# -*- coding: utf-8 -*-
#
# bait/view/impl/package_contents_panel.py
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

from cStringIO import StringIO
import logging
import wx
import wx.lib.scrolledpanel

from . import filter_panel, filtered_tree, settings_buttons
from ... import presenter


_logger = logging.getLogger(__name__)

_statsChartElementKeys = [
    "numSelectedMatched", "numSelectedMismatched", "numSelectedOverridden",
    "numSelectedMissing", "numTotalSelected", "numUnselectedMatched",
    "numUnselectedMismatched", "numUnselectedOverridden", "numUnselectedMissing",
    "numTotalUnselected", "numTotalMatched", "numTotalMismatched", "numTotalOverridden",
    "numTotalMissing", "numTotalSelectable"]

_bytesPerKb = 1024


def _add_tab(parentNotebook, tabName, filterIds, filterLabels,
             presenter_, filterRegistry, additionalStyle=0):
    tabPanel = wx.Panel(parentNotebook)
    sizer = wx.BoxSizer(wx.VERTICAL)
    filter_panel.FilterPanel(tabPanel, sizer, filterIds, filterLabels,
                             presenter_, filterRegistry)
    textCtrl = wx.TextCtrl(
        tabPanel, style=wx.TE_READONLY|wx.TE_MULTILINE|wx.NO_BORDER|additionalStyle)
    textCtrl.SetBackgroundColour(parentNotebook.GetBackgroundColour())
    sizer.Add(textCtrl, 1, wx.EXPAND)
    tabPanel.SetSizer(sizer)
    parentNotebook.AddPage(tabPanel, tabName)
    return textCtrl


