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
from .... import bosh # for modInfos, dirs
from ....bolt import GPath, sio, SubProgress, StateError, CsvReader, Path
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
class ListsMerger(SpecialPatcher,ListPatcher):
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
    autoKey = (u'Delev',u'Relev')
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
            textPath = bosh.dirs['patches'].join(fileName)
            if textPath.exists():
                with CsvReader(textPath) as reader:
                    for fields in reader:
                        if len(fields) < 2 or not fields[0] or \
                            fields[1] not in (u'DR', u'R', u'D', u'RD', u''):
                            continue
                        tags[GPath(fields[0])] = fields[1]
        return tags

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

class CBash_ListsMerger(SpecialPatcher,CBash_ListPatcher):
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
    autoKey = {u'Delev', u'Relev'}
    forceAuto = False
    forceItemCheck = True #--Force configChecked to True for all items
    iiMode = True
    selectCommands = False
    allowUnloaded = False
    scanRequiresChecked = False
    applyRequiresChecked = False
    defaultConfig = {'isEnabled': True, 'autoIsChecked': True,
                     'configItems': [], 'configChecks': {},
                     'configChoices': {}}

    #--Static------------------------------------------------------------------
    @staticmethod
    def getDefaultTags():
        tags = {}
        for fileName in (u'Leveled Lists.csv',u'My Leveled Lists.csv'):
            textPath = getPatchesPath(fileName)
            if textPath.exists():
                with CsvReader(textPath) as reader:
                    for fields in reader:
                        if len(fields) < 2 or not fields[0] or \
                            fields[1] not in (u'DR', u'R', u'D', u'RD', u''):
                            continue
                        tags[GPath(fields[0])] = fields[1]
        return tags

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
