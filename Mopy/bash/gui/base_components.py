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
"""This module houses parts of the GUI code that form the basis for the
more specialized parts (e.g. _AComponent)."""
from __future__ import annotations

__author__ = 'nycz, Infernio, Utumno'

import functools
import platform
import textwrap
from typing import get_type_hints

import wx as _wx
import wx.lib.newevent as _newevent

from .events import EventHandler, null_processor
from ..exception import GuiError

# Utilities -------------------------------------------------------------------
@functools.cache
def _csf() -> float:
    """Returns the content scale factor (CSF) needed for high DPI displays."""
    if platform.system() != 'Darwin': ##: Linux? os_name == 'nt' if so
        ##: This should really be GetContentScaleFactor(), but that always
        # returns 1.0 for me (on wxPython 4.2.0), so use a workaround
        scaled_size = _wx.Window().FromDIP((16, 16))
        return scaled_size[0] / 16
    else:
        return 1.0 # Everything scales automatically on macOS

def scaled(unscaled_size: int | float):
    scaled = unscaled_size * _csf()
    if isinstance(unscaled_size, int):
        scaled = int(scaled)
    return scaled

def wrapped_tooltip(tooltip_text: str, wrap_width: int = 50):
    """Returns tooltip with wrapped copy of text."""
    tooltip_text = textwrap.fill(tooltip_text, wrap_width)
    return _wx.ToolTip(tooltip_text)

class Color:
    """A simple RGB(A) color class used to avoid having to return wx.Colour
    objects."""
    def __init__(self, red: int, green: int, blue: int, alpha: int = 255):
        """Creates a new color object with the specified color properties.
        Note that all color components must be in the range [0-255] (inclusive
        on both ends), otherwise a RuntimeException is raised.

        :param red: The amount of red in this color: [0-255].
        :param green: The amount of green in this color: [0-255].
        :param blue: The amount of blue in this color: [0-255].
        :param alpha: The amount of alpha in this color: [0-255]. Defaults to
                      255."""
        for color in (red, green, blue, alpha):
            if color < 0 or color > 255:
                raise RuntimeError('All color components must be in range '
                                   '0-255.')
        self.red, self.green, self.blue, self.alpha = red, green, blue, alpha

    def to_rgba_tuple(self) -> tuple[int, int, int, int]:
        """Converts this Color object into a four-int RGBA tuple."""
        return self.red, self.green, self.blue, self.alpha

    def to_rgb_tuple(self) -> tuple[int, int, int]:
        """Converts this Color object into a three-int RGB tuple."""
        return self.red, self.green, self.blue

    def __eq__(self, other):
        if not isinstance(other, Color):
            return NotImplemented
        return (self.red == other.red and self.green == other.green and
                self.blue == other.blue and self.alpha == other.alpha)

    def __repr__(self):
        return f'Color(red={self.red}, green={self.green}, ' \
               f'blue={self.blue}, alpha={self.alpha})'

    @classmethod
    def from_wx(cls, color: _wx.Colour) -> Color:
        """Creates a new Color object by copying the color properties from the
        specified wx.Colour object.

        :param color: The wx.Colour object to copy.
        :return: A Color object representing the same color."""
        return cls(color.Red(), color.Green(), color.Blue(), color.Alpha())

class _ACFrozen:
    """Helper for _AComponent.pause_drawing."""
    def __init__(self, wx_parent):
        self._wx_parent = wx_parent

    def __enter__(self):
        self._wx_parent.Freeze()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._wx_parent.Thaw()

