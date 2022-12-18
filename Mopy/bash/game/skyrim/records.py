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
"""This module contains the skyrim record classes."""
from ... import bush
from ...bolt import Flags, TrimmedFlags, flag, sig_to_str
from ...brec import MelRecord, MelGroups, MelStruct, FID, MelAttx, MelRace, \
    MelGroup, MelString, AMreLeveledList, MelSet, MelFid, MelNull, \
    MelOptStruct, MelFids, AMreHeader, MelBase, MelSimpleArray, MelWeight, \
    AMreFlst, MelLString, MelMODS, AMreImad, MelRegions, MelIdleAnimations, \
    MelUnion, AttrValDecider, MelRegnEntrySubrecord, MelIdleTimerSetting, \
    PartialLoadDecider, FlagDecider, MelFloat, MelSInt8, MelSInt32, MelUInt8, \
    MelUInt16, MelUInt32, MelActionFlags, MelCounter, MelRaceData, MelBaseR, \
    MelPartialCounter, MelBounds, null3, null4, MelSequential, MelKeywords, \
    MelTruncatedStruct, MelIcons, MelIcons2, MelIcon, MelIco2, MelEdid, \
    MelFull, MelArray, MelWthrColors, MelFactions, MelReadOnly, MelRelations, \
    AMreActor, AMreWithItems, MelRef3D, MelXlod, MelActiFlags, AMelNvnm, \
    MelWorldBounds, MelEnableParent, MelRefScale, MelMapMarker, MelMdob, \
    MelEnchantment, MelDecalData, MelDescription, MelSInt16, MelSkipInterior, \
    MelSoundPickupDrop, MelActivateParents, BipedFlags, MelColor, \
    MelColorO, MelSpells, MelFixedString, MelUInt8Flags, MelTxstFlags, \
    MelUInt32Flags, MelOwnership, MelClmtWeatherTypes, AMelVmad, MelImgsTint, \
    MelActorSounds, MelFactRanks, MelSorted, MelReflectedRefractedBy, \
    perk_effect_key, MelValueWeight, MelSound, MelWaterType, MelIdlmFlags, \
    MelSoundActivation, MelInteractionKeyword, MelConditionList, MelAddnDnam, \
    MelConditions, ANvnmContext, MelNodeIndex, MelEquipmentType, MelAlchEnit, \
    MelEffects, AMelLLItems, MelUnloadEvent, MelShortName, AVmadContext, \
    MelPerkData, MelNextPerk, PerkEpdfDecider, MelPerkParamsGroups, MelBids, \
    MelArmaShared, MelBamt, MelTemplateArmor, MelArtType, MelGrasData, \
    MelAspcRdat, MelAspcBnam, MelBookText, MelImpactDataset, MelFlstFids, \
    MelBookDescription, MelInventoryArt, MelUnorderedGroups, MelExtra, \
    MelImageSpaceMod, MelClmtTiming, MelClmtTextures, MelCobjOutput, \
    MelSoundClose, AMelItems, MelContData, MelCpthShared, MelDoorFlags, \
    MelRandomTeleports, MelSoundLooping, MelEqupPnam, MelFactVendorInfo, \
    MelFactFlags, MelFactFids, MelSeasons, MelIngredient, MelFurnMarkerData, \
    MelHdptShared, MelIdleEnam, MelIdleRelatedAnims, MelIdleData, \
    perk_distributor, MelImgsCinematic, MelInfoResponsesFo3, MelIngrEnit, \
    MelIpctTextureSets, MelIpctSounds, MelIpctHazard, MelIpdsPnam, \
    MelLandShared, MelLandMpcd, MelIdleAnimationCountOld, MelLighLensFlare, \
    MelIdleAnimationCount, AMreCell, AMreWrld, MelLctnShared, gen_color, \
    MelDalc, gen_ambient_lighting, MelLighFade, MelLscrCameraPath, \
    MelLscrRotation, MelLscrNif, MelLtexGrasses, MelLtexSnam, MelLLFlags, \
    MelLLChanceNone, MelLLGlobal, MelMatoPropertyData, gen_color3, \
    MelMattShared, VWDFlag, NavMeshFlags, NotPlayableFlag

_is_sse = bush.game.fsName in (
    'Skyrim Special Edition', 'Skyrim VR', 'Enderal Special Edition')
def if_sse(le_version, se_version):
    """Resolves to one of two different objects, depending on whether we're
    managing Skyrim LE or SE."""
    return se_version if _is_sse else le_version

def sse_only(sse_obj):
    """Wrapper around if_sse that resolves to None for SLE. Useful for things
    that have been added in SSE as MelSet will ignore None elements. Can also
    be used with Flags, but keep in mind that a None flag will still take up an
    index in the flags list, so it's a good idea to specify flag indices
    explicitly when using it."""
    return if_sse(le_version=None, se_version=sse_obj)

#------------------------------------------------------------------------------
# Record Elements -------------------------------------------------------------
#------------------------------------------------------------------------------
class MelModel(MelGroup):
    """Represents a model subrecord."""
    # MODB and MODD are no longer used by TES5Edit
    typeSets = {
        b'MODL': (b'MODL', b'MODT', b'MODS'),
        b'MOD2': (b'MOD2', b'MO2T', b'MO2S'),
        b'MOD3': (b'MOD3', b'MO3T', b'MO3S'),
        b'MOD4': (b'MOD4', b'MO4T', b'MO4S'),
        b'MOD5': (b'MOD5', b'MO5T', b'MO5S'),
        b'DMDL': (b'DMDL', b'DMDT', b'DMDS'),
    }

    def __init__(self, mel_sig=b'MODL', attr='model'):
        types = self.__class__.typeSets[mel_sig]
        super().__init__(attr,
            MelString(types[0], 'modPath'),
            # Ignore texture hashes - they're only an optimization, plenty
            # of records in Skyrim.esm are missing them
            MelNull(types[1]),
            MelMODS(types[2], 'alternateTextures')
        )

#------------------------------------------------------------------------------
class _MelBodt(MelTruncatedStruct):
    """Handler for BODT subrecords. Upgrades the legacy non-playable flag."""
    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        super().load_mel(record, ins, sub_type, size_, *debug_strs)
        if record._rec_sig == b'ARMO':
            # Carry forward the one usable legacy flag - but don't overwrite
            # the non-playable status if it's already set at the record level
            record.flags1.not_playable |= record.legacy_flags.not_playable

class MelBodtBod2(MelSequential):
    """Handler for BODT and BOD2 subrecords. Reads both types, but writes only
    BOD2."""
    class _bp_flags(BipedFlags):
        head: bool
        hair: bool
        body: bool
        hands: bool
        forearms: bool
        amulet: bool
        ring: bool
        feet: bool
        calves: bool
        shield: bool
        addon_tail: bool
        long_hair: bool
        circlet: bool
        addon_ears: bool
        dragon_head: bool
        dragon_lwing: bool
        dragon_rwing: bool
        dragon_body: bool
        bodyaddon7: bool
        bodyaddon8: bool
        decapitate_head: bool
        decapitate: bool
        bodyaddon9: bool
        bodyaddon10: bool
        bodyaddon11: bool
        bodyaddon12: bool
        bodyaddon13: bool
        bodyaddon14: bool
        bodyaddon15: bool
        bodyaddon16: bool
        bodyaddon17: bool
        fx01: bool

    # Used when loading BODT subrecords - #4 is the only one we care about
    class _legacy_flags(TrimmedFlags):
        modulates_voice: bool = flag(0) # From FO3's ARMA, unused in Skyrim
        not_playable: bool = flag(4) # From ARMO

    def __init__(self):
        ##: armor_type is an enum, see wbArmorTypeEnum in xEdit and its usage
        # in multitweak_names
        super().__init__(
            MelReadOnly(_MelBodt(b'BODT', ['I', 'B', '3s', 'I'],
                (self._bp_flags, 'biped_flags'),
                (self._legacy_flags, 'legacy_flags'), 'bp_unused',
                'armor_type', old_versions={'IB3s'})),
            MelStruct(b'BOD2', ['2I'], (self._bp_flags, 'biped_flags'),
                'armor_type'),
        )

#------------------------------------------------------------------------------
class MelAttacks(MelSorted):
    """Handles the ATKD/ATKE subrecords shared between NPC_ and RACE."""
    class _atk_flags(Flags):
        ignoreWeapon: bool
        bashAttack: bool
        powerAttack: bool
        leftAttack: bool
        rotatingAttack: bool

    def __init__(self):
        super(MelAttacks, self).__init__(MelGroups(u'attacks',
             MelStruct(b'ATKD', [u'2f', u'2I', u'3f', u'I', u'3f'], u'attack_mult', u'attack_chance',
                       (FID, u'attack_spell'),
                       (self._atk_flags, u'attack_data_flags'),
                       u'attack_angle', u'strike_angle', u'attack_stagger',
                       (FID, u'attack_type'), u'attack_knockdown',
                       u'recovery_time', u'stamina_mult'),
             MelString(b'ATKE', u'attack_event'),
        ), sort_by_attrs='attack_chance')

#------------------------------------------------------------------------------
class MelDestructible(MelGroup):
    """Represents a collection of destruction-related subrecords."""
    class _dest_stage_flags(Flags):
        cap_damage: bool
        disable: bool
        destroy: bool
        ignore_external_damage: bool

    def __init__(self):
        super().__init__('destructible',
            MelStruct(b'DEST', ['i', '2B', '2s'], 'health', 'count',
                'vats_targetable', 'dest_unknown'),
            MelGroups('stages',
                MelStruct(b'DSTD', ['4B', 'i', '2I', 'i'], 'health', 'index',
                          'damage_stage',
                          (MelDestructible._dest_stage_flags, 'stage_flags'),
                          'self_damage_per_second', (FID, 'explosion'),
                          (FID, 'debris'), 'debris_count'),
                MelModel(b'DMDL'),
                MelBaseR(b'DSTF', 'dest_end_marker'),
            ),
        )

#------------------------------------------------------------------------------
class MelIdleHandler(MelGroup):
    """Occurs three times in PACK, so moved here to deduplicate the
    definition a bit."""
    # The subrecord type used for the marker
    _attr_lookup = {
        u'on_begin': b'POBA',
        u'on_change': b'POCA',
        u'on_end': b'POEA',
    }

    def __init__(self, attr):
        super(MelIdleHandler, self).__init__(attr,
            MelBase(self._attr_lookup[attr], attr + u'_marker'),
            MelFid(b'INAM', u'idle_anim'),
            *_leftovers,
            MelTopicData(u'idle_topic_data'),
        )

#------------------------------------------------------------------------------
class MelItems(AMelItems):
    """Handles the COCT/CNTO/COED subrecords defining items."""

#------------------------------------------------------------------------------
_leftovers = [MelBase(s, f'unused_{sig_to_str(s).lower()}') for s in
              [b'SCHR', b'SCDA', b'SCTX', b'QNAM', b'SCRO']]
class _MelLeftovers(MelGroup):
    """Leftovers from earlier CK versions."""
    def __init__(self, att):
        super().__init__(att, *_leftovers)

#------------------------------------------------------------------------------
class MelLinkedReferences(MelSorted):
    """The Linked References for a reference record (REFR, ACHR, etc.)."""
    def __init__(self):
        super(MelLinkedReferences, self).__init__(
            MelGroups(u'linked_references',
                MelTruncatedStruct(b'XLKR', ['2I'], (FID, 'keyword_ref'),
                    (FID, 'linked_ref'), old_versions={'I'}),
            ), sort_by_attrs='keyword_ref')

#------------------------------------------------------------------------------
class MelLLItems(AMelLLItems):
    """Handles the LLCT/LVLO/COED subrecords defining leveled list entries."""
    def __init__(self, with_coed=True):
        super().__init__(MelStruct(b'LVLO', ['H', '2s', 'I', 'H', '2s'],
            'level', 'unknown1', (FID, 'listId'), ('count', 1), 'unknown2'),
            with_coed=with_coed)

#------------------------------------------------------------------------------
class MelLocation(MelUnion):
    """A PLDT/PLVD (Location) subrecord. Occurs in PACK and FACT."""
    def __init__(self, sub_sig):
        super().__init__({
            (0, 1, 4, 6): MelOptStruct(sub_sig, ['i', 'I', 'i'],
                'location_type', (FID, 'location_value'), 'location_radius'),
            (2, 3, 7, 10, 11, 12): MelOptStruct(sub_sig, ['i', '4s', 'i'],
                'location_type', 'location_value', 'location_radius'),
            5: MelOptStruct(sub_sig, ['i', 'I', 'i'], 'location_type',
                'location_value', 'location_radius'),
            (8, 9): MelOptStruct(sub_sig, ['3i'], 'location_type',
                'location_value', 'location_radius'),
            }, decider=PartialLoadDecider(
                loader=MelSInt32(sub_sig, 'location_type'),
                decider=AttrValDecider('location_type'))
        )

#------------------------------------------------------------------------------
class MelNvnm(AMelNvnm):
    """Handles the NVNM (Navmesh Geometry) subrecord."""
    class _NvnmContextTes5(ANvnmContext):
        """Provides NVNM context for Skyrim."""
        max_nvnm_ver = 12
        cover_tri_mapping_has_covers = False
        nvnm_has_waypoints = False

    _nvnm_context_class = _NvnmContextTes5

#------------------------------------------------------------------------------
class MelSMFlags(MelStruct):
    """Handles Story Manager flags shared by SMBN, SMQN and SMEN."""
    class _node_flags(Flags):
        sm_random: bool
        no_child_warn: bool

    class _quest_flags(Flags):
        do_all_before_repeating: bool
        shares_event: bool
        num_quests_to_run: bool

    def __init__(self, with_quest_flags=False):
        sm_fmt = [u'I']
        sm_elements = [(self._node_flags, u'node_flags')]
        if with_quest_flags:
            sm_fmt = [u'2H']
            sm_elements.append((self._quest_flags, u'quest_flags'))
        super(MelSMFlags, self).__init__(b'DNAM', sm_fmt, *sm_elements)

#------------------------------------------------------------------------------
class MelSpellCounter(MelCounter):
    """Handles the SPCT (Spell Counter) subrecord. To be used in combination
    with MelSpells."""
    def __init__(self):
        super().__init__(MelUInt32(b'SPCT', 'spell_count'), counts='spells')

#------------------------------------------------------------------------------
class MelSpit(MelStruct):
    """Handles the SPIT subrecord shared between SCRL and SPEL."""
    class spit_flags(Flags):
        manualCostCalc: bool = flag(0)
        pcStartSpell: bool = flag(17)
        areaEffectIgnoresLOS: bool = flag(19)
        ignoreResistance: bool = flag(20)
        noAbsorbReflect: bool = flag(21)
        noDualCastModification: bool = flag(23)

    def __init__(self):
        super().__init__(b'SPIT', ['3I', 'f', '2I', '2f', 'I'], 'cost',
            (self.spit_flags, 'dataFlags'), 'spellType', 'charge_time',
            'cast_type', 'spell_target_type', 'castDuration', 'range',
            (FID, 'halfCostPerk'))

#------------------------------------------------------------------------------
class MelTopicData(MelGroups):
    """Occurs twice in PACK, so moved here to deduplicate the definition a
    bit. Can't be placed inside MrePack, since one of its own subclasses
    depends on this."""
    def __init__(self, attr):
        MelGroups.__init__(self, attr,
            MelUnion({
                0: MelStruct(b'PDTO', ['2I'], 'data_type', (FID, 'topic_ref')),
                1: MelStruct(b'PDTO', ['I', '4s'], 'data_type',
                             'topic_subtype'),
            }, decider=PartialLoadDecider(
                loader=MelUInt32(b'PDTO', 'data_type'),
                decider=AttrValDecider('data_type'))),
        )

#------------------------------------------------------------------------------
class MelVmad(AMelVmad):
    """Handles the VMAD (Virtual Machine Adapter) subrecord."""
    class _VmadContextTes5(AVmadContext):
        """Provides VMAD context for Skyrim."""
        max_vmad_ver = 5

    _vmad_context_class = _VmadContextTes5

#------------------------------------------------------------------------------
class MelWaterVelocities(MelSequential):
    """Handles the XWCU/XWCS/XWCN subrecords shared by REFR and CELL."""
    def __init__(self):
        super(MelWaterVelocities, self).__init__(
            # Old version of XWCN - replace with XWCN upon dumping
            MelReadOnly(MelUInt32(b'XWCS', u'water_velocities_count')),
            MelCounter(MelUInt32(b'XWCN', u'water_velocities_count'),
                       counts=u'water_velocities'),
            MelArray(u'water_velocities',
                MelStruct(b'XWCU', [u'4f'], u'x_offset', u'y_offset',
                    u'z_offset', u'unknown1'),
            ),
        )

#------------------------------------------------------------------------------
# Skyrim Records --------------------------------------------------------------
#------------------------------------------------------------------------------
class MreTes4(AMreHeader):
    """TES4 Record.  File header."""
    rec_sig = b'TES4'
    _post_masters_sigs = {b'SCRN', b'INTV', b'INCC', b'ONAM'}

    class HeaderFlags(AMreHeader.HeaderFlags):
        localized: bool = flag(7)
        esl_flag: bool = flag(sse_only(9))

    melSet = MelSet(
        MelStruct(b'HEDR', [u'f', u'2I'], ('version', 1.7), 'numRecords',
                  ('nextObject', 0x800)),
        MelNull(b'OFST'), # obsolete
        MelNull(b'DELE'), # obsolete
        AMreHeader.MelAuthor(),
        AMreHeader.MelDescription(),
        AMreHeader.MelMasterNames(),
        MelSimpleArray('overrides', MelFid(b'ONAM')),
        MelBase(b'SCRN', 'screenshot'),
        MelBase(b'INTV', 'unknownINTV'),
        MelBase(b'INCC', 'unknownINCC'),
    )

#------------------------------------------------------------------------------
class MreAact(MelRecord):
    """Action."""
    rec_sig = b'AACT'

    melSet = MelSet(
        MelEdid(),
        MelColorO(),
    )

#------------------------------------------------------------------------------
class MreAchr(MelRecord):
    """Placed NPC."""
    rec_sig = b'ACHR'

    class HeaderFlags(MelRecord.HeaderFlags):
        starts_dead: bool = flag(9)
        persistent: bool = flag(10)
        initially_disabled: bool = flag(11)
        no_ai_acquire: bool = flag(25)
        dont_havok_settle: bool = flag(29)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelFid(b'NAME', u'ref_base'),
        MelFid(b'XEZN', u'encounter_zone'),
        MelBase(b'XRGD', u'ragdoll_data'),
        MelBase(b'XRGB', u'ragdoll_biped_data'),
        MelFloat(b'XPRD', u'idle_time'),
        MelBase(b'XPPA', u'patrol_script_marker'),
        MelFid(b'INAM', u'ref_idle'),
        *_leftovers,
        MelTopicData(u'topic_data'),
        MelFid(b'TNAM', u'ref_topic'),
        MelSInt32(b'XLCM', u'level_modifier'),
        MelFid(b'XMRC', u'merchant_container'),
        MelSInt32(b'XCNT', u'ref_count'),
        MelFloat(b'XRDS', u'ref_radius'),
        MelFloat(b'XHLP', u'ref_health'),
        MelLinkedReferences(),
        MelActivateParents(),
        MelStruct(b'XCLP', ['3B', 's', '3B', 's'], *gen_color('start_color'),
            *gen_color('end_color')),
        MelFid(b'XLCN', u'persistent_location'),
        MelFid(b'XLRL', u'location_reference'),
        MelBase(b'XIS2', u'ignored_by_sandbox_2'),
        MelArray(u'location_ref_type',
            MelFid(b'XLRT', u'location_ref')
        ),
        MelFid(b'XHOR', u'ref_horse'),
        MelFloat(b'XHTW', u'head_tracking_weight'),
        MelFloat(b'XFVC', u'favor_cost'),
        MelEnableParent(),
        MelOwnership(),
        MelFid(b'XEMI', u'ref_emittance'),
        MelFid(b'XMBR', u'multi_bound_reference'),
        MelBase(b'XIBS', u'ignored_by_sandbox_1'),
        MelRefScale(),
        MelRef3D(),
    )

