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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module houses parts of the GUI code that form the basis for the
more specialized parts (e.g. _AComponent)."""

__author__ = u'nycz, Infernio'

import os
import platform
import textwrap
import wx as _wx
from .events import EventHandler, null_processor
from ..bolt import deprint
from ..exception import ArgumentError

# Utilities -------------------------------------------------------------------
_cached_csf = None
def csf(): ##: This is ugly, is there no nicer way?
    """Returns the content scale factor (CSF) needed for high DPI displays."""
    global _cached_csf
    if _cached_csf is None:
        if platform.system() != u'Darwin': ##: Linux? os_name == 'nt' if so
           _cached_csf = _wx.Window().GetContentScaleFactor()
        else:
            _cached_csf = 1.0 # Everything scales automatically on macOS
    return _cached_csf

def wrapped_tooltip(tooltip_text, wrap_width=50):
    """Returns tooltip with wrapped copy of text."""
    tooltip_text = textwrap.fill(tooltip_text, wrap_width)
    return _wx.ToolTip(tooltip_text)

class Color(object):
    """A simple RGB(A) color class used to avoid having to return wx.Colour
    objects."""
    def __init__(self, red, green, blue, alpha=255): # type: (int, int, int, int) -> None
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
                raise RuntimeError(u'All color components must be in range '
                                   u'0-255.')
        self.red, self.green, self.blue, self.alpha = red, green, blue, alpha

    def to_rgba_tuple(self): # type: () -> (int, int, int, int)
        """Converts this Color object into a four-int RGBA tuple."""
        return self.red, self.green, self.blue, self.alpha

    def to_rgb_tuple(self): # type: () -> (int, int, int)
        """Converts this Color object into a three-int RGB tuple."""
        return self.red, self.green, self.blue

    def __eq__(self, other):
        return (isinstance(other, Color) and other.red == self.red
                and self.green == other.green and self.blue == other.blue
                and self.alpha == other.alpha)

    def __repr__(self):
        return f'Color(red={self.red}, green={self.green}, ' \
               f'blue={self.blue}, alpha={self.alpha})'

    @classmethod
    def from_wx(cls, color): # type: (_wx.Colour) -> Color
        """Creates a new Color object by copying the color properties from the
        specified wx.Colour object.

        :param color: The wx.Colour object to copy.
        :return: A Color object representing the same color."""
        return cls(color.Red(), color.Green(), color.Blue(), color.Alpha())

class Colors(object):
    """Color collection and wrapper for wx.ColourDatabase. Provides
    dictionary syntax access (colors[key]) and predefined colors."""
    def __init__(self):
        self._colors = {}

    def __setitem__(self, key_, value):
        """Add a color to the database."""
        if isinstance(value, Color):
            self._colors[key_] = value
        else:
            self._colors[key_] = Color(*value)

    def __getitem__(self, key_):
        """Dictionary syntax: color = colors[key]."""
        return self._colors[key_]

    def __iter__(self):
        for key_ in self._colors:
            yield key_

class _ACFrozen(object):
    """Helper for _AComponent.pause_drawing."""
    def __init__(self, wx_parent):
        self._wx_parent = wx_parent
    def __enter__(self):
        self._wx_parent.Freeze()
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._wx_parent.Thaw()

# Base Elements ---------------------------------------------------------------
class _AComponent(object):
    """Abstract base class for all GUI items. Holds a reference to the native
    wx widget that we abstract over.
    # :type _native_widget: _wx.Window FIXME(ut) PY3: add type info"""
    _wx_widget_type = None # type: type

    def __init__(self, parent, *args, **kwargs):
        """Creates a new _AComponent instance by initializing the wx widget
        with the specified parent, args and kwargs."""
        self._native_widget = self._wx_widget_type(self._resolve(parent),
                                                   *args, **kwargs)

    def _evt_handler(self, evt, arg_proc=null_processor):
        """Register an EventHandler on _native_widget"""
        return EventHandler(self._native_widget, evt, arg_proc)

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
        if isinstance(obj, _AComponent):
            return obj._native_widget
        elif isinstance(obj, _wx.Window):
            return obj
        elif obj is None:
            return None
        else:
            raise RuntimeError(f"Failed to resolve object '{obj!r}' to wx "
                               f"object.")

    def get_component_name(self): # type: () -> str
        """Returns the name of this component.

        :return: This component's name."""
        return self._native_widget.GetName()

    def set_component_name(self, new_ctrl_name): # type: (str) -> None
        """Sets the name of this component to the specified name.

        :param new_ctrl_name: The string to change this component's name to."""
        self._native_widget.SetName(new_ctrl_name)

    @property
    def visible(self): # type: () -> bool
        """Returns True if this component is currently visible, i.e. if the
        user can see it in the GUI.

        :return: True if this component is currently visible."""
        return self._native_widget.IsShown()

    @visible.setter
    def visible(self, is_visible): # type: (bool) -> None
        """Shows or hides this component based on the specified parameter.

        :param is_visible: Whether or not to show this component."""
        self._native_widget.Show(is_visible)

    @property
    def enabled(self): # type: () -> bool
        """Returns True if this component is currently enabled, i.e. if the
        user can interact with it. Disabled widgets are typically styled in
        some way to indicate this fact to the user (e.g. greyed out).

        :return: True if this component is currently enabled."""
        return self._native_widget.IsEnabled()

    @enabled.setter
    def enabled(self, is_enabled): # type: (bool) -> None
        """Enables or disables this component based on the specified parameter.

        :param is_enabled: Whether or not to enable this component."""
        self._native_widget.Enable(is_enabled)

    @property
    def tooltip(self): # type: () -> str
        """Returns the current contents of this component's tooltip. If no
        tooltip is set, returns an empty string.

        :return: This component's tooltip."""
        return self._native_widget.GetToolTipText() or u''

    @tooltip.setter
    def tooltip(self, new_tooltip): # type: (str) -> None
        """Sets the tooltip of this component to the specified string. If the
        string is empty or None, the tooltip is simply removed.

        :param new_tooltip: The string to change the tooltip to."""
        if not new_tooltip:
            self._native_widget.UnsetToolTip()
        else:
            self._native_widget.SetToolTip(wrapped_tooltip(new_tooltip))

    def get_background_color(self): # type: () -> Color
        """Returns the background color of this component as a tuple.

        :return: The background color of this component."""
        return Color.from_wx(self._native_widget.GetBackgroundColour())

    def set_background_color(self, new_color): # type: (Color) -> None
        """Changes the background color of this component to the specified
        color. See gui.Color.

        :param new_color: The color to change the background color to."""
        self._native_widget.SetBackgroundColour(new_color.to_rgba_tuple())
        self._native_widget.Refresh()

    def reset_background_color(self):
        """Resets the background color of this component to the default one."""
        if _wx.Platform == '__WXMAC__': return ##: check what we need to do on linux
        self._native_widget.SetBackgroundColour(_wx.NullColour)
        self._native_widget.Refresh()

    def set_foreground_color(self, new_color): # type: (Color) -> None
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
    def component_position(self):
        """Returns the X and Y position of this component as a tuple.

        :return: A tuple containing the X and Y position of this this component
                 as two integers."""
        curr_pos = self._native_widget.GetPosition()
        return curr_pos.x, curr_pos.y

    @component_position.setter
    def component_position(self, new_position): # type: (tuple) -> None
        """Changes the X and Y position of this component to the specified
        values.

        :param new_position: A tuple of two integers, X and Y."""
        self._native_widget.Move(new_position)

    @property
    def component_size(self):
        """Returns the width and height of this component as a tuple.

        :return: A tuple containing the width and height in device-independent
            pixels (DIP) of this component as two integers."""
        curr_size = self._native_widget.ToDIP(self._native_widget.GetSize())
        return curr_size.width, curr_size.height

    @component_size.setter
    def component_size(self, new_size): # type: (tuple) -> None
        """Changes the width and height of this component to the specified
        values.

        :param new_size: A tuple of two integers, width and height, in
            device-independent pixels (DIP)."""
        self._native_widget.SetSize(self._native_widget.FromDIP(new_size))

    def scaled_size(self):
        """Returns the actual width and height in physical pixels that this
        component takes up. For most use cases, you will want component_size
        instead.

        :return: A tuple containing the width and height of this component as
            two integers."""
        curr_size = self._native_widget.GetSize()
        return curr_size.width, curr_size.height

    def set_min_size(self, width, height): # type: (int, int) -> None
        """Sets the minimum size of this component to the specified width and
        height in device-independent pixels (DIP)."""
        self._native_widget.SetMinSize(self._native_widget.FromDIP(
            (width, height)))

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

    def destroy_component(self):
        """Destroys this component - non-internal usage is a smell, avoid if at
        all possible."""
        self._native_widget.Destroy()

    def wx_id_(self): ##: Avoid, we do not want to program with gui ids
        return self._native_widget.GetId()

    def update_layout(self):
        """Tells the layout applied to this component to update and lay out its
        sub-components again, based on changes that have been made to them
        since then. For example, you would have to call this if you hid or
        resized one of the sub-components, so that the other sub-components can
        be resized/moved/otherwise updated to account for that."""
        self._native_widget.Layout()

    def pause_drawing(self):
        """To be used via Python's 'with' statement. Pauses all visual updates
        to this component while in the with statement."""
        return _ACFrozen(self._native_widget)

    def to_absolute_position(self, relative_pos): # type: (tuple) -> tuple
        """Converts the specified position that is relative to the center of
        this component into absolute coordinates, i.e. relative to the top left
        of the screen."""
        return tuple(self._native_widget.ClientToScreen(relative_pos))

    def to_relative_position(self, absolute_pos): # type: (tuple) -> tuple
        """The inverse of to_absolute_position."""
        return tuple(self._native_widget.ScreenToClient(absolute_pos))

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

    class _WrapMouseEvt(object):
        def __init__(self, mouse_evt):
            self.__mouse_evt = mouse_evt # type: _wx.MouseEvent

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

    def __init__(self, *args, **kwargs):
        super(WithMouseEvents, self).__init__(*args, **kwargs)
        lb_hit_test = lambda event: [ # HitTest may return an int or a tuple...
            self._native_widget.HitTest(event.GetPosition())]
        if self.__class__.bind_lclick_double:
            self.on_mouse_left_dclick = self._evt_handler(_wx.EVT_LEFT_DCLICK,
                                                          lb_hit_test)
        if self.__class__.bind_lclick_down:
            self.on_mouse_left_down = self._evt_handler(_wx.EVT_LEFT_DOWN,
                lambda event: [self._WrapMouseEvt(event),
                               lb_hit_test(event)[0]])
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
    class _WrapKeyEvt(object):
        def __init__(self, mouse_evt):
            self.__key_evt = mouse_evt # type: _wx.KeyEvent

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
        super(WithCharEvents, self).__init__(*args, **kwargs)
        wrap_processor = lambda event: [self._WrapKeyEvt(event)]
        self.on_key_down = self._evt_handler(_wx.EVT_KEY_DOWN, wrap_processor)
        self.on_key_up = self._evt_handler(_wx.EVT_KEY_UP, wrap_processor)

