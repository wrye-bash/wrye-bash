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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2026 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""The data model, complete with initialization functions. Main hierarchies
are the DataStore singletons and bolt.AFile subclasses populating the data
stores. bush.game must be set, to properly instantiate the data stores."""
from __future__ import annotations

import os
import pickle
import re
import sys
import time
from collections import defaultdict, deque, OrderedDict
from collections.abc import Iterable
from functools import wraps, partial
from itertools import chain
from os import DirEntry

# bosh-local imports - maybe work towards dropping (some of) these?
from . import bsa_files, converters, cosaves
from .converters import InstallerConverter
from .cosaves import PluggyCosave, xSECosave, ACosave
from .save_headers import get_save_header_type
from .. import archives, bass, bolt, bush, env, load_order
from ..bass import dirs, inisettings
from ..bolt import AFile, AFileInfo, DataDict, FName, FNDict, GPath, \
    ListInfo, Path, RefrIn, RefrData, SubProgress, deprint, dict_sort, \
    forward_compat_path_to_fn_list, os_name, struct_error, \
    OrderedLowerDict, attrgetter_cache, top_level_files, classproperty
from ..brec import FormIdReadContext, FormIdWriteContext, ModReader, \
    RecordHeader, RemapWriteContext, unpack_header
from ..exception import BoltError, BSAError, CancelError, \
    FailedIniInferError, FileError, ModError, PluginsFullError, \
    SaveFileError, SaveHeaderError, SkipError, SkippedMergeablePluginsError
from ..ini_files import AIniInfo, GameIni, IniFileInfo, OBSEIniFile, \
    get_ini_type_and_encoding
from ..load_order import LordDiff, LoadOrder
from ..loot_parser import LOOTParser
from ..mod_files import ModFile, ModHeaderReader
from ..plugin_types import MergeabilityCheck, PluginFlag, ST_ACTIVE, \
    ST_MERGED, ST_IMPORTED, ST_INACTIVE, active_keys
from ..wbtemp import TempFile

# Singletons, Constants -------------------------------------------------------
_ListInf = AFile | ListInfo | None| FName

#--Singletons
gameInis: tuple[GameIni | IniFileInfo] | None = None
oblivionIni: GameIni | None = None
modInfos: ModInfos | None = None
saveInfos: SaveInfos | None = None
iniInfos: INIInfos | None = None
bsaInfos: BSAInfos | None = None
screen_infos: ScreenInfos | None = None
# LOOT database instance - must be initiliazed after bass.dirs is updated
lootDb: LOOTParser | None = None

def data_tracking_stores() -> Iterable['_AFileInfos']:
    """Return an iterable containing all data stores that keep track of the
    Data folder and so will get refresh calls from BAIN when files get
    installed/changed/uninstalled. If they set _AFileInfos.tracks_ownership to
    True, they will also get ownership updates."""
    return tuple(s for s in (modInfos, iniInfos, bsaInfos, screen_infos) if
                 s is not None and s._bain_notify)

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
ss_image_exts = frozenset([*_common_image_exts, '.tga'])

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
            return bush.game.guess_flags(self.get_extension()).get(pflag, False)
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

    def info_status(self, *, loadOrderIndex, mi, **kwargs):
        if self.mod_info:
            act_st = self.mod_info.act_st
            ordered = load_order.cached_active_tuple()
            # current load order of master relative to other masters
            if mi != loadOrderIndex:  # there are active masters out of order
                return 20, act_st  # orange
            elif (mi < len(ordered)) and (ordered[mi] == self.curr_name):
                return -10, act_st  # Blue else 0, Green
            return 0, act_st
        return 30, ST_INACTIVE # 30: does not exist

    def __repr__(self):
        return f'{self.__class__.__name__}<{self.curr_name!r}>'

# Deprecated/Obsolete Bash Tags -----------------------------------------------
# Tags that have been removed from Wrye Bash and should be dropped from pickle
# files
_removed_tags = {'Merge', 'ScriptContents'}
#734: Indefinite backwards-compatibility aliases for deprecated tags
_tag_aliases = {
    'Actors.Perks.Add': {'NPC.Perks.Add'},
    'Actors.Perks.Change': {'NPC.Perks.Change'},
    'Actors.Perks.Remove': {'NPC.Perks.Remove'},
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

def _process_tags(tag_set: set[str], drop_unknown=True) -> set[str]:
    """Removes obsolete tags from and resolves any tag aliases in the
    specified set of tags. See the comments above for more information. If
    drop_unknown is True, also removes any unknown tags (tags that are not
    currently used, obsolete or aliases)."""
    if not tag_set: return tag_set # fast path - nothing to process
    ret_tags = tag_set.copy()
    ret_tags -= _removed_tags
    for old_tag, replacement_tags in _tag_aliases.items():
        if old_tag in tag_set:
            ret_tags.discard(old_tag)
            ret_tags.update(replacement_tags)
    if drop_unknown:
        ret_tags &= bush.game.allTags
    return ret_tags

def read_loot_tags(mod_info):
    """Wrapper around get_tags_from_loot. See that method for docs."""
    return map(_process_tags, lootDb.get_tags_from_loot(mod_info.fn_key))

# BashTags dir ----------------------------------------------------------------
def read_dir_tags(mod_info, ci_bt_filenames=None):
    """Retrieves a tuple containing a set of added and a set of deleted
    tags from the 'Data/BashTags/PLUGIN_NAME.txt' file, if it is
    present.

    :param mod_info: The plugin info to check the tag file for.
    :param ci_bt_filenames: An optional set containing lower-case
        versions of the names of all files currently present in the BashTags
        directory. If specified, get_tags_from_dir avoids having to stat to
        figure out if the file in question exists.
    :return: A tuple containing two sets of added and deleted tags."""
    removed, added = set(), set()
    # Check if the file even exists first, using the cache if possible
    tag_file: bolt.Path = mod_info.tags_path()
    has_tags = tag_file.is_file() if ci_bt_filenames is None else \
        tag_file.stail.lower() in ci_bt_filenames
    if not has_tags:
        return added, removed
    # BashTags files must be in UTF-8 (or ASCII, obviously)
    with tag_file.open(u'r', encoding=u'utf-8') as ins:
        for tag_line in ins:
            # Strip out comments and skip lines that are empty as a result
            tag_line = tag_line.split(u'#')[0].strip()
            if not tag_line: continue
            for tag_entry in tag_line.split(u','):
                tag_entry = tag_entry.strip()
                # Guard against things (e.g. typos) like 'TagA,,TagB'
                if not tag_entry: continue
                # If it starts with a minus, it's removing a tag
                if tag_entry[0] == u'-':
                    # Guard against a typo like '- C.Water'
                    removed.add(tag_entry[1:].strip())
                else:
                    added.add(tag_entry)
    return *map(_process_tags, (added, removed)),

def save_tags_to_dir(mod_info, plugin_tag_diff): # one use!
    """Accepts the diff of current mod_info tags to what would be applied by
    its description and the LOOT masterlist / userlist and saves the diff to
    Data/BashTags/PLUGIN_NAME.txt.

    :param mod_info: The plugin info to modify the tag file for.
    :param plugin_tag_diff: A tuple of two sets, (added_tags, removed_tags)."""
    bass.dirs['tag_files'].makedirs()
    tag_file = mod_info.tags_path()
    # Calculate the diff and ignore the minus when sorting the result
    tag_diff_add, tag_diff_del = plugin_tag_diff
    processed_diff = sorted(tag_diff_add | {f'-{t}' for t in tag_diff_del},
                            key=lambda t: t[1:] if t[0] == '-' else t)
    # While all our tags are ASCII, the comment at the top can be localized, so
    # use UTF-8
    with tag_file.open('w', encoding='utf-8') as out:
        # Stick a header in there to indicate that it's machine-generated
        # Also print the version, which could be helpful
        out.write(f"# {_('Generated by Wrye Bash %(wb_version)s')}\n" % {
            'wb_version': bass.AppVersion})
        out.write(', '.join(processed_diff) + '\n')

#------------------------------------------------------------------------------
class _TabledInfo:
    """Stores some of its attributes in a pickled dict. Most of the (hacky)
    internals are for translating the legacy dict keys to proper attr names."""
    _key_to_attr = {}

    def __init__(self, *args, att_val=None, exclude=frozenset(),
                 copy_from=None, **kwargs):
        if copy_from: ##:(300) we need to load here - vs InstallersData.factory
            att_val = copy_from.get_persistent_attrs(exclude=exclude)
        for k, v in (att_val or {}).items(): # set table props used in refresh
            try: ##: nightly regression storing 'installer' as FName - convert to fname actually!
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
                elif k == 'bashTags': # don't drop tags from later WB versions
                    v = _process_tags(v, drop_unknown=False)
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

    def setmtime(self, set_time: int | float = 0.0, **kwargs):
        """Sets ftime. Defaults to current value (i.e. reset)."""
        set_to = set_time or self.ftime
        self.abs_path.mtime = self.ftime = set_to
        return set_to

    # Backup stuff - beta, see #292 -------------------------------------------
    def makeBackup(self, forceBackup=False):
        """Creates backup(s) of file."""
        #--Skip backup?
        if self not in self._store().values(): return
        if self.madeBackup and not forceBackup: return
        #--Backup
        self.fs_copy(self.backup_path())
        #--First backup
        firstBackup = self.backup_path(True)
        if not firstBackup.exists():
            self.fs_copy(firstBackup)
        self.madeBackup = True

    def backup_path(self, is_first=False) -> Path:
        return self._store().bash_dir.join('Backups',
                                           self.fn_key + 'f' * is_first)

    def get_rename_paths(self, new_name, rename_dir, with_backups):
        old_new_paths = super().get_rename_paths(new_name, rename_dir,
                                                 with_backups)
        if with_backups:
            # map the backup paths for this file and its satellites (like
            # cosaves) to their rename destinations. Backup paths may not exist
            bk_dir = self.backup_path().head
            for fir in ('f', ''): # first backup and regular backup
                # get the backup paths for current and new names and pair them
                fn_to_new = (self.get_rename_paths(FName(f), bk_dir, False)
                             for f in (self.fn_key + fir, new_name + fir))
                old_new_paths.extend((a[1], b[1]) for a, b in zip(*fn_to_new))
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
        self.master_st = None # the status of the masters, cached
        super().__init__(fullpath, **kwargs)

    def _reset_cache(self, stat_tuple, *, load_cache=False, **kwargs):
        super()._reset_cache(stat_tuple, **kwargs)
        if load_cache: self.readHeader()

    def readHeader(self):
        """Read header from file and set self.header attribute."""
        self._reset_masters()

    def _reset_masters(self):
        #--Master Names/Order
        self.masterNames = tuple(self._get_masters())

    def _masters_order_status(self):
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

    def info_status(self, *, recalc_st=False, **kwargs):
        """Returns status of this file -- which depends on status of masters:
            - 30: Missing master(s)."""
        #--Missing files? (if self.masterNames is empty any() returns False)
        if recalc_st or self.master_st is None:
            self.master_st = 30 if any((m not in modInfos)
                for m in self.masterNames) else self._masters_order_status()
        return self.master_st

#------------------------------------------------------------------------------
class ModInfo(_WithMastersInfo):
    """A plugin file. Currently, these are .esp, .esm, .esl and .esu files."""
    # Cached, since we need them so often - set by PluginFlag
    _is_master = _is_esl = _is_overlay = _is_blueprint = _is_mid = False
    _key_to_attr = {'allowGhosting': 'mod_allow_ghosting',
        'autoBashTags': 'mod_auto_bash_tags', # this one is actually used
        'bash.patch.configs': 'mod_bp_config', 'bashTags': 'mod_bash_tags',
        'bp_split_parent': 'mod_bp_split_parent', 'crc': 'mod_crc',
        'crc_mtime': 'mod_crc_mtime', 'crc_size': 'mod_crc_size',
        'doc': 'mod_doc', 'docEdit': 'mod_editing_doc', 'group': 'mod_group',
        'ignoreDirty': 'mod_ignore_dirty', 'installer': 'mod_owner_inst',
        'mergeInfo': 'mod_merge_info', 'rating': 'mod_rating'}
    mod_auto_bash_tags: bool # autoBashTags - always set on __init__
    # we need to notify RUI to redraw redated infos without calling do_update
    redated = False
    file_exts = frozenset(bush.game.espm_extensions)

    def __init__(self, fullpath, *, itsa_ghost=None, bt_contents=None,
                 load_cache=False, **kwargs):
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
        self.act_st = None # cache active/merged/imported/inactive status
        super().__init__(fullpath, load_cache=load_cache, **kwargs)
        if (auto := self.get_table_prop('autoBashTags')) is None:
            # For a new mod with no tags, set auto tags to True (default)
            # else set it to False
            auto = self.get_table_prop('bashTags') is None
        if auto and load_cache: # we need to access the header to load the tags
            self.set_auto_tagged(auto, bt_contents) # sets mod_auto_bash_tags
        else: # if auto is True we don't load the tags - call do_update to load
            self.mod_auto_bash_tags = auto

    def do_update(self, *, itsa_ghost, bt_contents=None, **kwargs):
        # only call in refresh and always pass itsa_ghost
        old_ghost = self.is_ghost
        self.is_ghost = itsa_ghost
        # mark updated if ghost state changed but only reread header if needed
        did_change = super().do_update(**kwargs)
        if self.mod_auto_bash_tags: # we are only called on refresh (ideally)
            did_change |= self.set_auto_tagged(True, bt_contents)
        return did_change or self.is_ghost != old_ghost

    def get_hide_dir(self):
        hide_d = super().get_hide_dir()
        #--Use author subdirectory instead?
        mod_author = self.header.author
        if mod_author:
            authorDir = hide_d.join(mod_author)
            if authorDir.is_dir():
                return authorDir
        #--Use group subdirectory instead?
        file_group = self.get_table_prop(u'group')
        if file_group:
            groupDir = hide_d.join(file_group)
            if groupDir.is_dir():
                return groupDir
        return hide_d

    def get_persistent_attrs(self, *, exclude=frozenset()):
        if exclude is True:
            exclude = frozenset([ #'allowGhosting', 'bash.patch.configs',
                # 'doc', 'docEdit', 'group', 'installer', 'rating',
                'bp_split_parent', # 'autoBashTags', 'bashTags',
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
                self._update_onam(pl_flag) # recalculate ONAM info if necessary
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

    def setmtime(self, set_time: int | float = 0.0, *, crc_changed=False,
                 mark_redated=False):
        """Set ftime and if crc_changed is True recalculate the crc."""
        set_to = super().setmtime(set_time)
        # Prevent re-calculating the File CRC
        if not crc_changed:
            self.set_table_prop('crc_mtime', set_to)
        else:
            self.calculate_crc(recalculate=True)
        if mark_redated:
            self.redated = True

    def _get_masters(self):
        """Return the plugin masters, in the order listed in its header."""
        return self.header.masters

    def has_circular_masters(self, *, fake_masters: list[FName] | None = None):
        return self.fn_key in self.recurse_masters(fake_masters=fake_masters)

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
        self._store()._notify_bain({ghost_source}, altered={ghost_target})
        return True

    #--Bash Tags --------------------------------------------------------------
    def tagsies(self, tags_list):
        # Tracks if this plugin has at least one bash tags source - which may
        # still result in no tags at the end, e.g. if source A adds a tag and
        # source B removes it
        has_tags_source = False
        tags_file_fmt = {'tags_file': os.path.join(bush.game.mods_dir_name,
            'BashTags', f'{self.fn_key.fn_body}.txt')}
        sorted_tags = sorted(self.getBashTags())
        msgs = [_('From Plugin Description:'),
                _('From LOOT Masterlist and/or Userlist:'),
                _('Removed by LOOT Masterlist and/or Userlist:'),
                _('Added by %(tags_file)s:')  % tags_file_fmt,
                _('Removed by %(tags_file)s:') % tags_file_fmt,
                _('From Manual (overrides all other sources):')]
        tags = [self.getBashTagsDesc(), *read_loot_tags(self),
            *read_dir_tags(self), not self.mod_auto_bash_tags and sorted_tags]
        for tags_set, msg in zip(tags, msgs, strict=True):
            if tags_set:
                has_tags_source = True
                tags_list.append(f'  * {msg} {", ".join(sorted(tags_set))}')
        res = f'  * {_("Result:")} {", ".join(sorted_tags)}' \
            if has_tags_source else f'    {_("No tags")}'
        tags_list.append(res)

    def tags_path(self) -> bolt.Path:
        return bass.dirs['tag_files'].join(f'{self.fn_key.fn_body}.txt')

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
        return self.get_table_prop('bashTags', set()) & bush.game.allTags

    def getBashTagsDesc(self, *, __tags_search=re.compile(
            '{{ *BASH *:([^}]+)}}', re.I).search):
        """Returns any Bash flag keys."""
        if not (re_match := __tags_search(self.header.description)):
            return set()
        # Remove obsolete and unknown tags and resolve any tag aliases
        return _process_tags({*map(str.strip, re_match.group(1).split(','))})

    def set_auto_tagged(self, auto_tagged, bt_contents=None,
            override_tags=None, add_tags=None, remove_tags=None) -> bool:
        """Set whether this plugin receives its tags automatically and if yes
        reload bash tags from mod description, LOOT and Data/BashTags. Return
        True in this case if the tags actually changed, else False.

        :param bt_contents: Passed to read_dir_tags, see there for docs."""
        self.mod_auto_bash_tags = auto_tagged
        curr_tags = self.getBashTags()
        if not any(args := [override_tags, add_tags, remove_tags]):
            if not auto_tagged:
                return False
            wip_tags = self.getBashTagsDesc()
            # Tags from LOOT take precedence over the description
            added_tags, deleted_tags = read_loot_tags(self)
            wip_tags |= added_tags
            wip_tags -= deleted_tags
            # Tags from Data/BashTags/{self.fn_key}.txt take precedence over both
            # the description and LOOT
            added_tags, deleted_tags = read_dir_tags(self, bt_contents)
            wip_tags |= added_tags
            wip_tags -= deleted_tags
            override_tags = wip_tags
        elif sum(a is not None for a in args) > 1:
            raise ValueError(f'Pass exactly one of {override_tags=}, '
                             f'{add_tags=}, {remove_tags=}')
        else:
            if override_tags is None and add_tags:
                override_tags = curr_tags | add_tags
            elif remove_tags:
                override_tags = curr_tags - remove_tags
        if tags_changed := curr_tags != override_tags:
            self.set_table_prop('bashTags', override_tags)
        return tags_changed

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
            self._store().rescanMergeable([self.fn_key],
                                          sort_descending_lo=False)

    def writeDescription(self, new_desc):
        """Sets description to specified text and then writes hedr."""
        new_desc = new_desc[:min(511,len(new_desc))] # 511 + 1 for null = 512
        self.header.description = new_desc
        self.header.setChanged()
        self.writeHeader()

    def get_version(self):
        """Extract and return version number from self.header.description."""
        desc_match = reVersion.search(self.header.description)
        return (desc_match and desc_match.group(2)) or ''

    #--Helpers ----------------------------------------------------------------
    def isBP(self):
        return self.header.author == u'BASHED PATCH'

    def txt_status(self, *, __st_names={ST_ACTIVE: _('Active'),
            ST_MERGED: _('Merged'), ST_IMPORTED: _('Imported'),
            ST_INACTIVE: _('Inactive')}):
        return __st_names[self.act_st]

    def hasTimeConflict(self):
        """True if there is another mod with the same ftime."""
        return self.fn_key in self._store().lo_conflicts

    def hasActiveTimeConflict(self):
        """True if it has an active mtime conflict with another mod."""
        return self.fn_key in self._store().act_lo_conflicts

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

    def getStringsPaths(self, lang) -> set[Path]:
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

    def _update_onam(self, mf):
        """Checks if this plugin needs ONAM data and either adds or removes it
        based on that."""
        # Skip for games that don't need the ONAM generation
        if bush.game.Esp.generate_temp_child_onam:
            if mf.cached_type(self):
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
        if not scan_beth and skipbeth or self.get_table_prop('ignoreDirty',
                False) or not lootDb.is_plugin_dirty(self.fn_key, modInfos):
            return ''
        return True if skipbeth else _('Contains dirty edits, needs cleaning.')

    def match_oblivion_re(self):
        return self.fn_key in bush.game.modding_esm_size or \
               self.fn_key == 'Oblivion.esm'

    def get_rename_paths(self, new_name, rename_dir, *args):
        old_new_paths = super().get_rename_paths(new_name, rename_dir, *args)
        renaming = rename_dir is None # rename, not the rest of rename_op uses
        mod_infos = self._store()
        if rename_dir == (st_dir := mod_infos.store_dir) or renaming:
            new_ghost = old_new_paths[0][1] + '.ghost' # Path.__add__!
            ghost_dest = (mod_inf := mod_infos.get( # restoring backup
                self.fn_key)) and mod_inf.is_ghost
            if self.is_ghost or ghost_dest: # add ghost extension to dest path
                old_new_paths[0] = self.abs_path, new_ghost
            elif renaming:
                # Add ghosts - the file may exist in both states (bug, or user
                # mistake) in this case the file is marked as normal but let's
                # rename the ghost too - else will appear and frighten the user
                old_new_paths.append((self.abs_path + '.ghost', new_ghost))
            if self.info_dir == st_dir: # renaming or duplicating in store dir
                # Note that if duplicating over an existing mod and we haven't
                # got a tags file, the other mods tags file will be removed in
                # rename_operation - ##: specs?
                old_new_paths.append((tp := self.tags_path(),
                                      tp.head.join(f'{new_name.fn_body}.txt')))
        return old_new_paths

    def _masters_order_status(self, *, __lo=load_order.cached_lo_index):
        """Returns:
            - 0:  Good
            - 10: Out of order master(s)
            - 20: Loads before its master(s)
            - 21: 10 + 20"""
        mo = tuple(load_order.get_ordered(self.masterNames)) # masterOrder
        loads_before_its_masters = mo and __lo(mo[-1]) > __lo(self.fn_key)
        if (inordered := mo != self.masterNames) and loads_before_its_masters:
            return 21
        elif loads_before_its_masters:
            return 20
        elif inordered:
            return 10
        return 0

    def info_status(self, *args, act_dicts, recalc_st=False, **kwargs):
        if recalc_st or self.act_st is None:
            self.act_st = active_keys(self.fn_key, act_dicts)
        return super().info_status(*args, recalc_st=recalc_st, **kwargs
                                   ), self.act_st

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
    ini_st = None
    is_default_tweak = False
    _key_to_attr = {'installer': 'ini_owner_inst'}

    @classmethod
    def _store(cls): return iniInfos

    def info_status(self, *, target_ini_settings=None, recalc_st=False,
                    **kwargs):
        if recalc_st or self.ini_st is None: self.ini_st = self.getStatus(
            target_ini_settings=target_ini_settings)
        return self.ini_st

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
            15: mismatches (green with dot) - mismatches are with another
                tweak from same installer that is applied
            10: mismatches (yellow)
            0: not installed (green)
            -10: tweak file contains new sections/settings
            -20: incompatible tweak file (red)"""
        infos = iniInfos
        target_ini = target_ini or infos.ini
        tweak_settings = self.get_ci_settings()
        if self._incompatible(target_ini) or not tweak_settings:
            return -20
        found_match = False
        mismatch = 0
        ini_settings = target_ini_settings if target_ini_settings is not None \
            else target_ini.get_ci_settings()
        if self_installer := (FName(self.get_table_prop('installer')) or []):
            self_installer = [inf for inf in infos.values() if not (
                inf.get_table_prop('installer') != self_installer or
                inf is self or self._incompatible(inf))]
        for section_key in tweak_settings:
            if section_key not in ini_settings:
                return -10
            target_section = ini_settings[section_key]
            tweak_section = tweak_settings[section_key]
            for item in tweak_section:
                if item not in target_section:
                    return -10
                if tweak_section[item][0] != target_section[item][0]:
                    if mismatch < 2:
                        # Check to see if the mismatch is from another ini
                        # tweak that is applied, and from the same installer
                        mismatch = 2
                        for ini_info in self_installer:
                            value = ini_info.getSetting(section_key, item, None)
                            if value == target_section[item][0]:
                                # The other tweak has the setting we're worried about
                                mismatch = 1
                                break
                else:
                    found_match = True
        if not found_match:
            return 0
        elif not mismatch:
            return 20
        elif mismatch == 1:
            return 15
        elif mismatch == 2:
            return 10

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
        log = bolt.LogFile()
        for line in errors:
            log(line)
        return log.out.getvalue()

