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
"""Houses MediaViewer, an API for showing both static and animated images."""
from __future__ import annotations

__author__ = 'Infernio, Utumno'

from typing import get_type_hints

import wx as _wx
import wx.adv as _adv

from .base_components import _AComponent, Color, WithMouseEvents
from .events import EventResult
from .images import AnimatedImage, GuiImage
from .layouts import VLayout
from ..bolt import Path

# Loading images is expensive, so keep a central cache (indexed by CRC for
# invalidation purposes)
_img_cache: dict[Path, tuple[int, GuiImage]] = {}

def _load_image(img_path: Path):
    """Load an image from the specified path, checking cache first."""
    if img_path is None:
        return None
    try:
        img_crc = img_path.crc
    except FileNotFoundError:
        return None
    else:
        cache_entry = _img_cache.get(img_path)
        if cache_entry is not None and cache_entry[0] == img_crc:
            # We can use the cached image
            return cache_entry[1]
        new_image = GuiImage.from_path(img_path)
        _img_cache[img_path] = (img_crc, new_image)
        return new_image

class _AViewer(_AComponent):
    """Abstract base class for viewers."""
    def __init__(self, parent, width, height, scaling=1, ##: scaling unused
            background=None):
        super().__init__(parent, size=(width, height), style=_wx.BORDER_SUNKEN)
        self._native_widget.SetBackgroundStyle(_wx.BG_STYLE_CUSTOM)
        self._gui_bitmap = None
        self._background = self._get_brush(
            background or self._native_widget.GetBackgroundColour())
        #self.SetSizeHints(width,height,width,height)
        #--Events
        self._on_paint = self._evt_handler(_wx.EVT_PAINT)
        self._on_paint.subscribe(self._handle_paint)
        self._cached_scaled_size = (width, height)
        self.handle_resize()

    def set_background(self, background):
        self._background = self._get_brush(background)
        self.handle_resize()

    @staticmethod
    def _get_brush(background):
        if isinstance(background, Color):
            background = background.to_rgba_tuple()
        if isinstance(background, tuple):
            background = _wx.Colour(*background)
        if isinstance(background, _wx.Colour):
            background = _wx.Brush(background)
        return background

    def handle_resize(self, viewer_scaled_size=None):
        # This looks about as simple is it can be. Create a wx.Bitmap to
        # draw on, a DC to do the drawing with / associate the drawing with the
        # widget. Image manipulation can only really be done as a wx.Image
        # (unless you want to roll your own algorithms...bleh), while
        # drawing/blotting can only be done as wx.Bitmap (basically a thin
        # wrapper around the platform specific GUI image primitive), so you
        # usually have to do a bitmap -> image -> bitmap dance to do any
        # modifications at draw time. Alternatively we could store the base
        # image to be drawn as just a wx.Image and make a copy when we want the
        # resized version, but that's still an image -> image (copy) -> bitmap
        viewer_scaled_size = viewer_scaled_size or self._cached_scaled_size
        x, y = self._cached_scaled_size = viewer_scaled_size
        if x <= 0 or y <= 0: return
        self._buffer = _wx.Bitmap(x,y)
        dc = _wx.MemoryDC()
        dc.SelectObject(self._buffer)
        # Draw
        dc.SetBackground(self._background)
        dc.Clear()
        if self._gui_bitmap is not None:
            old_x,old_y = self._gui_bitmap.GetSize()
            scale = min(float(x)/old_x, float(y)/old_y)
            new_x = old_x * scale
            new_y = old_y * scale
            pos_x = max(0,x-new_x)/2
            pos_y = max(0,y-new_y)/2
            image = self._gui_bitmap.ConvertToImage()
            image.Rescale(int(new_x), int(new_y), _wx.IMAGE_QUALITY_HIGH)
            dc.DrawBitmap(_wx.Bitmap(image), int(pos_x), int(pos_y))
        del dc
        self._native_widget.Refresh()
        self._native_widget.Update()

    def _handle_paint(self):
        dc = _wx.BufferedPaintDC(self._native_widget, self._buffer)
        return EventResult.FINISH

    def set_viewer_image(self, bmp):
        """Set the bitmap on the native_widget and return the wx object for
        caching"""
        raise NotImplementedError

class _WithCursorMixin(_AViewer, WithMouseEvents):
    """Mixin for viewers that want to show a magnifiying glass icon on hover
    and open the shown image in a viewer."""
    bind_lclick_double = bind_middle_up = True

    def bind_callback(self, click_callback):
        """Bind the specified callback to run on double click and middle mouse
        button click."""
        self.on_mouse_left_dclick.subscribe(click_callback)
        self.on_mouse_middle_up.subscribe(click_callback)

    def set_viewer_image(self, bmp):
        # Don't want the bitmap to resize until we call self.update_layout()
        with self.pause_drawing():
            img = super().set_viewer_image(bmp)
            self._native_widget.SetCursor(
                _wx.Cursor(_wx.CURSOR_MAGNIFIER if img else _wx.CURSOR_ARROW))
        return img

