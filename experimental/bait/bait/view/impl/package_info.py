# -*- coding: utf-8 -*-
#
# bait/view/impl/package_info.py
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
import wx.lib.fancytext

from . import filter_panel
from ... import presenter


_logger = logging.getLogger(__name__)
_statsChartElementKeys = ["numSelectedMatched", "numSelectedMismatched", "numSelectedOverridden", "numSelectedMissing", "numTotalSelected", "numUnselectedMatched", "numUnselectedMismatched", "numUnselectedOverridden", "numUnselectelectedMissing", "numTotalUnselected", "numTotalMatched", "numTotalMismatched", "numTotalOverridden", "numTotalMissing", "numTotalSelectable"]
_dirtyTabFilterIds = frozenset((presenter.FILTER_ID_DIRTY_ADD, presenter.FILTER_ID_DIRTY_UPDATE, presenter.FILTER_ID_DIRTY_DELETE))
_conflictsTabFilterIds = frozenset((presenter.FILTER_ID_CONFLICTS_SELECTED, presenter.FILTER_ID_CONFLICTS_UNSELECTED, presenter.FILTER_ID_CONFLICTS_ACTIVE, presenter.FILTER_ID_CONFLICTS_INACTIVE, presenter.FILTER_ID_CONFLICTS_HIGHER, presenter.FILTER_ID_CONFLICTS_LOWER))
_selectedTabFilterIds = frozenset((presenter.FILTER_ID_SELECTED_MATCHED, presenter.FILTER_ID_SELECTED_MISMATCHED, presenter.FILTER_ID_SELECTED_OVERRIDDEN, presenter.FILTER_ID_SELECTED_MISSING))
_unselectedTabFilterIds = frozenset((presenter.FILTER_ID_UNSELECTED_MATCHED, presenter.FILTER_ID_UNSELECTED_MISMATCHED, presenter.FILTER_ID_UNSELECTED_OVERRIDDEN, presenter.FILTER_ID_UNSELECTED_MISSING))
_skippedTabFilterIds = frozenset((presenter.FILTER_ID_SKIPPED_NONGAME, presenter.FILTER_ID_SKIPPED_MASKED))


def _add_tab(parent, tabName, filterIds, filterLabelFormatPatterns, presenter_, additionalStyle=0):
    tabPanel = wx.Panel(parent)
    filterPanel = filter_panel.FilterPanel(tabPanel, filterIds, filterLabelFormatPatterns, presenter_)
    textCtrl = wx.TextCtrl(tabPanel, style=wx.TE_READONLY|wx.TE_MULTILINE|wx.NO_BORDER|additionalStyle)
    textCtrl.SetBackgroundColour(parent.GetBackgroundColour())
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(filterPanel, 0, wx.EXPAND)
    sizer.Add(textCtrl, 1, wx.EXPAND)
    tabPanel.SetSizer(sizer)
    parent.AddPage(tabPanel, tabName)
    return filterPanel, textCtrl


