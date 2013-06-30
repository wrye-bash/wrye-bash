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


class _FilteredTree:
    '''Provides a tree with a filter panel at the top'''
    def __init__(self, wxParent, sizer, filterIds, filterLabels, presenter_,
                 filterRegistry, selectionNotificationFn, nodeExpansionNotificationFn):
        panel = self._panel = wx.Panel(wxParent, style=wx.SUNKEN_BORDER)
        tree = self._tree = CT.CustomTreeCtrl(panel, style=wx.NO_BORDER,
                agwStyle=CT.TR_HAS_VARIABLE_ROW_HEIGHT|CT.TR_HAS_BUTTONS|\
                         CT.TR_HIDE_ROOT|CT.TR_MULTIPLE|CT.TR_NO_LINES)
        panel.SetBackgroundColour(tree.GetBackgroundColour())
        topSizer = wx.BoxSizer(wx.VERTICAL)
        filterPanel = filter_panel.FilterPanel(
            panel, topSizer, filterIds, filterLabels, presenter_, filterRegistry)
        topSizer.Add(tree, 1, wx.EXPAND)
        panel.SetSizer(topSizer)
        sizer.Add(panel, 1, wx.EXPAND)

        # create tree base
        tree.AddRoot("root")
        self._presenter = presenter_
        self._selectionNotificationFn = selectionNotificationFn
        self._nodeExpansionNotificationFn = nodeExpansionNotificationFn
        self._nodeIdToItem = {}

        # bind to events
        tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_sel_changed)
        tree.Bind(wx.EVT_TREE_ITEM_EXPANDED, self._on_item_expanded)
        tree.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self._on_item_collapsed)
        tree.Bind(wx.EVT_TREE_ITEM_GETTOOLTIP, self._on_tree_tooltip)


    def set_enabled(self, enabled):
        self._panel.Enable(enabled)

    def add_node(self, nodeId, label, isExpanded, parentNodeId, predecessorNodeId,
                 contextMenuId, isSelected, isBold, isItalics, textColor, highlightColor,
                 checkboxState, iconId):
        _logger.debug("adding node %d: '%s'", nodeId, label)
        if parentNodeId is None:
            parent = self._tree.GetRootItem()
        else:
            parent = self._nodeIdToItem[parentNodeId]

        predecessor = None
        if not predecessorNodeId is None:
            predecessor = self._nodeIdToItem[predecessorNodeId]

        if checkboxState is None:
            ct_type = 0
            checked = False
        else:
            ct_type = 1
            checked = checkboxState

        item = self._tree.InsertItem(parent, predecessor, label, ct_type)
        item.SetData((nodeId, contextMenuId))

        self._set_item_attributes(nodeId, item, isExpanded, isBold, isItalics, textColor,
                                  highlightColor, checked)
        self._set_icon(item, iconId)

        if isSelected:
            _logger.debug("highlighting node %d", nodeId)
            # don't use self.SelectItem since that will send a spurious selchanged event
            item.SetHilight()

        self._nodeIdToItem[nodeId] = item


    def update_node(self, nodeId, label, isExpanded, isBold, isItalics, textColor,
                    highlightColor, checkboxState, iconId):
        _logger.debug("updating node %d", nodeId)
        item = self._nodeIdToItem[nodeId]
        if label is not None:
            _logger.debug("updating node %d label to: '%s'", nodeId, label)
            item.SetText(label)
        self._set_item_attributes(nodeId, item, isExpanded, isBold, isItalics, textColor,
                                  highlightColor, checkboxState)
        self._set_icon(item, iconId)

    def move_node(self, nodeId, predNodeId):
        _logger.debug("moving node %d to below %s", nodeId, predNodeId)
        item = self._nodeIdToItem[nodeId]
        parentItem = item.GetParent()
        predItem = self._nodeIdToItem[predNodeId] if predNodeId is not None else None
        # copy branch
        branchCopy = {}
        self._copy_branch(nodeId, item, branchCopy)
        # delete branch -- just do it directly, no need to bind to the events; we'll be
        # overwriting the nodeIdToItem map elements anyway, and labels don't need to be
        # updated for the packages tree subclass since they will not change
        self._tree.Delete(item)
        # paste copy below predecessorNodeId
        self._paste_branch(nodeId, parentItem, predItem, branchCopy)

    def remove_node(self, nodeId):
        def on_item_deleted(event):
            nodeId = event.GetItem().GetData()[0]
            _logger.debug("removing node %d from the tree", nodeId)
            if nodeId in self._nodeIdToItem:
                del self._nodeIdToItem[nodeId]
                self._on_item_deleted(nodeId)
        if nodeId in self._nodeIdToItem:
            _logger.debug("removing subtree rooted at %d", nodeId)
            self._tree.Bind(wx.EVT_TREE_DELETE_ITEM, on_item_deleted)
            self._tree.Delete(self._nodeIdToItem[nodeId])
            self._tree.Unbind(wx.EVT_TREE_DELETE_ITEM)
        else:
            _logger.debug("skipping removing already-pruned subtree rooted at %d", nodeId)

    def clear(self):
        _logger.debug("clearing tree")
        self._tree.DeleteChildren(self._tree.GetRootItem())
        self._nodeIdToItem = {} # reset mappings

    def _set_icon(self, item, iconId):
        # overridden in PackagesTree subclass
        pass

    def _set_item_attributes(self, nodeId, item, isExpanded, isBold, isItalics, textColor,
                             highlightColor, checkboxState):
        if isExpanded is not None:
            if isExpanded:
                _logger.debug("expanding node %d", nodeId)
                item.Expand()
            else:
                _logger.debug("collapsing node %d", nodeId)
                item.Collapse()

        attr = item.Attr()
        if textColor is not None:
            _logger.debug("altering color of text for node %d", nodeId)
            attr.SetTextColour(textColor)
        if highlightColor is not None:
            _logger.debug("altering color of highlight for node %d", nodeId)
            attr.SetBackgroundColour(highlightColor)
        if isBold is not None:
            if isBold:
                _logger.debug("setting node %d text to bold", nodeId)
                item.SetBold(True)
            else:
                _logger.debug("setting node %d text to unbold", nodeId)
                item.SetBold(False)
        if isItalics is not None:
            if isItalics:
                _logger.debug("setting node %d text to italics", nodeId)
                item.SetItalic(True)
            else:
                _logger.debug("setting node %d text to non italics", nodeId)
                item.SetItalic(False)

        if checkboxState is not None:
            item.Check(checkboxState)
        item.AssignAttributes(attr)


    def _copy_branch(self, nodeId, item, destDict):
        """dict tuples are (label, type, data, isExpanded, isBold, isItalics, textColor,
                            highlightColor, checked, checkedIcon, uncheckedIcon,
                            isSelected, [childrenNodeIds])"""
        # copy branch rooted at nodeId
        childrenNodeIds = []
        attr = item.GetAttributes()
        destDict[nodeId] = (item.GetText(), item.GetType(), item.GetData(),
                            item.IsExpanded(), item.IsBold(), item.IsItalic(),
                            attr.GetTextColour(), attr.GetBackgroundColour(),
                            item.IsChecked(),
                            item._checkedimages[CT.TreeItemIcon_Checked],
                            item._checkedimages[CT.TreeItemIcon_NotChecked],
                            item.IsSelected(), childrenNodeIds)
        for childItem in item.GetChildren():
            childNodeId = item.GetData()[0]
            childrenNodeIds.append(childNodeId)
            self._copy_branch(childNodeId, childItem, destDict)

    def _paste_branch(self, nodeId, parentItem, predItem, srcDict):
        itemData = srcDict[nodeId]
        item = self._tree.InsertItemByItem(parentItem, predItem, itemData[0],
                                           ct_type=itemData[1], data=itemData[2])
        self._set_item_attributes(nodeId, item, itemData[3], itemData[4], itemData[5],
                                  itemData[6], itemData[7], itemData[8])
        item._checkedimages[CT.TreeItemIcon_Checked] = itemData[9]
        item._checkedimages[CT.TreeItemIcon_NotChecked] = itemData[10]
        item.SetHilight(itemData[11])
        self._nodeIdToItem[nodeId] = item
        for childNodeId in itemData[12]:
            self._paste_branch(childNodeId, parentItem, item, srcDict)

    def _on_sel_changed(self, event):
        '''notifies the presenter that tree selection has changed'''
        _logger.debug("handling tree selection changed event")
        nodeIds = []
        for item in self._tree.GetSelections():
            nodeIds.append(item.GetData()[0])
        self._selectionNotificationFn(nodeIds)
        event.Skip()

    def _on_item_expanded(self, event):
        '''tracks item expansion'''
        _logger.debug("handling tree item expansion event")
        self._nodeExpansionNotificationFn(event.GetItem().GetData()[0], True)
        event.Skip()

    def _on_item_collapsed(self, event):
        '''tracks item collapse'''
        _logger.debug("handling tree item collapse event")
        self._nodeExpansionNotificationFn(event.GetItem().GetData()[0], False)
        event.Skip()

    def _on_tree_tooltip(self, event):
        _logger.debug("getting tooltip")
        item = event.GetItem()
        if item:
            tree = self._tree
            rect = tree.GetBoundingRect(item, textOnly=True)
            if rect and (rect.GetLeft() < 0 or
                         tree.GetSize()[0] < rect.GetLeft()+rect.GetWidth()):
                text = tree.GetItemText(item)
                if text:
                    event.SetToolTip(wx.ToolTip(text))

    def _on_item_deleted(self, nodeId):
        # overridden by PackagesTree
        pass


