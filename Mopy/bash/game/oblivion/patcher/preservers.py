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
from collections import Counter

from ._shared import cobl_main, ExSpecial
from .... import load_order
from ....bolt import deprint
from ....brec import null4
from ....parsers import _HandleAliases
from ....patcher import getPatchesPath
from ....patcher.base import ImportPatcher, ListPatcher

class ImportRoadsPatcher(ImportPatcher, ExSpecial):
    """Imports roads."""
    patcher_name = _(u'Import Roads')
    patcher_desc = _(u"Import roads from source mods.")
    autoKey = {u'Roads'}
    _config_key = u'RoadImporter'

    logMsg = u'\n=== ' + _(u'Worlds Patched')
    _read_sigs = (b'CELL', b'WRLD', b'ROAD')

    def __init__(self, p_name, p_file, p_sources):
        super(ImportRoadsPatcher, self).__init__(p_name, p_file, p_sources)
        self.world_road = {}

    def initData(self,progress):
        """Get cells from source files."""
        if not self.isActive: return
        self.loadFactory = self._patcher_read_fact()
        for srcMod in self.srcs:
            if srcMod not in self.patchFile.p_file_minfos: continue
            srcInfo = self.patchFile.p_file_minfos[srcMod]
            srcFile = self._mod_file_read(srcInfo)
            for worldBlock in srcFile.tops[b'WRLD'].worldBlocks:
                if worldBlock.road:
                    worldId = worldBlock.world.fid
                    road = worldBlock.road.getTypeCopy()
                    self.world_road[worldId] = road
        self.isActive = bool(self.world_road)

    def scanModFile(self, modFile, progress): # scanModFile3 ?
        """Add lists from modFile."""
        if b'WRLD' not in modFile.tops: return
        patchWorlds = self.patchFile.tops[b'WRLD']
        for worldBlock in modFile.tops[b'WRLD'].worldBlocks:
            if worldBlock.road:
                worldId = worldBlock.world.fid
                road = worldBlock.road.getTypeCopy()
                patchWorlds.setWorld(worldBlock.world)
                patchWorlds.id_worldBlocks[worldId].road = road

    def buildPatch(self,log,progress): # buildPatch3: one type
        """Adds merged lists to patchfile."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        worldsPatched = set()
        for worldBlock in self.patchFile.tops[b'WRLD'].worldBlocks:
            worldId = worldBlock.world.fid
            curRoad = worldBlock.road
            newRoad = self.world_road.get(worldId)
            if newRoad and (not curRoad or curRoad.points_p != newRoad.points_p
                or curRoad.connections_p != newRoad.connections_p
                ):
                worldBlock.road = newRoad
                keep(worldId)
                keep(newRoad.fid)
                worldsPatched.add((worldId[0], worldBlock.world.eid))
        self.world_road.clear()
        self._patchLog(log,worldsPatched)

    def _plog(self,log,worldsPatched):
        log(self.__class__.logMsg)
        for modWorld in sorted(worldsPatched):
            log(u'* %s: %s' % modWorld)

    @classmethod
    def gui_cls_vars(cls):
        cls_vars = super(ImportRoadsPatcher, cls).gui_cls_vars()
        return cls_vars.update({u'autoKey': cls.autoKey}) or cls_vars

#------------------------------------------------------------------------------
class _ExSpecialList(_HandleAliases, ListPatcher, ExSpecial):
    _csv_key = u'OVERRIDE'

    def __init__(self, p_name, p_file, p_sources):
        super(_ExSpecialList, self).__init__(p_file.pfile_aliases)
        ListPatcher.__init__(self, p_name, p_file, p_sources)
        self.id_info = {}

    @classmethod
    def gui_cls_vars(cls):
        cls_vars = super(_ExSpecialList, cls).gui_cls_vars()
        more = {u'canAutoItemCheck': False, u'_csv_key': cls._csv_key}
        return cls_vars.update(more) or cls_vars

class CoblExhaustionPatcher(_ExSpecialList):
    """Modifies most Greater power to work with Cobl's power exhaustion
    feature."""
    patcher_name = _(u'Cobl Exhaustion')
    patcher_desc = u'\n\n'.join(
        [_(u"Modify greater powers to use Cobl's Power Exhaustion feature."),
         _(u'Will only run if Cobl Main v1.66 (or higher) is active.')])
    _csv_key = u'Exhaust'
    _config_key = u'CoblExhaustion'
    _read_sigs = (b'SPEL',)

    def __init__(self, p_name, p_file, p_sources):
        super(CoblExhaustionPatcher, self).__init__(p_name, p_file, p_sources)
        self.isActive &= (cobl_main in p_file.loadSet and
            self.patchFile.p_file_minfos.getVersionFloat(cobl_main) > 1.65)
        self.id_exhaustion = self.id_info

    def _pLog(self, log, count):
        log.setHeader(u'= ' + self._patcher_name)
        log(u'* ' + _(u'Powers Tweaked') + u': %d' % sum(count.values()))
        for srcMod in load_order.get_ordered(count):
            log(u'  * %s: %d' % (srcMod, count[srcMod]))

    def _parse_line(self, csv_fields): # mod, objectIndex, time
        self.id_info[self._coerce_fid(csv_fields[0], csv_fields[1])] = int(
            csv_fields[3])

    def initData(self,progress):
        """Get names from source files."""
        if not self.isActive: return
        progress.setFull(len(self.srcs))
        for srcFile in self.srcs:
            try: self.read_csv(getPatchesPath(srcFile))
            except OSError: deprint(
                u'%s is no longer in patches set' % srcFile, traceback=True)
            progress.plus()

    def scanModFile(self,modFile,progress): # if b'SPEL' not in modFile.tops: return
        patchRecords = self.patchFile.tops[b'SPEL']
        for record in modFile.tops[b'SPEL'].getActiveRecords():
            if not record.spellType == 2: continue
            if record.fid in self.id_exhaustion:
                patchRecords.setRecord(record.getTypeCopy())

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Will write to log."""
        if not self.isActive: return
        count = Counter()
        exhaustId = (cobl_main, 0x05139B)
        keep = self.patchFile.getKeeper()
        for record in self.patchFile.tops[b'SPEL'].records:
            ##: Skips OBME records - rework to support them
            if record.obme_record_version is not None: continue
            #--Skip this one?
            rec_fid = record.fid
            duration = self.id_exhaustion.get(rec_fid, 0)
            if not (duration and record.spellType == 2): continue
            isExhausted = False ##: unused, was it supposed to be used?
            for effect in record.effects:
                if effect.effect_sig == b'SEFF' \
                        and effect.scriptEffect.script_fid == exhaustId:
                    duration = 0
                    break
            if not duration: continue
            #--Okay, do it
            record.full = u'+' + record.full
            record.spellType = 3 #--Lesser power
            effect = record.getDefault(u'effects')
            effect.effect_sig = b'SEFF'
            effect.duration = duration
            scriptEffect = record.getDefault(u'effects.scriptEffect')
            scriptEffect.full = u'Power Exhaustion'
            scriptEffect.script_fid = exhaustId
            scriptEffect.school = 2
            scriptEffect.visual = null4
            scriptEffect.flags.hostile = False
            effect.scriptEffect = scriptEffect
            record.effects.append(effect)
            keep(rec_fid)
            count[rec_fid[0]] += 1
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

    def _pLog(self, log, changed):
        log.setHeader(u'= ' + self._patcher_name)
        self._srcMods(log)
        log(u'\n=== ' + _(u'Morphable Factions'))
        for mod in load_order.get_ordered(changed):
            log(u'* %s: %d' % (mod, changed[mod]))

    def _parse_line(self, csv_fields):
        # type: # (list[str]) -> tuple[object] | None
        mod, objectIndex = csv_fields[0], csv_fields[1]
        morphName = csv_fields[4].strip()
        if not morphName:
            return None # caller unpacks -> TypeError (should not happen often)
        rankName = csv_fields[5].strip() or _(u'Member')
        self.id_info[self._coerce_fid(mod, objectIndex)] = morphName, rankName

    def __init__(self, p_name, p_file, p_sources):
        super(MorphFactionsPatcher, self).__init__(p_name, p_file, p_sources)
        # self.id_info #--Morphable factions keyed by fid
        self.isActive &= cobl_main in p_file.loadSet
        self.mFactLong = (cobl_main, 0x33FB)

    def initData(self,progress):
        """Get names from source files."""
        if not self.isActive: return
        for srcFile in self.srcs:
            try: self.read_csv(getPatchesPath(srcFile))
            except OSError: deprint(
                u'%s is no longer in patches set' % srcFile, traceback=True)
            progress.plus()

    def scanModFile(self, modFile, progress):
        """Scan modFile."""
        id_info = self.id_info
        patchBlock = self.patchFile.tops[b'FACT']
        if modFile.fileInfo.ci_key == cobl_main:
            record = modFile.tops[b'FACT'].getRecord(self.mFactLong)
            if record:
                patchBlock.setRecord(record.getTypeCopy())
        for record in modFile.tops[b'FACT'].getActiveRecords():
            if record.fid in id_info:
                patchBlock.setRecord(record.getTypeCopy())

    def buildPatch(self,log,progress):
        """Make changes to patchfile."""
        if not self.isActive: return
        mFactLong = self.mFactLong
        id_info = self.id_info
        modFile = self.patchFile
        keep = self.patchFile.getKeeper()
        changed = Counter()
        mFactable = []
        for record in modFile.tops[b'FACT'].getActiveRecords():
            rec_fid = record.fid
            if rec_fid not in id_info: continue
            if rec_fid == mFactLong: continue
            mFactable.append(rec_fid)
            #--Update record if it doesn't have an existing relation with
            # mFactLong
            if not any(mFactLong == relation.faction for relation in
                       record.relations):
                record.general_flags.hidden_from_pc = False
                relation = record.getDefault(u'relations')
                relation.faction = mFactLong
                relation.mod = 10
                record.relations.append(relation)
                mname,rankName = id_info[rec_fid]
                record.full = mname
                if not record.ranks:
                    record.ranks = [record.getDefault(u'ranks')]
                for rank in record.ranks:
                    if not rank.male_title: rank.male_title = rankName
                    if not rank.female_title: rank.female_title = rankName
                    if not rank.insignia_path:
                        rank.insignia_path = (
                                u'Menus\\Stats\\Cobl\\generic%02d.dds' %
                                # if rank_level was not present it will be None
                                (rank.rank_level or 0))
                keep(rec_fid)
                changed[rec_fid[0]] += 1
        #--MFact record
        record = modFile.tops[b'FACT'].getRecord(mFactLong)
        if record:
            relations = record.relations
            del relations[:]
            for faction in mFactable:
                relation = record.getDefault(u'relations')
                relation.faction = faction
                relation.mod = 10
                relations.append(relation)
            keep(record.fid)
        self._pLog(log, changed)