#------------------------------------------------------------------------------
class SaveInfo(_WithMastersInfo):
    cosave_types: list[type[ACosave]] = [] # set in SaveInfos.__init__
    _cosave_ui_string = {PluggyCosave: u'XP', xSECosave: u'XO'} # ui strings
    _key_to_attr = {'info': 'save_notes'}
    # Dict of cosaves that may come with this save file
    _co_saves: dict[type[ACosave], ACosave] = {} # instance attr set in init
    sexts = {'save_ext_on': bush.game.Ess.ext}
    sexts['save_ext_off'] = sexts['save_ext_on'][:-1] + 'r'
    file_exts = frozenset([*sexts.values(), '.bak'])

    def __init__(self, fullpath, **kwargs):
        # Need to update cosaves first, since readHeader calls _get_masters,
        # which relies on the cosave for SSE and FO4
        self._update_cosaves(fullpath)
        super().__init__(fullpath, **kwargs)

    def set_path_keys(self, *args, **kwargs):
        """Update our cosave instance names/paths."""
        rpaths = super().set_path_keys(*args, **kwargs)
        for co_type, co_file in self._co_saves.items():
            co_file.abs_path = co_type.get_cosave_path(self.abs_path)
        return rpaths

    @classmethod
    def _store(cls): return saveInfos

    def _masters_order_status(self):
        mo = tuple(load_order.get_ordered(self.masterNames))
        if mo != self.masterNames:
            return 20 # Reordered masters are far more important in saves
        active_tuple = load_order.cached_active_tuple()
        if mo == active_tuple:
            # Exact match with LO -> purple
            return -20
        if mo == active_tuple[:len(mo)]:
            # Matches LO except for new plugins at the end -> blue
            return -10
        # Does not match the LO's active plugins, but the order is correct.
        # That means the LO has new plugins, but not at the end -> green
        return 0

    def info_status(self, *args, **kwargs):
        return super().info_status(*args, **kwargs), self.is_save_enabled()

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
        # If the cosaves have changed, the cached masters can no longer be
        # trusted since they may have been retrieved from the cosaves
        if cosaves_changed := self._update_cosaves():
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
        for j, co_typ in enumerate(reversed(self.__class__.cosave_types)):
            inst = instances.get(co_typ, None)
            if inst and inst.abs_path.exists():
                co_ui_strings[j] = self._cosave_ui_string[co_typ][
                    abs(inst.abs_path.mtime - self.ftime) < 10]
        return u'\n'.join(co_ui_strings)

    def get_rename_paths(self, new_name, rename_dir, *args):
        old_new_paths = super().get_rename_paths(new_name, rename_dir, *args)
        # super call added the backup paths but not the actual cosave paths
        # inside the store_dir - add those even if they don't exist as we must
        # delete cosaves for backup (if the backup has no cosaves)
        old_new_paths.extend(
            tuple(map(co_type.get_cosave_path, old_new_paths[0])) for co_type
            in self.__class__.cosave_types)
        return old_new_paths

    def _update_cosaves(self, co_path=None) -> bool:
        """Check for new and deleted cosaves and do_update old, surviving ones.
        """
        csaves, cosaves_changed, co_path = {}, False, co_path or self.abs_path
        for co_type in self.__class__.cosave_types:
            try: # Existing cosave could have changed, check if it did
                try:
                    if (csave := self._co_saves[co_type]).abs_path.is_dir():
                        continue # do_update won't see that a cosave is a dir now
                    cosaves_changed |= csave.do_update()
                except KeyError: # New cosave attached, add it to cache
                    csave = co_type(co_type.get_cosave_path(co_path))
                csaves[co_type] = csave
            except (OSError, FileError) as e:
                if not isinstance(e, (FileNotFoundError, IsADirectoryError)):
                    deprint(f'Failed to open {co_path}', traceback=True)
        cosaves_changed |= csaves.keys() != self._co_saves.keys()
        self._co_saves = csaves
        return cosaves_changed

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

