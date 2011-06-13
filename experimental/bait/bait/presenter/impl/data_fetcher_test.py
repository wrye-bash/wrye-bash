# -*- coding: utf-8 -*-
#
# bait/presenter/impl/data_fetcher_test.py
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
import time

from . import data_fetcher
from ... import model


_logger = logging.getLogger(__name__)

_data = {}
_data[1] = True


class _DummyModel:
    def get_node_attributes(self, nodeId):
        _logger.debug("retrieving attributes for node %d", nodeId)
        return _data.get(nodeId)

    def get_node_children(self, nodeId):
        _logger.debug("retrieving children for node %d", nodeId)
        return _data.get(nodeId)

    def get_node_details(self, nodeId):
        _logger.debug("retrieving details for node %d", nodeId)
        return _data.get(nodeId)

def _state_change_queue_reader(stateChangeQueue):
    while True:
        stateChange = stateChangeQueue.get()
        if stateChange is None:
            _logger.debug(
                "received sentinel value; state change reader thread exiting")
            break
        _logger.debug("received state change: %s", str(stateChange))


def _data_fetcher_test(numThreads):
    stateChangeQueue = Queue.Queue()
    stateChangeQueueReaderThread = threading.Thread(name="StateChangeReader",
                                                    target=_state_change_queue_reader,
                                                    args=(stateChangeQueue,))
    stateChangeQueueReaderThread.start()

    dummyModel = _DummyModel()
    df = data_fetcher.DataFetcher(dummyModel, numThreads)

    _logger.debug("starting DataFetcher")
    df.start()
    try:
        _logger.debug("starting DataFetcher again; should throw")
        df.start()
        _logger.warn("should not get here")
    except RuntimeError as e:
        _logger.debug("correctly threw: %s", e)

    update = (1, model.UpdateTypes.ATTRIBUTES, stateChangeQueue)
    _logger.debug("should successfully fetch attributes: %s", str(update))
    df.async_fetch(*update)

    update = (1, model.UpdateTypes.CHILDREN, stateChangeQueue)
    _logger.debug("should successfully fetch children: %s", str(update))
    df.async_fetch(*update)

    update = (1, model.UpdateTypes.DETAILS, stateChangeQueue)
    _logger.debug("should successfully fetch details: %s", str(update))
    df.async_fetch(*update)

    update = (0, model.UpdateTypes.DETAILS, stateChangeQueue)
    _logger.debug("should fail to fetch details: %s", str(update))
    df.async_fetch(*update)

    update = (1, model.UpdateTypes.parse_value(0), stateChangeQueue)
    _logger.debug("should warn about empty updateTypeMask: %s", str(update))
    df.async_fetch(*update)

    update = (
        1,
        model.UpdateTypes.CHILDREN|model.UpdateTypes.DETAILS|model.UpdateTypes.ERROR,
        stateChangeQueue)
    _logger.debug("should fetch children and details, then warn about unhandled part: %s",
                  str(update))
    df.async_fetch(*update)

    update = (1, "garbage", None)
    _logger.debug("should be detected as garbage: %s", str(update))
    df.async_fetch(*update)

    _logger.debug("waiting for items to be processed")
    while not df._fetchQueue.empty():
        time.sleep(0)

    _logger.debug("shutting down DataFetcher output")
    df.shutdown()

    update = (1, model.UpdateTypes.ATTRIBUTES, stateChangeQueue)
    _logger.debug("should skip: %s", str(update))
    df.async_fetch(*update)

    _logger.debug("shutting down state change reader thread")
    stateChangeQueue.put(None)
    stateChangeQueueReaderThread.join()


def data_fetcher_test_single_threaded():
    _data_fetcher_test(1)

def data_fetcher_test_multi_threaded():
    _data_fetcher_test(20)

def data_fetcher_test_fast_shutdown():
    stateChangeQueue = Queue.Queue()
    df = data_fetcher.DataFetcher(_DummyModel())
    df.start()
    update = (1, model.UpdateTypes.ATTRIBUTES, stateChangeQueue)
    for n in xrange(100):
        df.async_fetch(*update)
    df.shutdown()
    stateChangeQueue.put(None)
    _state_change_queue_reader(stateChangeQueue)
