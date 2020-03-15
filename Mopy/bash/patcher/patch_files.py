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
from __future__ import print_function
import time
from collections import defaultdict, Counter
from operator import attrgetter
from .. import bush # for game etc
from .. import bosh # for modInfos
from .. import bolt # for type hints
from ..balt import readme_url
from .. import load_order
from .. import bass
from ..parsers import LoadFactory, ModFile, MasterSet
from ..brec import MreRecord
from ..bolt import GPath, SubProgress, deprint, Progress
from ..cint import ObModFile, FormID, dump_record, ObCollection, MGEFCode
from ..exception import AbstractError, BoltError, CancelError, ModError, \
    StateError
from ..localize import format_date
from ..record_groups import MobObjects

# the currently executing patch set in _Mod_Patch_Update before showing the
# dialog - used in getAutoItems, to get mods loading before the patch
##: HACK ! replace with method param once gui_patchers are refactored
executing_patch = None # type: bolt.Path

class _PFile(object):
    """Base class of patch files - factoring out common code __WIP__. Wraps an
    executing bashed Patch."""
    def __init__(self, patchers, patch_path):
        """:type patch_path: bolt.Path"""
        #--New attrs
        self._patcher_instances = patchers
        self.patchName = patch_path # the bashed Patch
        # Aliases from one mod name to another. Used by text file patchers.
        self.aliases = {}
        self.mergeIds = set()
        self.loadErrorMods = []
        self.worldOrphanMods = []
        self.unFilteredMods = []
        self.compiledAllMods = []
        self.patcher_mod_skipcount = defaultdict(Counter)
        #--Config
        if bush.game.fsName in (u'FalloutNV', u'Fallout3',):
            self.bodyTags = 'HAGPBFE' #--Default bodytags
        else: #--Default bodytags
            self.bodyTags = 'ARGHTCCPBS'
        #--Mods
        # checking for files to include in patch, investigate
        loadMods = [m for m in load_order.cached_lower_loading_espms(
            self.patchName) if load_order.cached_is_active(m)]
        if not loadMods:
            raise BoltError(u"No active mods loading before the bashed patch")
        self.loadMods = tuple(loadMods)
        self.loadSet = frozenset(self.loadMods)
        self.set_mergeable_mods([])
        self.p_file_minfos = bosh.modInfos
        for patcher in self._patcher_instances:
            patcher.initPatchFile(self)

    def set_mergeable_mods(self, mergeMods):
        """Add to mod lists and sets the mergeable mods."""
        self.mergeMods = mergeMods
        self.mergeSet = set(self.mergeMods)
        self.allMods = load_order.get_ordered(self.loadSet | self.mergeSet)
        self.allSet = frozenset(self.allMods)

    def _log_header(self, log, patch_name):
        log.setHeader((u'= %s' % patch_name) + u' ' + u'=' * 30 + u'#', True)
        log(u"{{CONTENTS=1}}")
        #--Load Mods and error mods
        log.setHeader(u'= ' + _(u'Overview'), True)
        log.setHeader(u'=== ' + _(u'Date/Time'))
        log(u'* ' + format_date(time.time()))
        log(u'* ' + _(u'Elapsed Time: ') + 'TIMEPLACEHOLDER')
        def _link(link_id):
            return (readme_url(mopy=bass.dirs['mopy'], advanced=True),
                    u'#%s' % link_id)
        if self.patcher_mod_skipcount:
            log.setHeader(u'=== ' + _(u'Skipped Imports'))
            log(_(u"The following import patchers skipped records because the "
                  u"imported record required a missing or non-active mod to "
                  u"work properly. If this was not intentional, rebuild the "
                  u"patch after either deactivating the imported mods listed "
                  u"below or activating the missing mod(s)."))
            for patcher, mod_skipcount in \
                    self.patcher_mod_skipcount.iteritems():
                log(u'* ' + _(u'%s skipped %d records:') % (
                patcher, sum(mod_skipcount.values())))
                for mod, skipcount in mod_skipcount.iteritems():
                    log(u'  * ' + _(
                        u'The imported mod, %s, skipped %d records.') % (
                        mod, skipcount))
        if self.unFilteredMods:
            log.setHeader(u'=== ' + _(u'Unfiltered Mods'))
            log(_(u"The following mods were active when the patch was built. "
                  u"For the mods to work properly, you should deactivate the "
                  u"mods and then rebuild the patch with the mods [["
                  u"%s%s|Merged]] in.") % _link(u'patch-filter'))
            for mod in self.unFilteredMods: log(u'* ' + mod.s)
        if self.loadErrorMods:
            log.setHeader(u'=== ' + _(u'Load Error Mods'))
            log(_(u"The following mods had load errors and were skipped while "
                  u"building the patch. Most likely this problem is due to a "
                  u"badly formatted mod. For more info, see [["
                  u"http://www.uesp.net/wiki/Tes4Mod:Wrye_Bash/Bashed_Patch"
                  u"#Error_Messages|Bashed Patch: Error Messages]]."))
            for (mod, e) in self.loadErrorMods: log(
                u'* ' + mod.s + u': %s' % e)
        if self.worldOrphanMods:
            log.setHeader(u'=== ' + _(u'World Orphans'))
            log(_(u"The following mods had orphaned world groups, which were "
                  u"skipped. This is not a major problem, but you might want "
                  u"to use Bash's [[%s%s|Remove World Orphans]] command to "
                  u"repair the mods.") % _link(u'modsRemoveWorldOrphans'))
            for mod in self.worldOrphanMods: log(u'* ' + mod.s)
        if self.compiledAllMods:
            log.setHeader(u'=== ' + _(u'Compiled All'))
            log(_(u"The following mods have an empty compiled version of "
                u"genericLoreScript. This is usually a sign that the mod "
                u"author did a __compile all__ while editing scripts. This "
                u"may interfere with the behavior of other mods that "
                u"intentionally modify scripts from Oblivion.esm. (E.g. Cobl "
                u"and Unofficial Oblivion Patch.) You can use Bash's [["
                u"%s%s|Decompile All]] command to repair the mods."
                  ) % _link(u'modsDecompileAll'))
            for mod in self.compiledAllMods: log(u'* ' + mod.s)
        log.setHeader(u'=== ' + _(u'Active Mods'), True)
        for mname in self.allMods:
            version = bosh.modInfos.getVersion(mname)
            if mname in self.loadSet:
                message = u'* %02X ' % (self.loadMods.index(mname),)
            else:
                message = u'* ++ '
            if version:
                message += _(u'%s  [Version %s]') % (mname.s,version)
            else:
                message += mname.s
            log(message)
        #--Load Mods and error mods
        if self.aliases:
            log.setHeader(u'= ' + _(u'Mod Aliases'))
            for key, value in sorted(self.aliases.iteritems()):
                log(u'* %s >> %s' % (key.s, value.s))

    def init_patchers_data(self, progress): raise AbstractError

