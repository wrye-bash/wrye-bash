# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Houses wrappers of wx.Menu related classes."""
from __future__ import annotations

import wx as _wx

from .base_components import _AComponent, Lazy

class Links(Lazy):
    """List of menu or button links."""
    # Current popup menu, set in Links.popup_menu()
    Popup = None
    _native_widget: _wx.Menu

    def __init__(self):
        super().__init__()
        self._link_list = []

    def popup_menu(self, parent, selection):
        """Pops up a new menu from these links."""
        self.create_widget()
        to_popup = self._native_widget
        for link in self._link_list:
            link.AppendToMenu(to_popup, parent, selection)
        Links.Popup = to_popup
        if isinstance(parent, _AComponent):
            parent.show_popup_menu(to_popup)
        else:
            # TODO de-wx! Only use in BashNotebook
            parent.PopupMenu(to_popup)
        self.destroy_component()
        Links.Popup = None # do not leak the menu reference

    # self._link_list accessors
    def append_link(self, l):
        """Append a link to this Links instance."""
        self._link_list.append(l)

    def clear_links(self):
        """Remove all links from this Links instance."""
        self._link_list.clear()

    def __getitem__(self, item):
        self._link_list.__getitem__(item)

    def __len__(self): return len(self._link_list)

    def __iter__(self): return self._link_list.__iter__()
