# -*- coding: utf-8 -*-
#
# bait/presenter/impl/diff_engine.py
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
import re

from . import filters
from ... import model
from ...model import node_attributes
from ... import presenter


UPDATE_TYPE_MASK_IDX = 0
NODE_ID_IDX = 1

_logger = logging.getLogger(__name__)

_MATCHES_SEARCH_IDX = 0
_PRED_NODE_ID_IDX = 1
_ATTRIBUTES_IDX = 2
_CHILDREN_IDX = 3


def _visit_tree(rootNodeId, tree, quitEarlyIfFalseFn, visitor):
    # walk the tree breadth first starting from the children of the specified node
    childNodeIds = Queue.Queue()
    rootNodeData = tree[rootNodeId]
    # seed childeNodeIds queue
    if len(rootNodeData) > _CHILDREN_IDX:
        for childNodeId in rootNodeData[_CHILDREN_IDX].children:
            childNodeIds.put(childNodeId)
    # run start hook
    visitor.start_hook()
    while not childNodeIds.empty():
        if quitEarlyIfFalseFn and not quitEarlyIfFalseFn():
            _logger.debug("halting tree walk: early quit condition raised")
            break
        nodeId = childNodeIds.get()
        nodeData = tree[nodeId]
        if not visitor.visit(nodeId, nodeData):
            _logger.debug("visitor returned False at node %d, skipping children", nodeId)
            continue
        # if this node has children, add them to the processing queue
        if len(nodeData) > _CHILDREN_IDX:
            for childNodeId in nodeData[_CHILDREN_IDX].children:
                childNodeIds.put(childNodeId)
    # run end hook
    visitor.end_hook()

def _get_package_icon_id(packageNodeAttributes):
    if packageNodeAttributes.isCorrupt:
        if packageNodeAttributes.isArchive:
            return presenter.IconIds.INSTALLER_UNINSTALLABLE
        else:
            return presenter.IconIds.PROJECT_UNINSTALLABLE
    if packageNodeAttributes.hasMismatched:
        if packageNodeAttributes.isArchive:
            if packageNodeAttributes.hasWizard:
                return presenter.IconIds.INSTALLER_MISMATCHED_WIZ
            else:
                return presenter.IconIds.INSTALLER_MISMATCHED
        else:
            if packageNodeAttributes.hasWizard:
                return presenter.IconIds.PROJECT_MISMATCHED_WIZ
            else:
                return presenter.IconIds.PROJECT_MISMATCHED
    if packageNodeAttributes.hasMissing:
        if packageNodeAttributes.isArchive:
            if packageNodeAttributes.hasWizard:
                return presenter.IconIds.INSTALLER_MISSING_WIZ
            else:
                return presenter.IconIds.INSTALLER_MISSING
        else:
            if packageNodeAttributes.hasWizard:
                return presenter.IconIds.PROJECT_MISSING_WIZ
            else:
                return presenter.IconIds.PROJECT_MISSING
    if packageNodeAttributes.hasMatched:
        if packageNodeAttributes.isArchive:
            if packageNodeAttributes.hasWizard:
                return presenter.IconIds.INSTALLER_MATCHES_WIZ
            else:
                return presenter.IconIds.INSTALLER_MATCHES
        else:
            if packageNodeAttributes.hasWizard:
                return presenter.IconIds.PROJECT_MATCHES_WIZ
            else:
                return presenter.IconIds.PROJECT_MATCHES
    # has no other attributes; must be empty
    if packageNodeAttributes.isArchive:
        if packageNodeAttributes.hasWizard:
            return presenter.IconIds.INSTALLER_EMPTY_WIZ
        else:
            return presenter.IconIds.INSTALLER_EMPTY
    else:
        if packageNodeAttributes.hasWizard:
            return presenter.IconIds.PROJECT_EMPTY_WIZ
        else:
            return presenter.IconIds.PROJECT_EMPTY

def _get_font_style_mask(treeNodeAttributes):
    fontStyleMask = presenter.FontStyleIds.NONE
    if treeNodeAttributes.isNew:
        fontStyleMask |= presenter.FontStyleIds.BOLD
    if treeNodeAttributes.isCorrupt | treeNodeAttributes.isDirty | \
       treeNodeAttributes.isUnrecognized | treeNodeAttributes.hasMissingDeps | \
       treeNodeAttributes.updateAvailable:
        fontStyleMask |= presenter.FontStyleIds.ITALICS
    return fontStyleMask

