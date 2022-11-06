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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module contains base patcher classes."""

from collections import Counter, defaultdict
from itertools import chain
from operator import attrgetter

# Internal
from ..base import AMultiTweakItem, AMultiTweaker, Patcher, ListPatcher, \
    CsvListPatcher
from ... import load_order, bush
from ...bolt import deprint
from ...brec import RecordType
from ...exception import BPConfigError
from ...mod_files import LoadFactory, ModFile
from ...parsers import FidReplacer

# Patchers 1 ------------------------------------------------------------------
class MultiTweakItem(AMultiTweakItem):

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

    @staticmethod
    def _is_nonplayable(record):
        """Returns True if the specified record is marked as nonplayable."""
        ##: yuck, this whole thing is just hacky
        np_flag_attr, np_flag_name = bush.game.not_playable_flag
        return getattr(getattr(record, np_flag_attr), np_flag_name)

# HACK - and what an ugly one - we need a general API to express to the BP that
# a patcher/tweak wants it to index all records for certain record types in
# some central place (and NOT by forwarding all records into the BP!)
class IndexingTweak(MultiTweakItem):
    _index_sigs: list[bytes]

    def __init__(self):
        super(IndexingTweak, self).__init__()
        self.loadFactory = LoadFactory(keepAll=False, by_sig=self._index_sigs)
        self._indexed_records = defaultdict(dict)

    def _mod_file_read(self, modInfo):
        modFile = ModFile(modInfo, self.loadFactory)
        modFile.load_plugin()
        return modFile

    def prepare_for_tweaking(self, patch_file):
        pf_minfs = patch_file.p_file_minfos
        for fn_plugin in patch_file.merged_or_loaded_ord: ##: all_plugins?
            index_plugin = self._mod_file_read(pf_minfs[fn_plugin])
            for index_sig in self._index_sigs:
                self._indexed_records[index_sig].update(
                    index_plugin.tops[index_sig].getActiveRecords())
        super(IndexingTweak, self).prepare_for_tweaking(patch_file)

class CustomChoiceTweak(MultiTweakItem):
    """Base class for tweaks that have a custom choice with the 'Custom'
    label."""
    custom_choice = _(u'Custom')

class MultiTweaker(AMultiTweaker,Patcher):
    _tweak_dict: defaultdict[bytes, list[AMultiTweakItem]]

    def initData(self,progress):
        # Build up a dict mapping tweaks to the record signatures they're
        # interested in
        self._tweak_dict = defaultdict(list)
        for tweak in self.enabled_tweaks:
            for read_sig in tweak.tweak_read_classes:
                self._tweak_dict[read_sig].append(tweak)

    @property
    def _read_sigs(self):
        return set(chain.from_iterable(
            tweak.tweak_read_classes for tweak in self.enabled_tweaks))

    def scanModFile(self,modFile,progress):
        rec_pool = defaultdict(set)
        common_tops = set(modFile.tops) & set(self._tweak_dict)
        for curr_top in common_tops:
            # Collect all records that poolable tweaks are interested in
            poolable_tweaks = self._tweak_dict[curr_top]
            if not poolable_tweaks: continue
            pool_record = rec_pool[curr_top].add
            for _rid, record in modFile.tops[curr_top].iter_present_records(
                    curr_top):
                for p_tweak in poolable_tweaks:
                    if p_tweak.wants_record(record):
                        pool_record(record)
                        break # Exit as soon as a tweak is interested
        # Finally, copy all pooled records in one fell swoop
        for top_grup_sig, pooled_records in rec_pool.items():
            for record in pooled_records:
                self.patchFile.tops[top_grup_sig].setRecord(record)

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
            poolable_tweaks = self._tweak_dict[curr_top]
            if not poolable_tweaks: continue
            for rid, record in self.patchFile.tops[curr_top
                    ].iter_present_records(curr_top):
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
                        try:
                            p_tweak.tweak_record(record)
                        except:
                            deprint(record.error_string('tweaking'),
                                    traceback=True)
                            continue
                        keep(rid)
                        tweak_counter[p_tweak][rid.mod_fn] += 1
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
    _missing_master_error = _(
        '%(merged_plugin)s is supposed to be merged into the Bashed Patch, '
        'but at least one of its masters (%(missing_master)s) is '
        'missing.') + '\n\n' + _(
        'Please install %(missing_master)s to fix this.')
    _inactive_master_error = _(
        '%(merged_plugin)s is supposed to be merged into the Bashed Patch, '
        'but at least one of its masters (%(inactive_master)s) is '
        'inactive.') + '\n\n' + _(
        'Please activate %(inactive_master)s to fix this.')

    def __init__(self, p_name, p_file, p_sources):
        super(MergePatchesPatcher, self).__init__(p_name, p_file, p_sources)
        if not self.isActive: return
        pf_minfs = self.patchFile.p_file_minfos
        # First, perform an error check for missing/inactive masters
        for merge_src in self.srcs:
            merge_minf = pf_minfs[merge_src]
            for merge_master in merge_minf.masterNames:
                if merge_master not in pf_minfs:
                    # Filter plugins may legitimately be missing masters
                    if 'Filter' not in merge_minf.getBashTags():
                        raise BPConfigError(self._missing_master_error % {
                            'merged_plugin': merge_src,
                            'missing_master': merge_master,
                        })
                elif not load_order.cached_is_active(merge_master):
                    # It's present but inactive - that won't work for merging
                    raise BPConfigError(self._inactive_master_error % {
                        'merged_plugin': merge_src,
                        'inactive_master': merge_master,
                    })
        #--WARNING: Since other patchers may rely on the following update
        # during their __init__, it's important that MergePatchesPatcher runs
        # first - ensured through its group of 'General'
        p_file.set_mergeable_mods(self.srcs)

class ReplaceFormIDsPatcher(FidReplacer, CsvListPatcher):
    """Imports Form Id replacers into the Bashed Patch."""
    patcher_group = u'General'
    patcher_order = 15
    _read_sigs = RecordType.simpleTypes | { # this better be initialized
        b'CELL', b'WRLD', b'REFR', b'ACHR', b'ACRE'}

    def __init__(self, p_name, p_file, p_sources):
        super(ReplaceFormIDsPatcher, self).__init__(p_file.pfile_aliases)
        # we need to override self._parser_sigs from FidReplacer.__init__
        self._parser_sigs = self._read_sigs
        ListPatcher.__init__(self, p_name, p_file, p_sources)

    def _parse_line(self, csv_fields):
        oldId = self._coerce_fid(csv_fields[1], csv_fields[2]) # oldMod, oldObj
        newId = self._coerce_fid(csv_fields[5], csv_fields[6]) # newMod, newObj
        self.old_new[oldId] = newId

    def scanModFile(self, modFile, progress, *, __get_refs=(
            attrgetter('temp_refs'), attrgetter('persistent_refs'))):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        patchCells = self.patchFile.tops[b'CELL']
        patchWorlds = self.patchFile.tops[b'WRLD']
##        for top_grup_sig in MreRecord.simpleTypes:
##            for record in modFile.tops[top_grup_sig].getActiveRecords():
##                record = record.getTypeCopy(mapper)
##                if record.fid in self.old_new:
##                    self.patchFile.tops[top_grup_sig].setRecord(record)
        if b'CELL' in modFile.tops:
            for cfid, cellBlock in modFile.tops[b'CELL'].id_records.items():
                if patch_cell := cfid in patchCells.id_records:
                    patch_cell = patchCells.setRecord(cellBlock.master_record,
                                                      do_copy=False)
                for get_refs in __get_refs:
                    for record in get_refs(cellBlock).iter_records():
                        if getattr(record, 'base', None) in self.old_new:
                            if not patch_cell:
                                patch_cell = patchCells.setRecord(
                                    cellBlock.master_record)
                            get_refs(patch_cell).setRecord(record,
                                                           do_copy=False)
        if b'WRLD' in modFile.tops:
            for wfid, worldBlock in modFile.tops[b'WRLD'].id_records.items():
                if patch_wrld := (wfid in patchWorlds.id_records):
                    patch_wrld = patchWorlds.setRecord(
                        worldBlock.master_record, do_copy=False)
                for wcfid, cellBlock in worldBlock.ext_cells.id_records.items():
                    if patch_cell := (patch_wrld and wcfid in
                            patch_wrld.ext_cells.id_records):
                        patch_cell = patch_wrld.ext_cells.setRecord(
                            cellBlock.master_record, do_copy=False)
                    for get_refs in __get_refs:
                        for record in get_refs(cellBlock).iter_records():
                            if getattr(record, 'base', None) in self.old_new:
                                if not patch_wrld:
                                    patch_wrld = patchWorlds.setRecord(
                                        worldBlock.master_record)
                                if not patch_cell:
                                    patch_cell = patch_wrld.ext_cells.setRecord(
                                        cellBlock.master_record)
                                get_refs(patch_cell).setRecord(record,
                                                               do_copy=False)

    def buildPatch(self, log, progress, *, __get_refs=(attrgetter('temp_refs'),
                   attrgetter('persistent_refs'))):
        """Adds merged fids to patchfile."""
        if not self.isActive: return
        old_new = self.old_new
        keep = self.patchFile.getKeeper()
        count = Counter()
        def swapper(oldId):
            return old_new.get(oldId, oldId)
##        for type in MreRecord.simpleTypes:
##            for record in self.patchFile.tops[type].getActiveRecords():
##                if record.fid in self.old_new:
##                    record.fid = old_new.get(record.fid, record.fid)
##                    count.increment(record.fid[0])
####                    record.mapFids(swapper,True)
##                    record.setChanged()
##                    keep(record.fid)
        for cfid, cellBlock in self.patchFile.tops[b'CELL'].id_records.items():
            for get_refs in __get_refs:
                for rid, record in get_refs(cellBlock).id_records.items():
                    if getattr(record, 'base', None) in self.old_new:
                        record.base = swapper(record.base)
                        count[cfid.mod_fn] += 1
                        ## record.mapFids(swapper,True)
                        record.setChanged()
                        keep(rid)
        for worldId, worldBlock in self.patchFile.tops[
            b'WRLD'].id_records.items():
            keepWorld = False
            for cfid, cellBlock in worldBlock.ext_cells.id_records.items():
                for get_refs in __get_refs:
                    for rid, record in get_refs(cellBlock).id_records.items():
                        if getattr(record, 'base', None) in self.old_new:
                            record.base = swapper(record.base)
                            count[cfid.mod_fn] += 1
                            ## record.mapFids(swapper,True)
                            record.setChanged()
                            keep(rid)
                            keepWorld = True
            if keepWorld:
                keep(worldId)
        log.setHeader(f'= {self._patcher_name}')
        self._srcMods(log)
        log('\n=== ' + _('Records Patched'))
        for srcMod in load_order.get_ordered(count):
            log(f'* {srcMod}: {count[srcMod]:d}')

#------------------------------------------------------------------------------
def is_templated(record, flag_name):
    """Checks if the specified record has a template record and the
    appropriate template flag set."""
    return (getattr(record, u'template', None) is not None and
            getattr(record.templateFlags, flag_name))
