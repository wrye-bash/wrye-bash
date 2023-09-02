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
    'Anisotropic Filtering, Disabled.ini': {
        'Display': {'iMaxAnisotropy': '0'}},
    'Anisotropic Filtering, x2.ini': {'Display': {'iMaxAnisotropy': '2'}},
    'Anisotropic Filtering, x4.ini': {'Display': {'iMaxAnisotropy': '4'}},
    'Anisotropic Filtering, x8 ~Default.ini': {
        'Display': {'iMaxAnisotropy': '8'}},
    'Anisotropic Filtering, x16.ini': {'Display': {'iMaxAnisotropy': '16'}},
    'Anti-Aliasing, Disabled ~Default.ini': {'Display': {'iMultiSample': '0'}},
    'Anti-Aliasing, x2.ini': {'Display': {'iMultiSample': '2'}},
    'Anti-Aliasing, x4.ini': {'Display': {'iMultiSample': '4'}},
    'Anti-Aliasing, x8.ini': {'Display': {'iMultiSample': '8'}},
    'Border Regions, Disabled.ini': {'Main': {'bEnableBorderRegion': '0'}},
    'Border Regions, Enabled ~Default.ini': {
        'Main': {'bEnableBorderRegion': '1'}},
    'Fonts 1, ~Default.ini': {
        'Fonts': {'sFontFile_1': r'Textures\Fonts\Glow_Monofonto_Large.fnt'}},
    'Grass, Fade 4k-5k.ini': {
        'Grass': {'iMinGrassSize': '140',
                  'fGrassMaxStartFadeDistance': '5000.0000'}},
    'Mouse Acceleration, ~Default.ini': {
        'Controls': {'fForegroundMouseAccelBase': '',
                     'fForegroundMouseBase': '',
                     'fForegroundMouseAccelTop': '',
                     'fForegroundMouseMult': ''}},
    'Mouse Acceleration, Fixed.ini': {
        'Controls': {'fForegroundMouseAccelBase': '0',
                     'fForegroundMouseBase': '0',
                     'fForegroundMouseAccelTop': '0',
                     'fForegroundMouseMult': '0'}},
    'Refraction Shader, Disabled.ini': {
        'Display': {'bUseRefractionShader': '0'}},
    'Refraction Shader, Enabled ~Default.ini': {
        'Display': {'bUseRefractionShader': '1'}},
    'Save Backups, 1 ~Default.ini': {'General': {'iSaveGameBackupCount': '1'}},
    'Save Backups, 2.ini': {'General': {'iSaveGameBackupCount': '2'}},
    'Save Backups, 3.ini': {'General': {'iSaveGameBackupCount': '3'}},
    'Save Backups, 4.ini': {'General': {'iSaveGameBackupCount': '4'}},
    'Save Backups, 5.ini': {'General': {'iSaveGameBackupCount': '5'}},
    'Invalidate, Allow loose files.ini': {
        'Archive': {'bInvalidateOlderFiles': '1'}},
    'Invalidate, Disallow loose files ~Default.ini': {
        'Archive': {'bInvalidateOlderFiles': '0'}},
    'iConsoleTextXPos, ~Default.ini': {'Menu': {'iConsoleTextXPos': '30'}},
    'iConsoleTextXPos, Fixed.ini': {'Menu': {'iConsoleTextXPos': '130'}},
}
