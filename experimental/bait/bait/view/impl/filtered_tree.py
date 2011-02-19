# -*- coding: utf-8 -*-
#
# bait/view/impl/filtered_tree.py
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
import wx
from wx.lib.agw import customtreectrl as CT


_logger = logging.getLogger(__name__)


class _FilteredTree(CT.CustomTreeCtrl):
    def __init__(self, parent, filterIds, filterLabelFormatPatterns, presenter_):
        CT.CustomTreeCtrl.__init__(self, parent,
                style=wx.SUNKEN_BORDER,
                agwStyle=CT.TR_HAS_VARIABLE_ROW_HEIGHT|CT.TR_HAS_BUTTONS|CT.TR_HIDE_ROOT|CT.TR_MULTIPLE|CT.TR_NO_LINES)

        # reduce size of toggle filter labels by 2, but no smaller than 6
        parentFont = parent.GetFont()
        panelFont = wx.Font(
            max((6, parentFont.GetPointSize()-2)),
            parentFont.GetFamily(), parentFont.GetStyle(),
            wx.FONTWEIGHT_NORMAL, False, parentFont.GetFaceName())
        filterPanel = wx.Panel(self)
        filterPanel.SetBackgroundColour(self.GetBackgroundColour())
        filterPanel.SetFont(panelFont)
        filterPanelSizer = wx.BoxSizer(wx.HORIZONTAL)
        dc = wx.WindowDC(self)
        dc.SetFont(panelFont)
        panelLabel = wx.StaticText(filterPanel, label="Show:")
        filterPanelSizer.Add(panelLabel, 0, wx.ALIGN_CENTER_VERTICAL)
        self._filters = {}
        self._wxIdToFilterId = {}
        for filterId, filterLabelFormatPattern in zip(filterIds, filterLabelFormatPatterns):
            # calculate reduced button size dimensions and create buttons
            filterButton = wx.ToggleButton(filterPanel)
            self._set_filter_button_label(filterButton, filterLabelFormatPattern, 0, 0)
            curWidth, curHeight = filterButton.GetBestSize()
            filterButton.SetMinSize((curWidth, curHeight-6))
            filterPanelSizer.Add(filterButton, 0, wx.ALIGN_CENTER_VERTICAL)
            self._filters[filterId] = (filterButton, filterLabelFormatPattern)
            self._wxIdToFilterId[filterButton.GetId()] = filterId
            self.Bind(wx.EVT_TOGGLEBUTTON, self._on_toggle_filter)
        # no need to set size hints -- this panel doesn't determine any sizer limits
        filterPanel.SetSizer(filterPanelSizer)
        filterPanel.Fit()
        
        # create tree base
        self._topItem = self.AppendItem(self.AddRoot("root"), "", wnd=filterPanel)
        self._presenter = presenter_
        self._nodeIdToItem = {}
        
        # bind to events
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_sel_changed)
        self.Bind(wx.EVT_TREE_SEL_CHANGING, self._on_sel_changing)
        self.Bind(wx.EVT_TREE_ITEM_EXPANDED, self._on_item_expanded)
        self.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self._on_item_collapsed)
        
        
    def start(self, filterStateMap):
        # set initial filter states (presenter is notified in bait_view.start(), so no need to do it here)
        for (filterId, filterState) in filterStateMap.items():
            self._filters[filterId][0].SetValue(filterState)

    def clear(self):
        _logger.debug("clearing tree")
        # make a copy of the item list to avoid modifying the list we're iterating through
        # avoid removing/re-adding top filter item to prevent flickering
        children = self.GetRootItem().GetChildren()[1:]
        for item in children:
            #if item is self._topItem: continue
            _logger.debug("clearing node: %d", item.GetData())
            self.Delete(item)
        self._nodeIdToItem = {} # reset mappings

    def set_filter_stats(self, filterId, current, total):
        filterButton, filterLabelFormatPattern = self._filters[filterId]
        _logger.debug("updating filter %d label with stats: current=%d; total=%d", filterId, current, total)
        self._set_filter_button_label(filterButton, filterLabelFormatPattern, current, total)
        # resize button width to fit the new label
        curHeight = filterButton.GetSize()[1]
        filterButton.SetMinSize((filterButton.GetBestSize()[0], curHeight))
        filterPanel = self._topItem.GetWindow()
        filterPanel.Layout()
        filterPanel.Fit()

    def add_item(self, nodeId, label, parentNodeId, predNodeId, foregroundColor=None, checkboxState=None):
        _logger.debug("adding node %d: %s", nodeId, label)
        if parentNodeId is None:
            parent = self.GetRootItem()
        else:
            parent = self._nodeIdToItem[parentNodeId]
        predecessor = None
        if predNodeId is None:
            if parent is self.GetRootItem():
                predecessor = self._topItem
        else:
            predecessor = self._nodeIdToItem[predNodeId]

        if checkboxState is None:
            ct_type = 0
            checked = False
        else:
            ct_type = 1
            checked = checkboxState

        item = self.InsertItem(parent, predecessor, label, ct_type)
        item.SetData(nodeId)
        if not foregroundColor is None:
            _logger.debug("altering color of text for node %d", nodeId)
            attr = item.Attr()
            attr.SetTextColour(foregroundColor)
            item.AssignAttributes(attr)
        if checked:
            self.CheckItem(item)
        self._nodeIdToItem[nodeId] = item


    def select_items(self, nodeIds):
        _logger.debug("selecting nodes: %s", nodeIds)
        for nodeId in nodeIds:
            # don't use self.SelectItem since that will send a spurious selchanged event
            self._nodeIdToItem[nodeId].SetHilight()

    def expand_item(self, nodeId):
        _logger.debug("expanding node %d", nodeId)
        self._nodeIdToItem[nodeId].Expand()

    def _set_filter_button_label(self, filterButton, filterLabelFormatPattern, current, total):
        raise Exception("subclass must override this method")

    def _notify_presenter_of_tree_selections(self, nodeIds):
        raise Exception("subclass must override this method")

    def _on_toggle_filter(self, event):
        _logger.debug("handling toggle filter event")
        filterId = self._wxIdToFilterId[event.GetId()]
        self._presenter.set_filter_state(filterId, event.IsChecked())
        event.Skip()

    def _on_sel_changed(self, event):
        '''notifies the presenter that a details pane should be refreshed'''
        _logger.debug("handling tree selection changed event")
        nodeIds = []
        for item in self.GetSelections():
            nodeIds.append(item.GetData())                
        self._notify_presenter_of_tree_selections(nodeIds)
        event.Skip()

    def _on_sel_changing(self, event):
        '''prevents the filter panel row from being selected'''
        _logger.debug("handling tree selection changing event")
        if event.GetItem().GetData() is None:
            event.Veto()
        else:
            event.Skip()
            
    def _on_item_expanded(self, event):
        '''tracks item expansion'''
        _logger.debug("handling tree item expansion event")
        self._presenter.set_node_expanded(event.GetItem().GetData(), True)
        
    def _on_item_collapsed(self, event):
        '''tracks item collapse'''
        _logger.debug("handling tree item collapse event")
        self._presenter.set_node_expanded(event.GetItem().GetData(), False)


