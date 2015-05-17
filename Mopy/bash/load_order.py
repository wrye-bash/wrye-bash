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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2014 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
import bolt
import bush
import liblo as _liblo
import bosh

class LoadOrder(object):
    """Immutable class representing a load order."""
    __empty = ()
    __none = frozenset()

    def __init__(self, loadOrder=__empty, active=__none):
        self._loadOrder = tuple(loadOrder)
        self._active = frozenset(active)
        self.__mod_loIndex = dict((a, i) for i, a in enumerate(loadOrder))
        # sugar, client could readily compute this - API: maybe drop:
        self._activeOrdered = tuple(
            sorted(active, key=lambda x: self.__mod_loIndex[x]))

    @property
    def loadOrder(self): return self._loadOrder # test if empty
    @property
    def active(self): return self._active  # test if none
    @property # sugar
    def activeOrdered(self): return self._activeOrdered

# Module level cache
__empty = LoadOrder()
_current_lo = __empty # must always be valid (or __empty)

# liblo calls - they include fixup code (which may or may not be needed/working)
def _getLoFromLiblo():
    lord = _liblo_handle.GetLoadOrder()
    if _current_lo.loadOrder != lord: __fixLoadOrder(lord) # current always valid
    return lord

def __fixLoadOrder(lord):
    """HACK: Fix inconsistencies between given loadorder and actually installed
    mod files as well as impossible load orders - save the fixed order via
    liblo.

    Only called in _getLoFromLiblo() to fix a newly fetched LO. Purely python
    so cheap - till the call to SaveLoadOrder(). The save call does fail in
    current dev version of loadorder32.dll (for instance if Oblivion.esm
    timestamp is set later than other mods, saveLoadOrder will not save the
    corrected position). Is it still needed with liblo 0.6 ? Even liblo 4 (
    current) does not apparently need all fixes.
    """
    oldLord = lord[:] ### print
    # game's master might be out of place (if using timestamps for load
    # ordering or a manually edited loadorder.txt) so move it up
    masterDex = lord.index(bosh.modInfos.masterName)
    masterName = bosh.modInfos.masterName
    if masterDex > 0:
        bolt.deprint(u'%s in %d position' % (masterName, masterDex))
        lord.remove(masterName)
        lord.insert(0, masterName)
        reordered = True
    else: reordered = False
    loadOrder = set(lord)
    modFiles = set(bosh.modInfos.keys())
    # CORRUPTED FILES HAVE A LOAD ORDER TOO
    modFiles.update(bosh.modInfos.corrupted.keys())
    removedFiles = loadOrder - modFiles
    addedFiles = modFiles - loadOrder
    # Remove non existent plugins from load order
    lord[:] = [x for x in lord if x not in removedFiles]
    # Add new plugins to load order
    indexFirstEsp = 0
    while indexFirstEsp < len(lord) and bosh.modInfos[lord[indexFirstEsp]].isEsm():
        indexFirstEsp += 1
    for mod in addedFiles:
        if bosh.modInfos.data[mod].isEsm():
            lord.insert(mod, indexFirstEsp)
            indexFirstEsp += 1
        else:
            lord.append(mod)
    # Check to see if any esm files are loaded below an esp and reorder as necessary
    for mod in lord[indexFirstEsp:]: # SEEMS NOT NEEDED, liblo does this
        if bosh.modInfos.data[mod].isEsm():
            lord.remove(mod)
            lord.insert(indexFirstEsp, mod)
            indexFirstEsp += 1
            reordered = True
    # Save changes if necessary
    if removedFiles or addedFiles or reordered:
        bolt.deprint(u'Fixed Load Order: added(%s), removed(%s), reordered(%s)' % (
            str(_pl(addedFiles) or u'None'), str(_pl(removedFiles) or u'None'),
            u'No' if not reordered else _pl(oldLord, u'from:\n') +
                                        _pl(lord, u'\nto:\n')))
        SaveLoadOrder(lord)
        return True # changes, saved
    return False # no changes, not saved

