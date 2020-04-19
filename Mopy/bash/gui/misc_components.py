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
"""This module houses GUI classes that did not fit anywhere else. Once similar
classes accumulate in here, feel free to break them out into a module."""

__author__ = u'nycz, Infernio, Utumno'

import wx as _wx

from .base_components import _AComponent, Color, WithMouseEvents, \
    Image
from .events import EventResult
from ..bolt import Path

class Font(_wx.Font):
    @staticmethod
    def Style(font_, bold=False, slant=False, underline=False):
        if bold: font_.SetWeight(_wx.FONTWEIGHT_BOLD)
        if slant: font_.SetStyle(_wx.FONTSTYLE_SLANT)
        else: font_.SetStyle(_wx.FONTSTYLE_NORMAL)
        font_.SetUnderlined(underline)
        return font_

class Picture(_AComponent):
    """Picture panel."""
    _wx_widget_type = _wx.Window

    def __init__(self, parent, width, height, scaling=1,  ##: scaling unused
                 style=_wx.BORDER_SUNKEN, background=_wx.MEDIUM_GREY_BRUSH):
        super(Picture, self).__init__(parent, size=(width, height),
                                      style=style)
        self._native_widget.SetBackgroundStyle(_wx.BG_STYLE_CUSTOM)
        self.bitmap = None
        self.background = self._get_brush(
            background or self._native_widget.GetBackgroundColour())
        #self.SetSizeHints(width,height,width,height)
        #--Events
        self._on_paint = self._evt_handler(_wx.EVT_PAINT)
        self._on_paint.subscribe(self._handle_paint)
        self._on_size = self._evt_handler(_wx.EVT_SIZE)
        self._on_size.subscribe(self._handle_resize)
        self._handle_resize()

    def SetBackground(self, background):
        self.background = self._get_brush(background)
        self._handle_resize()

    @staticmethod
    def _get_brush(background):
        if isinstance(background, Color):
            background = background.to_rgba_tuple()
        if isinstance(background, tuple):
            background = _wx.Colour(*background)
        if isinstance(background, _wx.Colour):
            background = _wx.Brush(background)
        return background

    def set_bitmap(self, bmp):
        """Set the bitmap on the native_widget and return the wx object for
        caching"""
        if isinstance(bmp, Path):
            bmp = (bmp.isfile() and Image(bmp.s).GetBitmap()) or None
        elif isinstance(bmp, tuple):
            bmp = Image.GetImage(*bmp).ConvertToBitmap()
        self.bitmap = bmp
        self._handle_resize()
        return self.bitmap

    def _handle_resize(self): ##: is all these wx.Bitmap calls needed? One right way?
        x, y = self.component_size
        if x <= 0 or y <= 0: return
        self.buffer = _wx.Bitmap(x,y)
        dc = _wx.MemoryDC()
        dc.SelectObject(self.buffer)
        # Draw
        dc.SetBackground(self.background)
        dc.Clear()
        if self.bitmap:
            old_x,old_y = self.bitmap.GetSize()
            scale = min(float(x)/old_x, float(y)/old_y)
            new_x = old_x * scale
            new_y = old_y * scale
            pos_x = max(0,x-new_x)/2
            pos_y = max(0,y-new_y)/2
            image = self.bitmap.ConvertToImage()
            image.Rescale(new_x, new_y, _wx.IMAGE_QUALITY_HIGH)
            dc.DrawBitmap(_wx.Bitmap(image), pos_x, pos_y)
        del dc
        self._native_widget.Refresh()
        self._native_widget.Update()

    def _handle_paint(self):
        dc = _wx.BufferedPaintDC(self._native_widget, self.buffer)
        return EventResult.FINISH

class PictureWithCursor(Picture, WithMouseEvents):
    bind_lclick_double = bind_middle_up = True

    def set_bitmap(self, bmp):
        # Don't want the bitmap to resize until we call self.Layout()
        self._native_widget.Freeze()
        img = super(PictureWithCursor, self).set_bitmap(bmp)
        self._native_widget.SetCursor(
            _wx.Cursor(_wx.CURSOR_MAGNIFIER if img else _wx.CURSOR_ARROW))
        self._native_widget.Thaw()
        return img

class _ALine(_AComponent):
    """Abstract base class for simple graphical lines."""
    _line_style = None # override in subclasses
    _wx_widget_type = _wx.StaticLine

    def __init__(self, parent):
        super(_ALine, self).__init__(parent, style=self._line_style)

class HorizontalLine(_ALine):
    """A simple horizontal line."""
    _line_style = _wx.LI_HORIZONTAL

class VerticalLine(_ALine):
    """A simple vertical line."""
    _line_style = _wx.LI_VERTICAL
