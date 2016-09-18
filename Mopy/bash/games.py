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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2015 Wrye Bash Team
#  https://github.com/wrye-bash
#  Mopy/bash/games.py copyright (C) 2016 Utumno: Original design
#
# =============================================================================

"""Game class initially introduced to encapsulate load order handling and
eventually to wrap the bush.game module to a class API to be used in the rest
of Bash."""

__author__ = 'Utumno'

import re

import time
from collections import defaultdict

import bolt

def _write_plugins_txt_(path, lord, active, _star=False):
    with path.open('wb') as out:
        def asterisk(active_set=set(active)):
            return '*' if _star and (mod in active_set) else ''
        for mod in (_star and lord) or active:
            # Ok, this seems to work for Oblivion, but not Skyrim
            # Skyrim seems to refuse to have any non-cp1252 named file in
            # plugins.txt.  Even activating through the SkyrimLauncher
            # doesn't work.
            try:
                out.write(asterisk() + bolt.encode(mod.s))
                out.write('\r\n')
            except UnicodeEncodeError:
                pass

_re_plugins_txt_comment = re.compile(u'^#.*', re.U)
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
    with path.open('r') as ins:
        #--Load Files
        active, modnames = [], []
        for line in ins:
            # Oblivion/Skyrim saves the plugins.txt file in cp1252 format
            # It wont accept filenames in any other encoding
            try: # use raw strings below
                modname = _re_plugins_txt_comment.sub('', line).strip()
                if not modname: continue
                is_active = not _star or modname.startswith('*')
                if _star and is_active: modname = modname[1:]
                test = bolt.decode(modname)
            except UnicodeError: continue
            if bolt.GPath(test) not in mod_infos:
                # The automatic encoding detector could have returned
                # an encoding it actually wasn't.  Luckily, we
                # have a way to double check: modInfos.data
                for encoding in bolt.encodingOrder:
                    try:
                        test2 = unicode(modname, encoding)
                        if bolt.GPath(test2) not in mod_infos:
                            continue
                        modname = bolt.GPath(test2)
                        break
                    except UnicodeError:
                        pass
                else:
                    modname = bolt.GPath(test)
            else:
                modname = bolt.GPath(test)
            modnames.append(modname)
            if is_active: active.append(modname)
    return active, modnames