#------------------------------------------------------------------------------
class MreActi(MelRecord):
    """Activator."""
    rec_sig = b'ACTI'

    class HeaderFlags(NavMeshFlags, VWDFlag, MelRecord.HeaderFlags):
        has_tree_lod: bool = flag(6)
        must_update_anims: bool = flag(8)
        hide_from_local_map: bool = flag(9)
        random_animation_start: bool = flag(16)
        dangerous: bool = flag(17)
        ignore_object_interaction: bool = flag(20)
        is_marker: bool = flag(23)
        obstacle: bool = flag(25)
        child_can_use: bool = flag(29)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelColor(b'PNAM'),
        MelSound(),
        MelSoundActivation(),
        MelWaterType(),
        MelAttx(b'RNAM'),
        MelActiFlags(),
        MelInteractionKeyword(),
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
        MelAddnDnam(),
    )

#------------------------------------------------------------------------------
class MreAlch(MelRecord):
    """Ingestible."""
    rec_sig = b'ALCH'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelKeywords(),
        MelDescription(),
        MelModel(),
        MelDestructible(),
        MelIcons(),
        MelSoundPickupDrop(),
        MelEquipmentType(),
        MelWeight(),
        MelAlchEnit(),
        MelEffects(),
    )

#------------------------------------------------------------------------------
class MreAmmo(MelRecord):
    """Ammunition."""
    rec_sig = b'AMMO'

    class HeaderFlags(NotPlayableFlag, MelRecord.HeaderFlags):
        pass

    class AmmoTypeFlags(Flags):
        notNormalWeapon: bool
        nonPlayable: bool
        nonBolt: bool

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelSoundPickupDrop(),
        MelDescription(),
        MelKeywords(),
        if_sse(
            le_version=MelStruct(b'DATA', [u'I', u'I', u'f', u'I'], (FID, 'projectile'),
                                 (AmmoTypeFlags, 'flags'), 'damage', 'value'),
            se_version=MelTruncatedStruct(b'DATA', [u'2I', u'f', u'I', u'f'],
                (FID, 'projectile'), (AmmoTypeFlags, 'flags'),
                'damage', 'value', 'weight', old_versions={'2IfI'}),
        ),
        # Skyrim has strings but this one isn't localized, so we can't use
        # MelShortName here unfortunately
        MelString(b'ONAM', 'short_name'),
    )

#------------------------------------------------------------------------------
class MreAnio(MelRecord):
    """Animated Object."""
    rec_sig = b'ANIO'

    class HeaderFlags(MelRecord.HeaderFlags):
        unknown_9: bool = flag(9) # Present in updated records, not Skyrim.esm

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelUnloadEvent(),
    )

#------------------------------------------------------------------------------
class MreAppa(MelRecord):
    """Alchemical Apparatus."""
    rec_sig = b'APPA'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelSoundPickupDrop(),
        MelUInt32(b'QUAL', 'quality'),
        MelDescription(),
        MelValueWeight(),
    )

#------------------------------------------------------------------------------
class MreArma(MelRecord):
    """Armor Addon."""
    rec_sig = b'ARMA'

    melSet = MelSet(
        MelEdid(),
        MelBodtBod2(),
        MelRace(),
        MelArmaShared(MelModel),
    )

#------------------------------------------------------------------------------
class MreArmo(MelRecord):
    """Armor."""
    rec_sig = b'ARMO'

    class HeaderFlags(NotPlayableFlag, MelRecord.HeaderFlags):
        shield: bool = flag(6)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelEnchantment(),
        MelSInt16(b'EAMT', 'enchantment_amount'),
        MelModel(b'MOD2', 'maleWorld'),
        MelIcons('maleIconPath', 'maleSmallIconPath'),
        MelModel(b'MOD4', 'femaleWorld'),
        MelIcons2(),
        MelBodtBod2(),
        MelDestructible(),
        MelSoundPickupDrop(),
        MelString(b'BMCT', 'ragdollTemplatePath'), #Ragdoll Constraint Template
        MelEquipmentType(),
        MelBids(),
        MelBamt(),
        MelRace(),
        MelKeywords(),
        MelDescription(),
        MelFids('addons', MelFid(b'MODL')),
        MelValueWeight(),
        MelSInt32(b'DNAM', 'armorRating'),
        MelTemplateArmor(),
    )

#------------------------------------------------------------------------------
class MreArto(MelRecord):
    """Art Object."""
    rec_sig = b'ARTO'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
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
    )

#------------------------------------------------------------------------------
class MreAvif(MelRecord):
    """Actor Value Information."""
    rec_sig = b'AVIF'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelString(b'ANAM', 'abbreviation'),
        MelBase(b'CNAM', 'unknown_cnam'),
        MelOptStruct(b'AVSK', ['4f'], 'skill_use_mult', 'skill_offset_mult',
            'skill_improve_mult', 'skill_improve_offset'),
        MelGroups('perk_tree',
            MelFid(b'PNAM', 'perk_fid'),
            MelBase(b'FNAM', 'unknown_fnam'),
            MelUInt32(b'XNAM', 'perk_grid_x'),
            MelUInt32(b'YNAM', 'perk_grid_y'),
            MelFloat(b'HNAM', 'perk_horizontal_position'),
            MelFloat(b'VNAM', 'perk_vertical_position'),
            MelFid(b'SNAM', 'associated_skill'),
            MelGroups('perk_connections',
                MelUInt32(b'CNAM', 'line_to_index'),
            ),
            MelUInt32(b'INAM', 'perk_index'),
        ),
    ).with_distributor({
        b'CNAM': 'unknown_cnam',
        b'PNAM': {
            b'CNAM': 'perk_tree',
        },
    })

#------------------------------------------------------------------------------
class MreBook(MelRecord):
    """Book."""
    rec_sig = b'BOOK'

    class _book_type_flags(Flags):
        teaches_skill: bool
        cant_be_taken: bool
        teaches_spell: bool

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelBookText(),
        MelDestructible(),
        MelSoundPickupDrop(),
        MelKeywords(),
        MelUnion({
            False: MelStruct(b'DATA', ['2B', '2s', 'i', 'I', 'f'],
                (_book_type_flags, 'book_flags'), 'book_type',
                'unused1', 'book_skill', 'value', 'weight'),
            True: MelStruct(b'DATA', ['2B', '2s', '2I', 'f'],
                (_book_type_flags, 'book_flags'), 'book_type',
                'unused1', (FID, 'book_spell'), 'value',
                'weight'),
        }, decider=PartialLoadDecider(
            loader=MelUInt8Flags(b'DATA', 'book_flags', _book_type_flags),
            decider=FlagDecider('book_flags', ['teaches_spell']),
        )),
        MelInventoryArt(),
        MelBookDescription(),
    )

#------------------------------------------------------------------------------
class MreBptd(MelRecord):
    """Body Part Data."""
    rec_sig = b'BPTD'

    class _bpnd_flags(Flags):
        severable: bool
        ik_data: bool
        ik_biped_data: bool
        explodable: bool
        ik_is_head: bool
        ik_headtracking: bool
        to_hit_chance_absolute: bool

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelSorted(MelUnorderedGroups('body_part_list',
            MelLString(b'BPTN', 'part_name'),
            MelString(b'PNAM', 'pose_matching'),
            MelString(b'BPNN', 'part_node'),
            MelString(b'BPNT', 'vats_target'),
            MelString(b'BPNI', 'ik_data_start_node'),
            MelStruct(b'BPND',
                ['f', '3B', 'b', '2B', 'H', '2I', '2f', 'i', '2I', '7f', '2I',
                 '2B', '2s', 'f'], 'bpnd_damage_mult',
                (_bpnd_flags, 'bpnd_flags'), 'bpnd_part_type',
                'bpnd_health_percent', 'bpnd_actor_value',
                'bpnd_to_hit_chance', 'bpnd_explodable_chance_percent',
                'bpnd_explodable_debris_count',
                (FID, 'bpnd_explodable_debris'),
                (FID, 'bpnd_explodable_explosion'), 'bpnd_tracking_max_angle',
                'bpnd_explodable_debris_scale', 'bpnd_severable_debris_count',
                (FID, 'bpnd_severable_debris'),
                (FID, 'bpnd_severable_explosion'),
                'bpnd_severable_debris_scale', 'bpnd_gore_effect_pos_trans_x',
                'bpnd_gore_effect_pos_trans_y', 'bpnd_gore_effect_pos_trans_z',
                'bpnd_gore_effect_pos_rot_x', 'bpnd_gore_effect_pos_rot_y',
                'bpnd_gore_effect_pos_rot_z',
                (FID, 'bpnd_severable_impact_dataset'),
                (FID, 'bpnd_explodable_impact_dataset'),
                'bpnd_severable_decal_count', 'bpnd_explodable_decal_count',
                'bpnd_unused', 'bpnd_limb_replacement_scale'),
            MelString(b'NAM1', 'limb_replacement_model'),
            MelString(b'NAM4', 'gore_effects_target_bone'),
            # Ignore texture hashes - they're only an optimization, plenty of
            # records in Skyrim.esm are missing them
            MelNull(b'NAM5'),
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

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelTruncatedStruct(b'DATA', ['4I', '7f'], 'cams_action',
            'cams_location', 'cams_target', (_cams_flags, 'cams_flags'),
            'time_mult_player', 'time_mult_target', 'time_mult_global',
            'cams_max_time', 'cams_min_time', 'target_pct_between_actors',
            'near_target_distance', old_versions={'4I6f'}),
        MelImageSpaceMod(),
    )

#------------------------------------------------------------------------------
class MreCell(AMreCell):
    """Cell."""
    ref_types = {b'ACHR', b'PARW', b'PBAR', b'PBEA', b'PCON', b'PFLA', b'PGRE',
                 b'PHZD', b'PMIS', b'REFR'}
    interior_temp_extra = [b'NAVM']
    _has_duplicate_attrs = True # XWCS is an older version of XWCN

    class CellDataFlags1(Flags):
        isInterior: bool = flag(0)
        hasWater: bool = flag(1)
        cantFastTravel: bool = flag(2)
        noLODWater: bool = flag(3)
        publicPlace: bool = flag(5)
        handChanged: bool = flag(6)
        showSky: bool = flag(7)

    class CellDataFlags2(Flags):
        useSkyLighting: bool

    class CellInheritedFlags(Flags):
        ambientColor: bool = flag(0)
        directionalColor: bool = flag(1)
        fogColor: bool = flag(2)
        fogNear: bool = flag(3)
        fogFar: bool = flag(4)
        directionalRotation: bool = flag(5)
        directionalFade: bool = flag(6)
        clipDistance: bool = flag(7)
        fogPower: bool = flag(8)
        fogMax: bool = flag(9)
        lightFadeDistances: bool = flag(10)

    class _cell_land_flags(TrimmedFlags):
        hide_quad1: bool
        hide_quad2: bool
        hide_quad3: bool
        hide_quad4: bool

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelTruncatedStruct(b'DATA', [u'2B'], (CellDataFlags1, u'flags'),
                           (CellDataFlags2, u'skyFlags'),
                           old_versions={'B'}),
        ##: The other games skip this in interiors - why / why not here?
        # None defaults here are on purpose - XCLC does not necessarily exist,
        # but 0 is a valid value for both coordinates (duh)
        MelOptStruct(b'XCLC', ['2i', 'I'], ('posX', None), ('posY', None),
            (_cell_land_flags, 'cell_land_flags')),
        MelTruncatedStruct(b'XCLL',
            [u'3B', u's', u'3B', u's', u'3B', u's', u'2f', u'2i', u'3f', u'3B',
             u's', u'3B', u's', u'3B', u's', u'3B', u's', u'3B', u's', u'3B',
             u's', u'3B', u's', u'f', u'3B', u's', u'3f', u'I'],
            'ambientRed', 'ambientGreen', 'ambientBlue', 'unused1',
            'directionalRed', 'directionalGreen', 'directionalBlue',
            'unused2', 'fogRed', 'fogGreen', 'fogBlue',
            'unused3', 'fogNear', 'fogFar', 'directionalXY',
            'directionalZ', 'directionalFade', 'fogClip', 'fogPower',
            'redXplus', 'greenXplus', 'blueXplus', 'unknownXplus',
            'redXminus', 'greenXminus', 'blueXminus', 'unknownXminus',
            'redYplus', 'greenYplus', 'blueYplus', 'unknownYplus',
            'redYminus', 'greenYminus', 'blueYminus', 'unknownYminus',
            'redZplus', 'greenZplus', 'blueZplus', 'unknownZplus',
            'redZminus', 'greenZminus', 'blueZminus', 'unknownZminus',
            'redSpec', 'greenSpec', 'blueSpec', 'unknownSpec',
            'fresnelPower', 'fogColorFarRed', 'fogColorFarGreen',
            'fogColorFarBlue', 'unused4', 'fogMax', 'lightFadeBegin',
            'lightFadeEnd', (CellInheritedFlags, u'inherits'),
            is_optional=True, old_versions={
                '3Bs3Bs3Bs2f2i3f3Bs3Bs3Bs3Bs3Bs3Bs', '3Bs3Bs3Bs2fi'}),
        MelBase(b'TVDT','occlusionData'),
        # Decoded in xEdit, but properly reading it is relatively slow - see
        # 'Simple Records' option in xEdit - so we skip that for now
        MelBase(b'MHDT','maxHeightData'),
        MelFid(b'LTMP','lightTemplate',),
        # leftover flags, they are now in XCLC
        MelBase(b'LNAM','unknown_LNAM'),
        # Drop in interior cells for Skyrim, see #302 for discussion on this
        MelSkipInterior(MelFloat(b'XCLW', u'waterHeight')),
        MelString(b'XNAM','waterNoiseTexture'),
        MelRegions(),
        MelFid(b'XLCN','location',),
        MelWaterVelocities(),
        MelFid(b'XCWT','water'),
        MelOwnership(),
        MelFid(b'XILL','lockList',),
        MelString(b'XWEM','waterEnvironmentMap'),
        MelFid(b'XCCM','climate',), # xEdit calls this 'Sky/Weather From Region'
        MelFid(b'XCAS','acousticSpace',),
        MelFid(b'XEZN','encounterZone',),
        MelFid(b'XCMO','music',),
        MelFid(b'XCIM','imageSpace',),
    )

#------------------------------------------------------------------------------
class MreClas(MelRecord):
    """Class."""
    rec_sig = b'CLAS'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelIcons(),
        MelStruct(b'DATA', [u'4s', u'b', u'19B', u'f', u'I', u'4B'],'unknown',
                  'teaches','maximumtraininglevel',
                  'skillWeightsOneHanded','skillWeightsTwoHanded',
                  'skillWeightsArchery','skillWeightsBlock',
                  'skillWeightsSmithing','skillWeightsHeavyArmor',
                  'skillWeightsLightArmor','skillWeightsPickpocket',
                  'skillWeightsLockpicking','skillWeightsSneak',
                  'skillWeightsAlchemy','skillWeightsSpeech',
                  'skillWeightsAlteration','skillWeightsConjuration',
                  'skillWeightsDestruction','skillWeightsIllusion',
                  'skillWeightsRestoration','skillWeightsEnchanting',
                  'bleedoutDefault','voicePoints',
                  'attributeWeightsHealth','attributeWeightsMagicka',
                  'attributeWeightsStamina','attributeWeightsUnknown',),
    )

#------------------------------------------------------------------------------
class MreClfm(MelRecord):
    """Color."""
    rec_sig = b'CLFM'

    class HeaderFlags(NotPlayableFlag, MelRecord.HeaderFlags):
        pass

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelColorO(),
        MelUInt32(b'FNAM', 'playable'), # actually a bool, stored as uint32
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
class MreCobj(AMreWithItems):
    """Constructible Object."""
    rec_sig = b'COBJ'
    isKeyedByEid = True # NULL fids are acceptable

    melSet = MelSet(
        MelEdid(),
        MelItems(),
        MelConditionList(),
        MelCobjOutput(),
        MelUInt16(b'NAM1', 'created_object_count'),
    )

#------------------------------------------------------------------------------
class MreCont(AMreWithItems):
    """Container."""
    rec_sig = b'CONT'

    class HeaderFlags(VWDFlag, NavMeshFlags, AMreWithItems.HeaderFlags):
        random_animation_start: bool = flag(16)
        obstacle: bool = flag(26)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelItems(),
        MelDestructible(),
        MelContData(),
        MelSound(),
        MelSoundClose(),
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

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'CSGD', ['10f'], 'general_offensive_mult',
            'general_defensive_mult', 'general_group_offensive_mult',
            'general_equipment_score_mult_melee',
            'general_equipment_score_mult_magic',
            'general_equipment_score_mult_ranged',
            'general_equipment_score_mult_shout',
            'general_equipment_score_mult_unarmed',
            'general_equipment_score_mult_staff',
            'general_avoid_threat_chance'),
        MelBase(b'CSMD', 'unknown1'),
        MelTruncatedStruct(b'CSME', ['8f'], 'melee_attack_staggered_mult',
            'melee_power_attack_staggered_mult',
            'melee_power_attack_blocking_mult',
            'melee_bash_mult', 'melee_bash_recoil_mult',
            'melee_bash_attack_mult', 'melee_bash_power_attack_mult',
            'melee_special_attack_mult', old_versions={'7f'}),
        MelStruct(b'CSCR', ['4f'], 'close_range_circle_mult',
            'close_range_fallback_mult', 'close_range_flank_distance',
            'close_range_stalk_time'),
        MelFloat(b'CSLR', 'long_range_strafe_mult'),
        MelTruncatedStruct(b'CSFL', ['8f'], 'flight_hover_chance',
            'flight_dive_bomb_chance', 'flight_ground_attack_chance',
            'flight_hover_time', 'flight_ground_attack_time',
            'flight_perch_attack_chance', 'flight_perch_attack_time',
            'flight_flying_attack_chance', old_versions={'5f'}),
        MelUInt32Flags(b'DATA', 'csty_flags', _csty_flags),
    )

#------------------------------------------------------------------------------
class MreDial(MelRecord):
    """Dialogue."""
    rec_sig = b'DIAL'

    class DialTopicFlags(Flags):
        doAllBeforeRepeating: bool

    @classmethod
    def nested_records_sigs(cls):
        return {b'INFO'}

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelFloat(b'PNAM', 'priority',),
        MelFid(b'BNAM','branch',),
        MelFid(b'QNAM','quest',),
        MelStruct(b'DATA', ['2B', 'H'], (DialTopicFlags, 'flags_dt'),
                  'category', 'subtype'),
        MelFixedString(b'SNAM', 'subtypeName', 4),
        MelUInt32(b'TIFC', u'info_count'), # Updated in MobDial.dump
    )

