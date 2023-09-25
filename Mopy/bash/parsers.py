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
"""Parsers can read and write information from and to mods and from and to CSV
files. They store the read information in an internal representation, which
means that they can be used to export and import information from and to mods.
They are also used by some patchers in order to not duplicate the work that
has to be done when reading mods.
However, not all parsers fit this pattern - some have to read mods twice,
others barely even fit into the pattern at all (e.g. FidReplacer)."""
from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from functools import partial
from operator import itemgetter
from typing import get_type_hints

from . import bush, load_order
from .balt import Progress
from .bass import dirs, inisettings
from .bolt import DefaultFNDict, FName, attrgetter_cache, deprint, dict_sort, \
    int_or_none, setattr_deep, sig_to_str, str_or_none, str_to_sig
from .brec import FormId, RecordType, attr_csv_struct, null3
from .mod_files import LoadFactory, ModFile

##: In 311+, all of the BOM garbage (utf-8-sig) should go - that means adding
# backwards compatibility code. See TrustedBinariesPage._import_lists, we could
# break that out into a bolt tool for reading an 'optional-BOM UTF-8' file

# Utils
def _key_sort(di, fid_eid=False, values_key=(), by_value=False):
    """Adapted to current uses - values_key is eid or eid and some numerical
    field, fid_eid if True will sort by the FormId.mod_fn key then by eid."""
    if fid_eid: # values_key is eid here
        key_f = lambda k: (k.mod_fn, di[k].get('eid', '').lower())
    elif values_key:
        key_f = lambda k: tuple(
            (di[k].get(v) or '').lower() if v == 'eid' else di[k][v] for v in
            values_key)
    elif by_value:
        key_f = lambda k: di[k].lower()
    else:
        raise ValueError('One of fid_eid, values_key, by_value must be set')
    for fid_key in sorted(di, key=key_f):
        yield fid_key, di[fid_key]

def _fid_str(fid_tuple):
    return f'"{fid_tuple.mod_fn}","0x{fid_tuple.object_dex:06X}"'

#------------------------------------------------------------------------------
class _TextParser(object):
    """Basic read/write csv functionality - ScriptText handles script files
    not csvs though."""

    def _coerce_fid(self, modname, hex_fid):
        """Create a long formid from a unicode modname and a unicode
        hexadecimal - it will blow with ValueError if hex_fid is not
        in the form 0x123abc."""
        if not hex_fid.startswith(u'0x'):
            raise ValueError
        # We checked that hex_fid starts with 0x, so this must be hex
        return FormId.from_tuple((FName(modname), int(hex_fid, 16)))

    def write_text_file(self, textPath):
        """Export ____ to specified text file. You must override _write_rows.
        """
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            self._header_row(out)
            self._write_rows(out)

    def _write_rows(self, out):
        raise NotImplementedError(f'{type(self)} must implement _write_rows')

    def _header_row(self, out):
        raise NotImplementedError(f'{type(self)} must implement _header_row')

    # Load plugin -------------------------------------------------------------
    def _load_plugin(self, mod_info, keepAll=False, target_types=None,
                     load_fact=None):
        """Load the specified record types in the specified ModInfo and
        return the result.

        :param mod_info: The ModInfo object to read.
        :param target_types: An iterable yielding record signatures to load.
        :return: An object representing the loaded plugin."""
        mod_file = ModFile(mod_info, load_fact or self._load_factory(
            keepAll, target_types))
        mod_file.load_plugin()
        return mod_file

    def _load_factory(self, keepAll, target_types=None):
        return LoadFactory(keepAll, by_sig=target_types or self._parser_sigs)

    # Write plugin ------------------------------------------------------------
    _changed_type = dict # used in writeToMod to report changed records
    def writeToMod(self,modInfo):
        """Hasty writeToMod implementation - export id_stored_data to specified
        mod.

        :param modInfo: The ModInfo instance to write to.
        :return: info on number of changed records, usually per record type."""
        modFile = self._load_plugin(modInfo, keepAll=True,
                                    target_types=self.id_stored_data)
        changed_stats = self._changed_type()
        # Check which record types makes any sense to patch
        block_to_data = [(block, stored_info) for sig, stored_info in
                         self.id_stored_data.items() if stored_info and (
                             block := modFile.tops.get(sig))]
        # We know that the loaded mod only has the tops loaded that we need
        for rec_block, stored_rec_info in block_to_data:
            for rfid, record in rec_block.iter_present_records():
                self._check_write_record(rfid, record, stored_rec_info,
                                         changed_stats)
        changed_stats = self._additional_processing(changed_stats, modFile)
        # Check if we've actually changed something, otherwise skip saving
        if changed_stats: modFile.safeSave()
        return changed_stats

    def _additional_processing(self, changed_stats, modFile):
        return changed_stats

    def _check_write_record(self, rfid, record, stored_rec_info,
                            changed_stats):
        """Check if we have stored data for this record usually based on its
        fid."""
        stored_data = stored_rec_info.get(rfid)
        if stored_data:
            self._write_record(record, stored_data, changed_stats)

