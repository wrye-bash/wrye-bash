# -*- coding: utf-8 -*-
#
# bait/test/mock_model.py
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
import itertools
import logging

from .. import model
from ..model import node_attributes, node_children, node_details


_logger = logging.getLogger(__name__)

_ATTRIBUTES_IDX = 0
_CHILDREN_IDX = 1
_DETAILS_IDX = 2


def _generate_packages_all_attributes(data, parentId, parentChildren):
    nextId = parentId + 1
    attributes = [
        "isDirty", "isInstalled", "isNotInstalled", "isHidden", "isNew", "hasMissingDeps",
        "isUnrecognized", "isCorrupt", "updateAvailable", "alwaysVisible", "isArchive",
        "hasWizard", "hasMatched", "hasMismatched", "hasMissing", "hasSubpackages"]
    for numTrue in xrange(len(attributes)+1):
        for trueList in itertools.combinations(attributes, numTrue):
            if "isArchive" in trueList:
                contextMenuId = node_attributes.ContextMenuIds.ARCHIVE
            else:
                contextMenuId = node_attributes.ContextMenuIds.PROJECT
            attributeMap = {key:True for key in trueList}
            label = "attributes:"
            for attribute in attributes:
                if attribute in trueList:
                    label += " " + attribute
            data[nextId] = (
                node_attributes.PackageNodeAttributes(
                    label, parentId, contextMenuId, **attributeMap),
                None,
                node_details.PackageNodeDetails())
            parentChildren.append(nextId)
            nextId += 1
    return nextId



#  - MovingGroup
#    - Several packages that, when clicked on, change order within the group
#  - UpdateGroup
#    - Several packages that, when clicked on, change their attributes
#  - Random package generator: edit comments field with desired no. of packages
#    - initially empty, but will generate random empty packages on request
#  - Random file generator: edit comments field with desired no. of files
#    - initially empty, but will generate packages with files on request
#- All generated packages and files should have names that describe their
#    attributes so that they can be visually verified to be behaving properly.
class MockModel:
    def __init__(self):
        self.updateNotificationQueue = Queue.Queue()
        self._data = {}

        rootChildren = []
        self._data[model.ROOT_NODE_ID] = (
            node_attributes.RootNodeAttributes(
                node_attributes.StatusLoadingData(5, 1000)),
            node_children.NodeChildren(rootChildren),
            None)

        # reset trigger
        self._data[1] = (
            node_attributes.GroupNodeAttributes(
                "ResetGroup", 0, node_attributes.ContextMenuIds.GROUP),
            node_children.NodeChildren([2]),
            None)
        rootChildren.append(1)
        self._data[2] = (
            node_attributes.PackageNodeAttributes(
                "Select me to reset package list", 1,
                node_attributes.ContextMenuIds.PROJECT, alwaysVisible=True),
            None,
            node_details.PackageNodeDetails())

        # packages with valid attribute combinations
        self._data[3] = (
            node_attributes.GroupNodeAttributes(
                "Packages with expected attribute combinations", 0,
                node_attributes.ContextMenuIds.GROUP),
            node_children.NodeChildren([4]),
            None)
        rootChildren.append(3)
        self._data[4] = (
            node_attributes.PackageNodeAttributes(
                "Test", 3, node_attributes.ContextMenuIds.PROJECT, isInstalled=True),
            None,
            node_details.PackageNodeDetails())

        # packages with all attribute combinations
        allAttributesChildren = []
        self._data[5] = (
            node_attributes.GroupNodeAttributes(
                "Packages with all attribute combinations", 0,
                node_attributes.ContextMenuIds.GROUP),
            node_children.NodeChildren(allAttributesChildren),
            None)
        rootChildren.append(5)
        nextId = _generate_packages_all_attributes(self._data, 5, allAttributesChildren)


    def start(self):
        _logger.debug("mock model starting")

    def pause(self):
        _logger.debug("mock model pausing")

    def resume(self):
        _logger.debug("mock model resuming")

    def shutdown(self):
        _logger.debug("mock model shutting down")
        self.updateNotificationQueue.put(None)

    def get_node_attributes(self, nodeId):
        return self._get_node_element(nodeId, "attributes", _ATTRIBUTES_IDX)

    def get_node_children(self, nodeId):
        return self._get_node_element(nodeId, "children", _CHILDREN_IDX)

    def get_node_details(self, nodeId):
        return self._get_node_element(nodeId, "details", _DETAILS_IDX)

    def _get_node_element(self, nodeId, elementName, elementIdx):
        if nodeId in self._data:
            _logger.debug("retrieving %s for node %d", elementName, nodeId)
            return self._data[nodeId][elementIdx]
        _logger.debug("no %s to retrieve for node %d", elementName, nodeId)
        return None


