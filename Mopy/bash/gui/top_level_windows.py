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
"""Top level windows in wx is Frame and Dialog. I added some more like Panels
and the wx.adv (wizards) stuff."""
from __future__ import annotations

__author__ = u'Utumno, Infernio'

import wx as _wx
import wx.adv as _adv

from .base_components import Color, _AComponent, scaled
from ..bolt import deprint

# Special constant defining a window as having whatever position the underlying
# GUI implementation picks for it by default.
DEFAULT_POSITION = (-1, -1)

class _TopLevelWin(_AComponent):
    """Methods mixin for top level windows

    Events:
     - _on_close_evt(): request to close the window."""
    _def_pos = _wx.DefaultPosition
    _def_size = _wx.DefaultSize
    _min_size = _size_key = _pos_key = None
    _native_widget: _wx.TopLevelWindow

    def __init__(self, parent, sizes_dict, icon_bundle, *args, **kwargs):
        # dict holding size/pos info stored in bass.settings
        self._sizes_dict = sizes_dict.get('bash.window.sizes', {})
        super().__init__(parent, *args, **kwargs)
        self._set_pos_size(kwargs)
        self._on_close_evt = self._evt_handler(_wx.EVT_CLOSE)
        self._on_close_evt.subscribe(self.on_closing)
        if icon_bundle: self.set_icons(icon_bundle)
        if self._min_size: self.set_min_size(*self._min_size) ##: shouldn't we set this in _set_pos_size??

    def _set_pos_size(self, kwargs):
        wanted_pos = kwargs.get('pos', None) or \
            self._sizes_dict.get(self._pos_key, self._def_pos)
        # Resolve the special DEFAULT_POSITION constant to a real value
        self.component_position = (
            self._def_pos if wanted_pos == DEFAULT_POSITION else wanted_pos)
        wanted_width, wanted_height = kwargs.get('size', None) or \
            self._sizes_dict.get(self._size_key, self._def_size)
        # Check if our wanted width or height is too small and bump it up
        if self._min_size:
            if wanted_width < self._min_size[0]:
                wanted_width = self._min_size[0]
            if wanted_height < self._min_size[1]:
                wanted_height = self._min_size[1]
        self.component_size = (wanted_width, wanted_height)

    @property
    def is_maximized(self):
        """Returns True if this window has been maximized."""
        return self._native_widget.IsMaximized()

    @is_maximized.setter
    def is_maximized(self, new_maximized):
        """Maximizes or restores this window."""
        self._native_widget.Maximize(new_maximized)

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
            if self._pos_key: self._sizes_dict[self._pos_key] = self.component_position
            if self._size_key: self._sizes_dict[self._size_key] = self.component_size
        if destroy: self.destroy_component()

    def ensureDisplayed(self, x=100, y=100): ##: revisit uses
        """Ensure that frame is displayed."""
        if _wx.Display.GetFromWindow(self._native_widget) == -1:
            topLeft = _wx.Display(0).GetGeometry().GetTopLeft()
            self._native_widget.Move(topLeft.x + x, topLeft.y + y)

class WindowFrame(_TopLevelWin):
    """Wraps a wx.Frame - saves size/position on closing.

    Events:
     - on_activate(): Posted when the frame is activated.
     """
    _key_prefix = None
    _min_size = _def_size = (250, 250)
    _native_widget: _wx.Frame

    def __init__(self, parent, title, icon_bundle=None, sizes_dict={},
                 caption=False, style=_wx.DEFAULT_FRAME_STYLE, **kwargs):
        if self.__class__._key_prefix:
            self._pos_key = f'{self.__class__._key_prefix}.pos'
            self._size_key = f'{self.__class__._key_prefix}.size'
        if caption: style |= _wx.CAPTION
        if sizes_dict: style |= _wx.RESIZE_BORDER
        if kwargs.pop(u'clip_children', False): style |= _wx.CLIP_CHILDREN
        if kwargs.pop(u'tab_traversal', False): style |= _wx.TAB_TRAVERSAL
        super(WindowFrame, self).__init__(parent, sizes_dict, icon_bundle,
                                          title=title, style=style, **kwargs)
        self.on_activate = self._evt_handler(_wx.EVT_ACTIVATE,
                                             lambda event: [event.GetActive()])
        self.set_background_color(self._bkg_color())

    def show_frame(self, center=False):
        self._native_widget.Show()
        if center: self._native_widget.Center()

    def raise_frame(self): self._native_widget.Raise()

    def _bkg_color(self):
        """Returns the background color to use for this window."""
        return Color.from_wx(_wx.SystemSettings.GetColour(_wx.SYS_COLOUR_MENU))

