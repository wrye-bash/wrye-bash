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
"""Builds on the rest of brec to provide full definitions and base classes for
some commonly needed records."""

from operator import attrgetter

from . import utils_constants
from .advanced_elements import FidNotNullDecider, AttrValDecider, MelArray, \
    MelUnion, MelSorted
from .basic_elements import MelBase, MelFid, MelFids, MelFloat, MelGroups, \
    MelLString, MelNull, MelStruct, MelUInt32, MelSInt32, MelFixedString, \
    MelUnicode, unpackSubHeader
from .common_subrecords import MelEdid
from .record_structs import MelRecord, MelSet
from .utils_constants import FID, FormId
from .. import bolt, exception
from ..bolt import decoder, FName, struct_pack, structs_cache, \
    remove_newlines, to_unix_newlines, sig_to_str, to_win_newlines

#------------------------------------------------------------------------------
class MreHeaderBase(MelRecord):
    """File header.  Base class for all 'TES4' like records"""
    # Subrecords that can appear after the masters block - must be set per game
    _post_masters_sigs: set[bytes]

    class MelMasterNames(MelBase):
        """Handles both MAST and DATA, but turns them into two separate lists.
        This is done to make updating the master list much easier."""
        def __init__(self):
            self._debug = False
            self.mel_sig = b'MAST' # just in case something is expecting this

        def getLoaders(self, loaders):
            loaders[b'MAST'] = loaders[b'DATA'] = self

        def getSlotsUsed(self):
            return (u'masters', u'master_sizes')

        def setDefault(self, record):
            record.masters = []
            record.master_sizes = []

        def load_mel(self, record, ins, sub_type, size_, *debug_strs):
            __unpacker=structs_cache[u'Q'].unpack
            if sub_type == b'MAST':
                # Don't use ins.readString, because it will try to use
                # bolt.pluginEncoding for the filename. This is one case where
                # we want to use automatic encoding detection
                master_name = decoder(bolt.cstrip(ins.read(size_, *debug_strs)),
                                      avoidEncodings=(u'utf8', u'utf-8'))
                record.masters.append(FName(master_name))
            else: # sub_type == 'DATA'
                # DATA is the size for TES3, but unknown/unused for later games
                record.master_sizes.append(
                    ins.unpack(__unpacker, size_, *debug_strs)[0])

        def dumpData(self,record,out):
            record._truncate_masters()
            for master_name, master_size in zip(record.masters,
                                                record.master_sizes):
                MelUnicode(b'MAST', '', encoding=u'cp1252').packSub(
                    out, master_name)
                MelBase(b'DATA', '').packSub(
                    out, struct_pack(u'Q', master_size))

    class MelAuthor(MelUnicode):
        def __init__(self):
            from .. import bush
            super().__init__(b'CNAM', 'author_pstr', '',
                bush.game.Esp.max_author_length)

    class MelDescription(MelUnicode):
        def __init__(self):
            from .. import bush
            super().__init__(b'SNAM', 'description_pstr', '',
                bush.game.Esp.max_desc_length)

    @property
    def description(self):
        return to_unix_newlines(self.description_pstr or u'')
    @description.setter
    def description(self, new_desc):
        self.description_pstr = to_win_newlines(new_desc)
    @property
    def author(self):
        return remove_newlines(self.author_pstr or u'')
    @author.setter
    def author(self, new_author):
        self.author_pstr = remove_newlines(new_author)

    def loadData(self, ins, endPos, *, file_offset=0):
        """Loads data from input stream - copy pasted from parent cause we need
        to grab the masters as soon as possible due to ONAM needing FID
        wrapping."""
        loaders = self.__class__.melSet.loaders
        # Load each subrecord
        ins_at_end = ins.atEnd
        masters_loaded = False
        while not ins_at_end(endPos, self._rec_sig):
            sub_type, sub_size = unpackSubHeader(ins, self._rec_sig,
                                                 file_offset=file_offset)
            if not masters_loaded and sub_type in self._post_masters_sigs:
                masters_loaded = True
                utils_constants.FORM_ID = FormId.from_masters(
                    (*self.masters, ins.inName))
            try:
                loader = loaders[sub_type]
                try:
                    loader.load_mel(self, ins, sub_type, sub_size,
                                    self._rec_sig, sub_type) # *debug_strs
                    continue
                except Exception as er:
                    error = er
            except KeyError: # loaders[sub_type]
                # Wrap this error to make it more understandable
                error = f'Unexpected subrecord: {self.rec_str}.' \
                        f'{sig_to_str(sub_type)}'
            file_offset += ins.tell()
            bolt.deprint(self.error_string('loading', file_offset, sub_size,
                                           sub_type))
            if isinstance(error, str):
                raise exception.ModError(ins.inName, error)
            raise exception.ModError(ins.inName, f'{error!r}') from error
        if not masters_loaded:
            augmented_masters = (*self.masters, ins.inName)
            utils_constants.FORM_ID = FormId.from_masters(augmented_masters)
        self._truncate_masters()

    def _truncate_masters(self):
        # TODO(inf) For Morrowind, this will have to query the files for
        #  their size and then store that
        num_masters = self.num_masters
        num_sizes = len(self.master_sizes)
        # Just in case, truncate or pad the sizes with zeroes as needed
        self.master_sizes = self.master_sizes[:num_masters] + [0] * (
                num_masters - num_sizes) # [] * (-n) == []

    def getNextObject(self):
        """Gets next object index and increments it for next time."""
        self.nextObject += 1
        self.setChanged()
        return self.nextObject - 1

    @property
    def num_masters(self): return len(self.masters)

    __slots__ = []

