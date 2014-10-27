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
from bash.bosh import LoadFactory, modInfos, ModFile, CountDict
from bash.brec import MreRecord
from bash.patcher.base import AImportPatcher
from bash.patcher.oblivion.patchers.base import ImportPatcher, \
    CBash_ImportPatcher
from bash.cint import ValidateDict

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
        """Prepare to handle specified patch mod. All functions are called after this."""
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
                    tempCellData[fid][attr] = cellBlock.cell.__getattribute__(attr)
                for flag in flags:
                    tempCellData[fid+('flags',)][flag] = cellBlock.cell.flags.__getattr__(flag)
        def checkMasterCellBlockData(cellBlock):
            if not cellBlock.cell.flags1.ignored:
                fid = cellBlock.cell.fid
                if fid not in tempCellData: return
                if fid not in cellData:
                    cellData[fid] = {}
                    cellData[fid+('flags',)] = {}
                for attr in attrs:
                    if tempCellData[fid][attr] != cellBlock.cell.__getattribute__(attr):
                        cellData[fid][attr] = tempCellData[fid][attr]
                for flag in flags:
                    if tempCellData[fid+('flags',)][flag] != cellBlock.cell.flags.__getattr__(flag):
                        cellData[fid+('flags',)][flag] = tempCellData[fid+('flags',)][flag]
        cellData = self.cellData
        # cellData['Maps'] = {}
        loadFactory = LoadFactory(False,MreRecord.type_class['CELL'],
                                        MreRecord.type_class['WRLD'])
        progress.setFull(len(self.sourceMods))
        cachedMasters = {}
        for srcMod in self.sourceMods:
            if srcMod not in modInfos: continue
            tempCellData = {'Maps':{}}
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            srcFile.convertToLongFids(('CELL','WRLD'))
            masters = srcInfo.header.masters
            bashTags = srcInfo.getBashTags()
            # print bashTags
            try:
                attrs = set(reduce(operator.add, (self.recAttrs[bashKey] for bashKey in bashTags if
                    bashKey in self.recAttrs)))
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
                if not master in modInfos: continue # or break filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = modInfos[master]
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
        if not self.isActive or ('CELL' not in modFile.tops and 'WRLD' not in modFile.tops):
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
                        patchWorlds.id_worldBlocks[worldBlock.world.fid].setCell(
                            cellBlock.cell)
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
            for flag,value in cellData[cellBlock.cell.fid+('flags',)].iteritems():
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
                if cellBlock.cell.fid in cellData and handleCellBlock(cellBlock):
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
        for srcMod in modInfos.getOrdered(count.keys()):
            log(u'* %s: %d' % (srcMod.s,count[srcMod]))

class CBash_CellImporter(ACellImporter,CBash_ImportPatcher):
    autoKey = {u'C.Climate', u'C.Light', u'C.Water', u'C.Owner', u'C.Name',
               u'C.RecordFlags', u'C.Music'}  #,u'C.Maps'
    logMsg = u'* ' + _(u'Cells/Worlds Patched') + u': %d'

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
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
                    mod_count = self.mod_count
                    mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------

