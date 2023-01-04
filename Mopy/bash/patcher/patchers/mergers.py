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
#
# =============================================================================
"""This module houses mergers. A merger is an import patcher that targets a
list of entries, adding, removing (and, for more complex entries, changing)
entries from multiple tagged plugins to create a final merged list. The goal is
to eventually absorb all of them under the _AMerger base class."""

import copy
from collections import defaultdict, Counter
from itertools import chain
# Internal
from ..base import ImportPatcher, ListPatcher
from ... import bush, load_order
from ...bolt import FName
from ...exception import AbstractError, BoltError, ModSigMismatchError

#------------------------------------------------------------------------------
##: currently relies on the merged subrecord being sorted - fix that
##: add ForceAdd support
##: once the two tasks above are done, absorb all other mergers
##: a lot of code still shared with _APreserver - move to ImportPatcher
##: add CSV support - we broke Import Relations when we made it an _AMerger -
##: see gui_patchers.ImportRelations
# instance (the GUI will still list them too)
class _AMerger(ImportPatcher):
    """Still very WIP base class for mergers."""
    # Bash tags for each function of the merger. None means that it does not
    # support that function. E.g. the change tag is only applicable if the
    # entries in question are more complex than mere FormIDs.
    _add_tag = None
    _change_tag = None
    _remove_tag = None
    # Dict mapping each record type to the subrecord we want to merge for it
    _wanted_subrecord = {}
    # We want inactives since we process our sources in scanModFiles
    _scan_inactive = True

    def __init__(self, p_name, p_file, p_sources):
        super(_AMerger, self).__init__(p_name, p_file, p_sources)
        self.id_deltas = defaultdict(list)
        merger_masters = set(chain.from_iterable(
            p_file.p_file_minfos.recurse_masters(srcMod)
            for srcMod in self.srcs))
        self._masters_and_srcs = merger_masters | set(self.srcs)
        # Set of record signatures that are actually provided by sources
        self._present_sigs = set()
        self.mod_id_entries = {}
        self.touched = set()
        self.inventOnlyMods = {x for x in self.srcs if
                               x in p_file.ii_mode} if self.iiMode else set()

    ##: post-tweak pooling, see if we can use RecPath for this
    def _entry_key(self, subrecord_entry):
        """Returns a key to sort and compare by for the specified subrecord
        entry. Default implementation returns the entry itself (useful if the
        subrecord is e.g. just a list of FormIDs)."""
        return subrecord_entry

    @property
    def _read_sigs(self):
        return self._present_sigs

    def initData(self,progress):
        if not self.isActive or not self.srcs: return
        # set loadFactory attribute to be used by _mod_file_read
        self.loadFactory = self._patcher_read_fact(by_sig=self._wanted_subrecord)
        progress.setFull(len(self.srcs))
        minfs = self.patchFile.all_plugins
        for index,srcMod in enumerate(self.srcs):
            srcFile = self._mod_file_read(minfs[srcMod])
            for s, block in srcFile.iter_tops(self._wanted_subrecord):
                self._present_sigs.add(s)
                for rid, _record in block.iter_present_records():
                    if rid.mod_fn not in minfs: continue # or break filter mods
                    self.touched.add(rid)
            progress.plus()
        self.isActive = bool(self._present_sigs)

    def scanModFile(self, modFile, progress):
        touched = self.touched
        id_deltas = self.id_deltas
        mod_id_entries = self.mod_id_entries
        modName = modFile.fileInfo.fn_key
        #--Master or source?
        if modName in self._masters_and_srcs:
            id_entries = mod_id_entries[modName] = {}
            for curr_sig, block in modFile.iter_tops(self._present_sigs):
                sr_attr = self._wanted_subrecord[curr_sig]
                for rid, record in block.iter_present_records():
                    if rid in touched:
                        try:
                            id_entries[rid] = getattr(record, sr_attr)[:]
                        except AttributeError:
                            raise ModSigMismatchError(modName, record)
        #--Source mod?
        if modName in self.srcs:
            # The applied tags limit what data we're going to collect
            applied_tags = modFile.fileInfo.getBashTags()
            can_add = self._add_tag in applied_tags
            can_change = self._change_tag in applied_tags
            can_remove = self._remove_tag in applied_tags
            id_entries = {}
            en_key = self._entry_key
            for master in modFile.tes4.masters:
                if master in mod_id_entries:
                    id_entries.update(mod_id_entries[master])
            for fid,entries in mod_id_entries[modName].items():
                masterEntries = id_entries.get(fid)
                if masterEntries is None: continue
                master_keys = {en_key(x) for x in masterEntries}
                mod_keys = {en_key(x) for x in entries}
                remove_keys = master_keys - mod_keys if can_remove else set()
                # Note that we need to calculate these whether or not we're
                # Add-tagged, because Change needs them as well.
                addItems = mod_keys - master_keys
                addEntries = [x for x in entries if en_key(x) in addItems]
                # Changed entries are those entries that haven't been newly
                # added but also differ from the master entries
                if can_change:
                    changed_entries = [x for x in entries
                                       if x not in masterEntries
                                       and x not in addEntries]
                else:
                    changed_entries = []
                final_add_entries = addEntries if can_add else []
                if remove_keys or final_add_entries or changed_entries:
                    id_deltas[fid].append((remove_keys, final_add_entries,
                                           changed_entries))
        # Copy the new records we want to keep, unless we're an IIM merger and
        # the mod is IIM-tagged
        if modFile.fileInfo.fn_key not in self.inventOnlyMods:
            for curr_sig, block in modFile.iter_tops(self._present_sigs):
                patchBlock = self.patchFile.tops[curr_sig]
                id_records = patchBlock.id_records
                for rid, record in block.iter_present_records():
                    # Copy the defining version of each record into the BP -
                    # updating it is handled by
                    # mergeModFile/update_patch_records_from_mod
                    if rid in touched and rid not in id_records:
                        patchBlock.setRecord(record)

    def buildPatch(self,log,progress):
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        id_deltas = self.id_deltas
        mod_count = Counter()
        en_key = self._entry_key
        for curr_sig in self._present_sigs:
            sr_attr = self._wanted_subrecord[curr_sig]
            for rid, record in self.patchFile.tops[curr_sig].id_records.items():
                deltas = id_deltas[rid]
                if not deltas: continue
                # Use sorted to preserve duplicates, but ignore order. This is
                # safe because order does not matter for items.
                old_items = sorted(getattr(record, sr_attr), key=en_key)
                for remove_keys, add_entries, change_entries in deltas:
                    # First execute removals, don't want to change something
                    # we're going to remove
                    if remove_keys:
                        setattr(record, sr_attr,
                            [x for x in getattr(record, sr_attr)
                             if en_key(x) not in remove_keys])
                    # Then execute changes, don't want to modify our own
                    # additions
                    if change_entries:
                        # In order to not modify the list while iterating
                        final_remove = []
                        final_add = []
                        record_entries = getattr(record, sr_attr)
                        for change_entry in change_entries:
                            # Look for one with the same item - can't just use
                            # a dict or change the items directly because we
                            # have to respect duplicates
                            for curr_entry in record_entries:
                                if en_key(change_entry) == en_key(curr_entry):
                                    # Remove the old entry, add the changed one
                                    final_remove.append(curr_entry)
                                    final_add.append(change_entry)
                                    break
                        # No need to check both, see add/append above
                        if final_remove:
                            setattr(record, sr_attr,
                                [x for x in record_entries
                                 if x not in final_remove] + final_add)
                    # Finally, execute additions - fairly straightforward
                    if add_entries:
                        record_entries = getattr(record, sr_attr)
                        current_entries = {en_key(x) for x in record_entries}
                        for entry in add_entries:
                            if en_key(entry) not in current_entries:
                                record_entries.append(entry)
                if old_items != sorted(getattr(record, sr_attr), key=en_key):
                    keep(rid, record)
                    mod_count[rid.mod_fn] += 1
        self.id_deltas.clear()
        self._patchLog(log,mod_count)

    def _plog(self, log, mod_count): self._plog1(log, mod_count)

