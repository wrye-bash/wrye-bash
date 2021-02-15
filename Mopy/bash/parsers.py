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
import ctypes
import re
from collections import defaultdict, Counter
from itertools import izip
from operator import attrgetter, itemgetter

# Internal
from . import bush, load_order
from .balt import Progress
from .bass import dirs, inisettings
from .bolt import GPath, decoder, deprint, csvFormat, floats_equal, \
    setattr_deep, attrgetter_cache, struct_unpack, struct_pack
from .brec import MreRecord, MelObject, genFid, RecHeader, null4
from .exception import AbstractError
from .mod_files import ModFile, LoadFactory

# Utils ##: absorb in CsvParser
def _coerce(value, newtype, base=None, AllowNone=False):
    try:
        if newtype is float:
            #--Force standard precision
            return round(struct_unpack('f', struct_pack('f', float(value)))[0], 6)
        elif newtype is bool:
            if isinstance(value, (unicode, bytes)): ##: investigate
                retValue = value.strip().lower()
                if AllowNone and retValue == u'none': return None
                return retValue not in (u'',u'none',u'false',u'no',u'0',u'0.0')
            else: return bool(value)
        elif base: retValue = newtype(value, base)
        elif newtype is unicode: retValue = decoder(value)
        else: retValue = newtype(value)
        if (AllowNone and
            (isinstance(retValue,bytes) and retValue.lower() == b'none') or
            (isinstance(retValue,unicode) and retValue.lower() == u'none')
            ):
            return None
        return retValue
    except (ValueError,TypeError):
        if newtype is int and not AllowNone: return 0
        return None

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
    """Basic read/write csv functionality - ScriptParser handles script files
    not csvs though."""
    _csv_header = () # has property overrides
    _row_fmt_str = u'' # has property overrides

    def readFromText(self, csv_path):
        """Reads information from the specified CSV file and stores the result
        in id_stored_info. You must override _parse_line for this method to
        work.

        :param csv_path: The path to the CSV file that should be read."""
        with _CsvReader(csv_path) as ins:
            for fields in ins:
                try:
                    self._parse_line(fields)
                except (IndexError, ValueError, TypeError):
                    """TypeError/ValueError trying to unpack None/few values"""

    def _parse_line(self, csv_fields):
        """Parse the specified CSV line and update the parser's instance
        id_stored_info - both id and stored_info vary in type and meaning.

        :param csv_fields: A line in a CSV file, already split into fields."""
        raise AbstractError(u'%s must implement _parse_line' % type(self))

    def writeToText(self,textPath):
        """Exports ____ to specified text file."""
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            out.write(self._header_row())
            self._write_rows(out)

    def _write_rows(self, out):
        raise AbstractError

    def _header_row(self):
        return u'"%s"\n' % u'","'.join(self._csv_header)

