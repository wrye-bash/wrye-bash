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
"""Encapsulate wx images."""
from __future__ import annotations

import io
import os
import xml.etree.ElementTree as ET
from copy import copy

import wx as _wx
import wx.svg as _svg

from ._gui_globals import get_image, get_image_dir
from .base_components import Lazy, scaled
from ..bolt import deprint, Path
from ..exception import ArgumentError, GuiError

ET.register_namespace('', 'http://www.w3.org/2000/svg')

class GuiImage(Lazy):
    """Wrapper around various native image classes."""
    # allow to directly access the _native_window (force via _resolve?)
    _bypass_native_init = True

    img_types = {
        '.bmp': _wx.BITMAP_TYPE_BMP,
        '.ico': _wx.BITMAP_TYPE_ICO,
        '.jpeg': _wx.BITMAP_TYPE_JPEG,
        '.jpg': _wx.BITMAP_TYPE_JPEG,
        '.png': _wx.BITMAP_TYPE_PNG,
        '.svg': None, # Special handling needed, see _is_svg
        '.tif': _wx.BITMAP_TYPE_TIF,
        '.tga': _wx.BITMAP_TYPE_TGA,
    }

    def __init__(self, img_path, iconSize=-1, imageType=None, quality=None,
                 *args, **kwargs):
        self._img_path = img_path
        if not self.allow_create():
            raise ArgumentError(f'Missing resource file: {self._img_path}')
        super().__init__(*args, **kwargs)
        self.iconSize = iconSize
        self._img_type = imageType
        self._quality = quality

    def set_icon_size(self, icon_size: int) -> None:
        if self._is_created():
            raise GuiError(f'Cannot change icon size for {self._img_path} '
                           'after native widget initialization.')
        self.iconSize = icon_size

    def allow_create(self):
        return os.path.exists(self._img_path.split(';')[0])

    def get_img_size(self):
        return self._native_widget.GetWidth(), self._native_widget.GetHeight()

    @classmethod
    def from_path(cls, img_path: str | Path, imageType=None, iconSize=-1,
                  quality=None):
        """Static factory - creates an Image component from an image file."""
        _root, extension = os.path.splitext(img_path := f'{img_path}')
        try:
            img_type = imageType or cls.img_types[extension.lower()]
        except KeyError:
            deprint(f'Unknown image extension {extension}')
            img_type = _wx.BITMAP_TYPE_ANY
        if (is_svg := img_type is None) and iconSize == -1:
            raise ArgumentError('You must specify iconSize to '
                                'rasterize an SVG to a bitmap!')
        if not os.path.isabs(img_path):
            img_path = get_image_dir().join(img_path).s
        if cls is not GuiImage:
            return cls(img_path, iconSize, img_type, quality)
        if img_type == _wx.BITMAP_TYPE_ICO:
            return _BmpFromIcoPath(img_path, iconSize, img_type, quality)
        elif is_svg:
            return _SvgFromPath(img_path, iconSize, img_type, quality)
        else:
            return _BmpFromPath(img_path, iconSize, img_type, quality)

