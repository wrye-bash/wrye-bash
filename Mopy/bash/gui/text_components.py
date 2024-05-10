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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module contains all text-related GUI components. For example, text
input components like TextArea and TextField, but also static components like
Label reside here."""
from __future__ import annotations

__author__ = u'nycz, Infernio'

from enum import Enum

import wx as _wx
import wx.adv as _adv
from wx.lib.stattext import GenStaticText as _GenStaticTextWx
from wx.lib.wordwrap import wordwrap as _wordwrap_wx

from .base_components import _AComponent, scaled
from .events import EventResult

# Text Input ------------------------------------------------------------------
class TextAlignment(Enum):
    LEFT = 0
    RIGHT = 1
    CENTER = 2

_ta_to_wx = {
    TextAlignment.LEFT: _wx.TE_LEFT,
    TextAlignment.RIGHT: _wx.TE_RIGHT,
    TextAlignment.CENTER: _wx.TE_CENTER,
}

class _ATextInput(_AComponent):
    """Abstract base class for all text input classes.

    Events:
     - on_focus_lost(): Posted when this text input goes out of focus. Used in
       WB to auto-save edits.
     - on_right_clicked(): Posted when this text input is right-clicked.
     - on_text_changed(new_text: str): Posted when the text in this text
       input changes. Be warned that changing it via _ATextInput.text_content
       also posts this event, so if you have to change text in response to this
       event, use _ATextInput.modified to check if it was a user modification;
       otherwise, you risk getting into an infinite loop."""
    _native_widget: _wx.TextCtrl

    # TODO: (fixed) font(s)
    def __init__(self, parent, init_text: str | None = None,
            hint: str | None = None, multiline=True, editable=True,
            auto_tooltip=True, max_length: int | None = None, no_border=False,
            alignment=TextAlignment.LEFT, style=0):
        """Creates a new _ATextInput instance with the specified properties.

        :param parent: The object that this text input belongs to. May be a wx
                       object or a component.
        :param init_text: The initial text in this text input.
        :param hint: The hint for this text input (grey text shown when nothing
                     has been entered into the text input yet).
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
        :param alignment: The alignment of text in this component.
        :param style: Internal parameter used to allow subclasses to wrap style
                      flags on their own."""
        # Construct the native widget
        if multiline: style |= _wx.TE_MULTILINE
        if not editable: style |= _wx.TE_READONLY
        if no_border: style |= _wx.BORDER_NONE
        style |= _ta_to_wx[alignment]
        super(_ATextInput, self).__init__(parent, style=style)
        if init_text: self._native_widget.SetValue(init_text)
        if max_length:
            ##: multiline + max length is not supported on GTK
            if not multiline or _wx.Platform != u'__WXGTK__':
                self._native_widget.SetMaxLength(max_length)
        if hint:
            self._set_hint(hint)
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

    def _set_hint(self, hint: str):
        """Internal method for setting a text input's hint. Needed since
        SearchCtrl.SetHint does not work correctly on Windows."""
        self._native_widget.SetHint(hint)

    def _update_tooltip(self, new_text: str):
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
    def editable(self) -> bool:
        """Returns True if this text input can be edited by the user.

        :return: True if this text input is editable."""
        return self._native_widget.IsEditable()

    @editable.setter
    def editable(self, is_editable: bool):
        """Enables or disables user input to this text input based on the
        specified parameter.

        :param is_editable: Whether to enable or disable user input."""
        self._native_widget.SetEditable(is_editable)

    @property
    def text_content(self) -> str:
        """Returns the text that is currently inside this text input.

        :return: The entered text."""
        return self._native_widget.GetValue()

    @text_content.setter
    def text_content(self, new_text: str):
        """Changes the text inside this text input to the specified string.

        :param new_text: What to change this text input's text to."""
        self._native_widget.SetValue(new_text)

    @property
    def modified(self) -> bool:
        """Returns True if the user has modified the text inside this text
        input.

        :return: True if this text input has been modified."""
        return self._native_widget.IsModified()

    @modified.setter
    def modified(self, is_modified: bool):
        """Changes whether or not this text input is modified based on the
        specified parameter.

        :param is_modified: True if this text input should be marked as
                            modified."""
        self._native_widget.SetModified(is_modified)

    def select_all_text(self):
        """Selects all text currently present in this component."""
        self._native_widget.SelectAll()

