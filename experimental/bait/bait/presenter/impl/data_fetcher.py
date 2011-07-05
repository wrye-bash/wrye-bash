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


UPDATE_TYPE_IDX = 0
NODE_ID_IDX = 1
DATA_IDX = 2

_logger = logging.getLogger(__name__)


class DataFetcher:
    def __init__(self, model_, numThreads=1):
        self._model = model_
        self._numThreads = numThreads
        self._fetchQueue = Queue.Queue() # (nodeId, updateTypeMask, stateChangeQueue)
        self._fetchThreads = []
        self._shutdownLock = threading.Lock()
        self._shutdown = False
        self._updateInfo = zip(
            (model.UpdateTypes.ATTRIBUTES,
             model.UpdateTypes.CHILDREN,
             model.UpdateTypes.DETAILS),
            (model_.get_node_attributes,
             model_.get_node_children,
             model_.get_node_details),
            ("attributes", "children", "details"))

    def start(self):
        if len(self._fetchThreads) is not 0:
            raise RuntimeError("DataFetcher instance already started")
        for threadIdx in xrange(self._numThreads):
            t = threading.Thread(name="DataFetcher"+str(threadIdx), target=self._run)
            t.start()
            self._fetchThreads.append(t)

    def shutdown(self):
        with self._shutdownLock:
            self._shutdown = True
            for threadNum in xrange(self._numThreads):
                self._fetchQueue.put(None)
        for t in self._fetchThreads:
            t.join()
        self._fetchThreads = []

    def async_fetch(self, nodeId, updateTypeMask, stateChangeQueue):
        fetchRequest = (nodeId, updateTypeMask, stateChangeQueue)
        with self._shutdownLock:
            if self._shutdown:
                return
            self._fetchQueue.put(fetchRequest)

    def _run(self):
        _logger.debug("data fetcher thread starting")
        while True:
            fetchRequest = self._fetchQueue.get()
            # quit on None
            if fetchRequest is None:
                _logger.debug(
                    "received sentinel value; data fetcher thread exiting")
                break
            with self._shutdownLock:
                # if we are shutting down, eat all updates
                if self._shutdown:
                    continue
                try:
                    nodeId, updateTypeMask, stateChangeQueue = fetchRequest
                    _logger.debug("fetching %s for nodeId %d", updateTypeMask, nodeId)
                    if 0 == updateTypeMask:
                        _logger.warn("zero updateTypeMask in data fetcher")
                        continue
                    for updateType, updateFn, updateName in self._updateInfo:
                        if 0 != updateTypeMask & updateType:
                            updateTypeMask = updateTypeMask ^ updateType
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
                except Exception as e:
                    _logger.warn("invalid fetch reqeuest: %s: %s", str(fetchRequest), e)