class PackageInfoPanel(wx.Panel):
    '''Provides a panel that displays package information'''
    def __init__(self, parent, presenter_):
        wx.Panel.__init__(self, parent)

        label = self._label = wx.StaticText(self)
        packageInfoTabs = wx.Notebook(self)
        
        generalTabPanel = wx.Panel(packageInfoTabs)
        generalTabSummary = self._generalTabSummary = wx.StaticText(generalTabPanel)
        generalTabChartPanel = self._generalTabChartPanel = wx.Panel(generalTabPanel)
        generalTabStatsChart = self._generalTabStatsChart = dict((key, wx.StaticText(generalTabChartPanel)) for key in _statsChartElementKeys)
        packageInfoTabs.AddPage(generalTabPanel, "General")

        self._dirtyFilterPanel, self._dirtyText = _add_tab(packageInfoTabs, "Dirty",
            (presenter.FILTER_ID_DIRTY_ADD, presenter.FILTER_ID_DIRTY_UPDATE, presenter.FILTER_ID_DIRTY_DELETE),
            ("Add (%d)", "Update (%d)", "Delete (%d)"), presenter_, wx.TE_RICH2)
        self._conflictsFilterPanel, self._conflictsText = _add_tab(packageInfoTabs, "Conflicts",
            (presenter.FILTER_ID_CONFLICTS_SELECTED, presenter.FILTER_ID_CONFLICTS_UNSELECTED,
             presenter.FILTER_ID_CONFLICTS_ACTIVE, presenter.FILTER_ID_CONFLICTS_INACTIVE,
             presenter.FILTER_ID_CONFLICTS_HIGHER, presenter.FILTER_ID_CONFLICTS_LOWER),
            ("Selected (%d)", "Unselected (%d)", "Active (%d)", "Inactive (%d)", "Higher (%d)", "Lower (%d)"), presenter_)
        self._selectedFilterPanel, self._selectedText = _add_tab(packageInfoTabs, "Selected",
            (presenter.FILTER_ID_SELECTED_MATCHED, presenter.FILTER_ID_SELECTED_MISMATCHED,
             presenter.FILTER_ID_SELECTED_OVERRIDDEN, presenter.FILTER_ID_SELECTED_MISSING),
            ("Matched (%d)", "Mismatched (%d)", "Overridden (%d)", "Missing (%d)"), presenter_)
        self._unselectedFilterPanel, self._unselectedText = _add_tab(packageInfoTabs, "Unselected",
            (presenter.FILTER_ID_UNSELECTED_MATCHED, presenter.FILTER_ID_UNSELECTED_MISMATCHED,
             presenter.FILTER_ID_UNSELECTED_OVERRIDDEN, presenter.FILTER_ID_UNSELECTED_MISSING),
            ("Matched (%d)", "Mismatched (%d)", "Overridden (%d)", "Missing (%d)"), presenter_)
        self._skippedFilterPanel, self._skippedText = _add_tab(packageInfoTabs, "Skipped",
            (presenter.FILTER_ID_SKIPPED_NONGAME, presenter.FILTER_ID_SKIPPED_MASKED),
            ("Non-game (%d)", "Masked (%d)"), presenter_)

        generalTabChartSizer = wx.GridBagSizer(5, 5)
        generalTabChartSizer.Add(wx.StaticText(generalTabChartPanel, label="Matched"), (1,1), flag=wx.ALIGN_CENTER)
        generalTabChartSizer.Add(wx.StaticText(generalTabChartPanel, label="Mismatched"), (1,2), flag=wx.ALIGN_CENTER)
        generalTabChartSizer.Add(wx.StaticText(generalTabChartPanel, label="Overridden"), (1,3), flag=wx.ALIGN_CENTER)
        generalTabChartSizer.Add(wx.StaticText(generalTabChartPanel, label="Missing"), (1,4), flag=wx.ALIGN_CENTER)
        generalTabChartSizer.Add(wx.StaticText(generalTabChartPanel, label="Total"), (1,5), flag=wx.ALIGN_CENTER)
        generalTabChartSizer.Add(wx.StaticText(generalTabChartPanel, label="Selected"), (2,0), flag=wx.ALIGN_CENTER)
        generalTabChartSizer.Add(wx.StaticText(generalTabChartPanel, label="Unselected"), (3,0), flag=wx.ALIGN_CENTER)
        generalTabChartSizer.Add(wx.StaticText(generalTabChartPanel, label="Total"), (4,0), flag=wx.ALIGN_CENTER)
        row = 2
        col = 1
        for statsChartElement in _statsChartElementKeys:
            generalTabChartSizer.Add(generalTabStatsChart[statsChartElement], (row,col), flag=wx.ALIGN_RIGHT)
            col += 1
            if col is 6:
                col = 1
                row += 1
        generalTabChartPanel.SetSizer(generalTabChartSizer)

        generalTabSizer = wx.BoxSizer(wx.VERTICAL)
        generalTabSizer.Add(generalTabSummary, 1, wx.EXPAND)
        generalTabSizer.Add(generalTabChartPanel, 1, wx.EXPAND)
        generalTabPanel.SetSizer(generalTabSizer)
        
        packageInfoSizer = wx.BoxSizer(wx.VERTICAL)
        packageInfoSizer.Add(self._label, 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 3)
        packageInfoSizer.Add(packageInfoTabs, 1, wx.EXPAND)
        self.SetMinSize(packageInfoSizer.GetMinSize())
        self.SetSizer(packageInfoSizer)

        self._detailsTabIndexToTabId = {0:presenter.DETAILS_TAB_ID_GENERAL, 1:presenter.DETAILS_TAB_ID_DIRTY, 2:presenter.DETAILS_TAB_ID_CONFLICTS, 3:presenter.DETAILS_TAB_ID_SELECTED, 4:presenter.DETAILS_TAB_ID_UNSELECTED, 5:presenter.DETAILS_TAB_ID_SKIPPED}
        self._presenter = presenter_
        self._greyColor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        # TODO: make colors configurable?
        # TODO: get colors from style map?
        self._dirtyAttrs = {presenter.FILTER_ID_DIRTY_ADD:wx.TextAttr(wx.Color(34,139,34)), presenter.FILTER_ID_DIRTY_UPDATE:wx.TextAttr(wx.Color(0,0,139)), presenter.FILTER_ID_DIRTY_DELETE:wx.TextAttr(wx.Color(178,34,34))}
        self._dirtyActions = {presenter.FILTER_ID_DIRTY_ADD:" (add)", presenter.FILTER_ID_DIRTY_UPDATE:" (update)", presenter.FILTER_ID_DIRTY_DELETE:" (delete)"}

        packageInfoTabs.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self._on_tab_changing)
        self.set_label(None)


    def start(self, filterStateMap):
        self._dirtyFilterPanel.start(filterStateMap)
        self._conflictsFilterPanel.start(filterStateMap)
        self._selectedFilterPanel.start(filterStateMap)
        self._unselectedFilterPanel.start(filterStateMap)
        self._skippedFilterPanel.start(filterStateMap)

    def set_filter_stats(self, filterId, current, total):
        # TODO: dict lookup
        if filterId in _dirtyTabFilterIds: target = self._dirtyFilterPanel
        elif filterId in _conflictsTabFilterIds: target = self._conflictsFilterPanel
        elif filterId in _selectedTabFilterIds: target = self._selectedFilterPanel
        elif filterId in _unselectedTabFilterIds: target = self._unselectedFilterpanel
        elif filterId in _skippedTabFilterIds: target = self._skippedFilterPanel
        else:
            _logger.warn("filter stats set for unknown filterId: %d", filterId)
            return
        target.set_filter_stats(setFilterStatsCommand.filterId, setFilterStatsCommand.current, setFilterStatsCommand.total)

    def set_label(self, label):
        if label is None:
            self._label.SetLabel("")
        elif len(label) is 0:
            self._label.SetLabel("Multiple packages selected")
            self._label.Disable()
        else:
            self._label.Enable()
            self._label.SetLabel(label)
        # clear all tab contents
        self._generalTabSummary.SetLabel("Loading...")
        self._generalTabSummary.Disable()
        self._generalTabChartPanel.Hide()
        self._dirtyText.SetValue("Loading...")
        self._dirtyText.Disable()
        for textCtrl in (self._conflictsText, self._selectedText, self._unselectedText, self._skippedText):
            textCtrl.SetValue("Loading...")
            textCtrl.SetForegroundColour(self._greyColor)
            textCtrl.Disable()

    def set_tab_data(self, tabId, data):
        if tabId is presenter.DETAILS_TAB_ID_GENERAL: self._set_general_info(data)
        elif tabId is presenter.DETAILS_TAB_ID_DIRTY: self._set_dirty_info(data)
        elif tabId is presenter.DETAILS_TAB_ID_CONFLICTS: self._set_tab_text(self._conflictsText, data)
        elif tabId is presenter.DETAILS_TAB_ID_SELECTED: self._set_tab_text(self._selectedText, data)
        elif tabId is presenter.DETAILS_TAB_ID_UNSELECTED: self._set_tab_text(self._unselectedText, data)
        elif tabId is presenter.DETAILS_TAB_ID_SKIPPED: self._set_tab_text(self._skippedText, data)
        else:
            _logger.error("unhandled tab id: %s", tabId)

    def _set_general_info(self, generalStats):
        if generalStats is None:
            self._generalTabSummary.SetLabel("No package selected")
            self._generalTabSummary.Disable()
            self._generalTabChartPanel.Hide()
            return
        self._generalTabChartPanel.Show()
        self._generalTabSummary.Enable()

        if generalStats["isArchive"] is True: packageType = "Archive"
        elif generalStats["isArchive"] is False: packageType = "Project"
        
        if generalStats["isInstalled"] is True: installedPrefix = ""
        elif generalStats["isInstalled"] is False: installedPrefix = "Not "

        self._generalTabSummary.SetLabel("""Package type: %s (%sInstalled)
Package size: %s (%s fully installed)
Last Modified: %s
Files: %d
  Dirty: %d
  Overridden: %d
  Skipped: %d""" % (packageType, installedPrefix, generalStats["packageSize"], generalStats["contentsSize"], generalStats["lastModifiedTimestamp"],
                    generalStats.get(numFiles, 0), generalStats.get(numDirty, 0), generalStats.get(numOverridden, 0),
                    generalStats.get(numSkipped, 0)))
  
        generalTabStatsChart = self._generalTabStatsChart
        for key in _statsChartElementKeys:
            generalTabStatsChart[key].SetLabel(generalStats.get(key, 0))

    def _handle_empty_null_data(self, textCtrl, data):
        if data is None or len(data) is 0:
            textCtrl.SetForegroundColour(self._greyColor)
            textCtrl.Disable()
            if data is None: textCtrl.SetValue("No package selected")
            else: textCtrl.SetValue("None")
            return True
        textCtrl.Enable()
        textCtrl.SetForegroundColour(wx.NullColor)
        return False

    def _set_dirty_info(self, annealActions):
        textCtrl = self._dirtyText
        if self._handle_empty_null_data(textCtrl, annealActions): return
        dirtyAttrs = self._dirtyAttrs
        dirtyActions = self._dirtyActions
        textCtrl.SetValue("Files affected by next anneal action:")
        lastActionType = None
        for actionType, path in annealActions:
            textCtrl.write("\n")
            if not actionType is lastActionType:
                textCtrl.SetDefaultStyle(dirtyAttrs[actionType])
            textCtrl.AppendText(path)
            textCtrl.AppendText(dirtyActions[actionType])
            lastActionType = actionType

    def _set_tab_text(self, textCtrl, text):
        if self._handle_empty_null_data(textCtrl, text): return
        textCtrl.SetValue(text)

    def _on_tab_changing(self, event):
        if event.GetOldSelection() is -1:
            # shutting down; ignore
            return
        oldTabId = self._detailsTabIndexToTabId[event.GetOldSelection()]
        newTabId = self._detailsTabIndexToTabId[event.GetSelection()]
        _logger.debug("details tab changing from %d to %d", oldTabId, newTabId)
        self._presenter.set_details_tab_selection(newTabId)
        event.Skip()