class TextArea(_ATextInput):
    """A multi-line text edit widget. See the documentation for _ATextInput
    for a list of the events this component offers."""
    def __init__(self, parent, *args, **kwargs):
        """Creates a new TextArea instance with the specified properties.
        See _ATextInput for documentation on kwargs.

        :param do_wrap: Whether or not to wrap text inside this text area."""
        wrap_style = _wx.TE_DONTWRAP if not kwargs.pop('do_wrap', True) else 0
        super(TextArea, self).__init__(parent, *args, style=wrap_style,
                                       **kwargs)

class TextField(_ATextInput):
    """A single-line text edit widget. Pressing Enter while it is focused will
    send an event to the parent's OK button if it exists. See the documentation
    for _ATextInput for a list of the events this component offers."""
    def __init__(self, parent, *args, **kwargs):
        """Creates a new TextField instance with the specified properties.
        See _ATextInput for documentation on kwargs."""
        self._wx_parent = self._resolve(parent)
        super(TextField, self).__init__(parent, *args, multiline=False,
            style=_wx.TE_PROCESS_ENTER, **kwargs)
        # Handle Enter -> OK button event to parent
        self._on_enter = self._evt_handler(_wx.EVT_TEXT_ENTER)
        self._on_enter.subscribe(self._handle_enter)

    def _handle_enter(self):
        """Internal callback. Sends a click event to the OK button of the
        parent window, if it has one."""
        ok_btn = self._wx_parent.FindWindowById(_wx.ID_OK)
        if ok_btn:
            new_evt = _wx.PyCommandEvent(_wx.EVT_BUTTON.typeId, ok_btn.GetId())
            # Schedule this to run after we've finished handling this event
            _wx.CallAfter(_wx.PostEvent, ok_btn, new_evt)
        return EventResult.FINISH

class SearchBar(TextField):
    """A variant of TextField that looks like a typical search bar."""
    _native_widget: _wx.SearchCtrl

    def __init__(self, parent, *args, hint=_('Search'), **kwargs):
        """Creates a new TextField instance with the specified properties.
        See _ATextInput for documentation on kwargs.

        :param hint: The string to show if nothing has been entered into
            the search bar. Optional, defaults to 'Search'."""
        super().__init__(parent, *args, **kwargs)
        ##: Not sure what the difference between SetHint and SetDescriptiveText
        # is supposed to be, but this one works while SetHint does not...
        self._native_widget.SetDescriptiveText(hint)
        # Implement behavior for the small cancel button: show or hide based on
        # text content (present if text is present and vice versa)
        def _update_clear_btn_visibility(new_text: str):
            self._native_widget.ShowCancelButton(bool(new_text))
        self.on_text_changed.subscribe(_update_clear_btn_visibility)
        # And implement the button's actual behavior when clicked: clear the
        # search bar (which will then hide the button since this posts the
        # on_text_changed event)
        on_cancel = self._evt_handler(_wx.EVT_SEARCHCTRL_CANCEL_BTN)
        on_cancel.subscribe(self.clear_search_bar)

    def clear_search_bar(self, keep_str=''): # use sparingly
        """Clear us if we are not contained in keep_str. Fires wx.EVT_TEXT so
        on_text_changed handler is called - see _ATextInput docs."""
        if not keep_str or self.text_content.strip().lower() not in \
                keep_str.lower():
            self.text_content = ''

    def _set_hint(self, hint: str):
        # SearchCtrl.SetHint is broken (at least on Windows), avoid it
        self._native_widget.SetDescriptiveText(hint)

