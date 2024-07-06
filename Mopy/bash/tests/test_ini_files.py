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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Tests for the ini_files module - WIP."""

from Mopy.bash.ini_files import IniFileInfo, OBSEIniFile

def test_parse_ini_line():
    res = IniFileInfo.parse_ini_line('key=value')
    assert res == ('key=value', 'key', 'value', None, False)
    res = IniFileInfo.parse_ini_line('key=')
    assert res == ('key=', 'key', '', None, False)
    res = IniFileInfo.parse_ini_line(';-key=value')
    assert res == ('key=value', 'key', 'value', None, True)
    res = IniFileInfo.parse_ini_line('  key   =   value    ')
    assert res == ('key   =   value', 'key', 'value', None, False)
    res = IniFileInfo.parse_ini_line('   key     =    ')
    assert res == ('key     =', 'key', '', None, False) # value is stripped!
    res = IniFileInfo.parse_ini_line(';-   key  =   value')
    assert res == (failed := ('', None, None, None, False))
    res = IniFileInfo.parse_ini_line(';-key  =   value')
    assert res == ('key  =   value', 'key', 'value', None, True)
    res = IniFileInfo.parse_ini_line('  [    section  ]  ')
    assert res == ('[    section  ]', None, None, 'section', False)
    res = OBSEIniFile.parse_ini_line('  [    section  ]  ')
    assert res == failed
    res = OBSEIniFile.parse_ini_line('  set setting to value   ')
    assert res == ('set setting to value', 'setting', 'value', ']set[', False)
    res = OBSEIniFile.parse_ini_line('  setGS setting value   ')
    assert res == ('setGS setting value', 'setting', 'value', ']setGS[', False)
