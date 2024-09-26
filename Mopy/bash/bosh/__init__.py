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
"""The data model, complete with initialization functions. Main hierarchies
are the DataStore singletons and bolt.AFile subclasses populating the data
stores. bush.game must be set, to properly instantiate the data stores."""
from __future__ import annotations

import io
import os
import pickle
import re
import sys
import time
from collections import defaultdict, deque, OrderedDict
from collections.abc import Iterable, Callable
from dataclasses import dataclass, field
from functools import wraps
from itertools import chain
from typing import final

# bosh-local imports - maybe work towards dropping (some of) these?
from . import bsa_files, converters, cosaves
from ._mergeability import isPBashMergeable
from .converters import InstallerConverter
from .cosaves import PluggyCosave, xSECosave
from .mods_metadata import get_tags_from_dir, process_tags, read_dir_tags, \
    read_loot_tags
from .save_headers import get_save_header_type
from .. import archives, bass, bolt, bush, env, initialization, load_order
from ..bass import dirs, inisettings, Store
from ..bolt import AFile, AFileInfo, DataDict, FName, FNDict, GPath, \
    ListInfo, Path, deprint, dict_sort, forward_compat_path_to_fn, \
    forward_compat_path_to_fn_list, os_name, struct_error, top_level_files, \
    OrderedLowerDict, attrgetter_cache
from ..brec import FormIdReadContext, FormIdWriteContext, RecordHeader, \
    RemapWriteContext
from ..exception import ArgumentError, BoltError, BSAError, CancelError, \
    FailedIniInferError, FileError, ModError, PluginsFullError, SaveFileError, \
    SaveHeaderError, SkipError, SkippedMergeablePluginsError
from ..game import MergeabilityCheck, PluginFlag, MasterFlag
from ..ini_files import AIniInfo, GameIni, IniFileInfo, OBSEIniFile, \
    get_ini_type_and_encoding, supported_ini_exts
from ..load_order import LordDiff
from ..mod_files import ModFile, ModHeaderReader
from ..wbtemp import TempFile

# Singletons, Constants -------------------------------------------------------
empty_path = GPath(u'') # evaluates to False in boolean expressions
_ListInf = AFile | ListInfo | None| FName

#--Singletons
gameInis: tuple[GameIni | IniFileInfo] | None = None
oblivionIni: GameIni | None = None
modInfos: ModInfos | None = None
saveInfos: SaveInfos | None = None
iniInfos: INIInfos | None = None
bsaInfos: BSAInfos | None = None
screen_infos: ScreenInfos | None = None

def data_tracking_stores() -> Iterable['_AFileInfos']:
    """Return an iterable containing all data stores that keep track of the
    Data folder and so will get refresh calls from BAIN when files get
    installed/changed/uninstalled. If they set _AFileInfos.tracks_ownership to
    True, they will also get ownership updates."""
    return tuple(s for s in (modInfos, iniInfos, bsaInfos, screen_infos) if
                 s is not None)

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
bain_image_exts = {*_common_image_exts, '.webp'}
ss_image_exts = {*_common_image_exts, '.tga'}

#--Typing
_CosaveDict = dict[type[cosaves.ACosave], cosaves.ACosave]

#------------------------------------------------------------------------------
# File System -----------------------------------------------------------------
#------------------------------------------------------------------------------
def _mod_info_delegate(fn):
    """Decorator for MasterInfo methods that delegate to self.mod_info methods
    if the latter is not None."""
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        if self.mod_info is not None:
            return getattr(self.mod_info, fn.__name__)(*args, **kwargs)
        return fn(self, *args, **kwargs)
    return wrapper

class MasterInfo:
    """Slight abstraction over ModInfo that allows us to represent masters that
    are missing an active mod counterpart."""
    __slots__ = ('is_ghost', 'curr_name', 'mod_info', 'old_name',
                 'stored_size', '_was_esl', 'parent_mod_info')

    def __init__(self, *, parent_minf, master_name: FName, master_size,
                 was_esl):
        self.parent_mod_info = parent_minf
        self.stored_size = master_size
        self._was_esl = was_esl
        self.old_name = master_name
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
            self.is_ghost = mod_info.is_ghost
        return mod_info

    def disable_master(self):
        esp_name = f'XX{self.curr_name.fn_body}.esp'
        self.curr_name = ModInfo.unique_name(esp_name)
        self.is_ghost = False
        self.mod_info = None

    @_mod_info_delegate
    def has_esm_flag(self):
        return MasterFlag.ESM in bush.game.scale_flags.guess_flags(
            self.get_extension())

    @_mod_info_delegate
    def in_master_block(self):
        return self.has_esm_flag()

    @_mod_info_delegate
    def is_esl(self):
        """Delegate to self.modInfo.is_esl if exists, else rely on _was_esl."""
        return self._was_esl

    @_mod_info_delegate
    def is_overlay(self):
        """Delegate to self.modInfo.is_overlay if exists."""
        return False

    def has_master_size_mismatch(self, do_test): # used in set_item_format
        return _('Stored size does not match the one on disk.') if do_test \
          and modInfos.size_mismatch(self.curr_name, self.stored_size) else ''

    @_mod_info_delegate
    def getDirtyMessage(self, scan_beth=False):
        """Returns a dirty message from LOOT."""
        return ''

    @_mod_info_delegate
    def hasTimeConflict(self):
        """True if it has a mtime conflict with another mod."""
        return False

    @_mod_info_delegate
    def hasActiveTimeConflict(self):
        """True if it has an active mtime conflict with another mod."""
        return False

    @_mod_info_delegate
    def getBashTags(self):
        """Retrieve bash tags for master info if it's present in Data."""
        return set()

    def getStatus(self):
        return 30 if not self.mod_info else 0

    def __repr__(self):
        return f'{self.__class__.__name__}<{self.curr_name!r}>'

#------------------------------------------------------------------------------
class _TabledInfo:
    """Stores some of its attributes in a pickled dict. Most of the (hacky)
    internals are for translating the legacy dict keys to proper attr names."""
    _key_to_attr = {}
    _ignore_on_revert = frozenset()

    def __init__(self, *args, att_val=None, **kwargs):
        for k, v in (att_val or {}).items(): # set table props used in refresh
            try: ##: nightly regression storing 'installer' as FName - drop!
                if k == 'installer': v = str(v)
                elif k == 'doc': v = GPath(v) # needed for updates from old settings
                self.set_table_prop(k, v)
            except KeyError:  # 'mtime' - we don't need another mtime cache
                self.fn_key = FName(GPath(args[0]).stail) # for repr below
                deprint(f'Failed to set {k=} to {v=} for {self=}')
        super().__init__(*args, **kwargs)

    def get_table_prop(self, prop_key, default=None):
        """Get Info attribute for given prop_key."""
        return getattr(self, self.__class__._key_to_attr[prop_key], default)

    def set_table_prop(self, prop_key, val):
        if val is None:
            try:
                delattr(self, self.__class__._key_to_attr[prop_key])
            except AttributeError: return
        else: setattr(self, self.__class__._key_to_attr[prop_key], val)

    def get_persistent_attrs(self):
        return {pickle_key: val for pickle_key in self.__class__._key_to_attr
                if (val := self.get_table_prop(pickle_key)) is not None}

    def copy_persistent_attrs(self, other, exclude=None):
        if exclude is None:
            exclude = self.__class__._ignore_on_revert
        for pickle_key, val in other.get_persistent_attrs().items():
            if pickle_key not in exclude:
                self.set_table_prop(pickle_key, val)

class FileInfo(_TabledInfo, AFileInfo):
    """Abstract Mod, Save or BSA File. Features a half baked Backup API."""
    _null_stat = (-1, None, None)

    def _stat_tuple(self): return self.abs_path.size_mtime_ctime()

    def __init__(self, fullpath, load_cache=False, **kwargs):
        self.header = None
        self.masterNames: tuple[FName, ...] = ()
        self.madeBackup = False
        # True if the masters for this file are not reliable
        self.has_inaccurate_masters = False
        #--Ancillary storage
        self.extras = {}
        super().__init__(fullpath, load_cache, **kwargs)

    def _reset_masters(self):
        #--Master Names/Order
        self.masterNames = tuple(self._get_masters())

    def _file_changed(self, stat_tuple):
        return (self.fsize, self.ftime, self.ctime) != stat_tuple

    def _reset_cache(self, stat_tuple, **kwargs):
        self.fsize, self.ftime, self.ctime = stat_tuple
        if kwargs['load_cache']: self.readHeader()

    def setmtime(self, set_time: int | float = 0.0, crc_changed=False):
        """Sets ftime. Defaults to current value (i.e. reset)."""
        set_to = set_time or self.ftime
        self.abs_path.mtime = set_to
        self.ftime = set_to
        return set_to

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

    def has_circular_masters(self, *, fake_masters: list[FName] | None = None):
        """Check if this file has circular masters, i.e. if it depends on
        itself (either directly or transitively). If it doesn't have masters,
        raise a NotImplementedError.

        :param fake_masters: If not None, use this instead of self.masterNames
            for determining which masters to recurse into. Useful for checking
            if altering a master list would cause it to become circular."""
        raise NotImplementedError

    # Backup stuff - beta, see #292 -------------------------------------------
    def get_hide_dir(self):
        return self._store().hidden_dir

    def makeBackup(self, forceBackup=False):
        """Creates backup(s) of file."""
        #--Skip backup?
        if self not in self._store().values(): return
        if self.madeBackup and not forceBackup: return
        #--Backup
        self.fs_copy(self.backup_dir.join(self.fn_key))
        #--First backup
        firstBackup = self.backup_dir.join(self.fn_key) + 'f'
        if not firstBackup.exists():
            self.fs_copy(self.backup_dir.join(firstBackup.tail))
        self.madeBackup = True

    def backup_restore_paths(self, first, fname=None) -> list[tuple[Path, Path]]:
        """Return a list of tuples, mapping backup paths to their restore
        destinations. If fname is not given returns the (first) backup
        filename corresponding to self.abs_path, else the backup filename
        for fname mapped to its restore location in data_store.store_dir."""
        restore_path = (fname and self._store().store_dir.join(
            fname)) or self.abs_path
        fname = fname or self.fn_key
        return [(self.backup_dir.join(fname + 'f' * first), restore_path)]

    def all_backup_paths(self, fname=None):
        """Return the list of all possible paths a backup operation may create.
        __path does not really matter and is not necessarily correct when fname
        is passed in
        """
        return [backPath for first in (True, False) for backPath, __path in
                self.backup_restore_paths(first, fname)]

    def revert_backup(self, first=False): # single call site - good
        backup_paths = self.backup_restore_paths(first)
        for tup in backup_paths[1:]: # if cosaves do not exist shellMove fails!
            if not tup[0].exists():
                # if cosave exists while its backup not, delete it on restoring
                tup[1].remove()
                backup_paths.remove(tup)
        env.shellCopy(dict(backup_paths))
        # do not change load order for timestamp games - rest works ok
        self.setmtime(self.ftime)
        ##: _in_refresh=True is not entirely correct here but can't be made
        # entirely correct by leaving _in_refresh to False either as we
        # don't back up the config so we can't really detect changes in
        # imported/merged - a (another) backup edge case - as backup is
        # half-baked anyway let's agree for now that BPs remain BPs with the
        # same config as before - if not, manually run a mergeability scan
        # after updating the config (in case the restored file is a BP)
        inf = self._store().new_info(self.fn_key, notify_bain=True,
            _in_refresh=True)
        inf.copy_persistent_attrs(self)

    @property
    def backup_dir(self):
        return self._store().bash_dir.join('Backups')

    def delete_paths(self): # will include cosave ones
        return *super().delete_paths(), *self.all_backup_paths()

    def get_rename_paths(self, newName):
        old_new_paths = super().get_rename_paths(newName)
        # all_backup_paths will return the backup paths for this file and its
        # satellites (like cosaves). Passing newName in it returns the rename
        # destinations of the backup paths. Backup paths may not exist.
        old_new_paths.extend(
            zip(self.all_backup_paths(), self.all_backup_paths(newName)))
        return old_new_paths

