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
"""The data model, complete with initialization functions. Main hierarchies
are the DataStore singletons and bolt.AFile subclasses populating the data
stores. bush.game must be set, to properly instantiate the data stores."""
from __future__ import annotations

import collections
import io
import os
import pickle
import re
import sys
from collections import OrderedDict
from collections.abc import Iterable
from functools import wraps
from itertools import chain

# bosh-local imports - maybe work towards dropping (some of) these?
from . import bsa_files, converters, cosaves
from ._mergeability import is_esl_capable, isPBashMergeable
from .converters import InstallerConverter
from .cosaves import PluggyCosave, xSECosave
from .mods_metadata import get_tags_from_dir
from .save_headers import SaveFileHeader, get_save_header_type
from .. import archives, balt, bass, bolt, bush, env, initialization, \
    load_order
from ..bass import dirs, inisettings
from ..bolt import AFile, DataDict, FName, FNDict, GPath, ListInfo, Path, \
    decoder, deprint, dict_sort, forward_compat_path_to_fn, \
    forward_compat_path_to_fn_list, os_name, struct_error, top_level_files
from ..brec import FormIdReadContext, FormIdWriteContext, RecordHeader, \
    RemapWriteContext
from ..exception import ArgumentError, BoltError, BSAError, CancelError, \
    FailedIniInferError, FileError, ModError, PluginsFullError, \
    SaveFileError, SaveHeaderError, SkipError, SkippedMergeablePluginsError, \
    StateError
from ..gui import askYes ##: YAK!
from ..ini_files import AIniFile, DefaultIniFile, GameIni, IniFile, \
    OBSEIniFile, get_ini_type_and_encoding, supported_ini_exts
from ..mod_files import ModFile, ModHeaderReader

# Singletons, Constants -------------------------------------------------------
undefinedPath = GPath(u'C:\\not\\a\\valid\\path.exe')
empty_path = GPath(u'') # evaluates to False in boolean expressions
undefinedPaths = {GPath(u'C:\\Path\\exe.exe'), undefinedPath}

#--Singletons
gameInis: tuple[GameIni | IniFile] | None = None
oblivionIni: GameIni | None = None
modInfos: ModInfos | None = None
saveInfos: SaveInfos | None = None
iniInfos: INIInfos | None = None
bsaInfos: BSAInfos | None = None
screen_infos: ScreenInfos | None = None

#--Header tags
# re does not support \p{L} - [^\W\d_] is almost equivalent (N vs Nd)
reVersion = re.compile(
  r'((?:version|ver|rev|r|v)[:.]?)[^\S\r\n]*'
  r'(\d(?:\d|[^\W\d_])*(?:(?:\.|-)(?:\d|[^\W\d_])+)*\+?)',
  re.M | re.I)

#--Mod Extensions
__exts = fr'((\.({"|".join(ext[1:] for ext in archives.readExts)}))|)$'
reTesNexus = re.compile(r'(.*?)-(\d+)(?:-\w*)*(?:-\d+)?' + __exts, re.I)
reTESA = re.compile(r'(.*?)(?:-(\d{1,6})(?:\.tessource)?(?:-bain)?)?' + __exts,
                    re.I)
del __exts
# Image extensions for BAIN and for the Screnshots tab
_common_image_exts = {'.bmp', '.gif', '.jpg', '.jpeg', '.png', '.tif'}
bain_image_exts = _common_image_exts | {'.webp'}
ss_image_exts = _common_image_exts | {'.tga'}

#--Typing
_CosaveDict = dict[type[cosaves.ACosave], cosaves.ACosave]

#------------------------------------------------------------------------------
# File System -----------------------------------------------------------------
#------------------------------------------------------------------------------
class MasterInfo(object):
    """Slight abstraction over ModInfo that allows us to represent masters that
    are missing an active mod counterpart."""
    __slots__ = (u'is_ghost', u'curr_name', u'mod_info', u'old_name',
                 'stored_size', '_was_esl')

    def __init__(self, master_name, master_size, was_esl):
        self.stored_size = master_size
        self._was_esl = was_esl
        self.old_name = FName(master_name)
        self.mod_info = self.rename_if_present(master_name)
        if self.mod_info is None:
            self.curr_name = FName(master_name)
            self.is_ghost = False

    def get_extension(self):
        """Returns the file extension of this master."""
        return self.curr_name.fn_ext

    def rename_if_present(self, str_or_fn):
        """Set the current info name if a corresponding mod info is present."""
        mod_info = modInfos.get(str_or_fn, None)
        if mod_info is not None:
            self.curr_name = FName(str_or_fn)
            self.is_ghost = mod_info.isGhost
        return mod_info

    def disable_master(self):
        esp_name = f'XX{self.curr_name.fn_body}.esp'
        self.curr_name = ModInfo.unique_name(esp_name)
        self.is_ghost = False
        self.mod_info = None

    def has_esm_flag(self):
        if self.mod_info:
            return self.mod_info.has_esm_flag()
        else:
            return self.get_extension() in (u'.esm', u'.esl')

    def in_master_block(self):
        if self.mod_info:
            return self.mod_info.in_master_block()
        else:
            return self.get_extension() in (u'.esm', u'.esl')

    def is_esl(self):
        """Delegate to self.modInfo.is_esl if exists, else rely on ."""
        if self.mod_info:
            return self.mod_info.is_esl()
        else:
            return self._was_esl

    def hasTimeConflict(self):
        """True if has an mtime conflict with another mod."""
        return bool(self.mod_info) and self.mod_info.hasTimeConflict()

    def hasActiveTimeConflict(self):
        """True if has an active mtime conflict with another mod."""
        return bool(self.mod_info) and self.mod_info.hasActiveTimeConflict()

    def getBashTags(self):
        """Retrieve bash tags for master info if it's present in Data."""
        return self.mod_info.getBashTags() if self.mod_info else set()

    def getStatus(self):
        return 30 if not self.mod_info else 0

    def __repr__(self):
        return f'{self.__class__.__name__}<{self.curr_name!r}>'

#------------------------------------------------------------------------------
class FileInfo(AFile, ListInfo):
    """Abstract Mod, Save or BSA File. Features a half baked Backup API."""
    _null_stat = (-1, None, None)

    def _stat_tuple(self): return self.abs_path.size_mtime_ctime()

    def __init__(self, fullpath, load_cache=False, itsa_ghost=None):
        ##: We GPath this three times - not slow, but very inelegant
        g_path = GPath(fullpath)
        ListInfo.__init__(self, g_path.stail) # ghost must be lopped off
        self.header = None
        self.masterNames = tuple()
        self.masterOrder = tuple()
        self.madeBackup = False
        # True if the masters for this file are not reliable
        self.has_inaccurate_masters = False
        #--Ancillary storage
        self.extras = {}
        super(FileInfo, self).__init__(g_path, load_cache)

    def _reset_masters(self):
        #--Master Names/Order
        self.masterNames = tuple(self._get_masters())
        self.masterOrder = tuple() #--Reset to empty for now

    def _file_changed(self, stat_tuple):
        return (self.fsize, self.file_mod_time, self.ctime) != stat_tuple

    def _reset_cache(self, stat_tuple, load_cache):
        self.fsize, self.file_mod_time, self.ctime = stat_tuple
        if load_cache: self.readHeader()

    def _mark_unchanged(self):
        self._reset_cache(self._stat_tuple(), load_cache=False)

    ##: DEPRECATED-------------------------------------------------------------
    def getPath(self): return self.abs_path
    @property
    def mtime(self): return self.file_mod_time
    #--------------------------------------------------------------------------
    def setmtime(self, set_time: int | float = 0.0, crc_changed=False):
        """Sets mtime. Defaults to current value (i.e. reset)."""
        set_time = set_time or self.mtime
        self.abs_path.mtime = set_time
        self.file_mod_time = set_time
        return set_time

    def readHeader(self):
        """Read header from file and set self.header attribute."""
        pass

    def getStatus(self):
        """Returns status of this file -- which depends on status of masters.
        0:  Good
        10: Out of order master(s)
        20: Loads before its master(s)
        21: 10 + 20
        30: Missing master(s)."""
        #--Worst status from masters
        status = 30 if any( # if self.masterNames is empty returns False
            (m not in modInfos) for m in self.masterNames) else 0
        #--Missing files?
        if status == 30:
            return status
        #--Misordered?
        return self._masters_order_status(status)

    def _masters_order_status(self, status):
        return status

    def _get_masters(self):
        """Return the masters of this file as a list, if this file has
        'masters'. This is cached in the mastersNames attribute, as decoding
        and G-pathing are expensive.

        :return: A list of the masters of this file, as paths."""
        raise NotImplementedError

    # Backup stuff - beta, see #292 -------------------------------------------
    def get_hide_dir(self):
        return self.get_store().hidden_dir

    def _doBackup(self,backupDir,forceBackup=False):
        """Creates backup(s) of file, places in backupDir."""
        #--Skip backup?
        if self not in self.get_store().values(): return
        if self.madeBackup and not forceBackup: return
        #--Backup
        self.get_store().copy_info(self.fn_key, backupDir)
        #--First backup
        firstBackup = backupDir.join(self.fn_key) + u'f'
        if not firstBackup.exists():
            self.get_store().copy_info(self.fn_key, backupDir,
                                       firstBackup.tail)

    def tempBackup(self, forceBackup=True):
        """Creates backup(s) of file.  Uses temporary directory to avoid UAC issues."""
        self._doBackup(Path.baseTempDir().join(u'WryeBash_temp_backup'),forceBackup)

    def makeBackup(self, forceBackup=False):
        """Creates backup(s) of file."""
        backupDir = self.backup_dir
        self._doBackup(backupDir,forceBackup)
        #--Done
        self.madeBackup = True

    def backup_restore_paths(self, first=False, fname=None):
        """Return a list of tuples, mapping backup paths to their restore
        destinations. If fname is not given returns the (first) backup
        filename corresponding to self.abs_path, else the backup filename
        for fname mapped to its restore location in data_store.store_dir
        :rtype: list[tuple]
        """
        restore_path = (fname and self.get_store().store_dir.join(
            fname)) or self.getPath()
        fname = fname or self.fn_key
        return [(self.backup_dir.join(fname) + (u'f' if first else u''),
                 restore_path)]

    def all_backup_paths(self, fname=None):
        """Return the list of all possible paths a backup operation may create.
        __path does not really matter and is not necessarily correct when fname
        is passed in
        """
        return [backPath for first in (True, False) for backPath, __path in
                self.backup_restore_paths(first, fname)]

    def revert_backup(self, first=False):
        backup_paths = self.backup_restore_paths(first)
        for tup in backup_paths[1:]: # if cosaves do not exist shellMove fails!
            if not tup[0].exists():
                # if cosave exists while its backup not, delete it on restoring
                tup[1].remove()
                backup_paths.remove(tup)
        env.shellCopy(dict(backup_paths))
        # do not change load order for timestamp games - rest works ok
        self.setmtime(self.file_mod_time, crc_changed=True)
        self.get_store().new_info(self.fn_key, notify_bain=True)

    def getNextSnapshot(self):
        """Returns parameters for next snapshot."""
        destDir = self.snapshot_dir
        destDir.makedirs()
        root, ext = self.fn_key.fn_body, self.fn_key.fn_ext
        separator = u'-'
        snapLast = [u'00']
        #--Look for old snapshots.
        reSnap = re.compile(f'^{root}[ -]([0-9.]*[0-9]+){ext}$')
        for fileName in destDir.ilist():
            maSnap = reSnap.match(fileName)
            if not maSnap: continue
            snapNew = maSnap.group(1).split(u'.')
            #--Compare shared version numbers
            sharedNums = min(len(snapNew),len(snapLast))
            for index in range(sharedNums):
                (numNew,numLast) = (int(snapNew[index]),int(snapLast[index]))
                if numNew > numLast:
                    snapLast = snapNew
                    continue
            #--Compare length of numbers
            if len(snapNew) > len(snapLast):
                snapLast = snapNew
                continue
        #--New
        snapLast[-1] = (u'%0'+str(len(snapLast[-1]))+u'd') % (int(snapLast[-1])+1,)
        destName = root+separator+(u'.'.join(snapLast))+ext
        return destDir, destName, f'{root}*{ext}'

    @property
    def backup_dir(self):
        return self.get_store().bash_dir.join(u'Backups')

    @property
    def snapshot_dir(self):
        return self.get_store().bash_dir.join(u'Snapshots')

    def get_rename_paths(self, newName):
        old_new_paths = super(FileInfo, self).get_rename_paths(newName)
        # all_backup_paths will return the backup paths for this file and its
        # satellites (like cosaves). Passing newName in it returns the rename
        # destinations of the backup paths. Backup paths may not exist.
        for b_path, new_b_path in zip(self.all_backup_paths(),
                                       self.all_backup_paths(newName)):
            old_new_paths.append((b_path, new_b_path))
        return old_new_paths

#------------------------------------------------------------------------------
reBashTags = re.compile(u'{{ *BASH *:[^}]*}}\\s*\\n?',re.U)