class PatchFile(_PFile, ModFile):
    """Defines and executes patcher configuration."""

    #--Instance
    def __init__(self,modInfo,patchers):
        """Initialization."""
        ModFile.__init__(self,modInfo,None)
        self.tes4.author = u'BASHED PATCH'
        self.tes4.masters = [bosh.modInfos.masterName]
        self.longFids = True
        self.keepIds = set()
        _PFile.__init__(self, patchers, modInfo.name)

    def getKeeper(self):
        """Returns a function to add fids to self.keepIds."""
        def keep(fid):
            self.keepIds.add(fid)
            return fid
        return keep

    def init_patchers_data(self, progress):
        """Gives each patcher a chance to get its source data."""
        if not self._patcher_instances: return
        progress = progress.setFull(len(self._patcher_instances))
        for index,patcher in enumerate(self._patcher_instances):
            progress(index,_(u'Preparing')+u'\n'+patcher.getName())
            patcher.initData(SubProgress(progress,index))
        progress(progress.full,_(u'Patchers prepared.'))

    def initFactories(self,progress):
        """Gets load factories."""
        progress(0,_(u"Processing."))
        readClasses = {x for x in bush.game.readClasses}
        writeClasses = {x for x in bush.game.writeClasses}
        for patcher in self._patcher_instances:
            readClasses.update(
                MreRecord.type_class[x] for x in patcher.getReadClasses())
            writeClasses.update(
                MreRecord.type_class[x] for x in patcher.getWriteClasses())
        self.readFactory = LoadFactory(False, *readClasses)
        self.loadFactory = LoadFactory(True, *writeClasses)
        #--Merge Factory
        self.mergeFactory = LoadFactory(False, *bush.game.mergeClasses)

    def scanLoadMods(self,progress):
        """Scans load+merge mods."""
        nullProgress = Progress()
        progress = progress.setFull(len(self.allMods))
        for index,modName in enumerate(self.allMods):
            modInfo = bosh.modInfos[modName]
            bashTags = modInfo.getBashTags()
            if modName in self.loadSet and u'Filter' in bashTags:
                self.unFilteredMods.append(modName)
            try:
                loadFactory = (self.readFactory,self.mergeFactory)[modName in self.mergeSet]
                progress(index,modName.s+u'\n'+_(u'Loading...'))
                modFile = ModFile(modInfo,loadFactory)
                modFile.load(True,SubProgress(progress,index,index+0.5))
            except ModError as e:
                deprint('load error:', traceback=True)
                self.loadErrorMods.append((modName,e))
                continue
            try:
                #--Error checks
                if 'WRLD' in modFile.tops and modFile.WRLD.orphansSkipped:
                    self.worldOrphanMods.append(modName)
                # TODO adapt for other games
                if bush.game.fsName == u'Oblivion' and 'SCPT' in \
                        modFile.tops and modName != GPath(u'Oblivion.esm'):
                    gls = modFile.SCPT.getRecord(0x00025811)
                    if gls and gls.compiled_size == 4 and gls.last_index == 0:
                        self.compiledAllMods.append(modName)
                pstate = index+0.5
                isMerged = modName in self.mergeSet
                doFilter = isMerged and u'Filter' in bashTags
                #--iiMode is a hack to support Item Interchange. Actual key used is InventOnly.
                iiMode = isMerged and bool({u'InventOnly', u'IIM'} & bashTags)
                if isMerged:
                    progress(pstate,modName.s+u'\n'+_(u'Merging...'))
                    self.mergeModFile(modFile,nullProgress,doFilter,iiMode)
                else:
                    progress(pstate,modName.s+u'\n'+_(u'Scanning...'))
                    self.update_patch_records_from_mod(modFile)
                for patcher in sorted(self._patcher_instances, key=attrgetter('scanOrder')):
                    if iiMode and not patcher.iiMode: continue
                    progress(pstate,u'%s\n%s' % (modName.s,patcher.name))
                    patcher.scanModFile(modFile,nullProgress)
                # Clip max version at 1.0.  See explanation in the CBash version as to why.
                self.tes4.version = min(max(modFile.tes4.version, self.tes4.version), max(bush.game.Esp.validHeaderVersions))
            except CancelError:
                raise
            except:
                print(_(u"MERGE/SCAN ERROR:"),modName.s)
                raise
        progress(progress.full,_(u'Load mods scanned.'))

    def mergeModFile(self,modFile,progress,doFilter,iiMode):
        """Copies contents of modFile into self."""
        mergeIds = self.mergeIds
        mergeIdsAdd = mergeIds.add
        loadSet = self.loadSet
        modFile.convertToLongFids()
        badForm = (GPath(u"Oblivion.esm"),0xA31D) #--DarkPCB record
        selfLoadFactoryRecTypes = self.loadFactory.recTypes
        selfMergeFactoryType_class = self.mergeFactory.type_class
        selfReadFactoryAddClass = self.readFactory.addClass
        selfLoadFactoryAddClass = self.loadFactory.addClass
        nullFid = (bosh.modInfos.masterName, 0)
        for blockType,block in modFile.tops.iteritems():
            iiSkipMerge = iiMode and blockType not in bush.game.listTypes
            #--Make sure block type is also in read and write factories
            if blockType not in selfLoadFactoryRecTypes:
                recClass = selfMergeFactoryType_class[blockType]
                selfReadFactoryAddClass(recClass)
                selfLoadFactoryAddClass(recClass)
            patchBlock = getattr(self,blockType)
            patchBlockSetRecord = patchBlock.setRecord
            if not isinstance(patchBlock,MobObjects):
                raise BoltError(u"Merge unsupported for type: "+blockType)
            filtered = []
            filteredAppend = filtered.append
            loadSetIssuperset = loadSet.issuperset
            for record in block.getActiveRecords():
                fid = record.fid
                if fid == badForm: continue
                #--Include this record?
                if doFilter:
                    record.mergeFilter(loadSet)
                    masters = MasterSet()
                    record.updateMasters(masters)
                    if not loadSetIssuperset(masters):
                        continue
                filteredAppend(record)
                if iiSkipMerge: continue
                record = record.getTypeCopy()
                patchBlockSetRecord(record)
                if record.isKeyedByEid and fid == nullFid:
                    mergeIdsAdd(record.eid)
                else:
                    mergeIdsAdd(fid)
            #--Filter records
            block.records = filtered
            block.indexRecords()

    def update_patch_records_from_mod(self, modFile):
        """Scans file and overwrites own records with modfile records."""
        #--Keep all MGEFs
        modFile.convertToLongFids(('MGEF',))
        if 'MGEF' in modFile.tops:
            for record in modFile.MGEF.getActiveRecords():
                self.MGEF.setRecord(record.getTypeCopy())
        #--Merger, override.
        mergeIds = self.mergeIds
        mapper = modFile.getLongMapper()
        for blockType,block in self.tops.iteritems():
            if blockType in modFile.tops:
                block.updateRecords(modFile.tops[blockType],mapper,mergeIds)

    def buildPatch(self,log,progress):
        """Completes merge process. Use this when finished using
        scanLoadMods."""
        if not self._patcher_instances: return
        self._log_header(log, self.fileInfo.name.s)
        # Run buildPatch on each patcher
        self.keepIds |= self.mergeIds
        subProgress = SubProgress(progress, 0, 0.9, len(self._patcher_instances))
        for index,patcher in enumerate(sorted(self._patcher_instances, key=attrgetter('editOrder'))):
            subProgress(index,_(u'Completing')+u'\n%s...' % patcher.getName())
            patcher.buildPatch(log,SubProgress(subProgress,index))
        # Trim records to only keep ones we actually changed
        progress(0.9,_(u'Completing')+u'\n'+_(u'Trimming records...'))
        for block in self.tops.values():
            block.keepRecords(self.keepIds)
        progress(0.95,_(u'Completing')+u'\n'+_(u'Converting fids...'))
        # Convert masters to short fids
        self.tes4.masters = self.getMastersUsed()
        self.convertToShortFids()
        progress(1.0,_(u"Compiled."))
        # Build the description
        numRecords = sum([x.getNumRecords(False) for x in self.tops.values()])
        self.tes4.description = (
                _(u'Updated: ') + format_date(time.time()) + u'\n\n' + _(
                u'Records Changed') + u': %d' % numRecords)
        # Flag as ESL if the game supports them and the option is enabled
        # Note that we can always safely mark as ESL, since the BP only ever
        # contains overrides, no new records
        if bush.game.has_esl and bass.settings['bash.mods.auto_flag_esl']:
            self.tes4.flags1.eslFile = True
            self.tes4.description += (u'\nThis patch has been automatically '
                                      u'ESL-flagged to save a load order '
                                      u'slot.')