class PackagesTree(_FilteredTree):
    def __init__(self, wxParent, sizer, filterIds, filterLabels,
                 presenter_, filterRegistry):
        _FilteredTree.__init__(self, wxParent, sizer, filterIds, filterLabels, presenter_,
                               filterRegistry, presenter_.set_packages_tree_selections,
                               presenter_.set_group_node_expanded)
        self.nodeIdToLabelMap = {}
        self._checkedIconMap = {}
        self._uncheckedIconMap = {}
        self._tree.Bind(wx.EVT_CONTEXT_MENU, self._on_context_menu)
        self._tree.Bind(wx.EVT_LEFT_DCLICK, self._on_double_click)

    def add_node(self, nodeId, label, *args):
        _FilteredTree.add_node(self, nodeId, label, *args)
        self.nodeIdToLabelMap[nodeId] = label

    def update_node(self, nodeId, label, *args):
        _FilteredTree.update_node(self, nodeId, label, *args)
        if label is not None:
            self.nodeIdToLabelMap[nodeId] = label

    def clear(self):
        _FilteredTree.clear(self)
        self.nodeIdToLabelMap = {}

    def set_checkbox_images(self, checkedIconMap, uncheckedIconMap):
        self._checkedIconMap = {}
        self._uncheckedIconMap = {}
        imageList = None
        idx = 0
        for iconMap, _iconMap in ((checkedIconMap, self._checkedIconMap),
                                  (uncheckedIconMap, self._uncheckedIconMap)):
            for iconId in iconMap:
                _iconMap[iconId] = idx;
                idx = idx + 1
                image = wx.Image(iconMap[iconId])
                if image.HasMask() and not image.HasAlpha():
                    image.InitAlpha()
                bitmap = image.ConvertToBitmap()
                if imageList is None:
                    width, height = bitmap.GetSize()
                    imageList = wx.ImageList(width, height, False, 0)
                imageList.Add(bitmap)
        if not imageList is None:
            self._tree.SetImageListCheck(width, height, imageList)

    def _on_item_deleted(self, nodeId):
        del self.nodeIdToLabelMap[nodeId]

    def _set_icon(self, item, iconId):
        if not iconId is None:
            # item has no SetCheckedImage method, so fake it
            item._checkedimages[CT.TreeItemIcon_Checked] = self._checkedIconMap[iconId]
            item._checkedimages[CT.TreeItemIcon_NotChecked] = \
                self._uncheckedIconMap[iconId]

    def _on_double_click(self, event):
        _logger.debug("handling double click event")
        # TODO send "open package" command to the presenter

    def _on_context_menu(self, event):
        _logger.debug("showing files context menu")
        # TODO: respect contextMenuId of the given item
        menu = wx.Menu()

        fileMenu = wx.Menu()
        fileMenu.Append(-1, "Open")
        fileMenu.Append(-1, "Rename...")
        fileMenu.Append(-1, "Duplicate...")
        fileMenu.Append(-1, "Delete")
        menu.AppendMenu(-1, "File", fileMenu)

        packageMenu = wx.Menu()
        packageMenu.Append(-1, "List structure")
        packageMenu.Append(-1, "Force refresh")
        packageMenu.AppendSeparator()
        # TODO: only enable if archive
        packageMenu.Append(-1, "Create BCF...")
        packageMenu.Append(-1, "Apply BCF...")
        packageMenu.Append(-1, "Extract to project...")
        packageMenu.AppendSeparator()
        # TODO: only enable if project
        packageMenu.Append(-1, "Sync from data")
        packageMenu.Append(-1, "Pack to archive...")
        packageMenu.Append(-1, "Pack to release archive...")
        menu.AppendMenu(-1, "Package", packageMenu)

        webMenu = wx.Menu()
        webMenu.Append(-1, "Open homepage")
        webMenu.Append(-1, "Set homepage...")
        webMenu.AppendSeparator()
        webMenu.Append(-1, "Search for in Google")
        menu.AppendMenu(-1, "Web", webMenu)

        moveMenu = wx.Menu()
        moveMenu.Append(-1, "To top")
        moveMenu.Append(-1, "To bottom")
        moveMenu.Append(-1, "To group...")
        moveMenu.Append(-1, "To position...")
        menu.AppendMenu(-1, "Move", moveMenu)

        groupMenu = wx.Menu()
        groupMenu.Append(-1, "Create from selected packages...")
        groupMenu.Append(-1, "Ignore internal conflicts", kind=wx.ITEM_CHECK)
        menu.AppendMenu(-1, "Group", groupMenu)

        menu.AppendSeparator()
        menu.Append(-1, "Manual wizard...")
        menu.Append(-1, "Auto wizard...")
        menu.Append(-1, "Edit wizard...")
        menu.AppendSeparator()
        menu.Append(-1, "Anneal")
        menu.Append(-1, "Install")
        menu.Append(-1, "Uninstall")
        menu.AppendSeparator()
        menu.Append(-1, "Hide/unhide")
        self._tree.PopupMenu(menu)
        menu.Destroy()

class PackageContentsTree(_FilteredTree):
    def __init__(self, wxParent, sizer, filterIds, filterLabels,
                 presenter_, filterRegistry):
        _FilteredTree.__init__(self, wxParent, sizer, filterIds, filterLabels, presenter_,
                               filterRegistry, presenter_.set_files_tree_selections,
                               presenter_.set_dir_node_expanded)
        self._tree.Bind(wx.EVT_CONTEXT_MENU, self._on_context_menu)
        self._tree.Bind(wx.EVT_LEFT_DCLICK, self._on_double_click)

    def _on_double_click(self, event):
        _logger.debug("handling double click event")
        # TODO send "open file" command to the presenter

    def _on_context_menu(self, event):
        _logger.debug("showing files context menu")
        # TODO: respect contextMenuId of the given item
        menu = wx.Menu()
        menu.Append(-1, "Open")
        menu.Append(-1, "Check")
        menu.Append(-1, "Uncheck")
        menu.Append(-1, "Select all")
        menu.Append(-1, "Copy to project...")
        # TODO: delete (if project)
        # TODO: rename on install (if .bsa)
        self._tree.PopupMenu(menu)
        menu.Destroy()