class ImageWrapper(object):
    """Wrapper for images, allowing access in various formats/classes.

    Allows image to be specified before wx.App is initialized."""

    typesDict = {u'png': _wx.BITMAP_TYPE_PNG, u'jpg': _wx.BITMAP_TYPE_JPEG,
                 u'jpeg': _wx.BITMAP_TYPE_JPEG, u'ico': _wx.BITMAP_TYPE_ICO,
                 u'bmp': _wx.BITMAP_TYPE_BMP, u'tif': _wx.BITMAP_TYPE_TIF}

    def __init__(self, filename, imageType=None, iconSize=16):
        self._img_path = filename.s # must be a bolt.Path
        try:
            self._img_type = imageType or self.typesDict[filename.cext[1:]]
        except KeyError:
            deprint(f'Unknown image extension {filename.cext}')
            self._img_type = _wx.BITMAP_TYPE_ANY
        self.bitmap = None
        self.icon = None
        self.iconSize = iconSize
        if not os.path.exists(self._img_path.split(u';')[0]):
            raise ArgumentError(f'Missing resource file: {filename}.')

    def get_bitmap(self):
        if not self.bitmap:
            if self._img_type == _wx.BITMAP_TYPE_ICO:
                self.GetIcon()
                w, h = self.icon.GetWidth(), self.icon.GetHeight()
                self.bitmap = _wx.Bitmap(w, h)
                self.bitmap.CopyFromIcon(self.icon)
                # Hack - when user scales windows display icon may need scaling
                if w != self.iconSize or h != self.iconSize: # rescale !
                    self.bitmap = _wx.Bitmap(
                        self.bitmap.ConvertToImage().Scale(
                            self.iconSize, self.iconSize,
                            _wx.IMAGE_QUALITY_HIGH))
            else:
                self.bitmap = _wx.Bitmap(self._img_path, self._img_type)
        return self.bitmap

    def GetIcon(self):
        if not self.icon:
            if self._img_type == _wx.BITMAP_TYPE_ICO:
                self.icon = _wx.Icon(self._img_path, _wx.BITMAP_TYPE_ICO,
                                     self.iconSize, self.iconSize)
                # we failed to get the icon? (when display resolution changes)
                if not self.icon.GetWidth() or not self.icon.GetHeight():
                    self.icon = _wx.Icon(self._img_path, _wx.BITMAP_TYPE_ICO)
            else:
                self.icon = _wx.Icon()
                self.icon.CopyFromBitmap(self.get_bitmap())
        return self.icon

    @staticmethod
    def bmp_from_bitstream(bm_width, bm_height, stream_data, with_alpha):
        """Creates a bitmap from the specified stream data."""
        wx_depth = (32 if with_alpha else 24)
        wx_fmt = (_wx.BitmapBufferFormat_RGBA if with_alpha
                  else _wx.BitmapBufferFormat_RGB)
        bm = _wx.Bitmap(bm_width, bm_height, wx_depth)
        bm.CopyFromBuffer(stream_data, wx_fmt)
        return bm

    @staticmethod
    def Load(srcPath, quality):
        """Hasty wrapper around wx.Image - loads srcPath with specified
        quality if a jpeg."""
        bitmap = _wx.Image(srcPath.s)
        # This only has an effect on jpegs, so it's ok to do it on every kind
        bitmap.SetOption(_wx.IMAGE_OPTION_QUALITY, quality)
        return bitmap
