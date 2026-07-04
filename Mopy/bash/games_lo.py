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
LoList = list[FName]
ParsedLo = tuple[LoList, LoList]

class LoFile(AFile):
    """A file holding load order information (plugins.txt/loadorder.txt but
    also ini files for INIGame). We need to be careful in case sensitive
    file systems and backup could use more work but that's a proud beta."""
    def __init__(self, star, path, *args, **kwargs):
        self._star = star
        super().__init__(self._resolve_case_ambiguity(path), *args, **kwargs)

    def parse_modfile(self, dups_set, *, __re_comment=re.compile(b'^#.*')):
        """Parse loadorder.txt and plugins.txt files with or without stars.

        Return two lists when _star is True, whereupon the second list is
        the load order while the first the active plugins, else a single list,
        which is either the list of active mods (when parsing plugins.txt) or
        the load order (when parsing loadorder.txt)."""
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
        return (active, modnames) if self._star else (active,)

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

    def write_modfile(self, *args, mark_unchanged=True, backup_file=False):
        apath = self.abs_path
        if backup_file:
            try:
                self.fs_copy(apath.backup)
            except FileNotFoundError:
                bolt.deprint(f'Tried to back up {apath}, but it did not exist')
            except OSError:
                bolt.deprint(f'Failed to back up {apath}', traceback=True)
        try:
            self.__write_plugins(*args)
        except OSError:
            env.clear_read_only(apath)
            self.__write_plugins(*args)
        if mark_unchanged:
            self.do_update()

    def __write_plugins(self, active, lord=None):
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

class _CCCFile(DelFile, LoFile):
    """CCC files can be in different locations. We also need to keep track of
    their presence."""

    def _reset_cache(self, stat_tuple, **kwargs):
        super()._reset_cache(stat_tuple, **kwargs)
        if not self._deleted:
            self.ccc_contents, = self.parse_modfile(set()) # discard dups

