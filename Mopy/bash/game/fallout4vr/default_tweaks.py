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
    u'Modding, Enabled [Fallout4Custom].ini': OrderedDict(
        [(u'Archive', OrderedDict(
            [(u'bInvalidateOlderFiles', u'1'),
             (u'sResourceDataDirsFinal', u'')]))]),
    u'Modding, Disabled ~Default [Fallout4Custom].ini': OrderedDict(
        [(u'Archive', OrderedDict(
            [(u'bInvalidateOlderFiles', u'0'),
             (u'sResourceDataDirsFinal', u'STRINGS\\')]))]),
    u'Always Run, Disabled [Fallout4Prefs].ini': OrderedDict(
        [(u'Controls', OrderedDict([(u'bAlwaysRunByDefault', u'0')]))]),
    u'Always Run, Enabled ~Default [Fallout4Prefs].ini': OrderedDict(
        [(u'Controls', OrderedDict([(u'bAlwaysRunByDefault', u'1')]))]),
    u'Colour HUD, Buff [Fallout4Prefs].ini': OrderedDict(
        [(u'Interface', OrderedDict(
            [(u'iHUDColorG', u'180'), (u'iHUDColorR', u'238'),
                (u'iHUDColorB', u'34')]))]),
    u'Colour HUD, Coral [Fallout4Prefs].ini': OrderedDict(
        [(u'Interface', OrderedDict(
            [(u'iHUDColorG', u'114'), (u'iHUDColorR', u'255'),
                (u'iHUDColorB', u'86')]))]),
    u'Colour HUD, Cream [Fallout4Prefs].ini': OrderedDict(
        [(u'Interface', OrderedDict(
            [(u'iHUDColorG', u'230'), (u'iHUDColorR', u'238'),
                (u'iHUDColorB', u'133')]))]),
    u'Colour HUD, Green ~Default [Fallout4Prefs].ini': OrderedDict([(
        u'Interface', OrderedDict(
            [(u'iHUDColorG', u'255'), (u'iHUDColorR', u'18'),
             (u'iHUDColorB', u'21')]))]),
    u'Colour HUD, Mauve [Fallout4Prefs].ini': OrderedDict(
        [(u'Interface', OrderedDict(
            [(u'iHUDColorG', u'58'), (u'iHUDColorR', u'178'),
                (u'iHUDColorB', u'238')]))]),
    u'Colour HUD, Red [Fallout4Prefs].ini': OrderedDict(
        [(u'Interface', OrderedDict(
            [(u'iHUDColorG', u'0'), (u'iHUDColorR', u'205'),
                (u'iHUDColorB', u'0')]))]),
    u'Colour HUD, SeaGreen [Fallout4Prefs].ini': OrderedDict(
        [(u'Interface', OrderedDict(
            [(u'iHUDColorG', u'178'), (u'iHUDColorR', u'32'),
                (u'iHUDColorB', u'170')]))]),
    u'Colour PipBoy, Buff [Fallout4Prefs].ini': OrderedDict(
        [(u'Pipboy', OrderedDict([(u'fPipboyEffectColorB', u'0.0900'),
            (u'fPipboyEffectColorR', u'0.8840'),
            (u'fPipboyEffectColorG', u'0.6940')]))]),
    u'Colour PipBoy, Coral [Fallout4Prefs].ini': OrderedDict(
        [(u'Pipboy', OrderedDict([(u'fPipboyEffectColorB', u'0.3397'),
                                  (u'fPipboyEffectColorR', u'0.8314'),
                                  (u'fPipboyEffectColorG', u'0.4071')]))]),
    u'Colour PipBoy, Cream [Fallout4Prefs].ini': OrderedDict(
        [(u'Pipboy', OrderedDict([(u'fPipboyEffectColorB', u'0.4867'),
            (u'fPipboyEffectColorR', u'0.8771'),
            (u'fPipboyEffectColorG', u'0.8412')]))]),
    u'Colour PipBoy, Green ~Default [Fallout4Prefs].ini': OrderedDict([(
        u'Pipboy', OrderedDict([(u'fPipboyEffectColorB', u'0.0900'),
                                (u'fPipboyEffectColorR', u'0.0800'),
                                (u'fPipboyEffectColorG', u'1.0000')]))]),
    u'Colour PipBoy, Mauve [Fallout4Prefs].ini': OrderedDict(
        [(u'Pipboy', OrderedDict([(u'fPipboyEffectColorB', u'0.8579'),
            (u'fPipboyEffectColorR', u'0.6534'),
            (u'fPipboyEffectColorG', u'0.1853')]))]),
    u'Colour PipBoy, Red [Fallout4Prefs].ini': OrderedDict(
        [(u'Pipboy', OrderedDict([(u'fPipboyEffectColorB', u'0.0349'),
            (u'fPipboyEffectColorR', u'0.6436'),
            (u'fPipboyEffectColorG', u'0.0359')]))]),
    u'Colour PipBoy, SeaGreen [Fallout4Prefs].ini': OrderedDict(
        [(u'Pipboy', OrderedDict([(u'fPipboyEffectColorB', u'0.5983'),
            (u'fPipboyEffectColorR', u'0.0973'),
            (u'fPipboyEffectColorG', u'0.6185')]))]),
    u'DebugLog, Disabled ~Default [Fallout4Custom].ini': OrderedDict([(
        u'Papyrus', OrderedDict(
            [(u'bEnableLogging', u'0'), (u'bLoadDebugInformation', u'0'),
             (u'bEnableTrace', u'0')]))]),
    u'DebugLog, Enabled  [Fallout4Custom].ini': OrderedDict(
        [(u'Papyrus', OrderedDict(
            [(u'bEnableLogging', u'1'), (u'bLoadDebugInformation', u'1'),
                (u'bEnableTrace', u'1')]))]),
    u'Depth Of Field, Off [Fallout4Prefs].ini': OrderedDict(
        [(u'Imagespace', OrderedDict([(u'bDoDepthOfField', u'0')]))]),
    u'Depth Of Field, On ~Default [Fallout4Prefs].ini': OrderedDict(
        [(u'Imagespace', OrderedDict([(u'bDoDepthOfField', u'1')]))]),
    u'Max Particles, 3000 [Fallout4Prefs].ini': OrderedDict(
        [(u'Particles', OrderedDict([(u'iMaxDesired', u'3000')]))]),
    u'Max Particles, 4000 [Fallout4Prefs].ini': OrderedDict(
        [(u'Particles', OrderedDict([(u'iMaxDesired', u'4000')]))]),
    u'Max Particles, 5000 [Fallout4Prefs].ini': OrderedDict(
        [(u'Particles', OrderedDict([(u'iMaxDesired', u'5000')]))]),
    u'Max Particles, 6000 ~Default [Fallout4Prefs].ini': OrderedDict(
        [(u'Particles', OrderedDict([(u'iMaxDesired', u'6000')]))]),
    u'Max Particles, 7000 [Fallout4Prefs].ini': OrderedDict(
        [(u'Particles', OrderedDict([(u'iMaxDesired', u'7000')]))]),
    u'ShadowMap, res 1024 [Fallout4Prefs].ini': OrderedDict(
        [(u'Display', OrderedDict([(u'iShadowMapResolution', u'1024')]))]),
    u'ShadowMap, res 2048 [Fallout4Prefs].ini': OrderedDict(
        [(u'Display', OrderedDict([(u'iShadowMapResolution', u'2048')]))]),
    u'ShadowMap, res 4096 [Fallout4Prefs].ini': OrderedDict(
        [(u'Display', OrderedDict([(u'iShadowMapResolution', u'4096')]))]),
    u'ShadowMap, res 512 [Fallout4Prefs].ini': OrderedDict(
        [(u'Display', OrderedDict([(u'iShadowMapResolution', u'512')]))]),
    u'VR Render Size Multiplier, 0.8 [Fallout4Custom].ini': OrderedDict(
        [(u'VRDisplay', OrderedDict([(u'fRenderTargetSizeMultiplier', u'0.8')]))]),
    u'VR Render Size Multiplier, 1.0 [Fallout4Custom].ini': OrderedDict(
        [(u'VRDisplay', OrderedDict([(u'fRenderTargetSizeMultiplier', u'1.0')]))]),
    u'VR Render Size Multiplier, 1.2 [Fallout4Custom].ini': OrderedDict(
        [(u'VRDisplay', OrderedDict([(u'fRenderTargetSizeMultiplier', u'1.2')]))]),
    u'VR Render Size Multiplier, 1.4 [Fallout4Custom].ini': OrderedDict(
        [(u'VRDisplay', OrderedDict([(u'fRenderTargetSizeMultiplier', u'1.4')]))]),
    u'VR Scale, 70 [Fallout4VrCustom].ini': OrderedDict(
        [(u'VR', OrderedDict([(u'fVrScale', u'70')]))]),
    u'VR Scale, 75 [Fallout4VrCustom].ini': OrderedDict(
        [(u'VR', OrderedDict([(u'fVrScale', u'75')]))]),
    u'VR Scale, 80 [Fallout4VrCustom].ini': OrderedDict(
        [(u'VR', OrderedDict([(u'fVrScale', u'80')]))]),
}