class DialogWindow(_TopLevelWin):
    """Wrap a dialog control."""
    title: str
    _native_widget: _wx.Dialog

    def __init__(self, parent=None, title=None, icon_bundle=None,
            sizes_dict=None, caption=False, size_key=None, pos_key=None,
            stay_over_parent=False, style=0, **kwargs):
        self._size_key = size_key or self.__class__.__name__
        self._pos_key = pos_key
        self.title = title or self.__class__.title
        style |= _wx.DEFAULT_DIALOG_STYLE
        if stay_over_parent: style |= _wx.FRAME_FLOAT_ON_PARENT
        if sizes_dict is not None: style |= _wx.RESIZE_BORDER
        else: sizes_dict = {}
        if caption: style |= _wx.CAPTION
        super().__init__(parent, sizes_dict, icon_bundle, title=self.title,
                         style=style, **kwargs)
        self._on_size_changed = self._evt_handler(_wx.EVT_SIZE)
        self._on_size_changed.subscribe(self.save_size) # save dialog size

    def save_size(self):
        if self._sizes_dict is not None and self._size_key:
            self._sizes_dict[self._size_key] = self.component_size

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.destroy_component()

    def on_closing(self, destroy=False): # flip destroy to False
        # dialogs are shown via the context manager above, if we destroy
        # them here they won't be destroyed on __exit__ on mac at least
        super(DialogWindow, self).on_closing(destroy)

    @classmethod
    def display_dialog(cls, *args, **kwargs):
        """Instantiate a dialog, display it and return the ShowModal result."""
        with cls(*args, **kwargs) as dialog:
            return dialog.show_modal()

    def show_modal(self) -> bool:
        """Begins a new modal dialog and returns a boolean indicating if the
        exit code was fine. Note that some subclasses override this to return
        more than just that boolean.

        :return: True if the dialog was closed with a good exit code (e.g. by
            clicking an 'OK' or 'Yes' button), False otherwise."""
        return self._native_widget.ShowModal() in (_wx.ID_OK, _wx.ID_YES)

    def accept_modal(self):
        """Closes the modal dialog with a 'normal' exit code. Equivalent to
        clicking the OK button."""
        self._native_widget.EndModal(_wx.ID_OK)

    def cancel_modal(self):
        """Closes the modal dialog with an 'abnormal' exit code. Equivalent to
        clicking the Cancel button."""
        self._native_widget.EndModal(_wx.ID_CANCEL)

class StartupDialogWindow(DialogWindow):
    """Dialog shown during early boot, generally due to errors."""
    def __init__(self, *args, **kwargs):
        sd_style = _wx.STAY_ON_TOP | _wx.DIALOG_NO_PARENT
        super().__init__(*args, style=sd_style, **kwargs)

class MaybeModalDialogWindow(DialogWindow):
    """Dialog that may be modal or modeless."""
    def show_modeless(self):
        """Open this dialog in a modeless fashion. It will behave similarly to
        a WindowFrame."""
        self._native_widget.Show()
        self._native_widget.Raise()

# Panels ----------------------------------------------------------------------
class PanelWin(_AComponent):
    _native_widget: _wx.Panel

    def __init__(self, parent, no_border=True, wants_chars=False):
        super().__init__(parent,
            style=_wx.TAB_TRAVERSAL | (no_border and _wx.NO_BORDER) | (
                        wants_chars and _wx.WANTS_CHARS))