#------------------------------------------------------------------------------
class ModInfo(FileInfo):
    """A plugin file. Currently, these are .esp, .esm, .esl and .esu files."""
    # Cached, since we need them so often
    _has_esm_flag = _is_esl = _is_overlay = False
    _valid_exts_re = r'(\.(?:' + u'|'.join(
        x[1:] for x in bush.game.espm_extensions) + '))'
    _key_to_attr = {'allowGhosting': 'mod_allow_ghosting',
        'autoBashTags': 'mod_auto_bash_tags',
        'bash.patch.configs': 'mod_bp_config', 'bashTags': 'mod_bash_tags',
        'bp_split_parent': 'mod_bp_split_parent', 'crc': 'mod_crc',
        'crc_mtime': 'mod_crc_mtime', 'crc_size': 'mod_crc_size',
        'doc': 'mod_doc', 'docEdit': 'mod_editing_doc', 'group': 'mod_group',
        'ignoreDirty': 'mod_ignore_dirty', 'installer': 'mod_owner_inst',
        'mergeInfo': 'mod_merge_info', 'rating': 'mod_rating'}
    _ignore_on_revert = frozenset([#'allowGhosting', 'bash.patch.configs',
        'bp_split_parent', # 'doc', 'docEdit', 'group', 'installer', 'rating'
        # 'autoBashTags', 'bashTags', ##: reset bashTags on reverting?
        # ignore mergeInfo/crc cache so we recalculate (resets ignoreDirty - ?)
        'crc', 'crc_mtime', 'crc_size', 'ignoreDirty', 'mergeInfo'])

    def __init__(self, fullpath, load_cache=False, itsa_ghost=None, **kwargs):
        # list of string bsas sorted by search order for localized plugins -
        # None otherwise
        self.str_bsas_sorted = None
        if itsa_ghost is None and (fullpath.cs[-6:] == '.ghost'):
            fullpath = fullpath.root
            self.is_ghost = True
        else:  # new_info() path
            self._refresh_ghost_state(itsa_ghost, regular_path=fullpath)
        super().__init__(fullpath, load_cache, **kwargs)

    def get_hide_dir(self):
        dest_dir = self._store().hidden_dir
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

    def copy_persistent_attrs(self, other, exclude=None):
        super().copy_persistent_attrs(other, exclude)
        modInfos._update_info_sets()#we need to recalculate merged/imported based on the config

    @classmethod
    def _store(cls): return modInfos

    def get_extension(self):
        """Returns the file extension of this mod."""
        return self.fn_key.fn_ext

    def set_plugin_flags(self, flags_dict: dict[PluginFlag, bool | None]):
        """Set plugin flags. If a flag is None, it is left alone. If both ESL
        and Overlay flags are requested to be set a ValueError is raised. We
        then proceed to set the other flag to False if the game supports it."""
        flags_dict = bush.game.scale_flags.check_flag_assignments(flags_dict)
        for pl_flag, flag_val in flags_dict.items():
            pl_flag.set_mod_flag(self, flag_val)
            if pl_flag is MasterFlag.ESM:
                self._update_onam() # recalculate ONAM info if necessary
        self.writeHeader()

    # ESM flag ----------------------------------------------------------------
    def has_esm_flag(self):
        """Check if the mod info is a master file based on ESM flag alone -
        header must be set. You generally want in_master_block() instead."""
        return self._has_esm_flag

    def in_master_block(self, __master_exts=frozenset(('.esm', '.esl'))):
        """Return true for files that load in the masters' block."""
        ##: we should cache this and calculate in reset_cache and co
        mod_ext = self.get_extension()
        if bush.game.Esp.extension_forces_flags:
            # For games since FO4/SSE, .esm and .esl files set the master flag
            # in memory even if not set on the file on disk. For .esp files we
            # must check for the flag explicitly.
            return mod_ext in __master_exts or self.has_esm_flag()
        elif bush.game.fsName == 'Morrowind':
            ##: This is wrong, but works for now. We need game-specific
            # record headers to parse the ESM flag for MW correctly - #480!
            return mod_ext == '.esm'
        else:
            return self.has_esm_flag()

    def isInvertedMod(self):
        """Extension indicates esp/esm, but byte setting indicates opposite."""
        mod_ext = self.get_extension()
        if mod_ext not in (u'.esm', u'.esp'): # don't use for esls
            raise ArgumentError(
                f'isInvertedMod: {mod_ext} - only esm/esp allowed')
        return (self.header and
                mod_ext != (u'.esp', u'.esm')[int(self.header.flags1) & 1])

    # ESL flag ----------------------------------------------------------------
    def is_esl(self):
        """Check if this is a light plugin - .esl files are automatically
        set the light flag, for espms check the flag."""
        return self._is_esl

    # Overlay flag ------------------------------------------------------------
    def is_overlay(self):
        """Check if this is an overlay plugin."""
        return self._is_overlay

    # CRCs --------------------------------------------------------------------
    def calculate_crc(self, recalculate=False):
        cached_crc = self.get_table_prop(u'crc')
        recalculate = recalculate or cached_crc is None or \
            self.ftime != self.get_table_prop('crc_mtime') or \
            self.fsize != self.get_table_prop(u'crc_size')
        path_crc = cached_crc
        if recalculate:
            path_crc = self.abs_path.crc
            if path_crc != cached_crc:
                self.set_table_prop(u'crc', path_crc)
                self.set_table_prop(u'ignoreDirty', False)
            self.set_table_prop('crc_mtime', self.ftime)
            self.set_table_prop(u'crc_size', self.fsize)
        return path_crc, cached_crc

    def cached_mod_crc(self): # be sure it's valid before using it!
        return self.get_table_prop(u'crc')

    def crc_string(self):
        try:
            return f'{self.cached_mod_crc():08X}'
        except TypeError: # None, should not happen so let it show
            return u'UNKNOWN!'

    def setmtime(self, set_time: int | float = 0.0, crc_changed=False):
        """Set ftime and if crc_changed is True recalculate the crc."""
        set_to = super().setmtime(set_time)
        # Prevent re-calculating the File CRC
        if not crc_changed:
            self.set_table_prop('crc_mtime', set_to)
        else:
            self.calculate_crc(recalculate=True)

    def _get_masters(self):
        """Return the plugin masters, in the order listed in its header."""
        return self.header.masters

    def has_circular_masters(self, *, fake_masters: list[FName] | None = None):
        return self.fn_key in self.recurse_masters(fake_masters=fake_masters)

    def get_dependents(self):
        """Return a set of all plugins that have this plugin as a master."""
        return modInfos.dependents[self.fn_key]

    def recurse_masters(self, *, fake_masters: list[FName] | None = None) \
            -> set[FName]:
        """Recursively collect all masters of this plugin, including transitive
        ones.

        :param fake_masters: If not None, use this instead of self.masterNames
            for determining which masters to recurse into."""
        plugins_to_check = deque([self])
        checked_plugins = set()
        ret_masters = set()
        while plugins_to_check:
            src_plugin = plugins_to_check.popleft()
            checked_plugins.add(src_plugin.fn_key)
            src_masters = (fake_masters
                           if fake_masters is not None and src_plugin is self
                           else src_plugin.masterNames)
            for src_master in src_masters:
                ret_masters.add(src_master)
                # Check to make sure we're not going to enter an infinite loop
                # if we hit a circular master situation
                if (src_master not in checked_plugins and
                        (src_master_info := modInfos.get(src_master))):
                    plugins_to_check.append(src_master_info)
        return ret_masters

    # Ghosting and ghosting related overrides ---------------------------------
    def _refresh_ghost_state(self, itsa_ghost, *, regular_path=None): # TODO(ut): absorb in _reset_cache
        """Refreshes the is_ghost state by checking existence on disk."""
        if itsa_ghost is not None:
            self.is_ghost = itsa_ghost
            return
        if regular_path is None: regular_path = self._file_key
        self.is_ghost = not regular_path.is_file() and os.path.isfile(
            f'{regular_path}.ghost')

    def do_update(self, raise_on_error=False, itsa_ghost=None, **kwargs):
        old_ghost = self.is_ghost
        self._refresh_ghost_state(itsa_ghost)
        # mark updated if ghost state changed but only reread header if needed
        did_change = super(ModInfo, self).do_update(raise_on_error)
        return did_change or self.is_ghost != old_ghost

    @FileInfo.abs_path.getter
    def abs_path(self):
        """Return joined dir and name, adding .ghost if the file is ghosted."""
        return (self._file_key + '.ghost' # Path.__add__
                ) if self.is_ghost else self._file_key

    def setGhost(self, ghostify):
        """Set file to/from ghost mode. Return True if ghost status changed."""
        # Current status is already what we want it to be
        if ghostify == self.is_ghost or ( # Don't allow ghosting the master ESM
            ghostify and self.fn_key == bush.game.master_file):
            return False
        # Current status != what we want, so change it
        ghost = (normal := self._file_key) + '.ghost' # Path.__add__ !
        # Determine source and target, then perform the move
        ghost_source = normal if ghostify else ghost
        ghost_target = ghost if ghostify else normal
        try:
            ghost_source.moveTo(ghost_target)
        except:
            deprint(f'Failed to {"" if ghostify else "un"}ghost file '
                    f'{normal if ghostify else ghost}', traceback=True)
            return False
        self.is_ghost = ghostify
        # reset cache info as un/ghosting should not make do_update return True
        self._reset_cache((self.fsize, self.ftime, self.ctime),
                          load_cache=False)
        # This is necessary if BAIN externally tracked the (un)ghosted file
        self._store()._notify_bain(renamed={ghost_source: ghost_target})
        return True

    #--Bash Tags --------------------------------------------------------------
    def setBashTags(self,keys):
        """Sets bash keys as specified."""
        self.set_table_prop(u'bashTags', keys)

    def setBashTagsDesc(self, keys, *, __re_bash_tags=re.compile(
            '{{ *BASH *:[^}]*}}\\s*\\n?', re.I)):
        """Sets bash keys as specified."""
        keys = set(keys) #--Make sure it's a set.
        if keys == self.getBashTagsDesc(): return
        if keys:
            strKeys = u'{{BASH:'+(u','.join(sorted(keys)))+u'}}\n'
        else:
            strKeys = u''
        desc_ = self.header.description
        if __re_bash_tags.search(desc_):
            desc_ = __re_bash_tags.sub(strKeys, desc_)
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
        # check if we have a cached crc for this file, use fresh mtime and size
        self.calculate_crc() # for added and hopefully updated
        for v in chain(MasterFlag, bush.game.scale_flags):
            v.set_mod_flag(self, None) # initialize _is_esl/overlay/ etc

    def writeHeader(self, old_masters: list[FName] | None = None):
        """Write Header. Actually have to rewrite entire file."""
        with TempFile() as tmp_plugin:
            with FormIdReadContext.from_info(self) as ins:
                # If we need to remap masters, construct a remapping write
                # context. Otherwise we need a regular write context due to
                # ONAM fids
                aug_masters = [*self.header.masters, self.fn_key]
                ctx_args = [tmp_plugin, aug_masters, self.header.version]
                if old_masters is not None:
                    write_ctx = RemapWriteContext(old_masters, *ctx_args)
                else:
                    write_ctx = FormIdWriteContext(*ctx_args)
                with write_ctx as out:
                    try:
                        # We already read the file header (in
                        # FormIdReadContext), so just write out the new one and
                        # copy the rest over
                        self.header.getSize()
                        self.header.dump(out)
                        out.write(ins.read(ins.size - ins.tell()))
                    except struct_error as rex:
                        raise ModError(self.fn_key, f'Struct.error: {rex}')
            self.abs_path.replace_with_temp(tmp_plugin)
        self.setmtime(crc_changed=True)
        #--Merge info
        merge_size, canMerge = self.get_table_prop('mergeInfo', (None, {}))
        if merge_size is not None:
            self.set_table_prop('mergeInfo', (self.abs_path.psize, canMerge))

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
        """True if there is another mod with the same ftime."""
        return load_order.has_load_order_conflict(self.fn_key)

    def hasActiveTimeConflict(self):
        """True if it has an active mtime conflict with another mod."""
        return load_order.has_load_order_conflict_active(self.fn_key)

    def hasBadMasterNames(self): # used in status calculation
        """True if has a master with un unencodable name in cp1252."""
        try:
            for x in self.masterNames: x.encode('cp1252')
            return False
        except UnicodeEncodeError:
            return True

    def hasBsa(self):
        """Returns True if plugin has an associated BSA."""
        # bsaInfos must be updated and contain all existing bsas
        return bool(bush.game.Bsa.attached_bsas(bsaInfos, self.fn_key))

    def get_ini_name(self):
        """Returns the name of the INI matching this plugin, if it were to
        exist."""
        return self.fn_key.fn_body + '.ini'

    def _string_files_paths(self, lang: str) -> Iterable[str]:
        fmt_dict = {'body': self.fn_key.fn_body, 'ext': self.get_extension(),
                    'language': lang}
        for str_format in bush.game.Esp.stringsFiles:
            yield os.path.join('Strings', str_format % fmt_dict)

    def getStringsPaths(self, lang):
        """If Strings Files are available as loose files, just point to
        those, otherwise extract needed files from BSA. Only use for localized
        plugins."""
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
            bsa_assets = {}
            # calculate (once per refresh cycle) and return the bsa_lo
            bsa_lo = self._store().get_bsa_lo()[0]
            # reorder bsa list as ordered by bsa_lo - what happens to patch
            # and interface here depends on what's their order in the ini
            str_bsas = sorted(self.str_bsas_sorted, key=bsa_lo.__getitem__,
                              reverse=True) # sort higher loading bsas first
            for bsa_info in str_bsas: # None for non-localized mods
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
                if str_bsas:
                    msg.append('The following BSAs were scanned (based on '
                               'name and INI settings), but none of them '
                               'contain the missing files:')
                    msg.extend(f' - {binf}' for binf in str_bsas)
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
                    m = f"Could not extract Strings File from '{bsa_inf}': {e}"
                    raise ModError(self.fn_key, m) from e
                paths.update(map(out_path.join, assets))
        return paths

    def isMissingStrings(self, available_bsas, bsa_lo_inis,
                         ci_cached_strings_paths, i_lang):
        """True if the mod says it has .STRINGS files, but the files are
        missing. Sets the str_bsas_sorted attribute to the list of BSAs that
        may contain the strings files for this plugin. We assume some games
        will load strings from 'A - B.bsa' for both 'A.esp' and 'A - B.esp'.

        :param available_bsas: all bsas apart from ini-loaded ones
        :param bsa_lo_inis: bsas that are loaded by inis
        :param ci_cached_strings_paths: Set of lower-case versions of the paths
            to all strings files. They must match the format returned by
            _string_files_paths (i.e. starting with 'strings/')."""
        if not getattr(self.header.flags1, 'localized', False): return False
        # put plugin loaded bsas first - for master esm these should be empty
        self.str_bsas_sorted = *bush.game.Bsa.attached_bsas(available_bsas,
            self.fn_key), *bsa_lo_inis # pl_bsas order is undefined
        for assetPath in self._string_files_paths(i_lang):
            # Check loose files first
            if assetPath.lower() in ci_cached_strings_paths:
                continue
            # Check in BSA's next
            for bsa_info in self.str_bsas_sorted:
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

    def has_master_size_mismatch(self, do_test): # used in status calculation
        """Checks if this plugin has at least one stored master size that does
        not match that master's size on disk."""
        if not do_test: return ''
        m_sizes = self.header.master_sizes
        for i, master_name in enumerate(self.masterNames):
            if modInfos.size_mismatch(master_name, m_sizes[i]):
                return _('Has size-mismatched masters.')
        return ''

    def _update_onam(self):
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

    def getDirtyMessage(self, scan_beth=False):
        """Return a dirty message from LOOT - or, if scan_beth is True, just
        True for a dirty vanilla plugin."""
        skipbeth = bass.settings['bash.mods.ignore_dirty_vanilla_files'] and \
                   self.fn_key in bush.game.bethDataFiles
        if not scan_beth and skipbeth: return ''
        if self.get_table_prop(u'ignoreDirty', False) or not \
                initialization.lootDb.is_plugin_dirty(self.fn_key, modInfos):
            return ''
        return True if skipbeth else _('Contains dirty edits, needs cleaning.')

    def match_oblivion_re(self):
        return self.fn_key in bush.game.modding_esm_size or \
               self.fn_key == 'Oblivion.esm'

    def delete_paths(self):
        sup = super().delete_paths()
        if self.is_ghost:
            return sup
        # Add ghosts - the file may exist in both states (bug, or user mistake)
        # in this case the file is marked as normal but let's delete the ghost
        return *sup, self.abs_path + '.ghost' # Path.__add__!

    def fs_copy(self, dup_path, *, set_time=None):
        destDir, destName = dup_path.head, dup_path.stail
        if destDir == (st := self._store()).store_dir and destName in st:
            dup_path = st[destName].abs_path # used the (possibly) ghosted path
        super().fs_copy(dup_path, set_time=set_time)

    def get_rename_paths(self, newName):
        old_new_paths = super().get_rename_paths(newName)
        if self.is_ghost: # add ghost extension to dest path - Path.__add__!
            old_new_paths[0] = (self.abs_path, old_new_paths[0][1] + '.ghost')
        return old_new_paths

    def _masters_order_status(self, status):
        mo = tuple(load_order.get_ordered(self.masterNames)) # masterOrder
        loads_before_its_masters = mo and load_order.cached_lo_index(
            mo[-1]) > load_order.cached_lo_index(self.fn_key)
        if mo != self.masterNames and loads_before_its_masters:
            return 21
        elif loads_before_its_masters:
            return 20
        elif mo != self.masterNames:
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

    def getNextSnapshot(self):
        """Returns parameters for next snapshot."""
        snapshot_dir = self._store().bash_dir.join('Snapshots')
        snapshot_dir.makedirs()
        root, ext = self.fn_key.fn_body, self.fn_key.fn_ext
        separator = '-'
        snapLast = ['00']
        #--Look for old snapshots.
        reSnap = re.compile(f'^{root}[ -]([0-9.]*[0-9]+){ext}$')
        for fileName in snapshot_dir.ilist():
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
        snapLast[-1] = f'%0{len(snapLast[-1])}d' % (int(snapLast[-1]) + 1)
        destName = root+separator+('.'.join(snapLast))+ext
        return snapshot_dir, destName, f'{root}*{ext}'

