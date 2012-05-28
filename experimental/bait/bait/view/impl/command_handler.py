# -*- coding: utf-8 -*-
#
# bait/view/impl/command_handler.py
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
import operator
import threading
import wx

from . import message_manager
from ... import presenter
from ...util import monitored_thread, process_monitor


_logger = logging.getLogger(__name__)


class CommandHandler:
    def __init__(self, inCommandQueue, filterRegistry, installerTab,
                 imageLoader, maxPendingEvents=50,
                 messageManager=message_manager.MesssageManager(),
                 callAfterFn=wx.CallAfter):
        self._inCommandQueue = inCommandQueue
        self._filterRegistry = filterRegistry
        self._installerTab = installerTab
        self._imageLoader = imageLoader
        self._maxPendingEvents = maxPendingEvents
        self._messageManager = messageManager
        self._callAfterFn = callAfterFn
        self._throttleSemaphore = threading.Semaphore(0)
        self._ignoreUpdates = False
        self._foregroundColorMap = {}
        self._highlightColorMap = {}
        self._curImageFileHandle = None
        self._started = False
        self._frequencyStats = {}
        self._commandThread = monitored_thread.MonitoredThread(name="CommandHandler",
                                                               target=self._run)
        self._handlers = {}
        self._handlers[presenter.CommandIds.SET_GLOBAL_SETTINGS] = \
            self._set_global_settings
        self._handlers[presenter.CommandIds.SET_PACKAGE_CONTENTS_INFO] = \
            self._set_package_contents_info
        self._handlers[presenter.CommandIds.SET_STATUS_OK] = self._set_status_ok
        self._handlers[presenter.CommandIds.SET_STATUS_DIRTY] = self._set_status_dirty
        self._handlers[presenter.CommandIds.SET_STATUS_LOADING] = self._set_status_loading
        self._handlers[presenter.CommandIds.SET_STATUS_IO] = self._set_status_io
        self._handlers[presenter.CommandIds.SET_STYLE_MAPS] = self._set_style_maps
        self._handlers[presenter.CommandIds.UPDATE_NODE] = self._update_node
        self._handlers[presenter.CommandIds.ADD_NODE] = self._add_node
        self._handlers[presenter.CommandIds.MOVE_NODE] = self._move_node
        self._handlers[presenter.CommandIds.REMOVE_NODE] = self._remove_node
        self._handlers[presenter.CommandIds.CLEAR_TREE] = self._clear_tree
        self._handlers[presenter.CommandIds.SET_FILTER_STATS] = self._set_filter_stats
        self._handlers[presenter.CommandIds.SET_GENERAL_TAB_INFO] = \
            self._set_general_tab_info
        self._handlers[presenter.CommandIds.SET_DIRTY_TAB_INFO] = self._set_dirty_tab_info
        self._handlers[presenter.CommandIds.SET_CONFLICTS_TAB_INFO] = \
            self._set_conflicts_tab_info
        self._handlers[presenter.CommandIds.SET_FILE_LIST_TAB_INFO] = \
            self._set_file_list_tab_info
        self._handlers[presenter.CommandIds.DISPLAY_ERROR] = self._display_error
        self._handlers[presenter.CommandIds.ASK_CONFIRMATION] = self._ask_confirmation
        self._handlers[presenter.CommandIds.EXTENDED] = self._extended

    def start(self):
        self._commandThread.start()
        self._started = True
        process_monitor.register_statistics_callback(self._dump_stats)

    def shutdown(self):
        process_monitor.unregister_statistics_callback(self._dump_stats)
        # wait for presenter to send sentinel flag
        if self._started:
            # unblock thread if it is blocked
            self._throttleSemaphore.release()
            self._commandThread.join()
            self._started = False

    def set_ignore_updates(self):
        self._ignoreUpdates = True;

    def _run(self):
        _logger.debug("view command handler thread starting")
        # cache constant variables to avoid repetitive lookups
        inQueue = self._inCommandQueue
        handlerMap = self._handlers
        maxPendingEvents = self._maxPendingEvents
        frequencyStats = self._frequencyStats
        callAfterFn = self._callAfterFn
        throttleSemaphore = self._throttleSemaphore
        syncCountdown = maxPendingEvents
        try:
            while True:
                viewCommand = inQueue.get()
                if viewCommand is None:
                    _logger.debug("received sentinel value; command handler exiting")
                    inQueue.task_done()
                    break
                if self._ignoreUpdates:
                    inQueue.task_done()
                    continue
                _logger.debug("received %s command", viewCommand.__class__)
                if not hasattr(viewCommand, "commandId"):
                    _logger.warn("non-command retrieved from command queue: %s",
                                 viewCommand)
                    inQueue.task_done()
                    continue
                commandId = viewCommand.commandId
                handler = handlerMap.get(commandId)
                if handler is None:
                    _logger.warn("unhandled %s command: %s",
                                 viewCommand.__class__, viewCommand)
                    inQueue.task_done()
                    continue
                # keep frequency statistics
                commandName = commandId.name
                if commandName in frequencyStats:
                    frequencyStats[commandName] = frequencyStats[commandName] + 1
                else:
                    frequencyStats[commandName] = 1
                # enqueue a callback from the GUI thread so we can safely modify widgets
                callAfterFn(handler, viewCommand)
                inQueue.task_done()
                # every maxPendingEvents, ensure we're not overloading the wx event queue
                syncCountdown -= 1
                if 0 >= syncCountdown:
                    syncCountdown = maxPendingEvents
                    # don't enqueue any more events until this call makes it all the way
                    # through the queue
                    callAfterFn(throttleSemaphore.release)
                    _logger.debug("flushing wx event queue")
                    throttleSemaphore.acquire()
                    _logger.debug("continuing")
        except:
            _logger.error("error in command handler:", exc_info=True)
            inQueue.task_done()

    def _dump_stats(self, logFn):
        logFn("command frequencies: %s", sorted(self._frequencyStats.iteritems(),
                                                key=operator.itemgetter(1),
                                                reverse=True))

    def _set_global_settings(self, setGlobalSettingsCommand):
        _logger.debug("setting global settings: %s", setGlobalSettingsCommand)
        self._installerTab.globalSettingsButton.set_settings(
            setGlobalSettingsCommand.rememberTreeExpansionState,
            setGlobalSettingsCommand.skipDistantLod,
            setGlobalSettingsCommand.skipLodMeshes,
            setGlobalSettingsCommand.skipLodNormals,
            setGlobalSettingsCommand.skipLodTextures,
            setGlobalSettingsCommand.skipVoices)

    def _set_package_contents_info(self, setPackageContentsInfoCommand):
        _logger.debug("setting package contents info: %s", setPackageContentsInfoCommand)
        self._installerTab.packageContentsPanel.reset(
            setPackageContentsInfoCommand.title,
            setPackageContentsInfoCommand.enabled,
            setPackageContentsInfoCommand.skipDistantLod,
            setPackageContentsInfoCommand.skipLodMeshes,
            setPackageContentsInfoCommand.skipLodNormals,
            setPackageContentsInfoCommand.skipLodTextures,
            setPackageContentsInfoCommand.skipVoices)
        self._curImageFileHandle = None

    def _set_status_ok(self, setStatusOkCommand):
        _logger.debug("setting status to OK: %s", setStatusOkCommand)
        highlightColor = self._highlightColorMap.get(presenter.HighlightColorIds.OK)
        self._installerTab.statusPanel.set_ok(highlightColor,
            setStatusOkCommand.numInstalledFiles, setStatusOkCommand.numLibraryFiles,
            setStatusOkCommand.installedMb, setStatusOkCommand.libraryMb,
            setStatusOkCommand.freeInstalledMb, setStatusOkCommand.freeLibraryMb)

    def _set_status_dirty(self, setStatusDirtyCommand):
        _logger.debug("setting status to DIRTY: %s", setStatusDirtyCommand)
        highlightColor = self._highlightColorMap.get(presenter.HighlightColorIds.DIRTY)
        self._installerTab.statusPanel.set_dirty(
            highlightColor, setStatusDirtyCommand.dirtyPackageNodeIds,
            self._installerTab.packagesTree.nodeIdToLabelMap)

    def _set_status_loading(self, setStatusLoadingCommand):
        _logger.debug("setting status to LOADING: %s", setStatusLoadingCommand)
        highlightColor = self._highlightColorMap.get(presenter.HighlightColorIds.LOADING)
        self._installerTab.statusPanel.set_loading(
            highlightColor,
            setStatusLoadingCommand.progressComplete,
            setStatusLoadingCommand.progressTotal)

    def _set_status_io(self, setStatusIoCommand):
        _logger.debug("setting status to IO: %s", setStatusIoCommand)
        highlightColor = self._highlightColorMap.get(presenter.HighlightColorIds.ERROR)
        self._installerTab.statusPanel.set_doing_io(
            highlightColor,
            setStatusIoCommand.packageOperationInfos)

    def _set_style_maps(self, setStyleMapsCommand):
        _logger.debug("setting style maps: %s", setStyleMapsCommand)
        colorMap = setStyleMapsCommand.foregroundColorMap
        self._foregroundColorMap = dict(
            (key, wx.Color(*colorMap[key])) for key in colorMap)
        colorMap = setStyleMapsCommand.highlightColorMap
        self._highlightColorMap = dict(
            (key, wx.Color(*colorMap[key])) for key in colorMap)
        self._installerTab.packagesTree.set_checkbox_images(
            setStyleMapsCommand.checkedIconMap, setStyleMapsCommand.uncheckedIconMap)

    def _process_style(self, style):
        isBold = False
        isItalics = False
        textColor = None
        highlightColor = None
        checkboxState = None
        iconId = None
        if style is not None:
            checkboxState = style.checkboxState
            iconId = style.iconId
            if style.foregroundColorId is not None:
                textColor = self._foregroundColorMap.get(style.foregroundColorId)
                if textColor is None:
                    _logger.warn("unhandled color id: %s", style.foregroundColorId)
            if style.highlightColorId is not None:
                highlightColor = self._highlightColorMap.get(style.highlightColorId)
                if highlightColor is None:
                    _logger.warn("unhandled color id: %s", style.highlightColorId)
            if style.fontStyleMask is not None:
                isBold = style.fontStyleMask & presenter.FontStyleIds.BOLD != 0
                isItalics = style.fontStyleMask & presenter.FontStyleIds.ITALICS != 0
        return (isBold, isItalics, textColor, highlightColor, checkboxState, iconId)

    def _get_tree(self, nodeTreeId):
        if presenter.NodeTreeIds.PACKAGES == nodeTreeId:
            return self._installerTab.packagesTree
        elif presenter.NodeTreeIds.CONTENTS == nodeTreeId:
            return self._installerTab.packageContentsPanel.packageContentsTree
        raise RuntimeError("unhandled node tree id: %s" % nodeTreeId)

    def _update_node(self, updateNodeCommand):
        _logger.debug("updating node: %s", updateNodeCommand)
        self._get_tree(updateNodeCommand.nodeTreeId).update_node(
            updateNodeCommand.nodeId, updateNodeCommand.label,
            updateNodeCommand.isExpanded, *self._process_style(updateNodeCommand.style))

    def _add_node(self, addNodeCommand):
        _logger.debug("adding node: %s", addNodeCommand)
        self._get_tree(addNodeCommand.nodeTreeId).add_node(
            addNodeCommand.nodeId, addNodeCommand.label, addNodeCommand.isExpanded,
            addNodeCommand.parentNodeId, addNodeCommand.predecessorNodeId,
            addNodeCommand.contextMenuId, addNodeCommand.isSelected,
            *self._process_style(addNodeCommand.style))

    def _move_node(self, moveNodeCommand):
        _logger.debug("moving node: %s", moveNodeCommand)
        self._get_tree(moveNodeCommand.nodeTreeId).move_node(
            moveNodeCommand.nodeId, moveNodeCommand.predecessorNodeId)

    def _remove_node(self, removeNodeCommand):
        _logger.debug("removing node: %s", removeNodeCommand)
        self._get_tree(removeNodeCommand.nodeTreeId).remove_node(removeNodeCommand.nodeId)

    def _clear_tree(self, clearTreeCommand):
        _logger.debug("clearing tree: %s", clearTreeCommand)
        self._get_tree(clearTreeCommand.nodeTreeId).clear()

    def _set_filter_stats(self, setFilterStatsCommand):
        _logger.debug("setting filter stats: %s", setFilterStatsCommand)
        self._filterRegistry.set_filter_stats(setFilterStatsCommand.filterId,
                                              setFilterStatsCommand.current,
                                              setFilterStatsCommand.total)

    def _set_general_tab_info(self, setGeneralTabInfoCommand):
        _logger.debug("setting general tab info: %s", setGeneralTabInfoCommand)
        self._installerTab.packageContentsPanel.set_general_tab_info(
            setGeneralTabInfoCommand.isArchive, setGeneralTabInfoCommand.isHidden,
            setGeneralTabInfoCommand.isInstalled, setGeneralTabInfoCommand.packageBytes,
            setGeneralTabInfoCommand.selectedBytes,
            setGeneralTabInfoCommand.lastModifiedTimestamp,
            setGeneralTabInfoCommand.numFiles,
            setGeneralTabInfoCommand.numDirty,
            setGeneralTabInfoCommand.numOverridden,
            setGeneralTabInfoCommand.numSkipped,
            setGeneralTabInfoCommand.numSelectedMatched,
            setGeneralTabInfoCommand.numSelectedMismatched,
            setGeneralTabInfoCommand.numSelectedOverridden,
            setGeneralTabInfoCommand.numSelectedMissing,
            setGeneralTabInfoCommand.numTotalSelected,
            setGeneralTabInfoCommand.numUnselectedMatched,
            setGeneralTabInfoCommand.numUnselectedMismatched,
            setGeneralTabInfoCommand.numUnselectedOverridden,
            setGeneralTabInfoCommand.numUnselectedMissing,
            setGeneralTabInfoCommand.numTotalUnselected,
            setGeneralTabInfoCommand.numTotalMatched,
            setGeneralTabInfoCommand.numTotalMismatched,
            setGeneralTabInfoCommand.numTotalOverridden,
            setGeneralTabInfoCommand.numTotalMissing,
            setGeneralTabInfoCommand.numTotalSelectable)
        imageFileHandle = setGeneralTabInfoCommand.imageFileHandle
        # if the general tab image has changed, asynchronously load the image
        if imageFileHandle != self._curImageFileHandle:
            self._installerTab.packageContentsPanel.set_general_tab_image(None)
            self._curImageFileHandle = imageFileHandle
            self._imageLoader.load_image(imageFileHandle)

    def _set_dirty_tab_info(self, setDirtyTabInfoCommand):
        _logger.debug("setting dirty tab info: %s", setDirtyTabInfoCommand)
        self._installerTab.packageContentsPanel.set_dirty_tab_info(
            setDirtyTabInfoCommand.annealOperations)

    def _set_conflicts_tab_info(self, setConflictsTabInfoCommand):
        _logger.debug("setting conflicts tab info: %s", setConflictsTabInfoCommand)
        self._installerTab.packageContentsPanel.set_conflicts_tab_info(
            setConflictsTabInfoCommand.conflictLists,
            self._installerTab.packagesTree.nodeIdToLabelMap)

    def _set_file_list_tab_info(self, setFileListTabInfoCommand):
        _logger.debug("setting file list tab info: %s", setFileListTabInfoCommand)
        packageContentsPanel = self._installerTab.packageContentsPanel
        detailsTabId = setFileListTabInfoCommand.detailsTabId
        if presenter.DetailsTabIds.SELECTED == detailsTabId:
            packageContentsPanel.set_selected_tab_info(setFileListTabInfoCommand.paths)
        elif presenter.DetailsTabIds.UNSELECTED == detailsTabId:
            packageContentsPanel.set_unselected_tab_info(setFileListTabInfoCommand.paths)
        elif presenter.DetailsTabIds.SKIPPED == detailsTabId:
            packageContentsPanel.set_skipped_tab_info(setFileListTabInfoCommand.paths)
        else:
            raise RuntimeError("unhandled file list tab: %s" % detailsTabId)

    def _display_error(self, displayErrorCommand):
        _logger.debug("displaying error: %s", displayErrorCommand)
        self._installerTab.display_error(self._messageManager.get_error_message(
            displayErrorCommand.errorCode, displayErrorCommand.resourceName))

    def _ask_confirmation(self, askConfirmationCommand):
        _logger.debug("asking fo confirmation: %s", askConfirmationCommand)
        self._installerTab.ask_confirmation(self._messageManager.get_confirmation_message(
            askConfirmationCommand.confirmationQuestionId,
            askConfirmationCommand.resourceName))

    def _extended(self, extendedCommand):
        _logger.debug("processing extended command: %s", extendedCommand)
        # TODO: process image updates from imageLoader
