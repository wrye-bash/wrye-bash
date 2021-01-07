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
import copy
import io
import os
import re

from collections import Counter, defaultdict
from .... import bush, load_order
from ....bolt import GPath, deprint
from ....brec import MreRecord, RecHeader, null4
from ....mod_files import ModFile, LoadFactory
from ....parsers import _HandleAliases
from ....patcher import getPatchesPath
from ....patcher.base import Patcher, Abstract_Patcher
from ....patcher.patchers.base import ListPatcher

__all__ = [u'CoblCatalogsPatcher', u'CoblExhaustionPatcher',
           u'MorphFactionsPatcher', u'SEWorldTestsPatcher']
_cobl_main = GPath(u'COBL Main.esm')

class _ExSpecial(Abstract_Patcher):
    """Those used to be subclasses of SpecialPatcher that did not make much
    sense as they did not use scan_more."""
    patcher_group = u'Special'
    patcher_order = 40

    @classmethod
    def gui_cls_vars(cls):
        """Class variables for gui patcher classes created dynamically."""
        return {u'patcher_type': cls, u'patcher_desc': cls.patcher_desc,
                u'patcher_name': cls.patcher_name,
                u'_config_key': cls._config_key}

class CoblCatalogsPatcher(Patcher, _ExSpecial):
    """Updates COBL alchemical catalogs."""
    patcher_name = _(u'Cobl Catalogs')
    patcher_desc = u'\n\n'.join(
        [_(u"Update COBL's catalogs of alchemical ingredients and effects."),
         _(u'Will only run if Cobl Main.esm is loaded.')])
    _config_key = u'AlchemicalCatalogs'
    _read_sigs = (b'INGR',)

    @classmethod
    def gui_cls_vars(cls):
        cls_vars = super(CoblCatalogsPatcher, cls).gui_cls_vars()
        return cls_vars.update({u'default_isEnabled': True}) or cls_vars

    def __init__(self, p_name, p_file):
        super(CoblCatalogsPatcher, self).__init__(p_name, p_file)
        self.isActive = (_cobl_main in p_file.loadSet)
        self.id_ingred = {}

    @property
    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (b'BOOK',) if self.isActive else ()

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch
        mod, but won't alter it."""
        id_ingred = self.id_ingred
        for record in modFile.tops[b'INGR'].getActiveRecords():
            if not record.full: continue #--Ingredient must have name!
            if record.obme_record_version is not None:
                continue ##: Skips OBME records - rework to support them
            effects = record.getEffects()
            if not (b'SEFF', 0) in effects:
                id_ingred[record.fid] = (record.eid, record.full, effects)

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Will write to log."""
        if not self.isActive: return
        #--Setup
        alt_names = copy.deepcopy(self.patchFile.getMgefName())
        attr_or_skill = u'(%s|%s)' % (_(u'Attribute'), _(u'Skill'))
        for mgef in alt_names:
            alt_names[mgef] = re.sub(attr_or_skill, u'', alt_names[mgef])
        actorEffects = bush.game.generic_av_effects
        actorNames = bush.game.actor_values
        keep = self.patchFile.getKeeper()
        #--Book generator
        def getBook(objectId,eid,full,value,iconPath,modelPath,modb_p):
            book = MreRecord.type_class[b'BOOK'](RecHeader(b'BOOK', 0, 0, 0, 0))
            book.longFids = True
            book.changed = True
            book.eid = eid
            book.full = full
            book.value = value
            book.weight = 0.2
            book.book_text = u'<div align="left"><font face=3 color=4444>'
            book.book_text += (_(u"Salan's Catalog of %s") + u'\r\n\r\n') % full
            book.iconPath = iconPath
            book.model = book.getDefault(u'model')
            book.model.modPath = modelPath
            book.model.modb_p = modb_p
            book.modb = book
            ##: In Cobl Main.esm, the books have a script attached
            # (<cobGenDevalueOS [SCPT:01001DDD]>). This currently gets rid of
            # that, should we keep it instead?
            # book.script = (_cobl_main, 0x001DDD)
            book.fid = (_cobl_main, objectId)
            keep(book.fid)
            self.patchFile.tops[b'BOOK'].setRecord(book)
            return book
        #--Ingredients Catalog
        id_ingred = self.id_ingred
        iconPath, modPath, modb_p = (u'Clutter\\IconBook9.dds',
                                     u'Clutter\\Books\\Octavo02.NIF',
                                     b'\x03>@A')
        for (num,objectId,full,value) in _ingred_alchem:
            book = getBook(objectId, u'cobCatAlchemIngreds%s' % num, full,
                           value, iconPath, modPath, modb_p)
            buff = io.StringIO(book.book_text)
            buff.seek(0, os.SEEK_END)
            buffWrite = buff.write
            for eid, full, effects in sorted(id_ingred.values(),
                                             key=lambda a: a[1].lower()):
                buffWrite(full + u'\r\n')
                for mgef, actorValue in effects[:num]:
                    effectName = alt_names[mgef]
                    if mgef in actorEffects:
                        effectName += actorNames[actorValue]
                    buffWrite(u'  ' + effectName + u'\r\n')
                buffWrite(u'\r\n')
            book.book_text = re.sub(u'\r\n', u'<br>\r\n', buff.getvalue())
        #--Get Ingredients by Effect
        effect_ingred = defaultdict(list)
        for _fid,(eid,full,effects) in id_ingred.iteritems():
            for index,(mgef,actorValue) in enumerate(effects):
                effectName = alt_names[mgef]
                if mgef in actorEffects: effectName += actorNames[actorValue]
                effect_ingred[effectName].append((index,full))
        #--Effect catalogs
        iconPath, modPath, modb_p = (u'Clutter\\IconBook7.dds',
                                     u'Clutter\\Books\\Octavo01.NIF',
                                     b'\x03>@A')
        for (num, objectId, full, value) in _effect_alchem:
            book = getBook(objectId, u'cobCatAlchemEffects%s' % num, full,
                           value, iconPath, modPath, modb_p)
            buff = io.StringIO(book.book_text)
            buff.seek(0, os.SEEK_END)
            buffWrite = buff.write
            for effectName in sorted(effect_ingred):
                effects = [indexFull for indexFull in
                           effect_ingred[effectName] if indexFull[0] < num]
                if effects:
                    buffWrite(effectName + u'\r\n')
                    for (index, full) in sorted(effects, key=lambda a: a[
                        1].lower()):
                        exSpace = u' ' if index == 0 else u''
                        buffWrite(u' %s%s %s\r\n' % (index + 1, exSpace, full))
                    buffWrite(u'\r\n')
            book.book_text = re.sub(u'\r\n', u'<br>\r\n', buff.getvalue())
        #--Log
        log.setHeader(u'= ' + self._patcher_name)
        log(u'* '+_(u'Ingredients Cataloged') + u': %d' % len(id_ingred))
        log(u'* '+_(u'Effects Cataloged') + u': %d' % len(effect_ingred))

#------------------------------------------------------------------------------
class _ExSpecialList(_HandleAliases, ListPatcher, _ExSpecial):

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
        self.isActive |= (_cobl_main in p_file.loadSet and
            self.patchFile.p_file_minfos.getVersionFloat(_cobl_main) > 1.65)
        self.id_exhaustion = self.id_info

    def _pLog(self, log, count):
        log.setHeader(u'= ' + self._patcher_name)
        log(u'* ' + _(u'Powers Tweaked') + u': %d' % sum(count.values()))
        for srcMod in load_order.get_ordered(count):
            log(u'  * %s: %d' % (srcMod, count[srcMod]))

    def _parse_line(self, csv_fields): # mod, objectIndex, time
        return csv_fields[0], csv_fields[1], int(csv_fields[3])

    def _update_info_dict(self, fields):
        self.id_info[self._coerce_fid(fields[0], fields[1])] = fields[2]

    def initData(self,progress):
        """Get names from source files."""
        if not self.isActive: return
        progress.setFull(len(self.srcs))
        for srcFile in self.srcs:
            try: self.readFromText(getPatchesPath(srcFile))
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
        exhaustId = (_cobl_main, 0x05139B)
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
                        and effect.scriptEffect.script == exhaustId:
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
            scriptEffect.script = exhaustId
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
        # type: # (list[unicode]) -> tuple[object] | None
        mod, objectIndex = csv_fields[0], csv_fields[1]
        morphName = csv_fields[4].strip()
        if not morphName:
            return None # caller unpacks -> TypeError (should not happen often)
        rankName = csv_fields[5].strip() or _(u'Member')
        return mod, objectIndex, morphName, rankName

    def _update_info_dict(self, fields):
        self.id_info[self._coerce_fid(fields[0], fields[1])] = fields[2:]

    def __init__(self, p_name, p_file, p_sources):
        super(MorphFactionsPatcher, self).__init__(p_name, p_file, p_sources)
        # self.id_info #--Morphable factions keyed by fid
        self.isActive &= _cobl_main in p_file.loadSet
        self.mFactLong = (_cobl_main, 0x33FB)

    def initData(self,progress):
        """Get names from source files."""
        if not self.isActive: return
        for srcFile in self.srcs:
            try: self.readFromText(getPatchesPath(srcFile))
            except OSError: deprint(
                u'%s is no longer in patches set' % srcFile, traceback=True)
            progress.plus()

    def scanModFile(self, modFile, progress):
        """Scan modFile."""
        id_info = self.id_info
        patchBlock = self.patchFile.tops[b'FACT']
        if modFile.fileInfo.name == _cobl_main:
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
            if mFactLong not in [relation.faction for relation in
                                 record.relations]:
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
                                rank.rank_level)
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

#------------------------------------------------------------------------------
_ob_path = GPath(bush.game.master_file)
class SEWorldTestsPatcher(_ExSpecial, Patcher):
    """Suspends Cyrodiil quests while in Shivering Isles."""
    patcher_name = _(u'SEWorld Tests')
    patcher_desc = _(u"Suspends Cyrodiil quests while in Shivering Isles. "
                     u"I.e. re-instates GetPlayerInSEWorld tests as "
                     u"necessary.")
    _config_key = u'SEWorldEnforcer'
    _read_sigs = (b'QUST',)

    @classmethod
    def gui_cls_vars(cls):
        cls_vars = super(SEWorldTestsPatcher, cls).gui_cls_vars()
        return cls_vars.update({u'default_isEnabled': True}) or cls_vars

    def __init__(self, p_name, p_file):
        super(SEWorldTestsPatcher, self).__init__(p_name, p_file)
        self.cyrodiilQuests = set()
        if _ob_path in p_file.loadSet:
            loadFactory = LoadFactory(False, by_sig=[b'QUST'])
            modInfo = self.patchFile.p_file_minfos[_ob_path]
            modFile = ModFile(modInfo,loadFactory)
            modFile.load(True)
            for record in modFile.tops[b'QUST'].getActiveRecords():
                for condition in record.conditions:
                    if condition.ifunc == 365 and condition.compValue == 0:
                        self.cyrodiilQuests.add(record.fid)
                        break
        self.isActive = bool(self.cyrodiilQuests)

    def scanModFile(self,modFile,progress):
        if modFile.fileInfo.name == _ob_path: return
        cyrodiilQuests = self.cyrodiilQuests
        patchBlock = self.patchFile.tops[b'QUST']
        for record in modFile.tops[b'QUST'].getActiveRecords():
            if record.fid not in cyrodiilQuests: continue
            for condition in record.conditions:
                if condition.ifunc == 365: break #--365: playerInSeWorld
            else:
                patchBlock.setRecord(record.getTypeCopy())

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Will write to log."""
        if not self.isActive: return
        cyrodiilQuests = self.cyrodiilQuests
        patchFile = self.patchFile
        keep = patchFile.getKeeper()
        patched = []
        for record in patchFile.tops[b'QUST'].getActiveRecords():
            rec_fid = record.fid
            if rec_fid not in cyrodiilQuests: continue
            for condition in record.conditions:
                if condition.ifunc == 365: break #--365: playerInSeWorld
            else:
                condition = record.getDefault(u'conditions')
                condition.ifunc = 365
                record.conditions.insert(0,condition)
                keep(rec_fid)
                patched.append(record.eid)
        log.setHeader(u'= ' + self._patcher_name)
        log(u'==='+_(u'Quests Patched') + u': %d' % (len(patched),))

# Alchemical Catalogs ---------------------------------------------------------
_ingred_alchem = (
    (1,0xCED,_(u'Alchemical Ingredients I'),250),
    (2,0xCEC,_(u'Alchemical Ingredients II'),500),
    (3,0xCEB,_(u'Alchemical Ingredients III'),1000),
    (4,0xCE7,_(u'Alchemical Ingredients IV'),2000),
)
_effect_alchem = (
    (1,0xCEA,_(u'Alchemical Effects I'),500),
    (2,0xCE9,_(u'Alchemical Effects II'),1000),
    (3,0xCE8,_(u'Alchemical Effects III'),2000),
    (4,0xCE6,_(u'Alchemical Effects IV'),4000),
)
