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
#  Mopy/bash/games.py copyright (C) 2016 Utumno: Original design
#
# =============================================================================
"""Load order handling backend featuring a LoGame hierarchy implementing base
load order handling, and LoFile hierarchy for reading and writing load order
files. Imported in the game package for defining specific LoGame overrides (to
keep this file readable and avoid the need of a factory), and in load_order.py,
where it is initialized and used to implement the load order API."""
##: multiple backups? fixes can happen in rapid succession, so preserving
# several older files in a directory would be useful (maybe limit to some
# number, e.g. 5 older versions)
from __future__ import annotations

__author__ = 'Utumno'

import re
import time
from collections import defaultdict
from functools import partial
from itertools import chain

from . import bass, bolt, env, exception
from .bolt import AFile, FName, DelFile, Path, deprint, dict_sort
from .ini_files import get_ini_type_and_encoding
from .plugin_types import PluginFlag

# Typing
LoTuple = tuple[FName, ...]
LoList = LoTuple | list[FName] | None
_ParsedLo = tuple[list[FName], list[FName]]

class LoFile(AFile):
    """A file holding load order information (plugins.txt/loadorder.txt but
    also ini files for INIGame). We need to be careful in case sensitive
    file systems and backup could use more work but that's a proud beta."""
    def __init__(self, star, path, *args, **kwargs):
        self._star = star
        super().__init__(self._resolve_case_ambiguity(path), *args, **kwargs)

    def parse_modfile(self, dups_set, *, __re_comment=re.compile(b'^#.*')
                      ) -> _ParsedLo:
        """Parse loadorder.txt and plugins.txt files with or without stars.

        Return two lists which are identical except when _star is True,
        whereupon the second list is the load order while the first the
        active plugins. In all other cases use the first list, which is
        either the list of active mods (when parsing plugins.txt) or the
        load order (when parsing loadorder.txt)."""
        with self.abs_path.open('rb') as ins:
            #--Load Files
            active, modnames, is_active_, existing = [], [], True, set()
            for line in ins:
                modname = __re_comment.sub(b'', line.strip())#b' '.strip()==b''
                if self._star and (is_active_ := modname and modname[0] == 42):
                    modname = modname[1:]  # b'*'[0] == 42
                if modname:
                    # Oblivion/Skyrim saves the plugins.txt file in cp1252
                    # format. It wont accept filenames in any other encoding
                    try:
                        mod_fn = FName(modname.decode(encoding='cp1252'))
                    except UnicodeError:
                        bolt.deprint(f'{modname!r} failed to properly decode')
                        continue
                    if mod_fn.fn_ext == '.ghost':
                        mod_fn = mod_fn.fn_body # Vortex keeps the .ghost ext
                    if mod_fn in existing:
                        ##:(743) we keep the first load order/active state
                        # encountered - test with game
                        dups_set.add(mod_fn)
                        continue
                    existing.add(mod_fn)
                    modnames.append(mod_fn)
                    if is_active_: active.append(mod_fn)
        self.do_update() # update the cache info
        return active, modnames

    @staticmethod
    def _resolve_case_ambiguity(lo_file_path: Path):
        """Third-party tools like LOOT do not all use the same case for
        plugins.txt and loadorder.txt. This method returns the canonical
        path for the specified load order file path and cleans up multiple
        load order files in the same dir by using the one with the newest
        mtime and deleting the older ones."""
        lo_dir, lo_fname = lo_file_path.head, lo_file_path.stail
        matching_paths = [lo_dir.join(t_fname) for t_fname in lo_dir.ilist()
                          if t_fname == lo_fname]
        if len(matching_paths) > 1:
            matching_paths.sort(key=lambda tp: tp.mtime, reverse=True)
            filenames = [p.stail for p in matching_paths]
            bolt.deprint(f'Resolving ambiguous {lo_fname} case (found '
                         f'{filenames}) to newest file ({filenames[0]})')
            for p in matching_paths[1:]:
                try:
                    p.remove()
                except OSError:
                    bolt.deprint(f'Failed to remove {p} while resolving '
                                 f'{lo_fname} ambiguous case', traceback=True)
            return matching_paths[0]
        return matching_paths[0] if matching_paths else lo_file_path

    def write_modfile(self, lord, active):
        try:
            self.__write_plugins(lord, active)
        except OSError:
            env.clear_read_only(self.abs_path)
            self.__write_plugins(lord, active)

    def __write_plugins(self, lord, active):
        active_lookup = frozenset(active) if self._star else ()
        with self.abs_path.open('wb') as out:
            for mod in (self._star and lord) or active:
                # Ok, this seems to work for Oblivion, but not for Skyrim,
                # which seems to refuse to have any non-cp1252 named file in
                # plugins.txt. Even activating through the SkyrimLauncher
                # doesn't work.
                try:
                    star = '*' if mod in active_lookup else ''
                    out.write(f'{star}{mod}\r\n'.encode('cp1252'))
                except UnicodeEncodeError:
                    bolt.deprint(f'{mod} failed to properly encode and was '
                                 f'skipped for inclusion in load order file')

    def upd_on_swap(self, old_dir, new_dir):
        pl_path = self.abs_path
        # Save plugins.txt inside the old (saves) directory
        try: self.fs_copy(self._resolve_case_ambiguity(
            old_dir.join(pl_path.stail)))
        except FileNotFoundError: pass # no plugins.txt to save
        # Move the new plugins.txt here for use
        move = self._resolve_case_ambiguity(new_dir.join(pl_path.stail))
        try: # copy will not change mtime - do_update must detect the change
            move.copyTo(pl_path, set_time=time.time())
            return True
        except FileNotFoundError:
            return False

    def create_backup(self):
        pl_path = self.abs_path
        try:
            self.fs_copy(pl_path.backup)
        except FileNotFoundError:
            bolt.deprint(f'Tried to back up {pl_path}, but it did not exist')
        except OSError:
            bolt.deprint(f'Failed to back up {pl_path}', traceback=True)

