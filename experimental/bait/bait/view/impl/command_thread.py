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
_packageInfoFilterIds = frozenset((presenter.FILTER_ID_DIRTY_ADD, presenter.FILTER_ID_DIRTY_UPDATE, presenter.FILTER_ID_DIRTY_DELETE, presenter.FILTER_ID_CONFLICTS_SELECTED, presenter.FILTER_ID_CONFLICTS_UNSELECTED, presenter.FILTER_ID_CONFLICTS_ACTIVE, presenter.FILTER_ID_CONFLICTS_INACTIVE, presenter.FILTER_ID_CONFLICTS_HIGHER, presenter.FILTER_ID_CONFLICTS_LOWER, presenter.FILTER_ID_SELECTED_MATCHED, presenter.FILTER_ID_SELECTED_MISMATCHED, presenter.FILTER_ID_SELECTED_OVERRIDDEN, presenter.FILTER_ID_SELECTED_MISSING, presenter.FILTER_ID_UNSELECTED_MATCHED, presenter.FILTER_ID_UNSELECTED_MISMATCHED, presenter.FILTER_ID_UNSELECTED_OVERRIDDEN, presenter.FILTER_ID_UNSELECTED_MISSING, presenter.FILTER_ID_SKIPPED_NONGAME, presenter.FILTER_ID_SKIPPED_MASKED))


