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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#  Mopy/bash/load_order.py copyright (C) 2016 Utumno: Original design
#
# =============================================================================
"""Load order management, features caching, load order locking and undo/redo.

Notes:
- cached_lord is a cache exported to the next level of the load order API,
namely ModInfos. Do _not_ use outside of ModInfos. Must be valid at all
times. Should be updated on tabbing out and back in to Bash and on setting
lo/active from inside Bash.
- active mods must always be manipulated having a valid load order at hand:
 - all active mods must be present and have a load order and
 - especially for skyrim the relative order of entries in plugin.txt must be
 the same as their relative load order in loadorder.txt
- corrupted files do not have a load order.
- modInfos singleton must be up to date when calling the API methods that
delegate to the game_handle.
"""

__author__ = u'Utumno'

import sys
import math
import collections
import time

# Internal
from . import bass, bolt, bush, exception
from .bolt import sig_to_str
# Game instance providing load order operations API
from . import _games_lo

_game_handle = None # type: _games_lo.Game
_plugins_txt_path = _loadorder_txt_path = _lord_pickle_path = None
# Load order locking
locked = False
warn_locked = False
_lords_pickle = None # type: bolt.PickleDict
_LORDS_PICKLE_VERSION = 2
# active mod lists were saved in BashSettings.dat - sentinel needed for moving
# them to BashloadOrder.dat
__active_mods_sentinel = {}
_active_mods_lists = {}

def in_master_block(minf):
    return _game_handle.in_master_block(minf) # minf is a master or mod info

def check_active_limit(mods):
    return _game_handle.check_active_limit(mods)

def max_espms():
    return _game_handle.max_espms

def max_esls():
    return _game_handle.max_esls

def initialize_load_order_files():
    if bass.dirs[u'saveBase'] == bass.dirs[u'app']:
        #--If using the game directory as rather than the appdata dir.
        _dir = bass.dirs[u'app']
    else:
        _dir = bass.dirs[u'userApp']
    global _plugins_txt_path, _loadorder_txt_path, _lord_pickle_path
    _plugins_txt_path = _dir.join(u'plugins.txt')
    _loadorder_txt_path = _dir.join(u'loadorder.txt')
    _lord_pickle_path = bass.dirs[u'saveBase'].join(u'BashLoadOrders.dat')

def initialize_load_order_handle(mod_infos):
    global _game_handle
    _game_handle = _games_lo.game_factory(bush.game.fsName, mod_infos,
                                          _plugins_txt_path,
                                          _loadorder_txt_path)
    _game_handle.parse_ccc_file()
    _game_handle.print_lo_paths()
    __load_pickled_load_orders()

class LoadOrder(object):
    """Immutable class representing a load order."""
    __empty = ()
    __none = frozenset()

    def __init__(self, loadOrder=__empty, active=__none):
        """:type loadOrder: list | set | tuple
        :type active: list | set | tuple"""
        if set(active) - set(loadOrder):
            raise exception.BoltError(
                u'Active mods with no load order: ' + u', '.join(
                    [x.s for x in (set(active) - set(loadOrder))]))
        self._loadOrder = tuple(loadOrder)
        self._active = frozenset(active)
        self.__mod_loIndex = {a: i for i, a in enumerate(loadOrder)}
        # below would raise key error if active have no loadOrder
        self._activeOrdered = tuple(
            sorted(active, key=self.__mod_loIndex.__getitem__))
        self.__mod_actIndex = {a: i for i, a in enumerate(self._activeOrdered)}

    @property
    def loadOrder(self): return self._loadOrder # test if empty
    @property
    def active(self): return self._active  # test if none
    @property
    def activeOrdered(self): return self._activeOrdered

    def __eq__(self, other):
        return isinstance(other, LoadOrder) and self._active == other._active \
               and self._loadOrder == other._loadOrder
    def __ne__(self, other): return not (self == other)
    def __hash__(self): return hash((self._loadOrder, self._active))

    def lindex(self, mname): return self.__mod_loIndex[mname] # KeyError
    def lorder(self, paths):
        """Return a tuple containing the given paths in their load order.
        :param paths: iterable of paths that must all have a load order
        :type paths: collections.Iterable[bolt.Path]
        :rtype: tuple
        """
        return tuple(sorted(paths, key=self.__mod_loIndex.__getitem__))
    def activeIndex(self, mname): return self.__mod_actIndex[mname]

    def __getstate__(self): # we pickle _activeOrdered to avoid recreating it
        return {u'_activeOrdered': self._activeOrdered,
                u'_loadOrder': self.loadOrder}

    def __setstate__(self, dct):
        if not all(isinstance(k, str) for k in dct): # bytes keys from older versions
            dct = {sig_to_str(k): v for k, v in dct.items()}
        for k in ('_activeOrdered', '_loadOrder'):
            if k not in dct:
                bolt.deprint(f'Unpickling {dct} missing "{k}"')
                dct[k] = tuple()
        self.__dict__.update(dct)   # update attributes # __dict__ prints empty
        self._active = frozenset(self._activeOrdered)
        self.__mod_loIndex = {a: i for i, a in enumerate(self._loadOrder)}
        self.__mod_actIndex = {a: i for i, a in enumerate(self._activeOrdered)}

    def __str__(self):
        return u', '.join([((u'*%s' if x in self._active else u'%s') % x)
                           for x in self.loadOrder])

