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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module contains the fallout3 record classes. You must import from it
__once__ only in game.fallout3.Fallout3GameInfo#init. No other game.records
file must be imported till then."""

from ... import bush
from ...bolt import Flags, TrimmedFlags, flag, struct_calcsize, structs_cache
from ...brec import FID, AMelItems, AMelLLItems, AMreActor, AMreCell, \
    AMreFlst, AMreHeader, AMreImad, AMreLeveledList, AMreRace, AMreWithItems, \
    AMreWrld, AMreWthr, AttrValDecider, BipedFlags, MelActionFlags, \
    MelActivateParents, MelActorSounds, MelAddnDnam, MelAnimations, MelArray, \
    MelAspcRdat, MelBase, MelBaseR, MelBodyParts, MelBookText, MelBounds, \
    MelClmtWeatherTypes, MelCombatStyle, MelConditionsFo3, MelContData, \
    MelCpthShared, MelDeathItem, MelDecalData, MelDescription, MelDoorFlags, \
    MelEdid, MelEffectsFo3, MelEnableParent, MelEnchantment, MelExtra, \
    MelFactions, MelFactRanks, MelFid, MelFids, MelFloat, MelFlstFids, \
    MelFull, MelGrasData, MelGroup, MelGroups, MelHairFlags, MelIco2, \
    MelIcon, MelIcons, MelIcons2, MelIdleAnimationCountOld, \
    MelIdleAnimations, MelIdleRelatedAnims, MelIdleTimerSetting, \
    MelIdlmFlags, MelImageSpaceMod, MelImpactDataset, MelInfoResponsesFo3, \
    MelIpctSounds, MelIpctTextureSets, MelLandShared, MelLighFade, MelLists, \
    MelLLChanceNone, MelLLFlags, MelLLGlobal, MelLscrLocations, \
    MelLtexGrasses, MelLtexSnam, MelMapMarker, MelMODS, MelNodeIndex, \
    MelNull, MelObject, MelOptStruct, MelOwnership, MelPartialCounter, \
    MelPerkData, MelPerkParamsGroups, MelRace, MelRaceData, MelRaceParts, \
    MelRaceVoices, MelReadOnly, MelRecord, MelRef3D, MelReferences, \
    MelReflectedRefractedBy, MelRefScale, MelRegions, MelRegnEntrySubrecord, \
    MelRelations, MelScript, MelScriptVars, MelSequential, MelSet, \
    MelShortName, MelSimpleArray, MelSInt8, MelSInt16, MelSInt32, \
    MelSkipInterior, MelSorted, MelSound, MelSoundActivation, MelSoundClose, \
    MelSoundLooping, MelSoundPickupDrop, MelSpells, MelString, MelStruct, \
    MelTruncatedStruct, MelTxstFlags, MelUInt8, MelUInt8Flags, MelUInt16, \
    MelUInt16Flags, MelUInt32, MelUInt32Flags, MelUnion, MelUnorderedGroups, \
    MelValueWeight, MelWaterType, MelWeight, MelWorldBounds, MelWthrColors, \
    MelXlod, NavMeshFlags, PartialLoadDecider, PerkEpdfDecider, SizeDecider, \
    SpellFlags, VWDFlag, gen_color, gen_color3, null2, perk_distributor, \
    perk_effect_key
from ...exception import ModSizeError

_is_fnv = bush.game.fsName == 'FalloutNV'
def if_fnv(fo3_version, fnv_version):
    """Resolves to one of two different objects, depending on whether we're
    managing Fallout 3 or NV."""
    return fnv_version if _is_fnv else fo3_version

def fnv_only(fnv_obj):
    """Wrapper around if_fnv that resolves to None for FO3. Useful for things
    that have been added in FNV as MelSet will ignore None elements. Can also
    be used with Flags, but keep in mind that a None flag will still take up an
    index in the flags list, so it's a good idea to specify flag indices
    explicitly when using it."""
    return if_fnv(fo3_version=None, fnv_version=fnv_obj)

# noinspection PyRedeclaration
class MelRecord(MelRecord):
    class HeaderFlags(MelRecord.HeaderFlags):
        ##: Track down which records use this (it's not currently referenced
        # in ours or xEdit's code) and drop the redefinition
        no_voice_filter: bool = flag(13)

# Common Flags
class aiService(Flags):
    weapons: bool = flag(0)
    armor: bool = flag(1)
    clothing: bool = flag(2)
    books: bool = flag(3)
    foods: bool = flag(4)
    chems: bool = flag(5)
    stimpacks: bool = flag(6)
    lights: bool = flag(7)
    miscItems: bool = flag(10)
    potions: bool = flag(13)
    training: bool = flag(14)
    recharge: bool = flag(16)
    repair: bool = flag(17)

#------------------------------------------------------------------------------
# Record Elements -------------------------------------------------------------
#------------------------------------------------------------------------------
class AMreActorFo3(AMreActor):
    """Creatures and NPCs."""
    class TemplateFlags(Flags):
        useTraits: bool
        useStats: bool
        useFactions: bool
        useActorEffectList: bool
        useAIData: bool
        useAIPackages: bool
        useModelAnimation: bool
        useBaseData: bool
        useInventory: bool
        useScript: bool

#------------------------------------------------------------------------------
class MelModel(MelGroup):
    """Represents a model subrecord."""
    typeSets = {
        b'MODL': (b'MODL', b'MODB', b'MODT', b'MODS', b'MODD'),
        b'MOD2': (b'MOD2', b'MO2B', b'MO2T', b'MO2S'),
        b'MOD3': (b'MOD3', b'MO3B', b'MO3T', b'MO3S', b'MOSD'),
        b'MOD4': (b'MOD4', b'MO4B', b'MO4T', b'MO4S'),
        b'DMDL': (b'DMDL', b'DMDT'),
    }

    class _FacegenModelFlags(Flags):
        head: bool
        torso: bool
        rightHand: bool
        leftHand: bool

    def __init__(self, mel_sig=b'MODL', attr='model', with_facegen_flags=True):
        types = self.__class__.typeSets[mel_sig]
        mdl_elements = [MelString(types[0], 'modPath')]
        if mel_sig != b'DMDL':
            mdl_elements.extend([
                MelBase(types[1], 'modb_p'),
                MelBase(types[2], 'modt_p'), # Texture File Hashes
                MelMODS(types[3], 'alternateTextures'),
            ])
        else: # DMDL skips the '*B' subrecord
            mdl_elements.append(MelBase(types[1], 'modt_p'))
        # No MODD/MOSD equivalent for MOD2 and MOD4
        if len(types) == 5 and with_facegen_flags:
            mdl_elements.append(MelUInt8Flags(types[4], 'facegen_model_flags',
                self.__class__._FacegenModelFlags))
        super().__init__(attr, *mdl_elements)

#------------------------------------------------------------------------------
class MelActivationPrompt(MelString):
    """Handles the common XATO subrecord, introduced in FNV."""
    def __init__(self):
        super().__init__(b'XATO', 'activation_prompt')

#------------------------------------------------------------------------------
class MelBipedData(MelStruct):
    """Handles the common BMDT (Biped Data) subrecord."""
    class _BpFlags(BipedFlags):
        head: bool
        hair: bool
        upperBody: bool
        leftHand: bool
        rightHand: bool
        weapon: bool
        pipboy: bool
        backpack: bool
        necklace: bool
        headband: bool
        hat: bool
        eyeGlasses: bool
        noseRing: bool
        earrings: bool
        mask: bool
        choker: bool
        mouthObject: bool
        bodyAddon1: bool
        bodyAddon2: bool
        bodyAddon3: bool
        ##: Taken from valda's version, investigate
        _not_playable_flags = {'pipboy'}

    class _GeneralFlags(TrimmedFlags):
        hasBackpack: bool = flag(fnv_only(2))
        medium_armor: bool = flag(fnv_only(3))
        power_armor: bool = flag(5)
        notPlayable: bool = flag(6)
        heavy_armor: bool = flag(7)

    def __init__(self):
        super().__init__(b'BMDT', ['I', 'B', '3s'],
                         (self._BpFlags, 'biped_flags'),
                         (self._GeneralFlags, 'generalFlags'), 'bp_unused')

#------------------------------------------------------------------------------
class MelDestructible(MelGroup):
    """Represents a collection of destruction-related subrecords."""
    class _DestHeaderFlags(TrimmedFlags):
        vats_targetable: bool

    class _DestStageFlags(Flags):
        cap_damage: bool
        disable: bool
        destroy: bool

    def __init__(self):
        super().__init__('destructible',
            MelStruct(b'DEST', ['i', '2B', '2s'], 'health', 'count',
                      (MelDestructible._DestHeaderFlags, 'dest_flags'),
                      'dest_unused'),
            MelGroups('stages',
                MelStruct(b'DSTD', ['4B', 'i', '2I', 'i'], 'health', 'index',
                          'damage_stage',
                          (MelDestructible._DestStageFlags, 'stage_flags'),
                          'self_damage_per_second', (FID, 'explosion'),
                          (FID, 'debris'), 'debris_count'),
                MelModel(b'DMDL'),
                MelBaseR(b'DSTF', 'dest_end_marker'),
            ),
        )

#------------------------------------------------------------------------------
class MelEmbeddedScript(MelSequential):
    """Handles an embedded script, a SCHR/SCDA/SCTX/SLSD/SCVR/SCRO/SCRV
    subrecord combo."""
    class _ScriptHeaderFlags(Flags):
        enabled: bool

    def __init__(self):
        super(MelEmbeddedScript, self).__init__(
            MelOptStruct(b'SCHR', ['4s', '3I', '2H'], 'unused1', 'num_refs',
                         'compiled_size', 'last_index', 'script_type',
                         (self._ScriptHeaderFlags, 'schr_flags')),
            MelBase(b'SCDA', 'compiled_script'),
            MelString(b'SCTX', 'script_source'),
            MelScriptVars(),
            MelReferences(),
        )

#------------------------------------------------------------------------------
class MelEquipmentTypeFo3(MelSInt32):
    """Handles the common ETYP subrecord."""
    def __init__(self):
        ##: On py3, we really need enums for records. This is a prime candidate
        # 00: 'Big Guns',
        # 01: 'Energy Weapons',
        # 02: 'Small Guns',
        # 03: 'Melee Weapons',
        # 04: 'Unarmed Weapon',
        # 05: 'Thrown Weapons',
        # 06: 'Mine',
        # 07: 'Body Wear',
        # 08: 'Head Wear',
        # 09: 'Hand Wear',
        # 10: 'Chems',
        # 11: 'Stimpak',
        # 12: 'Food',
        # 13: 'Alcohol'
        super().__init__(b'ETYP', 'equipment_type')

#------------------------------------------------------------------------------
class MelItems(AMelItems):
    """Handles the CNTO/COED subrecords defining items."""
    def __init__(self):
        super().__init__(with_counter=False)

#------------------------------------------------------------------------------
##: Old format might be h2sI instead, which would retire this whole class
class MelLevListLvlo(MelTruncatedStruct):
    """Older format skips unused1, which is in the middle of the record."""
    def _pre_process_unpacked(self, unpacked_val):
        if len(unpacked_val) == 2:
            # Pad it in the middle, then let our parent deal with the rest
            unpacked_val = (unpacked_val[0], null2, unpacked_val[1])
        return super()._pre_process_unpacked(unpacked_val)

#------------------------------------------------------------------------------
class MelLinkedDecals(MelSorted):
    """Linked Decals for a reference record (REFR, ACHR, etc.)."""
    def __init__(self):
        super().__init__(MelGroups('linkedDecals',
            MelStruct(b'XDCR', ['2I'], (FID, 'reference'), 'unknown'),
        ), sort_by_attrs='reference')

#------------------------------------------------------------------------------
class MelLLItems(AMelLLItems):
    """Handles the LVLO/COED subrecords defining leveled list entries."""
    def __init__(self):
        super().__init__(MelLevListLvlo(b'LVLO', ['h', '2s', 'I', 'h', '2s'],
            'level', 'unused1', (FID, 'listId'), ('count', 1), 'unused2',
            old_versions={'iI'}), with_counter=False)

#------------------------------------------------------------------------------
class MelRaceHeadPart(MelGroup):
    """Implements special handling for ears, which can only contain an icon
    or a model, not both. Has to be here, since it's used by lambdas inside
    the RACE definition, so it can't be a subclass."""
    def __init__(self, part_indx):
        self._modl_loader = MelModel()
        self._icon_loader = MelIcons(mico_attr='')
        self._mico_loader = MelIcons(icon_attr='')
        super(MelRaceHeadPart, self).__init__('head_part',
            self._modl_loader,
            self._icon_loader,
            self._mico_loader,
        )
        self._part_indx = part_indx

    def dumpData(self, record, out):
        if self._part_indx == 1:
            target_head_part = getattr(record, self.attr)
            # Special handling for ears: If ICON or MICO is present, don't
            # dump the model
            has_icon = hasattr(target_head_part, 'iconPath')
            has_mico = hasattr(target_head_part, 'smallIconPath')
            if not has_icon and not has_mico:
                self._modl_loader.dumpData(target_head_part, out)
            else:
                if has_icon: self._icon_loader.dumpData(target_head_part, out)
                if has_mico: self._mico_loader.dumpData(target_head_part, out)
            return
        # Otherwise, delegate the dumpData call to MelGroup
        super(MelRaceHeadPart, self).dumpData(record, out)

#------------------------------------------------------------------------------
class MelSoundRandomLooping(MelFid):
    """Handles the common RNAM (Sound - Random/Looping) subrecord introduced in
    FNV."""
    def __init__(self):
        super().__init__(b'RNAM', 'sound_random_looping')

#------------------------------------------------------------------------------
# Fallout3 Records ------------------------------------------------------------
#------------------------------------------------------------------------------
class MreTes4(AMreHeader):
    """TES4 Record.  File header."""
    rec_sig = b'TES4'
    _post_masters_sigs = {b'ONAM', b'SCRN'}

    melSet = MelSet(
        MelStruct(b'HEDR', [u'f', u'2I'], ('version', 0.94), 'numRecords',
                  ('nextObject', 0x800)),
        MelNull(b'OFST'), # obsolete
        MelNull(b'DELE'), # obsolete
        AMreHeader.MelAuthor(),
        AMreHeader.MelDescription(),
        AMreHeader.MelMasterNames(),
        MelSimpleArray('overrides', MelFid(b'ONAM')),
        MelBase(b'SCRN', 'screenshot'),
    )

#------------------------------------------------------------------------------
class MreAchr(MelRecord):
    """Placed NPC."""
    rec_sig = b'ACHR'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'NAME','base'),
        MelFid(b'XEZN', u'encounterZone'),
        MelBase(b'XRGD','ragdollData'),
        MelBase(b'XRGB','ragdollBipedData'),
        MelGroup('patrolData',
            MelFloat(b'XPRD', 'idleTime'),
            MelBase(b'XPPA','patrolScriptMarker'),
            MelFid(b'INAM', 'idle'),
            MelEmbeddedScript(),
            MelFid(b'TNAM','topic'),
        ),
        MelSInt32(b'XLCM', 'levelModifier'),
        MelFid(b'XMRC', u'merchantContainer',),
        MelSInt32(b'XCNT', 'count'),
        MelFloat(b'XRDS', 'radius'),
        MelFloat(b'XHLP', 'health'),
        MelLinkedDecals(),
        MelFid(b'XLKR', u'linkedReference'),
        MelOptStruct(b'XCLP', [u'8B'],'linkStartColorRed','linkStartColorGreen','linkStartColorBlue','linkColorUnused1',
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue','linkColorUnused2'),
        MelActivateParents(),
        fnv_only(MelActivationPrompt()),
        MelEnableParent(),
        MelFid(b'XEMI', u'emittance'),
        MelFid(b'XMBR', u'multiboundReference'),
        MelBase(b'XIBS','ignoredBySandbox'),
        MelRefScale(),
        MelRef3D(),
    )

