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
"""A parser and minimally invasive writer for all kinds of INI files and
related formats (e.g. simple TOML files)."""
from __future__ import annotations

import os
import re
from collections import Counter

# Keep local imports to a minimum, this module is important for booting!
from .bolt import DefaultLowerDict, ListInfo, LowerDict, decoder, deprint, \
    getbestencoding, AFileInfo
# We may end up getting run very early in boot, make sure _() never breaks us
from .bolt import failsafe_underscore as _
from .exception import FailedIniInferError
from .wbtemp import TempFile

_h = r'[^\S\r\n]*' # Perl's \h (horizontal whitespace) sorely missed

# All extensions supported by this parser
supported_ini_exts = {'.ini', '.cfg', '.toml'}

def get_ini_type_and_encoding(abs_ini_path, *, fallback_type=None,
        consider_obse_inis=False) -> tuple[type[IniFileInfo], str]:
    """Return ini type (one of IniFileInfo, OBSEIniFile) and inferred encoding
    of the file at abs_ini_path. It reads the file and performs heuristics
    for detecting the encoding, then decodes and applies regexes to every
    line to detect the ini type. Those operations are somewhat expensive, so
    it would make sense to pass an encoding in, if we know that the ini file
    must have a specific encoding (for instance the game ini files that
    reportedly must be cp1252). More investigation needed.

    :param abs_ini_path: The full path to the INI file in question.
    :param fallback_type: If set, then if the INI type can't be detected,
        instead of raising an error, use this type.
    :param consider_obse_inis: Whether to consider OBSE INIs as well. If True,
        some empty/fully commented-out INIs can't be parsed properly. If False,
        OBSE INIs can't be parsed."""
    if os.path.splitext(abs_ini_path)[1] == '.toml':
        # TOML must always use UTF-8, demanded by its specification
        return TomlFile, 'utf-8'
    with open(abs_ini_path, u'rb') as ini_file:
        content = ini_file.read()
    detected_encoding, _confidence = getbestencoding(content)
    # If we don't have to worry about OBSE INIs, just the encoding suffices
    if not consider_obse_inis:
        return IniFileInfo, detected_encoding
    ##: Add a 'return encoding' param to decoder to avoid the potential double
    # chardet here!
    decoded_content = decoder(content, detected_encoding)
    inferred_ini_type = _scan_ini(lines := decoded_content.splitlines())
    if inferred_ini_type is not None:
        return inferred_ini_type, detected_encoding
    # Empty file/entirely comments or we failed to parse any line - try
    # again, considering commented out lines that match the INI format too
    inferred_ini_type = _scan_ini(lines, scan_comments=True)
    if inferred_ini_type is not None:
        return inferred_ini_type, detected_encoding
    # No settings even in the comments - if we have a fallback type, use that
    if fallback_type is not None:
        return fallback_type, detected_encoding
    raise FailedIniInferError(abs_ini_path)

def _scan_ini(lines, scan_comments=False):
    count = Counter()
    for ini_type in (IniFileInfo, OBSEIniFile):
        for line in lines:
            if ini_type.parse_ini_line(line, analyze_comments=scan_comments)[0]:
                count[ini_type] += 1
    return count.most_common(1)[0][0] if count else None

