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
import copy
from operator import itemgetter, attrgetter
import os
import re
import string
# Internal
from ... import bosh # for modInfos, dirs
from ...bolt import GPath, sio, SubProgress, StateError, CsvReader, Path
from ...bosh import PrintFormID, getPatchesList, getPatchesPath, \
    LoadFactory, ModFile
from ...brec import MreRecord, ModReader, null4
from ... import bush
from ...cint import MGEFCode, FormID
from .base import Patcher, CBash_Patcher, SpecialPatcher, ListPatcher, \
    CBash_ListPatcher

# Patchers: 40 ----------------------------------------------------------------
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

class CoblExhaustion(_ACoblExhaustion,ListPatcher):
    autoKey = u'Exhaust'

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

class CBash_CoblExhaustion(_ACoblExhaustion,CBash_ListPatcher):
    autoKey = {u'Exhaust'}
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
        mod_count = self.mod_count
        log.setHeader(u'= '+self.__class__.name)
        log(u'* '+_(u'Powers Tweaked') + u': %d' % (sum(mod_count.values()),))
        for srcMod in bosh.modInfos.getOrdered(mod_count.keys()):
            log(u'  * %s: %d' % (srcMod.s,mod_count[srcMod]))
        self.mod_count = {}

#------------------------------------------------------------------------------
class _AListsMerger(SpecialPatcher):
    """Merged leveled lists mod file."""
    scanOrder = 45
    editOrder = 45
    name = _(u'Leveled Lists')
    text = (_(
        u"Merges changes to leveled lists from ACTIVE/MERGED MODS ONLY.") +
            u'\n\n' + _(
        u'Advanced users may override Relev/Delev tags for any mod (active '
        u'or inactive) using the list below.'))
    tip = _(u"Merges changes to leveled lists from all active mods.")
    choiceMenu = (u'Auto', u'----', u'Delev', u'Relev')  #--List of possible
    # choices for each config item. Item 0 is default.
    forceAuto = False
    forceItemCheck = True #--Force configChecked to True for all items
    iiMode = True
    selectCommands = False
    defaultConfig = {'isEnabled': True, 'autoIsChecked': True,
                     'configItems': [], 'configChecks': {},
                     'configChoices': {}}

    #--Static------------------------------------------------------------------
    @staticmethod
    def getDefaultTags():
        tags = {}
        for fileName in (u'Leveled Lists.csv',u'My Leveled Lists.csv'):
            # TODO: P version: textPath = bosh.dirs['patches'].join(fileName)
            # Does it make a difference ?
            textPath = getPatchesPath(fileName)
            if textPath.exists():
                with CsvReader(textPath) as reader:
                    for fields in reader:
                        if len(fields) < 2 or not fields[0] or \
                            fields[1] not in (u'DR', u'R', u'D', u'RD', u''):
                            continue
                        tags[GPath(fields[0])] = fields[1]
        return tags