#------------------------------------------------------------------------------
class MreAcre(MelRecord):
    """Placed Creature."""
    rec_sig = b'ACRE'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'NAME','base'),
        MelFid(b'XEZN', u'encounterZone'),
        MelBase(b'XRGD','ragdollData'),
        MelBase(b'XRGB','ragdollBipedData'),
        MelGroup('patrolData',
            MelFloat(b'XPRD', 'idleTime'),
            MelBase(b'XPPA','patrolScriptMarker'),
            MelFid(b'INAM', 'idle'),
            MelEmbeddedScript(),
            MelFid(b'TNAM','topic'),
        ),
        MelSInt32(b'XLCM', 'levelModifier'),
        MelOwnership(),
        MelFid(b'XMRC', u'merchantContainer'),
        MelSInt32(b'XCNT', 'count'),
        MelFloat(b'XRDS', 'radius'),
        MelFloat(b'XHLP', 'health'),
        MelLinkedDecals(),
        MelFid(b'XLKR', u'linkedReference'),
        MelOptStruct(b'XCLP', [u'8B'],'linkStartColorRed','linkStartColorGreen','linkStartColorBlue','linkColorUnused1',
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue','linkColorUnused2'),
        MelActivateParents(),
        fnv_only(MelActivationPrompt()),
        MelEnableParent(),
        MelFid(b'XEMI', u'emittance'),
        MelFid(b'XMBR', u'multiboundReference'),
        MelBase(b'XIBS','ignoredBySandbox'),
        MelRefScale(),
        MelRef3D(),
    )

#------------------------------------------------------------------------------
class MreActi(MelRecord):
    """Activator."""
    rec_sig = b'ACTI'

    class HeaderFlags(NavMeshFlags, MelRecord.HeaderFlags):
        has_tree_lod: bool = flag(6)
        must_update_anims: bool = flag(8)           # FNV only?
        # NOTE: xEdit FO3 source has "On Local Map", but *hidden* is consistent
        # with all other games with this flag.
        hidden_from_local_map: bool = flag(9)
        random_animation_start: bool = flag(16)
        dangerous: bool = flag(17)
        ignore_object_interaction: bool = flag(20)  # FNV only?
        is_marker: bool = flag(23)                  # FNV only?
        obstacle: bool = flag(25)
        child_can_use: bool = flag(29)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelDestructible(),
        MelSound(),
        MelSoundActivation(),
        fnv_only(MelFid(b'INAM', 'radioTemplate')),
        MelFid(b'RNAM', u'radioStation'),
        MelWaterType(),
        fnv_only(MelActivationPrompt()),
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

    class _flags(Flags):
        autoCalc: bool
        alch_is_food: bool
        medicine: bool

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelScript(),
        MelDestructible(),
        MelSoundPickupDrop(),
        MelEquipmentTypeFo3(),
        MelWeight(),
        MelStruct(b'ENIT', [u'i', u'B', u'3s', u'I', u'f', u'I'], u'value', (_flags, u'flags'),
                  u'unused1', (FID, u'withdrawalEffect'),
                  'addictionChance', (FID, 'sound_consume')),
        MelEffectsFo3(),
    )

#------------------------------------------------------------------------------
class MreAmmo(MelRecord):
    """Ammunition."""
    rec_sig = b'AMMO'

    class _flags(Flags):
        notNormalWeapon: bool
        nonPlayable: bool

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        fnv_only(MelScript()),
        MelDestructible(),
        MelSoundPickupDrop(),
        MelStruct(b'DATA', [u'f', u'B', u'3s', u'i', u'B'],'speed',(_flags, u'flags'),'ammoData1',
                  'value','clipRounds'),
        fnv_only(MelTruncatedStruct(
            b'DAT2', [u'2I', u'f', u'I', u'f'], 'projPerShot',
            (FID, u'projectile'), 'weight', (FID, 'consumedAmmo'),
            'consumedPercentage', old_versions={'2If'})),
        MelShortName(),
        fnv_only(MelString(b'QNAM', 'abbreviation')),
        fnv_only(MelFids('effects', MelFid(b'RCIL'))),
    )

#------------------------------------------------------------------------------
class MreAnio(MelRecord):
    """Animation Object."""
    rec_sig = b'ANIO'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelFid(b'DATA','animationId'),
    )

#------------------------------------------------------------------------------
class _Fo3Playable(MelRecord):
    not_playable_flag = ('generalFlags', 'notPlayable')

class MreArma(_Fo3Playable):
    """Armor Addon."""
    rec_sig = b'ARMA'

    class _dnamFlags(Flags):
        modulates_voice: bool

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelBipedData(),
        MelModel(b'MODL', 'maleBody'),
        MelModel(b'MOD2', 'maleWorld'),
        MelIcons(u'maleIconPath', u'maleSmallIconPath'),
        MelModel(b'MOD3', 'femaleBody'),
        MelModel(b'MOD4', 'femaleWorld'),
        MelIcons2(),
        MelEquipmentTypeFo3(),
        MelStruct(b'DATA', [u'I', u'I', u'f'],'value','health','weight'),
        if_fnv(
            fo3_version=MelStruct(
                b'DNAM', [u'h', u'H'], 'dr', (_dnamFlags, u'dnamFlags')),
            fnv_version=MelTruncatedStruct(
                b'DNAM', [u'h', u'H', u'f', u'4s'], 'dr',
                (_dnamFlags, u'dnamFlags'), 'dt', 'armaDnam1',
                old_versions={'hH'}),
        ),
    )

#------------------------------------------------------------------------------
class MreArmo(_Fo3Playable):
    """Armor."""
    rec_sig = b'ARMO'

    class HeaderFlags(MelRecord.HeaderFlags):
        not_playable: bool = flag(fnv_only(2))

    class _dnamFlags(Flags):
        modulates_voice: bool

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelScript(),
        MelEnchantment(),
        MelBipedData(),
        MelModel(b'MODL', 'maleBody'),
        MelModel(b'MOD2', 'maleWorld'),
        MelIcons(u'maleIconPath', u'maleSmallIconPath'),
        MelModel(b'MOD3', 'femaleBody'),
        MelModel(b'MOD4', 'femaleWorld'),
        MelIcons2(),
        MelString(b'BMCT','ragdollTemplatePath'),
        MelDestructible(),
        MelFid(b'REPL','repairList'),
        MelFid(b'BIPL','bipedModelList'),
        MelEquipmentTypeFo3(),
        MelSoundPickupDrop(),
        MelStruct(b'DATA', [u'2i', u'f'],'value','health','weight'),
        if_fnv(
            fo3_version=MelStruct(
                b'DNAM', [u'h', u'H'], 'dr', (_dnamFlags, u'dnamFlags')),
            fnv_version=MelTruncatedStruct(
                b'DNAM', [u'h', u'H', u'f', u'4s'], 'dr',
                (_dnamFlags, u'dnamFlags'), 'dt', 'armoDnam1',
                old_versions={'hH'}),
        ),
        fnv_only(MelUInt32(b'BNAM', u'overridesAnimationSound')),
        fnv_only(MelGroups('animationSounds',
            MelStruct(b'SNAM', [u'I', u'B', u'3s', u'I'], (FID, 'sound'),
                      'chance', ('unused1', b'\xb7\xe7\x0b'), 'type'),
        )),
        fnv_only(MelFid(b'TNAM', 'animationSoundsTemplate')),
    )

#------------------------------------------------------------------------------
class MreAspc(MelRecord):
    """Acoustic Space."""
    rec_sig = b'ASPC'
    isKeyedByEid = True # NULL fids are acceptable

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        if_fnv(
            fo3_version=MelSound(),
            fnv_version=MelSequential(
                MelFid(b'SNAM', 'sound_dawn_default_loop'),
                MelFid(b'SNAM', 'sound_afternoon'),
                MelFid(b'SNAM', 'sound_dusk'),
                MelFid(b'SNAM', 'sound_night'),
                MelFid(b'SNAM', 'sound_walla'),
            ),
        ),
        fnv_only(MelUInt32(b'WNAM', 'walla_trigger_count')),
        MelAspcRdat(),
        MelUInt32(b'ANAM', 'environment_type'),
        fnv_only(MelUInt32(b'INAM', 'aspc_is_interior')),
    ).with_distributor(fnv_only({
        b'SNAM': [
            (b'SNAM', 'sound_dawn_default_loop'),
            (b'SNAM', 'sound_afternoon'),
            (b'SNAM', 'sound_dusk'),
            (b'SNAM', 'sound_night'),
            (b'SNAM', 'sound_walla'),
        ],
    }))

#------------------------------------------------------------------------------
class MreAvif(MelRecord):
    """Actor Value Information."""
    rec_sig = b'AVIF'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelIcons(),
        MelShortName(b'ANAM'),
    )

#------------------------------------------------------------------------------
class MreBook(MelRecord):
    """BOOK record."""
    rec_sig = b'BOOK'

    class _flags(Flags):
        isScroll: bool
        isFixed: bool

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelScript(),
        MelBookText(),
        MelDestructible(),
        MelSoundPickupDrop(),
        MelStruct(b'DATA', [u'B', u'b', u'I', u'f'],(_flags, u'flags'),('teaches',-1),'value','weight'),
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
        MelUnorderedGroups('body_part_list',
            MelString(b'BPTN', 'part_name'),
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
            MelBase(b'NAM5', 'texture_hashes'),
        ),
        MelFid(b'RAGA', 'ragdoll'),
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
        MelStruct(b'DATA', ['4I', '6f'], 'cams_action', 'cams_location',
            'cams_target', (_cams_flags, 'cams_flags'), 'time_mult_player',
            'time_mult_target', 'time_mult_global', 'cams_max_time',
            'cams_min_time', 'target_pct_between_actors'),
        MelImageSpaceMod(),
    )

#------------------------------------------------------------------------------
class MreCell(AMreCell):
    """Cell."""
    ref_types = {b'ACHR', b'ACRE', b'PBEA', b'PGRE', b'PMIS', b'REFR'}
    interior_temp_extra = [b'NAVM']

    class cellFlags(Flags):
        isInterior: bool = flag(0)
        hasWater: bool = flag(1)
        invertFastTravel: bool = flag(2)
        noLODWater: bool = flag(3)
        publicPlace: bool = flag(5)
        handChanged: bool = flag(6)
        behaveLikeExterior: bool = flag(7)

    class inheritFlags(Flags):
        ambientColor: bool
        directionalColor: bool
        fogColor: bool
        fogNear: bool
        fogFar: bool
        directionalRotation: bool
        directionalFade: bool
        clipDistance: bool
        fogPower: bool

    class _cell_land_flags(TrimmedFlags):
        hide_quad1: bool
        hide_quad2: bool
        hide_quad3: bool
        hide_quad4: bool

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt8Flags(b'DATA', u'flags', cellFlags),
        # None defaults here are on purpose - XCLC does not necessarily exist,
        # but 0 is a valid value for both coordinates (duh)
        MelSkipInterior(MelTruncatedStruct(b'XCLC', ['2i', 'I'],
            ('posX', None), ('posY', None),
            (_cell_land_flags, 'cell_land_flags'), is_optional=True,
            old_versions={'2i'})),
        MelTruncatedStruct(
            b'XCLL', [u'3B', u's', u'3B', u's', u'3B', u's', u'2f', u'2i',
                      u'3f'], 'ambientRed', 'ambientGreen', 'ambientBlue',
            'unused1', 'directionalRed', 'directionalGreen', 'directionalBlue',
            'unused2', 'fogRed', 'fogGreen', 'fogBlue', 'unused3', 'fogNear',
            'fogFar', 'directionalXY', 'directionalZ', 'directionalFade',
            'fogClip', 'fogPower', is_optional=True,
            old_versions={u'3Bs3Bs3Bs2f2i2f'}),
        MelBase(b'IMPF','footstepMaterials'), #--todo rewrite specific class.
        MelFid(b'LTMP','lightTemplate'),
        MelUInt32Flags(b'LNAM', u'lightInheritFlags', inheritFlags),
        MelFloat(b'XCLW', u'waterHeight'),
        MelString(b'XNAM','waterNoiseTexture'),
        MelRegions(),
        MelFid(b'XCIM','imageSpace'),
        MelUInt8(b'XCET', 'xcet_p'),
        MelFid(b'XEZN','encounterZone'),
        MelFid(b'XCCM','climate'),
        MelFid(b'XCWT','water'),
        MelOwnership(),
        MelFid(b'XCAS','acousticSpace'),
        MelNull(b'XCMT'),
        MelFid(b'XCMO','music'),
    )

#------------------------------------------------------------------------------
class MreClas(MelRecord):
    """Class."""
    rec_sig = b'CLAS'

    class _flags(TrimmedFlags):
        class_playable: bool
        class_guard: bool

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelIcon(),
        MelStruct(b'DATA', [u'4i', u'2I', u'b', u'B', u'2s'],'tagSkill1','tagSkill2','tagSkill3',
            'tagSkill4',(_flags, u'flags'),(aiService, u'services'),
            ('trainSkill',-1),'trainLevel','clasData1'),
        MelStruct(b'ATTR', [u'7B'], 'strength', 'perception', 'endurance',
                  'charisma', 'intelligence', 'agility', 'luck'),
    )

#------------------------------------------------------------------------------
class MreClmt(MelRecord):
    """Climate."""
    rec_sig = b'CLMT'

    melSet = MelSet(
        MelEdid(),
        MelClmtWeatherTypes(),
        MelString(b'FNAM','sunPath'),
        MelString(b'GNAM','glarePath'),
        MelModel(),
        MelStruct(b'TNAM', [u'6B'],'riseBegin','riseEnd','setBegin','setEnd',
                  'volatility','phaseLength',),
    )

#------------------------------------------------------------------------------
class MreCobj(MelRecord):
    """Constructible Object."""
    rec_sig = b'COBJ'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelScript(),
        MelSoundPickupDrop(),
        MelValueWeight(),
    )

#------------------------------------------------------------------------------
class MreCont(AMreWithItems):
    """Container."""
    rec_sig = b'CONT'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelItems(),
        MelDestructible(),
        MelContData(),
        MelSound(),
        MelSoundClose(),
        fnv_only(MelSoundRandomLooping()),
    )

#------------------------------------------------------------------------------
class MreCpth(MelRecord):
    """Camera Path."""
    rec_sig = b'CPTH'

    melSet = MelSet(
        MelEdid(),
        MelConditionsFo3(),
        MelCpthShared(),
    )