class AIniInfo(ListInfo):
    """ListInfo displayed on the ini tab - currently default tweaks or
    ini files, either standard or xSE ones."""
    _comments_start = ('#', ';') # we read both characters as comment starters
    reSetting = re.compile(fr'^(\w+?){_h}={_h}(.*?)({_h}[;#].*)?$')
    out_encoding = 'cp1252' # when opening a file for writing force cp1252
    defaultSection = u'General'
    # The comment character to use when writing new comments into this file
    _comment_char = ';'

    def __init__(self, filekey):
        ListInfo.__init__(self, filekey)
        self._deleted_cache = LowerDict()

    def getSetting(self, section, key, default):
        """Gets a single setting from the file."""
        try:
            return self.get_ci_settings()[section][key][0]
        except KeyError:
            return default

    def get_setting_values(self, section, default):
        """Returns a dictionary mapping keys to values for the specified
        section, falling back to the specified default value if the section
        does not exist."""
        try:
            return self.get_ci_settings()[section]
        except KeyError:
            return default

    # Abstract API - getting settings varies depending on if we are an ini
    # file or a hardcoded default tweak
    def get_ci_settings(self, with_deleted=False):
        """Populate and return cached settings - if not just reading them
        do a copy first !"""
        raise NotImplementedError

    def read_ini_content(self, as_unicode=True) -> list[str] | bytes:
        """Return a list of the decoded lines in the ini file, if as_unicode
        is True, or the raw bytes in the ini file, if as_unicode is False.
        Note we strip line endings at the end of the line in unicode mode."""
        raise NotImplementedError

    def analyse_tweak(self, tweak_inf):
        """Analyse the tweak lines based on self settings. Return a
        list of line info tuples in this format:
        [(fulltext, section, setting, value, status, ini_line_number, deleted)]
        where:
        fulltext = full line of text from the ini with newline characters
        stripped from the end
        section = the section that is being edited
        setting = the setting that is being edited
        value = the value the setting is being set to
        status:
            -10: doesn't exist in the ini
              0: does exist, but it's a heading or something else without a value
             10: does exist, but value isn't the same
             20: does exist, and value is the same
        ini_line_number = line number in the ini that this tweak applies to
        deleted: deleted setting"""
        lines = []
        ci_settings, ci_del_settings = self.get_ci_settings(with_deleted=True)
        #--Read ini file
        section = self.__class__.defaultSection #doesn't matter for OBSEIniFile
        for line in tweak_inf.read_ini_content():
            status = 0
            lineNo = -1
            stripped, setting, val, new_section, is_del = \
                self.parse_ini_line(line, parse_value=True)
            if setting: # for IniFile if setting is True, new_section is None
                section = new_section or section
                try:
                    self_val, lineNo = ci_settings[section][setting]
                    status = 10 if is_del or self_val != val else 20
                except KeyError:
                    try:
                        lineNo = ci_del_settings[section][setting][1]
                        status = 20 if is_del else -10
                    except KeyError: # not present or deleted
                        if not is_del: # else 0 (treat it as a comment)
                            status = -10
            elif new_section: # for OBSEIniFile True only if bool(setting)=True
                if (section := new_section) not in ci_settings:
                    status = -10
            elif stripped: # not a section/setting/line comment but not empty
                status = -10
            lines.append((line, section, setting, val, status, lineNo, is_del))
        return lines

    @classmethod
    def parse_ini_line(cls, whole_line, *, inline_comments=False,
                       parse_value=False, analyze_comments=False):
        lstripped = whole_line.lstrip()
        # deleted settings are comments with a dash after the comment character
        is_del = False
        try:
            if lstripped[0] in cls._comments_start:
                if lstripped[1] == '-':
                    is_del = True
                    lstripped = lstripped[2:].lstrip() if analyze_comments \
                        else lstripped[2:] # del settings dont start with space
                else: # a full line comment
                    lstripped = lstripped[1:].lstrip() if analyze_comments \
                        else ''
        except IndexError: # empty or a single comment character
            lstripped = ''
        return cls._parse_setting(lstripped, is_del, inline_comments,
                                  parse_value)

    @classmethod
    def _parse_setting(cls, lstripped, is_del, parse_comments, parse_value, *,
                       __re_section=re.compile(fr'^\[{_h}(.+?){_h}\]$')):
        # stripped, setting, value, section, del_sett
        if not lstripped:
            return '', None, None, None, False
        stripped = lstripped.rstrip()  # can't be empty
        if ma_setting := cls.reSetting.match(stripped):
            val = cls._parse_value(ma_setting.group(2)) if parse_value else \
                ma_setting.group(2)
            val = (val, ma_setting.group(3)) if parse_comments else val
            return stripped, ma_setting.group(1), val, None, is_del
        elif ma_section := __re_section.match(stripped):
            return stripped, None, None, ma_section.group(1), False
        return '', None, None, None, False

    @staticmethod
    def _parse_value(value):
        """Return a parsed version of the specified setting value. Just strips
        whitespace by default."""
        return value.strip()

