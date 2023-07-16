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
import os
import re
import time
from collections import Counter, OrderedDict

from . import bush, env
from .bass import dirs
from .bolt import AFile, CIstr, DefaultLowerDict, ListInfo, LowerDict, \
    OrderedLowerDict, decoder, deprint, getbestencoding
from .exception import CancelError, FailedIniInferError, SkipError

_comment_start_re = re.compile(r'^[^\S\r\n]*[;#][^\S\r\n]*')

# All extensions supported by this parser
supported_ini_exts = {'.ini', '.cfg', '.toml'}

def _to_lower(ini_settings):
    """Transforms dict of dict to LowerDict of LowerDict, respecting
    OrdererdDicts if they're used."""
    def _mk_dict(input_dict):
        ret_type = OrderedLowerDict if isinstance(input_dict,
                                                  OrderedDict) else LowerDict
        return ret_type(input_dict)
    return LowerDict((x, _mk_dict(y)) for x, y in ini_settings.items())

def get_ini_type_and_encoding(abs_ini_path, fallback_type=None):
    """Return ini type (one of IniFile, OBSEIniFile) and inferred encoding
    of the file at abs_ini_path. It reads the file and performs heuristics
    for detecting the encoding, then decodes and applies regexes to every
    line to detect the ini type. Those operations are somewhat expensive, so
    it would make sense to pass an encoding in, if we know that the ini file
    must have a specific encoding (for instance the game ini files that
    reportedly must be cp1252). More investigation needed.

    :param abs_ini_path: The full path to the INI file in question.
    :param fallback_type: If set, then if the INI type can't be detected,
        instead of raising an error, use this type."""
    if os.path.splitext(abs_ini_path)[1] == '.toml':
        # TOML must always use UTF-8, demanded by its specification
        return TomlFile, 'utf-8'
    with open(abs_ini_path, u'rb') as ini_file:
        content = ini_file.read()
    detected_encoding, _confidence = getbestencoding(content)
    # If the game does not have OBSE INIs, just the encoding suffices
    if not bush.game.Ini.has_obse_inis:
        return IniFile, detected_encoding
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
    for ini_type in (IniFile, OBSEIniFile):
        comment_re = _comment_start_re if scan_comments else ini_type.reComment
        for line in lines:
            line_stripped = comment_re.sub('', line).strip()
            if not line_stripped:
                continue # No need to try matching an empty string
            for ini_format_re in ini_type.formatRes:
                if ini_format_re.match(line_stripped):
                    count[ini_type] += 1
                    break
    return count.most_common(1)[0][0] if count else None

