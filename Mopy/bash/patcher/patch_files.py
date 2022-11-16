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
from __future__ import annotations
import time
from collections import defaultdict, Counter
from itertools import chain
from operator import attrgetter
from .. import bolt # for type hints
from .. import bush # for game etc
from .. import load_order, bass
from ..bolt import SubProgress, deprint, Progress, dict_sort, readme_url
from ..brec import RecHeader, FormId, RecordType
from ..exception import BoltError, CancelError, ModError
from ..localize import format_date
from ..mod_files import ModFile, LoadFactory

# the currently executing patch set in _Mod_Patch_Update before showing the
# dialog - used in _getAutoItems, to get mods loading before the patch
##: HACK ! replace with method param once gui_patchers are refactored
executing_patch: bolt.FName | None = None

class PatchFile(ModFile):
    """Base class of patch files. Wraps an executing bashed Patch."""

    def set_mergeable_mods(self, mergeMods):
        """Set `mergeSet` attribute to the srcs of MergePatchesPatcher."""
        self.mergeSet = set(mergeMods)
        self.merged_or_loaded = self.mergeSet | self.loadSet
        self.merged_or_loaded_ord = load_order.get_ordered(
            self.merged_or_loaded)

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
        for mname in self.merged_or_loaded_ord:
            version = self.p_file_minfos.getVersion(mname)
            if mname in self.loadSet:
                message = f'* {self.loadMods.index(mname):02X} '
            else:
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
    def __init__(self, modInfo, p_file_minfos):
        """Initialization."""
        ModFile.__init__(self,modInfo,None)
        self.tes4.author = 'BASHED PATCH'
        self.tes4.masters = [bush.game.master_file]
        self.keepIds = set()
        # Aliases from one mod name to another. Used by text file patchers.
        self.pfile_aliases = {}
        self.mergeIds = set()
        self.loadErrorMods = []
        self.worldOrphanMods = []
        self.needs_filter_mods = []
        self.compiledAllMods = []
        self.patcher_mod_skipcount = defaultdict(Counter)
        #--Mods
        # checking for files to include in patch, investigate
        self.all_plugins = load_order.cached_lower_loading(modInfo.fn_key)
        # exclude modding esms (those tend to be huge)
        self.all_plugins = [k for k in self.all_plugins if
                            k not in bush.game.modding_esm_size]
        loadMods = [m for m in self.all_plugins
                    if load_order.cached_is_active(m)]
        if not loadMods:
            raise BoltError('No active plugins loading before the Bashed '
                            'Patch')
        self.loadMods = tuple(loadMods)
        self.loadSet = frozenset(self.loadMods)
        self.set_mergeable_mods([])
        self.p_file_minfos = p_file_minfos

    def getKeeper(self):
        """Returns a function to add fids to self.keepIds."""
        return self.keepIds.add

    def create_record(self, new_rec_sig: bytes, new_rec_fid: FormId = None):
        """Creates a new record with the specified record signature (and
        optionally the specified FormID - if it's not given, it will become a
        new record inside the BP's FormID space), adds it to this patch and
        returns it."""
        if new_rec_fid is None:
            new_rec_fid = FormId.from_tuple(
                (self.fileInfo.fn_key, self.tes4.getNextObject()))
        new_rec = RecordType.sig_to_class[new_rec_sig](
            RecHeader(new_rec_sig, arg2=new_rec_fid, _entering_context=True))
        self.keepIds.add(new_rec_fid)
        self.tops[new_rec_sig].setRecord(new_rec, do_copy=False)
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

    def scanLoadMods(self,progress):
        """Scans load+merge mods."""
        nullProgress = Progress()
        progress = progress.setFull(len(self.all_plugins))
        all_plugins_set = set(self.all_plugins)
        # Set of all Bash Tags that don't trigger an import from some patcher
        non_import_bts = {'Deactivate', 'Filter', 'IIM',
                          'MustBeActiveIfImported', 'NoMerge'}
        for index,modName in enumerate(self.all_plugins):
            modInfo = self.p_file_minfos[modName]
            # Check some commonly needed properties of the current plugin
            bashTags = modInfo.getBashTags()
            is_loaded = modName in self.loadSet
            is_merged = modName in self.mergeSet
            can_filter = 'Filter' in bashTags
            if (set(modInfo.masterNames) - all_plugins_set and not can_filter
                    and (bashTags - non_import_bts)):
                # This plugin has missing masters, is not Filter-tagged but
                # still wants to import data -> user needs to add Filter tag
                self.needs_filter_mods.append(modName)
            # iiMode is a hack to support Item Interchange. Actual key used is
            # IIM.
            iiMode = is_merged and 'IIM' in bashTags
            try:
                loadFactory = (self.readFactory, self.mergeFactory)[is_merged]
                progress(index, f'{modName}\n' + _('Loading...'))
                modFile = ModFile(modInfo, loadFactory)
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
                    self.mergeModFile(modFile, can_filter, iiMode)
                elif is_loaded:
                    # Else, if the plugin is active, update records from it. If
                    # the plugin is inactive, we only want to import from it,
                    # so do nothing here
                    progress(pstate, f'{modName}\n' + _('Scanning...'))
                    self.update_patch_records_from_mod(modFile)
                for patcher in sorted(self._patcher_instances,
                        key=attrgetter('patcher_order')):
                    if iiMode and not patcher.iiMode: continue
                    progress(pstate, f'{modName}\n{patcher.getName()}')
                    patcher.scan_mod_file(modFile,nullProgress)
            except CancelError:
                raise
            except:
                bolt.deprint(f'MERGE/SCAN ERROR: {modName}', traceback=True)
                raise
        progress(progress.full, _('Load plugins scanned.'))

    def mergeModFile(self, modFile, doFilter, iiMode):
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
            self.tops[top_grup_sig].merge_records(block, self.loadSet,
                self.mergeIds, iiSkipMerge, doFilter)

    def update_patch_records_from_mod(self, modFile):
        """Scans file and overwrites own records with modfile records."""
        shared_rec_types = set(self.tops) & set(modFile.tops)
        # Keep and update all MGEFs no matter what
        if b'MGEF' in modFile.tops:
            shared_rec_types.discard(b'MGEF')
            add_mgef_to_patch = self.tops[b'MGEF'].setRecord
            for _rid, record in modFile.tops[b'MGEF'].getActiveRecords():
                add_mgef_to_patch(record)
        # Update all other record types
        for block_type in shared_rec_types:
            self.tops[block_type].updateRecords(modFile.tops[block_type],
                                                self.mergeIds)

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
        num_records = sum(x.getNumRecords(includeGroups=False)
                          for x in self.tops.values())
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