class IniFileInfo(AIniInfo, AFileInfo):
    """Any old ini file."""
    __empty_settings = LowerDict()
    _ci_settings_cache_linenum = __empty_settings

    def __init__(self, fullpath, ini_encoding):
        super(AIniInfo, self).__init__(fullpath)
        AIniInfo.__init__(self, fullpath.stail) # calls ListInfo.__init__ again
        self.ini_encoding = ini_encoding
        self.isCorrupted = u''
        #--Settings cache
        self._deleted = False
        self.updated = False # notify iniInfos which should clear this flag

    # AFile overrides ---------------------------------------------------------
    def do_update(self, raise_on_error=False, **kwargs):
        try:
            # do_update will return True if the file was deleted then restored
            self.updated |= super().do_update(raise_on_error=True)
            if self._deleted: # restored
                self._deleted = False
            return self.updated
        except OSError:
            # check if we already know it's deleted (used for main game ini)
            update = not self._deleted
            if update:
                # mark as deleted to avoid requesting updates on each refresh
                self._deleted = self.updated = True
            if raise_on_error: raise
            return update

    def _reset_cache(self, stat_tuple, **kwargs):
        super()._reset_cache(stat_tuple, **kwargs)
        self._ci_settings_cache_linenum = self.__empty_settings

    # AIniInfo overrides ------------------------------------------------------
    def read_ini_content(self, as_unicode=True, missing_ok=False):
        try:
            with open(self.abs_path, mode='rb') as f:
                content = f.read()
            if not as_unicode: return content
            decoded = str(content, self.ini_encoding)
            return decoded.splitlines(False) # keepends=False
        except UnicodeDecodeError:
            deprint(f'Failed to decode {self.abs_path} using '
                    f'{self.ini_encoding}', traceback=True)
        except FileNotFoundError:
            if not missing_ok:
                deprint(f'INI file {self.abs_path} missing when we tried '
                        f'reading it', traceback=True)
        except OSError:
            deprint(f'Error reading ini file {self.abs_path}', traceback=True)
        return []

    def get_ci_settings(self, with_deleted=False, *, missing_ok=False):
        """Return cached settings as LD[LD] of section -> (setting -> value).
        Keys in both levels are case insensitive. Values are stripped of
        whitespace. If you modify them do a copy first !"""
        try:
            if self._ci_settings_cache_linenum is self.__empty_settings \
                    or self.do_update(raise_on_error=True):
                try:
                    ci_settings = LowerDict()
                    ci_deleted_settings = LowerDict()
                    self.isCorrupted = ''
                    #--Read ini file
                    section = None
                    for i, line in enumerate(self.read_ini_content(
                            missing_ok=missing_ok)):
                        _strip, setting, val, new_section, is_del = \
                            self.parse_ini_line(line, parse_value=True)
                        if setting: # OBSEIni has `new_section` if setting=True
                            section = new_section or section
                            if is_del:
                                if not section: continue #treat it as a comment
                                settings_dict = ci_deleted_settings
                            else: settings_dict = ci_settings
                            try:
                                settings_dict[section][setting] = (val, i)
                            except KeyError:
                                if not section: # can't happen for OBSEIniFile
                                    self.isCorrupted = _("Your %(tweak_ini)s "
                                        "should begin with a section header "
                                        "(e.g. '[General]'), but it does not."
                                    ) % {'tweak_ini': self.abs_path}
                                    section = self.__class__.defaultSection
                                settings_dict[section] = LowerDict(
                                    [(setting, (val, i))])
                        elif new_section: # we got a section
                            section = new_section
                    self._ci_settings_cache_linenum, self._deleted_cache = \
                        ci_settings, ci_deleted_settings
                except UnicodeDecodeError as e:
                    msg = _('The INI file %(ini_full_path)s seems to have '
                            'unencodable characters:')
                    msg = f'{msg}\n\n{e}' % {'ini_full_path': self.abs_path}
                    self.isCorrupted = msg
                    return ({}, {}) if with_deleted else {}
        except OSError:
            return ({}, {}) if with_deleted else {}
        if with_deleted:
            return self._ci_settings_cache_linenum, self._deleted_cache
        return self._ci_settings_cache_linenum

    # Modify ini file ---------------------------------------------------------
    def _open_for_writing(self, temp_path): # preserve windows EOL
        """Write to ourselves respecting windows newlines and out_encoding.
        Note content to be writen (if coming from ini tweaks) must be encodable
        to out_encoding. temp_path must point to some temporary file created
        via TempFile or similar API."""
        return open(temp_path, 'w', encoding=self.out_encoding)

    def target_ini_exists(self, msg=None):
        return self.abs_path.is_file()

    def saveSettings(self, ini_settings, deleted_settings=None, *,
                     skip_sections=frozenset(), line_fmt=False):
        """Apply dictionary of settings to ini file. Leaf values in settings
        dictionary can be full ini lines, actual values or (value, comment)
        tuples, specifying an inline comment. Sections in skip_sections will
        be replaced with the values in ini_settings if given else removed."""
        ini_settings = LowerDict(
            (x1, LowerDict(y1)) for x1, y1 in ini_settings.items())
        deleted_settings = LowerDict((x, y) for x, y in
                                     (deleted_settings or {}).items())
        section = None
        with TempFile() as tmp_ini_path:
            with self._open_for_writing(tmp_ini_path) as tmp_ini:
                def _add_remaining_new_items(section_setts=None):
                    section_setts = ini_settings.pop(section, {}) \
                        if section_setts is None else section_setts
                    for sett, val in section_setts.items():
                        line = val if line_fmt else self.fmt_setting(sett, val)
                        tmp_ini.write(f'{line}\n')
                skip = False
                # We may have to create the file
                for line in self.read_ini_content(missing_ok=True):
                    stripped, setting, val, new_section, is_del = \
                        self.parse_ini_line(line, inline_comments=True)
                    if setting: # modify? we need be in a section
                        sect = new_section or section
                        try: # Check if we have a value for this setting
                            value = ini_settings[sect].pop(setting) # KeyError
                            # preserve the comment if we don't pass one in
                            line = value if line_fmt else self.fmt_setting(
                                setting, value, new_section,
                                comment=(val[1] or ''))
                        except KeyError:
                            # Check if was enabled and we want to delete it. We
                            # only delete existing settings by commenting out
                            if not is_del and (sect in deleted_settings
                                    and setting in deleted_settings[sect]):
                                # we remove all indentation/trailing spaces
                                line = f'{self._comment_char}-{stripped}'
                    elif new_section: # we never enter this block for OBSEIni
                        # 'new' entries still to be added from previous section
                        _add_remaining_new_items()
                        if section is not None:
                            tmp_ini.write('\n') # newline between sections
                        section = new_section # _add_remaining uses the section
                        if skip := section.lower() in skip_sections:
                            if section in ini_settings:
                                tmp_ini.write(f'{line}\n')
                    if not skip:
                        tmp_ini.write(f'{line}\n')
                # This will occur for the last INI section in the ini file
                _add_remaining_new_items()
                # Add remaining new entries that were not in the ini file
                for sect, sectionSettings in ini_settings.items():
                    if sectionSettings and not isinstance(self, OBSEIniFile):
                        if section is not None:
                            tmp_ini.write('\n') #separate section from previous
                        section = sect
                        tmp_ini.write(f'[{sect}]\n')
                    _add_remaining_new_items(sectionSettings)
            self.abs_path.replace_with_temp(tmp_ini_path)

    @classmethod
    def fmt_setting(cls, setting, value, section=None, comment=''):
        """Format a key-value setting appropriately for the current INI
        format."""
        if isinstance(value, tuple): # takes precedence over comment
            value, comment = value
        if comment:
            comment = f' {cls._comment_char} {comment}'
        return f'{setting}={value}{comment}'

    def apply_tweak(self, tweak_inf):
        """Create dictionaries of updated/new and deleted settings mapped to
        the lines of the tweak to pass to saveSettings."""
        ini_settings = DefaultLowerDict(LowerDict)
        deleted_settings = DefaultLowerDict(LowerDict)
        section = None
        for line in tweak_inf.read_ini_content():
            _strip, setting, _val, new_section, is_del = self.parse_ini_line(
                line)
            if not (section := new_section or section):
                continue # skip if we don't have a section
            if setting:
                # Save the whole ini line for applying (replacing the setting)
                (deleted_settings if is_del else ini_settings)[section][
                    setting] = line # if is_del `line` is ignored
        self.saveSettings(ini_settings, deleted_settings, line_fmt=True)
        return True