class _FixInfo:
    """Encapsulate info on load order and active lists fixups."""
    def __init__(self):
        self.lo_removed = set()
        self.lo_added = set()
        self.lo_duplicates = set()
        self.lo_reordered = ([], [])
        self.do_save_lo = ''
        # active mods corrections
        self.act_removed = set()
        self.act_added = set()
        self.act_duplicates = set()
        self.act_order_differs_from_load_order = []
        self.master_not_active = False
        self.missing_must_be_active = set()
        self.selectedExtra = []
        self.act_header = u''
        self.do_save_act = ''

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
            msg.append(f'{self.master_not_active} not active')
        for path in self.missing_must_be_active:
            msg.append(f'{path} not active while present in Data folder')
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
    force_load_first: LoTuple = () # master_file dynamically added in __init__
    _star = False # whether plugins.txt uses a star to denote an active plugin
    _order_active = False # match order of active plugins with load order
    _creating = _FixInfo() # sentinel - creating a LoFile (_filter_plugins_txt)

    def __init__(self, plugins_txt_path: Path, game_handle, mod_infos,
                 exit_on_boot=False, *, plugins_txt_type=LoFile, **kwargs):
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
        self._exit_on_boot_error = exit_on_boot

    # API: Get and helpers ----------------------------------------------------
    def get_load_order(self, cached_load_order: LoTuple | None,
                       cached_active_ordered: LoTuple | None, rdata_mods,
                       booting) -> ParsedLo:
        """Get and validate current load order and active plugins information.

        ***Only*** called in ModInfos.refresh to fetch load order and active
        plugins information, as validation usually depends on both. If the
        load order/plugins.txt read are invalid (messed up loadorder.txt,
        game's master redated out of order, etc) it will attempt fixing and
        saving them before returning. The caller is responsible for passing
        a valid cached value in, else you risk validating the other one based
        on stale data. NOTE: modInfos must be up to date for validation."""
        self._exit_on_boot_error = self._exit_on_boot_error and booting
        active, lo = self._cached_or_fetch(cached_active_ordered,
            cached_load_order, fix_lo=(fix_lo := _FixInfo()),
            rdata_mods=rdata_mods)
        # for timestamps we use modInfos so we should not get an invalid
        # load order (except redated master). For text based games however
        # the fetched order could be in whatever state, so get this fixed
        if cached_load_order is not lo:
            self._fix_load_order(lo, fix_lo=fix_lo)
        # having a valid load order we may fix active too if we fetched them
        if cached_active_ordered is not active:
            # since we fetched active keep plugins.txt order - else the desync
            # might be intentional (keep loadorder.txt order). Note that we
            # fetched lo in TextfileGame._cached_or_fetch, so lo is fixed
            if self._order_active:
                self._handle_desync(active, lo, self._plugins_txt.abs_path,
                                    fix_lo)
            self._fix_active_plugins(active, lo, fix_lo, False)
        elif (self._order_active and fix_lo.lo_reordered) or rdata_mods.redraw:
            # sync order of plugins.txt with lo
            self._check_active_order(active := list(active), lo, fix_lo)
            if rdata_mods.redraw: # plugin flag changed? - check active limits
                self.check_active_limit(active, filter_list=active,
                                        fix_active=fix_lo)
        savact = None if fix_lo.act_changed() or fix_lo.do_save_act else active
        savlo = None if fix_lo.lo_changed() or fix_lo.do_save_lo else lo
        self._persist_if_changed(lo, savlo, active, savact, fixlo=fix_lo)
        for msg in fix_lo.do_save_lo, fix_lo.do_save_act:
            if msg: bolt.deprint(msg)
        fix_lo.lo_deprint()
        return [*lo], [*active]

    def _cached_or_fetch(self, cached_active, cached_load_order, *, fix_lo,
                         rdata_mods=None, dups=None):
        """Responsible for deciding if cached values are still valid."""
        if (dups is not None or cached_active is None or
                self._plugins_txt.do_update()): # returns True also on deletion
            parsed, fix_lo = self._try_read(fix_lo, dups=dups)
            if parsed is None:
                parsed = cached_active, cached_load_order
            return self._filter_plugins_txt(*parsed, fix_lo=fix_lo)
        return cached_active,

    def _filter_plugins_txt(self, active, *args, fix_lo=None):
        if fix_lo is self._creating: # used also for loadorder.txt creation
            active = [*(active or self._get_force_act())]
        return active,

    # Asterisk game overrides -------------------------------------------------
    def _get_force_act(self, *, _reset=False, **kwargs) -> dict[FName, bool]:
        """Get (possibly re/setting) the pinned load order/active state caches
        and return the latter. Called in: LoGame._fix_load_order for setting
        the caches initially and in _fix_active_plugins to force de/activate.
        Also used in LoGame/Timestamp _filter_plugins_txt (hacky, we exploit
        the fact that for all but Asterisk (that overrides _filter_plugins_txt)
        [*pin_active_state] == [*fixed_order_plugins])."""
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
    def set_load_order(self, lord: LoList | None, active: LoList | None,
                       previous_cache: ParsedLo | None = None):
        """Set the load order and/or active plugins (or just validate, if
        previous_cache is None). The different way each game handles this and
        how it modifies common data structures necessitate that info on
        previous (cached) state be passed in, usually for both active
        plugins and load order. For instance, in the case of asterisk games,
        plugins.txt is the common structure for defining both the global
        load order and which plugins are active. The logic is as follows:
        1. at least one of `lord` or `active` must be not None, otherwise no
        much use in calling this function anyway - raise ValueError if not.
        2. if any of `lord` or `active` is None, you must pass previous_cache
        3. if lord is not None pass it through _fix_load_order. That might
        change it. If, after fixing it, it is the same as `previous_lord`
        then we won't do anything regarding it (no mtime, loadorder.txt etc).
        4. if load order is actually being set we need info on active plugins.
        In case active is None we do need to have previous_active - see 2.
        We then determine if active needs change (for TESIV if plugins were
        deleted we need to rewrite plugins.txt - for asterisk games we
        always need to rewrite the plugins.txt for any load order change,
        as it is stored there)
        5. we then validate active plugins against lord or previous_lord - if
        we were not setting the load order we need previous_lord here - see 2.
        By now we should have a lord and active lists to set, if we are not in
        dry run mode.
        :returns the (possibly fixed) lord and active lists
        """
        if lord is active is None:
            raise ValueError('Load order or active must be not None')
        previous_lord, previous_act = (None, None) if (
            dry_run := previous_cache is None) else previous_cache
        fix_lo = _FixInfo()
        if lord is not None:
            # fix the load order - lord is modified in place, hence test below
            self._fix_load_order(lord, fix_lo, _saving=True)
            if not dry_run and previous_lord != lord and active is None:
                # changing load order - test if active plugins must change too
                if self._must_update_active(lord, previous_lord):
                    active = [*previous_act] # copy for _fix_active_plugins
        else:
            lord = previous_lord
        if active is not None:
            # a load order is needed for all games to validate active against
            self._fix_active_plugins(active, lord, fix_lo, True)
        else:
            active = previous_act
        if not dry_run: # else just return the (possibly fixed) lists
            self._persist_if_changed(lord, previous_lord, active, previous_act)
        return lord, active, fix_lo # return what we set or was previously set

    @classmethod
    def _must_update_active(cls, lord, previous_lord):
        if (prev := set(previous_lord)) - (new := set(lord)):
            return True # files were deleted
        if not cls._order_active:
            return False
        common = prev & new
        return any(x != y for x, y in zip((x for x in lord if x in common),
            (x for x in previous_lord if x in common))) # reordered

    def _persist_if_changed(self, lord: LoList, previous_lord, active: LoList,
                            previous_active, fixlo=None):
        # Write plugins.txt - all but AsteriskGame override to write load order
        if previous_active is None or ((previous_active != active) if
                self._order_active else (set(previous_active) != set(active))):
            self._plugins_txt.write_modfile(*self._filter_plugins_txt(
                active, lord), backup_file=fixlo is not None and not
                    fixlo.do_save_act.startswith('Created'))

    # VALIDATION --------------------------------------------------------------
    def _fix_load_order(self, lord: LoList, fix_lo, _saving=False):
        """Fix inconsistencies between given loadorder and actually installed
        mod files as well as impossible load orders. We need a refreshed
        bosh.modInfos reflecting the contents of Data/.

        Called in get_load_order() to fix a newly fetched LO and in
        set_load_order() to check if a load order passed in is valid. Needs
        rethinking as saving load and active should be an atomic operation."""
        if _saving: # we come from set_load_order - maybe move this check?
            fix_lo.lo_duplicates = self._check_for_duplicates(lord)
        deduplicated = lord[:]
        # game's master might be out of place (if using timestamps for load
        # ordering or a manually edited loadorder.txt) so move it up
        master_name = self._game_handle.master_file
        cached_minfs = self._mod_infos
        try:
            mdex = lord.index(master_name)
        except ValueError:
            if master_name not in cached_minfs:
                raise exception.BoltError(
                    f'{master_name} is missing or corrupted')
            bolt.deprint(f'{master_name} inserted to Load order')
            lord.insert(0, master_name)
        else:
            if mdex > 0:
                bolt.deprint(f'{master_name} has index {mdex} (must be 0)')
                del lord[mdex] # remove master name
                lord.insert(0, master_name)
            master_name = None
        # below do not apply to timestamp method (except if we are passed in a
        # saved load order for validation or to restore)
        if not (mtimelo := isinstance(self, TimestampGame)) or _saving:
            loadorder_set = set(lord)
            mods_set = set(cached_minfs)
            # may remove corrupted mods present in text file
            fix_lo.lo_removed = loadorder_set - mods_set
            # Remove non existent plugins from load order
            lord[:] = [x for x in lord if x not in fix_lo.lo_removed]
            fix_lo.lo_added |= mods_set - loadorder_set
            if mtimelo: # _saving is True then
                self._add_last(lord, fix_lo.lo_added)
            else: # append all to the end, even esms, will be reordered below
                lord.extend(fix_lo.lo_added)
        if master_name is not None: fix_lo.lo_added.add(master_name)
        # we need to set the _shipwrecks for sort() - we will force activate in
        # _fix_active_plugins - and repeat the ccc files do_update - ##: avoid?
        self._get_force_act(_reset=bool(fix_lo.lo_added or fix_lo.lo_removed))
        # See if any esm files are loaded below an esp and reorder as necessary
        lord.sort(key=self.lo_sort_key())
        # loaded in _get_force_act - those ones come first
        if (*lord[:len(fo_mods := self.force_load_first)],) != fo_mods:
            fo_set = set(fo_mods)
            lord[:] = [*fo_mods, *(x for x in lord if x not in fo_set)]
            ord_change = True
        else: # check if any existing mod was moved in/out the master block
            ord_change = [x for x in deduplicated if x not in fix_lo.lo_removed
                ] != [x for x in lord if x not in fix_lo.lo_added]
        if ord_change:
            fix_lo.lo_reordered = deduplicated, lord

    def _fix_active_plugins(self, acti, lord, fix_active: _FixInfo, _saving):
        """Always called with a valid load order (in set_load_order lord has
        been already fixed, if called in get_load_order we either fetched and
        validated or we are passed a valid cache)."""
        if _saving: # callee is set_load_order - NOTE: this modifies acti!
            fix_active.act_duplicates = self._check_for_duplicates(acti)
        # Throw out files that aren't on disk, newly 'corrupted' files as
        # well as .esu files, which must never be active. Preserve acti order
        acti_filtered = [x for x in acti if x in self._mod_infos and
                         x.fn_ext != '.esu' or fix_active.act_removed.add(x)]
        # Use sets to avoid O(n) lookups due to lists
        acti_filtered_set = set(acti_filtered)
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
        self._check_active_order(acti_filtered, lord, fix_active)
        # check if we have more than 256 active mods
        self.check_active_limit(acti_filtered, filter_list=acti,
                                fix_active=fix_active)
        if fix_active.act_changed():
            fix_active.act_header = 'Invalid active plugins list corrected:' \
                if _saving else 'Invalid Plugin txt corrected:'

    # API: Exposed validation helpers - see load_order.py
    def lo_sort_key(self, *, ds=None, by_time=False):
        ds = self._mod_infos if ds is None else ds
        smk = self._game_handle.master_flags.sort_masters_key
        return (lambda fn: (*smk(ds[fn], self), ds[fn].ftime)) if by_time \
            else lambda fn: smk(ds[fn], self)

    def check_active_limit(self, acti_filtered, *, filter_list=None,
                           fix_active=None):
        pl_type_active, cached_minfs = defaultdict(list), self._mod_infos
        limit_flags = {pf: (pf.name.title(), max_num) for pf in
            self._game_handle.plugin_flags if (max_num := pf.max_plugins)}
        for m in acti_filtered:
            mi = cached_minfs[m]
            for pflag in limit_flags:
                if pflag.cached_type(mi):
                    pl_type_active[pflag].append(m)
                    break
            else:
                pl_type_active[PluginFlag].append(m)
        limit_flags[PluginFlag] = ('regular', PluginFlag.max_plugins)
        filtered = {f'{max_num:d} {type_name} plugins': to_disable
            for f, (type_name, max_num) in limit_flags.items() if (
                to_disable := pl_type_active[f][max_num:])}
        if (abort := self._exit_on_boot_error) or filter_list is None:
            if (msg := ' and '.join(k for k in filtered)) and abort:
                raise exception.LoadOrderBootError(f'More than {msg} are '
                    f'active. Disable some and restart')
            if filter_list is None: return msg
        # update filter_list in place - this must always be done, since it may
        # contain files that are no longer on disk (i.e. not in acti_filtered)
        filtered = set(chain(*filtered.values()))
        filter_list[:] = [x for x in acti_filtered if x not in filtered]
        if fix_active is not None and filtered:  # chop off extra
            cached_minfs.selectedExtra = fix_active.selectedExtra = [
                x for x in acti_filtered if x in filtered]
        return filtered

    def _check_active_order(self, acti, lord, fix_active: _FixInfo):
        old = acti[:] if self._order_active else acti
        dex_dict = {mod: index for index, mod in enumerate(lord)}
        acti.sort(key=dex_dict.__getitem__)
        if acti != old: # active mods order that disagrees with lord ?
            fix_active.act_order_differs_from_load_order = [
                f'Reordered active plugins', f'from: ({_pl(old)})',
                f'to  : ({_pl(acti)})']

    # API: Helpers
    def get_lo_files(self) -> list[Path]:
        """Returns the paths of the files used by this game for storing load
        order information."""
        return [self._plugins_txt.abs_path] # base case

    def swap(self, old_dir, new_dir):
        """Save current plugins into oldPath directory and load plugins from
        newPath directory (if present)."""
        return self._plugins_txt.upd_on_swap(old_dir, new_dir)

    # HELPERS -----------------------------------------------------------------
    @staticmethod
    def _check_for_duplicates(plugins_list: LoList):
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

    def _calculate_mtime_order(self, mods): # excludes mods in corrupted
        # split into master block and not master block then sort by ftime then
        # sort by name upercase descending (for time conflicts) - see
        # https://github.com/Ortham/libloadorder/issues/86#issuecomment-4254218481
        return sorted(sorted(mods, key=str.upper, reverse=True),
                      key=self.lo_sort_key(by_time=True))

    def _try_read(self, fix_lo, lo_file=None, dups=None):
        lo_file = self._plugins_txt if (is_plug:= lo_file is None) else lo_file
        dups = fix_lo.act_duplicates if dups is None else dups
        try:
            return lo_file.parse_modfile(dups), fix_lo
        except FileNotFoundError:
            create = f'Created {lo_file.abs_path} based on cached info'
            setattr(fix_lo, 'do_save_act' if is_plug else 'do_save_lo', create)
            return None, self._creating

    def _handle_desync(self, act, lo, pl_path, fix_lo):
        # handle desync with plugins txt - lo is fixed at this point
        lo_dex = {x: i for i, x in enumerate(lo)}
        # drop mods in plugins.txt, but not in loadorder.txt; they should be
        # really missing at this point as `lo` is fixed while act is not
        cached_active_copy = [m for m in act if m in lo_dex]
        cached_active_set = set(act)
        active_in_lo = [x for x in lo if x in cached_active_set]
        while active_in_lo:
            # Use list(), we may modify cached_active_copy and active_in_lo
            for i, (ordered, current) in list(
                    enumerate(zip(cached_active_copy, active_in_lo))):
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
            else:
                break
        fetched_lo = lo[:]
        lo.sort(key=lo_dex.get)
        if lo != fetched_lo:
            fix_lo.do_save_lo = (f'Corrected {self.get_lo_files()[1]} '
                f'(order of mods differed from their order in {pl_path})')

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
        def __init__(self, ini_key_tup, *args, **kwargs):
            super().__init__(*args, **kwargs)
            _ini, self._section, self._key_fmt = ini_key_tup

        def parse_modfile(self, dups_set=frozenset(), *, __re='') -> ParsedLo:
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

        def write_modfile(self, *args, mark_unchanged=True, **kwargs):
            """Write out the lord/active using the section/key format attrs."""
            section_contents = {self._key_fmt % {'lo_idx': i}: lo_mod for
                                i, lo_mod in enumerate(args[0])}
            # Remove any existing section - also prevents duplicate sections
            # with different case
            self.saveSettings({self._section: section_contents},
                              skip_sections={self._section.lower()})
            if mark_unchanged:
                self.do_update()

        def upd_on_swap(self, old_dir, new_dir):
            # If there's no INI inside the old (saves) directory, copy it
            old_ini = self._resolve_case_ambiguity(old_dir.join(ini_key[0]))
            if not old_ini.is_file():
                self.fs_copy(old_ini)
            # Read from the new INI if it exists and write to our main INI
            move_ini = self._resolve_case_ambiguity(new_dir.join(ini_key[0]))
            if move_ini.is_file():
                loact = _mk_ini(ini_key, self._star, move_ini).parse_modfile()
                self.write_modfile(*loact, mark_unchanged=False)
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

    def __init__(self, plugins_txt_path, *args, **kwargs):
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
        super().__init__(plugins_txt_path, *args, **kwargs)

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

    @classmethod
    def _must_update_active(cls, *args):
        if cls.ini_key_actives is not None:
            return True # Assume order is important for the INI
        return super()._must_update_active(*args)

