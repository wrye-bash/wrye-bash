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
#  Mopy/bash/games.py Copyright (C) 2016 Utumno: Original design
#  https://github.com/wrye-bash
#
# =============================================================================

"""Game class initially introduced to encapsulate load order handling and
eventually to wrap the bush.game module to a class API to be used in the rest
of Bash."""
import re

import bolt

def _write_plugins_txt(path, lord, active, _star=False):
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
        active, modNames = [], []
        for line in ins:
            # Oblivion/Skyrim saves the plugins.txt file in cp1252 format
            # It wont accept filenames in any other encoding
            try: # use raw strings below
                modName = _re_plugins_txt_comment.sub('', line).strip()
                if not modName: continue
                is_active = not _star or modName.startswith('*')
                if _star and is_active: modName = modName[1:]
                test = bolt.decode(modName)
            except UnicodeError: continue
            if bolt.GPath(test) not in mod_infos:
                # The automatic encoding detector could have returned
                # an encoding it actually wasn't.  Luckily, we
                # have a way to double check: modInfos.data
                for encoding in bolt.encodingOrder:
                    try:
                        test2 = unicode(modName, encoding)
                        if bolt.GPath(test2) not in mod_infos:
                            continue
                        modName = bolt.GPath(test2)
                        break
                    except UnicodeError:
                        pass
                else:
                    modName = bolt.GPath(test)
            else:
                modName = bolt.GPath(test)
            modNames.append(modName)
            if is_active: active.append(modName)
    return active, modNames

