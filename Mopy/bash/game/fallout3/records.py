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
"""This module contains the fallout3 record classes. You must import from it
__once__ only in game.fallout3.Fallout3GameInfo#init. No other game.records
file must be imported till then."""
from collections import OrderedDict

from ... import brec, bush
from ...bolt import Flags, structs_cache
from ...brec import MelRecord, MelGroups, MelStruct, FID, MelGroup, \
    MelString, MelSet, MelFid, MelOptStruct, MelFids, MreHeaderBase, \
    MelBase, MelFidList, MreGmstBase, MelBodyParts, MelMODS, MelFactions, \
    MelReferences, MelColorInterpolator, MelValueInterpolator, MelAnimations, \
    MelUnion, AttrValDecider, MelRegnEntrySubrecord, SizeDecider, MelFloat, \
    MelSInt8, MelSInt16, MelSInt32, MelUInt8, MelUInt16, MelUInt32, \
    MelPartialCounter, MelRaceParts, MelRelations, MelActorSounds, \
    MelRaceVoices, MelBounds, null1, null2, MelScriptVars, MelSorted, \
    MelSequential, MelTruncatedStruct, PartialLoadDecider, MelReadOnly, \
    MelSkipInterior, MelIcons, MelIcons2, MelIcon, MelIco2, MelEdid, MelFull, \
    MelArray, MelWthrColors, MreLeveledListBase, MreActorBase, MreWithItems, \
    MelCtdaFo3, MelRef3D, MelXlod, MelNull, MelWorldBounds, MelEnableParent, \
    MelRefScale, MelMapMarker, MelActionFlags, MelEnchantment, MelScript, \
    MelDecalData, MelDescription, MelLists, MelPickupSound, MelDropSound, \
    MelActivateParents, BipedFlags, MelSpells, MelUInt8Flags, MelUInt16Flags, \
    MelUInt32Flags, MelOwnership, MelDebrData, MelRaceData, MelRegions, \
    MelWeatherTypes, MelFactionRanks, perk_effect_key, MelLscrLocations, \
    MelReflectedRefractedBy
from ...exception import ModSizeError
# Set MelModel in brec but only if unset
if brec.MelModel is None:

    class _MelModel(MelGroup):
        """Represents a model record."""
        typeSets = ((b'MODL', b'MODB', b'MODT', b'MODS', b'MODD'),
                    (b'MOD2', b'MO2B', b'MO2T', b'MO2S'),
                    (b'MOD3', b'MO3B', b'MO3T', b'MO3S', b'MOSD'),
                    (b'MOD4', b'MO4B', b'MO4T', b'MO4S'))

        _facegen_model_flags = Flags(0, Flags.getNames(
            u'head',
            u'torso',
            u'rightHand',
            u'leftHand',
        ))

        def __init__(self, attr=u'model', index=0, with_facegen_flags=True):
            """Initialize. Index is 0,2,3,4 for corresponding type id."""
            types = self.__class__.typeSets[index - 1 if index > 0 else 0]
            model_elements = [
                MelString(types[0], u'modPath'),
                MelBase(types[1], u'modb_p'),
                # Texture File Hashes
                MelBase(types[2], u'modt_p'),
                MelMODS(types[3], u'alternateTextures'),
            ]
            # No MODD/MOSD equivalent for MOD2 and MOD4
            if len(types) == 5 and with_facegen_flags:
                model_elements += [
                    MelUInt8Flags(types[4], u'facegen_model_flags',
                                  _MelModel._facegen_model_flags)]
            super(_MelModel, self).__init__(attr, *model_elements)

    brec.MelModel = _MelModel
from ...brec import MelModel

#------------------------------------------------------------------------------
_is_fnv = bush.game.fsName == u'FalloutNV'
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

#------------------------------------------------------------------------------
# Record Elements    ----------------------------------------------------------
#------------------------------------------------------------------------------
class MreActor(MreActorBase):
    """Creatures and NPCs."""
    TemplateFlags = Flags(0, Flags.getNames(
        'useTraits',
        'useStats',
        'useFactions',
        'useActorEffectList',
        'useAIData',
        'useAIPackages',
        'useModelAnimation',
        'useBaseData',
        'useInventory',
        'useScript',
    ))
    __slots__ = []

#------------------------------------------------------------------------------
class MelBipedData(MelStruct):
    """Handles the common BMDT (Biped Data) subrecord."""
    _biped_flags = BipedFlags()
    _general_flags = Flags(0, Flags.getNames(
        fnv_only((2, u'hasBackpack')),
        fnv_only((3, u'medium_armor')),
        (5, u'powerArmor'),
        (6, u'notPlayable'),
        (7, u'heavyArmor'),
    ), unknown_is_unused=True)

    def __init__(self):
        super(MelBipedData, self).__init__(b'BMDT', [u'I', u'B', u'3s'],
            (self._biped_flags, u'biped_flags'),
            (self._general_flags, u'generalFlags'), u'biped_unused')

#------------------------------------------------------------------------------
class MelConditions(MelGroups):
    """A list of conditions."""
    def __init__(self):
        # Note that reference can be a fid - handled in MelCtdaFo3.mapFids
        super(MelConditions, self).__init__(u'conditions',
            MelCtdaFo3(suffix_fmt=[u'2I'],
                       suffix_elements=[u'runOn', u'reference'],
                       old_suffix_fmts={u'I', u''}))

#------------------------------------------------------------------------------
class MelDestructible(MelGroup):
    """Represents a set of destruct record."""

    MelDestVatsFlags = Flags(0, Flags.getNames(u'vatsTargetable'),
        unknown_is_unused=True)
    MelDestStageFlags = Flags(0, Flags.getNames(
        u'capDamage',
        u'disable',
        u'destroy'
    ))

    def __init__(self, attr=u'destructible'):
        super(MelDestructible, self).__init__(attr,
            MelStruct(b'DEST', [u'i', u'2B', u'2s'], u'health', u'count',
                (MelDestructible.MelDestVatsFlags, u'flagsDest'), u'unused'),
            MelGroups(u'stages',
                MelStruct(b'DSTD', [u'4B', u'i', u'2I', u'i'], u'health', u'index',
                          u'damageStage',
                          (MelDestructible.MelDestStageFlags, u'flagsDest'),
                          u'selfDamagePerSecond', (FID, u'explosion'),
                          (FID, u'debris'), u'debrisCount'),
                MelString(b'DMDL', u'model'),
                MelBase(b'DMDT', u'dmdt'),
                MelBase(b'DSTF', u'footer'),
            ),
        )

#------------------------------------------------------------------------------
class MelEffects(MelGroups):
    """Represents ingredient/potion/enchantment/spell effects."""
    def __init__(self):
        super(MelEffects, self).__init__(u'effects',
            MelFid(b'EFID', u'baseEffect'),
            MelStruct(b'EFIT', [u'4I', u'i'], u'magnitude', u'area', u'duration',
                u'recipient', u'actorValue'),
            MelConditions(),
        )

#------------------------------------------------------------------------------
class MelEmbeddedScript(MelSequential):
    """Handles an embedded script, a SCHR/SCDA/SCTX/SLSD/SCVR/SCRO/SCRV
    subrecord combo."""
    _script_header_flags = Flags(0, Flags.getNames(u'enabled'))

    def __init__(self):
        super(MelEmbeddedScript, self).__init__(
            MelOptStruct(
                b'SCHR', [u'4s', u'3I', u'2H'], u'unused1', u'num_refs',
                u'compiled_size', u'last_index', u'script_type',
                (self._script_header_flags, u'schr_flags')),
            MelBase(b'SCDA', u'compiled_script'),
            MelString(b'SCTX', u'script_source'),
            MelScriptVars(),
            MelReferences(),
        )

#------------------------------------------------------------------------------
class MelEquipmentType(MelSInt32):
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
        super(MelEquipmentType, self).__init__(b'ETYP', u'equipment_type', -1)

#------------------------------------------------------------------------------
class MelItems(MelSorted):
    """Wraps MelGroups for the common task of defining a list of items."""
    def __init__(self):
        super(MelItems, self).__init__(MelGroups(u'items',
            MelStruct(b'CNTO', [u'I', u'i'], (FID, u'item'), (u'count', 1)),
            MelOptStruct(b'COED', [u'2I', u'f'], (FID, u'owner'), (FID, u'glob'),
                         (u'condition', 1.0)),
        ), sort_by_attrs=('item', 'count', 'condition', 'owner', 'glob'))

