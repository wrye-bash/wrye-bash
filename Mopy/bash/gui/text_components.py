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

"""This module contains all text-related GUI components. For example, text
input components like TextArea and TextField, but also static components like
Label reside here."""

__author__ = u'nycz, Infernio'

import wx as _wx
import wx.adv as _adv

from .base_components import _AComponent

# Text Input ------------------------------------------------------------------
class _ATextInput(_AComponent):
    """Abstract base class for all text input classes.

    Events:
     - on_focus_lost(): Posted when this text input goes out of focus. Used in
       WB to auto-save edits.
     - on_right_clicked(): Posted when this text input is right-clicked.
     - on_text_changed(new_text: unicode): Posted when the text in this text
       input changes. Be warned that changing it via _ATextInput.text_content
       also posts this event, so if you have to change text in response to this
       event, use _ATextInput.modified to check if it was a user modification;
       otherwise, you risk getting into an infinite loop.

    :type _native_widget: _wx.TextCtrl"""
    # TODO: (fixed) font(s)
    def __init__(self, parent, init_text=None, multiline=True, editable=True,
                 auto_tooltip=True, max_length=None, no_border=False, style=0):
        """Creates a new _ATextInput instance with the specified properties.

        :param parent: The object that this text input belongs to. May be a wx
                       object or a component.
        :param init_text: The initial text in this text input.
        :param multiline: True if this text input allows multiple lines.
        :param editable: True if the user may edit text in this text input.
        :param auto_tooltip: Whether or not to automatically show a tooltip
                             when the entered text exceeds the length of this
                             text input.
        :param max_length: The maximum number of characters that can be
                           entered into this text input. None if you don't
                           want a limit.
        :param no_border: True if the borders of this text input should be
                          hidden.
        :param style: Internal parameter used to allow subclasses to wrap style
                      flags on their own."""
        # Construct the native widget
        if multiline: style |= _wx.TE_MULTILINE
        if not editable: style |= _wx.TE_READONLY
        if no_border: style |= _wx.BORDER_NONE
        super(_ATextInput, self).__init__(_wx.TextCtrl, parent, style=style)
        if init_text: self._native_widget.SetValue(init_text)
        if max_length:
            self._native_widget.SetMaxLength(max_length)
        # Events
        # Internal use only - used to implement auto_tooltip below
        self._on_size_changed = self._evt_handler(_wx.EVT_SIZE)
        self.on_focus_lost = self._evt_handler(_wx.EVT_KILL_FOCUS)
        self.on_right_clicked = self._evt_handler(_wx.EVT_CONTEXT_MENU)
        self.on_text_changed = self._evt_handler(_wx.EVT_TEXT,
                                            lambda event: [event.GetString()])
        # Need to delay this until now since it uses the events from above
        if auto_tooltip:
            self._on_size_changed.subscribe(self._on_size_change)
            self.on_text_changed.subscribe(self._update_tooltip)

    def _update_tooltip(self, new_text): # type: (unicode) -> None
        """Internal callback that shows or hides the tooltip depending on the
        length of the currently entered text and the size of this text input.

        :param new_text: The text inside this text input."""
        n_widget = self._native_widget
        if n_widget.GetClientSize()[0] < n_widget.GetTextExtent(new_text)[0]:
            self.tooltip = new_text
        else:
            self.tooltip = None

    def _on_size_change(self):
        """Internal callback that updates the tooltip when the size changes."""
        self._update_tooltip(self._native_widget.GetValue())

    @property
    def editable(self): # type: () -> bool
        """Returns True if this text input can be edited by the user.

        :return: True if this text input is editable."""
        return self._native_widget.IsEditable()

    @editable.setter
    def editable(self, is_editable): # type: (bool) -> None
        """Enables or disables user input to this text input based on the
        specified parameter.

        :param is_editable: Whether to enable or disable user input."""
        self._native_widget.SetEditable(is_editable)

    @property
    def text_content(self): # type: () -> unicode
        """Returns the text that is currently inside this text input.

        :return: The entered text."""
        return self._native_widget.GetValue()

    @text_content.setter
    def text_content(self, new_text): # type: (unicode) -> None
        """Changes the text inside this text input to the specified string.

        :param new_text: What to change this text input's text to."""
        self._native_widget.SetValue(new_text)

    @property
    def modified(self): # type: () -> bool
        """Returns True if the user has modified the text inside this text
        input.

        :return: True if this text input has been modified."""
        return self._native_widget.IsModified()

    @modified.setter
    def modified(self, is_modified):
        """Changes whether or not this text input is modified based on the
        specified parameter.

        :param is_modified: True if this text input should be marked as
                            modified."""
        self._native_widget.SetModified(is_modified)