class AIniFile(ListInfo):
    """ListInfo displayed on the ini tab - currently default tweaks or
    ini files, either standard or xSE ones."""
    reComment = re.compile('[;#].*')
    # These are horrible - Perl's \h (horizontal whitespace) sorely missed
    reDeletedSetting = re.compile(r'^[^\S\r\n]*[;#]-[^\S\r\n]*(\w.*?)'
                                  r'[^\S\r\n]*([;#].*$|=.*$|$)')
    reSection = re.compile(r'^\[[^\S\r\n]*(.+?)[^\S\r\n]*\]$')
    reSetting = re.compile(r'^[^\S\r\n]*(.+?)[^\S\r\n]*=[^\S\r\n]*(.*?)'
                           r'([^\S\r\n]*[;#].*)?$')
    formatRes = (reSetting, reSection)
    out_encoding = 'cp1252' # when opening a file for writing force cp1252
    defaultSection = u'General'
    # The comment character to use when writing new comments into this file
    _comment_char = ';'

    def __init__(self, filekey):
        ListInfo.__init__(self, filekey)
        self._deleted_cache = LowerDict()

    def has_setting(self, section, key):
        """Returns True if this INI file has the specified section and key."""
        ci_temp = self.get_ci_settings()
        return section in ci_temp and key in ci_temp[section]

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
    # file or a hardcoded default tweak, and what kind of ini file we are
    def get_ci_settings(self, with_deleted=False):
        """Populate and return cached settings - if not just reading them
        do a copy first !"""
        raise NotImplementedError

    def _get_ci_settings(self, tweakPath):
        """Get settings as defaultdict[dict] of section -> (setting -> value).
        Keys in both levels are case insensitive. Values are stripped of
        whitespace. "deleted settings" keep line number instead of value (?)
        Only used in get_ci_settings should be bypassed for DefaultIniFile.
        :rtype: tuple(DefaultLowerDict[bolt.LowerDict], DefaultLowerDict[
        bolt.LowerDict], boolean)
        """
        raise NotImplementedError

    def read_ini_content(self, as_unicode=True):
        """Return a list of the decoded lines in the ini file, if as_unicode
        is True, or the raw bytes in the ini file, if as_unicode is False.
        Note we strip line endings at the end of the line in unicode mode.
        :rtype: list[str]|bytes"""
        raise NotImplementedError

    def analyse_tweak(self, tweak_file):
        """Analyse the tweak lines based on self settings and type. Return a
        list of line info tuples in this format:
        [(fulltext,section,setting,value,status,ini_line_number, deleted)]
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
        deleted: deleted line (?)"""
        lines = []
        ci_settings, ci_deletedSettings = self.get_ci_settings(with_deleted=True)
        reComment = self.reComment
        reSection = self.reSection
        reDeleted = self.reDeletedSetting
        reSetting = self.reSetting
        #--Read ini file
        section = self.__class__.defaultSection
        for i, line in enumerate(tweak_file.read_ini_content()):
            maDeletedSetting = reDeleted.match(line)
            maSection = reSection.match(line)
            maSetting = reSetting.match(line)
            deleted = False
            setting = None
            value = u''
            status = 0
            lineNo = -1
            if maSection:
                section = maSection.group(1)
                if section not in ci_settings:
                    status = -10
            elif maSetting:
                if section in ci_settings:
                    setting = maSetting.group(1)
                    if setting in ci_settings[section]:
                        value = maSetting.group(2).strip()
                        lineNo = ci_settings[section][setting][1]
                        if ci_settings[section][setting][0] == value:
                            status = 20
                        else:
                            status = 10
                    else:
                        status = -10
                else:
                    status = -10
            elif maDeletedSetting:
                setting = maDeletedSetting.group(1)
                status = 20
                if section in ci_settings and setting in ci_settings[section]:
                    lineNo = ci_settings[section][setting][1]
                    status = 10
                elif section in ci_deletedSettings and setting in ci_deletedSettings[section]:
                    lineNo = ci_deletedSettings[section][setting]
                deleted = True
            else:
                if reComment.sub('', line).strip():
                    status = -10
            lines.append((line, section, setting, value, status, lineNo,
                          deleted))
        return lines

