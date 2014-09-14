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

"""This module contains the oblivion importer patcher classes.""" # TODO:DOCS

# Patchers: 20 ----------------------------------------------------------------
import operator
from .... import bosh # for modInfos
from ....bolt import GPath, MemorySet
from ....bosh import LoadFactory, ModFile, CountDict, getPatchesList, \
    reModExt, getPatchesPath
from ....brec import MreRecord, MelObject
from ....patcher.base import AImportPatcher, Patcher
from ....patcher.oblivion.patchers.base import ImportPatcher, \
    CBash_ImportPatcher
from ....cint import ValidateDict, ValidateList
from ..utilities import ActorFactions, CBash_ActorFactions, FactionRelations, \
    CBash_FactionRelations

class ACellImporter(AImportPatcher):
    """Merges changes to cells (climate, lighting, and water.)"""
    text = _(u"Import cells (climate, lighting, and water) from source mods.")
    tip = text
    name = _(u'Import Cells')

class CellImporter(ACellImporter, ImportPatcher):
    autoKey = (u'C.Climate', u'C.Light', u'C.Water', u'C.Owner', u'C.Name',
               u'C.RecordFlags', u'C.Music')  # ,u'C.Maps')
    logMsg = _(u'Cells/Worlds Patched')

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(CellImporter, self).initPatchFile(patchFile,loadMods)
        self.cellData = {}
        self.sourceMods = self.getConfigChecked()
        self.isActive = bool(self.sourceMods)
        # TODO: docs: recAttrs vs tag_attrs - extra in PBash:
        # 'unused1','unused2','unused3'
        self.recAttrs = {
            u'C.Climate': ('climate',),
            u'C.Music': ('music',),
            u'C.Name': ('full',),
            u'C.Owner': ('ownership',),
            u'C.Water': ('water','waterHeight'),
            u'C.Light': ('ambientRed','ambientGreen','ambientBlue','unused1',
                        'directionalRed','directionalGreen','directionalBlue','unused2',
                        'fogRed','fogGreen','fogBlue','unused3',
                        'fogNear','fogFar','directionalXY','directionalZ',
                        'directionalFade','fogClip'),
            u'C.RecordFlags': ('flags1',), # Yes seems funky but thats the way it is
            }
        self.recFlags = {
            u'C.Climate': 'behaveLikeExterior',
            u'C.Music': '',
            u'C.Name': '',
            u'C.Owner': 'publicPlace',
            u'C.Water': 'hasWater',
            u'C.Light': '',
            u'C.RecordFlags': '',
            }

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('CELL','WRLD',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('CELL','WRLD',) if self.isActive else ()

    def initData(self,progress):
        """Get cells from source files."""
        if not self.isActive: return
        def importCellBlockData(cellBlock):
            if not cellBlock.cell.flags1.ignored:
                fid = cellBlock.cell.fid
                if fid not in tempCellData:
                    tempCellData[fid] = {}
                    tempCellData[fid+('flags',)] = {}
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
                if fid not in cellData:
                    cellData[fid] = {}
                    cellData[fid+('flags',)] = {}
                for attr in attrs:
                    if tempCellData[fid][
                        attr] != cellBlock.cell.__getattribute__(attr):
                        cellData[fid][attr] = tempCellData[fid][attr]
                for flag in flags:
                    if tempCellData[fid + ('flags',)][flag] != \
                            cellBlock.cell.flags.__getattr__(flag):
                        cellData[fid + ('flags',)][flag] = \
                            tempCellData[fid + ('flags',)][flag]
        cellData = self.cellData
        # cellData['Maps'] = {}
        loadFactory = LoadFactory(False,MreRecord.type_class['CELL'],
                                        MreRecord.type_class['WRLD'])
        progress.setFull(len(self.sourceMods))
        cachedMasters = {}
        for srcMod in self.sourceMods:
            if srcMod not in bosh.modInfos: continue
            tempCellData = {'Maps':{}}
            srcInfo = bosh.modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            srcFile.convertToLongFids(('CELL','WRLD'))
            masters = srcInfo.header.masters
            bashTags = srcInfo.getBashTags()
            # print bashTags
            try:
                attrs = set(reduce(operator.add,
                                   (self.recAttrs[bashKey] for bashKey in
                                    bashTags if bashKey in self.recAttrs)))
            except: attrs = set()
            flags = tuple(self.recFlags[bashKey] for bashKey in bashTags if
                bashKey in self.recAttrs and self.recFlags[bashKey] != u'')
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

    def scanModFile(self, modFile, progress):
        """Add lists from modFile."""
        modName = modFile.fileInfo.name
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

    def buildPatch(self,log,progress):
        """Adds merged lists to patchfile."""
        def handleCellBlock(cellBlock):
            modified=False
            for attr,value in cellData[cellBlock.cell.fid].iteritems():
                if cellBlock.cell.__getattribute__(attr) != value:
                    cellBlock.cell.__setattr__(attr,value)
                    modified=True
            for flag, value in cellData[
                        cellBlock.cell.fid + ('flags',)].iteritems():
                if cellBlock.cell.flags.__getattr__(flag) != value:
                    cellBlock.cell.flags.__setattr__(flag,value)
                    modified=True
            if modified:
                cellBlock.cell.setChanged()
                keep(cellBlock.cell.fid)
            return modified
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        cellData,count = self.cellData, CountDict()
        for cellBlock in self.patchFile.CELL.cellBlocks:
            if cellBlock.cell.fid in cellData and handleCellBlock(cellBlock):
                count.increment(cellBlock.cell.fid[0])
        for worldBlock in self.patchFile.WRLD.worldBlocks:
            keepWorld = False
            for cellBlock in worldBlock.cellBlocks:
                if cellBlock.cell.fid in cellData and handleCellBlock(
                        cellBlock):
                    count.increment(cellBlock.cell.fid[0])
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
        self._patchLog(log, count, logMsg=u'\n=== ' + self.__class__.logMsg)

class CBash_CellImporter(ACellImporter,CBash_ImportPatcher):
    autoKey = {u'C.Climate', u'C.Light', u'C.Water', u'C.Owner', u'C.Name',
               u'C.RecordFlags', u'C.Music'}  #,u'C.Maps'
    logMsg = u'* ' + _(u'Cells/Worlds Patched') + u': %d'

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(CBash_CellImporter, self).initPatchFile(patchFile,loadMods)
        if not self.isActive: return
        self.fid_attr_value = {}
        self.mod_count = {}
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
                mod_skipcount = \
                    self.patchFile.patcher_mod_skipcount.setdefault(
                    self.name, {})
                mod_skipcount[modFile.GName] = mod_skipcount.setdefault(
                    modFile.GName, 0) + 1
                continue
            self.fid_attr_value.setdefault(record.fid,{}).update(attr_value)

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
                    mod_count = self.mod_count
                    mod_count[modFile.GName] = mod_count.get(modFile.GName,
                                                             0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
def _buildPatch(self,log,inner_for):
    """Common buildPatch() pattern of :
        GraphicsPatcher
        ActorImporter
        KFFZPatcher
        DeathItemPatcher
        ImportScripts
    """ # TODO: filter()
    if not self.isActive: return
    modFileTops = self.patchFile.tops
    keep = self.patchFile.getKeeper()
    id_data = self.id_data
    type_count = {}
    for recClass in self.srcClasses:
        type = recClass.classType
        if type not in modFileTops: continue
        type_count[type] = 0
        inner_for(id_data, keep, modFileTops, type, type_count)
    # noinspection PyUnusedLocal
    id_data = None # cleanup to save memory
    self._patchLog(log,type_count)

def _scanModFile(self, modFile):
    """Scan mod file against source data. Common scanModFile() pattern of :
        GraphicsPatcher
        KFFZPatcher
        DeathItemPatcher
        ImportScripts
    """
    if not self.isActive: return
    id_data = self.id_data
    modName = modFile.fileInfo.name # UNUSED ! TODO: bin ?
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
                if record.__getattribute__(attr) != value:
                    patchBlock.setRecord(record.getTypeCopy(mapper))
                    break

class GraphicsPatcher(ImportPatcher):
    """Merges changes to graphics (models and icons)."""
    name = _(u'Import Graphics')
    text = _(u"Import graphics (models, icons, etc.) from source mods.")
    tip = text
    autoKey = u'Graphics'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_data = {} #--Names keyed by long fid.
        self.srcClasses = set()  # --Record classes actually provided by src
        #  mods/files.
        self.sourceMods = self.getConfigChecked()
        self.isActive = len(self.sourceMods) != 0
        self.classestemp = set()
        #--Type Fields
        recAttrs_class = self.recAttrs_class = {}
        recFidAttrs_class = self.recFidAttrs_class = {}
        for recClass in (MreRecord.type_class[x] for x in ('BSGN','LSCR','CLAS','LTEX','REGN')):
            recAttrs_class[recClass] = ('iconPath',)
        for recClass in (MreRecord.type_class[x] for x in ('ACTI','DOOR','FLOR','FURN','GRAS','STAT')):
            recAttrs_class[recClass] = ('model',)
        for recClass in (MreRecord.type_class[x] for x in ('ALCH','AMMO','APPA','BOOK','INGR','KEYM','LIGH','MISC','SGST','SLGM','WEAP','TREE')):
            recAttrs_class[recClass] = ('iconPath','model')
        for recClass in (MreRecord.type_class[x] for x in ('ARMO','CLOT')):
            recAttrs_class[recClass] = ('maleBody','maleWorld','maleIconPath','femaleBody','femaleWorld','femaleIconPath','flags')
        for recClass in (MreRecord.type_class[x] for x in ('CREA',)):
            recAttrs_class[recClass] = ('bodyParts','nift_p')
        for recClass in (MreRecord.type_class[x] for x in ('MGEF',)):
            recAttrs_class[recClass] = ('iconPath','model')
            recFidAttrs_class[recClass] = ('effectShader','enchantEffect','light')
        for recClass in (MreRecord.type_class[x] for x in ('EFSH',)):
            recAttrs_class[recClass] = ('particleTexture','fillTexture','flags','unused1','memSBlend',
                                        'memBlendOp','memZFunc','fillRed','fillGreen','fillBlue','unused2',
                                        'fillAIn','fillAFull','fillAOut','fillAPRatio','fillAAmp','fillAFreq',
                                        'fillAnimSpdU','fillAnimSpdV','edgeOff','edgeRed','edgeGreen',
                                        'edgeBlue','unused3','edgeAIn','edgeAFull','edgeAOut','edgeAPRatio',
                                        'edgeAAmp','edgeAFreq','fillAFRatio','edgeAFRatio','memDBlend',
                                        'partSBlend','partBlendOp','partZFunc','partDBlend','partBUp',
                                        'partBFull','partBDown','partBFRatio','partBPRatio','partLTime',
                                        'partLDelta','partNSpd','partNAcc','partVel1','partVel2','partVel3',
                                        'partAcc1','partAcc2','partAcc3','partKey1','partKey2','partKey1Time',
                                        'partKey2Time','key1Red','key1Green','key1Blue','unused4','key2Red',
                                        'key2Green','key2Blue','unused5','key3Red','key3Green','key3Blue',
                                        'unused6','key1A','key2A','key3A','key1Time','key2Time','key3Time')
        #--Needs Longs
        self.longTypes = {'BSGN', 'LSCR', 'CLAS', 'LTEX', 'REGN', 'ACTI',
                          'DOOR', 'FLOR', 'FURN', 'GRAS', 'STAT', 'ALCH',
                          'AMMO', 'APPA', 'BOOK', 'INGR', 'KEYM', 'LIGH',
                          'MISC', 'SGST', 'SLGM', 'WEAP', 'TREE', 'ARMO',
                          'CLOT', 'CREA', 'MGEF', 'EFSH'}

    def initData(self,progress):
        """Get graphics from source files."""
        if not self.isActive: return
        id_data = self.id_data
        recAttrs_class = self.recAttrs_class
        loadFactory = LoadFactory(False,*recAttrs_class.keys())
        longTypes = self.longTypes & set(
            x.classType for x in self.recAttrs_class)
        progress.setFull(len(self.sourceMods))
        cachedMasters = {}
        for index,srcMod in enumerate(self.sourceMods):
            temp_id_data = {}
            if srcMod not in bosh.modInfos: continue
            srcInfo = bosh.modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            masters = srcInfo.header.masters
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass,recAttrs in recAttrs_class.iteritems():
                if recClass.classType not in srcFile.tops: continue
                self.srcClasses.add(recClass)
                self.classestemp.add(recClass)
                recFidAttrs = self.recFidAttrs_class.get(recClass, None)
                for record in srcFile.tops[
                    recClass.classType].getActiveRecords():
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
                                mod_skipcount = self.patchFile\
                                    .patcher_mod_skipcount.setdefault(
                                    self.name, {})
                                mod_skipcount[
                                    srcMod] = mod_skipcount.setdefault(srcMod,
                                                                       0) + 1
                                break
                        else:
                            temp_id_data[fid] = dict(
                                (attr, record.__getattribute__(attr)) for attr
                                in recAttrs)
                            temp_id_data[fid].update(attr_fidvalue)
                    else:
                        temp_id_data[fid] = dict(
                            (attr, record.__getattribute__(attr)) for attr in
                            recAttrs)
            for master in masters:
                if not master in bosh.modInfos: continue  # or break
                # filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = bosh.modInfos[master]
                    masterFile = ModFile(masterInfo,loadFactory)
                    masterFile.load(True)
                    masterFile.convertToLongFids(longTypes)
                    cachedMasters[master] = masterFile
                mapper = masterFile.getLongMapper()
                for recClass,recAttrs in recAttrs_class.iteritems():
                    if recClass.classType not in masterFile.tops: continue
                    if recClass not in self.classestemp: continue
                    for record in masterFile.tops[
                        recClass.classType].getActiveRecords():
                        fid = mapper(record.fid)
                        if fid not in temp_id_data: continue
                        for attr, value in temp_id_data[fid].iteritems():
                            if value == record.__getattribute__(attr): continue
                            else:
                                if fid not in id_data: id_data[fid] = dict()
                                try:
                                    id_data[fid][attr] = temp_id_data[fid][
                                        attr]
                                except KeyError:
                                    id_data[fid].setdefault(attr,value)
            progress.plus()
        temp_id_data = None
        self.longTypes = self.longTypes & set(
            x.classType for x in self.srcClasses)
        self.isActive = bool(self.srcClasses)

    def scanModFile(self, modFile, progress):
         _scanModFile(self,modFile)

    @staticmethod
    def _inner_loop(id_data, keep, modFileTops, type, type_count):
        for record in modFileTops[type].records:
            fid = record.fid
            if fid not in id_data: continue
            for attr, value in id_data[fid].iteritems():
                if isinstance(record.__getattribute__(attr),
                              basestring) and isinstance(value, basestring):
                    if record.__getattribute__(attr).lower() != value.lower():
                        break
                    continue
                elif attr == 'model':
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
            type_count[type] += 1

    def buildPatch(self,log,progress):
        """Merge last version of record with patched graphics data as
        needed."""
        _buildPatch(self,log,inner_for=self.__class__._inner_loop)

class CBash_GraphicsPatcher(CBash_ImportPatcher):
    """Merges changes to graphics (models and icons)."""
    name = _(u'Import Graphics')
    text = _(u"Import graphics (models, icons, etc.) from source mods.")
    tip = text
    autoKey = {u'Graphics'}

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.fid_attr_value = {}
        self.mod_count = {}
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
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        attr_value = record.ConflictDetails(self.class_attrs[record._Type])
        if not ValidateDict(attr_value, self.patchFile):
            mod_skipcount = self.patchFile.patcher_mod_skipcount.setdefault(
                self.name, {})
            mod_skipcount[modFile.GName] = mod_skipcount.setdefault(
                modFile.GName, 0) + 1
            return
        self.fid_attr_value.setdefault(record.fid,{}).update(attr_value)

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
                    class_mod_count = self.mod_count
                    class_mod_count.setdefault(record._Type, {})[
                        modFile.GName] = class_mod_count.setdefault(
                        record._Type, {}).get(modFile.GName, 0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def _clog(self, log):  # type 11
        mod_count = self.mod_count
        self._srcMods(log)
        log(u'\n=== ' + _(u'Modified Records'))
        for type in mod_count.keys():
            log(u'* ' + _(u'Modified %s Records: %d') % (
                type, sum(mod_count[type].values())))
            for srcMod in bosh.modInfos.getOrdered(
                    mod_count[type].keys()):
                log(u'  * %s: %d' % (srcMod.s, mod_count[type][srcMod]))
        self.mod_count = {}

#------------------------------------------------------------------------------
class ActorImporter(ImportPatcher):
    """Merges changes to actors."""
    name = _(u'Import Actors')
    text = _(u"Import Actor components from source mods.")
    tip = text
    autoKey = (u'Actors.AIData', u'Actors.Stats', u'Actors.ACBS', u'NPC.Class',
               u'Actors.CombatStyle', u'Creatures.Blood', u'NPC.Race',
               u'Actors.Skeleton')

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_data = {} #--Names keyed by long fid.
        self.srcClasses = set() #--Record classes actually provided by src mods/files.
        self.sourceMods = self.getConfigChecked()
        self.isActive = len(self.sourceMods) != 0
        self.classestemp = set()
        #--Type Fields
        recAttrs_class = self.recAttrs_class = {}
        self.actorClasses = (MreRecord.type_class['NPC_'],MreRecord.type_class['CREA'])
        for recClass in (MreRecord.type_class[x] for x in ('NPC_',)):
            self.recAttrs_class[recClass] = {
                u'Actors.AIData': ('aggression','confidence','energyLevel','responsibility','services','trainSkill','trainLevel'),
                u'Actors.Stats': ('skills','health','attributes'),
                u'Actors.ACBS': (('baseSpell','fatigue','level','calcMin','calcMax','flags.autoCalc','flags.pcLevelOffset'),
                                'barterGold','flags.female','flags.essential','flags.respawn','flags.noLowLevel',
                                'flags.noRumors','flags.summonable','flags.noPersuasion','flags.canCorpseCheck',
                                ),
                #u'Actors.ACBS': ('baseSpell','fatigue','barterGold','level','calcMin','calcMax','flags'),
                u'NPC.Class': ('iclass',),
                u'NPC.Race': ('race',),
                u'Actors.CombatStyle': ('combatStyle',),
                u'Creatures.Blood': (),
                u'Actors.Skeleton': ('model',),
                }
        for recClass in (MreRecord.type_class[x] for x in ('CREA',)):
            self.recAttrs_class[recClass] = {
                u'Actors.AIData': ('aggression','confidence','energyLevel','responsibility','services','trainSkill','trainLevel'),
                u'Actors.Stats': ('combat','magic','stealth','soul','health','attackDamage','strength','intelligence','willpower','agility','speed','endurance','personality','luck'),
                u'Actors.ACBS': (('baseSpell','fatigue','level','calcMin','calcMax','flags.pcLevelOffset',),
                                'barterGold','flags.biped','flags.essential','flags.weaponAndShield',
                                'flags.respawn','flags.swims','flags.flies','flags.walks','flags.noLowLevel',
                                'flags.noBloodSpray','flags.noBloodDecal','flags.noHead','flags.noRightArm',
                                'flags.noLeftArm','flags.noCombatInWater','flags.noShadow','flags.noCorpseCheck',
                                ),
                #u'Actors.ACBS': ('baseSpell','fatigue','barterGold','level','calcMin','calcMax','flags'),
                u'NPC.Class': (),
                u'NPC.Race': (),
                u'Actors.CombatStyle': ('combatStyle',),
                u'Creatures.Blood': ('bloodSprayPath','bloodDecalPath'),
                u'Actors.Skeleton': ('model',),
                }
        #--Needs Longs
        self.longTypes = {'CREA', 'NPC_'}

    def initData(self,progress):
        """Get graphics from source files."""
        if not self.isActive: return
        id_data = self.id_data
        recAttrs_class = self.recAttrs_class
        loadFactory = LoadFactory(False,MreRecord.type_class['NPC_'],
                                        MreRecord.type_class['CREA'])
        longTypes =self.longTypes & set(x.classType for x in self.actorClasses)
        progress.setFull(len(self.sourceMods))
        cachedMasters = {}
        for index,srcMod in enumerate(self.sourceMods):
            temp_id_data = {}
            if srcMod not in bosh.modInfos: continue
            srcInfo = bosh.modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            masters = srcInfo.header.masters
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for actorClass in self.actorClasses:
                if actorClass.classType not in srcFile.tops: continue
                self.srcClasses.add(actorClass)
                self.classestemp.add(actorClass)
                attrs = set(reduce(operator.add,
                               (self.recAttrs_class[actorClass][bashKey]
                                for bashKey in srcInfo.getBashTags() if
                                bashKey in self.recAttrs_class[actorClass])))
                for record in srcFile.tops[
                    actorClass.classType].getActiveRecords():
                    fid = mapper(record.fid)
                    temp_id_data[fid] = dict()
                    for attr in attrs:
                        if isinstance(attr,basestring):
                            temp_id_data[fid][attr] = \
                                reduce(getattr,attr.split('.'),record)
                        elif isinstance(attr,(list,tuple,set)):
                            temp_id_data[fid][attr] = dict(
                            (subattr,reduce(getattr,subattr.split('.'),record))
                                    for subattr in attr)
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
                for actorClass in self.actorClasses:
                    if actorClass.classType not in masterFile.tops: continue
                    if actorClass not in self.classestemp: continue
                    for record in masterFile.tops[
                        actorClass.classType].getActiveRecords():
                        fid = mapper(record.fid)
                        if fid not in temp_id_data: continue
                        for attr, value in temp_id_data[fid].iteritems():
                            if isinstance(attr,basestring):
                                if value == reduce(getattr, attr.split('.'),
                                                   record):
                                    continue
                                else:
                                    if fid not in id_data: id_data[
                                        fid] = dict()
                                    try:
                                        id_data[fid][attr] = temp_id_data[fid][
                                            attr]
                                    except KeyError:
                                        id_data[fid].setdefault(attr,value)
                            elif isinstance(attr,(list,tuple,set)):
                                temp_values = {}
                                keep = False
                                for subattr in attr:
                                    if value[subattr] != reduce(
                                            getattr,subattr.split('.'),record):
                                        keep = True
                                    temp_values[subattr] = value[subattr]
                                if keep:
                                    id_data.setdefault(fid, {})
                                    id_data[fid].update(temp_values)
            progress.plus()
        temp_id_data = None
        self.longTypes = self.longTypes & set(
            x.classType for x in self.srcClasses)
        self.isActive = bool(self.srcClasses)

    def scanModFile(self, modFile, progress):
        """Scan mod file against source data."""
        if not self.isActive: return
        id_data = self.id_data
        modName = modFile.fileInfo.name
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

    @staticmethod
    def _inner_loop(id_data, keep, modFileTops, type, type_count):
        for record in modFileTops[type].records:
            fid = record.fid
            if fid not in id_data: continue
            for attr, value in id_data[fid].iteritems():
                if reduce(getattr, attr.split('.'), record) != value: break
            else: continue
            for attr, value in id_data[fid].iteritems():
                setattr(reduce(getattr, attr.split('.')[:-1], record),
                        attr.split('.')[-1], value)
            keep(fid)
            type_count[type] += 1

    def buildPatch(self,log,progress):
       _buildPatch(self,log,inner_for=self.__class__._inner_loop)

class CBash_ActorImporter(CBash_ImportPatcher):
    """Merges changes to actors."""
    name = _(u'Import Actors')
    text = _(u"Import Actor components from source mods.")
    tip = text
    autoKey = {u'Actors.AIData', u'Actors.Stats', u'Actors.ACBS', u'NPC.Class',
               u'Actors.CombatStyle', u'Creatures.Blood', u'NPC.Race',
               u'Actors.Skeleton'}

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.fid_attr_value = {}
        self.mod_count = {}
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
                if not ValidateDict(attr_value, self.patchFile):
                    mod_skipcount = self.patchFile.patcher_mod_skipcount.setdefault(self.name,{})
                    mod_skipcount[modFile.GName] = mod_skipcount.setdefault(modFile.GName, 0) + 1
                    continue
                self.fid_attr_value.setdefault(record.fid,{}).update(attr_value)

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
                    class_mod_count = self.mod_count
                    class_mod_count.setdefault(record._Type,{})[modFile.GName] = class_mod_count.setdefault(record._Type,{}).get(modFile.GName,0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def _clog(self, log):  # type 11
        mod_count = self.mod_count
        self._srcMods(log)
        log(u'\n=== ' + _(u'Modified Records'))
        for type in mod_count.keys():
            log(u'* ' + _(u'Modified %s Records: %d') % (
                type, sum(mod_count[type].values())))
            for srcMod in bosh.modInfos.getOrdered(mod_count[type].keys()):
                log(u'  * %s: %d' % (srcMod.s, mod_count[type][srcMod]))
        self.mod_count = {}

#------------------------------------------------------------------------------
class KFFZPatcher(ImportPatcher):
    """Merges changes to actor animation lists."""
    name = _(u'Import Actors: Animations')
    text = _(u"Import Actor animations from source mods.")
    tip = text
    autoKey = u'Actors.Anims'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_data = {} #--Names keyed by long fid.
        self.srcClasses = set() #--Record classes actually provided by src
        #  mods/files.
        self.sourceMods = self.getConfigChecked()
        self.isActive = len(self.sourceMods) != 0
        self.classestemp = set()
        #--Type Fields
        recAttrs_class = self.recAttrs_class = {}
        for recClass in (MreRecord.type_class[x] for x in ('CREA','NPC_')):
            recAttrs_class[recClass] = ('animations',)
        #--Needs Longs
        self.longTypes = {'CREA', 'NPC_'}

    def initData(self,progress):
        """Get actor animation lists from source files."""
        if not self.isActive: return
        id_data = self.id_data
        recAttrs_class = self.recAttrs_class
        loadFactory = LoadFactory(False,*recAttrs_class.keys())
        longTypes = self.longTypes & set(
            x.classType for x in self.recAttrs_class)
        progress.setFull(len(self.sourceMods))
        cachedMasters = {}
        for index,srcMod in enumerate(self.sourceMods):
            temp_id_data = {}
            if srcMod not in bosh.modInfos: continue
            srcInfo = bosh.modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            masters = srcInfo.header.masters
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass,recAttrs in recAttrs_class.iteritems():
                if recClass.classType not in srcFile.tops: continue
                self.srcClasses.add(recClass)
                self.classestemp.add(recClass)
                for record in srcFile.tops[
                    recClass.classType].getActiveRecords():
                    fid = mapper(record.fid)
                    temp_id_data[fid] = dict(
                        (attr, record.__getattribute__(attr)) for attr in
                        recAttrs)
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
                for recClass,recAttrs in recAttrs_class.iteritems():
                    if recClass.classType not in masterFile.tops: continue
                    if recClass not in self.classestemp: continue
                    for record in masterFile.tops[
                        recClass.classType].getActiveRecords():
                        fid = mapper(record.fid)
                        if fid not in temp_id_data: continue
                        for attr, value in temp_id_data[fid].iteritems():
                            if value == record.__getattribute__(attr): continue
                            else:
                                if fid not in id_data: id_data[fid] = dict()
                                try:
                                    id_data[fid][attr] =temp_id_data[fid][attr]
                                except KeyError:
                                    id_data[fid].setdefault(attr,value)
            progress.plus()
        temp_id_data = None
        self.longTypes = self.longTypes & set(
            x.classType for x in self.srcClasses)
        self.isActive = bool(self.srcClasses)

    def scanModFile(self, modFile, progress):
         _scanModFile(self,modFile)

    @staticmethod
    def _inner_loop(id_data, keep, modFileTops, type, type_count):
        for record in modFileTops[type].records:
            fid = record.fid
            if fid not in id_data: continue
            for attr, value in id_data[fid].iteritems():
                if record.__getattribute__(attr) != value: break
            else: continue
            for attr, value in id_data[fid].iteritems():
                record.__setattr__(attr, value)
            keep(fid)
            type_count[type] += 1

    def buildPatch(self,log,progress):
        _buildPatch(self,log,inner_for=self.__class__._inner_loop)

class CBash_KFFZPatcher(CBash_ImportPatcher):
    """Merges changes to actor animations."""
    name = _(u'Import Actors: Animations')
    text = _(u"Import Actor animations from source mods.")
    tip = text
    autoKey = {u'Actors.Anims'}
    logMsg = u'* ' + _(u'Imported Animations') + u': %d'

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.id_animations = {}
        self.mod_count = {}

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CREA','NPC_']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        animations = self.id_animations.setdefault(record.fid,[])
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
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class NPCAIPackagePatcher(ImportPatcher):
    """Merges changes to the AI Packages of Actors."""
    name = _(u'Import Actors: AI Packages')
    text = _(u"Import Actor AI Package links from source mods.")
    tip = text
    autoKey = (u'Actors.AIPackages',u'Actors.AIPackagesForceAdd')
    logMsg = _(u'AI Package Lists Changed') + u': %d'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.sourceMods = self.getConfigChecked()
        self.isActive = len(self.sourceMods) != 0
        self.data = {}
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
        progress.setFull(len(self.sourceMods))
        cachedMasters = {}
        data = self.data
        for index,srcMod in enumerate(self.sourceMods):
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
                        if fid in data:
                            if tempData[fid] == data[fid]['merged']: continue
                        recordData = {'deleted':[],'merged':tempData[fid]}
                        for pkg in list(record.aiPackages):
                            if not pkg in tempData[fid]:
                                recordData['deleted'].append(pkg)
                        if not fid in data:
                            data[fid] = recordData
                        else:
                            for pkg in recordData['deleted']:
                                if pkg in data[fid]['merged']:
                                    data[fid]['merged'].remove(pkg)
                                data[fid]['deleted'].append(pkg)
                            if data[fid]['merged'] == []:
                                for pkg in recordData['merged']:
                                    if pkg in data[fid]['deleted'] and not \
                                      u'Actors.AIPackagesForceAdd' in bashTags:
                                        continue
                                    data[fid]['merged'].append(pkg)
                                continue
                            for index, pkg in enumerate(recordData['merged']):
                                if not pkg in data[fid]['merged']:  # so needs
                                    #  to be added... (unless deleted that is)
                                    # find the correct position to add and add.
                                    if pkg in data[fid]['deleted'] and not \
                                      u'Actors.AIPackagesForceAdd' in bashTags:
                                        continue  # previously deleted
                                    self._insertPackage(data, fid, index, pkg,
                                                        recordData)
                                    continue # Done with this package
                                elif index == data[fid]['merged'].index(
                                        pkg) or (
                                    len(recordData['merged']) - index) == (
                                    len(data[fid]['merged']) - data[fid][
                                    'merged'].index(pkg)):
                                    continue  # pkg same in both lists.
                                else:  # this import is later loading so we'll
                                    #  assume it is better order
                                    data[fid]['merged'].remove(pkg)
                                    self._insertPackage(data, fid, index, pkg,
                                                     recordData)
            progress.plus()

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('NPC_','CREA',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('NPC_','CREA',) if self.isActive else ()

    def scanModFile(self, modFile, progress):
        """Add record from modFile."""
        if not self.isActive: return
        data = self.data
        mapper = modFile.getLongMapper()
        modName = modFile.fileInfo.name
        for type in ('NPC_','CREA'):
            patchBlock = getattr(self.patchFile,type)
            for record in getattr(modFile,type).getActiveRecords():
                fid = mapper(record.fid)
                if fid in data:
                    if list(record.aiPackages) != data[fid]['merged']:
                        patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress):
        """Applies delta to patchfile."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        data = self.data
        mod_count = {}
        for type in ('NPC_','CREA'):
            for record in getattr(self.patchFile,type).records:
                fid = record.fid
                if not fid in data: continue
                changed = False
                if record.aiPackages != data[fid]['merged']:
                    record.aiPackages = data[fid]['merged']
                    changed = True
                if changed:
                    keep(record.fid)
                    mod = record.fid[0]
                    mod_count[mod] = mod_count.get(mod,0) + 1
        self._patchLog(log,mod_count,logMsg=u'\n=== ' + self.__class__.logMsg)

    def _plog(self,log,logMsg,mod_count): # type 1
        log(logMsg % sum(mod_count.values()))
        for mod in bosh.modInfos.getOrdered(mod_count):
            log(u'* %s: %3d' % (mod.s,mod_count[mod]))

class CBash_NPCAIPackagePatcher(CBash_ImportPatcher):
    """Merges changes to the AI Packages of Actors."""
    name = _(u'Import Actors: AI Packages')
    text = _(u"Import Actor AI Package links from source mods.")
    tip = text
    autoKey = {u'Actors.AIPackages', u'Actors.AIPackagesForceAdd'}
    scanRequiresChecked = False
    logMsg = u'* ' + _(u'AI Package Lists Changed') + u': %d'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.previousPackages = {}
        self.mergedPackageList = {}
        self.mod_count = {}

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CREA','NPC_']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        aiPackages = record.aiPackages
        if not ValidateList(aiPackages, self.patchFile):
            mod_skipcount = self.patchFile.patcher_mod_skipcount.setdefault(
                self.name, {})
            mod_skipcount[modFile.GName] = mod_skipcount.setdefault(
                modFile.GName, 0) + 1
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
                    mod_count = self.mod_count
                    mod_count[modFile.GName] = mod_count.get(modFile.GName,
                                                             0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class DeathItemPatcher(ImportPatcher):
    """Merges changes to actor death items."""
    name = _(u'Import Actors: Death Items')
    text = _(u"Import Actor death items from source mods.")
    tip = text
    autoKey = u'Actors.DeathItem'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_data = {} #--Names keyed by long fid.
        self.srcClasses = set() #--Record classes actually provided by src
        # mods/files.
        self.sourceMods = self.getConfigChecked()
        self.isActive = len(self.sourceMods) != 0
        #--Type Fields
        recAttrs_class = self.recAttrs_class = {}
        for recClass in (MreRecord.type_class[x] for x in ('CREA','NPC_')):
            recAttrs_class[recClass] = ('deathItem',)
        #--Needs Longs
        self.longTypes = {'CREA', 'NPC_'}

    def initData(self,progress):
        """Get actor death items from source files."""
        if not self.isActive: return
        self.classestemp = set()
        id_data = self.id_data
        recAttrs_class = self.recAttrs_class
        loadFactory = LoadFactory(False,*recAttrs_class.keys())
        longTypes = self.longTypes & set(x.classType for x in self.recAttrs_class)
        progress.setFull(len(self.sourceMods))
        cachedMasters = {}
        for index,srcMod in enumerate(self.sourceMods):
            temp_id_data = {}
            if srcMod not in bosh.modInfos: continue
            srcInfo = bosh.modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            masters = srcInfo.header.masters
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass,recAttrs in recAttrs_class.iteritems():
                if recClass.classType not in srcFile.tops: continue
                self.srcClasses.add(recClass)
                self.classestemp.add(recClass)
                for record in srcFile.tops[recClass.classType].getActiveRecords():
                    fid = mapper(record.fid)
                    temp_id_data[fid] = dict((attr,record.__getattribute__(attr)) for attr in recAttrs)
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
                for recClass,recAttrs in recAttrs_class.iteritems():
                    if recClass.classType not in masterFile.tops: continue
                    if recClass not in self.classestemp: continue
                    for record in masterFile.tops[recClass.classType].getActiveRecords():
                        fid = mapper(record.fid)
                        if fid not in temp_id_data: continue
                        for attr, value in temp_id_data[fid].iteritems():
                            if value == record.__getattribute__(attr): continue
                            else:
                                if fid not in id_data: id_data[fid] = dict()
                                try:
                                    id_data[fid][attr] = temp_id_data[fid][attr]
                                except KeyError:
                                    id_data[fid].setdefault(attr,value)
            progress.plus()
        temp_id_data = None
        self.longTypes = self.longTypes & set(x.classType for x in self.srcClasses)
        self.isActive = bool(self.srcClasses)

    def scanModFile(self, modFile, progress):
         _scanModFile(self,modFile)

    @staticmethod
    def _inner_loop(id_data, keep, modFileTops, type, type_count):
        # deprint(recClass,type,type_count[type])
        for record in modFileTops[type].records:
            fid = record.fid
            if fid not in id_data: continue
            for attr, value in id_data[fid].iteritems():
                if record.__getattribute__(attr) != value: break
            else: continue
            for attr, value in id_data[fid].iteritems():
                record.__setattr__(attr, value)
            keep(fid)
            type_count[type] += 1

    def buildPatch(self,log,progress):
        """Merge last version of record with patched actor death item as
        needed."""
        _buildPatch(self,log,inner_for=self.__class__._inner_loop)

class CBash_DeathItemPatcher(CBash_ImportPatcher):
    """Imports actor death items."""
    name = _(u'Import Actors: Death Items')
    text = _(u"Import Actor death items from source mods.")
    tip = text
    autoKey = {u'Actors.DeathItem'}
    logMsg = u'* ' + _(u'Imported Death Items') + u': %d'

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.id_deathItem = {}
        self.mod_count = {}

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
                mod_skipcount = \
                    self.patchFile.patcher_mod_skipcount.setdefault(
                    self.name, {})
                mod_skipcount[modFile.GName] = mod_skipcount.setdefault(
                    modFile.GName, 0) + 1

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        if recordId in self.id_deathItem and record.deathItem != \
                self.id_deathItem[recordId]:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.deathItem = self.id_deathItem[recordId]
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

    def _clog(self,log): # type 2
        self._srcMods(log)
        super(CBash_DeathItemPatcher, self)._clog(log)

#------------------------------------------------------------------------------
class ImportFactions(ImportPatcher):
    """Import factions to creatures and NPCs."""
    name = _(u'Import Factions')
    text = _(u"Import factions from source mods/files.")
    logMsg = _(u'Refactioned Actors')
    autoKey = u'Factions'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_data= {} #--Factions keyed by long fid. WAS: id_factions
        self.activeTypes = []  #--Types ('CREA','NPC_') of data actually
        # provided by src mods/files.
        self.sourceMods = self.getConfigChecked()
        self.isActive = bool(self.sourceMods)

    def initData(self,progress):
        """Get names from source files."""
        if not self.isActive: return
        actorFactions = ActorFactions(aliases=self.patchFile.aliases)
        progress.setFull(len(self.sourceMods))
        for srcFile in self.sourceMods:
            srcPath = GPath(srcFile)
            patchesList = getPatchesList()
            if reModExt.search(srcFile.s):
                if srcPath not in bosh.modInfos: continue
                srcInfo = bosh.modInfos[GPath(srcFile)]
                actorFactions.readFromMod(srcInfo)
            else:
                if srcPath not in patchesList: continue
                actorFactions.readFromText(getPatchesPath(srcFile))
            progress.plus()
        #--Finish
        id_factions= self.id_data
        for type,aFid_factions in actorFactions.type_id_factions.iteritems():
            if type not in ('CREA','NPC_'): continue
            self.activeTypes.append(type)
            for longid,factions in aFid_factions.iteritems():
                self.id_data[longid] = factions
        self.isActive = bool(self.activeTypes)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return tuple(self.activeTypes) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return tuple(self.activeTypes) if self.isActive else()

    def scanModFile(self, modFile, progress):
        """Scan modFile."""
        if not self.isActive: return
        id_factions = self.id_data
        modName = modFile.fileInfo.name
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

    def _inner_loop(self, id_data, keep, modFileTops, type, type_count):
        for record in modFileTops[type].records:
            fid = record.fid
            if fid not in id_data: continue
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
                type_count[type] += 1
                keep(fid)

    def buildPatch(self,log,progress):
        """Make changes to patchfile."""
        if not self.isActive: return
        modFileTops = self.patchFile.tops
        keep = self.patchFile.getKeeper()
        id_data= self.id_data
        type_count = {}
        for type in self.activeTypes: # TODO: activeTypes in all patchers ?
            if type not in modFileTops: continue
            type_count[type] = 0
            self._inner_loop(id_data, keep, modFileTops, type, type_count)
        self._patchLog(log, type_count,
                       modsHeader=u'=== ' + _(u'Source Mods/Files'),
                       logMsg=(u'\n=== ' + self.__class__.logMsg))

class CBash_ImportFactions(CBash_ImportPatcher):
    """Import factions to creatures and NPCs."""
    name = _(u'Import Factions')
    text = _(u"Import factions from source mods/files.")
    autoKey = {u'Factions'}

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.id_factions = {}
        self.csvId_factions = {}
        self.mod_count = {}

    def initData(self,group_patchers,progress):
        if not self.isActive: return
        CBash_ImportPatcher.initData(self,group_patchers,progress)
        actorFactions = CBash_ActorFactions(aliases=self.patchFile.aliases)
        progress.setFull(len(self.srcs))
        patchesList = getPatchesList()
        for srcFile in self.srcs:
            srcPath = GPath(srcFile)
            if not reModExt.search(srcFile.s):
                if srcPath not in patchesList: continue
                actorFactions.readFromText(getPatchesPath(srcFile))
            progress.plus()
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
                class_mod_count = self.mod_count
                class_mod_count.setdefault(record._Type, {})[
                    modFile.GName] = class_mod_count.setdefault(record._Type,
                    {}).get(modFile.GName, 0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

    def _clog(self,log): # type 12
        mod_count = self.mod_count
        for type in mod_count.keys():
            log(u'* ' + _(u'Refactioned %s Records: %d') % (
                type, sum(mod_count[type].values()),))
            for srcMod in bosh.modInfos.getOrdered(mod_count[type].keys()):
                log(u'  * %s: %d' % (srcMod.s,mod_count[type][srcMod]))
        self.mod_count = {}

#------------------------------------------------------------------------------
class ImportRelations(ImportPatcher):
    """Import faction relations to factions."""
    name = _(u'Import Relations')
    text = _(u"Import relations from source mods/files.")
    autoKey = u'Relations'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_relations = {}  #--[(otherLongid0,disp0),(...)] =
        # id_relations[mainLongid].
        self.sourceMods = self.getConfigChecked()
        self.isActive = bool(self.sourceMods)

    def initData(self,progress):
        """Get names from source files."""
        if not self.isActive: return
        factionRelations = FactionRelations(aliases=self.patchFile.aliases)
        progress.setFull(len(self.sourceMods))
        for srcFile in self.sourceMods:
            srcPath = GPath(srcFile)
            patchesList = getPatchesList()
            if reModExt.search(srcFile.s):
                if srcPath not in bosh.modInfos: continue
                srcInfo = bosh.modInfos[GPath(srcFile)]
                factionRelations.readFromMod(srcInfo)
            else:
                if srcPath not in patchesList: continue
                factionRelations.readFromText(getPatchesPath(srcFile))
            progress.plus()
        #--Finish
        for fid, relations in factionRelations.id_relations.iteritems():
            if fid and (
                    fid[0] is not None and fid[0] in self.patchFile.loadSet):
                filteredRelations = [relation for relation in relations if
                                     relation[0] and (
                                     relation[0][0] is not None and
                                     relation[0][0] in self.patchFile.loadSet)]
                if filteredRelations:
                    self.id_relations[fid] = filteredRelations
        self.isActive = bool(self.id_relations)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('FACT',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('FACT',) if self.isActive else ()

    def scanModFile(self, modFile, progress):
        """Scan modFile."""
        if not self.isActive: return
        id_relations= self.id_relations
        modName = modFile.fileInfo.name
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

    def buildPatch(self,log,progress):
        """Make changes to patchfile."""
        if not self.isActive: return
        modFile = self.patchFile
        keep = self.patchFile.getKeeper()
        id_relations= self.id_relations
        type_count = {}
        for type in ('FACT',):
            if type not in modFile.tops: continue
            type_count[type] = 0
            for record in modFile.tops[type].records:
                fid = record.fid
                if fid in id_relations:
                    newRelations = set(id_relations[fid])
                    curRelations = set(
                        (x.faction, x.mod) for x in record.relations)
                    changed = newRelations - curRelations
                    if not changed: continue
                    doKeep = False
                    for faction,disp in changed:
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
                        type_count[type] += 1
                        keep(fid)
        self._patchLog(log, type_count,
                       modsHeader=u'=== ' + _(u'Source Mods/Files'),
                       logMsg=u'\n=== ' + _(u'Modified Factions') + u': %d')

    def _plog(self,log,logMsg,type_count):
        log(logMsg % type_count['FACT'])

class CBash_ImportRelations(CBash_ImportPatcher):
    """Import faction relations to factions."""
    name = _(u'Import Relations')
    text = _(u"Import relations from source mods/files.")
    autoKey = {u'Relations'}
    logMsg = u'* ' + _(u'Re-Relationed Records') + u': %d'

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.fid_faction_mod = {}
        self.csvFid_faction_mod = {}
        self.mod_count = {}

    def initData(self,group_patchers,progress):
        if not self.isActive: return
        CBash_ImportPatcher.initData(self,group_patchers,progress)
        factionRelations = CBash_FactionRelations(
            aliases=self.patchFile.aliases)
        progress.setFull(len(self.srcs))
        patchesList = getPatchesList()
        for srcFile in self.srcs:
            srcPath = GPath(srcFile)
            if not reModExt.search(srcFile.s):
                if srcPath not in patchesList: continue
                factionRelations.readFromText(getPatchesPath(srcFile))
            progress.plus()
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
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class ImportScripts(ImportPatcher):
    """Imports attached scripts on objects."""
    name = _(u'Import Scripts')
    text = _(u"Import Scripts on containers, plants, misc, weapons etc. from "
             u"source mods.")
    tip = text
    autoKey = u'Scripts'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_data = {} #--Names keyed by long fid.
        self.srcClasses = set()  # --Record classes actually provided by src
        #  mods/files.
        self.sourceMods = self.getConfigChecked()
        self.isActive = len(self.sourceMods) != 0
        #--Type Fields
        recAttrs_class = self.recAttrs_class = {}
        self.longTypes = {'WEAP', 'ACTI', 'ALCH', 'APPA', 'ARMO', 'BOOK',
                          'CLOT', 'CONT', 'CREA', 'DOOR', 'FLOR', 'FURN',
                          'INGR', 'KEYM', 'LIGH', 'MISC', 'NPC_', 'QUST',
                          'SGST', 'SLGM'}
        for recClass in (MreRecord.type_class[x] for x in self.longTypes):
            recAttrs_class[recClass] = ('script',)

    def initData(self,progress):
        """Get script links from source files."""
        if not self.isActive: return
        self.classestemp = set()
        id_data = self.id_data
        recAttrs_class = self.recAttrs_class
        loadFactory = LoadFactory(False,*recAttrs_class.keys())
        longTypes = self.longTypes & set(
            x.classType for x in self.recAttrs_class)
        progress.setFull(len(self.sourceMods))
        cachedMasters = {}
        for index,srcMod in enumerate(self.sourceMods):
            temp_id_data = {}
            if srcMod not in bosh.modInfos: continue
            srcInfo = bosh.modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            masters = srcInfo.header.masters
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass,recAttrs in recAttrs_class.iteritems():
                if recClass.classType not in srcFile.tops: continue
                self.srcClasses.add(recClass)
                self.classestemp.add(recClass)
                for record in srcFile.tops[
                    recClass.classType].getActiveRecords():
                    fid = mapper(record.fid)
                    temp_id_data[fid] = dict(
                        (attr, record.__getattribute__(attr)) for attr in
                        recAttrs)
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
                for recClass,recAttrs in recAttrs_class.iteritems():
                    if recClass.classType not in masterFile.tops: continue
                    if recClass not in self.classestemp: continue
                    for record in masterFile.tops[
                        recClass.classType].getActiveRecords():
                        fid = mapper(record.fid)
                        if fid not in temp_id_data: continue
                        for attr, value in temp_id_data[fid].iteritems():
                            if value == record.__getattribute__(attr): continue
                            else:
                                if fid not in id_data: id_data[fid] = dict()
                                try:
                                    id_data[fid][attr] =temp_id_data[fid][attr]
                                except KeyError:
                                    id_data[fid].setdefault(attr,value)
            progress.plus()
        temp_id_data = None
        self.longTypes = self.longTypes & set(
            x.classType for x in self.srcClasses)
        self.isActive = bool(self.srcClasses)

    def scanModFile(self, modFile, progress):
         _scanModFile(self,modFile)

    @staticmethod
    def _inner_loop(id_data, keep, modFileTops, type, type_count):
        for record in modFileTops[type].records:
            fid = record.fid
            if fid not in id_data: continue
            for attr, value in id_data[fid].iteritems():
                if record.__getattribute__(attr) != value: break
            else: continue
            for attr, value in id_data[fid].iteritems():
                record.__setattr__(attr, value)
            keep(fid)
            type_count[type] += 1

    def buildPatch(self,log,progress):
        """Merge last version of record with patched scripts link as needed."""
        _buildPatch(self,log,inner_for=self.__class__._inner_loop)

class CBash_ImportScripts(CBash_ImportPatcher):
    """Imports attached scripts on objects."""
    name = _(u'Import Scripts')
    text = _(u"Import Scripts on containers, plants, misc, weapons etc from "
             u"source mods.")
    tip = text
    autoKey = {u'Scripts'}

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.id_script = {}
        self.mod_count = {}

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
                mod_skipcount = \
                    self.patchFile.patcher_mod_skipcount.setdefault(
                    self.name, {})
                mod_skipcount[modFile.GName] = mod_skipcount.setdefault(
                    modFile.GName, 0) + 1

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        if recordId in self.id_script and record.script != self.id_script[
            recordId]:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.script = self.id_script[recordId]
                class_mod_count = self.mod_count
                class_mod_count.setdefault(record._Type, {})[
                    modFile.GName] = class_mod_count.setdefault(record._Type,
                    {}).get(modFile.GName, 0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

    def _clog(self, log):  # type 11
        mod_count = self.mod_count
        self._srcMods(log)
        log(u'\n=== ' + _(u'Modified Records'))
        for type in mod_count.keys():
            log(u'* ' + _(u'Modified %s Records: %d') % (
                type, sum(mod_count[type].values())))
            for srcMod in bosh.modInfos.getOrdered(mod_count[type].keys()):
                log(u'  * %s: %d' % (srcMod.s, mod_count[type][srcMod]))
        self.mod_count = {}

#------------------------------------------------------------------------------