#------------------------------------------------------------------------------
def get_game_ini(ini_path, is_abs=True):
    """:rtype: GameIni | IniFileInfo | None"""
    for game_ini in gameInis:
        game_ini_path = game_ini.abs_path
        if ini_path == ((is_abs and game_ini_path) or game_ini_path.stail):
            return game_ini
    return None

def BestIniFile(abs_ini_path):
    """:rtype: IniFileInfo"""
    game_ini = get_game_ini(abs_ini_path)
    if game_ini:
        return game_ini
    inferred_ini_type, detected_encoding = get_ini_type_and_encoding(
        abs_ini_path, consider_obse_inis=bush.game.Ini.has_obse_inis)
    return inferred_ini_type(abs_ini_path, detected_encoding)

def best_ini_files(abs_ini_paths):
    """Similar to BestIniFile, but takes an iterable of INI paths and returns a
    dict mapping those paths to the created IniFileInfo objects. The functional
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
            found_types.add(IniFileInfo)
            continue
        try:
            detected_type, detected_enc = get_ini_type_and_encoding(aip,
                consider_obse_inis=bush.game.Ini.has_obse_inis)
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
            fallback_type=single_found_type,
            consider_obse_inis=bush.game.Ini.has_obse_inis)
        ret[aip] = detected_type(aip, detected_enc)
    return ret

class AINIInfo(_TabledInfo, AIniInfo):
    """Ini info, adding cached status and functionality to the ini files."""
    _status = None
    is_default_tweak = False
    _key_to_attr = {'installer': 'ini_owner_inst'}

    @classmethod
    def _store(cls): return iniInfos

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
        found_match = False
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
                    found_match = True
        if not found_match:
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
    _key_to_attr = {'info': 'save_notes'}
    _co_saves: _CosaveDict

    def __init__(self, fullpath, load_cache=False, **kwargs):
        # Dict of cosaves that may come with this save file. Need to get this
        # first, since readHeader calls _get_masters, which relies on the
        # cosave for SSE and FO4
        self._co_saves = self.get_cosaves_for_path(fullpath)
        super().__init__(fullpath, load_cache, **kwargs)

    @classmethod
    def _store(cls): return saveInfos

    def _masters_order_status(self, status):
        mo = tuple(load_order.get_ordered(self.masterNames))
        if mo != self.masterNames:
            return 20 # Reordered masters are far more important in saves
        elif status > 0:
            # Missing or reordered masters -> orange or red
            return status
        active_tuple = load_order.cached_active_tuple()
        if mo == active_tuple:
            # Exact match with LO -> purple
            return -20
        if mo == active_tuple[:len(mo)]:
            # Matches LO except for new plugins at the end -> blue
            return -10
        else:
            # Does not match the LO's active plugins, but the order is correct.
            # That means the LO has new plugins, but not at the end -> green
            return 0

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

    def do_update(self, raise_on_error=False, **kwargs):
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
        with TempFile() as tmp_plugin:
            with self.abs_path.open('rb') as ins:
                with open(tmp_plugin, 'wb') as out:
                    self.header.write_header(ins, out)
            self.abs_path.replace_with_temp(tmp_plugin)
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
                    abs(inst.abs_path.mtime - self.ftime) < 10]
        return u'\n'.join(co_ui_strings)

    def backup_restore_paths(self, first, fname=None):
        """Return as parent and in addition back up paths for the cosaves."""
        back_to_dest = super().backup_restore_paths(first, fname)
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
        try:
            xse_cosave = self.get_xse_cosave()
            # Make sure the cosave's masters are actually useful
            if xse_cosave.has_accurate_master_list():
                return [*map(FName, xse_cosave.get_master_list())]
        except (AttributeError, NotImplementedError):
            pass
        # Fall back on the regular masters - either the cosave is unnecessary,
        # doesn't exist or isn't accurate
        return [*map(FName, self.header.masters)]

    def has_circular_masters(self, *, fake_masters: list[FName] | None = None):
        return False # Saves can't have circular masters

    def _reset_masters(self):
        super(SaveInfo, self)._reset_masters()
        # If this save has ESL masters, and no cosave or a cosave from an
        # older version, then the masters are unreliable and we need to warn
        try:
            self.has_inaccurate_masters = self.header.masters_esl and (
                (xse_cosave := self.get_xse_cosave()) is None or
                not xse_cosave.has_accurate_master_list())
        except (AttributeError, NotImplementedError):
            self.has_inaccurate_masters = False

    def delete_paths(self, *, __abs=attrgetter_cache['abs_path']):
        # now add backups and cosaves backups
        return *super().delete_paths(), *map(__abs, self._co_saves.values())

    def move_info(self, destDir):
        """Moves member file to destDir. Will overwrite!"""
        super().move_info(destDir)
        SaveInfos.co_copy_or_move(self._co_saves, destDir.join(self.fn_key),
                                  move_cosave=True)

    def fs_copy(self, dup_path, *, set_time=None):
        """Copies savefile and associated cosaves file(s)."""
        super().fs_copy(dup_path, set_time=set_time)
        SaveInfos.co_copy_or_move(self._co_saves, dup_path)

    def get_rename_paths(self, newName):
        old_new_paths = super().get_rename_paths(newName)
        # super call added the backup paths but not the actual rename cosave
        # paths inside the store_dir - add those only if they exist
        old, new = old_new_paths[0] # HACK: (oldName.ess, newName.ess) abspaths
        old_new_paths.extend((co_file.abs_path, co_type.get_cosave_path(new))
                             for co_type, co_file in self._co_saves.items())
        return old_new_paths

#------------------------------------------------------------------------------
class ScreenInfo(AFileInfo):
    """Cached screenshot, stores a bitmap and refreshes it when its cache is
    invalidated."""
    _valid_exts_re = r'(\.(?:' + '|'.join(
        ext[1:] for ext in ss_image_exts) + '))'
    _has_digits = True

    def __init__(self, fullpath, load_cache=False, **kwargs):
        super().__init__(fullpath, load_cache, **kwargs)
        self.cached_bitmap = None

    def _reset_cache(self, stat_tuple, **kwargs):
        self.cached_bitmap = None # Lazily reloaded
        super()._reset_cache(stat_tuple, **kwargs)

    @classmethod
    def _store(cls): return screen_infos

    def validate_name(self, name_str, check_store=True):
        file_root, num_str = super().validate_name(name_str, check_store)
        return FName(file_root + num_str + self.fn_key.fn_ext), ''

#------------------------------------------------------------------------------
class DataStore(DataDict):
    """Base class for the singleton collections of infos."""
    store_dir: Path # where the data sit, static except for Save/ScreenInfos
    _dir_key: str # key in dirs dict for the store_dir
    # Each subclass must define this. Used when information related to the
    # store is passed between the GUI and the backend
    unique_store_key: Store

    def __init__(self, store_dict=None):
        super().__init__(FNDict() if store_dict is None else store_dict)

    def set_store_dir(self):
        self.store_dir = sd = dirs[self._dir_key]
        return sd

    # Store operations --------------------------------------------------------
    @final
    def delete(self, delete_keys, *, recycle=True):
        """Deletes member file(s)."""
        # factory is _AFileInfos only, but installers don't have corrupted so
        # let it blow if we are called with non-existing keys(join(None), boom)
        finfos = [v or self.factory(self.store_dir.join(k)) for k, v in
                  self.filter_essential(delete_keys).items()]
        try:
            self._delete_operation(finfos, recycle=recycle)
        finally:
            self.delete_refresh(finfos, True)

    def _delete_operation(self, finfos, *, recycle=True):
        abs_del_paths = [*chain.from_iterable(
            inf.delete_paths() for inf in finfos)]
        env.shellDelete(abs_del_paths, recycle=recycle)

    def delete_refresh(self, infos, check_existence):
        raise NotImplementedError

    def filter_essential(self, fn_items: Iterable[FName]):
        """Filters essential files out of the specified filenames. Returns the
        remaining ones as a dict, mapping file names to file infos. Useful to
        determine whether a file will cause instability when deleted/hidden."""
        return {k: self.get(k) for k in fn_items}

    def filter_unopenable(self, fn_items: Iterable[FName]):
        """Filter unopenable files out of the specified filenames. Returns the
        remaining ones as a dict, mapping file names to file infos."""
        return {k: self[k] for k in fn_items}

    def refresh(self): raise NotImplementedError
    def save_pickle(self): pass # for Screenshots

    def rename_operation(self, member_info, newName, rdata_ren,
                         store_refr=None):
        rename_paths = member_info.get_rename_paths(newName)
        for tup in rename_paths[1:]: # first rename path must always exist
            # if cosaves or backups do not exist shellMove fails!
            # if filenames are the same (for instance cosaves in disabling
            # saves) shellMove will offer to skip and raise SkipError
            if tup[0] == tup[1] or not tup[0].exists():
                rename_paths.remove(tup)
        env.shellMove(ren := dict(rename_paths))
        # self[newName]._mark_unchanged() # not needed with shellMove ! (#241...)
        old_key = member_info.fn_key
        ##: Make sure we pass FName in, then drop this FName call
        member_info.fn_key = FName(newName)
        #--FileInfo
        self[newName] = member_info
        member_info.abs_path = self.store_dir.join(newName)
        del self[old_key]
        if rdata_ren is None:
            rdata_ren = RefrData({old_key}, redraw={newName},
                                 renames={old_key: newName}, ren_paths=ren)
        else:
            rdata_ren.redraw.add(member_info.fn_key)
            rdata_ren.to_del.add(old_key)
            rdata_ren.renames[old_key] = newName
            rdata_ren.ren_paths.update(ren)
        return rdata_ren

    def add_info(self, file_info, destName, **kwargs):
        raise NotImplementedError

    @property
    def bash_dir(self) -> Path:
        """Return the folder where Bash persists its data.Create it on init!"""
        raise NotImplementedError

    @property
    def hidden_dir(self) -> Path:
        """Return the folder where Bash should move the file info to hide it"""
        return self.bash_dir.join(u'Hidden')

    def move_infos(self, sources, destinations, window, bash_frame):
        """Hasty hack for Files_Unhide - only use on files, not folders!"""
        try:
            env.shellMove(dict(zip(sources, destinations)), parent=window)
        except (CancelError, SkipError):
            pass
        return forward_compat_path_to_fn_list(
            {d.stail for d in destinations if d.exists()}, ret_type=set)

@dataclass(slots=True)
class RefrData:
    """Encapsulate info the backend needs to pass on to the UI for refresh."""
    to_del: set[FName] = field(default_factory=set)
    to_add: set[FName] = field(default_factory=set)
    redraw: set[FName] = field(default_factory=set)
    # renames are a dict of old fn keys to new fn keys
    renames: dict[FName, FName] = field(default_factory=dict)
    ren_paths: dict[Path, Path] = field(default_factory=dict)

    def __bool__(self):
        return bool(self.to_add or self.to_del or self.redraw)

class _AFileInfos(DataStore):
    """File data stores - all of them except InstallersData."""
    _bain_notify = True # notify BAIN on deletions/updates ?
    file_pattern = None # subclasses must define this !
    _rdata_type = RefrData
    factory: type[AFile]
    # Whether these file infos track ownership in a table
    tracks_ownership = False
    _boot_refresh_args = {'booting': True}

    def __init__(self, factory=None, *, do_refresh=True):
        """Init with specified directory and specified factory type."""
        super().__init__(self._init_store(self.set_store_dir()))
        self.factory = factory or self.__class__.factory
        if do_refresh: self.refresh(**self._boot_refresh_args)

    def _init_store(self, storedir):
        """Set up the self's _data/corrupted and return the former."""
        self.corrupted: FNDict[FName, Corrupted] = FNDict()
        deprint(f'Initializing {self.__class__.__name__}')
        deprint(f' store_dir: {storedir}')
        storedir.makedirs()
        self._data = FNDict()
        return self._data

    #--Refresh
    def refresh(self, refresh_infos=True, booting=False, *, stored_data={}):
        """Refresh from file directory."""
        rdata = self._rdata_type()
        if True: # refresh_infos
            new_or_present, del_infos = self._list_store_dir()
            for new, (oldInfo, kws) in new_or_present.items():
                try:
                    if oldInfo is not None:
                        # reread the header if any file attributes changed
                        if oldInfo.do_update(**kws):
                            rdata.redraw.add(new)
                    else: # new file or updated corrupted, get a new info
                        kws['att_val'] = stored_data.get(new)
                        self.new_info(new, _in_refresh=True,
                                      notify_bain=not booting, **kws)
                        rdata.to_add.add(new)
                except (FileError, UnicodeError, BoltError,
                        NotImplementedError) as e:
                    # old still corrupted, or new(ly) corrupted or we landed
                    # here cause cor_path was un/ghosted but file remained
                    # corrupted so in any case re-add to corrupted
                    cor_path = self.store_dir.join(new)
                    er = e.message if hasattr(e, 'message') else f'{e}'
                    self.corrupted[new] = cor = Corrupted(cor_path, er, **kws)
                    deprint(f'Failed to load {new} from {cor.abs_path}: {er}',
                            traceback=True)
                    if new := self.pop(new, None): # effectively deleted
                        del_infos.add(new)
            rdata.to_del = {d.fn_key for d in del_infos}
            self.delete_refresh(del_infos, check_existence=False)
        if rdata.redraw:
            self._notify_bain(altered={self[n].abs_path for n in rdata.redraw})
        return rdata

    #--Copy
    def add_info(self, file_info, destName, **kwargs):
        # TODO(ut) : in duplicate pass the info in and load_cache=False
        return self.new_info(destName, notify_bain=True)

    def new_info(self, fileName, *, _in_refresh=False, owner=None,
                 notify_bain=False, **kwargs):
        """Create, add to self and return a new info using self.factory.
        It will try to read the file to cache its header etc, so use on
        existing files. WIP, in particular _in_refresh must go, but that
        needs rewriting corrupted handling."""
        try:
            info = self[fileName] = self.factory(self.store_dir.join(fileName),
                                                 load_cache=True, **kwargs)
            self.corrupted.pop(fileName, None)
            if owner is not None: ##: ignore this - fixed later - belongs to info init
                try:info.set_table_prop('installer', f'{owner}')
                except KeyError:
                    deprint(f'Failed to set {owner=} for {info=}')
            if notify_bain:
                self._notify_bain(altered={info.abs_path})
            return info
        except FileError as error:
            if not _in_refresh: # if refresh just raise so we print the error
                self.corrupted[fileName] = Corrupted(
                    self.store_dir.join(fileName), error.message, **kwargs)
                self.pop(fileName, None)
            raise

    def _list_store_dir(self): # performance intensive
        file_matches_store = self.rightFileType
        inodes = top_level_files(self.store_dir)
        inodes = {x for x in inodes if file_matches_store(x)}
        return self._diff_dir(FNDict(((x, {}) for x in inodes)))

    def _diff_dir(self, inodes) -> tuple[ # ugh - when dust settles use 3.12
        dict[FName, tuple[AFile | None, dict]], set[ListInfo]]:
        """Return a dict of fn keys (see overrides) of files present in data
        dir and a set of deleted keys."""
        # for modInfos '.ghost' must have been lopped off from inode keys
        del_infos = {inf for inf in [*self.values(), *self.corrupted.values()]
                     if inf.fn_key not in inodes}
        new_or_present = {}
        for k, kws in inodes.items():
            # corrupted that has been updated on disk - if cor.abs_path
            # changed ghost state (effectively deleted) do_update returns True
            # ghost state can only change manually for corrupted - don't!
            if (cor := self.corrupted.get(k)) and cor.do_update():
                new_or_present[k] = (None, kws)
            elif not cor: # for default tweaks with a corrupted copy
                new_or_present[k] = (self.get(k), kws)
        return new_or_present, del_infos

    def delete_refresh(self, infos, check_existence):
        """Special case for the saves, inis, mods and bsas.
        :param infos: the infos corresponding to deleted items."""
        paths_to_keys = {inf.abs_path: inf.fn_key for inf in infos}
        if check_existence:
            for filePath in list(paths_to_keys):
                if filePath.exists():
                    del paths_to_keys[filePath]  # item was not deleted
        self._notify_bain(del_set={*paths_to_keys})
        del_keys = list(paths_to_keys.values())
        for del_fn in del_keys:
            self.pop(del_fn, None)
            self.corrupted.pop(del_fn, None)
        return del_keys

    def _notify_bain(self, del_set: set[Path] = frozenset(),
        altered: set[Path] = frozenset(), renamed: dict[Path, Path] = {}):
        """Note that all of these parameters need to be absolute paths!"""
        if self._bain_notify:
            InstallersData.notify_external(del_set=del_set, altered=altered,
                                           renamed=renamed)

    #--Right File Type?
    @classmethod
    def rightFileType(cls, fileName: bolt.FName | str):
        """Check if the filetype is correct for subclass by checking the
        basename (usually the extension but sometimes also the root).
        :rtype: _sre.SRE_Match | None"""
        return cls.file_pattern.search(fileName)

    def data_path_to_info(self, data_path: str, would_be=False) -> _ListInf:
        """Return the info corresponding to the specified (str, Fname or CIStr)
        path relative to the  Data folder - iff it belongs to this data store.
        If it does not, return None, except if would_be is True whereupon
        return the fname, if it is a valid one for self."""
        if (inf := self.get(fnkey := FName(str(data_path)))) or not would_be:
            return inf
        return fnkey if os.path.basename(data_path) == data_path and \
            self.rightFileType(fnkey) else None

    def rename_operation(self, member_info, newName, rdata_ren,
                         store_refr=None):
        # Override to allow us to notify BAIN if necessary
        rdata_ren = super().rename_operation(member_info, newName, rdata_ren)
        self._notify_bain(renamed=rdata_ren.ren_paths)
        return rdata_ren