class Game(object):

    _allow_deactivate_master = False
    _must_be_active_if_present = ()

    def __init__(self, mod_infos, plugins_txt_path):
        super(Game, self).__init__()
        self.plugins_txt_path = plugins_txt_path # type: bolt.Path
        self.mod_infos = mod_infos # type: bosh.ModInfos
        self.master_path = mod_infos.masterName # type: bolt.Path

    # API ---------------------------------------------------------------------
    def get_load_order(self, fetch_active):
        lo, active = self._fetch_load_order(fetch_active)
        # for timestamps we use modInfos so we should not get an invalid
        # load order. For text based games however the fetched order could
        # be in whatever state, so get this fixed
        _removedFiles, _addedFiles, _reordered = self._fix_load_order(lo)
        # now we have a valid load order we may fix active too if fetched
        fixed_active = fetch_active and self._fix_active_plugins(active, lo)
        self._save_fixed_load_order(_removedFiles, _addedFiles, _reordered,
                                    fixed_active, lo, active)
        return lo, active

    def set_load_order(self, lord, active, _fixed=False):
        raise NotImplementedError

    # ABSTRACT ----------------------------------------------------------------
    def _fetch_load_order(self, fetch_active):
        raise bolt.AbstractError

    def _persist_load_order(self, lord, active):
        raise bolt.AbstractError

    def _persist_active_plugins(self, active, lord):
        raise bolt.AbstractError

    def _save_fixed_load_order(self, _removedFiles, _addedFiles, _reordered,
                               fixed_active, lo, active):
        raise bolt.AbstractError

    # PLUGINS TXT -------------------------------------------------------------
    def _parse_plugins_txt(self, path):
        if not path.exists(): return [], []
        # #--Read file
        acti, _lo = _parse_plugins_txt_(path, self.mod_infos, _star=False)
        return acti, _lo

    def _fetch_active_plugins(self):
        acti, _lo = self._parse_plugins_txt(self.plugins_txt_path)
        return acti

    # VALIDATION --------------------------------------------------------------
    def _fix_load_order(self, lord):
        """Fix inconsistencies between given loadorder and actually installed
        mod files as well as impossible load orders - save the fixed order. We
        need a refreshed bosh.modInfos reflecting the contents of Data/.

        Called in get_load_order() to fix a newly fetched LO and in
        set_load_order() to check if a load order passed in is valid. Needs
        rethinking as save load and active should be an atomic operation -
        leads to hacks (like the _selected parameter).
        :type lord: list[bolt.Path]
        """
        oldLord = lord[:]
        # game's master might be out of place (if using timestamps for load
        # ordering or a manually edited loadorder.txt) so move it up
        masterName = self.mod_infos.masterName
        try:
            masterDex = lord.index(masterName)
        except ValueError:
            raise bolt.BoltError(u'%s is missing or corrupted' % masterName)
        if masterDex > 0:
            bolt.deprint(u'%s has index %d (must be 0)' % (masterName, masterDex))
            lord.remove(masterName)
            lord.insert(0, masterName)
            _reordered = True
        else: _reordered = False
        loadorder_set = set(lord)
        mods_set = set(self.mod_infos.keys())
        _removedFiles = loadorder_set - mods_set # may remove corrupted mods
        # present in text file, we are supposed to take care of that
        _addedFiles = mods_set - loadorder_set
        # Remove non existent plugins from load order
        lord[:] = [x for x in lord if x not in _removedFiles]
        indexFirstEsp = self._indexFirstEsp(lord)
        # See if any esm files are loaded below an esp and reorder as necessary
        for mod in lord[indexFirstEsp:]:
            if mod in self.mod_infos and self.mod_infos[mod].isEsm():
                lord.remove(mod)
                lord.insert(indexFirstEsp, mod)
                indexFirstEsp += 1
                _reordered = True
        # Append new plugins to load order
        for mod in _addedFiles:
            if self.mod_infos[mod].isEsm():
                lord.insert(indexFirstEsp, mod)
                indexFirstEsp += 1
            else: lord.append(mod)
        if _removedFiles or _addedFiles or _reordered:
            bolt.deprint(
                u'Fixed Load Order: added(%s), removed(%s), reordered(%s)' % (
                _pl(_addedFiles) or u'None', _pl(_removedFiles) or u'None',
                u'No' if not _reordered else _pl(oldLord,
                u'from:\n', joint=u'\n') + _pl(lord, u'\nto:\n', joint=u'\n')))
        return _removedFiles, _addedFiles, _reordered

    def _fix_active_plugins(self, acti, lord):
        # filter plugins not present in modInfos - this will disable corrupted too!
        actiFiltered = [x for x in acti if x in self.mod_infos] #preserve acti order
        _removed = set(acti) - set(actiFiltered)
        if _removed: # take note as we may need to rewrite plugins txt
            msg = u'Active list contains mods not present ' \
                  u'in Data/ directory or corrupted: ' + _pl(_removed) + u'\n'
            self.mod_infos.selectedBad = _removed
        else: msg = u''
        if not self._allow_deactivate_master:
            if not self.master_path in actiFiltered:
                actiFiltered.insert(0, self.master_path)
                msg += (u'%s not present in active mods' % self.master_path) + u'\n'
        added_active_paths = []
        for path in self._must_be_active_if_present:
            if path in lord and not path in actiFiltered:
                msg += (u'%s not present in active list '
                        u'while present in Data folder' % path) + u'\n'
                added_active_paths.append(path)
        msg += self._check_active_order(actiFiltered, lord)
        for path in added_active_paths: # insert after the last master (as does liblo)
            actiFiltered.insert(self._indexFirstEsp(actiFiltered), path)
        # check if we have more than 256 active mods
        if len(actiFiltered) > 255:
            msg += u'Active list contains more than 255 plugins' \
                   u' - the following plugins will be deactivated: '
            self.mod_infos.selectedExtra = actiFiltered[255:]
            msg += _pl(self.mod_infos.selectedExtra)
        # Check for duplicates
        mods, duplicates, j = set(), set(), 0
        for i, mod in enumerate(actiFiltered[:]):
            if mod in mods:
                del actiFiltered[i - j]
                j += 1
                duplicates.add(mod)
            else:
                mods.add(mod)
        if duplicates:
            msg += u'Removed duplicate entries from active list : '
            msg += _pl(duplicates)
        acti[:] = actiFiltered[:255] # chop off extra, and update acti in place
        if msg:
            # Notify user - ##: maybe backup previous plugin txt ?
            bolt.deprint(u'Invalid Plugin txt corrected' + u'\n' + msg)
            self._persist_active_plugins(acti, lord)
            return True # changes, saved
        return False # no changes, not saved

    @staticmethod
    def _check_active_order(acti, lord):
        dexDict = {mod: index for index, mod in enumerate(lord)}
        acti.sort(key=dexDict.__getitem__)
        return u''

    # HELPERS -----------------------------------------------------------------
    def _indexFirstEsp(self, lord):
        indexFirstEsp = 0
        while indexFirstEsp < len(lord) and self.mod_infos[
            lord[indexFirstEsp]].isEsm():
            indexFirstEsp += 1
        return indexFirstEsp

class TimestampGame(Game):

    _allow_deactivate_master = True

    def _fetch_load_order(self, fetch_active):
        active = (fetch_active and self._fetch_active_plugins()) or None
        return self.mod_infos.calculateLO(), active

    def _persist_load_order(self, lord, active):
        assert set(self.mod_infos.keys()) == set(lord)
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

    def _persist_active_plugins(self, active, lord):
        _write_plugins_txt(self.plugins_txt_path, active, active, _star=False)

    def _save_fixed_load_order(self, _removedFiles, _addedFiles, _reordered, fixed_active, lo, active):
        if _removedFiles or _addedFiles or _reordered:
            if _removedFiles: # we don't rewrite plugins.txt if _reordered -
                # so active plugins order is undefined
                if not fixed_active:
                    active = self._fetch_active_plugins()
                    self._fix_active_plugins(active, lo)
            self._persist_load_order(lo, None) # active is not used here

    def _fix_load_order(self, lord):
        _removedFiles, _addedFiles, _reordered = super(TimestampGame,
            self)._fix_load_order(lord)
        if _addedFiles: # should not occur
            bolt.deprint(u'Incomplete load order passed in to set_load_order')
            lord[:] = self.mod_infos.calculateLO(mods=lord)
        return _removedFiles, _addedFiles, _reordered

