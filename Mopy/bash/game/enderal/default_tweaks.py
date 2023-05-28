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
##: deduplicate with skyrim.default_tweaks
default_tweaks = {
    'Archery, ArrowTilt 0.0 [Enderal].ini': {
        'Combat': {'f1PArrowTiltUpAngle': '0.0',
                   'f3PArrowTiltUpAngle': '0.0'}},
    'Archery, ArrowTilt 0.7 [Enderal].ini': {
        'Combat': {'f1PArrowTiltUpAngle': '0.7',
                   'f3PArrowTiltUpAngle': '0.7'}},
    'Archery, NavMeshMove 12288 [Enderal].ini': {
        'Actor': {'fVisibleNavmeshMoveDist': '12288.0000'}},
    'Archery, NavMeshMove 4096 [Enderal].ini': {
        'Actor': {'fVisibleNavmeshMoveDist': '4096.0000'}},
    'Archery, NavMeshMove 8192 [Enderal].ini': {
        'Actor': {'fVisibleNavmeshMoveDist': '8192.0000'}},
    'Enderal Intro sequence, Disabled [Enderal].ini': {
        'General': {'sIntroSequence': '0'}},
    'Enderal Intro sequence, Enabled ~Default [Enderal].ini': {
        'General': {'sIntroSequence': '1'}},
    'Border Regions, Disabled [Enderal].ini': {
        'General': {'bBorderRegionsEnabled': '0'}},
    'Border Regions, Enabled [Enderal].ini': {
        'General': {'bBorderRegionsEnabled': '1'}},
    'Debug Log, Disabled [Enderal].ini': {
        'Papyrus': {'bEnableLogging': '0', 'bLoadDebugInformation': '0',
                    'bEnableTrace': '0'}},
    'Debug Log, Enabled ~Default [Enderal].ini': {
        'Papyrus': {'bEnableLogging': '1', 'bLoadDebugInformation': '1',
                    'bEnableTrace': '1'}},
    'Dialog Camera, ~Default [Enderal].ini': {
        'Controls': {'fDialogueSoftStopAngle1P': '20.0',
                     'fDialogueHardStopAngle1P': '45.0',
                     'fDialogueSoftStopAngle3P': '25.0',
                     'fDialogueHardStopAngle3P': '55.0'}},
    'Dialog Camera, Free [Enderal].ini': {
        'Controls': {'fDialogueSoftStopAngle1P': '180.0',
                     'fDialogueHardStopAngle1P': '180.0',
                     'fDialogueSoftStopAngle3P': '180.0',
                     'fDialogueHardStopAngle3P': '180.0'}},
    'Grass, Spacing 20 [Enderal].ini': {'Grass': {'iMinGrassSize': '20'}},
    'Grass, Spacing 40 [Enderal].ini': {'Grass': {'iMinGrassSize': '40'}},
    'Grass, Spacing 60 [Enderal].ini': {'Grass': {'iMinGrassSize': '60'}},
    'Grass, Spacing 80 [Enderal].ini': {'Grass': {'iMinGrassSize': '80'}},
    'Large Interiors Static Limit Fix [Enderal].ini': {
        'General': {'iLargeIntRefCount': '999999'}},
    'Large Interiors Static Limit [Enderal].ini': {
        'General': {'iLargeIntRefCount': '1000'}},
    'Particles, 100 [EnderalPrefs].ini': {'Particles': {'iMaxDesired': '100'}},
    'Particles, 150 [EnderalPrefs].ini': {'Particles': {'iMaxDesired': '150'}},
    'Particles, 250 [EnderalPrefs].ini': {'Particles': {'iMaxDesired': '250'}},
    'Particles, 350 [EnderalPrefs].ini': {'Particles': {'iMaxDesired': '350'}},
    'Particles, 450 [EnderalPrefs].ini': {'Particles': {'iMaxDesired': '450'}},
    'Particles, 550 [EnderalPrefs].ini': {'Particles': {'iMaxDesired': '550'}},
    'Particles, 650 [EnderalPrefs].ini': {'Particles': {'iMaxDesired': '650'}},
    'Particles, 750 ~Default [EnderalPrefs].ini': {
        'Particles': {'iMaxDesired': '750'}},
    'Screenshot, Disabled [Enderal].ini': {
        'Display': {'bAllowScreenShot': '0'}},
    'Screenshot, Enabled ~Default [Enderal].ini': {
        'Display': {'bAllowScreenShot': '1'}},
    'Shadows, Res512 [EnderalPrefs].ini': {
        'Display': {'iShadowMapResolution': '512'}},
    'Shadows, Res1024 [EnderalPrefs].ini': {
        'Display': {'iShadowMapResolution': '1024'}},
    'Shadows, Res2048 [EnderalPrefs].ini': {
        'Display': {'iShadowMapResolution': '2048'}},
    'Shadows, Res4096 ~Default [EnderalPrefs].ini': {
        'Display': {'iShadowMapResolution': '4096'}},
    'Vanity Camera, 120 [Enderal].ini': {
        'Camera': {'fAutoVanityModeDelay': '120.0000'}},
    'Vanity Camera, 600 [Enderal].ini': {
        'Camera': {'fAutoVanityModeDelay': '600.0000'}},
    'Vanity Camera, Disable [Enderal].ini': {
        'Camera': {'fAutoVanityModeDelay': '0'}},
    'Window Mode Top left, 20-225 [Enderal].ini': {
        'Display': {'iLocation Y': '20', 'iLocation X': '225'}},
    'Window Mode Top left, 5-5 [Enderal].ini': {
        'Display': {'iLocation Y': '5', 'iLocation X': '5'}},
    'Window Mode Top left, 5-60 [Enderal].ini': {
        'Display': {'iLocation Y': '5', 'iLocation X': '60'}},
    'Invalidate, Allow loose files ~Default [Enderal].ini': {
        'Archive': {'bInvalidateOlderFiles': '1'}},
    'Invalidate, Disallow loose files [Enderal].ini': {
        'Archive': {'bInvalidateOlderFiles': '0'}},
    'Depth Of Field, Off [EnderalPrefs].ini': {
        'Imagespace': {'bDoDepthOfField': '0'}},
    'Depth Of Field, On ~Default [EnderalPrefs].ini': {
        'Imagespace': {'bDoDepthOfField': '1'}},
    'In Game Compass, Off [EnderalPrefs].ini': {
        'Interface': {'bShowCompass': '0'}},
    'In Game Compass, On ~Default [EnderalPrefs].ini': {
        'Interface': {'bShowCompass': '1'}},
    'In Game Crosshair, Off [EnderalPrefs].ini': {
        'Main': {'bCrosshairEnabled': '0'}},
    'In Game Crosshair, On ~Default [EnderalPrefs].ini': {
        'Main': {'bCrosshairEnabled': '1'}},
    'In Game Quest Markers, Off [EnderalPrefs].ini': {
        'GamePlay': {'bShowFloatingQuestMarkers': '0'}},
    'In Game Quest Markers, On ~Default [EnderalPrefs].ini': {
        'GamePlay': {'bShowFloatingQuestMarkers': '1'}},
    'Map Quest Markers, Off [EnderalPrefs].ini': {
        'GamePlay': {'bShowQuestMarkers': '0'}},
    'Map Quest Markers, On ~Default [EnderalPrefs].ini': {
        'GamePlay': {'bShowQuestMarkers': '1'}},
    'Tutorials, Off [Enderal].ini': {'Interface': {'bShowTutorials': '0'}},
    'Tutorials, On [Enderal].ini': {'Interface': {'bShowTutorials': '1'}},
}
