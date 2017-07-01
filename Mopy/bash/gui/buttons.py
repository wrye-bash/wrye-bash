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

"""This module defines buttons, offering several predefined templates (e.g. OK
buttons, Cancel buttons, Save As... buttons, etc.)."""

__author__ = u'nycz, Infernio'

import wx as _wx

from .base_components import _AWidget

class _AButton(_AWidget):
    """Abstract base class for all buttons."""
    # TODO(inf) This will be expanded, don't remove

class Button(_AButton):
    """Represents a generic button that can be pressed, triggering an action.
    You probably want one of the more specialized versions of this class
    (e.g. OkButton or CancelButton)."""
    # The ID that will be passed to wx. Controls some OS-specific behavior,
    # e.g. when pressing Tab
    _id = _wx.ID_ANY
    # The label to use when no label was explicitly specified. Set per class.
    default_label = u''

    def __init__(self, parent, label=u'', on_click=None, tooltip=None,
                 default=False):
        """Creates a new Button with the specified properties.

        :param parent: The object that the button belongs to.
        :param label: The text shown on the button.
        :param on_click: A callback to execute when the button isclicked. Takes
                         no parameters.
        :param tooltip: A tooltip to show when the user hovers over the button.
        :param default: If set to True, this button will be the 'default',
                        meaning that if a user selects nothing else and hits
                        Enter, this button will activate."""
        super(Button, self).__init__()
        if not label and self.__class__.default_label:
            label = self.__class__.default_label
        self._native_widget = _wx.Button(parent, self.__class__._id,
                                         label=label, name=u'button')
        if on_click:
            self._native_widget.Bind(_wx.EVT_BUTTON, lambda __evt: on_click)
        if default:
            self._native_widget.SetDefault()
        if tooltip:
            self.tooltip = tooltip

class OkButton(Button):
    """A button with the label 'OK'. Applies pending changes and closes the
    dialog or shows that the user consented to something."""
    _id = _wx.ID_OK
    default_label = _(u'OK')

class CancelButton(Button):
    """A button with the label 'Cancel'. Rejects pending changes or aborts a
    running process."""
    _id = _wx.ID_CANCEL
    default_label = _(u'Cancel')

class SaveButton(Button):
    """A button with the label 'Save'. Saves pending changes or edits by the
    user."""
    _id = _wx.ID_SAVE
    default_label = _(u'Save')

class SaveAsButton(Button):
    """A button with the label 'Save As'. Behaves like the 'Save' button above,
    but shows some type of prompt first, asking the user where to save."""
    _id = _wx.ID_SAVEAS
    default_label = _(u'Save As...')

class RevertButton(Button):
    """A button with the label 'Revert'. Resets pending changes back to the
    default state or undoes any alterations made by the user."""
    _id = _wx.ID_REVERT
    default_label = _(u'Revert')

class RevertToSavedButton(Button):
    """A button with the label 'Revert to Saved'. Resets pending changes back
    to the previous state or undoes one or more alterations made by the
    user."""
    _id = _wx.ID_REVERT_TO_SAVED
    default_label = _(u'Revert to Saved')

class OpenButton(Button):
    """A button with the label 'Open'. Opens a file in an editor or displays
    some other GUI component (i.e. 'open a window')."""
    _id = _wx.ID_OPEN
    default_label = _(u'Open')

class SelectAllButton(Button):
    """A button with the label 'Select All'. Checks all elements in a
    multi-element selection component."""
    _id = _wx.ID_SELECTALL
    default_label = _(u'Select All')

class DeselectAllButton(Button):
    """A button with the label 'Deselect All'. Unchecks all elements in a
    multi-element selection component."""
    _id = _wx.ID_SELECTALL
    default_label = _(u'Deselect All')

class ApplyButton(Button):
    """A button with the label 'Apply'. Applies pending changes without closing
    the dialog."""
    _id = _wx.ID_APPLY
    default_label = _(u'Apply')

class ToggleButton(_AButton):
    """Represents a button that can be toggled on or off."""
    def __init__(self, parent, label=u'', on_toggle=None, tooltip=None):
        """Creates a new ToggleButton with the specified properties.

        :param parent: The object that the button belongs to.
        :param label: The text shown on the button.
        :param on_toggle: A callback to execute when the button is clicked.
                          Takes a single parameter, a boolean that is True if
                          the button is on.
        :param tooltip: A tooltip to show when the user hovers over the
                        button."""
        super(ToggleButton, self).__init__()
        self._native_widget = _wx.ToggleButton(parent, _wx.ID_ANY,
                                               label=label, name=u'button')
        if on_toggle:
            def _toggle_callback(_event): # type: (_wx.Event) -> None
                on_toggle(self._native_widget.GetValue())
            self._native_widget.Bind(_wx.EVT_TOGGLEBUTTON, _toggle_callback)
        if tooltip:
            self.tooltip = tooltip

    @property
    def toggled(self): # type: () -> bool
        """Returns True if this button is toggled on.

        :return: True if this button is toggled on."""
        return self._native_widget.GetValue()

    @toggled.setter
    def toggled(self, value): # type: (bool) -> None
        """Toggles this button on if the specified parameter is True.

        :param value: Whether to toggle this button on or off."""
        self._native_widget.SetValue(value)

class CheckBox(_AButton):
    """Represents a simple two-state checkbox."""
    def __init__(self, parent, label=u'', on_toggle=None, tooltip=None,
                 checked=False):
        """Creates a new CheckBox with the specified properties.

        :param parent: The object that the checkbox belongs to.
        :param label: The text shown on the checkbox.
        :param on_toggle: A callback to execute when the button is clicked.
                          Takes a single parameter, a boolean that is True if
                          the checkbox is checked.
        :param tooltip: A tooltip to show when the user hovers over the
                        checkbox.
        :param checked: The initial state of the checkbox."""
        super(CheckBox, self).__init__()
        self._native_widget = _wx.CheckBox(parent, _wx.ID_ANY,
                                           label=label, name=u'checkBox')
        if on_toggle:
            def _toggle_callback(_event): # type: (_wx.Event) -> None
                on_toggle(self._native_widget.GetValue())
            self._native_widget.Bind(_wx.EVT_CHECKBOX, _toggle_callback)
        if tooltip:
            self.tooltip = tooltip
        self.checked = checked

    @property
    def checked(self): # type: () -> bool
        """Returns True if this checkbox is checked.

        :return: True if this checkbox is checked."""
        return self._native_widget.GetValue()

    @checked.setter
    def checked(self, value): # type: (bool) -> None
        """Checks or unchecks this checkbox depending on the specified
        parameter.

        :param value: Whether to check or uncheck this checkbox."""
        self._native_widget.SetValue(value)
