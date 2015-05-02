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
"""Load order management, features caching and undo/redo.

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
import sys

import bass
import bolt
import bush
import bosh
# Game instance providing load order operations API
import games
game_handle = None # type: games.Game
_plugins_txt_path = _loadorder_txt_path = _lord_pickle_path = None
# Load order locking
__locked = False
_lords_pickle = None # type: bolt.PickleDict

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
    global game_handle
    game_handle = games.game_factory(bush.game.fsName, mod_infos,
                                     _plugins_txt_path, _loadorder_txt_path)

class LoadOrder(object):
    """Immutable class representing a load order."""
    __empty = ()
    __none = frozenset()

    def __init__(self, loadOrder=__empty, active=__none):
        if set(active) - set(loadOrder):
            raise bolt.BoltError(
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

    def lindex(self, path): return self.__mod_loIndex[path] # KeyError
    def lorder(self, paths):
        """Return a tuple containing the given paths in their load order.
        :param paths: iterable of paths that must all have a load order
        :type paths: collections.Iterable[bolt.Path]
        :rtype: tuple
        """
        return tuple(sorted(paths, key=self.__mod_loIndex.__getitem__))
    def activeIndex(self, path): return self.__mod_actIndex[path]

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

# Module level cache
__empty = LoadOrder()
cached_lord = __empty # must always be valid (or __empty)

# Saved load orders
_saved_load_orders = [] # type: list[LoadOrder]
_current_list_index = -1

# Load Order utility methods - make sure the cache is valid when using them
def activeCached():
    """Return the currently cached active mods in load order as a tuple.
    :rtype : tuple[bolt.Path]
    """
    return cached_lord.activeOrdered

def isActiveCached(mod):
    """Return true if the mod is in the current active mods cache."""
    return mod in cached_lord.active

# Load order and active indexes
def loIndexCached(mod): return cached_lord.lindex(mod)

def loIndexCachedOrMax(mod):
    try:
        return loIndexCached(mod)
    except KeyError:
        return sys.maxint # sort mods that do not have a load order LAST

def activeIndexCached(mod): return cached_lord.activeIndex(mod)

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
    mod_names.sort(key=loIndexCachedOrMax)
    return mod_names

# Get and set API
def save_lo(lord, acti=None, __index_move=0):
    """Save the Load Order (rewrite loadorder.txt or set modification times).

    Will update plugins.txt too if using the textfile method to reorder it
    as loadorder.txt, and of course rewrite it completely for fallout 4 (
    asterisk method)."""
    acti_list = list(acti) if acti is not None else None
    load_list = list(lord) if lord is not None else None
    lord, acti = game_handle.set_load_order(load_list, acti_list,
                                            list(cached_lord.loadOrder),
                                            list(cached_lord.activeOrdered))
    _reset_mtimes_cache()
    _update_cache(lord=lord, acti_sorted=acti, __index_move=__index_move)
    return cached_lord

def _reset_mtimes_cache():
    """Reset the mtimes cache or LockLO feature will revert intentional
    changes."""
    if using_txt_file(): return
    for name in bosh.modInfos.mtimes:
        path = bosh.modInfos[name].getPath()
        if path.exists(): bosh.modInfos.mtimes[name] = path.mtime

def _update_cache(lord=None, acti_sorted=None, __index_move=0):
    """
    :type lord: tuple[bolt.Path] | list[bolt.Path]
    :type acti_sorted: tuple[bolt.Path] | list[bolt.Path]
    """
    global cached_lord
    try:
        lord, acti_sorted = game_handle.get_load_order(lord, acti_sorted)
        cached_lord = LoadOrder(lord, acti_sorted)
    except Exception:
        bolt.deprint(u'Error updating load_order cache')
        cached_lord = __empty
        raise
    finally:
        if cached_lord is not __empty:
            global _current_list_index
            if _current_list_index < 0 or (not __index_move and
                cached_lord != _saved_load_orders[_current_list_index]):
                # either getting or setting, plant the new load order in
                _current_list_index += 1
                _saved_load_orders[_current_list_index:_current_list_index] = [
                    cached_lord]
            elif __index_move: # attempted to undo/redo
                _current_list_index += __index_move
                target = _saved_load_orders[_current_list_index]
                if target != cached_lord: # we failed to redo/undo
                    bolt.deprint(u'Failed to revert load order change')
                    # keep the invalid load order - for instance due to an esm
                    # flip - but move it in the list so we can retry undo/redo
                    _saved_load_orders[_current_list_index] = cached_lord
                    _saved_load_orders[
                        _current_list_index - __index_move] = target

def get_lo(cached=False, cached_active=True):
    global _lords_pickle, _saved_load_orders, _current_list_index
    if _lords_pickle is None:
        _lords_pickle = bolt.PickleDict(_lord_pickle_path)
        _lords_pickle.load()
        _lords_pickle.vdata['_lords_pickle_version'] = 1
        _saved_load_orders = _lords_pickle.data.get('_saved_load_orders', [])
        _current_list_index = _lords_pickle.data.get('_current_list_index', -1)
        if __locked and _saved_load_orders:
            saved = _saved_load_orders[_current_list_index] # type: LoadOrder
            lord, acti = game_handle.set_load_order( # pickle may need fixing
                list(saved.loadOrder), list(saved.activeOrdered), dry_run=True)
            _update_cache(lord, acti)
    if cached_lord is not __empty:
        lo = cached_lord.loadOrder if (
            cached and not game_handle.load_order_changed()) else None
        active = cached_lord.activeOrdered if (
            cached_active and not game_handle.active_changed()) else None
        old_lord = cached_lord.loadOrder
    else: active = lo = old_lord = None
    _update_cache(lo, active)
    if __locked and old_lord is not None:
        common_mods = set(lo) & set(old_lord)
        new_order = [x for x in lo if x in common_mods]
        cached_order = [x for x in old_lord if x in common_mods]
        if new_order != cached_order: ##: warn !
            save_lo(old_lord)
    return cached_lord

def undo_load_order():
    if _current_list_index <= 0: return cached_lord
    return __restore(-1)

def redo_load_order():
    if _current_list_index == len(_saved_load_orders) - 1: return cached_lord
    return __restore(1)

def __restore(index_move):
    previous = _saved_load_orders[_current_list_index + index_move]
    return save_lo(previous.loadOrder, previous.activeOrdered,
                   __index_move=index_move)

# API helpers
def swap(old_path, new_path): game_handle.swap(old_path, new_path)

def must_be_active_if_present():
    return set(game_handle.must_be_active_if_present) | (
        set() if game_handle.allow_deactivate_master else {
            game_handle.master_path})

def using_txt_file():
    return bush.game.fsName == u'Fallout4' or bush.game.fsName == u'Skyrim'

# Timestamp games helpers
def has_load_order_conflict(mod_name):
    return game_handle.has_load_order_conflict(mod_name)

def has_load_order_conflict_active(mod_name):
    if not isActiveCached(mod_name): return False
    return game_handle.has_load_order_conflict_active(mod_name,
                                                      cached_lord.active)

def get_free_time(start_time, default_time='+1'):
    return game_handle.get_free_time(start_time, default_time=default_time)

def install_last(): return game_handle.install_last()

# Lock load order
def lock_load_order(lock=True):
    global __locked
    __locked = lock