class ModInfo(FileInfo):
    """A plugin file. Currently, these are .esp, .esm, .esl and .esu files."""
    _has_esm_flag = _is_esl = False # Cached, since we need it so often
    _valid_exts_re = r'(\.(?:' + u'|'.join(
        x[1:] for x in bush.game.espm_extensions) + '))'

    def __init__(self, fullpath, load_cache=False, itsa_ghost=None):
        if itsa_ghost is None and (fullpath.cs[-6:] == u'.ghost'):
            fullpath = fullpath.s[:-6]
            self.isGhost = True
        else:  # new_info() path
            self._refresh_ghost_state(regular_path=fullpath,
                                      itsa_ghost=itsa_ghost)
        super(ModInfo, self).__init__(fullpath, load_cache)

    def get_hide_dir(self):
        dest_dir = self.get_store().hidden_dir
        #--Use author subdirectory instead?
        mod_author = self.header.author
        if mod_author:
            authorDir = dest_dir.join(mod_author)
            if authorDir.is_dir():
                return authorDir
        #--Use group subdirectory instead?
        file_group = self.get_table_prop(u'group')
        if file_group:
            groupDir = dest_dir.join(file_group)
            if groupDir.is_dir():
                return groupDir
        return dest_dir

    def _reset_cache(self, stat_tuple, load_cache):
        super(ModInfo, self)._reset_cache(stat_tuple, load_cache)
        # check if we have a cached crc for this file, use fresh mtime and size
        if load_cache:
            self.calculate_crc() # for added and hopefully updated
            if bush.game.has_esl: self._recalc_esl()
            self._recalc_esm()

    @classmethod
    def get_store(cls): return modInfos

    def get_extension(self):
        """Returns the file extension of this mod."""
        return self.fn_key.fn_ext

    def in_master_block(self, __master_exts=frozenset(('.esm', '.esl'))):
        """Return true for files that load in the masters' block."""
        ##: we should cache this and calculate in reset_cache and co
        mod_ext = self.get_extension()
        if  bush.game.Esp.extension_forces_flags:
            # For games since FO4/SSE, .esm and .esl files set the master flag
            # in memory even if not set on the file on disk. For .esp files we
            # must check for the flag explicitly.
            return mod_ext in __master_exts or self.has_esm_flag()
        elif bush.game.fsName == 'Morrowind':
            ##: This is wrong, but works for now. We need game-specific
            # record headers to parse the ESM flag for MW correctly - #480!
            return mod_ext == '.esm'
        else: return self.has_esm_flag()

    def has_esm_flag(self):
        """Check if the mod info is a master file based on master flag -
        header must be set"""
        return self._has_esm_flag

    def set_esm_flag(self, new_esm_flag):
        """Changes this file's ESM flag to the specified value. Recalculates
        ONAM info if necessary."""
        self.header.flags1.esm_flag = new_esm_flag
        self._recalc_esm()
        self.update_onam()
        self.writeHeader()

    def _recalc_esm(self):
        """Forcibly recalculates the cached ESM status."""
        self._has_esm_flag = self.header.flags1.esm_flag

    def has_esl_flag(self):
        """Check if the mod info is an ESL based on ESL flag alone - header
        must be set."""
        return self.header.flags1.esl_flag

    def set_esl_flag(self, new_esl_flag):
        """Changes this file's ESL flag to the specified value."""
        if bush.game.has_esl:
            self.header.flags1.esl_flag = new_esl_flag
            self._recalc_esl()
            self.writeHeader()

    def is_esl(self):
        """Check if this is a light plugin - .esl files are automatically
        set the light flag, for espms check the flag."""
        return self._is_esl

    def _recalc_esl(self):
        """Forcibly recalculates the cached ESL status."""
        self._is_esl = self.has_esl_flag() or self.get_extension() == u'.esl'

    def isInvertedMod(self):
        """Extension indicates esp/esm, but byte setting indicates opposite."""
        mod_ext = self.get_extension()
        if mod_ext not in (u'.esm', u'.esp'): # don't use for esls
            raise ArgumentError(
                f'isInvertedMod: {mod_ext} - only esm/esp allowed')
        return (self.header and
                mod_ext != (u'.esp', u'.esm')[int(self.header.flags1) & 1])

    def calculate_crc(self, recalculate=False):
        cached_crc = self.get_table_prop(u'crc')
        if not recalculate:
            recalculate = cached_crc is None \
                    or self.file_mod_time != self.get_table_prop('crc_mtime') \
                          or self.fsize != self.get_table_prop(u'crc_size')
        path_crc = cached_crc
        if recalculate:
            path_crc = self.abs_path.crc
            if path_crc != cached_crc:
                self.set_table_prop(u'crc', path_crc)
                self.set_table_prop(u'ignoreDirty', False)
            self.set_table_prop('crc_mtime', self.file_mod_time)
            self.set_table_prop(u'crc_size', self.fsize)
        return path_crc, cached_crc

    def cached_mod_crc(self): # be sure it's valid before using it!
        return self.get_table_prop(u'crc')

    def crc_string(self):
        try:
            return f'{self.cached_mod_crc():08X}'
        except TypeError: # None, should not happen so let it show
            return u'UNKNOWN!'

    def real_index(self):
        """Returns the 'real index' for this plugin, which is the one the game
        will assign it. ESLs will land in the 0xFE spot, while inactive plugins
        don't get any - so we sort them last."""
        return modInfos.real_indices[self.fn_key]

    def real_index_string(self):
        """Returns a string-based version of real_index for displaying in the
        Indices column."""
        return modInfos.real_index_strings[self.fn_key]

    def setmtime(self, set_time: int | float = 0.0, crc_changed=False):
        """Set mtime and if crc_changed is True recalculate the crc."""
        set_time = super().setmtime(set_time)
        # Prevent re-calculating the File CRC
        if not crc_changed:
            self.set_table_prop(u'crc_mtime', set_time)
        else:
            self.calculate_crc(recalculate=True)

    def _get_masters(self):
        """Return the plugin masters, in the order listed in its header."""
        return self.header.masters

    def get_dependents(self):
        """Return a set of all plugins that have this plugin as a master."""
        return modInfos.dependents[self.fn_key]

    # Ghosting and ghosting related overrides ---------------------------------
    def _refresh_ghost_state(self, regular_path=None, *, itsa_ghost=None):
        """Refreshes the isGhost state by checking existence on disk."""
        if itsa_ghost is not None:
            self.isGhost = itsa_ghost
            return
        if regular_path is None: regular_path = self._file_key
        self.isGhost = not regular_path.is_file() and os.path.isfile(
            f'{regular_path}.ghost')

    def do_update(self, raise_on_error=False, itsa_ghost=None):
        old_ghost = self.isGhost
        self._refresh_ghost_state(itsa_ghost=itsa_ghost)
        # mark updated if ghost state changed but only reread header if needed
        did_change = super(ModInfo, self).do_update(raise_on_error)
        return did_change or self.isGhost != old_ghost

    @FileInfo.abs_path.getter
    def abs_path(self):
        """Return joined dir and name, adding .ghost if the file is ghosted."""
        return (self._file_key + u'.ghost') if self.isGhost else self._file_key

    def setGhost(self, isGhost):
        """Sets file to/from ghost mode. Returns ghost status at end."""
        if isGhost == self.isGhost:
            # Current status is already what we want it to be
            return isGhost
        if self.fn_key == bush.game.master_file:
            # Don't allow the master ESM to be ghosted, we need that one
            return self.isGhost
        normal = self._file_key
        ghost = normal + '.ghost'
        # Current status != what we want, so change it
        try:
            if not normal.editable() or not ghost.editable():
                return self.isGhost
            # Determine source and target, then perform the move
            ghost_source = normal if isGhost else ghost
            ghost_target = ghost if isGhost else normal
            ghost_source.moveTo(ghost_target)
            self.isGhost = isGhost
            # reset cache info as un/ghosting should not make do_update return
            # True
            self._mark_unchanged()
            # Notify BAIN, as this is basically a rename operation
            modInfos._notify_bain(renamed={ghost_source: ghost_target})
        except:
            deprint(f'Failed to {"" if isGhost else "un"}ghost file '
                    f'{normal if isGhost else ghost}', traceback=True)
        return self.isGhost

    #--Bash Tags --------------------------------------------------------------
    def setBashTags(self,keys):
        """Sets bash keys as specified."""
        self.set_table_prop(u'bashTags', keys)

    def setBashTagsDesc(self,keys):
        """Sets bash keys as specified."""
        keys = set(keys) #--Make sure it's a set.
        if keys == self.getBashTagsDesc(): return
        if keys:
            strKeys = u'{{BASH:'+(u','.join(sorted(keys)))+u'}}\n'
        else:
            strKeys = u''
        desc_ = self.header.description
        if reBashTags.search(desc_):
            desc_ = reBashTags.sub(strKeys,desc_)
        else:
            desc_ = desc_ + u'\n' + strKeys
        if len(desc_) > 511: return False
        self.writeDescription(desc_)
        return True

    def getBashTags(self) -> set[str]:
        """Returns any Bash flag keys. Drops obsolete tags."""
        ret_tags = self.get_table_prop(u'bashTags', set())
        fixed_tags = process_tags(ret_tags, drop_unknown=False)
        if fixed_tags != ret_tags:
            self.setBashTags(fixed_tags)
        return fixed_tags & bush.game.allTags

    def getBashTagsDesc(self, *, __tags_search=re.compile(
        '{{ *BASH *:([^}]+)}}', re.I).search):
        """Returns any Bash flag keys."""
        maBashKeys = __tags_search(self.header.description)
        if not maBashKeys:
            return set()
        else:
            tags_set = {tag.strip() for tag in maBashKeys.group(1).split(u',')}
            # Remove obsolete and unknown tags and resolve any tag aliases
            return process_tags(tags_set)

    def reloadBashTags(self, ci_cached_bt_contents=None):
        """Reloads bash tags from mod description, LOOT and Data/BashTags.

        :param ci_cached_bt_contents: Passed to get_tags_from_dir, see there
            for docs."""
        wip_tags = set()
        wip_tags |= self.getBashTagsDesc()
        # Tags from LOOT take precedence over the description
        added_tags, deleted_tags = read_loot_tags(self.fn_key)
        wip_tags |= added_tags
        wip_tags -= deleted_tags
        # Tags from Data/BashTags/{self.fn_key}.txt take precedence over both
        # the description and LOOT
        added_tags, deleted_tags = read_dir_tags(self.fn_key,
            ci_cached_bt_contents=ci_cached_bt_contents)
        wip_tags |= added_tags
        wip_tags -= deleted_tags
        self.setBashTags(wip_tags)

    def is_auto_tagged(self, default_auto=True):
        """Returns True if this plugin receives its tags automatically from
        sources like the description, LOOT masterlist and BashTags files.

        :type default_auto: bool | None"""
        return self.get_table_prop(u'autoBashTags', default_auto)

    def set_auto_tagged(self, auto_tagged):
        """Changes whether or not this plugin receives its tags
        automatically. See is_auto_tagged."""
        self.set_table_prop(u'autoBashTags', auto_tagged)

    #--Header Editing ---------------------------------------------------------
    def readHeader(self):
        """Read header from file and set self.header attribute."""
        try:
            with FormIdReadContext.from_info(self) as ins:
                self.header = ins.plugin_header
        except struct_error as rex:
            raise ModError(self.fn_key, f'Struct.error: {rex}')
        if bush.game.Esp.warn_older_form_versions:
            if self.header.header.form_version != RecordHeader.plugin_form_version:
                modInfos.older_form_versions.add(self.fn_key)
        self._reset_masters()

    def writeHeader(self, old_masters: list[FName] | None = None):
        """Write Header. Actually have to rewrite entire file."""
        with FormIdReadContext.from_info(self) as ins:
            # If we need to remap masters, construct a remapping write context.
            # Otherwise we need a regular write context due to ONAM fids
            aug_masters = [*self.header.masters, self.fn_key]
            ctx_args = [self.abs_path.temp, aug_masters, self.header.version]
            if old_masters is not None:
                write_ctx = RemapWriteContext(old_masters, *ctx_args)
            else:
                write_ctx = FormIdWriteContext(*ctx_args)
            with write_ctx as out:
                try:
                    # We already read the file header (in FormIdReadContext),
                    # so just write out the new one and copy the rest over
                    self.header.getSize()
                    self.header.dump(out)
                    out.write(ins.read(ins.size - ins.tell()))
                except struct_error as rex:
                    raise ModError(self.fn_key, f'Struct.error: {rex}')
        #--Remove original and replace with temp
        self.abs_path.untemp()
        self.setmtime(crc_changed=True)
        #--Merge info
        merge_size, canMerge = self.get_table_prop(u'mergeInfo', (None, None))
        if merge_size is not None:
            self.set_table_prop(u'mergeInfo', (self.abs_path.psize, canMerge))

    def writeDescription(self, new_desc):
        """Sets description to specified text and then writes hedr."""
        new_desc = new_desc[:min(511,len(new_desc))] # 511 + 1 for null = 512
        self.header.description = new_desc
        self.header.setChanged()
        self.writeHeader()

    def get_version(self):
        """Extract and return version number from self.header.description."""
        if not self.header: ##: header not always present?
            return ''
        desc_match = reVersion.search(self.header.description)
        return (desc_match and desc_match.group(2)) or ''

    #--Helpers ----------------------------------------------------------------
    def isBP(self):
        return self.header.author == u'BASHED PATCH'

    def txt_status(self):
        fnkey = self.fn_key
        if load_order.cached_is_active(fnkey): return _(u'Active')
        elif fnkey in modInfos.merged: return _(u'Merged')
        elif fnkey in modInfos.imported: return _(u'Imported')
        else: return _('Inactive')

    def hasTimeConflict(self):
        """True if there is another mod with the same mtime."""
        return load_order.has_load_order_conflict(self.fn_key)

    def hasActiveTimeConflict(self):
        """True if has an active mtime conflict with another mod."""
        return load_order.has_load_order_conflict_active(self.fn_key)

    def hasBadMasterNames(self): # used in status calculation
        """True if has a master with un unencodable name in cp1252."""
        try:
            for x in self.masterNames: x.encode('cp1252')
            return False
        except UnicodeEncodeError:
            return True

    def mod_bsas(self, bsa_infos=None):
        """Returns a list of all BSAs that the game will attach to this plugin.
        bsa_infos is optional and will default to bosh.bsaInfos."""
        if bush.game.fsName == u'Morrowind':
            # Morrowind does not load attached BSAs at all - they all have to
            # be registered via the INI
            return []
        bsa_pattern = (re.escape(self.fn_key.fn_body) +
                       bush.game.Bsa.attachment_regex +
                       u'\\' + bush.game.Bsa.bsa_extension)
        is_attached = re.compile(bsa_pattern, re.I | re.U).match
        # bsaInfos must be updated and contain all existing bsas
        if bsa_infos is None: bsa_infos = bsaInfos
        return [binf for k, binf in bsa_infos.items() if is_attached(k)]

    def hasBsa(self):
        """Returns True if plugin has an associated BSA."""
        return bool(self.mod_bsas())

    def get_ini_name(self):
        """Returns the name of the INI matching this plugin, if it were to
        exist."""
        return self.fn_key.fn_body + '.ini'

    def _string_files_paths(self, lang):
        # type: (str) -> Iterable[str]
        str_f_body = self.fn_key.fn_body
        str_f_ext = self.get_extension()
        for str_format in bush.game.Esp.stringsFiles:
            yield os.path.join(u'Strings', str_format % {
                u'body': str_f_body, u'ext': str_f_ext, u'language': lang})

    def getStringsPaths(self, lang=u'English'):
        """If Strings Files are available as loose files, just point to
        those, otherwise extract needed files from BSA if needed."""
        baseDirJoin = self.info_dir.join
        extract = set()
        paths = set()
        #--Check for Loose Files first
        for filepath in self._string_files_paths(lang):
            loose = baseDirJoin(filepath)
            if not loose.is_file():
                extract.add(filepath)
            else:
                paths.add(loose)
        #--If there were some missing Loose Files
        if extract:
            ##: Pass cached_ini_info here for performance?
            potential_bsas = self._find_string_bsas()
            bsa_assets = OrderedDict()
            for bsa_info in potential_bsas:
                try:
                    found_assets = bsa_info.has_assets(extract)
                except BSAError:
                    deprint(f'Failed to parse {bsa_info}', traceback=True)
                    continue
                if not found_assets: continue
                bsa_assets[bsa_info] = found_assets
                extract -= set(found_assets)
                if not extract:
                    break
            else:
                msg = [f'This plugin is localized, but the following strings '
                       f'files seem to be missing:']
                msg.extend(f' - {e}' for e in extract)
                if potential_bsas:
                    msg.append('The following BSAs were scanned (based on '
                               'name and INI settings), but none of them '
                               'contain the missing files:')
                    msg.extend(f' - {bsa_inf}' for bsa_inf in potential_bsas)
                else:
                    msg.append('No BSAs were found that could contain the '
                        'missing strings - this is bad, validate your game '
                        'installation and double-check your INI settings')
                raise ModError(self.fn_key, '\n'.join(msg))
            for bsa_inf, assets in bsa_assets.items():
                out_path = dirs[u'bsaCache'].join(bsa_inf.fn_key)
                try:
                    bsa_inf.extract_assets(assets, out_path.s)
                except BSAError as e:
                    raise ModError(self.fn_key,
                      f"Could not extract Strings File from '{bsa_inf}': {e}")
                paths.update(map(out_path.join, assets))
        return paths

    # Heuristics for _find_string_bsas. Patch before interface because the
    # patch BSA (which only exists in SSE) will always load after the interface
    # BSA and hence should win all conflicts (including strings).
    _bsa_heuristics = list(enumerate((u'main', u'patch', u'interface')))
    def _find_string_bsas(self, cached_ini_info=(None, None, None)):
        """Return a list of BSAs to get strings files from. Note that this is
        *only* meant for strings files. It sorts the list in such a way as to
        prioritize files that are likely to contain the strings, instead of
        returning the true BSA order.

        :param cached_ini_info: Passed to get_bsa_lo, see there for docs."""
        ret_bsas = list(reversed(
            modInfos.get_bsa_lo(cached_ini_info=cached_ini_info,
                                for_plugins=[self.fn_key])[0]))
        # First heuristic sorting pass: sort 'main', 'patch' and 'interface' to
        # the front. This avoids parsing expensive BSAs at startup for the game
        # master (e.g. Skyrim.esm -> Skyrim - Textures0.bsa).
        heuristics = self._bsa_heuristics
        last_index = len(heuristics) # last place to sort unwanted BSAs
        def _bsa_heuristic(binf):
            b_lower = binf.fn_key.fn_body.lower()
            for i, h in heuristics:
                if h in b_lower:
                    return i
            return last_index
        ret_bsas.sort(key=_bsa_heuristic)
        # Second heuristic sorting pass: sort BSAs that begin with the body of
        # this plugin before others. This avoids parsing vanilla BSAs for third
        # party plugins, while being a noop for vanilla plugins (stable sort).
        plugin_prefix = self.fn_key.fn_body.lower()
        ret_bsas.sort(key=lambda b: not b.fn_key.lower().startswith(plugin_prefix))
        return ret_bsas

    def isMissingStrings(self, cached_ini_info=(None, None, None),
            ci_cached_strings_paths=None):
        """True if the mod says it has .STRINGS files, but the files are
        missing.

        :param cached_ini_info: Passed to get_bsa_lo, see there for docs.
        :param ci_cached_strings_paths: An optional set of lower-case versions
            of the paths to all strings files. They must match the format
            returned by _string_files_paths (i.e. starting with 'strings/'. If
            specified, no stat calls will occur to determine if loose strings
            files exist."""
        if not getattr(self.header.flags1, 'localized', False): return False
        lang = oblivionIni.get_ini_language()
        bsa_infos = self._find_string_bsas(cached_ini_info)
        info_dir_join = self.info_dir.join
        for assetPath in self._string_files_paths(lang):
            # Check loose files first
            if ci_cached_strings_paths is not None:
                if assetPath.lower() in ci_cached_strings_paths:
                    continue
            elif info_dir_join(assetPath).is_file():
                continue
            # Check in BSA's next
            for bsa_info in bsa_infos:
                try:
                    if bsa_info.has_assets((assetPath,)):
                        break # found
                except BSAError:
                    deprint(f'Failed to parse {bsa_info}', traceback=True)
                    continue
            else: # not found
                return True
        return False

    def hasResources(self):
        """Returns (hasBsa, has_blocking_resources) booleans according to
        presence of corresponding resources (a BSA with a matching name and one
        or more plugin-name-specific folder, respectively)."""
        return (self.hasBsa(), any(self._check_resources(pnd) for pnd
                                   in bush.game.plugin_name_specific_dirs))

    def _check_resources(self, resource_path):
        """Returns True if the directory created by joining self.info_dir, the
        specified path and self.fn_key exists. Used to check for the existence
        of plugin-name-specific directories, which prevent merging.

        :param resource_path: The path to the plugin-name-specific directory,
        as a list of path components."""
        # If resource_path is empty, then we would effectively query
        # self.info_dir.join(self.fn_key), which always exists - that's the
        # plugin file!
        return resource_path and self.info_dir.join(resource_path).join(
            self.fn_key).exists()

    def has_master_size_mismatch(self): # used in status calculation
        """Checks if this plugin has at least one stored master size that does
        not match that master's size on disk."""
        m_sizes = self.header.master_sizes
        for i, master_name in enumerate(self.masterNames):
            if modInfos.size_mismatch(master_name, m_sizes[i]):
                return True
        return False

    def update_onam(self):
        """Checks if this plugin needs ONAM data and either adds or removes it
        based on that."""
        # Skip for games that don't need the ONAM generation
        if bush.game.Esp.generate_temp_child_onam:
            if self.in_master_block():
                # We're a master now, so calculate the ONAM
                temp_headers = ModHeaderReader.read_temp_child_headers(self)
                num_masters = len(self.masterNames)
                # Note that the only thing that matters is the first byte of
                # the fid, since both overrides and injected records need ONAM.
                # We sort because xEdit does as well.
                new_onam = sorted([h.fid for h in temp_headers
                                   if h.fid.mod_dex < num_masters],
                    key=lambda f: f.short_fid)
            else:
                # We're no longer a master now, so discard all ONAM
                new_onam = []
            if new_onam != self.header.overrides:
                self.header.overrides = new_onam
                self.header.setChanged()
        # TODO(inf) On FO4, ONAM is based on all overrides in complex records.
        #  That will have to go somewhere like ModFile.save though.

    def getDirtyMessage(self):
        """Returns a dirty message from LOOT."""
        if self.get_table_prop(u'ignoreDirty', False) or not \
                initialization.lootDb.is_plugin_dirty(self.fn_key, modInfos):
            return False, u''
        return True, _(u'Contains dirty edits, needs cleaning.')

    def match_oblivion_re(self):
        return self.fn_key in bush.game.modding_esm_size or \
               self.fn_key == 'Oblivion.esm'

    def get_rename_paths(self, newName):
        old_new_paths = super(ModInfo, self).get_rename_paths(newName)
        if self.isGhost:
            old_new_paths[0] = (self.abs_path, old_new_paths[0][1] + u'.ghost')
        return old_new_paths

    def _masters_order_status(self, status):
        self.masterOrder = tuple(load_order.get_ordered(self.masterNames))
        loads_before_its_masters = self.masterOrder and \
                                   load_order.cached_lo_index(
            self.masterOrder[-1]) > load_order.cached_lo_index(self.fn_key)
        if self.masterOrder != self.masterNames and loads_before_its_masters:
            return 21
        elif loads_before_its_masters:
            return 20
        elif self.masterOrder != self.masterNames:
            return 10
        else:
            return status

    def ask_resources_ok(self, bsa_and_blocking_msg, bsa_msg, blocking_msg):
        hasBsa, hasBlocking = self.hasResources()
        if not hasBsa and not hasBlocking: return ''
        elif hasBsa and hasBlocking: msg = bsa_and_blocking_msg
        elif hasBsa: msg = bsa_msg
        else: msg = blocking_msg
        assoc_bsa = self.fn_key.fn_body + bush.game.Bsa.bsa_extension
        return msg % {
            'assoc_bsa_name': assoc_bsa,
            'pnd_example': os.path.join('Sound', 'Voice', self.fn_key)}

# Deprecated/Obsolete Bash Tags -----------------------------------------------
# Tags that have been removed from Wrye Bash and should be dropped from pickle
# files
removed_tags = {u'Merge', u'ScriptContents'}
# Indefinite backwards-compatibility aliases for deprecated tags
tag_aliases = {
    'Body-F': {'R.Body-F'},
    'Body-M': {'R.Body-M'},
    'Body-Size-F': {'R.Body-Size-F'},
    'Body-Size-M': {'R.Body-Size-M'},
    'C.GridFlags': {'C.ForceHideLand'},
    'Derel': {'Relations.Remove'},
    'Eyes': {'R.Eyes'},
    'Eyes-D': {'R.Eyes'},
    'Eyes-E': {'R.Eyes'},
    'Eyes-R': {'R.Eyes'},
    'Factions': {'Actors.Factions'},
    'Hair': {'R.Hair'},
    'Invent': {'Invent.Add', 'Invent.Remove'},
    'InventOnly': {'IIM', 'Invent.Add', 'Invent.Remove'},
    'Npc.EyesOnly': {'NPC.Eyes'},
    'Npc.HairOnly': {'NPC.Hair'},
    'NpcFaces': {'NPC.Eyes', 'NPC.Hair', 'NPC.FaceGen'},
    'R.Relations': {'R.Relations.Add', 'R.Relations.Change',
                    'R.Relations.Remove'},
    'Relations': {'Relations.Add', 'Relations.Change'},
    'Voice-F': {'R.Voice-F'},
    'Voice-M': {'R.Voice-M'},
}

def process_tags(tag_set: set[str], drop_unknown=True) -> set[str]:
    """Removes obsolete tags from and resolves any tag aliases in the
    specified set of tags. See the comments above for more information. If
    drop_unknown is True, also removes any unknown tags (tags that are not
    currently used, obsolete or aliases)."""
    if not tag_set: return tag_set # fast path - nothing to process
    ret_tags = tag_set.copy()
    ret_tags -= removed_tags
    for old_tag, replacement_tags in tag_aliases.items():
        if old_tag in tag_set:
            ret_tags.discard(old_tag)
            ret_tags.update(replacement_tags)
    if drop_unknown:
        ret_tags &= bush.game.allTags
    return ret_tags

# Some wrappers to decouple other files from process_tags
def read_dir_tags(plugin_name, ci_cached_bt_contents=None):
    """Wrapper around get_tags_from_dir. See that method for docs."""
    added_tags, deleted_tags = get_tags_from_dir(plugin_name,
        ci_cached_bt_contents=ci_cached_bt_contents)
    return process_tags(added_tags), process_tags(deleted_tags)