#------------------------------------------------------------------------------
class MreCrea(AMreActorFo3):
    """Creature."""
    rec_sig = b'CREA'

    class _flags(Flags):
        biped: bool = flag(0)
        essential: bool = flag(1)
        weaponAndShield: bool = flag(2)
        respawn: bool = flag(3)
        swims: bool = flag(4)
        flies: bool = flag(5)
        walks: bool = flag(6)
        pcLevelOffset: bool = flag(7)
        noLowLevel: bool = flag(9)
        noBloodSpray: bool = flag(11)
        noBloodDecal: bool = flag(12)
        noHead: bool = flag(15)
        noRightArm: bool = flag(16)
        noLeftArm: bool = flag(17)
        noCombatInWater: bool = flag(18)
        noShadow: bool = flag(19)
        noVATSMelee: bool = flag(20)
        allowPCDialogue: bool = flag(21)
        cantOpenDoors: bool = flag(22)
        immobile: bool = flag(23)
        tiltFrontBack: bool = flag(24)
        tiltLeftRight: bool = flag(25)
        noKnockDown: bool = flag(26)
        notPushable: bool = flag(27)
        allowPickpocket: bool = flag(28)
        isGhost: bool = flag(29)
        noRotatingHeadTrack: bool = flag(30)
        invulnerable: bool = flag(31)

    class aggroflags(Flags):
        aggroRadiusBehavior: bool

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelSpells(),
        MelEnchantment(),
        MelUInt16(b'EAMT', 'eamt'),
        MelBodyParts(),
        MelBase(b'NIFT','nift_p'), # Texture File Hashes
        MelStruct(b'ACBS', [u'I', u'2H', u'h', u'3H', u'f', u'h', u'H'],(_flags, u'flags'),'fatigue',
            'barterGold',('level_offset',1),'calcMin','calcMax','speedMultiplier',
            'karma', 'dispositionBase',
            (AMreActorFo3.TemplateFlags, 'templateFlags')),
        MelFactions(),
        MelDeathItem(),
        MelFid(b'VTCK','voice'),
        MelFid(b'TPLT','template'),
        MelDestructible(),
        MelScript(),
        MelItems(),
        MelStruct(b'AIDT', [u'5B', u'3s', u'I', u'b', u'B', u'b', u'B', u'i'], 'aggression', ('confidence', 2),
                  ('energyLevel', 50), ('responsibility', 50), 'mood',
                  'unused_aidt', (aiService, u'services'),
                  ('trainSkill', -1), 'trainLevel', 'assistance',
                  (aggroflags, u'aggroRadiusBehavior'), 'aggroRadius'),
        MelFids('aiPackages', MelFid(b'PKID')),
        MelAnimations(),
        MelStruct(b'DATA', [u'4B', u'h', u'2s', u'h', u'7B'],'creatureType','combatSkill','magicSkill',
            'stealthSkill','health','unused2','damage','strength',
            'perception','endurance','charisma','intelligence','agility',
            'luck'),
        MelUInt8(b'RNAM', 'attackReach'),
        MelCombatStyle(),
        MelFid(b'PNAM','bodyPartData'),
        MelFloat(b'TNAM', 'turningSpeed'),
        MelFloat(b'BNAM', 'baseScale'),
        MelFloat(b'WNAM', 'footWeight'),
        MelUInt32(b'NAM4', u'impactMaterialType'),
        MelUInt32(b'NAM5', u'soundLevel'),
        MelFid(b'CSCR','inheritsSoundsFrom'),
        MelActorSounds(),
        MelImpactDataset(b'CNAM'),
        MelFid(b'LNAM','meleeWeaponList'),
    )

#------------------------------------------------------------------------------
class MreCsty(MelRecord):
    """Combat Style."""
    rec_sig = b'CSTY'

    class _csty_flags(Flags):
        advanced: bool
        use_chance_for_attack: bool
        ignore_allies: bool
        will_yield: bool
        rejects_yields: bool
        fleeing_disabled: bool
        prefers_ranged: bool
        melee_alert_ok: bool

    melSet = MelSet(
        MelEdid(),
        MelOptStruct(b'CSTD',
            ['2B', '2s', '8f', '2B', '2s', '3f', 'B', '3s', '2f', '5B', '3s',
             '2f', 'H', '2s', '2B', '2s', 'f'], 'dodge_chance', 'lr_chance',
            'unused1', 'lr_timer_min', 'lr_timer_max', 'for_timer_min',
            'for_timer_max', 'back_timer_min', 'back_timer_max',
            'idle_timer_min', 'idle_timer_max', 'blk_chance', 'atk_chance',
            'unused2', 'atk_brecoil', 'atk_bunc', 'atk_bh_2_h', 'p_atk_chance',
            'unused3', 'p_atk_brecoil', 'p_atk_bunc', 'p_atk_normal',
            'p_atk_for', 'p_atk_back', 'p_atk_l', 'p_atk_r', 'unused4',
            'hold_timer_min', 'hold_timer_max', (_csty_flags, 'csty_flags'),
            'unused5', 'acro_dodge', 'rush_chance', 'unused6', 'rush_mult'),
        MelOptStruct(b'CSAD', ['21f'], 'dodge_fmult', 'dodge_fbase',
            'enc_sbase', 'enc_smult', 'dodge_atk_mult', 'dodge_natk_mult',
            'dodge_batk_mult', 'dodge_bnatk_mult', 'dodge_fatk_mult',
            'dodge_fnatk_mult', 'block_mult', 'block_base', 'block_atk_mult',
            'block_natk_mult', 'atk_mult', 'atk_base', 'atk_atk_mult',
            'atk_natk_mult', 'atk_block_mult', 'p_atk_fbase', 'p_atk_fmult'),
        MelOptStruct(b'CSSD', ['9f', '4s', 'I', '5f'], 'cover_search_radius',
            'take_cover_chance', 'wait_timer_min', 'wait_timer_max',
            'wait_to_fire_timer_min', 'wait_to_fire_timer_max',
            'fire_timer_min', 'fire_timer_max', 'ranged_weapon_range_mult_min',
            'unknown1', 'weapon_restrictions', 'ranged_weapon_range_mult_max',
            'max_targeting_fov', 'combat_radius',
            'semi_automatic_fire_delay_mult_min',
            'semi_automatic_fire_delay_mult_max'),
    )

#------------------------------------------------------------------------------
class MreDial(MelRecord):
    """Dialogue."""
    rec_sig = b'DIAL'

    class _DialFlags(Flags):
        rumors: bool
        toplevel: bool

    @classmethod
    def nested_records_sigs(cls):
        return {b'INFO'}

    melSet = MelSet(
        MelEdid(),
        MelSorted(MelFids('added_quests', MelFid(b'QSTI'))),
        MelSorted(MelFids('removed_quests', MelFid(b'QSTR'))),
        MelFull(),
        MelFloat(b'PNAM', 'priority'),
        MelTruncatedStruct(b'DATA', [u'2B'], 'dialType',
                           (_DialFlags, u'dialFlags'), old_versions={'B'}),
    )

#------------------------------------------------------------------------------
class MreDobj(MelRecord):
    """Default Object Manager."""
    rec_sig = b'DOBJ'

    # The FO3 and FNV DATA subrecords share the same 21 starting attributes
    _fo3_data = [(FID, a) for a in (
        'stimpack', 'superStimpack', 'radX', 'radAway', 'morphine',
        'perkParalysis', 'playerFaction', 'mysteriousStrangerNpc',
        'mysteriousStrangerFaction', 'defaultMusic', 'battleMusic',
        'deathMusic', 'successMusic', 'levelUpMusic', 'playerVoiceMale',
        'playerVoiceMaleChild', 'playerVoiceFemale', 'playerVoiceFemaleChild',
        'eatPackageDefaultFood', 'everyActorAbility', 'drugWearsOffImageSpace',
    )]
    _fnv_data = _fo3_data + [(FID, a) for a in (
        'doctersBag', 'missFortuneNpc', 'missFortuneFaction',
        'meltdownExplosion', 'unarmedForwardPA', 'unarmedBackwardPA',
        'unarmedLeftPA', 'unarmedRightPA', 'unarmedCrouchPA',
        'unarmedCounterPA', 'spotterEffect', 'itemDetectedEffect',
        'cateyeMobileEffect',
    )]

    melSet = MelSet(
        MelEdid(),
        if_fnv(
            fo3_version=MelStruct(b'DATA', [u'21I'], *_fo3_data),
            fnv_version=MelStruct(b'DATA', [u'34I'], *_fnv_data),
        ),
    )

#------------------------------------------------------------------------------
class MreDoor(MelRecord):
    """Door."""
    rec_sig = b'DOOR'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelDestructible(),
        MelSound(),
        MelSoundClose(b'ANAM'),
        MelSoundLooping(),
        MelDoorFlags(),
    )

#------------------------------------------------------------------------------
class MreEczn(MelRecord):
    """Encounter Zone."""
    rec_sig = b'ECZN'

    class _eczn_flags(Flags):
        never_resets: bool
        match_pc_below_minimum_level: bool

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', ['I', '2b', 'B', 's'], (FID, 'eczn_owner'),
            'eczn_rank', 'eczn_minimum_level', (_eczn_flags, 'eczn_flags'),
            'eczn_unused'),
    )

#------------------------------------------------------------------------------
class MreEfsh(MelRecord):
    """Effect Shader."""
    rec_sig = b'EFSH'

    class _efsh_flags(Flags):
        no_membrane_shader: bool = flag(0)
        no_particle_shader: bool = flag(3)
        ee_inverse: bool = flag(4)
        affect_skin_only: bool = flag(5)

    melSet = MelSet(
        MelEdid(),
        MelIcon('fill_texture'),
        MelIco2('particle_texture'),
        MelString(b'NAM7', 'holes_texture'),
        MelTruncatedStruct(b'DATA',
            ['B', '3s', '3I', '3B', 's', '9f', '3B', 's', '8f', '5I', '19f',
             '3B', 's', '3B', 's', '3B', 's', '11f', 'I', '5f', '3B', 's', 'f',
             '2I', '6f'], (_efsh_flags, 'efsh_flags'), 'unused1',
            'ms_source_blend_mode', 'ms_blend_operation', 'ms_z_test_function',
            *gen_color('fill_color1'), 'fill_alpha_fade_in_time',
            'fill_full_alpha_time', 'fill_alpha_fade_out_time',
            'fill_persistent_alpha_ratio', 'fill_alpha_pulse_amplitude',
            'fill_alpha_pulse_frequency', 'fill_texture_animation_speed_u',
            'fill_texture_animation_speed_v', 'ee_fall_off',
            *gen_color('ee_color'), 'ee_alpha_fade_in_time',
            'ee_full_alpha_time', 'ee_alpha_fade_out_time',
            'ee_persistent_alpha_ratio', 'ee_alpha_pulse_amplitude',
            'ee_alpha_pulse_frequency', 'fill_full_alpha_ratio',
            'ee_full_alpha_ratio', 'ms_dest_blend_mode',
            'ps_source_blend_mode', 'ps_blend_operation', 'ps_z_test_function',
            'ps_dest_blend_mode', 'ps_particle_birth_ramp_up_time',
            'ps_full_particle_birth_time', 'ps_particle_birth_ramp_down_time',
            'ps_full_particle_birth_ratio',
            'ps_persistent_particle_birth_ratio', 'ps_particle_lifetime',
            'ps_particle_lifetime_delta', 'ps_initial_speed_along_normal',
            'ps_acceleration_along_normal', 'ps_initial_velocity1',
            'ps_initial_velocity2', 'ps_initial_velocity3', 'ps_acceleration1',
            'ps_acceleration2', 'ps_acceleration3', 'ps_scale_key1',
            'ps_scale_key2', 'ps_scale_key1_time', 'ps_scale_key2_time',
            *gen_color ('color_key1'), *gen_color ('color_key2'),
            *gen_color ('color_key3'), 'color_key1_alpha', 'color_key2_alpha',
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
            'addon_models_scale_out_time', old_versions={
                'B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I4f',
                'B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I',
                'B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI',
                'B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11f',
                'B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs6f',
            }),
    )

#------------------------------------------------------------------------------
class MreEnch(MelRecord):
    """Object Effect."""
    rec_sig = b'ENCH'

    class _enit_flags(Flags):
        ench_no_auto_calc: bool
        auto_calculate: bool
        hide_effect: bool

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelStruct(b'ENIT', ['3I', 'B', '3s'], 'item_type', 'charge_amount',
            'enchantment_cost', (_enit_flags, 'enit_flags'), 'unused1'),
        MelEffectsFo3(),
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

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelEnchantment(),
        MelImageSpaceMod(),
        MelStruct(b'DATA', ['3f', '3I', 'f', '2I', '3f', 'I'], 'expl_force',
            'expl_damage', 'expl_radius', (FID, 'expl_light'),
            (FID, 'expl_sound1'), (_expl_flags, 'expl_flags'), 'is_radius',
            (FID, 'expl_impact_dataset'), (FID, 'expl_sound2'),
            'radiation_level', 'radiation_time', 'radiation_radius',
            'expl_sound_level'),
        MelFid(b'INAM', 'placed_impact_object'),
    )

#------------------------------------------------------------------------------
class MreFact(MelRecord):
    """Faction."""
    rec_sig = b'FACT'

    class _fact_flags1(Flags):
        hidden_from_pc: bool
        evil: bool
        special_combat: bool

    class _fact_flags2(Flags):
        track_crime: bool
        allow_sell: bool

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelRelations(),
        MelTruncatedStruct(b'DATA', ['2B', '2s'],
            (_fact_flags1, 'fact_flags1'), (_fact_flags2, 'fact_flags2'),
            'unused1', old_versions={'2B', 'B'}),
        MelFloat(b'CNAM', 'cnam_unused'), # leftover from Oblivion
        MelFactRanks(),
        fnv_only(MelFid(b'WMI1', 'reputation')),
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

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelDestructible(),
        MelBase(b'MNAM', 'active_markers_flags'), # not decoded in xEdit
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
class MreHair(MelRecord):
    """Hair."""
    rec_sig = b'HAIR'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelHairFlags(),
    )

#------------------------------------------------------------------------------
class MreHdpt(MelRecord):
    """Head Part."""
    rec_sig = b'HDPT'

    class _hdpt_flags(Flags):
        playable: bool

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelUInt8Flags(b'DATA', 'flags', _hdpt_flags),
        MelSorted(MelFids('extra_parts', MelFid(b'HNAM'))),
    )

#------------------------------------------------------------------------------
class MreIdle(MelRecord):
    """Idle Animation."""
    rec_sig = b'IDLE'

    class _idle_flags(Flags):
        no_attacking: bool

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelConditionsFo3(),
        MelIdleRelatedAnims(),
        MelTruncatedStruct(b'DATA', ['3B', 's', 'h', 'B', 's'],
            'animation_group_section', 'looping_min', 'looping_max',
            'unused1', 'replay_delay', (_idle_flags, 'idle_flags'),
            'unknown2', old_versions={'3Bsh'}),
    )

#------------------------------------------------------------------------------
class MreIdlm(MelRecord):
    """Idle Marker."""
    rec_sig = b'IDLM'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelIdlmFlags(),
        MelIdleAnimationCountOld(),
        MelIdleTimerSetting(),
        MelIdleAnimations(),
    )

#------------------------------------------------------------------------------
class MreImad(AMreImad): # see AMreImad for details
    """Image Space Adapter."""
    melSet = MelSet(
        MelEdid(),
        MelPartialCounter(MelTruncatedStruct(b'DNAM',
            ['I', 'f', '49I', '2f', '3I', 'B', '3s', '4I'], 'imad_animatable',
            'imad_duration', *AMreImad.dnam_counters1,
            'radial_blur_use_target', 'radial_blur_center_x',
            'radial_blur_center_y', *AMreImad.dnam_counters2,
            'dof_use_target', 'unused1', *AMreImad.dnam_counters3,
            old_versions={'If49I2f3IB3s3I', 'If49I2f3IB3s2I', 'If45I'}),
            counters=AMreImad.dnam_counter_mapping),
        *[AMreImad.special_impls[s](s, a) for s, a in AMreImad.imad_sig_attr],
        fnv_only(MelFid(b'RDSD', 'sound_intro')),
        fnv_only(MelFid(b'RDSI', 'sound_outro')),
    )

