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
default_tweaks = {
    'Invalidate, Allow loose files [Fallout4].ini': {
        'Archive': {'bInvalidateOlderFiles': '1',
                    'sResourceDataDirsFinal': ''}},
    'Invalidate, Disallow loose files ~Default [Fallout4].ini': {
        'Archive': {'bInvalidateOlderFiles': '0',
                    'sResourceDataDirsFinal': 'STRINGS\\'}},
    'Always Run, Disabled [Fallout4Prefs].ini': {
        'Controls': {'bAlwaysRunByDefault': '0'}},
    'Always Run, Enabled ~Default [Fallout4Prefs].ini': {
        'Controls': {'bAlwaysRunByDefault': '1'}},
    'Colour HUD, Buff [Fallout4Prefs].ini': {
        'Interface': {'iHUDColorG': '180', 'iHUDColorR': '238',
                      'iHUDColorB': '34'}},
    'Colour HUD, Coral [Fallout4Prefs].ini': {
        'Interface': {'iHUDColorG': '114', 'iHUDColorR': '255',
                      'iHUDColorB': '86'}},
    'Colour HUD, Cream [Fallout4Prefs].ini': {
        'Interface': {'iHUDColorG': '230', 'iHUDColorR': '238',
                      'iHUDColorB': '133'}},
    'Colour HUD, Green ~Default [Fallout4Prefs].ini': {
        'Interface': {'iHUDColorG': '255', 'iHUDColorR': '18',
                      'iHUDColorB': '21'}},
    'Colour HUD, Mauve [Fallout4Prefs].ini': {
        'Interface': {'iHUDColorG': '58', 'iHUDColorR': '178',
                      'iHUDColorB': '238'}},
    'Colour HUD, Red [Fallout4Prefs].ini': {
        'Interface': {'iHUDColorG': '0', 'iHUDColorR': '205',
                      'iHUDColorB': '0'}},
    'Colour HUD, SeaGreen [Fallout4Prefs].ini': {
        'Interface': {'iHUDColorG': '178', 'iHUDColorR': '32',
                      'iHUDColorB': '170'}},
    'Colour PipBoy, Buff [Fallout4Prefs].ini': {
        'Pipboy': {'fPipboyEffectColorB': '0.0900',
                   'fPipboyEffectColorR': '0.8840',
                   'fPipboyEffectColorG': '0.6940'}},
    'Colour PipBoy, Coral [Fallout4Prefs].ini': {
        'Pipboy': {'fPipboyEffectColorB': '0.3397',
                   'fPipboyEffectColorR': '0.8314',
                   'fPipboyEffectColorG': '0.4071'}},
    'Colour PipBoy, Cream [Fallout4Prefs].ini': {
        'Pipboy': {'fPipboyEffectColorB': '0.4867',
                   'fPipboyEffectColorR': '0.8771',
                   'fPipboyEffectColorG': '0.8412'}},
    'Colour PipBoy, Green ~Default [Fallout4Prefs].ini': {
        'Pipboy': {'fPipboyEffectColorB': '0.0900',
                   'fPipboyEffectColorR': '0.0800',
                   'fPipboyEffectColorG': '1.0000'}},
    'Colour PipBoy, Mauve [Fallout4Prefs].ini': {
        'Pipboy': {'fPipboyEffectColorB': '0.8579',
                   'fPipboyEffectColorR': '0.6534',
                   'fPipboyEffectColorG': '0.1853'}},
    'Colour PipBoy, Red [Fallout4Prefs].ini': {
        'Pipboy': {'fPipboyEffectColorB': '0.0349',
                   'fPipboyEffectColorR': '0.6436',
                   'fPipboyEffectColorG': '0.0359'}},
    'Colour PipBoy, SeaGreen [Fallout4Prefs].ini': {
        'Pipboy': {'fPipboyEffectColorB': '0.5983',
                   'fPipboyEffectColorR': '0.0973',
                   'fPipboyEffectColorG': '0.6185'}},
    'DebugLog, Disabled ~Default [Fallout4].ini': {
        'Papyrus': {'bEnableLogging': '0', 'bLoadDebugInformation': '0',
                    'bEnableTrace': '0'}},
    'DebugLog, Enabled  [Fallout4].ini': {
        'Papyrus': {'bEnableLogging': '1', 'bLoadDebugInformation': '1',
                    'bEnableTrace': '1'}},
    'Depth Of Field, Off [Fallout4Prefs].ini': {
        'Imagespace': {'bDoDepthOfField': '0'}},
    'Depth Of Field, On ~Default [Fallout4Prefs].ini': {
        'Imagespace': {'bDoDepthOfField': '1'}},
    'Max Particles, 3000 [Fallout4Prefs].ini': {
        'Particles': {'iMaxDesired': '3000'}},
    'Max Particles, 4000 [Fallout4Prefs].ini': {
        'Particles': {'iMaxDesired': '4000'}},
    'Max Particles, 5000 [Fallout4Prefs].ini': {
        'Particles': {'iMaxDesired': '5000'}},
    'Max Particles, 6000 ~Default [Fallout4Prefs].ini': {
        'Particles': {'iMaxDesired': '6000'}},
    'Max Particles, 7000 [Fallout4Prefs].ini': {
        'Particles': {'iMaxDesired': '7000'}},
    'ShadowMap, res 1024 [Fallout4Prefs].ini': {
        'Display': {'iShadowMapResolution': '1024'}},
    'ShadowMap, res 2048 [Fallout4Prefs].ini': {
        'Display': {'iShadowMapResolution': '2048'}},
    'ShadowMap, res 4096 [Fallout4Prefs].ini': {
        'Display': {'iShadowMapResolution': '4096'}},
    'ShadowMap, res 512 [Fallout4Prefs].ini': {
        'Display': {'iShadowMapResolution': '512'}},
}
