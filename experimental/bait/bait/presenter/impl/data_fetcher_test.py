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

def _assert_state_change(stateChangeQueue, updateType, nodeId, data):
    assert(not stateChangeQueue.empty())
    stateChange = stateChangeQueue.get()
    assert(updateType == stateChange[data_fetcher.UPDATE_TYPE_IDX])
    assert(nodeId == stateChange[data_fetcher.NODE_ID_IDX])
    assert(data == stateChange[data_fetcher.DATA_IDX])


def _data_fetcher_test(numThreads):
    stateChangeQueue = Queue.Queue()
    df = data_fetcher.DataFetcher(_DummyModel(), numThreads)

    df.start()
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

    # wait for items to be processed
    while not df._fetchQueue.empty():
        time.sleep(0)

    # assert output
    _assert_state_change(stateChangeQueue, model.UpdateTypes.ATTRIBUTES, 1, True)
    _assert_state_change(stateChangeQueue, model.UpdateTypes.CHILDREN, 1, True)
    _assert_state_change(stateChangeQueue, model.UpdateTypes.DETAILS, 1, True)
    _assert_state_change(stateChangeQueue, model.UpdateTypes.CHILDREN, 1, True)
    _assert_state_change(stateChangeQueue, model.UpdateTypes.DETAILS, 1, True)

    # shut down DataFetcher output
    df.shutdown()

    # skip post-shutdown update
    df.async_fetch(1, model.UpdateTypes.ATTRIBUTES, stateChangeQueue)

    assert df._fetchQueue.empty()
    assert stateChangeQueue.empty()


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
    assert 100 > stateChangeQueue.qsize()