class Splitter(_AComponent):
    _native_widget: _wx.SplitterWindow

    def __init__(self, parent, allow_split=True, min_pane_size=0,
                 sash_gravity=0):
        super(Splitter, self).__init__(parent, style=_wx.SP_LIVE_UPDATE)
        if not allow_split: # Don't allow unsplitting
            self._native_widget.Bind(_wx.EVT_SPLITTER_DCLICK,
                                     lambda event: event.Veto())
        if min_pane_size:
            self.set_min_pane_size(min_pane_size)
        if sash_gravity:
            self.set_sash_gravity(sash_gravity)
        self._panes = None

    def make_panes(self, sash_position=0, first_pane=None, second_pane=None,
                   vertically=False):
        self._panes = [first_pane or PanelWin(self),
                       second_pane or PanelWin(self)]
        split = self._native_widget.SplitVertically if vertically else \
            self._native_widget.SplitHorizontally
        split(self._panes[0]._native_widget, self._panes[1]._native_widget,
              sash_position)
        return self._panes[0], self._panes[1]

    def get_sash_pos(self): return self._native_widget.GetSashPosition()

    def set_sash_pos(self, sash_position):
        self._native_widget.SetSashPosition(sash_position)

    def set_min_pane_size(self, min_pane_size):
        self._native_widget.SetMinimumPaneSize(scaled(min_pane_size))

    def set_sash_gravity(self, sash_gravity):
        self._native_widget.SetSashGravity(sash_gravity)

class _APageComponent(_AComponent):
    """Abstract base class for 'page' compoenents, i.e. notebooks and
    listbooks."""
    _native_widget: _wx.BookCtrlBase

    def add_page(self, page_component, page_title):
        self._native_widget.AddPage(self._resolve(page_component), page_title)

    def get_selected_page_index(self):
        return self._native_widget.GetSelection()

    def set_selected_page_index(self, page_index: int) -> None:
        corrected_index = max(0, min(self.page_count - 1, page_index))
        if corrected_index != page_index:
            deprint(
                f'warning: attempted to set selected page to {page_index}, '
                f'out of range of available pages (0-{self.page_count - 1}). '
                f'Using {corrected_index} instead.'
            )
        self._native_widget.SetSelection(corrected_index)

    @property
    def page_count(self) -> int:
        return self._native_widget.PageCount

class TabbedPanel(_APageComponent):
    """A panel with tabs, each of which contains a different panel."""
    _native_widget: _wx.Notebook

    def __init__(self, parent, multiline=False):
        super(TabbedPanel, self).__init__(
            parent, style=_wx.NB_MULTILINE if multiline else 0)
        self.on_nb_page_change = self._evt_handler(
            _wx.EVT_NOTEBOOK_PAGE_CHANGED,
            lambda event: [event.GetId(), event.GetSelection()])

class ListPanel(_APageComponent):
    """A panel with a list of options that each correspond to a different
    panel."""
    _native_widget: _wx.Listbook

    def __init__(self, parent):
        super(ListPanel, self).__init__(parent)
        left_list = self._native_widget.GetChildren()[0]
        left_list.SetSingleStyle(_wx.LC_LIST | _wx.LC_ALIGN_LEFT)

class ScrollableWindow(_AComponent):
    """A window with a scrollbar."""
    _native_widget: _wx.ScrolledWindow

    def __init__(self, parent, scroll_horizontal=True, scroll_vertical=True):
        super(ScrollableWindow, self).__init__(parent)
        scroll_h = scaled(20 if scroll_horizontal else 0)
        scroll_v = scaled(20 if scroll_vertical else 0)
        units_h = scaled(50 if scroll_horizontal else 0)
        units_v = scaled(50 if scroll_vertical else 0)
        self._native_widget.SetScrollbars(scroll_h, scroll_v, units_h, units_v)

class CenteredSplash(_AComponent):
    """A centered splash screen without a timeout. Only disappears when either
    the entire application terminates or stop_splash is called."""
    _native_widget: _adv.SplashScreen

    def __init__(self, splash_path):
        """Creates a new CenteredSplash with an image read from the specified
        path."""
        splash_bitmap = _wx.Image(splash_path).ConvertToBitmap()
        # Center image on the screen and image will stay until clicked by
        # user or is explicitly destroyed when the main window is ready
        splash_style = _adv.SPLASH_CENTER_ON_SCREEN | _adv.SPLASH_NO_TIMEOUT
        # Can't use _AComponent.__init__ here, because for some ungodly reason
        # parent is the *fourth* parameter in SplashScreen
        self._native_widget = _adv.SplashScreen(
            splash_bitmap, splash_style, 1, None) # Timeout - ignored
        self._on_close_evt = self._evt_handler(_wx.EVT_CLOSE)
        self._on_close_evt.subscribe(self.stop_splash)
        _wx.Yield() ##: huh?

    def stop_splash(self):
        """Hides and terminates the splash screen."""
        self.destroy_component()
        ##: Apparently won't be hidden if warnTooManyModsBsas warns(?)
        self.visible = False
