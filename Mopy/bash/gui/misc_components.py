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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This module houses GUI classes that did not fit anywhere else. Once similar
classes accumulate in here, feel free to break them out into a module."""

__author__ = u'nycz, Infernio'

import wx as _wx

from .base_components import _AComponent
from .events import EventHandler

class CheckBox(_AComponent):
    """Represents a simple two-state checkbox.

    Events:
     - on_checked(checked: bool): Posted when this checkbox's state is changed
       by checking or unchecking it. The parameter is True if the checkbox is
       now checked and False if it is now unchecked."""
    def __init__(self, parent, label=u'', tooltip=None, checked=False):
        """Creates a new CheckBox with the specified properties.

        :param parent: The object that this checkbox belongs to. May be a wx
                       object or a component.
        :param label: The text shown on this checkbox.
        :param tooltip: A tooltip to show when the user hovers over this
                        checkbox.
        :param checked: The initial state of the checkbox."""
        super(CheckBox, self).__init__()
        # Create native widget
        self._native_widget = _wx.CheckBox(self._resolve(parent), _wx.ID_ANY,
                                           label=label, name=u'checkBox')
        if tooltip:
            self.tooltip = tooltip
        self.is_checked = checked
        # Events
        self.on_checked = EventHandler(self._native_widget, _wx.EVT_CHECKBOX,
                                       lambda event: [event.IsChecked()])

    @property
    def is_checked(self): # type: () -> bool
        """Returns True if this checkbox is checked.

        :return: True if this checkbox is checked."""
        return self._native_widget.GetValue()

    @is_checked.setter
    def is_checked(self, new_state): # type: (bool) -> None
        """Marks this checkbox as either checked or unchecked, depending on the
        value of new_state.

        :param new_state: True if this checkbox should be checked, False if it
                          should be unchecked."""
        self._native_widget.SetValue(new_state)