class CBash_PatchFile(_PFile, ObModFile):
    """Defines and executes patcher configuration."""

    #--Instance
    def __init__(self, patch_name, patchers):
        """Initialization."""
        self.group_patchers = defaultdict(list)
        self.indexMGEFs = False
        self.mgef_school = bush.game.mgef_school.copy()
        self.mgef_name = bush.game.mgef_name.copy()
        self.hostileEffects = bush.game.hostile_effects.copy()
        self.scanSet = set()
        self.races_vanilla = ['argonian', 'breton', 'dremora', 'dark elf',
                              'dark seducer', 'golden saint', 'high elf',
                              'imperial', 'khajiit', 'nord', 'orc', 'redguard',
                              'wood elf']
        self.races_data = {'EYES': [], 'HAIR': []}
        _PFile.__init__(self, patchers, patch_name)

    def init_patchers_data(self, progress):
        """Gives each patcher a chance to get its source data."""
        if not self._patcher_instances: return
        progress = progress.setFull(len(self._patcher_instances))
        for index,patcher in enumerate(sorted(self._patcher_instances, key=attrgetter('scanOrder'))):
            progress(index,_(u'Preparing')+u'\n'+patcher.getName())
            patcher.initData(self.group_patchers,SubProgress(progress,index))
        progress(progress.full,_(u'Patchers prepared.'))

    def mergeModFile(self,modFile,progress,doFilter,iiMode,group):
        """Copies contents of modFile group into self."""
        if iiMode and group not in ('LVLC','LVLI','LVSP'): return
        mergeIds = self.mergeIds
        badForm = FormID(GPath(u"Oblivion.esm"),0xA31D) #--DarkPCB record
        for record in getattr(modFile,group):
            #don't merge deleted items
            if record.IsDeleted and group not in ('REFRS','ACHRS','ACRES'):
                print(group)
                continue
            fid = record.fid
            if not fid.ValidateFormID(self): continue
            if fid == badForm: continue
            #--Include this record?
            if record.IsWinning():
                if record.HasInvalidFormIDs():
                    if doFilter:
                        record.mergeFilter(self)
                        if record.HasInvalidFormIDs():
                            print(u"Debugging mergeModFile - Skipping", fid, u"in mod (", record.GetParentMod().ModName, u")due to failed merge filter")
                            dump_record(record)
                            print()
                            continue
                    else:
                        print(u"Debugging mergeModFile - Skipping", fid, u"in mod (", record.GetParentMod().ModName, u")due to invalid formIDs")
                        dump_record(record)
                        print()
                        continue
                if record.IsDeleted and group in ('REFRS','ACHRS','ACRES'):
                    undelete = True
                    override = record.Conflicts()[1].CopyAsOverride(self, UseWinningParents=True)
                else:
                    undelete = False
                    override = record.CopyAsOverride(self, UseWinningParents=True)
                if override:
                    if undelete:
                        override.posZ -= 1000
                        override.IsInitiallyDisabled = True
                    mergeIds.add(override.fid)

    def buildPatch(self,progress):
        """Scans load+merge mods."""
        #Parent records must be processed before any children
        #EYES,HAIR must be processed before RACE
        # This should probably be updated for FO3/FNV/TES5 - see issue #287
        groupOrder = ['GMST','GLOB','MGEF','CLAS','HAIR','EYES','RACE',
                      'SOUN','SKIL','SCPT','LTEX','ENCH','SPEL','BSGN',
                      'ACTI','APPA','ARMO','BOOK','CLOT','DOOR','INGR',
                      'LIGH','MISC','STAT','GRAS','TREE','FLOR','FURN',
                      'WEAP','AMMO','FACT','LVLC','LVLI','LVSP','NPC_',
                      'CREA','CONT','SLGM','KEYM','ALCH','SBSP','SGST',
                      'WTHR','QUST','IDLE','PACK','CSTY','LSCR','ANIO',
                      'WATR','EFSH','CLMT','REGN','DIAL','INFOS','WRLD',
                      'ROADS','CELL','CELLS','PGRDS','LANDS','ACHRS',
                      'ACRES','REFRS']

        iiModeSet = {u'InventOnly', u'IIM'}
        levelLists = bush.game.listTypes
        nullProgress = Progress()

        infos = bosh.modInfos
        IIMSet = set([modName for modName in (self.allSet | self.scanSet) if
                      bool(infos[modName].getBashTags() & iiModeSet)])

        self.Current = ObCollection(ModsPath=bass.dirs['mods'].s)

        #add order reordered
        #mods can't be added more than once, and a mod could be in both the loadSet and mergeSet or loadSet and scanSet
        #if it was added as a normal mod first, it isn't flagged correctly when later added as a merge mod
        #if it was added as a scan mod first, it isn't flagged correctly when later added as a normal mod
        # checking for files to include in patch, investigate
        for m in load_order.cached_lower_loading_espms(self.patchName):
            real_filename = infos[m].getPath().stail # beware of .ghost
            if m in self.mergeSet: self.Current.addMergeMod(real_filename)
            elif m in self.loadSet: self.Current.addMod(real_filename)
            elif m in self.scanSet: self.Current.addScanMod(real_filename)
        self.patchName.temp.remove()
        patchFile = self.patchFile = self.Current.addMod(self.patchName.temp.s, CreateNew=True)
        self.Current.load()

        if self.Current.LookupModFileLoadOrder(self.patchName.temp.s) <= 0:
            print((u'\n'.join(
                (_(u"Please copy this entire message and report it on the "
                   u"current official thread at "
                   u"https://afkmods.com/index.php?/topic/4966-wrye-bash-all-games/."),
                 _(u'Also with:'),
                 _(u'1. Your OS:'),
                 _(u'2. Your installed MS Visual C++ redistributable '
                   u'versions:'),
                 _(u'3. Your system RAM amount:'),
                 _(u'4. How much memory Python.exe\pythonw.exe or '
                   u'Wrye Bash.exe is using'),
                 _(u'5. and finally... if restarting Wrye Bash and trying '
                   u'again and building the CBash Bashed Patch right away '
                   u'works fine'))) + u'\n'))
            print(self.Current.Debug_DumpModFiles())
            raise StateError()
        ObModFile.__init__(self, patchFile._ModID)

        self.TES4.author = u'BASHED PATCH'

        #With this indexing, MGEFs may be looped through twice if another patcher also looks through MGEFs
        #It's inefficient, but it really shouldn't be a problem since there are so few MGEFs.
        if self.indexMGEFs:
            mgefId_hostile = {}
            self.mgef_school.clear()
            self.mgef_name.clear()
            for modName in self.allMods:
                modFile = self.Current.LookupModFile(modName.s)
                for record in modFile.MGEF:
                    full = record.full
                    eid = record.eid
                    if full and eid:
                        eidRaw = eid.encode('cp1252')
                        mgefId = MGEFCode(eidRaw) if record.recordVersion is None else record.mgefCode
                        self.mgef_school[mgefId] = record.schoolType
                        self.mgef_name[mgefId] = full
                        mgefId_hostile[mgefId] = record.IsHostile
                    record.UnloadRecord()
            self.hostileEffects = set([mgefId for mgefId, hostile in mgefId_hostile.iteritems() if hostile])
        self.completeMods = load_order.get_ordered(self.allSet | self.scanSet)
        group_patchers = self.group_patchers

        mod_patchers = group_patchers.get('MOD')
        if mod_patchers:
            mod_apply = [patcher.mod_apply for patcher in sorted(mod_patchers,key=attrgetter('editOrder')) if hasattr(patcher,'mod_apply')]
            del group_patchers['MOD']
            del mod_patchers
        else:
            mod_apply = []

        for modName in self.completeMods:
            modInfo = bosh.modInfos[modName]
            bashTags = modInfo.getBashTags()
            modFile = self.Current.LookupModFile(modInfo.getPath().stail)

            #--Error checks
            if modName in self.loadSet and u'Filter' in bashTags:
                self.unFilteredMods.append(modName)
            if bush.game.fsName == u'Oblivion':
                gls = modFile.LookupRecord(FormID(0x00025811))
                if gls and gls.compiledSize == 4 and gls.lastIndex == 0 and \
                                modName != GPath(u'Oblivion.esm'):
                    self.compiledAllMods.append(modName)
            isScanned = modName in self.scanSet and modName not in self.loadSet and modName not in self.mergeSet
            if not isScanned:
                for p_mod_apply in mod_apply:
                    p_mod_apply(modFile)

        numFinishers = sum(
            any(hasattr(p, 'finishPatch') for p in patchers) for patchers in
            group_patchers.itervalues())

        progress = progress.setFull(len(groupOrder) + max(numFinishers,1))
        maxVersion = 0
        for index,group in enumerate(groupOrder):
            patchers = group_patchers.get(group, [])
            pstate = 0
            subProgress = SubProgress(progress,index)
            subProgress.setFull(max(len(self.completeMods),1))
            p_scan_sorted = sorted([p for p in patchers if hasattr(p, 'scan')],
                                   key=attrgetter('scanOrder'))
            for modName in self.completeMods:
                if modName == self.patchName: continue
                modInfo = bosh.modInfos[modName]
                bashTags = modInfo.getBashTags()
                isScanned = modName in self.scanSet and modName not in self.loadSet and modName not in self.mergeSet
                isMerged = modName in self.mergeSet
                doFilter = isMerged and u'Filter' in bashTags
                #--iiMode is a hack to support Item Interchange. Actual key used is InventOnly.
                iiMode = isMerged and bool(iiModeSet & bashTags)
                iiFilter = IIMSet and not (iiMode or group in levelLists)
                modFile = self.Current.LookupModFile(modInfo.getPath().stail)
                modGName = modFile.GName
                sorted_scan_ = [p for p in p_scan_sorted if
                    not p.scanRequiresChecked or (modGName in p.srcs)]
                if patchers:
                    subProgress(pstate,_(u'Patching...')+u'\n%s::%s' % (modName.s,group))
                    pstate += 1
                    #Filter the used patchers as needed
                    if iiMode:
                        applyPatchers = [p.apply for p in
                            sorted(patchers, key=attrgetter('editOrder'))
                        if hasattr(p, 'apply') and p.iiMode
                        if not p.applyRequiresChecked or (modGName in p.srcs)]
                        scanPatchers = [p.scan for p in sorted_scan_ if p.iiMode]
                    elif isScanned:
                        applyPatchers = [] #Scanned mods should never be copied directly into the bashed patch.
                        scanPatchers = [p.scan for p in sorted_scan_ if p.allowUnloaded]
                    else:
                        applyPatchers = [p.apply for p in
                            sorted(patchers, key=attrgetter('editOrder'))
                        if hasattr(p, 'apply')
                        if not p.applyRequiresChecked or (modGName in p.srcs)]
                        scanPatchers = [p.scan for p in sorted_scan_]
                    #See if all the patchers were filtered out
                    if not (applyPatchers or scanPatchers): continue
                    for record in getattr(modFile, group):
                        #If conflicts is > 0, it will include all conflicts, even the record that called it
                        #(i.e. len(conflicts) will never equal 1)
                        #The winning record is at position 0, and the last record is the one most overridden
                        if doFilter:
                            if not record.fid.ValidateFormID(self): continue
                            if record.HasInvalidFormIDs():
                                record.mergeFilter(self)
                                if record.HasInvalidFormIDs():
                                    print(u"Debugging buildPatch - Skipping", record.fid, u"in mod (", record.GetParentMod().ModName, u")due to failed merge filter")
                                    dump_record(record)
                                    print()
                                    continue

                        if not isScanned and record.HasInvalidFormIDs():
                            print(u"Debugging buildPatch - Skipping", record.fid, u"in mod (", record.GetParentMod().ModName, u")due to invalid formIDs")
                            dump_record(record)
                            print()
                            continue

                        if iiFilter:
                            #InventOnly/IIM tags are a pain. They don't fit the normal patch model.
                            #They're basically a mixture of scanned and merged.
                            #This effectively hides all non-level list records from the other patchers
                            conflicts = [conflict for conflict in record.Conflicts() if conflict.GetParentMod().GName not in IIMSet]
                            isWinning = (len(conflicts) < 2 or conflicts[0] == record)
                        else:
                            #Prevents scanned records from being scanned twice if the scanned record loads later than the real winning record
                            # (once when the real winning record is applied, and once when the scanned record is later encountered)
                            if isScanned and record.IsWinning(True): #Not the most optimized, but works well enough
                                continue #doesn't work if the record's been copied into the patch...needs work
                            isWinning = record.IsWinning()
                        for p_apply in applyPatchers if isWinning else scanPatchers:
                            p_apply(modFile, record, bashTags)
                        record.UnloadRecord()
                if isMerged:
                    progress(index,modFile.ModName+u'\n'+_(u'Merging...')+u'\n'+group)
                    self.mergeModFile(modFile,nullProgress,doFilter,iiMode,group)
                maxVersion = max(modFile.TES4.version, maxVersion)
        # Force 1.0 as max TES4 version for now, as we don't expect any new esp format changes,
        # and if they do come about, we can always change this.  Plus this will solve issues where
        # Mod files mistakenly have the header version set > 1.0
        self.Current.ClearReferenceLog()
        self.TES4.version = min(maxVersion, max(bush.game.Esp.validHeaderVersions))
        #Finish the patch
        progress(len(groupOrder))
        subProgress = SubProgress(progress,len(groupOrder))
        subProgress.setFull(max(numFinishers,1))
        pstate = 0
        for group, patchers in group_patchers.iteritems():
            finishPatchers = [patcher.finishPatch for patcher in sorted(patchers,key=attrgetter('editOrder')) if hasattr(patcher,'finishPatch')]
            if finishPatchers:
                subProgress(pstate,_(u'Final Patching...')+u'\n%s::%s' % (self.ModName,group))
                pstate += 1
                for p_finish in finishPatchers:
                    p_finish(self, subProgress)
        #--Fix UDR's
        progress(0,_(u'Cleaning...'))
        records = self.ACRES + self.ACHRS + self.REFRS
        progress.setFull(max(len(records),1))
        for i,record in enumerate(records):
            progress(i)
            if record.IsDeleted:
                record.IsDeleted = False
                record.IsIgnored = True
        #--Done
        progress(progress.full,_(u'Patchers applied.'))

    def buildPatchLog(self, log, progress):
        """Completes merge process. Use this when finished using buildPatch."""
        if not self._patcher_instances: return
        self._log_header(log, self.patchName)
        #--Patchers
        subProgress = SubProgress(progress, 0, 0.9, len(self._patcher_instances))
        for index,patcher in enumerate(sorted(self._patcher_instances, key=attrgetter('editOrder'))):
            subProgress(index,_(u'Completing')+u'\n%s...' % patcher.getName())
            patcher.buildPatchLog(log)
        progress(1.0,_(u"Compiled."))
        #--Description
        numRecords = sum([len(x) for x in self.aggregates.values()])
        self.TES4.description = (
                _(u"Updated: %s") % format_date(time.time()) + u'\n\n' + _(
                u'Records Changed') + u': %d' % numRecords)
