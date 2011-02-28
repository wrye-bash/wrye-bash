# -*- coding: utf-8 -*-
#
# bait/test/mock_presenter.py
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

from .. import presenter
from ..presenter import view_commands
from mock_presenter_data import *


_logger = logging.getLogger(__name__)
_colorMap = {
        view_commands.TEXT_DISABLED:(142,139,138),
        view_commands.TEXT_HAS_INACTIVE_OVERRIDDE:(255,165,0),
        view_commands.HIGHLIGHT_ERROR:(193,205,205),
        view_commands.HIGHLIGHT_MISSING_DEPENDENCY:(255,0,0),
        view_commands.HIGHLIGHT_DIRTY:(255,215,0)
    }
_checkedIconMap = {
        view_commands.ICON_PROJECT_MATCHES:"images/diamond_green_inc.png",
        view_commands.ICON_PROJECT_MISMATCHED:"images/diamond_orange_inc.png",
        view_commands.ICON_PROJECT_MISSING:"images/diamond_red_inc.png",
        view_commands.ICON_PROJECT_EMPTY:"images/diamond_white_inc.png",
        view_commands.ICON_PROJECT_UNINSTALLABLE:"images/diamond_grey_inc.png",
        view_commands.ICON_INSTALLER_MATCHES:"images/checkbox_green_inc.png",
        view_commands.ICON_INSTALLER_MISMATCHED:"images/checkbox_orange_inc.png",
        view_commands.ICON_INSTALLER_MISSING:"images/checkbox_red_inc.png",
        view_commands.ICON_INSTALLER_EMPTY:"images/checkbox_white_inc.png",
        view_commands.ICON_INSTALLER_UNINSTALLABLE:"images/checkbox_grey_inc.png"
    }
_uncheckedIconMap = {
        view_commands.ICON_PROJECT_MATCHES:"images/diamond_green_off.png",
        view_commands.ICON_PROJECT_MISMATCHED:"images/diamond_orange_off.png",
        view_commands.ICON_PROJECT_MISSING:"images/diamond_red_off.png",
        view_commands.ICON_PROJECT_EMPTY:"images/diamond_white_off.png",
        view_commands.ICON_PROJECT_UNINSTALLABLE:"images/diamond_grey_off.png",
        view_commands.ICON_INSTALLER_MATCHES:"images/checkbox_green_off.png",
        view_commands.ICON_INSTALLER_MISMATCHED:"images/checkbox_orange_off.png",
        view_commands.ICON_INSTALLER_MISSING:"images/checkbox_red_off.png",
        view_commands.ICON_INSTALLER_EMPTY:"images/checkbox_white_off.png",
        view_commands.ICON_INSTALLER_UNINSTALLABLE:"images/checkbox_grey_off.png"
    }