#------------------------------------------------------------------------------
class MreImgs(MelRecord):
    """Image Space."""
    rec_sig = b'IMGS'

    class _dnam_flags(TrimmedFlags):
        cinematic_saturation: bool
        cinematic_contrast: bool
        cinematic_tint: bool
        cinematic_brightness: bool

    # Struct elements shared by all three DNAM alternatives. Note that we can't
    # just use MelTruncatedStruct, because upgrading the format breaks interior
    # lighting for some reason.
    ##: If this becomes common, extract into dedicated class
    _dnam_common = [
        'eye_adapt_speed', 'blur_radius', 'blur_passes', 'emissive_mult',
        'target_lum', 'upper_lum_clamp', 'bright_scale', 'bright_clamp',
        'lum_ramp_no_tex', 'lum_ramp_min', 'lum_ramp_max', 'sunlight_dimmer',
        'grass_dimmer', 'tree_dimmer', 'skin_dimmer', 'bloom_blur_radius',
        'bloom_alpha_mult_interior', 'bloom_alpha_mult_exterior',
        'get_hit_blur_radius', 'get_hit_blur_damping_constant',
        'get_hit_damping_constant', *gen_color3('night_eye_tint'),
        'night_eye_brightness', 'cinematic_saturation',
        'cinematic_avg_lum_value', 'cinematic_value',
        'cinematic_brightness_value', *gen_color3('cinematic_tint'),
        'cinematic_tint_value',
    ]
    _dnam_fmts = ['33f', '4s', '4s', '4s', '4s']
    melSet = MelSet(
        MelEdid(),
        MelUnion({
            152: MelStruct(b'DNAM', _dnam_fmts + ['B', '3s'],
                *(_dnam_common + ['unknown1', 'unused1', 'unused2', 'unused3',
                                  (_dnam_flags, 'dnam_flags'), 'unused4'])),
            148: MelStruct(b'DNAM', _dnam_fmts, *(_dnam_common + [
                'unknown1', 'unused1', 'unused2', 'unused3'])),
            132: MelStruct(b'DNAM', ['33f'], *_dnam_common),
        }, decider=SizeDecider()),
    )

#------------------------------------------------------------------------------
class MreInfo(MelRecord):
    """Dialog Response."""
    rec_sig = b'INFO'

    class _info_response_flags1(Flags):
        goodbye: bool
        random: bool
        say_once: bool
        run_immediately: bool
        info_refusal: bool
        random_end: bool
        run_for_rumors: bool
        speech_challenge: bool

    class _info_response_flags2(Flags):
        say_once_aday: bool = flag(0)
        always_darken: bool = flag(1)
        low_intelligence: bool = flag(fnv_only(4))
        high_intelligence: bool = flag(fnv_only(5))

    melSet = MelSet(
        MelTruncatedStruct(b'DATA', ['4B'], 'info_type', 'next_speaker',
            (_info_response_flags1, 'response_flags'),
            (_info_response_flags2, 'response_flags2'), old_versions={'2B'}),
        MelFid(b'QSTI', 'info_quest'),
        MelFid(b'TPIC', 'info_topic'),
        MelFid(b'PNAM', 'prev_info'),
        MelFids('add_topics', MelFid(b'NAME')),
        MelInfoResponsesFo3(),
        MelConditionsFo3(),
        MelFids('info_choices', MelFid(b'TCLT')),
        MelFids('link_from', MelFid(b'TCLF')),
        fnv_only(MelFids('follow_up', MelFid(b'TCFU'))),
        MelGroup('script_begin',
            MelEmbeddedScript(),
        ),
        MelGroup('script_end',
            MelBaseR(b'NEXT', 'script_marker'),
            MelEmbeddedScript(),
        ),
        MelFid(b'SNDD', 'unused_sndd'),
        MelString(b'RNAM', 'info_prompt'),
        MelFid(b'ANAM', 'info_speaker'),
        MelFid(b'KNAM', 'actor_value_or_perk'),
        MelUInt32(b'DNAM', 'speech_challenge')
    )

#------------------------------------------------------------------------------
class MreIngr(MelRecord):
    """Ingredient."""
    rec_sig = b'INGR'

    class _flags(Flags):
        ingr_no_auto_calc: bool
        ingr_is_food: bool

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelEquipmentTypeFo3(),
        MelWeight(),
        MelStruct(b'ENIT', [u'i', u'B', u'3s'],'value',(_flags, u'flags'),'unused1'),
        MelEffectsFo3(),
    )

#------------------------------------------------------------------------------
class MreIpct(MelRecord):
    """Impact."""
    rec_sig = b'IPCT'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelStruct(b'DATA', ['f', 'I', '2f', '2I'], 'effect_duration',
            'effect_orientation', 'angle_threshold', 'placement_radius',
            'ipct_sound_level', 'ipct_no_decal_data'),
        MelDecalData(),
        MelIpctTextureSets(with_secondary=False),
        MelIpctSounds(),
    )

#------------------------------------------------------------------------------
class MreIpds(MelRecord):
    """Impact Dataset."""
    rec_sig = b'IPDS'

    melSet = MelSet(
        MelEdid(),
        MelTruncatedStruct(
            b'DATA', ['12I'], (FID, 'impact_stone'), (FID, 'impact_dirt'),
            (FID, 'impact_grass'), (FID, 'impact_glass'),
            (FID, 'impact_metal'), (FID, 'impact_wood'),
            (FID, 'impact_organic'), (FID, 'impact_cloth'),
            (FID, 'impact_water'), (FID, 'impact_hollow_metal'),
            (FID, 'impact_organic_bug'), (FID, 'impact_organic_glow'),
            old_versions={'10I', '9I'}),
    )

#------------------------------------------------------------------------------
class MreKeym(MelRecord):
    """Key."""
    rec_sig = b'KEYM'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelScript(),
        MelDestructible(),
        MelSoundPickupDrop(),
        MelValueWeight(),
        fnv_only(MelSoundRandomLooping()),
    )

#------------------------------------------------------------------------------
class MreLand(MelRecord):
    """Landscape."""
    rec_sig = b'LAND'

    melSet = MelSet(
        MelLandShared(),
    )

#------------------------------------------------------------------------------
class MreLgtm(MelRecord):
    """Lighting Template."""
    rec_sig = b'LGTM'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', ['3B', 's', '3B', 's', '3B', 's', '2f', '2i', '3f'],
            *gen_color('lgtm_ambient_color'),
            *gen_color('lgtm_directional_color'), *gen_color('lgtm_fog_color'),
            'lgtm_fog_near', 'lgtm_fog_far', 'lgtm_directional_rotation_xy',
            'lgtm_directional_rotation_z', 'lgtm_directional_fade',
            'lgtm_fog_clip_distance', 'lgtm_fog_power'),
    )

#------------------------------------------------------------------------------
class MreLigh(MelRecord):
    """Light."""
    rec_sig = b'LIGH'

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

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelScript(),
        MelDestructible(),
        MelFull(),
        MelIcons(),
        MelStruct(b'DATA', ['i', 'I', '3B', 's', 'I', '2f', 'I', 'f'],
            'duration', 'light_radius', *gen_color('light_color'),
            (_light_flags, 'light_flags'), 'light_falloff', 'light_fov',
            'value', 'weight'),
        MelLighFade(),
        MelSound(),
    )

#------------------------------------------------------------------------------
class MreLscr(MelRecord):
    """Load Screen."""
    rec_sig = b'LSCR'

    class HeaderFlags(MelRecord.HeaderFlags):
        displays_in_main_menu: bool = flag(10)

    melSet = MelSet(
        MelEdid(),
        MelIcon(),
        MelDescription(),
        # Marked as an unused byte array in FO3Edit, but has the exact same
        # size so just treat it the same as TES4/FNV
        MelLscrLocations(),
        fnv_only(MelFid(b'WMI1', 'lscr_type')),
    )

#------------------------------------------------------------------------------
class MreLtex(MelRecord):
    """Landscape Texture."""
    rec_sig = b'LTEX'

    melSet = MelSet(
        MelEdid(),
        MelIcon(),
        MelFid(b'TNAM', 'ltex_texture'),
        MelOptStruct(b'HNAM', ['3B'], 'hd_material_type', 'hd_friction',
            'hd_restitution'), # hd = 'Havok Data'
        MelLtexSnam(),
        MelLtexGrasses(),
    )

#------------------------------------------------------------------------------
class MreLvlc(AMreLeveledList):
    """Leveled Creature."""
    rec_sig = b'LVLC'
    _top_copy_attrs = ('lvl_chance_none', 'model')
    _entry_copy_attrs = ('level', 'listId', 'count', 'item_owner',
                         'item_global', 'item_condition')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelLLChanceNone(),
        MelLLFlags(),
        MelLLItems(),
        MelModel(),
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
    _top_copy_attrs = ('lvl_chance_none', 'model')
    _entry_copy_attrs = ('level', 'listId', 'count', 'item_owner',
                         'item_global', 'item_condition')

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelLLChanceNone(),
        MelLLFlags(),
        MelLLItems(),
        MelModel(),
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
        MelFid(b'INAM','icon'),
        MelBase(b'NAM0', 'unused_0'),
        MelBase(b'NAM1', 'unused_1'),
        MelBase(b'NAM2', 'unused_2'),
        MelBase(b'NAM3', 'unused_3'),
        MelBase(b'NAM4', 'unused_4'),
        MelBase(b'NAM5', 'unused_5'),
        MelBase(b'NAM6', 'unused_6'),
        MelBase(b'NAM7', 'unused_7'),
        MelBase(b'NAM8', 'unused_8'),
        MelBase(b'NAM9', 'unused_9'),
        MelUInt32Flags(b'DNAM', u'flags', MesgTypeFlags),
        MelUInt32(b'TNAM', 'displayTime'),
        MelGroups('menu_buttons',
            MelString(b'ITXT', 'button_text'),
            MelConditionsFo3(),
        ),
    )

#------------------------------------------------------------------------------
class MreMgef(MelRecord):
    """Magic Effect."""
    rec_sig = b'MGEF'

    class _flags(Flags):
        hostile: bool = flag(0)
        recover: bool = flag(1)
        detrimental: bool = flag(2)
        magnitude: bool = flag(3)
        self: bool = flag(4)
        touch: bool = flag(5)
        target: bool = flag(6)
        noDuration: bool = flag(7)
        noMagnitude: bool = flag(8)
        noArea: bool = flag(9)
        fxPersist: bool = flag(10)
        spellmaking: bool = flag(11)
        enchanting: bool = flag(12)
        noIngredient: bool = flag(13)
        useWeapon: bool = flag(16)
        useArmor: bool = flag(17)
        useCreature: bool = flag(18)
        useSkill: bool = flag(19)
        useAttr: bool = flag(20)
        useAV: bool = flag(24)
        sprayType: bool = flag(25)
        boltType: bool = flag(26)
        noHitEffect: bool = flag(27)

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelIcon(),
        MelModel(),
        MelPartialCounter(MelStruct(b'DATA',
            ['I', 'f', 'I', '2i', 'H', '2s', 'I', 'f', '6I', '2f',
             'I', 'i'], (_flags, 'flags'), 'base_cost',
            (FID, 'associated_item'), 'school', 'resist_value',
            'counter_effect_count', 'unused1', (FID, 'light'),
            'projectileSpeed', (FID, 'effectShader'), (FID, 'enchantEffect'),
            (FID, 'castingSound'), (FID, 'boltSound'), (FID, 'hitSound'),
            (FID, 'areaSound'), 'cef_enchantment', 'cef_barter',
            'effect_archetype', 'actorValue'),
            counters={'counter_effect_count': 'counter_effects'}),
        MelSorted(MelGroups(u'counter_effects',
            MelFid(b'ESCE', u'counter_effect_code'),
        ), sort_by_attrs='counter_effect_code'),
    )

#------------------------------------------------------------------------------
class MreMicn(MelRecord):
    """Menu Icon."""
    rec_sig = b'MICN'

    melSet = MelSet(
        MelEdid(),
        MelIcons(),
    )

#------------------------------------------------------------------------------
class MreMisc(MelRecord):
    """Misc. Item."""
    rec_sig = b'MISC'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelScript(),
        MelDestructible(),
        MelSoundPickupDrop(),
        MelValueWeight(),
        fnv_only(MelSoundRandomLooping()),
    )

#------------------------------------------------------------------------------
class MreMstt(MelRecord):
    """Moveable Static."""
    rec_sig = b'MSTT'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelBase(b'DATA','data_p'),
        MelSound(),
    )

#------------------------------------------------------------------------------
class MreMusc(MelRecord):
    """Music Type."""
    rec_sig = b'MUSC'

    melSet = MelSet(
        MelEdid(),
        MelString(b'FNAM','filename'),
        fnv_only(MelFloat(b'ANAM', 'dB')),
    )

#------------------------------------------------------------------------------
class MreNavi(MelRecord):
    """Navigation Mesh Info Map."""
    rec_sig = b'NAVI'

    melSet = MelSet(
        MelEdid(),
        MelUInt32(b'NVER', 'navi_version'),
        MelGroups('navigation_map_infos',
            # Rest of this subrecord is not yet decoded
            MelExtra(MelStruct(b'NVMI', ['4s', '2I', '2h'], 'nvmi_unknown1',
                (FID, 'nvmi_navmesh'), (FID, 'nvmi_location'), 'nvmi_grid_x',
                'nvmi_grid_y'), extra_attr='nvmi_unknown2'),
        ),
        ##: This isn't right, but would need custom code to handle
        MelSimpleArray('unknownDoors', MelFid(b'NVCI')),
    )

#------------------------------------------------------------------------------
# Not mergeable due to the way this record is linked to NAVI records
class MreNavm(MelRecord):
    """Navigation Mesh."""
    rec_sig = b'NAVM'

    melSet = MelSet(
        MelEdid(),
        MelUInt32(b'NVER', 'version'),
        MelStruct(b'DATA', ['I', '5I'], (FID, 'cell_fid'), 'vertexCount',
                  'triangleCount', 'enternalConnectionsCount', 'nvcaCount',
                  'doorsCount'),
        MelArray('vertices',
            MelStruct(b'NVVX', [u'3f'], 'vertexX', 'vertexY', 'vertexZ'),
        ),
        MelArray('triangles',
            MelStruct(b'NVTR', [u'6h', u'I'], 'vertex0', 'vertex1', 'vertex2',
                      'triangle0', 'triangle1', 'triangle2', 'flags'),
        ),
        MelSInt16(b'NVCA', 'nvca_p'),
        MelArray('doors',
            MelStruct(b'NVDP', [u'I', u'H', u'2s'], (FID, 'doorReference'), 'door_triangle',
                      'doorUnknown'),
        ),
        MelBase(b'NVGD','nvgd_p'),
        MelArray('externalConnections',
            MelStruct(b'NVEX', [u'4s', u'I', u'H'], 'nvexUnknown', (FID, 'navigationMesh'),
                      'triangle'),
        ),
    )

#------------------------------------------------------------------------------
class MreNote(MelRecord):
    """Note."""
    rec_sig = b'NOTE'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelSoundPickupDrop(),
        MelUInt8(b'DATA', 'dataType'),
        MelSorted(MelSimpleArray('quests', MelFid(b'ONAM'))),
        MelString(b'XNAM','texture'),
        MelUnion({
            3: MelFid(b'TNAM', u'textTopic'),
        }, decider=AttrValDecider(u'dataType'),
            fallback=MelString(b'TNAM', u'textTopic')),
        MelSound(),
    )

#------------------------------------------------------------------------------
class _MelNpcData(MelLists):
    """Convert npc stats into health, attributes."""
    _attr_indexes = {'health': 0, 'attributes': slice(1, None)}

    def __init__(self, struct_formats):
        super(_MelNpcData, self).__init__(b'DATA', struct_formats, u'health',
            (u'attributes', [0] * int(struct_formats[-1][:-1])))

class _MelNpcDecider(SizeDecider):
    can_decide_at_dump = True
    def decide_dump(self, record):
        return len(record.attributes) + 4