class TimestampGame(LoGame):
    """Oblivion and other games where load order is set using modification
    times."""

    def _cached_or_fetch(self, *args, rdata_mods, **kwargs):
        act, = super()._cached_or_fetch(*args, **kwargs)
        lord = self._calculate_mtime_order(self._mod_infos)
        self._add_last(lord, rdata_mods.to_add)
        return act, lord

    def _persist_if_changed(self, lord, previous_lord, *args, **kwargs):
        if previous_lord is None or previous_lord != lord:
            self._set_mtimes(lord)
        super()._persist_if_changed(lord, previous_lord, *args, **kwargs)

    def _add_last(self, lord, added):
        if added:
            lo_new = [] # if added mods are present in lord keep relative order
            # rdata.to_add are already present in lord, fix_lo.lo_added are not
            old = (m for m in lord if m not in added or ( # on boot to_add=lord
                    lo_new.append(m) or added.remove(m)))
            lo_new = [*old, *lo_new, *self._calculate_mtime_order(added)]
            lo_new.sort(key=self.lo_sort_key()) # sort added master files first
            self._set_mtimes(lo_new)
            lord[:] = lo_new

    def _set_mtimes(self, wanted_lord):
        """Set the mtimes of the mods in self._mod_infos to match wanted_lord
        order. If set(wanted_lord) != set(modInfos) a ValueError is raised."""
        current_lord = self._calculate_mtime_order(modinfos := self._mod_infos)
        # mods's mtimes match the current lord's order - break conflicts
        mods_it = map(modinfos.__getitem__, current_lord)
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
                restamp.append((ordered, modinfos[mod].ftime))
        for ordered, modification_time in restamp:
            modinfos[ordered].setmtime(modification_time)

