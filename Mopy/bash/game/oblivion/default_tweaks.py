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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2015 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from collections import OrderedDict

default_tweaks = {
    u'Autosave, Never [Oblivion].ini': OrderedDict(
        [(u'GamePlay', OrderedDict(
            [(u'bSaveOnWait', u'0'), (u'bSaveOnTravel', u'0'),
             (u'bSaveOnRest', u'0')]))]),
    u'Autosave, ~Always [Oblivion].ini':
        OrderedDict([(u'GamePlay', OrderedDict(
            [(u'bSaveOnWait', u'1'), (u'bSaveOnTravel', u'1'),
                (u'bSaveOnRest', u'1')]))]),
    u'Border Regions, Disabled [Oblivion].ini': OrderedDict(
        [(u'General', OrderedDict(
            [(u'bBorderRegionsEnabled', u'0')]))]),
    u'Border Regions, ~Enabled [Oblivion].ini': OrderedDict(
        [(u'General', OrderedDict(
            [(u'bBorderRegionsEnabled', u'1')]))]),
    u'Fonts 1, ~Default [Oblivion].ini': OrderedDict(
        [(u'Fonts', OrderedDict(
            [(u'SFontFile_1', u'Data\\Fonts\\Kingthings_Regular.fnt')]))]),
    u'Fonts, ~Default [Oblivion].ini': OrderedDict(
        [(u'Fonts', OrderedDict(
            [(u'SFontFile_4', u'Data\\Fonts\\Daedric_Font.fnt'),
             (u'SFontFile_5', u'Data\\Fonts\\Handwritten.fnt'),
             (u'SFontFile_1', u'Data\\Fonts\\Kingthings_Regular.fnt'),
             (u'SFontFile_2', u'Data\\Fonts\\Kingthings_Shadowed.fnt'),
             (u'SFontFile_3', u'Data\\Fonts\\Tahoma_Bold_Small.fnt')]))]),
    u'Grass, Fade 4k-5k [Oblivion].ini': OrderedDict(
        [(u'Grass', OrderedDict(
            [(u'iMinGrassSize', u'120'),
             (u'fGrassStartFadeDistance', u'4000.0000'),
             (u'fGrassEndDistance', u'5000.0000')]))]),
    u'Grass, ~Fade 2k-3k [Oblivion].ini': OrderedDict(
        [(u'Grass', OrderedDict(
        [(u'iMinGrassSize', u'80'), (u'fGrassStartFadeDistance', u'2000.0000'),
         (u'fGrassEndDistance', u'3000.0000')]))]),
    u'Intro Movies, Disabled [Oblivion].ini': OrderedDict(
        [(u'General', OrderedDict(
            [(u'SCreditsMenuMovie', u''), (u'SMainMenuMovieIntro', u''),
             (u'SMainMenuMovie', u''), (u'SIntroSequence', u'')]))]),
    u'Intro Movies, ~Normal [Oblivion].ini': OrderedDict(
        [(u'General', OrderedDict(
            [(u'SCreditsMenuMovie', u'CreditsMenu.bik'),
             (u'SMainMenuMovieIntro', u'Oblivion iv logo.bik'),
             (u'SMainMenuMovie', u'Map loop.bik'),
             (u'SIntroSequence',
              u'bethesda softworks HD720p.bik,2k games.bik,game studios.bik,'
              u'Oblivion Legal.bik')]))]),
    u'Joystick, Disabled [Oblivion].ini': OrderedDict(
        [(u'Controls', OrderedDict([(u'bUse Joystick', u'0')]))]),
    u'Joystick, ~Enabled [Oblivion].ini': OrderedDict(
        [(u'Controls', OrderedDict([(u'bUse Joystick', u'1')]))]),
    u'Local Map Shader, Disabled [Oblivion].ini': OrderedDict(
        [(u'Display', OrderedDict([(u'blocalmapshader', u'0')]))]),
    u'Local Map Shader, ~Enabled [Oblivion].ini': OrderedDict(
        [(u'Display', OrderedDict([(u'blocalmapshader', u'1')]))]),
    u'Music, Disabled [Oblivion].ini': OrderedDict(
        [(u'Audio', OrderedDict([(u'bMusicEnabled', u'0')]))]),
    u'Music, ~Enabled [Oblivion].ini': OrderedDict(
        [(u'Audio', OrderedDict([(u'bMusicEnabled', u'1')]))]),
    u'Refraction Shader, Disabled [Oblivion].ini': OrderedDict(
        [(u'Display', OrderedDict([(u'bUseRefractionShader', u'0')]))]),
    u'Refraction Shader, ~Enabled [Oblivion].ini': OrderedDict(
        [(u'Display', OrderedDict([(u'bUseRefractionShader', u'1')]))]),
    u'Save Backups, 1 [Oblivion].ini': OrderedDict(
        [(u'General', OrderedDict([(u'iSaveGameBackupCount', u'1')]))]),
    u'Save Backups, 2 [Oblivion].ini': OrderedDict(
        [(u'General', OrderedDict([(u'iSaveGameBackupCount', u'2')]))]),
    u'Save Backups, 3 [Oblivion].ini': OrderedDict(
        [(u'General', OrderedDict([(u'iSaveGameBackupCount', u'3')]))]),
    u'Save Backups, 5 [Oblivion].ini': OrderedDict(
        [(u'General', OrderedDict([(u'iSaveGameBackupCount', u'5')]))]),
    u'Screenshot, Enabled [Oblivion].ini': OrderedDict(
        [(u'Display', OrderedDict([(u'bAllowScreenShot', u'1')]))]),
    u'Screenshot, ~Disabled [Oblivion].ini': OrderedDict(
        [(u'Display', OrderedDict([(u'bAllowScreenShot', u'0')]))]),
    u'ShadowMapResolution, 1024 [Oblivion].ini': OrderedDict(
        [(u'Display', OrderedDict([(u'iShadowMapResolution', u'1024')]))]),
    u'ShadowMapResolution, ~256 [Oblivion].ini': OrderedDict(
        [(u'Display', OrderedDict([(u'iShadowMapResolution', u'256')]))]),
    u'Sound Card Channels, 128 [Oblivion].ini': OrderedDict(
        [(u'Audio', OrderedDict([(u'iMaxImpactSoundCount', u'128')]))]),
    u'Sound Card Channels, 16 [Oblivion].ini': OrderedDict(
        [(u'Audio', OrderedDict([(u'iMaxImpactSoundCount', u'16')]))]),
    u'Sound Card Channels, 192 [Oblivion].ini': OrderedDict(
        [(u'Audio', OrderedDict([(u'iMaxImpactSoundCount', u'192')]))]),
    u'Sound Card Channels, 24 [Oblivion].ini': OrderedDict(
        [(u'Audio', OrderedDict([(u'iMaxImpactSoundCount', u'24')]))]),
    u'Sound Card Channels, 48 [Oblivion].ini': OrderedDict(
        [(u'Audio', OrderedDict([(u'iMaxImpactSoundCount', u'48')]))]),
    u'Sound Card Channels, 64 [Oblivion].ini': OrderedDict(
        [(u'Audio', OrderedDict([(u'iMaxImpactSoundCount', u'64')]))]),
    u'Sound Card Channels, 8 [Oblivion].ini': OrderedDict(
        [(u'Audio', OrderedDict([(u'iMaxImpactSoundCount', u'8')]))]),
    u'Sound Card Channels, 96 [Oblivion].ini': OrderedDict(
        [(u'Audio', OrderedDict([(u'iMaxImpactSoundCount', u'96')]))]),
    u'Sound Card Channels, ~32 [Oblivion].ini': OrderedDict(
        [(u'Audio', OrderedDict([(u'iMaxImpactSoundCount', u'32')]))]),
    u'Sound, Disabled [Oblivion].ini': OrderedDict(
        [(u'Audio', OrderedDict([(u'bSoundEnabled', u'0')]))]),
    u'Sound, ~Enabled [Oblivion].ini': OrderedDict(
        [(u'Audio', OrderedDict([(u'bSoundEnabled', u'1')]))])
}
