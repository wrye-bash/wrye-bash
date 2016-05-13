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
#
# =============================================================================
"""Load order management, features caching.

Notes:
- _current_lo is meant to eventually become a cache exported to the rest of
Bash. Must be valid at all times. Should be updated on tabbing out and back
in to Bash and on setting lo/active from inside Bash.
- active mods must always be manipulated having a valid load order at hand:
 - all active mods must be present and have a load order and
 - especially for skyrim the relative order of entries in plugin.txt must be
 the same as their relative load order in loadorder.txt
- corrupted files do not have a load order

Double underscores and dirty comments are no accident - BETA, I need a Game
classes hierarchy to handle differences between the games.
"""
import sys

import bass
import bolt
import bush
import bosh
# Game instance providing load order operations API
import games
game_handle = None # type: games.Game
_plugins_txt_path = _loadorder_txt_path = None

def initialize_load_order_files():
    if bass.dirs['saveBase'] == bass.dirs['app']:
    #--If using the game directory as rather than the appdata dir.
        _dir = bass.dirs['app']
    else:
        _dir = bass.dirs['userApp']
    global _plugins_txt_path, _loadorder_txt_path
    _plugins_txt_path = _dir.join(u'plugins.txt')
    _loadorder_txt_path = _dir.join(u'loadorder.txt')

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
    def __ne__(self, other): return not self == other
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

# Module level cache
__empty = LoadOrder()
cached_lord = __empty # must always be valid (or __empty)

# Load Order utility methods - be sure cache is valid when using them
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

def SaveLoadOrder(lord, acti=None):
    """Save the Load Order (rewrite loadorder.txt or set modification times).

    Will update plugins.txt too if using the textfile method to reorder it
    as loadorder.txt, and of course rewrite it completely for fallout 4 (
    asterisk method)."""
    actiList = list(acti) if acti is not None else None
    lordList = list(lord) if lord is not None else None
    lord, acti = game_handle.set_load_order(lordList, actiList,
                                            list(cached_lord.loadOrder),
                                            list(cached_lord.activeOrdered))
    _reset_mtimes_cache()
    _updateCache(lord=lord, actiSorted=acti)
    return cached_lord

def _reset_mtimes_cache():
    """Reset the mtimes cache or LockLO feature will revert intentional
    changes."""
    if usingTxtFile(): return
    for name in bosh.modInfos.mtimes:
        path = bosh.modInfos[name].getPath()
        if path.exists(): bosh.modInfos.mtimes[name] = path.mtime

def _updateCache(lord=None, actiSorted=None):
    """
    :type lord: tuple[bolt.Path] | list[bolt.Path]
    :type actiSorted: tuple[bolt.Path] | list[bolt.Path]
    """
    global cached_lord
    try:
        lord, actiSorted = game_handle.get_load_order(lord, actiSorted)
        cached_lord = LoadOrder(lord, actiSorted)
    except Exception:
        bolt.deprint(u'Error updating load_order cache')
        cached_lord = __empty
        raise

def GetLo(cached=False, cached_active=True):
    if cached_lord is not __empty:
        loadOrder = cached_lord.loadOrder if (
            cached and not game_handle.load_order_changed()) else None
        active = cached_lord.activeOrdered if (
            cached_active and not game_handle.active_changed()) else None
    else: active = loadOrder = None
    _updateCache(loadOrder, active)
    return cached_lord

def usingTxtFile():
    return bush.game.fsName == u'Fallout4' or bush.game.fsName == u'Skyrim'

def swap(oldPath, newPath): game_handle.swap(oldPath, newPath)