class TableFileInfos(_AFileInfos):
    tracks_ownership = True
    _table_loaded = False

    def _init_from_table(self):
        """Load pickled data for mods, saves, inis and bsas."""
        deprint(f' bash_dir: {self.bash_dir}') # self.store_dir may need be set
        self.bash_dir.makedirs()
        return bolt.DataTable(self.bash_dir.join('Table.dat'),
                              load_pickle=True).pickled_data

    def refresh(self, *args, **kwargs):
        if not self._table_loaded:
            self._table_loaded = True
            kwargs['stored_data'] = self._init_from_table()
        return super().refresh(*args, **kwargs)

    def save_pickle(self):
        pd = bolt.DataTable(self.bash_dir.join('Table.dat')) # don't load!
        for k, v in self.items():
            if pickle_dict := v.get_persistent_attrs():
                pd.pickled_data[k] = pickle_dict
        pd.save()

class Corrupted(AFile):
    """A 'corrupted' file info. Stores the exception message. Not displayed."""

    def __init__(self, fullpath, error_message, *, itsa_ghost=False, **kwargs):
        self.fn_key = FName(fullpath.stail)
        if itsa_ghost:
            fullpath = fullpath + '.ghost' # Path.__add__ !
        super().__init__(fullpath, **kwargs)
        self.error_message = error_message

#------------------------------------------------------------------------------
class INIInfo(IniFileInfo, AINIInfo):
    _valid_exts_re = r'(\.(?:' + '|'.join(
        x[1:] for x in supported_ini_exts) + '))'

    def _reset_cache(self, stat_tuple, **kwargs):
        super()._reset_cache(stat_tuple, **kwargs)
        if kwargs['load_cache']: self._status = None ##: is the if check needed here?

class ObseIniInfo(OBSEIniFile, INIInfo): pass

class DefaultIniInfo(AINIInfo):
    """A default ini tweak - hardcoded."""
    is_default_tweak = True

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

    @property
    def info_dir(self):
        return dirs['ini_tweaks']

    def copy_to(self, cp_dest_path, **kwargs):
        # Default tweak, so the file doesn't actually exist
        self._store().copy_to_new_tweak(self, FName(cp_dest_path.stail))

# noinspection PyUnusedLocal
def ini_info_factory(fullpath, **kwargs) -> INIInfo:
    """INIInfos factory

    :param fullpath: Full path to the INI file to wrap
    :param load_cache: Dummy param used in INIInfos.new_info factory call
    :param kwargs: Cached ghost status information, ignored for INIs"""
    inferred_ini_type, detected_encoding = get_ini_type_and_encoding(fullpath,
        consider_obse_inis=bush.game.Ini.has_obse_inis)
    ini_info_type = (ObseIniInfo if inferred_ini_type == OBSEIniFile
                     else INIInfo)
    return ini_info_type(fullpath, detected_encoding)

@dataclass(slots=True)
class _RDIni(RefrData):
    ini_changed: bool = False

    def __bool__(self): # _RDIni is needed below
        return super(_RDIni, self).__bool__() or self.ini_changed