#------------------------------------------------------------------------------
class ScreenInfo(AFileInfo):
    """Cached screenshot, stores a bitmap and refreshes it when its cache is
    invalidated."""
    _has_digits = True
    file_exts = ss_image_exts

    def __init__(self, fullpath, **kwargs):
        super().__init__(fullpath, **kwargs)
        self.cached_bitmap = None

    def _reset_cache(self, stat_tuple, **kwargs):
        self.cached_bitmap = None # Lazily reloaded
        super()._reset_cache(stat_tuple, **kwargs)

    @classmethod
    def _store(cls): return screen_infos

    def validate_name(self, *args, **kwargs):
        file_root, num_str = super().validate_name(*args, **kwargs)
        return (file_root, num_str) if num_str is None else (
            FName(file_root + num_str + self.fn_key.fn_ext), '')

#------------------------------------------------------------------------------
def _check_renamed(paths_per_file):
    for inf, (rename_paths, new_name, *_inf_dir) in [*paths_per_file.items()]:
        if all(p[1].exists() for p in rename_paths):
            for p in rename_paths:
                p[0].remove() #(241) clear paths left behind (needed?)
            continue
        deprint(f'Renaming {inf} to {new_name} failed', traceback=True)
        del paths_per_file[inf]
        # When using moveTo I would get "WindowsError:[Error 32]The process
        # cannot access ..." -  the code below was reverting the changes.
        # With shellMove I mostly get CancelError so below not needed -
        # except if a save is locked and user presses Skip - so cosaves are
        # renamed! Error handling is still a WIP
        for old, new in rename_paths:
            if (nex := new.exists()) and not (oex := old.exists()):
                # some cosave move failed, restore files
                new.moveTo(old, check_exist=False)  # just checked
            elif nex and oex:
                # move copies then deletes, so the delete part failed
                new.remove()

