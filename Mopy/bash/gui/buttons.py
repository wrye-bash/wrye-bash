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
from .events import EventHandler

class _AButton(_AWidget):
    """Abstract base class for all buttons."""
    # TODO(inf) This will be expanded, don't remove

class Button(_AButton):
    """Represents a generic button that can be pressed, triggering an action.
    You probably want one of the more specialized versions of this class
    (e.g. OkButton or CancelButton).

    Events:
     - on_clicked(): Posted when the button is clicked."""
    # The ID that will be passed to wx. Controls some OS-specific behavior,
    # e.g. when pressing Tab
    _id = _wx.ID_ANY
    # The label to use when no label was explicitly specified. Set per class.
    default_label = u''

    def __init__(self, parent, label=u'', tooltip=None, default=False):
        """Creates a new Button with the specified properties.

        :param parent: The object that the button belongs to.
        :param label: The text shown on the button.
        :param tooltip: A tooltip to show when the user hovers over the button.
        :param default: If set to True, this button will be the 'default',
                        meaning that if a user selects nothing else and hits
                        Enter, this button will activate."""
        super(Button, self).__init__()
        # Create native widget
        if not label and self.__class__.default_label:
            label = self.__class__.default_label
        self._native_widget = _wx.Button(parent, self.__class__._id,
                                         label=label, name=u'button')
        if default:
            self._native_widget.SetDefault()
        if tooltip:
            self.tooltip = tooltip
        # Events
        self.on_clicked = EventHandler(self._native_widget, _wx.EVT_BUTTON)

class OkButton(Button):
    """A button with the label 'OK'. Applies pending changes and closes the
    dialog or shows that the user consented to something.

    See Button for documentation on button events."""
    _id = _wx.ID_OK
    default_label = _(u'OK')

class CancelButton(Button):
    """A button with the label 'Cancel'. Rejects pending changes or aborts a
    running process.

    See Button for documentation on button events."""
    _id = _wx.ID_CANCEL
    default_label = _(u'Cancel')

class SaveButton(Button):
    """A button with the label 'Save'. Saves pending changes or edits by the
    user.

    See Button for documentation on button events."""
    _id = _wx.ID_SAVE
    default_label = _(u'Save')

class SaveAsButton(Button):
    """A button with the label 'Save As'. Behaves like the 'Save' button above,
    but shows some type of prompt first, asking the user where to save."""
    _id = _wx.ID_SAVEAS
    default_label = _(u'Save As...')

class RevertButton(Button):
    """A button with the label 'Revert'. Resets pending changes back to the
    default state or undoes any alterations made by the user.

    See Button for documentation on button events."""
    _id = _wx.ID_REVERT
    default_label = _(u'Revert')

class RevertToSavedButton(Button):
    """A button with the label 'Revert to Saved'. Resets pending changes back
    to the previous state or undoes one or more alterations made by the
    user.

    See Button for documentation on button events."""
    _id = _wx.ID_REVERT_TO_SAVED
    default_label = _(u'Revert to Saved')

class OpenButton(Button):
    """A button with the label 'Open'. Opens a file in an editor or displays
    some other GUI component (i.e. 'open a window').

    See Button for documentation on button events."""
    _id = _wx.ID_OPEN
    default_label = _(u'Open')

class SelectAllButton(Button):
    """A button with the label 'Select All'. Checks all elements in a
    multi-element selection component.

    See Button for documentation on button events."""
    _id = _wx.ID_SELECTALL
    default_label = _(u'Select All')

class DeselectAllButton(Button):
    """A button with the label 'Deselect All'. Unchecks all elements in a
    multi-element selection component.

    See Button for documentation on button events."""
    _id = _wx.ID_SELECTALL
    default_label = _(u'Deselect All')

class ApplyButton(Button):
    """A button with the label 'Apply'. Applies pending changes without closing
    the dialog.

    See Button for documentation on button events."""
    _id = _wx.ID_APPLY
    default_label = _(u'Apply')