class CsvParser(_TextParser):
    _csv_header = ()

    # Write csv functionality -------------------------------------------------
    def _header_row(self, out):
        out.write(u'"%s"\n' % u'","'.join(self._csv_header))

    def _write_rows(self, out):
        """Writes rows to csv text file."""
        for top_grup_sig, id_data in dict_sort(self.id_stored_data):
            if not (section_data := self._write_section(
                    top_grup_sig, id_data, out)): continue
            for lfid, stored_data in self._row_sorter(id_data):
                row = self._row_out(lfid, stored_data, *section_data)
                if row and not row.isspace():
                    out.write(row)

    def _write_section(self, top_grup_sig, id_data, out):
        return bool(id_data) and [sig_to_str(top_grup_sig)]

    def _row_out(self, lfid, stored_data, top_grup):
        raise NotImplementedError(f'{type(self)} must implement _row_out')

    # Read csv functionality --------------------------------------------------
    def read_csv(self, csv_path):
        """Reads information from the specified CSV file and stores the result
        in id_stored_data. You must override _parse_line for this method to
        work. ScriptText is a special case.

        :param csv_path: The path to the CSV file that should be read."""
        with open(csv_path, encoding='utf-8-sig') as ins:
            first_line = ins.readline()
            ##: drop 'excel-tab' format and delimiter = ';'? backwards compat?
            excel_fmt = 'excel-tab' if '\t' in first_line else 'excel'
            ins.seek(0)
            if excel_fmt == 'excel':
                delimiter = ';' if ';' in first_line else ','
                reader = csv.reader(ins, excel_fmt, delimiter=delimiter)
            else:
                reader = csv.reader(ins, excel_fmt)
            for fields in reader:
                try:
                    self._parse_line(fields)
                except (IndexError, ValueError, TypeError):
                    """TypeError/ValueError trying to unpack None/few values"""

    def _parse_line(self, csv_fields):
        """Parse the specified CSV line and update the parser's instance
        id_stored_data - both id and stored_data vary in type and meaning.

        :param csv_fields: A line in a CSV file, already split into fields."""
        raise NotImplementedError(f'{type(self)} must implement _parse_line')

    def _update_from_csv(self, top_grup_sig, csv_fields, index_dict=None):
        return RecordType.sig_to_class[top_grup_sig].parse_csv_line(csv_fields,
            index_dict or self._attr_dex, reuse=index_dict is not None)

class _HandleAliases(CsvParser):
    """WIP aliases handling."""
    _parser_sigs = [] # record signatures this parser recognises
    # get (by index) the csv fields that will create the id in id_stored_data
    _key2_getter = itemgetter(0, 1)
    # the index of the csv field that contains the group record signature
    _grup_index = None
    # the type of the values of id_stored_data
    _nested_type = dict
    _id_data_type: defaultdict

    def __init__(self, aliases_, called_from_patcher=False):
        # Automatically set in _parse_csv_sources to the patch file's aliases -
        # used if the Aliases Patcher has been enabled
        self.aliases = aliases_ or {} # type: dict
        # Set to True when called by a patcher - can be used to alter stored
        # data format when reading from a csv - could be in a subclass
        self._called_from_patcher = called_from_patcher # avoid using this!
        # (Mostly) map record sigs to dicts that map long fids to stored info
        # May have been retrieved from mod in second pass, or from a CSV file.
        # Need __class__ access to get a function rather than a bound method
        self.id_stored_data = get_type_hints(self.__class__)['_id_data_type'](
            self.__class__._nested_type)

    def _coerce_fid(self, modname, hex_fid):
        """Version of _coerce_fid that also checks for aliases of modname."""
        return super()._coerce_fid(self.aliases.get(modname, modname), hex_fid)

    def _parse_line(self, csv_fields):
        key1 = self._key1(csv_fields)
        key2 = self._key2(csv_fields)
        value = self._update_from_csv(key1, csv_fields)
        if value is not None:
            self.id_stored_data[key1][key2] = value
        return key1, key2

    def _key1(self, csv_fields):
        if self._grup_index is not None:
            top_grup_sig = str_to_sig(csv_fields[self._grup_index])
        else:
            top_grup_sig = self._parser_sigs[0] # one rec type
        return top_grup_sig

    def _key2(self, csv_fields):
        return self._coerce_fid(*self._key2_getter(csv_fields))

    def readFromMod(self, modInfo):
        """Hasty readFromMod implementation."""
        modFile = self._load_plugin(modInfo)
        for top_grup_sig, typeBlock in modFile.iter_tops(self._parser_sigs):
            id_data = self.id_stored_data[top_grup_sig]
            for rfid, record in typeBlock.iter_present_records():
                self._read_record(record, id_data)

    def _read_record(self, record, id_data, __attrgetters=attrgetter_cache):
        id_data[record.fid] = {att: __attrgetters[att](record) for att in
                               self._attr_dex}