class TextfileGame(LoGame):
    # If True, the game master (e.g. Skyrim.esm) must never be written to
    # plugins.txt
    _remove_game_master_from_plugins_txt = True
    _order_active = True # Skyrim, Enderal, ORE

    def __init__(self, *args, loadorder_txt_path: Path, lo_txt_type=LoFile,
                 **kwargs):
        self._loadorder_txt = lo_txt_type(self._star, loadorder_txt_path)
        super().__init__(*args, **kwargs)

    def _cached_or_fetch(self, cached_active, cached_load_order, *, fix_lo,
                         **kwargs):
        """Read data from loadorder.txt file. If loadorder.txt does not exist
        request creating it and use cached/plugins.txt info so the load order
        of the user is preserved (note super will request creating plugins.txt
        if not existing). Additional mods should be added by caller who should
        anyway call _fix_load_order. The relative order of mods will be
        corrected to match their relative order in active returned by super."""
        act, = super()._cached_or_fetch(cached_active, cached_load_order,
                                        fix_lo=fix_lo, **kwargs)
        pl_changed = cached_active is not act # we fetched or requested update
        lo_changed = (pl_changed or cached_load_order is None or
                      self._loadorder_txt.do_update())
        if not lo_changed:
            return act, cached_load_order # note act is the cached one here too
        parsed, fix_lo = self._try_read(fix_lo, self._loadorder_txt,
                                        dups=fix_lo.lo_duplicates)
        if parsed is None:
            parsed = self._filter_plugins_txt(cached_load_order, fix_lo=fix_lo)
        return act, *parsed

    def _filter_plugins_txt(self, active, *args, fix_lo=None):
        if fix_lo is self._creating: # pinn_active_state == fixed_order_plugins
            return super()._filter_plugins_txt(active, fix_lo=fix_lo)
        if self._remove_game_master_from_plugins_txt:
            try:
                mas_index = active.index(mf := self._game_handle.master_file)
                if fix_lo is not None:
                    fix_lo.do_save_act = (f'Removed {mf} from '
                                          f'{self._plugins_txt.abs_path}')
                else:
                    del active[mas_index]
            except ValueError:
                # Prepend the game master - should be present and always active
                if fix_lo is not None:
                    active = [self._game_handle.master_file, *active]
        return active,

    def _persist_if_changed(self, lord, previous_lord, *args, fixlo=None):
        if previous_lord is None or previous_lord != lord:
            self._loadorder_txt.write_modfile(lord, backup_file=fixlo is not
                None and not fixlo.do_save_lo.startswith('Created'))
        super()._persist_if_changed(lord, previous_lord, *args, fixlo=fixlo)

    def swap(self, old_dir, new_dir):
        swapped_pl = super().swap(old_dir, new_dir)
        return self._loadorder_txt.upd_on_swap(old_dir, new_dir) or swapped_pl

    def get_lo_files(self):
        return [*super().get_lo_files(), self._loadorder_txt.abs_path]