#------------------------------------------------------------------------------
# Absorbed patchers -----------------------------------------------------------
#------------------------------------------------------------------------------
class ImportActorsPerksPatcher(_AMerger):
    logMsg = u'\n=== ' + _(u'Perk Lists Changed') + u': %d'
    _add_tag = u'Actors.Perks.Add'
    _change_tag = u'Actors.Perks.Change'
    _remove_tag = u'Actors.Perks.Remove'
    _wanted_subrecord = {x: u'perks' for x in bush.game.actor_types}

    def _entry_key(self, subrecord_entry):
        return subrecord_entry.perk

#------------------------------------------------------------------------------
class ImportInventoryPatcher(_AMerger):
    logMsg = u'\n=== ' + _(u'Inventories Changed') + u': %d'
    _add_tag = u'Invent.Add'
    _change_tag = u'Invent.Change'
    _remove_tag = u'Invent.Remove'
    _wanted_subrecord = {x: u'items' for x in bush.game.inventoryTypes}
    iiMode = True

    def _entry_key(self, subrecord_entry):
        return subrecord_entry.item

#------------------------------------------------------------------------------
class ImportOutfitsPatcher(_AMerger):
    logMsg = u'\n=== ' + _(u'Outfits Changed') + u': %d'
    _add_tag = u'Outfits.Add'
    _remove_tag = u'Outfits.Remove'
    _wanted_subrecord = {b'OTFT': u'items'}

#------------------------------------------------------------------------------
class ImportRacesRelationsPatcher(_AMerger):
    logMsg = u'\n=== ' + _(u'Race Relations Changed') + u': %d'
    _add_tag = u'R.Relations.Add'
    _change_tag = u'R.Relations.Change'
    _remove_tag = u'R.Relations.Remove'
    _wanted_subrecord = {b'RACE': u'relations'}

    def _entry_key(self, subrecord_entry):
        return subrecord_entry.faction

#------------------------------------------------------------------------------
class ImportRelationsPatcher(_AMerger):
    logMsg = u'\n=== ' + _(u'Modified Factions') + u': %d'
    _add_tag = u'Relations.Add'
    _change_tag = u'Relations.Change'
    _remove_tag = u'Relations.Remove'
    _wanted_subrecord = {b'FACT': u'relations'}

    def _entry_key(self, subrecord_entry):
        return subrecord_entry.faction

