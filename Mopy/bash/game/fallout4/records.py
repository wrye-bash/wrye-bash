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
    FID, MelLString, MelUInt8, MelFloat, MelBounds, MelEdid, MelUnloadEvent, \
    MelArray, MreGmstBase, MelUInt8Flags, MelSorted, MelGroups, MelShortName, \
    MelUInt32, MelRecord, MelColorO, MelFull, MelBaseR, MelKeywords, MelRace, \
    MelColor, MelSound, MelSoundActivation, MelWaterType, MelAlchEnit, \
    MelActiFlags, MelInteractionKeyword, MelConditions, MelTruncatedStruct, \
    AMelNvnm, ANvnmContext, MelNodeIndex, MelAddnDnam, MelUnion, MelIcons, \
    AttrValDecider, MelSoundPickup, MelSoundDrop, MelEquipmentType, AMelVmad, \
    MelDescription, MelEffects, AMelLLItems, MelValueWeight, AVmadContext, \
    MelIcon, MelConditionList, MelPerkData, MelNextPerk, MelSInt8, MelUInt16, \
    MelUInt16Flags, perk_effect_key, MelPerkParamsGroups, PerkEpdfDecider, \
    MelUInt32Flags, BipedFlags, MelArmaDnam, MelArmaModels, MelArmaSkins, \
    MelAdditionalRaces, MelFootstepSound, MelArtObject, MelEnchantment, \
    MelIcons2, MelBids, MelBamt, MelTemplateArmor, MelObjectTemplate, \
    MelArtType, MelAspcRdat, MelAspcBnam, MelAstpTitles, MelAstpData

#------------------------------------------------------------------------------
# Record Elements    ----------------------------------------------------------
#------------------------------------------------------------------------------
class MelModel(MelGroup):
    """Represents a model subrecord."""
    # MODB and MODD are no longer used by TES5Edit
    typeSets = {
        b'MODL': (b'MODL', b'MODT', b'MODC', b'MODS', b'MODF'),
        b'MOD2': (b'MOD2', b'MO2T', b'MO2C', b'MO2S', b'MO2F'),
        b'MOD3': (b'MOD3', b'MO3T', b'MO3C', b'MO3S', b'MO3F'),
        b'MOD4': (b'MOD4', b'MO4T', b'MO4C', b'MO4S', b'MO4F'),
        b'MOD5': (b'MOD5', b'MO5T', b'MO5C', b'MO5S', b'MO5F'),
        b'DMDL': (b'DMDL', b'DMDT', b'DMDC', b'DMDS'),
    }

    def __init__(self, mel_sig=b'MODL', attr='model', *, swap_3_4=False,
            always_use_modc=False, skip_5=False):
        """Fallout 4 has a whole lot of model nonsense:

        :param swap_3_4: If True, swaps the third (*C) and fourth (*S)
            elements.
        :param always_use_modc: If True, use MODC for the third (*C) element,
            regardless of what mel_sig is.
        :param skip_5: If True, skip the fifth (*F) element."""
        types = self.__class__.typeSets[mel_sig]
        mdl_elements = [
            MelString(types[0], 'modPath'),
            # Ignore texture hashes - they're only an optimization, plenty
            # of records in Skyrim.esm are missing them
            MelNull(types[1]),
            MelFloat(b'MODC' if always_use_modc else types[2],
                'color_remapping_index'),
            MelFid(types[3], 'material_swap'),
        ]
        if swap_3_4:
            mdl_elements[2], mdl_elements[3] = mdl_elements[3], mdl_elements[2]
        if len(types) == 5 and not skip_5:
            mdl_elements.append(MelBase(types[4], 'unknown_modf'))
        super().__init__(attr, *mdl_elements)

#------------------------------------------------------------------------------
class MelAnimationSound(MelFid):
    """Handles the common STCP (Animation Sound) subrecord."""
    def __init__(self):
        super().__init__(b'STCP', 'animation_sound')

#------------------------------------------------------------------------------
class MelAppr(MelSimpleArray):
    """Handles the common APPR (Attach Parent Slots) subrecord."""
    def __init__(self):
        super().__init__('attach_parent_slots', MelFid(b'APPR'))

#------------------------------------------------------------------------------
class MelBod2(MelUInt32Flags):
    """Handles the BOD2 (Biped Body Template) subrecord."""
    _bp_flags = BipedFlags.from_names()

    def __init__(self):
        super().__init__(b'BOD2', 'biped_flags', self._bp_flags)