def _get_foreground_color(treeNodeAttributes):
    if treeNodeAttributes.isHidden and \
       not treeNodeAttributes.isInstalled and not treeNodeAttributes.isNotInstalled:
        return presenter.ForegroundColorIds.DISABLED
    if getattr(treeNodeAttributes, "hasSubpackages", False):
        return presenter.ForegroundColorIds.HAS_SUBPACKAGES
    return None

def _get_highlight_color(treeNodeAttributes):
    if treeNodeAttributes.isCorrupt | treeNodeAttributes.isUnrecognized:
        return presenter.HighlightColorIds.ERROR
    if treeNodeAttributes.hasMissingDeps:
        return presenter.HighlightColorIds.MISSING_DEPENDENCY
    if treeNodeAttributes.isDirty:
        return presenter.HighlightColorIds.DIRTY
    return None

def _get_style(nodeAttributes):
    # craft visual style
    style = presenter.Style(_get_font_style_mask(nodeAttributes),
                            _get_foreground_color(nodeAttributes),
                            _get_highlight_color(nodeAttributes))
    if nodeAttributes.nodeType == model.NodeTypes.PACKAGE:
        # craft package-specific style elements
        style.checkboxState = nodeAttributes.isInstalled
        style.iconId = _get_package_icon_id(nodeAttributes)
    elif nodeAttributes.nodeType == model.NodeTypes.GROUP:
        # no additional attributes
        pass
    # TODO: package contents tree nodes
    else:
        raise TypeError(
            "unexpected node type: %s" % nodeAttributes.nodeType)
    return style

def _get_visible_predecessor(nodeData, tree, visibleLeafNodeIds, visibleBranchNodeIds):
    # walk the tree backwards to find a visible predecessor
    predNodeId = nodeData[_PRED_NODE_ID_IDX]
    while predNodeId is not None:
        if predNodeId in visibleLeafNodeIds or predNodeId in visibleBranchNodeIds:
            break
        predNodeId = tree[predNodeId][_PRED_NODE_ID_IDX]
    return predNodeId

def _add_node(nodeId, nodeData, tree, visibleLeafNodeIds, visibleBranchNodeIds,
              expandedNodeIds, selectedNodeIds, viewCommandQueue, nodeTreeId, rootNodeId):
    """adds given node and any required ancestors"""
    # show parentage if not already visible
    nodeAttributes = nodeData[_ATTRIBUTES_IDX]
    parentNodeId = nodeAttributes.parentNodeId
    if parentNodeId not in visibleBranchNodeIds:
        _logger.debug(
            "showing node %d due to it being upstream from newly visible node %d",
            parentNodeId, nodeId)
        _add_node(parentNodeId, tree[parentNodeId], tree, visibleLeafNodeIds,
                  visibleBranchNodeIds, expandedNodeIds, selectedNodeIds,
                  viewCommandQueue, nodeTreeId, rootNodeId)
        visibleBranchNodeIds.add(parentNodeId)
    predNodeId = _get_visible_predecessor(nodeData, tree, visibleLeafNodeIds,
                                          visibleBranchNodeIds)
    # craft visual style
    style = _get_style(nodeAttributes)
    isExpanded = nodeId in expandedNodeIds
    isSelected = nodeId in selectedNodeIds
    if parentNodeId == rootNodeId:
        parentNodeId = None
    _logger.debug("enqueuing command to add node %d: '%s'", nodeId, nodeAttributes.label)
    viewCommandQueue.put(presenter.AddNodeCommand(
        nodeTreeId, nodeId, nodeAttributes.label, isExpanded, style, parentNodeId,
        predNodeId, nodeAttributes.contextMenuId, isSelected))

def _update_node(nodeId, nodeData, viewCommandQueue, nodeTreeId):
    """updates given node"""
    nodeAttributes = nodeData[_ATTRIBUTES_IDX]
    _logger.debug("updating node %d: '%s'", nodeId, nodeAttributes.label)
    # craft visual style
    style = _get_style(nodeAttributes)
    # TODO: only send changed attributes
    viewCommandQueue.put(presenter.UpdateNodeCommand(
        nodeTreeId, nodeId, label=nodeAttributes.label, style=style))

