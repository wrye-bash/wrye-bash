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

from ... import brec
from ...bolt import Flags, structs_cache
from ...brec import MelRecord, MelGroups, MelStruct, FID, MelGroup, \
    MelString, MelSet, MelFid, MelOptStruct, MelFids, MreHeaderBase, \
    MelBase, MelFidList, MreGmstBase, MelStrings, MelMODS, \
    MelReferences, MelColorInterpolator, MelValueInterpolator, \
    MelUnion, AttrValDecider, MelRegnEntrySubrecord, SizeDecider, MelFloat, \
    MelSInt8, MelSInt16, MelSInt32, MelUInt8, MelUInt16, MelUInt32, \
    MelOptFid, MelOptFloat, MelOptSInt16, MelOptSInt32, MelOptUInt8, \
    MelOptUInt16, MelOptUInt32, MelPartialCounter, MelRaceParts, \
    MelRaceVoices, MelBounds, null1, null2, null3, null4, MelScriptVars, \
    MelSequential, MelTruncatedStruct, PartialLoadDecider, MelReadOnly, \
    MelSkipInterior, MelIcons, MelIcons2, MelIcon, MelIco2, MelEdid, MelFull, \
    MelArray, MelWthrColors, MreLeveledListBase, MreActorBase, MreWithItems, \
    MelCtdaFo3, MelRef3D, MelXlod, MelNull, MelWorldBounds, MelEnableParent, \
    MelRefScale, MelMapMarker, MelActionFlags, MelEnchantment, MelScript, \
    MelDecalData, MelDescription, MelLists, MelPickupSound, MelDropSound, \
    MelActivateParents, BipedFlags, MelSpells, MelUInt8Flags, MelUInt16Flags, \
    MelUInt32Flags, MelOptUInt32Flags, MelOptUInt8Flags, MelOwnership, \
    MelDebrData
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
                    MelOptUInt8Flags(types[4], u'facegen_model_flags',
                                     _MelModel._facegen_model_flags)]
            super(_MelModel, self).__init__(attr, *model_elements)

    brec.MelModel = _MelModel
from ...brec import MelModel

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
        (2, u'hasBackpack'), # The first two are FNV-only, but will just be
        (3, u'medium'),      # ignored on FO3, so no problem
        (5, u'powerArmor'),
        (6, u'notPlayable'),
        (7, u'heavyArmor'),
    ), unknown_is_unused=True)

    def __init__(self):
        super(MelBipedData, self).__init__(b'BMDT', u'IB3s',
            (self._biped_flags, u'biped_flags'),
            (self._general_flags, u'generalFlags'), u'biped_unused')

