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

"""This module contains the base patcher classes - must be game independent.
'A' in the names of the classes stands for 'Abstract'. You should not import
from this module outside of the patcher package."""
# FIXME: DETAILED docs - for the patcher attributes, the patcher methods and
# classes and the patching process. Once this is done we should delete the (
# unhelpful) docs from overriding methods to save some (100s) lines. We must
# also document which methods MUST be overridden by raising AbstractError. For
# instance Patcher.buildPatch() apparently is NOT always overridden
from .. import load_order
from ..bolt import dict_sort, sig_to_str
from ..exception import AbstractError
from ..mod_files import LoadFactory, ModFile

#------------------------------------------------------------------------------
# Abstract_Patcher and subclasses ---------------------------------------------
#------------------------------------------------------------------------------
class Abstract_Patcher(object):
    """Abstract base class for patcher elements - must be the penultimate class
     in MRO (method resolution order), just before object"""
    patcher_group = u'UNDEFINED'
    patcher_order = 10
    iiMode = False
    _read_sigs = () # top group signatures this patcher patches ##: type: tuple | set

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
    # Whether or not this patcher will get inactive plugins passed to its
    # scanModFile method
    ##: Once _AMerger is rewritten, this may become obsolete
    _scan_inactive = False

    @property
    def active_read_sigs(self):
        """Returns record signatures needed for reading."""
        return self._read_sigs if self.isActive else ()

    @property
    def active_write_sigs(self):
        """Returns record signatures needed for writing."""
        return self.active_read_sigs

    def initData(self,progress):
        """Compiles material, i.e. reads source text, esp's, etc. as
        necessary."""

    def scan_mod_file(self, modFile, progress):
        """Scans specified mod file to extract info. May add record to patch
        mod, but won't alter it. If adds record, should first convert it to
        long fids."""
        if not self.isActive: return # TODO(ut) raise
        if (modFile.fileInfo.ci_key not in self.patchFile.merged_or_loaded and
                not self._scan_inactive):
            return # Skip if inactive and inactives should not be scanned
        self.scanModFile(modFile, progress)

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch
        mod, but won't alter it. If adds record, should first convert it to
        long fids."""

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Should write to log."""

class ListPatcher(Patcher):
    """Subclass for patchers that have GUI lists of objects."""
    # log header to be used if the ListPatcher has mods/files source files
    srcsHeader = u'=== '+ _(u'Source Mods')

    def __init__(self, p_name, p_file, p_sources):
        """In addition to super implementation this defines the self.srcs
        ListPatcher attribute."""
        super(ListPatcher, self).__init__(p_name, p_file)
        self.srcs = p_sources
        self.isActive = bool(self.srcs)

    def _srcMods(self,log):
        """Logs the Source mods for this patcher."""
        log(self.__class__.srcsHeader)
        if not self.srcs:
            log(u'. ~~%s~~' % _(u'None'))
        else:
            for srcFile in self.srcs:
                log(u'* %s' % srcFile)

