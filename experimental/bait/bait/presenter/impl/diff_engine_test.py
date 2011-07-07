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


# TODO: remove when done designing tests
def _dump_queue(inQueue):
    import logging
    logger = logging.getLogger(__name__)
    logger.info("inQueue size: %d", inQueue.qsize())
    for itemNum in xrange(inQueue.qsize()):
        logger.info("  %s", str(inQueue.get()))


class _DummyManager:
    def __init__(self):
        self.enabled = True
        self.targetPackage = None
        self.isMultiple = False
    def enable_set_target_package(self, isEnabled):
        self.enabled = isEnabled
    def set_target_package(self, nodeId, isMultiple):
        assert self.enabled
        self.targetPackage = nodeId
        self.isMultiple = isMultiple


def _assert_group(inQueue, checkFn):
    assert not inQueue.empty()
    for itemNum in xrange(inQueue.qsize()):
        item = inQueue.get(block=False)
        checkFn(item)
    assert inQueue.empty()

def _assert_filter_view_command(viewCommandQueue, filterId, current, total,
                                isLastCommand=True):
    assert not viewCommandQueue.empty()
    setFilterStatsUpdate = viewCommandQueue.get()
    assert filterId == setFilterStatsUpdate.filterId
    assert current == setFilterStatsUpdate.current
    assert total == setFilterStatsUpdate.total
    if isLastCommand:
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

def _assert_expand_view_command(viewCommandQueue, nodeId, isExpanded, isLastCommand=True):
    assert not viewCommandQueue.empty()
    expandCommand = viewCommandQueue.get()
    assert nodeId == expandCommand.nodeId
    assert isExpanded == expandCommand.isExpanded
    if isLastCommand:
        assert viewCommandQueue.empty()

def _assert_view_commands(viewCommandQueue, commands, optionalCommands=None):
    """commands is a dict of ("f", filterId) -> (current, total) or
    ("n", nodeId) -> (style, parentNodeId, predNodeId) or ("e", nodeId) -> isExpanded.
    they are accepted in any order.  the letter prefixes in the tuples are required to
    avoid hash collisions.  the second dictionary is for commands that may be issues,
    but are not required to be."""
    def pop(key):
        if key in commands:
            return commands.pop(key)
        if optionalCommands is None:
            raise KeyError(key)
        return optionalCommands.pop(key)
    def check_view_command(command):
        if command.commandId == view_commands.CommandIds.SET_FILTER_STATS:
            filterId = command.filterId
            expectedUpdate = pop(("f", filterId))
            assert expectedUpdate[0] == command.current
            assert expectedUpdate[1] == command.total
        elif command.commandId == view_commands.CommandIds.ADD_PACKAGE or \
             command.commandId == view_commands.CommandIds.ADD_GROUP or \
             command.commandId == view_commands.CommandIds.UPDATE_PACKAGE or \
             command.commandId == view_commands.CommandIds.UPDATE_GROUP:
            nodeId = command.nodeId
            expectedUpdate = pop(("n", nodeId))
            assert cmp(expectedUpdate[0], command.style)
            assert expectedUpdate[1] == command.parentNodeId
            assert expectedUpdate[2] == command.predecessorNodeId
        elif command.commandId == view_commands.CommandIds.REMOVE_PACKAGES_TREE_NODE:
            nodeId = command.nodeId
            expectedUpdate = pop(("n", nodeId))
        elif command.commandId == view_commands.CommandIds.EXPAND_GROUP:
            nodeId = command.nodeId
            expectedUpdate = pop(("e", nodeId))
            assert expectedUpdate == command.isExpanded
        else:
            # unhandled case
            raise NotImplementedError("unchecked viewCommand type")
    _assert_group(viewCommandQueue, check_view_command)
    assert len(commands) == 0

def _assert_load_request(loadRequestQueue, updateMask, nodeId):
    assert not loadRequestQueue.empty()
    loadRequest = loadRequestQueue.get()
    assert updateMask == loadRequest[diff_engine.UPDATE_TYPE_MASK_IDX]
    assert nodeId == loadRequest[diff_engine.NODE_ID_IDX]
    assert loadRequestQueue.empty()

def _assert_load_requests(loadRequestQueue, updates):
    """updates is a dict of nodeId -> updateMask.  updates are accepted in any order"""
    def check_load_request(loadRequest):
        nodeId = loadRequest[diff_engine.NODE_ID_IDX]
        assert updates.pop(nodeId) == loadRequest[diff_engine.UPDATE_TYPE_MASK_IDX]
    _assert_group(loadRequestQueue, check_load_request)
    assert len(updates) == 0


