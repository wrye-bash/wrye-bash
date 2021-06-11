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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Houses functions and function-like objects (e.g. BusyCursor). Everything
that isn't a component, basically."""

import wx as _wx

from .base_components import _AComponent
from ..exception import ArgumentError

class _OpenClipboard(object):
    """Internal wrapper around wx.TheClipboard for use with Python's 'with'
    statement. Ensures that the clipboard is always opened and closed
    correctly."""
    def __enter__(self):
        self._successfully_opened = _wx.TheClipboard.Open()
        return self._successfully_opened

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._successfully_opened:
            _wx.TheClipboard.Close()

def bell(bell_arg=None):
    """"Rings the system bell and returns the input argument (useful for return
    bell(value) or returning None and ringing)."""
    _wx.Bell()
    return bell_arg

class BusyCursor(object):
    """To be used with 'with' statements - changes the user's cursor to the
    system's 'busy' cursor style. Useful to signal that a running operation is
    making progress, but won't take long enough to be worth a progress
    dialog."""
    def __enter__(self):
        _wx.BeginBusyCursor()

    def __exit__(self, exc_type, exc_val, exc_tb):
        _wx.EndBusyCursor()

def copy_text_to_clipboard(text_to_copy):
    """Copies the specified text to the system clipboard."""
    with _OpenClipboard() as clip_opened:
        if not clip_opened: return
        _wx.TheClipboard.SetData(_wx.TextDataObject(text_to_copy))

def copy_files_to_clipboard(file_paths_to_copy):
    """Copies the specified iterable of file paths to the system clipboard."""
    if not file_paths_to_copy: return
    with _OpenClipboard() as clip_opened:
        if not clip_opened: return
        clip_data = _wx.FileDataObject()
        for abs_path_to_copy in file_paths_to_copy:
            ##: wx docs say this is Windows-only - test and guard with
            # __WXMSW__ if that is the case (or find a cross-platform
            # alternative)
            clip_data.AddFile(abs_path_to_copy)
        _wx.TheClipboard.SetData(clip_data)

def read_from_clipboard():
    """Returns any text data that is currently in the system clipboard, or an
    empty string if none is stored."""
    with _OpenClipboard() as clip_opened:
        if not clip_opened: return u''
        text_data = _wx.TextDataObject()
        was_sucessful = _wx.TheClipboard.GetData(text_data)
    return text_data.GetText() if was_sucessful else u''

def read_files_from_clipboard_cb(files_callback):
    """Reads file paths from the clipboard and passes them to the specified
    callback once the current even chain is done executing."""
    if not files_callback: return
    with _OpenClipboard() as clip_opened:
        if not clip_opened: return
        if _wx.TheClipboard.IsSupported(_wx.DataFormat(_wx.DF_FILENAME)):
            clip_data = _wx.FileDataObject()
            _wx.TheClipboard.GetData(clip_data)
            _wx.CallAfter(files_callback, clip_data.GetFilenames())

def get_ctrl_down(): # type: () -> bool
    """Returns True if the Ctrl key is currently down."""
    return _wx.GetKeyState(_wx.WXK_CONTROL)

def get_key_down(key_char): # type: (str) -> bool
    """Returns True if the key corresponding to the specified character is
    currently down."""
    return _wx.GetKeyState(ord(key_char))

def get_shift_down(): # type: () -> bool
    """Returns True if the Shift key is currently down."""
    return _wx.GetKeyState(_wx.WXK_SHIFT)

# TODO(inf) de-wx! Actually, don't - absorb via better API
def staticBitmap(parent, bitmap=None, size=(32, 32), special=u'warn'):
    """Tailored to current usages - IAW: do not use."""
    if bitmap is None:
        bmp = _wx.ArtProvider.GetBitmap
        if special == u'warn':
            bitmap = bmp(_wx.ART_WARNING, _wx.ART_MESSAGE_BOX, size)
        elif special == u'undo':
            return bmp(_wx.ART_UNDO, _wx.ART_TOOLBAR, size)
        else: raise ArgumentError(
            u'special must be either warn or undo: %r given' % special)
    return _wx.StaticBitmap(_AComponent._resolve(parent), bitmap=bitmap)
