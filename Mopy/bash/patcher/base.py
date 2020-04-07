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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
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
from .. import load_order, bolt
from ..exception import AbstractError

#------------------------------------------------------------------------------
# Abstract_Patcher and subclasses ---------------------------------------------
#------------------------------------------------------------------------------
class Abstract_Patcher(object):
    """Abstract base class for patcher elements - must be the penultimate class
     in MRO (method resolution order), just before object"""
    scanOrder = 10
    editOrder = 10
    group = u'UNDEFINED'
    iiMode = False
    # TODO naming (_patcher_top_sigs ?) and unify getTypes/read/writeClasses
    _read_write_records = () # top group signatures this patcher patches

    def getName(self):
        """Return patcher name passed in by the gui, needed for logs."""
        return self._patcher_name

    def __init__(self, p_name, p_file):
        """Initialization of common values to defaults."""
        self.isActive = True
        self.patchFile = p_file
        self._patcher_name = p_name

class Patcher(Abstract_Patcher):
    """Abstract base class for patcher elements performing a PBash patch - must
    be just before Abstract_Patcher in MRO.""" ##: "performing" ? how ?

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return self.__class__._read_write_records if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return self.__class__._read_write_records if self.isActive else ()

    def initData(self,progress):
        """Compiles material, i.e. reads source text, esp's, etc. as
        necessary."""

    def scan_mod_file(self, modFile, progress):
        """Scans specified mod file to extract info. May add record to patch
        mod, but won't alter it. If adds record, should first convert it to
        long fids."""
        if not self.isActive: return # TODO(ut) raise
        self.scanModFile(modFile, progress)

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch
        mod, but won't alter it. If adds record, should first convert it to
        long fids."""

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Should write to log."""

class CBash_Patcher(Abstract_Patcher):
    """Abstract base class for patcher elements performing a CBash patch - must
    be just before Abstract_Patcher in MRO.""" ##: "performing" ? how ?
    allowUnloaded = True # if True patcher needs a srcs attribute
    scanRequiresChecked = False # if True patcher needs a srcs attribute
    applyRequiresChecked = False # if True patcher needs a srcs attribute

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return list(self.__class__._read_write_records) if self.isActive else []

    def initData(self, progress):
        """Compiles material, i.e. reads source text, esp's, etc. as
        necessary."""
        if not self.isActive: return
        for top_group_sig in self.getTypes():
            self.patchFile.group_patchers[top_group_sig].append(self)
        if self.allowUnloaded:
            loadMods = set([mod for mod in self.srcs if
                            self.patchFile.p_file_minfos.rightFileType(
                                mod) and mod not in self.patchFile.allMods])
            self.patchFile.scanSet |= loadMods

    def buildPatchLog(self,log):
        """Write to log."""
        pass

class AListPatcher(Abstract_Patcher):
    """Subclass for patchers that have GUI lists of objects."""
    # log header to be used if the ListPatcher has mods/files source files
    srcsHeader = u'=== '+ _(u'Source Mods')

    def __init__(self, p_name, p_file, p_sources):
        """In addition to super implementation this defines the self.srcs
        AListPatcher attribute."""
        super(AListPatcher, self).__init__(p_name, p_file)
        self.srcs = p_sources
        self.isActive = bool(self.srcs)

    def _srcMods(self,log):
        """Logs the Source mods for this patcher."""
        log(self.__class__.srcsHeader)
        if not self.srcs:
            log(u". ~~%s~~" % _(u'None'))
        else:
            for srcFile in self.srcs:
                log(u"* " +srcFile.s)

class AMultiTweaker(Abstract_Patcher):
    """Combines a number of sub-tweaks which can be individually enabled and
    configured through a choice menu."""
    group = _(u'Tweakers')
    scanOrder = 20
    editOrder = 20

    def __init__(self, p_name, p_file, enabled_tweaks):
        super(AMultiTweaker, self).__init__(p_name, p_file)
        self.enabled_tweaks = enabled_tweaks
        self.isActive = bool(enabled_tweaks)

    @classmethod
    def tweak_instances(cls):
        return sorted([cls() for cls in cls._tweak_classes],
                      key=lambda a: a.tweak_name.lower())


