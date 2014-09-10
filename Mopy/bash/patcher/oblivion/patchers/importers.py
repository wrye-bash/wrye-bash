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
import bash # to make bash.bosh.modInfos resolve...
from bash.bosh import LoadFactory, ModFile, CountDict
from bash.brec import MreRecord
from bash.patcher.base import AImportPatcher
from bash.patcher.oblivion.patchers.base import ImportPatcher, \
    CBash_ImportPatcher
from bash.cint import ValidateDict
from bash.patcher.base import Patcher

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
            if srcMod not in bash.bosh.modInfos: continue
            tempCellData = {'Maps':{}}
            srcInfo = bash.bosh.modInfos[srcMod]
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
                if not master in bash.bosh.modInfos: continue  # or break
                # filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = bash.bosh.modInfos[master]
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

    def _plog(self,log,logMsg,count):
        log(logMsg)
        for srcMod in bash.bosh.modInfos.getOrdered(count.keys()):
            log(u'* %s: %d' % (srcMod.s,count[srcMod]))

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
            if srcMod not in bash.bosh.modInfos: continue
            srcInfo = bash.bosh.modInfos[srcMod]
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
                if not master in bash.bosh.modInfos: continue  # or break
                # filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = bash.bosh.modInfos[master]
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
                    if record.__getattribute__(attr) != value:
                        patchBlock.setRecord(record.getTypeCopy(mapper))
                        break

    def buildPatch(self,log,progress):
        """Merge last version of record with patched graphics data as
        needed."""
        if not self.isActive: return
        modFile = self.patchFile
        keep = self.patchFile.getKeeper()
        id_data = self.id_data
        type_count = {}
        for recClass in self.srcClasses:
            type = recClass.classType
            if type not in modFile.tops: continue
            type_count[type] = 0
            for record in modFile.tops[type].records:
                fid = record.fid
                if fid not in id_data: continue
                for attr,value in id_data[fid].iteritems():
                    if isinstance(record.__getattribute__(attr),
                                  basestring) and isinstance(value,
                                                             basestring):
                        if record.__getattribute__(
                                attr).lower() != value.lower():
                            break
                        continue
                    elif attr == 'model':
                        try:
                            if record.__getattribute__(
                                    attr).modPath.lower() != \
                                    value.modPath.lower():
                                break
                            continue
                        except:
                            break  # assume they are not equal (ie they
                            # aren't __both__ NONE)
                    if record.__getattribute__(attr) != value:
                        break
                else:
                    continue
                for attr,value in id_data[fid].iteritems():
                    record.__setattr__(attr,value)
                keep(fid)
                type_count[type] += 1
        id_data = None
        self._patchLog(log,type_count)

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
            for srcMod in bash.bosh.modInfos.getOrdered(
                    mod_count[type].keys()):
                log(u'  * %s: %d' % (srcMod.s, mod_count[type][srcMod]))
        self.mod_count = {}

class ActorImporter(ImportPatcher):
    """Merges changes to actors."""
    name = _(u'Import Actors')
    text = _(u"Import Actor components from source mods.")
    tip = text
    autoKey = (u'Actors.AIData', u'Actors.Stats', u'Actors.ACBS', u'NPC.Class', u'Actors.CombatStyle', u'Creatures.Blood', u'NPC.Race', u'Actors.Skeleton')

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
            if srcMod not in bash.bosh.modInfos: continue
            srcInfo = bash.bosh.modInfos[srcMod]
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
                if not master in bash.bosh.modInfos: continue # or break filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = bash.bosh.modInfos[master]
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
                    if reduce(getattr,attr.split('.'),record) != value:
                        patchBlock.setRecord(record.getTypeCopy(mapper))
                        break

    def buildPatch(self,log,progress):
        """Merge last version of record with patched graphics data as needed."""
        if not self.isActive: return
        modFile = self.patchFile
        keep = self.patchFile.getKeeper()
        id_data = self.id_data
        type_count = {}
        for recClass in self.srcClasses:
            type = recClass.classType
            if type not in modFile.tops: continue
            type_count[type] = 0
            for record in modFile.tops[type].records:
                fid = record.fid
                if fid not in id_data: continue
                for attr,value in id_data[fid].iteritems():
                    if reduce(getattr,attr.split('.'),record) != value:
                        break
                else:
                    continue
                for attr,value in id_data[fid].iteritems():
                    setattr(reduce(getattr,attr.split('.')[:-1],record),attr.split('.')[-1], value)
                keep(fid)
                type_count[type] += 1
        self._patchLog(log,type_count)

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
            for srcMod in bash.bosh.modInfos.getOrdered(mod_count[type].keys()):
                log(u'  * %s: %d' % (srcMod.s, mod_count[type][srcMod]))
        self.mod_count = {}