#------------------------------------------------------------------------------
# Patchers to absorb ----------------------------------------------------------
#------------------------------------------------------------------------------
class ImportActorsAIPackagesPatcher(ImportPatcher):
    logMsg = u'\n=== ' + _(u'AI Package Lists Changed') + u': %d'
    _read_sigs = bush.game.actor_types

    def __init__(self, p_name, p_file, p_sources):
        super(ImportActorsAIPackagesPatcher, self).__init__(p_name, p_file, p_sources)
        # long_fid -> {u'merged':list[long_fid], u'deleted':list[long_fid]}
        self.id_merged_deleted = {}

    def _insertPackage(self, id_merged_deleted, fi, index, pkg, recordData):
        fi_merged = id_merged_deleted[fi][u'merged']
        if index == 0: fi_merged.insert(0, pkg)# insert as first item
        elif index == (len(recordData[u'merged']) - 1):
            fi_merged.append(pkg)  # insert as last item
        else:  # figure out a good spot to insert it based on next or last
            # recognized item (ugly ugly ugly)
            i = index - 1
            while i >= 0:
                if recordData[u'merged'][i] in fi_merged:
                    slot = fi_merged.index(
                        recordData[u'merged'][i]) + 1
                    fi_merged.insert(slot, pkg)
                    break
                i -= 1
            else:
                i = index + 1
                while i != len(recordData[u'merged']):
                    if recordData[u'merged'][i] in fi_merged:
                        slot = fi_merged.index(
                            recordData[u'merged'][i])
                        fi_merged.insert(slot, pkg)
                        break
                    i += 1

    def initData(self,progress):
        """Get data from source files."""
        if not self.isActive: return
        read_sigs = self._read_sigs
        self.loadFactory = self._patcher_read_fact()
        progress.setFull(len(self.srcs))
        cachedMasters = {}
        mer_del = self.id_merged_deleted
        minfs = self.patchFile.all_plugins
        for index,srcMod in enumerate(self.srcs):
            if not (srcInfo := minfs.get(srcMod)):
                continue
            tempData = {}
            srcFile = self._mod_file_read(srcInfo)
            force_add = 'Actors.AIPackagesForceAdd' in srcInfo.getBashTags()
            mod_tops = set()
            for rsig, block in srcFile.iter_tops(read_sigs):
                mod_tops.add(rsig)
                for rid, record in block.iter_present_records():
                    tempData[rid] = record.aiPackages
            for master in reversed(srcInfo.masterNames):
                if master not in minfs: continue # or break filter mods
                try:
                    masterFile = cachedMasters[master]
                except KeyError:
                    masterInfo = minfs[master]
                    masterFile = self._mod_file_read(masterInfo)
                    cachedMasters[master] = masterFile
                for rsig, block in masterFile.iter_tops(mod_tops):
                    for rid, record in block.iter_present_records():
                        if rid not in tempData: continue
                        if record.aiPackages == tempData[rid] and not force_add:
                            # if subrecord is identical to the last master
                            # then we don't care about older masters.
                            del tempData[rid]
                            continue
                        if rid in mer_del:
                            if tempData[rid] == mer_del[rid][u'merged']:
                                continue
                        recordData = {'deleted': [], 'merged': tempData[rid]}
                        for pkg in record.aiPackages:
                            if pkg not in tempData[rid]:
                                recordData[u'deleted'].append(pkg)
                        if rid not in mer_del:
                            mer_del[rid] = recordData
                        else:
                            for pkg in recordData[u'deleted']:
                                if pkg in mer_del[rid][u'merged']:
                                    mer_del[rid][u'merged'].remove(pkg)
                                mer_del[rid][u'deleted'].append(pkg)
                            if mer_del[rid][u'merged'] == []:
                                for pkg in recordData[u'merged']:
                                    if pkg in mer_del[rid][u'deleted'] and not force_add:
                                        continue
                                    mer_del[rid][u'merged'].append(pkg)
                                continue
                            for index, pkg in enumerate(recordData[u'merged']):
                                fi_merged = mer_del[rid]['merged']
                                if pkg not in fi_merged: # so needs to be
                                    # added... (unless deleted that is)
                                    # find the correct position to add and add.
                                    if force_add or pkg not in mer_del[rid][
                                            'deleted']:
                                        self._insertPackage(mer_del, rid, index,
                                                            pkg, recordData)
                                    continue # Done with this package
                                if index == (dex := fi_merged.index(pkg)) or (
                                        len(recordData['merged']) - index) == (
                                        len(fi_merged) - dex):
                                    continue  # pkg same in both lists.
                                # this import is later loading so we'll assume
                                # it is better order
                                fi_merged.remove(pkg)
                                self._insertPackage(mer_del, rid, index,
                                                    pkg, recordData)
            progress.plus()

    def scanModFile(self, modFile, progress): # scanModFile2: loop, LongTypes..
        """Add record from modFile."""
        merged_deleted = self.id_merged_deleted
        for top_grup_sig, block in modFile.iter_tops(self._read_sigs):
            patchBlock = self.patchFile.tops[top_grup_sig]
            for rid, rec in block.iter_present_records():
                if rid not in merged_deleted: continue
                if rec.aiPackages != merged_deleted[rid]['merged']:
                    patchBlock.setRecord(rec)

    def buildPatch(self,log,progress): # buildPatch1:no modFileTops, for type..
        """Applies delta to patchfile."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        merged_deleted = self.id_merged_deleted
        mod_count = Counter()
        for top_grup_sig, block in self.patchFile.iter_tops(self._read_sigs):
            for rid, record in block.id_records.items():
                if rid not in merged_deleted: continue
                if record.aiPackages != merged_deleted[rid][u'merged']:
                    record.aiPackages = merged_deleted[rid][u'merged']
                    mod_count[rid.mod_fn] += keep(rid, record)
        self.id_merged_deleted.clear()
        self._patchLog(log,mod_count)

    def _plog(self, log, mod_count): self._plog1(log, mod_count)

#------------------------------------------------------------------------------
class ImportActorsSpellsPatcher(ImportPatcher):
    logMsg = u'\n=== ' + _(u'Spell Lists Changed') + u': %d'
    _actor_sigs = bush.game.actor_types
    _spel_sigs = bush.game.spell_types
    if bush.game.Esp.sort_lvsp_after_spel:
        # We need to read LVSP & SPEL to properly sort spell lists in actors
        ##: This is a workaround, see MelSpellsTes4 for the proper solution
        _read_sigs = _actor_sigs + _spel_sigs
    else:
        _read_sigs = _actor_sigs

    def __init__(self, p_name, p_file, p_sources):
        super(ImportActorsSpellsPatcher, self).__init__(p_name, p_file, p_sources)
        # long_fid -> {u'merged':list[long_fid], u'deleted':list[long_fid]}
        self._id_merged_deleted = {}
        # long_fid -> rec_sig
        self._spel_type = {}

    def _index_spells(self, modFile):
        """Helper method for indexing SPEL and LVSP types during initData."""
        if bush.game.Esp.sort_lvsp_after_spel:
            spel_type = self._spel_type
            for spel_top_sig, block in modFile.iter_tops(self._spel_sigs):
                for rid, record in block.iter_present_records():
                    # Don't worry about overwriting - record type collisions
                    # are going to cause far worse problems than some
                    # mis-sorted spells in the BP :)
                    spel_type[rid] = record._rec_sig

    def initData(self,progress):
        """Get data from source files."""
        if not self.isActive: return
        actor_sigs = self._actor_sigs
        self.loadFactory = self._patcher_read_fact()
        progress.setFull(len(self.srcs))
        cachedMasters = {}
        mer_del = self._id_merged_deleted
        minfs = self.patchFile.all_plugins
        for srcMod in self.srcs:
            tempData = {}
            if srcMod not in minfs: continue
            srcInfo = minfs[srcMod]
            srcFile = self._mod_file_read(srcInfo)
            self._index_spells(srcFile)
            force_add = 'Actors.SpellsForceAdd' in srcInfo.getBashTags()
            mod_tops = set()
            for rsig, block in srcFile.iter_tops(actor_sigs):
                mod_tops.add(rsig)
                for rid, record in block.iter_present_records():
                    tempData[rid] = record.spells
            for master in reversed(srcInfo.masterNames):
                if master not in minfs: continue # or break filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = minfs[master]
                    masterFile = self._mod_file_read(masterInfo)
                    self._index_spells(masterFile)
                    cachedMasters[master] = masterFile
                for rsig, block in masterFile.iter_tops(mod_tops):
                    for rid, record in block.iter_present_records():
                        if rid not in tempData: continue
                        if record.spells == tempData[rid] and not force_add:
                            # if subrecord is identical to the last master then we don't care about older masters.
                            del tempData[rid]
                            continue
                        if rid in mer_del:
                            if tempData[rid] == mer_del[rid][u'merged']: continue
                        recordData = {u'deleted':[],u'merged':tempData[rid]}
                        for spell in record.spells:
                            if spell not in tempData[rid]:
                                recordData[u'deleted'].append(spell)
                        if rid not in mer_del:
                            mer_del[rid] = recordData
                        else:
                            for spell in recordData[u'deleted']:
                                if spell in mer_del[rid][u'merged']:
                                    mer_del[rid][u'merged'].remove(spell)
                                mer_del[rid][u'deleted'].append(spell)
                            if mer_del[rid][u'merged'] == []:
                                for spell in recordData[u'merged']:
                                    if spell in mer_del[rid][u'deleted'] and not force_add: continue
                                    mer_del[rid][u'merged'].append(spell)
                                continue
                            len_mer = len(rec_merged := recordData['merged'])
                            fi_merged = mer_del[rid]['merged']
                            for index, spell in enumerate(rec_merged):
                                if spell not in fi_merged: # so needs to be added... (unless deleted that is)
                                    # find the correct position to add and add.
                                    if spell in mer_del[rid][u'deleted'] and not force_add: continue #previously deleted
                                    if index == 0: #insert as first item
                                        fi_merged.insert(0, spell)
                                    elif index == (len_mer - 1):
                                        fi_merged.append(spell) #insert as last item
                                    else: #figure out a good spot to insert it based on next or last recognized item (ugly ugly ugly)
                                        for i in range(index - 1, -1, -1):
                                            try:
                                                slot = fi_merged.index(rec_merged[i]) + 1
                                                fi_merged.insert(slot, spell)
                                                break
                                            except ValueError: continue
                                        else:
                                            for i in range(index + 1, len_mer):
                                                try:
                                                    slot = fi_merged.index(rec_merged[i])
                                                    fi_merged.insert(slot, spell)
                                                    break
                                                except ValueError: continue
                                    continue # Done with this package
                                elif index == (dex := fi_merged.index(spell)) or (len_mer - index) == (len(fi_merged) - dex): continue #spell same in both lists.
                                else: #this import is later loading so we'll assume it is better order
                                    fi_merged.remove(spell)
                                    if index == 0: # insert as first item
                                        fi_merged.insert(0, spell)
                                    elif index == (len_mer - 1):
                                        fi_merged.append(spell) # insert as last item
                                    else:
                                        for i in range(index - 1, -1, -1):
                                            try:
                                                slot = fi_merged.index(rec_merged[i]) + 1
                                                fi_merged.insert(slot, spell)
                                                break
                                            except ValueError: continue
                                        else:
                                            for i in range(index + 1, len_mer):
                                                try:
                                                    slot = fi_merged.index(rec_merged[i])
                                                    fi_merged.insert(slot, spell)
                                                    break
                                                except ValueError: continue
            progress.plus()

    def scanModFile(self, modFile, progress): # scanModFile2
        """Add record from modFile."""
        merged_deleted = self._id_merged_deleted
        for top_grup_sig, block in modFile.iter_tops(self._actor_sigs):
            patch_set = self.patchFile.tops[top_grup_sig].setRecord
            for rid, rec in block.iter_present_records():
                if (rid in merged_deleted and rec.spells !=
                        merged_deleted[rid]['merged']):
                    patch_set(rec)
        # This plugin may override a record we're interested in and add spells
        # we then need to sort, so we have to index them here
        self._index_spells(modFile)

    def buildPatch(self,log,progress): # buildPatch1:no modFileTops, for type..
        """Applies delta to patchfile."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        merged_deleted = self._id_merged_deleted
        special_lvsp_sort = bush.game.Esp.sort_lvsp_after_spel
        spel_type = self._spel_type
        mod_count = Counter()
        def sorted_spells(spell_list):
            # First pass: sort by the final load order (and ObjectID)
            spells_ret = sorted(spell_list,
                key=lambda s: (load_order.cached_lo_index(s.mod_fn), s.object_dex))
            if special_lvsp_sort:
                # Second pass: sort LVSP after SPEL
                spells_ret.sort(key=lambda s: spel_type[s] == b'LVSP')
            return spells_ret
        for top_grup_sig in self._actor_sigs:
            for rid, record in self.patchFile.tops[top_grup_sig].id_records.items():
                if rid not in merged_deleted:
                    continue
                merged_spells = sorted_spells(
                    merged_deleted[rid]['merged'])
                if sorted_spells(record.spells) != merged_spells:
                    record.spells = merged_spells
                    mod_count[rid.mod_fn] += keep(rid, record)
        self._id_merged_deleted.clear()
        self._patchLog(log,mod_count)

    def _plog(self, log, mod_count): self._plog1(log, mod_count)

