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
"""Wrapper around liblo.py

Notes:
- _current_lo is meant to eventually become a cache exported to the rest of
Bash. Must be valid at all times. Should be updated on tabbing out and back
in to Bash and on setting lo/active from inside Bash.
- active mods must always be manipulated having a valid load order at hand:
 - all active mods must be present and have a load order and
 - especially for skyrim the relative order of entries in plugin.txt must be
 the same as their relative load order in loadorder.txt

Currently investigating what the liblo calls return to me and monkey
patching that (see __fix methods).
Double underscores and dirty comments are no accident - ALPHA
"""
import bolt
import bush
import liblo as _liblo
import bosh

class LoadOrder(object):
    """Immutable class representing a load order."""
    __empty = ()
    __none = frozenset()

    def __init__(self, loadOrder=__empty, active=__none):
        if set(active) - set(loadOrder):
            raise bolt.BoltError('Setting active with no load order')
        self._loadOrder = tuple(loadOrder)
        self._active = frozenset(active)
        self.__mod_loIndex = dict((a, i) for i, a in enumerate(loadOrder))
        # would raise key error if active have no loadOrder
        self._activeOrdered = tuple(
            sorted(active, key=self.__mod_loIndex.__getitem__))

    @property
    def loadOrder(self): return self._loadOrder # test if empty
    @property
    def active(self): return self._active  # test if none
    @property # sugar - API: maybe drop:
    def activeOrdered(self): return self._activeOrdered

    def lindex(self, path): return self.__mod_loIndex[path] # KeyError
    def lorder(self, paths): # API: sort in place ? see usages
        return tuple(sorted(paths, key=self.__mod_loIndex.__getitem__))

# Module level cache
__empty = LoadOrder()
_current_lo = __empty # must always be valid (or __empty)

# liblo calls - they include fixup code (which may or may not be needed/working)
def _getLoFromLiblo():
    lord = _liblo_handle.GetLoadOrder()
    __fixLoadOrder(lord)
    return lord

def _indexFirstEsp(lord):
    indexFirstEsp = 0
    while indexFirstEsp < len(lord) and bosh.modInfos[
        lord[indexFirstEsp]].isEsm():
        indexFirstEsp += 1
    return indexFirstEsp

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
        _reordered = True
    else: _reordered = False
    loadOrder = set(lord)
    modFiles = set(bosh.modInfos.keys())
    # CORRUPTED FILES HAVE A LOAD ORDER TOO
    modFiles.update(bosh.modInfos.corrupted.keys())
    _removedFiles = loadOrder - modFiles
    _addedFiles = modFiles - loadOrder
    # Remove non existent plugins from load order
    lord[:] = [x for x in lord if x not in _removedFiles]
    # Add new plugins to load order
    indexFirstEsp = _indexFirstEsp(lord)
    for mod in _addedFiles:
        if bosh.modInfos[mod].isEsm():
            lord.insert(indexFirstEsp, mod)
            indexFirstEsp += 1
        else:
            lord.append(mod)
    # Check to see if any esm files are loaded below an esp and reorder as necessary
    for mod in lord[indexFirstEsp:]: # SEEMS NOT NEEDED, liblo does this
        if bosh.modInfos[mod].isEsm():
            lord.remove(mod)
            lord.insert(indexFirstEsp, mod)
            indexFirstEsp += 1
            _reordered = True
    # Save changes if necessary
    if _removedFiles or _addedFiles or _reordered:
        if _removedFiles or _reordered: # must fix the active too
            __fixActive(_current_lo.activeOrdered, lord)
        bolt.deprint(u'Fixed Load Order: added(%s), removed(%s), reordered(%s)'
             % (_pl(_addedFiles) or u'None', _pl(_removedFiles) or u'None',
             u'No' if not _reordered else _pl(oldLord, u'from:\n') +
                                          _pl(lord, u'\nto:\n')))
        SaveLoadOrder(lord, _fixed=True)
        return True # changes, saved
    return False # no changes, not saved

def _getActiveFromLiblo(lord): # pass a VALID load order in
    acti = _liblo_handle.GetActivePlugins()
    acti = __fixActive(acti, lord)
    return acti

def __fixActive(acti, lord):
    # filter plugins not present in load order
    actiFiltered = [x for x in acti if x in lord] # preserve acti order
    _removed = set(acti) - set(actiFiltered)
    if _removed: # take note as we may need to rewrite plugins txt
        msg = u'Those mods were present in plugins.txt but were not present ' \
              u'in Data/ directory or were corrupted: ' + _pl(_removed) + u'\n'
    else: msg = u''
    # again is below needed ? Apparently not with liblo 4 (acti is [Skyrim.esm,
    # Update.esm] on empty plugins.txt) - Keep it cause eventually (when liblo
    # is made to return actual contents of plugins.txt at all times) I may
    # need to correct this here
    addUpdateEsm = False
    if bush.game.fsName == 'Skyrim':
        skyrim = bolt.GPath(u'Skyrim.esm')
        if not skyrim in actiFiltered:
            actiFiltered.insert(0, skyrim)
            msg += u'Skyrim.esm not present in active mods' + u'\n'
        updateEsm = bolt.GPath(u'Update.esm')
        if updateEsm in lord and not updateEsm in actiFiltered:
            msg += (u'Update.esm not present in plugins.txt while present in '
                    u'Data folder') + u'\n'
            addUpdateEsm = True
    dexDict = {mod:index for index, mod in enumerate(lord)}
    # not needed for oblivion, for skyrim liblo will write plugins.txt in order
    # STILL restore for skyrim to warn on LO change
    if usingTxtFile() and False: ## FIXME: LIBLO returns the entries unordered
        actiSorted = actiFiltered[:]
        actiSorted.sort(key=dexDict.__getitem__) # all present in lord
        if actiFiltered != actiSorted: # were mods in an order that disagrees with lord ?
            msg += (u'Plugins.txt order of plugins (%s) differs from current '
                   u'load order (%s)') % (_pl(actiFiltered), _pl(actiSorted))
    else: actiSorted = sorted(actiFiltered, key=dexDict.__getitem__)
    if addUpdateEsm: # insert after the last master (as does liblo)
        actiSorted.insert(_indexFirstEsp(actiSorted), updateEsm)
    if msg:
        ##: Notify user - maybe backup previous plugin txt ?
        bolt.deprint(u'Invalid Plugin txt corrected' + u'\n' + msg)
        SetActivePlugins(actiSorted, lord, _fixed=True)
    return actiSorted

