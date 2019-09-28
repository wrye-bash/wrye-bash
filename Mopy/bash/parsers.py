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

"""Parsers can read and write information from and to mods and from and to CSV
files. They store the read information in an internal representation, which
means that they can be used to export and import information from and to mods.
They are also used by some of the patchers in order to not duplicate the work
that has to be done when reading mods.
However, not all parsers fit this pattern - some have to read mods twice,
others barely even fit into the pattern at all (e.g. FidReplacer)."""

from __future__ import division, print_function
import ctypes
import re
from collections import defaultdict, Counter
from operator import attrgetter, itemgetter
# Internal
from . import bush, load_order
from .balt import Progress
from .bass import dirs, inisettings
from .bolt import GPath, decode, deprint, CsvReader, csvFormat, floats_equal
from .brec import MreRecord, MelObject, _coerce, genFid, RecHeader
from .cint import ObCollection, FormID, aggregateTypes, validTypes, MGEFCode, \
    ActorValue, ValidateList, IUNICODE, getattr_deep, setattr_deep
from .exception import AbstractError
from .mod_files import ModFile, LoadFactory


# TODO(inf) Once refactoring is done, we could easily take in Progress objects
#  for more accurate progress bars when importing/exporting
class _AParser(object):
    """The base class from which all parsers inherit. Attempts to accomodate
    all the different parsers.

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
        self.id_stored_info = defaultdict(dict)
        # Automatically set to True when called by a patcher - can be used to
        # alter behavior correspondingly
        self.called_from_patcher = False
        # Automatically set in _parse_sources to the patch file's aliases -
        # used if the Aliases Patcher has been enabled
        self.aliases = {}

    # Plugin-related utilities
    def _mod_has_tag(self, tag_name):
        """Returns True if the current mod has a Bash Tag with the specified
        name."""
        from . import bosh
        return self._current_mod and tag_name in bosh.modInfos[
            self._current_mod].getBashTags()

    def _load_plugin(self, mod_info, target_types):
        """Loads the specified record types in the specified ModInfo and
        returns the result. Abstract because it may be implemented by either
        PBash or CBash.

        :param mod_info: The ModInfo object to read.
        :param target_types: A list, set or tuple containing strings that shows
            which record types to load.
        :return: An object representing the loaded plugin."""
        raise AbstractError(u'_load_plugin not implemented')

    # Reading from plugin - first pass
    def _read_plugin_fp(self, loaded_mod):
        """Performs a first pass of reading on the specified plugin and its
        masters. Results are stored in id_context.

        :param loaded_mod: The loaded mod to read from."""
        raise AbstractError(u'_read_plugin_fp not implemented')

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
        raise AbstractError(u'_read_plugin_sp not implemented')

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
        loaded_mod = self._load_plugin(mod_info, a_types)
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
        raise AbstractError(u'_do_write_plugin not implemented')

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
        return self._do_write_plugin(self._load_plugin(
            mod_info, self.id_stored_info.keys()))

    # Reading from CSV
    def _get_read_format(self, csv_fields):
        """Determines the _ACsvFormat to use when reading the specified CSV
        line. We need to be dynamic here since some parsers need to support
        multiple formats (e.g. for backwards compatibility).

        :param csv_fields: A line in a CSV file, already split into fields.
        :return: An _ACsvFormat instance (*not* a class!)."""
        raise AbstractError()

    def readFromText(self, csv_path):
        """Reads information from the specified CSV file and stores the result
        in id_stored_info. You must override _get_format for this method to
        work.

        :param csv_path: The path to the CSV file that should be read."""
        with CsvReader(csv_path) as ins:
            for csv_fields in ins:
                # Figure out which format to use, then ask the format to parse
                # the line
                cur_format = self._get_read_format(csv_fields)
                rec_type, source_mod, fid_key, rec_info = \
                    cur_format.parse_line(csv_fields)
                self.id_stored_info[rec_type][source_mod][fid_key] = rec_info

    # Other API
    @property
    def all_types(self):
        """Returns a set of all record types that this parser requires."""
        return set(self._fp_types) | set(self._sp_types)

# CSV Formats
class _ACsvFormat(object):
    """A format determines how lines in a CSV file are parsed and written."""
    def parse_line(self, csv_fields):
        """Parses the specified CSV line and returns a tuple containing the
        result.

        :param csv_fields: A line in a CSV file, already split into fields.
        :return: A tuple containing the following, in order: The type of record
            described by this line, the name of the plugin from which this line
            originated, the (short) FormID of this"""

# PBash / CBash implementations of the parsers
# TODO(inf) Should this really be based on _AParser? Would object be better? If
#  we do that, we will lose typing though...
class _PBashParser(_AParser):
    """Mixin for parsers that implements reading and writing mods using PBash
    calls. You will of course still have to implement _read_record_fp et al.,
    depending on the passes and behavior you want."""

    def _load_plugin(self, mod_info, target_types):
        mod_file = ModFile(mod_info, LoadFactory(
            False, *[MreRecord.type_class[t] for t in target_types]))
        mod_file.load(do_unpack=True)
        mod_file.convertToLongFids(target_types)
        return mod_file

    def _read_plugin_fp(self, loaded_mod):
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
            _fp_loop(self._load_plugin(bosh.modInfos[mod_name],
                                       self._fp_types))
        # Finally, process the mod itself
        if loaded_mod.fileInfo.name in self._fp_mods: return
        _fp_loop(loaded_mod)

    def _read_plugin_sp(self, loaded_mod):
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

    def _do_write_plugin(self, loaded_mod):
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
        if sum(num_changed_records):
            # Don't forget to convert back to short fids when writing!
            loaded_mod.convertToShortFids()
            loaded_mod.safeSave()
        return num_changed_records

class ActorFactions(_PBashParser):
    """Parses factions from NPCs and Creatures (in games that have those). Can
    read and write both plugins and CSV, and uses a single pass if called from
    a patcher, but two passes if called from a link."""

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
        return [(f.faction, f.rank) for f in record.factions]

    def _should_write_record(self, new_info, cur_info):
        return bool(set(new_info) - set(cur_info))

    def _write_record(self, record, new_info, cur_info):
        for faction, rank in set(new_info) - set(cur_info):
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

    def readFromText(self,textPath):
        """Imports faction data from specified text file."""
        type_id_factions = self.id_stored_info
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 8 or fields[3][:2] != u'0x': continue
                type_,aed,amod,aobj,fed,fmod,fobj,rank = fields[:9]
                amod = GPath(amod)
                fmod = GPath(fmod)
                aid = (aliases.get(amod,amod),int(aobj[2:],16))
                fid = (aliases.get(fmod,fmod),int(fobj[2:],16))
                rank = int(rank)
                id_factions = type_id_factions[type_]
                factions = id_factions.get(aid)
                factiondict = dict(factions or [])
                factiondict.update({fid:rank})
                id_factions[aid] = [(fid,rank) for fid,rank in
                                    factiondict.iteritems()]

    def writeToText(self,textPath):
        """Exports faction data to specified text file."""
        type_id_factions,id_eid = self.id_stored_info, self.id_context
        headFormat = u'"%s","%s","%s","%s","%s","%s","%s","%s"\n'
        rowFormat = u'"%s","%s","%s","0x%06X","%s","%s","0x%06X","%s"\n'
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            out.write(headFormat % (
                _(u'Type'),_(u'Actor Eid'),_(u'Actor Mod'),_(u'Actor Object'),
                _(u'Faction Eid'),_(u'Faction Mod'),_(u'Faction Object'),
                _(u'Rank')))
            for type_ in sorted(type_id_factions):
                id_factions = type_id_factions[type_]
                for id_ in sorted(id_factions,
                                  key=lambda x:id_eid.get(x).lower()):
                    actorEid = id_eid.get(id_,u'Unknown')
                    for faction,rank in sorted(id_factions[id_],
                                               key=lambda x:id_eid.get(
                                                       x[0]).lower()):
                        factionEid = id_eid.get(faction,u'Unknown')
                        out.write(rowFormat % (
                            type_,actorEid,id_[0].s,id_[1],factionEid,
                            faction[0].s,faction[1],rank))

class CBash_ActorFactions(object):
    """Factions for npcs and creatures with functions for
    importing/exporting from/to mod/text file."""

    def __init__(self,aliases=None):
        self.group_fid_factions = {b'CREA': {}, b'NPC_': {}} #--factions =
        # group_fid_factions[group][longid]
        self.fid_eid = {}
        self.aliases = aliases or {}
        self.gotFactions = set()

    def readFromMod(self,modInfo):
        """Imports faction data from specified mod."""
        group_fid_factions,fid_eid,gotFactions = self.group_fid_factions,\
                                                 self.fid_eid,self.gotFactions
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            importFile = Current.addMod(modInfo.getPath().stail,Saveable=False)
            Current.load()
            for modFile in Current.LoadOrderMods:
                modName = modFile.GName
                if modName in gotFactions: continue
                for record in modFile.FACT:
                    fid_eid[record.fid] = record.eid
                if modFile != importFile: continue
                types = {b'CREA': modFile.CREA, b'NPC_': modFile.NPC_}
                for group,block in types.iteritems():
                    fid_factions = group_fid_factions[group]
                    for record in block:
                        fid = record.fid
                        factions = record.factions_list
                        if factions:
                            fid_eid[fid] = record.eid
                            fid_factions[fid] = factions
                modFile.Unload()
                gotFactions.add(modName)

    def writeToMod(self,modInfo):
        """Exports faction data to specified mod."""
        group_fid_factions = self.group_fid_factions
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            changed = Counter() # {'CREA':0,'NPC_':0}
            types = {b'CREA': modFile.CREA, b'NPC_': modFile.NPC_}
            for group,block in types.iteritems():
                fid_factions = group_fid_factions.get(group,None)
                if fid_factions is not None:
                    fid_factions = FormID.FilterValidDict(fid_factions,modFile,
                                                          True,False)
                    for record in block:
                        fid = record.fid
                        if fid not in fid_factions: continue
                        newFactions = set([(faction,rank) for faction,rank in
                                           fid_factions[fid] if
                                           faction.ValidateFormID(modFile)])
                        curFactions = set([(faction,rank) for faction,rank in
                                           record.factions_list if
                                           faction.ValidateFormID(modFile)])
                        changes = newFactions - curFactions
                        if not changes: continue
                        for faction,rank in changes:
                            for entry in record.factions:
                                if entry.faction == faction:
                                    entry.rank = rank
                                    break
                            else:
                                entry = record.create_faction()
                                entry.faction = faction
                                entry.rank = rank
                        changed[group] += 1
            #--Done
            if sum(changed.values()): modFile.save()
            return changed

    def readFromText(self,textPath):
        """Imports faction data from specified text file."""
        group_fid_factions = self.group_fid_factions
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 8 or fields[3][:2] != u'0x': continue
                group,aed,amod,aobj,fed,fmod,fobj,rank = fields[:9]
                group = _coerce(group,unicode)
                amod = GPath(_coerce(amod,unicode))
                fmod = GPath(_coerce(fmod,unicode))
                aid = FormID(aliases.get(amod,amod),_coerce(aobj[2:],int,16))
                fid = FormID(aliases.get(fmod,fmod),_coerce(fobj[2:],int,16))
                rank = _coerce(rank, int)
                fid_factions = group_fid_factions[group]
                factions = fid_factions.get(aid)
                factiondict = dict(factions or [])
                factiondict.update({fid:rank})
                fid_factions[aid] = [(fid,rank) for fid,rank in
                                     factiondict.iteritems()]

    def writeToText(self,textPath):
        """Exports faction data to specified text file."""
        group_fid_factions,fid_eid = self.group_fid_factions, self.fid_eid
        headFormat = u'"%s","%s","%s","%s","%s","%s","%s","%s"\n'
        rowFormat = u'"%s","%s","%s","0x%06X","%s","%s","0x%06X","%s"\n'
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            out.write(headFormat % (
                _(u'Type'),_(u'Actor Eid'),_(u'Actor Mod'),_(u'Actor Object'),
                _(u'Faction Eid'),_(u'Faction Mod'),_(u'Faction Object'),
                _(u'Rank')))
            for group in sorted(group_fid_factions):
                fid_factions = group_fid_factions[group]
                for fid in sorted(fid_factions,key = lambda x: fid_eid.get(x)):
                    actorEid = fid_eid.get(fid,u'Unknown')
                    for faction,rank in sorted(fid_factions[fid],
                                               key=lambda x:fid_eid.get(x[0])):
                        factionEid = fid_eid.get(faction,u'Unknown')
                        out.write(rowFormat % (
                            group,actorEid,fid[0].s,fid[1],factionEid,
                            faction[0].s,faction[1],rank))

#------------------------------------------------------------------------------
class ActorLevels(object):
    """Package: Functions for manipulating actor levels."""

    def __init__(self,aliases=None):
        self.mod_id_levels = {} #--levels = mod_id_levels[mod][longid]
        self.aliases = aliases or {}
        self.gotLevels = set()

    def readFromMod(self,modInfo):
        """Imports actor level data from the specified mod and its masters."""
        from . import bosh
        mod_id_levels, gotLevels = self.mod_id_levels, self.gotLevels
        loadFactory = LoadFactory(False,MreRecord.type_class[b'NPC_'])
        for modName in (modInfo.masterNames + (modInfo.name,)):
            if modName in gotLevels: continue
            modFile = ModFile(bosh.modInfos[modName],loadFactory)
            modFile.load(True)
            mapper = modFile.getLongMapper()
            for record in modFile.NPC_.getActiveRecords():
                id_levels = mod_id_levels.setdefault(modName,{})
                id_levels[mapper(record.fid)] = (
                    record.eid, bool(record.flags.pcLevelOffset),
                    record.level,record.calcMin,record.calcMax)
            gotLevels.add(modName)

    def writeToMod(self,modInfo):
        """Exports actor levels to specified mod."""
        mod_id_levels = self.mod_id_levels
        loadFactory = LoadFactory(True,MreRecord.type_class[b'NPC_'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        changed = 0
        id_levels = mod_id_levels.get(modInfo.name,
                                      mod_id_levels.get(GPath(u'Unknown'),
                                                        None))
        if id_levels:
            for record in modFile.NPC_.records:
                fid = mapper(record.fid)
                if fid in id_levels:
                    eid,isOffset,level,calcMin,calcMax = id_levels[fid]
                    if ((record.level,record.calcMin,record.calcMax) != (
                            level,calcMin,calcMax)):
                        (record.level,record.calcMin,record.calcMax) = (
                            level,calcMin,calcMax)
                        record.setChanged()
                        changed += 1
                    # else: print mod_id_levels
        #--Done
        if changed: modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Imports NPC level data from specified text file."""
        mod_id_levels = self.mod_id_levels
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if fields[0][:2] == u'0x': #old format
                    fid,eid,offset,calcMin,calcMax = fields[:5]
                    source = GPath(u'Unknown')
                    fidObject = _coerce(fid[4:], int, 16)
                    fid = (GPath(bush.game.master_file), fidObject)
                    eid = _coerce(eid, unicode)
                    offset = _coerce(offset, int)
                    calcMin = _coerce(calcMin, int)
                    calcMax = _coerce(calcMax, int)
                else:
                    if len(fields) < 7 or fields[3][:2] != u'0x': continue
                    source,eid,fidMod,fidObject,offset,calcMin,calcMax = \
                        fields[:7]
                    source = _coerce(source, unicode)
                    if source.lower() in (u'none', bush.game.master_file.lower()): continue
                    source = GPath(source)
                    eid = _coerce(eid, unicode)
                    fidMod = GPath(_coerce(fidMod, unicode))
                    if fidMod.s.lower() == u'none': continue
                    fidObject = _coerce(fidObject[2:], int, 16)
                    if fidObject is None: continue
                    fid = (aliases.get(fidMod,fidMod),fidObject)
                    offset = _coerce(offset, int)
                    calcMin = _coerce(calcMin, int)
                    calcMax = _coerce(calcMax, int)
                id_levels = mod_id_levels.setdefault(source, {})
                id_levels[fid] = (eid, 1, offset, calcMin, calcMax)

    def writeToText(self,textPath):
        """Export NPC level data to specified text file."""
        mod_id_levels = self.mod_id_levels
        headFormat = u'"%s","%s","%s","%s","%s","%s","%s","%s","%s","%s",' \
                     u'"%s"\n'
        rowFormat = u'"%s","%s","%s","0x%06X","%d","%d","%d"'
        extendedRowFormat = u',"%d","%d","%d","%d"\n'
        blankExtendedRow = u',,,,\n'
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            out.write(headFormat % (
                _(u'Source Mod'),_(u'Actor Eid'),_(u'Actor Mod'),
                _(u'Actor Object'),_(u'Offset'),_(u'CalcMin'),_(u'CalcMax'),
                _(u'Old IsPCLevelOffset'),_(u'Old Offset'),_(u'Old CalcMin'),
                _(u'Old CalcMax')))
            #Sorted based on mod, then editor ID
            obId_levels = mod_id_levels[GPath(bush.game.master_file)]
            for mod in sorted(mod_id_levels):
                if mod.s.lower() == bush.game.master_file.lower(): continue
                id_levels = mod_id_levels[mod]
                for id_ in sorted(id_levels,key=lambda k:(
                        k[0].s.lower(),id_levels[k][0].lower())):
                    eid,isOffset,offset,calcMin,calcMax = id_levels[id_]
                    if isOffset:
                        source = mod.s
                        fidMod, fidObject = id_[0].s,id_[1]
                        out.write(rowFormat % (
                            source,eid,fidMod,fidObject,offset,calcMin,
                            calcMax))
                        oldLevels = obId_levels.get(id_,None)
                        if oldLevels:
                            oldEid,wasOffset,oldOffset,oldCalcMin,oldCalcMax\
                                = oldLevels
                            out.write(extendedRowFormat % (
                                wasOffset,oldOffset,oldCalcMin,oldCalcMax))
                        else:
                            out.write(blankExtendedRow)