def _remove_branch(nodeId, nodeData, tree, visibleLeafNodeIds, visibleBranchNodeIds,
                   rootNodeId, viewCommandQueue):
    """removes given node, all descendants, and any empty ancestors"""
    branchRootNodeIdToRemove = nodeId
    parentNodeId = nodeData[_ATTRIBUTES_IDX].parentNodeId
    while parentNodeId is not rootNodeId and parentNodeId in visibleBranchNodeIds:
        parentNodeData = tree[parentNodeId]
        hasVisibleChildren = False
        # is upstream, so must have children
        for childNodeId in parentNodeData[_CHILDREN_IDX].children:
            if childNodeId in visibleLeafNodeIds or childNodeId in visibleBranchNodeIds:
                _logger.debug("found visible relation node %d; not removing ancestor %d",
                              childNodeId, parentNodeId)
                hasVisibleChildren = True
                break
        if not hasVisibleChildren:
            _logger.debug("removing node %d from visible branch set", parentNodeId)
            visibleBranchNodeIds.discard(parentNodeId)
            branchRootNodeIdToRemove = parentNodeId
        else:
            break
        parentNodeId = parentNodeData[_ATTRIBUTES_IDX].parentNodeId
    _logger.debug("removing tree rooted at node %d", branchRootNodeIdToRemove)
    viewCommandQueue.put(presenter.RemoveNodeCommand(
        presenter.NodeTreeIds.PACKAGES, branchRootNodeIdToRemove))

def _filter_and_sync(nodeId, nodeData, tree, searchMatchesLineage, filter_,
                     visibleBranchNodeIds, expandedNodeIds, selectedNodeIds, rootNodeId,
                     viewCommandQueue, nodeTreeId, updateIfNoVisibilityChange):
    attributes = nodeData[_ATTRIBUTES_IDX]
    wasVisible = nodeId in filter_.visibleNodeIds
    isVisible = filter_.process_and_get_visibility(
        nodeId, attributes, searchMatchesLineage or nodeData[_MATCHES_SEARCH_IDX])
    if isVisible:
        if wasVisible:
            if not updateIfNoVisibilityChange:
                return
            _logger.debug("updating visible node %d", nodeId)
            _update_node(nodeId, nodeData, viewCommandQueue, nodeTreeId)
        else:
            _logger.debug("adding newly visible node %d", nodeId)
            _add_node(nodeId, nodeData, tree, filter_.visibleNodeIds,
                      visibleBranchNodeIds, expandedNodeIds, selectedNodeIds,
                      viewCommandQueue, nodeTreeId, rootNodeId)
    elif wasVisible:
        _logger.debug("removing newly invisible node %d", nodeId)
        _remove_branch(nodeId, nodeData, tree, filter_.visibleNodeIds,
                       visibleBranchNodeIds, rootNodeId, viewCommandQueue)


class _Visitor:
    def start_hook(self):
        pass
    def end_hook(self):
        pass

class _RefilteringVisitor(_Visitor):
    def __init__(self, tree, searchMatchesLineage, filter_, visibleBranchNodeIds,
                 expandedNodeIds, selectedNodeIds, rootNodeId, nodeTreeId,
                 viewCommandQueue):
        self._tree = tree
        self._searchMatchesLineage = searchMatchesLineage
        self._filter = filter_
        self._visibleBranchNodeIds = visibleBranchNodeIds
        self._expandedNodeIds = expandedNodeIds
        self._selectedNodeIds = selectedNodeIds
        self._rootNodeId = rootNodeId
        self._viewCommandQueue = viewCommandQueue
        self._nodeTreeId = nodeTreeId
    def start_hook(self):
        self._filter.enable_automatic_updates(False)
    def visit(self, nodeId, nodeData):
        if len(nodeData) <= _ATTRIBUTES_IDX:
            _logger.debug("skipping branch since attributes not yet loaded")
            return False
        if nodeData[_ATTRIBUTES_IDX].nodeType == model.NodeTypes.GROUP:
            # group visibility is handled as a side effect of their child packages
            return True
        _filter_and_sync(nodeId, nodeData, self._tree, self._searchMatchesLineage,
                         self._filter, self._visibleBranchNodeIds, self._expandedNodeIds,
                         self._selectedNodeIds, self._rootNodeId, self._viewCommandQueue,
                         self._nodeTreeId, False)
    def end_hook(self):
        self._filter.enable_automatic_updates(True)

class _AddToSetVisitor(_Visitor):
    def __init__(self, nodeSet):
        self._nodeSet = nodeSet
    def visit(self, nodeId, nodeData):
        if len(nodeData) <= _ATTRIBUTES_IDX:
            _logger.debug("skipping branch since attributes not yet loaded")
            return False
        self._nodeSet.add(nodeId)
        return True

