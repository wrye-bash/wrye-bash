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

from . import bolt, exception
from .bolt import forward_compat_path_to_fn_list, sig_to_str, FName
from .games_lo import LoGame, LoList, LoTuple, ParsedLo

# LoGame instance providing load order operations backend ---------------------
_lo_handler: LoGame | None = None
_plugins_txt_path = _loadorder_txt_path = _lord_pickle_path = None

def initialize_load_order_files(bass_dirs):
    global _plugins_txt_path, _loadorder_txt_path, _lord_pickle_path
    _plugins_txt_path = bass_dirs['lo'].join('plugins.txt')
    _loadorder_txt_path = bass_dirs['lo'].join('loadorder.txt')
    _lord_pickle_path = bass_dirs['saveBase'].join('BashLoadOrders.dat')

def initialize_load_order_handle(game_handle, bass_settings, *args):
    global _lo_handler, locked
    _lo_handler = game_handle.lo_handler(_plugins_txt_path, game_handle, *args,
        loadorder_txt_path=_loadorder_txt_path)
    __load_pickled_load_orders()
    locked = bass_settings.get('bosh.modInfos.resetMTimes', False)

# Lock load order API ---------------------------------------------------------
locked = False
warn_locked = False

def toggle_lock_load_order(user_warning_callback, bass_settings):
    global locked
    lock = not locked
    if lock:
        # Make sure the user actually wants to enable this
        lock = user_warning_callback()
    else:
        bass_settings['bash.load_order.lock_active_plugins'] = False
    bass_settings['bosh.modInfos.resetMTimes'] = locked = lock

# Saved load orders -----------------------------------------------------------
lo_entry = collections.namedtuple('lo_entry', ['date', 'lord'])
_saved_load_orders: list[lo_entry] = []
_current_list_index = -1
_lords_pickle: bolt.PickleDict | None = None
_LORDS_PICKLE_VERSION = 2
# active mod lists were saved in BashSettings.dat - sentinel needed for moving
# them to BashloadOrder.dat
__active_mods_sentinel = {}
_active_mods_lists = {}

def __load_pickled_load_orders():
    global _lords_pickle, _saved_load_orders, _current_list_index, \
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
    if b'Bethesda ESMs' in _active_mods_lists: ##:(734) backwards compat
        _active_mods_lists['Vanilla'] = _active_mods_lists[b'Bethesda ESMs']
        del _active_mods_lists[b'Bethesda ESMs']
    # transform load orders to FName
    _saved_load_orders = [lo_entry(date, LoadOrder(
        forward_compat_path_to_fn_list(lo.loadOrder),
        forward_compat_path_to_fn_list(lo.active, ret_type=set)))
                          for (date, lo) in _saved_load_orders]
    _active_mods_lists = {k: forward_compat_path_to_fn_list(v) for k, v in
                          _active_mods_lists.items()}

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

@dataclass(slots=True)
class LordDiff:
    """Diff of two LoadOrders - see LoadOrder.lo_diff for the fields use."""
    missing: set[FName] = field(default_factory=set) # del from lo <=> del mods
    added: set[FName] = field(default_factory=set) # new in lo <=> new mods
    reordered: set[FName] = field(default_factory=set)
    active_flips: set[FName] = field(default_factory=set)
    act_index_change: set[FName] = field(default_factory=set)
    # used to handle autoghosting and record diffs of modInfos _lo/_active_wip
    new_inact: set[FName] = field(default_factory=set)
    new_act: set[FName] = field(default_factory=set)
    # externally populate with plugins that need to be redrawn due to load
    # order changes, for instance merged plugins upon deactivating a patch
    affected: set[FName] = field(default_factory=set)

    def act_ord_status(self):
        """Return existing items whose active state or active order changed."""
        return {*self.active_flips, *self.act_index_change}

    def __ior__(self, other):
        for att in self.__slots__:
            getattr(self, att).update(getattr(other, att))
        return self

    def __bool__(self): # ONLY use in _lo_op
        return any(getattr(self, att) for att in self.__slots__)

    def __str__(self):
        st = []
        for att in ('missing', 'added', 'reordered', 'active_flips'):
            if diff := getattr(self, att):
                st.append(f'{att[0].upper()}{" ".join(att[1:].split("_"))}:'
                          f' {", ".join(sorted(diff))}')
        return '\n'.join(st)

