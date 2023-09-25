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

"""An API for reading and writing DDS files. Pre-alpha, only useful for
reading/writing headers for existing DDS byte arrays (e.g. from a DX10 BA2).

Deviates from BSArch by trying to adhere to the official DDS specification as
closely as possible, whereas BSArch tries to create DDS files that are
byte-for-byte-identical to the ones created by Archive2.exe.

References:
https://docs.microsoft.com/en-us/windows/win32/direct3ddds/dx-graphics-dds-pguide
https://github.com/microsoft/DirectXTex
https://github.com/ModOrganizer2/modorganizer-preview_dds"""

from __future__ import annotations

__author__ = u'Infernio'

import copy
from collections import defaultdict
from struct import Struct

from ..bolt import AFile, Flags, flag, unpack_4s, unpack_int
from ..exception import DDSError
from ..wbtemp import TempFile

# Constants
_HEADER_MAGIC = b'DDS '
_HEADER_SIZE = 124
_PF_SIZE = 32

_MAGIC_DXT1 = b'DXT1'
_MAGIC_DXT2 = b'DXT2'
_MAGIC_DXT3 = b'DXT3'
_MAGIC_DXT4 = b'DXT4'
_MAGIC_DXT5 = b'DXT5'
_MAGIC_DXT10 = b'DX10'
_MAGIC_BC4_UNORM = b'BC4U'
_MAGIC_BC4_SNORM = b'BC4S'
_MAGIC_BC5_UNORM = b'BC5U'
_MAGIC_BC5_SNORM = b'BC5S'
_MAGIC_RGBG = b'RGBG'
_MAGIC_GRGB = b'GRGB'
_MAGIC_YUY2 = b'YUY2'
_MAGIC_BC6H = b'BC6H'

class _CAPS_FLAGS(Flags):
    DDSCAPS_COMPLEX: bool = flag(3)    # 0x8
    DDSCAPS_TEXTURE: bool = flag(12)   # 0x1000
    DDSCAPS_MIPMAP: bool = flag(22)    # 0x400000

class _CAPS2_FLAGS(Flags):
    DDSCAPS2_CUBEMAP: bool = flag(9)   # 0x200
    DDSCAPS2_CUBEMAP_POSITIVEX: bool    # 0x400
    DDSCAPS2_CUBEMAP_NEGATIVEX: bool    # 0x800
    DDSCAPS2_CUBEMAP_POSITIVEY: bool    # 0x1000
    DDSCAPS2_CUBEMAP_NEGATIVEY: bool    # 0x2000
    DDSCAPS2_CUBEMAP_POSITIVEZ: bool    # 0x4000
    DDSCAPS2_CUBEMAP_NEGATIVEZ: bool    # 0x8000
    DDSCAPS2_VOLUME: bool = flag(21)   # 0x200000

class _DDS_FLAGS(Flags):
    DDSD_CAPS: bool                     # 0x1
    DDSD_HEIGHT: bool                   # 0x2
    DDSD_WIDTH: bool                    # 0x4
    DDSD_PITCH: bool                    # 0x8
    DDSD_PIXELFORMAT: bool = flag(12)  # 0x1000
    DDSD_MIPMAPCOUNT: bool = flag(17)  # 0x20000
    DDSD_LINEARSIZE: bool = flag(19)   # 0x80000

class _PF_FLAGS(Flags):
    DDPF_ALPHAPIXELS: bool              # 0x1
    DDPF_ALPHA: bool                    # 0x2
    DDPF_FOURCC: bool                   # 0x4
    DDPF_RGB: bool = flag(6)           # 0x40
    DDPF_YUV: bool = flag(9)           # 0x200
    DDPF_LUMINANCE: bool = flag(17)    # 0x20000

# PY3: These are redundant, see above - IntFlag would help
_DDPF_ALPHAPIXELS = _PF_FLAGS(0x1)
_DDPF_FOURCC = _PF_FLAGS(0x4)
_DDPF_RGB = _PF_FLAGS(0x40)
_DDPF_LUMINANCE = _PF_FLAGS(0x20000)