class MockPresenter:
    def __init__(self):
        self.viewCommandQueue = Queue.Queue()
        self._filterMask = 0
        self._groupExpansionStates = {}
        self._dirExpansionStates = {}
        self._curDetailsTab = 0
        self._selectedPackages = []
        self._selectedFiles = []
        self._searchString = None

    def start(self, curDetailsTabId, filterStateMap):
        _logger.debug("mock presenter starting")
        self._curDetailsTab = curDetailsTabId
        for filterId, value in filterStateMap.iteritems():
            _logger.debug("initializing filter %d to %s", filterId, value)
            if value:
                self._filterMask |= filterId
            else:
                self._filterMask &= ~filterId
        self.viewCommandQueue.put(view_commands.SetStyleMaps(_colorMap, _checkedIconMap, _uncheckedIconMap))
        self.viewCommandQueue.put(view_commands.SetDataStats(127, 209, 2097, 41728))
        self.set_packages_tree_selections([])
        self.set_files_tree_selections([])
        self._rebuild_packages_tree()
        self.viewCommandQueue.put(view_commands.SetPackageInfo(presenter.DETAILS_TAB_ID_GENERAL, None))
        self.viewCommandQueue.put(view_commands.StatusUpdate("finished loading"))

    def pause(self):
        _logger.debug("mock presenter pausing")
        self.viewCommandQueue.put(view_commands.StatusUpdate("pausing"))

    def resume(self):
        _logger.debug("mock presenter resuming")
        self.viewCommandQueue.put(view_commands.StatusUpdate("resuming"))

    def shutdown(self):
        _logger.debug("mock presenter shutting down")
        self.viewCommandQueue.put(view_commands.StatusUpdate("shutting down"))
        self.viewCommandQueue.put(None)

    def set_filter_state(self, filterId, value):
        _logger.debug("setting filter %d to %s", filterId, value)
        if (not 0 is self._filterMask & filterId) is value:
            _logger.debug("filter %d already set to %s; ignoring", filterId, value)
            return
        if value:
            self._filterMask |= filterId
        else:
            self._filterMask &= ~filterId
        self._rebuild_packages_tree(self._searchString)

    def set_packages_tree_selections(self, nodeIds, saveSelections=True):
        _logger.debug("setting packages tree selection to node(s) %s, saveSelections=%s", nodeIds, saveSelections)
        self.viewCommandQueue.put(view_commands.ClearFiles())
        if saveSelections:
            self._selectedPackages = nodeIds
        numNodeIds = len(nodeIds)
        if numNodeIds is 1:
            # update package details
            node = pkgNodes[nodeIds[0]]
            self.viewCommandQueue.put(view_commands.SetPackageLabel(node[LABEL_IDX]))
            self.viewCommandQueue.put(view_commands.SetPackageInfo(self._curDetailsTab, node[PACKAGE_DETAILS_MAP_IDX][self._curDetailsTab]))
            self._rebuild_files_tree(node[FILE_NODES_IDX])
        elif numNodeIds is 0:
            self.viewCommandQueue.put(view_commands.SetPackageLabel(None))
        else:
            self.viewCommandQueue.put(view_commands.SetPackageLabel(""))
        
    def set_files_tree_selections(self, nodeIds, saveSelections=True):
        _logger.debug("setting files tree selection to node(s) %s", nodeIds)
        if saveSelections:
            self._selectedFiles = nodeIds
        numNodeIds = len(nodeIds)
        if numNodeIds is 1:
            # update file details
            self.viewCommandQueue.put(view_commands.SetFileDetails(pkgNodes[self._selectedPackages[0]][FILE_NODES_IDX][nodeIds[0]][FILE_DETAILS_IDX]))
        else:
            self.viewCommandQueue.put(view_commands.SetFileDetails(None))

    def set_details_tab_selection(self, detailsTabId):
        _logger.debug("setting details tab selection to %d", detailsTabId)
        self._curDetailsTab = detailsTabId
        numSelectedPackages = len(self._selectedPackages)
        if numSelectedPackages is 0:
            self.viewCommandQueue.put(view_commands.SetPackageInfo(detailsTabId, None))
        elif numSelectedPackages is 1:
            self.viewCommandQueue.put(view_commands.SetPackageInfo(detailsTabId, pkgNodes[self._selectedPackages[0]][PACKAGE_DETAILS_MAP_IDX][detailsTabId]))

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
        if node[NODE_TYPE_IDX] is presenter.NODE_TYPE_GROUP:
            addClass = view_commands.AddGroup
            expand = self._groupExpansionStates.get(nodeId)
            _logger.debug("adding group node %d (expanded: %s)", nodeId, expand)
        else:
            addClass = view_commands.AddPackage
            expand = False
            _logger.debug("adding package node %d", nodeId)
        self.viewCommandQueue.put(addClass(("%.2d "%(nodeId+1))+node[LABEL_IDX], nodeId, parentNodeId, predNodeId, node[STYLE_IDX]))
        if expand:
            self.viewCommandQueue.put(view_commands.ExpandGroup(nodeId))

    def _add_files_tree_node(self, node, nodeId, parentNodeId, predNodeId):
        if node[NODE_TYPE_IDX] is presenter.NODE_TYPE_DIRECTORY:
            expand = self._dirExpansionStates.get(nodeId)
            _logger.debug("adding dir node %d (expanded: %s)", nodeId, expand)
        else:
            expand = False
            _logger.debug("adding file node %d", nodeId)
        self.viewCommandQueue.put(view_commands.AddFile(node[LABEL_IDX], nodeId, parentNodeId, predNodeId, node[STYLE_IDX]))
        if expand:
            self.viewCommandQueue.put(view_commands.ExpandDir(nodeId))

    def _rebuild_packages_tree(self, searchString=None):
        # clear tree
        self.viewCommandQueue.put(view_commands.ClearPackages())

        # keep total and search match counts
        totals = {}
        totals[presenter.FILTER_ID_PACKAGES_HIDDEN] = 0
        totals[presenter.FILTER_ID_PACKAGES_INSTALLED] = 0
        totals[presenter.FILTER_ID_PACKAGES_NOT_INSTALLED] = 0
        matches = {}
        matches[presenter.FILTER_ID_PACKAGES_HIDDEN] = 0
        matches[presenter.FILTER_ID_PACKAGES_INSTALLED] = 0
        matches[presenter.FILTER_ID_PACKAGES_NOT_INSTALLED] = 0
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
                if not node[NODE_TYPE_IDX] is presenter.NODE_TYPE_GROUP:
                    matches[node[FILTER_IDX]] += 1
                # apply filters
                if not node[FILTER_IDX] & self._filterMask is 0:
                    self._add_node(pkgNodes, nodeId, addedSet, self._add_packages_tree_node)
            else:
                node[MATCHES_SEARCH_IDX] = False
            if not node[NODE_TYPE_IDX] is presenter.NODE_TYPE_GROUP:
                totals[node[FILTER_IDX]] += 1
        
        # update filter labels        
        self.viewCommandQueue.put(view_commands.SetFilterStats(presenter.FILTER_ID_PACKAGES_HIDDEN, matches[presenter.FILTER_ID_PACKAGES_HIDDEN], totals[presenter.FILTER_ID_PACKAGES_HIDDEN]))
        self.viewCommandQueue.put(view_commands.SetFilterStats(presenter.FILTER_ID_PACKAGES_INSTALLED, matches[presenter.FILTER_ID_PACKAGES_INSTALLED], totals[presenter.FILTER_ID_PACKAGES_INSTALLED]))
        self.viewCommandQueue.put(view_commands.SetFilterStats(presenter.FILTER_ID_PACKAGES_NOT_INSTALLED, matches[presenter.FILTER_ID_PACKAGES_NOT_INSTALLED], totals[presenter.FILTER_ID_PACKAGES_NOT_INSTALLED]))
        
        # persist selections for the packages that are still visible
        addedSet &= set(self._selectedPackages)
        addedSetList = list(addedSet)
        self.viewCommandQueue.put(view_commands.SelectPackages(addedSetList))
        self.set_packages_tree_selections(addedSetList, False)

    def _rebuild_files_tree(self, nodes=None):
        # clear tree
        self.viewCommandQueue.put(view_commands.ClearFiles())

        # keep counts
        filterIds = (presenter.FILTER_ID_FILES_PLUGINS, presenter.FILTER_ID_FILES_RESOURCES, presenter.FILTER_ID_FILES_OTHER)
        totals = {}
        for filterId in filterIds:
            totals[filterId] = 0

        # track which elements have been added
        addedSet = set()

        # scan nodes
        if nodes is None:
            nodes = pkgNodes[self._selectedPackages[0]][FILE_NODES_IDX]
        if not nodes is None:
            for nodeId in xrange(0, len(nodes)):
                _logger.debug("filtering file node %d", nodeId)
                node = nodes[nodeId]
                node[IS_VISIBLE_IDX] = False
                # apply filters
                filter = node[FILTER_IDX]
                if not filter & self._filterMask is 0:
                    self._add_node(nodes, nodeId, addedSet, self._add_files_tree_node)
                if not node[NODE_TYPE_IDX] is presenter.NODE_TYPE_DIRECTORY:
                    totals[filter] += 1
        
        # update filter labels        
        for filterId in filterIds:
            self.viewCommandQueue.put(view_commands.SetFilterStats(filterId, totals[filterId], totals[filterId]))
        
        # persist selections for the files that are still visible
        addedSet &= set(self._selectedFiles)
        addedSetList = list(addedSet)
        self.viewCommandQueue.put(view_commands.SelectFiles(addedSetList))
        self.set_files_tree_selections(addedSetList, False)
