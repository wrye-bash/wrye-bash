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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2015 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This module contains the base patcher classes - must be game independent.
'A' in the names of the classes stands for 'Abstract'. You should not import
from this module outside of the patcher package."""
# FIXME: DETAILED docs - for the patcher attributes, the patcher methods and
# classes and the patching process. Once this is done we should delete the (
# unhelpful) docs from overriding methods to save some (100s) lines. We must
# also document which methods MUST be overridden by raising AbstractError. For
# instance Patcher.buildPatch() apparently is NOT always overridden

from . import getPatchesList
from .. import load_order, bass, bolt

#------------------------------------------------------------------------------
# _Abstract_Patcher and subclasses---------------------------------------------
#------------------------------------------------------------------------------
class _Abstract_Patcher(object):
    """Abstract base class for patcher elements - must be the penultimate class
     in MRO (method resolution order), just before object"""
    scanOrder = 10
    editOrder = 10
    group = u'UNDEFINED'
    name = u'UNDEFINED'
    text = u"UNDEFINED."
    tip = None
    iiMode = False

    def getName(self):
        """Returns patcher name."""
        return self.__class__.name

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        """Initialization of common values to defaults."""
        self.patchFile = None
        self.scanOrder = self.__class__.scanOrder
        self.editOrder = self.__class__.editOrder
        self.isActive = True
        #--Gui stuff
        self.isEnabled = False #--Patcher is enabled.
        self.gConfigPanel = None
        # super(Abstract_Patcher, self).__init__()#UNNEEDED (ALWAYS BEFORE obj)

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called
        after this. Base implementation sets the patchFile to the actively
        executing patch - be sure to call super."""
        self.patchFile = patchFile

class Patcher(_Abstract_Patcher):
    """Abstract base class for patcher elements performing a PBash patch - must
    be just before Abstract_Patcher in MRO.""" ##: "performing" ? how ?
    # would it make any sense to make getRead/WriteClasses() into classmethods
    # and just define an attribute in the classes - so getReadClasses(cls):
    # return cls.READ and have in subclasses just READ = 'AMMO' (say)

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ()

    def initData(self,progress):
        """Compiles material, i.e. reads source text, esp's, etc. as
        necessary."""

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch
        mod, but won't alter it. If adds record, should first convert it to
        long fids."""

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Should write to log."""

class CBash_Patcher(_Abstract_Patcher):
    """Abstract base class for patcher elements performing a CBash patch - must
    be just before Abstract_Patcher in MRO.""" ##: "performing" ? how ?
    # would it make any sense to make getTypes into classmethod ?
    unloadedText = u""
    allowUnloaded = True
    scanRequiresChecked = False
    applyRequiresChecked = False

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(CBash_Patcher, self).__init__()
        if not self.allowUnloaded:
            self.text += self.unloadedText

    #--Patch Phase ------------------------------------------------------------
    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return []

    def initData(self,group_patchers,progress):
        """Compiles material, i.e. reads source text, esp's, etc. as
        necessary."""
        if not self.isActive: return
        for type_ in self.getTypes():
            group_patchers.setdefault(type_,[]).append(self)
        if self.allowUnloaded:
            loadMods = set([mod for mod in self.srcs if bass.reModExt.search(
                mod.s) and mod not in self.patchFile.allMods])
            self.patchFile.scanSet |= loadMods

    def buildPatchLog(self,log):
        """Write to log."""
        pass

class AListPatcher(_Abstract_Patcher):
    """Subclass for patchers that have GUI lists of objects.

    :type _patches_set: set[bolt.Path]"""
    #--Get/Save Config
    autoKey = None
    # log header to be used if the ListPatcher has mods/files source files
    srcsHeader = u'=== '+ _(u'Source Mods')
    _patches_set = None

    @staticmethod
    def list_patches_dir(): AListPatcher._patches_set = getPatchesList()

    @property
    def patches_set(self): # ONLY use in patchers config phase or initData
        if self._patches_set is None: self.list_patches_dir()
        return self._patches_set

    def initPatchFile(self, patchFile, loadMods):
        """Prepare to handle specified patch mod. All functions are called
        after this. In addition to super implemenation this defines the
        self.srcs AListPatcher attribute."""
        super(AListPatcher, self).initPatchFile(patchFile, loadMods)
        self.srcs = self.getConfigChecked()
        self.isActive = bool(self.srcs)

    def _srcMods(self,log):
        """Logs the Source mods for this patcher - patcher must have `srcs`
        attribute otherwise an AttributeError will be raised."""
        log(self.__class__.srcsHeader)
        if not self.srcs:
            log(u". ~~%s~~" % _(u'None'))
        else:
            for srcFile in self.srcs:
                log(u"* " +srcFile.s)

    #--Patch Phase ------------------------------------------------------------
    def getConfigChecked(self):
        """Returns checked config items in list order."""
        return [item for item in self.configItems if self.configChecks[item]]

