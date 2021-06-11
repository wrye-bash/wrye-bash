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
"""This module contains the Fallout 4 record classes. The great majority are
imported from skyrim, but only after setting MelModel to the FO4 format."""
from ... import brec
from ...brec import MelBase, MelGroup, MreHeaderBase, MelSet, MelString, \
    MelStruct, MelNull, MelFidList, MreLeveledListBase, MelFid, \
    FID, MelLString, MelUInt8, MelFloat, MelBounds, MelEdid, \
    MelArray, MreGmstBase, MelUInt8Flags

# Set brec.MelModel to the Fallout 4 one - do not import from skyrim.records yet
if brec.MelModel is None:

    class _MelModel(MelGroup):
        """Represents a model record."""
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

        def __init__(self, attr=u'model', mel_sig=b'MODL'):
            types = self.__class__.typeSets[mel_sig]
            MelGroup.__init__(
                self, attr,
                MelString(types[0], u'modPath'),
                # Ignore texture hashes - they're only an optimization, plenty
                # of records in Skyrim.esm are missing them
                MelNull(types[1]),
                MelFloat(types[2], u'colorRemappingIndex'),
                MelFid(types[3], u'materialSwap'),
                MelBase(types[3], u'modf_p')
            )

    brec.MelModel = _MelModel
# Now we can import from parent game records file
from ..skyrim.records import MreLeveledList

#------------------------------------------------------------------------------
# Fallout 4 Records -----------------------------------------------------------
#------------------------------------------------------------------------------
class MreTes4(MreHeaderBase):
    """TES4 Record.  File header."""
    rec_sig = b'TES4'

    melSet = MelSet(
        MelStruct(b'HEDR', [u'f', u'2I'], (u'version', 1.0), u'numRecords',
            (u'nextObject', 0x001)),
        MelBase(b'TNAM', 'tnam_p'),
        MreHeaderBase.MelAuthor(),
        MreHeaderBase.MelDescription(),
        MreHeaderBase.MelMasterNames(),
        MelFidList(b'ONAM','overrides',),
        MelBase(b'SCRN', 'screenshot'),
        MelBase(b'INTV', 'unknownINTV'),
        MelBase(b'INCC', 'unknownINCC'),
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
