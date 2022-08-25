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
from ...bolt import Flags, structs_cache, TrimmedFlags
from ...brec import MelRecord, MelGroups, MelStruct, FID, MelAttx, MelRace, \
    MelGroup, MelString, AMreLeveledList, MelSet, MelFid, MelNull, \
    MelOptStruct, MelFids, AMreHeader, MelBase, MelSimpleArray, MelWeight, \
    AMreGmst, MelLString, MelMODS, MelColorInterpolator, MelRegions, \
    MelValueInterpolator, MelUnion, AttrValDecider, MelRegnEntrySubrecord, \
    PartialLoadDecider, FlagDecider, MelFloat, MelSInt8, MelSInt32, MelUInt8, \
    MelUInt16, MelUInt32, MelActionFlags, MelCounter, MelRaceData, MelBaseR, \
    MelPartialCounter, MelBounds, null3, null4, MelSequential, MelKeywords, \
    MelTruncatedStruct, MelIcons, MelIcons2, MelIcon, MelIco2, MelEdid, \
    MelFull, MelArray, MelWthrColors, MelFactions, MelReadOnly, MelRelations, \
    AMreActor, AMreWithItems, MelRef3D, MelXlod, MelActiFlags, AMelNvnm, \
    MelWorldBounds, MelEnableParent, MelRefScale, MelMapMarker, MelMdob, \
    MelEnchantment, MelDecalData, MelDescription, MelSInt16, MelSkipInterior, \
    MelSoundPickupDrop, MelActivateParents, BipedFlags, MelColor, \
    MelColorO, MelSpells, MelFixedString, MelUInt8Flags, MelUInt16Flags, \
    MelUInt32Flags, MelOwnership, MelClmtWeatherTypes, AMelVmad, \
    MelActorSounds, MelFactionRanks, MelSorted, MelReflectedRefractedBy, \
    perk_effect_key, MelValueWeight, MelSound, MelWaterType, \
    MelSoundActivation, MelInteractionKeyword, MelConditionList, MelAddnDnam, \
    MelConditions, ANvnmContext, MelNodeIndex, MelEquipmentType, MelAlchEnit, \
    MelEffects, AMelLLItems, MelUnloadEvent, MelShortName, AVmadContext, \
    MelPerkData, MelNextPerk, PerkEpdfDecider, MelPerkParamsGroups, MelBids, \
    MelArmaDnam, MelArmaModels, MelArmaSkins, MelAdditionalRaces, MelBamt, \
    MelFootstepSound, MelArtObject, MelTemplateArmor, MelArtType, \
    MelAspcRdat, MelAspcBnam, MelAstpTitles, MelAstpData, MelBookText, \
    MelBookDescription, MelInventoryArt, MelUnorderedGroups, MelExtra, \
    MelImageSpaceMod, MelClmtTiming, MelClmtTextures, MelCobjOutput, \
    MelSoundClose, AMelItems, MelContData, MelCpthShared, MelDoorFlags, \
    MelRandomTeleports, MelSoundLooping, MelDualData, MelEqupPnam
from ...exception import ModSizeError

_is_sse = bush.game.fsName in (
    'Skyrim Special Edition', 'Skyrim VR', 'Enderal Special Edition',
    'Skyrim Special Edition MS')
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
        # Carry forward the one usable legacy flag - but don't overwrite
        # the non-playable status if it's already set at the record level
        record.flags1.isNotPlayable |= record.legacy_flags.non_playable

class MelBodtBod2(MelSequential):
    """Handler for BODT and BOD2 subrecords. Reads both types, but writes only
    BOD2."""
    _bp_flags = BipedFlags.from_names()
    # Used when loading BODT subrecords - #4 is the only one we care about
    _legacy_flags = TrimmedFlags.from_names(
        (0, 'modulates_voice'), # From ARMA
        (4, 'non_playable'), # From ARMO
    )

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
    _atk_flags = Flags.from_names(u'ignoreWeapon', u'bashAttack',
                                  u'powerAttack', u'leftAttack',
                                  u'rotatingAttack')

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
class MelDalc(MelTruncatedStruct):
    """Handles the common DALC subrecord."""
    def __init__(self):
        super().__init__(b'DALC', ['28B', 'f'], 'redXplus', 'greenXplus',
            'blueXplus', 'unknownXplus', 'redXminus', 'greenXminus',
            'blueXminus', 'unknownXminus', 'redYplus', 'greenYplus',
            'blueYplus', 'unknownYplus', 'redYminus', 'greenYminus',
            'blueYminus', 'unknownYminus', 'redZplus', 'greenZplus',
            'blueZplus', 'unknownZplus', 'redZminus', 'greenZminus',
            'blueZminus', 'unknownZminus', 'redSpec', 'greenSpec', 'blueSpec',
            'unknownSpec', 'fresnelPower', old_versions={'28B'})

#------------------------------------------------------------------------------
class MelDestructible(MelGroup):
    """Represents a collection of destruction-related subrecords."""
    _dest_stage_flags = Flags.from_names('cap_damage', 'disable', 'destroy',
                                         'ignore_external_damage')

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
            # The next four are leftovers from earlier CK versions
            MelBase(b'SCHR', u'unused1'),
            MelBase(b'SCTX', u'unused2'),
            MelBase(b'QNAM', u'unused3'),
            MelBase(b'TNAM', u'unused4'),
            MelTopicData(u'idle_topic_data'),
        )

#------------------------------------------------------------------------------
class MelItems(AMelItems):
    """Handles the COCT/CNTO/COED subrecords defining items."""

