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

from .base_components import _AComponent
from .events import EventHandler

class _AButton(_AComponent):
    """Abstract base class for all buttons."""
    # TODO(inf) This will be expanded, don't remove

class Button(_AButton):
    """Represents a generic button that can be pressed, triggering an action.
    You probably want one of the more specialized versions of this class
    (e.g. OkButton or CancelButton).

    Events:
     - on_clicked(): Posted when the button is clicked.
     - on_right_clicked(): Posted when the button is right-clicked."""
    # The ID that will be passed to wx. Controls some OS-specific behavior,
    # e.g. when pressing Tab
    _id = _wx.ID_ANY
    # The label to use when no label was explicitly specified. Set per class.
    default_label = u''

    def __init__(self, parent, label=u'', tooltip=None, default=False,
                 exact_fit=False, no_border=False):
        """Creates a new Button with the specified properties.

        :param parent: The object that this button belongs to. May be a wx
                       object or a component.
        :param label: The text shown on this button.
        :param tooltip: A tooltip to show when the user hovers over this
                        button.
        :param default: If set to True, this button will be the 'default',
                        meaning that if a user selects nothing else and hits
                        Enter, this button will activate.
        :param exact_fit: If set to True, will fit the size of this button
                          exactly to its contents.
        :param no_border: If set to True, the borders of this button will be
                          hidden."""
        super(Button, self).__init__()
        # Create native widget
        if not label and self.__class__.default_label:
            label = self.__class__.default_label
        btn_style = 0
        if exact_fit:
            btn_style |= _wx.BU_EXACTFIT
        if no_border:
            btn_style |= _wx.BORDER_NONE
        self._native_widget = _wx.Button(self._resolve(parent),
                                         self.__class__._id, label=label,
                                         name=u'button', style=btn_style)
        if default:
            self._native_widget.SetDefault()
        if tooltip:
            self.tooltip = tooltip
        # Events
        self.on_clicked = EventHandler(self._native_widget, _wx.EVT_BUTTON)
        self.on_right_clicked = EventHandler(self._native_widget,
                                             _wx.EVT_CONTEXT_MENU)

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

# TODO(inf) Image API! Need to get rid of all bitmaps passed to this
class ImageButton(Button):
    """A button that display an image alongside its label.

    See Button for documentation on button events."""
    # TODO(inf) This implementation locks us into wx 2.9+
    # Since wx 2.8 can't do bitmaps with a regular button
    def __init__(self, parent, image, label=u'', tooltip=None, default=False,
                 exact_fit=False, no_border=False):
        """Creates a new _AImageButton with the specified properties.

        :param parent: The object that this button belongs to. May be a wx
                       object or a component.
        :param image: The image shown on this button.
        :param label: The text shown on this button.
        :param tooltip: A tooltip to show when the user hovers over this
                        button.
        :param default: If set to True, this button will be the 'default',
                        meaning that if a user selects nothing else and hits
                        Enter, this button will activate.
        :param exact_fit: If set to True, will fit the size of this button
                          exactly to its contents.
        :param no_border: If set to True, the borders of this button will be
                          hidden."""
        super(ImageButton, self).__init__(parent, label=label, tooltip=tooltip,
                                          default=default, exact_fit=exact_fit,
                                          no_border=no_border)
        self.image = image

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

class BackwardButton(ImageButton):
    """An image button with no text that displays an arrow pointing to the
    right. Used for navigation, e.g. in a browser.

    See Button for documentation on button events."""
    def __init__(self, parent):
        """Creates a new BackwardButton with the specified parent.

        :param parent: The object that this button belongs to. May be a wx
                       object or a component."""
        backward_image = _wx.ArtProvider.GetBitmap(
            _wx.ART_GO_BACK, _wx.ART_HELP_BROWSER, (16, 16))
        super(BackwardButton, self).__init__(parent, backward_image,
                                             tooltip=_(u'Go Back'),
                                             exact_fit=True)

class ForwardButton(ImageButton):
    """An image button with no text that displays an arrow pointing to the
    right. Used for navigation, e.g. in a browser.

    See Button for documentation on button events."""
    def __init__(self, parent):
        """Creates a new ForwardButton with the specified parent.

        :param parent: The object that this button belongs to. May be a wx
                       object or a component."""
        forward_image = _wx.ArtProvider.GetBitmap(
            _wx.ART_GO_FORWARD, _wx.ART_HELP_BROWSER, (16, 16))
        super(ForwardButton, self).__init__(parent, forward_image,
                                            tooltip=_(u'Go Forwards'),
                                            exact_fit=True)

class ReloadButton(ImageButton):
    """An image button with no text that displays two arrows in a circle. Used
    for reloading documents, websites, etc.

    See Button for documentation on button events."""
    def __init__(self, parent):
        """Creates a new ReloadButton with the specified parent.

        :param parent: The object that this button belongs to. May be a wx
                       object or a component."""
        # TODO(inf) Image API! This is really, really ugly
        from .. import bass
        reload_icon = _wx.Bitmap(bass.dirs[u'images'].join(u'reload16.png').s,
                                 _wx.BITMAP_TYPE_PNG)
        super(ReloadButton, self).__init__(parent, reload_icon,
                                           tooltip=_(u'Reload'),
                                           exact_fit=True)

class ClickableImage(ImageButton):
    """An image that acts like a button. Has no text and no borders.

    See Button for documentation on button events."""
    def __init__(self, parent, image, tooltip=None):
        """Creates a new ClickableImage with the specified properties.

        :param parent: The object that this button belongs to. May be a wx
                       object or a component.
        :param image: The image shown on this button.
        :param tooltip: A tooltip to show when the user hovers over this
                        button."""
        super(ClickableImage, self).__init__(parent, image, tooltip=tooltip,
                                             exact_fit=True, no_border=True)