class MreNpc_(AMreActorFo3):
    """Non-Player Character."""
    rec_sig = b'NPC_'

    class _flags(Flags):
        female: bool = flag(0)
        essential: bool = flag(1)
        isChargenFacePreset: bool = flag(2)
        respawn: bool = flag(3)
        autoCalc: bool = flag(4)
        pcLevelOffset: bool = flag(7)
        useTemplate: bool = flag(8)
        noLowLevel: bool = flag(9)
        noBloodSpray: bool = flag(11)
        noBloodDecal: bool = flag(12)
        noVATSMelee: bool = flag(20)
        canBeAllRaces: bool = flag(22)
        autocalcService: bool = flag(fnv_only(23))
        noKnockDown: bool = flag(26)
        notPushable: bool = flag(27)
        noRotatingHeadTrack: bool = flag(30)

    class aggroflags(Flags):
        aggroRadiusBehavior: bool

    class MelNpcDnam(MelLists):
        """Convert npc stats into skills."""
        _attr_indexes = {'skillValues': slice(14),
                         'skillOffsets': slice(14, None)}

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelStruct(b'ACBS', [u'I', u'2H', u'h', u'3H', u'f', u'2H'],
            (_flags, u'flags'),'fatigue','barterGold',
            ('level_offset',1),'calcMin','calcMax','speedMultiplier','karma',
            'dispositionBase', (AMreActorFo3.TemplateFlags, u'templateFlags')),
        MelFactions(),
        MelDeathItem(),
        MelFid(b'VTCK','voice'),
        MelFid(b'TPLT','template'),
        MelRace(),
        MelEnchantment(),
        MelUInt16(b'EAMT', 'unarmedAttackAnimation'),
        MelDestructible(),
        MelSpells(),
        MelScript(),
        MelItems(),
        MelStruct(b'AIDT', [u'5B', u'3s', u'I', u'b', u'B', u'b', u'B', u'i'], 'aggression', ('confidence',2),
                  ('energyLevel', 50),('responsibility', 50), 'mood',
                  'unused_aidt',(aiService, u'services'),
                  ('trainSkill', -1), 'trainLevel', 'assistance',
                  (aggroflags, u'aggroRadiusBehavior'), 'aggroRadius'),
        MelFids('aiPackages', MelFid(b'PKID')),
        MelAnimations(),
        MelFid(b'CNAM','iclass'),
        MelUnion({
            11: _MelNpcData([u'I', u'7B']),
            25: _MelNpcData([u'I', u'21B'])
        }, decider=_MelNpcDecider()),
        MelSorted(MelFids('headParts', MelFid(b'PNAM'))),
        MelNpcDnam(b'DNAM', [u'14B', u'14B'], (u'skillValues', [0] * 14),
                   (u'skillOffsets', [0] * 14)),
        MelFid(b'HNAM', 'hair'),
        MelFloat(b'LNAM', u'hairLength'),
        MelFid(b'ENAM', 'eye'),
        MelStruct(b'HCLR', [u'3B', u's'],'hairRed','hairBlue','hairGreen','unused3'),
        MelCombatStyle(),
        MelUInt32(b'NAM4', u'impactMaterialType'),
        MelBase(b'FGGS','fggs_p'), ####FaceGen Geometry-Symmetric
        MelBase(b'FGGA','fgga_p'), ####FaceGen Geometry-Asymmetric
        MelBase(b'FGTS','fgts_p'), ####FaceGen Texture-Symmetric
        MelUInt16(b'NAM5', u'unknown'),
        MelFloat(b'NAM6', u'height'),
        MelFloat(b'NAM7', u'weight'),
    )

#------------------------------------------------------------------------------
class MelIdleHandler(MelGroup):
    """Occurs three times in PACK, so moved here to deduplicate the
    definition a bit."""

    class _variableFlags(Flags):
        isLongOrShort: bool

    def __init__(self, ih_sig, ih_attr):
        super(MelIdleHandler, self).__init__(ih_attr,
            MelBase(ih_sig, ih_attr + u'_marker'),
            MelFid(b'INAM', u'idle_anim'),
            MelEmbeddedScript(),
            MelFid(b'TNAM', u'topic'),
        )

class MelLocation2(MelUnion):
    """Occurs twice in PACK, so moved here to deduplicate the definition a
    bit."""
    def __init__(self, loc2_prefix):
        loc2_type = loc2_prefix + u'_type'
        loc2_id = loc2_prefix + u'_id'
        loc2_radius = loc2_prefix + u'_radius'
        super(MelLocation2, self).__init__({
            (0, 1, 4): MelOptStruct(b'PLD2', [u'i', u'I', u'i'], loc2_type,
                                    (FID, loc2_id), loc2_radius),
            (2, 3, 6, 7): MelOptStruct(b'PLD2', [u'i', u'4s', u'i'],
                                       loc2_type, loc2_id, loc2_radius),
            5: MelOptStruct(b'PLD2', [u'i', u'I', u'i'], loc2_type,
                            loc2_id, loc2_radius),
        }, decider=PartialLoadDecider(
            loader=MelSInt32(b'PLD2', loc2_type),
            decider=AttrValDecider(loc2_type),
        ))

class MrePack(MelRecord):
    """Package."""
    rec_sig = b'PACK'

    class _flags(Flags):
        offersServices: bool
        mustReachLocation: bool
        mustComplete: bool
        lockAtStart: bool
        lockAtEnd: bool
        lockAtLocation: bool
        unlockAtStart: bool
        unlockAtEnd: bool
        unlockAtLocation: bool
        continueIfPcNear: bool
        oncePerDay: bool
        skipFallout: bool = flag(12)
        alwaysRun: bool
        alwaysSneak: bool = flag(17)
        allowSwimming: bool
        allowFalls: bool
        unequipArmor: bool
        unequipWeapons: bool
        defensiveCombat: bool
        useHorse: bool
        noIdleAnims: bool

    class _fallout_behavior_flags(TrimmedFlags):
        hellos_to_player: bool
        random_conversations: bool
        observe_combat_behavior: bool
        unknown_flag_4: bool    # unknown but not unused
        reaction_to_player_actions: bool
        friendly_fire_comments: bool
        aggro_radius_behavior: bool
        allow_idle_chatter: bool
        avoid_radiation: bool

    class _dialogue_data_flags(Flags):
        no_headtracking: bool = flag(0)
        dont_control_target_movement: bool = flag(8)

    melSet = MelSet(
        MelEdid(), # required
        MelTruncatedStruct(
            b'PKDT', [u'I', u'2H', u'I'], (_flags, u'flags'), u'aiType',
            (_fallout_behavior_flags, u'falloutBehaviorFlags'),
            u'typeSpecificFlags', old_versions={u'I2H'}), # required
        MelUnion({
            (0, 1, 4): MelOptStruct(b'PLDT', [u'i', u'I', u'i'], u'locType',
                (FID, u'locId'), u'locRadius'),
            (2, 3, 6, 7): MelOptStruct(b'PLDT', [u'i', u'4s', u'i'], u'locType', u'locId',
                u'locRadius'),
            5: MelOptStruct(b'PLDT', [u'i', u'I', u'i'], u'locType', u'locId',
                u'locRadius'),
        }, decider=PartialLoadDecider(
            loader=MelSInt32(b'PLDT', u'locType'),
            decider=AttrValDecider(u'locType'),
        )),
        MelLocation2(u'loc2'),
        MelStruct(b'PSDT', [u'2b', u'B', u'b', u'i'], 'month', 'day', 'date',
                  'time', 'duration'), # required
        MelUnion({
            (0, 1): MelTruncatedStruct(b'PTDT', [u'i', u'I', u'i', u'f'], u'targetType',
                (FID, u'targetId'), u'targetCount', u'targetUnknown1',
                is_optional=True, old_versions={u'iIi'}),
            2: MelTruncatedStruct(b'PTDT', [u'i', u'I', u'i', u'f'], u'targetType', u'targetId',
                u'targetCount', u'targetUnknown1', is_optional=True,
                old_versions={u'iIi'}),
            3: MelTruncatedStruct(b'PTDT', [u'i', u'4s', u'i', u'f'], u'targetType',
                u'targetId', u'targetCount', u'targetUnknown1',
                is_optional=True, old_versions={u'i4si'}),
        }, decider=PartialLoadDecider(
            loader=MelSInt32(b'PTDT', u'targetType'),
            decider=AttrValDecider(u'targetType'),
        )),
        MelConditionsFo3(),
        MelGroup('idleAnimations',
            MelUInt8(b'IDLF', 'animationFlags'),
            MelIdleAnimationCountOld(),
            MelIdleTimerSetting(),
            MelIdleAnimations(),
            MelBase(b'IDLB','idlb_p'),
        ),
        MelBase(b'PKED','eatMarker'),
        MelUInt32(b'PKE2', 'escortDistance'),
        MelCombatStyle(b'CNAM'),
        MelFloat(b'PKFD', 'followStartLocationTrigerRadius'),
        MelBase(b'PKPT','patrolFlags'), # byte or short
        MelOptStruct(b'PKW3', [u'I', u'B', u'B', u'3H', u'f', u'f', u'4s'],'weaponFlags','fireRate','fireCount','numBursts',
                     'shootPerVolleysMin','shootPerVolleysMax','pauseBetweenVolleysMin','pauseBetweenVolleysMax','weaponUnknown'),
        MelUnion({
            (0, 1): MelTruncatedStruct(b'PTD2', [u'i', u'I', u'i', u'f'], u'targetType2',
                (FID, u'targetId2'), u'targetCount2', u'targetUnknown2',
                is_optional=True, old_versions={u'iIi'}),
            2: MelTruncatedStruct(b'PTD2', [u'i', u'I', u'i', u'f'], u'targetType2',
                u'targetId2', u'targetCount2', u'targetUnknown2',
                is_optional=True, old_versions={u'iIi'}),
            3: MelTruncatedStruct(b'PTD2', [u'i', u'4s', u'i', u'f'], u'targetType2',
                u'targetId2', u'targetCount2', u'targetUnknown2',
                is_optional=True, old_versions={u'i4si'}),
        }, decider=PartialLoadDecider(
            loader=MelSInt32(b'PTD2', u'targetType2'),
            decider=AttrValDecider(u'targetType2'),
        )),
        MelBase(b'PUID','useItemMarker'),
        MelBase(b'PKAM','ambushMarker'),
        MelTruncatedStruct(
            b'PKDD', [u'f', u'2I', u'4s', u'I', u'4s'], 'dialFov',
            (FID, 'dialTopic'), (_dialogue_data_flags, 'dialFlags'),
            'dialUnknown1', 'dialType', 'dialUnknown2', is_optional=True,
            old_versions={'f2I4sI', 'f2I4s', 'f2I'}),
        MelLocation2(u'loc2_again'),
        MelIdleHandler(b'POBA', u'on_begin'), # required
        MelIdleHandler(b'POEA', u'on_end'), # required
        MelIdleHandler(b'POCA', u'on_change'), # required
    ).with_distributor({
        b'PKDT': {
            b'PLD2': u'loc2_type',
        },
        b'PSDT': {
            b'PLD2': u'loc2_again_type',
        },
        b'POBA': {
            b'INAM|SCHR|SCDA|SCTX|SLSD|SCVR|SCRO|SCRV|TNAM': u'on_begin',
        },
        b'POEA': {
            b'INAM|SCHR|SCDA|SCTX|SLSD|SCVR|SCRO|SCRV|TNAM': u'on_end',
        },
        b'POCA': {
            b'INAM|SCHR|SCDA|SCTX|SLSD|SCVR|SCRO|SCRV|TNAM': u'on_change',
        },
    })

#------------------------------------------------------------------------------
class MrePerk(MelRecord):
    """Perk."""
    rec_sig = b'PERK'

    class _script_flags(Flags):
        run_immediately: bool

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelIcons(),
        MelConditionsFo3(),
        MelPerkData(),
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
                MelConditionsFo3(),
            ), sort_by_attrs='pe_run_on'),
            MelPerkParamsGroups(
                # EPFT has the following meanings:
                #  0: Unknown
                #  1: EPFD=float
                #  2: EPFD=float, float
                #  3: EPFD=fid (LVLI)
                #  4: EPFD=Null (Script)
                # There is a special case: if EPFT is 2 and the pe_function
                # (see DATA above) is 5, then EPFD=int, float - we use a return
                # value of 8 for this.
                MelUInt8(b'EPFT', 'pp_param_type'),
                MelUnion({
                    (0, 4): MelBase(b'EPFD', 'pp_param1'),
                    1: MelFloat(b'EPFD', 'pp_param1'),
                    2: MelStruct(b'EPFD', ['2f'], 'pp_param1', 'pp_param2'),
                    3: MelFid(b'EPFD', 'pp_param1'),
                    8: MelStruct(b'EPFD', ['I', 'f'], 'pp_param1',
                        'pp_param2'),
                }, decider=PerkEpdfDecider({5})),
                MelString(b'EPF2', 'pp_button_label'),
                MelUInt16Flags(b'EPF3', 'pp_script_flags', _script_flags),
                MelEmbeddedScript(),
            ),
            MelBaseR(b'PRKF', 'pe_end_marker'),
        ), sort_special=perk_effect_key),
    ).with_distributor(perk_distributor)

#------------------------------------------------------------------------------
class MrePgre(MelRecord):
    """Placed Grenade."""
    rec_sig = b'PGRE'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'NAME','base'),
        MelFid(b'XEZN','encounterZone'),
        MelBase(b'XRGD','ragdollData'),
        MelBase(b'XRGB','ragdollBipedData'),
        MelGroup('patrolData',
            MelFloat(b'XPRD', 'idleTime'),
            MelBase(b'XPPA','patrolScriptMarker'),
            MelFid(b'INAM', 'idle'),
            MelEmbeddedScript(),
            MelFid(b'TNAM','topic'),
        ),
        MelOwnership(),
        MelSInt32(b'XCNT', 'count'),
        MelFloat(b'XRDS', 'radius'),
        MelFloat(b'XHLP', 'health'),
        MelReflectedRefractedBy(),
        MelLinkedDecals(),
        MelFid(b'XLKR','linkedReference'),
        MelOptStruct(b'XCLP', [u'8B'],'linkStartColorRed','linkStartColorGreen','linkStartColorBlue','linkColorUnused1',
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue','linkColorUnused2'),
        MelActivateParents(),
        fnv_only(MelActivationPrompt()),
        MelEnableParent(),
        MelFid(b'XEMI', u'emittance'),
        MelFid(b'XMBR','multiboundReference'),
        MelBase(b'XIBS','ignoredBySandbox'),
        MelRefScale(),
        MelRef3D(),
    )

#------------------------------------------------------------------------------
class MrePmis(MelRecord):
    """Placed Missile."""
    rec_sig = b'PMIS'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'NAME','base'),
        MelFid(b'XEZN','encounterZone'),
        MelBase(b'XRGD','ragdollData'),
        MelBase(b'XRGB','ragdollBipedData'),
        MelGroup('patrolData',
            MelFloat(b'XPRD', 'idleTime'),
            MelBase(b'XPPA','patrolScriptMarker'),
            MelFid(b'INAM', 'idle'),
            MelEmbeddedScript(),
            MelFid(b'TNAM','topic'),
        ),
        MelOwnership(),
        MelSInt32(b'XCNT', 'count'),
        MelFloat(b'XRDS', 'radius'),
        MelFloat(b'XHLP', 'health'),
        MelReflectedRefractedBy(),
        MelLinkedDecals(),
        MelFid(b'XLKR','linkedReference'),
        MelOptStruct(b'XCLP', [u'8B'],'linkStartColorRed','linkStartColorGreen','linkStartColorBlue','linkColorUnused1',
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue','linkColorUnused2'),
        MelActivateParents(),
        fnv_only(MelActivationPrompt()),
        MelEnableParent(),
        MelFid(b'XEMI', u'emittance'),
        MelFid(b'XMBR','multiboundReference'),
        MelBase(b'XIBS','ignoredBySandbox'),
        MelRefScale(),
        MelRef3D(),
    )

