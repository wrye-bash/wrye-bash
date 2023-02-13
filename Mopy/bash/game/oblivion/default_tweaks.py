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
    'Autosave, Never [Oblivion].ini': {
        'GamePlay': {'bSaveOnWait': '0', 'bSaveOnTravel': '0',
                     'bSaveOnRest': '0'}},
    'Autosave, ~Always [Oblivion].ini': {
        'GamePlay': {'bSaveOnWait': '1', 'bSaveOnTravel': '1',
                     'bSaveOnRest': '1'}},
    'Border Regions, Disabled [Oblivion].ini': {
        'General': {'bBorderRegionsEnabled': '0'}},
    'Border Regions, ~Enabled [Oblivion].ini': {
        'General': {'bBorderRegionsEnabled': '1'}},
    'Fonts 1, ~Default [Oblivion].ini': {
        'Fonts': {'SFontFile_1': r'Data\Fonts\Kingthings_Regular.fnt'}},
    'Fonts, ~Default [Oblivion].ini': {
        'Fonts': {'SFontFile_4': r'Data\Fonts\Daedric_Font.fnt',
                  'SFontFile_5': r'Data\Fonts\Handwritten.fnt',
                  'SFontFile_1': r'Data\Fonts\Kingthings_Regular.fnt',
                  'SFontFile_2': r'Data\Fonts\Kingthings_Shadowed.fnt',
                  'SFontFile_3': r'Data\Fonts\Tahoma_Bold_Small.fnt'}},
    'Grass, Fade 4k-5k [Oblivion].ini': {'Grass': {
        'iMinGrassSize': '120', 'fGrassStartFadeDistance': '4000.0000',
        'fGrassEndDistance': '5000.0000'}},
    'Grass, ~Fade 2k-3k [Oblivion].ini': {'Grass': {
        'iMinGrassSize': '80', 'fGrassStartFadeDistance': '2000.0000',
        'fGrassEndDistance': '3000.0000'}},
    'Intro Movies, All Disabled [Oblivion].ini': {
        'General': {'SCreditsMenuMovie': '', 'SMainMenuMovieIntro': '',
                    'SMainMenuMovie': '', 'SIntroSequence': ''}},
    'Intro Movies, Intro Sequence Disabled [Oblivion].ini': {
        'General': {
            'SCreditsMenuMovie': 'CreditsMenu.bik',
            'SMainMenuMovieIntro': 'Oblivion iv logo.bik',
            'SMainMenuMovie': 'Map loop.bik', 'SIntroSequence': ''}},
    'Intro Movies, ~All Enabled [Oblivion].ini': {
        'General': {
            'SCreditsMenuMovie': 'CreditsMenu.bik',
            'SMainMenuMovieIntro': 'Oblivion iv logo.bik',
            'SMainMenuMovie': 'Map loop.bik',
            'SIntroSequence': 'bethesda softworks HD720p.bik,2k games.bik,'
                              'game studios.bik,Oblivion Legal.bik'}},
    'Joystick, Disabled [Oblivion].ini': {'Controls': {'bUse Joystick': '0'}},
    'Joystick, ~Enabled [Oblivion].ini': {'Controls': {'bUse Joystick': '1'}},
    'Local Map Shader, Disabled [Oblivion].ini': {
        'Display': {'blocalmapshader': '0'}},
    'Local Map Shader, ~Enabled [Oblivion].ini': {
        'Display': {'blocalmapshader': '1'}},
    'Music, Disabled [Oblivion].ini': {'Audio': {'bMusicEnabled': '0'}},
    'Music, ~Enabled [Oblivion].ini': {'Audio': {'bMusicEnabled': '1'}},
    'Refraction Shader, Disabled [Oblivion].ini': {
        'Display': {'bUseRefractionShader': '0'}},
    'Refraction Shader, ~Enabled [Oblivion].ini': {
        'Display': {'bUseRefractionShader': '1'}},
    'Save Backups, 1 [Oblivion].ini': {
        'General': {'iSaveGameBackupCount': '1'}},
    'Save Backups, 2 [Oblivion].ini': {
        'General': {'iSaveGameBackupCount': '2'}},
    'Save Backups, 3 [Oblivion].ini': {
        'General': {'iSaveGameBackupCount': '3'}},
    'Save Backups, 5 [Oblivion].ini': {
        'General': {'iSaveGameBackupCount': '5'}},
    'Screenshot, Enabled [Oblivion].ini': {
        'Display': {'bAllowScreenShot': '1'}},
    'Screenshot, ~Disabled [Oblivion].ini': {
        'Display': {'bAllowScreenShot': '0'}},
    'ShadowMapResolution, 1024 [Oblivion].ini': {
        'Display': {'iShadowMapResolution': '1024'}},
    'ShadowMapResolution, ~256 [Oblivion].ini': {
        'Display': {'iShadowMapResolution': '256'}},
    'Sound Card Channels, 128 [Oblivion].ini': {
        'Audio': {'iMaxImpactSoundCount': '128'}},
    'Sound Card Channels, 16 [Oblivion].ini': {
        'Audio': {'iMaxImpactSoundCount': '16'}},
    'Sound Card Channels, 192 [Oblivion].ini': {
        'Audio': {'iMaxImpactSoundCount': '192'}},
    'Sound Card Channels, 24 [Oblivion].ini': {
        'Audio': {'iMaxImpactSoundCount': '24'}},
    'Sound Card Channels, 48 [Oblivion].ini': {
        'Audio': {'iMaxImpactSoundCount': '48'}},
    'Sound Card Channels, 64 [Oblivion].ini': {
        'Audio': {'iMaxImpactSoundCount': '64'}},
    'Sound Card Channels, 8 [Oblivion].ini': {
        'Audio': {'iMaxImpactSoundCount': '8'}},
    'Sound Card Channels, 96 [Oblivion].ini': {
        'Audio': {'iMaxImpactSoundCount': '96'}},
    'Sound Card Channels, ~32 [Oblivion].ini': {
        'Audio': {'iMaxImpactSoundCount': '32'}},
    'Sound, Disabled [Oblivion].ini': {'Audio': {'bSoundEnabled': '0'}},
    'Sound, ~Enabled [Oblivion].ini': {'Audio': {'bSoundEnabled': '1'}},
    'Static Menu Background, Disabled [Oblivion].ini': {
        'Display': {'bStaticMenuBackground': '0'}},
    'Static Menu Background, ~Enabled [Oblivion].ini': {
        'Display': {'bStaticMenuBackground': '1'}},
}