class _PackageInfoTabs:
    def __init__(self, detailsSplitter, fileTreeSplitter, presenter_, filterRegistry):
        panel = wx.Panel(detailsSplitter)
        sizer = wx.BoxSizer(wx.VERTICAL)
        label = self._label = wx.StaticText(panel)
        sizer.Add(label, 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 3)
        notebook = wx.Notebook(panel)
        sizer.Add(notebook, 1, wx.EXPAND)

        # work around color weirdness on windows
        backgroundColor = panel.GetBackgroundColour()
        notebook.SetBackgroundColour(backgroundColor)

        generalTabPanel = wx.lib.scrolledpanel.ScrolledPanel(notebook)
        generalTabSummary = self._generalTabSummary = wx.StaticText(generalTabPanel)
        generalTabChartPanel = self._generalTabChartPanel = wx.Panel(generalTabPanel)
        generalTabStatsChart = self._generalTabStatsChart = dict(
            (key, wx.StaticText(generalTabChartPanel)) for key in _statsChartElementKeys)
        notebook.AddPage(generalTabPanel, "General")

        self._dirtyText = _add_tab(
            notebook, "Dirty",
            (presenter.FilterIds.DIRTY_ADD,
             presenter.FilterIds.DIRTY_UPDATE,
             presenter.FilterIds.DIRTY_DELETE),
            ("Add", "Update", "Delete"), presenter_, filterRegistry, wx.TE_RICH2)
        self._conflictsText = _add_tab(
            notebook, "Conflicts",
            (presenter.FilterIds.CONFLICTS_SELECTED,
             presenter.FilterIds.CONFLICTS_UNSELECTED,
             presenter.FilterIds.CONFLICTS_ACTIVE, presenter.FilterIds.CONFLICTS_INACTIVE,
             presenter.FilterIds.CONFLICTS_HIGHER, presenter.FilterIds.CONFLICTS_LOWER),
            ("Selected", "Unselected", "Active", "Inactive", "Higher", "Lower"),
            presenter_, filterRegistry)
        self._selectedText = _add_tab(
            notebook, "Selected",
            (presenter.FilterIds.SELECTED_MATCHED,
             presenter.FilterIds.SELECTED_MISMATCHED,
             presenter.FilterIds.SELECTED_MISSING,
             presenter.FilterIds.SELECTED_NO_CONFLICTS,
             presenter.FilterIds.SELECTED_HAS_CONFLICTS),
            ("Matched", "Mismatched", "Missing", "Non-Unique", "Unique"),
            presenter_, filterRegistry)
        self._unselectedText = _add_tab(
            notebook, "Unselected",
            (presenter.FilterIds.UNSELECTED_MATCHED,
             presenter.FilterIds.UNSELECTED_MISMATCHED,
             presenter.FilterIds.UNSELECTED_MISSING,
             presenter.FilterIds.UNSELECTED_NO_CONFLICTS,
             presenter.FilterIds.UNSELECTED_HAS_CONFLICTS),
            ("Matched", "Mismatched", "Missing", "Non-Unique", "Unique"),
            presenter_, filterRegistry)
        self._skippedText = _add_tab(notebook, "Skipped",
            (presenter.FilterIds.SKIPPED_NONGAME, presenter.FilterIds.SKIPPED_MASKED),
            ("Non-game", "Masked"), presenter_, filterRegistry)

        generalTabChartSizer = wx.GridBagSizer(2, 5)
        generalTabChartSizer.Add(wx.StaticText(
            generalTabChartPanel, label="Matched"), (0,1), flag=wx.ALIGN_CENTER)
        generalTabChartSizer.Add(wx.StaticText(
            generalTabChartPanel, label="Mismatched"), (0,2), flag=wx.ALIGN_CENTER)
        generalTabChartSizer.Add(wx.StaticText(
            generalTabChartPanel, label="Overridden"), (0,3), flag=wx.ALIGN_CENTER)
        generalTabChartSizer.Add(wx.StaticText(
            generalTabChartPanel, label="Missing"), (0,4), flag=wx.ALIGN_CENTER)
        generalTabChartSizer.Add(wx.StaticText(
            generalTabChartPanel, label="Total"), (0,5), flag=wx.ALIGN_CENTER)
        generalTabChartSizer.Add(wx.StaticText(
            generalTabChartPanel, label="Selected"), (1,0), flag=wx.ALIGN_CENTER)
        generalTabChartSizer.Add(wx.StaticText(
            generalTabChartPanel, label="Unselected"), (2,0), flag=wx.ALIGN_CENTER)
        generalTabChartSizer.Add(wx.StaticText(
            generalTabChartPanel, label="Total"), (3,0), flag=wx.ALIGN_CENTER)
        row = 1
        col = 1
        for statsChartElement in _statsChartElementKeys:
            generalTabChartSizer.Add(
                generalTabStatsChart[statsChartElement], (row,col), flag=wx.ALIGN_RIGHT)
            col += 1
            if col is 6:
                col = 1
                row += 1
        generalTabChartPanel.SetSizer(generalTabChartSizer)

        generalTabSizer = wx.BoxSizer(wx.VERTICAL)
        generalTabSizer.Add(generalTabSummary, 0, wx.EXPAND)
        generalTabSizer.Add(generalTabChartPanel, 0, wx.EXPAND)
        generalTabPanel.SetSizer(generalTabSizer)
        generalTabPanel.SetAutoLayout(True)
        generalTabPanel.SetupScrolling()

        self._detailsTabIndexToTabId = {
            0:presenter.DetailsTabIds.GENERAL, 1:presenter.DetailsTabIds.DIRTY,
            2:presenter.DetailsTabIds.CONFLICTS, 3:presenter.DetailsTabIds.SELECTED,
            4:presenter.DetailsTabIds.UNSELECTED, 5:presenter.DetailsTabIds.SKIPPED}
        self._presenter = presenter_
        self._greyColor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        # TODO: make colors configurable?
        # TODO: get colors from style map?
        self._dirtyAttrs = {
            presenter.AnnealOperationIds.COPY:wx.TextAttr(wx.Color(34,139,34)),
            presenter.AnnealOperationIds.OVERWRITE:wx.TextAttr(wx.Color(0,0,139)),
            presenter.AnnealOperationIds.DELETE:wx.TextAttr(wx.Color(178,34,34))}
        self._dirtyActions = {presenter.AnnealOperationIds.COPY:" (add)",
                              presenter.AnnealOperationIds.OVERWRITE:" (update)",
                              presenter.AnnealOperationIds.DELETE:" (delete)"}

        panel.SetMinSize(sizer.GetMinSize())
        panel.SetSizer(sizer)

        detailsSplitter.SetMinimumPaneSize(100)
        detailsSplitter.SplitHorizontally(panel, fileTreeSplitter)
        detailsSplitter.SetSashGravity(0.5) # resize both panels equally

        notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self._on_tab_changing)


    def reset(self, title):
        # TODO: for this whole file: when we disable, disable the entire notebook page so
        # TODO:   the filter buttons are disabled too
        if title is None:
            self._label.SetLabel("")
        elif len(title) is 0:
            self._label.SetLabel("Multiple packages selected")
            self._label.Disable()
        else:
            self._label.Enable()
            self._label.SetLabel(title)
        # clear all tab contents
        self._generalTabSummary.SetLabel("Loading...")
        self._generalTabSummary.Disable()
        self._generalTabChartPanel.Hide()
        self._dirtyText.SetValue("Loading...")
        self._dirtyText.Disable()
        for textCtrl in (self._conflictsText, self._selectedText,
                         self._unselectedText, self._skippedText):
            textCtrl.SetValue("Loading...")
            textCtrl.SetForegroundColour(self._greyColor)
            textCtrl.Disable()

    def set_general_tab_info(self, isArchive, isHidden=None, isInstalled=None,
            packageBytes=None, selectedBytes=None, lastModifiedTimestamp=None,
            numFiles=None, numDirty=None, numOverridden=None, numSkipped=None,
            numSelectedMatched=None, numSelectedMismatched=None,
            numSelectedOverridden=None, numSelectedMissing=None, numTotalSelected=None,
            numUnselectedMatched=None, numUnselectedMismatched=None,
            numUnselectedOverridden=None, numUnselectedMissing=None,
            numTotalUnselected=None, numTotalMatched=None, numTotalMismatched=None,
            numTotalOverridden=None, numTotalMissing=None, numTotalSelectable=None):
        if isArchive is None:
            self._generalTabSummary.SetLabel("Select a package to show details")
            self._generalTabSummary.Disable()
            self._generalTabChartPanel.Hide()
            return
        self._generalTabChartPanel.Show()
        self._generalTabSummary.Enable()

        if isArchive: packageType = "Archive"
        else: packageType = "Project"

        if isHidden: status = "Hidden"
        elif isInstalled: status = "Installed"
        else: status = "Not Installed"

        packageKb = packageBytes/_bytesPerKb
        selectedKb = selectedBytes/_bytesPerKb
        self._generalTabSummary.SetLabel("""Package type: %s (%s)
Package size: %s KB (%s KB selected for installation)
Last Modified: %s
Files: %d
  Dirty: %d
  Overridden: %d
  Skipped: %d""" % (packageType, status,
                    1 if packageKb == 0 and packageBytes > 0 else packageKb,
                    1 if selectedKb == 0 and selectedBytes > 0 else selectedKb,
                    lastModifiedTimestamp, numFiles, numDirty,
                    numOverridden, numSkipped))

        generalTabStatsChart = self._generalTabStatsChart
        for key in _statsChartElementKeys:
            generalTabStatsChart[key].SetLabel(str(locals()[key]))
        generalTabPanel = self._generalTabChartPanel.GetParent()
        generalTabPanel.Layout()
        generalTabPanel.SetupScrolling()


    def set_general_tab_image(self, image):
        pass

    def set_dirty_tab_info(self, annealOperations):
        textCtrl = self._dirtyText
        if self._handle_empty_null_data(textCtrl, annealOperations):
            return
        dirtyAttrs = self._dirtyAttrs
        dirtyActions = self._dirtyActions
        textCtrl.SetValue("Files affected by next anneal action:")
        lastActionType = None
        for actionType, path in annealOperations:
            textCtrl.write("\n")
            if not actionType is lastActionType:
                textCtrl.SetDefaultStyle(dirtyAttrs[actionType])
            textCtrl.AppendText(path)
            textCtrl.AppendText(dirtyActions[actionType])
            lastActionType = actionType

    def set_conflicts_tab_info(self, conflictLists, nodeIdToNodeLabelMap):
        # conflictLists is an enumeration of tuples:
        #   (conflictingPackageNodeId, [list of conflicting paths])
        if conflictLists is None:
            text = None
        elif len(conflictLists) == 0:
            text = ""
        else:
            outStr = StringIO()
            isFirst = True
            for conflictList in conflictLists:
                if not isFirst:
                    outStr.write("\n\n")
                # write header
                conflictLabel = nodeIdToNodeLabelMap[conflictList[0]]
                outStr.write(conflictLabel)
                outStr.write("\n")
                outStr.write("-"*len(conflictLabel))
                outStr.write("\n")
                self._build_path_list(conflictList[1], outStr)
                isFirst = False
            text = outStr.getvalue()
        self._set_text_tab_info(self._conflictsText, text)

    def set_selected_tab_info(self, paths):
        self._set_text_tab_info(self._selectedText, self._build_path_list(paths))

    def set_unselected_tab_info(self, paths):
        self._set_text_tab_info(self._unselectedText, self._build_path_list(paths))

    def set_skipped_tab_info(self, paths):
        self._set_text_tab_info(self._skippedText, self._build_path_list(paths))

    def _build_path_list(self, paths, outStr=None):
        if paths is None:
            return None
        if len(paths) == 0:
            return ""
        returnStr = True
        if outStr is None:
            outStr = StringIO()
            returnStr = False
        isFirst = True
        for path in paths:
            if not isFirst: outStr.write("\n")
            outStr.write(path)
            isFirst = False
        if returnStr:
            return outStr.getvalue()

    def _handle_empty_null_data(self, textCtrl, data):
        if data is None or len(data) is 0:
            textCtrl.SetForegroundColour(self._greyColor)
            textCtrl.Disable()
            if data is None: textCtrl.SetValue("Select a package to show details")
            else: textCtrl.SetValue("No files pass the selected filters")
            return True
        textCtrl.Enable()
        textCtrl.SetForegroundColour(wx.NullColor)
        return False

    def _set_text_tab_info(self, textCtrl, text):
        if self._handle_empty_null_data(textCtrl, text): return
        textCtrl.SetValue(text)

    def _on_tab_changing(self, event):
        if event.GetOldSelection() is -1:
            # shutting down; ignore
            return
        oldTabId = self._detailsTabIndexToTabId[event.GetOldSelection()]
        newTabId = self._detailsTabIndexToTabId[event.GetSelection()]
        _logger.debug("details tab changing from %s to %s", oldTabId, newTabId)
        self._presenter.set_details_tab_selection(newTabId)
        event.Skip()