class DataStore(DataDict):
    """Base class for the singleton collections of infos."""
    store_dir: Path # where the data sit, static except for Save/ScreenInfos
    _dir_key: str # key in dirs dict for the store_dir
    dat_loaded = False
    factory_type: type[AFileInfo]
    _boot_refresh_args: dict = {}
    _files_str = '' # used to create unhide wildcard

    def __init__(self):
        """Init then refresh if _boot_refresh arguments is not empty."""
        super().__init__(self._init_store(self.set_store_dir()))
        if self._boot_refresh_args:
            self.refresh(True, **self._boot_refresh_args)

    def set_store_dir(self):
        self.store_dir = sd = dirs[self._dir_key]
        self.store_dir.makedirs()
        return sd

    def _init_store(self, storedir):
        deprint(f'Initializing {self.__class__.__name__}')
        deprint(f' store_dir: {storedir}')
        storedir.makedirs()
        self._data = FNDict()
        return self._data

    # Store operations --------------------------------------------------------
    def refresh(self, refresh_in: RefrData | RefrIn | bool, *,
                extract_omods=None, progress=None, **kw_do_upd) -> RefrData:
        """Refreshes the store caches, returning a RefrData instance encoding
        information on which files were added/modified/deleted. Base
        implementation refreshes the main infos cache (namely self._data)
        according to the refresh_in parameter, which can be:
        - RefrData: cache was updated already (see rename_operation)
        - RefrIn: we need to update the data store according to the changes
          encoded in the RefrIn instance
        - bool: if True, we need to scan the store directory else skip infos
          refresh (we are called to update other data store info like load
          order).
        """
        if isinstance(refresh_in, RefrData):
            return refresh_in # already scanned, return as is
        rdata = RefrData() # create the return value instance then scan changes
        if not refresh_in: # False or empty RefrIn
            return rdata
        if (load := not self.dat_loaded) or not isinstance(refresh_in, RefrIn):
            if table_dat := load:
                self.dat_loaded = True # one chance to load
                table_dat = self._load_dat(progress)
            omds = [] if extract_omods else None
            inodes = FNDict()
            sk = table_dat or set()
            with os.scandir(self.store_dir) as it:
                for x in it:
                    try:
                        if kws := self.check_filename(x.name, _inode=x,
                                with_omods=omds, skipstat=sk, _inodes=inodes):
                            fn, kws = next(iter(kws.items()))
                            if 'cached_stat' not in kws: # for _AfileInfos
                                kws['cached_stat'] = x.stat()
                            inodes[fn] = kws
                    except OSError: # this should not happen
                        deprint(f'Failed to stat {x.name} in {self.store_dir}',
                                traceback=True)
            refresh_in = self._diff_dir(inodes)
            if omds:
                refresh_in |= extract_omods(omds)
            if load:
                self._merge_dat(refresh_in, table_dat)
        delinfos = refresh_in.del_infos
        if (nop := refresh_in.new_or_present) and progress:
            progress.setFull(len(nop))
        for index, (new, (old_inf, kws)) in enumerate(nop.items()):
            if progress: # currently only installers and only on boot
                progress(index, _('Scanning Packages…') + f'\n{new}')
                kws['progress'] = SubProgress(progress, index, index + 1)
            if newinf := self.get_update_info(new, old_inf, _rdata=rdata,
                                              **kws, **kw_do_upd):
                if create_inf := old_inf is None:
                    self[new] = newinf
                (rdata.to_add if create_inf else rdata.redraw).add(new)
        if delinfos:
            rdata.to_del |= self._delete_refresh(delinfos)
        return rdata

    def get_update_info(self, fname: FName | Path,
            old_inf: AFileInfo | None = None, *, _rdata=None,**kwargs):
        """Get new info (for new file or updated corrupted) else check updates.
        Will try loading from disk, only call on existing files."""
        if old_inf is None:
            if not isinstance(fname, Path): fname = self.store_dir.join(fname)
            return self.factory(fname, load_cache=True, **kwargs)
        return old_inf.do_update(**kwargs)

    def factory(self, info_path, **kwargs):
        return self.factory_type(info_path, **kwargs)

    def _delete_refresh(self, delinfos):
        """Only called from refresh.
        :param delinfos: the infos corresponding to deleted items."""
        return {del_fn for del_inf in delinfos if
                self.pop(del_fn := del_inf.fn_key, None)}

    @classmethod
    def check_filename(cls, fileName: FName | str, *, _allow_ext=None,
            _inode: DirEntry | None=None, _inodes=None, **_store_kws) -> \
                tuple[str, str] | None | False | dict:
        """Check if the filetype is correct for subclass by checking the
        basename (usually the extension but sometimes also the root).
        Returns None (or False) for InstallerProject in any case."""
        base, dot_ext = os.path.splitext(fileName)
        right_ext = dot_ext.lower() in (_allow_ext or cls._file_exts)
        if _inode is None: # else we are in DataStore.refresh
            return (base, dot_ext) if right_ext else None
        return _inode.is_file() and ( # see the Installer override
                    (right_ext and {FName(fileName): {}}) or None)

    @classproperty
    def _file_exts(cls):
        return cls.factory_type.file_exts

    @classmethod
    def info_exts(cls, with_ghosts=True):
        return cls._file_exts

    def _diff_dir(self, inodes) -> RefrIn: # single use in refresh (and super)
        """Return a dict of fn keys (see overrides) of files present in data
        dir and a set of deleted infos."""
        # for modInfos '.ghost' must have been lopped off from inode keys
        delinfos = self._get_delinfos(inodes)
        new_or_present = {}
        for k, kws in inodes.items():
            # corrupted that has been updated on disk - if cor.abs_path
            # changed ghost state (effectively deleted) do_update returns True
            # ghost state can only change manually for corrupted - don't!
            self._get_info(k, kws, new_or_present)
        return RefrIn(new_or_present, delinfos)

    def _get_delinfos(self, inodes):
        raise NotImplementedError

    def _get_info(self, k, kws, new_or_present):
        new_or_present[k] = (self.get(k), kws)

    def delete_op(self, info_keys, *, recycle=True, do_refr=True, _filter=True):
        """Deletes member file(s)."""
        # for _AFileInfos k may correspond to a corrupted file - create an info
        finfos = [v or self.factory(self.store_dir.join(k)) for k, v in
            self.filter_essential(info_keys).items()] if _filter else info_keys
        renpaths = chain.from_iterable(inf.get_rename_paths(
            inf.fn_key, None, True) for inf in finfos)
        try: # collect all the info/cosaves/backup paths
            if abs_del_paths := [a for a, b in renpaths]:
                env.shellDelete(abs_del_paths, recycle=recycle)
        finally:
            finfos = {inf for inf in finfos if not inf.abs_path.exists()}
            if finfos and do_refr:
                finfos = self.refresh(RefrIn(del_infos=finfos), what='I',
                                      unlock_lo=True)
        return finfos

    _retry_msg = [_('Wrye Bash encountered an error when renaming %(old)s to '
                    '%(new)s.'), '', '',
        _('The file is in use by another process such as %(xedit_name)s.'), '',
        _('Please close the other program that is accessing %(new)s.'), '', '',
        _('Try again?')]
    def rename_operation(self, info_new_name, *, try_once=True, set_mtime=None,
                         ren_parent=None, with_backups=False, copy_inf=False,
                         insert_after=None, force_flags=None) -> RefrData:
        rd_ren = RefrData()
        if not info_new_name:
            return rd_ren
        all_rename_paths = {}
        paths_per_file = {} # revert partial renames
        for inf, new_name, *inf_dir in info_new_name:
            infdir = inf_dir[0] if inf_dir else None
            rename_paths = inf.get_rename_paths(new_name, infdir, with_backups)
            for tup in rename_paths[1:]: # first rename path must always exist
                # if cosaves or backups do not exist shellMove fails!
                # if filenames are the same (for instance cosaves in disabling
                # saves) shellMove will offer to skip and raise SkipError
                if (src_missing := not tup[0].exists()) or tup[0] == tup[1]:
                    rename_paths.remove(tup)
                    # if cosave exists while its backup not, delete it on
                    # restoring - copy_inf is currently used in restore backup
                    # will also delete the tag files when duplicating mods
                    if src_missing and copy_inf:
                        tup[1].remove() ##:(292) we should document this
            all_rename_paths.update(rename_paths)
            paths_per_file[inf] = rename_paths, new_name, infdir
        if all_rename_paths:
            while try_once:
                try:
                    (env.shellCopy if copy_inf else env.shellMove)(
                        all_rename_paths, ren_parent)
                except (CancelError, OSError) as e:
                    ##:(#241)  only for swapping Oblivion esm, duh - was
                    # PermissionError, occurred if SHFileOperation isn't called
                    # (now we use IFileOperation anyway) - CancelError? Test!
                    if try_once is not True:
                        old, new = next(iter(all_rename_paths.items()))
                        msg = '\n'.join(self._retry_msg) % {'old': old,
                            'new': new, 'xedit_name': bush.game.Xe.full_name}
                        if isinstance(e, OSError) and try_once(
                                msg, title=_('File in Use')):
                            continue
                        _check_renamed(paths_per_file)
                        raise
                    _check_renamed(paths_per_file)
                break
        # self[newName]._mark_unchanged() # not needed with shellMove!(#241...)
        inst_dupl = isinstance(insert_after, int) ##: moveArchives must be moved
        for inf, (rename_paths, new_name, infdir) in paths_per_file.items():
            set_ghost = (ap := getattr(inf, 'abs_path', None)) and \
                        all_rename_paths[ap].cext == '.ghost'
            rd_ren |= RefrData(renames={(old_key := inf.fn_key): new_name},
                to_del={old_key} if not copy_inf and self.pop(
                    old_key, None) else set(), # pop if not unhiding/restoring
                # lastly set the new info abspath/key
                ren_paths=inf.set_path_keys(new_name, infodir=infdir))
            add_to_store = not rename_paths or inf.info_dir == self.store_dir
            if add_to_store: # add the info (or marker info) to the store
                kws = {'redraw' if new_name in self else 'to_add': {new_name}}
                self[new_name] = inf
                if inst_dupl:
                    self.moveArchives([new_name], insert_after)
                rd_ren |= RefrData(**kws) # pop from to_del
                if set_ghost: # do this after set_path_keys (restore backup)
                    inf.is_ghost = True # we need to mirror get_rename_paths
        for new, flgs in (force_flags or {}).items():
            self[new].set_plugin_flags(flgs)
        if set_mtime: # only set in self.try_set_version/restore backup
            for k, v in set_mtime.items():
                self[k].setmtime(v)
            if not copy_inf and len(renames_di := rd_ren.renames) == 2:
                move_to = renames_di.pop(bush.game.master_file)
                renames_di[next(iter(renames_di))] = move_to
        return self.refresh(rd_ren, unlock_lo=True, insert_after=insert_after,
                            what='N' if inst_dupl else 'I')

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
    def hide_dir(self) -> Path:
        """Return the folder where Bash should move the file info to hide it"""
        return self.bash_dir.join(u'Hidden')

    @classmethod
    def unhide_wildcard(cls, *, with_ghosts=True) -> str:
        exts = f'*{";*".join(cls.info_exts(with_ghosts))}'
        return f'{bush.game.display_name} {cls._files_str} ({exts})|{exts}'

    def warning_args(self, multi_warnings, lo_warnings):
        """Append the arguments for the warning message to the multi_warnings
        and lo_warnings lists, checking the data store _known_* caches."""

    # Abstract part - persistence (implemented for all but ScreenInfos)
    @property
    def bash_dir(self) -> Path:
        """Return the folder where Bash persists its data.Create it on init!"""
        raise NotImplementedError

    def _load_dat(self, progress=None):
        raise NotImplementedError

    def _merge_dat(self, refresh_in, table_dat):
        raise NotImplementedError

    def save_pickle(self): raise NotImplementedError