class _HandleAliases(CsvParser):##: Py3 move to bolt after absorbing _CsvReader
    """WIP aliases handling."""

    def __init__(self, aliases_):
        # Automatically set in _parse_csv_sources to the patch file's aliases -
        # used if the Aliases Patcher has been enabled
        self.aliases = aliases_ or {} # type: dict

    def _get_alias(self, modname):
        """Encapsulate getting alias for modname returned from _CsvReader."""
        ##: inline once parsers are refactored (and document also the csv format)
        modname = GPath(modname)
        return GPath(self.aliases.get(modname, modname)) ##: drop GPath?

    def _coerce_fid(self, modname, hex_fid):
        """Create a long formid from a unicode modname and a unicode
        hexadecimal - it will blow with ValueError if hex_fid is not
        convertible."""
        if not hex_fid.startswith(u'0x'): raise ValueError # exit _parse_line
        return self._get_alias(modname), int(hex_fid, 0)

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
        return LoadFactory(keepAll, by_sig=target_types or self.types)

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
       stored in id_stored_info. You will have to set _sp_types appropriately
       and override _is_record_useful and _read_record_sp to use this pass.
     - If you want to skip either pass, just leave _fp_types / _sp_types
       empty."""

    def __init__(self):
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
        self.id_stored_info = defaultdict(lambda : defaultdict(dict))
        # Automatically set to True when called by a patcher - can be used to
        # alter behavior correspondingly
        self.called_from_patcher = False
        super(_AParser, self).__init__({})

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
            self._fp_mods.add(mod_to_read.fileInfo.name)
        # Process the mod's masters first, but see if we need to sort them
        master_names = loaded_mod.tes4.masters
        if self._needs_fp_master_sort:
            master_names = load_order.get_ordered(master_names)
        for mod_name in master_names:
            if mod_name in self._fp_mods: continue
            _fp_loop(self._load_plugin(bosh.modInfos[mod_name], keepAll=False,
                                       target_types=self._fp_types))
        # Finally, process the mod itself
        if loaded_mod.fileInfo.name in self._fp_mods: return
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
        its masters. Results are stored in id_stored_info.

        :param loaded_mod: The loaded mod to read from."""
        for rec_type in self._sp_types:
            rec_block = loaded_mod.tops.get(rec_type, None)
            if not rec_block: continue
            for record in rec_block.getActiveRecords():
                # Check if we even want this record first
                if self._is_record_useful(record):
                    rec_fid = record.fid
                    self.id_stored_info[rec_type][rec_fid] = \
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
        in id_context and / or id_stored_info. Note that this does not
        automatically clear id_stored_info to allow combining multiple sources.

        :param mod_info: The ModInfo instance to read from."""
        self._current_mod = mod_info.name
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
        """Writes the information stored in id_stored_info into the specified
        plugin.

        :param loaded_mod: The loaded mod to write to.
        :return: A dict mapping record types to the number of changed records
            in them."""
        # Counts the number of records that were changed in each record type
        num_changed_records = Counter()
        # We know that the loaded mod only has the tops loaded that we need
        for rec_type, stored_rec_info in self.id_stored_info.iteritems():
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

    def _should_write_record(self, new_info, cur_info):
        """Checks if we should write out information for the current record,
        based on the 'new' information (i.e. the info stored in id_stored_info)
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
            self._load_plugin(mod_info, target_types=self.id_stored_info))

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

    def __init__(self):
        super(ActorFactions, self).__init__()
        a_types = bush.game.actor_types
        # We don't need the first pass if we're used by the parser
        self._fp_types = (a_types + (b'FACT',) if not self.called_from_patcher
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
        self.id_stored_info[top_grup.encode(u'ascii')][aid][fid] = rank

    def _write_rows(self, out):
        """Exports faction data to specified text file."""
        type_id_factions,id_eid = self.id_stored_info, self.id_context
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

    def __init__(self, aliases_=None):
        super(ActorLevels, self).__init__(aliases_)
        self.mod_id_levels = defaultdict(dict) #--levels = mod_id_levels[mod][longid]
        self.gotLevels = set()
        self.types = [b'NPC_']
        self._skip_mods = {u'none', bush.game.master_file.lower()}

    def readFromMod(self,modInfo):
        """Imports actor level data from the specified mod and its masters."""
        from . import bosh
        mod_id_levels, gotLevels = self.mod_id_levels, self.gotLevels
        loadFactory = self._load_factory(keepAll=False)
        for modName in (modInfo.masterNames + (modInfo.name,)):
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
        id_levels = mod_id_levels.get(modInfo.name,
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
        offset = _coerce(offset, int)
        calcMin = _coerce(calcMin, int)
        calcMax = _coerce(calcMax, int)
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
                        oldEid,wasOffset,oldOffset,oldCalcMin,oldCalcMax\
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

    def __init__(self, types=None, aliases_=None, questionableEidsSet=None,
                 badEidsList=None):
        super(EditorIds, self).__init__(aliases_)
        self.badEidsList = badEidsList
        self.questionableEidsSet = questionableEidsSet
        self.type_id_eid = defaultdict(dict) #--eid = eids[type][longid]
        self.old_new = {}
        if types:
            self.types = types
        else:
            self.types = set(MreRecord.simpleTypes)
            self.types.discard(b'CELL')

    def readFromMod(self,modInfo):
        """Imports eids from specified mod."""
        modFile = self._load_plugin(modInfo, keepAll=False)
        for top_grup_sig in self.types:
            typeBlock = modFile.tops.get(top_grup_sig)
            if not typeBlock: continue
            id_eid = self.type_id_eid[top_grup_sig]
            for record in typeBlock.getActiveRecords():
                if record.eid: id_eid[record.fid] = record.eid

    def writeToMod(self,modInfo):
        """Exports eids to specified mod."""
        modFile = self._load_plugin(modInfo)
        changed = []
        for type_ in self.types:
            id_eid = self.type_id_eid.get(type_, None)
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
        reWord = re.compile(r'\w+')
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
        eid = _coerce(eid, unicode, AllowNone=True)
        if not __reValidEid.match(eid):
            if self.badEidsList is not None:
                self.badEidsList.append(eid)
            return
        if self.questionableEidsSet is not None and not __reGoodEid.match(eid):
            self.questionableEidsSet.add(eid)
        #--Explicit old to new def? (Used for script updating.)
        if len(csv_fields) > 4:
            self.old_new[_coerce(csv_fields[4], unicode).lower()] = eid
        self.type_id_eid[top_grup.encode(u'ascii')][longid] = eid

    def _write_rows(self, out):
        for top_grup_sig, id_eid in _key_sort(self.type_id_eid):
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

    def __init__(self):
        super(FactionRelations, self).__init__()
        self._fp_types = (b'FACT',) if not self.called_from_patcher else ()
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
        relations = self.id_stored_info[b'FACT'][record.fid]
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
        self.id_stored_info[b'FACT'][mid][oid] = tuple(csv_fields[6:])

    def _write_rows(self, out):
        """Exports faction relations to specified text file."""
        id_relations, id_eid = self.id_stored_info[b'FACT'], self.id_context
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

    def __init__(self, types=None, aliases_=None):
        super(FidReplacer, self).__init__(aliases_)
        self.types = types or MreRecord.simpleTypes
        self.old_new = {} #--Maps old fid to new fid
        self.old_eid = {} #--Maps old fid to old editor id
        self.new_eid = {} #--Maps new fid to new editor id

    def _parse_line(self, csv_fields):
        oldMod, oldObj, oldEid, newEid, newMod, newObj = csv_fields[1:7]
        oldId = self._coerce_fid(oldMod, oldObj)
        newId = self._coerce_fid(newMod, newObj)
        oldEid = _coerce(oldEid, unicode, AllowNone=True)
        newEid = _coerce(newEid, unicode, AllowNone=True)
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
        for top_grup_sig in self.types:
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

    def __init__(self, types=None, aliases_=None):
        super(FullNames, self).__init__(aliases_)
        #--(eid,name) = type_id_name[type][longid]
        self.type_id_name = defaultdict(dict)
        self.types = types or bush.game.namesTypes

    def readFromMod(self,modInfo):
        """Imports type_id_name from specified mod."""
        type_id_name= self.type_id_name
        modFile = self._load_plugin(modInfo, keepAll=False)
        for type_ in self.types:
            typeBlock = modFile.tops.get(type_,None)
            if not typeBlock: continue
            id_name = type_id_name[type_]
            for record in typeBlock.getActiveRecords():
                longid = record.fid
                full = record.full or (type_ == b'LIGH' and u'NO NAME')
                if record.eid and full:
                    id_name[longid] = (record.eid,full)

    def writeToMod(self,modInfo):
        """Exports type_id_name to specified mod."""
        modFile = self._load_plugin(modInfo)
        changed = {}
        for type_ in self.types:
            id_name = self.type_id_name.get(type_, None)
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
        eid = _coerce(eid, unicode, AllowNone=True)
        full = _coerce(full, unicode, AllowNone=True)
        self.type_id_name[top_grup.encode(u'ascii')][longid] = (eid, full)

    def _write_rows(self, out):
        """Exports type_id_name to specified text file."""
        for top_grup_sig, id_name in _key_sort(self.type_id_name):
            for longid, (eid, rec_name) in _key_sort(id_name, keys_dex=[0],
                                                     values_dex=[0]):
                out.write(self._row_fmt_str % (top_grup_sig.decode(u'ascii'),
                    longid[0], longid[1], eid, rec_name.replace(u'"', u'""')))

#------------------------------------------------------------------------------
class ItemStats(_HandleAliases):
    """Statistics for armor and weapons, with functions for
    importing/exporting from/to mod/text file."""

    @staticmethod
    def sstr(value):
        return _coerce(value, unicode, AllowNone=True)

    @staticmethod
    def sfloat(value):
        return _coerce(value, float, AllowNone=True)

    @staticmethod
    def sint(value):
        return _coerce(value, int, AllowNone=False)

    @staticmethod
    def snoneint(value):
        x = _coerce(value, int, AllowNone=True)
        if x == 0: return None
        return x

    def __init__(self, types=None, aliases_=None):
        super(ItemStats, self).__init__(aliases_)
        self.class_attrs = bush.game.statsTypes
        self.class_fid_attr_value = defaultdict(lambda : defaultdict(dict))
        self.attr_type = {a: getattr(self, t) for a, t
                          in bush.game.item_attr_type.iteritems()}
        self.types = set(self.class_attrs)

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        modFile = self._load_plugin(modInfo, keepAll=False)
        for top_grup_sig, attrs in self.class_attrs.iteritems():
            for record in modFile.tops[top_grup_sig].getActiveRecords():
                self.class_fid_attr_value[top_grup_sig][record.fid].update(
                    izip(attrs, (getattr(record, a) for a in attrs)))

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        modFile = self._load_plugin(modInfo)
        changed = Counter() #--changed[modName] = numChanged
        for top_grup_sig, fid_attr_value in \
                self.class_fid_attr_value.iteritems():
            attrs = self.class_attrs[top_grup_sig]
            for record in modFile.tops[top_grup_sig].getActiveRecords():
                longid = record.fid
                itemStats = fid_attr_value.get(longid,None)
                if not itemStats: continue
                oldValues = {a: getattr(record, a) for a in attrs}
                for stat_key, n_stat in itemStats.iteritems():
                    o_stat = oldValues[stat_key]
                    if isinstance(o_stat, float) or isinstance(n_stat, float):
                        # These are floats, we have to do inexact comparison
                        if not floats_equal(o_stat, n_stat):
                            break
                    elif o_stat != n_stat:
                        break
                else:
                    continue # attrs are equal, move on to next record
                for attr, value in itemStats.iteritems():
                    setattr(record,attr,value)
                record.setChanged()
                changed[longid[0]] += 1
        if changed: modFile.safeSave()
        return changed

    def _parse_line(self, csv_fields):
        """Reads stats from specified text file."""
        top_grup, modName, objectStr = csv_fields[:3]
        longid = self._coerce_fid(modName, objectStr)
        attrs = self.class_attrs[top_grup]
        attr_value = {}
        for attr, value in izip(attrs, csv_fields[3:3 + len(attrs)]):
            attr_value[attr] = self.attr_type[attr](value)
        self.class_fid_attr_value[top_grup.encode(u'ascii')][longid].update(
            attr_value)

    def writeToText(self,textPath):
        """Writes stats to specified text file."""
        class_fid_attr_value = self.class_fid_attr_value
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            def write(out, attrs, values):
                attr_type = self.attr_type
                csvFormat = []
                sstr = self.sstr
                sint = self.sint
                snoneint = self.snoneint
                sfloat = self.sfloat
                for index, attr in enumerate(attrs):
                    if attr == u'enchantPoints':
                        stype = self.snoneint
                    else:
                        stype = attr_type[attr]
                    values[index] = stype(values[index]) #sanitize output
                    if values[index] is None:
                        csvFormat.append(u'"{0[%d]}"' % index)
                    elif stype is sstr:
                        csvFormat.append(u'"{0[%d]}"' % index)
                    elif stype is sint or stype is snoneint:
                        csvFormat.append(u'"{0[%d]:d}"' % index)
                    elif stype is sfloat:
                        csvFormat.append(u'"{0[%d]:f}"' % index)
                csvFormat = u','.join(csvFormat)
                out.write(csvFormat.format(values) + u'\n')
            for group,header in bush.game.statsHeaders:
                fid_attr_value = class_fid_attr_value[group]
                if not fid_attr_value: continue
                attrs = self.class_attrs[group]
                out.write(header)
                for longid in sorted(fid_attr_value, key=lambda lid: (
                        lid, fid_attr_value[lid][u'eid'].lower())):
                    attr_value = fid_attr_value[longid]
                    out.write(
                        u'"%s","%s","0x%06X",' % (group,longid[0],longid[1]))
                    write(out, attrs, list(attr_value[a] for a in attrs))

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
                self.writeToText(outpath)
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

    def _header_row(self, __win_line_sep=u'\r\n'):
        # __win_line_sep: scripts line separator - or so we trust
        __, longid, eid = self.__writting
        header = (__win_line_sep + u';').join(
            (u'%s' % longid[0], u'0x%06X' % longid[1], eid))
        return u';%s%s' % (header, __win_line_sep)

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
    headers = (
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

    def readEffects(self, _effects):
        schoolTypeName_Number = _UsesEffectsMixin.schoolTypeName_Number
        recipientTypeName_Number = _UsesEffectsMixin.recipientTypeName_Number
        actorValueName_Number = _UsesEffectsMixin.actorValueName_Number
        effects = []
        while len(_effects) >= 13:
            _effect,_effects = _effects[1:13],_effects[13:]
            eff_name,magnitude,area,duration,range_,actorvalue,semod,seobj,\
            seschool,sevisual,seflags,sename = tuple(_effect)
            eff_name = _coerce(eff_name,unicode,AllowNone=True) #OBME not supported
            # (support requires adding a mod/objectid format to the
            # csv, this assumes all MGEFCodes are raw)
            magnitude = _coerce(magnitude,int,AllowNone=True)
            area = _coerce(area,int,AllowNone=True)
            duration = _coerce(duration,int,AllowNone=True)
            range_ = _coerce(range_,unicode,AllowNone=True)
            if range_:
                range_ = recipientTypeName_Number.get(range_.lower(),
                                                      _coerce(range_,int))
            actorvalue = _coerce(actorvalue, unicode, AllowNone=True)
            if actorvalue:
                actorvalue = actorValueName_Number.get(actorvalue.lower(),
                                                       _coerce(actorvalue,int))
            if None in (eff_name,magnitude,area,duration,range_,actorvalue):
                continue
            effect = [eff_name,magnitude,area,duration,range_,actorvalue]
            semod = _coerce(semod, unicode, AllowNone=True)
            seobj = _coerce(seobj, int, 16, AllowNone=True)
            seschool = _coerce(seschool, unicode, AllowNone=True)
            if seschool:
                seschool = schoolTypeName_Number.get(seschool.lower(),
                                                     _coerce(seschool,int))
            sevisuals = _coerce(sevisual,int,AllowNone=True) #OBME not
            # supported (support requires adding a mod/objectid format to
            # the csv, this assumes visual MGEFCode is raw)
            if sevisuals is None:
                sevisuals = _coerce(sevisual, unicode, AllowNone=True)
            else:
                sevisuals = ctypes.cast(ctypes.byref(ctypes.c_ulong(sevisuals))
                    ,ctypes.POINTER(ctypes.c_char * 4)).contents.value
            if sevisuals == u'' or sevisuals is None:
                sevisuals = null4
            sevisual = sevisuals
            seflags = _coerce(seflags, int, AllowNone=True)
            sename = _coerce(sename, unicode, AllowNone=True)
            if None in (semod,seobj,seschool,sevisual,seflags,sename):
                effect.append([])
            else:
                effect.append([(self._get_alias(semod), seobj),
                               seschool, sevisual, seflags, sename])
            effects.append(effect)
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
            efname,magnitude,area,duration,range_,actorvalue = effect[:-1]
            range_ = recipientTypeNumber_Name.get(range_,range_)
            actorvalue = actorValueNumber_Name.get(actorvalue,actorvalue)
            scripteffect = effect[-1]
            output.append(effectFormat % (
                efname,magnitude,area,duration,range_,actorvalue))
            if len(scripteffect):
                longid,seschool,sevisual,seflags,sename = scripteffect
                if sevisual == u'\x00\x00\x00\x00':
                    sevisual = u'NONE'
                seschool = schoolTypeNumber_Name.get(seschool,seschool)
                output.append(scriptEffectFormat % (
                    longid[0],longid[1],seschool,sevisual,seflags,
                    sename))
            else:
                output.append(noscriptEffectFiller)
        return u''.join(output)

#------------------------------------------------------------------------------
class SigilStoneDetails(_UsesEffectsMixin):
    """Details on SigilStones, with functions for importing/exporting
    from/to mod/text file."""
    _csv_header = (_(u'Mod Name'), _(u'ObjectIndex'), _(u'Editor Id'),
                   _(u'Name'), _(u'Model Path'), _(u'Bound Radius'),
                   _(u'Icon Path'), _(u'Script Mod Name'),
                   _(u'Script ObjectIndex'), _(u'Uses'), _(u'Value'),
                   _(u'Weight'),) + _UsesEffectsMixin.headers * 2 + (
                      _(u'Additional Effects (Same format)'),)
    _row_fmt_str = u'"%s","0x%06X","%s","%s","%s","%f","%s","%s","0x%06X",' \
                   u'"%d","%d","%f"'

    def __init__(self, types=None, aliases_=None):
        super(SigilStoneDetails, self).__init__(aliases_)
        self.fid_stats = {}
        self.types = [b'SGST']

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        fid_stats = self.fid_stats
        modFile = self._load_plugin(modInfo, keepAll=False)
        for record in modFile.tops[b'SGST'].getActiveRecords():
            effects = []
            for effect in record.effects:
                effectlist = [effect.effect_sig,effect.magnitude,effect.area,
                              effect.duration,effect.recipient,
                              effect.actorValue]
                if effect.scriptEffect:
                    effectlist.append(
                        [effect.scriptEffect.script,effect.scriptEffect.school,
                         effect.scriptEffect.visual,
                         effect.scriptEffect.flags.hostile,
                         effect.scriptEffect.full])
                else: effectlist.append([])
                effects.append(effectlist)
            fid_stats[record.fid] = [record.eid,record.full,
                                     record.model.modPath,
                                     round(record.model.modb,6),
                                     record.iconPath,record.script,record.uses,
                                     record.value,round(record.weight,6),
                                     effects]

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        fid_stats = self.fid_stats
        modFile = self._load_plugin(modInfo)
        changed = [] #eids
        for record in modFile.tops[b'SGST'].getActiveRecords():
            newStats = fid_stats.get(record.fid, None)
            if not newStats: continue
            effects = []
            for effect in record.effects:
                effectlist = [effect.effect_sig,effect.magnitude,effect.area,
                              effect.duration,effect.recipient,
                              effect.actorValue]
                if effect.scriptEffect:
                    effectlist.append([effect.scriptEffect.script,
                                       effect.scriptEffect.school,
                                       effect.scriptEffect.visual,
                                       effect.scriptEffect.flags.hostile,
                                       effect.scriptEffect.full])
                else: effectlist.append([])
                effects.append(effectlist)
            oldStats = [record.eid,record.full,record.model.modPath,
                        round(record.model.modb,6),record.iconPath,
                        record.script,record.uses,record.value,
                        round(record.weight,6),effects]
            if oldStats != newStats:
                changed.append(oldStats[0]) #eid
                record.eid,record.full,record.model.modPath,\
                record.model.modb,record.iconPath,script,record.uses,\
                record.value,record.weight,effects = newStats
                record.script = script
                record.effects = []
                for effect in effects:
                    neweffect = record.getDefault(u'effects')
                    neweffect.effect_sig,neweffect.magnitude,neweffect.area,\
                    neweffect.duration,neweffect.recipient,\
                    neweffect.actorValue,scripteffect = effect
                    if len(scripteffect):
                        scriptEffect = record.getDefault(
                            u'effects.scriptEffect')
                        script,scriptEffect.school,scriptEffect.visual,\
                        scriptEffect.flags.hostile,scriptEffect.full = \
                            scripteffect
                        scriptEffect.script = script
                        neweffect.scriptEffect = scriptEffect
                    record.effects.append(neweffect)
                record.setChanged()
        if changed: modFile.safeSave()
        return changed

    def _parse_line(self, csv_fields):
        """Imports stats from specified text file."""
        mmod, mobj, eid, full, modPath, modb, iconPath, smod, sobj, uses, \
            value, weight = csv_fields[:12]
        mid = self._coerce_fid(mmod, mobj)
        smod = _coerce(smod,unicode,AllowNone=True)
        if smod is None: sid = None
        else: sid = self._coerce_fid(smod, sobj)
        eid = _coerce(eid,unicode,AllowNone=True)
        full = _coerce(full,unicode,AllowNone=True)
        modPath = _coerce(modPath,unicode,AllowNone=True)
        modb = _coerce(modb,float)
        iconPath = _coerce(iconPath,unicode,AllowNone=True)
        uses = _coerce(uses,int)
        value = _coerce(value,int)
        weight = _coerce(weight,float)
        effects = self.readEffects(csv_fields[12:])
        self.fid_stats[mid] = [eid, full, modPath, modb, iconPath, sid, uses,
                               value, weight, effects]

    def _write_rows(self, out):
        """Exports stats to specified text file."""
        altrowFormat = u'"%s","0x%06X","%s","%s","%s","%f","%s","%s","%s",' \
                       u'"%d","%d","%f"'
        for fid, (eid, name_, modpath, modb, iconpath, scriptfid, uses,
            value, weight,effects) in _key_sort(self.fid_stats,values_dex=[0]):
            scriptfid = scriptfid or (GPath(u'None'),None)
            try:
                output = self._row_fmt_str % (
                    fid[0], fid[1], eid, name_, modpath, modb, iconpath,
                    scriptfid[0], scriptfid[1], uses, value, weight)
            except TypeError:
                output = altrowFormat % (
                    fid[0],fid[1],eid,name_,modpath,modb,iconpath,
                    scriptfid[0],scriptfid[1],uses,value,weight)
            output += self.writeEffects(effects)
            output += u'\n'
            out.write(output)

#------------------------------------------------------------------------------
class ItemPrices(_HandleAliases):
    """Function for importing/exporting from/to mod/text file only the
    value, name and eid of records."""
    item_prices_attrs = (u'value', u'eid', u'full')
    _csv_header = (_(u'Mod Name'), _(u'ObjectIndex'), _(u'Value'),
                   _(u'Editor Id'), _(u'Name'), _(u'Type'))
    _row_fmt_str = u'"%s","0x%06X",' + csvFormat(u'iss') + u',%s\n'

    def __init__(self, types=None, aliases_=None):
        super(ItemPrices, self).__init__(aliases_)
        self.class_fid_stats = bush.game.pricesTypes
        self.types = set(self.class_fid_stats)

    def readFromMod(self,modInfo):
        """Reads data from specified mod."""
        modFile = self._load_plugin(modInfo, keepAll=False)
        attrs = self.item_prices_attrs
        for top_grup_sig, fid_stats in self.class_fid_stats.iteritems():
            for record in modFile.tops[top_grup_sig].getActiveRecords():
                fid_stats[record.fid] = [getattr(record, a) for a in attrs]

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        modFile = self._load_plugin(modInfo)
        changed = Counter() #--changed[modName] = numChanged
        for top_grup_sig, fid_stats in self.class_fid_stats.iteritems():
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
        value = _coerce(value, int)
        eid = _coerce(eid, unicode, AllowNone=True)
        itm_name = _coerce(itm_name, unicode, AllowNone=True)
        top_grup = _coerce(top_grup, unicode)
        self.class_fid_stats[top_grup.encode(u'ascii')][longid] = [value, eid,
                                                                   itm_name]

    def _write_rows(self, out):
        """Writes item prices to specified text file."""
        for top_grup_sig, fid_stats in _key_sort(self.class_fid_stats):
            if not fid_stats: continue
            for fid in sorted(fid_stats,key=lambda x:(
                    fid_stats[x][1].lower(),fid_stats[x][0])):
                out.write(self._row_fmt_str % ((fid[0], fid[1]) +
                    tuple(fid_stats[fid]) + (top_grup_sig.decode(u'ascii'),)))

#------------------------------------------------------------------------------
class SpellRecords(_UsesEffectsMixin):
    """Statistics for spells, with functions for importing/exporting from/to
    mod/text file."""

    def __init__(self, types=None, aliases_=None, detailed=False):
        super(SpellRecords, self).__init__(aliases_)
        self.fid_stats = {}
        self.attrs = bush.game.spell_stats_attrs
        self.detailed = detailed
        if detailed:
            self.attrs += ( # 'effects_list' is special cased
                u'flags.noAutoCalc', u'flags.startSpell',
                u'flags.immuneToSilence', u'flags.ignoreLOS',
                u'flags.scriptEffectAlwaysApplies',
                u'flags.disallowAbsorbReflect', u'flags.touchExplodesWOTarget')
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
        self.types = [b'SPEL']

    def readFromMod(self, modInfo, __attrgetters=attrgetter_cache):
        """Reads stats from specified mod."""
        fid_stats, attrs = self.fid_stats, self.attrs
        detailed = self.detailed
        modFile = self._load_plugin(modInfo, keepAll=False)
        for record in modFile.tops[b'SPEL'].getActiveRecords():
            fid_stats[record.fid] = [__attrgetters[attr](record) for attr in
                                     attrs]
            if detailed:
                effects = []
                for effect in record.effects:
                    effectlist = [effect.effect_sig,effect.magnitude,effect.area,
                                  effect.duration,effect.recipient,
                                  effect.actorValue]
                    if effect.scriptEffect:
                        effectlist.append([effect.scriptEffect.script,
                                           effect.scriptEffect.school,
                                           effect.scriptEffect.visual,
                                           effect.scriptEffect.flags.hostile,
                                           effect.scriptEffect.full])
                    else: effectlist.append([])
                    effects.append(effectlist)
                fid_stats[record.fid].append(effects)

    def writeToMod(self, modInfo, __attrgetters=attrgetter_cache):
        """Writes stats to specified mod."""
        fid_stats, attrs = self.fid_stats, self.attrs
        detailed = self.detailed
        modFile = self._load_plugin(modInfo)
        changed = [] #eids
        for record in modFile.tops[b'SPEL'].getActiveRecords():
            newStats = fid_stats.get(record.fid, None)
            if not newStats: continue
            oldStats = [__attrgetters[attr](record) for attr in attrs]
            if detailed:
                effects = []
                for effect in record.effects:
                    effectlist = [effect.effect_sig,effect.magnitude,effect.area,
                                  effect.duration,effect.recipient,
                                  effect.actorValue]
                    if effect.scriptEffect:
                        effectlist.append([effect.scriptEffect.script,
                                           effect.scriptEffect.school,
                                           effect.scriptEffect.visual,
                                           effect.scriptEffect.flags.hostile,
                                           effect.scriptEffect.full])
                    else: effectlist.append([])
                    effects.append(effectlist)
                oldStats.append(effects)
            if oldStats != newStats:
                changed.append(oldStats[0]) #eid
                for attr, value in izip(attrs, newStats):
                    setattr_deep(record, attr, value)
                if detailed and len(newStats) > len(attrs):
                    effects = newStats[-1]
                    record.effects = []
                    for effect in effects:
                        neweffect = record.getDefault(u'effects')
                        neweffect.effect_sig,neweffect.magnitude,neweffect.area,\
                        neweffect.duration,neweffect.recipient,\
                        neweffect.actorValue,scripteffect = effect
                        if len(scripteffect):
                            scriptEffect = record.getDefault(
                                u'effects.scriptEffect')
                            script,scriptEffect.school,scriptEffect.visual,\
                            scriptEffect.flags.hostile,scriptEffect.full = \
                                scripteffect
                            scriptEffect.script = script
                            neweffect.scriptEffect = scriptEffect
                        record.effects.append(neweffect)
                record.setChanged()
        if changed: modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Imports stats from specified text file."""
        detailed, spellTypeName_Number, levelTypeName_Number = \
            self.detailed, self.spellTypeName_Number, self.levelTypeName_Number
        fid_stats = self.fid_stats
        with _CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 8 or fields[2][:2] != u'0x': continue
                if isinstance(fields[4], unicode): # Index 4 was FULL
                    group, mmod, mobj, eid, _full, cost, levelType, \
                    spellType = fields[:8]# FULL was dropped and flags added
                    spell_flags = 0
                else:
                    group, mmod, mobj, eid, cost, levelType, spell_flags = \
                        fields[:8]
                fields = fields[8:]
                if group.lower() != u'spel': continue
                mid = self._coerce_fid(mmod, mobj)
                eid = _coerce(eid, unicode, AllowNone=True)
                cost = _coerce(cost, int)
                levelType = _coerce(levelType, unicode)
                levelType = levelTypeName_Number.get(levelType.lower(),
                                                     _coerce(levelType,
                                                             int) or 0)
                spellType = _coerce(spellType, unicode)
                spellType = spellTypeName_Number.get(spellType.lower(),
                                                     _coerce(spellType,
                                                             int) or 0)
                ##: HACK, 'flags' needs to be a Flags instance on dump
                MreRecord.type_class[b'SPEL']._SpellFlags(
                    _coerce(spell_flags, int))
                if not detailed or len(fields) < 7:
                    fid_stats[mid] = [eid, cost, levelType, spellType,
                                      spell_flags]
                    continue
                mc,ss,its,aeil,saa,daar,tewt = fields[:7]
                fields = fields[7:]
                mc = _coerce(mc, bool)
                ss = _coerce(ss, bool)
                its = _coerce(its, bool)
                aeil = _coerce(aeil, bool)
                saa = _coerce(saa, bool)
                daar = _coerce(daar, bool)
                tewt = _coerce(tewt, bool)
                effects = self.readEffects(fields)
                fid_stats[mid] = [eid, cost, levelType, spellType, spell_flags,
                                  mc, ss, its, aeil, saa, daar, tewt, effects]

    @property
    def _csv_header(self):
        header = (_(u'Type'), _(u'Mod Name'), _(u'ObjectIndex'),
                  _(u'Editor Id'), _(u'Cost'), _(u'Level Type'),
                  _(u'Spell Type'), _(u'Spell Flags'))
        if self.detailed:
            header = header + (
                _(u'Manual Cost'), _(u'Start Spell'), _(u'Immune To Silence'),
                _(u'Area Effect Ignores LOS'), _(u'Script Always Applies'),
                _(u'Disallow Absorb and Reflect'), _(
                    u'Touch Explodes Without Target'),
            ) + _UsesEffectsMixin.headers * 2 + (
                         _(u'Additional Effects (Same format)'),)
        return header

    @property
    def _row_fmt_str(self):
        return u'"%s","%s","0x%06X","%s","%d","%s","%s","%d"' + (
            u',"%s","%s","%s","%s","%s","%s","%s"%s\n' if self.detailed else
            u'\n')

    def _write_rows(self, out):
        """Exports stats to specified text file."""
        detailed,fid_stats,spellTypeNumber_Name,levelTypeNumber_Name = \
            self.detailed,self.fid_stats,self.spellTypeNumber_Name, \
            self.levelTypeNumber_Name
        rowFormat = self._row_fmt_str # cache it's a property!
        for fid in sorted(fid_stats,
                          key=lambda x:(fid_stats[x][0].lower(),x[0])):
            if detailed:
                eid, cost, levelType, spellType, spell_flags, mc, ss, its, \
                aeil, saa, daar, tewt, effects = fid_stats[fid]
                levelType = levelTypeNumber_Name.get(levelType,levelType)
                spellType = spellTypeNumber_Name.get(spellType,spellType)
                output = rowFormat % (
                    u'SPEL', fid[0], fid[1], eid, cost, levelType, spellType,
                    spell_flags, mc, ss, its, aeil, saa, daar, tewt,
                    self.writeEffects(effects))
            else:
                eid, cost, levelType, spellType, spell_flags = fid_stats[fid]
                levelType = levelTypeNumber_Name.get(levelType,levelType)
                spellType = spellTypeNumber_Name.get(spellType,spellType)
                output = rowFormat % (
                    u'SPEL', fid[0], fid[1], eid, cost, levelType, spellType,
                    spell_flags)
            out.write(output)

#------------------------------------------------------------------------------
class IngredientDetails(_UsesEffectsMixin):
    """Details on Ingredients, with functions for importing/exporting
    from/to mod/text file."""
    _csv_header = (_(u'Mod Name'), _(u'ObjectIndex'), _(u'Editor Id'),
        _(u'Name'), _(u'Model Path'), _(u'Bound Radius'), _(u'Icon Path'),
        _(u'Script Mod Name'), _(u'Script ObjectIndex'), _(u'Value'),
        _(u'Weight'),) + _UsesEffectsMixin.headers * 2 + \
                  (_(u'Additional Effects (Same format)'),)
    _row_fmt_str = u'"%s","0x%06X","%s","%s","%s","%f","%s","%s","0x%06X",' \
                   u'"%d","%f"'

    def __init__(self, types=None, aliases_=None):
        super(IngredientDetails, self).__init__(aliases_)
        self.fid_stats = {}
        self.types = [b'INGR']

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        fid_stats = self.fid_stats
        modFile = self._load_plugin(modInfo, keepAll=False)
        for record in modFile.tops[b'INGR'].getActiveRecords():
            effects = []
            for effect in record.effects:
                effectlist = [effect.effect_sig,effect.magnitude,effect.area,
                              effect.duration,effect.recipient,
                              effect.actorValue]
                if effect.scriptEffect:
                    effectlist.append(
                        [effect.scriptEffect.script,effect.scriptEffect.school,
                         effect.scriptEffect.visual,
                         effect.scriptEffect.flags.hostile,
                         effect.scriptEffect.full])
                else: effectlist.append([])
                effects.append(effectlist)
            fid_stats[record.fid] = [record.eid,record.full,
                                     record.model.modPath,
                                     round(record.model.modb,6),
                                     record.iconPath,record.script,
                                     record.value,round(record.weight,6),
                                     effects]

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        fid_stats = self.fid_stats
        modFile = self._load_plugin(modInfo)
        changed = [] #eids
        for record in modFile.tops[b'INGR'].getActiveRecords():
            newStats = fid_stats.get(record.fid, None)
            if not newStats: continue
            effects = []
            for effect in record.effects:
                effectlist = [effect.effect_sig,effect.magnitude,effect.area,
                              effect.duration,effect.recipient,
                              effect.actorValue]
                if effect.scriptEffect:
                    effectlist.append([effect.scriptEffect.script,
                                       effect.scriptEffect.school,
                                       effect.scriptEffect.visual,
                                       effect.scriptEffect.flags.hostile,
                                       effect.scriptEffect.full])
                else: effectlist.append([])
                effects.append(effectlist)
            oldStats = [record.eid,record.full,record.model.modPath,
                        round(record.model.modb,6),record.iconPath,
                        record.script, record.value,
                        round(record.weight,6),effects]
            if oldStats != newStats:
                changed.append(oldStats[0]) #eid
                record.eid,record.full,record.model.modPath,\
                record.model.modb,record.iconPath,script,record.value,\
                record.weight,effects = newStats
                record.script = script
                record.effects = []
                for effect in effects:
                    neweffect = record.getDefault(u'effects')
                    neweffect.effect_sig,neweffect.magnitude,neweffect.area,\
                    neweffect.duration,neweffect.recipient,\
                    neweffect.actorValue,scripteffect = effect
                    if len(scripteffect):
                        scriptEffect = record.getDefault(
                            u'effects.scriptEffect')
                        script,scriptEffect.school,scriptEffect.visual,\
                        scriptEffect.flags.hostile.hostile,scriptEffect.full\
                            = scripteffect
                        scriptEffect.script = script
                        neweffect.scriptEffect = scriptEffect
                    record.effects.append(neweffect)
                record.setChanged()
        if changed: modFile.safeSave()
        return changed

    def _parse_line(self, csv_fields):
        mmod, mobj, eid, full, modPath, modb, iconPath, smod, sobj, value,\
        weight = csv_fields[:11]
        mid = self._coerce_fid(mmod, mobj)
        smod = _coerce(smod, unicode, AllowNone=True)
        if smod is None: sid = None
        else: sid = self._coerce_fid(smod, sobj)
        eid = _coerce(eid, unicode, AllowNone=True)
        full = _coerce(full, unicode, AllowNone=True)
        modPath = _coerce(modPath, unicode, AllowNone=True)
        modb = _coerce(modb, float)
        iconPath = _coerce(iconPath, unicode, AllowNone=True)
        value = _coerce(value, int)
        weight = _coerce(weight, float)
        effects = self.readEffects(csv_fields[11:])
        self.fid_stats[mid] = [eid,full, modPath, modb, iconPath, sid, value,
                               weight, effects]

    def _write_rows(self, out):
        """Exports stats to specified text file."""
        altrowFormat = u'"%s","0x%06X","%s","%s","%s","%f","%s","%s","%s",' \
                       u'"%d","%f"'
        for fid in sorted(self.fid_stats,
                          key=lambda x: self.fid_stats[x][0].lower()):
            eid,name_,modpath,modb,iconpath,scriptfid,value,weight, \
            effects = self.fid_stats[fid]
            scriptfid = scriptfid or (GPath(u'None'), None)
            try:
                output = self._row_fmt_str % (
                    fid[0],fid[1],eid,name_,modpath,modb,iconpath,
                    scriptfid[0],scriptfid[1],value,weight)
            except TypeError:
                output = altrowFormat % (
                    fid[0],fid[1],eid,name_,modpath,modb,iconpath,
                    scriptfid[0],scriptfid[1],value,weight)
            output += self.writeEffects(effects)
            output += u'\n'
            out.write(output)