class ListsMerger(_AListsMerger,ListPatcher):
    autoKey = (u'Delev',u'Relev')

    #--Config Phase -----------------------------------------------------------
    def getChoice(self,item):
        """Get default config choice."""
        choice = self.configChoices.get(item)
        if not isinstance(choice,set): choice = {u'Auto'}
        if u'Auto' in choice:
            if item in bosh.modInfos:
                bashTags = bosh.modInfos[item].getBashTags()
                choice = {u'Auto'} | ({u'Delev', u'Relev'} & bashTags)
        self.configChoices[item] = choice
        return choice

    def getItemLabel(self,item):
        """Returns label for item to be used in list"""
        choice = map(itemgetter(0),self.configChoices.get(item,tuple()))
        if isinstance(item,Path): item = item.s
        if choice:
            return u'%s [%s]' % (item,u''.join(sorted(choice)))
        else:
            return item

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.srcMods = set(self.getConfigChecked()) & set(loadMods)
        self.listTypes = bush.game.listTypes
        self.type_list = dict([(type,{}) for type in self.listTypes])
        self.masterItems = {}
        self.mastersScanned = set()
        self.levelers = None #--Will initialize later
        self.empties = set()
        OverhaulCompat = False
        OOOMods = {GPath(u"Oscuro's_Oblivion_Overhaul.esm"),
                   GPath(u"Oscuro's_Oblivion_Overhaul.esp")}
        FransMods = {GPath(u"Francesco's Leveled Creatures-Items Mod.esm"),
                     GPath(u"Francesco.esp")}
        WCMods = {GPath(u"Oblivion Warcry.esp"),
                  GPath(u"Oblivion Warcry EV.esp")}
        TIEMods = {GPath(u"TIE.esp")}
        if GPath(u"Unofficial Oblivion Patch.esp") in self.srcMods:
            if (OOOMods|WCMods) & self.srcMods:
                OverhaulCompat = True
            elif FransMods & self.srcMods:
                if TIEMods & self.srcMods:
                    pass
                else:
                    OverhaulCompat = True
        if OverhaulCompat:
            self.OverhaulUOPSkips = set([
                (GPath(u'Oblivion.esm'),x) for x in [
                    0x03AB5D,   # VendorWeaponBlunt
                    0x03C7F1,   # LL0LootWeapon0Magic4Dwarven100
                    0x03C7F2,   # LL0LootWeapon0Magic7Ebony100
                    0x03C7F3,   # LL0LootWeapon0Magic5Elven100
                    0x03C7F4,   # LL0LootWeapon0Magic6Glass100
                    0x03C7F5,   # LL0LootWeapon0Magic3Silver100
                    0x03C7F7,   # LL0LootWeapon0Magic2Steel100
                    0x03E4D2,   # LL0NPCWeapon0MagicClaymore100
                    0x03E4D3,   # LL0NPCWeapon0MagicClaymoreLvl100
                    0x03E4DA,   # LL0NPCWeapon0MagicWaraxe100
                    0x03E4DB,   # LL0NPCWeapon0MagicWaraxeLvl100
                    0x03E4DC,   # LL0NPCWeapon0MagicWarhammer100
                    0x03E4DD,   # LL0NPCWeapon0MagicWarhammerLvl100
                    0x0733EA,   # ArenaLeveledHeavyShield,
                    0x0C7615,   # FGNPCWeapon0MagicClaymoreLvl100
                    0x181C66,   # SQ02LL0NPCWeapon0MagicClaymoreLvl100
                    0x053877,   # LL0NPCArmor0MagicLightGauntlets100
                    0x053878,   # LL0NPCArmor0MagicLightBoots100
                    0x05387A,   # LL0NPCArmor0MagicLightCuirass100
                    0x053892,   # LL0NPCArmor0MagicLightBootsLvl100
                    0x053893,   # LL0NPCArmor0MagicLightCuirassLvl100
                    0x053894,   # LL0NPCArmor0MagicLightGauntletsLvl100
                    0x053D82,   # LL0LootArmor0MagicLight5Elven100
                    0x053D83,   # LL0LootArmor0MagicLight6Glass100
                    0x052D89,   # LL0LootArmor0MagicLight4Mithril100
                    ]
                ])
        else:
            self.OverhaulUOPSkips = set()

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return self.listTypes

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return self.listTypes

    def scanModFile(self, modFile, progress):
        """Add lists from modFile."""
        #--Level Masters (complete initialization)
        if self.levelers is None:
            allMods = set(self.patchFile.allMods)
            self.levelers = [leveler for leveler in self.getConfigChecked() if
                             leveler in allMods]
            self.delevMasters = set()
            for leveler in self.levelers:
                self.delevMasters.update(bosh.modInfos[leveler].header.masters)
        #--Begin regular scan
        modName = modFile.fileInfo.name
        modFile.convertToLongFids(self.listTypes)
        #--PreScan for later Relevs/Delevs?
        if modName in self.delevMasters:
            for type in self.listTypes:
                for levList in getattr(modFile,type).getActiveRecords():
                    masterItems = self.masterItems.setdefault(levList.fid,{})
                    masterItems[modName] = set(
                        [entry.listId for entry in levList.entries])
            self.mastersScanned.add(modName)
        #--Relev/Delev setup
        configChoice = self.configChoices.get(modName,tuple())
        isRelev = (u'Relev' in configChoice)
        isDelev = (u'Delev' in configChoice)
        #--Scan
        for type in self.listTypes:
            levLists = self.type_list[type]
            newLevLists = getattr(modFile,type)
            for newLevList in newLevLists.getActiveRecords():
                listId = newLevList.fid
                if listId in self.OverhaulUOPSkips and modName == \
                        u'Unofficial Oblivion Patch.esp':
                    levLists[listId].mergeOverLast = True
                    continue
                isListOwner = (listId[0] == modName)
                #--Items, delevs and relevs sets
                newLevList.items = items = set(
                    [entry.listId for entry in newLevList.entries])
                if not isListOwner:
                    #--Relevs
                    newLevList.relevs = items.copy() if isRelev else set()
                    #--Delevs: all items in masters minus current items
                    newLevList.delevs = delevs = set()
                    if isDelev:
                        id_masterItems = self.masterItems.get(listId)
                        if id_masterItems:
                            for masterName in modFile.tes4.masters:
                                if masterName in id_masterItems:
                                    delevs |= id_masterItems[masterName]
                            delevs -= items
                            newLevList.items |= delevs
                #--Cache/Merge
                if isListOwner:
                    levList = copy.deepcopy(newLevList)
                    levList.mergeSources = []
                    levLists[listId] = levList
                elif listId not in levLists:
                    levList = copy.deepcopy(newLevList)
                    levList.mergeSources = [modName]
                    levLists[listId] = levList
                else:
                    levLists[listId].mergeWith(newLevList,modName)

    def buildPatch(self,log,progress):
        """Adds merged lists to patchfile."""
        keep = self.patchFile.getKeeper()
        #--Relevs/Delevs List
        log.setHeader(u'= '+self.__class__.name,True)
        log.setHeader(u'=== '+_(u'Delevelers/Relevelers'))
        for leveler in (self.levelers or []):
            log(u'* '+self.getItemLabel(leveler))
        #--Save to patch file
        for label, type in ((_(u'Creature'), 'LVLC'), (_(u'Actor'), 'LVLN'),
                (_(u'Item'), 'LVLI'), (_(u'Spell'), 'LVSP')):
            if type not in self.listTypes: continue
            log.setHeader(u'=== '+_(u'Merged %s Lists') % label)
            patchBlock = getattr(self.patchFile,type)
            levLists = self.type_list[type]
            for record in sorted(levLists.values(),key=attrgetter('eid')):
                if not record.mergeOverLast: continue
                fid = keep(record.fid)
                patchBlock.setRecord(levLists[fid])
                log(u'* '+record.eid)
                for mod in record.mergeSources:
                    log(u'  * ' + self.getItemLabel(mod))
        #--Discard empty sublists
        for label, type in ((_(u'Creature'), 'LVLC'), (_(u'Actor'), 'LVLN'),
                (_(u'Item'), 'LVLI'), (_(u'Spell'), 'LVSP')):
            if type not in self.listTypes: continue
            patchBlock = getattr(self.patchFile,type)
            levLists = self.type_list[type]
            #--Empty lists
            empties = []
            sub_supers = dict((x,[]) for x in levLists.keys())
            for record in sorted(levLists.values()):
                listId = record.fid
                if not record.items:
                    empties.append(listId)
                else:
                    subLists = [x for x in record.items if x in sub_supers]
                    for subList in subLists:
                        sub_supers[subList].append(listId)
            #--Clear empties
            removed = set()
            cleaned = set()
            while empties:
                empty = empties.pop()
                if empty not in sub_supers: continue
                for super in sub_supers[empty]:
                    record = levLists[super]
                    record.entries = [x for x in record.entries if
                                      x.listId != empty]
                    record.items.remove(empty)
                    patchBlock.setRecord(record)
                    if not record.items:
                        empties.append(super)
                    cleaned.add(record.eid)
                    removed.add(levLists[empty].eid)
                    keep(super)
            log.setHeader(u'=== '+_(u'Empty %s Sublists') % label)
            for eid in sorted(removed,key=string.lower):
                log(u'* '+eid)
            log.setHeader(u'=== '+_(u'Empty %s Sublists Removed') % label)
            for eid in sorted(cleaned,key=string.lower):
                log(u'* '+eid)