# Implementation
# https://docs.microsoft.com/en-us/windows/win32/direct3ddds/dds-pixelformat
class _DDSPixelFormat(object):
    """Implements a pixel format. See the _mk_* methods and the _DDSPF_*
    constants below."""
    __slots__ = (u'pf_size', u'pf_flags', u'pf_four_cc', u'pf_rgb_bit_count',
                 u'pf_r_bit_mask', u'pf_g_bit_mask', u'pf_b_bit_mask',
                 u'pf_a_bit_mask')
    _dump_pf = Struct(u'=2I4s5I').pack

    def __init__(self):
        """Initializes every field in the format to its default value."""
        for attr in _DDSPixelFormat.__slots__:
            setattr(self, attr, 0)
        self.pf_size = _PF_SIZE
        self.pf_four_cc = b''
        self.pf_flags = _PF_FLAGS(self.pf_flags)

    @property
    def needs_dxt10(self):
        """Checks if this pixel format needs a DXT10 header to be present."""
        return self.pf_flags.DDPF_FOURCC and self.pf_four_cc == _MAGIC_DXT10

    def load_format(self, ins):
        """Loads this format from the specified stream."""
        self.pf_size = unpack_int(ins)
        if self.pf_size != _PF_SIZE:
            raise DDSError(u'Invalid pixel format size: Expected %u, but got '
                           u'%u' % (_PF_SIZE, self.pf_size))
        self.pf_flags = _PF_FLAGS(unpack_int(ins))
        self.pf_four_cc = unpack_4s(ins)
        self.pf_rgb_bit_count = unpack_int(ins)
        self.pf_r_bit_mask = unpack_int(ins)
        self.pf_g_bit_mask = unpack_int(ins)
        self.pf_b_bit_mask = unpack_int(ins)
        self.pf_a_bit_mask = unpack_int(ins)

    def dump_format(self):
        """Dumps this format to a bytestring and returns the result."""
        return self._dump_pf(
            _PF_SIZE, self.pf_flags, self.pf_four_cc, self.pf_rgb_bit_count,
            self.pf_r_bit_mask, self.pf_g_bit_mask, self.pf_b_bit_mask,
            self.pf_a_bit_mask)

# Utility methods for building pixel formats
def _new_pf(**pf_props):
    """Builds a pixel format with the specified non-default properties."""
    ret = _DDSPixelFormat()
    for prop_name, prop_val in pf_props.items():
        setattr(ret, prop_name, prop_val)
    return ret

def _mk_fourcc(four_cc_magic):
    """Shorthand for fourcc formats."""
    return _new_pf(pf_flags=_DDPF_FOURCC, pf_four_cc=four_cc_magic)

def _mk_rgba(bpp, r_mask, g_mask, b_mask, a_mask):
    """Shorthand for RGBA formats."""
    return _new_pf(pf_flags=_DDPF_RGB | _DDPF_ALPHAPIXELS,
                   pf_rgb_bit_count=bpp, pf_r_bit_mask=r_mask,
                   pf_g_bit_mask=g_mask, pf_b_bit_mask=b_mask,
                   pf_a_bit_mask=a_mask)

def _mk_rgb(bpp, r_mask, g_mask, b_mask):
    """Shorthand for RGB formats."""
    return _new_pf(pf_flags=_DDPF_RGB, pf_rgb_bit_count=bpp,
                   pf_r_bit_mask=r_mask, pf_g_bit_mask=g_mask,
                   pf_b_bit_mask=b_mask)

def _mk_luminance(bpp, l_mask):
    """Shorthand for luminance formats."""
    return _new_pf(pf_flags=_DDPF_LUMINANCE, pf_rgb_bit_count=bpp,
                   pf_r_bit_mask=l_mask)

def _mk_luminance_a(bpp, l_mask, a_mask):
    """Shorthand for luminance + alpha formats."""
    return _new_pf(pf_flags=_DDPF_LUMINANCE | _DDPF_ALPHAPIXELS,
                   pf_rgb_bit_count=bpp, pf_r_bit_mask=l_mask,
                   pf_a_bit_mask=a_mask)