#------------------------------------------------------------------------------
class MreFlst(MelRecord):
    """FormID List."""
    rec_sig = b'FLST'

    melSet = MelSet(
        MelEdid(),
        MelFids('formIDInList', MelFid(b'LNAM')),  # do *not* sort!
    )

    __slots__ = melSet.getSlotsUsed() + [u'mergeOverLast', u'mergeSources',
                                         u'items', u'de_records',
                                         u're_records']

    def __init__(self, header, ins=None, do_unpack=False):
        super(MreFlst, self).__init__(header, ins, do_unpack=do_unpack)
        self.mergeOverLast = False #--Merge overrides last mod merged
        self.mergeSources = None #--Set to list by other functions
        self.items = None #--Set of items included in list
        #--Set of items deleted by list (Deflst mods) unused for Skyrim
        self.de_records = None #--Set of items deleted by list (Deflst mods)
        self.re_records = None # unused, needed by patcher

    def mergeFilter(self, modSet):
        self.formIDInList = [f for f in self.formIDInList if
                             f.mod_id in modSet]

    def mergeWith(self,other,otherMod):
        """Merges newLevl settings and entries with self.
        Requires that: self.items, other.de_records be defined."""
        #--Remove items based on other.removes
        if other.de_records:
            removeItems = self.items & other.de_records
            self.formIDInList = [fi for fi in self.formIDInList
                                 if fi not in removeItems]
            self.items |= other.de_records
        #--Add new items from other
        newItems = set()
        formIDInListAppend = self.formIDInList.append
        newItemsAdd = newItems.add
        for fi in other.formIDInList:
            if fi not in self.items:
                formIDInListAppend(fi)
                newItemsAdd(fi)
        if newItems:
            self.items |= newItems
        #--Is merged list different from other? (And thus written to patch.)
        if len(self.formIDInList) != len(other.formIDInList):
            self.mergeOverLast = True
        else:
            for selfEntry, otherEntry in zip(self.formIDInList,
                                              other.formIDInList):
                if selfEntry != otherEntry:
                    self.mergeOverLast = True
                    break
            else:
                self.mergeOverLast = False
        if self.mergeOverLast:
            self.mergeSources.append(otherMod)
        else:
            self.mergeSources = [otherMod]
        self.setChanged()

