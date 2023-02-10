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
"""This module defines buttons, offering several predefined templates (e.g. OK
buttons, Cancel buttons, Save As... buttons, etc.)."""
from __future__ import annotations

__author__ = u'nycz, Infernio'

import wx as _wx

from .base_components import _AComponent
from .. import bass

class Button(_AComponent):
    """Represents a generic button that can be pressed, triggering an action.
    When appropriate, use one of the more specialized versions of this class
    (e.g. OkButton or CancelButton).

    Events:
     - on_clicked(): Posted when the button is clicked.
     - on_right_clicked(): Posted when the button is right-clicked."""
    _native_widget: _wx.Button
    # The ID that will be passed to wx. Controls some OS-specific behavior,
    # e.g. when pressing Tab
    _id = _wx.ID_ANY
    # The label to use when no label was explicitly specified. Set per class.
    _default_label = u''

    def __init__(self, parent, btn_label: str = '', btn_tooltip: str = '',
            default: bool = False, exact_fit: bool = False,
            no_border: bool = False):
        """Creates a new Button with the specified properties.

        :param parent: The object that this button belongs to. May be a wx
                       object or a component.
        :param btn_label: The text shown on this button.
        :param btn_tooltip: A tooltip to show when the user hovers over this
                            button.
        :param default: If set to True, this button will be the 'default',
                        meaning that if a user selects nothing else and hits
                        Enter, this button will activate.
        :param exact_fit: If set to True, will fit the size of this button
                          exactly to its contents.
        :param no_border: If set to True, the borders of this button will be
                          hidden."""
        if not btn_label and self.__class__._default_label:
            btn_label = self.__class__._default_label
        btn_style = 0
        if exact_fit:
            btn_style |= _wx.BU_EXACTFIT
        if no_border:
            btn_style |= _wx.BORDER_NONE
        super().__init__(parent, self.__class__._id, style=btn_style,
            label=self._escape(btn_label))
        if default:
            self._native_widget.SetDefault()
        if btn_tooltip:
            self.tooltip = btn_tooltip
        # Events
        self.on_clicked = self._evt_handler(_wx.EVT_BUTTON)
        self.on_right_clicked = self._evt_handler(_wx.EVT_CONTEXT_MENU)

    @property
    def button_label(self) -> str:
        """Returns the label on this button as a string.

        :return: The label on this button."""
        return self._unescape(self._native_widget.GetLabel())

    @button_label.setter
    def button_label(self, new_btn_label):
        """Changes the label on this button to the specified string.

        :param new_btn_label: The new label to use."""
        if self.button_label != new_btn_label:
            self._native_widget.SetLabel(new_btn_label)

class OkButton(Button):
    """A button with the label 'OK'. Applies pending changes and closes the
    dialog or shows that the user consented to something. Note that if you use
    this button, it will be set as the default as soon as you initialize it. If
    you want a different button to be the default, initialize that button after
    this button and pass default=True for it.

    See Button for documentation on button events."""
    _id = _wx.ID_OK
    _default_label = _(u'OK')

    def __init__(self, *args, **kwargs):
        super(OkButton, self).__init__(*args, default=True, **kwargs)

class CancelButton(Button):
    """A button with the label 'Cancel'. Rejects pending changes or aborts a
    running process.

    See Button for documentation on button events."""
    _id = _wx.ID_CANCEL
    _default_label = _(u'Cancel')

class SaveButton(Button):
    """A button with the label 'Save'. Saves pending changes or edits by the
    user.

    See Button for documentation on button events."""
    _id = _wx.ID_SAVE
    _default_label = _(u'Save')

class SaveAsButton(Button):
    """A button with the label 'Save As'. Behaves like the 'Save' button above,
    but shows some type of prompt first, asking the user where to save."""
    _id = _wx.ID_SAVEAS
    _default_label = _(u'Save As...')

class RevertButton(Button):
    """A button with the label 'Revert'. Resets pending changes back to the
    default state or undoes any alterations made by the user.

    See Button for documentation on button events."""
    _id = _wx.ID_REVERT
    _default_label = _(u'Revert')

