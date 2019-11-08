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
import struct
# Set MelModel in brec, in this case it's identical to the fallout 3 one
from ..fallout3.records import MelOwnership, MelDestructible, MelBipedFlags, \
    MelEffects, MelConditions, MreHasEffects, MelEmbeddedScript
from ... import brec
from ...bolt import Flags
from ...brec import MelModel # set in Mopy/bash/game/fallout3/records.py
from ...brec import MelRecord, MelStructs, MelGroups, MelStruct, FID, \
    MelGroup, MelString, MelSet, MelFid, MelNull, MelOptStruct, MelFids, \
    MelBase, MelFidList, MelStructA, MreGmstBase, MreHeaderBase, MelUnicode, \
    MelColorInterpolator, MelValueInterpolator, MelRegnEntrySubrecord, \
    MelFloat, MelSInt8, MelSInt32, MelUInt8, MelUInt32, MelOptFid, \
    MelOptFloat, MelOptSInt32, MelOptUInt8, MelOptUInt16, MelOptUInt32, \
    MelBounds, null1, null2, null3, null4
from ...exception import ModSizeError

# Those are unused here, but need be in this file as are accessed via it
from ..fallout3.records import MreNpc ##: used in Oblivion only save code really

#------------------------------------------------------------------------------
# FalloutNV Records -----------------------------------------------------------
#------------------------------------------------------------------------------
class MreHeader(MreHeaderBase):
    """TES4 Record.  File header."""
    classType = 'TES4'

    melSet = MelSet(
        MelStruct('HEDR', 'f2I', ('version', 1.34), 'numRecords',
                  ('nextObject', 0x800)),
        MelBase('OFST','ofst_p',),  #--Obsolete?
        MelBase('DELE','dele_p',),  #--Obsolete?
        MelUnicode('CNAM','author',u'',512),
        MelUnicode('SNAM','description',u'',512),
        MreHeaderBase.MelMasterName('MAST','masters'),
        MelNull('DATA'), # 8 Bytes in Length
        MelFidList('ONAM','overrides'),
        MelBase('SCRN', 'screenshot'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreAchr(MelRecord):
    """Placed NPC."""
    classType = 'ACHR'

    _flags = Flags(0L,Flags.getNames('oppositeParent','popIn'))

    melSet = MelSet(
        MelString('EDID','eid'),
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
        MelStructs('XDCR','II','linkedDecals',(FID,'reference'),'unknown'),
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelUInt8('XAPD', 'flags'),
            MelStructs('XAPR','If','activateParentRefs',(FID,'reference'),'delay')
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

    _flags = Flags(0L,Flags.getNames('oppositeParent','popIn'))

    melSet = MelSet(
        MelString('EDID','eid'),
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
        MelStructs('XDCR','II','linkedDecals',(FID,'reference'),'unknown'),
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelUInt8('XAPD', 'flags'),
            MelStructs('XAPR','If','activateParentRefs',(FID,'reference'),'delay')
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
        MelString('EDID','eid'),
        MelBounds(),
        MelString('FULL','full'),
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
        MelString('EDID','eid'),
        MelString('FULL','full'),
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
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelStruct('DATA','2If','type','operation','value'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAmmo(MelRecord):
    """Ammunition."""
    classType = 'AMMO'

    _flags = Flags(0L,Flags.getNames('notNormalWeapon','nonPlayable'))

    class MelAmmoDat2(MelStruct):
        """Handle older truncated DAT2 for AMMO subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 20:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 12:
                unpacked = ins.unpack('IIf', size_, readId)
            else:
                raise ModSizeError(ins.inName, readId, (20, 12), size_)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('DATA','fB3siB','speed',(_flags,'flags',0L),('ammoData1',null3),
                  'value','clipRounds'),
        MelAmmoDat2('DAT2','IIfIf','projPerShot',(FID,'projectile',0L),'weight',
                    (FID,'consumedAmmo'),'consumedPercentage'),
        MelString('ONAM','shortName'),
        MelString('QNAM','abbrev'),
        MelFids('RCIL','effects'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArma(MelRecord):
    """Armor Addon."""
    classType = 'ARMA'

    _flags = MelBipedFlags(0L,Flags.getNames())
    _dnamFlags = Flags(0L,Flags.getNames(
        (0,'modulatesVoice'),
    ))
    _generalFlags = Flags(0L,Flags.getNames(
        ( 2,'hasBackpack'),
        ( 3,'medium'),
        (5,'powerArmor'),
        (6,'notPlayable'),
        (7,'heavyArmor')
    ))

    class MelArmaDnam(MelStruct):
        """Handle older truncated DNAM for ARMA subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 12:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 4:
                unpacked = ins.unpack('=hH', size_, readId)
            else:
                raise ModSizeError(ins.inName, readId, (12, 4), size_)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelString('FULL','full'),
        MelStruct('BMDT','=2I',(_flags,'bipedFlags',0L),(_generalFlags,'generalFlags',0L)),
        MelModel('maleBody'),
        MelModel('maleWorld',2),
        MelString('ICON','maleIconPath'),
        MelString('MICO','maleSmallIconPath'),
        MelModel('femaleBody',3),
        MelModel('femaleWorld',4),
        MelString('ICO2','femaleIconPath'),
        MelString('MIC2','femaleSmallIconPath'),
        MelSInt32('ETYP', ('etype', -1)),
        MelStruct('DATA','IIf','value','health','weight'),
        MelArmaDnam('DNAM','=hHf4s','ar',(_dnamFlags,'dnamFlags',0L),('dt',0.0),('armaDnam1',null4),),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArmo(MelRecord):
    """Armor."""
    classType = 'ARMO'

    _flags = MelBipedFlags(0L,Flags.getNames())
    _dnamFlags = Flags(0L,Flags.getNames(
        (0,'modulatesVoice'),
    ))
    _generalFlags = Flags(0L,Flags.getNames(
        (5,'powerArmor'),
        (6,'notPlayable'),
        (7,'heavyArmor')
    ))

    class MelArmoDnam(MelStruct):
        """Handle older truncated DNAM for ARMO subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 12:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 4:
                unpacked = ins.unpack('=hH', size_, readId)
            else:
                raise ModSizeError(ins.inName, readId, (12, 4), size_)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelString('FULL','full'),
        MelFid('SCRI','script'),
        MelFid('EITM','objectEffect'),
        MelStruct('BMDT','=IB3s',(_flags,'bipedFlags',0L),
                  (_generalFlags,'generalFlags',0L),('armoBMDT1',null3),),
        MelModel('maleBody'),
        MelModel('maleWorld',2),
        MelString('ICON','maleIconPath'),
        MelString('MICO','maleSmallIconPath'),
        MelModel('femaleBody',3),
        MelModel('femaleWorld',4),
        MelString('ICO2','femaleIconPath'),
        MelString('MIC2','femaleSmallIconPath'),
        MelString('BMCT','ragdollTemplatePath'),
        MelDestructible(),
        MelFid('REPL','repairList'),
        MelFid('BIPL','bipedModelList'),
        MelSInt32('ETYP', ('etype', -1)),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('DATA','=2if','value','health','weight'),
        MelArmoDnam('DNAM','=hHf4s','ar',(_dnamFlags,'dnamFlags',0L),('dt',0.0),('armoDnam1',null4),),
        MelUInt32('BNAM', ('overridesAnimationSound', 0L)),
        MelStructs('SNAM','IB3sI','animationSounds',(FID,'sound'),'chance',('unused','\xb7\xe7\x0b'),'type'),
        MelFid('TNAM','animationSoundsTemplate'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAspc(MelRecord):
    """Acoustic Space."""
    classType = 'ASPC'

    isKeyedByEid = True # NULL fids are acceptable

    melSet = MelSet(
        MelString('EDID','eid'),
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
        MelString('EDID','eid'),
        MelBounds(),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelFid('SCRI','script'),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelString('TX00','textureFace'),
        MelString('TX01','textureBack'),
        # TODO(inf) Ugly, revisit with distributor
        MelStructs('INTV','I','suitAndValue','value'),
        MelUInt32('DATA', 'value'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCdck(MelRecord):
    """Caravan Deck."""
    classType = 'CDCK'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelFids('CARD','cards'),
        MelUInt32('DATA', 'count'), # 'Count (broken)' in xEdit - unused?
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCell(MelRecord):
    """Cell."""
    classType = 'CELL'

    cellFlags = Flags(0L,Flags.getNames((0, 'isInterior'),(1,'hasWater'),(2,'invertFastTravel'),
        (3,'forceHideLand'),(5,'publicPlace'),(6,'handChanged'),(7,'behaveLikeExterior')))
    inheritFlags = Flags(0L,Flags.getNames('ambientColor','directionalColor','fogColor','fogNear','fogFar',
        'directionalRotation','directionalFade','clipDistance','fogPower'))

    class MelCoordinates(MelOptStruct):
        """Handle older truncated XCLC for CELL subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 12:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 8:
                unpacked = ins.unpack('ii',size_,readId)
            else:
                raise ModSizeError(ins.inName, readId, (12, 8), size_)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()

        def dumpData(self,record,out):
            if not record.flags.isInterior:
                MelOptStruct.dumpData(self,record,out)

    class MelCellXcll(MelOptStruct):
        """Handle older truncated XCLL for CELL subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 40:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 36:
                unpacked = ins.unpack('=3Bs3Bs3Bs2f2i2f',size_,readId)
            else:
                raise ModSizeError(ins.inName, readId, (40, 36), size_)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelUInt8('DATA', (cellFlags, 'flags', 0L)),
        MelCoordinates('XCLC','iiI',('posX',None),('posY',None),('forceHideLand',0L)),
        MelCellXcll('XCLL','=3Bs3Bs3Bs2f2i3f','ambientRed','ambientGreen','ambientBlue',
            ('unused1',null1),'directionalRed','directionalGreen','directionalBlue',
            ('unused2',null1),'fogRed','fogGreen','fogBlue',
            ('unused3',null1),'fogNear','fogFar','directionalXY','directionalZ',
            'directionalFade','fogClip','fogPower'),
        MelBase('IMPF','footstepMaterials'), #--todo rewrite specific class.
        MelFid('LTMP','lightTemplate'),
        MelOptUInt32('LNAM', (inheritFlags, 'lightInheritFlags', 0L)),
        #--CS default for water is -2147483648, but by setting default here to -2147483649,
        #  we force the bashed patch to retain the value of the last mod.
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
        MelString('EDID','eid'),
        MelString('FULL','full'),
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
        MelString('EDID','eid'),
        MelBounds(),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
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
        MelString('EDID','eid'),
        MelBounds(),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
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
        MelString('EDID','eid'),
        MelBounds(),
        MelString('FULL','full'),
        MelModel(),
        MelFid('SCRI','script'),
        MelGroups('items',
            MelStruct('CNTO','Ii',(FID,'item',None),('count',1)),
            MelOptStruct('COED','IIf',(FID,'owner',None),(FID,'glob',None),('condition',1.0)),
        ),
        MelDestructible(),
        MelStruct('DATA','=Bf',(_flags,'flags',0L),'weight'),
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
        MelString('EDID','eid'),
        MelString('FULL','full'),
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
            MelString('ICON','texture')
        ),
        MelGroups('blackjackDecks',
            MelString('ICO2','texture')
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCsty(MelRecord):
    """Combat Style."""
    classType = 'CSTY'

    _flagsA = Flags(0L,Flags.getNames(
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
        MelString('EDID','eid'),
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
        MelString('EDID','eid'),
        MelStruct('DATA','2I','trigerThreshold',(FID,'actorEffect')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDial(brec.MreDial):
    """Dialogue."""
    _flags = Flags(0,Flags.getNames('rumors','toplevel',))

    class MelDialData(MelStruct):
        """Handle older truncated DATA for DIAL subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 2:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 1:
                unpacked = ins.unpack('B', size_, readId)
            else:
                raise ModSizeError(ins.inName, readId, (2, 1), size_)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()

    melSet = MelSet(
        MelString('EDID','eid'),
        MelFid('INFC','bare_infc_p'),
        MelFid('INFX','bare_infx_p'),
        MelGroups('quests',
            MelFid('QSTI','quest'),
            MelGroups('unknown',
                MelFid('INFC','infc_p'),
                MelBase('INFX','infx_p'),
            ),
        ),
        MelString('FULL','full'),
        MelFloat('PNAM', 'priority'),
        MelString('TDUM','tdum_p'),
        MelDialData('DATA','BB','dialType',(_flags,'dialFlags',0L)),
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
        MelString('EDID','eid'),
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

    _flags = Flags(0L,Flags.getNames('noAutoCalc','autoCalculate','hideEffect'))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL', 'full'),
        MelStruct('ENIT','3IB3s','itemType','chargeAmount','enchantCost',
                  (_flags,'flags',0L),('unused1',null3)),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFact(MelRecord):
    """Faction."""
    classType = 'FACT'

    _flags = Flags(0L,Flags.getNames('hiddenFromPC','evil','specialCombat'))
    _flags2 = Flags(0L,Flags.getNames('trackCrime','allowSell',))

    class MelFactData(MelStruct):
        """Handle older truncated DATA for FACT subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 4:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 2:
                unpacked = ins.unpack('2B', size_, readId)
            elif size_ == 1:
                unpacked = ins.unpack('B', size_, readId)
            else:
                raise ModSizeError(ins.inName, readId, (4, 2, 1), size_)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelStructs('XNAM','IiI','relations',(FID,'faction'),'mod','groupCombatReaction'),
        MelFactData('DATA','2B2s',(_flags,'flags',0L),'flagsFact',('unknown',null2),),
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

    _flags = Flags(0L,Flags.getNames('playable',))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
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
        MelString('EDID','eid'),
        MelStruct('DATA','2I','trigerThreshold',(FID,'actorEffect')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreImad(MelRecord):
    """Image Space Adapter."""
    classType = 'IMAD'

    _ImadDofFlags = Flags(0L, Flags.getNames(
        (0, 'useTarget'),
    ))
    _ImadAnimatableFlags = Flags(0L, Flags.getNames(
        (0, 'animatable'),
    ))
    _ImadRadialBlurFlags = Flags(0L, Flags.getNames(
        (0, 'useTarget')
    ))

    melSet = MelSet(
        MelString('EDID', 'eid'),
        MelStruct('DNAM', 'If49I2f8I', (_ImadAnimatableFlags, 'aniFlags', 0L),
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
                  (_ImadRadialBlurFlags, 'radialBlurFlags', 0L),
                  'radialBlurCenterX', 'radialBlurCenterY', 'dofStrength',
                  'dofDistance', 'dofRange', (_ImadDofFlags, 'dofFlags', 0L),
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
        MelString('EDID','eid'),
        MelBounds(),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
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

    class MelInfoData(MelStruct):
        """Support older 2 byte version."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ != 2:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            unpacked = ins.unpack('2B', size_, readId)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print (record.dialType,record.flags.getTrueAttrs())

    melSet = MelSet(
        MelInfoData('DATA','HH','dialType','nextSpeaker',(_flags,'flags'),(_flags2,'flagsInfo'),),
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

    DecalDataFlags = Flags(0L,Flags.getNames(
            (0, 'parallax'),
            (0, 'alphaBlending'),
            (0, 'alphaTesting'),
            (0, 'noSubtextures'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelStruct('DATA','fIffII','effectDuration','effectOrientation',
                  'angleThreshold','placementRadius','soundLevel','flags'),
        MelOptStruct('DODT','7fBB2s3Bs','minWidth','maxWidth','minHeight',
                     'maxHeight','depth','shininess','parallaxScale',
                     'parallaxPasses',(DecalDataFlags,'decalFlags',0L),
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
        MelString('EDID','eid'),
        MelBounds(),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
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

    _flags = Flags(0L,Flags.getNames('dynamic','canTake','negative','flickers',
        'unk1','offByDefault','flickerSlow','pulse','pulseSlow','spotLight','spotShadow'))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelModel(),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelString('FULL','full'),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelStruct('DATA','iI3BsI2fIf','duration','radius','red','green','blue',
                  ('unused1',null1),(_flags,'flags',0L),'falloff','fov','value',
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
        MelString('EDID','eid'),
        MelString('ICON','iconPath'),
        MelString('DESC','text'),
        MelStructs('LNAM','2I2h','Locations',(FID,'direct'),(FID,'indirect'),'gridy','gridx'),
        MelFid('WMI1','loadScreenType'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLsct(MelRecord):
    """Load Screen Type."""
    classType = 'LSCT'

    melSet = MelSet(
        MelString('EDID','eid'),
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
        MelString('EDID','eid'),
        MelBounds(),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
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

    _flags = Flags(0L,Flags.getNames(
        ( 0,'dayOuter'),
        ( 1,'dayMiddle'),
        ( 2,'dayInner'),
        ( 3,'nightOuter'),
        ( 4,'nightMiddle'),
        ( 5,'nightInner'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
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
        MelString('EDID','eid'),
        MelString('FNAM','filename'),
        MelFloat('ANAM', 'dB'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MrePgre(MelRecord):
    """Placed Grenade."""
    classType = 'PGRE'

    _flags = Flags(0L,Flags.getNames('oppositeParent'))
    _watertypeFlags = Flags(0L,Flags.getNames('reflection','refraction'))

    melSet = MelSet(
        MelString('EDID','eid'),
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
            MelStruct('XPWR','2I',(FID,'waterReference'),(_watertypeFlags,'waterFlags',0L),),
        ),
        MelStructs('XDCR','II','linkedDecals',(FID,'reference'),'unknown'),
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelUInt8('XAPD', 'flags'),
            MelStructs('XAPR','If','activateParentRefs',(FID,'reference'),'delay')
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

    _flags = Flags(0L,Flags.getNames('oppositeParent'))
    _watertypeFlags = Flags(0L,Flags.getNames('reflection','refraction'))

    melSet = MelSet(
        MelString('EDID','eid'),
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
            MelStruct('XPWR','2I',(FID,'waterReference'),(_watertypeFlags,'waterFlags',0L),),
        ),
        MelStructs('XDCR','II','linkedDecals',(FID,'reference'),'unknown'),
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelUInt8('XAPD', 'flags'),
            MelStructs('XAPR','If','activateParentRefs',(FID,'reference'),'delay')
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

    class MelProjData(MelStruct):
        """Handle older truncated DATA for PROJ subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 84:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 72:
                unpacked = ins.unpack('HHfffIIfffIIfffIIIf', size_, readId)
            elif size_ == 68:
                unpacked = ins.unpack('HHfffIIfffIIfffIII', size_, readId)
            else:
                raise ModSizeError(ins.inName, readId, (84, 72, 68), size_)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelString('FULL','full'),
        MelModel(),
        MelDestructible(),
        MelProjData('DATA','HHfffIIfffIIfffIIIffff',(_flags,'flags'),'type',
                  ('gravity',0.00000),('speed',10000.00000),('range',10000.00000),
                  (FID,'light',0),(FID,'muzzleFlash',0),('tracerChance',0.00000),
                  ('explosionAltTrigerProximity',0.00000),('explosionAltTrigerTimer',0.00000),
                  (FID,'explosion',0),(FID,'sound',0),('muzzleFlashDuration',0.00000),
                  ('fadeDuration',0.00000),('impactForce',0.00000),
                  (FID,'soundCountDown',0),(FID,'soundDisable',0),
                  (FID,'defaultWeaponSource',0),('rotationX',0.00000),
                  ('rotationY',0.00000),('rotationZ',0.00000),('bouncyMult',0.00000)),
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
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelUInt8('DATA', 'flags'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRcpe(MelRecord):
    """Recipe."""
    classType = 'RCPE'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
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

    _flags = Flags(0L,Flags.getNames('visible', 'canTravelTo'))
    _parentFlags = Flags(0L,Flags.getNames('oppositeParent'))
    _actFlags = Flags(0L,Flags.getNames('useDefault', 'activate','open','openByDefault'))
    _lockFlags = Flags(0L,Flags.getNames(None, None, 'leveledLock'))
    _destinationFlags = Flags(0L,Flags.getNames('noAlarm'))

    class MelRefrXloc(MelOptStruct):
        """Handle older truncated XLOC for REFR subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 20:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            #elif size == 16:
            #    unpacked = ins.unpack('B3sIB3s',size,readId)
            elif size_ == 12:
                unpacked = ins.unpack('B3sI4s',size_,readId)
            else:
                raise ModSizeError(ins.inName, readId, (20, 12), size_)
            unpacked = unpacked[:-2] + self.defaults[len(unpacked)-2:-2] + unpacked[-2:]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    class MelRefrXmrk(MelStruct):
        """Handler for xmrk record. Conditionally loads next items."""
        def loadData(self, record, ins, sub_type, size_, readId):
            """Reads data from ins into record attribute."""
            junk = ins.read(size_, readId)
            record.hasXmrk = True
            insTell = ins.tell
            insUnpack = ins.unpack
            pos = insTell()
            (type_, size_) = insUnpack('4sH', 6, readId + '.FULL')
            while type_ in ['FNAM','FULL','TNAM','WMI1']:
                if type_ == 'FNAM':
                    value = insUnpack('B', size_, readId)
                    record.flags = MreRefr._flags(*value)
                elif type_ == 'FULL':
                    record.full = ins.readString(size_, readId)
                elif type_ == 'TNAM':
                    record.markerType, record.unused5 = insUnpack('Bs', size_, readId)
                elif type_ == 'WMI1':
                    record.reputation = insUnpack('I', size_, readId)
                pos = insTell()
                (type_, size_) = insUnpack('4sH', 6, readId + '.FULL')
            ins.seek(pos)
            if self._debug: print ' ',record.flags,record.full,record.markerType

        def dumpData(self,record,out):
            if (record.flags,record.full,record.markerType,record.unused5,record.reputation) != self.defaults[1:]:
                record.hasXmrk = True
            if record.hasXmrk:
                try:
                    out.write(struct.pack('=4sH','XMRK',0))
                    out.packSub('FNAM','B',record.flags.dump())
                    value = record.full
                    if value is not None:
                        out.packSub0('FULL',value)
                    out.packSub('TNAM','Bs',record.markerType, record.unused5)
                    out.packRef('WMI1',record.reputation)
                except struct.error:
                    print self.subType,self.format,record.flags,record.full,record.markerType
                    raise

    melSet = MelSet(
        MelString('EDID','eid'),
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
        MelRefrXmrk('XMRK','',('hasXmrk',False),(_flags,'flags',0L),'full','markerType',('unused5',null1),(FID,'reputation')),
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
        MelRefrXloc('XLOC','B3sI4sB3s4s','lockLevel',('unused1',null3),(FID,'lockKey'),('unused2',null4),(_lockFlags,'lockFlags'),('unused3',null3),('unused4',null4)),
        MelOptSInt32('XCNT', 'count'),
        MelOptFloat('XRDS', 'radius'),
        MelOptFloat('XHLP', 'health'),
        MelOptFloat('XRAD', 'radiation'),
        MelOptFloat('XCHG', ('charge', None)),
        MelGroup('ammo',
            MelFid('XAMT','type'),
            MelUInt32('XAMC', 'count'),
        ),
        MelStructs('XPWR','II','reflectedByWaters',(FID,'reference'),'type'),
        MelFids('XLTW','litWaters'),
        MelStructs('XDCR','II','linkedDecals',(FID,'reference'),'unknown'),
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelUInt8('XAPD', 'flags'),
            MelStructs('XAPR','If','activateParentRefs',(FID,'reference'),'delay')
        ),
        MelString('XATO','activationPrompt'),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_parentFlags,'parentFlags'),('unused6',null3)),
        MelOptFid('XEMI', 'emittance'),
        MelFid('XMBR','multiboundReference'),
        MelOptUInt32('XACT', (_actFlags, 'actFlags', 0L)),
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

    obflags = Flags(0L,Flags.getNames(
        ( 0,'conform'),
        ( 1,'paintVertices'),
        ( 2,'sizeVariance'),
        ( 3,'deltaX'),
        ( 4,'deltaY'),
        ( 5,'deltaZ'),
        ( 6,'Tree'),
        ( 7,'hugeRock'),))
    sdflags = Flags(0L,Flags.getNames(
        ( 0,'pleasant'),
        ( 1,'cloudy'),
        ( 2,'rainy'),
        ( 3,'snowy'),))
    rdatFlags = Flags(0L,Flags.getNames(
        ( 0,'Override'),))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelStruct('RCLR','3Bs','mapRed','mapBlue','mapGreen',('unused1',null1)),
        MelFid('WNAM','worldspace'),
        MelGroups('areas',
            MelUInt32('RPLI', 'edgeFalloff'),
            MelStructA('RPLD','2f','points','posX','posY')
        ),
        MelGroups('entries',
            MelStruct('RDAT', 'I2B2s', 'entryType', (rdatFlags, 'flags'),
                      'priority', ('unused1', null2)),
            MelRegnEntrySubrecord(2, MelStructA(
                'RDOT', 'IH2sf4B2H4s4f3H2s4s', 'objects', (FID,'objectId'),
                'parentIndex', ('unused1', null2), 'density', 'clustering',
                'minSlope', 'maxSlope', (obflags, 'flags'), 'radiusWRTParent',
                'radius', ('unk1', null4), 'maxHeight', 'sink', 'sinkVar',
                'sizeVar', 'angleVarX', 'angleVarY', 'angleVarZ',
                ('unused2', null2), ('unk2', null4))),
            MelRegnEntrySubrecord(4, MelString('RDMP', 'mapName')),
            MelRegnEntrySubrecord(6, MelStructA(
                'RDGS', 'I4s', 'grass', ('unknown', null4))),
            MelRegnEntrySubrecord(7, MelOptStruct(
                'RDMD', 'I', 'musicType')),
            MelRegnEntrySubrecord(7, MelFid('RDMO', 'music')),
            MelRegnEntrySubrecord(7, MelFid('RDSI', 'incidentalMediaSet')),
            MelRegnEntrySubrecord(7, MelFids('RDSB', 'battleMediaSets')),
            MelRegnEntrySubrecord(7, MelStructA(
                'RDSD', '3I', 'sounds', (FID, 'sound'), (sdflags, 'flags'),
                'chance')),
            MelRegnEntrySubrecord(3, MelStructA(
                'RDWT', '3I', 'weatherTypes', (FID, 'weather', None), 'chance',
                (FID, 'global', None))),
            MelRegnEntrySubrecord(8, MelFidList('RDID', 'imposters')),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRepu(MelRecord):
    """Reputation."""
    classType = 'REPU'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelFloat('DATA', 'value'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSlpd(MelRecord):
    """Sleep Deprivation Stage."""
    classType = 'SLPD'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('DATA','2I','trigerThreshold',(FID,'actorEffect')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSoun(MelRecord):
    """Sound."""
    classType = 'SOUN'

    _flags = Flags(0L,Flags.getNames(
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

    class MelSounSndx(MelStruct):
        """SNDX is a reduced version of SNDD. Allow it to read in, but not
        set defaults or write."""
        def loadData(self, record, ins, sub_type, size_, readId):
            MelStruct.loadData(self, record, ins, sub_type, size_, readId)
            record.point0 = 0
            record.point1 = 0
            record.point2 = 0
            record.point3 = 0
            record.point4 = 0
            record.reverb = 0
            record.priority = 0
            record.xLoc = 0
            record.yLoc = 0
        def getSlotsUsed(self):
            return ()
        def setDefault(self,record): return
        def dumpData(self,record,out): return

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelString('FNAM','soundFile'),
        MelUInt8('RNAM', '_rnam'),
        MelOptStruct('SNDD','=2BbsIh2B6h3i',('minDist',0), ('maxDist',0),
                    ('freqAdj',0), ('unusedSndd',null1),(_flags,'flags',0L),
                    ('staticAtten',0),('stopTime',0),('startTime',0),
                    ('point0',0),('point1',0),('point2',0),('point3',0),('point4',0),
                    ('reverb',0),('priority',0), ('xLoc',0), ('yLoc',0),),
        MelSounSndx('SNDX','=2BbsIh2B',('minDist',0), ('maxDist',0),
                   ('freqAdj',0), ('unusedSndd',null1),(_flags,'flags',0L),
                   ('staticAtten',0),('stopTime',0),('startTime',0),),
        MelBase('ANAM','_anam'), #--Should be a struct. Maybe later.
        MelBase('GNAM','_gnam'), #--Should be a struct. Maybe later.
        MelBase('HNAM','_hnam'), #--Should be a struct. Maybe later.
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreStat(MelRecord):
    """Static."""
    classType = 'STAT'

    melSet = MelSet(
        MelString('EDID','eid'),
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
        MelString('EDID','eid'),
        MelBounds(),
        MelString('FULL','full'),
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

    _flags = Flags(0L,Flags.getNames('notNormalWeapon'))
    _dflags1 = Flags(0L,Flags.getNames(
            'ignoresNormalWeaponResistance',
            'isAutomatic',
            'hasScope',
            'cantDrop',
            'hideBackpack',
            'embeddedWeapon',
            'dontUse1stPersonISAnimations',
            'nonPlayable',
        ))
    _dflags2 = Flags(0L,Flags.getNames(
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
    _cflags = Flags(0L,Flags.getNames(
            'onDeath',
            'unknown1','unknown2','unknown3','unknown4',
            'unknown5','unknown6','unknown7',
        ))

    class MelWeapDnam(MelStruct):
        """Handle older truncated DNAM for WEAP subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 204:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 200:
                unpacked = ins.unpack('IffBBBBfffffIBBBBffIIfffffffffffiIffiffffIIIfffIIsB2sffffff', size_, readId)
            elif size_ == 196:
                unpacked = ins.unpack('IffBBBBfffffIBBBBffIIfffffffffffiIffiffffIIIfffIIsB2sfffff', size_, readId)
            elif size_ == 180:
                unpacked = ins.unpack('IffBBBBfffffIBBBBffIIfffffffffffiIffiffffIIIfffIIsB2sf', size_, readId)
            elif size_ == 172:
                unpacked = ins.unpack('IffBBBBfffffIBBBBffIIfffffffffffiIffiffffIIIfffII', size_, readId)
            elif size_ == 164:
                unpacked = ins.unpack('IffBBBBfffffIBBBBffIIfffffffffffiIffiffffIIIfff', size_, readId)
            elif size_ == 136:
                unpacked = ins.unpack('IffBBBBfffffIBBBBffIIfffffffffffiIffifff', size_, readId)
            elif size_ == 124:
                unpacked = ins.unpack('IffBBBBfffffIBBBBffIIfffffffffffiIffi', size_, readId)
            elif size_ == 120:
                unpacked = ins.unpack('IffBBBBfffffIBBBBffIIfffffffffffiIff', size_, readId)
            else:
                raise ModSizeError(
                    ins.inName, readId, (204, 200, 196, 180, 172, 164, 136,
                                         124, 120), size_)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    class MelWeapVats(MelStruct):
        """Handle older truncated VATS for WEAP subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 20:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 16:
                unpacked = ins.unpack('Ifff', size_, readId)
            else:
                raise ModSizeError(ins.inName, readId, (20, 16), size_)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelString('FULL','full'),
        MelModel('model'),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
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
        MelWeapDnam('DNAM','IffBBBBfffffIBBBBffIIfffffffffffiIffiffffIIIfffIIsB2sffffffI',
                    'animationType','animationMultiplier','reach',
                    (_dflags1,'dnamFlags1',0L),('gripAnimation',255),'ammoUse',
                    'reloadAnimation','minSpread','spread','weapDnam1','sightFov',
                    ('weapDnam2',0.0),(FID,'projectile',0L),'baseVatsToHitChance',
                    ('attackAnimation',255),'projectileCount','embeddedWeaponActorValue',
                    'minRange','maxRange','onHit',(_dflags2,'dnamFlags2',0L),
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
                    'impulseDist','skillReq'),
        MelOptStruct('CRDT','H2sfB3sI',('criticalDamage', 0),('weapCrdt1', null2),
                     ('criticalMultiplier', 0.0),(_cflags,'criticalFlags', 0L),
                     ('weapCrdt2', null3),(FID,'criticalEffect', 0),),
        MelWeapVats('VATS','I3f2B2s','vatsEffect','vatsSkill','vatsDamMult',
                    'vatsAp','vatsSilent','vatsModReqiured',('weapVats1',null2)),
        MelBase('VNAM','soundLevel'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MelPnamNam0Handler(MelStructA):
    """Handle older truncated PNAM for WTHR subrecord."""
    def __init__(self, type_, attr):
        MelStructA.__init__(self, type_, '3Bs3Bs3Bs3Bs3Bs3Bs', attr,
            'riseRed','riseGreen','riseBlue', ('unused1',null1),
            'dayRed','dayGreen','dayBlue', ('unused2',null1),
            'setRed','setGreen','setBlue', ('unused3',null1),
            'nightRed','nightGreen','nightBlue', ('unused4',null1),
            'noonRed','noonGreen','noonBlue', ('unused5',null1),
            'midnightRed','midnightGreen','midnightBlue', ('unused6',null1),
                            )

    def loadData(self, record, ins, sub_type, size_, readId):
        """Handle older truncated PNAM for WTHR subrecord."""
        if (sub_type == 'PNAM' and size_ == 96) or (sub_type == 'NAM0' and size_ == 240):
            MelStructA.loadData(self, record, ins, sub_type, size_, readId)
            return
        elif (sub_type == 'PNAM' and size_ == 64) or (sub_type == 'NAM0' and size_ == 160):
            oldFormat = '3Bs3Bs3Bs3Bs'
            # Duplicated from MelStructA.loadData - don't worry, this entire
            # class will disappear soon ;)
            selfDefault = self.getDefault
            recordAppend = record.__getattribute__(self.attr).append
            selfAttrs = self.attrs
            itemSize = struct.calcsize(oldFormat)
            for x in xrange(size_/itemSize):
                target = selfDefault()
                recordAppend(target)
                target.__slots__ = selfAttrs
                unpacked = ins.unpack(oldFormat,itemSize,readId)
                setter = target.__setattr__
                for attr,value,action in zip(selfAttrs,unpacked,self.actions):
                    if action: value = action(value)
                    setter(attr,value)
        else:
            exp_sizes = (96, 64) if sub_type == 'PNAM' else (240, 160)
            raise ModSizeError(ins.inName, readId, exp_sizes, size_)

class MreWthr(MelRecord):
    """Weather."""
    classType = 'WTHR'

    melSet = MelSet(
        MelString('EDID','eid'),
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
        MelPnamNam0Handler('PNAM','cloudColors'),
        MelPnamNam0Handler('NAM0','daytimeColors'),
        MelStruct('FNAM','6f','fogDayNear','fogDayFar','fogNightNear','fogNightFar','fogDayPower','fogNightPower'),
        MelBase('INAM','_inam'), #--Should be a struct. Maybe later.
        MelStruct('DATA','15B',
            'windSpeed','lowerCloudSpeed','upperCloudSpeed','transDelta',
            'sunGlare','sunDamage','rainFadeIn','rainFadeOut','boltFadeIn',
            'boltFadeOut','boltFrequency','weatherType','boltRed','boltBlue','boltGreen'),
        MelStructs('SNAM','2I','sounds',(FID,'sound'),'type'),
    )
    __slots__ = melSet.getSlotsUsed()
