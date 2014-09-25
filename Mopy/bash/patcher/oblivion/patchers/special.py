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
import os
import re
from .... import bosh # for modInfos
from ....bolt import GPath, sio, SubProgress, StateError, CsvReader
from ....bosh import PrintFormID, getPatchesList, getPatchesPath
from ....brec import MreRecord, ModReader, null4
from .... import bush
from ....cint import MGEFCode, FormID
from ....patcher.base import Patcher, CBash_Patcher
from ....patcher.oblivion.patchers.base import SpecialPatcher, ListPatcher, \
    CBash_ListPatcher

# Patchers: 40 ----------------------------------------------------------------
class AlchemicalCatalogs(SpecialPatcher,Patcher):
    """Updates COBL alchemical catalogs."""
    name = _(u'Cobl Catalogs')
    text = (_(u"Update COBL's catalogs of alchemical ingredients and effects.")
            + u'\n\n' + _(u'Will only run if Cobl Main.esm is loaded.'))
    defaultConfig = {'isEnabled':True}

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
        for (num,objectId,full,value) in bush.ingred_alchem:
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
        for (num,objectId,full,value) in bush.effect_alchem:
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

class CBash_AlchemicalCatalogs(SpecialPatcher,CBash_Patcher):
    """Updates COBL alchemical catalogs."""
    name = _(u'Cobl Catalogs')
    text = (_(u"Update COBL's catalogs of alchemical ingredients and effects.")
            + u'\n\n' + _(u'Will only run if Cobl Main.esm is loaded.'))

    unloadedText = ""
    srcs = [] #so as not to fail screaming when determining load mods - but
    # with the least processing required.
    defaultConfig = {'isEnabled':True}

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
        subProgress.setFull(len(bush.effect_alchem) + len(bush.ingred_alchem))
        pstate = 0
        #--Setup
        try:
            coblMod = patchFile.Current.LookupModFile(u'Cobl Main.esm')
        except KeyError, error:
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
                    print PrintFormID(fid)
                    print patchFile.Current.Debug_DumpModFiles()
                    print book
                    raise StateError(u"Cobl Catalogs: Unable to lookup book"
                                     u" record in Cobl Main.esm!")
                book = book.CopyAsOverride(self.patchFile)
                if not book:
                    print PrintFormID(fid)
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
        for (num,objectId,full,value) in bush.ingred_alchem:
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
        for (num,objectId,full,value) in bush.effect_alchem:
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
class CoblExhaustion(SpecialPatcher,ListPatcher):
    """Modifies most Greater power to work with Cobl's power exhaustion
    feature."""
    name = _(u'Cobl Exhaustion')
    text = (_(u"Modify greater powers to use Cobl's Power Exhaustion feature.")
            + u'\n\n' + _(u'Will only run if Cobl Main v1.66 (or higher) is'
                          u' active.'))
    autoKey = u'Exhaust'
    canAutoItemCheck = False #--GUI: Whether new items are checked by default

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.cobl = GPath(u'Cobl Main.esm')
        self.srcFiles = self.getConfigChecked()
        self.isActive = bool(self.srcFiles) and (
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
        progress.setFull(len(self.srcFiles))
        for srcFile in self.srcFiles:
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
        log.setHeader(u'= '+self.__class__.name)
        log(u'* '+_(u'Powers Tweaked') + u': %d' % sum(count.values()))
        for srcMod in bosh.modInfos.getOrdered(count.keys()):
            log(u'  * %s: %d' % (srcMod.s,count[srcMod]))

class CBash_CoblExhaustion(SpecialPatcher,CBash_ListPatcher):
    """Modifies most Greater power to work with Cobl's power exhaustion
    feature."""
    name = _(u'Cobl Exhaustion')
    text = (_(u"Modify greater powers to use Cobl's Power Exhaustion feature.")
            + u'\n\n' + _(u'Will only run if Cobl Main v1.66 (or higher) is'
                          u' active.'))
    autoKey = {u'Exhaust'}
    canAutoItemCheck = False #--GUI: Whether new items are checked by default
    unloadedText = ""

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        CBash_ListPatcher.initPatchFile(self,patchFile,loadMods)
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
                        not reNum.match(fields[3]): continue
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
        mod_count = self.mod_count
        log.setHeader(u'= '+self.__class__.name)
        log(u'* '+_(u'Powers Tweaked') + u': %d' % (sum(mod_count.values()),))
        for srcMod in bosh.modInfos.getOrdered(mod_count.keys()):
            log(u'  * %s: %d' % (srcMod.s,mod_count[srcMod]))
        self.mod_count = {}

#------------------------------------------------------------------------------
