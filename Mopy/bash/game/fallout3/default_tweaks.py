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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from collections import OrderedDict

default_tweaks = {
    u'Anisotropic Filtering, Disabled.ini': OrderedDict(
        [(u'Display', OrderedDict(
            [(u'iMaxAnisotropy', u'0')]))]),
    u'Anisotropic Filtering, x2.ini': OrderedDict(
        [(u'Display', OrderedDict(
            [(u'iMaxAnisotropy', u'2')]))]),
    u'Anisotropic Filtering, x4.ini': OrderedDict(
        [(u'Display', OrderedDict(
            [(u'iMaxAnisotropy', u'4')]))]),
    u'Anisotropic Filtering, x8 ~Default.ini': OrderedDict(
        [(u'Display', OrderedDict(
            [(u'iMaxAnisotropy', u'8')]))]),
    u'Anisotropic Filtering, x16.ini': OrderedDict(
        [(u'Display', OrderedDict(
            [(u'iMaxAnisotropy', u'16')]))]),
    u'Anti-Aliasing, Disabled ~Default.ini': OrderedDict(
        [(u'Display', OrderedDict(
            [(u'iMultiSample', u'0')]))]),
    u'Anti-Aliasing, x2.ini': OrderedDict(
        [(u'Display', OrderedDict(
            [(u'iMultiSample', u'2')]))]),
    u'Anti-Aliasing, x4.ini': OrderedDict(
        [(u'Display', OrderedDict(
            [(u'iMultiSample', u'4')]))]),
    u'Anti-Aliasing, x8.ini': OrderedDict(
        [(u'Display', OrderedDict(
            [(u'iMultiSample', u'8')]))]),
    u'Border Regions, Disabled.ini': OrderedDict(
        [(u'Main', OrderedDict(
            [(u'bEnableBorderRegion', u'0')]))]),
    u'Border Regions, Enabled ~Default.ini': OrderedDict(
        [(u'Main', OrderedDict(
            [(u'bEnableBorderRegion', u'1')]))]),
    u'Fonts 1, ~Default.ini': OrderedDict(
        [(u'Fonts', OrderedDict(
            [(u'sFontFile_1',
              u'Textures\\Fonts\\Glow_Monofonto_Large.fnt')]))]),
    u'Grass, Fade 4k-5k.ini': OrderedDict(
        [(u'Grass', OrderedDict(
            [(u'iMinGrassSize', u'140'),
             (u'fGrassMaxStartFadeDistance', u'5000.0000')]))]),
    u'Mouse Acceleration, ~Default.ini': OrderedDict(
        [(u'Controls', OrderedDict(
            [(u'fForegroundMouseAccelBase', u''),
             (u'fForegroundMouseBase', u''),
             (u'fForegroundMouseAccelTop', u''),
             (u'fForegroundMouseMult', u'')]))]),
    u'Mouse Acceleration, Fixed.ini': OrderedDict(
        [(u'Controls', OrderedDict(
            [(u'fForegroundMouseAccelBase', u'0'),
             (u'fForegroundMouseBase', u'0'),
             (u'fForegroundMouseAccelTop', u'0'),
             (u'fForegroundMouseMult', u'0')]))]),
    u'Refraction Shader, Disabled.ini': OrderedDict(
        [(u'Display', OrderedDict(
            [(u'bUseRefractionShader', u'0')]))]),
    u'Refraction Shader, Enabled ~Default.ini': OrderedDict(
        [(u'Display', OrderedDict(
            [(u'bUseRefractionShader', u'1')]))]),
    u'Save Backups, 1 ~Default.ini': OrderedDict(
        [(u'General', OrderedDict(
            [(u'iSaveGameBackupCount', u'1')]))]),
    u'Save Backups, 2.ini': OrderedDict(
        [(u'General', OrderedDict(
            [(u'iSaveGameBackupCount', u'2')]))]),
    u'Save Backups, 3.ini': OrderedDict(
        [(u'General', OrderedDict(
            [(u'iSaveGameBackupCount', u'3')]))]),
    u'Save Backups, 4.ini': OrderedDict(
        [(u'General', OrderedDict(
            [(u'iSaveGameBackupCount', u'4')]))]),
    u'Save Backups, 5.ini': OrderedDict(
        [(u'General', OrderedDict(
            [(u'iSaveGameBackupCount', u'5')]))]),
    u'bInvalidateOlderFiles, Disabled ~Default.ini': OrderedDict(
        [(u'Archive', OrderedDict(
            [(u'bInvalidateOlderFiles', u'0')]))]),
    u'bInvalidateOlderFiles, Enabled.ini': OrderedDict(
        [(u'Archive', OrderedDict(
            [(u'bInvalidateOlderFiles', u'1')]))]),
    u'iConsoleTextXPos, ~Default.ini': OrderedDict(
        [(u'Menu', OrderedDict(
            [(u'iConsoleTextXPos', u'30')]))]),
    u'iConsoleTextXPos, Fixed.ini': OrderedDict(
        [(u'Menu', OrderedDict(
            [(u'iConsoleTextXPos', u'130')]))]),
}
