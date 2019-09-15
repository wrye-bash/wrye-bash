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
import itertools
import struct
# Set MelModel in brec, in this case it's identical to the fallout 3 one
from ..fallout3.records import MelScrxen, MelOwnership, MelDestructible, \
    MelBipedFlags, MelEffects, MelConditions, MreHasEffects
from ...bass import null1, null2, null3, null4
from ...bolt import Flags, GPath
from ...brec import MelModel # set in Mopy/bash/game/fallout3/records.py
from ...brec import MelRecord, MelStructs, MelGroups, MelStruct, FID, \
    MelGroup, MelString, MelSet, MelFid, MelNull, MelOptStruct, MelFids, \
    MelBase, MelFidList, MelStructA, MreGmstBase, MelFull0, MreHeaderBase, \
    MelUnicode, MreDial
from ...exception import ModError, ModSizeError

# Those are unused here, but need be in this file as are accessed via it
from ..fallout3.records import MreNpc ##: used in Oblivion only save code really

from_iterable = itertools.chain.from_iterable

#------------------------------------------------------------------------------
# FalloutNV Records -----------------------------------------------------------
#------------------------------------------------------------------------------
class MreHeader(MreHeaderBase):
    """TES4 Record.  File header."""
    classType = 'TES4'

    #--Data elements
    melSet = MelSet(
        MelStruct('HEDR','f2I',('version',1.34),'numRecords',('nextObject',0xCE6)),
        MelBase('OFST','ofst_p',),  #--Obsolete?
        MelBase('DELE','dele_p',),  #--Obsolete?
        MelUnicode('CNAM','author',u'',512),
        MelUnicode('SNAM','description',u'',512),
        MreHeaderBase.MelMasterName('MAST','masters'),
        MelNull('DATA'), # 8 Bytes in Length
        MelFidList('ONAM','overrides'),
        MelBase('SCRN', 'scrn_p'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreAchr(MelRecord):
    """Placed NPC"""
    classType = 'ACHR'
    _flags = Flags(0L,Flags.getNames('oppositeParent','popIn'))
    _variableFlags = Flags(0L,Flags.getNames('isLongOrShort'))
    melSet=MelSet(
        MelString('EDID','eid'),
        MelFid('NAME','base'),
        MelFid('XEZN','encounterZone'),
        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelGroup('patrolData',
            MelStruct('XPRD','f','idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelStruct('SCHR','4s4I',('unused1',null4),'numRefs','compiledSize','lastIndex','scriptType'),
            MelBase('SCDA','compiled_p'),
            MelString('SCTX','scriptText'),
            MelGroups('vars',
                MelStruct('SLSD','I12sB7s','index',('unused1',null4+null4+null4),(_variableFlags,'flags',0L),('unused2',null4+null3)),
                MelString('SCVR','name')),
            MelScrxen('SCRV/SCRO','references'),
            MelFid('TNAM','topic'),
            ),
        MelStruct('XLCM','i','levelModifier'),
        MelFid('XMRC','merchantContainer',),
        MelStruct('XCNT','i','count'),
        MelStruct('XRDS','f','radius',),
        MelStruct('XHLP','f','health',),
        MelStructs('XDCR','II','linkedDecals',(FID,'reference'),'unknown'), # ??
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelStruct('XAPD','B','flags'),
            MelStructs('XAPR','If','activateParentRefs',(FID,'reference'),'delay')
            ),
        MelString('XATO','activationPrompt'),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),('unused1',null3)),
        MelOptStruct('XEMI','I',(FID,'emittance')),
        MelFid('XMBR','multiboundReference'),
        MelBase('XIBS','ignoredBySandbox'),
        MelOptStruct('XSCL','f',('scale',1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAcre(MelRecord):
    """Placed Creature"""
    classType = 'ACRE'
    _flags = Flags(0L,Flags.getNames('oppositeParent','popIn'))
    _variableFlags = Flags(0L,Flags.getNames('isLongOrShort'))
    melSet=MelSet(
        MelString('EDID','eid'),
        MelFid('NAME','base'),
        MelFid('XEZN','encounterZone'),
        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelGroup('patrolData',
            MelStruct('XPRD','f','idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelStruct('SCHR','4s4I',('unused1',null4),'numRefs','compiledSize','lastIndex','scriptType'),
            MelBase('SCDA','compiled_p'),
            MelString('SCTX','scriptText'),
            MelGroups('vars',
                MelStruct('SLSD','I12sB7s','index',('unused1',null4+null4+null4),(_variableFlags,'flags',0L),('unused2',null4+null3)),
                MelString('SCVR','name')),
            MelScrxen('SCRV/SCRO','references'),
            MelFid('TNAM','topic'),
            ),
        MelStruct('XLCM','i','levelModifier'),
        MelOwnership(),
        MelFid('XMRC','merchantContainer'),
        MelStruct('XCNT','i','count'),
        MelStruct('XRDS','f','radius',),
        MelStruct('XHLP','f','health',),
        MelStructs('XDCR','II','linkedDecals',(FID,'reference'),'unknown'), # ??
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelStruct('XAPD','B','flags'),
            MelStructs('XAPR','If','activateParentRefs',(FID,'reference'),'delay')
            ),
        MelString('XATO','activationPrompt'),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),('unused1',null3)),
        MelOptStruct('XEMI','I',(FID,'emittance')),
        MelFid('XMBR','multiboundReference'),
        MelBase('XIBS','ignoredBySandbox'),
        MelOptStruct('XSCL','f',('scale',1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreActi(MelRecord):
    """Activator record."""
    classType = 'ACTI'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
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
    """Media location controller."""
    classType = 'ALOC'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelStruct('NAM1','I','flags'),
        MelStruct('NAM2','I','num2'),
        MelStruct('NAM3','I','nam3'),
        MelStruct('NAM4','f','locationDelay'),
        MelStruct('NAM5','I','dayStart'),
        MelStruct('NAM6','I','nightStart'),
        MelStruct('NAM7','f','retrigerDelay'),
        MelFids('HNAM','neutralSets'),
        MelFids('ZNAM','allySets'),
        MelFids('XNAM','friendSets'),
        MelFids('YNAM','enemySets'),
        MelFids('LNAM','locationSets'),
        MelFids('GNAM','battleSets'),
        MelFid('RNAM','conditionalFaction'),
        MelStruct('FNAM','I','fnam'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAmef(MelRecord):
    """Ammo effect record."""
    classType = 'AMEF'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelStruct('DATA','2If','type','operation','value'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAmmo(MelRecord):
    """Ammo (arrow) record."""
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
                raise "Unexpected size encountered for AMMO:DAT2 subrecord: %s" % size_
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
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
    """Armor addon record."""
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
                raise "Unexpected size encountered for ARMA subrecord: %s" % size_
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
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
        #-1:None,0:Big Guns,1:Energy Weapons,2:Small Guns,3:Melee Weapons,
        #4:Unarmed Weapon,5:Thrown Weapons,6:Mine,7:Body Wear,8:Head Wear,
        #9:Hand Wear,10:Chems,11:Stimpack,12:Food,13:Alcohol
        MelStruct('ETYP','i',('etype',-1)),
        MelStruct('DATA','IIf','value','health','weight'),
        MelArmaDnam('DNAM','=hHf4s','ar',(_dnamFlags,'dnamFlags',0L),('dt',0.0),('armaDnam1',null4),),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArmo(MelRecord):
    """Armor record."""
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
                raise "Unexpected size encountered for ARMO subrecord: %s" % size_
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()

    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
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
        #-1:None,0:Big Guns,1:Energy Weapons,2:Small Guns,3:Melee Weapons,
        #4:Unarmed Weapon,5:Thrown Weapons,6:Mine,7:Body Wear,8:Head Wear,
        #9:Hand Wear,10:Chems,11:Stimpack,12:Food,13:Alcohol
        MelStruct('ETYP','i',('etype',-1)),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('DATA','=2if','value','health','weight'),
        MelArmoDnam('DNAM','=hHf4s','ar',(_dnamFlags,'dnamFlags',0L),('dt',0.0),('armoDnam1',null4),),
        MelStruct('BNAM','I',('overridesAnimationSound',0L)),
        MelStructs('SNAM','IB3sI','animationSounds',(FID,'sound'),'chance',('unused','\xb7\xe7\x0b'),'type'),
        MelFid('TNAM','animationSoundsTemplate'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAspc(MelRecord):
    """Acoustic space record."""
    classType = 'ASPC'
    isKeyedByEid = True # NULL fids are acceptible

    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelFids('SNAM','soundLooping'),
        MelStruct('WNAM','I','wallaTrigerCount'),
        MelFid('RDAT','useSoundFromRegion'),
        MelStruct('ANAM','I','environmentType'),
        MelStruct('INAM','I','isInterior'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCcrd(MelRecord):
    """Caravan Card."""
    classType = 'CCRD'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelFid('SCRI','script'),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelString('TX00','textureFace'),
        MelString('TX01','textureBack'),
        MelStructs('INTV','I','suitAndValue','value'),
        MelStruct('DATA','I','value'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCdck(MelRecord):
    """Caravan deck record."""
    classType = 'CDCK'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelFids('CARD','cards'),
        MelStruct('DATA','I','count'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCell(MelRecord):
    """Cell record."""
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
                raise "Unexpected size encountered for XCLC subrecord: %s" % size_
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
                raise "Unexpected size encountered for XCLL subrecord: %s" % size_
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelStruct('DATA','B',(cellFlags,'flags',0L)),
        MelCoordinates('XCLC','iiI',('posX',None),('posY',None),('forceHideLand',0L)),
        MelCellXcll('XCLL','=3Bs3Bs3Bs2f2i3f','ambientRed','ambientGreen','ambientBlue',
            ('unused1',null1),'directionalRed','directionalGreen','directionalBlue',
            ('unused2',null1),'fogRed','fogGreen','fogBlue',
            ('unused3',null1),'fogNear','fogFar','directionalXY','directionalZ',
            'directionalFade','fogClip','fogPower'),
        MelBase('IMPF','footstepMaterials'), #--todo rewrite specific class.
        MelFid('LTMP','lightTemplate'),
        MelOptStruct('LNAM','I',(inheritFlags,'lightInheritFlags',0L)),
        #--CS default for water is -2147483648, but by setting default here to -2147483649,
        #  we force the bashed patch to retain the value of the last mod.
        MelOptStruct('XCLW','f',('waterHeight',-2147483649)),
        MelString('XNAM','waterNoiseTexture'),
        MelFidList('XCLR','regions'),
        MelOptStruct('XCMT','B','xcmt_p'),
        MelFid('XCIM','imageSpace'),
        MelOptStruct('XCET','B','xcet_p'),
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
    """Challenge record."""
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
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
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
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('DATA','I','absoluteValue'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCont(MelRecord):
    """Container record."""
    classType = 'CONT'
    _flags = Flags(0,Flags.getNames(None,'respawns'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
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
            MelString('MODL','model')),
        MelString('MOD2','slotMachineModel'),
        MelString('MOD3','blackjackTableModel'),
        MelString('MODT','extraBlackjackTableModel'),
        MelString('MOD4','rouletteTableModel'),
        MelGroups('slotReelTextures',
            MelString('ICON','texture')),
        MelGroups('blackjackDecks',
            MelString('ICO2','texture')),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCsty(MelRecord):
    """CSTY Record. Combat Styles."""
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

    #--Mel Set
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
    """Dehydration stage record."""
    classType = 'DEHY'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('DATA','2I','trigerThreshold',(FID,'actorEffect')),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDial(MreDial):
    """Dialog record."""
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
                raise "Unexpected size encountered for DIAL subrecord: %s" % size_
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()
    class MelDialDistributor(MelNull):
        def __init__(self):
            self._debug = False
        def getLoaders(self,loaders):
            """Self as loader for structure types."""
            for type_ in ('INFC','INFX',):
                loaders[type_] = self
        def setMelSet(self,melSet):
            """Set parent melset. Need this so that can reassign loaders later."""
            self.melSet = melSet
            self.loaders = {}
            for element in melSet.elements:
                attr = element.__dict__.get('attr',None)
                if attr: self.loaders[attr] = element
        def loadData(self, record, ins, sub_type, size_, readId):
            if sub_type in ('INFC', 'INFX'):
                quests = record.__getattribute__('quests')
                if quests:
                    element = self.loaders['quests']
                else:
                    if sub_type == 'INFC':
                        element = self.loaders['bare_infc_p']
                    elif sub_type == 'INFX':
                        element = self.loaders['bare_infx_p']
            element.loadData(record, ins, sub_type, size_, readId)

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
        MelStruct('PNAM','f','priority'),
        MelString('TDUM','tdum_p'),
        MelDialData('DATA','BB','dialType',(_flags,'dialFlags',0L)),
        MelDialDistributor(),
     )
    melSet.elements[-1].setMelSet(melSet)

    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDobj(MelRecord):
    """Default object manager record."""
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
    """Enchantment (Object Effect) record."""
    classType = 'ENCH'
    _flags = Flags(0L,Flags.getNames('noAutoCalc','autoCalculate','hideEffect'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFull0(), #--At least one mod has this. Odd.
        MelStruct('ENIT','3IB3s','itemType','chargeAmount','enchantCost',
                  (_flags,'flags',0L),('unused1',null3)),
        #--itemType = 0: Scroll, 1: Staff, 2: Weapon, 3: Apparel
        MelEffects(),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFact(MelRecord):
    """Faction record."""
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
                #--Else 2 byte record
                unpacked = ins.unpack('2B', size_, readId)
            elif size_ == 1:
                #--Else 1 byte record
                unpacked = ins.unpack('B', size_, readId)
            else:
                raise "Unexpected size encountered for FACT:DATA subrecord: %s" % size_
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
        MelOptStruct('CNAM','f',('crimeGoldMultiplier',None)),
        MelGroups('ranks',
            MelStruct('RNAM','i','rank'),
            MelString('MNAM','male'),
            MelString('FNAM','female'),
            MelString('INAM','insigniaPath'),),
        MelOptStruct('WMI1','I',(FID,'reputation',None)),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Marker for organization please don't remove ---------------------------------
# GLOB ------------------------------------------------------------------------
# Defined in brec.py as class MreGlob(MelRecord) ------------------------------
#------------------------------------------------------------------------------
class MreGmst(MreGmstBase):
    """Fallout New Vegas GMST record"""
    isKeyedByEid = True # NULL fids are acceptable.

#------------------------------------------------------------------------------
class MreHdpt(MelRecord):
    """Head part record."""
    classType = 'HDPT'
    _flags = Flags(0L,Flags.getNames('playable',))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelStruct('DATA','B',(_flags,'flags')),
        MelFids('HNAM','extraParts'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreHung(MelRecord):
    """Hunger stage record."""
    classType = 'HUNG'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('DATA','2I','trigerThreshold',(FID,'actorEffect')),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreImad(MelRecord):
    """Image space modifier record."""
    classType = 'IMAD'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelBase('DNAM','dnam_p'),
        MelBase('BNAM','bnam_p'),
        MelBase('VNAM','vnam_p'),
        MelBase('TNAM','tnam_p'),
        MelBase('NAM3','nam3_p'),
        MelBase('RNAM','rnam_p'),
        MelBase('SNAM','snam_p'),
        MelBase('UNAM','unam_p'),
        MelBase('NAM1','nam1_p'),
        MelBase('NAM2','nam2_p'),
        MelBase('WNAM','wnam_p'),
        MelBase('XNAM','xnam_p'),
        MelBase('YNAM','ynam_p'),
        MelBase('NAM4','nam4_p'),
        MelBase('\x00IAD','_00IAD'),
        MelBase('\x40IAD','_atiad_p'),
        MelBase('\x01IAD','_01IAD'),
        MelBase('AIAD','aiad_p'),
        MelBase('\x02IAD','_02IAD'),
        MelBase('BIAD','biad_p'),
        MelBase('\x03IAD','_03IAD'),
        MelBase('CIAD','ciad_p'),
        MelBase('\x04IAD','_04IAD'),
        MelBase('DIAD','diad_p'),
        MelBase('\x05IAD','_05IAD'),
        MelBase('EIAD','eiad_p'),
        MelBase('\x06IAD','_06IAD'),
        MelBase('FIAD','fiad_p'),
        MelBase('\x07IAD','_07IAD'),
        MelBase('GIAD','giad_p'),
        MelBase('\x08IAD','_08IAD'),
        MelBase('HIAD','hiad_p'),
        MelBase('\x09IAD','_09IAD'),
        MelBase('IIAD','iiad_p'),
        MelBase('\x0aIAD','_0aIAD'),
        MelBase('JIAD','jiad_p'),
        MelBase('\x0bIAD','_0bIAD'),
        MelBase('KIAD','kiad_p'),
        MelBase('\x0cIAD','_0cIAD'),
        MelBase('LIAD','liad_p'),
        MelBase('\x0dIAD','_0dIAD'),
        MelBase('MIAD','miad_p'),
        MelBase('\x0eIAD','_0eIAD'),
        MelBase('NIAD','niad_p'),
        MelBase('\x0fIAD','_0fIAD'),
        MelBase('OIAD','oiad_p'),
        MelBase('\x10IAD','_10IAD'),
        MelBase('PIAD','piad_p'),
        MelBase('\x11IAD','_11IAD'),
        MelBase('QIAD','qiad_p'),
        MelBase('\x12IAD','_12IAD'),
        MelBase('RIAD','riad_p'),
        MelBase('\x13IAD','_13iad_p'),
        MelBase('SIAD','siad_p'),
        MelBase('\x14IAD','_14iad_p'),
        MelBase('TIAD','tiad_p'),
        MelFid('RDSD','soundIntro'),
        MelFid('RDSI','soundOutro'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreImod(MelRecord):
    """Item mod."""
    classType = 'IMOD'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
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
    """Info (dialog entry) record."""
    classType = 'INFO'
    _flags = Flags(0,Flags.getNames(
        'goodbye','random','sayOnce','runImmediately','infoRefusal','randomEnd',
        'runForRumors','speechChallenge',))
    _flags2 = Flags(0,Flags.getNames(
        'sayOnceADay','alwaysDarken',None,None,'lowIntelligence','highIntelligence',))
    _variableFlags = Flags(0L,Flags.getNames('isLongOrShort'))
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

    class MelInfoSchr(MelStruct):
        """Print only if schd record is null."""
        def dumpData(self,record,out):
            if not record.schd_p:
                MelStruct.dumpData(self,record,out)
    #--MelSet
    melSet = MelSet(
        MelInfoData('DATA','HH','dialType','nextSpeaker',(_flags,'flags'),(_flags2,'flagsInfo'),),
        MelFid('QSTI','quests'),
        MelFid('TPIC','topic'),
        MelFid('PNAM','prevInfo'),
        MelFids('NAME','addTopics'),
        MelGroups('responses',
            MelStruct('TRDT','Ii4sB3sIB3s','emotionType','emotionValue',('unused1',null4),'responseNum',('unused2','0xcd0xcd0xcd'),
                      (FID,'sound'),'flags',('unused3','0xcd0xcd0xcd')),
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
        # MelBase('SCHD','schd_p'), #--Old format script header?
        MelGroup('scriptBegin',
            MelInfoSchr('SCHR','4s4I',('unused2',null4),'numRefs','compiledSize','lastIndex','scriptType'),
            MelBase('SCDA','compiled_p'),
            MelString('SCTX','scriptText'),
            MelGroups('vars',
                MelStruct('SLSD','I12sB7s','index',('unused1',null4+null4+null4),(_variableFlags,'flags',0L),('unused2',null4+null3)),
                MelString('SCVR','name')),
            MelScrxen('SCRV/SCRO','references'),
            ),
        MelGroup('scriptEnd',
            MelBase('NEXT','marker'),
            MelInfoSchr('SCHR','4s4I',('unused2',null4),'numRefs','compiledSize','lastIndex','scriptType'),
            MelBase('SCDA','compiled_p'),
            MelString('SCTX','scriptText'),
            MelGroups('vars',
                MelStruct('SLSD','I12sB7s','index',('unused1',null4+null4+null4),(_variableFlags,'flags',0L),('unused2',null4+null3)),
                MelString('SCVR','name')),
            MelScrxen('SCRV/SCRO','references'),
            ),
        # MelFid('SNDD','sndd_p'),
        MelString('RNAM','prompt'),
        MelFid('ANAM','speaker'),
        MelFid('KNAM','acterValuePeak'),
        MelStruct('DNAM', 'I', 'speechChallenge')
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIpct(MelRecord):
    """Impact record."""
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
    """MISC (miscellaneous item) record."""
    classType = 'KEYM'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
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
    """Light source record."""
    classType = 'LIGH'
    _flags = Flags(0L,Flags.getNames('dynamic','canTake','negative','flickers',
        'unk1','offByDefault','flickerSlow','pulse','pulseSlow','spotLight','spotShadow'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelModel(),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelString('FULL','full'),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelStruct('DATA','iI3BsI2fIf','duration','radius','red','green','blue',
                  ('unused1',null1),(_flags,'flags',0L),'falloff','fov','value',
                  'weight'),
        MelOptStruct('FNAM','f',('fade',None)),
        MelFid('SNAM','sound'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLscr(MelRecord):
    """Load screen."""
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
    """Load screen tip."""
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
    """MISC (miscellaneous item) record."""
    classType = 'MISC'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
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
        #-1:'No Set',0:'Battle Set',1:'Location Set',2:'Dungeon Set',3:'Incidental Set'
        MelStruct('NAM1','I','type'),
        MelString('NAM2','nam2'),
        MelString('NAM3','nam3'),
        MelString('NAM4','nam4'),
        MelString('NAM5','nam5'),
        MelString('NAM6','nam6'),
        MelString('NAM7','nam7'),
        MelStruct('NAM8','f','nam8'),
        MelStruct('NAM9','f','nam9'),
        MelStruct('NAM0','f','nam0'),
        MelStruct('ANAM','f','anam'),
        MelStruct('BNAM','f','bnam'),
        MelStruct('CNAM','f','cnam'),
        MelStruct('JNAM','f','jnam'),
        MelStruct('KNAM','f','knam'),
        MelStruct('LNAM','f','lnam'),
        MelStruct('MNAM','f','mnam'),
        MelStruct('NNAM','f','nnam'),
        MelStruct('ONAM','f','onam'),
        MelStruct('PNAM','B',(_flags,'enableFlags'),),
        MelStruct('DNAM','f','dnam'),
        MelStruct('ENAM','f','enam'),
        MelStruct('FNAM','f','fnam'),
        MelStruct('GNAM','f','gnam'),
        MelOptStruct('HNAM','I',(FID,'hnam')),
        MelOptStruct('INAM','I',(FID,'inam')),
        MelBase('DATA','data'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMusc(MelRecord):
    """Music type record."""
    classType = 'MUSC'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FNAM','filename'),
        MelStruct('ANAM','f','dB'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MrePgre(MelRecord):
    """Placed Grenade"""
    classType = 'PGRE'
    _flags = Flags(0L,Flags.getNames('oppositeParent'))
    _variableFlags = Flags(0L,Flags.getNames('isLongOrShort'))
    _watertypeFlags = Flags(0L,Flags.getNames('reflection','refraction'))
    melSet=MelSet(
        MelString('EDID','eid'),
        MelFid('NAME','base'),
        MelFid('XEZN','encounterZone'),
        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelGroup('patrolData',
            MelStruct('XPRD','f','idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelStruct('SCHR','4s4I',('unused1',null4),'numRefs','compiledSize','lastIndex','scriptType'),
            MelBase('SCDA','compiled_p'),
            MelString('SCTX','scriptText'),
            MelGroups('vars',
                MelStruct('SLSD','I12sB7s','index',('unused1',null4+null4+null4),(_variableFlags,'flags',0L),('unused2',null4+null3)),
                MelString('SCVR','name')),
            MelScrxen('SCRV/SCRO','references'),
            MelFid('TNAM','topic'),
            ),
        MelOwnership(),
        MelStruct('XCNT','i','count'),
        MelStruct('XRDS','f','radius',),
        MelStruct('XHLP','f','health',),
        MelGroups('reflectedRefractedBy',
            MelStruct('XPWR','2I',(FID,'waterReference'),(_watertypeFlags,'waterFlags',0L),),
        ),
        MelStructs('XDCR','II','linkedDecals',(FID,'reference'),'unknown'),
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelStruct('XAPD','B','flags'),
            MelStructs('XAPR','If','activateParentRefs',(FID,'reference'),'delay')
            ),
        MelString('XATO','activationPrompt'),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),('unused1',null3)),
        MelOptStruct('XEMI','I',(FID,'emittance')),
        MelFid('XMBR','multiboundReference'),
        MelBase('XIBS','ignoredBySandbox'),
        MelOptStruct('XSCL','f',('scale',1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MrePmis(MelRecord):
    """Placed Missile"""
    classType = 'PMIS'
    _flags = Flags(0L,Flags.getNames('oppositeParent'))
    _variableFlags = Flags(0L,Flags.getNames('isLongOrShort'))
    _watertypeFlags = Flags(0L,Flags.getNames('reflection','refraction'))
    melSet=MelSet(
        MelString('EDID','eid'),
        MelFid('NAME','base'),
        MelFid('XEZN','encounterZone'),
        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelGroup('patrolData',
            MelStruct('XPRD','f','idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelStruct('SCHR','4s4I',('unused1',null4),'numRefs','compiledSize','lastIndex','scriptType'),
            MelBase('SCDA','compiled_p'),
            MelString('SCTX','scriptText'),
            MelGroups('vars',
                MelStruct('SLSD','I12sB7s','index',('unused1',null4+null4+null4),(_variableFlags,'flags',0L),('unused2',null4+null3)),
                MelString('SCVR','name')),
            MelScrxen('SCRV/SCRO','references'),
            MelFid('TNAM','topic'),
            ),
        MelOwnership(),
        MelStruct('XCNT','i','count'),
        MelStruct('XRDS','f','radius',),
        MelStruct('XHLP','f','health',),
        MelGroups('reflectedRefractedBy',
            MelStruct('XPWR','2I',(FID,'waterReference'),(_watertypeFlags,'waterFlags',0L),),
        ),
        MelStructs('XDCR','II','linkedDecals',(FID,'reference'),'unknown'),
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelStruct('XAPD','B','flags'),
            MelStructs('XAPR','If','activateParentRefs',(FID,'reference'),'delay')
            ),
        MelString('XATO','activationPrompt'),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),('unused1',null3)),
        MelOptStruct('XEMI','I',(FID,'emittance')),
        MelFid('XMBR','multiboundReference'),
        MelBase('XIBS','ignoredBySandbox'),
        MelOptStruct('XSCL','f',('scale',1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreProj(MelRecord):
    """Projectile record."""
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
                raise "Unexpected size encountered for PROJ:DATA subrecord: %s" % size_
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
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
        MelStruct('VNAM','I','soundLevel'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRace(MelRecord):
    """Race record.

    This record is complex to read and write. Relatively simple problems are the VNAM
    which can be empty or zeroed depending on relationship between voices and
    the fid for the race.

    The face and body data is much more complicated, with the same subrecord types
    mapping to different attributes depending on preceding flag subrecords (NAM0, NAM1,
    NMAN, FNAM and INDX.) These are handled by using the MelRaceDistributor class
    to dynamically reassign melSet.loaders[type] as the flag records are encountered.

    It's a mess, but this is the shortest, clearest implementation that I could
    think of."""

    classType = 'RACE'
    _flags = Flags(0L,Flags.getNames('playable', None, 'child'))

    class MelRaceVoices(MelStruct):
        """Set voices to zero, if equal race fid. If both are zero, then don't skip dump."""
        def dumpData(self,record,out):
            if record.maleVoice == record.fid: record.maleVoice = 0L
            if record.femaleVoice == record.fid: record.femaleVoice = 0L
            if (record.maleVoice,record.femaleVoice) != (0,0):
                MelStruct.dumpData(self,record,out)

    class MelRaceHeadModel(MelGroup):
        """Most face data, like a MelModel + ICON + MICO. Load is controlled by MelRaceDistributor."""
        def __init__(self,attr,index):
            MelGroup.__init__(self,attr,
                MelString('MODL','modPath'),
                MelBase('MODB','modb_p'),
                MelBase('MODT','modt_p'),
                MelBase('MODS','mods_p'),
                MelOptStruct('MODD','B','modd_p'),
                MelString('ICON','iconPath'),
                MelBase('MICO','mico'))
            self.index = index
        def dumpData(self,record,out):
            out.packSub('INDX','I',self.index)
            MelGroup.dumpData(self,record,out)

    class MelRaceBodyModel(MelGroup):
        """Most body data, like a MelModel - MODB + ICON + MICO. Load is controlled by MelRaceDistributor."""
        def __init__(self,attr,index):
            MelGroup.__init__(self,attr,
                MelString('ICON','iconPath'),
                MelBase('MICO','mico'),
                MelString('MODL','modPath'),
                MelBase('MODT','modt_p'),
                MelBase('MODS','mods_p'),
                MelOptStruct('MODD','B','modd_p'))
            self.index = index
        def dumpData(self,record,out):
            out.packSub('INDX','I',self.index)
            MelGroup.dumpData(self,record,out)

    class MelRaceIcon(MelString):
        """Most body data plus eyes for face. Load is controlled by MelRaceDistributor."""
        def __init__(self,attr,index):
            MelString.__init__(self,'ICON',attr)
            self.index = index
        def dumpData(self,record,out):
            out.packSub('INDX','I',self.index)
            MelString.dumpData(self,record,out)

    class MelRaceFaceGen(MelGroup):
        """Most fecegen data. Load is controlled by MelRaceDistributor."""
        def __init__(self,attr):
            MelGroup.__init__(self,attr,
                MelBase('FGGS','fggs_p'), ####FaceGen Geometry-Symmetric
                MelBase('FGGA','fgga_p'), ####FaceGen Geometry-Asymmetric
                MelBase('FGTS','fgts_p'), ####FaceGen Texture-Symmetric
                MelStruct('SNAM','2s',('snam_p',null2)))

    class MelRaceDistributor(MelNull):
        """Handles NAM0, NAM1, MNAM, FMAN and INDX records. Distributes load
        duties to other elements as needed."""
        def __init__(self):
            headAttrs = ('Head', 'Ears', 'Mouth', 'TeethLower', 'TeethUpper', 'Tongue', 'LeftEye', 'RightEye')
            bodyAttrs = ('UpperBody','LeftHand','RightHand','UpperBodyTexture')
            self.headModelAttrs = {
                'MNAM':tuple('male'+text for text in headAttrs),
                'FNAM':tuple('female'+text for text in headAttrs),
                }
            self.bodyModelAttrs = {
                'MNAM':tuple('male'+text for text in bodyAttrs),
                'FNAM':tuple('female'+text for text in bodyAttrs),
                }
            self.attrs = {
                'NAM0':self.headModelAttrs,
                'NAM1':self.bodyModelAttrs
                }
            self.facegenAttrs = {'MNAM':'maleFaceGen','FNAM':'femaleFaceGen'}
            self._debug = False

        def getSlotsUsed(self):
            return '_loadAttrs', '_modelAttrs'

        def getLoaders(self,loaders):
            """Self as loader for structure types."""
            for type_ in ('NAM0','NAM1','MNAM','FNAM','INDX'):
                loaders[type_] = self

        def setMelSet(self,melSet):
            """Set parent melset. Need this so that can reassign loaders later."""
            self.melSet = melSet
            self.loaders = {}
            for element in melSet.elements:
                attr = element.__dict__.get('attr',None)
                if attr: self.loaders[attr] = element

        def loadData(self, record, ins, sub_type, size_, readId):
            if sub_type in ('NAM0', 'NAM1'):
                record._modelAttrs = self.attrs[sub_type]
                return
            elif sub_type in ('MNAM', 'FNAM'):
                record._loadAttrs = record._modelAttrs[sub_type]
                attr = self.facegenAttrs.get(sub_type)
                element = self.loaders[attr]
                for sub_type in ('FGGS', 'FGGA', 'FGTS', 'SNAM'):
                    self.melSet.loaders[sub_type] = element
            else: #--INDX
                index, = ins.unpack('I',4,readId)
                attr = record._loadAttrs[index]
                element = self.loaders[attr]
                for sub_type in ('MODL', 'MODB', 'MODT', 'MODS', 'MODD', 'ICON', 'MICO'):
                    self.melSet.loaders[sub_type] = element

    #--Mel Set
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelString('DESC','text'),
        MelStructs('XNAM','I2i','relations',(FID,'faction'),'mod','groupCombatReaction'),
        MelStruct('DATA','14b2s4fI','skill1','skill1Boost','skill2','skill2Boost',
                  'skill3','skill3Boost','skill4','skill4Boost','skill5','skill5Boost',
                  'skill6','skill6Boost','skill7','skill7Boost',('unused1',null2),
                  'maleHeight','femaleHeight','maleWeight','femaleWeight',(_flags,'flags',0L)),
        MelFid('ONAM','Older'),
        MelFid('YNAM','Younger'),
        MelBase('NAM2','_nam2',''),
        MelRaceVoices('VTCK','2I',(FID,'maleVoice'),(FID,'femaleVoice')), #--0 same as race fid.
        MelOptStruct('DNAM','2I',(FID,'defaultHairMale',0L),(FID,'defaultHairFemale',0L)), #--0=None
        MelStruct('CNAM','2B','defaultHairColorMale','defaultHairColorFemale'), #--Int corresponding to GMST sHairColorNN
        MelOptStruct('PNAM','f','mainClamp'),
        MelOptStruct('UNAM','f','faceClamp'),
        MelStruct('ATTR','2B','maleBaseAttribute','femaleBaseAttribute'),
        #--Begin Indexed entries
        MelBase('NAM0','_nam0',''), ####Face Data Marker, wbEmpty
        MelBase('MNAM','_mnam',''),
        MelRaceHeadModel('maleHead',0),
        MelRaceIcon('maleEars',1),
        MelRaceHeadModel('maleMouth',2),
        MelRaceHeadModel('maleTeethLower',3),
        MelRaceHeadModel('maleTeethUpper',4),
        MelRaceHeadModel('maleTongue',5),
        MelRaceHeadModel('maleLeftEye',6),
        MelRaceHeadModel('maleRightEye',7),
        MelBase('FNAM','_fnam',''),
        MelRaceHeadModel('femaleHead',0),
        MelRaceIcon('femaleEars',1),
        MelRaceHeadModel('femaleMouth',2),
        MelRaceHeadModel('femaleTeethLower',3),
        MelRaceHeadModel('femaleTeethUpper',4),
        MelRaceHeadModel('femaleTongue',5),
        MelRaceHeadModel('femaleLeftEye',6),
        MelRaceHeadModel('femaleRightEye',7),
        MelBase('NAM1','_nam1',''), ####Body Data Marker, wbEmpty
        MelBase('MNAM','_mnam',''), ####Male Body Data Marker, wbEmpty
        MelRaceBodyModel('maleUpperBody',0),
        MelRaceBodyModel('maleLeftHand',1),
        MelRaceBodyModel('maleRightHand',2),
        MelRaceBodyModel('maleUpperBodyTexture',3),
        MelBase('FNAM','_fnam',''), ####Female Body Data Marker, wbEmpty
        MelRaceBodyModel('femaleUpperBody',0),
        MelRaceBodyModel('femaleLeftHand',1),
        MelRaceBodyModel('femaleRightHand',2),
        MelRaceBodyModel('femaleUpperBodyTexture',3),
        #--Normal Entries
        MelFidList('HNAM','hairs'),
        MelFidList('ENAM','eyes'),
        #--FaceGen Entries
        MelBase('MNAM','_mnam',''),
        MelRaceFaceGen('maleFaceGen'),
        MelBase('FNAM','_fnam',''),
        MelRaceFaceGen('femaleFaceGen'),
        #--Distributor for face and body entries.
        MelRaceDistributor(),
        )
    melSet.elements[-1].setMelSet(melSet)
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRcct(MelRecord):
    """Recipe Category."""
    classType = 'RCCT'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelStruct('DATA','=B','flags'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRcpe(MelRecord):
    """Recipe."""
    classType = 'RCPE'
    class MelRcpeDistributor(MelNull):
        def __init__(self):
            self._debug = False
        def getLoaders(self,loaders):
            """Self as loader for structure types."""
            for type_ in ('RCQY',):
                loaders[type_] = self
        def setMelSet(self,melSet):
            """Set parent melset. Need this so that can reassign loaders later."""
            self.melSet = melSet
            self.loaders = {}
            for element in melSet.elements:
                attr = element.__dict__.get('attr',None)
                if attr: self.loaders[attr] = element
        def loadData(self, record, ins, sub_type, size_, readId):
            if sub_type in ('RCQY',):
                outputs = record.__getattribute__('outputs')
                if outputs:
                    element = self.loaders['outputs']
                else:
                    element = self.loaders['ingredients']
            element.loadData(record, ins, sub_type, size_, readId)
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelConditions(),
        MelStruct('DATA','4I','skill','level',(FID,'category'),(FID,'subCategory')),
        MelGroups('ingredients',
            MelFid('RCIL','item'),
            MelStruct('RCQY','I','quantity'),
            ),
        MelGroups('outputs',
            MelFid('RCOD','item'),
            MelStruct('RCQY','I','quantity'),
            ),
        MelRcpeDistributor(),
        )
    melSet.elements[-1].setMelSet(melSet)
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
    _variableFlags = Flags(0L,Flags.getNames('isLongOrShort'))
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
                print ins.unpack(('%dB' % size_),size_)
                raise ModError(ins.inName,_('Unexpected size encountered for REFR:XLOC subrecord: ')+str(size_))
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
        MelOptStruct('XTRI','I','collisionLayer'),
        MelBase('XMBP','multiboundPrimitiveMarker'),
        MelOptStruct('XMBO','3f','boundHalfExtentsX','boundHalfExtentsY','boundHalfExtentsZ'),
        MelOptStruct('XTEL','I6fI',(FID,'destinationFid'),'destinationPosX','destinationPosY',
            'destinationPosZ','destinationRotX','destinationRotY','destinationRotZ',(_destinationFlags,'destinationFlags')),
        MelRefrXmrk('XMRK','',('hasXmrk',False),(_flags,'flags',0L),'full','markerType',('unused5',null1),(FID,'reputation')), ####Map Marker Start Marker, wbEmpty
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
        MelOptStruct('XLCM','i',('levelMod',None)),
        MelGroup('patrolData',
            MelStruct('XPRD','f','idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelStruct('SCHR','4s4I',('unused1',null4),'numRefs','compiledSize','lastIndex','scriptType'),
            MelBase('SCDA','compiled_p'),
            MelString('SCTX','scriptText'),
            MelGroups('vars',
                MelStruct('SLSD','I12sB7s','index',('unused1',null4+null4+null4),(_variableFlags,'flags',0L),('unused2',null4+null3)),
                MelString('SCVR','name')),
            MelScrxen('SCRV/SCRO','references'),
            MelFid('TNAM','topic'),
            ),
        MelOptStruct('XRDO','fIfI','rangeRadius','broadcastRangeType','staticPercentage',(FID,'positionReference')),
        MelOwnership(),
        MelRefrXloc('XLOC','B3sI4sB3s4s','lockLevel',('unused1',null3),(FID,'lockKey'),('unused2',null4),(_lockFlags,'lockFlags'),('unused3',null3),('unused4',null4)),
        MelOptStruct('XCNT','i','count'),
        MelOptStruct('XRDS','f','radius'),
        MelOptStruct('XHLP','f','health'),
        MelOptStruct('XRAD','f','radiation'),
        MelOptStruct('XCHG','f',('charge',None)),
        MelGroup('ammo',
            MelFid('XAMT','type'),
            MelStruct('XAMC','I','count'),
            ),
        MelStructs('XPWR','II','reflectedByWaters',(FID,'reference'),'type'),
        MelFids('XLTW','litWaters'),
        MelStructs('XDCR','II','linkedDecals',(FID,'reference'),'unknown'), # ??
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelStruct('XAPD','B','flags'),
            MelStructs('XAPR','If','activateParentRefs',(FID,'reference'),'delay')
            ),
        MelString('XATO','activationPrompt'),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_parentFlags,'parentFlags'),('unused6',null3)),
        MelOptStruct('XEMI','I',(FID,'emittance')),
        MelFid('XMBR','multiboundReference'),
        MelOptStruct('XACT','I',(_actFlags,'actFlags',0L)), ####Action Flag
        MelBase('ONAM','onam_p'), ####Open by Default, wbEmpty
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
        MelOptStruct('XLOD','3f',('lod1',None),('lod2',None),('lod3',None)), ####Distant LOD Data, unknown
        MelOptStruct('XSCL','f',('scale',1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),

        ##Oblivion subrecords
        #MelOptStruct('XHLT','i',('health',None)),
        #MelXpci('XPCI'), ####fid, unknown
        #MelFid('XRTM','xrtm'), ####unknown
        #MelOptStruct('XSOL','B',('soul',None)), ####Was entirely missing. Confirmed by creating a test mod...it isn't present in any of the official esps
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRegn(MelRecord):
    """Region record."""
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

    ####Lazy hacks to correctly read/write regn data
    class MelRegnStructA(MelStructA):
        """Handler for regn record. Conditionally dumps next items."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if record.entryType == 2 and self.subType == 'RDOT':
                MelStructA.loadData(self, record, ins, sub_type, size_, readId)
            elif record.entryType == 3 and self.subType == 'RDWT':
                MelStructA.loadData(self, record, ins, sub_type, size_, readId)
            elif record.entryType == 6 and self.subType == 'RDGS':
                MelStructA.loadData(self, record, ins, sub_type, size_, readId)
            elif record.entryType == 7 and self.subType == 'RDSD':
                MelStructA.loadData(self, record, ins, sub_type, size_, readId)

        def dumpData(self,record,out):
            """Conditionally dumps data."""
            if record.entryType == 2 and self.subType == 'RDOT':
                MelStructA.dumpData(self,record,out)
            elif record.entryType == 3 and self.subType == 'RDWT':
                MelStructA.dumpData(self,record,out)
            elif record.entryType == 6 and self.subType == 'RDGS':
                MelStructA.dumpData(self,record,out)
            elif record.entryType == 7 and self.subType == 'RDSD':
                MelStructA.dumpData(self,record,out)

    class MelRegnString(MelString):
        """Handler for regn record. Conditionally dumps next items."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if record.entryType == 4 and self.subType == 'RDMP':
                MelString.loadData(self, record, ins, sub_type, size_, readId)
            elif record.entryType == 5 and self.subType == 'ICON':
                MelString.loadData(self, record, ins, sub_type, size_, readId)

        def dumpData(self,record,out):
            """Conditionally dumps data."""
            if record.entryType == 4 and self.subType == 'RDMP':
                MelString.dumpData(self,record,out)
            elif record.entryType == 5 and self.subType == 'ICON':
                MelString.dumpData(self,record,out)

    class MelRegnOptStruct(MelOptStruct):
        """Handler for regn record. Conditionally dumps next items."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if record.entryType == 7 and self.subType == 'RDMD':
                MelOptStruct.loadData(self, record, ins, sub_type, size_, readId)

        def dumpData(self,record,out):
            """Conditionally dumps data."""
            if record.entryType == 7 and self.subType == 'RDMD':
                MelOptStruct.dumpData(self,record,out)

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelStruct('RCLR','3Bs','mapRed','mapBlue','mapGreen',('unused1',null1)),
        MelFid('WNAM','worldspace'),
        MelGroups('areas',
            MelStruct('RPLI','I','edgeFalloff'),
            MelStructA('RPLD','2f','points','posX','posY')),
        MelGroups('entries',
            #2:Objects,3:Weather,4:Map,5:Land,6:Grass,7:Sound
            MelStruct('RDAT', 'I2B2s','entryType', (rdatFlags,'flags'), 'priority',
                     ('unused1',null2)),
            MelRegnStructA('RDOT', 'IH2sf4B2H4s4f3H2s4s', 'objects', (FID,'objectId'),
                           'parentIndex',('unused1',null2), 'density', 'clustering',
                           'minSlope', 'maxSlope',(obflags, 'flags'), 'radiusWRTParent',
                           'radius', ('unk1',null4),'maxHeight', 'sink', 'sinkVar',
                           'sizeVar', 'angleVarX','angleVarY',  'angleVarZ',
                           ('unused2',null2), ('unk2',null4)),
            MelRegnString('RDMP', 'mapName'),
            MelRegnStructA('RDGS', 'I4s', 'grass', ('unknown',null4)),
            MelRegnOptStruct('RDMD', 'I', 'musicType'),
            MelFid('RDMO','music'),
            MelFid('RDSI','incidentalMediaSet'),
            MelFids('RDSB','battleMediaSets'),
            MelRegnStructA('RDSD', '3I', 'sounds', (FID, 'sound'), (sdflags, 'flags'), 'chance'),
            MelRegnStructA('RDWT', '3I', 'weather', (FID, 'weather', None), 'chance', (FID, 'global', None)),
            MelFidList('RDID','imposters')),
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
        MelStruct('DATA','f','value'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSlpd(MelRecord):
    """Sleep deprivation stage record."""
    classType = 'SLPD'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('DATA','2I','trigerThreshold',(FID,'actorEffect')),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSoun(MelRecord):
    """Sound record."""
    classType = 'SOUN'

    # {0x0001} 'Random Frequency Shift',
    # {0x0002} 'Play At Random',
    # {0x0004} 'Environment Ignored',
    # {0x0008} 'Random Location',
    # {0x0010} 'Loop',
    # {0x0020} 'Menu Sound',
    # {0x0040} '2D',
    # {0x0080} '360 LFE',
    # {0x0100} 'Dialogue Sound',
    # {0x0200} 'Envelope Fast',
    # {0x0400} 'Envelope Slow',
    # {0x0800} '2D Radius',
    # {0x1000} 'Mute When Submerged',
    # {0x2000} 'Start at Random Position'
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
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FNAM','soundFile'),
        MelStruct('RNAM','B','_rnam'),
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
    """Static model record."""
    classType = 'STAT'

    # passthroughSound
    # -1, 'NONE'
    #  0, 'BushA',
    #  1, 'BushB',
    #  2, 'BushC',
    #  3, 'BushD',
    #  4, 'BushE',
    #  5, 'BushF',
    #  6, 'BushG',
    #  7, 'BushH',
    #  8, 'BushI',
    #  9, 'BushJ'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelModel(),
        MelStruct('BRUS','=b',('passthroughSound',-1)),
        MelFid('RNAM','soundRandomLooping'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreTact(MelRecord):
    """Talking activator record."""
    classType = 'TACT'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
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
    """Weapon record."""
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
                #--Else 124 byte record (skips sightUsage, semiAutomaticFireDelayMin and semiAutomaticFireDelayMax...
                unpacked = ins.unpack('IffBBBBfffffIBBBBffIIfffffffffffiIffi', size_, readId)
            elif size_ == 120:
                #--Else 120 byte record (skips resistType, sightUsage, semiAutomaticFireDelayMin and semiAutomaticFireDelayMax...
                unpacked = ins.unpack('IffBBBBfffffIBBBBffIIfffffffffffiIff', size_, readId)
            else:
                raise "Unexpected size encountered for WEAP:DNAM subrecord: %s" % size_
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
                raise "Unexpected size encountered for WEAP:VATS subrecord: %s" % size_
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelModel('model'),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelFid('SCRI','script'),
        MelFid('EITM','objectEffect'),
        MelOptStruct('EAMT','H','objectEffectPoints'),
        MelFid('NAM0','ammo'),
        MelDestructible(),
        MelFid('REPL','repairList'),
        #-1:None,0:Big Guns,1:Energy Weapons,2:Small Guns,3:Melee Weapons,
        #4:Unarmed Weapon,5:Thrown Weapons,6:Mine,7:Body Wear,8:Head Wear,
        #9:Hand Wear,10:Chems,11:Stimpack,12:Food,13:Alcohol
        MelStruct('ETYP','i',('etype',-1)),
        MelFid('BIPL','bipedModelList'),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelModel('shellCasingModel',2),
        MelModel('scopeModel',3),
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
            ## Following code works completely, but it's depend on the implementation of MelStructA.loadData and MelStruct.loadData.
            # newFormat = self.format
            # self.format = oldFormat # temporarily set to older format
            # MelStructA.loadData(self,record,ins,type,size,readId)
            # self.format = newFormat
            ## Following code is redundant but independent and robust.
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
            raise ModSizeError(record.inName, record.recType +'.' + sub_type, (96 if sub_type == 'PNAM' else 240), size_, True)

class MreWthr(MelRecord):
    """Weather record."""
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