#------------------------------------------------------------------------------
class _AListsMerger(ListPatcher):
    """Merges lists of objects, e.g. leveled lists or FormID lists."""
    patcher_group = u'Special'
    patcher_order = 45
    iiMode = True
    # De/Re Tags - None means the patcher does not have such a tag
    _de_tag = None
    _re_tag = None
    # Maps record type (bytes) to translated label (unicode)
    _sig_to_label = {}
    _de_re_header = None

    def _overhaul_compat(self, mods):
        OOOMods = {*map(FName, (f"Oscuro's_Oblivion_Overhaul.{x}" for x in
                                ('esm', 'esp')))}
        FransMods = {*map(FName, (
            'Francesco.esp', "Francesco's Leveled Creatures-Items Mod.esm"))}
        WCMods = {FName('Oblivion Warcry.esp'),
                  FName('Oblivion Warcry EV.esp')}
        TIEMods = FName('TIE.esp')
        OverhaulCompat = FName('Unofficial Oblivion Patch.esp') in mods and (
                (OOOMods | WCMods) & mods) or (
                                 FransMods & mods and not (TIEMods in mods))
        if OverhaulCompat:
            self.OverhaulUOPSkips = {*map(bush.game.master_fid, [
                    0x03AB5D,  # VendorWeaponBlunt
                    0x03C7F1,  # LL0LootWeapon0Magic4Dwarven100
                    0x03C7F2,  # LL0LootWeapon0Magic7Ebony100
                    0x03C7F3,  # LL0LootWeapon0Magic5Elven100
                    0x03C7F4,  # LL0LootWeapon0Magic6Glass100
                    0x03C7F5,  # LL0LootWeapon0Magic3Silver100
                    0x03C7F7,  # LL0LootWeapon0Magic2Steel100
                    0x03E4D2,  # LL0NPCWeapon0MagicClaymore100
                    0x03E4D3,  # LL0NPCWeapon0MagicClaymoreLvl100
                    0x03E4DA,  # LL0NPCWeapon0MagicWaraxe100
                    0x03E4DB,  # LL0NPCWeapon0MagicWaraxeLvl100
                    0x03E4DC,  # LL0NPCWeapon0MagicWarhammer100
                    0x03E4DD,  # LL0NPCWeapon0MagicWarhammerLvl100
                    0x0733EA,  # ArenaLeveledHeavyShield,
                    0x0C7615,  # FGNPCWeapon0MagicClaymoreLvl100
                    0x181C66,  # SQ02LL0NPCWeapon0MagicClaymoreLvl100
                    0x053877,  # LL0NPCArmor0MagicLightGauntlets100
                    0x053878,  # LL0NPCArmor0MagicLightBoots100
                    0x05387A,  # LL0NPCArmor0MagicLightCuirass100
                    0x053892,  # LL0NPCArmor0MagicLightBootsLvl100
                    0x053893,  # LL0NPCArmor0MagicLightCuirassLvl100
                    0x053894,  # LL0NPCArmor0MagicLightGauntletsLvl100
                    0x053D82,  # LL0LootArmor0MagicLight5Elven100
                    0x053D83,  # LL0LootArmor0MagicLight6Glass100
                    0x052D89,  # LL0LootArmor0MagicLight4Mithril100
                ])}
        else:
            self.OverhaulUOPSkips = set()

    def __init__(self, p_name, p_file, p_sources, remove_empty, tag_choices):
        """In addition to default parameters, accepts a boolean remove_empty,
        which determines whether or not the 'empty sublist removal' logic
        should run, and a defaultdict tag_choices, which maps each tagged
        plugin (represented as paths) to a set of the applied tags (as unicode
        strings, e.g. u'Delev'), defaulting to an empty set.

        :type remove_empty: bool
        :type tag_choices: defaultdict[bolt.Path, set[str]]"""
        super(_AListsMerger, self).__init__(p_name, p_file, p_sources)
        self.isActive |= bool(p_file.load_dict) # Can do meaningful work even without sources
        self.type_list = {rsig: {} for rsig in self._read_sigs}
        self.masterItems = defaultdict(dict)
        # Calculate levelers/de_masters first, using unmodified self.srcs
        self.levelers = [leveler for leveler in self.srcs if
                         leveler in self.patchFile.merged_or_loaded]
        # de_masters is a set of all the masters of each leveler, i.e. each
        # tagged plugin. These are the masters we have to consider records from
        # when determining whether or not to carry forward removals done by a
        # 'De'-tagged plugin
        self.de_masters = set()
        for leveler in self.levelers:
            self.de_masters.update(p_file.all_plugins[leveler].masterNames)
        self.srcs = {s for s in self.srcs if s in p_file.load_dict}
        self.remove_empty_sublists = remove_empty
        self.tag_choices = tag_choices

    def annotate_plugin(self, ann_plugin):
        """Returns the name of the specified plugin, with any Relev/Delev tags
        appended as [ADR], similar to how the patcher GUI displays it.

        :param ann_plugin: The plugin to return the name for, as a path.
        :type ann_plugin: bolt.Path"""
        applied_tags = [t[0] for t in self.tag_choices[ann_plugin]]
        return u'%s%s' % (ann_plugin, (u' [%s]' % u''.join(
            sorted(applied_tags)) if applied_tags else u''))

    def scanModFile(self, modFile, progress):
        #--Begin regular scan
        sc_name = modFile.fileInfo.fn_key
        #--PreScan for later Relevs/Delevs?
        if sc_name in self.de_masters:
            for _sig, block in modFile.iter_tops(self._read_sigs):
                for rid, de_list in block.iter_present_records():
                    self.masterItems[rid][sc_name] = set(
                        self._get_entries(de_list))
        #--Relev/Delev setup
        applied_tags = self.tag_choices[sc_name]
        is_relev = self._re_tag in applied_tags
        is_delev = self._de_tag in applied_tags
        #--Scan
        for list_type_sig, new_lists in modFile.iter_tops(self._read_sigs):
            stored_lists = self.type_list[list_type_sig]
            for rid, new_list in new_lists.iter_present_records():
                # FIXME(inf) This is hideous and slows everything down
                if (sc_name == u'Unofficial Oblivion Patch.esp' and
                        rid in self.OverhaulUOPSkips):
                    stored_lists[rid].mergeOverLast = True
                    continue
                is_list_owner = (rid.mod_fn == sc_name)
                #--Items, delevs and relevs sets
                new_list.items = items = set(self._get_entries(new_list))
                if not is_list_owner:
                    #--Relevs
                    new_list.re_records = items.copy() if is_relev else set()
                    #--Delevs: all items in masters minus current items
                    new_list.de_records = delevs = set()
                    if is_delev:
                        id_master_items = self.masterItems.get(rid)
                        if id_master_items:
                            for de_master in modFile.tes4.masters:
                                if de_master in id_master_items:
                                    delevs |= id_master_items[de_master]
                            # TODO(inf) Double-check that this works correctly,
                            #  this line (delevs -= items) seems a noop here
                            delevs -= items
                            new_list.items |= delevs
                #--Cache/Merge
                if is_list_owner:
                    de_list = copy.deepcopy(new_list)
                    de_list.mergeSources = []
                    stored_lists[rid] = de_list
                elif rid not in stored_lists:
                    de_list = copy.deepcopy(new_list)
                    de_list.mergeSources = [sc_name]
                    stored_lists[rid] = de_list
                else:
                    stored_lists[rid].mergeWith(new_list, sc_name)

    def buildPatch(self, log, progress):
        keep = self.patchFile.getKeeper()
        # Relevs/Delevs List
        log.setHeader(f'= {self._patcher_name}', True)
        log.setHeader(f'=== {self._de_re_header}')
        for leveler in self.levelers:
            log(u'* ' + self.annotate_plugin(leveler))
        # Save to patch file
        for list_type_sig, list_label in self._sig_to_label.items():
            if list_type_sig not in self._read_sigs: continue
            log.setHeader(u'=== ' + _(u'Merged %s Lists') % list_label)
            patch_block = self.patchFile.tops[list_type_sig]
            stored_lists = self.type_list[list_type_sig]
            for stored_list in sorted(stored_lists.values(),
                                      key=lambda l: l.eid or ''):
                if not stored_list.mergeOverLast: continue
                list_fid = stored_list.fid
                if keep(list_fid, stored_list):
                    patch_block.setRecord(stored_lists[list_fid],
                                          do_copy=False)
                    log(f'* {stored_list.eid}')
                    for merge_source in stored_list.mergeSources:
                        log(f'  * {self.annotate_plugin(merge_source)}')
                self._check_list(stored_list, log)
        #--Discard empty sublists
        if not self.remove_empty_sublists: return
        for list_type_sig, list_label in self._sig_to_label.items():
            if list_type_sig not in self._read_sigs: continue
            patch_block = self.patchFile.tops[list_type_sig]
            stored_lists = self.type_list[list_type_sig]
            empty_lists = []
            # Build a dict mapping leveled lists to other leveled lists that
            # they are sublists in
            sub_supers = {x: [] for x in stored_lists} ##: defaultdict??
            for stored_list in stored_lists.values():
                list_fid = stored_list.fid
                if not stored_list.items:
                    empty_lists.append(list_fid)
                else:
                    sub_lists = [x for x in stored_list.items if
                                 x in sub_supers]
                    for sub_list in sub_lists:
                        sub_supers[sub_list].append(list_fid)
            #--Clear empties
            removed_empty_sublists = set()
            cleaned_lists = set()
            while empty_lists:
                empty_list = empty_lists.pop()
                if empty_list not in sub_supers: continue
                # We have an empty list, look if it's a sublist in any other
                # list
                for sub_super in sub_supers[empty_list]:
                    stored_list = stored_lists[sub_super]
                    # Remove the emtpy list from this sublist
                    old_entries = stored_list.entries
                    stored_list.entries = [x for x in stored_list.entries
                                           if x.listId != empty_list]
                    stored_list.items.remove(empty_list)
                    patch_block.setRecord(stored_list, do_copy=False)
                    # If removing the empty list made this list empty too, then
                    # we should investigate it as well - could clean up even
                    # more lists
                    if not stored_list.items:
                        empty_lists.append(sub_super)
                    removed_empty_sublists.add(stored_lists[empty_list].eid)
                    # We don't need to write out records where another mod has
                    # already removed the empty sublist - that would just make
                    # an ITPO
                    if old_entries != stored_list.entries:
                        cleaned_lists.add(stored_list.eid)
                        keep(sub_super, stored_list)
            log.setHeader(u'=== ' + _(u'Empty %s Sublists') % list_label)
            for list_eid in sorted(removed_empty_sublists, key=str.lower):
                log(u'* ' + list_eid)
            log.setHeader(u'=== ' + _(u'Empty %s Sublists Removed') %
                          list_label)
            for list_eid in sorted(cleaned_lists, key=str.lower):
                log(u'* ' + list_eid)

    # Methods for patchers to override
    def _check_list(self, record, log):
        """Checks if any warnings for the specified list have to be logged.
        Default implementation does nothing."""

    def _get_entries(self, target_list):
        """Retrieves a list of the items in the specified list. No default
        implementation, every patcher needs to override this."""
        raise AbstractError()