class _CCCFile(DelFile, LoFile):
    """CCC files can be in different locations. We also need to keep track of
    their presence."""

    def _reset_cache(self, stat_tuple, **kwargs):
        super()._reset_cache(stat_tuple, **kwargs)
        if not self._deleted:
            _act, self.ccc_contents = self.parse_modfile(set()) # discard dups

class FixInfo(object):
    """Encapsulate info on load order and active lists fixups."""
    def __init__(self):
        self.lo_removed = set()
        self.lo_added = set()
        self.lo_duplicates = set()
        self.lo_reordered = ([], [])
        # active mods corrections
        self.act_removed = set()
        self.act_added = set()
        self.act_duplicates = set()
        self.act_order_differs_from_load_order = []
        self.master_not_active = False
        self.missing_must_be_active = set()
        self.selectedExtra = []
        self.act_header = u''

    def lo_changed(self):
        return bool(self.lo_removed or self.lo_added or self.lo_duplicates or
                    any(self.lo_reordered))

    def act_changed(self):
        return bool(
            self.act_removed or self.act_added or self.act_duplicates or
            self.act_order_differs_from_load_order or self.master_not_active
            or self.missing_must_be_active or self.selectedExtra)

    def lo_deprint(self):
        self._warn_lo()
        self._warn_active()

    def _warn_lo(self):
        if not self.lo_changed(): return
        msg = [_pl(li, f'{at[3:]}: ') for at in ('lo_removed', 'lo_added',
            'lo_duplicates') if (li := getattr(self, at))]
        if any(self.lo_reordered):
            msg.append('reordered:')
            msg.append(_pl(self.lo_reordered[0], 'from: '))
            msg.append(_pl(self.lo_reordered[1], 'to  : '))
        fixed_lo_msg = '\n'.join(msg)
        bolt.deprint(f'Fixed Load Order: {fixed_lo_msg}')

    def _warn_active(self):
        if not self.act_header: return
        msg = [self.act_header]
        if self.act_removed:
            msg.append('Active list contains mods not present in Data '
                       'directory, invalid and/or corrupted:')
            msg.append(', '.join(self.act_removed))
        if self.master_not_active:
            msg.append(f'{self.master_not_active} not present in active mods')
        for path in self.missing_must_be_active:
            msg.append(f'{path} not present in active list while present in '
                       f'Data folder')
        msg.extend(self.act_order_differs_from_load_order)
        if self.selectedExtra:
            msg.append('Active list contains more plugins than allowed - the '
                       'following plugins will be deactivated:')
            msg.append(', '.join(self.selectedExtra))
        if self.act_duplicates:
            msg.append('Removed duplicate entries from active list:')
            msg.append(', '.join(self.act_duplicates))
        bolt.deprint('\n'.join(msg))

