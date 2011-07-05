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
from ...presenter import view_commands


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
    def set_target_package(self, targetPackage):
        assert self.enabled
        self.targetPackage = targetPackage


def _assert_group(inQueue, itemDict, checkFn):
    assert not inQueue.empty()
    for itemNum in xrange(inQueue.qsize()):
        item = inQueue.get(block=False)
        checkFn(item, itemDict)
    assert inQueue.empty()

def _assert_filter_view_command(viewCommandQueue, filterId, current, total):
    assert not viewCommandQueue.empty()
    setFilterStatsUpdate = viewCommandQueue.get()
    assert filterId == setFilterStatsUpdate.filterId
    assert current == setFilterStatsUpdate.current
    assert total == setFilterStatsUpdate.total
    assert viewCommandQueue.empty()

def _assert_add_node_view_command(viewCommandQueue, nodeId, style,
                                  parentNodeId, predNodeId, isLastCommand=True):
    assert not viewCommandQueue.empty()
    addNodeCommand = viewCommandQueue.get()
    assert nodeId == addNodeCommand.nodeId
    assert cmp(style, addNodeCommand.style)
    assert parentNodeId == addNodeCommand.parentNodeId
    assert predNodeId == addNodeCommand.predecessorNodeId
    if isLastCommand:
        assert viewCommandQueue.empty()

def _assert_remove_node_view_command(viewCommandQueue, nodeId):
    assert not viewCommandQueue.empty()
    removeNodeCommand = viewCommandQueue.get()
    assert nodeId == removeNodeCommand.nodeId
    assert viewCommandQueue.empty()

def _assert_view_commands(viewCommandQueue, commands):
    """commands is a dict of filterId -> (current, total) or
    nodeId -> (style, parentNodeId, predNodeId).  they are accepted in any order"""
    def check_view_command(command, itemDict):
        if command.commandId == view_commands.CommandIds.SET_FILTER_STATS:
            filterId = command.filterId
            expectedUpdate = itemDict[filterId]
            assert expectedUpdate[0] == command.current
            assert expectedUpdate[1] == command.total
            del itemDict[filterId]
        elif command.commandId == view_commands.CommandIds.ADD_PACKAGE or \
             command.commandId == view_commands.CommandIds.ADD_GROUP:
            nodeId = command.nodeId
            expectedUpdate = itemDict[nodeId]
            assert cmp(expectedUpdate[0], command.style)
            assert expectedUpdate[1] == command.parentNodeId
            assert expectedUpdate[2] == command.predecessorNodeId
            del itemDict[nodeId]
        else:
            # unhandled case
            assert False
    _assert_group(viewCommandQueue, commands, check_view_command)

def _assert_load_request(loadRequestQueue, updateMask, nodeId):
    assert not loadRequestQueue.empty()
    loadRequest = loadRequestQueue.get()
    assert updateMask == loadRequest[diff_engine.UPDATE_TYPE_MASK_IDX]
    assert nodeId == loadRequest[diff_engine.NODE_ID_IDX]
    assert loadRequestQueue.empty()

def _assert_load_requests(loadRequestQueue, updates):
    """updates is a dict of nodeId -> updateMask.  updates are accepted in any order"""
    def check_load_request(loadRequest, itemDict):
        nodeId = loadRequest[diff_engine.NODE_ID_IDX]
        assert itemDict[nodeId] == loadRequest[diff_engine.UPDATE_TYPE_MASK_IDX]
        del itemDict[nodeId]
    _assert_group(loadRequestQueue, updates, check_load_request)


