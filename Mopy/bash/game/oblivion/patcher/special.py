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
#  https://github.com/wrye-bash
#
# =============================================================================

import os
import re
from ....bolt import GPath, sio, SubProgress, StateError, CsvReader
from ....patcher import getPatchesPath, getPatchesList
from ....parsers import LoadFactory, ModFile
from ....brec import MreRecord, ModReader
from ....bass import null4
# from  bush import  genericAVEffects
from .... import bush, bosh, load_order
from ....cint import MGEFCode, FormID
from ....patcher.base import Patcher, CBash_Patcher
from ....patcher.patchers.base import SpecialPatcher, ListPatcher, \
    CBash_ListPatcher

__all__ = ['AlchemicalCatalogs', 'CBash_AlchemicalCatalogs', 'CoblExhaustion',
           'MFactMarker', 'CBash_MFactMarker', 'CBash_CoblExhaustion',
           'SEWorldEnforcer', 'CBash_SEWorldEnforcer']

# Util Functions --------------------------------------------------------------
def _PrintFormID(fid):
    # PBash short Fid
    if isinstance(fid,(long,int)):
        print '%08X' % fid
    # PBash long FId
    elif isinstance(fid, tuple):
        print '(%s, %06X)' % (fid[0],fid[1])
    # CBash / other(error)
    else:
        print repr(fid)

class _AAlchemicalCatalogs(SpecialPatcher):
    """Updates COBL alchemical catalogs."""
    name = _(u'Cobl Catalogs')
    text = (_(u"Update COBL's catalogs of alchemical ingredients and effects.")
            + u'\n\n' + _(u'Will only run if Cobl Main.esm is loaded.'))
    defaultConfig = {'isEnabled':True}

