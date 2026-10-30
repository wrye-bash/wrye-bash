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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2026 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Tests for the ini_files module - WIP."""
import codecs
import os

from ..bolt import FName, FNDict, GPath
from ..game.starfield import SteamStarfieldGameInfo
from ..ini_files import GameIni, IniFileInfo, OBSEIniFile

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
    assert res == ('key  =   value', 'key', 'value', None, True)
    res = IniFileInfo.parse_ini_line(';-key  =   value')
    assert res == ('key  =   value', 'key', 'value', None, True)
    res = IniFileInfo.parse_ini_line('  [    section  ]  ')
    assert res == ('[    section  ]', None, None, 'section', False)
    res = OBSEIniFile.parse_ini_line('  [    section  ]  ')
    assert res == ('', None, None, None, False) # failed
    res = OBSEIniFile.parse_ini_line('  set setting to value   ')
    assert res == ('set setting to value', 'setting', 'value', ']set[', False)
    res = OBSEIniFile.parse_ini_line('  setGS setting value   ')
    assert res == ('setGS setting value', 'setting', 'value', ']setGS[', False)

def _game_ini(ini_dir, **ini_contents):
    """Write the INIs in ini_contents (name -> str or raw bytes content) to
    ini_dir and return the GameIni for main.ini, with custom.ini as its
    Custom INI."""
    ini_dir.mkdir()
    for ini_name, content in ini_contents.items():
        if isinstance(content, str):
            content = content.encode('cp1252')
        (ini_dir / f'{ini_name}.ini').write_bytes(content)
    def _ini(ini_name, custom_ini=None):
        return GameIni(GPath(os.fspath(ini_dir / f'{ini_name}.ini')),
                       'cp1252', custom_ini)
    return _ini('main', _ini('custom'))

def test_game_ini_language(tmp_path):
    """The Custom INI overrides the main INI - neither has to exist."""
    def _lang(case_dir, **ini_contents):
        return _game_ini(tmp_path / case_dir, **ini_contents).get_ini_language(
            SteamStarfieldGameInfo)
    assert _lang('none') == 'en' # the default
    assert _lang('main', main='[General]\nsLanguage=es\n') == 'es'
    assert _lang('custom', main='[General]\nsLanguage=es\n',
                 custom='[General]\nsLanguage=de\n') == 'de'

def test_game_ini_encodings(tmp_path):
    """Users may save game INIs as UTF-8, with a BOM even - we read their
    settings, but flag those that are not cp1252 as corrupted, and keep the
    bytes we cannot decode as they are when writing them back."""
    bom_ini = _game_ini(tmp_path / 'bom',
                        main=codecs.BOM_UTF8 + b'[General]\nsLanguage=fr\n')
    assert bom_ini.get_ini_language(SteamStarfieldGameInfo) == 'fr'
    assert not bom_ini.isCorrupted
    comment = '; Отключаем вступление'.encode('utf-8') # has an 0x81 byte
    utf8_ini = _game_ini(tmp_path / 'utf8',
                         main=b'[General]\n%s\nsLanguage=pl\n' % comment)
    assert utf8_ini.get_ini_language(SteamStarfieldGameInfo) == 'pl'
    assert utf8_ini.isCorrupted
    utf8_ini.saveSetting('General', 'sIntroSequence', '')
    assert {comment, b'sLanguage=pl', b'sIntroSequence='} <= {*map(bytes.strip,
        (tmp_path / 'utf8' / 'main.ini').read_bytes().splitlines())}
    # a cp1252 INI with a stray undefined byte
    stray_ini = _game_ini(tmp_path / 'stray',
                          main=b'[General]\n; caf\xe9 \x81\nsLanguage=it\n')
    assert stray_ini.get_ini_language(SteamStarfieldGameInfo) == 'it'

def test_sf_bsas_from_inis(tmp_path):
    """Starfield's vanilla archive lists are in its main INI, Starfield.ini,
    StarfieldCustom.ini overrides them key by key."""
    game_ini = _game_ini(tmp_path / 'inis',
        main='[Archive]\nsResourceStartUpArchiveList=Starfield - '
             'Localization.ba2, BlueprintShips-Starfield - Localization.ba2'
             '\nsResourceArchiveList=Starfield - Misc.ba2, Old.ba2\n'
             'sResourceEnglishVoiceList=Starfield - Voices01.ba2\n',
        custom='[Archive]\nsResourceArchiveList=Starfield - Misc.ba2\n'
               'sResourceArchiveList2=Mod - Main.ba2\n')
    class _Bsa:
        def __init__(self, bsa_name): self.fn_key = FName(bsa_name)
    av_bsas = FNDict((b, _Bsa(b)) for b in ('Starfield - Localization.ba2',
        'BlueprintShips-Starfield - Localization.ba2', 'Starfield - Misc.ba2',
        'Old.ba2', 'Mod - Main.ba2', 'Starfield - Voices01.ba2',
        'Unlisted.ba2'))
    bsa_lo = SteamStarfieldGameInfo.Ini.get_bsas_from_inis(av_bsas,
        *game_ini.setting_inis)
    assert {str(b.fn_key): b.lo_src for b in bsa_lo} == {
        'Starfield - Localization.ba2':
            'Loaded from: main.ini (sResourceStartUpArchiveList)',
        'BlueprintShips-Starfield - Localization.ba2':
            'Loaded from: main.ini (sResourceStartUpArchiveList)',
        'Starfield - Misc.ba2':
            'Loaded from: custom.ini (sResourceArchiveList)',
        'Mod - Main.ba2': 'Loaded from: custom.ini (sResourceArchiveList2)',
        'Starfield - Voices01.ba2':
            'Loaded from: main.ini (sResourceEnglishVoiceList)'}
    # The INI-loaded BSAs are taken out of the available ones
    assert [*av_bsas] == ['Old.ba2', 'Unlisted.ba2']
    # The missing strings check looks in the Localization BA2s first
    sf_bsa = SteamStarfieldGameInfo.Bsa
    hi_to_lo = sorted(bsa_lo, key=lambda b: sf_bsa.heuristic_sort_key(b,
                                                                      bsa_lo))
    assert {str(b.fn_key) for b in hi_to_lo[:2]} == {
        'Starfield - Localization.ba2',
        'BlueprintShips-Starfield - Localization.ba2'}