# TODO(inf) Once refactoring is done, we could easily take in Progress objects
#  for more accurate progress bars when importing/exporting
class _AParser(_HandleAliases):
    """Base class for parsers manipulating array record elements (factions and
    relations). Behaves like a merger when reading csvs, keeping all the csv
    entries (last item wins) and exporting to mods additions and changes.

    Reading from mods:
     - This is the most complex part of this design - we offer up to two
       passes, where the first pass reads a mod and all its masters, but does
       not offer fine-grained filtering of the read information. It is mapped
       by long FormID and stored in id_context. You will have to set
       _fp_types appropriately and override _read_record_fp to use this pass.
     - The second pass updates id_stored_data. You need to set _sp_types and
       override _is_record_useful and _read_record_sp to use this pass.
       `id_stored_data` indexes record information by record group and FormID -
       this information being usually the values for certain record attributes.
     - If you want to skip either pass, just leave _fp_types / _sp_types
       empty."""
    _nested_type = lambda: defaultdict(dict)
    _target_array = None # target record array attribute
    array_item_attrs = None # the attributes this parser needs from array elements

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
        super(_AParser, self).__init__(aliases_, called_from_patcher)

    def _row_sorter(self, rows):
        id_eid_ = self.id_context
        for k in sorted(rows, key=lambda k_: (id_eid_.get(k_) or '').lower()):
            yield k, (rows[k], id_eid_[k])

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
            for block_type, rec_block in mod_to_read.iter_tops(self._fp_types):
                for rfid, record in rec_block.iter_present_records():
                    self.id_context[rfid] = self._read_record_fp(record)
            self._fp_mods.add(mod_to_read.fileInfo.fn_key)
        # Process the mod's masters first, but see if we need to sort them
        master_names = loaded_mod.tes4.masters
        if self._needs_fp_master_sort:
            master_names = load_order.get_ordered(master_names)
        for mod_name in master_names:
            if mod_name in self._fp_mods: continue
            _fp_loop(self._load_plugin(bosh.modInfos[mod_name],
                                       target_types=self._fp_types))
        # Finally, process the mod itself
        if loaded_mod.fileInfo.fn_key in self._fp_mods: return
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
        raise NotImplementedError

    # Reading from plugin - second pass
    def _read_plugin_sp(self, loaded_mod):
        """Performs a second pass of reading on the specified plugin, but not
        its masters. Results are stored in id_stored_data.

        :param loaded_mod: The loaded mod to read from."""
        for rec_type, rec_block in loaded_mod.iter_tops(self._sp_types):
            for rfid, record in rec_block.iter_present_records():
                # Check if we even want this record first
                if self._is_record_useful(record):
                    self.id_stored_data[rec_type][rfid] = \
                        self._read_record_sp(record)
                    # Check if we need to follow up on the first pass info
                    if self._context_needs_followup:
                        self.id_context[rfid] = self._read_record_fp(record)

    def _is_record_useful(self, record):
        """The parser should check if the specified record would be useful to
        it during the second pass, i.e. if we should store information for it.

        :param record: The record in question.
        :return: True if information for the record should be stored."""
        raise NotImplementedError

    def _read_record_sp(self, record):
        """Performs the actual parser-specific second pass code on the
        specified record. Treat this as a kind of lambda for a map call over
        all records matching the _sp_types. Unless _get_cur_record_info is
        overriden, this will also be used during writing to compare new and old
        record information.

        :param record: The record to read.
        :return: Whatever representation you want to convert this record
            into."""
        raise NotImplementedError

    # Note the non-PEP8 names - those point to refactored pseudo-API methods
    def readFromMod(self, mod_info):
        """Asks this parser to read information from the specified ModInfo
        instance. Executes the needed passes and stores extracted information
        in id_context and / or id_stored_data. Note that this does not
        automatically clear id_stored_data to allow combining multiple sources.

        :param mod_info: The ModInfo instance to read from."""
        self._current_mod = mod_info.fn_key
        # Check if we need to read at all
        a_types = self.all_types
        if not a_types:
            # We need to unset _current_mod since we're no longer loading a mod
            self._current_mod = None
            return
        # Load mod_info once and for all, then execute every needed pass
        loaded_mod = self._load_plugin(mod_info, target_types=a_types)
        if self._fp_types:
            self._read_plugin_fp(loaded_mod)
        if self._sp_types:
            self._read_plugin_sp(loaded_mod)
        # We need to unset _current_mod since we're no longer loading a mod
        self._current_mod = None

    # Writing to plugins
    @classmethod
    def get_empty_object(cls, record, faction_fid):
        """Get an empty MelObject to add to the record array."""
        target_entry = record.getDefault(cls._target_array)
        target_entry.faction = faction_fid
        return target_entry

    _changed_type = Counter
    def _write_record(self, record, new_data, changed_stats):
        """Asks this parser to write its stored information to the specified
        record."""
        cur_data = self._read_record_sp(record)
        if new_data != cur_data:
            # It's different, ask the parser to write it out
            added_changed = set(new_data.items()) - set(cur_data.items())
            for faction_fid, item_values in added_changed:
                # See if this is a new item or a change to an existing one
                array = attrgetter_cache[self._target_array](record)
                for entry in array:
                    if faction_fid == entry.faction:
                        # Just a change, change the attributes
                        target_entry = entry
                        break
                else:
                    # It's an addition, we need to make a new object
                    target_entry = self.get_empty_object(record, faction_fid)
                    array.append(target_entry)
                # Actually write out the attributes from new_data
                if isinstance(self.array_item_attrs, str):
                    setattr(target_entry, self.array_item_attrs, item_values)
                else:
                    for rel_attr, rel_val in zip(self.array_item_attrs,
                                                 item_values):
                        setattr(target_entry, rel_attr, rel_val)
            record.setChanged()
            changed_stats[record.rec_sig] += 1

    # Other API
    @property
    def all_types(self):
        """Returns a set of all record types that this parser requires."""
        return set(self._fp_types) | set(self._sp_types)

    @property
    def _parser_sigs(self):
        """Returns a set of all record types that this parser requires."""
        return set(self._fp_types) | set(self._sp_types)

class ActorFactions(_AParser):
    """Parses factions from NPCs and Creatures (in games that have those). Can
    read and write both plugins and CSV, and uses a single pass if called from
    a patcher, but two passes if called from a link."""
    _csv_header = (_('Type'), _('Actor Eid'), _('Actor Mod'),
                   _('Actor Object'), _('Faction Eid'), _('Faction Mod'),
                   _('Faction Object'), _('Rank'))
    _grup_index = 0
    _key2_getter = itemgetter(2, 3)
    _target_array = 'factions'
    array_item_attrs = 'rank'

    def __init__(self, aliases_=None, called_from_patcher=False):
        super().__init__(aliases_, called_from_patcher)
        a_types = bush.game.actor_types
        # We don't need the first pass if we're used by the parser
        self._fp_types = () if called_from_patcher else (*a_types, b'FACT')
        self._sp_types = a_types

    def _read_record_fp(self, record):
        return record.eid

    def _is_record_useful(self, record):
        return bool(record.factions)

    def _read_record_sp(self, record):
        if self._called_from_patcher: # only used as a csv reader in patcher
            raise NotImplementedError
        return {f.faction: f.rank for f in record.factions} # last mod wins

    @classmethod
    def get_empty_object(cls, record, faction_fid):
        """We also need to set the (by default None) unused1 MelStruct
        element."""
        target_entry = super().get_empty_object(record, faction_fid)
        if hasattr(target_entry, 'unused1'): # Gone in FO4
            ##: in Oblivion.esm I get {b'NL\x00', b'IFZ', None}
            target_entry.unused1 = b'ODB'
        return target_entry

    def _update_from_csv(self, top_grup_sig, csv_fields, index_dict=None):
        lfid = self._coerce_fid(csv_fields[5], csv_fields[6])
        rank = int(csv_fields[7])
        aid = self._key2(csv_fields) ##: pass key2 ?
        self.id_stored_data[top_grup_sig][aid][lfid] = rank
        return None  # block updating id_stored_data in _parse_line

    def _row_out(self, aid, stored_data, top_grup):
        """Exports faction data to specified text file."""
        factions, actorEid = stored_data
        return '\n'.join([f'"{top_grup}","{actorEid}",{_fid_str(aid)},'
                          f'"{fac_eid}",{_fid_str(fa)},"{rank}"' for
            fa, (rank, fac_eid) in self._row_sorter(factions)]) + '\n'