class AlchemicalCatalogs(_AAlchemicalCatalogs,Patcher):

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.isActive = (GPath(u'COBL Main.esm') in loadMods)
        self.id_ingred = {}

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('INGR',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('BOOK',) if self.isActive else ()

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch
        mod, but won't alter it."""
        if not self.isActive: return
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
        actorEffects = bush.genericAVEffects
        actorNames = bush.actorValues
        keep = self.patchFile.getKeeper()
        #--Book generatator
        def getBook(objectId,eid,full,value,iconPath,modelPath,modb_p):
            book = MreRecord.type_class['BOOK'](
                ModReader.recHeader('BOOK', 0, 0, 0, 0))
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
        effect_ingred = {}
        for fid,(eid,full,effects) in id_ingred.iteritems():
            for index,(mgef,actorValue) in enumerate(effects):
                effectName = mgef_name[mgef]
                if mgef in actorEffects: effectName += actorNames[actorValue]
                if effectName not in effect_ingred:
                    effect_ingred[effectName] = []
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
        log.setHeader(u'= '+self.__class__.name)
        log(u'* '+_(u'Ingredients Cataloged') + u': %d' % len(id_ingred))
        log(u'* '+_(u'Effects Cataloged') + u': %d' % len(effect_ingred))

class CBash_AlchemicalCatalogs(_AAlchemicalCatalogs,CBash_Patcher):
    unloadedText = ""
    srcs = [] #so as not to fail screaming when determining load mods - but
    # with the least processing required.

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        CBash_Patcher.initPatchFile(self,patchFile,loadMods)
        self.isActive = GPath(u'Cobl Main.esm') in loadMods
        if not self.isActive: return
        patchFile.indexMGEFs = True
        self.id_ingred = {}
        self.effect_ingred = {}
        self.SEFF = MGEFCode('SEFF')
        self.DebugPrintOnce = 0

    def getTypes(self):
        return ['INGR']

    #--Patch Phase ------------------------------------------------------------
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

        mgef_name = patchFile.mgef_name.copy()
        for mgef in mgef_name:
            mgef_name[mgef] = re.sub(_(u'(Attribute|Skill)'), u'',
                                     mgef_name[mgef])
        actorEffects = bush.genericAVEffects
        actorNames = bush.actorValues
        #--Book generator
        def getBook(patchFile, objectId):
            book = coblMod.LookupRecord(
                FormID(GPath(u'Cobl Main.esm'), objectId))
            # There have been reports of this patcher failing, hence the
            # sanity checks
            if book:
                if book.recType != 'BOOK':
                    print _PrintFormID(fid)
                    print patchFile.Current.Debug_DumpModFiles()
                    print book
                    raise StateError(u"Cobl Catalogs: Unable to lookup book"
                                     u" record in Cobl Main.esm!")
                book = book.CopyAsOverride(self.patchFile)
                if not book:
                    print _PrintFormID(fid)
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
                                if mgef in bush.mgef_name:
                                    print u'mgef found in bush.mgef_name'
                                else:
                                    print u'mgef not found in bush.mgef_name'
                            if mgef in bush.mgef_name:
                                effectName = re.sub(_(u'(Attribute|Skill)'),
                                                    u'', bush.mgef_name[mgef])
                            else:
                                effectName = u'Unknown Effect'
                        if mgef in actorEffects: effectName += actorNames[
                            effect[5]]  # actorValue field
                        buff.write(u'  '+effectName+u'\r\n')
                    buff.write(u'\r\n')
                book.text = re.sub(u'\r\n',u'<br>\r\n',buff.getvalue())
        #--Get Ingredients by Effect
        effect_ingred = self.effect_ingred = {}
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
                        if mgef in bush.mgef_name:
                            print u'mgef found in bush.mgef_name'
                        else:
                            print u'mgef not found in bush.mgef_name'
                    if mgef in bush.mgef_name:
                        effectName = re.sub(_(u'(Attribute|Skill)'), u'',
                                            bush.mgef_name[mgef])
                    else:
                        effectName = u'Unknown Effect'
                if mgef in actorEffects: effectName += actorNames[actorValue]
                effect_ingred.setdefault(effectName, []).append((index,full))
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
        log.setHeader(u'= '+self.__class__.name)
        log(u'* '+_(u'Ingredients Cataloged') + u': %d' % len(id_ingred))
        log(u'* '+_(u'Effects Cataloged') + u': %d' % len(effect_ingred))

#------------------------------------------------------------------------------
class _ACoblExhaustion(SpecialPatcher):
    """Modifies most Greater power to work with Cobl's power exhaustion
    feature."""
    # TODO: readFromText differ only in (PBash -> CBash):
    # -         longid = (aliases.get(mod,mod),int(objectIndex[2:],16))
    # +         longid = FormID(aliases.get(mod,mod),int(objectIndex[2:],16))
    name = _(u'Cobl Exhaustion')
    text = (_(u"Modify greater powers to use Cobl's Power Exhaustion feature.")
            + u'\n\n' + _(u'Will only run if Cobl Main v1.66 (or higher) is'
                          u' active.'))
    canAutoItemCheck = False #--GUI: Whether new items are checked by default

    def _pLog(self, log, count):
        log.setHeader(u'= ' + self.__class__.name)
        log(u'* ' + _(u'Powers Tweaked') + u': %d' % sum(count.values()))
        for srcMod in bosh.modInfos.getOrdered(count.keys()):
            log(u'  * %s: %d' % (srcMod.s, count[srcMod]))

class CoblExhaustion(_ACoblExhaustion,ListPatcher):
    autoKey = u'Exhaust'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(CoblExhaustion, self).initPatchFile(patchFile, loadMods)
        self.cobl = GPath(u'Cobl Main.esm')
        self.isActive = bool(self.srcs) and (
            self.cobl in loadMods and bosh.modInfos.getVersionFloat(
                self.cobl) > 1.65)
        self.id_exhaustion = {}

    def readFromText(self,textPath):
        """Imports type_id_name from specified text file."""
        aliases = self.patchFile.aliases
        id_exhaustion = self.id_exhaustion
        textPath = GPath(textPath)
        with CsvReader(textPath) as ins:
            reNum = re.compile(ur'\d+',re.U)
            for fields in ins:
                if len(fields) < 4 or fields[1][:2] != u'0x' or \
                        not reNum.match(fields[3]):
                    continue
                mod,objectIndex,eid,time = fields[:4]
                mod = GPath(mod)
                longid = (aliases.get(mod,mod),int(objectIndex[2:],16))
                id_exhaustion[longid] = int(time)

    def initData(self,progress):
        """Get names from source files."""
        if not self.isActive: return
        progress.setFull(len(self.srcs))
        for srcFile in self.srcs:
            srcPath = GPath(srcFile)
            patchesList = getPatchesList()
            if srcPath not in patchesList: continue
            self.readFromText(getPatchesPath(srcFile))
            progress.plus()

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('SPEL',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('SPEL',) if self.isActive else ()

    def scanModFile(self,modFile,progress):
        if not self.isActive: return
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
        count = {}
        exhaustId = (self.cobl,0x05139B)
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
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        self._pLog(log, count)

class CBash_CoblExhaustion(_ACoblExhaustion, CBash_ListPatcher):
    autoKey = {u'Exhaust'}
    unloadedText = ""

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(CBash_CoblExhaustion, self).initPatchFile(patchFile, loadMods)
        if not self.isActive: return
        self.cobl = GPath(u'Cobl Main.esm')
        self.isActive = (self.cobl in loadMods and
                         bosh.modInfos.getVersionFloat(self.cobl) > 1.65)
        self.id_exhaustion = {}
        self.mod_count = {}
        self.SEFF = MGEFCode('SEFF')
        self.exhaustionId = FormID(self.cobl, 0x05139B)

    def initData(self,group_patchers,progress):
        if not self.isActive: return
        for type in self.getTypes():
            group_patchers.setdefault(type,[]).append(self)
        progress.setFull(len(self.srcs))
        for srcFile in self.srcs:
            srcPath = GPath(srcFile)
            patchesList = getPatchesList()
            if srcPath not in patchesList: continue
            self.readFromText(getPatchesPath(srcFile))
            progress.plus()

    def getTypes(self):
        return ['SPEL']

    def readFromText(self,textPath):
        """Imports type_id_name from specified text file."""
        aliases = self.patchFile.aliases
        id_exhaustion = self.id_exhaustion
        textPath = GPath(textPath)
        with CsvReader(textPath) as ins:
            reNum = re.compile(ur'\d+',re.U)
            for fields in ins:
                if len(fields) < 4 or fields[1][:2] != u'0x' or \
                        not reNum.match(fields[3]):
                    continue
                mod,objectIndex,eid,time = fields[:4]
                mod = GPath(mod)
                longid = FormID(aliases.get(mod,mod),int(objectIndex[2:],16))
                id_exhaustion[longid] = int(time)

    #--Patch Phase ------------------------------------------------------------
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
                effect.visual = MGEFCode(None,None)
                effect.IsHostile = False

                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        self._pLog(log, self.mod_count)
        self.mod_count = {}

#------------------------------------------------------------------------------
class _AMFactMarker(SpecialPatcher):
    """Mark factions that player can acquire while morphing."""
    name = _(u'Morph Factions')
    text = (_(u"Mark factions that player can acquire while morphing.") +
            u'\n\n' +
            _(u"Requires Cobl 1.28 and Wrye Morph or similar.")
            )
    autoRe = re.compile(ur"^UNDEFINED$",re.I|re.U)
    canAutoItemCheck = False #--GUI: Whether new items are checked by default
    srcsHeader = u'=== ' + _(u'Source Mods/Files')

    def _pLog(self, log, changed):
        log.setHeader(u'= ' + self.__class__.name)
        self._srcMods(log)
        log(u'\n=== ' + _(u'Morphable Factions'))
        for mod in bosh.modInfos.getOrdered(changed):
            log(u'* %s: %d' % (mod.s, changed[mod]))

class MFactMarker(_AMFactMarker,ListPatcher):
    autoKey = 'MFact'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(MFactMarker, self).initPatchFile(patchFile, loadMods)
        self.id_info = {} #--Morphable factions keyed by fid
        self.isActive = bool(self.srcs) and load_order.isActiveCached(
            GPath(u"Cobl Main.esm"))
        self.mFactLong = (GPath(u"Cobl Main.esm"),0x33FB)

    def initData(self,progress):
        """Get names from source files."""
        if not self.isActive: return
        aliases = self.patchFile.aliases
        id_info = self.id_info
        for srcFile in self.srcs:
            textPath = getPatchesPath(srcFile)
            if not textPath.exists(): continue
            with CsvReader(textPath) as ins:
                for fields in ins:
                    if len(fields) < 6 or fields[1][:2] != u'0x':
                        continue
                    mod,objectIndex = fields[:2]
                    mod = GPath(mod)
                    longid = (aliases.get(mod,mod),int(objectIndex,0))
                    morphName = fields[4].strip()
                    rankName = fields[5].strip()
                    if not morphName: continue
                    if not rankName: rankName = _(u'Member')
                    id_info[longid] = (morphName,rankName)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('FACT',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('FACT',) if self.isActive else ()

    def scanModFile(self, modFile, progress):
        """Scan modFile."""
        if not self.isActive: return
        id_info = self.id_info
        modName = modFile.fileInfo.name
        mapper = modFile.getLongMapper()
        patchBlock = self.patchFile.FACT
        if modFile.fileInfo.name == GPath(u"Cobl Main.esm"):
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
        changed = {}
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
                mod = record.fid[0]
                changed[mod] = changed.setdefault(mod,0) + 1
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

class CBash_MFactMarker(_AMFactMarker, CBash_ListPatcher):
    autoKey = {'MFact'}
    unloadedText = u""

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(CBash_MFactMarker, self).initPatchFile(patchFile, loadMods)
        if not self.isActive: return
        self.cobl = GPath(u'Cobl Main.esm')
        self.isActive = self.cobl in loadMods and \
                        bosh.modInfos.getVersionFloat(self.cobl) > 1.27
        self.id_info = {} #--Morphable factions keyed by fid
        self.mFactLong = FormID(self.cobl,0x33FB)
        self.mod_count = {}
        self.mFactable = set()

    def initData(self,group_patchers,progress):
        if not self.isActive: return
        for type in self.getTypes():
            group_patchers.setdefault(type,[]).append(self)
        progress.setFull(len(self.srcs))
        for srcFile in self.srcs:
            srcPath = GPath(srcFile)
            patchesList = getPatchesList()
            if srcPath not in patchesList: continue
            self.readFromText(getPatchesPath(srcFile))
            progress.plus()

    def getTypes(self):
        return ['FACT']

    def readFromText(self,textPath):
        """Imports id_info from specified text file."""
        aliases = self.patchFile.aliases
        id_info = self.id_info
        textPath = GPath(textPath)
        if not textPath.exists(): return
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 6 or fields[1][:2] != u'0x':
                    continue
                mod,objectIndex = fields[:2]
                mod = GPath(mod)
                longid = FormID(aliases.get(mod,mod),int(objectIndex,0))
                morphName = fields[4].strip()
                rankName = fields[5].strip()
                if not morphName: continue
                if not rankName: rankName = _(u'Member')
                id_info[longid] = (morphName,rankName)

    #--Patch Phase ------------------------------------------------------------
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
                    mod_count = self.mod_count
                    mod_count[modFile.GName] = mod_count.get(modFile.GName,
                                                             0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def finishPatch(self,patchFile,progress):
        """Edits the bashed patch file directly."""
        mFactable = self.mFactable
        if not mFactable: return
        subProgress = SubProgress(progress)
        subProgress.setFull(max(len(mFactable),1))
        pstate = 0
        coblMod = patchFile.Current.LookupModFile(self.cobl.s)

        record = coblMod.LookupRecord(self.mFactLong)
        if record.recType != 'FACT':
            print _PrintFormID(self.mFactLong)
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

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        self._pLog(log, self.mod_count)
        self.mod_count = {}

#------------------------------------------------------------------------------
class _ASEWorldEnforcer(SpecialPatcher):
    """Suspends Cyrodiil quests while in Shivering Isles."""
    name = _(u'SEWorld Tests')
    text = _(u"Suspends Cyrodiil quests while in Shivering Isles. I.e. "
             u"re-instates GetPlayerInSEWorld tests as necessary.")
    defaultConfig = {'isEnabled': True}

class SEWorldEnforcer(_ASEWorldEnforcer,Patcher):
    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.cyrodiilQuests = set()
        if GPath(u'Oblivion.esm') in loadMods:
            loadFactory = LoadFactory(False,MreRecord.type_class['QUST'])
            modInfo = bosh.modInfos[GPath(u'Oblivion.esm')]
            modFile = ModFile(modInfo,loadFactory)
            modFile.load(True)
            mapper = modFile.getLongMapper()
            for record in modFile.QUST.getActiveRecords():
                for condition in record.conditions:
                    if condition.ifunc == 365 and condition.compValue == 0:
                        self.cyrodiilQuests.add(mapper(record.fid))
                        break
        self.isActive = bool(self.cyrodiilQuests)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('QUST',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('QUST',) if self.isActive else ()

    def scanModFile(self,modFile,progress):
        if not self.isActive: return
        if modFile.fileInfo.name == GPath(u'Oblivion.esm'): return
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
        log.setHeader('= '+self.__class__.name)
        log(u'==='+_(u'Quests Patched') + u': %d' % (len(patched),))

class CBash_SEWorldEnforcer(_ASEWorldEnforcer,CBash_Patcher):
    scanRequiresChecked = True
    applyRequiresChecked = False

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        CBash_Patcher.initPatchFile(self,patchFile,loadMods)
        self.cyrodiilQuests = set()
        self.srcs = [GPath(u'Oblivion.esm')]
        self.isActive = self.srcs[0] in loadMods
        self.mod_eids = {}

    def getTypes(self):
        return ['QUST']

    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        for condition in record.conditions:
            if condition.ifunc == 365 and condition.compValue == 0:
                self.cyrodiilQuests.add(record.fid)
                return

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        if modFile.GName in self.srcs: return

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
                    self.mod_eids.setdefault(modFile.GName, []).append(
                        override.eid)
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        mod_eids = self.mod_eids
        log.setHeader(u'= ' +self.__class__.name)
        log(u'\n=== '+_(u'Quests Patched'))
        for mod,eids in mod_eids.iteritems():
            log(u'* %s: %d' % (mod.s,len(eids)))
            for eid in sorted(eids):
                log(u'  * %s' % eid)
        self.mod_eids = {}

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
