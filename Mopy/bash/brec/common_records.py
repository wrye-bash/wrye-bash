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

from collections import defaultdict
from itertools import chain
from operator import attrgetter
from typing import Type

from . import utils_constants
from .advanced_elements import AttrValDecider, MelUnion, MelSorted, \
    MelSimpleArray
from .basic_elements import MelBase, MelFid, MelFids, MelFloat, MelGroups, \
    MelLString, MelNull, MelStruct, MelUInt32, MelSInt32, MelFixedString, \
    MelUnicode, unpackSubHeader, MelUInt32Flags, MelString, MelUInt8Flags
from .common_subrecords import MelEdid, MelDescription, MelImpactDataset, \
    MelColor, MelDebrData, MelFull, MelIcon, MelBounds, MelColorInterpolator, \
    MelValueInterpolator
from .record_structs import MelRecord, MelSet
from .utils_constants import FID, FormId
from .. import bolt, exception
from ..bolt import decoder, FName, struct_pack, structs_cache, Flags, \
    remove_newlines, to_unix_newlines, sig_to_str, to_win_newlines

#------------------------------------------------------------------------------
# Base classes ----------------------------------------------------------------
#------------------------------------------------------------------------------
class AMreWithItems(MelRecord):
    """Base class for record types that contain a list of items (see
    common_subrecords.AMelItems)."""
    __slots__ = ()

    def mergeFilter(self, modSet):
        self.items = [i for i in self.items if i.item.mod_fn in modSet]

#------------------------------------------------------------------------------
class AMreActor(AMreWithItems):
    """Base class for Creatures and NPCs."""
    __slots__ = ()

    def mergeFilter(self, modSet):
        super().mergeFilter(modSet)
        self.spells = [x for x in self.spells if x.mod_fn in modSet]
        self.factions = [x for x in self.factions if x.faction.mod_fn in modSet]

#------------------------------------------------------------------------------
class AMreFlst(MelRecord):
    """Base class for FormID List."""
    rec_sig = b'FLST'
    __slots__ = ('mergeOverLast', 'mergeSources', 'items', 'de_records',
                 're_records')

    def __init__(self, header, ins=None, do_unpack=False):
        super().__init__(header, ins, do_unpack=do_unpack)
        self.mergeOverLast = False #--Merge overrides last mod merged
        self.mergeSources = None #--Set to list by other functions
        self.items = None #--Set of items included in list
        #--Set of items deleted by list (Deflst mods) unused for Skyrim
        self.de_records = None #--Set of items deleted by list (Deflst mods)
        self.re_records = None # unused, needed by patcher

    def mergeFilter(self, modSet):
        self.formIDInList = [f for f in self.formIDInList if
                             f.mod_fn in modSet]

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
class AMreHeader(MelRecord):
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

    __slots__ = ()