class LoGame:
    """API for setting, getting and validating the active plugins and the
    load order (of all plugins) according to the game engine (in principle)."""
    force_load_first: tuple[FName, ...] = () # master_file is added in __init__
    _star = False # whether plugins.txt uses a star to denote an active plugin

    def __init__(self, mod_infos, game_handle, plugins_txt_path: Path, *,
                 plugins_txt_type=LoFile, **kwargs):
        """:type mod_infos: bosh.ModInfos"""
        self._plugins_txt = plugins_txt_type(self._star, plugins_txt_path)
        # this is bosh.modInfos, must be up to date. Heavily used in
        # TimestampGame - keep uses down to a minimum
        self._mod_infos = mod_infos
        self._game_handle = game_handle
        self.__class__.force_load_first = (self._game_handle.master_file,
                                           *self.__class__.force_load_first)
        self.pin_active_state = self.fixed_order_plugins = None
        self._print_lo_paths()

    # API: Get and helpers ----------------------------------------------------
    def get_load_order(self, cached_load_order: LoList,
            cached_active_ordered: LoList, fix_lo) -> tuple[LoTuple, LoTuple]:
        """Get and validate current load order and active plugins information.

        Meant to fetch at once both load order and active plugins
        information as validation usually depends on both. If the load order
        read is invalid (messed up loadorder.txt, game's master redated out
        of order, etc) it will attempt fixing and saving them before returning.
        The caller is responsible for passing a valid cached value in. If you
        pass a cached value for either parameter this value will be returned
        unchanged, possibly validating the other one based on stale data.
        NOTE: modInfos must exist and be up to date for validation."""
        lo, active = self._cached_or_fetch(cached_load_order,
                                           cached_active_ordered, fix_lo)
        # for timestamps we use modInfos so we should not get an invalid
        # load order (except redated master). For text based games however
        # the fetched order could be in whatever state, so get this fixed
        if cached_load_order is not lo:
            self._fix_load_order(lo, fix_lo=fix_lo)
        # having a valid load order we may fix active too if we fetched them
        fixed_active = cached_active_ordered is not active and \
            self._fix_active_plugins(active, lo, fix_lo, on_disc=True)
        self._save_fixed_load_order(fix_lo, fixed_active, lo, active)
        return tuple(lo), tuple(active)

    def _cached_or_fetch(self, cached_load_order, cached_active, fix_lo):
        """Responsible for deciding if cached values are still valid."""
        if cached_active is None or self._plugins_txt.do_update():
            cached_active = self._fetch_active_plugins(fix_lo.act_duplicates)
        return cached_load_order, cached_active

    def _save_fixed_load_order(self, fix_lo, fixed_active, lo, active):
        if fix_lo.lo_changed():
            self._backup_load_order()
            self._persist_load_order(lo, None) # active is not used here

    # Asterisk game overrides -------------------------------------------------
    def _get_force_act(self, *, _reset=False, **kwargs) -> dict[FName, bool]:
        """Get (possibly re/setting) the pinned load order/active state caches
        and return the latter. Called in: LoGame._fix_load_order for setting
        the caches initially and in _fix_active_plugins to force de/activate.
        See also AsteriskGame._cached_or_fetch/_persist_load_order."""
        pinn = self.pin_active_state, self.fixed_order_plugins
        if any(p is None for p in pinn) or _reset:
            self.pin_active_state, self.fixed_order_plugins = \
                self._set_pinned_mods()
        return self.pin_active_state

    def _set_pinned_mods(self):
        """Set the master file(s) that must always be active if present."""
        fo = self.force_load_first = (*self._existing(self.force_load_first),)
        return dict.fromkeys(fo, True), fo

    # API: Set and helpers ----------------------------------------------------
    def set_load_order(self, lord, active, previous_lord=None,
                       previous_active=None, fix_lo=None):
        """Set the load order and/or active plugins (or just validate if
        previous_* are None). The different way each game handles this and how
        it modifies common data structures necessitate that info on previous
        (cached) state be passed in, usually for both active plugins and
        load order. For instance, in the case of asterisk games, plugins.txt
        is the common structure for defining both the global load order and
        which plugins are active. The logic is as follows:
        - at least one of `lord` or `active` must be not None, otherwise no
        much use in calling this function anyway - raise ValueError if not.
        - if lord is not None pass it through _fix_load_order. That might
        change it. If, after fixing it, it is the same as `previous_lord`
        then we won't do anything regarding it (no mtime, loadorder.txt etc).
        - if load order is actually being set we need info on active plugins.
        In case active is None we do need to have previous_active - otherwise
        a ValueError is raised.
        - otherwise we determine if active needs change (for TESIV if
        plugins were deleted we need to rewrite plugins.txt - for asterisk
        games we always need to rewrite the plugins.txt for any load order
        change, as it is stored there)
        - we then validate active plugins against lord or previous_lord - if
        we were not setting the load order we need previous_lord here otherwise
        a ValueError is raised.
        By now we should have a lord and active lists to set, if we are not in
        dry run mode.
        :returns the (possibly fixed) lord and active lists
        """
        if lord is active is None:
            raise ValueError('Load order or active must be not None')
        dry_run = previous_lord is previous_active is None
        if quiet := fix_lo is None: fix_lo = FixInfo() # will be discarded
        if setting_lo := lord is not None:
            # fix the load order - lord is modified in place, hence test below
            self._fix_load_order(lord, fix_lo, not quiet, _saving=True)
            setting_lo = previous_lord != lord
        setting_active = active is not None
        if setting_lo and not setting_active:
            # changing load order - must test if active plugins must change too
            if previous_active is None: # active is None
                raise ValueError(
                    'You must pass info on active when setting load order')
            setting_active = previous_lord is None # we must check active
            if not setting_active: # does active need change due to lo changes?
                prev = set(previous_lord)
                new = set(lord)
                dltd = prev - new
                common = prev & new
                reordered = any(x != y for x, y in
                                zip((x for x in previous_lord if x in common),
                                    (x for x in lord if x in common)))
                setting_active = self._must_update_active(dltd, reordered)
            if setting_active: active = list(previous_active) # active was None
        if setting_active:
            # a load order is needed for all games to validate active against
            if lord is previous_lord is None:
                raise ValueError(
                    u'You need to pass a load order in to set active plugins')
            test = lord if setting_lo else previous_lord
            self._fix_active_plugins(active, test, fix_lo, on_disc=False)
        lord = lord if setting_lo else previous_lord
        active = active if setting_active else previous_active
        if lord is None or active is None: # sanity check
            raise Exception('Returned load order and active must be not None')
        if not dry_run: # else just return the (possibly fixed) lists
            self._persist_if_changed(active, lord, previous_active,
                                     previous_lord)
        return lord, active # return what we set or was previously set

    @classmethod
    def _must_update_active(cls, deleted_plugins, reord_plugins):
        raise NotImplementedError

    # API: Helpers
    def get_lo_files(self) -> list[Path]:
        """Returns the paths of the files used by this game for storing load
        order information."""
        return [self._plugins_txt.abs_path] # base case

    def swap(self, old_dir, new_dir):
        """Save current plugins into oldPath directory and load plugins from
        newPath directory (if present)."""
        return self._plugins_txt.upd_on_swap(old_dir, new_dir)

    # Handle active plugins file (always exists)
    def _fetch_active_plugins(self, dups_set):
        try:
            active, _lo = self._plugins_txt.parse_modfile(dups_set)
            return active
        except FileNotFoundError:
            return []

    def _persist_active_plugins(self, active, lord, *, backup_act=False):
        """Write out whatever file stores the active plugins list."""
        if backup_act:
            self._plugins_txt.create_backup()
        self._plugins_txt.write_modfile(lord, active)
        self._plugins_txt.do_update()

    def _backup_load_order(self):
        pass # timestamps, no file to backup

    # ABSTRACT ----------------------------------------------------------------
    def _persist_load_order(self, lord, active):
        """Persist the fixed lord to disk - will break conflicts for
        timestamp games."""
        raise NotImplementedError(f'{type(self)} does not define '
                                  f'_persist_load_order')

    def _persist_if_changed(self, active, lord, previous_active,
                            previous_lord):
        # Override for fallout4 to write the file once and oblivion to save
        # active only if needed. Both active and lord must not be None.
        raise NotImplementedError

    # VALIDATION --------------------------------------------------------------
    def _fix_load_order(self, lord: list[FName], fix_lo, _mtime_order=True,
                        _saving=False):
        """Fix inconsistencies between given loadorder and actually installed
        mod files as well as impossible load orders. We need a refreshed
        bosh.modInfos reflecting the contents of Data/.

        Called in get_load_order() to fix a newly fetched LO and in
        set_load_order() to check if a load order passed in is valid. Needs
        rethinking as saving load and active should be an atomic operation."""
        if _saving: # we come from set_load_order - maybe move this check?
            fix_lo.lo_duplicates = self._check_for_duplicates(lord)
        old_lord = lord[:]
        # game's master might be out of place (if using timestamps for load
        # ordering or a manually edited loadorder.txt) so move it up
        master_name = self._game_handle.master_file
        # Tracks if fix_lo.lo_reordered needs updating
        lo_order_changed = any(fix_lo.lo_reordered)
        cached_minfs = self._mod_infos
        try:
            mdex = lord.index(master_name)
            if mdex > 0:
                bolt.deprint(f'{master_name} has index {mdex} (must be 0)')
                lord.remove(master_name)
                lord.insert(0, master_name)
                lo_order_changed = True
        except ValueError:
            if master_name not in cached_minfs:
                raise exception.BoltError(
                    f'{master_name} is missing or corrupted')
            fix_lo.lo_added = {master_name}
        # below do not apply to timestamp method (except if we are passed in a
        # saved load order for validation or to restore)
        loadorder_set = set(lord)
        mods_set = set(cached_minfs)
        fix_lo.lo_removed = loadorder_set - mods_set # may remove corrupted mods
        # present in text file, we are supposed to take care of that
        fix_lo.lo_added |= mods_set - loadorder_set
        # Remove non existent plugins from load order
        lord[:] = [x for x in lord if x not in fix_lo.lo_removed]
        ol = lord[:] # take a snapshot used in checking master block reordering
        for mod in fix_lo.lo_added: # Append new plugins to load order
            if mod == master_name:
                lord.insert(0, master_name)
                bolt.deprint(f'{master_name} inserted to Load order')
            else: # append all to the end, even esms, will be reordered below
                lord.append(mod)
        # we need to set the _shipwrecks for sort() - we will force activate in
        # _fix_active_plugins - and repeat the ccc files do_update - ##: avoid?
        self._get_force_act(_reset=bool(fix_lo.lo_added or fix_lo.lo_removed))
        # See if any esm files are loaded below an esp and reorder as necessary
        lord.sort(key=self.lo_sort_key())
        # check if any of the existing mods were moved in/out the master block
        lo_order_changed |= ol != [x for x in lord if x not in fix_lo.lo_added]
        # loaded in _get_force_act - those ones come first
        if (*lord[:len(fo_mods := self.force_load_first)],) != fo_mods:
            fo_set = set(fo_mods)
            lord[:] = [*fo_mods, *(x for x in lord if x not in fo_set)]
            lo_order_changed = True
        if lo_order_changed:
            fix_lo.lo_reordered = old_lord, lord

    def _fix_active_plugins(self, acti, lord, fix_active, on_disc):
        """Always called with a valid load order (in set_load_order lord has
        been already fixed, if called in get_load_order we either fetched and
        validated or we are passed a valid cache)."""
        if not on_disc: # callee is set_load_order - NOTE: this modifies acti!
            fix_active.act_duplicates = self._check_for_duplicates(acti)
        # filter plugins not present in modInfos - this will disable
        # corrupted too! Preserve acti order
        # Throw out files that aren't on disk as well as .esu files, which must
        # never be active
        cached_minfs = self._mod_infos
        acti_filtered = [x for x in acti if x in cached_minfs
                         and x.fn_ext != u'.esu']
        # Use sets to avoid O(n) lookups due to lists
        acti_filtered_set = set(acti_filtered)
        fix_active.act_removed = set(acti) - acti_filtered_set
        # present mods that are always active - noop for AsteriskGame as always
        # active plugins are manually added on getting the load order
        for fn_plugin, isact in self._get_force_act(active=acti_filtered_set).items():
            if isact and fn_plugin not in acti_filtered_set:
                if fn_plugin == self._game_handle.master_file:
                    acti_filtered.insert(0, fn_plugin)
                    acti_filtered_set.add(fn_plugin)
                    fix_active.master_not_active = fn_plugin
                else:
                    fix_active.missing_must_be_active.add(fn_plugin)
        # append missing mods and let _check_active_order place them
        acti_filtered.extend(fix_active.missing_must_be_active)
        # order - won't trigger saving for TimestampGame - affects which mods
        # are chopped off if > 255 (the ones that load last)
        fix_active.act_order_differs_from_load_order = \
            self._check_active_order(acti_filtered, lord)
        # check if we have more than 256 active mods
        disable = self.check_active_limit(acti_filtered)
        # update acti in place - this must always be done, since acti may
        # contain files that are no longer on disk (i.e. not in acti_filtered)
        acti[:] = [x for x in acti_filtered if x not in disable]
        if disable: # chop off extra
            cached_minfs.selectedExtra = fix_active.selectedExtra = [
                x for x in acti_filtered if x in disable]
        if fix_active.act_changed():
            if on_disc: # used when getting active and found invalid, fix 'em!
                # Notify user and backup previous plugins.txt
                fix_active.act_header = 'Invalid Plugin txt corrected:'
                self._persist_active_plugins(acti, lord, backup_act=True)
            else: # active list we passed in when setting load order is invalid
                fix_active.act_header = 'Invalid active plugins list corrected:'
            return True # changes, saved if loading plugins.txt
        return False # no changes, not saved

    # API: Exposed validation helpers - see load_order.py
    def lo_sort_key(self, *, ds=None, by_time=False):
        ds = self._mod_infos if ds is None else ds
        def _key(fn):
            is_m = self._game_handle.master_flags.sort_masters_key(ds[fn],self)
            if by_time:
                is_m = *is_m, ds[fn].ftime
            return is_m
        return _key

    def check_active_limit(self, acti_filtered, *, as_type=set):
        pl_type_active = defaultdict(list)
        limit_flags = {pf: (pf.name.title(), mp) for pf in
            self._game_handle.plugin_flags if (mp := pf.max_plugins)}
        for m in acti_filtered:
            mi = self._mod_infos[m]
            for pflag in limit_flags:
                if pflag.cached_type(mi):
                    pl_type_active[pflag].append(m)
                    break
            else:
                pl_type_active[PluginFlag].append(m)
        limit_flags[PluginFlag] = ('regular', PluginFlag.max_plugins)
        filtered = {f'{mp:d} {type_name} plugins': drop for f, (type_name, mp)
            in limit_flags.items() if (drop := pl_type_active[f][mp:])}
        if as_type is set:
            return set(chain(*filtered.values()))
        if as_type is str:
            return ' and '.join(k for k in filtered)
        raise ValueError(f'Invalid {as_type=}')

    @staticmethod
    def _check_active_order(acti, lord):
        old = acti[:]
        dex_dict = {mod: index for index, mod in enumerate(lord)}
        acti.sort(key=dex_dict.__getitem__)
        if acti != old: # active mods order that disagrees with lord ?
            return [f'Reordered active plugins with fixed order',
                    f'from: ({_pl(old)})', f'to  : ({_pl(acti)})']
        return []

    # HELPERS -----------------------------------------------------------------
    @staticmethod
    def _check_for_duplicates(plugins_list: list[FName]):
        mods, duplicates, j = set(), set(), 0
        mods_add = mods.add
        duplicates_add = duplicates.add
        for i, mod in enumerate(plugins_list[:]):
            if mod in mods:
                del plugins_list[i - j]
                j += 1
                duplicates_add(mod)
            else:
                mods_add(mod)
        return duplicates

    def _existing(self, mods):
        return (x for x in mods if x in self._mod_infos)

    def calculate_mtime_order(self, mods): # excludes mods in corrupted
        # split into master block and not master block then sort by ftime then
        # sort by name upercase descending (for time conflicts) - see
        # https://github.com/Ortham/libloadorder/issues/86#issuecomment-4254218481
        return sorted(sorted(mods, key=str.upper, reverse=True),
                      key=self.lo_sort_key(by_time=True))

    def _print_lo_paths(self):
        """Prints the paths that will be used and what they'll be used for.
        Useful for debugging."""
        acti_lo = self.get_lo_files()
        bolt.deprint('Using the following load order files:')
        if len(acti_lo) == 2 and acti_lo[0] == acti_lo[1]:
            bolt.deprint(f' - Load order and active plugins: {acti_lo[0]}')
        else:
            bolt.deprint(f' - Active plugins: {acti_lo.pop(0)}')
            if acti_lo:
                bolt.deprint(f' - Load order: {acti_lo.pop(0)}')

