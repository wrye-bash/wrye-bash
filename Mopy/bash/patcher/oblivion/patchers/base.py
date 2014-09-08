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

"""This module contains oblivion base patcher classes.""" # TODO:DOCS
import bash
from bash.patcher.base import AMultiTweakItem, AMultiTweaker, Patcher, \
    CBash_Patcher, ADoublePatcher, AAliasesPatcher, AListPatcher
from bash.bosh import PatchFile, getPatchesList, CBash_PatchFile, reModExt

class MultiTweakItem(AMultiTweakItem):
    # Notice the differences from Patcher in scanModFile and buildPatch
    # would it make any sense to make getRead/WriteClasses() into classmethods
    # see comments in Patcher
    # TODO: scanModFile() have VERY similar code - use getReadClasses here ?
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ()  # raise AbstractError ? NO: see NamesTweak_BodyTags

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ()

    def scanModFile(self,modFile,progress,patchFile): # extra param: patchFile
        """Scans specified mod file to extract info. May add record to patch
        mod, but won't alter it. If adds record, should first convert it to
        long fids."""
        pass

    def buildPatch(self,log,progress,patchFile): # extra param: patchFile
        """Edits patch file as desired. Should write to log."""
        pass  # TODO raise AbstractError ?

    def _patchLog(self, log, count):
        #--Log - must define self.logMsg in subclasses
        log.setHeader(self.logHeader)
        log(self.logMsg % sum(count.values()))
        for srcMod in bash.bosh.modInfos.getOrdered(count.keys()):
            log(u'  * %s: %d' % (srcMod.s, count[srcMod]))

class CBash_MultiTweakItem(AMultiTweakItem):
    # extra CBash_MultiTweakItem class variables
    iiMode = False
    scanRequiresChecked = False
    applyRequiresChecked = False
    # the default scan and edit orders - override as needed
    scanOrder = 32
    editOrder = 32

    def __init__(self,label,tip,key,*choices,**kwargs):
        super(CBash_MultiTweakItem, self).__init__(label, tip, key, *choices,
                                                   **kwargs)
        self.mod_count = {} # extra CBash_MultiTweakItem instance variable

    #--Patch Phase ------------------------------------------------------------
    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return []

    # def apply(self,modFile,record): # TODO bashTags argument is unused in
    # all subclasses

    def buildPatchLog(self,log):
        """Will write to log."""
        #--Log
        mod_count = self.mod_count
        log.setHeader(self.logHeader)
        log(self.logMsg % sum(mod_count.values()))
        for srcMod in bash.bosh.modInfos.getOrdered(mod_count.keys()):
            log(u'  * %s: %d' % (srcMod.s,mod_count[srcMod]))
        self.mod_count = {}

class MultiTweaker(AMultiTweaker,Patcher):

    def buildPatch(self,log,progress):
        """Applies individual tweaks."""
        if not self.isActive: return
        log.setHeader(u'= '+self.__class__.name,True)
        for tweak in self.enabledTweaks:
            tweak.buildPatch(log,progress,self.patchFile)

class CBash_MultiTweaker(AMultiTweaker,CBash_Patcher):
    #--Config Phase -----------------------------------------------------------
    def initData(self,group_patchers,progress):
        """Compiles material, i.e. reads source text, esp's, etc. as necessary."""
        if not self.isActive: return
        for tweak in self.enabledTweaks:
            for type_ in tweak.getTypes():
                group_patchers.setdefault(type_,[]).append(tweak)

    #--Patch Phase ------------------------------------------------------------
    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        log.setHeader(u'= '+self.__class__.name,True)
        for tweak in self.enabledTweaks:
            tweak.buildPatchLog(log)

class ListPatcher(AListPatcher,Patcher):

    def _patchesList(self):
        return bash.bosh.dirs['patches'].list()

    def _patchFile(self):
        return PatchFile

class CBash_ListPatcher(AListPatcher,CBash_Patcher):
    unloadedText = u'\n\n'+_(u'Any non-active, non-merged mods in the'
                             u' following list will be IGNORED.')

    #--Config Phase -----------------------------------------------------------
    def _patchesList(self):
        return getPatchesList()

    def _patchFile(self):
        return CBash_PatchFile

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(CBash_ListPatcher, self).initPatchFile(patchFile,loadMods)
        self.srcs = self.getConfigChecked()
        self.isActive = bool(self.srcs)

    def getConfigChecked(self):
        """Returns checked config items in list order."""
        if self.allowUnloaded:
            return [item for item in self.configItems if
                    self.configChecks[item]]
        else:
            return [item for item in self.configItems if
                    self.configChecks[item] and (
                        item in self.patchFile.allMods or not reModExt.match(
                            item.s))]

class DoublePatcher(ADoublePatcher, ListPatcher): pass

class CBash_DoublePatcher(ADoublePatcher, CBash_ListPatcher): pass

# Patchers: 10 ----------------------------------------------------------------
class AliasesPatcher(AAliasesPatcher,Patcher): pass

class CBash_AliasesPatcher(AAliasesPatcher,CBash_Patcher):
    #--Config Phase -----------------------------------------------------------
    def getConfig(self,configs):
        """Get config from configs dictionary and/or set to default."""
        super(CBash_AliasesPatcher,self).getConfig(configs)
        self.srcs = [] #so as not to fail screaming when determining load
        # mods - but with the least processing required.