#------------------------------------------------------------------------------
class ActorLevels(_HandleAliases):
    """id_stored_data differs here - _key1 is a mod:
    id_stored_data[fn_mod][longid] = levels_dict"""
    _csv_header = (
        _('Source Mod'), _('Actor Eid'), _('Actor Mod'), _('Actor Object'),
        _('Offset'), _('CalcMin'), _('CalcMax'), _('Old IsPCLevelOffset'),
        _('Old Offset'), _('Old CalcMin'), _('Old CalcMax'))
    _parser_sigs = [b'NPC_']
    _attr_dex = {'eid': 1, 'level_offset': 4, 'calc_min_level': 5,
                 'calc_max_level': 6}
    _key2_getter = itemgetter(2, 3)
    _row_sorter = partial(_key_sort, fid_eid=True)
    _id_data_type: DefaultFNDict

    def __init__(self, aliases_=None, called_from_patcher=False):
        super(ActorLevels, self).__init__(aliases_, called_from_patcher)
        self.gotLevels = set()
        self._skip_mods = {'none', bush.game.master_file.lower()}

    def readFromMod(self,modInfo):
        """Imports actor level data from the specified mod and its masters."""
        from . import bosh
        mod_id_levels, gotLevels = self.id_stored_data, self.gotLevels
        load_f = self._load_factory(keepAll=False)
        for modName in (*modInfo.masterNames, modInfo.fn_key):
            if modName in gotLevels: continue
            modFile = self._load_plugin(bosh.modInfos[modName],
                                        load_fact=load_f)
            for rfid, record in modFile.tops[b'NPC_'].iter_present_records():
                items = zip(
                    ('eid', 'npc_flags.pc_level_offset', 'level_offset',
                     'calc_min_level', 'calc_max_level'),
                    (record.eid, bool(record.npc_flags.pc_level_offset),
                     record.level_offset, record.calc_min_level,
                     record.calc_max_level))
                mod_id_levels[modName][rfid] = dict(items)
            gotLevels.add(modName)

    def writeToMod(self, modInfo):
        """Exports actor levels to specified mod."""
        id_levels = self.id_stored_data.get(modInfo.fn_key,
            self.id_stored_data.get('Unknown', None))
        if id_levels:
            # pretend we are a normal parser
            real = self.id_stored_data
            self.id_stored_data = {b'NPC_': id_levels}
            changed_stats = super().writeToMod(modInfo)
            self.id_stored_data = real
            return changed_stats
        return 0

    _changed_type = list
    def _write_record(self, record, levels, changed_stats, __getter=itemgetter(
        'level_offset', 'calc_min_level', 'calc_max_level')):
        got_lo, got_min_lv, got_max_lv = __getter(levels)
        if ((record.level_offset, record.calc_min_level,
             record.calc_max_level) != (got_lo, got_min_lv, got_max_lv)):
            record.level_offset = got_lo
            record.calc_min_level = got_min_lv
            record.calc_max_level = got_max_lv
            record.setChanged()
            changed_stats.append(record.fid)

    def _additional_processing(self, changed_stats, modFile):
        return len(changed_stats)

    def _update_from_csv(self, top_grup_sig, csv_fields, index_dict=None):
        attr_dex = super()._update_from_csv(b'NPC_', csv_fields)
        attr_dex['npc_flags.pc_level_offset'] = True
        return attr_dex

    def _key1(self, csv_fields: list[str]) -> str:
        if (source := csv_fields[0]).lower() in self._skip_mods:
            raise ValueError # exit _parse_line
        return source

    def _key2(self, csv_fields):
        fidMod = csv_fields[2]
        if fidMod.lower() == u'none':
            raise ValueError # exit _parse_line
        return super(ActorLevels, self)._key2(csv_fields)

    def _write_section(self, fn_mod, id_data, out):
        return ((fn_mod != (bg_mf := bush.game.master_file)) and [fn_mod,
            self.id_stored_data[bg_mf]])

    def _row_out(self, longfid, di, fn_mod, obId_levels, *,
            __getter=itemgetter(
                'eid', 'npc_flags.pc_level_offset', 'level_offset',
                'calc_min_level', 'calc_max_level')):
        """Export NPC level data to specified text file."""
        eid, isOffset, offset, row_calc_min, row_calc_max = __getter(di)
        if isOffset:
            out = f'"{fn_mod}","{eid}",{_fid_str(longfid)},"{offset:d}",' \
                  f'"{row_calc_min:d}","{row_calc_max:d}"'
            oldLevels = obId_levels.get(longfid, None)
            if oldLevels:
                oldEid, wasOffset, oldOffset, oldCalcMin, oldCalcMax = \
                    __getter(oldLevels)
                out += (f',"{wasOffset:d}","{oldOffset:d}","{oldCalcMin:d}",'
                        f'"{oldCalcMax:d}"')
            else:
                out += ',,,,'
            return out + '\n'