def read_loot_tags(plugin_name):
    """Wrapper around get_tags_from_loot. See that method for docs."""
    added_tags, deleted_tags = initialization.lootDb.get_tags_from_loot(
        plugin_name)
    return process_tags(added_tags), process_tags(deleted_tags)

#------------------------------------------------------------------------------
def get_game_ini(ini_path, is_abs=True):
    """:rtype: GameIni | IniFile | None"""
    for game_ini in gameInis:
        game_ini_path = game_ini.abs_path
        if ini_path == ((is_abs and game_ini_path) or game_ini_path.stail):
            return game_ini
    return None

def BestIniFile(abs_ini_path):
    """:rtype: IniFile"""
    game_ini = get_game_ini(abs_ini_path)
    if game_ini:
        return game_ini
    inferred_ini_type, detected_encoding = get_ini_type_and_encoding(
        abs_ini_path)
    return inferred_ini_type(abs_ini_path, detected_encoding)

def best_ini_files(abs_ini_paths):
    """Similar to BestIniFile, but takes an iterable of INI paths and returns a
    dict mapping those paths to the created IniFile objects. The functional
    difference is that this method can handle empty INI files, as long as all
    other INIs passed in have the same INI type (i.e. no mixing of OBSE INIs
    and regular INIs). Meant to be used if you have multiple versions of the
    same INI and hence can guarantee that they have the same type too."""
    ret = {}
    found_types = set()
    ambigous_paths = set()
    for aip in abs_ini_paths:
        game_ini = get_game_ini(aip)
        if game_ini:
            ret[aip] = game_ini
            found_types.add(IniFile)
            continue
        try:
            detected_type, detected_enc = get_ini_type_and_encoding(aip)
        except FailedIniInferError:
            # Come back to this later using the found types
            ambigous_paths.add(aip)
            continue
        ret[aip] = detected_type(aip, detected_enc)
        found_types.add(detected_type)
    # Check if we've only found a single INI type - if so, it's safe to assume
    # the remaining INIs have the same type too
    single_found_type = None
    if len(found_types) == 1:
        single_found_type = next(iter(found_types))
    for aip in ambigous_paths:
        detected_type, detected_enc = get_ini_type_and_encoding(aip,
            fallback_type=single_found_type)
        ret[aip] = detected_type(aip, detected_enc)
    return ret

class AINIInfo(AIniFile):
    """Ini info, adding cached status and functionality to the ini files."""
    _status = None
    is_default_tweak = False

    @classmethod
    def get_store(cls): return iniInfos

    def tweak_status(self, target_ini_settings=None):
        if self._status is None:
            self.getStatus(target_ini_settings=target_ini_settings)
        return self._status

    def _incompatible(self, other):
        if not isinstance(self, OBSEIniFile):
            return isinstance(other, OBSEIniFile)
        return not isinstance(other, OBSEIniFile)

    def is_applicable(self, stat=None):
        stat = stat or self.tweak_status()
        return stat != -20 and (
            bass.settings[u'bash.ini.allowNewLines'] or stat != -10)

    def getStatus(self, target_ini=None, target_ini_settings=None):
        """Returns status of the ini tweak:
        20: installed (green with check)
        15: mismatches (green with dot) - mismatches are with another tweak from same installer that is applied
        10: mismatches (yellow)
        0: not installed (green)
        -10: tweak file contains new sections/settings
        -20: incompatible tweak file (red)
        Also caches the value in self._status"""
        infos = iniInfos
        target_ini = target_ini or infos.ini
        tweak_settings = self.get_ci_settings()
        def _status(s):
            self._status = s
            return s
        if self._incompatible(target_ini) or not tweak_settings:
            return _status(-20)
        match = False
        mismatch = 0
        ini_settings = target_ini_settings if target_ini_settings is not None \
            else target_ini.get_ci_settings()
        self_installer = FName( # make comparison case insensitive below
            self.get_table_prop(u'installer'))
        for section_key in tweak_settings:
            if section_key not in ini_settings:
                return _status(-10)
            target_section = ini_settings[section_key]
            tweak_section = tweak_settings[section_key]
            for item in tweak_section:
                if item not in target_section:
                    return _status(-10)
                if tweak_section[item][0] != target_section[item][0]:
                    if mismatch < 2:
                        # Check to see if the mismatch is from another ini
                        # tweak that is applied, and from the same installer
                        mismatch = 2
                        if self_installer is None: continue
                        for ini_info in infos.values():
                            if self is ini_info: continue
                            if self_installer != ini_info.get_table_prop(
                                    u'installer'): continue
                            # It's from the same installer
                            if self._incompatible(ini_info): continue
                            value = ini_info.getSetting(section_key, item, None)
                            if value == target_section[item][0]:
                                # The other tweak has the setting we're worried about
                                mismatch = 1
                                break
                else:
                    match = True
        if not match:
            return _status(0)
        elif not mismatch:
            return _status(20)
        elif mismatch == 1:
            return _status(15)
        elif mismatch == 2:
            return _status(10)

    def reset_status(self): self._status = None

    def listErrors(self):
        """Returns ini tweak errors as text."""
        ini_infos_ini = iniInfos.ini
        errors = [f'{self.fn_key}:']
        pseudosections_lower = {s.lower() for s in
                                OBSEIniFile.ci_pseudosections.values()}
        if self._incompatible(ini_infos_ini):
            errors.append(' ' + _('Format mismatch:'))
            if isinstance(self, OBSEIniFile):
                errors.append('  ' + _('Target format is INI, tweak format is '
                                       'Batch Script.'))
            else:
                errors.append('  ' + _('Target format is Batch Script, tweak '
                                       'format is INI.'))
        else:
            tweak_settings = self.get_ci_settings()
            ini_settings = ini_infos_ini.get_ci_settings()
            if len(tweak_settings) == 0:
                if not isinstance(self, OBSEIniFile):
                    errors.append(' ' + _('No valid INI format lines.'))
                else:
                    errors.append(' ' + _('No valid Batch Script format '
                                          'lines.'))
            else:
                missing_settings = []
                for key in tweak_settings:
                    # Properly handle OBSE pseudosections - they're always
                    # missing from the ini_settings
                    is_pseudosection = key.lower() in pseudosections_lower
                    if not is_pseudosection and key not in ini_settings:
                        errors.append(f' [{key}] - ' + _('Invalid Header'))
                    else:
                        for item in tweak_settings[key]:
                            # Avoid modifying ini_settings by using get
                            if item not in ini_settings.get(key, ()):
                                missing_settings.append(
                                    f'  {item}' if is_pseudosection
                                    else f'  [{key}] {item}')
                if missing_settings:
                    errors.append(' ' + _('Settings missing from target INI:'))
                    errors.extend(missing_settings)
        if len(errors) == 1:
            errors.append(' ' + _('None'))
        log = bolt.LogFile(io.StringIO())
        for line in errors:
            log(line)
        return log.out.getvalue()

#------------------------------------------------------------------------------
class SaveInfo(FileInfo):
    cosave_types = () # cosave types for this game - set once in SaveInfos
    _cosave_ui_string = {PluggyCosave: u'XP', xSECosave: u'XO'} # ui strings
    _valid_exts_re = r'(\.(?:' + '|'.join(
        [bush.game.Ess.ext[1:], bush.game.Ess.ext[1:-1] + 'r', 'bak']) + '))'
    _co_saves: _CosaveDict

    def __init__(self, fullpath, load_cache=False, itsa_ghost=None):
        # Dict of cosaves that may come with this save file. Need to get this
        # first, since readHeader calls _get_masters, which relies on the
        # cosave for SSE and FO4
        self._co_saves = self.get_cosaves_for_path(fullpath)
        super(SaveInfo, self).__init__(fullpath, load_cache)

    @classmethod
    def get_store(cls): return saveInfos

    def getStatus(self):
        status = super(SaveInfo, self).getStatus()
        if status > 0:
            # Missing or reordered masters -> orange or red
            return status
        masterOrder = self.masterOrder
        active_tuple = load_order.cached_active_tuple()
        if masterOrder == active_tuple:
            # Exact match with LO -> purple
            return -20
        len_m = len(masterOrder)
        if len(active_tuple) > len_m and masterOrder == active_tuple[:len_m]:
            # Matches LO except for new plugins at the end -> blue
            return -10
        else:
            # Does not match the LO's active plugins, but the order is correct.
            # That means the LO has new plugins, but not at the end -> green
            return 0

    def _masters_order_status(self, status):
        self.masterOrder = tuple(load_order.get_ordered(self.masterNames))
        if self.masterOrder != self.masterNames:
            return 20 # Reordered masters are far more important in saves
        else:
            return status

    def is_save_enabled(self):
        """True if I am enabled."""
        return self.fn_key.fn_ext == bush.game.Ess.ext

    def readHeader(self):
        """Read header from file and set self.header attribute."""
        try:
            self.header = get_save_header_type(bush.game.fsName)(self)
        except SaveHeaderError as e:
            raise SaveFileError(self.fn_key, e.args[0]) from e
        self._reset_masters()

    def do_update(self, raise_on_error=False, itsa_ghost=None):
        # Check for new and deleted cosaves and do_update old, surviving ones
        cosaves_changed = False
        for co_type in SaveInfo.cosave_types:
            co_path = co_type.get_cosave_path(self.abs_path)
            if co_path.is_file():
                if co_type in self._co_saves:
                    # Existing cosave could have changed, check if it did
                    cosaves_changed |= self._co_saves[co_type].do_update()
                else:
                    # New cosave attached, add it to cache
                    self._co_saves[co_type] = self.make_cosave(co_type,
                                                               co_path)
                    cosaves_changed = True
            elif co_type in self._co_saves:
                # Old cosave deleted, remove it from cache
                del self._co_saves[co_type]
                cosaves_changed = True
        # If the cosaves have changed, the cached masters can no longer be
        # trusted since they may have been retrieved from the cosaves
        if cosaves_changed:
            self._reset_masters()
        # Delegate the call first, but also take the cosaves into account
        return super(SaveInfo, self).do_update(raise_on_error) or \
               cosaves_changed

    def write_masters(self, master_map):
        """Rewrites masters of existing save file and cosaves."""
        if not self.abs_path.exists():
            raise SaveFileError(self.abs_path.head, u'File does not exist.')
        self.header.remap_masters(master_map)
        with self.abs_path.open(u'rb') as ins:
            with self.abs_path.temp.open(u'wb') as out:
                self.header.write_header(ins, out)
        self.abs_path.untemp()
        if master_map:
            for co_file in self._co_saves.values():
                co_file.remap_plugins(master_map)
                co_file.write_cosave_safe()

    def get_cosave_tags(self):
        """Return strings expressing whether cosaves exist and are correct.
        Correct means not in more that 10 seconds difference from the save."""
        co_ui_strings = [u'', u'']
        instances = self._co_saves
        # last string corresponds to xse plugin so used reversed
        for j, co_typ in enumerate(reversed(self.cosave_types)):
            inst = instances.get(co_typ, None)
            if inst and inst.abs_path.exists():
                co_ui_strings[j] = self._cosave_ui_string[co_typ][
                    abs(inst.abs_path.mtime - self.mtime) < 10]
        return u'\n'.join(co_ui_strings)

    def backup_restore_paths(self, first=False, fname=None):
        """Return as parent and in addition back up paths for the cosaves."""
        back_to_dest = super(SaveInfo, self).backup_restore_paths(first, fname)
        # see if we have cosave backups - we must delete cosaves when restoring
        # if the backup does not have a cosave
        for co_type in self.cosave_types:
            co_paths = tuple(co_type.get_cosave_path(x) for x in back_to_dest[0])
            back_to_dest.append(co_paths)
        return back_to_dest

    @staticmethod
    def make_cosave(co_type, co_path):
        """Attempts to create a cosave of the specified type at the specified
        path and logs any resulting error.

        :rtype: cosaves.ACosave | None"""
        try:
            return co_type(co_path)
        except (OSError, FileError) as e:
            if not isinstance(e, FileNotFoundError):
                deprint(f'Failed to open {co_path}', traceback=True)
            return None

    @staticmethod
    def get_cosaves_for_path(save_path: Path) -> _CosaveDict:
        """Get ACosave instances for save_path if those paths exist.
        Return a dict of those instances keyed by their type."""
        result = {}
        for co_type in SaveInfo.cosave_types:
            new_cosave = SaveInfo.make_cosave(
                co_type, co_type.get_cosave_path(save_path))
            if new_cosave: result[co_type] = new_cosave
        return result

    def get_xse_cosave(self):
        """:rtype: xSECosave | None"""
        return self._co_saves.get(xSECosave, None)

    def get_pluggy_cosave(self):
        """:rtype: PluggyCosave | None"""
        return self._co_saves.get(PluggyCosave, None)

    def _get_masters(self):
        """Return the save file masters, ie the plugins listed in its plugin
        list. For esl games this order might not reflect the actual order the
        masters are mapped to form ids, hence we try to return the correct
        order if a suitable to this end cosave is present."""
        if bush.game.has_esl:
            xse_cosave = self.get_xse_cosave()
            if xse_cosave is not None: # the cached cosave should be valid
                # Make sure the cosave's masters are actually useful
                if xse_cosave.has_accurate_master_list():
                    return [*map(FName, xse_cosave.get_master_list())]
        # Fall back on the regular masters - either the cosave is unnecessary,
        # doesn't exist or isn't accurate
        return self.header.masters

    def _reset_masters(self):
        super(SaveInfo, self)._reset_masters()
        # If this save has ESL masters, and no cosave or a cosave from an
        # older version, then the masters are unreliable and we need to warn
        if bush.game.has_esl and self.header.has_esl_masters:
            xse_cosave = self.get_xse_cosave()
            self.has_inaccurate_masters = xse_cosave is None or \
                not xse_cosave.has_accurate_master_list()

    def get_rename_paths(self, newName):
        old_new_paths = super(SaveInfo, self).get_rename_paths(newName)
        # super call added the backup paths but not the actual rename cosave
        # paths inside the store_dir - add those only if they exist
        old, new = old_new_paths[0] # HACK: (oldName.ess, newName.ess) abspaths
        for co_type, co_file in self._co_saves.items():
            old_new_paths.append((co_file.abs_path,
                                  co_type.get_cosave_path(new)))
        return old_new_paths

#------------------------------------------------------------------------------
class ScreenInfo(FileInfo):
    """Cached screenshot, stores a bitmap and refreshes it when its cache is
    invalidated."""
    _valid_exts_re = r'(\.(?:' + '|'.join(
        ext[1:] for ext in ss_image_exts) + '))'
    _has_digits = True

    def __init__(self, fullpath, load_cache=False, itsa_ghost=None):
        self.cached_bitmap = None
        super(ScreenInfo, self).__init__(fullpath, load_cache)

    def _reset_cache(self, stat_tuple, load_cache):
        self.cached_bitmap = None # Lazily reloaded
        super(ScreenInfo, self)._reset_cache(stat_tuple, load_cache)

    @classmethod
    def get_store(cls): return screen_infos

#------------------------------------------------------------------------------
class DataStore(DataDict):
    """Base class for the singleton collections of infos."""
    store_dir = empty_path # where the data sit, static except for SaveInfos

    def __init__(self, store_dict=None):
        super().__init__(FNDict() if store_dict is None else store_dict)

    def delete(self, delete_keys, *, recycle=True):
        """Deletes member file(s)."""
        full_delete_paths, delete_info = self.files_to_delete(delete_keys)
        try:
            self._delete_operation(full_delete_paths, delete_info,
                recycle=recycle)
        finally:
            self.delete_refresh(full_delete_paths, delete_info,
                check_existence=True)

    def files_to_delete(self, filenames, **kwargs):
        raise NotImplementedError

    def _delete_operation(self, paths, delete_info, *, recycle=True):
        env.shellDelete(paths, recycle=recycle)

    def filter_essential(self, fn_items: Iterable[FName]):
        """Filters essential files out of the specified filenames. Useful to
        determine whether or not a file will cause instability when
        deleted/hidden."""
        return fn_items

    def delete_refresh(self, deleted, deleted2, check_existence):
        raise NotImplementedError

    def refresh(self): raise NotImplementedError
    def save(self): pass # for Screenshots

    def rename_operation(self, member_info, newName):
        rename_paths = member_info.get_rename_paths(newName)
        for tup in rename_paths[1:]: # first rename path must always exist
            # if cosaves or backups do not exist shellMove fails!
            # if filenames are the same (for instance cosaves in disabling
            # saves) shellMove will offer to skip and raise SkipError
            if tup[0] == tup[1] or not tup[0].exists():
                rename_paths.remove(tup)
        env.shellMove(dict(rename_paths))
        old_key = member_info.fn_key
        ##: Make sure we pass FName in, then drop this FName call
        member_info.fn_key = FName(newName)
        #--FileInfos
        self[newName] = member_info
        del self[old_key]
        return old_key

    @property
    def bash_dir(self):
        """Return the folder where Bash persists its data - create it on init!
        :rtype: bolt.Path"""
        raise NotImplementedError

    @property
    def hidden_dir(self):
        """Return the folder where Bash should move the file info to hide it
        :rtype: bolt.Path"""
        return self.bash_dir.join(u'Hidden')

    def move_infos(self, sources, destinations, window, bash_frame):
        # hasty hack for Files_Unhide, must absorb move_info
        try:
            env.shellMove(dict(zip(sources, destinations)), parent=window)
        except (CancelError, SkipError):
            pass
        return forward_compat_path_to_fn_list(
            {d.stail for d in destinations if d.exists()}, ret_type=set)

class TableFileInfos(DataStore):
    _bain_notify = True # notify BAIN on deletions/updates ?
    file_pattern = None # subclasses must define this !

    def _initDB(self, dir_):
        self.store_dir = dir_ #--Path
        deprint(f'Initializing {self.__class__.__name__}')
        deprint(f' store_dir: {self.store_dir}')
        deprint(f' bash_dir: {self.bash_dir}')
        self.store_dir.makedirs()
        self.bash_dir.makedirs() # self.store_dir may need be set
        # the type of the table keys is always bolt.FName
        self.table = bolt.DataTable(
            bolt.PickleDict(self.bash_dir.join(u'Table.dat')))
        ##: fix nightly regression storing FName as installer property
        inst_column = self.table.getColumn('installer')
        for fn_key, val in inst_column.items():
            if type(val) is not str:
                deprint(f'stored installer for {fn_key} is {val!r}')
                inst_column[fn_key] = str(val)
        self._data = FNDict()
        return self._data

    def __init__(self, dir_, factory=AFile):
        """Init with specified directory and specified factory type."""
        super().__init__(self._initDB(dir_))
        self.factory=factory

    def new_info(self, fileName, *, _in_refresh=False, owner=None,
                 notify_bain=False, itsa_ghost=None):
        """Create, add to self and return a new info using self.factory.
        It will try to read the file to cache its header etc, so use on
        existing files. WIP, in particular _in_refresh must go, but that
        needs rewriting corrupted handling."""
        info = self[fileName] = self.factory(self.store_dir.join(fileName),
            load_cache=True, itsa_ghost=itsa_ghost)
        if owner is not None:
            info.set_table_prop('installer', f'{owner}')
        if notify_bain:
            self._notify_bain(altered={info.abs_path})
        return info

    def _list_store_dir(self): # performance intensive
        file_matches_store = self.rightFileType
        return FNDict((x, False) for x in top_level_files(self.store_dir) if
                      file_matches_store(x))

    #--Right File Type?
    @classmethod
    def rightFileType(cls, fileName: bolt.FName | str):
        """Check if the filetype (extension) is correct for subclass.
        :rtype: _sre.SRE_Match | None"""
        return cls.file_pattern.search(fileName)

    #--Delete
    def files_to_delete(self, fileNames, **kwargs):
        abs_delete_paths = []
        #--Cache table updates
        tableUpdate = {}
        #--Go through each file
        for fileName in self.filter_essential(fileNames):
            try:
                fileInfo = self[fileName]
            except KeyError: # corrupted
                fileInfo = self.factory(self.store_dir.join(fileName))
            #--File
            filePath = fileInfo.abs_path
            abs_delete_paths.append(filePath)
            self._additional_deletes(fileInfo, abs_delete_paths)
            #--Table
            tableUpdate[filePath] = fileName
        #--Now do actual deletions
        abs_delete_paths = {x for x in abs_delete_paths if x.exists()}
        return abs_delete_paths, tableUpdate

    def _update_deleted_paths(self, deleted_keys, paths_to_keys,
                              check_existence):
        """Must be called BEFORE we remove the keys from self."""
        if paths_to_keys is None: # we passed the keys in, get the paths
            paths_to_keys = {self[n].abs_path: n for n in deleted_keys}
        if check_existence:
            for filePath in list(paths_to_keys):
                if filePath.exists():
                    del paths_to_keys[filePath] # item was not deleted
        self._notify_bain(deleted=paths_to_keys)
        return list(paths_to_keys.values())

    def _notify_bain(self, deleted: set[Path] = frozenset(),
        altered: set[Path] = frozenset(), renamed: dict[Path, Path] = {}):
        """Note that all of these parameters need to be absolute paths!"""
        if self.__class__._bain_notify:
            InstallersData.notify_external(deleted=deleted, altered=altered,
                                           renamed=renamed)

    def _additional_deletes(self, fileInfo, toDelete): pass

    def save(self):
        # items deleted outside Bash
        for deleted in set(self.table) - set(self):
            del self.table[deleted]
        self.table.save()

    def rename_operation(self, member_info, newName):
        # Override to allow us to notify BAIN if necessary
        ##: This is *very* inelegant/inefficient, we calculate these paths
        # twice (once here and once in super)
        self._notify_bain(renamed=dict(member_info.get_rename_paths(newName)))
        return super(TableFileInfos, self).rename_operation(member_info, newName)

    #--Copy
    def copy_info(self, fileName, destDir, destName=empty_path, set_mtime=None,
                  save_lo_cache=False):
        """Copies member file to destDir. Will overwrite! Will update
        internal self.data for the file if copied inside self.info_dir but the
        client is responsible for calling the final refresh of the data store.
        See usages.

        :param save_lo_cache: ModInfos only save the mod infos load order cache
        :param set_mtime: if None self[fileName].mtime is copied to destination
        """
        destDir.makedirs()
        if not destName: destName = fileName
        src_info = self[fileName]
        if destDir == self.store_dir and destName in self:
            destPath = self[destName].abs_path
        else:
            destPath = destDir.join(destName)
        self._do_copy(src_info, destPath)
        if destDir == self.store_dir:
            # TODO(ut) : pass the info in and load_cache=False
            self.new_info(destName, notify_bain=True)
            self.table.copyRow(fileName, destName)
            if set_mtime is not None:
                self[destName].setmtime(set_mtime) # correctly update table
        return set_mtime

    def _do_copy(self, cp_file_info, cp_dest_path):
        """Performs the actual copy operation, copying the file represented by
        the specified FileInfo to the specified destination path."""
        # Will set the destination's mtime to the source's mtime
        cp_file_info.abs_path.copyTo(cp_dest_path)

class FileInfos(TableFileInfos):
    """Common superclass for mod, saves and bsa infos."""

    def _initDB(self, dir_):
        self.corrupted = FNDict() #--errorMessage = corrupted[fileName]
        return super()._initDB(dir_)

    #--Refresh File
    def new_info(self, fileName, _in_refresh=False, owner=None,
                 notify_bain=False, itsa_ghost=None):
        try:
            fileInfo = super(FileInfos, self).new_info(fileName, owner=owner,
                notify_bain=notify_bain, itsa_ghost=itsa_ghost)
            self.corrupted.pop(fileName, None)
            return fileInfo
        except FileError as error:
            if not _in_refresh: # if refresh just raise so we print the error
                self.corrupted[fileName] = error.message
                self.pop(fileName, None)
            raise

    #--Refresh
    def refresh(self, refresh_infos=True, booting=False):
        """Refresh from file directory."""
        oldNames = set(self) | set(self.corrupted)
        _added = set()
        _updated = set()
        newNames = self._list_store_dir()
        for new, itsa_ghost in newNames.items(): #--Might have '.ghost' lopped off
            oldInfo = self.get(new) # None if new was in corrupted or new one
            try:
                if oldInfo is not None:
                    if oldInfo.do_update(itsa_ghost=itsa_ghost): # will reread the header
                        _updated.add(new)
                else: # added or known corrupted, get a new info
                    self.new_info(new, _in_refresh=True,
                        notify_bain=not booting, itsa_ghost=itsa_ghost)
                    _added.add(new)
            except FileError as e: # old still corrupted, or new(ly) corrupted
                if not new in self.corrupted \
                        or self.corrupted[new] != e.message:
                    deprint(f'Failed to load {new}: {e.message}',
                        traceback=True)
                    self.corrupted[new] = e.message
                self.pop(new, None)
        _deleted_ = oldNames - set(newNames)
        self.delete_refresh(_deleted_, None, check_existence=False,
                            _in_refresh=True)
        if _updated:
            self._notify_bain(altered={self[n].abs_path for n in _updated})
        change = bool(_added) or bool(_updated) or bool(_deleted_)
        if not change: return change
        return _added, _updated, _deleted_

    def delete_refresh(self, deleted_keys, paths_to_keys, check_existence,
                       _in_refresh=False):
        """Special case for the saves, inis, mods and bsas.
        :param deleted_keys: must be the data store keys and not full paths
        :param paths_to_keys: a dict mapping full paths to the keys
        """
        #--Table
        deleted = self._update_deleted_paths(deleted_keys, paths_to_keys,
                                             check_existence)
        if not deleted: return deleted
        for del_fn in deleted:
            self.pop(del_fn, None)
            self.corrupted.pop(del_fn, None)
            self.table.pop(del_fn, None)
        return deleted

    def _additional_deletes(self, fileInfo, toDelete):
        #--Backups
        toDelete.extend(fileInfo.all_backup_paths()) # will include cosave ones

    #--Rename
    def rename_operation(self, member_info, newName):
        """Renames member file from oldName to newName."""
        #--Update references
        #--File system
        old_key = super(FileInfos, self).rename_operation(member_info, newName)
        #--FileInfo
        member_info.abs_path = self.store_dir.join(newName)
        self.table.moveRow(old_key, newName)
        # self[newName]._mark_unchanged() # not needed with shellMove !
        return old_key

    #--Move
    def move_info(self, fileName, destDir):
        """Moves member file to destDir. Will overwrite! The client is
        responsible for calling delete_refresh of the data store."""
        srcPath = self[fileName].getPath()
        destPath = destDir.join(fileName)
        srcPath.moveTo(destPath)

#------------------------------------------------------------------------------
##: Can we simplify this now and obsolete AINIInfo?
class INIInfo(IniFile, AINIInfo):
    _valid_exts_re = r'(\.(?:' + '|'.join(
        x[1:] for x in supported_ini_exts) + '))'

    def _reset_cache(self, stat_tuple, load_cache):
        super(INIInfo, self)._reset_cache(stat_tuple, load_cache)
        if load_cache: self._status = None ##: is the if check needed here?

class ObseIniInfo(OBSEIniFile, INIInfo): pass

class DefaultIniInfo(DefaultIniFile, AINIInfo):
    is_default_tweak = True

    @property
    def info_dir(self):
        return dirs['ini_tweaks']

# noinspection PyUnusedLocal
def ini_info_factory(fullpath, load_cache=u'Ignored',
        itsa_ghost=False) -> INIInfo:
    """INIInfos factory

    :param fullpath: Full path to the INI file to wrap
    :param load_cache: Dummy param used in INIInfos.new_info factory call
    :param itsa_ghost: Cached ghost status information, ignored for INIs"""
    inferred_ini_type, detected_encoding = get_ini_type_and_encoding(fullpath)
    ini_info_type = (ObseIniInfo if inferred_ini_type == OBSEIniFile
                     else INIInfo)
    return ini_info_type(fullpath, detected_encoding)

class INIInfos(TableFileInfos):
    """:type _ini: IniFile
    :type data: dict[bolt.Path, IniInfo]"""
    file_pattern = re.compile('|'.join(
        f'\\{x}' for x in supported_ini_exts) + '$' , re.I)

    def __init__(self):
        self._default_tweaks = FNDict((k, DefaultIniInfo(k, v)) for k, v in
                                      bush.game.default_tweaks.items())
        super().__init__(dirs['ini_tweaks'], factory=ini_info_factory)
        self._ini = None
        # Check the list of target INIs, remove any that don't exist
        # if _target_inis is not an OrderedDict choice won't be set correctly
        _target_inis = bass.settings[u'bash.ini.choices'] # type: OrderedDict
        choice = bass.settings[u'bash.ini.choice'] # type: int
        if isinstance(_target_inis, OrderedDict):
            try:
                previous_ini = list(_target_inis)[choice]
                ##: HACK - sometimes choice points to Browse... - real fix
                # is to remove Browse from the list of inis....
                if _target_inis[previous_ini] is None:
                    choice, previous_ini = -1, None
            except IndexError:
                choice, previous_ini = -1, None
        else: # not an OrderedDict, updating from 306
            choice, previous_ini = -1, None
        # Make a copy, we may modify the _target_inis dict
        for ini_name, ini_path in list(_target_inis.items()):
            if ini_name == _(u'Browse...'): continue
            # If user started with non-translated, 'Browse...'
            # will still be in here, but in English.  It wont get picked
            # up by the previous check, so we'll just delete any non-Path
            # objects.  That will take care of it.
            if not isinstance(ini_path,bolt.Path) or not ini_path.is_file():
                if get_game_ini(ini_path):
                    continue # don't remove game inis even if missing
                del _target_inis[ini_name]
                if ini_name is previous_ini:
                    choice, previous_ini = -1, None
        try:
            csChoices = {x.lower() for x in _target_inis}
        except AttributeError: # 'Path' object has no attribute 'lower'
            deprint(f'_target_inis contain a Path {list(_target_inis)}')
            csChoices = {f'{x}'.lower() for x in _target_inis}
        for iFile in gameInis: # add the game inis even if missing
            if iFile.fn_key not in csChoices:
                _target_inis[iFile.abs_path.stail] = iFile.abs_path
        if _(u'Browse...') not in _target_inis:
            _target_inis[_(u'Browse...')] = None
        self.__sort_target_inis()
        if previous_ini:
            choice = list(bass.settings[u'bash.ini.choices']).index(
                previous_ini)
        bass.settings[u'bash.ini.choice'] = choice if choice >= 0 else 0
        self.ini = list(bass.settings[u'bash.ini.choices'].values())[
            bass.settings[u'bash.ini.choice']]

    @property
    def ini(self):
        return self._ini
    @ini.setter
    def ini(self, ini_path):
        """:type ini_path: bolt.Path"""
        if self._ini is not None and self._ini.abs_path == ini_path:
            return # nothing to do
        self._ini = BestIniFile(ini_path)
        for ini_info in self.values(): ini_info.reset_status()

    @staticmethod
    def update_targets(targets_dict):
        """Update 'bash.ini.choices' with targets_dict then re-sort the dict
        of target INIs"""
        for existing_ini in bass.settings[u'bash.ini.choices']:
            targets_dict.pop(existing_ini, None)
        if targets_dict:
            bass.settings[u'bash.ini.choices'].update(targets_dict)
            # now resort
            INIInfos.__sort_target_inis()
        return targets_dict

    @staticmethod
    def __sort_target_inis():
        # Sort non-game INIs alphabetically
        keys = sorted(bass.settings[u'bash.ini.choices'])
        # Sort game INIs to the top, and 'Browse...' to the bottom
        game_inis = bush.game.Ini.dropdown_inis
        len_inis = len(game_inis)
        keys.sort(key=lambda a: game_inis.index(a) if a in game_inis else (
                      len_inis + 1 if a == _(u'Browse...') else len_inis))
        bass.settings[u'bash.ini.choices'] = collections.OrderedDict(
            # convert stray Path instances back to unicode
            [(f'{k}', bass.settings['bash.ini.choices'][k]) for k in keys])

    def _refresh_ini_tweaks(self):
        """Refresh from file directory."""
        oldNames = {n for n, v in self.items() if not v.is_default_tweak}
        _added = set()
        _updated = set()
        newNames = self._list_store_dir()
        for new_tweak in newNames:
            oldInfo = self.get(new_tweak) # None if new_tweak was added
            if oldInfo is not None and not oldInfo.is_default_tweak:
                if oldInfo.do_update(): _updated.add(new_tweak)
            else: # added
                tweak_path = self.store_dir.join(new_tweak)
                try:
                    oldInfo = self.factory(tweak_path)
                except UnicodeDecodeError:
                    deprint(f'Failed to read {tweak_path}', traceback=True)
                    continue
                except (BoltError, NotImplementedError) as e:
                    deprint(e.message)
                    continue
                _added.add(new_tweak)
            self[new_tweak] = oldInfo
        _deleted_ = oldNames - set(newNames)
        self.delete_refresh(_deleted_, None, check_existence=False,
                            _in_refresh=True)
        # re-add default tweaks
        for k in list(self):
            if k not in newNames: del self[k]
        for k, default_info in self._missing_default_inis():
            self[k] = default_info # type: DefaultIniInfo
            if k in _deleted_: # we restore default over copy
                _updated.add(k)
                default_info.reset_status()
        if _updated:
            self._notify_bain(altered={self[n].abs_path for n in _updated})
        return _added, _deleted_, _updated

    def _missing_default_inis(self):
        return ((k, v) for k, v in self._default_tweaks.items() if
                k not in self)

    def refresh(self, refresh_infos=True, refresh_target=True):
        _added = _deleted_ = _updated = set()
        if refresh_infos:
            _added, _deleted_, _updated = self._refresh_ini_tweaks()
        change = refresh_target and (self.ini.updated or self.ini.do_update())
        if change: # reset the status of all infos and let RefreshUI set it
            self.ini.updated = False
            for ini_info in self.values(): ini_info.reset_status()
        change = bool(_added) or bool(_updated) or bool(_deleted_) or change
        if not change: return change
        return _added, _updated, _deleted_, change

    @property
    def bash_dir(self): return dirs[u'modsBash'].join(u'INI Data')

    def delete_refresh(self, deleted_keys, paths_to_keys, check_existence,
                       _in_refresh=False):
        deleted = self._update_deleted_paths(deleted_keys, paths_to_keys,
                                             check_existence)
        if not deleted: return deleted
        for del_fn in deleted:
            self.pop(del_fn, None)
            self.table.delRow(del_fn)
        if not _in_refresh: # re-add default tweaks
            for k, default_info in self._missing_default_inis():
                self[k] = default_info  # type: DefaultIniInfo
                default_info.reset_status()
        return deleted

    def filter_essential(self, fn_items: Iterable[FName]):
        # Can't remove default tweaks
        return (i for i in fn_items if not self[i].is_default_tweak)

    def get_tweak_lines_infos(self, tweakPath):
        return self._ini.analyse_tweak(self[tweakPath])

    def _copy_to_new_tweak(self, info, fn_new_tweak: FName):
        """Duplicate tweak into fn_new_teak."""
        with open(self.store_dir.join(fn_new_tweak), 'wb') as ini_file:
            ini_file.write(info.read_ini_content(as_unicode=False)) # binary
        return self.new_info(fn_new_tweak, notify_bain=True)

    def copy_tweak_from_target(self, tweak, fn_new_tweak: FName):
        """Duplicate tweak into fn_new_teak, but with the settings that are
        currently written in the target INI."""
        if not fn_new_tweak: return False
        dup_info = self._copy_to_new_tweak(self[tweak], fn_new_tweak)
        # Now edit it with the values from the target INI
        new_tweak_settings = bolt.LowerDict(dup_info.get_ci_settings())
        target_settings = self.ini.get_ci_settings()
        for section in new_tweak_settings:
            if section in target_settings:
                for setting in new_tweak_settings[section]:
                    if setting in target_settings[section]:
                        new_tweak_settings[section][setting] = \
                            target_settings[section][setting]
        for k, v in list(new_tweak_settings.items()): # drop line numbers
            new_tweak_settings[k] = { # saveSettings converts to LowerDict
                sett: val[0] for sett, val in v.items()}
        dup_info.saveSettings(new_tweak_settings)
        return True

    # FileInfos stuff ---------------------------------------------------------
    def _do_copy(self, cp_file_info, cp_dest_path):
        if cp_file_info.is_default_tweak:
            # Default tweak, so the file doesn't actually exist
            self._copy_to_new_tweak(cp_file_info, FName(cp_dest_path.stail))
        else:
            super()._do_copy(cp_file_info, cp_dest_path)

def _lo_cache(lord_func):
    """Decorator to make sure I sync modInfos cache with load_order cache
    whenever I change (or attempt to change) the latter, and that I do
    refresh modInfos."""
    @wraps(lord_func)
    def _modinfos_cache_wrapper(self, *args, **kwargs):
        """Sync the ModInfos load order and active caches and refresh for
        load order or active changes.

        :type self: ModInfos
        :return: 1 if only load order changed, 2 if only active changed,
        3 if both changed else 0
        """
        try:
            old_lo, old_active = load_order.cached_lo_tuple(), \
                                 load_order.cached_active_tuple()
            lord_func(self, *args, **kwargs)
            lo, active = load_order.cached_lo_tuple(), \
                         load_order.cached_active_tuple()
            lo_changed = lo != old_lo
            active_changed = active != old_active
            active_set = set(active)
            old_active_set = set(old_active)
            active_set_changed = active_changed and (
                    active_set != old_active_set)
            if active_changed:
                self._refresh_mod_inis() # before _refreshMissingStrings !
                self._refreshBadNames()
                self._reset_info_sets()
                self._refreshMissingStrings()
            #if lo changed (including additions/removals) let refresh handle it
            if active_set_changed or (set(lo) - set(old_lo)): # new mods, ghost
                self.autoGhost(force=False)
            # Always recalculate the real indices - any LO change requires us
            # to do this. We could technically be smarter, but this takes <1ms
            # even with hundreds of plugins
            self._recalc_real_indices()
            # Same reasoning goes for dependents as well
            self._recalc_dependents()
            new_active = active_set - old_active_set
            for neu in new_active: # new active mods, unghost
                self[neu].setGhost(False)
            return (lo_changed and 1) + (active_changed and 2)
        finally:
            self._lo_wip = list(load_order.cached_lo_tuple())
            self._active_wip = list(load_order.cached_active_tuple())
    return _modinfos_cache_wrapper

def _bsas_from_ini(bsa_ini, bsa_key, available_bsas):
    """Helper method for get_bsa_lo and friends. Retrieves BSA paths from an
    INI file."""
    r_bsas = (x.strip() for x in
              bsa_ini.getSetting(u'Archive', bsa_key, u'').split(u','))
    return (available_bsas[b] for b in r_bsas if b in available_bsas)

#------------------------------------------------------------------------------
class ModInfos(FileInfos):
    """Collection of modinfos. Represents mods in the Data directory."""

    def __init__(self):
        exts = '|'.join([f'\\{e}' for e in bush.game.espm_extensions])
        self.__class__.file_pattern = re.compile(fr'({exts})(\.ghost)?$', re.I)
        FileInfos.__init__(self, dirs[u'mods'], factory=ModInfo)
        #--Info lists/sets
        self.mergeScanned = [] #--Files that have been scanned for mergeability.
        if dirs[u'mods'].join(bush.game.master_file).is_file():
            self._master_esm = bush.game.master_file
        else:
            raise FileError(bush.game.master_file,
                            u'File is required, but could not be found')
        # Maps plugins to 'real indices', i.e. the ones the game will assign.
        self.real_indices = collections.defaultdict(lambda: sys.maxsize)
        self.real_index_strings = collections.defaultdict(lambda: '')
        # Maps each plugin to a set of all plugins that have it as a master
        self.dependents = collections.defaultdict(set)
        self.mergeable = set() #--Set of all mods which can be merged.
        self.bad_names = set() #--Set of all mods with names that can't be saved to plugins.txt
        self.missing_strings = set() #--Set of all mods with missing .STRINGS files
        self.new_missing_strings = set() #--Set of new mods with missing .STRINGS files
        self.activeBad = set() #--Set of all mods with bad names that are active
        # Set of plugins with form versions < RecordHeader.plugin_form_version
        self.older_form_versions = set()
        # sentinel for calculating info sets when needed in gui and patcher
        # code, **after** self is refreshed
        self.__calculate = object()
        self._reset_info_sets()
        #--Oblivion version
        self.voCurrent = None
        self.voAvailable = set()
        # removed/extra mods in plugins.txt - set in load_order.py,
        # used in RefreshData
        self.selectedBad = set()
        self.selectedExtra = []
        load_order.initialize_load_order_handle(self, bush.game.fsName)
        # Load order caches to manipulate, then call our save methods - avoid !
        self._active_wip = []
        self._lo_wip = []

    # merged, bashed_patches, imported caches
    def _reset_info_sets(self):
        self._merged = self._imported = self._bashed_patches = self.__calculate

    @property
    def imported(self):
        if self._imported is self.__calculate:
            self._merged, self._imported = self.getSemiActive()
        return self._imported

    @property
    def merged(self):
        if self._merged is self.__calculate:
            self._merged, self._imported = self.getSemiActive()
        return self._merged

    @property
    def bashed_patches(self):
        if self._bashed_patches is self.__calculate:
            self._bashed_patches = {mname for mname, modinf in self.items()
                                    if modinf.isBP()}
        return self._bashed_patches

    # Load order API for the rest of Bash to use - if the load order or
    # active plugins changed, those methods run a refresh on modInfos data
    @_lo_cache
    def refreshLoadOrder(self, forceRefresh=True, forceActive=True,
                         unlock_lo=False):
        def _do_lo_refresh():
            load_order.refresh_lo(cached=not forceRefresh,
                                  cached_active=not forceActive)
        # Needed for BAIN, which may have to reorder installed plugins
        if unlock_lo:
            with load_order.Unlock(): _do_lo_refresh()
        else: _do_lo_refresh()

    @_lo_cache
    def cached_lo_save_active(self, active=None):
        """Write data to Plugins.txt file.

        Always call AFTER setting the load order - make sure we unghost
        ourselves so ctime of the unghosted mods is not set."""
        load_order.save_lo(load_order.cached_lo_tuple(),
            load_order.cached_lord.lorder(
                self._active_wip if active is None else active))

    @_lo_cache
    def cached_lo_save_lo(self):
        """Save load order when active did not change."""
        load_order.save_lo(self._lo_wip)

    @_lo_cache
    def cached_lo_save_all(self):
        """Save load order and plugins.txt"""
        active_wip_set = set(self._active_wip)
        dex = {x: i for i, x in enumerate(self._lo_wip) if
               x in active_wip_set}
        self._active_wip.sort(key=dex.__getitem__) # order in their load order
        load_order.save_lo(self._lo_wip, acti=self._active_wip)

    @_lo_cache
    def undo_load_order(self): return load_order.undo_load_order()

    @_lo_cache
    def redo_load_order(self): return load_order.redo_load_order()

    #--Load Order utility methods - be sure cache is valid when using them
    def cached_lo_insert_after(self, previous, new_mod):
        previous_index = self._lo_wip.index(previous)
        if not bush.game.using_txt_file:
            # set the mtime to avoid reordering all subsequent mods
            try:
                next_mod = self._lo_wip[previous_index + 1]
            except IndexError: # last mod
                next_mod = None
            end_time = self[next_mod].mtime if next_mod else None
            start_time  = self[previous].mtime
            if end_time is not None and \
                    end_time <= start_time: # can happen on esm/esp boundary
                start_time = end_time - 60.0
            set_time = load_order.get_free_time(start_time, end_time=end_time)
            self[new_mod].setmtime(set_time)
        self._lo_wip[previous_index + 1:previous_index + 1] = [
            self[new_mod].fn_key] ##: new_mod is not always an FName

    def cached_lo_last_esm(self):
        last_esm = self._master_esm
        for mod in self._lo_wip[1:]:
            if not self[mod].in_master_block(): return last_esm
            last_esm = mod
        return last_esm

    def cached_lo_insert_at(self, first, modlist):
        # hasty method for Mod_OrderByName
        mod_set = set(modlist)
        first_dex = self._lo_wip.index(first)
        # Begin by splitting out the remainder
        rest = self._lo_wip[first_dex:]
        del self._lo_wip[first_dex:]
        # Clean out any duplicates left behind, in case we're moving forwards
        self._lo_wip[:] = [x for x in self._lo_wip if x not in mod_set]
        # Append the remainder, then insert the requested plugins
        for mod in rest:
            if mod in mod_set: continue
            self._lo_wip.append(mod)
        self._lo_wip[first_dex:first_dex] = modlist

    def cached_lo_append_if_missing(self, mods):
        new = mods - set(self._lo_wip)
        if not new: return
        esms = {x for x in new if self[x].in_master_block()}
        if esms:
            last = self.cached_lo_last_esm()
            for esm in esms:
                self.cached_lo_insert_after(last, esm)
                last = esm
            new -= esms
        self._lo_wip.extend(new)
        self.cached_lo_save_lo()

    @staticmethod
    def hexIndexString(mod):
        return '' if not load_order.cached_is_active(mod) else \
            f'{load_order.cached_active_index(mod):02X}'

    def masterWithVersion(self, master_name):
        if master_name == 'Oblivion.esm' and self.voCurrent:
            master_name += f' [{self.voCurrent}]'
        return master_name

    def dropItems(self, dropItem, firstItem, lastItem): # MUTATES plugins CACHE
        # Calculating indexes through order.index() cause we may be called in
        # a row before saving the modified load order
        order = self._lo_wip
        newPos = order.index(dropItem)
        if newPos <= 0: return False
        start = order.index(firstItem)
        stop = order.index(lastItem) + 1  # excluded
        # Can't move the game's master file anywhere else but position 0
        if self._master_esm in order[start:stop]: return False
        # List of names to move removed and then reinserted at new position
        toMove = order[start:stop]
        del order[start:stop]
        order[newPos:newPos] = toMove
        return True

    @property
    def bash_dir(self): return dirs[u'modsBash']

    #--Refresh-----------------------------------------------------------------
    def _list_store_dir(self):
        """Return a dict specifying if the key is in a ghosted state."""
        fname_to_ghost = super(ModInfos, self)._list_store_dir()
        for mname in list(fname_to_ghost): # initially ghost bits are all False
            if mname.fn_ext == '.ghost':
                del fname_to_ghost[mname] # remove the ghost
                if (unghosted := mname[:-6]) in fname_to_ghost:
                    deprint(f'Both {unghosted} and its ghost exist. The ghost '
                            f'will be ignored but this may lead to undefined '
                            f'behavior - please remove one or the other')
                else:
                    fname_to_ghost[unghosted] = True # a real ghost
        return fname_to_ghost

    def refresh(self, refresh_infos=True, booting=False, _modTimesChange=False):
        """Update file data for additions, removals and date changes.

        See usages for how to use the refresh_infos and _modTimesChange params.
        _modTimesChange is not strictly needed after the lo rewrite, as
        games.LoGame.load_order_changed will always return True for timestamp
        games - kept to help track places in the code where timestamp load
        order may change.
         NB: if an operation we performed changed the load order we do not want
         lock load order to revert our own operation. So either call some of
         the set_load_order methods, or guard refresh (which only *gets* load
         order) with load_order.Unlock.
        """
        change = deleted = False
        # Scan the data dir, getting info on added, deleted and modified files
        if refresh_infos:
            change = FileInfos.refresh(self, booting=booting)
            if change:
                _added, _updated, deleted = change
                # If any plugins have been added, updated or deleted, we need
                # to recalculate dependents
                self._recalc_dependents()
            change = bool(change)
        # If refresh_infos is False and mods are added _do_ manually refresh
        _modTimesChange = _modTimesChange and not bush.game.using_txt_file
        lo_changed = self.refreshLoadOrder(
            forceRefresh=change or _modTimesChange, forceActive=deleted)
        self._refresh_bash_tags()
        # if active did not change, we must perform the refreshes below
        if lo_changed < 2: # in case ini files were deleted or modified
            self._refresh_mod_inis()
        if lo_changed < 2 and change:
            self._refreshBadNames()
            self._reset_info_sets()
        elif lo_changed < 2: # maybe string files were deleted...
            #we need a load order below: in skyrim we read inis in active order
            change |= self._refreshMissingStrings()
        self.voAvailable, self.voCurrent = bush.game.modding_esms(self)
        oldMergeable = set(self.mergeable)
        scanList = self._refreshMergeable()
        difMergeable = (oldMergeable ^ self.mergeable) & set(self)
        if scanList:
            self.rescanMergeable(scanList)
        change |= bool(scanList or difMergeable)
        return bool(change) or lo_changed

    _plugin_inis = OrderedDict() # cache active mod inis in active mods order
    def _refresh_mod_inis(self):
        if not bush.game.Ini.supports_mod_inis: return
        data_folder_path = bass.dirs['mods']
        # First, check the Data folder for INIs present in it. Order does not
        # matter, we will only use this to look up existence
        lower_data_cont = (f.lower() for f in os.listdir(data_folder_path))
        present_inis = {i for i in lower_data_cont if i.endswith('.ini')}
        # Determine which INIs are active based on LO. Order now matters
        possible_inis = [self[m].get_ini_name() for m in
                         load_order.cached_active_tuple()]
        active_inis = [i for i in possible_inis if i.lower() in present_inis]
        # Delete now inactive or deleted INIs from the cache
        if self._plugin_inis: # avoid on boot
            active_inis_lower = {i.lower() for i in active_inis}
            for prev_ini in list(self._plugin_inis):
                if prev_ini.stail.lower() not in active_inis_lower:
                    del self._plugin_inis[prev_ini]
        # Add new or modified INIs to the cache and copy the final order
        data_join = bass.dirs['mods'].join
        ini_order = []
        for acti_ini_name in active_inis:
            # Need to restore the full path here since we'll stat that path
            # when resetting the cache during __init__
            acti_ini_path = data_join(acti_ini_name)
            acti_ini = self._plugin_inis.get(acti_ini_path)
            if acti_ini is None or acti_ini.do_update():
                acti_ini = self._plugin_inis[acti_ini_path] = IniFile(
                    acti_ini_path, 'cp1252')
            ini_order.append((acti_ini_path, acti_ini))
        self._plugin_inis = OrderedDict(ini_order)

    def _refreshBadNames(self):
        """Refreshes which filenames cannot be saved to plugins.txt
        It seems that Skyrim and Oblivion read plugins.txt as a cp1252
        encoded file, and any filename that doesn't decode to cp1252 will
        be skipped."""
        bad = self.bad_names = set()
        activeBad = self.activeBad = set()
        for fileName in self:
            if self.isBadFileName(fileName):
                if load_order.cached_is_active(fileName):
                    ##: For now, we'll leave them active, until we finish
                    # testing what the game will support
                    #self.lo_deactivate(fileName)
                    activeBad.add(fileName)
                else:
                    bad.add(fileName)
        return bool(activeBad)

    def _refreshMissingStrings(self):
        """Refreshes which mods are supposed to have strings files, but are
        missing them (=CTD). For Skyrim you need to have a valid load order."""
        oldBad = self.missing_strings
        # Determine BSA LO from INIs once, this gets expensive very quickly
        cached_ini_info = self.get_bsas_from_inis()
        # Determine the present strings files once to avoid stat'ing
        # non-existent strings files hundreds of times
        try:
            strings_files = os.listdir(bass.dirs['mods'].join('strings'))
            strings_prefix = f'strings{os.path.sep}'
            ci_cached_strings_paths = {strings_prefix + s.lower()
                                       for s in strings_files}
        except FileNotFoundError:
            # No loose strings folder -> all strings are in BSAs
            ci_cached_strings_paths = set()
        self.missing_strings = {
            k for k, v in self.items() if v.isMissingStrings(
                cached_ini_info=cached_ini_info,
                ci_cached_strings_paths=ci_cached_strings_paths)}
        self.new_missing_strings = self.missing_strings - oldBad
        return bool(self.new_missing_strings)

    def autoGhost(self,force=False):
        """Automatically turn inactive files to ghosts.

        Should be called when deactivating mods - will have an effect if
        bash.mods.autoGhost is true, or if force parameter is true (in which
        case, if autoGhost is False, it will actually unghost all ghosted
        mods). If both the mod and its ghost exist, the mod is not active and
        this method runs while autoGhost is on, the normal version will be
        moved to the ghost.
        :param force: set to True only in Mods_AutoGhost, so if fired when
        toggling bash.mods.autoGhost to False we forcibly unghost all mods
        """
        flipped = []
        toGhost = bass.settings[u'bash.mods.autoGhost']
        if force or toGhost:
            allowGhosting = self.table.getColumn(u'allowGhosting')
            for mod, modInfo in self.items():
                modGhost = toGhost and not load_order.cached_is_active(mod) \
                           and allowGhosting.get(mod, True)
                oldGhost = modInfo.isGhost
                newGhost = modInfo.setGhost(modGhost)
                if newGhost != oldGhost:
                    flipped.append(mod)
        return flipped

    def _refreshMergeable(self):
        """Refreshes set of mergeable mods."""
        #--Mods that need to be rescanned - call rescanMergeable !
        newMods = []
        self.mergeable.clear()
        name_mergeInfo = self.table.getColumn(u'mergeInfo')
        #--Add known/unchanged and esms - we need to scan dependent mods
        # first to account for mergeability of their masters
        for fn_mod, modInfo in dict_sort(self, reverse=True,
                                         key_f=load_order.cached_lo_index):
            cached_size, canMerge = name_mergeInfo.get(fn_mod, (None, None))
            # if ESL bit was flipped size won't change, so check this first
            if modInfo.is_esl():
                # Don't mark ESLs as ESL-capable (duh) - modInfo must have its
                # header set
                name_mergeInfo[fn_mod] = (modInfo.fsize, False)
            elif cached_size == modInfo.fsize:
                if canMerge: self.mergeable.add(fn_mod)
            else:
                newMods.append(fn_mod)
        return newMods

    def rescanMergeable(self, names, prog=None, return_results=False):
        """Rescan specified mods. Return value is only meaningful when
        return_results is set to True."""
        messagetext = _(u'Check ESL Qualifications') if bush.game.check_esl \
            else _(u'Mark Mergeable')
        with prog or balt.Progress(messagetext + u' ' * 30) as prog:
            return self._rescanMergeable(names, prog, return_results)

    def _rescanMergeable(self, names, progress, return_results):
        reasons = None if not return_results else []
        if bush.game.check_esl:
            is_mergeable = is_esl_capable
        else:
            is_mergeable = isPBashMergeable
        mod_mergeInfo = self.table.getColumn(u'mergeInfo')
        progress.setFull(max(len(names),1))
        result, tagged_no_merge = OrderedDict(), set()
        for i,fileName in enumerate(names):
            progress(i,fileName)
            fileInfo = self[fileName]
            cs_name = fileName.lower()
            if cs_name in bush.game.bethDataFiles:
                if return_results: reasons.append(_(u'Is Vanilla Plugin.'))
                canMerge = False
            elif fileInfo.is_esl():
                # Do not mark esls as esl capable
                if return_results: reasons.append(_(u'Already ESL-flagged.'))
                canMerge = False
            elif not bush.game.Esp.canBash:
                canMerge = False
            else:
                try:
                    canMerge = is_mergeable(fileInfo, self, reasons)
                except Exception as e:
                    # deprint(f'Error scanning mod {fileName} ({e})')
                    # canMerge = False #presume non-mergeable.
                    raise
            if fileName in self.mergeable and u'NoMerge' in fileInfo.getBashTags():
                tagged_no_merge.add(fileName)
                if return_results: reasons.append(_(u'Technically mergeable '
                                                    u'but has NoMerge tag.'))
            result[fileName] = reasons is not None and (
                    u'\n.    ' + u'\n.    '.join(reasons))
            if canMerge:
                self.mergeable.add(fileName)
                mod_mergeInfo[fileName] = (fileInfo.fsize, True)
            else:
                mod_mergeInfo[fileName] = (fileInfo.fsize, False)
                self.mergeable.discard(fileName)
            reasons = reasons if reasons is None else []
        return result, tagged_no_merge

    def _refresh_bash_tags(self):
        """Reloads bash tags for all mods set to receive automatic bash
        tags."""
        try:
            bt_contents = {t.lower() for t
                           in os.listdir(bass.dirs['tag_files'])}
        except FileNotFoundError:
            bt_contents = set() # No BashTags folder -> no BashTags files
        for modinf in self.values(): # type: ModInfo
            autoTag = modinf.is_auto_tagged(default_auto=None)
            if autoTag is None and modinf.get_table_prop(u'bashTags') is None:
                # A new mod, set auto tags to True (default)
                modinf.set_auto_tagged(True)
                autoTag = True
            elif autoTag is None:
                # An old mod that had manual bash tags added, disable auto tags
                modinf.set_auto_tagged(False)
            if autoTag:
                modinf.reloadBashTags(ci_cached_bt_contents=bt_contents)

    def refresh_crcs(self, mods=None): #TODO(ut) progress !
        pairs = {}
        for mod_key in (self if mods is None else mods):
            inf = self[mod_key]
            pairs[mod_key] = inf.calculate_crc(recalculate=True)
        return pairs

    #--Refresh File
    def new_info(self, fileName, _in_refresh=False, owner=None,
                 notify_bain=False, itsa_ghost=None):
        # we should refresh info sets if we manage to add the info, but also
        # if we fail, which might mean that some info got corrupted
        self._reset_info_sets()
        return super(ModInfos, self).new_info(fileName, _in_refresh, owner,
                                              notify_bain, itsa_ghost)

    #--Mod selection ----------------------------------------------------------
    def getSemiActive(self, patches=None, skip_active=False):
        """Return (merged,imported) mods made semi-active by Bashed Patch.

        If no bashed patches are present in 'patches' then return empty sets.
        Else for each bashed patch use its config (if present) to find mods
        it merges or imports.

        :param patches: A set of mods to look for bashed patches in.
        :param skip_active: If True, only return inactive merged/imported
            plugins."""
        if patches is None: patches = set(load_order.cached_active_tuple())
        merged_,imported_ = set(),set()
        for patch in patches & self.bashed_patches:
            patchConfigs = self.table.getItem(patch, u'bash.patch.configs')
            if not patchConfigs: continue
            if (merger_conf := patchConfigs.get('PatchMerger', {})).get(
                    u'isEnabled'):
                config_checked = merger_conf[u'configChecks']
                for modName, is_merged in forward_compat_path_to_fn(
                        config_checked).items():
                    if is_merged and modName in self:
                        if skip_active and load_order.cached_is_active(
                                modName): continue
                        merged_.add(modName)
            for imp_name in forward_compat_path_to_fn_list(
                    patchConfigs.get('ImportedMods', [])):
                if imp_name in self:
                    if skip_active and load_order.cached_is_active(
                            imp_name): continue
                    imported_.add(imp_name)
        return merged_,imported_

    def getModList(self, showCRC=False, showVersion=True, fileInfo=None,
                   wtxt=False, log_problems=True):
        """Returns mod list as text. If fileInfo is provided will show mod list
        for its masters. Otherwise will show currently loaded mods."""
        #--Setup
        log = bolt.LogFile(io.StringIO())
        head, bul, sMissing, sDelinquent, sImported = (
            '=== ',
            '* ',
            f"  * __{_('Missing Master: %(m_master)s')}__",
            f"  * __{_('Delinquent Master: %(d_master)s')}__",
            '&bull; &bull;'
            ) if wtxt else (
            '',
            '',
            f"----> {_('MISSING MASTER: %(m_master)s')}",
            f"----> {_('DELINQUENT MASTER: %(d_master)s')}",
            '**')
        if fileInfo:
            masters_set = set(fileInfo.masterNames)
            missing = sorted(x for x in masters_set if x not in self)
            log.setHeader(head + _('Missing Masters for %(mm_plugin)s:') % {
                'mm_plugin': fileInfo})
            for mod in missing:
                log(bul + f'xx {mod}')
            log.setHeader(head + _('Masters for %(m_plugin)s:') % {
                'm_plugin': fileInfo})
            present = {x for x in masters_set if x in self}
            if fileInfo.fn_key in self: #--In case is bashed patch (cf getSemiActive)
                present.add(fileInfo.fn_key)
            merged, imported = self.getSemiActive(present)
        else:
            log.setHeader(head + _(u'Active Plugins:'))
            masters_set = set(load_order.cached_active_tuple())
            merged, imported = self.merged, self.imported
        all_mods = (masters_set | merged | imported) & set(self)
        all_mods = load_order.get_ordered(all_mods)
        #--List
        modIndex = 0
        if not wtxt: log(u'[spoiler]\n', appendNewline=False)
        for mname in all_mods:
            if mname in masters_set:
                prefix = f'{bul}{modIndex:02X}'
                modIndex += 1
            elif mname in merged:
                prefix = f'{bul}++'
            else:
                prefix = f'{bul}{sImported}'
            log_str = f'{prefix}  {mname}'
            if showVersion and (vers := self.getVersion(mname)):
                log_str += '  ' + _('[Version %(plugin_ver)s]') % {
                    'plugin_ver': vers}
            if showCRC:
                log_str += '  ' + _('[CRC: %(plugin_crc)s]') % {
                    'plugin_crc': self[mname].crc_string()}
            log(log_str)
            if log_problems and mname in masters_set:
                for master2 in self[mname].masterNames:
                    if master2 not in self:
                        log(sMissing % {'m_master': master2})
                    elif load_order.get_ordered(
                            (mname, master2))[1] == master2:
                        log(sDelinquent % {'d_master': master2})
        if not wtxt: log(u'[/spoiler]')
        return log.out.getvalue()

    @staticmethod
    def _tagsies(modInfo, tagList):
        mname = modInfo.fn_key
        # Tracks if this plugin has at least one bash tags source - which may
        # still result in no tags at the end, e.g. if source A adds a tag and
        # source B removes it
        has_tags_source = False
        def _tags(tags_msg, tags_iter, tagsList):
            tags_result = ', '.join(tags_iter) if tags_iter else _('No tags')
            return f'{tagsList}  * {tags_msg} {tags_result}\n'
        tags_desc = modInfo.getBashTagsDesc()
        has_tags_source |= bool(tags_desc)
        if tags_desc:
            tagList = _tags(_('From Plugin Description:'),
                sorted(tags_desc), tagList)
        loot_added, loot_removed = read_loot_tags(mname)
        has_tags_source |= bool(loot_added | loot_removed)
        if loot_added:
            tagList = _tags(_('From LOOT Masterlist and/or Userlist:'),
                            sorted(loot_added), tagList)
        if loot_removed:
            tagList = _tags(_('Removed by LOOT Masterlist and/or '
                              'Userlist:'), sorted(loot_removed), tagList)
        dir_added, dir_removed = read_dir_tags(mname)
        has_tags_source |= bool(dir_added | dir_removed)
        tags_file_fmt = {'tags_file': f"'{bush.game.mods_dir}/BashTags"
                                      f"/{mname.fn_body}.txt'"}
        if dir_added:
            tagList = _tags(_('Added by %(tags_file)s:') % tags_file_fmt,
                sorted(dir_added), tagList)
        if dir_removed:
            tagList = _tags(_('Removed by %(tags_file)s:') % tags_file_fmt,
                sorted(dir_removed), tagList)
        sorted_tags = sorted(modInfo.getBashTags())
        if not modInfo.is_auto_tagged() and sorted_tags:
            has_tags_source = True
            tagList = _tags(_('From Manual (overrides all other sources):'),
                sorted_tags, tagList)
        return (_tags(_('Result:'), sorted_tags, tagList)
                if has_tags_source else tagList + f"    {_('No tags')}\n")

    def getTagList(self, mod_list=None):
        """Return the list as wtxt of current bash tags (but don't say which
        ones are applied via a patch) - either for all mods in the data folder
        or if specified for one specific mod."""
        tagList = f"=== {_('Current Bash Tags:')}\n"
        tagList += u'[spoiler]\n'
        tagList += _(u'Note: Sources are processed from top to bottom, '
                     u'meaning that lower-ranking sources override '
                     u'higher-ranking ones.') + u'\n'
        if mod_list is None:
            mod_list = []
            # sort output by load order
            for __mname, modInfo in dict_sort(self, key_f=(
                    lambda k: load_order.cached_lo_index(k))):
                if modInfo.getBashTags():
                    mod_list.append(modInfo)
        for modInfo in mod_list:
            tagList += f'\n* {modInfo}\n'
            tagList = self._tagsies(modInfo, tagList)
        tagList += u'[/spoiler]'
        return tagList

    #--Active mods management -------------------------------------------------
    def lo_activate(self, fileName, doSave=True, _modSet=None, _children=None,
                    _activated=None):
        """Mutate _active_wip cache then save if needed."""
        if _activated is None: _activated = set()
        # Skip .esu files, those can't be activated
        ##: This .esu handling needs to be centralized - sprinkled all over
        # actives related lo_* methods
        if fileName.fn_ext == u'.esu': return []
        try:
            espms_extra, esls_extra = load_order.check_active_limit(
                self._active_wip + [fileName])
            if espms_extra or esls_extra:
                msg = f'{fileName}: Trying to activate more than '
                if espms_extra:
                    msg += f'{load_order.max_espms():d} espms'
                else:
                    msg += f'{load_order.max_esls():d} light plugins'
                raise PluginsFullError(msg)
            _children = (_children or tuple()) + (fileName,)
            if fileName in _children[:-1]:
                raise BoltError(f'Circular Masters: {" >> ".join(_children)}')
            #--Select masters
            if _modSet is None: _modSet = set(self)
            #--Check for bad masternames:
            #  Disabled for now
            ##if self[fileName].hasBadMasterNames():
            ##    return
            # Speed up lookups, since they occur for the plugin and all masters
            acti_set = set(self._active_wip)
            for master in self[fileName].masterNames:
                # Check that the master is on disk and not already activated
                if master in _modSet and master not in acti_set:
                    self.lo_activate(master, False, _modSet, _children,
                                     _activated)
            #--Select in plugins
            if fileName not in acti_set:
                self._active_wip.append(fileName)
                _activated.add(fileName)
            return load_order.get_ordered(_activated or [])
        finally:
            if doSave: self.cached_lo_save_active()

    def lo_deactivate(self, fileName, doSave=True):
        """Remove mods and their children from _active_wip, can only raise if
        doSave=True."""
        if not isinstance(fileName, (set, list)): fileName = {fileName}
        notDeactivatable = load_order.must_be_active_if_present()
        fileNames = {x for x in fileName if x not in notDeactivatable}
        old = sel = set(self._active_wip)
        diff = sel - fileNames
        if len(diff) == len(sel): return set()
        #--Unselect self
        sel = diff
        #--Unselect children
        children = set()
        cached_dependents = self.dependents
        for fileName in fileNames:
            children |= cached_dependents[fileName]
        while children:
            child = children.pop()
            if child not in sel: continue # already inactive, skip checks
            sel.remove(child)
            children |= cached_dependents[child]
        # Commit the changes made above
        self._active_wip = [x for x in self._active_wip if x in sel]
        #--Save
        if doSave: self.cached_lo_save_active()
        return old - sel # return deselected

    def lo_activate_all(self, activate_mergeable=True):
        """Activates all non-mergeable plugins (except ones tagged Deactivate),
        then all mergeable plugins (again, except ones tagged Deactivate).
        Raises a PluginsFullError if too many non-mergeable plugins are present
        and a SkippedMergeablePluginsError if too many mergeable plugins are
        present."""
        wip_actives = set(load_order.cached_active_tuple())
        def _add_to_actives(p):
            """Helper for activating a plugin, if necessary."""
            if p not in wip_actives:
                self.lo_activate(p, doSave=False)
                wip_actives.add(p)
        def _activatable(p):
            """Helper for checking if a plugin should be activated."""
            return (p.fn_ext != '.esu' and
                    'Deactivate' not in modInfos[p].getBashTags())
        try:
            s_plugins = load_order.get_ordered(filter(_activatable, self))
            try:
                # First, activate non-mergeable plugins not tagged Deactivate
                for p in s_plugins:
                    if p not in self.mergeable: _add_to_actives(p)
            except PluginsFullError:
                raise
            if activate_mergeable:
                try:
                    # Then activate as many of the mergeable plugins as we can
                    for p in s_plugins:
                        if p in self.mergeable: _add_to_actives(p)
                except PluginsFullError as e:
                    raise SkippedMergeablePluginsError() from e
        except (BoltError, NotImplementedError):
            wip_actives.clear() # Don't save, something went wrong
            raise
        finally:
            if wip_actives: self.cached_lo_save_active(active=wip_actives)

    def lo_activate_exact(self, partial_actives: Iterable[FName]):
        """Activate exactly the specified iterable of plugin names (plus
        required masters and plugins that can't be deactivated). May contain
        missing plugins. Returns a warning message or an empty string."""
        partial_set = set(partial_actives)
        present_plugins = set(self)
        missing_plugins = partial_set - present_plugins
        wip_actives = partial_set - missing_plugins
        def _add_masters(target_plugin):
            """Recursively adds the target and its masters (and their masters,
            and so on)."""
            wip_actives.add(target_plugin)
            for tp_master in self[target_plugin].masterNames:
                if tp_master in self:
                    _add_masters(tp_master)
        # Expand the WIP actives to include all masters and required plugins
        for present_plugin in list(wip_actives):
            if present_plugin.fn_ext != '.esu':
                _add_masters(present_plugin)
        wip_actives |= (load_order.must_be_active_if_present() &
                        present_plugins)
        # Sort the result and check if we would hit an actives limit
        ordered_wip = load_order.get_ordered(wip_actives)
        trim_regular, trim_esl = load_order.check_active_limit(ordered_wip)
        trimmed_plugins = trim_regular | trim_esl
        # Trim off any excess plugins and commit
        self._active_wip = [p for p in ordered_wip if p not in trimmed_plugins]
        self.cached_lo_save_active()
        message = ''
        if missing_plugins:
            message += _('Some plugins could not be found and were '
                         'skipped:') + '\n* '
            message += '\n* '.join(load_order.get_ordered(missing_plugins))
        if trimmed_plugins:
            if missing_plugins:
                message += '\n'
            message += _('Plugin list is full, so some plugins were '
                         'skipped:') + '\n* '
            message += '\n* '.join(load_order.get_ordered(trimmed_plugins))
        return message

    def lo_reorder(self, partial_order: list[FName]):
        """Changes the load order to match the specified potentially invalid
        'partial' load order as much as possible. To that end, it filters out
        plugins that don't exist in the Data folder and tries to insert plugins
        that are present in the Data folder but not in the partial order before
        the same plugin that they are placed before in the current load
        order. Returns a warning message or an empty string."""
        present_plugins = set(self)
        partial_plugins = set(partial_order)
        # Plugins in the partial order that are missing from the Data folder
        excess_plugins = partial_plugins - present_plugins
        filtered_order = [p for p in partial_order if p not in excess_plugins]
        remaining_plugins = present_plugins - set(filtered_order)
        current_order = self._lo_wip
        collected_plugins = []
        left_off = 0
        while remaining_plugins:
            for i, curr_plugin in enumerate(current_order[left_off:]):
                # Look for continuous segments that are missing from the
                # filtered partial load order
                if curr_plugin in remaining_plugins:
                    collected_plugins.append(curr_plugin)
                    remaining_plugins.remove(curr_plugin)
                elif collected_plugins:
                    # We've hit a plugin that's common between current and
                    # filtered orders after a continuous segment, look up the
                    # shared plugin and insert the plugins in the same order
                    # they have in the current order into the filtered order
                    index_in_filtered = filtered_order.index(curr_plugin)
                    for coll_plugin in reversed(collected_plugins):
                        filtered_order.insert(index_in_filtered, coll_plugin)
                    left_off += i + 1
                    collected_plugins = []
                    break # Restart the for loop
            else:
                # Exited the loop without breaking -> some extra plugins should
                # be appended at the end
                filtered_order.extend(collected_plugins)
        self._lo_wip = filtered_order
        self.cached_lo_save_lo()
        message = u''
        if excess_plugins:
            message += _(u'Some plugins could not be found and were '
                         u'skipped:') + u'\n* '
            message += u'\n* '.join(excess_plugins)
        return message

    #--Helpers ----------------------------------------------------------------
    @staticmethod
    def isBadFileName(modName):
        """True if the name cannot be encoded to the proper format for plugins.txt"""
        try:
            modName.encode('cp1252')
            return False
        except UnicodeEncodeError:
            return True

    def ini_files(self): ##: What about SkyrimCustom.ini etc?
        # values in active order, later loading inis override previous settings
        return [*reversed(self._plugin_inis.values()), oblivionIni]

    def create_new_mod(self, newName, selected=(), wanted_masters=None,
                       dir_path=empty_path, is_bashed_patch=False, esm_flag=False,
                       esl_flag=False):
        if wanted_masters is None:
            wanted_masters = [self._master_esm]
        dir_path = dir_path or self.store_dir
        newInfo = self.factory(dir_path.join(newName))
        newFile = ModFile(newInfo)
        newFile.tes4.masters = wanted_masters
        if is_bashed_patch:
            newFile.tes4.author = u'BASHED PATCH'
        if esm_flag:
            newFile.tes4.flags1.esm_flag = True
        if esl_flag:
            newFile.tes4.flags1.esl_flag = True
        newFile.safeSave()
        if dir_path == self.store_dir:
            self.new_info(newName, notify_bain=True)  # notify just in case...
            last_selected = load_order.get_ordered(selected)[
                -1] if selected else self._lo_wip[-1]
            self.cached_lo_insert_after(last_selected, newName)
            self.cached_lo_save_lo()
            self.refresh(refresh_infos=False)

    def generateNextBashedPatch(self, selected_mods):
        """Attempt to create a new bashed patch, numbered from 0 to 9.  If
        a lowered number bashed patch exists, will create the next in the
        sequence."""
        for num in range(10):
            modName = f'Bashed Patch, {num}.esp'
            if modName not in self:
                self.create_new_mod(modName, selected=selected_mods,
                                    wanted_masters=[], is_bashed_patch=True)
                return FName(modName)
        return None

    def get_bsas_from_inis(self):
        """Retrieves BSA load order from INI files. This is separate so that we
        can cache it during early boot for massive speedups. The real solution
        to this is a full BSA LO cache though - see #233 as well."""
        # We'll be removing BSAs from here once we've given them a position
        available_bsas = FNDict(bsaInfos.items())
        bsa_lo = OrderedDict() # Final load order, -1 means it came from an INI
        bsa_cause = {} # Reason each BSA was loaded
        # BSAs from INI files load first
        ini_idx = -sys.maxsize - 1 # Make sure they come first
        for ini_k in bush.game.Ini.resource_archives_keys:
            for ini_f in self.ini_files():
                if ini_f.has_setting(u'Archive', ini_k):
                    for binf in _bsas_from_ini(ini_f, ini_k, available_bsas):
                        bsa_lo[binf] = ini_idx
                        bsa_cause[binf] = f'{ini_f.abs_path.stail} ({ini_k})'
                        ini_idx += 1
                        del available_bsas[binf.fn_key]
                    break # The first INI with the key wins ##: Test this
        # Some games have INI settings that override all other BSAs
        ini_idx = sys.maxsize # Make sure they come last
        res_ov_key = bush.game.Ini.resource_override_key
        if res_ov_key:
            # Start out with the defaults set by the engine
            res_ov_bsas = [available_bsas[b] for b in
                           bush.game.Ini.resource_override_defaults]
            res_ov_cause = f'{bush.game.Ini.dropdown_inis[0]} ({res_ov_key})'
            # Then look if any INIs overwrite them
            for ini_f in self.ini_files():
                if ini_f.has_setting(u'Archive', res_ov_key):
                    res_ov_bsas = _bsas_from_ini(
                        ini_f, res_ov_key, available_bsas)
                    res_ov_cause = f'{ini_f.abs_path.stail} ({res_ov_key})'
                    break # The first INI with the key wins ##: Test this
            for binf in res_ov_bsas:
                bsa_lo[binf] = ini_idx
                bsa_cause[binf] = res_ov_cause
                ini_idx -= 1
                del available_bsas[binf.fn_key]
        return available_bsas, bsa_lo, bsa_cause

    # TODO(inf): Morrowind does not have attached BSAs, there is instead a
    #  'second load order' of BSAs in the INI
    ##: This will need caching in the future - invalidation will be *hard*.
    # Prerequisite for a fully functional BSA tab though (see #233), especially
    # for Morrowind
    def get_bsa_lo(self, for_plugins=None, cached_ini_info=(None, None, None)):
        """Returns the full BSA load order for this game, mapping each BSA to
        the position of its activator mods. Also returns a dict mapping each
        BSA to a string describing the reason it was loaded. If a mod activates
        more than one bsa, their relative order is undefined.

        :param for_plugins: If not None, only returns plugin-name-specific BSAs
            for those plugins. Otherwise, returns it for all plugins.
        :param cached_ini_info: Can contain the result of calling
            get_bsas_from_inis, in which case calling that (fairly expensive)
            method will be skipped."""
        fetch_ini_info = any(c is None for c in cached_ini_info)
        if fetch_ini_info:
            # At least one part of the cached INI info we were passed in is
            # None, which means we need to fetch the info from disk
            available_bsas, bsa_lo, bsa_cause = self.get_bsas_from_inis()
        else:
            # We can use the cached INI info
            available_bsas, bsa_lo, bsa_cause = cached_ini_info
        # BSAs loaded based on plugin name load in the middle of the pack
        if for_plugins is None: for_plugins = list(self)
        for i, p in enumerate(for_plugins):
            for binf in self[p].mod_bsas(available_bsas):
                bsa_lo[binf] = i
                bsa_cause[binf] = p
                del available_bsas[binf.fn_key]
        return bsa_lo, bsa_cause

    def get_active_bsas(self):
        """Returns the load order of all active BSAs. See get_bsa_lo for more
        information."""
        return self.get_bsa_lo(for_plugins=load_order.cached_active_tuple())

    @staticmethod
    def plugin_wildcard(file_str=_(u'Mod Files')):
        joinstar = ';*'.join(bush.game.espm_extensions)
        return f'{bush.game.displayName} {file_str} (*{joinstar})|*{joinstar}'

    #--Mod move/delete/rename -------------------------------------------------
    def _lo_caches_remove_mods(self, to_remove):
        """Remove the specified mods from _lo_wip and _active_wip caches."""
        # Use set to speed up lookups and note that these are strings (at least
        # when they come from delete_refresh, check others?)
        to_remove = {FName(x) for x in to_remove}
        # Remove mods from cache
        self._lo_wip = [x for x in self._lo_wip if x not in to_remove]
        self._active_wip  = [x for x in self._active_wip if x not in to_remove]

    def rename_operation(self, member_info, newName):
        """Renames member file from oldName to newName."""
        isSelected = load_order.cached_is_active(member_info.fn_key)
        if isSelected:
            self.lo_deactivate(member_info, doSave=False) # will save later
        old_key = super(ModInfos, self).rename_operation(member_info, newName)
        # rename in load order caches
        oldIndex = self._lo_wip.index(old_key)
        self._lo_caches_remove_mods([old_key])
        self._lo_wip.insert(oldIndex, newName)
        if isSelected: self.lo_activate(newName, doSave=False)
        # Save to disc (load order and plugins.txt)
        self.cached_lo_save_all()
        return old_key

    #--Delete
    def files_to_delete(self, filenames, **kwargs):
        filenames = set(self.filter_essential(filenames))
        self.lo_deactivate(filenames, doSave=False) ##: do this *after* deletion?
        return super(ModInfos, self).files_to_delete(filenames)

    def delete_refresh(self, deleted, paths_to_keys, check_existence,
                       _in_refresh=False):
        # adapted from refresh() (avoid refreshing from the data directory)
        deleted = super(ModInfos, self).delete_refresh(deleted, paths_to_keys,
                                                       check_existence)
        if not deleted: return
        # temporarily track deleted mods so BAIN can update its UI
        if _in_refresh: return
        self._lo_caches_remove_mods(deleted)
        self.cached_lo_save_all()
        self._refreshBadNames()
        self._reset_info_sets()
        self._refreshMissingStrings()
        self._refreshMergeable()
        self._recalc_dependents()

    def _additional_deletes(self, fileInfo, toDelete):
        super(ModInfos, self)._additional_deletes(fileInfo, toDelete)
        # Add ghosts - the file may exist in both states (bug, or user mistake)
        # if both versions exist file should be marked as normal
        if not fileInfo.isGhost: # add ghost if not added
            ghost_version = self.store_dir.join(fileInfo.fn_key + u'.ghost')
            if ghost_version.exists(): toDelete.append(ghost_version)

    def filter_essential(self, fn_items: Iterable[FName]):
        # Removing the game master breaks everything, for obvious reasons
        return (i for i in fn_items if i != self._master_esm)

    def move_info(self, fileName, destDir):
        """Moves member file to destDir."""
        self.lo_deactivate(fileName, doSave=False)
        FileInfos.move_info(self, fileName, destDir)

    def move_infos(self, sources, destinations, window, bash_frame):
        moved = super(ModInfos, self).move_infos(sources, destinations, window,
                                                 bash_frame)
        self.refresh() # yak, it should have an "added" parameter
        bash_frame.warn_corrupted(warn_mods=True, warn_strings=True)
        return moved

    def copy_info(self, fileName, destDir, destName=empty_path, set_mtime=None,
                  save_lo_cache=False):
        """Copies modfile and optionally inserts into load order cache."""
        super(ModInfos, self).copy_info(fileName, destDir, destName, set_mtime)
        if self.store_dir == destDir:
            self.cached_lo_insert_after(fileName, destName)
        if save_lo_cache: self.cached_lo_save_lo()

    #--Mod info/modify --------------------------------------------------------
    def getVersion(self, fileName):
        """Check we have a fileInfo for fileName and call get_version on it."""
        return self[fileName].get_version() if fileName in self else ''

    #--Oblivion 1.1/SI Swapping -----------------------------------------------
    def _retry(self, old, new):  ##: we should check *before* writing the patch
        msg = _('Bash encountered an error when renaming %(old)s to %(new)s.')
        msg += '\n\n' + _('The file is in use by another process such as '
                          '%(xedit_name)s.') + '\n'
        msg += _('Please close the other program that is accessing %(new)s.')
        msg += '\n\n' + _('Try again?')
        msg %= {'xedit_name': bush.game.Xe.full_name, 'old': old, 'new': new}
        return askYes(self, msg, _('File in use'))

    def setOblivionVersion(self, newVersion):
        """Swaps Oblivion.esm to specified version."""
        baseName = self._master_esm # Oblivion.esm, say it's currently SI one
        # if new version is '1.1' then newName is FName(Oblivion_1.1.esm)
        newName = FName(f'{(fnb := baseName.fn_body)}_{newVersion}.esm')
        newSize = bush.game.modding_esm_size[newName]
        oldSize = self[baseName].fsize
        if newSize == oldSize: return
        current_version = bush.game.size_esm_version[oldSize]
        try: # for instance: Oblivion_SI.esm, we rename Oblivion.esm to this
            oldName = FName(f'{fnb}_{current_version}.esm')
        except KeyError:
            raise StateError("Can't match current main ESM to known version.")
        if self.store_dir.join(oldName).exists():
            raise StateError(f"Can't swap: {oldName} already exists.")
        if newName not in self:
            raise StateError(f"Can't swap: {newName} doesn't exist.")
        newInfo = self[newName]
        #--Rename
        baseInfo = self[self._master_esm]
        master_time = baseInfo.mtime
        new_info_time = newInfo.mtime
        is_master_active = load_order.cached_is_active(self._master_esm)
        is_new_info_active = load_order.cached_is_active(newName)
        # can't use ModInfos rename because it will mess up the load order
        file_info_rename_op = super(ModInfos, self).rename_operation
        while True:
            try:
                file_info_rename_op(baseInfo, oldName)
                break
            except PermissionError: ##: can only occur if SHFileOperation
                # isn't called, yak - file operation API badly needed
                if self._retry(baseInfo.getPath(),
                        self.store_dir.join(oldName)):
                    continue
                raise
            except CancelError:
                return
        while True:
            try:
                file_info_rename_op(newInfo, self._master_esm)
                break
            except PermissionError:
                if self._retry(newInfo.getPath(), baseInfo.getPath()):
                    continue
                #Undo any changes
                file_info_rename_op(oldName, self._master_esm)
                raise
            except CancelError:
                #Undo any changes
                file_info_rename_op(oldName, self._master_esm)
                return
        # set mtimes to previous respective values
        self[self._master_esm].setmtime(master_time)
        self[oldName].setmtime(new_info_time)
        oldIndex = self._lo_wip.index(newName)
        self._lo_caches_remove_mods([newName])
        self._lo_wip.insert(oldIndex, oldName)
        def _activate(active, mod):
            if active:
                self[mod].setGhost(False) # needed if autoGhost is False
                self.lo_activate(mod, doSave=False)
            else: self.lo_deactivate(mod, doSave=False)
        _activate(is_new_info_active, oldName)
        _activate(is_master_active, self._master_esm)
        # Save to disc (load order and plugins.txt)
        self.cached_lo_save_all() # sets ghost as needed iff autoGhost is True
        self.voCurrent = newVersion
        self.voAvailable.add(current_version)
        self.voAvailable.remove(newVersion)

    def swapPluginsAndMasterVersion(self, arcSaves, newSaves):
        """Save current plugins into arcSaves directory, load plugins from
        newSaves directory and set oblivion version."""
        arcPath, newPath = map(dirs[u'saveBase'].join, (arcSaves, newSaves))
        if load_order.swap(arcPath, newPath):
            self.refreshLoadOrder(unlock_lo=True)
        # Swap Oblivion version to memorized version
        voNew = saveInfos.get_profile_attr(newSaves, u'vOblivion', None)
        if voNew is None:
            saveInfos.set_profile_attr(newSaves, u'vOblivion', self.voCurrent)
            voNew = self.voCurrent
        if voNew in self.voAvailable: self.setOblivionVersion(voNew)

    def size_mismatch(self, plugin_name, plugin_size):
        """Checks if the specified plugin exists and, if so, if its size
        does not match the specified value (in bytes)."""
        return plugin_name in self and plugin_size != self[plugin_name].fsize

    def _recalc_real_indices(self):
        """Recalculates the real indices cache. See ModInfo.real_index for more
        info on these."""
        # Note that inactive plugins/ones with missing LO are handled by our
        # defaultdict factory
        regular_index = 0
        esl_index = 0
        esl_offset = load_order.max_espms() - 1
        self.real_indices.clear()
        self.real_index_strings.clear()
        for p in load_order.cached_active_tuple():
            if self[p].is_esl():
                # sort ESLs after all regular plugins
                self.real_indices[p] = esl_offset + esl_index
                self.real_index_strings[p] = f'FE {esl_index:03X}'
                esl_index += 1
            else:
                self.real_indices[p] = regular_index
                self.real_index_strings[p] = f'{regular_index:02X}'
                regular_index += 1

    def _recalc_dependents(self):
        """Recalculates the dependents cache. See ModInfo.get_dependents for
        more information."""
        cached_dependents = self.dependents
        cached_dependents.clear()
        for p, p_info in self.items():
            for p_master in p_info.masterNames:
                cached_dependents[p_master].add(p)

    def recurse_masters(self, fn_mod):
        """Recursively collect all masters of fn_mod."""
        ret_masters = set()
        src_masters = self[fn_mod].masterNames if fn_mod in self else []
        for src_master in src_masters:
            ret_masters.add(src_master)
            ret_masters.update(self.recurse_masters(src_master))
        return ret_masters

