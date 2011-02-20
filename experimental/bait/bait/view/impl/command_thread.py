# -*- coding: utf-8 -*-
#
# bait/view/impl/command_thread.py
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

import logging
import threading
import wx

from ... import presenter
from ...presenter import view_commands


_logger = logging.getLogger(__name__)
_packageFilterIds = frozenset((presenter.FILTER_ID_PACKAGES_HIDDEN, presenter.FILTER_ID_PACKAGES_INSTALLED, presenter.FILTER_ID_PACKAGES_NOT_INSTALLED))
_fileFilterIds = frozenset((presenter.FILTER_ID_FILES_PLUGINS, presenter.FILTER_ID_FILES_RESOURCES, presenter.FILTER_ID_FILES_OTHER))

class CommandThread(threading.Thread):
    def __init__(self, inCommandQueue, detailsTabMap, dataPanel, packageTree, fileTree, statusBox, projectInfoLabel, projectInfoTabs, fileInfo):
        threading.Thread.__init__(self, name="ViewCommand")
        self._inCommandQueue = inCommandQueue
        self._detailsTabMap = detailsTabMap
        self._dataPanel = dataPanel
        self._packageTree = packageTree
        self._fileTree = fileTree
        self._statusBox = statusBox
        self._projectInfoLabel = projectInfoLabel
        self._projectInfoTabs = projectInfoTabs
        self._fileInfo = fileInfo
        self._ignoreUpdates = False
        self._handlers = {}
        self._handlers[view_commands.ADD_GROUP] = self._add_package        
        self._handlers[view_commands.ADD_PACKAGE] = self._add_package
        self._handlers[view_commands.EXPAND_GROUP] = self._expand_group
        self._handlers[view_commands.EXPAND_DIR] = self._expand_dir
        self._handlers[view_commands.CLEAR_PACKAGES] = self._clear_packages
        self._handlers[view_commands.SET_FILTER_STATS] = self._set_filter_stats
        self._handlers[view_commands.STATUS_UPDATE] = self._update_status        
        self._handlers[view_commands.SET_PACKAGE_DETAILS] = self._update_package_details
        self._handlers[view_commands.SET_DATA_STATS] = self._set_data_stats
        self._handlers[view_commands.ADD_FILE] = self._add_file
        self._handlers[view_commands.CLEAR_FILES] = self._clear_files
        self._handlers[view_commands.SET_FILE_DETAILS] = self._update_file_details
        self._handlers[view_commands.SELECT_PACKAGES] = self._select_packages
        self._handlers[view_commands.SELECT_FILES] = self._select_files

    def set_ignore_updates(self, value):
        self._ignoreUpdates = value;
        
    def add_completion_callback(self):
        pass

    def run(self):
        _logger.debug("view command thread starting")
        # cache constant variables to avoid repetitive lookups
        inQueue = self._inCommandQueue
        handlerMap = self._handlers
        
        while True:
            viewCommand = inQueue.get()
            if viewCommand is None:
                _logger.debug("received sentinel value; view command thread exiting")
                break
            if self._ignoreUpdates:
                continue
            _logger.debug("received %s command" % viewCommand.__class__)
            handler = handlerMap.get(viewCommand.commandId)
            if handler is None:
                _logger.warn("unhandled %s command: %s", viewCommand.__class__, dir(viewCommand))
                continue
            # set a callback from the GUI thread so we can safely modify widget state
            wx.CallAfter(handler, viewCommand)

    def _add_tree_node(self, targetTree, addNodeCommand):
        foregroundColor = None
        checkboxState = None
        if not addNodeCommand.style is None:
            style = addNodeCommand.style
            checkboxState = style.checkboxState
            if not style.textColor is None:
                if style.textColor is view_commands.COLOR_GRAY:
                    foregroundColor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
                else:
                    _logger.warn("unhandled view_command color: %s" % style.textColor)
        targetTree.add_item(addNodeCommand.nodeId, addNodeCommand.label, addNodeCommand.parentNodeId, addNodeCommand.predecessorNodeId, foregroundColor, checkboxState)

    def _add_package(self, addPackageCommand):
        _logger.debug("adding package %d: %s", addPackageCommand.nodeId, addPackageCommand.label)
        self._add_tree_node(self._packageTree, addPackageCommand)

    def _add_file(self, addFileCommand):
        _logger.debug("adding file %d: %s", addFileCommand.nodeId, addFileCommand.label)
        self._add_tree_node(self._fileTree, addFileCommand)

    def _clear_packages(self, clearPackagesCommand):
        _logger.debug("clearing packages")
        self._packageTree.clear()

    def _clear_files(self, clearFilesCommand):
        _logger.debug("clearing files")
        self._fileTree.clear()

    def _select_packages(self, selectPackagesCommand):
        _logger.debug("selecting packages: %s", selectPackagesCommand.nodeIds)
        self._packageTree.select_items(selectPackagesCommand.nodeIds)

    def _select_files(self, selectFilesCommand):
        _logger.debug("selecting files: %s", selectFilesCommand.nodeIds)
        self._fileTree.select_items(selectFilesCommand.nodeIds)

    def _expand_group(self, expandGroupCommand):
        _logger.debug("expanding group %d", expandGroupCommand.nodeId)
        self._packageTree.expand_item(expandGroupCommand.nodeId)

    def _expand_dir(self, expandDirCommand):
        _logger.debug("expanding dir %d", expandDirCommand.nodeId)
        self._fileTree.expand_item(expandDirCommand.nodeId)

    def _set_filter_stats(self, setFilterStatsCommand):
        _logger.debug("setting filter %d stats to %d/%d", setFilterStatsCommand.filterId, setFilterStatsCommand.current, setFilterStatsCommand.total)
        if setFilterStatsCommand.filterId in _packageFilterIds:
            tree = self._packageTree
        elif setFilterStatsCommand.filterId in _fileFilterIds:
            tree = self._fileTree
        else:
            _logger.warn("filter stats set for unknown filterId: %d", setFilterStatsCommand.filterId)
            return
        tree.set_filter_stats(setFilterStatsCommand.filterId, setFilterStatsCommand.current, setFilterStatsCommand.total)

    def _set_data_stats(self, setDataStatsCommand):
        _logger.debug("setting data stats to %d/%d, %d/%d", setDataStatsCommand.activePlugins, setDataStatsCommand.totalPlugins, setDataStatsCommand.knownFiles, setDataStatsCommand.totalFiles)
        self._dataPanel.set_stats(setDataStatsCommand.activePlugins, setDataStatsCommand.totalPlugins, setDataStatsCommand.knownFiles, setDataStatsCommand.totalFiles)

    def _update_status(self, statusUpdateCommand):
        _logger.debug("updating status: '%s'", statusUpdateCommand.text)
        self._statusBox.AppendText("\n")
        self._statusBox.AppendText(statusUpdateCommand.text)
        
    def _update_package_details(self, setPackageDetailsCommand):
        _logger.debug("setting package details")
        if not setPackageDetailsCommand.label is None:
            self._projectInfoLabel.SetLabel(setPackageDetailsCommand.label)
        textCtrl = self._projectInfoTabs.GetCurrentPage()
        if setPackageDetailsCommand.text is None:
            textCtrl.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
            textCtrl.SetValue("No package selected")
        elif len(setPackageDetailsCommand.text) is 0:
            textCtrl.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
            textCtrl.SetValue("None")
        else:
            textCtrl.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT))
            textCtrl.SetValue(setPackageDetailsCommand.text)

    def _update_file_details(self, setFileDetailsCommand):
        _logger.debug("setting file details")
        if setFileDetailsCommand.text is None:
            self._fileInfo.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
            self._fileInfo.SetValue("No file selected")
        elif len(setFileDetailsCommand.text) is 0:
            self._fileInfo.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
            self._fileInfo.SetValue("None")
        else:
            self._fileInfo.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT))
            self._fileInfo.SetValue(setFileDetailsCommand.text)