class IniFile(AIniFile, AFile):
    """Any old ini file."""
    __empty_settings = LowerDict()
    _ci_settings_cache_linenum = __empty_settings

    def __init__(self, fullpath, ini_encoding):
        super(ListInfo, self).__init__(fullpath)
        ListInfo.__init__(self, fullpath.stail)
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

    # AIniFile overrides ------------------------------------------------------
    def read_ini_content(self, as_unicode=True):
        """Return a list of the decoded lines in the ini file, if as_unicode
        is True, or the raw bytes in the ini file, if as_unicode is False.
        Note we strip line endings at the end of the line in unicode mode.
        :rtype: list[str]|bytes"""
        try:
            with self.abs_path.open(u'rb') as f:
                content = f.read()
            if not as_unicode: return content
            decoded = str(content, self.ini_encoding)
            return decoded.splitlines(False) # keepends=False
        except UnicodeDecodeError:
            deprint(f'Failed to decode {self.abs_path} using '
                    f'{self.ini_encoding}', traceback=True)
        except OSError:
            deprint(f'Error reading ini file {self.abs_path}', traceback=True)
        return []

    def get_ci_settings(self, with_deleted=False):
        """Populate and return cached settings - if not just reading them
        do a copy first !"""
        try:
            if self._ci_settings_cache_linenum is self.__empty_settings \
                    or self.do_update(raise_on_error=True):
                try:
                    self._ci_settings_cache_linenum, self._deleted_cache, \
                        self.isCorrupted = self._get_ci_settings(self.abs_path)
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

    def _get_ci_settings(self, tweakPath):
        """Get settings as defaultdict[dict] of section -> (setting -> value).
        Keys in both levels are case insensitive. Values are stripped of
        whitespace. "deleted settings" keep line number instead of value (?)
        Only used in get_ci_settings should be bypassed for DefaultIniFile.
        :rtype: tuple(DefaultLowerDict[bolt.LowerDict], DefaultLowerDict[
        bolt.LowerDict], boolean)
        """
        ci_settings = DefaultLowerDict(LowerDict)
        ci_deleted_settings = DefaultLowerDict(LowerDict)
        default_section = self.__class__.defaultSection
        isCorrupted = u''
        reSection = self.__class__.reSection
        reDeleted = self.__class__.reDeletedSetting
        reSetting = self.__class__.reSetting
        #--Read ini file
        sectionSettings = None
        section = None
        for i, line in enumerate(self.read_ini_content()):
            maSection = reSection.match(line)
            maDeleted = reDeleted.match(line)
            maSetting = reSetting.match(line)
            if maSection:
                section = maSection.group(1)
                sectionSettings = ci_settings[section]
            elif maSetting:
                if sectionSettings is None:
                    sectionSettings = ci_settings[default_section]
                    msg = _("Your %(tweak_ini)s should begin with a section "
                            "header (e.g. '[General]'), but it does not.")
                    isCorrupted = msg % {'tweak_ini': tweakPath}
                sectionSettings[maSetting.group(1)] = (
                    maSetting.group(2).strip(), i)
            elif maDeleted:
                if not section: continue
                ci_deleted_settings[section][maDeleted.group(1)] = i
        return ci_settings, ci_deleted_settings, isCorrupted

    # Modify ini file ---------------------------------------------------------
    def _open_for_writing(self): # preserve windows EOL
        """Write to ourselves respecting windows newlines and out_encoding.
        Note content to be writen (if coming from ini tweaks) must be encodable
        to out_encoding."""
        return open(self.abs_path.temp, u'w', encoding=self.out_encoding)

    def target_ini_exists(self, msg=_(
        u'The target ini must exist to apply a tweak to it.')):
        return self.abs_path.is_file()

    def saveSettings(self, ini_settings, deleted_settings=None):
        """Apply dictionary of settings to ini file, latter must exist!
        Values in settings dictionary must be actual (setting, value) pairs."""
        ini_settings = _to_lower(ini_settings)
        deleted_settings = LowerDict((x, {CIstr(u) for u in y}) for x, y in
                                     (deleted_settings or {}).items())
        reDeleted = self.reDeletedSetting
        reSection = self.reSection
        reSetting = self.reSetting
        #--Read init, write temp
        section = None
        sectionSettings = {}
        with self._open_for_writing() as tmp_ini:
            def _add_remaining_new_items():
                if section in ini_settings: del ini_settings[section]
                if not sectionSettings: return
                for sett, val in sectionSettings.items():
                    tmp_ini.write(f'{self._fmt_setting(sett, val)}\n')
                tmp_ini.write('\n')
            for line in self.read_ini_content(as_unicode=True):
                maSection = reSection.match(line)
                if maSection:
                    # 'new' entries still to be added from previous section
                    _add_remaining_new_items()
                    section = maSection.group(1)  # entering new section
                    sectionSettings = ini_settings.get(section, {})
                else:
                    match_set = reSetting.match(line)
                    match_del = reDeleted.match(line)
                    if match := (match_set or match_del):
                        ##: What about inline comments in deleted lines?
                        comment = match_set.group(3) if match_set else ''
                        setting = match.group(1)
                        if setting in sectionSettings:
                            value = sectionSettings[setting]
                            line = self._fmt_setting(setting, value)
                            if comment:
                                line += comment # preserve inline comments
                            del sectionSettings[setting]
                        elif section in deleted_settings and setting in deleted_settings[section]:
                            line = f'{self._comment_char}-{line}'
                tmp_ini.write(f'{line}\n')
            # This will occur for the last INI section in the ini file
            _add_remaining_new_items()
            # Add remaining new entries
            for section, sectionSettings in list(ini_settings.items()):
                # _add_remaining_new_items may modify ini_settings
                if sectionSettings:
                    tmp_ini.write(f'[{section}]\n')
                    _add_remaining_new_items()
        #--Done
        self.abs_path.untemp()

    def _fmt_setting(self, setting, value):
        """Format a key-value setting appropriately for the current INI
        format."""
        return f'{setting}={value}'

    def applyTweakFile(self, tweak_lines):
        """Read ini tweak file and apply its settings to self (the target ini).
        """
        reDeleted = self.reDeletedSetting
        reSection = self.reSection
        reSetting = self.reSetting
        #--Read Tweak file
        ini_settings = DefaultLowerDict(LowerDict)
        deleted_settings = DefaultLowerDict(set)
        section = None
        for line in tweak_lines:
            maSection = reSection.match(line)
            maDeleted = reDeleted.match(line)
            maSetting = reSetting.match(line)
            if maSection:
                section = maSection.group(1)
            elif maSetting:
                ini_settings[section][maSetting.group(1)] = maSetting.group(
                    2).strip()
            elif maDeleted:
                deleted_settings[section].add(CIstr(maDeleted.group(1)))
        self.saveSettings(ini_settings,deleted_settings)
        return True

    def remove_section(self, target_section): # type: (str) -> None
        """Removes a section and all its contents from the INI file. Note that
        this will only remove the first matching section. If you want to remove
        multiple, you will have to call this in a loop and check if the section
        still exists after each iteration."""
        re_section = self.reSection
        # Tri-State: If None, we haven't hit the section yet. If True, then
        # we've hit it and are actively removing it. If False, then we've fully
        # removed the section already and should ignore further occurences.
        remove_current = None
        with self._open_for_writing() as out:
            for line in self.read_ini_content(as_unicode=True):
                match_section = re_section.match(line)
                if match_section:
                    section = match_section.group(1)
                    # Check if we need to remove this section
                    if remove_current is None and section.lower() == \
                            target_section.lower():
                        # Yes, so start removing every read line
                        remove_current = True
                    elif remove_current:
                        # We've removed the target section, remember that
                        remove_current = False
                if not remove_current:
                    out.write(line + u'\n')
        self.abs_path.untemp()

