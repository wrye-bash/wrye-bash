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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module contains the Morrowind record classes. Also contains records
and subrecords used for the saves - see MorrowindSaveHeader for more
information."""
from ... import bolt, brec
from ...bolt import cstrip, decode, Flags
from ...brec import MelBase, MelSet, MelString, MelStruct, MelArray, \
    MreHeaderBase, MelUnion, SaveDecider, MelNull, MelSequential, MelRecord, \
    MelGroup, MelGroups, MelUInt8
if brec.MelModel is None:

    class _MelModel(MelGroup):
        def __init__(self):
            super(_MelModel, self).__init__(u'model',
                MelString(b'MODL', u'modPath'))

    brec.MelModel = _MelModel
from ...brec import MelModel

#------------------------------------------------------------------------------
# Utilities -------------------------------------------------------------------
#------------------------------------------------------------------------------
def _decode_raw(target_str):
    """Adapted from MelUnicode.loadData. ##: maybe move to bolt/brec?"""
    return u'\n'.join(
        decode(x, avoidEncodings=(u'utf8', u'utf-8')) for x
        in cstrip(target_str).split(b'\n'))

#------------------------------------------------------------------------------
class MelMWId(MelString):
    """Wraps MelString to define a common NAME handler."""
    def __init__(self):
        super(MelMWId, self).__init__(b'NAME', u'mw_id')

#------------------------------------------------------------------------------
class MelMWFull(MelString):
    """Defines FNAM, Morrowind's version of FULL."""
    def __init__(self):
        super(MelMWFull, self).__init__(b'FNAM', u'full')

#------------------------------------------------------------------------------
class MelSavesOnly(MelSequential):
    """Record element that only loads contents if the input file is a save
    file."""
    def __init__(self, *elements):
        super(MelSavesOnly, self).__init__(*(MelUnion({
            True: element,
            False: MelNull(b'ANY')
        }, decider=SaveDecider()) for element in elements))

#------------------------------------------------------------------------------
class MelScriptId(MelString):
    """Handles the common SCRI subrecord."""
    def __init__(self):
        super(MelScriptId, self).__init__(b'SCRI', u'script_id'),

#------------------------------------------------------------------------------
# Shared (plugins + saves) record classes -------------------------------------
#------------------------------------------------------------------------------
class MreTes3(MreHeaderBase):
    """TES3 Record. File header."""
    rec_sig = b'TES3'

    class MelTes3Hedr(MelStruct):
        """Wrapper around MelStruct to handle the author and description
        fields, which are padded to 32 and 256 bytes, respectively, with null
        bytes."""
        def loadData(self, record, ins, sub_type, size_, readId):
            super(MreTes3.MelTes3Hedr, self).loadData(record, ins, sub_type,
                                                      size_, readId)
            # Strip off the null bytes and convert to unicode
            record.author = _decode_raw(record.author)
            record.description = _decode_raw(record.description)

        def dumpData(self, record, out):
            # Store the original values in case we dump more than once
            orig_author = record.author
            orig_desc = record.description
            # Encode and enforce limits, then dump out
            record.author = bolt.encode_complex_string(
                record.author, max_size=32, min_size=32)
            record.description = bolt.encode_complex_string(
                record.description, max_size=256, min_size=256)
            super(MreTes3.MelTes3Hedr, self).dumpData(record, out)
            # Restore the original values again, see comment above
            record.author = orig_author
            record.description = orig_desc

    melSet = MelSet(
        MelTes3Hedr(b'HEDR', u'fI32s256sI', (u'version', 1.3), u'esp_flags',
                    u'author', u'description', u'numRecords'),
        MreHeaderBase.MelMasterNames(),
        MelSavesOnly(
            # Wrye Mash calls unknown1 'day', but that seems incorrect?
            MelStruct(b'GMDT', u'6f64sf32s', u'pc_curr_health',
                      u'pc_max_health', u'unknown1', u'unknown2', u'unknown3',
                      u'unknown4', u'curr_cell', u'unknown5', u'pc_name'),
            MelBase(b'SCRD', u'unknown_scrd'), # likely screenshot-related
            MelArray(u'screenshot_data',
                # Yes, the correct order is bgra
                MelStruct(b'SCRS', u'4B', u'blue', u'green', u'red', u'alpha'),
            ),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Plugins-only record classes -------------------------------------------------
#------------------------------------------------------------------------------
class MreActi(MelRecord):
    """Activator."""
    rec_sig = b'ACTI'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelMWFull(),
        MelScriptId(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAlch(MelRecord):
    """Potion."""
    rec_sig = b'ALCH'

    _potion_flags = Flags(0, Flags.getNames(u'auto_calc'))

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelString(b'TEXT', u'book_text'),
        MelScriptId(),
        MelMWFull(),
        MelStruct(b'ALDT', u'f2I', u'potion_weight', u'potion_value',
            (_potion_flags, u'potion_flags')),
        MelGroups(u'potion_enchantments',
            MelStruct(b'ENAM', u'H2b5I', u'effect_index', u'skill_affected',
                u'attribute_affected', u'ench_range', u'ench_area',
                u'ench_duration', u'ench_magnitude_min',
                u'ench_magnitude_max'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAppa(MelRecord):
    """Alchemical Apparatus."""
    rec_sig = b'APPA'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelMWFull(),
        MelScriptId(),
        MelStruct(b'AADT', u'I2fI', u'appa_type', u'appa_quality',
            u'appa_weight', u'appa_value'),
        MelString(b'ITEX', u'icon_filename'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArmo(MelRecord):
    """Armor."""
    rec_sig = b'ARMO'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelMWFull(),
        MelScriptId(),
        MelStruct(b'AODT', u'If4I', u'armo_type', u'armo_weight',
            u'armo_value', u'armo_health', u'enchant_points', u'armor_rating'),
        MelString(b'ITEX', u'icon_filename'),
        MelGroups(u'armor_data',
            MelUInt8(b'INDX', u'biped_object'),
            MelString(b'BNAM', u'armor_name_male'),
            MelString(b'CNAM', u'armor_name_female'),
        ),
        MelString(b'ENAM', u'enchant_name'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreBody(MelRecord):
    """Body Parts."""
    rec_sig = b'BODY'

    _part_flags = Flags(0, Flags.getNames(u'part_female', u'part_playable'))

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelString(b'FNAM', u'race_name'),
        MelStruct(b'BYDT', u'4B', u'part_index', u'part_vampire',
            (_part_flags, u'part_flags'), u'part_type'),
    )
    __slots__ = melSet.getSlotsUsed()
