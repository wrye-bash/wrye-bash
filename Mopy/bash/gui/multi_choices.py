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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Components that offer a choice from several possible values - whether
through a list, a dropdown, or even a color picker."""
from __future__ import annotations

__author__ = u'nycz, Utumno'

import wx as _wx
import wx.adv as _adv

from .base_components import Color, WithCharEvents, WithMouseEvents, \
    _AComponent
##: de-wx, then move to base_components
from .misc_components import Font

class DropDown(_AComponent):
    """Shows a dropdown with multiple options to pick one from. Often called a
    'combobox'. Features an automatic tooltip if the text of any choice is
    wider than width of control.

    Events:
     - on_combo_select(selected_label: str): Posted when an item on the list is
       selected. The parameter is the new value of selection."""
    _native_widget: _wx.ComboBox

    def __init__(self, parent, value: str, choices: list[str], dd_tooltip=''):
        """Creates a new DropDown with the specified properties.

        :param parent: The object that this dropdown belongs to. May be a wx
                       object or a component.
        :param value: The selected choice, also the text shown on this
                      dropdown.
        :param choices: The choices to show in the dropdown.
        :param dd_tooltip: If set to a non-empty string, sets this DropDown's
            tooltip."""
        # We behave like wx.Choice, but we need some ComboBox methods - hence
        # we use ComboBox and CB_READONLY
        super().__init__(parent, value=value, choices=choices,
            style=_wx.CB_READONLY)
        if dd_tooltip:
            self.tooltip = dd_tooltip
        # Events
        self.on_combo_select = self._evt_handler(_wx.EVT_COMBOBOX,
            lambda event: (event.GetString(),), _wx.CommandEvent)

    def set_choices(self, dd_choices: list[str]):
        """Set the choices shown in this dropdown."""
        self._native_widget.SetItems(dd_choices)

    def set_selection(self, dd_selection: int):
        """Set the choice that is currently selected in this dropdown."""
        self._native_widget.SetSelection(dd_selection)

    def get_value(self) -> str:
        """Get the value of the choice that is currently selected in this
        dropdown."""
        return self._native_widget.GetValue()

class ImageDropDown(DropDown):
    """A version of DropDown that shows a bitmap in front of each entry."""
    _native_widget: _adv.BitmapComboBox

    def set_bitmaps(self, bitmaps):
        """Changes the bitmaps shown in the dropdown."""
        with self.pause_drawing():
            for i, bitmap in enumerate(bitmaps):
                self._native_widget.SetItemBitmap(i, bitmap)

class ColorPicker(_AComponent):
    """A button with a color that launches a color picker dialog.

    Events:
     - on_color_picker_evt(selected_label: bytes): Posted when the button is
       clicked."""
    _native_widget: _wx.ColourPickerCtrl

    def __init__(self, parent, color=None):
        super(ColorPicker, self).__init__(parent)
        if color is not None:
            self.set_color(color)
        self.on_color_picker_evt = self._evt_handler(
            _wx.EVT_COLOURPICKER_CHANGED)

    def get_color(self) -> Color:
        return Color.from_wx(self._native_widget.GetColour())

    def set_color(self, color: Color):
        self._native_widget.SetColour(color.to_rgba_tuple())

class ListBox(WithMouseEvents):
    """A list of options, of which one or more can be selected.

    Events:
      - on_list_box(lb_dex: int, item_text: str): Posted when user selects
      an item from list. The default arg processor extracts the index of the
      event and the list item label
      - Mouse events - see gui.base_components.WithMouseEvents"""
    bind_motion = bind_rclick_down = bind_rclick_up = True
    _native_widget: _wx.ListBox

    def __init__(self, parent, choices: list[str] | None = None, isSingle=True,
            isSort=False, isHScroll=False, isExtended=False, onSelect=None):
        style = 0
        if isSingle: style |= _wx.LB_SINGLE
        if isSort: style |= _wx.LB_SORT
        if isHScroll: style |= _wx.LB_HSCROLL
        if isExtended: style |= _wx.LB_EXTENDED
        kwargs_ = {u'style': style}
        if choices: kwargs_['choices'] = choices
        super().__init__(parent, **kwargs_)
        if onSelect:
            self.on_list_box = self._evt_handler(_wx.EVT_LISTBOX,
                lambda event: (event.GetSelection(), event.GetString(),),
                _wx.CommandEvent)
            self.on_list_box.subscribe(onSelect)

    def lb_select_index(self, lb_selection_dex: int | None):
        self._native_widget.SetSelection( # clear selection if dex is None
            _wx.NOT_FOUND if lb_selection_dex is None else lb_selection_dex)

    def lb_insert(self, str_item: str, lb_selection_dex: int):
        self._native_widget.Insert(str_item, lb_selection_dex)

    def lb_set_items(self, items: list[str]):
        """Replace all the items in the control"""
        self._native_widget.Set(items)

    def lb_set_label_at_index(self, lb_selection_dex: int, str_item: str):
        """Set the label for the given item"""
        self._native_widget.SetString(lb_selection_dex, str_item)

    def lb_delete_at_index(self, lb_selection_dex: int):
        """Delete the item at specified index."""
        self._native_widget.Delete(lb_selection_dex)

    def lb_scroll_lines(self, scroll: int):
        self._native_widget.ScrollLines(scroll)

    def lb_append(self, str_item: str):
        self._native_widget.Append(str_item)

    def lb_clear(self): self._native_widget.Clear()

    def lb_style_font_at_index(self, lb_selection_dex: int, bold=False,
                               italics=False):
        curr_font = self._native_widget.GetFont()
        styled_font = Font.Style(curr_font, strong=bold, slant=italics)
        self._native_widget.SetItemFont(lb_selection_dex, styled_font)

    # Getters - we should encapsulate index access
    def lb_get_str_item_at_index(self, lb_selection_dex: int) -> str:
        return self._native_widget.GetString(lb_selection_dex)

    def lb_get_str_items(self) -> list[str]:
        return self._native_widget.GetStrings()

    def lb_get_selections(self) -> list[int]:
        return self._native_widget.GetSelections()

    def lb_index_for_str_item(self, str_item) -> int | None:
        # return self._native_widget.FindString(str_item) ##: fails on mac check on windows
        try:
            return self.lb_get_str_items().index(str_item)
        except ValueError:
            return None

    def lb_get_vertical_scroll_pos(self) -> int:
        if _wx.Platform == '__WXGTK__':
            ##: Causes 'this window is not scrollable' assertion in wxGTK,
            # see e.g. https://forums.wxwidgets.org/viewtopic.php?t=25153
            return 0
        return self._native_widget.GetScrollPos(_wx.VERTICAL)

    def lb_get_items_count(self) -> int:
        return self._native_widget.GetCount()

    def lb_get_selected_strings(self) -> list[str]:
        return [self.lb_get_str_item_at_index(i)
                for i in self.lb_get_selections()]

    def lb_select_none(self):
        """Entirely clears the selection of this ListBox."""
        self.lb_select_index(None)

    def lb_select_all(self):
        """Selects all items in the ListBox. Pointless if isSingle=True was
        passed to this ListBox."""
        with self.pause_drawing():
            for i in range(self.lb_get_items_count()):
                self.lb_select_index(i)

class CheckListBox(ListBox, WithCharEvents):
    """A list of checkboxes, of which one or more can be selected.

    Events:
      - on_box_checked(index: int): Posted when user checks an item from the
        list. The default arg processor extracts the index of the event.
      - on_context(lb_instance: CheckListBox): Posted when this CheckListBox is
        right-clicked.
      - Mouse events - see gui.base_components.WithMouseEvents.
      - Key events - see gui.base_components.WithCharEvents."""
    # type _native_widget: wx.CheckListBox
    bind_mouse_leaving = bind_lclick_double = True
    _native_widget: _wx.CheckListBox

    # note isSingle=False by default
    def __init__(self, parent, choices: list[str] | None = None,
            isSingle=False, isSort=False, isHScroll=False, isExtended=False,
            onSelect=None):
        super().__init__(parent, choices, isSingle, isSort, isHScroll,
            isExtended, onSelect)
        self.on_box_checked = self._evt_handler(_wx.EVT_CHECKLISTBOX,
            lambda event: (event.GetSelection(),),
            _wx.CommandEvent)
        self.on_context = self._evt_handler(_wx.EVT_CONTEXT_MENU,
                                            lambda event: (self,))

    def lb_check_at_index(self, lb_selection_dex: int, do_check: bool):
        self._native_widget.Check(lb_selection_dex, do_check)

    def lb_is_checked_at_index(self, lb_selection_dex: int) -> bool:
        return self._native_widget.IsChecked(lb_selection_dex)

    def get_checked_strings(self) -> tuple[str, ...]:
        """Returns a tuple of strings corresponding to checked items."""
        return self._native_widget.GetCheckedStrings()

    def toggle_checked_at_index(self, lb_selection_dex):
        do_check = not self.lb_is_checked_at_index(lb_selection_dex)
        self.lb_check_at_index(lb_selection_dex, do_check)

    def set_all_checkmarks(self, checked: bool):
        """Sets all checkmarks to the specified state - checked if True,
        unchecked if False."""
        with self.pause_drawing():
            for i in range(self.lb_get_items_count()):
                self.lb_check_at_index(i, checked)

    def set_all_items(self, keys_values: dict[str, bool]):
        """Completely clears the list and repopulates it using the specified
        key and value lists. Much faster than set_all_items_keep_pos, but
        discards the current scroll position."""
        with self.pause_drawing():
            self.lb_set_items(list(keys_values))
            for i, v in enumerate(keys_values.values()):
                self.lb_check_at_index(i, v)

    ##: Test that the claim below is actually accurate
    def set_all_items_keep_pos(self, keys_values: dict[str, bool]):
        """Convenience method for setting a bunch of wxCheckListBox items. The
        main advantage of this is that it doesn't clear the list unless it
        needs to, which is good if you want to preserve the scroll position
        of the list. If you do not need that behavior, however, use
        set_all_items instead as it is much faster."""
        if not keys_values:
            self.lb_clear()
            return
        with self.pause_drawing():
            for index, (lab, ch) in enumerate(keys_values.items()):
                if index >= self.lb_get_items_count():
                    self.lb_append(lab)
                else:
                    self.lb_set_label_at_index(index, lab)
                self.lb_check_at_index(index, ch)
            for index in range(self.lb_get_items_count(), len(keys_values), -1):
                self.lb_delete_at_index(index - 1)