#------------------------------------------------------------------------------
class EditorIds(_HandleAliases):
    """Editor IDs for records, with functions for importing/exporting
    from/to mod/text file: id_stored_data[top_grup_sig][longid] = eid"""
    _csv_header = (_('Type'), _('Mod Name'), _('ObjectIndex'), _('Editor Id'))
    _key2_getter = itemgetter(1, 2)
    _grup_index = 0
    _attr_dex = {u'eid': 3}
    _row_sorter = partial(_key_sort, by_value=True)

    def __init__(self, aliases_=None, questionableEidsSet=None,
                 badEidsList=None, called_from_patcher=False):
        super(EditorIds, self).__init__(aliases_, called_from_patcher)
        self.badEidsList = badEidsList
        self.questionableEidsSet = questionableEidsSet
        #--eid = eids[type][longid]
        self.old_new = {}
        self._parser_sigs = set(RecordType.simpleTypes)

    def _read_record(self, record, id_data):
        if record.eid: id_data[record.fid] = record.eid

    def _additional_processing(self, changed_stats, modFile):
        #--Update scripts
        old_new = dict(self.old_new)
        old_new.update({oldEid.lower(): newEid for oldEid, newEid in changed_stats})
        changed_stats.extend(self.changeScripts(modFile, old_new))
        return changed_stats

    _changed_type = list
    def _write_record(self, record, newEid, changed_stats):
        oldEid = record.eid
        if oldEid and newEid != oldEid:
            record.eid = newEid
            record.setChanged()
            changed_stats.append((oldEid, newEid))

    def changeScripts(self,modFile,old_new):
        """Changes scripts in modfile according to changed."""
        changed_stats = []
        if not old_new: return changed_stats
        reWord = re.compile(r'\w+')
        def subWord(ma_word):
            word = ma_word.group(0)
            newWord = old_new.get(word.lower())
            if not newWord:
                return word
            else:
                return newWord
        #--Scripts
        scpt_recs = modFile.tops[b'SCPT'].iter_present_records()
        scpt_recs = [(r.eid, r) for _gkey, r in scpt_recs]
        for reid, script_rec in sorted(scpt_recs, key=itemgetter(0)): # by eid
            if not script_rec.script_source: continue
            newText = reWord.sub(subWord,script_rec.script_source)
            if newText != script_rec.script_source:
                # header = u'\r\n\r\n; %s %s\r\n' % (script_rec.eid,u'-' * (77 -
                # len(script_rec.eid))) # unused - bug ?
                script_rec.script_source = newText
                script_rec.setChanged()
                changed_stats.append((_('Script'), reid))
        #--Quest Scripts
        qust_recs = modFile.tops[b'QUST'].iter_present_records()
        qust_recs = [(r.eid, r) for _gkey, r in qust_recs]
        for reid, quest in sorted(qust_recs, key=itemgetter(0)): # sort by eid
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
                changed_stats.append((_('Quest'), reid))
                quest.setChanged()
        #--Done
        return changed_stats

    def _parse_line(self, csv_fields):
        top_grup_sig, longid = super(EditorIds, self)._parse_line(csv_fields)
        #--Explicit old to new def? (Used for script updating.)
        if len(csv_fields) > 4:
            self.old_new[csv_fields[4].lower()] = \
                self.id_stored_data[top_grup_sig][longid]

    def _update_from_csv(self, top_grup_sig, csv_fields, index_dict=None, *,
                         __reValidEid=re.compile('^[a-zA-Z0-9]+$'),
                         __reGoodEid=re.compile('^[a-zA-Z]')):
        eid = super()._update_from_csv(top_grup_sig, csv_fields, index_dict)[
            'eid']
        if not __reValidEid.match(eid):
            if self.badEidsList is not None:
                self.badEidsList.append(eid)
            raise ValueError # exit _parse_line
        if self.questionableEidsSet is not None and not __reGoodEid.match(eid):
            self.questionableEidsSet.add(eid)
        return eid

    def _row_out(self, lfid, stored_data, top_grup):
        return f'"{top_grup}",{_fid_str(lfid)},"{stored_data}"\n'

#------------------------------------------------------------------------------
class FactionRelations(_AParser):
    """Parses the relations between factions. Can read and write both plugins
    and CSV, and uses two passes to do so."""
    array_item_attrs = bush.game.relations_attrs[1:] # chop off 'faction'
    _target_array = 'relations'

    def __init__(self, aliases_=None, called_from_patcher=False):
        super(FactionRelations, self).__init__(aliases_, called_from_patcher)
        self._fp_types = () if self._called_from_patcher else (b'FACT',)
        self._sp_types = (b'FACT',)
        self._needs_fp_master_sort = True
        self._csv_header = (_('Main Eid'), _('Main Mod'), _('Main Object'),
            _('Other Eid'), _('Other Mod'), _('Other Object')) + tuple(
            attr_csv_struct[a][1] for a in self.__class__.array_item_attrs)

    def _read_record_fp(self, record):
        # Gather the latest value for the EID matching the FID
        return record.eid

    def _is_record_useful(self, _record):
        # We want all records - even ones that have no relations, since those
        # may have still deleted original relations.
        return True

    def _read_record_sp(self, record, *, __attrgetters=tuple(
            attrgetter_cache[a] for a in ('faction', *array_item_attrs))):
        # Look if we already have relations and base ourselves on those,
        # otherwise make a new list
        relations = self.id_stored_data[b'FACT'][record.fid]
        # Merge added relations, preserve changed relations
        for relation in record.relations:
            other_fac, *rel_attrs = (a(relation) for a in __attrgetters)
            relations[other_fac] = rel_attrs
        return relations

    def _parse_line(self, csv_fields):
        _med, mmod, mobj, _oed, omod, oobj = csv_fields[:6]
        mid = self._coerce_fid(mmod, mobj)
        oid = self._coerce_fid(omod, oobj)
        self.id_stored_data[b'FACT'][mid][oid] = tuple(csv_fields[6:])

    def _row_out(self, lfid, stored_data, top_grup):
        """Exports faction relations to specified text file."""
        rel, main_eid = stored_data
        return '\n'.join(['"%s",%s,"%s",%s,%s' % (
            main_eid, _fid_str(lfid), oth_eid, _fid_str(oth_fid), ','.join(
                attr_csv_struct[a][2](x) for a, x in
                zip(self.__class__.array_item_attrs, relation_obj)))
        for oth_fid, (relation_obj, oth_eid) in self._row_sorter(rel)]) + '\n'