def test_packages_tree_diff_engine():
    viewCommandQueue = Queue.Queue()
    dummyGeneralTabManager = _DummyManager()
    dummyPackageContentsManager = _DummyManager()

    de = diff_engine.PackagesTreeDiffEngine(
        dummyGeneralTabManager, dummyPackageContentsManager, viewCommandQueue)

    # set and verify initial state
    assert viewCommandQueue.empty()
    _assert_load_request(de.loadRequestQueue, _CHILDREN, model.ROOT_NODE_ID)
    de.set_selected_nodes(None)
    de.set_pending_search_string(None)
    de.update_search_string(None)
    filterMask = presenter.FilterIds.PACKAGES_INSTALLED|\
               presenter.FilterIds.PACKAGES_NOT_INSTALLED
    de.set_pending_filter_mask(filterMask)
    de.update_filter(filterMask)
    assert viewCommandQueue.empty()
    assert de.loadRequestQueue.empty()

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
    assert viewCommandQueue.empty()
    _assert_load_request(de.loadRequestQueue, _ATTRIBUTES|_CHILDREN, 1)
    # service load request
    packageNode = node_attributes.PackageNodeAttributes()
    packageNode.hasMatched = True
    packageNode.hasWizard = True
    packageNode.hasSubpackages = True
    packageNode.isArchive = True
    packageNode.isInstalled = True
    packageNode.isNew = True
    packageNode.label = "testPackage"
    packageNode.parentNodeId = model.ROOT_NODE_ID
    assert de.update_is_in_scope(_ATTRIBUTES, packageNode.nodeType)
    assert de.could_use_update(_ATTRIBUTES, 1, packageNode.version)
    de.update_attributes(1, packageNode)
    assert de.loadRequestQueue.empty()
    _assert_view_commands(
        viewCommandQueue,
        {presenter.FilterIds.PACKAGES_INSTALLED:(1,1),
         1:(view_commands.Style(
             fontStyleMask=view_commands.FontStyleIds.BOLD,
             foregroundColorId=view_commands.ForegroundColorIds.HAS_SUBPACKAGES,
             checkboxState=True,
             iconId=view_commands.IconIds.INSTALLER_MATCHES_WIZ),0,None)})

    # update filters to hide node 1
    filterMask = presenter.FilterIds.PACKAGES_NOT_INSTALLED
    de.set_pending_filter_mask(filterMask)
    de.update_filter(filterMask)
    assert de.loadRequestQueue.empty()
    _assert_remove_node_view_command(viewCommandQueue, 1)

    # add in some more nodes
    nodeChildren = node_children.NodeChildren([1,2,6,10])
    nodeChildren.version = 2
    de.update_children(model.ROOT_NODE_ID, nodeChildren)
    _assert_load_requests(de.loadRequestQueue, {2:_ATTRIBUTES|_CHILDREN,
                                                6:_ATTRIBUTES|_CHILDREN,
                                                10:_ATTRIBUTES|_CHILDREN})

    installedGroup = node_attributes.GroupNodeAttributes()
    installedGroup.isInstalled = True
    installedGroup.isDirty = True
    installedGroup.label = "installedGroup"
    installedGroup.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(2, installedGroup)
    assert viewCommandQueue.empty()
    assert de.loadRequestQueue.empty()
    de.update_children(2, node_children.NodeChildren([3, 4, 5]))
    assert viewCommandQueue.empty()
    _assert_load_requests(de.loadRequestQueue, {3:_ATTRIBUTES|_CHILDREN,
                                                4:_ATTRIBUTES|_CHILDREN,
                                                5:_ATTRIBUTES|_CHILDREN})
    instPkg1 = node_attributes.PackageNodeAttributes()
    instPkg1.hasMismatched = True
    instPkg1.isInstalled = True
    instPkg1.label = "instPkg1"
    instPkg1.parentNodeId = 2
    instPkg2 = node_attributes.PackageNodeAttributes()
    instPkg2.hasMismatched = True
    instPkg2.isDirty = True
    instPkg2.isInstalled = True
    instPkg2.label = "instPkg2"
    instPkg2.parentNodeId = 2
    instPkg3 = node_attributes.PackageNodeAttributes()
    instPkg3.hasMatched = True
    instPkg3.isInstalled = True
    instPkg3.label = "instPkg3"
    instPkg3.parentNodeId = 2
    # update children attributes out of order
    de.update_attributes(3, instPkg1)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 2, 2)
    de.update_attributes(5, instPkg3)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 3, 3)
    de.update_attributes(4, instPkg2)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 4, 4)
    assert de.loadRequestQueue.empty()

    uninstalledGroup = node_attributes.GroupNodeAttributes()
    uninstalledGroup.isNotInstalled = True
    uninstalledGroup.label = "uninstalledGroup"
    uninstalledGroup.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(6, uninstalledGroup)
    _assert_add_node_view_command(viewCommandQueue, 6, view_commands.Style(), 0, None)
    assert de.loadRequestQueue.empty()
    de.update_children(6, node_children.NodeChildren([7, 8, 9]))
    assert viewCommandQueue.empty()
    _assert_load_requests(de.loadRequestQueue, {7:_ATTRIBUTES|_CHILDREN,
                                                8:_ATTRIBUTES|_CHILDREN,
                                                9:_ATTRIBUTES|_CHILDREN})
    uninstPkg1 = node_attributes.PackageNodeAttributes()
    uninstPkg1.hasMissing = True
    uninstPkg1.isNotInstalled = True
    uninstPkg1.label = "uninstPkg1"
    uninstPkg1.parentNodeId = 6
    uninstPkg2 = node_attributes.PackageNodeAttributes()
    uninstPkg2.hasSubpackages = True
    uninstPkg2.isNotInstalled = True
    uninstPkg2.label = "uninstPkg2"
    uninstPkg2.parentNodeId = 6
    uninstPkg3 = node_attributes.PackageNodeAttributes()
    uninstPkg3.hasMissing = True
    uninstPkg3.isNotInstalled = True
    uninstPkg3.label = "uninstPkg3"
    uninstPkg3.parentNodeId = 6
    # update children attributes in reverse order
    de.update_attributes(9, uninstPkg3)
    _assert_view_commands(
        viewCommandQueue,
        {presenter.FilterIds.PACKAGES_NOT_INSTALLED:(1,1),
         9:(view_commands.Style(
             iconId=view_commands.IconIds.PROJECT_MISSING,
             checkboxState=False),6,None),
         6:(view_commands.Style(),model.ROOT_NODE_ID,1)})
    de.update_attributes(8, uninstPkg2)
    _assert_view_commands(
        viewCommandQueue,
        {presenter.FilterIds.PACKAGES_NOT_INSTALLED:(2,2),
         8:(view_commands.Style(
             foregroundColorId=view_commands.ForegroundColorIds.HAS_SUBPACKAGES,
             iconId=view_commands.IconIds.PROJECT_EMPTY,
             checkboxState=False),6,None)})
    de.update_attributes(7, uninstPkg1)
    _assert_view_commands(
        viewCommandQueue,
        {presenter.FilterIds.PACKAGES_NOT_INSTALLED:(3,3),
         7:(view_commands.Style(
             iconId=view_commands.IconIds.PROJECT_MISSING,
             checkboxState=False),6,None)})
    assert de.loadRequestQueue.empty()

    hiddenGroup = node_attributes.GroupNodeAttributes()
    hiddenGroup.isHidden = True
    hiddenGroup.label = "hiddenGroup"
    hiddenGroup.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(10, hiddenGroup)
    assert viewCommandQueue.empty()
    assert de.loadRequestQueue.empty()
    de.update_children(10, node_children.NodeChildren([11, 12, 13]))
    assert viewCommandQueue.empty()
    _assert_load_requests(de.loadRequestQueue, {11:_ATTRIBUTES|_CHILDREN,
                                                12:_ATTRIBUTES|_CHILDREN,
                                                13:_ATTRIBUTES|_CHILDREN})
    hiddenPkg1 = node_attributes.PackageNodeAttributes()
    hiddenPkg1.isHidden = True
    hiddenPkg1.label = "hiddenPkg1"
    hiddenPkg1.parentNodeId = 10
    hiddenPkg2 = node_attributes.PackageNodeAttributes()
    hiddenPkg2.isHidden = True
    hiddenPkg2.label = "hiddenPkg2"
    hiddenPkg2.parentNodeId = 10
    hiddenPkg3 = node_attributes.PackageNodeAttributes()
    hiddenPkg3.isHidden = True
    hiddenPkg3.label = "hiddenPkg3"
    hiddenPkg3.parentNodeId = 10
    # update children attributes in order
    de.update_attributes(11, hiddenPkg1)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_HIDDEN, 1, 1)
    de.update_attributes(12, hiddenPkg2)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_HIDDEN, 2, 2)
    de.update_attributes(13, hiddenPkg3)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_HIDDEN, 3, 3)
    assert de.loadRequestQueue.empty()

    # enable more filters
    filterMask = presenter.FilterIds.PACKAGES_NOT_INSTALLED|\
               presenter.FilterIds.PACKAGES_HIDDEN
    de.set_pending_filter_mask(filterMask)
    de.update_filter(filterMask)
    assert de.loadRequestQueue.empty()
    _assert_add_node_view_command(
        viewCommandQueue, 10, view_commands.Style(
            foregroundColorId=view_commands.ForegroundColorIds.DISABLED),
        model.ROOT_NODE_ID, 6, False)
    _assert_add_node_view_command(
        viewCommandQueue, 11, view_commands.Style(
            foregroundColorId=view_commands.ForegroundColorIds.DISABLED,
            iconId=view_commands.IconIds.PROJECT_EMPTY), 10, None, False)
    _assert_add_node_view_command(
        viewCommandQueue, 12, view_commands.Style(
            foregroundColorId=view_commands.ForegroundColorIds.DISABLED,
            iconId=view_commands.IconIds.PROJECT_EMPTY), 10, 11, False)
    _assert_add_node_view_command(
        viewCommandQueue, 13, view_commands.Style(
            foregroundColorId=view_commands.ForegroundColorIds.DISABLED,
            iconId=view_commands.IconIds.PROJECT_EMPTY), 10, 12)

    # filter out packages not in a group
    de.set_pending_search_string("group")
    de.update_search_string("group")
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 3, 4)


    import logging
    logger = logging.getLogger(__name__)
    logger.info("viewCommandQueue size: %d", viewCommandQueue.qsize())
    for itemNum in xrange(viewCommandQueue.qsize()):
        logger.info("  %s", str(viewCommandQueue.get()))
    logger.info("loadRequestQueue size: %d", de.loadRequestQueue.qsize())
    for itemNum in xrange(de.loadRequestQueue.qsize()):
        logger.info("  %s", str(de.loadRequestQueue.get()))

    #de.could_use_update(updateType, nodeId, version)
    #de.loadRequestQueue
    #de.set_node_expansion(nodeId, isExpanded)
    #de.set_pending_filter_mask(filterMask)
    #de.set_pending_search_string(searchString)
    #de.set_selected_nodes(nodeIds)
    #de.update_attributes(nodeId, nodeAttributes)
    #de.update_children(nodeId, nodeChildren)
    #de.update_filter(filterMask)
    #de.update_is_in_scope(updateType, nodeType)
    #de.update_search_string(searchString)
