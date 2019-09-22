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
import codecs
import re
import time
from collections import OrderedDict, Counter

from . import AFile
from .. import env, bush, balt
from ..bass import dirs
from ..bolt import LowerDict, CIstr, deprint, GPath, DefaultLowerDict, \
    decode, getbestencoding
from ..exception import AbstractError, CancelError, SkipError, BoltError

def _to_lower(ini_settings): # transform dict of dict to LowerDict of LowerDict
    return LowerDict((x, LowerDict(y)) for x, y in ini_settings.iteritems())

def get_ini_type_and_encoding(abs_ini_path):
    """Return ini type (one of IniFile, OBSEIniFile) and inferred encoding
    of the file at abs_ini_path. It reads the file and performs heuristics
    for detecting the encoding, then decodes and applies regexes to every
    line to detect the ini type. Those operations are somewhat expensive so
    it would make sense to pass an encoding in, if we know that the ini file
    must have a specific encoding (for instance the game ini files that
    reportedly must be cp1252). More investigation needed."""
    with open(u'%s' % abs_ini_path, 'rb') as ini_file:
        content = ini_file.read()
    detected_encoding, _confidence = getbestencoding(content)
    decoded_content = decode(content, detected_encoding)
    count = Counter()
    for line in decoded_content.splitlines():
        for ini_type in (IniFile, OBSEIniFile):
            stripped = ini_type.reComment.sub(u'', line).strip()
            for regex in ini_type.formatRes:
                if regex.match(stripped):
                    count[ini_type] += 1
                    break
    try:
        inferred_ini_type = count.most_common(1)[0][0]
    except IndexError: # empty file or failed to parse ini lines
        raise BoltError(u'Failed to infer type for %s' % abs_ini_path)
    return inferred_ini_type, detected_encoding

