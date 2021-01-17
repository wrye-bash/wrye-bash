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
"""This module contains the falloutnv record classes."""
from __future__ import division
# Set MelModel in brec, in this case it's identical to the fallout 3 one
from ..fallout3.records import MelOwnership, MelDestructible, MelEffects, \
    MelConditions, MelEmbeddedScript, MelItems, MelEquipmentType, MelBipedData
from ..fallout3.records import _MelModel # HACK - needed for tests
from ...bolt import Flags, struct_calcsize
from ...brec import MelModel # set in Mopy/bash/game/fallout3/records.py
from ...brec import MelRecord, MelGroups, MelStruct, FID, MelGroup, \
    MelString, MelSet, MelFid, MelOptStruct, MelFids, MelBase, \
    MelFidList, MreGmstBase, MreHeaderBase, MelColorInterpolator, \
    MelValueInterpolator, MelRegnEntrySubrecord, MelFloat, MelSInt8, \
    MelSInt16, MelSInt32, MelUInt8, MelUInt32, MelOptFid, MelOptFloat, \
    MelOptSInt32, MelOptUInt8, MelOptUInt16, MelOptUInt32, MelBounds, null1, \
    null2, null3, null4, MelTruncatedStruct, MelReadOnly, MelSkipInterior, \
    MelIcons, MelIcons2, MelIcon, MelIco2, MelEdid, MelFull, MelArray, \
    MelObject, MreWithItems, MelRef3D, MelXlod, MelNull, MelEnableParent, \
    MelRefScale, MelMapMarker, MelActionFlags, MelEnchantment, MelScript, \
    MelDecalData, MelDescription, MelPickupSound, MelDropSound, \
    MelActivateParents, MelUInt8Flags, MelOptUInt32Flags
from ...exception import ModSizeError