class LoadOrder(object):
    """Immutable class representing a load order."""
    __empty = ()
    __none = frozenset()

    def __init__(self, loadOrder: Iterable[FName] = __empty,
            active: Iterable[FName] = __none):
        self._active = set_act = frozenset(active)
        self.mod_lo_index = {a: i for i, a in enumerate(loadOrder)}
        try: # below will raise a key error if mods in active have no loadOrder
            self._activeOrdered = tuple(
                sorted(set_act, key=self.mod_lo_index.__getitem__))
        except KeyError:
            raise exception.BoltError(f'Active mods with no load order: '
                f'{", ".join(set_act - self.mod_lo_index.keys())}')
        self._loadOrder = tuple(self.mod_lo_index)
        self.mod_act_index = {a: i for i, a in enumerate(self._activeOrdered)}

    @property
    def loadOrder(self): return self._loadOrder # test if empty
    @property
    def active(self): return self._active  # test if none
    @property
    def activeOrdered(self): return self._activeOrdered

    def lo_diff(self, other: LoadOrder):
        lodiff = LordDiff()
        # plugins missing from other and plugins that appear fresh in other
        lodiff.missing = self.mod_lo_index.keys() - other.mod_lo_index
        lodiff.added = other.mod_lo_index.keys() - self.mod_lo_index
        new_del = lodiff.missing | lodiff.added
        diff = self.mod_lo_index.items() ^ other.mod_lo_index.items()
        # present plugins that are not new and their load order differs
        lodiff.reordered = {k for k, _v in diff if k not in new_del}
        diff = self.mod_act_index.items() ^ other.mod_act_index.items()
        diff_count = collections.Counter(k for k, _v in diff)
        # if it appears twice, its active order changed
        lodiff.act_index_change = {k for k, c in diff_count.items() if c == 2}
        act_state_change = {k for k, c in diff_count.items() if c == 1}
        lodiff.active_flips = {k for k in act_state_change if k not in new_del}
        lodiff.new_inact = (act_state_change & self.active) - lodiff.missing
        lodiff.new_act = act_state_change & other.active
        return lodiff

    def as_lists(self) -> ParsedLo: # helper to provide mutable lo/active lists
        return [*self._loadOrder], [*self._activeOrdered]

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
                          self._loadOrder])

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

def cached_sort(mod_paths: Iterable[FName], *, __m=sys.maxsize) -> LoList:
    """Return a list containing mod_paths' elements sorted into load order.

    If some elements do not have a load order they are appended to the list
    in alphabetical, case insensitive order (used also to resolve
    modification time conflicts)."""
    return sorted(mod_paths, key=lambda fn: (
        _cached_lord.mod_lo_index.get(fn, __m), fn))

# Get and set API -------------------------------------------------------------
def save_lo(lord: LoList | None, acti: LoList | None, *, __index_move=0,
            quiet=False):
    """Save the Load Order (rewrite loadorder.txt or set modification times).

    Will update plugins.txt too if using the textfile method to reorder it
    as loadorder.txt, and of course rewrite it completely for AsteriskGame."""
    lord, acti, fix_lo = _lo_handler.set_load_order(lord, acti,
                                                    _cached_lord.as_lists())
    if not quiet:
        fix_lo.lo_deprint()
    return _update_cache(lord, acti, __index_move=__index_move)

def _update_cache(lord: LoList, acti_sorted: LoList, __index_move=0)->LordDiff:
    """Update module cache (_cached_lord and _saved_load_orders) and return
    the diff between the old and new load orders. If any of lord/acti_sorted
    is None, we are called from refresh_lo, and we need to get the load
    order from the game_handle. Else we are called from save_lo (with validated
    load order/active info), and we just need to update the caches."""
    global _cached_lord, _current_list_index
    lorddiff = _cached_lord.lo_diff(
        (_cached_lord := LoadOrder(lord, acti_sorted)))
    if new_entry := _current_list_index < 0 or (not __index_move and
            _cached_lord != _saved_load_orders[_current_list_index].lord):
        # either getting or setting, plant the new load order in
        _current_list_index += 1
    elif __index_move:  # attempted to undo/redo
        _current_list_index += __index_move
        target = _saved_load_orders[_current_list_index].lord
        if new_entry := target != _cached_lord: # we partially redid/undid
            # put it after (redo) or before (undo) the target
            _current_list_index += int(math.copysign(1, __index_move))
            # list[-1:-1] won't do what we want
            _current_list_index = max(0, _current_list_index)
    if new_entry:
        _saved_load_orders[_current_list_index:_current_list_index] = [
            lo_entry(time.time(), _cached_lord)]
    return lorddiff