# Module level cache
__empty = LoadOrder()
cached_lord = __empty # must always be valid (or __empty)

# Saved load orders
lo_entry = collections.namedtuple(u'lo_entry', [u'date', u'lord'])
_saved_load_orders = [] # type: list[lo_entry]
_current_list_index = -1

def _new_entry():
    _saved_load_orders[_current_list_index:_current_list_index] = [
        lo_entry(time.time(), cached_lord)]

def persist_orders(__keep_max=256):
    _lords_pickle.vdata[u'_lords_pickle_version'] = _LORDS_PICKLE_VERSION
    length = len(_saved_load_orders)
    if length > __keep_max:
        x, y = _keep_max(__keep_max, length)
        _lords_pickle.pickled_data[u'_saved_load_orders'] = \
            _saved_load_orders[_current_list_index - x:_current_list_index + y]
        _lords_pickle.pickled_data[u'_current_list_index'] = x
    else:
        _lords_pickle.pickled_data[u'_saved_load_orders'] = _saved_load_orders
        _lords_pickle.pickled_data[u'_current_list_index'] = _current_list_index
    _lords_pickle.pickled_data[u'_active_mods_lists'] = _active_mods_lists
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

# Load Order utility methods - make sure the cache is valid when using them
def cached_active_tuple():
    """Return the currently cached active mods in load order as a tuple.

    :rtype: tuple[bolt.Path]"""
    return cached_lord.activeOrdered

def cached_lo_tuple():
    """Return the currently cached load order (including inactive mods) as a
    tuple.

    :rtype: tuple[bolt.Path]"""
    return cached_lord.loadOrder

def cached_is_active(mod):
    """Return true if the mod is in the current active mods cache."""
    return mod in cached_lord.active

# Load order and active indexes
def cached_lo_index(mod): return cached_lord.lindex(mod)

def cached_lo_index_or_max(mod):
    try:
        return cached_lo_index(mod)
    except KeyError:
        return sys.maxsize # sort mods that do not have a load order LAST

def cached_active_index(mod): return cached_lord.activeIndex(mod)

def cached_lower_loading(mod):
    return cached_lord.loadOrder[:cached_lo_index(mod)]

def cached_higher_loading(mod):
    return cached_lord.loadOrder[cached_lo_index(mod):]

def get_ordered(mod_paths):
    """Return a list containing mod_paths' elements sorted into load order.

    If some elements do not have a load order they are appended to the list
    in alphabetical, case insensitive order (used also to resolve
    modification time conflicts).
    :type mod_paths: collections.Iterable[bolt.Path]
    :rtype : list[bolt.Path]
    """
    # resolve time conflicts or no load order
    mod_paths = sorted(mod_paths)
    mod_paths.sort(key=cached_lo_index_or_max)
    return mod_paths

def filter_pinned(imods):
    pinn = _game_handle.pinned_mods()
    return [m for m in imods if m in pinn]

