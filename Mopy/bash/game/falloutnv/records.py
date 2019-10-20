# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module contains the falloutnv record classes."""
from __future__ import division
import struct
# Set MelModel in brec, in this case it's identical to the fallout 3 one
from ..fallout3.records import MelOwnership, MelDestructible, MelBipedFlags, \
    MelEffects, MelConditions, MreHasEffects, MelEmbeddedScript
from ... import brec
from ...bolt import Flags
from ...brec import MelModel # set in Mopy/bash/game/fallout3/records.py
from ...brec import MelRecord, MelGroups, MelStruct, FID, MelGroup, \
    MelString, MelSet, MelFid, MelNull, MelOptStruct, MelFids, MelBase, \
    MelFidList, MreGmstBase, MreHeaderBase, MelUnicode, MelColorInterpolator, \
    MelValueInterpolator, MelRegnEntrySubrecord, MelFloat, MelSInt8, \
    MelSInt16, MelSInt32, MelUInt8, MelUInt32, MelOptFid, MelOptFloat, \
    MelOptSInt32, MelOptUInt8, MelOptUInt16, MelOptUInt32, MelBounds, null1, \
    null2, null3, null4, MelTruncatedStruct, MelReadOnly, MelCoordinates, \
    MelIcons, MelIcons2, MelIcon, MelIco2, MelEdid, MelFull, MelArray, \
    MelObject
from ...exception import ModSizeError

