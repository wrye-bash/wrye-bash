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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module contains the Fallout 4 record classes."""
import operator

from ...bolt import Flags, flag
from ...brec import FID, AMelItems, AMelLLItems, AMelNvnm, AMelVmad, \
    AMreCell, AMreFlst, AMreHeader, AMreImad, AMreLeveledList, AMreWithItems, \
    AMreWithKeywords, ANvnmContext, AttrValDecider, AVmadContext, BipedFlags, \
    FormVersionDecider, MelActiFlags, MelAddnDnam, MelAlchEnit, MelExtra, \
    MelArmaShared, MelArray, MelArtType, MelAspcBnam, MelAspcRdat, MelAttx, \
    MelBamt, MelBase, MelBaseR, MelBids, MelBookDescription, MelBookText, \
    MelBounds, MelClmtTextures, MelClmtTiming, MelClmtWeatherTypes, \
    MelCobjOutput, MelColor, MelColorO, MelConditionList, MelConditions, \
    MelContData, MelCounter, MelCpthShared, MelDalc, MelDecalData, \
    MelDescription, MelDoorFlags, MelEdid, MelEffects, MelEnchantment, \
    MelEquipmentType, MelEqupPnam, MelFactFids, MelFactFlags, MelFactRanks, \
    MelFactVendorInfo, MelFid, MelFloat, MelFlstFids, MelFull, \
    MelFurnMarkerData, MelGrasData, MelGroup, MelGroups, MelHdptShared, \
    MelIco2, MelIcon, MelIcons, MelIcons2, MelIdleAnimationCount, \
    MelIdleAnimations, MelIdleData, MelIdleEnam, MelIdleRelatedAnims, \
    MelIdleTimerSetting, MelImageSpaceMod, MelImgsCinematic, \
    MelImgsTint, MelIngredient, MelIngrEnit, MelInteractionKeyword, \
    MelInventoryArt, MelIpctHazard, MelIpctSounds, MelIpctTextureSets, \
    MelIpdsPnam, MelKeywords, MelLandMpcd, MelLandShared, MelLctnShared, \
    MelLensShared, MelLighFade, MelLighLensFlare, MelLLChanceNone, \
    MelLLFlags, MelLLGlobal, MelLscrCameraPath, MelLscrNif, MelLscrRotation, \
    MelLString, MelLtexGrasses, MelLtexSnam, MelMatoPropertyData, \
    MelMattShared, MelNextPerk, MelNodeIndex, MelNull, MelObject, \
    MelObjectTemplate, MelPartialCounter, MelPerkData, AMreGlob, \
    MelPerkParamsGroups, MelRace, MelRandomTeleports, MelReadOnly, MelRecord, \
    MelRelations, MelSeasons, MelSequential, MelSet, MelShortName, MelVoice, \
    MelSimpleArray, MelSInt8, MelSInt32, MelSorted, MelSound, MelMustShared, \
    MelSoundActivation, MelSoundClose, MelSoundLooping, MelSoundPickupDrop, \
    MelString, MelStruct, MelTemplateArmor, MelTruncatedStruct, MelUInt8, \
    MelUInt16, MelUInt16Flags, MelUInt32, MelUInt32Flags, MelUnion, \
    MelUnloadEvent, MelUnorderedGroups, MelValueWeight, MelWaterType, \
    MelWeight, PartialLoadDecider, MelMovtThresholds, MelMovtName, \
    PerkEpdfDecider, color_attrs, color3_attrs, lens_distributor, \
    perk_distributor, perk_effect_key, AMreWrld, MelMesgButtons, \
    MelMesgShared, MelMdob, MelMgefData, MelMgefEsce, MgefFlags, AMreActor, \
    MelMgefSounds, AMreMgefTes5, MelMgefDnam, SinceFormVersionDecider, \
    MelMuscShared, TemplateFlags, MelFactions, MelDeathItem, MelTemplate, \
    MelSpellCounter, MelSpells, MelSkin, MelNpcAnam, MelAttackRace, \
    MelOverridePackageLists, MelNpcPerks, MelAIPackages, MelNpcClass, \
    MelNpcHeadParts, MelNpcHairColor, MelCombatStyle, MelNpcGiftFilter, \
    MelSoundLevel, MelInheritsSoundsFrom, MelNpcShared, SizeDecider, \
    MelActorSounds2, MelUInt8Flags, MelFilterString, MelOmodData, \
    MelIdleAnimFlags, MelPackPkdt, MelPackSchedule, MelPackOwnerQuest, \
    MelPackPkcu, MelPackDataInputValues, MelPackDataInputs, MelNoteType, \
    MelPackProcedureTree, MelPackIdleHandler, MelProjMuzzleFlashModel, \
    position_attrs, rotation_attrs, AMreRegn, MelRegnEntryMapName, \
    MelWorldspace, MelRegnAreas, MelRegnRdat, MelRegnEntryObjects, \
    MelRegnEntryMusic, MelRegnEntrySounds, MelRegnEntryWeatherTypes, \
    MelRegnEntryGrasses, MelRevbData, MelScolParts, MelSmbnShared, \
    MelSmenShared, MelSmqnShared, MelSnctFlags, MelParent, MelSnctVnamUnam, \
    MelSndrCategory, MelSndrType, MelSndrSounds, MelSndrOutputModel, \
    MelSndrLnam, MelSndrBnam, MelSimpleGroups, MelSopmData, MelSopmType, \
    MelSInt16, MelSopmOutputValues, MelSounSdsc, MelSpit, MelStagTnam

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

    class _ModelFlags(Flags):
        has_facebones_model: bool
        has_1stperson_model: bool

    def __init__(self, mel_sig=b'MODL', attr='model', *, swap_3_4=False,
            always_use_modc=False, no_flags=False):
        """Fallout 4 has a whole lot of model nonsense:

        :param swap_3_4: If True, swaps the third (*C) and fourth (*S)
            elements.
        :param always_use_modc: If True, use MODC for the third (*C) element,
            regardless of what mel_sig is.
        :param no_flags: If True, skip the flags (*F) element."""
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
        if len(types) == 5 and not no_flags:
            mdl_elements.append(MelUInt8Flags(types[4], 'model_flags',
                self._ModelFlags))
        super().__init__(attr, *mdl_elements)

#------------------------------------------------------------------------------
# A distributor config for use with MelObjectTemplate, since MelObjectTemplate
# also contains a FULL subrecord
_object_template_distributor = {
    b'FULL': 'full',
    b'OBTE': {
        b'FULL': 'ot_combinations',
    },
    # For NPC_, which has its main FULL after the object template
    b'STOP': {
        b'FULL': 'full',
    }
}

#------------------------------------------------------------------------------
class _AMreWithProperties(MelRecord):
    """Mixin class for record types that contain a list of properties (see
    MelProperties)."""
    def keep_fids(self, keep_plugins):
        super().keep_fids(keep_plugins)
        self.properties = [c for c in self.properties
                           if c.prop_actor_value.mod_fn in keep_plugins]

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
class MelAttacks(MelSorted):
    """Handles the ATKD/ATKE/ATKW/ATKS/ATKT subrecords shared between NPC_ and
    RACE."""
    class _AttackFlags(Flags):
        ignore_weapon: bool
        bash_attack: bool
        power_attack: bool
        charge_attack: bool
        rotating_attack: bool
        continuous_attack: bool
        override_data: bool = flag(31)

    def __init__(self):
        super().__init__(MelGroups('attacks',
            MelStruct(b'ATKD', ['2f', '2I', '6f', 'i'], 'damage_mult',
                'attack_chance', (FID, 'attack_spell'),
                (self._AttackFlags, 'attack_flags'), 'attack_angle',
                'strike_angle', 'attack_stagger', 'attack_knockdown',
                'recovery_time', 'action_points_mult', 'stagger_offset'),
            MelString(b'ATKE', 'attack_event'),
            MelFid(b'ATKW', 'weapon_slot'),
            MelFid(b'ATKS', 'required_slot'),
            MelString(b'ATKT', 'attack_description'),
        ), sort_by_attrs='attack_event')

#------------------------------------------------------------------------------
class MelBod2(MelUInt32Flags):
    """Handles the BOD2 (Biped Body Template) subrecord."""
    _bp_flags = BipedFlags  # Needs filling in

    def __init__(self):
        super().__init__(b'BOD2', 'biped_flags', self._bp_flags)

#------------------------------------------------------------------------------
class MelDestructible(MelGroup):
    """Represents a collection of destruction-related subrecords."""
    class _dest_header_flags(Flags):
        vats_targetable: bool
        large_actor_destroys: bool

    class _dest_stage_flags(Flags):
        cap_damage: bool
        disable: bool
        destroy: bool
        ignore_external_damage: bool
        becomes_dynamic: bool

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
class MelGodRays(MelFid):
    """Handles the common WGDR (God Rays) subrecord."""
    def __init__(self):
        super().__init__(b'WGDR', 'god_rays')

#------------------------------------------------------------------------------
class MelItems(AMelItems):
    """Handles the COCT/CNTO/COED subrecords defining items."""

#------------------------------------------------------------------------------
class MelLLItems(AMelLLItems):
    """Handles the LLCT/LVLO/COED subrecords defining leveled list entries."""
    def __init__(self, with_coed=True):
        super().__init__(MelStruct(b'LVLO', ['H', '2s', 'I', 'H', 'B', 's'],
            'level', 'unused1', (FID, 'listId'), ('count', 1),
            'item_chance_none', 'unused2'),
            with_coed=with_coed)

#------------------------------------------------------------------------------
class MelLlkc(MelSorted):
    """Handles the common LLKC (Filter Keyword Chances) subrecord."""
    def __init__(self):
        super().__init__(MelArray('filter_keyword_chances',
            MelStruct(b'LLKC', ['2I'], (FID, 'llkc_keyword'), 'llkc_chance'),
        ), sort_by_attrs='llkc_keyword')

#------------------------------------------------------------------------------
class MelLLMaxCount(MelUInt8):
    """Handles the common LVLM (Max Count) subrecord."""
    def __init__(self):
        super().__init__(b'LVLM', 'lvl_max_count')

#------------------------------------------------------------------------------
class MelLocation(MelUnion):
    """A PLDT/PLVD (Location) subrecord. Occurs in PACK and FACT."""
    def __init__(self, sub_sig):
        super().__init__({
            (0, 1, 4, 6): MelTruncatedStruct(
                sub_sig, ['i', 'I', 'i', 'I'], 'package_location_type',
                (FID, 'package_location_value'), 'package_location_radius',
                'package_location_collection_index', old_versions={'iIi'}),
            (2, 3, 7, 12, 13): MelTruncatedStruct(
                sub_sig, ['i', '4s', 'i', 'I'], 'package_location_type',
                'package_location_value', 'package_location_radius',
                'package_location_collection_index', old_versions={'i4si'}),
            (5, 10, 11): MelTruncatedStruct(
                sub_sig, ['i', 'I', 'i', 'I'], 'package_location_type',
                'package_location_value', 'package_location_radius',
                'package_location_collection_index', old_versions={'iIi'}),
            (8, 9, 14): MelTruncatedStruct(
                sub_sig, ['3i', 'I'], 'package_location_type',
                'package_location_value', 'package_location_radius',
                'package_location_collection_index', old_versions={'3i'}),
            }, decider=PartialLoadDecider(
                loader=MelSInt32(sub_sig, 'package_location_type'),
                decider=AttrValDecider('package_location_type')),
            fallback=MelNull(b'NULL') # ignore
        )

#------------------------------------------------------------------------------
class MelNativeTerminal(MelFid):
    """Handles the common NTRM (Native Terminal) subrecord."""
    def __init__(self):
        super().__init__(b'NTRM', 'native_terminal')

#------------------------------------------------------------------------------
class MelNotesTypeRule(MelSequential):
    """Handles the AACT/KYWD subrecords DNAM (Notes), TNAM (Type) and DATA
    (Attraction Rule)."""
    def __init__(self):
        super().__init__(
            MelString(b'DNAM', 'aact_kywd_notes'),
            MelUInt32(b'TNAM', 'aact_kywd_type'),
            MelFid(b'DATA', 'attraction_rule'),
        )

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
        ), sort_by_attrs='prop_actor_value')

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
class MelSped(MelUnion):
    """Handles the common SPED (Movement Data) subrecord."""
    def __init__(self):
        super().__init__({
            0: MelStruct(b'SPED', ['10f'], 'speed_left_walk', 'speed_left_run',
                'speed_right_walk', 'speed_right_run', 'speed_forward_walk',
                'speed_forward_run', 'speed_back_walk', 'speed_back_run',
                'pitch_walk', 'pitch_run'),
            1: MelStruct(b'SPED', ['11f'], 'speed_left_walk', 'speed_left_run',
                'speed_right_walk', 'speed_right_run', 'speed_forward_walk',
                'speed_forward_run', 'speed_back_walk', 'speed_back_run',
                'pitch_walk', 'pitch_run', 'unknown1'),
            2: MelStruct(b'SPED', ['17f'], 'speed_left_walk', 'speed_left_run',
                'speed_right_walk', 'speed_right_run', 'speed_forward_walk',
                'speed_forward_run', 'speed_back_walk', 'speed_back_run',
                'pitch_walk', 'pitch_run', 'roll_walk', 'roll_run', 'yaw_walk',
                'yaw_run', 'unknown1', 'unknown2', 'unknown3'),
            3: MelStruct(b'SPED', ['28f'], 'speed_left_stand',
                'speed_left_walk', 'speed_left_run', 'speed_left_sprint',
                'speed_right_stand', 'speed_right_walk', 'speed_right_run',
                'speed_right_sprint', 'speed_forward_stand',
                'speed_forward_walk', 'speed_forward_run',
                'speed_forward_sprint', 'speed_back_stand',
                'speed_back_walk', 'speed_back_run', 'speed_back_sprint',
                'pitch_stand', 'pitch_walk', 'pitch_run', 'pitch_sprint',
                'roll_stand', 'roll_walk', 'roll_run', 'roll_sprint',
                'yaw_stand', 'yaw_walk', 'yaw_run', 'yaw_sprint'),
        }, decider=FormVersionDecider(self._decide_record_level))

    @staticmethod
    def _decide_record_level(rec_form_ver: int):
        """Places the record into one of four categories based on its form
        version v: 0 iff 0 <= v < 28, 1 iff 28 <= v < 60, 2 iff 60 <= v < 104
        and 3 iff 104 <= v."""
        if rec_form_ver < 28: return 0
        elif rec_form_ver < 60: return 1
        elif rec_form_ver < 104: return 2
        else: return 3

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        super().load_mel(record, ins, sub_type, size_, *debug_strs)
        if record.header.form_version < 60:
            # Before form version 60, pitch/roll/yaw used two shared floats
            pry_walk = record.pitch_walk
            pry_run = record.pitch_run
            record.roll_walk = pry_walk
            record.roll_run = pry_run
            record.yaw_walk = pry_walk
            record.yaw_run = pry_run

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
    next_object_default = 0x001

    class HeaderFlags(AMreHeader.HeaderFlags):
        optimized_file: bool = flag(4)
        localized: bool = flag(7)
        esl_flag: bool = flag(9)

    melSet = MelSet(
        MelStruct(b'HEDR', ['f', '2I'], ('version', 1.0), 'numRecords',
                  ('nextObject', next_object_default), is_required=True),
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
        MelUInt32(b'INCC', 'interior_cell_count'),
    )

#------------------------------------------------------------------------------
class MreAact(MelRecord):
    """Action."""
    rec_sig = b'AACT'

    class HeaderFlags(MelRecord.HeaderFlags):
        restricted: bool = flag(15)

    melSet = MelSet(
        MelEdid(),
        MelColorO(),
        MelNotesTypeRule(),
        MelFull(),
    )

#------------------------------------------------------------------------------
class MreActi(AMreWithKeywords, _AMreWithProperties):
    """Activator."""
    rec_sig = b'ACTI'

    class HeaderFlags(MelRecord.HeaderFlags):
        never_fades: bool = flag(2)
        non_occluder: bool = flag(4)
        heading_marker: bool = flag(7)
        must_update_anims: bool = flag(8)
        hidden_from_local_map: bool = flag(9)
        headtrack_marker: bool = flag(10)
        used_as_platform: bool = flag(11)
        pack_in_use_only: bool = flag(13)
        has_distant_lod: bool = flag(15)
        random_anim_start: bool = flag(16)
        dangerous: bool = flag(17)
        ignore_object_interaction: bool = flag(20)
        is_marker: bool = flag(23)
        obstacle: bool = flag(25)
        navmesh_filter: bool = flag(26)
        navmesh_bounding_box: bool = flag(27)
        child_can_use: bool = flag(29)
        navmesh_ground: bool = flag(30)

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

#------------------------------------------------------------------------------
class MreAlch(AMreWithKeywords):
    """Ingestible."""
    rec_sig = b'ALCH'

    class HeaderFlags(MelRecord.HeaderFlags):
        medicine: bool = flag(29)

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
        MelWeight(),
        MelAlchEnit(),
        MelLString(b'DNAM', 'addiction_name'),
        MelEffects(),
    )

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

#------------------------------------------------------------------------------
class MreAmmo(AMreWithKeywords):
    """Ammunition."""
    rec_sig = b'AMMO'

    class HeaderFlags(MelRecord.HeaderFlags):
        not_playable: bool = flag(2)

    class _ammo_flags(Flags):
        notNormalWeapon: bool
        nonPlayable: bool
        has_count_based_3d: bool

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
        MelString(b'NAM1', 'casing_model'),
        # Ignore texture hashes - they're only an optimization, plenty of
        # records in Skyrim.esm are missing them
        MelNull(b'NAM2'),
    )

#------------------------------------------------------------------------------
class MreAnio(MelRecord):
    """Animated Object."""
    rec_sig = b'ANIO'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelUnloadEvent(),
    )

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

#------------------------------------------------------------------------------
class MreArma(MelRecord):
    """Armor Addon."""
    rec_sig = b'ARMA'

    class HeaderFlags(MelRecord.HeaderFlags):
        no_underarmor_scaling: bool = flag(6)
        has_sculpt_data: bool = flag(9)
        hi_res_1st_person_only: bool = flag(30)

    melSet = MelSet(
        MelEdid(),
        MelBod2(),
        MelRace(),
        MelArmaShared(MelModel),
        MelGroups('bone_scale_modifier_set',
            MelUInt32(b'BSMP', 'target_gender'),
            MelSorted(MelGroups('bone_scale_modifiers',
                MelString(b'BSMB', 'bone_name'),
                MelStruct(b'BSMS', ['3f'], 'bone_scale_delta_x',
                    'bone_scale_delta_y', 'bone_scale_delta_z'),
            ), sort_by_attrs='bone_name'),
        )
    )

#------------------------------------------------------------------------------
class MreArmo(AMreWithKeywords):
    """Armor."""
    rec_sig = b'ARMO'

    class HeaderFlags(MelRecord.HeaderFlags):
        not_playable: bool = flag(2)
        shield: bool = flag(6)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelEnchantment(),
        MelModel(b'MOD2', 'maleWorld', always_use_modc=True, no_flags=True),
        MelIcons('maleIconPath', 'maleSmallIconPath'),
        MelModel(b'MOD4', 'femaleWorld', always_use_modc=True, no_flags=True),
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
    ).with_distributor(_object_template_distributor)

#------------------------------------------------------------------------------
class MreArto(AMreWithKeywords):
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

#------------------------------------------------------------------------------
class MreAvif(MelRecord):
    """Actor Value Information."""
    rec_sig = b'AVIF'

    class _avif_flags(Flags):
        af_skill: bool = flag(1)
        af_uses_enum: bool = flag(2)
        af_dont_allow_script_edits: bool = flag(3)
        af_is_full_av_cached: bool = flag(4)
        af_is_permanent_av_cached: bool = flag(5)
        af_default_to_0: bool = flag(10)
        af_default_to_1: bool = flag(11)
        af_default_to_100: bool = flag(12)
        af_contains_list: bool = flag(15)
        af_value_less_than_1: bool = flag(19)
        af_minimum_1: bool = flag(20)
        af_maximum_10: bool = flag(21)
        af_maximum_100: bool = flag(22)
        af_multiply_by_100: bool = flag(23)
        af_percentage: bool = flag(24)
        af_damage_is_positive: bool = flag(26)
        af_god_mode_immune: bool = flag(27)
        af_harcoded: bool = flag(28)

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelLString(b'ANAM', 'abbreviation'),
        MelFloat(b'NAM0', 'avif_default_value'),
        MelUInt32Flags(b'AVFL', 'avif_flags', _avif_flags),
        MelUInt32(b'NAM1', 'avif_type'),
    )

#------------------------------------------------------------------------------
class MreBnds(MelRecord):
    """Bendable Spline."""
    rec_sig = b'BNDS'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelStruct(b'DNAM', ['f', '2H', '5f'],'default_num_tiles',
            'default_num_slices', 'default_num_tiles_relative_to_length',
            *color3_attrs('default_color'), 'wind_sensibility',
            'wind_flexibility'),
        MelFid(b'TNAM', 'spline_texture'),
    )

#------------------------------------------------------------------------------
class MreBook(AMreWithKeywords):
    """Book."""
    rec_sig = b'BOOK'

    class _book_type_flags(Flags):
        advance_actor_value: bool
        cant_be_taken: bool
        add_spell: bool
        add_perk: bool

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

#------------------------------------------------------------------------------
class MreBptd(MelRecord):
    """Body Part Data."""
    rec_sig = b'BPTD'

    class _bpnd_flags(Flags):
        severable: bool
        hit_reaction: bool
        hit_reaction_default: bool
        explodable: bool
        cut_meat_cap_sever: bool
        on_cripple: bool
        explodable_absolute_chance: bool
        show_cripple_geometry: bool

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        ##: This sort_by_attrs might need a sort_special to handle part_node
        # being None, keep an eye out for TypeError tracebacks
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
                (FID, 'bpnd_severable_impact_dataset'),
                (FID, 'bpnd_explodable_impact_dataset'),
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
                (FID, 'bpnd_on_cripple_impact_dataset'),
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

#------------------------------------------------------------------------------
class MreCams(MelRecord):
    """Camera Shot."""
    rec_sig = b'CAMS'

    class _cams_flags(Flags):
        position_follows_location: bool
        rotation_follows_target: bool
        dont_follow_bone: bool
        first_person_camera: bool
        no_tracer: bool
        start_at_time_zero: bool
        dont_reset_location_spring: bool
        dont_reset_target_spring: bool

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelConditionList(),
        MelTruncatedStruct(b'DATA', ['4I', '12f'], 'cams_action',
            'cams_location', 'cams_target', (_cams_flags, 'cams_flags'),
            'time_mult_player', 'time_mult_target', 'time_mult_global',
            'cams_max_time', 'cams_min_time', 'target_pct_between_actors',
            'near_target_distance', 'location_spring', 'target_spring',
            *rotation_attrs('cams_offset'), old_versions={'4I9f', '4I7f'}),
        MelImageSpaceMod(),
    )

#------------------------------------------------------------------------------
class MreCell(AMreCell): ##: Implement once regular records are done
    """Cell."""
    ref_types = {b'ACHR', b'PARW', b'PBAR', b'PBEA', b'PCON', b'PFLA', b'PGRE',
                 b'PHZD', b'PMIS', b'REFR'}
    interior_temp_extra = [b'NAVM']

    class HeaderFlags(AMreCell.HeaderFlags):
        no_previs: bool = flag(7)
        partial_form: bool = flag(14)

#------------------------------------------------------------------------------
class MreClas(_AMreWithProperties):
    """Class."""
    rec_sig = b'CLAS'

    class HeaderFlags(MelRecord.HeaderFlags):
        not_playable: bool = flag(2)

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelIcon(),
        MelProperties(),
        MelStruct(b'DATA', ['4s', 'f'], 'unknown1', 'bleedout_default'),
    )

#------------------------------------------------------------------------------
class MreClfm(MelRecord):
    """Color."""
    rec_sig = b'CLFM'

    class HeaderFlags(MelRecord.HeaderFlags):
        not_playable: bool = flag(2)

    class _clfm_flags(Flags):
        playable: bool
        remapping_index: bool
        extended_lut: bool

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt32(b'CNAM', 'color_or_index'),
        MelUInt32Flags(b'FNAM', 'clfm_flags', _clfm_flags),
        MelConditionList(),
    )

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

    def keep_fids(self, keep_plugins):
        super().keep_fids(keep_plugins)
        self.cobj_components = [c for c in self.cobj_components
                                if c.component_fid.mod_fn in keep_plugins]

#------------------------------------------------------------------------------
class MreCont(AMreWithItems, AMreWithKeywords, _AMreWithProperties):
    """Container."""
    rec_sig = b'CONT'

    class HeaderFlags(AMreWithItems.HeaderFlags):
        has_distant_lod: bool = flag(15)
        random_anim_start: bool = flag(16)
        obstacle: bool = flag(25)
        navmesh_filter: bool = flag(26)
        navmesh_bounding_box: bool = flag(27)
        navmesh_ground: bool = flag(30)

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

#------------------------------------------------------------------------------
class MreCpth(MelRecord):
    """Camera Path."""
    rec_sig = b'CPTH'

    melSet = MelSet(
        MelEdid(),
        MelConditionList(),
        MelCpthShared(),
    )

#------------------------------------------------------------------------------
class MreCsty(MelRecord):
    """Combat Style."""
    rec_sig = b'CSTY'

    class HeaderFlags(MelRecord.HeaderFlags):
        allow_dual_wielding: bool = flag(19)

    class _csty_flags(Flags):
        dueling: bool
        flanking: bool
        allow_dual_wielding: bool
        charging: bool
        retarget_any_nearby_melee_target: bool

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

#------------------------------------------------------------------------------
class MreDfob(MelRecord):
    """Default Object."""
    rec_sig = b'DFOB'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'DATA', 'default_object'),
    )

#------------------------------------------------------------------------------
class MreDial(MelRecord): ##: Implement once regular records are done
    """Dialogue."""
    rec_sig = b'DIAL'

    class HeaderFlags(MelRecord.HeaderFlags):
        partial_form: bool = flag(14)

    @classmethod
    def nested_records_sigs(cls):
        return {b'INFO'}

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
        }, decider=SinceFormVersionDecider(operator.ge, 78)),
    )

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

#------------------------------------------------------------------------------
class MreDoor(AMreWithKeywords):
    """Door."""
    rec_sig = b'DOOR'

    class HeaderFlags(MelRecord.HeaderFlags):
        non_occluder: bool = flag(4)
        has_distant_lod: bool = flag(15)
        random_anim_start: bool = flag(16)
        is_marker: bool = flag(23)

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

#------------------------------------------------------------------------------
class MreEczn(MelRecord):
    """Encounter Zone."""
    rec_sig = b'ECZN'

    class _eczn_flags(Flags):
        never_resets: bool
        match_pc_below_minimum_level: bool
        disable_combat_boundary: bool
        workshop: bool

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', ['2I', '2b', 'B', 'b'],
            (FID, 'eczn_owner'), (FID, 'eczn_location'), 'eczn_rank',
            'eczn_minimum_level', (_eczn_flags, 'eczn_flags'),
            'eczn_max_level'),
    )

#------------------------------------------------------------------------------
##: Check if this record needs adding to skip_form_version_upgrade
class MreEfsh(MelRecord):
    """Effect Shader."""
    rec_sig = b'EFSH'

    class _efsh_flags(Flags):
        no_membrane_shader: bool = flag(0)
        membrane_grayscale_color: bool = flag(1)
        membrane_grayscale_alpha: bool = flag(2)
        no_particle_shader: bool = flag(3)
        ee_inverse: bool = flag(4)
        affect_skin_only: bool = flag(5)
        te_ignore_alpha: bool = flag(6)
        te_project_uvs: bool = flag(7)
        ignore_base_geometry_alpha: bool = flag(8)
        te_lighting: bool = flag(9)
        te_no_weapons: bool = flag(10)
        use_alpha_sorting: bool = flag(11)
        prefer_dismembered_limbs: bool = flag(12)
        particle_animated: bool = flag(15)
        particle_grayscale_color: bool = flag(16)
        particle_grayscale_alpha: bool = flag(17)
        use_blood_geometry: bool = flag(24)

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
                'ms_blend_operation', 'ms_z_test_function',
                *color_attrs('fill_color1'), 'fill_alpha_fade_in_time',
                'fill_full_alpha_time', 'fill_alpha_fade_out_time',
                'fill_persistent_alpha_ratio', 'fill_alpha_pulse_amplitude',
                'fill_alpha_pulse_frequency', 'fill_texture_animation_speed_u',
                'fill_texture_animation_speed_v', 'ee_fall_off',
                *color_attrs('ee_color'), 'ee_alpha_fade_in_time',
                'ee_full_alpha_time', 'ee_alpha_fade_out_time',
                'ee_persistent_alpha_ratio', 'ee_alpha_pulse_amplitude',
                'ee_alpha_pulse_frequency', 'fill_full_alpha_ratio',
                'ee_full_alpha_ratio', 'ms_dest_blend_mode',
                'holes_start_time', 'holes_end_time', 'holes_start_value',
                'holes_end_value', (FID, 'sound_ambient'),
                *color_attrs('fill_color2'), *color_attrs('fill_color3'),
                'unknown1', 'fill_color1_scale', 'fill_color2_scale',
                'fill_color3_scale', 'fill_color1_time', 'fill_color2_time',
                'fill_color3_time', (_efsh_flags, 'efsh_flags'),
                'fill_texture_scale_u', 'fill_texture_scale_v'),
            False: MelStruct(b'DNAM',
                ['s', '3I', '3B', 's', '9f', '3B', 's', '8f', '5I', '19f',
                 '3B', 's', '3B', 's', '3B', 's', '11f', 'I', '5f', '3B', 's',
                 'f', '2I', '6f', 'I', '3B', 's', '3B', 's', '9f', '8I', '2f',
                 '2s'], 'unknown1', 'ms_source_blend_mode',
                'ms_blend_operation', 'ms_z_test_function',
                *color_attrs('fill_color1'), 'fill_alpha_fade_in_time',
                'fill_full_alpha_time', 'fill_alpha_fade_out_time',
                'fill_persistent_alpha_ratio', 'fill_alpha_pulse_amplitude',
                'fill_alpha_pulse_frequency', 'fill_texture_animation_speed_u',
                'fill_texture_animation_speed_v', 'ee_fall_off',
                *color_attrs('ee_color'), 'ee_alpha_fade_in_time',
                'ee_full_alpha_time', 'ee_alpha_fade_out_time',
                'ee_persistent_alpha_ratio', 'ee_alpha_pulse_amplitude',
                'ee_alpha_pulse_frequency', 'fill_full_alpha_ratio',
                'ee_full_alpha_ratio', 'ms_dest_blend_mode',
                'ps_source_blend_mode', 'ps_blend_operation',
                'ps_z_test_function', 'ps_dest_blend_mode',
                'ps_particle_birth_ramp_up_time',
                'ps_full_particle_birth_time',
                'ps_particle_birth_ramp_down_time',
                'ps_full_particle_birth_ratio', 'ps_persistent_particle_count',
                'ps_particle_lifetime', 'ps_particle_lifetime_delta',
                'ps_initial_speed_along_normal',
                'ps_acceleration_along_normal', 'ps_initial_velocity1',
                'ps_initial_velocity2', 'ps_initial_velocity3',
                'ps_acceleration1', 'ps_acceleration2', 'ps_acceleration3',
                'ps_scale_key1', 'ps_scale_key2', 'ps_scale_key1_time',
                'ps_scale_key2_time',
                *color_attrs('color_key1', rename_alpha=True),
                *color_attrs('color_key2', rename_alpha=True),
                *color_attrs('color_key3', rename_alpha=True),
                'color_key1_alpha', 'color_key2_alpha', 'color_key3_alpha',
                'color_key1_time', 'color_key2_time', 'color_key3_time',
                'ps_initial_speed_along_normal_delta', 'ps_initial_rotation',
                'ps_initial_rotation_delta', 'ps_rotation_speed',
                'ps_rotation_speed_delta', (FID, 'addon_models'),
                'holes_start_time', 'holes_end_time', 'holes_start_value',
                'holes_end_value', 'ee_width', *color_attrs('edge_color'),
                'explosion_wind_speed', 'texture_count_u', 'texture_count_v',
                'addon_models_fade_in_time', 'addon_models_fade_out_time',
                'addon_models_scale_start', 'addon_models_scale_end',
                'addon_models_scale_in_time', 'addon_models_scale_out_time',
                (FID, 'sound_ambient'), *color_attrs('fill_color2'),
                *color_attrs('fill_color3'), 'fill_color1_scale',
                'fill_color2_scale', 'fill_color3_scale', 'fill_color1_time',
                'fill_color2_time', 'fill_color3_time', 'color_scale',
                'birth_position_offset', 'birth_position_offset_range_delta',
                'psa_start_frame', 'psa_start_frame_variation',
                'psa_end_frame', 'psa_loop_start_frame',
                'psa_loop_start_variation', 'psa_frame_count',
                'psa_frame_count_variation', (_efsh_flags, 'efsh_flags'),
                'fill_texture_scale_u', 'fill_texture_scale_v', 'unused9'),
        }, decider=SinceFormVersionDecider(operator.ge, 106)),
        MelModel(),
    )

#------------------------------------------------------------------------------
class MreEnch(MelRecord):
    """Object Effect."""
    rec_sig = b'ENCH'

    class _enit_flags(Flags):
        ench_no_auto_calc: bool = flag(0)
        extend_duration_on_recast: bool = flag(2)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelStruct(b'ENIT', ['i', '2I', 'i', '2I', 'f', '2I'],
            'enchantment_cost', (_enit_flags, 'enit_flags'),
            'enchantment_cast_type', 'enchantment_amount',
            'enchantment_target_type', 'enchantment_type',
            'enchantment_charge_time', (FID, 'base_enchantment'),
            (FID, 'worn_restrictions')),
        MelEffects(),
    )

#------------------------------------------------------------------------------
class MreEqup(MelRecord):
    """Equip Type."""
    rec_sig = b'EQUP'

    class _equp_flags(Flags):
        use_all_parents: bool
        parents_optional: bool
        item_slot: bool

    melSet = MelSet(
        MelEdid(),
        MelEqupPnam(),
        MelUInt32Flags(b'DATA', 'equp_flags', _equp_flags),
        MelFid(b'ANAM', 'condition_actor_value'),
    )

#------------------------------------------------------------------------------
class MreExpl(MelRecord):
    """Explosion."""
    rec_sig = b'EXPL'

    class _expl_flags(Flags):
        always_uses_world_orientation: bool = flag(1)
        knock_down_always: bool = flag(2)
        knock_down_by_formula: bool = flag(3)
        ignore_los_check: bool = flag(4)
        push_explosion_source_ref_only: bool = flag(5)
        ignore_image_space_swap: bool = flag(6)
        explosion_chain: bool = flag(7)
        no_controller_vibration: bool = flag(8)
        placed_object_persists: bool = flag(9)
        skip_underwater_tests: bool = flag(10)

    class MelExplData(MelTruncatedStruct):
        """Handles the EXPL subrecord DATA, which requires special code."""
        def _pre_process_unpacked(self, unpacked_val):
            if len(unpacked_val) in (13, 14, 15):
                # Form Version 97 added the inner_radius float right before the
                # outer_radius float
                unpacked_val = (*unpacked_val[:8], float(self.defaults[8]),
                                *unpacked_val[8:])
            return super()._pre_process_unpacked(unpacked_val)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelEnchantment(),
        MelImageSpaceMod(),
        MelExplData(b'DATA', ['6I', '6f', '2I', 'f', 'I', '4f', 'I'],
            (FID, 'expl_light'), (FID, 'expl_sound1'), (FID, 'expl_sound2'),
            (FID, 'expl_impact_dataset'), (FID, 'placed_object'),
            (FID, 'spawn_object'), 'expl_force', 'expl_damage', 'inner_radius',
            'outer_radius', 'is_radius', 'vertical_offset_mult',
            (_expl_flags, 'expl_flags'), 'expl_sound_level',
            'placed_object_autofade_delay', 'expl_stagger', 'expl_spawn_x',
            'expl_spawn_y', 'expl_spawn_z', 'expl_spawn_spread_degrees',
            'expl_spawn_count', old_versions={'6I6f2IfI', '6I5f2IfI',
                                              '6I5f2If', '6I5f2I'}),
    )

#------------------------------------------------------------------------------
class MreFact(MelRecord):
    """Faction."""
    rec_sig = b'FACT'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelRelations(),
        MelFactFlags(),
        MelFactFids(),
        # 'cv_arrest' and 'cv_attack_on_sight' are actually bools, cv means
        # 'crime value' (which is what this struct is about)
        MelStruct(b'CRVA', ['2B', '5H', 'f', '2H'], 'cv_arrest',
            'cv_attack_on_sight', 'cv_murder', 'cv_assault', 'cv_trespass',
            'cv_pickpocket', 'cv_unknown', 'cv_steal_multiplier', 'cv_escape',
            'cv_werewolf'),
        MelFactRanks(),
        MelFactVendorInfo(),
        MelLocation(b'PLVD'),
        MelConditions(),
    )

#------------------------------------------------------------------------------
class MreFlor(AMreWithKeywords, _AMreWithProperties):
    """Flora."""
    rec_sig = b'FLOR'
    _has_duplicate_attrs = True # RNAM is an older version of ATTX

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelProperties(),
        MelColor(b'PNAM'),
        MelAttx(),
        # Older format - read, but only dump ATTX
        MelReadOnly(MelAttx(b'RNAM')),
        MelActiFlags(),
        MelIngredient(),
        MelSound(),
        MelSeasons(),
    )

#------------------------------------------------------------------------------
class MreFlst(AMreFlst):
    """FormID List."""
    rec_sig = b'FLST'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelFlstFids(),
    )

#------------------------------------------------------------------------------
##: It should be possible to absorb this in MelArray, see MelWthrColorsFnv for
# a plan of attack. But note that if we have form version info, we should be
# able to pass that in too, since the other algorithm is ambiguous once a
# subrecord of size lcm(new, old) is reached - MelFVDArray (form version
# dependent)?
class MelFurnMarkerParams(MelArray):
    """Handles the FURN subrecord SNAM (Furniture Marker Parameters), which
    requires special code."""
    class _param_entry_types(Flags):
        entry_type_front: bool
        entry_type_rear: bool
        entry_type_right: bool
        entry_type_left: bool
        entry_type_other: bool
        entry_type_unused1: bool
        entry_type_unused2: bool
        entry_type_unused3: bool

    def __init__(self):
        struct_args = (b'SNAM', ['4f', 'I', 'B', '3s'], 'param_offset_x',
                       'param_offset_y', 'param_offset_z', 'param_rotation_z',
                       (FID, 'param_keyword'),
                       (self._param_entry_types, 'param_entry_types'),
                       'param_unknown')
        # Trick MelArray into thinking we have a static-sized element
        super().__init__('furn_marker_parameters', MelStruct(*struct_args))
        self._real_loader = MelTruncatedStruct(*struct_args,
            old_versions={'4fI'})

    def _load_array(self, record, ins, sub_type, size_, *debug_strs):
        append_entry = getattr(record, self.attr).append
        entry_slots = self.array_element_attrs
        # Form version 125 added the entry types to the end
        entry_size = 24 if record.header.form_version >= 125 else 20
        load_entry = self._real_loader.load_mel
        for x in range(size_ // entry_size):
            arr_entry = MelObject()
            append_entry(arr_entry)
            arr_entry.__slots__ = entry_slots
            load_entry(arr_entry, ins, sub_type, entry_size, *debug_strs)

class MreFurn(AMreWithItems, AMreWithKeywords, _AMreWithProperties):
    """Furniture."""
    rec_sig = b'FURN'

    class HeaderFlags(AMreWithItems.HeaderFlags):
        has_container: bool = flag(2)
        is_perch: bool = flag(7)
        has_distant_lod: bool = flag(15)
        random_anim_start: bool = flag(16)
        is_marker: bool = flag(23)
        power_armor: bool = flag(25)
        must_exit_to_talk: bool = flag(28)
        child_can_use: bool = flag(29)

    class _active_markers_flags(Flags):
        interaction_point_0: bool = flag(0)
        interaction_point_1: bool = flag(1)
        interaction_point_2: bool = flag(2)
        interaction_point_3: bool = flag(3)
        interaction_point_4: bool = flag(4)
        interaction_point_5: bool = flag(5)
        interaction_point_6: bool = flag(6)
        interaction_point_7: bool = flag(7)
        interaction_point_8: bool = flag(8)
        interaction_point_9: bool = flag(9)
        interaction_point_10: bool = flag(10)
        interaction_point_11: bool = flag(11)
        interaction_point_12: bool = flag(12)
        interaction_point_13: bool = flag(13)
        interaction_point_14: bool = flag(14)
        interaction_point_15: bool = flag(15)
        interaction_point_16: bool = flag(16)
        interaction_point_17: bool = flag(17)
        interaction_point_18: bool = flag(18)
        interaction_point_19: bool = flag(19)
        interaction_point_20: bool = flag(20)
        interaction_point_21: bool = flag(21)
        allow_awake_sound: bool = flag(22)
        enter_with_weapon_drawn: bool = flag(23)
        play_anim_when_full: bool = flag(24)
        disables_activation: bool = flag(25)
        is_perch: bool = flag(26)
        must_exit_to_talk: bool = flag(27)
        use_static_to_avoid_node: bool = flag(28)
        has_model: bool = flag(30)
        is_sleep_furniture: bool = flag(31)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelProperties(),
        MelNativeTerminal(),
        MelFtyp(),
        MelColor(b'PNAM'),
        MelFid(b'WNAM', 'drinking_water_type'),
        MelAttx(),
        MelActiFlags(),
        MelConditions(),
        MelItems(),
        MelUInt32Flags(b'MNAM', 'active_markers_flags', _active_markers_flags),
        MelTruncatedStruct(b'WBDT', ['B', 'b'], 'bench_type', 'uses_skill',
            old_versions={'B'}),
        MelFid(b'NAM1', 'associated_form'),
        MelFurnMarkerData(),
        MelFurnMarkerParams(),
        MelAppr(),
        MelObjectTemplate(),
        MelNvnm(),
    ).with_distributor(_object_template_distributor)

#------------------------------------------------------------------------------
class MreGdry(MelRecord):
    """God Rays."""
    rec_sig = b'GDRY'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', ['15f'], *color3_attrs('back_color'),
            *color3_attrs('forward_color'), 'godray_intensity',
            'air_color_scale', 'back_color_scale', 'forward_color_scale',
            'back_phase', *color3_attrs('air_color'), 'forward_phase'),
    )

#------------------------------------------------------------------------------
class MreGlob(AMreGlob):
    """Global."""
    class HeaderFlags(AMreGlob.HeaderFlags):
        constant: bool = flag(6)

#------------------------------------------------------------------------------
class MreGras(MelRecord):
    """Grass."""
    rec_sig = b'GRAS'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelGrasData(),
    )

#------------------------------------------------------------------------------
class MreHazd(MelRecord):
    """Hazard."""
    rec_sig = b'HAZD'

    class _hazd_flags(Flags):
        affects_player_only: bool
        inherit_duration_from_spawn_spell: bool
        align_to_impact_normal: bool
        inherit_radius_from_spawn_spell: bool
        drop_to_ground: bool
        taper_effectiveness_by_proximity: bool

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelImageSpaceMod(),
        MelStruct(b'DNAM', ['I', '4f', '5I', '3f'], 'hazd_limit',
            'hazd_radius', 'hazd_lifetime', 'image_space_radius',
            'target_interval', (_hazd_flags, 'hazd_flags'),
            (FID, 'hazd_effect'), (FID, 'hazd_light'),
            (FID, 'hazd_impact_dataset'), (FID, 'hazd_sound'),
            'taper_full_effect_radius', 'taper_weight', 'taper_curse'),
    )

#------------------------------------------------------------------------------
class MreHdpt(MelRecord):
    """Head Part."""
    rec_sig = b'HDPT'

    class HeaderFlags(MelRecord.HeaderFlags):
        not_playable: bool = flag(2)

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelHdptShared(),
        MelConditionList(),
    )

#------------------------------------------------------------------------------
class MreIdle(MelRecord):
    """Idle Animation."""
    rec_sig = b'IDLE'

    melSet = MelSet(
        MelEdid(),
        MelConditionList(),
        MelString(b'DNAM', 'behavior_graph'),
        MelIdleEnam(),
        MelIdleRelatedAnims(),
        MelIdleData(),
        MelString(b'GNAM', 'animation_file'),
    )

#------------------------------------------------------------------------------
class MreIdlm(AMreWithKeywords):
    """Idle Marker."""
    rec_sig = b'IDLM'

    class HeaderFlags(MelRecord.HeaderFlags):
        child_can_use: bool = flag(29)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelKeywords(),
        MelIdleAnimFlags(),
        MelIdleAnimationCount(),
        MelIdleTimerSetting(),
        MelIdleAnimations(),
        MelFid(b'QNAM', 'unknown_qnam'),
        MelModel(),
    )

#------------------------------------------------------------------------------
_dnam_attrs4 = ('dof_vignette_radius', 'dof_vignette_strength')
_dnam_counters4 = tuple(f'{x}_count' for x in _dnam_attrs4)
_dnam_counter_mapping = AMreImad.dnam_counter_mapping | dict(
    zip(_dnam_attrs4, _dnam_counters4))
_imad_sig_attr = AMreImad.imad_sig_attr.copy()
_imad_sig_attr.insert(12, (b'NAM5', 'dof_vignette_radius'))
_imad_sig_attr.insert(13, (b'NAM6', 'dof_vignette_strength'))

class MreImad(AMreImad): # see AMreImad for details
    """Image Space Adapter."""
    melSet = MelSet(
        MelEdid(),
        MelPartialCounter(MelTruncatedStruct(b'DNAM',
            ['I', 'f', '49I', '2f', '3I', '2B', '2s', '6I'], 'imad_animatable',
            'imad_duration', *AMreImad.dnam_counters1,
            'radial_blur_use_target', 'radial_blur_center_x',
            'radial_blur_center_y', *AMreImad.dnam_counters2,
            'dof_use_target', (AMreImad.imad_dof_flags, 'dof_flags'),
            'unused1', *AMreImad.dnam_counters3, *_dnam_counters4,
            old_versions={'If49I2f3I2B2s4I'}),
            counters=AMreImad.dnam_counter_mapping),
        *[AMreImad.special_impls[s](s, a) for s, a in _imad_sig_attr],
    )

#------------------------------------------------------------------------------
class MreImgs(MelRecord):
    """Image Space."""
    rec_sig = b'IMGS'
    _has_duplicate_attrs = True # ENAM is an older version of HNAM/CNAM/TNAM

    melSet = MelSet(
        MelEdid(),
        # Only found in one record (DefaultImageSpaceExterior [IMGS:00000161]),
        # skip for everything else
        MelReadOnly(MelStruct(b'ENAM', ['14f'], 'hdr_eye_adapt_speed',
            'hdr_tonemap_e', 'hdr_bloom_threshold', 'hdr_bloom_scale',
            'hdr_auto_exposure_min_max', 'hdr_sunlight_scale', 'hdr_sky_scale',
            'cinematic_saturation', 'cinematic_brightness',
            'cinematic_contrast', 'tint_amount', *color3_attrs('tint_color'))),
        ##: Do we need to specify defaults for hdr_auto_exposure_max,
        # hdr_auto_exposure_min and hdr_middle_gray so that we can upgrade ENAM
        # to HNAM?
        MelStruct(b'HNAM', ['9f'], 'hdr_eye_adapt_speed', 'hdr_tonemap_e',
            'hdr_bloom_threshold', 'hdr_bloom_scale', 'hdr_auto_exposure_max',
            'hdr_auto_exposure_min', 'hdr_sunlight_scale', 'hdr_sky_scale',
            'hdr_middle_gray'),
        MelImgsCinematic(),
        MelImgsTint(),
        MelTruncatedStruct(b'DNAM', ['3f', '2s', 'H', '2f'], 'dof_strength',
            'dof_distance', 'dof_range', 'dof_unknown', 'dof_sky_blur_radius',
            'dof_vignette_radius', 'dof_vignette_strength',
            old_versions={'3f2sH'}),
        MelString(b'TX00', 'imgs_lut'),
    )

#------------------------------------------------------------------------------
class MreInfo(MelRecord):
    """Dialog Response."""
    rec_sig = b'INFO'

    class HeaderFlags(MelRecord.HeaderFlags):
        info_group: bool = flag(6)
        exclude_from_export: bool = flag(7)
        actor_changed: bool = flag(13)

    class _info_response_flags(Flags):
        start_scene_on_end: bool = flag(0)
        random: bool = flag(1)
        say_once: bool = flag(2)
        requires_player_activation: bool = flag(3)
        random_end: bool = flag(5)
        end_running_scene: bool = flag(6)
        force_greet_hello: bool = flag(7)
        player_address: bool = flag(8)
        force_subtitle: bool = flag(9)
        can_move_while_greeting: bool = flag(10)
        no_lip_file: bool = flag(11)
        requires_post_processing: bool = flag(12)
        audio_output_override: bool = flag(13)
        has_capture: bool = flag(14)

    class _info_response_flags2(Flags):
        random: bool = flag(1)
        force_all_children_player_activate_only: bool = flag(3)
        random_end: bool = flag(5)
        child_infos_dont_inherit_reset_data: bool = flag(8)
        force_all_children_random: bool = flag(9)
        dont_do_all_before_repeating: bool = flag(11)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelStruct(b'ENAM', ['3H'], (_info_response_flags, 'response_flags'),
            (_info_response_flags2, 'response_flags2'), 'reset_hours'),
        MelFid(b'TPIC', 'info_topic'),
        MelFid(b'PNAM', 'prev_info'),
        MelFid(b'DNAM', 'shared_info'),
        MelFid(b'GNAM', 'info_group'),
        MelString(b'IOVR', 'override_file_name'),
        MelGroups('info_responses',
            MelStruct(b'TRDA', ['I', 'B', 'I', 's', 'H', '2i'],
                (FID, 'rd_emotion'), 'rd_response_number', (FID, 'rd_sound'),
                'rd_unknown1', 'rd_interrupt_percentage',
                'rd_camera_target_alias', 'rd_camera_location_alias'),
            MelLString(b'NAM1', 'response_text'),
            MelString(b'NAM2', 'script_notes'),
            MelString(b'NAM3', 'response_edits'),
            MelString(b'NAM4', 'alternate_lip_text'),
            MelFid(b'SNAM', 'idle_animations_speaker'),
            MelFid(b'LNAM', 'idle_animations_listener'),
            MelUInt16(b'TNAM', 'interrupt_percentage'),
            MelBase(b'NAM9', 'response_text_hash'),
            MelFid(b'SRAF', 'response_camera_path'),
            MelBase(b'WZMD', 'stop_on_scene_end'),
        ),
        MelConditionList(),
        MelLString(b'RNAM', 'info_prompt'),
        MelFid(b'ANAM', 'info_speaker'),
        MelFid(b'TSCE', 'start_scene'),
        MelBase(b'INTV', 'unknown_intv'),
        MelSInt32(b'ALFA', 'forced_alias'),
        MelFid(b'ONAM', 'audio_output_override'),
        MelUInt32(b'GREE', 'greet_distance'),
        MelStruct(b'TIQS', ['2h'], 'spqs_on_begin', 'spqs_on_end'),
        MelString(b'NAM0', 'start_scene_phase'),
        MelUInt32(b'INCC', 'info_challenge'),
        MelFid(b'MODQ', 'reset_global'),
        MelUInt32(b'INAM', 'subtitle_priority'),
    )

#------------------------------------------------------------------------------
class MreIngr(AMreWithKeywords):
    """Ingredient."""
    rec_sig = b'INGR'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelKeywords(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelEquipmentType(),
        MelSoundPickupDrop(),
        MelValueWeight(),
        MelIngrEnit(),
        MelEffects(),
    )

#------------------------------------------------------------------------------
class MreInnr(MelRecord):
    """Instance Naming Rules."""
    rec_sig = b'INNR'

    melSet = MelSet(
        MelEdid(),
        MelUInt32(b'UNAM', 'innr_target'),
        MelGroups('naming_rulesets',
            MelCounter(MelUInt32(b'VNAM', 'naming_rules_count'),
                counts='naming_rules'),
            MelGroups('naming_rules',
                MelLString(b'WNAM', 'naming_rule_text'),
                MelKeywords(),
                MelStruct(b'XNAM', ['f', '2B'], 'naming_rule_property_value',
                    'naming_rule_property_target', 'naming_rule_property_op'),
                MelUInt16(b'YNAM', 'naming_rule_index'),
            ),
        ),
    )

#------------------------------------------------------------------------------
class MreIpct(MelRecord):
    """Impact."""
    rec_sig = b'IPCT'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelStruct(b'DATA', ['f', 'I', '2f', 'I', '2B', '2s'],
            'effect_duration', 'effect_orientation', 'angle_threshold',
            'placement_radius', 'ipct_sound_level', 'ipct_no_decal_data',
            'impact_result', 'unknown1'),
        MelDecalData(),
        MelIpctTextureSets(),
        MelIpctSounds(),
        MelFid(b'NAM3', 'footstep_explosion'),
        MelIpctHazard(),
        MelFloat(b'FNAM', 'footstep_particle_max_dist'),
    )

#------------------------------------------------------------------------------
class MreIpds(MelRecord):
    """Impact Dataset."""
    rec_sig = b'IPDS'

    melSet = MelSet(
        MelEdid(),
        MelIpdsPnam(),
    )

#------------------------------------------------------------------------------
class MreKeym(AMreWithKeywords):
    """Key."""
    rec_sig = b'KEYM'

    class HeaderFlags(MelRecord.HeaderFlags):
        calc_value_from_components: bool = flag(11)
        pack_in_use_only: bool = flag(13)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelSoundPickupDrop(),
        MelKeywords(),
        MelValueWeight(),
    )

#------------------------------------------------------------------------------
class MreKssm(MelRecord):
    """Sound Keyword Mapping."""
    rec_sig = b'KSSM'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'DNAM', 'primary_descriptor'),
        MelFid(b'ENAM', 'exterior_tail'),
        MelFid(b'VNAM', 'vats_descriptor'),
        MelFloat(b'TNAM', 'vats_threshold'),
        MelSimpleGroups('kssm_keywords', MelFid(b'KNAM')),
        MelSorted(MelGroups('kssm_sounds',
            MelStruct(b'RNAM', ['2I'], 'ks_reverb_class',
                (FID, 'ks_sound_descriptor')),
        ), sort_by_attrs='ks_reverb_class'),
    )

#------------------------------------------------------------------------------
class MreKywd(MelRecord):
    """Keyword."""
    rec_sig = b'KYWD'
    _has_duplicate_attrs = True # NNAM is an older version of FULL

    class HeaderFlags(MelRecord.HeaderFlags):
        restricted: bool = flag(15)

    melSet = MelSet(
        MelEdid(),
        MelColorO(),
        MelNotesTypeRule(),
        MelFull(),
        # Older format - read, but only dump FULL
        MelReadOnly(MelString(b'NNAM', 'full')),
    )

#------------------------------------------------------------------------------
class MreLand(MelRecord):
    """Landscape."""
    rec_sig = b'LAND'

    melSet = MelSet(
        MelLandShared(),
        MelLandMpcd(),
    )

#------------------------------------------------------------------------------
class MreLayr(MelRecord):
    """Layer."""
    rec_sig = b'LAYR'

    melSet = MelSet(
        MelEdid(),
        MelParent(),
    )

#------------------------------------------------------------------------------
class MreLcrt(MelRecord):
    """Location Reference Type."""
    rec_sig = b'LCRT'

    melSet = MelSet(
        MelEdid(),
        MelColorO(),
        MelBase(b'TNAM', 'unknown_tnam'),
    )

#------------------------------------------------------------------------------
class MreLctn(AMreWithKeywords):
    """Location."""
    rec_sig = b'LCTN'

    class HeaderFlags(MelRecord.HeaderFlags):
        # mouthful - better name?
        interior_cells_use_ref_for_world_map_player_location: bool = flag(11)
        partial_form: bool = flag(14)

    melSet = MelSet(
        MelLctnShared(),
        MelFloat(b'ANAM', 'actor_fade_mult'),
        MelColorO(),
    )

#------------------------------------------------------------------------------
class MreLens(MelRecord):
    """Lens Flare."""
    rec_sig = b'LENS'

    melSet = MelSet(
        MelLensShared(),
    ).with_distributor(lens_distributor)

#------------------------------------------------------------------------------
class MreLgtm(MelRecord):
    """Lighting Template."""
    rec_sig = b'LGTM'

    melSet = MelSet(
        MelEdid(),
        MelTruncatedStruct(b'DATA',
            ['3B', 's', '3B', 's', '3B', 's', '2f', '2i', '3f', '32s', '3B',
             's', '3f', '4s', '2f', '3B', 's', '3B', 's', '7f'],
            *color_attrs('lgtm_ambient_color'),
            *color_attrs('lgtm_directional_color'),
            *color_attrs('lgtm_fog_color_near'), 'lgtm_fog_near',
            'lgtm_fog_far', 'lgtm_directional_rotation_xy',
            'lgtm_directional_rotation_z', 'lgtm_directional_fade',
            'lgtm_fog_clip_distance', 'lgtm_fog_power',
            'lgtm_unused1', *color_attrs('lgtm_fog_color_far'),
            'lgtm_fog_max', 'lgtm_light_fade_distances_start',
            'lgtm_light_fade_distances_end', 'lgtm_unused2',
            'lgtm_near_height_mid', 'lgtm_near_height_range',
            *color_attrs('lgtm_fog_color_high_near'),
            *color_attrs('lgtm_fog_color_high_far'), 'lgtm_high_density_scale',
            'lgtm_fog_near_scale', 'lgtm_fog_far_scale',
            'lgtm_fog_high_near_scale', 'lgtm_fog_high_far_scale',
            'lgtm_far_height_mid', 'lgtm_far_height_range', old_versions={
                '3Bs3Bs3Bs2f2i3f32s3Bs3f4s2f3Bs3Bs5f',
                '3Bs3Bs3Bs2f2i3f32s3Bs3f4s',
            }),
        MelDalc(),
        MelGodRays(),
    )

#------------------------------------------------------------------------------
class MreLigh(AMreWithKeywords, _AMreWithProperties):
    """Light."""
    rec_sig = b'LIGH'

    class HeaderFlags(MelRecord.HeaderFlags):
        random_anim_start: bool = flag(16)
        obstacle: bool = flag(25)
        portal_strict: bool = flag(28)

    class _light_flags(Flags):
        light_can_take: bool = flag(1)
        light_flickers: bool = flag(3)
        light_off_by_default: bool = flag(5)
        light_pulses: bool = flag(7)
        light_shadow_spotlight: bool = flag(10)
        light_shadow_hemisphere: bool = flag(11)
        light_shadow_omnidirectional: bool = flag(12)
        light_nonshadow_spotlight: bool = flag(14)
        light_non_specular: bool = flag(15)
        light_attenuation_only: bool = flag(16)
        light_nonshadow_box: bool = flag(17)
        light_ignore_roughness: bool = flag(18)
        light_no_rim_lighting: bool = flag(19)
        light_ambient_only: bool = flag(20)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelPreviewTransform(),
        MelModel(),
        MelKeywords(),
        MelDestructible(),
        MelProperties(),
        MelFull(),
        MelIcons(),
        MelTruncatedStruct(b'DATA', ['i', 'I', '3B', 's', 'I', '10f', 'I',
                                     'f'], 'duration', 'light_radius',
            *color_attrs('light_color'), (_light_flags, 'light_flags'),
            'light_falloff', 'light_fov', 'light_near_clip',
            'light_fe_period', # fe = 'Flicker Effect'
            'light_fe_intensity_amplitude', 'light_fe_movement_amplitude',
            'light_constant', 'light_scalar', 'light_exponent',
            'light_god_rays_near_clip', 'value', 'weight', old_versions={
                'iI3BsI10fI', 'iI3BsI8f',
            }),
        MelLighFade(),
        MelString(b'NAM0', 'light_gobo'),
        MelLighLensFlare(),
        MelGodRays(),
        MelSound(),
    )

#------------------------------------------------------------------------------
class MreLscr(MelRecord):
    """Load Screen."""
    rec_sig = b'LSCR'

    class HeaderFlags(MelRecord.HeaderFlags):
        displays_in_main_menu: bool = flag(10)
        no_rotation: bool = flag(15)

    melSet = MelSet(
        MelEdid(),
        MelDescription(),
        MelConditionList(),
        MelLscrNif(),
        MelFid(b'TNAM', 'lscr_transform'),
        MelLscrRotation(),
        MelStruct(b'ZNAM', ['2f'], 'lscr_zoom_min', 'lscr_zoom_max'),
        MelLscrCameraPath(),
    )

#------------------------------------------------------------------------------
class MreLtex(MelRecord):
    """Landscape Texture."""
    rec_sig = b'LTEX'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'TNAM', 'ltex_texture_set'),
        MelFid(b'MNAM', 'ltex_material_type'),
        MelStruct(b'HNAM', ['2B'], 'hd_friction',
            'hd_restitution'), # hd = 'Havok Data'
        MelLtexSnam(),
        MelLtexGrasses(),
    )

#------------------------------------------------------------------------------
class MreLvli(AMreLeveledList):
    """Leveled Item."""
    rec_sig = b'LVLI'
    _top_copy_attrs = ('lvl_chance_none', 'lvl_max_count', 'lvl_global',
                       'filter_keyword_chances', 'epic_loot_chance',
                       'lvli_override_name')
    _entry_copy_attrs = ('level', 'listId', 'count', 'item_chance_none',
                         'item_owner', 'item_global', 'item_condition')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelLLChanceNone(),
        MelLLMaxCount(),
        MelLLFlags(),
        MelLLGlobal(),
        MelLLItems(),
        MelLlkc(),
        MelFid(b'LVSG', 'epic_loot_chance'),
        MelLString(b'ONAM', 'lvli_override_name')
    )

#------------------------------------------------------------------------------
class MreLvln(AMreLeveledList):
    """Leveled NPC."""
    rec_sig = b'LVLN'
    _top_copy_attrs = ('lvl_chance_none', 'lvl_max_count', 'lvl_global',
                       'filter_keyword_chances', 'model')
    _entry_copy_attrs = ('level', 'listId', 'count', 'item_chance_none',
                         'item_owner', 'item_global', 'item_condition')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelLLChanceNone(),
        MelLLMaxCount(),
        MelLLFlags(),
        MelLLGlobal(),
        MelLLItems(),
        MelLlkc(),
        MelModel(),
    )

#------------------------------------------------------------------------------
class MreLvsp(AMreLeveledList):
    """Leveled Spell."""
    rec_sig = b'LVSP'
    _top_copy_attrs = ('lvl_chance_none', 'lvl_max_count')
    _entry_copy_attrs = ('level', 'listId', 'count', 'item_chance_none')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelLLChanceNone(),
        MelLLMaxCount(),
        MelLLFlags(),
        MelLLItems(with_coed=False),
    )

#------------------------------------------------------------------------------
class MreMato(MelRecord):
    """Material Object."""
    rec_sig = b'MATO'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelMatoPropertyData(),
        MelTruncatedStruct(b'DATA', ['11f', 'I'], 'falloff_scale',
            'falloff_bias', 'noise_uv_scale', 'material_uv_scale',
            'projection_vector_x', 'projection_vector_y',
            'projection_vector_z', 'normal_dampener',
            *color3_attrs('single_pass_color'), 'is_single_pass',
            old_versions={'8f', '7f'}),
    )

#------------------------------------------------------------------------------
class MreMatt(MelRecord):
    """Material Type."""
    rec_sig = b'MATT'

    melSet = MelSet(
        MelEdid(),
        MelMattShared(),
        MelString(b'ANAM', 'breakable_fx'),
        # Ignore texture hashes - they're only an optimization, plenty of
        # records in Skyrim.esm are missing them
        MelNull(b'MODT'),
    )

#------------------------------------------------------------------------------
class MreMesg(MelRecord):
    """Message."""
    rec_sig = b'MESG'

    melSet = MelSet(
        MelEdid(),
        MelDescription(),
        MelFull(),
        MelMesgShared(),
        MelString(b'SNAM', 'message_swf'),
        MelLString(b'NNAM', 'short_title'),
        MelMesgButtons(MelConditionList()),
    )

#------------------------------------------------------------------------------
class MreMgef(AMreMgefTes5):
    """Magic Effect."""
    rec_sig = b'MGEF'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelFull(),
        MelMdob(),
        MelKeywords(),
        # Names match Skyrim because MGEF access is all over the codebase
        MelMgefData(MelStruct(b'DATA',
            ['I', 'f', 'I', '4s', 'I', 'H', '2s', 'I', 'f', '4I', '4f', '10I',
             'f', 'I', 'f', '7I', '2f'],
            (MgefFlags, 'flags'), 'base_cost', (FID, 'associated_item'),
            'unused_magic_skill', (FID, 'resist_value'),
            'counter_effect_count', 'unused1', (FID, 'light'), 'taper_weight',
            (FID, 'hit_shader'), (FID, 'enchant_shader'),
            'minimum_skill_level', 'spellmaking_area',
            'spellmaking_casting_time', 'taper_curve', 'taper_duration',
            'second_av_weight', 'effect_archetype', (FID, 'actorValue'),
            (FID, 'projectile'), (FID, 'explosion'), 'casting_type',
            'delivery', (FID, 'second_av'), (FID, 'casting_art'),
            (FID, 'hit_effect_art'), (FID, 'effect_impact_data'),
            'skill_usage_multiplier', (FID, 'dual_casting_art'),
            'dual_casting_scale', (FID, 'enchant_art'), (FID, 'hit_visuals'),
            (FID, 'enchant_visuals'), (FID, 'equip_ability'),
            (FID, 'effect_imad'), (FID, 'perk_to_apply'),
            'casting_sound_level', 'script_effect_ai_score',
            'script_effect_ai_delay_time')),
        MelMgefEsce(),
        MelMgefSounds(),
        MelMgefDnam(),
        MelConditionList(),
    )

#------------------------------------------------------------------------------
class MreMisc(AMreWithKeywords):
    """Misc. Item."""
    rec_sig = b'MISC'

    class HeaderFlags(MelRecord.HeaderFlags):
        calc_from_components: bool = flag(11)
        pack_in_use_only: bool = flag(13)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelSoundPickupDrop(),
        MelKeywords(),
        MelFid(b'FIMD', 'featured_item_message'),
        MelValueWeight(),
        MelArray('misc_components',
            MelStruct(b'CVPA', ['2I'], (FID, 'component_fid'),
                'component_count'),
        ),
        MelSimpleArray('component_display_indices', MelUInt8(b'CDIX')),
    )

#------------------------------------------------------------------------------
class MreMovt(MelRecord):
    """Movement Type."""
    rec_sig = b'MOVT'

    melSet = MelSet(
        MelEdid(),
        MelMovtName(),
        MelSped(),
        MelMovtThresholds(), # unused, leftover
        MelFloat(b'JNAM', 'float_height'),
        MelFloat(b'LNAM', 'flight_angle_gain'),
    )

#------------------------------------------------------------------------------
class MreMstt(AMreWithKeywords, _AMreWithProperties):
    """Moveable Static."""
    rec_sig = b'MSTT'

    class HeaderFlags(MelRecord.HeaderFlags):
        must_update_anims: bool = flag(8)
        hidden_from_local_map: bool = flag(9)
        used_as_platform: bool = flag(11)
        pack_in_use_only: bool = flag(13)
        has_distant_lod: bool = flag(15)
        random_anim_start: bool = flag(16)
        has_currents: bool = flag(19)
        obstacle: bool = flag(25)
        navmesh_filter: bool = flag(26)
        navmesh_bounding_box: bool = flag(27)
        navmesh_ground: bool = flag(30)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelProperties(),
        MelUInt8(b'DATA', 'on_local_map'), # really a bool
        MelSound(),
    )

#------------------------------------------------------------------------------
class MreMswp(MelRecord):
    """Material Swap."""
    rec_sig = b'MSWP'

    class HeaderFlags(MelRecord.HeaderFlags):
        custom_swap: bool = flag(16)

    melSet = MelSet(
        MelEdid(),
        MelString(b'FNAM', 'tree_folder'),
        MelSorted(MelGroups('material_substitutions',
            MelString(b'BNAM', 'original_material'),
            MelString(b'SNAM', 'replacement_material'),
            ##: xEdit sources say "will be moved up to First FNAM", is that
            # something we have to implement?
            MelString(b'FNAM', 'tree_folder_obsolete'),
            MelFloat(b'CNAM', 'color_remapping_index'),
        ), sort_by_attrs='original_material'),
    ).with_distributor({
        b'FNAM': 'tree_folder',
        b'BNAM': {
            b'FNAM': 'material_substitutions',
        },
    })

#------------------------------------------------------------------------------
class MreMusc(MelRecord):
    """Music Type."""
    rec_sig = b'MUSC'

    melSet = MelSet(
        MelEdid(),
        MelMuscShared(),
    )

#------------------------------------------------------------------------------
class MreMust(MelRecord):
    """Music Track."""
    rec_sig = b'MUST'

    melSet = MelSet(
        MelMustShared(MelConditions()),
    )

#------------------------------------------------------------------------------
# Not mergeable due to the weird special handling the game and CK do with it
# (plus we only have like half the record implemented)
class MreNavi(MelRecord):
    """Navigation Mesh Info Map."""
    rec_sig = b'NAVI'

    melSet = MelSet(
        MelEdid(),
        MelUInt32(b'NVER', 'navi_version'),
        MelGroups('navigation_map_infos',
            ##: Rest of this subrecord would need custom code to handle
            ##: The 20 bytes probably have the same meaning as in Skyrim
            MelExtra(MelStruct(b'NVMI', ['I', '20s'],
                'nvmi_navmesh', 'nvmi_unknown1'), extra_attr='nvmi_todo'),
        ),
        ##: Would need custom code to handle
        MelBase(b'NVPP', 'nvpp_todo'),
        MelBase(b'NVSI', 'unknown_nvsi'), # Not decoded yet
    )

#------------------------------------------------------------------------------
# Not mergeable because it's related to navmeshes (and barely decoded at that)
class MreNocm(MelRecord):
    """Navigation Mesh Obstacle Manager."""
    rec_sig = b'NOCM'

    melSet = MelSet(
        MelEdid(),
        MelGroups('nocm_unknown1',
            MelUInt32(b'INDX', 'nocm_index'),
            MelGroups('unknown_data',
                MelBase(b'DATA', 'unknown_data_entry'),
            ),
            MelBase(b'INTV', 'unknown_intv'),
            MelString(b'NAM1', 'nocm_model'),
        ),
    )

#------------------------------------------------------------------------------
class MreNote(MelRecord):
    """Note."""
    rec_sig = b'NOTE'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelPreviewTransform(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelSoundPickupDrop(),
        MelNoteType(b'DNAM'),
        MelValueWeight(),
        MelUnion({
            0: MelStruct(b'SNAM', ['4s'], 'note_contents'), # Unused
            (1, 2, 3): MelFid(b'SNAM', 'note_contents'),
        }, decider=AttrValDecider('note_type')),
        MelString(b'PNAM', 'program_file'),
    )

#------------------------------------------------------------------------------
class _NpcTendDecider(SizeDecider):
    """The NPC_ subrecord TEND specifies properties for one tint layer. It can
    either be a single byte in size, in which case it only specifies a value
    (e.g. setting '1182 Damage - Scar - Lip Gouges' to 0.33) or it can be 7
    bytes in length, in which case it specifies a value, a color and a template
    color index for the layer.

    This is easy to handle at load time, but in order to allow runtime
    modification we need to check if WB set or removed the non-value fields.
    Since this is all or nothing (either you add all the extra fields or you
    remove all of them, anything else would blow up on dump), we only check the
    template color index."""
    can_decide_at_dump = True

    def decide_dump(self, record):
        return 1 if record.tint_template_color_index is None else 7

class MreNpc_(AMreActor, AMreWithKeywords, _AMreWithProperties):
    """Non-Player Character."""
    rec_sig = b'NPC_'

    class HeaderFlags(AMreActor.HeaderFlags):
        bleedout_override: bool = flag(29)

    class NpcFlags(Flags):
        npc_female: bool = flag(0)
        npc_essential: bool = flag(1)
        is_chargen_face_preset: bool = flag(2)
        npc_respawn: bool = flag(3)
        npc_auto_calc: bool = flag(4)
        npc_unique: bool = flag(5)
        does_not_affect_stealth: bool = flag(6)
        pc_level_offset: bool = flag(7)
        calc_for_each_template: bool = flag(9)
        npc_protected: bool = flag(11)
        npc_summonable: bool = flag(14)
        does_not_bleed: bool = flag(16)
        bleedout_override: bool = flag(18)
        opposite_gender_anims: bool = flag(19)
        simple_actor: bool = flag(20)
        no_activation_or_hellos: bool = flag(23)
        diffuse_alpha_test: bool = flag(24)
        npc_is_ghost: bool = flag(29)
        npc_invulnerable: bool = flag(31)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(is_required=True),
        MelPreviewTransform(),
        MelAnimationSound(),
        MelStruct(b'ACBS', ['I', '2h', '2H', 'h', '2H', '2s'],
            (NpcFlags, 'npc_flags'), 'xp_value_offset', 'level_offset',
            'calc_min_level', 'calc_max_level', 'disposition_base',
            (TemplateFlags, 'template_flags'), 'bleedout_override',
            'unknown1', is_required=True),
        MelFactions(),
        MelDeathItem(),
        MelVoice(),
        MelTemplate('default_template'),
        MelFid(b'LTPT', 'legendary_template'),
        MelFid(b'LTPC', 'legendary_chance'),
        MelStruct(b'TPTA', ['13I'], (FID, 'template_actor_traits'),
            (FID, 'template_actor_stats'), (FID, 'template_actor_factions'),
            (FID, 'template_actor_spell_list'),
            (FID, 'template_actor_ai_data'),
            (FID, 'template_actor_ai_packages'),
            (FID, 'template_actor_model_animation'),
            (FID, 'template_actor_base_data'),
            (FID, 'template_actor_inventory'), (FID, 'template_actor_script'),
            (FID, 'template_actor_def_pack_list'),
            (FID, 'template_actor_attack_data'),
            (FID, 'template_actor_keywords')),
        MelRace(),
        MelSpellCounter(),
        MelSpells(),
        MelDestructible(),
        MelSkin(),
        MelNpcAnam(),
        MelAttackRace(),
        MelAttacks(),
        MelOverridePackageLists(),
        MelFid(b'FCPL', 'follower_command_package_list'),
        MelFid(b'RCLR', 'follower_elevator_package_list'),
        MelNpcPerks(),
        MelProperties(),
        MelFtyp(),
        MelNativeTerminal(),
        MelItems(),
        MelTruncatedStruct(b'AIDT', ['8B', '3I', 'B', '3s'], 'ai_aggression',
            'ai_confidence', 'ai_energy_level', 'ai_responsibility', 'ai_mood',
            'ai_assistance', 'ai_aggro_radius_behavior', 'ai_unknown1',
            'ai_warn', 'ai_warn_attack', 'ai_attack', 'ai_no_slow_approach',
            'ai_unknown2', old_versions={'8B3I'}),
        MelAIPackages(),
        MelKeywords(),
        MelAppr(),
        MelObjectTemplate(),
        MelNpcClass(),
        MelFull(),
        MelShortName(b'SHRT'),
        MelBaseR(b'DATA', 'npc_marker'),
        MelStruct(b'DNAM', ['3H', 'B', 's'], 'calculated_health',
            'calculated_action_points', 'far_away_model_distance',
            'geared_up_weapons', 'dnam_unused'),
        MelNpcHeadParts(),
        MelNpcHairColor(),
        MelFid(b'BCLF', 'facial_hair_color'),
        MelCombatStyle(),
        MelNpcGiftFilter(),
        ##: Marker? xEdit just has it as unknown. Seems to always be two bytes
        # and set to 0x00FF
        MelBaseR(b'NAM5', 'unknown_required'),
        MelFloat(b'NAM6', 'npc_height_min'),
        MelFloat(b'NAM7', 'unused_nam7'),
        MelFloat(b'NAM4', 'npc_height_max'),
        MelStruct(b'MWGT', ['3f'], 'npc_weight_thin', 'npc_weight_muscular',
            'npc_weight_fat'),
        MelSoundLevel(b'NAM8'),
        MelActorSounds2(),
        MelInheritsSoundsFrom(),
        MelFid(b'PFRN', 'power_armor_stand'),
        MelNpcShared(),
        MelStruct(b'QNAM', ['4f'], *color_attrs('texture_lighting')),
        # These two are linked and will need special handling if we wanted to
        # patch them for some reason
        MelSimpleArray('morph_keys', MelUInt32(b'MSDK')),
        MelSimpleArray('morph_values', MelFloat(b'MSDV')),
        MelSorted(MelGroups('face_tint_layers',
            MelStruct(b'TETI', ['2H'], 'tint_data_type', 'tint_index'),
            # These can (and do) occur freely mixed within the same record, see
            # _NpcTendDecider
            MelUnion({
                1: MelUInt8(b'TEND', 'tint_value'),
                7: MelStruct(b'TEND', ['5B', 'h'], 'tint_value',
                    *color_attrs('tint_color'), 'tint_template_color_index'),
            }, decider=_NpcTendDecider()),
        ), sort_by_attrs='tint_index'),
        # bmrv = 'body morph region values'
        MelStruct(b'MRSV', ['5f'], 'bmrv_head', 'bmrv_upper_torso',
            'bmrv_arms', 'bmrv_lower_torso', 'bmrv_legs'),
        ##: xEdit says 'reported to cause issues when sorted', but then it
        # *does* sort it. Outdated comment or wrong code?
        MelSorted(MelGroups('face_morphs',
            # fm = 'face morph'
            MelUInt32(b'FMRI', 'fm_index'),
            ##: fm_unknown seems to always be 8 bytes, figure out what it is
            MelExtra(MelStruct(b'FMRS', ['7f'], *position_attrs('fm'),
                *rotation_attrs('fm'), 'fm_scale'),
                extra_attr='fm_unknown'),
        ), sort_by_attrs='fm_index'),
        MelFloat(b'FMIN', 'facial_morph_intensity'),
        MelAttx(),
    ).with_distributor(_object_template_distributor)

#------------------------------------------------------------------------------
class MreOmod(MelRecord):
    """Object Modification."""
    rec_sig = b'OMOD'

    class HeaderFlags(MelRecord.HeaderFlags):
        legendary_omod: bool = flag(4)
        omod_collection: bool = flag(7)

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelModel(),
        MelOmodData(),
        MelSimpleArray('target_omod_keywords', MelFid(b'MNAM')),
        MelSimpleArray('filter_keywords', MelFid(b'FNAM')),
        MelFid(b'LNAM', 'loose_omod'),
        MelUInt8(b'NAM1', 'omod_priority'),
        MelFilterString(),
    )

#------------------------------------------------------------------------------
class MreOvis(MelRecord):
    """Object Visibility Manager."""
    rec_sig = b'OVIS'

    melSet = MelSet(
        MelEdid(),
        MelGroups('ovis_unknown',
            MelFid(b'INDX', 'ovis_object_fid'),
            MelStruct(b'DATA', ['6f'], 'ovis_object_bounds_x1',
                'ovis_object_bounds_y1', 'ovis_object_bounds_z1',
                'ovis_object_bounds_x2', 'ovis_object_bounds_y2',
                'ovis_object_bounds_z2'),
        ),
    )

#------------------------------------------------------------------------------
class MrePack(MelRecord):
    """Package."""
    rec_sig = b'PACK'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelPackPkdt(),
        MelPackSchedule(),
        MelConditionList(),
        MelGroup('package_idles',
            MelIdleAnimFlags(),
            MelIdleAnimationCount(),
            MelIdleTimerSetting(),
            MelIdleAnimations(),
            MelBase(b'IDLB', 'unknown_idlb'),
        ),
        MelCombatStyle(b'CNAM'),
        MelPackOwnerQuest(),
        MelPackPkcu(),
        MelPackDataInputValues(
            pldt_element=MelLocation(b'PLDT'),
            ptda_element=MelUnion({
                (0, 1, 3, 7): MelStruct(b'PTDA', ['i', 'I', 'i'],
                    'package_target_type', (FID, 'package_target_value'),
                    'package_target_count'),
                (2, 5): MelStruct(b'PTDA', ['i', 'I', 'i'],
                    'package_target_type', 'package_target_value',
                    'package_target_count'),
                4: MelStruct(b'PTDA', ['3i'],
                    'package_target_type', 'package_target_value',
                    'package_target_count'),
                (6, 8): MelStruct(b'PTDA', ['i', '4s', 'i'],
                    'package_target_type', 'package_target_value',
                    'package_target_count'),
            }, decider=PartialLoadDecider(
                loader=MelSInt32(b'PTDA', 'package_target_type'),
                decider=AttrValDecider('package_target_type')),
                fallback=MelNull(b'NULL')), # ignore
        ),
        MelPackDataInputs('data_inputs1'),
        MelBaseR(b'XNAM', 'xnam_marker'),
        MelPackProcedureTree(MelConditions()),
        MelPackDataInputs('data_inputs2'),
        MelPackIdleHandler('on_begin'),
        MelPackIdleHandler('on_end'),
        MelPackIdleHandler('on_change'),
    ).with_distributor({
        b'PKDT': {
            b'CTDA|CIS1|CIS2': 'conditions',
            b'CNAM': 'combat_style',
            b'QNAM': 'owner_quest',
            b'ANAM': ('data_input_values', {
                b'BNAM|CNAM|PDTO': 'data_input_values',
            }),
            b'UNAM': ('data_inputs1', {
                b'BNAM|PNAM': 'data_inputs1',
            }),
        },
        b'XNAM': {
            b'ANAM|CTDA|CIS1|CIS2|PNAM': 'procedure_tree_branches',
            b'UNAM': ('data_inputs2', {
                b'BNAM|PNAM': 'data_inputs2',
            }),
        },
        b'POBA': {
            b'INAM|TNAM|PDTO': 'on_begin',
        },
        b'POEA': {
            b'INAM|TNAM|PDTO': 'on_end',
        },
        b'POCA': {
            b'INAM|TNAM|PDTO': 'on_change',
        },
    })

#------------------------------------------------------------------------------
class MrePerk(MelRecord):
    """Perk."""
    rec_sig = b'PERK'

    class HeaderFlags(MelRecord.HeaderFlags):
        not_playable: bool = flag(2)

    class _script_flags(Flags):
        run_immediately: bool
        replace_default: bool

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
    ).with_distributor(perk_distributor)

#------------------------------------------------------------------------------
class MrePkin(MelRecord):
    """Pack-In."""
    rec_sig = b'PKIN'

    class HeaderFlags(MelRecord.HeaderFlags):
        prefab: bool = flag(9)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFilterString(),
        MelFid(b'CNAM', 'packin_cell'),
        MelUInt32(b'VNAM', 'packin_version'),
    )

#------------------------------------------------------------------------------
class MreProj(MelRecord):
    """Projectile."""
    rec_sig = b'PROJ'

    class _ProjFlags(Flags):
        is_hitscan: bool = flag(0)
        is_explosive: bool = flag(1)
        alt_trigger: bool = flag(2)
        has_muzzle_flash: bool = flag(3)
        can_be_disabled: bool = flag(5)
        can_be_picked_up: bool = flag(6)
        is_super_sonic: bool = flag(7)
        pins_limbs: bool = flag(8)
        pass_through_small_transparent: bool = flag(9)
        disable_combat_aim_correction: bool = flag(10)
        penetrates_geometry: bool = flag(11)
        continuous_update: bool = flag(12)
        seeks_target: bool = flag(13)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelBase(b'DATA', 'unused_data'), # Now DNAM
        MelStruct(b'DNAM',
            ['2H', '3f', '2I', '2f', '2I', '3f', '3I', '4f', '2I', 'B', 'I'],
            (_ProjFlags, 'proj_flags'), 'proj_type', 'proj_gravity',
            'proj_speed', 'proj_range', (FID, 'proj_light'),
            (FID, 'muzzle_flash'), 'explosion_alt_trigger_proximity',
            'explosion_alt_trigger_timer', (FID, 'proj_explosion'),
            (FID, 'proj_sound'), 'muzzle_flash_duration',
            'proj_fade_duration', 'proj_impact_force',
            (FID, 'proj_sound_countdown'), (FID, 'proj_sound_disable'),
            (FID, 'default_weapon_source'), 'proj_cone_spread',
            'proj_collision_radius', 'proj_lifetime', 'proj_relaunch_interval',
            (FID, 'proj_decal_data'), (FID, 'proj_collision_layer'),
            'tracer_frequency', (FID, 'vats_projectile')),
        MelProjMuzzleFlashModel(),
        MelSoundLevel(),
    )

#------------------------------------------------------------------------------
class MreRegn(AMreRegn):
    """Region."""
    melSet = MelSet(
        MelEdid(),
        MelColor(b'RCLR'),
        MelWorldspace(),
        MelRegnAreas(with_unknown_anam=True),
        MelSorted(MelGroups('regn_entries',
            MelRegnRdat(),
            MelIcon(),
            MelRegnEntryMusic(),
            MelRegnEntrySounds(),
            MelRegnEntryMapName(),
            MelRegnEntryObjects(),
            MelRegnEntryGrasses(),
            MelRegnEntryWeatherTypes(),
            MelFloat(b'RLDM', 'lod_display_distance_multiplier'),
            MelFloat(b'ANAM', 'occlusion_accuracy_distance'),
        ), sort_by_attrs='regn_data_type'),
    ).with_distributor({
        b'RCLR': {
            b'ANAM': 'regn_areas',
        },
        b'RDAT': {
            b'ANAM': 'regn_entries',
        },
    })

#------------------------------------------------------------------------------
class MreRela(MelRecord):
    """Relationship."""
    rec_sig = b'RELA'

    class _RelationshipFlags(Flags):
        rela_secret: bool = flag(7)

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', ['2I', 'B', '2s', 'B', 'I'], (FID, 'rela_parent'),
            (FID, 'rela_child'), 'rela_rank_type', 'rela_unknown',
            (_RelationshipFlags,  'rela_flags'),
            (FID,'rela_association_type')),
    )

#------------------------------------------------------------------------------
class MreRevb(MelRecord):
    """Reverb Parameters"""
    rec_sig = b'REVB'

    melSet = MelSet(
        MelEdid(),
        MelRevbData(),
        MelUInt32(b'ANAM', 'revb_reverb_class'),
    )

#------------------------------------------------------------------------------
class MreRfgp(MelRecord):
    """Reference Group."""
    rec_sig = b'RFGP'

    melSet = MelSet(
        MelEdid(),
        MelString(b'NNAM', 'rfgp_name'),
        MelFid(b'RNAM', 'rfgp_reference'),
        MelFid(b'PNAM', 'rfgp_packin'),
    )

#------------------------------------------------------------------------------
class _MelSccoXnam(MelStruct):
    """Occurs twice in SCCO (because Bethesda), so deduplicated here."""
    def __init__(self):
        super().__init__(b'XNAM', ['2i'], 'scco_coordinates_x',
            'scco_coordinates_y'),

class MreScco(MelRecord):
    """Scene Collection."""
    rec_sig = b'SCCO'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'QNAM', 'scco_quest'),
        MelGroups('scco_scene_layout',
            MelFid(b'SNAM', 'scco_scene_fid'),
            _MelSccoXnam(),
        ),
        MelBaseR(b'VNAM', 'scco_unknown_vnam1'), # required, marker?
        MelGroups('scco_unknown_array',
            _MelSccoXnam(),
        ),
        MelBaseR(b'VNAM', 'scco_unknown_vnam2'), # required, marker?
    ).with_distributor({
        b'XNAM': 'scco_scene_layout',
        b'VNAM': ('scco_unknown_vnam1', {
            b'VNAM': 'scco_unknown_vnam2',
            b'XNAM': 'scco_unknown_array',
        }),
    })

#------------------------------------------------------------------------------
class MreScol(MelRecord):
    """Static Collection."""
    rec_sig = b'SCOL'

    class HeaderFlags(MelRecord.HeaderFlags):
        non_occluder: bool = flag(4)
        hidden_from_local_map: bool = flag(9)
        scol_loadscreen: bool = flag(10)
        used_as_platform: bool = flag(11)
        has_distant_lod: bool = flag(15)
        obstacle: bool = flag(25)
        navmesh_filter: bool = flag(26)
        navmesh_bounding_box: bool = flag(27)
        navmesh_ground: bool = flag(30)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelPreviewTransform(),
        MelModel(),
        MelFull(),
        MelFilterString(),
        MelSorted(MelScolParts(), sort_by_attrs='scol_part_static'),
    )

#------------------------------------------------------------------------------
class MreScsn(MelRecord):
    """Audio Category Snapshot."""
    rec_sig = b'SCSN'

    melSet = MelSet(
        MelEdid(),
        MelUInt16(b'PNAM', 'scsn_priority'),
        MelGroups('category_multipliers',
            MelStruct(b'CNAM', ['I', 'f'], (FID, 'cm_category'),
                'cm_multiplier'),
        ),
    )

#------------------------------------------------------------------------------
class MreSmbn(MelRecord):
    """Story Manager Branch Node."""
    rec_sig = b'SMBN'

    melSet = MelSet(
        MelSmbnShared(MelConditions()),
    )

#------------------------------------------------------------------------------
class MreSmen(MelRecord):
    """Story Manager Event Node."""
    rec_sig = b'SMEN'

    melSet = MelSet(
        MelSmenShared(MelConditions()),
    )

#------------------------------------------------------------------------------
class MreSmqn(MelRecord):
    """Story Manager Quest Node."""
    rec_sig = b'SMQN'

    melSet = MelSet(
        MelSmqnShared(MelConditions(), with_extra_hours_until_reset=True),
    )

#------------------------------------------------------------------------------
class MreSnct(MelRecord):
    """Sound Category."""
    rec_sig = b'SNCT'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelSnctFlags(),
        MelParent(),
        MelFid(b'ONAM', 'menu_slider_category'),
        MelSnctVnamUnam(),
        MelFloat(b'MNAM', 'min_frequency_multiplier'),
        MelFloat(b'CNAM', 'sidechain_target_multiplier'),
    )

#------------------------------------------------------------------------------
class MreSndr(MelRecord):
    """Sound Descriptor."""
    rec_sig = b'SNDR'

    melSet = MelSet(
        MelEdid(),
        MelString(b'NNAM', 'descriptor_notes'),
        MelSndrType(),
        MelSndrCategory(),
        MelSound(),
        MelSndrSounds(),
        MelSndrOutputModel(),
        MelConditionList(),
        MelSndrLnam(),
        MelUnion({
            # AutoWeapon
            0xED157AE3: MelFid(b'BNAM', 'base_descriptor'),
        }, decider=AttrValDecider('descriptor_type'), fallback=MelSndrBnam()),
        MelSimpleGroups('sndr_descriptors', MelFid(b'DNAM')),
        MelCounter(MelUInt32(b'ITMC', 'rates_of_fire_count'),
            counts='rates_of_fire'),
        MelSorted(MelGroups('rates_of_fire',
            MelBase(b'ITMS', 'rof_marker_start'),
            MelUInt32(b'INTV', 'rof_rpm'),
            MelString(b'FNAM', 'rof_file'),
            MelBase(b'ITME', 'rof_marker_end'), # marker, but not(?) required
        ), sort_by_attrs='rof_rpm'),
    )

#------------------------------------------------------------------------------
class MreSopm(MelRecord):
    """Sound Output Model."""
    rec_sig = b'SOPM'

    melSet = MelSet(
        MelEdid(),
        MelSopmData(),
        MelSopmType(),
        MelSInt16(b'VNAM', 'sopm_static_attenuation'),
        MelSopmOutputValues(),
        # dav = 'Dynamic Attenuation Values'
        MelStruct(b'ATTN', ['4f', '8B'], 'dav_fade_in_distance_start',
            'dav_fade_in_distance_end', 'dav_fade_out_distance_start',
            'dav_fade_out_distance_end', 'dav_fade_in_curve1',
            'dav_fade_in_curve2', 'dav_fade_in_curve3', 'dav_fade_in_curve4',
            'dav_fade_out_curve1', 'dav_fade_out_curve2',
            'dav_fade_out_curve3', 'dav_fade_out_curve4'),
        MelFid(b'ENAM', 'effect_chain'),
    )

#------------------------------------------------------------------------------
class MreSoun(MelRecord):
    """Sound Marker."""
    rec_sig = b'SOUN'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelSounSdsc(),
        MelTruncatedStruct(b'REPT', ['2f', 'B'], 'repeat_min_time',
            'repeat_max_time', 'repeat_stackable', old_versions={'2f'}),
    )

#------------------------------------------------------------------------------
class MreSpel(AMreWithKeywords):
    """Spell."""
    rec_sig = b'SPEL'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelKeywords(),
        MelEquipmentType(),
        MelDescription(),
        MelSpit(),
        MelEffects(),
    )

#------------------------------------------------------------------------------
class MreSpgd(MelRecord):
    """Shader Particle Geometry."""
    rec_sig = b'SPGD'

    melSet = MelSet(
        MelEdid(),
        # What on earth did you do to this struct, Bethesda? It was so nice and
        # normal in Skyrim...
        MelExtra(MelStruct(b'DATA',
            ['f', '4s', 'f', '4s', '3f', '4s', 'f', '4s', 'f', '4s', 'f', '4s',
             'I', '4s', 'I', '4s', 'I', '4s', 'I', '4s', 'f'],
            'gravity_velocity', 'unknown1', 'rotation_velocity', 'unknown2',
            'particle_size_x', 'center_offset_min1', 'particle_size_y',
            'unknown3', 'center_offset_min2', 'unknown4', 'center_offset_max',
            'unknown5', 'initial_rotation', 'unknown6', 'num_subtextures_x',
            'unknown7', 'num_subtextures_y', 'unknown8', 'spgd_type',
            'unknown9', 'spgd_box_size', 'unknown10', 'particle_density'),
            extra_attr='unknown11'),
        MelString(b'MNAM', 'spgd_particle_texture'),
    )

#------------------------------------------------------------------------------
class MreStag(MelRecord):
    """Animation Sound Tag Set."""
    rec_sig = b'STAG'

    melSet = MelSet(
        MelEdid(),
        MelGroups('stag_sounds',
            MelStagTnam(),
        ),
    )

#------------------------------------------------------------------------------
class MreWrld(AMreWrld): ##: Implement once regular records are done
    """Worldspace."""
    ref_types = MreCell.ref_types
    exterior_temp_extra = [b'LAND', b'NAVM']
    wrld_children_extra = [b'CELL'] # CELL for the persistent block

    class HeaderFlags(AMreWrld.HeaderFlags):
        partial_form: bool = flag(14)