# Labels ----------------------------------------------------------------------
class _ALabel(_AComponent):
    """Abstract base class for labels."""
    @property
    def label_text(self) -> str:
        """Returns the text of this label as a string.

        :return: The text of this label."""
        return self._unescape(self._native_widget.GetLabel())

    @label_text.setter
    def label_text(self, new_text: str):
        """Changes the text of this label to the specified string.

        :param new_text: The new text to use."""
        # Check first to avoid GUI flicker when setting to identical text
        if self.label_text != new_text:
            self._native_widget.SetLabel(self._escape(new_text))

class Label(_ALabel):
    """A static text element. Doesn't have a border and the text can't be
    interacted with by the user."""
    _native_widget: _wx.StaticText

    def __init__(self, parent, init_text, alignment=TextAlignment.LEFT):
        """Creates a new Label with the specified parent and text.

        :param parent: The object that this label belongs to.
        :param init_text: The initial text of this label.
        :param alignment: The alignment of text in this component."""
        super().__init__(parent, label=self._escape(init_text),
            style=_ta_to_wx[alignment])

    def wrap(self, max_length: int):
        """Wraps this label's text so that each line is at most max_length
        pixels long.

        :param max_length: The maximum number of device-independent pixels
            (DIP) a line may be long."""
        self._native_widget.Wrap(scaled(max_length))

# All code starting from the 'BEGIN WXPYTHON-LICENSED PART' comment and until
# the 'END WXPYTHON-LICENSED PART' comment is based on wx.lib.agw.infobar.AutoWrapStaticText
# https://github.com/wxWidgets/Phoenix/blob/a3b6cfec77fcdcada6b7cb04b9e8f617525d763c/wx/lib/agw/infobar.py
# by Andrea Gavana.
# Modified to refactor and fit WB's code style, get rid of the background color
# change and work around a weird bug.
# BEGIN WXPYTHON-LICENSED PART ================================================
class _WrappingStaticTextWx(_GenStaticTextWx):
    """A StaticText alternative that automatically word-wraps when the parent
    window is resized."""
    # Param names must match the native StaticText ones
    def __init__(self, parent, label, style):
        # Set this first - DoGetBestSize needs it and gets called by parent's
        # __init__
        self._orig_label = label
        super().__init__(parent, label=label,
                         style=_wx.ST_NO_AUTORESIZE | style)
        self.Bind(_wx.EVT_SIZE, self.OnSize)

    def OnSize(self, event):
        self.Wrap(event.GetSize().width)
        event.Skip()

    def Wrap(self, new_width):
        if new_width < 0:
            return
        self.Freeze()
        dc = _wx.ClientDC(self)
        dc.SetFont(self.GetFont())
        self.SetLabel(_wordwrap_wx(self._orig_label, new_width, dc), wrapped=True)
        self.Thaw()

    def SetLabel(self, label, wrapped=False):
        # wrapped is only True if called from Wrap() since it doesn't exist in
        # the parent method's signature
        if not wrapped:
            self._orig_label = label
        super().SetLabel(label)

    def DoGetBestSize(self):
        wst_font = self.GetFont()
        if not wst_font:
            wst_font = _wx.SystemSettings.GetFont(_wx.SYS_DEFAULT_GUI_FONT)
        dc = _wx.ClientDC(self)
        dc.SetFont(wst_font)
        wst_label = self.GetLabel()
        # Workaround for a really weird bug where we sometimes get a label
        # that's got a \n before every single word character (e.g.
        # '\nf\no\no \nb\na\nr')
        if wst_label.startswith('\n'):
            wst_label = ''.join(wst_label.split('\n'))
        # Draw the label's text in memory (i.e. not on a real window) and keep
        # track of how much we drew
        longest_line_width = total_drawn_height = 0
        for label_line in wst_label.split('\n'):
            if label_line == '':
                w, h = dc.GetTextExtent('W') # Empty lines have height too
            else:
                w, h = dc.GetTextExtent(label_line)
            total_drawn_height += h
            longest_line_width = max(longest_line_width, w)
        wst_best = _wx.Size(longest_line_width, total_drawn_height)
        self.CacheBestSize(wst_best)
        return wst_best
