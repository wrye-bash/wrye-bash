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

"""This module contains the oblivion importer patcher classes."""
import collections
import operator
import re
# Internal
from ... import bosh # for modInfos
from ... import load_order
from ...bush import game # for Name patcher
from ...bolt import GPath, MemorySet
from ...brec import MreRecord, MelObject
from ...cint import ValidateDict, ValidateList, FormID, validTypes, \
    getattr_deep, setattr_deep
from ..base import AImportPatcher
from ...parsers import ActorFactions, CBash_ActorFactions, FactionRelations, \
    CBash_FactionRelations, FullNames, CBash_FullNames, ItemStats, \
    CBash_ItemStats, SpellRecords, CBash_SpellRecords, LoadFactory, ModFile
from .base import ImportPatcher, CBash_ImportPatcher

class _SimpleImporter(ImportPatcher):
    """For lack of a better name - common methods of a bunch of importers.
    :type rec_attrs: dict[str, tuple]"""
    rec_attrs = {}
    long_types = None

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(_SimpleImporter, self).initPatchFile(patchFile, loadMods)
        #--(attribute-> value) dicts keyed by long fid.
        self.id_data = collections.defaultdict(dict)
        self.srcClasses = set() #--Record classes actually provided by src
        # mods/files.
        self.classestemp = set()
        #--Type Fields
        self.recAttrs_class = {MreRecord.type_class[recType]: attrs for
                               recType, attrs in self.rec_attrs.iteritems()}
        #--Needs Longs
        self.longTypes = set(self.__class__.long_types or self.rec_attrs)

    def _init_data_loop(self, mapper, recClass, srcFile, srcMod, temp_id_data):
        recAttrs = self.recAttrs_class[recClass]
        for record in srcFile.tops[recClass.classType].getActiveRecords():
            fid = mapper(record.fid)
            temp_id_data[fid] = dict(
                (attr, record.__getattribute__(attr)) for attr in recAttrs)

    def initData(self, progress):
        """Common initData pattern.

        Used in KFFZPatcher, DeathItemPatcher, SoundPatcher, ImportScripts.
        Adding _init_data_loop absorbed GraphicsPatcher also.
        """
        if not self.isActive: return
        id_data = self.id_data
        loadFactory = LoadFactory(False, *self.recAttrs_class.keys())
        longTypes = self.longTypes & set(
            x.classType for x in self.recAttrs_class)
        progress.setFull(len(self.srcs))
        cachedMasters = {}
        for index,srcMod in enumerate(self.srcs):
            temp_id_data = {}
            if srcMod not in bosh.modInfos: continue
            srcInfo = bosh.modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            masters = srcInfo.header.masters
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass in self.recAttrs_class:
                if recClass.classType not in srcFile.tops: continue
                self.srcClasses.add(recClass)
                self.classestemp.add(recClass)
                self._init_data_loop(mapper, recClass, srcFile, srcMod,
                                     temp_id_data)
            for master in masters:
                if not master in bosh.modInfos: continue # or break filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = bosh.modInfos[master]
                    masterFile = ModFile(masterInfo,loadFactory)
                    masterFile.load(True)
                    masterFile.convertToLongFids(longTypes)
                    cachedMasters[master] = masterFile
                mapper = masterFile.getLongMapper()
                for recClass in self.recAttrs_class:
                    if recClass.classType not in masterFile.tops: continue
                    if recClass not in self.classestemp: continue
                    for record in masterFile.tops[
                        recClass.classType].getActiveRecords():
                        fid = mapper(record.fid)
                        if fid not in temp_id_data: continue
                        for attr, value in temp_id_data[fid].iteritems():
                            if value == record.__getattribute__(attr): continue
                            else:
                                id_data[fid][attr] = value
            progress.plus()
        self.longTypes = self.longTypes & set(
            x.classType for x in self.srcClasses)
        self.isActive = bool(self.srcClasses)

    def scanModFile(self, modFile, progress):
        """Identical scanModFile() pattern of :

            GraphicsPatcher, KFFZPatcher, DeathItemPatcher, ImportScripts,
            SoundPatcher.
        """
        if not self.isActive: return
        id_data = self.id_data
        mapper = modFile.getLongMapper()
        if self.longTypes:
            modFile.convertToLongFids(self.longTypes)
        for recClass in self.srcClasses:
            if recClass.classType not in modFile.tops: continue
            patchBlock = getattr(self.patchFile, recClass.classType)
            for record in modFile.tops[recClass.classType].getActiveRecords():
                fid = record.fid
                if not record.longFids: fid = mapper(fid)
                if fid not in id_data: continue
                for attr, value in id_data[fid].iteritems():
                    if record.__getattribute__(attr) != value:
                        patchBlock.setRecord(record.getTypeCopy(mapper))
                        break

    def _inner_loop(self, keep, records, top_mod_rec, type_count):
        """Most common pattern for the internal buildPatch() loop.

        In:
            KFFZPatcher, DeathItemPatcher, ImportScripts, SoundPatcher
        """
        id_data, set_id_data = self.id_data, set(self.id_data)
        for record in records:
            fid = record.fid
            if fid not in set_id_data: continue
            for attr, value in id_data[fid].iteritems():
                if record.__getattribute__(attr) != value: break
            else: continue
            for attr, value in id_data[fid].iteritems():
                record.__setattr__(attr, value)
            keep(fid)
            type_count[top_mod_rec] += 1

    def buildPatch(self, log, progress, types=None):
        """Common buildPatch() pattern of:

            GraphicsPatcher, ActorImporter, KFFZPatcher, DeathItemPatcher,
            ImportScripts, SoundPatcher
        Consists of a type selection loop which could be rewritten to support
        more patchers (maybe using filter()) and an inner loop that should be
        provided by a patcher specific, _inner_loop() method.
        Adding `types` parameter absorbed ImportRelations and ImportFactions.
        """
        if not self.isActive: return
        modFileTops = self.patchFile.tops
        keep = self.patchFile.getKeeper()
        type_count = collections.defaultdict(int)
        types = filter(lambda x: x in modFileTops,
                   types if types else map(lambda x: x.classType, self.srcClasses))
        for top_mod_rec in types:
            records = modFileTops[top_mod_rec].records
            self._inner_loop(keep, records, top_mod_rec, type_count)
        self.id_data.clear() # cleanup to save memory
        # Log
        self._patchLog(log,type_count)

class _RecTypeModLogging(CBash_ImportPatcher):
    """Import patchers that log type -> [mod-> count]"""
    listSrcs = True # whether or not to list sources
    logModRecs = u'* ' + _(u'Modified %(type)s Records: %(count)d')
    logMsg = u'\n=== ' + _(u'Modified Records')

    def initPatchFile(self,patchFile,loadMods):
        super(_RecTypeModLogging, self).initPatchFile(patchFile,loadMods)
        self.mod_count = collections.defaultdict(
            lambda: collections.defaultdict(int))
        self.fid_attr_value = collections.defaultdict(dict) # used in some

    def _clog(self, log):
        """Used in: CBash_SoundPatcher, CBash_ImportScripts,
        CBash_ActorImporter, CBash_GraphicsPatcher. Adding
        AImportPatcher.srcsHeader attribute absorbed CBash_NamesPatcher and
        CBash_StatsPatcher. Adding logModRecs, listSrcs class variables
        absorbs CBash_ImportFactions and CBash_ImportInventory.
        """
        # TODO(ut): remove logModRecs - not yet though - adds noise to the
        # patch comparisons
        mod_count = self.mod_count
        if self.__class__.listSrcs:
            self._srcMods(log)
            log(self.__class__.logMsg)
        for group_type in sorted(mod_count.keys()):
            log(self.__class__.logModRecs % {'type': u'%s ' % group_type,
                              'count': sum(mod_count[group_type].values())})
            for srcMod in load_order.get_ordered(mod_count[group_type].keys()):
                log(u'  * %s: %d' % (srcMod.s, mod_count[group_type][srcMod]))
        self.mod_count = collections.defaultdict(
                lambda: collections.defaultdict(int))

    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        attr_value = record.ConflictDetails(self.class_attrs[record._Type])
        if not attr_value: return
        if not ValidateDict(attr_value, self.patchFile):
            self.patchFile.patcher_mod_skipcount[self.name][
                modFile.GName] += 1
            return
        self.fid_attr_value[record.fid].update(attr_value)

# Patchers: 20 ----------------------------------------------------------------
class _ACellImporter(AImportPatcher):
    """Merges changes to cells (climate, lighting, and water.)"""
    text = _(u"Import cells (climate, lighting, and water) from source mods.")
    tip = text
    name = _(u'Import Cells')