#------------------------------------------------------------------------------
# FalloutNV Records -----------------------------------------------------------
#------------------------------------------------------------------------------
class MreTes4(MreHeaderBase):
    """TES4 Record.  File header."""
    classType = 'TES4'

    melSet = MelSet(
        MelStruct('HEDR', 'f2I', ('version', 1.34), 'numRecords',
                  ('nextObject', 0x800)),
        MelBase('OFST','ofst_p',),  #--Obsolete?
        MelBase('DELE','dele_p',),  #--Obsolete?
        MelUnicode('CNAM','author',u'',512),
        MelUnicode('SNAM','description',u'',512),
        MreHeaderBase.MelMasterNames(),
        MelFidList('ONAM','overrides'),
        MelBase('SCRN', 'screenshot'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreAchr(MelRecord):
    """Placed NPC."""
    classType = 'ACHR'

    _flags = Flags(0, Flags.getNames('oppositeParent','popIn'))

    melSet = MelSet(
        MelEdid(),
        MelFid('NAME','base'),
        MelFid('XEZN','encounterZone'),
        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelGroup('patrolData',
            MelFloat('XPRD', 'idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelEmbeddedScript(),
            MelFid('TNAM','topic'),
        ),
        MelSInt32('XLCM', 'levelModifier'),
        MelFid('XMRC','merchantContainer',),
        MelSInt32('XCNT', 'count'),
        MelFloat('XRDS', 'radius'),
        MelFloat('XHLP', 'health'),
        MelGroups('linkedDecals',
            MelStruct('XDCR', '2I', (FID, 'reference'), 'unknown'),
        ),
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelUInt8('XAPD', 'flags'),
            MelGroups('activateParentRefs',
                MelStruct('XAPR', 'If', (FID, 'reference'), 'delay'),
            ),
        ),
        MelString('XATO','activationPrompt'),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),('unused1',null3)),
        MelOptFid('XEMI', 'emittance'),
        MelFid('XMBR','multiboundReference'),
        MelBase('XIBS','ignoredBySandbox'),
        MelOptFloat('XSCL', ('scale', 1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAcre(MelRecord):
    """Placed Creature."""
    classType = 'ACRE'

    _flags = Flags(0, Flags.getNames('oppositeParent','popIn'))

    melSet = MelSet(
        MelEdid(),
        MelFid('NAME','base'),
        MelFid('XEZN','encounterZone'),
        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelGroup('patrolData',
            MelFloat('XPRD', 'idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelEmbeddedScript(),
            MelFid('TNAM','topic'),
        ),
        MelSInt32('XLCM', 'levelModifier'),
        MelOwnership(),
        MelFid('XMRC','merchantContainer'),
        MelSInt32('XCNT', 'count'),
        MelFloat('XRDS', 'radius'),
        MelFloat('XHLP', 'health'),
        MelGroups('linkedDecals',
            MelStruct('XDCR', '2I', (FID, 'reference'), 'unknown'),
        ),
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelUInt8('XAPD', 'flags'),
            MelGroups('activateParentRefs',
                MelStruct('XAPR', 'If', (FID, 'reference'), 'delay'),
            ),
        ),
        MelString('XATO','activationPrompt'),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),('unused1',null3)),
        MelOptFid('XEMI', 'emittance'),
        MelFid('XMBR','multiboundReference'),
        MelBase('XIBS','ignoredBySandbox'),
        MelOptFloat('XSCL', ('scale', 1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreActi(MelRecord):
    """Activator."""
    classType = 'ACTI'
    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelFid('SNAM','soundLooping'),
        MelFid('VNAM','soundActivation'),
        MelFid('INAM','radioTemplate'),
        MelFid('RNAM','radioStation'),
        MelFid('WNAM','waterType'),
        MelString('XATO','activationPrompt'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAloc(MelRecord):
    """Media Location Controller."""
    classType = 'ALOC'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt32('NAM1', 'flags'),
        MelUInt32('NAM2', 'num2'),
        MelUInt32('NAM3', 'nam3'),
        MelUInt32('NAM4', 'locationDelay'),
        MelUInt32('NAM5', 'dayStart'),
        MelUInt32('NAM6', 'nightStart'),
        MelUInt32('NAM7', 'retrigerDelay'),
        MelFids('HNAM','neutralSets'),
        MelFids('ZNAM','allySets'),
        MelFids('XNAM','friendSets'),
        MelFids('YNAM','enemySets'),
        MelFids('LNAM','locationSets'),
        MelFids('GNAM','battleSets'),
        MelFid('RNAM','conditionalFaction'),
        MelUInt32('FNAM', 'fnam'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAmef(MelRecord):
    """Ammo Effect."""
    classType = 'AMEF'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelStruct('DATA','2If','type','operation','value'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAmmo(MelRecord):
    """Ammunition."""
    classType = 'AMMO'

    _flags = Flags(0, Flags.getNames('notNormalWeapon','nonPlayable'))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('DATA','fB3siB','speed',(_flags,'flags',0),('ammoData1',null3),
                  'value','clipRounds'),
        MelTruncatedStruct('DAT2', '2IfIf', 'projPerShot',
                           (FID, 'projectile', 0), 'weight',
                           (FID, 'consumedAmmo'), 'consumedPercentage',
                           old_versions={'2If'}),
        MelString('ONAM','shortName'),
        MelString('QNAM','abbrev'),
        MelFids('RCIL','effects'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArma(MelRecord):
    """Armor Addon."""
    classType = 'ARMA'

    _flags = MelBipedFlags(0, Flags.getNames())
    _dnamFlags = Flags(0, Flags.getNames(
        (0,'modulatesVoice'),
    ))
    _generalFlags = Flags(0, Flags.getNames(
        ( 2,'hasBackpack'),
        ( 3,'medium'),
        (5,'powerArmor'),
        (6,'notPlayable'),
        (7,'heavyArmor')
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelStruct('BMDT','=2I',(_flags,'bipedFlags',0),(_generalFlags,'generalFlags',0)),
        MelModel('maleBody'),
        MelModel('maleWorld',2),
        MelIcons('maleIconPath', 'maleSmallIconPath'),
        MelModel('femaleBody',3),
        MelModel('femaleWorld',4),
        MelIcons2(),
        MelSInt32('ETYP', ('etype', -1)),
        MelStruct('DATA','IIf','value','health','weight'),
        MelTruncatedStruct('DNAM', 'hHf4s', 'ar',
                           (_dnamFlags, 'dnamFlags', 0), ('dt', 0.0),
                           ('armaDnam1', null4), old_versions={'hH'}),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArmo(MelRecord):
    """Armor."""
    classType = 'ARMO'

    _flags = MelBipedFlags(0, Flags.getNames())
    _dnamFlags = Flags(0, Flags.getNames(
        (0,'modulatesVoice'),
    ))
    _generalFlags = Flags(0, Flags.getNames(
        (5,'powerArmor'),
        (6,'notPlayable'),
        (7,'heavyArmor')
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelFid('SCRI','script'),
        MelFid('EITM','objectEffect'),
        MelStruct('BMDT','=IB3s',(_flags,'bipedFlags',0),
                  (_generalFlags,'generalFlags',0),('armoBMDT1',null3),),
        MelModel('maleBody'),
        MelModel('maleWorld',2),
        MelIcons('maleIconPath', 'maleSmallIconPath'),
        MelModel('femaleBody',3),
        MelModel('femaleWorld',4),
        MelIcons2(),
        MelString('BMCT','ragdollTemplatePath'),
        MelDestructible(),
        MelFid('REPL','repairList'),
        MelFid('BIPL','bipedModelList'),
        MelSInt32('ETYP', ('etype', -1)),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('DATA','=2if','value','health','weight'),
        MelTruncatedStruct('DNAM', 'hHf4s', 'ar',
                           (_dnamFlags, 'dnamFlags', 0), ('dt', 0.0),
                           ('armoDnam1', null4), old_versions={'hH'}),
        MelUInt32('BNAM', ('overridesAnimationSound', 0)),
        MelGroups('animationSounds',
            MelStruct('SNAM', 'IB3sI', (FID, 'sound'), 'chance',
                      ('unused1', '\xb7\xe7\x0b'), 'type'),
        ),
        MelFid('TNAM','animationSoundsTemplate'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAspc(MelRecord):
    """Acoustic Space."""
    classType = 'ASPC'

    isKeyedByEid = True # NULL fids are acceptable

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFids('SNAM','soundLooping'),
        MelUInt32('WNAM', 'wallaTrigerCount'),
        MelFid('RDAT','useSoundFromRegion'),
        MelUInt32('ANAM', 'environmentType'),
        MelUInt32('INAM', 'isInterior'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCcrd(MelRecord):
    """Caravan Card."""
    classType = 'CCRD'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelFid('SCRI','script'),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelString('TX00','textureFace'),
        MelString('TX01','textureBack'),
        MelUInt32('INTV', 'card_suit'),
        MelUInt32('INTV', 'card_value'),
        MelUInt32('DATA', 'value'),
    ).with_distributor({
        'INTV': ('card_suit', {
            'INTV': 'card_value',
        }),
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCdck(MelRecord):
    """Caravan Deck."""
    classType = 'CDCK'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelFids('CARD','cards'),
        MelUInt32('DATA', 'count'), # 'Count (broken)' in xEdit - unused?
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCell(MelRecord):
    """Cell."""
    classType = 'CELL'

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

    # 'Force Hide Land' flags
    CellFHLFlags = Flags(0, Flags.getNames(
        (0, 'quad1'),
        (1, 'quad2'),
        (2, 'quad3'),
        (3, 'quad4'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt8('DATA', (cellFlags, 'flags', 0)),
        MelCoordinates('XCLC', '2iI', ('posX', None), ('posY', None),
                       (CellFHLFlags, 'fhlFlags', 0), is_optional=True,
                       old_versions={'2i'}),
        MelTruncatedStruct('XCLL', '=3Bs3Bs3Bs2f2i3f', 'ambientRed',
                           'ambientGreen', 'ambientBlue', ('unused1', null1),
                           'directionalRed', 'directionalGreen',
                           'directionalBlue', ('unused2', null1), 'fogRed',
                           'fogGreen', 'fogBlue', ('unused3', null1),
                           'fogNear', 'fogFar', 'directionalXY',
                           'directionalZ', 'directionalFade', 'fogClip',
                           'fogPower', is_optional=True,
                           old_versions={'3Bs3Bs3Bs2f2i2f'}),
        MelBase('IMPF','footstepMaterials'), #--todo rewrite specific class.
        MelFid('LTMP','lightTemplate'),
        MelOptUInt32('LNAM', (inheritFlags, 'lightInheritFlags', 0)),
        # GECK default for water is -2147483648, but by setting default here to
        # -2147483649, we force the Bashed Patch to retain the value of the
        # last mod.
        MelOptFloat('XCLW', ('waterHeight', -2147483649)),
        MelString('XNAM','waterNoiseTexture'),
        MelFidList('XCLR','regions'),
        MelOptUInt8('XCMT', 'xcmt_p'),
        MelFid('XCIM','imageSpace'),
        MelOptUInt8('XCET', 'xcet_p'),
        MelFid('XEZN','encounterZone'),
        MelFid('XCCM','climate'),
        MelFid('XCWT','water'),
        MelOwnership(),
        MelFid('XCAS','acousticSpace'),
        MelFid('XCMO','music'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreChal(MelRecord):
    """Challenge."""
    classType = 'CHAL'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelFid('SCRI','script'),
        MelString('DESC','description'),
        MelStruct('DATA','4I2s2s4s','type','threshold','flags','interval',
                  'dependOnType1','dependOnType2','dependOnType3'),
        MelFid('SNAM','dependOnType4'),
        MelFid('XNAM','dependOnType5'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreChip(MelRecord):
    """Casino Chip."""
    classType = 'CHIP'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCmny(MelRecord):
    """Caravan Money."""
    classType = 'CMNY'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelUInt32('DATA', 'absoluteValue'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCont(MelRecord):
    """Container."""
    classType = 'CONT'

    _flags = Flags(0,Flags.getNames(None,'respawns'))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelFid('SCRI','script'),
        MelGroups('items',
            MelStruct('CNTO','Ii',(FID,'item',None),('count',1)),
            MelOptStruct('COED','IIf',(FID,'owner',None),(FID,'glob',None),('condition',1.0)),
        ),
        MelDestructible(),
        MelStruct('DATA','=Bf',(_flags,'flags',0),'weight'),
        MelFid('SNAM','soundOpen'),
        MelFid('QNAM','soundClose'),
        MelFid('RNAM','soundRandomLooping'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCsno(MelRecord):
    """Casino."""
    classType = 'CSNO'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelStruct('DATA','2f9I2II','decksPercentBeforeShuffle','BlackjackPayoutRatio',
            'slotReel0','slotReel1','slotReel2','slotReel3','slotReel4','slotReel5','slotReel6',
            'numberOfDecks','maxWinnings',(FID,'currency'),(FID,'casinoWinningQuest'),'flags'),
        MelGroups('chipModels',
            MelString('MODL','model')
        ),
        MelString('MOD2','slotMachineModel'),
        MelString('MOD3','blackjackTableModel'),
        MelString('MODT','extraBlackjackTableModel'),
        MelString('MOD4','rouletteTableModel'),
        MelGroups('slotReelTextures',
            MelIcon('texture'),
        ),
        MelGroups('blackjackDecks',
            MelIco2('texture'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCsty(MelRecord):
    """Combat Style."""
    classType = 'CSTY'

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
        MelOptStruct('CSTD', '2B2s8f2B2s3fB3s2f5B3s2fH2s2B2sf','dodgeChance',
                    'lrChance',('unused1',null2),'lrTimerMin','lrTimerMax',
                    'forTimerMin','forTimerMax','backTimerMin','backTimerMax',
                    'idleTimerMin','idleTimerMax','blkChance','atkChance',
                    ('unused2',null2),'atkBRecoil','atkBunc','atkBh2h',
                    'pAtkChance',('unused3',null3),'pAtkBRecoil','pAtkBUnc',
                    'pAtkNormal','pAtkFor','pAtkBack','pAtkL','pAtkR',
                    ('unused4',null3),'holdTimerMin','holdTimerMax',
                    (_flagsA,'flagsA'),('unused5',null2),'acroDodge',
                    ('rushChance',25),('unused6',null3),('rushMult',1.0),),
        MelOptStruct('CSAD', '21f', 'dodgeFMult', 'dodgeFBase', 'encSBase', 'encSMult',
                     'dodgeAtkMult', 'dodgeNAtkMult', 'dodgeBAtkMult', 'dodgeBNAtkMult',
                     'dodgeFAtkMult', 'dodgeFNAtkMult', 'blockMult', 'blockBase',
                     'blockAtkMult', 'blockNAtkMult', 'atkMult','atkBase', 'atkAtkMult',
                     'atkNAtkMult', 'atkBlockMult', 'pAtkFBase', 'pAtkFMult'),
        MelOptStruct('CSSD', '9f4sI5f', 'coverSearchRadius', 'takeCoverChance',
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
    classType = 'DEHY'

    melSet = MelSet(
        MelEdid(),
        MelStruct('DATA','2I','trigerThreshold',(FID,'actorEffect')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDial(brec.MreDial):
    """Dialogue."""
    _DialFlags = Flags(0, Flags.getNames('rumors', 'toplevel', ))

    melSet = MelSet(
        MelEdid(),
        MelFid('INFC','bare_infc_p'),
        MelFid('INFX','bare_infx_p'),
        MelGroups('quests',
            MelFid('QSTI','quest'),
            MelGroups('unknown',
                MelFid('INFC','infc_p'),
                MelBase('INFX','infx_p'),
            ),
        ),
        MelFull(),
        MelFloat('PNAM', 'priority'),
        MelString('TDUM','tdum_p'),
        MelTruncatedStruct('DATA', '2B', 'dialType',
                           (_DialFlags, 'dialFlags', 0), old_versions={'B'}),
    ).with_distributor({
        'INFC': 'bare_infc_p',
        'INFX': 'bare_infx_p',
        'QSTI': {
            'INFC|INFX': 'quests',
        }
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDobj(MelRecord):
    """Default Object Manager."""
    classType = 'DOBJ'

    melSet = MelSet(
        MelEdid(),
        MelStruct('DATA','34I',(FID,'stimpack'),(FID,'superStimpack'),(FID,'radX'),(FID,'radAway'),
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
class MreEnch(MelRecord,MreHasEffects):
    """Object Effect."""
    classType = 'ENCH'

    _flags = Flags(0, Flags.getNames('noAutoCalc','autoCalculate','hideEffect'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelStruct('ENIT','3IB3s','itemType','chargeAmount','enchantCost',
                  (_flags,'flags',0),('unused1',null3)),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFact(MelRecord):
    """Faction."""
    classType = 'FACT'

    _flags = Flags(0, Flags.getNames('hiddenFromPC','evil','specialCombat'))
    _flags2 = Flags(0, Flags.getNames('trackCrime','allowSell',))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelGroups('relations',
            MelStruct('XNAM', 'IiI', (FID, 'faction'), 'mod',
                      'groupCombatReaction'),
        ),
        MelTruncatedStruct('DATA', '2B2s', (_flags, 'flags', 0), 'flagsFact',
                           ('unknown', null2), old_versions={'2B', 'B'}),
        MelOptFloat('CNAM', ('crimeGoldMultiplier', None)),
        MelGroups('ranks',
            MelSInt32('RNAM', 'rank'),
            MelString('MNAM','male'),
            MelString('FNAM','female'),
            MelString('INAM','insigniaPath')
        ),
        MelOptFid('WMI1', 'reputation', None),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Marker for organization please don't remove ---------------------------------
# GLOB ------------------------------------------------------------------------
# Defined in brec.py as class MreGlob(MelRecord) ------------------------------
#------------------------------------------------------------------------------
class MreGmst(MreGmstBase):
    """Game Setting."""
    isKeyedByEid = True # NULL fids are acceptable.

#------------------------------------------------------------------------------
class MreHdpt(MelRecord):
    """Head Part."""
    classType = 'HDPT'

    _flags = Flags(0, Flags.getNames('playable',))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelUInt8('DATA', (_flags, 'flags')),
        MelFids('HNAM','extraParts'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreHung(MelRecord):
    """Hunger Stage."""
    classType = 'HUNG'

    melSet = MelSet(
        MelEdid(),
        MelStruct('DATA','2I','trigerThreshold',(FID,'actorEffect')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreImad(MelRecord):
    """Image Space Adapter."""
    classType = 'IMAD'

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
        MelStruct('DNAM', 'If49I2f8I', (_ImadAnimatableFlags, 'aniFlags', 0),
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
        MelValueInterpolator('BNAM', 'blurRadiusInterp'),
        MelValueInterpolator('VNAM', 'doubleVisionStrengthInterp'),
        MelColorInterpolator('TNAM', 'tintColorInterp'),
        MelColorInterpolator('NAM3', 'fadeColorInterp'),
        MelValueInterpolator('RNAM', 'radialBlurStrengthInterp'),
        MelValueInterpolator('SNAM', 'radialBlurRampUpInterp'),
        MelValueInterpolator('UNAM', 'radialBlurStartInterp'),
        MelValueInterpolator('NAM1', 'radialBlurRampDownInterp'),
        MelValueInterpolator('NAM2', 'radialBlurDownStartInterp'),
        MelValueInterpolator('WNAM', 'dofStrengthInterp'),
        MelValueInterpolator('XNAM', 'dofDistanceInterp'),
        MelValueInterpolator('YNAM', 'dofRangeInterp'),
        MelValueInterpolator('NAM4', 'motionBlurStrengthInterp'),
        MelValueInterpolator('\x00IAD', 'eyeAdaptSpeedMultInterp'),
        MelValueInterpolator('\x40IAD', 'eyeAdaptSpeedAddInterp'),
        MelValueInterpolator('\x01IAD', 'bloomBlurRadiusMultInterp'),
        MelValueInterpolator('\x41IAD', 'bloomBlurRadiusAddInterp'),
        MelValueInterpolator('\x02IAD', 'bloomThresholdMultInterp'),
        MelValueInterpolator('\x42IAD', 'bloomThresholdAddInterp'),
        MelValueInterpolator('\x03IAD', 'bloomScaleMultInterp'),
        MelValueInterpolator('\x43IAD', 'bloomScaleAddInterp'),
        MelValueInterpolator('\x04IAD', 'targetLumMinMultInterp'),
        MelValueInterpolator('\x44IAD', 'targetLumMinAddInterp'),
        MelValueInterpolator('\x05IAD', 'targetLumMaxMultInterp'),
        MelValueInterpolator('\x45IAD', 'targetLumMaxAddInterp'),
        MelValueInterpolator('\x06IAD', 'sunlightScaleMultInterp'),
        MelValueInterpolator('\x46IAD', 'sunlightScaleAddInterp'),
        MelValueInterpolator('\x07IAD', 'skyScaleMultInterp'),
        MelValueInterpolator('\x47IAD', 'skyScaleAddInterp'),
        MelValueInterpolator('\x08IAD', 'lumRampNoTexMultInterp'),
        MelValueInterpolator('\x48IAD', 'lumRampNoTexAddInterp'),
        MelValueInterpolator('\x09IAD', 'lumRampMinMultInterp'),
        MelValueInterpolator('\x49IAD', 'lumRampMinAddInterp'),
        MelValueInterpolator('\x0AIAD', 'lumRampMaxMultInterp'),
        MelValueInterpolator('\x4AIAD', 'lumRampMaxAddInterp'),
        MelValueInterpolator('\x0BIAD', 'sunlightDimmerMultInterp'),
        MelValueInterpolator('\x4BIAD', 'sunlightDimmerAddInterp'),
        MelValueInterpolator('\x0CIAD', 'grassDimmerMultInterp'),
        MelValueInterpolator('\x4CIAD', 'grassDimmerAddInterp'),
        MelValueInterpolator('\x0DIAD', 'treeDimmerMultInterp'),
        MelValueInterpolator('\x4DIAD', 'treeDimmerAddInterp'),
        MelValueInterpolator('\x0EIAD', 'blurRadiusMultInterp'),
        MelValueInterpolator('\x4EIAD', 'blurRadiusAddInterp'),
        MelValueInterpolator('\x0FIAD', 'alphaMultInteriorMultInterp'),
        MelValueInterpolator('\x4FIAD', 'alphaMultInteriorAddInterp'),
        MelValueInterpolator('\x10IAD', 'alphaMultExteriorMultInterp'),
        MelValueInterpolator('\x50IAD', 'alphaMultExteriorAddInterp'),
        MelValueInterpolator('\x11IAD', 'saturationMultInterp'),
        MelValueInterpolator('\x51IAD', 'saturationAddInterp'),
        MelValueInterpolator('\x12IAD', 'contrastMultInterp'),
        MelValueInterpolator('\x52IAD', 'contrastAddInterp'),
        MelValueInterpolator('\x13IAD', 'contrastAvgMultInterp'),
        MelValueInterpolator('\x53IAD', 'contrastAvgAddInterp'),
        MelValueInterpolator('\x14IAD', 'brightnessMultInterp'),
        MelValueInterpolator('\x54IAD', 'brightnessAddInterp'),
        MelFid('RDSD', 'soundIntro'),
        MelFid('RDSI', 'soundOutro'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreImod(MelRecord):
    """Item Mod."""
    classType = 'IMOD'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelFid('SCRI','script'),
        MelString('DESC','description'),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('DATA','If','value','weight'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreInfo(MelRecord):
    """Dialog Response."""
    classType = 'INFO'

    _flags = Flags(0,Flags.getNames(
        'goodbye','random','sayOnce','runImmediately','infoRefusal','randomEnd',
        'runForRumors','speechChallenge',))
    _flags2 = Flags(0,Flags.getNames(
        'sayOnceADay','alwaysDarken',None,None,'lowIntelligence','highIntelligence',))

    melSet = MelSet(
        MelTruncatedStruct('DATA', '4B', 'dialType', 'nextSpeaker',
                           (_flags, 'flags'), (_flags2, 'flagsInfo'),
                           old_versions={'2B'}),
        MelFid('QSTI','quests'),
        MelFid('TPIC','topic'),
        MelFid('PNAM','prevInfo'),
        MelFids('NAME','addTopics'),
        MelGroups('responses',
            MelStruct('TRDT','Ii4sB3sIB3s','emotionType','emotionValue',('unused1',null4),'responseNum',('unused2','\xcd\xcd\xcd'),
                      (FID,'sound'),'flags',('unused3','\xcd\xcd\xcd')),
            MelString('NAM1','responseText'),
            MelString('NAM2','actorNotes'),
            MelString('NAM3','edits'),
            MelFid('SNAM','speakerAnimation'),
            MelFid('LNAM','listenerAnimation'),
        ),
        MelConditions(),
        MelFids('TCLT','choices'),
        MelFids('TCLF','linksFrom'),
        MelFids('TCFU','tcfu_p'),
        MelGroup('scriptBegin',
            MelEmbeddedScript(),
        ),
        MelGroup('scriptEnd',
            MelBase('NEXT','marker'),
            MelEmbeddedScript(),
        ),
        MelFid('SNDD','sndd_p'),
        MelString('RNAM','prompt'),
        MelFid('ANAM','speaker'),
        MelFid('KNAM','acterValuePeak'),
        MelUInt32('DNAM', 'speechChallenge')
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIpct(MelRecord):
    """Impact."""
    classType = 'IPCT'

    DecalDataFlags = Flags(0, Flags.getNames(
            (0, 'parallax'),
            (0, 'alphaBlending'),
            (0, 'alphaTesting'),
            (0, 'noSubtextures'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelStruct('DATA','fIffII','effectDuration','effectOrientation',
                  'angleThreshold','placementRadius','soundLevel','flags'),
        MelOptStruct('DODT','7fBB2s3Bs','minWidth','maxWidth','minHeight',
                     'maxHeight','depth','shininess','parallaxScale',
                     'parallaxPasses',(DecalDataFlags,'decalFlags',0),
                     ('unused1',null2),'red','green','blue',('unused2',null1)),
        MelFid('DNAM','textureSet'),
        MelFid('SNAM','sound1'),
        MelFid('NAM1','sound2'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreKeym(MelRecord):
    """Key."""
    classType = 'KEYM'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('DATA','if','value','weight'),
        MelFid('RNAM','soundRandomLooping'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLigh(MelRecord):
    """Light."""
    classType = 'LIGH'

    _flags = Flags(0, Flags.getNames('dynamic','canTake','negative','flickers',
        'unk1','offByDefault','flickerSlow','pulse','pulseSlow','spotLight','spotShadow'))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelFull(),
        MelIcons(),
        MelStruct('DATA','iI3BsI2fIf','duration','radius','red','green','blue',
                  ('unused1',null1),(_flags,'flags',0),'falloff','fov','value',
                  'weight'),
        MelOptFloat('FNAM', ('fade', None)),
        MelFid('SNAM','sound'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLscr(MelRecord):
    """Load Screen."""
    classType = 'LSCR'

    melSet = MelSet(
        MelEdid(),
        MelIcon(),
        MelString('DESC','text'),
        MelGroups('locations',
            MelStruct('LNAM', '2I2h', (FID, 'direct'), (FID, 'indirect'),
                      'gridy', 'gridx'),
        ),
        MelFid('WMI1','loadScreenType'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLsct(MelRecord):
    """Load Screen Type."""
    classType = 'LSCT'

    melSet = MelSet(
        MelEdid(),
        MelStruct('DATA','5IfI3fI20sI3f4sI','type','data1X','data1Y','data1Width',
                         'data1Height','data1Orientation',
            'data1Font','data1ColorR','data1ColorG','data1ColorB','data1Align','unknown1',
            'data2Font','data2ColorR','data2ColorG','data2ColorB','unknown2','stats'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMisc(MelRecord):
    """Misc. Item."""
    classType = 'MISC'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('DATA','if','value','weight'),
        MelFid('RNAM','soundRandomLooping'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMset(MelRecord):
    """Media Set."""
    classType = 'MSET'

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
        MelUInt32('NAM1', 'type'),
        MelString('NAM2','nam2'),
        MelString('NAM3','nam3'),
        MelString('NAM4','nam4'),
        MelString('NAM5','nam5'),
        MelString('NAM6','nam6'),
        MelString('NAM7','nam7'),
        MelFloat('NAM8', 'nam8'),
        MelFloat('NAM9', 'nam9'),
        MelFloat('NAM0', 'nam0'),
        MelFloat('ANAM', 'anam'),
        MelFloat('BNAM', 'bnam'),
        MelFloat('CNAM', 'cnam'),
        MelFloat('JNAM', 'jnam'),
        MelFloat('KNAM', 'knam'),
        MelFloat('LNAM', 'lnam'),
        MelFloat('MNAM', 'mnam'),
        MelFloat('NNAM', 'nnam'),
        MelFloat('ONAM', 'onam'),
        MelFloat('PNAM', (_flags, 'enableFlags')),
        MelFloat('DNAM', 'dnam'),
        MelFloat('ENAM', 'enam'),
        MelFloat('FNAM', 'fnam'),
        MelFloat('GNAM', 'gnam'),
        MelOptFid('HNAM', 'hnam'),
        MelOptFid('INAM', 'inam'),
        MelBase('DATA','data'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMusc(MelRecord):
    """Music Type."""
    classType = 'MUSC'

    melSet = MelSet(
        MelEdid(),
        MelString('FNAM','filename'),
        MelFloat('ANAM', 'dB'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MrePgre(MelRecord):
    """Placed Grenade."""
    classType = 'PGRE'

    _flags = Flags(0, Flags.getNames('oppositeParent'))
    _watertypeFlags = Flags(0, Flags.getNames('reflection','refraction'))

    melSet = MelSet(
        MelEdid(),
        MelFid('NAME','base'),
        MelFid('XEZN','encounterZone'),
        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelGroup('patrolData',
            MelFloat('XPRD', 'idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelEmbeddedScript(),
            MelFid('TNAM','topic'),
        ),
        MelOwnership(),
        MelSInt32('XCNT', 'count'),
        MelFloat('XRDS', 'radius',),
        MelFloat('XHLP', 'health',),
        MelGroups('reflectedRefractedBy',
            MelStruct('XPWR','2I',(FID,'waterReference'),(_watertypeFlags,'waterFlags',0),),
        ),
        MelGroups('linkedDecals',
            MelStruct('XDCR', '2I', (FID, 'reference'), 'unknown'),
        ),
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelUInt8('XAPD', 'flags'),
            MelGroups('activateParentRefs',
                MelStruct('XAPR', 'If', (FID, 'reference'), 'delay'),
            ),
        ),
        MelString('XATO','activationPrompt'),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),('unused1',null3)),
        MelOptFid('XEMI', 'emittance'),
        MelFid('XMBR','multiboundReference'),
        MelBase('XIBS','ignoredBySandbox'),
        MelOptFloat('XSCL', ('scale', 1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MrePmis(MelRecord):
    """Placed Missile."""
    classType = 'PMIS'

    _flags = Flags(0, Flags.getNames('oppositeParent'))
    _watertypeFlags = Flags(0, Flags.getNames('reflection','refraction'))

    melSet = MelSet(
        MelEdid(),
        MelFid('NAME','base'),
        MelFid('XEZN','encounterZone'),
        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelGroup('patrolData',
            MelFloat('XPRD', 'idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelEmbeddedScript(),
            MelFid('TNAM','topic'),
        ),
        MelOwnership(),
        MelSInt32('XCNT', 'count'),
        MelFloat('XRDS', 'radius',),
        MelFloat('XHLP', 'health',),
        MelGroups('reflectedRefractedBy',
            MelStruct('XPWR','2I',(FID,'waterReference'),(_watertypeFlags,'waterFlags',0),),
        ),
        MelGroups('linkedDecals',
            MelStruct('XDCR', '2I', (FID, 'reference'), 'unknown'),
        ),
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelUInt8('XAPD', 'flags'),
            MelGroups('activateParentRefs',
                MelStruct('XAPR', 'If', (FID, 'reference'), 'delay'),
            ),
        ),
        MelString('XATO','activationPrompt'),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),('unused1',null3)),
        MelOptFid('XEMI', 'emittance'),
        MelFid('XMBR','multiboundReference'),
        MelBase('XIBS','ignoredBySandbox'),
        MelOptFloat('XSCL', ('scale', 1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreProj(MelRecord):
    """Projectile."""
    classType = 'PROJ'

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
            'DATA', '2H3f2I3f2I3f3I4f', (_flags,'flags'), 'type',
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
        MelString('NAM1','muzzleFlashPath'),
        MelBase('NAM2','_nam2'),
        MelUInt32('VNAM', 'soundLevel'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRcct(MelRecord):
    """Recipe Category."""
    classType = 'RCCT'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt8('DATA', 'flags'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRcpe(MelRecord):
    """Recipe."""
    classType = 'RCPE'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelConditions(),
        MelStruct('DATA','4I','skill','level',(FID,'category'),(FID,'subCategory')),
        MelGroups('ingredients',
            MelFid('RCIL','item'),
            MelUInt32('RCQY', 'quantity'),
        ),
        MelGroups('outputs',
            MelFid('RCOD','item'),
            MelUInt32('RCQY', 'quantity'),
        ),
    ).with_distributor({
        'RCIL': {
            'RCQY': 'ingredients',
        },
        'RCOD': {
            'RCQY': 'outputs',
        },
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRefr(MelRecord):
    """Placed Object"""
    classType = 'REFR'

    _marker_flags = Flags(0, Flags.getNames(
        'visible',
        'can_travel_to',
        'show_all_hidden',
    ))
    _parentFlags = Flags(0, Flags.getNames('oppositeParent'))
    _actFlags = Flags(0, Flags.getNames('useDefault', 'activate','open','openByDefault'))
    _lockFlags = Flags(0, Flags.getNames(None, None, 'leveledLock'))
    _destinationFlags = Flags(0, Flags.getNames('noAlarm'))
    reflectFlags = Flags(0, Flags.getNames('reflection', 'refraction'))

    melSet = MelSet(
        MelEdid(),
        MelOptStruct('RCLR','8B','referenceStartColorRed','referenceStartColorGreen','referenceStartColorBlue',('referenceColorUnused1',null1),
                     'referenceEndColorRed','referenceEndColorGreen','referenceEndColorBlue',('referenceColorUnused2',null1)),
        MelFid('NAME','base'),
        MelFid('XEZN','encounterZone'),
        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelOptStruct('XPRM','3f3IfI','primitiveBoundX','primitiveBoundY','primitiveBoundX',
                     'primitiveColorRed','primitiveColorGreen','primitiveColorBlue','primitiveUnknown','primitiveType'),
        MelOptUInt32('XTRI', 'collisionLayer'),
        MelBase('XMBP','multiboundPrimitiveMarker'),
        MelOptStruct('XMBO','3f','boundHalfExtentsX','boundHalfExtentsY','boundHalfExtentsZ'),
        MelOptStruct('XTEL','I6fI',(FID,'destinationFid'),'destinationPosX','destinationPosY',
            'destinationPosZ','destinationRotX','destinationRotY','destinationRotZ',(_destinationFlags,'destinationFlags')),
        MelGroup('map_marker',
            MelBase('XMRK', 'marker_data'),
            MelOptUInt8('FNAM', (_marker_flags, 'marker_flags')),
            MelFull(),
            MelOptStruct('TNAM', 'Bs', 'marker_type', 'unused1'),
            MelFid('WMI1', 'marker_reputation'),
        ),
        MelGroup('audioData',
            MelBase('MMRK','audioMarker'),
            MelBase('FULL','full_p'),
            MelFid('CNAM','audioLocation'),
            MelBase('BNAM','bnam_p'),
            MelBase('MNAM','mnam_p'),
            MelBase('NNAM','nnam_p'),
        ),
        MelBase('XSRF','xsrf_p'),
        MelBase('XSRD','xsrd_p'),
        MelFid('XTRG','targetId'),
        MelOptSInt32('XLCM', ('levelMod', None)),
        MelGroup('patrolData',
            MelFloat('XPRD', 'idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelEmbeddedScript(),
            MelFid('TNAM','topic'),
        ),
        MelOptStruct('XRDO','fIfI','rangeRadius','broadcastRangeType','staticPercentage',(FID,'positionReference')),
        MelOwnership(),
        ##: I dropped special handling here, looks like a regular truncated
        # record to me - but no way to test since we don't load this yet
        MelTruncatedStruct(
            'XLOC', 'B3sI4sB3s4s', 'lockLevel', ('unused1',null3),
            (FID, 'lockKey'), ('unused2', null4), (_lockFlags, 'lockFlags'),
            ('unused3', null3), ('unused4', null4), is_optional=True,
            old_versions={'B3sI4s'}),
        MelOptSInt32('XCNT', 'count'),
        MelOptFloat('XRDS', 'radius'),
        MelOptFloat('XHLP', 'health'),
        MelOptFloat('XRAD', 'radiation'),
        MelOptFloat('XCHG', ('charge', None)),
        MelGroup('ammo',
            MelFid('XAMT','type'),
            MelUInt32('XAMC', 'count'),
        ),
        MelGroups('reflectedByWaters',
            MelStruct('XPWR', '2I', (FID, 'reference'),
                      (reflectFlags, 'reflection_type')),
        ),
        MelFids('XLTW','litWaters'),
        MelGroups('linkedDecals',
            MelStruct('XDCR', '2I', (FID, 'reference'), 'unknown'),
        ),
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelUInt8('XAPD', 'flags'),
            MelGroups('activateParentRefs',
                MelStruct('XAPR', 'If', (FID, 'reference'), 'delay'),
            ),
        ),
        MelString('XATO','activationPrompt'),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_parentFlags,'parentFlags'),('unused6',null3)),
        MelOptFid('XEMI', 'emittance'),
        MelFid('XMBR','multiboundReference'),
        MelOptUInt32('XACT', (_actFlags, 'actFlags', 0)),
        MelBase('ONAM','onam_p'),
        MelBase('XIBS','ignoredBySandbox'),
        MelOptStruct('XNDP','2I',(FID,'navMesh'),'unknown'),
        MelOptStruct('XPOD','II',(FID,'portalDataRoom0'),(FID,'portalDataRoom1')),
        MelOptStruct('XPTL','9f','portalWidth','portalHeight','portalPosX','portalPosY','portalPosZ',
                     'portalRot1','portalRot2','portalRot3','portalRot4'),
        MelBase('XSED','speedTreeSeed'),
        ####SpeedTree Seed, if it's a single byte then it's an offset into the list of seed values in the TREE record
        ####if it's 4 byte it's the seed value directly.
        MelGroup('roomData',
            MelStruct('XRMR','H2s','linkedRoomsCount','unknown'),
            MelFids('XLRM','linkedRoom'),
        ),
        MelOptStruct('XOCP','9f','occlusionPlaneWidth','occlusionPlaneHeight','occlusionPlanePosX','occlusionPlanePosY','occlusionPlanePosZ',
                     'occlusionPlaneRot1','occlusionPlaneRot2','occlusionPlaneRot3','occlusionPlaneRot4'),
        MelOptStruct('XORD','4I',(FID,'linkedOcclusionPlane0'),(FID,'linkedOcclusionPlane1'),(FID,'linkedOcclusionPlane2'),(FID,'linkedOcclusionPlane3')),
        MelOptStruct('XLOD','3f',('lod1',None),('lod2',None),('lod3',None)),
        MelOptFloat('XSCL', ('scale', 1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRegn(MelRecord):
    """Region."""
    classType = 'REGN'

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
        MelStruct('RCLR','3Bs','mapRed','mapBlue','mapGreen',('unused1',null1)),
        MelFid('WNAM','worldspace'),
        MelGroups('areas',
            MelUInt32('RPLI', 'edgeFalloff'),
            MelArray('points',
                MelStruct('RPLD', '2f', 'posX', 'posY'),
            ),
        ),
        MelGroups('entries',
            MelStruct('RDAT', 'I2B2s', 'entryType', (rdatFlags, 'flags'),
                      'priority', ('unused1', null2)),
            MelRegnEntrySubrecord(2, MelArray('objects',
                MelStruct(
                    'RDOT', 'IH2sf4B2H5f3H2s4s', (FID, 'objectId'),
                    'parentIndex', ('unk1', null2), 'density', 'clustering',
                    'minSlope', 'maxSlope', (obflags, 'flags'),
                    'radiusWRTParent', 'radius', 'minHeight', 'maxHeight',
                    'sink', 'sinkVar', 'sizeVar', 'angleVarX', 'angleVarY',
                    'angleVarZ', ('unk2', null2), ('unk3', null4)),
            )),
            MelRegnEntrySubrecord(4, MelString('RDMP', 'mapName')),
            MelRegnEntrySubrecord(6, MelArray('grasses',
                MelStruct('RDGS', 'I4s', (FID, 'grass'), ('unknown', null4)),
            )),
            MelRegnEntrySubrecord(7, MelOptUInt32('RDMD', 'musicType')),
            MelRegnEntrySubrecord(7, MelFid('RDMO', 'music')),
            MelRegnEntrySubrecord(7, MelFid('RDSI', 'incidentalMediaSet')),
            MelRegnEntrySubrecord(7, MelFids('RDSB', 'battleMediaSets')),
            MelRegnEntrySubrecord(7, MelArray('sounds',
                MelStruct('RDSD', '3I', (FID, 'sound'), (sdflags, 'flags'),
                          'chance'),
            )),
            MelRegnEntrySubrecord(3, MelArray('weatherTypes',
                MelStruct('RDWT', '3I', (FID, 'weather', None), 'chance',
                          (FID, 'global', None)),
            )),
            MelRegnEntrySubrecord(8, MelFidList('RDID', 'imposters')),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRepu(MelRecord):
    """Reputation."""
    classType = 'REPU'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelIcons(),
        MelFloat('DATA', 'value'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSlpd(MelRecord):
    """Sleep Deprivation Stage."""
    classType = 'SLPD'

    melSet = MelSet(
        MelEdid(),
        MelStruct('DATA','2I','trigerThreshold',(FID,'actorEffect')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSoun(MelRecord):
    """Sound."""
    classType = 'SOUN'

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
        MelString('FNAM','soundFile'),
        MelUInt8('RNAM', 'random_chance'),
        MelStruct('SNDD', '2BbsIh2B6h3i', 'minDist', 'maxDist', 'freqAdj',
                  ('unusedSndd', null1), (_flags, 'flags'), 'staticAtten',
                  'stopTime', 'startTime', 'point0', 'point1', 'point2',
                  'point3', 'point4', 'reverb', 'priority', 'xLoc', 'yLoc'),
        # These are the older format - read them, but only write out SNDD
        MelReadOnly(
            MelStruct('SNDX', '2BbsIh2B', 'minDist', 'maxDist', 'freqAdj',
                      ('unusedSndd', null1), (_flags, 'flags'), 'staticAtten',
                      'stopTime', 'startTime'),
            MelStruct('ANAM', '5h', 'point0', 'point1', 'point2', 'point3',
                      'point4'),
            MelSInt16('GNAM', 'reverb'),
            MelSInt32('HNAM', 'priority'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreStat(MelRecord):
    """Static."""
    classType = 'STAT'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelSInt8('BRUS', ('passthroughSound', -1)),
        MelFid('RNAM','soundRandomLooping'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreTact(MelRecord):
    """Talking Activator."""
    classType = 'TACT'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel('model'),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelFid('SNAM','sound'),
        MelFid('VNAM','voiceType'),
        MelFid('INAM','radioTemplate'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWeap(MelRecord):
    """Weapon."""
    classType = 'WEAP'

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
        MelModel('model'),
        MelIcons(),
        MelFid('SCRI','script'),
        MelFid('EITM','objectEffect'),
        MelOptUInt16('EAMT', 'objectEffectPoints'),
        MelFid('NAM0','ammo'),
        MelDestructible(),
        MelFid('REPL','repairList'),
        MelSInt32('ETYP', ('etype', -1)),
        MelFid('BIPL','bipedModelList'),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelModel('shellCasingModel',2),
        MelModel('scopeModel', 3, with_facegen_flags=False),
        MelFid('EFSD','scopeEffect'),
        MelModel('worldModel',4),
        MelGroup('modelWithMods',
            MelString('MWD1','mod1Path'),
            MelString('MWD2','mod2Path'),
            MelString('MWD3','mod1and2Path'),
            MelString('MWD4','mod3Path'),
            MelString('MWD5','mod1and3Path'),
            MelString('MWD6','mod2and3Path'),
            MelString('MWD7','mod1and2and3Path'),
        ),
        MelString('VANM','vatsAttackName'),
        MelString('NNAM','embeddedWeaponNode'),
        MelFid('INAM','impactDataset'),
        MelFid('WNAM','firstPersonModel'),
        MelGroup('firstPersonModelWithMods',
            MelFid('WNM1','mod1Path'),
            MelFid('WNM2','mod2Path'),
            MelFid('WNM3','mod1and2Path'),
            MelFid('WNM4','mod3Path'),
            MelFid('WNM5','mod1and3Path'),
            MelFid('WNM6','mod2and3Path'),
            MelFid('WNM7','mod1and2and3Path'),
        ),
        MelGroup('weaponMods',
            MelFid('WMI1','mod1'),
            MelFid('WMI2','mod2'),
            MelFid('WMI3','mod3'),
        ),
        MelFids('SNAM','soundGunShot3D'),
        MelFid('XNAM','soundGunShot2D'),
        MelFid('NAM7','soundGunShot3DLooping'),
        MelFid('TNAM','soundMeleeSwingGunNoAmmo'),
        MelFid('NAM6','soundBlock'),
        MelFid('UNAM','idleSound',),
        MelFid('NAM9','equipSound',),
        MelFid('NAM8','unequipSound',),
        MelFids('WMS1','soundMod1Shoot3Ds'),
        MelFid('WMS2','soundMod1Shoot2D'),
        MelStruct('DATA','2IfHB','value','health','weight','damage','clipsize'),
        MelTruncatedStruct('DNAM', 'I2f4B5fI4B2f2I11fiI2fi4f3I3f2IsB2s6fI',
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
        MelOptStruct('CRDT','H2sfB3sI',('criticalDamage', 0),('weapCrdt1', null2),
                     ('criticalMultiplier', 0.0),(_cflags,'criticalFlags', 0),
                     ('weapCrdt2', null3),(FID,'criticalEffect', 0),),
        MelTruncatedStruct('VATS', 'I3f2B2s', 'vatsEffect', 'vatsSkill',
                           'vatsDamMult', 'vatsAp', 'vatsSilent',
                           'vatsModReqiured', ('weapVats1', null2),
                           old_versions={'I3f'}),
        MelBase('VNAM','soundLevel'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWthr(MelRecord):
    """Weather."""
    classType = 'WTHR'

    class MelWthrColorsFnv(MelArray):
        """Used twice in WTHR for PNAM and NAM0. Needs to handle older versions
        as well. Can't simply use MelArray because MelTruncatedStruct does not
        have a static_size."""
        # TODO(inf) Rework MelArray - instead of static_size, have a
        #  get_entry_size that receives the total size_ of loadData.
        #  MelTruncatedStruct could override that and make a guess based on its
        #  sizes. If that guess doesn't work, a small override class can be
        #  created by hand
        _new_sizes = {'PNAM': 96, 'NAM0': 240}
        _old_sizes = {'PNAM': 64, 'NAM0': 160}

        def __init__(self, wthr_sub_sig, wthr_attr):
            struct_definition = [
                '3Bs3Bs3Bs3Bs3Bs3Bs', 'riseRed', 'riseGreen', 'riseBlue',
                ('unused1', null1), 'dayRed', 'dayGreen', 'dayBlue',
                ('unused2', null1), 'setRed', 'setGreen', 'setBlue',
                ('unused3', null1), 'nightRed', 'nightGreen', 'nightBlue',
                ('unused4', null1), 'noonRed', 'noonGreen', 'noonBlue',
                ('unused5', null1), 'midnightRed', 'midnightGreen',
                'midnightBlue', ('unused6', null1)
            ]
            MelArray.__init__(self, wthr_attr,
                MelStruct(wthr_sub_sig, *struct_definition),
            )
            self._element_old = MelTruncatedStruct(
                wthr_sub_sig, *struct_definition,
                old_versions={'3Bs3Bs3Bs3Bs'})

        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == self._new_sizes[sub_type]:
                MelArray.loadData(self, record, ins, sub_type, size_, readId)
            elif size_ == self._old_sizes[sub_type]:
                # Copied and adjusted from MelArray. Yuck. See comment below
                # docstring for some ideas for getting rid of this
                append_entry = getattr(record, self.attr).append
                entry_slots = self._element_old.attrs
                entry_size = struct.calcsize('3Bs3Bs3Bs3Bs')
                load_entry = self._element_old.loadData
                for x in xrange(size_ // entry_size):
                    arr_entry = MelObject()
                    append_entry(arr_entry)
                    arr_entry.__slots__ = entry_slots
                    load_entry(arr_entry, ins, sub_type, entry_size, readId)
            else:
                _expected_sizes = (self._new_sizes[sub_type],
                                   self._old_sizes[sub_type])
                raise ModSizeError(ins.inName, readId, _expected_sizes, size_)

    melSet = MelSet(
        MelEdid(),
        MelFid("\x00IAD", 'sunriseImageSpaceModifier'),
        MelFid("\x01IAD", 'dayImageSpaceModifier'),
        MelFid("\x02IAD", 'sunsetImageSpaceModifier'),
        MelFid("\x03IAD", 'nightImageSpaceModifier'),
        MelFid("\x04IAD", 'unknown1ImageSpaceModifier'),
        MelFid("\x05IAD", 'unknown2ImageSpaceModifier'),
        MelString('DNAM','upperLayer'),
        MelString('CNAM','lowerLayer'),
        MelString('ANAM','layer2'),
        MelString('BNAM','layer3'),
        MelModel(),
        MelBase('LNAM','unknown1'),
        MelStruct('ONAM','4B','cloudSpeed0','cloudSpeed1','cloudSpeed3','cloudSpeed4'),
        MelWthrColorsFnv('PNAM', 'cloudColors'),
        MelWthrColorsFnv('NAM0', 'daytimeColors'),
        MelStruct('FNAM','6f','fogDayNear','fogDayFar','fogNightNear','fogNightFar','fogDayPower','fogNightPower'),
        MelBase('INAM', 'unused1', null1 * 304),
        MelStruct('DATA','15B',
            'windSpeed','lowerCloudSpeed','upperCloudSpeed','transDelta',
            'sunGlare','sunDamage','rainFadeIn','rainFadeOut','boltFadeIn',
            'boltFadeOut','boltFrequency','weatherType','boltRed','boltBlue','boltGreen'),
        MelGroups('sounds',
            MelStruct('SNAM', '2I', (FID, 'sound'), 'type'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()