class _AFileInfos(DataStore):
    """File data stores - all of them except InstallersData."""
    _bain_notify = True # notify BAIN on deletions/updates ?
    # Whether these file infos track ownership in a table
    tracks_ownership = True
    _boot_refresh_args = {'booting': True}

    def _init_store(self, storedir):
        """Set up self's _data/corrupted and return the former."""
        self.corrupted: FNDict[FName, _Corrupted] = FNDict()
        return super()._init_store(storedir)

    #--Refresh
    def refresh(self, refresh_in, *, booting=False, **kwargs):
        """Refresh from file directory."""
        rdata = super().refresh(refresh_in, **kwargs)
        if not booting and ((alt := rdata.new_changed()) or rdata.ren_paths):
            self._notify_bain( # normal deletions are handled in super
                {*rdata.ren_paths}, {self[n].abs_path for n in alt})
        return rdata

    def get_update_info(self, fn, old_inf=None, *, _rdata=None, **kwargs):
        try: ##:701 revisit this - why NIE?
            info = super().get_update_info(fn, old_inf, **kwargs)
            if _rdata is not None:
                self.corrupted.pop(fn, None) # effectively updated
            return info
        except (FileError, UnicodeError, BoltError, NotImplementedError) as e:
            # old still corrupted, or new(ly) corrupted or we landed
            # here cause cor_path was manually un/ghosted but file remained
            # corrupted so in any case re-add to corrupted
            er = e.message if hasattr(e, 'message') else f'{e}'
            cor_path = fn if isinstance(fn, Path) else self.store_dir.join(fn)
            if _rdata is not None: # we are called from refresh, fn is FName
                if del_inf := self.pop(fn, None): # effectively deleted
                    _rdata |= RefrData(to_del={fn})
                    cor_path = del_inf.abs_path
                elif self is modInfos: # modInfos needs be set here!
                    if (isg := kwargs.get('itsa_ghost')) is None:
                        isg = not cor_path.is_file() and os.path.isfile(
                            f'{cor_path}.ghost')
                    if isg: cor_path = cor_path + '.ghost'  # Path.__add__ !
                self.corrupted[fn] = cor = _Corrupted(cor_path, er, fn, **kwargs)
                cor_path = cor.abs_path
            deprint(f'Failed to load {fn} from {cor_path}: {er}', traceback=True)
            return False

    def _get_delinfos(self, inodes):
        return {inf for inf in [*self.values(), *self.corrupted.values()]
                if inf.fn_key not in inodes}

    def _get_info(self, k, kws, new_or_present):
        if (cor := self.corrupted.get(k)) and cor.do_update():
            new_or_present[k] = (None, kws)
        elif not cor:  # for default tweaks with a corrupted copy
            super()._get_info(k, kws, new_or_present)

    def _delete_refresh(self, delinfos):
        for del_fn in (inf.fn_key for inf in delinfos):
            self.corrupted.pop(del_fn, None)
        self._notify_bain({inf.abs_path for inf in delinfos})
        return super()._delete_refresh(delinfos)

    def _notify_bain(self, del_set: set[Path] = frozenset(),
                     altered: set[Path] = frozenset()):
        """Note that all of these parameters need to be absolute paths!"""
        if self._bain_notify:
            InstallersData.notify_external(del_set, altered)

    def _load_dat(self, progress=None):
        """Load pickled data for mods, saves, inis and bsas."""
        deprint(f' bash_dir: {self.bash_dir}') # self.store_dir may need be set
        self.bash_dir.makedirs()
        return bolt.DataTable(self.bash_dir.join('Table.dat'),
                              load_pickle=True).pickled_data

    def _merge_dat(self, refresh_in, table_dat):
        table_dat = {k: v for k, v in table_dat.items() if
                     k in refresh_in.new_or_present}
        refresh_in |= RefrIn.from_tabled_infos(extra_attrs=table_dat)

    def save_pickle(self):
        pd = bolt.DataTable(self.bash_dir.join('Table.dat')) # don't load!
        for k, v in self.items():
            if pickle_dict := v.get_persistent_attrs():
                pd.pickled_data[k] = pickle_dict
        pd.save()

    # _AFileInfos specific methods --------------------------------------------
    def data_path_to_info(self, data_path: str, *, get_dest_paths=False,
                          with_corrupted=True)-> _ListInf | tuple[Path, FName]:
        """Return the info corresponding to the specified (str, Fname or CIStr)
        path relative to the  Data folder - iff it belongs to this data store.
        If it does not, return None, except if get_dest_paths is True whereupon
        return the pair of dest_path/fn_key, if it is a valid one for self."""
        inf = self.get(fnkey := FName(str(data_path))) or (
            with_corrupted and self.corrupted.get(fnkey))
        if not get_dest_paths:
            return inf
        if not inf and not (os.path.basename(fnkey) == fnkey and #bare filename
                            self.check_filename(fnkey)):
            return None
        # we may be installing a DefaultIni here (no abs_path) or inf be None
        dest = getattr(inf, 'abs_path', None) or self.store_dir.join(fnkey)
        return dest, fnkey

class _Corrupted(AFile):
    """A 'corrupted' file info. Stores the exception message. Not displayed."""

    def __init__(self, fullpath, error_message, cor_key, **kwargs):
        self.fn_key = cor_key
        super().__init__(fullpath, **kwargs)
        self.error_message = error_message

#------------------------------------------------------------------------------
class INIInfo(IniFileInfo, AINIInfo):

    def _reset_cache(self, stat_tuple, **kwargs):
        super()._reset_cache(stat_tuple, **kwargs)
        self.ini_st = None

class ObseIniInfo(OBSEIniFile, INIInfo): pass

class DefaultIniInfo(AINIInfo):
    """A default ini tweak - hardcoded."""
    is_default_tweak = True
    file_exts = frozenset(['.ini']) # only extension allowed - enforce it

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

