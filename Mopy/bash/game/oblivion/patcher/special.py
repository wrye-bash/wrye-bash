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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
import os
import re
from collections import Counter, defaultdict
from .... import bush, load_order
from ....bolt import GPath, sio, SubProgress, CsvReader, deprint
from ....brec import MreRecord, RecordHeader, null4
from ....exception import StateError
from ....mod_files import ModFile, LoadFactory
from ....patcher import getPatchesPath
from ....patcher.base import Patcher, CBash_Patcher, Abstract_Patcher, \
    AListPatcher
from ....patcher.patchers.base import ListPatcher, CBash_ListPatcher

__all__ = ['AlchemicalCatalogs', 'CBash_AlchemicalCatalogs', 'CoblExhaustion',
           'MFactMarker', 'CBash_MFactMarker', 'CBash_CoblExhaustion',
           'SEWorldEnforcer', 'CBash_SEWorldEnforcer']
_cobl_main = GPath(u'COBL Main.esm')

# Util Functions --------------------------------------------------------------
def _PrintFormID(fid):
    # PBash short Fid
    if isinstance(fid, (int, long)): # PY3: just int here
        fid = u'%08X' % fid
    # PBash long FId
    elif isinstance(fid, tuple):
        fid =  u'(%s, %06X)' % (fid[0], fid[1])
    # CBash / other(error)
    else:
        fid = repr(fid)
    print fid.encode('utf-8')

class _ExSpecial(Abstract_Patcher):
    """Those used to be subclasses of SpecialPatcher that did not make much
    sense as they did not use scan_more."""
    group = _(u'Special')
    scanOrder = 40
    editOrder = 40

    @classmethod
    def gui_cls_vars(cls):
        """Class variables for gui patcher classes created dynamically."""
        return {u'patcher_type': cls, u'_patcher_txt': cls.patcher_text,
                u'patcher_name': cls.patcher_name}

class _AAlchemicalCatalogs(_ExSpecial):
    """Updates COBL alchemical catalogs."""
    patcher_name = _(u'Cobl Catalogs')
    patcher_text = u'\n\n'.join(
        [_(u"Update COBL's catalogs of alchemical ingredients and effects."),
         _(u'Will only run if Cobl Main.esm is loaded.')])
    _read_write_records = ('INGR',)

    @classmethod
    def gui_cls_vars(cls):
        cls_vars = super(_AAlchemicalCatalogs, cls).gui_cls_vars()
        return cls_vars.update({u'default_isEnabled': True}) or cls_vars

