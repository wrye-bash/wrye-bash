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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#  Mopy/bash/games.py copyright (C) 2016 Utumno: Original design
#
# =============================================================================
"""Game class implementing load order handling - **only** imported in
load_order.py."""
##: multiple backups? fixes can happen in rapid succession, so preserving
# several older files in a directory would be useful (maybe limit to some
# number, e.g. 5 older versions)

__author__ = u'Utumno'

import re
import time
from collections import defaultdict, OrderedDict

# Local
from . import bass, bolt, env, exception
from .bolt import GPath_no_norm, dict_sort
from .ini_files import get_ini_type_and_encoding

def _write_plugins_txt_(path, lord, active, _star):
    try:
        with path.open(u'wb') as out:
            __write_plugins(out, lord, active, _star)
    except OSError:
        env.clear_read_only(path)
        with path.open(u'wb') as out:
            __write_plugins(out, lord, active, _star)

def __write_plugins(out, lord, active, _star):
    def asterisk(active_set=frozenset(active)):
        return b'*' if _star and (mod in active_set) else b''
    for mod in (_star and lord) or active:
        # Ok, this seems to work for Oblivion, but not Skyrim
        # Skyrim seems to refuse to have any non-cp1252 named file in
        # plugins.txt.  Even activating through the SkyrimLauncher
        # doesn't work.
        try:
            out.write(asterisk() + bolt.encode(mod.s, firstEncoding=u'cp1252'))
            out.write(b'\r\n')
        except UnicodeEncodeError:
            bolt.deprint(u'%s failed to properly encode and was not '
                         u'included in plugins.txt' % mod)

_re_plugins_txt_comment = re.compile(b'^#.*')
def _parse_plugins_txt_(path, mod_infos, _star):
    """Parse loadorder.txt and plugins.txt files with or without stars.

    Return two lists which are identical except when _star is True, whereupon
    the second list is the load order while the first the active plugins. In
    all other cases use the first list, which is either the list of active
    mods (when parsing plugins.txt) or the load order (when parsing
    loadorder.txt)
    :type path: bolt.Path
    :type mod_infos: bosh.ModInfos
    :type _star: bool
    :rtype: (list[bolt.Path], list[bolt.Path])
    """
    with path.open(u'rb') as ins:
        #--Load Files
        active, modnames = [], []
        for line in ins:
            # Oblivion/Skyrim saves the plugins.txt file in cp1252 format
            # It wont accept filenames in any other encoding
            modname = _re_plugins_txt_comment.sub(b'', line.strip())
            if not modname: continue
            # use raw strings below
            is_active_ = not _star or modname.startswith(b'*')
            if _star and is_active_: modname = modname[1:]
            try:
                test = bolt.decoder(modname, encoding=u'cp1252')
            except UnicodeError:
                bolt.deprint(f'{modname!r} failed to properly decode')
                continue
            mod_g_path = GPath_no_norm(test)
            if mod_g_path not in mod_infos: # TODO(ut): is this really needed??
                # The automatic encoding detector could have returned
                # an encoding it actually wasn't.  Luckily, we
                # have a way to double check: modInfos.data
                for encoding in bolt.encodingOrder:
                    try:
                        test2 = str(modname, encoding)
                        mod_gpath_2 = GPath_no_norm(test2)
                        if mod_gpath_2 in mod_infos:
                            mod_g_path = mod_gpath_2
                            break
                    except UnicodeError:
                        pass
            modnames.append(mod_g_path)
            if is_active_: active.append(mod_g_path)
    return active, modnames

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
        self.act_reordered = ()
        self.act_order_differs_from_load_order = u''
        self.master_not_active = False
        self.missing_must_be_active = []
        self.selectedExtra = []
        self.act_header = u''

    def lo_changed(self):
        return bool(self.lo_removed or self.lo_added or self.lo_duplicates or
                    any(self.lo_reordered))

    def act_changed(self):
        return bool(
            self.act_removed or self.act_added or self.act_duplicates or
            self.act_reordered or self.act_order_differs_from_load_order or
            self.master_not_active or self.missing_must_be_active)

    def lo_deprint(self):
        self.warn_lo()
        self.warn_active()

    def warn_lo(self):
        if not self.lo_changed(): return
        added = _pl(self.lo_added) or u'None'
        removed = _pl(self.lo_removed) or u'None'
        duplicates = f'lo_duplicates({_pl(self.lo_duplicates)}), ' \
            if self.lo_duplicates else u''
        reordered = u'(No)' if not any(self.lo_reordered) else _pl(
            self.lo_reordered[0], u'from:\n', joint=u'\n') + _pl(
            self.lo_reordered[1], u'\nto:\n', joint=u'\n')
        bolt.deprint(f'Fixed Load Order: added({added}), removed({removed}), '
                     f'{duplicates}reordered {reordered}')

    def warn_active(self):
        if not self.act_header: return
        msg = self.act_header
        if self.act_removed:
            msg += u'Active list contains mods not present in Data/ ' \
                   u'directory, invalid and/or corrupted: '
            msg += _pl(self.act_removed) + u'\n'
        if self.master_not_active:
            msg += f'{self.master_not_active} not present in active mods\n'
        for path in self.missing_must_be_active:
            msg += (u'%s not present in active list while present in Data '
                    u'folder' % path) + u'\n'
        msg += self.act_order_differs_from_load_order
        if self.selectedExtra:
            msg += u'Active list contains more plugins than allowed' \
                   u' - the following plugins will be deactivated: '
            msg += _pl(self.selectedExtra)
        if self.act_duplicates:
            msg += u'Removed duplicate entries from active list : '
            msg += _pl(self.act_duplicates)
        if len(self.act_reordered) == 2: # from, to
            msg += u'Reordered active plugins with fixed order '
            msg += _pl(self.act_reordered[0], u'from:\n', joint=u'\n')
            msg += _pl(self.act_reordered[1], u'\nto:\n', joint=u'\n')
        bolt.deprint(msg)

