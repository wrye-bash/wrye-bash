# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, either version 3
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <https://www.gnu.org/licenses/>.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""List control wrapper - this is the main control that Bash uses to display
mods, saves, inis, installers etc"""
from __future__ import annotations

__author__ = u'Lojack, Utumno'

import pickle

import wx as _wx
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin

from . import EventHandler
from .base_components import Color, WithCharEvents, WithMouseEvents, \
    _auto_size_to_wx
from .. import bolt

class _DragListCtrl(_wx.ListCtrl, ListCtrlAutoWidthMixin):
    """List control extended with the wxPython auto-width mixin class.

    Also extended to support drag-and-drop.  To define custom drag-and-drop
    functionality, you can provide callbacks for, or override the following functions:
    OnDropFiles(self, x, y, filenames) - called when files are dropped in the list control
    OnDropIndexes(self,indexes,newPos) - called to move the specified indexes to new starting position 'newPos'
    You must provide a callback for fnDndAllow(self, event) - return true to
    allow dnd, false otherwise

    OnDropFiles callback:   fnDropFiles
    OnDropIndexes callback: fnDropIndexes
    """
    class DropFileOrList(_wx.DropTarget):

        def __init__(self, window, dndFiles, dndList):
            super().__init__()
            self.window = window
            self.data_object = _wx.DataObjectComposite()
            self.dataFile = _wx.FileDataObject()                 # Accept files
            self.dataList = _wx.CustomDataObject(u'ListIndexes')  # Accept indexes from a list
            if dndFiles: self.data_object.Add(self.dataFile)
            if dndList : self.data_object.Add(self.dataList)
            self.SetDataObject(self.data_object)

        def OnData(self, x, y, _data):
            if self.GetData():
                dtype = self.data_object.GetReceivedFormat().GetType()
                if dtype == _wx.DF_FILENAME:
                    # File(s) were dropped
                    self.window.OnDropFiles(x, y, self.dataFile.GetFilenames())
                    return _wx.DragCopy
                elif dtype == self.dataList.GetFormat().GetType():
                    # ListCtrl indexes
                    _data = pickle.loads(self.dataList.GetData().tobytes(),
                                         encoding='bytes')
                    self.window._OnDropList(x, y, _data)
                    return _wx.DragCopy
            return _wx.DragNone

        def OnDragOver(self, x, y, dragResult):
            self.window.OnDragging(x,y,dragResult)
            return _wx.DropTarget.OnDragOver(self,x,y,dragResult)

    def __init__(self, parent, fnDndAllow, style=0, dndFiles=False,
                 dndList=False, fnDropFiles=None, fnDropIndexes=None,
                 dndOnlyMoveContinuousGroup=True):
        _wx.ListCtrl.__init__(self, parent, style=style)
        ListCtrlAutoWidthMixin.__init__(self)
        if dndFiles or dndList:
            self.SetDropTarget(_DragListCtrl.DropFileOrList(self, dndFiles, dndList))
            if dndList:
                self.Bind(_wx.EVT_LIST_BEGIN_DRAG, self.OnBeginDrag)
        self.dndOnlyCont = dndOnlyMoveContinuousGroup
        self.fnDropFiles = fnDropFiles
        self.fnDropIndexes = fnDropIndexes
        self.fnDndAllow = fnDndAllow

    def OnDragging(self,x,y,dragResult):
        # We're dragging, see if we need to scroll the list
        index, _hit_flags = self.HitTest((x, y))
        if index == _wx.NOT_FOUND:   # Didn't drop it on an item
            if self.GetItemCount() > 0:
                if y <= self.GetItemRect(0).y:
                    # Mouse is above the first item
                    self.LineUp()
                elif y >= self.GetItemRect(self.GetItemCount() - 1).y:
                    # Mouse is after the last item
                    self.LineDown()
        else:
            # Screen position if item hovering over
            pos = index - self.GetScrollPos(_wx.VERTICAL)
            if pos == 0:
                # Over the first item, see if it's over the top half
                rect = self.GetItemRect(index)
                if y < rect.y + rect.height/2:
                    self.LineUp()
            elif pos == self.GetCountPerPage():
                # On last item/one that's not fully visible
                self.LineDown()

    def OnBeginDrag(self, event):
        if not self.fnDndAllow(event): return
        indexes = []
        start = stop = -1
        for index in range(self.GetItemCount()):
            if self.GetItemState(index, _wx.LIST_STATE_SELECTED):
                if stop >= 0 and self.dndOnlyCont:
                    # Only allow moving selections if they are in a
                    # continuous block...they aren't
                    return
                if start < 0:
                    start = index
                indexes.append(index)
            else:
                if start >=0 > stop:
                    stop = index - 1
        if stop < 0: stop = self.GetItemCount()
        selected = pickle.dumps(indexes, 1)
        ldata = _wx.CustomDataObject(u'ListIndexes')
        ldata.SetData(selected)
        data_object = _wx.DataObjectComposite()
        data_object.Add(ldata)
        source = _wx.DropSource(self)
        source.SetData(data_object)
        source.DoDragDrop(flags=_wx.Drag_DefaultMove)

    def OnDropFiles(self, x, y, filenames):
        if self.fnDropFiles:
            _wx.CallLater(10,self.fnDropFiles,x,y,filenames)

    def _OnDropList(self, x, y, indexes):
        start = indexes[0]
        stop = indexes[-1]
        index, _hit_flags = self.HitTest((x, y))
        if index == _wx.NOT_FOUND:   # Didn't drop it on an item
            if self.GetItemCount() > 0:
                if y <= self.GetItemRect(0).y:
                    # Dropped it before the first item
                    index = 0
                elif y >= self.GetItemRect(self.GetItemCount() - 1).y:
                    # Dropped it after the last item
                    index = self.GetItemCount()
                else:
                    # Dropped it on the edge of the list, but not above or below
                    return
            else:
                # Empty list
                index = 0
        else:
            # Dropped on top of an item
            target = index
            if start <= target <= stop:
                # Trying to drop it back on itself
                return
            elif target < start:
                # Trying to drop it furthur up in the list
                pass
            elif target > stop:
                # Trying to drop it further down the list
                index -= 1 + (stop-start)
            # If dropping on the top half of the item, insert above it,
            # otherwise insert below it
            rect = self.GetItemRect(target)
            if y > rect.y + rect.height/2:
                index += 1
        # Do the moving
        self.OnDropIndexes(indexes, index)

    def OnDropIndexes(self, indexes, newPos):
        if self.fnDropIndexes:
            _wx.CallLater(10,self.fnDropIndexes,indexes,newPos)

class UIListCtrl(WithMouseEvents, WithCharEvents):
    """Backing list control for UILists. Wraps a wx list control, which needs
    a peculiar system with internal ids to support sorting PY3: something simpler?
    ALWAYS add new items via InsertListCtrlItem() and delete them via
    RemoveItemAt().
    Events:
      - on_item_selected(uilist_item_key): on clicking on an item on the list -
      type of uilist_item_key varies, usually a Path
    """
    bind_motion = True
    bind_mouse_leaving = bind_lclick_double = bind_lclick_down = True
    _native_widget: _DragListCtrl

    def __init__(self, parent, allow_edit, is_border_sunken, is_single_select,
            *args, **kwargs):
        kwargs['style'] = _wx.LC_REPORT | (allow_edit and _wx.LC_EDIT_LABELS
            ) | (is_border_sunken and _wx.BORDER_SUNKEN) | (
                is_single_select and _wx.LC_SINGLE_SEL)
        super(UIListCtrl, self).__init__(parent, *args, **kwargs)
        evt_col = lambda event: [event.GetColumn()]
        self.on_lst_col_rclick = self._evt_handler(
            _wx.EVT_LIST_COL_RIGHT_CLICK, evt_col)
        self.on_context_menu = self._evt_handler(_wx.EVT_CONTEXT_MENU)
        self.on_lst_col_click = self._evt_handler(_wx.EVT_LIST_COL_CLICK,
                                                   evt_col)
        self.on_lst_col_end_drag = self._evt_handler(_wx.EVT_LIST_COL_END_DRAG,
                                                     evt_col)
        self.on_item_selected = self._evt_handler(_wx.EVT_LIST_ITEM_SELECTED,
            lambda event: [self.FindItemAt(event.GetIndex())])
        if allow_edit:
            self.on_edit_label_begin = self._evt_handler(
                _wx.EVT_LIST_BEGIN_LABEL_EDIT,
                lambda event: [event.GetLabel(), self])
            self.on_edit_label_end = self._evt_handler(
                _wx.EVT_LIST_END_LABEL_EDIT,
                lambda event: [event.IsEditCancelled(), event.GetLabel(),
                    event.GetIndex(), self.FindItemAt(event.GetIndex())])
        #--Item/Id mapping
        self._item_itemId: dict[bolt.FName | str | int, int] = {}
        self._itemId_item: dict[int, bolt.FName | str | int] = {}

    # API (beta) -------------------------------------------------------------
    # Internal id <-> item mappings used in wx._controls.ListCtrl.SortItems
    __item_id = 0
    def __id(self, item):
        self.__class__.__item_id += 1
        self._item_itemId[item] = self.__item_id
        self._itemId_item[self.__item_id] = item
        return self.__item_id

    def InsertListCtrlItem(self, index, value, item, decorate_cb):
        """Insert an item to the list control giving it an internal id.

        :param decorate_cb: A callback that will be passed the created wx item.
            Use this to set properties on the item once before it is inserted
            into the ListCtrl via SetItem."""
        i = self.__id(item)
        new_index = self._native_widget.InsertItem(index, value)
        if new_index == -1:
            raise RuntimeError(f'Failed to insert UIList item {value}')
        # The item/row is inserted now, but all ancillary data has to be added
        # to the actual wx object, then committed (see below)
        gItem = self._native_widget.GetItem(new_index)
        # Associate our internal id with this item/row
        gItem.SetData(i)
        ##: de-wx! This is a wx object escaping - should be internal-only,
        # need to absorb __setUI in gui and export a public API like
        # ListItemFormat for that
        decorate_cb(gItem)
        # This commits the actual changed data in the ListCtrl
        self._native_widget.SetItem(gItem)

    def RemoveItemAt(self, index):
        """Remove item at specified list index."""
        itemId = self._native_widget.GetItemData(index)
        item = self._itemId_item[itemId]
        del self._item_itemId[item]
        del self._itemId_item[itemId]
        self._native_widget.DeleteItem(index)

    def DeleteAll(self):
        self._item_itemId.clear()
        self._itemId_item.clear()
        self._native_widget.DeleteAllItems()

    def FindIndexOf(self, item):
        """Return index of specified item."""
        return self._native_widget.FindItem(-1, self._item_itemId[item])

    def FindItemAt(self, index):
        """Return item for specified list index."""
        return self._itemId_item[self._native_widget.GetItemData(index)]

    def ReorderDisplayed(self, inorder):
        """Reorder the list control displayed items to match inorder."""
        sortDict = {self._item_itemId[y]: x for x, y in enumerate(inorder)}
        self._native_widget.SortItems(lambda x, y: bolt.cmp_(sortDict[x], sortDict[y]))

    # native edit control wrappers
    def __ec(self): # may return None on mac
        return self._native_widget.GetEditControl()

    def ec_set_selection(self, start, stop):
        (ec := self.__ec()) and ec.SetSelection(start, stop)

    def ec_get_selection(self):
        return (ec := self.__ec()) and ec.GetSelection()

    def ec_set_f2_handler(self, on_char_handler):
        """Sets a handler for when the F2 key is pressed. Note that you have to
        return EventResult.FINISH when handling this event."""
        ec = self.__ec()
        if ec is None: return
        on_char = EventHandler(ec, _wx.EVT_KEY_DOWN,
                               lambda event: [event.GetKeyCode() == _wx.WXK_F2,
                                              ec.GetValue(), self])
        on_char.subscribe(on_char_handler)

    def ec_rename_prompt_opened(self):
        """Returns True if the rename prompt is currently open."""
        return self.__ec() is not None

    ##: column wrappers - belong to a superclass that wraps ListCtrl
    def lc_get_columns_count(self) -> int:
        return self._native_widget.GetColumnCount()

    def lc_get_column_width(self, evt_col: int) -> int:
        return self._native_widget.GetColumnWidth(evt_col)

    def lc_set_column_width(self, evt_col: int, column_width: int):
        self._native_widget.SetColumnWidth(evt_col, column_width)

    def lc_set_auto_column_width(self, evt_col: int, auto_col: int):
        self._native_widget.SetColumnWidth(evt_col, _auto_size_to_wx[auto_col])

    def lc_item_count(self) -> int:
        return self._native_widget.GetItemCount()

    def lc_get_column(self, colDex: int):
        return self._native_widget.GetColumn(colDex)

    def lc_insert_column(self, colDex: int, colName: str):
        self._native_widget.InsertColumn(colDex, colName)

    def lc_delete_column(self, colDex: int):
        self._native_widget.DeleteColumn(colDex)

    def lc_select_item_at_index(self, index: int, select=True,
                                __select=_wx.LIST_STATE_SELECTED):
        self._native_widget.SetItemState(index, select * __select, __select)

    # wrappers for UIList used methods ----------------------------------------
    def get_selected_index(self, after=-1, *, __next_all=_wx.LIST_NEXT_ALL,
                           __state_selected=_wx.LIST_STATE_SELECTED):
        """Get selected indexes after the specified index - if not specified
        get first selected index."""
        return self._native_widget.GetNextItem(after, __next_all,
                                               __state_selected)

    def set_item_data(self, *args):
        self._native_widget.SetItem(*args)

    def get_item_data(self, dex):
        return self._native_widget.GetItem(dex)

    def get_text_color(self):
        return Color.from_wx(self._native_widget.GetTextColour())

    def resize_last_col(self):
        self._native_widget.resizeLastColumn(0)

    def focus_index(self, dex):
        self._native_widget.Focus(dex)

    def ensure_visible_index(self, dex):
        self._native_widget.EnsureVisible(dex)

    def edit_label(self, dex):
        self._native_widget.EditLabel(dex)

    # Images
    def set_image_list(self, image_list, *, __which=_wx.IMAGE_LIST_SMALL):
        self._native_widget.SetImageList(self._resolve(image_list), __which)

    def clear_col_image(self, col_dex):
        self._native_widget.ClearColumnImage(col_dex)

    def set_col_image(self, col_dex, image):
        self._native_widget.SetColumnImage(col_dex, image)

    # Scroll
    def get_scroll_pos(self, is_vertical):
        return self._native_widget.GetScrollPos(
            _wx.VERTICAL if is_vertical else _wx.HORIZONTAL)

    def set_scroll_pos(self, pos):
        return self._native_widget.ScrollLines(pos)