class AAliasesPatcher(Abstract_Patcher):
    """Specify mod aliases for patch files."""
    scanOrder = 10
    editOrder = 10
    group = _(u'General')

#------------------------------------------------------------------------------
# AMultiTweakItem(object) -----------------------------------------------------
#------------------------------------------------------------------------------
class AMultiTweakItem(object):
    """A tweak item, optionally with configuration choices. See tweak_
    attribute comments below for information on how to specify names, tooltips,
    dropdown choices, etc."""
    # The signatures of the record types this tweak wants to edit. Must be
    # bytestrings.
    tweak_read_classes = ()
    # The name of the tweak, shown in the GUI
    tweak_name = u'OVERRIDE'
    # The tooltip to show when hovering over the tweak in the GUI
    tweak_tip = u'OVERRIDE'
    # A string used to persist whether this tweak was enabled and which of
    # the tweak's options the user chose in the settings files. Must be unique
    # per tweaker, but prefer completely unique strings. Changing this for an
    # already released tweak will of course reset it for every user.
    tweak_key = u'OVERRIDE'
    # The choices to show to the user. A list of tuples, where each tuple
    # specifies a single item to show the user in a dropdown. The first item in
    # the tuple is the label to show in the GUI, while all subsequent items
    # are the values to apply, available at runtime via
    # self.choiceValues[self.chosen]. It is up to each tweak to decide for
    # itself how to best lay these out.
    #
    # If a label starts with '[' and ends with ']', it is treated as the
    # default option.
    # If a label starts with 'Custom' (or the translated equivalent of it), it
    # is treated as a custom choice. This choice will allow the user to choose
    # any value they wish.
    # Setting a label to '----' will not add a new choice. Instead, a separator
    # will be added at that point in the dropdown.
    # If only one choice is available, no dropdown will be shown - the tweak
    # can only be toggled on and off.
    #
    # An example:
    # tweak_choices = [(_(u'One Day', 24), (_(u'[Two Days]'), 48)]
    #
    # This will show two options to the user, with the 'Two Days' option as the
    # default one. When retrieving a value via self.choiceValues[self.chosen],
    # either 24 or 48 will be returned, which the tweak could use to e.g.
    # change a record attribute controlling how long a quest is delayed.
    tweak_choices = []

    def __init__(self, defaultEnabled=False):
        # TODO: docs for attributes below! - done for static ones above
        self.choiceLabels = []
        self.choiceValues = []
        self.default = None
        has_custom = False
        # Caught some copy-paste mistakes where I forgot to make a it list,
        # left it in for that reason
        if not isinstance(self.tweak_choices, list):
            self._raise_tweak_syntax_error(u'tweak_choices must be a list of '
                                           u'tuples')
        for choice_index, choice_tuple in enumerate(self.tweak_choices):
            # See comments above for the syntax definition
            choice_label, choice_items = choice_tuple[0], choice_tuple[1:]
            # Validate that we have at most one custom value
            if choice_label.startswith(_(u'Custom')):
                if has_custom:
                    self._raise_tweak_syntax_error(u'At most one custom '
                                                   u'choice may be specified')
                has_custom = True
            self.choiceLabels.append(choice_label)
            self.choiceValues.append(choice_items)
            if choice_label.startswith(u'[') and choice_label.endswith(u']'):
                # This is the default item, check for duplicates and mark it
                if self.default is not None:
                    self._raise_tweak_syntax_error(u'Tweaks may only have one '
                                                   u'default item')
                self.default = choice_index
        if self.default is None:
            self.default = 0 # no explicit default item, so default to first
        #--Config
        self.isEnabled = False
        self.defaultEnabled = defaultEnabled
        self.chosen = 0
        #--Log
        self.logHeader = u'=== '+ self.tweak_name

    def _patchLog(self, log, count):
        """Log - must define self.logMsg in subclasses"""
        log.setHeader(self.logHeader)
        log(self.logMsg % sum(count.values()))
        for srcMod in load_order.get_ordered(count.keys()):
            log(u'  * %s: %d' % (srcMod.s, count[srcMod]))

    def init_tweak_config(self, configs):
        """Get config from configs dictionary and/or set to default."""
        self.isEnabled,self.chosen = self.defaultEnabled,0
        self._isNew = not (self.tweak_key in configs)
        if not self._isNew:
            self.isEnabled,value = configs[self.tweak_key]
            if value in self.choiceValues:
                self.chosen = self.choiceValues.index(value)
            else:
                for choice_label in self.choiceLabels:
                    if choice_label.startswith(_(u'Custom')):
                        self.chosen = self.choiceLabels.index(choice_label)
                        self.choiceValues[self.chosen] = value
        else:
            if self.default:
                self.chosen = self.default

    def save_tweak_config(self, configs):
        """Save config to configs dictionary."""
        if self.choiceValues: value = self.choiceValues[self.chosen]
        else: value = None
        configs[self.tweak_key] = self.isEnabled,value

    # Methods particular to AMultiTweakItem
    def _raise_tweak_syntax_error(self, err_msg):
        """Small helper method to aid in validation. Raises a SyntaxError with
        the specified error message and some information that should make
        identifying the offending tweak much easier appended."""
        err_msg += u'\nOffending tweak:'
        # To distinguish dynamic tweaks, which have the same class
        err_msg += u"\n Name: '%s'" % self.tweak_name
        # To identify problems with e.g. duplicate custom values immediately
        err_msg += u'\n Choices: %s' % self.tweak_choices
        # To distinguish between a PBash and CBash-specific problem
        err_msg += u'\n Class: %s.%s' % (self.__class__.__module__,
                                         self.__class__.__name__)
        raise SyntaxError(err_msg)

    def isNew(self):
        """returns whether this tweak is new (i.e. whether the value was not
        loaded from a saved config"""
        return getattr(self, "_isNew", False)

    def getListLabel(self):
        """Returns label to be used in list"""
        tweakname = self.tweak_name
        if len(self.choiceLabels) > 1:
            tweakname += u' [' + self.choiceLabels[self.chosen] + u']'
        return tweakname

    def wants_record(self, record):
        """Return a truthy value if you want to get a chance to change the
        specified record. Must be implemented by every PBash tweak that
        supports pooling (see MultiTweakItem.supports_pooling)."""
        raise AbstractError(u'wants_record not implemented')

