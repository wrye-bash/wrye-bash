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

default_tweaks = {u'Border Regions, Disabled.ini': OrderedDict(
    [(u'MAIN', OrderedDict([(u'bEnableBorderRegion', u'0')]))]),
    u'Border Regions, ~Enabled.ini': OrderedDict(
        [(u'MAIN', OrderedDict([(u'bEnableBorderRegion', u'1')]))]),
    u'Fonts 1, ~Default.ini': OrderedDict([(u'Fonts', OrderedDict(
        [(u'sFontFile_1', u'Textures\\Fonts\\Glow_Monofonto_Large.fnt')]))]),
    u'Grass, Fade 4k-5k.ini': OrderedDict([(u'Grass', OrderedDict(
        [(u'iMinGrassSize', u'140'),
         (u'fGrassMaxStartFadeDistance', u'5000.0000')]))]),
    u'Mouse Acceleration, Default.ini': OrderedDict([(u'CONTROLS', OrderedDict(
        [(u'fForegroundMouseAccelBase', u''), (u'fForegroundMouseBase', u''),
         (u'fForegroundMouseAccelTop', u''),
         (u'fForegroundMouseMult', u'')]))]),
    u'Mouse Acceleration, ~Fixed.ini': OrderedDict([(u'CONTROLS', OrderedDict(
        [(u'fForegroundMouseAccelBase', u'0'), (u'fForegroundMouseBase', u'0'),
         (u'fForegroundMouseAccelTop', u'0'),
         (u'fForegroundMouseMult', u'0')]))]),
    u'Refraction Shader, Disabled.ini': OrderedDict(
        [(u'Display', OrderedDict([(u'bUseRefractionShader', u'0')]))]),
    u'Refraction Shader, ~Enabled.ini': OrderedDict(
        [(u'Display', OrderedDict([(u'bUseRefractionShader', u'1')]))]),
    u'Save Backups, 1.ini': OrderedDict(
        [(u'General', OrderedDict([(u'iSaveGameBackupCount', u'1')]))]),
    u'Save Backups, 2.ini': OrderedDict(
        [(u'General', OrderedDict([(u'iSaveGameBackupCount', u'2')]))]),
    u'Save Backups, 3.ini': OrderedDict(
        [(u'General', OrderedDict([(u'iSaveGameBackupCount', u'3')]))]),
    u'Save Backups, 5.ini': OrderedDict(
        [(u'General', OrderedDict([(u'iSaveGameBackupCount', u'5')]))]),
    u'bInvalidateOlderFiles, ~Default.ini': OrderedDict(
        [(u'Archive', OrderedDict([(u'bInvalidateOlderFiles', u'0')]))]),
    u'bInvalidateOlderFiles, ~Enabled.ini': OrderedDict(
        [(u'Archive', OrderedDict([(u'bInvalidateOlderFiles', u'1')]))]),
    u'iConsoleTextXPos, Default.ini': OrderedDict(
        [(u'Menu', OrderedDict([(u'iConsoleTextXPos', u'30')]))]),
    u'iConsoleTextXPos, ~Fixed.ini': OrderedDict(
        [(u'Menu', OrderedDict([(u'iConsoleTextXPos', u'130')]))])
}
