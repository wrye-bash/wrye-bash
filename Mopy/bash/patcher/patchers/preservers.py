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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module houses preservers. A preserver is an import patcher that simply
carries forward changes from the last tagged plugin. The goal is to eventually
absorb all of them under the _APreserver base class."""

from collections import defaultdict, Counter
from itertools import chain

# Internal
from .. import getPatchesPath
from ..base import ImportPatcher
from ... import bush, load_order, parsers
from ...bolt import attrgetter_cache, deprint, setattr_deep
from ...brec import MreRecord
from ...exception import ModSigMismatchError

#------------------------------------------------------------------------------
class APreserver(ImportPatcher):
    """Fairly mature base class for preservers. Some parts could (read should)
    be moved to ImportPatcher and used to eliminate duplication with _AMerger.

    :type rec_attrs: dict[bytes, tuple] | dict[bytes, dict[str, tuple]]"""
    rec_attrs = {}
    # Record attributes that are FormIDs. These will be checked to see if their
    # FormID is valid before being imported
    ##: set for more patchers?
    _fid_rec_attrs = {}
    # True if this importer is a multi-tag importer. That means its rec_attrs
    # must map record signatures to dicts mapping the tags to a tuple of the
    # subrecords to import, instead of just mapping the record signatures
    # directly to the tuples
    _multi_tag = False
    _csv_parser = None
    # A bash tag to force the import of all relevant data from a tagged mod,
    # without it being checked against the masters first. None means no such
    # tag exists for this patcher
    _force_full_import_tag = None

    def __init__(self, p_name, p_file, p_sources):
        super(APreserver, self).__init__(p_name, p_file, p_sources)
        #--(attribute-> value) dicts keyed by long fid.
        self.id_data = defaultdict(dict)
        self.srcs_sigs = set() #--Record signatures actually provided by src
        # mods/files.
        #--Type Fields
        self._fid_rec_attrs_class = (defaultdict(dict) if self._multi_tag
                                     else defaultdict(tuple))
        self._fid_rec_attrs_class.update(self._fid_rec_attrs)
        # We want FormID attrs in the full recAttrs as well. They're only
        # separate for checking before we import
        if self._multi_tag: ##: This is hideous
            def collect_attrs(r, tag_dict):
                return {t: a + self._fid_rec_attrs.get(r, {}).get(t, ())
                        for t, a in tag_dict.items()}
        else:
            def collect_attrs(r, a):
                return a + self._fid_rec_attrs.get(r, ())
        self.rec_type_attrs = {r: collect_attrs(r, a)
                               for r, a in self.rec_attrs.items()}
        # Check if we need to use setattr_deep to set attributes
        if self._multi_tag:
            all_attrs = chain.from_iterable(
                v for d in self.rec_type_attrs.values()
                for v in d.values())
        else:
            all_attrs = chain.from_iterable(self.rec_type_attrs.values())
        self._deep_attrs = any(u'.' in a for a in all_attrs)
        # Split srcs based on CSV extension ##: move somewhere else?
        self.csv_srcs = [s for s in p_sources if s.cext == u'.csv']
        self.srcs = [s for s in p_sources if s.cext != u'.csv']
        self.loadFactory = self._patcher_read_fact(by_sig=self.rec_type_attrs)

    # CSV helpers
    def _parse_csv_sources(self, progress):
        """Parses CSV files. Only called if _csv_parser is set."""
        parser_instance = self._csv_parser(self.patchFile.pfile_aliases,
                                           called_from_patcher=True)
        for src_path in self.csv_srcs:
            try:
                parser_instance.readFromText(getPatchesPath(src_path))
            except OSError:
                deprint(u'%s is no longer in patches set' % src_path,
                    traceback=True)
            except UnicodeError:
                deprint(u'%s is not saved in UTF-8 format' % src_path,
                    traceback=True)
            progress.plus()
        parsed_sources = parser_instance.id_stored_data
        # Filter out any entries that don't actually have data or don't
        # actually exist (for this game at least)
        ##: make sure k is always bytes and drop encode below
        filtered_dict = {k.encode(u'ascii') if type(k) is str else k: v
                         for k, v in parsed_sources.items()
                         if v and k in MreRecord.type_class}
        self.srcs_sigs.update(filtered_dict)
        for src_data in filtered_dict.values():
            self.id_data.update(src_data)

    @property
    def _read_sigs(self):
        return self.srcs_sigs

    # noinspection PyDefaultArgument
    def _init_data_loop(self, top_grup_sig, srcFile, srcMod, mod_id_data,
                        mod_tags, loaded_mods, __attrgetters=attrgetter_cache):
        recAttrs = self.rec_type_attrs[top_grup_sig]
        fid_attrs = self._fid_rec_attrs_class[top_grup_sig]
        if self._multi_tag:
            # For multi-tag importers, we need to look up the applied bash tags
            # and use those to find all applicable attributes
            recAttrs = set(chain.from_iterable(
                attrs for t, attrs in recAttrs.items() if t in mod_tags))
            fid_attrs = set(chain.from_iterable(
                attrs for t, attrs in fid_attrs.items() if t in mod_tags))
        for rfid, record in srcFile.tops[top_grup_sig].iter_present_records():
            # If we have FormID attributes, check those before importing
            if fid_attrs:
                fid_attr_values = [__attrgetters[a](record) for a in fid_attrs]
                if any(f and (f[0] not in loaded_mods) for f in
                       fid_attr_values):
                    # Ignore the record. Another option would be to just ignore
                    # the fid_attr_values result
                    self.patchFile.patcher_mod_skipcount[
                        self._patcher_name][srcMod] += 1
                    continue
            mod_id_data[rfid] = {attr: __attrgetters[attr](record) for attr in
                                 recAttrs}

    # noinspection PyDefaultArgument
    def initData(self, progress, __attrgetters=attrgetter_cache):
        if not self.isActive: return
        id_data = self.id_data
        progress.setFull(len(self.srcs) + len(self.csv_srcs))
        cachedMasters = {}
        minfs = self.patchFile.p_file_minfos
        loaded_mods = self.patchFile.loadSet
        for index,srcMod in enumerate(self.srcs):
            mod_id_data = {}
            if srcMod not in minfs: continue
            srcInfo = minfs[srcMod]
            srcFile = self._mod_file_read(srcInfo)
            mod_sigs = set()
            mod_tags = srcFile.fileInfo.getBashTags() if self._multi_tag else None
            for rsig in self.rec_type_attrs:
                if rsig not in srcFile.tops: continue
                self.srcs_sigs.add(rsig)
                mod_sigs.add(rsig)
                self._init_data_loop(rsig, srcFile, srcMod, mod_id_data,
                                     mod_tags, loaded_mods, __attrgetters)
            if (self._force_full_import_tag and
                    self._force_full_import_tag in srcInfo.getBashTags()):
                # We want to force-import - copy the temp data without
                # filtering by masters, then move on to the next mod
                id_data.update(mod_id_data)
                continue
            for master in srcInfo.masterNames:
                if master not in minfs: continue # or break filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterFile = self._mod_file_read(minfs[master])
                    cachedMasters[master] = masterFile
                for rsig in self.rec_type_attrs:
                    if rsig not in masterFile.tops or rsig not in mod_sigs:
                        continue
                    for rfid, record in masterFile.tops[rsig].iter_present_records():
                        if rfid not in mod_id_data: continue
                        for attr, value in mod_id_data[rfid].items():
                            try:
                                if value == __attrgetters[attr](record):
                                    continue
                                else:
                                    id_data[rfid][attr] = value
                            except AttributeError:
                                raise ModSigMismatchError(master, record)
            progress.plus()
        if self._csv_parser:
            self._parse_csv_sources(progress)
        self.isActive = bool(self.srcs_sigs)

    # noinspection PyDefaultArgument
    def scanModFile(self, modFile, progress, __attrgetters=attrgetter_cache):
        id_data = self.id_data
        for rsig in self.srcs_sigs:
            if rsig not in modFile.tops: continue
            patchBlock = self.patchFile.tops[rsig]
            # Records that have been copied into the BP once will automatically
            # be updated by update_patch_records_from_mod/mergeModFile
            copied_records = patchBlock.id_records
            for rfid, record in modFile.tops[rsig].iter_present_records():
                # Skip if we've already copied this record or if we're not
                # interested in it
                if rfid in copied_records or rfid not in id_data: continue
                for attr, value in id_data[rfid].items():
                    if __attrgetters[attr](record) != value:
                        patchBlock.setRecord(record.getTypeCopy())
                        break

    # noinspection PyDefaultArgument
    def _inner_loop(self, keep, records, top_mod_rec, type_count,
                    __attrgetters=attrgetter_cache):
        loop_setattr = setattr_deep if self._deep_attrs else setattr
        id_data = self.id_data
        for rfid, record in records:
            if rfid not in id_data: continue
            for attr, value in id_data[rfid].items():
                if __attrgetters[attr](record) != value: break
            else: continue
            for attr, value in id_data[rfid].items():
                loop_setattr(record, attr, value)
            keep(rfid)
            type_count[top_mod_rec] += 1

    def buildPatch(self, log, progress):
        if not self.isActive: return
        modFileTops = self.patchFile.tops
        keep = self.patchFile.getKeeper()
        type_count = Counter()
        for rsig in self.srcs_sigs:
            if rsig not in modFileTops: continue
            records = modFileTops[rsig].iter_present_records(
                include_ignored=True) ##: why include_ignored?
            self._inner_loop(keep, records, rsig, type_count)
        self.id_data.clear() # cleanup to save memory
        # Log
        self._patchLog(log, type_count)

    def _srcMods(self,log):
        log(self.__class__.srcsHeader)
        all_srcs = self.srcs + self.csv_srcs
        if not all_srcs:
            log(u". ~~%s~~" % _(u'None'))
        else:
            for srcFile in all_srcs:
                log(u"* %s" % srcFile)

#------------------------------------------------------------------------------
# Absorbed patchers -----------------------------------------------------------
#------------------------------------------------------------------------------
class ImportActorsPatcher(APreserver):
    rec_attrs = bush.game.actor_importer_attrs
    _multi_tag = True

#------------------------------------------------------------------------------
##: Could be absorbed by ImportActors, but would break existing configs
class ImportActorsAnimationsPatcher(APreserver):
    rec_attrs = {x: (u'animations',) for x in bush.game.actor_types}

#------------------------------------------------------------------------------
##: Could be absorbed by ImportActors, but would break existing configs
class ImportActorsDeathItemsPatcher(APreserver):
    rec_attrs = {x: (u'deathItem',) for x in bush.game.actor_types}

#------------------------------------------------------------------------------
class ImportActorsFacesPatcher(APreserver):
    logMsg = u'\n=== '+_(u'Faces Patched')
    rec_attrs = {b'NPC_': {
        u'NPC.Eyes': (),
        u'NPC.FaceGen': (u'fggs_p', u'fgga_p', u'fgts_p'),
        u'NPC.Hair': (u'hairLength', u'hairRed', u'hairBlue', u'hairGreen'),
        u'NpcFacesForceFullImport': (u'fggs_p', u'fgga_p', u'fgts_p',
                                     u'hairLength', u'hairRed', u'hairBlue',
                                     u'hairGreen'),
    }}
    _fid_rec_attrs = {b'NPC_': {
        u'NPC.Eyes': (u'eye',),
        u'NPC.FaceGen': (),
        u'NPC.Hair': (u'hair',),
        u'NpcFacesForceFullImport': (u'eye', u'hair'),
    }}
    _multi_tag = True
    _force_full_import_tag = u'NpcFacesForceFullImport'

#------------------------------------------------------------------------------
class ImportActorsFactionsPatcher(APreserver):
    logMsg = u'\n=== ' + _(u'Refactioned Actors')
    srcsHeader = u'=== ' + _(u'Source Mods/Files')
    rec_attrs = {x: (u'factions',) for x in bush.game.actor_types}
    _csv_parser = parsers.ActorFactions

#------------------------------------------------------------------------------
class ImportDestructiblePatcher(APreserver):
    """Merges changes to destructible records."""
    rec_attrs = {x: (u'destructible',) for x in bush.game.destructible_types}

#------------------------------------------------------------------------------
class ImportEffectsStatsPatcher(APreserver):
    """Preserves changes to MGEF stats."""
    rec_attrs = {b'MGEF': bush.game.mgef_stats_attrs}

#------------------------------------------------------------------------------
class ImportEnchantmentStatsPatcher(APreserver):
    """Preserves changes to ENCH stats."""
    rec_attrs = {b'ENCH': bush.game.ench_stats_attrs}

#------------------------------------------------------------------------------
class ImportKeywordsPatcher(APreserver):
    rec_attrs = {x: (u'keywords',) for x in bush.game.keywords_types}

#------------------------------------------------------------------------------
class ImportNamesPatcher(APreserver):
    """Import names from source mods/files."""
    logMsg =  u'\n=== ' + _(u'Renamed Items')
    srcsHeader = u'=== ' + _(u'Source Mods/Files')
    rec_attrs = {x: (u'full',) for x in bush.game.namesTypes}
    _csv_parser = parsers.FullNames

#------------------------------------------------------------------------------
class ImportObjectBoundsPatcher(APreserver):
    rec_attrs = {x: (u'bounds',) for x in bush.game.object_bounds_types}

#------------------------------------------------------------------------------
class ImportScriptsPatcher(APreserver):
    rec_attrs = {x: (u'script_fid',) for x in bush.game.scripts_types}

#------------------------------------------------------------------------------
class ImportSoundsPatcher(APreserver):
    """Imports sounds from source mods into patch."""
    rec_attrs = bush.game.soundsTypes

#------------------------------------------------------------------------------
class ImportSpellStatsPatcher(APreserver):
    """Import spell changes from mod files."""
    srcsHeader = u'=== ' + _(u'Source Mods/Files')
    rec_attrs = {x: bush.game.spell_stats_attrs
                 for x in bush.game.spell_stats_types}
    _csv_parser = parsers.SpellRecords

#------------------------------------------------------------------------------
class ImportStatsPatcher(APreserver):
    """Import stats from mod file."""
    patcher_order = 28 # Run ahead of Bow Reach Fix ##: This seems unneeded
    logMsg = u'\n=== ' + _(u'Imported Stats')
    srcsHeader = u'=== ' + _(u'Source Mods/Files')
    # Don't patch Editor IDs - those are only in statsTypes for the
    # Export/Import links
    rec_attrs = {r: tuple(x for x in a if x != u'eid')
                 for r, a in bush.game.statsTypes.items()}
    _csv_parser = parsers.ItemStats

#------------------------------------------------------------------------------
class ImportTextPatcher(APreserver):
    rec_attrs = bush.game.text_types

#------------------------------------------------------------------------------
# Patchers to absorb ----------------------------------------------------------
#------------------------------------------------------------------------------
##: absorbing this one will be hard - hint: getActiveRecords only exists on
# MobObjects, iter_records works for all Mob* classes, so attack that part of
# _APreserver
class ImportCellsPatcher(ImportPatcher):
    logMsg = u'\n=== ' + _(u'Cells/Worlds Patched')
    _read_sigs = (b'CELL', b'WRLD')

    def __init__(self, p_name, p_file, p_sources):
        super(ImportCellsPatcher, self).__init__(p_name, p_file, p_sources)
        self.cellData = defaultdict(dict)
        self.recAttrs = bush.game.cellRecAttrs # dict[str, tuple[str]]
        self.loadFactory = self._patcher_read_fact()

    def initData(self, progress, __attrgetters=attrgetter_cache):
        """Get cells from source files."""
        if not self.isActive: return
        cellData = self.cellData
        def importCellBlockData(cellBlock):
            """
            Add attribute values from source mods to a temporary cache.
            These are used to filter for required records by formID and
            to update the attribute values taken from the master files
            when creating cell_data.
            """
            if not cellBlock.cell.flags1.ignored:
                cfid = cellBlock.cell.fid
                # If we're in an interior, see if we have to ignore any attrs
                actual_attrs = ((attrs - bush.game.cell_skip_interior_attrs)
                                if cellBlock.cell.flags.isInterior else attrs)
                for attr in actual_attrs:
                    tempCellData[cfid][attr] = __attrgetters[attr](
                        cellBlock.cell)
        def checkMasterCellBlockData(cellBlock):
            """
            Add attribute values from record(s) in master file(s).
            Only adds records where a matching formID is found in temp
            cell data.
            The attribute values in temp cell data are then used to
            update these records where the value is different.
            """
            if not cellBlock.cell.flags1.ignored:
                cfid = cellBlock.cell.fid
                if cfid not in tempCellData: return
                # If we're in an interior, see if we have to ignore any attrs
                actual_attrs = ((attrs - bush.game.cell_skip_interior_attrs)
                                if cellBlock.cell.flags.isInterior else attrs)
                for attr in actual_attrs:
                    master_attr = __attrgetters[attr](cellBlock.cell)
                    if tempCellData[cfid][attr] != master_attr:
                        cellData[cfid][attr] = tempCellData[cfid][attr]
        progress.setFull(len(self.srcs))
        cachedMasters = {}
        minfs = self.patchFile.p_file_minfos
        for srcMod in self.srcs:
            if srcMod not in minfs: continue
            # tempCellData maps long fids for cells in srcMod to dicts of
            # (attributes (among attrs) -> their values for this mod). It is
            # used to update cellData with cells that change those attributes'
            # values from the value in any of srcMod's masters.
            tempCellData = defaultdict(dict)
            srcInfo = minfs[srcMod]
            srcFile = self._mod_file_read(srcInfo)
            cachedMasters[srcMod] = srcFile
            bashTags = srcInfo.getBashTags()
            # print bashTags
            tags = bashTags & set(self.recAttrs)
            if not tags: continue
            attrs = set(chain.from_iterable(
                self.recAttrs[bashKey] for bashKey in tags
                if bashKey in self.recAttrs))
            if b'CELL' in srcFile.tops:
                for cellBlock in srcFile.tops[b'CELL'].cellBlocks:
                    importCellBlockData(cellBlock)
            if b'WRLD' in srcFile.tops:
                for worldBlock in srcFile.tops[b'WRLD'].worldBlocks:
                    for cellBlock in worldBlock.cellBlocks:
                        importCellBlockData(cellBlock)
                    if worldBlock.worldCellBlock:
                        importCellBlockData(worldBlock.worldCellBlock)
            for master in srcInfo.masterNames:
                if master not in minfs: continue # or break filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = minfs[master]
                    masterFile = self._mod_file_read(masterInfo)
                    cachedMasters[master] = masterFile
                if b'CELL' in masterFile.tops:
                    for cellBlock in masterFile.tops[b'CELL'].cellBlocks:
                        checkMasterCellBlockData(cellBlock)
                if b'WRLD' in masterFile.tops:
                    for worldBlock in masterFile.tops[b'WRLD'].worldBlocks:
                        for cellBlock in worldBlock.cellBlocks:
                            checkMasterCellBlockData(cellBlock)
                        if worldBlock.worldCellBlock:
                            checkMasterCellBlockData(worldBlock.worldCellBlock)
            tempCellData = {}
            progress.plus()

    def scanModFile(self, modFile, progress): # scanModFile0
        """Add lists from modFile."""
        if not self.isActive or not (set(modFile.tops) & {b'CELL', b'WRLD'}):
            return
        cellData = self.cellData
        patchCells = self.patchFile.tops[b'CELL']
        patchWorlds = self.patchFile.tops[b'WRLD']
        if b'CELL' in modFile.tops:
            for cellBlock in modFile.tops[b'CELL'].cellBlocks:
                if cellBlock.cell.fid in cellData:
                    patchCells.setCell(cellBlock.cell)
        if b'WRLD' in modFile.tops:
            for worldBlock in modFile.tops[b'WRLD'].worldBlocks:
                patchWorlds.setWorld(worldBlock.world)
                curr_pworld = patchWorlds.id_worldBlocks[worldBlock.world.fid]
                for cellBlock in worldBlock.cellBlocks:
                    if cellBlock.cell.fid in cellData:
                        curr_pworld.setCell(cellBlock.cell)
                pers_cell_block = worldBlock.worldCellBlock
                if pers_cell_block and pers_cell_block.cell.fid in cellData:
                    curr_pworld.worldCellBlock = pers_cell_block

    def buildPatch(self, log, progress, __attrgetters=attrgetter_cache):
        """Adds merged lists to patchfile."""
        def handlePatchCellBlock(patchCellBlock):
            """This function checks if an attribute or flag in CellData has
            a value which is different to the corresponding value in the
            bash patch file.
            The Patch file will contain the last corresponding record
            found when it is created regardless of tags.
            If the CellData value is different, then the value is copied
            to the bash patch, and the cell is flagged as modified.
            Modified cell Blocks are kept, the other are discarded."""
            modified = False
            patch_cell_fid = patchCellBlock.cell.fid
            for attr,value in cellData[patch_cell_fid].items():
                curr_value = __attrgetters[attr](patchCellBlock.cell)
                ##: If we made MelSorted sort on load too, we could drop this -
                # but that might be too expensive? Maybe add a parameter to
                # MelSorted to sort on load only for specific subrecords?
                if attr == u'regions':
                    if set(value).difference(set(curr_value)):
                        setattr_deep(patchCellBlock.cell, attr, value)
                        modified = True
                else:
                    if value != curr_value:
                        setattr_deep(patchCellBlock.cell, attr, value)
                        modified = True
            if modified:
                patchCellBlock.cell.setChanged()
                keep(patch_cell_fid)
            return modified
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        cellData, count = self.cellData, Counter()
        for cellBlock in self.patchFile.tops[b'CELL'].cellBlocks:
            cell_fid = cellBlock.cell.fid
            if cell_fid in cellData and handlePatchCellBlock(cellBlock):
                count[cell_fid[0]] += 1
        for worldBlock in self.patchFile.tops[b'WRLD'].worldBlocks:
            keepWorld = False
            for cellBlock in worldBlock.cellBlocks:
                cell_fid = cellBlock.cell.fid
                if cell_fid in cellData and handlePatchCellBlock(cellBlock):
                    count[cell_fid[0]] += 1
                    keepWorld = True
            if worldBlock.worldCellBlock:
                cell_fid = worldBlock.worldCellBlock.cell.fid
                if cell_fid in cellData and handlePatchCellBlock(
                        worldBlock.worldCellBlock):
                    count[cell_fid[0]] += 1
                    keepWorld = True
            if keepWorld:
                keep(worldBlock.world.fid)
        self.cellData.clear()
        self._patchLog(log, count)

    def _plog(self,log,count): # type 1 but for logMsg % sum(...)
        log(self.__class__.logMsg)
        for srcMod in load_order.get_ordered(count):
            log(u'* %s: %d' % (srcMod,count[srcMod]))

#------------------------------------------------------------------------------
class ImportGraphicsPatcher(APreserver):
    rec_attrs = bush.game.graphicsTypes
    _fid_rec_attrs = bush.game.graphicsFidTypes

    def _inner_loop(self, keep, records, top_mod_rec, type_count,
                    __attrgetters=attrgetter_cache):
        id_data = self.id_data
        for rfid, record in records:
            if rfid not in id_data: continue
            for attr, value in id_data[rfid].items():
                rec_attr = __attrgetters[attr](record)
                if isinstance(rec_attr, str) and isinstance(
                        value, str):
                    if rec_attr.lower() != value.lower():
                        break
                    continue
                elif attr in bush.game.graphicsModelAttrs:
                    try:
                        if rec_attr.modPath.lower() != value.modPath.lower():
                            break
                        continue
                    except: break  # assume they are not equal (ie they
                        # aren't __both__ NONE)
                if rec_attr != value: break
            else: continue
            for attr, value in id_data[rfid].items():
                setattr(record, attr, value)
            keep(rfid)
            type_count[top_mod_rec] += 1

#------------------------------------------------------------------------------
class ImportRacesPatcher(APreserver):
    rec_attrs = bush.game.import_races_attrs
    _multi_tag = True

    def _inner_loop(self, keep, records, top_mod_rec, type_count,
                    __attrgetters=attrgetter_cache):
        loop_setattr = setattr_deep if self._deep_attrs else setattr
        id_data = self.id_data
        for rfid, record in records:
            if rfid not in id_data: continue
            for attr, value in id_data[rfid].items():
                record_val = __attrgetters[attr](record)
                if attr in (u'eyes', u'hairs'):
                    if set(record_val) != set(value): break
                else:
                    if attr in (u'leftEye', u'rightEye') and not record_val:
                        deprint(u'Very odd race %s found - %s is None' % (
                            record.full, attr))
                    elif record_val != value: break
            else: continue
            for attr, value in id_data[rfid].items():
                loop_setattr(record, attr, value)
            keep(rfid)
            type_count[top_mod_rec] += 1