# Base Elements ---------------------------------------------------------------
_no_parent = _wx.Object() # signals that this native component has no parent
class _AObject:
    """Abstract base class for all GUI items. Holds a reference to the native
    wx widget that we abstract over. We mimic wx hierarchy as we need to wrap
    components on all levels."""
    _native_widget: _wx.Object

    def __init__(self, parent=_no_parent, *args, **kwargs):
        """Creates a new _AComponent instance by initializing the wx widget
        with the specified parent, args and kwargs."""
        wx_widget_type = get_type_hints(self.__class__)['_native_widget']
        if parent is not _no_parent:
            args = self._resolve(parent), *args
        widget = wx_widget_type(*args, **kwargs)
        if isinstance(self, Lazy):
            self._cached_widget = widget
        else:
            self._native_widget = widget

    @staticmethod
    def _escape(s):
        """Because someone somewhere thought that making us escape every single
        ampersand ever passed to a widget's label was a good idea. We don't use
        them for accelerators, why can't we just disable this behavior
        altogether?

        Call this whenever accepting a string from the rest of WB into gui that
        will be used for a widget's label."""
        return s.replace('&', '&&')

    @staticmethod
    def _unescape(s):
        """Inverse of _escape. Call this whenever passing a string that went
        through _escape from gui to the rest of WB."""
        return s.replace('&&', '&')

    @staticmethod
    def _resolve(obj):
        """Resolves the specified object down to a wx object. If obj is a wx
        object already, then this just returns it. If obj is a component,
        this returns its _native_widget object. If obj is anything else, this
        raises a RuntimeError. The primary usage of this method is to allow
        both wx objects and components as parents.

        :param obj: The object to resolve.
        :return: The resolved wx object.
        """
        if isinstance(obj, _AObject):
            return obj._native_widget
        elif isinstance(obj, _wx.Object) or obj is None:
            return obj
        else:
            raise RuntimeError(f"Failed to resolve object '{obj!r}' to wx "
                               f"object.")

    def native_destroy(self):
        """Destroys this component - non-internal usage is a smell, avoid if at
        all possible."""
        self._native_widget.Destroy()

class _AEvtHandler(_AObject):
    """Wrap an EvtHandler instance."""
    _native_widget: _wx.EvtHandler

    def _evt_handler(self, evt, arg_proc=null_processor):
        """Register an EventHandler on _native_widget"""
        return EventHandler(self._native_widget, evt, arg_proc)

    def _make_custom_event(self, callback):
        """Creates a wrapper around a custom event.

        :param callback: The method to call when the event is posted.
        :return: A method that will pass whatever kwargs are given to it along
            to the callback."""
        event_cls, binder = _newevent.NewEvent()
        def _receiver(event):
            received_kwargs = {a: getattr(event, a)
                               for a in getattr(event, '_kwargs', [])}
            callback(**received_kwargs)
        self._native_widget.Bind(binder, _receiver)
        def _sender(**kwargs):
            _wx.PostEvent(self._native_widget, event_cls(**kwargs,
                _kwargs=list(kwargs))) # So that we can access them again
        return _sender

    def pause_drawing(self) -> _ACFrozen:
        """To be used via Python's 'with' statement. Pauses all visual updates
        to this component while in the with statement."""
        return _ACFrozen(self._native_widget)

class Lazy(_AObject):
    """Lazily create the native widget on first accessing self._native_widget.
    _AObject needs to know about us - think of Lazy on the same level as it."""
    # allow creating the native widget by directly accessing the _native_widget
    # if False you can *only* access _native_widget after successfully calling
    # native_init
    _bypass_native_init = False

    # noinspection PyMissingConstructor
    def __init__(self, *args, **kwargs):
        """Postpone calling super.__init__ till the widget is accessed."""
        # passed from native_init for classes that have a parent
        self._parent = _no_parent
        self._cached_args = args
        self._cached_kwargs = kwargs
        self._cached_widget = None
        self.__native_init_called = self._bypass_native_init

    @property
    def _native_widget(self):
        if not self._is_created():
            if not self.__native_init_called:
                raise GuiError(f'{self!r} accessing the native widget without '
                               f'calling native_init first')
            super(Lazy, self).__init__(self._parent, *self._cached_args,
                                       **self._cached_kwargs)
        return self._cached_widget

    def native_destroy(self):
        if self._is_created():
            self._cached_widget.Destroy()
            self._cached_widget = None
            self._parent = _no_parent
            self.__native_init_called = self._bypass_native_init

    # Lazy API - probe into the internals of the class - special occasions only
    def _is_created(self):
        """Return True if self._cached_widget is available."""
        return self._cached_widget is not None

    def allow_create(self):
        """Check if the required resources to create the widget exist."""
        return True

    def native_init(self, parent=_no_parent, *, recreate=True, **kwargs):
        """Create the native Object - if freshly created return True."""
        if not self.allow_create(): return False
        if recreate:
            self.native_destroy()
        elif self._is_created():
            return False
        self._parent = parent
        self._cached_kwargs.update(kwargs)
        self.__native_init_called = True
        # will call super init and create the widget
        return bool(self._native_widget) # True