#------------------------------------------------------------------------------
class FidReplacer(_HandleAliases):
    """Replaces one set of fids with another."""

    def __init__(self, aliases_=None, called_from_patcher=False):
        super(FidReplacer, self).__init__(aliases_, called_from_patcher)
        # simpleTypes are not defined when parsers are imported in
        # game/oblivion/patcher/preservers.py:30
        self._parser_sigs = RecordType.simpleTypes
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
        modFile = self._load_plugin(modInfo, keepAll=True)
        # Create filtered versions of our mappings
        masters_list = set(modFile.augmented_masters())
        filt_fids = {oldId for oldId in self.old_eid if
                     oldId[0] in masters_list}
        filt_fids.update(newId for newId in self.new_eid
                         if newId[0] in masters_list)
        old_eid_filtered = {oldId: eid for oldId, eid
                            in self.old_eid.items() if oldId in filt_fids}
        new_eid_filtered = {newId: eid for newId, eid
                            in self.new_eid.items() if newId in filt_fids}
        old_new_filtered = {oldId: newId for oldId, newId
                            in self.old_new.items()
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
        for _sig, top_block in modFile.iter_tops(self._parser_sigs):
            for rfid, record in top_block.iter_present_records():
                if changeBase: record.fid = swapper(rfid)
                record.mapFids(swapper, save_fids=True)
                record.setChanged()
        #--Done
        if not old_count: return False
        modFile.safeSave()
        entries = [(count, old_eid_filtered[oldId],
                    new_eid_filtered[old_new_filtered[oldId]])
                   for oldId, count in old_count.items()]
        entries.sort(key=itemgetter(1))
        return '\n'.join(['%3d %s >> %s' % entry for entry in entries])

#------------------------------------------------------------------------------
class FullNames(_HandleAliases):
    """Names for records, with functions for importing/exporting from/to
    mod/text file: id_stored_data[top_grup_sig][longid] = (eid, name)"""
    _csv_header = (_('Type'), _('Mod Name'), _('ObjectIndex'), _('Editor Id'),
                   _('Name'))
    _key2_getter = itemgetter(1, 2)
    _grup_index = 0
    _row_sorter = partial(_key_sort, fid_eid=True)

    def __init__(self, aliases_=None, called_from_patcher=False):
        super(FullNames, self).__init__(aliases_, called_from_patcher)
        self._parser_sigs = bush.game.names_types
        self._attr_dex = {u'full': 4} if self._called_from_patcher else {
            u'eid': 3, u'full': 4}

    def _update_from_csv(self, top_grup_sig, csv_fields, index_dict=None):
        if csv_fields[-1] == 'NO NAME':
            raise ValueError # Leftover from pre-310 days, just skip it
        return super()._update_from_csv(top_grup_sig, csv_fields, index_dict)

    def _read_record(self, record, id_data, __attrgetters=attrgetter_cache):
        super()._read_record(record, id_data)
        rec_data = id_data[record.fid]
        if not rec_data['full']: # No FULL -> skip this record
            del id_data[record.fid]

    def _write_record(self, record, di, changed_stats):
        old_full = record.full
        new_full = di['full']
        if new_full != old_full:
            record.full = new_full
            record.setChanged()
            changed_stats[di['eid']] = (old_full, new_full)

    def _row_out(self, lfid, stored_data, top_grup):
        return ('"%s",%s,"%s","%s"\n' % (
            top_grup, _fid_str(lfid), stored_data['eid'],
            stored_data['full'].replace('"', '""')))

#------------------------------------------------------------------------------
class ItemStats(_HandleAliases):
    """Statistics for armor and weapons, with functions for
    importing/exporting from/to mod/text file."""
    _nested_type = lambda: defaultdict(dict)
    _row_sorter = partial(_key_sort, fid_eid=True)

    def __init__(self, aliases_=None, called_from_patcher=False):
        super(ItemStats, self).__init__(aliases_, called_from_patcher)
        self.sig_stats_attrs = bush.game.stats_csv_attrs
        if self._called_from_patcher: # filter eid
            self.sig_stats_attrs = {r: t for r, a in
                                    self.sig_stats_attrs.items() if
                                    (t := tuple(x for x in a if x != 'eid'))}
        self._parser_sigs = set(self.sig_stats_attrs)

    def _read_record(self, record, id_data, __attrgetters=attrgetter_cache):
        atts = self.sig_stats_attrs[record.rec_sig]
        id_data[record.fid].update((a, __attrgetters[a](record)) for a in atts)

    _changed_type = Counter #--changed[modName] = numChanged
    def _write_record(self, record, itemStats, changed_stats,
                      __attrgetters=attrgetter_cache):
        """Writes stats to specified mod."""
        change = False
        for stat_key, n_stat in itemStats.items():
            if change:
                setattr(record, stat_key, n_stat)
                continue
            change = __attrgetters[stat_key](record) != n_stat
            if change:
                setattr(record, stat_key, n_stat)
        if change:
            record.setChanged()
            changed_stats[record.fid.mod_fn] += 1

    def _parse_line(self, csv_fields):
        """Reads stats from specified text file."""
        top_grup, modName, objectStr = csv_fields[:3]
        longid = self._coerce_fid(modName, objectStr) # blow and exit on header
        top_grup_sig = str_to_sig(top_grup)
        attrs = self.sig_stats_attrs[top_grup_sig]
        eid_or_next = 3 + self._called_from_patcher
        attr_dex = {att: dex for att, dex in
                    zip(attrs, range(eid_or_next, eid_or_next + len(attrs)))}
        attr_val = self._update_from_csv(top_grup_sig, csv_fields,
                                         index_dict=attr_dex)
        self.id_stored_data[top_grup_sig][longid].update(attr_val)

    def _header_row(self, out): pass # different header per sig

    def _write_section(self, top_grup_sig, id_data, out):
        if not (sup := super()._write_section(top_grup_sig, id_data, out)):
            return
        atts = self.sig_stats_attrs[top_grup_sig]
        sers = [attr_csv_struct[x][2] for x in atts]
        section_head = '","'.join((_('Type'), _('Mod Name'), _('ObjectIndex'),
                                   *(attr_csv_struct[a][1] for a in atts)))
        out.write(f'"{section_head}"\n')
        return [*sup, [*zip(atts, sers)]]

    def _row_out(self, longid, attr_value, top_grup, attrs_sers):
        """Writes stats to specified text file."""
        return '"%s",%s,%s\n' % (top_grup, _fid_str(longid), ','.join(
            ser(attr_value[x]) for x, ser in attrs_sers))

#------------------------------------------------------------------------------
class ScriptText(_TextParser):
    """Import & export functions for script text.

    Notes regarding line separator handling:
     - We use the native platform's line separators when writing to exported
       .txt files.
     - We use CRLF (Windows-style) when writing to plugins (that seems more
       common from a quick survey of Cobl's scripts).
     - Internally we store lists of strings, i.e. with the newlines chopped
       off."""
    _parser_sigs = [b'SCPT']

    def __init__(self):
        self.eid_data = {}
        self.id_stored_data = {b'SCPT': self.eid_data}

    def export_scripts(self, folder, progress, skip, deprefix, skipcomments):
        """Writes scripts to specified folder."""
        eid_data = self.eid_data
        skip, deprefix = skip.lower(), deprefix.lower()
        x = len(skip)
        exportedScripts = []
        y = len(eid_data)
        r = len(deprefix)
        for z, eid in enumerate(sorted(eid_data,
                key=lambda eid: (eid, eid_data[eid][1]))):
            scpt_lines, longid = eid_data[eid]
            if skipcomments:
                scpt_lines =  self._filter_comments(scpt_lines)
                if not scpt_lines: continue
            progress((0.5 + (0.5 / y) * z), _(u'Exporting script %s.') % eid)
            if x == 0 or skip != eid[:x].lower():
                fileName = eid
                if r and deprefix == fileName[:r].lower():
                    fileName = fileName[r:]
                outpath = dirs[u'patches'].join(folder).join(
                    fileName + inisettings[u'ScriptFileExt'])
                self._writing_state = (scpt_lines, longid, eid)
                self.write_text_file(outpath)
                del self._writing_state
                exportedScripts.append(eid)
        return exportedScripts

    @staticmethod
    def _filter_comments(scpt_lines):
        tmp_lines = []
        for scpt_line in scpt_lines:
            comment_pos = scpt_line.find(';')
            if comment_pos == -1:  # note ''.find(';') == -1
                tmp_lines.append(scpt_line)
            elif comment_pos != 0:
                uncommented_line = scpt_line[:comment_pos]
                if not uncommented_line.isspace():
                    tmp_lines.append(uncommented_line)
        return tmp_lines

    def _header_row(self, out):
        # __win_line_sep: scripts line separator - or so we trust
        _scpt_lines, longid, eid = self._writing_state
        comment = f'{longid.mod_fn}\n;0x{longid.object_dex:06X}\n;{eid}'
        out.write(f';{comment}\n')

    def _write_rows(self, out):
        scpt_lines, _longid, _eid = self._writing_state
        out.write('\n'.join(scpt_lines) + '\n')

    def readFromMod(self, modInfo):
        """Reads scripts from specified mod."""
        eid_data = self.eid_data
        modFile = self._load_plugin(modInfo)
        with Progress(_('Export Scripts')) as progress:
            present_recs = list(modFile.tops[b'SCPT'].iter_present_records())
            y = len(present_recs)
            for z, (rfid, record) in enumerate(present_recs):
                progress((0.5 / y) * z, _('Reading scripts in %s.') % modInfo)
                eid_data[record.eid] = record.script_source.splitlines(), rfid

    _changed_type = list
    def writeToMod(self, modInfo, makeNew=False):
        """Writes scripts to specified mod."""
        self.makeNew = makeNew
        changed_stats = super(ScriptText, self).writeToMod(modInfo)
        return ([], []) if changed_stats is None else changed_stats

    def _check_write_record(self, rfid, record, eid_data, changed_stats):
        # the keys are eids here!
        eid = record.eid
        data_ = eid_data.get(eid,None)
        if data_:
            self._write_record(record, data_, changed_stats)

    def _write_record(self, record, data_, changed_stats):
        new_lines, longid = data_
        old_lines = record.script_source.splitlines()
        if old_lines != new_lines:
            record.script_source = '\r\n'.join(new_lines)
            record.setChanged()
            changed_stats.append(record.eid)
        del self.eid_data[record.eid]

    def _additional_processing(self, changed_stats, modFile):
        added = []
        if self.makeNew and self.eid_data:
            for eid, (new_lines, _longid) in self.eid_data.items():
                newScript = modFile.create_record(b'SCPT', head_flags=0x40000)
                newScript.eid = eid
                newScript.script_source = '\r\n'.join(new_lines)
                added.append(eid)
        if changed_stats or added: return changed_stats, added
        return None

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
                self._read_script(root_dir.join(f))
        return bool(self.eid_data)

    def _read_script(self, textPath):
        with textPath.open(u'r', encoding=u'utf-8-sig') as ins:
            all_lines = ins.read().splitlines()
            if len(all_lines) > 3:
                # First three lines are the header - strip off the comment
                # prefixes
                modName, FormID, eid = [x[1:] for x in all_lines[:3]]
                try:
                    self.eid_data[eid] = (all_lines[3:],
                                          self._coerce_fid(modName, FormID))
                except ValueError:
                    deprint(f'Skipped {textPath.tail} - malformed script '
                            f'header', traceback=True)
            else:
                deprint(f'Skipped {textPath.tail} - malformed script header')

#------------------------------------------------------------------------------
class ItemPrices(_HandleAliases):
    """Function for importing/exporting from/to mod/text file only the
    value, name and eid of records."""
    _csv_header = (_(u'Mod Name'), _(u'ObjectIndex'), _(u'Value'),
                   _(u'Editor Id'), _(u'Name'), _(u'Type'))
    _key2_getter = itemgetter(0, 1)
    _grup_index = 5
    _attr_dex = {u'value': 2, u'eid': 3, u'full': 4}
    _row_sorter = partial(_key_sort, values_key=['eid', 'value'])

    def __init__(self, aliases_=None):
        super(ItemPrices, self).__init__(aliases_)
        self._parser_sigs = set(bush.game.pricesTypes)

    _changed_type = Counter
    def _write_record(self, record, stats, changed_stats):
        """Writes stats to specified record."""
        value = stats[u'value']
        if record.value != value:
            record.value = value
            changed_stats[record.fid.mod_fn] += 1
            record.setChanged()

    def _row_out(self, lfid, stored_data, top_grup,
                 __getter=itemgetter(*_attr_dex)):
        return '%s,"%d","%s","%s","%s"\n' % (
            _fid_str(lfid), *__getter(stored_data), top_grup)

#------------------------------------------------------------------------------
class _UsesEffectsMixin(_HandleAliases):
    """Mixin class to support reading/writing effect data to/from csv files"""
    _key2_getter = itemgetter(0, 1)
    _row_sorter = partial(_key_sort, values_key=['eid'])

    def __init__(self, aliases_, atts, called_from_patcher=False):
        super(_UsesEffectsMixin, self).__init__(aliases_, called_from_patcher)
        self.fid_stats = {}
        self.id_stored_data = {self._parser_sigs[0]: self.fid_stats}
        # Get encoders per attribute - each encoder should return a string
        # corresponding to a csv column
        self._attr_serializer = {k: attr_csv_struct[k][2] for k in atts}
        self._csv_header = [_(u'Mod Name'), _(u'ObjectIndex')]
        for a in self._attr_serializer:
            column_header = attr_csv_struct[a][1]
            if isinstance(column_header, str):
                self._csv_header.append(column_header)
            else: # a tuple of column headers
                self._csv_header.extend(column_header)

    def _update_from_csv(self, top_grup_sig, csv_fields, index_dict=None):
        """Common code for Sigil/Ingredients."""
        attr_val = super()._update_from_csv(top_grup_sig, csv_fields)
        smod = str_or_none(csv_fields[7])
        sid = smod and self._coerce_fid(smod, csv_fields[8])
        attr_val[u'script_fid'] = sid
        return attr_val

    def _read_record(self, record, id_data, __attrgetters=attrgetter_cache):
        ##: Skip OBME records, do not have actorValue for one
        if record.obme_record_version is not None:
            return
        id_data[record.fid] = {att: __attrgetters[att](record) for att in
                               self._attr_serializer}

    _changed_type = list
    def _write_record(self, record, newStats, changed_stats,
                      __attrgetters=attrgetter_cache):
        """Writes stats to specified mod."""
        imported = False
        for att, val in newStats.items():
            old_val = __attrgetters[att](record)
            if att == u'eid': old_eid = old_val
            if att == 'effects':
                # To avoid creating stupid noop edits due to the one unused
                # field inside the SEFF struct, set the record's unused1 to
                # three null bytes before comparing
                for eff in old_val:
                    if se := eff.scriptEffect:
                        se.unused1 = null3
            if old_val != val:
                imported = True
                setattr_deep(record, att, val)
        if imported:
            changed_stats.append(old_eid)
            record.setChanged()

    def _row_out(self, lfid, stored_data, top_grup):
        return '%s,%s\n' % (_fid_str(lfid), ','.join(
            ser(stored_data[k]) for k, ser in self._attr_serializer.items()))

#------------------------------------------------------------------------------
class SigilStoneDetails(_UsesEffectsMixin):
    """Details on SigilStones, with functions for importing/exporting
    from/to mod/text file."""
    _parser_sigs = [b'SGST']

    def __init__(self, aliases_=None, called_from_patcher=False):
        super(SigilStoneDetails, self).__init__(aliases_,
            [u'eid', u'full', u'model.modPath', u'model.modb', u'iconPath',
             u'script_fid', u'uses', u'value', u'weight', u'effects'],
            called_from_patcher)
        self._attr_dex = {'eid': 2, 'full': 3, 'model.modPath': 4,
            'model.modb': 5, 'iconPath': 6, 'uses': 9, 'value': 10,
            'weight': 11, 'effects': (12, self._coerce_fid)}

#------------------------------------------------------------------------------
class SpellRecords(_UsesEffectsMixin):
    """Statistics for spells, with functions for importing/exporting from/to
    mod/text file."""
    _extra_attrs = tuple(f'spell_flags.{x}' for x in
                         ['noAutoCalc', 'startSpell', 'immuneToSilence',
                          'ignoreLOS', 'scriptEffectAlwaysApplies',
                          'disallowAbsorbReflect', 'touchExplodesWOTarget'])
    _csv_attrs = ('eid', 'cost', 'level', 'spellType', 'spell_flags')
    _parser_sigs = [b'SPEL']
    _attr_dex = None

    def __init__(self, aliases_=None, detailed=False,
                 called_from_patcher=False):
        ##: Drop this if check now and always use the game var?
        atts = (bush.game.spell_stats_csv_attrs if called_from_patcher
                else self._csv_attrs)
        if detailed:
            extra_attrs = self.__class__._extra_attrs
            atts += (*extra_attrs, 'effects')
            self._attr_dex = dict(zip(extra_attrs, range(8, 15)))
            self._attr_dex['effects'] = (15, self._coerce_fid)
        super(SpellRecords, self).__init__(aliases_, atts, called_from_patcher)
        self._csv_header = (_('Type'), *self._csv_header)

    def _parse_line(self, fields):
        """Imports stats from specified text file."""
        if fields[0].lower() != u'spel': return
        mid = self._coerce_fid(fields[1], fields[2])
        if int_or_none(fields[4]) is None:  # Index 4 was FULL now cost
            attr_dex = {u'eid': 3, u'cost': 5, u'level': 6, u'spellType': 7}
        else: # FULL was dropped and flags added
            attr_dex = {u'eid': 3, u'cost': 4, u'level': 5, u'spellType': 6,
                        u'spell_flags': 7}
        self.fid_stats[mid] = super(_UsesEffectsMixin, self)._update_from_csv(
            b'SPEL', fields, index_dict=attr_dex)
        if self._attr_dex:  # and not len(fields) < 7: IndexError
            attr_val = super(_UsesEffectsMixin, self)._update_from_csv(b'SPEL',
                                                                       fields)
            self.fid_stats[mid].update(attr_val)

    def _row_out(self, lfid, stored_data, top_grup):
        return f'"SPEL",{super()._row_out(lfid, stored_data, top_grup)}'

#------------------------------------------------------------------------------
class IngredientDetails(_UsesEffectsMixin):
    """Details on Ingredients, with functions for importing/exporting
    from/to mod/text file."""
    _parser_sigs = [b'INGR']

    def __init__(self, aliases_=None, called_from_patcher=False):
        # same as SGST apart from 'uses'
        super(IngredientDetails, self).__init__(aliases_, [u'eid', u'full',
            u'model.modPath', u'model.modb', u'iconPath', u'script_fid',
            u'value', u'weight', u'effects'], called_from_patcher)
        self._attr_dex = {'eid': 2, 'full': 3, 'model.modPath': 4,
                          'model.modb': 5, 'iconPath': 6, 'value': 9,
                          'weight': 10, 'effects': (11, self._coerce_fid)}