class INIInfos(_AFileInfos):
    _ini: IniFileInfo | None
    _data: dict[FName, AINIInfo]
    _dir_key = 'ini_tweaks'
    _file_exts = IniFileInfo.file_exts

    def __init__(self):
        self._default_tweaks = FNDict((k, DefaultIniInfo(k, v)) for k, v in
                                      bush.game.default_tweaks.items())
        super().__init__()
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
        global iniInfos
        iniInfos = self # needed for status calculation in getStatus
        self.ini = list(bass.settings[u'bash.ini.choices'].values())[
            bass.settings['bash.ini.choice']] # set self.redraw_target = True

    def refresh(self, refresh_in, *, booting=False, **kwargs):
        rdata = super().refresh(refresh_in, booting=booting)
        # re-add default tweaks (booting / restoring a default over copy,
        # delete should take care of this but needs to update rdata...)
        miss = (dt for dt in self._default_tweaks.items() if dt[0] not in self)
        for k, default_info in miss:
            self[k] = default_info  # type: DefaultIniInfo
            if k in rdata.to_del: # we restore default over copy
                rdata |= RefrData({k}) # will pop it from to_del also
                default_info.info_status(recalc_st=True, **kwargs)
            else: # booting
                rdata.to_add.add(k)
        if not booting and ((targ := self.ini).updated or targ.do_update()):
            targ.updated = False
            rdata |= self._reset_all_statuses() # set the status of all infos
        return rdata

    def factory(self, fullpath, *, copy_from=None, dup_path=None,
                rd_def_ini=None, **kwargs) -> INIInfo | None:
        """INIInfos factory - copy_from/dup_path used when duplicating an ini"""
        if isinstance(copy_from, DefaultIniInfo):
            with open(fullpath, 'wb') as ini_file:
                ini_file.write(copy_from.read_ini_content(as_unicode=False))
            dup_info = INIInfo(fullpath, 'ascii')
            dup_info.fs_copy(dup_path, do_move=True)
            dup_info.set_path_keys(FName(dup_path.stail), infodir=dup_path.head)
            if dup_info.info_dir == self.store_dir:
                rd_def_ini |= RefrData(
                    renames={copy_from.fn_key: (dup_fn := dup_info.fn_key)},
                    **{'redraw' if dup_fn in self else 'to_add': {dup_fn}})
                self[dup_fn] = dup_info
            return None
        else:
            inferred_ini_type, detected_encoding = get_ini_type_and_encoding(
                fullpath, consider_obse_inis=bush.game.Ini.has_obse_inis)
            ini_info_type = (ObseIniInfo if inferred_ini_type == OBSEIniFile
                             else INIInfo)
        return ini_info_type(fullpath, detected_encoding, copy_from=copy_from)

    def _diff_dir(self, inodes):
        old_ini_infos = {*(v for v in self.values() if not v.is_default_tweak),
                         *self.corrupted.values()}
        rin_diff = super()._diff_dir(inodes)
        # if iinf is a default tweak a file has replaced it - set it to None
        rin_diff.new_or_present = {
            k: (inf and (None if inf.is_default_tweak else inf), kws) for
            k, (inf, kws) in rin_diff.new_or_present.items()}
        rin_diff.del_infos &= old_ini_infos # drop default tweaks
        return rin_diff

    def _reset_all_statuses(self): # only return infos that changed status
        updt = {fn for fn, ini_info in self.items() if
                ini_info.ini_st != ini_info.info_status(recalc_st=True)}
        self.redraw_target = True # we are called on target update - msg the UI
        return RefrData(updt)

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
    def data_path_to_info(self, data_path: str, **kwargs) -> _ListInf:
        parts = os.path.split(os.fspath(data_path))
        # 1. Must have a single parent folder
        # 2. That folder must be named 'ini tweaks' (case-insensitively)
        # 3. The extension must be a valid INI-like extension - super checks it
        if len(parts) == 2 and parts[0].lower() == 'ini tweaks':
            return super().data_path_to_info(parts[1], **kwargs)
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

    def copy_to_new_tweak(self, info, fn_new_tweak):
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
            ldiff = LordDiff() if ldiff is None else ldiff #only set in refresh
            ldiff |= lord_func(self, *args, **kwargs)
            if ldiff:
                # Update all data structures that may be affected by LO change
                ldiff.affected |= self._refresh_mod_inis_and_strings()
                ldiff.affected |= self._file_or_active_updates()
                # unghost new active mods and ghost new inactive (if autoGhost)
                ghostify = dict.fromkeys(ldiff.new_act, False)
                if bass.settings['bash.mods.autoGhost']: # new mods, ghost
                    new_inactive = ldiff.new_inact | (
                                ldiff.added - ldiff.new_act)
                    ghostify.update({k: True for k in new_inactive if
                        self[k].get_table_prop('allowGhosting', True)})
                ldiff.affected.update(mod for mod, ghost_it in ghostify.items()
                                      if self[mod].setGhost(ghost_it))
            # check for load order conflicts - if ldiff is empty we should keep
            # it empty (for refresh to check if it needs the refreshes above),
            # but we should notify the UI to redraw items that changed status
            mt_conflicts_changes = set()
            if bush.game.mtime_lo:
                mtime_mods = defaultdict(set)
                for mod, info in self.items():
                    mtime_mods[int(info.ftime)].add(mod)
                mtime_mods = {frozenset(v) for v in mtime_mods.values() if
                              len(v) > 1} # keep conflicting sets of mods
                lo_conflicts, act_lo_conflicts = set(), set()
                if mtime_mods:
                    activ = {*load_order.cached_active_tuple()}
                    for confls in mtime_mods:
                        lo_conflicts |= confls
                        if len(confls_act := confls & activ) > 1:
                            # active mods conflicting with other active mods
                            act_lo_conflicts |= confls_act
                # mods that started/stopped conflicting or were redated
                mt_conflicts_changes |= (self.lo_conflicts ^ lo_conflicts |
                    act_lo_conflicts ^ self.act_lo_conflicts |
                    self.scan_redated()) & set(self) # drop missing mods
                self.lo_conflicts = lo_conflicts
                self.act_lo_conflicts = act_lo_conflicts
            # note we ignore missing/added here - this is the responsibility of
            # refresh - if we are not called from refresh those should be empty
            return RefrData(ldiff.reordered | ldiff.affected |
                            ldiff.act_ord_status() | mt_conflicts_changes)
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
        ldiff = LordDiff() if ldiff is None else ldiff #output: used in refresh
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
                        RefrData() # out_diff is empty
            return out_diff if lo_msg is None else (lo_msg, out_diff)
    return _lo_wip_wrapper