class IniFile(AFile):
    """Any old ini file."""
    reComment = re.compile(u';.*',re.U)
    reDeletedSetting = re.compile(ur';-\s*(\w.*?)\s*(;.*$|=.*$|$)',re.U)
    reSection = re.compile(ur'^\[\s*(.+?)\s*\]$',re.U)
    reSetting = re.compile(ur'(.+?)\s*=(.*)',re.U)
    formatRes = (reSetting, reSection)
    out_encoding = 'cp1252' # when opening a file for writing force cp1252
    __empty = LowerDict()
    defaultSection = u'General'

    def __init__(self, fullpath, ini_encoding):
        super(IniFile, self).__init__(fullpath)
        self.ini_encoding = ini_encoding
        self.isCorrupted = u''
        #--Settings cache
        self._ci_settings_cache_linenum = self.__empty
        self._deleted_cache = self.__empty
        self._deleted = False
        self.updated = False # notify iniInfos which should clear this flag

    def getSetting(self, section, key, default):
        """Gets a single setting from the file."""
        try:
            return self.get_ci_settings()[section][key][0]
        except KeyError:
            return default

    def get_ci_settings(self, with_deleted=False):
        """Populate and return cached settings - if not just reading them
        do a copy first !"""
        if not self.abs_path.isfile():
            return ({}, {}) if with_deleted else {}
        if self._ci_settings_cache_linenum is self.__empty \
                or self.do_update():
            try:
                self._ci_settings_cache_linenum, self._deleted_cache, \
                    self.isCorrupted = self._get_ci_settings(self.abs_path)
            except UnicodeDecodeError as e:
                self.isCorrupted = (_(u'Your %s seems to have unencodable '
                    u'characters:') + u'\n\n%s') % (self.abs_path, e)
                return ({}, {}) if with_deleted else {}
        if with_deleted:
            return self._ci_settings_cache_linenum, self._deleted_cache
        return self._ci_settings_cache_linenum

    def do_update(self):
        try:
            stat_tuple = self._stat_tuple()
            if self._deleted:
                self.updated = True # restored
                self._deleted = False
        except OSError:
            self._reset_cache(self._null_stat, load_cache=False)
            if not self._deleted:
                # mark as deleted to avoid requesting updates on each refresh
                self._deleted = self.updated = True
                return True
            return False # we already know it's deleted (used for game inis)
        if self._file_changed(stat_tuple):
            self._reset_cache(stat_tuple, load_cache=True)
            self._ci_settings_cache_linenum = self.__empty
            self.updated = True
            return True
        return False

    def _get_ci_settings(self, tweakPath):
        """Get settings as defaultdict[dict] of section -> (setting -> value).
        Keys in both levels are case insensitive. Values are stripped of
        whitespace. "deleted settings" keep line number instead of value (?)
        :rtype: tuple(DefaultLowerDict[bolt.LowerDict], DefaultLowerDict[
        bolt.LowerDict], boolean)
        """
        ci_settings = DefaultLowerDict(LowerDict)
        ci_deleted_settings = DefaultLowerDict(LowerDict)
        default_section = self.__class__.defaultSection
        isCorrupted = u''
        reComment = self.__class__.reComment
        reSection = self.__class__.reSection
        reDeleted = self.__class__.reDeletedSetting
        reSetting = self.__class__.reSetting
        #--Read ini file
        with tweakPath.open('r') as iniFile:
            sectionSettings = None
            section = None
            for i,line in enumerate(iniFile.readlines()):
                line = unicode(line, self.ini_encoding)
                maDeleted = reDeleted.match(line)
                stripped = reComment.sub(u'',line).strip()
                maSection = reSection.match(stripped)
                maSetting = reSetting.match(stripped)
                if maSection:
                    section = maSection.group(1)
                    sectionSettings = ci_settings[section]
                elif maSetting:
                    if sectionSettings is None:
                        sectionSettings = ci_settings[default_section]
                        isCorrupted = _(
                            u'Your %s should begin with a section header ('
                            u'e.g. "[General]"), but does not.') % tweakPath
                    sectionSettings[maSetting.group(1)] = maSetting.group(
                        2).strip(), i
                elif maDeleted:
                    if not section: continue
                    ci_deleted_settings[section][maDeleted.group(1)] = i
        return ci_settings, ci_deleted_settings, isCorrupted

    def read_ini_content(self, as_unicode=True):
        """Return a list of the decoded lines in the ini file, if as_unicode
        is True, or the raw bytes in the ini file, if as_unicode is False.
        Note we strip line endings at the end of the line in unicode mode.
        :rtype: list[unicode]|str"""
        try:
            with self.abs_path.open('rb') as f:
                content = f.read()
            if not as_unicode: return content
            decoded = unicode(content, self.ini_encoding)
            return decoded.splitlines(False) # keepends=False
        except UnicodeDecodeError:
            deprint(u'Failed to decode %s using %s' % (
                self.abs_path, self.ini_encoding), traceback=True)
        except OSError:
            deprint(u'Error reading ini file %s' % self.abs_path,
                    traceback=True)
        return []

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
        tweak_lines = tweak_file.read_ini_content() # type: list[unicode]
        for i, line in enumerate(tweak_lines):
            maDeletedSetting = reDeleted.match(line)
            stripped = reComment.sub(u'', line).strip()
            maSection = reSection.match(stripped)
            maSetting = reSetting.match(stripped)
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
                if stripped:
                    status = -10
            lines.append((line, section, setting, value, status, lineNo,
                          deleted))
        return lines

    def _open_for_writing(self, filepath): # preserve windows EOL
        """Write to ourselves respecting windows newlines and out_encoding.
        Note content to be writen (if coming from ini tweaks) must be encodable
        to out_encoding."""
        return codecs.getwriter(self.out_encoding)(open(filepath, 'w'))

    def ask_create_target_ini(self, msg=_(
            u'The target ini must exist to apply a tweak to it.')):
        return self.abs_path.isfile()

    def saveSettings(self,ini_settings,deleted_settings={}):
        """Apply dictionary of settings to ini file, latter must exist!
        Values in settings dictionary must be actual (setting, value) pairs."""
        ini_settings = _to_lower(ini_settings)
        deleted_settings = LowerDict((x, set(CIstr(u) for u in y)) for x, y in
                                     deleted_settings.iteritems())
        reDeleted = self.reDeletedSetting
        reComment = self.reComment
        reSection = self.reSection
        reSetting = self.reSetting
        #--Read init, write temp
        section = None
        sectionSettings = {}
        ini_lines = self.read_ini_content(as_unicode=True)
        with self._open_for_writing(self.abs_path.temp.s) as tmpFile:
            tmpFileWrite = tmpFile.write
            def _add_remaining_new_items():
                if section in ini_settings: del ini_settings[section]
                if not sectionSettings: return
                for sett, val in sectionSettings.iteritems():
                    tmpFileWrite(u'%s=%s\n' % (sett, val))
                tmpFileWrite(u'\n')
            for line in ini_lines:
                stripped = reComment.sub(u'', line).strip()
                maSection = reSection.match(stripped)
                if maSection:
                    # 'new' entries still to be added from previous section
                    _add_remaining_new_items()
                    section = maSection.group(1)  # entering new section
                    sectionSettings = ini_settings.get(section, {})
                else:
                    match = reSetting.match(stripped) or reDeleted.match(
                        line)  # note we run maDeleted on LINE
                    if match:
                        setting = match.group(1)
                        if setting in sectionSettings:
                            value = sectionSettings[setting]
                            line = u'%s=%s' % (setting, value)
                            del sectionSettings[setting]
                        elif section in deleted_settings and setting in deleted_settings[section]:
                            line = u';-' + line
                tmpFileWrite(line + u'\n')
            # This will occur for the last INI section in the ini file
            _add_remaining_new_items()
            # Add remaining new entries
            for section, sectionSettings in ini_settings.items():
                # _add_remaining_new_items may modify ini_settings
                if sectionSettings:
                    tmpFileWrite(u'[%s]\n' % section)
                    _add_remaining_new_items()
        #--Done
        self.abs_path.untemp()

    def applyTweakFile(self, tweak_lines):
        """Read Ini tweak file and apply its settings to self (the target ini).
        """
        reDeleted = self.reDeletedSetting
        reComment = self.reComment
        reSection = self.reSection
        reSetting = self.reSetting
        #--Read Tweak file
        ini_settings = DefaultLowerDict(LowerDict)
        deleted_settings = DefaultLowerDict(set)
        section = None
        for line in tweak_lines:
            maDeleted = reDeleted.match(line)
            stripped = reComment.sub(u'',line).strip()
            maSection = reSection.match(stripped)
            maSetting = reSetting.match(stripped)
            if maSection:
                section = maSection.group(1)
            elif maSetting:
                ini_settings[section][maSetting.group(1)] = maSetting.group(
                    2).strip()
            elif maDeleted:
                deleted_settings[section].add(CIstr(maDeleted.group(1)))
        self.saveSettings(ini_settings,deleted_settings)
        return True

