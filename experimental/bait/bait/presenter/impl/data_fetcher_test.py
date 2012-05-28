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
import threading
import time

from . import data_fetcher
from ... import model


_data = {}
_data[1] = True


class _DummyModel:
    def get_node_attributes(self, nodeId): return _data.get(nodeId)
    def get_node_children(self, nodeId): return _data.get(nodeId)
    def get_node_details(self, nodeId): return _data.get(nodeId)

def _assert_state_changes(stateChangeQueue, expectedStateChanges):
    """expectedStateChanges is a dictionary of (updateType,nodeId,data) -> count"""
    assert not stateChangeQueue.empty()
    while not stateChangeQueue.empty():
        stateChange = stateChangeQueue.get()
        count = expectedStateChanges[stateChange]
        if count == 1:
            del expectedStateChanges[stateChange]
        else:
            expectedStateChanges[stateChange] = count - 1
    assert stateChangeQueue.empty()
    assert len(expectedStateChanges) == 0

def _assert_state_change(stateChangeQueue, updateType, nodeId, data):
    assert not stateChangeQueue.empty()
    stateChange = stateChangeQueue.get()
    assert updateType == stateChange[data_fetcher.UPDATE_TYPE_IDX]
    assert nodeId == stateChange[data_fetcher.NODE_ID_IDX]
    assert data == stateChange[data_fetcher.DATA_IDX]


def _data_fetcher_test(numThreads):
    stateChangeQueue = Queue.Queue()
    df = data_fetcher.DataFetcher(_DummyModel(), numThreads)

    df.start()
    try:
        try:
            df.start()
            assert False
        except RuntimeError as e:
            pass

        # successfully fetch attributes
        df.async_fetch(1, model.UpdateTypes.ATTRIBUTES, stateChangeQueue)

        # successfully fetch children
        df.async_fetch(1, model.UpdateTypes.CHILDREN, stateChangeQueue)

        # successfully fetch details
        df.async_fetch(1, model.UpdateTypes.DETAILS, stateChangeQueue)

        # fail to fetch details
        df.async_fetch(0, model.UpdateTypes.DETAILS, stateChangeQueue)

        # warn about empty updateTypeMask
        df.async_fetch(1, model.UpdateTypes.parse_value(0), stateChangeQueue)

        # fetch children and details, then warn about unhandled part
        df.async_fetch(
            1,
            model.UpdateTypes.CHILDREN|model.UpdateTypes.DETAILS|model.UpdateTypes.ERROR,
            stateChangeQueue)

        # detect as garbage
        df.async_fetch(1, "garbage", None)

        # wait for items to be dequeued
        while 0 < df._fetchQueue.qsize():
            time.sleep(0)

    finally:
        df.shutdown()


    # assert output (order of events is not deterministic due to multithreading)
    _assert_state_changes(stateChangeQueue, {
        (model.UpdateTypes.ATTRIBUTES, 1, True):1,
        (model.UpdateTypes.CHILDREN, 1, True):2,
        (model.UpdateTypes.DETAILS, 1, True):2})

    # skip post-shutdown update
    df.async_fetch(1, model.UpdateTypes.ATTRIBUTES, stateChangeQueue)

    assert df._fetchQueue.empty()
    assert stateChangeQueue.empty()


def data_fetcher_test_single_threaded():
    _data_fetcher_test(1)

def data_fetcher_test_multi_threaded():
    _data_fetcher_test(20)

def data_fetcher_test_fast_shutdown():
    class SlowQueue(Queue.Queue):
        def __init__(self, lock):
            Queue.Queue.__init__(self)
            self._lock = lock
            self._isFirstTime = True
        """Ensures 'put'ting thread is as interrupted as possible"""
        def put(self, item):
            if self._isFirstTime:
                self._lock.acquire()
                time.sleep(0.1)
                self._isFirstTime = False
            Queue.Queue.put(self, item)
            time.sleep(0)

    lock = threading.RLock()
    stateChangeQueue = SlowQueue(lock)
    df = data_fetcher.DataFetcher(_DummyModel())
    df.start()
    lock.acquire()
    try:
        update = (1, model.UpdateTypes.ATTRIBUTES, stateChangeQueue)
        for n in xrange(100):
            df.async_fetch(*update)
    finally:
        # shutdown before the data fetcher thread has enough time to process the queue
        lock.release()
        df.shutdown()
    assert df._fetchQueue.empty()
    assert 100 > stateChangeQueue.qsize()

def data_fetcher_test_failed_start():
    class UnstableList(list):
        def append(self, object):
            list.append(self, object)
            raise RuntimeError("testing")

    df = data_fetcher.DataFetcher(_DummyModel())
    df._fetchThreads = UnstableList()
    try:
        df.start()
        assert False
    except:
        pass