#------------------------------------------------------------------------------
class MelLinkedReferences(MelSorted):
    """The Linked References for a reference record (REFR, ACHR, etc.)."""
    def __init__(self):
        super(MelLinkedReferences, self).__init__(
            MelGroups(u'linked_references',
                MelStruct(b'XLKR', [u'2I'], (FID, u'keyword_ref'),
                          (FID, u'linked_ref')),
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
        super(MelLocation, self).__init__({
            (0, 1, 4, 6): MelOptStruct(sub_sig, [u'i', u'I', u'i'], u'location_type',
                (FID, u'location_value'), u'location_radius'),
            (2, 3, 7, 10, 11, 12): MelOptStruct(sub_sig, [u'i', u'4s', u'i'],
                u'location_type', u'location_value', u'location_radius'),
            5: MelOptStruct(sub_sig, [u'i', u'I', u'i'], u'location_type',
                u'location_value', u'location_radius'),
            (8, 9): MelOptStruct(sub_sig, [u'3i'], u'location_type',
                u'location_value', u'location_radius'),
            }, decider=PartialLoadDecider(
                loader=MelSInt32(sub_sig, u'location_type'),
                decider=AttrValDecider(u'location_type'))
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
    _node_flags = Flags.from_names(u'sm_random', u'no_child_warn')
    _quest_flags = Flags.from_names(
        u'do_all_before_repeating',
        u'shares_event',
        u'num_quests_to_run'
    )

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
        super(MelSpellCounter, self).__init__(
            MelUInt32(b'SPCT', u'spell_count'), counts=u'spells')

#------------------------------------------------------------------------------
class MelSpit(MelStruct):
    """Handles the SPIT subrecord shared between SCRL and SPEL."""
    spit_flags = Flags.from_names(
        (0,  u'manualCostCalc'),
        (17, u'pcStartSpell'),
        (19, u'areaEffectIgnoresLOS'),
        (20, u'ignoreResistance'),
        (21, u'noAbsorbReflect'),
        (23, u'noDualCastModification'),
    )

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
                0: MelStruct(b'PDTO', [u'2I'], u'data_type',
                    (FID, u'topic_ref')),
                1: MelStruct(b'PDTO', [u'I', u'4s'], u'data_type', u'topic_subtype'),
            }, decider=PartialLoadDecider(
                loader=MelUInt32(b'PDTO', u'data_type'),
                decider=AttrValDecider(u'data_type'))),
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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAact(MelRecord):
    """Action."""
    rec_sig = b'AACT'
    melSet = MelSet(
        MelEdid(),
        MelColorO(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAchr(MelRecord):
    """Placed NPC."""
    rec_sig = b'ACHR'

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
        MelBase(b'SCHR', u'unused_schr'),
        MelBase(b'SCDA', u'unused_scda'),
        MelBase(b'SCTX', u'unused_sctx'),
        MelBase(b'QNAM', u'unused_qnam'),
        MelBase(b'SCRO', u'unused_scro'),
        MelTopicData(u'topic_data'),
        MelFid(b'TNAM', u'ref_topic'),
        MelSInt32(b'XLCM', u'level_modifier'),
        MelFid(b'XMRC', u'merchant_container'),
        MelSInt32(b'XCNT', u'ref_count'),
        MelFloat(b'XRDS', u'ref_radius'),
        MelFloat(b'XHLP', u'ref_health'),
        MelLinkedReferences(),
        MelActivateParents(),
        MelStruct(b'XCLP', [u'3B', u's', u'3B', u's'], u'start_color_red', u'start_color_green',
                  u'start_color_blue', u'start_color_unused', u'end_color_red',
                  u'end_color_green', u'end_color_blue', u'end_color_unused'),
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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreActi(MelRecord):
    """Activator."""
    rec_sig = b'ACTI'

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
        MelAddnDnam(),
    )
    __slots__ = melSet.getSlotsUsed()

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAmmo(MelRecord):
    """Ammunition."""
    rec_sig = b'AMMO'

    AmmoTypeFlags = Flags.from_names('notNormalWeapon', 'nonPlayable',
                                     'nonBolt')

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArma(MelRecord):
    """Armor Addon."""
    rec_sig = b'ARMA'

    melSet = MelSet(
        MelEdid(),
        MelBodtBod2(),
        MelRace(),
        MelArmaDnam(),
        MelArmaModels(MelModel),
        MelArmaSkins(),
        MelAdditionalRaces(),
        MelFootstepSound(),
        MelArtObject(),
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
    __slots__ = melSet.getSlotsUsed()

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreBook(MelRecord):
    """Book."""
    rec_sig = b'BOOK'

    _book_type_flags = Flags.from_names('teaches_skill', 'cant_be_taken',
                                        'teaches_spell')

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreBptd(MelRecord):
    """Body Part Data."""
    rec_sig = b'BPTD'

    _bpnd_flags = Flags.from_names('severable', 'ik_data', 'ik_biped_data',
        'explodable', 'ik_is_head','ik_headtracking',' to_hit_chance_absolute')

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
                (FID, 'bpnd_severable_impact_data_set'),
                (FID, 'bpnd_explodable_impact_data_set'),
                'bpnd_severable_decal_count', 'bpnd_explodable_decal_count',
                'bpnd_unused', 'bpnd_limb_replacement_scale'),
            MelString(b'NAM1', 'limb_replacement_model'),
            MelString(b'NAM4', 'gore_effects_target_bone'),
            # Ignore texture hashes - they're only an optimization, plenty of
            # records in Skyrim.esm are missing them
            MelNull(b'NAM5'),
        ), sort_by_attrs='part_node'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCams(MelRecord):
    """Camera Shot."""
    rec_sig = b'CAMS'

    _cams_flags = Flags.from_names('position_follows_location',
        'rotation_follows_target', 'dont_follow_bone', 'first_person_camera',
        'no_tracer', 'start_at_time_zero')

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCell(MelRecord):
    """Cell."""
    rec_sig = b'CELL'
    _has_duplicate_attrs = True # XWCS is an older version of XWCN

    CellDataFlags1 = Flags.from_names(
        (0,'isInterior'),
        (1,'hasWater'),
        (2,'cantFastTravel'),
        (3,'noLODWater'),
        (5,'publicPlace'),
        (6,'handChanged'),
        (7,'showSky'),
    )

    CellDataFlags2 = Flags.from_names('useSkyLighting')

    CellInheritedFlags = Flags.from_names(
        (0, 'ambientColor'),
        (1, 'directionalColor'),
        (2, 'fogColor'),
        (3, 'fogNear'),
        (4, 'fogFar'),
        (5, 'directionalRotation'),
        (6, 'directionalFade'),
        (7, 'clipDistance'),
        (8, 'fogPower'),
        (9, 'fogMax'),
        (10, 'lightFadeDistances'),
    )

    _land_flags = TrimmedFlags.from_names('quad1', 'quad2', 'quad3', 'quad4')

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelTruncatedStruct(b'DATA', [u'2B'], (CellDataFlags1, u'flags'),
                           (CellDataFlags2, u'skyFlags'),
                           old_versions={'B'}),
        ##: The other games skip this in interiors - why / why not here?
        # None defaults here are on purpose - XCLC does not necessarily exist,
        # but 0 is a valid value for both coordinates (duh)
        MelOptStruct(b'XCLC', [u'2i', u'I'], (u'posX', None), (u'posY', None),
            (_land_flags, u'land_flags')),
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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClas(MelRecord):
    """Class."""
    rec_sig = b'CLAS'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelIcons(),
        MelStruct(b'DATA', [u'4s', u'b', u'19B', u'f', u'I', u'4B'],'unknown','teaches','maximumtraininglevel',
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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClfm(MelRecord):
    """Color."""
    rec_sig = b'CLFM'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelColorO(),
        MelUInt32(b'FNAM', 'playable'), # actually a bool, stored as uint32
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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCont(AMreWithItems):
    """Container."""
    rec_sig = b'CONT'

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCpth(MelRecord):
    """Camera Path"""
    rec_sig = b'CPTH'

    melSet = MelSet(
        MelEdid(),
        MelConditionList(),
        MelCpthShared(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCsty(MelRecord):
    """Combat Style."""
    rec_sig = b'CSTY'

    _csty_flags = Flags.from_names('dueling', 'flanking',
        'allow_dual_wielding')

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
        MelStruct(b'CSME', ['8f'], 'melee_attack_staggered_mult',
            'melee_power_attack_staggered_mult',
            'melee_power_attack_blocking_mult',
            'melee_bash_mult', 'melee_bash_recoil_mult',
            'melee_bash_attack_mult', 'melee_bash_power_attack_mult',
            'melee_special_attack_mult'),
        MelStruct(b'CSCR', ['4f'], 'close_range_circle_mult',
            'close_range_fallback_mult', 'close_range_flank_distance',
            'close_range_stalk_time'),
        MelFloat(b'CSLR', 'long_range_strafe_mult'),
        MelStruct(b'CSFL', ['8f'], 'flight_hover_chance',
            'flight_dive_bomb_chance', 'flight_ground_attack_chance',
            'flight_hover_time', 'flight_ground_attack_time',
            'flight_perch_attack_chance', 'flight_perch_attack_time',
            'flight_flying_attack_chance'),
        MelUInt32Flags(b'DATA', 'csty_flags', _csty_flags),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDial(MelRecord):
    """Dialogue."""
    rec_sig = b'DIAL'

    DialTopicFlags = Flags.from_names('doAllBeforeRepeating')

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelFloat(b'PNAM', 'priority',),
        MelFid(b'BNAM','branch',),
        MelFid(b'QNAM','quest',),
        MelStruct(b'DATA', [u'2B', u'H'],(DialTopicFlags, u'flags_dt'),'category',
                  'subtype',),
        MelFixedString(b'SNAM', u'subtypeName', 4),
        MelUInt32(b'TIFC', u'info_count'), # Updated in MobDial.dump
    )
    __slots__ = melSet.getSlotsUsed()

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDoor(MelRecord):
    """Door."""
    rec_sig = b'DOOR'

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
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
        'match_pc_below_minimum_level', 'disable_combat_boundary')

    melSet = MelSet(
        MelEdid(),
        MelTruncatedStruct(b'DATA', ['2I', '2b', 'B', 'b'],
            (FID, 'eczn_owner'), (FID, 'eczn_location'), 'eczn_rank',
            'eczn_minimum_level', (_eczn_flags, 'eczn_flags'),
            'eczn_max_level', old_versions={'2I'}),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
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
        MelTruncatedStruct(b'DATA',
            ['4s', '3I', '3B', 's', '9f', '3B', 's', '8f', '5I', '19f', '3B',
             's', '3B', 's', '3B', 's', '11f', 'I', '5f', '3B', 's', 'f', '2I',
             '6f', 'I', '3B', 's', '3B', 's', '9f', '8I', '2f', '4s'],
            'unknown1', 'ms_source_blend_mode', 'ms_blend_operation',
            'ms_z_test_function', 'fill_color1_red',
            'fill_color1_green', 'fill_color1_blue', 'unused1',
            'fill_alpha_fade_in_time', 'fill_full_alpha_time',
            'fill_alpha_fade_out_time', 'fill_persistent_alpha_ratio',
            'fill_alpha_pulse_amplitude', 'fill_alpha_pulse_frequency',
            'fill_texture_animation_speed_u', 'fill_texture_animation_speed_v',
            'ee_fall_off', 'ee_color_red', 'ee_color_green', 'ee_color_blue',
            'unused2', 'ee_alpha_fade_in_time', 'ee_full_alpha_time',
            'ee_alpha_fade_out_time', 'ee_persistent_alpha_ratio',
            'ee_alpha_pulse_amplitude', 'ee_alpha_pulse_frequency',
            'fill_full_alpha_ratio', 'ee_full_alpha_ratio',
            'ms_dest_blend_mode', 'ps_source_blend_mode', 'ps_blend_operation',
            'ps_z_test_function', 'ps_dest_blend_mode',
            'ps_particle_birth_ramp_up_time', 'ps_full_particle_birth_time',
            'ps_particle_birth_ramp_down_time', 'ps_full_particle_birth_ratio',
            'ps_persistent_particle_count', 'ps_particle_lifetime',
            'ps_particle_lifetime_delta', 'ps_initial_speed_along_normal',
            'ps_acceleration_along_normal', 'ps_initial_velocity1',
            'ps_initial_velocity2', 'ps_initial_velocity3', 'ps_acceleration1',
            'ps_acceleration2', 'ps_acceleration3', 'ps_scale_key1',
            'ps_scale_key2', 'ps_scale_key1_time', 'ps_scale_key2_time',
            'color_key1_red', 'color_key1_green', 'color_key1_blue', 'unused3',
            'color_key2_red', 'color_key2_green', 'color_key2_blue', 'unused4',
            'color_key3_red', 'color_key3_green', 'color_key3_blue', 'unused5',
            'color_key1_alpha', 'color_key2_alpha', 'color_key3_alpha',
            'color_key1_time', 'color_key2_time', 'color_key3_time',
            'ps_initial_speed_along_normal_delta', 'ps_initial_rotation',
            'ps_initial_rotation_delta', 'ps_rotation_speed',
            'ps_rotation_speed_delta', (FID, 'addon_models'),
            'holes_start_time', 'holes_end_time', 'holes_start_value',
            'holes_end_value', 'ee_width', 'edge_color_red',
            'edge_color_green', 'edge_color_blue', 'unused6',
            'explosion_wind_speed', 'texture_count_u', 'texture_count_v',
            'addon_models_fade_in_time', 'addon_models_fade_out_time',
            'addon_models_scale_start', 'addon_models_scale_end',
            'addon_models_scale_in_time', 'addon_models_scale_out_time',
            (FID, 'sound_ambient'), 'fill_color2_red',
            'fill_color2_green', 'fill_color2_blue', 'unused7',
            'fill_color3_red', 'fill_color3_green', 'fill_color3_blue',
            'unused8', 'fill_color1_scale', 'fill_color2_scale',
            'fill_color3_scale', 'fill_color1_time', 'fill_color2_time',
            'fill_color3_time', 'color_scale', 'birth_position_offset',
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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEnch(MelRecord):
    """Object Effect."""
    rec_sig = b'ENCH'

    _enit_flags = Flags.from_names(
        (0, 'ench_no_auto_calc'),
        (2, 'extend_duration_on_recast'),
    )

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEqup(MelRecord):
    """Equip Type."""
    rec_sig = b'EQUP'

    melSet = MelSet(
        MelEdid(),
        MelEqupPnam(),
        MelUInt32(b'DATA', 'use_all_parents'), # actually a bool
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreExpl(MelRecord):
    """Explosion."""
    rec_sig = b'EXPL'

    _expl_flags = Flags.from_names(
        (1, 'always_uses_world_orientation'),
        (2, 'knock_down_always'),
        (3, 'knock_down_by_formula'),
        (4, 'ignore_los_check'),
        (5, 'push_explosion_source_ref_only'),
        (6, 'ignore_image_space_swap'),
        (7, 'explosion_chain'),
        (8, 'no_controller_vibration'),
    )

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEyes(MelRecord):
    """Eyes."""
    rec_sig = b'EYES'

    EyesTypeFlags = Flags.from_names('playable', 'notMale', 'notFemale')

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelIcons(),
        MelUInt8Flags(b'DATA', u'flags', EyesTypeFlags),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFact(MelRecord):
    """Faction."""
    rec_sig = b'FACT'

    _general_flags = Flags.from_names(
        ( 0, u'hidden_from_pc'),
        ( 1, u'special_combat'),
        ( 6, u'track_crime'),
        ( 7, u'ignore_crimes_murder'),
        ( 8, u'ignore_crimes_assault'),
        ( 9, u'ignore_crimes_stealing'),
        (10, u'ignore_crimes_trespass'),
        (11, u'do_not_report_crimes_against_members'),
        (12, u'crime_gold_use_defaults'),
        (13, u'ignore_crimes_pickpocket'),
        (14, u'allow_sell'), # vendor
        (15, u'can_be_owner'),
        (16, u'ignore_crimes_werewolf'),
    )

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelRelations(),
        MelUInt32Flags(b'DATA', u'general_flags', _general_flags),
        MelFid(b'JAIL', u'exterior_jail_marker'),
        MelFid(b'WAIT', u'follower_wait_marker'),
        MelFid(b'STOL', u'stolen_goods_container'),
        MelFid(b'PLCN', u'player_inventory_container'),
        MelFid(b'CRGR', u'shared_crime_faction_list'),
        MelFid(b'JOUT', u'jail_outfit'),
        # 'cv_arrest' and 'cv_attack_on_sight' are actually bools, cv means
        # 'crime value' (which is what this struct is about)
        MelTruncatedStruct(b'CRVA', [u'2B', u'5H', u'f', u'2H'], u'cv_arrest',
                           u'cv_attack_on_sight', u'cv_murder', u'cv_assault',
                           u'cv_trespass', u'cv_pickpocket',
                           u'cv_unknown', u'cv_steal_multiplier', u'cv_escape',
                           u'cv_werewolf', old_versions={u'2B5Hf', u'2B5H'}),
        MelFactionRanks(),
        MelFid(b'VEND', u'vendor_buy_sell_list'),
        MelFid(b'VENC', u'merchant_container'),
        # 'vv_only_buys_stolen_items' and 'vv_not_sell_buy' are actually bools,
        # vv means 'vendor value' (which is what this struct is about)
        MelStruct(b'VENV', [u'3H', u'2s', u'2B', u'2s'], u'vv_start_hour', u'vv_end_hour',
                  u'vv_radius', u'vv_unknown1', u'vv_only_buys_stolen_items',
                  u'vv_not_sell_buy', u'vv_unknown2'),
        MelLocation(b'PLVD'),
        MelConditions(),
    )
    __slots__ = melSet.getSlotsUsed()

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
        MelBase(b'PNAM','unknown01'),
        MelAttx(b'RNAM'),
        MelBase(b'FNAM','unknown02'),
        MelFid(b'PFIG','ingredient'),
        MelSound(),
        MelStruct(b'PFPC', [u'4B'],'spring','summer','fall','winter',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFstp(MelRecord):
    """Footstep."""
    rec_sig = b'FSTP'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'DATA','impactSet'),
        MelString(b'ANAM','tag'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFsts(MelRecord):
    """Footstep Set."""
    rec_sig = b'FSTS'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'XCNT', [u'5I'],'walkForward','runForward','walkForwardAlt',
                  'runForwardAlt','walkForwardAlternate2',),
        MelSimpleArray('footstepSets', MelFid(b'DATA')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFurn(MelRecord):
    """Furniture."""
    rec_sig = b'FURN'

    FurnGeneralFlags = Flags.from_names((1, 'ignoredBySandbox'))

    FurnActiveMarkerFlags = Flags.from_names(
        (0, 'sit0'),
        (1, 'sit1'),
        (2, 'sit2'),
        (3, 'sit3'),
        (4, 'sit4'),
        (5, 'sit5'),
        (6, 'sit6'),
        (7, 'sit7'),
        (8, 'sit8'),
        (9, 'sit9'),
        (10, 'sit10'),
        (11, 'sit11'),
        (12, 'sit12'),
        (13, 'sit13'),
        (14, 'sit14'),
        (15, 'sit15'),
        (16, 'sit16'),
        (17, 'sit17'),
        (18, 'sit18'),
        (19, 'sit19'),
        (20, 'sit20'),
        (21, 'Sit21'),
        (22, 'Sit22'),
        (23, 'sit23'),
        (24, 'unknown25'),
        (25, 'disablesActivation'),
        (26, 'isPerch'),
        (27, 'mustExittoTalk'),
        (28, 'unknown29'),
        (29, 'unknown30'),
        (30, 'unknown31'),
        (31, 'unknown32'),
    )

    MarkerEntryPointFlags = Flags.from_names(
        (0, 'front'),
        (1, 'behind'),
        (2, 'right'),
        (3, 'left'),
        (4, 'up'),
    )

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelBase(b'PNAM','pnam_p'),
        MelUInt16Flags(b'FNAM', u'general_f', FurnGeneralFlags),
        MelFid(b'KNAM','interactionKeyword'),
        MelUInt32Flags(b'MNAM', u'activeMarkers', FurnActiveMarkerFlags),
        MelStruct(b'WBDT', [u'B', u'b'],'benchType','usesSkill',),
        MelFid(b'NAM1','associatedSpell'),
        MelGroups('markers',
            MelUInt32(b'ENAM', 'markerIndex',),
            MelStruct(b'NAM0', [u'2s', u'H'], u'unknown1',
                      (MarkerEntryPointFlags, u'disabledPoints_f')),
            MelFid(b'FNMK','markerKeyword',),
        ),
        MelGroups('entryPoints',
            MelStruct(b'FNPR', [u'2H'], u'markerType',
                      (MarkerEntryPointFlags, u'entryPointsFlags')),
        ),
        MelString(b'XMRK','modelFilename'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreGmst(AMreGmst):
    """Game Setting."""
    isKeyedByEid = True # NULL fids are acceptable.
    __slots__ = ()

#------------------------------------------------------------------------------
class MreGras(MelRecord):
    """Grass."""
    rec_sig = b'GRAS'

    GrasTypeFlags = Flags.from_names('vertexLighting', 'uniformScaling',
                                     'fitToSlope')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelStruct(b'DATA', [u'3B', u's', u'H', u'2s', u'I', u'4f', u'B', u'3s'],'density','minSlope','maxSlope',
                  'unkGras1','unitsFromWater','unkGras2',
                  'unitsFromWaterType','positionRange','heightRange',
                  'colorRange', 'wave_period', (GrasTypeFlags, u'flags'),
                  'unkGras3',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreHazd(MelRecord):
    """Hazard."""
    rec_sig = b'HAZD'

    HazdTypeFlags = Flags.from_names(
        (0, 'affectsPlayerOnly'),
        (1, 'inheritDurationFromSpawnSpell'),
        (2, 'alignToImpactNormal'),
        (3, 'inheritRadiusFromSpawnSpell'),
        (4, 'dropToGround'),
    )

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelImageSpaceMod(),
        MelStruct(b'DATA', [u'I', u'4f', u'5I'],'limit','radius','lifetime',
                  'imageSpaceRadius','targetInterval',(HazdTypeFlags, u'flags'),
                  (FID,'spell'),(FID,'light'),(FID,'impactDataSet'),(FID,'sound'),),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreHdpt(MelRecord):
    """Head Part."""
    rec_sig = b'HDPT'

    HdptTypeFlags = Flags.from_names(
        (0, 'playable'),
        (1, 'notFemale'),
        (2, 'notMale'),
        (3, 'isExtraPart'),
        (4, 'useSolidTint'),
    )

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelUInt8Flags(b'DATA', u'flags', HdptTypeFlags),
        MelUInt32(b'PNAM', 'hdpt_type'),
        MelSorted(MelFids('extraParts', MelFid(b'HNAM'))),
        MelGroups('partsData',
            MelUInt32(b'NAM0', 'headPartType',),
            MelString(b'NAM1','filename'),
        ),
        MelFid(b'TNAM','textureSet'),
        MelFid(b'CNAM','color'),
        MelFid(b'RNAM','validRaces'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIdle(MelRecord):
    """Idle Animation."""
    rec_sig = b'IDLE'

    IdleTypeFlags = TrimmedFlags.from_names(u'parent', u'sequence',
                                            u'noAttacking', u'blocking')

    melSet = MelSet(
        MelEdid(),
        MelConditionList(),
        MelString(b'DNAM','filename'),
        MelString(b'ENAM','animationEvent'),
        MelGroups('idleAnimations',
            MelStruct(b'ANAM', [u'I', u'I'],(FID,'parent'),(FID,'prevId'),),
        ),
        MelStruct(b'DATA', [u'4B', u'H'],'loopMin','loopMax',(IdleTypeFlags, u'flags'),
                  'animationGroupSection','replayDelay',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIdlm(MelRecord):
    """Idle Marker."""
    rec_sig = b'IDLM'

    IdlmTypeFlags = Flags.from_names(
        (0, 'runInSequence'),
        (1, 'unknown1'),
        (2, 'doOnce'),
        (3, 'unknown3'),
        (4, 'ignoredBySandbox'),
    )

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8Flags(b'IDLF', u'flags', IdlmTypeFlags),
        MelCounter(MelUInt8(b'IDLC', 'animation_count'), counts='animations'),
        MelFloat(b'IDLT', 'idleTimerSetting'),
        MelSimpleArray('animations', MelFid(b'IDLA')),
        MelModel(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreInfo(MelRecord):
    """Dialog Response."""
    rec_sig = b'INFO'

    _InfoResponsesFlags = Flags.from_names('useEmotionAnimation')

    _EnamResponseFlags = Flags.from_names(
        (0,  u'goodbye'),
        (1,  u'random'),
        (2,  u'say_once'),
        (3,  u'requires_player_activation'),
        (4,  u'info_refusal'),
        (5,  u'random_end'),
        (6,  u'invisible_continue'),
        (7,  u'walk_away'),
        (8,  u'walk_away_invisible_in_menu'),
        (9,  u'force_subtitle'),
        (10, u'can_move_while_greeting'),
        (11, u'no_lip_file'),
        (12, u'requires_post_processing'),
        (13, u'audio_output_override'),
        (14, u'spends_favor_points'),
    )

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBase(b'DATA','unknownDATA'),
        MelStruct(b'ENAM', [u'2H'], (_EnamResponseFlags, u'flags'),
                  'resetHours',),
        MelFid(b'TPIC', u'info_topic'),
        MelFid(b'PNAM', 'prev_info'),
        MelUInt8(b'CNAM', 'favorLevel'),
        MelFids('linkTo', MelFid(b'TCLT')),
        MelFid(b'DNAM','responseData',),
        MelGroups('responses',
            MelStruct(b'TRDT', [u'2I', u'4s', u'B', u'3s', u'I', u'B', u'3s'], u'emotionType', u'emotionValue',
                      u'unused1', u'responseNumber',
                      u'unused2', (FID, u'sound'),
                      (_InfoResponsesFlags, u'responseFlags'),
                      u'unused3'),
            MelLString(b'NAM1','responseText'),
            MelString(b'NAM2','scriptNotes'),
            MelString(b'NAM3','edits'),
            MelFid(b'SNAM','idleAnimationsSpeaker',),
            MelFid(b'LNAM','idleAnimationsListener',),
        ),
        MelConditionList(),
        MelGroups('leftOver',
            MelBase(b'SCHR','unknown1'),
            MelFid(b'QNAM','unknown2'),
            MelNull(b'NEXT'),
        ),
        MelLString(b'RNAM','prompt'),
        MelFid(b'ANAM','speaker',),
        MelFid(b'TWAT','walkAwayTopic',),
        MelFid(b'ONAM','audioOutputOverride',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreImad(MelRecord):
    """Image Space Adapter."""
    rec_sig = b'IMAD'

    _imad_dof_flags = Flags.from_names(
        'mode_front',
        'mode_back',
        'no_sky',
        'blur_radius_bit_2',
        'blur_radius_bit_1',
        'blur_radius_bit_0',
    )
    _ImadRadialBlurFlags = Flags.from_names('useTarget')

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DNAM', ['I', 'f', '49I', '2f', '3I', '2B', '2s', '4I'],
                  'animatable', 'duration',
                  u'eyeAdaptSpeedMult', u'eyeAdaptSpeedAdd',
                  u'bloomBlurRadiusMult', u'bloomBlurRadiusAdd',
                  u'bloomThresholdMult', u'bloomThresholdAdd',
                  u'bloomScaleMult', u'bloomScaleAdd', u'targetLumMinMult',
                  u'targetLumMinAdd', u'targetLumMaxMult', u'targetLumMaxAdd',
                  u'sunlightScaleMult', u'sunlightScaleAdd', u'skyScaleMult',
                  u'skyScaleAdd', u'unknown08Mult', u'unknown48Add',
                  u'unknown09Mult', u'unknown49Add', u'unknown0AMult',
                  u'unknown4AAdd', u'unknown0BMult', u'unknown4BAdd',
                  u'unknown0CMult', u'unknown4CAdd', u'unknown0DMult',
                  u'unknown4DAdd', u'unknown0EMult', u'unknown4EAdd',
                  u'unknown0FMult', u'unknown4FAdd', u'unknown10Mult',
                  u'unknown50Add', u'saturationMult', u'saturationAdd',
                  u'brightnessMult', u'brightnessAdd', u'contrastMult',
                  u'contrastAdd', u'unknown14Mult', u'unknown54Add',
                  u'tintColor', u'blurRadius', u'doubleVisionStrength',
                  u'radialBlurStrength', u'radialBlurRampUp',
                  u'radialBlurStart',
                  (_ImadRadialBlurFlags, u'radialBlurFlags'),
                  u'radialBlurCenterX', u'radialBlurCenterY', u'dofStrength',
                  u'dofDistance', u'dofRange', 'dof_use_target',
                  (_imad_dof_flags, 'dof_flags'), 'unused1',
                  u'radialBlurRampDown', u'radialBlurDownStart', u'fadeColor',
                  u'motionBlurStrength'),
        MelValueInterpolator(b'BNAM', 'blurRadiusInterp'),
        MelValueInterpolator(b'VNAM', 'doubleVisionStrengthInterp'),
        MelColorInterpolator(b'TNAM', 'tintColorInterp'),
        MelColorInterpolator(b'NAM3', 'fadeColorInterp'),
        MelValueInterpolator(b'RNAM', 'radialBlurStrengthInterp'),
        MelValueInterpolator(b'SNAM', 'radialBlurRampUpInterp'),
        MelValueInterpolator(b'UNAM', 'radialBlurStartInterp'),
        MelValueInterpolator(b'NAM1', 'radialBlurRampDownInterp'),
        MelValueInterpolator(b'NAM2', 'radialBlurDownStartInterp'),
        MelValueInterpolator(b'WNAM', 'dofStrengthInterp'),
        MelValueInterpolator(b'XNAM', 'dofDistanceInterp'),
        MelValueInterpolator(b'YNAM', 'dofRangeInterp'),
        MelValueInterpolator(b'NAM4', 'motionBlurStrengthInterp'),
        MelValueInterpolator(b'\x00IAD', 'eyeAdaptSpeedMultInterp'),
        MelValueInterpolator(b'\x40IAD', 'eyeAdaptSpeedAddInterp'),
        MelValueInterpolator(b'\x01IAD', 'bloomBlurRadiusMultInterp'),
        MelValueInterpolator(b'\x41IAD', 'bloomBlurRadiusAddInterp'),
        MelValueInterpolator(b'\x02IAD', 'bloomThresholdMultInterp'),
        MelValueInterpolator(b'\x42IAD', 'bloomThresholdAddInterp'),
        MelValueInterpolator(b'\x03IAD', 'bloomScaleMultInterp'),
        MelValueInterpolator(b'\x43IAD', 'bloomScaleAddInterp'),
        MelValueInterpolator(b'\x04IAD', 'targetLumMinMultInterp'),
        MelValueInterpolator(b'\x44IAD', 'targetLumMinAddInterp'),
        MelValueInterpolator(b'\x05IAD', 'targetLumMaxMultInterp'),
        MelValueInterpolator(b'\x45IAD', 'targetLumMaxAddInterp'),
        MelValueInterpolator(b'\x06IAD', 'sunlightScaleMultInterp'),
        MelValueInterpolator(b'\x46IAD', 'sunlightScaleAddInterp'),
        MelValueInterpolator(b'\x07IAD', 'skyScaleMultInterp'),
        MelValueInterpolator(b'\x47IAD', 'skyScaleAddInterp'),
        MelBase(b'\x08IAD', 'unknown08IAD'),
        MelBase(b'\x48IAD', 'unknown48IAD'),
        MelBase(b'\x09IAD', 'unknown09IAD'),
        MelBase(b'\x49IAD', 'unknown49IAD'),
        MelBase(b'\x0AIAD', 'unknown0aIAD'),
        MelBase(b'\x4AIAD', 'unknown4aIAD'),
        MelBase(b'\x0BIAD', 'unknown0bIAD'),
        MelBase(b'\x4BIAD', 'unknown4bIAD'),
        MelBase(b'\x0CIAD', 'unknown0cIAD'),
        MelBase(b'\x4CIAD', 'unknown4cIAD'),
        MelBase(b'\x0DIAD', 'unknown0dIAD'),
        MelBase(b'\x4DIAD', 'unknown4dIAD'),
        MelBase(b'\x0EIAD', 'unknown0eIAD'),
        MelBase(b'\x4EIAD', 'unknown4eIAD'),
        MelBase(b'\x0FIAD', 'unknown0fIAD'),
        MelBase(b'\x4FIAD', 'unknown4fIAD'),
        MelBase(b'\x10IAD', 'unknown10IAD'),
        MelBase(b'\x50IAD', 'unknown50IAD'),
        MelValueInterpolator(b'\x11IAD', 'saturationMultInterp'),
        MelValueInterpolator(b'\x51IAD', 'saturationAddInterp'),
        MelValueInterpolator(b'\x12IAD', 'brightnessMultInterp'),
        MelValueInterpolator(b'\x52IAD', 'brightnessAddInterp'),
        MelValueInterpolator(b'\x13IAD', 'contrastMultInterp'),
        MelValueInterpolator(b'\x53IAD', 'contrastAddInterp'),
        MelBase(b'\x14IAD', 'unknown14IAD'),
        MelBase(b'\x54IAD', 'unknown54IAD'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreImgs(MelRecord):
    """Image Space."""
    rec_sig = b'IMGS'

    melSet = MelSet(
        MelEdid(),
        MelBase(b'ENAM','eman_p'),
        MelStruct(b'HNAM', [u'9f'],'eyeAdaptSpeed','bloomBlurRadius','bloomThreshold','bloomScale',
                  'receiveBloomThreshold','white','sunlightScale','skyScale',
                  'eyeAdaptStrength',),
        MelStruct(b'CNAM', [u'3f'],'Saturation','Brightness','Contrast',),
        MelStruct(b'TNAM', [u'4f'],'tintAmount','tintRed','tintGreen','tintBlue',),
        MelStruct(b'DNAM', [u'3f', u'2s', u'H'],'dofStrength','dofDistance','dofRange','unknown',
                  'skyBlurRadius',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIngr(MelRecord):
    """Ingredient."""
    rec_sig = b'INGR'

    IngrTypeFlags = Flags.from_names(
        (0, 'no_auto_calc'),
        (1, 'food_item'),
        (8, 'references_persist'),
    )

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
        MelStruct(b'ENIT', [u'i', u'I'],'ingrValue',(IngrTypeFlags, u'flags'),),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIpct(MelRecord):
    """Impact."""
    rec_sig = b'IPCT'

    _IpctTypeFlags = Flags.from_names('noDecalData')

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelTruncatedStruct(b'DATA', [u'f', u'I', u'2f', u'I', u'2B', u'2s'], 'effectDuration',
                           'effectOrientation', 'angleThreshold',
                           'placementRadius', 'soundLevel',
                           (_IpctTypeFlags, u'ipctFlags'), 'impactResult',
                           'unkIpct1', old_versions={'fI2f'}),
        MelDecalData(),
        MelFid(b'DNAM','textureSet'),
        MelFid(b'ENAM','secondarytextureSet'),
        MelSound(),
        MelFid(b'NAM1','sound2'),
        MelFid(b'NAM2','hazard'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIpds(MelRecord):
    """Impact Dataset."""
    rec_sig = b'IPDS'

    melSet = MelSet(
        MelEdid(),
        MelSorted(MelGroups('impactData',
            MelStruct(b'PNAM', [u'2I'], (FID, 'material'), (FID, 'impact')),
        ), sort_by_attrs='material'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreKeym(MelRecord):
    """Key."""
    rec_sig = b'KEYM'

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreKywd(MelRecord):
    """Keyword record."""
    rec_sig = b'KYWD'

    melSet = MelSet(
        MelEdid(),
        MelColorO(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLcrt(MelRecord):
    """Location Reference Type."""
    rec_sig = b'LCRT'

    melSet = MelSet(
        MelEdid(),
        MelColorO(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLctn(MelRecord):
    """Location"""
    rec_sig = b'LCTN'

    melSet = MelSet(
        MelEdid(),
        MelArray('actorCellPersistentReference',
            MelStruct(b'ACPR', [u'2I', u'2h'], (FID, 'actor'), (FID, 'location'),
                      'gridX', 'gridY'),
        ),
        MelArray('locationCellPersistentReference',
            MelStruct(b'LCPR', [u'2I', u'2h'], (FID, 'actor'), (FID, 'location'),
                      'gridX', 'gridY'),
        ),
        MelSimpleArray('referenceCellPersistentReference', MelFid(b'RCPR')),
        MelArray('actorCellUnique',
            MelStruct(b'ACUN', [u'3I'], (FID, 'actor'), (FID, 'eef'),
                      (FID, 'location')),
        ),
        MelArray('locationCellUnique',
            MelStruct(b'LCUN', [u'3I'], (FID, 'actor'), (FID, 'eef'),
                      (FID, 'location')),
        ),
        MelSimpleArray('referenceCellUnique', MelFid(b'RCUN')),
        MelArray('actorCellStaticReference',
            MelStruct(b'ACSR', [u'3I', u'2h'], (FID, 'locRefType'), (FID, 'marker'),
                      (FID, 'location'), 'gridX', 'gridY'),
        ),
        MelArray('locationCellStaticReference',
            MelStruct(b'LCSR', [u'3I', u'2h'], (FID, 'locRefType'), (FID, 'marker'),
                      (FID, 'location'), 'gridX', 'gridY'),
        ),
        MelSimpleArray('referenceCellStaticReference', MelFid(b'RCSR')),
        MelGroups(u'actorCellEncounterCell',
            MelArray(u'coordinates',
                MelStruct(b'ACEC', [u'2h'], u'grid_x', u'grid_y'),
                     prelude=MelFid(b'ACEC', u'location'),
            ),
        ),
        MelGroups(u'locationCellEncounterCell',
            MelArray(u'coordinates',
                MelStruct(b'LCEC', [u'2h'], u'grid_x', u'grid_y'),
                     prelude=MelFid(b'LCEC', u'location'),
            ),
        ),
        MelGroups(u'referenceCellEncounterCell',
            MelArray(u'coordinates',
                MelStruct(b'RCEC', [u'2h'], u'grid_x', u'grid_y'),
                     prelude=MelFid(b'RCEC', u'location'),
            ),
        ),
        MelSimpleArray('actorCellMarkerReference', MelFid(b'ACID')),
        MelSimpleArray('locationCellMarkerReference', MelFid(b'LCID')),
        MelArray('actorCellEnablePoint',
            MelStruct(b'ACEP', [u'2I', u'2h'], (FID, 'actor'), (FID,'ref'), 'gridX',
                      'gridY'),
        ),
        MelArray('locationCellEnablePoint',
            MelStruct(b'LCEP', [u'2I', u'2h'], (FID, 'actor'), (FID,'ref'), 'gridX',
                      'gridY'),
        ),
        MelFull(),
        MelKeywords(),
        MelFid(b'PNAM','parentLocation',),
        MelFid(b'NAM1','music',),
        MelFid(b'FNAM','unreportedCrimeFaction',),
        MelFid(b'MNAM','worldLocationMarkerRef',),
        MelFloat(b'RNAM', 'worldLocationRadius'),
        MelFid(b'NAM0','horseMarkerRef',),
        MelColorO(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLgtm(MelRecord):
    """Lighting Template."""
    rec_sig = b'LGTM'

    class MelLgtmData(MelStruct):
        """Older format skips 8 bytes in the middle and has the same unpacked
        length, so we can't use MelTruncatedStruct."""

        def load_mel(self, record, ins, sub_type, size_, *debug_strs,
                __unpacker=structs_cache['3Bs3Bs3Bs2f2i3f24s3Bs3f4s'].unpack):
            if size_ == 92:
                super(MreLgtm.MelLgtmData, self).load_mel(
                    record, ins, sub_type, size_, *debug_strs)
                return
            elif size_ == 84:
                unpacked_val = ins.unpack(__unpacker, size_, *debug_strs)
                # Pad it with 8 null bytes in the middle
                unpacked_val = (*unpacked_val[:19],
                    unpacked_val[19] + null4 * 2, *unpacked_val[20:])
                for attr, value, action in zip(self.attrs, unpacked_val,
                                               self.actions):
                    if action is not None: value = action(value) ##: fids?
                    setattr(record, attr, value)
            else:
                raise ModSizeError(ins.inName, debug_strs, (92, 84), size_)

    melSet = MelSet(
        MelEdid(),
        MelLgtmData(b'DATA',
            [u'3B', u's', u'3B', u's', u'3B', u's', u'2f', u'2i', u'3f',
             u'32s', u'3B', u's', u'3f', u'4s'], 'redLigh', 'greenLigh',
            'blueLigh','unknownLigh', 'redDirect', 'greenDirect', 'blueDirect',
            'unknownDirect', 'redFog', 'greenFog', 'blueFog', 'unknownFog',
            'fogNear', 'fogFar', 'dirRotXY', 'dirRotZ', 'directionalFade',
            'fogClipDist', 'fogPower', 'ambientColors',
            'redFogFar', 'greenFogFar', 'blueFogFar', 'unknownFogFar',
            'fogMax', 'lightFaceStart', 'lightFadeEnd',
            'unknownData2'),
        MelDalc(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLigh(MelRecord):
    """Light."""
    rec_sig = b'LIGH'

    LighTypeFlags = Flags.from_names(
        (0, 'dynamic'),
        (1, 'canbeCarried'),
        (2, 'negative'),
        (3, 'flicker'),
        (4, 'unknown'),
        (5, 'offByDefault'),
        (6, 'flickerSlow'),
        (7, 'pulse'),
        (8, 'pulseSlow'),
        (9, 'spotLight'),
        (10, 'shadowSpotlight'),
        (11, 'shadowHemisphere'),
        (12, 'shadowOmnidirectional'),
        (13, 'portalstrict'),
    )

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelModel(),
        MelDestructible(),
        MelFull(),
        MelIcons(),
        # fe = 'Flicker Effect'
        MelStruct(b'DATA', ['i', 'I', '4B', 'I', '6f', 'I', 'f'], 'duration',
                  'radius', 'red', 'green', 'blue', 'unknown',
                  (LighTypeFlags, 'flags'), 'falloff', 'fov', 'nearClip',
                  'fePeriod', 'feIntensityAmplitude', 'feMovementAmplitude',
                  'value', 'weight'),
        MelFloat(b'FNAM', u'fade'),
        MelSound(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLscr(MelRecord):
    """Load Screen."""
    rec_sig = b'LSCR'

    melSet = MelSet(
        MelEdid(),
        MelIcons(),
        MelDescription(),
        MelConditionList(),
        MelFid(b'NNAM','loadingScreenNIF'),
        MelFloat(b'SNAM', 'initialScale'),
        MelStruct(b'RNAM', [u'3h'],'rotGridY','rotGridX','rotGridZ',),
        MelStruct(b'ONAM', [u'2h'],'rotOffsetMin','rotOffsetMax',),
        MelStruct(b'XNAM', [u'3f'],'transGridY','transGridX','transGridZ',),
        MelString(b'MOD2','cameraPath'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLtex(MelRecord):
    """Landscape Texture."""
    rec_sig = b'LTEX'

    _SnowFlags = Flags.from_names('considered_snow')

    melSet = MelSet(
        MelEdid(),
        MelFid(b'TNAM','textureSet',),
        MelFid(b'MNAM','materialType',),
        MelStruct(b'HNAM', [u'2B'], 'friction', 'restitution',),
        MelUInt8(b'SNAM', 'textureSpecularExponent'),
        MelSorted(MelFids('grasses', MelFid(b'GNAM'))),
        sse_only(MelUInt32Flags(b'INAM', u'snow_flags', _SnowFlags))
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLvli(AMreLeveledList):
    """Leveled Item."""
    rec_sig = b'LVLI'
    top_copy_attrs = ('chanceNone','glob',)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8(b'LVLD', 'chanceNone'),
        MelUInt8Flags(b'LVLF', u'flags', AMreLeveledList._flags),
        MelFid(b'LVLG', 'glob'),
        MelLLItems(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLvln(AMreLeveledList):
    """Leveled NPC."""
    rec_sig = b'LVLN'
    top_copy_attrs = ('chanceNone','model','modt_p',)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8(b'LVLD', 'chanceNone'),
        MelUInt8Flags(b'LVLF', u'flags', AMreLeveledList._flags),
        MelFid(b'LVLG', 'glob'),
        MelLLItems(),
        MelString(b'MODL','model'),
        MelBase(b'MODT','modt_p'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLvsp(AMreLeveledList):
    """Leveled Spell."""
    rec_sig = b'LVSP'

    top_copy_attrs = ('chanceNone',)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8(b'LVLD', 'chanceNone'),
        MelUInt8Flags(b'LVLF', u'flags', AMreLeveledList._flags),
        MelLLItems(with_coed=False),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMato(MelRecord):
    """Material Object."""
    rec_sig = b'MATO'

    _MatoTypeFlags = Flags.from_names('singlePass')
    _SnowFlags = Flags.from_names('considered_snow')

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelGroups('property_data',
            MelBase(b'DNAM', 'data_entry'),
        ),
        if_sse(
            le_version=MelTruncatedStruct(
                b'DATA', [u'11f', u'I'], 'falloffScale', 'falloffBias', 'noiseUVScale',
                'materialUVScale', 'projectionVectorX', 'projectionVectorY',
                'projectionVectorZ', 'normalDampener', 'singlePassColorRed',
                'singlePassColorGreen', 'singlePassColorBlue',
                (_MatoTypeFlags, 'single_pass_flags'), old_versions={'7f'}),
            se_version=MelTruncatedStruct(
                b'DATA', [u'11f', u'I', u'B', u'3s'], 'falloffScale', 'falloffBias',
                'noiseUVScale', 'materialUVScale', 'projectionVectorX',
                'projectionVectorY', 'projectionVectorZ', 'normalDampener',
                'singlePassColorRed', 'singlePassColorGreen',
                'singlePassColorBlue', (_MatoTypeFlags, 'single_pass_flags'),
                (_SnowFlags, 'snow_flags'), 'unused1',
                old_versions={u'7f', u'11fI'}),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMatt(MelRecord):
    """Material Type."""
    rec_sig = b'MATT'

    MattTypeFlags = Flags.from_names('stairMaterial', 'arrowsStick')

    melSet = MelSet(
        MelEdid(),
        MelFid(b'PNAM', 'materialParent',),
        MelString(b'MNAM','materialName'),
        MelStruct(b'CNAM', [u'3f'], 'red', 'green', 'blue'),
        MelFloat(b'BNAM', 'buoyancy'),
        MelUInt32Flags(b'FNAM', u'flags', MattTypeFlags),
        MelFid(b'HNAM', 'havokImpactDataSet',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMesg(MelRecord):
    """Message."""
    rec_sig = b'MESG'

    MesgTypeFlags = Flags.from_names('messageBox', 'autoDisplay')

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMgef(MelRecord):
    """Magic Effect."""
    rec_sig = b'MGEF'

    MgefGeneralFlags = Flags.from_names(
            ( 0, u'hostile'),
            ( 1, u'recover'),
            ( 2, u'detrimental'),
            ( 3, u'snaptoNavmesh'),
            ( 4, u'noHitEvent'),
            ( 8, u'dispellwithKeywords'),
            ( 9, u'noDuration'),
            (10, u'noMagnitude'),
            (11, u'noArea'),
            (12, u'fXPersist'),
            (14, u'goryVisuals'),
            (15, u'hideinUI'),
            (17, u'noRecast'),
            (21, u'powerAffectsMagnitude'),
            (22, u'powerAffectsDuration'),
            (26, u'painless'),
            (27, u'noHitEffect'),
            (28, u'noDeathDispel'),
    )

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMisc(MelRecord):
    """Misc. Item."""
    rec_sig = b'MISC'

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
    __slots__ = melSet.getSlotsUsed()

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMstt(MelRecord):
    """Moveable Static."""
    rec_sig = b'MSTT'

    MsttTypeFlags = Flags.from_names('onLocalMap', 'unknown2')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelUInt8Flags(b'DATA', u'flags', MsttTypeFlags),
        MelSound(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMusc(MelRecord):
    """Music Type."""
    rec_sig = b'MUSC'

    MuscTypeFlags = Flags.from_names(
        (0,'playsOneSelection'),
        (1,'abruptTransition'),
        (2,'cycleTracks'),
        (3,'maintainTrackOrder'),
        (4,'unknown5'),
        (5,'ducksCurrentTrack'),
    )

    melSet = MelSet(
        MelEdid(),
        MelUInt32Flags(b'FNAM', u'flags', MuscTypeFlags),
        # Divided by 100 in TES5Edit, probably for editing only
        MelStruct(b'PNAM', [u'2H'],'priority','duckingDB'),
        MelFloat(b'WNAM', 'fadeDuration'),
        MelSimpleArray('musicTracks', MelFid(b'TNAM')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMust(MelRecord):
    """Music Track."""
    rec_sig = b'MUST'

    melSet = MelSet(
        MelEdid(),
        MelUInt32(b'CNAM', 'trackType'),
        MelFloat(b'FLTV', 'duration'),
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
    __slots__ = melSet.getSlotsUsed()

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Not mergeable due to the way this record is linked to NAVI records
class MreNavm(MelRecord):
    """Navigation Mesh."""
    rec_sig = b'NAVM'

    melSet = MelSet(
        MelEdid(),
        MelNvnm(),
        MelBase(b'ONAM', 'unknownONAM'),
        MelBase(b'PNAM', 'unknownPNAM'),
        MelBase(b'NNAM', 'unknownNNAM'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreNpc(AMreActor):
    """Non-Player Character."""
    rec_sig = b'NPC_'

    _TemplateFlags = Flags.from_names(
        (0, 'useTraits'),
        (1, 'useStats'),
        (2, 'useFactions'),
        (3, 'useSpellList'),
        (4, 'useAIData'),
        (5, 'useAIPackages'),
        (6, 'useModelAnimation'),
        (7, 'useBaseData'),
        (8, 'useInventory'),
        (9, 'useScript'),
        (10, 'useDefPackList'),
        (11, 'useAttackData'),
        (12, 'useKeywords'),
    )

    NpcFlags1 = Flags.from_names(
        (0, 'female'),
        (1, 'essential'),
        (2, 'isCharGenFacePreset'),
        (3, 'respawn'),
        (4, 'autoCalc'),
        (5, 'unique'),
        (6, 'doesNotAffectStealth'),
        (7, 'pcLevelOffset'),
        (8, 'useTemplate'),
        (9, 'unknown9'),
        (10, 'unknown10'),
        (11, 'protected'),
        (12, 'unknown12'),
        (13, 'unknown13'),
        (14, 'summonable'),
        (15, 'unknown15'),
        (16, 'doesNotBleed'),
        (17, 'unknown17'),
        (18, 'bleedoutOverride'),
        (19, 'oppositeGenderAnims'),
        (20, 'simpleActor'),
        (21, 'loopedScript'),
        (22, 'unknown22'),
        (23, 'unknown23'),
        (24, 'unknown24'),
        (25, 'unknown25'),
        (26, 'unknown26'),
        (27, 'unknown27'),
        (28, 'loopedAudio'),
        (29, 'isGhost'),
        (30, 'unknown30'),
        (31, 'invulnerable'),
    )

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreOtft(MelRecord):
    """Outfit."""
    rec_sig = b'OTFT'

    melSet = MelSet(
        MelEdid(),
        MelSorted(MelSimpleArray('items', MelFid(b'INAM'))),
    )
    __slots__ = melSet.getSlotsUsed()

    def mergeFilter(self, modSet):
        self.items = [i for i in self.items if i.mod_id in modSet]

#------------------------------------------------------------------------------
class MrePack(MelRecord):
    """Package."""
    rec_sig = b'PACK'

    _GeneralFlags = Flags.from_names(
        (0, 'offers_services'),
        (2, 'must_complete'),
        (3, 'maintain_speed_at_goal'),
        (6, 'unlock_doors_at_package_start'),
        (7, 'unlock_doors_at_package_end'),
        (9, 'continue_if_pc_near'),
        (10, 'once_per_day'),
        (13, 'preferred_speed'),
        (17, 'always_sneak'),
        (18, 'allow_swimming'),
        (20, 'ignore_combat'),
        (21, 'weapons_unequipped'),
        (23, 'weapon_drawn'),
        (27, 'no_combat_alert'),
        (29, 'wear_sleep_outfit'),
    )
    _InterruptFlags = Flags.from_names(
        (0, 'hellos_to_player'),
        (1, 'random_conversations'),
        (2, 'observe_combat_behavior'),
        (3, 'greet_corpse_behavior'),
        (4, 'reaction_to_player_actions'),
        (5, 'friendly_fire_comments'),
        (6, 'aggro_radius_behavior'),
        (7, 'allow_idle_chatter'),
        (9, 'world_interactions'),
    )
    _SubBranchFlags = Flags.from_names('repeat_when_complete')
    _BranchFlags = Flags.from_names('success_completes_package')

    class MelDataInputs(MelGroups):
        """Occurs twice in PACK, so moved here to deduplicate the
        definition a bit."""
        _DataInputFlags = Flags.from_names('public')

        def __init__(self, attr):
            MelGroups.__init__(self, attr,
                MelSInt8(b'UNAM', 'input_index'),
                MelString(b'BNAM', 'input_name'),
                MelUInt32Flags(b'PNAM', u'input_flags', self._DataInputFlags),
            ),

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
            MelPartialCounter(MelStruct(b'IDLC', ['B', '3s'],
                'animation_count', 'unknown1'),
                counters={'animation_count': 'animations'}),
            MelFloat(b'IDLT', 'idleTimerSetting',),
            MelSimpleArray('animations', MelFid(b'IDLA')),
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
            b'INAM|SCHR|SCTX|QNAM|TNAM|PDTO': u'on_begin',
        },
        b'POEA': {
            b'INAM|SCHR|SCTX|QNAM|TNAM|PDTO': u'on_end',
        },
        b'POCA': {
            b'INAM|SCHR|SCTX|QNAM|TNAM|PDTO': u'on_change',
        },
    })
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

#------------------------------------------------------------------------------
class MreProj(MelRecord):
    """Projectile."""
    rec_sig = b'PROJ'

    ProjTypeFlags = Flags.from_names(
        (0, 'is_hitscan'),
        (1, 'is_explosive'),
        (2, 'alt_trigger'),
        (3, 'has_muzzle_flash'),
        (5, 'can_be_disabled'),
        (6, 'can_be_picked_up'),
        (7, 'is_super_sonic'),
        (8, 'pins_limbs'),
        (9, 'pass_through_small_transparent'),
        (10, 'disable_combat_aim_correction'),
        (11, 'projectile_rotates'),
    )

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Needs testing should be mergable
class MreQust(MelRecord):
    """Quest."""
    rec_sig = b'QUST'

    _questFlags = Flags.from_names(
        (0,  u'startGameEnabled'),
        (1,  u'completed'),
        (2,  u'add_idle_topic_to_hello'),
        (3,  u'allowRepeatedStages'),
        (4,  u'starts_enabled'),
        (5,  u'displayed_in_hud'),
        (6,  u'failed'),
        (7,  u'stage_wait'),
        (8,  u'runOnce'),
        (9,  u'excludeFromDialogueExport'),
        (10, u'warnOnAliasFillFailure'),
        (11, u'active'),
        (12, u'repeats_conditions'),
        (13, u'keep_instance'),
        (14, u'want_dormat'),
        (15, u'has_dialogue_data'),
    )
    _stageFlags = Flags.from_names(
        (0,'unknown0'),
        (1,'startUpStage'),
        (2,'startDownStage'),
        (3,'keepInstanceDataFromHereOn'),
    )
    stageEntryFlags = Flags.from_names('complete','fail')
    objectiveFlags = Flags.from_names('oredWithPrevious')
    targetFlags = Flags.from_names('ignoresLocks')
    aliasFlags = Flags.from_names(
        (0,'reservesLocationReference'),
        (1,'optional'),
        (2,'questObject'),
        (3,'allowReuseInQuest'),
        (4,'allowDead'),
        (5,'inLoadedArea'),
        (6,'essential'),
        (7,'allowDisabled'),
        (8,'storesText'),
        (9,'allowReserved'),
        (10,'protected'),
        (11,'noFillType'),
        (12,'allowDestroyed'),
        (13,'closest'),
        (14,'usesStoredText'),
        (15,'initiallyDisabled'),
        (16,'allowCleared'),
        (17,'clearsNameWhenRemoved'),
    )

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
                MelBase(b'SCHR', 'unusedSCHR'),
                MelBase(b'SCTX', 'unusedSCTX'),
                MelBase(b'QNAM', 'unusedQNAM'),
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
    __slots__ = melSet.getSlotsUsed()

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
    __slots__ = []
    def _clean_flags(self):
        if self.overlay_head_part_list and self.override_head_part_list:
            self.overlay_head_part_list = False

class MreRace(MelRecord):
    """Race."""
    rec_sig = b'RACE'

    _data_flags_1 = _RaceDataFlags1.from_names(
        u'playable', u'facegen_head', u'child', u'tilt_front_back',
        u'tilt_left_right', u'no_shadow', u'swims', u'flies', u'walks',
        u'immobile', u'not_pushable', u'no_combat_in_water',
        u'no_rotating_to_head_track', u'dont_show_blood_spray',
        u'dont_show_blood_decal', u'uses_head_track_anim',
        u'spells_align_with_magic_mode', u'use_world_raycasts_for_footik',
        u'allow_ragdoll_collisions', u'regen_hp_in_combat', u'cant_open_doors',
        u'allow_pc_dialogue', u'no_knockdowns', u'allow_pickpocket',
        u'always_use_proxy_controller', u'dont_show_weapon_blood',
        u'overlay_head_part_list', u'override_head_part_list',
        u'can_pickup_items', u'allow_multiple_membrane_shaders',
        u'can_dual_wield', u'avoids_roads',
    )
    _data_flags_2 = Flags.from_names(
        (0, u'use_advanced_avoidance'),
        (1, u'non_hostile'),
        (4, u'allow_mounted_combat'),
    )
    _equip_type_flags = TrimmedFlags.from_names(
        u'et_hand_to_hand_melee', u'et_one_hand_sword', u'et_one_hand_dagger',
        u'et_one_hand_axe', u'et_one_hand_mace', u'et_two_hand_sword',
        u'et_two_hand_axe', u'et_bow', u'et_staff', u'et_spell', u'et_shield',
        u'et_torch', u'et_crossbow')

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
            [u'14b', u'2s', u'4f', u'I', u'7f', u'I', u'2i', u'f', u'i', u'5f',
             'i', '4f', 'I', '9f'], ('skills', [0] * 14), 'unknown1',
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
        MelFloat(b'PNAM', u'facegen_main_clamp'), # required
        MelFloat(b'UNAM', u'facegen_face_clamp'), # required
        MelFid(b'ATKR', u'attack_race'),
        MelAttacks(),
        MelBaseR(b'NAM1', 'body_data_marker'), # required
        MelBaseR(b'MNAM', 'male_data_marker'), # required
        MelSorted(MelGroups(u'male_body_data',
            MelUInt32(b'INDX', u'body_part_index'), # required
            MelModel(),
        ), sort_by_attrs='body_part_index'),
        MelBaseR(b'FNAM', 'female_data_marker'), # required
        MelSorted(MelGroups(u'female_body_data',
            MelUInt32(b'INDX', u'body_part_index'), # required
            MelModel(),
        ), sort_by_attrs='body_part_index'),
        # These seem like unused leftovers from TES4/FO3, never occur in
        # vanilla or in any of the ~400 mod plugins I checked
        MelSorted(MelSimpleArray('hairs', MelFid(b'HNAM'))),
        MelSorted(MelSimpleArray('eyes', MelFid(b'ENAM'))),
        MelFid(b'GNAM', u'body_part_data'), # required
        MelBase(b'NAM2', u'marker_nam2_2'),
        MelBaseR(b'NAM3', 'behavior_graph_marker'), # required
        MelBaseR(b'MNAM', 'male_graph_marker'), # required
        MelModel(b'MODL', 'male_behavior_graph'),
        MelBaseR(b'FNAM', 'female_graph_marker'), # required
        MelModel(b'MODL', 'female_behavior_graph'),
        MelFid(b'NAM4', u'material_type'),
        MelFid(b'NAM5', u'impact_data_set'),
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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Needs Updating
class MreRefr(MelRecord):
    """Placed Object."""
    rec_sig = b'REFR'

    _lockFlags = Flags.from_names(None, None, 'leveledLock')
    _destinationFlags = Flags.from_names('noAlarm')
    _parentActivate = Flags.from_names('parentActivateOnly')
    reflectFlags = Flags.from_names('reflection', 'refraction')
    roomDataFlags = Flags.from_names(
        (6,'hasImageSpace'),
        (7,'hasLightingTemplate'),
    )

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
        MelOptStruct(b'XLIG', [u'4f', u'4s'], u'fov90Delta', u'fadeDelta',
            u'end_distance_cap', u'shadowDepthBias', u'unknown2'),
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
            MelBase(b'SCHR','schr_p',),
            MelBase(b'SCTX','sctx_p',),
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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRegn(MelRecord):
    """Region."""
    rec_sig = b'REGN'

    obflags = Flags.from_names(
        ( 0,'conform'),
        ( 1,'paintVertices'),
        ( 2,'sizeVariance'),
        ( 3,'deltaX'),
        ( 4,'deltaY'),
        ( 5,'deltaZ'),
        ( 6,'Tree'),
        ( 7,'hugeRock'),)
    sdflags = Flags.from_names(
        ( 0,'pleasant'),
        ( 1,'cloudy'),
        ( 2,'rainy'),
        ( 3,'snowy'),)
    rdatFlags = Flags.from_names('Override')

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRela(MelRecord):
    """Relationship."""
    rec_sig = b'RELA'

    RelationshipFlags = Flags.from_names(
        (0,'Unknown 1'),
        (1,'Unknown 2'),
        (2,'Unknown 3'),
        (3,'Unknown 4'),
        (4,'Unknown 5'),
        (5,'Unknown 6'),
        (6,'Unknown 7'),
        (7,'Secret'),
    )

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', [u'2I', u'H', u's', u'B', u'I'],(FID,'parent'),(FID,'child'),'rankType',
                  'unknown',(RelationshipFlags, u'relaFlags'),(FID,'associationType'),),
    )
    __slots__ = melSet.getSlotsUsed()

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRfct(MelRecord):
    """Visual Effect."""
    rec_sig = b'RFCT'

    RfctTypeFlags = Flags.from_names(
        u'rotate_to_face_target',
        u'attach_to_camera',
        u'inherit_rotation',
    )

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', [u'3I'], (FID, u'rfct_art'), (FID, u'rfct_shader'),
            (RfctTypeFlags, u'rfct_flags')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreScen(MelRecord):
    """Scene."""
    rec_sig = b'SCEN'

    ScenFlags5 = Flags.from_names(
        (15, 'faceTarget'),
        (16, 'looping'),
        (17, 'headtrackPlayer'),
    )

    ScenFlags3 = Flags.from_names(
        (0, 'deathPauseunsused'),
        (1, 'deathEnd'),
        (2, 'combatPause'),
        (3, 'combatEnd'),
        (4, 'dialoguePause'),
        (5, 'dialogueEnd'),
        (6, 'oBS_COMPause'),
        (7, 'oBS_COMEnd'),
    )

    ScenFlags2 = Flags.from_names('noPlayerActivation', 'optional')

    ScenFlags1 = Flags.from_names(
        (0, 'beginonQuestStart'),
        (1, 'stoponQuestEnd'),
        (2, 'unknown3'),
        (3, 'repeatConditionsWhileTrue'),
        (4, 'interruptible'),
    )

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelUInt32Flags(b'FNAM', u'flags', ScenFlags1),
        MelGroups('phases',
            MelNull(b'HNAM'),
            # Phase description. Always present, even if just a null-terminator
            MelString(b'NAM0', u'phase_desc',),
            MelGroup('startConditions',
                MelConditionList(),
            ),
            MelNull(b'NEXT'),
            MelGroup('completionConditions',
                MelConditionList(),
            ),
            # The next three are all leftovers
            MelGroup(u'unused1',
                MelBase(b'SCHR','schr_p'),
                MelBase(b'SCDA','scda_p'),
                MelBase(b'SCTX','sctx_p'),
                MelBase(b'QNAM','qnam_p'),
                MelBase(b'SCRO','scro_p'),
            ),
            MelNull(b'NEXT'),
            MelGroup(u'unused2',
                MelBase(b'SCHR','schr_p'),
                MelBase(b'SCDA','scda_p'),
                MelBase(b'SCTX','sctx_p'),
                MelBase(b'QNAM','qnam_p'),
                MelBase(b'SCRO','scro_p'),
            ),
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
            MelGroup('unused', # leftover
                MelBase(b'SCHR','schr_p'),
                MelBase(b'SCDA','scda_p'),
                MelBase(b'SCTX','sctx_p'),
                MelBase(b'QNAM','qnam_p'),
                MelBase(b'SCRO','scro_p'),
            ),
            MelNull(b'ANAM'),
        ),
        # The next three are all leftovers
        MelGroup(u'unused1',
            MelBase(b'SCHR','schr_p'),
            MelBase(b'SCDA','scda_p'),
            MelBase(b'SCTX','sctx_p'),
            MelBase(b'QNAM','qnam_p'),
            MelBase(b'SCRO','scro_p'),
        ),
        MelNull(b'NEXT'),
        MelGroup(u'unused2',
            MelBase(b'SCHR','schr_p'),
            MelBase(b'SCDA','scda_p'),
            MelBase(b'SCTX','sctx_p'),
            MelBase(b'QNAM','qnam_p'),
            MelBase(b'SCRO','scro_p'),
        ),
        MelFid(b'PNAM','quest',),
        MelUInt32(b'INAM', 'lastActionIndex'),
        MelBase(b'VNAM','vnam_p'),
        MelConditionList(),
    )
    __slots__ = melSet.getSlotsUsed()

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreShou(MelRecord):
    """Shout."""
    rec_sig = b'SHOU'

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSlgm(MelRecord):
    """Soul Gem."""
    rec_sig = b'SLGM'

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
        MelUInt8(b'SLCP', u'capacity', 1),
        MelFid(b'NAM0','linkedTo'),
    )
    __slots__ = melSet.getSlotsUsed()

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
    __slots__ = melSet.getSlotsUsed()

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
    __slots__ = melSet.getSlotsUsed()

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSnct(MelRecord):
    """Sound Category."""
    rec_sig = b'SNCT'

    SoundCategoryFlags = Flags.from_names('muteWhenSubmerged',
                                          'shouldAppearOnMenu')

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt32Flags(b'FNAM', u'flags', SoundCategoryFlags),
        MelFid(b'PNAM','parent',),
        MelUInt16(b'VNAM', 'staticVolumeMultiplier'),
        MelUInt16(b'UNAM', 'defaultMenuValue'),
    )
    __slots__ = melSet.getSlotsUsed()

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSopm(MelRecord):
    """Sound Output Model."""
    rec_sig = b'SOPM'

    _sopm_flags = Flags.from_names('attenuates_with_distance', 'allows_rumble')

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
    __slots__ = melSet.getSlotsUsed()

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
    __slots__ = melSet.getSlotsUsed()

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSpgd(MelRecord):
    """Shader Particle Geometry."""
    rec_sig = b'SPGD'

    _SpgdDataFlags = Flags.from_names('rain', 'snow')

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreStat(MelRecord):
    """Static."""
    rec_sig = b'STAT'

    _SnowFlags = Flags.from_names('considered_Snow')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        if_sse(
            le_version=MelStruct(b'DNAM', [u'f', u'I'], 'maxAngle30to120',
                                 (FID, 'material')),
            se_version=MelTruncatedStruct(
                b'DNAM', [u'f', u'I', u'B', u'3s'], 'maxAngle30to120',
                (FID, 'material'), (_SnowFlags, 'snow_flags'), 'unused1',
                old_versions={'fI'}),
        ),
        # Contains null-terminated mesh filename followed by random data
        # up to 260 bytes and repeats 4 times
        MelBase(b'MNAM', 'distantLOD'),
        MelBase(b'ENAM', 'unknownENAM'),
    )
    __slots__ = melSet.getSlotsUsed()

# MNAM Should use a custom unpacker if needed for the patcher otherwise MelBase
#------------------------------------------------------------------------------
class MreTact(MelRecord):
    """Talking Activator."""
    rec_sig = b'TACT'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelBase(b'PNAM','pnam_p'),
        MelSound(),
        MelBase(b'FNAM','fnam_p'),
        MelFid(b'VNAM', 'voiceType'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreTree(MelRecord):
    """Tree."""
    rec_sig = b'TREE'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelModel(),
        MelFid(b'PFIG','harvestIngredient'),
        MelSound(),
        MelStruct(b'PFPC', [u'4B'],'spring','summer','fall','wsinter',),
        MelFull(),
        MelStruct(b'CNAM', [u'12f'], u'trunk_flexibility', u'branch_flexibility',
                  u'trunk_amplitude', u'front_amplitude', u'back_amplitude',
                  u'side_amplitude', u'front_frequency', u'back_frequency',
                  u'side_frequency', u'leaf_flexibility', u'leaf_amplitude',
                  u'leaf_frequency'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreTxst(MelRecord):
    """Texture Set."""
    rec_sig = b'TXST'

    TxstTypeFlags = Flags.from_names(
        (0, 'noSpecularMap'),
        (1, 'facegenTextures'),
        (2, 'hasModelSpaceNormalMap'),
    )

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelGroups('destructionData',
            MelString(b'TX00','difuse'),
            MelString(b'TX01','normalGloss'),
            MelString(b'TX02','enviroMaskSubSurfaceTint'),
            MelString(b'TX03','glowDetailMap'),
            MelString(b'TX04','height'),
            MelString(b'TX05','environment'),
            MelString(b'TX06','multilayer'),
            MelString(b'TX07','backlightMaskSpecular'),
        ),
        MelDecalData(),
        MelUInt16Flags(b'DNAM', u'flags', TxstTypeFlags),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreVtyp(MelRecord):
    """Voice Type."""
    rec_sig = b'VTYP'

    VtypTypeFlags = Flags.from_names('allowDefaultDialog', 'female')

    melSet = MelSet(
        MelEdid(),
        MelUInt8Flags(b'DNAM', u'flags', VtypTypeFlags),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWatr(MelRecord):
    """Water."""
    rec_sig = b'WATR'

    WatrTypeFlags = Flags.from_names('causesDamage')

    # Struct elements shared by DNAM in SLE and SSE
    _dnam_common = [
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
            le_version=MelStruct(b'DNAM', [u'7f', u'4s', u'2f', u'3B', u's', u'3B', u's', u'3B', u's', u'4s', u'43f'],
                                 *_dnam_common),
            se_version=MelTruncatedStruct(b'DNAM',
                [u'7f', u'4s', u'2f', u'3B', u's', u'3B', u's', u'3B', u's',
                 u'4s', u'44f'],
                *(_dnam_common + ['noisePropertiesFlowmapScale']),
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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWeap(MelRecord):
    """Weapon"""
    rec_sig = b'WEAP'

    WeapFlags3 = Flags.from_names('onDeath')

    WeapFlags2 = Flags.from_names(
        (0, 'playerOnly'),
        (1, 'nPCsUseAmmo'),
        (2, 'noJamAfterReloadunused'),
        (3, 'unknown4'),
        (4, 'minorCrime'),
        (5, 'rangeFixed'),
        (6, 'notUsedinNormalCombat'),
        (7, 'unknown8'),
        (8, 'dont_use_3rd_person_IS_anim'),
        (9, 'unknown10'),
        (10, 'rumbleAlternate'),
        (11, 'unknown12'),
        (12, 'nonhostile'),
        (13, 'boundWeapon'),
    )

    WeapFlags1 = Flags.from_names(
        (0, 'ignoresNormalWeaponResistance'),
        (1, 'automaticunused'),
        (2, 'hasScopeunused'),
        (3, 'cant_drop'),
        (4, 'hideBackpackunused'),
        (5, 'embeddedWeaponunused'),
        (6, 'dont_use_1st_person_IS_anim_unused'),
        (7, 'nonplayable'),
    )

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
        MelFid(b'INAM','impactDataSet',),
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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWoop(MelRecord):
    """Word of Power."""
    rec_sig = b'WOOP'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelLString(b'TNAM','translation'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWrld(MelRecord):
    """Worldspace."""
    rec_sig = b'WRLD'

    WrldFlags2 = Flags.from_names(
        (0, 'smallWorld'),
        (1, 'noFastTravel'),
        (2, 'unknown3'),
        (3, 'noLODWater'),
        (4, 'noLandscape'),
        (5, 'unknown6'),
        (6, 'fixedDimensions'),
        (7, 'noGrass'),
    )

    WrldFlags1 = Flags.from_names(
        (0, 'useLandData'),
        (1, 'useLODData'),
        (2, 'useMapData'),
        (3, 'useWaterData'),
        (4, 'useClimateData'),
        (5, 'useImageSpaceDataunused'),
        (6, 'useSkyCell'),
    )

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Many Things Marked MelBase that need updated
class MreWthr(MelRecord):
    """Weather"""
    rec_sig = b'WTHR'

    WthrFlags2 = Flags.from_names(
        (0, 'layer_0'),
        (1, 'layer_1'),
        (2, 'layer_2'),
        (3, 'layer_3'),
        (4, 'layer_4'),
        (5, 'layer_5'),
        (6, 'layer_6'),
        (7, 'layer_7'),
        (8, 'layer_8'),
        (9, 'layer_9'),
        (10, 'layer_10'),
        (11, 'layer_11'),
        (12, 'layer_12'),
        (13, 'layer_13'),
        (14, 'layer_14'),
        (15, 'layer_15'),
        (16, 'layer_16'),
        (17, 'layer_17'),
        (18, 'layer_18'),
        (19, 'layer_19'),
        (20, 'layer_20'),
        (21, 'layer_21'),
        (22, 'layer_22'),
        (23, 'layer_23'),
        (24, 'layer_24'),
        (25, 'layer_25'),
        (26, 'layer_26'),
        (27, 'layer_27'),
        (28, 'layer_28'),
        (29, 'layer_29'),
        (30, 'layer_30'),
        (31, 'layer_31'),
    )

    WthrFlags1 = Flags.from_names(
        (0, 'weatherPleasant'),
        (1, 'weatherCloudy'),
        (2, 'weatherRainy'),
        (3, 'weatherSnow'),
        (4, 'skyStaticsAlwaysVisible'),
        (5, 'skyStaticsFollowsSunPosition'),
    )

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
    __slots__ = melSet.getSlotsUsed()