#------------------------------------------------------------------------------
class MreGlob(MelRecord):
    """Global record.  Rather stupidly all values, despite their designation
       (short,long,float), are stored as floats -- which means that very large
       integers lose precision."""
    rec_sig = b'GLOB'

    melSet = MelSet(
        MelEdid(),
        MelFixedString(b'FNAM', u'global_format', 1, u's'),
        MelFloat(b'FLTV', u'global_value'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreGmstBase(MelRecord):
    """Game Setting record.  Base class, each game should derive from this
    class."""
    Ids = None
    rec_sig = b'GMST'

    melSet = MelSet(
        MelEdid(),
        MelUnion({
            u'b': MelUInt32(b'DATA', u'value'), # actually a bool
            u'f': MelFloat(b'DATA', u'value'),
            u's': MelLString(b'DATA', u'value'),
        }, decider=AttrValDecider(
            u'eid', transformer=lambda e: e[0] if e else u'i'),
            fallback=MelSInt32(b'DATA', u'value')
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLand(MelRecord):
    """Land structure. Part of exterior cells."""
    rec_sig = b'LAND'

    melSet = MelSet(
        MelBase(b'DATA', u'unknown'),
        MelBase(b'VNML', u'vertex_normals'),
        MelBase(b'VHGT', u'vertex_height_map'),
        MelBase(b'VCLR', u'vertex_colors'),
        MelSorted(MelGroups(u'layers',
            # Start a new layer each time we hit one of these
            MelUnion({
                b'ATXT': MelStruct(b'ATXT', [u'I', u'B', u's', u'h'], (FID, u'atxt_texture'),
                    u'quadrant', u'unknown', u'layer'),
                b'BTXT': MelStruct(b'BTXT', [u'I', u'B', u's', u'h'], (FID, u'btxt_texture'),
                    u'quadrant', u'unknown', u'layer'),
            }),
            # VTXT only exists for ATXT layers, i.e. if ATXT's FormID is valid
            MelUnion({
                True:  MelBase(b'VTXT', u'alpha_layer_data'), # sorted
                False: MelNull(b'VTXT'),
            }, decider=FidNotNullDecider(u'atxt_texture')),
        ), sort_by_attrs=(u'quadrant', u'layer')),
        MelArray(u'vertex_textures',
            MelFid(b'VTEX', u'vertex_texture'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLeveledListBase(MelRecord):
    """Base type for leveled item/creature/npc/spells.
       it requires the base class to use the following:
       classAttributes:
          top_copy_attrs -> List of attributes to modify by copying when
                            merging
          entry_copy_attrs -> List of attributes to modify by copying for each
                              list entry when merging
       instanceAttributes:
          entries -> List of items, with the following attributes:
              listId
              level
              count
          chanceNone
          flags
    """
    _flags = bolt.Flags.from_names(u'calcFromAllLevels', u'calcForEachItem',
                                   u'useAllSpells', u'specialLoot')
    top_copy_attrs = ()
    # TODO(inf) Only overriden for FO3/FNV right now - Skyrim/FO4?
    entry_copy_attrs = (u'listId', u'level', u'count')
    __slots__ = [u'mergeOverLast', u'mergeSources', u'items', u'de_records',
                 u're_records']
                # + ['flags', 'entries'] # define those in the subclasses

    def __init__(self, header, ins=None, do_unpack=False):
        super().__init__(header, ins, do_unpack=do_unpack)
        self.mergeOverLast = False #--Merge overrides last mod merged
        self.mergeSources = None #--Set to list by other functions
        self.items = None #--Set of items included in list
        self.de_records = None #--Set of items deleted by list (Delev and Relev mods)
        self.re_records = None #--Set of items relevelled by list (Relev mods)

    def mergeFilter(self, modSet):
        self.entries = [entry for entry in self.entries if
                        entry.listId.mod_id in modSet]

    def mergeWith(self,other,otherMod):
        """Merges newLevl settings and entries with self.
        Requires that self.items, other.de_records and other.re_records be
        defined."""
        #--Relevel or not?
        if other.re_records:
            for attr in self.__class__.top_copy_attrs:
                setattr(self, attr, getattr(other, attr))
            self.flags = other.flags() # Flags copy!
        else:
            for attr in self.__class__.top_copy_attrs:
                otherAttr = getattr(other, attr)
                if otherAttr is not None:
                    setattr(self, attr, otherAttr)
            self.flags |= other.flags
        #--Remove items based on other.removes
        if other.de_records or other.re_records:
            removeItems = self.items & (other.de_records | other.re_records)
            self.entries = [entry for entry in self.entries if entry.listId not in removeItems]
            self.items = (self.items | other.de_records) - other.re_records
        hasOldItems = bool(self.items)
        #--Add new items from other
        newItems = set()
        entriesAppend = self.entries.append
        newItemsAdd = newItems.add
        for entry in other.entries:
            if entry.listId not in self.items:
                entriesAppend(entry)
                newItemsAdd(entry.listId)
        # Check if merging exceeded the counter's limit and, if so, truncate it
        # and warn. Note that pre-Skyrim games do not have this limitation.
        from .. import bush
        max_lvl_size = bush.game.Esp.max_lvl_list_size
        if max_lvl_size and len(self.entries) > max_lvl_size:
            # TODO(inf) In the future, offer an option to auto-split these into
            #  multiple sub-lists instead
            bolt.deprint(u"Merging changes from mod '%s' to leveled list %r "
                         u'caused it to exceed %u entries. Truncating back '
                         u'to %u, you will have to fix this manually!' %
                         (otherMod, self, max_lvl_size, max_lvl_size))
            self.entries = self.entries[:max_lvl_size]
        entry_copy_attrs_key = attrgetter(*self.__class__.entry_copy_attrs)
        if newItems:
            self.items |= newItems
            self.entries.sort(key=entry_copy_attrs_key)
        #--Is merged list different from other? (And thus written to patch.)
        if ((len(self.entries) != len(other.entries)) or
                (self.flags != other.flags)):
            self.mergeOverLast = True
        else:
            # Check copy-attributes first, break if they are different
            for attr in self.__class__.top_copy_attrs:
                if getattr(self, attr) != getattr(other, attr):
                    self.mergeOverLast = True
                    break
            else:
                # Then, check the sort-attributes, same story
                otherlist = other.entries
                otherlist.sort(key=entry_copy_attrs_key)
                for selfEntry, otherEntry in zip(self.entries, otherlist):
                    for attr in self.__class__.entry_copy_attrs:
                        if getattr(selfEntry, attr) != getattr(
                                otherEntry, attr):
                            break
                    else:
                        # attributes are identical, try next entry
                        continue
                    # attributes differ, no need to look at more entries
                    self.mergeOverLast = True
                    break
                else:
                    # Neither one had different attributes
                    self.mergeOverLast = False
        if self.mergeOverLast:
            self.mergeSources.append(otherMod)
        else:
            self.mergeSources = [otherMod]
        self.setChanged(self.mergeOverLast)

#------------------------------------------------------------------------------
class MreWithItems(MelRecord):
    """Base class for record types that contain a list of items (MelItems)."""
    __slots__ = []

    def mergeFilter(self, modSet):
        self.items = [i for i in self.items if i.item.mod_id in modSet]

#------------------------------------------------------------------------------
class MreActorBase(MreWithItems):
    """Base class for Creatures and NPCs."""
    __slots__ = []

    def mergeFilter(self, modSet):
        super().mergeFilter(modSet)
        self.spells = [x for x in self.spells if x.mod_id in modSet]
        self.factions = [x for x in self.factions if x.faction.mod_id in modSet]