def test_packages_tree_diff_engine():
    viewCommandQueue = Queue.Queue()
    dummyGeneralTabManager = _DummyManager()
    dummyPackageContentsManager = _DummyManager()

    de = diff_engine.PackagesTreeDiffEngine(
        dummyGeneralTabManager, dummyPackageContentsManager, viewCommandQueue)

    # set and verify initial state
    assert viewCommandQueue.empty()
    _assert_load_request(de.loadRequestQueue, _CHILDREN, model.ROOT_NODE_ID)
    dummyGeneralTabManager.enable_set_target_package(True)
    dummyPackageContentsManager.enable_set_target_package(True)
    de.set_selected_nodes(None)
    assert dummyGeneralTabManager.targetPackage is None
    assert not dummyGeneralTabManager.isMultiple
    assert dummyPackageContentsManager.targetPackage is None
    assert not dummyPackageContentsManager.isMultiple
    dummyGeneralTabManager.enable_set_target_package(False)
    dummyPackageContentsManager.enable_set_target_package(False)
    de.set_pending_search_string(None)
    de.update_search_string(None)
    filterMask = presenter.FilterIds.PACKAGES_INSTALLED|\
               presenter.FilterIds.PACKAGES_NOT_INSTALLED
    de.set_pending_filter_mask(filterMask)
    de.update_filter(filterMask)
    assert viewCommandQueue.empty()
    assert de.loadRequestQueue.empty()

    assert not de.could_use_update(_ATTRIBUTES, 100, 0)
    assert not de.could_use_update(_ATTRIBUTES, model.ROOT_NODE_ID, 0)

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
    _assert_load_request(de.loadRequestQueue, _ATTRIBUTES, 1)
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
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 1)
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(1,1),
         ("n", 1):(view_commands.Style(
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
    _assert_load_requests(de.loadRequestQueue, {2:_ATTRIBUTES, 6:_ATTRIBUTES,
                                                10:_ATTRIBUTES})

    installedGroup = node_attributes.GroupNodeAttributes()
    installedGroup.isInstalled = True
    installedGroup.isDirty = True
    installedGroup.label = "instGroup"
    installedGroup.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(2, installedGroup)
    assert viewCommandQueue.empty()
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 2)
    de.update_children(2, node_children.NodeChildren([3, 4, 5]))
    assert viewCommandQueue.empty()
    _assert_load_requests(de.loadRequestQueue, {3:_ATTRIBUTES, 4:_ATTRIBUTES,
                                                5:_ATTRIBUTES})
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
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 3)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 2, 2)
    de.update_attributes(5, instPkg3)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 5)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 3, 3)
    de.update_attributes(4, instPkg2)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 4)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 4, 4)

    uninstalledGroup = node_attributes.GroupNodeAttributes()
    uninstalledGroup.isNotInstalled = True
    uninstalledGroup.label = "uninstalledGroup"
    uninstalledGroup.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(6, uninstalledGroup)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 6)
    de.update_children(6, node_children.NodeChildren([7, 8, 9]))
    assert viewCommandQueue.empty()
    _assert_load_requests(de.loadRequestQueue, {7:_ATTRIBUTES, 8:_ATTRIBUTES,
                                                9:_ATTRIBUTES})
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
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 9)
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(1,1),
         ("n", 6):(view_commands.Style(),0,None),
         ("n", 9):(view_commands.Style(
             iconId=view_commands.IconIds.PROJECT_MISSING,
             checkboxState=False),6,None)})
    de.update_attributes(8, uninstPkg2)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 8)
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(2,2),
         ("n", 8):(view_commands.Style(
             foregroundColorId=view_commands.ForegroundColorIds.HAS_SUBPACKAGES,
             iconId=view_commands.IconIds.PROJECT_EMPTY,
             checkboxState=False),6,None)})
    de.update_attributes(7, uninstPkg1)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 7)
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(3,3),
         ("n", 7):(view_commands.Style(
             iconId=view_commands.IconIds.PROJECT_MISSING,
             checkboxState=False),6,None)})

    hiddenGroup = node_attributes.GroupNodeAttributes()
    hiddenGroup.isHidden = True
    hiddenGroup.label = "hiddenGroup"
    hiddenGroup.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(10, hiddenGroup)
    assert viewCommandQueue.empty()
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 10)
    de.update_children(10, node_children.NodeChildren([11, 12, 13]))
    assert viewCommandQueue.empty()
    _assert_load_requests(de.loadRequestQueue, {11:_ATTRIBUTES, 12:_ATTRIBUTES,
                                                13:_ATTRIBUTES})
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
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 11)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_HIDDEN, 1, 1)
    de.update_attributes(12, hiddenPkg2)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 12)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_HIDDEN, 2, 2)
    de.update_attributes(13, hiddenPkg3)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 13)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_HIDDEN, 3, 3)

    # play with node expansion a bit
    de.set_node_expansion(10, True)
    _assert_expand_view_command(viewCommandQueue, 10, True)
    de.set_node_expansion(6, False)
    assert viewCommandQueue.empty()
    de.set_node_expansion(6, True)
    _assert_expand_view_command(viewCommandQueue, 6, True)
    de.set_node_expansion(6, True)
    assert viewCommandQueue.empty()
    de.set_node_expansion(6, False)
    _assert_expand_view_command(viewCommandQueue, 6, False)

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
    _assert_expand_view_command(viewCommandQueue, 10, True, False)
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

    # add a non-matching package to a matching group while the filter is active
    updatedHiddenNodeChildren = node_children.NodeChildren([11, 12, 13, 14])
    updatedHiddenNodeChildren.version = 1
    de.update_children(10, updatedHiddenNodeChildren)
    assert viewCommandQueue.empty()
    _assert_load_request(de.loadRequestQueue, _ATTRIBUTES, 14)
    hiddenPkg4 = node_attributes.PackageNodeAttributes()
    hiddenPkg4.isHidden = True
    hiddenPkg4.label = "hiddenPkg4"
    hiddenPkg4.parentNodeId = 10
    de.update_attributes(14, hiddenPkg4)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 14)
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_HIDDEN):(4,4),
         ("n", 14):(view_commands.Style(
             foregroundColorId=view_commands.ForegroundColorIds.DISABLED,
             iconId=view_commands.IconIds.PROJECT_EMPTY),10,13)})

    # add a matching package while the filter is active
    nodeChildren = node_children.NodeChildren([1,2,6,10,15])
    nodeChildren.version = 3
    de.update_children(model.ROOT_NODE_ID, nodeChildren)
    _assert_load_request(de.loadRequestQueue, _ATTRIBUTES, 15)
    hiddenPkg5 = node_attributes.PackageNodeAttributes()
    hiddenPkg5.isHidden = True
    hiddenPkg5.label = "hiddenPkg5NotInAGroup"
    hiddenPkg5.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(15, hiddenPkg5)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 15)
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_HIDDEN):(5,5),
         ("n", 15):(view_commands.Style(
             foregroundColorId=view_commands.ForegroundColorIds.DISABLED,
             iconId=view_commands.IconIds.PROJECT_EMPTY),model.ROOT_NODE_ID,10)})
    assert de.loadRequestQueue.empty()

    dummyGeneralTabManager.enable_set_target_package(True)
    dummyPackageContentsManager.enable_set_target_package(True)
    de.set_selected_nodes([13,15])
    assert dummyGeneralTabManager.targetPackage is None
    assert dummyGeneralTabManager.isMultiple
    assert dummyPackageContentsManager.targetPackage is None
    assert dummyPackageContentsManager.isMultiple

    # single out a particular package
    de.set_pending_search_string("hiddenPkg3")
    de.update_search_string("hiddenPkg3")
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(0,4),
         ("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(0,3),
         ("f", presenter.FilterIds.PACKAGES_HIDDEN):(1,5),
         ("n", 6):None, ("n", 11):None, ("n", 12):None, ("n", 14):None, ("n", 15):None},
        {("n", 8):None, ("n", 9):None})

    # ensure managers were updated properly
    assert dummyGeneralTabManager.targetPackage is 13
    assert not dummyGeneralTabManager.isMultiple
    assert dummyPackageContentsManager.targetPackage is 13
    assert not dummyPackageContentsManager.isMultiple

    # stop testing managers so it doesn't get in the way
    de.set_selected_nodes(None)
    assert dummyGeneralTabManager.targetPackage is None
    assert dummyGeneralTabManager.isMultiple is False
    assert dummyPackageContentsManager.targetPackage is None
    assert dummyPackageContentsManager.isMultiple is False
    dummyGeneralTabManager.enable_set_target_package(False)
    dummyPackageContentsManager.enable_set_target_package(False)

    # single out a particular group
    de.set_pending_search_string("instGroup")
    de.update_search_string("instGroup")
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(3,4),
         ("f", presenter.FilterIds.PACKAGES_HIDDEN):(0,5),
         ("n", 10):None})
    filterMask = presenter.FilterIds.PACKAGES_INSTALLED|\
               presenter.FilterIds.PACKAGES_HIDDEN
    de.set_pending_filter_mask(filterMask)
    de.update_filter(filterMask)
    _assert_view_commands(
        viewCommandQueue,
        {("n", 2):(view_commands.Style(
            highlightColorId=view_commands.HighlightColorIds.DIRTY,
            fontStyleMask=view_commands.FontStyleIds.ITALICS),
                   model.ROOT_NODE_ID,None),
         ("n", 3):(view_commands.Style(
             iconId=view_commands.IconIds.PROJECT_MISMATCHED,
             checkboxState=True),2,None),
         ("n", 4):(view_commands.Style(
             iconId=view_commands.IconIds.PROJECT_MISMATCHED,
             fontStyleMask=view_commands.FontStyleIds.ITALICS,
             highlightColorId=view_commands.HighlightColorIds.DIRTY,
             checkboxState=True),2,3),
         ("n", 5):(view_commands.Style(
             iconId=view_commands.IconIds.PROJECT_MATCHES,
             checkboxState=True),2,4)})

    # update an existing group so that it now matches the search
    updatedHiddenGroup = node_attributes.GroupNodeAttributes()
    updatedHiddenGroup.isHidden = True
    updatedHiddenGroup.label = "hiddenInstGroup"
    updatedHiddenGroup.parentNodeId = model.ROOT_NODE_ID
    updatedHiddenGroup.version = 1
    de.update_attributes(10, updatedHiddenGroup)
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_HIDDEN):(4,5),
         ("n", 10):(view_commands.Style(
             foregroundColorId=view_commands.ForegroundColorIds.DISABLED),
                    model.ROOT_NODE_ID, 2, False),
         ("e", 10):True,
         ("n", 11):(view_commands.Style(
             foregroundColorId=view_commands.ForegroundColorIds.DISABLED,
             iconId=view_commands.IconIds.PROJECT_EMPTY), 10, None),
         ("n", 12):(view_commands.Style(
             foregroundColorId=view_commands.ForegroundColorIds.DISABLED,
             iconId=view_commands.IconIds.PROJECT_EMPTY), 10, 11),
         ("n", 13):(view_commands.Style(
             foregroundColorId=view_commands.ForegroundColorIds.DISABLED,
             iconId=view_commands.IconIds.PROJECT_EMPTY), 10, 12),
         ("n", 14):(view_commands.Style(
             foregroundColorId=view_commands.ForegroundColorIds.DISABLED,
            iconId=view_commands.IconIds.PROJECT_EMPTY), 10, 13)})

    # ensure stale search strings are not evaluated
    de.set_pending_search_string("hiddenPkg2")
    de.set_pending_search_string("hiddenPkg3")
    de.update_search_string("hiddenPkg2")
    assert viewCommandQueue.empty()
    de.update_search_string("hiddenPkg3")
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(0,4),
         ("f", presenter.FilterIds.PACKAGES_HIDDEN):(1,5),
         ("n", 2):None, ("n", 11):None, ("n", 12):None, ("n", 14):None},
        {("n", 4):None, ("n", 5):None})
    de.set_pending_search_string("hiddenPkg2")
    de.set_pending_search_string("hiddenPkg3")
    de.update_search_string("hiddenPkg2")
    assert viewCommandQueue.empty()
    de.update_search_string("hiddenPkg3")
    assert viewCommandQueue.empty()

    # ensure stale filters are not evaluated
    de.set_pending_filter_mask(presenter.FilterIds.PACKAGES_HIDDEN)
    de.set_pending_filter_mask(filterMask)
    de.update_filter(presenter.FilterIds.PACKAGES_HIDDEN)
    de.update_filter(filterMask)
    assert viewCommandQueue.empty()