def find_first_difference(lo_a, acti_a, lo_b, acti_b):
    """Returns the first different index (in terms of LO indices) between two
    load orders A and B. Returns None if the two are identical (but don't use
    it for that, just compare tuples :P)."""
    # Acts as a replacement for cached_lo_index
    lindex_a = {p: i for i, p in enumerate(lo_a)}
    lindex_b = {p: i for i, p in enumerate(lo_b)}
    # Look for the first difference between the LOs
    low_diff = (None, None)
    for a, b in zip(lo_a, lo_b):
        if a != b:
            low_diff = (a, b)
            break
    if low_diff != (None, None):
        # We found a difference, use the smaller of the two indices into each
        # load orders' LO list
        low_lo = min(lindex_a[low_diff[0]], lindex_b[low_diff[1]])
    elif len(lo_a) != len(lo_b):
        # We found no difference but the lengths are different, so plugins have
        # been removed from the end of one of them
        low_lo = min(len(lo_a), len(lo_b))
    else: low_lo = None # no difference in LO
    # Then do the exact same thing with actives
    low_diff = (None, None)
    for a, b in zip(acti_a, acti_b):
        if a != b:
            low_diff = (a, b)
            break
    if low_diff != (None, None):
        low_acti = min(lindex_a[low_diff[0]], lindex_b[low_diff[1]])
    elif len(acti_a) != len(acti_b):
        low_acti = min(len(acti_a), len(acti_b))
    else: low_acti = None
    # Finally, we need to deal with cases where one of the two is None and
    # return the smaller result
    if low_lo is None: return low_acti
    elif low_acti is None: return low_lo
    else: return min(low_lo, low_acti)

# Get and set API -------------------------------------------------------------
def save_lo(lord, acti=None, __index_move=0, quiet=False):
    """Save the Load Order (rewrite loadorder.txt or set modification times).

    Will update plugins.txt too if using the textfile method to reorder it
    as loadorder.txt, and of course rewrite it completely for fallout 4 (
    asterisk method)."""
    acti_list = list(acti) if acti is not None else None
    load_list = list(lord) if lord is not None else None
    fix_lo = _games_lo.FixInfo() if not quiet else None
    lord, acti = _game_handle.set_load_order(load_list, acti_list,
                                             list(cached_lord.loadOrder),
                                             list(cached_lord.activeOrdered),
                                             fix_lo=fix_lo)
    if fix_lo: fix_lo.lo_deprint()
    _update_cache(lord=lord, acti_sorted=acti, __index_move=__index_move)
    return cached_lord

def _update_cache(lord=None, acti_sorted=None, __index_move=0):
    """
    :type lord: tuple[bolt.Path] | list[bolt.Path]
    :type acti_sorted: tuple[bolt.Path] | list[bolt.Path]
    """
    global cached_lord
    try:
        fix_lo = _games_lo.FixInfo()
        lord, acti_sorted = _game_handle.get_load_order(lord, acti_sorted,
                                                        fix_lo)
        fix_lo.lo_deprint()
        cached_lord = LoadOrder(lord, acti_sorted)
    except Exception:
        bolt.deprint(u'Error updating load_order cache')
        cached_lord = __empty
        raise
    finally:
        if cached_lord is not __empty:
            global _current_list_index
            if _current_list_index < 0 or (not __index_move and
                cached_lord != _saved_load_orders[_current_list_index].lord):
                # either getting or setting, plant the new load order in
                _current_list_index += 1
                _new_entry()
            elif __index_move: # attempted to undo/redo
                _current_list_index += __index_move
                target = _saved_load_orders[_current_list_index].lord
                if target != cached_lord: # we partially redid/undid
                    # put it after (redo) or before (undo) the target
                    _current_list_index += int(math.copysign(1, __index_move))
                     # list[-1:-1] won't do what we want
                    _current_list_index = max (0, _current_list_index)
                    _new_entry()

def refresh_lo(cached=False, cached_active=True):
    """Refresh cached_lord, reverting if locked to the saved one. If any of
    cached or cached_active are True, we will keep the cached values for
    those except if _game_handle.***_changed() respective methods return
    True. In the case of timestamp games, cached is effectively always False,
    as load_order_changed returns True - that's not slow, as getting the load
    order just involves getting mtime info from modInfos cache. This last one
    **must be up to date** for correct load order/active validation."""
    if locked and _saved_load_orders:
        saved = _saved_load_orders[_current_list_index].lord # type: LoadOrder
        lord, acti = _game_handle.set_load_order( # make sure saved lo is valid
            list(saved.loadOrder), list(saved.activeOrdered), dry_run=True)
        fixed = LoadOrder(lord, acti)
        if fixed != saved:
            bolt.deprint(u'Saved load order is no longer valid: %s'
                         u'\nCorrected to %s' % (saved, fixed))
        saved = fixed
    else: saved = __empty
    if cached_lord is not __empty:
        lo = cached_lord.loadOrder if (
            cached and not _game_handle.load_order_changed()) else None
        active = cached_lord.activeOrdered if (
            cached_active and not _game_handle.active_changed()) else None
    else: active = lo = None
    _update_cache(lo, active)
    if locked and saved is not __empty:
        if cached_lord.loadOrder != saved.loadOrder or (
           cached_lord.active != saved.active and # active order doesn't matter
           bass.settings[u'bash.load_order.lock_active_plugins']):
            save_lo(saved.loadOrder, saved.activeOrdered)
            global warn_locked
            warn_locked = True

