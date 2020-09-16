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
from collections import OrderedDict

from ..fallout4.default_tweaks import default_tweaks

# Add new FO4VR-specific tweaks
default_tweaks.update({
    u'VR Render Size Multiplier, 0.8 [Fallout4].ini': OrderedDict(
        [(u'VRDisplay', OrderedDict(
            [(u'fRenderTargetSizeMultiplier', u'0.8')]))]),
    u'VR Render Size Multiplier, 1.0 [Fallout4].ini': OrderedDict(
        [(u'VRDisplay', OrderedDict(
            [(u'fRenderTargetSizeMultiplier', u'1.0')]))]),
    u'VR Render Size Multiplier, 1.2 [Fallout4].ini': OrderedDict(
        [(u'VRDisplay', OrderedDict(
            [(u'fRenderTargetSizeMultiplier', u'1.2')]))]),
    u'VR Render Size Multiplier, 1.4 [Fallout4].ini': OrderedDict(
        [(u'VRDisplay', OrderedDict(
            [(u'fRenderTargetSizeMultiplier', u'1.4')]))]),
    u'VR Scale, 70 [Fallout4VrCustom].ini': OrderedDict(
        [(u'VR', OrderedDict([(u'fVrScale', u'70')]))]),
    u'VR Scale, 75 [Fallout4VrCustom].ini': OrderedDict(
        [(u'VR', OrderedDict([(u'fVrScale', u'75')]))]),
    u'VR Scale, 80 [Fallout4VrCustom].ini': OrderedDict(
        [(u'VR', OrderedDict([(u'fVrScale', u'80')]))]),
})