class _AComponent(_AEvtHandler):
    """Wrap an inheritor of wx.Window. Wraps methods present in wx.Window."""
    _native_widget: _wx.Window

    def get_component_name(self) -> str:
        """Returns the name of this component.

        :return: This component's name."""
        return self._native_widget.GetName()

    def set_component_name(self, new_ctrl_name: str):
        """Sets the name of this component to the specified name.

        :param new_ctrl_name: The string to change this component's name to."""
        self._native_widget.SetName(new_ctrl_name)

    @property
    def visible(self) -> bool:
        """Returns True if this component is currently visible, i.e. if the
        user can see it in the GUI.

        :return: True if this component is currently visible."""
        return self._native_widget.IsShown()

    @visible.setter
    def visible(self, is_visible: bool):
        """Shows or hides this component based on the specified parameter.

        :param is_visible: Whether or not to show this component."""
        self._native_widget.Show(is_visible)

    @property
    def enabled(self) -> bool:
        """Returns True if this component is currently enabled, i.e. if the
        user can interact with it. Disabled widgets are typically styled in
        some way to indicate this fact to the user (e.g. greyed out).

        :return: True if this component is currently enabled."""
        return self._native_widget.IsEnabled()

    @enabled.setter
    def enabled(self, is_enabled: bool):
        """Enables or disables this component based on the specified parameter.

        :param is_enabled: Whether or not to enable this component."""
        self._native_widget.Enable(is_enabled)

    @property
    def tooltip(self) -> str:
        """Returns the current contents of this component's tooltip. If no
        tooltip is set, returns an empty string.

        :return: This component's tooltip."""
        return self._native_widget.GetToolTipText() or ''

    @tooltip.setter
    def tooltip(self, new_tooltip: str):
        """Sets the tooltip of this component to the specified string. If the
        string is empty or None, the tooltip is simply removed.

        :param new_tooltip: The string to change the tooltip to."""
        if not new_tooltip:
            self._native_widget.UnsetToolTip()
        else:
            self._native_widget.SetToolTip(wrapped_tooltip(new_tooltip))

    def get_background_color(self) -> Color:
        """Returns the background color of this component as a tuple.

        :return: The background color of this component."""
        return Color.from_wx(self._native_widget.GetBackgroundColour())

    def set_background_color(self, new_color: Color):
        """Changes the background color of this component to the specified
        color. See gui.Color.

        :param new_color: The color to change the background color to."""
        self._native_widget.SetBackgroundColour(new_color.to_rgba_tuple())
        self._native_widget.Refresh()

    def reset_background_color(self):
        """Resets the background color of this component to the default one."""
        if _wx.Platform == '__WXOSX__':
            return ##: check what we need to do on linux and if this still applies on macos
        self._native_widget.SetBackgroundColour(_wx.NullColour)
        self._native_widget.Refresh()

    def set_foreground_color(self, new_color: Color):
        """Changes the foreground color of this component to the specified
        color. See gui.Color.

        :param new_color: The color to change the foreground color to."""
        self._native_widget.SetForegroundColour(new_color.to_rgba_tuple())
        self._native_widget.Refresh()

    def reset_foreground_color(self):
        """Reset the foreground color of this component to the default one."""
        self._native_widget.SetForegroundColour(_wx.NullColour)
        self._native_widget.Refresh()

    @property
    def component_position(self) -> tuple[int, int]:
        """Returns the X and Y position of this component as a tuple.

        :return: A tuple containing the X and Y position of this component
                 as two integers."""
        curr_pos = self._native_widget.GetPosition()
        return curr_pos.x, curr_pos.y

    @component_position.setter
    def component_position(self, new_position: tuple[int, int]):
        """Changes the X and Y position of this component to the specified
        values.

        :param new_position: A tuple of two integers, X and Y."""
        self._native_widget.Move(new_position)

    @property
    def component_size(self) -> tuple[int, int]:
        """Returns the width and height of this component as a tuple.

        :return: A tuple containing the width and height in device-independent
            pixels (DIP) of this component as two integers."""
        curr_size = self._native_widget.ToDIP(self._native_widget.GetSize())
        return curr_size.width, curr_size.height

    @component_size.setter
    def component_size(self, new_size: tuple[int, int]):
        """Changes the width and height of this component to the specified
        values.

        :param new_size: A tuple of two integers, width and height, in
            device-independent pixels (DIP)."""
        self._native_widget.SetSize(self._native_widget.FromDIP(new_size))

    def scaled_size(self) -> tuple[int, int]:
        """Returns the actual width and height in physical pixels that this
        component takes up. For most use cases, you will want component_size
        instead.

        :return: A tuple containing the width and height of this component as
            two integers."""
        curr_size = self._native_widget.GetSize()
        return curr_size.width, curr_size.height

    def set_min_size(self, width: int, height: int):
        """Sets the minimum size of this component to the specified width and
        height in device-independent pixels (DIP)."""
        self._native_widget.SetMinSize(self._native_widget.FromDIP(
            (width, height)))

    def set_cursor(self, hand=False):
        self._native_widget.SetCursor(_wx.Cursor(
            _wx.CURSOR_HAND if hand else _wx.CURSOR_ARROW))

    # focus methods wrappers
    def set_focus_from_kb(self):
        """Set focus to this window as the result of a keyboard action.
        Normally only called internally."""
        # TODO(ut): Normally only called internally use set_focus?
        self._native_widget.SetFocusFromKbd()

    def set_focus(self):
        """Set the focus to this window, allowing it to receive keyboard
        input."""
        self._native_widget.SetFocus()

    def wx_id_(self): ##: Avoid, we do not want to program with gui ids
        return self._native_widget.GetId()

    def update_layout(self):
        """Tells the layout applied to this component to update and lay out its
        sub-components again, based on changes that have been made to them
        since then. For example, you would have to call this if you hid or
        resized one of the sub-components, so that the other sub-components can
        be resized/moved/otherwise updated to account for that."""
        self._native_widget.Layout()

    def to_absolute_position(self,
            relative_pos: tuple[int, int]) -> tuple[int, int]:
        """Converts a position that is relative to the center of this component
        into absolute coordinates, i.e. relative to the top left of the
        screen."""
        return tuple(self._native_widget.ClientToScreen(relative_pos))

    def to_relative_position(self,
            absolute_pos: tuple[int, int]) -> tuple[int, int]:
        """The inverse of to_absolute_position."""
        return tuple(self._native_widget.ScreenToClient(absolute_pos))

    # TODO(inf) de-wx! Menu should become a wrapped component as well
    def show_popup_menu(self, menu):
        self._native_widget.PopupMenu(menu)