#------------------------------------------------------------------------------
class MreDobj(MelRecord):
    """Default Object Manager."""
    rec_sig = b'DOBJ'

    melSet = MelSet(
        MelEdid(),
        # This subrecord can have <=7 bytes of noise at the end
        MelExtra(MelSorted(MelArray('default_objects',
            MelStruct(b'DNAM', ['2I'], 'default_object_use',
                (FID, 'default_object_fid')),
        ), sort_by_attrs='default_object_use'), extra_attr='unknown_dnam'),
    )

#------------------------------------------------------------------------------
class MreDoor(MelRecord):
    """Door."""
    rec_sig = b'DOOR'

    class HeaderFlags(VWDFlag, MelRecord.HeaderFlags):
        random_animation_start: bool = flag(16)
        is_marker: bool = flag(23)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelSound(),
        MelSoundClose(b'ANAM'),
        MelSoundLooping(),
        MelDoorFlags(),
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

    melSet = MelSet(
        MelEdid(),
        MelTruncatedStruct(b'DATA', ['2I', '2b', 'B', 'b'],
            (FID, 'eczn_owner'), (FID, 'eczn_location'), 'eczn_rank',
            'eczn_minimum_level', (_eczn_flags, 'eczn_flags'),
            'eczn_max_level', old_versions={'2I'}),
    )

#------------------------------------------------------------------------------
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
        MelTruncatedStruct(b'DATA',
            ['4s', '3I', '3B', 's', '9f', '3B', 's', '8f', '5I', '19f', '3B',
             's', '3B', 's', '3B', 's', '11f', 'I', '5f', '3B', 's', 'f', '2I',
             '6f', 'I', '3B', 's', '3B', 's', '9f', '8I', '2f', '4s'],
            'unknown1', 'ms_source_blend_mode', 'ms_blend_operation',
            'ms_z_test_function', *gen_color('fill_color1'),
            'fill_alpha_fade_in_time', 'fill_full_alpha_time',
            'fill_alpha_fade_out_time', 'fill_persistent_alpha_ratio',
            'fill_alpha_pulse_amplitude', 'fill_alpha_pulse_frequency',
            'fill_texture_animation_speed_u', 'fill_texture_animation_speed_v',
            'ee_fall_off', *gen_color('ee_color'), 'ee_alpha_fade_in_time',
            'ee_full_alpha_time', 'ee_alpha_fade_out_time',
            'ee_persistent_alpha_ratio', 'ee_alpha_pulse_amplitude',
            'ee_alpha_pulse_frequency', 'fill_full_alpha_ratio',
            'ee_full_alpha_ratio', 'ms_dest_blend_mode',
            'ps_source_blend_mode', 'ps_blend_operation', 'ps_z_test_function',
            'ps_dest_blend_mode', 'ps_particle_birth_ramp_up_time',
            'ps_full_particle_birth_time', 'ps_particle_birth_ramp_down_time',
            'ps_full_particle_birth_ratio', 'ps_persistent_particle_count',
            'ps_particle_lifetime', 'ps_particle_lifetime_delta',
            'ps_initial_speed_along_normal', 'ps_acceleration_along_normal',
            'ps_initial_velocity1', 'ps_initial_velocity2',
            'ps_initial_velocity3', 'ps_acceleration1', 'ps_acceleration2',
            'ps_acceleration3', 'ps_scale_key1', 'ps_scale_key2',
            'ps_scale_key1_time', 'ps_scale_key2_time',
            *gen_color('color_key1'), *gen_color('color_key2'),
            *gen_color('color_key3'), 'color_key1_alpha', 'color_key2_alpha',
            'color_key3_alpha', 'color_key1_time', 'color_key2_time',
            'color_key3_time', 'ps_initial_speed_along_normal_delta',
            'ps_initial_rotation', 'ps_initial_rotation_delta',
            'ps_rotation_speed', 'ps_rotation_speed_delta',
            (FID, 'addon_models'), 'holes_start_time', 'holes_end_time',
            'holes_start_value', 'holes_end_value', 'ee_width',
            *gen_color('edge_color'), 'explosion_wind_speed',
            'texture_count_u', 'texture_count_v', 'addon_models_fade_in_time',
            'addon_models_fade_out_time', 'addon_models_scale_start',
            'addon_models_scale_end', 'addon_models_scale_in_time',
            'addon_models_scale_out_time', (FID, 'sound_ambient'),
            *gen_color('fill_color2'), *gen_color('fill_color3'),
            'fill_color1_scale', 'fill_color2_scale', 'fill_color3_scale',
            'fill_color1_time', 'fill_color2_time', 'fill_color3_time',
            'color_scale', 'birth_position_offset',
            'birth_position_offset_range_delta', 'psa_start_frame',
            'psa_start_frame_variation', 'psa_end_frame',
            'psa_loop_start_frame', 'psa_loop_start_variation',
            'psa_frame_count', 'psa_frame_count_variation',
            (_efsh_flags, 'efsh_flags'), 'fill_texture_scale_u',
            'fill_texture_scale_v', 'unused9', old_versions={
                '4s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I6fI3Bs3Bs9f8I2f',
                '4s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I6fI3Bs3Bs6f',
                '4s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I6fI',
                '4s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I6f',
            }),
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
        MelTruncatedStruct(b'ENIT', ['i', '2I', 'i', '2I', 'f', '2I'],
            'enchantment_cost', (_enit_flags, 'enit_flags'), 'cast_type',
            'enchantment_amount', 'enchantment_target_type',
            'enchantment_type', 'charge_time', (FID, 'base_enchantment'),
            (FID, 'worn_restrictions'), old_versions={'i2Ii2IfI'}),
        MelEffects(),
    )

#------------------------------------------------------------------------------
class MreEqup(MelRecord):
    """Equip Type."""
    rec_sig = b'EQUP'

    melSet = MelSet(
        MelEdid(),
        MelEqupPnam(),
        MelUInt32(b'DATA', 'use_all_parents'), # actually a bool
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

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelEnchantment(),
        MelImageSpaceMod(),
        MelTruncatedStruct(b'DATA', ['6I', '5f', '2I'], (FID, 'expl_light'),
            (FID, 'expl_sound1'), (FID, 'expl_sound2'),
            (FID, 'expl_impact_dataset'), (FID, 'placed_object'),
            (FID, 'spawn_projectile'), 'expl_force', 'expl_damage',
            'expl_radius', 'is_radius', 'vertical_offset_mult',
            (_expl_flags, 'expl_flags'), 'expl_sound_level',
            old_versions={'6I5fI', '6I5f', '6I4f'}),
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
        MelTruncatedStruct(b'CRVA', ['2B', '5H', 'f', '2H'], 'cv_arrest',
            'cv_attack_on_sight', 'cv_murder', 'cv_assault', 'cv_trespass',
            'cv_pickpocket', 'cv_unknown', 'cv_steal_multiplier', 'cv_escape',
            'cv_werewolf', old_versions={'2B5Hf', '2B5H'}),
        MelFactRanks(),
        MelFactVendorInfo(),
        MelLocation(b'PLVD'),
        MelConditions(),
    )

#------------------------------------------------------------------------------
class MreFlor(MelRecord):
    """Flora."""
    rec_sig = b'FLOR'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelColor(b'PNAM'),
        MelAttx(b'RNAM'),
        MelActiFlags(),
        MelIngredient(),
        MelSound(),
        MelSeasons(),
    )

#------------------------------------------------------------------------------
class MreFlst(AMreFlst):
    """FormID List."""
    melSet = MelSet(
        MelEdid(),
        MelFlstFids(),
    )

#------------------------------------------------------------------------------
class MreFurn(MelRecord):
    """Furniture."""
    rec_sig = b'FURN'

    class HeaderFlags(VWDFlag, MelRecord.HeaderFlags):
        is_perch: bool = flag(7)
        random_animation_start: bool = flag(16)
        is_marker: bool = flag(23)
        must_exit_to_talk: bool = flag(28)
        child_can_use: bool = flag(29)

    class _active_markers_flags(Flags):
        sit_0: bool = flag(0)
        sit_1: bool = flag(1)
        sit_2: bool = flag(2)
        sit_3: bool = flag(3)
        sit_4: bool = flag(4)
        sit_5: bool = flag(5)
        sit_6: bool = flag(6)
        sit_7: bool = flag(7)
        sit_8: bool = flag(8)
        sit_9: bool = flag(9)
        sit_10: bool = flag(10)
        sit_11: bool = flag(11)
        sit_12: bool = flag(12)
        sit_13: bool = flag(13)
        sit_14: bool = flag(14)
        sit_15: bool = flag(15)
        sit_16: bool = flag(16)
        sit_17: bool = flag(17)
        sit_18: bool = flag(18)
        sit_19: bool = flag(19)
        sit_20: bool = flag(20)
        sit_21: bool = flag(21)
        sit_22: bool = flag(22)
        sit_23: bool = flag(23)
        disables_activation: bool = flag(25)
        is_perch: bool = flag(26)
        must_exit_to_talk: bool = flag(27)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelColor(b'PNAM'),
        MelActiFlags(),
        MelInteractionKeyword(),
        MelUInt32Flags(b'MNAM', 'active_markers_flags', _active_markers_flags),
        MelStruct(b'WBDT', ['B', 'b'], 'bench_type', 'uses_skill'),
        MelFid(b'NAM1', 'associated_spell'),
        MelFurnMarkerData(with_marker_keyword=True),
    )

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

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelImageSpaceMod(),
        MelStruct(b'DATA', ['I', '4f', '5I'], 'hazd_limit', 'hazd_radius',
            'hazd_lifetime', 'image_space_radius', 'target_interval',
            (_hazd_flags, 'hazd_flags'), (FID, 'hazd_spell'),
            (FID, 'hazd_light'), (FID, 'hazd_impact_dataset'),
            (FID, 'hazd_sound')),
    )

#------------------------------------------------------------------------------
class MreHdpt(MelRecord):
    """Head Part."""
    rec_sig = b'HDPT'

    class HeaderFlags(NotPlayableFlag, MelRecord.HeaderFlags):
        pass

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelHdptShared(),
    )

#------------------------------------------------------------------------------
class MreIdle(MelRecord):
    """Idle Animation."""
    rec_sig = b'IDLE'

    melSet = MelSet(
        MelEdid(),
        MelConditionList(),
        MelString(b'DNAM', 'idle_filename'),
        MelIdleEnam(),
        MelIdleRelatedAnims(),
        MelIdleData(),
    )

#------------------------------------------------------------------------------
class MreIdlm(MelRecord):
    """Idle Marker."""
    rec_sig = b'IDLM'

    class HeaderFlags(MelRecord.HeaderFlags):
        child_can_use: bool = flag(29)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelIdlmFlags(),
        MelIdleAnimationCount(),
        MelIdleTimerSetting(),
        MelIdleAnimations(),
        MelModel(),
    )

#------------------------------------------------------------------------------
class MreInfo(MelRecord):
    """Dialog Response."""
    rec_sig = b'INFO'

    class HeaderFlags(MelRecord.HeaderFlags):
        actor_changed: bool = flag(13)

    class _info_response_flags(Flags):
        goodbye: bool
        random: bool
        say_once: bool
        requires_player_activation: bool
        info_refusal: bool
        random_end: bool
        invisible_continue: bool
        walk_away: bool
        walk_away_invisible_in_menu: bool
        force_subtitle: bool
        can_move_while_greeting: bool
        no_lip_file: bool
        requires_post_processing: bool
        audio_output_override: bool
        spends_favor_points: bool

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBase(b'DATA', 'unknown_data'),
        MelStruct(b'ENAM', ['2H'], (_info_response_flags, 'response_flags'),
            'reset_hours'),
        MelFid(b'TPIC', 'info_topic'),
        MelFid(b'PNAM', 'prev_info'),
        MelUInt8(b'CNAM', 'favor_level'),
        MelFids('link_to', MelFid(b'TCLT')),
        MelFid(b'DNAM', 'response_data'),
        MelInfoResponsesFo3(),
        MelConditionList(),
        MelGroups('ck_left_overs',
            *_leftovers,
            MelBaseR(b'NEXT', 'left_over_marker'),
        ),
        MelLString(b'RNAM', 'info_prompt'),
        MelFid(b'ANAM', 'info_speaker'),
        MelFid(b'TWAT', 'walk_away_topic'),
        MelFid(b'ONAM', 'audio_output_override'),
    )

#------------------------------------------------------------------------------
class MreImad(AMreImad): # see AMreImad for details
    """Image Space Adapter."""
    melSet = MelSet(
        MelEdid(),
        MelPartialCounter(MelStruct(b'DNAM',
            ['I', 'f', '49I', '2f', '3I', '2B', '2s', '4I'], 'imad_animatable',
            'imad_duration', *AMreImad.dnam_counters1,
            'radial_blur_use_target', 'radial_blur_center_x',
            'radial_blur_center_y', *AMreImad.dnam_counters2,
            'dof_use_target', (AMreImad.imad_dof_flags, 'dof_flags'),
            'unused1', *AMreImad.dnam_counters3),
            counters=AMreImad.dnam_counter_mapping),
        *[AMreImad.special_impls[s](s, a) for s, a in AMreImad.imad_sig_attr],
    )

#------------------------------------------------------------------------------
class MreImgs(MelRecord):
    """Image Space."""
    rec_sig = b'IMGS'

    melSet = MelSet(
        MelEdid(),
        MelBase(b'ENAM', 'unknown_enam'),
        MelStruct(b'HNAM', ['9f'], 'hdr_eye_adapt_speed',
            'hdr_bloom_blur_radius', 'hdr_bloom_threshold', 'hdr_bloom_scale',
            'hdr_receive_bloom_threshold', 'hdr_white', 'hdr_sunlight_scale',
            'hdr_sky_scale', 'hdr_eye_adapt_strength'),
        MelImgsCinematic(),
        MelImgsTint(),
        MelTruncatedStruct(b'DNAM', ['3f', '2s', 'H'], 'dof_strength',
                           'dof_distance', 'dof_range', 'dof_unknown',
                           'dof_sky_blur_radius', old_versions={'3f'}),
    )

#------------------------------------------------------------------------------
class MreIngr(MelRecord):
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
        MelEquipmentType(),
        MelSoundPickupDrop(),
        MelValueWeight(),
        MelIngrEnit(),
        MelEffects(),
    )

#------------------------------------------------------------------------------
class MreIpct(MelRecord):
    """Impact."""
    rec_sig = b'IPCT'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelTruncatedStruct(b'DATA', ['f', 'I', '2f', 'I', '2B', '2s'],
            'effect_duration', 'effect_orientation', 'angle_threshold',
            'placement_radius', 'ipct_sound_level', 'ipct_no_decal_data',
            'impact_result', 'unknown1', old_versions={'fI2f'}),
        MelDecalData(),
        MelIpctTextureSets(),
        MelIpctSounds(),
        MelIpctHazard(),
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
class MreKeym(MelRecord):
    """Key."""
    rec_sig = b'KEYM'

    class HeaderFlags(NotPlayableFlag, MelRecord.HeaderFlags):
        pass

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelSoundPickupDrop(),
        MelKeywords(),
        MelValueWeight(),
    )

#------------------------------------------------------------------------------
class MreKywd(MelRecord):
    """Keyword."""
    rec_sig = b'KYWD'

    melSet = MelSet(
        MelEdid(),
        MelColorO(),
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
class MreLcrt(MelRecord):
    """Location Reference Type."""
    rec_sig = b'LCRT'

    melSet = MelSet(
        MelEdid(),
        MelColorO(),
    )

#------------------------------------------------------------------------------
class MreLctn(MelRecord):
    """Location"""
    rec_sig = b'LCTN'

    melSet = MelSet(
        MelLctnShared(),
        MelFid(b'NAM0', 'horse_marker_ref'),
        MelColorO(),
    )

#------------------------------------------------------------------------------
class MreLgtm(MelRecord):
    """Lighting Template."""
    rec_sig = b'LGTM'

    melSet = MelSet(
        MelEdid(),
        MelTruncatedStruct(b'DATA',
            ['3B', 's', '3B', 's', '3B', 's', '2f', '2i', '3f', '28B', 'f',
             '3B', 's', '3f', '4s'], *gen_color('lgtm_ambient_color'),
            *gen_color('lgtm_directional_color'),
            *gen_color('lgtm_fog_color_near'), 'lgtm_fog_near',
            'lgtm_fog_far', 'lgtm_directional_rotation_xy',
            'lgtm_directional_rotation_z', 'lgtm_directional_fade',
            'lgtm_fog_clip_distance', 'lgtm_fog_power',
            *gen_ambient_lighting('lgtm'), *gen_color('lgtm_fog_color_far'),
            'lgtm_fog_max', 'lgtm_light_fade_distances_start',
            'lgtm_light_fade_distances_end', 'lgtm_unknown_data',
            old_versions={'3Bs3Bs3Bs2f2i3f28Bf', '3Bs3Bs3Bs2f2i3f24B'}),
        MelDalc(),
    )

#------------------------------------------------------------------------------
class MreLigh(MelRecord):
    """Light."""
    rec_sig = b'LIGH'

    class HeaderFlags(MelRecord.HeaderFlags):
        random_animation_start: bool = flag(16)
        portal_strict: bool = flag(17)
        obstacle: bool = flag(25)

    class _light_flags(Flags):
        light_dynamic: bool = flag(0)
        light_can_take: bool = flag(1)
        light_negative: bool = flag(2)
        light_flickers: bool = flag(3)
        light_off_by_default: bool = flag(5)
        light_flickers_slow: bool = flag(6)
        light_pulses: bool = flag(7)
        light_pulses_slow: bool = flag(8)
        light_spot_light: bool = flag(9)
        light_shadow_spotlight: bool = flag(10)
        light_shadow_hemisphere: bool = flag(11)
        light_shadow_omnidirectional: bool = flag(12)
        light_portal_strict: bool = flag(13)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelModel(),
        MelDestructible(),
        MelFull(),
        MelIcons(),
        MelStruct(b'DATA', ['i', 'I', '4B', 'I', '6f', 'I', 'f'],
            'duration', 'light_radius', *gen_color('light_color'),
            (_light_flags, 'light_flags'), 'light_falloff', 'light_fov',
            'light_near_clip', 'light_fe_period', # fe = 'Flicker Effect'
            'light_fe_intensity_amplitude', 'light_fe_movement_amplitude',
            'value', 'weight'),
        MelLighFade(),
        MelSound(),
        sse_only(MelLighLensFlare()),
    )

#------------------------------------------------------------------------------
class MreLscr(MelRecord):
    """Load Screen."""
    rec_sig = b'LSCR'

    class HeaderFlags(MelRecord.HeaderFlags):
        displays_in_main_menu: bool = flag(10)

    melSet = MelSet(
        MelEdid(),
        MelIcons(),
        MelDescription(),
        MelConditionList(),
        MelLscrNif(),
        MelFloat(b'SNAM', 'lscr_initial_scale'),
        MelStruct(b'RNAM', ['3h'], 'lscr_rotation_grid_y',
            'lscr_rotation_grid_x', 'lscr_rotation_grid_z'),
        MelLscrRotation(),
        MelStruct(b'XNAM', ['3f'], 'lscr_translation_grid_y',
            'lscr_translation_grid_x', 'lscr_translation_grid_z'),
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
        sse_only(MelUInt32(b'INAM', 'is_considered_snow')),
    )