class _SvgFromPath(GuiImage):
    """Wrap an svg."""
    _native_widget: _wx.BitmapBundle.FromBitmaps

    def __init__(self, *args, **kwargs):
        self._svg_data = None
        self._cached_svg_vars = {}
        super().__init__(*args, **kwargs)

    @property
    def _native_widget(self):
        if not self._is_created():
            if (svg_data := self._svg_data) is None:
                with open(self._img_path, 'rb') as ins:
                    svg_data = ins.read()
            for var_name, var_value in self._svg_vars().items():
                var_bytes = b'var(--' + var_name + b')'
                if var_bytes in svg_data:
                    svg_data = svg_data.replace(var_bytes, var_value)
            svg_img = _svg.SVGimage.CreateFromBytes(svg_data)
            # Use a bitmap bundle so we get an actual high-res asset at high
            # DPIs, rather than wx deciding to scale up the low-res asset
            wanted_svgs = [svg_img.ConvertToScaledBitmap((s, s))
                           for s in (self.iconSize, scaled(self.iconSize))]
            self._cached_args = (wanted_svgs,)
        return super()._native_widget
    
    def composite(self, base_svg, *layer_svgs: str | Path):
        """Create a composite SVG image, by combining elements from the given
        layers, with the first layer being the lowest layer.
        """
        im_dir_join = get_image_dir().join
        svg_paths = [p if os.path.isabs(p) else im_dir_join(p).s for p in
                     (base_svg, *layer_svgs)]
        for (ldex, layer) in enumerate(map(ET.parse, svg_paths)):
            layer_svg_root = layer.getroot()
            if layer_svg_root is None:
                raise ValueError(f'Invalid SVG {layer=!r} loaded from '
                                 f'{svg_paths[ldex]}')
            if not ldex:
                base_layer, base_svg_root = layer, layer_svg_root
                continue
            base_svg_root.extend(layer_svg_root.findall('.*'))
        with io.BytesIO() as out:
            base_layer.write(out)
            self._svg_data = out.getvalue()

    def with_svg_vars(self, **svg_vars):
        """Create a copy of this image with the specified svg variables."""
        svg_vars = {
            name.encode('utf8'): value
            for name, value in svg_vars.items()
        }
        new_instance = copy(self)
        new_instance._cached_svg_vars = svg_vars
        return new_instance
    
    def _svg_vars(self):
        from .. import bass
        if bass.settings:
            return {
                b'invert': b'#FFF' if bass.settings['bash.use_reverse_icons'] else b'#000'
            } | self._cached_svg_vars
        else:
            return self._cached_svg_vars

class IcoFromPng(GuiImage):
    """Create a wx.Icon from a GuiImage instance - no new uses please!"""
    _native_widget: _wx.Icon

    def __init__(self, gui_image):
        super(GuiImage, self).__init__() # bypass GuiImage.__init__
        self._gui_image = gui_image

    @property
    def _native_widget(self):
        if self._is_created(): return self._cached_widget
        native = super()._native_widget # create a plain wx.Icon
        native_bmp = self._resolve(self._gui_image)
        if isinstance(native_bmp, _wx.BitmapBundle):
            native_bmp = native_bmp.GetBitmap(native_bmp.GetDefaultSize())
        native.CopyFromBitmap(native_bmp)
        return native

class _IcoFromPath(GuiImage):
    """Only used internally in _BmpFromIcoPath."""
    _native_widget: _wx.Icon

    @property
    def _native_widget(self):
        if self._is_created(): return self._cached_widget
        self._cached_args = self._img_path, self._img_type, self.iconSize, \
            self.iconSize
        widget = super()._native_widget
        # we failed to get the icon? (when display resolution changes)
        ##: Ut: I (hope I) carried previous logic to new API but is there a
        # better way (and/or any leaks)?
        if not all(self.get_img_size()):
            self._cached_args = self._img_path, _wx.BITMAP_TYPE_ICO
            self.native_destroy()
            return super()._native_widget
        return widget

class _BmpFromIcoPath(GuiImage):
    _native_widget: _wx.Bitmap

    @property
    def _native_widget(self):
        if self._is_created(): return self._cached_widget
        img_ico = _IcoFromPath(self._img_path, self.iconSize, self._img_type)
        w, h = img_ico.get_img_size()
        self._cached_args = w, h
        native = super()._native_widget
        native.CopyFromIcon(self._resolve(img_ico))
        # Hack - when user scales windows display icon may need scaling
        if (self.iconSize != -1 and w != self.iconSize or
            h != self.iconSize): # rescale !
            scaled = native.ConvertToImage().Scale(self.iconSize,
                self.iconSize, _wx.IMAGE_QUALITY_HIGH)
            self._cached_args = scaled,
            return super()._native_widget
        return native

class ImgFromPath(GuiImage):
    """Used internally in _BmpFromPath but also used to create a wx.Image
    directly."""
    _native_widget: _wx.Image

    @property
    def _native_widget(self):
        if self._is_created(): return self._cached_widget
        self._cached_args = self._img_path, self._img_type
        native = super()._native_widget
        if self.iconSize != -1:
            # Don't use the scaled icon size here - _BmpFromPath performs its
            # own scaling and Screen_ConvertTo wouldn't want to scale anyways
            wanted_size = self.iconSize
            if self.get_img_size() != (wanted_size, wanted_size):
                native.Rescale(wanted_size, wanted_size,
                    _wx.IMAGE_QUALITY_HIGH)
        if self._quality is not None: # This only has an effect on jpgs
            native.SetOption(_wx.IMAGE_OPTION_QUALITY, self._quality)
        return native

    def save_bmp(self, imagePath, exten='.jpg'):
        return self._native_widget.SaveFile(imagePath, self.img_types[exten])