#------------------------------------------------------------------------------
class MreProj(MelRecord):
    """Projectile."""
    rec_sig = b'PROJ'

    class _flags(Flags):
        is_hitscan: bool = flag(0)
        is_explosive: bool = flag(1)
        alt_trigger: bool = flag(2)
        has_muzzle_flash: bool = flag(3)
        can_be_disabled: bool = flag(5)
        can_be_picked_up: bool = flag(6)
        is_super_sonic: bool = flag(7)
        pins_limbs: bool = flag(8)
        pass_through_small_transparent: bool = flag(9)
        projectile_detonates: bool = flag(fnv_only(10))
        projectile_rotates: bool = flag(fnv_only(11))

    # Attributes shared between FO3 and FNV for the DATA subrecord
    _shared_data = [(_flags, 'flags'), 'type', 'gravity', ('speed', 10000.0),
                    ('range', 10000.0), (FID, 'light'), (FID, 'muzzleFlash'),
                    'tracerChance', 'explosionAltTrigerProximity',
                    'explosionAltTrigerTimer', (FID, 'explosion'),
                    (FID, 'sound'), 'muzzleFlashDuration', 'fadeDuration',
                    'impactForce', (FID, 'sound_countdown'),
                    (FID, 'sound_disable'), (FID, 'defaultWeaponSource')]

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        if_fnv(
            fo3_version=MelStruct(
                b'DATA', [u'2H', u'3f', u'2I', u'3f', u'2I', u'3f', u'3I'],
                *_shared_data),
            fnv_version=MelTruncatedStruct(
                b'DATA', [u'2H', u'3f', u'2I', u'3f', u'2I', u'3f', u'3I',
                          u'4f'],
                *(_shared_data + ['rotationX', 'rotationY', 'rotationZ',
                                  'bouncyMult']),
                old_versions={'2H3f2I3f2I3f3If', '2H3f2I3f2I3f3I'}),
        ),
        MelString(b'NAM1','muzzleFlashPath'),
        MelBase(b'NAM2','_nam2'),
        MelUInt32(b'VNAM', 'soundLevel'),
    )

#------------------------------------------------------------------------------
class MrePwat(MelRecord):
    """Placeable Water."""
    rec_sig = b'PWAT'

    class _flags(Flags):
        reflects: bool = flag(0)
        reflectsActers: bool = flag(1)
        reflectsLand: bool = flag(2)
        reflectsLODLand: bool = flag(3)
        reflectsLODBuildings: bool = flag(4)
        reflectsTrees: bool = flag(5)
        reflectsSky: bool = flag(6)
        reflectsDynamicObjects: bool = flag(7)
        reflectsDeadBodies: bool = flag(8)
        refracts: bool = flag(9)
        refractsActors: bool = flag(10)
        refractsLands: bool = flag(11)
        refractsDynamicObjects: bool = flag(16)
        refractsDeadBodies: bool = flag(17)
        silhouetteReflections: bool = flag(18)
        depth: bool = flag(28)
        objectTextureCoordinates: bool = flag(29)
        noUnderwaterFog: bool = flag(31)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelStruct(b'DNAM', [u'2I'],(_flags,'flags'),(FID,'water'))
    )

#------------------------------------------------------------------------------
class MreQust(MelRecord):
    """Quest."""
    rec_sig = b'QUST'

    class _questFlags(Flags):
        startGameEnabled: bool
        repeatedTopics: bool = flag(2)
        repeatedStages: bool

    class stageFlags(Flags):
        complete: bool

    class targetFlags(Flags):
        ignoresLocks: bool

    melSet = MelSet(
        MelEdid(),
        MelScript(),
        MelFull(),
        MelIcon(),
        MelTruncatedStruct(b'DATA', [u'2B', u'2s', u'f'], (_questFlags, u'questFlags'),
                           'priority', 'unused2',
                           'questDelay', old_versions={'2B'}),
        MelConditionsFo3(),
        MelSorted(MelGroups('stages',
            MelSInt16(b'INDX', 'stage'),
            MelGroups('entries',
                MelUInt8Flags(b'QSDT', u'flags', stageFlags),
                MelConditionsFo3(),
                MelString(b'CNAM','text'),
                MelEmbeddedScript(),
                MelFid(b'NAM0', 'nextQuest'),
            ),
        ), sort_by_attrs='stage'),
        MelGroups('objectives',
            MelSInt32(b'QOBJ', 'index'),
            MelString(b'NNAM', 'display_text'),
            MelGroups('targets',
                MelStruct(b'QSTA', [u'I', u'B', u'3s'],(FID,'targetId'),(targetFlags,'flags'),'unused1'),
                MelConditionsFo3(),
            ),
        ),
    ).with_distributor({
        b'EDID|DATA': { # just in case one is missing
            b'CTDA': u'conditions',
        },
        b'INDX': {
            b'CTDA': u'stages',
        },
        b'QOBJ': {
            b'CTDA': u'objectives',
        },
    })

#------------------------------------------------------------------------------
# TODO(inf) Using this for Oblivion would be nice, but faces.py seems to
#  use those attributes directly, so that would need rewriting
class MelRaceFaceGen(MelGroup):
    """Defines facegen subrecords for RACE."""
    def __init__(self, facegen_attr):
        super(MelRaceFaceGen, self).__init__(facegen_attr,
            MelBase(b'FGGS', u'fggs_p'), # FaceGen Geometry - Symmetric
            MelBase(b'FGGA', u'fgga_p'), # FaceGen Geometry - Asymmetric
            MelBase(b'FGTS', u'fgts_p'), # FaceGen Texture  - Symmetric
            MelStruct(b'SNAM', [u'2s'], u'snam_p'))

class MreRace(AMreRace):
    """Race."""
    rec_sig = b'RACE'

    class _flags(Flags):
        playable: bool = flag(0)
        child: bool = flag(2)

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelRelations(),
        MelRaceData(b'DATA', ['14b', '2s', '4f', 'I'], ('skills', [0] * 14),
                    'unused1', 'maleHeight', 'femaleHeight', 'maleWeight',
                    'femaleWeight', (_flags, 'flags')),
        MelFid(b'ONAM','Older'),
        MelFid(b'YNAM','Younger'),
        MelBaseR(b'NAM2', 'unknown_marker'),
        MelRaceVoices(b'VTCK', [u'2I'], (FID, 'maleVoice'), (FID, 'femaleVoice')),
        MelOptStruct(b'DNAM', ['2I'], (FID, 'defaultHairMale'),
                     (FID, 'defaultHairFemale')),
        # Int corresponding to GMST sHairColorNN
        MelStruct(b'CNAM', [u'2B'],'defaultHairColorMale','defaultHairColorFemale'),
        MelFloat(b'PNAM', 'mainClamp'),
        MelFloat(b'UNAM', 'faceClamp'),
        MelStruct(b'ATTR', [u'2s'], u'unused_attributes'), # leftover
        MelBaseR(b'NAM0', 'head_data_marker'),
        MelBaseR(b'MNAM', 'male_head_data_marker'),
        MelRaceParts({
            0: u'maleHead',
            1: u'maleEars',
            2: u'maleMouth',
            3: u'maleTeethLower',
            4: u'maleTeethUpper',
            5: u'maleTongue',
            6: u'maleLeftEye',
            7: u'maleRightEye',
        }, group_loaders=lambda indx: (MelRaceHeadPart(indx),)),
        MelBaseR(b'FNAM', 'female_head_data_marker'),
        MelRaceParts({
            0: u'femaleHead',
            1: u'femaleEars',
            2: u'femaleMouth',
            3: u'femaleTeethLower',
            4: u'femaleTeethUpper',
            5: u'femaleTongue',
            6: u'femaleLeftEye',
            7: u'femaleRightEye',
        }, group_loaders=lambda indx: (MelRaceHeadPart(indx),)),
        MelBaseR(b'NAM1', 'body_data_marker'),
        MelBaseR(b'MNAM', 'male_body_data_marker'),
        MelRaceParts({
            0: u'maleUpperBody',
            1: u'maleLeftHand',
            2: u'maleRightHand',
            3: u'maleUpperBodyTexture',
        }, group_loaders=lambda _indx: (
            MelIcons(),
            MelModel(),
        )),
        MelBaseR(b'FNAM', 'female_body_data_marker'),
        MelRaceParts({
            0: u'femaleUpperBody',
            1: u'femaleLeftHand',
            2: u'femaleRightHand',
            3: u'femaleUpperBodyTexture',
        }, group_loaders=lambda _indx: (
            MelIcons(),
            MelModel(),
        )),
        # Note: xEdit marks both HNAM and ENAM as sorted. They are not, but
        # changing it would cause too many conflicts. We do *not* want to mark
        # them as sorted here, because that's what the Race Checker is for!
        MelSimpleArray('hairs', MelFid(b'HNAM')),
        MelSimpleArray('eyes', MelFid(b'ENAM')),
        MelBaseR(b'MNAM', 'male_facegen_marker'),
        MelRaceFaceGen('maleFaceGen'),
        MelBaseR(b'FNAM', 'female_facegen_marker'),
        MelRaceFaceGen('femaleFaceGen'),
    ).with_distributor({
        b'NAM0': {
            b'MNAM': (u'male_head_data_marker', {
                b'INDX|ICON|MICO|MODL|MODB|MODT|MODS|MODD': u'maleHead',
            }),
            b'FNAM': (u'female_head_data_marker', {
                b'INDX|ICON|MICO|MODL|MODB|MODT|MODS|MODD': u'femaleHead',
            }),
        },
        b'NAM1': {
            b'MNAM': (u'male_body_data_marker', {
                b'INDX|ICON|MICO|MODL|MODB|MODT|MODS|MODD': u'maleUpperBody',
            }),
            b'FNAM': (u'female_body_data_marker', {
                b'INDX|ICON|MICO|MODL|MODB|MODT|MODS|MODD': u'femaleUpperBody',
            }),
        },
        b'ENAM': {
            b'MNAM': (u'male_facegen_marker', {
                b'FGGS|FGGA|FGTS|SNAM': u'maleFaceGen',
            }),
            b'FNAM': (u'female_facegen_marker', {
                b'FGGS|FGGA|FGTS|SNAM': u'femaleFaceGen',
            }),
        },
    })

#------------------------------------------------------------------------------
class MreRads(MelRecord):
    """Radiation Stage."""
    rec_sig = b'RADS'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', [u'2I'],'trigerThreshold',(FID,'actorEffect')),
    )

#------------------------------------------------------------------------------
class MreRefr(MelRecord):
    """Placed Object."""
    rec_sig = b'REFR'

    class HeaderFlags(VWDFlag, NavMeshFlags, MelRecord.HeaderFlags):
        hidden_from_local_map: bool = flag(6)   # DOOR
        inaccessible: bool = flag(8)            # DOOR
        doesnt_light_water: bool = flag(8)      # LIGH
        casts_shadows: bool = flag(9)           # LIGH
        motion_blur: bool = flag(9)             # MSTT?
        persistent: bool = flag(10)
        full_lod: bool = flag(16)               # non-LIGH?
        never_fades: bool = flag(16)            # LIGH
        doesnt_light_landscape: bool = flag(17) # LIGH
        no_ai_acquire: bool = flag(25)
        reflected_by_auto_water: bool = flag(28)# LIGH
        no_respawn: bool = flag(30)
        multi_bound: bool = flag(31)

    class _lockFlags(Flags):
        leveledLock: bool = flag(2)

    class _destinationFlags(Flags):
        noAlarm: bool

    melSet = MelSet(
        MelEdid(),
        MelOptStruct(b'RCLR', [u'8B'],'referenceStartColorRed','referenceStartColorGreen','referenceStartColorBlue','referenceColorUnused1',
                     'referenceEndColorRed','referenceEndColorGreen','referenceEndColorBlue','referenceColorUnused2'),
        MelFid(b'NAME','base'),
        MelFid(b'XEZN','encounterZone'),
        MelBase(b'XRGD','ragdollData'),
        MelBase(b'XRGB','ragdollBipedData'),
        MelOptStruct(b'XPRM', [u'3f', u'3I', u'f', u'I'], u'primitiveBoundX',
            u'primitiveBoundY', u'primitiveBoundZ', u'primitiveColorRed',
            u'primitiveColorGreen', u'primitiveColorBlue', u'primitiveUnknown',
            u'primitiveType'),
        MelUInt32(b'XTRI', 'collisionLayer'),
        MelBase(b'XMBP','multiboundPrimitiveMarker'),
        MelOptStruct(b'XMBO', [u'3f'],'boundHalfExtentsX','boundHalfExtentsY','boundHalfExtentsZ'),
        MelOptStruct(b'XTEL', [u'I', u'6f', u'I'],(FID,'destinationFid'),'destinationPosX','destinationPosY',
            'destinationPosZ','destinationRotX','destinationRotY','destinationRotZ',(_destinationFlags,'destinationFlags')),
        MelMapMarker(with_reputation=fnv_only(True)),
        fnv_only(MelGroup('audioData',
            MelBase(b'MMRK', 'audioMarker'),
            MelBase(b'FULL', 'full_p'),
            MelFid(b'CNAM', 'audioLocation'),
            MelBase(b'BNAM', 'bnam_p'),
            MelBase(b'MNAM', 'mnam_p'),
            MelBase(b'NNAM', 'nnam_p'),
        )),
        fnv_only(MelBase(b'XSRF', 'xsrf_p')),
        fnv_only(MelBase(b'XSRD', 'xsrd_p')),
        MelFid(b'XTRG','targetId'),
        MelSInt32(b'XLCM', u'levelMod'),
        MelGroup('patrolData',
            MelFloat(b'XPRD', 'idleTime'),
            MelBase(b'XPPA','patrolScriptMarker'),
            MelFid(b'INAM', 'idle'),
            MelEmbeddedScript(),
            MelFid(b'TNAM','topic'),
        ),
        MelOptStruct(b'XRDO', [u'f', u'I', u'f', u'I'],'rangeRadius','broadcastRangeType','staticPercentage',(FID,'positionReference')),
        MelOwnership(),
        ##: I dropped special handling here, looks like a regular truncated
        # record to me - but no way to test since we don't load this yet
        MelTruncatedStruct(
            b'XLOC', [u'B', u'3s', u'I', u'4s', u'B', u'3s', u'4s'], 'lockLevel', 'unused1',
            (FID, 'lockKey'), 'unused2', (_lockFlags, 'lockFlags'),
            'unused3', 'unused4', is_optional=True,
            old_versions={'B3sI4s'}),
        MelSInt32(b'XCNT', 'count'),
        MelFloat(b'XRDS', 'radius'),
        MelFloat(b'XHLP', 'health'),
        MelFloat(b'XRAD', 'radiation'),
        MelFloat(b'XCHG', u'charge'),
        MelGroup('ammo',
            MelFid(b'XAMT','type'),
            MelUInt32(b'XAMC', 'count'),
        ),
        MelReflectedRefractedBy(),
        MelSorted(MelFids('litWaters', MelFid(b'XLTW'))),
        MelLinkedDecals(),
        MelFid(b'XLKR','linkedReference'),
        MelOptStruct(b'XCLP', [u'8B'],'linkStartColorRed','linkStartColorGreen','linkStartColorBlue','linkColorUnused1',
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue','linkColorUnused2'),
        MelActivateParents(),
        fnv_only(MelActivationPrompt()),
        MelEnableParent(),
        MelFid(b'XEMI', u'emittance'),
        MelFid(b'XMBR','multiboundReference'),
        MelActionFlags(),
        MelBase(b'ONAM','onam_p'),
        MelBase(b'XIBS','ignoredBySandbox'),
        MelOptStruct(b'XNDP', [u'2I'],(FID,'navMesh'),'unknown'),
        MelOptStruct(b'XPOD', [u'I', u'I'],(FID,'portalDataRoom0'),(FID,'portalDataRoom1')),
        MelOptStruct(b'XPTL', [u'9f'],'portalWidth','portalHeight','portalPosX','portalPosY','portalPosZ',
                     'portalRot1','portalRot2','portalRot3','portalRot4'),
        ####SpeedTree Seed, if it's a single byte then it's an offset into the list of seed values in the TREE record
        ####if it's 4 byte it's the seed value directly.
        MelBase(b'XSED','speedTreeSeed'),
        MelGroup('bound_data',
            MelPartialCounter(MelStruct(b'XRMR', ['H', '2s'],
                'linked_rooms_count', 'unknown1'),
                counters={'linked_rooms_count': 'linked_rooms'}),
            MelSorted(MelFids('linked_rooms', MelFid(b'XLRM'))),
        ),
        MelOptStruct(b'XOCP', [u'9f'], 'occlusionPlaneWidth',
            'occlusionPlaneHeight', 'occlusionPlanePosX', 'occlusionPlanePosY',
            'occlusionPlanePosZ', 'occlusionPlaneRot1', 'occlusionPlaneRot2',
            'occlusionPlaneRot3', 'occlusionPlaneRot4'),
        MelOptStruct(b'XORD', ['4I'], (FID, 'linkedOcclusionPlane0'),
            (FID, 'linkedOcclusionPlane1'), (FID, 'linkedOcclusionPlane2'),
            (FID, 'linkedOcclusionPlane3')),
        MelXlod(),
        MelRefScale(),
        MelRef3D(),
    )

#------------------------------------------------------------------------------
class MreRegn(MelRecord):
    """Region."""
    rec_sig = b'REGN'

    class HeaderFlags(MelRecord.HeaderFlags):
        border_region: bool = flag(6)

    class obflags(Flags):
        conform: bool
        paintVertices: bool
        sizeVariance: bool
        deltaX: bool
        deltaY: bool
        deltaZ: bool
        Tree: bool
        hugeRock: bool

    class sdflags(Flags):
        pleasant: bool
        cloudy: bool
        rainy: bool
        snowy: bool

    class rdatFlags(Flags):
        Override: bool

    melSet = MelSet(
        MelEdid(),
        MelIcons(),
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
            MelRegnEntrySubrecord(2, MelArray('objects',
                MelStruct(b'RDOT',
                    [u'I', u'H', u'2s', u'f', u'4B', u'2H', u'5f', u'3H',
                     u'2s', u'4s'], (FID, 'objectId'),
                    'parentIndex', 'unk1', 'density', 'clustering',
                    'minSlope', 'maxSlope', (obflags, 'flags'),
                    'radiusWRTParent', 'radius', 'minHeight', 'maxHeight',
                    'sink', 'sinkVar', 'sizeVar', 'angleVarX', 'angleVarY',
                    'angleVarZ', 'unk2', 'unk3'),
            )),
            MelRegnEntrySubrecord(4, MelString(b'RDMP', 'mapName')),
            MelRegnEntrySubrecord(6, MelSorted(MelArray('grasses',
                MelStruct(b'RDGS', [u'I', u'4s'], (FID, 'grass'), 'unknown'),
            ), sort_by_attrs='grass')),
            MelRegnEntrySubrecord(7, MelUInt32(b'RDMD', 'musicType')),
            MelRegnEntrySubrecord(7, MelFid(b'RDMO', 'music')),
            fnv_only(MelRegnEntrySubrecord(
                7, MelFid(b'RDSI', 'incidentalMediaSet'))),
            fnv_only(MelRegnEntrySubrecord(
                7, MelFids('battleMediaSets', MelFid(b'RDSB')))),
            MelRegnEntrySubrecord(7, MelSorted(MelArray('sounds',
                MelStruct(b'RDSD', [u'3I'], (FID, 'sound'), (sdflags, 'flags'),
                          'chance'),
            ), sort_by_attrs='sound')),
            MelRegnEntrySubrecord(3, MelSorted(MelArray('weatherTypes',
                MelStruct(b'RDWT', [u'3I'], (FID, u'weather'), u'chance',
                          (FID, u'global')),
            ), sort_by_attrs='weather')),
            fnv_only(MelRegnEntrySubrecord(
                8, MelSimpleArray('imposters', MelFid(b'RDID')))),
        ), sort_by_attrs='entryType'),
    )