class TextfileGame(Game):

    _must_be_active_if_present = (bolt.GPath(u'Update.esm'),)

    def __init__(self, mod_infos, plugins_txt_path, loadorder_txt_path):
        super(TextfileGame, self).__init__(mod_infos, plugins_txt_path)
        self.loadorder_txt_path = loadorder_txt_path

    # Abstract overrides ------------------------------------------------------
    def _fetch_load_order(self, fetch_active):
        """Read data from loadorder.txt file. If loadorder.txt does not exist
        create it and try reading plugins.txt so the load order of the user is
        preserved. Additional mods should be added by caller who should anyway
        call _fix_load_order.
        NOTE: modInfos must exist and be up to date."""
        if not self.loadorder_txt_path.exists():
            if self.plugins_txt_path.exists():
                active, _mods = _parse_plugins_txt_(self.plugins_txt_path, self.mod_infos, _star=False)
            else: active = []
            _write_plugins_txt(self.loadorder_txt_path, active, active, _star=False)
            bolt.deprint(u'Created %s' % self.loadorder_txt_path)
            return active, active
        # if not force and _current_lo is not __empty and not _loadorder_txt_changed():
        #     return list(_current_lo.loadOrder)
        # ##: TODO(ut): handle desync with plugins txt
        #--Read file
        if fetch_active:
            active, _lo = _parse_plugins_txt_(self.plugins_txt_path,
                                              self.mod_infos, _star=False)
        else: active = None
        _acti, lo = _parse_plugins_txt_(self.loadorder_txt_path, self.mod_infos,
                                        _star=False)
        return lo, active

    def _persist_load_order(self, lord, active):
        _write_plugins_txt(self.loadorder_txt_path, lord, lord, _star=False)

    def _persist_active_plugins(self, active, lord):
        _write_plugins_txt(self.plugins_txt_path, active[1:], active[1:],
                           _star=False) # we need to chop off Skyrim.esm

    def _save_fixed_load_order(self, _removedFiles, _addedFiles, _reordered,
                               fixed_active, lo, active):
        if _removedFiles or _addedFiles or _reordered:
            if _removedFiles or _reordered: # must fix the active too
                if not fixed_active:
                    active = self._fetch_active_plugins()
                    self._fix_active_plugins(active, lo)
            self._persist_load_order(lo, None) # active is not used here

    @staticmethod
    def _check_active_order(acti, lord):
        dexDict = {mod: index for index, mod in enumerate(lord)}
        old = acti[:]
        acti.sort(key=dexDict.__getitem__) # all present in lord
        if acti != old: # active mods order that disagrees with lord ?
            return (u'Active list order of plugins (%s) differs from supplied '
                    u'load order (%s)') % (_pl(old), _pl(acti))
        return u''

class AsteriskGame(Game):

    def _fetch_load_order(self, fetch_active=True):
        """Read data from plugins.txt file. If plugins.txt does not exist
        create it - all mods should be added by caller who should anyway
        call _fix_load_order.
        NOTE: modInfos must exist and be up to date."""
        if not self.plugins_txt_path.exists():
            _write_plugins_txt(self.plugins_txt_path, [], [], _star=True)
            bolt.deprint(u'Created %s' % self.plugins_txt_path)
            return [], []
        # if not force and _current_lo is not __empty and not _loadorder_txt_changed():
        #     return list(_current_lo.loadOrder)
        active, lo = _parse_plugins_txt_(self.plugins_txt_path, self.mod_infos,
                                         _star=True)
        return lo, active

    def _persist_load_order(self, lord, active):
        assert active # must at least contain Fallout4.esm
        _write_plugins_txt(self.plugins_txt_path, lord, active, _star=True)

    def _persist_active_plugins(self, active, lord):
        self._persist_load_order(lord, active)

    def _save_fixed_load_order(self, _removedFiles, _addedFiles, _reordered,
                               fixed_active, lo, active):
        if fixed_active: return # plugins.txt already saved
        if _removedFiles or _addedFiles or _reordered:
            self._persist_load_order(lo, active)

    def _parse_plugins_txt(self, path):
        if not path: return [], []
        acti, lo = _parse_plugins_txt_(path, self.mod_infos, _star=True)
        return acti, lo

def game_factory(name, mod_infos, plugins_txt_path, loadorder_txt_path=None):
    if name == u'Skyrim':
        return TextfileGame(mod_infos, plugins_txt_path, loadorder_txt_path)
    elif name == u'Fallout4':
        return AsteriskGame(mod_infos, plugins_txt_path)
    else:
        return TimestampGame(mod_infos, plugins_txt_path)

# helper - print a list
def _pl(aList, legend=u'', joint=u', '):
    return legend + joint.join(u'%s' % x for x in aList) # use Path.__unicode__
