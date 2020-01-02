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

"""This module houses parts of the GUI code that form the basis for the
more specialized parts (e.g. _AComponent)."""

__author__ = u'nycz, Infernio'

import textwrap
import wx as _wx

# Utilities -------------------------------------------------------------------
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

    def _to_wx(self): # type: () -> _wx.Colour
        """Converts this Color object back into a wx.Colour object.

        :return: A wx.Colour object representing the same color as this one."""
        return _wx.Colour(self.red, self.green, self.blue, self.alpha)

    @staticmethod
    def _from_wx(color): # type: (_wx.Colour) -> Color
        """Creates a new Color object by copying the color properties from the
        specified wx.Colour object.

        :param color: The wx.Colour object to copy.
        :return: A Color object representing the same color."""
        return Color(color.red, color.green, color.blue, color.alpha)

# Base Elements ---------------------------------------------------------------
class _AComponent(object):
    """Abstract base class for all GUI items. Holds a reference to the native
    wx widget that we abstract over.
    # :type _native_widget: _wx.Window FIXME(ut) PY3: add type info
    """
    def __init__(self, wx_window_type, parent, *args, **kwargs):
        """Creates a new _AComponent instance. This initializes _native_widget
        to None, which will later receive a proper value inside the __init__
        methods of _AComponent's subclasses."""
        self._native_widget = wx_window_type(self._resolve(parent), *args,
                                             **kwargs)

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
        else:
            raise RuntimeError(u"Failed to resolve object '%r' to wx object." %
                               obj)

    @property
    def component_name(self): # type: () -> unicode
        """Returns the name of this component.

        :return: This component's name."""
        return self._native_widget.GetName()

    @component_name.setter
    def component_name(self, new_name): # type: (unicode) -> None
        """Sets the name of this component to the specified name.

        :param new_name: The string to change this component's name to."""
        self._native_widget.SetName(new_name)

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
    def tooltip(self): # type: () -> unicode
        """Returns the current contents of this component's tooltip. If no
        tooltip is set, returns an empty string.

        :return: This component's tooltip."""
        return self._native_widget.GetToolTipString() or u''

    @tooltip.setter
    def tooltip(self, new_tooltip): # type: (unicode) -> None
        """Sets the tooltip of this component to the specified string. If the
        string is empty or None, the tooltip is simply removed.

        :param new_tooltip: The string to change the tooltip to."""
        if not new_tooltip:
            self._native_widget.UnsetToolTip()
        else:
            self._native_widget.SetToolTip(wrapped_tooltip(new_tooltip))

    # TODO: use a custom color class here
    @property
    def background_color(self): # type: () -> _wx.Colour
        """Returns the background color of this component as a wx.Colour
        object.

        :return: The background color of this component."""
        return self._native_widget.GetBackgroundColour()

    @background_color.setter
    def background_color(self, new_color): # type: (_wx.Colour) -> None
        """Changes the background color of this component to the color
        represented by the specified wx.Colour object.

        :param new_color: The color to change the background color to."""
        self._native_widget.SetBackgroundColour(new_color)
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

        :return: A tuple containing the width and height size of this component
                 as two integers."""
        curr_size = self._native_widget.GetSize()
        return curr_size.width, curr_size.height

    @component_size.setter
    def component_size(self, new_size): # type: (tuple) -> None
        """Changes the X and Y size of this component to the specified
        values.

        :param new_size: A tuple of two integers, X and Y size."""
        self._native_widget.SetSize(new_size)

    def set_min_size(self, width, height): # type: (int, int) -> None
        """Sets the minimum size of this component to the specified width and
        height."""
        self._native_widget.SetMinSize(_wx.Size(width, height))

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

    @property
    def wx_id_(self): # avoid, we do not want to program with gui ids
        return self._native_widget.GetId()