class AlchemicalCatalogs(_AAlchemicalCatalogs,Patcher):

    def __init__(self, p_name, p_file):
        super(AlchemicalCatalogs, self).__init__(p_name, p_file)
        self.isActive = (_cobl_main in p_file.loadSet)
        self.id_ingred = {}

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('BOOK',) if self.isActive else ()

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch
        mod, but won't alter it."""
        id_ingred = self.id_ingred
        mapper = modFile.getLongMapper()
        for record in modFile.INGR.getActiveRecords():
            if not record.full: continue #--Ingredient must have name!
            effects = record.getEffects()
            if not ('SEFF',0) in effects:
                id_ingred[mapper(record.fid)] = (
                    record.eid, record.full, effects)

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Will write to log."""
        if not self.isActive: return
        #--Setup
        mgef_name = self.patchFile.getMgefName()
        for mgef in mgef_name:
            mgef_name[mgef] = re.sub(_(u'(Attribute|Skill)'), u'',
                                     mgef_name[mgef])
        actorEffects = bush.game.generic_av_effects
        actorNames = bush.game.actor_values
        keep = self.patchFile.getKeeper()
        #--Book generatator
        def getBook(objectId,eid,full,value,iconPath,modelPath,modb_p):
            book = MreRecord.type_class['BOOK'](
                RecordHeader('BOOK', 0, 0, 0, 0))
            book.longFids = True
            book.changed = True
            book.eid = eid
            book.full = full
            book.value = value
            book.weight = 0.2
            book.fid = keep((GPath(u'Cobl Main.esm'),objectId))
            book.text = u'<div align="left"><font face=3 color=4444>'
            book.text += _(u"Salan's Catalog of ")+u'%s\r\n\r\n' % full
            book.iconPath = iconPath
            book.model = book.getDefault('model')
            book.model.modPath = modelPath
            book.model.modb_p = modb_p
            book.modb = book
            self.patchFile.BOOK.setRecord(book)
            return book
        #--Ingredients Catalog
        id_ingred = self.id_ingred
        iconPath, modPath, modb_p = (u'Clutter\\IconBook9.dds',
                                     u'Clutter\\Books\\Octavo02.NIF','\x03>@A')
        for (num,objectId,full,value) in _ingred_alchem:
            book = getBook(objectId, u'cobCatAlchemIngreds%s' % num, full,
                           value, iconPath, modPath, modb_p)
            with sio(book.text) as buff:
                buff.seek(0,os.SEEK_END)
                buffWrite = buff.write
                for eid, full, effects in sorted(id_ingred.values(),
                                                 key=lambda a: a[1].lower()):
                    buffWrite(full+u'\r\n')
                    for mgef,actorValue in effects[:num]:
                        effectName = mgef_name[mgef]
                        if mgef in actorEffects:
                            effectName += actorNames[actorValue]
                        buffWrite(u'  '+effectName+u'\r\n')
                    buffWrite(u'\r\n')
                book.text = re.sub(u'\r\n',u'<br>\r\n',buff.getvalue())
        #--Get Ingredients by Effect
        effect_ingred = defaultdict(list)
        for fid,(eid,full,effects) in id_ingred.iteritems():
            for index,(mgef,actorValue) in enumerate(effects):
                effectName = mgef_name[mgef]
                if mgef in actorEffects: effectName += actorNames[actorValue]
                effect_ingred[effectName].append((index,full))
        #--Effect catalogs
        iconPath, modPath, modb_p = (u'Clutter\\IconBook7.dds',
                                     u'Clutter\\Books\\Octavo01.NIF','\x03>@A')
        for (num, objectId, full, value) in _effect_alchem:
            book = getBook(objectId, u'cobCatAlchemEffects%s' % num, full,
                           value, iconPath, modPath, modb_p)
            with sio(book.text) as buff:
                buff.seek(0,os.SEEK_END)
                buffWrite = buff.write
                for effectName in sorted(effect_ingred.keys()):
                    effects = [indexFull for indexFull in
                               effect_ingred[effectName] if indexFull[0] < num]
                    if effects:
                        buffWrite(effectName + u'\r\n')
                        for (index, full) in sorted(effects, key=lambda a: a[
                            1].lower()):
                            exSpace = u' ' if index == 0 else u''
                            buffWrite(u' %s%s %s\r\n'%(index + 1,exSpace,full))
                        buffWrite(u'\r\n')
                book.text = re.sub(u'\r\n',u'<br>\r\n',buff.getvalue())
        #--Log
        log.setHeader(u'= ' + self._patcher_name)
        log(u'* '+_(u'Ingredients Cataloged') + u': %d' % len(id_ingred))
        log(u'* '+_(u'Effects Cataloged') + u': %d' % len(effect_ingred))

class CBash_AlchemicalCatalogs(_AAlchemicalCatalogs,CBash_Patcher):
    allowUnloaded = False # avoid the srcs check in CBash_Patcher.initData

    def __init__(self, p_name, p_file):
        super(CBash_AlchemicalCatalogs, self).__init__(p_name, p_file)
        self.isActive = _cobl_main in p_file.loadSet
        if not self.isActive: return
        p_file.indexMGEFs = True
        self.id_ingred = {}
        self.effect_ingred = defaultdict(list)
        from ....cint import MGEFCode
        self.SEFF = MGEFCode('SEFF')
        self.DebugPrintOnce = 0

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.full:
            SEFF = self.SEFF
            for effect in record.effects:
                if effect.name == SEFF:
                    return
            self.id_ingred[record.fid] = (
                record.eid, record.full, record.effects_list)

    def finishPatch(self,patchFile,progress):
        """Edits the bashed patch file directly."""
        subProgress = SubProgress(progress)
        subProgress.setFull(len(_effect_alchem) + len(_ingred_alchem))
        pstate = 0
        #--Setup
        try:
            coblMod = patchFile.Current.LookupModFile(u'Cobl Main.esm')
        except KeyError as error:
            print u"CBash_AlchemicalCatalogs:finishPatch"
            print error[0]
            return
        from ....cint import FormID
        mgef_name = patchFile.mgef_name.copy()
        for mgef in mgef_name:
            mgef_name[mgef] = re.sub(_(u'(Attribute|Skill)'), u'',
                                     mgef_name[mgef])
        actorEffects = bush.game.generic_av_effects
        actorNames = bush.game.actor_values
        #--Book generator
        def getBook(patchFile, objectId):
            book = coblMod.LookupRecord(
                FormID(GPath(u'Cobl Main.esm'), objectId))
            # There have been reports of this patcher failing, hence the
            # sanity checks
            if book:
                if book.recType != 'BOOK':
                    _PrintFormID(fid)
                    print patchFile.Current.Debug_DumpModFiles()
                    print book
                    raise StateError(u"Cobl Catalogs: Unable to lookup book"
                                     u" record in Cobl Main.esm!")
                book = book.CopyAsOverride(self.patchFile)
                if not book:
                    _PrintFormID(fid)
                    print patchFile.Current.Debug_DumpModFiles()
                    print book
                    book = coblMod.LookupRecord(
                        FormID(GPath(u'Cobl Main.esm'), objectId))
                    print book
                    print book.text
                    print
                    raise StateError(u"Cobl Catalogs: Unable to create book!")
            return book
        #--Ingredients Catalog
        id_ingred = self.id_ingred
        for (num, objectId, full, value) in _ingred_alchem:
            subProgress(pstate, _(u'Cataloging Ingredients...')+u'\n%s' % full)
            pstate += 1
            book = getBook(patchFile, objectId)
            if not book: continue
            with sio() as buff:
                buff.write(u'<div align="left"><font face=3 color=4444>' + _(
                    u"Salan's Catalog of ") + u"%s\r\n\r\n" % full)
                for eid, full, effects_list in sorted(
                        id_ingred.values(),key=lambda a: a[1].lower()):
                    buff.write(full+u'\r\n')
                    for effect in effects_list[:num]:
                        mgef = effect[0] #name field
                        try:
                            effectName = mgef_name[mgef]
                        except KeyError:
                            if not self.DebugPrintOnce:
                                self.DebugPrintOnce = 1
                                print patchFile.Current.Debug_DumpModFiles()
                                print
                                print u'mgef_name:', mgef_name
                                print
                                print u'mgef:', mgef
                                print
                                if mgef in bush.game.mgef_name:
                                    print u'mgef found in constants.mgef_name'
                                else:
                                    print u'mgef not found in constants.mgef_name'
                            if mgef in bush.game.mgef_name:
                                effectName = re.sub(_(u'(Attribute|Skill)'),
                                                    u'', bush.game.mgef_name[mgef])
                            else:
                                effectName = u'Unknown Effect'
                        if mgef in actorEffects: effectName += actorNames[
                            effect[5]]  # actorValue field
                        buff.write(u'  '+effectName+u'\r\n')
                    buff.write(u'\r\n')
                book.text = re.sub(u'\r\n',u'<br>\r\n',buff.getvalue())
        #--Get Ingredients by Effect
        effect_ingred = self.effect_ingred = defaultdict(list)
        for fid,(eid,full,effects_list) in id_ingred.iteritems():
            for index,effect in enumerate(effects_list):
                mgef, actorValue = effect[0], effect[5]
                try:
                    effectName = mgef_name[mgef]
                except KeyError:
                    if not self.DebugPrintOnce:
                        self.DebugPrintOnce = 1
                        print patchFile.Current.Debug_DumpModFiles()
                        print
                        print u'mgef_name:', mgef_name
                        print
                        print u'mgef:', mgef
                        print
                        if mgef in bush.game.mgef_name:
                            print u'mgef found in constants.mgef_name'
                        else:
                            print u'mgef not found in constants.mgef_name'
                    if mgef in bush.game.mgef_name:
                        effectName = re.sub(_(u'(Attribute|Skill)'), u'',
                                            bush.game.mgef_name[mgef])
                    else:
                        effectName = u'Unknown Effect'
                if mgef in actorEffects: effectName += actorNames[actorValue]
                effect_ingred[effectName].append((index, full))
        #--Effect catalogs
        for (num, objectId, full, value) in _effect_alchem:
            subProgress(pstate, _(u'Cataloging Effects...')+u'\n%s' % full)
            book = getBook(patchFile,objectId)
            with sio() as buff:
                buff.write(u'<div align="left"><font face=3 color=4444>' + _(
                    u"Salan's Catalog of ") + u"%s\r\n\r\n" % full)
                for effectName in sorted(effect_ingred.keys()):
                    effects = [indexFull for indexFull in
                               effect_ingred[effectName] if indexFull[0] < num]
                    if effects:
                        buff.write(effectName+u'\r\n')
                        for (index, full) in sorted(effects, key=lambda a: a[
                            1].lower()):
                            exSpace = u' ' if index == 0 else u''
                            buff.write(
                                u' %s%s %s\r\n' % (index + 1, exSpace, full))
                        buff.write(u'\r\n')
                book.text = re.sub(u'\r\n',u'<br>\r\n',buff.getvalue())
            pstate += 1

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        id_ingred = self.id_ingred
        effect_ingred = self.effect_ingred
        log.setHeader(u'= ' + self._patcher_name)
        log(u'* '+_(u'Ingredients Cataloged') + u': %d' % len(id_ingred))
        log(u'* '+_(u'Effects Cataloged') + u': %d' % len(effect_ingred))

#------------------------------------------------------------------------------
class _ExSpecialList(_ExSpecial, AListPatcher):

    @classmethod
    def gui_cls_vars(cls):
        cls_vars = super(_ExSpecialList, cls).gui_cls_vars()
        more = {u'canAutoItemCheck': False, u'autoKey': cls.autoKey}
        return cls_vars.update(more) or cls_vars

class _DefaultDictLog(CBash_ListPatcher):
    """Patchers that log [mod -> record count] """

    def buildPatchLog(self, log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        self._pLog(log, self.mod_count)
        self.mod_count = Counter()

class _ACoblExhaustion(_ExSpecialList):
    """Modifies most Greater power to work with Cobl's power exhaustion
    feature."""
    patcher_name = _(u'Cobl Exhaustion')
    patcher_text = u'\n\n'.join(
        [_(u"Modify greater powers to use Cobl's Power Exhaustion feature."),
         _(u'Will only run if Cobl Main v1.66 (or higher) is active.')])
    autoKey = {u'Exhaust'}
    _read_write_records = ('SPEL',)

    def __init__(self, p_name, p_file, p_sources):
        super(_ACoblExhaustion, self).__init__(p_name, p_file, p_sources)
        self.isActive |= (_cobl_main in p_file.loadSet and
            self.patchFile.p_file_minfos.getVersionFloat(_cobl_main) > 1.65)
        self.id_exhaustion = {}

    def _pLog(self, log, count):
        log.setHeader(u'= ' + self._patcher_name)
        log(u'* ' + _(u'Powers Tweaked') + u': %d' % sum(count.values()))
        for srcMod in load_order.get_ordered(count.keys()):
            log(u'  * %s: %d' % (srcMod.s, count[srcMod]))

    def readFromText(self, textPath):
        """Imports type_id_name from specified text file."""
        aliases = self.patchFile.aliases
        id_exhaustion = self.id_exhaustion
        textPath = GPath(textPath)
        with CsvReader(textPath) as ins:
            for fields in ins:
                try:
                    if fields[1][:2] != u'0x': # may raise IndexError
                        continue
                    mod, objectIndex, eid, time = fields[:4] # may raise VE
                    mod = GPath(mod)
                    longid = (aliases.get(mod, mod), int(objectIndex[2:], 16))
                    id_exhaustion[longid] = int(time)
                except (IndexError, ValueError):
                    pass #ValueError: Either we couldn't unpack or int() failed

class CoblExhaustion(_ACoblExhaustion,ListPatcher):

    def initData(self,progress):
        """Get names from source files."""
        if not self.isActive: return
        progress.setFull(len(self.srcs))
        for srcFile in self.srcs:
            try: self.readFromText(getPatchesPath(srcFile))
            except OSError: deprint(
                u'%s is no longer in patches set' % srcFile, traceback=True)
            progress.plus()

    def scanModFile(self,modFile,progress):
        mapper = modFile.getLongMapper()
        patchRecords = self.patchFile.SPEL
        for record in modFile.SPEL.getActiveRecords():
            if not record.spellType == 2: continue
            record = record.getTypeCopy(mapper)
            if record.fid in self.id_exhaustion:
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Will write to log."""
        if not self.isActive: return
        count = Counter()
        exhaustId = (_cobl_main, 0x05139B)
        keep = self.patchFile.getKeeper()
        for record in self.patchFile.SPEL.records:
            #--Skip this one?
            duration = self.id_exhaustion.get(record.fid,0)
            if not (duration and record.spellType == 2): continue
            isExhausted = False
            for effect in record.effects:
                if effect.name == 'SEFF' and effect.scriptEffect.script == \
                        exhaustId:
                    duration = 0
                    break
            if not duration: continue
            #--Okay, do it
            record.full = '+'+record.full
            record.spellType = 3 #--Lesser power
            effect = record.getDefault('effects')
            effect.name = 'SEFF'
            effect.duration = duration
            scriptEffect = record.getDefault('effects.scriptEffect')
            scriptEffect.full = u"Power Exhaustion"
            scriptEffect.script = exhaustId
            scriptEffect.school = 2
            scriptEffect.visual = null4
            scriptEffect.flags.hostile = False
            effect.scriptEffect = scriptEffect
            record.effects.append(effect)
            keep(record.fid)
            count[record.fid[0]] += 1
        #--Log
        self._pLog(log, count)