class DefaultIniFile(AIniFile):
    """A default ini tweak - hardcoded."""

    def __init__(self, default_ini_name, settings_dict):
        super().__init__(default_ini_name)
        #--Settings cache
        self.lines, current_line = [], 0
        self._ci_settings_cache_linenum = OrderedLowerDict()
        for sect, setts in settings_dict.items():
            self.lines.append(f'[{sect}]')
            self._ci_settings_cache_linenum[sect] = OrderedLowerDict()
            current_line += 1
            for sett, val in setts.items():
                self.lines.append(f'{sett}={val}')
                self._ci_settings_cache_linenum[sect][sett] = (
                    val, current_line)
                current_line += 1

    def get_ci_settings(self, with_deleted=False):
        if with_deleted:
            return self._ci_settings_cache_linenum, self._deleted_cache
        return self._ci_settings_cache_linenum

    def read_ini_content(self, as_unicode=True):
        """Note as_unicode=True strips line endings as opposed to parent -
        this is wanted and does not harm in this case. Note also, the binary
        instantiation of the default ini is with windows EOL."""
        if as_unicode:
            return iter(self.lines) # do not modify return value directly
        # Add a newline at the end of the INI
        return b'\r\n'.join(li.encode('ascii') for li in self.lines) + b'\r\n'

