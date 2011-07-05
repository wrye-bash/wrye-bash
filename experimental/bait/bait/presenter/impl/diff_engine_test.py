# -*- coding: utf-8 -*-
#
# bait/presenter/impl/diff_engine_test.py
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

from . import diff_engine
from ... import model
from ...model import node_attributes, node_children
from ... import presenter


# local abbreviations
_ATTRIBUTES = model.UpdateTypes.ATTRIBUTES
_CHILDREN = model.UpdateTypes.CHILDREN
_DETAILS = model.UpdateTypes.DETAILS


class _DummyManager:
    def __init__(self):
        self.enabled = False
        self.targetPackage = None
    def enable_set_target_package(self, isEnabled):
        self.enabled = isEnabled
    def set_target_pacakge(self, targetPackage):
        assert self.enabled
        self.targetPackage = targetPackage


def _assert_view_command(viewCommandQueue, filterId, current, total):
    assert(not viewUpdateQueue.empty())
    setFilterStatsUpdate = viewCommandQueue.get()
    assert(filterId == setFilterStatsUpdate.filterId)
    assert(current == setFilterStatsUpdate.current)
    assert(total == setFilterStatsUpdate.total)

def _assert_load_reqeuest(loadRequestQueue, updateMask, nodeId):
    assert not loadRequestQueue.empty()
    loadRequest = loadRequestQueue.get()
    assert 2 == len(loadRequest)
    assert updateMask == loadRequest[0]
    assert nodeId == loadRequest[1]
    assert loadRequestQueue.empty()

def _assert_load_requests(loadReqeustQueue, updates):
    """updates is a dict of nodeId -> updateMask"""
    for updateNum in xrange(len(updates)):
        assert not loadRequestQueue.empty()
        loadRequest = loadRequestQueue.get()
        assert 2 == len(loadRequest)
        assert updates[loadRequest[1]] == loadRequest[0]
    assert loadRequestQueue.empty()


def test_packages_tree_diff_engine():
    viewCommandQueue = Queue.Queue()
    dummyGeneralTabManager = _DummyManager()
    dummyPackageContentsManager = _DummyManager()

    de = diff_engine.PackagesTreeDiffEngine(
        dummyGeneralTabManager, dummyPackageContentsManager, viewCommandQueue)

    # verify initial state
    assert viewCommandQueue.empty()
    _assert_load_reqeuest(de.loadRequestQueue, _CHILDREN, model.ROOT_NODE_ID)

    # test empty insert
    emptyRootNodeChildren = node_children.NodeChildren()
    assert de.update_is_in_scope(_CHILDREN, model.NodeTypes.ROOT)
    assert de.could_use_update(_CHILDREN, model.ROOT_NODE_ID,
                               emptyRootNodeChildren.version)
    de.update_children(model.ROOT_NODE_ID, emptyRootNodeChildren)
    assert viewCommandQueue.empty()
    assert de.loadRequestQueue.empty()

    # test non-empty insert
    nonemptyRootNodeChildren = node_children.NodeChildren()
    nonemptyRootNodeChildren.children.append(1)
    nonemptyRootNodeChildren.version = emptyRootNodeChildren.version + 1
    assert de.update_is_in_scope(_CHILDREN, model.NodeTypes.ROOT)
    assert not de.could_use_update(_CHILDREN, model.ROOT_NODE_ID,
                                   emptyRootNodeChildren.version)
    assert de.could_use_update(_CHILDREN, model.ROOT_NODE_ID,
                               nonemptyRootNodeChildren.version)
    de.update_children(model.ROOT_NODE_ID, nonemptyRootNodeChildren)
    assert viewCommandQueue.empty() # TODO
    assert de.loadRequestQueue.empty() # TODO

    de.could_use_update(updateType, nodeId, version)
    de.loadRequestQueue
    de.set_node_expansion(nodeId, isExpanded)
    de.set_pending_filter_mask(filterMask)
    de.set_pending_search_string(searchString)
    de.set_selected_nodes(nodeIds)
    de.update_attributes(nodeId, nodeAttributes)
    de.update_children(nodeId, nodeChildren)
    de.update_filter(filterMask)
    de.update_is_in_scope(updateType, nodeType)
    de.update_search_string(searchString)