class CommandThread(threading.Thread):
    def __init__(self, inCommandQueue, statusPanel, packageTree, fileTree, packageInfoPanel, fileInfo):
        threading.Thread.__init__(self, name="ViewCommand")
        self._inCommandQueue = inCommandQueue
        self._statusPanel = statusPanel
        self._packageTree = packageTree
        self._fileTree = fileTree
        self._packageInfoPanel = packageInfoPanel
        self._fileInfo = fileInfo
        self._ignoreUpdates = False
        self._colorMap = None
        self._handlers = {}
        self._handlers[view_commands.ADD_GROUP] = self._add_package        
        self._handlers[view_commands.ADD_PACKAGE] = self._add_package
        self._handlers[view_commands.EXPAND_GROUP] = self._expand_group
        self._handlers[view_commands.EXPAND_DIR] = self._expand_dir
        self._handlers[view_commands.CLEAR_PACKAGES] = self._clear_packages
        self._handlers[view_commands.SET_FILTER_STATS] = self._set_filter_stats
        self._handlers[view_commands.SET_STATUS] = self._set_status        
        self._handlers[view_commands.SET_PACKAGE_LABEL] = self._set_package_label
        self._handlers[view_commands.ADD_FILE] = self._add_file
        self._handlers[view_commands.CLEAR_FILES] = self._clear_files
        self._handlers[view_commands.SET_FILE_DETAILS] = self._update_file_details
        self._handlers[view_commands.SELECT_PACKAGES] = self._select_packages
        self._handlers[view_commands.SELECT_FILES] = self._select_files
        self._handlers[view_commands.SET_STYLE_MAPS] = self._set_style_maps
        self._handlers[view_commands.SET_PACKAGE_INFO] = self._set_package_info

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

    def _set_style_maps(self, setStyleMapsCommand):
        _logger.debug("setting color map: %s; unchecked icon map: %s; checked icon map: %s", setStyleMapsCommand.colorMap, setStyleMapsCommand.uncheckedIconMap, setStyleMapsCommand.checkedIconMap)
        colorMap = setStyleMapsCommand.colorMap
        self._colorMap = dict((key, wx.Color(*colorMap[key])) for key in colorMap)
        self._packageTree.set_checkbox_images(setStyleMapsCommand.checkedIconMap, setStyleMapsCommand.uncheckedIconMap)

    def _add_tree_node(self, targetTree, addNodeCommand):
        isBold = False
        isItalics = False
        textColor = None
        hilightColor = None
        checkboxState = None
        iconId = None
        style = addNodeCommand.style
        if not style is None:
            checkboxState = style.checkboxState
            iconId = style.iconId
            if not style.textColorId is None:
                textColor = self._colorMap[style.textColorId]
                if textColor is None: _logger.warn("unhandled color id: %s" % style.textColorId)
            if not style.hilightColorId is None:
                hilightColor = self._colorMap[style.hilightColorId]
                if hilightColor is None: _logger.warn("unhandled color id: %s" % style.hilightColorId)
            if not style.fontStyleMask is None:
                isBold = not style.fontStyleMask & view_commands.FONT_STYLE_BOLD_FLAG is 0
                isItalics = not style.fontStyleMask & view_commands.FONT_STYLE_ITALICS_FLAG is 0
        targetTree.add_item(addNodeCommand.nodeId, addNodeCommand.label, addNodeCommand.parentNodeId, addNodeCommand.predecessorNodeId, isBold, isItalics, textColor, hilightColor, checkboxState, iconId)

    def _add_package(self, addPackageCommand):
        _logger.debug("adding package %d: '%s'", addPackageCommand.nodeId, addPackageCommand.label)
        self._add_tree_node(self._packageTree, addPackageCommand)

    def _add_file(self, addFileCommand):
        _logger.debug("adding file %d: '%s'", addFileCommand.nodeId, addFileCommand.label)
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
        filterId = setFilterStatsCommand.filterId
        # TODO: dict lookup
        if filterId in _packageFilterIds: target = self._packageTree
        elif filterId in _fileFilterIds: target = self._fileTree
        elif filterId in _packageInfoFilterIds: target = self._packageInfoPanel
        else:
            _logger.warn("filter stats set for unknown filterId: %d", filterId)
            return
        target.set_filter_stats(setFilterStatsCommand.filterId, setFilterStatsCommand.current, setFilterStatsCommand.total)

    def _set_data_stats(self, setDataStatsCommand):
        _logger.debug("setting data stats to %d/%d, %d/%d", setDataStatsCommand.activePlugins, setDataStatsCommand.totalPlugins, setDataStatsCommand.knownFiles, setDataStatsCommand.totalFiles)
        self._statusPanel.set_data_stats(setDataStatsCommand.activePlugins, setDataStatsCommand.totalPlugins, setDataStatsCommand.knownFiles, setDataStatsCommand.totalFiles)

    def _set_status(self, setStatusCommand):
        status = setStatusCommand.status
        _logger.debug("setting status to: '%s'", status)
        hilightColor = self._colorMap[setStatusCommand.hilightColorId]
        if status is view_commands.STATUS_OK:
            self._statusPanel.set_ok_status(hilightColor, setStatusCommand.activePlugins, setStatusCommand.totalPlugins, setStatusCommand.knownFiles, setStatusCommand.totalFiles)
        elif status is view_commands.STATUS_LOADING:
            self._statusPanel.set_loading_status(hilightColor, setStatusCommand.loadingComplete, setStatusCommand.loadingTotal)
        elif status is view_commands.STATUS_NEEDS_ANNEALING:
            self._statusPanel.set_dirty_status(hilightColor)
        elif status is view_commands.STATUS_DOING_IO:
            self._statusPanel.set_io_status(hilightColor, setStatusCommand.ioOperations)
        else:
            _logger.warn("unknown status: %d", status)
        
    def _set_package_label(self, setPackageLabelCommand):
        _logger.debug("setting package label to '%s'", setPackageLabelCommand.text)
        self._packageInfoPanel.set_label(setPackageLabelCommand.text)

    def _set_package_info(self, setPackageInfoCommand):
        _logger.debug("setting package info for tab %d", setPackageInfoCommand.tabId)
        self._packageInfoPanel.set_tab_data(setPackageInfoCommand.tabId, setPackageInfoCommand.data)

    def _update_file_details(self, setFileDetailsCommand):
        _logger.debug("setting file details")
        if setFileDetailsCommand.text is None:
            self._fileInfo.SetForegroundColour(self._colorMap[view_commands.TEXT_DISABLED])
            self._fileInfo.SetValue("No file selected")
        elif len(setFileDetailsCommand.text) is 0:
            self._fileInfo.SetForegroundColour(self._colorMap[view_commands.TEXT_DISABLED])
            self._fileInfo.SetValue("None")
        else:
            self._fileInfo.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT))
            self._fileInfo.SetValue(setFileDetailsCommand.text)