class CBash_ActorLevels(object):
    """Package: Functions for manipulating actor levels."""

    def __init__(self,aliases=None):
        self.mod_fid_levels = {} #--levels = mod_id_levels[mod][longid]
        self.aliases = aliases or {}
        self.gotLevels = set()

    def readFromMod(self,modInfo):
        """Imports actor level data from the specified mod and its masters."""
        mod_fid_levels, gotLevels = self.mod_fid_levels, self.gotLevels
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            Current.addMod(bush.game.master_file, Saveable=False)
            Current.addMod(modInfo.getPath().stail, Saveable=False)
            Current.load()
            for modFile in Current.LoadOrderMods:
                modName = modFile.GName
                if modName in gotLevels: continue
                fid_levels = mod_fid_levels.setdefault(modName, {})
                for record in modFile.NPC_:
                    fid_levels[record.fid] = (
                        record.eid,record.IsPCLevelOffset and 1 or 0,
                        record.level,record.calcMin,record.calcMax)
                modFile.Unload()
                gotLevels.add(modName)

    def writeToMod(self,modInfo):
        """Exports actor levels to specified mod."""
        mod_fid_levels = self.mod_fid_levels
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            changed = 0
            fid_levels = mod_fid_levels.get(modFile.GName,mod_fid_levels.get(
                GPath(u'Unknown'),None))
            if fid_levels:
                for record in modFile.NPC_:
                    fid = record.fid
                    if fid not in fid_levels: continue
                    eid,isOffset,level,calcMin,calcMax = fid_levels[fid]
                    if ((record.level,record.calcMin,record.calcMax) != (
                            level,calcMin,calcMax)):
                        (record.level,record.calcMin,record.calcMax) = (
                            level,calcMin,calcMax)
                        changed += 1
            #--Done
            if changed: modFile.save()
            return changed

    def readFromText(self,textPath):
        """Imports NPC level data from specified text file."""
        mod_fid_levels = self.mod_fid_levels
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if fields[0][:2] == u'0x': #old format
                    fid,eid,offset,calcMin,calcMax = fields[:5]
                    source = GPath(u'Unknown')
                    fidObject = _coerce(fid[4:], int, 16)
                    fid = FormID(GPath(bush.game.master_file), fidObject)
                    eid = _coerce(eid, unicode, AllowNone=True)
                    offset = _coerce(offset, int)
                    calcMin = _coerce(calcMin, int)
                    calcMax = _coerce(calcMax, int)
                else:
                    if len(fields) < 7 or fields[3][:2] != u'0x': continue
                    source,eid,fidMod,fidObject,offset,calcMin,calcMax = \
                        fields[:7]
                    source = _coerce(source, unicode)
                    if source.lower() in (
                            u'none', bush.game.master_file.lower()): continue
                    source = GPath(source)
                    eid = _coerce(eid, unicode, AllowNone=True)
                    fidMod = GPath(_coerce(fidMod, unicode))
                    if fidMod.s.lower() == u'none': continue
                    fidObject = _coerce(fidObject[2:], int, 16)
                    if fidObject is None: continue
                    fid = FormID(aliases.get(fidMod,fidMod),fidObject)
                    offset = _coerce(offset, int)
                    calcMin = _coerce(calcMin, int)
                    calcMax = _coerce(calcMax, int)
                fid_levels = mod_fid_levels.setdefault(source, {})
                fid_levels[fid] = (eid, 1, offset, calcMin, calcMax)

    def writeToText(self,textPath):
        """Export NPC level data to specified text file."""
        mod_fid_levels = self.mod_fid_levels
        headFormat = u'"%s","%s","%s","%s","%s","%s","%s","%s","%s","%s",' \
                     u'"%s"\n'
        rowFormat = u'"%s","%s","%s","0x%06X","%d","%d","%d"'
        extendedRowFormat = u',"%d","%d","%d","%d"\n'
        blankExtendedRow = u',,,,\n'
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            out.write(headFormat % (
                _(u'Source Mod'),_(u'Actor Eid'),_(u'Actor Mod'),
                _(u'Actor Object'),_(u'Offset'),_(u'CalcMin'),_(u'CalcMax'),
                _(u'Old IsPCLevelOffset'),_(u'Old Offset'),_(u'Old CalcMin'),
                _(u'Old CalcMax')))
            #Sorted based on mod, then editor ID
            obfid_levels = mod_fid_levels[GPath(bush.game.master_file)]
            for mod in sorted(mod_fid_levels):
                if mod.s.lower() == bush.game.master_file.lower(): continue
                fid_levels = mod_fid_levels[mod]
                for fid in sorted(fid_levels,
                                  key=lambda k:(k[0].s,fid_levels[k][0])):
                    eid, isOffset, offset, calcMin, calcMax = fid_levels[fid]
                    if isOffset:
                        source = mod.s
                        fidMod,fidObject = fid[0].s,fid[1]
                        out.write(rowFormat % (
                            source,eid,fidMod,fidObject,offset,calcMin,
                            calcMax))
                        oldLevels = obfid_levels.get(fid,None)
                        if oldLevels:
                            oldEid,wasOffset,oldOffset,oldCalcMin,oldCalcMax\
                                = oldLevels
                            out.write(extendedRowFormat % (
                                wasOffset,oldOffset,oldCalcMin,oldCalcMax))
                        else:
                            out.write(blankExtendedRow)

