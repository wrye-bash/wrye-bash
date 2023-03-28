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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module houses preservers. A preserver is an import patcher that simply
carries forward changes from the last tagged plugin. The goal is to eventually
absorb all of them under the _APreserver base class."""
from __future__ import annotations

import operator
from collections import Counter, defaultdict
from itertools import chain

from ..base import ImportPatcher
from ... import bush, load_order, parsers
from ...bolt import attrgetter_cache, combine_dicts, deprint, setattr_deep
from ...brec import RecordType
from ...exception import ModSigMismatchError

#------------------------------------------------------------------------------
class APreserver(ImportPatcher):
    """Fairly mature base class for preservers. Some parts could (read should)
    be moved to ImportPatcher and used to eliminate duplication with
    _AMerger."""
    # The record attributes to patch. Can be either a straight
    # signature-to-tuple mapping or a more complex mapping for multi-tag
    # importers (see _multi_tag below). Each of the tuples may contain
    # regular attributes (represented as strings), which get carried forward
    # one by one, and fused attributes (represented as tuples of strings),
    # which get carried forward as a 'block' - if one of the attributes in a
    # fused attribute differs, then all attributes in that 'block' get carried
    # forward, even if the others are unchanged. See for example the handling
    # of level_offset and pcLevelOffset
    rec_attrs: dict[bytes, tuple] | dict[bytes, dict[str, tuple]] = {}
    # Record attributes that are FormIDs. These will be checked to see if their
    # FormID is valid before being imported. Set this or Filter plugins will
    # not work correctly when importing FormID data
    _fid_rec_attrs = {}
    # True if this importer is a multi-tag importer. That means its rec_attrs
    # must map record signatures to dicts mapping the tags to a tuple of the
    # subrecords to import, instead of just mapping the record signatures
    # directly to the tuples
    _multi_tag = False
    # A bash tag to force the import of all relevant data from a tagged mod,
    # without it being checked against the masters first. None means no such
    # tag exists for this patcher
    _force_full_import_tag = None
    _filter_in_patch = True

    def __init__(self, p_name, p_file, p_sources):
        #--(attribute-> value) dicts keyed by long fid.
        self.id_data = {}
        self.srcs_sigs = set() #--Record signatures actually provided by src
        # mods/files.
        #--Type Fields
        self._fid_rec_attrs_class = (defaultdict(dict) if self._multi_tag
                                     else defaultdict(tuple))
        self._fid_rec_attrs_class.update(self._fid_rec_attrs)
        # We want FormID attrs in the full rec_type_attrs as well. They're only
        # separate for checking before we import
        if self._multi_tag:
            def _combine_attrs(tag_dict_a: dict[str, tuple[str, ...]],
                    tag_dict_b: dict[str, tuple[str, ...]]):
                return combine_dicts(tag_dict_a, tag_dict_b, operator.add)
        else:
            def _combine_attrs(attrs_a: tuple[str, ...],
                    attrs_b: tuple[str, ...]):
                return attrs_a + attrs_b
        self.rec_type_attrs = combine_dicts(
            self.rec_attrs, self._fid_rec_attrs, _combine_attrs)
        # Check if we need to use setattr_deep to set attributes
        if self._multi_tag:
            all_attrs = chain.from_iterable(
                v for d in self.rec_type_attrs.values()
                for v in d.values())
        else:
            all_attrs = chain.from_iterable(self.rec_type_attrs.values())
        self._deep_attrs = any(u'.' in a for a in all_attrs)
        super().__init__(p_name, p_file, p_sources)

    # CSV helpers
    def _parse_csv_sources(self):
        filtered_dict = super()._parse_csv_sources()
        self.srcs_sigs.update(filtered_dict)
        for src_data in filtered_dict.values():
            self.id_data.update(src_data)

    @property
    def _read_sigs(self):
        return (self.srcs_sigs if self.srcs_sigs else self.rec_type_attrs) if \
            self.isActive else ()

    def _init_data_loop(self, top_grup_sig, src_top, srcMod, mod_id_data,
                        mod_tags, loaded_mods, __attrgetters=attrgetter_cache):
        rec_attrs = self.rec_type_attrs[top_grup_sig]
        fid_attrs = self._fid_rec_attrs_class[top_grup_sig]
        if self._multi_tag:
            # For multi-tag importers, we need to look up the applied bash tags
            # and use those to find all applicable attributes
            def _merge_attrs(to_merge):
                """Helper to concatenate all applicable tags' attributes into a
                final list while preserving order."""
                merged_attrs = []
                merged_attrs_set = set()
                for t, m_attrs in to_merge.items():
                    if t in mod_tags:
                        for a in m_attrs:
                            if a not in merged_attrs_set:
                                merged_attrs_set.add(a)
                                merged_attrs.append(a)
                return merged_attrs
            rec_attrs = _merge_attrs(rec_attrs)
            fid_attrs = _merge_attrs(fid_attrs)
        # Faster than a dict since we save the items() call in the (very hot)
        # loop below ##: Measure again now that we're on 3.11
        ra_getters = [(a, __attrgetters[a]) for a in rec_attrs]
        fa_getters = [__attrgetters[a] for a in fid_attrs]
        # If we have FormID attributes, check those before importing - since
        # this is constant for the entire loop, duplicate the loop to save the
        # overhead in the no-FormIDs case
        if fa_getters:
            for rfid, record in src_top.iter_present_records():
                fid_attr_values = [getter(record) for getter in fa_getters]
                if any(f and (f.mod_fn not in loaded_mods) for f in
                       fid_attr_values):
                    # Ignore the record. Another option would be to just ignore
                    # the fid_attr_values result
                    self.patchFile.patcher_mod_skipcount[
                        self._patcher_name][srcMod] += 1
                    continue
                mod_id_data[rfid] = {attr: getter(record) for attr, getter in
                                     ra_getters}
        else:
            for rfid, record in src_top.iter_present_records():
                mod_id_data[rfid] = {attr: getter(record) for attr, getter in
                                     ra_getters}

    def initData(self, progress, __attrgetters=attrgetter_cache):
        if not self.isActive: return
        id_data = defaultdict(dict)
        progress.setFull(len(self.srcs))
        loaded_mods = self.patchFile.load_dict
        srcssigs = set()
        for srcMod in self.srcs:
            mod_id_data = {}
            srcFile = self.patchFile.get_loaded_mod(srcMod)
            mod_sigs = set()
            mod_tags = srcFile.fileInfo.getBashTags()
            # don't use _read_sigs here as srcs_sigs might be updated in
            # _parse_csv_sources
            for rsig, block in srcFile.iter_tops(self.rec_type_attrs):
                srcssigs.add(rsig)
                mod_sigs.add(rsig)
                self._init_data_loop(rsig, block, srcMod, mod_id_data,
                                     mod_tags, loaded_mods, __attrgetters)
            if (self._force_full_import_tag and
                    self._force_full_import_tag in mod_tags):
                # We want to force-import - copy the temp data without
                # filtering by masters, then move on to the next mod
                id_data.update(mod_id_data)
                continue
            for master in srcFile.fileInfo.masterNames:
                if not (masterFile := self.patchFile.get_loaded_mod(master)):
                    continue # or break filter mods
                for rsig, block in masterFile.iter_tops(mod_sigs):
                    for rfid, record in block.iter_present_records():
                        if rfid not in mod_id_data: continue
                        for attr, val in mod_id_data[rfid].items():
                            try:
                                if val == __attrgetters[attr](record):
                                    continue
                                else:
                                    id_data[rfid][attr] = val
                            except AttributeError:
                                raise ModSigMismatchError(master, record)
            progress.plus()
        self.id_data = {**id_data, **self.id_data} # csvs take precedence
        self.srcs_sigs.update(srcssigs)
        self.isActive = bool(self.srcs_sigs)

    @property
    def _keep_ids(self):
        return self.id_data

    def _add_to_patch(self, rid, record, top_sig, *,
                      __attrgetters=attrgetter_cache):
        for att, val in self.id_data[rid].items():
            if __attrgetters[att](record) != val:
                return True

    def _inner_loop(self, keep, records, top_mod_rec, type_count,
                    __attrgetters=attrgetter_cache):
        loop_setattr = setattr_deep if self._deep_attrs else setattr
        id_data_dict = self.id_data
        for rfid, record in records:
            if rfid not in id_data_dict: continue
            for attr, val in id_data_dict[rfid].items():
                if __attrgetters[attr](record) != val: break
            else: continue
            for attr, val in id_data_dict[rfid].items():
                if isinstance(attr, tuple):
                    # This is a fused attribute, so unpack the attrs and assign
                    # each value to each matching attr
                    for f_a, f_v in zip(attr, val):
                        loop_setattr(record, f_a, f_v)
                else:
                    # This is a regular attribute, so we just need to assign it
                    loop_setattr(record, attr, val)
            keep(rfid, record)
            type_count[top_mod_rec] += 1

    def buildPatch(self, log, progress):
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        type_count = Counter()
        for rsig, block in self.patchFile.iter_tops(self.srcs_sigs):
            present_recs = block.iter_present_records()
            self._inner_loop(keep, present_recs, rsig, type_count)
        self.id_data.clear() # cleanup to save memory
        # Log
        self._patchLog(log, type_count)

#------------------------------------------------------------------------------
# Absorbed patchers -----------------------------------------------------------
#------------------------------------------------------------------------------
class ImportActorsPatcher(APreserver):
    rec_attrs = bush.game.actor_importer_attrs
    _fid_rec_attrs = bush.game.actor_importer_fid_attrs
    _multi_tag = True

#------------------------------------------------------------------------------
class ImportActorsFacesPatcher(APreserver):
    logMsg = '\n=== ' + _('Faces Patched')
    rec_attrs = {b'NPC_': {
        'NPC.FaceGen': ('fggs_p', 'fgga_p', 'fgts_p'),
        'NPC.Hair': ('hairLength', 'hairRed', 'hairBlue', 'hairGreen'),
        'NpcFacesForceFullImport': (
            'fggs_p', 'fgga_p', 'fgts_p', 'hairLength', 'hairRed', 'hairBlue',
            'hairGreen'),
    }}
    _fid_rec_attrs = {b'NPC_': {
        'NPC.Eyes': ('eye',),
        'NPC.Hair': ('hair',),
        'NpcFacesForceFullImport': ('eye', 'hair'),
    }}
    _multi_tag = True
    _force_full_import_tag = 'NpcFacesForceFullImport'

#------------------------------------------------------------------------------
class ImportActorsFactionsPatcher(APreserver):
    logMsg = u'\n=== ' + _(u'Refactioned Actors')
    srcsHeader = u'=== ' + _(u'Source Mods/Files')
    # Has FormIDs, but will be filtered in AMreActor.keep_fids
    rec_attrs = {x: (u'factions',) for x in bush.game.actor_types}
    _csv_parser = parsers.ActorFactions

    def _filter_csv_fids(self, parser_instance, loaded_csvs):
        """Transform the parser structure to the one used by the patcher."""
        filtered_dict = super()._filter_csv_fids(parser_instance, loaded_csvs)
        # filter existing factions and convert to the patcher representation
        earlier_loading = self.patchFile.all_plugins
        patcher_dict = {}
        for sig, d in filtered_dict.items():
            rec_type = RecordType.sig_to_class[sig]
            patcher_dict_sig = {}
            for f, facts in d.items():
                fact_obj = []
                for fact_fid, rank in facts.items():
                    if fact_fid.mod_fn not in earlier_loading: continue
                    ret_obj = rec_type.getDefault('factions')
                    ret_obj.faction = fact_fid
                    ret_obj.rank = rank
                    ret_obj.unused1 = b'ODB'
                    fact_obj.append(ret_obj)
                if fact_obj: patcher_dict_sig[f] = {'factions': fact_obj}
            if patcher_dict_sig: patcher_dict[sig] = patcher_dict_sig
        return patcher_dict

#------------------------------------------------------------------------------
class ImportDestructiblePatcher(APreserver):
    """Merges changes to destructible records."""
    ##: Has FormIDs, filter these in keep_fids?
    rec_attrs = {x: (u'destructible',) for x in bush.game.destructible_types}

#------------------------------------------------------------------------------
class ImportEffectsStatsPatcher(APreserver):
    """Preserves changes to MGEF stats."""
    rec_attrs = {b'MGEF': bush.game.mgef_stats_attrs}
    _fid_rec_attrs = {b'MGEF': bush.game.mgef_stats_fid_attrs}

#------------------------------------------------------------------------------
class ImportEnchantmentsPatcher(APreserver):
    """Preserves changes to EITM (enchantment/object effect) subrecords."""
    _fid_rec_attrs = {x: ('enchantment',) for x in bush.game.enchantment_types}

#------------------------------------------------------------------------------
class ImportEnchantmentStatsPatcher(APreserver):
    """Preserves changes to ENCH stats."""
    rec_attrs = {b'ENCH': bush.game.ench_stats_attrs}
    _fid_rec_attrs = {b'ENCH': bush.game.ench_stats_fid_attrs}

#------------------------------------------------------------------------------
class ImportKeywordsPatcher(APreserver):
    # Has FormIDs, but will be filtered in AMreWithKeywords.keep_fids
    rec_attrs = {x: (u'keywords',) for x in bush.game.keywords_types}

#------------------------------------------------------------------------------
class ImportNamesPatcher(APreserver):
    """Import names from source mods/files."""
    logMsg =  '\n=== ' + _('Renamed Items')
    srcsHeader = u'=== ' + _(u'Source Mods/Files')
    rec_attrs = {x: (u'full',) for x in bush.game.namesTypes}
    _csv_parser = parsers.FullNames

#------------------------------------------------------------------------------
class ImportObjectBoundsPatcher(APreserver):
    rec_attrs = {x: (u'bounds',) for x in bush.game.object_bounds_types}

#------------------------------------------------------------------------------
class ImportScriptsPatcher(APreserver):
    _fid_rec_attrs = {x: ('script_fid',) for x in bush.game.scripts_types}

#------------------------------------------------------------------------------
class ImportSoundsPatcher(APreserver):
    """Imports sounds from source mods into patch."""
    rec_attrs = bush.game.sounds_attrs
    _fid_rec_attrs = bush.game.sounds_fid_attrs

#------------------------------------------------------------------------------
class ImportSpellStatsPatcher(APreserver):
    """Import spell changes from mod files."""
    srcsHeader = u'=== ' + _(u'Source Mods/Files')
    rec_attrs = {x: bush.game.spell_stats_attrs
                 for x in bush.game.spell_stats_types}
    _fid_rec_attrs = {x: bush.game.spell_stats_fid_attrs
                      for x in bush.game.spell_stats_types}
    _csv_parser = parsers.SpellRecords if bush.game.fsName == 'Oblivion' \
        else None

#------------------------------------------------------------------------------
class ImportStatsPatcher(APreserver):
    """Import stats from mod file."""
    patcher_order = 28 # Run ahead of Bow Reach Fix ##: This seems unneeded
    logMsg = u'\n=== ' + _(u'Imported Stats')
    srcsHeader = u'=== ' + _(u'Source Mods/Files')
    rec_attrs = bush.game.stats_attrs
    _fid_rec_attrs = bush.game.stats_fid_attrs
    _csv_parser = parsers.ItemStats

#------------------------------------------------------------------------------
class ImportTextPatcher(APreserver):
    rec_attrs = bush.game.text_types

#------------------------------------------------------------------------------
# Patchers to absorb ----------------------------------------------------------
#------------------------------------------------------------------------------
##: absorbing this one will be hard - or not :P
class ImportCellsPatcher(ImportPatcher):
    logMsg = '\n=== ' + _('Cells/Worlds Patched')
    _read_sigs = (b'CELL', b'WRLD')

    def __init__(self, p_name, p_file, p_sources):
        super(ImportCellsPatcher, self).__init__(p_name, p_file, p_sources)
        self.cellData = defaultdict(dict)
        self.recAttrs = bush.game.cellRecAttrs # dict[str, tuple[str]]

    def initData(self, progress, __attrgetters=attrgetter_cache):
        """Get cells from source files."""
        if not self.isActive: return
        cellData = self.cellData
        progress.setFull(len(self.srcs))
        for srcMod in self.srcs:
            # tempCellData maps long fids for cells in srcMod to dicts of
            # (attributes (among attrs) -> their values for this mod). It is
            # used to update cellData with cells that change those attributes'
            # values from the value in any of srcMod's masters.
            tempCellData = defaultdict(dict)
            srcInfo = self.patchFile.all_plugins[srcMod]
            bashTags = srcInfo.getBashTags()
            tags = bashTags & set(self.recAttrs)
            if not tags: continue
            srcFile = self.patchFile.get_loaded_mod(srcMod)
            attrs = set(chain.from_iterable(
                self.recAttrs[bashKey] for bashKey in tags))
            interior_attrs = attrs - bush.game.cell_skip_interior_attrs
            # Add attribute values from source mods to a temporary cache. These
            # are used to filter for required records by formID and to update
            # the attribute values taken from the master files when creating
            # cell_data.
            for _sig, block in srcFile.iter_tops(self._read_sigs):
                # for the WRLD block iter_present_records will return
                # exterior cells and the persistent cell - previous code
                # did not differentiate either
                for cfid, cell_rec in block.iter_present_records(b'CELL'):
                    # If we're in an interior, see if we have to ignore
                    # any attrs
                    actual_attrs = interior_attrs if \
                        cell_rec.flags.isInterior else attrs
                    for att in actual_attrs:
                        tempCellData[cfid][att] = __attrgetters[att](cell_rec)
            # Add attribute values from record(s) in master file(s). Only adds
            # records where a matching formID is found in temp cell data. The
            # attribute values in temp cell data are then used to update these
            # records where the value is different.
            for master in srcInfo.masterNames:
                if not (masterFile := self.patchFile.get_loaded_mod(master)):
                    continue # or break filter mods
                for _sig, block in masterFile.iter_tops(self._read_sigs):
                    for cfid, cell_rec in block.iter_present_records(b'CELL'):
                        if cfid not in tempCellData: continue
                        attrs1 = interior_attrs if cell_rec.flags.isInterior\
                            else attrs
                        for att in attrs1:
                            master_attr = __attrgetters[att](cell_rec)
                            if tempCellData[cfid][att] != master_attr:
                                cellData[cfid][att] = tempCellData[cfid][att]
            progress.plus()

    def _add_to_patch(self, rid, cell_wrld_block, top_sig):
        """Handle CELL and WRLD top blocks here."""
        if top_sig == b'CELL' and rid in self.cellData:
            self.patchFile.tops[b'CELL'].setRecord(
                cell_wrld_block.master_record)
        elif top_sig == b'WRLD':
            curr_pworld = self.patchFile.tops[b'WRLD'].setRecord(
                cell_wrld_block.master_record)
            for rid, cell_rec in cell_wrld_block.iter_present_records(b'CELL'):
                if rid in self.cellData:
                    curr_pworld.set_cell(cell_rec)

    def buildPatch(self, log, progress, __attrgetters=attrgetter_cache):
        """Adds merged lists to patchfile."""
        if not self.isActive: return
        def handlePatchCellBlock():
            """This function checks if an attribute or flag in CellData has
            a value which is different to the corresponding value in the
            bash patch file.
            The Patch file will contain the last corresponding record
            found when it is created regardless of tags.
            If the CellData value is different, then the value is copied
            to the bash patch, and the cell is flagged as modified.
            Modified cell Blocks are kept, the other are discarded."""
            cell_modified = False
            for attr, val in cellData[cell_fid].items():
                if val != __attrgetters[attr](patch_cell):
                    setattr_deep(patch_cell, attr, val)
                    cell_modified = True
            if cell_modified:
                keep(cell_fid, patch_cell)
            return cell_modified
        keep = self.patchFile.getKeeper()
        cellData, count = self.cellData, Counter()
        for cell_fid, patch_cell in self.patchFile.tops[b'CELL'
                ].iter_present_records(b'CELL'):
            if cell_fid in cellData and handlePatchCellBlock():
                count[cell_fid.mod_fn] += 1
        for worldId, worldBlock in self.patchFile.tops[
            b'WRLD'].id_records.items():
            keepWorld = False
            for cell_fid, patch_cell in worldBlock.get_cells():
                if cell_fid in cellData and handlePatchCellBlock():
                    count[cell_fid.mod_fn] += 1
                    keepWorld = True
            if keepWorld:
                keep(worldId, worldBlock)
        self.cellData.clear()
        self._patchLog(log, count)

    def _plog(self,log,count): # type 1 but for logMsg % sum(...)
        log(self.__class__.logMsg)
        for srcMod in load_order.get_ordered(count):
            log(f'* {srcMod}: {count[srcMod]:d}')

#------------------------------------------------------------------------------
class ImportGraphicsPatcher(APreserver):
    rec_attrs = bush.game.graphicsTypes
    _fid_rec_attrs = bush.game.graphicsFidTypes

    def _inner_loop(self, keep, records, top_mod_rec, type_count,
                    __attrgetters=attrgetter_cache):
        id_data_dict = self.id_data
        for rfid, record in records:
            if rfid not in id_data_dict: continue
            for attr, val in id_data_dict[rfid].items():
                rec_attr = __attrgetters[attr](record)
                if isinstance(rec_attr, str) and isinstance(val, str):
                    if rec_attr.lower() != val.lower():
                        break
                    continue
                elif attr in bush.game.graphicsModelAttrs:
                    try:
                        if rec_attr.modPath.lower() != val.modPath.lower():
                            break
                        continue
                    except AttributeError:
                        if rec_attr is val is None: continue
                        if rec_attr is None or val is None: # not both
                            break
                        if rec_attr.modPath is val.modPath is None: continue
                        break
                if rec_attr != val: break
            else: continue
            for attr, val in id_data_dict[rfid].items():
                setattr(record, attr, val)
            keep(rfid, record)
            type_count[top_mod_rec] += 1

#------------------------------------------------------------------------------
class ImportRacesPatcher(APreserver):
    rec_attrs = bush.game.import_races_attrs
    _fid_rec_attrs = bush.game.import_races_fid_attrs
    _multi_tag = True

    def _inner_loop(self, keep, records, top_mod_rec, type_count,
                    __attrgetters=attrgetter_cache):
        loop_setattr = setattr_deep if self._deep_attrs else setattr
        id_data_dict = self.id_data
        for rfid, record in records:
            if rfid not in id_data_dict: continue
            for att, val in id_data_dict[rfid].items():
                record_val = __attrgetters[att](record)
                if att in ('eyes', 'hairs'):
                    if set(record_val) != set(val): break
                else:
                    if att in ('leftEye', 'rightEye') and not record_val:
                        deprint(f'Very odd race {record.full} found - {att} '
                                f'is None')
                    elif record_val != val: break
            else: continue
            for att, val in id_data_dict[rfid].items():
                loop_setattr(record, att, val)
            keep(rfid, record)
            type_count[top_mod_rec] += 1