# END WXPYTHON-LICENSED PART ==================================================

class WrappingLabel(Label):
    """Similar to Label, but automatically word-wraps when the parent window is
    resized. After creating and using it in a layout, call auto_wrap if your
    label's parents/sizers have proper sizes. If they don't, you will have to
    pass in the right initial sizes manually (see settings_dialog.py for an
    example)."""
    _native_widget: _WrappingStaticTextWx

    @_ALabel.label_text.setter
    def label_text(self, new_text: str):
        # Override to word-wrap when changing text programmatically as well.
        # Note: you *do* still have to call update_layout after doing this!
        if self.label_text != new_text:
            self._native_widget.SetLabel(new_text)
            self.wrap(self.component_size[0])

    def auto_wrap(self):
        """Automatically wrap this label to fit in the client size it was
        given."""
        self.wrap(self._native_widget.GetClientSize().width)

class HyperlinkLabel(_ALabel):
    """A label that opens a URL when clicked, imitating a hyperlink in a
    browser. Typically styled blue.

    Events:
        - on_link_clicked(target_url: str): Posted when the link is
        clicked on by the user."""
    _native_widget: _adv.HyperlinkCtrl

    def __init__(self, parent, init_text: str, url: str,
            always_unvisited=False):
        """Creates a new HyperlinkLabel with the specified parent, text and
        URL.

        :param parent: The object that this hyperlink label belongs to. May be
                       a wx object or a component.
        :param init_text: The initial text of this hyperlink label.
        :param url: The URL to open when this hyperlink label is clicked on.
        :param always_unvisited: If set to True, this link will always appear
                                 as if it hasn't been clicked on (i.e. blue -
                                 it will never turn purple)."""
        super(HyperlinkLabel, self).__init__(parent, label=init_text, url=url)
        if always_unvisited:
            self._native_widget.SetVisitedColour(
                self._native_widget.GetNormalColour())
        self.on_link_clicked = self._evt_handler(_adv.EVT_HYPERLINK,
            lambda event: [event.GetURL()])

    # No escaping needed for wx.adv.HyperlinkCtrl, doing this would just double
    # all ampersands
    @staticmethod
    def _escape(s):
        return s

    @staticmethod
    def _unescape(s):
        return s

# Spinner - technically text, just limited to digits --------------------------
class Spinner(_AComponent):
    """A field for entering integers. Features small arrow buttons on the right
    to increment and decrement the value.

    Events:
      - on_spun(new_num: int): Posted when a new value is entered into the
        spinner (whether manually or through the buttons)."""
    _native_widget: _wx.SpinCtrl

    def __init__(self, parent, initial_num: int = 0, min_num: int = 0,
            max_num: int = 100, spin_tip: str = ''):
        """Initializes a new Spinner with the specified parameters.

        :param parent: The object that this spinner belongs to. May be a wx
            object or a component.
        :param initial_num: The initial number displayed in this spinner.
        :param min_num: The minimum number that may be entered via this
            spinner.
        :param max_num: The maximum number that may be entered via this
            spinner.
        :param spin_tip: If set to a nonempty string, the tooltip displayed
            when hovering over this spinner."""
        super().__init__(parent, style=_wx.SP_ARROW_KEYS, min=min_num,
            max=max_num, initial=initial_num)
        self.on_spun = self._evt_handler(_wx.EVT_SPINCTRL,
            lambda event: [event.GetPosition()])
        if spin_tip: self.tooltip = spin_tip

    @property
    def spinner_value(self):
        return int(self._native_widget.GetValue())

    @spinner_value.setter
    def spinner_value(self, sp_value):
        self._native_widget.SetValue(int(sp_value))
