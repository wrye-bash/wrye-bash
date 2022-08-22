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
import operator

from ...bolt import Flags
from ...brec import MelBase, MelGroup, AMreHeader, MelSet, MelString, \
    MelStruct, MelNull, MelSimpleArray, AMreLeveledList, MelFid, MelAttx, \
    FID, MelLString, MelUInt8, MelFloat, MelBounds, MelEdid, MelUnloadEvent, \
    MelArray, AMreGmst, MelUInt8Flags, MelSorted, MelGroups, MelShortName, \
    MelUInt32, MelRecord, MelColorO, MelFull, MelBaseR, MelKeywords, MelRace, \
    MelColor, MelSound, MelSoundActivation, MelWaterType, MelAlchEnit, \
    MelActiFlags, MelInteractionKeyword, MelConditions, MelTruncatedStruct, \
    AMelNvnm, ANvnmContext, MelNodeIndex, MelAddnDnam, MelUnion, MelIcons, \
    AttrValDecider, MelSoundPickupDrop, MelEquipmentType, AMelVmad, \
    MelDescription, MelEffects, AMelLLItems, MelValueWeight, AVmadContext, \
    MelIcon, MelConditionList, MelPerkData, MelNextPerk, MelSInt8, MelUInt16, \
    MelUInt16Flags, perk_effect_key, MelPerkParamsGroups, PerkEpdfDecider, \
    MelUInt32Flags, BipedFlags, MelArmaDnam, MelArmaModels, MelArmaSkins, \
    MelAdditionalRaces, MelFootstepSound, MelArtObject, MelEnchantment, \
    MelIcons2, MelBids, MelBamt, MelTemplateArmor, MelObjectTemplate, \
    MelArtType, MelAspcRdat, MelAspcBnam, MelAstpTitles, MelAstpData, \
    MelBookText, MelBookDescription, MelInventoryArt, MelUnorderedGroups, \
    MelImageSpaceMod, MelClmtWeatherTypes, MelClmtTiming, MelClmtTextures, \
    MelCobjOutput, AMreWithItems, AMelItems, MelContData, MelSoundClose, \
    MelCpthShared, FormVersionDecider, MelSoundLooping, MelDoorFlags, \
    MelRandomTeleports, MelDualData, MelIco2