#------------------------------------------------------------------------------
class AMreImad(MelRecord):
    """Base class for Image Space Adapters. This is perhaps the weirdest record
    implementation in our codebase. There is a ton of duplication and it's
    really ugly to implement, so we generate most of the subrecords and
    counters programmatically."""
    rec_sig = b'IMAD'

    imad_dof_flags = Flags.from_names(
        'mode_front',
        'mode_back',
        'no_sky',
        'blur_radius_bit_2',
        'blur_radius_bit_1',
        'blur_radius_bit_0',
    )

    dnam_attrs1 = (
        'eye_adapt_speed_mult', 'eye_adapt_speed_add',
        'bloom_blur_radius_mult', 'bloom_blur_radius_add',
        'bloom_threshold_mult', 'bloom_threshold_add', 'bloom_scale_mult',
        'bloom_scale_add', 'target_lum_min_mult', 'target_lum_min_add',
        'target_lum_max_mult', 'target_lum_max_add', 'sunlight_scale_mult',
        'sunlight_scale_add', 'sky_scale_mult', 'sky_scale_add',
        'unknown_08_mult', 'unknown_48_add', 'unknown_09_mult',
        'unknown_49_add', 'unknown_0a_mult', 'unknown_4a_add',
        'unknown_0b_mult', 'unknown_4b_add', 'unknown_0c_mult',
        'unknown_4c_add', 'unknown_0d_mult', 'unknown_4d_add',
        'unknown_0e_mult', 'unknown_4e_add', 'unknown_0f_mult',
        'unknown_4f_add', 'unknown_10_mult', 'unknown_50_add',
        'saturation_mult', 'saturation_add', 'brightness_mult',
        'brightness_add', 'contrast_mult', 'contrast_add', 'unknown_14_mult',
        'unknown_54_add', 'tint_color', 'blur_radius',
        'double_vision_strength', 'radial_blur_strength',
        'radial_blur_ramp_up', 'radial_blur_start')
    dnam_counters1 = tuple(f'{x}_count' for x in dnam_attrs1)
    dnam_attrs2 = ('dof_strength', 'dof_distance', 'dof_range')
    dnam_counters2 = tuple(f'{x}_count' for x in dnam_attrs2)
    dnam_attrs3 = ('radial_blur_ramp_down', 'radial_blur_down_start',
                   'fade_color', 'motion_blur_strength')
    dnam_counters3 = tuple(f'{x}_count' for x in dnam_attrs3)
    dnam_counter_mapping = dict(zip(chain(dnam_counters1, dnam_counters2,
        dnam_counters3), chain(dnam_attrs1, dnam_attrs2, dnam_attrs3)))
    imad_sig_attr = [
        (b'BNAM', 'blur_radius'),
        (b'VNAM', 'double_vision_strength'),
        (b'TNAM', 'tint_color'),
        (b'NAM3', 'fade_color'),
        (b'RNAM', 'radial_blur_strength'),
        (b'SNAM', 'radial_blur_ramp_up'),
        (b'UNAM', 'radial_blur_start'),
        (b'NAM1', 'radial_blur_ramp_down'),
        (b'NAM2', 'radial_blur_down_start'),
        (b'WNAM', 'dof_strength'),
        (b'XNAM', 'dof_distance'),
        (b'YNAM', 'dof_range'),
        (b'NAM4', 'motion_blur_strength'),
        (b'\x00IAD', 'eye_adapt_speed_mult'),
        (b'\x40IAD', 'eye_adapt_speed_add'),
        (b'\x01IAD', 'bloom_blur_radius_mult'),
        (b'\x41IAD', 'bloom_blur_radius_add'),
        (b'\x02IAD', 'bloom_threshold_mult'),
        (b'\x42IAD', 'bloom_threshold_add'),
        (b'\x03IAD', 'bloom_scale_mult'),
        (b'\x43IAD', 'bloom_scale_add'),
        (b'\x04IAD', 'target_lum_min_mult'),
        (b'\x44IAD', 'target_lum_min_add'),
        (b'\x05IAD', 'target_lum_max_mult'),
        (b'\x45IAD', 'target_lum_max_add'),
        (b'\x06IAD', 'sunlight_scale_mult'),
        (b'\x46IAD', 'sunlight_scale_add'),
        (b'\x07IAD', 'sky_scale_mult'),
        (b'\x47IAD', 'sky_scale_add'),
        (b'\x08IAD', 'unknown_08_mult'),
        (b'\x48IAD', 'unknown_48_add'),
        (b'\x09IAD', 'unknown_09_mult'),
        (b'\x49IAD', 'unknown_49_add'),
        (b'\x0AIAD', 'unknown_0a_mult'),
        (b'\x4AIAD', 'unknown_4a_add'),
        (b'\x0BIAD', 'unknown_0b_mult'),
        (b'\x4BIAD', 'unknown_4b_add'),
        (b'\x0CIAD', 'unknown_0c_mult'),
        (b'\x4CIAD', 'unknown_4c_add'),
        (b'\x0DIAD', 'unknown_0d_mult'),
        (b'\x4DIAD', 'unknown_4d_add'),
        (b'\x0EIAD', 'unknown_0e_mult'),
        (b'\x4EIAD', 'unknown_4e_add'),
        (b'\x0FIAD', 'unknown_0f_mult'),
        (b'\x4FIAD', 'unknown_4f_add'),
        (b'\x10IAD', 'unknown_10_mult'),
        (b'\x50IAD', 'unknown_50_add'),
        (b'\x11IAD', 'saturation_mult'),
        (b'\x51IAD', 'saturation_add'),
        (b'\x12IAD', 'brightness_mult'),
        (b'\x52IAD', 'brightness_add'),
        (b'\x13IAD', 'contrast_mult'),
        (b'\x53IAD', 'contrast_add'),
        (b'\x14IAD', 'unknown_14_mult'),
        (b'\x54IAD', 'unknown_54_add'),
    ]
    special_impls: defaultdict[bytes, Type[MelBase]] = defaultdict(
        lambda: MelValueInterpolator)
    # Doing it this way avoids PyCharm complaining about type mismatch
    special_impls[b'TNAM'] = MelColorInterpolator
    special_impls[b'NAM3'] = MelColorInterpolator

    __slots__ = ()