#------------------------------------------------------------------------------
class EditorIds(object):
    """Editor ids for records, with functions for importing/exporting
    from/to mod/text file."""

    def __init__(self,types=None,aliases=None):
        self.type_id_eid = {} #--eid = eids[type][longid]
        self.old_new = {}
        if types:
            self.types = types
        else:
            self.types = set(MreRecord.simpleTypes)
            self.types.discard(b'CELL')
        self.aliases = aliases or {}

    def readFromMod(self,modInfo):
        """Imports eids from specified mod."""
        type_id_eid,types = self.type_id_eid,self.types
        classes = [MreRecord.type_class[x] for x in types]
        loadFactory = LoadFactory(False,*classes)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        for type_ in types:
            typeBlock = modFile.tops.get(type_)
            if not typeBlock: continue
            if type_ not in type_id_eid: type_id_eid[type_] = {}
            id_eid = type_id_eid[type_]
            for record in typeBlock.getActiveRecords():
                longid = mapper(record.fid)
                if record.eid: id_eid[longid] = record.eid

    def writeToMod(self,modInfo):
        """Exports eids to specified mod."""
        type_id_eid,types = self.type_id_eid,self.types
        classes = [MreRecord.type_class[x] for x in types]
        loadFactory = LoadFactory(True,*classes)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        changed = []
        for type_ in types:
            id_eid = type_id_eid.get(type_,None)
            typeBlock = modFile.tops.get(type_,None)
            if not id_eid or not typeBlock: continue
            for record in typeBlock.records:
                longid = mapper(record.fid)
                newEid = id_eid.get(longid)
                oldEid = record.eid
                if newEid and record.eid and newEid != oldEid:
                    record.eid = newEid
                    record.setChanged()
                    changed.append((oldEid,newEid))
        #--Update scripts
        old_new = dict(self.old_new)
        old_new.update(
            dict([(oldEid.lower(),newEid) for oldEid,newEid in changed]))
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
        for script in sorted(modFile.SCPT.records, key=attrgetter(u'eid')):
            if not script.script_source: continue
            newText = reWord.sub(subWord,script.script_source)
            if newText != script.script_source:
                # header = u'\r\n\r\n; %s %s\r\n' % (script.eid,u'-' * (77 -
                # len(script.eid))) # unused - bug ?
                script.script_source = newText
                script.setChanged()
                changed.append((_(u'Script'),script.eid))
        #--Quest Scripts
        for quest in sorted(modFile.QUST.records, key=attrgetter(u'eid')):
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

    def readFromText(self,textPath,questionableEidsSet=None,badEidsList=None):
        """Imports eids from specified text file."""
        type_id_eid = self.type_id_eid
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            reValidEid = re.compile(u'^[a-zA-Z0-9]+$')
            reGoodEid = re.compile(u'^[a-zA-Z]')
            for fields in ins:
                if len(fields) < 4 or fields[2][:2] != u'0x': continue
                group,mod,objectIndex,eid = fields[:4]
                group = _coerce(group,unicode)
                mod = GPath(_coerce(mod,unicode))
                longid = (aliases.get(mod,mod),_coerce(objectIndex[2:],int,16))
                eid = _coerce(eid,unicode, AllowNone=True)
                if not reValidEid.match(eid):
                    if badEidsList is not None:
                        badEidsList.append(eid)
                    continue
                if questionableEidsSet is not None and not reGoodEid.match(
                        eid):
                    questionableEidsSet.add(eid)
                id_eid = type_id_eid.setdefault(group, {})
                id_eid[longid] = eid
                #--Explicit old to new def? (Used for script updating.)
                if len(fields) > 4:
                    self.old_new[_coerce(fields[4], unicode).lower()] = eid

    def writeToText(self,textPath):
        """Exports eids to specified text file."""
        type_id_eid = self.type_id_eid
        headFormat = u'"%s","%s","%s","%s"\n'
        rowFormat = u'"%s","%s","0x%06X","%s"\n'
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            out.write(headFormat % (
                _(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id')))
            for type_ in sorted(type_id_eid):
                id_eid = type_id_eid[type_]
                for id_ in sorted(id_eid,key = lambda a: id_eid[a].lower()):
                    out.write(rowFormat % (type_,id_[0].s,id_[1],id_eid[id_]))

class CBash_EditorIds(object):
    """Editor ids for records, with functions for importing/exporting
    from/to mod/text file."""

    def __init__(self,types=None,aliases=None):
        self.group_fid_eid = {} #--eid = group_fid_eid[group][longid]
        self.old_new = {}
        if types:
            self.groups = set(types)
        else:
            self.groups = aggregateTypes
        self.aliases = aliases or {}

    def readFromMod(self,modInfo):
        """Imports eids from specified mod."""
        group_fid_eid,groups = self.group_fid_eid,self.groups
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,Saveable=False,
                                     LoadMasters=False)
            Current.load()
            for group in groups:
                fid_eid = group_fid_eid.setdefault(group[:4], {})
                for record in getattr(modFile, group):
                    eid = record.eid
                    if eid: fid_eid[record.fid] = eid
                modFile.Unload()

    def writeToMod(self,modInfo):
        """Exports eids to specified mod."""
        group_fid_eid = self.group_fid_eid
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            changed = []
            for group,block in modFile.aggregates.iteritems():
                fid_eid = group_fid_eid.get(group[:4],None)
                if not fid_eid: continue
                for record in block:
                    fid = record.fid
                    newEid = fid_eid.get(fid)
                    oldEid = record.eid
                    if newEid and newEid != oldEid:
                        record.eid = newEid
                        if record.eid == newEid: #Can silently fail if a
                            # record keyed by editorID (GMST,MGEF) already has
                            # the value
                            changed.append((oldEid or u'',newEid or u''))
            #--Update scripts
            old_new = dict(self.old_new)
            old_new.update(
                dict([(oldEid.lower(),newEid) for oldEid,newEid in changed]))
            changed.extend(self.changeScripts(modFile,old_new))
            #--Done
            if changed: modFile.save()
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
        for script in sorted(modFile.SCPT, key=attrgetter(u'eid')):
            if not script.scriptText: continue
            newText = reWord.sub(subWord,script.scriptText)
            if newText != script.scriptText:
                script.scriptText = newText
                changed.append((_(u'Script'),script.eid))
        #--Quest Scripts
        for quest in sorted(modFile.QUST, key=attrgetter(u'eid')):
            questChanged = False
            for stage in quest.stages:
                for entry in stage.entries:
                    oldScript = entry.scriptText
                    if not oldScript: continue
                    newScript = reWord.sub(subWord,oldScript)
                    if newScript != oldScript:
                        entry.scriptText = newScript
                        questChanged = True
            if questChanged:
                changed.append((_(u'Quest'),quest.eid))
        #--Done
        return changed

    def readFromText(self,textPath,questionableEidsSet=None,badEidsList=None):
        """Imports eids from specified text file."""
        group_fid_eid = self.group_fid_eid
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            reValidEid = re.compile(u'^[a-zA-Z0-9]+$')
            reGoodEid = re.compile(u'^[a-zA-Z]')
            for fields in ins:
                if len(fields) < 4 or fields[2][:2] != u'0x': continue
                group,mod,objectIndex,eid = fields[:4]
                group = _coerce(group,unicode)[:4]
                if group not in validTypes: continue
                mod = GPath(_coerce(mod,unicode))
                longid = FormID(aliases.get(mod,mod),
                                _coerce(objectIndex[2:],int,16))
                eid = _coerce(eid,unicode, AllowNone=True)
                if not reValidEid.match(eid):
                    if badEidsList is not None:
                        badEidsList.append(eid)
                    continue
                if questionableEidsSet is not None and not reGoodEid.match(
                        eid):
                    questionableEidsSet.add(eid)
                fid_eid = group_fid_eid.setdefault(group, {})
                fid_eid[longid] = eid
                #--Explicit old to new def? (Used for script updating.)
                if len(fields) > 4:
                    self.old_new[_coerce(fields[4], unicode).lower()] = eid

    def writeToText(self,textPath):
        """Exports eids to specified text file."""
        group_fid_eid = self.group_fid_eid
        headFormat = u'"%s","%s","%s","%s"\n'
        rowFormat = u'"%s","%s","0x%06X","%s"\n'
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            out.write(headFormat % (
                _(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id')))
            for group in sorted(group_fid_eid):
                fid_eid = group_fid_eid[group]
                for fid in sorted(fid_eid,key = lambda a: fid_eid[a]):
                    out.write(rowFormat % (group,fid[0].s,fid[1],fid_eid[fid]))

#------------------------------------------------------------------------------
class FactionRelations(_PBashParser):
    """Parses the relations between factions. Can read and write both plugins
    and CSV, and uses two passes to do so."""
    cls_rel_attrs = bush.game.relations_attrs

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
        relations = self.id_stored_info[b'FACT'].get(record.fid, [])
        other_index = dict((y[0], x) for x, y in enumerate(relations))
        # Merge added relations, preserve changed relations
        for relation in record.relations:
            rel_attrs = tuple(getattr(relation, a) for a
                              in self.cls_rel_attrs)
            other_fac = rel_attrs[0]
            if other_fac in other_index:
                # This is just a change, preserve the latest value
                relations[other_index[other_fac]] = rel_attrs
            else:
                # This is an addition, merge it
                relations.append(rel_attrs)
        return relations

    def _write_record(self, record, new_info, cur_info):
        for relation in set(new_info) - set(cur_info):
            rel_fac = relation[0]
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
            for rel_attr, rel_val in zip(self.cls_rel_attrs, relation):
                setattr(target_entry, rel_attr, rel_val)

    def readFromText(self,textPath):
        """Imports faction relations from specified text file."""
        id_relations = self.id_stored_info[b'FACT']
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 7 or fields[2][:2] != u'0x': continue
                med, mmod, mobj, oed, omod, oobj = fields[:6]
                mmod = _coerce(mmod, unicode)
                omod = _coerce(omod, unicode)
                mid = (GPath(aliases.get(mmod,mmod)),_coerce(mobj[2:],int,16))
                oid = (GPath(aliases.get(omod,omod)),_coerce(oobj[2:],int,16))
                relation_attrs = (oid,) + tuple(fields[6:])
                relations = id_relations.get(mid)
                if relations is None:
                    relations = id_relations[mid] = []
                for index,entry in enumerate(relations):
                    if entry[0] == oid:
                        relations[index] = relation_attrs
                        break
                else:
                    relations.append(relation_attrs)

    def writeToText(self,textPath):
        """Exports faction relations to specified text file."""
        id_relations, id_eid = self.id_stored_info[b'FACT'], self.id_context
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            out.write(bush.game.relations_csv_header)
            for main_fid in sorted(id_relations,
                                   key=lambda x: id_eid.get(x).lower()):
                main_eid = id_eid.get(main_fid, u'Unknown')
                for relation_obj in sorted(
                        id_relations[main_fid],
                        key=lambda x: id_eid.get(x[0]).lower()):
                    other_fid = relation_obj[0]
                    other_eid = id_eid.get(other_fid, u'Unknown')
                    # I wish py2 allowed star exprs in tuples/lists...
                    row_vals = (main_eid, main_fid[0].s, main_fid[1],
                                other_eid, other_fid[0].s,
                                other_fid[1]) + relation_obj[1:]
                    out.write(bush.game.relations_csv_row_format % row_vals)

class CBash_FactionRelations(object):
    """Faction relations."""

    def __init__(self,aliases=None):
        self.fid_faction_mod = {}
        self.fid_eid = {} #--For all factions.
        self.aliases = aliases or {}
        self.gotFactions = set()

    def readFromMod(self,modInfo):
        """Imports faction relations from specified mod."""
        fid_faction_mod,fid_eid,gotFactions = self.fid_faction_mod,\
                                              self.fid_eid,self.gotFactions
        importFile = modInfo.getPath().tail
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            importFile = Current.addMod(importFile.s, Saveable=False)
            Current.load()
            for modFile in Current.LoadOrderMods:
                modName = modFile.GName
                if modName in gotFactions: continue
                if modFile == importFile:
                    for record in modFile.FACT:
                        fid = record.fid
                        fid_eid[fid] = record.eid
                        relations = record.relations_list
                        if relations:
                            faction_mod = fid_faction_mod.setdefault(fid,{})
                            faction_mod.update(relations)
                else:
                    for record in modFile.FACT:
                        fid_eid[record.fid] = record.eid
                modFile.Unload()
                gotFactions.add(modName)

    def readFromText(self,textPath):
        """Imports faction relations from specified text file."""
        fid_faction_mod = self.fid_faction_mod
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 7 or fields[2][:2] != u'0x': continue
                med,mmod,mobj,oed,omod,oobj,disp = fields[:9]
                mmod = _coerce(mmod,unicode)
                omod = _coerce(omod,unicode)
                mid = FormID(GPath(aliases.get(mmod,mmod)),
                             _coerce(mobj[2:],int,16))
                oid = FormID(GPath(aliases.get(omod,omod)),
                             _coerce(oobj[2:],int,16))
                disp = _coerce(disp,int)
                faction_mod = fid_faction_mod.setdefault(mid,{})
                faction_mod[oid] = disp

    def writeToMod(self,modInfo):
        """Exports faction relations to specified mod."""
        fid_faction_mod = self.fid_faction_mod
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            changed = 0
            for record in modFile.FACT:
                fid = record.fid
                if fid not in fid_faction_mod: continue
                faction_mod = FormID.FilterValidDict(fid_faction_mod[fid],
                                                     modFile,True,False)
                newRelations = set([(faction,mod) for faction,mod in
                                    FormID.FilterValidDict(faction_mod,modFile,
                                                           True,
                                                           False).iteritems()])
                curRelations = set(
                    [(faction,mod) for faction,mod in record.relations_list if
                     faction.ValidateFormID(modFile)])
                changes = newRelations - curRelations
                if not changes: continue
                for faction,mod in changes:
                    for entry in record.relations:
                        if entry.faction == faction:
                            entry.mod = mod
                            break
                    else:
                        entry = record.create_relation()
                        entry.faction = faction
                        entry.mod = mod
                changed += 1
            #--Done
            if changed: modFile.save()
            return changed

    def writeToText(self,textPath):
        """Exports faction relations to specified text file."""
        fid_faction_mod,fid_eid = self.fid_faction_mod, self.fid_eid
        headFormat = u'"%s","%s","%s","%s","%s","%s","%s"\n'
        rowFormat = u'"%s","%s","0x%06X","%s","%s","0x%06X","%s"\n'
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            out.write(headFormat % (
                _(u'Main Eid'),_(u'Main Mod'),_(u'Main Object'),
                _(u'Other Eid'),_(u'Other Mod'),_(u'Other Object'),_(u'Disp')))
            for main in sorted(fid_faction_mod, key=lambda x: fid_eid.get(x)):
                mainEid = fid_eid.get(main,u'Unknown')
                faction_mod = fid_faction_mod[main]
                for other,disp in sorted(faction_mod.items(),
                                         key=lambda x:fid_eid.get(x[0])):
                    otherEid = fid_eid.get(other,u'Unknown')
                    out.write(rowFormat % (
                        mainEid,main[0].s,main[1],otherEid,other[0].s,other[1],
                        disp))

#------------------------------------------------------------------------------
class FidReplacer(object):
    """Replaces one set of fids with another."""

    def __init__(self,types=None,aliases=None):
        self.types = types or MreRecord.simpleTypes
        self.aliases = aliases or {} #--For aliasing mod names
        self.old_new = {} #--Maps old fid to new fid
        self.old_eid = {} #--Maps old fid to old editor id
        self.new_eid = {} #--Maps new fid to new editor id

    def readFromText(self,textPath):
        """Reads replacement data from specified text file."""
        old_new,old_eid,new_eid = self.old_new,self.old_eid,self.new_eid
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 7 or fields[2][:2] != u'0x'\
                        or fields[6][:2] != u'0x': continue
                oldMod,oldObj,oldEid,newEid,newMod,newObj = fields[1:7]
                oldMod = _coerce(oldMod, unicode)
                oldEid = _coerce(oldEid, unicode, AllowNone=True)
                newEid = _coerce(newEid, unicode, AllowNone=True)
                newMod = _coerce(newMod, unicode)
                oldMod,newMod = map(GPath,(oldMod,newMod))
                oldId = (
                    GPath(aliases.get(oldMod,oldMod)),_coerce(oldObj,int,16))
                newId = (
                    GPath(aliases.get(newMod,newMod)),_coerce(newObj,int,16))
                old_new[oldId] = newId
                old_eid[oldId] = oldEid
                new_eid[newId] = newEid

    def updateMod(self,modInfo,changeBase=False):
        """Updates specified mod file."""
        types = self.types
        classes = [MreRecord.type_class[type_] for type_ in types]
        loadFactory = LoadFactory(True,*classes)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        #--Create  filtered versions of mappers.
        mapper = modFile.getShortMapper()
        masters = modFile.tes4.masters + [modFile.fileInfo.name]
        short = dict((oldId,mapper(oldId)) for oldId in self.old_eid if
                     oldId[0] in masters)
        short.update((newId,mapper(newId)) for newId in self.new_eid if
                     newId[0] in masters)
        old_eid = dict(
            (short[oldId],eid) for oldId,eid in self.old_eid.iteritems() if
            oldId in short)
        new_eid = dict(
            (short[newId],eid) for newId,eid in self.new_eid.iteritems() if
            newId in short)
        old_new = dict((short[oldId],short[newId]) for oldId,newId in
                       self.old_new.iteritems() if
                       (oldId in short and newId in short))
        if not old_new: return False
        #--Swapper function
        old_count = {}
        def swapper(oldId):
            newId = old_new.get(oldId,None)
            if newId:
                old_count.setdefault(oldId,0)
                old_count[oldId] += 1
                return newId
            else:
                return oldId
        #--Do swap on all records
        for type_ in types:
            for record in getattr(modFile,type_).getActiveRecords():
                if changeBase: record.fid = swapper(record.fid)
                record.mapFids(swapper,True)
                record.setChanged()
        #--Done
        if not old_count: return False
        modFile.safeSave()
        entries = [(count,old_eid[oldId],new_eid[old_new[oldId]]) for
                   oldId,count in old_count.iteritems()]
        entries.sort(key=itemgetter(1))
        return u'\n'.join([u'%3d %s >> %s' % entry for entry in entries])

class CBash_FidReplacer(object):
    """Replaces one set of fids with another."""

    def __init__(self,types=None,aliases=None):
        self.aliases = aliases or {} #--For aliasing mod names
        self.old_new = {} #--Maps old fid to new fid
        self.old_eid = {} #--Maps old fid to old editor id
        self.new_eid = {} #--Maps new fid to new editor id

    def readFromText(self,textPath):
        """Reads replacement data from specified text file."""
        old_new,old_eid,new_eid = self.old_new,self.old_eid,self.new_eid
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 7 or fields[2][:2] != u'0x'\
                        or fields[6][:2] != u'0x': continue
                oldMod,oldObj,oldEid,newEid,newMod,newObj = fields[1:7]
                oldMod = _coerce(oldMod, unicode)
                oldEid = _coerce(oldEid, unicode)
                newEid = _coerce(newEid, unicode, AllowNone=True)
                newMod = _coerce(newMod, unicode, AllowNone=True)
                oldMod,newMod = map(GPath,(oldMod,newMod))
                oldId = FormID(GPath(aliases.get(oldMod,oldMod)),
                               _coerce(oldObj,int,16))
                newId = FormID(GPath(aliases.get(newMod,newMod)),
                               _coerce(newObj,int,16))
                old_new[oldId] = newId
                old_eid[oldId] = oldEid
                new_eid[newId] = newEid

    def updateMod(self,modInfo,changeBase=False):
        """Updates specified mod file."""
        from . import bosh
        old_new,old_eid,new_eid = self.old_new,self.old_eid,self.new_eid
        #Filter the fid replacements to only include existing mods
        existing = bosh.modInfos.keys()
        old_new = dict((oldId,newId) for oldId,newId in old_new.iteritems() if
                       oldId[0] in existing and newId[0] in existing)
        if not old_new: return False
        # old_count = {} # unused - was meant to be used ?
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            for newId in set(old_new.values()):
                Current.addMod(bosh.modInfos[newId[0]].getPath().stail,
                               Saveable=False)
            modFile = Current.addMod(modInfo.getPath().stail)
            Current.load()
            counts = modFile.UpdateReferences(old_new)
            #--Done
            if not sum(counts): return False
            modFile.save()
            entries = [(count,old_eid[oldId],new_eid[newId]) for
                       count,oldId,newId in
                       zip(counts,old_new.keys(),old_new.values())]
            entries.sort(key=itemgetter(1))
            return u'\n'.join([u'%3d %s >> %s' % entry for entry in entries])

#------------------------------------------------------------------------------
class FullNames(object):
    """Names for records, with functions for importing/exporting from/to
    mod/text file."""

    def __init__(self,types=None,aliases=None):
        self.type_id_name = {} #--(eid,name) = type_id_name[type][longid]
        self.types = types or bush.game.namesTypes
        self.aliases = aliases or {}

    def readFromMod(self,modInfo):
        """Imports type_id_name from specified mod."""
        type_id_name,types = self.type_id_name, self.types
        classes = [MreRecord.type_class[x] for x in self.types]
        loadFactory = LoadFactory(False,*classes)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        for type_ in types:
            typeBlock = modFile.tops.get(type_,None)
            if not typeBlock: continue
            if type_ not in type_id_name: type_id_name[type_] = {}
            id_name = type_id_name[type_]
            for record in typeBlock.getActiveRecords():
                longid = mapper(record.fid)
                full = record.full or (type_ == b'LIGH' and u'NO NAME')
                if record.eid and full:
                    id_name[longid] = (record.eid,full)

    def writeToMod(self,modInfo):
        """Exports type_id_name to specified mod."""
        type_id_name,types = self.type_id_name,self.types
        classes = [MreRecord.type_class[x] for x in self.types]
        loadFactory = LoadFactory(True,*classes)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        changed = {}
        for type_ in types:
            id_name = type_id_name.get(type_,None)
            typeBlock = modFile.tops.get(type_,None)
            if not id_name or not typeBlock: continue
            for record in typeBlock.records:
                longid = mapper(record.fid)
                full = record.full
                eid,newFull = id_name.get(longid,(0,0))
                if newFull and newFull not in (full,u'NO NAME'):
                    record.full = newFull
                    record.setChanged()
                    changed[eid] = (full,newFull)
        if changed: modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Imports type_id_name from specified text file."""
        textPath = GPath(textPath)
        type_id_name = self.type_id_name
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 5 or fields[2][:2] != u'0x': continue
                group,mod,objectIndex,eid,full = fields[:5]
                group = _coerce(group, unicode)
                mod = GPath(_coerce(mod, unicode))
                longid = (aliases.get(mod,mod),_coerce(objectIndex[2:],int,16))
                eid = _coerce(eid, unicode, AllowNone=True)
                full = _coerce(full, unicode, AllowNone=True)
                if group in type_id_name:
                    type_id_name[group][longid] = (eid,full)
                else:
                    type_id_name[group] = {longid:(eid,full)}

    def writeToText(self,textPath):
        """Exports type_id_name to specified text file."""
        textPath = GPath(textPath)
        type_id_name = self.type_id_name
        headFormat = u'"%s","%s","%s","%s","%s"\n'
        rowFormat = u'"%s","%s","0x%06X","%s","%s"\n'
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            out.write(headFormat % (
                _(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id'),
                _(u'Name')))
            for type_ in sorted(type_id_name):
                id_name = type_id_name[type_]
                longids = id_name.keys()
                longids.sort(key=lambda a: id_name[a][0].lower())
                longids.sort(key=itemgetter(0))
                for longid in longids:
                    eid,name = id_name[longid]
                    out.write(rowFormat % (
                        type_,longid[0].s,longid[1],eid,
                        name.replace(u'"',u'""')))

class CBash_FullNames(object):
    """Names for records, with functions for importing/exporting from/to
    mod/text file."""
    defaultTypes = {b'CLAS',b'FACT',b'HAIR',b'EYES',b'RACE',b'MGEF',b'ENCH',b'SPEL',
                    b'BSGN',b'ACTI',b'APPA',b'ARMO',b'BOOK',b'CLOT',b'CONT',b'DOOR',
                    b'INGR',b'LIGH',b'MISC',b'FLOR',b'FURN',b'WEAP',b'AMMO',b'NPC_',
                    b'CREA',b'SLGM',b'KEYM',b'ALCH',b'SGST',b'WRLD',b'CELLS',b'DIAL',
                    b'QUST'}

    def __init__(self,types=None,aliases=None):
        self.group_fid_name = {} #--(eid,name) = group_fid_name[group][longid]
        self.types = types or CBash_FullNames.defaultTypes
        self.aliases = aliases or {}

    def readFromMod(self,modInfo):
        """Imports type_id_name from specified mod."""
        group_fid_name = self.group_fid_name
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,Saveable=False,
                                     LoadMasters=False)
            Current.load()
            for group in self.types:
                fid_name = group_fid_name.setdefault(group[:4],{})
                for record in getattr(modFile,group):
                    if hasattr(record, u'full'):
                        full = record.full or (group == b'LIGH' and u'NO NAME')
                        eid = record.eid
                        if eid and full:
                            fid_name[record.fid] = (eid,full)
                modFile.Unload()

    def writeToMod(self,modInfo):
        """Exports type_id_name to specified mod."""
        group_fid_name = self.group_fid_name
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            changed = {}
            for group in self.types:
                fid_name = group_fid_name.get(group,None)
                if not fid_name: continue
                fid_name = FormID.FilterValidDict(fid_name,modFile,True,False)
                for record in getattr(modFile,group):
                    fid = record.fid
                    full = record.full
                    eid,newFull = fid_name.get(fid,(0,0))
                    if newFull and newFull not in (full,u'NO NAME'):
                        record.full = newFull
                        changed[eid] = (full,newFull)
            if changed: modFile.save()
            return changed

    def readFromText(self,textPath):
        """Imports type_id_name from specified text file."""
        textPath = GPath(textPath)
        group_fid_name = self.group_fid_name
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 5 or fields[2][:2] != u'0x': continue
                group,mod,objectIndex,eid,full = fields[:5]
                group = _coerce(group,unicode)
                mod = GPath(_coerce(mod,unicode))
                longid = FormID(aliases.get(mod,mod),
                                _coerce(objectIndex[2:],int,16))
                eid = _coerce(eid,unicode,AllowNone=True)
                full = _coerce(full,unicode,AllowNone=True)
                group_fid_name.setdefault(group,{})[longid] = (eid,full)

    def writeToText(self,textPath):
        """Exports type_id_name to specified text file."""
        textPath = GPath(textPath)
        group_fid_name = self.group_fid_name
        headFormat = u'"%s","%s","%s","%s","%s"\n'
        rowFormat = u'"%s","%s","0x%06X","%s","%s"\n'
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            outWrite = out.write
            outWrite(headFormat % (
                _(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id'),
                _(u'Name')))
            for group in sorted(group_fid_name):
                fid_name = group_fid_name[group]
                longids = fid_name.keys()
                longids.sort(key=lambda a: fid_name[a][0])
                longids.sort(key=itemgetter(0))
                for longid in longids:
                    eid,name = fid_name[longid]
                    outWrite(rowFormat % (
                        group,longid[0],longid[1],eid,
                        name.replace(u'"',u'""')))

#------------------------------------------------------------------------------
class ItemStats(object):
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

    def __init__(self,types=None,aliases=None):
        self.class_attrs = bush.game.statsTypes
        self.class_fid_attr_value = defaultdict(lambda : defaultdict(dict))
        self.aliases = aliases or {} #--For aliasing mod names
        if bush.game.fsName in (u'Enderal', u'Skyrim',
                                u'Skyrim Special Edition'):
            self.attr_type = {u'eid': self.sstr,
                              u'weight': self.sfloat,
                              u'value': self.sint,
                              u'damage': self.sint,
                              u'armorRating': self.sint,
                              u'duration': self.sint,
                              u'speed': self.sfloat,
                              u'reach': self.sfloat,
                              u'stagger': self.sfloat,
                              u'enchantPoints': self.sint,
                              u'critDamage': self.sint,
                              u'criticalMultiplier': self.sfloat,
                              u'criticalEffect': self.sint,}
        elif bush.game.fsName in (u'FalloutNV', u'Fallout3'):
            self.attr_type = {u'eid': self.sstr,
                              u'weight': self.sfloat,
                              u'value': self.sint,
                              u'damage': self.sint,
                              u'speed': self.sfloat,
                              u'enchantPoints': self.snoneint,
                              u'health': self.sint,
                              u'strength': self.sint,
                              u'duration': self.sint,
                              u'quality': self.sfloat,
                              u'uses': self.sint,
                              u'reach': self.sfloat,
                              u'clipRounds': self.sint,
                              u'projPerShot': self.sint,
                              u'ar': self.sint,
                              u'dt': self.sfloat,
                              u'clipsize': self.sint,
                              u'animationMultiplier': self.sfloat,
                              u'ammoUse': self.sint,
                              u'minSpread': self.sfloat,
                              u'spread': self.sfloat,
                              u'sightFov': self.sfloat,
                              u'baseVatsToHitChance': self.sint,
                              u'projectileCount': self.sint,
                              u'minRange': self.sfloat,
                              u'maxRange': self.sfloat,
                              u'animationAttackMultiplier': self.sfloat,
                              u'fireRate': self.sfloat,
                              u'overrideActionPoint': self.sfloat,
                              u'rumbleLeftMotorStrength': self.sfloat,
                              u'rumbleRightMotorStrength': self.sfloat,
                              u'rumbleDuration': self.sfloat,
                              u'overrideDamageToWeaponMult': self.sfloat,
                              u'attackShotsPerSec': self.sfloat,
                              u'reloadTime': self.sfloat,
                              u'jamTime': self.sfloat,
                              u'aimArc': self.sfloat,
                              u'rambleWavelangth': self.sfloat,
                              u'limbDmgMult': self.sfloat,
                              u'sightUsage': self.sfloat,
                              u'semiAutomaticFireDelayMin': self.sfloat,
                              u'semiAutomaticFireDelayMax': self.sfloat,
                              u'strengthReq': self.sint,
                              u'regenRate': self.sfloat,
                              u'killImpulse': self.sfloat,
                              u'impulseDist': self.sfloat,
                              u'skillReq': self.sint,
                              u'criticalDamage': self.sint,
                              u'criticalMultiplier': self.sfloat,
                              u'vatsSkill': self.sfloat,
                              u'vatsDamMult': self.sfloat,
                              u'vatsAp': self.sfloat,}
        elif bush.game.fsName == u'Oblivion':
            self.attr_type = {u'eid': self.sstr,
                              u'weight': self.sfloat,
                              u'value': self.sint,
                              u'damage': self.sint,
                              u'speed': self.sfloat,
                              u'enchantPoints': self.sint,
                              u'health': self.sint,
                              u'strength': self.sint,
                              u'duration': self.sint,
                              u'quality': self.sfloat,
                              u'uses': self.sint,
                              u'reach': self.sfloat,}

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        typeClasses = [MreRecord.type_class[x] for x in self.class_attrs]
        loadFactory = LoadFactory(False,*typeClasses)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        modFile.convertToLongFids(list(self.class_attrs))
        for group, attrs in self.class_attrs.iteritems():
            for record in getattr(modFile,group).getActiveRecords():
                self.class_fid_attr_value[group][record.fid].update(
                    zip(attrs, map(record.__getattribute__, attrs)))

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        typeClasses = [MreRecord.type_class[x] for x in self.class_attrs]
        loadFactory = LoadFactory(True,*typeClasses)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        changed = Counter() #--changed[modName] = numChanged
        for group, fid_attr_value in self.class_fid_attr_value.iteritems():
            attrs = self.class_attrs[group]
            for record in getattr(modFile,group).getActiveRecords():
                longid = record.fid
                itemStats = fid_attr_value.get(longid,None)
                if not itemStats: continue
                oldValues = dict(zip(attrs,map(record.__getattribute__,attrs)))
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

    def readFromText(self,textPath):
        """Reads stats from specified text file."""
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            attr_type = self.attr_type
            for fields in ins:
                if len(fields) < 3 or fields[2][:2] != u'0x': continue
                group,modName,objectStr = fields[0:3]
                modName = GPath(_coerce(modName,unicode))
                longid = (GPath(aliases.get(modName,modName)),
                    _coerce(objectStr,int,16))
                attrs = self.class_attrs[group]
                attr_value = {}
                for attr, value in zip(attrs, fields[3:3+len(attrs)]):
                    attr_value[attr] = attr_type[attr](value)
                self.class_fid_attr_value[group][longid].update(attr_value)

    def writeToText(self,textPath):
        """Writes stats to specified text file."""
        class_fid_attr_value = self.class_fid_attr_value
        def getSortedIds(fid_attr_value):
            longids = fid_attr_value.keys()
            longids.sort(key=lambda a: fid_attr_value[a][u'eid'].lower())
            longids.sort(key=itemgetter(0))
            return longids
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            def write(out, attrs, values):
                attr_type = self.attr_type
                csvFormat = u''
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
                        csvFormat += u',"{0[%d]}"' % index
                    elif stype is sstr: csvFormat += u',"{0[%d]}"' % index
                    elif stype is sint or stype is snoneint: csvFormat += \
                        u',"{0[%d]:d}"' % index
                    elif stype is sfloat: csvFormat += u',"{0[%d]:f}"' % index
                csvFormat = csvFormat[1:] #--Chop leading comma
                out.write(csvFormat.format(values) + u'\n')
            for group,header in bush.game.statsHeaders:
                fid_attr_value = class_fid_attr_value[group]
                if not fid_attr_value: continue
                attrs = self.class_attrs[group]
                out.write(header)
                for longid in getSortedIds(fid_attr_value):
                    out.write(
                        u'"%s","%s","0x%06X",' % (group,longid[0].s,longid[1]))
                    attr_value = fid_attr_value[longid]
                    write(out, attrs, map(attr_value.get, attrs))

class CBash_ItemStats(object):
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
        return _coerce(value, int, AllowNone=True)

    @staticmethod
    def snoneint(value):
        x = _coerce(value, int, AllowNone=True)
        if x == 0: return None
        return x

    def __init__(self,types=None,aliases=None):
        self.class_attrs = bush.game.statsTypes
        self.class_fid_attr_value = defaultdict(lambda : defaultdict(dict))
        self.aliases = aliases or {} #--For aliasing mod names
        self.attr_type = {u'eid': self.sstr,
                          u'weight': self.sfloat,
                          u'value': self.sint,
                          u'damage': self.sint,
                          u'speed': self.sfloat,
                          u'enchantPoints': self.snoneint,
                          u'health': self.sint,
                          u'strength': self.sint,
                          u'duration': self.sint,
                          u'quality': self.sfloat,
                          u'uses': self.sint,
                          u'reach': self.sfloat,}

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            for group, attrs in self.class_attrs.iteritems():
                for record in getattr(modFile,group):
                    self.class_fid_attr_value[group][record.fid].update(
                        zip(attrs,map(record.__getattribute__,attrs)))

    def writeToMod(self,modInfo):
        """Exports type_id_name to specified mod."""
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            changed = Counter() #--changed[modName] = numChanged
            for group, fid_attr_value in self.class_fid_attr_value.iteritems():
                attrs = self.class_attrs[group]
                fid_attr_value = FormID.FilterValidDict(fid_attr_value,modFile,
                                                        True,False)
                for fid, attr_value in fid_attr_value.iteritems():
                    record = modFile.LookupRecord(fid)
                    if record and record._Type == group:
                        oldValues = dict(
                            zip(attrs,map(record.__getattribute__,attrs)))
                        if oldValues != attr_value:
                            for attr, value in attr_value.iteritems():
                                setattr(record,attr,value)
                            changed[fid[0]] += 1
            if changed: modFile.save()
            return changed

    def readFromText(self,textPath):
        """Reads stats from specified text file."""
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            attr_type = self.attr_type
            for fields in ins:
                if len(fields) < 3 or fields[2][:2] != u'0x': continue
                group,modName,objectStr = fields[0:3]
                modName = GPath(_coerce(modName,unicode))
                longid = FormID(GPath(aliases.get(modName,modName)),
                                _coerce(objectStr,int,16))
                attrs = self.class_attrs[group]
                attr_value = {}
                for attr, value in zip(attrs, fields[3:3+len(attrs)]):
                    attr_value[attr] = attr_type[attr](value)
                self.class_fid_attr_value[group][longid].update(attr_value)

    def writeToText(self,textPath):
        """Writes stats to specified text file."""
        class_fid_attr_value = self.class_fid_attr_value
        def getSortedIds(fid_attr_value):
            longids = fid_attr_value.keys()
            longids.sort(key=lambda a: fid_attr_value[a][u'eid'])
            longids.sort(key=itemgetter(0))
            return longids
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            def write(out, attrs, values):
                attr_type = self.attr_type
                _csvFormat = u''
                sstr = self.sstr
                sint = self.sint
                snoneint = self.snoneint
                sfloat = self.sfloat
                for index, attr in enumerate(attrs):
                    stype = attr_type[attr]
                    values[index] = stype(values[index]) #sanitize output
                    if values[index] is None:
                        _csvFormat += u',"{0[%d]}"' % index
                    elif stype is sstr: _csvFormat += u',"{0[%d]}"' % index
                    elif stype is sint or stype is snoneint: _csvFormat += \
                        u',"{0[%d]:d}"' % index
                    elif stype is sfloat: _csvFormat += u',"{0[%d]:f}"' % index
                _csvFormat = _csvFormat[1:] #--Chop leading comma
                out.write(_csvFormat.format(values) + u'\n')
            for group,header in bush.game.statsHeaders:
                fid_attr_value = class_fid_attr_value[group]
                if not fid_attr_value: continue
                attrs = self.class_attrs[group]
                out.write(header)
                for longid in getSortedIds(fid_attr_value):
                    out.write(
                        u'"%s","%s","0x%06X",' % (group,longid[0],longid[1]))
                    attr_value = fid_attr_value[longid]
                    write(out, attrs, map(attr_value.get, attrs))

#------------------------------------------------------------------------------
class _ScriptText(object):
    """import & export functions for script text."""

    def __init__(self,types=None,aliases=None):
        self.eid_data = {}
        self.aliases = aliases or {} #--For aliasing mod names

    def writeToText(self,textPath,skip,folder,deprefix,esp,skipcomments):
        """Writes stats to specified text file."""
        eid_data = self.eid_data
        skip, deprefix = skip.lower(), deprefix.lower()
        x = len(skip)
        exportedScripts = []
        y = len(eid_data)
        z = 0
        num = 0
        r = len(deprefix)
        with Progress(_(u'Export Scripts')) as progress:
            for eid in sorted(eid_data, key=lambda b: (b, eid_data[b][1])):
                text, longid = eid_data[eid]
                text = decode(text) # TODO(ut) was only present in PBash version - needed ?
                if skipcomments:
                    tmp = u''
                    for line in text.split(u'\n'):
                        pos = line.find(u';')
                        if pos == -1:
                            tmp += line + u'\n'
                        elif pos == 0:
                            continue
                        else:
                            if line[:pos].isspace(): continue
                            tmp += line[:pos] + u'\n'
                    text = tmp
                z += 1
                progress((0.5 + 0.5 / y * z), _(u'Exporting script %s.') % eid)
                if x == 0 or skip != eid[:x].lower():
                    fileName = eid
                    if r >= 1 and deprefix == fileName[:r].lower():
                        fileName = fileName[r:]
                    num += 1
                    outpath = dirs[u'patches'].join(folder).join(
                        fileName + inisettings[u'ScriptFileExt'])
                    with outpath.open(u'wb', encoding=u'utf-8-sig') as out:
                        formid = u'0x%06X' % longid[1]
                        out.write(u';' + longid[0].s + u'\r\n;' + formid + u'\r\n;' + eid + u'\r\n' + text)
                    exportedScripts.append(eid)
        return (_(u'Exported %d scripts from %s:') + u'\n') % (
            num,esp) + u'\n'.join(exportedScripts)

class ScriptText(_ScriptText):

    def readFromMod(self, modInfo, file_):
        """Reads stats from specified mod."""
        eid_data = self.eid_data
        loadFactory = LoadFactory(False,MreRecord.type_class[b'SCPT'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        with Progress(_(u'Export Scripts')) as progress:
            records = modFile.SCPT.getActiveRecords()
            y = len(records)
            z = 0
            for record in records:
                z += 1
                progress((0.5/y*z),_(u'Reading scripts in %s.')% file_)
                eid_data[record.eid] = (record.script_source,
                                        mapper(record.fid))

    def writeToMod(self, modInfo, makeNew=False):
        """Writes scripts to specified mod."""
        eid_data = self.eid_data
        changed = []
        added = []
        loadFactory = LoadFactory(True,MreRecord.type_class[b'SCPT'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        for record in modFile.SCPT.getActiveRecords():
            eid = record.eid
            data = eid_data.get(eid,None)
            if data is not None:
                newText, longid = data
                oldText = record.script_source
                if oldText.lower() != newText.lower():
                    record.script_source = newText
                    record.setChanged()
                    changed.append(eid)
                del eid_data[eid]
        if makeNew and eid_data:
            tes4 = modFile.tes4
            for eid, data in eid_data.iteritems():
                newText, longid = data
                scriptFid = genFid(len(tes4.masters),tes4.getNextObject())
                newScript = MreRecord.type_class[b'SCPT'](
                    RecHeader(b'SCPT', 0, 0x40000, scriptFid, 0))
                newScript.eid = eid
                newScript.script_source = newText
                newScript.setChanged()
                modFile.SCPT.records.append(newScript)
                added.append(eid)
        if changed or added: modFile.safeSave()
        return changed, added

    def readFromText(self,textPath,modInfo):
        """Reads scripts from files in specified mods' directory in bashed
        patches folder."""
        eid_data = self.eid_data
        textPath = GPath(textPath)
        with Progress(_(u'Import Scripts')) as progress:
            for root_dir, dirs, files in textPath.walk():
                y = len(files)
                z = 0
                for name in files:
                    z += 1
                    if name.cext != inisettings[u'ScriptFileExt']:
                        progress(((1/y)*z),_(u'Skipping file %s.') % name.s)
                        continue
                    progress(((1 / y) * z),_(u'Reading file %s.') % name.s)
                    with root_dir.join(name).open(
                            u'r', encoding=u'utf-8-sig') as text:
                        lines = text.readlines()
                    try:
                        modName,FormID,eid = lines[0][1:-2],lines[1][1:-2], \
                                             lines[2][1:-2]
                    except:
                        deprint(
                            _(u'%s has malformed script header lines - was '
                              u'skipped') % name)
                        continue
                    scriptText = u''.join(lines[3:])
                    eid_data[eid] = (scriptText, FormID)
        if eid_data: return True
        return False

class CBash_ScriptText(_ScriptText):

    def readFromMod(self, modInfo, file_):
        """Reads stats from specified mod."""
        eid_data = self.eid_data
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            with Progress(_(u'Export Scripts')) as progress:
                records = modFile.SCPT
                y = len(records)
                z = 0
                for record in records:
                    z += 1
                    progress((0.5/y*z),_(u'Reading scripts in %s.') % file_)
                    eid_data[record.eid] = (record.scriptText,record.fid)

    def writeToMod(self, modInfo, makeNew=False):
        """Writes scripts to specified mod."""
        eid_data = self.eid_data
        changed = []
        added = []
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            for record in modFile.SCPT:
                eid = record.eid
                data = eid_data.get(eid,None)
                if data is not None:
                    newText, longid = data
                    oldText = record.scriptText
                    if oldText != newText:
                        record.scriptText = newText
                        changed.append(eid)
                    del eid_data[eid]
            if makeNew and eid_data:
                for eid, data in eid_data.iteritems():
                    newText, longid = data
                    newScript = modFile.create_SCPT()
                    if newScript is not None:
                        newScript.eid = eid
                        newScript.scriptText = newText
                        added.append(eid)
            if changed or added: modFile.save()
            return changed, added

    def readFromText(self,textPath,modInfo):
        """Reads scripts from files in specified mods' directory in bashed
        patches folder."""
        eid_data = self.eid_data
        textPath = GPath(textPath)
        with Progress(_(u'Import Scripts')) as progress:
            for root_dir, dirs, files in textPath.walk():
                y = len(files)
                z = 0
                for name in files:
                    z += 1
                    if name.cext != inisettings[u'ScriptFileExt']:
                        progress(((1/y)*z),_(u'Skipping file %s.') % name.s)
                        continue
                    progress(((1 / y) * z),_(u'Reading file %s.') % name.s)
                    with root_dir.join(name).open(
                            u'r', encoding=u'utf-8-sig') as text:
                        lines = text.readlines()
                    if not lines: continue
                    modName,formID,eid = lines[0][1:-2],lines[1][1:-2],\
                                         lines[2][1:-2]
                    scriptText = u''.join(lines[3:])
                    eid_data[IUNICODE(eid)] = (
                        IUNICODE(scriptText),formID) #script text is case
                    # insensitive
        if eid_data: return True
        return False

#------------------------------------------------------------------------------
class _UsesEffectsMixin(object):
    """Mixin class to support reading/writing effect data to/from csv files"""
    headers = (
        _(u'Effect'),_(u'Name'),_(u'Magnitude'),_(u'Area'),_(u'Duration'),
        _(u'Range'),_(u'Actor Value'),_(u'SE Mod Name'),_(u'SE ObjectIndex'),
        _(u'SE school'),_(u'SE visual'),_(u'SE Is Hostile'),_(u'SE Name'))
    headerFormat = u'"%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%s",' \
                   u'"%s","%s"'
    recipientTypeNumber_Name = {None:u'NONE',0:u'Self',1:u'Touch',2:u'Target',}
    recipientTypeName_Number = dict(
        [(y.lower(),x) for x,y in recipientTypeNumber_Name.iteritems() if
         x is not None])
    actorValueNumber_Name = dict(
        [(x,y) for x,y in enumerate(bush.game.actor_values)])
    actorValueNumber_Name[None] = u'NONE'
    actorValueName_Number = dict(
        [(y.lower(),x) for x,y in actorValueNumber_Name.iteritems() if
         x is not None])
    schoolTypeNumber_Name = {None:u'NONE',0:u'Alteration',1:u'Conjuration',
                             2:u'Destruction',3:u'Illusion',4:u'Mysticism',
                             5:u'Restoration',}
    schoolTypeName_Number = dict(
        [(y.lower(),x) for x,y in schoolTypeNumber_Name.iteritems() if
         x is not None])

    def readEffects(self,_effects,aliases,doCBash):
        schoolTypeName_Number = _UsesEffectsMixin.schoolTypeName_Number
        recipientTypeName_Number = _UsesEffectsMixin.recipientTypeName_Number
        actorValueName_Number = _UsesEffectsMixin.actorValueName_Number
        effects = []
        while len(_effects) >= 13:
            _effect,_effects = _effects[1:13],_effects[13:]
            name,magnitude,area,duration,range_,actorvalue,semod,seobj,\
            seschool,sevisual,seflags,sename = tuple(_effect)
            name = _coerce(name,unicode,AllowNone=True) #OBME not supported
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
            if None in (name,magnitude,area,duration,range_,actorvalue):
                continue
            if doCBash:
                effect = [MGEFCode(name),magnitude,area,duration,range_,
                          ActorValue(actorvalue)]
            else:
                effect = [name,magnitude,area,duration,range_,actorvalue]
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
            if doCBash:
                if sevisuals == u'':
                    sevisuals = 0
            else:
                if sevisuals == u'' or sevisuals is None:
                    sevisuals = u'\x00\x00\x00\x00'
            sevisual = sevisuals
            seflags = _coerce(seflags, int, AllowNone=True)
            sename = _coerce(sename, unicode, AllowNone=True)
            if None in (semod,seobj,seschool,sevisual,seflags,sename):
                if doCBash:
                    effect.extend(
                        [FormID(None,None),None,MGEFCode(None,None),None,None])
                else:
                    effect.append([])
            else:
                if doCBash:
                    effect.extend(
                        [FormID(GPath(aliases.get(semod,semod)),seobj),
                         seschool,MGEFCode(sevisual),seflags,sename])
                else:
                    effect.append(
                        [(GPath(aliases.get(semod,semod)),seobj),seschool,
                         sevisual,seflags,sename])
            if doCBash:
                effects.append(tuple(effect))
            else:
                effects.append(effect)
        return effects

    def writeEffects(self,effects,doCBash):
        schoolTypeNumber_Name = _UsesEffectsMixin.schoolTypeNumber_Name
        recipientTypeNumber_Name = _UsesEffectsMixin.recipientTypeNumber_Name
        actorValueNumber_Name = _UsesEffectsMixin.actorValueNumber_Name
        effectFormat = u',,"%s","%d","%d","%d","%s","%s"'
        scriptEffectFormat = u',"%s","0x%06X","%s","%s","%s","%s"'
        noscriptEffectFiller = u',"None","None","None","None","None","None"'
        output = []
        for effect in effects:
            if doCBash:
                efname,magnitude,area,duration,range_,actorvalue = effect[:6]
                efname = efname[1] # OBME not supported (support requires
                # adding a mod/objectid format to the csv, this assumes all
                # MGEFCodes are raw)
                actorvalue = actorvalue[1] # OBME not supported (support
                # requires adding a mod/objectid format to the csv,
                # this assumes all ActorValues are raw)
            else:
                efname,magnitude,area,duration,range_,actorvalue = effect[:-1]
            range_ = recipientTypeNumber_Name.get(range_,range_)
            actorvalue = actorValueNumber_Name.get(actorvalue,actorvalue)
            if doCBash:
                scripteffect = effect[6:]
            else:
                scripteffect = effect[-1]
            output.append(effectFormat % (
                efname,magnitude,area,duration,range_,actorvalue))
            if doCBash:
                if None in scripteffect:
                    output.append(noscriptEffectFiller)
                else:
                    semod,seobj,seschool,sevisual,seflags,sename = \
                        scripteffect[0][0],scripteffect[0][1],scripteffect[1],\
                        scripteffect[2],scripteffect[3],scripteffect[4]
                    seschool = schoolTypeNumber_Name.get(seschool,seschool)
                    sevisual = sevisual[1] # OBME not supported (support
                    #  requires adding a mod/objectid format to the csv,
                    # this assumes visual MGEFCode is raw)
                    if sevisual in (None, 0, u''):
                        sevisual = u'NONE'
                    output.append(scriptEffectFormat % (
                        semod,seobj,seschool,sevisual,seflags,sename))
            else:
                if len(scripteffect):
                    longid,seschool,sevisual,seflags,sename = scripteffect
                    if sevisual == u'\x00\x00\x00\x00':
                        sevisual = u'NONE'
                    seschool = schoolTypeNumber_Name.get(seschool,seschool)
                    output.append(scriptEffectFormat % (
                        longid[0].s,longid[1],seschool,sevisual,seflags,
                        sename))
                else:
                    output.append(noscriptEffectFiller)
        return u''.join(output)

#------------------------------------------------------------------------------
class SigilStoneDetails(_UsesEffectsMixin):
    """Details on SigilStones, with functions for importing/exporting
    from/to mod/text file."""

    def __init__(self,types=None,aliases=None):
        self.fid_stats = {}
        self.aliases = aliases or {} #--For aliasing mod names

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        fid_stats = self.fid_stats
        loadFactory = LoadFactory(False,MreRecord.type_class[b'SGST'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        modFile.convertToLongFids([b'SGST'])
        for record in modFile.SGST.getActiveRecords():
            effects = []
            for effect in record.effects:
                effectlist = [effect.name,effect.magnitude,effect.area,
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
        loadFactory = LoadFactory(True,MreRecord.type_class[b'SGST'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        shortMapper = modFile.getShortMapper()
        changed = [] #eids
        for record in modFile.SGST.getActiveRecords():
            newStats = fid_stats.get(mapper(record.fid),None)
            if not newStats: continue
            effects = []
            for effect in record.effects:
                effectlist = [effect.name,effect.magnitude,effect.area,
                              effect.duration,effect.recipient,
                              effect.actorValue]
                if effect.scriptEffect:
                    effectlist.append([mapper(effect.scriptEffect.script),
                                       effect.scriptEffect.school,
                                       effect.scriptEffect.visual,
                                       effect.scriptEffect.flags.hostile,
                                       effect.scriptEffect.full])
                else: effectlist.append([])
                effects.append(effectlist)
            oldStats = [record.eid,record.full,record.model.modPath,
                        round(record.model.modb,6),record.iconPath,
                        mapper(record.script),record.uses,record.value,
                        round(record.weight,6),effects]
            if oldStats != newStats:
                changed.append(oldStats[0]) #eid
                record.eid,record.full,record.model.modPath,\
                record.model.modb,record.iconPath,script,record.uses,\
                record.value,record.weight,effects = newStats
                record.script = shortMapper(script)
                record.effects = []
                for effect in effects:
                    neweffect = record.getDefault(u'effects')
                    neweffect.name,neweffect.magnitude,neweffect.area,\
                    neweffect.duration,neweffect.recipient,\
                    neweffect.actorValue,scripteffect = effect
                    if len(scripteffect):
                        scriptEffect = record.getDefault(
                            u'effects.scriptEffect')
                        script,scriptEffect.school,scriptEffect.visual,\
                        scriptEffect.flags.hostile,scriptEffect.full = \
                            scripteffect
                        scriptEffect.script = shortMapper(script)
                        neweffect.scriptEffect = scriptEffect
                    record.effects.append(neweffect)
                record.setChanged()
        if changed: modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Imports stats from specified text file."""
        fid_stats,aliases = self.fid_stats,self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 12 or fields[1][:2] != u'0x': continue
                mmod,mobj,eid,full,modPath,modb,iconPath,smod,sobj,uses,\
                value,weight = fields[:12]
                mmod = _coerce(mmod,unicode)
                mid = (GPath(aliases.get(mmod,mmod)),_coerce(mobj,int,16))
                smod = _coerce(smod,unicode,AllowNone=True)
                if smod is None: sid = None
                else: sid = (
                    GPath(aliases.get(smod,smod)),_coerce(sobj,int,16))
                eid = _coerce(eid,unicode,AllowNone=True)
                full = _coerce(full,unicode,AllowNone=True)
                modPath = _coerce(modPath,unicode,AllowNone=True)
                modb = _coerce(modb,float)
                iconPath = _coerce(iconPath,unicode,AllowNone=True)
                uses = _coerce(uses,int)
                value = _coerce(value,int)
                weight = _coerce(weight,float)
                effects = self.readEffects(fields[12:],aliases,False)
                fid_stats[mid] = [eid,full,modPath,modb,iconPath,sid,uses,
                                  value,weight,effects]

    def writeToText(self,textPath):
        """Exports stats to specified text file."""
        fid_stats = self.fid_stats
        header = (_(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id'),_(u'Name'),
                  _(u'Model Path'),_(u'Bound Radius'),_(u'Icon Path'),
                  _(u'Script Mod Name'),_(u'Script ObjectIndex'),_(u'Uses'),
                  _(u'Value'),_(u'Weight'),) + _UsesEffectsMixin.headers * 2 +\
                     (_(u'Additional Effects (Same format)'),)
        headFormat = u','.join([u'"%s"'] * len(header)) + u'\n'
        rowFormat = u'"%s","0x%06X","%s","%s","%s","%f","%s","%s","0x%06X",' \
                    u'"%d","%d","%f"'
        altrowFormat = u'"%s","0x%06X","%s","%s","%s","%f","%s","%s","%s",' \
                       u'"%d","%d","%f"'
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            outWrite = out.write
            outWrite(headFormat % header)
            for fid in sorted(fid_stats,key=lambda x:fid_stats[x][0].lower()):
                eid,name,modpath,modb,iconpath,scriptfid,uses,value,weight,\
                effects = fid_stats[fid]
                scriptfid = scriptfid or (GPath(u'None'),None)
                try:
                    output = rowFormat % (
                        fid[0].s,fid[1],eid,name,modpath,modb,iconpath,
                        scriptfid[0].s,scriptfid[1],uses,value,weight)
                except TypeError:
                    output = altrowFormat % (
                        fid[0].s,fid[1],eid,name,modpath,modb,iconpath,
                        scriptfid[0].s,scriptfid[1],uses,value,weight)
                output += self.writeEffects(effects,False)
                output += u'\n'
                outWrite(output)

class CBash_SigilStoneDetails(_UsesEffectsMixin):
    """Details on SigilStones, with functions for importing/exporting
    from/to mod/text file."""

    def __init__(self,types=None,aliases=None):
        self.fid_stats = {}
        self.aliases = aliases or {} #--For aliasing mod names

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        fid_stats = self.fid_stats
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,Saveable=False,
                                     LoadMasters=False)
            Current.load()
            for record in modFile.SGST:
                fid_stats[record.fid] = [record.eid,record.full,record.modPath,
                                         record.modb,record.iconPath,
                                         record.script,record.uses,
                                         record.value,record.weight,
                                         record.effects_list]

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        fid_stats = self.fid_stats
        changed = []
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            fid_stats = FormID.FilterValidDict(fid_stats,modFile,True,False)
            for record in modFile.SGST:
                newStats = fid_stats.get(record.fid,None)
                if not newStats: continue
                if not ValidateList(newStats,modFile): continue
                oldStats = [record.eid,record.full,record.modPath,record.modb,
                            record.iconPath,record.script,record.uses,
                            record.value,record.weight,record.effects_list]
                if oldStats != newStats:
                    changed.append(oldStats[0]) #eid
                    record.eid,record.full,record.modPath,record.modb,\
                    record.iconPath,record.script,record.uses,record.value,\
                    record.weight,effects = newStats
                    record.effects_list = effects
            if changed: modFile.save()
            return changed

    def readFromText(self,textPath):
        """Imports stats from specified text file."""
        fid_stats,aliases = self.fid_stats,self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 12 or fields[1][:2] != u'0x': continue
                mmod,mobj,eid,full,modPath,modb,iconPath,smod,sobj,uses,\
                value,weight = fields[:12]
                mmod = _coerce(mmod,unicode)
                mid = FormID(GPath(aliases.get(mmod,mmod)),
                             _coerce(mobj,int,16))
                smod = _coerce(smod,unicode,AllowNone=True)
                if smod is None: sid = FormID(None,None)
                else: sid = FormID(GPath(aliases.get(smod,smod)),
                                   _coerce(sobj,int,16))
                eid = _coerce(eid,unicode,AllowNone=True)
                full = _coerce(full,unicode,AllowNone=True)
                modPath = _coerce(modPath,unicode,AllowNone=True)
                modb = _coerce(modb,float)
                iconPath = _coerce(iconPath,unicode,AllowNone=True)
                uses = _coerce(uses,int)
                value = _coerce(value,int)
                weight = _coerce(weight,float)
                effects = self.readEffects(fields[12:],aliases,True)
                fid_stats[mid] = [eid,full,modPath,modb,iconPath,sid,uses,
                                  value,weight,effects]

    def writeToText(self,textPath):
        """Exports stats to specified text file."""
        fid_stats = self.fid_stats
        header = (_(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id'),_(u'Name'),
                  _(u'Model Path'),_(u'Bound Radius'),_(u'Icon Path'),
                  _(u'Script Mod Name'),_(u'Script ObjectIndex'),_(u'Uses'),
                  _(u'Value'),_(u'Weight'),) + _UsesEffectsMixin.headers * 2 +\
                     (_(u'Additional Effects (Same format)'),)
        headFormat = u','.join([u'"%s"'] * len(header)) + u'\n'
        rowFormat = u'"%s","0x%06X","%s","%s","%s","%f","%s","%s","0x%06X",' \
                    u'"%d","%d","%f"'
        altrowFormat = u'"%s","0x%06X","%s","%s","%s","%f","%s","%s","%s",' \
                       u'"%d","%d","%f"'
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            outWrite = out.write
            outWrite(headFormat % header)
            for fid in sorted(fid_stats,key=lambda x:fid_stats[x][0]):
                eid,name,modpath,modb,iconpath,scriptfid,uses,value,weight,\
                effects = fid_stats[fid]
                scriptfid = scriptfid or (GPath(u'None'),None)
                try:
                    output = rowFormat % (
                        fid[0],fid[1],eid,name,modpath,modb,iconpath,
                        scriptfid[0],scriptfid[1],uses,value,weight)
                except TypeError:
                    output = altrowFormat % (
                        fid[0],fid[1],eid,name,modpath,modb,iconpath,
                        scriptfid[0],scriptfid[1],uses,value,weight)
                output += self.writeEffects(effects,True)
                output += u'\n'
                outWrite(output)

#------------------------------------------------------------------------------
class _ItemPrices(object):
    item_prices_attrs = (u'value', u'eid', u'full')

class ItemPrices(_ItemPrices):
    """Function for importing/exporting from/to mod/text file only the
    value, name and eid of records."""

    def __init__(self,types=None,aliases=None):
        self.class_fid_stats = bush.game.pricesTypes
        self.aliases = aliases or {} #--For aliasing mod names

    def readFromMod(self,modInfo):
        """Reads data from specified mod."""
        class_fid_stats = self.class_fid_stats
        typeClasses = [MreRecord.type_class[x] for x in class_fid_stats]
        loadFactory = LoadFactory(False,*typeClasses)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        attrs = self.item_prices_attrs
        for group, fid_stats in class_fid_stats.iteritems():
            for record in getattr(modFile,group).getActiveRecords():
                fid_stats[mapper(record.fid)] = map(record.__getattribute__,
                                                    attrs)

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        class_fid_stats = self.class_fid_stats
        typeClasses = [MreRecord.type_class[x] for x in class_fid_stats]
        loadFactory = LoadFactory(True,*typeClasses)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        changed = Counter() #--changed[modName] = numChanged
        for group, fid_stats in class_fid_stats.iteritems():
            for record in getattr(modFile,group).getActiveRecords():
                longid = mapper(record.fid)
                stats = fid_stats.get(longid,None)
                if not stats: continue
                value = stats[0]
                if record.value != value:
                    record.value = value
                    changed[longid[0]] += 1
                    record.setChanged()
        if changed: modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Reads stats from specified text file."""
        class_fid_stats, aliases = self.class_fid_stats, self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 6 or fields[1][:2] != u'0x': continue
                mmod,mobj,value,eid,name,group = fields[:6]
                mmod = GPath(_coerce(mmod, unicode))
                longid = (GPath(aliases.get(mmod,mmod)),_coerce(mobj, int, 16))
                value = _coerce(value, int)
                eid = _coerce(eid, unicode, AllowNone=True)
                name = _coerce(name, unicode, AllowNone=True)
                group = _coerce(group, unicode)
                class_fid_stats[group][longid] = [value,eid,name]

    def writeToText(self,textPath):
        """Writes stats to specified text file."""
        class_fid_stats = self.class_fid_stats
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            format_,header = csvFormat(u'iss'),(u'"' + u'","'.join((
                _(u'Mod Name'),_(u'ObjectIndex'),_(u'Value'),_(u'Editor Id'),
                _(u'Name'),_(u'Type'))) + u'"\n')
            for group, fid_stats in sorted(class_fid_stats.iteritems()):
                if not fid_stats: continue
                out.write(header)
                for fid in sorted(fid_stats,key=lambda x:(
                        fid_stats[x][1].lower(),fid_stats[x][0])):
                    out.write(u'"%s","0x%06X",' % (fid[0].s,fid[1]))
                    out.write(
                        format_ % tuple(fid_stats[fid]) + u',%s\n' % group)

class CBash_ItemPrices(_ItemPrices):
    """Function for importing/exporting from/to mod/text file only the
    value, name and eid of records."""

    def __init__(self,types=None,aliases=None):
        self.class_fid_stats = {b'ALCH':{},b'AMMO':{},b'APPA':{},b'ARMO':{},
                                b'BOOK':{},b'CLOT':{},b'INGR':{},b'KEYM':{},
                                b'LIGH':{},b'MISC':{},b'SGST':{},b'SLGM':{},
                                b'WEAP':{}}
        self.aliases = aliases or {} #--For aliasing mod names

    def readFromMod(self,modInfo):
        """Reads data from specified mod."""
        class_fid_stats, attrs = self.class_fid_stats, self.item_prices_attrs
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            for group, fid_stats in class_fid_stats.iteritems():
                for record in getattr(modFile,group):
                    fid_stats[record.fid] = map(record.__getattribute__,attrs)

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        class_fid_stats = self.class_fid_stats
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            changed = defaultdict(int) #--changed[modName] = numChanged
            for group,fid_stats in class_fid_stats.iteritems():
                fid_stats = FormID.FilterValidDict(fid_stats,modFile,True,
                                                   False)
                for fid,stats in fid_stats.iteritems():
                    record = modFile.LookupRecord(fid)
                    if record and record._Type == group:
                        value = stats[0]
                        if record.value != value:
                            record.value = value
                            changed[fid[0]] += 1
            if changed: modFile.save()
            return changed

    def readFromText(self,textPath):
        """Reads stats from specified text file."""
        class_fid_stats, aliases = self.class_fid_stats, self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 6 or fields[1][:2] != u'0x': continue
                mmod,mobj,value,eid,name,group = fields[:6]
                mmod = GPath(_coerce(mmod, unicode))
                longid = FormID(GPath(aliases.get(mmod,mmod)),
                                _coerce(mobj,int,16))
                value = _coerce(value, int)
                eid = _coerce(eid, unicode, AllowNone=True)
                name = _coerce(name, unicode, AllowNone=True)
                group = _coerce(group, unicode)
                class_fid_stats[group][longid] = [value,eid,name]

    def writeToText(self,textPath):
        """Writes stats to specified text file."""
        class_fid_stats = self.class_fid_stats
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            format_,header = csvFormat(u'iss'),(u'"' + u'","'.join((
                _(u'Mod Name'),_(u'ObjectIndex'),_(u'Value'),_(u'Editor Id'),
                _(u'Name'),_(u'Type'))) + u'"\n')
            for group,fid_stats in sorted(class_fid_stats.iteritems()):
                if not fid_stats: continue
                out.write(header)
                for fid in sorted(fid_stats,key=lambda x:(
                        fid_stats[x][1],fid_stats[x][0])):
                    out.write(u'"%s","0x%06X",' % (fid[0],fid[1]))
                    out.write(
                        format_ % tuple(fid_stats[fid]) + u',%s\n' % group)

#------------------------------------------------------------------------------
class SpellRecords(_UsesEffectsMixin):
    """Statistics for spells, with functions for importing/exporting from/to
    mod/text file."""

    def __init__(self,types=None,aliases=None,detailed=False):
        self.fid_stats = {}
        self.aliases = aliases or {} #--For aliasing mod names
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
        self.spellTypeName_Number = dict(
            [(y.lower(),x) for x,y in self.spellTypeNumber_Name.iteritems() if
             x is not None])
        self.levelTypeNumber_Name = {None : u'NONE',
                                     0    : u'Novice',
                                     1    : u'Apprentice',
                                     2    : u'Journeyman',
                                     3    : u'Expert',
                                     4    : u'Master',}
        self.levelTypeName_Number = dict(
            [(y.lower(),x) for x,y in self.levelTypeNumber_Name.iteritems() if
             x is not None])

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        fid_stats, attrs = self.fid_stats, self.attrs
        detailed = self.detailed
        loadFactory= LoadFactory(False,MreRecord.type_class[b'SPEL'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        modFile.convertToLongFids([b'SPEL'])
        for record in modFile.SPEL.getActiveRecords():
            fid_stats[record.fid] = [getattr_deep(record,attr) for attr in
                                     attrs]
            if detailed:
                effects = []
                for effect in record.effects:
                    effectlist = [effect.name,effect.magnitude,effect.area,
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

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        fid_stats, attrs = self.fid_stats, self.attrs
        detailed = self.detailed
        loadFactory= LoadFactory(True,MreRecord.type_class[b'SPEL'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        shortMapper = modFile.getShortMapper()
        changed = [] #eids
        for record in modFile.SPEL.getActiveRecords():
            newStats = fid_stats.get(mapper(record.fid), None)
            if not newStats: continue
            oldStats = [getattr_deep(record, attr) for attr in attrs]
            if detailed:
                effects = []
                for effect in record.effects:
                    effectlist = [effect.name,effect.magnitude,effect.area,
                                  effect.duration,effect.recipient,
                                  effect.actorValue]
                    if effect.scriptEffect:
                        effectlist.append([mapper(effect.scriptEffect.script),
                                           effect.scriptEffect.school,
                                           effect.scriptEffect.visual,
                                           effect.scriptEffect.flags.hostile,
                                           effect.scriptEffect.full])
                    else: effectlist.append([])
                    effects.append(effectlist)
                oldStats.append(effects)
            if oldStats != newStats:
                changed.append(oldStats[0]) #eid
                for attr, value in zip(attrs, newStats):
                    setattr_deep(record, attr, value)
                if detailed and len(newStats) > len(attrs):
                    effects = newStats[-1]
                    record.effects = []
                    for effect in effects:
                        neweffect = record.getDefault(u'effects')
                        neweffect.name,neweffect.magnitude,neweffect.area,\
                        neweffect.duration,neweffect.recipient,\
                        neweffect.actorValue,scripteffect = effect
                        if len(scripteffect):
                            scriptEffect = record.getDefault(
                                u'effects.scriptEffect')
                            script,scriptEffect.school,scriptEffect.visual,\
                            scriptEffect.flags.hostile,scriptEffect.full = \
                                scripteffect
                            scriptEffect.script = shortMapper(script)
                            neweffect.scriptEffect = scriptEffect
                        record.effects.append(neweffect)
                record.setChanged()
        if changed: modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Imports stats from specified text file."""
        detailed,aliases,spellTypeName_Number,levelTypeName_Number = \
            self.detailed,self.aliases,self.spellTypeName_Number,\
            self.levelTypeName_Number
        fid_stats = self.fid_stats
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 8 or fields[2][:2] != u'0x': continue
                group,mmod,mobj,eid,full,cost,levelType,spellType = fields[:8]
                fields = fields[8:]
                group = _coerce(group, unicode)
                if group.lower() != u'spel': continue
                mmod = _coerce(mmod, unicode)
                mid = (GPath(aliases.get(mmod,mmod)),_coerce(mobj,int,16))
                eid = _coerce(eid, unicode, AllowNone=True)
                full = _coerce(full, unicode, AllowNone=True)
                cost = _coerce(cost, int)
                levelType = _coerce(levelType, unicode)
                levelType = levelTypeName_Number.get(levelType.lower(),
                                                     _coerce(levelType,
                                                             int) or 0)
                spellType = _coerce(spellType, unicode)
                spellType = spellTypeName_Number.get(spellType.lower(),
                                                     _coerce(spellType,
                                                             int) or 0)
                if not detailed or len(fields) < 7:
                    fid_stats[mid] = [eid,full,cost,levelType,spellType]
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
                effects = self.readEffects(fields, aliases, False)
                fid_stats[mid] = [eid,full,cost,levelType,spellType,mc,ss,its,
                                  aeil,saa,daar,tewt,effects]

    def writeToText(self,textPath):
        """Exports stats to specified text file."""
        detailed,fid_stats,spellTypeNumber_Name,levelTypeNumber_Name = \
            self.detailed,self.fid_stats,self.spellTypeNumber_Name,\
            self.levelTypeNumber_Name
        header = (_(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id'),
                  _(u'Name'),_(u'Cost'),_(u'Level Type'),_(u'Spell Type'))
        rowFormat = u'"%s","%s","0x%06X","%s","%s","%d","%s","%s"'
        if detailed:
            header = header + (
                _(u'Manual Cost'),_(u'Start Spell'),_(u'Immune To Silence'),
                _(u'Area Effect Ignores LOS'),_(u'Script Always Applies'),
                _(u'Disallow Absorb and Reflect'),
                _(u'Touch Explodes Without Target'),
            ) + _UsesEffectsMixin.headers * 2 + (
                         _(u'Additional Effects (Same format)'),)
            rowFormat += u',"%s","%s","%s","%s","%s","%s","%s"'
        headFormat = u','.join([u'"%s"'] * len(header)) + u'\n'
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            out.write(headFormat % header)
            for fid in sorted(fid_stats,
                              key=lambda x:(fid_stats[x][0].lower(),x[0])):
                if detailed:
                    eid,name,cost,levelType,spellType,mc,ss,its,aeil,saa,\
                    daar,tewt,effects = \
                    fid_stats[fid]
                    levelType = levelTypeNumber_Name.get(levelType,levelType)
                    spellType = spellTypeNumber_Name.get(spellType,spellType)
                    output = rowFormat % (
                    u'SPEL',fid[0].s,fid[1],eid,name,cost,levelType,spellType,
                    mc,ss,its,aeil,saa,daar,tewt)
                    output += self.writeEffects(effects, False)
                else:
                    eid,name,cost,levelType,spellType = fid_stats[fid]
                    levelType = levelTypeNumber_Name.get(levelType,levelType)
                    spellType = spellTypeNumber_Name.get(spellType,spellType)
                    output = rowFormat % (
                    u'SPEL',fid[0].s,fid[1],eid,name,cost,levelType,spellType)
                output += u'\n'
                out.write(output)

class CBash_SpellRecords(_UsesEffectsMixin):
    """Statistics for spells, with functions for importing/exporting from/to
    mod/text file."""

    def __init__(self,types=None,aliases=None,detailed=False):
        self.fid_stats = {}
        self.aliases = aliases or {} #--For aliasing mod names
        self.attrs = (u'eid', u'full', u'cost', u'levelType', u'spellType')
        self.detailed = detailed
        if detailed:
            self.attrs += (u'IsManualCost', u'IsStartSpell',
                           u'IsSilenceImmune', u'IsAreaEffectIgnoresLOS',
                           u'IsScriptAlwaysApplies',
                           u'IsDisallowAbsorbReflect',
                           u'IsTouchExplodesWOTarget', u'effects_list')
        self.spellTypeNumber_Name = {None : u'NONE',
                                     0    : u'Spell',
                                     1    : u'Disease',
                                     2    : u'Power',
                                     3    : u'LesserPower',
                                     4    : u'Ability',
                                     5    : u'Poison',}
        self.spellTypeName_Number = dict(
            [(y.lower(),x) for x,y in self.spellTypeNumber_Name.iteritems() if
             x is not None])
        self.levelTypeNumber_Name = {None : u'NONE',
                                     0    : u'Novice',
                                     1    : u'Apprentice',
                                     2    : u'Journeyman',
                                     3    : u'Expert',
                                     4    : u'Master',}
        self.levelTypeName_Number = dict(
            [(y.lower(),x) for x,y in self.levelTypeNumber_Name.iteritems() if
             x is not None])

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        fid_stats, attrs = self.fid_stats, self.attrs
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            for record in modFile.SPEL:
                fid_stats[record.fid] = map(record.__getattribute__, attrs)

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        fid_stats, attrs = self.fid_stats, self.attrs
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            changed = []
            for record in modFile.SPEL:
                newStats = fid_stats.get(record.fid, None)
                if not newStats: continue
                if not ValidateList(newStats, modFile): continue
                oldStats = map(record.__getattribute__,attrs)
                if oldStats != newStats:
                    changed.append(oldStats[0]) #eid
                    map(record.__setattr__,attrs,newStats)
            #--Done
            if changed: modFile.save()
            return changed

    def readFromText(self,textPath):
        """Imports stats from specified text file."""
        detailed,aliases,spellTypeName_Number,levelTypeName_Number = \
            self.detailed,self.aliases,self.spellTypeName_Number,\
            self.levelTypeName_Number
        fid_stats = self.fid_stats
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 8 or fields[2][:2] != u'0x': continue
                group,mmod,mobj,eid,full,cost,levelType,spellType = fields[:8]
                fields = fields[8:]
                group = _coerce(group, unicode)
                if group.lower() != u'spel': continue
                mmod = _coerce(mmod, unicode)
                mid = FormID(GPath(aliases.get(mmod,mmod)),
                             _coerce(mobj,int,16))
                eid = _coerce(eid, unicode, AllowNone=True)
                full = _coerce(full, unicode, AllowNone=True)
                cost = _coerce(cost, int)
                levelType = _coerce(levelType, unicode)
                levelType = levelTypeName_Number.get(levelType.lower(),
                                                     _coerce(levelType,
                                                             int) or 0)
                spellType = _coerce(spellType, unicode)
                spellType = spellTypeName_Number.get(spellType.lower(),
                                                     _coerce(spellType,
                                                             int) or 0)
                if not detailed or len(fields) < 7:
                    fid_stats[mid] = [eid,full,cost,levelType,spellType]
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
                effects = self.readEffects(fields, aliases, True)
                fid_stats[mid] = [eid,full,cost,levelType,spellType,mc,ss,its,
                                  aeil,saa,daar,tewt,effects]

    def writeToText(self,textPath):
        """Exports stats to specified text file."""
        detailed,fid_stats,spellTypeNumber_Name,levelTypeNumber_Name = \
            self.detailed,self.fid_stats,self.spellTypeNumber_Name,\
            self.levelTypeNumber_Name
        header = (_(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id'),
                  _(u'Name'),_(u'Cost'),_(u'Level Type'),_(u'Spell Type'))
        rowFormat = u'"%s","%s","0x%06X","%s","%s","%d","%s","%s"'
        if detailed:
            header = header + (
                _(u'Manual Cost'),_(u'Start Spell'),_(u'Immune To Silence'),
                _(u'Area Effect Ignores LOS'),_(u'Script Always Applies'),
                _(u'Disallow Absorb and Reflect'),
                _(u'Touch Explodes Without Target'),
            ) + _UsesEffectsMixin.headers * 2 + (
                         _(u'Additional Effects (Same format)'),)
            rowFormat += u',"%s","%s","%s","%s","%s","%s","%s"'
        headFormat = u','.join([u'"%s"'] * len(header)) + u'\n'
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            out.write(headFormat % header)
            for fid in sorted(fid_stats,key=lambda x:(fid_stats[x][0],x[0])):
                if detailed:
                    eid,name,cost,levelType,spellType,mc,ss,its,aeil,saa,\
                    daar,tewt,effects = fid_stats[fid]
                    levelType = levelTypeNumber_Name.get(levelType,levelType)
                    spellType = spellTypeNumber_Name.get(spellType,spellType)
                    output = rowFormat % (
                        u'SPEL',fid[0],fid[1],eid,name,cost,levelType,
                        spellType,mc,ss,its,aeil,saa,daar,tewt)
                    output += self.writeEffects(effects, True)
                else:
                    eid,name,cost,levelType,spellType = fid_stats[fid]
                    levelType = levelTypeNumber_Name.get(levelType,levelType)
                    spellType = spellTypeNumber_Name.get(spellType,spellType)
                    output = rowFormat % (
                        u'SPEL',fid[0],fid[1],eid,name,cost,levelType,
                        spellType)
                output += u'\n'
                out.write(output)

#------------------------------------------------------------------------------
class IngredientDetails(_UsesEffectsMixin):
    """Details on Ingredients, with functions for importing/exporting
    from/to mod/text file."""

    def __init__(self,types=None,aliases=None):
        self.fid_stats = {}
        self.aliases = aliases or {} #--For aliasing mod names

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        fid_stats = self.fid_stats
        loadFactory= LoadFactory(False,MreRecord.type_class[b'INGR'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        modFile.convertToLongFids([b'INGR'])
        for record in modFile.INGR.getActiveRecords():
            effects = []
            for effect in record.effects:
                effectlist = [effect.name,effect.magnitude,effect.area,
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
        loadFactory = LoadFactory(True,MreRecord.type_class[b'INGR'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        shortMapper = modFile.getShortMapper()
        changed = [] #eids
        for record in modFile.INGR.getActiveRecords():
            newStats = fid_stats.get(mapper(record.fid), None)
            if not newStats: continue
            effects = []
            for effect in record.effects:
                effectlist = [effect.name,effect.magnitude,effect.area,
                              effect.duration,effect.recipient,
                              effect.actorValue]
                if effect.scriptEffect:
                    effectlist.append([mapper(effect.scriptEffect.script),
                                       effect.scriptEffect.school,
                                       effect.scriptEffect.visual,
                                       effect.scriptEffect.flags.hostile,
                                       effect.scriptEffect.full])
                else: effectlist.append([])
                effects.append(effectlist)
            oldStats = [record.eid,record.full,record.model.modPath,
                        round(record.model.modb,6),record.iconPath,
                        mapper(record.script),record.value,
                        round(record.weight,6),effects]
            if oldStats != newStats:
                changed.append(oldStats[0]) #eid
                record.eid,record.full,record.model.modPath,\
                record.model.modb,record.iconPath,script,record.value,\
                record.weight,effects = newStats
                record.script = shortMapper(script)
                record.effects = []
                for effect in effects:
                    neweffect = record.getDefault(u'effects')
                    neweffect.name,neweffect.magnitude,neweffect.area,\
                    neweffect.duration,neweffect.recipient,\
                    neweffect.actorValue,scripteffect = effect
                    if len(scripteffect):
                        scriptEffect = record.getDefault(
                            u'effects.scriptEffect')
                        script,scriptEffect.school,scriptEffect.visual,\
                        scriptEffect.flags.hostile.hostile,scriptEffect.full\
                            = scripteffect
                        scriptEffect.script = shortMapper(script)
                        neweffect.scriptEffect = scriptEffect
                    record.effects.append(neweffect)
                record.setChanged()
        if changed: modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Imports stats from specified text file."""
        fid_stats,aliases = self.fid_stats, self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 11 or fields[1][:2] != u'0x': continue
                mmod,mobj,eid,full,modPath,modb,iconPath,smod,sobj,value,\
                weight = fields[:11]
                mmod = _coerce(mmod, unicode)
                mid = (GPath(aliases.get(mmod,mmod)),_coerce(mobj,int,16))
                smod = _coerce(smod, unicode, AllowNone=True)
                if smod is None: sid = None
                else: sid = (
                    GPath(aliases.get(smod,smod)),_coerce(sobj,int,16))
                eid = _coerce(eid, unicode, AllowNone=True)
                full = _coerce(full, unicode, AllowNone=True)
                modPath = _coerce(modPath, unicode, AllowNone=True)
                modb = _coerce(modb, float)
                iconPath = _coerce(iconPath, unicode, AllowNone=True)
                value = _coerce(value, int)
                weight = _coerce(weight, float)
                effects = self.readEffects(fields[11:], aliases, False)
                fid_stats[mid] = [eid,full,modPath,modb,iconPath,sid,value,
                                  weight,effects]

    def writeToText(self,textPath):
        """Exports stats to specified text file."""
        fid_stats = self.fid_stats
        header = (_(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id'),_(u'Name'),
                  _(u'Model Path'),_(u'Bound Radius'),_(u'Icon Path'),
                  _(u'Script Mod Name'),_(u'Script ObjectIndex'),_(u'Value'),
                  _(u'Weight'),) + _UsesEffectsMixin.headers * 2 + (
                     _(u'Additional Effects (Same format)'),)
        headFormat = u','.join([u'"%s"'] * len(header)) + u'\n'
        rowFormat = u'"%s","0x%06X","%s","%s","%s","%f","%s","%s","0x%06X",' \
                    u'"%d","%f"'
        altrowFormat = u'"%s","0x%06X","%s","%s","%s","%f","%s","%s","%s",' \
                       u'"%d","%f"'
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            out.write(headFormat % header)
            for fid in sorted(fid_stats,key=lambda x:fid_stats[x][0].lower()):
                eid,name,modpath,modb,iconpath,scriptfid,value,weight,\
                effects = fid_stats[fid]
                scriptfid = scriptfid or (GPath(u'None'), None)
                try:
                    output = rowFormat % (
                        fid[0].s,fid[1],eid,name,modpath,modb,iconpath,
                        scriptfid[0].s,scriptfid[1],value,weight)
                except TypeError:
                    output = altrowFormat % (
                        fid[0].s,fid[1],eid,name,modpath,modb,iconpath,
                        scriptfid[0].s,scriptfid[1],value,weight)
                output += self.writeEffects(effects, False)
                output += u'\n'
                out.write(output)

class CBash_IngredientDetails(_UsesEffectsMixin):
    """Details on SigilStones, with functions for importing/exporting
    from/to mod/text file."""

    def __init__(self,types=None,aliases=None):
        self.fid_stats = {}
        self.aliases = aliases or {} #--For aliasing mod names

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        fid_stats = self.fid_stats
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,Saveable=False,
                                     LoadMasters=False)
            Current.load()
            for record in modFile.INGR:
                fid_stats[record.fid] = [record.eid,record.full,record.modPath,
                                         record.modb,record.iconPath,
                                         record.script,record.value,
                                         record.weight,record.effects_list]

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        fid_stats = self.fid_stats
        changed = []
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            fid_stats = FormID.FilterValidDict(fid_stats, modFile, True, False)
            for record in modFile.INGR:
                newStats = fid_stats.get(record.fid, None)
                if not newStats: continue
                if not ValidateList(newStats, modFile): continue
                oldStats = [record.eid,record.full,record.modPath,record.modb,
                            record.iconPath,record.script,record.value,
                            record.weight,record.effects_list]
                if oldStats != newStats:
                    changed.append(oldStats[0]) #eid
                    record.eid,record.full,record.modPath,record.modb,\
                    record.iconPath,record.script,record.value,\
                    record.weight,effects = newStats
                    record.effects_list = effects
            if changed: modFile.save()
            return changed

    def readFromText(self,textPath):
        """Imports stats from specified text file."""
        fid_stats,aliases = self.fid_stats, self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 11 or fields[1][:2] != u'0x': continue
                mmod,mobj,eid,full,modPath,modb,iconPath,smod,sobj,value,\
                weight = fields[:11]
                mmod = _coerce(mmod, unicode)
                mid = FormID(GPath(aliases.get(mmod,mmod)),
                             _coerce(mobj,int,16))
                smod = _coerce(smod, unicode, AllowNone=True)
                if smod is None: sid = FormID(None,None)
                else: sid = FormID(GPath(aliases.get(smod,smod)),
                                   _coerce(sobj,int,16))
                eid = _coerce(eid, unicode, AllowNone=True)
                full = _coerce(full, unicode, AllowNone=True)
                modPath = _coerce(modPath, unicode, AllowNone=True)
                modb = _coerce(modb, float)
                iconPath = _coerce(iconPath, unicode, AllowNone=True)
                value = _coerce(value, int)
                weight = _coerce(weight, float)
                effects = self.readEffects(fields[11:], aliases, True)
                fid_stats[mid] = [eid,full,modPath,modb,iconPath,sid,value,
                                  weight,effects]

    def writeToText(self,textPath):
        """Exports stats to specified text file."""
        fid_stats = self.fid_stats
        header = (_(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id'),_(u'Name'),
                  _(u'Model Path'),_(u'Bound Radius'),_(u'Icon Path'),
                  _(u'Script Mod Name'),_(u'Script ObjectIndex'),_(u'Value'),
                  _(u'Weight'),) + _UsesEffectsMixin.headers * 2 + (
                     _(u'Additional Effects (Same format)'),)
        headFormat = u','.join([u'"%s"'] * len(header)) + u'\n'
        rowFormat = u'"%s","0x%06X","%s","%s","%s","%f","%s","%s","0x%06X",' \
                    u'"%d","%f"'
        altrowFormat = u'"%s","0x%06X","%s","%s","%s","%f","%s","%s","%s",' \
                       u'"%d","%f"'
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            outWrite = out.write
            outWrite(headFormat % header)
            for fid in sorted(fid_stats,key = lambda x: fid_stats[x][0]):
                eid,name,modpath,modb,iconpath,scriptfid,value,weight,\
                effects = fid_stats[fid]
                scriptfid = scriptfid or (GPath(u'None'), None)
                try:
                    output = rowFormat % (
                    fid[0],fid[1],eid,name,modpath,modb,iconpath,scriptfid[0],
                    scriptfid[1],value,weight)
                except TypeError:
                    output = altrowFormat % (
                    fid[0],fid[1],eid,name,modpath,modb,iconpath,scriptfid[0],
                    scriptfid[1],value,weight)
                output += self.writeEffects(effects, True)
                output += u'\n'
                outWrite(output)

#------------------------------------------------------------------------------
# CBASH ONLY
#------------------------------------------------------------------------------
class CBash_MapMarkers(object):
    """Map marker references, with functions for importing/exporting from/to
    mod/text file."""

    def __init__(self,types=None,aliases=None):
        self.fid_markerdata = {}
        self.aliases = aliases or {}
        self.markerFid = FormID(GPath(bush.game.master_file), 0x000010)
        self.attrs = [u'eid', u'markerName', u'markerType', u'IsVisible',
                      u'IsCanTravelTo', u'posX', u'posY', u'posZ', u'rotX',
                      u'rotY', u'rotZ']
        self.markerTypeNumber_Name = {
            None : u'NONE',
            0    : u'NONE',
            1    : u'Camp',
            2    : u'Cave',
            3    : u'City',
            4    : u'Elven Ruin',
            5    : u'Fort Ruin',
            6    : u'Mine',
            7    : u'Landmark',
            8    : u'Tavern',
            9    : u'Settlement',
            10   : u'Daedric Shrine',
            11   : u'Oblivion Gate',
            12   : u'?',
            13   : u'Ayleid Well',
            14   : u'Wayshrine',
            15   : u'Magical Stone',
            16   : u'Spire',
            17   : u'Obelisk of Order',
            18   : u'House',
            19   : u'Player marker (flag)',
            20   : u'Player marker (Q flag)',
            21   : u'Player marker (i flag)',
            22   : u'Player marker (? flag)',
            23   : u'Harbor/dock',
            24   : u'Stable',
            25   : u'Castle',
            26   : u'Farm',
            27   : u'Chapel',
            28   : u'Merchant',
            29   : u'Ayleid Step (old Ayleid ruin icon)',}
        self.markerTypeName_Number = dict(
            [(y.lower(),x) for x,y in self.markerTypeNumber_Name.iteritems() if
             x is not None])

    def readFromMod(self,modInfo):
        """Imports type_id_name from specified mod."""
        fid_markerdata,markerFid,attrs = self.fid_markerdata,self.markerFid,\
                                         self.attrs
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,Saveable=False,
                                     LoadMasters=False)
            Current.load()
            for record in modFile.REFRS:
                if record.base == markerFid:
                    fid_markerdata[record.fid] = [getattr(record,attr) for attr
                                                  in attrs]
                record.UnloadRecord()

    def writeToMod(self,modInfo):
        """Imports type_id_name to specified mod."""
        fid_markerdata,markerFid,attrs = self.fid_markerdata,self.markerFid,\
                                         self.attrs
        changed = []
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            fid_markerdata = FormID.FilterValidDict(fid_markerdata,modFile,
                                                    True,False)
            fid_markerdata = FormID.FilterValidDict(fid_markerdata,modFile,
                                                    True,False)
            for record in modFile.REFRS:
                fid = record.fid
                if not fid in fid_markerdata or record.base != markerFid:
                    record.UnloadRecord()
                    continue
                oldValues = [getattr(record, attr) for attr in attrs]
                newValues = fid_markerdata[fid]
                if oldValues == newValues:
                    record.UnloadRecord()
                    continue
                changed.append(oldValues[0]) #eid
                for attr, value in zip(attrs, newValues):
                    setattr(record, attr, value)
            if changed: modFile.save()
            return changed

    def readFromText(self,textPath):
        """Imports type_id_name from specified text file."""
        fid_markerdata,aliases,markerTypeName_Number = self.fid_markerdata,\
                                        self.aliases,self.markerTypeName_Number
        with CsvReader(GPath(textPath)) as ins:
            for fields in ins:
                if len(fields) < 13 or fields[1][:2] != u'0x': continue
                mod,objectIndex,eid,markerName,_markerType,IsVisible,\
                IsCanTravelTo,posX,posY,posZ,rotX,rotY,rotZ = fields[:13]
                mod = GPath(_coerce(mod, unicode))
                longid = FormID(aliases.get(mod,mod),
                                _coerce(objectIndex,int,16))
                eid = _coerce(eid, unicode, AllowNone=True)
                markerName = _coerce(markerName, unicode, AllowNone=True)
                markerType = _coerce(_markerType, int)
                if markerType is None: #coercion failed
                    markerType = markerTypeName_Number.get(_markerType.lower(),
                                                           0)
                IsVisible = _coerce(IsVisible, bool)
                IsCanTravelTo = _coerce(IsCanTravelTo, bool)
                posX = _coerce(posX, float)
                posY = _coerce(posY, float)
                posZ = _coerce(posZ, float)
                rotX = _coerce(rotX, float)
                rotY = _coerce(rotY, float)
                rotZ = _coerce(rotZ, float)
                fid_markerdata[longid] = [eid,markerName,markerType,IsVisible,
                                          IsCanTravelTo,posX,posY,posZ,rotX,
                                          rotY,rotZ]

    def writeToText(self,textPath):
        """Exports markers to specified text file."""
        fid_markerdata,markerTypeNumber_Name = self.fid_markerdata,\
                                               self.markerTypeNumber_Name
        textPath = GPath(textPath)
        headFormat = u'"%s","%s","%s","%s","%s","%s","%s","%s","%s","%s",' \
                     u'"%s","%s","%s"\n'
        rowFormat = u'"%s","0x%06X","%s","%s","%s","%s","%s","%s","%s","%s",' \
                    u'"%s","%s","%s"\n'
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            outWrite = out.write
            outWrite(headFormat % (
                _(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id'),_(u'Name'),
                _(u'Type'),_(u'IsVisible'),_(u'IsCanTravelTo'),_(u'posX'),
                _(u'posY'),_(u'posZ'),_(u'rotX'),_(u'rotY'),_(u'rotZ')))
            longids = fid_markerdata.keys()
            longids.sort(key=lambda a: fid_markerdata[a][0])
            longids.sort(key=itemgetter(0))
            for longid in longids:
                eid,markerName,markerType,IsVisible,IsCanTravelTo,posX,posY,\
                posZ,rotX,rotY,rotZ = fid_markerdata[longid]
                markerType = markerTypeNumber_Name.get(markerType,markerType)
                outWrite(rowFormat % (
                    longid[0],longid[1],eid,markerName,markerType,IsVisible,
                    IsCanTravelTo,posX,posY,posZ,rotX,rotY,rotZ))

#------------------------------------------------------------------------------
class CBash_CellBlockInfo(object):
    """Map marker references, with functions for importing/exporting from/to
    mod/text file."""

    def __init__(self,types=None,aliases=None):
        self.celldata = {}
        self.aliases = aliases or {}

    def readFromMod(self,modInfo):
        """Imports type_id_name from specified mod."""
        celldata = self.celldata
        with ObCollection(ModsPath=dirs[u'mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,Saveable=False,
                                     LoadMasters=False)
            Current.load()
            for record in modFile.CELLS:
                celldata[record.eid] = record.bsb
                record.UnloadRecord()

    def writeToText(self,textPath):
        """Exports markers to specified text file."""
        celldata = self.celldata
        textPath = GPath(textPath)
        headFormat = u'"%s","%s","%s",\n'
        rowFormat  = u'"%s","%s","%s",\n'
        with textPath.open(u'w', encoding=u'utf-8-sig') as out:
            out.write(
                headFormat % (_(u'Editor Id'),_(u'Block'),_(u'Sub-Block')))
            eids = celldata.keys()
            eids.sort()
            for eid in eids:
                block, subblock = celldata[eid]
                out.write(rowFormat % (eid, block, subblock))
