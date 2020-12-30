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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""Parsers can read and write information from and to mods and from and to CSV
files. They store the read information in an internal representation, which
means that they can be used to export and import information from and to mods.
They are also used by some of the patchers in order to not duplicate the work
that has to be done when reading mods.
However, not all parsers fit this pattern - some have to read mods twice,
others barely even fit into the pattern at all (e.g. FidReplacer)."""

from __future__ import division, print_function

import csv
import re
from collections import defaultdict, Counter, OrderedDict
from itertools import izip, chain
from operator import attrgetter, itemgetter

# Internal
from . import bush, load_order
from .balt import Progress
from .bass import dirs, inisettings
from .bolt import GPath, decoder, deprint, csvFormat, setattr_deep, \
    attrgetter_cache, str_or_none, int_or_none, nonzero_or_none, \
    structs_cache, float_or_none, int_or_zero
from .brec import MreRecord, MelObject, genFid, RecHeader, null4
from .exception import AbstractError
from .mod_files import ModFile, LoadFactory

# Utils ##: absorb in CsvParser
def _str_to_bool(value, __falsy=frozenset(
    [u'', u'none', u'false', u'no', u'0', u'0.0'])):
    return value.strip().lower() not in __falsy

class _CsvReader(object):
    """For reading csv files. Handles comma, semicolon and tab separated (excel) formats.
       CSV files must be encoded in UTF-8"""
    @staticmethod
    def utf_8_encoder(unicode_csv_data):
        for line in unicode_csv_data:
            yield line.encode(u'utf8')

    def __init__(self,path): ##: Py3 Revisit - is Csv reader still bytes?  get rid of BOM?
        self.ins = GPath(path).open(u'r', encoding=u'utf-8-sig')
        first_line = self.ins.readline()
        excel_fmt = b'excel-tab' if u'\t' in first_line else b'excel'
        self.ins.seek(0)
        if excel_fmt == b'excel':
            # TypeError: "delimiter" must be string, not unicode
            delimiter = b';' if b';' in first_line else b','
            self.reader = csv.reader(_CsvReader.utf_8_encoder(self.ins),
                                     excel_fmt, delimiter=delimiter)
        else:
            self.reader = csv.reader(_CsvReader.utf_8_encoder(self.ins),
                                     excel_fmt)

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_value, exc_traceback): self.ins.close()

    def __iter__(self):
        for row in self.reader:
            yield [unicode(x, u'utf8') for x in row]

    def close(self):
        self.reader = None
        self.ins.close()

#------------------------------------------------------------------------------
def _key_sort(di, id_eid_=None, keys_dex=(), values_dex=(), by_value=False):
    """Adapted to current uses"""
    if id_eid_ is not None: # we passed id_eid in sort by eid
        key_f=lambda k: id_eid_.get(k, u'unknown').lower()
        for k in sorted(di, key=key_f):
            yield k, di[k], id_eid_[k]
    else:
        if keys_dex or values_dex: # TODO(ut): drop below when keys are CIStr
            key_f = lambda k: tuple((u'%s' % k[x]).lower() for x in keys_dex
                        ) + tuple(di[k][x].lower() for x in values_dex)
        elif by_value:
            key_f = lambda k: di[k].lower()
        else:
            key_f = None # default
        for k in sorted(di, key=key_f):
            yield k, di[k]

class CsvParser(object):
    """Basic read/write csv functionality - ScriptText handles script files
    not csvs though."""
    _csv_header = ()
    _row_fmt_str = u''

    def readFromText(self, csv_path):
        """Reads information from the specified CSV file and stores the result
        in id_stored_data. You must override _parse_line for this method to
        work. ScriptText is a special case.

        :param csv_path: The path to the CSV file that should be read."""
        with _CsvReader(csv_path) as ins:
            for fields in ins:
                try:
                    self._parse_line(fields)
                except (IndexError, ValueError, TypeError):
                    """TypeError/ValueError trying to unpack None/few values"""

    def _parse_line(self, csv_fields):
        """Parse the specified CSV line and update the parser's instance
        id_stored_data - both id and stored_data vary in type and meaning.

        :param csv_fields: A line in a CSV file, already split into fields."""
        raise AbstractError(u'%s must implement _parse_line' % type(self))

    def write_text_file(self, textPath):
        """Export ____ to specified text file. You must override _write_rows.
        """
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            self._header_row(out)
            self._write_rows(out)

    def _write_rows(self, out):
        raise AbstractError(u'%s must implement _write_rows' % type(self))

    def _header_row(self, out):
        out.write(u'"%s"\n' % u'","'.join(self._csv_header))

class _HandleAliases(CsvParser):##: Py3 move to bolt after absorbing _CsvReader
    """WIP aliases handling."""
    _parser_sigs = [] # record signatures this parser recognises

    def __init__(self, aliases_, called_from_patcher=False):
        # Automatically set in _parse_csv_sources to the patch file's aliases -
        # used if the Aliases Patcher has been enabled
        self.aliases = aliases_ or {} # type: dict
        # Set to True when called by a patcher - can be used to alter stored
        # data format when reading from a csv - could be in a subclass
        self._called_from_patcher = called_from_patcher

    def _coerce_fid(self, modname, hex_fid):
        """Create a long formid from a unicode modname and a unicode
        hexadecimal - it will blow with ValueError if hex_fid is not
        in the form 0x123abc abd check for aliases of modname."""
        if not hex_fid.startswith(u'0x'): raise ValueError # exit _parse_line
        # get alias for modname returned from _CsvReader
        modname = GPath(modname)
        return GPath(self.aliases.get(modname, modname)), int(hex_fid, 0)

    def _load_plugin(self, mod_info, keepAll=True, target_types=None):
        """Loads the specified record types in the specified ModInfo and
        returns the result.

        :param mod_info: The ModInfo object to read.
        :param target_types: An iterable yielding record signatures to load.
        :return: An object representing the loaded plugin."""
        mod_file = ModFile(mod_info, self._load_factory(keepAll, target_types))
        mod_file.load(do_unpack=True)
        return mod_file

    def _load_factory(self, keepAll=True, target_types=None):
        return LoadFactory(keepAll, by_sig=target_types or self._parser_sigs)

    def readFromMod(self, modInfo):
        """Hasty readFromMod implementation."""
        modFile = self._load_plugin(modInfo, keepAll=False)
        for top_grup_sig in self._parser_sigs:
            typeBlock = modFile.tops.get(top_grup_sig)
            if not typeBlock: continue
            id_data = self.id_stored_data[top_grup_sig]
            for record in typeBlock.getActiveRecords():
                self._read_record(record, id_data)

    def _read_record(self, record, id_data):
        raise AbstractError

# TODO(inf) Once refactoring is done, we could easily take in Progress objects
#  for more accurate progress bars when importing/exporting
class _AParser(_HandleAliases):
    """The base class from which all parsers inherit, implements reading and
    writing mods using PBash calls. You will of course still have to
    implement _read_record_fp et al., depending on the passes and behavior
    you want.

    Reading from mods:
     - This is the most complex part of this design - we offer up to two
       passes, where the first pass reads a mod and all its masters, but does
       not offer fine-grained filtering of the read information. It is mapped
       by long FormID and stored in id_context. You will have to set
       _fp_types appropriately and override _read_record_fp to use this pass.
     - The second pass filters by record type and long FormID, and can choose
       whether or not it wants to store certain information. The result is
       stored in id_stored_data. You will have to set _sp_types appropriately
       and override _is_record_useful and _read_record_sp to use this pass.
     - If you want to skip either pass, just leave _fp_types / _sp_types
       empty."""

    def __init__(self, aliases_=None, called_from_patcher=False):
        # The types of records to read from in the first pass. These should be
        # strings matching the record types, *not* classes.
        self._fp_types = ()
        # Internal variable, keeps track of mods we've already processed during
        # the first pass to avoid repeating work
        self._fp_mods = set()
        # The name of the mod that is currently being loaded. Some parsers need
        # this to change their behavior when loading a mod file. This is a
        # unicode string matching the name of the mod being loaded, or None if
        # no mod is being loaded.
        self._current_mod = None
        # True if id_context needs another round of processing during the
        # second pass
        self._context_needs_followup = False
        # Do we need to sort the masters during the first pass according to
        # current LO?
        self._needs_fp_master_sort = False
        # Maps long fids to context info read during first pass
        self.id_context = {}
        # The types of records to read from in the second pass. These should be
        # strings matching the record types, *not* classes.
        self._sp_types = ()
        # Maps record types to dicts that map long fids to stored information
        # May have been retrieved from mod in second pass, or from a CSV file
        self.id_stored_data = defaultdict(lambda : defaultdict(dict))
        super(_AParser, self).__init__(aliases_, called_from_patcher)

    # Plugin-related utilities
    def _mod_has_tag(self, tag_name):
        """Returns True if the current mod has a Bash Tag with the specified
        name."""
        from . import bosh
        return self._current_mod and tag_name in bosh.modInfos[
            self._current_mod].getBashTags()

    # Reading from plugin - first pass
    def _read_plugin_fp(self, loaded_mod):
        """Performs a first pass of reading on the specified plugin and its
        masters. Results are stored in id_context.

        :param loaded_mod: The loaded mod to read from."""
        from . import bosh
        def _fp_loop(mod_to_read):
            """Central loop of _read_plugin_fp, factored out into a method so
            that it can easily be used twice."""
            for block_type in self._fp_types:
                rec_block = mod_to_read.tops.get(block_type, None)
                if not rec_block: continue
                for record in rec_block.getActiveRecords():
                    self.id_context[record.fid] = \
                        self._read_record_fp(record)
            self._fp_mods.add(mod_to_read.fileInfo.ci_key)
        # Process the mod's masters first, but see if we need to sort them
        master_names = loaded_mod.tes4.masters
        if self._needs_fp_master_sort:
            master_names = load_order.get_ordered(master_names)
        for mod_name in master_names:
            if mod_name in self._fp_mods: continue
            _fp_loop(self._load_plugin(bosh.modInfos[mod_name], keepAll=False,
                                       target_types=self._fp_types))
        # Finally, process the mod itself
        if loaded_mod.fileInfo.ci_key in self._fp_mods: return
        _fp_loop(loaded_mod)

    # TODO(inf) Might need second_pass parameter?
    def _read_record_fp(self, record):
        """Performs the actual parser-specific first pass code on the specified
        record. Treat this as a kind of lambda for a map call over all records
        matching the _fp_types. If _context_needs_followup is true, this will
        be called on every record again during the second pass.

        :param record: The record to read.
        :return: Whatever representation you want to convert this record
            into."""
        raise AbstractError(u'_read_record_fp not implemented')

    # Reading from plugin - second pass
    def _read_plugin_sp(self, loaded_mod):
        """Performs a second pass of reading on the specified plugin, but not
        its masters. Results are stored in id_stored_data.

        :param loaded_mod: The loaded mod to read from."""
        for rec_type in self._sp_types:
            rec_block = loaded_mod.tops.get(rec_type, None)
            if not rec_block: continue
            for record in rec_block.getActiveRecords():
                # Check if we even want this record first
                if self._is_record_useful(record):
                    rec_fid = record.fid
                    self.id_stored_data[rec_type][rec_fid] = \
                        self._read_record_sp(record)
                    # Check if we need to follow up on the first pass info
                    if self._context_needs_followup:
                        self.id_context[rec_fid] = \
                            self._read_record_fp(record)

    def _is_record_useful(self, record):
        """The parser should check if the specified record would be useful to
        it during the second pass, i.e. if we should store information for it.

        :param record: The record in question.
        :return: True if information for the record should be stored."""
        raise AbstractError(u'_is_record_useful not implemented')

    def _read_record_sp(self, record):
        """Performs the actual parser-specific second pass code on the
        specified record. Treat this as a kind of lambda for a map call over
        all records matching the _sp_types. Unless _get_cur_record_info is
        overriden, this will also be used during writing to compare new and old
        record information.

        :param record: The record to read.
        :return: Whatever representation you want to convert this record
            into."""
        raise AbstractError(u'_read_record_sp not implemented')

    # Note the non-PEP8 names - those point to refactored pseudo-API methods
    def readFromMod(self, mod_info):
        """Asks this parser to read information from the specified ModInfo
        instance. Executes the needed passes and stores extracted information
        in id_context and / or id_stored_data. Note that this does not
        automatically clear id_stored_data to allow combining multiple sources.

        :param mod_info: The ModInfo instance to read from."""
        self._current_mod = mod_info.ci_key
        # Check if we need to read at all
        a_types = self.all_types
        if not a_types:
            # We need to unset _current_mod since we're no longer loading a mod
            self._current_mod = None
            return
        # Load mod_info once and for all, then execute every needed pass
        loaded_mod = self._load_plugin(mod_info, keepAll=False,
                                       target_types=a_types)
        if self._fp_types:
            self._read_plugin_fp(loaded_mod)
        if self._sp_types:
            self._read_plugin_sp(loaded_mod)
        # We need to unset _current_mod since we're no longer loading a mod
        self._current_mod = None

    # Writing to plugins
    def _do_write_plugin(self, loaded_mod):
        """Writes the information stored in id_stored_data into the specified
        plugin.

        :param loaded_mod: The loaded mod to write to.
        :return: A dict mapping record types to the number of changed records
            in them."""
        # Counts the number of records that were changed in each record type
        num_changed_records = Counter()
        # We know that the loaded mod only has the tops loaded that we need
        for rec_type, stored_rec_info in self.id_stored_data.iteritems():
            rec_block = loaded_mod.tops.get(rec_type, None)
            # Check if this record type makes any sense to patch
            if not stored_rec_info or not rec_block: continue
            # TODO(inf) Copied from implementations below, may have to be
            #  getActiveRecords()?
            for record in rec_block.records:
                rec_fid = record.fid
                if rec_fid not in stored_rec_info: continue
                # Compare the stored information to the information currently
                # in the plugin
                new_info = stored_rec_info[rec_fid]
                cur_info = self._get_cur_record_info(record)
                if self._should_write_record(new_info, cur_info):
                    # It's different, ask the parser to write it out
                    self._write_record(record, new_info, cur_info)
                    record.setChanged()
                    num_changed_records[rec_type] += 1
        # Check if we've actually changed something, otherwise skip saving
        if num_changed_records:
            loaded_mod.safeSave()
        return num_changed_records

    def _get_cur_record_info(self, record):
        """Reads current information for the specified record in order to
        compare it with the stored information to determine if we need to write
        out. Falls back to the regular _read_record_sp method if it's
        implemented, since most parsers will want to do the same thing here,
        but you may want to override this e.g. if your parser can write, but
        not read plugins.

        :param record: The record to read.
        :return: Whatever representation you want to convert this record
            into."""
        return self._read_record_sp(record)

    @staticmethod
    def _should_write_record(new_info, cur_info):
        """Checks if we should write out information for the current record,
        based on the 'new' information (i.e. the info stored in id_stored_data)
        and the 'current' information (i.e. the info stored in the record
        itself). By default, this returns True if they are different. However,
        you may want to override this if you e.g. only care about the contents
        of a list and not its order.

        :param new_info: The new record info.
        :param cur_info: The current record info.
        :return: True if _write_record should be called."""
        return new_info != cur_info

    def _write_record(self, record, new_info, cur_info):
        """This is where your parser should perform the actual work of writing
        out the necessary changes to the record, using the given record
        information to determine what to change.

        :param record: The record to write to.
        :param new_info: The new record info.
        :param cur_info: The current record info."""
        raise AbstractError(u'_write_record not implemented')

    def writeToMod(self, mod_info):
        """Asks this parser to write its stored information to the specified
        ModInfo instance.

        :param mod_info: The ModInfo instance to write to.
        :return: A dict mapping record types to the number of changed records
            in them."""
        return self._do_write_plugin(
            self._load_plugin(mod_info, target_types=self.id_stored_data))

    # Other API
    @property
    def all_types(self):
        """Returns a set of all record types that this parser requires."""
        return set(self._fp_types) | set(self._sp_types)

class ActorFactions(_AParser):
    """Parses factions from NPCs and Creatures (in games that have those). Can
    read and write both plugins and CSV, and uses a single pass if called from
    a patcher, but two passes if called from a link."""
    _csv_header = (_(u'Type'), _(u'Actor Eid'), _(u'Actor Mod'),
                   _(u'Actor Object'), _(u'Faction Eid'), _(u'Faction Mod'),
                   _(u'Faction Object'), _(u'Rank'))
    _row_fmt_str = u'"%s","%s","%s","0x%06X","%s","%s","0x%06X","%s"\n'

    def __init__(self, aliases_=None, called_from_patcher=False):
        super(ActorFactions, self).__init__(aliases_, called_from_patcher)
        if self._called_from_patcher:
            self.id_stored_data = defaultdict(
                lambda: defaultdict(lambda: {u'factions': []}))
        a_types = bush.game.actor_types
        # We don't need the first pass if we're used by the parser
        self._fp_types = (a_types + (b'FACT',) if not called_from_patcher
                          else ())
        self._sp_types = a_types

    def _read_record_fp(self, record):
        return record.eid

    def _is_record_useful(self, record):
        return bool(record.factions)

    def _read_record_sp(self, record):
        return {f.faction: f.rank for f in record.factions}

    def _write_record(self, record, new_info, cur_info):
        for faction, rank in set(new_info.iteritems()) - set(cur_info.iteritems()):
            # Check if this an addition or a change
            for entry in record.factions:
                if entry.faction == faction:
                    # Just a change, use the existing faction
                    target_entry = entry
                    break
            else:
                # This is an addition, we need to create a new faction instance
                target_entry = MelObject()
                record.factions.append(target_entry)
            # Actually write out the attributes from new_info
            target_entry.faction = faction
            target_entry.rank = rank
            target_entry.unused1 = b'ODB'

    def _parse_line(self, csv_fields):
        top_grup, _aed, amod, aobj, _fed, fmod, fobj, rank = csv_fields[:8]
        aid = self._coerce_fid(amod, aobj)
        fid = self._coerce_fid(fmod, fobj)
        rank = int(rank)
        top_grup_sig = top_grup.encode(u'ascii')
        if self._called_from_patcher:
            ret_obj = MreRecord.type_class[top_grup_sig].getDefault(u'factions')
            ret_obj.faction = fid
            ret_obj.rank = rank
            self.id_stored_data[top_grup_sig][aid][u'factions'].append(ret_obj)
        else:
            self.id_stored_data[top_grup_sig][aid][fid] = rank

    def _write_rows(self, out):
        """Exports faction data to specified text file."""
        type_id_factions,id_eid = self.id_stored_data, self.id_context
        for top_grup_sig, id_factions in _key_sort(type_id_factions):
            for aid, factions, actorEid in _key_sort(id_factions, id_eid):
                for faction, rank, factionEid in _key_sort(factions, id_eid):
                    out.write(self._row_fmt_str % (top_grup_sig.decode(u'ascii'),
                        actorEid, aid[0], aid[1], factionEid,
                        faction[0], faction[1], rank))

#------------------------------------------------------------------------------
class ActorLevels(_HandleAliases):
    """Package: Functions for manipulating actor levels."""
    _csv_header = (_(u'Source Mod'), _(u'Actor Eid'), _(u'Actor Mod'),
        _(u'Actor Object'), _(u'Offset'), _(u'CalcMin'), _(u'CalcMax'),
        _(u'Old IsPCLevelOffset'), _(u'Old Offset'), _(u'Old CalcMin'),
        _(u'Old CalcMax'))
    _row_fmt_str = u'"%s","%s","%s","0x%06X","%d","%d","%d"'
    _parser_sigs = [b'NPC_']

    def __init__(self, aliases_=None, called_from_patcher=False):
        super(ActorLevels, self).__init__(aliases_, called_from_patcher)
        self.mod_id_levels = defaultdict(dict) #--levels = mod_id_levels[mod][longid]
        self.gotLevels = set()
        self._skip_mods = {u'none', bush.game.master_file.lower()}

    def readFromMod(self,modInfo):
        """Imports actor level data from the specified mod and its masters."""
        from . import bosh
        mod_id_levels, gotLevels = self.mod_id_levels, self.gotLevels
        loadFactory = self._load_factory(keepAll=False)
        for modName in (modInfo.masterNames + (modInfo.ci_key,)):
            if modName in gotLevels: continue
            modFile = ModFile(bosh.modInfos[modName],loadFactory)
            modFile.load(True)
            for record in modFile.tops[b'NPC_'].getActiveRecords():
                mod_id_levels[modName][record.fid] = (
                    record.eid, bool(record.flags.pcLevelOffset), record.level,
                    record.calcMin, record.calcMax)
            gotLevels.add(modName)

    def writeToMod(self,modInfo):
        """Exports actor levels to specified mod."""
        mod_id_levels = self.mod_id_levels
        modFile = self._load_plugin(modInfo)
        changed = 0
        id_levels = mod_id_levels.get(modInfo.ci_key,
                                      mod_id_levels.get(GPath(u'Unknown'),
                                                        None))
        if id_levels:
            for record in modFile.tops[b'NPC_'].records:
                fid = record.fid
                if fid in id_levels:
                    eid,isOffset,level,calcMin,calcMax = id_levels[fid]
                    if ((record.level,record.calcMin,record.calcMax) != (
                            level,calcMin,calcMax)):
                        (record.level,record.calcMin,record.calcMax) = (
                            level,calcMin,calcMax)
                        record.setChanged()
                        changed += 1
        #--Done
        if changed: modFile.safeSave()
        return changed

    def _parse_line(self, csv_fields):
        source, eid, fidMod, fidObject, offset, calcMin, calcMax = csv_fields[:7]
        if (source.lower() in self._skip_mods) or fidMod.lower() == u'none':
            return
        fid = self._coerce_fid(fidMod, fidObject)
        offset = int_or_zero(offset)
        calcMin = int_or_zero(calcMin)
        calcMax = int_or_zero(calcMax)
        self.mod_id_levels[source][fid] = (eid, 1, offset, calcMin, calcMax)

    def _write_rows(self, out):
        """Export NPC level data to specified text file."""
        extendedRowFormat = u',"%d","%d","%d","%d"\n'
        blankExtendedRow = u',,,,\n'
        #Sorted based on mod, then editor ID
        obId_levels = self.mod_id_levels[GPath(bush.game.master_file)]
        for mod, id_levels in _key_sort(self.mod_id_levels):
            if mod.s.lower() == bush.game.master_file.lower(): continue
            sor = _key_sort(id_levels, keys_dex=[0], values_dex=[0])
            for (fidMod, fidObject), (
                    eid, isOffset, offset, calcMin, calcMax) in sor:
                if isOffset:
                    out.write(self._row_fmt_str % (
                        mod, eid, fidMod, fidObject, offset, calcMin,
                        calcMax))
                    oldLevels = obId_levels.get((fidMod, fidObject),None)
                    if oldLevels:
                        oldEid,wasOffset,oldOffset,oldCalcMin,oldCalcMax \
                            = oldLevels
                        out.write(extendedRowFormat % (
                            wasOffset,oldOffset,oldCalcMin,oldCalcMax))
                    else:
                        out.write(blankExtendedRow)

#------------------------------------------------------------------------------
class EditorIds(_HandleAliases):
    """Editor ids for records, with functions for importing/exporting
    from/to mod/text file."""
    _csv_header = (_(u'Type'), _(u'Mod Name'), _(u'ObjectIndex'),
                   _(u'Editor Id'))
    _row_fmt_str = u'"%s","%s","0x%06X","%s"\n'

    def __init__(self, aliases_=None, questionableEidsSet=None,
                 badEidsList=None, called_from_patcher=False):
        super(EditorIds, self).__init__(aliases_, called_from_patcher)
        self.badEidsList = badEidsList
        self.questionableEidsSet = questionableEidsSet
        self.id_stored_data = defaultdict(dict) #--eid = eids[type][longid]
        self.old_new = {}
        self._parser_sigs = set(MreRecord.simpleTypes) - {b'CELL'}

    def _read_record(self, record, id_data):
        if record.eid: id_data[record.fid] = record.eid

    def writeToMod(self,modInfo):
        """Exports eids to specified mod."""
        modFile = self._load_plugin(modInfo)
        changed = []
        for type_ in self._parser_sigs:
            id_eid = self.id_stored_data.get(type_, None)
            typeBlock = modFile.tops.get(type_, None)
            if not id_eid or not typeBlock: continue
            for record in typeBlock.records:
                newEid = id_eid.get(record.fid)
                oldEid = record.eid
                if newEid and record.eid and newEid != oldEid:
                    record.eid = newEid
                    record.setChanged()
                    changed.append((oldEid,newEid))
        #--Update scripts
        old_new = dict(self.old_new)
        old_new.update({oldEid.lower(): newEid for oldEid, newEid in changed})
        changed.extend(self.changeScripts(modFile,old_new))
        #--Done
        if changed: modFile.safeSave()
        return changed

    def changeScripts(self,modFile,old_new):
        """Changes scripts in modfile according to changed."""
        changed = []
        if not old_new: return changed
        reWord = re.compile(u'' r'\w+')
        def subWord(match):
            word = match.group(0)
            newWord = old_new.get(word.lower())
            if not newWord:
                return word
            else:
                return newWord
        #--Scripts
        for script_rec in sorted(modFile.tops[b'SCPT'].records, key=attrgetter(u'eid')):
            if not script_rec.script_source: continue
            newText = reWord.sub(subWord,script_rec.script_source)
            if newText != script_rec.script_source:
                # header = u'\r\n\r\n; %s %s\r\n' % (script_rec.eid,u'-' * (77 -
                # len(script_rec.eid))) # unused - bug ?
                script_rec.script_source = newText
                script_rec.setChanged()
                changed.append((_(u'Script'),script_rec.eid))
        #--Quest Scripts
        for quest in sorted(modFile.tops[b'QUST'].records, key=attrgetter(u'eid')):
            questChanged = False
            for stage in quest.stages:
                for entry in stage.entries:
                    oldScript = entry.script_source
                    if not oldScript: continue
                    newScript = reWord.sub(subWord,oldScript)
                    if newScript != oldScript:
                        entry.script_source = newScript
                        questChanged = True
            if questChanged:
                changed.append((_(u'Quest'),quest.eid))
                quest.setChanged()
        #--Done
        return changed

    def _parse_line(self, csv_fields,
                    __reValidEid=re.compile(u'^[a-zA-Z0-9]+$'),
                    __reGoodEid=re.compile(u'^[a-zA-Z]')):
        top_grup, mod, objectIndex, eid = csv_fields[:4]  ##: debug: top_grup??
        longid = self._coerce_fid(mod, objectIndex)
        eid = str_or_none(eid)
        if not __reValidEid.match(eid):
            if self.badEidsList is not None:
                self.badEidsList.append(eid)
            return
        if self.questionableEidsSet is not None and not __reGoodEid.match(eid):
            self.questionableEidsSet.add(eid)
        #--Explicit old to new def? (Used for script updating.)
        if len(csv_fields) > 4:
            self.old_new[csv_fields[4].lower()] = eid
        self.id_stored_data[top_grup.encode(u'ascii')][longid] = eid

    def _write_rows(self, out):
        for top_grup_sig, id_eid in _key_sort(self.id_stored_data):
            for id_, eid_ in _key_sort(id_eid, by_value=True):
                out.write(self._row_fmt_str % (
                    top_grup_sig.decode(u'ascii'), id_[0], id_[1], eid_))

#------------------------------------------------------------------------------
class FactionRelations(_AParser):
    """Parses the relations between factions. Can read and write both plugins
    and CSV, and uses two passes to do so."""
    cls_rel_attrs = bush.game.relations_attrs
    _csv_header = bush.game.relations_csv_header
    _row_fmt_str = bush.game.relations_csv_row_format

    def __init__(self, aliases_=None, called_from_patcher=False):
        super(FactionRelations, self).__init__(aliases_, called_from_patcher)
        self._fp_types = (b'FACT',) if not self._called_from_patcher else ()
        self._sp_types = (b'FACT',)
        self._needs_fp_master_sort = True

    def _read_record_fp(self, record):
        # Gather the latest value for the EID matching the FID
        return record.eid

    def _is_record_useful(self, _record):
        # We want all records - even ones that have no relations, since those
        # may have still deleted original relations.
        return True

    def _read_record_sp(self, record):
        # Look if we already have relations and base ourselves on those,
        # otherwise make a new list
        relations = self.id_stored_data[b'FACT'][record.fid]
        # Merge added relations, preserve changed relations
        for relation in record.relations:
            rel_attrs = tuple(getattr(relation, a) for a
                              in self.cls_rel_attrs)
            other_fac = rel_attrs[0]
            relations[other_fac] = rel_attrs[1:]
        return relations

    def _write_record(self, record, new_info, cur_info):
        for rel_fac, rel_attributes in set(new_info.iteritems()) - set(cur_info.iteritems()):
            # See if this is a new relation or a change to an existing one
            for entry in record.relations:
                if rel_fac == entry.faction:
                    # Just a change, change the attributes
                    target_entry = entry
                    break
            else:
                # It's an addition, we need to make a new relation object
                target_entry = MelObject()
                record.relations.append(target_entry)
            # Actually write out the attributes from new_info
            for rel_attr, rel_val in izip(self.cls_rel_attrs,
                                         (rel_fac,) + rel_attributes): ##: Py3: unpack
                setattr(target_entry, rel_attr, rel_val)

    def _parse_line(self, csv_fields):
        _med, mmod, mobj, _oed, omod, oobj = csv_fields[:6]
        mid = self._coerce_fid(mmod, mobj)
        oid = self._coerce_fid(omod, oobj)
        self.id_stored_data[b'FACT'][mid][oid] = tuple(csv_fields[6:])

    def _write_rows(self, out):
        """Exports faction relations to specified text file."""
        id_relations, id_eid = self.id_stored_data[b'FACT'], self.id_context
        for main_fid, rel, main_eid in _key_sort(id_relations, id_eid_=id_eid):
            for oth_fid, relation_obj, oth_eid in _key_sort(
                    rel, id_eid_=id_eid):
                # PY3: I wish py2 allowed star exprs in tuples/lists...
                row_vals = (main_eid, main_fid[0], main_fid[1],
                            oth_eid, oth_fid[0], oth_fid[1]) + relation_obj
                out.write(self._row_fmt_str % row_vals)

#------------------------------------------------------------------------------
class FidReplacer(_HandleAliases):
    """Replaces one set of fids with another."""

    def __init__(self, aliases_=None, called_from_patcher=False):
        super(FidReplacer, self).__init__(aliases_, called_from_patcher)
        self._parser_sigs = MreRecord.simpleTypes
        self.old_new = {} #--Maps old fid to new fid
        self.old_eid = {} #--Maps old fid to old editor id
        self.new_eid = {} #--Maps new fid to new editor id

    def _parse_line(self, csv_fields):
        oldMod, oldObj, oldEid, newEid, newMod, newObj = csv_fields[1:7]
        oldId = self._coerce_fid(oldMod, oldObj)
        newId = self._coerce_fid(newMod, newObj)
        oldEid = str_or_none(oldEid)
        newEid = str_or_none(newEid)
        self.old_new[oldId] = newId
        self.old_eid[oldId] = oldEid
        self.new_eid[newId] = newEid

    def updateMod(self,modInfo,changeBase=False):
        """Updates specified mod file."""
        modFile = self._load_plugin(modInfo)
        # Create filtered versions of our mappings
        masters_list = set(modFile.augmented_masters())
        filt_fids = {oldId for oldId in self.old_eid if
                     oldId[0] in masters_list}
        filt_fids.update(newId for newId in self.new_eid
                         if newId[0] in masters_list)
        old_eid_filtered = {oldId: eid for oldId, eid
                            in self.old_eid.iteritems() if oldId in filt_fids}
        new_eid_filtered = {newId: eid for newId, eid
                            in self.new_eid.iteritems() if newId in filt_fids}
        old_new_filtered = {oldId: newId for oldId, newId
                            in self.old_new.iteritems()
                            if oldId in filt_fids and newId in filt_fids}
        if not old_new_filtered: return False
        #--Swapper function
        old_count = Counter()
        def swapper(oldId):
            newId = old_new_filtered.get(oldId, None)
            if newId:
                old_count[oldId] += 1
                return newId
            else:
                return oldId
        #--Do swap on all records
        for top_grup_sig in self._parser_sigs:
            for record in modFile.tops[top_grup_sig].getActiveRecords():
                if changeBase: record.fid = swapper(record.fid)
                record.mapFids(swapper, save=True)
                record.setChanged()
        #--Done
        if not old_count: return False
        modFile.safeSave()
        entries = [(count, old_eid_filtered[oldId],
                    new_eid_filtered[old_new_filtered[oldId]])
                   for oldId, count in old_count.iteritems()]
        entries.sort(key=itemgetter(1))
        return u'\n'.join([u'%3d %s >> %s' % entry for entry in entries])

#------------------------------------------------------------------------------
class FullNames(_HandleAliases):
    """Names for records, with functions for importing/exporting from/to
    mod/text file."""
    _csv_header = (_(u'Type'), _(u'Mod Name'), _(u'ObjectIndex'),
                   _(u'Editor Id'), _(u'Name'))
    _row_fmt_str = u'"%s","%s","0x%06X","%s","%s"\n'

    def __init__(self, aliases_=None, called_from_patcher=False):
        super(FullNames, self).__init__(aliases_, called_from_patcher)
        #--id_stored_data[top_grup_sig][longid] = (eid,name)
        self.id_stored_data = defaultdict(dict)
        self._parser_sigs = bush.game.namesTypes

    def _read_record(self, record, id_data):
        full = record.full or (record.rec_sig == b'LIGH' and u'NO NAME')
        if record.eid and full:
            id_data[record.fid] = (record.eid, full)

    def writeToMod(self,modInfo):
        """Exports id_stored_data to specified mod."""
        modFile = self._load_plugin(modInfo)
        changed = {}
        for type_ in self._parser_sigs:
            id_name = self.id_stored_data.get(type_, None)
            typeBlock = modFile.tops.get(type_,None)
            if not id_name or not typeBlock: continue
            for record in typeBlock.records:
                longid = record.fid
                full = record.full
                eid,newFull = id_name.get(longid,(0,0))
                if newFull and newFull not in (full,u'NO NAME'):
                    record.full = newFull
                    record.setChanged()
                    changed[eid] = (full,newFull)
        if changed: modFile.safeSave()
        return changed

    def _parse_line(self, csv_fields):
        top_grup, mod, objectIndex, eid, full = csv_fields[:5]
        longid = self._coerce_fid(mod, objectIndex)
        eid = str_or_none(eid)
        full = str_or_none(full)
        self.id_stored_data[top_grup.encode(u'ascii')][longid] = {
            # Discard the Editor ID and turn the tuples into dictionaries
            u'full': full} if self._called_from_patcher else (eid, full)

    def _write_rows(self, out):
        """Exports id_stored_data to specified text file."""
        for top_grup_sig, id_name in _key_sort(self.id_stored_data):
            for longid, (eid, rec_name) in _key_sort(id_name, keys_dex=[0],
                                                     values_dex=[0]):
                out.write(self._row_fmt_str % (top_grup_sig.decode(u'ascii'),
                    longid[0], longid[1], eid, rec_name.replace(u'"', u'""')))

#------------------------------------------------------------------------------
class ItemStats(_HandleAliases):
    """Statistics for armor and weapons, with functions for
    importing/exporting from/to mod/text file."""
    _row_fmt_str = u'"%s","%s","0x%06X",%s\n'

    def __init__(self, aliases_=None, called_from_patcher=False):
        super(ItemStats, self).__init__(aliases_, called_from_patcher)
        self.sig_stats_attrs = bush.game.statsTypes
        self.id_stored_data = defaultdict(lambda : defaultdict(dict))
        self._parser_sigs = set(self.sig_stats_attrs)
        # Populate _attr_serializer per attribute
        def _create_lambda(k):
            stype = nonzero_or_none if k == u'enchantPoints' else \
                bush.game.stats_attrs_desers[k][0] # previous behavior
            def _serialize(c):
                val = stype(c[k])
                tval = type(val)
                if val is None or tval is unicode:
                    return u'"%s"' % val
                elif tval is int:
                    return u'"%d"' % val
                elif tval is float:
                    return u'"%f"' % val
            return _serialize
        self._attr_serializer = {att: _create_lambda(att) for att in set(
            chain.from_iterable(self.sig_stats_attrs.viewvalues()))}

    def _read_record(self, record, id_data):
        atts = self.sig_stats_attrs[record.rec_sig]
        id_data[record.fid].update(
            izip(atts, (getattr(record, a) for a in atts)))

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        modFile = self._load_plugin(modInfo)
        changed = Counter() #--changed[modName] = numChanged
        for top_grup_sig, fid_attr_value in self.id_stored_data.iteritems():
            for record in modFile.tops[top_grup_sig].getActiveRecords():
                longid = record.fid
                itemStats = fid_attr_value.get(longid,None)
                if not itemStats: continue
                change = False
                for stat_key, n_stat in itemStats.iteritems():
                    if change:
                        setattr(record, stat_key, n_stat)
                        continue
                    o_stat = getattr(record, stat_key)
                    change = o_stat != n_stat
                    if change:
                        setattr(record, stat_key, n_stat)
                if change:
                    record.setChanged()
                    changed[longid[0]] += 1
        if changed: modFile.safeSave()
        return changed

    def _parse_line(self, csv_fields):
        """Reads stats from specified text file."""
        top_grup, modName, objectStr = csv_fields[:3]
        longid = self._coerce_fid(modName, objectStr) # blow and exit on header
        top_grup_sig = top_grup.encode(u'ascii')
        attrs = self.sig_stats_attrs[top_grup_sig]
        attr_value = {att: bush.game.stats_attrs_desers[att][0](value) for
                      att, value in izip(attrs, csv_fields[3:3 + len(attrs)])}
        if self._called_from_patcher:
            del attr_value[u'eid']
        self.id_stored_data[top_grup_sig][longid].update(attr_value)

    def _header_row(self, out): pass # different header per sig

    def _write_rows(self, out):
        """Writes stats to specified text file."""
        for top_grup_sig, fid_attr_value in _key_sort(self.id_stored_data):
            if not fid_attr_value: continue
            sers = [self._attr_serializer[x] for x in
                    self.sig_stats_attrs[top_grup_sig]]
            out.write(u'"%s"\n' % u'","'.join( # Py3: unpack
                (_(u'Type'), _(u'Mod Name'), _(u'ObjectIndex')) + tuple(
                    bush.game.stats_attrs_desers[a][1] for a in
                    self.sig_stats_attrs[top_grup_sig])))
            top_grup = top_grup_sig.decode(u'ascii')
            for longid in sorted(fid_attr_value, key=lambda lid: (
                    lid, fid_attr_value[lid][u'eid'].lower())):
                attr_value = fid_attr_value[longid]
                output = self._row_fmt_str % (top_grup, longid[0], longid[1],
                    u','.join(ser(attr_value) for ser in sers))
                out.write(output)

#------------------------------------------------------------------------------
class ScriptText(CsvParser):
    #todo(ut): maybe standardize script line endings (read both write windows)?
    """import & export functions for script text."""

    def __init__(self):
        self.eid_data = {}

    def export_scripts(self, folder, progress, skip, deprefix, skipcomments):
        """Writes scripts to specified folder."""
        eid_data = self.eid_data
        skip, deprefix = skip.lower(), deprefix.lower()
        x = len(skip)
        exportedScripts = []
        y = len(eid_data)
        r = len(deprefix)
        for z, eid in enumerate(sorted(eid_data, key=lambda eid: (eid, eid_data[eid][1]))):
            (scpt_txt, longid) = eid_data[eid]
            scpt_txt = decoder(scpt_txt)
            if skipcomments:
                scpt_txt =  self._filter_comments(scpt_txt)
                if not scpt_txt: continue
            progress((0.5 + (0.5 / y) * z), _(u'Exporting script %s.') % eid)
            if x == 0 or skip != eid[:x].lower():
                fileName = eid
                if r and deprefix == fileName[:r].lower():
                    fileName = fileName[r:]
                outpath = dirs[u'patches'].join(folder).join(
                    fileName + inisettings[u'ScriptFileExt'])
                self.__writting = (scpt_txt, longid, eid)
                self.write_text_file(outpath)
                del self.__writting
                exportedScripts.append(eid)
        return exportedScripts

    @staticmethod
    def _filter_comments(scpt_txt, __win_line_sep=u'\r\n'):
        tmp = []
        for line in scpt_txt.split(__win_line_sep):
            pos = line.find(u';')
            if pos == -1:  # note ''.find(u';') == -1
                tmp.append(line)
            elif pos == 0:
                continue
            else:
                if line[:pos].isspace(): continue
                tmp.append(line[:pos])
        return __win_line_sep.join(tmp) if tmp else u''

    def _header_row(self, out, __win_line_sep=u'\r\n'):
        # __win_line_sep: scripts line separator - or so we trust
        __, longid, eid = self.__writting
        header = (__win_line_sep + u';').join(
            (u'%s' % longid[0], u'0x%06X' % longid[1], eid))
        out.write(u';%s%s' % (header, __win_line_sep))

    def _write_rows(self, out):
        scpt_txt, __fid, __eid = self.__writting
        out.write(scpt_txt)

    def readFromMod(self, modInfo):
        """Reads stats from specified mod."""
        eid_data = self.eid_data
        loadFactory = LoadFactory(False, by_sig=[b'SCPT'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        with Progress(_(u'Export Scripts')) as progress:
            records = modFile.tops[b'SCPT'].getActiveRecords()
            y = len(records)
            for z, record in enumerate(records):
                progress(((0.5/y) * z), _(u'Reading scripts in %s.') % modInfo)
                eid_data[record.eid] = (record.script_source, record.fid)

    def writeToMod(self, modInfo, makeNew=False):
        """Writes scripts to specified mod."""
        eid_data = self.eid_data
        changed = []
        added = []
        loadFactory = LoadFactory(True, by_sig=[b'SCPT'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        for record in modFile.tops[b'SCPT'].getActiveRecords():
            eid = record.eid
            data_ = eid_data.get(eid,None)
            if data_ is not None:
                newText, longid = data_
                oldText = record.script_source
                if oldText.lower() != newText.lower():
                    record.script_source = newText
                    record.setChanged()
                    changed.append(eid)
                del eid_data[eid]
        if makeNew and eid_data:
            tes4 = modFile.tes4
            for eid, (newText, longid) in eid_data.iteritems():
                scriptFid = genFid(tes4.num_masters, tes4.getNextObject())
                newScript = MreRecord.type_class[b'SCPT'](
                    RecHeader(b'SCPT', 0, 0x40000, scriptFid, 0))
                newScript.eid = eid
                newScript.script_source = newText
                newScript.setChanged()
                modFile.tops[b'SCPT'].records.append(newScript)
                added.append(eid)
        if changed or added: modFile.safeSave()
        return changed, added

    def read_script_folder(self, textPath, progress):
        """Reads scripts from files in specified mods' directory in bashed
        patches folder."""
        for root_dir, dirs, files in textPath.walk():
            y = len(files)
            for z, f in enumerate(files):
                if f.cext != inisettings[u'ScriptFileExt']:
                    progress(((1 / y) * z), _(u'Skipping file %s.') % f)
                    continue
                progress(((1 / y) * z), _(u'Reading file %s.') % f)
                self.readFromText(root_dir.join(f))
        return bool(self.eid_data)

    def readFromText(self, textPath):
        with textPath.open(u'r', encoding=u'utf-8-sig') as ins:
            modName = FormID = eid = u''
            try:
                modName, FormID, eid = next(ins)[1:-2], next(ins)[1:-2], next(
                    ins)[1:-2]
                # we need a seek else we get ValueError: Mixing iteration and
                # read methods would lose data # 12 == what we chopped off + '\r\n'
                ins.seek(sum(len(x) for x in (modName, FormID, eid)) + 12)
                scriptText = ins.read() # read the rest in one blob
                self.eid_data[eid] = (scriptText, FormID)
            except (IndexError, StopIteration):
                deprint(u'Skipped %s - malformed script header lines:\n%s' % (
                    textPath.tail, u''.join((modName, FormID, eid))))

#------------------------------------------------------------------------------
class _UsesEffectsMixin(_HandleAliases):
    """Mixin class to support reading/writing effect data to/from csv files"""
    effect_headers = (
        _(u'Effect'),_(u'Name'),_(u'Magnitude'),_(u'Area'),_(u'Duration'),
        _(u'Range'),_(u'Actor Value'),_(u'SE Mod Name'),_(u'SE ObjectIndex'),
        _(u'SE school'),_(u'SE visual'),_(u'SE Is Hostile'),_(u'SE Name'))
    recipientTypeNumber_Name = {None:u'NONE',0:u'Self',1:u'Touch',2:u'Target',}
    recipientTypeName_Number = {y.lower(): x for x, y
                                in recipientTypeNumber_Name.iteritems()
                                if x is not None}
    actorValueNumber_Name = {x: y for x, y
                             in enumerate(bush.game.actor_values)}
    actorValueNumber_Name[None] = u'NONE'
    actorValueName_Number = {y.lower(): x for x, y
                             in actorValueNumber_Name.iteritems()
                             if x is not None}
    schoolTypeNumber_Name = {None:u'NONE',0:u'Alteration',1:u'Conjuration',
                             2:u'Destruction',3:u'Illusion',4:u'Mysticism',
                             5:u'Restoration',}
    schoolTypeName_Number = {y.lower(): x for x, y
                             in schoolTypeNumber_Name.iteritems()
                             if x is not None}
    _float_attrs = frozenset([u'model.modb', u'weight'])
    _int_attrs = ()
    _row_fmt_str = u'"%s","0x%06X",%s\n'

    def __init__(self, aliases_, atts, called_from_patcher=False):
        super(_UsesEffectsMixin, self).__init__(aliases_, called_from_patcher)
        self._get_csv_serializers(atts)
        self.fid_stats = {}
        self.id_stored_data = {self._parser_sigs[0]: self.fid_stats}

    def _parse_line(self, mid): # common operations for Sigil/Ingredients
        for att in self._float_attrs:
            self.fid_stats[mid][att] = float_or_none(self.fid_stats[mid][att])
        for att in self._int_attrs:
            self.fid_stats[mid][att] = int_or_none(self.fid_stats[mid][att])
        for att in [u'eid', u'full', u'model.modPath', u'iconPath']:
            self.fid_stats[mid][att] = str_or_none(self.fid_stats[mid][att])

    def _get_csv_serializers(self, atts): ##: technically belongs to records
        """Return encoders per attribute - each encoder should return a
        string corresponding to a csv column."""
        # we need to capture k otherwise it will point to atts[-1]
        _create_lambda = lambda k: (lambda c: u'"%s"' % c[k])
        self._attr_serializer = OrderedDict(
            (k, _create_lambda(k)) for k in atts)
        # special handling for script_fid - used to be exception based...
        if u'script_fid' in atts:
            def _handle_script_fid(c):
                fid_tuple = c[u'script_fid']
                if fid_tuple is not None:
                    return u'"%s","0x%06X"' % fid_tuple
                return u'"None","None"'
            self._attr_serializer[u'script_fid'] = _handle_script_fid
        # int attributes
        for k in self._int_attrs: ##: make sure %d works even for flags
            self._attr_serializer[k] = (lambda k: (lambda c: u'"%d"' % c[k]))(
                k)
        # effects
        if u'effects' in atts:
            self._attr_serializer[u'effects'] = lambda c: self.writeEffects(
                c[u'effects'])[1:] # chop off the first comma...

    def _read_record(self, record, id_data, __attrgetters=attrgetter_cache):
        id_data[record.fid] = {att: __attrgetters[att](record) for att in
                               self._attr_serializer}

    def readEffects(self, _effects, __packer=structs_cache[u'I'].pack):
        schoolTypeName_Number = _UsesEffectsMixin.schoolTypeName_Number
        recipientTypeName_Number = _UsesEffectsMixin.recipientTypeName_Number
        actorValueName_Number = _UsesEffectsMixin.actorValueName_Number
        effects = []
        while len(_effects) >= 13:
            _effect,_effects = _effects[1:13],_effects[13:]
            eff_name,magnitude,area,duration,range_,actorvalue,semod,seobj,\
            seschool,sevisual,seflags,sename = _effect
            eff_name = str_or_none(eff_name) #OBME not supported
            # (support requires adding a mod/objectid format to the
            # csv, this assumes all MGEFCodes are raw)
            magnitude, area, duration = [int_or_none(x) for x in
                                         (magnitude, area, duration)]
            range_ = str_or_none(range_)
            if range_:
                range_ = recipientTypeName_Number.get(range_.lower(),
                                                      int_or_zero(range_))
            actorvalue = str_or_none(actorvalue)
            if actorvalue:
                actorvalue = actorValueName_Number.get(actorvalue.lower(),
                                                       int_or_zero(actorvalue))
            if None in (eff_name,magnitude,area,duration,range_,actorvalue):
                continue
            rec_type = MreRecord.type_class[self._parser_sigs[0]]
            eff = rec_type.getDefault(u'effects')
            effects.append(eff)
            eff.effect_sig = eff_name.encode(u'ascii')
            eff.magnitude = magnitude
            eff.area = area
            eff.duration = duration
            eff.recipient = range_
            eff.actorValue = actorvalue
            # script effect
            semod = str_or_none(semod)
            if semod is None or not seobj.startswith(u'0x'):
                continue
            seschool = str_or_none(seschool)
            if seschool:
                seschool = schoolTypeName_Number.get(seschool.lower(),
                                                     int_or_zero(seschool))
            seflags = int_or_none(seflags)
            sename = str_or_none(sename)
            if any(x is None for x in (seschool, seflags, sename)):
                continue
            eff.scriptEffect = se = rec_type.getDefault(
                u'effects.scriptEffect')
            se.full = sename
            se.script_fid = self._coerce_fid(semod, seobj)
            se.school = seschool
            sevisuals = int_or_none(sevisual) #OBME not
            # supported (support requires adding a mod/objectid format to
            # the csv, this assumes visual MGEFCode is raw)
            if sevisuals is None: # it was no int try to read unicode MGEF Code
                sevisuals = str_or_none(sevisual)
                if sevisuals == u'' or sevisuals is None:
                    sevisuals = null4
                else:
                    sevisuals = sevisuals.encode(u'ascii')
            else: # pack int to bytes
                sevisuals = __packer(sevisuals)
            sevisual = sevisuals
            se.visual = sevisual
            se.flags = seflags # FIXME this need to be a se_flags
        return effects

    @staticmethod
    def writeEffects(effects):
        schoolTypeNumber_Name = _UsesEffectsMixin.schoolTypeNumber_Name
        recipientTypeNumber_Name = _UsesEffectsMixin.recipientTypeNumber_Name
        actorValueNumber_Name = _UsesEffectsMixin.actorValueNumber_Name
        effectFormat = u',,"%s","%d","%d","%d","%s","%s"'
        scriptEffectFormat = u',"%s","0x%06X","%s","%s","%s","%s"'
        noscriptEffectFiller = u',"None","None","None","None","None","None"'
        output = []
        for effect in effects:
            efname, magnitude, area, duration, range_, actorvalue = \
                effect.effect_sig.decode(u'ascii'), effect.magnitude, \
                effect.area, effect.duration, effect.recipient, \
                effect.actorValue
            range_ = recipientTypeNumber_Name.get(range_,range_)
            actorvalue = actorValueNumber_Name.get(actorvalue,actorvalue)
            output.append(effectFormat % (
                efname,magnitude,area,duration,range_,actorvalue))
            if effect.scriptEffect: ##: #480 - setDefault commit - return None
                se = effect.scriptEffect
                longid, seschool, sevisual, seflags, sename = \
                    se.script_fid, se.school, se.visual, se.flags, se.full
                sevisual = u'NONE' if sevisual == null4 else sevisual.decode(
                    u'ascii')
                seschool = schoolTypeNumber_Name.get(seschool,seschool)
                output.append(scriptEffectFormat % (longid[0], longid[1],
                    seschool, sevisual, bool(int(seflags)), sename))
            else:
                output.append(noscriptEffectFiller)
        return u''.join(output)

    def writeToMod(self, modInfo, __attrgetters=attrgetter_cache):
        """Writes stats to specified mod."""
        fid_stats = self.fid_stats
        modFile = self._load_plugin(modInfo)
        changed = [] #eids
        for record in modFile.tops[self._parser_sigs[0]].getActiveRecords():
            newStats = fid_stats.get(record.fid, None)
            if not newStats: continue
            imported = False
            for att, val in newStats.iteritems():
                old_val = __attrgetters[att](record)
                if att == u'eid': old_eid = old_val
                if old_val != val:
                    imported = True
                    setattr_deep(record, att, val)
            if imported:
                changed.append(old_eid)
                record.setChanged()
        if changed: modFile.safeSave()
        return changed

    def _write_rows(self, out):
        """Exports stats to specified text file."""
        stats, row_fmt_str = self.fid_stats, self._row_fmt_str
        for rfid in sorted(stats, key=lambda x: stats[x][u'eid'].lower()): ##: , x[0]) ??
            output = row_fmt_str % (rfid[0], rfid[1], u','.join(
                ser(stats[rfid]) for ser in self._attr_serializer.itervalues()))
            out.write(output)

#------------------------------------------------------------------------------
class SigilStoneDetails(_UsesEffectsMixin):
    """Details on SigilStones, with functions for importing/exporting
    from/to mod/text file."""
    _csv_header = (_(u'Mod Name'), _(u'ObjectIndex'), _(u'Editor Id'),
                   _(u'Name'), _(u'Model Path'), _(u'Bound Radius'),
                   _(u'Icon Path'), _(u'Script Mod Name'),
                   _(u'Script ObjectIndex'), _(u'Uses'), _(u'Value'),
                   _(u'Weight'),) + _UsesEffectsMixin.effect_headers * 2 + (
                      _(u'Additional Effects (Same format)'),)
    _int_attrs = (u'uses', u'value')
    _parser_sigs = [b'SGST']

    def __init__(self, aliases_=None, called_from_patcher=False):
        super(SigilStoneDetails, self).__init__(aliases_,
            [u'eid', u'full', u'model.modPath', u'model.modb', u'iconPath',
             u'script_fid', u'uses', u'value', u'weight', u'effects'],
            called_from_patcher)

    def _parse_line(self, csv_fields):
        """Imports stats from specified text file."""
        mmod, mobj, eid, full, modPath, modb, iconPath, smod, sobj, uses, \
            value, weight = csv_fields[:12]
        mid = self._coerce_fid(mmod, mobj)
        smod = str_or_none(smod)
        if smod is None: sid = None
        else: sid = self._coerce_fid(smod, sobj)
        vals = [eid, full, modPath, modb, iconPath, sid, uses, value, weight,
                self.readEffects(csv_fields[12:])]
        self.fid_stats[mid] = dict(izip(self._attr_serializer, vals))
        super(SigilStoneDetails, self)._parse_line(mid)

#------------------------------------------------------------------------------
class ItemPrices(_HandleAliases):
    """Function for importing/exporting from/to mod/text file only the
    value, name and eid of records."""
    item_prices_attrs = (u'value', u'eid', u'full')
    _csv_header = (_(u'Mod Name'), _(u'ObjectIndex'), _(u'Value'),
                   _(u'Editor Id'), _(u'Name'), _(u'Type'))
    _row_fmt_str = u'"%s","0x%06X",' + csvFormat(u'iss') + u',%s\n'

    def __init__(self, aliases_=None):
        super(ItemPrices, self).__init__(aliases_)
        self.id_stored_data = defaultdict(dict)
        self._parser_sigs = set(bush.game.pricesTypes)

    def _read_record(self, record, id_data):
        id_data[record.fid] = [getattr(record, a) for a in
                               self.item_prices_attrs]

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        modFile = self._load_plugin(modInfo)
        changed = Counter() #--changed[modName] = numChanged
        for top_grup_sig, fid_stats in self.id_stored_data.iteritems():
            for record in modFile.tops[top_grup_sig].getActiveRecords():
                longid = record.fid
                stats = fid_stats.get(longid,None)
                if not stats: continue
                value = stats[0]
                if record.value != value:
                    record.value = value
                    changed[longid[0]] += 1
                    record.setChanged()
        if changed: modFile.safeSave()
        return changed

    def _parse_line(self, csv_fields):
        mmod, mobj, value, eid, itm_name, top_grup = csv_fields[:6]
        longid = self._coerce_fid(mmod, mobj)
        value = int_or_zero(value)
        eid = str_or_none(eid)
        itm_name = str_or_none(itm_name)
        self.id_stored_data[top_grup.encode(u'ascii')][longid] = [value, eid,
                                                                  itm_name]

    def _write_rows(self, out):
        """Writes item prices to specified text file."""
        for top_grup_sig, fid_stats in _key_sort(self.id_stored_data):
            if not fid_stats: continue
            top_grup = top_grup_sig.decode(u'ascii')
            for fid in sorted(fid_stats,key=lambda x:(
                    fid_stats[x][1].lower(),fid_stats[x][0])):
                out.write(self._row_fmt_str % ((fid[0], fid[1]) +
                    tuple(fid_stats[fid]) + (top_grup,)))

#------------------------------------------------------------------------------
class SpellRecords(_UsesEffectsMixin):
    """Statistics for spells, with functions for importing/exporting from/to
    mod/text file."""
    _extra_attrs = (u'flags.noAutoCalc', u'flags.startSpell',
        u'flags.immuneToSilence', u'flags.ignoreLOS',
        u'flags.scriptEffectAlwaysApplies', u'flags.disallowAbsorbReflect',
        u'flags.touchExplodesWOTarget', u'effects')
    _csv_attrs = (u'eid', u'cost', u'level', u'spellType', u'flags')
    _csv_header = (_(u'Type'), _(u'Mod Name'), _(u'ObjectIndex'),
                  _(u'Editor Id'), _(u'Cost'), _(u'Level Type'),
                  _(u'Spell Type'), _(u'Spell Flags'))
    _float_attrs = frozenset()
    _int_attrs = (u'cost', u'flags')
    _row_fmt_str = u'"SPEL","%s","0x%06X",%s\n'
    _parser_sigs = [b'SPEL']

    def __init__(self, aliases_=None, detailed=False,
                 called_from_patcher=False):
        atts = (bush.game.spell_stats_attrs if called_from_patcher
                else self._csv_attrs)
        self.detailed = detailed
        if detailed:
            atts += self.__class__._extra_attrs
            self._csv_header += (
                _(u'Manual Cost'), _(u'Start Spell'), _(u'Immune To Silence'),
                _(u'Area Effect Ignores LOS'), _(u'Script Always Applies'),
                _(u'Disallow Absorb and Reflect'), _(
                    u'Touch Explodes Without Target'),
            ) + _UsesEffectsMixin.effect_headers * 2 + (
                         _(u'Additional Effects (Same format)'),)
        self.spellTypeNumber_Name = {None: u'NONE',
                                     0   : u'Spell',
                                     1   : u'Disease',
                                     2   : u'Power',
                                     3   : u'LesserPower',
                                     4   : u'Ability',
                                     5   : u'Poison',}
        self.spellTypeName_Number = {y.lower(): x for x, y
                                     in self.spellTypeNumber_Name.iteritems()
                                     if x is not None}
        self.levelTypeNumber_Name = {None : u'NONE',
                                     0    : u'Novice',
                                     1    : u'Apprentice',
                                     2    : u'Journeyman',
                                     3    : u'Expert',
                                     4    : u'Master',}
        self.levelTypeName_Number = {y.lower(): x for x, y
                                     in self.levelTypeNumber_Name.iteritems()
                                     if x is not None}
        super(SpellRecords, self).__init__(aliases_, atts, called_from_patcher)

    def _get_csv_serializers(self, atts):
        super(SpellRecords, self)._get_csv_serializers(atts)
        level_name = self.levelTypeNumber_Name
        spell_name = self.spellTypeNumber_Name
        if u'level' in self._attr_serializer:
            self._attr_serializer[u'level'] = lambda c: \
                u'"%s"' % level_name.get(c[u'level'], c[u'level'])
        if u'spellType' in self._attr_serializer:
            self._attr_serializer[u'spellType'] = lambda c: \
                u'"%s"' % spell_name.get(c[u'spellType'], c[u'spellType'])

    def _parse_line(self, fields):
        """Imports stats from specified text file."""
        if int_or_none(fields[4]) is None:  # Index 4 was FULL now cost
            group, mmod, mobj, eid, _full, cost, levelType, spellType = \
                fields[:8] # FULL was dropped and flags added
            spell_flags = 0
        else:
            group, mmod, mobj, eid, cost, levelType, spellType, spell_flags = \
                fields[:8]
        if group.lower() != u'spel': return
        mid = self._coerce_fid(mmod, mobj)
        eid = str_or_none(eid)
        cost = int_or_zero(cost)
        levelType = self.levelTypeName_Number.get(levelType.lower(),
                                                  int_or_zero(levelType))
        spellType = self.spellTypeName_Number.get(spellType.lower(),
                                                  int_or_zero(spellType))
        ##: HACK, 'flags' needs to be a Flags instance on dump
        spell_flags = MreRecord.type_class[b'SPEL']._SpellFlags(
            int_or_zero(spell_flags))
        vals = [eid, cost, levelType, spellType, spell_flags]
        self.fid_stats[mid] = dict( ##: this won't work for other games
            izip(self._csv_attrs, vals))
        if not self.detailed:  # or len(fields) < 7: ValueError
            return
        mc, ss, its, aeil, saa, daar, tewt = [_str_to_bool(f) for f in
                                              fields[8:15]] #py3: map
        vals = [mc, ss, its, aeil, saa, daar, tewt,
                self.readEffects(fields[15:])]
        self.fid_stats[mid].update(izip(self.__class__._extra_attrs, vals))

#------------------------------------------------------------------------------
class IngredientDetails(_UsesEffectsMixin):
    """Details on Ingredients, with functions for importing/exporting
    from/to mod/text file."""
    _csv_header = (_(u'Mod Name'), _(u'ObjectIndex'), _(u'Editor Id'),
        _(u'Name'), _(u'Model Path'), _(u'Bound Radius'), _(u'Icon Path'),
        _(u'Script Mod Name'), _(u'Script ObjectIndex'), _(u'Value'),
        _(u'Weight'),) + _UsesEffectsMixin.effect_headers * 2 + \
                  (_(u'Additional Effects (Same format)'),)
    _int_attrs = (u'value',)
    _parser_sigs = [b'INGR']

    def __init__(self, aliases_=None, called_from_patcher=False):
        # same as SGST apart from 'uses'
        super(IngredientDetails, self).__init__(aliases_, [u'eid', u'full',
            u'model.modPath', u'model.modb', u'iconPath', u'script_fid',
            u'value', u'weight', u'effects'], called_from_patcher)

    def _parse_line(self, csv_fields):
        mmod, mobj, eid, full, modPath, modb, iconPath, smod, sobj, value,\
        weight = csv_fields[:11]
        mid = self._coerce_fid(mmod, mobj)
        smod = str_or_none(smod)
        if smod is None: sid = None
        else: sid = self._coerce_fid(smod, sobj)
        self.fid_stats[mid] = dict(izip(self._attr_serializer, [eid, full,
            modPath, modb, iconPath, sid, value, weight, self.readEffects(
                csv_fields[11:])]))
        super(IngredientDetails, self)._parse_line(mid)