class CBash_ListsMerger(_AListsMerger,CBash_ListPatcher):
    autoKey = {u'Delev', u'Relev'}
    allowUnloaded = False
    scanRequiresChecked = False
    applyRequiresChecked = False

    #--Config Phase -----------------------------------------------------------
    def getChoice(self,item):
        """Get default config choice."""
        choice = self.configChoices.get(item)
        if not isinstance(choice,set): choice = {u'Auto'}
        if u'Auto' in choice:
            if item in bosh.modInfos:
                choice = {u'Auto'}
                bashTags = bosh.modInfos[item].getBashTags()
                for key in (u'Delev',u'Relev'):
                    if key in bashTags: choice.add(key)
        self.configChoices[item] = choice
        return choice

    def getItemLabel(self,item):
        """Returns label for item to be used in list"""
        choice = map(itemgetter(0),self.configChoices.get(item,tuple()))
        if isinstance(item,Path): item = item.s
        if choice:
            return u'%s [%s]' % (item,u''.join(sorted(choice)))
        else:
            return item

    def initPatchFile(self,patchFile,loadMods):
        CBash_ListPatcher.initPatchFile(self,patchFile,loadMods)
        self.isActive = True
        self.id_delevs = {}
        self.id_list = {}
        self.id_attrs = {}
        self.mod_count = {}
        self.empties = set()
        importMods = set(self.srcs) & set(loadMods)
        OverhaulCompat = False
        OOOMods = {GPath(u"Oscuro's_Oblivion_Overhaul.esm"),
                   GPath(u"Oscuro's_Oblivion_Overhaul.esp")}
        FransMods = {GPath(u"Francesco's Leveled Creatures-Items Mod.esm"),
                     GPath(u"Francesco.esp")}
        WCMods = {GPath(u"Oblivion Warcry.esp"),
                  GPath(u"Oblivion Warcry EV.esp")}
        TIEMods = {GPath(u"TIE.esp")}
        if GPath(u"Unofficial Oblivion Patch.esp") in importMods:
            if (OOOMods|WCMods) & importMods:
                OverhaulCompat = True
            elif FransMods & importMods:
                if TIEMods & importMods:
                    pass
                else:
                    OverhaulCompat = True
        if OverhaulCompat:
            self.OverhaulUOPSkips = set([
                FormID(GPath(u'Oblivion.esm'),x) for x in [
                    0x03AB5D,   # VendorWeaponBlunt
                    0x03C7F1,   # LL0LootWeapon0Magic4Dwarven100
                    0x03C7F2,   # LL0LootWeapon0Magic7Ebony100
                    0x03C7F3,   # LL0LootWeapon0Magic5Elven100
                    0x03C7F4,   # LL0LootWeapon0Magic6Glass100
                    0x03C7F5,   # LL0LootWeapon0Magic3Silver100
                    0x03C7F7,   # LL0LootWeapon0Magic2Steel100
                    0x03E4D2,   # LL0NPCWeapon0MagicClaymore100
                    0x03E4D3,   # LL0NPCWeapon0MagicClaymoreLvl100
                    0x03E4DA,   # LL0NPCWeapon0MagicWaraxe100
                    0x03E4DB,   # LL0NPCWeapon0MagicWaraxeLvl100
                    0x03E4DC,   # LL0NPCWeapon0MagicWarhammer100
                    0x03E4DD,   # LL0NPCWeapon0MagicWarhammerLvl100
                    0x0733EA,   # ArenaLeveledHeavyShield,
                    0x0C7615,   # FGNPCWeapon0MagicClaymoreLvl100
                    0x181C66,   # SQ02LL0NPCWeapon0MagicClaymoreLvl100
                    0x053877,   # LL0NPCArmor0MagicLightGauntlets100
                    0x053878,   # LL0NPCArmor0MagicLightBoots100
                    0x05387A,   # LL0NPCArmor0MagicLightCuirass100
                    0x053892,   # LL0NPCArmor0MagicLightBootsLvl100
                    0x053893,   # LL0NPCArmor0MagicLightCuirassLvl100
                    0x053894,   # LL0NPCArmor0MagicLightGauntletsLvl100
                    0x053D82,   # LL0LootArmor0MagicLight5Elven100
                    0x053D83,   # LL0LootArmor0MagicLight6Glass100
                    0x052D89,   # LL0LootArmor0MagicLight4Mithril100
                    ]
                ])
        else:
            self.OverhaulUOPSkips = set()

    def getTypes(self):
        return ['LVLC','LVLI','LVSP']

    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        recordId = record.fid
        if recordId in self.OverhaulUOPSkips and modFile.GName == GPath(
                'Unofficial Oblivion Patch.esp'):
            return
        script = record.script
        if script and not script.ValidateFormID(self.patchFile):
            script = None
        template = record.template
        if template and not template.ValidateFormID(self.patchFile):
            template = None
        curList = [(level, listId, count) for level, listId, count in
                   record.entries_list if
                   listId.ValidateFormID(self.patchFile)]
        if recordId not in self.id_list:
            #['level', 'listId', 'count']
            self.id_list[recordId] = curList
            self.id_attrs[recordId] = [record.chanceNone, script, template,
                                       (record.flags or 0)]
        else:
            mergedList = self.id_list[recordId]
            configChoice = self.configChoices.get(modFile.GName,tuple())
            isRelev = u'Relev' in configChoice
            isDelev = u'Delev' in configChoice
            delevs = self.id_delevs.setdefault(recordId, set())
            curItems = set([listId for level, listId, count in curList])
            if isRelev:
                # Can add and set the level/count of items, but not delete
                # items
                #Ironically, the first step is to delete items that the list
                #  will add right back
                #This is an easier way to update level/count than actually
                # checking if they need changing

                #Filter out any records that may have their level/count updated
                mergedList = [entry for entry in mergedList if
                              entry[1] not in curItems]  # entry[1] = listId
                #Add any new records as well as any that were filtered out
                mergedList += curList
                #Remove the added items from the deleveled list
                delevs -= curItems
                self.id_attrs[recordId] = [record.chanceNone, script, template,
                                           (record.flags or 0)]
            else:
                #Can add new items, but can't change existing ones
                items = set([entry[1] for entry in mergedList])  # entry[1]
                # = listId
                mergedList += [(level, listId, count) for level, listId, count
                               in curList if listId not in items]
                mergedAttrs = self.id_attrs[recordId]
                self.id_attrs[recordId] =[record.chanceNone or mergedAttrs[0],
                                         script or mergedAttrs[1],
                                         template or mergedAttrs[2],
                                         (record.flags or 0) | mergedAttrs[3]]
            #--Delevs: all items in masters minus current items
            if isDelev:
                deletedItems = set([listId for master in record.History() for
                                    level, listId, count in master.entries_list
                                    if listId.ValidateFormID(
                        self.patchFile)]) - curItems
                delevs |= deletedItems

            #Remove any items that were deleveled
            mergedList = [entry for entry in mergedList if
                          entry[1] not in delevs]  # entry[1] = listId
            self.id_list[recordId] = mergedList
            self.id_delevs[recordId] = delevs

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        recordId = record.fid
        merged = recordId in self.id_list
        if merged:
            self.scan(modFile,record,bashTags)
            mergedList = self.id_list[recordId]
            mergedAttrs = self.id_attrs[recordId]
            newList = [(level, listId, count) for level, listId, count in
                       record.entries_list if
                       listId.ValidateFormID(self.patchFile)]
            script = record.script
            if script and not script.ValidateFormID(self.patchFile):
                script = None
            template = record.template
            if template and not template.ValidateFormID(self.patchFile):
                template = None
            newAttrs = [record.chanceNone, script, template,
                        (record.flags or 0)]
        # Can't tell if any sublists are actually empty until they've all
        # been processed/merged
        #So every level list gets copied into the patch, so that they can be
        #  checked after the regular patch process
        #They'll get deleted from the patch there as needed.
        override = record.CopyAsOverride(self.patchFile)
        if override:
            if merged and (newAttrs != mergedAttrs or sorted(newList,
                key=itemgetter(1)) != sorted(mergedList, key=itemgetter(1))):
                override.chanceNone, override.script, override.template, \
                override.flags = mergedAttrs
                override.entries_list = mergedList
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
            record.UnloadRecord()
            record._RecordID = override._RecordID

    def finishPatch(self,patchFile, progress):
        """Edits the bashed patch file directly."""
        if self.empties is None: return
        subProgress = SubProgress(progress)
        subProgress.setFull(len(self.getTypes()))
        pstate = 0
        #Clean up any empty sublists
        empties = self.empties
        emptiesAdd = empties.add
        emptiesDiscard = empties.discard
        for type in self.getTypes():
            subProgress(pstate,
                        _(u'Looking for empty %s sublists...') % type + u'\n')
            #Remove any empty sublists
            madeChanges = True
            while madeChanges:
                madeChanges = False
                oldEmpties = empties.copy()
                for record in getattr(patchFile,type):
                    recordId = record.fid
                    items = set([entry.listId for entry in record.entries])
                    if items:
                        emptiesDiscard(recordId)
                    else:
                        emptiesAdd(recordId)
                    toRemove = empties & items
                    if toRemove:
                        madeChanges = True
                        cleanedEntries = [entry for entry in record.entries if
                                          entry.listId not in toRemove]
                        record.entries = cleanedEntries
                        if cleanedEntries:
                            emptiesDiscard(recordId)
                        else:
                            emptiesAdd(recordId)
                if oldEmpties != empties:
                    oldEmpties = empties.copy()
                    madeChanges = True

            # Remove any identical to winning lists, except those that were
            # merged into the patch
            for record in getattr(patchFile,type):
                conflicts = record.Conflicts()
                numConflicts = len(conflicts)
                if numConflicts:
                    curConflict = 1  # Conflict at 0 will be the patchfile.
                    # No sense comparing it to itself.
                    #Find the first conflicting record that wasn't merged
                    while curConflict < numConflicts:
                        prevRecord = conflicts[curConflict]
                        if prevRecord.GetParentMod().GName not in \
                                patchFile.mergeSet:
                            break
                        curConflict += 1
                    else:
                        continue
                    # If the record in the patchfile matches the previous
                    # non-merged record, delete it.
                    #Ordering doesn't matter, hence the conversion to sets
                    if set(prevRecord.entries_list) == set(
                            record.entries_list) and [record.chanceNone,
                                                      record.script,
                                                      record.template,
                                                      record.flags] == [
                        prevRecord.chanceNone, prevRecord.script,
                        prevRecord.template, prevRecord.flags]:
                        record.DeleteRecord()
            pstate += 1
        self.empties = None

    def buildPatchLog(self,log):
        """Will write to log."""
        #--Log
        mod_count = self.mod_count
        log.setHeader(u'= ' +self.__class__.name)
        log(u'* '+_(u'Modified LVL') + u': %d' % (sum(mod_count.values()),))
        for srcMod in bosh.modInfos.getOrdered(mod_count.keys()):
            log(u'  * %s: %d' % (srcMod.s,mod_count[srcMod]))
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

