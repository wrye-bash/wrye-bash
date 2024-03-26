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
#  Mopy/bash/load_order.py copyright (C) 2016 Utumno: Original design
#
# =============================================================================
"""Load order management, features caching, load order locking and undo/redo.

Notes:
- _cached_lord is a cache exported to the next level of the load order API,
namely ModInfos. Do _not_ use outside of ModInfos. Must be valid at all
times. Should be updated on tabbing out and back in to Bash and on setting
lo/active from inside Bash.
- active mods must always be manipulated having a valid load order at hand:
 - all active mods must be present and have a load order and
 - especially for skyrim the relative order of entries in plugins.txt must be
 the same as their relative load order in loadorder.txt
- corrupted files do not have a load order.
- modInfos singleton must be up to date when calling the API methods that
delegate to the game_handle.
"""
from __future__ import annotations

__author__ = 'Utumno'

import collections
import math
import sys
import time
from collections.abc import Iterable
from dataclasses import dataclass, field

from . import bass, bolt, exception
from ._games_lo import FixInfo, INIGame, LoGame, LoList, LoTuple
from .bolt import forward_compat_path_to_fn_list, sig_to_str, FName

# LoGame instance providing load order operations API
_game_handle: LoGame | None = None
_plugins_txt_path = _loadorder_txt_path = _lord_pickle_path = None
# Load order locking
locked = False
warn_locked = False
_lords_pickle: bolt.PickleDict | None = None
_LORDS_PICKLE_VERSION = 2
# active mod lists were saved in BashSettings.dat - sentinel needed for moving
# them to BashloadOrder.dat
__active_mods_sentinel = {}
_active_mods_lists = {}

def initialize_load_order_files():
    if bass.dirs['saveBase'] == bass.dirs['app']:
        #--If using the game directory as rather than the appdata dir.
        _dir = bass.dirs['app']
    else:
        _dir = bass.dirs['userApp']
    global _plugins_txt_path, _loadorder_txt_path, _lord_pickle_path
    _plugins_txt_path = _dir.join('plugins.txt')
    _loadorder_txt_path = _dir.join('loadorder.txt')
    _lord_pickle_path = bass.dirs['saveBase'].join('BashLoadOrders.dat')

def initialize_load_order_handle(mod_infos, game_handle):
    global _game_handle
    _game_handle = game_handle.lo_handler(mod_infos, _plugins_txt_path,
        loadorder_txt_path=_loadorder_txt_path)
    __load_pickled_load_orders()

# Saved load orders -----------------------------------------------------------
lo_entry = collections.namedtuple('lo_entry', ['date', 'lord'])
_saved_load_orders: list[lo_entry] = []
_current_list_index = -1

def __load_pickled_load_orders():
    global _lords_pickle, _saved_load_orders, _current_list_index, locked, \
        _active_mods_lists
    _lords_pickle = bolt.PickleDict(_lord_pickle_path)
    _lords_pickle.load()
    if _lords_pickle.vdata.get('_lords_pickle_version',
                               1) < _LORDS_PICKLE_VERSION:
        # used to load active lists from settings
        active_mods_list = __active_mods_sentinel
    else:
        active_mods_list = {}
    _get = lambda x, d: _lords_pickle.pickled_data.get(
        x, d) or _lords_pickle.pickled_data.get(x.encode('ascii'), d)
    _saved_load_orders = _get('_saved_load_orders', [])
    _current_list_index = _get('_current_list_index', -1)
    _active_mods_lists = _get('_active_mods_lists', active_mods_list)
    if b'Bethesda ESMs' in _active_mods_lists: ##: backwards compat
        _active_mods_lists['Vanilla'] = _active_mods_lists[b'Bethesda ESMs']
        del _active_mods_lists[b'Bethesda ESMs']
    # transform load orders to FName
    _saved_load_orders = [lo_entry(date, LoadOrder(
        forward_compat_path_to_fn_list(lo.loadOrder),
        forward_compat_path_to_fn_list(lo.active, ret_type=set)))
                          for (date, lo) in _saved_load_orders]
    _active_mods_lists = {k: forward_compat_path_to_fn_list(v) for k, v in
                          _active_mods_lists.items()}
    locked = bass.settings.get('bosh.modInfos.resetMTimes', False)

def persist_orders(__keep_max=256):
    _lords_pickle.vdata['_lords_pickle_version'] = _LORDS_PICKLE_VERSION
    length = len(_saved_load_orders)
    if length > __keep_max:
        x, y = _keep_max(__keep_max, length)
        _lords_pickle.pickled_data['_saved_load_orders'] = \
            _saved_load_orders[_current_list_index - x:_current_list_index + y]
        _lords_pickle.pickled_data['_current_list_index'] = x
    else:
        _lords_pickle.pickled_data['_saved_load_orders'] = _saved_load_orders
        _lords_pickle.pickled_data['_current_list_index'] = _current_list_index
    _lords_pickle.pickled_data['_active_mods_lists'] = _active_mods_lists
    _lords_pickle.save()

