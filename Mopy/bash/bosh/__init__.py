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
from dataclasses import dataclass
from functools import wraps
from itertools import chain
from typing import final

# bosh-local imports - maybe work towards dropping (some of) these?
from . import bsa_files, converters, cosaves
from .converters import InstallerConverter
from .cosaves import PluggyCosave, xSECosave
from .mods_metadata import get_tags_from_dir, process_tags, read_dir_tags, \
    read_loot_tags
from .save_headers import get_save_header_type
from .. import archives, bass, bolt, bush, env, initialization, load_order
from ..bass import dirs, inisettings, Store
from ..bolt import AFile, AFileInfo, DataDict, FName, FNDict, GPath, \
    ListInfo, Path, RefrIn, deprint, dict_sort, \
    forward_compat_path_to_fn_list, os_name, struct_error, \
    OrderedLowerDict, attrgetter_cache, RefrData
from ..brec import FormIdReadContext, FormIdWriteContext, ModReader, \
    RecordHeader, RemapWriteContext, unpack_header
from ..exception import BoltError, BSAError, CancelError, \
    FailedIniInferError, FileError, ModError, PluginsFullError, SaveFileError, \
    SaveHeaderError, SkipError, SkippedMergeablePluginsError
from ..ini_files import AIniInfo, GameIni, IniFileInfo, OBSEIniFile, \
    get_ini_type_and_encoding, supported_ini_exts