class PackagesTree(_FilteredTree):
    def __init__(self, parent, filterIds, filterLabelFormatPatterns, presenter):
        _FilteredTree.__init__(self, parent, filterIds, filterLabelFormatPatterns, presenter)

    def _set_filter_button_label(self, filterButton, filterLabelFormatPattern, current, total):
        label = filterLabelFormatPattern % (current, total)
        filterButton.SetLabel(label)
        filterButton.SetToolTipString("%d of %d package(s) fit search terms" % (current, total))

    def _notify_presenter_of_tree_selections(self, nodeIds):
        self._presenter.set_packages_tree_selections(nodeIds)

    def _on_item_expanded(self, event):
        _logger.debug("handling group expansion event")
        self._presenter.set_group_node_expanded(event.GetItem().GetData(), True)
        
    def _on_item_collapsed(self, event):
        _logger.debug("handling group collapse event")
        self._presenter.set_group_node_expanded(event.GetItem().GetData(), False)


class FilesTree(_FilteredTree):
    def __init__(self, parent, filterIds, filterLabelFormatPatterns, presenter):
        _FilteredTree.__init__(self, parent, filterIds, filterLabelFormatPatterns, presenter)

    def _set_filter_button_label(self, filterButton, filterLabelFormatPattern, current, total):
        filterButton.SetLabel(filterLabelFormatPattern % total)

    def _notify_presenter_of_tree_selections(self, nodeIds):
        self._presenter.set_files_tree_selections(nodeIds)

    def _on_item_expanded(self, event):
        _logger.debug("handling directory expansion event")
        self._presenter.set_dir_node_expanded(event.GetItem().GetData(), True)
        
    def _on_item_collapsed(self, event):
        _logger.debug("handling directory collapse event")
        self._presenter.set_dir_node_expanded(event.GetItem().GetData(), False)