class AMultiTweaker(Abstract_Patcher):
    """Combines a number of sub-tweaks which can be individually enabled and
    configured through a choice menu."""
    patcher_group = u'Tweakers'
    patcher_order = 30
    _tweak_classes = set() # override in implementations

    def __init__(self, p_name, p_file, enabled_tweaks):
        super(AMultiTweaker, self).__init__(p_name, p_file)
        self.enabled_tweaks = enabled_tweaks
        self.isActive = bool(enabled_tweaks)

    @classmethod
    def tweak_instances(cls):
        # Sort alphabetically first for aesthetic reasons
        tweak_classes = sorted(cls._tweak_classes, key=lambda c: c.tweak_name)
        # After that, sort to make tweaks instantiate & run in the right order
        tweak_classes.sort(key=lambda c: c.tweak_order)
        return [t() for t in tweak_classes]

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
    # Setting a label to '----' will not add a new choice. Instead, a separator
    # will be added at that point in the dropdown.
    # If only one choice is available, no dropdown will be shown - the tweak
    # can only be toggled on and off.
    #
    # An example:
    # tweak_choices = [(_(u'One Day', 24), (_(u'Two Days'), 48)]
    #
    # This will show two options to the user. When retrieving a value via
    # self.choiceValues[self.chosen][0], the selected value (24 or 48) will be
    # returned, which the tweak could use to e.g. change a record attribute
    # controlling how long a quest is delayed.
    tweak_choices = []
    # The choice label (see tweak_choices above) that should be selected by
    # default.
    default_choice = None
    # If set to a string, adds a new choice to the end of the tweak_choices
    # list with that label and the default choice's value (see default_choice)
    # that will open a dialog allowing the user to pick a custom value when
    # clicked.
    custom_choice = None
    # The header to log before logging anything else about this tweak.
    # If set to None, defaults to this tweak's name. Automatically gets wtxt
    # formatting prepended.
    tweak_log_header = None
    # The message to log directly after the header (see above), listing the
    # total number of changes made by the tweak. Receives a named formatting
    # argument, total_changed, which contains the total number of changed
    # records. Automatically gets wtxt formatting prepended.
    tweak_log_msg = u'OVERRIDE'
    # A sorting key which the tweaker that this tweak belongs to uses to
    # determine the order in which to run tweaks. A lower number means that the
    # tweak will run sooner, a higher number means later.
    tweak_order = 10
    # If True, this tweak will be checked by default
    default_enabled = False
    # If True, tweak_key will be shown in the 'custom value' popup
    show_key_for_custom = False

    def __init__(self):
        # Don't check tweak_log_msg, settings tweaks don't use it
        for tweak_attr in (u'tweak_name', u'tweak_tip', u'tweak_key',
                           u'tweak_log_msg'):
            if getattr(self, tweak_attr) == u'OVERRIDE':
                self._raise_tweak_syntax_error(u"A '%s' attribute is still "
                                               u'set to the default '
                                               u"('OVERRIDE')" % tweak_attr)
        # TODO: docs for attributes below! - done for static ones above
        self.choiceLabels = []
        self.choiceValues = []
        self.default = None
        # Caught some copy-paste mistakes where I forgot to make a it list,
        # left it in for that reason
        if not isinstance(self.tweak_choices, list):
            self._raise_tweak_syntax_error(u'tweak_choices must be a list of '
                                           u'tuples')
        for choice_index, choice_tuple in enumerate(self.tweak_choices):
            # See comments above for the syntax definition
            choice_label, choice_items = choice_tuple[0], choice_tuple[1:]
            if choice_label == self.default_choice:
                choice_label = u'[%s]' % choice_label
                self.default = choice_index
            self.choiceLabels.append(choice_label)
            self.choiceValues.append(choice_items)
        if self.default is None:
            if self.default_choice is not None:
                self._raise_tweak_syntax_error(u'default_choice is not in '
                                               u'tweak_choices')
            self.default = 0 # no explicit default item, so default to first
        # Create the custom choice if a label was specified for it
        if self.custom_choice is not None:
            # Add a separator right before the custom choice
            self.choiceLabels.append(u'----')
            self.choiceValues.append(u'----')
            self.choiceLabels.append(self.custom_choice)
            self.choiceValues.append(self.choiceValues[self.default])
        #--Config
        self.isEnabled = False
        self.chosen = 0
        #--Log
        if self.tweak_log_header is None:
            self.tweak_log_header = self.tweak_name # default to tweak name

    def tweak_log(self, log, count):
        """Logs the total changes and details for each plugin."""
        log.setHeader(u'=== ' + self.tweak_log_header)
        log(u'* ' + self.tweak_log_msg % {
            u'total_changed': sum(count.values())})
        for src_plugin in load_order.get_ordered(count):
            log(u'  * %s: %d' % (src_plugin, count[src_plugin]))

    def init_tweak_config(self, configs):
        """Get config from configs dictionary and/or set to default."""
        self.isEnabled, self.chosen = self.default_enabled, 0
        self._isNew = self.tweak_key not in configs
        if not self._isNew:
            self.isEnabled,value = configs[self.tweak_key]
            if value in self.choiceValues:
                self.chosen = self.choiceValues.index(value)
            else:
                if self.custom_choice is not None:
                    self.chosen = len(self.choiceLabels) - 1 # always last
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
        err_msg += u'\n Class: %s.%s' % (self.__class__.__module__,
                                         self.__class__.__name__)
        raise SyntaxError(err_msg)

    def isNew(self):
        """returns whether this tweak is new (i.e. whether the value was not
        loaded from a saved config"""
        return getattr(self, '_isNew', False)

    def getListLabel(self):
        """Returns label to be used in list"""
        tweakname = self.tweak_name
        if len(self.choiceLabels) > 1:
            tweakname += u' [' + self.choiceLabels[self.chosen] + u']'
        return tweakname

    def validate_values(self, chosen_values):
        """Gives this tweak a chance to check if the specified values (given
        as a tuple, as if they were retrieved via
        self.choiceValues[self.chosen][0]) are valid for this tweak. Return a
        string if the values are invalid. It will then be shown as an error
        message to the user. Return None if the values are valid, the values
        will then be accepted and the tweak will be activated."""
        return None

    def wants_record(self, record):
        """Return a truthy value if you want to get a chance to change the
        specified record. Must be implemented by every PBash tweak that
        supports pooling (see MultiTweakItem.supports_pooling)."""
        raise AbstractError(u'wants_record not implemented')

    def tweak_record(self, record):
        """This is where each tweak gets a chance to change the specified
        record, which is a copy of the winning override inside the BP. It is
        guaranteed that wants_record has been called and returned True right
        before this call. Note that there is no taking that back: right after
        this call, keep() will be called and the record will be kept as an
        override in the BP. So make sure wants_record *never* lets ITMs and
        ITPOs through! Must be implemented by every PBash tweak that supports
        pooling (see MultiTweakItem.supports_pooling)."""
        raise AbstractError(u'tweak_record not implemented')