class AMultiTweaker(_Abstract_Patcher):
    """Combines a number of sub-tweaks which can be individually enabled and
    configured through a choice menu."""
    group = _(u'Tweakers')
    scanOrder = 20
    editOrder = 20

class AAliasesPatcher(_Abstract_Patcher):
    """Specify mod aliases for patch files."""
    scanOrder = 10
    editOrder = 10
    group = _(u'General')
    name = _(u"Alias Mod Names")
    text = _(u"Specify mod aliases for reading CSV source files.")
    tip = None

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called
        after this."""
        super(AAliasesPatcher, self).initPatchFile(patchFile,loadMods)
        if self.isEnabled:
            self.patchFile.aliases = self.aliases

#------------------------------------------------------------------------------
# AMultiTweakItem(object)------------------------------------------------------
#------------------------------------------------------------------------------
class AMultiTweakItem(object):
    """A tweak item, optionally with configuration choices."""
    tweak_read_classes = ()

    def __init__(self,label,tip,key,*choices,**kwargs):
        # TODO: docs for attributes !
        self.label = label
        self.tip = tip
        self.key = key
        self.choiceLabels = []
        self.choiceValues = []
        self.default = 0
        for choice_tuple in choices: # (choice_label, choice1, choice2, ...)
            self.choiceLabels.append(choice_tuple[0])
            if choice_tuple[0][0] == u'[':
                self.default = choices.index(choice_tuple)
            self.choiceValues.append(choice_tuple[1:])
        #--Config
        self.isEnabled = False
        self.defaultEnabled = kwargs.get('defaultEnabled', False)
        self.chosen = 0
        #--Log
        self.logHeader = u'=== '+ label

    def _patchLog(self, log, count):
        """Log - must define self.logMsg in subclasses"""
        log.setHeader(self.logHeader)
        log(self.logMsg % sum(count.values()))
        for srcMod in load_order.get_ordered(count.keys()):
            log(u'  * %s: %d' % (srcMod.s, count[srcMod]))

    #--Config Phase -----------------------------------------------------------
    # Methods present in _Abstract_Patcher too
    def get_tweak_config(self, configs):
        """Get config from configs dictionary and/or set to default."""
        self.isEnabled,self.chosen = self.defaultEnabled,0
        self._isNew = not (self.key in configs)
        if not self._isNew:
            self.isEnabled,value = configs[self.key]
            if value in self.choiceValues:
                self.chosen = self.choiceValues.index(value)
            else:
                for label in self.choiceLabels:
                    if label.startswith(_(u'Custom')):
                        self.chosen = self.choiceLabels.index(label)
                        self.choiceValues[self.chosen] = value
        else:
            if self.default:
                self.chosen = self.default

    def save_tweak_config(self, configs):
        """Save config to configs dictionary."""
        if self.choiceValues: value = self.choiceValues[self.chosen]
        else: value = None
        configs[self.key] = self.isEnabled,value

    # Methods particular to AMultiTweakItem
    def isNew(self):
        """returns whether this tweak is new (i.e. whether the value was not
        loaded from a saved config"""
        return getattr(self, "_isNew", False)

    def getListLabel(self):
        """Returns label to be used in list"""
        label = self.label
        if len(self.choiceLabels) > 1:
            label += u' [' + self.choiceLabels[self.chosen] + u']'
        return label

#------------------------------------------------------------------------------
# AListPatcher subclasses------------------------------------------------------
#------------------------------------------------------------------------------
class AImportPatcher(AListPatcher):
    """Subclass for patchers in group Importer."""
    group = _(u'Importers')
    scanOrder = 20
    editOrder = 20
    masters = {}

class APatchMerger(AListPatcher):
    """Merges specified patches into Bashed Patch."""
    scanOrder = 10
    editOrder = 10
    group = _(u'General')
    name = _(u'Merge Patches')
    text = _(u"Merge patch mods into Bashed Patch.")
    autoKey = {u'Merge'}

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(APatchMerger,self).initPatchFile(patchFile,loadMods)
        #--WARNING: Since other patchers may rely on the following update
        # during their initPatchFile section, it's important that PatchMerger
        # runs first or near first.
        if not self.isActive: return
        if self.isEnabled: #--Since other mods may rely on this
            patchFile.setMods(None, self.srcs) # self.srcs set in initPatchFile

class AUpdateReferences(AListPatcher):
    """Imports Form Id replacers into the Bashed Patch."""
    scanOrder = 15
    editOrder = 15
    group = _(u'General')
    name = _(u'Replace Form IDs')
    text = _(u"Imports Form Id replacers from csv files into the Bashed Patch.")
    autoKey = {u'Formids'}