class DynamicTweak(AMultiTweakItem):
    """A tweak that has its name, tip, key and choices passed in as init
    parameters."""
    def __init__(self, tweak_name, tweak_tip, tweak_key, *tweak_choices,
                 **kwargs):
        self.tweak_name = tweak_name
        self.tweak_tip = tweak_tip
        self.tweak_key = tweak_key
        self.tweak_choices = list(tweak_choices)
        super(DynamicTweak, self).__init__(**kwargs)

    def __repr__(self):  return u'%s(%s)' % (
        self.__class__.__name__, self.tweak_name)

#------------------------------------------------------------------------------
# AListPatcher subclasses -----------------------------------------------------
#------------------------------------------------------------------------------
class AImportPatcher(AListPatcher):
    """Subclass for patchers in group Importer."""
    group = _(u'Importers')
    scanOrder = 20
    editOrder = 20

class APatchMerger(AListPatcher):
    """Merges specified patches into Bashed Patch."""
    scanOrder = 10
    editOrder = 10
    group = _(u'General')

    def __init__(self, p_name, p_file, p_sources):
        super(APatchMerger, self).__init__(p_name, p_file, p_sources)
        if not self.isActive: return
        #--WARNING: Since other patchers may rely on the following update
        # during their __init__, it's important that PatchMerger runs first
        p_file.set_mergeable_mods(self.srcs)

class AUpdateReferences(AListPatcher):
    """Imports Form Id replacers into the Bashed Patch."""
    scanOrder = 15
    editOrder = 15
    group = _(u'General')
