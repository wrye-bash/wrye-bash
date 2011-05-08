# -*- coding: utf-8 -*-
#
# bait/presenter/bait_presenter.py
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

from .. import presenter
from . import view_commands
from impl import colors_and_icons, update_monitor


_logger = logging.getLogger(__name__)


class BaitPresenter:
    def __init__(self, model, viewCommandQueue, stateManager=None):
        self.viewCommandQueue = viewCommandQueue
        self._model = model
        self._stateManager = stateManager
        self._updateMonitorThread = None
        self._colorsAndIcons = None
        self._filterMask = 0
        self._groupExpansionStates = {}
        self._dirExpansionStates = {}
        self._curDetailsTab = 0
        self._selectedPackages = []
        self._selectedFiles = []
        self._searchString = None

    def start(self, curDetailsTabId, filterStateMap):
        _logger.debug("presenter starting")
        self._colorsAndIcons = colors_and_icons.ColorsAndIcons(self._stateManager)
        self.viewCommandQueue.put(self._colorsAndIcons.get_set_style_maps_command())
        self.viewCommandQueue.put(view_commands.SetStatus(
            view_commands.STATUS_LOADING, view_commands.HIGHLIGHT_LOADING,
            loadingComplete=0, loadingTotal=100))
        self._curDetailsTab = curDetailsTabId
        for filterId, value in filterStateMap.iteritems():
            _logger.debug("initializing filter %d to %s", filterId, value)
            self._filterMask |= filterId
        self.set_packages_tree_selections([])
        self.set_files_tree_selections([])
        self.viewCommandQueue.put(view_commands.SetPackageInfo(
            presenter.DETAILS_TAB_ID_GENERAL, None))
        self._model.start()
        self._updateMonitorThread = update_monitor.UpdateMonitor(self._model.updateQueue)
        self._updateMonitorThread.start()

    def pause(self):
        _logger.debug("presenter pausing")
        self._model.pause()

    def resume(self):
        _logger.debug("presenter resuming")
        self._model.resume()

    def shutdown(self):
        _logger.debug("presenter shutting down")
        self._model.shutdown()
        # TODO: join the update reading thread
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
        # TODO: apply filter and send UI commands in another thread

    def set_packages_tree_selections(self, nodeIds, saveSelections=True):
        _logger.debug(
            "setting packages tree selection to node(s) %s, saveSelections=%s",
            nodeIds, saveSelections)
        self.viewCommandQueue.put(view_commands.ClearFiles())
        if saveSelections:
            self._selectedPackages = nodeIds
        numNodeIds = len(nodeIds)
        if numNodeIds is 1:
            # TODO: populate UI elements for selected package in background
            pass
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
            # TODO: fetch file details from model in background and update UI
            pass
        else:
            self.viewCommandQueue.put(view_commands.SetFileDetails(None))

    def set_details_tab_selection(self, detailsTabId):
        _logger.debug("setting details tab selection to %d", detailsTabId)
        self._curDetailsTab = detailsTabId
        numSelectedPackages = len(self._selectedPackages)
        if numSelectedPackages is 0:
            self.viewCommandQueue.put(view_commands.SetPackageInfo(detailsTabId, None))
        elif numSelectedPackages is 1:
            # TODO: fetch data, filter, and update UI in background
            pass

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
        # TODO: apply search filter in background
        self._searchString = text