class _SyncVisibleNodesVisitor(_Visitor):
    def __init__(self, tree, previouslyVisibleNodeIds, filter_, visibleBranchNodeIds,
                 expandedNodeIds, selectedNodeIds, rootNodeId, viewCommandQueue,
                 nodeTreeId):
        self._tree = tree
        self._previouslyVisibleNodeIds = previouslyVisibleNodeIds
        self._filter = filter_
        self._visibleBranchNodeIds = visibleBranchNodeIds
        self._expandedNodeIds = expandedNodeIds
        self._selectedNodeIds = selectedNodeIds
        self._rootNodeId = rootNodeId
        self._viewCommandQueue = viewCommandQueue
        self._nodeTreeId = nodeTreeId
    def visit(self, nodeId, nodeData):
        if len(nodeData) <= _ATTRIBUTES_IDX:
            _logger.debug("skipping branch since attributes not yet loaded")
            return False
        if nodeData[_ATTRIBUTES_IDX].nodeType == model.NodeTypes.GROUP:
            # we're done -- group visibility is handled according to their child packages
            return True
        isVisible = nodeId in self._filter.visibleNodeIds
        if bool(isVisible) == bool(nodeId in self._previouslyVisibleNodeIds):
            _logger.debug("visibility unchanged (%s) for node %d", isVisible, nodeId)
            return True
        if isVisible:
            _logger.debug("adding newly visible node %d", nodeId)
            _add_node(nodeId, nodeData, self._tree, self._filter.visibleNodeIds,
                      self._visibleBranchNodeIds, self._expandedNodeIds,
                      self._selectedNodeIds, self._viewCommandQueue, self._nodeTreeId,
                      self._rootNodeId)
        else:
            _logger.debug("removing newly invisible node %d", nodeId)
            _remove_branch(nodeId, nodeData, self._tree, self._filter.visibleNodeIds,
                           self._visibleBranchNodeIds, self._rootNodeId,
                           self._viewCommandQueue)
        return True

class _AddToSetAndMatchVisitor(_AddToSetVisitor):
    def __init__(self, nodeSet, expression):
        _AddToSetVisitor.__init__(self, nodeSet)
        self._expression = expression
    def visit(self, nodeId, nodeData):
        if len(nodeData) <= _ATTRIBUTES_IDX:
            _logger.debug("skipping branch since attributes not yet loaded")
            return False
        nodeAttributes = nodeData[_ATTRIBUTES_IDX]
        nodeData[_MATCHES_SEARCH_IDX] = bool(
            self._expression.search(nodeAttributes.label))
        return _AddToSetVisitor.visit(self, nodeId, nodeData)

class _SearchVisitor(_Visitor):
    """Assembles the set of nodeIds whose attributes match the given search expression"""
    def __init__(self, tree, rootNodeId, expression):
        self.matchedNodeIds = set()
        self._tree = tree
        self._rootNodeId = rootNodeId
        self._expression = expression
    def visit(self, nodeId, nodeData):
        # if this node has no attributes yet, it doesn't match (and it has no children,
        # so don't recurse)
        if len(nodeData) <= _ATTRIBUTES_IDX:
            _logger.debug("trimming branch since attributes not yet loaded")
            return False
        nodeAttributes = nodeData[_ATTRIBUTES_IDX]
        # if this node matches, add its ancestors and descendants
        if self._expression.search(nodeAttributes.label):
            nodeData[_MATCHES_SEARCH_IDX] = True
            # get ancestors
            parentNodeId = nodeAttributes.parentNodeId
            while parentNodeId is not self._rootNodeId:
                if parentNodeId in self.matchedNodeIds:
                    break
                self.matchedNodeIds.add(parentNodeId)
                # if the parent didn't have attributes, we wouldn't have gotten this far
                # down in the tree to begin with, so we can assume the parent node's
                # attributes are not None here
                parentNodeId = self._tree[parentNodeId][_ATTRIBUTES_IDX].parentNodeId
            # get descendants
            _visit_tree(nodeId, self._tree, None,
                        _AddToSetAndMatchVisitor(self.matchedNodeIds, self._expression))
            self.matchedNodeIds.add(nodeId)
            # we've already processed the children; no need to recurse
            return False
        nodeData[_MATCHES_SEARCH_IDX] = False
        # keep searching: one of its children might still match
        return True


