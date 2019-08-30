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
from collections import OrderedDict

default_tweaks = {
    u'Archery, ArrowTilt 0.0 [Enderal].ini': OrderedDict(
        [(u'Combat', OrderedDict(
            [(u'f1PArrowTiltUpAngle', u'0.0'),
             (u'f3PArrowTiltUpAngle', u'0.0')]))]),
    u'Archery, ArrowTilt 0.7 [Enderal].ini': OrderedDict(
        [(u'Combat', OrderedDict(
            [(u'f1PArrowTiltUpAngle', u'0.7'),
             (u'f3PArrowTiltUpAngle', u'0.7')]))]),
    u'Archery, NavMeshMove 12288 [Enderal].ini': OrderedDict(
        [(u'Actor', OrderedDict(
            [(u'fVisibleNavmeshMoveDist', u'12288.0000')]))]),
    u'Archery, NavMeshMove 4096 [Enderal].ini': OrderedDict(
        [(u'Actor', OrderedDict(
            [(u'fVisibleNavmeshMoveDist', u'4096.0000')]))]),
    u'Archery, NavMeshMove 8192 [Enderal].ini': OrderedDict(
        [(u'Actor', OrderedDict(
            [(u'fVisibleNavmeshMoveDist', u'8192.0000')]))]),
    u'Enderal Intro sequence, Disabled [Enderal].ini': OrderedDict(
        [(u'General', OrderedDict([(u'sIntroSequence', u'0')]))]),
    u'Enderal Intro sequence, Enabled ~Default [Enderal].ini': OrderedDict(
        [(u'General', OrderedDict([(u'sIntroSequence', u'1')]))]),
    u'Border Regions, Disabled [Enderal].ini': OrderedDict(
        [(u'General', OrderedDict([(u'bBorderRegionsEnabled', u'0')]))]),
    u'Border Regions, Enabled [Enderal].ini': OrderedDict(
        [(u'General', OrderedDict([(u'bBorderRegionsEnabled', u'1')]))]),
    u'Debug Log, Disabled [Enderal].ini': OrderedDict(
        [(u'Papyrus', OrderedDict(
            [(u'bEnableLogging', u'0'), (u'bLoadDebugInformation', u'0'),
             (u'bEnableTrace', u'0')]))]),
    u'Debug Log, Enabled ~Default [Enderal].ini': OrderedDict(
        [(u'Papyrus', OrderedDict(
        [(u'bEnableLogging', u'1'), (u'bLoadDebugInformation', u'1'),
         (u'bEnableTrace', u'1')]))]),
    u'Grass, Spacing 20 [Enderal].ini': OrderedDict(
        [(u'Grass', OrderedDict([(u'iMinGrassSize', u'20')]))]),
    u'Grass, Spacing 40 [Enderal].ini': OrderedDict(
        [(u'Grass', OrderedDict([(u'iMinGrassSize', u'40')]))]),
    u'Grass, Spacing 60 [Enderal].ini': OrderedDict(
        [(u'Grass', OrderedDict([(u'iMinGrassSize', u'60')]))]),
    u'Grass, Spacing 80 [Enderal].ini': OrderedDict(
        [(u'Grass', OrderedDict([(u'iMinGrassSize', u'80')]))]),
    u'Large Interiors Static Limit Fix [Enderal].ini': OrderedDict(
        [(u'General', OrderedDict([(u'iLargeIntRefCount', u'999999')]))]),
    u'Large Interiors Static Limit [Enderal].ini': OrderedDict(
        [(u'General', OrderedDict([(u'iLargeIntRefCount', u'1000')]))]),
    u'Particles, 100 [EnderalPrefs.ini].ini': OrderedDict(
        [(u'Particles', OrderedDict([(u'iMaxDesired', u'100')]))]),
    u'Particles, 150 [EnderalPrefs.ini].ini': OrderedDict(
        [(u'Particles', OrderedDict([(u'iMaxDesired', u'150')]))]),
    u'Particles, 250 [EnderalPrefs.ini].ini': OrderedDict(
        [(u'Particles', OrderedDict([(u'iMaxDesired', u'250')]))]),
    u'Particles, 350 [EnderalPrefs.ini].ini': OrderedDict(
        [(u'Particles', OrderedDict([(u'iMaxDesired', u'350')]))]),
    u'Particles, 450 [EnderalPrefs.ini].ini': OrderedDict(
        [(u'Particles', OrderedDict([(u'iMaxDesired', u'450')]))]),
    u'Particles, 550 [EnderalPrefs.ini].ini': OrderedDict(
        [(u'Particles', OrderedDict([(u'iMaxDesired', u'550')]))]),
    u'Particles, 650 [EnderalPrefs.ini].ini': OrderedDict(
        [(u'Particles', OrderedDict([(u'iMaxDesired', u'650')]))]),
    u'Particles, 750 ~Default [EnderalPrefs.ini].ini': OrderedDict(
        [(u'Particles', OrderedDict([(u'iMaxDesired', u'750')]))]),
    u'Screenshot, Disabled [Enderal].ini': OrderedDict(
        [(u'Display', OrderedDict([(u'bAllowScreenShot', u'0')]))]),
    u'Screenshot, Enabled ~Default [Enderal].ini': OrderedDict(
        [(u'Display', OrderedDict([(u'bAllowScreenShot', u'1')]))]),
    u'Shadows, Res512 [EnderalPrefs.ini].ini': OrderedDict(
        [(u'Display', OrderedDict([(u'iShadowMapResolution', u'512')]))]),
    u'Shadows, Res1024 [EnderalPrefs.ini].ini': OrderedDict(
        [(u'Display', OrderedDict([(u'iShadowMapResolution', u'1024')]))]),
    u'Shadows, Res2048 [EnderalPrefs.ini].ini': OrderedDict(
        [(u'Display', OrderedDict([(u'iShadowMapResolution', u'2048')]))]),
    u'Shadows, Res4096 ~Default [EnderalPrefs.ini].ini': OrderedDict(
        [(u'Display', OrderedDict([(u'iShadowMapResolution', u'4096')]))]),
    u'Vanity Camera, 120 [Enderal].ini': OrderedDict(
        [(u'Camera', OrderedDict([(u'fAutoVanityModeDelay', u'120.0000')]))]),
    u'Vanity Camera, 600 [Enderal].ini': OrderedDict(
        [(u'Camera', OrderedDict([(u'fAutoVanityModeDelay', u'600.0000')]))]),
    u'Vanity Camera, Disable [Enderal].ini': OrderedDict(
        [(u'Camera', OrderedDict([(u'fAutoVanityModeDelay', u'0')]))]),
    u'Window Mode Top left, 20-225 [Enderal].ini': OrderedDict(
        [(u'Display', OrderedDict(
            [(u'iLocation Y', u'20'), (u'iLocation X', u'225')]))]),
    u'Window Mode Top left, 5-5 [Enderal].ini': OrderedDict(
        [(u'Display', OrderedDict(
            [(u'iLocation Y', u'5'), (u'iLocation X', u'5')]))]),
    u'Window Mode Top left, 5-60 [Enderal].ini': OrderedDict(
        [(u'Display', OrderedDict(
            [(u'iLocation Y', u'5'), (u'iLocation X', u'60')]))]),
    u'Invalidate, Allow loose files ~Default [Enderal].ini': OrderedDict(
        [(u'Archive', OrderedDict([(u'bInvalidateOlderFiles', u'1')]))]),
    u'Invalidate, Disallow loose files [Enderal].ini': OrderedDict(
        [(u'Archive', OrderedDict([(u'bInvalidateOlderFiles', u'0')]))]),
    u'Depth Of Field, Off [EnderalPrefs.ini].ini': OrderedDict(
        [(u'Imagespace', OrderedDict([(u'bDoDepthOfField', u'0')]))]),
    u'Depth Of Field, On ~Default [EnderalPrefs.ini].ini': OrderedDict(
        [(u'Imagespace', OrderedDict([(u'bDoDepthOfField', u'1')]))]),
    u'In Game Compass, Off [EnderalPrefs.ini].ini': OrderedDict(
        [(u'Interface', OrderedDict([(u'bShowCompass', u'0')]))]),
    u'In Game Compass, On ~Default [EnderalPrefs.ini].ini': OrderedDict(
        [(u'Interface', OrderedDict([(u'bShowCompass', u'1')]))]),
    u'In Game Crosshair, Off [EnderalPrefs.ini].ini': OrderedDict(
        [(u'Main', OrderedDict([(u'bCrosshairEnabled', u'0')]))]),
    u'In Game Crosshair, On ~Default [EnderalPrefs.ini].ini': OrderedDict(
        [(u'Main', OrderedDict([(u'bCrosshairEnabled', u'1')]))]),
    u'In Game Quest Markers, Off [EnderalPrefs.ini].ini': OrderedDict(
        [(u'GamePlay', OrderedDict([(u'bShowFloatingQuestMarkers', u'0')]))]),
    u'In Game Quest Markers, On ~Default [EnderalPrefs.ini].ini': OrderedDict(
        [(u'GamePlay', OrderedDict([(u'bShowFloatingQuestMarkers', u'1')]))]),
    u'Map Quest Markers, Off [EnderalPrefs.ini].ini': OrderedDict(
        [(u'GamePlay', OrderedDict([(u'bShowQuestMarkers', u'0')]))]),
    u'Map Quest Markers, On ~Default [EnderalPrefs.ini].ini': OrderedDict(
        [(u'GamePlay', OrderedDict([(u'bShowQuestMarkers', u'1')]))]),
    u'Tutorials, Off [Enderal].ini': OrderedDict(
        [(u'Interface', OrderedDict([(u'bShowTutorials', u'0')]))]),
    u'Tutorials, On [Enderal].ini': OrderedDict(
        [(u'Interface', OrderedDict([(u'bShowTutorials', u'1')]))]),
}