#------------------------------------------------------------------------------
class MreLvli(AMreLeveledList):
    """Leveled Item."""
    rec_sig = b'LVLI'
    _top_copy_attrs = ('lvl_chance_none', 'lvl_global')
    _entry_copy_attrs = ('level', 'listId', 'count', 'item_owner',
                         'item_global', 'item_condition')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelLLChanceNone(),
        MelLLFlags(),
        MelLLGlobal(),
        MelLLItems(),
    )

#------------------------------------------------------------------------------
class MreLvln(AMreLeveledList):
    """Leveled NPC."""
    rec_sig = b'LVLN'
    _top_copy_attrs = ('lvl_chance_none', 'lvl_global', 'model')
    _entry_copy_attrs = ('level', 'listId', 'count', 'item_owner',
                         'item_global', 'item_condition')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelLLChanceNone(),
        MelLLFlags(),
        MelLLGlobal(),
        MelLLItems(),
        MelModel(),
    )

#------------------------------------------------------------------------------
class MreLvsp(AMreLeveledList):
    """Leveled Spell."""
    rec_sig = b'LVSP'
    _top_copy_attrs = ('lvl_chance_none',)
    _entry_copy_attrs = ('level', 'listId', 'count')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelLLChanceNone(),
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
        if_sse(
            le_version=MelTruncatedStruct(b'DATA', ['11f', 'I'],
                'falloff_scale', 'falloff_bias', 'noise_uv_scale',
                'material_uv_scale', 'projection_vector_x',
                'projection_vector_y', 'projection_vector_z',
                'normal_dampener', *gen_color3('single_pass_color'),
                'is_single_pass', old_versions={'7f'}),
            se_version=MelTruncatedStruct(b'DATA', ['11f', 'I', 'B', '3s'],
                'falloff_scale', 'falloff_bias', 'noise_uv_scale',
                'material_uv_scale', 'projection_vector_x',
                'projection_vector_y', 'projection_vector_z',
                'normal_dampener', *gen_color3('single_pass_color'),
                'is_single_pass', 'is_considered_snow', 'unused1',
                old_versions={'7f', '11fI'}),
        ),
    )

#------------------------------------------------------------------------------
class MreMatt(MelRecord):
    """Material Type."""
    rec_sig = b'MATT'

    melSet = MelSet(
        MelEdid(),
        MelMattShared(),
    )

#------------------------------------------------------------------------------
class MreMesg(MelRecord):
    """Message."""
    rec_sig = b'MESG'

    class MesgTypeFlags(Flags):
        messageBox: bool
        autoDisplay: bool

    melSet = MelSet(
        MelEdid(),
        MelDescription(),
        MelFull(),
        MelFid(b'INAM','iconUnused'), # leftover
        MelFid(b'QNAM','materialParent'),
        MelUInt32Flags(b'DNAM', u'flags', MesgTypeFlags),
        MelUInt32(b'TNAM', 'displayTime'),
        MelGroups('menu_buttons',
            MelLString(b'ITXT', 'button_text'),
            MelConditionList(),
        ),
    )

#------------------------------------------------------------------------------
class MreMgef(MelRecord):
    """Magic Effect."""
    rec_sig = b'MGEF'

    class MgefGeneralFlags(Flags):
        hostile: bool = flag(0)
        recover: bool = flag(1)
        detrimental: bool = flag(2)
        snaptoNavmesh: bool = flag(3)
        noHitEvent: bool = flag(4)
        dispellwithKeywords: bool = flag(8)
        noDuration: bool = flag(9)
        noMagnitude: bool = flag(10)
        noArea: bool = flag(11)
        fXPersist: bool = flag(12)
        goryVisuals: bool = flag(14)
        hideinUI: bool = flag(15)
        noRecast: bool = flag(17)
        powerAffectsMagnitude: bool = flag(21)
        powerAffectsDuration: bool = flag(22)
        painless: bool = flag(26)
        noHitEffect: bool = flag(27)
        noDeathDispel: bool = flag(28)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelFull(),
        MelMdob(),
        MelKeywords(),
        MelPartialCounter(MelStruct(b'DATA',
            ['I', 'f', 'I', '2i', 'H', '2s', 'I', 'f', '4I', '4f', 'I', 'i',
             '4I', 'i', '3I', 'f', 'I', 'f', '7I', '2f'],
            (MgefGeneralFlags, 'flags'), 'base_cost', (FID, 'associated_item'),
            'magic_skill', 'resist_value', 'counter_effect_count', 'unused1',
            (FID, 'light'), 'taper_weight', (FID, 'hit_shader'),
            (FID, 'enchant_shader'), 'minimum_skill_level', 'spellmaking_area',
            'spellmaking_casting_time', 'taper_curve', 'taper_duration',
            'second_av_weight', 'effect_archetype', 'actorValue',
            (FID, 'projectile'), (FID, 'explosion'), 'casting_type',
            'delivery', 'second_av', (FID, 'casting_art'),
            (FID, 'hit_effect_art'), (FID, 'effect_impact_data'),
            'skill_usage_multiplier', (FID, 'dual_casting_art'),
            'dual_casting_scale', (FID, 'enchant_art'), (FID, 'hit_visuals'),
            (FID, 'enchant_visuals'), (FID, 'equip_ability'),
            (FID, 'effect_imad'), (FID, 'perk_to_apply'),
            'casting_sound_level', 'script_effect_ai_score',
            'script_effect_ai_delay_time'),
            counters={'counter_effect_count': 'counter_effects'}),
        MelSorted(MelGroups(u'counter_effects',
            MelFid(b'ESCE', u'counter_effect_code'),
        ), sort_by_attrs='counter_effect_code'),
        MelArray(u'sounds',
            MelStruct(b'SNDD', [u'2I'], u'soundType', (FID, u'sound')),
        ),
        MelLString(b'DNAM', u'magic_item_description'),
        MelConditionList(),
    )

#------------------------------------------------------------------------------
class MreMisc(MelRecord):
    """Misc. Item."""
    rec_sig = b'MISC'

    class HeaderFlags(NotPlayableFlag, MelRecord.HeaderFlags):
        pass

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelSoundPickupDrop(),
        MelKeywords(),
        MelValueWeight(),
    )

#------------------------------------------------------------------------------
class MreMovt(MelRecord):
    """Movement Type."""
    rec_sig = b'MOVT'

    melSet = MelSet(
        MelEdid(),
        MelString(b'MNAM','mnam_n'),
        MelTruncatedStruct(b'SPED', [u'11f'], 'leftWalk', 'leftRun', 'rightWalk',
                           'rightRun', 'forwardWalk', 'forwardRun', 'backWalk',
                           'backRun', 'rotateInPlaceWalk', 'rotateInPlaceRun',
                           'rotateWhileMovingRun', old_versions={'10f'}),
        MelOptStruct(b'INAM', [u'3f'],'directional','movementSpeed','rotationSpeed'),
    )

#------------------------------------------------------------------------------
class MreMstt(MelRecord):
    """Moveable Static."""
    rec_sig = b'MSTT'

    class HeaderFlags(NavMeshFlags, VWDFlag, MelRecord.HeaderFlags):
        must_update_anims: bool = flag(8)
        hidden_from_local_map: bool = flag(9)
        random_animation_start: bool = flag(16)
        has_currents: bool = flag(19)
        obstacle: bool =  flag(25)


    class MsttTypeFlags(Flags):
        onLocalMap: bool
        unknown2: bool

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelUInt8Flags(b'DATA', u'flags', MsttTypeFlags),
        MelSound(),
    )

#------------------------------------------------------------------------------
class MreMusc(MelRecord):
    """Music Type."""
    rec_sig = b'MUSC'

    class MuscTypeFlags(Flags):
        playsOneSelection: bool = flag(0)
        abruptTransition: bool = flag(1)
        cycleTracks: bool = flag(2)
        maintainTrackOrder: bool = flag(3)
        unknown5: bool = flag(4)
        ducksCurrentTrack: bool = flag(5)

    melSet = MelSet(
        MelEdid(),
        MelUInt32Flags(b'FNAM', u'flags', MuscTypeFlags),
        # Divided by 100 in TES5Edit, probably for editing only
        MelStruct(b'PNAM', [u'2H'],'priority','duckingDB'),
        MelFloat(b'WNAM', 'fadeDuration'),
        MelSimpleArray('musicTracks', MelFid(b'TNAM')),
    )

#------------------------------------------------------------------------------
class MreMust(MelRecord):
    """Music Track."""
    rec_sig = b'MUST'

    melSet = MelSet(
        MelEdid(),
        MelUInt32(b'CNAM', 'trackType'),
        MelFloat(b'FLTV', 'track_duration'),
        MelUInt32(b'DNAM', 'fadeOut'),
        MelString(b'ANAM','trackFilename'),
        MelString(b'BNAM','finaleFilename'),
        MelArray('points',
            MelFloat(b'FNAM', u'cuePoints'),
        ),
        MelOptStruct(b'LNAM', [u'2f', u'I'],'loopBegins','loopEnds','loopCount',),
        MelConditions(),
        MelSimpleArray('tracks', MelFid(b'SNAM')),
    )

#------------------------------------------------------------------------------
# Not Mergable - FormIDs unaccounted for
class MreNavi(MelRecord):
    """Navigation Mesh Info Map."""
    rec_sig = b'NAVI'

    melSet = MelSet(
        MelEdid(),
        MelUInt32(b'NVER', 'version'),
        # NVMI and NVPP would need special routines to handle them
        # If no mitigation is needed, then leave it as MelBase
        MelBase(b'NVMI','navigationMapInfos',),
        MelBase(b'NVPP','preferredPathing',),
        MelSimpleArray('navigationMesh', MelFid(b'NVSI')),
    )

#------------------------------------------------------------------------------
# Not mergeable due to the way this record is linked to NAVI records
class MreNavm(MelRecord):
    """Navigation Mesh."""
    rec_sig = b'NAVM'

    class HeaderFlags(MelRecord.HeaderFlags):
        auto_generate: bool = flag(26)
        generate_cell: bool = flag(31)

    melSet = MelSet(
        MelEdid(),
        MelNvnm(),
        MelBase(b'ONAM', 'unknownONAM'),
        MelBase(b'PNAM', 'unknownPNAM'),
        MelBase(b'NNAM', 'unknownNNAM'),
    )

#------------------------------------------------------------------------------
class MreNpc_(AMreActor):
    """Non-Player Character."""
    rec_sig = b'NPC_'

    class HeaderFlags(AMreActor.HeaderFlags):
        bleedout_override: bool = flag(29)

    class _TemplateFlags(Flags):
        useTraits: bool = flag(0)
        useStats: bool = flag(1)
        useFactions: bool = flag(2)
        useSpellList: bool = flag(3)
        useAIData: bool = flag(4)
        useAIPackages: bool = flag(5)
        useModelAnimation: bool = flag(6)
        useBaseData: bool = flag(7)
        useInventory: bool = flag(8)
        useScript: bool = flag(9)
        useDefPackList: bool = flag(10)
        useAttackData: bool = flag(11)
        useKeywords: bool = flag(12)

    class NpcFlags1(Flags):
        female: bool = flag(0)
        essential: bool = flag(1)
        isCharGenFacePreset: bool = flag(2)
        respawn: bool = flag(3)
        autoCalc: bool = flag(4)
        unique: bool = flag(5)
        doesNotAffectStealth: bool = flag(6)
        pcLevelOffset: bool = flag(7)
        useTemplate: bool = flag(8)
        unknown9: bool = flag(9)
        unknown10: bool = flag(10)
        protected: bool = flag(11)
        unknown12: bool = flag(12)
        unknown13: bool = flag(13)
        summonable: bool = flag(14)
        unknown15: bool = flag(15)
        doesNotBleed: bool = flag(16)
        unknown17: bool = flag(17)
        bleedoutOverride: bool = flag(18)
        oppositeGenderAnims: bool = flag(19)
        simpleActor: bool = flag(20)
        loopedScript: bool = flag(21)
        unknown22: bool = flag(22)
        unknown23: bool = flag(23)
        unknown24: bool = flag(24)
        unknown25: bool = flag(25)
        unknown26: bool = flag(26)
        unknown27: bool = flag(27)
        loopedAudio: bool = flag(28)
        isGhost: bool = flag(29)
        unknown30: bool = flag(30)
        invulnerable: bool = flag(31)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelStruct(b'ACBS', [u'I', u'2H', u'h', u'3H', u'h', u'3H'],
                  (NpcFlags1, u'flags'),'magickaOffset',
                  'staminaOffset','level_offset','calcMin',
                  'calcMax','speedMultiplier','dispositionBase',
                  (_TemplateFlags, u'templateFlags'), 'healthOffset',
                  'bleedoutOverride',),
        MelFactions(),
        MelFid(b'INAM', 'deathItem'),
        MelFid(b'VTCK', 'voice'),
        MelFid(b'TPLT', 'template'),
        MelRace(),
        MelSpellCounter(),
        MelSpells(),
        MelDestructible(),
        MelFid(b'WNAM', 'wornArmor'),
        MelFid(b'ANAM', 'farawaymodel'),
        MelFid(b'ATKR', 'attackRace'),
        MelAttacks(),
        MelFid(b'SPOR', 'spectator'),
        MelFid(b'OCOR', 'observe'),
        MelFid(b'GWOR', 'guardWarn'),
        MelFid(b'ECOR', 'combat'),
        MelCounter(MelUInt32(b'PRKZ', 'perk_count'), counts='perks'),
        MelSorted(MelGroups('perks',
            MelOptStruct(b'PRKR', [u'I', u'B', u'3s'],(FID, 'perk'),'rank','prkrUnused'),
        ), sort_by_attrs='perk'),
        MelItems(),
        MelStruct(b'AIDT', [u'B', u'B', u'B', u'B', u'B', u'B', u'B', u'B', u'I', u'I', u'I'], 'aggression', 'confidence',
                  'energyLevel', 'responsibility', 'mood', 'assistance',
                  'aggroRadiusBehavior',
                  'aidtUnknown', 'warn', 'warnAttack', 'attack'),
        MelFids('aiPackages', MelFid(b'PKID')),
        MelKeywords(),
        MelFid(b'CNAM', 'iclass'),
        MelFull(),
        MelShortName(b'SHRT'),
        MelBase(b'DATA', 'marker'),
        MelStruct(b'DNAM', [u'36B', u'H', u'H', u'H', u'2s', u'f', u'B', u'3s'],
            'oneHandedSV','twoHandedSV','marksmanSV','blockSV','smithingSV',
            'heavyArmorSV','lightArmorSV','pickpocketSV','lockpickingSV',
            'sneakSV','alchemySV','speechcraftSV','alterationSV','conjurationSV',
            'destructionSV','illusionSV','restorationSV','enchantingSV',
            'oneHandedSO','twoHandedSO','marksmanSO','blockSO','smithingSO',
            'heavyArmorSO','lightArmorSO','pickpocketSO','lockpickingSO',
            'sneakSO','alchemySO','speechcraftSO','alterationSO','conjurationSO',
            'destructionSO','illusionSO','restorationSO','enchantingSO',
            'health','magicka','stamina','dnamUnused1',
            'farawaymodeldistance','gearedupweapons','dnamUnused2'),
        MelSorted(MelFids('head_part_addons', MelFid(b'PNAM'))),
        MelFid(b'HCLF', u'hair_color'),
        MelFid(b'ZNAM', u'combatStyle'),
        MelFid(b'GNAM', u'gifts'),
        MelBase(b'NAM5', u'nam5_p'),
        MelFloat(b'NAM6', u'height'),
        MelFloat(b'NAM7', u'weight'),
        MelUInt32(b'NAM8', u'sound_level'),
        MelActorSounds(),
        MelFid(b'CSCR', u'audio_template'),
        MelFid(b'DOFT', u'default_outfit'),
        MelFid(b'SOFT', u'sleep_outfit'),
        MelFid(b'DPLT', u'default_package'),
        MelFid(b'CRIF', u'crime_faction'),
        MelFid(b'FTST', u'face_texture'),
        MelOptStruct(b'QNAM', [u'3f'], u'skin_tone_r', u'skin_tone_g',
            u'skin_tone_b'),
        MelOptStruct(b'NAM9', [u'19f'], u'nose_long', u'nose_up', u'jaw_up',
            u'jaw_wide', u'jaw_forward', u'cheeks_up', u'cheeks_back',
            u'eyes_up', u'eyes_out', u'brows_up', u'brows_out',
            u'brows_forward', u'lips_up', u'lips_out', u'chin_wide',
            u'chin_down', u'chin_underbite', u'eyes_back', u'nam9_unused'),
        MelOptStruct(b'NAMA', [u'I', u'i', u'2I'], u'nose', u'unknown', u'eyes', u'mouth'),
        MelSorted(MelGroups(u'face_tint_layer',
            MelUInt16(b'TINI', u'tint_item'),
            MelStruct(b'TINC', [u'4B'], u'tintRed', u'tintGreen', u'tintBlue',
                u'tintAlpha'),
            MelSInt32(b'TINV', u'tint_value'),
            MelSInt16(b'TIAS', u'preset'),
        ), sort_by_attrs='tint_item'),
    )

#------------------------------------------------------------------------------
class MreOtft(MelRecord):
    """Outfit."""
    rec_sig = b'OTFT'

    melSet = MelSet(
        MelEdid(),
        MelSorted(MelSimpleArray('items', MelFid(b'INAM'))),
    )

    def mergeFilter(self, modSet):
        self.items = [i for i in self.items if i.mod_fn in modSet]

