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

"""This module contains oblivion base patcher classes.""" # TODO:DOCS
import struct
from operator import itemgetter
# Internal
from ... import bosh # for bosh.modInfos, dirs
from ...bosh import PatchFile, getPatchesList, CBash_PatchFile, reModExt, \
    getPatchesPath, CountDict
from ...bolt import GPath, CsvReader
from ...brec import MreRecord
from ..base import AMultiTweakItem, AMultiTweaker, Patcher, \
    CBash_Patcher, ADoublePatcher, AAliasesPatcher, AListPatcher, \
    AImportPatcher, APatchMerger, AUpdateReferences

# Patchers 1 ------------------------------------------------------------------
class ListPatcher(AListPatcher,Patcher):

    def _patchesList(self):
        return bosh.dirs['patches'].list()

    def _patchFile(self):
        return PatchFile

class CBash_ListPatcher(AListPatcher,CBash_Patcher):
    unloadedText = u'\n\n'+_(u'Any non-active, non-merged mods in the'
                             u' following list will be IGNORED.')

    #--Config Phase -----------------------------------------------------------
    def _patchesList(self):
        return getPatchesList()

    def _patchFile(self):
        return CBash_PatchFile

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(CBash_ListPatcher, self).initPatchFile(patchFile,loadMods)
        self.srcs = self.getConfigChecked()
        self.isActive = bool(self.srcs)

    def getConfigChecked(self):
        """Returns checked config items in list order."""
        if self.allowUnloaded:
            return [item for item in self.configItems if
                    self.configChecks[item]]
        else:
            return [item for item in self.configItems if
                    self.configChecks[item] and (
                        item in self.patchFile.allMods or not reModExt.match(
                            item.s))]

class MultiTweakItem(AMultiTweakItem):
    # Notice the differences from Patcher in scanModFile and buildPatch
    # would it make any sense to make getRead/WriteClasses() into classmethods
    # see comments in Patcher
    # TODO: scanModFile() have VERY similar code - use getReadClasses here ?
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ()  # raise AbstractError ? NO: see NamesTweak_BodyTags

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ()

    def scanModFile(self,modFile,progress,patchFile): # extra param: patchFile
        """Scans specified mod file to extract info. May add record to patch
        mod, but won't alter it. If adds record, should first convert it to
        long fids."""
        pass

    def buildPatch(self,log,progress,patchFile): # extra param: patchFile
        """Edits patch file as desired. Should write to log."""
        pass  # TODO raise AbstractError ?

    def _patchLog(self, log, count):
        #--Log - must define self.logMsg in subclasses
        log.setHeader(self.logHeader)
        log(self.logMsg % sum(count.values()))
        for srcMod in bosh.modInfos.getOrdered(count.keys()):
            log(u'  * %s: %d' % (srcMod.s, count[srcMod]))

class CBash_MultiTweakItem(AMultiTweakItem):
    # extra CBash_MultiTweakItem class variables
    iiMode = False
    scanRequiresChecked = False
    applyRequiresChecked = False
    # the default scan and edit orders - override as needed
    scanOrder = 32
    editOrder = 32

    def __init__(self,label,tip,key,*choices,**kwargs):
        super(CBash_MultiTweakItem, self).__init__(label, tip, key, *choices,
                                                   **kwargs)
        self.mod_count = {} # extra CBash_MultiTweakItem instance variable

    #--Patch Phase ------------------------------------------------------------
    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return []

    # def apply(self,modFile,record): # TODO bashTags argument is unused in
    # all subclasses

    def buildPatchLog(self,log):
        """Will write to log."""
        #--Log
        mod_count = self.mod_count
        log.setHeader(self.logHeader)
        log(self.logMsg % sum(mod_count.values()))
        for srcMod in bosh.modInfos.getOrdered(mod_count.keys()):
            log(u'  * %s: %d' % (srcMod.s,mod_count[srcMod]))
        self.mod_count = {}

class MultiTweaker(AMultiTweaker,Patcher):

    def buildPatch(self,log,progress):
        """Applies individual tweaks."""
        if not self.isActive: return
        log.setHeader(u'= '+self.__class__.name,True)
        for tweak in self.enabledTweaks:
            tweak.buildPatch(log,progress,self.patchFile)