#------------------------------------------------------------------------------
class MelBoneData(MelGroups):
    """Handles the bone data subrecord complex."""
    def __init__(self):
        super().__init__('bone_data',
            MelUInt32(b'BSMP', 'bone_scale_gender'),
            MelGroups('bone_weight_scales',
                MelString(b'BSMB', 'bone_name'),
                # In the latest version of xEdit's source code, the decoding
                # for this particular part is much more complex - would
                # probably have to require custom code to handle (custom
                # handler for duplicate signatures inside a single MelGroups,
                # plus conditional loading to read one subrecord ahead and
                # check its size). This works fine and is *way* simpler, so not
                # going to bother.
                MelSimpleArray('weight_scale_values', MelFloat(b'BSMS')),
                MelUInt32(b'BMMP', 'bone_modifies_gender'),
            ),
        )

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
            MelResistances(b'DAMC'),
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
class MelLLItems(AMelLLItems):
    """Handles the LVLO and LLCT subrecords defining leveled list items"""
    def __init__(self):
        super().__init__([MelStruct(b'LVLO', ['H', '2s', 'I', 'H', 'B', 's'],
            'level', 'unused1', (FID, 'listId'), ('count', 1), 'chance_none',
            'unused2')])

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
class MelResistances(MelSorted):
    """Handles a sorted array of resistances. Signatures vary."""
    def __init__(self, res_sig):
        super().__init__(MelArray('resistances',
            MelStruct(res_sig, ['2I'], (FID, 'damage_type'),
                'resistance_value'),
        ), sort_by_attrs='damage_type')

#------------------------------------------------------------------------------
class MelSoundCrafting(MelFid):
    """Handles the common CUSD (Sound - Crafting) subrecord."""
    def __init__(self):
        super().__init__(b'CUSD', 'sound_crafting')

#------------------------------------------------------------------------------
class MelVmad(AMelVmad):
    class _VmadContextFo4(AVmadContext):
        """Provides VMAD context for Fallout 4."""
        max_vmad_ver = 6

    _vmad_context_class = _VmadContextFo4