def _mk_ini(ini_key, star, ini_fpath):
    """Creates a new IniFile from the specified bolt.Path object."""
    # We don't support OBSE INIs here, only regular IniFile objects
    ini_type, ini_encoding = get_ini_type_and_encoding(ini_fpath)
    class _IniLoFile(LoFile, ini_type):
        def __init__(self, ini_key, *args, **kwargs):
            super().__init__(*args, **kwargs)
            _ini, self._section, self._key_fmt = ini_key

        def parse_modfile(self, dups_set=frozenset(), *, __re='') -> _ParsedLo:
            """Read the section specified in self._section and return all
            its values as FName objects. Handles missing INI file and an
            absent section gracefully."""
            # Returned format is dict[FName, tuple[str, int]], we want the
            # unicode (i.e. the mod names)
            section_mapping = self.get_setting_values(self._section, {})
            # Sort by line number, then convert the values to FNames and return
            section_vals = dict_sort(section_mapping, values_dex=[1])
            out = [FName(v[0]) for k, v in section_vals]
            self.do_update() # update the cached info
            return out, out

        def write_modfile(self, lord, active):
            """Write out the lord/active using the section/key format attrs."""
            section_contents = {self._key_fmt % {'lo_idx': i}: lo_mod for
                                i, lo_mod in enumerate(active)}
            # Remove any existing section - also prevents duplicate sections
            # with different case
            self.saveSettings({self._section: section_contents},
                              skip_sections={self._section.lower()})

        def upd_on_swap(self, old_dir, new_dir):
            # If there's no INI inside the old (saves) directory, copy it
            old_ini = self._resolve_case_ambiguity(old_dir.join(ini_key[0]))
            if not old_ini.is_file():
                self.fs_copy(old_ini)
            # Read from the new INI if it exists and write to our main INI
            move_ini = self._resolve_case_ambiguity(new_dir.join(ini_key[0]))
            if move_ini.is_file():
                loact = _mk_ini(ini_key, self._star, move_ini).parse_modfile()
                self.write_modfile(*loact)
                return True
            return False
    return _IniLoFile(ini_key, star, ini_fpath, ini_encoding)

