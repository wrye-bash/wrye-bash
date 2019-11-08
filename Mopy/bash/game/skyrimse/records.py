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
"""This module contains the skyrim SE record classes. The great majority are
imported from skyrim."""
# Set MelModel in brec, in this case it's identical to the skyrim one
from ..skyrim.records import MelBounds, MelDestructible, MelKeywords, MelVmad
from ...bolt import Flags
from ...brec import MelModel # set in Mopy/bash/game/skyrim/records.py
from ...brec import MelRecord, MelStructs, MelObject, MelGroups, MelStruct, \
    FID, MelString, MelSet, MelFid, MelOptStruct, MelFids, MelBase, \
    MelStructA, MelLString, MelFloat, MelUInt8, MelUInt16, MelUInt32, \
    MelCounter, null1, null2, null3, null4
from ...exception import ModSizeError
# Those are unused here, but need be in this file as are accessed via it
from ..skyrim.records import MreHeader, MreGmst

#------------------------------------------------------------------------------
# Updated for SSE -------------------------------------------------------------
#------------------------------------------------------------------------------
class MreAmmo(MelRecord):
    """Ammunition."""
    classType = 'AMMO'

    AmmoTypeFlags = Flags(0L,Flags.getNames(
        (0, 'notNormalWeapon'),
        (1, 'nonPlayable'),
        (2, 'nonBolt'),
    ))

    class MelAmmoData(MelStruct):
        """Handle older truncated DATA for AMMO subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 20:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 16:
                unpacked = ins.unpack('IIfI', size_, readId)
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
        MelLString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelLString('DESC','description'),
        MelKeywords(),
        MelAmmoData('DATA', 'IIfIf', (FID, 'projectile'),
            (AmmoTypeFlags, 'flags', 0L), ('damage', 1.0), ('value', 0),
            ('weight', 0.1)),
        MelString('ONAM','onam_n'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLtex(MelRecord):
    """Landscape Texture."""
    classType = 'LTEX'

    LtexSnowFlags = Flags(0L,Flags.getNames(
            (0, 'snow'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelFid('TNAM','textureSet',),
        MelFid('MNAM','materialType',),
        MelStruct('HNAM','BB','friction','restitution',),
        MelUInt8('SNAM', 'textureSpecularExponent'),
        MelFids('GNAM','grasses'),
        MelUInt32('INAM', (LtexSnowFlags, 'flags', 0L)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMato(MelRecord):
    """Material Object."""
    classType = 'MATO'

    MatoTypeFlags = Flags(0L,Flags.getNames(
            (0, 'singlePass'),
        ))

    MatoSnowFlags = Flags(0L,Flags.getNames(
            (0, 'snow'),
        ))

    class MelMatoData(MelStruct):
        """Handle older truncated DATA for MATO subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 52:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 48: # old skyrim record
                unpacked = ins.unpack('11fI', size_, readId)
            else:
                raise ModSizeError(ins.inName, readId, (52, 48), size_)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()

    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelGroups('property_data',
            MelBase('DNAM', 'data_entry'),
        ),
        MelMatoData('DATA','11fIB3s','falloffScale','falloffBias',
                    'noiseUVScale','materialUVScale','projectionVectorX',
                    'projectionVectorY','projectionVectorZ','normalDampener',
                    'singlePassColorRed','singlePassColorGreen',
                    'singlePassColorBlue',
                    (MatoTypeFlags,'singlePassFlags',0L),
                    (MatoSnowFlags,'snowflags',0L),'unkMato1'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreStat(MelRecord):
    """Static."""
    classType = 'STAT'

    _StatSnowFlags = Flags(0L, Flags.getNames(
        (0, 'consideredSnow'),
    ))

    class MelStatDnam(MelStruct):
        """Handle older truncated DNAM for STAT subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 12:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 8: # old skyrim record
                unpacked = ins.unpack('fI', size_, readId)
            else:
                raise ModSizeError(ins.inName, readId, (12, 8), size_)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()

    melSet = MelSet(
        MelString('EDID', 'eid'),
        MelBounds(),
        MelModel(),
        MelStatDnam('DNAM', 'fIB3s', 'maxAngle30to120', (FID, 'material'),
                    (_StatSnowFlags, 'snowFlags', 0L), ('unknown1', null3),),
        # Contains null-terminated mesh filename followed by random data
        # up to 260 bytes and repeats 4 times
        MelBase('MNAM', 'distantLOD'),
        MelBase('ENAM', 'unknownENAM'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWatr(MelRecord):
    """Water."""
    classType = 'WATR'

    WatrTypeFlags = Flags(0L,Flags.getNames(
            (0, 'causesDamage'),
        ))

    class MelWatrDnam(MelStruct):
        """Handle older truncated DNAM for WATR subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 232:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 228: # old skyrim record
                unpacked = ins.unpack('7f4s2f3Bs3Bs3Bs4s43f', size_, readId)
            else:
                raise ModSizeError(ins.inName, readId, (232, 228), size_)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()

    melSet = MelSet(
        MelString('EDID','eid'),
        MelLString('FULL','full'),
        MelGroups('unused',
            MelString('NNAM','noiseMap',),
        ),
        MelUInt8('ANAM', 'opacity'),
        MelUInt8('FNAM', (WatrTypeFlags, 'flags', 0L)),
        MelBase('MNAM','unused1'),
        MelFid('TNAM','material',),
        MelFid('SNAM','openSound',),
        MelFid('XNAM','spell',),
        MelFid('INAM','imageSpace',),
        MelUInt16('DATA', 'damagePerSecond'),
        MelWatrDnam('DNAM','7f4s2f3Bs3Bs3Bs4s44f','unknown1','unknown2','unknown3',
                  'unknown4','specularPropertiesSunSpecularPower',
                  'waterPropertiesReflectivityAmount',
                  'waterPropertiesFresnelAmount',('unknown5',null4),
                  'fogPropertiesAboveWaterFogDistanceNearPlane',
                  'fogPropertiesAboveWaterFogDistanceFarPlane',
                  # Shallow Color
                  'red_sc','green_sc','blue_sc','unknown_sc',
                  # Deep Color
                  'red_dc','green_dc','blue_dc','unknown_dc',
                  # Reflection Color
                  'red_rc','green_rc','blue_rc','unknown_rc',
                  ('unknown6',null4),'unknown7','unknown8','unknown9','unknown10',
                  'displacementSimulatorStartingSize',
                  'displacementSimulatorForce','displacementSimulatorVelocity',
                  'displacementSimulatorFalloff','displacementSimulatorDampner',
                  'unknown11','noisePropertiesNoiseFalloff',
                  'noisePropertiesLayerOneWindDirection',
                  'noisePropertiesLayerTwoWindDirection',
                  'noisePropertiesLayerThreeWindDirection',
                  'noisePropertiesLayerOneWindSpeed',
                  'noisePropertiesLayerTwoWindSpeed',
                  'noisePropertiesLayerThreeWindSpeed',
                  'unknown12','unknown13','fogPropertiesAboveWaterFogAmount',
                  'unknown14','fogPropertiesUnderWaterFogAmount',
                  'fogPropertiesUnderWaterFogDistanceNearPlane',
                  'fogPropertiesUnderWaterFogDistanceFarPlane',
                  'waterPropertiesRefractionMagnitude',
                  'specularPropertiesSpecularPower',
                  'unknown15','specularPropertiesSpecularRadius',
                  'specularPropertiesSpecularBrightness',
                  'noisePropertiesLayerOneUVScale',
                  'noisePropertiesLayerTwoUVScale',
                  'noisePropertiesLayerThreeUVScale',
                  'noisePropertiesLayerOneAmplitudeScale',
                  'noisePropertiesLayerTwoAmplitudeScale',
                  'noisePropertiesLayerThreeAmplitudeScale',
                  'waterPropertiesReflectionMagnitude',
                  'specularPropertiesSunSparkleMagnitude',
                  'specularPropertiesSunSpecularMagnitude',
                  'depthPropertiesReflections','depthPropertiesRefraction',
                  'depthPropertiesNormals','depthPropertiesSpecularLighting',
                  'specularPropertiesSunSparklePower',
                  'noisePropertiesFlowmapScale'),
        MelBase('GNAM','unused2'),
        # Linear Velocity
        MelStruct('NAM0','3f','linv_x','linv_y','linv_z',),
        # Angular Velocity
        MelStruct('NAM1','3f','andv_x','andv_y','andv_z',),
        MelString('NAM2','noiseTextureLayer1'),
        MelString('NAM3','noiseTextureLayer2'),
        MelString('NAM4','noiseTextureLayer3'),
        MelString('NAM5','flowNormalsNoiseTexture'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWeap(MelRecord):
    """Weapon."""
    classType = 'WEAP'

    WeapFlags3 = Flags(0L,Flags.getNames(
        (0, 'onDeath'),
    ))

    WeapFlags2 = Flags(0L,Flags.getNames(
            (0, 'playerOnly'),
            (1, 'nPCsUseAmmo'),
            (2, 'noJamAfterReloadunused'),
            (3, 'unknown4'),
            (4, 'minorCrime'),
            (5, 'rangeFixed'),
            (6, 'notUsedinNormalCombat'),
            (7, 'unknown8'),
            (8, 'don'),
            (9, 'unknown10'),
            (10, 'rumbleAlternate'),
            (11, 'unknown12'),
            (12, 'nonhostile'),
            (13, 'boundWeapon'),
        ))

    WeapFlags1 = Flags(0L,Flags.getNames(
            (0, 'ignoresNormalWeaponResistance'),
            (1, 'automaticunused'),
            (2, 'hasScopeunused'),
            (3, 'can'),
            (4, 'hideBackpackunused'),
            (5, 'embeddedWeaponunused'),
            (6, 'don'),
            (7, 'nonplayable'),
        ))

    class MelWeapCrdt(MelStruct):
        """Handle older truncated CRDT for WEAP subrecord.

           Old Skyrim format H2sfB3sI FormID is the last integer.

           New Format H2sfB3s4sI4s FormID is the integer priot to the
           last 4S. Bethesda did not append the record they inserted bytes
           which shifts the FormID 4 bytes. """
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 24:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 16:
                # old skyrim record, insert null bytes in the middle(!)
                ##: Why use null3 instead of _crdUnk2?
                critDamage, crdtUnk1, criticalMultiplier, criticalFlags, \
                _crdtUnk2, criticalEffect = ins.unpack('H2sfB3sI', size_,
                                                      readId)
                unpacked = (critDamage, crdtUnk1, criticalMultiplier,
                            criticalFlags, null3, null4, criticalEffect, null4)
            else:
                raise ModSizeError(ins.inName, readId, (24, 16), size_)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()

    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel('model1','MODL'),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelFid('EITM','enchantment',),
        MelUInt16('EAMT', 'enchantPoints'),
        MelDestructible(),
        MelFid('ETYP','equipmentType',),
        MelFid('BIDS','blockBashImpactDataSet',),
        MelFid('BAMT','alternateBlockMaterial',),
        MelFid('YNAM','pickupSound',),
        MelFid('ZNAM','dropSound',),
        MelKeywords(),
        MelLString('DESC','description'),
        MelModel('model2','MOD3'),
        MelBase('NNAM','unused1'),
        MelFid('INAM','impactDataSet',),
        MelFid('WNAM','firstPersonModelObject',),
        MelFid('SNAM','attackSound',),
        MelFid('XNAM','attackSound2D',),
        MelFid('NAM7','attackLoopSound',),
        MelFid('TNAM','attackFailSound',),
        MelFid('UNAM','idleSound',),
        MelFid('NAM9','equipSound',),
        MelFid('NAM8','unequipSound',),
        MelStruct('DATA','IfH','value','weight','damage',),
        MelStruct('DNAM','B3s2fH2sf4s4B2f2I5f12si8si4sf','animationType',
                  ('dnamUnk1',null3),'speed','reach',
                  (WeapFlags1,'dnamFlags1',None),('dnamUnk2',null2),'sightFOV',
                  ('dnamUnk3',null4),'baseVATSToHitChance','attackAnimation',
                  'numProjectiles','embeddedWeaponAVunused','minRange',
                  'maxRange','onHit',(WeapFlags2,'dnamFlags2',None),
                  'animationAttackMultiplier',('dnamUnk4',0.0),
                  'rumbleLeftMotorStrength','rumbleRightMotorStrength',
                  'rumbleDuration',('dnamUnk5',null4+null4+null4),'skill',
                  ('dnamUnk6',null4+null4),'resist',('dnamUnk7',null4),'stagger',),
        MelWeapCrdt('CRDT','H2sfB3s4sI4s',('critDamage',0),('crdtUnk1',null2),
                    ('criticalMultiplier',1.0),(WeapFlags3,'criticalFlags',0L),
                    ('crdtUnk2',null3),('crdtUnk3',null4),
                    (FID,'criticalEffect',None),('crdtUnk4',null4),),
        MelUInt32('VNAM', 'detectionSoundLevel'),
        MelFid('CNAM','template',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWthr(MelRecord):
    """Weather."""
    classType = 'WTHR'

    WthrFlags2 = Flags(0L,Flags.getNames(
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
        ))

    WthrFlags1 = Flags(0L,Flags.getNames(
            (0, 'weatherPleasant'),
            (1, 'weatherCloudy'),
            (2, 'weatherRainy'),
            (3, 'weatherSnow'),
            (4, 'skyStaticsAlwaysVisible'),
            (5, 'skyStaticsFollowsSunPosition'),
        ))

    class MelWthrDalc(MelStructs):
        """Handle older truncated DALC for WTHR subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 32:
                MelStructs.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 24:
                unpacked = ins.unpack('=4B4B4B4B4B4B', size_, readId)
            else:
                raise ModSizeError(ins.inName, readId, (32, 24), size_)
            unpacked += self.defaults[len(unpacked):]
            target = MelObject()
            record.__getattribute__(self.attr).append(target)
            target.__slots__ = self.attrs
            setter = target.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('\x300TX','cloudTextureLayer_0'),
        MelString('\x310TX','cloudTextureLayer_1'),
        MelString('\x320TX','cloudTextureLayer_2'),
        MelString('\x330TX','cloudTextureLayer_3'),
        MelString('\x340TX','cloudTextureLayer_4'),
        MelString('\x350TX','cloudTextureLayer_5'),
        MelString('\x360TX','cloudTextureLayer_6'),
        MelString('\x370TX','cloudTextureLayer_7'),
        MelString('\x380TX','cloudTextureLayer_8'),
        MelString('\x390TX','cloudTextureLayer_9'),
        MelString('\x3A0TX','cloudTextureLayer_10'),
        MelString('\x3B0TX','cloudTextureLayer_11'),
        MelString('\x3C0TX','cloudTextureLayer_12'),
        MelString('\x3D0TX','cloudTextureLayer_13'),
        MelString('\x3E0TX','cloudTextureLayer_14'),
        MelString('\x3F0TX','cloudTextureLayer_15'),
        MelString('\x400TX','cloudTextureLayer_16'),
        MelString('A0TX','cloudTextureLayer_17'),
        MelString('B0TX','cloudTextureLayer_18'),
        MelString('C0TX','cloudTextureLayer_19'),
        MelString('D0TX','cloudTextureLayer_20'),
        MelString('E0TX','cloudTextureLayer_21'),
        MelString('F0TX','cloudTextureLayer_22'),
        MelString('G0TX','cloudTextureLayer_23'),
        MelString('H0TX','cloudTextureLayer_24'),
        MelString('I0TX','cloudTextureLayer_25'),
        MelString('J0TX','cloudTextureLayer_26'),
        MelString('K0TX','cloudTextureLayer_27'),
        MelString('L0TX','cloudTextureLayer_28'),
        MelBase('DNAM','dnam_p'),
        MelBase('CNAM','cnam_p'),
        MelBase('ANAM','anam_p'),
        MelBase('BNAM','bnam_p'),
        MelBase('LNAM','lnam_p'),
        MelFid('MNAM','precipitationType',),
        MelFid('NNAM','visualEffect',),
        MelBase('ONAM','onam_p'),
        MelBase('RNAM','cloudSpeedY'),
        MelBase('QNAM','cloudSpeedX'),
        MelStructA('PNAM','3Bs3Bs3Bs3Bs','cloudColors',
            'riseRedPnam','riseGreenPnam','riseBluePnam',('unused1',null1),
            'dayRedPnam','dayGreenPnam','dayBluePnam',('unused2',null1),
            'setRedPnam','setGreenPnam','setBluePnam',('unused3Pnam',null1),
            'nightRedPnam','nightGreenPnam','nightBluePnam',('unused4',null1)),
        MelStructA('JNAM','4f','cloudAlphas','sunAlpha','dayAlpha','setAlpha','nightAlpha',),
        MelStructA('NAM0','3Bs3Bs3Bs3Bs','daytimeColors',
            'riseRed','riseGreen','riseBlue',('unused5',null1),
            'dayRed','dayGreen','dayBlue',('unused6',null1),
            'setRed','setGreen','setBlue',('unused7',null1),
            'nightRed','nightGreen','nightBlue',('unused8',null1)),
        MelStruct('FNAM','8f','dayNear','dayFar','nightNear','nightFar',
                  'dayPower','nightPower','dayMax','nightMax',),
        MelStruct('DATA','B2s16B','windSpeed',('unknown',null2),'transDelta',
                  'sunGlare','sunDamage','precipitationBeginFadeIn',
                  'precipitationEndFadeOut','thunderLightningBeginFadeIn',
                  'thunderLightningEndFadeOut','thunderLightningFrequency',
                  (WthrFlags1,'wthrFlags1',0L),'red','green','blue',
                  'visualEffectBegin','visualEffectEnd',
                  'windDirection','windDirectionRange',),
        MelUInt32('NAM1', (WthrFlags2, 'wthrFlags2', 0L)),
        MelStructs('SNAM','2I','sounds',(FID,'sound'),'type'),
        MelFids('TNAM','skyStatics',),
        MelStruct('IMSP','4I',(FID,'imageSpacesSunrise'),(FID,'imageSpacesDay'),
                  (FID,'imageSpacesSunset'),(FID,'imageSpacesNight'),),
        MelOptStruct('HNAM','4I',(FID,'volumetricLightingSunrise'),
                  (FID,'volumetricLightingDay'),
                  (FID,'volumetricLightingSunset'),
                  (FID,'volumetricLightingNight'),),
        MelWthrDalc('DALC','=4B4B4B4B4B4B4Bf','wthrAmbientColors',
            'redXplus','greenXplus','blueXplus','unknownXplus',
            'redXminus','greenXminus','blueXminus','unknownXminus',
            'redYplus','greenYplus','blueYplus','unknownYplus',
            'redYminus','greenYminus','blueYminus','unknownYminus',
            'redZplus','greenZplus','blueZplus','unknownZplus',
            'redZminus','greenZminus','blueZminus','unknownZminus',
            'redSpec','greenSpec','blueSpec','unknownSpec',
            'fresnelPower'),
        MelBase('NAM2','nam2_p'),
        MelBase('NAM3','nam3_p'),
        MelModel('aurora','MODL'),
        MelFid('GNAM', 'sunGlareLensFlare',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Added in SSE ----------------------------------------------------------------
#------------------------------------------------------------------------------
class MreVoli(MelRecord):
    """Volumetric Lighting."""
    classType = 'VOLI'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelFloat('CNAM', 'intensity'),
        MelFloat('DNAM', 'customColorContribution'),
        MelFloat('ENAM', 'red'),
        MelFloat('FNAM', 'green'),
        MelFloat('GNAM', 'blue'),
        MelFloat('HNAM', 'densityContribution'),
        MelFloat('INAM', 'densitySize'),
        MelFloat('JNAM', 'densityWindSpeed'),
        MelFloat('KNAM', 'densityFallingSpeed'),
        MelFloat('LNAM', 'phaseFunctionContribution'),
        MelFloat('MNAM', 'phaseFunctionScattering'),
        MelFloat('NNAM', 'samplingRepartitionRangeFactor'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLens(MelRecord):
    """Lens Flare."""
    classType = 'LENS'

    LensFlareFlags = Flags(0L,Flags.getNames(
            (0, 'rotates'),
            (1, 'shrinksWhenOccluded'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelFloat('CNAM', 'colorInfluence'),
        MelFloat('DNAM', 'fadeDistanceRadiusScale'),
        MelCounter(MelUInt32('LFSP', 'sprite_count'),
                   counts='lensFlareSprites'),
        MelGroups('lensFlareSprites',
            MelString('DNAM','spriteID'),
            MelString('FNAM','texture'),
            MelStruct('LFSD', 'f8I', 'tintRed', 'tintGreen', 'tintBlue',
                'width', 'height', 'position', 'angularFade', 'opacity',
                (LensFlareFlags, 'lensFlags', 0L), ),
        )
    ).with_distributor({
        'DNAM': 'fadeDistanceRadiusScale',
        'LFSP': {
            'DNAM': 'lensFlareSprites',
        },
    })
    __slots__ = melSet.getSlotsUsed()
