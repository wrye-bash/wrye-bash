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
from ...bolt import Flags
from ...brec import MelBase, MelGroup, MreHeaderBase, MelSet, MelString, \
    MelStruct, MelNull, MelSimpleArray, MreLeveledListBase, MelFid, MelAttx, \
    FID, MelLString, MelUInt8, MelFloat, MelBounds, MelEdid, MelCounter, \
    MelArray, MreGmstBase, MelUInt8Flags, MelCoed, MelSorted, MelGroups, \
    MelUInt32, MelRecord, MelColorO, MelFull, MelBaseR, MelKeywords, \
    MelColor, MelSoundLooping, MelSoundActivation, MelWaterType, \
    MelActiFlags, MelInteractionKeyword, MelConditions, MelTruncatedStruct, \
    AMelNvnm, ANvnmContext

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
        b'DMDL': (b'DMDL', b'DMDT', b'DMDC', b'DMDS'),
    }

    def __init__(self, mel_sig=b'MODL', attr='model'):
        types = self.__class__.typeSets[mel_sig]
        model_elements = [
            MelString(types[0], 'modPath'),
            # Ignore texture hashes - they're only an optimization, plenty
            # of records in Skyrim.esm are missing them
            MelNull(types[1]),
            MelFloat(types[2], 'color_remapping_index'),
            MelFid(types[3], 'material_swap'),
        ]
        if len(types) == 5:
            model_elements.append(MelBase(types[4], 'unknownMODF'))
        super().__init__(attr, *model_elements)

#------------------------------------------------------------------------------
class MelAnimationSound(MelFid):
    """Handles the common STCP (Animation Sound) subrecord."""
    def __init__(self):
        super().__init__(b'STCP', 'animation_sound')

#------------------------------------------------------------------------------
class MelDestructible(MelGroup):
    """Represents a collection of destruction-related subrecords."""
    _dest_header_flags = Flags.from_names('vats_targetable',
                                          'large_actor_destroys')
    _dest_stage_flags = Flags.from_names('cap_damage', 'disable', 'destroy',
                                         'ignore_external_damage',
                                         'becomes_dynamic')

    def __init__(self):
        super().__init__('destructible',
            MelStruct(b'DEST', ['i', '2B', '2s'], 'health', 'count',
                (MelDestructible._dest_header_flags, 'dest_flags'),
                'dest_unknown'),
            MelSorted(MelArray('resistances',
                MelStruct(b'DAMC', ['2I'], (FID, 'damage_type'),
                    'resistance_value'),
            ), sort_by_attrs='damage_type'),
            MelGroups('stages',
                MelStruct(b'DSTD', ['4B', 'i', '2I', 'i'], 'health', 'index',
                          'damage_stage',
                          (MelDestructible._dest_stage_flags, 'stage_flags'),
                          'self_damage_per_second', (FID, 'explosion'),
                          (FID, 'debris'), 'debris_count'),
                MelString(b'DSTA', 'sequence_name'),
                MelModel(b'DMDL'),
                MelBaseR(b'DSTF', 'dest_end_marker'),
            ),
        )

#------------------------------------------------------------------------------
class MelFtyp(MelFid):
    """Handles the common FTYP (Forced Loc Ref Type) subrecord."""
    def __init__(self):
        super().__init__(b'FTYP', 'forced_loc_ref_type')

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
class MelNativeTerminal(MelFid):
    """Handles the common NTRM (Native Terminal) subrecord."""
    def __init__(self):
        super().__init__(b'NTRM', 'native_terminal')

#------------------------------------------------------------------------------
class MelNvnm(AMelNvnm):
    """Handles the NVNM (Navmesh Geometry) subrecord."""
    class _NvnmContextFo4(ANvnmContext):
        """Provides NVNM context for Fallout 4."""
        max_nvnm_ver = 15
        cover_tri_mapping_has_covers = True
        nvnm_has_waypoints = True

    _nvnm_context_class = _NvnmContextFo4

#------------------------------------------------------------------------------
class MelPreviewTransform(MelFid):
    """Handles the common PTRN (Preview Transform) subrecord."""
    def __init__(self):
        super().__init__(b'PTRN', 'preview_transform')

#------------------------------------------------------------------------------
class MelProperties(MelSorted):
    """Handles the common PRPS (Properites) subrecord."""
    def __init__(self):
        super().__init__(MelArray('properties',
            MelStruct(b'PRPS', ['I', 'f'], (FID, 'prop_actor_value'),
                'prop_value'),
        ))

#------------------------------------------------------------------------------
class MelVmad(MelNull): # TODO(inf) Refactor Skyrim's MelVmad and remove this
    def __init__(self):
        super().__init__(b'VMAD')

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
class MreAact(MelRecord):
    """Action."""
    rec_sig = b'AACT'

    melSet = MelSet(
        MelEdid(),
        MelColorO(),
        MelString(b'DNAM', 'action_notes'),
        MelUInt32(b'TNAM', 'action_type'),
        MelFid(b'DATA', 'attraction_rule'),
        MelFull(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreActi(MelRecord):
    """Activator."""
    rec_sig = b'ACTI'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelPreviewTransform(),
        MelAnimationSound(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelProperties(),
        MelNativeTerminal(),
        MelFtyp(),
        MelColor(b'PNAM'),
        MelSoundLooping(),
        MelSoundActivation(),
        MelWaterType(),
        MelAttx(),
        MelActiFlags(),
        MelInteractionKeyword(),
        MelTruncatedStruct(b'RADR', ['I', '2f', '2B'], (FID, 'rr_sound_model'),
            'rr_frequency', 'rr_volume', 'rr_starts_active',
            'rr_no_signal_static', old_versions={'I2fB'}),
        MelConditions(),
        MelNvnm(),
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