class Game(object):
    """API for setting, getting and validating the active plugins and the
    load order (of all plugins) according to the game engine (in principle)."""
    allow_deactivate_master = False
    must_be_active_if_present = ()
    max_espms = 255
    max_esls = 0
    # If set to False, indicates that this game has no plugins.txt. Currently
    # only allows swap() to be a sentinel method for multiple inheritance,
    # everything else has to be handled through overrides
    # TODO(inf) Refactor  Game to use this value and raise AbstractExceptions
    #  when it's False
    has_plugins_txt = True
    _star = False # whether plugins.txt uses a star to denote an active plugin

    def __init__(self, mod_infos, plugins_txt_path):
        super(Game, self).__init__()
        self.plugins_txt_path = plugins_txt_path # type: bolt.Path
        self.mod_infos = mod_infos # this is bosh.ModInfos, must be up to date
        self.master_path = mod_infos.masterName # type: bolt.Path
        self.mtime_plugins_txt = 0.0
        self.size_plugins_txt = 0

    def _plugins_txt_modified(self):
        exists = self.plugins_txt_path.exists()
        if not exists and self.mtime_plugins_txt: return True # deleted !
        return exists and ((self.size_plugins_txt, self.mtime_plugins_txt) !=
                           self.plugins_txt_path.size_mtime())

    # API ---------------------------------------------------------------------
    def get_load_order(self, cached_load_order, cached_active_ordered,
                       fix_lo=None):
        """Get and validate current load order and active plugins information.

        Meant to fetch at once both load order and active plugins
        information as validation usually depends on both. If the load order
        read is invalid (messed up loadorder.txt, game's master redated out
        of order, etc) it will attempt fixing and saving them before returning.
        The caller is responsible for passing a valid cached value in. If you
        pass a cached value for either parameter this value will be returned
        unchanged, possibly validating the other one based on stale data.
        NOTE: modInfos must exist and be up to date for validation.
        :type cached_load_order: tuple[bolt.Path]
        :type cached_active_ordered: tuple[bolt.Path]
        :rtype: (tuple[bolt.Path], tuple[bolt.Path])
        """
        if cached_load_order is not None and cached_active_ordered is not None:
            return cached_load_order, cached_active_ordered # NOOP
        lo, active = self._cached_or_fetch(cached_load_order,
                                           cached_active_ordered)
        # for timestamps we use modInfos so we should not get an invalid
        # load order (except redated master). For text based games however
        # the fetched order could be in whatever state, so get this fixed
        if cached_load_order is None: ##: if not should we assert is valid ?
            self._fix_load_order(lo, fix_lo=fix_lo)
        # having a valid load order we may fix active too if we fetched them
        fixed_active = cached_active_ordered is None and \
          self._fix_active_plugins(active, lo, on_disc=True, fix_active=fix_lo)
        self._save_fixed_load_order(fix_lo, fixed_active, lo, active)
        return tuple(lo), tuple(active)

    def _cached_or_fetch(self, cached_load_order, cached_active):
        # we need to override this bit for fallout4 to parse the file once
        if cached_active is None: # first get active plugins
            cached_active = self._fetch_active_plugins()
        # we need active plugins fetched to check for desync in load order
        if cached_load_order is None:
            cached_load_order = self._fetch_load_order(cached_load_order,
                                                       cached_active)
        return list(cached_load_order), list(cached_active)

    def _save_fixed_load_order(self, fix_lo, fixed_active, lo, active):
        if fix_lo.lo_changed():
            self._backup_load_order()
            self._persist_load_order(lo, None) # active is not used here

    def set_load_order(self, lord, active, previous_lord=None,
                       previous_active=None, dry_run=False, fix_lo=None):
        """Set the load order and/or active plugins (or just validate if
        dry_run is True). The different way each game handles this and how
        it modifies common data structures necessitate that info on previous
        (cached) state is passed in, usually for both active plugins and
        load order. For instance, in the case of asterisk games plugins.txt
        is the common structure for defining both the global load order and
        which plugins are active). The logic is as follows:
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
            raise ValueError(u'Load order or active must be not None')
        setting_lo = lord is not None
        setting_active = active is not None
        if setting_lo:
            # fix the load order - lord is modified in place, hence test below
            self._fix_load_order(lord, fix_lo=fix_lo)
        setting_lo = setting_lo and previous_lord != lord
        if setting_lo and not setting_active:
            # changing load order - must test if active plugins must change too
            if previous_active is None: # active is None
                raise ValueError(
                    u'You must pass info on active when setting load order')
            setting_active = previous_lord is None # we must check active
            if not setting_active: # does active need change due to lo changes?
                prev = set(previous_lord)
                new = set(lord)
                deleted = prev - new
                common = prev & new
                reordered = any(x != y for x, y in
                                zip((x for x in previous_lord if x in common),
                                    (x for x in lord if x in common)))
                setting_active = self._must_update_active(deleted, reordered)
            if setting_active: active = list(previous_active) # active was None
        if setting_active:
            if lord is previous_lord is None:
                raise ValueError(
                    u'You need to pass a load order in to set active plugins')
            # a load order is needed for all games to validate active against
            test = lord if setting_lo else previous_lord
            self._fix_active_plugins(active, test, on_disc=False,
                                     fix_active=fix_lo)
        lord = lord if setting_lo else previous_lord
        active = active if setting_active else previous_active
        if lord is  None or active is  None: # sanity check
            raise Exception(u'Returned load order and active must be not None')
        if not dry_run: # else just return the (possibly fixed) lists
            self._persist_if_changed(active, lord, previous_active,
                                     previous_lord)
        return lord, active # return what was set or was previously set

    def _active_entries_to_remove(self):
        """Returns a set of plugin names that should not be written into the LO
        file that stores active plugins."""
        return {self.master_path}

    def pinned_mods(self):
        """Returns a set of plugin names that may not be reordered by the
        user."""
        return {self.master_path}

    # Conflicts - only for timestamp games
    def has_load_order_conflict(self, mod_name): return False
    def has_load_order_conflict_active(self, mod_name, active): return False
    # force installation last - only for timestamp games
    def get_free_time(self, start_time, end_time=None):
        raise exception.AbstractError

    @classmethod
    def _must_update_active(cls, deleted, reordered):
        raise exception.AbstractError

    def active_changed(self): return self._plugins_txt_modified()

    def load_order_changed(self): return True # timestamps, just calculate it

    # Swap plugins and loadorder txt
    def swap(self, old_dir, new_dir):
        """Save current plugins into oldPath directory and load plugins from
        newPath directory (if present)."""
        # If this game has no plugins.txt, don't try to swap it
        if not self.__class__.has_plugins_txt: return
        # Save plugins.txt inside the old (saves) directory
        if self.plugins_txt_path.exists():
            self.plugins_txt_path.copyTo(old_dir.join(u'plugins.txt'))
        # Move the new plugins.txt here for use
        move = new_dir.join(u'plugins.txt')
        if move.exists():
            move.copyTo(self.plugins_txt_path)
            self.plugins_txt_path.mtime = time.time() # copy will not change mtime, bad

    def in_master_block(self, minf): # minf is a master or mod info
        """Return true for files that load in the masters' block."""
        return minf.has_esm_flag()

    # ABSTRACT ----------------------------------------------------------------
    def _backup_active_plugins(self):
        """This method should make a backup of whatever file is storing the
        active plugins list."""
        raise exception.AbstractError

    def _backup_load_order(self):
        """This method should make a backup of whatever file is storing the
        load order plugins list."""
        raise exception.AbstractError

    def _fetch_load_order(self, cached_load_order, cached_active):
        """:type cached_load_order: tuple[bolt.Path] | None
        :type cached_active: tuple[bolt.Path]"""
        raise exception.AbstractError

    def _fetch_active_plugins(self): # no override for AsteriskGame
        """:rtype: list[bolt.Path]"""
        raise exception.AbstractError

    def _persist_load_order(self, lord, active):
        """Persist the fixed lord to disk - will break conflicts for
        timestamp games."""
        raise exception.AbstractError

    def _persist_active_plugins(self, active, lord):
        raise exception.AbstractError

    def _persist_if_changed(self, active, lord, previous_active,
                            previous_lord):
        # Override for fallout4 to write the file once and oblivion to save
        # active only if needed. Both active and lord must not be None.
        raise exception.AbstractError

    # MODFILES PARSING --------------------------------------------------------
    def _parse_modfile(self, path):
        """:rtype: (list[bolt.Path], list[bolt.Path])"""
        if not path.exists(): return [], []
        #--Read file
        acti, _lo = _parse_plugins_txt_(path, self.mod_infos, _star=self._star)
        return acti, _lo

    def _write_modfile(self, path, lord, active):
        _write_plugins_txt_(path, lord, active, _star=self._star)

    # PLUGINS TXT -------------------------------------------------------------
    def _parse_plugins_txt(self):
        """:rtype: (list[bolt.Path], list[bolt.Path])"""
        if not self.plugins_txt_path.exists(): return [], []
        #--Read file
        acti, _lo = self._parse_modfile(self.plugins_txt_path)
        self.__update_plugins_txt_cache_info()
        return acti, _lo

    def _write_plugins_txt(self, lord, active):
        self._write_modfile(self.plugins_txt_path, lord, active)
        self.__update_plugins_txt_cache_info()

    def _filter_actives(self, active, rem_from_acti):
        """Removes entries that are not supposed to be in the actives file."""
        return [x for x in active if x not in rem_from_acti]

    def _clean_actives(self, active, lord): # LO matters only for AsteriskGame
        """Removes all plugins from the actives file that should not be there,
        then returns the actives order with such plugins in the right spot."""
        rem_from_acti = self._active_entries_to_remove()
        active_filtered = self._filter_actives(active, rem_from_acti)
        active_dropped = set(active) - set(active_filtered)
        if active_dropped:
            bolt.deprint(f'Removed {sorted(active_dropped)} from '
                         f'{self.get_acti_file()}')
            # We removed plugins that don't belong here, back up first
            self._backup_active_plugins()
            self._persist_active_plugins(active_filtered, active_filtered)
        # Prepend all fixed-order plugins that can't be in the actives plugins
        # list to the actives
        sorted_rem = [x for x in self._fixed_order_plugins()
                      if x in rem_from_acti]
        return sorted_rem + active_filtered, lord

    def __update_plugins_txt_cache_info(self):
        self.size_plugins_txt, self.mtime_plugins_txt = \
            self.plugins_txt_path.size_mtime()

    def get_acti_file(self):
        """Returns the path of the file used by this game for storing active
        plugins.

        :rtype: bolt.Path"""
        return None # base case

    def get_lo_file(self):
        """Returns the path of the file used by this game for storing load
        order.

        :rtype: bolt.Path"""
        return None # base case

    def _set_acti_file(self, new_acti_file):
        """Sets the path of the file used by this game for storing active
        plugins."""
        pass # base case

    def _set_lo_file(self, new_lo_file):
        """Sets the path of the file used by this game for storing load
        order."""
        pass # base case

    # VALIDATION --------------------------------------------------------------
    def _fix_load_order(self, lord, fix_lo):
        """Fix inconsistencies between given loadorder and actually installed
        mod files as well as impossible load orders. We need a refreshed
        bosh.modInfos reflecting the contents of Data/.

        Called in get_load_order() to fix a newly fetched LO and in
        set_load_order() to check if a load order passed in is valid. Needs
        rethinking as save load and active should be an atomic operation -
        leads to hacks (like the _selected parameter).
        :type lord: list[bolt.Path]
        """
        if fix_lo is None: fix_lo = FixInfo() # discard fix info
        old_lord = lord[:]
        # game's master might be out of place (if using timestamps for load
        # ordering or a manually edited loadorder.txt) so move it up
        master_name = self.master_path
        master_dex = 0
        # Tracks if fix_lo.lo_reordered needs updating
        lo_order_changed = any(fix_lo.lo_reordered)
        cached_minfs = self.mod_infos
        try:
            master_dex = lord.index(master_name)
        except ValueError:
            if not master_name in cached_minfs:
                raise exception.BoltError(
                    f'{master_name} is missing or corrupted')
            fix_lo.lo_added = {master_name}
        if master_dex > 0:
            bolt.deprint(f'{master_name} has index {master_dex} (must be 0)')
            lord.remove(master_name)
            lord.insert(0, master_name)
            lo_order_changed = True
        # below do not apply to timestamp method (on getting it)
        loadorder_set = set(lord)
        mods_set = set(cached_minfs)
        fix_lo.lo_removed = loadorder_set - mods_set # may remove corrupted mods
        # present in text file, we are supposed to take care of that
        fix_lo.lo_added |= mods_set - loadorder_set
        # Remove non existent plugins from load order
        lord[:] = [x for x in lord if x not in fix_lo.lo_removed]
        # See if any esm files are loaded below an esp and reorder as necessary
        ol = lord[:]
        in_mblock = self.in_master_block
        lord.sort(key=lambda m: not in_mblock(cached_minfs[m]))
        lo_order_changed |= ol != lord
        if fix_lo.lo_added:
            # Append new plugins to load order
            index_first_esp = self._index_of_first_esp(lord)
            for mod in fix_lo.lo_added:
                if in_mblock(cached_minfs[mod]):
                    if not mod == master_name:
                        lord.insert(index_first_esp, mod)
                    else:
                        lord.insert(0, master_name)
                        bolt.deprint(u'%s inserted to Load order' %
                                     master_name)
                    index_first_esp += 1
                else: lord.append(mod)
        # end textfile get
        fix_lo.lo_duplicates = self._check_for_duplicates(lord)
        lo_order_changed |= self._order_fixed(lord)
        if lo_order_changed:
            fix_lo.lo_reordered = old_lord, lord

    def _fix_active_plugins(self, acti, lord, on_disc, fix_active):
        # filter plugins not present in modInfos - this will disable
        # corrupted too! Preserve acti order
        quiet = fix_active is None
        if quiet: fix_active = FixInfo() # discard fix info
        # Throw out files that aren't on disk as well as .esu files, which must
        # never be active
        cached_minfs = self.mod_infos
        acti_filtered = [x for x in acti if x in cached_minfs
                         and x.cext != u'.esu']
        # Use sets to avoid O(n) lookups due to lists
        acti_filtered_set = set(acti_filtered)
        lord_set = set(lord)
        fix_active.act_removed = set(acti) - acti_filtered_set
        if fix_active.act_removed and not quiet:
            # take note as we may need to rewrite plugins txt
            cached_minfs.selectedBad = fix_active.lo_removed
        if not self.allow_deactivate_master:
            if self.master_path not in acti_filtered_set:
                acti_filtered.insert(0, self.master_path)
                acti_filtered_set.add(self.master_path)
                fix_active.master_not_active = self.master_path
        for path in self.must_be_active_if_present:
            if path in lord_set and path not in acti_filtered_set:
                fix_active.missing_must_be_active.append(path)
        # order - affects which mods are chopped off if > 255 (the ones that
        # load last) - won't trigger saving but for Skyrim
        fix_active.act_order_differs_from_load_order += \
            self._check_active_order(acti_filtered, lord)
        for path in fix_active.missing_must_be_active: # insert after the last master
            acti_filtered.insert(self._index_of_first_esp(acti_filtered), path)
        # Check for duplicates - NOTE: this modifies acti_filtered!
        fix_active.act_duplicates = self._check_for_duplicates(acti_filtered)
        # check if we have more than 256 active mods
        drop_espms, drop_esls = self.check_active_limit(acti_filtered)
        disable = drop_espms | drop_esls
        # update acti in place - this must always be done, since acti may
        # contain files that are no longer on disk (i.e. not in acti_filtered)
        acti[:] = [x for x in acti_filtered if x not in disable]
        if disable: # chop off extra
            cached_minfs.selectedExtra = fix_active.selectedExtra = [
                x for x in acti_filtered if x in disable]
        before_reorder = acti # with overflowed plugins removed
        if self._order_fixed(acti):
            fix_active.act_reordered = (before_reorder, acti)
        if fix_active.act_changed():
            if on_disc: # used when getting active and found invalid, fix 'em!
                # Notify user and backup previous plugins.txt
                fix_active.act_header = u'Invalid Plugin txt corrected:\n'
                self._backup_active_plugins()
                self._persist_active_plugins(acti, lord)
            else: # active list we passed in when setting load order is invalid
                fix_active.act_header = u'Invalid active plugins list corrected:\n'
            return True # changes, saved if loading plugins.txt
        return False # no changes, not saved

    def check_active_limit(self, acti_filtered):
        return set(acti_filtered[self.max_espms:]), set()

    def _fixed_order_plugins(self):
        """Returns a list of plugins that must have the order they have in this
        list. The list may only contain plugins that are actually present in
        the Data folder."""
        fixed_ord = [x for x in self.must_be_active_if_present
                     if x in self.mod_infos]
        return [self.master_path] + fixed_ord

    def _order_fixed(self, lord):
        fixed_order = self._fixed_order_plugins()
        if not fixed_order: return False # nothing to do
        fixed_order_set = set(fixed_order)
        filtered_lo = [x for x in lord if x not in fixed_order_set]
        lo_with_fixed = fixed_order + filtered_lo
        if lord != lo_with_fixed:
            lord[:] = lo_with_fixed
            return True
        return False

    @staticmethod
    def _check_active_order(acti, lord):
        dex_dict = {mod: index for index, mod in enumerate(lord)}
        acti.sort(key=dex_dict.__getitem__)
        return u''

    # HELPERS -----------------------------------------------------------------
    def _index_of_first_esp(self, lord):
        index_of_first_esp = 0
        while index_of_first_esp < len(lord) and self.in_master_block(
            self.mod_infos[lord[index_of_first_esp]]):
            index_of_first_esp += 1
        return index_of_first_esp

    @staticmethod
    def _check_for_duplicates(plugins_list):
        """:type plugins_list: list[bolt.Path]"""
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

    # INITIALIZATION ----------------------------------------------------------
    @classmethod
    def parse_ccc_file(cls): pass

    def print_lo_paths(self):
        """Prints the paths that will be used and what they'll be used for.
        Useful for debugging."""
        lo_file = self.get_lo_file()
        acti_file = self.get_acti_file()
        if lo_file or acti_file:
            bolt.deprint(u'Using the following load order files:')
            if acti_file == lo_file:
                bolt.deprint(f' - Load order and active plugins: {acti_file}')
            else:
                if lo_file:
                    bolt.deprint(f' - Load order: {lo_file}')
                if acti_file:
                    bolt.deprint(f' - Active plugins: {acti_file}')