#------------------------------------------------------------------------------
class AMreLeveledList(MelRecord):
    """Base class for leveled item/creature/npc/spells.

    It uses the following attributes:
    Class attributes:
        top_copy_attrs -> List of attributes to modify by copying when merging
        entry_copy_attrs -> List of attributes to modify by copying for each
                            list entry when merging
    Instance attributes:
        entries -> List of items, with the following attributes:
            listId
            level
            count
            chanceNone
            flags"""
    _flags = bolt.Flags.from_names(u'calcFromAllLevels', u'calcForEachItem',
                                   u'useAllSpells', u'specialLoot')
    top_copy_attrs = ()
    # TODO(inf) Only overriden for FO3/FNV right now - Skyrim/FO4?
    entry_copy_attrs = ('listId', 'level', 'count')
    __slots__ = ('mergeOverLast', 'mergeSources', 'items', 'de_records',
                 're_records')
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
                        entry.listId.mod_fn in modSet]

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
# Full classes ----------------------------------------------------------------
#------------------------------------------------------------------------------
class MreAstp(MelRecord):
    """Association Type."""
    rec_sig = b'ASTP'

    melSet = MelSet(
        MelEdid(),
        MelString(b'MPRT', 'male_parent_title'),
        MelString(b'FPRT', 'female_parent_title'),
        MelString(b'MCHT', 'male_child_title'),
        MelString(b'FCHT', 'female_child_title'),
        MelUInt32(b'DATA', 'family_association'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreColl(MelRecord):
    """Collision Layer."""
    rec_sig = b'COLL'

    _coll_flags = Flags.from_names('trigger_volume', 'sensor',
        'navmesh_obstacle')

    melSet = MelSet(
        MelEdid(),
        MelDescription(),
        MelUInt32(b'BNAM', 'layer_index'),
        MelColor(b'FNAM'),
        MelUInt32Flags(b'GNAM', 'layer_flags', _coll_flags),
        MelString(b'MNAM', 'layer_name'),
        MelUInt32(b'INTV', 'interactables_count'),
        MelSorted(MelSimpleArray('collides_with', MelFid(b'CNAM'))),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDebr(MelRecord):
    """Debris."""
    rec_sig = b'DEBR'

    melSet = MelSet(
        MelEdid(),
        MelGroups('debr_models',
            MelDebrData(),
            # Ignore texture hashes - they're only an optimization, plenty
            # of records in Skyrim.esm are missing them
            MelNull(b'MODT'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDlbr(MelRecord):
    """Dialog Branch."""
    rec_sig = b'DLBR'

    _dlbr_flags = Flags.from_names('top_level', 'blocking', 'exclusive')

    melSet = MelSet(
        MelEdid(),
        MelFid(b'QNAM', 'dlbr_quest'),
        MelUInt32(b'TNAM', 'dlbr_category'),
        MelUInt32Flags(b'DNAM', 'dlbr_flags', _dlbr_flags),
        MelFid(b'SNAM', 'starting_topic'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDlvw(MelRecord):
    """Dialog View"""
    rec_sig = b'DLVW'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'QNAM', 'dlvw_quest'),
        MelFids('dlvw_branches', MelFid(b'BNAM')),
        MelGroups('unknown_tnam',
            MelBase(b'TNAM', 'unknown1'),
        ),
        MelBase(b'ENAM', 'unknown_enam'),
        MelBase(b'DNAM', 'unknown_dnam'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDual(MelRecord):
    """Dual Cast Data."""
    rec_sig = b'DUAL'

    _inherit_scale_flags = Flags.from_names('hit_effect_art_scale',
        'projectile_scale', 'explosion_scale')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelStruct(b'DATA', ['6I'], (FID, 'dual_projectile'),
            (FID, 'dual_explosion'), (FID, 'effect_shader'),
            (FID, 'dual_hit_effect_art'), (FID, 'dual_impact_dataset'),
            (_inherit_scale_flags, 'inherit_scale_flags')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEyes(MelRecord):
    """Eyes."""
    rec_sig = b'EYES'

    # not_male and not_female exist since FO3
    _eyes_flags = Flags.from_names('playable', 'not_male', 'not_female')

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelIcon(),
        MelUInt8Flags(b'DATA', 'flags', _eyes_flags),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFstp(MelRecord):
    """Footstep."""
    rec_sig = b'FSTP'

    melSet = MelSet(
        MelEdid(),
        MelImpactDataset(b'DATA'),
        MelString(b'ANAM', 'fstp_tag'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFsts(MelRecord):
    """Footstep Set."""
    rec_sig = b'FSTS'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'XCNT', ['5I'], 'count_walking', 'count_running',
            'count_sprinting', 'count_sneaking', 'count_swimming'),
        MelSimpleArray('footstep_sets', MelFid(b'DATA')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreGlob(MelRecord):
    """Global."""
    rec_sig = b'GLOB'

    melSet = MelSet(
        MelEdid(),
        MelFixedString(b'FNAM', 'global_format', 1, 's'),
        # Rather stupidly all values, despite their designation (short, long,
        # float, bool (FO4)), are stored as floats - which means that very
        # large integers lose precision
        MelFloat(b'FLTV', 'global_value'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreGmst(MelRecord):
    """Game Setting.."""
    rec_sig = b'GMST'
    isKeyedByEid = True # NULL fids are acceptable.

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
