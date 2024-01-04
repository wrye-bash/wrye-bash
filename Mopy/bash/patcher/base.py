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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
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
# instance APatcher.buildPatch() apparently is NOT always overridden
from __future__ import annotations

from collections.abc import Iterable
from itertools import chain

from .. import load_order, bass
from ..bolt import deprint, dict_sort, sig_to_str
from ..exception import BPConfigError
from ..parsers import _HandleAliases

#------------------------------------------------------------------------------
# APatcher and subclasses -----------------------------------------------------
#------------------------------------------------------------------------------
class APatcher:
    """Abstract base class for patcher elements - must be the penultimate class
    in MRO (method resolution order), just before object."""
    patcher_group = 'UNDEFINED'
    patcher_order = 10
    iiMode = False
    _read_sigs: Iterable[bytes] = () #top group signatures this patcher patches
    # Whether this patcher will get inactive plugins passed to its scanModFile
    ##: Once _AMerger is rewritten, this may become obsolete
    _scan_inactive = False

    def __init__(self, p_name, p_file):
        """Initialization of common values to defaults."""
        self.isActive = True
        self.patchFile = p_file
        self._patcher_name = p_name

    def getName(self):
        """Return patcher name passed in by the gui, needed for logs."""
        return self._patcher_name

    @property
    def active_read_sigs(self):
        """Returns record signatures needed for reading."""
        return self._read_sigs if self.isActive else ()

    @property
    def active_write_sigs(self):
        """Returns record signatures needed for writing."""
        return self.active_read_sigs

    def initData(self,progress):
        """Compiles material, i.e. reads esp's, etc. as necessary."""

    def scan_mod_file(self, modFile, progress):
        """Scans specified mod file to extract info. May add record to patch
        mod, but won't alter it. If adds record, should first convert it to
        long fids."""
        if not self.isActive: return # TODO(ut) raise
        if (modFile.fileInfo.fn_key not in self.patchFile.merged_or_loaded and
                not self._scan_inactive):
            return # Skip if inactive and inactives should not be scanned
        self.scanModFile(modFile, progress)

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch
        mod, but won't alter it."""

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Should write to log."""

class ListPatcher(APatcher):
    """Subclass for patchers that have GUI lists of objects."""
    # log header to be used if the ListPatcher has mods/files source files
    srcsHeader = '=== ' + _('Source Mods')
    # a CsvParser type to parse the csv sources of this patcher
    _csv_parser = None
    patcher_tags = set()
    # CSV files for this patcher have to end with _{this value}.csv
    _csv_key = None ##: todo this belongs to the parsers would deduplicate mod_links wildcards also

    def __init__(self, p_name, p_file, p_sources):
        """In addition to super implementation this defines the self.srcs
        ListPatcher attribute."""
        super(ListPatcher, self).__init__(p_name, p_file)
        self.isActive = self._process_sources(p_sources, p_file)

    @classmethod
    def get_sources(cls, p_file, p_sources=None, raise_on_error=False):
        """Get a list of plugin/csv sources for this patcher. If p_sources are
        passed in filter/validate them."""
        if p_sources is None: # getting the sources
            p_sources = [*p_file.all_plugins]
            if cls._csv_key:
                p_sources.extend(sorted(p_file.patches_set))
        return [src_fn for src_fn in p_sources if
                cls._validate_src(p_file, src_fn, raise_on_error)]

    @classmethod
    def _validate_src(cls, p_file, src_fn, raise_on_error):
        try:
            return cls._validate_mod(p_file, src_fn, raise_on_error)
        except KeyError:
            if src_fn[-4:] == '.csv':
                if cls._csv_key:
                    if src_fn not in p_file.patches_set:
                        err = f'{cls.__name__}: {src_fn} is not present'
                    elif src_fn.endswith(f'_{cls._csv_key}.csv'):
                        return True
                    else:
                        err = f'{cls.__name__}: invalid csv type {src_fn}'
                else:
                    err = f'{cls.__name__}: csv src passed in: {src_fn}'
            else:
                err = f'{cls.__name__}: {src_fn} is not loading before the ' \
                      f'BP or is not a mod'
        if raise_on_error:
            raise BPConfigError(err)
        return False

    @classmethod
    def _validate_mod(cls, p_file, src_fn, raise_on_error):
        """Return True if the src_fn plugin should be part of the sources
        for this patcher."""
        # Must have an appropriate tag and no missing masters or a Filter tag
        if src_fn in p_file.inactive_mm: ##fixme or active_mm
            err = f'{cls.__name__}: {src_fn} is inactive'
        elif not (cls.patcher_tags & p_file.all_tags[src_fn]):
            err = f'{cls.__name__}: {src_fn} is not tagged with supported ' \
                  f'tags {cls.patcher_tags}'
        else:
            return True
        if raise_on_error:
            raise BPConfigError(err)
        return False

    def _process_sources(self, p_sources, p_file):
        """Validate srcs and update p_file read factories."""
        self.get_sources(p_file, p_sources, raise_on_error=True)
        self.csv_srcs = [s for s in p_sources if s.fn_ext == '.csv']
        self.srcs = [s for s in p_sources if s.fn_ext != '.csv']
        self._update_patcher_factories(p_file)
        self._parse_csv_sources()
        return bool(self.srcs or self.csv_srcs)

    def _update_patcher_factories(self, p_file):
        # run before _parse_csv_sources as the latter updates srcs_sigs for
        # APreserver - we want _read_sigs to return rec_type_attrs here
        p_file.update_read_factories(self._read_sigs, self.srcs)

    def _log_srcs(self, log):
        """Logs the Source mods/csvs for this patcher."""
        log(self.__class__.srcsHeader)
        all_srcs = [*self.srcs, *self.csv_srcs]
        if not all_srcs:
            log(f'. ~~{_("None")}~~')
        else:
            for srcFile in all_srcs:
                log(f'* {srcFile}')

    # CSV helpers
    def _parse_csv_sources(self):
        """Parses CSV files. Only called if _parser_instance returns a
        parser."""
        if not (parser_instance := self._parser_instance):
            return {}
        loaded_csvs = []
        for src_path in self.csv_srcs:
            try:
                try: ##: the correct path must be passed from gui_patchers.py
                    csv_path = bass.dirs['patches'].join(src_path)
                    parser_instance.read_csv(csv_path)
                except OSError:
                    csv_path = bass.dirs['defaultPatches'].join(src_path)
                    parser_instance.read_csv(csv_path)
                loaded_csvs.append(src_path)
            except OSError:
                deprint(f'{src_path} is no longer in patches set',
                        traceback=True)
            except UnicodeError:
                deprint(f'{src_path} is not saved in UTF-8 format',
                        traceback=True)
        self.csv_srcs = loaded_csvs
        filtered_dict = self._filter_csv_fids(parser_instance, loaded_csvs)
        return filtered_dict

    def _filter_csv_fids(self, parser_instance, loaded_csvs):
        # Filter out any entries that don't actually have data or whose
        # record signatures do not appear in _parser_sigs - these might not
        # always be a subset of read_sigs for instance CoblExhaustionPatcher
        # which reads b'FACT' but _read_sigs is b'SPEL'
        rec_att = {*parser_instance._parser_sigs}
        sig_data = parser_instance.id_stored_data
        if s := (sig_data.keys() - rec_att):
            deprint(f'{self.getName()}: {s} unhandled signatures loaded from '
                    f'{loaded_csvs}')
        ##: make sure k is always bytes and drop encode below
        earlier_loading = self.patchFile.all_plugins
        filtered_dict = {k.encode('ascii') if isinstance(k, str) else k: v for
            k, d in sig_data.items() if (k in rec_att) and (v := {f: j for
                f, j in d.items() if f.mod_fn in earlier_loading})}
        return filtered_dict

    @property
    def _parser_instance(self):
        return self._csv_parser and self._csv_parser(
            self.patchFile.pfile_aliases, called_from_patcher=True)

class CsvListPatcher(_HandleAliases, ListPatcher):
    """List patcher that is-a CsvParser - we could change this to has-a,
    would retire this class."""

    @property
    def _parser_instance(self):
        return self

#------------------------------------------------------------------------------
# MultiTweakItem --------------------------------------------------------------
#------------------------------------------------------------------------------
class MultiTweakItem:
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
    tweak_choices = [] ##: Replace with a dict now that we're on py3?
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

    def __init__(self, bashed_patch):
        # Don't check tweak_log_msg, settings tweaks don't use it
        for tweak_attr in (u'tweak_name', u'tweak_tip', u'tweak_key',
                           u'tweak_log_msg'):
            if getattr(self, tweak_attr) == u'OVERRIDE':
                self._raise_tweak_syntax_error(f"A '{tweak_attr}' attribute "
                    f"is still set to the default ('OVERRIDE')")
        # TODO: docs for attributes below! - done for static ones above
        self.choiceLabels = []
        self.choiceValues = []
        self.default = None
        # Caught some copy-paste mistakes where I forgot to make it a list,
        # left it in for that reason
        if not isinstance(self.tweak_choices, list):
            self._raise_tweak_syntax_error(u'tweak_choices must be a list of '
                                           u'tuples')
        for choice_index, choice_tuple in enumerate(self.tweak_choices):
            # See comments above for the syntax definition
            choice_label, choice_items = choice_tuple[0], choice_tuple[1:]
            if choice_label == self.default_choice:
                choice_label = f'[{choice_label}]'
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
        self._tweak_make_log_header(log)
        log('* ' + self.tweak_log_msg % {'total_changed': sum(count.values())})
        for src_plugin in load_order.get_ordered(count):
            log(f'  * {src_plugin}: {count[src_plugin]}')

    def _tweak_make_log_header(self, log):
        """Sets the header - override if you only need to add something to the
        header."""
        log.setHeader('=== ' + self.tweak_log_header)

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

    # Methods particular to MultiTweakItem
    def _raise_tweak_syntax_error(self, err_msg):
        """Small helper method to aid in validation. Raises a SyntaxError with
        the specified error message and some information that should make
        identifying the offending tweak much easier appended."""
        err_msg += u'\nOffending tweak:'
        # To distinguish dynamic tweaks, which have the same class
        err_msg += f"\n Name: '{self.tweak_name}'"
        # To identify problems with e.g. duplicate custom values immediately
        err_msg += f'\n Choices: {self.tweak_choices}'
        err_msg += (f'\n Class: {self.__class__.__module__}.'
                    f'{self.__class__.__name__}')
        raise SyntaxError(err_msg)

    def isNew(self):
        """returns whether this tweak is new (i.e. whether the value was not
        loaded from a saved config"""
        return getattr(self, '_isNew', False)

    def getListLabel(self):
        """Returns label to be used in list"""
        tweakname = self.tweak_name
        if len(self.choiceLabels) > 1:
            tweakname += f' [{self.choiceLabels[self.chosen]}]'
        return tweakname

    def validate_values(self, chosen_values: tuple) -> str | None:
        """Gives this tweak a chance to check if the specified values (given
        as a tuple, as if they were retrieved via
        self.choiceValues[self.chosen][0]) are valid for this tweak. Return a
        string if the values are invalid. It will then be shown as an error
        message to the user. Return None if the values are valid, the values
        will then be accepted and the tweak will be activated."""
        return None

    def validation_error_header(self, error_values: tuple) -> str:
        """Gives this tweak a chacne to customize the error header that will be
        shown to the user if validate_values returns a non-None result."""
        t_val = (', '.join(map(str, error_values)) if len(error_values) > 1
                 else error_values[0])
        return (_("The values you entered (%(t_val)s) are not valid for the "
                  "'%(t_name)s' tweak.") % {'t_val': t_val,
                                            't_name': self.tweak_name}
                 if len(error_values) > 1 else
                _("The value you entered (%(t_val)s) is not valid for the "
                  "'%(t_name)s' tweak.") % {'t_val': t_val,
                                            't_name': self.tweak_name})

    # Tweaking API ------------------------------------------------------------
    def wants_record(self, record):
        """Return a truthy value if you want to get a chance to change the
        specified record."""
        raise NotImplementedError

    def prepare_for_tweaking(self, patch_file):
        """Gives this tweak a chance to prepare for the phase where it gets
        its tweak_record calls using the specified patch file instance. At this
        point, all relevant files have been scanned, wanted records have been
        forwarded into the BP, MGEFs have been indexed, etc. Default
        implementation does nothing."""

    def tweak_record(self, record):
        """This is where each tweak gets a chance to change the specified
        record, which is a copy of the winning override inside the BP. It is
        guaranteed that wants_record has been called and returned True right
        before this call. Note that there is no taking that back: right after
        this call, keep() will be called and the record will be kept as an
        override in the BP. So make sure wants_record *never* lets ITMs and
        ITPOs through!"""
        raise NotImplementedError

    def finish_tweaking(self, patch_file):
        """Gives this tweak a chance to clean up and do any work after the
        tweak_records phase is over using the specified patch file instance. At
        this point, all tweak_record calls for all tweaks belonging to the
        parent 'tweaker' have been executed. Default implementation does
        nothing."""

class ScanPatcher(APatcher):
    """WIP class to encapsulate scanModFile common logic."""
    # filter records that exist in corresponding patch block
    _filter_in_patch = False

    @property
    def _keep_ids(self):
        return None

    def scanModFile(self, modFile, progress, scan_sigs=None):
        """Add records from modFile."""
        if keep_ids := self._keep_ids is not None:
            if not (keep_ids := self._keep_ids): return # won't add to patch
        for top_sig, block in modFile.iter_tops(scan_sigs or self._read_sigs):
            # do not create the patch block till needed
            patchBlock = self.patchFile.tops.get(top_sig)
            rid_rec = block.iter_present_records()
            if self._filter_in_patch and patchBlock:
                rid_rec = ((rid, rec) for rid, rec in rid_rec if
                           rid not in patchBlock.id_records)
            if keep_ids:
                rid_rec = ((rid, rec) for rid, rec in rid_rec if
                           rid in keep_ids)
            try:
                rid_rec = [(rid, rec) for rid, rec in rid_rec if
                           self._add_to_patch(rid, rec, top_sig)]
            except NotImplementedError:
                pass
            for rid, rec in rid_rec:
                try:
                    patchBlock.setRecord(rec)
                except AttributeError:
                    patchBlock = self.patchFile.tops[top_sig]
                    patchBlock.setRecord(rec)

    def _add_to_patch(self, rid, record, top_sig):
        """Decide if this record should be added to the patch top_sig block.
        Records that have been copied into the BP once will automatically
        be updated by update_patch_records_from_mod/mergeModFile so skip if
        we've already copied this record or if we're not interested in it."""
        raise NotImplementedError

# Patchers: 20 ----------------------------------------------------------------
class ImportPatcher(ListPatcher, ScanPatcher):
    """Subclass for patchers in group Importer."""
    patcher_group = u'Importers'
    patcher_order = 20
    # Override in subclasses as needed
    logMsg = u'\n=== ' + _(u'Modified Records')

    def _update_patcher_factories(self, p_file):
        # most of the import patchers scan their sources' masters
        mast = (p_file.all_plugins[s].masterNames for s in self.srcs)
        sources = set(chain(self.srcs, *mast))
        p_file.update_read_factories(self._read_sigs, sources)

    def _patchLog(self,log,type_count):
        log.setHeader(f'= {self._patcher_name}')
        self._log_srcs(log)
        self._plog(log,type_count)

    ##: Unify these - decide which one looks best in the end and make all
    # patchers use that one
    def _plog(self,log,type_count):
        """Most common logging pattern - override as needed."""
        log(self.__class__.logMsg)
        for top_grup_sig, count in dict_sort(type_count):
            if count:
                log('* ' + _('Modified %(tg_type)s Records: %(rec_cnt)d') % {
                    'tg_type': sig_to_str(top_grup_sig), 'rec_cnt': count})

    def _plog1(self,log,mod_count): # common logging variation
        log(self.__class__.logMsg % sum(mod_count.values()))
        for mod in load_order.get_ordered(mod_count):
            log(f'* {mod}: {mod_count[mod]:3d}')