class MFactMarker(_AMFactMarker,ListPatcher):
    autoKey = 'MFact'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_info = {} #--Morphable factions keyed by fid
        self.srcFiles = self.getConfigChecked()
        self.isActive = bool(self.srcFiles) and GPath(
            u"Cobl Main.esm") in bosh.modInfos.ordered
        self.mFactLong = (GPath(u"Cobl Main.esm"),0x33FB)

    def initData(self,progress):
        """Get names from source files."""
        if not self.isActive: return
        aliases = self.patchFile.aliases
        id_info = self.id_info
        for srcFile in self.srcFiles:
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
        modsHeader = u'=== ' + _(u'Source Mods/Files')
        log.setHeader(u'= ' + self.__class__.name)
        log(modsHeader)
        for file in self.srcFiles:
            log(u'* ' +file.s)
        log(u'\n=== '+_(u'Morphable Factions'))
        for mod in sorted(changed):
            log(u'* %s: %d' % (mod.s,changed[mod]))

class CBash_MFactMarker(_AMFactMarker,CBash_ListPatcher):
    autoKey = {'MFact'}
    unloadedText = u""

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        CBash_ListPatcher.initPatchFile(self,patchFile,loadMods)
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
            print PrintFormID(self.mFactLong)
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
        mod_count = self.mod_count
        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods/Files'))
        for file in self.srcs:
            log(u'* '+file.s)
        log(u'\n=== '+_(u'Morphable Factions'))
        for srcMod in bosh.modInfos.getOrdered(mod_count.keys()):
            log(u'* %s: %d' % (srcMod.s,mod_count[srcMod]))
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