class CBash_MultiTweaker(AMultiTweaker,CBash_Patcher):
    #--Config Phase -----------------------------------------------------------
    def initData(self,group_patchers,progress):
        """Compiles material, i.e. reads source text, esp's, etc. as necessary."""
        if not self.isActive: return
        for tweak in self.enabledTweaks:
            for type_ in tweak.getTypes():
                group_patchers.setdefault(type_,[]).append(tweak)

    #--Patch Phase ------------------------------------------------------------
    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        log.setHeader(u'= '+self.__class__.name,True)
        for tweak in self.enabledTweaks:
            tweak.buildPatchLog(log)

class DoublePatcher(ADoublePatcher, ListPatcher): pass

class CBash_DoublePatcher(ADoublePatcher, CBash_ListPatcher): pass

# Patchers: 10 ----------------------------------------------------------------
class AliasesPatcher(AAliasesPatcher,Patcher): pass

class CBash_AliasesPatcher(AAliasesPatcher,CBash_Patcher):
    #--Config Phase -----------------------------------------------------------
    def getConfig(self,configs):
        """Get config from configs dictionary and/or set to default."""
        super(CBash_AliasesPatcher,self).getConfig(configs)
        self.srcs = [] #so as not to fail screaming when determining load
        # mods - but with the least processing required.

class PatchMerger(APatchMerger, ListPatcher):
    autoKey = u'Merge'

    def _setMods(self,patchFile):
        if self.isEnabled: #--Since other mods may rely on this
            patchFile.setMods(None,self.getConfigChecked())

class CBash_PatchMerger(APatchMerger, CBash_ListPatcher):
    autoKey = {u'Merge'}
    unloadedText = "" # Cbash only

    def _setMods(self,patchFile):
        if not self.isActive: return
        if self.isEnabled: #--Since other mods may rely on this
            patchFile.setMods(None,self.srcs)

class UpdateReferences(AUpdateReferences,ListPatcher):
    autoKey = u'Formids'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.srcFiles = self.getConfigChecked()
        self.isActive = bool(self.srcFiles)
        self.types = MreRecord.simpleTypes
        self.classes = self.types.union(
            {'CELL', 'WRLD', 'REFR', 'ACHR', 'ACRE'})
        self.old_new = {} #--Maps old fid to new fid
        self.old_eid = {} #--Maps old fid to old editor id
        self.new_eid = {} #--Maps new fid to new editor id

    def readFromText(self,textPath):
        """Reads replacment data from specified text file."""
        old_new,old_eid,new_eid = self.old_new,self.old_eid,self.new_eid
        aliases = self.patchFile.aliases
        with CsvReader(textPath) as ins:
            pack,unpack = struct.pack,struct.unpack
            for fields in ins:
                if len(fields) < 7 or fields[2][:2] != u'0x' or fields[6][:2] != u'0x': continue
                oldMod,oldObj,oldEid,newEid,newMod,newObj = fields[1:7]
                oldMod,newMod = map(GPath,(oldMod,newMod))
                oldId = (GPath(aliases.get(oldMod,oldMod)),int(oldObj,16))
                newId = (GPath(aliases.get(newMod,newMod)),int(newObj,16))
                old_new[oldId] = newId
                old_eid[oldId] = oldEid
                new_eid[newId] = newEid

    def initData(self,progress):
        """Get names from source files."""
        if not self.isActive: return
        progress.setFull(len(self.srcFiles))
        patchesList = getPatchesList()
        for srcFile in self.srcFiles:
            srcPath = GPath(srcFile)
            if srcPath not in patchesList: continue
            if getPatchesPath(srcFile).isfile():
                self.readFromText(getPatchesPath(srcFile))
            progress.plus()

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return tuple(self.classes) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return tuple(self.classes) if self.isActive else ()

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        if not self.isActive: return
        mapper = modFile.getLongMapper()
        patchCells = self.patchFile.CELL
        patchWorlds = self.patchFile.WRLD
        newRecords = []
        modFile.convertToLongFids(('CELL','WRLD','REFR','ACRE','ACHR'))