#------------------------------------------------------------------------------
class SaveInfos(FileInfos):
    """SaveInfo collection. Represents save directory and related info."""
    _bain_notify = False
    # Enabled and disabled saves, no .bak files ##: needed?
    file_pattern = re.compile('(%s)(f?)$' % '|'.join(r'\.%s' % s for s in
        [bush.game.Ess.ext[1:], bush.game.Ess.ext[1:-1] + 'r']), re.I | re.U)

    def _setLocalSaveFromIni(self):
        """Read the current save profile from the oblivion.ini file and set
        local save attribute to that value."""
        # saveInfos singleton is constructed in InitData after bosh.oblivionIni
        self.localSave = oblivionIni.getSetting(
            *bush.game.Ini.save_profiles_key,
            default=bush.game.Ini.save_prefix)
        if self.localSave.endswith(u'\\'): self.localSave = self.localSave[:-1]
        # Hopefully will solve issues with unicode usernames # TODO(ut) test
        self.localSave = decoder(self.localSave) # encoding = u'cp1252' ?

    def __init__(self):
        self.localSave = bush.game.Ini.save_prefix
        self._setLocalSaveFromIni()
        super(SaveInfos, self).__init__(dirs[u'saveBase'].join(self.localSave),
                                        factory=SaveInfo)
        # Save Profiles database
        self.profiles = bolt.PickleDict(
            dirs[u'saveBase'].join(u'BashProfiles.dat'), load_pickle=True)
        # save profiles used to have a trailing slash, remove it if present
        for row in [r for r in self.profiles.pickled_data if r.endswith('\\')]:
            self.rename_profile(row, row[:-1])
        SaveInfo.cosave_types = cosaves.get_cosave_types(
            bush.game.fsName, self._parse_save_path,
            bush.game.Se.cosave_tag, bush.game.Se.cosave_ext)

    def get_profile_attr(self, prof_key, attr_key, default_val):
        return self.profiles.pickled_data.get(prof_key, {}).get(attr_key,
                                                                default_val)

    def set_profile_attr(self, prof_key, attr_key, val):
        self.profiles.pickled_data.setdefault(prof_key, {})[attr_key] = val

    def rename_profile(self, oldName, newName):
        """Rename save profile - if newName is None just delete the row."""
        pd = self.profiles.pickled_data
        if oldName in pd:
            if newName is not None:
                pd[newName] = pd[oldName]
            del pd[oldName]

    @classmethod
    def rightFileType(cls, fileName: bolt.FName | str):
        return all(cls._parse_save_path(fileName))

    @classmethod
    def valid_save_exts(cls):
        """Returns a cached version of the valid extensions that a save may
        have."""
        try:
            return cls._valid_save_exts
        except AttributeError:
            std_save_ext = bush.game.Ess.ext[1:]
            accepted_exts = {std_save_ext, std_save_ext[:-1] + u'r', u'bak'}
            # Add 'first backup' versions of the extensions too
            for e in accepted_exts.copy():
                accepted_exts.add(e + u'f')
            cls._valid_save_exts = accepted_exts
            return accepted_exts

    @classmethod
    def _parse_save_path(cls, save_path: str) -> tuple[str | None,
                                                       str | None]:
        """Parses the specified save path into root and extension, returning
        them as a tuple. If the save path does not point to a valid save,
        returns two Nones instead."""
        accepted_exts = cls.valid_save_exts()
        save_root, save_ext = os.path.splitext(save_path)
        save_ext_trunc = save_ext[1:]
        if save_ext_trunc.lower() not in accepted_exts:
            # Can't be a valid save, doesn't end in ess/esr/bak
            return None, None
        cs_ext = bush.game.Se.cosave_ext[1:]
        if any(s.lower() == cs_ext for s in save_root.split(u'.')):
            # Almost certainly not a valid save, had the cosave extension
            # in one of its root parts
            return None, None
        return save_root, save_ext

    @property
    def bash_dir(self): return self.store_dir.join(u'Bash')

    def refresh(self, refresh_infos=True, booting=False):
        if not booting: self._refreshLocalSave() # otherwise we just did this
        return refresh_infos and FileInfos.refresh(self, booting=booting)

    def rename_operation(self, member_info, newName):
        """Renames member file from oldName to newName, update also cosave
        instance names."""
        old_key = super(SaveInfos, self).rename_operation(member_info, newName)
        for co_type, co_file in self[newName]._co_saves.items():
            co_file.abs_path = co_type.get_cosave_path(self[newName].abs_path)
        return old_key

    def _additional_deletes(self, fileInfo, toDelete):
        # type: (SaveInfo, list) -> None
        toDelete.extend(
            x.abs_path for x in fileInfo._co_saves.values())
        # now add backups and cosaves backups
        super(SaveInfos, self)._additional_deletes(fileInfo, toDelete)

    def copy_info(self, fileName, destDir, destName=empty_path, set_mtime=None,
                  save_lo_cache=False):
        """Copies savefile and associated cosaves file(s)."""
        super(SaveInfos, self).copy_info(fileName, destDir, destName, set_mtime)
        self._co_copy_or_move(self[fileName].abs_path,
            destDir.join(destName or fileName))

    def _co_copy_or_move(self, src_path: Path, dest_path: Path,
            move_cosave=False):
        try:
            co_instances = self[src_path.stail]._co_saves
        except KeyError: # src_path is outside self.store_dir
            co_instances = SaveInfo.get_cosaves_for_path(src_path)
        for co_type, co_file in co_instances.items():
            newPath = co_type.get_cosave_path(dest_path)
            if newPath.exists(): newPath.remove() ##: dont like it, investigate
            co_apath = co_file.abs_path
            if co_apath.exists():
                path_func = co_apath.moveTo if move_cosave else co_apath.copyTo
                path_func(newPath)

    def move_infos(self, sources, destinations, window, bash_frame):
        # operations should be atomic - we should construct a list of filenames
        # to unhide and pass that in
        moved = super(SaveInfos, self).move_infos(sources, destinations,
                                                  window, bash_frame)
        for s, d in zip(sources, destinations):
            if FName(d.stail) in moved:
                self._co_copy_or_move(s, d, move_cosave=True)
                break
        for m in moved:
            try:
                self.new_info(m, notify_bain=True)
            except FileError:
                pass # will warn below
        bash_frame.warn_corrupted(warn_saves=True)
        return moved

    def move_info(self, fileName, destDir):
        """Moves member file to destDir. Will overwrite!"""
        FileInfos.move_info(self, fileName, destDir)
        self._co_copy_or_move(self[fileName].abs_path, destDir.join(fileName),
            move_cosave=True)

    #--Local Saves ------------------------------------------------------------
    def _refreshLocalSave(self):
        """Refreshes self.localSave."""
        #--self.localSave is NOT a Path object.
        localSave = self.localSave
        self._setLocalSaveFromIni()
        if localSave == self.localSave: return # no change
        self.table.save()
        self._initDB(dirs[u'saveBase'].join(self.localSave))

    def setLocalSave(self, localSave: str, refreshSaveInfos=True):
        """Sets SLocalSavePath in Oblivion.ini. The latter must exist."""
        self.table.save()
        self.localSave = localSave
        ##: not sure if appending the slash is needed for the game to parse
        # the setting correctly, kept previous behavior
        oblivionIni.saveSetting(*bush.game.Ini.save_profiles_key,
                                value=localSave + u'\\')
        self._initDB(dirs[u'saveBase'].join(self.localSave))
        if refreshSaveInfos: self.refresh()

