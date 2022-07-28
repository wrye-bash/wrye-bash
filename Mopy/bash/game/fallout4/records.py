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
"""This module contains the Fallout 4 record classes."""
from ...brec import MelBase, MelGroup, MreHeaderBase, MelSet, MelString, \
    MelStruct, MelNull, MelSimpleArray, MreLeveledListBase, MelFid, \
    FID, MelLString, MelUInt8, MelFloat, MelBounds, MelEdid, MelCounter, \
    MelArray, MreGmstBase, MelUInt8Flags, MelCoed, MelSorted, MelGroups, \
    MelUInt32

#------------------------------------------------------------------------------
# Record Elements    ----------------------------------------------------------
#------------------------------------------------------------------------------
class MelModel(MelGroup):
    """Represents a model subrecord."""
    # MODB and MODD are no longer used by TES5Edit
    typeSets = {
        b'MODL': (b'MODL', b'MODT', b'MODC', b'MODS', b'MODF'),
        b'MOD2': (b'MOD2', b'MODT', b'MO2C', b'MO2S', b'MO2F'),
        b'MOD3': (b'MOD3', b'MODT', b'MO3C', b'MO3S', b'MO3F'),
        b'MOD4': (b'MOD4', b'MODT', b'MO4C', b'MO4S', b'MO4F'),
        b'MOD5': (b'MOD5', b'MODT', b'MO5C', b'MO5S', b'MO5F'),
        # Destructible
        b'DMDL': (b'DMDL', b'DMDT', b'DMDC', b'DMDS'),
    }

    def __init__(self, mel_sig=b'MODL', attr='model'):
        types = self.__class__.typeSets[mel_sig]
        super().__init__(attr,
            MelString(types[0], 'modPath'),
            # Ignore texture hashes - they're only an optimization, plenty
            # of records in Skyrim.esm are missing them
            MelNull(types[1]),
            MelFloat(types[2], 'colorRemappingIndex'),
            MelFid(types[3], 'materialSwap'),
            MelBase(types[3], 'modf_p')
        )

#------------------------------------------------------------------------------
class MreLeveledList(MreLeveledListBase): ##: some duplication with skyrim
    """Fallout 4 leveled list. Defines some common subrecords."""
    __slots__ = []

    class MelLlct(MelCounter):
        def __init__(self):
            super().__init__(MelUInt8(b'LLCT', 'entry_count'),
                counts='entries')

    class MelLvlo(MelSorted):
        def __init__(self, with_coed=True):
            lvl_elements = [
                MelStruct(b'LVLO', ['H', '2s', 'I', 'H', 'B', 's'], 'level',
                    'unused1', (FID, 'listId'), ('count', 1), 'chance_none',
                    'unused2'),
            ]
            lvl_sort_attrs = ('level', 'listId', 'count')
            if with_coed:
                lvl_elements.append(MelCoed())
                lvl_sort_attrs += ('itemCondition', 'owner', 'glob')
            super().__init__(MelGroups('entries', *lvl_elements),
                sort_by_attrs=lvl_sort_attrs)

#------------------------------------------------------------------------------
# Fallout 4 Records -----------------------------------------------------------
#------------------------------------------------------------------------------
class MreTes4(MreHeaderBase):
    """TES4 Record.  File header."""
    rec_sig = b'TES4'

    melSet = MelSet(
        MelStruct(b'HEDR', [u'f', u'2I'], (u'version', 1.0), u'numRecords',
            (u'nextObject', 0x001)),
        MelNull(b'OFST'), # obsolete
        MelNull(b'DELE'), # obsolete
        MreHeaderBase.MelAuthor(),
        MreHeaderBase.MelDescription(),
        MreHeaderBase.MelMasterNames(),
        MelSimpleArray('overrides', MelFid(b'ONAM')),
        MelBase(b'SCRN', 'screenshot'),
        MelGroups('transient_types',
            MelSimpleArray('unknownTNAM', MelFid(b'TNAM'),
                prelude=MelUInt32(b'TNAM', 'form_type')),
        ),
        MelUInt32(b'INTV', 'unknownINTV'),
        MelUInt32(b'INCC', 'internal_cell_count'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreGmst(MreGmstBase):
    """Game Setting."""
    isKeyedByEid = True # NULL fids are acceptable.

#------------------------------------------------------------------------------
class MreLvli(MreLeveledList):
    """Leveled Item."""
    rec_sig = b'LVLI'

    top_copy_attrs = ('chanceNone','maxCount','glob','filterKeywordChances',
                 'epicLootChance','overrideName')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8(b'LVLD', 'chanceNone'),
        MelUInt8(b'LVLM', 'maxCount'),
        MelUInt8Flags(b'LVLF', u'flags', MreLeveledListBase._flags),
        MelFid(b'LVLG', 'glob'),
        MreLeveledList.MelLlct(),
        MreLeveledList.MelLvlo(),
        MelArray('filterKeywordChances',
            MelStruct(b'LLKC', [u'2I'], (FID, u'keyword'), u'chance'),
        ),
        MelFid(b'LVSG', 'epicLootChance'),
        MelLString(b'ONAM', 'overrideName')
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLvln(MreLeveledList):
    """Leveled NPC."""
    rec_sig = b'LVLN'

    top_copy_attrs = ('chanceNone','maxCount','glob','filterKeywordChances',
                 'model','modt_p')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8(b'LVLD', 'chanceNone'),
        MelUInt8(b'LVLM', 'maxCount'),
        MelUInt8Flags(b'LVLF', u'flags', MreLeveledListBase._flags),
        MelFid(b'LVLG', 'glob'),
        MreLeveledList.MelLlct(),
        MreLeveledList.MelLvlo(),
        MelArray('filterKeywordChances',
            MelStruct(b'LLKC', [u'2I'], (FID, u'keyword'), u'chance'),
        ),
        MelString(b'MODL','model'),
        MelBase(b'MODT','modt_p'),
    )
    __slots__ = melSet.getSlotsUsed()