class INIGame(LoGame):
    """Class for games which use an INI section to determine parts of the load
    order. Meant to be used in multiple inheritance with other LoGame types, be
    sure to put INIGame first, so its init runs first in order to initialize
    the plugins txt (currently) as a _IniLoFile instance. It is currently
    used with TimeStampGame and could in principle be used with TextfileGame
    too, but we are not looking forward to that. It can't be used with
    AsteriskGame, makes no sense.

    To use an INI section to specify active plugins, change ini_key_actives.
    To use an INI section to specify load order, change ini_key_lo. You can
    also specify both if the game uses an INI for everything.
    Format for them is (INI Name, section, entry format string).
    The entry format string receives a format argument, %(lo_idx)s, which
    corresponds to the load order position of the mod written as a value.
    For example, (u'test.ini', u'Mods', u'Mod%(lo_idx)s') would result in
    something like this:
        [Mods]
        Mod0=FirstMod.esp
        Mod1=SecondMod.esp"""
    # The INI keys, see class docstring for more info
    ini_key_actives = None
    ini_key_lo = None

    def __init__(self, mod_infos, game_handle, plugins_txt_path, **kwargs):
        """Creates a new INIGame instance. plugins_txt_path does not have to
        be specified if INIGame will manage active plugins."""
        if self.__class__.ini_key_actives:
            plugins_txt_path = self.ini_dir_actives.join(
                self.ini_key_actives[0])
            kwargs['plugins_txt_type'] = partial(_mk_ini, self.ini_key_actives)
        if self.__class__.ini_key_lo:
            kwargs.update({ # we must come just before TextfileGame in the MRO
                'loadorder_txt_path': self.ini_dir_lo.join(self.ini_key_lo[0]),
                'lo_txt_type': partial(_mk_ini, self.ini_key_lo)})
        super().__init__(mod_infos, game_handle, plugins_txt_path, **kwargs)

    # INI directories, override if needed
    @property
    def ini_dir_actives(self) -> Path:
        """Returns the directory containing the actives INI. Defaults to the
        game path."""
        return bass.dirs[u'app']

    @property
    def ini_dir_lo(self) -> Path:
        """Returns the directory containing the load order INI. Defaults to the
        game path."""
        return bass.dirs[u'app']

    # Misc overrides
    @classmethod
    def _must_update_active(cls, deleted_plugins, reord_plugins):
        if cls.ini_key_actives is not None:
            return True # Assume order is important for the INI
        return super()._must_update_active(deleted_plugins, reord_plugins)

