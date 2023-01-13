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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module contains base patcher classes."""

from collections import Counter, defaultdict
from operator import attrgetter

from ..base import APatcher, CsvListPatcher, ListPatcher, MultiTweakItem, \
    ScanPatcher
from ... import load_order
from ...bolt import deprint
from ...brec import RecordType
from ...exception import BPConfigError
from ...mod_files import LoadFactory, ModFile
from ...parsers import FidReplacer

# Patchers 1 ------------------------------------------------------------------
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
        for fn_plugin, pl_info in patch_file.merged_or_loaded_ord.items(): ##: all_plugins?
            index_plugin = self._mod_file_read(pl_info)
            for index_sig in self._index_sigs:
                self._indexed_records[index_sig].update(
                    index_plugin.tops[index_sig].iter_present_records())
        super(IndexingTweak, self).prepare_for_tweaking(patch_file)

class CustomChoiceTweak(MultiTweakItem):
    """Base class for tweaks that have a custom choice with the 'Custom'
    label."""
    custom_choice = _(u'Custom')

class MultiTweaker(ScanPatcher):
    """Combines a number of sub-tweaks which can be individually enabled and
    configured through a choice menu."""
    patcher_group = 'Tweakers'
    patcher_order = 30
    _tweak_classes = set() # override in implementations

    def __init__(self, p_name, p_file, enabled_tweaks: list[MultiTweakItem]):
        super().__init__(p_name, p_file)
        for e_tweak in enabled_tweaks:
            if e_tweak.custom_choice:
                e_values = tuple(e_tweak.choiceValues[e_tweak.chosen])
                validation_err = e_tweak.validate_values(e_values)
                # We've somehow ended up with a custom value that is not
                # accepted by the tweak itself, this will almost certainly fail
                # at runtime so abort the BP process now with a more
                # informative error message
                if validation_err is not None:
                    err_header = e_tweak.validation_error_header(e_values)
                    raise BPConfigError(err_header + '\n\n' + validation_err)
        self.enabled_tweaks: list[MultiTweakItem] = enabled_tweaks
        self.isActive = bool(enabled_tweaks)
        # Build up a dict mapping record signatures to the tweaks who need them
        tweak_dict = defaultdict(list)
        for tweak in self.enabled_tweaks:
            for read_sig in tweak.tweak_read_classes:
                tweak_dict[read_sig].append(tweak)
        self._tweak_dict: dict[bytes, list[MultiTweakItem]] = dict(tweak_dict)

    @classmethod
    def tweak_instances(cls):
        # Sort alphabetically first for aesthetic reasons
        tweak_classes = sorted(cls._tweak_classes, key=lambda c: c.tweak_name)
        # After that, sort to make tweaks instantiate & run in the right order
        tweak_classes.sort(key=lambda c: c.tweak_order)
        return [t() for t in tweak_classes]

    @property
    def _read_sigs(self):
        return set(self._tweak_dict)

    def scanModFile(self, modFile, progress, scan_sigs=None):
        """We need to iterate only through the master records for complex
        groups."""
        for top_sig, block in modFile.iter_tops(scan_sigs or self._read_sigs):
            patchBlock = self.patchFile.tops[top_sig]
            for rid, rec in block.iter_present_records(top_sig): # this
                for p_tweak in self._tweak_dict[top_sig]:
                    if p_tweak.wants_record(rec):
                        patchBlock.setRecord(rec)
                        break # Exit as soon as a tweak is interested

    def buildPatch(self,log,progress):
        """Applies individual tweaks."""
        if not self.isActive: return
        log.setHeader(u'= ' + self._patcher_name, True)
        for tweak in self.enabled_tweaks:
            tweak.prepare_for_tweaking(self.patchFile)
        keep = self.patchFile.getKeeper()
        tweak_counter = defaultdict(Counter)
        for curr_top, block in self.patchFile.iter_tops(self._tweak_dict):
            for rid, record in block.iter_present_records(curr_top):
                for p_tweak in self._tweak_dict[curr_top]:
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
                        keep(rid, record)
                        tweak_counter[p_tweak][rid.mod_fn] += 1
        # We're done with all tweaks, give them a chance to clean up and do any
        # finishing touches (e.g. creating records for GMST tweaks), then log
        for tweak in self.enabled_tweaks:
            tweak.finish_tweaking(self.patchFile)
            tweak.tweak_log(log, tweak_counter[tweak])

# Patchers: 10 ----------------------------------------------------------------
class AliasModNamesPatcher(APatcher):
    """Specify mod aliases for patch files."""
    patcher_group = u'General'
    patcher_order = 10

class MergePatchesPatcher(ListPatcher):
    """Merges specified patches into Bashed Patch."""
    patcher_group = u'General'
    patcher_order = 10
    _missing_master_error = '\n\n'.join([_(
        '%(merged_plugin)s is supposed to be merged into the Bashed Patch, '
        'but some of its masters %(missing_master)s are missing.'),
        _('Please install the missing master(s) to fix this.')])
    _inactive_master_error = '\n\n'.join([_(
        '%(merged_plugin)s is supposed to be merged into the Bashed Patch, '
        'but some of its masters %(inactive_master)s are inactive.'),
        _('Please activate the inactive master(s) to fix this.')])

    def _process_sources(self, p_sources, p_file):
        # First, perform an error check for missing/inactive masters
        for merge_src in p_sources:
            if ((mm := p_file.active_mm.get(merge_src)) or  # should not happen
                    (mm := p_file.inactive_mm.get(merge_src))):
                raise BPConfigError(self._missing_master_error % {
                    'merged_plugin': merge_src, 'missing_master': mm})
            elif mm := p_file.inactive_inm.get(merge_src):
                # It's present but inactive - that won't work for merging
                raise BPConfigError(self._inactive_master_error % {
                    'merged_plugin': merge_src, 'inactive_master': mm})
        self.srcs = p_sources
        #--WARNING: Since other patchers may rely on the following update
        # during their __init__, it's important that MergePatchesPatcher runs
        # first - ensured through its group of 'General'
        p_file.set_mergeable_mods(p_sources)
        return bool(p_sources)

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
##            for record in modFile.tops[top_grup_sig].iter_present_records():
##                record = record.getTypeCopy(mapper)
##                if record.fid in self.old_new:
##                    self.patchFile.tops[top_grup_sig].setRecord(record)
        if b'CELL' in modFile.tops:
            for cfid, cblock in modFile.tops[b'CELL'].iter_present_records():
                if patch_cell := cfid in patchCells.id_records:
                    patch_cell = patchCells.setRecord(cblock.master_record,
                                                      do_copy=False)
                for get_refs in __get_refs:
                    for __, rec in get_refs(cblock).iter_present_records():
                        if getattr(rec, 'base', None) in self.old_new:
                            if not patch_cell:
                                patch_cell = patchCells.setRecord(
                                    cblock.master_record)
                            get_refs(patch_cell).setRecord(rec, do_copy=False)
        if b'WRLD' in modFile.tops:
            for wfid, worldBlock in modFile.tops[b'WRLD'].iter_present_records():
                if patch_wrld := (wfid in patchWorlds.id_records):
                    patch_wrld = patchWorlds.setRecord(
                        worldBlock.master_record, do_copy=False)
                for wcfid, cblock in worldBlock.ext_cells.iter_present_records():
                    if patch_cell := (patch_wrld and wcfid in
                            patch_wrld.ext_cells.id_records):
                        patch_cell = patch_wrld.ext_cells.setRecord(
                            cblock.master_record, do_copy=False)
                    for get_refs in __get_refs:
                        for __, rec in get_refs(cblock).iter_present_records():
                            if getattr(rec, 'base', None) in self.old_new:
                                if not patch_wrld:
                                    patch_wrld = patchWorlds.setRecord(
                                        worldBlock.master_record)
                                if not patch_cell:
                                    patch_cell = patch_wrld.ext_cells.setRecord(
                                        cblock.master_record)
                                get_refs(patch_cell).setRecord(rec,
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
##            for rid, record in self.patchFile.tops[type].iter_present_records():
##                if rid in self.old_new:
##                    record.fid = old_new.get(record.fid, record.fid)
##                    count.increment(record.fid[0])
####                    record.mapFids(swapper,True)
##                    keep(record.fid, record)
        for cfid, cellBlock in self.patchFile.tops[b'CELL'].id_records.items():
            for get_refs in __get_refs:
                for rid, record in get_refs(cellBlock).id_records.items():
                    if getattr(record, 'base', None) in self.old_new:
                        record.base = swapper(record.base)
                        count[cfid.mod_fn] += 1
                        ## record.mapFids(swapper,True)
                        keep(rid, record)
        for worldId, worldBlock in self.patchFile.tops[
            b'WRLD'].id_records.items():
            if worldBlock.should_skip():
                deprint(f'Block {worldBlock!r} should have been skipped')
                continue
            keepWorld = False
            for cfid, cellBlock in worldBlock.ext_cells.id_records.items():
                for get_refs in __get_refs:
                    for rid, record in get_refs(cellBlock).id_records.items():
                        if getattr(record, 'base', None) in self.old_new:
                            record.base = swapper(record.base)
                            count[cfid.mod_fn] += 1
                            ## record.mapFids(swapper,True)
                            keepWorld |= keep(rid, record)
            if keepWorld:
                keep(worldId, worldBlock)
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