#------------------------------------------------------------------------------
class MreRgdl(MelRecord):
    """Ragdoll."""
    rec_sig = b'RGDL'

    class _flags(Flags):
        disableOnMove: bool

    melSet = MelSet(
        MelEdid(),
        MelUInt32(b'NVER', 'version'),
        MelStruct(b'DATA', [u'I', u'4s', u'5B', u's'],'boneCount','unused1','feedback',
            'footIK','lookIK','grabIK','poseMatching','unused2'),
        MelFid(b'XNAM','actorBase'),
        MelFid(b'TNAM','bodyPartData'),
        MelStruct(b'RAFD', [u'13f', u'2i'],'keyBlendAmount','hierarchyGain','positionGain',
            'velocityGain','accelerationGain','snapGain','velocityDamping',
            'snapMaxLinearVelocity','snapMaxAngularVelocity','snapMaxLinearDistance',
            'snapMaxAngularDistance','posMaxVelLinear',
            'posMaxVelAngular','posMaxVelProjectile','posMaxVelMelee'),
        MelArray('feedbackDynamicBones',
            MelUInt16(b'RAFB', 'bone'),
        ),
        MelStruct(b'RAPS', [u'3H', u'B', u's', u'4f'],'matchBones1','matchBones2','matchBones3',
            (_flags,'flags'),'unused3','motorsStrength',
            'poseActivationDelayTime','matchErrorAllowance',
            'displacementToDisable',),
        MelString(b'ANAM','deathPose'),
    )

#------------------------------------------------------------------------------
class MreScol(MelRecord):
    """Static Collection."""
    rec_sig = b'SCOL'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelGroups('parts',
            MelFid(b'ONAM','static'),
            MelSorted(MelArray('placements',
                MelStruct(b'DATA', [u'7f'], u'posX', u'posY', u'posZ', u'rotX',
                          u'rotY', u'rotZ', u'scale'),
            ), sort_by_attrs=('posX', 'posY', 'posZ', 'rotX', 'rotY', 'rotZ',
                              'scale')),
        ),
    )

#------------------------------------------------------------------------------
class MreScpt(MelRecord):
    """Script."""
    rec_sig = b'SCPT'

    melSet = MelSet(
        MelEdid(),
        MelEmbeddedScript(),
    )

#------------------------------------------------------------------------------
class MreSoun(MelRecord):
    """Sound."""
    rec_sig = b'SOUN'
    _has_duplicate_attrs = True # SNDX, ANAM, GNAM and HNAM upgrade to SNDD

    class _flags(Flags):
        randomFrequencyShift: bool = flag(0)
        playAtRandom: bool = flag(1)
        environmentIgnored: bool = flag(2)
        randomLocation: bool = flag(3)
        loop: bool = flag(4)
        menuSound: bool = flag(5)
        twoD: bool = flag(6)
        three60LFE: bool = flag(7)
        dialogueSound: bool = flag(8)
        envelopeFast: bool = flag(9)
        envelopeSlow: bool = flag(10)
        twoDRadius: bool = flag(11)
        muteWhenSubmerged: bool = flag(12)
        startatRandomPosition: bool = flag(fnv_only(13))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelString(b'FNAM','soundFile'),
        fnv_only(MelUInt8(b'RNAM', 'random_chance')),
        MelStruct(b'SNDD', [u'2B', u'b', u's', u'I', u'h', u'2B', u'6h', u'3i'], 'minDist', 'maxDist', 'freqAdj',
                  'unusedSndd', (_flags, 'flags'), 'staticAtten',
                  'stopTime', 'startTime', 'point0', 'point1', 'point2',
                  'point3', 'point4', 'reverb', 'priority', 'xLoc', 'yLoc'),
        # These are the older format - read them, but only write out SNDD
        MelReadOnly(
            MelStruct(b'SNDX', [u'2B', u'b', u's', u'I', u'h', u'2B'], 'minDist', 'maxDist', 'freqAdj',
                      'unusedSndd', (_flags, 'flags'), 'staticAtten',
                      'stopTime', 'startTime'),
            MelStruct(b'ANAM', [u'5h'], 'point0', 'point1', 'point2', 'point3',
                      'point4'),
            MelSInt16(b'GNAM', 'reverb'),
            MelSInt32(b'HNAM', 'priority'),
        ),
    )

#------------------------------------------------------------------------------
class MreSpel(MelRecord):
    """Actor Effect"""
    rec_sig = b'SPEL'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelStruct(b'SPIT', [u'3I', u'B', u'3s'], 'spellType', 'cost', 'level',
                  (SpellFlags, 'spell_flags'), 'unused1'),
        MelEffectsFo3(),
    )

#------------------------------------------------------------------------------
class MreStat(MelRecord):
    """Static."""
    rec_sig = b'STAT'

    class HeaderFlags(VWDFlag, MelRecord.HeaderFlags):
        has_tree_lod: bool = flag(6)
        addon_lod_object: bool = flag(7)    # FNV only?
        # cannot_save: 14 - runtime only
        # 17: use_hd_lod_texture
        #     Not in xEdit source, but in old WB comments (not specified which
        #     game).  In Sky it's STAT:use_hd_lod_texture
        use_hd_lod_texture: bool = flag(17)
        platform_specific_texture: bool = flag(19)  # ? in old WB comments
        has_currents: bool = flag(19) # matches skyrim, so probably the right 19
        show_in_world_map: bool = flag(28)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        fnv_only(MelSInt8(b'BRUS', 'passthroughSound')),
        fnv_only(MelSoundRandomLooping()),
    )

#------------------------------------------------------------------------------
class MreTact(MelRecord):
    """Talking Activator."""
    rec_sig = b'TACT'

    class HeaderFlags(MelRecord.HeaderFlags):
        radio_station: bool = flag(17)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelDestructible(),
        MelSound(),
        MelFid(b'VNAM','voiceType'),
        fnv_only(MelFid(b'INAM', 'radioTemplate')),
    )

#------------------------------------------------------------------------------
class MreTerm(MelRecord):
    """Terminal."""
    rec_sig = b'TERM'

    class _flags(Flags):
        leveled: bool
        unlocked: bool
        alternateColors: bool
        hideWellcomeTextWhenDisplayingImage: bool

    class _menuFlags(Flags):
        addNote: bool
        forceRedraw: bool

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelDestructible(),
        MelDescription(),
        MelSound(),
        MelFid(b'PNAM','passwordNote'),
        MelTruncatedStruct(b'DNAM', [u'3B', u's'], 'baseHackingDifficulty',
                           (_flags,'flags'), 'serverType', 'unused1',
                           old_versions={'3B'}),
        MelGroups('menuItems',
            MelString(b'ITXT','itemText'),
            MelString(b'RNAM','resultText'),
            MelUInt8Flags(b'ANAM', u'menuFlags', _menuFlags),
            MelFid(b'INAM','displayNote'),
            MelFid(b'TNAM','subMenu'),
            MelEmbeddedScript(),
            MelConditionsFo3(),
        ),
    )

#------------------------------------------------------------------------------
class MreTree(MelRecord):
    """Tree."""
    rec_sig = b'TREE'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelIcon(),
        MelSorted(MelArray('speedTree',
            MelUInt32(b'SNAM', 'seed'),
        ), sort_by_attrs='seed'),
        MelStruct(b'CNAM', [u'5f', u'i', u'2f'], 'curvature','minAngle','maxAngle',
                  'branchDim','leafDim','shadowRadius','rockSpeed',
                  'rustleSpeed'),
        MelStruct(b'BNAM', [u'2f'],'widthBill','heightBill'),
    )

#------------------------------------------------------------------------------
class MreTxst(MelRecord):
    """Texture Set."""
    rec_sig = b'TXST'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelString(b'TX00', 'base_image_transparency_texture'),
        MelString(b'TX01', 'normal_map_specular_texture'),
        MelString(b'TX02', 'environment_map_mask_texture'),
        MelString(b'TX03', 'glow_map_texture'),
        MelString(b'TX04', 'parallax_map_texture'),
        MelString(b'TX05', 'environment_map_texture'),
        MelDecalData(),
        MelTxstFlags(),
    )

#------------------------------------------------------------------------------
class MreVtyp(MelRecord):
    """Voice Type."""
    rec_sig = b'VTYP'

    class _flags(Flags):
        allowDefaultDialog: bool
        female: bool

    melSet = MelSet(
        MelEdid(),
        MelUInt8Flags(b'DNAM', u'flags', _flags),
    )

#------------------------------------------------------------------------------
class MreWatr(MelRecord):
    """Water."""
    rec_sig = b'WATR'
    _has_duplicate_attrs = True # DATA is an older version of DNAM + DATA

    class _flags(Flags):
        causesDmg: bool
        reflective: bool

    class MelWatrData(MelStruct):
        """Older subrecord consisting of a truncated DNAM with the damage short
        appended at the end. Read it in, but only dump out the damage - let
        DNAM handle the rest via duplicate attrs."""
        def load_mel(self, record, ins, sub_type, size_, *debug_strs):
            __unpacker=structs_cache[u'H'].unpack
            if size_ == 186:
                super(MreWatr.MelWatrData, self).load_mel(
                    record, ins, sub_type, size_, *debug_strs)
            elif size_ == 2:
                record.damage = ins.unpack(__unpacker, size_, *debug_strs)[0]
            else:
                raise ModSizeError(ins.inName, debug_strs, (186, 2), size_)

        def pack_subrecord_data(self, record,
                __packer=structs_cache[u'H'].pack):
            return __packer(record.damage)

    class MelWatrDnam(MelTruncatedStruct):
        # TODO(inf) Why do we do this?
        def _pre_process_unpacked(self, unpacked_val):
            if len(unpacked_val) == 55:
                unpacked_val = unpacked_val[:-1]
            return super()._pre_process_unpacked(unpacked_val)

    _els = [('windVelocity', 0.1), ('windDirection', 90), ('waveAmp', 0.5),
        ('waveFreq', 1), ('sunPower', 50), ('reflectAmt', 0.5),
        ('fresnelAmt', 0.025), 'unknown1', ('fogNear', 27852.8),
        ('fogFar', 163840), 'shallowRed', ('shallowGreen', 128),
        ('shallowBlue', 128), 'unused1', 'deepRed', 'deepGreen',
        ('deepBlue', 25), 'unused2', ('reflRed', 255),
        ('reflGreen', 255), ('reflBlue', 255), 'unused3', 'unknown2',
        ('rainForce', 0.1), ('rainVelocity', 0.6), ('rainFalloff', 0.9850),
        ('rainDampner', 2), ('rainSize', 0.01), ('dispForce', 0.4),
        ('dispVelocity', 0.6), ('dispFalloff', 0.9850), ('dispDampner', 10),
        ('dispSize', 0.05), ('noiseNormalsScale', 1.8),
        'noiseLayer1WindDirection',
        ('noiseLayer2WindDirection', -431602080.05),
        ('noiseLayer3WindDirection', -431602080.05), 'noiseLayer1WindVelocity',
        ('noiseLayer2WindVelocity', -431602080.05),
        ('noiseLayer3WindVelocity', -431602080.05),
        'noiseNormalsDepthFalloffStart', ('noiseNormalsDepthFalloffEnd', 0.10),
        ('fogAboveWaterAmount', 1), ('noiseNormalsUvScale', 500),
        ('fogUnderWaterAmount', 1), 'fogUnderWaterNear',
        ('fogUnderWaterFar', 1000), ('distortionAmount', 250),
        ('shininess', 100), ('reflectHdrMult', 1), ('lightRadius', 10000),
        ('lightBrightness', 1), ('noiseLayer1UvScale', 100),
        ('noiseLayer2UvScale', 100), ('noiseLayer3UvScale', 100)]
    _fmts = [u'10f', u'3B', u's', u'3B', u's', u'3B', u's', u'I',]

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelString(b'NNAM','texture'),
        MelUInt8(b'ANAM', 'opacity'),
        MelUInt8Flags(b'FNAM', u'flags', _flags),
        MelString(b'MNAM','material'),
        MelSound(),
        MelFid(b'XNAM','effect'),
        MelWatrData(b'DATA', _fmts + [u'32f', u'H'], *(_els + ['damage'])),
        MelWatrDnam(b'DNAM', _fmts + [u'35f'], *(
                _els + ['noiseLayer1Amp', 'noiseLayer2Amp', 'noiseLayer3Amp']),
                    old_versions={'10f3Bs3Bs3BsI32f'}),
        MelSimpleArray('relatedWaters', MelFid(b'GNAM')),
    )