class _DiffEngine:
    """Subclasses are thread safe as long as all update_* methods are called from a single
    thread.  set_* methods can be called concurrently from different threads.
    Implementation notes:
    ensure attributres exist before children to satisfy algorithm invariants when tracing
    parentage
    ensure a node can be asynchronously updated from a model update before we request it
    explicitly.  this will avoid a potential race condition where we might miss an update.
    """

    def __init__(self, rootNodeId, filter_, generalTabManager, viewCommandQueue):
        self.loadRequestQueue = Queue.Queue() # tuples of (updateTypeMask, nodeId)
        self._rootNodeId = rootNodeId
        self._filter = filter_
        self._generalTabManager = generalTabManager
        self._viewCommandQueue = viewCommandQueue
        self._pendingFilterMask = presenter.FilterIds.NONE
        self._prevSingleSelectedNodeId = None
        self._prevIsMultipleSelected = None
        self._selectedNodeIds = set()
        self._visibleBranchNodeIds = set()
        self._expandedNodeIds = set()
        # nodeId -> [matchesSearch, predNodeId, attributes, children]
        self._tree = {}
        self._tree[self._rootNodeId] = [False, None,
                                        node_attributes.RootNodeAttributes(None)]
        self._visibleBranchNodeIds.add(rootNodeId)
        # put initial load request
        self.loadRequestQueue.put((model.UpdateTypes.CHILDREN, rootNodeId))

    def set_pending_filter_mask(self, filterMask):
        self._pendingFilterMask = self._filter.idMask & filterMask

    def is_in_scope(self, updateType, nodeType):
        """subclass will return whether the specified class of update is in its scope"""
        raise NotImplementedError("subclass must implement")

    def could_use_update(self, updateType, nodeId, version):
        """Assumes update is in scope.  Returns boolean."""
        raise NotImplementedError("subclass must implement")


