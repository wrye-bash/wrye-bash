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

from . import filter_panel


_logger = logging.getLogger(__name__)


class _FilteredTree(wx.Panel):
    '''Provides a tree with a filter panel at the top'''
    def __init__(self, parent, filterIds, filterLabelFormatPatterns, presenter_, setFilterButtonLabelFn=None):
        wx.Panel.__init__(self, parent, style=wx.SUNKEN_BORDER)

        tree = self._tree = CT.CustomTreeCtrl(self, style=wx.NO_BORDER,
                agwStyle=CT.TR_HAS_VARIABLE_ROW_HEIGHT|CT.TR_HAS_BUTTONS|CT.TR_HIDE_ROOT|CT.TR_MULTIPLE|CT.TR_NO_LINES)
        self.SetBackgroundColour(tree.GetBackgroundColour())
        filterPanel = self._filterPanel = filter_panel.FilterPanel(self, filterIds, filterLabelFormatPatterns, presenter_, setFilterButtonLabelFn=setFilterButtonLabelFn)

        topSizer = wx.BoxSizer(wx.VERTICAL)
        topSizer.Add(filterPanel, 0, wx.EXPAND)
        topSizer.Add(tree, 1, wx.EXPAND)
        self.SetSizer(topSizer)
        
        # create tree base
        tree.AddRoot("root")
        self._presenter = presenter_
        self._nodeIdToItem = {}
        self._checkedIconMap = {}
        self._uncheckedIconMap = {}
        
        # bind to events
        tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_sel_changed)
        tree.Bind(wx.EVT_TREE_ITEM_EXPANDED, self._on_item_expanded)
        tree.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self._on_item_collapsed)


    def start(self, filterStateMap):
        self._filterPanel.start(filterStateMap)

    def clear(self):
        _logger.debug("clearing tree")
        self._tree.DeleteChildren(self._tree.GetRootItem())
        self._nodeIdToItem = {} # reset mappings

    def set_filter_stats(self, filterId, current, total):
        self._filterPanel.set_filter_stats(filterId, current, total)

    def set_checkbox_images(self, checkedIconMap, uncheckedIconMap):
        self._checkedIconMap = {}
        self._uncheckedIconMap = {}
        imageList = None
        idx = 0
        for iconMap, _iconMap in ((checkedIconMap, self._checkedIconMap), (uncheckedIconMap, self._uncheckedIconMap)):
            for iconId in iconMap:
                _iconMap[iconId] = idx;
                idx = idx + 1
                bitmap = wx.Bitmap(iconMap[iconId])
                if imageList is None:
                    width, height = bitmap.GetSize()
                    imageList = wx.ImageList(width, height, False, 0)
                imageList.Add(bitmap)
        if not imageList is None:
            self._tree.SetImageListCheck(width, height, imageList)

    def add_item(self, nodeId, label, parentNodeId, predNodeId, isBold, isItalics, textColor, hilightColor, checkboxState, iconId):
        _logger.debug("adding node %d: '%s'", nodeId, label)
        if parentNodeId is None:
            parent = self._tree.GetRootItem()
        else:
            parent = self._nodeIdToItem[parentNodeId]
        predecessor = None
        if not predNodeId is None:
            predecessor = self._nodeIdToItem[predNodeId]

        if checkboxState is None:
            ct_type = 0
            checked = False
        else:
            ct_type = 1
            checked = checkboxState

        item = self._tree.InsertItem(parent, predecessor, label, ct_type)
        item.SetData(nodeId)
        
        if not iconId is None:
            # item has no SetCheckedImage method, so fake it
            item._checkedimages[CT.TreeItemIcon_Checked] = self._checkedIconMap[iconId]
            item._checkedimages[CT.TreeItemIcon_NotChecked] = self._uncheckedIconMap[iconId]

        attr = item.Attr()
        if not textColor is None:
            _logger.debug("altering color of text for node %d", nodeId)
            attr.SetTextColour(textColor)
        if not hilightColor is None:
            _logger.debug("altering color of highlight for node %d", nodeId)
            attr.SetBackgroundColour(hilightColor)
        if isBold:
            _logger.debug("setting node %d text to bold", nodeId)
            item.SetBold(True)
        if isItalics:
            _logger.debug("setting node %d text to italics", nodeId)
            item.SetItalic(True)
        if checked:
            self._tree.CheckItem(item)
        item.AssignAttributes(attr)
        self._nodeIdToItem[nodeId] = item


    def select_items(self, nodeIds):
        _logger.debug("selecting nodes: %s", nodeIds)
        for nodeId in nodeIds:
            # don't use self.SelectItem since that will send a spurious selchanged event
            self._nodeIdToItem[nodeId].SetHilight()

    def expand_item(self, nodeId):
        _logger.debug("expanding node %d", nodeId)
        self._nodeIdToItem[nodeId].Expand()

    def _notify_presenter_of_tree_selections(self, nodeIds):
        raise Exception("subclass must override this method")

    def _on_sel_changed(self, event):
        '''notifies the presenter that a details pane should be refreshed'''
        _logger.debug("handling tree selection changed event")
        nodeIds = []
        for item in self._tree.GetSelections():
            nodeIds.append(item.GetData())                
        self._notify_presenter_of_tree_selections(nodeIds)
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
        _FilteredTree.__init__(self, parent, filterIds, filterLabelFormatPatterns, presenter, setFilterButtonLabelFn=self._set_filter_button_label)

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

    def _notify_presenter_of_tree_selections(self, nodeIds):
        self._presenter.set_files_tree_selections(nodeIds)

    def _on_item_expanded(self, event):
        _logger.debug("handling directory expansion event")
        self._presenter.set_dir_node_expanded(event.GetItem().GetData(), True)
        
    def _on_item_collapsed(self, event):
        _logger.debug("handling directory collapse event")
        self._presenter.set_dir_node_expanded(event.GetItem().GetData(), False)