def _keep_max(max_to_keep, length):
    max_2 = max_to_keep // 2
    y = length - _current_list_index
    if y <= max_2:
        x = max_to_keep - y
    else:
        if _current_list_index > max_2:
            x = y = max_2
        else:
            x, y = _current_list_index, max_to_keep - _current_list_index
    return x, y

def _new_entry():
    _saved_load_orders[_current_list_index:_current_list_index] = [
        lo_entry(time.time(), _cached_lord)]

@dataclass(slots=True)
class LordDiff: ##: a cousin of both FixInfo and RefrData (property overrides?)
    """Diff of two LoadOrders - see LoadOrder.lo_diff for the fields use."""
    missing: set[FName] = field(default_factory=set) # del from lo <=> del mods
    added: set[FName] = field(default_factory=set) # new in lo <=> new mods
    reordered: set[FName] = field(default_factory=set)
    active_flips: set[FName] = field(default_factory=set)
    act_index_change: set[FName] = field(default_factory=set)
    act_del: set[FName] = field(default_factory=set)
    act_new: set[FName] = field(default_factory=set)
    # externally populate with plugins that need to be redrawn due to load
    # order changes, for instance merged plugins upon deactivating a patch
    affected: set[FName] = field(default_factory=set)

    def act_changed(self):
        """Return items whose active state or active order changed."""
        return {*self.active_flips, *self.act_index_change, *self.act_del,
                *self.act_new}

    def lo_changed(self):
        return self.added or self.missing or self.reordered

class LoadOrder(object):
    """Immutable class representing a load order."""
    __empty = ()
    __none = frozenset()

    def __init__(self, loadOrder: Iterable[FName] = __empty,
            active: Iterable[FName] = __none):
        set_act = frozenset(active)
        if missing := (set_act - set(loadOrder)):
            raise exception.BoltError(
                f'Active mods with no load order: {", ".join(missing)}')
        self._loadOrder = tuple(loadOrder)
        self._active = set_act
        self.mod_lo_index = {a: i for i, a in enumerate(loadOrder)}
        # below would raise key error if active have no loadOrder
        self._activeOrdered = tuple(
            sorted(active, key=self.mod_lo_index.__getitem__))
        self.mod_act_index = {a: i for i, a in enumerate(self._activeOrdered)}

    @property
    def loadOrder(self): return self._loadOrder # test if empty
    @property
    def active(self): return self._active  # test if none
    @property
    def activeOrdered(self): return self._activeOrdered

    def lo_diff(self, other: LoadOrder):
        ldiff = LordDiff()
        # plugins missing from other and plugins that appear fresh in other
        ldiff.missing = self.mod_lo_index.keys() - other.mod_lo_index
        ldiff.added = other.mod_lo_index.keys() - self.mod_lo_index
        new_del = ldiff.missing | ldiff.added
        diff = self.mod_lo_index.items() ^ other.mod_lo_index.items()
        # present plugins that are not new and their load order differs
        ldiff.reordered = {k for k, _v in diff if k not in new_del}
        diff = self.mod_act_index.items() ^ other.mod_act_index.items()
        diff_count = collections.Counter(k for k, _v in diff)
        # if it appears twice, its active order changed
        ldiff.act_index_change = {k for k, c in diff_count.items() if c == 2}
        act_state_change = {k for k, c in diff_count.items() if c == 1}
        ldiff.active_flips = {k for k in act_state_change if k not in new_del}
        ldiff.act_del = act_state_change & self.active
        ldiff.act_new = act_state_change & other.active
        return ldiff

    def __eq__(self, other):
        return isinstance(other, LoadOrder) and self._active == other._active \
               and self._loadOrder == other._loadOrder
    def __ne__(self, other): return not (self == other)
    def __hash__(self): return hash((self._loadOrder, self._active))

    def __getstate__(self): # we pickle _activeOrdered to avoid recreating it
        return {'_activeOrdered': self._activeOrdered,
                '_loadOrder': self.loadOrder}

    def __setstate__(self, dct):
        if not all(isinstance(k, str) for k in dct): # bytes keys from older versions
            dct = {sig_to_str(k): v for k, v in dct.items()}
        for k in ('_activeOrdered', '_loadOrder'):
            if k not in dct:
                bolt.deprint(f'Unpickling {dct} missing "{k}"')
                dct[k] = tuple()
        self.__dict__.update(dct)   # update attributes # __dict__ prints empty
        self._active = frozenset(self._activeOrdered)
        self.mod_lo_index = {a: i for i, a in enumerate(self._loadOrder)}
        self.mod_act_index = {a: i for i, a in enumerate(self._activeOrdered)}

    def __str__(self):
        return ', '.join([(f'*{x}' if x in self._active else x) for x in
                          self.loadOrder])