def set_mtimes(wanted_lord, current_lord, fnkey_info: dict):
    """Set the mtimes of the mods in current lord to match wanted_lord order.
    set(wanted_lord) == set(current_lord) == mods is assumed."""
    # mods's mtimes match the current lord's order - break conflicts
    mods_it = map(fnkey_info.__getitem__, current_lord)
    older = next(mods_it).ftime # initialize to older mod's ftime
    for info in mods_it:
        # mods_it is ordered in ftime so conflicts come in chunks
        if older == (older := info.ftime):
            # respace this and next mods in 60 sec intervals
            for inf in (info, *mods_it):
                older += 60.0
                inf.setmtime(older, mark_redated=True)
            break
    restamp = []
    # set(wanted_lord) == set(current_lord) - collect modification times
    for ordered, mod in zip(wanted_lord, current_lord, strict=True):
        if ordered != mod:
            restamp.append((ordered, fnkey_info[mod].ftime))
    for ordered, modification_time in restamp:
        fnkey_info[ordered].setmtime(modification_time)

class TimestampGame(LoGame):
    """Oblivion and other games where load order is set using modification
    times."""

    @staticmethod
    def _check_active_order(acti, lord):
        super(TimestampGame, TimestampGame)._check_active_order(acti, lord)
        return [] # no need to reorder plugins.txt - fix_lo.act_reordered False

    @classmethod
    def _must_update_active(cls, deleted_plugins, reord_plugins):
        return deleted_plugins

    # Abstract overrides ------------------------------------------------------
    def _cached_or_fetch(self, *args):
        _lo, act = super()._cached_or_fetch(*args)
        # ignore cached - we could patch fix_load_order to do minimal work here
        return self.calculate_mtime_order(self._mod_infos), act

    def _persist_load_order(self, lord, active):
        current = self.calculate_mtime_order(modinfos := self._mod_infos)
        set_mtimes(lord, current, modinfos)

    def _persist_if_changed(self, active, lord, previous_active,
                            previous_lord):
        if previous_lord is None or previous_lord != lord:
            self._persist_load_order(lord, active)
        if previous_active is None or set(previous_active) != set(active):
            self._persist_active_plugins(active, lord)

    # Other overrides ---------------------------------------------------------
    def _fix_load_order(self, lord, fix_lo, _mtime_order=True, _saving=False):
        """If _mtime_order is True, the load order will be sorted by mtime -
        previous behavior (see clients) but may not be what we want in all
        cases."""
        super()._fix_load_order(lord, fix_lo, _saving=_saving)
        if _mtime_order and fix_lo.lo_added:
            lord[:] = self.calculate_mtime_order(mods=lord)