#------------------------------------------------------------------------------
class ModInfos(_AFileInfos):
    """Collection of modinfos. Represents mods in the Data directory."""
    _dir_key = 'mods'
    # caches for UI warnings
    _known_cor_mods = set()
    _known_invalid_versions = set()
    _known_older_form_versions = set()
    factory_type = ModInfo
    _files_str = _('Plugins')

    def __init__(self):
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
        self.bashed_patches = set() # bashed_patches cache
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
        # lo conflicts cache only used in _ModsUIList.set_item_format
        self.lo_conflicts, self.act_lo_conflicts = set(), set()
        super().__init__()

    # Refresh - not quite surprisingly this is super complex - therefore define
    # refresh satellite methods before even defining the DataStore overrides
    def refresh(self, refresh_in, *, booting=False, unlock_lo=False,
                insert_after: FNDict[FName, FName] | None = None, **kwargs):
        """Update file data for additions, removals and date changes.
        See usages for how to use the refresh_infos and unlock_lo params.
        NB: if an operation *we* performed changed the load order we do not
        want lock load order to revert our own operation. So either call
        some of the set_load_order methods, or pass unlock_lo=True
        (refreshLoadOrder only *gets* load order)."""
        # Scan the data dir, getting info on added, deleted and modified files
        try:
            bt_contents = {*top_level_files(bass.dirs['tag_files'])}
        except FileNotFoundError:
            bt_contents = set()  # No BashTags folder -> no BashTags files
        rdata = super().refresh(refresh_in, booting=booting,
                                bt_contents=bt_contents)
        mods_changes = bool(rdata)
        ldiff = LordDiff()
        if deltd := rdata.to_del: #restore first backup is_rename but no to_del
            if rdata.is_rename: # rename in load order caches and properties
                rget = rdata.renames.get
                for mod_inf in self.values():
                    if par := rget(mod_inf.get_table_prop('bp_split_parent')):
                        mod_inf.set_table_prop('bp_split_parent', str(par))
                wip_lo = [rget(x, x) for x in self._lo_wip]
            else:
                wip_lo = [x for x in self._lo_wip if x not in deltd]
            act = [x for x in self._active_wip if x not in deltd]
            # pass the out diff to ensure we save - we need to filter active
            dlos = self._diff_los(new_lo=wip_lo, new_act=act)
            self._active_wip, self._lo_wip = act, wip_lo
            # warn the user on deactivated dependents?
            lordata = self.lo_deactivate(*deltd, ldiff=ldiff, save_all=True,
                                         out_diff=dlos, _deleted=True)
        elif insert_after: # we should have no deletions here!
            lordata = self._lo_insert_after(insert_after, save_wip_lo=True,
                                            ldiff=ldiff)
        else: # if refresh_infos is False but mods are added force refresh
            lordata = self.refreshLoadOrder(ldiff=ldiff,
                forceRefresh=mods_changes or unlock_lo,
                forceActive=bool(rdata.to_del), unlock_lo=unlock_lo)
            if not unlock_lo and ldiff.missing: # unlock_lo=True in delete/BAIN
                self.warn_missing_lo_act.update(ldiff.missing)
        # if load order did not change, we must perform the refreshes below
        if not ldiff:
            # in case ini files were deleted or modified or maybe string files
            # were deleted... we need a load order below: in skyrim we read
            # inis in active order - we then need to redraw what changed status
            rdata.redraw |= self._refresh_mod_inis_and_strings() | \
                            self.scan_redated()
            if mods_changes:
                rdata.redraw |= self._file_or_active_updates()
        rdata |= lordata
        self._voAvailable, self.voCurrent = bush.game.modding_esms(self)
        return rdata

    def scan_redated(self):
        return {k for k, v in self.items() if # reset 'redated'
                v.redated and not setattr(v, 'redated', False)}

    # _AFileInfos overrides that are used in refresh - ghosts ahead
    @classmethod
    def check_filename(cls, fname, *, _inodes=None, **kwargs):
        if itsa_ghost := fname[-6:].lower() == '.ghost':
            fname = fname[:-6]
        fname = FName(fname)
        if _inodes and fname in _inodes:
            ##: we need to propagate this warning once refresh dust settles
            deprint(f'File {fname} and its ghost exist. The ghost will be '
                    f'ignored but this may lead to undefined behavior - please '
                    f'remove one or the other')
            if itsa_ghost: return None # ignore the ghost
            return {fname: {'itsa_ghost': False}} # override entry in _inodes
        if sup := super().check_filename(fname, **kwargs):
            if isinstance(sup, dict):
                sup[fname]['itsa_ghost'] = itsa_ghost
        return sup

    @classmethod
    def info_exts(cls, with_ghosts=True):
        sup = super().info_exts()
        return {*sup, '.ghost'} if with_ghosts else sup

    def _file_or_active_updates(self, *, __lo=load_order.cached_lo_index):
        """If any plugins have been added, updated or deleted, or the active
        order/status changed we need to recalculate cached data structures."""
        ##:(701) We could be more granular passing ldiff (and rdata) - this
        # would be a final check for ModInfos.refresh
        # Recalculate the dependents cache
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
        none_ = (None, {})
        act = {*(act_tuple := load_order.cached_active_tuple())}
        for fn_mod, plug in dict_sort(self, reverse=True, key_f=__lo):
            for p_master in plug.masterNames:
                cached_dependents[p_master].add(fn_mod)
            isact = fn_mod in act
            if plug.isBP():
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
            cached_size, canMerge = plug.get_table_prop('mergeInfo', none_)
            # Quickly check if some mergeability types are impossible for this
            # plugin (because it already has the target type)
            new_checks = {m: False for m, m_check in quick_checks.items() if
                          m_check(plug)}
            # If ve already covered all required checks with the quick checks
            # above (e.g. an ESL-flagged plugin in a game with only ESL
            # support -> not ESL-flaggable), or the cached size matches what we
            # have on disk, and we have data for all required mergeability
            # checks, we can cache the info
            if len(new_checks) == all_checks or (len(canMerge) == all_checks
                    and cached_size == plug.fsize):
                if canMerge != (canMerge := canMerge | new_checks):
                    changed.add(fn_mod)
                plug.set_table_prop('mergeInfo', (plug.fsize, canMerge))
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
            ((p, self[p]) for p in act_tuple))
        merged, imported = self.getSemiActive(active_patches)
        dex_xor = (k for k, v in self.real_indices.items() ^ old_dexs.items()
            if v[0] != sys.maxsize) # added from defaultdict for inactive mods
        chain_ch = chain(self.bashed_patches ^ bps, dex_xor, changed,
            rescan_mods, self.activeBad ^ old_ab, self.bad_names ^ old_bad)
        to_redraw = {m for m in chain_ch if m in self}
        # reset and cache master status for (all) mod infos (more granular?)
        self.active_statuses = {ST_ACTIVE: act,
                                ST_MERGED: merged, ST_IMPORTED: imported}
        for fn, plug in self.items(): # we could use dependents here?
            old, new = (plug.master_st, plug.act_st), plug.info_status(
                recalc_st=True, act_dicts=self.active_statuses)
            if old != new: # we need to redraw
                to_redraw.add(fn)
        return to_redraw

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
        ##:(701) depends on bsaInfos thus a bsaInfos.refresh should trigger a
        # modInfos.refresh - see comments in get_bsa_lo
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
        present_inis = {i for i in os.listdir(data_folder_path) if
                        i.lower().endswith('.ini')}
        # Determine which INIs are active based on LO. Order now matters
        active_inis = [i for m in load_order.cached_active_tuple() if
                       (i := self[m].get_ini_name()).lower() in present_inis]
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

    def getSemiActive(self, patches):
        """Return (merged,imported) mods made semi-active by Bashed Patch.

        If no bashed patches are present in 'patches' then return empty sets.
        Else for each bashed patch use its config (if present) to find mods
        it merges or imports.

        :param patches: A set of mods to look for bashed patches in."""
        merged_, imported_ = set(), set()
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
        return merged_, imported_

    # Rest of DataStore overrides ---------------------------------------------
    def filter_essential(self, fn_items: Iterable[FName]):
        # Removing the game master breaks everything, for obvious reasons
        return {k: self.get(k) for k in fn_items if k != self._master_esm}

    @property
    def bash_dir(self): return dirs[u'modsBash']

    def warning_args(self, multi_warnings, lo_warnings):
        corruptMods = set(self.corrupted)
        if new_cor := corruptMods - self._known_cor_mods:
            msg = _('The following plugins could not be read. This most '
                    'likely means that they are corrupt.')
            multi_warnings.append((msg, new_cor, self))
            self._known_cor_mods |= corruptMods
        valid_vers = bush.game.Esp.validHeaderVersions
        invalidVersions = {ck for ck, x in self.items() if
                           all(x.header.version != v for v in valid_vers)}
        if new_inv := invalidVersions - self._known_invalid_versions:
            multi_warnings.append((_(
                'The following plugins have header versions that are not '
                'valid for this game. This may mean that they are actually '
                'intended to be used for a different game.'), new_inv, self))
            self._known_invalid_versions |= invalidVersions
        old_fvers = self.older_form_versions
        if new_old_fvers := old_fvers - self._known_older_form_versions:
            msg = _('The following plugins use an older Form Version for '
                    'their main header. This most likely means that they '
                    'were not ported properly (if at all).')
            multi_warnings.append((msg, new_old_fvers, self))
            self._known_older_form_versions |= old_fvers
        if self.new_missing_strings:
            msg = _('The following plugins are marked as localized, but are '
                    'missing strings localization files in the language your '
                    'game is set to. This will cause CTDs if they are '
                    'activated.')
            multi_warnings.append((msg, self.new_missing_strings, self))
            self.new_missing_strings = set()
        if self.warn_missing_lo_act:
            msg = _('The following plugins could not be found in the '
                    '%(data_folder)s folder or are corrupt and have thus '
                    'been removed from the load order.')
            lo_warnings.append((msg % {'data_folder': bush.game.mods_dir_name},
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
    def lo_deactivate(self, *to_deac, out_diff, _deleted=False):
        """Remove mods and their children from _active_wip."""
        to_deac = {*to_deac} if _deleted else load_order.filter_pinned(
            to_deac, filter_mods=True)
        #--Unselect filenames
        set_awip = set(self._active_wip) - to_deac
        #--Unselect children
        get_dependents = self.dependents.__getitem__
        children = {*chain.from_iterable(map(get_dependents, to_deac))}
        while children:
            child = children.pop()
            if child in set_awip: # else it's already inactive, skip checks
                set_awip.remove(child)
                children |= get_dependents(child)
        # Commit the changes made above
        set_awip = [x for x in self._active_wip if x in set_awip]
        out_diff |= self._diff_los(new_act=set_awip)
        self._active_wip = set_awip

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
            # _CopyToLink might overwrite, not DummyMasters/File_Duplicate
            if new_mod in lwip: lwip.remove(new_mod)
            dex = lwip.index(previous)
            if bush.game.mtime_lo:
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
                    self[new_mod].setmtime(new_time, mark_redated=True)
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

    def create_new_mod(self, mod_fn: str | FName,
            selected: tuple[FName, ...] = (), *,
            wanted_masters: list[FName] | None = None, dir_path=None,
            author_str='', flags_dict=None) -> ModInfo | None:
        """Create a new plugin.

        :param mod_fn: The name the created plugin will have.
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
        newFile = ModFile((dir_path or self.store_dir).join(mod_fn))
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
            new = FNDict([(mod_fn := FName(mod_fn), last_selected)])
            rdata = self.refresh(RefrIn.from_added([mod_fn]), insert_after=new)
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

    def getVersion(self, fileName):
        """Check we have a fileInfo for fileName and call get_version on it."""
        return self[fileName].get_version() if fileName in self else ''

    def getModList(self, showCRC=False, showVersion=True, fileInfo=None,
                   wtxt=False, log_problems=True):
        """Returns mod list as text. If fileInfo is provided will show mod list
        for its masters. Otherwise will show currently loaded mods."""
        #--Setup
        log = bolt.LogFile()
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
                log(f'{bul}xx {mod}')
            log.setHeader(head + _('Masters for %(m_plugin)s:') % {
                'm_plugin': fileInfo})
            present = {x for x in masters_set if x in self}
            if fileInfo.fn_key in self: #--In case is bashed patch (cf getSemiActive)
                present.add(fileInfo.fn_key)
            merged, imported = self.getSemiActive(present)
            all_mods = (masters_set | merged | imported) & set(self)
        else:
            log.setHeader(head + _(u'Active Plugins:'))
            statuses = self.active_statuses
            all_mods = {*chain.from_iterable(statuses.values())}
            masters_set, merged = statuses[ST_ACTIVE], statuses[ST_MERGED]
        all_mods = load_order.get_ordered(all_mods)
        #--List
        modIndex = 0
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
        return log.out.getvalue()

    def getTagList(self, mod_list=None):
        """Return the list as wtxt of current bash tags (but don't say which
        ones are applied via a patch) - either for all mods in the data folder
        or if specified for one specific mod."""
        tags_list = [f'=== {_("Current Bash Tags:")}', _(
            'Note: Sources are processed from top to bottom, meaning that '
            'lower-ranking sources override higher-ranking ones.')]
        if mod_list is None:
            mod_list = []
            # sort output by load order
            for __mname, modInfo in dict_sort(self, key_f=(
                    lambda k: load_order.cached_lo_index(k))):
                if modInfo.getBashTags():
                    mod_list.append(modInfo)
        for modInfo in mod_list:
            tags_list.append(f'\n* {modInfo}')
            modInfo.tagsies(tags_list)
        tags_list.append('')
        return '\n'.join(tags_list)

    def masterWithVersion(self, master_name):
        if master_name == 'Oblivion.esm' and (curr_ver := self.voCurrent):
            master_name += f' [{curr_ver}]'
        return master_name

    #--Oblivion 1.1/SI Swapping -----------------------------------------------
    def try_set_version(self, set_version, *, do_swap=None):
        """Set Oblivion version to specified one - dry run if do_swap is None,
        else do_swap must be an askYes callback. Our caches must be fresh from
        refresh to detect versions properly."""
        curr_ver = self.voCurrent # may be None if Oblivion.esm size is unknown
        master_esm = self._master_esm # Oblivion.esm, say it's currently SI one
        # rename Oblivion.esm to this, for instance: Oblivion_SI.esm
        move_to = FName(f'{(fnb := master_esm.fn_body)}_{curr_ver}.esm')
        can_set = (set_version and curr_ver and set_version != curr_ver and
                   set_version in self._voAvailable and not (
                        move_to in self or move_to in self.corrupted))
        if not do_swap: return can_set # we can/can't swap
        ren_data = RefrData()
        if not can_set:
            return ren_data
        # Swap Oblivion.esm to specified version - do_swap is askYes callback
        # if new version=='1.1' then copy_from==FName(Oblivion_1.1.esm)
        copy_from = FName(f'{fnb}_{set_version}.esm')
        swapped_inf = self[copy_from]
        swapping_a_ghost = swapped_inf.is_ghost # will ghost the master esm!
        #--Rename
        baseInfo = self[master_esm]
        mt = {master_esm: baseInfo.ftime}
        try:
            inf_target = [(baseInfo, move_to), (swapped_inf, master_esm)]
            # set mtimes to previous respective values
            ren_data |= self.rename_operation(inf_target, set_mtime={**mt,
              move_to: swapped_inf.ftime}, try_once=do_swap, with_backups=True)
        except CancelError:
            pass
        finally:
            if master_esm not in self:
                ren_data |= self.rename_operation([(self[move_to],
                    master_esm)], set_mtime=mt, with_backups=True)
            if swapping_a_ghost: # we need to unghost the master esm
                self[master_esm].setGhost(False)
        return ren_data

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
class SaveInfos(_AFileInfos):
    """SaveInfo collection. Represents save directory and related info."""
    _bain_notify = tracks_ownership = False
    _ess_skips = bush.game.Ess.save_skips
    # Enabled and disabled saves and .bak files
    _known_cor_saves = set()
    factory_type = SaveInfo
    _files_str = _('Save files')

    def __init__(self):
        all_ext = {*(fe := SaveInfo.file_exts), *(f'{e}f' for e in fe)}
        par = partial(self.check_filename, _allow_ext=all_ext)
        SaveInfo.cosave_types = cosaves.get_cosave_types(bush.game.fsName, par,
            bush.game.Se.cosave_tag, bush.game.Se.cosave_ext)
        super().__init__()
        # Save Profiles database
        self.profiles = bolt.PickleDict(
            dirs['saveBase'].join('BashProfiles.dat'), load_pickle=True)
        # save profiles used to have a trailing slash, remove it if present
        for row in [r for r in self.profiles.pickled_data if r.endswith('\\')]:
            self.rename_profile(row, row[:-1])

    def set_store_dir(self, save_dir=None, do_swap=None, rd_out=None):
        """If save_dir is None, read the current save profile from
        oblivion.ini file, else update the ini with save_dir."""
        # saveInfos singleton is constructed in InitData after oblivionIni
        prev = getattr(self, 'localSave', None)
        if sp_key := bush.game.Ini.save_profiles_key:
            if save_dir is None:
                save_dir = oblivionIni.getSetting(*sp_key,
                    default=bush.game.Ini.save_prefix).rstrip('\\')
            else:
                # set SLocalSavePath in Oblivion.ini - the latter must exist.
                # Not sure if appending the slash is needed for the game to
                # parse the setting correctly, kept previous behavior
                oblivionIni.saveSetting(*sp_key, value=f'{save_dir}\\')
        else:
            # The game has no INI key for the Saves folder and instead uses a
            # hardcoded folder name
            save_dir = bush.game.Ess.saves_dir
        self.localSave = save_dir
        if (boot := prev is None) or prev != save_dir:
            old = not boot and self.store_dir
            if not boot:
                self.save_pickle() # save current data before setting store_dir
                self.dat_loaded = False
            self.store_dir = sd = dirs['saveBase'].join(env.convert_separators(
                save_dir)) # localSave always has backslashes
            if do_swap:
                # try to swap Oblivion version to memorized version - note that
                # whether we manage or not we don't edit our saved version
                voNew = self.get_profile_attr(save_dir, 'vOblivion', None)
                rd_mods = modInfos.try_set_version(voNew, do_swap=do_swap)
                # now we possibly swapped modding esms, we can swap lo/act info
                # save current plugins into old directory, load plugins from sd
                if load_order.swap(old, sd): # refresh again
                    rd_mods |= modInfos.refresh(False, unlock_lo=True)
                if rd_out is not None:
                    rd_out |= rd_mods
            if not boot: # else in __init__,  calling _init_store right after
                self._init_store(sd)
        return self.store_dir

    def refresh(self, refresh_in, *, booting=False, save_dir=None,
                do_swap=None, rd_out=None, **kwargs):
        if not booting: # else we just called __init__
            self.set_store_dir(save_dir, do_swap, rd_out)
        return super().refresh(refresh_in, booting=booting, **kwargs)

    @classmethod
    def check_filename(cls, fileName, **kwargs):
        """Parse the specified save name into root and extension and return
        them as a tuple. If the save path does not point to a valid save,
        return None instead."""
        if fileName in cls._ess_skips:
            return None
        if sup := super().check_filename(fileName, **kwargs):
            save_root = sup[0] if isinstance(sup, tuple) else next(
                iter(sup)).fn_body
            cs_ext = bush.game.Se.cosave_ext[1:]
            if any(s.lower() == cs_ext for s in save_root.split('.')):
                # Almost certainly not a valid save, had the cosave extension
                # in one of its root parts
                return None
        return sup

    def warning_args(self, multi_warnings, lo_warnings):
        corruptSaves = set(self.corrupted)
        if not corruptSaves <= self._known_cor_saves:
            multi_warnings.append(
                (_('The following save files could not be read. This most '
                   'likely means that they are corrupt.'),
                 corruptSaves - self._known_cor_saves, self))
            self._known_cor_saves |= corruptSaves

    @property
    def bash_dir(self): return self.store_dir.join('Bash')

    def data_path_to_info(self, data_path: str, **kwargs) -> _ListInf:
        return None # Never relative to Data folder

    # SaveInfos Profiles ------------------------------------------------------
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

#------------------------------------------------------------------------------
class BSAInfos(_AFileInfos):
    """BSAInfo collection. Represents bsa files in game's Data directory."""
    # BSAs that have versions other than the one expected for the current game
    mismatched_versions = set()
    # Maps BA2 hashes to BA2 names, used to detect collisions
    ba2_hashes = defaultdict(set)
    ba2_collisions = set()
    _dir_key = 'mods'
    _known_mismatched_version_bsas = set()
    _known_ba2_collisions = set()

    def __init__(self):
        ##: Hack, this should not use display_name
        if bush.game.display_name == 'Oblivion':
            # Need to do this at runtime since it depends on inisettings (ugh)
            bush.game.Bsa.redate_dict[inisettings[
                u'OblivionTexturesBSAName']] = 1104530400 # '2005-01-01'
        _bsa_type = bsa_files.get_bsa_type(bush.game.fsName)
        class BSAInfo(FileInfo, _bsa_type):
            file_exts = frozenset([bush.game.Bsa.bsa_extension])
            def __init__(self, fullpath, **kwargs):
                try:
                    super().__init__(fullpath, **kwargs)
                except BSAError as e:
                    raise FileError(GPath(fullpath).tail,
                        f'{e.__class__.__name__}  {e.message}') from e
                self._reset_bsa_mtime()
                # If the BSA has a mismatched version, schedule a warning
                if bush.game.Bsa.valid_versions and self.inspect_version() \
                        not in bush.game.Bsa.valid_versions:
                    BSAInfos.mismatched_versions.add(self.fn_key)
                self._check_collisions(BSAInfos)
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
        self.__class__.factory_type = BSAInfo
        super().__init__()

    def warning_args(self, multi_warnings, lo_warnings):
        bsa_mvers = self.mismatched_versions
        if not bsa_mvers <= self._known_mismatched_version_bsas:
            m = _('The following BSAs have a version different from the one '
                  '%(game_name)s expects. This can lead to CTDs, please '
                  'extract and repack them using the %(ck_name)s-provided '
                  'tool.') % {'game_name': bush.game.display_name,
                              'ck_name': bush.game.Ck.long_name}
            multi_warnings.append(
                (m, bsa_mvers - self._known_mismatched_version_bsas, self))
            self._known_mismatched_version_bsas |= bsa_mvers
        ba2_colls = self.ba2_collisions
        if not ba2_colls <= self._known_ba2_collisions:
            m = _('The following BA2s have filenames whose hashes collide, '
                  'which will cause one or more of them to fail to work '
                  'correctly. This should be corrected by the mod authors '
                  'by renaming the files to avoid the collision.')
            multi_warnings.append(
                (m, ba2_colls - self._known_ba2_collisions, self))
            self._known_ba2_collisions |= ba2_colls

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
    _ss_skips = {*map(FName, ('enblensmask.png', 'enbpalette.bmp',
        'enbsunsprite.bmp', 'enbsunsprite.tga', 'enbunderwaternoise.bmp'))}
    factory_type = ScreenInfo
    _boot_refresh_args = {}
    tracks_ownership = False
    dat_loaded = True # nothing to load

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
    def check_filename(cls, fileName, **kwargs):
        if FName(fileName) in cls._ss_skips:
            # Some non-screenshot file, skip it
            return None
        return super().check_filename(fileName, **kwargs)

    def data_path_to_info(self, data_path: str, **kwargs) -> _ListInf:
        if not self._bain_notify:
            # Current store_dir is not relative to Data folder, so we do not
            # need to pay attention to BAIN
            return None
        *parts, filename = os.path.split(os.fspath(data_path))
        # The parent directories must match
        if len(parts) != len(self._ci_curr_data_prefix) or any(p != cp for
            p, cp in zip(map(str.lower, parts), self._ci_curr_data_prefix)):
            return None
        return super().data_path_to_info(filename, **kwargs)

    def refresh(self, *args, **kwargs):
        self.set_store_dir()
        return super().refresh(*args, **kwargs)

    def save_pickle(self): pass

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
def initBosh(game_ini_path, game_info):
    # Setup loot_parser, needs to be done after the dirs are initialized
    if not bass.bash_dirs_initialized:
        raise BoltError('initBosh: Bash dirs are not initialized')
    # game ini files
    deprint(f'Looking for main game INI at {game_ini_path}')
    global oblivionIni, gameInis, lootDb
    loot_gname = game_info.loot_dir
    loot_folder = dirs['local_appdata'].join('LOOT')
    # Since LOOT v0.18, games are stored in LOOT\games\<game>, try that first
    loot_path = loot_folder.join('games', loot_gname)
    if not loot_path.is_dir():
        # Fall back to the 'legacy' path (LOOT\<game>)
        loot_path = loot_folder.join(loot_gname)
    loot_master_path = loot_path.join('masterlist.yaml')
    loot_user_path = loot_path.join('userlist.yaml')
    loot_tag_path = dirs['taglists'].join('taglist.yaml')
    lootDb = LOOTParser(loot_master_path, loot_user_path, loot_tag_path)
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
    INIInfos() # iniInfos global is set in __init__
    return modInfos