class _LowerOrderedDict(LowerDict, OrderedDict): pass

class DefaultIniFile(IniFile):
    """A default ini tweak - hardcoded."""
    __empty = _LowerOrderedDict()

    def __init__(self, default_ini_name, settings_dict=__empty):
        # we don't call AFile#__init__ to avoid stat'ing the non existing file
        self.abs_path = GPath(default_ini_name)
        self._file_size, self._file_mod_time = self._null_stat
        #--Settings cache
        self.lines, current_line = [], 0
        self._ci_settings_cache_linenum = _LowerOrderedDict()
        for sect, setts in settings_dict.iteritems():
            self.lines.append('[' + str(sect) + ']')
            self._ci_settings_cache_linenum[sect] = _LowerOrderedDict()
            current_line += 1
            for sett, val in setts.iteritems():
                self.lines.append(str(sett) + '=' + str(val))
                self._ci_settings_cache_linenum[sect][sett] = (val, current_line)
                current_line += 1
        self._deleted_cache = self.__empty

    def get_ci_settings(self, with_deleted=False):
        if with_deleted:
            return self._ci_settings_cache_linenum, self._deleted_cache
        return self._ci_settings_cache_linenum

    def read_ini_content(self, as_unicode=True):
        """Note as_unicode=True strips line endings as opposed to parent -
        this is wanted and does not harm in this case. Note also, the binary
        instantiation of the default ini is with windows EOL."""
        return map(unicode, self.lines) if as_unicode else '\r\n'.join(
            self.lines) + '\r\n' # add a newline at the end of the ini

    # Abstract for DefaultIniFile, bit of a smell
    def do_update(self): raise AbstractError
    @classmethod
    def _get_ci_settings(cls, tweakPath):
        """Do not call this on DefaultTweaks - settings are set in __init__"""
        raise AbstractError
    def applyTweakFile(self, tweak_lines): raise AbstractError
    def saveSettings(self,ini_settings,deleted_settings={}):
        raise AbstractError