class OldMockPresenter:
    def __init__(self):
        self.viewCommandQueue = Queue.Queue()
        self._filterMask = presenter.FilterIds.NONE
        self._groupExpansionStates = {}
        self._dirExpansionStates = {}
        self._curDetailsTab = presenter.DetailsTabIds.NONE
        self._selectedPackages = []
        self._selectedFiles = []
        self._searchString = None

    def start(self, curDetailsTabId, filterStateMap):
        _logger.debug("mock presenter starting")
        self._curDetailsTab = curDetailsTabId
        for filterId, value in filterStateMap.iteritems():
            _logger.debug("initializing filter %s to %s", filterId, value)
            if value:
                self._filterMask = self._filterMask | filterId
            else:
                self._filterMask = self._filterMask & ~filterId
        self.viewCommandQueue.put(presenter.SetStyleMaps(
            _foregroundColorMap, _highlightColorMap, _checkedIconMap, _uncheckedIconMap))
        self.viewCommandQueue.put(presenter.SetStatus(
            presenter.Status.LOADING, presenter.HighlightColorIds.LOADING,
            loadingComplete=0, loadingTotal=100))
        self.set_packages_tree_selections([])
        self.set_files_tree_selections([])
        self._rebuild_packages_tree()
        self.viewCommandQueue.put(presenter.SetPackageInfo(
            presenter.DetailsTabIds.GENERAL, None))
        self.viewCommandQueue.put(presenter.SetStatus(
            presenter.Status.OK, presenter.HighlightColorIds.OK))

    def pause(self):
        _logger.debug("mock presenter pausing")

    def resume(self):
        _logger.debug("mock presenter resuming")

    def shutdown(self):
        _logger.debug("mock presenter shutting down")
        self.viewCommandQueue.put(None)

    def set_filter_state(self, filterId, value):
        _logger.debug("setting filter %s to %s", filterId, value)
        if (not 0 is self._filterMask & filterId) is value:
            _logger.debug("filter %s already set to %s; ignoring", filterId, value)
            return
        if value:
            self._filterMask |= filterId
        else:
            self._filterMask &= ~filterId
        self._rebuild_packages_tree(self._searchString)

    def set_packages_tree_selections(self, nodeIds, saveSelections=True):
        _logger.debug("setting packages tree selection to node(s) %s, saveSelections=%s",
                      nodeIds, saveSelections)
        self.viewCommandQueue.put(presenter.ClearFiles())
        if saveSelections:
            self._selectedPackages = nodeIds
        numNodeIds = len(nodeIds)
        if numNodeIds is 1:
            # update package details
            node = pkgNodes[nodeIds[0]]
            self.viewCommandQueue.put(presenter.SetPackageLabel(node[LABEL_IDX]))
            if self._curDetailsTab is presenter.DetailsTabIds.GENERAL:
                self.viewCommandQueue.put(presenter.SetPackageInfo(
                    self._curDetailsTab, get_general_map(nodeIds[0])))
            else:
                self.viewCommandQueue.put(presenter.SetPackageInfo(
                    self._curDetailsTab,
                    node[PACKAGE_DETAILS_MAP_IDX][self._curDetailsTab]))
            self._rebuild_files_tree(node[FILE_NODES_IDX])
        elif numNodeIds is 0:
            self.viewCommandQueue.put(presenter.SetPackageLabel(None))
        else:
            self.viewCommandQueue.put(presenter.SetPackageLabel(""))

    def set_files_tree_selections(self, nodeIds, saveSelections=True):
        _logger.debug("setting files tree selection to node(s) %s", nodeIds)
        if saveSelections:
            self._selectedFiles = nodeIds
        numNodeIds = len(nodeIds)
        if numNodeIds is 1:
            # update file details
            self.viewCommandQueue.put(presenter.SetFileDetails(
                pkgNodes[self._selectedPackages[0]][FILE_NODES_IDX][nodeIds[0]][FILE_DETAILS_IDX]))
        else:
            self.viewCommandQueue.put(presenter.SetFileDetails(None))

    def set_details_tab_selection(self, detailsTabId):
        _logger.debug("setting details tab selection to %s", detailsTabId)
        self._curDetailsTab = detailsTabId
        numSelectedPackages = len(self._selectedPackages)
        if numSelectedPackages is 0:
            self.viewCommandQueue.put(presenter.SetPackageInfo(detailsTabId, None))
        elif numSelectedPackages is 1:
            if self._curDetailsTab is presenter.DetailsTabIds.GENERAL:
                self.viewCommandQueue.put(presenter.SetPackageInfo(
                    detailsTabId, get_general_map(self._selectedPackages[0])))
            else:
                self.viewCommandQueue.put(presenter.SetPackageInfo(
                    detailsTabId,
                    pkgNodes[self._selectedPackages[0]][PACKAGE_DETAILS_MAP_IDX][detailsTabId]))

    def set_group_node_expanded(self, nodeId, value):
        _logger.debug("setting group node %d expansion to %s", nodeId, value)
        self._groupExpansionStates[nodeId] = value

    def set_dir_node_expanded(self, nodeId, value):
        _logger.debug("setting directory node %d expansion to %s", nodeId, value)
        self._dirExpansionStates[nodeId] = value

    def set_search_string(self, text):
        if text is "": text = None
        if text is self._searchString:
            _logger.debug("search string unchanged; skipping")
            return
        _logger.debug("running search: '%s'", text)
        self._rebuild_packages_tree(text)
        self._searchString = text

    def _matches_search(self, nodeIds, searchString, parentMatches):
        if searchString is None or parentMatches:
            return True
        if hasattr(nodeIds, "__iter__"):
            for nodeId in nodeIds:
                if re.search(searchString, pkgNodes[nodeId][LABEL_IDX]): return True
        else:
            return re.search(searchString, pkgNodes[nodeIds][LABEL_IDX])
        return False

    def _add_node(self, nodes, nodeId, addedSet, addNodeFn):
        node = nodes[nodeId]
        parentNodeId = node[PARENT_NODE_ID_IDX]
        if not parentNodeId is None and not nodes[parentNodeId][IS_VISIBLE_IDX]:
            # add parents if they're not already visible
            _logger.debug("adding parent of node %d", nodeId)
            self._add_node(nodes, parentNodeId, addedSet, addNodeFn)
        # calculate predNodeId
        predNodeId = node[PRED_NODE_ID_IDX]
        while not predNodeId is None:
            predNode = nodes[predNodeId]
            # if we found a visible predecessor, stop iterating
            if predNode[IS_VISIBLE_IDX]: break
            predNodeId = predNode[PRED_NODE_ID_IDX]
        addNodeFn(node, nodeId, parentNodeId, predNodeId)
        node[IS_VISIBLE_IDX] = True
        addedSet.add(nodeId)

    def _add_packages_tree_node(self, node, nodeId, parentNodeId, predNodeId):
        if node[NODE_TYPE_IDX] is model.NodeTypes.GROUP:
            addClass = presenter.AddGroup
            expand = self._groupExpansionStates.get(nodeId)
            _logger.debug("adding group node %d (expanded: %s)", nodeId, expand)
        else:
            addClass = presenter.AddPackage
            expand = False
            _logger.debug("adding package node %d", nodeId)
        self.viewCommandQueue.put(addClass(("%.2d "%(nodeId+1))+node[LABEL_IDX], nodeId,
                                           parentNodeId, predNodeId, node[STYLE_IDX]))
        if expand:
            self.viewCommandQueue.put(presenter.ExpandGroup(nodeId))

    def _add_files_tree_node(self, node, nodeId, parentNodeId, predNodeId):
        if node[NODE_TYPE_IDX] is model.NodeTypes.DIRECTORY:
            expand = self._dirExpansionStates.get(nodeId)
            _logger.debug("adding dir node %d (expanded: %s)", nodeId, expand)
        else:
            expand = False
            _logger.debug("adding file node %d", nodeId)
        self.viewCommandQueue.put(presenter.AddFile(node[LABEL_IDX], nodeId,
                                                        parentNodeId, predNodeId,
                                                        node[STYLE_IDX]))
        if expand:
            self.viewCommandQueue.put(presenter.ExpandDir(nodeId))

    def _rebuild_packages_tree(self, searchString=None):
        # clear tree
        self.viewCommandQueue.put(presenter.ClearPackages())

        # keep total and search match counts
        totals = {}
        totals[presenter.FilterIds.PACKAGES_HIDDEN] = 0
        totals[presenter.FilterIds.PACKAGES_INSTALLED] = 0
        totals[presenter.FilterIds.PACKAGES_NOT_INSTALLED] = 0
        matches = {}
        matches[presenter.FilterIds.PACKAGES_HIDDEN] = 0
        matches[presenter.FilterIds.PACKAGES_INSTALLED] = 0
        matches[presenter.FilterIds.PACKAGES_NOT_INSTALLED] = 0
        # track which elements have been added
        addedSet = set()

        # scan nodes
        for nodeId in xrange(0, len(pkgNodes)):
            _logger.debug("filtering node %d", nodeId)
            node = pkgNodes[nodeId]
            node[IS_VISIBLE_IDX] = False
            if node[PARENT_NODE_ID_IDX] is None:
                parentMatches = False
            else:
                parentMatches = pkgNodes[node[PARENT_NODE_ID_IDX]][MATCHES_SEARCH_IDX]
            if self._matches_search(nodeId, searchString, parentMatches):
                node[MATCHES_SEARCH_IDX] = True
                if not node[NODE_TYPE_IDX] is model.NodeTypes.GROUP:
                    matches[node[FILTER_IDX]] += 1
                # apply filters
                if node[FILTER_IDX] & self._filterMask != 0:
                    self._add_node(pkgNodes, nodeId, addedSet,
                                   self._add_packages_tree_node)
            else:
                node[MATCHES_SEARCH_IDX] = False
            if not node[NODE_TYPE_IDX] is model.NodeTypes.GROUP:
                totals[node[FILTER_IDX]] += 1

        # update filter labels
        self.viewCommandQueue.put(presenter.SetFilterStats(
            presenter.FilterIds.PACKAGES_HIDDEN,
            matches[presenter.FilterIds.PACKAGES_HIDDEN],
            totals[presenter.FilterIds.PACKAGES_HIDDEN]))
        self.viewCommandQueue.put(presenter.SetFilterStats(
            presenter.FilterIds.PACKAGES_INSTALLED,
            matches[presenter.FilterIds.PACKAGES_INSTALLED],
            totals[presenter.FilterIds.PACKAGES_INSTALLED]))
        self.viewCommandQueue.put(presenter.SetFilterStats(
            presenter.FilterIds.PACKAGES_NOT_INSTALLED,
            matches[presenter.FilterIds.PACKAGES_NOT_INSTALLED],
            totals[presenter.FilterIds.PACKAGES_NOT_INSTALLED]))

        # persist selections for the packages that are still visible
        addedSet &= set(self._selectedPackages)
        addedSetList = list(addedSet)
        #self.viewCommandQueue.put(presenter.SelectPackages(addedSetList))
        self.set_packages_tree_selections(addedSetList, False)

    def _rebuild_files_tree(self, nodes=None):
        # clear tree
        self.viewCommandQueue.put(presenter.ClearFiles())

        # keep counts
        filterIds = (presenter.FilterIds.FILES_PLUGINS,
                     presenter.FilterIds.FILES_RESOURCES,
                     presenter.FilterIds.FILES_OTHER)
        totals = {}
        for filterId in filterIds:
            totals[filterId] = 0

        # track which elements have been added
        addedSet = set()

        # scan nodes
        if nodes is None:
            nodes = pkgNodes[self._selectedPackages[0]][FILE_NODES_IDX]
        if not nodes is None:
            numNodes = len(nodes)
            for nodeId in xrange(0, numNodes):
                node = nodes[nodeId]
                node[IS_VISIBLE_IDX] = False
                # apply filters
                filter = node[FILTER_IDX]
                if not filter & self._filterMask is 0:
                    self._add_node(nodes, nodeId, addedSet, self._add_files_tree_node)
                if not node[NODE_TYPE_IDX] is model.NodeTypes.DIRECTORY:
                    totals[filter] += 1
            _logger.debug("filtered %d file nodes", numNodes)

        # update filter labels
        for filterId in filterIds:
            self.viewCommandQueue.put(presenter.SetFilterStats(
                filterId, totals[filterId], totals[filterId]))

        # persist selections for the files that are still visible
        addedSet &= set(self._selectedFiles)
        addedSetList = list(addedSet)
        self.viewCommandQueue.put(presenter.SelectFiles(addedSetList))
        self.set_files_tree_selections(addedSetList, False)
