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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
import re
from collections import Counter
from operator import itemgetter

from ._shared import ExSpecial, cobl_main
from .... import load_order
from ....brec import FormId, null4
from ....patcher.base import CsvListPatcher, ImportPatcher, ListPatcher

class ImportRoadsPatcher(ImportPatcher, ExSpecial):
    """Imports roads."""
    patcher_name = _(u'Import Roads')
    patcher_desc = _(u"Import roads from source mods.")
    patcher_tags = {'Roads'}
    _config_key = u'RoadImporter'

    logMsg = '\n=== ' + _('Worlds Patched')
    _read_sigs = (b'CELL', b'WRLD', b'ROAD') ##: do we need cell??

    def __init__(self, p_name, p_file, p_sources):
        super(ImportRoadsPatcher, self).__init__(p_name, p_file, p_sources)
        self.world_road = {}

    def _update_patcher_factories(self, p_file):
        """We don't scan masters (?)"""
        return super(ImportPatcher, self)._update_patcher_factories(p_file)

    def initData(self,progress):
        """Get roads from source files."""
        if not self.isActive: return
        for srcMod in self.srcs:
            srcFile = self.patchFile.get_loaded_mod(srcMod)
            for worldId, worldBlock in srcFile.tops[
                    b'WRLD'].iter_present_records():
                if worldBlock.road:
                    self.world_road[worldId] = worldBlock.road.getTypeCopy()
        self.isActive = bool(self.world_road)

    def scanModFile(self, modFile, progress, scan_sigs=None):
        super().scanModFile(modFile, progress, [b'WRLD'])

    def _add_to_patch(self, rid, worldBlock, top_sig):
        """We deal with a worldBlock - do the update here."""
        if worldBlock.road:
            patch_world_block = self.patchFile.tops[b'WRLD'].setRecord(
                worldBlock.master_record)
            patch_world_block.road = worldBlock.road.getTypeCopy()

    def buildPatch(self,log,progress): # buildPatch3: one type
        """Adds merged lists to patchfile."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        worldsPatched = set()
        for worldId, worldBlock in self.patchFile.tops[
                b'WRLD'].id_records.items():
            curRoad = worldBlock.road
            newRoad = self.world_road.get(worldId)
            if newRoad and (not curRoad or curRoad.points_p != newRoad.points_p
                    or curRoad.connections_p != newRoad.connections_p):
                if keep(worldId, worldBlock) and keep(newRoad.fid, newRoad):
                    worldBlock.road = newRoad
                    worldsPatched.add(
                        (worldId.mod_fn, worldBlock.master_record.eid))
        self.world_road.clear()
        self._patchLog(log,worldsPatched)

    def _plog(self,log,worldsPatched):
        log(self.__class__.logMsg)
        for modWorld in sorted(worldsPatched):
            log(u'* %s: %s' % modWorld)

#------------------------------------------------------------------------------
class _ExSpecialList(CsvListPatcher, ExSpecial):
    _csv_key = u'OVERRIDE'

    def __init__(self, p_name, p_file, p_sources):
        super(_ExSpecialList, self).__init__(p_file.pfile_aliases)
        ListPatcher.__init__(self, p_name, p_file, p_sources)

    @property
    def _keep_ids(self):
        return self.id_stored_data[b'FACT']

    @classmethod
    def gui_cls_vars(cls):
        cls_vars = super(_ExSpecialList, cls).gui_cls_vars()
        return cls_vars.update({'canAutoItemCheck': False}) or cls_vars

class CoblExhaustionPatcher(_ExSpecialList):
    """Modifies most Greater powers to work with Cobl's power exhaustion
    feature."""
    patcher_name = _(u'Cobl Exhaustion')
    patcher_desc = u'\n\n'.join(
        [_(u"Modify greater powers to use Cobl's Power Exhaustion feature."),
         _(u'Will only run if Cobl Main v1.66 (or higher) is active.')])
    _csv_key = u'Exhaust'
    _config_key = u'CoblExhaustion'
    _read_sigs = (b'SPEL',)
    _key2_getter = itemgetter(0, 1)
    _parser_sigs = [b'FACT']
    _exhaust_fid = FormId.from_tuple((cobl_main, 0x05139B))

    def _process_sources(self, p_sources, p_file):
        if cobl_main in p_file.load_dict:
            vers = self.patchFile.all_plugins[cobl_main].get_version()
            maVersion = re.search(r'(\d+\.?\d*)', vers)
            if maVersion and float(maVersion.group(1)) > 1.65:
                return super()._process_sources(p_sources, p_file)
        return False # COBL not loaded or its version is < 1.65

    def _pLog(self, log, count):
        log.setHeader(u'= ' + self._patcher_name)
        log('* ' + _('Powers Tweaked: %(total_changed)d') % {
            'total_changed': sum(count.values())})
        for srcMod in load_order.get_ordered(count):
            log(f'  * {srcMod}: {count[srcMod]:d}')

    def _update_from_csv(self, top_grup_sig, csv_fields, index_dict=None):
        return int(csv_fields[3])

    def _add_to_patch(self, rid, record, top_sig):
        return record.spell_type == 2

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Will write to log."""
        if not self.isActive: return
        count = Counter()
        keep = self.patchFile.getKeeper()
        id_info = self.id_stored_data[b'FACT']
        for rid, record in self.patchFile.tops[b'SPEL'].id_records.items():
            ##: Skips OBME records - rework to support them
            if (record.obme_record_version is not None or
                    record.spell_type != 2):
                continue
            #--Skip this one?
            if not (duration := id_info.get(rid)): continue
            isExhausted = False ##: unused, was it supposed to be used?
            if any(ef.effect_sig == b'SEFF' and
                   ef.scriptEffect.script_fid == self._exhaust_fid
                   for ef in record.effects):
                continue
            #--Okay, do it
            record.full = f'+{record.full}'
            record.spell_type = 3 #--Lesser power
            effect = record.getDefault(u'effects')
            effect.effect_sig = b'SEFF'
            effect.duration = duration
            scriptEffect = record.getDefault(u'effects.scriptEffect')
            scriptEffect.full = u'Power Exhaustion'
            scriptEffect.script_fid = self._exhaust_fid
            scriptEffect.school = 2
            scriptEffect.visual = null4
            scriptEffect.flags.hostile = False
            effect.scriptEffect = scriptEffect
            record.effects.append(effect)
            keep(rid, record)
            count[rid.mod_fn] += 1
        #--Log
        self._pLog(log, count)