#------------------------------------------------------------------------------
class MreLeveledList(MreLeveledListBase):
    """Leveled item/creature/spell list.."""
    top_copy_attrs = (u'chanceNone', u'glob')
    entry_copy_attrs = (u'listId', u'level', u'count', u'owner', u'condition')

    class MelLevListLvld(MelUInt8):
        """Subclass to support alternate format."""
        def load_mel(self, record, ins, sub_type, size_, *debug_strs):
            super(MreLeveledList.MelLevListLvld, self).load_mel(record, ins,
                                                                sub_type,
                                                                size_, *debug_strs)
            if record.chanceNone > 127:
                record.flags.calcFromAllLevels = True
                record.chanceNone &= 127

    ##: Old format might be h2sI instead, which would retire this whole class
    class MelLevListLvlo(MelTruncatedStruct):
        """Older format skips unused1, which is in the middle of the record."""
        def _pre_process_unpacked(self, unpacked_val):
            if len(unpacked_val) == 2:
                # Pad it in the middle, then let our parent deal with the rest
                unpacked_val = (unpacked_val[0], null2, unpacked_val[1])
            return super(MreLeveledList.MelLevListLvlo,
                self)._pre_process_unpacked(unpacked_val)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelLevListLvld(b'LVLD', u'chanceNone'),
        MelUInt8Flags(b'LVLF', u'flags', MreLeveledListBase._flags),
        MelFid(b'LVLG', u'glob'),
        MelSorted(MelGroups(u'entries',
            MelLevListLvlo(b'LVLO', [u'h', u'2s', u'I', u'h', u'2s'], u'level',
                           u'unused1', (FID, u'listId'), (u'count', 1),
                           u'unused2', old_versions={u'iI'}),
            MelOptStruct(b'COED', [u'2I', u'f'], (FID, u'owner'), (FID, u'glob'),
                         (u'condition', 1.0)),
        ), sort_by_attrs=('level', 'listId', 'count', 'condition', 'owner',
                          'glob')),
        MelModel(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MelRaceHeadPart(MelGroup):
    """Implements special handling for ears, which can only contain an icon
    or a model, not both. Has to be here, since it's used by lambdas inside
    the RACE definition so it can't be a subclass."""
    def __init__(self, part_indx):
        self._modl_loader = MelModel()
        self._icon_loader = MelIcons(mico_attr=u'')
        self._mico_loader = MelIcons(icon_attr=u'')
        super(MelRaceHeadPart, self).__init__(u'head_part',
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
            has_icon = hasattr(target_head_part, u'iconPath')
            has_mico = hasattr(target_head_part, u'smallIconPath')
            if not has_icon and not has_mico:
                self._modl_loader.dumpData(target_head_part, out)
            else:
                if has_icon: self._icon_loader.dumpData(target_head_part, out)
                if has_mico: self._mico_loader.dumpData(target_head_part, out)
            return
        # Otherwise, delegate the dumpData call to MelGroup
        super(MelRaceHeadPart, self).dumpData(record, out)

#------------------------------------------------------------------------------
class MelLinkedDecals(MelSorted):
    """Linked Decals for a reference record (REFR, ACHR, etc.)."""
    def __init__(self):
        super(MelLinkedDecals, self).__init__(MelGroups(u'linkedDecals',
            MelStruct(b'XDCR', [u'2I'], (FID, u'reference'), u'unknown'),
        ), sort_by_attrs=u'reference')

#------------------------------------------------------------------------------
# Fallout3 Records ------------------------------------------------------------
#------------------------------------------------------------------------------
class MreTes4(MreHeaderBase):
    """TES4 Record.  File header."""
    rec_sig = b'TES4'

    melSet = MelSet(
        MelStruct(b'HEDR', [u'f', u'2I'], ('version', 0.94), 'numRecords',
                  ('nextObject', 0x800)),
        MelNull(b'OFST'), # Not even CK/xEdit can recalculate these right now
        MelBase(b'DELE','dele_p',),  #--Obsolete?
        MreHeaderBase.MelAuthor(),
        MreHeaderBase.MelDescription(),
        MreHeaderBase.MelMasterNames(),
        MelFidList(b'ONAM','overrides'),
        MelBase(b'SCRN', 'screenshot'),
    )
    __slots__ = melSet.getSlotsUsed()

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
        fnv_only(MelString(b'XATO', 'activationPrompt')),
        MelEnableParent(),
        MelFid(b'XEMI', u'emittance'),
        MelFid(b'XMBR', u'multiboundReference'),
        MelBase(b'XIBS','ignoredBySandbox'),
        MelRefScale(),
        MelRef3D(),
    )
    __slots__ = melSet.getSlotsUsed()

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
        fnv_only(MelString(b'XATO', 'activationPrompt')),
        MelEnableParent(),
        MelFid(b'XEMI', u'emittance'),
        MelFid(b'XMBR', u'multiboundReference'),
        MelBase(b'XIBS','ignoredBySandbox'),
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
        MelBounds(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelDestructible(),
        MelFid(b'SNAM', u'soundLooping'),
        MelFid(b'VNAM', u'soundActivation'),
        fnv_only(MelFid(b'INAM', 'radioTemplate')),
        MelFid(b'RNAM', u'radioStation'),
        MelFid(b'WNAM', u'waterType'),
        fnv_only(MelString(b'XATO', 'activationPrompt')),
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
        MelSInt32(b'DATA', 'nodeIndex'),
        MelFid(b'SNAM', u'ambientSound'),
        MelStruct(b'DNAM', [u'H', u'2s'],'mastPartSysCap','unknown',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAlch(MelRecord):
    """Ingestible."""
    rec_sig = b'ALCH'

    _flags = Flags(0, Flags.getNames('autoCalc','isFood','medicine',))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelScript(),
        MelDestructible(),
        MelPickupSound(),
        MelDropSound(),
        MelEquipmentType(),
        MelFloat(b'DATA', 'weight'),
        MelStruct(b'ENIT', [u'i', u'B', u'3s', u'I', u'f', u'I'], u'value', (_flags, u'flags'),
                  u'unused1', (FID, u'withdrawalEffect'),
                  u'addictionChance', (FID, u'soundConsume')),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAmmo(MelRecord):
    """Ammunition."""
    rec_sig = b'AMMO'

    _flags = Flags(0, Flags.getNames('notNormalWeapon','nonPlayable'))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        fnv_only(MelScript()),
        MelDestructible(),
        MelPickupSound(),
        MelDropSound(),
        MelStruct(b'DATA', [u'f', u'B', u'3s', u'i', u'B'],'speed',(_flags, u'flags'),'ammoData1',
                  'value','clipRounds'),
        fnv_only(MelTruncatedStruct(
            b'DAT2', [u'2I', u'f', u'I', u'f'], 'projPerShot',
            (FID, u'projectile'), 'weight', (FID, 'consumedAmmo'),
            'consumedPercentage', old_versions={'2If'})),
        MelString(b'ONAM','shortName'),
        fnv_only(MelString(b'QNAM', 'abbrev')),
        fnv_only(MelFids(b'RCIL', 'effects')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAnio(MelRecord):
    """Animation Object."""

    rec_sig = b'ANIO'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelFid(b'DATA','animationId'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArma(MelRecord):
    """Armor Addon."""
    rec_sig = b'ARMA'

    _dnamFlags = Flags(0, Flags.getNames(u'modulatesVoice'))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelBipedData(),
        MelModel(u'maleBody'),
        MelModel(u'maleWorld', 2),
        MelIcons(u'maleIconPath', u'maleSmallIconPath'),
        MelModel(u'femaleBody', 3),
        MelModel(u'femaleWorld', 4),
        MelIcons2(),
        MelEquipmentType(),
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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArmo(MelRecord):
    """Armor."""
    rec_sig = b'ARMO'

    _dnamFlags = Flags(0, Flags.getNames(u'modulatesVoice'))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelScript(),
        MelEnchantment(),
        MelBipedData(),
        MelModel(u'maleBody'),
        MelModel(u'maleWorld', 2),
        MelIcons(u'maleIconPath', u'maleSmallIconPath'),
        MelModel(u'femaleBody', 3),
        MelModel(u'femaleWorld', 4),
        MelIcons2(),
        MelString(b'BMCT','ragdollTemplatePath'),
        MelDestructible(),
        MelFid(b'REPL','repairList'),
        MelFid(b'BIPL','bipedModelList'),
        MelEquipmentType(),
        MelPickupSound(),
        MelDropSound(),
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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAspc(MelRecord):
    """Acoustic Space."""
    rec_sig = b'ASPC'

    isKeyedByEid = True # NULL fids are acceptable

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        if_fnv(
            fo3_version=MelFid(b'SNAM', 'soundLooping'),
            fnv_version=MelFids(b'SNAM', 'soundLooping'),
        ),
        fnv_only(MelUInt32(b'WNAM', 'wallaTrigerCount')),
        MelFid(b'RDAT','useSoundFromRegion'),
        MelUInt32(b'ANAM', 'environmentType'),
        fnv_only(MelUInt32(b'INAM', 'isInterior')),
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
        MelIcons(),
        MelString(b'ANAM','shortName'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreBook(MelRecord):
    """BOOK record."""
    rec_sig = b'BOOK'

    _flags = Flags(0,Flags.getNames('isScroll','isFixed'))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelScript(),
        MelDescription(u'book_text'),
        MelDestructible(),
        MelPickupSound(),
        MelDropSound(),
        MelStruct(b'DATA', [u'B', u'b', u'I', u'f'],(_flags, u'flags'),('teaches',-1),'value','weight'),
    )
    __slots__ = melSet.getSlotsUsed() + ['modb']

#------------------------------------------------------------------------------
class MelBptdParts(MelGroups):
    """Handles the 'body parts' subrecords in BPTD. BPNN can either start a new
    body part or belong to an existing one, depending on whether or not we hit
    a BPTN before it."""
    _bpnd_flags = Flags(0, Flags.getNames(u'severable', u'ikData',
        u'ikBipedData', u'explodable', u'ikIsHead', u'ikHeadtracking',
        u'toHitChanceAbsolute'))

    def __init__(self):
        super(MelBptdParts, self).__init__(u'bodyParts',
            MelString(b'BPTN', u'partName'),
            MelString(b'BPNN', u'nodeName'),
            MelString(b'BPNT', u'vatsTarget'),
            MelString(b'BPNI', u'ikDataStartNode'),
            MelStruct(b'BPND', [u'f', u'3B', u'b', u'2B', u'H', u'2I', u'2f', u'i', u'2I', u'7f', u'2I', u'2B', u'2s', u'f'], u'damageMult',
                (self._bpnd_flags, u'flags'), u'partType',
                u'healthPercent', u'actorValue', u'toHitChance',
                u'explodableChancePercent', u'explodableDebrisCount',
                (FID, u'explodableDebris'), (FID, u'explodableExplosion'),
                u'trackingMaxAngle', u'explodableDebrisScale',
                u'severableDebrisCount', (FID, u'severableDebris'),
                (FID, u'severableExplosion'), u'severableDebrisScale',
                u'goreEffectPosTransX', u'goreEffectPosTransY',
                u'goreEffectPosTransZ', u'goreEffectPosRotX',
                u'goreEffectPosRotY', u'goreEffectPosRotZ',
                (FID, u'severableImpactDataSet'),
                (FID, u'explodableImpactDataSet'), u'severableDecalCount',
                u'explodableDecalCount', u'unused',
                u'limbReplacementScale'),
            MelString(b'NAM1', u'limbReplacementModel'),
            MelString(b'NAM4', u'goreEffectsTargetBone'),
            MelBase(b'NAM5', u'texture_hashes'),
        )

    def setDefault(self, record):
        super(MelBptdParts, self).setDefault(record)
        record._had_bptn = False

    def getSlotsUsed(self):
        return (u'_had_bptn',) + super(MelBptdParts, self).getSlotsUsed()

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        if sub_type == b'BPTN':
            # We hit a BPTN, this is a new body part
            record._had_bptn = True
        elif sub_type == b'BPNN':
            if record._had_bptn:
                # We hit a BPNN, but had a BPTN before it. This BPNN is
                # part of the current body part
                record._had_bptn = False
            else:
                # We hit a BPNN, but there was no BPTN before it. This BPNN
                # starts a new unnamed body part
                self._new_object(record)
        # Finally, delegate to the correct subrecord loader
        super(MelBptdParts, self).load_mel(record, ins, sub_type, size_,
                                           *debug_strs)

    def dumpData(self, record, out):
        for bp_target in getattr(record, self.attr):
            for bp_element in self.elements:
                if bp_element.mel_sig == b'BPTN' and getattr(
                        bp_target, bp_element.attr) is None:
                    continue # unnamed body part, skip
                bp_element.dumpData(bp_target, out)

class MreBptd(MelRecord):
    """Body Part Data."""
    rec_sig = b'BPTD'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelBptdParts(),
        MelFid(b'RAGA', u'ragdoll'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCams(MelRecord):
    """Camera Shot."""
    rec_sig = b'CAMS'

    CamsFlagsFlags = Flags(0, Flags.getNames(
            (0, 'positionFollowsLocation'),
            (1, 'rotationFollowsTarget'),
            (2, 'dontFollowBone'),
            (3, 'firstPersonCamera'),
            (4, 'noTracer'),
            (5, 'startAtTimeZero'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelStruct(b'DATA', [u'4I', u'6f'],'action','location','target',
                  (CamsFlagsFlags, u'flags'),'timeMultPlayer',
                  'timeMultTarget','timeMultGlobal','maxTime','minTime',
                  'targetPctBetweenActors',),
        MelFid(b'MNAM','imageSpaceModifier',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCell(MelRecord):
    """Cell."""
    rec_sig = b'CELL'

    cellFlags = Flags(0, Flags.getNames(
        (0, 'isInterior'),
        (1, 'hasWater'),
        (2, 'invertFastTravel'),
        (3, 'noLODWater'),
        (5, 'publicPlace'),
        (6, 'handChanged'),
        (7, 'behaveLikeExterior')
    ))

    inheritFlags = Flags(0, Flags.getNames(
        'ambientColor',
        'directionalColor',
        'fogColor',
        'fogNear',
        'fogFar',
        'directionalRotation',
        'directionalFade',
        'clipDistance',
        'fogPower'
    ))

    _land_flags = Flags(0, Flags.getNames(u'quad1', u'quad2', u'quad3',
        u'quad4'), unknown_is_unused=True)

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt8Flags(b'DATA', u'flags', cellFlags),
        # None defaults here are on purpose - XCLC does not necessarily exist,
        # but 0 is a valid value for both coordinates (duh)
        MelSkipInterior(MelTruncatedStruct(b'XCLC', [u'2i', u'I'], (u'posX', None),
            (u'posY', None), (_land_flags, u'land_flags'), is_optional=True,
            old_versions={u'2i'})),
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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClas(MelRecord):
    """Class."""
    rec_sig = b'CLAS'

    _flags = Flags(0, Flags.getNames(
        u'class_playable',
        u'class_guard',
    ), unknown_is_unused=True)
    aiService = Flags(0, Flags.getNames(
        (0,'weapons'),
        (1,'armor'),
        (2,'clothing'),
        (3,'books'),
        (4,'foods'),
        (5,'chems'),
        (6,'stimpacks'),
        (7,'lights'),
        (10,'miscItems'),
        (13,'potions'),
        (14,'training'),
        (16,'recharge'),
        (17,'repair')))

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClmt(MelRecord):
    """Climate."""
    rec_sig = b'CLMT'

    melSet = MelSet(
        MelEdid(),
        MelWeatherTypes(),
        MelString(b'FNAM','sunPath'),
        MelString(b'GNAM','glarePath'),
        MelModel(),
        MelStruct(b'TNAM', [u'6B'],'riseBegin','riseEnd','setBegin','setEnd',
                  'volatility','phaseLength',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCobj(MelRecord):
    """Constructible Object (Recipes)."""
    rec_sig = b'COBJ'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelScript(),
        MelPickupSound(),
        MelDropSound(),
        MelStruct(b'DATA', [u'i', u'f'],'value','weight'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCont(MreWithItems):
    """Container."""
    rec_sig = b'CONT'

    _flags = Flags(0,Flags.getNames(None,'respawns'))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelItems(),
        MelDestructible(),
        MelStruct(b'DATA', [u'B', u'f'],(_flags, u'flags'),'weight'),
        MelFid(b'SNAM','soundOpen'),
        MelFid(b'QNAM','soundClose'),
        fnv_only(MelFid(b'RNAM', 'soundRandomLooping')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCpth(MelRecord):
    """Camera Path."""
    rec_sig = b'CPTH'

    melSet = MelSet(
        MelEdid(),
        MelConditions(),
        MelFidList(b'ANAM','relatedCameraPaths',),
        MelUInt8(b'DATA', 'cameraZoom'),
        MelFids(b'SNAM','cameraShots',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCrea(MreActor):
    """Creature."""
    rec_sig = b'CREA'

    _flags = Flags(0, Flags.getNames(
        ( 0,'biped'),
        ( 1,'essential'),
        ( 2,'weaponAndShield'),
        ( 3,'respawn'),
        ( 4,'swims'),
        ( 5,'flies'),
        ( 6,'walks'),
        ( 7,'pcLevelOffset'),
        ( 9,'noLowLevel'),
        (11,'noBloodSpray'),
        (12,'noBloodDecal'),
        (15,'noHead'),
        (16,'noRightArm'),
        (17,'noLeftArm'),
        (18,'noCombatInWater'),
        (19,'noShadow'),
        (20,'noVATSMelee'),
        (21,'allowPCDialogue'),
        (22,'cantOpenDoors'),
        (23,'immobile'),
        (24,'tiltFrontBack'),
        (25,'tiltLeftRight'),
        (26,'noKnockDown'),
        (27,'notPushable'),
        (28,'allowPickpocket'),
        (29,'isGhost'),
        (30,'noRotatingHeadTrack'),
        (31,'invulnerable')))
    aiService = Flags(0, Flags.getNames(
        (0,'weapons'),
        (1,'armor'),
        (2,'clothing'),
        (3,'books'),
        (4,'foods'),
        (5,'chems'),
        (6,'stimpacks'),
        (7,'lights'),
        (10,'miscItems'),
        (13,'potions'),
        (14,'training'),
        (16,'recharge'),
        (17,'repair')))
    aggroflags = Flags(0, Flags.getNames('aggroRadiusBehavior',))

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
            (MreActor.TemplateFlags, 'templateFlags')),
        MelFactions(),
        MelFid(b'INAM','deathItem'),
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
        MelFids(b'PKID','aiPackages'),
        MelAnimations(),
        MelStruct(b'DATA', [u'4B', u'h', u'2s', u'h', u'7B'],'creatureType','combatSkill','magicSkill',
            'stealthSkill','health','unused2','damage','strength',
            'perception','endurance','charisma','intelligence','agility',
            'luck'),
        MelUInt8(b'RNAM', 'attackReach'),
        MelFid(b'ZNAM','combatStyle'),
        MelFid(b'PNAM','bodyPartData'),
        MelFloat(b'TNAM', 'turningSpeed'),
        MelFloat(b'BNAM', 'baseScale'),
        MelFloat(b'WNAM', 'footWeight'),
        MelUInt32(b'NAM4', u'impactMaterialType'),
        MelUInt32(b'NAM5', u'soundLevel'),
        MelFid(b'CSCR','inheritsSoundsFrom'),
        MelActorSounds(),
        MelFid(b'CNAM','impactDataset'),
        MelFid(b'LNAM','meleeWeaponList'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCsty(MelRecord):
    """Combat Style."""
    rec_sig = b'CSTY'

    _flagsA = Flags(0, Flags.getNames(
        ( 0,'advanced'),
        ( 1,'useChanceForAttack'),
        ( 2,'ignoreAllies'),
        ( 3,'willYield'),
        ( 4,'rejectsYields'),
        ( 5,'fleeingDisabled'),
        ( 6,'prefersRanged'),
        ( 7,'meleeAlertOK'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelOptStruct(b'CSTD', [u'2B', u'2s', u'8f', u'2B', u'2s', u'3f', u'B', u'3s', u'2f', u'5B', u'3s', u'2f', u'H', u'2s', u'2B', u'2s', u'f'],'dodgeChance',
                    'lrChance','unused1','lrTimerMin','lrTimerMax',
                    'forTimerMin','forTimerMax','backTimerMin','backTimerMax',
                    'idleTimerMin','idleTimerMax','blkChance','atkChance',
                    'unused2','atkBRecoil','atkBunc','atkBh2h',
                    'pAtkChance','unused3','pAtkBRecoil','pAtkBUnc',
                    'pAtkNormal','pAtkFor','pAtkBack','pAtkL','pAtkR',
                    'unused4','holdTimerMin','holdTimerMax',
                    (_flagsA,'flagsA'),'unused5','acroDodge',
                    ('rushChance',25),'unused6',('rushMult',1.0)),
        MelOptStruct(b'CSAD', [u'21f'], 'dodgeFMult', 'dodgeFBase', 'encSBase', 'encSMult',
                     'dodgeAtkMult', 'dodgeNAtkMult', 'dodgeBAtkMult', 'dodgeBNAtkMult',
                     'dodgeFAtkMult', 'dodgeFNAtkMult', 'blockMult', 'blockBase',
                     'blockAtkMult', 'blockNAtkMult', 'atkMult','atkBase', 'atkAtkMult',
                     'atkNAtkMult', 'atkBlockMult', 'pAtkFBase', 'pAtkFMult'),
        MelOptStruct(b'CSSD', [u'9f', u'4s', u'I', u'5f'], 'coverSearchRadius', 'takeCoverChance',
                     'waitTimerMin', 'waitTimerMax', 'waitToFireTimerMin',
                     'waitToFireTimerMax', 'fireTimerMin', 'fireTimerMax',
                     'rangedWeaponRangeMultMin','unknown1','weaponRestrictions',
                     'rangedWeaponRangeMultMax','maxTargetingFov','combatRadius',
                     'semiAutomaticFireDelayMultMin','semiAutomaticFireDelayMultMax'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDebr(MelRecord):
    """Debris."""
    rec_sig = b'DEBR'

    dataFlags = Flags(0, Flags.getNames(u'hasCollissionData'))

    melSet = MelSet(
        MelEdid(),
        MelGroups(u'models',
            MelDebrData(),
            MelBase(b'MODT', u'modt_p'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDial(MelRecord):
    """Dialogue."""
    rec_sig = b'DIAL'

    _DialFlags = Flags(0, Flags.getNames('rumors', 'toplevel'))

    melSet = MelSet(
        MelEdid(),
        MelSorted(MelFids(b'QSTI', 'added_quests')),
        MelSorted(MelFids(b'QSTR', 'removed_quests')),
        MelFull(),
        MelFloat(b'PNAM', 'priority'),
        MelTruncatedStruct(b'DATA', [u'2B'], 'dialType',
                           (_DialFlags, u'dialFlags'), old_versions={'B'}),
    )
    __slots__ = melSet.getSlotsUsed()

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDoor(MelRecord):
    """Door."""
    rec_sig = b'DOOR'

    _flags = Flags(0,Flags.getNames(
        ( 1,'automatic'),
        ( 2,'hidden'),
        ( 3,'minimalUse'),
        ( 4,'slidingDoor',),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelDestructible(),
        MelFid(b'SNAM','soundOpen'),
        MelFid(b'ANAM','soundClose'),
        MelFid(b'BNAM','soundLoop'),
        MelUInt8Flags(b'FNAM', u'flags', _flags),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEczn(MelRecord):
    """Encounter Zone."""
    rec_sig = b'ECZN'

    _flags = Flags(0, Flags.getNames('neverResets','matchPCBelowMinimumLevel'))

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', [u'I', u'2b', u'B', u's'], (FID, u'owner'), u'rank', u'minimumLevel',
                  (_flags, u'flags'), u'unused1'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEfsh(MelRecord):
    """Effect Shader."""
    rec_sig = b'EFSH'

    _flags = Flags(0, Flags.getNames(
        (0, u'noMemShader'),
        (3, u'noPartShader'),
        (4, u'edgeInverse'),
        (5, u'memSkinOnly'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelIcon(u'fillTexture'),
        MelIco2(u'particleTexture'),
        MelString(b'NAM7', u'holesTexture'),
        MelTruncatedStruct(b'DATA',
            [u'B', u'3s', u'3I', u'3B', u's', u'9f', u'3B', u's', u'8f', u'5I',
             u'19f', u'3B', u's', u'3B', u's', u'3B', u's', u'11f', u'I',
             u'5f', u'3B', u's', u'f', u'2I', u'6f'], (_flags, u'flags'),
            u'unused1', (u'memSBlend', 5), (u'memBlendOp', 1),
            (u'memZFunc', 3), u'fillRed', u'fillGreen', u'fillBlue',
            u'unused2', u'fillAIn', u'fillAFull', u'fillAOut',
            u'fillAPRatio', u'fillAAmp', u'fillAFreq', u'fillAnimSpdU',
            u'fillAnimSpdV', u'edgeOff', u'edgeRed', u'edgeGreen', u'edgeBlue',
            u'unused3', u'edgeAIn', u'edgeAFull', u'edgeAOut',
            u'edgeAPRatio', u'edgeAAmp', u'edgeAFreq', u'fillAFRatio',
            u'edgeAFRatio', (u'memDBlend', 6), (u'partSBlend', 5),
            (u'partBlendOp', 1), (u'partZFunc', 4), (u'partDBlend', 6),
            u'partBUp', u'partBFull', u'partBDown', (u'partBFRatio', 1.0),
            (u'partBPRatio', 1.0), (u'partLTime', 1.0), u'partLDelta',
            u'partNSpd', u'partNAcc', u'partVel1', u'partVel2', u'partVel3',
            u'partAcc1', u'partAcc2', u'partAcc3', (u'partKey1', 1.0),
            (u'partKey2', 1.0), u'partKey1Time', (u'partKey2Time', 1.0),
            (u'key1Red', 255), (u'key1Green', 255), (u'key1Blue', 255),
            u'unused4', (u'key2Red', 255), (u'key2Green', 255),
            (u'key2Blue', 255), u'unused5', (u'key3Red', 255),
            (u'key3Green', 255), (u'key3Blue', 255), u'unused6',
            (u'key1A', 1.0), (u'key2A', 1.0), (u'key3A', 1.0), u'key1Time',
            (u'key2Time', 0.5), (u'key3Time', 1.0), u'partNSpdDelta',
            u'partRot', u'partRotDelta', u'partRotSpeed', u'partRotSpeedDelta',
            (FID, u'addonModels'), u'holesStartTime', u'holesEndTime',
            u'holesStartVal', u'holesEndVal', u'edgeWidth',
            (u'edge_color_red', 255), (u'edge_color_green', 255),
            (u'edge_color_blue', 255), u'unused7',
            u'explosionWindSpeed', (u'textureCountU', 1),
            (u'textureCountV', 1), (u'addonModelsFadeInTime', 1.0),
            (u'addonModelsFadeOutTime', 1.0), (u'addonModelsScaleStart', 1.0),
            (u'addonModelsScaleEnd', 1.0), (u'addonModelsScaleInTime', 1.0),
            (u'addonModelsScaleOutTime', 1.0),
            old_versions={u'B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I4f',
                          u'B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I',
                          u'B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI',
                          u'B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11f',
                          u'B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs6f'}),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEnch(MelRecord):
    """Object Effect."""
    rec_sig = b'ENCH'

    _flags = Flags(0, Flags.getNames(
        (0, 'noAutoCalc'),
        fnv_only((1, 'autoCalculate')),
        (2, 'hideEffect',)
    ))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelStruct(b'ENIT', [u'3I', u'B', u'3s'],'itemType','chargeAmount','enchantCost',
                  (_flags, u'flags'),'unused1'),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreExpl(MelRecord):
    """Explosion."""
    rec_sig = b'EXPL'

    _flags = Flags(0,Flags.getNames(
        (1, 'alwaysUsesWorldOrientation'),
        (2, 'knockDownAlways'),
        (3, 'knockDownByFormular'),
        (4, 'ignoreLosCheck'),
        (5, 'pushExplosionSourceRefOnly'),
        (6, 'ignoreImageSpaceSwap'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelEnchantment(),
        MelFid(b'MNAM','imageSpaceModifier'),
        MelStruct(b'DATA', [u'3f', u'3I', u'f', u'2I', u'3f', u'I'], u'force', u'damage', u'radius',
                  (FID, u'light'), (FID, u'sound1'), (_flags, u'flags'),
                  u'isRadius', (FID, u'impactDataset'), (FID, u'sound2'),
                  u'radiationLevel', u'radiationTime', u'radiationRadius',
                  u'soundLevel'),
        MelFid(b'INAM','placedImpactObject'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEyes(MelRecord):
    """Eyes."""
    rec_sig = b'EYES'

    _flags = Flags(0, Flags.getNames(
            (0, 'playable'),
            (1, 'notMale'),
            (2, 'notFemale'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelIcon(),
        MelUInt8Flags(b'DATA', u'flags', _flags),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFact(MelRecord):
    """Faction."""
    rec_sig = b'FACT'

    _general_flags = Flags(0, Flags.getNames(u'hidden_from_pc', u'evil',
                                     u'special_combat'))
    _general_flags_2 = Flags(0, Flags.getNames(u'track_crime', u'allow_sell'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelRelations(),
        MelTruncatedStruct(b'DATA', [u'2B', u'2s'],
                           (_general_flags, u'general_flags'),
                           (_general_flags_2, u'general_flags_2'),
                           u'unused1', old_versions={u'2B', u'B'}),
        MelFloat(b'CNAM', u'cnam_unused'), # leftover from Oblivion
        MelFactionRanks(),
        fnv_only(MelFid(b'WMI1', u'reputation')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFurn(MelRecord):
    """Furniture."""
    rec_sig = b'FURN'

    _flags = Flags() #--Governs type of furniture and which anims are available
    #--E.g., whether it's a bed, and which of the bed entry/exit animations are available

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelDestructible(),
        MelUInt32Flags(b'MNAM', u'activeMarkers', _flags),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreGmst(MreGmstBase):
    """Game Setting."""
    isKeyedByEid = True # NULL fids are acceptable.

#------------------------------------------------------------------------------
class MreGras(MelRecord):
    """Grass."""
    rec_sig = b'GRAS'

    _flags = Flags(0,Flags.getNames('vLighting','uScaling','fitSlope'))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelStruct(b'DATA', [u'3B', u's', u'H', u'2s', u'I', u'4f', u'B', u'3s'],'density','minSlope',
                  'maxSlope','unused1','waterDistance','unused2',
                  'waterOp','posRange','heightRange','colorRange',
                  'wave_period', (_flags, 'flags'), 'unused3'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreHair(MelRecord):
    """Hair."""
    rec_sig = b'HAIR'

    _flags = Flags(0, Flags.getNames('playable','notMale','notFemale','fixed'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelUInt8Flags(b'DATA', u'flags', _flags),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreHdpt(MelRecord):
    """Head Part."""
    rec_sig = b'HDPT'

    _flags = Flags(0, Flags.getNames('playable',))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelUInt8Flags(b'DATA', u'flags', _flags),
        MelSorted(MelFids(b'HNAM', 'extraParts')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIdle(MelRecord):
    """Idle Animation."""
    rec_sig = b'IDLE'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelConditions(),
        MelStruct(b'ANAM', [u'I', u'I'],(FID,'parent'),(FID,'prevId')),
        MelTruncatedStruct(b'DATA', [u'3B', u's', u'h', u'B', u's'], 'group', 'loopMin', 'loopMax',
                           'unknown1', 'delay', 'flags',
                           'unknown2', old_versions={'3Bsh'}),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIdlm(MelRecord):
    """Idle Marker."""
    rec_sig = b'IDLM'

    _flags = Flags(0, Flags.getNames('runInSequence',None,'doOnce'))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8Flags(b'IDLF', u'flags', _flags),
        MelPartialCounter(MelTruncatedStruct(
            b'IDLC', [u'B', u'3s'], 'animation_count', 'unused',
            old_versions={'B'}),
            counter='animation_count', counts='animations'),
        MelFloat(b'IDLT', 'idleTimerSetting'),
        MelFidList(b'IDLA','animations'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreImad(MelRecord):
    """Image Space Adapter."""
    rec_sig = b'IMAD'

    _ImadDofFlags = Flags(0, Flags.getNames(
        (0, 'useTarget'),
    ))
    _ImadAnimatableFlags = Flags(0, Flags.getNames(
        (0, 'animatable'),
    ))
    _ImadRadialBlurFlags = Flags(0, Flags.getNames(
        (0, 'useTarget')
    ))

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DNAM', [u'I', u'f', u'49I', u'2f', u'8I'], (_ImadAnimatableFlags, u'aniFlags'),
                  'duration', 'eyeAdaptSpeedMult', 'eyeAdaptSpeedAdd',
                  'bloomBlurRadiusMult', 'bloomBlurRadiusAdd',
                  'bloomThresholdMult', 'bloomThresholdAdd', 'bloomScaleMult',
                  'bloomScaleAdd', 'targetLumMinMult', 'targetLumMinAdd',
                  'targetLumMaxMult', 'targetLumMaxAdd', 'sunlightScaleMult',
                  'sunlightScaleAdd', 'skyScaleMult', 'skyScaleAdd',
                  'unknown08Mult', 'unknown48Add', 'unknown09Mult',
                  'unknown49Add', 'unknown0AMult', 'unknown4AAdd',
                  'unknown0BMult', 'unknown4BAdd', 'unknown0CMult',
                  'unknown4CAdd', 'unknown0DMult', 'unknown4DAdd',
                  'unknown0EMult', 'unknown4EAdd', 'unknown0FMult',
                  'unknown4FAdd', 'unknown10Mult', 'unknown50Add',
                  'saturationMult', 'saturationAdd', 'brightnessMult',
                  'brightnessAdd', 'contrastMult', 'contrastAdd',
                  'unknown14Mult', 'unknown54Add',
                  'tintColor', 'blurRadius', 'doubleVisionStrength',
                  'radialBlurStrength', 'radialBlurRampUp', 'radialBlurStart',
                  (_ImadRadialBlurFlags, u'radialBlurFlags'),
                  'radialBlurCenterX', 'radialBlurCenterY', 'dofStrength',
                  'dofDistance', 'dofRange', (_ImadDofFlags, u'dofFlags'),
                  'radialBlurRampDown', 'radialBlurDownStart', 'fadeColor',
                  'motionBlurStrength'),
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
        # FIXME(inf) Test! From here until saturationMultInterp were marked as
        #  MelBase and unknown in FO3
        MelValueInterpolator(b'\x08IAD', 'lumRampNoTexMultInterp'),
        MelValueInterpolator(b'\x48IAD', 'lumRampNoTexAddInterp'),
        MelValueInterpolator(b'\x09IAD', 'lumRampMinMultInterp'),
        MelValueInterpolator(b'\x49IAD', 'lumRampMinAddInterp'),
        MelValueInterpolator(b'\x0AIAD', 'lumRampMaxMultInterp'),
        MelValueInterpolator(b'\x4AIAD', 'lumRampMaxAddInterp'),
        MelValueInterpolator(b'\x0BIAD', 'sunlightDimmerMultInterp'),
        MelValueInterpolator(b'\x4BIAD', 'sunlightDimmerAddInterp'),
        MelValueInterpolator(b'\x0CIAD', 'grassDimmerMultInterp'),
        MelValueInterpolator(b'\x4CIAD', 'grassDimmerAddInterp'),
        MelValueInterpolator(b'\x0DIAD', 'treeDimmerMultInterp'),
        MelValueInterpolator(b'\x4DIAD', 'treeDimmerAddInterp'),
        MelValueInterpolator(b'\x0EIAD', 'blurRadiusMultInterp'),
        MelValueInterpolator(b'\x4EIAD', 'blurRadiusAddInterp'),
        MelValueInterpolator(b'\x0FIAD', 'alphaMultInteriorMultInterp'),
        MelValueInterpolator(b'\x4FIAD', 'alphaMultInteriorAddInterp'),
        MelValueInterpolator(b'\x10IAD', 'alphaMultExteriorMultInterp'),
        MelValueInterpolator(b'\x50IAD', 'alphaMultExteriorAddInterp'),
        MelValueInterpolator(b'\x11IAD', 'saturationMultInterp'),
        MelValueInterpolator(b'\x51IAD', 'saturationAddInterp'),
        MelValueInterpolator(b'\x12IAD', if_fnv(
            fo3_version='brightnessMultInterp',
            fnv_version='contrastMultInterp',
        )),
        MelValueInterpolator(b'\x52IAD', if_fnv(
            fo3_version='brightnessAddInterp',
            fnv_version='contrastAddInterp',
        )),
        MelValueInterpolator(b'\x13IAD', if_fnv(
            fo3_version='contrastMultInterp',
            fnv_version='contrastAvgMultInterp',
        )),
        MelValueInterpolator(b'\x53IAD', if_fnv(
            fo3_version='contrastAddInterp',
            fnv_version='contrastAvgAddInterp',
        )),
        # FIXME(inf) Test! These two were MelBase in FO3
        MelValueInterpolator(b'\x14IAD', if_fnv(
            fo3_version='unknown14IAD',
            fnv_version='brightnessMultInterp',
        )),
        MelValueInterpolator(b'\x54IAD', if_fnv(
            fo3_version='unknown54IAD',
            fnv_version='brightnessAddInterp'
        )),
        fnv_only(MelFid(b'RDSD', 'soundIntro')),
        fnv_only(MelFid(b'RDSI', 'soundOutro')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreImgs(MelRecord):
    """Image Space."""
    rec_sig = b'IMGS'

    _dnam_flags = Flags(0, Flags.getNames(
        u'saturation',
        u'contrast',
        u'tint',
        u'brightness'
    ), unknown_is_unused=True)

    # Struct elements shared by all three DNAM alternatives. Note that we can't
    # just use MelTruncatedStruct, because upgrading the format breaks interior
    # lighting for some reason.
    ##: If this becomes common, extract into dedicated class
    _dnam_common = [
        u'eyeAdaptSpeed', u'blurRadius', u'blurPasses', u'emissiveMult',
        u'targetLUM', u'upperLUMClamp', u'brightScale', u'brightClamp',
        u'lumRampNoTex', u'lumRampMin', u'lumRampMax', u'sunlightDimmer',
        u'grassDimmer', u'treeDimmer', u'skinDimmer', u'bloomBlurRadius',
        u'bloomAlphaMultInterior', u'bloomAlphaMultExterior',
        u'getHitBlurRadius', u'getHitBlurDampingConstant',
        u'getHitDampingConstant', u'nightEyeTintRed', u'nightEyeTintGreen',
        u'nightEyeTintBlue', u'nightEyeBrightness', u'cinematicSaturation',
        u'cinematicAvgLumValue', u'cinematicValue',
        u'cinematicBrightnessValue', u'cinematicTintRed',
        u'cinematicTintGreen', u'cinematicTintBlue', u'cinematicTintValue',
    ]
    _dnam_fmts = [u'33f', u'4s', u'4s', u'4s', u'4s']
    melSet = MelSet(
        MelEdid(),
        MelUnion({
            152: MelStruct(
                b'DNAM', _dnam_fmts + [u'B', u'3s'], *(_dnam_common + [
                    u'unused1', u'unused2', u'unused3', u'unused4',
                    (_dnam_flags, u'dnam_flags'), u'unused5',
                ])),
            148: MelStruct(
                b'DNAM', _dnam_fmts, *(_dnam_common + [
                    u'unused1', u'unused2',
                    u'unused3', u'unused4',
                ])),
            132: MelStruct(b'DNAM', [u'33f'], *_dnam_common),
        }, decider=SizeDecider()),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreInfo(MelRecord):
    """Dialog Response."""
    rec_sig = b'INFO'

    _flags = Flags(0, Flags.getNames(
        'goodbye',
        'random',
        'sayOnce',
        'runImmediately',
        'infoRefusal',
        'randomEnd',
        'runForRumors',
        'speechChallenge',
    ))
    _flags2 = Flags(0, Flags.getNames(
        (0, 'sayOnceADay'),
        (1, 'alwaysDarken'),
        fnv_only((4, 'lowIntelligence')),
        fnv_only((5, 'highIntelligence')),
    ))

    melSet = MelSet(
        MelTruncatedStruct(b'DATA', [u'4B'], 'dialType', 'nextSpeaker',
                           (_flags, 'flags'), (_flags2, 'flagsInfo'),
                           old_versions={'2B'}),
        MelFid(b'QSTI', u'info_quest'),
        MelFid(b'TPIC', u'info_topic'),
        MelFid(b'PNAM', 'prev_info'),
        MelFids(b'NAME','addTopics'),
        MelGroups('responses',
            MelStruct(b'TRDT', [u'I', u'i', u'4s', u'B', u'3s', u'I', u'B', u'3s'],'emotionType','emotionValue','unused1','responseNum',('unused2',b'\xcd\xcd\xcd'),
                      (FID,'sound'),'flags',('unused3',b'\xcd\xcd\xcd')),
            MelString(b'NAM1','responseText'),
            MelString(b'NAM2','actorNotes'),
            MelString(b'NAM3','edits'),
            MelFid(b'SNAM','speakerAnimation'),
            MelFid(b'LNAM','listenerAnimation'),
        ),
        MelConditions(),
        MelFids(b'TCLT','choices'),
        MelFids(b'TCLF','linksFrom'),
        fnv_only(MelFids(b'TCFU', 'follow_up')),
        MelGroup('scriptBegin',
            MelEmbeddedScript(),
        ),
        MelGroup('scriptEnd',
            MelBase(b'NEXT','marker'),
            MelEmbeddedScript(),
        ),
        MelFid(b'SNDD','sndd_p'),
        MelString(b'RNAM','prompt'),
        MelFid(b'ANAM','speaker'),
        MelFid(b'KNAM','acterValuePeak'),
        MelUInt32(b'DNAM', 'speechChallenge')
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIngr(MelRecord):
    """Ingredient."""
    rec_sig = b'INGR'

    _flags = Flags(0, Flags.getNames('noAutoCalc','isFood'))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelEquipmentType(),
        MelFloat(b'DATA', 'weight'),
        MelStruct(b'ENIT', [u'i', u'B', u'3s'],'value',(_flags, u'flags'),'unused1'),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIpct(MelRecord):
    """Impact."""
    rec_sig = b'IPCT'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelStruct(b'DATA', [u'f', u'I', u'f', u'f', u'I', u'I'],'effectDuration','effectOrientation',
                  'angleThreshold','placementRadius','soundLevel','flags'),
        MelDecalData(),
        MelFid(b'DNAM','textureSet'),
        MelFid(b'SNAM','sound1'),
        MelFid(b'NAM1','sound2'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIpds(MelRecord):
    """Impact Dataset."""
    rec_sig = b'IPDS'

    melSet = MelSet(
        MelEdid(),
        MelTruncatedStruct(
            b'DATA', [u'12I'], (FID, u'stone'), (FID, u'dirt'),
            (FID, u'grass'), (FID, u'glass'), (FID, u'metal'),
            (FID, u'wood'), (FID, u'organic'), (FID, u'cloth'),
            (FID, u'water'), (FID, u'hollowMetal'), (FID, u'organicBug'),
            (FID, u'organicGlow'), old_versions={'10I', '9I'}),
    )
    __slots__ = melSet.getSlotsUsed()

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
        MelPickupSound(),
        MelDropSound(),
        MelStruct(b'DATA', [u'i', u'f'],'value','weight'),
        fnv_only(MelFid(b'RNAM', 'soundRandomLooping')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLgtm(MelRecord):
    """Lighting Template."""
    rec_sig = b'LGTM'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', [u'3B', u's', u'3B', u's', u'3B', u's', u'2f', u'2i', u'3f'],
            'redLigh','greenLigh','blueLigh','unknownLigh',
            'redDirect','greenDirect','blueDirect','unknownDirect',
            'redFog','greenFog','blueFog','unknownFog',
            'fogNear','fogFar',
            'dirRotXY','dirRotZ',
            'directionalFade','fogClipDist','fogPower',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLigh(MelRecord):
    """Light."""
    rec_sig = b'LIGH'

    _flags = Flags(0, Flags.getNames('dynamic','canTake','negative','flickers',
        'unk1','offByDefault','flickerSlow','pulse','pulseSlow','spotLight','spotShadow'))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelScript(),
        MelDestructible(),
        MelFull(),
        MelIcons(),
        MelStruct(b'DATA', [u'i', u'I', u'3B', u's', u'I', u'2f', u'I', u'f'],'duration','radius','red','green','blue',
                  'unused1',(_flags, u'flags'),'falloff','fov','value',
                  'weight'),
        MelFloat(b'FNAM', u'fade'),
        MelFid(b'SNAM','sound'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLscr(MelRecord):
    """Load Screen."""
    rec_sig = b'LSCR'

    melSet = MelSet(
        MelEdid(),
        MelIcon(),
        MelDescription(),
        # Marked as an unused byte array in FO3Edit, but has the exact same
        # size so just treat it the same as TES4/FNV
        MelLscrLocations(),
        fnv_only(MelFid(b'WMI1', 'loadScreenType')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLtex(MelRecord):
    """Landscape Texture."""
    rec_sig = b'LTEX'

    melSet = MelSet(
        MelEdid(),
        MelIcon(),
        MelFid(b'TNAM', 'texture'),
        MelOptStruct(b'HNAM', [u'3B'],'materialType','friction','restitution'),
        MelUInt8(b'SNAM', 'specular'),
        MelSorted(MelFids(b'GNAM', 'grass')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLvlc(MreLeveledList):
    """Leveled Creature."""
    rec_sig = b'LVLC'
    __slots__ = []

#------------------------------------------------------------------------------
class MreLvli(MreLeveledList):
    """Leveled Item."""
    rec_sig = b'LVLI'
    __slots__ = []

#------------------------------------------------------------------------------
class MreLvln(MreLeveledList):
    """Leveled NPC."""
    rec_sig = b'LVLN'
    __slots__ = []

#------------------------------------------------------------------------------
class MreMesg(MelRecord):
    """Message."""
    rec_sig = b'MESG'

    MesgTypeFlags = Flags(0, Flags.getNames(
            (0, 'messageBox'),
            (1, 'autoDisplay'),
        ))

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
        MelGroups('menuButtons',
            MelString(b'ITXT','buttonText'),
            MelConditions(),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMgef(MelRecord):
    """Magic Effect."""
    rec_sig = b'MGEF'

    _flags = Flags(0, Flags.getNames(
        ( 0, u'hostile'),
        ( 1, u'recover'),
        ( 2, u'detrimental'),
        ( 3, u'magnitude'),
        ( 4, u'self'),
        ( 5, u'touch'),
        ( 6, u'target'),
        ( 7, u'noDuration'),
        ( 8, u'noMagnitude'),
        ( 9, u'noArea'),
        (10, u'fxPersist'),
        (11, u'spellmaking'),
        (12, u'enchanting'),
        (13, u'noIngredient'),
        (16, u'useWeapon'),
        (17, u'useArmor'),
        (18, u'useCreature'),
        (19, u'useSkill'),
        (20, u'useAttr'),
        (24, u'useAV'),
        (25, u'sprayType'),
        (26, u'boltType'),
        (27, u'noHitEffect')))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelIcon(),
        MelModel(),
        MelPartialCounter(MelStruct(b'DATA',
            [u'I', u'f', u'I', u'2i', u'H', u'2s', u'I', u'f', u'6I', u'2f',
             u'I', u'i'], (_flags, u'flags'), u'base_cost',
            (FID, u'associated_item'), u'school', u'resist_value',
            u'counter_effect_count', u'unused1',
            (FID, u'light'), u'projectileSpeed', (FID, u'effectShader'),
            (FID, u'enchantEffect'), (FID, u'castingSound'),
            (FID, u'boltSound'), (FID, u'hitSound'), (FID, u'areaSound'),
            u'cef_enchantment', u'cef_barter', u'effect_archetype',
            u'actorValue'),
            counter=u'counter_effect_count', counts=u'counter_effects'),
        MelSorted(MelGroups(u'counter_effects',
            MelFid(b'ESCE', u'counter_effect_code'),
        ), sort_by_attrs='counter_effect_code'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMicn(MelRecord):
    """Menu Icon."""
    rec_sig = b'MICN'
    melSet = MelSet(
        MelEdid(),
        MelIcons(),
    )
    __slots__ = melSet.getSlotsUsed()

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
        MelPickupSound(),
        MelDropSound(),
        MelStruct(b'DATA', [u'i', u'f'],'value','weight'),
        fnv_only(MelFid(b'RNAM', 'soundRandomLooping')),
    )
    __slots__ = melSet.getSlotsUsed()

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
        MelFid(b'SNAM','sound'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMusc(MelRecord):
    """Music Type."""
    rec_sig = b'MUSC'

    melSet = MelSet(
        MelEdid(),
        MelString(b'FNAM','filename'),
        fnv_only(MelFloat(b'ANAM', 'dB')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreNavi(MelRecord):
    """Navigation Mesh Info Map."""
    rec_sig = b'NAVI'

    melSet = MelSet(
        MelEdid(),
        MelUInt32(b'NVER', u'version', 11),
        MelGroups('nav_map_infos',
            # Contains fids, but we probably won't ever be able to merge NAVI,
            # so leaving this as MelBase for now
            MelBase(b'NVMI', 'nav_map_info'),
        ),
        MelFidList(b'NVCI','unknownDoors',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreNavm(MelRecord):
    """Navigation Mesh."""
    rec_sig = b'NAVM'

    melSet = MelSet(
        MelEdid(),
        MelUInt32(b'NVER', u'version', 11),
        MelStruct(b'DATA', [u'I', u'5I'],(FID,'cell'),'vertexCount','triangleCount','enternalConnectionsCount','nvcaCount','doorsCount'),
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
    __slots__ = melSet.getSlotsUsed()

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
        MelPickupSound(),
        MelDropSound(),
        MelUInt8(b'DATA', 'dataType'),
        MelSorted(MelFidList(b'ONAM', 'quests')),
        MelString(b'XNAM','texture'),
        MelUnion({
            3: MelFid(b'TNAM', u'textTopic'),
        }, decider=AttrValDecider(u'dataType'),
            fallback=MelString(b'TNAM', u'textTopic')),
        MelFid(b'SNAM', 'soundNpc'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class _MelNpcData(MelLists):
    """Convert npc stats into health, attributes."""
    _attr_indexes = OrderedDict(
        [(u'health', 0), (u'attributes', slice(1, None))])

    def __init__(self, struct_formats):
        super(_MelNpcData, self).__init__(b'DATA', struct_formats, u'health',
                                          (u'attributes', [0] * 21))

class MreNpc(MreActor):
    """Non-Player Character."""
    rec_sig = b'NPC_'

    _flags = Flags(0, Flags.getNames(
        ( 0,'female'),
        ( 1,'essential'),
        ( 2,'isChargenFacePreset'),
        ( 3,'respawn'),
        ( 4,'autoCalc'),
        ( 7,'pcLevelOffset'),
        ( 8,'useTemplate'),
        ( 9,'noLowLevel'),
        (11,'noBloodSpray'),
        (12,'noBloodDecal'),
        (20,'noVATSMelee'),
        (22,'canBeAllRaces'),
        (23,'autocalcService'), # FNV Only
        (26,'noKnockDown'),
        (27,'notPushable'),
        (30,'noRotatingHeadTrack')))
    aiService = Flags(0, Flags.getNames(
        (0,'weapons'),
        (1,'armor'),
        (2,'clothing'),
        (3,'books'),
        (4,'foods'),
        (5,'chems'),
        (6,'stimpacks'),
        (7,'lights'),
        (10,'miscItems'),
        (13,'potions'),
        (14,'training'),
        (16,'recharge'),
        (17,'repair')))
    aggroflags = Flags(0, Flags.getNames('aggroRadiusBehavior',))

    class MelNpcDnam(MelLists):
        """Convert npc stats into skills."""
        _attr_indexes = OrderedDict(
            [(u'skillValues', slice(14)), (u'skillOffsets', slice(14, None))])

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelStruct(b'ACBS', [u'I', u'2H', u'h', u'3H', u'f', u'2H'],
            (_flags, u'flags'),'fatigue','barterGold',
            ('level_offset',1),'calcMin','calcMax','speedMultiplier','karma',
            'dispositionBase', (MreActor.TemplateFlags, u'templateFlags')),
        MelFactions(),
        MelFid(b'INAM','deathItem'),
        MelFid(b'VTCK','voice'),
        MelFid(b'TPLT','template'),
        MelFid(b'RNAM','race'),
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
        MelFids(b'PKID','aiPackages'),
        MelAnimations(),
        MelFid(b'CNAM','iclass'),
        MelUnion({
            11: _MelNpcData([u'I', u'7B']),
            25: _MelNpcData([u'I', u'21B'])
        }, decider=SizeDecider()),
        MelSorted(MelFids(b'PNAM', 'headParts')),
        MelNpcDnam(b'DNAM', [u'14B', u'14B'], (u'skillValues', [0] * 14),
                   (u'skillOffsets', [0] * 14)),
        MelFid(b'HNAM', 'hair'),
        MelFloat(b'LNAM', u'hairLength'),
        MelFid(b'ENAM', 'eye'),
        MelStruct(b'HCLR', [u'3B', u's'],'hairRed','hairBlue','hairGreen','unused3'),
        MelFid(b'ZNAM','combatStyle'),
        MelUInt32(b'NAM4', u'impactMaterialType'),
        MelBase(b'FGGS','fggs_p'), ####FaceGen Geometry-Symmetric
        MelBase(b'FGGA','fgga_p'), ####FaceGen Geometry-Asymmetric
        MelBase(b'FGTS','fgts_p'), ####FaceGen Texture-Symmetric
        MelUInt16(b'NAM5', u'unknown'),
        MelFloat(b'NAM6', u'height'),
        MelFloat(b'NAM7', u'weight'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MelIdleHandler(MelGroup):
    """Occurs three times in PACK, so moved here to deduplicate the
    definition a bit."""
    _variableFlags = Flags(0, Flags.getNames(u'isLongOrShort'))

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

    _flags = Flags(0,Flags.getNames(
        'offersServices','mustReachLocation','mustComplete','lockAtStart',
        'lockAtEnd','lockAtLocation','unlockAtStart','unlockAtEnd',
        'unlockAtLocation','continueIfPcNear','oncePerDay',None,
        'skipFallout','alwaysRun',None,None,
        None,'alwaysSneak','allowSwimming','allowFalls',
        'unequipArmor','unequipWeapons','defensiveCombat','useHorse',
        'noIdleAnims',))
    _fallout_behavior_flags = Flags(0, Flags.getNames(
        u'hellos_to_player',
        u'random_conversations',
        u'observe_combat_behavior',
        u'unknown_flag_4', # unknown, but not unused
        u'reaction_to_player_actions',
        u'friendly_fire_comments',
        u'aggro_radius_behavior',
        u'allow_idle_chatter',
        u'avoid_radiation',
    ), unknown_is_unused=True)
    _dialogue_data_flags = Flags(0, Flags.getNames(
        (0, u'no_headtracking'),
        (8, u'dont_control_target_movement'),
    ))

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
        MelConditions(),
        MelGroup('idleAnimations',
            MelUInt8(b'IDLF', 'animationFlags'),
            MelPartialCounter(MelStruct(b'IDLC', [u'B', u'3s'], 'animation_count',
                                        'unused'),
                              counter='animation_count', counts='animations'),
            MelFloat(b'IDLT', 'idleTimerSetting'),
            MelFidList(b'IDLA','animations'),
            MelBase(b'IDLB','idlb_p'),
        ),
        MelBase(b'PKED','eatMarker'),
        MelUInt32(b'PKE2', 'escortDistance'),
        MelFid(b'CNAM','combatStyle'),
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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MrePerk(MelRecord):
    """Perk."""
    rec_sig = b'PERK'

    _PerkScriptFlags = Flags(0, Flags.getNames(
        (0, 'runImmediately'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelIcons(),
        MelConditions(),
        MelTruncatedStruct(b'DATA', [u'5B'], 'trait', 'minLevel',
                           'ranks', 'playable', 'hidden',
                           old_versions={'4B'}),
        MelSorted(MelGroups('effects',
            MelStruct(b'PRKE', [u'3B'], 'type', 'rank', 'priority'),
            MelUnion({
                0: MelStruct(b'DATA', [u'I', u'B', u'3s'], (FID, u'quest'), u'quest_stage',
                    u'unused_data'),
                1: MelFid(b'DATA', u'ability'),
                2: MelStruct(b'DATA', [u'3B'], u'entry_point', u'function',
                    u'perk_conditions_tab_count'),
            }, decider=AttrValDecider(u'type')),
            MelSorted(MelGroups('effectConditions',
                MelSInt8(b'PRKC', 'runOn'),
                MelConditions(),
            ), sort_by_attrs='runOn'),
            MelGroups('effectParams',
                # EPFT has the following meanings:
                #  0: Unknown
                #  1: EPFD=float
                #  2: EPFD=float, float
                #  3: EPFD=fid (LVLI)
                #  4: EPFD=Null (Script)
                # TODO(inf) there is a special case: If EPFT is 2 and
                #  DATA/function is 5, then:
                #  EPFD=uint32, float
                #  See commented out skeleton below - needs '../' syntax
                MelUInt8(b'EPFT', 'function_parameter_type'),
                MelUnion({
                    (0, 4): MelBase(b'EPFD', u'param1'),
                    1: MelFloat(b'EPFD', u'param1'),
                    2: MelStruct(b'EPFD', [u'I', u'f'], u'param1', u'param2'),
                    # 2: MelUnion({
                    #     5: MelStruct(b'EPFD', [u'I', u'f'], u'param1', u'param2'),
                    # }, decider=AttrValDecider(u'../function',
                    #     assign_missing=-1),
                    #     fallback=MelStruct(b'EPFD', [u'2f'], u'param1',
                    #         u'param2')),
                    3: MelFid(b'EPFD', u'param1'),
                }, decider=AttrValDecider(u'function_parameter_type')),
                MelString(b'EPF2','buttonLabel'),
                MelUInt16Flags(b'EPF3', u'script_flags', _PerkScriptFlags),
                MelEmbeddedScript(),
            ),
            MelBase(b'PRKF','footer'),
        ), sort_special=perk_effect_key),
    ).with_distributor({
        b'DESC': {
            b'CTDA|CIS1|CIS2': u'conditions',
            b'DATA': u'trait',
        },
        b'PRKE': {
            b'CTDA|CIS1|CIS2|DATA': u'effects',
        },
    })
    __slots__ = melSet.getSlotsUsed()

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
        fnv_only(MelString(b'XATO', 'activationPrompt')),
        MelEnableParent(),
        MelFid(b'XEMI', u'emittance'),
        MelFid(b'XMBR','multiboundReference'),
        MelBase(b'XIBS','ignoredBySandbox'),
        MelRefScale(),
        MelRef3D(),
    )
    __slots__ = melSet.getSlotsUsed()

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
        fnv_only(MelString(b'XATO', 'activationPrompt')),
        MelEnableParent(),
        MelFid(b'XEMI', u'emittance'),
        MelFid(b'XMBR','multiboundReference'),
        MelBase(b'XIBS','ignoredBySandbox'),
        MelRefScale(),
        MelRef3D(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreProj(MelRecord):
    """Projectile."""
    rec_sig = b'PROJ'

    _flags = Flags(0, Flags.getNames(
        (0, 'is_hitscan'),
        (1, 'is_explosive'),
        (2, 'alt_trigger'),
        (3, 'has_muzzle_flash'),
        (5, 'can_be_disabled'),
        (6, 'can_be_picked_up'),
        (7, 'is_super_sonic'),
        (8, 'pins_limbs'),
        (9, 'pass_through_small_transparent'),
        fnv_only((10, 'projectile_detonates')),
        fnv_only((11, 'projectile_rotates')),
    ))
    # Attributes shared between FO3 and FNV for the DATA subrecord
    _shared_data = [(_flags, 'flags'), 'type', 'gravity', ('speed', 10000.0),
                    ('range', 10000.0), (FID, 'light'), (FID, 'muzzleFlash'),
                    'tracerChance', 'explosionAltTrigerProximity',
                    'explosionAltTrigerTimer', (FID, 'explosion'),
                    (FID, 'sound'), 'muzzleFlashDuration', 'fadeDuration',
                    'impactForce', (FID, 'soundCountDown'),
                    (FID, 'soundDisable'), (FID, 'defaultWeaponSource')]

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MrePwat(MelRecord):
    """Placeable Water."""
    rec_sig = b'PWAT'

    _flags = Flags(0, Flags.getNames(
        ( 0,'reflects'),
        ( 1,'reflectsActers'),
        ( 2,'reflectsLand'),
        ( 3,'reflectsLODLand'),
        ( 4,'reflectsLODBuildings'),
        ( 5,'reflectsTrees'),
        ( 6,'reflectsSky'),
        ( 7,'reflectsDynamicObjects'),
        ( 8,'reflectsDeadBodies'),
        ( 9,'refracts'),
        (10,'refractsActors'),
        (11,'refractsLands'),
        (16,'refractsDynamicObjects'),
        (17,'refractsDeadBodies'),
        (18,'silhouetteReflections'),
        (28,'depth'),
        (29,'objectTextureCoordinates'),
        (31,'noUnderwaterFog'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelStruct(b'DNAM', [u'2I'],(_flags,'flags'),(FID,'water'))
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreQust(MelRecord):
    """Quest."""
    rec_sig = b'QUST'

    _questFlags = Flags(0,Flags.getNames('startGameEnabled',None,'repeatedTopics','repeatedStages'))
    stageFlags = Flags(0,Flags.getNames('complete'))
    targetFlags = Flags(0,Flags.getNames('ignoresLocks'))

    melSet = MelSet(
        MelEdid(),
        MelScript(),
        MelFull(),
        MelIcon(),
        MelTruncatedStruct(b'DATA', [u'2B', u'2s', u'f'], (_questFlags, u'questFlags'),
                           'priority', 'unused2',
                           'questDelay', old_versions={'2B'}),
        MelConditions(),
        MelSorted(MelGroups('stages',
            MelSInt16(b'INDX', 'stage'),
            MelGroups('entries',
                MelUInt8Flags(b'QSDT', u'flags', stageFlags),
                MelConditions(),
                MelString(b'CNAM','text'),
                MelEmbeddedScript(),
                MelFid(b'NAM0', 'nextQuest'),
            ),
        ), sort_by_attrs='stage'),
        MelGroups('objectives',
            MelSInt32(b'QOBJ', 'index'),
            MelString(b'NNAM','description'),
            MelGroups('targets',
                MelStruct(b'QSTA', [u'I', u'B', u'3s'],(FID,'targetId'),(targetFlags,'flags'),'unused1'),
                MelConditions(),
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
    __slots__ = melSet.getSlotsUsed()

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

class MreRace(MelRecord):
    """Race."""
    rec_sig = b'RACE'

    _flags = Flags(0, Flags.getNames((0, 'playable'), (2, 'child')))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelRelations(),
        MelRaceData(b'DATA', [u'14b', u'2s', u'4f', u'I'],
                    (u'skills', [0] * 14), 'unused1', 'maleHeight',
                    'femaleHeight', 'maleWeight', 'femaleWeight',
                    (_flags, u'flags')),
        MelFid(b'ONAM','Older'),
        MelFid(b'YNAM','Younger'),
        MelBase(b'NAM2','_nam2',b''),
        MelRaceVoices(b'VTCK', [u'2I'], (FID, 'maleVoice'), (FID, 'femaleVoice')),
        MelOptStruct(b'DNAM', [u'2I'],(FID, u'defaultHairMale'),(FID, u'defaultHairFemale')),
        # Int corresponding to GMST sHairColorNN
        MelStruct(b'CNAM', [u'2B'],'defaultHairColorMale','defaultHairColorFemale'),
        MelFloat(b'PNAM', 'mainClamp'),
        MelFloat(b'UNAM', 'faceClamp'),
        MelStruct(b'ATTR', [u'2s'], u'unused_attributes'), # leftover
        MelBase(b'NAM0', 'head_data_marker', b''),
        MelBase(b'MNAM', 'male_head_data_marker', b''),
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
        MelBase(b'FNAM', u'female_head_data_marker', b''),
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
        MelBase(b'NAM1', u'body_data_marker', b''),
        MelBase(b'MNAM', u'male_body_data_marker', b''),
        MelRaceParts({
            0: u'maleUpperBody',
            1: u'maleLeftHand',
            2: u'maleRightHand',
            3: u'maleUpperBodyTexture',
        }, group_loaders=lambda _indx: (
            MelIcons(),
            MelModel(),
        )),
        MelBase(b'FNAM', u'female_body_data_marker', b''),
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
        MelFidList(b'HNAM','hairs'),
        MelFidList(b'ENAM','eyes'),
        MelBase(b'MNAM', 'male_facegen_marker', b''),
        MelRaceFaceGen('maleFaceGen'),
        MelBase(b'FNAM', 'female_facegen_marker', b''),
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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRads(MelRecord):
    """Radiation Stage."""
    rec_sig = b'RADS'
    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', [u'2I'],'trigerThreshold',(FID,'actorEffect')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRefr(MelRecord):
    """Placed Object."""
    rec_sig = b'REFR'

    _lockFlags = Flags(0, Flags.getNames(None, None, 'leveledLock'))
    _destinationFlags = Flags(0, Flags.getNames('noAlarm'))

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
        MelSorted(MelFids(b'XLTW', 'litWaters')),
        MelLinkedDecals(),
        MelFid(b'XLKR','linkedReference'),
        MelOptStruct(b'XCLP', [u'8B'],'linkStartColorRed','linkStartColorGreen','linkStartColorBlue','linkColorUnused1',
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue','linkColorUnused2'),
        MelActivateParents(),
        fnv_only(MelString(b'XATO', 'activationPrompt')),
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
            MelPartialCounter(MelStruct(
                b'XRMR', [u'H', u'2s'], 'linked_rooms_count', 'unknown1'),
                counter='linked_rooms_count', counts='linked_rooms'),
            MelSorted(MelFids(b'XLRM', 'linked_rooms')),
        ),
        MelOptStruct(b'XOCP', [u'9f'],'occlusionPlaneWidth','occlusionPlaneHeight','occlusionPlanePosX','occlusionPlanePosY','occlusionPlanePosZ',
                     'occlusionPlaneRot1','occlusionPlaneRot2','occlusionPlaneRot3','occlusionPlaneRot4'),
        MelOptStruct(b'XORD', [u'4I'],(FID,'linkedOcclusionPlane0'),(FID,'linkedOcclusionPlane1'),(FID,'linkedOcclusionPlane2'),(FID,'linkedOcclusionPlane3')),
        MelXlod(),
        MelRefScale(),
        MelRef3D(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRegn(MelRecord):
    """Region."""
    rec_sig = b'REGN'

    obflags = Flags(0, Flags.getNames(
        'conform',
        'paintVertices',
        'sizeVariance',
        'deltaX',
        'deltaY',
        'deltaZ',
        'Tree',
        'hugeRock',
    ))
    sdflags = Flags(0, Flags.getNames(
        'pleasant',
        'cloudy',
        'rainy',
        'snowy',
    ))
    rdatFlags = Flags(0, Flags.getNames(
        'Override',
    ))

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
                7, MelFids(b'RDSB', 'battleMediaSets'))),
            MelRegnEntrySubrecord(7, MelSorted(MelArray('sounds',
                MelStruct(b'RDSD', [u'3I'], (FID, 'sound'), (sdflags, 'flags'),
                          'chance'),
            ), sort_by_attrs='sound')),
            MelRegnEntrySubrecord(3, MelSorted(MelArray('weatherTypes',
                MelStruct(b'RDWT', [u'3I'], (FID, u'weather'), u'chance',
                          (FID, u'global')),
            ), sort_by_attrs='weather')),
            fnv_only(MelRegnEntrySubrecord(
                8, MelFidList(b'RDID', 'imposters'))),
        ), sort_by_attrs='entryType'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRgdl(MelRecord):
    """Ragdoll."""
    rec_sig = b'RGDL'

    _flags = Flags(0, Flags.getNames('disableOnMove'))

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
    __slots__ = melSet.getSlotsUsed()

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreScpt(MelRecord):
    """Script."""
    rec_sig = b'SCPT'

    melSet = MelSet(
        MelEdid(),
        MelEmbeddedScript(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSoun(MelRecord):
    """Sound."""
    rec_sig = b'SOUN'
    _has_duplicate_attrs = True # SNDX, ANAM, GNAM and HNAM upgrade to SNDD

    _flags = Flags(0, Flags.getNames(
        (0, 'randomFrequencyShift'),
        (1, 'playAtRandom'),
        (2, 'environmentIgnored'),
        (3, 'randomLocation'),
        (4, 'loop'),
        (5, 'menuSound'),
        (6, 'twoD'),
        (7, 'three60LFE'),
        (8, 'dialogueSound'),
        (9, 'envelopeFast'),
        (10, 'envelopeSlow'),
        (11, 'twoDRadius'),
        (12, 'muteWhenSubmerged'),
        fnv_only((13, 'startatRandomPosition')),
    ))

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSpel(MelRecord):
    """Actor Effect"""
    rec_sig = b'SPEL'

    class SpellFlags(Flags):
        """For SpellFlags, immuneToSilence activates bits 1 AND 3."""
        def __setitem__(self,index,value):
            setter = Flags.__setitem__
            setter(self,index,value)
            if index == 1:
                setter(self,3,value)

    _SpellFlags = SpellFlags(0, Flags.getNames('noAutoCalc','immuneToSilence',
        'startSpell', None, 'ignoreLOS', 'scriptEffectAlwaysApplies',
        'disallowAbsorbReflect', 'touchExplodesWOTarget'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelStruct(b'SPIT', [u'3I', u'B', u'3s'], 'spellType', 'cost', 'level',
                  (_SpellFlags, u'flags'), 'unused1'),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreStat(MelRecord):
    """Static."""
    rec_sig = b'STAT'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        fnv_only(MelSInt8(b'BRUS', 'passthroughSound', -1)),
        fnv_only(MelFid(b'RNAM', 'soundRandomLooping')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreTact(MelRecord):
    """Talking Activator."""
    rec_sig = b'TACT'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelDestructible(),
        MelFid(b'SNAM','sound'),
        MelFid(b'VNAM','voiceType'),
        fnv_only(MelFid(b'INAM', 'radioTemplate')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreTerm(MelRecord):
    """Terminal."""
    rec_sig = b'TERM'

    _flags = Flags(0, Flags.getNames('leveled','unlocked','alternateColors','hideWellcomeTextWhenDisplayingImage'))
    _menuFlags = Flags(0, Flags.getNames('addNote','forceRedraw'))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelDestructible(),
        MelDescription(),
        MelFid(b'SNAM','soundLooping'),
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
            MelConditions(),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreTxst(MelRecord):
    """Texture Set."""
    rec_sig = b'TXST'

    TxstTypeFlags = Flags(0, Flags.getNames(
        (0, 'noSpecularMap'),
    ))
    DecalDataFlags = Flags(0, Flags.getNames(
            (0, 'parallax'),
            (0, 'alphaBlending'),
            (0, 'alphaTesting'),
            (0, 'noSubtextures'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelString(b'TX00','baseImage'),
        MelString(b'TX01','normalMap'),
        MelString(b'TX02','environmentMapMask'),
        MelString(b'TX03','growMap'),
        MelString(b'TX04','parallaxMap'),
        MelString(b'TX05','environmentMap'),
        MelDecalData(),
        MelUInt16Flags(b'DNAM', u'flags', TxstTypeFlags),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreVtyp(MelRecord):
    """Voice Type."""
    rec_sig = b'VTYP'

    _flags = Flags(0, Flags.getNames('allowDefaultDialog','female'))

    melSet = MelSet(
        MelEdid(),
        MelUInt8Flags(b'DNAM', u'flags', _flags),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWatr(MelRecord):
    """Water."""
    rec_sig = b'WATR'
    _has_duplicate_attrs = True # DATA is an older version of DNAM + DATA

    _flags = Flags(0, Flags.getNames('causesDmg','reflective'))

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
            return super(MreWatr.MelWatrDnam, self)._pre_process_unpacked(
                unpacked_val)

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
        MelFid(b'SNAM','sound',),
        MelFid(b'XNAM','effect'),
        MelWatrData(b'DATA', _fmts + [u'32f', u'H'], *(_els + ['damage'])),
        MelWatrDnam(b'DNAM', _fmts + [u'35f'], *(
                _els + ['noiseLayer1Amp', 'noiseLayer2Amp', 'noiseLayer3Amp']),
                    old_versions={'10f3Bs3Bs3BsI32f'}),
        MelFidList(b'GNAM','relatedWaters'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWeap(MelRecord):
    """Weapon."""
    rec_sig = b'WEAP'

    _flags = Flags(0, Flags.getNames('notNormalWeapon'))
    _dflags1 = Flags(0, Flags.getNames(
        'ignoresNormalWeaponResistance',
        'isAutomatic',
        'hasScope',
        'cantDrop',
        'hideBackpack',
        'embeddedWeapon',
        'dontUse1stPersonISAnimations',
        'nonPlayable',
    ))
    _dflags2 = Flags(0, Flags.getNames(
        (0, 'playerOnly'),
        (1, 'npcsUseAmmo'),
        (2, 'noJamAfterReload'),
        (3, 'overrideActionPoint'),
        (4, 'minorCrime'),
        (5, 'rangeFixed'),
        (6, 'notUseInNormalCombat'),
        (7, 'overrideDamageToWeaponMult'),
        (8, 'dontUse3rdPersonISAnimations'),
        (9, 'shortBurst'),
        (10, 'RumbleAlternate'),
        (11, 'longBurst'),
        fnv_only((12, 'scopeHasNightVision')),
        fnv_only((13, 'scopeFromMod')),
    ))
    _cflags = Flags(0, Flags.getNames('onDeath'))

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
        MelEquipmentType(),
        MelFid(b'BIPL','bipedModelList'),
        MelPickupSound(),
        MelDropSound(),
        MelModel(u'shellCasingModel', 2),
        MelModel(u'scopeModel', 3, with_facegen_flags=False),
        MelFid(b'EFSD','scopeEffect'),
        MelModel(u'worldModel', 4),
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
        MelFid(b'INAM','impactDataset'),
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
            fo3_version=MelFid(b'SNAM', 'soundGunShot3D'),
            fnv_version=MelFids(b'SNAM', 'soundGunShot3D'),
        ),
        MelFid(b'XNAM','soundGunShot2D'),
        MelFid(b'NAM7','soundGunShot3DLooping'),
        MelFid(b'TNAM','soundMeleeSwingGunNoAmmo'),
        MelFid(b'NAM6','soundBlock'),
        MelFid(b'UNAM','idleSound',),
        MelFid(b'NAM9','equipSound',),
        MelFid(b'NAM8','unequipSound',),
        fnv_only(MelFids(b'WMS1', 'soundMod1Shoot3Ds')),
        fnv_only(MelFid(b'WMS2', 'soundMod1Shoot2D')),
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
        MelOptStruct(b'CRDT', [u'H', u'2s', u'f', u'B', u'3s', u'I'],'criticalDamage','weapCrdt1',
                     'criticalMultiplier',(_cflags, u'criticalFlags'),
                     'weapCrdt2',(FID, u'criticalEffect')),
        fnv_only(MelTruncatedStruct(
            b'VATS', ['I', '3f', '2B', '2s'], (FID, 'vatsEffect'),
            'vatsSkill', 'vatsDamMult', 'vatsAp', 'vatsSilent',
            'vats_mod_required', 'weapVats1', old_versions={'I3f'},
            is_optional=True)),
        MelBase(b'VNAM','soundLevel'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWrld(MelRecord):
    """Worldspace."""
    rec_sig = b'WRLD'

    _flags = Flags(0, Flags.getNames('smallWorld','noFastTravel','oblivionWorldspace',None,
        'noLODWater','noLODNoise','noAllowNPCFallDamage'))
    pnamFlags = Flags(0, Flags.getNames(
        (0, u'useLandData'),
        (1, u'useLODData'),
        (2, u'useMapData'),
        (3, u'useWaterData'),
        (4, u'useClimateData'),
        (5, u'useImageSpaceData'),
        (7, u'needsWaterAdjustment'),
    ), unknown_is_unused=True)

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelFid(b'XEZN','encounterZone'),
        MelFid(b'WNAM','parent'),
        MelOptStruct(b'PNAM', [u'B', u'B'],(pnamFlags, u'parentFlags'),('unknownff',0xff)),
        MelFid(b'CNAM','climate'),
        MelFid(b'NAM2','water'),
        MelFid(b'NAM3','waterType'),
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
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWthr(MelRecord):
    """Weather."""
    rec_sig = b'WTHR'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'\x00IAD', 'sunriseImageSpaceModifier'),
        MelFid(b'\x01IAD', 'dayImageSpaceModifier'),
        MelFid(b'\x02IAD', 'sunsetImageSpaceModifier'),
        MelFid(b'\x03IAD', 'nightImageSpaceModifier'),
        MelString(b'DNAM','upperLayer'),
        MelString(b'CNAM','lowerLayer'),
        MelString(b'ANAM','layer2'),
        MelString(b'BNAM','layer3'),
        MelModel(),
        MelBase(b'LNAM','unknown1'),
        MelStruct(b'ONAM', [u'4B'],'cloudSpeed0','cloudSpeed1','cloudSpeed3','cloudSpeed4'),
        MelArray('cloudColors',
            MelWthrColors(b'PNAM'),
        ),
        MelArray('daytimeColors',
            MelWthrColors(b'NAM0'),
        ),
        MelStruct(b'FNAM', [u'6f'],'fogDayNear','fogDayFar','fogNightNear','fogNightFar','fogDayPower','fogNightPower'),
        MelBase(b'INAM', 'unused1', null1 * 304),
        MelStruct(b'DATA', [u'15B'],
            'windSpeed','lowerCloudSpeed','upperCloudSpeed','transDelta',
            'sunGlare','sunDamage','rainFadeIn','rainFadeOut','boltFadeIn',
            'boltFadeOut','boltFrequency','weatherType','boltRed','boltBlue','boltGreen'),
        MelGroups('sounds',
            MelStruct(b'SNAM', [u'2I'], (FID, 'sound'), 'type'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()