class OBSEIniFile(IniFile):
    """OBSE Configuration ini file.  Minimal support provided, only can
    handle 'set', 'setGS', and 'SetNumericGameSetting' statements."""
    reDeleted = re.compile(ur';-(\w.*?)$',re.U)
    reSet     = re.compile(ur'\s*set\s+(.+?)\s+to\s+(.*)', re.I|re.U)
    reSetGS   = re.compile(ur'\s*setGS\s+(.+?)\s+(.*)', re.I|re.U)
    reSetNGS   = re.compile(ur'\s*SetNumericGameSetting\s+(.+?)\s+(.*)', re.I|re.U)
    out_encoding = 'utf-8' # FIXME: ask
    formatRes = (reSet, reSetGS, reSetNGS)
    defaultSection = u'' # Change the default section to something that
    # can't occur in a normal ini

    ci_pseudosections = LowerDict({u'set': u']set[', u'setGS': u']setGS[',
        u'SetNumericGameSetting': u']SetNumericGameSetting['})

    def getSetting(self, section, key, default):
        section = self.ci_pseudosections.get(section, section)
        return super(OBSEIniFile, self).getSetting(section, key, default)

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

    @classmethod
    def _get_ci_settings(cls, tweakPath):
        """Get the settings in the ini script."""
        ini_settings = DefaultLowerDict(LowerDict)
        deleted_settings = DefaultLowerDict(LowerDict)
        reDeleted = cls.reDeleted
        reComment = cls.reComment
        with tweakPath.open('r') as iniFile:
            for i,line in enumerate(iniFile.readlines()):
                maDeleted = reDeleted.match(line)
                if maDeleted:
                    line = maDeleted.group(1)
                    settings_dict = deleted_settings
                else:
                    settings_dict = ini_settings
                stripped = reComment.sub(u'',line).strip()
                match, section_key, _fmt = cls._parse_obse_line(stripped)
                if match:
                    settings_dict[section_key][match.group(1)] = match.group(
                        2).strip(), i
        return ini_settings, deleted_settings, False

    def analyse_tweak(self, tweak_file):
        lines = []
        ci_settings, deletedSettings = self.get_ci_settings(with_deleted=True)
        reDeleted = self.reDeleted
        reComment = self.reComment
        tweak_lines = tweak_file.read_ini_content()  # type: list[unicode]
        for line in tweak_lines:
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

    def saveSettings(self,ini_settings,deleted_settings={}):
        """Apply dictionary of settings to self, latter must exist!
        Values in settings dictionary can be either actual values or
        full ini lines ending in newline char."""
        ini_settings = _to_lower(ini_settings)
        deleted_settings = _to_lower(deleted_settings)
        reDeleted = self.reDeleted
        reComment = self.reComment
        ini_lines = self.read_ini_content(as_unicode=True)
        with self._open_for_writing(self.abs_path.temp.s) as tmpFile:
            # Modify/Delete existing lines
            for line in ini_lines:
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
                        if isinstance(value, basestring) and value[-1:] == u'\n':
                            line = value.rstrip(u'\n\r')
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