class CBash_CoblExhaustion(_ACoblExhaustion, _DefaultDictLog):

    def __init__(self, *args, **kwargs):
        super(CBash_CoblExhaustion, self).__init__(*args, **kwargs)
        from ....cint import MGEFCode, FormID
        self.SEFF = MGEFCode('SEFF')
        self._null_mgef = MGEFCode(None,None)
        self.exhaustionId = FormID(_cobl_main, 0x05139B)

    def initData(self, progress):
        if not self.isActive: return
        for top_group_sig in self.getTypes():
            self.patchFile.group_patchers[top_group_sig].append(self)
        progress.setFull(len(self.srcs))
        for srcFile in self.srcs:
            try: self.readFromText(getPatchesPath(srcFile))
            except OSError: deprint(
                u'%s is no longer in patches set' % srcFile, traceback=True)
            progress.plus()
        from ....cint import FormID
        self.id_exhaustion = {FormID(*k): v for k, v in
                              self.id_exhaustion.iteritems()}

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.IsPower:
            #--Skip this one?
            duration = self.id_exhaustion.get(record.fid,0)
            if not duration: return
            for effect in record.effects:
                if effect.name == self.SEFF and effect.script == \
                        self.exhaustionId:
                    return
            #--Okay, do it
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.full = u'+' + override.full
                override.IsLesserPower = True
                effect = override.create_effect()
                effect.name = self.SEFF
                effect.duration = duration
                effect.full = u'Power Exhaustion'
                effect.script = self.exhaustionId
                effect.IsDestruction = True
                effect.visual = self._null_mgef
                effect.IsHostile = False
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _AMFactMarker(_ExSpecialList):
    """Mark factions that player can acquire while morphing."""
    patcher_name = _(u'Morph Factions')
    patcher_text = u'\n\n'.join(
        [_(u"Mark factions that player can acquire while morphing."),
         _(u"Requires Cobl 1.28 and Wrye Morph or similar.")])
    srcsHeader = u'=== ' + _(u'Source Mods/Files')
    autoKey = {u'MFact'}
    _read_write_records = ('FACT',)

    def _pLog(self, log, changed):
        log.setHeader(u'= ' + self._patcher_name)
        self._srcMods(log)
        log(u'\n=== ' + _(u'Morphable Factions'))
        for mod in load_order.get_ordered(changed):
            log(u'* %s: %d' % (mod.s, changed[mod]))

    def readFromText(self, textPath):
        """Imports id_info from specified text file."""
        aliases = self.patchFile.aliases
        id_info = self.id_info
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 6 or fields[1][:2] != u'0x':
                    continue
                mod, objectIndex = fields[:2]
                mod = GPath(mod)
                longid = (aliases.get(mod, mod), int(objectIndex, 0))
                morphName = fields[4].strip()
                rankName = fields[5].strip()
                if not morphName: continue
                if not rankName: rankName = _(u'Member')
                id_info[longid] = (morphName, rankName)