# Pixel format definitions begin here
# cf. https://github.com/microsoft/DirectXTex/blob/master/DirectXTex/DDS.h
_DDSPF_DXT1 = _mk_fourcc(_MAGIC_DXT1)
_DDSPF_DXT2 = _mk_fourcc(_MAGIC_DXT2)
_DDSPF_DXT3 = _mk_fourcc(_MAGIC_DXT3)
_DDSPF_DXT4 = _mk_fourcc(_MAGIC_DXT4)
_DDSPF_DXT5 = _mk_fourcc(_MAGIC_DXT5)
_DDSPF_DXT10 = _mk_fourcc(_MAGIC_DXT10)
_DDSPF_BC4_UNORM = _mk_fourcc(_MAGIC_BC4_UNORM)
_DDSPF_BC4_SNORM = _mk_fourcc(_MAGIC_BC4_SNORM)
_DDSPF_BC5_UNORM = _mk_fourcc(_MAGIC_BC5_UNORM)
_DDSPF_BC5_SNORM = _mk_fourcc(_MAGIC_BC5_SNORM)
_DDSPF_R8G8_B8G8 = _mk_fourcc(_MAGIC_RGBG)
_DDSPF_G8R8_G8B8 = _mk_fourcc(_MAGIC_GRGB)
_DDSPF_YUY2 = _mk_fourcc(_MAGIC_YUY2)
_DDSPF_A8R8G8B8 = _mk_rgba(32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
_DDSPF_X8R8G8B8 = _mk_rgb(32, 0x00FF0000, 0x0000FF00, 0x000000FF)
_DDSPF_A8B8G8R8 = _mk_rgba(32, 0x000000FF, 0x0000FF00, 0x00FF0000, 0xFF000000)
_DDSPF_X8B8G8R8 = _mk_rgb(32, 0x000000FF, 0x0000FF00, 0x00FF0000)
_DDSPF_G16R16 = _mk_rgb(32, 0x0000FFFF, 0xFFFF0000, 0x00000000)
_DDSPF_R5G6B5 = _mk_rgb(16, 0xF800, 0x07E0, 0x001F)
_DDSPF_A1R5G5B5 = _mk_rgba(16, 0x7C00, 0x03E0, 0x001F, 0x8000)
_DDSPF_A4R4G4B4 = _mk_rgba(16, 0x0F00, 0x00F0, 0x000F, 0xF000)
_DDSPF_R8G8B8 = _mk_rgb(24, 0xFF0000, 0x00FF00, 0x0000FF)
_DDSPF_L8 = _mk_luminance(8, 0xFF)
_DDSPF_L16 = _mk_luminance(16, 0xFFFF)
_DDSPF_A8L8 = _mk_luminance_a(16, 0x00FF, 0xFF00)
_DDSPF_A8L8_ALT = _mk_luminance_a(8, 0x00FF, 0xFF00)
_DDSPF_A8 = _new_pf(pf_flags=_DDPF_ALPHAPIXELS, pf_rgb_bit_count=8,
                    pf_a_bit_mask=0xFF)

# https://docs.microsoft.com/en-us/windows/win32/api/dxgiformat/ne-dxgiformat-dxgi_format
class _DXGIFormat(object): # PY3: enums sorely missed...
    """Implements a DXGI format. Exposed publicly because bsa_files needs it
    when extracting DDS files."""
    __slots__ = (u'_fmt_index', u'_fmt_name', u'_fmt_ddspf', u'_fmt_bpp',
                 u'_fmt_compressed')
    _curr_index = 0
    index_to_fmt = {}

    def __init__(self, fmt_name: str, fmt_ddspf: _DDSPixelFormat | None = None,
            *, fmt_bpp=0, fmt_compressed=False):
        """Create a new _DXGIFormat with the specified name and optional
        properties. Automatically acquires a slot in the index-to-format
        mapping.

        :param fmt_name: The standardized name of this format.
        :param fmt_ddspf: The pixel format to use with this DXGI format.
        :param fmt_bpp: The bits per pixel.
        :param fmt_compressed: True if this format is compressed."""
        self._fmt_index = _DXGIFormat._curr_index
        self._fmt_name = fmt_name
        self._fmt_ddspf = fmt_ddspf
        self._fmt_bpp = fmt_bpp
        self._fmt_compressed = fmt_compressed
        _DXGIFormat.index_to_fmt[_DXGIFormat._curr_index] = self
        _DXGIFormat._curr_index += 1

    @property
    def fmt_index(self):
        """Returns the index of this DXGI format, for writing to a DDS file."""
        return self._fmt_index

    def setup_file(self, dds_file: DDSFile, use_legacy_formats=False):
        """Sets up the specified DDS file to work with this DXGI format.

        :param use_legacy_formats: If set to True, use non-DXT10 legacy formats
            that are equivalent instead."""
        target_pf = (self._fmt_ddspf
                     if use_legacy_formats and self._fmt_ddspf else
                     _DDSPF_DXT10)
        dds_file.dds_header.ddspf = copy.copy(target_pf)
        row_pitch, slice_pitch = _compute_pitch[self._fmt_name](
            self._fmt_bpp, dds_file.dds_header.dw_width,
            dds_file.dds_header.dw_height)
        if self._fmt_compressed:
            dds_file.dds_header.dw_flags.DDSD_PITCH = False
            dds_file.dds_header.dw_flags.DDSD_LINEARSIZE = True
            dds_file.dds_header.dw_pitch_or_linear_size = slice_pitch
        else:
            dds_file.dds_header.dw_flags.DDSD_PITCH = True
            dds_file.dds_header.dw_flags.DDSD_LINEARSIZE = False
            dds_file.dds_header.dw_pitch_or_linear_size = row_pitch
        if target_pf.needs_dxt10:
            dds_file.dds_dxt10.dxgi_format = copy.copy(self)

    def __repr__(self):
        return u'%s (%u)' % (self._fmt_name, self._fmt_index)

# DXGI format definitions begin here
# cf. https://docs.microsoft.com/en-us/windows/win32/api/dxgiformat/ne-dxgiformat-dxgi_format
# and https://github.com/microsoft/DirectXTex/blob/master/DirectXTex/DirectXTexDDS.cpp
# and https://github.com/microsoft/DirectXTex/blob/master/DirectXTex/DirectXTexUtil.cpp
##: Mirror the bi-map set up in the link above, i.e. support converting from
# legacy to DXGI format as well
_DXGIFormat(u'DXGI_FORMAT_UNKNOWN')
_DXGIFormat(u'DXGI_FORMAT_R32G32B32A32_TYPELESS', fmt_bpp=128)
_DXGIFormat(u'DXGI_FORMAT_R32G32B32A32_FLOAT', fmt_bpp=128)
_DXGIFormat(u'DXGI_FORMAT_R32G32B32A32_UINT', fmt_bpp=128)
_DXGIFormat(u'DXGI_FORMAT_R32G32B32A32_SINT', fmt_bpp=128)
_DXGIFormat(u'DXGI_FORMAT_R32G32B32_TYPELESS', fmt_bpp=96)
_DXGIFormat(u'DXGI_FORMAT_R32G32B32_FLOAT', fmt_bpp=96)
_DXGIFormat(u'DXGI_FORMAT_R32G32B32_UINT', fmt_bpp=96)
_DXGIFormat(u'DXGI_FORMAT_R32G32B32_SINT', fmt_bpp=96)
_DXGIFormat(u'DXGI_FORMAT_R16G16B16A16_TYPELESS', fmt_bpp=64)
_DXGIFormat(u'DXGI_FORMAT_R16G16B16A16_FLOAT', fmt_bpp=64)
_DXGIFormat(u'DXGI_FORMAT_R16G16B16A16_UNORM', fmt_bpp=64)
_DXGIFormat(u'DXGI_FORMAT_R16G16B16A16_UINT', fmt_bpp=64)
_DXGIFormat(u'DXGI_FORMAT_R16G16B16A16_SNORM', fmt_bpp=64)
_DXGIFormat(u'DXGI_FORMAT_R16G16B16A16_SINT', fmt_bpp=64)
_DXGIFormat(u'DXGI_FORMAT_R32G32_TYPELESS', fmt_bpp=64)
_DXGIFormat(u'DXGI_FORMAT_R32G32_FLOAT', fmt_bpp=64)
_DXGIFormat(u'DXGI_FORMAT_R32G32_UINT', fmt_bpp=64)
_DXGIFormat(u'DXGI_FORMAT_R32G32_SINT', fmt_bpp=64)
_DXGIFormat(u'DXGI_FORMAT_R32G8X24_TYPELESS', fmt_bpp=64)
_DXGIFormat(u'DXGI_FORMAT_D32_FLOAT_S8X24_UINT', fmt_bpp=64)
_DXGIFormat(u'DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS', fmt_bpp=64)
_DXGIFormat(u'DXGI_FORMAT_X32_TYPELESS_G8X24_UINT', fmt_bpp=64)
_DXGIFormat(u'DXGI_FORMAT_R10G10B10A2_TYPELESS', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R10G10B10A2_UNORM', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R10G10B10A2_UINT', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R11G11B10_FLOAT', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R8G8B8A8_TYPELESS', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R8G8B8A8_UNORM', _DDSPF_A8B8G8R8, fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R8G8B8A8_UNORM_SRGB', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R8G8B8A8_UINT', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R8G8B8A8_SNORM', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R8G8B8A8_SINT', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R16G16_TYPELESS', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R16G16_FLOAT', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R16G16_UNORM', _DDSPF_G16R16, fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R16G16_UINT', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R16G16_SNORM', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R16G16_SINT', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R32_TYPELESS', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_D32_FLOAT', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R32_FLOAT', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R32_UINT', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R32_SINT', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R24G8_TYPELESS', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_D24_UNORM_S8_UINT', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R24_UNORM_X8_TYPELESS', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_X24_TYPELESS_G8_UINT', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R8G8_TYPELESS', fmt_bpp=16)
_DXGIFormat(u'DXGI_FORMAT_R8G8_UNORM', _DDSPF_A8L8, fmt_bpp=16)
_DXGIFormat(u'DXGI_FORMAT_R8G8_UINT', fmt_bpp=16)
_DXGIFormat(u'DXGI_FORMAT_R8G8_SNORM', fmt_bpp=16)
_DXGIFormat(u'DXGI_FORMAT_R8G8_SINT', fmt_bpp=16)
_DXGIFormat(u'DXGI_FORMAT_R16_TYPELESS', fmt_bpp=16)
_DXGIFormat(u'DXGI_FORMAT_R16_FLOAT', fmt_bpp=16)
_DXGIFormat(u'DXGI_FORMAT_D16_UNORM', fmt_bpp=16)
_DXGIFormat(u'DXGI_FORMAT_R16_UNORM', _DDSPF_L16, fmt_bpp=16)
_DXGIFormat(u'DXGI_FORMAT_R16_UINT', fmt_bpp=16)
_DXGIFormat(u'DXGI_FORMAT_R16_SNORM', fmt_bpp=16)
_DXGIFormat(u'DXGI_FORMAT_R16_SINT', fmt_bpp=16)
_DXGIFormat(u'DXGI_FORMAT_R8_TYPELESS', fmt_bpp=8)
_DXGIFormat(u'DXGI_FORMAT_R8_UNORM', _DDSPF_L8, fmt_bpp=8)
_DXGIFormat(u'DXGI_FORMAT_R8_UINT', fmt_bpp=8)
_DXGIFormat(u'DXGI_FORMAT_R8_SNORM', fmt_bpp=8)
_DXGIFormat(u'DXGI_FORMAT_R8_SINT', fmt_bpp=8)
_DXGIFormat(u'DXGI_FORMAT_A8_UNORM', _DDSPF_A8, fmt_bpp=8)
_DXGIFormat(u'DXGI_FORMAT_R1_UNORM', fmt_bpp=1)
_DXGIFormat(u'DXGI_FORMAT_R9G9B9E5_SHAREDEXP', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R8G8_B8G8_UNORM', _DDSPF_R8G8_B8G8, fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_G8R8_G8B8_UNORM', _DDSPF_G8R8_G8B8, fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_BC1_TYPELESS', fmt_bpp=4, fmt_compressed=True)
_DXGIFormat(u'DXGI_FORMAT_BC1_UNORM', _DDSPF_DXT1, fmt_bpp=4,
            fmt_compressed=True)
_DXGIFormat(u'DXGI_FORMAT_BC1_UNORM_SRGB', fmt_bpp=4, fmt_compressed=True)
_DXGIFormat(u'DXGI_FORMAT_BC2_TYPELESS', fmt_bpp=8, fmt_compressed=True)
_DXGIFormat(u'DXGI_FORMAT_BC2_UNORM', _DDSPF_DXT3, fmt_bpp=8,
            fmt_compressed=True)
_DXGIFormat(u'DXGI_FORMAT_BC2_UNORM_SRGB', fmt_bpp=8, fmt_compressed=True)
_DXGIFormat(u'DXGI_FORMAT_BC3_TYPELESS', fmt_bpp=8, fmt_compressed=True)
_DXGIFormat(u'DXGI_FORMAT_BC3_UNORM', _DDSPF_DXT5, fmt_bpp=8,
            fmt_compressed=True)
_DXGIFormat(u'DXGI_FORMAT_BC3_UNORM_SRGB', fmt_bpp=8, fmt_compressed=True)
_DXGIFormat(u'DXGI_FORMAT_BC4_TYPELESS', fmt_bpp=4, fmt_compressed=True)
_DXGIFormat(u'DXGI_FORMAT_BC4_UNORM', _DDSPF_BC4_UNORM, fmt_bpp=4,
            fmt_compressed=True)
_DXGIFormat(u'DXGI_FORMAT_BC4_SNORM', _DDSPF_BC4_SNORM, fmt_bpp=4,
            fmt_compressed=True)
_DXGIFormat(u'DXGI_FORMAT_BC5_TYPELESS', fmt_bpp=8, fmt_compressed=True)
_DXGIFormat(u'DXGI_FORMAT_BC5_UNORM', _DDSPF_BC5_UNORM, fmt_bpp=8,
            fmt_compressed=True)
_DXGIFormat(u'DXGI_FORMAT_BC5_SNORM', _DDSPF_BC5_SNORM, fmt_bpp=8,
            fmt_compressed=True)
_DXGIFormat(u'DXGI_FORMAT_B5G6R5_UNORM', _DDSPF_R5G6B5, fmt_bpp=16)
_DXGIFormat(u'DXGI_FORMAT_B5G5R5A1_UNORM', _DDSPF_A1R5G5B5, fmt_bpp=16)
_DXGIFormat(u'DXGI_FORMAT_B8G8R8A8_UNORM', _DDSPF_A8R8G8B8, fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_B8G8R8X8_UNORM', _DDSPF_X8R8G8B8, fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_R10G10B10_XR_BIAS_A2_UNORM', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_B8G8R8A8_TYPELESS', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_B8G8R8A8_UNORM_SRGB', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_B8G8R8X8_TYPELESS', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_B8G8R8X8_UNORM_SRGB', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_BC6H_TYPELESS', fmt_bpp=8, fmt_compressed=True)
_DXGIFormat(u'DXGI_FORMAT_BC6H_UF16', fmt_bpp=8, fmt_compressed=True)
_DXGIFormat(u'DXGI_FORMAT_BC6H_SF16', fmt_bpp=8, fmt_compressed=True)
_DXGIFormat(u'DXGI_FORMAT_BC7_TYPELESS', fmt_bpp=8, fmt_compressed=True)
_DXGIFormat(u'DXGI_FORMAT_BC7_UNORM', fmt_bpp=8, fmt_compressed=True)
_DXGIFormat(u'DXGI_FORMAT_BC7_UNORM_SRGB', fmt_bpp=8, fmt_compressed=True)
_DXGIFormat(u'DXGI_FORMAT_AYUV', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_Y410', fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_Y416', fmt_bpp=64)
_DXGIFormat(u'DXGI_FORMAT_NV12', fmt_bpp=12)
_DXGIFormat(u'DXGI_FORMAT_P010', fmt_bpp=24)
_DXGIFormat(u'DXGI_FORMAT_P016', fmt_bpp=24)
_DXGIFormat(u'DXGI_FORMAT_420_OPAQUE', fmt_bpp=12)
_DXGIFormat(u'DXGI_FORMAT_YUY2', _DDSPF_YUY2, fmt_bpp=32)
_DXGIFormat(u'DXGI_FORMAT_Y210', fmt_bpp=64)
_DXGIFormat(u'DXGI_FORMAT_Y216', fmt_bpp=64)
_DXGIFormat(u'DXGI_FORMAT_NV11', fmt_bpp=12)
_DXGIFormat(u'DXGI_FORMAT_AI44', fmt_bpp=8)
_DXGIFormat(u'DXGI_FORMAT_IA44', fmt_bpp=8)
_DXGIFormat(u'DXGI_FORMAT_P8', fmt_bpp=8)
_DXGIFormat(u'DXGI_FORMAT_A8P8', fmt_bpp=16)
_DXGIFormat(u'DXGI_FORMAT_B4G4R4A4_UNORM', _DDSPF_A4R4G4B4, fmt_bpp=16)
_DXGIFormat._curr_index = 130 # The enum counter skips here
_DXGIFormat(u'DXGI_FORMAT_P208', fmt_bpp=16)
_DXGIFormat(u'DXGI_FORMAT_V208', fmt_bpp=16)
_DXGIFormat(u'DXGI_FORMAT_V408', fmt_bpp=24)

# Pitch calculations
# https://docs.microsoft.com/en-us/windows/win32/direct3ddds/dx-graphics-dds-pguide
# https://github.com/microsoft/DirectXTex/blob/master/DirectXTex/DirectXTexUtil.cpp
def _compute_block(block_size):
    """Returns a function that computes row/slice pitch for block-compressed
    formats with the specified block size."""
    def _compute_block_dyn(_bpp, width, height):
        nbw = max(1, (width + 3) // 4)
        nbh = max(1, (height + 3) // 4)
        return nbw * block_size, nbw * nbh * block_size
    return _compute_block_dyn
_compute_block_8 = _compute_block(8)
_compute_block_16 = _compute_block(16)

def _compute_complex(to_multiply, extra_height_func=None, to_add=1,
                     to_shift=1):
    """Returns a function that computes row/slice pitch for various formats,
    with several parameters to tune for the variations."""
    def _compute_shift_dyn(_bpp, width, height):
        pitch = ((width + to_add) >> to_shift) * to_multiply
        extra_height = extra_height_func(height) if extra_height_func else 0
        return pitch, pitch * (height + extra_height)
    return _compute_shift_dyn
_compute_packed_4 = _compute_complex(4)
_compute_packed_8 = _compute_complex(8)
_compute_planar_v1 = _compute_complex(2, lambda height: (height + 1) >> 1)
_compute_planar_v2 = _compute_complex(4, lambda height: (height + 1) >> 1)
_compute_nv11 = _compute_complex(4, lambda height: height, 3, 2)
_compute_p208 = _compute_complex(2, lambda height: height)

def _compute_v208(width, height):
    """V208-specific row/slice pitch computation function."""
    return width, width * (height + (((height + 1) >> 1) * 2))

def _compute_v408(width, height):
    """V408-specific row/slice pitch computation function."""
    return width, width * (height + ((height >> 1) * 4))

def _compute_default(bpp, width, height):
    """The function used to compute row/slice pitch for all other formats."""
    pitch = (width * bpp + 7) // 8
    return pitch, pitch * height

# Maps each DXGI format to a function that computes the image row pitch in
# bytes, and the slice pitch (size in bytes of the image)
_compute_pitch = defaultdict(lambda: _compute_default, {
    # Block-compressed formats, block size 8
    u'DXGI_FORMAT_BC1_TYPELESS': _compute_block_8,
    u'DXGI_FORMAT_BC1_UNORM': _compute_block_8,
    u'DXGI_FORMAT_BC1_UNORM_SRGB': _compute_block_8,
    u'DXGI_FORMAT_BC4_TYPELESS': _compute_block_8,
    u'DXGI_FORMAT_BC4_UNORM': _compute_block_8,
    u'DXGI_FORMAT_BC4_UNORM_SRGB': _compute_block_8,
    # Block-compressed formats, block size 16
    u'DXGI_FORMAT_BC2_TYPELESS': _compute_block_16,
    u'DXGI_FORMAT_BC2_UNORM': _compute_block_16,
    u'DXGI_FORMAT_BC2_UNORM_SRGB': _compute_block_16,
    u'DXGI_FORMAT_BC3_TYPELESS': _compute_block_16,
    u'DXGI_FORMAT_BC3_UNORM': _compute_block_16,
    u'DXGI_FORMAT_BC3_UNORM_SRGB': _compute_block_16,
    u'DXGI_FORMAT_BC5_TYPELESS': _compute_block_16,
    u'DXGI_FORMAT_BC5_UNORM': _compute_block_16,
    u'DXGI_FORMAT_BC5_SNORM': _compute_block_16,
    u'DXGI_FORMAT_BC6H_TYPELESS': _compute_block_16,
    u'DXGI_FORMAT_BC6H_UF16': _compute_block_16,
    u'DXGI_FORMAT_BC6H_SF16': _compute_block_16,
    u'DXGI_FORMAT_BC7_TYPELESS': _compute_block_16,
    u'DXGI_FORMAT_BC7_UNORM': _compute_block_16,
    u'DXGI_FORMAT_BC7_UNORM_SRGB': _compute_block_16,
    # Packed formats
    u'DXGI_FORMAT_R8G8_B8G8_UNORM': _compute_packed_4,
    u'DXGI_FORMAT_G8R8_G8B8_UNORM': _compute_packed_4,
    u'DXGI_FORMAT_YUY2': _compute_packed_4,
    u'DXGI_FORMAT_Y210': _compute_packed_8,
    u'DXGI_FORMAT_Y216': _compute_packed_8,
    # Planar formats
    u'DXGI_FORMAT_NV12': _compute_planar_v1,
    u'DXGI_FORMAT_420_OPAQUE': _compute_planar_v1,
    u'DXGI_FORMAT_P010': _compute_planar_v2,
    u'DXGI_FORMAT_P016': _compute_planar_v2,
    u'DXGI_FORMAT_NV11': _compute_nv11,
    u'DXGI_FORMAT_P208': _compute_p208,
    u'DXGI_FORMAT_V208': _compute_v208,
    u'DXGI_FORMAT_V408': _compute_v408,
})

# https://docs.microsoft.com/en-us/windows/win32/direct3ddds/dds-header
class _DDSHeader(object):
    """A DDS header, contains a pixel format."""
    __slots__ = (u'dds_magic', u'dw_size', u'dw_flags', u'dw_height',
                 u'dw_width', u'dw_pitch_or_linear_size', u'dw_depth',
                 u'dw_mip_map_count', u'dw_reserved1', u'ddspf', u'dw_caps',
                 u'dw_caps2', u'dw_caps3', u'dw_caps4', u'dw_reserved2')
    _dump_pt1 = Struct(u'=4s18I').pack
    _dump_pt2 = Struct(u'=5I').pack

    def __init__(self):
        """Initializes every field in the header to its default value."""
        # Start by setting everything to 0
        for attr in _DDSHeader.__slots__:
            setattr(self, attr, 0)
        # Then set any nonzero defaults
        self.dds_magic = _HEADER_MAGIC
        self.dw_size = _HEADER_SIZE
        self.dw_reserved1 = [0] * 11
        self.ddspf = _DDSPixelFormat()
        self._set_flags()

    def _set_flags(self):
        """Sets all appropriate flags. Includes forcibly setting required
        flags, since MS's docs warn that some writers may not set them."""
        self.dw_flags = _DDS_FLAGS(self.dw_flags)
        self.dw_caps = _CAPS_FLAGS(self.dw_caps)
        self.dw_caps2 = _CAPS2_FLAGS(self.dw_caps2)
        self.dw_flags.DDSD_CAPS = True
        self.dw_flags.DDSD_HEIGHT = True
        self.dw_flags.DDSD_WIDTH = True
        self.dw_flags.DDSD_PIXELFORMAT = True
        self.dw_flags.DDSD_MIPMAPCOUNT = self.dw_mip_map_count > 0
        if self.dw_mip_map_count > 1: ##: Implement other conditions for this
            self.dw_caps.DDSCAPS_COMPLEX = True
        self.dw_caps.DDSCAPS_TEXTURE = True
        self.dw_caps.DDSCAPS_MIPMAP = self.dw_mip_map_count > 1
        ##: Expand to set all appropriate flags

    def load_header(self, ins):
        """Loads this header from the specified stream."""
        self.dds_magic = unpack_4s(ins)
        if self.dds_magic != _HEADER_MAGIC:
            raise DDSError(u'Invalid magic: Expected %s, but got %s' % (
                _HEADER_MAGIC, self.dds_magic))
        self.dw_size = unpack_int(ins)
        if self.dw_size != _HEADER_SIZE:
            raise DDSError(u'Invaild header size: Expected %u, but got %u' % (
                _HEADER_SIZE, self.dw_size))
        self.dw_flags = unpack_int(ins)
        self.dw_height = unpack_int(ins)
        self.dw_width = unpack_int(ins)
        self.dw_pitch_or_linear_size = unpack_int(ins)
        self.dw_depth = unpack_int(ins)
        self.dw_mip_map_count = unpack_int(ins)
        for x in range(len(self.dw_reserved1)):
            self.dw_reserved1[x] = unpack_int(ins)
        self.ddspf.load_format(ins)
        self.dw_caps = unpack_int(ins)
        self.dw_caps2 = unpack_int(ins)
        self.dw_caps3 = unpack_int(ins)
        self.dw_caps4 = unpack_int(ins)
        self.dw_reserved2 = unpack_int(ins)
        self._set_flags()

    def dump_header(self):
        """Dumps this header to a bytestring and returns the result."""
        self._set_flags()
        out_data = self._dump_pt1(
            _HEADER_MAGIC, _HEADER_SIZE, self.dw_flags, self.dw_height,
            self.dw_width, self.dw_pitch_or_linear_size, self.dw_depth,
            self.dw_mip_map_count, *self.dw_reserved1)
        out_data += self.ddspf.dump_format()
        return out_data + self._dump_pt2(
            self.dw_caps, self.dw_caps2, self.dw_caps3, self.dw_caps4,
            self.dw_reserved2)

# https://docs.microsoft.com/en-us/windows/win32/direct3ddds/dds-header-dxt10
class _DDSHeaderDXT10(object):
    """A DDS DXT10 header, contains a pixel format."""
    __slots__ = (u'dxgi_format', u'resource_dimension', u'misc_flag',
                 u'array_size', u'misc_flags2')
    _dump_dxt10 = Struct(u'=5I').pack

    def __init__(self):
        """Initializes every field in the header to its default value."""
        for attr in _DDSHeaderDXT10.__slots__:
            setattr(self, attr, 0)

    def load_header(self, ins):
        """Loads this header from the specified stream."""
        self.dxgi_format = mk_dxgi_fmt(unpack_int(ins))
        self.resource_dimension = unpack_int(ins)
        self.misc_flag = unpack_int(ins)
        self.array_size = unpack_int(ins)
        self.misc_flags2 = unpack_int(ins)

    def dump_header(self):
        """Dumps this header to a bytestring and returns the result."""
        return self._dump_dxt10(
            self.dxgi_format.fmt_index, self.resource_dimension,
            self.misc_flag, self.array_size, self.misc_flags2)

# API
class DDSFile(AFile):
    """A DDS file, currently just reads the DDS and DX10 headers, if
    present, then reads and stores the rest of the stream."""
    __slots__ = (u'dds_header', u'dds_dxt10', u'dds_contents')
    def load_file(self):
        """Load the entire DDS file from the file that this DDSFile instance
        was created with."""
        with self.abs_path.open(u'rb') as ins:
            self.load_from_stream(ins)

    def load_from_stream(self, ins):
        """Load the entire DDS file from the specified stream."""
        self.dds_header.load_header(ins)
        # Check if a DXT10 header is going to be present
        if self.dds_header.ddspf.needs_dxt10:
            self.dds_dxt10.load_header(ins)
        # Read and store the rest of the stream
        self.dds_contents = ins.read()

    def dump_file(self):
        """Dumps this DDS file to a bytestring and returns the result."""
        out_data = self.dds_header.dump_header()
        # Check if we should dump a DXT10 header
        if self.dds_header.ddspf.needs_dxt10:
            out_data += self.dds_dxt10.dump_header()
        return out_data + self.dds_contents

    def write_file(self, out_path=None):
        """Writes this DDS file to the specified path. If out_path is None,
        this file's own path will be used."""
        out_path = out_path or self.abs_path
        with open(out_path, 'wb') as out:
            out.write(self.dump_file())

    def write_file_safe(self, out_path=None):
        """Writes this DDS file to the specified path, utilizing a temporary
        file in-between in case something goes wrong while dumping. If out_path
        is None, this file's own path will be used."""
        out_path = out_path or self.abs_path
        with TempFile() as tmp_path:
            self.write_file(tmp_path)
            out_path.replace_with_temp(tmp_path)

    def _reset_cache(self, stat_tuple, **kwargs):
        super()._reset_cache(stat_tuple, **kwargs)
        self.dds_header = _DDSHeader()
        self.dds_dxt10 = _DDSHeaderDXT10()
        self.dds_contents = b''

def mk_dxgi_fmt(fmt_index):
    """Returns a matching DXGI format instance for the specified DXGI index."""
    try:
        return _DXGIFormat.index_to_fmt[fmt_index]
    except KeyError:
        raise DDSError(u'Unknown DXGI format with index %u' % fmt_index)
