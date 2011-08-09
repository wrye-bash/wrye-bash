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
from impl import data_fetcher, diff_engine, widget_manager, update_dispatcher


_logger = logging.getLogger(__name__)


class BaitPresenter:
    def __init__(self, model_, presenterIoGateway, viewCommandQueue):
        """don't start threads here since we may be initialized in a different process
        from where we're started"""
        self.viewCommandQueue = viewCommandQueue
        self._model = model_
        self._stateManager = stateManager
        # TODO: is it better to initialize these in start()?
        #self._colorsAndIcons = colors_and_icons.ColorsAndIcons(self._stateManager)
        self._dataFetcher = data_fetcher.DataFetcher(model_)
        # TODO: add other widget managers as they are implemented
        self._generalTabManager = widget_manager.GeneralTabWidgetManager()
        self._packageContentsManager = widget_manager.PackageContentsTreeWidgetManager()
        self._packagesTreeDiffEngine = diff_engine.PackagesTreeDiffEngine(
            self._generalTabManager, self._packageContentsManager, viewCommandQueue)
        self._packagesTreeManager = widget_manager.PackagesTreeWidgetManager(
            self._dataFetcher, self._packagesTreeDiffEngine)
        self._managers = [self._packagesTreeManager]
        self._filteringManagers = [self._packagesTreeManager]
        self._updateDispatcher = update_dispatcher.UpdateDispatcher(
            model_.updateNotificationQueue, viewCommandQueue, self._managers)
        self._filterMask = presenter.FilterIds.NONE

    def start(self, initialDetailsTabId, initialFilterMask):
        _logger.debug("presenter starting; curDetailsTabId = %s; initialFilterMask = %s",
                      curDetailsTabId, initialFilterMask)
        self._filterMask = initialFilterMask
        _logger.debug("starting subcomponents")
        try:
            self._model.start()
            self._dataFetcher.start()
            self._packagesTreeManager.start()
            self._updateDispatcher.start()
            for manager in self._filteringManagers:
                manager.handle_filter_update(initialFilterMask)
        except:
            self.shutdown()
            raise
        #self.viewCommandQueue.put(self._colorsAndIcons.get_set_style_maps_command())
        #self.viewCommandQueue.put(view_commands.SetStatus(
        #    view_commands.STATUS_LOADING, view_commands.HIGHLIGHT_LOADING,
        #    loadingComplete=0, loadingTotal=100))
        #self._curDetailsTab = curDetailsTabId
        #self.set_packages_tree_selections([])
        #self.set_files_tree_selections([])
        #self.viewCommandQueue.put(view_commands.SetPackageInfo(
        #    presenter.DETAILS_TAB_ID_GENERAL, None))

    def pause(self):
        _logger.debug("presenter pausing")
        self._model.pause()

    def resume(self):
        _logger.debug("presenter resuming")
        self._model.resume()

    def shutdown(self):
        _logger.debug("presenter shutting down")
        try: self._updateDispatcher.shutdown_output()
        except: _logger.exception("exception while shutting down dispatcher output")
        try: self._dataFetcher.shutdown()
        except:  _logger.exception("exception while shutting down data fetcher")
        try: self._packagesTreeManager.shutdown()
        except:  _logger.exception("exception while shutting down packages tree manager")
        try: self._model.shutdown()
        except:  _logger.exception("exception while shutting down model")
        try: self._updateDispatcher.shutdown_input()
        except:  _logger.exception("exception while shutting down dispatcher input")
        self.viewCommandQueue.put(None)

    def set_filter_state(self, filterId, value):
        if (filterId in self._filterMask) is value:
            _logger.debug("filter %d already set to %s; ignoring", filterId, value)
            return
        _logger.debug("setting filter %d to %s", filterId, value)
        self._filterMask ^= filterId
        for manager in self._filteringManagers:
            manager.handle_filter_update(self._filterMask)

    def set_packages_tree_selections(self, nodeIds, saveSelections=True):
        _logger.debug(
            "setting packages tree selection to node(s) %s, saveSelections=%s",
            nodeIds, saveSelections)
        self._packagesTreeManager.handle_selection_update(nodeIds)
        #self.viewCommandQueue.put(view_commands.ClearFiles())
        #if saveSelections:
            #self._selectedPackages = nodeIds
        #numNodeIds = len(nodeIds)
        #if numNodeIds is 1:
            ## TODO: populate UI elements for selected package in background
            #pass
        #elif numNodeIds is 0:
            #self.viewCommandQueue.put(view_commands.SetPackageLabel(None))
        #else:
            #self.viewCommandQueue.put(view_commands.SetPackageLabel(""))

    def set_files_tree_selections(self, nodeIds, saveSelections=True):
        _logger.debug("setting files tree selection to node(s) %s", nodeIds)
        #if saveSelections:
            #self._selectedFiles = nodeIds
        #numNodeIds = len(nodeIds)
        #if numNodeIds is 1:
            ## TODO: fetch file details from model in background and update UI
            #pass
        #else:
            #self.viewCommandQueue.put(view_commands.SetFileDetails(None))

    def set_details_tab_selection(self, detailsTabId):
        _logger.debug("setting details tab selection to %d", detailsTabId)
        #self._curDetailsTab = detailsTabId
        #numSelectedPackages = len(self._selectedPackages)
        #if numSelectedPackages is 0:
            #self.viewCommandQueue.put(view_commands.SetPackageInfo(detailsTabId, None))
        #elif numSelectedPackages is 1:
            ## TODO: fetch data, filter, and update UI in background
            #pass

    def set_group_node_expanded(self, nodeId, value):
        _logger.debug("setting group node %d expansion to %s", nodeId, value)
        self._packagesTreeManager.handle_expansion_update(nodeId, value)

    def set_dir_node_expanded(self, nodeId, value):
        _logger.debug("setting directory node %d expansion to %s", nodeId, value)

    def set_search_string(self, text):
        _logger.debug("setting search string '%s'", text)
        self._packagesTreeManager.handle_search_update(text)