#------------------------------------------------------------------------------
class MorphFactionsPatcher(_ExSpecialList):
    """Mark factions that player can acquire while morphing."""
    patcher_name = _(u'Morph Factions')
    patcher_desc = u'\n\n'.join(
        [_(u"Mark factions that player can acquire while morphing."),
         _(u"Requires Cobl 1.28 and Wrye Morph or similar.")])
    srcsHeader = u'=== ' + _(u'Source Mods/Files')
    _csv_key = u'MFact'
    _config_key = u'MFactMarker'
    _read_sigs = (b'FACT',)
    _key2_getter = itemgetter(0, 1)
    _parser_sigs = [b'FACT']

    def _pLog(self, log, changes_dict):
        log.setHeader(u'= ' + self._patcher_name)
        self._log_srcs(log)
        log(u'\n=== ' + _(u'Morphable Factions'))
        for mod in load_order.get_ordered(changes_dict):
            log(f'* {mod}: {changes_dict[mod]:d}')

    def _update_from_csv(self, top_grup_sig, csv_fields, index_dict=None):
        # type: # (list[str]) -> tuple[object] | None
        morphName = csv_fields[4].strip()
        if not morphName: raise ValueError # exit _parse_line
        rankName = csv_fields[5].strip() or _(u'Member')
        return morphName, rankName

    def __init__(self, p_name, p_file, p_sources):
        super(MorphFactionsPatcher, self).__init__(p_name, p_file, p_sources)
        # self.id_info #--Morphable factions keyed by fid
        self.mFactLong = FormId.from_tuple((cobl_main, 0x33FB))

    def _process_sources(self, p_sources, p_file):
        return cobl_main in p_file.load_dict and super()._process_sources(
            p_sources, p_file)

    def scanModFile(self, modFile, progress, scan_sigs=None):
        """Scan modFile."""
        if modFile.fileInfo.fn_key == cobl_main:
            record = modFile.tops[b'FACT'].id_records.get(self.mFactLong)
            if record:
                self.patchFile.tops[b'FACT'].setRecord(record)
        super().scanModFile(modFile, progress, scan_sigs)

    def buildPatch(self,log,progress):
        """Make changes to patchfile."""
        if not self.isActive: return
        mFactLong = self.mFactLong
        id_info = self.id_stored_data[b'FACT']
        keep = self.patchFile.getKeeper()
        changes_counts = Counter()
        mFactable = []
        for rid, record in self.patchFile.tops[b'FACT'].id_records.items():
            if rid not in id_info: continue
            if rid == mFactLong: continue
            mFactable.append(rid)
            #--Update record if it doesn't have an existing relation with
            # mFactLong
            if not any(mFactLong == relation.faction for relation in
                       record.relations):
                record.fact_flags.hidden_from_pc = False
                relation = record.getDefault(u'relations')
                relation.faction = mFactLong
                relation.mod = 10
                record.relations.append(relation)
                mname, rankName = id_info[rid]
                record.full = mname
                if not record.ranks:
                    record.ranks = [record.getDefault(u'ranks')]
                for rank in record.ranks:
                    if rank.rank_level is None: rank.rank_level = 0
                    if not rank.male_title: rank.male_title = rankName
                    if not rank.female_title: rank.female_title = rankName
                    if not rank.insignia_path:
                        # if rank_level was not present it will be None
                        dds_ = f'generic{rank.rank_level or 0:02d}.dds'
                        rank.insignia_path = rf'Menus\Stats\Cobl\{dds_}'
                keep(rid, record)
                changes_counts[rid.mod_fn] += 1
        #--MFact record
        record = self.patchFile.tops[b'FACT'].id_records.get(mFactLong)
        if record:
            relations = record.relations
            del relations[:]
            for faction in mFactable:
                relation = record.getDefault(u'relations')
                relation.faction = faction
                relation.mod = 10
                relations.append(relation)
            keep(mFactLong, record)
        self._pLog(log, changes_counts)
