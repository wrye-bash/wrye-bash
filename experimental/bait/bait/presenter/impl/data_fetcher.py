# -*- coding: utf-8 -*-
#
# bait/presenter/impl/data_fetcher.py
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <http://www.gnu.org/licenses/>.
#
#  Wrye Bash Copyright (C) 2011 Myk Taylor
#
# =============================================================================

import Queue
import logging
import threading

from ... import model
from ...util import monitored_thread, process_monitor


UPDATE_TYPE_IDX = 0
NODE_ID_IDX = 1
DATA_IDX = 2

_logger = logging.getLogger(__name__)


class DataFetcher:
    def __init__(self, model_, numThreads=1):
        self._model = model_
        self._numThreads = numThreads
        # fetchQueue is not absolutely guaranteed to be empty after shutdown is called
        # (nodeId, updateTypeMask, stateChangeQueue)
        self._fetchQueue = Queue.Queue(maxsize=100)
        self._fetchThreads = []
        self._isShutdownLock = threading.RLock()
        self._isShutdown = True
        self._updateInfo = zip(
            (model.UpdateTypes.ATTRIBUTES,
             model.UpdateTypes.CHILDREN,
             model.UpdateTypes.DETAILS),
            (model_.get_node_attributes,
             model_.get_node_children,
             model_.get_node_details),
            ("attributes", "children", "details"))

    def start(self):
        _logger.debug("starting data fetcher")
        with self._isShutdownLock:
            if not self._isShutdown:
                raise RuntimeError("DataFetcher instance already started")
            try:
                for threadIdx in xrange(self._numThreads):
                    t = monitored_thread.MonitoredThread(
                        name="DataFetcher"+str(threadIdx), target=self._run)
                    t.start()
                    self._fetchThreads.append(t)
                self._isShutdown = False
                process_monitor.register_statistics_callback(self._dump_stats)
            except:
                self._shutdown()
                raise

    def shutdown(self):
        process_monitor.unregister_statistics_callback(self._dump_stats)
        self._shutdown()

    def async_fetch(self, nodeId, updateTypeMask, stateChangeQueue):
        _logger.debug("scheduling fetch of %s for nodeId %d", updateTypeMask, nodeId)
        fetchRequest = (nodeId, updateTypeMask, stateChangeQueue)
        if self._isShutdown:
            return
        self._fetchQueue.put(fetchRequest)

    def _dump_stats(self, logFn):
        logFn("fetchQueue length: %d", self._fetchQueue.qsize())

    def _run(self):
        _logger.debug("data fetcher thread starting")
        fetchQueue = self._fetchQueue
        while True:
            fetchRequest = fetchQueue.get()
            # quit on None
            if fetchRequest is None:
                _logger.debug(
                    "received sentinel value; data fetcher thread exiting")
                fetchQueue.task_done()
                break
            # if we are shutting down, eat all updates
            if self._isShutdown:
                fetchQueue.task_done()
                continue
            try:
                nodeId, updateTypeMask, stateChangeQueue = fetchRequest
                _logger.debug("fetching %s for nodeId %d", updateTypeMask, nodeId)
                if 0 == updateTypeMask:
                    _logger.warn("zero updateTypeMask in data fetcher")
                    fetchQueue.task_done()
                    continue
                for updateType, updateFn, updateName in self._updateInfo:
                    if updateType in updateTypeMask:
                        updateTypeMask ^= updateType
                        data = updateFn(nodeId)
                        if data is None:
                            _logger.debug("%s for nodeId %d not found",
                                          updateName, nodeId)
                        else:
                            stateChangeQueue.put((updateType, nodeId, data))
                    if 0 == updateTypeMask:
                        break
                if 0 != updateTypeMask:
                    _logger.warn("unhandled fetch request type: 0x%x",
                                     updateTypeMask.value)
            except:
                _logger.warn("invalid fetch reqeuest: %s", str(fetchRequest),
                             exc_info=True)
            fetchQueue.task_done()

    def _shutdown(self):
        _logger.debug("shutting down data fetcher")
        with self._isShutdownLock:
            self._isShutdown = True
            for threadNum in xrange(len(self._fetchThreads)):
                self._fetchQueue.put(None)
            while 0 < len(self._fetchThreads):
                t = self._fetchThreads.pop()
                t.join()