class INIInfos(TableFileInfos):
    file_pattern = re.compile('|'.join(
        f'\\{x}' for x in supported_ini_exts) + '$' , re.I)
    unique_store_key = Store.INIS
    _rdata_type = _RDIni
    _ini: IniFileInfo | None
    _data: dict[FName, AINIInfo]
    factory: Callable[[...], INIInfo]
    _dir_key = 'ini_tweaks'
    _boot_refresh_args = {'booting': True, 'refresh_target': False}

    def __init__(self):
        self._default_tweaks = FNDict((k, DefaultIniInfo(k, v)) for k, v in
                                      bush.game.default_tweaks.items())
        super().__init__(ini_info_factory)
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
            if ini_name == _('Browse…'): continue
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
        if _('Browse…') not in _target_inis:
            _target_inis[_('Browse…')] = None
        self.__sort_target_inis()
        if previous_ini:
            choice = list(bass.settings[u'bash.ini.choices']).index(
                previous_ini)
        bass.settings[u'bash.ini.choice'] = choice if choice >= 0 else 0
        self.ini = list(bass.settings[u'bash.ini.choices'].values())[
            bass.settings[u'bash.ini.choice']]

    def data_path_to_info(self, data_path: str, would_be=False) -> _ListInf:
        parts = os.path.split(os.fspath(data_path))
        # 1. Must have a single parent folder
        # 2. That folder must be named 'ini tweaks' (case-insensitively)
        # 3. The extension must be a valid INI-like extension - super checks it
        if len(parts) == 2 and parts[0].lower() == 'ini tweaks':
            return super().data_path_to_info(parts[1], would_be)
        return None

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
                      len_inis + 1 if a == _('Browse…') else len_inis))
        bass.settings[u'bash.ini.choices'] = OrderedDict(
            # convert stray Path instances back to unicode
            [(f'{k}', bass.settings['bash.ini.choices'][k]) for k in keys])

    def _diff_dir(self, inodes):
        old_ini_infos = {*(v for v in self.values() if not v.is_default_tweak),
                         *self.corrupted.values()}
        new_or_present, del_infos = super()._diff_dir(inodes)
        # if iinf is a default tweak a file has replaced it - set it to None
        new_or_present = {k: (inf and (None if inf.is_default_tweak else inf),
            kws) for k, (inf, kws) in new_or_present.items()}
        return new_or_present, del_infos & old_ini_infos # drop default tweaks

    def _missing_default_inis(self):
        return ((k, v) for k, v in self._default_tweaks.items() if
                k not in self)

    def refresh(self, refresh_infos=True, booting=False, refresh_target=True):
        rdata = super().refresh(booting=booting) if refresh_infos else _RDIni()
        # re-add default tweaks (booting / restoring a default over copy,
        # delete should take care of this but needs to update redraw...)
        for k, default_info in self._missing_default_inis():
            self[k] = default_info  # type: DefaultIniInfo
            if k in rdata.to_del:  # we restore default over copy
                rdata.redraw.add(k)
                default_info.reset_status()
            else: # booting
                rdata.to_add.add(k)
        rdata.ini_changed = refresh_target and (
                    self.ini.updated or self.ini.do_update())
        if rdata.ini_changed: # reset the status of all infos and let RefreshUI set it
            self.ini.updated = False
            for ini_info in self.values(): ini_info.reset_status()
        return rdata

    @property
    def bash_dir(self): return dirs[u'modsBash'].join(u'INI Data')

    def delete_refresh(self, infos, check_existence):
        del_keys = super().delete_refresh(infos, check_existence)
        if check_existence: # DataStore.delete() path - re-add default tweaks
            for k, default_info in self._missing_default_inis():
                self[k] = default_info  # type: DefaultIniInfo
                default_info.reset_status()
        return del_keys

    def filter_essential(self, fn_items: Iterable[FName]):
        # Can't remove default tweaks
        return {k: v for k in fn_items if # return None for corrupted
                not (v := self.get(k)) or not v.is_default_tweak}

    def filter_unopenable(self, fn_items: Iterable[FName]):
        # Can't open default tweaks, they are entirely virtual
        return self.filter_essential(fn_items)

    def get_tweak_lines_infos(self, tweakPath):
        return self._ini.analyse_tweak(self[tweakPath])

    def copy_to_new_tweak(self, info, fn_new_tweak: FName):
        """Duplicate tweak into fn_new_teak."""
        with open(self.store_dir.join(fn_new_tweak), 'wb') as ini_file:
            ini_file.write(info.read_ini_content(as_unicode=False)) # binary
        return self.new_info(fn_new_tweak, notify_bain=True)

    def copy_tweak_from_target(self, tweak, fn_new_tweak: FName):
        """Duplicate tweak into fn_new_teak, but with the settings that are
        currently written in the target INI."""
        if not fn_new_tweak: return False
        dup_info = self.copy_to_new_tweak(self[tweak], fn_new_tweak)
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

#-- ModInfos ------------------------------------------------------------------
def _lo_cache(lord_func):
    """Decorator to make sure I sync modInfos cache with load_order cache
    whenever I change (or attempt to change) the latter, and that I do
    refresh modInfos."""
    @wraps(lord_func)
    def _modinfos_cache_wrapper(self: ModInfos, *args, **kwargs) -> LordDiff:
        """Sync the ModInfos load order and active caches and refresh for
        load order or active changes."""
        try:
            ldiff: LordDiff = lord_func(self, *args, **kwargs)
            if not (ldiff.act_changed() or ldiff.added or ldiff.missing):
                return ldiff
            # Update all data structures that may be affected by LO change
            ldiff.affected |= self._refresh_mod_inis_and_strings()
            ldiff.affected |= self._file_or_active_updates()
            # unghost new active plugins and ghost new inactive (if autoGhost)
            ghostify = dict.fromkeys(ldiff.act_new, False)
            if bass.settings['bash.mods.autoGhost']:
                new_inactive = (ldiff.act_del - ldiff.missing) | (
                        ldiff.added - ldiff.act_new) # new mods, ghost
                ghostify.update({k: True for k in new_inactive if
                    self[k].get_table_prop('allowGhosting', True)})
            ldiff.affected.update(mod for mod, modGhost in ghostify.items()
                                  if self[mod].setGhost(modGhost))
            return ldiff
        finally:
            self._lo_wip = list(load_order.cached_lo_tuple())
            self._active_wip = list(load_order.cached_active_tuple())
    return _modinfos_cache_wrapper

