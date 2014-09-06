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
    CBash_Patcher, ADoublePatcher, AAliasesPatcher
from bash.bosh import ListPatcher, CBash_ListPatcher

class MultiTweakItem(AMultiTweakItem): pass # TODO: should it inherit from
#  Patcher ? Should I define the  getWriteClasses, getReadClasses here ?
# TODO: scanModFile() have VERY similar code - use getReadClasses here ?

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

class DoublePatcher(ADoublePatcher, ListPatcher): pass

class CBash_DoublePatcher(ADoublePatcher, CBash_ListPatcher): pass

class AliasesPatcher(AAliasesPatcher,Patcher): pass

class CBash_AliasesPatcher(AAliasesPatcher,CBash_Patcher):
    #--Config Phase -----------------------------------------------------------
    def getConfig(self,configs):
        """Get config from configs dictionary and/or set to default."""
        super(CBash_AliasesPatcher,self).getConfig(configs)
        self.srcs = [] #so as not to fail screaming when determining load
        # mods - but with the least processing required.