#------------------------------------------------------------------------------
class MrePack(MelRecord):
    """Package."""
    rec_sig = b'PACK'

    class _GeneralFlags(Flags):
        offers_services: bool = flag(0)
        must_complete: bool = flag(2)
        maintain_speed_at_goal: bool = flag(3)
        unlock_doors_at_package_start: bool = flag(6)
        unlock_doors_at_package_end: bool = flag(7)
        continue_if_pc_near: bool = flag(9)
        once_per_day: bool = flag(10)
        preferred_speed: bool = flag(13)
        always_sneak: bool = flag(17)
        allow_swimming: bool = flag(18)
        ignore_combat: bool = flag(20)
        weapons_unequipped: bool = flag(21)
        weapon_drawn: bool = flag(23)
        no_combat_alert: bool = flag(27)
        wear_sleep_outfit: bool = flag(29)

    class _InterruptFlags(Flags):
        hellos_to_player: bool = flag(0)
        random_conversations: bool = flag(1)
        observe_combat_behavior: bool = flag(2)
        greet_corpse_behavior: bool = flag(3)
        reaction_to_player_actions: bool = flag(4)
        friendly_fire_comments: bool = flag(5)
        aggro_radius_behavior: bool = flag(6)
        allow_idle_chatter: bool = flag(7)
        world_interactions: bool = flag(9)

    class _SubBranchFlags(Flags):
        repeat_when_complete: bool

    class _BranchFlags(Flags):
        success_completes_package: bool

    class MelDataInputs(MelGroups):
        """Occurs twice in PACK, so moved here to deduplicate the
        definition a bit."""
        class _DataInputFlags(Flags):
            public: bool

        def __init__(self, attr):
            MelGroups.__init__(self, attr,
                MelSInt8(b'UNAM', 'input_index'),
                MelString(b'BNAM', 'input_name'),
                MelUInt32Flags(b'PNAM', u'input_flags', self._DataInputFlags),
            )

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelStruct(b'PKDT', ['I', '3B', 's', 'H', '2s'],
            (_GeneralFlags, 'pack_flags'), 'package_type',
            'interruptOverride', 'preferredSpeed', 'unknown1',
            (_InterruptFlags, 'interruptFlags'), 'unknown2'),
        MelStruct(b'PSDT', ['2b', 'B', '2b', '3s', 'i'], 'schedule_month',
            'schedule_day', 'schedule_date', 'schedule_hour',
            'schedule_minute', 'unused1', 'schedule_duration'),
        MelConditionList(),
        MelGroup('idleAnimations',
            MelUInt8(b'IDLF', u'animation_flags'),
            MelIdleAnimationCountOld(),
            MelIdleTimerSetting(),
            MelIdleAnimations(),
            MelBase(b'IDLB', 'unknown1'),
        ),
        MelFid(b'CNAM', 'combatStyle',),
        MelFid(b'QNAM', 'owner_quest'),
        MelStruct(b'PKCU', [u'3I'], 'dataInputCount', (FID, 'packageTemplate'),
                  'versionCount'),
        MelGroups('data_input_values',
            MelString(b'ANAM', 'value_type'),
            MelUnion({
                u'Bool': MelUInt8(b'CNAM', u'value_val'),
                u'Int': MelUInt32(b'CNAM', u'value_val'),
                u'Float': MelFloat(b'CNAM', u'value_val'),
                # Mirrors what xEdit does, despite how weird it looks
                u'ObjectList': MelFloat(b'CNAM', u'value_val'),
            }, decider=AttrValDecider(u'value_type'),
                # All other kinds of values, typically missing
                fallback=MelBase(b'CNAM', u'value_val')),
            MelBase(b'BNAM', 'unknown1'),
            MelTopicData('value_topic_data'),
            MelLocation(b'PLDT'),
            MelUnion({
                (0, 1, 3): MelOptStruct(b'PTDA', [u'i', u'I', u'i'], u'target_type',
                    (FID, u'target_value'), u'target_count'),
                2: MelOptStruct(b'PTDA', [u'i', u'I', u'i'], u'target_type',
                    u'target_value', u'target_count'),
                4: MelOptStruct(b'PTDA', [u'3i'], u'target_type',
                    u'target_value', u'target_count'),
                (5, 6): MelOptStruct(b'PTDA', [u'i', u'4s', u'i'], u'target_type',
                    u'target_value', u'target_count'),
            }, decider=PartialLoadDecider(
                loader=MelSInt32(b'PTDA', u'target_type'),
                decider=AttrValDecider(u'target_type'))),
            MelBase(b'TPIC', 'unknown2'),
        ),
        MelDataInputs('data_inputs1'),
        MelBase(b'XNAM', 'marker'),
        MelGroups('procedure_tree_branches',
            MelString(b'ANAM', 'branch_type'),
            MelConditions(),
            MelOptStruct(b'PRCB', [u'2I'], 'sub_branch_count',
                         (_SubBranchFlags, u'sub_branch_flags')),
            MelString(b'PNAM', 'procedure_type'),
            MelUInt32Flags(b'FNAM', u'branch_flags', _BranchFlags),
            MelGroups('data_input_indices',
                MelUInt8(b'PKC2', 'input_index'),
            ),
            MelGroups('flag_overrides',
                MelStruct(b'PFO2', [u'2I', u'2H', u'B', u'3s'],
                          (_GeneralFlags, u'set_general_flags'),
                          (_GeneralFlags, u'clear_general_flags'),
                          (_InterruptFlags, u'set_interrupt_flags'),
                          (_InterruptFlags, u'clear_interrupt_flags'),
                          'preferred_speed_override', 'unknown1'),
            ),
            MelGroups('unknown1',
                MelBase(b'PFOR', 'unknown1'),
            ),
        ),
        MelDataInputs('data_inputs2'),
        MelIdleHandler(u'on_begin'),
        MelIdleHandler(u'on_end'),
        MelIdleHandler(u'on_change'),
    ).with_distributor({
        b'PKDT': {
            b'CTDA|CIS1|CIS2': u'conditions',
            b'CNAM': u'combatStyle',
            b'QNAM': u'owner_quest',
            b'ANAM': (u'data_input_values', {
                b'BNAM|CNAM|PDTO': u'data_input_values',
            }),
            b'UNAM': (u'data_inputs1', {
                b'BNAM|PNAM': u'data_inputs1',
            }),
        },
        b'XNAM': {
            b'ANAM|CTDA|CIS1|CIS2|PNAM': u'procedure_tree_branches',
            b'UNAM': (u'data_inputs2', {
                b'BNAM|PNAM': u'data_inputs2',
            }),
        },
        b'POBA': {
            b'INAM|SCHR|SCDA|SCTX|QNAM|TNAM|PDTO': 'on_begin',
        },
        b'POEA': {
            b'INAM|SCHR|SCDA|SCTX|QNAM|TNAM|PDTO': 'on_end',
        },
        b'POCA': {
            b'INAM|SCHR|SCDA|SCTX|QNAM|TNAM|PDTO': 'on_change',
        },
    })

#------------------------------------------------------------------------------
class MrePerk(MelRecord):
    """Perk."""
    rec_sig = b'PERK'

    class HeaderFlags(NotPlayableFlag, MelRecord.HeaderFlags):
        pass

    class _script_flags(Flags):
        run_immediately: bool
        replace_default: bool

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelFull(),
        MelDescription(),
        MelIcons(),
        MelConditionList(),
        MelPerkData(),
        MelNextPerk(),
        MelSorted(MelGroups('perk_effects',
            MelStruct(b'PRKE', ['3B'], 'pe_type', 'pe_rank', 'pe_priority'),
            MelUnion({
                0: MelStruct(b'DATA', ['I', 'B', '3s'], (FID, 'pe_quest'),
                    'pe_quest_stage', 'pe_unused'),
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
                # There is a special case: if EPFT is 2 and the pe_function
                # (see DATA above) is one of 5, 12, 13 or 14, then
                # EPFD=int, float - we use a return value of 8 for this.
                MelUInt8(b'EPFT', 'pp_param_type'),
                MelLString(b'EPF2', 'pp_button_label'),
                MelStruct(b'EPF3', ['2H'], (_script_flags, 'pp_script_flags'),
                    'pp_fragment_index'),
                MelUnion({
                    0: MelBase(b'EPFD', 'pp_param1'),
                    1: MelFloat(b'EPFD', 'pp_param1'),
                    2: MelStruct(b'EPFD', ['2f'], 'pp_param1', 'pp_param2'),
                    (3, 4, 5): MelFid(b'EPFD', 'pp_param1'),
                    6: MelString(b'EPFD', 'pp_param1'),
                    7: MelLString(b'EPFD', 'pp_param1'),
                    8: MelStruct(b'EPFD', ['I', 'f'], 'pp_param1',
                        'pp_param2'),
                }, decider=PerkEpdfDecider({5, 12, 13, 14})),
            ),
            MelBaseR(b'PRKF', 'pe_end_marker'),
        ), sort_special=perk_effect_key),
    ).with_distributor(perk_distributor)

#------------------------------------------------------------------------------
class MreProj(MelRecord):
    """Projectile."""
    rec_sig = b'PROJ'

    class ProjTypeFlags(Flags):
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
        projectile_rotates: bool = flag(11)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelTruncatedStruct(b'DATA',
            [u'2H', u'3f', u'2I', u'3f', u'2I', u'3f', u'3I', u'4f', u'2I'],
            (ProjTypeFlags, u'flags'),
            'projectileTypes', 'gravity', ('speed', 10000.0),
            ('range', 10000.0), (FID, u'light'), (FID, u'muzzleFlash'),
            'tracerChance', 'explosionAltTrigerProximity',
            'explosionAltTrigerTimer', (FID, u'explosion'),
            (FID, u'sound'), 'muzzleFlashDuration',
            'fadeDuration', 'impactForce',
            (FID, u'soundCountDown'), (FID, u'soundDisable'),
            (FID, u'defaultWeaponSource'), 'coneSpread',
            'collisionRadius', 'lifetime',
            'relaunchInterval', (FID, u'decalData'),
            (FID, u'collisionLayer'), old_versions={'2H3f2I3f2I3f3I4fI',
                                                    '2H3f2I3f2I3f3I4f'}),
        MelGroup('models',
            MelString(b'NAM1','muzzleFlashPath'),
            # Ignore texture hashes - they're only an optimization, plenty of
            # records in Skyrim.esm are missing them
            MelNull(b'NAM2'),
        ),
        MelUInt32(b'VNAM', 'soundLevel',),
    )

#------------------------------------------------------------------------------
# Needs testing should be mergable
class MreQust(MelRecord):
    """Quest."""
    rec_sig = b'QUST'

    class _questFlags(Flags):
        startGameEnabled: bool = flag(0)
        completed: bool = flag(1)
        add_idle_topic_to_hello: bool = flag(2)
        allowRepeatedStages: bool = flag(3)
        starts_enabled: bool = flag(4)
        displayed_in_hud: bool = flag(5)
        failed: bool = flag(6)
        stage_wait: bool = flag(7)
        runOnce: bool = flag(8)
        excludeFromDialogueExport: bool = flag(9)
        warnOnAliasFillFailure: bool = flag(10)
        active: bool = flag(11)
        repeats_conditions: bool = flag(12)
        keep_instance: bool = flag(13)
        want_dormat: bool = flag(14)
        has_dialogue_data: bool = flag(15)

    class _stageFlags(Flags):
        unknown0: bool = flag(0)
        startUpStage: bool = flag(1)
        startDownStage: bool = flag(2)
        keepInstanceDataFromHereOn: bool = flag(3)

    class stageEntryFlags(Flags):
        complete: bool
        fail: bool

    class objectiveFlags(Flags):
        oredWithPrevious: bool

    class targetFlags(Flags):
        ignoresLocks: bool

    class aliasFlags(Flags):
        reservesLocationReference: bool = flag(0)
        optional: bool = flag(1)
        questObject: bool = flag(2)
        allowReuseInQuest: bool = flag(3)
        allowDead: bool = flag(4)
        inLoadedArea: bool = flag(5)
        essential: bool = flag(6)
        allowDisabled: bool = flag(7)
        storesText: bool = flag(8)
        allowReserved: bool = flag(9)
        protected: bool = flag(10)
        noFillType: bool = flag(11)
        allowDestroyed: bool = flag(12)
        closest: bool = flag(13)
        usesStoredText: bool = flag(14)
        initiallyDisabled: bool = flag(15)
        allowCleared: bool = flag(16)
        clearsNameWhenRemoved: bool = flag(17)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelFull(),
        MelStruct(b'DNAM', [u'H', u'2B', u'4s', u'I'], (_questFlags, u'questFlags'),
                  'priority', 'formVersion', 'unknown', 'questType'),
        MelOptStruct(b'ENAM', [u'4s'], u'event_name'),
        MelFids('textDisplayGlobals', MelFid(b'QTGL')),
        MelString(b'FLTR','objectWindowFilter'),
        MelConditionList('dialogueConditions'),
        MelBase(b'NEXT','marker'),
        MelConditionList('eventConditions'),
        MelSorted(MelGroups('stages',
            MelStruct(b'INDX', [u'H', u'2B'],'index',(_stageFlags, u'flags'),'unknown'),
            MelGroups('log_entries',
                MelUInt8Flags(b'QSDT', u'stageFlags', stageEntryFlags),
                MelConditionList(),
                MelLString(b'CNAM', 'log_entry_text'),
                MelFid(b'NAM0', 'nextQuest'),
                *_leftovers,
            ),
        ), sort_by_attrs='index'),
        MelGroups('objectives',
            MelUInt16(b'QOBJ', 'index'),
            MelUInt32Flags(b'FNAM', u'flags', objectiveFlags),
            MelLString(b'NNAM', 'display_text'),
            MelGroups('targets',
                MelStruct(b'QSTA', [u'i', u'B', u'3s'],'alias',(targetFlags,'flags'),'unused1'),
                MelConditionList(),
            ),
        ),
        MelBase(b'ANAM','aliasMarker'),
        MelGroups(u'qust_aliases',
            MelUnion({
                b'ALST': MelUInt32(b'ALST', u'aliasId'),
                b'ALLS': MelUInt32(b'ALLS', u'aliasId'),
            }),
            MelString(b'ALID', 'aliasName'),
            MelUInt32Flags(b'FNAM', u'flags', aliasFlags),
            MelSInt32(b'ALFI', u'forcedIntoAlias'), # alias ID
            MelFid(b'ALFL','specificLocation'),
            MelFid(b'ALFR','forcedReference'),
            MelFid(b'ALUA','uniqueActor'),
            MelGroup('locationAliasReference',
                MelSInt32(b'ALFA', 'alias'),
                MelFid(b'KNAM','keyword'),
                MelFid(b'ALRT','referenceType'),
            ),
            MelGroup('externalAliasReference',
                MelFid(b'ALEQ','quest'),
                MelSInt32(b'ALEA', 'alias'),
            ),
            MelGroup('createReferenceToObject',
                MelFid(b'ALCO','object'),
                MelStruct(b'ALCA', [u'h', u'H'], 'alias', 'create_target'),
                MelUInt32(b'ALCL', 'createLevel'),
            ),
            MelGroup('findMatchingReferenceNearAlias',
                MelSInt32(b'ALNA', 'alias'),
                MelUInt32(b'ALNT', 'type'),
            ),
            MelGroup('findMatchingReferenceFromEvent',
                MelStruct(b'ALFE', [u'4s'],'fromEvent'),
                MelStruct(b'ALFD', [u'4s'],'eventData'),
            ),
            MelConditionList(),
            MelKeywords(),
            MelItems(),
            MelFid(b'SPOR','spectatorOverridePackageList'),
            MelFid(b'OCOR','observeDeadBodyOverridePackageList'),
            MelFid(b'GWOR','guardWarnOverridePackageList'),
            MelFid(b'ECOR','combatOverridePackageList'),
            MelFid(b'ALDN','displayName'),
            MelFids('aliasSpells', MelFid(b'ALSP')),
            MelFids('aliasFactions', MelFid(b'ALFC')),
            MelFids('aliasPackageData', MelFid(b'ALPC')),
            MelFid(b'VTCK','voiceType'),
            MelBase(b'ALED','aliasEnd'),
        ),
        MelLString(b'NNAM','description'),
        MelGroups('targets',
            MelStruct(b'QSTA', [u'I', u'B', u'3s'], (FID, 'target'), (targetFlags, 'flags'),
                      'unknown1'),
            MelConditionList(),
        ),
    ).with_distributor({
        b'DNAM': {
            b'CTDA|CIS1|CIS2': u'dialogueConditions',
        },
        b'NEXT': {
            b'CTDA|CIS1|CIS2': u'eventConditions',
        },
        b'INDX': {
            b'CTDA|CIS1|CIS2': u'stages',
        },
        b'QOBJ': {
            b'CTDA|CIS1|CIS2|FNAM|NNAM|QSTA': u'objectives',
        },
        b'ANAM': {
            b'CTDA|CIS1|CIS2|FNAM': u'qust_aliases',
            # ANAM is required, so piggyback off of it here to resolve QSTA
            b'QSTA': (u'targets', {
                b'CTDA|CIS1|CIS2': u'targets',
            }),
            b'NNAM': u'description',
        },
    })

#------------------------------------------------------------------------------
class _MelTintMasks(MelGroups):
    """Hacky way to allow a MelGroups of two MelGroups."""
    def __init__(self, attr):
        super(_MelTintMasks, self).__init__(attr,
            MelGroups(u'tint_textures',
                MelUInt16(b'TINI', u'tint_index'),
                MelString(b'TINT', u'tint_file'),
                MelUInt16(b'TINP', u'tint_mask_type'),
                MelFid(b'TIND', u'tint_preset_default'),
            ),
            MelGroups(u'tint_presets',
                MelFid(b'TINC', u'preset_color'),
                MelFloat(b'TINV', u'preset_default'),
                MelUInt16(b'TIRS', u'preset_index'),
            ),
        )
        self._init_sigs = {b'TINI'}

class _RaceDataFlags1(TrimmedFlags):
    """The Overlay/Override Head Part List flags are mutually exclusive."""
    __slots__ = ()
    def _clean_flags(self):
        if self.overlay_head_part_list and self.override_head_part_list:
            self.overlay_head_part_list = False