class _PictureViewer(_AViewer):
    """A viewer for displaying static images."""
    def set_viewer_image(self, bmp):
        if bmp is not None:
            bmp = self._resolve(bmp)
            # If bmp comes from a BmpFromStream, this will be a bitmap; if it
            # comes from a _BmpFromPath, it will be a bitmap bundle (with only
            # one bitmap in it)
            if isinstance(bmp, _wx.BitmapBundle):
                bmp = bmp.GetBitmap(bmp.GetDefaultSize())
        self._gui_bitmap = bmp
        return self._gui_bitmap

class _AnimationViewer(_AViewer):
    """A viewer for animated images, e.g. GIFs."""
    _native_widget: _adv.AnimationCtrl

    def set_viewer_image(self, bmp):
        bmp = self._resolve(bmp)
        self._native_widget.SetAnimation(bmp)
        self._native_widget.Play()
        return bmp

    def handle_resize(self, viewer_scaled_size=None):
        viewer_scaled_size = viewer_scaled_size or self._cached_scaled_size
        self._cached_scaled_size = viewer_scaled_size
        self._native_widget.CenterOnParent()
        ##: This isn't working. Is there any way to actually scale down the
        # AnimationCtrl? I tried bypassing it entirely and doing the animation
        # frame processing myself, but it turns out wx.Animation.GetFrame is
        # not implemented on GTK, so that's a nonstarter :/
        self._native_widget.SetMaxSize(viewer_scaled_size)
        self._native_widget.Refresh()
        self._native_widget.Update()

    ##: Doesn't draw the background right now, not sure how to do that
    def _handle_paint(self):
        pass

class MediaViewer(_AComponent):
    """A unified media viewer that can handle both static and animated
    images."""
    _picture_viewer: _PictureViewer
    _anim_viewer: _AnimationViewer

    def __init__(self, parent, width, height, scaling=1, background=None):
        super().__init__(parent, size=(width, height))
        type_hints = get_type_hints(self.__class__)
        self._picture_viewer = type_hints['_picture_viewer'](self, width,
            height, scaling, background)
        self._anim_viewer = type_hints['_anim_viewer'](self, width, height,
            scaling, background)
        self._active_viewer: _AViewer | None = None
        self._switch_to_mode(animated_mode=False)
        self._on_size = self._evt_handler(_wx.EVT_SIZE)
        self._on_size.subscribe(self._on_resize)
        VLayout(item_expand=True, item_weight=1, items=[
            self._picture_viewer,
            self._anim_viewer,
        ]).apply_to(self)

    def _switch_to_mode(self, *, animated_mode: bool):
        """Switch the viewer to the animated or static viewer, depending on
        animated_mode."""
        self._picture_viewer.visible = not animated_mode
        self._anim_viewer.visible = animated_mode
        self._active_viewer = (self._anim_viewer if animated_mode else
                               self._picture_viewer)

    def _on_resize(self):
        """Internal callback, called when the window is resized."""
        self._active_viewer.handle_resize(self.scaled_size())

    def _show_image(self, img):
        """Shared code of load_from_path and load_from_buffer."""
        self._switch_to_mode(animated_mode=isinstance(img, AnimatedImage))
        self._active_viewer.set_viewer_image(img)
        self._active_viewer.handle_resize(self.scaled_size())

    # Public API --------------------------------------------------------------
    def load_from_path(self, image_path: Path):
        """Load an image from the specified path and show it in the viewer."""
        self._show_image(_load_image(image_path))

    def load_from_buffer(self, image_buffer: GuiImage):
        """Load an image from the specified buffered image and show it in the
        viewer."""
        self._show_image(image_buffer)

    def clear_viewer(self):
        """Clear the viewer so that only the background is shown."""
        self._show_image(None)

    def set_viewer_background(self, background_color: Color):
        """Change the background color used for the viewer to the specified
        color."""
        self._picture_viewer.set_background(background_color)
        ##: This doesn't work, see _AnimationViewer._handle_paint
        self._anim_viewer.set_background(background_color)

class _PictureViewerWithCursor(_WithCursorMixin, _PictureViewer): pass
class _AnimationViewerWithCusor(_WithCursorMixin, _AnimationViewer): pass

class MediaViewerWithCursor(MediaViewer):
    """Similar to MediaViewer, but also shows changes the cursor to a
    magnifiying glass icon when hovering over the viewer and allows opening the
    image in the system's default program when double clicking or clicking the
    middle mouse button."""
    _picture_viewer: _PictureViewerWithCursor
    _anim_viewer: _AnimationViewerWithCusor

    def __init__(self, parent, width, height, scaling=1, background=None, *,
            click_callback: callable = None):
        super().__init__(parent, width, height, scaling, background)
        if click_callback is not None:
            self._picture_viewer.bind_callback(click_callback)
            self._anim_viewer.bind_callback(click_callback)
