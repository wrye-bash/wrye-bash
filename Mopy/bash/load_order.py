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

__author__ = 'Utumno'

import sys
import math
import collections
import time
# Internal
import balt
import bass
import bolt
import bush
import exception
# Game instance providing load order operations API
import games
_game_handle = None # type: games.Game
_plugins_txt_path = _loadorder_txt_path = _lord_pickle_path = None
# Load order locking
locked = False
warn_locked = False
_lords_pickle = None # type: bolt.PickleDict

max_espms = games.max_espms

def initialize_load_order_files():
    if bass.dirs['saveBase'] == bass.dirs['app']:
        #--If using the game directory as rather than the appdata dir.
        _dir = bass.dirs['app']
    else:
        _dir = bass.dirs['userApp']
    global _plugins_txt_path, _loadorder_txt_path, _lord_pickle_path
    _plugins_txt_path = _dir.join(u'plugins.txt')
    _loadorder_txt_path = _dir.join(u'loadorder.txt')
    _lord_pickle_path = bass.dirs['saveBase'].join(u'BashLoadOrders.dat')

def initialize_load_order_handle(mod_infos):
    global _game_handle
    _game_handle = games.game_factory(bush.game.fsName, mod_infos,
                                      _plugins_txt_path, _loadorder_txt_path)
    _game_handle.parse_ccc_file()

class LoadOrder(object):
    """Immutable class representing a load order."""
    __empty = ()
    __none = frozenset()

    def __init__(self, loadOrder=__empty, active=__none):
        if set(active) - set(loadOrder):
            raise exception.BoltError(
                u'Active mods with no load order: ' + u', '.join(
                    [x.s for x in (set(active) - set(loadOrder))]))
        self._loadOrder = tuple(loadOrder)
        self._active = frozenset(active)
        self.__mod_loIndex = dict((a, i) for i, a in enumerate(loadOrder))
        # below would raise key error if active have no loadOrder
        self._activeOrdered = tuple(
            sorted(active, key=self.__mod_loIndex.__getitem__))
        self.__mod_actIndex = dict(
            (a, i) for i, a in enumerate(self._activeOrdered))

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
        return {'_activeOrdered': self._activeOrdered,
                '_loadOrder': self.loadOrder}

    def __setstate__(self, dct):
        self.__dict__.update(dct)   # update attributes
        self._active = frozenset(self._activeOrdered)
        self.__mod_loIndex = dict(
            (a, i) for i, a in enumerate(self._loadOrder))
        self.__mod_actIndex = dict(
            (a, i) for i, a in enumerate(self._activeOrdered))

    def __unicode__(self):
        return u', '.join([((u'*%s' if x in self._active else u'%s') % x)
                           for x in self.loadOrder])

# Module level cache
__empty = LoadOrder()
cached_lord = __empty # must always be valid (or __empty)

# Saved load orders
lo_entry = collections.namedtuple('lo_entry', ['date', 'lord'])
_saved_load_orders = [] # type: list[lo_entry]
_current_list_index = -1

def _new_entry():
    _saved_load_orders[_current_list_index:_current_list_index] = [
        lo_entry(time.time(), cached_lord)]

def persist_orders(__keep_max=256):
    _lords_pickle.vdata['_lords_pickle_version'] = 1
    length = len(_saved_load_orders)
    if length > __keep_max:
        x, y = _keep_max(__keep_max, length)
        _lords_pickle.data['_saved_load_orders'] = \
            _saved_load_orders[_current_list_index - x:_current_list_index + y]
        _lords_pickle.data['_current_list_index'] = x
    else:
        _lords_pickle.data['_saved_load_orders'] = _saved_load_orders
        _lords_pickle.data['_current_list_index'] = _current_list_index
    _lords_pickle.save()