##        for type in self.types:
##            for record in getattr(modFile,type).getActiveRecords():
##                record = record.getTypeCopy(mapper)
##                if record.fid in self.old_new:
##                    getattr(self.patchFile,type).setRecord(record)
        if 'CELL' in modFile.tops:
            for cellBlock in modFile.CELL.cellBlocks:
                cellImported = False
                if cellBlock.cell.fid in patchCells.id_cellBlock:
                    patchCells.id_cellBlock[cellBlock.cell.fid].cell = cellBlock.cell
                    cellImported = True
                for record in cellBlock.temp:
                    if record.base in self.old_new:
                        if not cellImported:
                            patchCells.setCell(cellBlock.cell)
                            cellImported = True
                        for newRef in patchCells.id_cellBlock[cellBlock.cell.fid].temp:
                            if newRef.fid == record.fid:
                                loc = patchCells.id_cellBlock[cellBlock.cell.fid].temp.index(newRef)
                                patchCells.id_cellBlock[cellBlock.cell.fid].temp[loc] = record
                                break
                        else:
                            patchCells.id_cellBlock[cellBlock.cell.fid].temp.append(record)
                for record in cellBlock.persistent:
                    if record.base in self.old_new:
                        if not cellImported:
                            patchCells.setCell(cellBlock.cell)
                            cellImported = True
                        for newRef in patchCells.id_cellBlock[cellBlock.cell.fid].persistent:
                            if newRef.fid == record.fid:
                                loc = patchCells.id_cellBlock[cellBlock.cell.fid].persistent.index(newRef)
                                patchCells.id_cellBlock[cellBlock.cell.fid].persistent[loc] = record
                                break
                        else:
                            patchCells.id_cellBlock[cellBlock.cell.fid].persistent.append(record)
        if 'WRLD' in modFile.tops:
            for worldBlock in modFile.WRLD.worldBlocks:
                worldImported = False
                if worldBlock.world.fid in patchWorlds.id_worldBlocks:
                    patchWorlds.id_worldBlocks[worldBlock.world.fid].world = worldBlock.world
                    worldImported = True
                for cellBlock in worldBlock.cellBlocks:
                    cellImported = False
                    if worldBlock.world.fid in patchWorlds.id_worldBlocks and cellBlock.cell.fid in patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock:
                        patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].cell = cellBlock.cell
                        cellImported = True
                    for record in cellBlock.temp:
                        if record.base in self.old_new:
                            if not worldImported:
                                patchWorlds.setWorld(worldBlock.world)
                                worldImported = True
                            if not cellImported:
                                patchWorlds.id_worldBlocks[worldBlock.world.fid].setCell(cellBlock.cell)
                                cellImported = True
                            for newRef in patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].temp:
                                if newRef.fid == record.fid:
                                    loc = patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].temp.index(newRef)
                                    patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].temp[loc] = record
                                    break
                            else:
                                patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].temp.append(record)
                    for record in cellBlock.persistent:
                        if record.base in self.old_new:
                            if not worldImported:
                                patchWorlds.setWorld(worldBlock.world)
                                worldImported = True
                            if not cellImported:
                                patchWorlds.id_worldBlocks[worldBlock.world.fid].setCell(cellBlock.cell)
                                cellImported = True
                            for newRef in patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].persistent:
                                if newRef.fid == record.fid:
                                    loc = patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].persistent.index(newRef)
                                    patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].persistent[loc] = record
                                    break
                            else:
                                patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].persistent.append(record)

    def buildPatch(self,log,progress):
        """Adds merged fids to patchfile."""
        if not self.isActive: return
        old_new,old_eid,new_eid = self.old_new,self.old_eid,self.new_eid
        masters = self.patchFile
        keep = self.patchFile.getKeeper()
        count = CountDict()
        def swapper(oldId):
            newId = old_new.get(oldId,None)
            return newId if newId else oldId
##        for type in self.types:
##            for record in getattr(self.patchFile,type).getActiveRecords():
##                if record.fid in self.old_new:
##                    record.fid = swapper(record.fid)
##                    count.increment(record.fid[0])
####                    record.mapFids(swapper,True)
##                    record.setChanged()
##                    keep(record.fid)
        for cellBlock in self.patchFile.CELL.cellBlocks:
            for record in cellBlock.temp:
                if record.base in self.old_new:
                    record.base = swapper(record.base)
                    count.increment(cellBlock.cell.fid[0])