class MreRace(MelRecord):
    """Race."""
    rec_sig = b'RACE'

    class HeaderFlags(MelRecord.HeaderFlags):
        critter: bool = flag(19)    # maybe

    class _data_flags_1(_RaceDataFlags1):
        playable: bool
        facegen_head: bool
        child: bool
        tilt_front_back: bool
        tilt_left_right: bool
        no_shadow: bool
        swims: bool
        flies: bool
        walks: bool
        immobile: bool
        not_pushable: bool
        no_combat_in_water: bool
        no_rotating_to_head_track: bool
        dont_show_blood_spray: bool
        dont_show_blood_decal: bool
        uses_head_track_anim: bool
        spells_align_with_magic_mode: bool
        use_world_raycasts_for_footik: bool
        allow_ragdoll_collisions: bool
        regen_hp_in_combat: bool
        cant_open_doors: bool
        allow_pc_dialogue: bool
        no_knockdowns: bool
        allow_pickpocket: bool
        always_use_proxy_controller: bool
        dont_show_weapon_blood: bool
        overlay_head_part_list: bool
        override_head_part_list: bool
        can_pickup_items: bool
        allow_multiple_membrane_shaders: bool
        can_dual_wield: bool
        avoids_roads: bool

    class _data_flags_2(Flags):
        use_advanced_avoidance: bool = flag(0)
        non_hostile: bool = flag(1)
        allow_mounted_combat: bool = flag(4)

    class _equip_type_flags(TrimmedFlags):
        et_hand_to_hand_melee: bool
        et_one_hand_sword: bool
        et_one_hand_dagger: bool
        et_one_hand_axe: bool
        et_one_hand_mace: bool
        et_two_hand_sword: bool
        et_two_hand_axe: bool
        et_bow: bool
        et_staff: bool
        et_spell: bool
        et_shield: bool
        et_torch: bool
        et_crossbow: bool

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(), # required
        MelSpellCounter(),
        MelSpells(),
        MelFid(b'WNAM', u'race_skin'),
        MelBodtBod2(), # required
        MelKeywords(),
        MelRaceData(b'DATA', # required
            ['14b', '2s', '4f', 'I', '7f', 'I', '2i', 'f', 'i', '5f', 'i',
             '4f', 'I', '9f'], ('skills', [0] * 14), 'unknown1',
            u'maleHeight', u'femaleHeight', u'maleWeight', u'femaleWeight',
            (_data_flags_1, u'data_flags_1'), u'starting_health',
            u'starting_magicka', u'starting_stamina', u'base_carry_weight',
            u'base_mass', u'acceleration_rate', u'deceleration_rate',
            u'race_size', u'head_biped_object', u'hair_biped_object',
            u'injured_health_percentage', u'shield_biped_object',
            u'health_regen', u'magicka_regen', u'stamina_regen',
            u'unarmed_damage', u'unarmed_reach', u'body_biped_object',
            u'aim_angle_tolerance', u'flight_radius',
            u'angular_acceleration_tolerance', u'angular_tolerance',
            (_data_flags_2, u'data_flags_2'), (u'mount_offset_x', -63.479000),
            u'mount_offset_y', u'mount_offset_z',
            (u'dismount_offset_x', -50.0), u'dismount_offset_y',
            (u'dismount_offset_z', 65.0), u'mount_camera_offset_x',
            (u'mount_camera_offset_y', -300.0), u'mount_camera_offset_z',
            old_versions={u'14b2s4fI7fI2ifi5fi4fI'}),
        MelBaseR(b'MNAM', 'male_marker'), # required
        MelString(b'ANAM', u'male_skeletal_model'),
        # Texture hash - we have to give it a name for the distributor
        MelReadOnly(MelBase(b'MODT', u'male_hash')),
        MelBaseR(b'FNAM', 'female_marker'), # required
        MelString(b'ANAM', u'female_skeletal_model'),
        # Texture hash - we have to give it a name for the distributor
        MelReadOnly(MelBase(b'MODT', u'female_hash')),
        MelBase(b'NAM2', u'marker_nam2_1'),
        MelSorted(MelGroups(u'movement_type_names',
            MelString(b'MTNM', u'mt_name'),
        ), sort_by_attrs='mt_name'),
        # required
        MelStruct(b'VTCK', [u'2I'], (FID, u'maleVoice'), (FID, u'femaleVoice')),
        MelOptStruct(b'DNAM', [u'2I'], (FID, u'male_decapitate_armor'),
                     (FID, u'female_decapitate_armor')),
        MelOptStruct(b'HCLF', [u'2I'], (FID, u'male_default_hair_color'),
                     (FID, u'female_default_hair_color')),
        ##: Needs to be updated for total tint count, but not even xEdit can do
        # that right now
        MelUInt16(b'TINL', u'tint_count'),
        MelFloat(b'PNAM', u'facegen_main_clamp', set_default=0), # required
        MelFloat(b'UNAM', u'facegen_face_clamp', set_default=0), # required
        MelFid(b'ATKR', u'attack_race'),
        MelAttacks(),
        MelBaseR(b'NAM1', 'body_data_marker'), # required
        MelBaseR(b'MNAM', 'male_data_marker'), # required
        MelSorted(MelGroups(u'male_body_data',
            MelUInt32(b'INDX', u'body_part_index', set_default=0), # required
            MelModel(),
        ), sort_by_attrs='body_part_index'),
        MelBaseR(b'FNAM', 'female_data_marker'), # required
        MelSorted(MelGroups(u'female_body_data',
            MelUInt32(b'INDX', u'body_part_index', set_default=0), # required
            MelModel(),
        ), sort_by_attrs='body_part_index'),
        # These seem like unused leftovers from TES4/FO3, never occur in
        # vanilla or in any of the ~400 mod plugins I checked
        MelSorted(MelSimpleArray('hairs', MelFid(b'HNAM'))),
        MelSorted(MelSimpleArray('eyes', MelFid(b'ENAM'))),
        MelFid(b'GNAM', u'body_part_data', set_default=0), # required
        MelBase(b'NAM2', u'marker_nam2_2'),
        MelBaseR(b'NAM3', 'behavior_graph_marker'), # required
        MelBaseR(b'MNAM', 'male_graph_marker'), # required
        MelModel(b'MODL', 'male_behavior_graph'),
        MelBaseR(b'FNAM', 'female_graph_marker'), # required
        MelModel(b'MODL', 'female_behavior_graph'),
        MelFid(b'NAM4', u'material_type'),
        MelImpactDataset(b'NAM5'),
        MelFid(b'NAM7', u'decapitation_fx'),
        MelFid(b'ONAM', u'open_loot_sound'),
        MelFid(b'LNAM', u'close_loot_sound'),
        MelGroups(u'biped_object_names', ##: required, len should always be 32!
            MelString(b'NAME', u'bo_name'),
        ),
        MelSorted(MelGroups(u'movement_types',
            MelFid(b'MTYP', u'movement_type'),
            MelOptStruct(b'SPED', [u'11f'], u'override_left_walk',
                         u'override_left_run', u'override_right_walk',
                         u'override_right_run', u'override_forward_walk',
                         u'override_forward_run', u'override_back_walk',
                         u'override_back_run', u'override_rotate_walk',
                         u'override_rotate_run', u'unknown1'),
        ), sort_by_attrs='movement_type'),
        MelUInt32Flags(b'VNAM', u'equip_type_flags', _equip_type_flags),
        MelSorted(MelGroups(u'equip_slots',
            MelFid(b'QNAM', u'equip_slot'),
        ), sort_by_attrs='equip_slot'),
        MelFid(b'UNES', u'unarmed_equip_slot'),
        MelGroups(u'phoneme_target_names',
            MelString(b'PHTN', u'pt_name'),
        ),
        MelGroups(u'facefx_phonemes',
            MelTruncatedStruct(
                b'PHWT', [u'16f'], u'aah_lipbigaah_weight',
                u'bigaah_lipdst_weight', u'bmp_lipeee_weight',
                u'chjsh_lipfv_weight', u'dst_lipk_weight', u'eee_lipl_weight',
                u'eh_lipr_weight', u'fv_lipth_weight', u'i_weight',
                u'k_weight', u'n_weight', u'oh_weight', u'oohq_weight',
                u'r_weight', u'th_weight', u'w_weight', old_versions={u'8f'}),
        ),
        MelFid(b'WKMV', u'base_movement_default_walk'),
        MelFid(b'RNMV', u'base_movement_default_run'),
        MelFid(b'SWMV', u'base_movement_default_swim'),
        MelFid(b'FLMV', u'base_movement_default_fly'),
        MelFid(b'SNMV', u'base_movement_default_sneak'),
        MelFid(b'SPMV', u'base_movement_default_sprint'),
        MelBase(b'NAM0', u'male_head_data_marker'),
        MelBase(b'MNAM', u'male_head_parts_marker'),
        MelSorted(MelGroups(u'male_head_parts',
            MelUInt32(b'INDX', u'head_part_number'),
            MelFid(b'HEAD', u'head_part'),
        ), sort_by_attrs='head_part_number'),
        # The MPAVs are semi-decoded in xEdit, but including them seems wholly
        # unnecessary (too complex to edit, tons of flags, many unknowns)
        MelBase(b'MPAI', u'male_morph_unknown1'),
        MelBase(b'MPAV', u'male_nose_variants'),
        MelBase(b'MPAI', u'male_morph_unknown2'),
        MelBase(b'MPAV', u'male_brow_variants'),
        MelBase(b'MPAI', u'male_morph_unknown3'),
        MelBase(b'MPAV', u'male_eye_variants'),
        MelBase(b'MPAI', u'male_morph_unknown4'),
        MelBase(b'MPAV', u'male_lip_variants'),
        MelSorted(MelGroups(u'male_race_presets',
            MelFid(b'RPRM', u'preset_npc'),
        ), sort_by_attrs='preset_npc'),
        MelSorted(MelGroups(u'male_available_hair_colors',
            MelFid(b'AHCM', u'hair_color'),
        ), sort_by_attrs='hair_color'),
        MelSorted(MelGroups(u'male_face_texture_sets',
            MelFid(b'FTSM', u'face_texture_set'),
        ), sort_by_attrs='face_texture_set'),
        MelFid(b'DFTM', u'male_default_face_texture'),
        _MelTintMasks(u'male_tint_masks'),
        MelModel(b'MODL', 'male_head_model'),
        MelBase(b'NAM0', u'female_head_data_marker'),
        MelBase(b'FNAM', u'female_head_parts_marker'),
        MelSorted(MelGroups(u'female_head_parts',
            MelUInt32(b'INDX', u'head_part_number'),
            MelFid(b'HEAD', u'head_part'),
        ), sort_by_attrs='head_part_number'),
        # The MPAVs are semi-decoded in xEdit, but including them seems wholly
        # unnecessary (too complex to edit, tons of flags, many unknowns)
        MelBase(b'MPAI', u'female_morph_unknown1'),
        MelBase(b'MPAV', u'female_nose_variants'),
        MelBase(b'MPAI', u'female_morph_unknown2'),
        MelBase(b'MPAV', u'female_brow_variants'),
        MelBase(b'MPAI', u'female_morph_unknown3'),
        MelBase(b'MPAV', u'female_eye_variants'),
        MelBase(b'MPAI', u'female_morph_unknown4'),
        MelBase(b'MPAV', u'female_lip_variants'),
        MelSorted(MelGroups(u'female_race_presets',
            MelFid(b'RPRF', u'preset_npc'),
        ), sort_by_attrs='preset_npc'),
        MelSorted(MelGroups(u'female_available_hair_colors',
            MelFid(b'AHCF', u'hair_color'),
        ), sort_by_attrs='hair_color'),
        MelSorted(MelGroups(u'female_face_texture_sets',
            MelFid(b'FTSF', u'face_texture_set'),
        ), sort_by_attrs='face_texture_set'),
        MelFid(b'DFTF', u'female_default_face_texture'),
        _MelTintMasks(u'female_tint_masks'),
        MelModel(b'MODL', 'female_head_model'),
        MelFid(b'NAM8', u'morph_race'),
        MelRace(),
    ).with_distributor({
        b'DATA': {
            b'MNAM': (u'male_marker', {
                b'ANAM': u'male_skeletal_model',
                b'MODT': u'male_hash',
            }),
            b'FNAM': (u'female_marker', {
                b'ANAM': u'female_skeletal_model',
                b'MODT': u'female_hash',
            }),
            b'NAM2': u'marker_nam2_1',
        },
        b'NAM1': {
            b'MNAM': (u'male_data_marker', {
                b'INDX|MODL|MODT|MODS': u'male_body_data',
            }),
            b'FNAM': (u'female_data_marker', {
                b'INDX|MODL|MODT|MODS': u'female_body_data',
            }),
            b'NAM2': u'marker_nam2_2',
        },
        b'NAM3': {
            b'MNAM': (u'male_graph_marker', {
                b'MODL|MODT|MODS': u'male_behavior_graph',
            }),
            b'FNAM': (u'female_graph_marker', {
                b'MODL|MODT|MODS': u'female_behavior_graph',
            }),
        },
        b'NAM0': (u'male_head_data_marker', {
            b'MNAM': (u'male_head_parts_marker', {
                b'INDX|HEAD': u'male_head_parts',
                b'MPAI': [
                    (b'MPAI', u'male_morph_unknown1'),
                    (b'MPAV', u'male_nose_variants'),
                    (b'MPAI', u'male_morph_unknown2'),
                    (b'MPAV', u'male_brow_variants'),
                    (b'MPAI', u'male_morph_unknown3'),
                    (b'MPAV', u'male_eye_variants'),
                    (b'MPAI', u'male_morph_unknown4'),
                    (b'MPAV', u'male_lip_variants'),
                ],
                b'TINI|TINT|TINP|TIND|TINC|TINV|TIRS': u'male_tint_masks',
                b'MODL|MODT|MODS': u'male_head_model',
            }),
            # For some ungodly reason Bethesda inserted another NAM0 after the
            # male section. So we have to make a hierarchy where the second
            # NAM0 sits inside the dict of the first NAM0.
            b'NAM0': (u'female_head_data_marker', {
                b'FNAM': (u'female_head_parts_marker', {
                    b'INDX|HEAD': u'female_head_parts',
                    b'MPAI': [
                        (b'MPAI', u'female_morph_unknown1'),
                        (b'MPAV', u'female_nose_variants'),
                        (b'MPAI', u'female_morph_unknown2'),
                        (b'MPAV', u'female_brow_variants'),
                        (b'MPAI', u'female_morph_unknown3'),
                        (b'MPAV', u'female_eye_variants'),
                        (b'MPAI', u'female_morph_unknown4'),
                        (b'MPAV', u'female_lip_variants'),
                    ],
                    b'TINI|TINT|TINP|TIND|TINC|TINV|TIRS':
                        u'female_tint_masks',
                    b'MODL|MODT|MODS': u'female_head_model',
                }),
            }),
        }),
    })

#------------------------------------------------------------------------------
# Needs Updating
class MreRefr(MelRecord):
    """Placed Object."""
    rec_sig = b'REFR'

    class HeaderFlags(NavMeshFlags, VWDFlag, MelRecord.HeaderFlags):
        hidden_from_local_map: bool = flag(6)       # DOOR
        inaccessible: bool = flag(8)                # DOOR
        doesnt_light_water: bool = flag(8)          # LIGH
        hidden_from_local_map: bool = flag(9)       # ACTI, STAT, TREE, FLOR
        casts_shadows: bool = flag(9)               # LIGH
        motion_blur: bool = flag(9)                 # MSTT
        initially_disabled: bool = flag(11)
        sky_marker: bool = flag(13)                 # ACTI, STAT, TREE, FLOR
        full_lod: bool = flag(16)
        never_fades: bool = flag(16)                # LIGH
        doesnt_light_landscape: bool = flag(17)     # LIGH
        # 25: LIGH, ALCH, SCRL, AMMO, ARMO, INGR, KEYM, MISC, SLGM, WEAP
        no_ai_acquire: bool = flag(25)
        # NavMeshFlags 25, 27:
        # LIGH, ADDN, ALCH, SCRL, AMMO, ARMO, INGR, KEYM, MISC, SLGM, WEAP
        reflected_by_auto_water: bool = flag(28)
        # 29: ACTI, STAT, TREE, FLOR, CONT, DOOR, LIGH, MSTT, ADDN, ALCH, SCRL,
        #     AMMO, ARMO, INGR, KEYM, MISC, SLGM, WEAP
        dont_havok_settle: bool = flag(29)
        # 30:
        #  no_respawn: ACTI, STAT, TREE,FLOR, DOOR, LIGH, MSTT, ADDN, ALCH,
        #              SCRL, AMMO, ARMO, INGR, KEYM, MISC, SLGM, WEAP
        #  navmesh_ground: otherwise
        no_respawn: bool = flag(30)
        multi_bound: bool = flag(31)

    class _lockFlags(Flags):
        leveledLock: bool = flag(2)

    class _destinationFlags(Flags):
        noAlarm: bool

    class _parentActivate(Flags):
        parentActivateOnly: bool

    class reflectFlags(Flags):
        reflection: bool
        refraction: bool

    class roomDataFlags(Flags):
        hasImageSpace: bool = flag(6)
        hasLightingTemplate: bool = flag(7)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelFid(b'NAME','base'),
        MelOptStruct(b'XMBO', [u'3f'],'boundHalfExtentsX','boundHalfExtentsY','boundHalfExtentsZ'),
        MelOptStruct(b'XPRM', [u'f', u'f', u'f', u'f', u'f', u'f', u'f', u'I'],'primitiveBoundX','primitiveBoundY','primitiveBoundZ',
                     'primitiveColorRed','primitiveColorGreen','primitiveColorBlue',
                     'primitiveUnknown','primitiveType'),
        MelBase(b'XORD','xord_p'),
        MelOptStruct(b'XOCP', [u'9f'],'occlusionPlaneWidth','occlusionPlaneHeight',
                     'occlusionPlanePosX','occlusionPlanePosY','occlusionPlanePosZ',
                     'occlusionPlaneRot1','occlusionPlaneRot2','occlusionPlaneRot3',
                     'occlusionPlaneRot4'),
        MelArray('portalData',
            MelStruct(b'XPOD', [u'2I'], (FID, 'portalOrigin'),
                      (FID, 'portalDestination')),
        ),
        MelOptStruct(b'XPTL', [u'9f'],'portalWidth','portalHeight','portalPosX','portalPosY','portalPosZ',
                     'portalRot1','portalRot2','portalRot3','portalRot4'),
        MelGroup('bound_data',
            MelPartialCounter(MelStruct(b'XRMR', ['2B', '2s'],
                'linked_rooms_count', (roomDataFlags, 'room_flags'),
                'unknown1'),
                counters={'linked_rooms_count': 'linked_rooms'}),
            MelFid(b'LNAM', 'lightingTemplate'),
            MelFid(b'INAM', 'imageSpace'),
            MelSorted(MelFids('linked_rooms', MelFid(b'XLRM'))),
        ),
        MelBase(b'XMBP','multiboundPrimitiveMarker'),
        MelBase(b'XRGD','ragdollData'),
        MelBase(b'XRGB','ragdollBipedData'),
        MelFloat(b'XRDS', 'radius'),
        MelReflectedRefractedBy(),
        MelSorted(MelFids('litWaters', MelFid(b'XLTW'))),
        MelFid(b'XEMI', 'emittance'),
        MelTruncatedStruct(b'XLIG', ['4f', '4s'], 'fov90Delta', 'fadeDelta',
            'end_distance_cap', 'shadowDepthBias', 'unknown2',
            old_versions={'4f'}, is_optional=True),
        MelOptStruct(b'XALP', [u'B', u'B'],'cutoffAlpha','baseAlpha',),
        MelOptStruct(b'XTEL', [u'I', u'6f', u'I'],(FID,'destinationFid'),'destinationPosX',
                     'destinationPosY','destinationPosZ','destinationRotX',
                     'destinationRotY','destinationRotZ',
                     (_destinationFlags,'destinationFlags')),
        MelFids('teleportMessageBox', MelFid(b'XTNM')),
        MelFid(b'XMBR','multiboundReference'),
        MelWaterVelocities(),
        MelOptStruct(b'XCVL', [u'4s', u'f', u'4s'], u'unknown3', u'angleX', u'unknown4'),
        MelFid(b'XCZR', u'unknown5'),
        MelBase(b'XCZA', 'xcza_p',),
        MelFid(b'XCZC', u'unknown6'),
        MelRefScale(),
        MelFid(b'XSPC','spawnContainer'),
        MelActivateParents(),
        MelFid(b'XLIB','leveledItemBaseObject'),
        MelSInt32(b'XLCM', 'levelModifier'),
        MelFid(b'XLCN','persistentLocation',),
        MelUInt32(b'XTRI', 'collisionLayer'),
        # {>>Lock Tab for REFR when 'Locked' is Unchecked this record is not present <<<}
        MelTruncatedStruct(b'XLOC', [u'B', u'3s', u'I', u'B', u'3s', u'8s'], 'lockLevel', 'unused1',
                           (FID, 'lockKey'), (_lockFlags, 'lockFlags'),
                           'unused3', 'unused4',
                           old_versions={'B3sIB3s4s', 'B3sIB3s'}),
        MelFid(b'XEZN','encounterZone'),
        MelOptStruct(b'XNDP', [u'I', u'H', u'2s'], (FID, u'navMesh'),
            u'teleportMarkerTriangle', u'unknown7'),
        MelSimpleArray('locationRefType', MelFid(b'XLRT')),
        MelNull(b'XIS2',),
        MelOwnership(),
        MelSInt32(b'XCNT', 'count'),
        MelFloat(b'XCHG', u'charge'),
        MelFid(b'XLRL','locationReference'),
        MelEnableParent(),
        MelLinkedReferences(),
        MelGroup('patrolData',
            MelFloat(b'XPRD', 'idleTime'),
            MelBase(b'XPPA','patrolScriptMarker'),
            MelFid(b'INAM', 'idle'),
            *_leftovers,
            MelTopicData('topic_data'),
        ),
        MelActionFlags(),
        MelFloat(b'XHTW', 'headTrackingWeight'),
        MelFloat(b'XFVC', 'favorCost'),
        MelBase(b'ONAM','onam_p'),
        MelMapMarker(),
        MelFid(b'XATR', 'attachRef'),
        MelXlod(),
        MelRef3D(),
    )

