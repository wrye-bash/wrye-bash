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
from __future__ import annotations

import time
from collections import Counter, defaultdict
from itertools import chain, count
from operator import attrgetter

from .. import bass, load_order
from .. import bolt # for type hints
from .. import bush # for game etc
from ..bolt import Progress, SubProgress, deprint, dict_sort, readme_url
from ..exception import BoltError, CancelError, ModError
from ..localize import format_date
from ..mod_files import LoadFactory, ModFile

class PatchFile(ModFile):
    """Base class of patch files. Wraps an executing bashed Patch."""

    def set_mergeable_mods(self, mergeMods):
        """Set 'mergeSet' attribute to the srcs of MergePatchesPatcher."""
        self.mergeSet = set(mergeMods)
        self.merged_or_loaded = {*self.mergeSet, *self.load_dict}
        self.merged_or_loaded_ord = {m: self.p_file_minfos[m] for m in
            load_order.get_ordered(self.merged_or_loaded)}
        self.ii_mode = {m for m in self.mergeSet if
                        'IIM' in self.p_file_minfos[m].getBashTags()}

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
            log(_('The following plugins are missing masters and have tags '
                  'that indicate that you want to import data from them into '
                  'the Bashed Patch. However, since they have missing masters '
                  'and do not have a Filter tag they have been skipped. '
                  'Consider adding a Filter tag to them or installing the '
                  'required masters. See the '
                  '[[%(filtering_section)s|Filtering]] section of the readme '
                  'for more information.') % {
                'filtering_section': _link('patch-filter')})
            for mod in self.needs_filter_mods: log(f'* {mod}')
        if self.loadErrorMods:
            log.setHeader('=== ' + _('Load Error Plugins'))
            log(_('The following plugins had load errors and were skipped '
                  'while building the patch. Most likely this problem is due '
                  'to a badly formatted plugin. For more info, generate a '
                  '[[%(url_bbd)s|BashBugDump]].') % {
                'url_bbd': 'https://github.com/wrye-bash/wrye-bash/wiki/'
                           '%5Bgithub%5D-Reporting-a-bug#the-bashbugdumplog'})
            for (mod, e) in self.loadErrorMods: log(f'* {mod}: {e}')
        if self.worldOrphanMods:
            log.setHeader('=== ' + _('World Orphans'))
            log(_("The following plugins had orphaned world groups, which "
                  "were skipped. This is not a major problem, but you might "
                  "want to use Wrye Bash's "
                  "[[%(url_rwo)s|Remove World Orphans]] command to repair "
                  "the plugins.") % {
                'url_rwo': _link('modsRemoveWorldOrphans')})
            for mod in self.worldOrphanMods: log(f'* {mod}')
        if self.compiledAllMods:
            log.setHeader('=== ' + _('Compiled All'))
            log(_("The following plugins have an empty compiled version of "
                  "genericLoreScript. This is usually a sign that the plugin "
                  "author did a __compile all__ while editing scripts. This "
                  "may interfere with the behavior of other plugins that "
                  "intentionally modify scripts from %(game_name)s (e.g. Cobl "
                  "and Unofficial Oblivion Patch). You can use Wrye Bash's "
                  "[[%(url_decomp)s|Decompile All]] command to repair the "
                  "plugins.") % {'game_name': bush.game.master_file,
                                 'url_decomp': _link('modsDecompileAll')})
            for mod in self.compiledAllMods: log(f'* {mod}')
        log.setHeader('=== ' + _('Active Plugins'), True)
        for mname, modinfo in self.merged_or_loaded_ord.items():
            version = modinfo.get_version()
            try:
                message = f'* {self.load_dict[mname]:02X} '
            except KeyError:
                message = '* ++ '
            if version:
                message += _('%(msg_plugin)s  [Version %(plugin_ver)s]') % {
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
        loaded_mods = {m: next(c) for m in self.all_plugins if
                       load_order.cached_is_active(m)}
        # TODO: display those
        loaded_modding_esms = [m for m in load_order.cached_active_tuple() if
                               m in bush.game.modding_esm_size]
        if not loaded_mods:
            raise BoltError('No active plugins loading before the Bashed '
                            'Patch')
        self.load_dict = loaded_mods # used in printing BP masters' indexes
        self.set_mergeable_mods([]) # reset - depends on load_dict
        # Populate mod arrays for the rest of the patch stages ----------------
        all_plugins_set = set(self.all_plugins)
        self.needs_filter_mods = {}
        self.bp_mergeable = set() # plugins we can show as sources for the merge patcher
        # inactive plugins with missing masters - that may be ok
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
        mi_mergeable = pfile_minfos.mergeable
        for index, (modName, modInfo) in enumerate(self.all_plugins.items()):
            # Check some commonly needed properties of the current plugin
            bashTags = modInfo.getBashTags()
            is_loaded = modName in loaded_mods
            for master in modInfo.masterNames:
                if master not in loaded_mods:
                    if is_loaded:
                        self.active_mm[modName].append(master)
                    elif master not in all_plugins_set: ##: test against modInfos?
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
            if (modName in mi_mergeable and
                    modName not in self.inactive_inm and
                    'NoMerge' not in bashTags):
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
        if mod_name not in self.load_dict and 'Filter' in \
                mod_info.getBashTags():
            load_set = set(self.load_dict)
            # PatchFile does not have its load factory set up yet so we'd get a
            # MobBase instance from it, which obviously can't do filtering. So
            # use a temporary LoadFactory as a workaround
            for top_grup_sig, filter_block in mod_file.tops.items():
                temp_block = lf.getTopClass(top_grup_sig).empty_mob(
                    lf, top_grup_sig)
                temp_block.merge_records(filter_block, load_set, set(), True)
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
            is_filter = 'Filter' in modInfo.getBashTags()
            # iiMode is a hack to support Item Interchange. Actual key used is
            # IIM.
            iiMode = modName in self.ii_mode
            try:
                scan_factory = (self.readFactory, self.mergeFactory)[is_merged]
                progress(index, f'{modName}\n' + _('Loading...'))
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
                    progress(pstate, f'{modName}\n' + _('Merging...'))
                    self.mergeModFile(modFile,
                        # loaded_mods = None -> signal we won't "filter"
                        load_set if is_filter else None, iiMode)
                elif modName in self.load_dict:
                    # Else, if the plugin is active, update records from it
                    progress(pstate, f'{modName}\n' + _('Scanning...'))
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
            iiSkipMerge = iiMode and top_grup_sig not in bush.game.listTypes
            self.tops[top_grup_sig].merge_records(block, loaded_mods,
                                                  self.mergeIds, iiSkipMerge)

    def filter_plugin(self, modFile, loaded_mods):
        """Filters the specified plugin according to the specified loaded
        plugins. Does nothing else."""
        read_fact = self.readFactory
        for top_grup_sig, block in modFile.tops.items():
            if top_grup_sig in read_fact.topTypes:
                ##: Same ugly hack as in _filtered_mod_read, figure out a
                # better way (can't just use self.tops since that uses
                # loadFactory rather than readFactory)
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
                subProgress(i, _('Completing') + f'\n{patcher.getName()}...')
                patcher.buildPatch(log, SubProgress(subProgress, i))
        # Trim records to only keep ones we actually changed
        progress(0.9, _('Completing') + '\n' + _('Trimming records...'))
        for block in self.tops.values():
            block.keepRecords(self.keepIds)
        progress(0.95, _('Completing') + '\n' + _('Converting FormIDs...'))
        # Convert masters to short fids
        self.tes4.masters = self.getMastersUsed()
        progress(1.0, _('Compiled.'))
        # Build the description
        num_records = sum(x.get_num_records() for x in self.tops.values())
        self.tes4.description = (_('Updated: %(update_time)s') % {
            'update_time': format_date(time.time())} + '\n\n' + _(
            'Records Changed: %(num_recs)d') % {'num_recs': num_records})
        # Flag as ESL if the game supports them and the option is enabled
        # Note that we can always safely mark as ESL as long as the number of
        # new records we created is smaller than 0xFFF, since the BP only ever
        # copies overrides into itself, no new records. The only new records it
        # can contain come from Tweak Settings, which creates them through
        # getNextObject and so properly increments nextObject.
        if (bush.game.has_esl and bass.settings['bash.mods.auto_flag_esl'] and
                self.tes4.nextObject <= 0xFFF):
            self.tes4.flags1.esl_flag = True
            msg = '\n' + _('This patch has been automatically ESL-flagged to '
                           'save a load order slot.')
            self.tes4.description += msg