class TextArea(_ATextInput):
    """A multi-line text edit widget. See the documentation for _ATextInput
    for a list of the events this component offers."""
    def __init__(self, parent, init_text=None, editable=True,
                 auto_tooltip=True, max_length=None, no_border=False,
                 do_wrap=True):
        """Creates a new TextArea instance with the specified properties.

        :param parent: The object that this text area belongs to. May be a wx
                       object or a component.
        :param init_text: The initial text in this text area.
        :param editable: True if the user may edit text in this text area.
        :param auto_tooltip: Whether or not to automatically show a tooltip
                             when the entered text exceeds the length of this
                             text area.
        :param max_length: The maximum number of characters that can be
                           entered into this text area. None if you don't
                           want a limit.
        :param no_border: True if the borders of this text area should be
                          hidden.
        :param do_wrap: Whether or not to wrap text inside this text area."""
        wrap_style = _wx.TE_DONTWRAP if not do_wrap else 0
        super(TextArea, self).__init__(parent, init_text=init_text,
                                       editable=editable,
                                       auto_tooltip=auto_tooltip,
                                       max_length=max_length,
                                       no_border=no_border, style=wrap_style)

class TextField(_ATextInput):
    """A single-line text edit widget. See the documentation for _ATextInput
    for a list of the events this component offers."""
    def __init__(self, parent, init_text=None, editable=True,
                 auto_tooltip=True, max_length=None, no_border=False):
        """Creates a new TextField instance with the specified properties.

        :param parent: The object that this text field belongs to. May be a wx
                       object or a component.
        :param init_text: The initial text in this text field.
        :param editable: True if the user may edit text in this text field.
        :param auto_tooltip: Whether or not to automatically show a tooltip
                             when the entered text exceeds the length of this
                             text field.
        :param max_length: The maximum number of characters that can be
                           entered into this text field. None if you don't
                           want a limit.
        :param no_border: True if the borders of this text field should be
                          hidden."""
        super(TextField, self).__init__(parent, init_text=init_text,
                                        multiline=False, editable=editable,
                                        auto_tooltip=auto_tooltip,
                                        max_length=max_length,
                                        no_border=no_border)

# Labels ----------------------------------------------------------------------
class _ALabel(_AComponent):
    """Abstract base class for labels."""
    @property
    def label_text(self): # type: () -> unicode
        """Returns the text of this label as a string.

        :return: The text of this label."""
        return self._native_widget.GetLabel()

    @label_text.setter
    def label_text(self, new_text): # type: (unicode) -> None
        """Changes the text of this label to the specified string.

        :param new_text: The new text to use."""
        self._native_widget.SetLabel(new_text)

class Label(_ALabel):
    """A static text element. Doesn't have a border and the text can't be
    interacted with by the user."""
    # _native_widget: type: _wx.StaticText
    def __init__(self, parent, init_text):
        """Creates a new Label with the specified parent and text.

        :param parent: The object that this label belongs to.
        :param init_text: The initial text of this label."""
        super(Label, self).__init__(_wx.StaticText, parent, _wx.ID_ANY,
                                    init_text)
        self._init_text = init_text

    def wrap(self, max_length): # type: (int) -> None
        """Wraps this label's text so that each line is at most max_length
        pixels long.

        :param max_length: The maximum number of pixels a line may be long."""
        self._native_widget.Freeze()
        self._native_widget.SetLabel(self._init_text)
        self._native_widget.Wrap(max_length)
        self._native_widget.Thaw()

class HyperlinkLabel(_ALabel):
    """A label that opens a URL when clicked, imitating a hyperlink in a
    browser. Typically styled blue."""
    def __init__(self, parent, init_text, url, always_unvisited=False):
        """Creates a new HyperlinkLabel with the specified parent, text and
        URL.

        :param parent: The object that this hyperlink label belongs to. May be
                       a wx object or a component.
        :param init_text: The initial text of this hyperlink label.
        :param url: The URL to open when this hyperlink label is clicked on.
        :param always_unvisited: If set to True, this link will always appear
                                 as if it hasn't been clicked on (i.e. blue -
                                 it will never turn purple)."""
        super(HyperlinkLabel, self).__init__(_adv.HyperlinkCtrl, parent,
                                             _wx.ID_ANY, init_text, url)
        if always_unvisited:
            self._native_widget.SetVisitedColour(
                self._native_widget.GetNormalColour())