#------------------------------------------------------------------------------
class BSAInfos(FileInfos):
    """BSAInfo collection. Represents bsa files in game's Data directory."""
    # BSAs that have versions other than the one expected for the current game
    mismatched_versions = set()
    # Maps BA2 hashes to BA2 names, used to detect collisions
    _ba2_hashes = collections.defaultdict(set)
    ba2_collisions = set()

    def __init__(self):
        if bush.game.displayName == u'Oblivion':
            # Need to do this at runtime since it depends on inisettings (ugh)
            bush.game.Bsa.redate_dict[inisettings[
                u'OblivionTexturesBSAName']] = 1104530400 # '2005-01-01'
        self.__class__.file_pattern = re.compile(
            re.escape(bush.game.Bsa.bsa_extension) + u'$', re.I | re.U)
        _bsa_type = bsa_files.get_bsa_type(bush.game.fsName)

        class BSAInfo(FileInfo, _bsa_type):
            _valid_exts_re = fr'(\.{bush.game.Bsa.bsa_extension[1:]})'
            def __init__(self, fullpath, load_cache=False, itsa_ghost=None):
                try:  # Never load_cache for memory reasons - let it be
                    # loaded as needed
                    super(BSAInfo, self).__init__(fullpath, load_cache=False)
                except BSAError as e:
                    raise FileError(GPath(fullpath).tail,
                        f'{e.__class__.__name__}  {e.message}') from e
                self._reset_bsa_mtime()

            @classmethod
            def get_store(cls): return bsaInfos

            def do_update(self, raise_on_error=False, itsa_ghost=None):
                did_change = super(BSAInfo, self).do_update(raise_on_error)
                self._reset_bsa_mtime()
                return did_change

            def readHeader(self):  # just reset the cache
                self._assets = self.__class__._assets

            def _reset_bsa_mtime(self):
                if bush.game.Bsa.allow_reset_timestamps and inisettings[
                    u'ResetBSATimestamps']:
                    default_mtime = bush.game.Bsa.redate_dict[self.fn_key]
                    if self.file_mod_time != default_mtime:
                        self.setmtime(default_mtime)

        super(BSAInfos, self).__init__(dirs[u'mods'], factory=BSAInfo)

    def new_info(self, fileName, _in_refresh=False, owner=None,
                 notify_bain=False, itsa_ghost=None):
        new_bsa = super(BSAInfos, self).new_info(fileName, _in_refresh, owner,
                                                 notify_bain, itsa_ghost)
        new_bsa_name = new_bsa.fn_key
        # Check if the BSA has a mismatched version - if so, schedule a warning
        if bush.game.Bsa.valid_versions: # If empty, skip checks for this game
            if new_bsa.inspect_version() not in bush.game.Bsa.valid_versions:
                self.mismatched_versions.add(new_bsa_name)
        # For BA2s, check for hash collisions
        if new_bsa_name.fn_ext == u'.ba2':
            ba2_entry = self._ba2_hashes[new_bsa.ba2_hash()]
            # Drop the previous collision if it's present, then check if we
            # have a new one
            self.ba2_collisions.discard(u' & '.join(sorted(ba2_entry)))
            ba2_entry.add(new_bsa_name)
            if len(ba2_entry) >= 2:
                self.ba2_collisions.add(u' & '.join(sorted(ba2_entry)))
        return new_bsa

    @property
    def bash_dir(self): return dirs[u'modsBash'].join(u'BSA Data')

    @staticmethod
    def remove_invalidation_file():
        """Removes ArchiveInvalidation.txt, if it exists in the game folder.
        This is used when disabling other solutions to the Archive Invalidation
        problem prior to enabling WB's BSA Redirection."""
        dirs[u'app'].join(u'ArchiveInvalidation.txt').remove()

#------------------------------------------------------------------------------
class ScreenInfos(FileInfos):
    """Collection of screenshot. This is the backend of the Screens tab."""
    _bain_notify = False # BAIN can't install to game dir
    # Files that go in the main game folder (aka default screenshots folder)
    # and have screenshot extensions, but aren't screenshots and therefore
    # shouldn't be managed here - right now only ENB stuff
    _ss_skips = {FName(s) for s in (
        'enblensmask.png', 'enbpalette.bmp', 'enbsunsprite.bmp',
        'enbsunsprite.tga', 'enbunderwaternoise.bmp')}

    def __init__(self):
        self._orig_store_dir = dirs[u'app'] # type: bolt.Path
        self.__class__.file_pattern = re.compile(
            r'\.(' + '|'.join(ext[1:] for ext in ss_image_exts) + ')$',
            re.I | re.U)
        super(ScreenInfos, self).__init__(self._orig_store_dir,
                                          factory=ScreenInfo)

    def rightFileType(cls, fileName: bolt.FName | str):
        if fileName in cls._ss_skips:
            # Some non-screenshot file, skip it
            return False
        return super().rightFileType(fileName)

    def refresh(self, refresh_infos=True, booting=False):
        # Check if we need to adjust the screenshot dir
        ss_base = GPath(oblivionIni.getSetting(
            u'Display', u'SScreenShotBaseName', u'ScreenShot'))
        new_store_dir = self._orig_store_dir.join(ss_base.head)
        if self.store_dir != new_store_dir:
            self.store_dir = new_store_dir
        return super(ScreenInfos, self).refresh(refresh_infos, booting)

    @property
    def bash_dir(self): return dirs[u'modsBash'].join(u'Screenshot Data')