#------------------------------------------------------------------------------
class ModInfos(TableFileInfos):
    """Collection of modinfos. Represents mods in the Data directory."""
    unique_store_key = Store.MODS
    _dir_key = 'mods'

    def __init__(self):
        exts = '|'.join([f'\\{e}' for e in bush.game.espm_extensions])
        self.__class__.file_pattern = re.compile(fr'({exts})(\.ghost)?$', re.I)
        #--Info lists/sets. Most are set in refresh and used in the UI. Some
        # of those could be set JIT in set_item_format, for instance, however
        # the catch is that the UI refresh is triggered by
        # RefrData.redraw/to_add so we need to calculate these in refresh.
        self.mergeScanned = [] #--Files that have been scanned for mergeability.
        masterpath = dirs['mods'].join(bush.game.master_file)
        if (master_missing := not masterpath.is_file()) and (
                ghost := masterpath + '.ghost').is_file():  # Path.__add__ !
            ghost.moveTo(masterpath)
            deprint(f'Unghosted master file - was: {ghost}')
        elif master_missing:
            raise FileError(bush.game.master_file,
                            u'File is required, but could not be found')
        self._master_esm = bush.game.master_file
        # Maps plugins to 'real indices', i.e. the ones the game will assign.
        # values are tuples of int and str for displaying in the Indices column
        self.real_indices = defaultdict(lambda: (sys.maxsize, ''))
        # Maps each plugin to a set of all plugins that have it as a master
        self.dependents = defaultdict(set)
        # Map each mergeability type to a set of plugins that can be handled
        # via that type
        self._mergeable_by_type = {m: set() for m in MergeabilityCheck}
        self.bad_names = set() #--Set of all mods with names that can't be saved to plugins.txt
        self.missing_strings = set() #--Set of all mods with missing .STRINGS files
        self.new_missing_strings = set() #--Set of new mods with missing .STRINGS files
        self.activeBad = set() #--Set of all mods with bad names that are active
        # active mod inis in active mods order (used in bsa files detection
        # for string files and in mergeability checks)
        self.plugin_inis = FNDict()
        # Set of plugins with form versions < RecordHeader.plugin_form_version
        self.older_form_versions = set()
        # merged, imported, bashed_patches caches
        self.merged, self.imported, self.bashed_patches = set(), set(), set()
        #--Oblivion version
        self.voCurrent = None
        self._voAvailable = set()
        # removed/extra mods in plugins.txt - set in load_order.py,
        # used in RefreshData
        self.warn_missing_lo_act = set()
        self.selectedExtra = set()
        # Load order caches to manipulate, then call our save methods - avoid !
        self._active_wip = []
        self._lo_wip = []
        load_order.initialize_load_order_handle(self, bush.game)
        # cache the bsa_lo for the current load order - expensive to calculate
        self.__bsa_lo = self.__bsa_cause = self.__available_bsas = None
        global modInfos
        modInfos = self ##: hack needed in ModInfo.readHeader
        super().__init__(ModInfo)

    def _update_info_sets(self):
        """Refresh bashed_patches/imported/merged - active state changes and/or
        removal/addition of plugins should trigger a refresh."""
        bps, self.bashed_patches = self.bashed_patches, {
            mname for mname, modinf in self.items() if modinf.isBP()}
        mrgd, imprtd = self.merged, self.imported
        active_patches = {bp for bp in self.bashed_patches if
               load_order.cached_is_active(bp)}
        self.merged, self.imported = self.getSemiActive(active_patches)
        return {*(bps ^ self.bashed_patches), *(mrgd ^ self.merged),
                *(imprtd ^ self.imported)}

    ##: Do we need fast_cached_property here?
    @property
    def mergeable_plugins(self) -> set[FName]:
        """All plugins that can be merged into the Bashed Patch (they may
        already *be* merged - see ModInfos.merged)."""
        return self._mergeable_by_type[MergeabilityCheck.MERGE]

    # Load order API for the rest of Bash to use - if the load order or
    # active plugins changed, those methods run a refresh on modInfos data
    @_lo_cache
    def refreshLoadOrder(self, forceRefresh=True, forceActive=True,
                         unlock_lo=False):
        # Needed for BAIN, which may have to reorder installed plugins
        with load_order.Unlock(unlock_lo):
            return load_order.refresh_lo(cached=not forceRefresh,
                                         cached_active=not forceActive)

    @_lo_cache
    def cached_lo_save_active(self, active=None):
        """Write data to Plugins.txt file.

        Always call AFTER setting the load order - make sure we unghost
        ourselves so ctime of the unghosted mods is not set."""
        return load_order.save_lo(None, load_order.get_ordered(
            self._active_wip if active is None else active))

    @_lo_cache
    def cached_lo_save_lo(self):
        """Save load order when active did not change."""
        return load_order.save_lo(self._lo_wip)

    @_lo_cache
    def cached_lo_save_all(self):
        """Save load order and plugins.txt"""
        active_wip_set = set(self._active_wip)
        dex = {x: i for i, x in enumerate(self._lo_wip) if
               x in active_wip_set}
        self._active_wip.sort(key=dex.__getitem__) # order in their load order
        return load_order.save_lo(self._lo_wip, acti=self._active_wip)

    @_lo_cache
    def undo_load_order(self): return load_order.undo_load_order()

    @_lo_cache
    def redo_load_order(self): return load_order.redo_load_order()

    #--Load Order utility methods - be sure cache is valid when using them
    def cached_lo_insert_after(self, previous, new_mod):
        new_mod = self[new_mod].fn_key ##: new_mod is not always an FName
        if new_mod in self._lo_wip: self._lo_wip.remove(new_mod)  # ...
        dex = self._lo_wip.index(previous)
        if not bush.game.using_txt_file:
            t_prev = self[previous].ftime
            if self._lo_wip[-1] == previous: # place it after the last mod
                new_time = t_prev + 60
            else:
                # try to put it right before the next mod to avoid resetting
                # ftimes of all subsequent mods - note (t_prev >= t_next)
                # might be True at the esm boundary, we could be smarter here
                t_next = self[self._lo_wip[dex + 1]].ftime
                t_prev += 1 # add one second
                new_time = t_prev if t_prev < t_next else None
            if new_time is not None:
                self[new_mod].setmtime(new_time)
        self._lo_wip[dex + 1:dex + 1] = [new_mod]

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
        lo_wip_set = set(self._lo_wip)
        new = [x for x in mods if x not in lo_wip_set]
        if not new: return
        esms = [x for x in new if self[x].in_master_block()]
        if esms:
            last = self.cached_lo_last_esm()
            for esm in esms:
                self.cached_lo_insert_after(last, esm)
                last = esm
            esms_set = set(esms)
            new = [x for x in new if x not in esms_set]
        self._lo_wip.extend(new)
        self.cached_lo_save_lo()

    def masterWithVersion(self, master_name):
        if master_name == 'Oblivion.esm' and (curr_ver := self.voCurrent):
            master_name += f' [{curr_ver}]'
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
    def _diff_dir(self, inodes):
        """ModInfos.rightFileType matches ghosts - filter those out from keys
        and pass the ghost state info to refresh."""
        ghosts = set()
        for ghost in [x for x in inodes if x.fn_ext == '.ghost']:
            if (normal := ghost.fn_body) in inodes: # they exist in both states
                ##: we need to propagate this warning once refresh dust settles
                deprint(f'File {normal} and its ghost exist. The ghost '
                        f'will be ignored but this may lead to undefined '
                        f'behavior - please remove one or the other')
            else:
                inodes[normal] = inodes[ghost]
                ghosts.add(normal)
            del inodes[ghost]
        return super()._diff_dir(FNDict(
            (x, {**kws, 'itsa_ghost': x in ghosts}) for x, kws in
            inodes.items()))

    def refresh(self, refresh_infos=True, booting=False, unlock_lo=False):
        """Update file data for additions, removals and date changes.
        See usages for how to use the refresh_infos and unlock_lo params.
        NB: if an operation *we* performed changed the load order we do not
        want lock load order to revert our own operation. So either call
        some of the set_load_order methods, or pass unlock_lo=True
        (refreshLoadOrder only *gets* load order)."""
        # Scan the data dir, getting info on added, deleted and modified files
        rdata = super().refresh(booting=booting) if refresh_infos else \
            self._rdata_type()
        mods_changes = bool(rdata)
        self._refresh_bash_tags()
        # If refresh_infos is False and mods are added _do_ manually refresh
        ldiff = self.refreshLoadOrder(forceRefresh=mods_changes or
            unlock_lo, forceActive=bool(rdata.to_del), unlock_lo=unlock_lo)
        # if active did not change, we must perform the refreshes below
        if not ((act_ch := ldiff.act_changed()) or ldiff.added or
                ldiff.missing):
            rdata.redraw |= ldiff.reordered
            # in case ini files were deleted or modified or maybe string files
            # were deleted... we need a load order below: in skyrim we read
            # inis in active order - we then need to redraw what changed status
            rdata.redraw |= self._refresh_mod_inis_and_strings()
            if mods_changes:
                rdata.redraw |= self._file_or_active_updates()
        else: # we did all the refreshes above in _modinfos_cache_wrapper
            rdata.redraw |= act_ch | ldiff.reordered | ldiff.affected
        self._voAvailable, self.voCurrent = bush.game.modding_esms(self)
        rdata.redraw -= rdata.to_add | rdata.to_del ##: centralize this
        return rdata

    def _file_or_active_updates(self):
        """If any plugins have been added, updated or deleted, or the active
        order/status changed we need to recalculate cached data structures.
        We could be more granular but the performance is elsewhere plus the
        complexity might not worth it."""
        self._recalc_dependents()
        return {*self._refresh_active_no_cp1252(), *self._update_info_sets(),
                *self._recalc_real_indices(), *self._refreshMergeable()}

    def _refresh_mod_inis_and_strings(self):
        """Refresh ini and str files from Data directory. Those need to be
        refreshed if active mods change or mods are added/removed - but also
        in a plain tab out/in Bash, as those are regular files. We should
        centralize data dir scanning. String files depend on inis."""
        ##: depends on bsaInfos thus a bsaInfos.refresh should trigger
        # a modInfos.refresh - see comments in get_bsa_lo
        data_folder_path = bass.dirs['mods']
        self.plugin_inis = self.__load_plugin_inis(data_folder_path)
        # We'll be removing BSAs from here once we've given them a position
        self.__available_bsas = av_bsas = FNDict(bsaInfos.items())
        # Determine BSA LO from INIs once, this gets expensive very quickly
        ##: What about SkyrimCustom.ini etc?
        self.__bsa_lo, self.__bsa_cause = bush.game.Ini.get_bsas_from_inis(
            av_bsas, *self.plugin_inis.values(), oblivionIni)
        if not bush.game.Esp.stringsFiles:
            return set()
        # refresh which mods are supposed to have strings files, but are
        # missing them (=CTD). For Skyrim you need to have a valid load order
        oldBad = self.missing_strings
        # Determine the present strings files once to avoid stat'ing
        # non-existent strings files hundreds of times
        try:
            strings_files = os.listdir(data_folder_path.join('strings'))
            ci_cached_strings_paths = {f'strings{os.path.sep}{s.lower()}'
                                       for s in strings_files}
        except FileNotFoundError:
            # No loose strings folder -> all strings are in BSAs
            ci_cached_strings_paths = set()
        i_lang = oblivionIni.get_ini_language(bush.game.Ini.default_game_lang)
        # sort the ini-loaded bsas in an optimal way for detecting strings
        hi_to_lo = sorted(self.__bsa_lo, key=lambda bi:
            bush.game.Bsa.heuristic_sort_key(bi, self.__bsa_lo))
        self.missing_strings = {k for k, v in self.items() if
            v.isMissingStrings(av_bsas, hi_to_lo, ci_cached_strings_paths,
                               i_lang)}
        self.new_missing_strings = self.missing_strings - oldBad
        return self.missing_strings ^ oldBad

    def __load_plugin_inis(self, data_folder_path):
        if not bush.game.Ini.supports_mod_inis:
            return self.plugin_inis # empty FNDict
        # First, check the Data folder for INIs present in it. Order does not
        # matter, we will only use this to look up existence
        lower_data_cont = (f.lower() for f in os.listdir(data_folder_path))
        present_inis = {i for i in lower_data_cont if i.endswith('.ini')}
        # Determine which INIs are active based on LO. Order now matters
        possible_inis = [self[m].get_ini_name() for m in
                         load_order.cached_active_tuple()]
        active_inis = [i for i in possible_inis if i.lower() in present_inis]
        # Add new or modified INIs to the cache and copy the final order
        inis_active = []
        # check present inis for updates
        prev_inis = {k.abs_path: k for k in self.plugin_inis.values()}
        for acti_ini_name in active_inis:
            # Need to restore the full path here since we'll stat that path
            # when resetting the cache during __init__
            acti_ini_path = data_folder_path.join(acti_ini_name)
            acti_ini = prev_inis.get(acti_ini_path)
            if acti_ini is None or acti_ini.do_update():
                acti_ini = IniFileInfo(acti_ini_path, 'cp1252')
            inis_active.append(acti_ini)
        # values in active order, later loading inis override previous settings
        return FNDict((k.abs_path.stail, k) for k in reversed(inis_active))

    def _refresh_active_no_cp1252(self):
        """Refresh which filenames cannot be saved to plugins.txt - active
        state changes and/or removal/addition of plugins should trigger a
        refresh. It seems that Skyrim and Oblivion read plugins.txt as a
        cp1252 encoded file, and any filename that doesn't decode to cp1252
        will be skipped."""
        old_bad, self.bad_names = self.bad_names, set()
        old_ab, self.activeBad = self.activeBad, set()
        for fileName in self:
            if self.isBadFileName(fileName):
                if load_order.cached_is_active(fileName):
                    ##: For now, we'll leave them active, until we finish
                    # testing what the game will support
                    #self.lo_deactivate(fileName)
                    self.activeBad.add(fileName)
                else:
                    self.bad_names.add(fileName)
        return (self.activeBad ^ old_ab) | (self.bad_names ^ old_bad)

    def _refreshMergeable(self):
        """Refreshes set of mergeable mods."""
        # All plugins that could be merged, ESL-flagged or Overlay-flagged
        oldMergeable = {*chain.from_iterable(self._mergeable_by_type.values())}
        #--Mods that need to be rescanned
        rescan_mods = set()
        for m in self._mergeable_by_type.values():
            m.clear()
        merg_checks = bush.game.mergeability_checks
        # We store ints in the settings files, so use those for comparing
        merg_checks_ints = {c.value for c in merg_checks}
        quick_checks = {mc: pflag.check_type for pflag in bush.game.scale_flags
                        if (mc := pflag.merge_check) is not None}
        # We need to scan dependent mods first to account for mergeability of
        # their masters
        for fn_mod, modInfo in dict_sort(self, reverse=True,
                                         key_f=load_order.cached_lo_index):
            cached_size, canMerge = modInfo.get_table_prop('mergeInfo',
                                                           (None, {}))
            if not isinstance(canMerge, dict):
                canMerge = {} # Convert older settings (had a bool here)
            # Quickly check if some mergeability types are impossible for this
            # plugin (because it already has the target type)
            covered_checks = set()
            for m, m_check in quick_checks.items():
                if m_check(modInfo):
                    canMerge[m.value] = False
                    covered_checks.add(m)
            # Clean up cached mergeability info - this can get out of sync if
            # we add or remove a mergeability type from a game or change a
            # mergeability type's int key in the enum
            for m in list(canMerge):
                if m not in merg_checks_ints:
                    del canMerge[m]
            modInfo.set_table_prop('mergeInfo', (cached_size, canMerge))
            if not (merg_checks - covered_checks):
                # We've already covered all required checks with those checks
                # above (e.g. an ESL-flagged plugin in a game with only ESL
                # support -> not ESL-flaggable), so move on
                continue
            elif (cached_size == modInfo.fsize and
                  set(canMerge) == merg_checks_ints):
                # The cached size matches what we have on disk and we have data
                # for all required mergeability checks, so use the cached info
                self._update_mergeable(fn_mod, canMerge)
            else:
                # We have to rescan mergeability - either the plugin's size
                # changed or there is at least one required mergeability check
                # we have not yet run for this plugin
                rescan_mods.add(fn_mod)
        if rescan_mods:
            self.rescanMergeable(rescan_mods) ##: maybe re-add progress?
        difMergeable = (oldMergeable ^ {*chain.from_iterable(
            self._mergeable_by_type.values())}) & set(self)
        return rescan_mods | difMergeable

    def rescanMergeable(self, names, progress=bolt.Progress(),
                        return_results=False):
        """Rescan specified mods. Return value is only meaningful when
        return_results is set to True."""
        merge = MergeabilityCheck.MERGE
        checks = bush.game.mergeability_checks
        # The checks that are actually required for this game
        required_checks = {merge: isPBashMergeable} if merge in checks else {}
        required_checks.update(
            {mc: pflag.can_convert for pflag in bush.game.scale_flags if
             (mc := pflag.merge_check) in checks})
        with progress:
            progress.setFull(max(len(names),1))
            result = {}
            for i, fileName in enumerate(names): ##: this must be sorted in inverted load order for _dependent
                all_reasons = {m: [] if return_results else None for m in
                               required_checks}
                progress(i, fileName)
                fileInfo = self[fileName]
                cs_name = fileName.lower()
                check_results = {}
                for merg_type, merg_check in required_checks.items():
                    reasons = all_reasons[merg_type]
                    if cs_name in bush.game.bethDataFiles:
                        # Fail all mergeability checks for vanilla plugins
                        if return_results:
                            reasons.append(_('Is Vanilla Plugin.'))
                        check_results[merg_type] = False
                    else:
                        try:
                            check_results[merg_type] = merg_check(
                                fileInfo, self, reasons, ModHeaderReader)
                        except Exception: # as e
                            # deprint(f'Error scanning mod {fileName} ({e})')
                            # # Assume it's not mergeable
                            # check_results[merg_type] = False
                            raise
                # Special handling for MERGE: NoMerge-tagged plugins
                if return_results:
                    if check_results.get(merge) and \
                            'NoMerge' in fileInfo.getBashTags():
                        all_reasons[merge].append(
                            _('Technically mergeable, but has NoMerge tag.'))
                    result[fileName] = all_reasons
                self._update_mergeable(fileName, check_results)
                # Only store the enum values (i.e. the ints) in our settings
                # files, we are moving away from pickling non-std classes
                fileInfo.set_table_prop('mergeInfo', (fileInfo.fsize, {
                    k.value: v for k, v in check_results.items()}))
            return result

    def _update_mergeable(self, fileName,
                          check_results: dict[MergeabilityCheck | int, bool]):
        """Update internal _mergeable_by_type cache - should be replaced by
        ModInfo properties."""
        for m, m_mergeable in check_results.items():
            merg_set = self._mergeable_by_type[MergeabilityCheck(m)]
            if m_mergeable:
                merg_set.add(fileName)
            else:
                merg_set.discard(fileName)

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
            if autoTag is None:
                if modinf.get_table_prop('bashTags') is None:
                    # A new mod, set auto tags to True (default)
                    modinf.set_auto_tagged(True)
                    autoTag = True
                else:
                    # An old mod that had manual bash tags added
                    modinf.set_auto_tagged(False) # disable auto tags
            if autoTag:
                modinf.reloadBashTags(ci_cached_bt_contents=bt_contents)

    def refresh_crcs(self, mods=None, progress=None):
        pairs = {}
        with (progress := progress or bolt.Progress()):
            mods = (self if mods is None else mods)
            if mods: progress.setFull(len(mods))
            for dex, mod_key in enumerate(mods):
                progress(dex, _('Calculating crc:') + f'\n{mod_key}')
                inf = self[mod_key]
                pairs[mod_key] = inf.calculate_crc(recalculate=True)
        return pairs

    #--Refresh File
    def new_info(self, fileName, _in_refresh=False, owner=None,
                 notify_bain=False, **kwargs):
        try:
            return super().new_info(fileName, _in_refresh=_in_refresh,
                owner=owner, notify_bain=notify_bain, **kwargs)
        finally:
            # we should refresh info sets if we manage to add the info, but
            # also if we fail, which might mean that some info got corrupted
            if not _in_refresh:
                self._update_info_sets() # we may need to use the return value

    #--Mod selection ----------------------------------------------------------
    def getSemiActive(self, patches, skip_active=False):
        """Return (merged,imported) mods made semi-active by Bashed Patch.

        If no bashed patches are present in 'patches' then return empty sets.
        Else for each bashed patch use its config (if present) to find mods
        it merges or imports.

        :param patches: A set of mods to look for bashed patches in.
        :param skip_active: If True, only return inactive merged/imported
            plugins."""
        merged_,imported_ = set(),set()
        for patch in patches & self.bashed_patches: # this must be up to date!
            patchConfigs = self[patch].get_table_prop('bash.patch.configs')
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
    def lo_activate(self, fileName, _modSet=None, _children=None,
                    _activated=None, doSave=False):
        """Mutate _active_wip cache then save if doSave is True."""
        if _activated is None: _activated = set()
        # Skip .esu files, those can't be activated
        ##: This .esu handling needs to be centralized - sprinkled all over
        # actives related lo_* methods
        if fileName.fn_ext == u'.esu': return []
        try:
            msg = load_order.check_active_limit([*self._active_wip, fileName],
                                                as_type=str)
            if msg:
                msg = f'{fileName}: Trying to activate more than {msg}'
                raise PluginsFullError(msg)
            if _children:
                if fileName in _children:
                    raise BoltError(f'Circular Masters: '
                                    f'{" >> ".join((*_children, fileName))}')
                _children.append(fileName)
            else:
                _children = [fileName]
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
                    self.lo_activate(master, _modSet, _children, _activated)
            #--Select in plugins
            if fileName not in acti_set:
                self._active_wip.append(fileName)
                _activated.add(fileName)
            return load_order.get_ordered(_activated)
        finally:
            if doSave: self.cached_lo_save_active()

    def lo_deactivate(self, *filenames, doSave=False):
        """Remove mods and their children from _active_wip, can only raise if
        doSave=True."""
        filenames = {*load_order.filter_pinned(filenames, filter_mods=True)}
        old = set_awip = set(self._active_wip)
        diff = set_awip - filenames
        if len(diff) == len(set_awip): return set()
        #--Unselect self
        set_awip = diff
        #--Unselect children
        children = set()
        cached_dependents = self.dependents
        for fileName in filenames:
            children |= cached_dependents[fileName]
        while children:
            child = children.pop()
            if child not in set_awip: continue # already inactive, skip checks
            set_awip.remove(child)
            children |= cached_dependents[child]
        # Commit the changes made above
        self._active_wip = [x for x in self._active_wip if x in set_awip]
        #--Save
        if doSave: self.cached_lo_save_active()
        return old - set_awip # return deselected

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
                self.lo_activate(p)
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
                    if p not in self.mergeable_plugins: _add_to_actives(p)
            except PluginsFullError:
                raise
            if activate_mergeable:
                try:
                    # Then activate as many of the mergeable plugins as we can
                    for p in s_plugins:
                        if p in self.mergeable_plugins: _add_to_actives(p)
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
        wip_actives.update(load_order.filter_pinned(present_plugins))
        # Sort the result and check if we would hit an actives limit
        ordered_wip = load_order.get_ordered(wip_actives)
        trimmed_plugins = load_order.check_active_limit(ordered_wip)
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

    def create_new_mod(self, newName: str | FName,
            selected: tuple[FName, ...] = (),
            wanted_masters: list[FName] | None = None, dir_path=empty_path,
            is_bashed_patch=False, flags_dict=None) -> ModInfo | None:
        """Create a new plugin.

        :param newName: The name the created plugin will have.
        :param selected: The currently selected after which the plugin will be
            created in the load order. If empty, the new plugin will be placed
            last in the load order. Only relevant if dir_path is unset or
            matches the Data folder.
        :param wanted_masters: The masters the created plugin will have.
        :param dir_path: The directory in which the plugin will be created. If
            empty, defaults to the Data folder.
        :param is_bashed_patch: If True, mark the created plugin as a Bashed
            Patch.
        :param flags_dict: set plugin flags - incompatible flags will raise an
            InvalidPluginFlagsError."""
        if wanted_masters is None:
            wanted_masters = [self._master_esm]
        dir_path = dir_path or self.store_dir
        newInfo = self.factory(dir_path.join(newName))
        newFile = ModFile(newInfo)
        newFile.tes4.masters = wanted_masters
        if is_bashed_patch:
            newFile.tes4.author = u'BASHED PATCH'
        flags_dict = bush.game.scale_flags.check_flag_assignments(
            flags_dict or {})
        for pl_flag, flag_val in flags_dict.items():
            pl_flag.set_mod_flag(newFile.tes4.flags1, flag_val)
        newFile.safeSave()
        if dir_path == self.store_dir:
            last_selected = load_order.get_ordered(selected)[
                -1] if selected else self._lo_wip[-1]
            inf = self.add_info(newInfo, newName, insert_after=last_selected,
                                save_lo_cache=True)
            self.refresh(refresh_infos=False)
            return inf

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

    def get_bsa_lo(self):
        """Get the load order of all active BSAs. Used from bain, so we
        calculate it JIT using the cached result of get_bsas_from_inis.
        Therefore, self.__bsa_lo is initially populated by bsas loaded from
        the inis, having ±sys.maxsize load order."""
        ##:(233) we do this once till next refresh - not entirely correct,
        # as deletions/installs of BSAs from inside Bash (BAIN or future
        # bsa tab) should rerun _refresh_mod_inis_and_strings/notify modInfos
        if self.__available_bsas is not None:
            bush.game.Bsa.update_bsa_lo(load_order.cached_active_tuple(),
                self.__available_bsas, self.__bsa_lo, self.__bsa_cause)
            # we are called in a loop, cache on first iteration
            self.__available_bsas = None
        return self.__bsa_lo, self.__bsa_cause

    @staticmethod
    def plugin_wildcard(file_str=_('Plugins')):
        joinstar = ';*'.join(bush.game.espm_extensions)
        return f'{bush.game.display_name} {file_str} (*{joinstar})|*{joinstar}'

    #--Mod move/delete/rename -------------------------------------------------
    def _lo_caches_remove_mods(self, to_remove):
        """Remove the specified mods from _lo_wip and _active_wip caches."""
        # Use set to speed up lookups and note that these are strings (at least
        # when they come from delete_refresh, check others?)
        to_remove = {FName(x) for x in to_remove}
        # Remove mods from cache
        self._lo_wip = [x for x in self._lo_wip if x not in to_remove]
        self._active_wip = [x for x in self._active_wip if x not in to_remove]

    def rename_operation(self, member_info, newName, rdata_ren,
                         store_refr=None):
        """Renames member file from oldName to newName."""
        isSelected = load_order.cached_is_active(member_info.fn_key)
        if isSelected:
            self.lo_deactivate(member_info.fn_key)
        rdata_ren = super().rename_operation(member_info, newName, rdata_ren)
        # rename in load order caches
        oldIndex = self._lo_wip.index(old_key := next(iter(rdata_ren.renames)))
        self._lo_caches_remove_mods([old_key])
        self._lo_wip.insert(oldIndex, newName)
        if isSelected: self.lo_activate(newName)
        # Save to disc (load order and plugins.txt)
        self.cached_lo_save_all()
        # Update linked BP parts if the parent BP got renamed
        for mod_inf in self.values():
            if mod_inf.get_table_prop('bp_split_parent') == old_key:
                mod_inf.set_table_prop('bp_split_parent', newName)
        return rdata_ren

    #--Delete
    def delete_refresh(self, infos, check_existence):
        # adapted from refresh() (avoid refreshing from the data directory)
        del_keys = super().delete_refresh(infos, check_existence)
        # we need to call deactivate to deactivate dependents
        self.lo_deactivate(*del_keys) # no-op if empty
        if del_keys and check_existence: # delete() path - refresh caches
            self._lo_caches_remove_mods(del_keys)
            self.cached_lo_save_all() # will perform the needed refreshes
        return del_keys

    def filter_essential(self, fn_items: Iterable[FName]):
        # Removing the game master breaks everything, for obvious reasons
        return {k: self.get(k) for k in fn_items if k != self._master_esm}

    def move_infos(self, sources, destinations, window, bash_frame):
        moved = super().move_infos(sources, destinations, window, bash_frame)
        self.refresh() # yak, it should have an "added" parameter
        bash_frame.warn_corrupted(warn_mods=True, warn_strings=True)
        return moved

    def add_info(self, file_info, destName, *, insert_after=None,
                 save_lo_cache=False):
        inf = super().add_info(file_info, destName)
        self.cached_lo_insert_after(insert_after or file_info.fn_key, destName)
        if save_lo_cache: self.cached_lo_save_lo()
        return inf

    #--Mod info/modify --------------------------------------------------------
    def getVersion(self, fileName):
        """Check we have a fileInfo for fileName and call get_version on it."""
        return self[fileName].get_version() if fileName in self else ''

    #--Oblivion 1.1/SI Swapping -----------------------------------------------
    _retry_msg = [_('Wrye Bash encountered an error when renaming %(old)s to '
                    '%(new)s.'), '', '',
        _('The file is in use by another process such as %(xedit_name)s.'), '',
        _('Please close the other program that is accessing %(new)s.'), '', '',
        _('Try again?')]
    def try_set_version(self, set_version, *, do_swap=None):
        """Set Oblivion version to specified one - dry run if do_swap is None,
        else do_swap must be an askYes callback. Our caches must be fresh from
        refresh to detect versions properly."""
        curr_ver = self.voCurrent # may be None if Oblivion.esm size is unknown
        if set_version is None or curr_ver is None:
            # for do_swap False set_version != None => curr_ver == None
            return curr_ver # return curr_ver as a convenience for saveInfos
        master_esm = self._master_esm # Oblivion.esm, say it's currently SI one
        # rename Oblivion.esm to this, for instance: Oblivion_SI.esm
        move_to = FName(f'{(fnb := master_esm.fn_body)}_{curr_ver}.esm')
        if set_version != curr_ver and set_version in self._voAvailable and \
                not (move_to in self or move_to in self.corrupted):
            if not do_swap: return True # we can swap
        else: return False
        # Swap Oblivion.esm to specified version - do_swap is askYes callback
        # if new version is '1.1' then copy_from is FName(Oblivion_1.1.esm)
        copy_from = FName(f'{fnb}_{set_version}.esm')
        swapped_inf = self[copy_from]
        swapping_a_ghost = swapped_inf.is_ghost # will ghost the master esm!
        #--Rename
        baseInfo = self[master_esm]
        master_time = baseInfo.ftime
        new_info_time = swapped_inf.ftime
        is_new_info_active = load_order.cached_is_active(copy_from)
        # can't use ModInfos rename because it will mess up the load order
        file_info_rename_op = super(ModInfos, self).rename_operation
        rename_args = (baseInfo, move_to), (swapped_inf, master_esm)
        deltd = swapped_inf.abs_path # will be (effectively) deleted
        for do_undo, inf_fname in enumerate(rename_args):
            while True:
                try:
                    file_info_rename_op(*inf_fname)
                    break
                except PermissionError: ##: can only occur if SHFileOperation
                    # isn't called - file operation API badly needed (#241)
                    old = inf_fname[0].abs_path
                    new = inf_fname[0].get_rename_paths(inf_fname[1])[0][1]
                    msg = '\n'.join(self._retry_msg) % {'old': old, 'new': new,
                        'xedit_name': bush.game.Xe.full_name, }
                    if do_swap(msg, title=_('File in Use')):
                        continue
                    if do_undo: file_info_rename_op(self[move_to], master_esm)
                    raise
                except CancelError:
                    if do_undo: file_info_rename_op(self[move_to], master_esm)
                    return
        master_inf = self[master_esm]
        # set mtimes to previous respective values
        master_inf.setmtime(master_time)
        self[move_to].setmtime(new_info_time)
        oldIndex = self._lo_wip.index(copy_from)
        self._lo_caches_remove_mods([copy_from])
        self._lo_wip.insert(oldIndex, move_to)
        (self.lo_activate if is_new_info_active else self.lo_deactivate)(
            move_to)
        if swapping_a_ghost: # we need to unghost the master esm
            master_inf.setGhost(False)
        # Save to disc (load order and plugins.txt)
        self.cached_lo_save_all()
        # make sure to notify BAIN rename_operation passes only renames param
        self._notify_bain(altered={master_inf.abs_path}, del_set={deltd})
        self.voCurrent = set_version
        self._voAvailable.add(curr_ver)
        self._voAvailable.remove(set_version)

    def size_mismatch(self, plugin_name, plugin_size):
        """Checks if the specified plugin exists and, if so, if its size
        does not match the specified value (in bytes)."""
        return plugin_name in self and plugin_size != self[plugin_name].fsize

    def _recalc_real_indices(self):
        """Recalculate the real indices cache, which is the index the game will
        assign to plugins. ESLs will land in the 0xFE spot, while inactive
        plugins don't get any - so we sort them last. Return a set of mods
        whose real index changed."""
        # Note that inactive plugins are handled by our defaultdict factory
        old, self.real_indices = self.real_indices, defaultdict(
            lambda: (sys.maxsize, ''))
        bush.game.scale_flags.get_indexes(
            ((p, self[p]) for p in load_order.cached_active_tuple()),
            self.real_indices)
        return {k for k, v in old.items() ^ self.real_indices.items()}

    def _recalc_dependents(self):
        """Recalculates the dependents cache. See ModInfo.get_dependents for
        more information."""
        cached_dependents = self.dependents
        cached_dependents.clear()
        for p, p_info in self.items():
            for p_master in p_info.masterNames:
                cached_dependents[p_master].add(p)