class RevertToSavedButton(Button):
    """A button with the label 'Revert to Saved'. Resets pending changes back
    to the previous state or undoes one or more alterations made by the
    user.

    See Button for documentation on button events."""
    _id = _wx.ID_REVERT_TO_SAVED
    _default_label = _(u'Revert to Saved')

class OpenButton(Button):
    """A button with the label 'Open'. Opens a file in an editor or displays
    some other GUI component (i.e. 'open a window').

    See Button for documentation on button events."""
    _id = _wx.ID_OPEN
    _default_label = _(u'Open')

class SelectAllButton(Button):
    """A button with the label 'Select All'. Checks all elements in a
    multi-element selection component.

    See Button for documentation on button events."""
    _id = _wx.ID_SELECTALL
    _default_label = _(u'Select All')

class DeselectAllButton(Button):
    """A button with the label 'Deselect All'. Unchecks all elements in a
    multi-element selection component.

    See Button for documentation on button events."""
    _id = _wx.ID_SELECTALL
    _default_label = _(u'Deselect All')

class ApplyButton(Button):
    """A button with the label 'Apply'. Applies pending changes without closing
    the dialog.

    See Button for documentation on button events."""
    _id = _wx.ID_APPLY
    _default_label = _(u'Apply')

class BackButton(Button):
    """A button with the label '< Back'. Moves to a previous element.

    See Button for documentation on button events."""
    _id = _wx.ID_BACKWARD
    _default_label = u'< %s' % _(u'Back')

class NextButton(Button):
    """A button with the label 'Next >'. Moves to a next element.

    See Button for documentation on button events."""
    _id = _wx.ID_FORWARD
    _default_label = u'%s >' % _(u'Next')

# TODO(inf) Image API! Need to get rid of all bitmaps passed to this
class ImageButton(Button):
    """A button that display an image alongside its label.

    See Button for documentation on button events."""
    def __init__(self, parent, wx_bitmap=None, **kwargs):
        """Creates a new _AImageButton with the specified properties. See
        Button for documentation on all other keyword arguments.

        :param wx_bitmap: The bitmap shown on this button."""
        super(ImageButton, self).__init__(parent, **kwargs)
        self.image = wx_bitmap

    @property
    def image(self): # type: () -> _wx.Bitmap
        """Returns the image that is shown on this button.

        :return: The image on this button."""
        return self._native_widget.GetBitmap()

    @image.setter
    def image(self, new_image): # type: (_wx.Bitmap) -> None
        """Changes the image that is shown on this button to the specified
        image.

        :param new_image: The image that should be shown on this button."""
        self._native_widget.SetBitmap(new_image)
        # Changing bitmap may change the 'best size', so resize it
        self._native_widget.SetInitialSize()

class PureImageButton(ImageButton):
    """An image that acts like a button. Has no text, but does have a border.

    See Button for documentation on button events.

    See also ClickableImage."""
    def __init__(self, parent, wx_bitmap, *, btn_tooltip: str):
        """Creates a new ClickableImage with the specified properties.

        :param parent: The object that this button belongs to. May be a wx
                       object or a component.
        :param wx_bitmap: The image id to be shown on this button.
        :param btn_tooltip: A tooltip to show when the user hovers over this
            button. Required for accessibility purposes - without it users
            would have to guess based on the image."""
        super().__init__(parent, wx_bitmap, btn_tooltip=btn_tooltip,
            exact_fit=True)

class ClickableImage(ImageButton):
    """An image that acts like a button. Has no text and no borders.

    See Button for documentation on button events.

    See also PureImageButton."""
    def __init__(self, parent, wx_bitmap, *, btn_tooltip: str):
        """Creates a new ClickableImage with the specified properties.

        :param parent: The object that this button belongs to. May be a wx
                       object or a component.
        :param wx_bitmap: The image id to be shown on this button.
        :param btn_tooltip: A tooltip to show when the user hovers over this
            button. Required for accessibility purposes - without it users
            would have to guess based on the image."""
        super().__init__(parent, wx_bitmap, btn_tooltip=btn_tooltip,
            exact_fit=True, no_border=True)