#------------------------------------------------------------------------------
# Hack below needed as older Converters.dat expect bosh.InstallerConverter
# See InstallerConverter.__reduce__()
# noinspection PyRedeclaration
class InstallerConverter(InstallerConverter): pass

##: This hides a circular dependency (__init__ -> bain -> __init__)
from .bain import Installer, InstallerArchive, InstallerMarker, \
    InstallerProject, InstallersData

# Same hack for Installers.dat...
# noinspection PyRedeclaration
class InstallerArchive(InstallerArchive): pass
# noinspection PyRedeclaration
class InstallerMarker(InstallerMarker): pass
# noinspection PyRedeclaration
class InstallerProject(InstallerProject): pass

# Initialization --------------------------------------------------------------
def initTooldirs():
    #-- Other tool directories
    #   First to default path
    pf = [GPath(u'C:\\Program Files'),GPath(u'C:\\Program Files (x86)')]
    def pathlist(*args): return [x.join(*args) for x in pf]
    def multi_path(*paths):
        return list(chain.from_iterable(pathlist(*p) for p in paths))
    tooldirs = bass.tooldirs = bolt.LowerDict() ##: Yak! needed for case insensitive keys
    def _get_boss_loot(registry_key, game_folder, exe_name):
        """Helper for determing correct BOSS/LOOT path."""
        # Check game folder for a copy first
        if dirs['app'].join(game_folder, exe_name).is_file():
            ret_path = dirs['app'].join(game_folder, exe_name)
        else:
            ret_path = GPath('C:\\**DNE**')
            # Detect globally installed program (into Program Files)
            path_in_registry = env.get_registry_path(*registry_key,
                lambda p: p.join(exe_name).is_file())
            if path_in_registry:
                ret_path = path_in_registry.join(exe_name)
        return ret_path
    tooldirs['boss'] = _get_boss_loot(
        ('Boss', 'Installed Path'), 'BOSS', 'BOSS.exe')
    tooldirs['LOOT'] = _get_boss_loot(
        ('LOOT', 'Installed Path'), 'LOOT', 'LOOT.exe')
    tooldirs[u'TES3EditPath'] = dirs[u'app'].join(u'TES3Edit.exe')
    tooldirs[u'Tes4FilesPath'] = dirs[u'app'].join(u'Tools', u'TES4Files.exe')
    tooldirs[u'Tes4EditPath'] = dirs[u'app'].join(u'TES4Edit.exe')
    tooldirs[u'Tes5EditPath'] = dirs[u'app'].join(u'TES5Edit.exe')
    tooldirs[u'TES5VREditPath'] = dirs[u'app'].join(u'TES5VREdit.exe')
    tooldirs[u'EnderalEditPath'] = dirs[u'app'].join(u'EnderalEdit.exe')
    tooldirs[u'SSEEditPath'] = dirs[u'app'].join(u'SSEEdit.exe')
    tooldirs[u'Fo4EditPath'] = dirs[u'app'].join(u'FO4Edit.exe')
    tooldirs[u'Fo3EditPath'] = dirs[u'app'].join(u'FO3Edit.exe')
    tooldirs[u'FnvEditPath'] = dirs[u'app'].join(u'FNVEdit.exe')
    tooldirs[u'FO4VREditPath'] = dirs[u'app'].join(u'FO4VREdit.exe')
    tooldirs[u'Tes4LodGenPath'] = dirs[u'app'].join(u'TES4LodGen.exe')
    tooldirs[u'Tes4GeckoPath'] = dirs[u'app'].join(u'Tes4Gecko.jar')
    tooldirs[u'Tes5GeckoPath'] = pathlist(u'Dark Creations',u'TESVGecko',u'TESVGecko.exe')
    tooldirs[u'OblivionBookCreatorPath'] = dirs[u'mods'].join(u'OblivionBookCreator.jar')
    tooldirs[u'NifskopePath'] = pathlist(u'NifTools',u'NifSkope',u'Nifskope.exe')
    tooldirs[u'BlenderPath'] = pathlist(u'Blender Foundation',u'Blender',u'blender.exe')
    tooldirs[u'GmaxPath'] = GPath(u'C:\\GMAX').join(u'gmax.exe')
    tooldirs[u'MaxPath'] = pathlist(u'Autodesk',u'3ds Max 2010',u'3dsmax.exe')
    tooldirs[u'MayaPath'] = undefinedPath
    tooldirs['PhotoshopPath'] = multi_path( ##: CC path
        ['Adobe', 'Adobe Photoshop CS6 (64 Bit)', 'Photoshop.exe'],
        ['Adobe', 'Adobe Photoshop CS3', 'Photoshop.exe'])
    tooldirs[u'GIMP'] = pathlist(u'GIMP-2.0',u'bin',u'gimp-2.6.exe')
    tooldirs[u'ISOBL'] = dirs[u'app'].join(u'ISOBL.exe')
    tooldirs[u'ISRMG'] = dirs[u'app'].join(u'Insanitys ReadMe Generator.exe')
    tooldirs[u'ISRNG'] = dirs[u'app'].join(u'Random Name Generator.exe')
    tooldirs[u'ISRNPCG'] = dirs[u'app'].join(u'Random NPC.exe')
    tooldirs[u'NPP'] = pathlist(u'Notepad++',u'notepad++.exe')
    tooldirs[u'Fraps'] = GPath(u'C:\\Fraps').join(u'Fraps.exe')
    tooldirs[u'Audacity'] = pathlist(u'Audacity',u'Audacity.exe')
    tooldirs[u'Artweaver'] = pathlist(u'Artweaver 1.0',u'Artweaver.exe')
    tooldirs[u'DDSConverter'] = pathlist(u'DDS Converter 2',u'DDS Converter 2.exe')
    tooldirs[u'PaintNET'] = pathlist(u'Paint.NET',u'PaintDotNet.exe')
    tooldirs[u'Milkshape3D'] = pathlist(u'MilkShape 3D 1.8.4',u'ms3d.exe')
    tooldirs[u'Wings3D'] = pathlist(u'wings3d_1.2',u'Wings3D.exe')
    tooldirs[u'BSACMD'] = pathlist(u'BSACommander',u'bsacmd.exe')
    tooldirs[u'MAP'] = dirs[u'app'].join(u'Modding Tools', u'Interactive Map of Cyrodiil and Shivering Isles 3.52', u'Mapa v 3.52.exe')
    tooldirs[u'OBMLG'] = dirs[u'app'].join(u'Modding Tools', u'Oblivion Mod List Generator', u'Oblivion Mod List Generator.exe')
    tooldirs[u'OBFEL'] = pathlist(u'Oblivion Face Exchange Lite',u'OblivionFaceExchangeLite.exe')
    tooldirs[u'ArtOfIllusion'] = pathlist(u'ArtOfIllusion',u'Art of Illusion.exe')
    tooldirs[u'ABCAmberAudioConverter'] = pathlist(u'ABC Amber Audio Converter',u'abcaudio.exe')
    tooldirs[u'Krita'] = pathlist(u'Krita (x86)',u'bin',u'krita.exe')
    tooldirs[u'PixelStudio'] = pathlist(u'Pixel',u'Pixel.exe')
    tooldirs[u'TwistedBrush'] = pathlist(u'Pixarra',u'TwistedBrush Open Studio',u'tbrush_open_studio.exe')
    tooldirs[u'PhotoScape'] = pathlist(u'PhotoScape',u'PhotoScape.exe')
    tooldirs[u'Photobie'] = pathlist(u'Photobie',u'Photobie.exe')
    tooldirs[u'PhotoFiltre'] = pathlist(u'PhotoFiltre',u'PhotoFiltre.exe')
    tooldirs[u'PaintShopPhotoPro'] = pathlist(u'Corel',u'Corel PaintShop Photo Pro',u'X3',u'PSPClassic',u'Corel Paint Shop Pro Photo.exe')
    tooldirs[u'Dogwaffle'] = pathlist(u'project dogwaffle',u'dogwaffle.exe')
    tooldirs[u'GeneticaViewer'] = pathlist(u'Spiral Graphics',u'Genetica Viewer 3',u'Genetica Viewer 3.exe')
    tooldirs[u'LogitechKeyboard'] = pathlist(u'Logitech',u'GamePanel Software',u'G-series Software',u'LGDCore.exe')
    tooldirs[u'AutoCad'] = pathlist(u'Autodesk Architectural Desktop 3',u'acad.exe')
    tooldirs[u'Genetica'] = pathlist(u'Spiral Graphics',u'Genetica 3.5',u'Genetica.exe')
    tooldirs[u'IrfanView'] = pathlist(u'IrfanView',u'i_view32.exe')
    tooldirs[u'XnView'] = pathlist(u'XnView',u'xnview.exe')
    tooldirs[u'FastStone'] = pathlist(u'FastStone Image Viewer',u'FSViewer.exe')
    tooldirs[u'Steam'] = pathlist(u'Steam',u'steam.exe')
    tooldirs[u'EVGAPrecision'] = pathlist(u'EVGA Precision',u'EVGAPrecision.exe')
    tooldirs[u'IcoFX'] = pathlist(u'IcoFX 1.6',u'IcoFX.exe')
    tooldirs[u'AniFX'] = pathlist(u'AniFX 1.0',u'AniFX.exe')
    tooldirs[u'WinMerge'] = pathlist(u'WinMerge',u'WinMergeU.exe')
    tooldirs[u'FreeMind'] = pathlist(u'FreeMind',u'Freemind.exe')
    tooldirs[u'MediaMonkey'] = pathlist(u'MediaMonkey',u'MediaMonkey.exe')
    tooldirs['Inkscape'] = multi_path(['Inkscape', 'bin', 'inkscape.exe'],
                                      ['Inkscape', 'inkscape.exe']) # older ver
    tooldirs[u'FileZilla'] = pathlist(u'FileZilla FTP Client',u'filezilla.exe')
    tooldirs[u'RADVideo'] = pathlist(u'RADVideo',u'radvideo.exe')
    tooldirs[u'EggTranslator'] = pathlist(u'Egg Translator',u'EggTranslator.exe')
    tooldirs[u'Sculptris'] = pathlist(u'sculptris',u'Sculptris.exe')
    tooldirs[u'Mudbox'] = pathlist(u'Autodesk',u'Mudbox2011',u'mudbox.exe')
    tooldirs[u'Tabula'] = dirs[u'app'].join(u'Modding Tools', u'Tabula', u'Tabula.exe')
    tooldirs[u'MyPaint'] = pathlist(u'MyPaint',u'mypaint.exe')
    tooldirs[u'Pixia'] = pathlist(u'Pixia',u'pixia.exe')
    tooldirs[u'DeepPaint'] = pathlist(u'Right Hemisphere',u'Deep Paint',u'DeepPaint.exe')
    tooldirs[u'CrazyBump'] = pathlist(u'Crazybump',u'CrazyBump.exe')
    tooldirs[u'xNormal'] = pathlist(u'Santiago Orgaz',u'xNormal',u'3.17.3',u'x86',u'xNormal.exe')
    tooldirs[u'SoftimageModTool'] = GPath(u'C:\\Softimage').join(u'Softimage_Mod_Tool_7.5',u'Application',u'bin',u'XSI.bat')
    tooldirs[u'SpeedTree'] = undefinedPath
    tooldirs[u'Treed'] = pathlist(u'gile[s]',u'plugins',u'tree[d]',u'tree[d].exe')
    tooldirs[u'WinSnap'] = pathlist(u'WinSnap',u'WinSnap.exe')
    tooldirs[u'PhotoSEAM'] = pathlist(u'PhotoSEAM',u'PhotoSEAM.exe')
    tooldirs[u'TextureMaker'] = pathlist(u'Texture Maker',u'texturemaker.exe')
    tooldirs[u'MaPZone'] = pathlist(u'Allegorithmic',u'MaPZone 2.6',u'MaPZone2.exe')
    tooldirs[u'NVIDIAMelody'] = pathlist(u'NVIDIA Corporation',u'Melody',u'Melody.exe')
    tooldirs[u'WTV'] = pathlist(u'WindowsTextureViewer',u'WTV.exe')
    tooldirs[u'Switch'] = pathlist(u'NCH Swift Sound',u'Switch',u'switch.exe')
    tooldirs[u'Freeplane'] = pathlist(u'Freeplane',u'freeplane.exe')

def initDefaultSettings():
    # *some* settings from the INI - note we get some ini settings (such as
    # sOblivionMods) via get_ini_option/get_path_from_ini we never store those
    # in bass.inisettings
    inisettings[u'ScriptFileExt'] = u'.txt'
    inisettings[u'ResetBSATimestamps'] = True
    inisettings[u'EnsurePatchExists'] = True
    inisettings[u'OblivionTexturesBSAName'] = u'Oblivion - Textures - Compressed.bsa'
    inisettings[u'ShowDevTools'] = False
    inisettings[u'Tes4GeckoJavaArg'] = u'-Xmx1024m'
    inisettings[u'OblivionBookCreatorJavaArg'] = u'-Xmx1024m'
    inisettings[u'ShowTextureToolLaunchers'] = True
    inisettings[u'ShowModelingToolLaunchers'] = True
    inisettings[u'ShowAudioToolLaunchers'] = True
    inisettings[u'7zExtraCompressionArguments'] = u''
    inisettings[u'xEditCommandLineArguments'] = u''
    inisettings[u'AutoItemCheck'] = True
    inisettings[u'SkipHideConfirmation'] = False
    inisettings[u'SkipResetTimeNotifications'] = False
    inisettings[u'SoundSuccess'] = u''
    inisettings[u'SoundError'] = u''
    inisettings[u'EnableSplashScreen'] = True
    inisettings[u'PromptActivateBashedPatch'] = True
    inisettings[u'WarnTooManyFiles'] = True
    inisettings[u'SkippedBashInstallersDirs'] = u''
    inisettings[u'Command7z'] = '7z'

__type_key_preffix = {  # Path is tooldirs only int does not appear in either!
    bolt.Path: u's', str: u's', list: u's', int: u'i', bool: u'b'}
def initOptions(bashIni):
    initTooldirs()
    initDefaultSettings()
    # if bash.ini exists update the settings from there
    if bashIni:
        defaultOptions = {}
        for settingsDict in [bass.tooldirs, inisettings]:
            for defaultKey, defaultValue in settingsDict.items():
                valueType = type(defaultValue)
                readKey = __type_key_preffix[valueType] + defaultKey
                defaultOptions[readKey.lower()] = (defaultKey, settingsDict, valueType)
        unknownSettings = {} ##: print those
        for section in bashIni.sections():
            # retrieving ini settings is case insensitive - key: lowecase
            for key, value in bashIni.items(section):
                usedKey, usedSettings, settingType = defaultOptions.get(
                    key, (key[1:], unknownSettings, str))
                compDefaultValue = usedSettings.get(usedKey, u'')
                if settingType in (bolt.Path,list):
                    if value == u'.': continue
                    value = GPath(value)
                    if not value.is_absolute():
                        value = dirs[u'app'].join(value)
                elif settingType is bool:
                    if value == u'.': continue
                    value = bashIni.getboolean(section,key)
                else:
                    value = settingType(value)
                comp_val = value
                if settingType is str:
                    compDefaultValue = compDefaultValue.lower()
                    comp_val = comp_val.lower()
                elif settingType is list:
                    compDefaultValue = compDefaultValue[0]
                if comp_val != compDefaultValue:
                    usedSettings[usedKey] = value
    if os_name != 'nt':
        archives.exe7z = inisettings[u'Command7z']
    bass.tooldirs[u'Tes4ViewPath'] = bass.tooldirs[u'Tes4EditPath'].head.join(u'TES4View.exe')
    bass.tooldirs[u'Tes4TransPath'] = bass.tooldirs[u'Tes4EditPath'].head.join(u'TES4Trans.exe')

def initBosh(bashIni, game_ini_path):
    # Setup loot_parser, needs to be done after the dirs are initialized
    if not initialization.bash_dirs_initialized:
        raise BoltError(u'initBosh: Bash dirs are not initialized')
    # game ini files
    deprint(f'Looking for main game INI at {game_ini_path}')
    global oblivionIni, gameInis
    oblivionIni = GameIni(game_ini_path, 'cp1252')
    gameInis = [oblivionIni]
    gameInis.extend(IniFile(dirs[u'saveBase'].join(x), 'cp1252') for x in
                    bush.game.Ini.dropdown_inis[1:])
    load_order.initialize_load_order_files()
    initOptions(bashIni)
    Installer.init_bain_dirs()

def initSettings(ask_yes, readOnly=False, _dat='BashSettings.dat',
                 _bak='BashSettings.dat.bak'):
    """Init user settings from files and load the defaults (also in basher)."""
    def _load(dat_file=_dat):
    # bolt.PickleDict.load() handles EOFError, ValueError falling back to bak
        return bolt.Settings( # calls PickleDict.load() and copies loaded data
            bolt.PickleDict(dirs[u'saveBase'].join(dat_file), readOnly))
    _dat = dirs[u'saveBase'].join(_dat)
    _bak = dirs[u'saveBase'].join(_bak)
    def _loadBakOrEmpty(delBackup=False, ignoreBackup=False):
        _dat.remove()
        if delBackup: _bak.remove()
        # bolt machinery will automatically load the backup - bypass it if
        # user did, by temporarily renaming the .bak file
        if ignoreBackup: _bak.moveTo(f'{_bak}.ignore')
        # load the .bak file, or an empty settings dict saved to disc at exit
        loaded = _load()
        if ignoreBackup: GPath(f'{_bak}.ignore').moveTo(_bak)
        return loaded
    #--Set bass.settings ------------------------------------------------------
    try:
        bass.settings = _load()
    except pickle.UnpicklingError as err:
        msg = _(
            "Error reading the Wrye Bash Settings database (the error is "
            "'%(settings_err)s'). This is probably not recoverable with the "
            "current file. Do you want to try the backup "
            "%(settings_file_name)s (it will have all your settings from the "
            "second to last time that you used Wrye Bash)?") % {
            'settings_err': repr(err),
            'settings_file_name': 'BashSettings.dat'}
        usebck = ask_yes(None, msg, _('Settings Load Error'))
        if usebck:
            try:
                bass.settings = _loadBakOrEmpty()
            except pickle.UnpicklingError as err:
                msg = _(
                    "Error reading the backup Wrye Bash Settings database "
                    "(the error is '%(settings_err)s'). This is probably not "
                    "recoverable with the current file. Do you want to delete "
                    "the corrupted settings and load Wrye Bash without your "
                    "saved settings (choosing 'No' will cause Wrye Bash to "
                    "exit)?") % {'settings_err': repr(err)}
                delete = ask_yes(None, msg, _('Settings Load Error'))
                if delete:
                    bass.settings = _loadBakOrEmpty(delBackup=True)
                else:
                    raise
        else:
            msg = _(
                "Do you want to delete the corrupted settings and load Wrye "
                "Bash without your saved settings (choosing 'No' will cause "
                "Wrye Bash to exit)?")
            delete = ask_yes(None, msg, _('Settings Load Error'))
            if delete: # Ignore bak but don't delete, overwrite on exit instead
                bass.settings = _loadBakOrEmpty(ignoreBackup=True)
            else:
                raise