class _TextFileLo(LoGame):
    """Common code for games that use a text file to store the load order."""

    def _backup_load_order(self):
        """This method should make a backup of whatever file is storing the
        load order plugins list."""
        self.get_lo_file().create_backup()

    def get_lo_file(self): # AsteriskGame - has a single lo/actives file
        return self._plugins_txt

    def get_lo_files(self):
        return [*super().get_lo_files(), self.get_lo_file().abs_path]

class TextfileGame(_TextFileLo):
    # If True, the game master (e.g. Skyrim.esm) must never be written to
    # plugins.txt
    _remove_game_master_from_plugins_txt = True

    def __init__(self, mod_infos, game_handle, plugins_txt_path,
                 loadorder_txt_path: Path, *, lo_txt_type=LoFile, **kwargs):
        self._loadorder_txt = lo_txt_type(self._star, loadorder_txt_path)
        super().__init__(mod_infos, game_handle, plugins_txt_path, **kwargs)

    @classmethod
    def _must_update_active(cls, deleted_plugins, reord_plugins):
        return deleted_plugins or reord_plugins

    def swap(self, old_dir, new_dir):
        swapped_pl = super().swap(old_dir, new_dir)
        return self._loadorder_txt.upd_on_swap(old_dir, new_dir) or swapped_pl

    def get_lo_file(self):
        return self._loadorder_txt

    # Abstract overrides ------------------------------------------------------
    def _cached_or_fetch(self, cached_load_order, cached_active, fix_lo):
        """Read data from loadorder.txt file. If loadorder.txt does not
        exist create it and use cached/plugins.txt info so the load order of
        the user is preserved (note it will create the plugins.txt if not
        existing). Additional mods should be added by caller who should
        anyway call _fix_load_order. The relative order of mods will be
        corrected to match their relative order in active returned by super."""
        _lo, act = super()._cached_or_fetch(cached_load_order, cached_active,
                                            fix_lo)
        pl_changed = cached_active is not act # we fetched or requested update
        lo_changed = (pl_changed or cached_load_order is None or
                      self._loadorder_txt.do_update())
        if not lo_changed:
            return cached_load_order, act
        pl_path = self._plugins_txt.abs_path
        try: #--Read file
            _acti, lo = self._loadorder_txt.parse_modfile(fix_lo.lo_duplicates)
        except FileNotFoundError:
            if not pl_path.exists():
                self._persist_active_plugins(act, act)
                bolt.deprint(f'Created {pl_path} based on cached info')
            self._persist_load_order(act, act)
            bolt.deprint(f'Created {self._loadorder_txt.abs_path}')
            return act, act
        if not pl_changed:
            # then the desync might be intentional keep loadorder.txt order
            return lo, act
        # handle desync with plugins txt
        lo_dex = {x: i for i, x in enumerate(lo)}
        # drop mods in plugins.txt, but not in loadorder.txt; we'll check
        # if it's really missing in _fix_active_plugins ##:(743) what about missing
        # from lo - those would be added last (although maybe added to
        # plugins.txt from the game and reordered already by the user)
        cached_active_copy = [m for m in act if m in lo_dex]
        cached_active_set = set(act)
        active_in_lo = [x for x in lo if x in cached_active_set]
        while active_in_lo:
            # Use list(), we may modify cached_active_copy and active_in_lo
            for i, (ordered, current) in list(enumerate(
                    zip(cached_active_copy, active_in_lo))):
                if ordered != current:
                    for j, x in enumerate(active_in_lo[i:]):
                        if x == ordered: break
                        # x should be above ordered
                        to = lo_dex[ordered] + 1 + j
                        # make room
                        lo_dex = {k: (i if i < to else i + 1) for k, i in
                                  lo_dex.items()}
                        lo_dex[x] = to  # bubble them up !
                    active_in_lo.remove(ordered)
                    cached_active_copy = cached_active_copy[i + 1:]
                    active_in_lo = active_in_lo[i:]
                    break
            else: break
        fetched_lo = lo[:]
        lo.sort(key=lo_dex.get)
        if lo != fetched_lo:
            # We fixed a desync, make a backup and write the load order
            self._backup_load_order()
            self._persist_load_order(lo, lo)
            bolt.deprint(f'Corrected {self._loadorder_txt.abs_path} '
                f'(order of mods differed from their order in {pl_path})')
        return lo, act

    def _fetch_active_plugins(self, dups_set):
        """Fetch what's in the plugins.txt - if something shouldn't be there,
        remove it and rewrite the plugins.txt."""
        act = super()._fetch_active_plugins(dups_set)
        if self._game_handle.master_file in act:
            if self._remove_game_master_from_plugins_txt:
                bolt.deprint(f'Removing {self._game_handle.master_file} from '
                             f'{self._plugins_txt.abs_path}')
                act = self._persist_active_plugins(act, act, backup_act=True)
            else:
                # Game master already in active and should not be removed
                return act
        # Prepend the game master - should be present and is always active
        return [self._game_handle.master_file, *act]

    def _persist_load_order(self, lord, active):
        self._loadorder_txt.write_modfile(lord, lord)
        self._loadorder_txt.do_update()

    def _persist_active_plugins(self, active, lord, **kw):
        if self._remove_game_master_from_plugins_txt:
            active = [x for x in active if x != self._game_handle.master_file]
        super()._persist_active_plugins(active, active, **kw)
        return active

    def _persist_if_changed(self, active, lord, previous_active,
                            previous_lord):
        if previous_lord is None or previous_lord != lord:
            self._persist_load_order(lord, active)
        if previous_active is None or previous_active != active:
            self._persist_active_plugins(active, lord)