# Module level cache ----------------------------------------------------------
__lo_unset = LoadOrder() # load order is not yet set or we failed to set it
_cached_lord = __lo_unset # must always be valid (or __lo_unset)

# _cached_lord getters - make sure the cache is valid when using them ---------
def cached_active_tuple() -> LoTuple:
    """Return the currently cached active mods in load order as a tuple."""
    return _cached_lord.activeOrdered

def cached_lo_tuple() -> LoTuple:
    """Return the currently cached load order (including inactive mods) as a
    tuple."""
    return _cached_lord.loadOrder

def cached_is_active(mod):
    """Return true if the mod is in the current active mods cache."""
    return mod in _cached_lord.active

# Load order and active indexes
def cached_lo_index(mod): return _cached_lord.mod_lo_index[mod]

def cached_active_index_str(mod):
    return '' if (dex := _cached_lord.mod_act_index.get(mod)) is None else \
        f'{dex:02X}'

def cached_lower_loading(mod):
    return _cached_lord.loadOrder[:_cached_lord.mod_lo_index[mod]]

def get_ordered(mod_paths: Iterable[FName], *, __m=sys.maxsize) -> list[FName]:
    """Return a list containing mod_paths' elements sorted into load order.

    If some elements do not have a load order they are appended to the list
    in alphabetical, case insensitive order (used also to resolve
    modification time conflicts)."""
    return sorted(mod_paths, key=lambda fn: (
        _cached_lord.mod_lo_index.get(fn, __m), fn))

# Get and set API -------------------------------------------------------------
def save_lo(lord, acti=None, __index_move=0, quiet=False):
    """Save the Load Order (rewrite loadorder.txt or set modification times).

    Will update plugins.txt too if using the textfile method to reorder it
    as loadorder.txt, and of course rewrite it completely for AsteriskGame."""
    acti_list = None if acti is None else list(acti)
    load_list = None if lord is None else list(lord)
    fix_lo = None if quiet else FixInfo()
    lord, acti = _game_handle.set_load_order(load_list, acti_list, # pass lists
      [*_cached_lord.loadOrder], [*_cached_lord.activeOrdered], fix_lo=fix_lo)
    if not quiet:
        fix_lo.lo_deprint()
    return _update_cache(lord, acti, __index_move=__index_move)

def _update_cache(lord: LoList, acti_sorted: LoList, __index_move=0):
    """Update module cache (_cached_lord and _saved_load_orders) and return
    the diff between the old and new load orders. If any of lord/acti_sorted
    is None, we are called from refresh_lo, and we need to get the load
    order from the game_handle. Else we are called from save_lo, and we just
    need to update the caches."""
    global _cached_lord
    try:
        if lord is None or acti_sorted is None: # really go get load order
            fix_lo = FixInfo()
            lord, acti_sorted = _game_handle.get_load_order(lord, acti_sorted,
                                                            fix_lo)
            fix_lo.lo_deprint()
        return _cached_lord.lo_diff(
            (_cached_lord := LoadOrder(lord, acti_sorted)))
    except Exception:
        bolt.deprint('Error updating load_order cache')
        _cached_lord = __lo_unset
        raise
    finally:
        if _cached_lord is not __lo_unset:
            global _current_list_index
            if _current_list_index < 0 or (not __index_move and
                _cached_lord != _saved_load_orders[_current_list_index].lord):
                # either getting or setting, plant the new load order in
                _current_list_index += 1
                _new_entry()
            elif __index_move: # attempted to undo/redo
                _current_list_index += __index_move
                target = _saved_load_orders[_current_list_index].lord
                if target != _cached_lord: # we partially redid/undid
                    # put it after (redo) or before (undo) the target
                    _current_list_index += int(math.copysign(1, __index_move))
                     # list[-1:-1] won't do what we want
                    _current_list_index = max (0, _current_list_index)
                    _new_entry()