def SaveLoadOrder(lord, _fixed=False):
    """Save the Load Order (rewrite loadorder.txt or set modification times).

    Will update plugins.txt too if using the textfile method (in liblo 4.0 at
    least) - check lo_set_load_order - to reorder it as loadorder.txt.
    It 'checks the validity' of lord passed and will raise if invalid."""
    if not _fixed: __fixLoadOrder(lord)
    _liblo_handle.SetLoadOrder(lord) # also rewrite plugins.txt (text file lo method)
    _reset_mtimes_cache() # Rename this to _notify_modInfos_change_intentional()
    _setLoTxtModTime()
    _updateCache(lord=lord, actiSorted=_current_lo.active)
    return _current_lo

def _reset_mtimes_cache():
    """Reset the mtimes cache or LockLO feature will revert intentional
    changes."""
    if usingTxtFile(): return
    for name in bosh.modInfos.mtimes:
        path = bosh.modInfos[name].getPath()
        if path.exists(): bosh.modInfos.mtimes[name] = path.mtime

def _updateCache(lord=None, actiSorted=None):
    global _current_lo
    try:
        if lord is None:
            lord = _getLoFromLiblo()
            _setLoTxtModTime()
        # got a valid load order - now to active...
        if actiSorted is None:
            actiSorted = _getActiveFromLiblo(lord)
            _setPluginsTxtModTime()
        _current_lo = LoadOrder(lord, actiSorted)
    except Exception:
        bolt.deprint('Error updating load_order cache from liblo')
        _current_lo = __empty
        raise

def GetLo(cached=False):
    if not cached or _current_lo is __empty: _updateCache()
    return _current_lo

def SetActivePlugins(act, lord, _fixed=False): # we need a valid load order to set active
    if not _fixed: act = __fixActive(act, lord)
    _liblo_handle.SetActivePlugins(act)
    _setPluginsTxtModTime()
    _updateCache(lord=lord, actiSorted=act)
    return _current_lo

def usingTxtFile(): return _liblo_handle.usingTxtFile()

def haveLoFilesChanged():
    """True if plugins.txt or loadorder.txt file has changed."""
    if _plugins_txt_path.exists() and (mtimePlugins != _plugins_txt_path.mtime
                                    or sizePlugins  != _plugins_txt_path.size):
        return True
    if not usingTxtFile():
        return True  # Until we find a better way, Oblivion always needs True #FIXME !!!!!!!!!!
    return _loadorder_txt_path.exists() and (
            mtimeOrder != _loadorder_txt_path.mtime or
            sizeOrder  != _loadorder_txt_path.size)

#----------------------------------------------------------------------REFACTOR
_liblo_handle, _liblo_error = _liblo.Init(bosh.dirs['compiled'].s)
# That didn't work - Wrye Bash isn't installed correctly
if not _liblo.liblo:
    raise bolt.BoltError(u'The libloadorder API could not be loaded.')
bolt.deprint(u'Using libloadorder API version:', _liblo.version)

_liblo_handle = _liblo_handle(bosh.dirs['app'].s,bush.game.fsName)
if bush.game.fsName == u'Oblivion' and bosh.dirs['mods'].join(
        u'Nehrim.esm').isfile():
    _liblo_handle.SetGameMaster(u'Nehrim.esm')

if bosh.dirs['saveBase'] == bosh.dirs['app']:
#--If using the game directory as rather than the appdata dir.
    _dir = bosh.dirs['app']
else:
    _dir = bosh.dirs['userApp']
_plugins_txt_path = _dir.join(u'plugins.txt')
_loadorder_txt_path = _dir.join(u'loadorder.txt')
mtimePlugins = 0
sizePlugins = 0
mtimeOrder = 0
sizeOrder = 0

def _setLoTxtModTime():
    if usingTxtFile() and _loadorder_txt_path.exists():
        global mtimeOrder, sizeOrder
        mtimeOrder, sizeOrder = _loadorder_txt_path.mtime, \
                                _loadorder_txt_path.size

def _setPluginsTxtModTime():
    global mtimePlugins, sizePlugins
    if  _plugins_txt_path.exists():
        mtimePlugins, sizePlugins = _plugins_txt_path.mtime, \
                                    _plugins_txt_path.size
    else: mtimePlugins, sizePlugins = 0, 0

# helper - print a list
def _pl(aList, legend=u''):
    try:
        return legend + u', '.join(x.s for x in aList)
    except AttributeError:
        return legend + u', '.join(map(repr, aList))