#------------------------------------------------------------------------------
class MreWeap(MelRecord):
    """Weapon."""
    rec_sig = b'WEAP'

    class _flags(Flags):
        notNormalWeapon: bool

    class _dflags1(Flags):
        ignoresNormalWeaponResistance: bool
        isAutomatic: bool
        hasScope: bool
        cantDrop: bool
        hideBackpack: bool
        embeddedWeapon: bool
        dontUse1stPersonISAnimations: bool
        nonPlayable: bool

    class _dflags2(Flags):
        playerOnly: bool = flag(0)
        npcsUseAmmo: bool = flag(1)
        noJamAfterReload: bool = flag(2)
        overrideActionPoint: bool = flag(3)
        minorCrime: bool = flag(4)
        rangeFixed: bool = flag(5)
        notUseInNormalCombat: bool = flag(6)
        overrideDamageToWeaponMult: bool = flag(7)
        dontUse3rdPersonISAnimations: bool = flag(8)
        shortBurst: bool = flag(9)
        RumbleAlternate: bool = flag(10)
        longBurst: bool = flag(11)
        scopeHasNightVision: bool = flag(fnv_only(12))
        scopeFromMod: bool = flag(fnv_only(13))

    class _cflags(Flags):
        onDeath: bool

    # Attributes shared between FO3 and FNV for the DNAM subrecord
    _shared_dnam = ['animationType', 'animationMultiplier', 'reach',
                    (_dflags1, 'dnamFlags1'), ('gripAnimation', 255),
                    'ammoUse', 'reloadAnimation', 'minSpread', 'spread',
                    'weapDnam1', 'sightFov', 'weapDnam2', (FID, 'projectile'),
                    'baseVatsToHitChance', ('attackAnimation', 255),
                    'projectileCount', 'embeddedWeaponActorValue', 'minRange',
                    'maxRange', 'onHit', (_dflags2, 'dnamFlags2'),
                    'animationAttackMultiplier', 'fireRate',
                    'overrideActionPoint', 'rumbleLeftMotorStrength',
                    'rumbleRightMotorStrength', 'rumbleDuration',
                    'overrideDamageToWeaponMult', 'attackShotsPerSec',
                    'reloadTime', 'jamTime', 'aimArc', ('skill', 45),
                    'rumblePattern', 'rumbleWavelength', 'limbDmgMult',
                    ('resistType', -1), 'sightUsage',
                    'semiAutomaticFireDelayMin', 'semiAutomaticFireDelayMax']

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelScript(),
        MelEnchantment(),
        MelUInt16(b'EAMT', 'objectEffectPoints'),
        MelFid(b'NAM0','ammo'),
        MelDestructible(),
        MelFid(b'REPL','repairList'),
        MelEquipmentTypeFo3(),
        MelFid(b'BIPL','bipedModelList'),
        MelSoundPickupDrop(),
        MelModel(b'MOD2', 'shellCasingModel'),
        MelModel(b'MOD3', 'scopeModel', with_facegen_flags=False),
        MelFid(b'EFSD','scopeEffect'),
        MelModel(b'MOD4', 'worldModel'),
        fnv_only(MelGroup('modelWithMods',
            MelString(b'MWD1', 'mod1Path'),
            MelString(b'MWD2', 'mod2Path'),
            MelString(b'MWD3', 'mod1and2Path'),
            MelString(b'MWD4', 'mod3Path'),
            MelString(b'MWD5', 'mod1and3Path'),
            MelString(b'MWD6', 'mod2and3Path'),
            MelString(b'MWD7', 'mod1and2and3Path'),
        )),
        fnv_only(MelString(b'VANM', 'vatsAttackName')),
        MelString(b'NNAM','embeddedWeaponNode'),
        MelImpactDataset(b'INAM'),
        MelFid(b'WNAM','firstPersonModel'),
        fnv_only(MelGroup('firstPersonModelWithMods',
            MelFid(b'WNM1', 'mod1Path'),
            MelFid(b'WNM2', 'mod2Path'),
            MelFid(b'WNM3', 'mod1and2Path'),
            MelFid(b'WNM4', 'mod3Path'),
            MelFid(b'WNM5', 'mod1and3Path'),
            MelFid(b'WNM6', 'mod2and3Path'),
            MelFid(b'WNM7', 'mod1and2and3Path'),
        )),
        fnv_only(MelGroup('weaponMods',
            MelFid(b'WMI1', 'mod1'),
            MelFid(b'WMI2', 'mod2'),
            MelFid(b'WMI3', 'mod3'),
        )),
        if_fnv(
            fo3_version=MelSound(),
            fnv_version=MelSequential(
                MelFid(b'SNAM', 'sound_gun_shoot_3d'),
                MelFid(b'SNAM', 'sound_gun_shoot_dist'),
            ),
        ),
        MelFid(b'XNAM','soundGunShot2D'),
        MelFid(b'NAM7','soundGunShot3DLooping'),
        MelFid(b'TNAM','soundMeleeSwingGunNoAmmo'),
        MelFid(b'NAM6','soundBlock'),
        MelFid(b'UNAM','idleSound',),
        MelFid(b'NAM9','equipSound',),
        MelFid(b'NAM8','unequipSound',),
        fnv_only(MelFid(b'WMS1', 'sound_mod1_shoot_3d')),
        fnv_only(MelFid(b'WMS1', 'sound_mod1_shoot_dist')),
        fnv_only(MelFid(b'WMS2', 'sound_mod1_shoot_2d')),
        MelStruct(b'DATA', [u'2I', u'f', u'H', u'B'],'value','health','weight','damage','clipsize'),
        if_fnv(
            fo3_version=MelTruncatedStruct(
                b'DNAM', [u'I', u'2f', u'4B', u'5f', u'I', u'4B', u'2f', u'2I',
                          u'11f', u'i', u'I', u'2f', u'i', u'3f'],
                *_shared_dnam, old_versions={'I2f4B5fI4B2f2I11fiI2fi',
                                             'I2f4B5fI4B2f2I11fiI2f'}),
            fnv_version=MelTruncatedStruct(
                b'DNAM', [u'I', u'2f', u'4B', u'5f', u'I', u'4B', u'2f', u'2I',
                          u'11f', u'i', u'I', u'2f', u'i', u'4f', u'3I', u'3f',
                          u'2I', u's', u'B', u'2s', u'6f', u'I'],
                *(_shared_dnam + [
                    'weapDnam3', 'effectMod1', 'effectMod2', 'effectMod3',
                    'valueAMod1', 'valueAMod2', 'valueAMod3',
                    'powerAttackAnimation', 'strengthReq', 'weapDnam4',
                    'reloadAnimationMod', 'weapDnam5', 'regenRate',
                    'killImpulse', 'valueBMod1', 'valueBMod2', 'valueBMod3',
                    'impulseDist', 'skillReq']),
                old_versions={
                    'I2f4B5fI4B2f2I11fiI2fi4f3I3f2IsB2s6f',
                    'I2f4B5fI4B2f2I11fiI2fi4f3I3f2IsB2s5f',
                    'I2f4B5fI4B2f2I11fiI2fi4f3I3f2IsB2sf',
                    'I2f4B5fI4B2f2I11fiI2fi4f3I3f2I',
                    'I2f4B5fI4B2f2I11fiI2fi4f3I3f', 'I2f4B5fI4B2f2I11fiI2fi3f',
                    'I2f4B5fI4B2f2I11fiI2fi', 'I2f4B5fI4B2f2I11fiI2f',
                }),
        ),
        MelOptStruct(b'CRDT', ['H', '2s', 'f', 'B', '3s', 'I'],
                     'criticalDamage', 'weapCrdt1', 'criticalMultiplier',
                     (_cflags, 'criticalFlags'), 'weapCrdt2',
                     (FID, 'criticalEffect')),
        fnv_only(MelTruncatedStruct(
            b'VATS', ['I', '3f', '2B', '2s'], (FID, 'vatsEffect'),
            'vatsSkill', 'vatsDamMult', 'vatsAp', 'vatsSilent',
            'vats_mod_required', 'weapVats1', old_versions={'I3f'},
            is_optional=True)),
        MelBase(b'VNAM','soundLevel'),
    ).with_distributor(fnv_only({
        b'SNAM': [
            (b'SNAM', 'sound_gun_shoot_3d'),
            (b'SNAM', 'sound_gun_shoot_dist'),
        ],
        b'WMS1': [
            (b'WMS1', 'sound_mod1_shoot_3d'),
            (b'WMS1', 'sound_mod1_shoot_dist'),
        ],
    }))

#------------------------------------------------------------------------------
class MreWrld(AMreWrld):
    """Worldspace."""
    ref_types = MreCell.ref_types
    exterior_temp_extra = [b'LAND', b'NAVM']
    wrld_children_extra = [b'CELL']

    class _flags(Flags):
        smallWorld: bool
        noFastTravel: bool
        oblivionWorldspace: bool
        noLODWater: bool = flag(4)
        noLODNoise: bool
        noAllowNPCFallDamage: bool

    class pnamFlags(TrimmedFlags):
        useLandData: bool = flag(0)
        useLODData: bool = flag(1)
        useMapData: bool = flag(2)
        useWaterData: bool = flag(3)
        useClimateData: bool = flag(4)
        useImageSpaceData: bool = flag(5)
        needsWaterAdjustment: bool = flag(7)

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelFid(b'XEZN','encounterZone'),
        MelFid(b'WNAM','parent'),
        MelOptStruct(b'PNAM', ['B', 'B'], (pnamFlags, 'parentFlags'),
                     'unknownff'),
        MelFid(b'CNAM','climate'),
        MelFid(b'NAM2','water'),
        MelFid(b'NAM3', 'lod_water_type'),
        MelFloat(b'NAM4', 'waterHeight'),
        MelStruct(b'DNAM', [u'f', u'f'],'defaultLandHeight','defaultWaterHeight'),
        MelIcon(u'mapPath'),
        MelStruct(b'MNAM', [u'2i', u'4h'], u'dimX', u'dimY', u'NWCellX', u'NWCellY',
                  u'SECellX', u'SECellY'),
        MelStruct(b'ONAM', [u'f', u'f', u'f'],'worldMapScale','cellXOffset','cellYOffset'),
        MelFid(b'INAM','imageSpace'),
        MelUInt8Flags(b'DATA', u'flags', _flags),
        MelWorldBounds(),
        MelFid(b'ZNAM','music'),
        MelString(b'NNAM','canopyShadow'),
        MelString(b'XNAM','waterNoiseTexture'),
        MelSorted(MelGroups('swappedImpacts',
            MelStruct(b'IMPS', [u'3I'], 'materialType', (FID, 'old'),
                      (FID, 'new')),
        ), sort_by_attrs=('materialType', 'old', 'new')),
        MelBase(b'IMPF','footstepMaterials'), #--todo rewrite specific class.
        MelNull(b'OFST'), # Not even CK/xEdit can recalculate these right now
    )

#------------------------------------------------------------------------------
class MelWthrColorsFnv(MelArray):
    """Used twice in WTHR for PNAM and NAM0. Needs to handle older versions
    as well. Can't simply use MelArray because MelTruncatedStruct does not
    have a static_size."""
    # TODO(inf) Rework MelArray - instead of static_size, have a
    #  get_entry_size that receives the total size_ of load_mel.
    #  MelTruncatedStruct could override that and make a guess based on its
    #  sizes. If that guess doesn't work, a small override class can be
    #  created by hand
    _new_sizes = {b'PNAM': 96, b'NAM0': 240}
    _old_sizes = {b'PNAM': 64, b'NAM0': 160}

    def __init__(self, wthr_sub_sig, wthr_attr):
        struct_definition = [
            [u'3B', u's', u'3B', u's', u'3B', u's', u'3B', u's', u'3B', u's',
             u'3B', u's'], u'riseRed', u'riseGreen', u'riseBlue',
            u'unused1', u'dayRed', u'dayGreen', u'dayBlue',
            u'unused2', u'setRed', u'setGreen', u'setBlue',
            u'unused3', u'nightRed', u'nightGreen', u'nightBlue',
            u'unused4', u'noonRed', u'noonGreen', u'noonBlue',
            u'unused5', u'midnightRed', u'midnightGreen',
            u'midnightBlue', u'unused6'
        ]
        super(MelWthrColorsFnv, self).__init__(wthr_attr,
            MelStruct(wthr_sub_sig, *struct_definition),
        )
        self._element_old = MelTruncatedStruct(
            wthr_sub_sig, *struct_definition,
            old_versions={u'3Bs3Bs3Bs3Bs'})

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        if size_ == self._new_sizes[sub_type]:
            super(MelWthrColorsFnv, self).load_mel(record, ins, sub_type,
                                                   size_, *debug_strs)
        elif size_ == self._old_sizes[sub_type]:
            # Copied and adjusted from MelArray. Yuck. See comment below
            # docstring for some ideas for getting rid of this
            append_entry = getattr(record, self.attr).append
            entry_slots = self._element_old.attrs
            entry_size = struct_calcsize(u'3Bs3Bs3Bs3Bs')
            load_entry = self._element_old.load_mel
            for x in range(size_ // entry_size):
                arr_entry = MelObject()
                append_entry(arr_entry)
                arr_entry.__slots__ = entry_slots
                load_entry(arr_entry, ins, sub_type, entry_size, *debug_strs)
        else:
            _expected_sizes = (self._new_sizes[sub_type],
                               self._old_sizes[sub_type])
            raise ModSizeError(ins.inName, debug_strs, _expected_sizes, size_)

class MreWthr(AMreWthr):
    """Weather."""
    rec_sig = b'WTHR'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'\x00IAD', 'sunriseImageSpaceModifier'),
        MelFid(b'\x01IAD', 'dayImageSpaceModifier'),
        MelFid(b'\x02IAD', 'sunsetImageSpaceModifier'),
        MelFid(b'\x03IAD', 'nightImageSpaceModifier'),
        fnv_only(MelFid(b'\x04IAD', 'unknown1ImageSpaceModifier')),
        fnv_only(MelFid(b'\x05IAD', 'unknown2ImageSpaceModifier')),
        MelString(b'DNAM','upperLayer'),
        MelString(b'CNAM','lowerLayer'),
        MelString(b'ANAM','layer2'),
        MelString(b'BNAM','layer3'),
        MelModel(),
        MelBase(b'LNAM','unknown1'),
        MelStruct(b'ONAM', [u'4B'],'cloudSpeed0','cloudSpeed1','cloudSpeed3','cloudSpeed4'),
        if_fnv(fo3_version=MelArray('cloudColors',
            MelWthrColors(b'PNAM'),
        ), fnv_version=MelWthrColorsFnv(b'PNAM', 'cloudColors')),
        if_fnv(fo3_version=MelArray('daytimeColors',
            MelWthrColors(b'NAM0'),
        ), fnv_version=MelWthrColorsFnv(b'NAM0', 'daytimeColors')),
        MelStruct(b'FNAM', [u'6f'],'fogDayNear','fogDayFar','fogNightNear','fogNightFar','fogDayPower','fogNightPower'),
        MelBase(b'INAM', 'unused1'),
        MelStruct(b'DATA', [u'15B'],
            'windSpeed','lowerCloudSpeed','upperCloudSpeed','transDelta',
            'sunGlare','sunDamage','rainFadeIn','rainFadeOut','boltFadeIn',
            'boltFadeOut','boltFrequency','weatherType','boltRed','boltBlue','boltGreen'),
        MelGroups('sounds',
            MelStruct(b'SNAM', [u'2I'], (FID, 'sound'), 'type'),
        ),
    )