from ..load_order import LordDiff, LoadOrder
from ..mod_files import ModFile, ModHeaderReader
from ..plugin_types import MergeabilityCheck, PluginFlag
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
    are missing a present mod counterpart."""
    __slots__ = ('is_ghost', 'curr_name', 'mod_info', 'old_name',
                 'stored_size', '_was_scale', 'parent_mod_info')

    def __init__(self, *, parent_minf, master_name: FName, master_size,
                 was_scale):
        self.parent_mod_info = parent_minf
        self.stored_size = master_size
        self._was_scale = was_scale
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

    def has_master_size_mismatch(self, do_test): # used in set_item_format
        return _('Stored size does not match the one on disk.') if do_test \
          and modInfos.size_mismatch(self.curr_name, self.stored_size) else ''

    def flag_fallback(self, pflag):
        """For esm missing masters check extension - for scale flags rely on
        cached info."""
        if pflag is bush.game.master_flag:
            return pflag in bush.game.plugin_flags.guess_flags(
                self.get_extension(), bush.game)
        return pflag in self._was_scale # should we use ext heuristics for esl?

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

    @_mod_info_delegate
    def merge_types(self):
        """Ask the mod info or shrug."""
        return set()

    def info_status(self, *, loadOrderIndex, mi):
        if self.mod_info:
            ordered = load_order.cached_active_tuple()
            # current load order of master relative to other masters
            if mi != loadOrderIndex:  # there are active masters out of order
                return 20  # orange
            elif (mi < len(ordered)) and (ordered[mi] == self.curr_name):
                return -10  # Blue else 0, Green
            return 0
        return 30 # 30: does not exist

    def __repr__(self):
        return f'{self.__class__.__name__}<{self.curr_name!r}>'

#------------------------------------------------------------------------------
class _TabledInfo:
    """Stores some of its attributes in a pickled dict. Most of the (hacky)
    internals are for translating the legacy dict keys to proper attr names."""
    _key_to_attr = {}

    def __init__(self, *args, att_val=None, **kwargs):
        for k, v in (att_val or {}).items(): # set table props used in refresh
            try: ##: nightly regression storing 'installer' as FName - drop!
                if k == 'installer': v = str(v)
                elif k == 'doc': # needed for updates from old settings
                    v = GPath(v)
                elif k == 'mergeInfo':
                    # Clean up cached mergeability info - can get out of sync
                    # if we add or remove a mergeability type from a game
                    try:
                        cached_size, canMerge = v
                        canMerge = {mc: v for m, v in canMerge.items() if (
                            (mc := MergeabilityCheck(m))) in
                                    bush.game.mergeability_checks}
                        v = cached_size, canMerge
                    except (TypeError, ValueError, AttributeError):
                        # Convert older settings (had a bool in canMerge)
                        v = -1, {}
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

    def get_persistent_attrs(self, *, exclude=frozenset()):
        if exclude is True: exclude = frozenset()
        return {pickle_key: val for pickle_key in self.__class__._key_to_attr
                if (val := self.get_table_prop(pickle_key)) is not None and
                pickle_key not in exclude}

class FileInfo(_TabledInfo, AFileInfo):
    """Abstract Mod, Save or BSA File. Features a half baked Backup API."""
    _null_stat = (-1, None, None)

    def __init__(self, fullpath, **kwargs):
        self.madeBackup = False
        super().__init__(fullpath, **kwargs)

    def _stat_tuple(self, cached_stat=None):
        return self.abs_path.size_mtime_ctime() if cached_stat is None else (
            cached_stat.st_size, cached_stat.st_mtime, cached_stat.st_ctime)

    def _file_changed(self, stat_tuple):
        return (self.fsize, self.ftime, self.ctime) != stat_tuple

    def _reset_cache(self, stat_tuple, **kwargs):
        self.fsize, self.ftime, self.ctime = stat_tuple

    def setmtime(self, set_time: int | float = 0.0, crc_changed=False):
        """Sets ftime. Defaults to current value (i.e. reset)."""
        set_to = set_time or self.ftime
        self.abs_path.mtime = set_to
        self.ftime = set_to
        return set_to

    # Backup stuff - beta, see #292 -------------------------------------------
    def get_hide_dir(self):
        return self._store().hide_dir

    def makeBackup(self, forceBackup=False):
        """Creates backup(s) of file."""
        #--Skip backup?
        if self not in self._store().values(): return
        if self.madeBackup and not forceBackup: return
        #--Backup
        self.fs_copy(self.backup_restore_paths(False)[0][0])
        #--First backup
        firstBackup = self.backup_restore_paths(True)[0][0]
        if not firstBackup.exists():
            self.fs_copy(firstBackup)
        self.madeBackup = True

    def backup_restore_paths(self, first, fname=None) -> list[tuple[Path, Path]]:
        """Return a list of tuples, mapping backup paths to their restore
        destinations. If fname is not given returns the (first) backup
        filename corresponding to self.abs_path, else the backup filename
        for fname mapped to its restore location in data_store.store_dir."""
        restore_path = (fname and self._store().store_dir.join(
            fname)) or self.abs_path
        fname = fname or self.fn_key
        return [(self._store().bash_dir.join('Backups').join(
            fname + 'f' * first), restore_path)]

    def all_backup_paths(self, fname=None):
        """Return the list of all possible paths a backup operation may create.
        __path does not really matter and is not necessarily correct when fname
        is passed in
        """
        return [backPath for first in (True, False) for backPath, __path in
                self.backup_restore_paths(first, fname)]

    def revert_backup(self, first): # single call site - good
        backup_paths = self.backup_restore_paths(first)
        for tup in backup_paths[1:]: # if cosaves do not exist shellMove fails!
            if not tup[0].exists():
                # if cosave exists while its backup not, delete it on restoring
                tup[1].remove()
                backup_paths.remove(tup)
        env.shellCopy(dict(backup_paths))
        # do not change load order for timestamp games - rest works ok
        self.setmtime(self.ftime)
        # in case the restored file is a BP: refresh below will try to
        # refresh info sets, but we don't back up the config so we can't
        # really detect changes in imported/merged - a (another) backup edge
        # case - as backup is half-baked anyway let's agree for now that BPs
        # remain BPs with the same config as before - if not, manually run a
        # mergeability scan after updating the config
        self._store().refresh(RefrIn.from_tabled_infos(
            {self.fn_key: self}, exclude=True))

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

class _WithMastersInfo(FileInfo):
    """A FileInfo that has masters."""

    def __init__(self, fullpath, **kwargs):
        self.header = None
        self.masterNames: tuple[FName, ...] = ()
        # True if the masters for this file are not reliable
        self.has_inaccurate_masters = False
        #--Ancillary storage
        self.extras = {} # ModInfo only - don't use!
        super().__init__(fullpath, **kwargs)

    def _reset_cache(self, stat_tuple, **kwargs):
        super()._reset_cache(stat_tuple, **kwargs)
        if kwargs.get('load_cache'): self.readHeader()

    def readHeader(self):
        """Read header from file and set self.header attribute."""
        self._reset_masters()

    def _reset_masters(self):
        #--Master Names/Order
        self.masterNames = tuple(self._get_masters())

    def _masters_order_status(self, status):
        raise NotImplementedError

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

    def info_status(self, **kwargs):
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

#------------------------------------------------------------------------------
class ModInfo(_WithMastersInfo):
    """A plugin file. Currently, these are .esp, .esm, .esl and .esu files."""
    # Cached, since we need them so often - set by PluginFlag
    _is_master = _is_esl = _is_overlay = _is_blueprint = _is_mid = False
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

    def __init__(self, fullpath, itsa_ghost=None, **kwargs):
        # list of string bsas sorted by search order for localized plugins -
        # None otherwise
        self.str_bsas_sorted = None
        if itsa_ghost is None:
            if fullpath.cs[-6:] == '.ghost':
                fullpath = fullpath.root
                itsa_ghost = True
            else:
                itsa_ghost = not fullpath.is_file() and os.path.isfile(
                    f'{fullpath}.ghost')
        self.is_ghost = itsa_ghost
        super().__init__(fullpath, **kwargs)

    def get_hide_dir(self):
        dest_dir = self._store().hide_dir
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

    def get_persistent_attrs(self, *, exclude=frozenset()):
        if exclude is True:
            exclude = frozenset([ #'allowGhosting', 'bash.patch.configs',
                'bp_split_parent', # 'doc', 'docEdit', 'group', 'installer',
                # 'rating', 'autoBashTags', 'bashTags', ##: reset bashTags on reverting?
                # ignore mergeInfo/crc cache so we recalculate (resets ignoreDirty - ?)
                'crc', 'crc_mtime', 'crc_size', 'ignoreDirty', 'mergeInfo'])
        return super().get_persistent_attrs(exclude=exclude)

    @classmethod
    def _store(cls): return modInfos

    def get_extension(self):
        """Returns the file extension of this mod."""
        return self.fn_key.fn_ext

    def set_plugin_flags(self, flags_dict: dict[PluginFlag, bool | None],
                         save_flags=True):
        """Set plugin flags. If a flag is None, we initialize the ModInfo
        flag attribute. Do not pass invalid flag values combinations."""
        for pl_flag, flag_val in flags_dict.items():
            pl_flag.set_mod_flag(self, flag_val, bush.game)
            if flag_val is not None and pl_flag is bush.game.master_flag:
                self._update_onam() # recalculate ONAM info if necessary
        if save_flags: self.writeHeader(rescan_merge=True)

    def _scan_fids(self, fid_cond):
        with ModReader.from_info(self) as ins:
            try:
                while not ins.atEnd():
                    next_header = unpack_header(ins)
                    # Skip GRUPs themselves, only process their records
                    if next_header.recType != b'GRUP':
                        if fid_cond(next_header.fid):
                            return True
                        next_header.skip_blob(ins)
            except (OSError, struct_error) as e:
                raise ModError(ins.inName, f"Error scanning {self}, file read "
                    f"pos: {ins.tell():d}\nCaused by: '{e!r}'")
        return False

    def formids_out_of_range(self, pf_name: str):
        """Check if the plugin contains any FormIDs out of the range of
        the named scale flag."""
        num_masters = len(self.masterNames)
        mask = bush.game.plugin_flags[pf_name].fid_mask
        return self._scan_fids(lambda header_fid: header_fid.mod_dex >=
            num_masters and header_fid.object_dex > mask)

    def has_new_records(self):
        """Checks we have any new records."""
        num_masters = len(self.masterNames)
        # Check for NULL to skip the main file header (i.e. TES3/TES4)
        return self._scan_fids(lambda header_fid: header_fid.mod_dex >=
            num_masters and not header_fid.is_null())

    def merge_types(self):
        """Get all merge types for this mod info."""
        return {m for m, m_mergeable in self.get_table_prop('mergeInfo', (
            None, {}))[1].items() if m_mergeable}

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
    def do_update(self, *, itsa_ghost, **kwargs):
        # only call in refresh and always pass itsa_ghost
        old_ghost = self.is_ghost
        self.is_ghost = itsa_ghost
        # mark updated if ghost state changed but only reread header if needed
        did_change = super().do_update(**kwargs)
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
        self._reset_cache((self.fsize, self.ftime, self.ctime))
        # This is necessary if BAIN externally tracked the (un)ghosted file
        self._store()._notify_bain(renamed={ghost_source: ghost_target})
        return True

    #--Bash Tags --------------------------------------------------------------
    def tagsies(self, tagList): ##: join the strings once here
        mname = self.fn_key
        # Tracks if this plugin has at least one bash tags source - which may
        # still result in no tags at the end, e.g. if source A adds a tag and
        # source B removes it
        has_tags_source = False
        def _tags(tags_msg, tags_iter, tagsList):
            tags_result = ', '.join(tags_iter) if tags_iter else _('No tags')
            return f'{tagsList}  * {tags_msg} {tags_result}\n'
        tags_desc = self.getBashTagsDesc()
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
        sorted_tags = sorted(self.getBashTags())
        if not self.is_auto_tagged() and sorted_tags:
            has_tags_source = True
            tagList = _tags(_('From Manual (overrides all other sources):'),
                sorted_tags, tagList)
        return (_tags(_('Result:'), sorted_tags, tagList)
                if has_tags_source else tagList + f"    {_('No tags')}\n")

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
        super().readHeader() # reset masters
        # check if we have a cached crc for this file, use fresh mtime and size
        self.calculate_crc() # for added and hopefully updated
        flags_dict = dict.fromkeys(chain(*bush.game.all_flags)) # values = None
        self.set_plugin_flags(flags_dict, save_flags=False) # set _is_esl etc

    def writeHeader(self, old_masters: list[FName] | None = None, *,
                    rescan_merge=False):
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
        if not rescan_merge and merge_size is not None:
            self.set_table_prop('mergeInfo', (self.abs_path.psize, canMerge))
        else:
            modInfos.rescanMergeable([self.fn_key], sort_descending_lo=False)

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
            if bush.game.master_flag.cached_type(self):
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

    def info_status(self, *, target_ini_settings=None, **kwargs):
        if self._status is None:
            self.getStatus(target_ini_settings=target_ini_settings)
        return self._status

    def _incompatible(self, other):
        if not isinstance(self, OBSEIniFile):
            return isinstance(other, OBSEIniFile)
        return not isinstance(other, OBSEIniFile)

    def is_applicable(self, stat=None):
        stat = stat or self.info_status()
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
        if self._incompatible(target_ini) or not tweak_settings:
            return self.reset_status(-20)
        found_match = False
        mismatch = 0
        ini_settings = target_ini_settings if target_ini_settings is not None \
            else target_ini.get_ci_settings()
        self_installer = FName( # make comparison case insensitive below
            self.get_table_prop(u'installer'))
        for section_key in tweak_settings:
            if section_key not in ini_settings:
                return self.reset_status(-10)
            target_section = ini_settings[section_key]
            tweak_section = tweak_settings[section_key]
            for item in tweak_section:
                if item not in target_section:
                    return self.reset_status(-10)
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
            return self.reset_status(0)
        elif not mismatch:
            return self.reset_status(20)
        elif mismatch == 1:
            return self.reset_status(15)
        elif mismatch == 2:
            return self.reset_status(10)

    def reset_status(self, s=None):
        self._status = s
        return s

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
class SaveInfo(_WithMastersInfo):
    cosave_types = () # cosave types for this game - set once in SaveInfos
    _cosave_ui_string = {PluggyCosave: u'XP', xSECosave: u'XO'} # ui strings
    _valid_exts_re = r'(\.(?:' + '|'.join(
        [bush.game.Ess.ext[1:], bush.game.Ess.ext[1:-1] + 'r', 'bak']) + '))'
    _key_to_attr = {'info': 'save_notes'}
    _co_saves: _CosaveDict

    def __init__(self, fullpath, **kwargs):
        # Dict of cosaves that may come with this save file. Need to get this
        # first, since readHeader calls _get_masters, which relies on the
        # cosave for SSE and FO4
        self._co_saves = self.get_cosaves_for_path(fullpath)
        super().__init__(fullpath, **kwargs)

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
        super().readHeader()

    def do_update(self, **kwargs):
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
        return super().do_update(**kwargs) or cosaves_changed

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
            self.has_inaccurate_masters = any(self.header.scale_masters.values(
                )) and ((xse_cosave := self.get_xse_cosave()) is None or not
            xse_cosave.has_accurate_master_list())
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

    def __init__(self, fullpath, **kwargs):
        super().__init__(fullpath, **kwargs)
        self.cached_bitmap = None

    def _reset_cache(self, stat_tuple, **kwargs):
        self.cached_bitmap = None # Lazily reloaded
        super()._reset_cache(stat_tuple, **kwargs)

    @classmethod
    def _store(cls): return screen_infos

    def validate_name(self, name_str, check_store=True):
        file_root, num_str = super().validate_name(name_str, check_store)
        return (file_root, num_str) if num_str is None else (
            FName(file_root + num_str + self.fn_key.fn_ext), '')

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
    def refresh(self, refresh_infos: RefrIn | list[FName] | bool = True,
                **kwargs): raise NotImplementedError

    @final
    def delete(self, delete_keys, *, recycle=True):
        """Deletes member file(s)."""
        # factory is _AFileInfos only, but installers don't have corrupted so
        # let it blow if we are called with non-existing keys(join(None), boom)
        finfos = [v or self.factory(self.store_dir.join(k)) for k, v in
                  self.filter_essential(delete_keys).items()]
        try:
            self._delete_operation(finfos, recycle)
        finally: # markers are popped from finfos - we refreshed in _delete_op
            if finfos := self.check_removed(finfos):
                # ok to suppose the only lo modification is due to deleted
                # files at this point
                self.refresh(RefrIn(del_infos=finfos), what='I',
                             unlock_lo=True)

    def _delete_operation(self, finfos: list, recycle):
        if abs_del_paths := [
                *chain.from_iterable(inf.delete_paths() for inf in finfos)]:
            env.shellDelete(abs_del_paths, recycle=recycle)

    def check_removed(self, infos):
        """Lift your skirts, we are entering the realm of #241."""
        return {inf for inf in infos if not inf.abs_path.exists()}

    def rename_operation(self, member_info, newName, store_refr=None):
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
        member_info.fn_key = newName = FName(newName)
        #--FileInfo
        self[newName] = member_info
        member_info.abs_path = self.store_dir.join(newName)
        del self[old_key]
        return RefrData({newName}, to_del={old_key},
                        renames={old_key: newName}, ren_paths=ren)

    def filter_essential(self, fn_items: Iterable[FName]):
        """Filters essential files out of the specified filenames. Returns the
        remaining ones as a dict, mapping file names to file infos. Useful to
        determine whether a file will cause instability when deleted/hidden."""
        return {k: self.get(k) for k in fn_items}

    def filter_unopenable(self, fn_items: Iterable[FName]):
        """Filter unopenable files out of the specified filenames. Returns the
        remaining ones as a dict, mapping file names to file infos."""
        return {k: self[k] for k in fn_items}

    @property
    def bash_dir(self) -> Path:
        """Return the folder where Bash persists its data.Create it on init!"""
        raise NotImplementedError

    @property
    def hide_dir(self) -> Path:
        """Return the folder where Bash should move the file info to hide it"""
        return self.bash_dir.join(u'Hidden')

    def move_infos(self, sources, destinations, window):
        """Hasty hack for Files_Unhide - only use on files, not folders!"""
        try:
            env.shellMove(dict(zip(sources, destinations)), parent=window)
        except (CancelError, SkipError):
            pass
        return forward_compat_path_to_fn_list(
            {d.stail for d in destinations if d.exists()}, ret_type=set)

    def save_pickle(self): pass # for Screenshots

    def warning_args(self, multi_warnings, lo_warnings, link_frame, store_key):
        """Append the arguments for the warning message to the multi_warnings
        and lo_warnings lists, checking the caches currently in Link.Frame."""