#------------------------------------------------------------------------------
class MreRegn(MelRecord):
    """Region."""
    rec_sig = b'REGN'

    class HeaderFlags(MelRecord.HeaderFlags):
        border_region: bool = flag(6)

    class obflags(Flags):
        conform: bool = flag(0)
        paintVertices: bool = flag(1)
        sizeVariance: bool = flag(2)
        deltaX: bool = flag(3)
        deltaY: bool = flag(4)
        deltaZ: bool = flag(5)
        Tree: bool = flag(6)
        hugeRock: bool = flag(7)

    class sdflags(Flags):
        pleasant: bool = flag(0)
        cloudy: bool = flag(1)
        rainy: bool = flag(2)
        snowy: bool = flag(3)

    class rdatFlags(Flags):
        Override: bool

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'RCLR', [u'3B', u's'],'mapRed','mapBlue','mapGreen','unused1'),
        MelFid(b'WNAM','worldspace'),
        MelGroups('areas',
            MelUInt32(b'RPLI', 'edgeFalloff'),
            MelArray('points',
                MelStruct(b'RPLD', [u'2f'], 'posX', 'posY'),
            ),
        ),
        MelSorted(MelGroups('entries',
            MelStruct(b'RDAT', [u'I', u'2B', u'2s'], 'entryType', (rdatFlags, 'flags'),
                      'priority', 'unused1'),
            MelIcon(),
            MelRegnEntrySubrecord(7, MelFid(b'RDMO', 'music')),
            MelRegnEntrySubrecord(7, MelSorted(MelArray('sounds',
                MelStruct(b'RDSA', [u'2I', u'f'], (FID, 'sound'),
                          (sdflags, 'flags'), 'chance'),
            ), sort_by_attrs='sound')),
            MelRegnEntrySubrecord(4, MelString(b'RDMP', 'mapName')),
            MelRegnEntrySubrecord(2, MelArray('objects',
                MelStruct(b'RDOT',
                    [u'I', u'H', u'2s', u'f', u'4B', u'2H', u'5f', u'3H', u'2s', u'4s'], (FID, 'objectId'),
                    'parentIndex', 'unk1', 'density', 'clustering',
                    'minSlope', 'maxSlope', (obflags, 'flags'),
                    'radiusWRTParent', 'radius', 'minHeight', 'maxHeight',
                    'sink', 'sinkVar', 'sizeVar', 'angleVarX', 'angleVarY',
                    'angleVarZ', 'unk2', 'unk3'),
            )),
            MelRegnEntrySubrecord(6, MelSorted(MelArray('grasses',
                MelStruct(b'RDGS', [u'I', u'4s'], (FID, 'grass'), 'unknown'),
            ), sort_by_attrs='grass')),
            MelRegnEntrySubrecord(3, MelSorted(MelArray('weatherTypes',
                MelStruct(b'RDWT', [u'3I'], (FID, u'weather'), u'chance',
                          (FID, u'global')),
            ), sort_by_attrs='weather')),
        ), sort_by_attrs='entryType'),
    )

#------------------------------------------------------------------------------
class MreRela(MelRecord):
    """Relationship."""
    rec_sig = b'RELA'

    class HeaderFlags(MelRecord.HeaderFlags):
        secret: bool = flag(6)

    class RelationshipFlags(Flags):
        unknown_1: bool = flag(0)
        unknown_2: bool = flag(1)
        unknown_3: bool = flag(2)
        unknown_4: bool = flag(3)
        unknown_5: bool = flag(4)
        unknown_6: bool = flag(5)
        unknown_7: bool = flag(6)
        Secret: bool = flag(7)

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', [u'2I', u'H', u's', u'B', u'I'],(FID,'parent'),(FID,'child'),'rankType',
                  'unknown',(RelationshipFlags, u'relaFlags'),(FID,'associationType'),),
    )

#------------------------------------------------------------------------------
class MreRevb(MelRecord):
    """Reverb Parameters"""
    rec_sig = b'REVB'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', [u'2H', u'4b', u'6B'],'decayTimeMS','hfReferenceHZ','roomFilter',
                  'hfRoomFilter','reflections','reverbAmp','decayHFRatio',
                  'reflectDelayMS','reverbDelayMS','diffusion','density',
                  'unknown',),
        )

#------------------------------------------------------------------------------
class MreRfct(MelRecord):
    """Visual Effect."""
    rec_sig = b'RFCT'

    class RfctTypeFlags(Flags):
        rotate_to_face_target: bool
        attach_to_camera: bool
        inherit_rotation: bool

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', [u'3I'], (FID, u'rfct_art'), (FID, u'rfct_shader'),
            (RfctTypeFlags, u'rfct_flags')),
    )

#------------------------------------------------------------------------------
class MreScen(MelRecord):
    """Scene."""
    rec_sig = b'SCEN'

    class ScenFlags5(Flags):
        faceTarget: bool = flag(15)
        looping: bool = flag(16)
        headtrackPlayer: bool = flag(17)

    class ScenFlags3(Flags):
        deathPauseunsused: bool = flag(0)
        deathEnd: bool = flag(1)
        combatPause: bool = flag(2)
        combatEnd: bool = flag(3)
        dialoguePause: bool = flag(4)
        dialogueEnd: bool = flag(5)
        oBS_COMPause: bool = flag(6)
        oBS_COMEnd: bool = flag(7)

    class ScenFlags2(Flags):
        noPlayerActivation: bool
        optional: bool

    class ScenFlags1(Flags):
        beginonQuestStart: bool = flag(0)
        stoponQuestEnd: bool = flag(1)
        unknown3: bool = flag(2)
        repeatConditionsWhileTrue: bool = flag(3)
        interruptible: bool = flag(4)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelUInt32Flags(b'FNAM', u'flags', ScenFlags1),
        MelGroups('phases',
            MelNull(b'HNAM'),
            # Phase description. Always present, even if just a null-terminator
            MelString(b'NAM0', u'phase_desc',),
            MelConditionList('startConditions',),
            MelNull(b'NEXT'),
            MelConditionList('completionConditions',),
            # The next three are all leftovers
            _MelLeftovers('unused1'),
            MelNull(b'NEXT'),
            _MelLeftovers('unused2'),
            MelUInt32(b'WNAM', 'editorWidth'),
            MelNull(b'HNAM'),
        ),
        MelGroups('actors',
            MelUInt32(b'ALID', 'actorID'),
            MelUInt32Flags(b'LNAM', u'scenFlags2', ScenFlags2),
            MelUInt32Flags(b'DNAM', u'flags3', ScenFlags3),
        ),
        MelGroups('actions',
            MelUInt16(b'ANAM', 'actionType'),
            MelString(b'NAM0', u'action_desc',),
            MelUInt32(b'ALID', 'actorID',),
            MelBase(b'LNAM','lnam_p',),
            MelUInt32(b'INAM', 'index'),
            MelUInt32Flags(b'FNAM', u'flags', ScenFlags5),
            MelUInt32(b'SNAM', 'startPhase'),
            MelUInt32(b'ENAM', 'endPhase'),
            MelFloat(b'SNAM', 'timerSeconds'),
            MelFids('packages', MelFid(b'PNAM')),
            MelFid(b'DATA','topic'),
            MelUInt32(b'HTID', 'headtrackActorID'),
            MelFloat(b'DMAX', 'loopingMax'),
            MelFloat(b'DMIN', 'loopingMin'),
            MelUInt32(b'DEMO', 'emotionType'),
            MelUInt32(b'DEVA', 'emotionValue'),
            _MelLeftovers('unused'),
            MelNull(b'ANAM'),
        ),
        # The next three are all leftovers
        _MelLeftovers('unused1'),
        MelNull(b'NEXT'),
        _MelLeftovers('unused2'),
        MelFid(b'PNAM','quest',),
        MelUInt32(b'INAM', 'lastActionIndex'),
        MelBase(b'VNAM','vnam_p'),
        MelConditionList(),
    )

#------------------------------------------------------------------------------
class MreScrl(MelRecord):
    """Scroll."""
    rec_sig = b'SCRL'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelKeywords(),
        MelMdob(),
        MelEquipmentType(),
        MelDescription(),
        MelModel(),
        MelDestructible(),
        MelSoundPickupDrop(),
        MelStruct(b'DATA', [u'I', u'f'], u'itemValue', u'itemWeight'),
        MelSpit(),
        MelEffects(),
    )

#------------------------------------------------------------------------------
class MreShou(MelRecord):
    """Shout."""
    rec_sig = b'SHOU'

    class HeaderFlags(MelRecord.HeaderFlags):
        treat_spells_as_powers: bool = flag(7)

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelMdob(),
        MelDescription(),
        MelGroups('wordsOfPower',
            MelStruct(b'SNAM', [u'2I', u'f'], (FID, u'word'), (FID, u'spell'),
                      u'recoveryTime'),
        ),
    )

#------------------------------------------------------------------------------
class MreSlgm(MelRecord):
    """Soul Gem."""
    rec_sig = b'SLGM'

    class HeaderFlags(MelRecord.HeaderFlags):
        can_hold_npc_soul: bool = flag(17)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelSoundPickupDrop(),
        MelKeywords(),
        MelValueWeight(),
        MelUInt8(b'SOUL', u'soul'),
        MelUInt8(b'SLCP', 'capacity'),
        MelFid(b'NAM0','linkedTo'),
    )

#------------------------------------------------------------------------------
class MreSmbn(MelRecord):
    """Story Manager Branch Node."""
    rec_sig = b'SMBN'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'PNAM', u'sm_parent'),
        MelFid(b'SNAM', u'sm_child'),
        MelConditions(),
        MelSMFlags(),
        MelUInt32(b'XNAM', u'max_concurrent_quests'),
    )

#------------------------------------------------------------------------------
class MreSmen(MelRecord):
    """Story Manager Event Node."""
    rec_sig = b'SMEN'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'PNAM', u'sm_parent'),
        MelFid(b'SNAM', u'sm_child'),
        MelConditions(),
        MelSMFlags(),
        MelUInt32(b'XNAM', u'max_concurrent_quests'),
        MelUInt32(b'ENAM', u'sm_type'),
    )

#------------------------------------------------------------------------------
class MreSmqn(MelRecord):
    """Story Manager Quest Node."""
    rec_sig = b'SMQN'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'PNAM', u'sm_parent'),
        MelFid(b'SNAM', u'sm_child'),
        MelConditions(),
        MelSMFlags(with_quest_flags=True),
        MelUInt32(b'XNAM', u'max_concurrent_quests'),
        MelUInt32(b'MNAM', u'num_quests_to_run'),
        MelCounter(MelUInt32(b'QNAM', u'quest_count'), counts=u'sm_quests'),
        MelGroups(u'sm_quests',
            MelFid(b'NNAM', u'sm_quest'),
            MelUInt32(b'FNAM', u'sm_quest_flags'), # all unknown
            MelFloat(b'RNAM', u'hours_until_reset'),
        )
    )

#------------------------------------------------------------------------------
class MreSnct(MelRecord):
    """Sound Category."""
    rec_sig = b'SNCT'

    class SoundCategoryFlags(Flags):
        muteWhenSubmerged: bool
        shouldAppearOnMenu: bool

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt32Flags(b'FNAM', u'flags', SoundCategoryFlags),
        MelFid(b'PNAM','parent',),
        MelUInt16(b'VNAM', 'staticVolumeMultiplier'),
        MelUInt16(b'UNAM', 'defaultMenuValue'),
    )

#------------------------------------------------------------------------------
class MreSndr(MelRecord):
    """Sound Descriptor."""
    rec_sig = b'SNDR'

    melSet = MelSet(
        MelEdid(),
        MelBase(b'CNAM', 'descriptor_type'),
        MelFid(b'GNAM', 'descriptor_category'),
        MelSound(),
        MelGroups('sound_files',
            MelString(b'ANAM', 'sound_file_name',),
        ),
        MelFid(b'ONAM', 'output_model'),
        MelLString(b'FNAM', 'descriptor_string'),
        MelConditionList(),
        MelStruct(b'LNAM', ['s', 'B', 's', 'B'], 'unknown1', 'looping_type',
            'unknown2', 'rumble_send_value'),
        MelStruct(b'BNAM', ['2b', '2B', 'H'], 'pct_frequency_shift',
            'pct_frequency_variance', 'descriptor_priority', 'db_variance',
            'staticAtten'),
    )

#------------------------------------------------------------------------------
class MreSopm(MelRecord):
    """Sound Output Model."""
    rec_sig = b'SOPM'

    class _sopm_flags(Flags):
        attenuates_with_distance: bool
        allows_rumble: bool

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'NAM1', [u'B', u'2s', u'B'], (_sopm_flags, u'flags'),
            u'unknown1', u'reverbSendpct'),
        MelBase(b'FNAM', u'unused_fnam'),
        MelUInt32(b'MNAM', u'outputType'),
        MelBase(b'CNAM', u'unused_cnam'),
        MelBase(b'SNAM', u'unused_snam'),
        MelStruct(b'ONAM', [u'24B'], u'ch0_l', u'ch0_r', u'ch0_c', u'ch0_lFE',
            u'ch0_rL', u'ch0_rR', u'ch0_bL', u'ch0_bR', u'ch1_l', u'ch1_r',
            u'ch1_c', u'ch1_lFE', u'ch1_rL', u'ch1_rR', u'ch1_bL', u'ch1_bR',
            u'ch2_l', u'ch2_r', u'ch2_c', u'ch2_lFE', u'ch2_rL', u'ch2_rR',
            u'ch2_bL', u'ch2_bR'),
        MelStruct(b'ANAM', [u'4s', u'2f', u'5B', u'3s'], u'unknown2',
            u'minDistance', u'maxDistance', u'curve1', u'curve2', u'curve3',
            u'curve4', u'curve5', u'unknown3'),
    )

#------------------------------------------------------------------------------
class MreSoun(MelRecord):
    """Sound Marker."""
    rec_sig = b'SOUN'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelString(b'FNAM','soundFileUnused'), # leftover
        MelBase(b'SNDD','soundDataUnused'), # leftover
        MelFid(b'SDSC','soundDescriptor'),
    )

#------------------------------------------------------------------------------
class MreSpel(MelRecord):
    """Spell."""
    rec_sig = b'SPEL'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelKeywords(),
        MelMdob(),
        MelEquipmentType(),
        MelDescription(),
        MelSpit(),
        MelEffects(),
    )

#------------------------------------------------------------------------------
class MreSpgd(MelRecord):
    """Shader Particle Geometry."""
    rec_sig = b'SPGD'

    class _SpgdDataFlags(Flags):
        rain: bool
        snow: bool

    melSet = MelSet(
        MelEdid(),
        MelTruncatedStruct(b'DATA',
            [u'7f', u'4I', u'f'], 'gravityVelocity', 'rotationVelocity',
            'particleSizeX', 'particleSizeY', 'centerOffsetMin',
            'centerOffsetMax', 'initialRotationRange', 'numSubtexturesX',
            'numSubtexturesY', (_SpgdDataFlags, u'typeFlags'),
            'boxSize', 'particleDensity', old_versions={'7f3I'}),
        MelIcon(),
    )

#------------------------------------------------------------------------------
class MreStat(MelRecord):
    """Static."""
    rec_sig = b'STAT'

    class HeaderFlags(NavMeshFlags, VWDFlag, MelRecord.HeaderFlags):
        never_fades: bool = flag(2)
        has_tree_lod: bool = flag(6)
        addon_lod_object: bool = flag(7)
        hidden_from_local_map: bool = flag(9)
        unknown_11: bool = flag(11) # Present in Skyrim.esm, but can't be set
        unknown_16: bool = flag(16) # Present in Skyrim.esm, but can't be set
        use_hd_lod_texture: bool = flag(17)
        has_currents: bool = flag(19)
        is_marker: bool = flag(23)
        obstacle: bool = flag(25)
        show_in_world_map: bool = flag(28)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        if_sse(
            le_version=MelStruct(b'DNAM', [u'f', u'I'], 'maxAngle30to120',
                                 (FID, 'material')),
            se_version=MelTruncatedStruct(
                b'DNAM', [u'f', u'I', u'B', u'3s'], 'maxAngle30to120',
                (FID, 'material'), 'is_considered_snow', 'unused1',
                old_versions={'fI'}),
        ),
        # Contains null-terminated mesh filename followed by random data
        # up to 260 bytes and repeats 4 times
        MelBase(b'MNAM', 'distantLOD'),
        MelBase(b'ENAM', 'unknownENAM'),
    )

#------------------------------------------------------------------------------
class MreTact(MelRecord):
    """Talking Activator."""
    rec_sig = b'TACT'

    class HeaderFlags(MelRecord.HeaderFlags):
        hidden_from_local_map: bool = flag(9)
        random_animation_start: bool = flag(16)
        radio_station: bool = flag(17)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelColor(b'PNAM'),
        MelSound(),
        MelActiFlags(),
        MelFid(b'VNAM', 'voiceType'),
    )

#------------------------------------------------------------------------------
class MreTree(MelRecord):
    """Tree."""
    rec_sig = b'TREE'

    class HeaderFlags(VWDFlag, MelRecord.HeaderFlags):
        pass

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelModel(),
        MelIngredient(),
        MelSound(),
        MelSeasons(),
        MelFull(),
        MelStruct(b'CNAM', [u'12f'], u'trunk_flexibility', u'branch_flexibility',
                  u'trunk_amplitude', u'front_amplitude', u'back_amplitude',
                  u'side_amplitude', u'front_frequency', u'back_frequency',
                  u'side_frequency', u'leaf_flexibility', u'leaf_amplitude',
                  u'leaf_frequency'),
    )

#------------------------------------------------------------------------------
class MreTxst(MelRecord):
    """Texture Set."""
    rec_sig = b'TXST'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelString(b'TX00', 'diffuse_texture'),
        MelString(b'TX01', 'normal_gloss_texture'),
        MelString(b'TX02', 'environment_mask_subsurface_tint_texture'),
        MelString(b'TX03', 'glow_detail_map_texture'),
        MelString(b'TX04', 'height_texture'),
        MelString(b'TX05', 'environment_texture'),
        MelString(b'TX06', 'multilayer_texture'),
        MelString(b'TX07', 'backlight_mask_specular_texture'),
        MelDecalData(),
        MelTxstFlags()
    )

#------------------------------------------------------------------------------
class MreVtyp(MelRecord):
    """Voice Type."""
    rec_sig = b'VTYP'

    class VtypTypeFlags(Flags):
        allowDefaultDialog: bool
        female: bool

    melSet = MelSet(
        MelEdid(),
        MelUInt8Flags(b'DNAM', u'flags', VtypTypeFlags),
    )