class AsteriskGame(LoGame):
    """Stores active state in the lo file - active plugins are marked with a
    star."""
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

    def _cached_or_fetch(self, *chs, fix_lo, **kwargs):
        """Read data from plugins.txt file once. If plugins.txt does not exist
        create it. Will *always* fetch both load order and active."""
        if not (any(a is None for a in chs) or self._plugins_txt.do_update()):
            return chs
        return super()._cached_or_fetch(*chs, dups=fix_lo.lo_duplicates,
                                        fix_lo=fix_lo, **kwargs)

    def _filter_plugins_txt(self, active, lord, *, fix_lo=None):
        rem_from_acti = self._get_force_act(active=active)
        if fix_lo is self._creating:
            # keep cached version or populate with fixed order/always active
            return [*(lord or self.fixed_order_plugins)], [*(
                active or (k for k, v in self.pin_active_state.items() if v))]
        getting = fix_lo is not None
        if any_dropped := [x for x in lord if x in rem_from_acti]:
            lord = [x for x in lord if x not in rem_from_acti]
            active = [x for x in active if x not in rem_from_acti]
            if getting: fix_lo.do_save_lo = (f'Removed {_pl(any_dropped)} '
                f'from {self._plugins_txt.abs_path}')
        if getting:
            self._readd_mods(lord, active, self.force_load_first)
        return active, lord

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

    def _set_pinned_mods(self):
        mbaip, fo_mods = super()._set_pinned_mods() # set(fo_mods) == mbaip
        # first put the force_load_first then the ccc contents (minus the mods
        # already in force_load_first), then whatever remains in _ccc_fallback
        return mbaip, (*fo_mods, *self._existing( # still set(fo_mods) == mbaip
            p for p in self._ccc_fallback if p not in mbaip))

    def _readd_mods(self, lo, active, sorted_rem):
        # Prepend all present fixed-order plugins that can't be in the
        # plugins txt to the active and lord lists
        lo[:] = [*sorted_rem, *lo]
        active[:] = [*sorted_rem, *active]

    @classmethod
    def _must_update_active(cls, *args): return True

    def _persist_if_changed(self, lord, previous_lord, active, previous_active,
                            **kwargs):
        if previous_lord is None or previous_lord != lord:
            previous_active = None # force write the plugins.txt
        super()._persist_if_changed(lord, previous_lord, active,
                                    previous_active, **kwargs)

    def get_lo_files(self):
        return [*super().get_lo_files()] * 2

# Print helpers
def _pl(it, legend=''):
    return legend + ', '.join(it)
