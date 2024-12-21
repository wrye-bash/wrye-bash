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
from ..skyrim.default_tweaks import default_tweaks

# Remove tweaks that don't apply to SSE
remove_tweaks = {'Shadows, Res512 Dist 1 [SkyrimPrefs].ini',
                 'SunShadow, Update 0.0000 [Skyrim].ini',
                 'SunShadow, Update 0.0500 [Skyrim].ini',
                 'SunShadow, Update 0.1000 [Skyrim].ini',
                 'SunShadow, Update 0.2000 [Skyrim].ini',
                 'WaterReflect, Res1024 [SkyrimPrefs].ini',
                 'WaterReflect, Res256 [SkyrimPrefs].ini',
                 'WaterReflect, Res512 ~Default[SkyrimPrefs].ini'}
default_tweaks = {k: v for k, v in default_tweaks.items()
                  if k not in remove_tweaks}

# Add new SSE-specific tweaks
add_tweaks = {
    'Invalidate, Allow loose files [Skyrim].ini': {
        'Archive': {'bInvalidateOlderFiles': '1'}},
    'Invalidate, Disallow loose files ~Default [Skyrim].ini': {
        'Archive': {'bInvalidateOlderFiles': '0'}},
    'Save Game Compression, LZ4 ~Default [Skyrim].ini': {
        'SaveGame': {'uiCompression': '2'}},
    'Save Game Compression, zlib [Skyrim].ini': {
        'SaveGame': {'uiCompression': '1'}},
    'Save Game Compression, Off [Skyrim].ini': {
        'SaveGame': {'uiCompression': '0'}},
    'Depth Of Field, Off [SkyrimPrefs].ini': {
        'Imagespace': {'bDoDepthOfField': '0'}},
    'Depth Of Field, On ~Default [SkyrimPrefs].ini': {
        'Imagespace': {'bDoDepthOfField': '1'}},
    'In Game Compass, Off [SkyrimPrefs].ini': {
        'Interface': {'bShowCompass': '0'}},
    'In Game Compass, On ~Default [SkyrimPrefs].ini': {
        'Interface': {'bShowCompass': '1'}},
    'In Game Crosshair, Off [SkyrimPrefs].ini': {
        'Main': {'bCrosshairEnabled': '0'}},
    'In Game Crosshair, On ~Default [SkyrimPrefs].ini': {
        'Main': {'bCrosshairEnabled': '1'}},
    'In Game Quest Markers, Off [SkyrimPrefs].ini': {
        'GamePlay': {'bShowFloatingQuestMarkers': '0'}},
    'In Game Quest Markers, On ~Default [SkyrimPrefs].ini': {
        'GamePlay': {'bShowFloatingQuestMarkers': '1'}},
    'Map Quest Markers, Off [SkyrimPrefs].ini': {
        'GamePlay': {'bShowQuestMarkers': '0'}},
    'Map Quest Markers, On ~Default [SkyrimPrefs].ini': {
        'GamePlay': {'bShowQuestMarkers': '1'}},
    'Tutorials, Off [Skyrim].ini': {'Interface': {'bShowTutorials': '0'}},
    'Tutorials, On [Skyrim].ini': {'Interface': {'bShowTutorials': '1'}},
}
default_tweaks.update(add_tweaks)