#------------------------------------------------------------------------------
class _AContentsChecker(SpecialPatcher):
    """Checks contents of leveled lists, inventories and containers for
    correct content types."""
    scanOrder = 50
    editOrder = 50
    name = _(u'Contents Checker')
    text = _(u"Checks contents of leveled lists, inventories and containers"
             u" for correct types.")
    defaultConfig = {'isEnabled': True}

class ContentsChecker(_AContentsChecker,Patcher):
    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.contType_entryTypes = {
            'LVSP':'LVSP,SPEL'.split(','),
            'LVLC':'LVLC,NPC_,CREA'.split(','),
            #--LVLI will also be applied for containers.
            'LVLI': 'LVLI,ALCH,AMMO,APPA,ARMO,BOOK,CLOT,INGR,KEYM,LIGH,MISC,'
                    'SGST,SLGM,WEAP'.split(','),
            }
        self.contType_entryTypes['CONT'] = self.contType_entryTypes['LVLI']
        self.contType_entryTypes['CREA'] = self.contType_entryTypes['LVLI']
        self.contType_entryTypes['NPC_'] = self.contType_entryTypes['LVLI']
        self.id_type = {}
        self.id_eid = {}
        #--Types
        self.contTypes = self.contType_entryTypes.keys()
        self.entryTypes = sum(self.contType_entryTypes.values(),[])

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return tuple(self.contTypes + self.entryTypes) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return tuple(self.contTypes) if self.isActive else ()

    def scanModFile(self, modFile, progress):
        """Scan modFile."""
        if not self.isActive: return
        modName = modFile.fileInfo.name
        mapper = modFile.getLongMapper()
        #--Remember types (only when first defined)
        id_type = self.id_type
        for type in self.entryTypes:
            if type not in modFile.tops: continue
            for record in modFile.tops[type].getActiveRecords():
                fid = record.fid
                if not record.longFids: fid = mapper(fid)
                if fid not in id_type:
                    id_type[fid] = type