#------------------------------------------------------------------------------
class MreWatr(MelRecord):
    """Water."""
    rec_sig = b'WATR'

    class WatrTypeFlags(Flags):
        causesDamage: bool

    _dnam_common = [ # Struct elements shared by DNAM in SLE and SSE
        'unknown1', 'unknown2', 'unknown3', 'unknown4',
        'specularPropertiesSunSpecularPower',
        'waterPropertiesReflectivityAmount', 'waterPropertiesFresnelAmount',
        'unknown5', 'fogPropertiesAboveWaterFogDistanceNearPlane',
        'fogPropertiesAboveWaterFogDistanceFarPlane',
        # Shallow Color
        'red_sc','green_sc','blue_sc','unknown_sc',
        # Deep Color
        'red_dc','green_dc','blue_dc','unknown_dc',
        # Reflection Color
        'red_rc','green_rc','blue_rc','unknown_rc',
        'unknown6', 'unknown7', 'unknown8', 'unknown9', 'unknown10',
        'displacementSimulatorStartingSize', 'displacementSimulatorForce',
        'displacementSimulatorVelocity', 'displacementSimulatorFalloff',
        'displacementSimulatorDampner', 'unknown11',
        'noisePropertiesNoiseFalloff', 'noisePropertiesLayerOneWindDirection',
        'noisePropertiesLayerTwoWindDirection',
        'noisePropertiesLayerThreeWindDirection',
        'noisePropertiesLayerOneWindSpeed', 'noisePropertiesLayerTwoWindSpeed',
        'noisePropertiesLayerThreeWindSpeed', 'unknown12', 'unknown13',
        'fogPropertiesAboveWaterFogAmount', 'unknown14',
        'fogPropertiesUnderWaterFogAmount',
        'fogPropertiesUnderWaterFogDistanceNearPlane',
        'fogPropertiesUnderWaterFogDistanceFarPlane',
        'waterPropertiesRefractionMagnitude',
        'specularPropertiesSpecularPower', 'unknown15',
        'specularPropertiesSpecularRadius',
        'specularPropertiesSpecularBrightness',
        'noisePropertiesLayerOneUVScale', 'noisePropertiesLayerTwoUVScale',
        'noisePropertiesLayerThreeUVScale',
        'noisePropertiesLayerOneAmplitudeScale',
        'noisePropertiesLayerTwoAmplitudeScale',
        'noisePropertiesLayerThreeAmplitudeScale',
        'waterPropertiesReflectionMagnitude',
        'specularPropertiesSunSparkleMagnitude',
        'specularPropertiesSunSpecularMagnitude',
        'depthPropertiesReflections', 'depthPropertiesRefraction',
        'depthPropertiesNormals', 'depthPropertiesSpecularLighting',
        'specularPropertiesSunSparklePower',
    ]

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelGroups('unused',
            MelString(b'NNAM','noiseMap',),
        ),
        MelUInt8(b'ANAM', 'opacity'),
        MelUInt8Flags(b'FNAM', u'flags', WatrTypeFlags),
        MelBase(b'MNAM','unused1'),
        MelFid(b'TNAM','material',),
        MelSound(),
        MelFid(b'XNAM','spell',),
        MelFid(b'INAM','imageSpace',),
        MelUInt16(b'DATA', 'damagePerSecond'),
        if_sse(
            le_version=MelStruct(b'DNAM',
              ['7f', '4s', '2f', '3B', 's', '3B', 's', '3B', 's', '4s', '43f'],
                                 *_dnam_common),
            se_version=MelTruncatedStruct(b'DNAM',
              ['7f', '4s', '2f', '3B', 's', '3B', 's', '3B', 's', '4s', '44f'],
                *(*_dnam_common, 'noisePropertiesFlowmapScale'),
                old_versions={'7f4s2f3Bs3Bs3Bs4s43f'}),
        ),
        MelBase(b'GNAM','unused2'),
        # Linear Velocity
        MelStruct(b'NAM0', [u'3f'],'linv_x','linv_y','linv_z',),
        # Angular Velocity
        MelStruct(b'NAM1', [u'3f'],'andv_x','andv_y','andv_z',),
        MelString(b'NAM2', 'noiseTextureLayer1'),
        MelString(b'NAM3', 'noiseTextureLayer2'),
        MelString(b'NAM4', 'noiseTextureLayer3'),
        sse_only(MelString(b'NAM5', 'flowNormalsNoiseTexture')),
    )

#------------------------------------------------------------------------------
class MreWeap(MelRecord):
    """Weapon"""
    rec_sig = b'WEAP'

    class HeaderFlags(NotPlayableFlag, MelRecord.HeaderFlags):
        pass

    class WeapFlags3(Flags):
        onDeath: bool

    class WeapFlags2(Flags):
        playerOnly: bool = flag(0)
        nPCsUseAmmo: bool = flag(1)
        noJamAfterReloadunused: bool = flag(2)
        unknown4: bool = flag(3)
        minorCrime: bool = flag(4)
        rangeFixed: bool = flag(5)
        notUsedinNormalCombat: bool = flag(6)
        unknown8: bool = flag(7)
        dont_use_3rd_person_IS_anim: bool = flag(8)
        unknown10: bool = flag(9)
        rumbleAlternate: bool = flag(10)
        unknown12: bool = flag(11)
        nonhostile: bool = flag(12)
        boundWeapon: bool = flag(13)

    class WeapFlags1(Flags):
        ignoresNormalWeaponResistance: bool = flag(0)
        automaticunused: bool = flag(1)
        hasScopeunused: bool = flag(2)
        cant_drop: bool = flag(3)
        hideBackpackunused: bool = flag(4)
        embeddedWeaponunused: bool = flag(5)
        dont_use_1st_person_IS_anim_unused: bool = flag(6)
        nonplayable: bool = flag(7)

    class MelWeapCrdt(MelTruncatedStruct):
        """Handle older truncated CRDT for WEAP subrecord.

        Old Skyrim format H2sfB3sI FormID is the last integer.

        New Format H2sfB3s4sI4s FormID is the integer prior to the last 4S.
        Bethesda did not append the record they inserted bytes which shifts the
        FormID 4 bytes."""
        def _pre_process_unpacked(self, unpacked_val):
            if len(unpacked_val) == 6:
                # old skyrim record, insert null bytes in the middle(!)
                crit_damage, crit_unknown1, crit_mult, crit_flags, \
                crit_unknown2, crit_effect = unpacked_val
                ##: Why use null3 instead of crit_unknown2?
                unpacked_val = (crit_damage, crit_unknown1, crit_mult,
                                crit_flags, null3, null4, crit_effect, null4)
            return super()._pre_process_unpacked(unpacked_val)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelEnchantment(),
        MelUInt16(b'EAMT', 'enchantPoints'),
        MelDestructible(),
        MelEquipmentType(),
        MelBids(),
        MelBamt(),
        MelSoundPickupDrop(),
        MelKeywords(),
        MelDescription(),
        MelModel(b'MOD3', 'model2'),
        MelBase(b'NNAM','unused1'),
        MelImpactDataset(b'INAM'),
        MelFid(b'WNAM','firstPersonModelObject',),
        MelSound(),
        MelFid(b'XNAM','attackSound2D',),
        MelFid(b'NAM7','attackLoopSound',),
        MelFid(b'TNAM','attackFailSound',),
        MelFid(b'UNAM','idleSound',),
        MelFid(b'NAM9','equipSound',),
        MelFid(b'NAM8','unequipSound',),
        MelStruct(b'DATA', [u'I', u'f', u'H'],'value','weight','damage',),
        MelStruct(b'DNAM', ['B', '3s', '2f', 'H', '2s', 'f', '4s', '4B', '2f',
                            '2I', '5f', '12s', 'i', '8s', 'i', '4s', 'f'],
                  'animationType', 'dnamUnk1', 'speed', 'reach',
                  (WeapFlags1, u'dnamFlags1'), u'dnamUnk2',
                  u'sightFOV', u'dnamUnk3', u'baseVATSToHitChance',
                  u'attackAnimation', u'numProjectiles',
                  u'embeddedWeaponAVunused', u'minRange', u'maxRange',
                  u'onHit', (WeapFlags2, u'dnamFlags2'),
                  u'animationAttackMultiplier', u'dnamUnk4',
                  u'rumbleLeftMotorStrength', u'rumbleRightMotorStrength',
                  u'rumbleDuration', u'dnamUnk5', u'skill',
                  u'dnamUnk6', u'resist', u'dnamUnk7', u'stagger'),
        if_sse(
            le_version=MelStruct(b'CRDT', ['H', '2s', 'f', 'B', '3s', 'I'],
                'criticalDamage', 'crdtUnk1', 'criticalMultiplier',
                (WeapFlags3, 'criticalFlags'), 'crdtUnk2',
                (FID, 'criticalEffect')),
            se_version=MelWeapCrdt(b'CRDT',
                ['H', '2s', 'f', 'B', '3s', '4s', 'I', '4s'], 'criticalDamage',
                'crdtUnk1', 'criticalMultiplier',
                (WeapFlags3, 'criticalFlags'), 'crdtUnk2', 'crdtUnk3',
                (FID, 'criticalEffect'), 'crdtUnk4',
                old_versions={'H2sfB3sI'}),
        ),
        MelUInt32(b'VNAM', 'detectionSoundLevel'),
        MelFid(b'CNAM','template',),
    )

#------------------------------------------------------------------------------
class MreWoop(MelRecord):
    """Word of Power."""
    rec_sig = b'WOOP'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelLString(b'TNAM','translation'),
    )

#------------------------------------------------------------------------------
class MreWrld(AMreWrld):
    """Worldspace."""
    ref_types = MreCell.ref_types
    exterior_temp_extra = [b'LAND', b'NAVM']
    wrld_children_extra = [b'CELL'] # CELL for the persistent block


    class WrldFlags2(Flags):
        smallWorld: bool = flag(0)
        noFastTravel: bool = flag(1)
        unknown3: bool = flag(2)
        noLODWater: bool = flag(3)
        noLandscape: bool = flag(4)
        unknown6: bool = flag(5)
        fixedDimensions: bool = flag(6)
        noGrass: bool = flag(7)

    class WrldFlags1(Flags):
        useLandData: bool = flag(0)
        useLODData: bool = flag(1)
        useMapData: bool = flag(2)
        useWaterData: bool = flag(3)
        useClimateData: bool = flag(4)
        useImageSpaceDataunused: bool = flag(5)
        useSkyCell: bool = flag(6)

    melSet = MelSet(
        MelEdid(),
        if_sse(le_version=MelNull(b'RNAM'), # unused
               se_version=MelGroups('large_references',
                   MelArray('large_refs', MelStruct(b'RNAM', ['I', '2h'],
                       (FID, 'lr_ref'), 'lr_y', 'lr_x'),
                       prelude=MelPartialCounter(MelStruct(b'RNAM',
                           ['2h', 'I'], 'lr_grid_y', 'lr_grid_x',
                           'large_refs_count'),
                           counters={'large_refs_count': 'large_refs'})))),
        MelBase(b'MHDT','maxHeightData'),
        MelFull(),
        # Fixed Dimensions Center Cell
        MelOptStruct(b'WCTR', [u'2h'],'fixedX','fixedY',),
        MelFid(b'LTMP','interiorLighting',),
        MelFid(b'XEZN','encounterZone',),
        MelFid(b'XLCN','location',),
        MelGroup('parent',
            MelFid(b'WNAM','worldspace',),
            MelStruct(b'PNAM', [u'B', u's'],(WrldFlags1, u'parentFlags'),'unknown',),
        ),
        MelFid(b'CNAM','climate',),
        MelFid(b'NAM2','water',),
        MelFid(b'NAM3', 'lod_water_type'),
        MelFloat(b'NAM4', u'lODWaterHeight'),
        MelOptStruct(b'DNAM', [u'2f'],'defaultLandHeight',
                     'defaultWaterHeight',),
        MelIcon(u'mapImage'),
        MelModel(b'MODL', 'cloudModel'),
        MelTruncatedStruct(b'MNAM', [u'2i', u'4h', u'3f'], 'usableDimensionsX',
                           'usableDimensionsY', 'cellCoordinatesX',
                           'cellCoordinatesY', 'seCellX', 'seCellY',
                           'cameraDataMinHeight', 'cameraDataMaxHeight',
                           'cameraDataInitialPitch', is_optional=True,
                           old_versions={'2i4h2f', '2i4h'}),
        MelStruct(b'ONAM', [u'4f'],'worldMapScale','cellXOffset','cellYOffset',
                  'cellZOffset',),
        MelFloat(b'NAMA', 'distantLODMultiplier'),
        MelUInt8Flags(b'DATA', u'dataFlags', WrldFlags2),
        MelWorldBounds(),
        MelFid(b'ZNAM','music',),
        MelString(b'NNAM','canopyShadowunused'),
        MelString(b'XNAM','waterNoiseTexture'),
        MelString(b'TNAM','hDLODDiffuseTexture'),
        MelString(b'UNAM','hDLODNormalTexture'),
        MelString(b'XWEM','waterEnvironmentMapunused'),
        MelNull(b'OFST'), # Not even CK/xEdit can recalculate these right now
    )

#------------------------------------------------------------------------------
# Many Things Marked MelBase that need updated
class MreWthr(MelRecord):
    """Weather"""
    rec_sig = b'WTHR'

    class WthrFlags2(Flags):
        layer_0: bool = flag(0)
        layer_1: bool = flag(1)
        layer_2: bool = flag(2)
        layer_3: bool = flag(3)
        layer_4: bool = flag(4)
        layer_5: bool = flag(5)
        layer_6: bool = flag(6)
        layer_7: bool = flag(7)
        layer_8: bool = flag(8)
        layer_9: bool = flag(9)
        layer_10: bool = flag(10)
        layer_11: bool = flag(11)
        layer_12: bool = flag(12)
        layer_13: bool = flag(13)
        layer_14: bool = flag(14)
        layer_15: bool = flag(15)
        layer_16: bool = flag(16)
        layer_17: bool = flag(17)
        layer_18: bool = flag(18)
        layer_19: bool = flag(19)
        layer_20: bool = flag(20)
        layer_21: bool = flag(21)
        layer_22: bool = flag(22)
        layer_23: bool = flag(23)
        layer_24: bool = flag(24)
        layer_25: bool = flag(25)
        layer_26: bool = flag(26)
        layer_27: bool = flag(27)
        layer_28: bool = flag(28)
        layer_29: bool = flag(29)
        layer_30: bool = flag(30)
        layer_31: bool = flag(31)

    class WthrFlags1(Flags):
        weatherPleasant: bool = flag(0)
        weatherCloudy: bool = flag(1)
        weatherRainy: bool = flag(2)
        weatherSnow: bool = flag(3)
        skyStaticsAlwaysVisible: bool = flag(4)
        skyStaticsFollowsSunPosition: bool = flag(5)

    melSet = MelSet(
        MelEdid(),
        MelString(b'\x300TX','cloudTextureLayer_0'),
        MelString(b'\x310TX','cloudTextureLayer_1'),
        MelString(b'\x320TX','cloudTextureLayer_2'),
        MelString(b'\x330TX','cloudTextureLayer_3'),
        MelString(b'\x340TX','cloudTextureLayer_4'),
        MelString(b'\x350TX','cloudTextureLayer_5'),
        MelString(b'\x360TX','cloudTextureLayer_6'),
        MelString(b'\x370TX','cloudTextureLayer_7'),
        MelString(b'\x380TX','cloudTextureLayer_8'),
        MelString(b'\x390TX','cloudTextureLayer_9'),
        MelString(b'\x3A0TX','cloudTextureLayer_10'),
        MelString(b'\x3B0TX','cloudTextureLayer_11'),
        MelString(b'\x3C0TX','cloudTextureLayer_12'),
        MelString(b'\x3D0TX','cloudTextureLayer_13'),
        MelString(b'\x3E0TX','cloudTextureLayer_14'),
        MelString(b'\x3F0TX','cloudTextureLayer_15'),
        MelString(b'\x400TX','cloudTextureLayer_16'),
        MelString(b'A0TX','cloudTextureLayer_17'),
        MelString(b'B0TX','cloudTextureLayer_18'),
        MelString(b'C0TX','cloudTextureLayer_19'),
        MelString(b'D0TX','cloudTextureLayer_20'),
        MelString(b'E0TX','cloudTextureLayer_21'),
        MelString(b'F0TX','cloudTextureLayer_22'),
        MelString(b'G0TX','cloudTextureLayer_23'),
        MelString(b'H0TX','cloudTextureLayer_24'),
        MelString(b'I0TX','cloudTextureLayer_25'),
        MelString(b'J0TX','cloudTextureLayer_26'),
        MelString(b'K0TX','cloudTextureLayer_27'),
        MelString(b'L0TX','cloudTextureLayer_28'),
        MelBase(b'DNAM', 'unused1'),
        MelBase(b'CNAM', 'unused2'),
        MelBase(b'ANAM', 'unused3'),
        MelBase(b'BNAM', 'unused4'),
        MelBase(b'LNAM','lnam_p'),
        MelFid(b'MNAM','precipitationType',),
        MelFid(b'NNAM','visualEffect',),
        MelBase(b'ONAM', 'unused5'),
        MelArray('cloudSpeedY',
            MelUInt8(b'RNAM', 'cloud_speed_layer'),
        ),
        MelArray('cloudSpeedX',
            MelUInt8(b'QNAM', 'cloud_speed_layer'),
        ),
        MelArray('cloudColors',
            MelWthrColors(b'PNAM'),
        ),
        MelArray('cloudAlphas',
            MelStruct(b'JNAM', [u'4f'], 'sunAlpha', 'dayAlpha', 'setAlpha',
                      'nightAlpha'),
        ),
        MelArray('daytimeColors',
            MelWthrColors(b'NAM0'),
        ),
        MelStruct(b'FNAM', [u'8f'],'dayNear','dayFar','nightNear','nightFar',
                  'dayPower','nightPower','dayMax','nightMax',),
        MelStruct(b'DATA', [u'B', u'2s', u'16B'],'windSpeed','unknown','transDelta',
                  'sunGlare','sunDamage','precipitationBeginFadeIn',
                  'precipitationEndFadeOut','thunderLightningBeginFadeIn',
                  'thunderLightningEndFadeOut','thunderLightningFrequency',
                  (WthrFlags1, u'wthrFlags1'),'red','green','blue',
                  'visualEffectBegin','visualEffectEnd',
                  'windDirection','windDirectionRange',),
        MelUInt32Flags(b'NAM1', u'wthrFlags2', WthrFlags2),
        MelGroups('sounds',
            MelStruct(b'SNAM', [u'2I'], (FID, 'sound'), 'type'),
        ),
        MelSorted(MelFids('skyStatics', MelFid(b'TNAM'))),
        MelStruct(b'IMSP', [u'4I'], (FID, 'image_space_sunrise'),
                  (FID, 'image_space_day'), (FID, 'image_space_sunset'),
                  (FID, 'image_space_night'),),
        sse_only(MelOptStruct(
            b'HNAM', [u'4I'], (FID, 'volumetricLightingSunrise'),
            (FID, 'volumetricLightingDay'), (FID, 'volumetricLightingSunset'),
            (FID, 'volumetricLightingNight'))),
        MelGroups('wthrAmbientColors',
            MelDalc(),
        ),
        MelBase(b'NAM2', 'unused6'),
        MelBase(b'NAM3', 'unused7'),
        MelModel(b'MODL', 'aurora'),
        sse_only(MelFid(b'GNAM', 'sunGlareLensFlare')),
    )