##: What about texture hashes? I carried discarding them forward from Skyrim,
# but that was due to the 43-44 problems. See also #620.
#------------------------------------------------------------------------------
# Record Elements -------------------------------------------------------------
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
                (self._dest_header_flags, 'dest_flags'),
                'dest_unknown'),
            MelResistances(b'DAMC'),
            MelGroups('stages',
                MelStruct(b'DSTD', ['4B', 'i', '2I', 'i'], 'health', 'index',
                          'damage_stage',
                          (self._dest_stage_flags, 'stage_flags'),
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
class MelItems(AMelItems):
    """Handles the COCT/CNTO/COED subrecords defining items."""

#------------------------------------------------------------------------------
class MelLLItems(AMelLLItems):
    """Handles the LLCT/LVLO/COED subrecords defining leveled list entries."""
    def __init__(self):
        super().__init__(MelStruct(b'LVLO', ['H', '2s', 'I', 'H', 'B', 's'],
            'level', 'unused1', (FID, 'listId'), ('count', 1), 'chance_none',
            'unused2'))

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
class MreTes4(AMreHeader):
    """TES4 Record.  File header."""
    rec_sig = b'TES4'
    _post_masters_sigs = {b'ONAM', b'SCRN', b'TNAM', b'INTV', b'INCC'}

    melSet = MelSet(
        MelStruct(b'HEDR', [u'f', u'2I'], (u'version', 1.0), u'numRecords',
            (u'nextObject', 0x001)),
        MelNull(b'OFST'), # obsolete
        MelNull(b'DELE'), # obsolete
        AMreHeader.MelAuthor(),
        AMreHeader.MelDescription(),
        AMreHeader.MelMasterNames(),
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
        MelSoundPickupDrop(),
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
        MelSoundPickupDrop(),
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
        MelSoundPickupDrop(),
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
class MreBook(MelRecord):
    """Book."""
    rec_sig = b'BOOK'

    _book_type_flags = Flags.from_names('advance_actor_value', 'cant_be_taken',
        'add_spell', 'add_perk')

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelBookText(),
        MelSoundPickupDrop(),
        MelKeywords(),
        MelFid(b'FIMD', 'featured_item_message'),
        MelValueWeight(),
        # The book_flags determine what kind of FormID is acceptable for
        # book_teaches, but we don't care about that - only that it is a FormID
        MelStruct(b'DNAM', ['B', '3I'], (_book_type_flags, 'book_flags'),
            (FID,'book_teaches'), 'text_offset_x', 'text_offset_y'),
        MelBookDescription(),
        MelInventoryArt(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreBptd(MelRecord):
    """Body Part Data."""
    rec_sig = b'BPTD'

    _bpnd_flags = Flags.from_names('severable', 'hit_reaction',
        'hit_reaction_default', 'explodable', 'cut_meat_cap_sever',
        'on_cripple', 'explodable_absolute_chance', 'show_cripple_geometry')

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelSorted(MelUnorderedGroups('body_part_list',
            MelLString(b'BPTN', 'part_name'),
            MelString(b'BPNN', 'part_node'),
            MelString(b'BPNT', 'vats_target'),
            MelStruct(b'BPND',
                ['f', '2I', 'f', '2I', '7f', '2I', 'f', '3B', 'I', '8B', '4I',
                 'f', '2B'], 'bpnd_damage_mult',
                (FID, 'bpnd_explodable_debris'),
                (FID, 'bpnd_explodable_explosion'),
                'bpnd_explodable_debris_scale', (FID, 'bpnd_severable_debris'),
                (FID, 'bpnd_severable_explosion'),
                'bpnd_severable_debris_scale', 'bpnd_cut_min', 'bpnd_cut_max',
                'bpnd_cut_radius', 'bpnd_gore_effects_local_rotate_x',
                'bpnd_gore_effects_local_rotate_y', 'bpnd_cut_tesselation',
                (FID, 'bpnd_severable_impact_data_set'),
                (FID, 'bpnd_explodable_impact_data_set'),
                'bpnd_explodable_limb_replacement_scale',
                (_bpnd_flags, 'bpnd_flags'), 'bpnd_part_type',
                'bpnd_health_percent', 'bpnd_actor_value',
                'bpnd_to_hit_chance', 'bpnd_explodable_explosion_chance_pct',
                'bpnd_non_lethal_dismemberment_chance',
                'bpnd_severable_debris_count', 'bpnd_explodable_debris_count',
                'bpnd_severable_decal_count', 'bpnd_explodable_decal_count',
                'bpnd_geometry_segment_index',
                (FID, 'bpnd_on_cripple_art_object'),
                (FID, 'bpnd_on_cripple_debris'),
                (FID, 'bpnd_on_cripple_explosion'),
                (FID, 'bpnd_on_cripple_impact_data_set'),
                'bpnd_on_cripple_debris_scale', 'bpnd_on_cripple_debris_count',
                'bpnd_on_cripple_decal_count'),
            MelString(b'NAM1', 'limb_replacement_model'),
            MelString(b'NAM4', 'gore_effects_target_bone'),
            # Ignore texture hashes - they're only an optimization, plenty of
            # records in Skyrim.esm are missing them
            MelNull(b'NAM5'),
            MelString(b'ENAM', 'hit_reaction_start'),
            MelString(b'FNAM', 'hit_reaction_end'),
            MelFid(b'BNAM', 'gore_effects_dismember_blood_art'),
            MelFid(b'INAM', 'gore_effects_blood_impact_material_type'),
            MelFid(b'JNAM', 'on_cripple_blood_impact_material_type'),
            MelFid(b'CNAM', 'meat_cap_texture_set'),
            MelFid(b'NAM2', 'collar_texture_set'),
            MelString(b'DNAM', 'twist_variable_prefix'),
        ), sort_by_attrs='part_node'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCams(MelRecord):
    """Camera Shot."""
    rec_sig = b'CAMS'

    _cams_flags = Flags.from_names('position_follows_location',
        'rotation_follows_target', 'dont_follow_bone', 'first_person_camera',
        'no_tracer', 'start_at_time_zero', 'dont_reset_location_spring',
        'dont_reset_target_spring')

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelConditionList(),
        MelTruncatedStruct(b'DATA', ['4I', '12f'], 'cams_action',
            'cams_location', 'cams_target', (_cams_flags, 'cams_flags'),
            'time_mult_player', 'time_mult_target', 'time_mult_global',
            'cams_max_time', 'cams_min_time', 'target_pct_between_actors',
            'near_target_distance', 'location_spring', 'target_spring',
            'rotation_offset_x', 'rotation_offset_y', 'rotation_offset_z',
            old_versions={'4I9f', '4I7f'}),
        MelImageSpaceMod(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClas(MelRecord):
    """Class."""
    rec_sig = b'CLAS'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelIcon(),
        MelProperties(),
        MelStruct(b'DATA', ['4s', 'f'], 'unknown1', 'bleedout_default'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClfm(MelRecord):
    """Color."""
    rec_sig = b'CLFM'

    _clfm_flags = Flags.from_names('playable', 'remapping_index',
        'extended_lut')

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt32(b'CNAM', 'color_or_index'),
        MelUInt32Flags(b'FNAM', 'clfm_flags', _clfm_flags),
        MelConditionList(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClmt(MelRecord):
    """Climate."""
    rec_sig = b'CLMT'

    melSet = MelSet(
        MelEdid(),
        MelClmtWeatherTypes(),
        MelClmtTextures(),
        MelModel(),
        MelClmtTiming(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCmpo(MelRecord):
    """Component."""
    rec_sig = b'CMPO'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelSoundCrafting(),
        MelUInt32(b'DATA', 'auto_calc_value'),
        MelFid(b'MNAM', 'scrap_item'),
        MelFid(b'GNAM', 'mod_scrap_scalar'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCobj(MelRecord):
    """Constructible Object."""
    rec_sig = b'COBJ'
    ##: What about isKeyedByEid?

    melSet = MelSet(
        MelEdid(),
        MelSoundPickupDrop(),
        MelSorted(MelArray('cobj_components',
            MelStruct(b'FVPA', ['2I'], (FID, 'component_fid'),
                'component_count'),
        ), sort_by_attrs='component_fid'),
        MelDescription(),
        MelConditionList(),
        MelCobjOutput(),
        MelBase(b'NAM1', 'unused1'),
        MelBase(b'NAM2', 'unused2'),
        MelBase(b'NAM3', 'unused3'),
        MelFid(b'ANAM', 'menu_art_object'),
        MelSorted(MelSimpleArray('category_keywords', MelFid(b'FNAM'))),
        MelTruncatedStruct(b'INTV', ['2H'], 'created_object_count',
            'cobj_priority', old_versions={'H'}),
    )
    __slots__ = melSet.getSlotsUsed()

    def mergeFilter(self, modSet):
        self.cobj_components = [c for c in self.cobj_components
                                if c.component_fid.mod_id in modSet]

#------------------------------------------------------------------------------
class MreCont(AMreWithItems):
    """Container."""
    rec_sig = b'CONT'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelModel(),
        MelItems(),
        MelDestructible(),
        MelContData(),
        MelKeywords(),
        MelFtyp(),
        MelProperties(),
        MelNativeTerminal(),
        MelSound(),
        MelSoundClose(),
        MelFid(b'TNAM', 'sound_take_all'),
        MelFid(b'ONAM', 'cont_filter_list'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCpth(MelRecord):
    """Camera Path."""
    rec_sig = b'CPTH'

    melSet = MelSet(
        MelEdid(),
        MelConditionList(),
        MelCpthShared(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCsty(MelRecord):
    rec_sig = b'CSTY'

    _csty_flags = Flags.from_names('dueling', 'flanking',
        'allow_dual_wielding', 'charging', 'retarget_any_nearby_melee_target')

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'CSGD', ['12f'], 'general_offensive_mult',
            'general_defensive_mult', 'general_group_offensive_mult',
            'general_equipment_score_mult_melee',
            'general_equipment_score_mult_magic',
            'general_equipment_score_mult_ranged',
            'general_equipment_score_mult_shout',
            'general_equipment_score_mult_unarmed',
            'general_equipment_score_mult_staff',
            'general_avoid_threat_chance', 'general_dodge_threat_chance',
            'general_evade_threat_chance'),
        MelBase(b'CSMD', 'unknown1'),
        MelTruncatedStruct(b'CSME', ['10f'], 'melee_attack_staggered_mult',
            'melee_power_attack_staggered_mult',
            'melee_power_attack_blocking_mult',
            'melee_bash_mult', 'melee_bash_recoil_mult',
            'melee_bash_attack_mult', 'melee_bash_power_attack_mult',
            'melee_special_attack_mult', 'melee_block_when_staggered_mult',
            'melee_attack_when_staggered_mult', old_versions={'9f'}),
        MelFloat(b'CSRA', 'ranged_accuracy_mult'),
        MelStruct(b'CSCR', ['9f', 'I', 'f'], 'close_range_dueling_circle_mult',
            'close_range_dueling_fallback_mult',
            'close_range_flanking_flank_distance',
            'close_range_flanking_stalk_time',
            'close_range_charging_charge_distance',
            'close_range_charging_throw_probability',
            'close_range_charging_sprint_fast_probability',
            'close_range_charging_sideswipe_probability',
            'close_range_charging_disengage_probability',
            'close_range_charging_throw_max_targets',
            'close_range_flanking_flank_variance'),
        MelTruncatedStruct(b'CSLR', ['5f'], 'long_range_strafe_mult',
            'long_range_adjust_range_mult', 'long_range_crouch_mult',
            'long_range_wait_mult', 'long_range_range_mult',
            old_versions={'4f', '3f'}),
        MelFloat(b'CSCV', 'cover_search_distance_mult'),
        MelStruct(b'CSFL', ['8f'], 'flight_hover_chance',
            'flight_dive_bomb_chance', 'flight_ground_attack_chance',
            'flight_hover_time', 'flight_ground_attack_time',
            'flight_perch_attack_chance', 'flight_perch_attack_time',
            'flight_flying_attack_chance'),
        MelUInt32Flags(b'DATA', 'csty_flags', _csty_flags),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDfob(MelRecord):
    """Default Object."""
    rec_sig = b'DFOB'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'DATA', 'default_object'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDmgt(MelRecord):
    """Damage Type."""
    rec_sig = b'DMGT'

    melSet = MelSet(
        MelEdid(),
        MelUnion({
            True: MelArray('damage_types',
                MelStruct(b'DNAM', ['2I'], (FID, 'dt_actor_value'),
                    (FID, 'dt_spell')),
            ),
            False: MelSimpleArray('damage_types', MelUInt32(b'DNAM')),
        }, decider=FormVersionDecider(operator.ge, 78)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDobj(MelRecord):
    """Default Object Manager."""
    rec_sig = b'DOBJ'

    melSet = MelSet(
        MelEdid(),
        MelSorted(MelArray('default_objects',
            MelStruct(b'DNAM', ['2I'], 'default_object_use',
                (FID, 'default_object_fid')),
        ), sort_by_attrs='default_object_use'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDoor(MelRecord):
    """Door."""
    rec_sig = b'DOOR'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelNativeTerminal(),
        MelSound(),
        MelSoundClose(b'ANAM'),
        MelSoundLooping(),
        MelDoorFlags(),
        MelLString(b'ONAM', 'alternate_text_open'),
        MelLString(b'CNAM', 'alternate_text_close'),
        MelRandomTeleports(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Not present in Fallout4.esm, but can be created in CK
class MreDual(MelRecord):
    """Dual Cast Data."""
    rec_sig = b'DUAL'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelDualData(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEczn(MelRecord):
    """Encounter Zone."""
    rec_sig = b'ECZN'

    _eczn_flags = Flags.from_names('never_resets',
        'match_pc_below_minimum_level', 'disable_combat_boundary', 'workshop')

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', ['2I', '2b', 'B', 'b'],
            (FID, 'eczn_owner'), (FID, 'eczn_location'), 'eczn_rank',
            'eczn_minimum_level', (_eczn_flags, 'eczn_flags'),
            'eczn_max_level'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
##: Check if this record needs adding to skip_form_version_upgrade
class MreEfsh(MelRecord):
    """Effect Shader."""
    rec_sig = b'EFSH'

    _efsh_flags = Flags.from_names(
        (0,  'no_membrane_shader'),
        (1,  'membrane_grayscale_color'),
        (2,  'membrane_grayscale_alpha'),
        (3,  'no_particle_shader'),
        (4,  'ee_inverse'),
        (5,  'affect_skin_only'),
        (6,  'te_ignore_alpha'),
        (7,  'te_project_uvs'),
        (8,  'ignore_base_geometry_alpha'),
        (9,  'te_lighting'),
        (10, 'te_no_weapons'),
        (11, 'use_alpha_sorting'),
        (12, 'prefer_dismembered_limbs'),
        (15, 'particle_animated'),
        (16, 'particle_grayscale_color'),
        (17, 'particle_grayscale_alpha'),
        (24, 'use_blood_geometry'),
    )

    melSet = MelSet(
        MelEdid(),
        MelIcon('fill_texture'),
        MelIco2('particle_texture'),
        MelString(b'NAM7', 'holes_texture'),
        MelString(b'NAM8', 'membrane_palette_texture'),
        MelString(b'NAM9', 'particle_palette_texture'),
        MelBase(b'DATA', 'unknown_data'),
        MelUnion({
            True: MelStruct(b'DNAM',
                ['3I', '3B', 's', '9f', '3B', 's', '8f', 'I', '4f', 'I', '3B',
                 's', '3B', 's', 's', '6f', 'I', '2f'], 'ms_source_blend_mode',
                'ms_blend_operation', 'ms_z_test_function', 'fill_color1_red',
                'fill_color1_green', 'fill_color1_blue', 'unused1',
                'fill_alpha_fade_in_time', 'fill_full_alpha_time',
                'fill_alpha_fade_out_time', 'fill_persistent_alpha_ratio',
                'fill_alpha_pulse_amplitude', 'fill_alpha_pulse_frequency',
                'fill_texture_animation_speed_u',
                'fill_texture_animation_speed_v', 'ee_fall_off',
                'ee_color_red', 'ee_color_green', 'ee_color_blue', 'unused2',
                'ee_alpha_fade_in_time', 'ee_full_alpha_time',
                'ee_alpha_fade_out_time', 'ee_persistent_alpha_ratio',
                'ee_alpha_pulse_amplitude', 'ee_alpha_pulse_frequency',
                'fill_full_alpha_ratio', 'ee_full_alpha_ratio',
                'ms_dest_blend_mode', 'holes_start_time', 'holes_end_time',
                'holes_start_value', 'holes_end_value', (FID, 'sound_ambient'),
                'fill_color2_red', 'fill_color2_green', 'fill_color2_blue',
                'unused7', 'fill_color3_red', 'fill_color3_green',
                'fill_color3_blue', 'unused8', 'unknown1', 'fill_color1_scale',
                'fill_color2_scale', 'fill_color3_scale', 'fill_color1_time',
                'fill_color2_time', 'fill_color3_time',
                (_efsh_flags, 'efsh_flags'), 'fill_texture_scale_u',
                'fill_texture_scale_v'),
            False: MelStruct(b'DNAM',
                ['s', '3I', '3B', 's', '9f', '3B', 's', '8f', '5I', '19f',
                 '3B', 's', '3B', 's', '3B', 's', '11f', 'I', '5f', '3B', 's',
                 'f', '2I', '6f', 'I', '3B', 's', '3B', 's', '9f', '8I', '2f',
                 '2s'], 'unknown1', 'ms_source_blend_mode',
                'ms_blend_operation', 'ms_z_test_function', 'fill_color1_red',
                'fill_color1_green', 'fill_color1_blue', 'unused1',
                'fill_alpha_fade_in_time', 'fill_full_alpha_time',
                'fill_alpha_fade_out_time', 'fill_persistent_alpha_ratio',
                'fill_alpha_pulse_amplitude', 'fill_alpha_pulse_frequency',
                'fill_texture_animation_speed_u',
                'fill_texture_animation_speed_v', 'ee_fall_off',
                'ee_color_red', 'ee_color_green', 'ee_color_blue', 'unused2',
                'ee_alpha_fade_in_time', 'ee_full_alpha_time',
                'ee_alpha_fade_out_time', 'ee_persistent_alpha_ratio',
                'ee_alpha_pulse_amplitude', 'ee_alpha_pulse_frequency',
                'fill_full_alpha_ratio', 'ee_full_alpha_ratio',
                'ms_dest_blend_mode', 'ps_source_blend_mode',
                'ps_blend_operation', 'ps_z_test_function',
                'ps_dest_blend_mode', 'ps_particle_birth_ramp_up_time',
                'ps_full_particle_birth_time',
                'ps_particle_birth_ramp_down_time',
                'ps_full_particle_birth_ratio', 'ps_persistent_particle_count',
                'ps_particle_lifetime', 'ps_particle_lifetime_delta',
                'ps_initial_speed_along_normal',
                'ps_acceleration_along_normal', 'ps_initial_velocity1',
                'ps_initial_velocity2', 'ps_initial_velocity3',
                'ps_acceleration1', 'ps_acceleration2', 'ps_acceleration3',
                'ps_scale_key1', 'ps_scale_key2', 'ps_scale_key1_time',
                'ps_scale_key2_time', 'color_key1_red', 'color_key1_green',
                'color_key1_blue', 'unused3', 'color_key2_red',
                'color_key2_green', 'color_key2_blue', 'unused4',
                'color_key3_red', 'color_key3_green', 'color_key3_blue',
                'unused5', 'color_key1_alpha', 'color_key2_alpha',
                'color_key3_alpha', 'color_key1_time', 'color_key2_time',
                'color_key3_time', 'ps_initial_speed_along_normal_delta',
                'ps_initial_rotation', 'ps_initial_rotation_delta',
                'ps_rotation_speed', 'ps_rotation_speed_delta',
                (FID, 'addon_models'), 'holes_start_time', 'holes_end_time',
                'holes_start_value', 'holes_end_value', 'ee_width',
                'edge_color_red', 'edge_color_green', 'edge_color_blue',
                'unused6', 'explosion_wind_speed', 'texture_count_u',
                'texture_count_v', 'addon_models_fade_in_time',
                'addon_models_fade_out_time', 'addon_models_scale_start',
                'addon_models_scale_end', 'addon_models_scale_in_time',
                'addon_models_scale_out_time', (FID, 'sound_ambient'),
                'fill_color2_red', 'fill_color2_green', 'fill_color2_blue',
                'unused7', 'fill_color3_red', 'fill_color3_green',
                'fill_color3_blue', 'unused8', 'fill_color1_scale',
                'fill_color2_scale', 'fill_color3_scale', 'fill_color1_time',
                'fill_color2_time', 'fill_color3_time', 'color_scale',
                'birth_position_offset', 'birth_position_offset_range_delta',
                'psa_start_frame', 'psa_start_frame_variation',
                'psa_end_frame', 'psa_loop_start_frame',
                'psa_loop_start_variation', 'psa_frame_count',
                'psa_frame_count_variation', (_efsh_flags, 'efsh_flags'),
                'fill_texture_scale_u', 'fill_texture_scale_v', 'unused9'),
        }, decider=FormVersionDecider(operator.ge, 106)),
        MelModel(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreGmst(AMreGmst):
    """Game Setting."""
    isKeyedByEid = True # NULL fids are acceptable.
    __slots__ = ()

#------------------------------------------------------------------------------
class MreLvli(AMreLeveledList):
    """Leveled Item."""
    rec_sig = b'LVLI'

    top_copy_attrs = ('chanceNone','maxCount','glob','filterKeywordChances',
                      'epicLootChance','overrideName')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8(b'LVLD', 'chanceNone'),
        MelUInt8(b'LVLM', 'maxCount'),
        MelUInt8Flags(b'LVLF', u'flags', AMreLeveledList._flags),
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
class MreLvln(AMreLeveledList):
    """Leveled NPC."""
    rec_sig = b'LVLN'

    top_copy_attrs = ('chanceNone','maxCount','glob','filterKeywordChances',
                      'model','modt_p')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8(b'LVLD', 'chanceNone'),
        MelUInt8(b'LVLM', 'maxCount'),
        MelUInt8Flags(b'LVLF', u'flags', AMreLeveledList._flags),
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