#------------------------------------------------------------------------------
class MelConditions(MelGroups):
    """A list of conditions."""
    def __init__(self):
        # Note that reference can be a fid - handled in MelCtdaFo3.mapFids
        super(MelConditions, self).__init__(u'conditions',
            MelCtdaFo3(suffix_fmt=u'2I',
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
            MelStruct(b'DEST', u'i2B2s', u'health', u'count',
                (MelDestructible.MelDestVatsFlags, u'flagsDest'), u'unused'),
            MelGroups(u'stages',
                MelStruct(b'DSTD', u'4Bi2Ii', u'health', u'index',
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
            MelStruct(b'EFIT', u'4Ii', u'magnitude', u'area', u'duration',
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
            MelStruct(b'SCHR', u'4s3I2H', (u'unused1', null4), u'num_refs',
                      u'compiled_size', u'last_index', u'script_type',
                      (self._script_header_flags, u'schr_flags', 0)),
            MelBase(b'SCDA', u'compiled_script'),
            MelString(b'SCTX', u'script_source'),
            MelScriptVars(),
            MelReferences(),
        )

#------------------------------------------------------------------------------
class MelEquipmentType(MelSInt32):
    """Handles the common ETYP subrecord."""
    def __init__(self):
        super(MelEquipmentType, self).__init__(b'ETYP', u'equipment_type', -1)

#------------------------------------------------------------------------------
class MelItems(MelGroups):
    """Wraps MelGroups for the common task of defining a list of items."""
    def __init__(self):
        super(MelItems, self).__init__(u'items',
            MelStruct(b'CNTO', u'Ii', (FID, u'item'), (u'count', 1)),
            MelOptStruct(b'COED', u'2If', (FID, u'owner'), (FID, u'glob'),
                         (u'condition', 1.0)),
        )

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
        MelGroups(u'entries',
            MelLevListLvlo(b'LVLO', u'h2sIh2s', u'level', (u'unused1', null2),
                           (FID, u'listId'), (u'count', 1),
                           (u'unused2', null2), old_versions={u'iI'}),
            MelOptStruct(b'COED', u'2If', (FID, u'owner'), (FID, u'glob'),
                         (u'condition', 1.0)),
        ),
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
# Fallout3 Records ------------------------------------------------------------
#------------------------------------------------------------------------------
class MreTes4(MreHeaderBase):
    """TES4 Record.  File header."""
    rec_sig = b'TES4'

    melSet = MelSet(
        MelStruct(b'HEDR', 'f2I', ('version', 0.94), 'numRecords',
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
        MelOptFid(b'XEZN', u'encounterZone'),
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
        MelOptFid(b'XMRC', u'merchantContainer',),
        MelSInt32(b'XCNT', 'count'),
        MelFloat(b'XRDS', 'radius'),
        MelFloat(b'XHLP', 'health'),
        MelGroups('linkedDecals',
            MelStruct(b'XDCR', '2I', (FID, 'reference'), 'unknown'),
        ),
        MelOptFid(b'XLKR', u'linkedReference'),
        MelOptStruct(b'XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelActivateParents(),
        MelEnableParent(),
        MelOptFid(b'XEMI', u'emittance'),
        MelOptFid(b'XMBR', u'multiboundReference'),
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
        MelOptFid(b'XEZN', u'encounterZone'),
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
        MelOptFid(b'XMRC', u'merchantContainer'),
        MelSInt32(b'XCNT', 'count'),
        MelFloat(b'XRDS', 'radius'),
        MelFloat(b'XHLP', 'health'),
        MelGroups('linkedDecals',
            MelStruct(b'XDCR', '2I', (FID, 'reference'), 'unknown'),
        ),
        MelOptFid(b'XLKR', u'linkedReference'),
        MelOptStruct(b'XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelActivateParents(),
        MelEnableParent(),
        MelOptFid(b'XEMI', u'emittance'),
        MelOptFid(b'XMBR', u'multiboundReference'),
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
        MelOptFid(b'SNAM', u'soundLooping'),
        MelOptFid(b'VNAM', u'soundActivation'),
        MelOptFid(b'RNAM', u'radioStation'),
        MelOptFid(b'WNAM', u'waterType'),
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
        MelOptSInt32(b'DATA', 'nodeIndex'),
        MelOptFid(b'SNAM', u'ambientSound'),
        MelStruct(b'DNAM','H2s','mastPartSysCap','unknown',),
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
        MelStruct(b'ENIT', u'iB3sIfI', u'value', (_flags, u'flags'),
                  (u'unused1', null3), (FID, u'withdrawalEffect'),
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
        MelDestructible(),
        MelPickupSound(),
        MelDropSound(),
        MelStruct(b'DATA','fB3siB','speed',(_flags,'flags',0),('ammoData1',null3),
                  'value','clipRounds'),
        MelString(b'ONAM','shortName'),
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
        MelStruct(b'DATA','IIf','value','health','weight'),
        MelStruct(b'DNAM','hH','ar',(_dnamFlags,'dnamFlags',0),),
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
        MelStruct(b'DATA','=2if','value','health','weight'),
        MelStruct(b'DNAM','=hH','ar',(_dnamFlags,'dnamFlags',0),),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAspc(MelRecord):
    """Acoustic Space."""
    rec_sig = b'ASPC'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFid(b'SNAM','soundLooping'),
        MelFid(b'RDAT','useSoundFromRegion'),
        MelUInt32(b'ANAM', 'environmentType'),
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
        MelStruct(b'DATA', '=BbIf',(_flags,'flags',0),('teaches',-1),'value','weight'),
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
            MelStruct(b'BPND', u'f3Bb2BH2I2fi2I7f2I2B2sf', u'damageMult',
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
                u'explodableDecalCount', (u'unused', null2),
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
        MelStruct(b'DATA','4I6f','action','location','target',
                  (CamsFlagsFlags,'flags',0),'timeMultPlayer',
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
        MelSkipInterior(MelTruncatedStruct(b'XCLC', u'2iI', (u'posX', None),
            (u'posY', None), (_land_flags, u'land_flags'), is_optional=True,
            old_versions={u'2i'})),
        MelTruncatedStruct(b'XCLL', '=3Bs3Bs3Bs2f2i3f', 'ambientRed',
                           'ambientGreen', 'ambientBlue', ('unused1', null1),
                           'directionalRed', 'directionalGreen',
                           'directionalBlue', ('unused2', null1), 'fogRed',
                           'fogGreen', 'fogBlue', ('unused3', null1),
                           'fogNear', 'fogFar', 'directionalXY',
                           'directionalZ', 'directionalFade', 'fogClip',
                           'fogPower', is_optional=True,
                           old_versions={'3Bs3Bs3Bs2f2i2f'}),
        MelBase(b'IMPF','footstepMaterials'), #--todo rewrite specific class.
        MelFid(b'LTMP','lightTemplate'),
        MelOptUInt32Flags(b'LNAM', u'lightInheritFlags', inheritFlags),
        # GECK default for water is -2147483648, but by setting default here to
        # -2147483649, we force the Bashed Patch to retain the value of the
        # last mod.
        MelOptFloat(b'XCLW', u'waterHeight', -2147483649),
        MelString(b'XNAM','waterNoiseTexture'),
        MelFidList(b'XCLR','regions'),
        MelFid(b'XCIM','imageSpace'),
        MelOptUInt8(b'XCET', 'xcet_p'),
        MelFid(b'XEZN','encounterZone'),
        MelFid(b'XCCM','climate'),
        MelFid(b'XCWT','water'),
        MelOwnership(),
        MelFid(b'XCAS','acousticSpace'),
        MelOptUInt8(b'XCMT', 'xcmt_p'),
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
        (17,'repair'),))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelIcon(),
        MelStruct(b'DATA','4i2IbB2s','tagSkill1','tagSkill2','tagSkill3',
            'tagSkill4',(_flags,'flags',0),(aiService,'services',0),
            ('trainSkill',-1),('trainLevel',0),('clasData1',null2)),
        MelStruct(b'ATTR', '7B', 'strength', 'perception', 'endurance',
                  'charisma', 'intelligence', 'agility', 'luck'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClmt(MelRecord):
    """Climate."""
    rec_sig = b'CLMT'

    melSet = MelSet(
        MelEdid(),
        MelArray('weather_types',
            MelStruct(b'WLST', 'IiI', (FID,'weather'), 'chance',
                      (FID, 'global')),
        ),
        MelString(b'FNAM','sunPath'),
        MelString(b'GNAM','glarePath'),
        MelModel(),
        MelStruct(b'TNAM','6B','riseBegin','riseEnd','setBegin','setEnd',
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
        MelStruct(b'DATA','if','value','weight'),
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
        MelStruct(b'DATA','=Bf',(_flags,'flags',0),'weight'),
        MelFid(b'SNAM','soundOpen'),
        MelFid(b'QNAM','soundClose'),
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
        (31,'invulnerable'),))
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
        (17,'repair'),))
    aggroflags = Flags(0, Flags.getNames('aggroRadiusBehavior',))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelSpells(),
        MelEnchantment(),
        MelUInt16(b'EAMT', 'eamt'),
        MelStrings(b'NIFZ','bodyParts'),
        MelBase(b'NIFT','nift_p'), # Texture File Hashes
        MelStruct(b'ACBS','=I2Hh3HfhH',(_flags,'flags',0),'fatigue',
            'barterGold',('level',1),'calcMin','calcMax','speedMultiplier',
            'karma', 'dispositionBase',
            (MreActor.TemplateFlags, 'templateFlags', 0)),
        MelGroups(u'factions',
            MelStruct(b'SNAM', u'IB3s', (FID, u'faction'), u'rank',
                      (u'unused1', b'IFZ')),
        ),
        MelFid(b'INAM','deathItem'),
        MelFid(b'VTCK','voice'),
        MelFid(b'TPLT','template'),
        MelDestructible(),
        MelScript(),
        MelItems(),
        MelStruct(b'AIDT','=5B3sIbBbBi', ('aggression', 0), ('confidence', 2),
                  ('energyLevel', 50), ('responsibility', 50), ('mood', 0),
                  ('unused_aidt', null3), (aiService, 'services', 0),
                  ('trainSkill', -1), 'trainLevel', ('assistance', 0),
                  (aggroflags, 'aggroRadiusBehavior', 0), 'aggroRadius'),
        MelFids(b'PKID','aiPackages'),
        MelStrings(b'KFFZ','animations'),
        MelStruct(b'DATA','=4Bh2sh7B','creatureType','combatSkill','magicSkill',
            'stealthSkill','health',('unused2',null2),'damage','strength',
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
        MelGroups('sounds',
            MelUInt32(b'CSDT', 'type'),
            MelFid(b'CSDI','sound'),
            MelUInt8(b'CSDC', 'chance'),
        ),
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
        MelOptStruct(b'CSTD', '2B2s8f2B2s3fB3s2f5B3s2fH2s2B2sf','dodgeChance',
                    'lrChance',('unused1',null2),'lrTimerMin','lrTimerMax',
                    'forTimerMin','forTimerMax','backTimerMin','backTimerMax',
                    'idleTimerMin','idleTimerMax','blkChance','atkChance',
                    ('unused2',null2),'atkBRecoil','atkBunc','atkBh2h',
                    'pAtkChance',('unused3',null3),'pAtkBRecoil','pAtkBUnc',
                    'pAtkNormal','pAtkFor','pAtkBack','pAtkL','pAtkR',
                    ('unused4',null3),'holdTimerMin','holdTimerMax',
                    (_flagsA,'flagsA'),('unused5',null2),'acroDodge',
                    ('rushChance',25),('unused6',null3),('rushMult',1.0),),
        MelOptStruct(b'CSAD', '21f', 'dodgeFMult', 'dodgeFBase', 'encSBase', 'encSMult',
                     'dodgeAtkMult', 'dodgeNAtkMult', 'dodgeBAtkMult', 'dodgeBNAtkMult',
                     'dodgeFAtkMult', 'dodgeFNAtkMult', 'blockMult', 'blockBase',
                     'blockAtkMult', 'blockNAtkMult', 'atkMult','atkBase', 'atkAtkMult',
                     'atkNAtkMult', 'atkBlockMult', 'pAtkFBase', 'pAtkFMult'),
        MelOptStruct(b'CSSD', '9f4sI5f', 'coverSearchRadius', 'takeCoverChance',
                     'waitTimerMin', 'waitTimerMax', 'waitToFireTimerMin',
                     'waitToFireTimerMax', 'fireTimerMin', 'fireTimerMax'
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
        MelFids(b'QSTI','quests'),
        MelFids(b'QSTR','rQuests'),
        MelFull(),
        MelFloat(b'PNAM', 'priority'),
        MelTruncatedStruct(b'DATA', '2B', 'dialType',
                           (_DialFlags, 'dialFlags', 0), old_versions={'B'}),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDobj(MelRecord):
    """Default Object Manager."""
    rec_sig = b'DOBJ'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA','21I',(FID,'stimpack'),(FID,'superStimpack'),(FID,'radX'),(FID,'radAway'),
            (FID,'morphine'),(FID,'perkParalysis'),(FID,'playerFaction'),(FID,'mysteriousStrangerNpc'),
            (FID,'mysteriousStrangerFaction'),(FID,'defaultMusic'),(FID,'battleMusic'),(FID,'deathMusic'),
            (FID,'successMusic'),(FID,'levelUpMusic'),(FID,'playerVoiceMale'),(FID,'playerVoiceMaleChild'),
            (FID,'playerVoiceFemale'),(FID,'playerVoiceFemaleChild'),(FID,'eatPackageDefaultFood'),
            (FID,'everyActorAbility'),(FID,'drugWearsOffImageSpace'),),
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
        MelStruct(b'DATA', u'I2bBs', (FID, u'owner'), u'rank', u'minimumLevel',
                  (_flags, u'flags'), (u'unused1', null1)),
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
            u'B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I6f', (_flags, u'flags'),
            (u'unused1', null3), (u'memSBlend', 5), (u'memBlendOp', 1),
            (u'memZFunc', 3), u'fillRed', u'fillGreen', u'fillBlue',
            (u'unused2', null1), u'fillAIn', u'fillAFull', u'fillAOut',
            u'fillAPRatio', u'fillAAmp', u'fillAFreq', u'fillAnimSpdU',
            u'fillAnimSpdV', u'edgeOff', u'edgeRed', u'edgeGreen', u'edgeBlue',
            (u'unused3', null1), u'edgeAIn', u'edgeAFull', u'edgeAOut',
            u'edgeAPRatio', u'edgeAAmp', u'edgeAFreq', u'fillAFRatio',
            u'edgeAFRatio', (u'memDBlend', 6), (u'partSBlend', 5),
            (u'partBlendOp', 1), (u'partZFunc', 4), (u'partDBlend', 6),
            u'partBUp', u'partBFull', u'partBDown', (u'partBFRatio', 1.0),
            (u'partBPRatio', 1.0), (u'partLTime', 1.0), u'partLDelta',
            u'partNSpd', u'partNAcc', u'partVel1', u'partVel2', u'partVel3',
            u'partAcc1', u'partAcc2', u'partAcc3', (u'partKey1', 1.0),
            (u'partKey2', 1.0), u'partKey1Time', (u'partKey2Time', 1.0),
            (u'key1Red', 255), (u'key1Green', 255), (u'key1Blue', 255),
            (u'unused4', null1), (u'key2Red', 255), (u'key2Green', 255),
            (u'key2Blue', 255), (u'unused5', null1), (u'key3Red', 255),
            (u'key3Green', 255), (u'key3Blue', 255), (u'unused6', null1),
            (u'key1A', 1.0), (u'key2A', 1.0), (u'key3A', 1.0), u'key1Time',
            (u'key2Time', 0.5), (u'key3Time', 1.0), u'partNSpdDelta',
            u'partRot', u'partRotDelta', u'partRotSpeed', u'partRotSpeedDelta',
            (FID, u'addonModels'), u'holesStartTime', u'holesEndTime',
            u'holesStartVal', u'holesEndVal', u'edgeWidth',
            (u'edge_color_red', 255), (u'edge_color_green', 255),
            (u'edge_color_blue', 255), (u'unused7', null1),
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

    _flags = Flags(0, Flags.getNames('noAutoCalc',None,'hideEffect'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelStruct(b'ENIT','3IB3s','itemType','chargeAmount','enchantCost',
                  (_flags,'flags',0),('unused1',null3)),
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
        MelStruct(b'DATA', u'3f3If2I3fI', u'force', u'damage', u'radius',
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
        MelGroups(u'relations',
            MelStruct(b'XNAM', u'IiI', (FID, u'faction'), u'mod',
                      u'group_combat_reaction'),
        ),
        MelTruncatedStruct(b'DATA', u'2B2s',
                           (_general_flags, u'general_flags'),
                           (_general_flags_2, u'general_flags_2'),
                           (u'unused1', null2), old_versions={u'2B', u'B'}),
        MelOptFloat(b'CNAM', u'cnam_unused'), # leftover from Oblivion
        MelGroups(u'ranks',
            MelSInt32(b'RNAM', u'rank_level'),
            MelString(b'MNAM', u'male_title'),
            MelString(b'FNAM', u'female_title'),
            MelString(b'INAM', u'insignia_path')
        ),
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
        MelStruct(b'DATA','3BsH2sI4fB3s','density','minSlope',
                  'maxSlope',('unused1',null1),'waterDistance',('unused2',null2),
                  'waterOp','posRange','heightRange','colorRange',
                  'wavePeriod',(_flags,'flags'),('unused3',null3)),
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
        MelFids(b'HNAM','extraParts'),
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
        MelStruct(b'ANAM','II',(FID,'parent'),(FID,'prevId')),
        MelTruncatedStruct(b'DATA', '3BshBs', 'group', 'loopMin', 'loopMax',
                           ('unknown1', null1), 'delay', 'flags',
                           ('unknown2', null1), old_versions={'3Bsh'}),
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
            b'IDLC', 'B3s', 'animation_count', ('unused', null3),
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
        MelStruct(b'DNAM', 'If49I2f8I', (_ImadAnimatableFlags, 'aniFlags', 0),
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
                  (_ImadRadialBlurFlags, 'radialBlurFlags', 0),
                  'radialBlurCenterX', 'radialBlurCenterY', 'dofStrength',
                  'dofDistance', 'dofRange', (_ImadDofFlags, 'dofFlags', 0),
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

    melSet = MelSet(
        MelEdid(),
        MelUnion({
            152: MelStruct(
                b'DNAM', u'33f4s4s4s4sB3s', *(_dnam_common + [
                    (u'unused1', null4), (u'unused2', null4),
                    (u'unused3', null4), (u'unused4', null4),
                    (_dnam_flags, u'dnam_flags'), (u'unused5', null3),
                ])),
            148: MelStruct(
                b'DNAM', u'33f4s4s4s4s', *(_dnam_common + [
                    (u'unused1', null4), (u'unused2', null4),
                    (u'unused3', null4), (u'unused4', null4),
                ])),
            132: MelStruct(b'DNAM', u'33f', *_dnam_common),
        }, decider=SizeDecider()),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreInfo(MelRecord):
    """Dialog Response."""
    rec_sig = b'INFO'

    _flags = Flags(0,Flags.getNames(
        'goodbye','random','sayOnce','runImmediately','infoRefusal','randomEnd',
        'runForRumors','speechChallenge',))
    _flags2 = Flags(0,Flags.getNames(
        'sayOnceADay','alwaysDarken',))

    melSet = MelSet(
        MelTruncatedStruct(b'DATA', '4B', 'dialType', 'nextSpeaker',
                           (_flags, 'flags'), (_flags2, 'flagsInfo'),
                           old_versions={'2B'}),
        MelFid(b'QSTI', u'info_quest'),
        MelFid(b'TPIC', u'info_topic'),
        MelFid(b'PNAM','prevInfo'),
        MelFids(b'NAME','addTopics'),
        MelGroups('responses',
            MelStruct(b'TRDT','Ii4sB3sIB3s','emotionType','emotionValue',('unused1',null4),'responseNum',('unused2',b'\xcd\xcd\xcd'),
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
        MelStruct(b'ENIT','iB3s','value',(_flags,'flags',0),('unused1',null3)),
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
        MelStruct(b'DATA','fIffII','effectDuration','effectOrientation',
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
            b'DATA', '12I', (FID, 'stone', 0), (FID, 'dirt', 0),
            (FID, 'grass', 0), (FID, 'glass', 0), (FID, 'metal', 0),
            (FID, 'wood', 0), (FID, 'organic', 0), (FID, 'cloth', 0),
            (FID, 'water', 0), (FID, 'hollowMetal', 0), (FID, 'organicBug', 0),
            (FID, 'organicGlow', 0), old_versions={'10I', '9I'}),
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
        MelStruct(b'DATA','if','value','weight'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLgtm(MelRecord):
    """Lighting Template."""
    rec_sig = b'LGTM'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA','3Bs3Bs3Bs2f2i3f',
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
        MelIcon(),
        MelStruct(b'DATA','iI3BsI2fIf','duration','radius','red','green','blue',
                  ('unused1',null1),(_flags,'flags',0),'falloff','fov','value',
                  'weight'),
        # None here is on purpose! See AssortedTweak_LightFadeValueFix
        MelOptFloat(b'FNAM', u'fade', None),
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
        MelGroups('locations',
            MelStruct(b'LNAM', 'I8s', (FID, 'cell'),
                      ('unused1', null4 + null4)),
        ),
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
        MelOptStruct(b'HNAM','3B','materialType','friction','restitution'),
        MelOptUInt8(b'SNAM', 'specular'),
        MelFids(b'GNAM', 'grass'),
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
        (27, u'noHitEffect'),))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(u'text'),
        MelIcon(),
        MelModel(),
        MelPartialCounter(MelStruct(
            b'DATA', u'IfI2iH2sIf6I2fIi', (_flags, u'flags'), u'base_cost',
            (FID, u'associated_item'), u'school', u'resist_value',
            u'counter_effect_count', (u'unused1', null2),
            (FID, u'light'), u'projectileSpeed', (FID, u'effectShader'),
            (FID, u'enchantEffect'), (FID, u'castingSound'),
            (FID, u'boltSound'), (FID, u'hitSound'), (FID, u'areaSound'),
            u'cef_enchantment', u'cef_barter', u'effect_archetype',
            u'actorValue'),
            counter=u'counter_effect_count', counts=u'counter_effects'),
        MelGroups(u'counter_effects',
            MelOptFid(b'ESCE', u'counter_effect_code'),
        ),
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
        MelStruct(b'DATA','if','value','weight'),
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
        MelStruct(b'DATA','I5I',(FID,'cell'),'vertexCount','triangleCount','enternalConnectionsCount','nvcaCount','doorsCount'),
        MelArray('vertices',
            MelStruct(b'NVVX', '3f', 'vertexX', 'vertexY', 'vertexZ'),
        ),
        MelArray('triangles',
            MelStruct(b'NVTR', '6hI', 'vertex0', 'vertex1', 'vertex2',
                      'triangle0', 'triangle1', 'triangle2', 'flags'),
        ),
        MelOptSInt16(b'NVCA', 'nvca_p'),
        MelArray('doors',
            MelStruct(b'NVDP', 'IH2s', (FID, 'doorReference'), 'door_triangle',
                      'doorUnknown'),
        ),
        MelBase(b'NVGD','nvgd_p'),
        MelArray('externalConnections',
            MelStruct(b'NVEX', '=4sIH', 'nvexUnknown', (FID, 'navigationMesh'),
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
        MelFidList(b'ONAM','quests'),
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

    def __init__(self, struct_format):
        super(_MelNpcData, self).__init__(b'DATA', struct_format, u'health',
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
        (30,'noRotatingHeadTrack'),))
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
        (17,'repair'),))
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
        MelStruct(b'ACBS','=I2Hh3Hf2H',
            (_flags,'flags',0),'fatigue','barterGold',
            ('level',1),'calcMin','calcMax','speedMultiplier','karma',
            'dispositionBase', (MreActor.TemplateFlags, 'templateFlags', 0)),
        MelGroups('factions',
            MelStruct(b'SNAM', u'IB3s', (FID, u'faction'), u'rank',
                      (u'unused1', b'ODB')),
        ),
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
        MelStruct(b'AIDT','=5B3sIbBbBi', ('aggression', 0), ('confidence',2),
                  ('energyLevel', 50),('responsibility', 50), ('mood', 0),
                  ('unused_aidt', null3),(aiService, 'services', 0),
                  ('trainSkill', -1), 'trainLevel', ('assistance', 0),
                  (aggroflags, 'aggroRadiusBehavior', 0), 'aggroRadius'),
        MelFids(b'PKID','aiPackages'),
        MelStrings(b'KFFZ','animations'),
        MelFid(b'CNAM','iclass'),
        MelUnion({
            11: _MelNpcData(u'=I7B'),
            25: _MelNpcData(u'=I21B')
        }, decider=SizeDecider()),
        MelFids(b'PNAM','headParts'),
        MelNpcDnam(b'DNAM', u'=28B', (u'skillValues', [0] * 14),
                   (u'skillOffsets', [0] * 14)),
        MelFid(b'HNAM','hair'),
        # None here is on purpose, for race patcher
        MelOptFloat(b'LNAM', u'hairLength', None),
        MelFid(b'ENAM','eye'), ####fid Array
        MelStruct(b'HCLR','3Bs','hairRed','hairBlue','hairGreen',('unused3',null1)),
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
    # The subrecord type used for the marker
    _attr_lookup = {
        u'on_begin': b'POBA',
        u'on_change': b'POCA',
        u'on_end': b'POEA',
    }
    _variableFlags = Flags(0, Flags.getNames(u'isLongOrShort'))

    def __init__(self, attr):
        super(MelIdleHandler, self).__init__(attr,
            MelBase(self._attr_lookup[attr], attr + u'_marker'),
            MelFid(b'INAM', u'idle_anim'),
            MelEmbeddedScript(),
            MelFid(b'TNAM', u'topic'),
        )

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

    melSet = MelSet(
        MelEdid(),
        MelTruncatedStruct(b'PKDT', u'I2HI', (_flags, u'flags'), u'aiType',
            (_fallout_behavior_flags, u'falloutBehaviorFlags'),
            u'typeSpecificFlags', old_versions={u'I2H'}),
        MelUnion({
            (0, 1, 4): MelOptStruct(b'PLDT', u'iIi', u'locType',
                (FID, u'locId'), u'locRadius'),
            (2, 3, 6, 7): MelOptStruct(b'PLDT', u'i4si', u'locType', u'locId',
                u'locRadius'),
            5: MelOptStruct(b'PLDT', u'iIi', u'locType', u'locId',
                u'locRadius'),
        }, decider=PartialLoadDecider(
            loader=MelSInt32(b'PLDT', u'locType'),
            decider=AttrValDecider(u'locType'),
        )),
        MelUnion({
            (0, 1, 4): MelOptStruct(b'PLD2', u'iIi', u'locType2',
                (FID, u'locId2'), u'locRadius2'),
            (2, 3, 6, 7): MelOptStruct(b'PLD2', u'i4si', u'locType2',
                u'locId2', u'locRadius2'),
            5: MelOptStruct(b'PLD2', u'iIi', u'locType2', u'locId2',
                u'locRadius2'),
        }, decider=PartialLoadDecider(
            loader=MelSInt32(b'PLD2', u'locType2'),
            decider=AttrValDecider(u'locType2'),
        )),
        MelStruct(b'PSDT','2bBbi','month','day','date','time','duration'),
        MelUnion({
            (0, 1): MelTruncatedStruct(b'PTDT', u'iIif', u'targetType',
                (FID, u'targetId'), u'targetCount', u'targetUnknown1',
                is_optional=True, old_versions={u'iIi'}),
            2: MelTruncatedStruct(b'PTDT', u'iIif', u'targetType', u'targetId',
                u'targetCount', u'targetUnknown1', is_optional=True,
                old_versions={u'iIi'}),
            3: MelTruncatedStruct(b'PTDT', u'i4sif', u'targetType',
                u'targetId', u'targetCount', u'targetUnknown1',
                is_optional=True, old_versions={u'i4si'}),
        }, decider=PartialLoadDecider(
            loader=MelSInt32(b'PTDT', u'targetType'),
            decider=AttrValDecider(u'targetType'),
        )),
        MelConditions(),
        MelGroup('idleAnimations',
            MelUInt8(b'IDLF', 'animationFlags'),
            MelPartialCounter(MelStruct(b'IDLC', 'B3s', 'animation_count',
                                        'unused'),
                              counter='animation_count', counts='animations'),
            MelFloat(b'IDLT', 'idleTimerSetting'),
            MelFidList(b'IDLA','animations'),
            MelBase(b'IDLB','idlb_p'),
        ),
        MelBase(b'PKED','eatMarker'),
        MelOptUInt32(b'PKE2', 'escortDistance'),
        MelFid(b'CNAM','combatStyle'),
        MelOptFloat(b'PKFD', 'followStartLocationTrigerRadius'),
        MelBase(b'PKPT','patrolFlags'), # byte or short
        MelOptStruct(b'PKW3','IBB3Hff4s','weaponFlags','fireRate','fireCount','numBursts',
                     'shootPerVolleysMin','shootPerVolleysMax','pauseBetweenVolleysMin','pauseBetweenVolleysMax','weaponUnknown'),
        MelUnion({
            (0, 1): MelTruncatedStruct(b'PTD2', u'iIif', u'targetType2',
                (FID, u'targetId2'), u'targetCount2', u'targetUnknown2',
                is_optional=True, old_versions={u'iIi'}),
            2: MelTruncatedStruct(b'PTD2', u'iIif', u'targetType2',
                u'targetId2', u'targetCount2', u'targetUnknown2',
                is_optional=True, old_versions={u'iIi'}),
            3: MelTruncatedStruct(b'PTD2', u'i4sif', u'targetType2',
                u'targetId2', u'targetCount2', u'targetUnknown2',
                is_optional=True, old_versions={u'i4si'}),
        }, decider=PartialLoadDecider(
            loader=MelSInt32(b'PTD2', u'targetType2'),
            decider=AttrValDecider(u'targetType2'),
        )),
        MelBase(b'PUID','useItemMarker'),
        MelBase(b'PKAM','ambushMarker'),
        MelTruncatedStruct(b'PKDD', 'f2I4sI4s', 'dialFov', 'dialTopic',
                           'dialFlags', 'dialUnknown1', 'dialType',
                           'dialUnknown2', is_optional=True,
                           old_versions={'f2I4sI', 'f2I4s', 'f2I'}),
        MelIdleHandler(u'on_begin'),
        MelIdleHandler(u'on_end'),
        MelIdleHandler(u'on_change'),
    ).with_distributor({
        b'POBA': {
            b'INAM|SCHR|SCDA|SCTX|SLSD|SCVR|SCRO|SCRV|TNAM': u'on_begin',
        },
        b'POEA': {
            b'INAM|SCHR|SCDA|SCTX|SLSD|SCVR|SCRO|SCRV|TNAM': u'on_begin',
        },
        b'POCA': {
            b'INAM|SCHR|SCDA|SCTX|SLSD|SCVR|SCRO|SCRV|TNAM': u'on_begin',
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
        MelTruncatedStruct(b'DATA', '5B', ('trait', 0), ('minLevel', 0),
                           ('ranks', 0), ('playable', 0), ('hidden', 0),
                           old_versions={'4B'}),
        MelGroups('effects',
            MelStruct(b'PRKE', '3B', 'type', 'rank', 'priority'),
            MelUnion({
                0: MelStruct(b'DATA', u'IB3s', (FID, u'quest'), u'quest_stage',
                    u'unused_data'),
                1: MelFid(b'DATA', u'ability'),
                2: MelStruct(b'DATA', u'3B', u'entry_point', u'function',
                    u'perk_conditions_tab_count'),
            }, decider=AttrValDecider(u'type')),
            MelGroups('effectConditions',
                MelSInt8(b'PRKC', 'runOn'),
                MelConditions(),
            ),
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
                    2: MelStruct(b'EPFD', u'If', u'param1', u'param2'),
                    # 2: MelUnion({
                    #     5: MelStruct(b'EPFD', u'If', u'param1', u'param2'),
                    # }, decider=AttrValDecider(u'../function',
                    #     assign_missing=-1),
                    #     fallback=MelStruct(b'EPFD', u'2f', u'param1',
                    #         u'param2')),
                    3: MelFid(b'EPFD', u'param1'),
                }, decider=AttrValDecider(u'function_parameter_type')),
                MelString(b'EPF2','buttonLabel'),
                MelUInt16Flags(b'EPF3', u'script_flags', _PerkScriptFlags),
                MelEmbeddedScript(),
            ),
            MelBase(b'PRKF','footer'),
        ),
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

    _watertypeFlags = Flags(0, Flags.getNames('reflection','refraction'))

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
        MelGroups('reflectedRefractedBy',
            MelStruct(b'XPWR','2I',(FID,'waterReference'),(_watertypeFlags,'waterFlags',0),),
        ),
        MelGroups('linkedDecals',
            MelStruct(b'XDCR', '2I', (FID, 'reference'), 'unknown'),
        ),
        MelFid(b'XLKR','linkedReference'),
        MelOptStruct(b'XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelActivateParents(),
        MelEnableParent(),
        MelOptFid(b'XEMI', u'emittance'),
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

    _watertypeFlags = Flags(0, Flags.getNames('reflection','refraction'))

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
        MelGroups('reflectedRefractedBy',
            MelStruct(b'XPWR','2I',(FID,'waterReference'),(_watertypeFlags,'waterFlags',0),),
        ),
        MelGroups('linkedDecals',
            MelStruct(b'XDCR', '2I', (FID, 'reference'), 'unknown'),
        ),
        MelFid(b'XLKR','linkedReference'),
        MelOptStruct(b'XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelActivateParents(),
        MelEnableParent(),
        MelOptFid(b'XEMI', u'emittance'),
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

    _flags = Flags(0,Flags.getNames(
        'hitscan',
        'explosive',
        'altTriger',
        'muzzleFlash',
        None,
        'canbeDisable',
        'canbePickedUp',
        'superSonic',
        'pinsLimbs',
        'passThroughSmallTransparent'
        ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelStruct(b'DATA','HHfffIIfffIIfffIII',(_flags,'flags'),'type',
                  ('gravity',0.00000),('speed',10000.00000),('range',10000.00000),
                  (FID,'light',0),(FID,'muzzleFlash',0),('tracerChance',0.00000),
                  ('explosionAltTrigerProximity',0.00000),('explosionAltTrigerTimer',0.00000),
                  (FID,'explosion',0),(FID,'sound',0),('muzzleFlashDuration',0.00000),
                  ('fadeDuration',0.00000),('impactForce',0.00000),
                  (FID,'soundCountDown',0),(FID,'soundDisable',0),
                  (FID,'defaultWeaponSource',0),),
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
        MelStruct(b'DNAM','2I',(_flags,'flags'),(FID,'water'))
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
        MelTruncatedStruct(b'DATA', '2B2sf', (_questFlags, 'questFlags', 0),
                           ('priority', 0), ('unused2', null2),
                           ('questDelay', 0.0), old_versions={'2B'}),
        MelConditions(),
        MelGroups('stages',
            MelSInt16(b'INDX', 'stage'),
            MelGroups('entries',
                MelUInt8Flags(b'QSDT', u'flags', stageFlags),
                MelConditions(),
                MelString(b'CNAM','text'),
                MelEmbeddedScript(),
                MelFid(b'NAM0', 'nextQuest'),
            ),
        ),
        MelGroups('objectives',
            MelSInt32(b'QOBJ', 'index'),
            MelString(b'NNAM','description'),
            MelGroups('targets',
                MelStruct(b'QSTA','IB3s',(FID,'targetId'),(targetFlags,'flags'),('unused1',null3)),
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
            MelStruct(b'SNAM', u'2s', (u'snam_p', null2)))

class MreRace(MelRecord):
    """Race."""
    rec_sig = b'RACE'

    _flags = Flags(0, Flags.getNames('playable', None, 'child'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(u'text'),
        MelGroups('relations',
            MelStruct(b'XNAM', 'I2i', (FID, 'faction'), 'mod',
                      'group_combat_reaction'),
        ),
        MelStruct(b'DATA','14b2s4fI','skill1','skill1Boost','skill2','skill2Boost',
                  'skill3','skill3Boost','skill4','skill4Boost','skill5','skill5Boost',
                  'skill6','skill6Boost','skill7','skill7Boost',('unused1',null2),
                  'maleHeight','femaleHeight','maleWeight','femaleWeight',(_flags,'flags',0)),
        MelFid(b'ONAM','Older'),
        MelFid(b'YNAM','Younger'),
        MelBase(b'NAM2','_nam2',b''),
        MelRaceVoices(b'VTCK', '2I', (FID, 'maleVoice'), (FID, 'femaleVoice')),
        MelOptStruct(b'DNAM','2I',(FID,'defaultHairMale',0),(FID,'defaultHairFemale',0)),
        # Int corresponding to GMST sHairColorNN
        MelStruct(b'CNAM','2B','defaultHairColorMale','defaultHairColorFemale'),
        MelOptFloat(b'PNAM', 'mainClamp'),
        MelOptFloat(b'UNAM', 'faceClamp'),
        MelStruct(b'ATTR','2B','maleBaseAttribute','femaleBaseAttribute'),
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
            MelModel()
        )),
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
        MelStruct(b'DATA','2I','trigerThreshold',(FID,'actorEffect')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRefr(MelRecord):
    """Placed Object."""
    rec_sig = b'REFR'

    _lockFlags = Flags(0, Flags.getNames(None, None, 'leveledLock'))
    _destinationFlags = Flags(0, Flags.getNames('noAlarm'))
    reflectFlags = Flags(0, Flags.getNames('reflection', 'refraction'))

    melSet = MelSet(
        MelEdid(),
        MelOptStruct(b'RCLR','8B','referenceStartColorRed','referenceStartColorGreen','referenceStartColorBlue',('referenceColorUnused1',null1),
                     'referenceEndColorRed','referenceEndColorGreen','referenceEndColorBlue',('referenceColorUnused2',null1)),
        MelFid(b'NAME','base'),
        MelFid(b'XEZN','encounterZone'),
        MelBase(b'XRGD','ragdollData'),
        MelBase(b'XRGB','ragdollBipedData'),
        MelOptStruct(b'XPRM', u'3f3IfI', u'primitiveBoundX',
            u'primitiveBoundY', u'primitiveBoundZ', u'primitiveColorRed',
            u'primitiveColorGreen', u'primitiveColorBlue', u'primitiveUnknown',
            u'primitiveType'),
        MelOptUInt32(b'XTRI', 'collisionLayer'),
        MelBase(b'XMBP','multiboundPrimitiveMarker'),
        MelOptStruct(b'XMBO','3f','boundHalfExtentsX','boundHalfExtentsY','boundHalfExtentsZ'),
        MelOptStruct(b'XTEL','I6fI',(FID,'destinationFid'),'destinationPosX','destinationPosY',
            'destinationPosZ','destinationRotX','destinationRotY','destinationRotZ',(_destinationFlags,'destinationFlags')),
        MelMapMarker(),
        MelFid(b'XTRG','targetId'),
        MelOptSInt32(b'XLCM', u'levelMod'),
        MelGroup('patrolData',
            MelFloat(b'XPRD', 'idleTime'),
            MelBase(b'XPPA','patrolScriptMarker'),
            MelFid(b'INAM', 'idle'),
            MelEmbeddedScript(),
            MelFid(b'TNAM','topic'),
        ),
        MelOptStruct(b'XRDO','fIfI','rangeRadius','broadcastRangeType','staticPercentage',(FID,'positionReference')),
        MelOwnership(),
        ##: I dropped special handling here, looks like a regular truncated
        # record to me - but no way to test since we don't load this yet
        MelTruncatedStruct(
            b'XLOC', 'B3sI4sB3s4s', 'lockLevel', ('unused1',null3),
            (FID, 'lockKey'), ('unused2', null4), (_lockFlags, 'lockFlags'),
            ('unused3', null3), ('unused4', null4), is_optional=True,
            old_versions={'B3sI4s'}),
        MelOptSInt32(b'XCNT', 'count'),
        MelOptFloat(b'XRDS', 'radius'),
        MelOptFloat(b'XHLP', 'health'),
        MelOptFloat(b'XRAD', 'radiation'),
        MelOptFloat(b'XCHG', u'charge'),
        MelGroup('ammo',
            MelFid(b'XAMT','type'),
            MelUInt32(b'XAMC', 'count'),
        ),
        MelGroups('reflectedByWaters',
            MelStruct(b'XPWR', '2I', (FID, 'reference'),
                      (reflectFlags, 'reflection_type')),
        ),
        MelFids(b'XLTW','litWaters'),
        MelGroups('linkedDecals',
            MelStruct(b'XDCR', '2I', (FID, 'reference'), 'unknown'),
        ),
        MelFid(b'XLKR','linkedReference'),
        MelOptStruct(b'XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelActivateParents(),
        MelEnableParent(),
        MelOptFid(b'XEMI', u'emittance'),
        MelFid(b'XMBR','multiboundReference'),
        MelActionFlags(),
        MelBase(b'ONAM','onam_p'),
        MelBase(b'XIBS','ignoredBySandbox'),
        MelOptStruct(b'XNDP','2I',(FID,'navMesh'),'unknown'),
        MelOptStruct(b'XPOD','II',(FID,'portalDataRoom0'),(FID,'portalDataRoom1')),
        MelOptStruct(b'XPTL','9f','portalWidth','portalHeight','portalPosX','portalPosY','portalPosZ',
                     'portalRot1','portalRot2','portalRot3','portalRot4'),
        MelBase(b'XSED','speedTreeSeed'),
        ####SpeedTree Seed, if it's a single byte then it's an offset into the list of seed values in the TREE record
        ####if it's 4 byte it's the seed value directly.
        MelGroup('roomData',
            MelStruct(b'XRMR','H2s','linkedRoomsCount','unknown'),
            MelFids(b'XLRM','linkedRoom'),
        ),
        MelOptStruct(b'XOCP','9f','occlusionPlaneWidth','occlusionPlaneHeight','occlusionPlanePosX','occlusionPlanePosY','occlusionPlanePosZ',
                     'occlusionPlaneRot1','occlusionPlaneRot2','occlusionPlaneRot3','occlusionPlaneRot4'),
        MelOptStruct(b'XORD','4I',(FID,'linkedOcclusionPlane0'),(FID,'linkedOcclusionPlane1'),(FID,'linkedOcclusionPlane2'),(FID,'linkedOcclusionPlane3')),
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
        ( 0,'conform'),
        ( 1,'paintVertices'),
        ( 2,'sizeVariance'),
        ( 3,'deltaX'),
        ( 4,'deltaY'),
        ( 5,'deltaZ'),
        ( 6,'Tree'),
        ( 7,'hugeRock'),))
    sdflags = Flags(0, Flags.getNames(
        ( 0,'pleasant'),
        ( 1,'cloudy'),
        ( 2,'rainy'),
        ( 3,'snowy'),))
    rdatFlags = Flags(0, Flags.getNames(
        ( 0,'Override'),))

    melSet = MelSet(
        MelEdid(),
        MelIcons(),
        MelStruct(b'RCLR','3Bs','mapRed','mapBlue','mapGreen',('unused1',null1)),
        MelFid(b'WNAM','worldspace'),
        MelGroups('areas',
            MelUInt32(b'RPLI', 'edgeFalloff'),
            MelArray('points',
                MelStruct(b'RPLD', '2f', 'posX', 'posY'),
            ),
        ),
        MelGroups('entries',
            MelStruct(b'RDAT', 'I2B2s', 'entryType', (rdatFlags, 'flags'),
                      'priority', ('unused1', null2)),
            MelRegnEntrySubrecord(2, MelArray('objects',
                MelStruct(
                    b'RDOT', 'IH2sf4B2H5f3H2s4s', (FID, 'objectId'),
                    'parentIndex', ('unk1', null2), 'density', 'clustering',
                    'minSlope', 'maxSlope', (obflags, 'flags'),
                    'radiusWRTParent', 'radius', 'minHeight', 'maxHeight',
                    'sink', 'sinkVar', 'sizeVar', 'angleVarX', 'angleVarY',
                    'angleVarZ', ('unk2', null2), ('unk3', null4)),
            )),
            MelRegnEntrySubrecord(4, MelString(b'RDMP', 'mapName')),
            MelRegnEntrySubrecord(6, MelArray('grasses',
                MelStruct(b'RDGS', 'I4s', (FID, 'grass'), ('unknown', null4)),
            )),
            MelRegnEntrySubrecord(7, MelOptUInt32(b'RDMD', 'musicType')),
            MelRegnEntrySubrecord(7, MelFid(b'RDMO', 'music')),
            MelRegnEntrySubrecord(7, MelArray('sounds',
                MelStruct(b'RDSD', '3I', (FID, 'sound'), (sdflags, 'flags'),
                          'chance'),
            )),
            MelRegnEntrySubrecord(3, MelArray('weatherTypes',
                MelStruct(b'RDWT', u'3I', (FID, u'weather'), u'chance',
                          (FID, u'global')),
            )),
        ),
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
        MelStruct(b'DATA','I4s5Bs','boneCount','unused1','feedback',
            'footIK','lookIK','grabIK','poseMatching','unused2'),
        MelFid(b'XNAM','actorBase'),
        MelFid(b'TNAM','bodyPartData'),
        MelStruct(b'RAFD','13f2i','keyBlendAmount','hierarchyGain','positionGain',
            'velocityGain','accelerationGain','snapGain','velocityDamping',
            'snapMaxLinearVelocity','snapMaxAngularVelocity','snapMaxLinearDistance',
            'snapMaxAngularDistance','posMaxVelLinear',
            'posMaxVelAngular','posMaxVelProjectile','posMaxVelMelee'),
        MelArray('feedbackDynamicBones',
            MelUInt16(b'RAFB', 'bone'),
        ),
        MelStruct(b'RAPS','3HBs4f','matchBones1','matchBones2','matchBones3',
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
            MelArray('placements',
                MelStruct(b'DATA', u'7f', u'posX', u'posY', u'posZ', u'rotX',
                          u'rotY', u'rotZ', u'scale'),
            ),
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
            'randomFrequencyShift',
            'playAtRandom',
            'environmentIgnored',
            'randomLocation',
            'loop',
            'menuSound',
            'twoD',
            'three60LFE',
            'dialogueSound',
            'envelopeFast',
            'envelopeSlow',
            'twoDRadius',
            'muteWhenSubmerged',
        ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelString(b'FNAM','soundFile'),
        MelStruct(b'SNDD', '2BbsIh2B6h3i', 'minDist', 'maxDist', 'freqAdj',
                  ('unusedSndd', null1), (_flags, 'flags'), 'staticAtten',
                  'stopTime', 'startTime', 'point0', 'point1', 'point2',
                  'point3', 'point4', 'reverb', 'priority', 'xLoc', 'yLoc'),
        # These are the older format - read them, but only write out SNDD
        MelReadOnly(
            MelStruct(b'SNDX', '2BbsIh2B', 'minDist', 'maxDist', 'freqAdj',
                      ('unusedSndd', null1), (_flags, 'flags'), 'staticAtten',
                      'stopTime', 'startTime'),
            MelStruct(b'ANAM', '5h', 'point0', 'point1', 'point2', 'point3',
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
        MelStruct(b'SPIT', '3IB3s', 'spellType', 'cost', 'level',
                  (_SpellFlags, 'flags', 0), ('unused1', null3)),
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
        MelTruncatedStruct(b'DNAM', '3Bs', 'baseHackingDifficulty',
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
        MelArray('speedTree',
            MelUInt32(b'SNAM', 'seed'),
        ),
        MelStruct(b'CNAM','5fi2f', 'curvature','minAngle','maxAngle',
                  'branchDim','leafDim','shadowRadius','rockSpeed',
                  'rustleSpeed'),
        MelStruct(b'BNAM','2f','widthBill','heightBill'),
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

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelString(b'NNAM','texture'),
        MelUInt8(b'ANAM', 'opacity'),
        MelUInt8Flags(b'FNAM', u'flags', _flags),
        MelString(b'MNAM','material'),
        MelFid(b'SNAM','sound',),
        MelFid(b'XNAM','effect'),
        MelWatrData(b'DATA','10f3Bs3Bs3BsI32fH',('windVelocity',0.100),('windDirection',90.0),
            ('waveAmp',0.5),('waveFreq',1.0),('sunPower',50.0),('reflectAmt',0.5),
            ('fresnelAmt',0.0250),('unknown1',0.0),('fogNear',27852.8),('fogFar',163840.0),
            ('shallowRed',0),('shallowGreen',128),('shallowBlue',128),('unused1',null1),
            ('deepRed',0),('deepGreen',0),('deepBlue',25),('unused2',null1),
            ('reflRed',255),('reflGreen',255),('reflBlue',255),('unused3',null1),
            ('unknown2',0),
            ('rainForce',0.1000),('rainVelocity',0.6000),('rainFalloff',0.9850),('rainDampner',2.0000),('rainSize',0.0100),
            ('dispForce',0.4000),('dispVelocity', 0.6000),('dispFalloff',0.9850),('dispDampner',10.0000),('dispSize',0.0500),
            ('noiseNormalsScale',1.8000),('noiseLayer1WindDirection',0.0000),('noiseLayer2WindDirection',-431602080.0500),
            ('noiseLayer3WindDirection',-431602080.0500),('noiseLayer1WindVelocity',0.0000),
            ('noiseLayer2WindVelocity',-431602080.0500),('noiseLayer3WindVelocity',-431602080.0500),
            ('noiseNormalsDepthFalloffStart',0.00000),('noiseNormalsDepthFalloffEnd',0.10000),
            ('fogAboveWaterAmount',1.00000),('noiseNormalsUvScale',500.00000),
            ('fogUnderWaterAmount',1.00000),('fogUnderWaterNear',0.00000),('fogUnderWaterFar',1000.00000),
            ('distortionAmount',250.00000),('shininess',100.00000),('reflectHdrMult',1.00000),
            ('lightRadius',10000.00000),('lightBrightness',1.00000),
            ('noiseLayer1UvScale',100.00000),('noiseLayer2UvScale',100.00000),('noiseLayer3UvScale',100.00000),
            ('damage',0)),
        MelWatrDnam(b'DNAM','10f3Bs3Bs3BsI35f',('windVelocity',0.100),('windDirection',90.0),
            ('waveAmp',0.5),('waveFreq',1.0),('sunPower',50.0),('reflectAmt',0.5),
            ('fresnelAmt',0.0250),('unknown1',0.0),('fogNear',27852.8),('fogFar',163840.0),
            ('shallowRed',0),('shallowGreen',128),('shallowBlue',128),('unused1',null1),
            ('deepRed',0),('deepGreen',0),('deepBlue',25),('unused2',null1),
            ('reflRed',255),('reflGreen',255),('reflBlue',255),('unused3',null1),
            ('unknown2',0),
            ('rainForce',0.1000),('rainVelocity',0.6000),('rainFalloff',0.9850),('rainDampner',2.0000),('rainSize',0.0100),
            ('dispForce',0.4000),('dispVelocity', 0.6000),('dispFalloff',0.9850),('dispDampner',10.0000),('dispSize',0.0500),
            ('noiseNormalsScale',1.8000),('noiseLayer1WindDirection',0.0000),('noiseLayer2WindDirection',-431602080.0500),
            ('noiseLayer3WindDirection',-431602080.0500),('noiseLayer1WindVelocity',0.0000),
            ('noiseLayer2WindVelocity',-431602080.0500),('noiseLayer3WindVelocity',-431602080.0500),
            ('noiseNormalsDepthFalloffStart',0.00000),('noiseNormalsDepthFalloffEnd',0.10000),
            ('fogAboveWaterAmount',1.00000),('noiseNormalsUvScale',500.00000),
            ('fogUnderWaterAmount',1.00000),('fogUnderWaterNear',0.00000),('fogUnderWaterFar',1000.00000),
            ('distortionAmount',250.00000),('shininess',100.00000),('reflectHdrMult',1.00000),
            ('lightRadius',10000.00000),('lightBrightness',1.00000),
            ('noiseLayer1UvScale',100.00000),('noiseLayer2UvScale',100.00000),('noiseLayer3UvScale',100.00000),
            ('noiseLayer1Amp',0.00000),('noiseLayer2Amp',0.00000),('noiseLayer3Amp',0.00000),
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
            'playerOnly',
            'npcsUseAmmo',
            'noJamAfterReload',
            'overrideActionPoint',
            'minorCrime',
            'rangeFixed',
            'notUseInNormalCombat',
            'overrideDamageToWeaponMult',
            'dontUse3rdPersonISAnimations',
            'shortBurst',
            'RumbleAlternate',
            'longBurst',
        ))
    _cflags = Flags(0, Flags.getNames(
            'onDeath',
            'unknown1','unknown2','unknown3','unknown4',
            'unknown5','unknown6','unknown7',
        ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelScript(),
        MelEnchantment(),
        MelOptUInt16(b'EAMT', 'objectEffectPoints'),
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
        MelString(b'NNAM','embeddedWeaponNode'),
        MelFid(b'INAM','impactDataset'),
        MelFid(b'WNAM','firstPersonModel'),
        MelFid(b'SNAM','soundGunShot3D'),
        MelFid(b'XNAM','soundGunShot2D'),
        MelFid(b'NAM7','soundGunShot3DLooping'),
        MelFid(b'TNAM','soundMeleeSwingGunNoAmmo'),
        MelFid(b'NAM6','soundBlock'),
        MelFid(b'UNAM','idleSound',),
        MelFid(b'NAM9','equipSound',),
        MelFid(b'NAM8','unequipSound',),
        MelStruct(b'DATA','2IfHB','value','health','weight','damage','clipsize'),
        MelTruncatedStruct(b'DNAM', 'I2f4B5fI4B2f2I11fiI2fi3f',
                    'animationType','animationMultiplier','reach',
                    (_dflags1,'dnamFlags1',0),('gripAnimation',255),'ammoUse',
                    'reloadAnimation','minSpread','spread','weapDnam1','sightFov',
                    ('weapDnam2',0.0),(FID,'projectile',0),'baseVatsToHitChance',
                    ('attackAnimation',255),'projectileCount','embeddedWeaponActorValue',
                    'minRange','maxRange','onHit',(_dflags2,'dnamFlags2',0),
                    'animationAttackMultiplier','fireRate','overrideActionPoint',
                    'rumbleLeftMotorStrength','rumbleRightMotorStrength',
                    'rumbleDuration','overrideDamageToWeaponMult','attackShotsPerSec',
                    'reloadTime','jamTime','aimArc',('skill',45),'rumblePattern',
                    'rambleWavelangth','limbDmgMult',('resistType',-1),
                    'sightUsage','semiAutomaticFireDelayMin',
                    'semiAutomaticFireDelayMax',
                    old_versions={'I2f4B5fI4B2f2I11fiI2fi',
                                  'I2f4B5fI4B2f2I11fiI2f'}),
        MelOptStruct(b'CRDT','H2sfB3sI',('criticalDamage', 0),('weapCrdt1', null2),
                     ('criticalMultiplier', 0.0),(_cflags,'criticalFlags', 0),
                     ('weapCrdt2', null3),(FID,'criticalEffect', 0)),
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
        MelOptStruct(b'PNAM','BB',(pnamFlags,'parentFlags',0),('unknownff',0xff)),
        MelFid(b'CNAM','climate'),
        MelFid(b'NAM2','water'),
        MelFid(b'NAM3','waterType'),
        MelFloat(b'NAM4', 'waterHeight'),
        MelStruct(b'DNAM','ff','defaultLandHeight','defaultWaterHeight'),
        MelIcon(u'mapPath'),
        MelStruct(b'MNAM', u'2i4h', u'dimX', u'dimY', u'NWCellX', u'NWCellY',
                  u'SECellX', u'SECellY'),
        MelStruct(b'ONAM','fff','worldMapScale','cellXOffset','cellYOffset'),
        MelFid(b'INAM','imageSpace'),
        MelUInt8Flags(b'DATA', u'flags', _flags),
        MelWorldBounds(),
        MelFid(b'ZNAM','music'),
        MelString(b'NNAM','canopyShadow'),
        MelString(b'XNAM','waterNoiseTexture'),
        MelGroups('swappedImpacts',
            MelStruct(b'IMPS', '3I', 'materialType', (FID, 'old'),
                      (FID, 'new')),
        ),
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
        MelStruct(b'ONAM','4B','cloudSpeed0','cloudSpeed1','cloudSpeed3','cloudSpeed4'),
        MelArray('cloudColors',
            MelWthrColors(b'PNAM'),
        ),
        MelArray('daytimeColors',
            MelWthrColors(b'NAM0'),
        ),
        MelStruct(b'FNAM','6f','fogDayNear','fogDayFar','fogNightNear','fogNightFar','fogDayPower','fogNightPower'),
        MelBase(b'INAM', 'unused1', null1 * 304),
        MelStruct(b'DATA','15B',
            'windSpeed','lowerCloudSpeed','upperCloudSpeed','transDelta',
            'sunGlare','sunDamage','rainFadeIn','rainFadeOut','boltFadeIn',
            'boltFadeOut','boltFrequency','weatherType','boltRed','boltBlue','boltGreen'),
        MelGroups('sounds',
            MelStruct(b'SNAM', '2I', (FID, 'sound'), 'type'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()
