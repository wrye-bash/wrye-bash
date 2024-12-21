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
from ..fallout4.default_tweaks import default_tweaks

# Add new FO4VR-specific tweaks
default_tweaks.update({
    'VR Render Size Multiplier, 0.8 [Fallout4].ini': {
        'VRDisplay': {'fRenderTargetSizeMultiplier': '0.8'}},
    'VR Render Size Multiplier, 1.0 [Fallout4].ini': {
        'VRDisplay': {'fRenderTargetSizeMultiplier': '1.0'}},
    'VR Render Size Multiplier, 1.2 [Fallout4].ini': {
        'VRDisplay': {'fRenderTargetSizeMultiplier': '1.2'}},
    'VR Render Size Multiplier, 1.4 [Fallout4].ini': {
        'VRDisplay': {'fRenderTargetSizeMultiplier': '1.4'}},
    'VR Scale, 70 [Fallout4VrCustom].ini': {'VR': {'fVrScale': '70'}},
    'VR Scale, 75 [Fallout4VrCustom].ini': {'VR': {'fVrScale': '75'}},
    'VR Scale, 80 [Fallout4VrCustom].ini': {'VR': {'fVrScale': '80'}},
})