class _AFileInfos(DataStore):
    """File data stores - all of them except InstallersData."""
    _bain_notify = True # notify BAIN on deletions/updates ?
    file_pattern = None # subclasses must define this !
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
        self.corrupted: FNDict[FName, _Corrupted] = FNDict()
        deprint(f'Initializing {self.__class__.__name__}')
        deprint(f' store_dir: {storedir}')
        storedir.makedirs()
        self._data = FNDict()
        return self._data

    #--Refresh
    def refresh(self, refresh_infos: bool | RefrIn = True, *, booting=False,
                **kwargs):
        """Refresh from file directory."""
        try:
            new_or_present, delinfos = (refresh_infos.new_or_present,
                                        refresh_infos.del_infos)
        except AttributeError:
            new_or_present, delinfos = self._list_store_dir() \
                if refresh_infos else ({}, set())
        rdata = RefrData() # create the return value instance then scan changes
        for new, (oldInfo, kws) in new_or_present.items():
            try:
                if oldInfo is not None:
                    # reread the header if any file attributes changed
                    if oldInfo.do_update(**kws):
                        rdata.redraw.add(new)
                else: # new file or updated corrupted, get a new info
                    self[new] = self.factory(self.store_dir.join(new),
                        load_cache=True, **kws)
                    self.corrupted.pop(new, None)
                    rdata.to_add.add(new)
            except (FileError, UnicodeError, BoltError,
                    NotImplementedError) as e:
                # old still corrupted, or new(ly) corrupted or we landed
                # here cause cor_path was manually un/ghosted but file remained
                # corrupted so in any case re-add to corrupted
                cor_path = self.store_dir.join(new)
                if del_inf := self.pop(new, None): # effectively deleted
                    delinfos.add(del_inf)
                    cor_path = del_inf.abs_path
                elif self is modInfos: # needs be set here!
                    if (isg := kws.get('itsa_ghost')) is None:
                        isg = not cor_path.is_file() and os.path.isfile(
                            f'{cor_path}.ghost')
                    if isg: cor_path = cor_path + '.ghost' # Path __add__ !
                er = e.message if hasattr(e, 'message') else f'{e}'
                self.corrupted[new] = cor = _Corrupted(cor_path, er, new,**kws)
                deprint(f'Failed to load {new} from {cor.abs_path}: {er}',
                        traceback=True)
        rdata.to_del = {d.fn_key for d in delinfos}
        if delinfos: self._delete_refresh(delinfos)
        if not booting and ((alt := rdata.redraw | rdata.to_add) or delinfos):
            self._notify_bain(altered={self[n].abs_path for n in alt},
                              del_set={inf.abs_path for inf in delinfos})
        return rdata

    def _list_store_dir(self):
        file_matches_store = self.rightFileType
        inodes = FNDict()
        with os.scandir(self.store_dir) as it: # performance intensive
            for x in it:
                try:
                    if x.is_file() and file_matches_store(n := x.name):
                        inodes[n] = {'cached_stat': x.stat()}
                except OSError: # this should not happen - investigating
                    deprint(f'Failed to stat {x.name} in {self.store_dir}',
                            traceback=True)
        return self._diff_dir(inodes)

    def _diff_dir(self, inodes) -> tuple[ # ugh - when dust settles use 3.12
        dict[FName, tuple[AFile | None, dict]], set[ListInfo]]:
        """Return a dict of fn keys (see overrides) of files present in data
        dir and a set of deleted keys."""
        # for modInfos '.ghost' must have been lopped off from inode keys
        delinfos = {inf for inf in [*self.values(), *self.corrupted.values()]
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
        return new_or_present, delinfos

    def _delete_refresh(self, infos):
        """Only called from refresh - should be inlined but for ModInfos.
        :param infos: the infos corresponding to deleted items."""
        del_keys = [inf.fn_key for inf in infos]
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

    def rename_operation(self, member_info, newName, store_refr=None):
        # Override to allow us to notify BAIN if necessary
        rdata_ren = super().rename_operation(member_info, newName)
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

    def refresh(self, refresh_infos=True, **kwargs):
        if not self._table_loaded:
            self._table_loaded = True
            new_or_present, delinfos = self._list_store_dir()
            table = self._init_from_table()
            for fn, (_inf, kws) in new_or_present.items():
                if props := table.get(fn):
                    kws['att_val'] = props
            refresh_infos = RefrIn(new_or_present, delinfos)
        return super().refresh(refresh_infos, **kwargs)

    def save_pickle(self):
        pd = bolt.DataTable(self.bash_dir.join('Table.dat')) # don't load!
        for k, v in self.items():
            if pickle_dict := v.get_persistent_attrs():
                pd.pickled_data[k] = pickle_dict
        pd.save()

class _Corrupted(AFile):
    """A 'corrupted' file info. Stores the exception message. Not displayed."""

    def __init__(self, fullpath, error_message, cor_key, **kwargs):
        self.fn_key = cor_key
        super().__init__(fullpath, **kwargs)
        self.error_message = error_message

#------------------------------------------------------------------------------
class INIInfo(IniFileInfo, AINIInfo):
    _valid_exts_re = r'(\.(?:' + '|'.join(
        x[1:] for x in supported_ini_exts) + '))'

    def _reset_cache(self, stat_tuple, **kwargs):
        super()._reset_cache(stat_tuple, **kwargs)
        self.reset_status()

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
    :param kwargs: Cached ghost status information, ignored for INIs"""
    inferred_ini_type, detected_encoding = get_ini_type_and_encoding(fullpath,
        consider_obse_inis=bush.game.Ini.has_obse_inis)
    ini_info_type = (ObseIniInfo if inferred_ini_type == OBSEIniFile
                     else INIInfo)
    return ini_info_type(fullpath, detected_encoding)

class INIInfos(TableFileInfos):
    file_pattern = re.compile('|'.join(
        f'\\{x}' for x in supported_ini_exts) + '$' , re.I)
    unique_store_key = Store.INIS
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
            # If user started with non-translated, 'Browse…'
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
            bass.settings['bash.ini.choice']] # set self.redraw_target = True

    def refresh(self, refresh_infos=True, *, booting=False,
                refresh_target=True, **kwargs):
        rdata = super().refresh(refresh_infos, booting=booting)
        # re-add default tweaks (booting / restoring a default over copy,
        # delete should take care of this but needs to update redraw...)
        for k, default_info in ((k1, v) for k1, v in
                self._default_tweaks.items() if k1 not in self):
            self[k] = default_info  # type: DefaultIniInfo
            if k in rdata.to_del:  # we restore default over copy
                rdata.redraw.add(k)
                default_info.reset_status()
            else: # booting
                rdata.to_add.add(k)
        if refresh_target and ((targ := self.ini).updated or targ.do_update()):
            # reset the status of all infos and let RefreshUI set it
            targ.updated = False
            rdata |= self._reset_all_statuses()
        return rdata

    def _reset_all_statuses(self):
        updt = {ini_info.reset_status() or ini_info.fn_key for ini_info in
                self.values()} ##:(701) only return infos that changed status
        self.redraw_target = True # we are called on target update - msg the UI
        return RefrData(updt)

    def check_removed(self, infos):
        regular_tweaks = []
        def_tweaks = {inf for inf in infos if inf.fn_key in
                      self._default_tweaks or regular_tweaks.append(inf)}
        return {*def_tweaks, *super().check_removed(regular_tweaks)}

    def filter_essential(self, fn_items: Iterable[FName]):
        # Can't remove default tweaks
        return {k: v for k in fn_items if # return None for corrupted
                not (v := self.get(k)) or not v.is_default_tweak}

    def filter_unopenable(self, fn_items: Iterable[FName]):
        # Can't open default tweaks, they are entirely virtual
        return self.filter_essential(fn_items)

    @property
    def bash_dir(self): return dirs[u'modsBash'].join(u'INI Data')

    # _AFileInfos overrides ---------------------------------------------------
    def _diff_dir(self, inodes):
        old_ini_infos = {*(v for v in self.values() if not v.is_default_tweak),
                         *self.corrupted.values()}
        new_or_present, delinfos = super()._diff_dir(inodes)
        # if iinf is a default tweak a file has replaced it - set it to None
        new_or_present = {k: (inf and (None if inf.is_default_tweak else inf),
            kws) for k, (inf, kws) in new_or_present.items()}
        return new_or_present, delinfos & old_ini_infos # drop default tweaks

    def data_path_to_info(self, data_path: str, would_be=False) -> _ListInf:
        parts = os.path.split(os.fspath(data_path))
        # 1. Must have a single parent folder
        # 2. That folder must be named 'ini tweaks' (case-insensitively)
        # 3. The extension must be a valid INI-like extension - super checks it
        if len(parts) == 2 and parts[0].lower() == 'ini tweaks':
            return super().data_path_to_info(parts[1], would_be)
        return None

    # Target INI handling -----------------------------------------------------
    @property
    def ini(self):
        return self._ini

    @ini.setter
    def ini(self, ini_path):
        """:type ini_path: bolt.Path"""
        if self._ini is not None and self._ini.abs_path == ini_path:
            return # nothing to do
        self._ini = BestIniFile(ini_path)
        self._reset_all_statuses()

    @staticmethod
    def update_targets(targets):
        """Update 'bash.ini.choices' with new inis in targets dictionnary,
        then re-sort the dict of target INIs."""
        inis = bass.settings['bash.ini.choices']
        if targets := {k: v for k, v in targets.items() if k not in inis}:
            inis.update(targets)
            INIInfos.__sort_target_inis()
        return targets

    @staticmethod
    def __sort_target_inis():
        # Sort non-game INIs alphabetically
        keys = sorted(bass.settings[u'bash.ini.choices'])
        # Sort game INIs to the top, and 'Browse…' to the bottom
        game_inis = bush.game.Ini.dropdown_inis
        len_inis = len(game_inis)
        keys.sort(key=lambda a: game_inis.index(a) if a in game_inis else (
                      len_inis + 1 if a == _('Browse…') else len_inis))
        bass.settings[u'bash.ini.choices'] = OrderedDict(
            # convert stray Path instances back to unicode
            [(f'{k}', bass.settings['bash.ini.choices'][k]) for k in keys])

    def get_tweak_lines_infos(self, tweakPath):
        return self._ini.analyse_tweak(self[tweakPath])

    def copy_to_new_tweak(self, info, fn_new_tweak: FName):
        """Duplicate tweak into fn_new_teak."""
        with open(self.store_dir.join(fn_new_tweak), 'wb') as ini_file:
            ini_file.write(info.read_ini_content(as_unicode=False)) # binary
        self.refresh(RefrIn.from_added([fn_new_tweak]))
        return self[fn_new_tweak]

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
    def _modinfos_cache_wrapper(self: ModInfos, *args, ldiff=None,
                                **kwargs) -> RefrData:
        """Sync the ModInfos load order and active caches and refresh for
        load order or active changes."""
        try:
            ldiff = LordDiff() if ldiff is None else ldiff
            ldiff |= lord_func(self, *args, **kwargs)
            if ldiff.inact_changes_only():
                return ldiff.to_rdata()
            # Update all data structures that may be affected by LO change
            ldiff.affected |= self._refresh_mod_inis_and_strings()
            ldiff.affected |= self._file_or_active_updates()
            # unghost new active plugins and ghost new inactive (if autoGhost)
            ghostify = dict.fromkeys(ldiff.new_act, False)
            if bass.settings['bash.mods.autoGhost']: # new mods, ghost
                new_inactive = ldiff.new_inact | (ldiff.added - ldiff.new_act)
                ghostify.update({k: True for k in new_inactive if
                    self[k].get_table_prop('allowGhosting', True)})
            ldiff.affected.update(mod for mod, modGhost in ghostify.items()
                                  if self[mod].setGhost(modGhost))
            return ldiff.to_rdata()
        finally:
            self._lo_wip = list(load_order.cached_lo_tuple())
            self._active_wip = list(load_order.cached_active_tuple())
    return _modinfos_cache_wrapper

def _lo_op(lop_func):
    """Decorator centralizing saving active state/load order changes."""
    @wraps(lop_func)
    def _lo_wip_wrapper(self: ModInfos, *args, ldiff=None, save_all=False,
                        save_wip_lo=False, save_act=False, **kwargs):
        """Update _active_wip/_lo_wip cache and possibly save changes.
        :param save_all: save load order and plugins.txt
        :param save_wip_lo: save load order when active did not change
        :param save_act: save plugins.txt - always call with a valid load order
        """
        out_diff = kwargs.setdefault('out_diff', LordDiff())
        ldiff = LordDiff() if ldiff is None else ldiff
        save = sum((save_act, save_wip_lo, save_all))
        if save > 1:
            raise ValueError(f'{save_act=}/{save_wip_lo=}/{save_all=}')
        lo_msg = None
        try:
            lo_msg = lop_func(self, *args, **kwargs)
        finally:
            if save:
                out_diff = self._wip_lo_save(save_wip_lo or save_all,
                    save_act or save_all, ldiff=ldiff) if out_diff else \
                        out_diff.to_rdata() # should be empty
            return out_diff if lo_msg is None else (lo_msg, out_diff)
    return _lo_wip_wrapper

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

    # Refresh - not quite surprisingly this is super complex - therefore define
    # refresh satellite methods before even defining the DataStore overrides
    def refresh(self, refresh_infos=True, *, booting=False, unlock_lo=False,
                insert_after: FNDict[FName, FName] | None = None, **kwargs):
        """Update file data for additions, removals and date changes.
        See usages for how to use the refresh_infos and unlock_lo params.
        NB: if an operation *we* performed changed the load order we do not
        want lock load order to revert our own operation. So either call
        some of the set_load_order methods, or pass unlock_lo=True
        (refreshLoadOrder only *gets* load order)."""
        # Scan the data dir, getting info on added, deleted and modified files
        rdata = super().refresh(refresh_infos, booting=booting)
        mods_changes = bool(rdata)
        self._refresh_bash_tags()
        ldiff = LordDiff()
        if insert_after:
            lordata = self._lo_insert_after(insert_after, save_wip_lo=True,
                                            ldiff=ldiff)
        else: # if refresh_infos is False but mods are added force refresh
            lordata = self.refreshLoadOrder(ldiff=ldiff,
                forceRefresh=mods_changes or unlock_lo,
                forceActive=bool(rdata.to_del), unlock_lo=unlock_lo)
            if not unlock_lo and ldiff.missing: # unlock_lo=True in delete/BAIN
                self.warn_missing_lo_act.update(ldiff.missing)
        rdata |= lordata
        # if active did not change, we must perform the refreshes below
        if ldiff.inact_changes_only():
            # in case ini files were deleted or modified or maybe string files
            # were deleted... we need a load order below: in skyrim we read
            # inis in active order - we then need to redraw what changed status
            rdata.redraw |= self._refresh_mod_inis_and_strings()
            if mods_changes:
                rdata.redraw |= self._file_or_active_updates()
        self._voAvailable, self.voCurrent = bush.game.modding_esms(self)
        return rdata

    # _AFileInfos overrides that are used in refresh - ghosts ahead
    def _delete_refresh(self, infos):
        del_keys = super()._delete_refresh(infos)
        # we need to call deactivate to deactivate dependents - refresh handles
        # saving the load order - can't do in delete_op (due to check_exists)
        self.lo_deactivate(*del_keys) # no-op if empty
        return del_keys

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

    def _file_or_active_updates(self):
        """If any plugins have been added, updated or deleted, or the active
        order/status changed we need to recalculate cached data structures.
        We could be more granular but the performance is elsewhere plus the
        complexity might not worth it."""
        # Recalculate the dependents cache. See ModInfo.get_dependents
        cached_dependents = self.dependents
        cached_dependents.clear()
        # Refresh which filenames cannot be saved to plugins.txt. It seems
        # that Skyrim and Oblivion read plugins.txt as a cp1252 encoded file,
        # and any filename that doesn't decode to cp1252 will be skipped
        old_bad, self.bad_names = self.bad_names, set()
        old_ab, self.activeBad = self.activeBad, set()
        # Refresh bashed_patches/imported/merged - active state changes and/or
        # removal/addition of plugins should trigger a refresh
        bps, self.bashed_patches = self.bashed_patches, set()
        active_patches = set()
        # Refresh set of mergeable mods
        rescan_mods = [] # Mods that need to be rescanned for mergeability
        full_checks = bush.game.mergeability_checks
        quick_checks = {mc: pflag.cached_type for pflag in
            bush.game.plugin_flags if (mc := pflag.merge_check) in full_checks}
        all_checks = len(full_checks)
        changed = set()
        # We need to scan dependent mods first to account for mergeability of
        # their masters
        for fn_mod, modInfo in dict_sort(self, reverse=True,
                                         key_f=load_order.cached_lo_index):
            for p_master in modInfo.masterNames:
                cached_dependents[p_master].add(fn_mod)
            isact = load_order.cached_is_active(fn_mod)
            if modInfo.isBP():
                self.bashed_patches.add(fn_mod)
                if isact: active_patches.add(fn_mod)
            if self.isBadFileName(fn_mod):
                if isact:
                    ##: For now, we'll leave them active, until we finish
                    # testing what the game will support
                    #self.lo_deactivate(fn_mod)
                    self.activeBad.add(fn_mod)
                else:
                    self.bad_names.add(fn_mod)
            cached_size, canMerge = modInfo.get_table_prop('mergeInfo',
                                                           (None, {}))
            # Quickly check if some mergeability types are impossible for this
            # plugin (because it already has the target type)
            new_checks = {m: False for m, m_check in quick_checks.items() if
                          m_check(modInfo)}
            # If ve already covered all required checks with the quick checks
            # above (e.g. an ESL-flagged plugin in a game with only ESL
            # support -> not ESL-flaggable), or the cached size matches what we
            # have on disk, and we have data for all required mergeability
            # checks, we can cache the info
            if len(new_checks) == all_checks or (len(canMerge) == all_checks
                    and cached_size == modInfo.fsize):
                if canMerge != (canMerge := canMerge | new_checks):
                    changed.add(fn_mod)
                modInfo.set_table_prop('mergeInfo', (modInfo.fsize, canMerge))
            else:
                # We have to rescan mergeability - either the plugin's size
                # changed or there is at least one required mergeability check
                # we have not yet run for this plugin
                rescan_mods.append(fn_mod)
        if rescan_mods: ##: maybe re-add progress?
            self.rescanMergeable(rescan_mods, sort_descending_lo=False)
        # Recalculate the real indices cache, which is the index the game will
        # assign to plugins. ESLs will land in the 0xFE spot, while inactive
        # plugins don't get any - so we sort them last. Note that inactive
        # plugins are handled by our defaultdict factory
        old_dexs = self.real_indices
        self.real_indices = bush.game.plugin_flags.get_indexes(
            ((p, self[p]) for p in load_order.cached_active_tuple()))
        mrgd, imprtd = self.merged, self.imported
        self.merged, self.imported = self.getSemiActive(active_patches)
        dex_xor = (k for k, v in self.real_indices.items() ^ old_dexs.items()
            if v[0] != sys.maxsize) # added from defaultdict for inactive mods
        return {plug for plug in chain(dex_xor, changed, rescan_mods,
            self.bashed_patches ^ bps, self.merged ^ mrgd,
            self.imported ^ imprtd, self.activeBad ^ old_ab,
            self.bad_names ^ old_bad) if plug in self}

    def rescanMergeable(self, names, progress=bolt.Progress(),
                        return_results=False, sort_descending_lo=True):
        """Rescan specified mods. Return value is only meaningful when
        return_results is set to True."""
        merge = MergeabilityCheck.MERGE
        full_checks = bush.game.mergeability_checks
        all_reasons = defaultdict(list) if return_results else dict.fromkeys(
            full_checks)
        if sort_descending_lo: # sort in inverted load order for _dependent
            names = sorted(names, key=load_order.cached_lo_index, reverse=True)
        with progress:
            progress.setFull(max(len(names),1))
            result = {}
            for i, fileName in enumerate(names):
                progress(i, fileName)
                fileInfo = self[fileName]
                check_results = {}
                for merg_type, merg_check in full_checks.items():
                    try:
                        check_results[merg_type] = merg_check(fileInfo, self,
                            all_reasons[merg_type], bush.game)
                    except Exception:  # as e
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
                    all_reasons = defaultdict(list)
                fileInfo.set_table_prop('mergeInfo',
                                        (fileInfo.fsize, check_results))
            return result

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
        return {m for m in self.missing_strings ^ oldBad if m in self}

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

    def getSemiActive(self, patches):
        """Return (merged,imported) mods made semi-active by Bashed Patch.

        If no bashed patches are present in 'patches' then return empty sets.
        Else for each bashed patch use its config (if present) to find mods
        it merges or imports.

        :param patches: A set of mods to look for bashed patches in."""
        merged_,imported_ = set(),set()
        for patch in patches & self.bashed_patches: # this must be up to date!
            patchConfigs = self[patch].get_table_prop('bash.patch.configs')
            if not patchConfigs: continue
            mod_sets = [(imported_, patchConfigs.get('ImportedMods', []))]
            if (merger_conf := patchConfigs.get('PatchMerger', {})).get(
                    u'isEnabled'):
                config_checked = (modName for modName, is_merged in
                    merger_conf['configChecks'].items() if is_merged)
                mod_sets.append((merged_, config_checked))
            for mod_set, bp_mods in mod_sets:
                mod_set.update(fn for fn in forward_compat_path_to_fn_list(
                    bp_mods) if fn in self)
        return merged_,imported_

    # Rest of DataStore overrides ---------------------------------------------
    def rename_operation(self, member_info, newName, store_refr=None):
        """Renames member file from oldName to newName."""
        isSelected = load_order.cached_is_active(member_info.fn_key)
        if isSelected:
            self.lo_deactivate(member_info.fn_key)
        rdata_ren = super().rename_operation(member_info, newName)
        # rename in load order caches
        self._lo_move_mod(old_key := next(iter(rdata_ren.renames)),
                          FName(newName), isSelected, save_all=True)
        # Update linked BP parts if the parent BP got renamed
        for mod_inf in self.values():
            if mod_inf.get_table_prop('bp_split_parent') == old_key:
                mod_inf.set_table_prop('bp_split_parent', str(newName))
        return rdata_ren

    def filter_essential(self, fn_items: Iterable[FName]):
        # Removing the game master breaks everything, for obvious reasons
        return {k: self.get(k) for k in fn_items if k != self._master_esm}

    def move_infos(self, sources, destinations, window):
        moved = super().move_infos(sources, destinations, window)
        self.refresh(RefrIn.from_added(moved))
        return moved

    @property
    def bash_dir(self): return dirs[u'modsBash']

    def warning_args(self, multi_warnings, lo_warnings, link_frame, store_key):
        corruptMods = set(self.corrupted)
        if new_cor := corruptMods - link_frame.knownCorrupted:
            multi_warnings.append(
                (_('The following plugins could not be read. This most likely '
                   'means that they are corrupt.'), new_cor, store_key))
            link_frame.knownCorrupted |= corruptMods
        valid_vers = bush.game.Esp.validHeaderVersions
        invalidVersions = {ck for ck, x in self.items() if
                           all(x.header.version != v for v in valid_vers)}
        if new_inv := invalidVersions - link_frame.known_invalid_versions:
            multi_warnings.append(
                (_('The following plugins have header versions that are not '
                   'valid for this game. This may mean that they are '
                   'actually intended to be used for a different game.'),
                 new_inv, store_key))
            link_frame.known_invalid_versions |= invalidVersions
        old_fvers = self.older_form_versions
        if new_old_fvers := old_fvers - link_frame.known_older_form_versions:
            multi_warnings.append(
                (_('The following plugins use an older Form Version for their '
                   'main header. This most likely means that they were not '
                   'ported properly (if at all).'), new_old_fvers, store_key))
            link_frame.known_older_form_versions |= old_fvers
        if self.new_missing_strings:
            multi_warnings.append(
                (_('The following plugins are marked as localized, but are '
                   'missing strings localization files in the language your '
                   'game is set to. This will cause CTDs if they are '
                   'activated.'), self.new_missing_strings, store_key))
            self.new_missing_strings = set()
        if self.warn_missing_lo_act:
            lo_warnings.append((_('The following plugins could not be found '
                    'in the %(data_folder)s folder or are corrupt and have '
                    'thus been removed from the load order.') % {
                                    'data_folder': bush.game.mods_dir, },
                                self.warn_missing_lo_act))
            self.warn_missing_lo_act = set()
        if self.selectedExtra:
            lo_warnings.append(
                (bush.game.plugin_flags.deactivate_msg(), self.selectedExtra))
            self.selectedExtra = set()
        ##: Disable this message for now, until we're done testing if we can
        # get the game to load these files
        # if self.activeBad:
        #     lo_warnings.append(mk_warning(
        #         _('The following plugins have been deactivated because they '
        #           'have filenames that cannot be encoded in Windows-1252 and '
        #           'thus cannot be loaded by %(game_name)s.') % {
        #             'game_name': bush.game.display_name, }, self.activeBad))
        #     self.activeBad = set()

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
    def _wip_lo_save(self, update_lo, update_act):
        """Save load order and plugins.txt"""
        lo = act_key = None # if these remain both None, save_lo will raise
        if update_lo:
            lo = self._lo_wip
            if update_act: # order active wip in the new load order
                act_key = {x: i for i, x in enumerate(lo)}.__getitem__
        elif update_act:
            act_key = load_order.cached_lo_index
        if update_act:
            self._active_wip.sort(key=act_key)
        return load_order.save_lo(lo, self._active_wip if update_act else None)

    @_lo_cache
    def wip_lo_undo_redo_load_order(self, redo):
        return load_order.undo_redo_load_order(redo)

    #--Lo/active wip caches management ----------------------------------------
    @_lo_op
    def _lo_activate(self, fileName, *, out_diff):
        """Never passed save_***=True - kept it a _lo_op for creating the
        LordDiff() in one place."""
        self._do_activate(fileName, set(self), [], out_diff)

    def _do_activate(self, fileName, _modSet, _children, out_diff):
        # Skip .esu files, those can't be activated
        ##: This .esu handling needs to be centralized - sprinkled all over
        # actives related lo_* methods
        if fileName.fn_ext == '.esu': return
        # Speed up lookups, since they occur for the plugin and all masters
        acti_set = set(self._active_wip)
        if fileName not in acti_set: # else we are called to activate masters
            msg = load_order.check_active_limit([*self._active_wip, fileName],
                                            as_type=str)
            if msg:
                msg = f'{fileName}: Trying to activate more than {msg}'
                raise PluginsFullError(msg)
        if _children:
            if fileName in _children:
                raise BoltError(f'Circular Masters: '
                                f'{" >> ".join((*_children, fileName))}')
        _children = [fileName]
        #--Check for bad masternames:
        #  Disabled for now
        ##if self[fileName].hasBadMasterNames(): return
        #--Select masters
        for master in self[fileName].masterNames:
            # Check that the master is on disk and not already activated
            if master in _modSet and master not in acti_set:
                self._do_activate(master, _modSet, _children, out_diff)
        #--Select in plugins
        if fileName not in acti_set:
            self._active_wip.append(fileName)
            out_diff.new_act.add(fileName) # manipulate out_diff attrs directly

    @_lo_op
    def lo_deactivate(self, *filenames, out_diff):
        """Remove mods and their children from _active_wip."""
        filenames = {*load_order.filter_pinned(filenames, filter_mods=True)}
        old = set(self._active_wip)
        diff = old - filenames
        if len(diff) == len(old): return
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
        out_diff.new_inact.update(old - set_awip) # manipulate out_diff attrs

    @_lo_op
    def lo_toggle_active(self, mods, *, do_activate=True, out_diff):
        impacted_mods = {}
        _lo_meth, attr = (self._lo_activate, 'new_act') if do_activate \
            else (self.lo_deactivate, 'new_inact')
        modified_attr = attrgetter_cache[attr]
        # Track illegal activations/deactivations for the return value
        illegal, act_error = [], None
        for fn_mod in mods:
            if fn_mod in modified_attr(out_diff):
                continue # already activated or deactivated
            ## For now, allow selecting unicode named files, for testing
            ## I'll leave the warning in place, but maybe we can get the
            ## game to load these files
            #if fileName in self.bad_names: return
            try:
                changes_diff = _lo_meth(fn_mod)
            except (BoltError, PluginsFullError) as e: # only for _lo_activate
                act_error = e
                break
            if not changes_diff: # Can't de/activate that mod, track this
                illegal.append(fn_mod)
                continue
            out_diff |= changes_diff
            (impacted := modified_attr(changes_diff)).discard(fn_mod)
            if impacted: # deactivated dependents or activated masters
                impacted_mods[fn_mod] = load_order.get_ordered(impacted)
        return impacted_mods, illegal, act_error

    @_lo_op
    def lo_activate_all(self, *, activate_mergeable=True, out_diff):
        """Activates all non-mergeable plugins (except ones tagged Deactivate),
        then all mergeable plugins (again, except ones tagged Deactivate).
        Raises a PluginsFullError if too many non-mergeable plugins are present
        and a SkippedMergeablePluginsError if too many mergeable plugins are
        present."""
        act_set = set(load_order.cached_active_tuple())
        def _activatable(p):
            """Helper for checking if a plugin should be activated."""
            return (p.fn_ext != '.esu' and p not in act_set
                    and 'Deactivate' not in modInfos[p].getBashTags())
        mergeable = MergeabilityCheck.MERGE.cached_types(modInfos)[0]
        s_plugins = {p: self[p] for p in
                     load_order.get_ordered(filter(_activatable, self))}
        # First, activate non-mergeable plugins not tagged Deactivate
        to_act = [p for p, v in s_plugins.items() if v not in mergeable]
        first_mergeable = len(to_act)
        # Then activate as many of the mergeable plugins as we can
        if mergeable and activate_mergeable:
            to_act.extend(p for p, v in s_plugins.items() if v in mergeable)
        if not to_act: return
        try:
            try:
                for j, p in enumerate(to_act):
                    if p not in out_diff.new_act: # else a delinquent master(?)
                        self._lo_activate(p, out_diff=out_diff)
            except PluginsFullError as e:
                if j >= first_mergeable:
                    raise SkippedMergeablePluginsError from e
                raise
        except BoltError:
            out_diff.new_act.clear() # Don't save, something went wrong
            raise

    @_lo_op
    def lo_activate_exact(self, partial_actives: Iterable[FName], *, out_diff):
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
        to_act = [p for p in ordered_wip if p not in trimmed_plugins]
        out_diff |= self._diff_los(new_act=to_act)
        self._active_wip = to_act
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

    @_lo_op
    def lo_reorder(self, partial_order: list[FName], *, out_diff):
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
        collected_plugins = []
        left_off = 0
        while remaining_plugins:
            for i, curr_plugin in enumerate(self._lo_wip[left_off:]):
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
        out_diff |= self._diff_los(new_lo=filtered_order)
        self._lo_wip = filtered_order
        if excess_plugins:
            return (_('Some plugins could not be found and were skipped:') +
                    '\n* ' + '\n* '.join(excess_plugins))
        return ''

    @_lo_op
    def _lo_move_mod(self, old_name, new_name, do_activate, *,
                     deactivate=False, out_diff):
        """Move new_name to the place of old_name and handle active state."""
        oldIndex = self._lo_wip.index(old_name)
        self._lo_wip[oldIndex] = new_name
        self._active_wip = [x for x in self._active_wip if x != old_name]
        if do_activate:
            self._lo_activate(new_name)
        elif deactivate:
            self.lo_deactivate(new_name)
        # only the truth value of out_diff matters
        out_diff.added, out_diff.missing = {new_name}, {old_name} # inform diff

    @_lo_op
    def lo_insert_at(self, first, modlist, *, out_diff):
        """Call with save_all True (not just save_wip_lo) to avoid bogus LO
        warnings on games that reorder active plugins to match load order."""
        mod_set = set(modlist)
        # Clean out any duplicates left behind, in case we're moving forwards
        # Insert the requested plugins then append the remainder
        lwip = []
        for mod in self._lo_wip:
            if mod == first: lwip.extend(modlist)
            if mod not in mod_set: lwip.append(mod)
        out_diff |= self._diff_los(new_lo=lwip)
        self._lo_wip = lwip

    @_lo_op
    def _lo_insert_after(self, insert_after, *, out_diff): #only use in refresh
        lwip = self._lo_wip.copy()
        for new_mod, previous in insert_after.items():
            new_mod = self[new_mod].fn_key  ##: new_mod is not always an FName
            if new_mod in lwip: lwip.remove(new_mod)  # ...
            dex = lwip.index(previous)
            if not bush.game.using_txt_file:
                t_prev = self[previous].ftime
                if lwip[-1] == previous:  # place it after the last mod
                    new_time = t_prev + 60
                else:
                    # try to put it right before the next mod to avoid resetting
                    # ftimes of all subsequent mods - note (t_prev >= t_next)
                    # might be True at the esm boundary, we could be smarter here
                    t_next = self[lwip[dex + 1]].ftime
                    t_prev += 1  # add one second
                    new_time = t_prev if t_prev < t_next else None
                if new_time is not None:
                    self[new_mod].setmtime(new_time)
            lwip[dex + 1:dex + 1] = [new_mod]
        out_diff |= self._diff_los(new_lo=lwip)
        self._lo_wip = lwip

    @_lo_op
    def lo_drop_items(self, items, *, out_diff):
        lwip = self._lo_wip.copy()
        for firstItem, lastItem, dropItem in items:
            newPos = lwip.index(dropItem)
            if newPos <= 0: continue # disallow taking position 0 (master esm)
            start = lwip.index(firstItem)
            stop = lwip.index(lastItem) + 1 # excluded
            # Can't move the game's master file anywhere else but position 0
            if self._master_esm in lwip[start:stop]: continue
            # List of names to move removed and then reinserted at new position
            toMove = lwip[start:stop]
            del lwip[start:stop]
            lwip[newPos:newPos] = toMove
        out_diff |= self._diff_los(new_lo=lwip)
        self._lo_wip = lwip

    def _diff_los(self, *, new_lo=None, new_act=None):
        new_lord = LoadOrder(self._lo_wip if new_lo is None else new_lo,
                             self._active_wip if new_act is None else new_act)
        return LoadOrder(self._lo_wip, self._active_wip).lo_diff(new_lord)

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
            selected: tuple[FName, ...] = (), *,
            wanted_masters: list[FName] | None = None, dir_path=None,
            author_str='', flags_dict=None) -> ModInfo | None:
        """Create a new plugin.

        :param newName: The name the created plugin will have.
        :param selected: The currently selected after which the plugin will be
            created in the load order. If empty, the new plugin will be placed
            last in the load order. Only relevant if dir_path is unset or
            matches the Data folder.
        :param wanted_masters: The masters the created plugin will have.
        :param dir_path: The directory in which the plugin will be created. If
            None, defaults to the Data folder and a refresh will be triggered.
        :param author_str: set author - marks the created plugin as a Bashed
            Patch or a Dummy master
        :param flags_dict: set plugin flags - incompatible flags will raise an
            InvalidPluginFlagsError."""
        if wanted_masters is None:
            wanted_masters = [self._master_esm]
        newInfo = self.factory((dir_path or self.store_dir).join(newName))
        newFile = ModFile(newInfo)
        newFile.tes4.masters = wanted_masters
        if author_str:
            newFile.tes4.author = author_str
        flags_dict = bush.game.plugin_flags.check_flag_assignments(
            flags_dict or {})
        for pl_flag, flag_val in flags_dict.items():
            pl_flag.set_mod_flag(newFile.tes4.flags1, flag_val, bush.game)
        newFile.safeSave()
        if dir_path is None:
            last_selected = (load_order.get_ordered(selected) if selected
                             else self._lo_wip)[-1]
            new = FNDict([(newName, last_selected)])
            rdata = self.refresh(RefrIn.from_added(new), insert_after=new)
            # if we failed to add this will raise KeyError we 'd want to
            # return the message from corrupted
            return self[rdata.to_add.pop()]

    def generateNextBashedPatch(self, selected_mods):
        """Attempt to create a new bashed patch, numbered from 0 to 9.  If
        a lowered number bashed patch exists, will create the next in the
        sequence."""
        for num in range(10):
            modName = f'Bashed Patch, {num}.esp'
            if modName not in self:
                self.create_new_mod(modName, selected=selected_mods,
                    wanted_masters=[], author_str='BASHED PATCH')
                return FName(modName)
        return None

    def get_bsa_lo(self):
        """Get the load order of all active BSAs. Used from bain, so we
        calculate it JIT using the cached result of get_bsas_from_inis.
        Therefore, self.__bsa_lo is initially populated by bsas loaded from
        the inis, having ±sys.maxsize load order."""
        ##:(701) we do this once till next refresh - not entirely correct,
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

    def getVersion(self, fileName):
        """Check we have a fileInfo for fileName and call get_version on it."""
        return self[fileName].get_version() if fileName in self else ''

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
            tagList = modInfo.tagsies(tagList)
        tagList += u'[/spoiler]'
        return tagList

    def masterWithVersion(self, master_name):
        if master_name == 'Oblivion.esm' and (curr_ver := self.voCurrent):
            master_name += f' [{curr_ver}]'
        return master_name

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
        if swapping_a_ghost: # we need to unghost the master esm
            master_inf.setGhost(False)
        self[move_to].setmtime(new_info_time)
        self._lo_move_mod(copy_from, move_to, is_new_info_active,
            deactivate=not is_new_info_active, save_all=True) # always deactivate?
        # make sure to notify BAIN rename_operation passes only renames param
        self._notify_bain(altered={master_inf.abs_path}, del_set={deltd})
        self.voCurrent = set_version
        self._voAvailable.add(curr_ver)
        self._voAvailable.remove(set_version)

    def size_mismatch(self, plugin_name, plugin_size):
        """Checks if the specified plugin exists and, if so, if its size
        does not match the specified value (in bytes)."""
        return plugin_name in self and plugin_size != self[plugin_name].fsize

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

#------------------------------------------------------------------------------
class SaveInfos(TableFileInfos):
    """SaveInfo collection. Represents save directory and related info."""
    _bain_notify = tracks_ownership = False
    # Enabled and disabled saves, no .bak files ##: needed?
    file_pattern = re.compile('(%s)(f?)$' % '|'.join(fr'\.{s}' for s in
        [bush.game.Ess.ext[1:], bush.game.Ess.ext[1:-1] + 'r']), re.I)
    unique_store_key = Store.SAVES

    def __init__(self):
        SaveInfo.cosave_types = cosaves.get_cosave_types(
            bush.game.fsName, self._parse_save_path,
            bush.game.Se.cosave_tag, bush.game.Se.cosave_ext)
        super().__init__(SaveInfo)
        # Save Profiles database
        self.profiles = bolt.PickleDict(
            dirs['saveBase'].join('BashProfiles.dat'), load_pickle=True)
        # save profiles used to have a trailing slash, remove it if present
        for row in [r for r in self.profiles.pickled_data if r.endswith('\\')]:
            self.rename_profile(row, row[:-1])

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

    def warning_args(self, multi_warnings, lo_warnings, link_frame, store_key):
        corruptSaves = set(self.corrupted)
        if not corruptSaves <= link_frame.knownCorrupted:
            multi_warnings.append(
                (_('The following save files could not be read. This most '
                   'likely means that they are corrupt.'),
                 corruptSaves - link_frame.knownCorrupted, store_key))
            link_frame.knownCorrupted |= corruptSaves

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

    def refresh(self, refresh_infos=True, *, booting=False, save_dir=None,
                do_swap=None, **kwargs):
        if not booting: # else we just called __init__
            self.set_store_dir(save_dir, do_swap)
        return super().refresh(refresh_infos, booting=booting, **kwargs)

    def rename_operation(self, member_info, newName, store_refr=None):
        """Renames member file from oldName to newName, update also cosave
        instance names."""
        rdata_ren = super().rename_operation(member_info, newName)
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

    def move_infos(self, sources, destinations, window):
        # we should use fs_copy in base method so cosaves are copied - we
        # need to create infos for the hidden files using _store.factory
        moved = super().move_infos(sources, destinations, window)
        for s, d in zip(sources, destinations):
            if FName(d.stail) in moved:
                co_instances = SaveInfo.get_cosaves_for_path(s)
                self.co_copy_or_move(co_instances, d, move_cosave=True)
        self.refresh(RefrIn.from_added(moved))
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
            def __init__(self, fullpath, **kwargs):
                try:
                    super().__init__(fullpath, **kwargs)
                except BSAError as e:
                    raise FileError(GPath(fullpath).tail,
                        f'{e.__class__.__name__}  {e.message}') from e
                self._reset_bsa_mtime()
            _key_to_attr = {'info': 'bsa_notes', 'installer': 'bsa_owner_inst'}

            @classmethod
            def _store(cls): return bsaInfos

            def do_update(self, **kwargs):
                did_change = super().do_update(**kwargs)
                self._reset_bsa_mtime()
                return did_change

            def _reset_cache(self, *args, **kwargs):
                super()._reset_cache(*args, **kwargs)
                self._assets = None

            def _reset_bsa_mtime(self):
                if bush.game.Bsa.allow_reset_timestamps and inisettings[
                    u'ResetBSATimestamps']:
                    default_mtime = bush.game.Bsa.redate_dict[self.fn_key]
                    if self.ftime != default_mtime:
                        self.setmtime(default_mtime)
        super().__init__(BSAInfo)

    def refresh(self, *args, **kwargs):
        rdata = super().refresh(*args, **kwargs)
        for new_bsa_name in rdata.to_add:
            binf = self[new_bsa_name]
            # If the BSA has a mismatched version, schedule a warning
            if bush.game.Bsa.valid_versions: # else skip checks for this game
                if binf.inspect_version() not in bush.game.Bsa.valid_versions:
                    self.mismatched_versions.add(new_bsa_name)
            # For BA2s, check for hash collisions
            if new_bsa_name.fn_ext == '.ba2':
                ba2_entry = self._ba2_hashes[binf.ba2_hash()]
                # Drop the previous collision if it's present, then check if we
                # have a new one
                self.ba2_collisions.discard(' & '.join(sorted(ba2_entry)))
                ba2_entry.add(new_bsa_name)
                if len(ba2_entry) >= 2:
                    self.ba2_collisions.add(' & '.join(sorted(ba2_entry)))
        return rdata

    def warning_args(self, multi_warnings, lo_warnings, link_frame, store_key):
        bsa_mvers = self.mismatched_versions
        if not bsa_mvers <= link_frame.known_mismatched_version_bsas:
            multi_warnings.append(
                (_('The following BSAs have a version different from the one '
                   '%(game_name)s expects. This can lead to CTDs, please '
                   'extract and repack them using the %(ck_name)s-provided '
                   'tool.') % {'game_name': bush.game.display_name,
                               'ck_name': bush.game.Ck.long_name},
                 bsa_mvers - link_frame.known_mismatched_version_bsas,
                 store_key))
            link_frame.known_mismatched_version_bsas |= bsa_mvers
        ba2_colls = self.ba2_collisions
        if not ba2_colls <= link_frame.known_ba2_collisions:
            multi_warnings.append(
                (_('The following BA2s have filenames whose hashes collide, '
                   'which will cause one or more of them to fail to work '
                   'correctly. This should be corrected by the mod authors '
                   'by renaming the files to avoid the collision.'),
                 ba2_colls - link_frame.known_ba2_collisions, store_key))
            link_frame.known_ba2_collisions |= ba2_colls

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

    def refresh(self, refresh_infos=True, *, booting=False, **kwargs):
        self.set_store_dir()
        return super().refresh(refresh_infos, booting=booting)

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