class TomlFile(IniFileInfo):
    """A TOML file. Encoding is always UTF-8 (demanded by spec). Note that
    ini_files only supports INI-like TOML files right now. That means TOML
    files must be tables of key-value pairs and the values may not be arrays or
    inline tables. Multi-line strings, escapes inside strings and any of the
    weird date/time values are also not supported yet."""
    out_encoding = 'utf-8' # see above
    _comments_start = ('#',)
    reSetting = re.compile(
        fr'^(.+?)' # Key on the left side --> group 1
        fr'{_h}={_h}(' # Equal sign --> start group 2
        fr'"[^"]+?"|' # Strings
        fr"'[^']+?'|" # Literal strings
        fr'[+-]?[\d_]+|' # Ints
        fr'0b[01_]+|' # Binary ints
        fr'0o[01234567_]+|' # Octal ints
        fr'0x[\dabcdefABCDEF_]+|' # Hexadecimal ints
        fr'[+-]?[\d_]+(?:\.[\d_]+)?(?:[eE][+-]?[\d_]+)?|' # Floats
        fr'[+-]?(?:nan|inf)|' # Special floats
        fr'true|false' # Booleans (lowercase only) --> end group 2
        fr')({_h}#.*)?$') # Inline comment --> group 3
    _comment_char = '#'

    @classmethod
    def fmt_setting(cls, setting, value, section=None, comment=''):
        # If we're given a specific comment, use that (and format it nicely)
        if isinstance(value, tuple): # takes precedence over comment
            value, comment = value
        if comment:
            comment = f' {cls._comment_char} {comment}'
        if isinstance(value, str):
            value = f"'{value}'" # Prefer formatting with literal strings
        elif isinstance(value, (int, float)):
            value = str(value)
        elif isinstance(value, bool):
            value = str(value).lower()
        return f'{setting} = {value}{comment}'

    @staticmethod
    def _parse_value(value):
        if value.startswith(('"', "'")):
            return value[1:-1] # Drop the string's quotes
        try:
            # Valid base 10 ints pass float() too, so this must go first
            return int(value, base=0)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                if value in ('true', 'false'):
                    return value == 'true'
        raise ValueError(f"Cannot parse TOML value '{value}' (yet)")