def refresh_lo(cached: bool, cached_active: bool):
    """Refresh _cached_lord, reverting if locked to the saved one. If any of
    cached or cached_active are True, we will keep the cached values for
    those except if _game_handle.***_changed() respective methods return
    True. In the case of timestamp games, cached is effectively always False,
    as load_order_changed returns True - that's not slow, as getting the load
    order just involves getting ftime info from modInfos cache. This last one
    **must be up to date** for correct load order/active validation."""
    if locked and _saved_load_orders:
        saved: LoadOrder = _saved_load_orders[_current_list_index].lord
        if _cached_lord is not __lo_unset:
            if _cached_lord != saved: # sanity check, should not happen
                bolt.deprint(f'Bug: {_cached_lord=} differs from {saved=}')
        # validate saved lo (remove/add deleted/added mods - new mods should
        # be appended - note fix_lo is None)
        lord, acti = _game_handle.set_load_order(
            list(saved.loadOrder), list(saved.activeOrdered))
        fixed = LoadOrder(lord, acti)
        if fixed != saved:
            bolt.deprint(f'*** Saved load order is no longer valid: {saved}\n'
                         f'*** Corrected to {fixed}: {saved.lo_diff(fixed)}')
            saved = fixed
        # rest of Bash should only use _cached_lord so since we eventually
        # might impose saved (to move new plugins at the end for instance)
        # cache the diff from _cached_lord to saved to return in that case
        ldiff_saved = _cached_lord.lo_diff(saved)
    else: saved = __lo_unset
    if _cached_lord is not __lo_unset:
        lo, active = _game_handle._request_cache_update(
            _cached_lord.loadOrder if cached else None,
            _cached_lord.activeOrdered if cached_active else None)
    else: active = lo = None
    ldiff = _update_cache(lo, active)
    if saved is not __lo_unset:
        if _cached_lord.loadOrder != saved.loadOrder or (
           _cached_lord.active != saved.active and #active order doesn't matter ##: was true for oblivion still valid?
           bass.settings['bash.load_order.lock_active_plugins']):
            global warn_locked
            warn_locked = True
            save_lo(saved.loadOrder, saved.activeOrdered)
            return ldiff_saved
    return ldiff

def get_active_mods_lists():
    """Get the user active mods lists from BashLoadOrder.dat, except if they
    are still saved in BashSettings.dat"""
    global _active_mods_lists
    if _active_mods_lists is __active_mods_sentinel:
        settings_mods_list = bass.settings.get('bash.loadLists.data',
                                               __active_mods_sentinel)
        _active_mods_lists = settings_mods_list
    return _active_mods_lists

def undo_load_order(): return _restore_lo(-1)

def redo_load_order(): return _restore_lo(1)

def _restore_lo(index_move):
    index = _current_list_index + index_move
    if index < 0 or index > len(_saved_load_orders) - 1: return _cached_lord
    previous = _saved_load_orders[index].lord
    # fix previous
    lord, acti = _game_handle.set_load_order(list(previous.loadOrder),
                                             list(previous.activeOrdered))
    previous = LoadOrder(lord, acti) # possibly fixed with new mods appended
    if previous == _cached_lord: # increase or decrease by 1
        index_move += int(math.copysign(1, index_move))
        return _restore_lo(index_move)
    return save_lo(previous.loadOrder, previous.activeOrdered,
                   __index_move=index_move, quiet=True)

# _game_handle wrappers -------------------------------------------------------
def check_active_limit(mods):
    return _game_handle.check_active_limit(mods)

def max_espms():
    return _game_handle.max_espms

def max_esls():
    return _game_handle.max_esls

def swap(old_dir, new_dir):
    return _game_handle.swap(old_dir, new_dir)

def filter_pinned(imods, remove=False, fixed_order=True):
    """Keep only mods that are always active from imods (or remove them if
    remove is True). If fixed_order is True, only always active mods with a
    fixed order will be considered (one known case those differ)."""
    pinned = _game_handle.fixed_order_always_active() if fixed_order else {
        *_game_handle.must_be_active_if_present}
    if remove:
        return [m for m in imods if m not in pinned]
    return [m for m in imods if m in pinned]

def using_ini_file(): return isinstance(_game_handle, INIGame)

def get_lo_files():
    """Returns a list of all files used by this game for storing load
    order."""
    return sorted(_game_handle.get_lo_files())

# Timestamp games helpers
def has_load_order_conflict(mod_name):
    return _game_handle.has_load_order_conflict(mod_name)

def has_load_order_conflict_active(mod_name):
    if not cached_is_active(mod_name): return False
    return _game_handle.has_load_order_conflict_active(mod_name,
                                                       _cached_lord.active)

def set_mtime_order(previous, previous_index, new_mod):
    return _game_handle.set_mtime_order(previous, previous_index, new_mod)

# Lock load order -------------------------------------------------------------
def toggle_lock_load_order(user_warning_callback):
    global locked
    lock = not locked
    if lock:
        # Make sure the user actually wants to enable this
        lock = user_warning_callback()
    bass.settings['bosh.modInfos.resetMTimes'] = locked = lock

class Unlock:
    """Context manager to temporarily unlock the load order."""

    def __init__(self, do_unlock=True):
        self._do_unlock = do_unlock

    def __enter__(self):
        global locked
        self.__locked = locked
        locked = False if self._do_unlock else locked

    def __exit__(self, exc_type, exc_val, exc_tb):
        global locked
        locked = self.__locked