class TomlFile(IniFile):
    """A TOML file. Encoding is always UTF-8 (demanded by spec). Note that
    ini_files only supports INI-like TOML files right now. That means TOML
    files must be tables of key-value pairs and the values may not be arrays or
    inline tables."""
    out_encoding = 'utf-8' # see above
    reComment = re.compile('#.*')
    reDeletedSetting = re.compile(r'^[^\S\r\n]*#-[^\S\r\n]*(\w.*?)[^\S\r\n]*'
                                  r'(#.*$|=.*$|$)')
    reSetting = re.compile(r'^[^\S\r\n]*(.+?)[^\S\r\n]*=[^\S\r\n]*(.+?)'
                           r'([^\S\r\n]*#.*)?$')
    _comment_char = '#'

    def _fmt_setting(self, setting, value):
        return f'{setting} = {value}'

class OBSEIniFile(IniFile):
    """OBSE Configuration ini file.  Minimal support provided, only can
    handle 'set', 'setGS', and 'SetNumericGameSetting' statements."""
    reDeleted = re.compile(r';-(\w.*?)$')
    reSet     = re.compile(r'[^\S\r\n]*set[^\S\r\n]+(.+?)[^\S\r\n]+to'
                           r'[^\S\r\n]+(.*)', re.I)
    reSetGS   = re.compile(r'[^\S\r\n]*setGS[^\S\r\n]+(.+?)[^\S\r\n]+'
                           r'(.*)', re.I)
    reSetNGS  = re.compile(r'[^\S\r\n]*SetNumericGameSetting[^\S\r\n]+(.+?)'
                           r'[^\S\r\n]+(.*)', re.I)
    out_encoding = 'utf-8' # FIXME: ask
    formatRes = (reSet, reSetGS, reSetNGS)
    defaultSection = u'' # Change the default section to something that
    # can't occur in a normal ini

    ci_pseudosections = LowerDict({u'set': u']set[', u'setGS': u']setGS[',
        u'SetNumericGameSetting': u']SetNumericGameSetting['})

    def getSetting(self, section, key, default):
        section = self.ci_pseudosections.get(section, section)
        return super(OBSEIniFile, self).getSetting(section, key, default)

    def get_setting_values(self, section, default):
        section = self.ci_pseudosections.get(section, section)
        return super(OBSEIniFile, self).get_setting_values(section, default)

    _regex_tuples = ((reSet, u']set[', u'set %s to %s'),
      (reSetGS, u']setGS[', u'setGS %s %s'),
      (reSetNGS, u']SetNumericGameSetting[', u'SetNumericGameSetting %s %s'))

    @classmethod
    def _parse_obse_line(cls, line):
        for regex, sectionKey, format_string in cls._regex_tuples:
            match = regex.match(line)
            if match:
                return match, sectionKey, format_string
        return None, None, None

    def _get_ci_settings(self, tweakPath):
        """Get the settings in the ini script."""
        ini_settings = DefaultLowerDict(LowerDict)
        deleted_settings = DefaultLowerDict(LowerDict)
        reDeleted = self.reDeleted
        reComment = self.reComment
        with tweakPath.open(u'r', encoding=self.ini_encoding) as iniFile:
            for i,line in enumerate(iniFile.readlines()):
                maDeleted = reDeleted.match(line)
                if maDeleted:
                    line = maDeleted.group(1)
                    settings_dict = deleted_settings
                else:
                    settings_dict = ini_settings
                stripped = reComment.sub(u'',line).strip()
                match, section_key, _fmt = self._parse_obse_line(stripped)
                if match:
                    settings_dict[section_key][match.group(1)] = match.group(
                        2).strip(), i
        return ini_settings, deleted_settings, False

    def analyse_tweak(self, tweak_file):
        lines = []
        ci_settings, deletedSettings = self.get_ci_settings(with_deleted=True)
        reDeleted = self.reDeleted
        reComment = self.reComment
        for line in tweak_file.read_ini_content():
            # Check for deleted lines
            maDeleted = reDeleted.match(line)
            if maDeleted: stripped = maDeleted.group(1)
            else: stripped = line
            stripped = reComment.sub(u'',stripped).strip()
            # Check which kind it is - 'set' or 'setGS' or 'SetNumericGameSetting'
            match, section, _fmt = self._parse_obse_line(stripped)
            if match:
                groups = match.groups()
            else:
                if stripped:
                    # Some other kind of line
                    lines.append((line, u'', u'', u'', -10, -1, False))
                else:
                    # Just a comment line
                    lines.append((line, u'', u'', u'', 0, -1, False))
                continue
            setting = groups[0].strip()
            value = groups[1].strip()
            lineNo = -1
            if section in ci_settings and setting in ci_settings[section]:
                ini_value, lineNo = ci_settings[section][setting]
                if maDeleted:            status = 10
                elif ini_value == value: status = 20
                else:                    status = 10
            elif section in deletedSettings and setting in deletedSettings[section]:
                _del_value, lineNo = deletedSettings[section][setting]
                if maDeleted: status = 20
                else:         status = 10
            else:
                status = -10
            lines.append((line, section, setting, value, status, lineNo,
                          bool(maDeleted)))
        return lines

    def saveSettings(self, ini_settings, deleted_settings=None):
        """Apply dictionary of settings to self, latter must exist!
        Values in settings dictionary can be either actual values or
        full ini lines ending in newline char."""
        ini_settings = _to_lower(ini_settings)
        deleted_settings = _to_lower(deleted_settings or {})
        reDeleted = self.reDeleted
        reComment = self.reComment
        with self._open_for_writing() as tmpFile:
            # Modify/Delete existing lines
            for line in self.read_ini_content(as_unicode=True):
                # if not line.rstrip(): continue
                # Test if line is currently deleted
                maDeleted = reDeleted.match(line)
                if maDeleted: stripped = maDeleted.group(1)
                else: stripped = line
                # Test what kind of line it is - 'set' or 'setGS' or 'SetNumericGameSetting'
                stripped = reComment.sub(u'', stripped).strip()
                match, section_key, format_string = self._parse_obse_line(
                    stripped)
                if match:
                    setting = match.group(1)
                    # Apply the modification
                    if section_key in ini_settings and setting in ini_settings[section_key]:
                        # Un-delete/modify it
                        value = ini_settings[section_key][setting]
                        del ini_settings[section_key][setting]
                        if isinstance(value, bytes):
                            raise RuntimeError(u'Do not pass bytes into '
                                               u'saveSettings!')
                        if isinstance(value, str) and value[-1:] == u'\n':
                            line = value.rstrip(u'\n\r') # removes just \n too
                        else:
                            line = format_string % (setting, value)
                    elif not maDeleted and section_key in deleted_settings and setting in deleted_settings[section_key]:
                        # It isn't deleted, but we want it deleted
                        line = u';-' + line
                tmpFile.write(line + u'\n')
            # Add new lines
            for sectionKey in ini_settings:
                section = ini_settings[sectionKey]
                for setting in section:
                    tmpFile.write(section[setting])
        self.abs_path.untemp()

    def applyTweakFile(self, tweak_lines):
        reDeleted = self.reDeleted
        reComment = self.reComment
        ini_settings = DefaultLowerDict(LowerDict)
        deleted_settings = DefaultLowerDict(LowerDict)
        for line in tweak_lines:
            # Check for deleted lines
            maDeleted = reDeleted.match(line)
            if maDeleted:
                stripped = maDeleted.group(1)
                settings_ = deleted_settings
            else:
                stripped = line
                settings_ = ini_settings
            # Check which kind of line - 'set' or 'setGS' or 'SetNumericGameSetting'
            stripped = reComment.sub(u'',stripped).strip()
            match, section_key, _fmt = self._parse_obse_line(stripped)
            if match:
                setting = match.group(1)
                # Save the setting for applying
                if line[-1] != u'\n': line += u'\n'
                settings_[section_key][setting] = line
        self.saveSettings(ini_settings,deleted_settings)
        return True

    def remove_section(self, target_section, do_backup=False):
        # type: (str, bool) -> None
        re_comment = self.reComment
        re_section = self.reSection
        # Tri-State: If None, we haven't hit the section yet. If True, then
        # we've hit it and are actively removing it. If False, then we've fully
        # removed the section already and should ignore further occurences.
        remove_current = None
        with self._open_for_writing() as out:
            for line in self.read_ini_content(as_unicode=True):
                stripped = re_comment.sub(u'', line).strip()
                # Try checking if it's an OBSE line first
                _match, section, _fmt = self._parse_obse_line(stripped)
                if not section:
                    # It's not, assume it's a regular line
                    match_section = re_section.match(stripped)
                    section = match_section.group(1) if match_section else u''
                if section:
                    # Check if we need to remove this section
                    if remove_current is None and section.lower() == \
                            target_section.lower():
                        # Yes, so start removing every read line
                        remove_current = True
                    elif remove_current:
                        # We've removed the target section, remember that
                        remove_current = False
                if not remove_current:
                    out.write(line + u'\n')
        self.abs_path.untemp(do_backup)

