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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module contains the Fallout 4 record classes. The great majority are
imported from skyrim, but only after setting MelModel to the FO4 format."""
from ... import brec
from ...brec import MelBase, MelGroup, MreHeaderBase, MelSet, MelString, \
    MelStruct, MelUnicode, MelNull, MelFidList, MreLeveledListBase, MelFid, \
    FID, MelLString, MelUInt8, MelOptFid, MelOptFloat, MelBounds, MelEdid, \
    MelArray
# Set brec.MelModel to the Fallout 4 one - do not import from skyrim.records yet
if brec.MelModel is None:

    class _MelModel(MelGroup):
        """Represents a model record."""
        # MODB and MODD are no longer used by TES5Edit
        typeSets = {
            'MODL': ('MODL', 'MODT', 'MODC', 'MODS', 'MODF'),
            'MOD2': ('MOD2', 'MODT', 'MO2C', 'MO2S', 'MO2F'),
            'MOD3': ('MOD3', 'MODT', 'MO3C', 'MO3S', 'MO3F'),
            'MOD4': ('MOD4', 'MODT', 'MO4C', 'MO4S', 'MO4F'),
            'MOD5': ('MOD5', 'MODT', 'MO5C', 'MO5S', 'MO5F'),
            # Destructible
            'DMDL': ('DMDL', 'DMDT', 'DMDC', 'DMDS'),
        }

        def __init__(self, attr='model', subType='MODL'):
            types = self.__class__.typeSets[subType]
            MelGroup.__init__(
                self, attr,
                MelString(types[0], 'modPath'),
                # Ignore texture hashes - they're only an optimization, plenty
                # of records in Skyrim.esm are missing them
                MelNull(types[1]),
                MelOptFloat(types[2], 'colorRemappingIndex'),
                MelOptFid(types[3], 'materialSwap'),
                MelBase(types[3], 'modf_p')
            )

    brec.MelModel = _MelModel
# Now we can import from parent game records file
from ..skyrim.records import MreLeveledList
# Those are unused here, but need be in this file as are accessed via it
from ..skyrim.records import MreGmst # used in basher.app_buttons.App_GenPickle#_update_pkl

#------------------------------------------------------------------------------
# Fallout 4 Records -----------------------------------------------------------
#------------------------------------------------------------------------------
class MreTes4(MreHeaderBase):
    """TES4 Record.  File header."""
    classType = 'TES4'

    melSet = MelSet(
        MelStruct('HEDR', 'f2I', ('version', 1.0), 'numRecords',
                  ('nextObject', 0x800)),
        MelBase('TNAM', 'tnam_p'),
        MelUnicode('CNAM','author',u'',512),
        MelUnicode('SNAM','description',u'',512),
        MreHeaderBase.MelMasterNames(),
        MelFidList('ONAM','overrides',),
        MelBase('SCRN', 'screenshot'),
        MelBase('INTV', 'unknownINTV'),
        MelBase('INCC', 'unknownINCC'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Marker for organization please don't remove ---------------------------------
# GLOB ------------------------------------------------------------------------
# Defined in brec.py as class MreGlob(MelRecord) ------------------------------
#------------------------------------------------------------------------------
class MreLvli(MreLeveledList):
    """Leveled Item."""
    classType = 'LVLI'

    top_copy_attrs = ('chanceNone','maxCount','glob','filterKeywordChances',
                 'epicLootChance','overrideName')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8('LVLD', 'chanceNone'),
        MelUInt8('LVLM', 'maxCount'),
        MelUInt8('LVLF', (MreLeveledListBase._flags, 'flags', 0)),
        MelOptFid('LVLG', 'glob'),
        MreLeveledList.MelLlct(),
        MreLeveledList.MelLvlo(),
        MelArray('filterKeywordChances',
            MelStruct('LLKC', '2I', (FID, 'keyword', None), 'chance'),
        ),
        MelFid('LVSG', 'epicLootChance'),
        MelLString('ONAM', 'overrideName')
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLvln(MreLeveledList):
    """Leveled NPC."""
    classType = 'LVLN'

    top_copy_attrs = ('chanceNone','maxCount','glob','filterKeywordChances',
                 'model','modt_p')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8('LVLD', 'chanceNone'),
        MelUInt8('LVLM', 'maxCount'),
        MelUInt8('LVLF', (MreLeveledListBase._flags, 'flags', 0)),
        MelOptFid('LVLG', 'glob'),
        MreLeveledList.MelLlct(),
        MreLeveledList.MelLvlo(),
        MelArray('filterKeywordChances',
            MelStruct('LLKC', '2I', (FID, 'keyword', None), 'chance'),
        ),
        MelString('MODL','model'),
        MelBase('MODT','modt_p'),
    )
    __slots__ = melSet.getSlotsUsed()
