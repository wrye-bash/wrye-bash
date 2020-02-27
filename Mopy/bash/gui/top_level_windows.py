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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Top level windows in wx is Frame and Dialog."""
__author__ = u'Utumno, Infernio'

import wx as _wx

defPos = _wx.DefaultPosition
defSize = _wx.DefaultSize

from .base_components import _AComponent
from .events import EventHandler

class _TopLevelWin(_AComponent):
    """Methods mixin for top level windows

    Events:
     - _on_close_evt(): request to close the window."""
    _defPos = defPos
    _def_size = defSize
    sizesKey = posKey = None

    def __init__(self, wx_window_type, parent, sizes_dict, icon_bundle, *args,
                 **kwargs):
        self._sizes_dict = sizes_dict
        kwargs[u'pos'] = kwargs.get(u'pos', None) or sizes_dict.get(
            self.posKey, self._defPos)
        kwargs[u'size'] = kwargs.get(u'size', None) or sizes_dict.get(
            self.sizesKey, self._def_size)
        super(_TopLevelWin, self).__init__(wx_window_type, parent, *args,
                                           **kwargs)
        self._on_close_evt = EventHandler(self._native_widget, _wx.EVT_CLOSE)
        self._on_close_evt.subscribe(self.on_closing)
        if icon_bundle: self.set_icons(icon_bundle)

    @property
    def is_maximized(self):
        """IsMaximized(self) -> bool"""
        return self._native_widget.IsMaximized()

    @property
    def is_iconized(self):
        """IsIconized(self) -> bool"""
        return self._native_widget.IsIconized()

    # TODO(inf) de-wx! Image API - these use wx.Icon and wx.IconBundle
    def set_icon(self, wx_icon):
        """SetIcon(self, Icon icon)"""
        return self._native_widget.SetIcon(wx_icon)

    def set_icons(self, wx_icon_bundle):
        """SetIcons(self, wxIconBundle icons)"""
        return self._native_widget.SetIcons(wx_icon_bundle)

    def close_win(self, force_close=False):
        """This function simply generates a EVT_CLOSE event whose handler usually
        tries to close the window. It doesn't close the window itself,
        however.  If force is False (the default) then the window's close
        handler will be allowed to veto the destruction of the window."""
        self._native_widget.Close(force_close)

    def on_closing(self, destroy=True):
        """Invoked right before this window is destroyed."""
        if self._sizes_dict and not self.is_iconized and not self.is_maximized:
            if self.posKey: self._sizes_dict[self.posKey] = self.component_position
            if self.sizesKey: self._sizes_dict[self.sizesKey] = self.component_size
        if destroy: self.destroy_component()

class WindowFrame(_TopLevelWin):
    """Wraps a wx.Frame - saves size/position on closing.

    Events:
     - on_activate(): Posted when the frame is activated.
     """
    _frame_settings_key = None
    _min_size = _def_size = (250, 250)

    def __init__(self, parent, title, icon_bundle=None, _base_key=None,
                 sizes_dict={}, style=_wx.DEFAULT_FRAME_STYLE, **kwargs):
        _key = _base_key or self.__class__._frame_settings_key
        if _key:
            self.posKey = _key + u'.pos'
            self.sizesKey = _key + u'.size'
        super(WindowFrame, self).__init__(_wx.Frame, parent, sizes_dict,
                                          icon_bundle, title=title,
                                          style=style, **kwargs)
        self.on_activate = EventHandler(self._native_widget, _wx.EVT_ACTIVATE,
            arg_processor=lambda event: [event.GetActive()])
        self.background_color = _wx.NullColour
        self.set_min_size(*self._min_size)

    def show_frame(self): self._native_widget.Show()

    # TODO(inf) de-wx! Menu should become a wrapped component as well
    def popup_menu(self, menu):
        self._native_widget.PopupMenu(menu)

class DialogWindow(_TopLevelWin):
    """Wrap a dialog control."""
    title = u'OVERRIDE'

    def __init__(self, parent=None, title=None, icon_bundle=None,
                 sizes_dict={}, caption=False, sizesKey=None, posKey=None,
                 style=0, **kwargs):
        self.sizesKey = sizesKey or self.__class__.__name__
        self.posKey = posKey
        self.title = title or self.__class__.title
        style |= _wx.DEFAULT_DIALOG_STYLE
        if sizes_dict: style |= _wx.RESIZE_BORDER
        if caption: style |= _wx.CAPTION
        super(DialogWindow, self).__init__(_wx.Dialog, parent, sizes_dict,
                                           icon_bundle, title=self.title,
                                           style=style, **kwargs)
        self.on_size_changed = EventHandler(self._native_widget, _wx.EVT_SIZE)

    def save_size(self):
        if self._sizes_dict and self.sizesKey:
            self._sizes_dict[self.sizesKey] = self.component_size

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.destroy_component()

    @classmethod
    def display_dialog(cls, *args, **kwargs):
        """Instantiate a dialog, display it and return the ShowModal result."""
        with cls(*args, **kwargs) as dialog:
            return dialog.show_modal()

    def show_modal(self):
        """Begins a new modal dialog and returns a boolean indicating if the
        exit code was fine.

        :return: True if the dialog was closed with a good exit code (e.g. by
            clicking an 'OK' or 'Yes' button), False otherwise."""
        return self.show_modal_raw() in (_wx.ID_OK, _wx.ID_YES)

    # TODO(inf) Investigate uses, they all seem to have weird, fragile logic
    def show_modal_raw(self):
        """Begins a new modal dialog and returns the raw exit code."""
        return self._native_widget.ShowModal()

    def accept_modal(self):
        """Closes the modal dialog with a 'normal' exit code. Equivalent to
        clicking the OK button."""
        self.exit_modal(_wx.ID_OK)

    def cancel_modal(self):
        """Closes the modal dialog with an 'abnormal' exit code. Equivalent to
        clicking the Cancel button."""
        self.exit_modal(_wx.ID_CANCEL)

    # TODO(inf) Investigate uses, see show_modal_raw above
    def exit_modal(self, custom_code):
        """Closes the modal dialog with a custom exit code."""
        self._native_widget.EndModal(custom_code)