def test_packages_tree_diff_engine_style():
    viewCommandQueue = Queue.Queue()
    dummyGeneralTabManager = _DummyManager()
    dummyPackageContentsManager = _DummyManager()

    de = diff_engine.PackagesTreeDiffEngine(
        dummyGeneralTabManager, dummyPackageContentsManager, viewCommandQueue)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, model.ROOT_NODE_ID)

    # turn on all filters so we can test the visual styles
    filterMask = presenter.FilterIds.PACKAGES_INSTALLED|\
               presenter.FilterIds.PACKAGES_NOT_INSTALLED|\
               presenter.FilterIds.PACKAGES_HIDDEN
    de.set_pending_filter_mask(filterMask)
    de.update_filter(filterMask)

    de.update_children(model.ROOT_NODE_ID, node_children.NodeChildren(range(1,19)))
    _assert_load_requests(de.loadRequestQueue, {i:_ATTRIBUTES for i in range(1,19)})

    pkg1 = node_attributes.PackageNodeAttributes()
    pkg1.isNotInstalled = True
    pkg1.isCorrupt = True
    pkg1.isNew = True
    pkg1.isArchive = True
    pkg1.label = "pkg1"
    pkg1.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(1, pkg1)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 1, 1, False)
    _assert_add_node_view_command(
        viewCommandQueue, 1, view_commands.Style(
            fontStyleMask=view_commands.FontStyleIds.BOLD|\
            view_commands.FontStyleIds.ITALICS,
            highlightColorId=view_commands.HighlightColorIds.ERROR,
            checkboxState=False,
            iconId=view_commands.IconIds.INSTALLER_UNINSTALLABLE),
        model.ROOT_NODE_ID, None)

    pkg2 = node_attributes.PackageNodeAttributes()
    pkg2.isNotInstalled = True
    pkg2.isCorrupt = True
    pkg2.label = "pkg2"
    pkg2.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(2, pkg2)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 2, 2, False)
    _assert_add_node_view_command(
        viewCommandQueue, 2, view_commands.Style(
            fontStyleMask=view_commands.FontStyleIds.ITALICS,
            highlightColorId=view_commands.HighlightColorIds.ERROR,
            checkboxState=False,
            iconId=view_commands.IconIds.PROJECT_UNINSTALLABLE),
        model.ROOT_NODE_ID, 1)

    pkg3 = node_attributes.PackageNodeAttributes()
    pkg3.isInstalled = True
    pkg3.hasMismatched = True
    pkg3.isArchive = True
    pkg3.label = "pkg3"
    pkg3.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(3, pkg3)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 1, 1, False)
    _assert_add_node_view_command(
        viewCommandQueue, 3, view_commands.Style(
            checkboxState=True,
            iconId=view_commands.IconIds.INSTALLER_MISMATCHED),
        model.ROOT_NODE_ID, 2)

    pkg4 = node_attributes.PackageNodeAttributes()
    pkg4.isInstalled = True
    pkg4.hasMismatched = True
    pkg4.label = "pkg4"
    pkg4.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(4, pkg4)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 2, 2, False)
    _assert_add_node_view_command(
        viewCommandQueue, 4, view_commands.Style(
            checkboxState=True,
            iconId=view_commands.IconIds.PROJECT_MISMATCHED),
        model.ROOT_NODE_ID, 3)

    pkg5 = node_attributes.PackageNodeAttributes()
    pkg5.isInstalled = True
    pkg5.hasMismatched = True
    pkg5.isArchive = True
    pkg5.hasWizard = True
    pkg5.label = "pkg5"
    pkg5.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(5, pkg5)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 3, 3, False)
    _assert_add_node_view_command(
        viewCommandQueue, 5, view_commands.Style(
            checkboxState=True,
            iconId=view_commands.IconIds.INSTALLER_MISMATCHED_WIZ),
        model.ROOT_NODE_ID, 4)

    pkg6 = node_attributes.PackageNodeAttributes()
    pkg6.isInstalled = True
    pkg6.hasMismatched = True
    pkg6.hasWizard = True
    pkg6.label = "pkg6"
    pkg6.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(6, pkg6)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 4, 4, False)
    _assert_add_node_view_command(
        viewCommandQueue, 6, view_commands.Style(
            checkboxState=True,
            iconId=view_commands.IconIds.PROJECT_MISMATCHED_WIZ),
        model.ROOT_NODE_ID, 5)

    pkg7 = node_attributes.PackageNodeAttributes()
    pkg7.isInstalled = True
    pkg7.hasMissing = True
    pkg7.isArchive = True
    pkg7.label = "pkg7"
    pkg7.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(7, pkg7)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 5, 5, False)
    _assert_add_node_view_command(
        viewCommandQueue, 7, view_commands.Style(
            checkboxState=True,
            iconId=view_commands.IconIds.INSTALLER_MISSING),
        model.ROOT_NODE_ID, 6)

    pkg8 = node_attributes.PackageNodeAttributes()
    pkg8.isInstalled = True
    pkg8.hasMissing = True
    pkg8.label = "pkg8"
    pkg8.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(8, pkg8)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 6, 6, False)
    _assert_add_node_view_command(
        viewCommandQueue, 8, view_commands.Style(
            checkboxState=True,
            iconId=view_commands.IconIds.PROJECT_MISSING),
        model.ROOT_NODE_ID, 7)

    pkg9 = node_attributes.PackageNodeAttributes()
    pkg9.isInstalled = True
    pkg9.hasMissing = True
    pkg9.isArchive = True
    pkg9.hasWizard = True
    pkg9.label = "pkg9"
    pkg9.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(9, pkg9)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 7, 7, False)
    _assert_add_node_view_command(
        viewCommandQueue, 9, view_commands.Style(
            checkboxState=True,
            iconId=view_commands.IconIds.INSTALLER_MISSING_WIZ),
        model.ROOT_NODE_ID, 8)

    pkg10 = node_attributes.PackageNodeAttributes()
    pkg10.isInstalled = True
    pkg10.hasMissing = True
    pkg10.hasWizard = True
    pkg10.label = "pkg10"
    pkg10.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(10, pkg10)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 8, 8, False)
    _assert_add_node_view_command(
        viewCommandQueue, 10, view_commands.Style(
            checkboxState=True,
            iconId=view_commands.IconIds.PROJECT_MISSING_WIZ),
        model.ROOT_NODE_ID, 9)

    pkg11 = node_attributes.PackageNodeAttributes()
    pkg11.isInstalled = True
    pkg11.hasMatched = True
    pkg11.isArchive = True
    pkg11.label = "pkg11"
    pkg11.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(11, pkg11)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 9, 9, False)
    _assert_add_node_view_command(
        viewCommandQueue, 11, view_commands.Style(
            checkboxState=True,
            iconId=view_commands.IconIds.INSTALLER_MATCHES),
        model.ROOT_NODE_ID, 10)

    pkg12 = node_attributes.PackageNodeAttributes()
    pkg12.isInstalled = True
    pkg12.hasMatched = True
    pkg12.label = "pkg12"
    pkg12.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(12, pkg12)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 10, 10, False)
    _assert_add_node_view_command(
        viewCommandQueue, 12, view_commands.Style(
            checkboxState=True,
            iconId=view_commands.IconIds.PROJECT_MATCHES),
        model.ROOT_NODE_ID, 11)

    pkg13 = node_attributes.PackageNodeAttributes()
    pkg13.isInstalled = True
    pkg13.hasMatched = True
    pkg13.isArchive = True
    pkg13.hasWizard = True
    pkg13.label = "pkg13"
    pkg13.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(13, pkg13)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 11, 11, False)
    _assert_add_node_view_command(
        viewCommandQueue, 13, view_commands.Style(
            checkboxState=True,
            iconId=view_commands.IconIds.INSTALLER_MATCHES_WIZ),
        model.ROOT_NODE_ID, 12)

    pkg14 = node_attributes.PackageNodeAttributes()
    pkg14.isInstalled = True
    pkg14.hasMissingDeps = True
    pkg14.hasMatched = True
    pkg14.hasWizard = True
    pkg14.label = "pkg14"
    pkg14.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(14, pkg14)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 12, 12, False)
    _assert_add_node_view_command(
        viewCommandQueue, 14, view_commands.Style(
            fontStyleMask=view_commands.FontStyleIds.ITALICS,
            highlightColorId=view_commands.HighlightColorIds.MISSING_DEPENDENCY,
            checkboxState=True,
            iconId=view_commands.IconIds.PROJECT_MATCHES_WIZ),
        model.ROOT_NODE_ID, 13)

    pkg15 = node_attributes.PackageNodeAttributes()
    pkg15.isNotInstalled = True
    pkg15.isArchive = True
    pkg15.isDirty = True
    pkg15.label = "pkg15"
    pkg15.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(15, pkg15)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 3, 3, False)
    _assert_add_node_view_command(
        viewCommandQueue, 15, view_commands.Style(
            fontStyleMask=view_commands.FontStyleIds.ITALICS,
            highlightColorId=view_commands.HighlightColorIds.DIRTY,
            checkboxState=False,
            iconId=view_commands.IconIds.INSTALLER_EMPTY),
        model.ROOT_NODE_ID, 14)

    pkg16 = node_attributes.PackageNodeAttributes()
    pkg16.isNotInstalled = True
    pkg16.label = "pkg16"
    pkg16.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(16, pkg16)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 4, 4, False)
    _assert_add_node_view_command(
        viewCommandQueue, 16, view_commands.Style(
            checkboxState=False,
            iconId=view_commands.IconIds.PROJECT_EMPTY),
        model.ROOT_NODE_ID, 15)

    pkg17 = node_attributes.PackageNodeAttributes()
    pkg17.isNotInstalled = True
    pkg17.isArchive = True
    pkg17.hasWizard = True
    pkg17.label = "pkg17"
    pkg17.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(17, pkg17)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 5, 5, False)
    _assert_add_node_view_command(
        viewCommandQueue, 17, view_commands.Style(
            checkboxState=False,
            iconId=view_commands.IconIds.INSTALLER_EMPTY_WIZ),
        model.ROOT_NODE_ID, 16)

    pkg18 = node_attributes.PackageNodeAttributes()
    pkg18.isNotInstalled = True
    pkg18.hasSubpackages = True
    pkg18.hasWizard = True
    pkg18.label = "pkg18"
    pkg18.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(18, pkg18)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 6, 6, False)
    _assert_add_node_view_command(
        viewCommandQueue, 18, view_commands.Style(
            foregroundColorId=view_commands.ForegroundColorIds.HAS_SUBPACKAGES,
            checkboxState=False,
            iconId=view_commands.IconIds.PROJECT_EMPTY_WIZ),
        model.ROOT_NODE_ID, 17)

    _assert_load_requests(de.loadRequestQueue, {i:_CHILDREN for i in range(1,19)})


