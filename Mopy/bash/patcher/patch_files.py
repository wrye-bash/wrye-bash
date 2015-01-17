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
import time
from operator import attrgetter
from .. import bush # for game etc
from .. import bosh # for modInfos
from ..bosh import ModFile, ModInfo, LoadFactory, MasterSet, formatDate
from ..brec import MreRecord, ModError
from ..balt import showWarning
from ..bolt import GPath, BoltError, CancelError, SubProgress, deprint, \
    Progress
from ..record_groups import MobObjects

class PatchFile(ModFile):
    """Defines and executes patcher configuration."""

    @staticmethod
    def generateNextBashedPatch(wxParent=None):
        """Attempts to create a new bashed patch, numbered from 0 to 9.  If a lowered number bashed patch exists,
           will create the next in the sequence.  if wxParent is not None and we are unable to create a patch,
           displays a dialog error"""
        for num in xrange(10):
            modName = GPath(u'Bashed Patch, %d.esp' % num)
            if modName not in bosh.modInfos:
                patchInfo = ModInfo(bosh.modInfos.dir,GPath(modName))
                patchInfo.mtime = max([time.time()]+[info.mtime for info in bosh.modInfos.values()])
                patchFile = ModFile(patchInfo)
                patchFile.tes4.author = u'BASHED PATCH'
                patchFile.safeSave()
                bosh.modInfos.refresh()
                return modName
        else:
            if wxParent is not None:
                showWarning(wxParent, u"Unable to create new bashed patch: 10 bashed patches already exist!")
        return None

    #--Instance
    def __init__(self,modInfo,patchers):
        """Initialization."""
        ModFile.__init__(self,modInfo,None)
        self.tes4.author = u'BASHED PATCH'
        self.tes4.masters = [bosh.modInfos.masterName]
        self.longFids = True
        #--New attrs
        self.aliases = {} #--Aliases from one mod name to another. Used by text file patchers.
        self.patchers = patchers
        self.keepIds = set()
        self.mergeIds = set()
        self.loadErrorMods = []
        self.worldOrphanMods = []
        self.unFilteredMods = []
        self.compiledAllMods = []
        self.patcher_mod_skipcount = {}
        #--Config
        self.bodyTags = 'ARGHTCCPBS' #--Default bodytags
        #--Mods
        loadMods = [name for name in bosh.modInfos.ordered if bush.fullLoadOrder[name] < bush.fullLoadOrder[PatchFile.patchName]]
        if not loadMods:
            raise BoltError(u"No active mods dated before the bashed patch")
        self.setMods(loadMods, [])
        for patcher in self.patchers:
            patcher.initPatchFile(self,loadMods)

    def setMods(self,loadMods=None,mergeMods=None):
        """Sets mod lists and sets."""
        if loadMods is not None: self.loadMods = loadMods
        if mergeMods is not None: self.mergeMods = mergeMods
        self.loadSet = set(self.loadMods)
        self.mergeSet = set(self.mergeMods)
        self.allMods = bosh.modInfos.getOrdered(self.loadSet|self.mergeSet)
        self.allSet = set(self.allMods)

    def getKeeper(self):
        """Returns a function to add fids to self.keepIds."""
        def keep(fid):
            self.keepIds.add(fid)
            return fid
        return keep

    def initData(self,progress):
        """Gives each patcher a chance to get its source data."""
        if not len(self.patchers): return
        progress = progress.setFull(len(self.patchers))
        for index,patcher in enumerate(self.patchers):
            progress(index,_(u'Preparing')+u'\n'+patcher.getName())
            patcher.initData(SubProgress(progress,index))
        progress(progress.full,_(u'Patchers prepared.'))

    def initFactories(self,progress):
        """Gets load factories."""
        progress(0,_(u"Processing."))
        def updateClasses(type_classes,newClasses):
            if not newClasses: return
            for item in newClasses:
                if not isinstance(item,basestring):
                    type_classes[item.classType] = item
                elif item not in type_classes:
                    type_classes[item] = item
        readClasses = {}
        writeClasses = {}
        updateClasses(readClasses, bush.game.readClasses)
        updateClasses(writeClasses, bush.game.writeClasses)
        for patcher in self.patchers:
            updateClasses(readClasses, (MreRecord.type_class[x] for x in patcher.getReadClasses()))
            updateClasses(writeClasses, (MreRecord.type_class[x] for x in patcher.getWriteClasses()))
        self.readFactory = LoadFactory(False,*readClasses.values())
        self.loadFactory = LoadFactory(True,*writeClasses.values())
        #--Merge Factory
        self.mergeFactory = LoadFactory(False, *bush.game.mergeClasses)

    def scanLoadMods(self,progress):
        """Scans load+merge mods."""
        if not len(self.loadMods): return
        nullProgress = Progress()
        progress = progress.setFull(len(self.allMods))
        for index,modName in enumerate(self.allMods):
            bashTags = bosh.modInfos[modName].getBashTags()
            if modName in self.loadMods and u'Filter' in bashTags:
                self.unFilteredMods.append(modName)
            try:
                loadFactory = (self.readFactory,self.mergeFactory)[modName in self.mergeSet]
                progress(index,modName.s+u'\n'+_(u'Loading...'))
                modInfo = bosh.modInfos[GPath(modName)]
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
                if 'SCPT' in modFile.tops and modName != u'Oblivion.esm':
                    gls = modFile.SCPT.getRecord(0x00025811)
                    if gls and gls.compiledSize == 4 and gls.lastIndex == 0:
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
                    self.scanModFile(modFile,nullProgress)
                for patcher in sorted(self.patchers,key=attrgetter('scanOrder')):
                    if iiMode and not patcher.iiMode: continue
                    progress(pstate,u'%s\n%s' % (modName.s,patcher.name))
                    patcher.scanModFile(modFile,nullProgress)
                # Clip max version at 1.0.  See explanation in the CBash version as to why.
                self.tes4.version = min(max(modFile.tes4.version, self.tes4.version),max(bush.game.esp.validHeaderVersions))
            except CancelError:
                raise
            except:
                print _(u"MERGE/SCAN ERROR:"),modName.s
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
        nullFid = (GPath(bosh.modInfos.masterName),0)
        for blockType,block in modFile.tops.iteritems():
            iiSkipMerge = iiMode and blockType not in ('LVLC','LVLI','LVSP')
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

    def scanModFile(self,modFile,progress):
        """Scans file and overwrites own records with modfile records."""
        #--Keep all MGEFs
        modFile.convertToLongFids('MGEF')
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
        """Completes merge process. Use this when finished using scanLoadMods."""
        if not len(self.patchers): return
        log.setHeader(u'= '+self.fileInfo.name.s+u' '+u'='*30+u'#',True)
        log(u"{{CONTENTS=1}}")
        #--Load Mods and error mods
        log.setHeader(u'= '+_(u'Overview'),True)
        log.setHeader(u'=== '+_(u'Date/Time'))
        log(u'* '+formatDate(time.time()))
        log(u'* '+_(u'Elapsed Time: ') + 'TIMEPLACEHOLDER')
        if self.patcher_mod_skipcount:
            log.setHeader(u'=== '+_(u'Skipped Imports'))
            log(_(u"The following import patchers skipped records because the imported record required a missing or non-active mod to work properly. If this was not intentional, rebuild the patch after either deactivating the imported mods listed below or activating the missing mod(s)."))
            for patcher, mod_skipcount in self.patcher_mod_skipcount.iteritems():
                log (u'* '+_(u'%s skipped %d records:') % (patcher,sum(mod_skipcount.values())))
                for mod, skipcount in mod_skipcount.iteritems():
                    log (u'  * '+_(u'The imported mod, %s, skipped %d records.') % (mod,skipcount))
        if self.unFilteredMods:
            log.setHeader(u'=== '+_(u'Unfiltered Mods'))
            log(_(u"The following mods were active when the patch was built. For the mods to work properly, you should deactivate the mods and then rebuild the patch with the mods [[http://wrye.ufrealms.net/Wrye%20Bash.html#MergeFiltering|Merged]] in."))
            for mod in self.unFilteredMods: log (u'* '+mod.s)
        if self.loadErrorMods:
            log.setHeader(u'=== '+_(u'Load Error Mods'))
            log(_(u"The following mods had load errors and were skipped while building the patch. Most likely this problem is due to a badly formatted mod. For more info, see [[http://www.uesp.net/wiki/Tes4Mod:Wrye_Bash/Bashed_Patch#Error_Messages|Bashed Patch: Error Messages]]."))
            for (mod,e) in self.loadErrorMods: log (u'* '+mod.s+u': %s'%e)
        if self.worldOrphanMods:
            log.setHeader(u'=== '+_(u'World Orphans'))
            log(_(u"The following mods had orphaned world groups, which were skipped. This is not a major problem, but you might want to use Bash's [[http://wrye.ufrealms.net/Wrye%20Bash.html#RemoveWorldOrphans|Remove World Orphans]] command to repair the mods."))
            for mod in self.worldOrphanMods: log (u'* '+mod.s)
        if self.compiledAllMods:
            log.setHeader(u'=== '+_(u'Compiled All'))
            log(_(u"The following mods have an empty compiled version of genericLoreScript. This is usually a sign that the mod author did a __compile all__ while editing scripts. This may interfere with the behavior of other mods that intentionally modify scripts from Oblivion.esm. (E.g. Cobl and Unofficial Oblivion Patch.) You can use Bash's [[http://wrye.ufrealms.net/Wrye%20Bash.html#DecompileAll|Decompile All]] command to repair the mods."))
            for mod in self.compiledAllMods: log (u'* '+mod.s)
        log.setHeader(u'=== '+_(u'Active Mods'),True)
        for name in self.allMods:
            version = bosh.modInfos.getVersion(name)
            if name in self.loadMods:
                message = u'* %02X ' % (self.loadMods.index(name),)
            else:
                message = u'* ++ '
            if version:
                message += _(u'%s  [Version %s]') % (name.s,version)
            else:
                message += name.s
            log(message)
        #--Load Mods and error mods
        if self.aliases:
            log.setHeader(u'= '+_(u'Mod Aliases'))
            for key,value in sorted(self.aliases.iteritems()):
                log(u'* %s >> %s' % (key.s,value.s))
        #--Patchers
        self.keepIds |= self.mergeIds
        subProgress = SubProgress(progress,0,0.9,len(self.patchers))
        for index,patcher in enumerate(sorted(self.patchers,key=attrgetter('editOrder'))):
            subProgress(index,_(u'Completing')+u'\n%s...' % patcher.getName())
            patcher.buildPatch(log,SubProgress(subProgress,index))
        #--Trim records
        progress(0.9,_(u'Completing')+u'\n'+_(u'Trimming records...'))
        for block in self.tops.values():
            block.keepRecords(self.keepIds)
        progress(0.95,_(u'Completing')+u'\n'+_(u'Converting fids...'))
        #--Convert masters to short fids
        self.tes4.masters = self.getMastersUsed()
        self.convertToShortFids()
        progress(1.0,_(u"Compiled."))
        #--Description
        numRecords = sum([x.getNumRecords(False) for x in self.tops.values()])
        self.tes4.description = (_(u'Updated: ')+formatDate(time.time())
                                 + u'\n\n' +
                                 _(u'Records Changed') + u': %d' % numRecords
                                 )