##                if fid[0] == modName:
##                    id_type[fid] = type
        #--Save container types
        modFile.convertToLongFids(self.contTypes)
        for type in self.contTypes:
            if type not in modFile.tops: continue
            patchBlock = getattr(self.patchFile,type)
            id_records = patchBlock.id_records
            for record in modFile.tops[type].getActiveRecords():
                if record.fid not in id_records:
                    patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress):
        """Make changes to patchfile."""
        if not self.isActive: return
        modFile = self.patchFile
        keep = self.patchFile.getKeeper()
        id_type = self.id_type
        id_eid = self.id_eid
        log.setHeader('= '+self.__class__.name)
        #--Lists
        for cAttr,eAttr,types in (
            ('entries','listId',('LVSP','LVLI','LVLC')),
            ('items','item',('CONT','CREA','NPC_')),
            ):
            for type in types:
                if type not in modFile.tops: continue
                entryTypes = set(self.contType_entryTypes[type])
                id_removed = {}
                for record in modFile.tops[type].records:
                    newEntries = []
                    oldEntries = getattr(record,cAttr)
                    for entry in oldEntries:
                        entryId = getattr(entry,eAttr)
                        if id_type.get(entryId) in entryTypes:
                            newEntries.append(entry)
                        else:
                            removed = id_removed.setdefault(record.fid,[])
                            removed.append(entryId)
                            id_eid[record.fid] = record.eid
                    if len(newEntries) != len(oldEntries):
                        setattr(record,cAttr,newEntries)
                        keep(record.fid)
                #--Log it
                if id_removed:
                    log(u"\n=== "+type)
                    for contId in sorted(id_removed):
                        log(u'* ' + id_eid[contId])
                        for removedId in sorted(id_removed[contId]):
                            mod,index = removedId
                            log(u'  . %s: %06X' % (mod.s,index))

