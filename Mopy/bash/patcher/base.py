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

"""This module contains the base patcher classes - must be game independent."""
import copy
import re
import bash.bolt
from bash.bolt import AbstractError, GPath
from bash.bosh import reModExt, dirs, reCsvExt
import bash.bush
# from cint import _ # added by PyCharm, and again

class _Abstract_Patcher(object):
    """Abstract base class for patcher elements - must be the penultimate class
     in MRO, just before object"""
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

    def initData(self,progress):
        """Compiles material, i.e. reads source text, esp's, etc. as
        necessary."""
        pass  # TODO raise AbstractError ?

class Patcher(_Abstract_Patcher):
    """Abstract base class for patcher elements performing a PBash patch - must
    be just before Abstract_Patcher in MRO.""" # TODO : clarify "performing" ?
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ()  # TODO raise AbstractError ?

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ()  # TODO raise AbstractError ?

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch
        mod, but won't alter it. If adds record, should first convert it to
        long fids."""
        pass  # TODO raise AbstractError ?

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Should write to log."""
        pass  # TODO raise AbstractError ?

class CBash_Patcher(_Abstract_Patcher):
    """Abstract base class for patcher elements performing a CBash patch - must
    be just before Abstract_Patcher in MRO.""" # TODO : clarify "performing" ?
    unloadedText = u""
    allowUnloaded = True
    scanRequiresChecked = False
    applyRequiresChecked = False

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(CBash_Patcher, self).__init__()
        if not self.allowUnloaded:
            self.text = self.text + self.unloadedText

    #--Patch Phase ------------------------------------------------------------
    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return []  # TODO raise AbstractError ?

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
        pass  # TODO raise AbstractError ?

class AListPatcher(_Abstract_Patcher):
    """Subclass for patchers that have GUI lists of objects.""" # TODO: docs
    #--Get/Save Config
    choiceMenu = None #--List of possible choices for each config item. Item
    #  0 is default.
    defaultConfig = {'isEnabled':False,'autoIsChecked':True,'configItems':[],
                     'configChecks':{},'configChoices':{}}
    canAutoItemCheck = True #--GUI: Whether new items are checked by default
    forceItemCheck = False #--Force configChecked to True for all items
    autoRe = re.compile(u'^UNDEFINED$',re.U)#--Compiled re used by getAutoItems
    autoKey = None
    forceAuto = True

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
        for modInfo in bash.bosh.modInfos.data.values():
            if autoRe.match(modInfo.name.s) or (
                autoKey & modInfo.getBashTags()):
                if bash.bush.fullLoadOrder[modInfo.name] > \
                        bash.bush.fullLoadOrder[
                            self._patchFile().patchName]: continue
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
            if ((reModExt.search(
                    srcPath.s) and srcPath in bash.bosh.modInfos) or
                        reCsvExt.search(
                    srcPath.s) and srcPath in patchesDir):
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

    def _patchesList(self): raise AbstractError # TODO needed? check subclasses

    def _patchFile(self): raise AbstractError

    def getChoice(self,item):
        """Get default config choice."""
        return self.configChoices.setdefault(item,self.choiceMenu[0])

    def getItemLabel(self,item):
        """Returns label for item to be used in list"""
        if isinstance(item,bash.bolt.Path): item = item.s
        if self.choiceMenu:
            return u'%s [%s]' % (item,self.getChoice(item))
        else:
            return item

    def sortConfig(self,items):
        """Return sorted items. Default assumes mods and sorts by load
        order."""
        return bash.bosh.modInfos.getOrdered(items,False)

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

class AMultiTweakItem(object):
    """A tweak item, optionally with configuration choices."""
    def __init__(self,label,tip,key,*choices,**kwargs):
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

    def saveConfig(self,configs):
        """Save config to configs dictionary."""
        if self.choiceValues: value = self.choiceValues[self.chosen]
        else: value = None
        configs[self.key] = self.isEnabled,value

    def _patchLog(self,log,count):
        #--Log - must define self.logMsg in subclasses - TODO: move up ? down ?
        log.setHeader(self.logHeader)
        log(self.logMsg % sum(count.values()))
        for srcMod in bash.bosh.modInfos.getOrdered(count.keys()):
            log(u'  * %s: %d' % (srcMod.s,count[srcMod]))