def __load_pickled_load_orders():
    global _lords_pickle, _saved_load_orders, _current_list_index, locked, \
        _active_mods_lists
    _lords_pickle = bolt.PickleDict(_lord_pickle_path)
    _lords_pickle.load()
    if _lords_pickle.vdata.get(u'_lords_pickle_version', 1) < _LORDS_PICKLE_VERSION:
        # used to load active lists from settings
        active_mods_list = __active_mods_sentinel
    else:
        active_mods_list = {}
    _get = lambda x, d: _lords_pickle.pickled_data.get(
        x, d) or _lords_pickle.pickled_data.get(x.encode(u'ascii'), d)
    _saved_load_orders = _get(u'_saved_load_orders', [])
    _current_list_index = _get(u'_current_list_index', -1)
    _active_mods_lists = _get(u'_active_mods_lists', active_mods_list)
    if b'Bethesda ESMs' in _active_mods_lists: ##: backwards compat
        _active_mods_lists[u'Vanilla'] = _active_mods_lists[b'Bethesda ESMs']
        del _active_mods_lists[b'Bethesda ESMs']
    locked = bass.settings.get(u'bosh.modInfos.resetMTimes', False)

def get_active_mods_lists():
    """Get the user active mods lists from BashLoadOrder.dat, except if they
    are still saved in BashSettings.dat"""
    global _active_mods_lists
    if _active_mods_lists is __active_mods_sentinel:
        settings_mods_list = bass.settings.get(u'bash.loadLists.data',
                                               __active_mods_sentinel)
        _active_mods_lists = settings_mods_list
    return _active_mods_lists

def undo_load_order(): return _restore_lo(-1)

def redo_load_order(): return _restore_lo(1)

def _restore_lo(index_move):
    index = _current_list_index + index_move
    if index < 0 or index > len(_saved_load_orders) - 1: return cached_lord
    previous = _saved_load_orders[index].lord
    # fix previous
    lord, acti = _game_handle.set_load_order(list(previous.loadOrder),
                                             list(previous.activeOrdered),
                                             dry_run=True)
    previous = LoadOrder(lord, acti) # possibly fixed
    if previous == cached_lord:
        index_move += int(math.copysign(1, index_move)) # increase or decrease by 1
        return _restore_lo(index_move)
    return save_lo(previous.loadOrder, previous.activeOrdered,
                   __index_move=index_move, quiet=True)

# API helpers
def swap(old_dir, new_dir): _game_handle.swap(old_dir, new_dir)

def must_be_active_if_present():
    return set(_game_handle.must_be_active_if_present) | (
        set() if _game_handle.allow_deactivate_master else {
            _game_handle.master_path})

def using_txt_file(): return bush.game.using_txt_file

def using_ini_file(): return isinstance(_game_handle, _games_lo.INIGame)

def get_lo_files():
    """Returns a list of all files used by this game for storing load
    order."""
    all_lo_files = set()
    acti_file = _game_handle.get_acti_file()
    if acti_file:
        all_lo_files.add(acti_file)
    lo_file = _game_handle.get_lo_file()
    if lo_file:
        all_lo_files.add(lo_file)
    return sorted(all_lo_files)

# Timestamp games helpers
def has_load_order_conflict(mod_name):
    return _game_handle.has_load_order_conflict(mod_name)

def has_load_order_conflict_active(mod_name):
    if not cached_is_active(mod_name): return False
    return _game_handle.has_load_order_conflict_active(mod_name,
                                                       cached_lord.active)

def get_free_time(start_time, end_time=None):
    return _game_handle.get_free_time(start_time, end_time)

# Lock load order -------------------------------------------------------------
def toggle_lock_load_order(user_warning_callback):
    global locked
    lock = not locked
    if lock:
        # Make sure the user actually wants to enable this
        lock = user_warning_callback()
    bass.settings[u'bosh.modInfos.resetMTimes'] = locked = lock

class Unlock(object):

    def __enter__(self):
        global locked
        self.__locked = locked
        locked = False

    def __exit__(self, exc_type, exc_val, exc_tb):
        global locked
        locked = self.__locked