class OblivionIni(IniFile):
    """Oblivion.ini file."""
    bsaRedirectors = {u'archiveinvalidationinvalidated!.bsa',
                      u'..\\obmm\\bsaredirection.bsa'}
    _ini_language = None

    def saveSetting(self,section,key,value):
        """Changes a single setting in the file."""
        ini_settings = {section:{key:value}}
        self.saveSettings(ini_settings)

    def get_ini_language(self, cached=True):
        if not cached or self._ini_language is None:
            self._ini_language = self.getSetting(u'General', u'sLanguage',
                                                 u'English')
        return self._ini_language

    @balt.conversation
    def ask_create_target_ini(self, msg=_(
            u'The game ini must exist to apply a tweak to it.')):
        from . import oblivionIni, iniInfos # YAK
        if self is not oblivionIni: return True
        if self.abs_path.exists(): return True
        srcPath = dirs['app'].join(bush.game.defaultIniFile)
        default_path_exists = srcPath.exists()
        msg = _(u'%(ini_path)s does not exist.' % {'ini_path': self.abs_path}) + \
              u'\n\n' + ((msg + u'\n\n') if msg else u'')
        if default_path_exists:
            msg += _(u'Do you want Bash to create it by copying '
                     u'%(default_ini)s ?' % {'default_ini': srcPath})
            if not balt.askYes(None, msg, _(u'Missing game Ini')):
                return False
        else:
            msg += _(u'Please create it manually to continue.')
            balt.showError(None, msg, _(u'Missing game Ini'))
            return False
        try:
            srcPath.copyTo(self.abs_path)
            if balt.Link.Frame.iniList:
                balt.Link.Frame.iniList.panel.ShowPanel(refresh_target=True)
            else:
                iniInfos.refresh(refresh_infos=False)
            return True
        except (OSError, IOError):
            error_msg = u'Failed to copy %s to %s' % (srcPath, self.abs_path)
            deprint(error_msg, traceback=True)
            balt.showError(None, error_msg, _(u'Missing game Ini'))
        return False

    #--BSA Redirection --------------------------------------------------------
    def setBsaRedirection(self,doRedirect=True):
        """Activate or deactivate BSA redirection - game ini must exist!"""
        if self.isCorrupted: return
        section,key = bush.game.ini.bsaRedirection
        if not section or not key: return
        aiBsa = dirs['mods'].join(u'ArchiveInvalidationInvalidated!.bsa')
        aiBsaMTime = time.mktime((2006, 1, 2, 0, 0, 0, 0, 2, 0))
        if aiBsa.exists() and aiBsa.mtime > aiBsaMTime:
            aiBsa.mtime = aiBsaMTime
        # check if BSA redirection is active
        sArchives = self.getSetting(section, key, u'')
        is_bsa_redirection_active = any(x for x in sArchives.split(u',')
            if x.strip().lower() in self.bsaRedirectors)
        if doRedirect == is_bsa_redirection_active:
            return
        # Skyrim does not have an Archive Invalidation File
        if doRedirect and not aiBsa.exists():
            source = dirs['templates'].join(bush.game.fsName, u'ArchiveInvalidationInvalidated!.bsa')
            source.mtime = aiBsaMTime
            try:
                env.shellCopy(source, aiBsa, allowUndo=True, autoRename=True)
            except (env.AccessDeniedError, CancelError, SkipError):
                return
        sArchives = self.getSetting(section,key,u'')
        #--Strip existing redirectors out
        archives_ = [x.strip() for x in sArchives.split(u',') if
                     x.strip().lower() not in self.bsaRedirectors]
        #--Add redirector back in?
        if doRedirect:
            archives_.insert(0, u'ArchiveInvalidationInvalidated!.bsa')
        sArchives = u', '.join(archives_)
        self.saveSetting(u'Archive',u'sArchiveList',sArchives)
