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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from .... import bosh
from ....parsers import LoadFactory, ModFile
from ....brec import MreRecord
from ....patcher.patchers.base import AImportPatcher, CBash_ImportPatcher, \
    ImportPatcher

__all__ = ['RoadImporter', 'CBash_RoadImporter']

class _ARoadImporter(AImportPatcher):
    """Imports roads."""
    name = _(u'Import Roads')
    text = _(u"Import roads from source mods.")
    tip = text
    autoKey = {u'Roads'}

class RoadImporter(ImportPatcher, _ARoadImporter):
    logMsg = u'\n=== ' + _(u'Worlds Patched')

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self, patchFile):
        super(RoadImporter, self).initPatchFile(patchFile)
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
    def initPatchFile(self, patchFile):
        """Prepare to handle specified patch mod. All functions are called
        after this."""
        super(CBash_RoadImporter, self).initPatchFile(patchFile)
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