class ModLoader(Patcher):
    """Mixin for patchers loading mods"""
    loadFactory = None

    def _patcher_read_fact(self, by_sig=None): # read can have keepAll=False
        return LoadFactory(keepAll=False, by_sig=by_sig or self._read_sigs)

    def _mod_file_read(self, modInfo):
        modFile = ModFile(modInfo,
                          self.loadFactory or self._patcher_read_fact())
        modFile.load(True)
        return modFile

# Patchers: 20 ----------------------------------------------------------------
class ImportPatcher(ListPatcher, ModLoader):
    """Subclass for patchers in group Importer."""
    patcher_group = u'Importers'
    patcher_order = 20
    # Override in subclasses as needed
    logMsg = u'\n=== ' + _(u'Modified Records')

    def _patchLog(self,log,type_count):
        log.setHeader(u'= %s' % self._patcher_name)
        self._srcMods(log)
        self._plog(log,type_count)

    ##: Unify these - decide which one looks best in the end and make all
    # patchers use that one
    def _plog(self,log,type_count):
        """Most common logging pattern - override as needed."""
        log(self.__class__.logMsg)
        for top_grup_sig, count in dict_sort(type_count):
            if count: log(u'* ' + _(u'Modified %(type)s Records: %(count)d')
                % {u'type': sig_to_str(top_grup_sig), u'count': count})

    def _plog1(self,log,mod_count): # common logging variation
        log(self.__class__.logMsg % sum(mod_count.values()))
        for mod in load_order.get_ordered(mod_count):
            log(u'* %s: %3d' % (mod, mod_count[mod]))