_h_req = r'[^\S\r\n]+' # required horizontal whitespace
class OBSEIniFile(IniFileInfo):
    """OBSE Configuration ini file.  Minimal support provided, only can
    handle 'set', 'setGS', and 'SetNumericGameSetting' statements."""
    reSetting = None # not used
    _xse_regexes = {f']set[': (re.compile(
         fr'set{_h_req}(.+?){_h_req}to{_h_req}(.*)', re.I), 'set %s to %s')}
    out_encoding = 'utf-8' # we would very much wish so
    _xse_regexes.update({f']{k}[':
        (re.compile(fr'{k}{_h_req}(.+?){_h_req}(.*)', re.I), f'{k} %s %s')
        for k in ('setGS', 'SetNumericGameSetting')})
    ci_pseudosections = LowerDict((f'{k[1:-1]}', k) for k in _xse_regexes)

    def getSetting(self, section, key, default):
        section = self.ci_pseudosections.get(section, section)
        return super(OBSEIniFile, self).getSetting(section, key, default)

    def get_setting_values(self, section, default):
        section = self.ci_pseudosections.get(section, section)
        return super().get_setting_values(section, default)

    @classmethod
    def _parse_setting(cls, line, is_del, parse_comments, parse_value, *,
            __re_comment=re.compile('[#;].*')): # only keep `;` here?
        stripped = __re_comment.sub('', line).rstrip() # for inline comments
        for sectionKey, (regex, _fmt_str) in cls._xse_regexes.items():
            if ma_obse := regex.match(stripped):
                val = cls._parse_value(ma_obse.group(2)) if parse_value else \
                    ma_obse.group(2)
                return stripped, ma_obse.group(1), val, sectionKey, is_del
        return '', None, None, None, False

    @classmethod
    def fmt_setting(cls, setting, value, section=None, comment=''):
        if isinstance(value, bytes): # huh?
            raise RuntimeError('Do not pass bytes into saveSettings!')
        if isinstance(value, tuple):
            raise RuntimeError('OBSE INIs do not support writing inline '
                               'comments yet')
        else:
            line = cls._xse_regexes[section][1] % (setting, value)
        return line

class GameIni(IniFileInfo):
    """Main game ini file. Only use to instantiate bosh.oblivionIni"""
    _ini_language: str | None = None

    def saveSetting(self,section,key,value):
        """Changes a single setting in the file."""
        ini_settings = {section:{key:value}}
        self.saveSettings(ini_settings)

    def get_ini_language(self, default_lang: str, cached=True) -> str:
        if not cached or self._ini_language is None:
            self._ini_language = self.getSetting('General', 'sLanguage',
                default_lang)
        return self._ini_language

    def target_ini_exists(self, msg=None):
        """Attempt to create the game ini in some scenarios"""
        if msg is None:
            msg = _(u'The game INI must exist to apply a tweak to it.')
        target_exists = super(GameIni, self).target_ini_exists()
        if target_exists: return True
        msg = _('%(ini_full_path)s does not exist.') % {
            'ini_full_path': self.abs_path} + f'\n\n{msg}\n\n'
        return msg