class GameIni(IniFile):
    """Main game ini file. Only use to instantiate bosh.oblivionIni"""
    bsaRedirectors = {u'archiveinvalidationinvalidated!.bsa',
                      u'..\\obmm\\bsaredirection.bsa'}
    _ini_language = None

    def saveSetting(self,section,key,value):
        """Changes a single setting in the file."""
        ini_settings = {section:{key:value}}
        self.saveSettings(ini_settings)

    def get_ini_language(self, cached=True):
        if not cached or self._ini_language is None:
            self._ini_language = self.getSetting('General', 'sLanguage',
                bush.game.Ini.default_game_lang)
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

    #--BSA Redirection --------------------------------------------------------
    def setBsaRedirection(self,doRedirect=True):
        """Activate or deactivate BSA redirection - game ini must exist!"""
        if self.isCorrupted: return
        br_section, br_key = bush.game.Ini.bsa_redirection_key
        if not br_section or not br_key: return
        aiBsa = dirs[u'mods'].join(u'ArchiveInvalidationInvalidated!.bsa')
        aiBsaMTime = time.mktime((2006, 1, 2, 0, 0, 0, 0, 2, 0))
        if aiBsa.exists() and aiBsa.mtime > aiBsaMTime:
            aiBsa.mtime = aiBsaMTime
        # check if BSA redirection is active
        sArchives = self.getSetting(br_section, br_key, u'')
        is_bsa_redirection_active = any(x for x in sArchives.split(u',')
            if x.strip().lower() in self.bsaRedirectors)
        if doRedirect == is_bsa_redirection_active:
            return
        if doRedirect and not aiBsa.exists():
            source = dirs[u'templates'].join(
                bush.game.template_dir, u'ArchiveInvalidationInvalidated!.bsa')
            source.mtime = aiBsaMTime
            try:
                env.shellCopy({source: aiBsa}, allow_undo=True, auto_rename=True)
            except (PermissionError, CancelError, SkipError):
                return
        sArchives = self.getSetting(br_section, br_key, u'')
        #--Strip existing redirectors out
        archives_ = [x.strip() for x in sArchives.split(u',') if
                     x.strip().lower() not in self.bsaRedirectors]
        #--Add redirector back in?
        if doRedirect:
            archives_.insert(0, u'ArchiveInvalidationInvalidated!.bsa')
        sArchives = u', '.join(archives_)
        self.saveSetting(u'Archive',u'sArchiveList',sArchives)