class INIGame(Game):
    """Class for games which use an INI section to determine parts of the load
    order. Meant to be used in multiple inheritance with other Game types, be
    sure to put INIGame first, as a few of its methods delegate to super
    implementations, which are abstract in the Game base class.

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
    ini_key_actives = (u'', u'', u'')
    ini_key_lo = (u'', u'', u'')

    def __init__(self, mod_infos, plugins_txt_path=u''):
        """Creates a new INIGame instance. plugins_txt_path does not have to
        be specified if INIGame will manage active plugins."""
        super(INIGame, self).__init__(mod_infos, plugins_txt_path)
        self._handles_actives = self.__class__.ini_key_actives != (
            u'', u'', u'')
        self._handles_lo = self.__class__.ini_key_lo != (u'', u'', u'')
        if self._handles_actives:
            self._cached_ini_actives = self._mk_ini(
                self.ini_dir_actives.join(self.ini_key_actives[0]))
        if self._handles_lo:
            self._cached_ini_lo = self._mk_ini(
                self.ini_dir_lo.join(self.ini_key_lo[0]))

    # INI directories, override if needed
    @property
    def ini_dir_actives(self): # type: () -> bolt.Path
        """Returns the directory containing the actives INI. Defaults to the
        game path."""
        return bass.dirs[u'app']

    @property
    def ini_dir_lo(self): # type: () -> bolt.Path
        """Returns the directory containing the load order INI. Defaults to the
        game path."""
        return bass.dirs[u'app']

    # Utilities
    @staticmethod
    def _mk_ini(ini_fpath):
        """Creates a new IniFile from the specified bolt.Path object."""
        ini_type, ini_encoding = get_ini_type_and_encoding(ini_fpath)
        return ini_type(ini_fpath, ini_encoding)

    @staticmethod
    def _read_ini(cached_ini, ini_key):
        """Reads a section specified INI using the specified key and returns
        all its values, as bolt.Path objects. Handles missing INI file and an
        absent section gracefully.

        :type cached_ini: bosh.ini_files.IniFile
        :type ini_key: tuple[str, str, str]
        :rtype: list[bolt.Path]"""
        # Returned format is dict[CIstr, tuple[str, int]], we want the
        # unicode (i.e. the mod names)
        section_mapping = cached_ini.get_setting_values(ini_key[1], {})
        # Sort by line number, then convert the values to paths and return
        section_vals = dict_sort(section_mapping, values_dex=[1])
        return [GPath_no_norm(x[1][0]) for x in section_vals]

    @staticmethod
    def _write_ini(cached_ini, ini_key, mod_list):
        """Writes out the specified INI using the specified key and mod list.

        :type cached_ini: bosh.ini_files.IniFile
        :type ini_key: tuple[str, str, str]
        :type mod_list: list[bolt.Path]"""
        # Remove any existing section - also prevents duplicate sections with
        # different case
        cached_ini.remove_section(ini_key[1])
        # Now, write out the changed values - no backup here
        section_contents = OrderedDict()
        for i, lo_mod in enumerate(mod_list):
            section_contents[ini_key[2] % {u'lo_idx': i}] = lo_mod.s
        cached_ini.saveSettings({ini_key[1]: section_contents})

    # Backups
    def _backup_active_plugins(self):
        if self._handles_actives:
            ini_path = self._cached_ini_actives.abs_path
            try:
                ini_path.copyTo(ini_path.backup)
            except OSError:
                bolt.deprint(
                    f'Tried to back up {ini_path}, but it did not exist')
        else: super(INIGame, self)._backup_active_plugins()

    def _backup_load_order(self):
        if self._handles_lo:
            ini_path = self._cached_ini_lo.abs_path
            try:
                ini_path.copyTo(ini_path.backup)
            except OSError:
                bolt.deprint(
                    f'Tried to back up {ini_path}, but it did not exist')
        else: super(INIGame, self)._backup_load_order()

    # Reading from INI
    def _fetch_active_plugins(self):
        if self._handles_actives:
            return self._read_ini(self._cached_ini_actives,
                                  self.__class__.ini_key_actives)
        return super(INIGame, self)._fetch_active_plugins()

    def _fetch_load_order(self, cached_load_order, cached_active):
        if self._handles_lo:
            return self._read_ini(self._cached_ini_lo,
                                  self.__class__.ini_key_lo)
        return super(INIGame, self)._fetch_load_order(cached_load_order,
                                                      cached_active)

    # Writing changes to INI
    def _persist_if_changed(self, active, lord, previous_active,
                            previous_lord):
        if self._handles_actives:
            if previous_active is None or previous_active != active:
                self._persist_active_plugins(active, lord)
            # We've handled this, let the next one in line know
            previous_active = active
        if self._handles_lo:
            if previous_lord is None or previous_lord != lord:
                self._persist_load_order(lord, active)
            # Same idea as above
            previous_lord = lord
        # If we handled both, don't do anything. Otherwise, delegate persisting
        # to the next method in the MRO
        if previous_lord != lord or previous_active != active:
            super(INIGame, self)._persist_if_changed(
                active, lord, previous_active, previous_lord)

    def _persist_active_plugins(self, active, lord):
        if self._handles_actives:
            self._write_ini(self._cached_ini_actives,
                            self.__class__.ini_key_actives, active)
            self._cached_ini_actives.do_update()
        else:
            super(INIGame, self)._persist_active_plugins(active, lord)

    def _persist_load_order(self, lord, active):
        if self._handles_lo:
            self._write_ini(self._cached_ini_lo,
                            self.__class__.ini_key_lo, lord)
            self._cached_ini_lo.do_update()
        else:
            super(INIGame, self)._persist_load_order(lord, active)

    # Misc overrides
    @classmethod
    def _must_update_active(cls, deleted, reordered):
        # Can't use _handles_active here, need to duplicate the logic
        if cls.ini_key_actives != (u'', u'', u''):
            return True # Assume order is important for the INI
        return super(INIGame, cls)._must_update_active(deleted, reordered)

    def active_changed(self):
        if self._handles_actives:
            return self._cached_ini_actives.needs_update()
        return super(INIGame, self).active_changed()

    def load_order_changed(self):
        if self._handles_lo:
            return self._cached_ini_lo.needs_update()
        return super(INIGame, self).load_order_changed()

    def swap(self, old_dir, new_dir):
        def _do_swap(cached_ini, ini_key):
            # If there's no INI inside the old (saves) directory, copy it
            old_ini = old_dir.join(ini_key[0])
            if not old_ini.isfile():
                cached_ini.abs_path.copyTo(old_ini)
            # Read from the new INI if it exists and write to our main INI
            move_ini = new_dir.join(ini_key[0])
            if move_ini.isfile():
                self._write_ini(cached_ini, ini_key, self._read_ini(
                    self._mk_ini(move_ini), ini_key))
        if self._handles_actives:
            _do_swap(self._cached_ini_actives, self.ini_key_actives)
        if self._handles_lo:
            _do_swap(self._cached_ini_lo, self.ini_key_lo)
        super(INIGame, self).swap(old_dir, new_dir)

    def get_acti_file(self):
        if self._handles_actives:
            return self._cached_ini_actives.abs_path
        return super(INIGame, self).get_acti_file()

    def get_lo_file(self):
        if self._handles_lo:
            return self._cached_ini_lo.abs_path
        return super(INIGame, self).get_lo_file()

    def _set_acti_file(self, new_acti_file):
        raise exception.AbstractError(u'INIGame does not support'
                                      u'_set_acti_file right now')

    def _set_lo_file(self, new_lo_file):
        raise exception.AbstractError(u'INIGame does not support _set_lo_file '
                                      u'right now')

class TimestampGame(Game):
    """Oblivion and other games where load order is set using modification
    times.

    :type _mtime_mods: dict[int, set[bolt.Path]]
    """

    allow_deactivate_master = True
    _mtime_mods = defaultdict(set) # intentionally imprecise mtime cache
    _get_free_time_step = 1.0 # step by one second intervals

    @classmethod
    def _must_update_active(cls, deleted, reordered): return deleted

    # Timestamp games write everything into plugins.txt, including game master
    def _active_entries_to_remove(self): return set()

    def has_load_order_conflict(self, mod_name):
        mtime = int(self.mod_infos[mod_name].mtime)
        return mtime in self._mtime_mods and len(self._mtime_mods[mtime]) > 1

    def has_load_order_conflict_active(self, mod_name, active):
        mtime = int(self.mod_infos[mod_name].mtime)
        return self.has_load_order_conflict(mod_name) and bool(
            (self._mtime_mods[mtime] - {mod_name}) & active)

    def get_free_time(self, start_time, end_time=None):
        all_mtimes = {x.mtime for x in self.mod_infos.values()}
        end_time = end_time or (start_time + 1000) # 1000 (seconds) is an arbitrary limit
        while start_time < end_time:
            if not start_time in all_mtimes:
                return start_time
            start_time += self._get_free_time_step
        return max(all_mtimes) + self._get_free_time_step

    def get_acti_file(self):
        return self.plugins_txt_path

    def _set_acti_file(self, new_acti_file):
        self.plugins_txt_path = new_acti_file

    # Abstract overrides ------------------------------------------------------
    def __calculate_mtime_order(self, mods=None): # excludes corrupt mods
        # sort case insensitive (for time conflicts)
        mods = sorted(self.mod_infos if mods is None else mods)
        mods.sort(key=lambda x: self.mod_infos[x].mtime)
        mods.sort(key=lambda x: not self.in_master_block(self.mod_infos[x]))
        return mods

    def _backup_active_plugins(self):
        try:
            self.plugins_txt_path.copyTo(self.plugins_txt_path.backup)
        except OSError:
            bolt.deprint(f'Tried to back up {self.plugins_txt_path}, '
                         f'but it did not exist')

    def _backup_load_order(self):
        pass # timestamps, no file to backup

    def _fetch_load_order(self, cached_load_order, cached_active):
        self._rebuild_mtimes_cache() ##: will need that tweaked for lock load order
        return self.__calculate_mtime_order()

    def _fetch_active_plugins(self):
        active, _lo = self._parse_plugins_txt()
        return active

    def _persist_load_order(self, lord, active):
        assert set(self.mod_infos) == set(lord) # (lord must be valid)
        if len(lord) == 0: return
        current = self.__calculate_mtime_order()
        # break conflicts
        older = self.mod_infos[current[0]].mtime # initialize to game master
        for i, mod in enumerate(current[1:]):
            info = self.mod_infos[mod]
            if info.mtime == older: break
            older = info.mtime
        else: mod = i = None # define i to avoid warning below
        if mod is not None: # respace this and next mods in 60 sec intervals
            for mod in current[i + 1:]:
                info = self.mod_infos[mod]
                older += 60.0
                info.setmtime(older)
        restamp = []
        for ordered, mod in zip(lord, current):
            if ordered == mod: continue
            restamp.append((ordered, self.mod_infos[mod].mtime))
        for ordered, mtime in restamp:
            self.mod_infos[ordered].setmtime(mtime)
        # rebuild our cache
        self._rebuild_mtimes_cache()

    def _rebuild_mtimes_cache(self):
        self._mtime_mods.clear()
        for mod, info in self.mod_infos.items():
            self._mtime_mods[int(info.mtime)] |= {mod}

    def _persist_active_plugins(self, active, lord):
        self._write_plugins_txt(active, active)

    def _persist_if_changed(self, active, lord, previous_active,
                            previous_lord):
        if previous_lord is None or previous_lord != lord:
            self._persist_load_order(lord, active)
        if previous_active is None or set(previous_active) != set(active):
            self._persist_active_plugins(active, lord)

    # Other overrides ---------------------------------------------------------
    def _fix_load_order(self, lord, fix_lo):
        super(TimestampGame, self)._fix_load_order(lord, fix_lo)
        if fix_lo is not None and fix_lo.lo_added:
            # should not occur, except if undoing
            bolt.deprint(u'Incomplete load order passed in to set_load_order. '
                u'Missing: ' + u', '.join(x.s for x in fix_lo.lo_added))
            lord[:] = self.__calculate_mtime_order(mods=lord)

# TimestampGame overrides
class Morrowind(INIGame, TimestampGame):
    """Morrowind uses timestamps for specifying load order, but stores active
    plugins in Morrowind.ini."""
    has_plugins_txt = False
    ini_key_actives = (u'Morrowind.ini', u'Game Files', u'GameFile%(lo_idx)s')

    ##: This is wrong, but works for now. We need game-specific record headers
    # to parse the ESM flag for MW correctly - #480!
    def in_master_block(self, minf):
        return minf.get_extension() == u'.esm'

class TextfileGame(Game):

    def __init__(self, mod_infos, plugins_txt_path, loadorder_txt_path):
        super(TextfileGame, self).__init__(mod_infos, plugins_txt_path)
        self.loadorder_txt_path = loadorder_txt_path # type: bolt.Path
        self.mtime_loadorder_txt = 0
        self.size_loadorder_txt = 0

    def pinned_mods(self):
        return super(TextfileGame, self).pinned_mods() | set(
            self.must_be_active_if_present)

    def _active_entries_to_remove(self):
        # Starting with Skyrim LE, the Update.esm file needs to be removed from
        # plugins.txt too
        return super(TextfileGame, self)._active_entries_to_remove() | {
            GPath_no_norm(u'Update.esm')}

    def load_order_changed(self):
        # if active changed externally refetch load order to check for desync
        return self.active_changed() or (self.loadorder_txt_path.exists() and (
            (self.size_loadorder_txt, self.mtime_loadorder_txt) !=
            self.loadorder_txt_path.size_mtime()))

    def __update_lo_cache_info(self):
        self.size_loadorder_txt, self.mtime_loadorder_txt = \
            self.loadorder_txt_path.size_mtime()

    @classmethod
    def _must_update_active(cls, deleted, reordered):
        return deleted or reordered

    def swap(self, old_dir, new_dir):
        super(TextfileGame, self).swap(old_dir, new_dir)
        # Save loadorder.txt inside the old (saves) directory
        if self.loadorder_txt_path.exists():
            self.loadorder_txt_path.copyTo(old_dir.join(u'loadorder.txt'))
        # Move the new loadorder.txt here for use
        move = new_dir.join(u'loadorder.txt')
        if move.exists():
            move.copyTo(self.loadorder_txt_path)
            self.loadorder_txt_path.mtime = time.time() # update mtime to trigger refresh

    def get_acti_file(self):
        return self.plugins_txt_path

    def get_lo_file(self):
        return self.loadorder_txt_path

    def _set_acti_file(self, new_acti_file):
        self.plugins_txt_path = new_acti_file

    def _set_lo_file(self, new_lo_file):
        self.loadorder_txt_path = new_lo_file

    # Abstract overrides ------------------------------------------------------
    def _backup_active_plugins(self):
        try:
            self.plugins_txt_path.copyTo(self.plugins_txt_path.backup)
        except OSError:
            bolt.deprint(f'Tried to back up {self.plugins_txt_path}, '
                         f'but it did not exist')

    def _backup_load_order(self):
        try:
            self.loadorder_txt_path.copyTo(self.loadorder_txt_path.backup)
        except OSError:
            bolt.deprint(f'Tried to back up {self.loadorder_txt_path},'
                         f' but it did not exist')

    def _fetch_load_order(self, cached_load_order, cached_active):
        """Read data from loadorder.txt file. If loadorder.txt does not
        exist create it and try reading plugins.txt so the load order of the
        user is preserved (note it will create the plugins.txt if not
        existing). Additional mods should be added by caller who should
        anyway call _fix_load_order. If cached_active is passed, the relative
        order of mods will be corrected to match their relative order in
        cached_active.
        :type cached_active: tuple[bolt.Path] | list[bolt.Path]"""
        if not self.loadorder_txt_path.exists():
            mods = cached_active or []
            if (cached_active is not None
                    and not self.plugins_txt_path.exists()):
                self._write_plugins_txt(cached_active, cached_active)
                bolt.deprint(
                    f'Created {self.plugins_txt_path} based on cached info')
            elif cached_active is None and self.plugins_txt_path.exists():
                mods = self._fetch_active_plugins() # will add Skyrim.esm
            self._persist_load_order(mods, mods)
            bolt.deprint(f'Created {self.loadorder_txt_path}')
            return mods
        #--Read file
        _acti, lo = self._parse_modfile(self.loadorder_txt_path)
        # handle desync with plugins txt
        if cached_active is not None:
            cached_active_copy = cached_active[:]
            cached_active_set = set(cached_active)
            active_in_lo = [x for x in lo if x in cached_active_set]
            w = {x: i for i, x in enumerate(lo)}
            while active_in_lo:
                # Use list(), we may modify cached_active_copy and active_in_lo
                for i, (ordered, current) in list(enumerate(
                        zip(cached_active_copy, active_in_lo))):
                    if ordered != current:
                        if ordered not in lo:
                            # Mod is in plugins.txt, but not in loadorder.txt;
                            # just drop it from the copy for now, we'll check
                            # if it's really missing in _fix_active_plugins
                            cached_active_copy.remove(ordered)
                            break
                        for j, x in enumerate(active_in_lo[i:]):
                            if x == ordered: break
                            # x should be above ordered
                            to = w[ordered] + 1 + j
                            # make room
                            w = {x: (i if i < to else i + 1) for x, i in
                                 w.items()}
                            w[x] = to # bubble them up !
                        active_in_lo.remove(ordered)
                        cached_active_copy = cached_active_copy[i + 1:]
                        active_in_lo = active_in_lo[i:]
                        break
                else: break
            fetched_lo = lo[:]
            lo.sort(key=w.get)
            if lo != fetched_lo:
                # We fixed a desync, make a backup and write the load order
                self._backup_load_order()
                self._persist_load_order(lo, lo)
                bolt.deprint(f'Corrected {self.loadorder_txt_path} (order of '
                             f'mods differed from their order in '
                             f'{self.plugins_txt_path})')
        self.__update_lo_cache_info()
        return lo

    def _fetch_active_plugins(self):
        acti, _lo = self._clean_actives(*self._parse_plugins_txt())
        return acti

    def _persist_load_order(self, lord, active):
        _write_plugins_txt_(self.loadorder_txt_path, lord, lord, _star=False)
        self.__update_lo_cache_info()

    def _persist_active_plugins(self, active, lord):
        active_filtered = self._filter_actives(
            active, self._active_entries_to_remove())
        self._write_plugins_txt(active_filtered, active_filtered)

    def _persist_if_changed(self, active, lord, previous_active,
                            previous_lord):
        if previous_lord is None or previous_lord != lord:
            self._persist_load_order(lord, active)
        if previous_active is None or previous_active != active:
            self._persist_active_plugins(active, lord)

    # Validation overrides ----------------------------------------------------
    @staticmethod
    def _check_active_order(acti, lord):
        dex_dict = {mod: index for index, mod in enumerate(lord)}
        old = acti[:]
        acti.sort(key=dex_dict.__getitem__) # all present in lord
        if acti != old: # active mods order that disagrees with lord ?
            return f'Active list order of plugins ({_pl(old)}) differs from ' \
                   f'supplied load order ({_pl(acti)})'
        return u''

class AsteriskGame(Game):

    max_espms = 254
    max_esls = 4096 # hard limit, game runs out of fds sooner, testing needed
    # Creation Club content file - if empty, indicates that this game has no CC
    _ccc_filename = u''
    # Hardcoded list used if the file specified above does not exist or could
    # not be read
    _ccc_fallback = ()
    _star = True

    def _active_entries_to_remove(self):
        return super(AsteriskGame, self)._active_entries_to_remove() | set(
            self.must_be_active_if_present)

    def pinned_mods(self):
        return super(AsteriskGame, self).pinned_mods() | set(
            self.must_be_active_if_present)

    def load_order_changed(self): return self._plugins_txt_modified()

    def in_master_block(self, minf,
                        __master_exts=frozenset((u'.esm', u'.esl'))):
        """For esl games .esm and .esl files are set the master flag in
        memory even if not set on the file on disk. For esps we must check
        for the flag explicitly."""
        return minf.get_extension() in __master_exts or minf.has_esm_flag()

    def _cached_or_fetch(self, cached_load_order, cached_active):
        # read the file once
        return self._fetch_load_order(cached_load_order, cached_active)

    @classmethod
    def _must_update_active(cls, deleted, reordered): return True

    def get_acti_file(self):
        return self.plugins_txt_path

    def get_lo_file(self):
        return self.plugins_txt_path

    def _set_acti_file(self, new_acti_file):
        self.plugins_txt_path = new_acti_file

    def _set_lo_file(self, new_lo_file):
        self.plugins_txt_path = new_lo_file

    # Abstract overrides ------------------------------------------------------
    def _backup_active_plugins(self):
        try:
            self.plugins_txt_path.copyTo(self.plugins_txt_path.backup)
        except OSError:
            bolt.deprint(u'Tried to back up %s, but it did not '
                         u'exist' % self.plugins_txt_path)

    def _backup_load_order(self):
        self._backup_active_plugins() # same thing for asterisk games

    def _fetch_load_order(self, cached_load_order, cached_active):
        """Read data from plugins.txt file. If plugins.txt does not exist
        create it. Discards information read if cached is passed in."""
        exists = self.plugins_txt_path.exists()
        active, lo = self._parse_modfile(self.plugins_txt_path) # empty if not exists
        active = active if cached_active is None else cached_active
        lo = lo if cached_load_order is None else cached_load_order
        active, lo = self._clean_actives(active, lo)
        if not exists:
            # Create it if it doesn't exist
            self._persist_load_order(lo, active)
            bolt.deprint(u'Created %s' % self.plugins_txt_path)
        return lo, active

    def _persist_load_order(self, lord, active):
        assert active # must at least contain the master esm for these games
        rem_from_acti = self._active_entries_to_remove()
        self._write_plugins_txt(self._filter_actives(lord, rem_from_acti),
                                self._filter_actives(active, rem_from_acti))

    def _persist_active_plugins(self, active, lord):
        self._persist_load_order(lord, active)

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

    # Validation overrides ----------------------------------------------------
    def check_active_limit(self, acti_filtered):
        acti_filtered_espm = []
        append_espm = acti_filtered_espm.append
        acti_filtered_esl = []
        append_esl = acti_filtered_esl.append
        cached_minfs = self.mod_infos
        for x in acti_filtered:
            (append_esl if cached_minfs[x].is_esl() else append_espm)(x)
        return set(acti_filtered_espm[self.max_espms:]) , set(
            acti_filtered_esl[self.max_esls:])

    def _clean_actives(self, active, lord):
        """Override since we need to worry about LO here as well."""
        rem_from_acti = self._active_entries_to_remove()
        active_filtered = self._filter_actives(active, rem_from_acti)
        lord_filtered = self._filter_actives(lord, rem_from_acti)
        any_dropped = set(active) - set(active_filtered)
        any_dropped |= set(lord) - set(lord_filtered)
        if any_dropped:
            bolt.deprint(u'Removed %s from %s' % (
                u', '.join(u'%s' % s for s in sorted(any_dropped)),
                self.get_acti_file()))
            # We removed plugins that don't belong here, back up first
            self._backup_active_plugins()
            self._persist_active_plugins(active_filtered, lord_filtered)
        # Prepend all fixed-order plugins that can't be in the actives plugins
        # list to the actives
        sorted_rem = [x for x in self._fixed_order_plugins()
                      if x in rem_from_acti]
        return sorted_rem + active_filtered, sorted_rem + lord_filtered

    @classmethod
    def parse_ccc_file(cls):
        if not cls._ccc_filename: return # Abort if this game has no CC
        ccc_path = bass.dirs[u'app'].join(cls._ccc_filename)
        try:
            with open(ccc_path.s, u'rb') as ins:
                ccc_contents = []
                for ccc_line in ins.readlines():
                    try:
                        ccc_dec = bolt.decoder(ccc_line, encoding=u'cp1252')
                        ccc_contents.append(GPath_no_norm(ccc_dec.strip()))
                    except UnicodeError:
                        bolt.deprint(u'Failed to decode CCC entry %r'
                                     % ccc_line)
                        continue
                cls.must_be_active_if_present += tuple(ccc_contents)
        except OSError as e:
            if not isinstance(e, FileNotFoundError):
                bolt.deprint(u'Failed to open %s' % ccc_path, traceback=True)
            bolt.deprint(u'%s does not exist or could not be read, falling '
                         u'back to hardcoded CCC list' % cls._ccc_filename)
            cls.must_be_active_if_present += cls._ccc_fallback

class WindowsStoreGame(Game):
    """Mixin for Windows Store games, which have a second, fallback directory
    which we must keep in sync with the main one."""
    @property
    def _fallback_lo_files(self):
        """Returns a tuple containing the fallback actives/LO files"""
        try:
            return self._second_acti_file, self._second_lo_file
        except AttributeError:
            from . import bush
            sec_path = bass.dirs[u'local_appdata'].join(bush.game.appdata_name)
            acti_file = self.get_acti_file()
            self._second_acti_file = (sec_path.join(acti_file.stail)
                                      if acti_file else None)
            lo_file = self.get_lo_file()
            self._second_lo_file = (sec_path.join(lo_file.stail)
                                    if lo_file else None)
            return self._second_acti_file, self._second_lo_file

    def _fetch_load_order(self, cached_load_order, cached_active):
        _fb_acti_file, fb_lo_file = self._fallback_lo_files
        lo_file = self.get_lo_file()
        if lo_file and fb_lo_file:
            # Use the main LO file if possible, but if the main file is missing
            # or the fallback file is newer, use that one
            if lo_file.isfile():
                file_to_use = lo_file
                if fb_lo_file.isfile() and fb_lo_file.mtime > lo_file.mtime:
                    file_to_use = fb_lo_file
            else:
                file_to_use = fb_lo_file
            swap_files = file_to_use is not lo_file
        else:
            # We don't even have LO files for this game, skip right to parent
            file_to_use = None
            swap_files = False
        if swap_files:
            self._set_lo_file(file_to_use)
        ret_lo = super(WindowsStoreGame, self)._fetch_load_order(
            cached_load_order, cached_active)
        if swap_files:
            self._set_lo_file(lo_file)
        return ret_lo

    def _fetch_active_plugins(self):
        fb_acti_file, _fb_lo_file = self._fallback_lo_files
        acti_file = self.get_acti_file()
        if acti_file and fb_acti_file:
            # Use the main actives file if possible, but if the main file is
            # missing or the fallback file is newer, use that one
            if acti_file.isfile():
                file_to_use = acti_file
                if (fb_acti_file.isfile() and
                        fb_acti_file.mtime > acti_file.mtime):
                    file_to_use = fb_acti_file
            else:
                file_to_use = fb_acti_file
            swap_files = file_to_use is not acti_file
        else:
            # We don't even have actives files for this game, skip right to
            # parent
            file_to_use = None
            swap_files = False
        if swap_files:
            self._set_acti_file(file_to_use)
        ret_acti = super(WindowsStoreGame, self)._fetch_active_plugins()
        if swap_files:
            self._set_acti_file(acti_file)
        return ret_acti

    def _persist_active_plugins(self, active, lord):
        super(WindowsStoreGame, self)._persist_active_plugins(active, lord)
        fb_acti_file, _fb_lo_file = self._fallback_lo_files
        if fb_acti_file:
            self.get_acti_file().copyTo(fb_acti_file)

    def _persist_load_order(self, lord, active):
        super(WindowsStoreGame, self)._persist_load_order(lord, active)
        _fb_acti_file, fb_lo_file = self._fallback_lo_files
        if fb_lo_file:
            self.get_lo_file().copyTo(fb_lo_file)

    def print_lo_paths(self):
        super(WindowsStoreGame, self).print_lo_paths()
        fb_acti_file, fb_lo_file = self._fallback_lo_files
        if fb_lo_file:
            bolt.deprint(u' - Load order (fallback): %s' % fb_lo_file)
        if fb_acti_file and fb_acti_file != fb_lo_file:
            bolt.deprint(u' - Active plugins (fallback): %s' % fb_acti_file)

# TextfileGame overrides
class Skyrim(TextfileGame):
    must_be_active_if_present = tuple(GPath_no_norm(p) for p in (
        u'Update.esm', u'Dawnguard.esm', u'Hearthfires.esm',
        u'Dragonborn.esm'))

class Enderal(TextfileGame):
    must_be_active_if_present = tuple(GPath_no_norm(p) for p in (
        u'Update.esm', u'Enderal - Forgotten Stories.esm'))

# AsteriskGame overrides
class Fallout4(AsteriskGame):
    must_be_active_if_present = tuple(GPath_no_norm(p) for p in (
        u'DLCRobot.esm', u'DLCworkshop01.esm', u'DLCCoast.esm',
        u'DLCWorkshop02.esm', u'DLCWorkshop03.esm', u'DLCNukaWorld.esm',
        u'DLCUltraHighResolution.esm'))
    _ccc_filename = u'Fallout4.ccc'
    _ccc_fallback = tuple(GPath_no_norm(p) for p in (
        # Up to date as of 2019/11/22
        u'ccBGSFO4001-PipBoy(Black).esl',
        u'ccBGSFO4002-PipBoy(Blue).esl',
        u'ccBGSFO4003-PipBoy(Camo01).esl',
        u'ccBGSFO4004-PipBoy(Camo02).esl',
        u'ccBGSFO4006-PipBoy(Chrome).esl',
        u'ccBGSFO4012-PipBoy(Red).esl',
        u'ccBGSFO4014-PipBoy(White).esl',
        u'ccBGSFO4005-BlueCamo.esl',
        u'ccBGSFO4016-Prey.esl',
        u'ccBGSFO4018-GaussRiflePrototype.esl',
        u'ccBGSFO4019-ChineseStealthArmor.esl',
        u'ccBGSFO4020-PowerArmorSkin(Black).esl',
        u'ccBGSFO4022-PowerArmorSkin(Camo01).esl',
        u'ccBGSFO4023-PowerArmorSkin(Camo02).esl',
        u'ccBGSFO4025-PowerArmorSkin(Chrome).esl',
        u'ccBGSFO4033-PowerArmorSkinWhite.esl',
        u'ccBGSFO4024-PACamo03.esl',
        u'ccBGSFO4038-HorseArmor.esl',
        u'ccBGSFO4041-DoomMarineArmor.esl',
        u'ccBGSFO4042-BFG.esl',
        u'ccBGSFO4044-HellfirePowerArmor.esl',
        u'ccFSVFO4001-ModularMilitaryBackpack.esl',
        u'ccFSVFO4002-MidCenturyModern.esl',
        u'ccFRSFO4001-HandmadeShotgun.esl',
        u'ccEEJFO4001-DecorationPack.esl',
        u'ccRZRFO4001-TunnelSnakes.esm',
        u'ccBGSFO4045-AdvArcCab.esl',
        u'ccFSVFO4003-Slocum.esl',
        u'ccGCAFO4001-FactionWS01Army.esl',
        u'ccGCAFO4002-FactionWS02ACat.esl',
        u'ccGCAFO4003-FactionWS03BOS.esl',
        u'ccGCAFO4004-FactionWS04Gun.esl',
        u'ccGCAFO4005-FactionWS05HRPink.esl',
        u'ccGCAFO4006-FactionWS06HRShark.esl',
        u'ccGCAFO4007-FactionWS07HRFlames.esl',
        u'ccGCAFO4008-FactionWS08Inst.esl',
        u'ccGCAFO4009-FactionWS09MM.esl',
        u'ccGCAFO4010-FactionWS10RR.esl',
        u'ccGCAFO4011-FactionWS11VT.esl',
        u'ccGCAFO4012-FactionAS01ACat.esl',
        u'ccGCAFO4013-FactionAS02BoS.esl',
        u'ccGCAFO4014-FactionAS03Gun.esl',
        u'ccGCAFO4015-FactionAS04HRPink.esl',
        u'ccGCAFO4016-FactionAS05HRShark.esl',
        u'ccGCAFO4017-FactionAS06Inst.esl',
        u'ccGCAFO4018-FactionAS07MM.esl',
        u'ccGCAFO4019-FactionAS08Nuk.esl',
        u'ccGCAFO4020-FactionAS09RR.esl',
        u'ccGCAFO4021-FactionAS10HRFlames.esl',
        u'ccGCAFO4022-FactionAS11VT.esl',
        u'ccGCAFO4023-FactionAS12Army.esl',
        u'ccAWNFO4001-BrandedAttire.esl',
        u'ccSWKFO4001-AstronautPowerArmor.esm',
        u'ccSWKFO4002-PipNuka.esl',
        u'ccSWKFO4003-PipQuan.esl',
        u'ccBGSFO4050-DgBColl.esl',
        u'ccBGSFO4051-DgBox.esl',
        u'ccBGSFO4052-DgDal.esl',
        u'ccBGSFO4053-DgGoldR.esl',
        u'ccBGSFO4054-DgGreatD.esl',
        u'ccBGSFO4055-DgHusk.esl',
        u'ccBGSFO4056-DgLabB.esl',
        u'ccBGSFO4057-DgLabY.esl',
        u'ccBGSFO4058-DGLabC.esl',
        u'ccBGSFO4059-DgPit.esl',
        u'ccBGSFO4060-DgRot.esl',
        u'ccBGSFO4061-DgShiInu.esl',
        u'ccBGSFO4036-TrnsDg.esl',
        u'ccRZRFO4004-PipInst.esl',
        u'ccBGSFO4062-PipPat.esl',
        u'ccRZRFO4003-PipOver.esl',
        u'ccFRSFO4002-AntimaterielRifle.esl',
        u'ccEEJFO4002-Nuka.esl',
        u'ccYGPFO4001-PipCruiser.esl',
        u'ccBGSFO4072-PipGrog.esl',
        u'ccBGSFO4073-PipMMan.esl',
        u'ccBGSFO4074-PipInspect.esl',
        u'ccBGSFO4075-PipShroud.esl',
        u'ccBGSFO4076-PipMystery.esl',
        u'ccBGSFO4071-PipArc.esl',
        u'ccBGSFO4079-PipVim.esl',
        u'ccBGSFO4078-PipReily.esl',
        u'ccBGSFO4077-PipRocket.esl',
        u'ccBGSFO4070-PipAbra.esl',
        u'ccBGSFO4008-PipGrn.esl',
        u'ccBGSFO4015-PipYell.esl',
        u'ccBGSFO4009-PipOran.esl',
        u'ccBGSFO4011-PipPurp.esl',
        u'ccBGSFO4021-PowerArmorSkinBlue.esl',
        u'ccBGSFO4027-PowerArmorSkinGreen.esl',
        u'ccBGSFO4034-PowerArmorSkinYellow.esl',
        u'ccBGSFO4028-PowerArmorSkinOrange.esl',
        u'ccBGSFO4031-PowerArmorSkinRed.esl',
        u'ccBGSFO4030-PowerArmorSkinPurple.esl',
        u'ccBGSFO4032-PowerArmorSkinTan.esl',
        u'ccBGSFO4029-PowerArmorSkinPink.esl',
        u'ccGRCFO4001-PipGreyTort.esl',
        u'ccGRCFO4002-PipGreenVim.esl',
        u'ccBGSFO4013-PipTan.esl',
        u'ccBGSFO4010-PipPnk.esl',
        u'ccSBJFO4001-SolarFlare.esl',
        u'ccZSEF04001-BHouse.esm',
        u'ccTOSFO4001-NeoSky.esm',
        u'ccKGJFO4001-bastion.esl',
        u'ccBGSFO4063-PAPat.esl',
        u'ccQDRFO4001_PowerArmorAI.esl',
        u'ccBGSFO4048-Dovah.esl',
        u'ccBGSFO4101-AS_Shi.esl',
        u'ccBGSFO4114-WS_Shi.esl',
        u'ccBGSFO4115-X02.esl',
        u'ccRZRFO4002-Disintegrate.esl',
        u'ccBGSFO4116-HeavyFlamer.esl',
        u'ccBGSFO4091-AS_Bats.esl',
        u'ccBGSFO4092-AS_CamoBlue.esl',
        u'ccBGSFO4093-AS_CamoGreen.esl',
        u'ccBGSFO4094-AS_CamoTan.esl',
        u'ccBGSFO4097-AS_Jack-oLantern.esl',
        u'ccBGSFO4104-WS_Bats.esl',
        u'ccBGSFO4105-WS_CamoBlue.esl',
        u'ccBGSFO4106-WS_CamoGreen.esl',
        u'ccBGSFO4107-WS_CamoTan.esl',
        u'ccBGSFO4111-WS_Jack-oLantern.esl',
        u'ccBGSFO4118-WS_TunnelSnakes.esl',
        u'ccBGSFO4113-WS_ReillysRangers.esl',
        u'ccBGSFO4112-WS_Pickman.esl',
        u'ccBGSFO4110-WS_Enclave.esl',
        u'ccBGSFO4108-WS_ChildrenOfAtom.esl',
        u'ccBGSFO4103-AS_TunnelSnakes.esl',
        u'ccBGSFO4099-AS_ReillysRangers.esl',
        u'ccBGSFO4098-AS_Pickman.esl',
        u'ccBGSFO4096-AS_Enclave.esl',
        u'ccBGSFO4095-AS_ChildrenOfAtom.esl',
        u'ccBGSFO4090-PipTribal.esl',
        u'ccBGSFO4089-PipSynthwave.esl',
        u'ccBGSFO4087-PipHaida.esl',
        u'ccBGSFO4085-PipHawaii.esl',
        u'ccBGSFO4084-PipRetro.esl',
        u'ccBGSFO4083-PipArtDeco.esl',
        u'ccBGSFO4082-PipPRC.esl',
        u'ccBGSFO4081-PipPhenolResin.esl',
        u'ccBGSFO4080-PipPop.esl',
        u'ccBGSFO4035-Pint.esl',
        u'ccBGSFO4086-PipAdventure.esl',
        u'ccJVDFO4001-Holiday.esl',
        u'ccBGSFO4047-QThund.esl',
        u'ccFRSFO4003-CR75L.esl',
        u'ccZSEFO4002-SManor.esm',
        u'ccACXFO4001-VSuit.esl',
        u'ccBGSFO4040-VRWorkshop01.esl',
        u'ccFSVFO4005-VRDesertIsland.esl',
        u'ccFSVFO4006-VRWasteland.esl',
        u'ccSBJFO4002_ManwellRifle.esl',
        u'ccTOSFO4002_NeonFlats.esm',
        u'ccBGSFO4117-CapMerc.esl',
        u'ccFSVFO4004-VRWorkshopGNRPlaza.esl',
        u'ccBGSFO4046-TesCan.esl',
        u'ccGCAFO4025-PAGunMM.esl',
        u'ccCRSFO4001-PipCoA.esl',
    ))

class Fallout4VR(Fallout4):
    must_be_active_if_present = Fallout4.must_be_active_if_present + (
        GPath_no_norm(u'Fallout4_VR.esm'),)
    _ccc_filename = u''

class SkyrimSE(AsteriskGame):
    must_be_active_if_present = tuple(GPath_no_norm(p) for p in (
        u'Update.esm', u'Dawnguard.esm', u'Hearthfires.esm', u'Dragonborn.esm'
    ))
    _ccc_filename = u'Skyrim.ccc'
    _ccc_fallback = tuple(GPath_no_norm(p) for p in (
        # Up to date as of 2019/11/22
        u'ccBGSSSE002-ExoticArrows.esl',
        u'ccBGSSSE003-Zombies.esl',
        u'ccBGSSSE004-RuinsEdge.esl',
        u'ccBGSSSE006-StendarsHammer.esl',
        u'ccBGSSSE007-Chrysamere.esl',
        u'ccBGSSSE010-PetDwarvenArmoredMudcrab.esl',
        u'ccBGSSSE014-SpellPack01.esl',
        u'ccBGSSSE019-StaffofSheogorath.esl',
        u'ccBGSSSE020-GrayCowl.esl',
        u'ccBGSSSE021-LordsMail.esl',
        u'ccMTYSSE001-KnightsoftheNine.esl',
        u'ccQDRSSE001-SurvivalMode.esl',
        u'ccTWBSSE001-PuzzleDungeon.esm',
        u'ccEEJSSE001-Hstead.esm',
        u'ccQDRSSE002-Firewood.esl',
        u'ccBGSSSE018-Shadowrend.esl',
        u'ccBGSSSE035-PetNHound.esl',
        u'ccFSVSSE001-Backpacks.esl',
        u'ccEEJSSE002-Tower.esl',
        u'ccEDHSSE001-NorJewel.esl',
        u'ccVSVSSE002-Pets.esl',
        u'ccBGSSSE037-Curios.esl',
        u'ccBGSSSE034-MntUni.esl',
        u'ccBGSSSE045-Hasedoki.esl',
        u'ccBGSSSE008-Wraithguard.esl',
        u'ccBGSSSE036-PetBWolf.esl',
        u'ccFFBSSE001-ImperialDragon.esl',
        u'ccMTYSSE002-VE.esl',
        u'ccBGSSSE043-CrossElv.esl',
        u'ccVSVSSE001-Winter.esl',
        u'ccEEJSSE003-Hollow.esl',
        u'ccBGSSSE016-Umbra.esm',
        u'ccBGSSSE031-AdvCyrus.esm',
        u'ccBGSSSE040-AdvObGobs.esl',
        u'ccBGSSSE050-BA_Daedric.esl',
        u'ccBGSSSE052-BA_Iron.esl',
        u'ccBGSSSE054-BA_Orcish.esl',
        u'ccBGSSSE058-BA_Steel.esl',
        u'ccBGSSSE059-BA_Dragonplate.esl',
        u'ccBGSSSE061-BA_Dwarven.esl',
        u'ccPEWSSE002-ArmsOfChaos.esl',
        u'ccBGSSSE041-NetchLeather.esl',
        u'ccEDHSSE002-SplKntSet.esl',
        u'ccBGSSSE064-BA_Elven.esl',
        u'ccBGSSSE063-BA_Ebony.esl',
        u'ccBGSSSE062-BA_DwarvenMail.esl',
        u'ccBGSSSE060-BA_Dragonscale.esl',
        u'ccBGSSSE056-BA_Silver.esl',
        u'ccBGSSSE055-BA_OrcishScaled.esl',
        u'ccBGSSSE053-BA_Leather.esl',
        u'ccBGSSSE051-BA_DaedricMail.esl',
        u'ccBGSSSE057-BA_Stalhrim.esl',
        u'ccVSVSSE003-NecroArts.esl',
        u'ccBGSSSE025-AdvDSGS.esm',
        u'ccFFBSSE002-CrossbowPack.esl',
        u'ccBGSSSE013-Dawnfang.esl',
        u'ccRMSSSE001-NecroHouse.esl',
        u'ccEEJSSE004-Hall.esl',
    ))

class SkyrimVR(SkyrimSE):
    must_be_active_if_present = SkyrimSE.must_be_active_if_present + (
        GPath_no_norm(u'SkyrimVR.esm'),)
    _ccc_filename = u''

class EnderalSE(SkyrimSE):
    # Update.esm is forcibly loaded after the (empty) DLC plugins by the game
    must_be_active_if_present = tuple(GPath_no_norm(p) for p in (
        u'Dawnguard.esm', u'Hearthfires.esm', u'Dragonborn.esm', u'Update.esm',
        u'Enderal - Forgotten Stories.esm',
    ))

    def _active_entries_to_remove(self):
        return super(EnderalSE, self)._active_entries_to_remove() - {
            # Enderal - Forgotten Stories.esm is *not* hardcoded to load, so
            # don't remove it from the LO
            GPath_no_norm(u'Enderal - Forgotten Stories.esm'),
        }

# WindowsStoreGame overrides
class SkyrimSEWS(WindowsStoreGame, SkyrimSE): pass
class Fallout4WS(WindowsStoreGame, Fallout4): pass

# Game factory
def game_factory(game_fsName, mod_infos, plugins_txt_path,
                 loadorder_txt_path=None):
    if game_fsName == u'Morrowind':
        return Morrowind(mod_infos)
    elif game_fsName == u'Skyrim':
        return Skyrim(mod_infos, plugins_txt_path, loadorder_txt_path)
    elif game_fsName == u'Enderal':
        return Enderal(mod_infos, plugins_txt_path, loadorder_txt_path)
    elif game_fsName == u'Enderal Special Edition':
        return EnderalSE(mod_infos, plugins_txt_path)
    elif game_fsName == u'Skyrim Special Edition':
        return SkyrimSE(mod_infos, plugins_txt_path)
    elif game_fsName == u'Skyrim VR':
        return SkyrimVR(mod_infos, plugins_txt_path)
    elif game_fsName == u'Skyrim Special Edition MS':
        return SkyrimSEWS(mod_infos, plugins_txt_path)
    elif game_fsName == u'Fallout4':
        return Fallout4(mod_infos, plugins_txt_path)
    elif game_fsName == u'Fallout4VR':
        return Fallout4VR(mod_infos, plugins_txt_path)
    elif game_fsName == u'Fallout4 MS':
        return Fallout4WS(mod_infos, plugins_txt_path)
    else:
        return TimestampGame(mod_infos, plugins_txt_path)

# Print helpers
def _pl(it, legend=u'', joint=u', '):
    return legend + joint.join(u'%s' % x for x in it) # use Path.__str__