class CBash_ContentsChecker(_AContentsChecker,CBash_Patcher):
    srcs = []  # so as not to fail screaming when determining load mods - but
    # with the least processing required.

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        CBash_Patcher.initPatchFile(self,patchFile,loadMods)
        self.isActive = True
        self.type_validEntries = {'LVSP': {'LVSP', 'SPEL'},
                                'LVLC': {'LVLC', 'NPC_', 'CREA'},
                                'LVLI': {'LVLI', 'ALCH', 'AMMO', 'APPA',
                                         'ARMO', 'BOOK', 'CLOT', 'INGR',
                                         'KEYM', 'LIGH', 'MISC', 'SGST',
                                         'SLGM', 'WEAP'},
                                'CONT': {'LVLI', 'ALCH', 'AMMO', 'APPA',
                                         'ARMO', 'BOOK', 'CLOT', 'INGR',
                                         'KEYM', 'LIGH', 'MISC', 'SGST',
                                         'SLGM', 'WEAP'},
                                'CREA': {'LVLI', 'ALCH', 'AMMO', 'APPA',
                                         'ARMO', 'BOOK', 'CLOT', 'INGR',
                                         'KEYM', 'LIGH', 'MISC', 'SGST',
                                         'SLGM', 'WEAP'},
                                'NPC_': {'LVLI', 'ALCH', 'AMMO', 'APPA',
                                         'ARMO', 'BOOK', 'CLOT', 'INGR',
                                         'KEYM', 'LIGH', 'MISC', 'SGST',
                                         'SLGM', 'WEAP'}}
        self.listTypes = {'LVSP', 'LVLC', 'LVLI'}
        self.containerTypes = {'CONT', 'CREA', 'NPC_'}
        self.mod_type_id_badEntries = {}
        self.knownGood = set()

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CONT','CREA','NPC_','LVLI','LVLC','LVSP']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        type = record._Type
        Current = self.patchFile.Current
        badEntries = set()
        goodEntries = []
        knownGood = self.knownGood
        knownGoodAdd = knownGood.add
        goodAppend = goodEntries.append
        badAdd = badEntries.add
        validEntries = self.type_validEntries[type]
        if type in self.listTypes:
            topattr, subattr = ('entries','listId')
        else: #Is a container type
            topattr, subattr = ('items','item')

        for entry in getattr(record,topattr):
            entryId = getattr(entry,subattr)
            #Cache known good entries to decrease execution time
            if entryId in knownGood:
                goodAppend(entry)
            else:
                if entryId.ValidateFormID(self.patchFile):
                    entryRecords = Current.LookupRecords(entryId)
                else:
                    entryRecords = None
                if not entryRecords:
                    badAdd((_(u'NONE'),entryId,None,_(u'NONE')))
                else:
                    entryRecord = entryRecords[0]
                    if entryRecord.recType in validEntries:
                        knownGoodAdd(entryId)
                        goodAppend(entry)
                    else:
                        badAdd((entryRecord.eid, entryId,
                                entryRecord.GetParentMod().GName,
                                entryRecord.recType))
                        entryRecord.UnloadRecord()

        if badEntries:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                setattr(override, topattr, goodEntries)
                type_id_badEntries = self.mod_type_id_badEntries.setdefault(
                    modFile.GName, {})
                id_badEntries = type_id_badEntries.setdefault(type, {})
                id_badEntries[record.eid] = badEntries.copy()
                record.UnloadRecord()
                record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        mod_type_id_badEntries = self.mod_type_id_badEntries
        log.setHeader(u'= ' +self.__class__.name)
        for mod, type_id_badEntries in mod_type_id_badEntries.iteritems():
            log(u'\n=== %s' % mod.s)
            for type,id_badEntries in type_id_badEntries.iteritems():
                log(u'  * '+_(u'Cleaned %s: %d') % (type,len(id_badEntries)))
                for id, badEntries in id_badEntries.iteritems():
                    log(u'    * %s : %d' % (id,len(badEntries)))
                    for entry in sorted(badEntries, key=itemgetter(0)):
                        longId = entry[1]
                        if entry[2]:
                            modName = entry[2].s
                        else:
                            try:
                                modName = longId[0].s
                            except:
                                log(u'        . ' + _(
                                    u'Unloaded Object or Undefined Reference'))
                                continue
                        log(u'        . ' + _(
                            u'Editor ID: "%s", Object ID %06X: Defined in '
                            u'mod "%s" as %s') % (
                                entry[0], longId[1], modName, entry[3]))
        self.mod_type_id_badEntries = {}