def test_packages_tree_diff_engine_errors():
    viewCommandQueue = Queue.Queue()
    dummyGeneralTabManager = _DummyManager()
    dummyPackageContentsManager = _DummyManager()

    de = diff_engine.PackagesTreeDiffEngine(
        dummyGeneralTabManager, dummyPackageContentsManager, viewCommandQueue)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, model.ROOT_NODE_ID)

    # enable all filters
    filterMask = presenter.FilterIds.PACKAGES_INSTALLED|\
               presenter.FilterIds.PACKAGES_NOT_INSTALLED|\
               presenter.FilterIds.PACKAGES_HIDDEN
    de.set_pending_filter_mask(filterMask)
    de.update_filter(filterMask)

    # define data
    de.update_children(model.ROOT_NODE_ID, node_children.NodeChildren([1]))
    _assert_load_request(de.loadRequestQueue, _ATTRIBUTES, 1)

    instPkg1 = node_attributes.PackageNodeAttributes()
    instPkg1.isInstalled = True
    instPkg1.label = "instPkg1"
    instPkg1.parentNodeId = model.ROOT_NODE_ID
    instPkg1.nodeType = None
    try:
        de.update_attributes(1, instPkg1)
        assert False
    except TypeError:
        pass


def test_packages_tree_diff_engine_node_updates():
    viewCommandQueue = Queue.Queue()
    dummyGeneralTabManager = _DummyManager()
    dummyPackageContentsManager = _DummyManager()

    de = diff_engine.PackagesTreeDiffEngine(
        dummyGeneralTabManager, dummyPackageContentsManager, viewCommandQueue)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, model.ROOT_NODE_ID)

    # define data
    de.update_children(model.ROOT_NODE_ID, node_children.NodeChildren([1,8,10,12]))
    _assert_load_requests(de.loadRequestQueue, {1:_ATTRIBUTES, 8:_ATTRIBUTES,
                                                10:_ATTRIBUTES, 12:_ATTRIBUTES})

    # populate groups
    allGroup = node_attributes.GroupNodeAttributes()
    allGroup.isInstalled = True
    allGroup.isNotInstalled = True
    allGroup.isHidden = True
    allGroup.label = "allGroup"
    allGroup.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(1, allGroup)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 1)
    de.update_children(1, node_children.NodeChildren([2,4,6]))
    _assert_load_requests(de.loadRequestQueue, {2:_ATTRIBUTES, 4:_ATTRIBUTES,
                                                6:_ATTRIBUTES})
    instGroup1 = node_attributes.GroupNodeAttributes()
    instGroup1.isInstalled = True
    instGroup1.label = "instGroup1"
    instGroup1.parentNodeId = 1
    de.update_attributes(2, instGroup1)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 2)
    uninstGroup1 = node_attributes.GroupNodeAttributes()
    uninstGroup1.isNotInstalled = True
    uninstGroup1.label = "uninstGroup1"
    uninstGroup1.parentNodeId = 1
    de.update_attributes(4, uninstGroup1)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 4)
    hiddenGroup1 = node_attributes.GroupNodeAttributes()
    hiddenGroup1.isHidden = True
    hiddenGroup1.label = "hiddenGroup1"
    hiddenGroup1.parentNodeId = 1
    de.update_attributes(6, hiddenGroup1)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 6)
    instGroup2 = node_attributes.GroupNodeAttributes()
    instGroup2.isInstalled = True
    instGroup2.label = "instGroup2"
    instGroup2.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(8, instGroup2)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 8)
    uninstGroup2 = node_attributes.GroupNodeAttributes()
    uninstGroup2.isNotInstalled = True
    uninstGroup2.label = "uninstGroup2"
    uninstGroup2.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(10, uninstGroup2)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 10)
    hiddenGroup2 = node_attributes.GroupNodeAttributes()
    hiddenGroup2.isHidden = True
    hiddenGroup2.label = "hiddenGroup2"
    hiddenGroup2.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(12, hiddenGroup2)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 12)
    de.update_children(2, node_children.NodeChildren([3]))
    _assert_load_request(de.loadRequestQueue, _ATTRIBUTES, 3)
    de.update_children(4, node_children.NodeChildren([5]))
    _assert_load_request(de.loadRequestQueue, _ATTRIBUTES, 5)
    de.update_children(6, node_children.NodeChildren([7]))
    _assert_load_request(de.loadRequestQueue, _ATTRIBUTES, 7)
    de.update_children(8, node_children.NodeChildren([9]))
    _assert_load_request(de.loadRequestQueue, _ATTRIBUTES, 9)
    de.update_children(10, node_children.NodeChildren([11]))
    _assert_load_request(de.loadRequestQueue, _ATTRIBUTES, 11)
    de.update_children(12, node_children.NodeChildren([13]))
    _assert_load_request(de.loadRequestQueue, _ATTRIBUTES, 13)
    assert viewCommandQueue.empty()

    # add packages
    instPkg1 = node_attributes.PackageNodeAttributes()
    instPkg1.isInstalled = True
    instPkg1.label = "instPkg1"
    instPkg1.parentNodeId = 2
    de.update_attributes(3, instPkg1)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 3)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 1, 1)
    uninstPkg1 = node_attributes.PackageNodeAttributes()
    uninstPkg1.isNotInstalled = True
    uninstPkg1.label = "uninstPkg1"
    uninstPkg1.parentNodeId = 4
    de.update_attributes(5, uninstPkg1)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 5)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 1, 1)
    hiddenPkg1 = node_attributes.PackageNodeAttributes()
    hiddenPkg1.isHidden = True
    hiddenPkg1.label = "hiddenPkg1"
    hiddenPkg1.parentNodeId = 6
    de.update_attributes(7, hiddenPkg1)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 7)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_HIDDEN, 1, 1)
    instPkg2 = node_attributes.PackageNodeAttributes()
    instPkg2.isInstalled = True
    instPkg2.label = "instPkg2"
    instPkg2.parentNodeId = 8
    de.update_attributes(9, instPkg2)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 9)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 2, 2)
    uninstPkg2 = node_attributes.PackageNodeAttributes()
    uninstPkg2.isNotInstalled = True
    uninstPkg2.label = "uninstPkg2"
    uninstPkg2.parentNodeId = 10
    de.update_attributes(11, uninstPkg2)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 11)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 2, 2)
    hiddenPkg2 = node_attributes.PackageNodeAttributes()
    hiddenPkg2.isHidden = True
    hiddenPkg2.label = "hiddenPkg2"
    hiddenPkg2.parentNodeId = 12
    de.update_attributes(13, hiddenPkg2)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 13)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_HIDDEN, 2, 2)

    # make everything visible
    filterMask = presenter.FilterIds.PACKAGES_INSTALLED|\
               presenter.FilterIds.PACKAGES_NOT_INSTALLED|\
               presenter.FilterIds.PACKAGES_HIDDEN
    de.set_pending_filter_mask(filterMask)
    de.update_filter(filterMask)
    _assert_view_commands(
        viewCommandQueue,
        {("n", 1):(view_commands.Style(),model.ROOT_NODE_ID,None),
         ("n", 2):(view_commands.Style(),1,None),
         ("n", 3):(view_commands.Style(
             checkboxState=True, iconId=view_commands.IconIds.PROJECT_EMPTY),
                   2,None),
         ("n", 4):(view_commands.Style(),1,2),
         ("n", 5):(view_commands.Style(
             checkboxState=False, iconId=view_commands.IconIds.PROJECT_EMPTY),
                   4,None),
         ("n", 6):(view_commands.Style(
            foregroundColorId=view_commands.ForegroundColorIds.DISABLED),
                   1,4),
         ("n", 7):(view_commands.Style(
            foregroundColorId=view_commands.ForegroundColorIds.DISABLED,
            iconId=view_commands.IconIds.PROJECT_EMPTY),
                   6,None),
         ("n", 8):(view_commands.Style(),model.ROOT_NODE_ID,None),
         ("n", 9):(view_commands.Style(
             checkboxState=True, iconId=view_commands.IconIds.PROJECT_EMPTY),
                   8,None),
         ("n", 10):(view_commands.Style(),model.ROOT_NODE_ID,8),
         ("n", 11):(view_commands.Style(
             checkboxState=False, iconId=view_commands.IconIds.PROJECT_EMPTY),
                   10,None),
         ("n", 12):(view_commands.Style(
            foregroundColorId=view_commands.ForegroundColorIds.DISABLED),
                   model.ROOT_NODE_ID,10),
         ("n", 13):(view_commands.Style(
            foregroundColorId=view_commands.ForegroundColorIds.DISABLED,
            iconId=view_commands.IconIds.PROJECT_EMPTY),
                   12,None)})

    # apply a search to single out uninstalled packages
    de.set_pending_search_string("uninst")
    de.update_search_string("uninst")
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(0,2),
         ("f", presenter.FilterIds.PACKAGES_HIDDEN):(0,2),
         ("n", 2):None, ("n", 6):None, ("n", 8):None, ("n", 12):None})

    # toggle filters with search active
    de.set_pending_filter_mask(presenter.FilterIds.NONE)
    de.update_filter(presenter.FilterIds.NONE)
    _assert_view_commands(
        viewCommandQueue,
        {("n", 1):None, ("n", 10):None})
    de.set_pending_filter_mask(filterMask)
    de.update_filter(filterMask)
    _assert_view_commands(
        viewCommandQueue,
        {("n", 1):(view_commands.Style(),model.ROOT_NODE_ID,None),
         ("n", 4):(view_commands.Style(),1,None),
         ("n", 5):(view_commands.Style(
             checkboxState=False, iconId=view_commands.IconIds.PROJECT_EMPTY),
                   4,None),
         ("n", 10):(view_commands.Style(),model.ROOT_NODE_ID,None),
         ("n", 11):(view_commands.Style(
             checkboxState=False, iconId=view_commands.IconIds.PROJECT_EMPTY),
                   10,None)})

    # hide hidden stuff
    filterMask = presenter.FilterIds.PACKAGES_INSTALLED|\
               presenter.FilterIds.PACKAGES_NOT_INSTALLED
    de.set_pending_filter_mask(filterMask)
    de.update_filter(filterMask)
    assert viewCommandQueue.empty()

    # update one of the uninstalled packages to hidden and back to uninstalled (package
    # first, then group)
    hiddenUninstPkg1 = node_attributes.PackageNodeAttributes()
    hiddenUninstPkg1.isHidden = True
    hiddenUninstPkg1.label = "hiddenUninstPkg1"
    hiddenUninstPkg1.parentNodeId = 4
    hiddenUninstPkg1.version = 1
    de.update_attributes(5, hiddenUninstPkg1)
    hiddenUninstGroup1 = node_attributes.GroupNodeAttributes()
    hiddenUninstGroup1.isHidden = True
    hiddenUninstGroup1.label = "hiddenUninstGroup1"
    hiddenUninstGroup1.parentNodeId = 1
    hiddenUninstGroup1.version = 1
    de.update_attributes(4, hiddenUninstGroup1)
    assert de.loadRequestQueue.empty()
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(1,1),
         ("f", presenter.FilterIds.PACKAGES_HIDDEN):(1,3),
         ("n", 1):None})

    revertedUninstPkg1 = node_attributes.PackageNodeAttributes()
    revertedUninstPkg1.isNotInstalled = True
    revertedUninstPkg1.label = "revertedUninstPkg1"
    revertedUninstPkg1.parentNodeId = 4
    revertedUninstPkg1.version = 2
    de.update_attributes(5, revertedUninstPkg1)
    assert de.loadRequestQueue.empty()
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(2,2),
         ("f", presenter.FilterIds.PACKAGES_HIDDEN):(0,2),
         ("n", 1):(view_commands.Style(),model.ROOT_NODE_ID,None),
         ("n", 4):(view_commands.Style(
             foregroundColorId=view_commands.ForegroundColorIds.DISABLED),1,None),
         ("n", 5):(view_commands.Style(
             checkboxState=False, iconId=view_commands.IconIds.PROJECT_EMPTY),
                   4,None)})
    revertedUninstGroup1 = node_attributes.GroupNodeAttributes()
    revertedUninstGroup1.isNotInstalled = True
    revertedUninstGroup1.label = "revertedUninstGroup1"
    revertedUninstGroup1.parentNodeId = 1
    revertedUninstGroup1.version = 2
    de.update_attributes(4, revertedUninstGroup1)
    assert de.loadRequestQueue.empty()
    _assert_add_node_view_command(viewCommandQueue, 4, view_commands.Style(), 1, None)

    # update one of the uninstalled packages to hidden and back to uninstalled (group
    # first, then package, simulating out-of-order processing due to multithreading)
    hiddenUninstGroup2 = node_attributes.GroupNodeAttributes()
    hiddenUninstGroup2.isHidden = True
    hiddenUninstGroup2.label = "hiddenUninstGroup2"
    hiddenUninstGroup2.parentNodeId = model.ROOT_NODE_ID
    hiddenUninstGroup2.version = 1
    de.update_attributes(10, hiddenUninstGroup2)
    _assert_add_node_view_command(viewCommandQueue, 10, view_commands.Style(
        foregroundColorId=view_commands.ForegroundColorIds.DISABLED), 0, 1)
    hiddenUninstPkg2 = node_attributes.PackageNodeAttributes()
    hiddenUninstPkg2.isHidden = True
    hiddenUninstPkg2.label = "hiddenUninstPkg2"
    hiddenUninstPkg2.parentNodeId = 10
    hiddenUninstPkg2.version = 1
    de.update_attributes(11, hiddenUninstPkg2)
    assert de.loadRequestQueue.empty()
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(1,1),
         ("f", presenter.FilterIds.PACKAGES_HIDDEN):(1,3),
         ("n", 10):None})

    revertedUninstGroup2 = node_attributes.GroupNodeAttributes()
    revertedUninstGroup2.isNotInstalled = True
    revertedUninstGroup2.label = "revertedUninstGroup2"
    revertedUninstGroup2.parentNodeId = model.ROOT_NODE_ID
    revertedUninstGroup2.version = 2
    de.update_attributes(10, revertedUninstGroup2)
    assert de.loadRequestQueue.empty()
    revertedUninstPkg2 = node_attributes.PackageNodeAttributes()
    revertedUninstPkg2.isNotInstalled = True
    revertedUninstPkg2.label = "revertedUninstPkg2"
    revertedUninstPkg2.parentNodeId = 10
    revertedUninstPkg2.version = 2
    de.update_attributes(11, revertedUninstPkg2)
    assert de.loadRequestQueue.empty()
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(2,2),
         ("f", presenter.FilterIds.PACKAGES_HIDDEN):(0,2),
         ("n", 10):(view_commands.Style(), model.ROOT_NODE_ID, 1),
         ("n", 11):(view_commands.Style(
             checkboxState=False, iconId=view_commands.IconIds.PROJECT_EMPTY),
                   10,None)})

    # change the label of an uninstalled package and its group so they no longer match
    # the search
    renamedUninstPkg1 = node_attributes.PackageNodeAttributes()
    renamedUninstPkg1.isNotInstalled = True
    renamedUninstPkg1.label = "renamedU instPkg1"
    renamedUninstPkg1.parentNodeId = 4
    renamedUninstPkg1.version = 3
    de.update_attributes(5, renamedUninstPkg1)
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(1,2),
         ("n", 5):(view_commands.Style(
             checkboxState=False, iconId=view_commands.IconIds.PROJECT_EMPTY),
                   4,None)})
    renamedUninstGroup1 = node_attributes.GroupNodeAttributes()
    renamedUninstGroup1.isNotInstalled = True
    renamedUninstGroup1.label = "renamedU instGroup1"
    renamedUninstGroup1.parentNodeId = 1
    renamedUninstGroup1.version = 3
    de.update_attributes(4, renamedUninstGroup1)
    assert de.loadRequestQueue.empty()
    _assert_view_commands(viewCommandQueue, {("n", 1):None})

    # remove allGroup tree
    rootChildren = node_children.NodeChildren([8,10,12])
    rootChildren.version = 1
    de.update_children(model.ROOT_NODE_ID, rootChildren)
    assert de.loadRequestQueue.empty()
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(0,1),
         ("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(1,1),
         ("f", presenter.FilterIds.PACKAGES_HIDDEN):(0,1)})