class PackageContentsPanel:
    def __init__(self, splitters, oneLineHeight, presenter_, filterRegistry):
        detailsSplitter = splitters["details"]
        fileTreeSplitter = splitters["fileTree"]
        self._packageInfoTabs = _PackageInfoTabs(detailsSplitter, fileTreeSplitter,
                                                 presenter_, filterRegistry)

        fileTreePanel = wx.Panel(fileTreeSplitter)
        fileTreeHeaderSizer = wx.BoxSizer(wx.HORIZONTAL)
        self._projectSettingsButton = settings_buttons.PackageSettingsButton(
            fileTreePanel, fileTreeHeaderSizer)
        fileTreeLabel = wx.StaticText(fileTreePanel, label="Package contents")
        fileTreeHeaderSizer.Add(fileTreeLabel, 1,
                                wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM, 5)

        fileTreeSizer = wx.BoxSizer(wx.VERTICAL)
        fileTreeSizer.Add(fileTreeHeaderSizer, 0, wx.EXPAND)
        self.packageContentsTree = filtered_tree.PackageContentsTree(
            fileTreePanel, fileTreeSizer,
            (presenter.FilterIds.FILES_PLUGINS,
             presenter.FilterIds.FILES_RESOURCES,
             presenter.FilterIds.FILES_OTHER),
            ("Plugins", "Resources", "Other"),
            presenter_, filterRegistry)
        fileTreePanel.SetMinSize(fileTreeSizer.GetMinSize())
        fileTreePanel.SetSizer(fileTreeSizer)

        fileInfoPanel = wx.Panel(fileTreeSplitter)
        fileInfoSizer = wx.BoxSizer(wx.VERTICAL)
        fileInfoLabel = wx.StaticText(fileInfoPanel, label="File details")
        fileInfoSizer.Add(fileInfoLabel, 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
        fileInfo = wx.TextCtrl(fileInfoPanel, style=wx.TE_READONLY|wx.TE_MULTILINE)
        fileInfo.SetBackgroundColour(fileTreeLabel.GetBackgroundColour())
        fileInfoSizer.Add(fileInfo, 1, wx.EXPAND)
        fileInfoPanel.SetMinSize(fileInfoSizer.GetMinSize())
        fileInfoPanel.SetSizer(fileInfoSizer)

        commentsSplitter = splitters["comments"]
        commentsPanel = wx.Panel(commentsSplitter)
        commentsSizer = wx.BoxSizer(wx.VERTICAL)
        commentsLabel = wx.StaticText(commentsPanel, label="Comments")
        commentsSizer.Add(commentsLabel, 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 3)
        commentsText = wx.SearchCtrl(
            commentsPanel, size=(-1, oneLineHeight), style=wx.TE_MULTILINE)
        commentsText.SetDescriptiveText("Enter comments for this project here")
        commentsText.ShowSearchButton(False)
        commentsSizer.Add(commentsText, 1, wx.EXPAND)
        commentsPanel.SetMinSize(commentsSizer.GetMinSize())
        commentsPanel.SetSizer(commentsSizer)

        # set up splitters
        fileTreeSplitter.SetMinimumPaneSize(50)
        fileTreeSplitter.SplitVertically(fileTreePanel, fileInfoPanel)
        fileTreeSplitter.SetSashGravity(0.5) # resize both panels equally
        commentsSplitter.SetMinimumPaneSize(oneLineHeight)
        commentsSplitter.SplitHorizontally(detailsSplitter, commentsPanel)
        commentsSplitter.SetSashGravity(1.0) # only resize details

        self.reset(None, False, *[None]*5)
        self.set_general_tab_info(None)


    def reset(self, title, enabled, skipDistantLod, skipLodMeshes, skipLodNormals,
              skipLodTextures, skipVoices):
        self._projectSettingsButton.set_settings(
            skipDistantLod, skipLodMeshes, skipLodNormals, skipLodTextures, skipVoices)
        self._packageInfoTabs.reset(title)
        self._projectSettingsButton.set_enabled(enabled)
        self.packageContentsTree.set_enabled(enabled)

    def set_general_tab_info(self, *args):
        self._packageInfoTabs.set_general_tab_info(*args)
    def set_general_tab_image(self, image):
        self._packageInfoTabs.set_general_tab_image(image)
    def set_dirty_tab_info(self, annealOperations):
        self._packageInfoTabs.set_dirty_tab_info(annealOperations)
    def set_conflicts_tab_info(self, conflictLists, nodeIdToNodeLabelMap):
        self._packageInfoTabs.set_conflicts_tab_info(conflictLists, nodeIdToNodeLabelMap)
    def set_selected_tab_info(self, paths):
        self._packageInfoTabs.set_selected_tab_info(paths)
    def set_unselected_tab_info(self, paths):
        self._packageInfoTabs.set_unselected_tab_info(paths)
    def set_skipped_tab_info(self, paths):
        self._packageInfoTabs.set_skipped_tab_info(paths)