##                    record.mapFids(swapper,True)
                    record.setChanged()
                    keep(record.fid)
            for record in cellBlock.persistent:
                if record.base in self.old_new:
                    record.base = swapper(record.base)
                    count.increment(cellBlock.cell.fid[0])
##                    record.mapFids(swapper,True)
                    record.setChanged()
                    keep(record.fid)
        for worldBlock in self.patchFile.WRLD.worldBlocks:
            keepWorld = False
            for cellBlock in worldBlock.cellBlocks:
                for record in cellBlock.temp:
                    if record.base in self.old_new:
                        record.base = swapper(record.base)
                        count.increment(cellBlock.cell.fid[0])
##                        record.mapFids(swapper,True)
                        record.setChanged()
                        keep(record.fid)
                        keepWorld = True
                for record in cellBlock.persistent:
                    if record.base in self.old_new:
                        record.base = swapper(record.base)
                        count.increment(cellBlock.cell.fid[0])
##                        record.mapFids(swapper,True)
                        record.setChanged()
                        keep(record.fid)
                        keepWorld = True
            if keepWorld:
                keep(worldBlock.world.fid)

        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        for mod in self.getConfigChecked():
            log(u'* ' +mod.s)
        log(u'\n=== '+_(u'Records Patched'))
        for srcMod in bosh.modInfos.getOrdered(count.keys()):
            log(u'* %s: %d' % (srcMod.s,count[srcMod]))

from ..utilities import CBash_FidReplacer