class Game(object):

    allow_deactivate_master = False
    must_be_active_if_present = ()

    def __init__(self, mod_infos, plugins_txt_path):
        super(Game, self).__init__()
        self.plugins_txt_path = plugins_txt_path # type: bolt.Path
        self.mod_infos = mod_infos # type: bosh.ModInfos
        self.master_path = mod_infos.masterName # type: bolt.Path
        self.mtime_plugins_txt = 0
        self.size_plugins_txt = 0

    def _plugins_txt_modified(self):
        exists = self.plugins_txt_path.exists()
        if not exists and self.mtime_plugins_txt: return True # deleted !
        return exists and ((self.size_plugins_txt, self.mtime_plugins_txt) !=
                           self.plugins_txt_path.size_mtime())

    # API ---------------------------------------------------------------------
    def get_load_order(self, cached_load_order, cached_active_ordered,
                       quiet=False):
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
        :rtype: (list[bolt.Path], list[bolt.Path]) |
                (tuple[bolt.Path], tuple[bolt.Path])
        """
        if cached_load_order is not None and cached_active_ordered is not None:
            return cached_load_order, cached_active_ordered # NOOP
        lo, active = self._cached_or_fetch(cached_load_order,
                                           cached_active_ordered)
        # for timestamps we use modInfos so we should not get an invalid
        # load order (except redated master). For text based games however
        # the fetched order could be in whatever state, so get this fixed
        if cached_load_order is None: ##: if not should we assert is valid ?
            removed, added, reordered = self._fix_load_order(lo, quiet=quiet)
        else: removed = added = reordered = set()
        # having a valid load order we may fix active too if we fetched them
        fixed_active = cached_active_ordered is None and \
                self._fix_active_plugins(active, lo, on_disc=True, quiet=quiet)
        self._save_fixed_load_order(removed, added, reordered,
                                    fixed_active, lo, active)
        return lo, active

    def _cached_or_fetch(self, cached_load_order, cached_active):
        # we need to override this bit for fallout4 to parse the file once
        if cached_active is None: # first get active plugins
            cached_active = self._fetch_active_plugins()
        # we need active plugins fetched to check for desync in load order
        if cached_load_order is None:
            cached_load_order = self._fetch_load_order(cached_load_order,
                                                       cached_active)
        return list(cached_load_order), list(cached_active)

    def _save_fixed_load_order(self, removed, added, reordered, fixed_active,
                               lo, active):
        if removed or added or reordered:
            self._persist_load_order(lo, None) # active is not used here

    def set_load_order(self, lord, active, previous_lord=None,
                       previous_active=None, dry_run=False):
        assert lord is not None or active is not None, \
            'load order or active must be not None'
        if lord is not None: self._fix_load_order(lord, quiet=dry_run)
        if (previous_lord is None or previous_lord != lord) and active is None:
            # changing load order - must test if active plugins must change too
            assert previous_active is not None, \
                'you must pass info on active when setting load order'
            if previous_lord is not None:
                prev = set(previous_lord)
                new = set(lord)
                deleted = prev - new
                common = prev & new
                reordered = any(x != y for x, y in
                                zip((x for x in previous_lord if x in common),
                                    (x for x in lord if x in common)))
                test_active = self._must_update_active(deleted, reordered)
            else:
                test_active = True
            if test_active: active = list(previous_active)
        if active is not None:
            assert lord is not None or previous_lord is not None, \
                'you need to pass a load order in to set active plugins'
            # a load order is needed for all games to validate active against
            test = lord if lord is not None else previous_lord
            self._fix_active_plugins(active, test, on_disc=False, quiet=dry_run)
        lord = lord if lord is not None else previous_lord
        active = active if active is not None else previous_active
        assert lord is not None and active is not None, \
            'returned load order and active must be not None'
        if not dry_run: # else just return the (possibly fixed) lists
            self._persist_if_changed(active, lord, previous_active,
                                     previous_lord)
        return lord, active # return what was set or was previously set

    # Conflicts - only for timestamp games
    def has_load_order_conflict(self, mod_name): return False
    def has_load_order_conflict_active(self, mod_name, active): return False
    # force installation last - only for timestamp games
    def install_last(self):
        """Install mods last in load order (done by default when txt method
        used - for mod times method make sure we get the latest mod time)."""
        return lambda *args: None
    def get_free_time(self, start_time, default_time='+1'): return time.time()

    @staticmethod
    def _must_update_active(deleted, reordered): raise bolt.AbstractError

    def active_changed(self): return self._plugins_txt_modified()

    def load_order_changed(self): return True # timestamps, just calculate it

    # Swap plugins and loadorder txt
    def swap(self, old_path, new_path):
        """Save current plugins into oldPath directory and load plugins from
        newPath directory (if present)."""
        # Save plugins.txt inside the old (saves) directory
        if self.plugins_txt_path.exists():
            self.plugins_txt_path.copyTo(old_path.join(u'plugins.txt'))
        # Move the new plugins.txt here for use
        move = new_path.join(u'plugins.txt')
        if move.exists():
            move.copyTo(self.plugins_txt_path)
            self.plugins_txt_path.mtime = time.time() # copy will not change mtime, bad

    # ABSTRACT ----------------------------------------------------------------
    def _fetch_load_order(self, cached_load_order, cached_active):
        """:type cached_load_order: tuple[bolt.Path]
        :type cached_active: tuple[bolt.Path]"""
        raise bolt.AbstractError

    def _fetch_active_plugins(self): # no override for AsteriskGame
        """:rtype: list[bolt.Path]"""
        raise bolt.AbstractError

    def _persist_load_order(self, lord, active):
        """Persist the fixed lord to disk - will break conflicts for
        timestamp games."""
        raise bolt.AbstractError

    def _persist_active_plugins(self, active, lord):
        raise bolt.AbstractError

    def _persist_if_changed(self, active, lord, previous_active,
                            previous_lord):
        # Override for fallout4 to write the file once and oblivion to save
        # active only if needed. Both active and lord must not be None.
        raise bolt.AbstractError

    # MODFILES PARSING --------------------------------------------------------
    def _parse_modfile(self, path):
        """:rtype: (list[bolt.Path], list[bolt.Path])"""
        if not path.exists(): return [], []
        #--Read file
        acti, _lo = _parse_plugins_txt_(path, self.mod_infos, _star=False)
        return acti, _lo

    def _write_modfile(self, path, lord, active):
        _write_plugins_txt_(path, lord, active, _star=False)

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

    def __update_plugins_txt_cache_info(self):
        self.size_plugins_txt, self.mtime_plugins_txt = \
            self.plugins_txt_path.size_mtime()

    # VALIDATION --------------------------------------------------------------
    def _fix_load_order(self, lord, quiet=False):
        """Fix inconsistencies between given loadorder and actually installed
        mod files as well as impossible load orders. We need a refreshed
        bosh.modInfos reflecting the contents of Data/.

        Called in get_load_order() to fix a newly fetched LO and in
        set_load_order() to check if a load order passed in is valid. Needs
        rethinking as save load and active should be an atomic operation -
        leads to hacks (like the _selected parameter).
        :type lord: list[bolt.Path]
        """
        old_lord = lord[:]
        # game's master might be out of place (if using timestamps for load
        # ordering or a manually edited loadorder.txt) so move it up
        master_name = self.master_path
        master_dex = 0
        try:
            master_dex = lord.index(master_name)
            _addedFiles = set()
        except ValueError:
            if not master_name in self.mod_infos:
                raise bolt.BoltError(
                    u'%s is missing or corrupted' % master_name)
            _addedFiles = {master_name}
        if master_dex > 0:
            bolt.deprint(
                u'%s has index %d (must be 0)' % (master_name, master_dex))
            lord.remove(master_name)
            lord.insert(0, master_name)
            _reordered = True
        else: _reordered = False
        # below do not apply to timestamp method (on getting it)
        loadorder_set = set(lord)
        mods_set = set(self.mod_infos.keys())
        _removedFiles = loadorder_set - mods_set # may remove corrupted mods
        # present in text file, we are supposed to take care of that
        _addedFiles |= mods_set - loadorder_set
        # Remove non existent plugins from load order
        lord[:] = [x for x in lord if x not in _removedFiles]
        # See if any esm files are loaded below an esp and reorder as necessary
        ol = lord[:]
        lord.sort(key=lambda m: not self.mod_infos[m].isEsm())
        _reordered |= ol != lord
        # Append new plugins to load order
        index_first_esp = self._index_of_first_esp(lord)
        for mod in _addedFiles:
            if self.mod_infos[mod].isEsm():
                if not mod == master_name:
                    lord.insert(index_first_esp, mod)
                else:
                    lord.insert(0, master_name)
                    bolt.deprint(u'%s inserted to Load order' % master_name)
                index_first_esp += 1
            else: lord.append(mod)
        # end textfile get
        duplicates = self._check_for_duplicates(lord)
        if not quiet: warn_lo_fixed(_addedFiles, _removedFiles, _reordered,
                                    duplicates, lord, old_lord)
        return _removedFiles, _addedFiles, _reordered

    def _fix_active_plugins(self, acti, lord, on_disc, quiet=False):
        # filter plugins not present in modInfos - this will disable
        # corrupted too! Preserve acti order
        acti_filtered = [x for x in acti if x in self.mod_infos]
        _removed = set(acti) - set(acti_filtered)
        if _removed: # take note as we may need to rewrite plugins txt
            msg = u'Active list contains mods not present ' \
                  u'in Data/ directory or corrupted: ' + _pl(_removed) + u'\n'
            self.mod_infos.selectedBad = _removed
        else: msg = u''
        if not self.allow_deactivate_master:
            if not self.master_path in acti_filtered:
                acti_filtered.insert(0, self.master_path)
                msg += (u'%s not present in active mods\n' % self.master_path)
        added_active_paths = []
        for path in self.must_be_active_if_present:
            if path in lord and not path in acti_filtered:
                msg += (u'%s not present in active list '
                        u'while present in Data folder' % path) + u'\n'
                added_active_paths.append(path)
        # order - affects which mods are chopped off if > 255 (the ones that
        # load last) - won't trigger saving but for Skyrim
        msg += self._check_active_order(acti_filtered, lord)
        for path in added_active_paths: # insert after the last master
            acti_filtered.insert(self._index_of_first_esp(acti_filtered), path)
        # check if we have more than 256 active mods
        if len(acti_filtered) > 255:
            msg += u'Active list contains more than 255 plugins' \
                   u' - the following plugins will be deactivated: '
            self.mod_infos.selectedExtra = acti_filtered[255:]
            msg += _pl(self.mod_infos.selectedExtra)
        # Check for duplicates
        duplicates = self._check_for_duplicates(acti_filtered)
        if duplicates:
            msg += u'Removed duplicate entries from active list : '
            msg += _pl(duplicates)
        acti[:] = acti_filtered[:255] # chop off extra, update acti in place
        if msg:
            if on_disc: # used when getting active and found invalid, fix 'em!
                # Notify user - ##: maybe backup previous plugin txt ?
                msg = u'Invalid Plugin txt corrected:\n' + msg
                self._persist_active_plugins(acti, lord)
            else: # active list we passed in when setting load order is invalid
                msg = u'Invalid active plugins list corrected:\n' + msg
            if not quiet: bolt.deprint(msg)
            return True # changes, saved if loading plugins.txt
        return False # no changes, not saved

    @staticmethod
    def _check_active_order(acti, lord):
        dex_dict = {mod: index for index, mod in enumerate(lord)}
        acti.sort(key=dex_dict.__getitem__)
        return u''

    # HELPERS -----------------------------------------------------------------
    def _index_of_first_esp(self, lord):
        index_of_first_esp = 0
        while index_of_first_esp < len(lord) and self.mod_infos[
            lord[index_of_first_esp]].isEsm():
            index_of_first_esp += 1
        return index_of_first_esp

    @staticmethod
    def _check_for_duplicates(plugins_list):
        """:type plugins_list: list[bolt.Path]"""
        mods, duplicates, j = set(), set(), 0
        for i, mod in enumerate(plugins_list[:]):
            if mod in mods:
                del plugins_list[i - j]
                j += 1
                duplicates.add(mod)
            else:
                mods.add(mod)
        return duplicates

class TimestampGame(Game):

    allow_deactivate_master = True
    _mod_mtime = {} # type: dict[bolt.Path, int]
    _mtime_mods = defaultdict(set) # type: dict[int, set[bolt.Path]]
    _get_free_time_step = 1 # step by one second intervals

    @staticmethod
    def _must_update_active(deleted, reordered): return deleted

    def has_load_order_conflict(self, mod_name):
        mtime = self.mod_infos[mod_name].mtime
        return mtime in self._mtime_mods and len(self._mtime_mods[mtime]) > 1

    def has_load_order_conflict_active(self, mod_name, active):
        mtime = self.mod_infos[mod_name].mtime
        return self.has_load_order_conflict(mod_name) and bool(
            (self._mtime_mods[mtime] - {mod_name}) & active)

    __max_time = -1
    def install_last(self):
        maxi = max(mtime for mtime in self._mtime_mods.iterkeys())
        maxi = [max(maxi, self.__max_time) + 60] # a list to be manipulated
        def timestamps(p):
            self.__max_time = p.mtime = maxi[0]
            maxi[0] += 60 # space at one minute intervals
        return timestamps

    def get_free_time(self, start_time, default_time='+1'):
        all_mtimes = set(self._mtime_mods)
        end_time = start_time + 1000 # 1000 (seconds) is an arbitrary limit
        while start_time < end_time:
            if not start_time in all_mtimes:
                return start_time
            start_time += self._get_free_time_step
        return default_time

    # Abstract overrides ------------------------------------------------------
    def _fetch_load_order(self, cached_load_order, cached_active):
        self._rebuild_mtimes_cache() ##: will need that tweaked for lock load order
        return self.mod_infos.calculateLO()

    def _fetch_active_plugins(self):
        active, _lo = self._parse_plugins_txt()
        return active

    def _persist_load_order(self, lord, active):
        assert set(self.mod_infos.keys()) == set(lord) # (lord must be valid)
        if len(lord) == 0: return
        current = self.mod_infos.calculateLO()
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
                older += 60
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
        self._mod_mtime.clear()
        self._mtime_mods.clear()
        for mod, info in self.mod_infos.iteritems():
            mtime = info.mtime
            self._mod_mtime[mod] = mtime
            self._mtime_mods[mtime] |= {mod}

    def _persist_active_plugins(self, active, lord):
        self._write_plugins_txt(active, active)

    def _persist_if_changed(self, active, lord, previous_active,
                            previous_lord):
        if previous_lord is None or previous_lord != lord:
            self._persist_load_order(lord, active)
        if previous_active is None or set(previous_active) != set(active):
            self._persist_active_plugins(active, lord)

    def _fix_load_order(self, lord, quiet=False):
        _removedFiles, _addedFiles, _reordered = super(TimestampGame,
            self)._fix_load_order(lord, quiet)
        if _addedFiles: # should not occur
            bolt.deprint(u'Incomplete load order passed in to set_load_order')
            lord[:] = self.mod_infos.calculateLO(mods=lord)
        return _removedFiles, _addedFiles, _reordered

class TextfileGame(Game):

    must_be_active_if_present = (bolt.GPath(u'Update.esm'),)

    def __init__(self, mod_infos, plugins_txt_path, loadorder_txt_path):
        super(TextfileGame, self).__init__(mod_infos, plugins_txt_path)
        self.loadorder_txt_path = loadorder_txt_path
        self.mtime_loadorder_txt = 0
        self.size_loadorder_txt = 0

    def load_order_changed(self):
        # if active changed externally refetch load order to check for desync
        return self.active_changed() or (self.loadorder_txt_path.exists() and (
            (self.size_loadorder_txt, self.mtime_loadorder_txt) !=
            self.loadorder_txt_path.size_mtime()))

    def __update_lo_cache_info(self):
        self.size_loadorder_txt, self.mtime_loadorder_txt = \
            self.loadorder_txt_path.size_mtime()

    @staticmethod
    def _must_update_active(deleted, reordered): return deleted or reordered

    def swap(self, old_path, new_path):
        super(TextfileGame, self).swap(old_path, new_path)
        # Save loadorder.txt inside the old (saves) directory
        if self.loadorder_txt_path.exists():
            self.loadorder_txt_path.copyTo(old_path.join(u'loadorder.txt'))
        # Move the new loadorder.txt here for use
        move = new_path.join(u'loadorder.txt')
        if move.exists():
            move.copyTo(self.loadorder_txt_path)
            self.loadorder_txt_path.mtime = time.time() # update mtime to trigger refresh

    # Abstract overrides ------------------------------------------------------
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
            if cached_active is not None and not self.plugins_txt_path.exists():
                self._write_plugins_txt(cached_active, cached_active)
                bolt.deprint(
                    u'Created %s based on cached info' % self.plugins_txt_path)
            elif cached_active is None and self.plugins_txt_path.exists():
                mods = self._fetch_active_plugins() # will add Skyrim.esm
            self._persist_load_order(mods, mods)
            bolt.deprint(u'Created %s' % self.loadorder_txt_path)
            return mods
        #--Read file
        _acti, lo = self._parse_modfile(self.loadorder_txt_path)
        # handle desync with plugins txt
        if cached_active is not None:
            cached_active_copy = cached_active[:]
            active_in_lo = [x for x in lo if x in set(cached_active)]
            w = dict((x, i) for i, x in enumerate(lo))
            while active_in_lo:
                for i, (ordered, current) in enumerate(
                        zip(cached_active_copy, active_in_lo)):
                    if ordered != current:
                        for j, x in enumerate(active_in_lo[i:]):
                            if x == ordered: break
                            # x should be above ordered
                            to = w[ordered] + 1 + j
                            # make room
                            w = dict((x, i if i < to else i + 1) for x, i in
                                     w.iteritems())
                            w[x] = to # bubble them up !
                        active_in_lo.remove(ordered)
                        cached_active_copy = cached_active_copy[i + 1:]
                        active_in_lo = active_in_lo[i:]
                        break
                else: break
            fetched_lo = lo[:]
            lo.sort(key=w.get)
            if lo != fetched_lo:
                self._persist_load_order(lo, lo)
                bolt.deprint(u'Corrected %s (order of mods differed from '
                             u'their order in %s)' % (
                        self.loadorder_txt_path, self.plugins_txt_path))
        self.__update_lo_cache_info()
        return lo

    def _fetch_active_plugins(self):
        acti, _lo = self._parse_plugins_txt()
        if self.master_path in acti:
            acti.remove(self.master_path)
            self._write_plugins_txt(acti, acti)
            bolt.deprint(u'Removed %s from %s' % (
                self.master_path, self.plugins_txt_path))
        acti.insert(0, self.master_path)
        return acti

    def _persist_load_order(self, lord, active):
        _write_plugins_txt_(self.loadorder_txt_path, lord, lord, _star=False)
        self.__update_lo_cache_info()

    def _persist_active_plugins(self, active, lord): # must chop off Skyrim.esm
        self._write_plugins_txt(active[1:], active[1:])

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
            return (u'Active list order of plugins (%s) differs from supplied '
                    u'load order (%s)') % (_pl(old), _pl(acti))
        return u''

class AsteriskGame(Game):

    must_be_active_if_present = (bolt.GPath(u'DLCRobot.esm'),
                                 bolt.GPath(u'DLCworkshop01.esm'),
                                 bolt.GPath(u'DLCCoast.esm'),
                                 bolt.GPath(u'DLCWorkshop02.esm'),
                                 bolt.GPath(u'DLCWorkshop03.esm'),
                                 bolt.GPath(u'DLCNukaWorld.esm'),)

    def load_order_changed(self): return self._plugins_txt_modified()

    def _cached_or_fetch(self, cached_load_order, cached_active):
        # read the file once
        return self._fetch_load_order(cached_load_order, cached_active)

    @staticmethod
    def _must_update_active(deleted, reordered): return True

    # Abstract overrides ------------------------------------------------------
    def _fetch_load_order(self, cached_load_order, cached_active):
        """Read data from plugins.txt file. If plugins.txt does not exist
        create it. Discards information read if cached is passed in."""
        exists = self.plugins_txt_path.exists()
        active, lo = self._parse_modfile(self.plugins_txt_path) # empty if not exists
        lo, active = (lo if cached_load_order is None else cached_load_order,
                      active if cached_active is None else cached_active)
        if not exists:
            self._write_plugins_txt(lo, active)
            bolt.deprint(u'Created %s' % self.plugins_txt_path)
        return list(lo), list(active)

    def _persist_load_order(self, lord, active):
        assert active # must at least contain Fallout4.esm
        self._write_plugins_txt(lord, active)

    def _persist_active_plugins(self, active, lord):
        self._persist_load_order(lord, active)

    def _save_fixed_load_order(self, removed, added, reordered, fixed_active,
                               lo, active):
        if fixed_active: return # plugins.txt already saved
        if removed or added or reordered: self._persist_load_order(lo, active)

    def _persist_if_changed(self, active, lord, previous_active,
                            previous_lord):
        if (previous_lord is None or previous_lord != lord) or (
                previous_active is None or previous_active != active):
            self._persist_load_order(lord, active)

    # Modfiles parsing overrides ----------------------------------------------
    def _parse_modfile(self, path):
        if not path.exists(): return [], []
        acti, lo = _parse_plugins_txt_(path, self.mod_infos, _star=True)
        return acti, lo

    def _write_modfile(self, path, lord, active):
        _write_plugins_txt_(path, lord, active, _star=True)

def game_factory(name, mod_infos, plugins_txt_path, loadorder_txt_path=None):
    if name == u'Skyrim':
        return TextfileGame(mod_infos, plugins_txt_path, loadorder_txt_path)
    elif name == u'Fallout4':
        return AsteriskGame(mod_infos, plugins_txt_path)
    else:
        return TimestampGame(mod_infos, plugins_txt_path)

# Print helpers
def warn_lo_fixed(_addedFiles, _removedFiles, _reordered, duplicates,
                  lord, old_lord):
    if not (_removedFiles or _addedFiles or _reordered): return
    bolt.deprint(u'Fixed Load Order: added(%s), removed(%s), %sreordered %s'
             % (_pl(_addedFiles) or u'None', _pl(_removedFiles) or u'None',
                u'duplicates(%s), ' % (_pl(duplicates) if duplicates else u''),
                u'(No)' if not _reordered else _pl(old_lord, u'from:\n',
                            joint=u'\n') + _pl(lord, u'\nto:\n', joint=u'\n')))

def _pl(it, legend=u'', joint=u', '):
    return legend + joint.join(u'%s' % x for x in it) # use Path.__unicode__