# Events Mixins ---------------------------------------------------------------
class WithMouseEvents(_AComponent):
    """An _AComponent that handles mouse events.

    Mouse events.
      Clicks: Default arg processor returns the HitTest result on the position
      of the event
        - on_mouse_left_dclick(hit_test: tuple[int]): left mouse doubleclick.
        - on_mouse_left_down(wrapped_evt: _WrapMouseEvt, lb_dex: int): left
        mouse click.
        - on_mouse_right_up(hit_test: tuple[int]): right mouse button released.
        - on_mouse_right_down(position: tuple[int]): right mouse button click.
        - on_mouse_middle_up(): middle mouse button released.
      - on_mouse_motion(wrapped_evt: _WrapMouseEvt, hit_test: int): mouse moved
      - on_mouse_leaving(): mouse is leaving the window
    """
    bind_lclick_double = bind_lclick_up = bind_lclick_down = False
    bind_rclick_up = bind_rclick_down = False
    bind_motion = bind_mouse_leaving = False
    bind_middle_up = False

    class _WrapMouseEvt:
        def __init__(self, mouse_evt: _wx.MouseEvent):
            self.__mouse_evt = mouse_evt

        @property
        def is_moving(self):
            return self.__mouse_evt.Moving()

        @property
        def is_dragging(self):
            return self.__mouse_evt.Dragging()

        @property
        def evt_pos(self):
            return tuple(self.__mouse_evt.GetPosition())

        @property
        def is_alt_down(self):
            return self.__mouse_evt.AltDown()

        @property
        def event_object_(self): # yak, for dragging, any better way?
            return self.__mouse_evt.GetEventObject()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        lb_hit_test = lambda event: [ # HitTest may return an int or a tuple...
            self._native_widget.HitTest(event.GetPosition())]
        if self.__class__.bind_lclick_double:
            self.on_mouse_left_dclick = self._evt_handler(_wx.EVT_LEFT_DCLICK,
                                                          lb_hit_test)
        if self.__class__.bind_lclick_down:
            self.on_mouse_left_down = self._evt_handler(_wx.EVT_LEFT_DOWN,
                lambda event: [self._WrapMouseEvt(event),
                               lb_hit_test(event)[0]])
        if self.__class__.bind_lclick_up:
            self.on_mouse_left_up = self._evt_handler(_wx.EVT_LEFT_UP,
                lambda event: [self._WrapMouseEvt(event)])
        if self.__class__.bind_rclick_up:
            self.on_mouse_right_up = self._evt_handler(_wx.EVT_RIGHT_UP,
                                                       lb_hit_test)
        if self.__class__.bind_rclick_down:
            self.on_mouse_right_down = self._evt_handler(_wx.EVT_RIGHT_DOWN,
                lambda event: [event.GetPosition()])
        if self.__class__.bind_motion:
            self.on_mouse_motion = self._evt_handler(_wx.EVT_MOTION,
                lambda event: [self._WrapMouseEvt(event),
                               lb_hit_test(event)[0]])
        if self.__class__.bind_mouse_leaving:
            self.on_mouse_leaving = self._evt_handler(_wx.EVT_LEAVE_WINDOW)
        if self.__class__.bind_middle_up:
            self.on_mouse_middle_up = self._evt_handler(_wx.EVT_MIDDLE_UP)