class MFactMarker(_AMFactMarker,ListPatcher):

    def __init__(self, p_name, p_file, p_sources):
        super(MFactMarker, self).__init__(p_name, p_file, p_sources)
        self.id_info = {} #--Morphable factions keyed by fid
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
        mapper = modFile.getLongMapper()
        patchBlock = self.patchFile.FACT
        if modFile.fileInfo.name == _cobl_main:
            modFile.convertToLongFids(('FACT',))
            record = modFile.FACT.getRecord(self.mFactLong)
            if record:
                patchBlock.setRecord(record.getTypeCopy())
        for record in modFile.FACT.getActiveRecords():
            fid = record.fid
            if not record.longFids: fid = mapper(fid)
            if fid in id_info:
                patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress):
        """Make changes to patchfile."""
        if not self.isActive: return
        mFactLong = self.mFactLong
        id_info = self.id_info
        modFile = self.patchFile
        keep = self.patchFile.getKeeper()
        changed = Counter()
        mFactable = []
        for record in modFile.FACT.getActiveRecords():
            if record.fid not in id_info: continue
            if record.fid == mFactLong: continue
            mFactable.append(record.fid)
            #--Update record if it doesn't have an existing relation with
            # mFactLong
            if mFactLong not in [relation.faction for relation in
                                 record.relations]:
                record.flags.hiddenFromPC = False
                relation = record.getDefault('relations')
                relation.faction = mFactLong
                relation.mod = 10
                record.relations.append(relation)
                mname,rankName = id_info[record.fid]
                record.full = mname
                if not record.ranks:
                    record.ranks = [record.getDefault('ranks')]
                for rank in record.ranks:
                    if not rank.male: rank.male = rankName
                    if not rank.female: rank.female = rank.male
                    if not rank.insigniaPath:
                        rank.insigniaPath = \
                            u'Menus\\Stats\\Cobl\\generic%02d.dds' % rank.rank
                keep(record.fid)
                changed[record.fid[0]] += 1
        #--MFact record
        record = modFile.FACT.getRecord(mFactLong)
        if record:
            relations = record.relations
            del relations[:]
            for faction in mFactable:
                relation = record.getDefault('relations')
                relation.faction = faction
                relation.mod = 10
                relations.append(relation)
            keep(record.fid)
        self._pLog(log, changed)

