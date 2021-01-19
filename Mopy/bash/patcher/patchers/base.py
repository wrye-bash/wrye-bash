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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This module contains base patcher classes."""
from __future__ import print_function
from collections import Counter, defaultdict
from itertools import chain
# Internal
from .. import getPatchesPath
from ..base import AMultiTweakItem, AMultiTweaker, Patcher, AListPatcher
from ... import load_order, bush
from ...bolt import GPath, CsvReader, deprint
from ...brec import MreRecord
from ...exception import AbstractError

# Patchers 1 ------------------------------------------------------------------
class ListPatcher(AListPatcher,Patcher): pass

class MultiTweakItem(AMultiTweakItem):
    # If True, do not call tweak_scan_file and pool the records this tweak
    # wants together with other tweaks so that we can do one big record copy
    # instead of a bunch of small ones. More elegant and *much* faster, but
    # only works for tweaks that target 'simple' record types (basically
    # anything but CELL, DIAL and WRLD). See the wiki page '[dev] Tweak
    # Pooling' for a detailed overview of its implementation.
    supports_pooling = True

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return self.__class__.tweak_read_classes

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return self.__class__.tweak_read_classes

    def prepare_for_tweaking(self, patch_file):
        """Gives this tweak a chance to use prepare for the phase where it gets
        its tweak_record calls using the specified patch file instance. At this
        point, all relevant files have been scanned, wanted records have been
        forwarded into the BP, MGEFs have been indexed, etc. Default
        implementation does nothing."""

    def finish_tweaking(self, patch_file):
        """Gives this tweak a chance to clean up and do any work after the
        tweak_records phase is over using the specified patch file instance. At
        this point, all tweak_record calls for all tweaks belonging to the
        parent 'tweaker' have been executed. Default implementation does
        nothing."""

    ##: Rare APIs, rework MobCell etc. and drop?
    def tweak_scan_file(self, mod_file, patch_file):
        """Gives this tweak a chance to implement completely custom behavior
        for scanning the specified mod file, with the specified patch file as
        context. *Must* be implemented if this tweak does not support pooling,
        but never gets called if this tweak does support pooling."""
        raise AbstractError(u'tweak_scan_file not implemented')

    def tweak_build_patch(self, log, count, patch_file):
        """Gives this tweak a chance to implement completely custom behavior
        for editing the patch file directly and logging its results. *Must* be
        implemented if this tweak does not support pooling, but never gets
        called if this tweak does support pooling."""
        raise AbstractError(u'tweak_build_patch not implemented')

    @staticmethod
    def _is_nonplayable(record):
        """Returns True if the specified record is marked as nonplayable."""
        ##: yuck, this whole thing is just hacky
        np_flag_attr, np_flag_name = bush.game.not_playable_flag
        return getattr(getattr(record, np_flag_attr), np_flag_name)

class CustomChoiceTweak(MultiTweakItem):
    """Base class for tweaks that have a custom choice with the 'Custom'
    label."""
    custom_choice = _(u'Custom')

class MultiTweaker(AMultiTweaker,Patcher):

    def initData(self,progress):
        # Build up a dict ordering tweaks by the record signatures they're
        # interested in and whether or not they can be pooled
        self._tweak_dict = t_dict = defaultdict(lambda: ([], []))
        for tweak in self.enabled_tweaks: # type: MultiTweakItem
            for read_sig in tweak.getReadClasses():
                t_dict[read_sig][tweak.supports_pooling].append(tweak)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return chain.from_iterable(tweak.getReadClasses()
            for tweak in self.enabled_tweaks) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return chain.from_iterable(tweak.getWriteClasses()
            for tweak in self.enabled_tweaks) if self.isActive else ()

    def scanModFile(self,modFile,progress):
        rec_pool = defaultdict(set)
        common_tops = set(modFile.tops) & set(self._tweak_dict)
        for curr_top in common_tops:
            top_dict = self._tweak_dict[curr_top]
            # Need to give other tweaks a chance to do work first
            for o_tweak in top_dict[False]:
                o_tweak.tweak_scan_file(modFile, self.patchFile)
            # Now we can collect all records that poolable tweaks are
            # interested in
            pool_record = rec_pool[curr_top].add
            poolable_tweaks = top_dict[True]
            if not poolable_tweaks: continue # likely complex type, e.g. CELL
            for record in modFile.tops[curr_top].getActiveRecords():
                for p_tweak in poolable_tweaks: # type: MultiTweakItem
                    if p_tweak.wants_record(record):
                        pool_record(record)
                        break # Exit as soon as a tweak is interested
        # Finally, copy all pooled records in one fell swoop
        for rsig, pooled_records in rec_pool.iteritems():
            if pooled_records: # only copy if we could pool
                getattr(self.patchFile, rsig.decode(u'ascii')).copy_records(
                    pooled_records)

    def buildPatch(self,log,progress):
        """Applies individual tweaks."""
        if not self.isActive: return
        log.setHeader(u'= ' + self._patcher_name, True)
        for tweak in self.enabled_tweaks: # type: MultiTweakItem
            tweak.prepare_for_tweaking(self.patchFile)
        common_tops = set(self.patchFile.tops) & set(self._tweak_dict)
        keep = self.patchFile.getKeeper()
        tweak_counter = defaultdict(Counter)
        for curr_top in common_tops:
            top_dict = self._tweak_dict[curr_top]
            # Need to give other tweaks a chance to do work first
            for o_tweak in top_dict[False]:
                o_tweak.tweak_build_patch(log, tweak_counter[o_tweak],
                                          self.patchFile)
            poolable_tweaks = top_dict[True]
            if not poolable_tweaks: continue  # likely complex type, e.g. CELL
            for record in self.patchFile.tops[curr_top].getActiveRecords():
                for p_tweak in poolable_tweaks:  # type: MultiTweakItem
                    # Check if this tweak can actually change the record - just
                    # relying on the check in scanModFile is *not* enough.
                    # After all, another tweak or patcher could have made a
                    # copy of an entirely unrelated record that *it* was
                    # interested in that just happened to have the same record
                    # type
                    if p_tweak.wants_record(record):
                        # Give the tweak a chance to do its work, and remember
                        # that we now want to keep the record. Note that we
                        # can't break early here, because more than one tweak
                        # may want to touch this record
                        p_tweak.tweak_record(record)
                        keep(record.fid)
                        tweak_counter[p_tweak][record.fid[0]] += 1
        # We're done with all tweaks, give them a chance to clean up and do any
        # finishing touches (e.g. creating records for GMST tweaks), then log
        for tweak in self.enabled_tweaks:
            tweak.finish_tweaking(self.patchFile)
            tweak.tweak_log(log, tweak_counter[tweak])

# Patchers: 10 ----------------------------------------------------------------
class AliasModNamesPatcher(Patcher):
    """Specify mod aliases for patch files."""
    patcher_group = u'General'
    patcher_order = 10

class MergePatchesPatcher(ListPatcher):
    """Merges specified patches into Bashed Patch."""
    patcher_group = u'General'
    patcher_order = 10

    def __init__(self, p_name, p_file, p_sources):
        super(MergePatchesPatcher, self).__init__(p_name, p_file, p_sources)
        if not self.isActive: return
        #--WARNING: Since other patchers may rely on the following update
        # during their __init__, it's important that MergePatchesPatcher runs
        # first - ensured through its group of 'General'
        p_file.set_mergeable_mods(self.srcs)

# TODO move this to a file it's imported after MreRecord.simpleTypes is set
class ReplaceFormIDsPatcher(ListPatcher):
    """Imports Form Id replacers into the Bashed Patch."""
    patcher_group = u'General'
    patcher_order = 15

    def __init__(self, p_name, p_file, p_sources):
        super(ReplaceFormIDsPatcher, self).__init__(p_name, p_file, p_sources)
        self.old_new = {} #--Maps old fid to new fid
        self.old_eid = {} #--Maps old fid to old editor id
        self.new_eid = {} #--Maps new fid to new editor id

    def readFromText(self,textPath):
        """Reads replacement data from specified text file."""
        old_new,old_eid,new_eid = self.old_new,self.old_eid,self.new_eid
        aliases = self.patchFile.pfile_aliases
        with CsvReader(textPath) as ins:
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
        progress.setFull(len(self.srcs))
        for srcFile in self.srcs:
            srcPath = GPath(srcFile)
            try: self.readFromText(getPatchesPath(srcFile))
            except OSError: deprint(
                u'%s is no longer in patches set' % srcPath, traceback=True)
            progress.plus()

    def getReadClasses(self):
        return tuple(MreRecord.simpleTypes | (
            {b'CELL', b'WRLD', b'REFR', b'ACHR', b'ACRE'}))

    def getWriteClasses(self):
        return tuple(MreRecord.simpleTypes | (
            {b'CELL', b'WRLD', b'REFR', b'ACHR', b'ACRE'}))

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        patchCells = self.patchFile.CELL
        patchWorlds = self.patchFile.WRLD
##        for type in MreRecord.simpleTypes:
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
                for record in cellBlock.temp_refs:
                    if record.base in self.old_new:
                        if not cellImported:
                            patchCells.setCell(cellBlock.cell)
                            cellImported = True
                        for newRef in patchCells.id_cellBlock[cellBlock.cell.fid].temp_refs:
                            if newRef.fid == record.fid:
                                loc = patchCells.id_cellBlock[cellBlock.cell.fid].temp_refs.index(newRef)
                                patchCells.id_cellBlock[cellBlock.cell.fid].temp_refs[loc] = record
                                break
                        else:
                            patchCells.id_cellBlock[cellBlock.cell.fid].temp_refs.append(record)
                for record in cellBlock.persistent_refs:
                    if record.base in self.old_new:
                        if not cellImported:
                            patchCells.setCell(cellBlock.cell)
                            cellImported = True
                        for newRef in patchCells.id_cellBlock[cellBlock.cell.fid].persistent_refs:
                            if newRef.fid == record.fid:
                                loc = patchCells.id_cellBlock[cellBlock.cell.fid].persistent_refs.index(newRef)
                                patchCells.id_cellBlock[cellBlock.cell.fid].persistent_refs[loc] = record
                                break
                        else:
                            patchCells.id_cellBlock[cellBlock.cell.fid].persistent_refs.append(record)
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
                    for record in cellBlock.temp_refs:
                        if record.base in self.old_new:
                            if not worldImported:
                                patchWorlds.setWorld(worldBlock.world)
                                worldImported = True
                            if not cellImported:
                                patchWorlds.id_worldBlocks[worldBlock.world.fid].setCell(cellBlock.cell)
                                cellImported = True
                            for newRef in patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].temp_refs:
                                if newRef.fid == record.fid:
                                    loc = patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].temp_refs.index(newRef)
                                    patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].temp_refs[loc] = record
                                    break
                            else:
                                patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].temp_refs.append(record)
                    for record in cellBlock.persistent_refs:
                        if record.base in self.old_new:
                            if not worldImported:
                                patchWorlds.setWorld(worldBlock.world)
                                worldImported = True
                            if not cellImported:
                                patchWorlds.id_worldBlocks[worldBlock.world.fid].setCell(cellBlock.cell)
                                cellImported = True
                            for newRef in patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].persistent_refs:
                                if newRef.fid == record.fid:
                                    loc = patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].persistent_refs.index(newRef)
                                    patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].persistent_refs[loc] = record
                                    break
                            else:
                                patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].persistent_refs.append(record)

    def buildPatch(self,log,progress):
        """Adds merged fids to patchfile."""
        if not self.isActive: return
        old_new,old_eid,new_eid = self.old_new,self.old_eid,self.new_eid
        keep = self.patchFile.getKeeper()
        count = Counter()
        def swapper(oldId):
            newId = old_new.get(oldId,None)
            return newId if newId else oldId
##        for type in MreRecord.simpleTypes:
##            for record in getattr(self.patchFile,type).getActiveRecords():
##                if record.fid in self.old_new:
##                    record.fid = swapper(record.fid)
##                    count.increment(record.fid[0])
####                    record.mapFids(swapper,True)
##                    record.setChanged()
##                    keep(record.fid)
        for cellBlock in self.patchFile.CELL.cellBlocks:
            for record in cellBlock.temp_refs:
                if record.base in self.old_new:
                    record.base = swapper(record.base)
                    count[cellBlock.cell.fid[0]] += 1
##                    record.mapFids(swapper,True)
                    record.setChanged()
                    keep(record.fid)
            for record in cellBlock.persistent_refs:
                if record.base in self.old_new:
                    record.base = swapper(record.base)
                    count[cellBlock.cell.fid[0]] += 1
##                    record.mapFids(swapper,True)
                    record.setChanged()
                    keep(record.fid)
        for worldBlock in self.patchFile.WRLD.worldBlocks:
            keepWorld = False
            for cellBlock in worldBlock.cellBlocks:
                for record in cellBlock.temp_refs:
                    if record.base in self.old_new:
                        record.base = swapper(record.base)
                        count[cellBlock.cell.fid[0]] += 1
##                        record.mapFids(swapper,True)
                        record.setChanged()
                        keep(record.fid)
                        keepWorld = True
                for record in cellBlock.persistent_refs:
                    if record.base in self.old_new:
                        record.base = swapper(record.base)
                        count[cellBlock.cell.fid[0]] += 1
##                        record.mapFids(swapper,True)
                        record.setChanged()
                        keep(record.fid)
                        keepWorld = True
            if keepWorld:
                keep(worldBlock.world.fid)

        log.setHeader(u'= ' + self._patcher_name)
        self._srcMods(log)
        log(u'\n=== '+_(u'Records Patched'))
        for srcMod in load_order.get_ordered(count):
            log(u'* %s: %d' % (srcMod,count[srcMod]))

# Patchers: 20 ----------------------------------------------------------------
class ImportPatcher(ListPatcher):
    """Subclass for patchers in group Importer."""
    patcher_group = u'Importers'
    patcher_order = 20
    # Override in subclasses as needed
    logMsg = u'\n=== ' + _(u'Modified Records')

    def _patchLog(self,log,type_count):
        log.setHeader(u'= %s' % self._patcher_name)
        self._srcMods(log)
        self._plog(log,type_count)

    def _plog(self,log,type_count):
        """Most common logging pattern - override as needed."""
        log(self.__class__.logMsg)
        for type_,count in sorted(type_count.iteritems()):
            if count: log(u'* ' + _(u'Modified %(type)s Records: %(count)d')
                          % {u'type': type_, u'count': count})

    def _plog1(self,log,mod_count): # common logging variation
        log(self.__class__.logMsg % sum(mod_count.values()))
        for mod in load_order.get_ordered(mod_count):
            log(u'* %s: %3d' % (mod, mod_count[mod]))

    def _plog2(self,log,allCounts):
        log(self.__class__.logMsg)
        for top_rec_type, count, counts in allCounts:
            if not count: continue
            typeName = bush.game.record_type_name[top_rec_type]
            log(u'* %s: %d' % (typeName, count))
            for modName in sorted(counts):
                log(u'  * %s: %d' % (modName, counts[modName]))
