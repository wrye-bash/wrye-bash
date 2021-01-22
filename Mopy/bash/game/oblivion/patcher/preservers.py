# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, either version 3
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <https://www.gnu.org/licenses/>.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from .special import _ExSpecial ##: ugh
from ....mod_files import ModFile, LoadFactory
from ....patcher.patchers.base import ImportPatcher

__all__ = [u'ImportRoadsPatcher']

class ImportRoadsPatcher(ImportPatcher, _ExSpecial):
    """Imports roads."""
    patcher_name = _(u'Import Roads')
    patcher_desc = _(u"Import roads from source mods.")
    autoKey = {u'Roads'}
    _config_key = u'RoadImporter'

    logMsg = u'\n=== ' + _(u'Worlds Patched')
    _read_sigs = (b'CELL', b'WRLD', b'ROAD')

    def __init__(self, p_name, p_file, p_sources):
        super(ImportRoadsPatcher, self).__init__(p_name, p_file, p_sources)
        self.world_road = {}

    def initData(self,progress):
        """Get cells from source files."""
        if not self.isActive: return
        loadFactory = LoadFactory(False, by_sig=self._read_sigs)
        for srcMod in self.srcs:
            if srcMod not in self.patchFile.p_file_minfos: continue
            srcInfo = self.patchFile.p_file_minfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            for worldBlock in srcFile.tops[b'WRLD'].worldBlocks:
                if worldBlock.road:
                    worldId = worldBlock.world.fid
                    road = worldBlock.road.getTypeCopy()
                    self.world_road[worldId] = road
        self.isActive = bool(self.world_road)

    def scanModFile(self, modFile, progress): # scanModFile3 ?
        """Add lists from modFile."""
        if not self.isActive or b'WRLD' not in modFile.tops: return
        patchWorlds = self.patchFile.tops[b'WRLD']
        for worldBlock in modFile.tops[b'WRLD'].worldBlocks:
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
        for worldBlock in self.patchFile.tops[b'WRLD'].worldBlocks:
            worldId = worldBlock.world.fid
            curRoad = worldBlock.road
            newRoad = self.world_road.get(worldId)
            if newRoad and (not curRoad or curRoad.points_p != newRoad.points_p
                or curRoad.connections_p != newRoad.connections_p
                ):
                worldBlock.road = newRoad
                keep(worldId)
                keep(newRoad.fid)
                worldsPatched.add((worldId[0], worldBlock.world.eid))
        self.world_road.clear()
        self._patchLog(log,worldsPatched)

    def _plog(self,log,worldsPatched):
        log(self.__class__.logMsg)
        for modWorld in sorted(worldsPatched):
            log(u'* %s: %s' % modWorld)

    @classmethod
    def gui_cls_vars(cls):
        cls_vars = super(ImportRoadsPatcher, cls).gui_cls_vars()
        return cls_vars.update({u'autoKey': cls.autoKey}) or cls_vars
