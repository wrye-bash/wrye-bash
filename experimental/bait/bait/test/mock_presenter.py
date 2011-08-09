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
import time

from .. import presenter
from ..util import monitored_thread


_logger = logging.getLogger(__name__)
_foregroundColorMap = {
        presenter.ForegroundColorIds.DISABLED:(142,139,138),
        presenter.ForegroundColorIds.HAS_INACTIVE_OVERRIDDE:(255,165,0)
    }
_highlightColorMap = {
        presenter.HighlightColorIds.ERROR:(193,205,205),
        presenter.HighlightColorIds.MISSING_DEPENDENCY:(255,0,0),
        presenter.HighlightColorIds.DIRTY:(255,215,0),
        presenter.HighlightColorIds.LOADING:(255,255,0),
        presenter.HighlightColorIds.OK:(0,255,0)
    }
_checkedIconMap = {
        presenter.IconIds.PROJECT_MATCHES:"images/diamond_green_inc.png",
        presenter.IconIds.PROJECT_MATCHES_WIZ:"images/diamond_green_inc_wiz.png",
        presenter.IconIds.PROJECT_MISMATCHED:"images/diamond_orange_inc.png",
        presenter.IconIds.PROJECT_MISMATCHED_WIZ:"images/diamond_orange_inc_wiz.png",
        presenter.IconIds.PROJECT_MISSING:"images/diamond_red_inc.png",
        presenter.IconIds.PROJECT_MISSING_WIZ:"images/diamond_red_inc_wiz.png",
        presenter.IconIds.PROJECT_EMPTY:"images/diamond_white_off.png",
        presenter.IconIds.PROJECT_EMPTY_WIZ:"images/diamond_white_off_wiz.png",
        presenter.IconIds.PROJECT_UNINSTALLABLE:"images/diamond_grey_off.png",
        presenter.IconIds.INSTALLER_MATCHES:"images/checkbox_green_inc.png",
        presenter.IconIds.INSTALLER_MATCHES_WIZ:"images/checkbox_green_inc_wiz.png",
        presenter.IconIds.INSTALLER_MISMATCHED:"images/checkbox_orange_inc.png",
        presenter.IconIds.INSTALLER_MISMATCHED_WIZ:"images/checkbox_orange_inc_wiz.png",
        presenter.IconIds.INSTALLER_MISSING:"images/checkbox_red_inc.png",
        presenter.IconIds.INSTALLER_MISSING_WIZ:"images/checkbox_red_inc_wiz.png",
        presenter.IconIds.INSTALLER_EMPTY:"images/checkbox_white_off.png",
        presenter.IconIds.INSTALLER_EMPTY_WIZ:"images/checkbox_white_off_wiz.png",
        presenter.IconIds.INSTALLER_UNINSTALLABLE:"images/checkbox_grey_off.png"
    }
_uncheckedIconMap = {
        presenter.IconIds.PROJECT_MATCHES:"images/diamond_green_off.png",
        presenter.IconIds.PROJECT_MATCHES_WIZ:"images/diamond_green_off_wiz.png",
        presenter.IconIds.PROJECT_MISMATCHED:"images/diamond_orange_off.png",
        presenter.IconIds.PROJECT_MISMATCHED_WIZ:"images/diamond_orange_off_wiz.png",
        presenter.IconIds.PROJECT_MISSING:"images/diamond_red_off.png",
        presenter.IconIds.PROJECT_MISSING_WIZ:"images/diamond_red_off_wiz.png",
        presenter.IconIds.PROJECT_EMPTY:"images/diamond_white_off.png",
        presenter.IconIds.PROJECT_EMPTY_WIZ:"images/diamond_white_off_wiz.png",
        presenter.IconIds.PROJECT_UNINSTALLABLE:"images/diamond_grey_off.png",
        presenter.IconIds.INSTALLER_MATCHES:"images/checkbox_green_off.png",
        presenter.IconIds.INSTALLER_MATCHES_WIZ:"images/checkbox_green_off_wiz.png",
        presenter.IconIds.INSTALLER_MISMATCHED:"images/checkbox_orange_off.png",
        presenter.IconIds.INSTALLER_MISMATCHED_WIZ:"images/checkbox_orange_off_wiz.png",
        presenter.IconIds.INSTALLER_MISSING:"images/checkbox_red_off.png",
        presenter.IconIds.INSTALLER_MISSING_WIZ:"images/checkbox_red_off_wiz.png",
        presenter.IconIds.INSTALLER_EMPTY:"images/checkbox_white_off.png",
        presenter.IconIds.INSTALLER_EMPTY_WIZ:"images/checkbox_white_off_wiz.png",
        presenter.IconIds.INSTALLER_UNINSTALLABLE:"images/checkbox_grey_off.png"
    }