#------------------------------------------------------------------------------
class SaveInfos(TableFileInfos):
    """SaveInfo collection. Represents save directory and related info."""
    _bain_notify = tracks_ownership = False
    # Enabled and disabled saves, no .bak files ##: needed?
    file_pattern = re.compile('(%s)(f?)$' % '|'.join(fr'\.{s}' for s in
        [bush.game.Ess.ext[1:], bush.game.Ess.ext[1:-1] + 'r']), re.I)
    unique_store_key = Store.SAVES

    def set_store_dir(self, save_dir=None, do_swap=None):
        """If save_dir is None, read the current save profile from
        oblivion.ini file, else update the ini with save_dir."""
        # saveInfos singleton is constructed in InitData after oblivionIni
        prev = getattr(self, 'localSave', None)
        if save_dir is None:
            save_dir = oblivionIni.getSetting(*bush.game.Ini.save_profiles_key,
                default=bush.game.Ini.save_prefix).rstrip('\\')
        else: # set SLocalSavePath in Oblivion.ini - the latter must exist
            # not sure if appending the slash is needed for the game to parse
            # the setting correctly, kept previous behavior
            oblivionIni.saveSetting(*bush.game.Ini.save_profiles_key,
                                    value=f'{save_dir}\\')
        self.localSave = save_dir
        if (boot := prev is None) or prev != save_dir:
            old = not boot and self.store_dir
            if not boot:
                self.save_pickle() # save current data before setting store_dir
                self._table_loaded = False
            self.store_dir = sd = dirs['saveBase'].join(env.convert_separators(
                save_dir)) # localSave always has backslashes
            if do_swap:
                # save current plugins into old directory, load plugins from sd
                if load_order.swap(old, sd):
                    modInfos.refreshLoadOrder(unlock_lo=True)
                # Swap Oblivion version to memorized version
                voNew = self.get_profile_attr(save_dir, 'vOblivion', None)
                if curr := modInfos.try_set_version(voNew, do_swap=do_swap):
                    self.set_profile_attr(save_dir, 'vOblivion', curr)
            if not boot: # else in __init__,  calling _init_store right after
                self._init_store(sd)
        return self.store_dir

    def __init__(self):
        super().__init__(SaveInfo)
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

    def data_path_to_info(self, data_path: str, would_be=False) -> _ListInf:
        return None # Never relative to Data folder

    @classmethod
    def valid_save_exts(cls):
        """Returns a cached version of the valid extensions that a save may
        have."""
        try:
            return cls._valid_save_exts
        except AttributeError:
            std_save_ext = bush.game.Ess.ext[1:]
            accepted_exts = {std_save_ext, std_save_ext[:-1] + 'r', 'bak'}
            # Add 'first backup' versions of the extensions too
            accepted_exts.update(f'{e}f' for e in accepted_exts.copy())
            cls._valid_save_exts = accepted_exts
            return accepted_exts

    @classmethod
    def _parse_save_path(cls, save_name: FName | str) -> tuple[
            str | None, str | None]:
        """Parses the specified save name into root and extension, returning
        them as a tuple. If the save path does not point to a valid save,
        returns two Nones instead."""
        save_root, save_ext = os.path.splitext(save_name)
        save_ext_trunc = save_ext[1:]
        if save_ext_trunc.lower() not in cls.valid_save_exts():
            # Can't be a valid save, doesn't end in ess/esr/bak
            return None, None
        cs_ext = bush.game.Se.cosave_ext[1:]
        if any(s.lower() == cs_ext for s in save_root.split('.')):
            # Almost certainly not a valid save, had the cosave extension
            # in one of its root parts
            return None, None
        return save_root, save_ext

    @property
    def bash_dir(self): return self.store_dir.join(u'Bash')

    def refresh(self, refresh_infos=True, booting=False, *, save_dir=None,
                do_swap=None):
        if not booting: # else we just called __init__
            self.set_store_dir(save_dir, do_swap)
        return super().refresh(booting=booting) if refresh_infos else \
           self._rdata_type()

    def rename_operation(self, member_info, newName, rdata_ren,
                         store_refr=None):
        """Renames member file from oldName to newName, update also cosave
        instance names."""
        rdata_ren = super().rename_operation(member_info, newName, rdata_ren)
        for co_type, co_file in self[newName]._co_saves.items():
            co_file.abs_path = co_type.get_cosave_path(self[newName].abs_path)
        return rdata_ren

    @staticmethod
    def co_copy_or_move(co_instances, dest_path: Path, move_cosave=False):
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
        moved = super().move_infos(sources, destinations, window, bash_frame)
        for s, d in zip(sources, destinations):
            if FName(d.stail) in moved:
                co_instances = SaveInfo.get_cosaves_for_path(s)
                self.co_copy_or_move(co_instances, d, move_cosave=True)
        for m in moved:
            try:
                self.new_info(m, notify_bain=True) ##: why True??
            except FileError:
                pass # will warn below
        bash_frame.warn_corrupted(warn_saves=True)
        return moved