class LeveledListsPatcher(_AListsMerger):
    """Merges leveled lists."""
    _read_sigs = bush.game.listTypes # bush.game must be set!
    _de_tag = u'Delev'
    _re_tag = u'Relev'
    _sig_to_label = {
        b'LVLC': _(u'Creature'),
        b'LVLN': _(u'Actor'),
        b'LVLI': _(u'Item'),
        b'LVSP': _(u'Spell'),
    }
    _de_re_header = _(u'Delevelers/Relevelers')

    def __init__(self, p_name, p_file, p_sources, remove_empty, tag_choices):
        super(LeveledListsPatcher, self).__init__(p_name, p_file, p_sources,
                                          remove_empty, tag_choices)
        self.empties = set()
        self._overhaul_compat(self.srcs)

    def _check_list(self, record, log):
        # Emit a warning for lists that may have exceeded 255 - note that
        # pre-Skyrim games have no size limit since they have no counter
        max_lvl_size = bush.game.Esp.max_lvl_list_size
        if max_lvl_size and len(record.entries) == max_lvl_size:
            log(u'  * __%s__' % _(u'Warning: Now has %u entries, may '
                                  u'have been truncated - check and '
                                  u'fix manually!') % max_lvl_size)

    def _get_entries(self, target_list):
        return [list_entry.listId for list_entry in target_list.entries]