_commands = [
    presenter.SetStyleMapsCommand(
            _foregroundColorMap, _highlightColorMap, _checkedIconMap, _uncheckedIconMap),
    presenter.SetStatusLoadingCommand(0, 6),
    presenter.AddNodeCommand(1, "Installed Data", False, presenter.Style(),
                             presenter.NodeTreeIds.PACKAGES, None, None,
                             presenter.ContextMenuIds.INSTALLED_DATA, False),
    presenter.SetStatusLoadingCommand(1, 6),
    presenter.AddNodeCommand(5, "Uninstalled archive with wizard", False,
                             presenter.Style(
                                 checkboxState=False,
                                 iconId=presenter.IconIds.PROJECT_MISSING_WIZ),
                             presenter.NodeTreeIds.PACKAGES, None, 1,
                             presenter.ContextMenuIds.ARCHIVE, False),
    presenter.SetStatusLoadingCommand(2, 6),
    presenter.AddNodeCommand(2, "Group of packages", True, presenter.Style(),
                             presenter.NodeTreeIds.PACKAGES, None, 5,
                             presenter.ContextMenuIds.GROUP, False),
    presenter.SetStatusLoadingCommand(3, 6),
    presenter.AddNodeCommand(3, "Installed, prehighlighted project", False,
                             presenter.Style(checkboxState=True,
                                             iconId=presenter.IconIds.PROJECT_MISMATCHED),
                             presenter.NodeTreeIds.PACKAGES, 2, None,
                             presenter.ContextMenuIds.PROJECT, True),
    presenter.SetStatusLoadingCommand(4, 6),
    presenter.AddNodeCommand(6, "Installed archive", False,
                             presenter.Style(checkboxState=True,
                                             iconId=presenter.IconIds.INSTALLER_MATCHES),
                             presenter.NodeTreeIds.PACKAGES, None, 2,
                             presenter.ContextMenuIds.ARCHIVE, False),
    presenter.SetStatusLoadingCommand(5, 6),
    presenter.SetPackageContentsInfoCommand("Dummy info", True),
    presenter.SetGeneralTabInfoCommand(True, False, True, 123, 43, "2011 Aug 09", 21, 3,
                                       5, 2, 14, 0, 5, 0, 19, 0, 0, 0, 0, 0, 14, 0, 5, 0,
                                       19, None),
    presenter.SetDirtyTabInfoCommand([
        (presenter.AnnealOperationIds.COPY, 'Meshes/sampleMesh.nif'),
        (presenter.AnnealOperationIds.DELETE, 'neatoburrito.esp'),
        (presenter.AnnealOperationIds.OVERWRITE, 'Textures/sampleTex.dds')]),
    presenter.SetConflictsTabInfoCommand([
        (3, ['patchplugin.esp', 'Meshes/sampleMesh.nif']),
        (6, ['Textures/tex1.dds', 'Textures/tex2.dds', 'Textures/tex3.dds'])
        ]),
    presenter.SetFileListTabInfoCommand(presenter.DetailsTabIds.SELECTED, [
        ]),
    presenter.SetFileListTabInfoCommand(presenter.DetailsTabIds.UNSELECTED, []),
    presenter.SetFileListTabInfoCommand(presenter.DetailsTabIds.SKIPPED, ['readme.txt']),
    presenter.AddNodeCommand(4, "Hidden archive", False,
                             presenter.Style(
                                 foregroundColorId=presenter.ForegroundColorIds.DISABLED,
                                 checkboxState=False,
                                 iconId=presenter.IconIds.INSTALLER_UNINSTALLABLE),
                             presenter.NodeTreeIds.PACKAGES, 2, 3,
                             presenter.ContextMenuIds.ARCHIVE, False),
    presenter.SetStatusLoadingCommand(6, 6),
    presenter.SetStatusOkCommand(100, 1023, 24000, 3423, 123, 24000)
    ]

class MockPresenter:
    def __init__(self):
        self.viewCommandQueue = Queue.Queue()
        self._loaderThread = monitored_thread.MonitoredThread(name="MockPresenterLoader",
                                                              target=self._load_data)
    def start(self, initialDetailsTabId, initialFilterMask):
        _logger.debug("presenter starting; curDetailsTabId = %s; initialFilterMask = %s",
                      initialDetailsTabId, initialFilterMask)
        self._loaderThread.start()
    def pause(self):
        _logger.debug("presenter pausing")
    def resume(self):
        _logger.debug("presenter resuming")
    def shutdown(self):
        _logger.debug("presenter shutting down")
        self._loaderThread.join()
        self.viewCommandQueue.put(None)

    def set_filter_state(self, filterId, value):
        _logger.debug("setting filter %s to %s", filterId, value)
    def set_packages_tree_selections(self, nodeIds):
        _logger.debug("setting packages tree selection to nodes: %s", nodeIds)
    def set_files_tree_selections(self, nodeIds):
        _logger.debug("setting files tree selection to nodes %s", nodeIds)
    def set_details_tab_selection(self, detailsTabId):
        _logger.debug("setting details tab selection to %s", detailsTabId)
    def set_group_node_expanded(self, nodeId, value):
        _logger.debug("setting group node %d expansion to %s", nodeId, value)
    def set_dir_node_expanded(self, nodeId, value):
        _logger.debug("setting directory node %d expansion to %s", nodeId, value)
    def set_search_string(self, text):
        _logger.debug("setting search string to '%s'", text)

    def _load_data(self):
        _logger.debug("loader thread starting")
        for command in _commands:
            self.viewCommandQueue.put(command)
            time.sleep(0.5)


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
