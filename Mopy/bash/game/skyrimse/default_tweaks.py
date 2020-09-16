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

from ..skyrim.default_tweaks import default_tweaks

# Remove tweaks that don't apply to SSE
for t in {u'Shadows, Res512 Dist 1 [SkyrimPrefs].ini',
          u'SunShadow, Update 0.0000 [Skyrim].ini',
          u'SunShadow, Update 0.0500 [Skyrim].ini',
          u'SunShadow, Update 0.1000 [Skyrim].ini',
          u'SunShadow, Update 0.2000 [Skyrim].ini',
          u'WaterReflect, Res1024 [SkyrimPrefs].ini',
          u'WaterReflect, Res256 [SkyrimPrefs].ini',
          u'WaterReflect, Res512 ~Default[SkyrimPrefs].ini'}:
    del default_tweaks[t]

# Add new SSE-specific tweaks
default_tweaks.update({
    u'Invalidate, Allow loose files [Skyrim].ini': OrderedDict(
        [(u'Archive', OrderedDict([(u'bInvalidateOlderFiles', u'1')]))]),
    u'Invalidate, Disallow loose files ~Default [Skyrim].ini': OrderedDict(
        [(u'Archive', OrderedDict([(u'bInvalidateOlderFiles', u'0')]))]),
    u'Depth Of Field, Off [SkyrimPrefs].ini': OrderedDict(
        [(u'Imagespace', OrderedDict([(u'bDoDepthOfField', u'0')]))]),
    u'Depth Of Field, On ~Default [SkyrimPrefs].ini': OrderedDict(
        [(u'Imagespace', OrderedDict([(u'bDoDepthOfField', u'1')]))]),
    u'In Game Compass, Off [SkyrimPrefs].ini': OrderedDict(
        [(u'Interface', OrderedDict([(u'bShowCompass', u'0')]))]),
    u'In Game Compass, On ~Default [SkyrimPrefs].ini': OrderedDict(
        [(u'Interface', OrderedDict([(u'bShowCompass', u'1')]))]),
    u'In Game Crosshair, Off [SkyrimPrefs].ini': OrderedDict(
        [(u'Main', OrderedDict([(u'bCrosshairEnabled', u'0')]))]),
    u'In Game Crosshair, On ~Default [SkyrimPrefs].ini': OrderedDict(
        [(u'Main', OrderedDict([(u'bCrosshairEnabled', u'1')]))]),
    u'In Game Quest Markers, Off [SkyrimPrefs].ini': OrderedDict(
        [(u'GamePlay', OrderedDict([(u'bShowFloatingQuestMarkers', u'0')]))]),
    u'In Game Quest Markers, On ~Default [SkyrimPrefs].ini': OrderedDict(
        [(u'GamePlay', OrderedDict([(u'bShowFloatingQuestMarkers', u'1')]))]),
    u'Map Quest Markers, Off [SkyrimPrefs].ini': OrderedDict(
        [(u'GamePlay', OrderedDict([(u'bShowQuestMarkers', u'0')]))]),
    u'Map Quest Markers, On ~Default [SkyrimPrefs].ini': OrderedDict(
        [(u'GamePlay', OrderedDict([(u'bShowQuestMarkers', u'1')]))]),
    u'Tutorials, Off [Skyrim].ini': OrderedDict(
        [(u'Interface', OrderedDict([(u'bShowTutorials', u'0')]))]),
    u'Tutorials, On [Skyrim].ini': OrderedDict(
        [(u'Interface', OrderedDict([(u'bShowTutorials', u'1')]))]),
})