class _BmpFromPath(GuiImage):
    _native_widget: _wx.BitmapBundle.FromBitmaps

    @property
    def _native_widget(self):
        # Pass wx.Image to wx.Bitmap
        base_img: _wx.Image = self._resolve(ImgFromPath(self._img_path,
            imageType=self._img_type))
        scaled_imgs = [base_img]
        if self.iconSize != -1:
            # If we can, also add a scaled-up version so wx stops trying to
            # scale this by itself - using a higher-res image here if we have
            # one would be better, but that would be very difficult to
            # implement, something for the (far) future
            wanted_size = scaled(self.iconSize)
            scaled_imgs.append(base_img.Scale(wanted_size, wanted_size,
                quality=_wx.IMAGE_QUALITY_HIGH))
        self._cached_args = (list(map(_wx.Bitmap, scaled_imgs)),)
        return super()._native_widget

class BmpFromStream(GuiImage):
    """Call init directly - hmm."""
    _native_widget: _wx.Bitmap

    def __init__(self, bm_width, bm_height, stream_data, with_alpha):
        super(GuiImage, self).__init__() # bypass GuiImage.__init__
        self._with_alpha = with_alpha
        self._stream_data = stream_data
        self._bm_height = bm_height
        self._bm_width = bm_width

    @property
    def _native_widget(self):
        if self._is_created(): return self._cached_widget
        wx_depth = (32 if self._with_alpha else 24)
        wx_fmt = (_wx.BitmapBufferFormat_RGBA if self._with_alpha
                  else _wx.BitmapBufferFormat_RGB)
        self._cached_args = (self._bm_width, self._bm_height, wx_depth)
        native = super()._native_widget
        native.CopyFromBuffer(self._stream_data, wx_fmt)
        self._stream_data = None # save some memory
        return native

    def save_bmp(self, imagePath, exten='.jpg'):
        self._native_widget.ConvertToImage()
        return self._native_widget.SaveFile(imagePath, self.img_types[exten])

class StaticBmp(GuiImage):
    """This one has a parent and a default value - we should generalize the
    latter."""
    _native_widget: _wx.StaticBitmap

    def __init__(self, parent, gui_image=None):
        super(GuiImage, self).__init__( # bypass GuiImage.__init__
            bitmap=self._resolve(gui_image or get_image('warning.32')))
        self._parent = parent

#------------------------------------------------------------------------------
class ImageList(Lazy):
    """Wrapper for wx.ImageList. Allows ImageList to be specified before
    wx.App is initialized."""
    _native_widget: _wx.ImageList

    def __init__(self, il_width, il_height):
        super().__init__()
        self.width = il_width
        self.height = il_height
        self._images = []
        self._indices = None

    @property
    def _native_widget(self):
        if self._is_created(): return self._cached_widget
        # scaling crashes if done before the wx.App is initialized
        self._cached_args = scaled(self.width), scaled(self.height)
        return super()._native_widget

    def native_init(self, *args, **kwargs):
        kwargs.setdefault('recreate', False)
        freshly_created = super().native_init(*args, **kwargs)
        ##: Accessing these like this feels wrong - maybe store the scaled size
        # somewhere and retrieve it here?
        scaled_sb_size = self._cached_args[0:2]
        if freshly_created: # ONCE! we don't support adding more images
            self._indices = {}
            for k, im in self._images:
                nat_img = self._resolve(im)
                if isinstance(nat_img, _wx.BitmapBundle):
                    nat_img = nat_img.GetBitmap(scaled_sb_size)
                self._indices[k] = self._native_widget.Add(nat_img)

    def img_dex(self, *args) -> int | None:
        """Return the index of the specified image in the native control."""
        return None if (a := args[0]) is None else self._indices[a]