#------------------------------------------------------------------------------
class BSAInfos(TableFileInfos):
    """BSAInfo collection. Represents bsa files in game's Data directory."""
    # BSAs that have versions other than the one expected for the current game
    mismatched_versions = set()
    # Maps BA2 hashes to BA2 names, used to detect collisions
    _ba2_hashes = defaultdict(set)
    ba2_collisions = set()
    unique_store_key = Store.BSAS
    _dir_key = 'mods'

    def __init__(self):
        ##: Hack, this should not use display_name
        if bush.game.display_name == 'Oblivion':
            # Need to do this at runtime since it depends on inisettings (ugh)
            bush.game.Bsa.redate_dict[inisettings[
                u'OblivionTexturesBSAName']] = 1104530400 # '2005-01-01'
        self.__class__.file_pattern = re.compile(
            f'{re.escape(bush.game.Bsa.bsa_extension)}$', re.I)
        _bsa_type = bsa_files.get_bsa_type(bush.game.fsName)
        class BSAInfo(FileInfo, _bsa_type):
            _valid_exts_re = fr'(\.{bush.game.Bsa.bsa_extension[1:]})'
            def __init__(self, fullpath, load_cache=False, **kwargs):
                try:  # Never load_cache for memory reasons - let it be
                    # loaded as needed
                    super().__init__(fullpath, load_cache=False, **kwargs)
                except BSAError as e:
                    raise FileError(GPath(fullpath).tail,
                        f'{e.__class__.__name__}  {e.message}') from e
                self._reset_bsa_mtime()
            _key_to_attr = {'info': 'bsa_notes', 'installer': 'bsa_owner_inst'}

            @classmethod
            def _store(cls): return bsaInfos

            def do_update(self, raise_on_error=False, **kwargs):
                did_change = super(BSAInfo, self).do_update(raise_on_error)
                self._reset_bsa_mtime()
                return did_change

            def readHeader(self):  # just reset the cache
                self._assets = self.__class__._assets

            def _reset_bsa_mtime(self):
                if bush.game.Bsa.allow_reset_timestamps and inisettings[
                    u'ResetBSATimestamps']:
                    default_mtime = bush.game.Bsa.redate_dict[self.fn_key]
                    if self.ftime != default_mtime:
                        self.setmtime(default_mtime)
        super().__init__(BSAInfo)

    def new_info(self, fileName, _in_refresh=False, owner=None,
                 notify_bain=False, **kwargs):
        new_bsa = super().new_info(fileName, _in_refresh=_in_refresh,
            owner=owner, notify_bain=notify_bain, **kwargs)
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

    # BSA Redirection ---------------------------------------------------------
    _aii_name = 'ArchiveInvalidationInvalidated!.bsa'
    _bsa_redirectors = {_aii_name.lower(), '..\\obmm\\bsaredirection.bsa'}

    @staticmethod
    def remove_invalidation_file():
        """Removes ArchiveInvalidation.txt, if it exists in the game folder.
        This is used when disabling other solutions to the Archive Invalidation
        problem prior to enabling WB's BSA Redirection."""
        dirs['app'].join('ArchiveInvalidation.txt').remove()

    def set_bsa_redirection(self, *, do_redirect: bool):
        """Activate or deactivate BSA redirection - game ini must exist!"""
        if oblivionIni.isCorrupted: return
        br_section, br_key = bush.game.Ini.bsa_redirection_key
        if not br_section or not br_key: return
        aii_bsa = self.get(self._aii_name)
        aiBsaMTime = time.mktime((2006, 1, 2, 0, 0, 0, 0, 2, 0))
        if aii_bsa and aii_bsa.ftime > aiBsaMTime:
            aii_bsa.setmtime(aiBsaMTime)
        # check if BSA redirection is active
        sArchives = oblivionIni.getSetting(br_section, br_key, '')
        is_bsa_redirection_active = any(x for x in sArchives.split(',')
            if x.strip().lower() in self._bsa_redirectors)
        if do_redirect == is_bsa_redirection_active:
            return
        if do_redirect and not aii_bsa:
            source = dirs['templates'].join(
                bush.game.template_dir, self._aii_name)
            source.mtime = aiBsaMTime
            try:
                env.shellCopy({source: self.store_dir.join(self._aii_name)},
                    allow_undo=True, auto_rename=True)
            except (PermissionError, CancelError, SkipError):
                return
        # Strip any existing redirectors out, then add our own
        bsa_archs = [x_s for x in sArchives.split(',') if
                     (x_s := x.strip()).lower() not in self._bsa_redirectors]
        if do_redirect:
            bsa_archs.insert(0, self._aii_name)
        sArchives = ', '.join(bsa_archs)
        oblivionIni.saveSetting('Archive', 'sArchiveList', sArchives)

#------------------------------------------------------------------------------
class ScreenInfos(_AFileInfos):
    """Collection of screenshots. This is the backend of the Screenshots
    tab."""
    # Files that go in the main game folder (aka default screenshots folder)
    # and have screenshot extensions, but aren't screenshots and therefore
    # shouldn't be managed here - right now only ENB stuff
    _ss_skips = {FName(s) for s in (
        'enblensmask.png', 'enbpalette.bmp', 'enbsunsprite.bmp',
        'enbsunsprite.tga', 'enbunderwaternoise.bmp')}
    unique_store_key = Store.SCREENSHOTS
    file_pattern = re.compile(
        r'\.(' + '|'.join(ext[1:] for ext in ss_image_exts) + ')$', re.I)
    factory = ScreenInfo

    def set_store_dir(self):
        # Check if we need to adjust the screenshot dir
        ss_base = GPath(oblivionIni.getSetting(
            u'Display', u'SScreenShotBaseName', u'ScreenShot'))
        new_store_dir = dirs['app'].join(ss_base.shead)
        if (prev := getattr(self, 'store_dir', None)) != new_store_dir:
            self.store_dir = new_store_dir
            if prev is not None: # else we are in __init__
                self._init_store(new_store_dir)
            # Also check if we're now in the Data folder and hence need to
            # pay attention to BAIN
            if in_data := self.store_dir.cs.startswith(bass.dirs['mods'].cs):
                self._ci_curr_data_prefix = os.path.split(os.path.relpath(
                    new_store_dir, bass.dirs['mods']).lower())
            else:
                self._ci_curr_data_prefix = []
            self._bain_notify = in_data
        return new_store_dir

    @classmethod
    def rightFileType(cls, fileName: bolt.FName):
        if fileName in cls._ss_skips:
            # Some non-screenshot file, skip it
            return False
        return super().rightFileType(fileName)

    def data_path_to_info(self, data_path: str, would_be=False) -> _ListInf:
        if not self._bain_notify:
            # Current store_dir is not relative to Data folder, so we do not
            # need to pay attention to BAIN
            return None
        *parts, filename = os.path.split(os.fspath(data_path))
        # The parent directories must match
        if (len(parts) != len(self._ci_curr_data_prefix) or
                [*map(str.lower, parts)] != self._ci_curr_data_prefix):
            return None
        return super().data_path_to_info(filename, would_be)

    def refresh(self, refresh_infos=True, booting=False):
        self.set_store_dir()
        return super().refresh(refresh_infos, booting)

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
def initBosh(game_ini_path):
    # Setup loot_parser, needs to be done after the dirs are initialized
    if not initialization.bash_dirs_initialized:
        raise BoltError(u'initBosh: Bash dirs are not initialized')
    # game ini files
    deprint(f'Looking for main game INI at {game_ini_path}')
    global oblivionIni, gameInis
    oblivionIni = GameIni(game_ini_path, 'cp1252')
    gameInis = [oblivionIni, *(IniFileInfo(dirs['saveBase'].join(x), 'cp1252')
                               for x in bush.game.Ini.dropdown_inis[1:])]
    load_order.initialize_load_order_files()
    if os_name != 'nt':
        archives.exe7z = bass.inisettings['Command7z']
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

def init_stores(progress):
    """Initialize the data stores. Bsas first - used in warnTooManyModsBsas
    and modInfos strings detection. Screens/installers data are refreshed
    upon showing the panel - we should probably do the same for saves."""
    global bsaInfos, saveInfos, iniInfos
    progress(0.2, _('Initializing BSAs'))
    bsaInfos = BSAInfos()
    progress(0.3, _('Initializing plugins'))
    ModInfos() # modInfos global is set in __init__
    progress(0.5, _('Initializing saves'))
    saveInfos = SaveInfos()
    progress(0.6, _('Initializing INIs'))
    iniInfos = INIInfos()
    return modInfos