#------------------------------------------------------------------------------
# Fallout 4 Records -----------------------------------------------------------
#------------------------------------------------------------------------------
class MreTes4(MreHeaderBase):
    """TES4 Record.  File header."""
    rec_sig = b'TES4'
    _post_masters_sigs = {b'ONAM', b'SCRN', b'TNAM', b'INTV', b'INCC'}

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
        MelSound(),
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
class MreAddn(MelRecord):
    """Addon Node."""
    rec_sig = b'ADDN'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelNodeIndex(),
        MelSound(),
        MelFid(b'LNAM', 'addon_light'),
        MelAddnDnam(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAech(MelRecord):
    """Audio Effect Chain."""
    rec_sig = b'AECH'

    melSet = MelSet(
        MelEdid(),
        MelGroups('chain_effects',
            MelUInt32(b'KNAM', 'ae_type'),
            MelUnion({
                # BSOverdrive - 'Overdrive'
                0x864804BE: MelStruct(b'DNAM', ['I', '4f'], 'ae_enabled',
                    'od_input_gain', 'od_output_gain', 'od_upper_threshold',
                    'od_lower_threshold'),
                # BSStateVariableFilter - 'State Variable Filter'
                0xEF575F7F: MelStruct(b'DNAM', ['I', '2f', 'I'], 'ae_enabled',
                    'svf_center_freq', 'svf_q_value', 'svf_filter_mode'),
                # BSDelayEffect - 'Delay Effect'
                0x18837B4F: MelStruct(b'DNAM', ['I', '2f', 'I'], 'ae_enabled',
                    'de_feedback_pct', 'de_wet_mix_pct', 'de_delay_ms'),
            }, decider=AttrValDecider('ae_type')),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAlch(MelRecord):
    """Ingestible."""
    rec_sig = b'ALCH'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelKeywords(),
        MelModel(),
        MelIcons(),
        MelSoundPickup(),
        MelSoundDrop(),
        MelEquipmentType(),
        MelSoundCrafting(),
        MelDestructible(),
        MelDescription(),
        MelAlchEnit(),
        MelLString(b'DNAM', 'addiction_name'),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAmdl(MelRecord):
    """Aim Model."""
    rec_sig = b'AMDL'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DNAM', ['4f', 'I', '6f', 'I', '4f'], 'cof_min_angle',
            'cof_max_angle', 'cof_increase_per_shot', 'cof_decrease_per_shot',
            'cof_decrease_delay_ms', 'cof_sneak_mult',
            'recoil_diminish_spring_force', 'recoil_diminish_sights_mult',
            'recoil_max_per_shot', 'recoil_min_per_shot', 'recoil_hip_mult',
            'runaway_recoil_shots', 'recoil_arc', 'recoil_arc_rotate',
            'cof_iron_sights_mult', 'base_stability'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAmmo(MelRecord):
    """Ammunition."""
    rec_sig = b'AMMO'

    _ammo_flags = Flags.from_names('notNormalWeapon', 'nonPlayable',
        'has_count_based_3d')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelSoundPickup(),
        MelSoundDrop(),
        MelDescription(),
        MelKeywords(),
        MelValueWeight(),
        MelStruct(b'DNAM', ['I', 'B', '3s', 'f', 'I'], (FID, 'projectile'),
            (_ammo_flags, 'flags'), 'unused_dnam', 'damage', 'health'),
        MelShortName(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAnio(MelRecord):
    """Animated Object."""
    rec_sig = b'ANIO'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelUnloadEvent(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAoru(MelRecord):
    """Attraction Rule."""
    rec_sig = b'AORU'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'AOR2', ['3f', '2B', '2s'], 'attraction_radius',
            'attraction_min_delay', 'attraction_max_delay',
            'requires_line_of_sight', 'combat_target', 'unused_aor2'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArma(MelRecord):
    """Armor Addon."""
    rec_sig = b'ARMA'

    melSet = MelSet(
        MelEdid(),
        MelBod2(),
        MelRace(),
        MelArmaDnam(),
        MelArmaModels(MelModel),
        MelArmaSkins(),
        MelAdditionalRaces(),
        MelFootstepSound(),
        MelArtObject(),
        MelBoneData(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArmo(MelRecord):
    """Armor."""
    rec_sig = b'ARMO'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelEnchantment(),
        MelModel(b'MOD2', 'maleWorld', always_use_modc=True, skip_5=True),
        MelIcons('maleIconPath', 'maleSmallIconPath'),
        MelModel(b'MOD4', 'femaleWorld', always_use_modc=True, skip_5=True),
        MelIcons2(),
        MelBod2(),
        MelDestructible(),
        MelSoundPickup(),
        MelSoundDrop(),
        MelEquipmentType(),
        MelBids(),
        MelBamt(),
        MelRace(),
        MelKeywords(),
        MelDescription(),
        MelFid(b'INRD', 'instance_naming'),
        MelGroups('addons',
            MelUInt16(b'INDX', 'addon_index'),
            MelFid(b'MODL', 'addon_fid'),
        ),
        MelStruct(b'DATA', ['i', 'f', 'I'], 'value', 'weight', 'health'),
        MelStruct(b'FNAM', ['2H', 'B', '3s'], 'armorRating',
            'base_addon_index', 'stagger_rating', 'unknown_fnam'),
        MelResistances(b'DAMA'),
        MelTemplateArmor(),
        MelAppr(),
        MelObjectTemplate(),
    ).with_distributor({
        b'FULL': 'full',
        b'OBTE': {
            b'FULL': 'ot_combinations',
        },
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArto(MelRecord):
    """Art Object."""
    rec_sig = b'ARTO'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelPreviewTransform(),
        MelKeywords(),
        MelModel(),
        MelArtType(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAspc(MelRecord):
    """Acoustic Space."""
    rec_sig = b'ASPC'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelSound(),
        MelAspcRdat(),
        MelAspcBnam(),
        MelUInt8(b'XTRI', 'aspc_is_interior'),
        MelUInt16(b'WNAM', 'weather_attenuation'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAstp(MelRecord):
    """Association Type."""
    rec_sig = b'ASTP'

    melSet = MelSet(
        MelEdid(),
        MelAstpTitles(),
        MelAstpData(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAvif(MelRecord):
    """Actor Value Information."""
    rec_sig = b'AVIF'

    _avif_flags = Flags.from_names(
        (1,  'af_skill'),
        (2,  'af_uses_enum'),
        (3,  'af_dont_allow_script_edits'),
        (4,  'af_is_full_av_cached'),
        (5,  'af_is_permanent_av_cached'),
        (10, 'af_default_to_0'),
        (11, 'af_default_to_1'),
        (12, 'af_default_to_100'),
        (15, 'af_contains_list'),
        (19, 'af_value_less_than_1'),
        (20, 'af_minimum_1'),
        (21, 'af_maximum_10'),
        (22, 'af_maximum_100'),
        (23, 'af_multiply_by_100'),
        (24, 'af_percentage'),
        (26, 'af_damage_is_positive'),
        (27, 'af_god_mode_immune'),
        (28, 'af_harcoded'),
    )

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelLString(b'ANAM', 'abbreviation'),
        MelFloat(b'NAM0', 'avif_default_value'),
        MelUInt32Flags(b'AVFL', 'avif_flags', _avif_flags),
        MelUInt32(b'NAM1', 'avif_type'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreBnds(MelRecord):
    """Bendable Spline."""
    rec_sig = b'BNDS'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelStruct(b'DNAM', ['f', '2H', '5f'],'default_num_tiles',
            'default_num_slices', 'default_num_tiles_relative_to_length',
            'default_red', 'default_green', 'default_blue', 'wind_sensibility',
            'wind_flexibility'),
        MelFid(b'TNAM', 'spline_texture'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreGmst(MreGmstBase):
    """Game Setting."""
    isKeyedByEid = True # NULL fids are acceptable.
    __slots__ = ()

#------------------------------------------------------------------------------
class MreLvli(MreLeveledListBase):
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
        MelLLItems(),
        MelArray('filterKeywordChances',
            MelStruct(b'LLKC', [u'2I'], (FID, u'keyword'), u'chance'),
        ),
        MelFid(b'LVSG', 'epicLootChance'),
        MelLString(b'ONAM', 'overrideName')
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLvln(MreLeveledListBase):
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
        MelLLItems(),
        MelArray('filterKeywordChances',
            MelStruct(b'LLKC', [u'2I'], (FID, u'keyword'), u'chance'),
        ),
        MelString(b'MODL','model'),
        MelBase(b'MODT','modt_p'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MrePerk(MelRecord):
    """Perk."""
    rec_sig = b'PERK'

    _script_flags = Flags.from_names('run_immediately', 'replace_default')

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelFull(),
        MelDescription(),
        MelIcon(),
        MelConditionList(),
        MelPerkData(),
        MelSound(),
        MelNextPerk(),
        MelString(b'FNAM', 'perk_swf'),
        MelSorted(MelGroups('perk_effects',
            MelStruct(b'PRKE', ['3B'], 'pe_type', 'pe_rank', 'pe_priority'),
            MelUnion({
                0: MelStruct(b'DATA', ['I', 'H'], (FID, 'pe_quest'),
                    'pe_quest_stage'),
                1: MelFid(b'DATA', 'pe_ability'),
                2: MelStruct(b'DATA', ['3B'], 'pe_entry_point', 'pe_function',
                    'pe_perk_conditions_tab_count'),
            }, decider=AttrValDecider('pe_type')),
            MelSorted(MelGroups('pe_conditions',
                MelSInt8(b'PRKC', 'pe_run_on'),
                MelConditionList(),
            ), sort_by_attrs='pe_run_on'),
            MelPerkParamsGroups(
                # EPFT has the following meanings:
                #  0: Unknown
                #  1: EPFD=float
                #  2: EPFD=float, float
                #  3: EPFD=fid (LVLI)
                #  4: EPFD=fid (SPEL), EPF2 and EPF3 are used
                #  5: EPFD=fid (SPEL)
                #  6: EPFD=string
                #  7: EPFD=lstring
                #  8: EPFD=fid (AVIF), float
                # There is a special case: if EPFT is 2 and the pe_function
                # (see DATA above) is one of 5, 12, 13 or 14, then
                # EPFD=fid (AVIF), float - same as in the 8 case above.
                MelUInt8(b'EPFT', 'pp_param_type'),
                MelUInt16(b'EPFB', 'pp_perk_entry_id'),
                MelLString(b'EPF2', 'pp_button_label'),
                MelUInt16Flags(b'EPF3', 'pp_script_flags', _script_flags),
                MelUnion({
                    0: MelBase(b'EPFD', 'pp_param1'),
                    1: MelFloat(b'EPFD', 'pp_param1'),
                    2: MelStruct(b'EPFD', ['2f'], 'pp_param1', 'pp_param2'),
                    (3, 4, 5): MelFid(b'EPFD', 'pp_param1'),
                    6: MelString(b'EPFD', 'pp_param1'),
                    7: MelLString(b'EPFD', 'pp_param1'),
                    8: MelStruct(b'EPFD', ['I', 'f'], (FID, 'pp_param1'),
                        'pp_param2'),
                }, decider=PerkEpdfDecider({5, 12, 13, 14})),
            ),
            MelBaseR(b'PRKF', 'pe_end_marker'),
        ), sort_special=perk_effect_key),
    ).with_distributor({
        b'DESC': {
            b'CTDA|CIS1|CIS2': 'conditions',
            b'DATA': 'perk_trait',
        },
        b'PRKE': {
            b'CTDA|CIS1|CIS2|DATA': 'perk_effects',
        },
    })
    __slots__ = melSet.getSlotsUsed()