#------------------------------------------------------------------------------
# FalloutNV Records -----------------------------------------------------------
#------------------------------------------------------------------------------
class MreTes4(MreHeaderBase):
    """TES4 Record.  File header."""
    rec_sig = b'TES4'

    melSet = MelSet(
        MelStruct(b'HEDR', 'f2I', ('version', 1.34), 'numRecords',
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
        MelSInt32(b'XLCM', 'levelModifier'),
        MelFid(b'XMRC','merchantContainer',),
        MelSInt32(b'XCNT', 'count'),
        MelFloat(b'XRDS', 'radius'),
        MelFloat(b'XHLP', 'health'),
        MelGroups('linkedDecals',
            MelStruct(b'XDCR', '2I', (FID, 'reference'), 'unknown'),
        ),
        MelFid(b'XLKR','linkedReference'),
        MelOptStruct(b'XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelActivateParents(),
        MelString(b'XATO','activationPrompt'),
        MelEnableParent(),
        MelOptFid(b'XEMI', 'emittance'),
        MelFid(b'XMBR','multiboundReference'),
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
        MelSInt32(b'XLCM', 'levelModifier'),
        MelOwnership(),
        MelFid(b'XMRC','merchantContainer'),
        MelSInt32(b'XCNT', 'count'),
        MelFloat(b'XRDS', 'radius'),
        MelFloat(b'XHLP', 'health'),
        MelGroups('linkedDecals',
            MelStruct(b'XDCR', '2I', (FID, 'reference'), 'unknown'),
        ),
        MelFid(b'XLKR','linkedReference'),
        MelOptStruct(b'XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelActivateParents(),
        MelString(b'XATO','activationPrompt'),
        MelEnableParent(),
        MelOptFid(b'XEMI', 'emittance'),
        MelFid(b'XMBR','multiboundReference'),
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
        MelFid(b'SNAM','soundLooping'),
        MelFid(b'VNAM','soundActivation'),
        MelFid(b'INAM','radioTemplate'),
        MelFid(b'RNAM','radioStation'),
        MelFid(b'WNAM','waterType'),
        MelString(b'XATO','activationPrompt'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAloc(MelRecord):
    """Media Location Controller."""
    rec_sig = b'ALOC'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt32(b'NAM1', 'flags'),
        MelUInt32(b'NAM2', 'num2'),
        MelUInt32(b'NAM3', 'nam3'),
        MelUInt32(b'NAM4', 'locationDelay'),
        MelUInt32(b'NAM5', 'dayStart'),
        MelUInt32(b'NAM6', 'nightStart'),
        MelUInt32(b'NAM7', 'retrigerDelay'),
        MelFids(b'HNAM','neutralSets'),
        MelFids(b'ZNAM','allySets'),
        MelFids(b'XNAM','friendSets'),
        MelFids(b'YNAM','enemySets'),
        MelFids(b'LNAM','locationSets'),
        MelFids(b'GNAM','battleSets'),
        MelFid(b'RNAM','conditionalFaction'),
        MelUInt32(b'FNAM', 'fnam'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAmef(MelRecord):
    """Ammo Effect."""
    rec_sig = b'AMEF'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelStruct(b'DATA','2If','type','operation','value'),
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
        MelScript(),
        MelDestructible(),
        MelPickupSound(),
        MelDropSound(),
        MelStruct(b'DATA','fB3siB','speed',(_flags,'flags',0),('ammoData1',null3),
                  'value','clipRounds'),
        MelTruncatedStruct(b'DAT2', '2IfIf', 'projPerShot',
                           (FID, 'projectile', 0), 'weight',
                           (FID, 'consumedAmmo'), 'consumedPercentage',
                           old_versions={'2If'}),
        MelString(b'ONAM','shortName'),
        MelString(b'QNAM','abbrev'),
        MelFids(b'RCIL','effects'),
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
        MelTruncatedStruct(b'DNAM', 'hHf4s', 'ar',
                           (_dnamFlags, 'dnamFlags', 0), ('dt', 0.0),
                           ('armaDnam1', null4), old_versions={'hH'}),
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
        MelTruncatedStruct(b'DNAM', 'hHf4s', 'ar',
                           (_dnamFlags, 'dnamFlags', 0), ('dt', 0.0),
                           ('armoDnam1', null4), old_versions={'hH'}),
        MelUInt32(b'BNAM', u'overridesAnimationSound'),
        MelGroups('animationSounds',
            MelStruct(b'SNAM', 'IB3sI', (FID, 'sound'), 'chance',
                      ('unused1', b'\xb7\xe7\x0b'), 'type'),
        ),
        MelFid(b'TNAM','animationSoundsTemplate'),
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
        MelFids(b'SNAM','soundLooping'),
        MelUInt32(b'WNAM', 'wallaTrigerCount'),
        MelFid(b'RDAT','useSoundFromRegion'),
        MelUInt32(b'ANAM', 'environmentType'),
        MelUInt32(b'INAM', 'isInterior'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCcrd(MelRecord):
    """Caravan Card."""
    rec_sig = b'CCRD'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelScript(),
        MelPickupSound(),
        MelDropSound(),
        MelString(b'TX00','textureFace'),
        MelString(b'TX01','textureBack'),
        MelUInt32(b'INTV', 'card_suit'),
        MelUInt32(b'INTV', 'card_value'),
        MelUInt32(b'DATA', 'value'),
    ).with_distributor({
        b'INTV': (u'card_suit', {
            b'INTV': u'card_value',
        }),
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCdck(MelRecord):
    """Caravan Deck."""
    rec_sig = b'CDCK'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelFids(b'CARD','cards'),
        MelUInt32(b'DATA', 'count'), # 'Count (broken)' in xEdit - unused?
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
        MelOptUInt8(b'XCMT', 'xcmt_p'),
        MelFid(b'XCIM','imageSpace'),
        MelOptUInt8(b'XCET', 'xcet_p'),
        MelFid(b'XEZN','encounterZone'),
        MelFid(b'XCCM','climate'),
        MelFid(b'XCWT','water'),
        MelOwnership(),
        MelFid(b'XCAS','acousticSpace'),
        MelFid(b'XCMO','music'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreChal(MelRecord):
    """Challenge."""
    rec_sig = b'CHAL'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelScript(),
        MelDescription(),
        MelStruct(b'DATA','4I2s2s4s','type','threshold','flags','interval',
                  'dependOnType1','dependOnType2','dependOnType3'),
        MelFid(b'SNAM','dependOnType4'),
        MelFid(b'XNAM','dependOnType5'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreChip(MelRecord):
    """Casino Chip."""
    rec_sig = b'CHIP'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelPickupSound(),
        MelDropSound(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCmny(MelRecord):
    """Caravan Money."""
    rec_sig = b'CMNY'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelPickupSound(),
        MelDropSound(),
        MelUInt32(b'DATA', 'absoluteValue'),
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
        MelFid(b'RNAM','soundRandomLooping'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCsno(MelRecord):
    """Casino."""
    rec_sig = b'CSNO'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelStruct(b'DATA','2f9I2II','decksPercentBeforeShuffle','BlackjackPayoutRatio',
            'slotReel0','slotReel1','slotReel2','slotReel3','slotReel4','slotReel5','slotReel6',
            'numberOfDecks','maxWinnings',(FID,'currency'),(FID,'casinoWinningQuest'),'flags'),
        MelGroups('chipModels',
            MelString(b'MODL','model')
        ),
        MelString(b'MOD2','slotMachineModel'),
        MelString(b'MOD3','blackjackTableModel'),
        MelString(b'MODT','extraBlackjackTableModel'),
        MelString(b'MOD4','rouletteTableModel'),
        MelGroups('slotReelTextures',
            MelIcon(u'texture'),
        ),
        MelGroups('blackjackDecks',
            MelIco2(u'texture'),
        ),
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
                     'waitToFireTimerMax', 'fireTimerMin', 'fireTimerMax',
                     'rangedWeaponRangeMultMin', 'unkCSSD1', 'weaponRestrictions',
                     'rangedWeaponRangeMultMax', 'maxTargetingFov', 'combatRadius',
                     'semiAutomaticFireDelayMultMin', 'semiAutomaticFireDelayMultMax'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDehy(MelRecord):
    """Dehydration Stage."""
    rec_sig = b'DEHY'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA','2I','trigerThreshold',(FID,'actorEffect')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDial(MelRecord):
    """Dialogue."""
    rec_sig = b'DIAL'

    _DialFlags = Flags(0, Flags.getNames('rumors', 'toplevel', ))

    melSet = MelSet(
        MelEdid(),
        MelFid(b'INFC','bare_infc_p'),
        MelFid(b'INFX','bare_infx_p'),
        MelGroups('quests',
            MelFid(b'QSTI','quest'),
            MelGroups('unknown',
                MelFid(b'INFC','infc_p'),
                MelBase(b'INFX','infx_p'),
            ),
        ),
        MelFull(),
        MelFloat(b'PNAM', 'priority'),
        MelString(b'TDUM','tdum_p'),
        MelTruncatedStruct(b'DATA', '2B', 'dialType',
                           (_DialFlags, 'dialFlags', 0), old_versions={'B'}),
    ).with_distributor({
        b'INFC': u'bare_infc_p',
        b'INFX': u'bare_infx_p',
        b'QSTI': {
            b'INFC|INFX': u'quests',
        },
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDobj(MelRecord):
    """Default Object Manager."""
    rec_sig = b'DOBJ'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA','34I',(FID,'stimpack'),(FID,'superStimpack'),(FID,'radX'),(FID,'radAway'),
            (FID,'morphine'),(FID,'perkParalysis'),(FID,'playerFaction'),(FID,'mysteriousStrangerNpc'),
            (FID,'mysteriousStrangerFaction'),(FID,'defaultMusic'),(FID,'battleMusic'),(FID,'deathMusic'),
            (FID,'successMusic'),(FID,'levelUpMusic'),(FID,'playerVoiceMale'),(FID,'playerVoiceMaleChild'),
            (FID,'playerVoiceFemale'),(FID,'playerVoiceFemaleChild'),(FID,'eatPackageDefaultFood'),
            (FID,'everyActorAbility'),(FID,'drugWearsOffImageSpace'),(FID,'doctersBag'),(FID,'missFortuneNpc'),
            (FID,'missFortuneFaction'),(FID,'meltdownExplosion'),(FID,'unarmedForwardPA'),(FID,'unarmedBackwardPA'),
            (FID,'unarmedLeftPA'),(FID,'unarmedRightPA'),(FID,'unarmedCrouchPA'),(FID,'unarmedCounterPA'),
            (FID,'spotterEffect'),(FID,'itemDetectedEffect'),(FID,'cateyeMobileEffect'),),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEnch(MelRecord):
    """Object Effect."""
    rec_sig = b'ENCH'

    _flags = Flags(0, Flags.getNames('noAutoCalc','autoCalculate','hideEffect'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelStruct(b'ENIT','3IB3s','itemType','chargeAmount','enchantCost',
                  (_flags,'flags',0),('unused1',null3)),
        MelEffects(),
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
        MelOptFid(b'WMI1', u'reputation'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreGmst(MreGmstBase):
    """Game Setting."""
    isKeyedByEid = True # NULL fids are acceptable.

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
class MreHung(MelRecord):
    """Hunger Stage."""
    rec_sig = b'HUNG'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA','2I','trigerThreshold',(FID,'actorEffect')),
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
        MelValueInterpolator(b'\x12IAD', 'contrastMultInterp'),
        MelValueInterpolator(b'\x52IAD', 'contrastAddInterp'),
        MelValueInterpolator(b'\x13IAD', 'contrastAvgMultInterp'),
        MelValueInterpolator(b'\x53IAD', 'contrastAvgAddInterp'),
        MelValueInterpolator(b'\x14IAD', 'brightnessMultInterp'),
        MelValueInterpolator(b'\x54IAD', 'brightnessAddInterp'),
        MelFid(b'RDSD', 'soundIntro'),
        MelFid(b'RDSI', 'soundOutro'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreImod(MelRecord):
    """Item Mod."""
    rec_sig = b'IMOD'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelScript(),
        MelDescription(),
        MelDestructible(),
        MelPickupSound(),
        MelDropSound(),
        MelStruct(b'DATA','If','value','weight'),
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
        'sayOnceADay','alwaysDarken',None,None,'lowIntelligence','highIntelligence',))

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
        MelFids(b'TCFU','tcfu_p'),
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
        MelFid(b'RNAM','soundRandomLooping'),
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
            MelStruct(b'LNAM', '2I2h', (FID, 'direct'), (FID, 'indirect'),
                      'gridy', 'gridx'),
        ),
        MelFid(b'WMI1','loadScreenType'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLsct(MelRecord):
    """Load Screen Type."""
    rec_sig = b'LSCT'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA','5IfI3fI20sI3f4sI','type','data1X','data1Y','data1Width',
                         'data1Height','data1Orientation',
            'data1Font','data1ColorR','data1ColorG','data1ColorB','data1Align','unknown1',
            'data2Font','data2ColorR','data2ColorG','data2ColorB','unknown2','stats'),
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
        MelFid(b'RNAM','soundRandomLooping'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMset(MelRecord):
    """Media Set."""
    rec_sig = b'MSET'

    _flags = Flags(0, Flags.getNames(
        ( 0,'dayOuter'),
        ( 1,'dayMiddle'),
        ( 2,'dayInner'),
        ( 3,'nightOuter'),
        ( 4,'nightMiddle'),
        ( 5,'nightInner'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt32(b'NAM1', 'type'),
        MelString(b'NAM2','nam2'),
        MelString(b'NAM3','nam3'),
        MelString(b'NAM4','nam4'),
        MelString(b'NAM5','nam5'),
        MelString(b'NAM6','nam6'),
        MelString(b'NAM7','nam7'),
        MelFloat(b'NAM8', 'nam8'),
        MelFloat(b'NAM9', 'nam9'),
        MelFloat(b'NAM0', 'nam0'),
        MelFloat(b'ANAM', 'anam'),
        MelFloat(b'BNAM', 'bnam'),
        MelFloat(b'CNAM', 'cnam'),
        MelFloat(b'JNAM', 'jnam'),
        MelFloat(b'KNAM', 'knam'),
        MelFloat(b'LNAM', 'lnam'),
        MelFloat(b'MNAM', 'mnam'),
        MelFloat(b'NNAM', 'nnam'),
        MelFloat(b'ONAM', 'onam'),
        MelUInt8Flags(b'PNAM', u'enableFlags', _flags),
        MelFloat(b'DNAM', 'dnam'),
        MelFloat(b'ENAM', 'enam'),
        MelFloat(b'FNAM', 'fnam'),
        MelFloat(b'GNAM', 'gnam'),
        MelOptFid(b'HNAM', 'hnam'),
        MelOptFid(b'INAM', 'inam'),
        MelBase(b'DATA','data'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMusc(MelRecord):
    """Music Type."""
    rec_sig = b'MUSC'

    melSet = MelSet(
        MelEdid(),
        MelString(b'FNAM','filename'),
        MelFloat(b'ANAM', 'dB'),
    )
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
        MelFloat(b'XRDS', 'radius',),
        MelFloat(b'XHLP', 'health',),
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
        MelString(b'XATO','activationPrompt'),
        MelEnableParent(),
        MelOptFid(b'XEMI', 'emittance'),
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
        MelFloat(b'XRDS', 'radius',),
        MelFloat(b'XHLP', 'health',),
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
        MelString(b'XATO','activationPrompt'),
        MelEnableParent(),
        MelOptFid(b'XEMI', 'emittance'),
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
        'detonates',
        'rotation'
        ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelTruncatedStruct(
            b'DATA', '2H3f2I3f2I3f3I4f', (_flags,'flags'), 'type',
            ('gravity', 0.0), ('speed', 10000.0), ('range', 10000.0),
            (FID, 'light', 0), (FID, 'muzzleFlash', 0), ('tracerChance', 0.0),
            ('explosionAltTrigerProximity', 0.0),
            ('explosionAltTrigerTimer', 0.0), (FID, 'explosion', 0),
            (FID, 'sound', 0), ('muzzleFlashDuration', 0.0),
            ('fadeDuration', 0.0), ('impactForce', 0.0),
            (FID, 'soundCountDown', 0), (FID, 'soundDisable', 0),
            (FID, 'defaultWeaponSource', 0), ('rotationX', 0.0),
            ('rotationY', 0.0), ('rotationZ', 0.0), ('bouncyMult', 0.0),
            old_versions={'2H3f2I3f2I3f3If', '2H3f2I3f2I3f3I'}),
        MelString(b'NAM1','muzzleFlashPath'),
        MelBase(b'NAM2','_nam2'),
        MelUInt32(b'VNAM', 'soundLevel'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRcct(MelRecord):
    """Recipe Category."""
    rec_sig = b'RCCT'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt8(b'DATA', 'flags'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRcpe(MelRecord):
    """Recipe."""
    rec_sig = b'RCPE'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelConditions(),
        MelStruct(b'DATA','4I','skill','level',(FID,'category'),(FID,'subCategory')),
        MelGroups('ingredients',
            MelFid(b'RCIL','item'),
            MelUInt32(b'RCQY', 'quantity'),
        ),
        MelGroups('outputs',
            MelFid(b'RCOD','item'),
            MelUInt32(b'RCQY', 'quantity'),
        ),
    ).with_distributor({
        b'RCIL': {
            b'RCQY': u'ingredients',
        },
        b'RCOD': {
            b'RCQY': u'outputs',
        },
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRefr(MelRecord):
    """Placed Object"""
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
        MelMapMarker(with_reputation=True),
        MelGroup('audioData',
            MelBase(b'MMRK','audioMarker'),
            MelBase(b'FULL','full_p'),
            MelFid(b'CNAM','audioLocation'),
            MelBase(b'BNAM','bnam_p'),
            MelBase(b'MNAM','mnam_p'),
            MelBase(b'NNAM','nnam_p'),
        ),
        MelBase(b'XSRF','xsrf_p'),
        MelBase(b'XSRD','xsrd_p'),
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
        MelString(b'XATO','activationPrompt'),
        MelEnableParent(),
        MelOptFid(b'XEMI', 'emittance'),
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
            MelRegnEntrySubrecord(7, MelFid(b'RDSI', 'incidentalMediaSet')),
            MelRegnEntrySubrecord(7, MelFids(b'RDSB', 'battleMediaSets')),
            MelRegnEntrySubrecord(7, MelArray('sounds',
                MelStruct(b'RDSD', '3I', (FID, 'sound'), (sdflags, 'flags'),
                          'chance'),
            )),
            MelRegnEntrySubrecord(3, MelArray('weatherTypes',
                MelStruct(b'RDWT', u'3I', (FID, u'weather'), u'chance',
                          (FID, u'global')),
            )),
            MelRegnEntrySubrecord(8, MelFidList(b'RDID', 'imposters')),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRepu(MelRecord):
    """Reputation."""
    rec_sig = b'REPU'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelIcons(),
        MelFloat(b'DATA', 'value'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSlpd(MelRecord):
    """Sleep Deprivation Stage."""
    rec_sig = b'SLPD'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA','2I','trigerThreshold',(FID,'actorEffect')),
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
            'startatRandomPosition',
        ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelString(b'FNAM','soundFile'),
        MelUInt8(b'RNAM', 'random_chance'),
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
class MreStat(MelRecord):
    """Static."""
    rec_sig = b'STAT'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelSInt8(b'BRUS', u'passthroughSound', -1),
        MelFid(b'RNAM','soundRandomLooping'),
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
        MelFid(b'INAM','radioTemplate'),
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
            'scopeHasNightVision',
            'scopeFromMod',
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
        MelGroup('modelWithMods',
            MelString(b'MWD1','mod1Path'),
            MelString(b'MWD2','mod2Path'),
            MelString(b'MWD3','mod1and2Path'),
            MelString(b'MWD4','mod3Path'),
            MelString(b'MWD5','mod1and3Path'),
            MelString(b'MWD6','mod2and3Path'),
            MelString(b'MWD7','mod1and2and3Path'),
        ),
        MelString(b'VANM','vatsAttackName'),
        MelString(b'NNAM','embeddedWeaponNode'),
        MelFid(b'INAM','impactDataset'),
        MelFid(b'WNAM','firstPersonModel'),
        MelGroup('firstPersonModelWithMods',
            MelFid(b'WNM1','mod1Path'),
            MelFid(b'WNM2','mod2Path'),
            MelFid(b'WNM3','mod1and2Path'),
            MelFid(b'WNM4','mod3Path'),
            MelFid(b'WNM5','mod1and3Path'),
            MelFid(b'WNM6','mod2and3Path'),
            MelFid(b'WNM7','mod1and2and3Path'),
        ),
        MelGroup('weaponMods',
            MelFid(b'WMI1','mod1'),
            MelFid(b'WMI2','mod2'),
            MelFid(b'WMI3','mod3'),
        ),
        MelFids(b'SNAM','soundGunShot3D'),
        MelFid(b'XNAM','soundGunShot2D'),
        MelFid(b'NAM7','soundGunShot3DLooping'),
        MelFid(b'TNAM','soundMeleeSwingGunNoAmmo'),
        MelFid(b'NAM6','soundBlock'),
        MelFid(b'UNAM','idleSound',),
        MelFid(b'NAM9','equipSound',),
        MelFid(b'NAM8','unequipSound',),
        MelFids(b'WMS1','soundMod1Shoot3Ds'),
        MelFid(b'WMS2','soundMod1Shoot2D'),
        MelStruct(b'DATA','2IfHB','value','health','weight','damage','clipsize'),
        MelTruncatedStruct(b'DNAM', 'I2f4B5fI4B2f2I11fiI2fi4f3I3f2IsB2s6fI',
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
                    # NV additions
                    ('weapDnam3',0.0),'effectMod1','effectMod2','effectMod3','valueAMod1',
                    'valueAMod2','valueAMod3','powerAttackAnimation','strengthReq',
                    ('weapDnam4',null1),'reloadAnimationMod',('weapDnam5',null2),
                    'regenRate','killImpulse','valueBMod1','valueBMod2','valueBMod3',
                    'impulseDist','skillReq',
                    old_versions={
                        'I2f4B5fI4B2f2I11fiI2fi4f3I3f2IsB2s6f',
                        'I2f4B5fI4B2f2I11fiI2fi4f3I3f2IsB2s5f',
                        'I2f4B5fI4B2f2I11fiI2fi4f3I3f2IsB2sf',
                        'I2f4B5fI4B2f2I11fiI2fi4f3I3f2I',
                        'I2f4B5fI4B2f2I11fiI2fi4f3I3f',
                        'I2f4B5fI4B2f2I11fiI2fi3f',
                        'I2f4B5fI4B2f2I11fiI2fi',
                        'I2f4B5fI4B2f2I11fiI2f',
                    }),
        MelOptStruct(b'CRDT','H2sfB3sI',('criticalDamage', 0),('weapCrdt1', null2),
                     ('criticalMultiplier', 0.0),(_cflags,'criticalFlags', 0),
                     ('weapCrdt2', null3),(FID,'criticalEffect', 0),),
        MelTruncatedStruct(b'VATS', u'I3f2B2s', (FID, u'vatsEffect'),
            u'vatsSkill', u'vatsDamMult', u'vatsAp', u'vatsSilent',
            u'vatsModReqiured', (u'weapVats1', null2), old_versions={u'I3f'},
            is_optional=True),
        MelBase(b'VNAM','soundLevel'),
    )
    __slots__ = melSet.getSlotsUsed()

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
            u'3Bs3Bs3Bs3Bs3Bs3Bs', u'riseRed', u'riseGreen', u'riseBlue',
            (u'unused1', null1), u'dayRed', u'dayGreen', u'dayBlue',
            (u'unused2', null1), u'setRed', u'setGreen', u'setBlue',
            (u'unused3', null1), u'nightRed', u'nightGreen', u'nightBlue',
            (u'unused4', null1), u'noonRed', u'noonGreen', u'noonBlue',
            (u'unused5', null1), u'midnightRed', u'midnightGreen',
            u'midnightBlue', (u'unused6', null1)
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
            for x in xrange(size_ // entry_size):
                arr_entry = MelObject()
                append_entry(arr_entry)
                arr_entry.__slots__ = entry_slots
                load_entry(arr_entry, ins, sub_type, entry_size, *debug_strs)
        else:
            _expected_sizes = (self._new_sizes[sub_type],
                               self._old_sizes[sub_type])
            raise ModSizeError(ins.inName, debug_strs, _expected_sizes, size_)

class MreWthr(MelRecord):
    """Weather."""
    rec_sig = b'WTHR'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'\x00IAD', 'sunriseImageSpaceModifier'),
        MelFid(b'\x01IAD', 'dayImageSpaceModifier'),
        MelFid(b'\x02IAD', 'sunsetImageSpaceModifier'),
        MelFid(b'\x03IAD', 'nightImageSpaceModifier'),
        MelFid(b'\x04IAD', 'unknown1ImageSpaceModifier'),
        MelFid(b'\x05IAD', 'unknown2ImageSpaceModifier'),
        MelString(b'DNAM','upperLayer'),
        MelString(b'CNAM','lowerLayer'),
        MelString(b'ANAM','layer2'),
        MelString(b'BNAM','layer3'),
        MelModel(),
        MelBase(b'LNAM','unknown1'),
        MelStruct(b'ONAM','4B','cloudSpeed0','cloudSpeed1','cloudSpeed3','cloudSpeed4'),
        MelWthrColorsFnv(b'PNAM', u'cloudColors'),
        MelWthrColorsFnv(b'NAM0', u'daytimeColors'),
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
