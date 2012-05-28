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


# useful when debugging tests
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


def _assert_group(inQueue, checkFn, isLastCommand=True):
    assert not inQueue.empty()
    for itemNum in xrange(inQueue.qsize()):
        item = inQueue.get(block=False)
        if not checkFn(item): break
    if isLastCommand:
        assert inQueue.empty()

def _assert_presenter(viewCommandQueue, commands,
                      optionalCommands=None, isLastCommand=True):
    """commands is a dict of ("f", filterId) -> (current, total) or
    ("a", nodeId) -> (nodeTreeId, label, isExpanded, style, parentNodeId,
    predecessorNodeId, contextMenuId, isSelected) or ("u", nodeId) -> (nodeTreeId, label,
    isExpanded, style) or ("r", nodeId) -> None.  they are accepted in any order.  the
    letter prefixes in the tuples are required to avoid hash collisions.  the second
    dictionary is for commands that may be issued, but are not required to be."""
    def pop(key):
        if key in commands:
            return commands.pop(key)
        if optionalCommands is None:
            raise KeyError(key)
        return optionalCommands.pop(key)
    def check_view_command(command):
        if command.commandId == presenter.CommandIds.SET_FILTER_STATS:
            filterId = command.filterId
            expectedUpdate = pop(("f", filterId))
            assert expectedUpdate[0] == command.current
            assert expectedUpdate[1] == command.total
        elif command.commandId == presenter.CommandIds.ADD_NODE:
            nodeId = command.nodeId
            expectedUpdate = pop(("a", nodeId))
            assert expectedUpdate[0] == command.nodeTreeId
            assert expectedUpdate[1] == command.label
            assert expectedUpdate[2] == command.isExpanded
            assert cmp(expectedUpdate[3], command.style)
            assert expectedUpdate[4] == command.parentNodeId
            assert expectedUpdate[5] == command.predecessorNodeId
            assert expectedUpdate[6] == command.contextMenuId
            assert expectedUpdate[7] == command.isSelected
        elif command.commandId == presenter.CommandIds.UPDATE_NODE:
            nodeId = command.nodeId
            expectedUpdate = pop(("u", nodeId))
            assert expectedUpdate[0] == command.nodeTreeId
            assert expectedUpdate[1] == command.label
            assert expectedUpdate[2] == command.isExpanded
            assert expectedUpdate[3] is command.style or \
                   cmp(expectedUpdate[3], command.style)
        elif command.commandId == presenter.CommandIds.REMOVE_NODE:
            nodeId = command.nodeId
            expectedUpdate = pop(("r", nodeId))
        else:
            # unhandled case
            raise NotImplementedError("unchecked viewCommand type")
        return 0 < len(commands)
    _assert_group(viewCommandQueue, check_view_command, isLastCommand)
    assert len(commands) == 0

def _assert_filter_view_command(viewCommandQueue, filterId, current, total,
                                isLastCommand=True):
    _assert_presenter(viewCommandQueue, {("f", filterId):(current, total)},
                      isLastCommand=isLastCommand)

def _assert_add_node_view_command(viewCommandQueue, nodeId, nodeTreeId, label, isExpanded,
                                  style, parentNodeId, predNodeId, contextMenuId,
                                  isSelected, isLastCommand=True):
    _assert_presenter(viewCommandQueue, {("a", nodeId):(nodeTreeId, label, isExpanded,
                                                        style, parentNodeId, predNodeId,
                                                        contextMenuId, isSelected)},
                      isLastCommand=isLastCommand)

def _assert_update_node_view_command(viewCommandQueue, nodeId, nodeTreeId, label=None,
                                     isExpanded=None, style=None, isLastCommand=True):
    _assert_presenter(viewCommandQueue,
                      {("u", nodeId):(nodeTreeId, label, isExpanded, style)},
                      isLastCommand=isLastCommand)

def _assert_remove_node_view_command(viewCommandQueue, nodeId, isLastCommand=True):
    _assert_presenter(viewCommandQueue, {("r", nodeId):None},
                      isLastCommand=isLastCommand)

def _assert_load_requests(loadRequestQueue, updates, isLastCommand=True):
    """updates is a dict of nodeId -> updateMask.  updates are accepted in any order"""
    def check_load_request(loadRequest):
        nodeId = loadRequest[diff_engine.NODE_ID_IDX]
        assert updates.pop(nodeId) == loadRequest[diff_engine.UPDATE_TYPE_MASK_IDX]
        return 0 < len(updates)
    _assert_group(loadRequestQueue, check_load_request, isLastCommand)
    assert len(updates) == 0

