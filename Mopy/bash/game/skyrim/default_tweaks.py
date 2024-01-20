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
default_tweaks = {
    'Archery, ArrowTilt 0.0 ~Default [Skyrim].ini': {
        'Combat': {'f1PArrowTiltUpAngle': '0.0',
                   'f3PArrowTiltUpAngle': '0.0'}},
    'Archery, ArrowTilt 0.7 [Skyrim].ini': {
        'Combat': {'f1PArrowTiltUpAngle': '0.7',
                   'f3PArrowTiltUpAngle': '0.7'}},
    'Archery, NavMeshMove 12288 [Skyrim].ini': {
        'Actor': {'fVisibleNavmeshMoveDist': '12288.0000'}},
    'Archery, NavMeshMove 4096 ~Default [Skyrim].ini': {
        'Actor': {'fVisibleNavmeshMoveDist': '4096.0000'}},
    'Archery, NavMeshMove 8192 [Skyrim].ini': {
        'Actor': {'fVisibleNavmeshMoveDist': '8192.0000'}},
    'Blood and Gore, Enabled ~Default [Skyrim.ini]': {
        'General': {'bDisableAllGore': '0'}},
    'Blood and Gore, Disabled [Skyrim.ini]': {
        'General': {'bDisableAllGore': '1'}},
    'BGS Intro sequence, Disabled [Skyrim].ini': {
        'General': {'sIntroSequence': ''}},
    'BGS Intro sequence, Enabled ~Default [Skyrim].ini': {
        'General': {'sIntroSequence': 'BGS_LOGO.BIK'}},
    'Border Regions, Disabled [Skyrim].ini': {
        'General': {'bBorderRegionsEnabled': '0'}},
    'Border Regions, Enabled ~Default [Skyrim].ini': {
        'General': {'bBorderRegionsEnabled': '1'}},
    'Debug Log, Disabled [Skyrim].ini': {
        'Papyrus': {'bEnableLogging': '0', 'bLoadDebugInformation': '0',
                    'bEnableTrace': '0'}},
    'Debug Log, Enabled [Skyrim].ini': {
        'Papyrus': {'bEnableLogging': '1', 'bLoadDebugInformation': '1',
                    'bEnableTrace': '1'}},
    'Dialog Camera, ~Default [Skyrim].ini': {
        'Controls': {'fDialogueSoftStopAngle1P': '20.0',
                     'fDialogueHardStopAngle1P': '45.0',
                     'fDialogueSoftStopAngle3P': '25.0',
                     'fDialogueHardStopAngle3P': '55.0'}},
    'Dialog Camera, Free [Skyrim].ini': {
        'Controls': {'fDialogueSoftStopAngle1P': '180.0',
                     'fDialogueHardStopAngle1P': '180.0',
                     'fDialogueSoftStopAngle3P': '180.0',
                     'fDialogueHardStopAngle3P': '180.0'}},
    'Grass, Spacing 20 ~Default [Skyrim].ini': {
        'Grass': {'iMinGrassSize': '20'}},
    'Grass, Spacing 40 [Skyrim].ini': {'Grass': {'iMinGrassSize': '40'}},
    'Grass, Spacing 60 [Skyrim].ini': {'Grass': {'iMinGrassSize': '60'}},
    'Grass, Spacing 80 [Skyrim].ini': {'Grass': {'iMinGrassSize': '80'}},
    'Large Interiors Static Limit Fix [Skyrim].ini': {
        'General': {'iLargeIntRefCount': '999999'}},
    'Large Interiors Static Limit ~Default [Skyrim].ini': {
        'General': {'iLargeIntRefCount': '1000'}},
    'Particles, 100 [SkyrimPrefs].ini': {'Particles': {'iMaxDesired': '100'}},
    'Particles, 150 [SkyrimPrefs].ini': {'Particles': {'iMaxDesired': '150'}},
    'Particles, 250 [SkyrimPrefs].ini': {'Particles': {'iMaxDesired': '250'}},
    'Particles, 350 [SkyrimPrefs].ini': {'Particles': {'iMaxDesired': '350'}},
    'Particles, 450 [SkyrimPrefs].ini': {'Particles': {'iMaxDesired': '450'}},
    'Particles, 550 [SkyrimPrefs].ini': {'Particles': {'iMaxDesired': '550'}},
    'Particles, 650 [SkyrimPrefs].ini': {'Particles': {'iMaxDesired': '650'}},
    'Particles, 750 ~Default [SkyrimPrefs].ini': {
        'Particles': {'iMaxDesired': '750'}},
    'Screenshot, Disabled ~Default [Skyrim].ini': {
        'Display': {'bAllowScreenShot': '0'}},
    'Screenshot, Enabled [Skyrim].ini': {'Display': {'bAllowScreenShot': '1'}},
    'Shadows, Res512 Dist 1 [SkyrimPrefs].ini': {
        'Display': {'fShadowDistance': '1.0000', 'fShadowBiasScale': '0.6000',
                    'iShadowMapResolutionPrimary': '1024',
                    'iShadowMapResolutionSecondary': '512',
                    'fInteriorShadowDistance': '2000.0000',
                    'iShadowMapResolution': '512'}},
    'Shadows, Res512 [SkyrimPrefs].ini': {
        'Display': {'fShadowDistance': '2000.0000',
                    'fShadowBiasScale': '0.6000',
                    'iShadowMapResolutionPrimary': '1024',
                    'iShadowMapResolutionSecondary': '512',
                    'fInteriorShadowDistance': '2000.0000',
                    'iShadowMapResolution': '512'}},
    'SunShadow, Update 0.0000 [Skyrim].ini': {
        'Display': {'fSunUpdateThreshold': '0.0000',
                    'fSunShadowUpdateTime': '0.0000'}},
    'SunShadow, Update 0.0500 [Skyrim].ini': {
        'Display': {'fSunUpdateThreshold': '0.0500',
                    'fSunShadowUpdateTime': '0.0000'}},
    'SunShadow, Update 0.1000 [Skyrim].ini': {
        'Display': {'fSunUpdateThreshold': '0.1000',
                    'fSunShadowUpdateTime': '0.0000'}},
    'SunShadow, Update 0.2000 [Skyrim].ini': {
        'Display': {'fSunUpdateThreshold': '0.2000',
                    'fSunShadowUpdateTime': '0.0000'}},
    'Texture Detail, High [SkyrimPrefs].ini': {
        'Display': {'iTexMipMapSkip': '0'}},
    'Texture Detail, Low [SkyrimPrefs].ini': {
        'Display': {'iTexMipMapSkip': '2'}},
    'Texture Detail, Medium [SkyrimPrefs].ini': {
        'Display': {'iTexMipMapSkip': '1'}},
    'Vanity Camera, 120 ~Default [Skyrim].ini': {
        'Camera': {'fAutoVanityModeDelay': '120.0000'}},
    'Vanity Camera, 600 [Skyrim].ini': {
        'Camera': {'fAutoVanityModeDelay': '600.0000'}},
    'Vanity Camera, Disable [Skyrim].ini': {
        'Camera': {'fAutoVanityModeDelay': '0'}},
    'WaterReflect, Res1024 [SkyrimPrefs].ini': {
        'Water': {'iWaterReflectWidth': '1024',
                  'iWaterReflectHeight': '1024'}},
    'WaterReflect, Res256 [SkyrimPrefs].ini': {
        'Water': {'iWaterReflectWidth': '256', 'iWaterReflectHeight': '256'}},
    'WaterReflect, Res512 ~Default[SkyrimPrefs].ini': {
        'Water': {'iWaterReflectWidth': '512', 'iWaterReflectHeight': '512'}},
    'Window Mode Top left, 20-225 [Skyrim].ini': {
        'Display': {'iLocation Y': '20', 'iLocation X': '225'}},
    'Window Mode Top left, 5-5 ~Default [Skyrim].ini': {
        'Display': {'iLocation Y': '5', 'iLocation X': '5'}},
    'Window Mode Top left, 5-60 [Skyrim].ini': {
        'Display': {'iLocation Y': '5', 'iLocation X': '60'}},
}