# modInfos.refresh only!
def refresh_lo(unlock_lo: bool, rdata_mods, lock_act, *, booting=False):
    """Refresh _cached_lord, reverting if locked to the saved one. We pass
    the cached values to _game_handle.get_load_order (or None for load order
    if we pass unlock_lo or mods changed), which decides if those need update.
    For timestamp games we always calculate the load order, as this just
    involves getting ftime info from modInfos cache - that one **must be up to
    date** for correct load order/active validation, which is guaranteed
    as long as we call refresh_lo only inside modInfos.refresh."""
    global _cached_lord
    saved, old_cache = __lo_unset, _cached_lord
    if is_locked := not unlock_lo and locked and _saved_load_orders:
        saved: LoadOrder = _saved_load_orders[_current_list_index].lord
        if old_cache is not __lo_unset and old_cache != saved: # sanity check
            _cached_lord = __lo_unset # should not happen - raise
            raise Exception(f'Bug: {old_cache=} differs from {saved=}')
        # validate saved lo (remove/add deleted/added mods but also active
        # could change (think of a ccc file update) - append new mods)
        lord, acti, fix_lo = __validate(saved)
        if fix_lo.lo_changed() or fix_lo.act_changed():
            fixed = LoadOrder(lord, acti)
            sstr, fstr = ', '.join(saved.loadOrder), ', '.join(fixed.loadOrder)
            ldiff_fixed = saved.lo_diff(fixed)
            bolt.deprint('\n'.join([f'Saved load order is no longer valid:',
                f'{ldiff_fixed}', f'*** saved: {sstr}', f'*** fixed: {fstr}']))
            saved = fixed
    keep_cached = not unlock_lo and not rdata_mods
    lo, act = (None, None) if old_cache is __lo_unset else (
        old_cache.loadOrder if keep_cached else None, old_cache.activeOrdered)
    try:
        lo, act = _lo_handler.get_load_order(lo, act, rdata_mods, booting)
        ldiff = _update_cache(lo, act)
    except Exception as e:
        # LoadOrderBootError is known and fatal, we will be exiting, logging
        # and warning the user anyway; no need to deprint here
        if not isinstance(e, exception.LoadOrderBootError):
            bolt.deprint('Error updating load_order cache')
        _cached_lord = __lo_unset
        raise e
    if is_locked: # check if _cached_lord differs from saved
        if (ldiff_saved := _cached_lord.lo_diff(saved)).reordered or (
                lock_act and ldiff_saved.act_ord_status()):
            global warn_locked
            warn_locked = True
            li_lo, li_act = saved.as_lists()
            save_lo(li_lo, li_act if lock_act else None)
            return old_cache.lo_diff(_cached_lord)
    return ldiff

def __validate(saved): # not passing cached results in dry-run
    return _lo_handler.set_load_order(*saved.as_lists())

def get_active_mods_lists(bass_settings):
    """Get the user active mods lists from BashLoadOrder.dat, except if they
    are still saved in BashSettings.dat"""
    global _active_mods_lists
    if _active_mods_lists is __active_mods_sentinel:
        settings_mods_list = bass_settings.get('bash.loadLists.data',
                                               __active_mods_sentinel)
        _active_mods_lists = settings_mods_list
    return _active_mods_lists

def undo_redo_load_order(index_move):
    index = _current_list_index + index_move
    if index < 0 or index > len(_saved_load_orders) - 1: return LordDiff()
    previous = _saved_load_orders[index].lord
    lord, acti, _fix_lo = __validate(previous)
    previous = LoadOrder(lord, acti) # possibly fixed with new mods appended
    if previous == _cached_lord: # increase or decrease by 1
        return undo_redo_load_order(
            index_move + int(math.copysign(1, index_move)))
    return save_lo(*previous.as_lists(), __index_move=index_move, quiet=True)

# _game_handle wrappers -------------------------------------------------------
def master_sort(*args, **kwargs):
    return _lo_handler.lo_sort_key(*args, **kwargs)

def check_active_limit(*args, **kwargs):
    return _lo_handler.check_active_limit(*args, **kwargs)

def swap(*args):
    return _lo_handler.swap(*args)

def filter_pinned(mod_set) -> LoList:
    """Return a list of plugins that we can't change their load order."""
    mod_set = {*mod_set}
    return [k for k in _lo_handler.fixed_order_plugins if k in mod_set]

def must_be_active(imods) -> set[FName]:
    return {k for k in imods if _lo_handler.pin_active_state.get(k)}

def get_lo_files() -> list[bolt.Path]:
    """Retrieve a set of all files used by this game for storing load order."""
    # The order of these is an implementation detail, hide it ouside the game
    # implementations
    return sorted(set(_lo_handler.get_lo_files()))