class CBash_MFactMarker(_AMFactMarker, _DefaultDictLog):

    def __init__(self, p_name, p_file, p_sources):
        super(CBash_MFactMarker, self).__init__(p_name, p_file, p_sources)
        self.isActive = _cobl_main in p_file.loadSet and \
            self.patchFile.p_file_minfos.getVersionFloat(_cobl_main) > 1.27
        self.id_info = {} #--Morphable factions keyed by fid
        from ....cint import FormID
        self.mFactLong = FormID(_cobl_main, 0x33FB)
        self.mFactable = set()

    def initData(self, progress):
        if not self.isActive: return
        for top_group_sig in self.getTypes():
            self.patchFile.group_patchers[top_group_sig].append(self)
        progress.setFull(len(self.srcs))
        for srcFile in self.srcs:
            try: self.readFromText(getPatchesPath(srcFile))
            except OSError: deprint(
                u'%s is no longer in patches set' % srcFile, traceback=True)
            progress.plus()
        from ....cint import FormID
        self.id_info = {FormID(*k): v for k, v in self.id_info.iteritems()}

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        id_info = self.id_info
        recordId = record.fid
        mFactLong = self.mFactLong
        if recordId in id_info and recordId != mFactLong:
            self.mFactable.add(recordId)
            if mFactLong not in [relation.faction for relation in
                                 record.relations]:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.IsHiddenFromPC = False
                    relation = override.create_relation()
                    relation.faction = mFactLong
                    relation.mod = 10
                    mname,rankName = id_info[recordId]
                    override.full = mname
                    ranks = override.ranks or [override.create_rank()]
                    for rank in ranks:
                        if not rank.male: rank.male = rankName
                        if not rank.female: rank.female = rank.male
                        if not rank.insigniaPath:
                            rank.insigniaPath = \
                            u'Menus\\Stats\\Cobl\\generic%02d.dds' % rank.rank
                    self.mod_count[modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def finishPatch(self,patchFile,progress):
        """Edits the bashed patch file directly."""
        mFactable = self.mFactable
        if not mFactable: return
        subProgress = SubProgress(progress)
        subProgress.setFull(max(len(mFactable),1))
        coblMod = patchFile.Current.LookupModFile(_cobl_main.s)
        record = coblMod.LookupRecord(self.mFactLong)
        if record.recType != 'FACT':
            _PrintFormID(self.mFactLong)
            print patchFile.Current.Debug_DumpModFiles()
            print record
            raise StateError(u"Cobl Morph Factions: Unable to lookup morphable"
                             u" faction record in Cobl Main.esm!")

        override = record.CopyAsOverride(patchFile)
        if override:
            override.relations = None
            pstate = 0
            for faction in mFactable:
                subProgress(pstate, _(u'Marking Morphable Factions...')+u'\n')
                relation = override.create_relation()
                relation.faction = faction
                relation.mod = 10
                pstate += 1
        mFactable.clear()

#------------------------------------------------------------------------------
class _ASEWorldEnforcer(_ExSpecial):
    """Suspends Cyrodiil quests while in Shivering Isles."""
    patcher_name = _(u'SEWorld Tests')
    patcher_text = _(u"Suspends Cyrodiil quests while in Shivering Isles. "
                     u"I.e. re-instates GetPlayerInSEWorld tests as "
                     u"necessary.")
    _read_write_records = ('QUST',)

    @classmethod
    def gui_cls_vars(cls):
        cls_vars = super(_ASEWorldEnforcer, cls).gui_cls_vars()
        return cls_vars.update({u'default_isEnabled': True}) or cls_vars

_ob_path = GPath(bush.game.master_file)
class SEWorldEnforcer(_ASEWorldEnforcer,Patcher):

    def __init__(self, p_name, p_file):
        super(SEWorldEnforcer, self).__init__(p_name, p_file)
        self.cyrodiilQuests = set()
        if _ob_path in p_file.loadSet:
            loadFactory = LoadFactory(False,MreRecord.type_class['QUST'])
            modInfo = self.patchFile.p_file_minfos[_ob_path]
            modFile = ModFile(modInfo,loadFactory)
            modFile.load(True)
            mapper = modFile.getLongMapper()
            for record in modFile.QUST.getActiveRecords():
                for condition in record.conditions:
                    if condition.ifunc == 365 and condition.compValue == 0:
                        self.cyrodiilQuests.add(mapper(record.fid))
                        break
        self.isActive = bool(self.cyrodiilQuests)

    def scanModFile(self,modFile,progress):
        if modFile.fileInfo.name == _ob_path: return
        cyrodiilQuests = self.cyrodiilQuests
        mapper = modFile.getLongMapper()
        patchBlock = self.patchFile.QUST
        for record in modFile.QUST.getActiveRecords():
            fid = mapper(record.fid)
            if fid not in cyrodiilQuests: continue
            for condition in record.conditions:
                if condition.ifunc == 365: break #--365: playerInSeWorld
            else:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Will write to log."""
        if not self.isActive: return
        cyrodiilQuests = self.cyrodiilQuests
        patchFile = self.patchFile
        keep = patchFile.getKeeper()
        patched = []
        for record in patchFile.QUST.getActiveRecords():
            if record.fid not in cyrodiilQuests: continue
            for condition in record.conditions:
                if condition.ifunc == 365: break #--365: playerInSeWorld
            else:
                condition = record.getDefault('conditions')
                condition.ifunc = 365
                record.conditions.insert(0,condition)
                keep(record.fid)
                patched.append(record.eid)
        log.setHeader(u'= ' + self._patcher_name)
        log(u'==='+_(u'Quests Patched') + u': %d' % (len(patched),))

class CBash_SEWorldEnforcer(_ASEWorldEnforcer,CBash_Patcher):
    # needed as scanRequiresChecked is True, will also add Oblivion to scanSet
    srcs = [_ob_path]
    scanRequiresChecked = True
    applyRequiresChecked = False

    def __init__(self, p_name, p_file):
        super(CBash_SEWorldEnforcer, self).__init__(p_name, p_file)
        self.cyrodiilQuests = set()
        self.isActive = _ob_path in p_file.loadSet
        self.mod_eids = defaultdict(list)

    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        for condition in record.conditions:
            if condition.ifunc == 365 and condition.compValue == 0:
                self.cyrodiilQuests.add(record.fid)
                return

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        if modFile.GName == _ob_path: return
        recordId = record.fid
        if recordId in self.cyrodiilQuests:
            for condition in record.conditions:
                if condition.ifunc == 365: return #--365: playerInSeWorld
            else:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    conditions = override.conditions
                    condition = override.create_condition()
                    condition.ifunc = 365
                    conditions.insert(0,condition)
                    override.conditions = conditions
                    self.mod_eids[modFile.GName].append(override.eid)
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        log.setHeader(u'= ' + self._patcher_name)
        log(u'\n=== '+_(u'Quests Patched'))
        for mod, eids in self.mod_eids.iteritems():
            log(u'* %s: %d' % (mod.s, len(eids)))
            for eid in sorted(eids):
                log(u'  * %s' % eid)
        self.mod_eids = defaultdict(list)

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