def _keep_max(max_to_keep, length):
    max_2 = max_to_keep / 2
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
    :rtype : tuple[bolt.Path]
    """
    return cached_lord.activeOrdered

def cached_is_active(mod):
    """Return true if the mod is in the current active mods cache."""
    return mod in cached_lord.active

# Load order and active indexes
def cached_lo_index(mod): return cached_lord.lindex(mod)

def cached_lo_index_or_max(mod):
    try:
        return cached_lo_index(mod)
    except KeyError:
        return sys.maxint # sort mods that do not have a load order LAST

def cached_active_index(mod): return cached_lord.activeIndex(mod)

def cached_lower_loading_espms(mod, mod_infos):
    return [x for x in cached_lord.loadOrder[:cached_lo_index(mod)] if
            not mod_infos[x].is_esl()]

def get_ordered(mod_names):
    """Return a list containing modNames' elements sorted into load order.

    If some elements do not have a load order they are appended to the list
    in alphabetical, case insensitive order (used also to resolve
    modification time conflicts).
    :type mod_names: collections.Iterable[bolt.Path]
    :rtype : list[bolt.Path]
    """
    mod_names = list(mod_names)
    mod_names.sort() # resolve time conflicts or no load order
    mod_names.sort(key=cached_lo_index_or_max)
    return mod_names

def filter_pinned(imods):
    return filter(_game_handle.pinned_mods.__contains__, imods)

# Get and set API -------------------------------------------------------------
def save_lo(lord, acti=None, __index_move=0, quiet=False):
    """Save the Load Order (rewrite loadorder.txt or set modification times).

    Will update plugins.txt too if using the textfile method to reorder it
    as loadorder.txt, and of course rewrite it completely for fallout 4 (
    asterisk method)."""
    acti_list = list(acti) if acti is not None else None
    load_list = list(lord) if lord is not None else None
    fix_lo = games.FixInfo() if not quiet else None
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
        fix_lo = games.FixInfo()
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
    if _lords_pickle is None: __load_pickled_load_orders() # once only
    if locked and _saved_load_orders:
        saved = _saved_load_orders[_current_list_index].lord # type: LoadOrder
        lord, acti = _game_handle.set_load_order( # make sure saved lo is valid
            list(saved.loadOrder), list(saved.activeOrdered), dry_run=True)
        fixed = LoadOrder(lord, acti)
        if fixed != saved:
            bolt.deprint(u'Saved load order is no longer valid: %s'
                         u'\nCorrected to %s' % (saved, fixed))
        saved = fixed
    else: saved = None
    if cached_lord is not __empty:
        lo = cached_lord.loadOrder if (
            cached and not _game_handle.load_order_changed()) else None
        active = cached_lord.activeOrdered if (
            cached_active and not _game_handle.active_changed()) else None
    else: active = lo = None
    _update_cache(lo, active)
    if locked and saved is not None:
        if cached_lord.loadOrder != saved.loadOrder:
            save_lo(saved.loadOrder, saved.activeOrdered)
            global warn_locked
            warn_locked = True

def __load_pickled_load_orders():
    global _lords_pickle, _saved_load_orders, _current_list_index, locked
    _lords_pickle = bolt.PickleDict(_lord_pickle_path)
    _lords_pickle.load()
    _lords_pickle.vdata['_lords_pickle_version'] = 1
    _saved_load_orders = _lords_pickle.data.get('_saved_load_orders', [])
    _current_list_index = _lords_pickle.data.get('_current_list_index', -1)
    locked = bass.settings.get('bosh.modInfos.resetMTimes', False)

def undo_load_order(): return __restore(-1)

def redo_load_order(): return __restore(1)

def __restore(index_move):
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
        return __restore(index_move)
    return save_lo(previous.loadOrder, previous.activeOrdered,
                   __index_move=index_move, quiet=True)

# API helpers
def swap(old_path, new_path): _game_handle.swap(old_path, new_path)

def must_be_active_if_present():
    return set(_game_handle.must_be_active_if_present) | (
        set() if _game_handle.allow_deactivate_master else {
            _game_handle.master_path})

def using_txt_file(): return bush.game.using_txt_file

# Timestamp games helpers
def has_load_order_conflict(mod_name):
    return _game_handle.has_load_order_conflict(mod_name)

def has_load_order_conflict_active(mod_name):
    if not cached_is_active(mod_name): return False
    return _game_handle.has_load_order_conflict_active(mod_name,
                                                       cached_lord.active)

def get_free_time(start_time, default_time='+1', end_time=None):
    return _game_handle.get_free_time(start_time, default_time, end_time)

# Lock load order -------------------------------------------------------------
def toggle_lock_load_order():
    global locked
    lock = not locked
    if lock:
        message =  _(u'Lock Load Order is a feature which resets load order '
            u'to a previously memorized state.  While this feature is good '
            u'for maintaining your load order, it will also undo any load '
            u'order changes that you have made outside Bash.')
        lock = balt.askContinue(None, message, 'bash.load_order.lock_continue',
                                title=_(u'Lock Load Order'))
    bass.settings['bosh.modInfos.resetMTimes'] = locked = lock

class Unlock(object):

    def __enter__(self):
        global locked
        self.__locked = locked
        locked = False

    def __exit__(self, exc_type, exc_val, exc_tb):
        global locked
        locked = self.__locked