class CBash_UpdateReferences(AUpdateReferences,CBash_ListPatcher):
    autoKey = {u'Formids'}
    unloadedText = u'\n\n'+_(u'Any non-active, non-merged mods referenced by files selected in the following list will be IGNORED.')

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ListPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.old = [] #--Maps old fid to new fid # TODO: unused ?
        self.new = [] #--Maps old fid to new fid # TODO: unused ?
        self.old_eid = {} #--Maps old fid to old editor id
        self.new_eid = {} #--Maps new fid to new editor id
        self.mod_count_old_new = {}

    def initData(self,group_patchers,progress):
        """Compiles material, i.e. reads source text, esp's, etc. as necessary."""
        if not self.isActive: return
        fidReplacer = CBash_FidReplacer(aliases=self.patchFile.aliases)
        progress.setFull(len(self.srcs))
        patchesList = getPatchesList()
        for srcFile in self.srcs:
            if not reModExt.search(srcFile.s):
                if srcFile not in patchesList: continue
                if getPatchesPath(srcFile).isfile():
                    fidReplacer.readFromText(getPatchesPath(srcFile))
            progress.plus()
        #--Finish
        self.old_new = fidReplacer.old_new
        self.old_eid.update(fidReplacer.old_eid)
        self.new_eid.update(fidReplacer.new_eid)
        self.isActive = bool(self.old_new)
        if not self.isActive: return

        for type_ in self.getTypes():
            group_patchers.setdefault(type_,[]).append(self)

    def getTypes(self):
        return ['MOD','FACT','RACE','MGEF','SCPT','LTEX','ENCH',
                'SPEL','BSGN','ACTI','APPA','ARMO','BOOK',
                'CLOT','CONT','DOOR','INGR','LIGH','MISC',
                'FLOR','FURN','WEAP','AMMO','NPC_','CREA',
                'LVLC','SLGM','KEYM','ALCH','SGST','LVLI',
                'WTHR','CLMT','REGN','CELLS','WRLD','ACHRS',
                'ACRES','REFRS','DIAL','INFOS','QUST','IDLE',
                'PACK','LSCR','LVSP','ANIO','WATR']

    #--Patch Phase ------------------------------------------------------------
    def mod_apply(self,modFile,bashTags):
        """Changes the mod in place without copying any records."""
        counts = modFile.UpdateReferences(self.old_new)
        #--Done
        if sum(counts):
            self.mod_count_old_new[modFile.GName] = [(count,self.old_eid[old_newId[0]],self.new_eid[old_newId[1]]) for count, old_newId in zip(counts, self.old_new.iteritems())]

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.GetRecordUpdatedReferences():
            override = record.CopyAsOverride(self.patchFile, UseWinningParents=True)
            if override:
                record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        mod_count_old_new = self.mod_count_old_new

        log.setHeader(u'= ' +self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        if not self.srcs:
            log(u". ~~%s~~" % _(u'None'))
        else:
            for srcFile in self.srcs:
                log(u"* " +srcFile.s)
        log(u'\n')
        for mod in bosh.modInfos.getOrdered(mod_count_old_new.keys()):
            entries = mod_count_old_new[mod]
            log(u'\n=== %s' % mod.s)
            entries.sort(key=itemgetter(1))
            log(u'  * '+_(u'Updated References') + u': %d' % sum([count for count, old, new in entries]))
            log(u'\n'.join([u'    * %3d %s >> %s' % entry for entry in entries if entry[0] > 0]))

        self.old_new = {} #--Maps old fid to new fid
        self.old_eid = {} #--Maps old fid to old editor id
        self.new_eid = {} #--Maps new fid to new editor id
        self.mod_count_old_new = {}

# Patchers: 20 ----------------------------------------------------------------
class ImportPatcher(AImportPatcher, ListPatcher):
    # Override in subclasses as needed
    logMsg = u'\n=== ' + _(u'Modified Records')

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return tuple(
            x.classType for x in self.srcClasses) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return tuple(
            x.classType for x in self.srcClasses) if self.isActive else ()

    def _patchLog(self,log,type_count):
        log.setHeader(u'= ' + self.__class__.name)
        log(self.__class__.modsHeader)
        for mod in self.sourceMods:
            log(u'* ' + mod.s)
        self._plog(log,type_count)

    def _plog(self,log,type_count):
        """Most common logging pattern - override as needed.

        Used in:
        GraphicsPatcher, ActorImporter, KFFZPatcher, DeathItemPatcher,
        ImportFactions, ImportScripts, NamesPatcher, SoundPatcher.
        """
        log(self.__class__.logMsg)
        for type_,count in sorted(type_count.iteritems()):
            if count: log(u'* ' + _(u'Modified %(type)s Records: %(count)d')
                          % {'type': type_, 'count': count})

class CBash_ImportPatcher(AImportPatcher, CBash_ListPatcher):
    scanRequiresChecked = True
    applyRequiresChecked = False

    def scan_more(self,modFile,record,bashTags):
        if modFile.GName in self.srcs:
            self.scan(modFile,record,bashTags)
        #Must check for "unloaded" conflicts that occur past the winning record
        #If any exist, they have to be scanned
        for conflict in record.Conflicts(True):
            if conflict != record:
                mod = conflict.GetParentMod()
                if mod.GName in self.srcs:
                    tags = bosh.modInfos[mod.GName].getBashTags()
                    self.scan(mod,conflict,tags)
            else: return

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        log.setHeader(u'= ' +self.__class__.name)
        self._clog(log)

    def _clog(self,log):
        """Most common logging pattern - override as needed.

        Used in:
        CBash_CellImporter, CBash_KFFZPatcher, CBash_NPCAIPackagePatcher,
        CBash_ImportRelations, CBash_RoadImporter, CBash_SpellsPatcher.
        You must define logMsg as a class attribute in subclasses except
        CBash_ImportFactions and CBash_ImportInventory.
        """
        mod_count = self.mod_count
        log(self.__class__.logMsg % sum(mod_count.values()))
        for srcMod in bosh.modInfos.getOrdered(mod_count.keys()):
            log(u'  * %s: %d' % (srcMod.s,mod_count[srcMod]))
        self.mod_count = {}

    def _srcMods(self,log):
        """Logs the Source mods for this patcher - patcher must have `srcs`
        attribute otherwise an AttributeError will be raised."""
        log(self.__class__.modsHeader)
        for mod in self.srcs:
            log(u'* ' + mod.s)

# Patchers: 40 ----------------------------------------------------------------
class SpecialPatcher(object):
    """Provides default group, scan and edit orders."""
    group = _(u'Special')
    scanOrder = 40
    editOrder = 40

    def scan_more(self,modFile,record,bashTags):
        if modFile.GName in self.srcs:
            self.scan(modFile,record,bashTags)
        #Must check for "unloaded" conflicts that occur past the winning record
        #If any exist, they have to be scanned
        for conflict in record.Conflicts(True):
            if conflict != record:
                mod = conflict.GetParentMod()
                if mod.GName in self.srcs:
                    tags = bosh.modInfos[mod.GName].getBashTags()
                    self.scan(mod,conflict,tags)
            else: return