class WithCharEvents(_AComponent):
    """An _AComponent that handles key presses events.

    Key events.
      - on_key_down(wrapped_evt: _WrapKeyEvt): Posted when a key is starting to
        be pressed, before OS handlers have had a chance to handle it. That
        means you can override behavior like jumping to a list item when a
        letter is pressed by using this. Note that you have to return
        EventResult.FINISH if you override behavior for a particular key code,
        otherwise the OS behavior will also be executed.
      - on_key_up(wrapped_evt: _WrapKeyEvt, self: WithCharEvents): Posted when
        a key is starting to be released. OS handlers for this key have run if
        they weren't overriden by an on_key_down subscription."""
    class _WrapKeyEvt:
        def __init__(self, mouse_evt: _wx.KeyEvent):
            self.__key_evt = mouse_evt

        @property
        def key_code(self):
            return self.__key_evt.GetKeyCode()

        @property
        def is_cmd_down(self):
            return self.__key_evt.CmdDown()

        @property
        def is_shift_down(self):
            return self.__key_evt.ShiftDown()

        @property
        def is_space(self):
            return self.key_code == _wx.WXK_SPACE

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        wrap_processor = lambda event: [self._WrapKeyEvt(event)]
        self.on_key_down = self._evt_handler(_wx.EVT_KEY_DOWN, wrap_processor)
        self.on_key_up = self._evt_handler(_wx.EVT_KEY_UP, wrap_processor)

class WithDragEvents(WithMouseEvents):
    """An _AComponent that handles drag events for the mouse - alpha.

    Drag events.
      - on_mouse_capture_lost(wrapped_evt: _WrapMouseEvt) - only on __WXMSW__.
    """
    bind_lclick_up = bind_lclick_down = bind_motion = True

    def __init__(self, *args, on_drag_start, on_drag_end, on_drag_end_forced,
                 on_drag, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_mouse_left_down.subscribe(on_drag_start)
        self.on_mouse_left_up.subscribe(on_drag_end)
        if _wx.Platform == '__WXMSW__':
            self.on_mouse_capture_lost = self._evt_handler(
                _wx.EVT_MOUSE_CAPTURE_LOST)
            self.on_mouse_capture_lost.subscribe(on_drag_end_forced)
        self.on_mouse_motion.subscribe(on_drag)

# Automatic column sizing -----------------------------------------------------
class AutoSize:
    """Represents the different types of automatic sizing of columns supported
    by WB. Can't use an enum here because we need to store these ints into our
    settings."""
    FIT_MANUAL = 0
    FIT_CONTENTS = 1
    FIT_HEADER = 2

_auto_size_to_wx = {
    AutoSize.FIT_MANUAL: 0,
    AutoSize.FIT_CONTENTS: _wx.LIST_AUTOSIZE,
    AutoSize.FIT_HEADER: _wx.LIST_AUTOSIZE_USEHEADER,
}