class AsteriskGame(_TextFileLo):
    """_TextFileLo storing also active state in the lo file - active plugins
    are marked with a star."""
    # Creation Club content file - if empty, indicates that this game has no CC
    _ccc_filename = u''
    # Hardcoded list used if the file specified above does not exist or could
    # not be read
    _ccc_fallback = ()
    _star = True
    _ccc_dirs = 'app',

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        paths = (bass.dirs[d].join(self._ccc_filename) for d in
                 self._ccc_dirs) if self._ccc_filename else ()
        self.__cc_files = {p: _CCCFile(False, p) for p in paths}

    def _cached_or_fetch(self, ca_load_order, ca_active, fix_lo):
        """Read data from plugins.txt file once. If plugins.txt does not exist
        create it. Will *always* fetch both load order and active."""
        chs = ca_load_order, ca_active
        if not (any(a is None for a in chs) or self._plugins_txt.do_update()):
            return chs
        try:
            active, lo = self._plugins_txt.parse_modfile(fix_lo.lo_duplicates)
            rem_from_acti = self._get_force_act(active=active)
            if any_dropped := [x for x in lo if x in rem_from_acti]:
                bolt.deprint(f'Removing {_pl(any_dropped)} from '
                             f'{self._plugins_txt.abs_path}')
                # We removed plugins that don't belong here, back up first
                lo, active = self._persist_load_order(lo, active,
                    backup_act=True, rem_from_acti=rem_from_acti)
            self._readd_mods(lo, active, self.force_load_first)
        except FileNotFoundError:
            # Create it if it doesn't exist - we could use sorted_rem but
            # those are removed in _persist_load_order
            self._persist_load_order(lo := [*(ca_load_order or [])],
                                     active := [*(ca_active or [])])
            bolt.deprint(f'Created {self._plugins_txt.abs_path}')
        return lo, active

    def _get_force_act(self, **kwargs):
        fload_set = {*(fload := self.__class__.force_load_first)}
        for ccc_file in self.__cc_files.values():
            try:
                ccc_file.do_update(raise_os_error=True)
                fload = (*fload, *(m for m in ccc_file.ccc_contents if
                                   m not in fload_set))
                break # first ccc file found
            except OSError as e:
                if ccc_file.has_changed: # freshly deleted or not found
                    if isinstance(e, FileNotFoundError):
                        deprint(f'{ccc_file.abs_path} does not exist')
                    else:
                        deprint(f'Failed to open {ccc_file.abs_path}',
                                traceback=True)
                    ccc_file.has_changed = False # deprint the first time only
        if (fload := (*self._existing(fload),)) != self.force_load_first:
            self.force_load_first = fload
            kwargs['_reset'] = True
        return super()._get_force_act(**kwargs)

    def _readd_mods(self, lo, active, sorted_rem):
        # Prepend all present fixed-order plugins that can't be in the
        # plugins txt to the active and lord lists
        lo[:] = [*sorted_rem, *lo]
        active[:] = [*sorted_rem, *active]

    @classmethod
    def _must_update_active(cls, deleted_plugins, reord_plugins): return True

    # Abstract overrides ------------------------------------------------------
    def _fetch_active_plugins(self, *args) -> list[FName]:
        raise NotImplementedError # only used in super._cached_or_fetch

    def _persist_active_plugins(self, active, lord, *,
                                rem_from_acti=None, **kwargs):
        rem_from_acti = self._get_force_act(active=active) \
            if rem_from_acti is None else rem_from_acti
        lord = [x for x in lord if x not in rem_from_acti]
        active = [x for x in active if x not in rem_from_acti]
        super()._persist_active_plugins(active, lord, **kwargs)
        return lord, active

    def _persist_load_order(self, lord, active, **kwargs):
        return self._persist_active_plugins(active, lord, **kwargs)

    def _save_fixed_load_order(self, fix_lo, fixed_active, lo, active):
        if fixed_active: return # plugins.txt already saved
        if fix_lo.lo_changed():
            self._backup_load_order()
            self._persist_load_order(lo, active)

    def _persist_if_changed(self, active, lord, previous_active,
                            previous_lord):
        if (previous_lord is None or previous_lord != lord) or (
                previous_active is None or previous_active != active):
            self._persist_load_order(lord, active)

    def _set_pinned_mods(self):
        mbaip, fo_mods = super()._set_pinned_mods() # set(fo_mods) == mbaip
        # first put the force_load_first then the ccc contents (minus the mods
        # already in force_load_first), then whatever remains in _ccc_fallback
        return mbaip, (*fo_mods, *self._existing( # still set(fo_mods) == mbaip
            p for p in self._ccc_fallback if p not in mbaip))

# Print helpers
def _pl(it, legend=''):
    return legend + ', '.join(it)