def test_packages_tree_diff_engine_deep_hierarchy():
    viewCommandQueue = Queue.Queue()
    dummyGeneralTabManager = _DummyManager()
    dummyPackageContentsManager = _DummyManager()

    de = diff_engine.PackagesTreeDiffEngine(
        dummyGeneralTabManager, dummyPackageContentsManager, viewCommandQueue)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, model.ROOT_NODE_ID)

    de.set_pending_filter_mask(presenter.FilterIds.PACKAGES_INSTALLED)
    de.update_filter(presenter.FilterIds.PACKAGES_INSTALLED)

    # define data
    # 1      instGroup - isInstalled, isHidden
    #   2    hiddenGroup - isHidden
    #     4  hiddenPkg - isHidden
    #     .. uninitialized
    #   3    instPkg - isInstalled
    de.update_children(model.ROOT_NODE_ID, node_children.NodeChildren([1]))
    _assert_load_requests(de.loadRequestQueue, {1:_ATTRIBUTES})

    # test searching on an uninitialized first node
    de.set_pending_search_string("inst")
    de.update_search_string("inst")
    de.set_pending_search_string(None)
    de.update_search_string(None)

    instGroup = node_attributes.GroupNodeAttributes()
    instGroup.isInstalled = True
    instGroup.isHidden = True
    instGroup.label = "instGroup"
    instGroup.parentNodeId = model.ROOT_NODE_ID
    de.update_attributes(1, instGroup)
    de.update_children(1, node_children.NodeChildren([2, 3]))
    _assert_load_requests(de.loadRequestQueue, {1:_CHILDREN,
                                                2:_ATTRIBUTES, 3:_ATTRIBUTES})

    hiddenGroup = node_attributes.GroupNodeAttributes()
    hiddenGroup.isHidden = True
    hiddenGroup.label = "hiddenGroup"
    hiddenGroup.parentNodeId = 1
    de.update_attributes(2, hiddenGroup)
    de.update_children(2, node_children.NodeChildren([4,5,6,7]))
    _assert_load_requests(de.loadRequestQueue, {2:_CHILDREN, 4:_ATTRIBUTES, 5:_ATTRIBUTES,
                                                6:_ATTRIBUTES, 7:_ATTRIBUTES})

    uninitGroup = node_attributes.GroupNodeAttributes()
    uninitGroup.label = "uninitGroup"
    uninitGroup.parentNodeId = 2
    de.update_attributes(6, hiddenGroup)
    de.update_children(6, node_children.NodeChildren([9,10]))
    _assert_load_requests(de.loadRequestQueue, {6:_CHILDREN,
                                                9:_ATTRIBUTES, 10:_ATTRIBUTES})

    instPkg = node_attributes.PackageNodeAttributes()
    instPkg.isInstalled = True
    instPkg.label = "instPkg"
    instPkg.parentNodeId = 1
    de.update_attributes(3, instPkg)
    _assert_load_requests(de.loadRequestQueue, {3:_CHILDREN})

    hiddenPkg = node_attributes.PackageNodeAttributes()
    hiddenPkg.isHidden = True
    hiddenPkg.label = "hiddenPkg"
    hiddenPkg.parentNodeId = 2
    de.update_attributes(4, hiddenPkg)
    _assert_load_requests(de.loadRequestQueue, {4:_CHILDREN})
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(1,1),
         ("f", presenter.FilterIds.PACKAGES_HIDDEN):(1,1),
         ("n", 1):(view_commands.Style(),model.ROOT_NODE_ID,None),
         ("n", 3):(view_commands.Style(
             checkboxState=True, iconId=view_commands.IconIds.PROJECT_EMPTY),
                   1,None)})

    # remove some uninitialized nodes
    updatedChildren = node_children.NodeChildren([4,5,7])
    updatedChildren.version = 1
    de.update_children(2, updatedChildren)
    assert de.loadRequestQueue.empty()
    assert viewCommandQueue.empty()

    # update nodes 1 and 3 so that they no longer match the filter
    updatedInstGroup = node_attributes.GroupNodeAttributes()
    updatedInstGroup.isNotInstalled = True
    updatedInstGroup.isHidden = True
    updatedInstGroup.label = "updatedInstGroup"
    updatedInstGroup.parentNodeId = model.ROOT_NODE_ID
    updatedInstGroup.version = 1
    de.update_attributes(1, updatedInstGroup)
    _assert_add_node_view_command(viewCommandQueue, 1, view_commands.Style(),
                                  model.ROOT_NODE_ID, None)
    updatedInstPkg = node_attributes.PackageNodeAttributes()
    updatedInstPkg.isNotInstalled = True
    updatedInstPkg.label = "updatedInstPkg"
    updatedInstPkg.parentNodeId = 1
    updatedInstPkg.version = 1
    de.update_attributes(3, updatedInstPkg)
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(0,0),
         ("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(1,1),
         ("n", 1):None})

    # change them back
    revertedInstPkg = node_attributes.PackageNodeAttributes()
    revertedInstPkg.isInstalled = True
    revertedInstPkg.label = "instPkg"
    revertedInstPkg.parentNodeId = 1
    revertedInstPkg.version = 2
    de.update_attributes(3, revertedInstPkg)
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(1,1),
         ("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(0,0),
         ("n", 1):(view_commands.Style(),model.ROOT_NODE_ID,None),
         ("n", 3):(view_commands.Style(
             checkboxState=True, iconId=view_commands.IconIds.PROJECT_EMPTY),
                   1,None)})
    revertedInstGroup = node_attributes.GroupNodeAttributes()
    revertedInstGroup.isInstalled = True
    revertedInstGroup.isHidden = True
    revertedInstGroup.label = "instGroup"
    revertedInstGroup.parentNodeId = model.ROOT_NODE_ID
    revertedInstGroup.version = 2
    de.update_attributes(1, revertedInstGroup)
    _assert_view_commands(
        viewCommandQueue,
        {("n", 1):(view_commands.Style(),model.ROOT_NODE_ID,None)})

    # add in a search that matches installed packages and test again
    de.set_pending_search_string("inst")
    de.update_search_string("inst")

    # make nodes 1 and 3 no longer match the filter but still match the search
    updatedInstGroup2 = node_attributes.GroupNodeAttributes()
    updatedInstGroup2.isNotInstalled = True
    updatedInstGroup2.isHidden = True
    updatedInstGroup2.label = "updatedInstGroup"
    updatedInstGroup2.parentNodeId = model.ROOT_NODE_ID
    updatedInstGroup2.version = 3
    de.update_attributes(1, updatedInstGroup2)
    _assert_add_node_view_command(viewCommandQueue, 1, view_commands.Style(),
                                  model.ROOT_NODE_ID, None)
    updatedInstPkg2 = node_attributes.PackageNodeAttributes()
    updatedInstPkg2.isNotInstalled = True
    updatedInstPkg2.label = "updatedInstPkg"
    updatedInstPkg2.parentNodeId = 1
    updatedInstPkg2.version = 3
    de.update_attributes(3, updatedInstPkg2)
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(0,0),
         ("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(1,1),
         ("n", 1):None})

    # change them back
    revertedInstGroup2 = node_attributes.GroupNodeAttributes()
    revertedInstGroup2.isInstalled = True
    revertedInstGroup2.isHidden = True
    revertedInstGroup2.label = "instGroup"
    revertedInstGroup2.parentNodeId = model.ROOT_NODE_ID
    revertedInstGroup2.version = 4
    de.update_attributes(1, revertedInstGroup2)
    revertedInstPkg2 = node_attributes.PackageNodeAttributes()
    revertedInstPkg2.isInstalled = True
    revertedInstPkg2.label = "instPkg"
    revertedInstPkg2.parentNodeId = 1
    revertedInstPkg2.version = 4
    de.update_attributes(3, revertedInstPkg2)
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(1,1),
         ("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(0,0),
         ("n", 1):(view_commands.Style(),model.ROOT_NODE_ID,None),
         ("n", 3):(view_commands.Style(
             checkboxState=True, iconId=view_commands.IconIds.PROJECT_EMPTY),
                   1,None)})

    # make node 1 no longer match the search
    updatedInstGroup3 = node_attributes.GroupNodeAttributes()
    updatedInstGroup3.isInstalled = True
    updatedInstGroup3.isHidden = True
    updatedInstGroup3.label = "In tGroup"
    updatedInstGroup3.parentNodeId = model.ROOT_NODE_ID
    updatedInstGroup3.version = 5
    de.update_attributes(1, updatedInstGroup3)
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_HIDDEN):(0,1),
         ("n", 1):(view_commands.Style(),model.ROOT_NODE_ID,None)})

    # change it back
    revertedInstGroup3 = node_attributes.GroupNodeAttributes()
    revertedInstGroup3.isInstalled = True
    revertedInstGroup3.isHidden = True
    revertedInstGroup3.label = "instGroup"
    revertedInstGroup3.parentNodeId = model.ROOT_NODE_ID
    revertedInstGroup3.version = 6
    de.update_attributes(1, revertedInstGroup3)
    _assert_view_commands(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_HIDDEN):(1,1),
         ("n", 1):(view_commands.Style(),model.ROOT_NODE_ID,None)})

    # match two subtrees independently (nothing should change externally)
    de.set_pending_search_string("instPkg|hiddenPkg")
    de.update_search_string("instPkg|hiddenPkg")
    assert viewCommandQueue.empty()


def test_diff_engine_internals():
    # test things that can only happen non-deterministically in a multithreaded env
    class DummyVisitor(diff_engine._Visitor):
        def __init__(self, n):
            self._n = n
        def visit(self, nodeId, nodeData):
            return True
        def false_after_n(self):
            if self._n < 0: return False
            self._n = self._n - 1
            return True
    tree = {}
    tree[0] = [False, None, None, node_children.NodeChildren([1,2,3])]
    tree[1] = [False, None, None, node_children.NodeChildren([4])]
    tree[2] = [False, None, None, node_children.NodeChildren([5,6])]
    tree[3] = [False, None, None]
    tree[4] = [False, None, None]
    tree[5] = [False, None, None]
    tree[6] = [False, None, None]

    visitor = DummyVisitor(3)
    diff_engine._visit_tree(0, tree, visitor.false_after_n, visitor)