class PackagesTreeDiffEngine(_DiffEngine):
    def __init__(self, generalTabManager, packageContentsManager, viewCommandQueue):
        _DiffEngine.__init__(self, model.ROOT_NODE_ID,
                             filters.PackagesTreeFilter(viewCommandQueue),
                             generalTabManager, viewCommandQueue)
        self._packageContentsManager = packageContentsManager
        self._pendingSearchString = None
        self._searchExpression = None

    # override
    def is_in_scope(self, updateType, nodeType):
        # called to determine if model updates are in scope for this diff engine
        return (updateType is model.UpdateTypes.ATTRIBUTES and \
                (nodeType is model.NodeTypes.PACKAGE or \
                 nodeType is model.NodeTypes.GROUP)) or \
               (updateType is model.UpdateTypes.CHILDREN and \
                (nodeType is model.NodeTypes.ROOT or \
                 nodeType is model.NodeTypes.GROUP))

    # override
    def could_use_update(self, updateType, nodeId, version):
        """Assumes update is in scope.  Returns boolean"""
        # the following algorithm is thread safe in the sense that it does not mess up
        # other algorithms, being read-only.  These conditions will be checked again, of
        # course, by the thread that actually modifies the data structures
        nodeData = self._tree.get(nodeId)
        if nodeData is None:
            _logger.debug("can't use update: node %d not in tree", nodeId)
            return False
        if model.UpdateTypes.ATTRIBUTES in updateType and len(nodeData) > _ATTRIBUTES_IDX:
            nodeAttributes = nodeData[_ATTRIBUTES_IDX]
            if nodeAttributes is not None:
                if nodeAttributes.version < version:
                    _logger.debug("can use update: node %d is out of date", nodeId)
                    return True
                else:
                    _logger.debug("can't use update: node %d up to date", nodeId)
                    return False
        if model.UpdateTypes.CHILDREN in updateType and len(nodeData) > _CHILDREN_IDX:
            nodeChildren = nodeData[_CHILDREN_IDX]
            if nodeChildren is not None:
                if nodeChildren.version < version:
                    _logger.debug("can use update: node %d is out of date", nodeId)
                    return True
                else:
                    _logger.debug("can't use update: node %d up to date", nodeId)
                    return False
        _logger.debug("can use update for node %d", nodeId)
        return True

    def set_pending_search_string(self, searchString):
        self._pendingSearchString = searchString

    def set_node_expansion(self, nodeId, isExpanded):
        if isExpanded:
            if nodeId in self._expandedNodeIds:
                _logger.warn("node already recorded as expanded: %d", nodeId)
            else:
                _logger.debug("expanding node %d", nodeId)
                self._expandedNodeIds.add(nodeId)
                self._viewCommandQueue.put(
                    presenter.UpdateNodeCommand(presenter.NodeTreeIds.PACKAGES, nodeId,
                                                isExpanded=True))
        else:
            if nodeId not in self._expandedNodeIds:
                _logger.warn("node already recorded as collapsed: %d", nodeId)
            else:
                _logger.debug("collapsing node %d", nodeId)
                self._expandedNodeIds.discard(nodeId)
                self._viewCommandQueue.put(
                    presenter.UpdateNodeCommand(presenter.NodeTreeIds.PACKAGES, nodeId,
                                                isExpanded=False))

    def set_selected_nodes(self, nodeIds):
        _logger.debug("setting selected nodes %s", nodeIds)
        if nodeIds is None:
            self._selectedNodeIds = set()
        else:
            self._selectedNodeIds = set(nodeIds)
        self._update_managers()

    def update_attributes(self, nodeId, nodeAttributes):
        _logger.debug("updating %s node %d attributes to: %s",
                      nodeAttributes.nodeType, nodeId, nodeAttributes)
        nodeData = self._tree[nodeId]
        if len(nodeData) > _ATTRIBUTES_IDX:
            curNodeAttributes = nodeData[_ATTRIBUTES_IDX]
            if nodeAttributes.version <= curNodeAttributes.version:
                _logger.debug("stale incoming update (version %d <= %d); skipping update",
                              nodeAttributes.version, curNodeAttributes.version)
                return
        else:
            # this is the first time we're getting attributes for this node
            _logger.debug("requesting children for node %d", nodeId)
            self.loadRequestQueue.put((model.UpdateTypes.CHILDREN, nodeId))
            nodeData.append(None)
        nodeData[_ATTRIBUTES_IDX] = nodeAttributes
        wasVisibleGroup = nodeId in self._visibleBranchNodeIds
        searchMatchesLineage = self._handle_search(nodeId, nodeData)
        if nodeAttributes.nodeType == model.NodeTypes.GROUP:
            # only update if the group was already visible
            if nodeId in self._visibleBranchNodeIds and wasVisibleGroup:
                _update_node(nodeId, nodeData, self._viewCommandQueue,
                             presenter.NodeTreeIds.PACKAGES)
        else:
            _filter_and_sync(nodeId, nodeData, self._tree, searchMatchesLineage,
                             self._filter, self._visibleBranchNodeIds,
                             self._expandedNodeIds, self._selectedNodeIds,
                             self._rootNodeId, self._viewCommandQueue,
                             presenter.NodeTreeIds.PACKAGES, True)
        self._update_managers()

    def update_children(self, nodeId, nodeChildren):
        nodeData = self._tree[nodeId]
        if len(nodeData) <= _ATTRIBUTES_IDX:
            raise RuntimeError("can't update children without first updating attributes")
        _logger.debug("updating %s node %d children to: %s",
                      nodeData[_ATTRIBUTES_IDX].nodeType, nodeId, nodeChildren)
        curNodeChildren = None
        if len(nodeData) > _CHILDREN_IDX:
            curNodeChildren = nodeData[_CHILDREN_IDX]
            if curNodeChildren.version >= nodeChildren.version:
                _logger.debug("stale incoming update (version %d <= %d); skipping update",
                              nodeChildren.version, curNodeChildren.version)
                return
        else:
            nodeData.append(None)
        nodeData[_CHILDREN_IDX] = nodeChildren
        newChildren = nodeChildren.children
        _logger.debug("updating children for node %d from %s to %s",
                      nodeId, curNodeChildren, newChildren)
        if curNodeChildren is None or len(curNodeChildren.children) == 0:
            if newChildren is not None and len(newChildren) > 0:
                # add new nodes to the tree
                predChildNodeId = None
                for childNodeId in newChildren:
                    self._tree[childNodeId] = [False, predChildNodeId]
                    predChildNodeId = childNodeId
                    _logger.debug("requesting attributes for node %d", childNodeId)
                    self.loadRequestQueue.put((model.UpdateTypes.ATTRIBUTES, childNodeId))
        else:
            newChildrenSet = set(newChildren)
            curChildrenSet = set(curNodeChildren.children)
            # remove newly deleted node trees
            self._filter.enable_automatic_updates(False)
            for childNodeId in curChildrenSet.difference(newChildrenSet):
                nodesToRemove = set()
                _visit_tree(childNodeId, self._tree, None,
                            _AddToSetVisitor(nodesToRemove))
                nodesToRemove.add(childNodeId)
                isVisible = childNodeId in self._filter.visibleNodeIds or \
                          childNodeId in self._visibleBranchNodeIds
                self._filter.remove(nodesToRemove)
                if isVisible:
                    _remove_branch(childNodeId, self._tree[childNodeId], self._tree,
                                   self._filter.visibleNodeIds,
                                   self._visibleBranchNodeIds, self._rootNodeId,
                                   self._viewCommandQueue)
            self._filter.enable_automatic_updates(True)
            for childNodeId in newChildrenSet.difference(curChildrenSet):
                # initialize new node data
                assert childNodeId not in self._tree
                self._tree[childNodeId] = [False, None]
                _logger.debug("requesting attributes for node %d", childNodeId)
                self.loadRequestQueue.put((model.UpdateTypes.ATTRIBUTES, childNodeId))
            # fix up child graph
            predChildNodeId = None
            for childNodeId in newChildren:
                childNode = self._tree[childNodeId]
                if childNode[_PRED_NODE_ID_IDX] != predChildNodeId:
                    _logger.debug("adjusting predecessor for child node %d to %s",
                                  childNodeId, predChildNodeId)
                    childNode[_PRED_NODE_ID_IDX] = predChildNodeId
                    # if this node was already visible, adjust its position in the list
                    # TODO: ensure actual predecessor has changed before updating
                    isVisible = childNodeId in self._filter.visibleNodeIds or \
                              childNodeId in self._visibleBranchNodeIds
                    if isVisible:
                        self._viewCommandQueue.put(presenter.MoveNodeCommand(
                            presenter.NodeTreeIds.PACKAGES, childNodeId,
                            _get_visible_predecessor(childNode, self._tree,
                                                     self._filter.visibleNodeIds,
                                                     self._visibleBranchNodeIds)))
                predChildNodeId = childNodeId
        self._update_managers()

    def update_filter(self, filterMask):
        filterMask &= self._filter.idMask
        _logger.debug("updating filter mask to %s", filterMask)
        if filterMask != self._pendingFilterMask:
            _logger.debug("filter mask stale; not processing")
            return
        previouslyVisibleNodeIds = set(self._filter.visibleNodeIds)
        _logger.debug("previouslyVisibleNodeIds: %s", previouslyVisibleNodeIds)
        if self._filter.set_active_mask(filterMask):
            _visit_tree(self._rootNodeId, self._tree, None,
                        _SyncVisibleNodesVisitor(
                            self._tree, previouslyVisibleNodeIds, self._filter,
                            self._visibleBranchNodeIds, self._expandedNodeIds,
                            self._selectedNodeIds, self._rootNodeId,
                            self._viewCommandQueue, presenter.NodeTreeIds.PACKAGES))
        self._update_managers()

    def update_search_string(self, searchString):
        _logger.debug("updating search string to '%s'", searchString)
        def is_search_string_current():
            return searchString == self._pendingSearchString
        if not is_search_string_current():
            _logger.debug("search string stale; not processing")
            return
        previouslyVisibleNodeIds = set(self._filter.visibleNodeIds)
        _logger.debug("previouslyVisibleNodeIds: %s", previouslyVisibleNodeIds)
        if searchString is None or len(searchString) == 0:
            expression = None
            self._filter.apply_search(None)
        else:
            expression = re.compile(searchString, re.IGNORECASE)
            # walk the tree, matching nodes against the search string, stopping early if
            # the search string goes out of date
            searchVisitor = _SearchVisitor(self._tree, self._rootNodeId, expression)
            _visit_tree(self._rootNodeId, self._tree, is_search_string_current,
                        searchVisitor)
            if not is_search_string_current():
                _logger.debug("search string stale; not processing")
                return
            self._filter.apply_search(searchVisitor.matchedNodeIds)
        _visit_tree(self._rootNodeId, self._tree, None,
                    _SyncVisibleNodesVisitor(
                        self._tree, previouslyVisibleNodeIds, self._filter,
                        self._visibleBranchNodeIds, self._expandedNodeIds,
                        self._selectedNodeIds, self._rootNodeId, self._viewCommandQueue,
                        presenter.NodeTreeIds.PACKAGES))
        self._searchExpression = expression
        self._update_managers()

    def _update_managers(self):
        visibleSelectedNodeIds = self._selectedNodeIds.intersection(
            self._filter.visibleNodeIds)
        numNodes = len(visibleSelectedNodeIds)
        if numNodes == 1:
            nodeId = visibleSelectedNodeIds.pop()
            if nodeId != self._prevSingleSelectedNodeId:
                _logger.debug("updating managers with target node: %d", nodeId)
                self._prevSingleSelectedNodeId = nodeId
                self._prevIsMultipleSelected = False
                self._generalTabManager.set_target_package(nodeId)
                self._packageContentsManager.set_target_package(nodeId, False)
        elif numNodes == 0:
            if self._prevSingleSelectedNodeId is not None or \
               self._prevIsMultipleSelected is not False:
                _logger.debug("updating managers: nothing selected")
                self._prevSingleSelectedNodeId = None
                self._prevIsMultipleSelected = False
                self._generalTabManager.set_target_package(None)
                self._packageContentsManager.set_target_package(None, False)
        elif self._prevSingleSelectedNodeId is not None or \
             self._prevIsMultipleSelected is not True:
            _logger.debug("updating managers: multiple selected")
            self._prevSingleSelectedNodeId = None
            self._prevIsMultipleSelected = True
            self._generalTabManager.set_target_package(None)
            self._packageContentsManager.set_target_package(None, True)

    def _does_ancestor_match_search(self, nodeId, nodeAttributes):
        # check up the tree to see if any ancestor matches the search
        parentNodeId = nodeAttributes.parentNodeId
        while parentNodeId is not self._rootNodeId:
            parentNodeData = self._tree[parentNodeId]
            if parentNodeData[_MATCHES_SEARCH_IDX]:
                return True
            parentNodeId = parentNodeData[_ATTRIBUTES_IDX].parentNodeId
        return False

    def _handle_search(self, nodeId, nodeData):
        """updates matchesSearch attribute for this node.  if it changes, refilters
        and updates visiblity of downstream nodes.  returns whether this node is included
        in a search (that is, returns true if there is no active search, this node matches
        the search, or an ancestor or descendant matches the search)."""
        if self._searchExpression is None:
            _logger.debug("no search active; node %d matches by default", nodeId)
            return True
        nodeAttributes = nodeData[_ATTRIBUTES_IDX]
        if self._searchExpression.search(nodeAttributes.label):
            _logger.debug("node %d matches search", nodeId)
            matchesSearch = True
        else:
            _logger.debug("node %d does not match search", nodeId)
            matchesSearch = False
        prevMatchesSearch = nodeData[_MATCHES_SEARCH_IDX]
        nodeData[_MATCHES_SEARCH_IDX] = matchesSearch
        # TODO: possible optimization: for each node, store whether an ancestor matches
        # TODO: the search
        if matchesSearch:
            if prevMatchesSearch:
                _logger.debug("node %d already matched; no refiltering necessary", nodeId)
                return True
            if self._does_ancestor_match_search(nodeId, nodeAttributes):
                _logger.debug(
                    "an ancestor of node %d already matched; no refiltering necessary",
                    nodeId)
                return True
            _logger.debug("node %d now matches search; refiltering descendants", nodeId)
            _visit_tree(nodeId, self._tree, None, _RefilteringVisitor(
                self._tree, True, self._filter, self._visibleBranchNodeIds,
                self._expandedNodeIds, self._selectedNodeIds, self._rootNodeId,
                presenter.NodeTreeIds.PACKAGES, self._viewCommandQueue))
            return True
        ancestorMatchesSearch = self._does_ancestor_match_search(nodeId, nodeAttributes)
        if prevMatchesSearch:
            if ancestorMatchesSearch:
                _logger.debug("node %d no longer matches search, but an ancestor does",
                              nodeId)
                return True
            _logger.debug("node %d now doesn't match search; refiltering descendants",
                          nodeId)
            _visit_tree(nodeId, self._tree, None, _RefilteringVisitor(
                self._tree, False, self._filter, self._visibleBranchNodeIds,
                self._expandedNodeIds, self._selectedNodeIds, self._rootNodeId,
                presenter.NodeTreeIds.PACKAGES, self._viewCommandQueue))
            return False
        return ancestorMatchesSearch


#class PackageContentsTreeDiffEngine(_DiffEngine):
    #def __init__(self, generalTabManager, fileDetailsManager, viewCommandQueue):
        #_DiffEngine.__init__(self, generalTabManager, viewCommandQueue)
        #self._fileDetailsManager = fileDetailsManager
        #self._pendingDetailsTabId = presenter.DetailsTabIds.NONE
        #self._detailsTabId = presenter.DetailsTabIds.NONE

    #def set_pending_details_tab_selection(self, detailsTabId):
        #self._pendingDetailsTabId = detailsTabId
        # TODO: inform general tab manager

    #def apply_update(self, update):
        #pass
