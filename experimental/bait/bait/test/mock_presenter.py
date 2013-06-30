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
from ..presenter.impl import colors_and_icons
from ..util import monitored_thread


_logger = logging.getLogger(__name__)

_commands = [
    presenter.SetStyleMapsCommand(
            colors_and_icons._foregroundColorMap, colors_and_icons._highlightColorMap,
            colors_and_icons._checkedIconMap, colors_and_icons._uncheckedIconMap),
    presenter.SetStatusLoadingCommand(0, 6),
    presenter.AddNodeCommand(presenter.NodeTreeIds.PACKAGES, 1, "Installed Data", False,
                             presenter.Style(), None, None,
                             presenter.ContextMenuIds.INSTALLED_DATA, False),
    presenter.SetStatusLoadingCommand(1, 6),
    presenter.AddNodeCommand(presenter.NodeTreeIds.PACKAGES, 5,
                             "Uninstalled archive with wizard", False,
                             presenter.Style(
                                 checkboxState=False,
                                 iconId=presenter.IconIds.PROJECT_MISSING_WIZ),
                             None, 1, presenter.ContextMenuIds.ARCHIVE, False),
    presenter.SetStatusLoadingCommand(2, 6),
    presenter.AddNodeCommand(presenter.NodeTreeIds.PACKAGES, 2, "Group of packages", True,
                             presenter.Style(), None, 5,
                             presenter.ContextMenuIds.GROUP, False),
    presenter.SetStatusLoadingCommand(3, 6),
    presenter.AddNodeCommand(presenter.NodeTreeIds.PACKAGES, 3,
                             "Installed, prehighlighted project", False,
                             presenter.Style(checkboxState=True,
                                             iconId=presenter.IconIds.PROJECT_MISMATCHED),
                             2, None, presenter.ContextMenuIds.PROJECT, True),
    presenter.SetStatusLoadingCommand(4, 6),
    presenter.AddNodeCommand(presenter.NodeTreeIds.PACKAGES, 6, "Installed archive",
                             False,
                             presenter.Style(checkboxState=True,
                                             iconId=presenter.IconIds.INSTALLER_MATCHES),
                             None, 2, presenter.ContextMenuIds.ARCHIVE, False),
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
    presenter.AddNodeCommand(presenter.NodeTreeIds.PACKAGES, 4, "Hidden archive", False,
                             presenter.Style(
                                 foregroundColorId=presenter.ForegroundColorIds.DISABLED,
                                 checkboxState=False,
                                 iconId=presenter.IconIds.INSTALLER_UNINSTALLABLE),
                             2, 3, presenter.ContextMenuIds.ARCHIVE, False),
    presenter.SetStatusLoadingCommand(6, 6),
    presenter.AddNodeCommand(
        presenter.NodeTreeIds.PACKAGES, 6,
        "Package with very long name to test tooltips when name is wider than the tree",
        False, presenter.Style(checkboxState=True,
                               iconId=presenter.IconIds.INSTALLER_MATCHES_WIZ),
        2, 4, presenter.ContextMenuIds.ARCHIVE, False),
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
