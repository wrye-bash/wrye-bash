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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Components that can be in one of two states, checked or unchecked."""

from __future__ import annotations

__author__ = u'Infernio'

import wx as _wx

from .base_components import _AComponent

class _ACheckable(_AComponent):
    """A component that can be checked by the user.

    Events:
      - on_checked(checked: bool): Posted when this component's state is
        changed by checking or unchecking it. The parameter is True if this
        component is now checked and False if it is now unchecked.
      - on_context(checkable: _ACheckable): Posted when the user right-clicks
        on this component. The parameter is the instance of _ACheckable that
        was hovered over.
      - on_hovered(hovered: _ACheckable): Posted when the user hovers over this
        component. The parameter is the instance of _ACheckable that was
        hovered over."""
    _native_widget: _wx.CheckBox | _wx.RadioButton

    def __init__(self, *args, **kwargs):
        checked = kwargs.pop(u'checked', False)
        super(_ACheckable, self).__init__(*args, **kwargs)
        self.is_checked = checked
        self._block_user_func = None
        self_proc = lambda _evt: [self]
        self.on_hovered = self._evt_handler(_wx.EVT_ENTER_WINDOW, self_proc)
        self.on_context = self._evt_handler(_wx.EVT_CONTEXT_MENU, self_proc)
        # on_checked needs to be done by subclasses, since the wx event differs

    @property
    def is_checked(self): # type: () -> bool
        """Return True if this component is checked.

        :return: True if this checkbox is checked."""
        return self._native_widget.GetValue()

    @is_checked.setter
    def is_checked(self, new_state): # type: (bool) -> None
        """Mark this component as either checked or unchecked, depending on the
        value of new_state.

        :param new_state: True if this component should be checked, False if it
                          should be unchecked."""
        self._native_widget.SetValue(new_state)

    def block_user(self, block_user_func):
        """Denies all attempts by the user to interact with this checkable and
        runs the specified function when the user does attempt to do so. The
        function will be given a single parameter, the instance of _ACheckable
        that was interacted with."""
        self._block_user_func = block_user_func

    def is_blocked(self):
        """Returns True if user interaction for this component is blocked."""
        return bool(self._block_user_func)

class CheckBox(_ACheckable):
    """Represents a simple two-state checkbox. See _ACheckable for event
    docstrings."""
    _wx_widget_type = _wx.CheckBox
    _native_widget: _wx.CheckBox

    def __init__(self, parent, label=u'', chkbx_tooltip=None, checked=False):
        """Creates a new CheckBox with the specified properties.

        :param parent: The object that this checkbox belongs to. May be a wx
                       object or a component.
        :param label: The text shown on this checkbox.
        :param chkbx_tooltip: A tooltip to show when the user hovers over this
                              checkbox.
        :param checked: The initial state of the checkbox."""
        super(CheckBox, self).__init__(parent, label=label, checked=checked)
        if chkbx_tooltip:
            self.tooltip = chkbx_tooltip
        self.on_checked = self._evt_handler(_wx.EVT_CHECKBOX,
                                            lambda event: [event.IsChecked()])

    def block_user(self, block_user_func):
        super(CheckBox, self).block_user(block_user_func)
        self.on_checked.subscribe(self._do_block_user)

    def _do_block_user(self, checked):
        """Internal event handler to implement the block_user parameter."""
        # Undo the change, then call the function if it was set.
        self.is_checked = not checked
        self._block_user_func(self)

class RadioButton(_ACheckable):
    """A radio button. Once checked, can only be unchecked by checking another
    radio button in the same group. See _ACheckable for event docstrings. Note
    that block_user will only 'freeze' the state of *this* particular radio
    button. You will have to implement some custom logic to freeze an entire
    group of radio buttons."""
    _wx_widget_type = _wx.RadioButton
    _native_widget: _wx.RadioButton

    def __init__(self, parent, label, is_group=False):
        super(RadioButton, self).__init__(parent, label=label,
                                          style=is_group and _wx.RB_GROUP)
        self.on_checked = self._evt_handler(_wx.EVT_RADIOBUTTON,
                                            lambda event: [event.IsChecked()])

    def block_user(self, block_user_func):
        super(RadioButton, self).block_user(block_user_func)
        self.on_checked.subscribe(self._do_block_user)

    def _do_block_user(self, checked):
        self.is_checked = not checked
        self._block_user_func(self)