class CellImporter(_ACellImporter, ImportPatcher):
    autoKey = game.cellAutoKeys
    logMsg = _(u'Cells/Worlds Patched')

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(CellImporter, self).initPatchFile(patchFile,loadMods)
        self.cellData = collections.defaultdict(dict)
        # TODO: docs: recAttrs vs tag_attrs - extra in PBash:
        # 'unused1','unused2','unused3'
        self.recAttrs = game.cellRecAttrs # dict[unicode, tuple[str]]
        self.recFlags = game.cellRecFlags # dict[unicode, str]

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('CELL','WRLD',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('CELL','WRLD',) if self.isActive else ()

    def initData(self,progress):
        """Get cells from source files."""
        if not self.isActive: return
        cellData = self.cellData
        # cellData['Maps'] = {}
        def importCellBlockData(cellBlock):
            if not cellBlock.cell.flags1.ignored:
                fid = cellBlock.cell.fid
                for attr in attrs:
                    tempCellData[fid][attr] = cellBlock.cell.__getattribute__(
                        attr)
                for flag in flags:
                    tempCellData[fid + ('flags',)][
                        flag] = cellBlock.cell.flags.__getattr__(flag)
        def checkMasterCellBlockData(cellBlock):
            if not cellBlock.cell.flags1.ignored:
                fid = cellBlock.cell.fid
                if fid not in tempCellData: return
                for attr in attrs:
                    master_attr = cellBlock.cell.__getattribute__(attr)
                    if tempCellData[fid][attr] != master_attr:
                        cellData[fid][attr] = tempCellData[fid][attr]
                for flag in flags:
                    master_flag = cellBlock.cell.flags.__getattr__(flag)
                    if tempCellData[fid + ('flags',)][flag] != master_flag:
                        cellData[fid + ('flags',)][flag] = \
                            tempCellData[fid + ('flags',)][flag]
        loadFactory = LoadFactory(False,MreRecord.type_class['CELL'],
                                        MreRecord.type_class['WRLD'])
        progress.setFull(len(self.srcs))
        cachedMasters = {}
        for srcMod in self.srcs:
            if srcMod not in bosh.modInfos: continue
            # tempCellData maps long fids for cells in srcMod to dicts of
            # (attributes (among attrs) -> their values for this mod). It is
            # used to update cellData with cells that change those attributes'
            # values from the value in any of srcMod's masters.
            tempCellData = collections.defaultdict(dict)
            tempCellData['Maps'] = {} # unused !
            srcInfo = bosh.modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            srcFile.convertToLongFids(('CELL','WRLD'))
            cachedMasters[srcMod] = srcFile
            masters = srcInfo.header.masters
            bashTags = srcInfo.getBashTags()
            # print bashTags
            tags = bashTags & set(self.recAttrs)
            if not tags: continue
            attrs = set(reduce(# adds tuples together, then takes the set
                operator.add, (self.recAttrs[bashKey] for bashKey in tags)))
            flags = tuple(self.recFlags[bashKey] for bashKey in tags if
                          self.recFlags[bashKey] != u'')
            if 'CELL' in srcFile.tops:
                for cellBlock in srcFile.CELL.cellBlocks:
                    importCellBlockData(cellBlock)
            if 'WRLD' in srcFile.tops:
                for worldBlock in srcFile.WRLD.worldBlocks:
                    for cellBlock in worldBlock.cellBlocks:
                        importCellBlockData(cellBlock)
                    # if 'C.Maps' in bashTags:
                    #     if worldBlock.world.mapPath:
                    #         tempCellData['Maps'][worldBlock.world.fid] = worldBlock.world.mapPath
            for master in masters:
                if not master in bosh.modInfos: continue  # or break
                # filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = bosh.modInfos[master]
                    masterFile = ModFile(masterInfo,loadFactory)
                    masterFile.load(True)
                    masterFile.convertToLongFids(('CELL','WRLD'))
                    cachedMasters[master] = masterFile
                if 'CELL' in masterFile.tops:
                    for cellBlock in masterFile.CELL.cellBlocks:
                        checkMasterCellBlockData(cellBlock)
                if 'WRLD' in masterFile.tops:
                    for worldBlock in masterFile.WRLD.worldBlocks:
                        for cellBlock in worldBlock.cellBlocks:
                            checkMasterCellBlockData(cellBlock)
                        # if worldBlock.world.fid in tempCellData['Maps']:
                            # if worldBlock.world.mapPath != tempCellData['Maps'][worldBlock.world.fid]:
                                # cellData['Maps'][worldBlock.world.fid] = tempCellData['Maps'][worldBlock.world.fid]
            tempCellData = {}
            progress.plus()

    def scanModFile(self, modFile, progress): # scanModFile0
        """Add lists from modFile."""
        if not self.isActive or (
                'CELL' not in modFile.tops and 'WRLD' not in modFile.tops):
            return
        cellData = self.cellData
        patchCells = self.patchFile.CELL
        patchWorlds = self.patchFile.WRLD
        modFile.convertToLongFids(('CELL','WRLD'))
        if 'CELL' in modFile.tops:
            for cellBlock in modFile.CELL.cellBlocks:
                if cellBlock.cell.fid in cellData:
                    patchCells.setCell(cellBlock.cell)
        if 'WRLD' in modFile.tops:
            for worldBlock in modFile.WRLD.worldBlocks:
                for cellBlock in worldBlock.cellBlocks:
                    if cellBlock.cell.fid in cellData:
                        patchWorlds.setWorld(worldBlock.world)
                        patchWorlds.id_worldBlocks[
                            worldBlock.world.fid].setCell(cellBlock.cell)
                # if worldBlock.world.fid in cellData['Maps']:
                    # patchWorlds.setWorld(worldBlock.world)

    def buildPatch(self,log,progress): # buildPatch0
        """Adds merged lists to patchfile."""
        def handlePatchCellBlock(patchCellBlock):
            modified=False
            for attr,value in cellData[patchCellBlock.cell.fid].iteritems():
                if patchCellBlock.cell.__getattribute__(attr) != value:
                    patchCellBlock.cell.__setattr__(attr, value)
                    modified=True
            for flag, value in cellData[
                        patchCellBlock.cell.fid + ('flags',)].iteritems():
                if patchCellBlock.cell.flags.__getattr__(flag) != value:
                    patchCellBlock.cell.flags.__setattr__(flag, value)
                    modified=True
            if modified:
                patchCellBlock.cell.setChanged()
                keep(patchCellBlock.cell.fid)
            return modified
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        cellData, count = self.cellData, collections.defaultdict(int)
        for cellBlock in self.patchFile.CELL.cellBlocks:
            if cellBlock.cell.fid in cellData and handlePatchCellBlock(cellBlock):
                count[cellBlock.cell.fid[0]] += 1
        for worldBlock in self.patchFile.WRLD.worldBlocks:
            keepWorld = False
            for cellBlock in worldBlock.cellBlocks:
                if cellBlock.cell.fid in cellData and handlePatchCellBlock(
                        cellBlock):
                    count[cellBlock.cell.fid[0]] += 1
                    keepWorld = True
            # if worldBlock.world.fid in cellData['Maps']:
                # if worldBlock.world.mapPath != cellData['Maps'][worldBlock.world.fid]:
                    # print worldBlock.world.mapPath
                    # worldBlock.world.mapPath = cellData['Maps'][worldBlock.world.fid]
                    # print worldBlock.world.mapPath
                    # worldBlock.world.setChanged()
                    # keepWorld = True
            if keepWorld:
                keep(worldBlock.world.fid)
        self.cellData.clear()
        self._patchLog(log, count)

    def _plog(self,log,count): # type 1 but for logMsg % sum(count.values())...
        log(self.__class__.logMsg)
        for srcMod in load_order.get_ordered(count.keys()):
            log(u'* %s: %d' % (srcMod.s,count[srcMod]))

class CBash_CellImporter(_ACellImporter,CBash_ImportPatcher):
    autoKey = {u'C.Climate', u'C.Light', u'C.Water', u'C.Owner', u'C.Name',
               u'C.RecordFlags', u'C.Music'}  #,u'C.Maps'
    logMsg = u'* ' + _(u'Cells/Worlds Patched') + u': %d'

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(CBash_CellImporter, self).initPatchFile(patchFile,loadMods)
        if not self.isActive: return
        self.fid_attr_value = collections.defaultdict(dict)
        self.tag_attrs = {
            u'C.Climate': ('climate','IsBehaveLikeExterior'),
            u'C.Music': ('musicType',),
            u'C.Name': ('full',),
            u'C.Owner': ('owner','rank','globalVariable','IsPublicPlace'),
            u'C.Water': ('water','waterHeight','IsHasWater'),
            u'C.Light': ('ambientRed','ambientGreen','ambientBlue',
                        'directionalRed','directionalGreen','directionalBlue',
                        'fogRed','fogGreen','fogBlue',
                        'fogNear','fogFar','directionalXY','directionalZ',
                        'directionalFade','fogClip'),
            u'C.RecordFlags': ('flags1',), # Yes seems funky but thats the way it is
            }

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CELLS']

    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        for bashKey in bashTags & self.autoKey:
            attr_value = record.ConflictDetails(self.tag_attrs[bashKey])
            if not ValidateDict(attr_value, self.patchFile):
                self.patchFile.patcher_mod_skipcount[self.name][
                    modFile.GName] += 1
                continue
            self.fid_attr_value[record.fid].update(attr_value)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        prev_attr_value = self.fid_attr_value.get(recordId,None)
        if prev_attr_value:
            cur_attr_value = dict(
                (attr, getattr(record, attr)) for attr in prev_attr_value)
            if cur_attr_value != prev_attr_value:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_attr_value.iteritems():
                        setattr(override,attr,value)
                    self.mod_count[modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _AGraphicsPatcher(AImportPatcher):
    """Merges changes to graphics (models and icons)."""
    name = _(u'Import Graphics')
    text = _(u"Import graphics (models, icons, etc.) from source mods.")
    tip = text
    autoKey = {u'Graphics'}

class GraphicsPatcher(_SimpleImporter, _AGraphicsPatcher):
    rec_attrs = game.graphicsTypes
    long_types = game.graphicsLongsTypes

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(GraphicsPatcher, self).initPatchFile(patchFile, loadMods)
        #--Type Fields
        # Not available in Skyrim yet LAND, PERK, PACK, QUST, RACE, SCEN, REFR, REGN
        # Look into why these records are not included, are they part of other patchers?
        # no 'model' attr: 'EYES', 'AVIF', 'MICN',
        # Would anyone ever change these: 'PERK', 'QUST', 'SKIL', 'REPU'
        # for recClass in (MreRecord.type_class[x] for x in game.graphicsIconOnlyRecs):
        #     recAttrs_class[recClass] = ('iconPath',)
        # no 'iconPath' attr: 'ADDN', 'ANIO', 'ARTO', 'BPTD', 'CAMS', 'CLMT',
        # 'CONT', 'EXPL', 'HAZD', 'HPDT', 'IDLM',  'IPCT', 'MATO', 'MSTT',
        # 'PROJ', 'TACT', 'TREE',
        # for recClass in (MreRecord.type_class[x] for x in game.graphicsModelOnlyRecs):
        #     recAttrs_class[recClass] = ('model',)
        # no'model' and 'iconpath' attr: 'COBJ', 'HAIR', 'NOTE', 'CCRD', 'CHIP', 'CMNY', 'IMOD',
        # Is 'RACE' included in race patcher?
        # for recClass in (MreRecord.type_class[x] for x in game.graphicsIconModelRecs):
        #     recAttrs_class[recClass] = ('iconPath','model',)
        # Why does Graphics have a seperate entry for Fids when SoundPatcher does not?
        # for recClass in (MreRecord.type_class[x] for x in ('MGEF',)):
        #     recFidAttrs_class[recClass] = game.graphicsMgefFidAttrs
        self.recFidAttrs_class = {MreRecord.type_class[recType]: attrs for
                        recType, attrs in game.graphicsFidTypes.iteritems()}

    def _init_data_loop(self, mapper, recClass, srcFile, srcMod, temp_id_data):
        recAttrs = self.recAttrs_class[recClass]
        recFidAttrs = self.recFidAttrs_class.get(recClass, None)
        for record in srcFile.tops[recClass.classType].getActiveRecords():
            fid = mapper(record.fid)
            if recFidAttrs:
                attr_fidvalue = dict(
                    (attr, record.__getattribute__(attr)) for attr in
                    recFidAttrs)
                for fidvalue in attr_fidvalue.values():
                    if fidvalue and (fidvalue[0] is None or fidvalue[
                        0] not in self.patchFile.loadSet):
                        # Ignore the record. Another option would be
                        # to just ignore the attr_fidvalue result
                        self.patchFile.patcher_mod_skipcount[self.name][
                            srcMod] += 1
                        break
                else:
                    temp_id_data[fid] = dict(
                        (attr, record.__getattribute__(attr)) for attr in
                        recAttrs)
                    temp_id_data[fid].update(attr_fidvalue)
            else:
                temp_id_data[fid] = dict(
                    (attr, record.__getattribute__(attr)) for attr in recAttrs)

    def _inner_loop(self, keep, records, top_mod_rec, type_count):
        id_data = self.id_data
        for record in records:
            fid = record.fid
            if fid not in id_data: continue
            for attr, value in id_data[fid].iteritems():
                if isinstance(record.__getattribute__(attr),
                              basestring) and isinstance(value, basestring):
                    if record.__getattribute__(attr).lower() != value.lower():
                        break
                    continue
                elif attr in game.graphicsModelAttrs:
                    try:
                        if record.__getattribute__(
                                attr).modPath.lower() != value.modPath.lower():
                            break
                        continue
                    except: break  # assume they are not equal (ie they
                        # aren't __both__ NONE)
                if record.__getattribute__(attr) != value: break
            else: continue
            for attr, value in id_data[fid].iteritems():
                record.__setattr__(attr, value)
            keep(fid)
            type_count[top_mod_rec] += 1

class CBash_GraphicsPatcher(_RecTypeModLogging, _AGraphicsPatcher):

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(CBash_GraphicsPatcher, self).initPatchFile(patchFile, loadMods)
        if not self.isActive: return
        class_attrs = self.class_attrs = {}
        model = ('modPath','modb','modt_p')
        icon = ('iconPath',)
        class_attrs['BSGN'] = icon
        class_attrs['LSCR'] = icon
        class_attrs['CLAS'] = icon
        class_attrs['LTEX'] = icon
        class_attrs['REGN'] = icon
        class_attrs['ACTI'] = model
        class_attrs['DOOR'] = model
        class_attrs['FLOR'] = model
        class_attrs['FURN'] = model
        class_attrs['GRAS'] = model
        class_attrs['STAT'] = model
        class_attrs['ALCH'] = icon + model
        class_attrs['AMMO'] = icon + model
        class_attrs['APPA'] = icon + model
        class_attrs['BOOK'] = icon + model
        class_attrs['INGR'] = icon + model
        class_attrs['KEYM'] = icon + model
        class_attrs['LIGH'] = icon + model
        class_attrs['MISC'] = icon + model
        class_attrs['SGST'] = icon + model
        class_attrs['SLGM'] = icon + model
        class_attrs['WEAP'] = icon + model
        class_attrs['TREE'] = icon + model

        class_attrs['ARMO'] = ('maleBody_list',
                               'maleWorld_list',
                               'maleIconPath',
                               'femaleBody_list',
                               'femaleWorld_list',
                               'femaleIconPath', 'flags')
        class_attrs['CLOT'] = class_attrs['ARMO']

        class_attrs['CREA'] = ('bodyParts', 'nift_p')
        class_attrs['MGEF'] = icon + model + ('effectShader','enchantEffect','light')
        class_attrs['EFSH'] = ('fillTexturePath','particleTexturePath','flags','memSBlend','memBlendOp',
                               'memZFunc','fillRed','fillGreen','fillBlue','fillAIn','fillAFull',
                               'fillAOut','fillAPRatio','fillAAmp','fillAFreq','fillAnimSpdU',
                               'fillAnimSpdV','edgeOff','edgeRed','edgeGreen','edgeBlue','edgeAIn',
                               'edgeAFull','edgeAOut','edgeAPRatio','edgeAAmp','edgeAFreq',
                               'fillAFRatio','edgeAFRatio','memDBlend','partSBlend','partBlendOp',
                               'partZFunc','partDBlend','partBUp','partBFull','partBDown',
                               'partBFRatio','partBPRatio','partLTime','partLDelta','partNSpd',
                               'partNAcc','partVel1','partVel2','partVel3','partAcc1','partAcc2',
                               'partAcc3','partKey1','partKey2','partKey1Time','partKey2Time',
                               'key1Red','key1Green','key1Blue','key2Red','key2Green','key2Blue',
                               'key3Red','key3Green','key3Blue','key1A','key2A','key3A',
                               'key1Time','key2Time','key3Time')

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['BSGN','LSCR','CLAS','LTEX','REGN','ACTI','DOOR','FLOR',
                'FURN','GRAS','STAT','ALCH','AMMO','APPA','BOOK','INGR',
                'KEYM','LIGH','MISC','SGST','SLGM','WEAP','TREE','ARMO',
                'CLOT','CREA','MGEF','EFSH']

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        prev_attr_value = self.fid_attr_value.get(record.fid,None)
        if prev_attr_value:
            cur_attr_value = dict(
                (attr, getattr(record, attr)) for attr in prev_attr_value)
            if cur_attr_value != prev_attr_value:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_attr_value.iteritems():
                        setattr(override,attr,value)
                    self.mod_count[record._Type][modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _AActorImporter(AImportPatcher):
    """Merges changes to actors."""
    name = _(u'Import Actors')
    text = _(u"Import Actor components from source mods.")
    tip = text
    autoKey = {u'Actors.AIData', u'Actors.Stats', u'Actors.ACBS', u'NPC.Class',
               u'Actors.CombatStyle', u'Creatures.Blood', u'NPC.Race',
               u'Actors.Skeleton'}

class ActorImporter(_SimpleImporter, _AActorImporter):
    # note peculiar mapping of record type to dictionaries[tag, attributes]
    rec_attrs = {'NPC_':{
        u'Actors.AIData': ('aggression', 'confidence', 'energyLevel',
                           'responsibility', 'services', 'trainSkill',
                           'trainLevel'),
        u'Actors.Stats': ('skills','health','attributes'),
        u'Actors.ACBS': (('baseSpell', 'fatigue', 'level', 'calcMin',
                          'calcMax', 'flags.autoCalc', 'flags.pcLevelOffset'),
                         'barterGold', 'flags.female', 'flags.essential',
                         'flags.respawn', 'flags.noLowLevel', 'flags.noRumors',
                         'flags.summonable', 'flags.noPersuasion',
                         'flags.canCorpseCheck',),
        #u'Actors.ACBS': ('baseSpell','fatigue','barterGold','level',
        #                 'calcMin','calcMax','flags'),
        u'NPC.Class': ('iclass',),
        u'NPC.Race': ('race',),
        u'Actors.CombatStyle': ('combatStyle',),
        u'Creatures.Blood': (),
        u'Actors.Skeleton': ('model',),
        },
        'CREA':{
            u'Actors.AIData': ('aggression', 'confidence', 'energyLevel',
                               'responsibility', 'services', 'trainSkill',
                               'trainLevel'),
            u'Actors.Stats': ('combat','magic', 'stealth', 'soul', 'health',
                              'attackDamage', 'strength', 'intelligence',
                              'willpower', 'agility', 'speed', 'endurance',
                              'personality','luck'),
            u'Actors.ACBS': (('baseSpell', 'fatigue', 'level', 'calcMin',
                              'calcMax', 'flags.pcLevelOffset',), 'barterGold',
                             'flags.biped', 'flags.essential',
                             'flags.weaponAndShield', 'flags.respawn',
                             'flags.swims', 'flags.flies', 'flags.walks',
                             'flags.noLowLevel', 'flags.noBloodSpray',
                             'flags.noBloodDecal', 'flags.noHead',
                             'flags.noRightArm', 'flags.noLeftArm',
                             'flags.noCombatInWater', 'flags.noShadow',
                             'flags.noCorpseCheck',),
            #u'Actors.ACBS': ('baseSpell','fatigue','barterGold','level',
            #                 'calcMin','calcMax','flags'),
            u'NPC.Class': (),
            u'NPC.Race': (),
            u'Actors.CombatStyle': ('combatStyle',),
            u'Creatures.Blood': ('bloodSprayPath','bloodDecalPath'),
            u'Actors.Skeleton': ('model',),
        }
    }

    #--Patch Phase ------------------------------------------------------------
    def initData(self,progress):
        """Get actors from source files."""
        if not self.isActive: return
        id_data = self.id_data
        loadFactory = LoadFactory(False, *self.recAttrs_class.keys())
        longTypes = self.longTypes & set(
            x.classType for x in self.recAttrs_class)
        progress.setFull(len(self.srcs))
        cachedMasters = {}
        for index,srcMod in enumerate(self.srcs):
            temp_id_data = {}
            if srcMod not in bosh.modInfos: continue
            srcInfo = bosh.modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            masters = srcInfo.header.masters
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass in self.recAttrs_class:
                if recClass.classType not in srcFile.tops: continue
                self.srcClasses.add(recClass)
                self.classestemp.add(recClass)
                self._init_data_loop(mapper, recClass, srcFile, srcMod,
                                     temp_id_data)
            for master in masters:
                if not master in bosh.modInfos: continue # or break filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = bosh.modInfos[master]
                    masterFile = ModFile(masterInfo,loadFactory)
                    masterFile.load(True)
                    masterFile.convertToLongFids(longTypes)
                    cachedMasters[master] = masterFile
                mapper = masterFile.getLongMapper()
                for recClass in self.recAttrs_class:
                    if recClass.classType not in masterFile.tops: continue
                    if recClass not in self.classestemp: continue
                    for record in masterFile.tops[
                        recClass.classType].getActiveRecords():
                        fid = mapper(record.fid)
                        if fid not in temp_id_data: continue
                        for attr, value in temp_id_data[fid].iteritems():
                            if isinstance(attr,basestring):
                                if value == reduce(getattr, attr.split('.'),
                                                   record):
                                    continue
                                else:
                                    id_data[fid][attr] = value
                            elif isinstance(attr,(list,tuple,set)):
                                temp_values = {}
                                keep = False
                                for subattr in attr:
                                    if value[subattr] != reduce(
                                            getattr,subattr.split('.'),record):
                                        keep = True
                                    temp_values[subattr] = value[subattr]
                                if keep:
                                    id_data[fid].update(temp_values)
            progress.plus()
        self.longTypes = self.longTypes & set(
            x.classType for x in self.srcClasses)
        self.isActive = bool(self.srcClasses)

    def _init_data_loop(self, mapper, recClass, srcFile, srcMod, temp_id_data):
        mod_tags = srcFile.fileInfo.getBashTags()
        common_tags = set(self.recAttrs_class[recClass]) & mod_tags
        attrs = set(reduce(operator.add,
            (self.recAttrs_class[recClass][tag] for tag in common_tags)))
        for record in srcFile.tops[recClass.classType].getActiveRecords():
            fid = mapper(record.fid)
            temp_id_data[fid] = dict()
            for attr in attrs:
                if isinstance(attr, basestring):
                    temp_id_data[fid][attr] = reduce(getattr, attr.split('.'),
                                                     record)
                elif isinstance(attr, (list, tuple, set)):
                    temp_id_data[fid][attr] = dict(
                        (subattr, reduce(getattr, subattr.split('.'), record))
                        for subattr in attr)

    def scanModFile(self, modFile, progress): # scanModFile1: reduce(...)
        """Scan mod file against source data."""
        if not self.isActive: return
        id_data = self.id_data
        mapper = modFile.getLongMapper()
        if self.longTypes:
            modFile.convertToLongFids(self.longTypes)
        for recClass in self.srcClasses:
            type = recClass.classType
            if type not in modFile.tops: continue
            patchBlock = getattr(self.patchFile,type)
            for record in modFile.tops[type].getActiveRecords():
                fid = record.fid
                if not record.longFids: fid = mapper(fid)
                if fid not in id_data: continue
                for attr,value in id_data[fid].iteritems():
                    # OOPS: line below is the only diff from _scanModFile()
                    if reduce(getattr,attr.split('.'),record) != value:
                        patchBlock.setRecord(record.getTypeCopy(mapper))
                        break

    def _inner_loop(self, keep, records, top_mod_rec, type_count):
        id_data, set_id_data = self.id_data, set(self.id_data)
        for record in records:
            fid = record.fid
            if fid not in set_id_data: continue
            for attr, value in id_data[fid].iteritems():
                if reduce(getattr, attr.split('.'), record) != value: break
            else: continue
            for attr, value in id_data[fid].iteritems():
                # OOPS: line below is the only diff from base _inner_loop()
                setattr(reduce(getattr, attr.split('.')[:-1], record),
                        attr.split('.')[-1], value)
            keep(fid)
            type_count[top_mod_rec] += 1

class CBash_ActorImporter(_RecTypeModLogging, _AActorImporter):

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        super(CBash_ActorImporter, self).initPatchFile(patchFile, loadMods)
        if not self.isActive: return
        class_tag_attrs = self.class_tag_attrs = {}
        class_tag_attrs['NPC_'] = {
                u'Actors.AIData': ('aggression','confidence','energyLevel','responsibility','services','trainSkill','trainLevel'),
                u'Actors.Stats': ('armorer','athletics','blade','block','blunt','h2h','heavyArmor','alchemy',
                                 'alteration','conjuration','destruction','illusion','mysticism','restoration',
                                 'acrobatics','lightArmor','marksman','mercantile','security','sneak','speechcraft',
                                 'health',
                                 'strength','intelligence','willpower','agility','speed','endurance','personality','luck',),
                u'Actors.ACBS': (('baseSpell','fatigue','level','calcMin','calcMax','IsPCLevelOffset','IsAutoCalc',),
                                'barterGold','IsFemale','IsEssential','IsRespawn','IsNoLowLevel','IsNoRumors',
                                'IsSummonable','IsNoPersuasion','IsCanCorpseCheck',
                                ),
                u'NPC.Class': ('iclass',),
                u'NPC.Race': ('race',),
                u'Actors.CombatStyle': ('combatStyle',),
                u'Creatures.Blood': (),
                u'Actors.Skeleton': ('modPath','modb','modt_p'),
                }
        class_tag_attrs['CREA'] = {
                u'Actors.AIData': ('aggression','confidence','energyLevel','responsibility','services','trainSkill','trainLevel'),
                u'Actors.Stats': ('combat','magic','stealth','soulType','health','attackDamage','strength','intelligence','willpower',
                                 'agility','speed','endurance','personality','luck'),
                u'Actors.ACBS': (('baseSpell','fatigue','level','calcMin','calcMax','IsPCLevelOffset',),
                                'barterGold','IsBiped','IsEssential','IsWeaponAndShield','IsRespawn',
                                'IsSwims','IsFlies','IsWalks','IsNoLowLevel','IsNoBloodSpray','IsNoBloodDecal',
                                'IsNoHead','IsNoRightArm','IsNoLeftArm','IsNoCombatInWater','IsNoShadow',
                                'IsNoCorpseCheck',
                                ),
                u'NPC.Class': (),
                u'NPC.Race': (),
                u'Actors.CombatStyle': ('combatStyle',),
                u'Creatures.Blood': ('bloodSprayPath','bloodDecalPath'),
                u'Actors.Skeleton': ('modPath','modb','modt_p',),
                }

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CREA','NPC_']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        if modFile.GName == record.fid[0]: return
        for bashKey in bashTags & self.autoKey:
            attrs = self.class_tag_attrs[record._Type].get(bashKey, None)
            if attrs:
                attr_value = record.ConflictDetails(attrs)
                if not attr_value: continue
                if not ValidateDict(attr_value, self.patchFile):
                    self.patchFile.patcher_mod_skipcount[self.name][
                        modFile.GName] += 1
                    continue
                self.fid_attr_value[record.fid].update(attr_value)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        prev_attr_value = self.fid_attr_value.get(recordId,None)
        if prev_attr_value:
            cur_attr_value = dict((attr,getattr(record,attr)) for attr in prev_attr_value)
            if cur_attr_value != prev_attr_value:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_attr_value.iteritems():
                        setattr(override,attr,value)
                    self.mod_count[record._Type][modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _AKFFZPatcher(AImportPatcher):
    """Merges changes to actor animation lists."""
    name = _(u'Import Actors: Animations')
    text = _(u"Import Actor animations from source mods.")
    tip = text
    autoKey = {u'Actors.Anims'}

class KFFZPatcher(_SimpleImporter, _AKFFZPatcher):
    rec_attrs = dict((x, ('animations',)) for x in {'CREA', 'NPC_'})

class CBash_KFFZPatcher(CBash_ImportPatcher, _AKFFZPatcher):
    logMsg = u'* ' + _(u'Imported Animations') + u': %d'

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.id_animations = collections.defaultdict(list)

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CREA','NPC_']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        animations = self.id_animations[record.fid]
        animations.extend(
            [anim for anim in record.animations if anim not in animations])

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        if recordId in self.id_animations and record.animations != \
                self.id_animations[recordId]:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.animations = self.id_animations[recordId]
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _ANPCAIPackagePatcher(AImportPatcher):
    """Merges changes to the AI Packages of Actors."""
    name = _(u'Import Actors: AI Packages')
    text = _(u"Import Actor AI Package links from source mods.")
    tip = text
    autoKey = {u'Actors.AIPackages', u'Actors.AIPackagesForceAdd'}

class NPCAIPackagePatcher(ImportPatcher, _ANPCAIPackagePatcher):
    logMsg = _(u'AI Package Lists Changed') + u': %d'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(NPCAIPackagePatcher, self).initPatchFile(patchFile, loadMods)
        # long_fid -> {'merged':list[long_fid], 'deleted':list[long_fid]}
        self.id_merged_deleted = {}
        self.longTypes = {'CREA', 'NPC_'}

    def _insertPackage(self, data, fid, index, pkg, recordData):
        if index == 0: data[fid]['merged'].insert(0, pkg)# insert as first item
        elif index == (len(recordData['merged']) - 1):
            data[fid]['merged'].append(pkg)  # insert as last item
        else:  # figure out a good spot to insert it based on next or last
            # recognized item (ugly ugly ugly)
            i = index - 1
            while i >= 0:
                if recordData['merged'][i] in data[fid]['merged']:
                    slot = data[fid]['merged'].index(
                        recordData['merged'][i]) + 1
                    data[fid]['merged'].insert(slot, pkg)
                    break
                i -= 1
            else:
                i = index + 1
                while i != len(recordData['merged']):
                    if recordData['merged'][i] in data[fid]['merged']:
                        slot = data[fid]['merged'].index(
                            recordData['merged'][i])
                        data[fid]['merged'].insert(slot, pkg)
                        break
                    i += 1

    def initData(self,progress):
        """Get data from source files."""
        if not self.isActive: return
        longTypes = self.longTypes
        loadFactory = LoadFactory(False,MreRecord.type_class['CREA'],
                                        MreRecord.type_class['NPC_'])
        progress.setFull(len(self.srcs))
        cachedMasters = {}
        mer_del = self.id_merged_deleted
        for index,srcMod in enumerate(self.srcs):
            tempData = {}
            if srcMod not in bosh.modInfos: continue
            srcInfo = bosh.modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            masters = srcInfo.header.masters
            bashTags = srcInfo.getBashTags()
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass in (MreRecord.type_class[x] for x in ('NPC_','CREA')):
                if recClass.classType not in srcFile.tops: continue
                for record in srcFile.tops[
                    recClass.classType].getActiveRecords():
                    fid = mapper(record.fid)
                    tempData[fid] = list(record.aiPackages)
            for master in reversed(masters):
                if not master in bosh.modInfos: continue # or break filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = bosh.modInfos[master]
                    masterFile = ModFile(masterInfo,loadFactory)
                    masterFile.load(True)
                    masterFile.convertToLongFids(longTypes)
                    cachedMasters[master] = masterFile
                mapper = masterFile.getLongMapper()
                blocks = (MreRecord.type_class[x] for x in ('NPC_', 'CREA'))
                for block in blocks:
                    if block.classType not in srcFile.tops: continue
                    if block.classType not in masterFile.tops: continue
                    for record in masterFile.tops[
                        block.classType].getActiveRecords():
                        fid = mapper(record.fid)
                        if not fid in tempData: continue
                        if record.aiPackages == tempData[fid] and not \
                            u'Actors.AIPackagesForceAdd' in bashTags:
                            # if subrecord is identical to the last master
                            # then we don't care about older masters.
                            del tempData[fid]
                            continue
                        if fid in mer_del:
                            if tempData[fid] == mer_del[fid]['merged']:
                                continue
                        recordData = {'deleted':[],'merged':tempData[fid]}
                        for pkg in list(record.aiPackages):
                            if not pkg in tempData[fid]:
                                recordData['deleted'].append(pkg)
                        if not fid in mer_del:
                            mer_del[fid] = recordData
                        else:
                            for pkg in recordData['deleted']:
                                if pkg in mer_del[fid]['merged']:
                                    mer_del[fid]['merged'].remove(pkg)
                                mer_del[fid]['deleted'].append(pkg)
                            if mer_del[fid]['merged'] == []:
                                for pkg in recordData['merged']:
                                    if pkg in mer_del[fid]['deleted'] and not \
                                      u'Actors.AIPackagesForceAdd' in bashTags:
                                        continue
                                    mer_del[fid]['merged'].append(pkg)
                                continue
                            for index, pkg in enumerate(recordData['merged']):
                                if not pkg in mer_del[fid]['merged']:# so needs
                                    #  to be added... (unless deleted that is)
                                    # find the correct position to add and add.
                                    if pkg in mer_del[fid]['deleted'] and not \
                                      u'Actors.AIPackagesForceAdd' in bashTags:
                                        continue  # previously deleted
                                    self._insertPackage(mer_del, fid, index,
                                                        pkg, recordData)
                                    continue # Done with this package
                                elif index == mer_del[fid]['merged'].index(
                                        pkg) or (
                                    len(recordData['merged']) - index) == (
                                    len(mer_del[fid]['merged']) - mer_del[fid][
                                    'merged'].index(pkg)):
                                    continue  # pkg same in both lists.
                                else:  # this import is later loading so we'll
                                    #  assume it is better order
                                    mer_del[fid]['merged'].remove(pkg)
                                    self._insertPackage(mer_del, fid, index,
                                                        pkg, recordData)
            progress.plus()

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('NPC_','CREA',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('NPC_','CREA',) if self.isActive else ()

    def scanModFile(self, modFile, progress): # scanModFile2: loop, LongTypes..
        """Add record from modFile."""
        if not self.isActive: return
        merged_deleted = self.id_merged_deleted
        mapper = modFile.getLongMapper()
        for rec_type in ('NPC_','CREA'):
            patchBlock = getattr(self.patchFile,rec_type)
            for record in getattr(modFile,rec_type).getActiveRecords():
                fid = mapper(record.fid)
                if not fid in merged_deleted: continue
                if list(record.aiPackages) != merged_deleted[fid]['merged']:
                    patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress): # buildPatch1:no modFileTops, for type..
        """Applies delta to patchfile."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        merged_deleted = self.id_merged_deleted
        mod_count = collections.defaultdict(int)
        for rec_type in ('NPC_','CREA'):
            for record in getattr(self.patchFile,rec_type).records:
                fid = record.fid
                if not fid in merged_deleted: continue
                changed = False
                if record.aiPackages != merged_deleted[fid]['merged']:
                    record.aiPackages = merged_deleted[fid]['merged']
                    changed = True
                if changed:
                    keep(record.fid)
                    mod = record.fid[0]
                    mod_count[mod] += 1
        self.id_merged_deleted.clear()
        self._patchLog(log,mod_count)

    def _plog(self, log, mod_count): self._plog1(log, mod_count)

class CBash_NPCAIPackagePatcher(CBash_ImportPatcher, _ANPCAIPackagePatcher):
    scanRequiresChecked = False
    logMsg = u'* ' + _(u'AI Package Lists Changed') + u': %d'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.previousPackages = {}
        self.mergedPackageList = {}

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CREA','NPC_']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        aiPackages = record.aiPackages
        if not ValidateList(aiPackages, self.patchFile):
            self.patchFile.patcher_mod_skipcount[self.name][modFile.GName] += 1
            return

        recordId = record.fid
        newPackages = MemorySet(aiPackages)
        self.previousPackages.setdefault(recordId, {})[
            modFile.GName] = newPackages

        if modFile.GName in self.srcs:
            masterPackages = self.previousPackages[recordId].get(recordId[0],
                                                                 None)
            # can't just do "not masterPackages ^ newPackages" since the
            # order may have changed
            if masterPackages is not None and masterPackages == newPackages:
                return
            mergedPackages = self.mergedPackageList.setdefault(recordId,
                                                               newPackages)
            if newPackages == mergedPackages: return  # same as the current
            # list, just skip.
            for master in reversed(modFile.TES4.masters):
                masterPath = GPath(master)
                masterPackages = self.previousPackages[recordId].get(
                    masterPath, None)
                if masterPackages is None: continue

                # Get differences from master
                added = newPackages - masterPackages
                sameButReordered = masterPackages & newPackages
                prevDeleted = MemorySet(mergedPackages.discarded)
                newDeleted = masterPackages - newPackages

                # Merge those changes into mergedPackages
                mergedPackages |= newPackages
                if u'Actors.AIPackagesForceAdd' not in bashTags:
                    prevDeleted -= newPackages
                prevDeleted |= newDeleted
                mergedPackages -= prevDeleted
                self.mergedPackageList[recordId] = mergedPackages
                break

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        if recordId in self.mergedPackageList:
            mergedPackages = list(self.mergedPackageList[recordId])
            if record.aiPackages != mergedPackages:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    try:
                        override.aiPackages = mergedPackages
                    except:
                        newMergedPackages = []
                        for pkg in mergedPackages:
                            if not pkg[0] is None: newMergedPackages.append(
                                pkg)
                        override.aiPackages = newMergedPackages
                    self.mod_count[modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _ADeathItemPatcher(AImportPatcher):
    """Merges changes to actor death items."""
    name = _(u'Import Actors: Death Items')
    text = _(u"Import Actor death items from source mods.")
    tip = text
    autoKey = {u'Actors.DeathItem'}

class DeathItemPatcher(_SimpleImporter, _ADeathItemPatcher):
    rec_attrs = dict((x, ('deathItem',)) for x in {'CREA', 'NPC_'})

class CBash_DeathItemPatcher(CBash_ImportPatcher, _ADeathItemPatcher):
    logMsg = u'* ' + _(u'Imported Death Items') + u': %d'

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.id_deathItem = {}

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CREA','NPC_']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        deathitem = record.ConflictDetails(('deathItem',))
        if deathitem:
            if deathitem['deathItem'].ValidateFormID(self.patchFile):
                self.id_deathItem[record.fid] = deathitem['deathItem']
            else:
                # Ignore the record. Another option would be to just ignore
                # the invalid formIDs
                self.patchFile.patcher_mod_skipcount[self.name][
                    modFile.GName] += 1

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        if recordId in self.id_deathItem and record.deathItem != \
                self.id_deathItem[recordId]:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.deathItem = self.id_deathItem[recordId]
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

    def _clog(self,log): # type 2
        self._srcMods(log)
        super(CBash_DeathItemPatcher, self)._clog(log)

#------------------------------------------------------------------------------
class _AImportFactions(AImportPatcher):
    """Import factions to creatures and NPCs."""
    name = _(u'Import Factions')
    text = _(u"Import factions from source mods/files.")
    autoKey = {u'Factions'}

class ImportFactions(_SimpleImporter, _AImportFactions):
    logMsg = _(u'Refactioned Actors')
    srcsHeader = u'=== ' + _(u'Source Mods/Files')

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(ImportFactions, self).initPatchFile(patchFile, loadMods)
        self.activeTypes = []  #--Types ('CREA','NPC_') of data actually
        # provided by src mods/files.

    def initData(self,progress):
        """Get names from source files."""
        actorFactions = self._parse_sources(progress, parser=ActorFactions)
        if not actorFactions: return
        #--Finish
        id_factions= self.id_data
        for type,aFid_factions in actorFactions.type_id_factions.iteritems():
            if type not in ('CREA','NPC_'): continue
            self.activeTypes.append(type)
            for longid,factions in aFid_factions.iteritems():
                id_factions[longid] = factions
        self.isActive = bool(self.activeTypes)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return tuple(self.activeTypes) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return tuple(self.activeTypes) if self.isActive else()

    def scanModFile(self, modFile, progress): # scanModFile2
        """Scan modFile."""
        if not self.isActive: return
        id_factions = self.id_data
        mapper = modFile.getLongMapper()
        for type in self.activeTypes: # here differs from _scanModFile
            if type not in modFile.tops: continue
            patchBlock = getattr(self.patchFile,type)
            id_records = patchBlock.id_records
            for record in modFile.tops[type].getActiveRecords():
                fid = record.fid
                if not record.longFids: fid = mapper(fid)
                if fid in id_records: continue
                if fid not in id_factions: continue
                patchBlock.setRecord(record.getTypeCopy(mapper))

    def _inner_loop(self, keep, records, top_mod_rec, type_count):
        id_data, set_id_data = self.id_data, set(self.id_data)
        for record in records:
            fid = record.fid
            if fid not in set_id_data: continue
            newFactions = set(id_data[fid])
            curFactions = set((x.faction, x.rank) for x in record.factions)
            changed = newFactions - curFactions
            if not changed: continue
            doKeep = False
            for faction, rank in changed:
                for entry in record.factions:
                    if entry.faction == faction:
                        if entry.rank != rank:
                            entry.rank = rank
                            doKeep = True
                            keep(fid)
                        break
                else:
                    entry = MelObject()
                    entry.faction = faction
                    entry.rank = rank
                    entry.unused1 = 'ODB'
                    record.factions.append(entry)
                    doKeep = True
            if doKeep:
                record.factions = [x for x in record.factions if x.rank != -1]
                type_count[top_mod_rec] += 1
                keep(fid)

    def buildPatch(self, log, progress, types=None):
        super(ImportFactions, self).buildPatch(log, progress, self.activeTypes)

class CBash_ImportFactions(_RecTypeModLogging, _AImportFactions):
    listSrcs = False
    logModRecs = u'* ' + _(u'Refactioned %(type)s Records: %(count)d')

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(CBash_ImportFactions, self).initPatchFile(patchFile, loadMods)
        if not self.isActive: return
        self.id_factions = {}
        self.csvId_factions = {}

    def initData(self,group_patchers,progress):
        if not self.isActive: return
        CBash_ImportPatcher.initData(self,group_patchers,progress)
        actorFactions = self._parse_texts(CBash_ActorFactions, progress)
        #--Finish
        csvId_factions = self.csvId_factions
        for group, aFid_factions in \
                actorFactions.group_fid_factions.iteritems():
            if group not in ('CREA','NPC_'): continue
            for fid,factions in aFid_factions.iteritems():
                csvId_factions[fid] = factions

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CREA','NPC_']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        if modFile.GName == record.fid[0]: return
        factions = record.ConflictDetails(('factions_list',))
        if factions:
            masterRecord = self.patchFile.Current.LookupRecords(record.fid)[-1]
            masterFactions = masterRecord.factions_list
            masterDict = dict((x[0],x[1]) for x in masterFactions)
            # Initialize the factions list with what's in the master record
            self.id_factions.setdefault(record.fid, masterDict)
            # Only add/remove records if different than the master record
            thisFactions = factions['factions_list']
            masterFids = set([x[0] for x in masterFactions])
            thisFids = set([x[0] for x in thisFactions])
            removedFids = masterFids - thisFids
            addedFids = thisFids - masterFids
            # Add new factions
            self.id_factions[record.fid].update(
                dict((x[0], x[1]) for x in thisFactions if x[0] in addedFids))
            # Remove deleted factions
            for fid in removedFids:
                self.id_factions[record.fid].pop(fid,None)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        fid = record.fid
        if fid in self.csvId_factions:
            newFactions = set(
                [(faction, rank) for faction, rank in self.csvId_factions[fid]
                 if faction.ValidateFormID(self.patchFile)])
        elif fid in self.id_factions:
            newFactions = set([(faction, rank) for faction, rank in
                               self.id_factions[fid].iteritems() if
                               faction.ValidateFormID(self.patchFile)])
        else:
            return
        curFactions = set(
            [(faction[0], faction[1]) for faction in record.factions_list if
             faction[0].ValidateFormID(self.patchFile)])
        changed = newFactions - curFactions
        removed = curFactions - newFactions
        if changed or removed:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                for faction,rank in changed:
                    for entry in override.factions:
                        if entry.faction == faction:
                            entry.rank = rank
                            break
                    else:
                        entry = override.create_faction()
                        entry.faction = faction
                        entry.rank = rank
                override.factions_list = [(faction, rank) for faction, rank in
                                          override.factions_list if
                                          (faction, rank) not in removed]
                self.mod_count[record._Type][modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _AImportRelations(AImportPatcher):
    """Import faction relations to factions."""
    name = _(u'Import Relations')
    text = _(u"Import relations from source mods/files.")
    autoKey = {u'Relations'}

class ImportRelations(_SimpleImporter, _AImportRelations):
    logMsg = u'\n=== ' + _(u'Modified Factions') + u': %d'
    srcsHeader = u'=== ' + _(u'Source Mods/Files')

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(ImportRelations, self).initPatchFile(patchFile, loadMods)
        self.id_data = {}  #--[(otherLongid0,disp0),(...)] =
        # id_relations[mainLongid]. # WAS id_relations -renamed for _buildPatch

    def initData(self,progress):
        """Get names from source files."""
        factionRelations = self._parse_sources(progress, parser=FactionRelations)
        if not factionRelations: return
        #--Finish
        for fid, relations in factionRelations.id_relations.iteritems():
            if fid and (
                    fid[0] is not None and fid[0] in self.patchFile.loadSet):
                filteredRelations = [relation for relation in relations if
                                     relation[0] and (
                                     relation[0][0] is not None and
                                     relation[0][0] in self.patchFile.loadSet)]
                if filteredRelations:
                    self.id_data[fid] = filteredRelations
        self.isActive = bool(self.id_data)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('FACT',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('FACT',) if self.isActive else ()

    def scanModFile(self, modFile, progress): # scanModFile2
        """Scan modFile."""
        if not self.isActive: return
        id_relations= self.id_data
        mapper = modFile.getLongMapper()
        for type in ('FACT',):
            if type not in modFile.tops: continue
            patchBlock = getattr(self.patchFile,type)
            id_records = patchBlock.id_records
            for record in modFile.tops[type].getActiveRecords():
                fid = record.fid
                if not record.longFids: fid = mapper(fid)
                if fid in id_records: continue
                if fid not in id_relations: continue
                patchBlock.setRecord(record.getTypeCopy(mapper))

    def _inner_loop(self, keep, records, top_mod_rec, type_count):
        id_data, set_id_data = self.id_data, set(self.id_data)
        for record in records:
            fid = record.fid
            if fid in set_id_data:
                newRelations = set(id_data[fid])
                curRelations = set(
                    (x.faction, x.mod) for x in record.relations)
                changed = newRelations - curRelations
                if not changed: continue
                doKeep = False
                for faction, disp in changed:
                    for entry in record.relations:
                        if entry.faction == faction:
                            if entry.mod != disp:
                                entry.mod = disp
                                doKeep = True
                                keep(fid)
                            break
                    else:
                        entry = MelObject()
                        entry.faction = faction
                        entry.mod = disp
                        record.relations.append(entry)
                        doKeep = True
                if doKeep:
                    type_count[top_mod_rec] += 1
                    keep(fid)

    def buildPatch(self, log, progress, types=None):
        super(ImportRelations, self).buildPatch(log, progress, ('FACT',))

    def _plog(self,log,type_count):
        log(self.__class__.logMsg % type_count['FACT'])

class CBash_ImportRelations(CBash_ImportPatcher, _AImportRelations):
    logMsg = u'* ' + _(u'Re-Relationed Records') + u': %d'

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.fid_faction_mod = {}
        self.csvFid_faction_mod = {}

    def initData(self,group_patchers,progress):
        if not self.isActive: return
        CBash_ImportPatcher.initData(self,group_patchers,progress)
        factionRelations = self._parse_texts(CBash_FactionRelations, progress)
        #--Finish
        self.csvFid_faction_mod.update(factionRelations.fid_faction_mod)

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['FACT']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        relations = record.ConflictDetails(('relations_list',))
        if relations:
            self.fid_faction_mod.setdefault(record.fid, {}).update(
                relations['relations_list'])

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        fid = record.fid
        if fid in self.csvFid_faction_mod:
            newRelations = set((faction, mod) for faction, mod in
                               self.csvFid_faction_mod[fid].iteritems() if
                               faction.ValidateFormID(self.patchFile))
        elif fid in self.fid_faction_mod:
            newRelations = set((faction, mod) for faction, mod in
                               self.fid_faction_mod[fid].iteritems() if
                               faction.ValidateFormID(self.patchFile))
        else:
            return
        curRelations = set(record.relations_list)
        changed = newRelations - curRelations
        if changed:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                for faction,mod in changed:
                    for relation in override.relations:
                        if relation.faction == faction:
                            relation.mod = mod
                            break
                    else:
                        relation = override.create_relation()
                        relation.faction,relation.mod = faction,mod
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _AImportScripts(AImportPatcher):
    """Imports attached scripts on objects."""
    name = _(u'Import Scripts')
    text = _(u"Import Scripts on containers, plants, misc, weapons etc from "
             u"source mods.")
    tip = text
    autoKey = {u'Scripts'}

class ImportScripts(_SimpleImporter, _AImportScripts):
    rec_attrs = dict((x, ('script',)) for x in
                     {'WEAP', 'ACTI', 'ALCH', 'APPA', 'ARMO', 'BOOK', 'CLOT',
                      'CONT', 'CREA', 'DOOR', 'FLOR', 'FURN', 'INGR', 'KEYM',
                      'LIGH', 'MISC', 'NPC_', 'QUST', 'SGST', 'SLGM'})

class CBash_ImportScripts(_RecTypeModLogging, _AImportScripts):

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(CBash_ImportScripts, self).initPatchFile(patchFile, loadMods)
        if not self.isActive: return
        self.id_script = {}

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['ACTI','ALCH','APPA','ARMO','BOOK','CLOT','CONT','CREA',
                'DOOR','FLOR','FURN','INGR','KEYM','LIGH','LVLC','MISC',
                'NPC_','QUST','SGST','SLGM','WEAP']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        script = record.ConflictDetails(('script',))
        if script:
            script = script['script']
            if script.ValidateFormID(self.patchFile):
                # Only save if different from the master record
                if record.GetParentMod().GName != record.fid[0]:
                    history = record.History()
                    if history and len(history) > 0:
                        masterRecord = history[0]
                        if masterRecord.GetParentMod().GName == record.fid[
                            0] and masterRecord.script == record.script:
                            return # Same
                self.id_script[record.fid] = script
            else:
                # Ignore the record. Another option would be to just ignore
                # the invalid formIDs
                self.patchFile.patcher_mod_skipcount[self.name][
                    modFile.GName] += 1

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        if recordId in self.id_script and record.script != self.id_script[
            recordId]:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.script = self.id_script[recordId]
                self.mod_count[record._Type][modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _AImportInventory(AImportPatcher):
    """Merge changes to actor inventories."""
    name = _(u'Import Inventory')
    text = _(u"Merges changes to NPC, creature and container inventories.")
    autoKey = {u'Invent', u'InventOnly'}
    iiMode = True

class ImportInventory(ImportPatcher, _AImportInventory):
    logMsg = _(u'Inventories Changed') + u': %d'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(ImportInventory, self).initPatchFile(patchFile, loadMods)
        self.id_deltas = {}
        self.srcs = [x for x in self.srcs if
                     x in bosh.modInfos and x in patchFile.allSet]
        self.inventOnlyMods = set(x for x in self.srcs if (
            x in patchFile.mergeSet and
            {u'InventOnly', u'IIM'} & bosh.modInfos[x].getBashTags()))
        self.isActive = bool(self.srcs)
        self.masters = set()
        for srcMod in self.srcs:
            self.masters |= set(bosh.modInfos[srcMod].header.masters)
        self.allMods = self.masters | set(self.srcs)
        self.mod_id_entries = {}
        self.touched = set()

    def initData(self,progress):
        """Get data from source files."""
        if not self.isActive or not self.srcs: return
        if game.fsName == u'Skyrim':
            loadFactory = LoadFactory(False,'NPC_','CONT')
        else:
            loadFactory = LoadFactory(False,'CREA','NPC_','CONT')
        progress.setFull(len(self.srcs))
        for index,srcMod in enumerate(self.srcs):
            srcInfo = bosh.modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            mapper = srcFile.getLongMapper()
            if game.fsName == u'Skyrim':
                for block in (srcFile.NPC_, srcFile.CONT):
                    for record in block.getActiveRecords():
                        self.touched.add(mapper(record.fid))
            else:
                for block in (srcFile.CREA, srcFile.NPC_, srcFile.CONT):
                    for record in block.getActiveRecords():
                        self.touched.add(mapper(record.fid))
            progress.plus()

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return game.inventoryTypes if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return game.inventoryTypes if self.isActive else ()

    def scanModFile(self, modFile, progress): # scanModFile0
        """Add record from modFile."""
        if not self.isActive: return
        touched = self.touched
        id_deltas = self.id_deltas
        mod_id_entries = self.mod_id_entries
        mapper = modFile.getLongMapper()
        modName = modFile.fileInfo.name
        #--Master or source?
        if modName in self.allMods:
            id_entries = mod_id_entries[modName] = {}
            modFile.convertToLongFids(game.inventoryTypes)
            for type in game.inventoryTypes:
                for record in getattr(modFile,type).getActiveRecords():
                    if record.fid in touched:
                        id_entries[record.fid] = record.items[:]
        #--Source mod?
        if modName in self.srcs:
            id_entries = {}
            for master in modFile.tes4.masters:
                if master in mod_id_entries:
                    id_entries.update(mod_id_entries[master])
            for fid,entries in mod_id_entries[modName].iteritems():
                masterEntries = id_entries.get(fid)
                if masterEntries is None: continue
                masterItems = set(x.item for x in masterEntries)
                modItems = set(x.item for x in entries)
                removeItems = masterItems - modItems
                addItems = modItems - masterItems
                addEntries = [x for x in entries if x.item in addItems]
                deltas = self.id_deltas.get(fid)
                if deltas is None: deltas = self.id_deltas[fid] = []
                deltas.append((removeItems,addEntries))
        #--Keep record?
        if modFile.fileInfo.name not in self.inventOnlyMods:
            for type in game.inventoryTypes:
                patchBlock = getattr(self.patchFile,type)
                id_records = patchBlock.id_records
                for record in getattr(modFile,type).getActiveRecords():
                    fid = mapper(record.fid)
                    if fid in touched and fid not in id_records:
                        patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress): # buildPatch1:no modFileTops, for type..
        """Applies delta to patchfile."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        id_deltas = self.id_deltas
        mod_count = collections.defaultdict(int)
        for type in game.inventoryTypes:
            for record in getattr(self.patchFile,type).records:
                changed = False
                deltas = id_deltas.get(record.fid)
                if not deltas: continue
                removable = set(x.item for x in record.items)
                for removeItems,addEntries in reversed(deltas):
                    if removeItems:
                        #--Skip if some items to be removed have already
                        # been removed
                        if not removeItems.issubset(removable): continue
                        record.items = [x for x in record.items if
                                        x.item not in removeItems]
                        removable -= removeItems
                        changed = True
                    if addEntries:
                        current = set(x.item for x in record.items)
                        for entry in addEntries:
                            if entry.item not in current:
                                record.items.append(entry)
                                changed = True
                if changed:
                    keep(record.fid)
                    mod = record.fid[0]
                    mod_count[mod] += 1
        self.id_deltas.clear()
        self._patchLog(log,mod_count)

    def _plog(self, log, mod_count): self._plog1(log, mod_count)

class CBash_ImportInventory(_RecTypeModLogging, _AImportInventory):
    listSrcs=False
    logModRecs = u'%(type)s ' + _(u'Inventories Changed') + u': %(count)d'

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(CBash_ImportInventory, self).initPatchFile(patchFile, loadMods)
        if not self.isActive: return
        self.id_deltas = {}
        #should be redundant since this patcher doesn't allow unloaded
        #self.srcs = [x for x in self.srcs if (x in modInfos and x in
        # patchFile.allMods)]
        self.inventOnlyMods = set(x for x in self.srcs if (
            x in patchFile.mergeSet and
            {u'InventOnly', u'IIM'} & bosh.modInfos[x].getBashTags()))

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CREA','NPC_','CONT']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        #--Source mod?
        masters = record.History()
        if not masters: return
        entries = record.items_list
        modItems = set((item, count) for item, count in entries if
                       item.ValidateFormID(self.patchFile))
        masterEntries = []
        id_deltas = self.id_deltas
        fid = record.fid
        for masterEntry in masters:
            masterItems = set(
                (item, count) for item, count in masterEntry.items_list if
                item.ValidateFormID(self.patchFile))
            removeItems = masterItems - modItems
            addItems = modItems - masterItems
            if len(removeItems) or len(addItems):
                deltas = id_deltas.get(fid)
                if deltas is None: deltas = id_deltas[fid] = []
                deltas.append(
                    (set((item for item, count in removeItems)), addItems))

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        deltas = self.id_deltas.get(record.fid)
        if not deltas: return
        #If only the inventory is imported, the deltas have to be applied to
        #whatever record would otherwise be winning
        if modFile.GName in self.inventOnlyMods:
            conflicts = record.Conflicts()
            if conflicts:
                #If this isn't actually the winning record, use it.
                #This could be the case if a record was already copied into
                # the patch
                if conflicts[0] != record:
                    record = conflicts[0]
                #Otherwise, use the previous one.
                else:
                    record = conflicts[1]

        removable = set(entry.item for entry in record.items)
        items = record.items_list
        for removeItems,addEntries in reversed(deltas):
            if removeItems:
                #--Skip if some items to be removed have already been removed
                if not removeItems.issubset(removable): continue
                items = [(item, count) for item, count in items if
                         item not in removeItems]
                removable -= removeItems
            if addEntries:
                current = set(item for item,count in items)
                for item,count in addEntries:
                    if item not in current:
                        items.append((item,count))

        if len(items) != len(record.items_list) or set(
                (item, count) for item, count in record.items_list) != set(
                (item, count) for item, count in items):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.items_list = items
                self.mod_count[record._Type][modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _AImportActorsSpells(AImportPatcher):
    """Merges changes to the spells lists of Actors."""
    name = _(u'Import Actors: Spells')
    text = _(u"Merges changes to NPC and creature spell lists.")
    tip = text
    autoKey = {u'Actors.Spells', u'Actors.SpellsForceAdd'}

class ImportActorsSpells(ImportPatcher, _AImportActorsSpells):
    logMsg = _(u'Spell Lists Changed') + u': %d'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(ImportActorsSpells, self).initPatchFile(patchFile, loadMods)
        # long_fid -> {'merged':list[long_fid], 'deleted':list[long_fid]}
        self.id_merged_deleted = {}
        self.longTypes = {'CREA', 'NPC_'}

    def initData(self,progress):
        """Get data from source files."""
        if not self.isActive: return
        longTypes = self.longTypes
        loadFactory = LoadFactory(False,MreRecord.type_class['CREA'],
                                        MreRecord.type_class['NPC_'])
        progress.setFull(len(self.srcs))
        cachedMasters = {}
        mer_del = self.id_merged_deleted
        for index,srcMod in enumerate(self.srcs):
            tempData = {}
            if srcMod not in bosh.modInfos: continue
            srcInfo = bosh.modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            masters = srcInfo.header.masters
            bashTags = srcInfo.getBashTags()
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass in (MreRecord.type_class[x] for x in ('NPC_','CREA')):
                if recClass.classType not in srcFile.tops: continue
                for record in srcFile.tops[recClass.classType].getActiveRecords():
                    fid = mapper(record.fid)
                    tempData[fid] = list(record.spells)
            for master in reversed(masters):
                if not master in bosh.modInfos: continue # or break filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = bosh.modInfos[master]
                    masterFile = ModFile(masterInfo,loadFactory)
                    masterFile.load(True)
                    masterFile.convertToLongFids(longTypes)
                    cachedMasters[master] = masterFile
                mapper = masterFile.getLongMapper()
                for block in (MreRecord.type_class[x] for x in ('NPC_','CREA')):
                    if block.classType not in srcFile.tops: continue
                    if block.classType not in masterFile.tops: continue
                    for record in masterFile.tops[block.classType].getActiveRecords():
                        fid = mapper(record.fid)
                        if not fid in tempData: continue
                        if record.spells == tempData[fid] and not u'Actors.SpellsForceAdd' in bashTags:
                            # if subrecord is identical to the last master then we don't care about older masters.
                            del tempData[fid]
                            continue
                        if fid in mer_del:
                            if tempData[fid] == mer_del[fid]['merged']: continue
                        recordData = {'deleted':[],'merged':tempData[fid]}
                        for spell in list(record.spells):
                            if not spell in tempData[fid]:
                                recordData['deleted'].append(spell)
                        if not fid in mer_del:
                            mer_del[fid] = recordData
                        else:
                            for spell in recordData['deleted']:
                                if spell in mer_del[fid]['merged']:
                                    mer_del[fid]['merged'].remove(spell)
                                mer_del[fid]['deleted'].append(spell)
                            if mer_del[fid]['merged'] == []:
                                for spell in recordData['merged']:
                                    if spell in mer_del[fid]['deleted'] and not u'Actors.SpellsForceAdd' in bashTags: continue
                                    mer_del[fid]['merged'].append(spell)
                                continue
                            for index, spell in enumerate(recordData['merged']):
                                if not spell in mer_del[fid]['merged']: # so needs to be added... (unless deleted that is)
                                    # find the correct position to add and add.
                                    if spell in mer_del[fid]['deleted'] and not u'Actors.SpellsForceAdd' in bashTags: continue #previously deleted
                                    if index == 0:
                                        mer_del[fid]['merged'].insert(0, spell) #insert as first item
                                    elif index == (len(recordData['merged'])-1):
                                        mer_del[fid]['merged'].append(spell) #insert as last item
                                    else: #figure out a good spot to insert it based on next or last recognized item (ugly ugly ugly)
                                        i = index - 1
                                        while i >= 0:
                                            if recordData['merged'][i] in mer_del[fid]['merged']:
                                                slot = mer_del[fid]['merged'].index(recordData['merged'][i]) + 1
                                                mer_del[fid]['merged'].insert(slot, spell)
                                                break
                                            i -= 1
                                        else:
                                            i = index + 1
                                            while i != len(recordData['merged']):
                                                if recordData['merged'][i] in mer_del[fid]['merged']:
                                                    slot = mer_del[fid]['merged'].index(recordData['merged'][i])
                                                    mer_del[fid]['merged'].insert(slot, spell)
                                                    break
                                                i += 1
                                    continue # Done with this package
                                elif index == mer_del[fid]['merged'].index(spell) or (len(recordData['merged'])-index) == (len(mer_del[fid]['merged'])-mer_del[fid]['merged'].index(spell)): continue #spell same in both lists.
                                else: #this import is later loading so we'll assume it is better order
                                    mer_del[fid]['merged'].remove(spell)
                                    if index == 0:
                                        mer_del[fid]['merged'].insert(0, spell) #insert as first item
                                    elif index == (len(recordData['merged'])-1):
                                        mer_del[fid]['merged'].append(spell) #insert as last item
                                    else:
                                        i = index - 1
                                        while i >= 0:
                                            if recordData['merged'][i] in mer_del[fid]['merged']:
                                                slot = mer_del[fid]['merged'].index(recordData['merged'][i]) + 1
                                                mer_del[fid]['merged'].insert(slot, spell)
                                                break
                                            i -= 1
                                        else:
                                            i = index + 1
                                            while i != len(recordData['merged']):
                                                if recordData['merged'][i] in mer_del[fid]['merged']:
                                                    slot = mer_del[fid]['merged'].index(recordData['merged'][i])
                                                    mer_del[fid]['merged'].insert(slot, spell)
                                                    break
                                                i += 1
            progress.plus()

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('NPC_','CREA',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('NPC_','CREA',) if self.isActive else ()

    def scanModFile(self, modFile, progress): # scanModFile2
        """Add record from modFile."""
        if not self.isActive: return
        merged_deleted = self.id_merged_deleted
        mapper = modFile.getLongMapper()
        for type in ('NPC_','CREA'):
            patchBlock = getattr(self.patchFile,type)
            for record in getattr(modFile,type).getActiveRecords():
                fid = mapper(record.fid)
                if fid in merged_deleted:
                    if list(record.spells) != merged_deleted[fid]['merged']:
                        patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress): # buildPatch1:no modFileTops, for type..
        """Applies delta to patchfile."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        merged_deleted = self.id_merged_deleted
        mod_count = collections.defaultdict(int)
        for rec_type in ('NPC_','CREA'):
            for record in getattr(self.patchFile,rec_type).records:
                fid = record.fid
                if not fid in merged_deleted: continue
                changed = False
                mergedSpells = sorted(merged_deleted[fid]['merged'])
                if sorted(list(record.spells)) != mergedSpells:
                    record.spells = mergedSpells
                    changed = True
                if changed:
                    keep(record.fid)
                    mod = record.fid[0]
                    mod_count[mod] += 1
        self.id_merged_deleted.clear()
        self._patchLog(log,mod_count)

    def _plog(self, log, mod_count): self._plog1(log, mod_count)

class CBash_ImportActorsSpells(CBash_ImportPatcher, _AImportActorsSpells):
    logMsg = u'* '+_(u'Imported Spell Lists') + u': %d'

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.id_spells = {}

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CREA','NPC_']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        curData = {'deleted':[],'merged':[]}
        curspells = FormID.FilterValid(record.spells, self.patchFile)
        parentRecords = record.History()
        if parentRecords:
            parentSpells = FormID.FilterValid(parentRecords[-1].spells,
                                              self.patchFile)
            if parentSpells != curspells or u'Actors.SpellsForceAdd' in \
                    bashTags:
                for spell in parentSpells:
                    if spell not in curspells:
                        curData['deleted'].append(spell)
            curData['merged'] = curspells
            if not record.fid in self.id_spells:
                self.id_spells[record.fid] = curData
            else:
                id_spells = self.id_spells[record.fid]
                for spell in curData['deleted']:
                    if spell in id_spells['merged']:
                        id_spells['merged'].remove(spell)
                    id_spells['deleted'].append(spell)
                for spell in curData['merged']:
                    if spell in id_spells['merged']: continue  # don't want
                    # to add 20 copies of the spell afterall
                    if not spell in id_spells[
                        'deleted'] or u'Actors.SpellsForceAdd' in bashTags:
                        id_spells['merged'].append(spell)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        mergedSpells = self.id_spells.get(recordId,None)
        if mergedSpells:
            if sorted(record.spells) != sorted(mergedSpells['merged']):
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.spells = mergedSpells['merged']
                    self.mod_count[modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def _clog(self,log): # type 2
        self._srcMods(log)
        super(CBash_ImportActorsSpells, self)._clog(log)

#------------------------------------------------------------------------------
class _ANamesPatcher(AImportPatcher):
    """Import names from source mods/files."""
    name = _(u'Import Names')
    text = _(u"Import names from source mods/files.")
    autoKey = {u'Names'}
    logMsg =  u'\n=== ' + _(u'Renamed Items')
    srcsHeader = u'=== ' + _(u'Source Mods/Files')

class NamesPatcher(_ANamesPatcher, ImportPatcher):

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(NamesPatcher, self).initPatchFile(patchFile, loadMods)
        self.id_full = {} #--Names keyed by long fid.
        self.activeTypes = []  #--Types ('ALCH', etc.) of data actually
        # provided by src mods/files.
        self.skipTypes = [] #--Unknown types that were skipped.

    def initData(self,progress):
        """Get names from source files."""
        fullNames = self._parse_sources(progress, parser=FullNames)
        if not fullNames: return
        #--Finish
        id_full = self.id_full
        knownTypes = set(MreRecord.type_class.keys())
        for type,id_name in fullNames.type_id_name.iteritems():
            if type not in knownTypes:
                self.skipTypes.append(type)
                continue
            self.activeTypes.append(type)
            for longid,(eid,name) in id_name.iteritems():
                if name != u'NO NAME':
                    id_full[longid] = name
        self.isActive = bool(self.activeTypes)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return tuple(self.activeTypes) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return tuple(self.activeTypes) if self.isActive else ()

    def scanModFile(self, modFile, progress): # scanModFile0?
        """Scan modFile."""
        if not self.isActive: return
        id_full = self.id_full
        mapper = modFile.getLongMapper()
        for active_type in self.activeTypes:
            if active_type not in modFile.tops: continue
            patchBlock = getattr(self.patchFile, active_type)
            if active_type == 'CELL':
                id_records = patchBlock.id_cellBlock
                activeRecords = (cellBlock.cell for cellBlock in
                                 modFile.CELL.cellBlocks if
                                 not cellBlock.cell.flags1.ignored)
                setter = patchBlock.setCell
            elif active_type == 'WRLD':
                id_records = patchBlock.id_worldBlocks
                activeRecords = (worldBlock.world for worldBlock in
                                 modFile.WRLD.worldBlocks if
                                 not worldBlock.world.flags1.ignored)
                setter = patchBlock.setWorld
            else:
                id_records = patchBlock.id_records
                activeRecords = modFile.tops[active_type].getActiveRecords()
                setter = patchBlock.setRecord
            for record in activeRecords:
                fid = record.fid
                if not record.longFids: fid = mapper(fid)
                if fid in id_records: continue
                if fid not in id_full: continue # not a name
                if record.full != id_full[fid]:
                    setter(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress):# buildPatch0
        """Make changes to patchfile."""
        if not self.isActive: return
        modFile = self.patchFile
        keep = self.patchFile.getKeeper()
        id_full = self.id_full
        type_count = collections.defaultdict(int)
        for act_type in self.activeTypes:
            if act_type not in modFile.tops: continue
            if act_type == 'CELL':
                records = (cellBlock.cell for cellBlock in
                           modFile.CELL.cellBlocks)
            elif act_type == 'WRLD':
                records = (worldBlock.world for worldBlock in
                           modFile.WRLD.worldBlocks)
            else:
                records = modFile.tops[act_type].records
            for record in records:
                fid = record.fid
                if fid in id_full and record.full != id_full[fid]:
                    record.full = id_full[fid]
                    keep(fid)
                    type_count[act_type] += 1
        self.id_full.clear()
        self._patchLog(log,type_count)

class CBash_NamesPatcher(_ANamesPatcher, _RecTypeModLogging):

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(CBash_NamesPatcher, self).initPatchFile(patchFile, loadMods)
        if not self.isActive: return
        self.id_full = {}
        self.csvId_full = {}

    def initData(self,group_patchers,progress):
        if not self.isActive: return
        CBash_ImportPatcher.initData(self,group_patchers,progress)
        fullNames = self._parse_texts(CBash_FullNames, progress)
        #--Finish
        csvId_full = self.csvId_full
        for group,fid_name in fullNames.group_fid_name.iteritems():
            if group not in validTypes: continue
            for fid,(eid,name) in fid_name.iteritems():
                if name != u'NO NAME':
                    csvId_full[fid] = name

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CLAS','FACT','HAIR','EYES','RACE','MGEF','ENCH',
                'SPEL','BSGN','ACTI','APPA','ARMO','BOOK','CLOT',
                'CONT','DOOR','INGR','LIGH','MISC','FLOR','FURN',
                'WEAP','AMMO','NPC_','CREA','SLGM','KEYM','ALCH',
                'SGST','WRLD','CELLS','DIAL','QUST']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        full = record.ConflictDetails(('full',))
        if full:
            self.id_full[record.fid] = full['full']

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        full = self.id_full.get(recordId, None)
        full = self.csvId_full.get(recordId, full)
        if full and record.full != full:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.full = full
                self.mod_count[record._Type][modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _ANpcFacePatcher(AImportPatcher):
    """NPC Faces patcher, for use with TNR or similar mods."""
    name = _(u'Import NPC Faces')
    text = _(u"Import NPC face/eyes/hair from source mods. For use with TNR"
             u" and similar mods.")
    autoRe = re.compile(ur"^TNR .*.esp$",re.I|re.U)
    autoKey = {u'NpcFaces', u'NpcFacesForceFullImport', u'Npc.HairOnly',
               u'Npc.EyesOnly'}

    def _ignore_record(self, faceMod):
        # Ignore the record. Another option would be to just ignore the
        # attr_fidvalue result
        self.patchFile.patcher_mod_skipcount[self.name][faceMod] += 1

class NpcFacePatcher(_ANpcFacePatcher,ImportPatcher):
    logMsg = u'\n=== '+_(u'Faces Patched')+ u': %d'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(NpcFacePatcher, self).initPatchFile(patchFile, loadMods)
        self.faceData = {}

    def initData(self,progress):
        """Get faces from TNR files."""
        if not self.isActive: return
        faceData = self.faceData
        loadFactory = LoadFactory(False,MreRecord.type_class['NPC_'])
        progress.setFull(len(self.srcs))
        cachedMasters = {}
        for index,faceMod in enumerate(self.srcs):
            if faceMod not in bosh.modInfos: continue
            temp_faceData = {}
            faceInfo = bosh.modInfos[faceMod]
            faceFile = ModFile(faceInfo,loadFactory)
            masters = faceInfo.header.masters
            bashTags = faceInfo.getBashTags()
            faceFile.load(True)
            faceFile.convertToLongFids(('NPC_',))
            for npc in faceFile.NPC_.getActiveRecords():
                if npc.fid[0] in self.patchFile.loadSet:
                    attrs, fidattrs = [],[]
                    if u'Npc.HairOnly' in bashTags:
                        fidattrs += ['hair']
                        attrs = ['hairLength','hairRed','hairBlue','hairGreen']
                    if u'Npc.EyesOnly' in bashTags: fidattrs += ['eye']
                    if fidattrs:
                        attr_fidvalue = dict(
                            (attr, npc.__getattribute__(attr)) for attr in
                            fidattrs)
                    else:
                        attr_fidvalue = dict(
                            (attr, npc.__getattribute__(attr)) for attr in
                            ('eye', 'hair'))
                    for fidvalue in attr_fidvalue.values():
                        if fidvalue and (fidvalue[0] is None or fidvalue[0] not in self.patchFile.loadSet):
                            self._ignore_record(faceMod)
                            break
                    else:
                        if not fidattrs:
                            temp_faceData[npc.fid] = dict(
                                (attr, npc.__getattribute__(attr)) for attr in
                                ('fggs_p', 'fgga_p', 'fgts_p', 'hairLength',
                                 'hairRed', 'hairBlue', 'hairGreen',
                                 'unused3'))
                        else:
                            temp_faceData[npc.fid] = dict(
                                (attr, npc.__getattribute__(attr)) for attr in
                                attrs)
                        temp_faceData[npc.fid].update(attr_fidvalue)
            if u'NpcFacesForceFullImport' in bashTags:
                for fid in temp_faceData:
                    faceData[fid] = temp_faceData[fid]
            else:
                for master in masters:
                    if not master in bosh.modInfos: continue # or break filter mods
                    if master in cachedMasters:
                        masterFile = cachedMasters[master]
                    else:
                        masterInfo = bosh.modInfos[master]
                        masterFile = ModFile(masterInfo,loadFactory)
                        masterFile.load(True)
                        masterFile.convertToLongFids(('NPC_',))
                        cachedMasters[master] = masterFile
                    mapper = masterFile.getLongMapper()
                    if 'NPC_' not in masterFile.tops: continue
                    for npc in masterFile.NPC_.getActiveRecords():
                        if npc.fid not in temp_faceData: continue
                        for attr, value in temp_faceData[npc.fid].iteritems():
                            if value == npc.__getattribute__(attr): continue
                            if npc.fid not in faceData: faceData[
                                npc.fid] = dict()
                            try:
                                faceData[npc.fid][attr] = \
                                temp_faceData[npc.fid][attr]
                            except KeyError:
                                faceData[npc.fid].setdefault(attr,value)
            progress.plus()

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('NPC_',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('NPC_',) if self.isActive else ()

    def scanModFile(self, modFile, progress): # scanModFile3: mapper unused !
        """Add lists from modFile."""
        modName = modFile.fileInfo.name
        if not self.isActive or modName in self.srcs or 'NPC_' not in modFile.tops:
            return
        mapper = modFile.getLongMapper()
        faceData,patchNpcs = self.faceData,self.patchFile.NPC_
        modFile.convertToLongFids(('NPC_',))
        for npc in modFile.NPC_.getActiveRecords():
            if npc.fid in faceData:
                patchNpcs.setRecord(npc)

    def buildPatch(self,log,progress):# buildPatch3: one type
        """Adds merged lists to patchfile."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        faceData, count = self.faceData, 0
        for npc in self.patchFile.NPC_.records:
            if npc.fid in faceData:
                changed = False
                for attr, value in faceData[npc.fid].iteritems():
                    if value != npc.__getattribute__(attr):
                        npc.__setattr__(attr,value)
                        changed = True
                if changed:
                    npc.setChanged()
                    keep(npc.fid)
                    count += 1
        self.faceData.clear()
        self._patchLog(log,count)

    def _plog(self, log, count): log(self.__class__.logMsg % count)

class CBash_NpcFacePatcher(_ANpcFacePatcher,CBash_ImportPatcher):
    logMsg = u'* '+_(u'Faces Patched') + u': %d'

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.id_face = {}
        self.faceData = (
            'fggs_p', 'fgga_p', 'fgts_p', 'eye', 'hair', 'hairLength',
            'hairRed', 'hairBlue', 'hairGreen', 'fnam')

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['NPC_']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        attrs = []
        if u'NpcFacesForceFullImport' in bashTags:
            face = dict((attr,getattr(record,attr)) for attr in self.faceData)
            if ValidateDict(face, self.patchFile):
                self.id_face[record.fid] = face
            else:
                self._ignore_record(modFile.GName)
            return
        elif u'NpcFaces' in bashTags:
            attrs = self.faceData
        else:
            if u'Npc.HairOnly' in bashTags:
                attrs = ['hair', 'hairLength','hairRed','hairBlue','hairGreen']
            if u'Npc.EyesOnly' in bashTags:
                attrs += ['eye']
        if not attrs:
            return
        face = record.ConflictDetails(attrs)
        if ValidateDict(face, self.patchFile):
            fid = record.fid
            # Only save if different from the master record
            if record.GetParentMod().GName != fid[0]:
                history = record.History()
                if history and len(history) > 0:
                    masterRecord = history[0]
                    if masterRecord.GetParentMod().GName == record.fid[0]:
                        for attr, value in face.iteritems():
                            if getattr(masterRecord,attr) != value:
                                break
                        else:
                            return
            self.id_face.setdefault(fid,{}).update(face)
        else:
            self._ignore_record(modFile.GName)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)

        recordId = record.fid
        prev_face_value = self.id_face.get(recordId,None)
        if prev_face_value:
            cur_face_value = dict(
                (attr, getattr(record, attr)) for attr in prev_face_value)
            if cur_face_value != prev_face_value:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_face_value.iteritems():
                        setattr(override,attr,value)
                    self.mod_count[modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def _clog(self,log): # type 2
        self._srcMods(log)
        super(CBash_NpcFacePatcher, self)._clog(log)

#------------------------------------------------------------------------------
class _ARoadImporter(AImportPatcher):
    """Imports roads."""
    name = _(u'Import Roads')
    text = _(u"Import roads from source mods.")
    tip = text
    autoKey = {u'Roads'}

class RoadImporter(ImportPatcher, _ARoadImporter):
    logMsg = _(u'Worlds Patched')

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(RoadImporter, self).initPatchFile(patchFile, loadMods)
        self.world_road = {}

    def initData(self,progress):
        """Get cells from source files."""
        if not self.isActive: return
        loadFactory = LoadFactory(False,MreRecord.type_class['CELL'],
                                        MreRecord.type_class['WRLD'],
                                        MreRecord.type_class['ROAD'])
        progress.setFull(len(self.srcs))
        for srcMod in self.srcs:
            if srcMod not in bosh.modInfos: continue
            srcInfo = bosh.modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            srcFile.convertToLongFids(('WRLD','ROAD'))
            for worldBlock in srcFile.WRLD.worldBlocks:
                if worldBlock.road:
                    worldId = worldBlock.world.fid
                    road = worldBlock.road.getTypeCopy()
                    self.world_road[worldId] = road
        self.isActive = bool(self.world_road)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('CELL','WRLD','ROAD',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('CELL','WRLD','ROAD',) if self.isActive else ()

    def scanModFile(self, modFile, progress): # scanModFile3 ?
        """Add lists from modFile."""
        if not self.isActive or 'WRLD' not in modFile.tops: return
        patchWorlds = self.patchFile.WRLD
        modFile.convertToLongFids(('CELL','WRLD','ROAD'))
        for worldBlock in modFile.WRLD.worldBlocks:
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
        for worldBlock in self.patchFile.WRLD.worldBlocks:
            worldId = worldBlock.world.fid
            curRoad = worldBlock.road
            newRoad = self.world_road.get(worldId)
            if newRoad and (not curRoad or curRoad.points_p != newRoad.points_p
                or curRoad.connections_p != newRoad.connections_p
                ):
                worldBlock.road = newRoad
                keep(worldId)
                keep(newRoad.fid)
                worldsPatched.add((worldId[0].s,worldBlock.world.eid))
        self.world_road.clear()
        self._patchLog(log,worldsPatched)

    def _plog(self,log,worldsPatched):
        log(self.__class__.logMsg)
        for modWorld in sorted(worldsPatched):
            log(u'* %s: %s' % modWorld)

class CBash_RoadImporter(CBash_ImportPatcher, _ARoadImporter):
    logMsg = u'* ' + _(u'Roads Imported') + u': %d'
    #The regular patch routine doesn't allow merging of world records. The CBash patch routine does.
    #So, allowUnloaded isn't needed for this patcher to work. The same functionality could be gained by merging the tagged record.
    #It is needed however so that the regular patcher and the CBash patcher have the same behavior.
    #The regular patcher has to allow unloaded mods because it can't otherwise force the road record to be merged
    #This isn't standard behavior for import patchers, but consistency between patchers is more important.

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.id_ROAD = {}

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['ROADS']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        self.id_ROAD[record.fid] = record

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        #If a previous road was scanned, and it is replaced by a new road
        curRoad = record
        newRoad = self.id_ROAD.get(recordId, None)
        if newRoad:
            #Roads and pathgrids are complex records...
            #No good way to tell if the roads are equal.
            #A direct comparison can prove equality, but not inequality
            if curRoad.pgrp_list == newRoad.pgrp_list and curRoad.pgrr_list == newRoad.pgrr_list:
                return
            #So some records that are actually equal won't pass the above test and end up copied over
            #Bloats the patch a little, but won't hurt anything.
            if newRoad.fid.ValidateFormID(self.patchFile):
                copyRoad = newRoad #Copy the new road over
            elif curRoad and curRoad.fid.ValidateFormID(self.patchFile):
                copyRoad = curRoad #Copy the current road over (its formID is acceptable)
            else:
                #Ignore the record.
                self.patchFile.patcher_mod_skipcount[self.name][
                    modFile.GName] += 1
                return

            override = copyRoad.CopyAsOverride(self.patchFile, UseWinningParents=True) #Copies the road over (along with the winning version of its parents if needed)
            if override:
                #Copy the new road values into the override (in case the CopyAsOverride returned a record pre-existing in the patch file)
                for copyattr in newRoad.copyattrs:
                    setattr(override, copyattr, getattr(newRoad, copyattr))
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _ASoundPatcher(AImportPatcher):
    """Imports sounds from source mods into patch."""
    name = _(u'Import Sounds')
    autoKey = {u'Sound'}

class SoundPatcher(_SimpleImporter, _ASoundPatcher):
    """Imports sounds from source mods into patch."""
    text = _(u"Import sounds (from Magic Effects, Containers, Activators,"
             u" Lights, Weathers and Doors) from source mods.")
    tip = text
    rec_attrs = game.soundsTypes
    long_types = game.soundsLongsTypes

class CBash_SoundPatcher(_RecTypeModLogging, _ASoundPatcher):
    """Imports sounds from source mods into patch."""
    text = _(u"Import sounds (from Activators, Containers, Creatures, Doors,"
             u" Lights, Magic Effects and Weathers) from source mods.")
    tip = text

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(CBash_SoundPatcher, self).initPatchFile(patchFile, loadMods)
        if not self.isActive: return
        class_attrs = self.class_attrs = {}
        class_attrs['ACTI'] = ('sound',)
        class_attrs['CONT'] = ('soundOpen','soundClose')
        class_attrs['CREA'] = ('footWeight','inheritsSoundsFrom','sounds_list')
        class_attrs['DOOR'] = ('soundOpen','soundClose','soundLoop')
        class_attrs['LIGH'] = ('sound',)
        class_attrs['MGEF'] = (
            'castingSound', 'boltSound', 'hitSound', 'areaSound')
        ##        class_attrs['REGN'] = ('sound','sounds_list')
        class_attrs['WTHR'] = ('sounds_list',)

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['ACTI','CONT','CREA','DOOR','LIGH','MGEF','WTHR']

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        prev_attr_value = self.fid_attr_value.get(recordId,None)
        if prev_attr_value:
            cur_attr_value = dict(
                (attr, getattr(record, attr)) for attr in prev_attr_value)
            if cur_attr_value != prev_attr_value:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_attr_value.iteritems():
                        setattr(override,attr,value)
                    self.mod_count[record._Type][modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _AStatsPatcher(AImportPatcher):
    """Import stats from mod file."""
    scanOrder = 28
    editOrder = 28 #--Run ahead of bow patcher
    name = _(u'Import Stats')
    text = _(u"Import stats from any pickupable items from source mods/files.")
    autoKey = {u'Stats'}
    logMsg = u'\n=== ' + _(u'Imported Stats')
    srcsHeader = u'=== ' + _(u'Source Mods/Files')

class StatsPatcher(_AStatsPatcher, ImportPatcher):

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(StatsPatcher, self).initPatchFile(patchFile, loadMods)
        #--To be filled by initData
        self.fid_attr_value = {} #--Stats keyed by long fid.
        self.activeTypes = [] #--Types ('ARMO', etc.) of data actually provided by src mods/files.
        self.class_attrs = {}

    def initData(self,progress):
        """Get stats from source files."""
        itemStats = self._parse_sources(progress, parser=ItemStats)
        if not itemStats: return
        #--Finish
        for group,nId_attr_value in itemStats.class_fid_attr_value.iteritems():
            self.activeTypes.append(group)
            for id, attr_value in nId_attr_value.iteritems():
                del attr_value['eid']
            self.fid_attr_value.update(nId_attr_value)
            self.class_attrs[group] = itemStats.class_attrs[group][1:]
        self.isActive = bool(self.activeTypes)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return tuple(self.activeTypes) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return tuple(self.activeTypes) if self.isActive else ()

    def scanModFile(self, modFile, progress): # scanModFile4: ?
        """Add affected items to patchFile."""
        if not self.isActive: return
        fid_attr_value = self.fid_attr_value
        mapper = modFile.getLongMapper()
        for group in self.activeTypes:
            if group not in modFile.tops: continue
            attrs = self.class_attrs[group]
            patchBlock = getattr(self.patchFile,group)
            id_records = patchBlock.id_records
            for record in getattr(modFile,group).getActiveRecords():
                longid = record.fid
                if not record.longFids: longid = mapper(longid)
                if longid in id_records: continue
                itemStats = fid_attr_value.get(longid,None)
                if not itemStats: continue
                oldValues = dict(zip(attrs,map(record.__getattribute__,attrs)))
                if oldValues != itemStats:
                    patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress):# buildPatch2 !!!!
        """Adds merged lists to patchfile."""
        if not self.isActive: return
        patchFile = self.patchFile
        keep = self.patchFile.getKeeper()
        fid_attr_value = self.fid_attr_value
        allCounts = []
        for group in self.activeTypes:
            if group not in patchFile.tops: continue
            attrs = self.class_attrs[group]
            count,counts = 0,{}
            for record in patchFile.tops[group].records:
                fid = record.fid
                itemStats = fid_attr_value.get(fid,None)
                if not itemStats: continue
                oldValues = dict(zip(attrs,map(record.__getattribute__,attrs)))
                if oldValues != itemStats:
                    for attr, value in itemStats.iteritems():
                        setattr(record,attr,value)
                    keep(fid)
                    count += 1
                    counts[fid[0]] = 1 + counts.get(fid[0],0)
            allCounts.append((group,count,counts))
        self.fid_attr_value.clear()
        self._patchLog(log, allCounts)

    def _plog(self, log, allCounts): self._plog2(log, allCounts)

class CBash_StatsPatcher(_AStatsPatcher, _RecTypeModLogging):

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        super(CBash_StatsPatcher, self).initPatchFile(patchFile, loadMods)
        if not self.isActive: return
        self.csvFid_attr_value = {}
        self.class_attrs = CBash_ItemStats.class_attrs

    def initData(self,group_patchers,progress):
        """Compiles material, i.e. reads source text, esp's, etc. as necessary."""
        if not self.isActive: return
        CBash_ImportPatcher.initData(self,group_patchers,progress)
        itemStats = self._parse_texts(CBash_ItemStats, progress)
        #--Finish
        for group,nId_attr_value in itemStats.class_fid_attr_value.iteritems():
            if group not in validTypes: continue
            self.csvFid_attr_value.update(nId_attr_value)

        for group in self.getTypes():
            group_patchers.setdefault(group,[]).append(self)

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return self.class_attrs.keys()

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        prev_attr_value = self.fid_attr_value.get(recordId, None)
        csv_attr_value = self.csvFid_attr_value.get(recordId, None)
        if csv_attr_value and ValidateDict(csv_attr_value, self.patchFile):
            prev_attr_value = csv_attr_value
        if prev_attr_value:
            cur_attr_value = dict((attr,getattr(record,attr)) for attr in prev_attr_value)
            if cur_attr_value != prev_attr_value:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_attr_value.iteritems():
                        setattr(override,attr,value)
                    self.mod_count[record._Type][modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _ASpellsPatcher(AImportPatcher):
    """Import spell changes from mod files."""
    scanOrder = 29
    editOrder = 29 #--Run ahead of bow patcher
    name = _(u'Import Spell Stats')
    text = _(u"Import stats from any spells from source mods/files.")
    autoKey = {u'Spells',u'SpellStats'}

class SpellsPatcher(ImportPatcher, _ASpellsPatcher):
    logMsg = u'\n=== ' + _(u'Modified SPEL Stats')
    srcsHeader = u'=== ' + _(u'Source Mods/Files')

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(SpellsPatcher, self).initPatchFile(patchFile, loadMods)
        #--To be filled by initData
        self.id_stat = {} #--Stats keyed by long fid.
        self.spell_attrs = None #set in initData

    def initData(self,progress):
        """Get stats from source files."""
        spellStats = self._parse_sources(progress, parser=SpellRecords)
        if not spellStats: return
        self.spell_attrs = spellStats.attrs
        #--Finish
        self.id_stat.update(spellStats.fid_stats)
        self.isActive = bool(self.id_stat)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('SPEL',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('SPEL',) if self.isActive else ()

    def scanModFile(self, modFile, progress): # scanModFile4: ?
        """Add affected items to patchFile."""
        if not self.isActive or 'SPEL' not in modFile.tops:
            return
        id_stat = self.id_stat
        mapper = modFile.getLongMapper()
        spell_attrs = self.spell_attrs
        patchBlock = self.patchFile.SPEL
        id_records = patchBlock.id_records
        for record in modFile.SPEL.getActiveRecords():
            fid = record.fid
            if not record.longFids: fid = mapper(fid)
            if fid in id_records: continue
            spellStats = id_stat.get(fid)
            if not spellStats: continue
            oldValues = [getattr_deep(record, attr) for attr in spell_attrs]
            if oldValues != spellStats:
                patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress):# buildPatch3: one type
        """Adds merged lists to patchfile."""
        if not self.isActive: return
        patchFile = self.patchFile
        keep = self.patchFile.getKeeper()
        id_stat = self.id_stat
        allCounts = []
        spell_attrs = self.spell_attrs
        count,counts = 0,{}
        for record in patchFile.SPEL.records:
            fid = record.fid
            spellStats = id_stat.get(fid)
            if not spellStats: continue
            oldValues = [getattr_deep(record, attr) for attr in spell_attrs]
            if oldValues == spellStats: continue
            for attr,value in zip(spell_attrs,spellStats):
                setattr_deep(record,attr,value)
            keep(fid)
            count += 1
            counts[fid[0]] = 1 + counts.get(fid[0],0)
        self.id_stat.clear()
        allCounts.append(('SPEL',count,counts))
        self._patchLog(log, allCounts)

    def _plog(self, log, allCounts): self._plog2(log, allCounts)

class CBash_SpellsPatcher(CBash_ImportPatcher, _ASpellsPatcher):
    logMsg = u'* ' + _(u'Modified SPEL Stats') + u': %d'

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.id_stats = {}
        self.csvId_stats = {}
        self.spell_attrs = None #set in initData

    def initData(self,group_patchers,progress):
        if not self.isActive: return
        CBash_ImportPatcher.initData(self,group_patchers,progress)
        spellStats = self._parse_texts(CBash_SpellRecords, progress)
        self.spell_attrs = spellStats.attrs
        #--Finish
        self.csvId_stats.update(spellStats.fid_stats)

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['SPEL']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        conflicts = record.ConflictDetails(self.spell_attrs)
        if conflicts:
            if ValidateDict(conflicts, self.patchFile):
                self.id_stats.setdefault(record.fid,{}).update(conflicts)
            else:
                #Ignore the record. Another option would be to just ignore the invalid formIDs
                self.patchFile.patcher_mod_skipcount[self.name][
                    modFile.GName] += 1

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        prev_values = self.id_stats.get(recordId, None)
        csv_values = self.csvId_stats.get(recordId, None)
        if csv_values and ValidateDict(csv_values, self.patchFile):
            prev_values = csv_values
        if prev_values:
            rec_values = dict(
                (attr, getattr(record, attr)) for attr in prev_values)
            if rec_values != prev_values:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_values.iteritems():
                        setattr(override,attr,value)
                    self.mod_count[modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID
