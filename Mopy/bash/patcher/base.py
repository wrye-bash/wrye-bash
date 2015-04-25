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

"""This module contains the base patcher classes - must be game independent.
'A' in the names of the classes stands for 'Abstract'. You should not import
from this module outside of the patcher package."""
# FIXME: DETAILED docs - for the patcher attributes, the patcher methods and
# classes and the patching process. Once this is done we should delete the (
# unhelpful) docs from overriding methods to save some (100s) lines. We must
# also document which methods MUST be overridden by raising AbstractError. For
# instance Patcher.buildPatch() apparently is NOT always overridden

import copy
import re
from ..bolt import AbstractError, GPath, Path
from ..bosh import reModExt, dirs, reCsvExt # should I not import dirs here ?
from .. import bush # for fullLoadOrder - needed ?
from .. import bosh # for modInfos

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
    defaultConfig = {'isEnabled':False}
    iiMode = False
    selectCommands = True

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

    def getConfig(self,configs):
        """Get config from configs dictionary and/or set to default."""
        config = configs.setdefault(self.__class__.__name__,{})
        for attr,default in self.__class__.defaultConfig.iteritems():
            value = copy.deepcopy(config.get(attr,default))
            setattr(self,attr,value)

    def saveConfig(self,configs):
        """Save config to configs dictionary."""
        config = configs[self.__class__.__name__] = {}
        for attr in self.__class__.defaultConfig:
            config[attr] = copy.deepcopy(getattr(self,attr))

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called
        after this."""
        self.patchFile = patchFile

class Patcher(_Abstract_Patcher):
    """Abstract base class for patcher elements performing a PBash patch - must
    be just before Abstract_Patcher in MRO.""" ##: "performing" ? how ?
    # would make any sense to make getRead/WriteClasses() into classmethods
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
            loadMods = set([mod for mod in self.srcs if reModExt.search(
                mod.s) and mod not in self.patchFile.allMods])
            self.patchFile.scanSet |= loadMods

    def buildPatchLog(self,log):
        """Write to log."""
        pass

class AListPatcher(_Abstract_Patcher):
    """Subclass for patchers that have GUI lists of objects."""
    #--Get/Save Config
    choiceMenu = None #--List of possible choices for each config item. Item
    #  0 is default.
    defaultConfig = {'isEnabled':False,'autoIsChecked':True,'configItems':[],
                     'configChecks':{},'configChoices':{}}
    canAutoItemCheck = True #--GUI: Whether new items are checked by default
    forceItemCheck = False #--Force configChecked to True for all items
    autoRe = re.compile(u'^UNDEFINED$',re.U)#--Compiled re used by getAutoItems
    # all subclasses override this with re.compile(ur"^UNDEFINED$",re.I|re.U)
    # except DoublePatcher and UpdateReference ones
    autoKey = None
    forceAuto = True
    # log header to be used if the ListPatcher has mods/files source files
    srcsHeader = u'=== '+ _(u'Source Mods')

    def initPatchFile(self, patchFile, loadMods):
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

    #--Config Phase -----------------------------------------------------------
    def getAutoItems(self):
        """Returns list of items to be used for automatic configuration."""
        autoItems = []
        autoRe = self.__class__.autoRe
        autoKey = self.__class__.autoKey
        if isinstance(autoKey,basestring):
            autoKey = {autoKey}
        autoKey = set(autoKey)
        self.choiceMenu = self.__class__.choiceMenu
        for modInfo in bosh.modInfos.data.values():
            if autoRe.match(modInfo.name.s) or (
                autoKey & modInfo.getBashTags()):
                if bush.fullLoadOrder[modInfo.name] > \
                    bush.fullLoadOrder[self._patchFile().patchName]: continue
                autoItems.append(modInfo.name)
                if self.choiceMenu: self.getChoice(modInfo.name)
        reFile = re.compile(u'_('+(u'|'.join(autoKey))+ur')\.csv$',re.U)
        for fileName in sorted(set(dirs['patches'].list()) | set(
                dirs['defaultPatches'].list())):
            if reFile.search(fileName.s):
                autoItems.append(fileName)
        return autoItems

    def getConfig(self,configs):
        """Get config from configs dictionary and/or set to default."""
        super(AListPatcher,self).getConfig(configs)
        if self.forceAuto:
            self.autoIsChecked = True
        #--Verify file existence
        newConfigItems = []
        patchesDir = self._patchesList()
        for srcPath in self.configItems:
            if ((reModExt.search(srcPath.s) and srcPath in bosh.modInfos) or
                        reCsvExt.search(srcPath.s) and srcPath in patchesDir):
                newConfigItems.append(srcPath)
        self.configItems = newConfigItems
        if self.__class__.forceItemCheck:
            for item in self.configItems:
                self.configChecks[item] = True
        #--Make sure configChoices are set (if choiceMenu exists).
        if self.choiceMenu:
            for item in self.configItems:
                self.getChoice(item)
        #--AutoItems?
        if self.autoIsChecked:
            self.getAutoItems()

    def _patchesList(self): raise AbstractError # TODO(ut) why different overrides ?

    def _patchFile(self): raise AbstractError

    def getChoice(self,item):
        """Get default config choice."""
        return self.configChoices.setdefault(item,self.choiceMenu[0])

    def getItemLabel(self,item):
        """Returns label for item to be used in list"""
        if isinstance(item,Path): item = item.s
        if self.choiceMenu:
            return u'%s [%s]' % (item,self.getChoice(item))
        else:
            return item

    def sortConfig(self,items):
        """Return sorted items. Default assumes mods and sorts by load
        order."""
        return bosh.modInfos.getOrdered(items,False)

    def saveConfig(self,configs):
        """Save config to configs dictionary."""
        #--Toss outdated configCheck data.
        listSet = set(self.configItems)
        self.configChecks = dict(
            [(key,value) for key,value in self.configChecks.iteritems() if
             key in listSet])
        self.configChoices = dict(
            [(key,value) for key,value in self.configChoices.iteritems() if
             key in listSet])
        super(AListPatcher,self).saveConfig(configs)

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

    #--Config Phase -----------------------------------------------------------
    def getConfig(self,configs):
        """Get config from configs dictionary and/or set to default."""
        config = configs.setdefault(self.__class__.__name__,
                                    self.__class__.defaultConfig)
        self.isEnabled = config.get('isEnabled',False)
        self.tweaks = copy.deepcopy(self.__class__.tweaks)
        for tweak in self.tweaks:
            tweak.getConfig(config)

    def saveConfig(self,configs):
        """Save config to configs dictionary."""
        config = configs[self.__class__.__name__] = {}
        config['isEnabled'] = self.isEnabled
        for tweak in self.tweaks:
            tweak.saveConfig(config)
        self.enabledTweaks = [tweak for tweak in self.tweaks if
                              tweak.isEnabled]
        self.isActive = len(self.enabledTweaks) > 0

class AAliasesPatcher(_Abstract_Patcher):
    """Specify mod aliases for patch files."""
    scanOrder = 10
    editOrder = 10
    group = _(u'General')
    name = _(u"Alias Mod Names")
    text = _(u"Specify mod aliases for reading CSV source files.")
    tip = None
    defaultConfig = {'isEnabled':False,'aliases':{}}

    #--Config Phase -----------------------------------------------------------
    def getConfig(self,configs):
        """Get config from configs dictionary and/or set to default."""
        super(AAliasesPatcher, self).getConfig(configs)
        #--Update old configs to use Paths instead of strings.
        self.aliases = dict(
            map(GPath, item) for item in self.aliases.iteritems())

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
    def __init__(self,label,tip,key,*choices,**kwargs):
        # TODO: docs for attributes !
        self.label = label
        self.tip = tip
        self.key = key
        self.choiceLabels = []
        self.choiceValues = []
        self.default = 0
        for choice in choices:
            self.choiceLabels.append(choice[0])
            if choice[0][0] == u'[':
                self.default = choices.index(choice)
            self.choiceValues.append(choice[1:])
        #--Config
        self.isEnabled = False
        self.defaultEnabled = kwargs.get('defaultEnabled', False)
        self.chosen = 0
        #--Log
        self.logHeader = u'=== '+ label

    #--Config Phase -----------------------------------------------------------
    # Methods present in _Abstract_Patcher too
    def getConfig(self,configs):
        """Get config from configs dictionary and/or set to default."""
        self.isEnabled,self.chosen = self.defaultEnabled,0
        if self.key in configs:
            self._isNew = False
            self.isEnabled,value = configs[self.key]
            if value in self.choiceValues:
                self.chosen = self.choiceValues.index(value)
            else:
                for label in self.choiceLabels:
                    if label.startswith(_(u'Custom')):
                        self.chosen = self.choiceLabels.index(label)
                        self.choiceValues[self.chosen] = value
        else:
            self._isNew = True
            if self.default:
                self.chosen = self.default

    def saveConfig(self,configs):
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
class ADoublePatcher(AListPatcher):

    def getConfig(self,configs):
        """Get config from configs dictionary and/or set to default."""
        super(ADoublePatcher, self).getConfig(configs)
        self.tweaks = copy.deepcopy(self.__class__.tweaks)
        config = configs.setdefault(self.__class__.__name__,self.__class__.defaultConfig)
        for tweak in self.tweaks:
            tweak.getConfig(config)

    def saveConfig(self,configs):
        """Save config to configs dictionary."""
        #--Toss outdated configCheck data.
        super(ADoublePatcher, self).saveConfig(configs)
        config = configs[self.__class__.__name__]
        for tweak in self.tweaks:
            tweak.saveConfig(config)
        self.enabledTweaks = [tweak for tweak in self.tweaks if tweak.isEnabled]

class AImportPatcher(AListPatcher):
    """Subclass for patchers in group Importer."""
    group = _(u'Importers')
    scanOrder = 20
    editOrder = 20
    masters = {}
    autoRe = re.compile(ur"^UNDEFINED$",re.I|re.U) # overridden by
    # NamesPatcher, NpcFacePatcher, and not used by ImportInventory,
    # ImportRelations, ImportFactions

    def saveConfig(self,configs):
        """Save config to configs dictionary."""
        super(AImportPatcher, self).saveConfig(configs)
        if self.isEnabled:
            importedMods = [item for item,value in
                            self.configChecks.iteritems() if
                            value and reModExt.search(item.s)]
            configs['ImportedMods'].update(importedMods)

class APatchMerger(AListPatcher):
    """Merges specified patches into Bashed Patch."""
    scanOrder = 10
    editOrder = 10
    group = _(u'General')
    name = _(u'Merge Patches')
    text = _(u"Merge patch mods into Bashed Patch.")
    autoRe = re.compile(ur"^UNDEFINED$",re.I|re.U)

    def getAutoItems(self):
        """Returns list of items to be used for automatic configuration."""
        autoItems = []
        for modInfo in bosh.modInfos.data.values():
            if modInfo.name in bosh.modInfos.mergeable and u'NoMerge' not in \
                    modInfo.getBashTags() and \
                            bush.fullLoadOrder[modInfo.name] < \
                            bush.fullLoadOrder[self._patchFile().patchName]:
                autoItems.append(modInfo.name)
        return autoItems

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(APatchMerger,self).initPatchFile(patchFile,loadMods)
        #--WARNING: Since other patchers may rely on the following update
        # during their initPatchFile section, it's important that PatchMerger
        # runs first or near first.
        self._setMods(patchFile)

    def _setMods(self, patchFile): raise AbstractError # override in subclasses

class AUpdateReferences(AListPatcher):
    """Imports Form Id replacers into the Bashed Patch."""
    scanOrder = 15
    editOrder = 15
    group = _(u'General')
    name = _(u'Replace Form IDs')
    text = _(u"Imports Form Id replacers from csv files into the Bashed Patch.")
    canAutoItemCheck = False #--GUI: Whether new items are checked by default.