def _assert_load_request(loadRequestQueue, updateMask, nodeId, isLastCommand=True):
    _assert_load_requests(loadRequestQueue, {nodeId:updateMask}, isLastCommand)


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
    assert de.is_in_scope(_CHILDREN, model.NodeTypes.ROOT)
    assert de.could_use_update(_CHILDREN, model.ROOT_NODE_ID,
                               emptyRootNodeChildren.version)
    de.update_children(model.ROOT_NODE_ID, emptyRootNodeChildren)
    assert viewCommandQueue.empty()
    assert de.loadRequestQueue.empty()

    # test non-empty insert
    nonemptyRootNodeChildren = node_children.NodeChildren([1])
    nonemptyRootNodeChildren.version = emptyRootNodeChildren.version + 1
    assert de.is_in_scope(_CHILDREN, model.NodeTypes.ROOT)
    assert not de.could_use_update(_CHILDREN, model.ROOT_NODE_ID,
                                   emptyRootNodeChildren.version)
    assert de.could_use_update(_CHILDREN, model.ROOT_NODE_ID,
                               nonemptyRootNodeChildren.version)
    de.update_children(model.ROOT_NODE_ID, nonemptyRootNodeChildren)
    assert viewCommandQueue.empty()
    _assert_load_request(de.loadRequestQueue, _ATTRIBUTES, 1)

    # service load request
    packageNode = node_attributes.PackageNodeAttributes(
        "testPackage", model.ROOT_NODE_ID, hasMatched=True, hasWizard=True,
        hasSubpackages=True, isArchive=True, isInstalled=True, isNew=True,
        contextMenuId=presenter.ContextMenuIds.ARCHIVE)
    assert de.is_in_scope(_ATTRIBUTES, packageNode.nodeType)
    assert de.could_use_update(_ATTRIBUTES, 1, packageNode.version)
    de.update_attributes(1, packageNode)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 1)
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(1,1),
         ("a", 1):(presenter.NodeTreeIds.PACKAGES, "testPackage", False, presenter.Style(
             fontStyleMask=presenter.FontStyleIds.BOLD,
             foregroundColorId=presenter.ForegroundColorIds.HAS_SUBPACKAGES,
             checkboxState=True,
             iconId=presenter.IconIds.INSTALLER_MATCHES_WIZ), 0, None,
                   presenter.ContextMenuIds.ARCHIVE, False)})

    # ensure we can't go backwards
    de.update_children(model.ROOT_NODE_ID, emptyRootNodeChildren)
    de.update_attributes(1, packageNode)
    assert viewCommandQueue.empty()
    assert de.loadRequestQueue.empty()

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

    # check ordering rules
    try:
        de.update_children(2, node_children.NodeChildren())
        assert False
    except RuntimeError:
        pass

    installedGroup = node_attributes.GroupNodeAttributes(
        "instGroup", model.ROOT_NODE_ID, presenter.ContextMenuIds.GROUP, isDirty=True)
    de.update_attributes(2, installedGroup)
    assert viewCommandQueue.empty()
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 2)
    de.update_children(2, node_children.NodeChildren([3, 4, 5]))
    assert viewCommandQueue.empty()
    _assert_load_requests(de.loadRequestQueue, {3:_ATTRIBUTES, 4:_ATTRIBUTES,
                                                5:_ATTRIBUTES})
    instPkg1 = node_attributes.PackageNodeAttributes(
        "instPkg1", 2, presenter.ContextMenuIds.PROJECT, hasMismatched=True,
        isInstalled=True)
    instPkg2 = node_attributes.PackageNodeAttributes(
        "instPkg2", 2, presenter.ContextMenuIds.PROJECT, hasMismatched=True,
        isDirty=True, isInstalled=True)
    instPkg3 = node_attributes.PackageNodeAttributes(
        "instPkg3", 2, presenter.ContextMenuIds.PROJECT, hasMatched=True,
        isInstalled=True)
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

    uninstalledGroup = node_attributes.GroupNodeAttributes(
        "uninstalledGroup", model.ROOT_NODE_ID,
        contextMenuId=presenter.ContextMenuIds.GROUP)
    de.update_attributes(6, uninstalledGroup)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 6)
    de.update_children(6, node_children.NodeChildren([7, 8, 9]))
    assert viewCommandQueue.empty()
    _assert_load_requests(de.loadRequestQueue, {7:_ATTRIBUTES, 8:_ATTRIBUTES,
                                                9:_ATTRIBUTES})
    uninstPkg1 = node_attributes.PackageNodeAttributes(
        "uninstPkg1", 6, presenter.ContextMenuIds.PROJECT, hasMissing=True,
        isNotInstalled=True)
    uninstPkg2 = node_attributes.PackageNodeAttributes(
        "uninstPkg2", 6, presenter.ContextMenuIds.PROJECT, hasSubpackages=True,
        isNotInstalled=True)
    uninstPkg3 = node_attributes.PackageNodeAttributes(
        "uninstPkg3", 6, presenter.ContextMenuIds.PROJECT, hasMissing=True,
        isNotInstalled=True)
    # update children attributes in reverse order
    de.update_attributes(9, uninstPkg3)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 9)
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(1,1),
         ("a", 6):(presenter.NodeTreeIds.PACKAGES, "uninstalledGroup", False,
                   presenter.Style(), 0, None,
                   presenter.ContextMenuIds.GROUP, False),
         ("a", 9):(presenter.NodeTreeIds.PACKAGES, "uninstPkg3", False, presenter.Style(
             iconId=presenter.IconIds.PROJECT_MISSING,
             checkboxState=False), 6, None, presenter.ContextMenuIds.PROJECT, False)})
    de.update_attributes(8, uninstPkg2)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 8)
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(2,2),
         ("a", 8):(presenter.NodeTreeIds.PACKAGES, "uninstPkg2", False, presenter.Style(
             foregroundColorId=presenter.ForegroundColorIds.HAS_SUBPACKAGES,
             iconId=presenter.IconIds.PROJECT_EMPTY,
             checkboxState=False), 6, None, presenter.ContextMenuIds.PROJECT, False)})
    de.update_attributes(7, uninstPkg1)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 7)
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(3,3),
         ("a", 7):(presenter.NodeTreeIds.PACKAGES, "uninstPkg1", False, presenter.Style(
             iconId=presenter.IconIds.PROJECT_MISSING,
             checkboxState=False), 6, None, presenter.ContextMenuIds.PROJECT, False)})

    hiddenGroup = node_attributes.GroupNodeAttributes(
        "hiddenGroup", model.ROOT_NODE_ID, presenter.ContextMenuIds.GROUP)
    de.update_attributes(10, hiddenGroup)
    assert viewCommandQueue.empty()
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 10)
    de.update_children(10, node_children.NodeChildren([11, 12, 13]))
    assert viewCommandQueue.empty()
    _assert_load_requests(de.loadRequestQueue, {11:_ATTRIBUTES, 12:_ATTRIBUTES,
                                                13:_ATTRIBUTES})
    hiddenPkg1 = node_attributes.PackageNodeAttributes(
        "hiddenPkg1", 10, presenter.ContextMenuIds.PROJECT, isHidden=True)
    hiddenPkg2 = node_attributes.PackageNodeAttributes(
        "hiddenPkg2", 10, presenter.ContextMenuIds.PROJECT, isHidden=True)
    hiddenPkg3 = node_attributes.PackageNodeAttributes(
        "hiddenPkg3", 10, presenter.ContextMenuIds.PROJECT, isHidden=True)
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
    _assert_update_node_view_command(viewCommandQueue, 10, presenter.NodeTreeIds.PACKAGES,
                                     isExpanded=True)
    de.set_node_expansion(6, False)
    assert viewCommandQueue.empty()
    de.set_node_expansion(6, True)
    _assert_update_node_view_command(viewCommandQueue, 6, presenter.NodeTreeIds.PACKAGES,
                                     isExpanded=True)
    de.set_node_expansion(6, True)
    assert viewCommandQueue.empty()
    de.set_node_expansion(6, False)
    _assert_update_node_view_command(viewCommandQueue, 6, presenter.NodeTreeIds.PACKAGES,
                                     isExpanded=False)

    # enable more filters
    filterMask = presenter.FilterIds.PACKAGES_NOT_INSTALLED|\
               presenter.FilterIds.PACKAGES_HIDDEN
    de.set_pending_filter_mask(filterMask)
    de.update_filter(filterMask)
    assert de.loadRequestQueue.empty()
    _assert_add_node_view_command(
        viewCommandQueue, 10, presenter.NodeTreeIds.PACKAGES, "hiddenGroup", True,
        presenter.Style(foregroundColorId=presenter.ForegroundColorIds.DISABLED),
        model.ROOT_NODE_ID, 6, presenter.ContextMenuIds.GROUP, False, False)
    _assert_add_node_view_command(
        viewCommandQueue, 11, presenter.NodeTreeIds.PACKAGES, "hiddenPkg1", False,
        presenter.Style(foregroundColorId=presenter.ForegroundColorIds.DISABLED,
                        iconId=presenter.IconIds.PROJECT_EMPTY),
        10, None, presenter.ContextMenuIds.PROJECT, False, False)
    _assert_add_node_view_command(
        viewCommandQueue, 12, presenter.NodeTreeIds.PACKAGES, "hiddenPkg2", False,
        presenter.Style(foregroundColorId=presenter.ForegroundColorIds.DISABLED,
                        iconId=presenter.IconIds.PROJECT_EMPTY),
        10, 11, presenter.ContextMenuIds.PROJECT, False, False)
    _assert_add_node_view_command(
        viewCommandQueue, 13, presenter.NodeTreeIds.PACKAGES, "hiddenPkg3", False,
        presenter.Style(foregroundColorId=presenter.ForegroundColorIds.DISABLED,
                        iconId=presenter.IconIds.PROJECT_EMPTY),
        10, 12, presenter.ContextMenuIds.PROJECT, False, False)

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
    hiddenPkg4 = node_attributes.PackageNodeAttributes("hiddenPkg4", 10,
                                                       presenter.ContextMenuIds.PROJECT,
                                                       isHidden=True)
    de.update_attributes(14, hiddenPkg4)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 14)
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_HIDDEN):(4,4),
         ("a", 14):(presenter.NodeTreeIds.PACKAGES, "hiddenPkg4", False, presenter.Style(
             foregroundColorId=presenter.ForegroundColorIds.DISABLED,
             iconId=presenter.IconIds.PROJECT_EMPTY), 10, 13,
                    presenter.ContextMenuIds.PROJECT, False)})

    # add a matching package while the filter is active
    nodeChildren = node_children.NodeChildren([1,2,6,10,15])
    nodeChildren.version = 3
    de.update_children(model.ROOT_NODE_ID, nodeChildren)
    _assert_load_request(de.loadRequestQueue, _ATTRIBUTES, 15)
    hiddenPkg5 = node_attributes.PackageNodeAttributes("hiddenPkg5NotInAGroup",
                                                       model.ROOT_NODE_ID,
                                                       presenter.ContextMenuIds.PROJECT,
                                                       isHidden=True)
    de.update_attributes(15, hiddenPkg5)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 15)
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_HIDDEN):(5,5),
         ("a", 15):(presenter.NodeTreeIds.PACKAGES, "hiddenPkg5NotInAGroup", False,
                    presenter.Style(
             foregroundColorId=presenter.ForegroundColorIds.DISABLED,
             iconId=presenter.IconIds.PROJECT_EMPTY), model.ROOT_NODE_ID, 10,
                    presenter.ContextMenuIds.PROJECT, False)})
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
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(0,4),
         ("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(0,3),
         ("f", presenter.FilterIds.PACKAGES_HIDDEN):(1,5),
         ("r", 6):None, ("r", 11):None, ("r", 12):None, ("r", 14):None, ("r", 15):None},
        {("r", 8):None, ("r", 9):None})

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
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(3,4),
         ("f", presenter.FilterIds.PACKAGES_HIDDEN):(0,5),
         ("r", 10):None})
    filterMask = presenter.FilterIds.PACKAGES_INSTALLED|\
               presenter.FilterIds.PACKAGES_HIDDEN
    de.set_pending_filter_mask(filterMask)
    de.update_filter(filterMask)
    _assert_presenter(
        viewCommandQueue,
        {("a", 2):(presenter.NodeTreeIds.PACKAGES, "instGroup", False,
                   presenter.Style(
                       highlightColorId=presenter.HighlightColorIds.DIRTY,
                       fontStyleMask=presenter.FontStyleIds.ITALICS), model.ROOT_NODE_ID,
                   None, presenter.ContextMenuIds.GROUP, False),
         ("a", 3):(presenter.NodeTreeIds.PACKAGES, "instPkg1", False,
                   presenter.Style(iconId=presenter.IconIds.PROJECT_MISMATCHED,
                                   checkboxState=True), 2, None,
                   presenter.ContextMenuIds.PROJECT, False),
         ("a", 4):(presenter.NodeTreeIds.PACKAGES, "instPkg2", False,
                   presenter.Style(iconId=presenter.IconIds.PROJECT_MISMATCHED,
                                   checkboxState=True), 2, 3,
                   presenter.ContextMenuIds.PROJECT, False),
         ("a", 5):(presenter.NodeTreeIds.PACKAGES, "instPkg3", False,
                   presenter.Style(iconId=presenter.IconIds.PROJECT_MISMATCHED,
                                   checkboxState=True), 2, 4,
                   presenter.ContextMenuIds.PROJECT, False)})

    # update an existing group so that it now matches the search
    updatedHiddenGroup = node_attributes.GroupNodeAttributes(
        "hiddenInstGroup", model.ROOT_NODE_ID, presenter.ContextMenuIds.GROUP,
        version=1)
    de.update_attributes(10, updatedHiddenGroup)
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_HIDDEN):(4,5),
         ("a", 10):(presenter.NodeTreeIds.PACKAGES, "hiddenInstGroup", True,
                   presenter.Style(
                       foregroundColorId=presenter.ForegroundColorIds.DISABLED),
                   model.ROOT_NODE_ID, 2, presenter.ContextMenuIds.GROUP, False),

         ("a", 11):(presenter.NodeTreeIds.PACKAGES, "hiddenPkg1", False,
                   presenter.Style(
                       foregroundColorId=presenter.ForegroundColorIds.DISABLED,
                       iconId=presenter.IconIds.PROJECT_EMPTY), 10, None,
                   presenter.ContextMenuIds.PROJECT, False),
         ("a", 12):(presenter.NodeTreeIds.PACKAGES, "hiddenPkg2", False,
                   presenter.Style(
                       foregroundColorId=presenter.ForegroundColorIds.DISABLED,
                       iconId=presenter.IconIds.PROJECT_EMPTY), 10, 11,
                   presenter.ContextMenuIds.PROJECT, False),
         ("a", 13):(presenter.NodeTreeIds.PACKAGES, "hiddenPkg3", False,
                   presenter.Style(
                       foregroundColorId=presenter.ForegroundColorIds.DISABLED,
                       iconId=presenter.IconIds.PROJECT_EMPTY), 10, 12,
                   presenter.ContextMenuIds.PROJECT, False),
         ("a", 14):(presenter.NodeTreeIds.PACKAGES, "hiddenPkg4", False,
                   presenter.Style(
                       foregroundColorId=presenter.ForegroundColorIds.DISABLED,
                       iconId=presenter.IconIds.PROJECT_EMPTY), 10, 13,
                   presenter.ContextMenuIds.PROJECT, False)})

    # ensure stale search strings are not evaluated
    de.set_pending_search_string("hiddenPkg2")
    de.set_pending_search_string("hiddenPkg3")
    de.update_search_string("hiddenPkg2")
    assert viewCommandQueue.empty()
    de.update_search_string("hiddenPkg3")
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(0,4),
         ("f", presenter.FilterIds.PACKAGES_HIDDEN):(1,5),
         ("r", 2):None, ("r", 11):None, ("r", 12):None, ("r", 14):None},
        {("r", 4):None, ("r", 5):None})
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

    # delete everything
    finalRootNodeChildren = node_children.NodeChildren([])
    finalRootNodeChildren.version = 100
    de.update_children(model.ROOT_NODE_ID, finalRootNodeChildren)
    assert de.loadRequestQueue.empty()
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(0,0),
         ("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(0,0),
         ("f", presenter.FilterIds.PACKAGES_HIDDEN):(0,0),
         ("r", 10):None})


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

    pkg1 = node_attributes.PackageNodeAttributes(
        "pkg1", model.ROOT_NODE_ID, presenter.ContextMenuIds.ARCHIVE, isNotInstalled=True,
        isCorrupt=True, isNew=True, isArchive=True)
    de.update_attributes(1, pkg1)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 1, 1, False)
    _assert_add_node_view_command(
        viewCommandQueue, 1, presenter.NodeTreeIds.PACKAGES, "pkg1", False,
        presenter.Style(
            fontStyleMask=presenter.FontStyleIds.BOLD|\
            presenter.FontStyleIds.ITALICS,
            highlightColorId=presenter.HighlightColorIds.ERROR,
            checkboxState=False,
            iconId=presenter.IconIds.INSTALLER_UNINSTALLABLE), model.ROOT_NODE_ID, None,
        presenter.ContextMenuIds.ARCHIVE, False)

    pkg2 = node_attributes.PackageNodeAttributes(
        "pkg2", model.ROOT_NODE_ID, presenter.ContextMenuIds.PROJECT, isNotInstalled=True,
        isCorrupt=True)
    de.update_attributes(2, pkg2)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 2, 2, False)
    _assert_add_node_view_command(
        viewCommandQueue, 2, presenter.NodeTreeIds.PACKAGES, "pkg2", False,
        presenter.Style(
            fontStyleMask=presenter.FontStyleIds.ITALICS,
            highlightColorId=presenter.HighlightColorIds.ERROR,
            checkboxState=False,
            iconId=presenter.IconIds.PROJECT_UNINSTALLABLE), model.ROOT_NODE_ID, 1,
        presenter.ContextMenuIds.PROJECT, False)

    pkg3 = node_attributes.PackageNodeAttributes(
        "pkg3", model.ROOT_NODE_ID, presenter.ContextMenuIds.ARCHIVE, isInstalled=True,
        hasMismatched=True, isArchive=True)
    de.update_attributes(3, pkg3)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 1, 1, False)
    _assert_add_node_view_command(
        viewCommandQueue, 3, presenter.NodeTreeIds.PACKAGES, "pkg3", False,
        presenter.Style(checkboxState=True,
                        iconId=presenter.IconIds.INSTALLER_MISMATCHED),
        model.ROOT_NODE_ID, 2, presenter.ContextMenuIds.ARCHIVE, False)

    pkg4 = node_attributes.PackageNodeAttributes(
        "pkg4", model.ROOT_NODE_ID, presenter.ContextMenuIds.PROJECT, isInstalled=True,
        hasMismatched=True)
    de.update_attributes(4, pkg4)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 2, 2, False)
    _assert_add_node_view_command(
        viewCommandQueue, 4, presenter.NodeTreeIds.PACKAGES, "pkg4", False,
        presenter.Style(checkboxState=False,
                        iconId=presenter.IconIds.PROJECT_MISMATCHED),
        model.ROOT_NODE_ID, 3, presenter.ContextMenuIds.PROJECT, False)

    pkg5 = node_attributes.PackageNodeAttributes(
        "pkg5", model.ROOT_NODE_ID, presenter.ContextMenuIds.ARCHIVE, isInstalled=True,
        hasMismatched=True, isArchive=True, hasWizard=True)
    de.update_attributes(5, pkg5)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 3, 3, False)
    _assert_add_node_view_command(
        viewCommandQueue, 5, presenter.NodeTreeIds.PACKAGES, "pkg5", False,
        presenter.Style(checkboxState=True,
                        iconId=presenter.IconIds.INSTALLER_MISMATCHED_WIZ),
        model.ROOT_NODE_ID, 4, presenter.ContextMenuIds.ARCHIVE, False)

    pkg6 = node_attributes.PackageNodeAttributes(
        "pkg6", model.ROOT_NODE_ID, presenter.ContextMenuIds.PROJECT, isInstalled=True,
        hasMismatched=True, hasWizard=True)
    de.update_attributes(6, pkg6)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 4, 4, False)
    _assert_add_node_view_command(
        viewCommandQueue, 6, presenter.NodeTreeIds.PACKAGES, "pkg6", False,
        presenter.Style(checkboxState=True,
                        iconId=presenter.IconIds.PROJECT_MISMATCHED_WIZ),
        model.ROOT_NODE_ID, 5, presenter.ContextMenuIds.PROJECT, False)

    pkg7 = node_attributes.PackageNodeAttributes(
        "pkg7", model.ROOT_NODE_ID, presenter.ContextMenuIds.ARCHIVE, isInstalled=True,
        hasMissing=True, isArchive=True)
    de.update_attributes(7, pkg7)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 5, 5, False)
    _assert_add_node_view_command(
        viewCommandQueue, 7, presenter.NodeTreeIds.PACKAGES, "pkg7", False,
        presenter.Style(checkboxState=True,
                        iconId=presenter.IconIds.INSTALLER_MISSING),
        model.ROOT_NODE_ID, 6, presenter.ContextMenuIds.ARCHIVE, False)

    pkg8 = node_attributes.PackageNodeAttributes(
        "pkg8", model.ROOT_NODE_ID, presenter.ContextMenuIds.PROJECT, isInstalled=True,
        hasMissing=True)
    de.update_attributes(8, pkg8)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 6, 6, False)
    _assert_add_node_view_command(
        viewCommandQueue, 8, presenter.NodeTreeIds.PACKAGES, "pkg8", False,
        presenter.Style(checkboxState=True,
                        iconId=presenter.IconIds.PROJECT_MISSING),
        model.ROOT_NODE_ID, 7, presenter.ContextMenuIds.PROJECT, False)

    pkg9 = node_attributes.PackageNodeAttributes(
        "pkg9", model.ROOT_NODE_ID, presenter.ContextMenuIds.ARCHIVE, isInstalled=True,
        hasMissing=True, isArchive=True, hasWizard=True)
    de.update_attributes(9, pkg9)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 7, 7, False)
    _assert_add_node_view_command(
        viewCommandQueue, 9, presenter.NodeTreeIds.PACKAGES, "pkg9", False,
        presenter.Style(checkboxState=True,
                        iconId=presenter.IconIds.INSTALLER_MISSING_WIZ),
        model.ROOT_NODE_ID, 8, presenter.ContextMenuIds.ARCHIVE, False)

    pkg10 = node_attributes.PackageNodeAttributes(
        "pkg10", model.ROOT_NODE_ID, presenter.ContextMenuIds.PROJECT, isInstalled=True,
        hasMissing=True, hasWizard=True)
    de.update_attributes(10, pkg10)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 8, 8, False)
    _assert_add_node_view_command(
        viewCommandQueue, 10, presenter.NodeTreeIds.PACKAGES, "pkg10", False,
        presenter.Style(checkboxState=True,
                        iconId=presenter.IconIds.PROJECT_MISSING_WIZ),
        model.ROOT_NODE_ID, 9, presenter.ContextMenuIds.PROJECT, False)

    pkg11 = node_attributes.PackageNodeAttributes(
        "pkg11", model.ROOT_NODE_ID, presenter.ContextMenuIds.ARCHIVE, isInstalled=True,
        hasMatched=True, isArchive=True)
    de.update_attributes(11, pkg11)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 9, 9, False)
    _assert_add_node_view_command(
        viewCommandQueue, 11, presenter.NodeTreeIds.PACKAGES, "pkg11", False,
        presenter.Style(checkboxState=True,
                        iconId=presenter.IconIds.INSTALLER_MATCHES),
        model.ROOT_NODE_ID, 10, presenter.ContextMenuIds.ARCHIVE, False)

    pkg12 = node_attributes.PackageNodeAttributes(
        "pkg12", model.ROOT_NODE_ID, presenter.ContextMenuIds.PROJECT, isInstalled=True,
        hasMatched=True)
    de.update_attributes(12, pkg12)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 10, 10, False)
    _assert_add_node_view_command(
        viewCommandQueue, 12, presenter.NodeTreeIds.PACKAGES, "pkg12", False,
        presenter.Style(checkboxState=True,
                        iconId=presenter.IconIds.PROJECT_MATCHES),
        model.ROOT_NODE_ID, 11, presenter.ContextMenuIds.PROJECT, False)

    pkg13 = node_attributes.PackageNodeAttributes(
        "pkg13", model.ROOT_NODE_ID, presenter.ContextMenuIds.ARCHIVE, isInstalled=True,
        hasMatched=True, isArchive=True, hasWizard=True)
    de.update_attributes(13, pkg13)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 11, 11, False)
    _assert_add_node_view_command(
        viewCommandQueue, 13, presenter.NodeTreeIds.PACKAGES, "pkg13", False,
        presenter.Style(checkboxState=True,
                        iconId=presenter.IconIds.INSTALLER_MATCHES_WIZ),
        model.ROOT_NODE_ID, 12, presenter.ContextMenuIds.ARCHIVE, False)

    pkg14 = node_attributes.PackageNodeAttributes(
        "pkg14", model.ROOT_NODE_ID, presenter.ContextMenuIds.PROJECT, isInstalled=True,
        hasMissingDeps=True, hasMatched=True, hasWizard=True)
    de.update_attributes(14, pkg14)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 12, 12, False)
    _assert_add_node_view_command(
        viewCommandQueue, 14, presenter.NodeTreeIds.PACKAGES, "pkg14", False,
        presenter.Style(fontStyleMask=presenter.FontStyleIds.ITALICS,
                        highlightColorId=presenter.HighlightColorIds.MISSING_DEPENDENCY,
                        checkboxState=True,
                        iconId=presenter.IconIds.PROJECT_MATCHES_WIZ),
        model.ROOT_NODE_ID, 13, presenter.ContextMenuIds.PROJECT, False)

    pkg15 = node_attributes.PackageNodeAttributes(
        "pkg15", model.ROOT_NODE_ID, presenter.ContextMenuIds.ARCHIVE,
        isNotInstalled=True, isDirty=True, isArchive=True)
    de.update_attributes(15, pkg15)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 3, 3, False)
    _assert_add_node_view_command(
        viewCommandQueue, 15, presenter.NodeTreeIds.PACKAGES, "pkg15", False,
        presenter.Style(fontStyleMask=presenter.FontStyleIds.ITALICS,
                        highlightColorId=presenter.HighlightColorIds.DIRTY,
                        checkboxState=False,
                        iconId=presenter.IconIds.INSTALLER_EMPTY),
        model.ROOT_NODE_ID, 14, presenter.ContextMenuIds.ARCHIVE, False)

    pkg16 = node_attributes.PackageNodeAttributes(
        "pkg16", model.ROOT_NODE_ID, presenter.ContextMenuIds.PROJECT,
        isNotInstalled=True)
    de.update_attributes(16, pkg16)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 4, 4, False)
    _assert_add_node_view_command(
        viewCommandQueue, 16, presenter.NodeTreeIds.PACKAGES, "pkg16", False,
        presenter.Style(checkboxState=False,
                        iconId=presenter.IconIds.PROJECT_EMPTY),
        model.ROOT_NODE_ID, 15, presenter.ContextMenuIds.PROJECT, False)

    pkg17 = node_attributes.PackageNodeAttributes(
        "pkg17", model.ROOT_NODE_ID, presenter.ContextMenuIds.ARCHIVE,
        isNotInstalled=True, hasWizard=True, isArchive=True)
    de.update_attributes(17, pkg17)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 5, 5, False)
    _assert_add_node_view_command(
        viewCommandQueue, 17, presenter.NodeTreeIds.PACKAGES, "pkg17", False,
        presenter.Style(checkboxState=False,
                        iconId=presenter.IconIds.INSTALLER_EMPTY_WIZ),
        model.ROOT_NODE_ID, 16, presenter.ContextMenuIds.ARCHIVE, False)

    pkg18 = node_attributes.PackageNodeAttributes(
        "pkg18", model.ROOT_NODE_ID, presenter.ContextMenuIds.PROJECT,
        isNotInstalled=True, hasSubpackages=True, hasWizard=True)
    de.update_attributes(18, pkg18)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 6, 6, False)
    _assert_add_node_view_command(
        viewCommandQueue, 18, presenter.NodeTreeIds.PACKAGES, "pkg18", False,
        presenter.Style(foregroundColorId=presenter.ForegroundColorIds.HAS_SUBPACKAGES,
                        checkboxState=False,
                        iconId=presenter.IconIds.PROJECT_EMPTY_WIZ),
        model.ROOT_NODE_ID, 17, presenter.ContextMenuIds.PROJECT, False)

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

    instPkg1 = node_attributes.PackageNodeAttributes(
        "instPkg1", model.ROOT_NODE_ID, presenter.ContextMenuIds.PROJECT,
        isInstalled=True)
    instPkg1.nodeType = None
    try:
        diff_engine._get_style(instPkg1)
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
    allGroup = node_attributes.GroupNodeAttributes("allGroup", model.ROOT_NODE_ID,
                                                   presenter.ContextMenuIds.GROUP)
    de.update_attributes(1, allGroup)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 1)
    de.update_children(1, node_children.NodeChildren([2,4,6]))
    _assert_load_requests(de.loadRequestQueue, {2:_ATTRIBUTES, 4:_ATTRIBUTES,
                                                6:_ATTRIBUTES})
    instGroup1 = node_attributes.GroupNodeAttributes("instGroup1", 1,
                                                     presenter.ContextMenuIds.GROUP)
    de.update_attributes(2, instGroup1)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 2)
    uninstGroup1 = node_attributes.GroupNodeAttributes("uninstGroup1", 1,
                                                       presenter.ContextMenuIds.GROUP)
    de.update_attributes(4, uninstGroup1)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 4)
    hiddenGroup1 = node_attributes.GroupNodeAttributes("hiddenGroup1", 1,
                                                       presenter.ContextMenuIds.GROUP)
    de.update_attributes(6, hiddenGroup1)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 6)
    instGroup2 = node_attributes.GroupNodeAttributes("instGroup2", model.ROOT_NODE_ID,
                                                     presenter.ContextMenuIds.GROUP)
    de.update_attributes(8, instGroup2)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 8)
    uninstGroup2 = node_attributes.GroupNodeAttributes("uninstGroup2", model.ROOT_NODE_ID,
                                                       presenter.ContextMenuIds.GROUP)
    de.update_attributes(10, uninstGroup2)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 10)
    hiddenGroup2 = node_attributes.GroupNodeAttributes("hiddenGroup2", model.ROOT_NODE_ID,
                                                       presenter.ContextMenuIds.GROUP)
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
    instPkg1 = node_attributes.PackageNodeAttributes(
        "instPkg1", 2, presenter.ContextMenuIds.PROJECT, isInstalled=True)
    de.update_attributes(3, instPkg1)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 3)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 1, 1)
    uninstPkg1 = node_attributes.PackageNodeAttributes(
        "uninstPkg1", 4, presenter.ContextMenuIds.PROJECT, isNotInstalled=True)
    de.update_attributes(5, uninstPkg1)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 5)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 1, 1)
    hiddenPkg1 = node_attributes.PackageNodeAttributes(
        "hiddenPkg1", 6, presenter.ContextMenuIds.PROJECT, isHidden=True)
    de.update_attributes(7, hiddenPkg1)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 7)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_HIDDEN, 1, 1)
    instPkg2 = node_attributes.PackageNodeAttributes(
        "instPkg2", 8, presenter.ContextMenuIds.PROJECT, isInstalled=True)
    de.update_attributes(9, instPkg2)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 9)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_INSTALLED, 2, 2)
    uninstPkg2 = node_attributes.PackageNodeAttributes(
        "uninstPkg2", 10, presenter.ContextMenuIds.PROJECT, isNotInstalled=True)
    de.update_attributes(11, uninstPkg2)
    _assert_load_request(de.loadRequestQueue, _CHILDREN, 11)
    _assert_filter_view_command(
        viewCommandQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 2, 2)
    hiddenPkg2 = node_attributes.PackageNodeAttributes(
        "hiddenPkg2", 12, presenter.ContextMenuIds.PROJECT, isHidden=True)
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
    _assert_presenter(
        viewCommandQueue,
        {("a", 1):(presenter.NodeTreeIds.PACKAGES, "allGroup", False,
                   presenter.Style(),
                   model.ROOT_NODE_ID, None, presenter.ContextMenuIds.GROUP, False),
         ("a", 2):(presenter.NodeTreeIds.PACKAGES, "instGroup1", False,
                   presenter.Style(),
                   1, None, presenter.ContextMenuIds.GROUP, False),
         ("a", 3):(presenter.NodeTreeIds.PACKAGES, "instPkg1", False,
                   presenter.Style(
                       checkboxState=True, iconId=presenter.IconIds.PROJECT_EMPTY),
                   2, None, presenter.ContextMenuIds.PROJECT, False),
         ("a", 4):(presenter.NodeTreeIds.PACKAGES, "uninstGroup1", False,
                   presenter.Style(),
                   1, 2, presenter.ContextMenuIds.GROUP, False),
         ("a", 5):(presenter.NodeTreeIds.PACKAGES, "uninstPkg1", False,
                   presenter.Style(
                       checkboxState=False, iconId=presenter.IconIds.PROJECT_EMPTY),
                   4, None, presenter.ContextMenuIds.PROJECT, False),
         ("a", 6):(presenter.NodeTreeIds.PACKAGES, "hiddenGroup1", False,
                   presenter.Style(
                       foregroundColorId=presenter.ForegroundColorIds.DISABLED),
                   1, 4, presenter.ContextMenuIds.GROUP, False),
         ("a", 7):(presenter.NodeTreeIds.PACKAGES, "hiddenPkg1", False,
                   presenter.Style(
                       foregroundColorId=presenter.ForegroundColorIds.DISABLED,
                       iconId=presenter.IconIds.PROJECT_EMPTY),
                   6, None, presenter.ContextMenuIds.PROJECT, False),
         ("a", 8):(presenter.NodeTreeIds.PACKAGES, "instGroup2", False,
                   presenter.Style(),
                   model.ROOT_NODE_ID, None, presenter.ContextMenuIds.GROUP, False),
         ("a", 9):(presenter.NodeTreeIds.PACKAGES, "instPkg2", False,
                   presenter.Style(
                       checkboxState=True, iconId=presenter.IconIds.PROJECT_EMPTY),
                   8, None, presenter.ContextMenuIds.PROJECT, False),
         ("a", 10):(presenter.NodeTreeIds.PACKAGES, "uninstGroup2", False,
                    presenter.Style(),
                    model.ROOT_NODE_ID, 8, presenter.ContextMenuIds.GROUP, False),
         ("a", 11):(presenter.NodeTreeIds.PACKAGES, "uninstPkg2", False,
                    presenter.Style(
                        checkboxState=False, iconId=presenter.IconIds.PROJECT_EMPTY),
                    10, None, presenter.ContextMenuIds.PROJECT, False),
         ("a", 12):(presenter.NodeTreeIds.PACKAGES, "hiddenGroup2", False,
                    presenter.Style(
                        foregroundColorId=presenter.ForegroundColorIds.DISABLED),
                    model.ROOT_NODE_ID, 10, presenter.ContextMenuIds.GROUP, False),
         ("a", 13):(presenter.NodeTreeIds.PACKAGES, "hiddenPkg2", False,
                    presenter.Style(
                        foregroundColorId=presenter.ForegroundColorIds.DISABLED,
                        iconId=presenter.IconIds.PROJECT_EMPTY),
                    12, None, presenter.ContextMenuIds.PROJECT, False)})

    # apply a search to single out uninstalled packages
    de.set_pending_search_string("uninst")
    de.update_search_string("uninst")
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(0,2),
         ("f", presenter.FilterIds.PACKAGES_HIDDEN):(0,2),
         ("r", 2):None, ("r", 6):None, ("r", 8):None, ("r", 12):None})

    # toggle filters with search active
    de.set_pending_filter_mask(presenter.FilterIds.NONE)
    de.update_filter(presenter.FilterIds.NONE)
    _assert_presenter(
        viewCommandQueue,
        {("r", 1):None, ("r", 10):None})
    de.set_pending_filter_mask(filterMask)
    de.update_filter(filterMask)
    _assert_presenter(
        viewCommandQueue,
        {("a", 1):(presenter.NodeTreeIds.PACKAGES, "allGroup", False,
                   presenter.Style(),
                   model.ROOT_NODE_ID, None, presenter.ContextMenuIds.GROUP, False),
         ("a", 4):(presenter.NodeTreeIds.PACKAGES, "uninstGroup1", False,
                   presenter.Style(),
                   1, None, presenter.ContextMenuIds.GROUP, False),
         ("a", 5):(presenter.NodeTreeIds.PACKAGES, "uninstPkg1", False,
                   presenter.Style(
                       checkboxState=False, iconId=presenter.IconIds.PROJECT_EMPTY),
                   4, None, presenter.ContextMenuIds.PROJECT, False),
         ("a", 10):(presenter.NodeTreeIds.PACKAGES, "uninstGroup2", False,
                    presenter.Style(),
                    model.ROOT_NODE_ID, None, presenter.ContextMenuIds.GROUP, False),
         ("a", 11):(presenter.NodeTreeIds.PACKAGES, "uninstPkg2", False,
                    presenter.Style(
                        checkboxState=False, iconId=presenter.IconIds.PROJECT_EMPTY),
                    10, None, presenter.ContextMenuIds.PROJECT, False)})

    # hide hidden stuff
    filterMask = presenter.FilterIds.PACKAGES_INSTALLED|\
               presenter.FilterIds.PACKAGES_NOT_INSTALLED
    de.set_pending_filter_mask(filterMask)
    de.update_filter(filterMask)
    assert viewCommandQueue.empty()

    # update one of the uninstalled packages to hidden and back to uninstalled (package
    # first, then group)
    hiddenUninstPkg1 = node_attributes.PackageNodeAttributes(
        "hiddenUninstPkg1", 4, presenter.ContextMenuIds.PROJECT, isHidden=True, version=1)
    de.update_attributes(5, hiddenUninstPkg1)
    hiddenUninstGroup1 = node_attributes.GroupNodeAttributes(
        "hiddenUninstGroup1", 1, presenter.ContextMenuIds.GROUP, version=1)
    de.update_attributes(4, hiddenUninstGroup1)
    assert de.loadRequestQueue.empty()
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(1,1),
         ("f", presenter.FilterIds.PACKAGES_HIDDEN):(1,3),
         ("r", 1):None})

    revertedUninstPkg1 = node_attributes.PackageNodeAttributes(
        "revertedUninstPkg1", 4, presenter.ContextMenuIds.PROJECT, isNotInstalled=True,
        version=2)
    de.update_attributes(5, revertedUninstPkg1)
    assert de.loadRequestQueue.empty()
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(2,2),
         ("f", presenter.FilterIds.PACKAGES_HIDDEN):(0,2),
         ("a", 1):(presenter.NodeTreeIds.PACKAGES, "allGroup", False,
                   presenter.Style(),
                   model.ROOT_NODE_ID, None, presenter.ContextMenuIds.GROUP, False),
         ("a", 4):(presenter.NodeTreeIds.PACKAGES, "hiddenUninstGroup1", False,
                   presenter.Style(
                       foregroundColorId=presenter.ForegroundColorIds.DISABLED),
                   1, None, presenter.ContextMenuIds.GROUP, False),
         ("a", 5):(presenter.NodeTreeIds.PACKAGES, "revertedUninstPkg1", False,
                   presenter.Style(
                       checkboxState=False, iconId=presenter.IconIds.PROJECT_EMPTY),
                   4, None, presenter.ContextMenuIds.PROJECT, False)})
    revertedUninstGroup1 = node_attributes.GroupNodeAttributes(
        "revertedUninstGroup1", 1, presenter.ContextMenuIds.GROUP, version=2)
    de.update_attributes(4, revertedUninstGroup1)
    assert de.loadRequestQueue.empty()
    _assert_update_node_view_command(viewCommandQueue, 4, presenter.NodeTreeIds.PACKAGES,
                                     label="revertedUninstGroup1",
                                     style=presenter.Style())

    # update one of the uninstalled packages to hidden and back to uninstalled (group
    # first, then package, simulating out-of-order processing due to multithreading)
    hiddenUninstGroup2 = node_attributes.GroupNodeAttributes(
        "hiddenUninstGroup2", model.ROOT_NODE_ID, presenter.ContextMenuIds.GROUP,
        version=1)
    de.update_attributes(10, hiddenUninstGroup2)
    _assert_update_node_view_command(viewCommandQueue, 10, presenter.NodeTreeIds.PACKAGES,
                                     label="hiddenUninstGroup2", style=presenter.Style(
        foregroundColorId=presenter.ForegroundColorIds.DISABLED))
    hiddenUninstPkg2 = node_attributes.PackageNodeAttributes(
        "hiddenUninstPkg2", 10, presenter.ContextMenuIds.PROJECT, isHidden=True,
        version=1)
    de.update_attributes(11, hiddenUninstPkg2)
    assert de.loadRequestQueue.empty()
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(1,1),
         ("f", presenter.FilterIds.PACKAGES_HIDDEN):(1,3),
         ("r", 10):None})

    revertedUninstGroup2 = node_attributes.GroupNodeAttributes(
        "revertedUninstGroup2", model.ROOT_NODE_ID, presenter.ContextMenuIds.GROUP,
        version=2)
    de.update_attributes(10, revertedUninstGroup2)
    assert de.loadRequestQueue.empty()
    revertedUninstPkg2 = node_attributes.PackageNodeAttributes(
        "revertedUninstPkg2", 10, presenter.ContextMenuIds.PROJECT, isNotInstalled=True,
        version=2)
    de.update_attributes(11, revertedUninstPkg2)
    assert de.loadRequestQueue.empty()
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(2,2),
         ("f", presenter.FilterIds.PACKAGES_HIDDEN):(0,2),
         ("a", 10):(presenter.NodeTreeIds.PACKAGES, "revertedUninstGroup2", False,
                    presenter.Style(),
                    model.ROOT_NODE_ID, 1, presenter.ContextMenuIds.GROUP, False),
         ("a", 11):(presenter.NodeTreeIds.PACKAGES, "revertedUninstPkg2", False,
                    presenter.Style(
                        checkboxState=False, iconId=presenter.IconIds.PROJECT_EMPTY),
                    10, None, presenter.ContextMenuIds.PROJECT, False)})

    # change the label of an uninstalled package and its group so they no longer match
    # the search
    renamedUninstPkg1 = node_attributes.PackageNodeAttributes(
        "renamedU instPkg1", 4, presenter.ContextMenuIds.PROJECT, isNotInstalled=True,
        version=3)
    de.update_attributes(5, renamedUninstPkg1)
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(1,2),
         ("u", 5):(presenter.NodeTreeIds.PACKAGES, "renamedU instPkg1", None,
                   presenter.Style(
                       checkboxState=False, iconId=presenter.IconIds.PROJECT_EMPTY))})
    renamedUninstGroup1 = node_attributes.GroupNodeAttributes(
        "renamedU instGroup1", 1, presenter.ContextMenuIds.GROUP, version=3)
    de.update_attributes(4, renamedUninstGroup1)
    assert de.loadRequestQueue.empty()
    _assert_presenter(viewCommandQueue, {("r", 1):None})

    # remove allGroup tree
    rootChildren = node_children.NodeChildren([8,10,12])
    rootChildren.version = 1
    de.update_children(model.ROOT_NODE_ID, rootChildren)
    assert de.loadRequestQueue.empty()
    _assert_presenter(
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

    instGroup = node_attributes.GroupNodeAttributes(
        "instGroup", model.ROOT_NODE_ID, presenter.ContextMenuIds.GROUP)
    de.update_attributes(1, instGroup)
    de.update_children(1, node_children.NodeChildren([2, 3]))
    _assert_load_requests(de.loadRequestQueue, {1:_CHILDREN,
                                                2:_ATTRIBUTES, 3:_ATTRIBUTES})

    hiddenGroup = node_attributes.GroupNodeAttributes(
        "hiddenGroup", 1, presenter.ContextMenuIds.GROUP)
    de.update_attributes(2, hiddenGroup)
    de.update_children(2, node_children.NodeChildren([4,5,6,7]))
    _assert_load_requests(de.loadRequestQueue, {2:_CHILDREN, 4:_ATTRIBUTES, 5:_ATTRIBUTES,
                                                6:_ATTRIBUTES, 7:_ATTRIBUTES})

    uninitGroup = node_attributes.GroupNodeAttributes(
        "uninitGroup", 2, presenter.ContextMenuIds.GROUP)
    de.update_attributes(6, hiddenGroup)
    de.update_children(6, node_children.NodeChildren([9,10]))
    _assert_load_requests(de.loadRequestQueue, {6:_CHILDREN,
                                                9:_ATTRIBUTES, 10:_ATTRIBUTES})

    instPkg = node_attributes.PackageNodeAttributes(
        "instPkg", 1, presenter.ContextMenuIds.PROJECT, isInstalled=True)
    de.update_attributes(3, instPkg)
    _assert_load_requests(de.loadRequestQueue, {3:_CHILDREN})

    hiddenPkg = node_attributes.PackageNodeAttributes(
        "hiddenPkg", 2, presenter.ContextMenuIds.PROJECT, isHidden=True)
    de.update_attributes(4, hiddenPkg)
    _assert_load_requests(de.loadRequestQueue, {4:_CHILDREN})
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(1,1),
         ("f", presenter.FilterIds.PACKAGES_HIDDEN):(1,1),
         ("a", 1):(presenter.NodeTreeIds.PACKAGES, "instGroup", False,
                    presenter.Style(),
                    model.ROOT_NODE_ID, None, presenter.ContextMenuIds.GROUP, False),
         ("a", 3):(presenter.NodeTreeIds.PACKAGES, "instPkg", False,
                    presenter.Style(
                        checkboxState=True, iconId=presenter.IconIds.PROJECT_EMPTY),
                    1, None, presenter.ContextMenuIds.PROJECT, False)})

    # remove some uninitialized nodes
    updatedChildren = node_children.NodeChildren([4,5,7])
    updatedChildren.version = 1
    de.update_children(2, updatedChildren)
    assert de.loadRequestQueue.empty()
    assert viewCommandQueue.empty()

    # update nodes 1 and 3 so that they no longer match the filter
    updatedInstGroup = node_attributes.GroupNodeAttributes(
        "updatedInstGroup", model.ROOT_NODE_ID, presenter.ContextMenuIds.GROUP,
        version=1)
    de.update_attributes(1, updatedInstGroup)
    _assert_update_node_view_command(viewCommandQueue, 1, presenter.NodeTreeIds.PACKAGES,
                                     "updatedInstGroup", None, presenter.Style())
    updatedInstPkg = node_attributes.PackageNodeAttributes(
        "updatedInstPkg", 1, presenter.ContextMenuIds.PROJECT, isNotInstalled=True,
        version=1)
    de.update_attributes(3, updatedInstPkg)
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(0,0),
         ("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(1,1),
         ("r", 1):None})

    # change them back
    revertedInstPkg = node_attributes.PackageNodeAttributes(
        "instPkg", 1, presenter.ContextMenuIds.PROJECT, isInstalled=True, version=2)
    de.update_attributes(3, revertedInstPkg)
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(1,1),
         ("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(0,0),
         ("a", 1):(presenter.NodeTreeIds.PACKAGES, "updatedInstGroup", False,
                    presenter.Style(),
                    model.ROOT_NODE_ID, None, presenter.ContextMenuIds.GROUP, False),
         ("a", 3):(presenter.NodeTreeIds.PACKAGES, "instPkg", False,
                    presenter.Style(
                        checkboxState=True, iconId=presenter.IconIds.PROJECT_EMPTY),
                    1, None, presenter.ContextMenuIds.PROJECT, False)})
    revertedInstGroup = node_attributes.GroupNodeAttributes(
        "instGroup", model.ROOT_NODE_ID, presenter.ContextMenuIds.GROUP, version=2)
    de.update_attributes(1, revertedInstGroup)
    _assert_presenter(
        viewCommandQueue,
        {("u", 1):(presenter.NodeTreeIds.PACKAGES, "instGroup", None, presenter.Style())})

    # add in a search that matches installed packages and test again
    de.set_pending_search_string("inst")
    de.update_search_string("inst")

    # make nodes 1 and 3 no longer match the filter but still match the search
    updatedInstGroup2 = node_attributes.GroupNodeAttributes(
        "updatedInstGroup", model.ROOT_NODE_ID, presenter.ContextMenuIds.GROUP, version=3)
    de.update_attributes(1, updatedInstGroup2)
    _assert_update_node_view_command(viewCommandQueue, 1, presenter.NodeTreeIds.PACKAGES,
                                     "updatedInstGroup", None, presenter.Style())
    updatedInstPkg2 = node_attributes.PackageNodeAttributes(
        "updatedInstPkg", 1, presenter.ContextMenuIds.PROJECT, isNotInstalled=True,
        version=3)
    de.update_attributes(3, updatedInstPkg2)
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(0,0),
         ("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(1,1),
         ("r", 1):None})

    # change them back
    revertedInstGroup2 = node_attributes.GroupNodeAttributes(
        "instGroup", model.ROOT_NODE_ID, presenter.ContextMenuIds.GROUP, version=4)
    de.update_attributes(1, revertedInstGroup2)
    revertedInstPkg2 = node_attributes.PackageNodeAttributes(
        "instPkg", 1, presenter.ContextMenuIds.PROJECT, isInstalled=True, version=4)
    de.update_attributes(3, revertedInstPkg2)
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_INSTALLED):(1,1),
         ("f", presenter.FilterIds.PACKAGES_NOT_INSTALLED):(0,0),
         ("a", 1):(presenter.NodeTreeIds.PACKAGES, "instGroup", False,
                    presenter.Style(),
                    model.ROOT_NODE_ID, None, presenter.ContextMenuIds.GROUP, False),
         ("a", 3):(presenter.NodeTreeIds.PACKAGES, "instPkg", False,
                    presenter.Style(
                        checkboxState=True, iconId=presenter.IconIds.PROJECT_EMPTY),
                    1, None, presenter.ContextMenuIds.PROJECT, False)})

    # make node 1 no longer match the search
    updatedInstGroup3 = node_attributes.GroupNodeAttributes(
        "In tGroup", model.ROOT_NODE_ID, presenter.ContextMenuIds.GROUP, version=5)
    de.update_attributes(1, updatedInstGroup3)
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_HIDDEN):(0,1),
         ("u", 1):(presenter.NodeTreeIds.PACKAGES, "In tGroup", None, presenter.Style())})

    # change it back
    revertedInstGroup3 = node_attributes.GroupNodeAttributes(
        "instGroup", model.ROOT_NODE_ID, presenter.ContextMenuIds.GROUP, version=6)
    de.update_attributes(1, revertedInstGroup3)
    _assert_presenter(
        viewCommandQueue,
        {("f", presenter.FilterIds.PACKAGES_HIDDEN):(1,1),
         ("u", 1):(presenter.NodeTreeIds.PACKAGES, "instGroup", None, presenter.Style())})

    # match two subtrees independently (nothing should change externally)
    de.set_pending_search_string("instPkg|hiddenPkg")
    de.update_search_string("instPkg|hiddenPkg")
    assert viewCommandQueue.empty()

    # test what happens when a new search string comes in while we're still searching
    class UnstableString:
        def __init__(self, val, val2, n):
            self._val = val
            self._val2 = val2
            self._n = n
        def __get_val(self):
            if self._n <= 0: return self._val2
            self._n = self._n - 1
            return self._val
        def __cmp__(self, other):
            return cmp(self.__get_val(), other)
        def __str__(self):
            return self.__get_val()
        def __len__(self):
            return len(self.__get_val())
        def __hash__(self):
            return hash(self.__get_val())

    s = UnstableString("s1", "s2", 1)
    de.set_pending_search_string(s)
    de.update_search_string("s1")
    assert viewCommandQueue.empty()

    # ensure nothing happens when an ancestor and descendant group both match the search,
    # but then the descendant is updated to not match the search.  The children of the
    # descendant should still be shown
    filterMask = presenter.FilterIds.PACKAGES_INSTALLED|\
               presenter.FilterIds.PACKAGES_NOT_INSTALLED|\
               presenter.FilterIds.PACKAGES_HIDDEN
    de.set_pending_filter_mask(filterMask)
    de.update_filter(filterMask)
    _assert_presenter(
        viewCommandQueue,
        {("a", 2):(presenter.NodeTreeIds.PACKAGES, "hiddenGroup", False,
                    presenter.Style(
                        foregroundColorId=presenter.ForegroundColorIds.DISABLED),
                    1, None, presenter.ContextMenuIds.GROUP, False),
         ("a", 4):(presenter.NodeTreeIds.PACKAGES, "hiddenPkg", False,
                    presenter.Style(
                        foregroundColorId=presenter.ForegroundColorIds.DISABLED,
                        iconId=presenter.IconIds.PROJECT_EMPTY),
                    2, None, presenter.ContextMenuIds.PROJECT, False)})
    de.set_pending_search_string("group")
    de.update_search_string("group")

    # make node 2 no longer match the search
    updatedHiddenGroup = node_attributes.GroupNodeAttributes(
        "hiddenGr up", 1, presenter.ContextMenuIds.GROUP, version=2)
    de.update_attributes(2, updatedHiddenGroup)
    _assert_update_node_view_command(viewCommandQueue, 2, presenter.NodeTreeIds.PACKAGES,
                                     label="hiddenGr up", style=presenter.Style(
        foregroundColorId=presenter.ForegroundColorIds.DISABLED))
    assert de.loadRequestQueue.empty()

    # change it back
    revertedHiddenGroup = node_attributes.GroupNodeAttributes(
        "hiddenGroup", 1, presenter.ContextMenuIds.GROUP, version=3)
    de.update_attributes(2, revertedHiddenGroup)
    _assert_update_node_view_command(viewCommandQueue, 2, presenter.NodeTreeIds.PACKAGES,
                                     label="hiddenGroup", style=presenter.Style(
        foregroundColorId=presenter.ForegroundColorIds.DISABLED))
    assert de.loadRequestQueue.empty()


def test_diff_engine_internals():
    # test things that can only happen non-deterministically in a multithreaded env
    class DummyVisitor(diff_engine._Visitor):
        def __init__(self, n):
            self._n = n
        def visit(self, nodeId, nodeData):
            return True
        def false_after_n(self):
            if self._n <= 0: return False
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

    de = diff_engine._DiffEngine(0, None, None, None)
    try:
        de.is_in_scope(None, None)
        assert False
    except NotImplementedError:
        pass

    try:
        de.could_use_update(None, None, None)
        assert False
    except NotImplementedError:
        pass