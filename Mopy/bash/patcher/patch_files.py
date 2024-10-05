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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from __future__ import annotations

import re
import time
from collections import Counter, defaultdict, deque
from itertools import chain, count
from operator import attrgetter
from typing import Self

from .. import bass, load_order
from .. import bolt # for type hints
from .. import bush # for game etc
from ..bolt import Progress, SubProgress, deprint, dict_sort, readme_url, FName
from ..exception import BoltError, CancelError, ModError
from ..plugin_types import MergeabilityCheck
from ..localize import format_date
from ..mod_files import LoadFactory, ModFile

class PatchFile(ModFile):
    """Base class of patch files. Wraps an executing bashed Patch."""

    def set_mergeable_mods(self, mergeMods):
        """Set 'mergeSet' attribute to the srcs of MergePatchesPatcher."""
        self.mergeSet = merge_set = set(mergeMods)
        self.merged_or_loaded = merged_active = {*merge_set, *self.load_dict}
        self.merged_or_loaded_ord = {m: self.p_file_minfos[m] for m in
                                     load_order.get_ordered(merged_active)}
        self.ii_mode = {m for m in merge_set if 'IIM' in self.all_tags[m]}

    def _log_header(self, log, patch_name):
        log.setHeader(f'= {patch_name} {"=" * 30}#', True)
        log('{{CONTENTS=1}}')
        #--Load Mods and error mods
        log.setHeader('= ' + _('Overview'), True)
        log.setHeader('=== ' + _('Date/Time'))
        log('* ' + format_date(time.time()))
        log('* ' + _('Elapsed Time: %(elapsed_time)s') % {
            'elapsed_time': 'TIMEPLACEHOLDER'})
        def _link(link_id):
            return (readme_url(mopy=bass.dirs['mopy'], advanced=True) +
                    f'#{link_id}')
        if self.patcher_mod_skipcount:
            log.setHeader('=== ' + _('Skipped Imports'))
            log(_('The following import patchers skipped records because the '
                  'imported record required a missing or inactive plugin to '
                  'work properly. If this was not intentional, rebuild the '
                  'patch after either deactivating the imported plugins '
                  'listed below or activating the missing plugins.'))
            for patcher, mod_skipcount in self.patcher_mod_skipcount.items():
                log('* ' + _('%(patcher_n)s skipped %(num_skip)d records:') % {
                    'patcher_n': patcher,
                    'num_skip': sum(mod_skipcount.values())})
                for mod, skipcount in mod_skipcount.items():
                    log('  * ' + _('The imported plugin, %(imp_plugin)s, '
                                   'skipped %(num_recs)d records.') % {
                        'imp_plugin': mod, 'num_recs': skipcount})
        if self.needs_filter_mods:
            log.setHeader('===' + _('Plugins Needing Filter Tag'))
            log(_("The following plugins are missing masters and have tags "
                  "that indicate that you want to import data from them into "
                  "the Bashed Patch. However, since they have missing masters "
                  "and do not have a Filter tag they have been skipped. "
                  "Consider adding a Filter tag to them or installing the "
                  "required masters. See the '%(filtering_link)s' section of "
                  "the readme for more information.") % {
                'filtering_link': f"[[{_link('patch-filter')}"
                                  f"|{_('Filtering')}]]"})
            for mod in self.needs_filter_mods: log(f'* {mod}')
        if self.loadErrorMods:
            log.setHeader('=== ' + _('Load Error Plugins'))
            log(_('The following plugins had load errors and were skipped '
                  'while building the patch. Most likely this problem is due '
                  'to a badly formatted plugin. For more info, generate a '
                  '%(bashbugdump_link)s.') % {
                'bashbugdump_link': f"[[https://github.com/wrye-bash"
                                    f"/wrye-bash/wiki/%5Bgithub%5D-Reporting-a"
                                    f"-bug#the-bashbugdumplog|BashBugDump]]"})
            for (mod, e) in self.loadErrorMods: log(f'* {mod}: {e}')
        if self.worldOrphanMods:
            log.setHeader('=== ' + _('World Orphans'))
            log(_("The following plugins had orphaned world groups, which "
                  "were skipped. This is not a major problem, but you might "
                  "want to use Wrye Bash's '%(link_rwo)s' command to repair "
                  "the plugins.") % {
                'link_rwo': f"[[{_link('modsRemoveWorldOrphans')}"
                            f"|{_('Remove World Orphans')}]]"})
            for mod in self.worldOrphanMods: log(f'* {mod}')
        if self.compiledAllMods:
            log.setHeader('=== ' + _('Compiled All'))
            log(_("The following plugins have an empty compiled version of "
                  "genericLoreScript. This is usually a sign that the plugin "
                  "author did a %(compile_all)s while editing scripts. "
                  "This may interfere with the behavior of other plugins that "
                  "intentionally modify scripts from %(game_name)s (e.g. Cobl "
                  "and Unofficial Oblivion Patch). You can use Wrye Bash's "
                  "'%(link_decomp_all)s' command to repair the plugins.") % {
                'compile_all': f'__{_("Compile All")}__',
                'game_name': bush.game.master_file,
                'link_decomp_all': f"[[{_link('modsDecompileAll')}"
                                   f"|{_('Decompile All')}]]"})
            for mod in self.compiledAllMods: log(f'* {mod}')
        log.setHeader('=== ' + _('Active Plugins'), True)
        for mname, modinfo in self.merged_or_loaded_ord.items():
            version = modinfo.get_version()
            try:
                message = f'* {self.load_dict[mname]:02X} '
            except KeyError:
                message = '* ++ '
            if version:
                message += _('%(msg_plugin)s [Version %(plugin_ver)s]') % {
                    'msg_plugin': mname, 'plugin_ver': version}
            else:
                message += mname
            log(message)
        #--Load Mods and error mods
        if self.pfile_aliases:
            log.setHeader('= ' + _('Plugin Aliases'))
            for alias_target, alias_repl in dict_sort(self.pfile_aliases):
                log(f'* {alias_target} >> {alias_repl}')

    def init_patchers_data(self, patcher_instances, progress):
        """Gives each patcher a chance to get its source data."""
        self._patcher_instances = [p for p in patcher_instances if p.isActive]
        if not self._patcher_instances: return
        progress = progress.setFull(len(self._patcher_instances))
        for index, patcher in enumerate(self._patcher_instances):
            progress(index, _('Preparing') + f'\n{patcher.getName()}')
            patcher.initData(SubProgress(progress, index))
        progress(progress.full, _('Patchers prepared.'))
        # initData may set isActive to zero - TODO(ut) track down
        self._patcher_instances = [p for p in patcher_instances if p.isActive]

    #--Instance
    def __init__(self, modInfo, pfile_minfos):
        """Initialization."""
        ModFile.__init__(self,modInfo,None)
        self.tes4.author = 'BASHED PATCH'
        self.tes4.masters = [bush.game.master_file]
        # Start records at 0x800 to avoid problems where people use older
        # versions of games that don't support the expanded ESL range. BPs
        # generally end up with very few new records, so we're very
        # unlikely to end up exceeding the 2048 barrier where the BP would
        # take a full slot again, even with this.
        self.tes4.nextObject = 0x800
        self.keepIds = set()
        # Aliases from one mod name to another. Used by text file patchers.
        self.pfile_aliases = {}
        self.mergeIds = set()
        # Information arrays
        self.loadErrorMods = []
        self.worldOrphanMods = []
        self.compiledAllMods = []
        self.patcher_mod_skipcount = defaultdict(Counter)
        #--Mods
        # Load order is not supposed to change during patch execution
        self.all_plugins = load_order.cached_lower_loading(modInfo.fn_key)
        # exclude modding esms (those tend to be huge)
        self.all_plugins = {k: pfile_minfos[k] for k in self.all_plugins if
                            k not in bush.game.modding_esm_size}
        # cache the tags
        self.all_tags = {k: v.getBashTags() for k, v in
                         self.all_plugins.items()}
        # list the patchers folders to get potential Bash Patches csv
        # sources and cache the result for this patch  execution session
        self.patches_set = set(bass.dirs['patches'].ilist())
        if bass.dirs['defaultPatches']:
            self.patches_set.update(bass.dirs['defaultPatches'].ilist())
        self.p_file_minfos = pfile_minfos
        self.set_active_arrays(pfile_minfos)
        # cache of mods loaded - eventually share between initData/scanModFile
        self._loaded_mods = {}
        # read signatures we need to load per plugin - updated by the patchers
        self._read_signatures = defaultdict(set)

    def set_active_arrays(self, pfile_minfos):
        """Populate PatchFile data structures with info on active mods - must
        be rerun when active plugins change"""
        c = count()
        active_mods = {m: next(c) for m in self.all_plugins if
                       load_order.cached_is_active(m)}
        # TODO: display those
        loaded_modding_esms = [m for m in load_order.cached_active_tuple() if
                               m in bush.game.modding_esm_size]
        if not active_mods:
            raise BoltError('No active plugins loading before the Bashed '
                            'Patch')
        self.load_dict = active_mods # used in printing BP masters' indexes
        self.set_mergeable_mods([]) # reset - depends on load_dict
        # Populate mod arrays for the rest of the patch stages ----------------
        self.needs_filter_mods = {}
        self.bp_mergeable = set() # plugins we can show as sources for the merge patcher
        # inactive plugins with missing or delinquent masters - that may be ok
        self.inactive_mm = defaultdict(list)
        # inactive plugins with inactive masters (unless the inactive masters
        # are mergeable!) - not ok but not for merged
        self.inactive_inm = defaultdict(list)
        previousMods = set()
        # GUI - fatal errors
        # active mods with missing/inactive masters
        self.active_mm = defaultdict(list)
        # active mods whose masters load after them
        self.delinquent = defaultdict(list)
        # Set of all Bash Tags that don't trigger an import from some patcher
        non_import_bts = {'Deactivate', 'Filter', 'IIM',
                          'MustBeActiveIfImported', 'NoMerge'}
        mi_mergeable = [modinfo.fn_key for modinfo in
                        MergeabilityCheck.MERGE.cached_types(pfile_minfos)[0]]
        for index, (modName, modInfo) in enumerate(self.all_plugins.items()):
            # Check some commonly needed properties of the current plugin
            bashTags = self.all_tags[modName]
            is_loaded = modName in active_mods
            for master in modInfo.masterNames:
                if master not in active_mods:
                    if is_loaded:
                        self.active_mm[modName].append(master)
                    elif master not in self.all_plugins: # might be delinquent
                        self.inactive_mm[modName].append(master)
                    elif master not in mi_mergeable:
                        self.inactive_inm[modName].append(master)
                elif master not in previousMods:
                    if is_loaded: self.delinquent[modName].append(master)
            previousMods.add(modName)
            if modName in self.active_mm or modName in self.delinquent:
                continue
            can_filter = 'Filter' in bashTags
            if modName in list(self.inactive_mm):
                if not can_filter:
                    if bashTags - non_import_bts:
                        # This plugin has missing masters, is not Filter-tagged but
                        # still wants to import data -> user needs to add Filter tag
                        self.needs_filter_mods[modName] = self.inactive_mm[modName]
                    continue
                else:
                    # is filtered tagged, we will filter some masters and
                    # then recheck in merge_record - drop from inactive_mm
                    del self.inactive_mm[modName]
            if (modName in mi_mergeable and modName not in
                    self.inactive_inm and 'NoMerge' not in bashTags):
                self.bp_mergeable.add(modName)

    def getKeeper(self):
        """Returns a function to add fids to self.keepIds."""
        def _patch_keeper(rec_formid, rec):
            """Keep rec_formid if rec is not ignored/deleted - setChanged on
            rec."""
            if rec.should_skip():
                deprint(f'Record {rec!r} should have been skipped')
                return 0
            self.keepIds.add(rec_formid)
            rec.setChanged() # this here may be a _ComplexRec
            return 1
        return _patch_keeper

    def create_record(self, new_rec_sig, new_rec_fid=None, head_flags=0):
        """In addition to super add the fid of the new record to this patch."""
        new_rec = super().create_record(new_rec_sig, new_rec_fid)
        self.keepIds.add(new_rec.fid)
        return new_rec

    def new_gmst(self, gmst_eid, gmst_val):
        """Creates a new GMST record with the specified EDID and value and adds
        it to this patch."""
        gmst_rec = self.create_record(b'GMST')
        gmst_rec.eid = gmst_eid
        gmst_rec.value = gmst_val

    def initFactories(self,progress):
        """Gets load factories."""
        progress(0, _('Processing.'))
        read_sigs = set(bush.game.readClasses) | set(chain.from_iterable(
            p.active_read_sigs for p in self._patcher_instances))
        self.readFactory = LoadFactory(False, by_sig=read_sigs)
        write_sigs = set(bush.game.writeClasses) | set(chain.from_iterable(
            p.active_write_sigs for p in self._patcher_instances))
        self.loadFactory = LoadFactory(True, by_sig=write_sigs)
        #--Merge Factory
        self.mergeFactory = LoadFactory(False, by_sig=bush.game.mergeable_sigs)

    def update_read_factories(self, sigs, mods):
        """Let the patchers request loading the specified `sigs` for the
        specified `mods` to use in its initData (eventually scanModFile)."""
        for m in mods: self._read_signatures[m].update(sigs)

    def get_loaded_mod(self, mod_name):
        # get which signatures the patchers need to load for this mod
        load_sigs = self._read_signatures.get(mod_name) or set()
        if mod_name in self._loaded_mods:
            loaded_mod: ModFile = self._loaded_mods[mod_name]
            if loaded_mod.topsSkipped & load_sigs: # we need to reload
                # never happens for initData but see mergeModFile
                del self._loaded_mods[mod_name]
            else:
                return loaded_mod
        elif mod_name not in self.all_plugins:
            return None # (Filter tagged) mods with missing masters
        lf = LoadFactory(False, by_sig=load_sigs)
        mod_info = self.all_plugins[mod_name]
        mod_file = ModFile(mod_info, lf)
        mod_file.load_plugin()
        # don't waste time for active Filter plugins, since we already ensure
        # those don't have missing masters before we even begin building the BP
        if mod_name not in self.load_dict and 'Filter' in self.all_tags[
                mod_name]:
            load_set = set(self.load_dict)
            # pass lf in - in initData self.readFactory is not initialized yet
            self.filter_plugin(mod_file, load_set, lf=lf)
        self._loaded_mods[mod_name] = mod_file
        return mod_file

    def scanLoadMods(self,progress):
        """Scans load+merge mods."""
        nullProgress = Progress()
        progress = progress.setFull(len(self.all_plugins))
        load_set = set(self.load_dict)
        patchers_ord = sorted(self._patcher_instances,
                              key=attrgetter('patcher_order'))
        for index, (modName, modInfo) in enumerate(self.all_plugins.items()):
            if modName in self.needs_filter_mods:
                continue
            # Check some commonly needed properties of the current plugin
            is_merged = modName in self.mergeSet
            is_filter = 'Filter' in self.all_tags[modName]
            # iiMode is a hack to support Item Interchange. Actual key used is
            # IIM.
            iiMode = modName in self.ii_mode
            try:
                scan_factory = (self.readFactory, self.mergeFactory)[is_merged]
                progress(index, f'{modName}\n' + _('Loading…'))
                modFile = ModFile(modInfo, scan_factory)
                modFile.load_plugin(SubProgress(progress, index, index + 0.5))
            except ModError as e:
                deprint('load error:', traceback=True)
                self.loadErrorMods.append((modName,e))
                continue
            try:
                #--Error checks
                bush.game.check_loaded_mod(self, modFile)
                pstate = index+0.5
                if is_merged:
                    # If the plugin is to be merged, merge it
                    progress(pstate, f'{modName}\n' + _('Merging…'))
                    self.mergeModFile(modFile,
                        # loaded_mods = None -> signal we won't "filter"
                        load_set if is_filter else None, iiMode)
                elif modName in self.load_dict:
                    # Else, if the plugin is active, update records from it
                    progress(pstate, f'{modName}\n' + _('Scanning…'))
                    self.update_patch_records_from_mod(modFile)
                elif is_filter:
                    # Else, if the plugin is a Filter plugin, filter it but
                    # don't merge any of its contents (since it's inactive, but
                    # we might still want to import filtered data, e.g. actor
                    # factions)
                    self.filter_plugin(modFile, load_set)
                for patcher in patchers_ord:
                    if iiMode and not patcher.iiMode: continue
                    progress(pstate, f'{modName}\n{patcher.getName()}')
                    patcher.scan_mod_file(modFile,nullProgress)
            except CancelError:
                raise
            except:
                bolt.deprint(f'MERGE/SCAN ERROR: {modName}', traceback=True)
                raise
        progress(progress.full, _('Load plugins scanned.'))

    def mergeModFile(self, modFile, loaded_mods, iiMode):
        """Copies contents of modFile into self."""
        for top_grup_sig,block in modFile.tops.items():
            # Make sure that once we merge a record type, all later plugin
            # loads will load that record type too so that we can update the
            # merged records according to load order
            for s in block.get_all_signatures():
                if s not in self.loadFactory.sig_to_type:
                    self.readFactory.add_class(s)
                    self.loadFactory.add_class(s)
            iiSkipMerge = (iiMode and
                           top_grup_sig not in bush.game.leveled_list_types)
            self.tops[top_grup_sig].merge_records(block, loaded_mods,
                                                  self.mergeIds, iiSkipMerge)

    def filter_plugin(self, modFile, loaded_mods, lf=None):
        """Filters the specified plugin according to the specified loaded
        plugins. Does nothing else."""
        # PatchFile might not have its load factory set up yet so we'd get a
        # MobBase instance from it, which obviously can't do filtering
        read_fact = lf or self.readFactory
        for top_grup_sig, block in modFile.iter_tops(read_fact.topTypes):
            # get a temp TopGrup to call merge_records on which will do the
            # filtering
            temp_block = read_fact.getTopClass(top_grup_sig).empty_mob(
                read_fact, top_grup_sig)
            temp_block.merge_records(block, loaded_mods, set(), True)

    def update_patch_records_from_mod(self, modFile):
        """Scans file and overwrites own records with modfile records."""
        shared_rec_types = self.tops.keys() & modFile.tops
        # Keep and update all MGEFs no matter what
        if b'MGEF' in modFile.tops:
            shared_rec_types.discard(b'MGEF')
            add_mgef_to_patch = self.tops[b'MGEF'].setRecord
            for _rid, record in modFile.tops[b'MGEF'].iter_present_records():
                add_mgef_to_patch(record)
        # Update all other record types
        for top_sig, block in self.iter_tops(shared_rec_types):
            block.updateRecords(modFile.tops[top_sig], self.mergeIds)

    def buildPatch(self,log,progress):
        """Completes merge process. Use this when finished using
        scanLoadMods."""
        # Do *not* skip this method, ever - it needs to be called before we
        # save the patch since it trims records and sets up the necessary
        # masters. Without it, we may blow up due to being unable to resolve
        # FormIDs while saving.
        self._log_header(log, self.fileInfo.fn_key)
        # Run buildPatch on each patcher
        self.keepIds |= self.mergeIds
        if self._patcher_instances:
            subProgress = SubProgress(progress, 0, 0.9,
                len(self._patcher_instances))
            for i, patcher in enumerate(sorted(self._patcher_instances,
                    key=attrgetter('patcher_order'))):
                subProgress(i, _('Completing') + f'\n{patcher.getName()}…')
                patcher.buildPatch(log, SubProgress(subProgress, i))
        # Trim records to only keep ones we actually changed
        progress(0.9, _('Completing') + '\n' + _('Trimming records…'))
        for block in self.tops.values():
            block.keepRecords(self.keepIds)
        progress(0.95, _('Completing') + '\n' + _('Converting FormIDs…'))

    def set_attributes(self, *, was_split=False, split_part=0):
        """Create the description, set appropriate flags, etc."""
        self.tes4.masters = load_order.get_ordered(self.used_masters())
        # Build the description
        num_records = sum(x.get_num_records() for x in self.tops.values())
        self.tes4.description = (_('Updated: %(update_time)s') % {
            'update_time': format_date(time.time())} + '\n\n' + _(
            'Records Changed: %(num_recs)d') % {'num_recs': num_records})
        ##: Consider flagging as Overlay instead if that flag is supported by
        # the game and no new records have been included?
        # Flag as ESL if the game supports them, the option is enabled and the
        # BP has <= 2048 new records
        num_new_recs = self.count_new_records(next_object_start=0x800)
        if (bush.game.has_esl and bass.settings['bash.mods.auto_flag_esl'] and
            num_new_recs <= 2048):
            self.tes4.flags1.esl_flag = True
            msg = '\n\n' + _('This patch has been automatically ESL-flagged '
                             'to save a load order slot.')
            self.tes4.description += msg
        if was_split:
            msg = '\n\n' + _(
                'This patch had to be split due to it having more than '
                '%(max_num_masters)d masters. This is part %(bp_part)d.') % {
                'max_num_masters': bush.game.Esp.master_limit,
                'bp_part': split_part + 1,
            }
            self.tes4.description += msg

    def split_patch(self) -> list[Self] | None:
        """Split this patch to fit within the game's master limit. Must not be
        called on BPs that contain a top group with more masters than the game
        allows, otherwise a RuntimeError will be raised.

        :return: A list of the created Bashed Patch files, or None if splitting
            was not possible."""
        bp_part_counter = 1
        def new_bp_part():
            """Helper to create a new BP part in the Data folder and add it to
            ModInfos."""
            nonlocal bp_part_counter
            new_part_name = (f'{self.fileInfo.fn_key.fn_body}-'
                             f'{bp_part_counter}.esp')
            bp_part_counter += 1
            if not (new_part := self.p_file_minfos.get(new_part_name)):
                new_part = self.p_file_minfos.create_new_mod(new_part_name,
                  selected=[latest_sel.fileInfo.fn_key], is_bashed_patch=True)
            return self.__class__(new_part, self.p_file_minfos)
        # Find the top groups with the highest number
        master_dict = self.used_masters_by_top()
        max_masters = bush.game.Esp.master_limit
        if any(len(m) > max_masters for m in master_dict.values()):
            # Let's be defensive here, the check is cheap and will prevent an
            # endless loop down below if someone messes up
            raise RuntimeError(f'Do not call split_patch on BPs with top '
                               f'groups that have >{max_masters} masters!')
        largest_groups = deque(sorted(master_dict,
                    key=lambda k: len(master_dict[k]), reverse=True))
        source_bp_file = self
        latest_sel = source_bp_file
        latest_sel = target_bp_file = new_bp_part()
        all_bp_parts = [source_bp_file, target_bp_file]
        while True:
            while True:
                if not source_bp_file.tops:
                    # These being empty means we ended up just moving
                    # everything from the source to the target, which can't fix
                    # the problem. Fixing this would need record-level
                    # splitting, so just abort here
                    return None
                # Move the top group with the largest number of masters into
                # the target file
                t_sig = largest_groups.popleft()
                target_bp_file.tops[t_sig] = source_bp_file.tops.pop(t_sig)
                all_target_masters = target_bp_file.used_masters()
                if len(all_target_masters) > max_masters:
                    # The most recent move was too much, undo it and move on to
                    # the next file
                    source_bp_file.tops[t_sig] = target_bp_file.tops.pop(t_sig)
                    largest_groups.appendleft(t_sig)
                    break
            all_source_masters = source_bp_file.used_masters()
            if len(all_source_masters) <= max_masters:
                # We're done for good, all BP parts are within the master limit
                break
            # Wow, this source is big. We need another part to move more of the
            # source's top groups into
            latest_sel = target_bp_file = new_bp_part()
            all_bp_parts.append(target_bp_file)
        return all_bp_parts

    def find_unneded_parts(self, valid_parts: list[Self]) -> list[FName]:
        """Find a list of all ModInfo keys that belong to ModInfos which
        represent previously created parts of this split Bashed Patch which are
        no longer needed. This is relevant if a reduction in the number of
        masters left the BP with more parts in the Data folder that are
        actually needed now."""
        re_bp_parts = re.compile(re.escape(self.fileInfo.fn_key.fn_body) +
                                 r'-\d+\.esp')
        valid_part_fnames = {p.fileInfo.fn_key for p in valid_parts}
        unneded_parts = []
        for p_fname in list(self.p_file_minfos):
            if re_bp_parts.match(p_fname) and p_fname not in valid_part_fnames:
                unneded_parts.append(p_fname)
        return unneded_parts