def _getActiveFromLiblo(lord): # pass load order in to check for mismatch
    acti = _liblo_handle.GetActivePlugins()
    # __fixActive
    # filter plugins not present in load order
    actiFiltered = [x for x in acti if x in lord]
    changed = acti != actiFiltered  # take note as we may need to rewrite
    # plugins txt
    if changed:
        removed = set(acti) - set(actiFiltered)
        msg = _(u'Those mods were present in plugins txt but not present in '
                u'Data/ directory') + u': ' + u', '.join(x.s for x in removed)
    else: msg = u''
    # not needed for oblivion, for skyrim liblo will write plugins.txt in order
    # STILL restore for skyrim to warn on LO change
    if usingTxtFile() and False: ## FIXME: LIBLO returns the entries unordered
        actiSorted = actiFiltered[:]
        actiSorted.sort(key=lambda y: lord.index(y)) # all present in lord
        if actiFiltered != actiSorted: # were mods in an order that disagrees with lord ?
            if msg: msg += u'\n'
            msg += u'Plugins.txt order of plugins (%s) differs from current ' \
                   u'load order (%s)' % (_pl(actiFiltered), _pl(actiSorted))
            changed = True
    else: actiSorted = actiFiltered
    if changed:
        ##: Notify user - maybe backup previous plugin txt ?
        bolt.deprint(u'Invalid Plugin txt corrected' + u'\n' + msg)
        SetActivePlugins(actiSorted)
    return actiSorted

def SaveLoadOrder(lord):
    """Save the Load Order (rewrite loadorder.txt or set modification times).

    Will update plugins.txt too if using the textfile method (in liblo 4.0 at
    least) - check lo_set_load_order - to reorder it as loadorder.txt.
    It 'checks the validity' of lord passed and will raise if invalid."""
    _liblo_handle.SetLoadOrder(lord) # also rewrite plugins.txt (text file lo method)
    _reset_mtimes_cache() # Rename this to _notify_modInfos_change_intentional()
    # YAK!!!!!!!!
    if _liblo_handle.usingTxtFile() and bosh.modInfos.plugins.pathOrder.exists():
        bosh.modInfos.plugins.mtimeOrder = bosh.modInfos.plugins.pathOrder.mtime
        bosh.modInfos.plugins.sizeOrder = bosh.modInfos.plugins.pathOrder.size

def _reset_mtimes_cache():
    """Reset the mtimes cache or LockLO feature will revert intentional
    changes."""
    if usingTxtFile(): return
    for name in bosh.modInfos.mtimes:
        path = bosh.modInfos[name].getPath()
        if path.exists(): bosh.modInfos.mtimes[name] = path.mtime

def _updateCache():
    global _current_lo
    try:
        lord = _getLoFromLiblo()
        # got a valid load order - now to active...
        actiSorted = _getActiveFromLiblo(lord)
        _current_lo = LoadOrder(lord, actiSorted)
    except _liblo.LibloError:
        _current_lo = __empty
        raise

def GetLo(cached=False):
    if not cached or _current_lo is __empty: _updateCache()
    return list(_current_lo.loadOrder)

def GetActivePlugins(cached=False):
    if not cached or _current_lo is __empty: _updateCache()
    return list(_current_lo.activeOrdered)

def SetActivePlugins(act):
    _liblo_handle.SetActivePlugins(act)
    # YAK!!!!!!!!
    bosh.modInfos.plugins.mtimePlugins = bosh.modInfos.plugins.pathPlugins.mtime
    bosh.modInfos.plugins.sizePlugins  = bosh.modInfos.plugins.pathPlugins .size

def libloLOMismatchCallback():
    """Called whenever a mismatched loadorder.txt and plugins.txt is found"""
    # Force a rewrite of both plugins.txt and loadorder.txt
    # In other words, use what's in loadorder.txt to write plugins.txt
    # TODO: Check if this actually works. # FIXME !!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # plugins is modInfos private + this is a hack + ...
    bosh.modInfos.plugins.loadLoadOrder()
    bosh.modInfos.plugins.saveLoadOrder()

#----------------------------------------------------------------------REFACTOR
_liblo.Init(bosh.dirs['compiled'].s)
# That didn't work - Wrye Bash isn't installed correctly
if not _liblo.liblo:
    raise bolt.BoltError(u'The libloadorder API could not be loaded.')
bolt.deprint(u'Using libloadorder API version:', _liblo.version)

_liblo_handle = _liblo.LibloHandle(bosh.dirs['app'].s,bush.game.fsName)
if bush.game.fsName == u'Oblivion' and bosh.dirs['mods'].join(
        u'Nehrim.esm').isfile():
    _liblo_handle.SetGameMaster(u'Nehrim.esm')
#---------------------------------------------------------------NO CALLBACKS!!!
# This warning can only occur when using libloadorder with a game that uses
# the textfile-based load order system
_liblo.RegisterCallback(_liblo.LIBLO_WARN_LO_MISMATCH, libloLOMismatchCallback)

def usingTxtFile(): return _liblo_handle.usingTxtFile()

# helper - print a list
def _pl(aList, legend=u''):
    try:
        return legend + u', '.join(x.s for x in aList)
    except AttributeError:
        return legend + u', '.join(map(repr, aList))
