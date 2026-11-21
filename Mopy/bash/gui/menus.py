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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2026 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Houses wrappers of wx.Menu related classes."""
from __future__ import annotations

from enum import Enum

import wx as _wx

from .base_components import AObject, _AEvtHandler

class MenuItemKind(Enum):
    """What an item of a Menu is: a command, a check box or a radio item."""
    NORMAL = _wx.ITEM_NORMAL
    CHECK = _wx.ITEM_CHECK
    RADIO = _wx.ITEM_RADIO

class MenuItem(AObject):
    """An item of a Menu, that returned it on appending it. It dies with its
    menu, unbeknownst to us - set its state right then, do not keep it."""
    _native_widget: _wx.MenuItem

    @property
    def enabled(self) -> bool:
        """Whether the user can select this item."""
        return self._native_widget.IsEnabled()

    @enabled.setter
    def enabled(self, is_enabled: bool):
        self._native_widget.Enable(is_enabled)

    @property
    def is_checked(self) -> bool:
        """Whether this check or radio item is checked."""
        return self._native_widget.IsChecked()

    @is_checked.setter
    def is_checked(self, is_checked: bool):
        self._native_widget.Check(is_checked)

class Menu(_AEvtHandler):
    """A menu, popped up or of the menu bar - the links append their items
    and submenus to it."""
    _native_widget: _wx.Menu

    def append_item(self, item_label: str, item_help: str, on_selected,
                    kind=MenuItemKind.NORMAL, keyboard_hint='') -> MenuItem:
        """Append an item that calls on_selected when the user selects it."""
        item_label = self._escape(item_label)
        if keyboard_hint: # \u200b: a hint, not a wx accelerator
            item_label += f'\t{keyboard_hint}\u200b'
        # Note default id here is *not* ID_ANY but the special ID_SEPARATOR!
        native_item = _wx.MenuItem(self._native_widget, _wx.ID_ANY, item_label,
                                   item_help, kind.value)
        # wx tries the item's menu first - the binding dies with the menu
        self._native_widget.Bind(_wx.EVT_MENU, lambda _event: on_selected(),
                                 native_item)
        self._native_widget.Append(native_item)
        return MenuItem._wrap_object(native_item, type_check=False)

    def append_submenu(self, menu_label: str) -> tuple[Menu, MenuItem]:
        """Append a submenu - return it, and its item in this menu."""
        sub_menu = Menu()
        return sub_menu, MenuItem._wrap_object(
            self._native_widget.AppendSubMenu(sub_menu._native_widget,
                self._escape(menu_label)), type_check=False)

    def append_separator(self):
        """Append a line separating the items before it and after it."""
        self._native_widget.AppendSeparator()

    def append_break(self):
        """Have the items appended next start a new column."""
        self._native_widget.Break()

    def clear_items(self):
        """Destroy our items, and the bindings of append_item with them."""
        for native_item in self._native_widget.GetMenuItems():
            self._native_widget.Unbind(_wx.EVT_MENU, native_item)
            self._native_widget.DestroyItem(native_item)

    def item_help(self, item_id: int) -> str:
        """The help of our item with that wx id - '' if we have none."""
        native_item = self._native_widget.FindItemById(item_id)
        return native_item.GetHelp() if native_item else ''

class Links:
    """List of menu or button links."""
    # The Menu currently popped up, or opened in the menu bar
    Popup = None

    def __init__(self):
        self._link_list = []

    def popup_menu(self, parent, selection):
        """Pops up a new menu from these links."""
        to_popup = Menu()
        try:
            for link in self._link_list:
                link.AppendToMenu(to_popup, parent, selection)
            Links.Popup = to_popup
            AObject._resolve(parent).PopupMenu(to_popup._native_widget)
        finally:
            to_popup.native_destroy()
            Links.Popup = None # do not leak the menu reference

    # self._link_list accessors
    def append_link(self, l):
        """Append a link to this Links instance."""
        self._link_list.append(l)

    def clear_links(self):
        """Remove all links from this Links instance."""
        self._link_list.clear()

    def __len__(self): return len(self._link_list)

    def __iter__(self): return self._link_list.__iter__()