#------------------------------------------------------------------------------
class FormIDListsPatcher(_AListsMerger):
    """Merges FormID lists."""
    patcher_order = 46
    _read_sigs = (b'FLST',)
    _de_tag = u'Deflst'
    _sig_to_label = {b'FLST': _(u'FormID')}
    _de_re_header = _(u'Deflsters')

    def _get_entries(self, target_list):
        return target_list.formIDInList

#------------------------------------------------------------------------------
class ImportRacesSpellsPatcher(ImportPatcher):
    _read_sigs = (b'RACE',)

    def __init__(self, p_name, p_file, p_sources):
        super().__init__(p_name, p_file, p_sources)
        self.raceData = defaultdict(dict) #--Race eye meshes, hair, eyes

    def initData(self, progress):
        if not self.isActive or not self.srcs: return
        self.loadFactory = self._patcher_read_fact()
        progress.setFull(len(self.srcs))
        cachedMasters = {}
        minfs = self.patchFile.all_plugins
        for index, srcMod in enumerate(self.srcs):
            if srcMod not in minfs: continue
            srcInfo = minfs[srcMod]
            srcFile = self._mod_file_read(srcInfo)
            if b'RACE' not in srcFile.tops: continue
            bashTags = srcInfo.getBashTags()
            tmp_race_data = defaultdict(dict) #so as not to carry anything over!
            change_spells = 'R.ChangeSpells' in bashTags
            add_spells = 'R.AddSpells' in bashTags
            if change_spells and add_spells:
                raise BoltError(f'WARNING mod {srcMod} has both R.AddSpells '
                                f'and R.ChangeSpells tags - only one of '
                                f'those tags should be on a mod at one time')
            for rid, race in srcFile.tops[b'RACE'].iter_present_records():
                if add_spells:
                    tmp_race_data[rid]['AddSpells'] = race.spells
                if change_spells:
                    self.raceData[rid]['spellsOverride'] = race.spells
            for master in srcInfo.masterNames:
                if master not in minfs: continue # or break filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = minfs[master]
                    masterFile = self._mod_file_read(masterInfo)
                    cachedMasters[master] = masterFile
                    if b'RACE' not in masterFile.tops: continue
                for rid, race in masterFile.tops[b'RACE'].iter_present_records():
                    if rid not in tmp_race_data: continue
                    tempRaceData = tmp_race_data[rid]
                    raceData = self.raceData[rid]
                    if u'AddSpells' in tempRaceData:
                        raceData.setdefault(u'AddSpells', []) ##: set?
                        for spell in tempRaceData[u'AddSpells']:
                            if spell not in race.spells:
                                if spell not in raceData[u'AddSpells']:
                                    raceData[u'AddSpells'].append(spell)
                        del tempRaceData[u'AddSpells']
                    for race_key in tempRaceData:
                        if tempRaceData[race_key] != getattr(race, race_key):
                            raceData[race_key] = tempRaceData[race_key]
            progress.plus()

    def scanModFile(self, modFile, progress):
        for top_grup_sig, block in modFile.iter_tops(self._read_sigs):
            patchBlock = self.patchFile.tops[top_grup_sig]
            id_records = patchBlock.id_records
            for rid, record in block.iter_present_records():
                if rid not in id_records:
                    patchBlock.setRecord(record)

    def buildPatch(self, log, progress):
        patchFile = self.patchFile
        if b'RACE' not in patchFile.tops: return
        keep = patchFile.getKeeper()
        racesPatched = []
        for rfid, race in patchFile.tops[b'RACE'].id_records.items():
            raceData = self.raceData.get(rfid, None)
            if not raceData: continue
            orig_spells = race.spells[:]
            if u'spellsOverride' in raceData:
                race.spells = raceData[u'spellsOverride']
            if u'AddSpells' in raceData:
                for spell in raceData[u'AddSpells']:
                    race.spells.append(spell)
            #--Changed
            if race.spells != orig_spells:
                racesPatched.append(race.eid)
                keep(rfid, race)
        #--Done
        log.setHeader(u'= ' + self._patcher_name)
        self._srcMods(log)
        log(u'\n=== ' + _(u'Merged'))
        if not racesPatched:
            log(f'. ~~{_("None")}~~')
        else:
            for eid in sorted(racesPatched):
                log(f'* {eid}')
