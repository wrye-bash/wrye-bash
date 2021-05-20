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
"""This package contains the Fallout 3 specific patchers. This module
contains the data structures that are dynamically set on a per game basis in
bush."""
# ***no imports!***

# Function Info ---------------------------------------------------------------
# Needs to be public so we can import it for FNV
# 0: no param; 1: int param; 2: formid param; 3: float param

condition_function_data = {
    1:    (u'GetDistance', 2, 0),
    5:    (u'GetLocked', 0, 0),
    6:    (u'GetPos', 0, 0),
    8:    (u'GetAngle', 0, 0),
    10:   (u'GetStartingPos', 0, 0),
    11:   (u'GetStartingAngle', 0, 0),
    12:   (u'GetSecondsPassed', 0, 0),
    14:   (u'GetActorValue', 2, 0),
    18:   (u'GetCurrentTime', 0, 0),
    24:   (u'GetScale', 0, 0),
    25:   (u'IsMoving', 0, 0),
    26:   (u'IsTurning', 0, 0),
    27:   (u'GetLineOfSight', 2, 0),
    32:   (u'GetInSameCell', 2, 0),
    35:   (u'GetDisabled', 0, 0),
    36:   (u'MenuMode', 1, 0),
    39:   (u'GetDisease', 0, 0),
    40:   (u'GetVampire', 0, 0),
    41:   (u'GetClothingValue', 0, 0),
    42:   (u'SameFaction', 2, 0),
    43:   (u'SameRace', 2, 0),
    44:   (u'SameSex', 2, 0),
    45:   (u'GetDetected', 2, 0),
    46:   (u'GetDead', 0, 0),
    47:   (u'GetItemCount', 2, 0),
    48:   (u'GetGold', 0, 0),
    49:   (u'GetSleeping', 0, 0),
    50:   (u'GetTalkedToPC', 0, 0),
    53:   (u'GetScriptVariable', 2, 0),
    56:   (u'GetQuestRunning', 2, 0),
    58:   (u'GetStage', 2, 0),
    59:   (u'GetStageDone', 2, 1),
    60:   (u'GetFactionRankDifference', 2, 2),
    61:   (u'GetAlarmed', 0, 0),
    62:   (u'IsRaining', 0, 0),
    63:   (u'GetAttacked', 0, 0),
    64:   (u'GetIsCreature', 0, 0),
    65:   (u'GetLockLevel', 0, 0),
    66:   (u'GetShouldAttack', 2, 0),
    67:   (u'GetInCell', 2, 0),
    68:   (u'GetIsClass', 2, 0),
    69:   (u'GetIsRace', 2, 0),
    70:   (u'GetIsSex', 1, 0),
    71:   (u'GetInFaction', 2, 0),
    72:   (u'GetIsID', 2, 0),
    73:   (u'GetFactionRank', 2, 0),
    74:   (u'GetGlobalValue', 2, 0),
    75:   (u'IsSnowing', 0, 0),
    76:   (u'GetDisposition', 2, 0),
    77:   (u'GetRandomPercent', 0, 0),
    79:   (u'GetQuestVariable', 2, 0),
    80:   (u'GetLevel', 0, 0),
    81:   (u'GetArmorRating', 0, 0),
    84:   (u'GetDeadCount', 2, 0),
    91:   (u'GetIsAlerted', 0, 0),
    98:   (u'GetPlayerControlsDisabled', 1, 1),
    99:   (u'GetHeadingAngle', 2, 0),
    101:  (u'IsWeaponOut', 0, 0),
    102:  (u'IsTorchOut', 0, 0),
    103:  (u'IsShieldOut', 0, 0),
    106:  (u'IsFacingUp', 0, 0),
    107:  (u'GetKnockedState', 0, 0),
    108:  (u'GetWeaponAnimType', 0, 0),
    109:  (u'IsWeaponSkillType', 2, 0),
    110:  (u'GetCurrentAIPackage', 0, 0),
    111:  (u'IsWaiting', 0, 0),
    112:  (u'IsIdlePlaying', 0, 0),
    116:  (u'GetMinorCrimeCount', 0, 0),
    117:  (u'GetMajorCrimeCount', 0, 0),
    118:  (u'GetActorAggroRadiusViolated', 0, 0),
    122:  (u'GetCrime', 2, 1),
    123:  (u'IsGreetingPlayer', 0, 0),
    125:  (u'IsGuard', 0, 0),
    127:  (u'HasBeenEaten', 0, 0),
    128:  (u'GetFatiguePercentage', 0, 0),
    129:  (u'GetPCIsClass', 2, 0),
    130:  (u'GetPCIsRace', 2, 0),
    131:  (u'GetPCIsSex', 1, 0),
    132:  (u'GetPCInFaction', 2, 0),
    133:  (u'SameFactionAsPC', 0, 0),
    134:  (u'SameRaceAsPC', 0, 0),
    135:  (u'SameSexAsPC', 0, 0),
    136:  (u'GetIsReference', 2, 0),
    141:  (u'IsTalking', 0, 0),
    142:  (u'GetWalkSpeed', 0, 0),
    143:  (u'GetCurrentAIProcedure', 0, 0),
    144:  (u'GetTrespassWarningLevel', 0, 0),
    145:  (u'IsTrespassing', 0, 0),
    146:  (u'IsInMyOwnedCell', 0, 0),
    147:  (u'GetWindSpeed', 0, 0),
    148:  (u'GetCurrentWeatherPercent', 0, 0),
    149:  (u'GetIsCurrentWeather', 2, 0),
    150:  (u'IsContinuingPackagePCNear', 0, 0),
    153:  (u'CanHaveFlames', 0, 0),
    154:  (u'HasFlames', 0, 0),
    157:  (u'GetOpenState', 0, 0),
    159:  (u'GetSitting', 0, 0),
    160:  (u'GetFurnitureMarkerID', 0, 0),
    161:  (u'GetIsCurrentPackage', 2, 0),
    162:  (u'IsCurrentFurnitureRef', 2, 0),
    163:  (u'IsCurrentFurnitureObj', 2, 0),
    170:  (u'GetDayOfWeek', 0, 0),
    172:  (u'GetTalkedToPCParam', 2, 0),
    175:  (u'IsPCSleeping', 0, 0),
    176:  (u'IsPCAMurderer', 0, 0),
    180:  (u'GetDetectionLevel', 2, 0),
    182:  (u'GetEquipped', 2, 0),
    185:  (u'IsSwimming', 0, 0),
    190:  (u'GetAmountSoldStolen', 0, 0),
    192:  (u'GetIgnoreCrime', 0, 0),
    193:  (u'GetPCExpelled', 2, 0),
    195:  (u'GetPCFactionMurder', 2, 0),
    197:  (u'GetPCEnemyofFaction', 2, 0),
    199:  (u'GetPCFactionAttack', 2, 0),
    203:  (u'GetDestroyed', 0, 0),
    214:  (u'HasMagicEffect', 2, 0),
    215:  (u'GetDefaultOpen', 0, 0),
    219:  (u'GetAnimAction', 0, 0),
    223:  (u'IsSpellTarget', 2, 0),
    224:  (u'GetVATSMode', 0, 0),
    225:  (u'GetPersuasionNumber', 0, 0),
    226:  (u'GetSandman', 0, 0),
    227:  (u'GetCannibal', 0, 0),
    228:  (u'GetIsClassDefault', 2, 0),
    229:  (u'GetClassDefaultMatch', 0, 0),
    230:  (u'GetInCellParam', 2, 2),
    235:  (u'GetVatsTargetHeight', 0, 0),
    237:  (u'GetIsGhost', 0, 0),
    242:  (u'GetUnconscious', 0, 0),
    244:  (u'GetRestrained', 0, 0),
    246:  (u'GetIsUsedItem', 2, 0),
    247:  (u'GetIsUsedItemType', 2, 0),
    254:  (u'GetIsPlayableRace', 0, 0),
    255:  (u'GetOffersServicesNow', 0, 0),
    258:  (u'GetUsedItemLevel', 0, 0),
    259:  (u'GetUsedItemActivate', 0, 0),
    264:  (u'GetBarterGold', 0, 0),
    265:  (u'IsTimePassing', 0, 0),
    266:  (u'IsPleasant', 0, 0),
    267:  (u'IsCloudy', 0, 0),
    274:  (u'GetArmorRatingUpperBody', 0, 0),
    277:  (u'GetBaseActorValue', 2, 0),
    278:  (u'IsOwner', 2, 0),
    280:  (u'IsCellOwner', 2, 2),
    282:  (u'IsHorseStolen', 0, 0),
    285:  (u'IsLeftUp', 0, 0),
    286:  (u'IsSneaking', 0, 0),
    287:  (u'IsRunning', 0, 0),
    288:  (u'GetFriendHit', 0, 0),
    289:  (u'IsInCombat', 0, 0),
    300:  (u'IsInInterior', 0, 0),
    304:  (u'IsWaterObject', 0, 0),
    306:  (u'IsActorUsingATorch', 0, 0),
    309:  (u'IsXBox', 0, 0),
    310:  (u'GetInWorldspace', 2, 0),
    312:  (u'GetPCMiscStat', 0, 0),
    313:  (u'IsActorEvil', 0, 0),
    314:  (u'IsActorAVictim', 0, 0),
    315:  (u'GetTotalPersuasionNumber', 0, 0),
    318:  (u'GetIdleDoneOnce', 0, 0),
    320:  (u'GetNoRumors', 0, 0),
    323:  (u'WhichServiceMenu', 0, 0),
    327:  (u'IsRidingHorse', 0, 0),
    332:  (u'IsInDangerousWater', 0, 0),
    338:  (u'GetIgnoreFriendlyHits', 0, 0),
    339:  (u'IsPlayersLastRiddenHorse', 0, 0),
    353:  (u'IsActor', 0, 0),
    354:  (u'IsEssential', 0, 0),
    358:  (u'IsPlayerMovingIntoNewSpace', 0, 0),
    361:  (u'GetTimeDead', 0, 0),
    362:  (u'GetPlayerHasLastRiddenHorse', 0, 0),
    365:  (u'IsChild', 0, 0),
    367:  (u'GetLastPlayerAction', 0, 0),
    368:  (u'IsPlayerActionActive', 1, 0),
    370:  (u'IsTalkingActivatorActor', 2, 0),
    372:  (u'IsInList', 2, 0),
    382:  (u'GetHasNote', 2, 0),
    391:  (u'GetHitLocation', 0, 0),
    392:  (u'IsPC1stPerson', 0, 0),
    397:  (u'GetCauseofDeath', 0, 0),
    398:  (u'IsLimbGone', 1, 0),
    399:  (u'IsWeaponInList', 2, 0),
    403:  (u'HasFriendDisposition', 0, 0),
    # We set the second to 'unused' here to receive it as 4 bytes, which we
    # then handle inside MelCtdaFo3.
    408:  (u'GetVATSValue', 1, 0),
    409:  (u'IsKiller', 2, 0),
    410:  (u'IsKillerObject', 2, 0),
    411:  (u'GetFactionCombatReaction', 2, 2),
    415:  (u'Exists', 2, 0),
    416:  (u'GetGroupMemberCount', 0, 0),
    417:  (u'GetGroupTargetCount', 0, 0),
    427:  (u'GetIsVoiceType', 0, 0),
    428:  (u'GetPlantedExplosive', 0, 0),
    430:  (u'IsActorTalkingThroughActivator', 0, 0),
    431:  (u'GetHealthPercentage', 0, 0),
    433:  (u'GetIsObjectType', 2, 0),
    435:  (u'GetDialogueEmotion', 0, 0),
    436:  (u'GetDialogueEmotionValue', 0, 0),
    438:  (u'GetIsCreatureType', 1, 0),
    446:  (u'GetInZone', 2, 0),
    449:  (u'HasPerk', 2, 0),
    450:  (u'GetFactionRelation', 2, 0),
    451:  (u'IsLastIdlePlayed', 2, 0),
    454:  (u'GetPlayerTeammate', 0, 0),
    455:  (u'GetPlayerTeammateCount', 0, 0),
    459:  (u'GetActorCrimePlayerEnemy', 0, 0),
    460:  (u'GetActorFactionPlayerEnemy', 0, 0),
    464:  (u'IsPlayerGrabbedRef', 2, 0),
    471:  (u'GetDestructionStage', 0, 0),
    474:  (u'GetIsAlignment', 1, 0),
    478:  (u'GetThreatRatio', 2, 0),
    480:  (u'GetIsUsedItemEquipType', 1, 0),
    489:  (u'GetConcussed', 0, 0),
    492:  (u'GetMapMarkerVisible', 0, 0),
    495:  (u'GetPermanentActorValue', 2, 0),
    496:  (u'GetKillingBlowLimb', 0, 0),
    500:  (u'GetWeaponHealthPerc', 0, 0),
    503:  (u'GetRadiationLevel', 0, 0),
    510:  (u'GetLastHitCritical', 0, 0),
    515:  (u'IsCombatTarget', 2, 0),
    518:  (u'GetVATSRightAreaFree', 2, 0),
    519:  (u'GetVATSLeftAreaFree', 2, 0),
    520:  (u'GetVATSBackAreaFree', 2, 0),
    521:  (u'GetVATSFrontAreaFree', 2, 0),
    522:  (u'GetIsLockBroken', 0, 0),
    523:  (u'IsPS3', 0, 0),
    524:  (u'IsWin32', 0, 0),
    525:  (u'GetVATSRightTargetVisible', 2, 0),
    526:  (u'GetVATSLeftTargetVisible', 2, 0),
    527:  (u'GetVATSBackTargetVisible', 2, 0),
    528:  (u'GetVATSFrontTargetVisible', 2, 0),
    531:  (u'IsInCriticalStage', 1, 0),
    533:  (u'GetXPForNextLevel', 0, 0),
    546:  (u'GetQuestCompleted', 2, 0),
    550:  (u'IsGoreDisabled', 0, 0),
    555:  (u'GetSpellUsageNum', 2, 0),
    557:  (u'GetActorsInHigh', 0, 0),
    558:  (u'HasLoaded3D', 0, 0),

    # extended by FOSE
    1024: (u'GetFOSEVersion', 0, 0),
    1025: (u'GetFOSERevision', 0, 0),
    1028: (u'GetWeight', 2, 0),
    1082: (u'IsKeyPressed', 1, 0),
    1165: (u'GetWeaponHasScope', 2, 0),
    1166: (u'IsControlPressed', 1, 0),
    1213: (u'GetFOSEBeta', 0, 0),
}
getvatsvalue_index = 408

#------------------------------------------------------------------------------
# Leveled Lists
#------------------------------------------------------------------------------
listTypes = (b'LVLC',b'LVLI',b'LVLN')

#------------------------------------------------------------------------------
# Import Names
#------------------------------------------------------------------------------
namesTypes = {
    b'ACTI', b'ALCH', b'AMMO', b'ARMO', b'AVIF', b'BOOK', b'CLAS', b'COBJ',
    b'CONT', b'CREA', b'DOOR', b'ENCH', b'EYES', b'FACT', b'HAIR', b'INGR',
    b'KEYM', b'LIGH', b'MESG', b'MGEF', b'MISC', b'NOTE', b'NPC_', b'PERK',
    b'RACE', b'SPEL', b'TACT', b'TERM', b'WEAP',
}

#------------------------------------------------------------------------------
# Import Prices
#------------------------------------------------------------------------------
pricesTypes = {b'ALCH', b'AMMO', b'ARMA', b'ARMO', b'BOOK', b'INGR', b'KEYM',
               b'LIGH', b'MISC', b'WEAP'}

#------------------------------------------------------------------------------
# Import Stats
#------------------------------------------------------------------------------
# The contents of these tuples has to stay fixed because of CSV parsers
statsTypes = {
    b'ALCH': ('eid', 'weight', 'value'),
    b'AMMO': ('eid', 'value', 'speed', 'clipRounds'),
    b'ARMA': ('eid', 'weight', 'value', 'health', 'dr'),
    b'ARMO': ('eid', 'weight', 'value', 'health', 'dr'),
    b'BOOK': ('eid', 'weight', 'value'),
    b'INGR': ('eid', 'weight', 'value'),
    b'KEYM': ('eid', 'weight', 'value'),
    b'LIGH': ('eid', 'weight', 'value', 'duration'),
    b'MISC': ('eid', 'weight', 'value'),
    b'WEAP': (
        'eid', 'weight', 'value', 'health', 'damage', 'clipsize',
        'animationMultiplier', 'reach', 'ammoUse', 'minSpread', 'spread',
        'sightFov', 'baseVatsToHitChance', 'projectileCount', 'minRange',
        'maxRange', 'animationAttackMultiplier', 'fireRate',
        'overrideActionPoint', 'rumbleLeftMotorStrength',
        'rumbleRightMotorStrength', 'rumbleDuration',
        'overrideDamageToWeaponMult', 'attackShotsPerSec', 'reloadTime',
        'jamTime', 'aimArc', 'rumbleWavelength', 'limbDmgMult', 'sightUsage',
        'semiAutomaticFireDelayMin', 'semiAutomaticFireDelayMax',
        'criticalDamage', 'criticalMultiplier'),
}

#------------------------------------------------------------------------------
# Import Sounds
#------------------------------------------------------------------------------
soundsTypes = {
    b'ACTI': (u'soundLooping', u'soundActivation'),
    b'ADDN': (u'ambientSound',),
    b'ALCH': (u'dropSound', u'pickupSound', u'soundConsume'),
    b'ARMO': (u'pickupSound', u'dropSound'),
    b'ASPC': (u'soundLooping', u'useSoundFromRegion'),
    b'COBJ': (u'pickupSound', u'dropSound'),
    b'CONT': (u'soundOpen', u'soundClose'),
    b'CREA': (u'footWeight', u'inheritsSoundsFrom', u'sounds'),
    b'DOOR': (u'soundOpen', u'soundClose', u'soundLoop'),
    b'EXPL': (u'soundLevel', u'sound1', u'sound2'),
    b'IPCT': (u'soundLevel', u'sound1', u'sound2'),
    b'LIGH': (u'sound',),
    b'MGEF': (u'castingSound', u'boltSound', u'hitSound', u'areaSound'),
    b'PROJ': (u'sound', u'soundCountDown', u'soundDisable', u'soundLevel'),
#    b'REGN': ('entries.sounds',),
    b'SOUN': (u'soundFile', u'minDist', u'maxDist', u'freqAdj', u'flags',
              u'staticAtten', u'stopTime', u'startTime', u'point0', u'point1',
              u'point2', u'point3', u'point4', u'reverb', u'priority', u'xLoc',
              u'yLoc'),
    b'TACT': (u'sound',),
    b'WATR': (u'sound',),
    b'WEAP': (u'pickupSound', u'dropSound', u'soundGunShot3D',
              u'soundGunShot2D', u'soundGunShot3DLooping',
              u'soundMeleeSwingGunNoAmmo', u'soundBlock', u'idleSound',
              u'equipSound', u'unequipSound', u'soundLevel'),
    b'WTHR': (u'sounds',),
}

#------------------------------------------------------------------------------
# Import Cells
#------------------------------------------------------------------------------
cellRecAttrs = {
    u'C.Acoustic': (u'acousticSpace',),
    u'C.Climate': (u'climate', u'flags.behaveLikeExterior'),
    u'C.Encounter': (u'encounterZone',),
    u'C.ForceHideLand': (u'land_flags',),
    u'C.ImageSpace': (u'imageSpace',),
    ##: Patches unuseds?
    u'C.Light': (u'ambientRed', u'ambientGreen', u'ambientBlue', u'unused1',
                 u'directionalRed', u'directionalGreen', u'directionalBlue',
                 u'unused2', u'fogRed', u'fogGreen', u'fogBlue', u'unused3',
                 u'fogNear', u'fogFar', u'directionalXY', u'directionalZ',
                 u'directionalFade', u'fogClip', u'fogPower',
                 u'lightTemplate', u'lightInheritFlags'),
    u'C.MiscFlags': (u'flags.isInterior', u'flags.invertFastTravel',
                     u'flags.noLODWater', u'flags.handChanged'),
    u'C.Music': (u'music',),
    u'C.Name': (u'full',),
    u'C.Owner': (u'ownership', u'flags.publicPlace'),
    u'C.RecordFlags': (u'flags1',), # Yes seems funky but thats the way it is
    u'C.Regions': (u'regions',),
    u'C.Water': (u'water', u'waterHeight', u'waterNoiseTexture',
                 u'flags.hasWater'),
}

#------------------------------------------------------------------------------
# Import Graphics
#------------------------------------------------------------------------------
graphicsTypes = {
    b'ACTI': (u'model',),
    b'ALCH': (u'iconPath', u'smallIconPath', u'model'),
    b'AMMO': (u'iconPath', u'smallIconPath', u'model'),
    b'ARMA': (u'maleBody', u'maleWorld', u'maleIconPath', u'maleSmallIconPath',
              u'femaleBody', u'femaleWorld', u'femaleIconPath',
              u'femaleSmallIconPath', u'dnamFlags', u'biped_flags'),
    b'ARMO': (u'maleBody', u'maleWorld', u'maleIconPath', u'maleSmallIconPath',
              u'femaleBody', u'femaleWorld', u'femaleIconPath',
              u'femaleSmallIconPath', u'dnamFlags', u'biped_flags'),
    b'AVIF': (u'iconPath', u'smallIconPath'),
    b'BOOK': (u'iconPath', u'smallIconPath', u'model'),
    b'BPTD': (u'model',),
    b'CLAS': (u'iconPath',),
    b'COBJ': (u'iconPath', u'smallIconPath', u'model'),
    b'CONT': (u'model',),
    b'CREA': (u'model', u'bodyParts', u'nift_p'),
    b'DOOR': (u'model',),
    b'EFSH': (u'flags', u'particleTexture', u'fillTexture', u'holesTexture',
              u'unused1', u'memSBlend', u'memBlendOp', u'memZFunc', u'fillRed',
              u'fillGreen', u'fillBlue', u'unused2', u'fillAIn', u'fillAFull',
              u'fillAOut', u'fillAPRatio', u'fillAAmp', u'fillAFreq',
              u'fillAnimSpdU', u'fillAnimSpdV', u'edgeOff', u'edgeRed',
              u'edgeGreen', u'edgeBlue', u'unused3', u'edgeAIn', u'edgeAFull',
              u'edgeAOut', u'edgeAPRatio', u'edgeAAmp', u'edgeAFreq',
              u'fillAFRatio', u'edgeAFRatio', u'memDBlend', u'partSBlend',
              u'partBlendOp', u'partZFunc', u'partDBlend', u'partBUp',
              u'partBFull', u'partBDown', u'partBFRatio', u'partBPRatio',
              u'partLTime', u'partLDelta', u'partNSpd', u'partNAcc',
              u'partVel1', u'partVel2', u'partVel3', u'partAcc1', u'partAcc2',
              u'partAcc3', u'partKey1', u'partKey2', u'partKey1Time',
              u'partKey2Time', u'key1Red', u'key1Green', u'key1Blue',
              u'unused4', u'key2Red', u'key2Green', u'key2Blue', u'unused5',
              u'key3Red', u'key3Green', u'key3Blue', u'unused6', u'key1A',
              u'key2A', u'key3A', u'key1Time', u'key2Time', u'key3Time',
              u'partNSpdDelta', u'partRot', u'partRotDelta', u'partRotSpeed',
              u'partRotSpeedDelta', u'holesStartTime', u'holesEndTime',
              u'holesStartVal', u'holesEndVal', u'edgeWidth',
              u'edge_color_red', u'edge_color_green', u'edge_color_blue',
              u'unused7', u'explosionWindSpeed', u'textureCountU',
              u'textureCountV', u'addonModelsFadeInTime',
              u'addonModelsFadeOutTime', u'addonModelsScaleStart',
              u'addonModelsScaleEnd', u'addonModelsScaleInTime',
              u'addonModelsScaleOutTime'),
    b'EXPL': (u'model',),
    b'EYES': (u'iconPath',),
    b'FURN': (u'model',),
    b'GRAS': (u'model',),
    b'HAIR': (u'iconPath', u'model'),
    b'HDPT': (u'model',),
    b'INGR': (u'iconPath', u'model'),
    b'IPCT': (u'model', u'effectDuration', u'effectOrientation',
              u'angleThreshold', u'placementRadius', u'flags', u'minWidth',
              u'maxWidth', u'minHeight', u'maxHeight', u'depth', u'shininess',
              u'parallaxScale', u'parallaxPasses', u'decalFlags', u'redDecal',
              u'greenDecal', u'blueDecal'),
    b'KEYM': (u'iconPath', u'smallIconPath', u'model'),
    b'LIGH': (u'iconPath', u'model', u'duration', u'radius', u'red', u'green',
              u'blue', u'flags', u'falloff', u'fade'),
    b'LSCR': (u'iconPath',),
    b'MGEF': (u'iconPath', u'model'),
    b'MICN': (u'iconPath', u'smallIconPath'),
    b'MISC': (u'iconPath', u'smallIconPath', u'model'),
    b'MSTT': (u'model',),
    b'NOTE': (u'iconPath', u'smallIconPath', u'model', u'texture'),
    b'PERK': (u'iconPath', u'smallIconPath'),
    b'PROJ': (u'model', u'muzzleFlashDuration', u'fadeDuration',
              u'muzzleFlashPath'),
    b'PWAT': (u'model',),
    b'STAT': (u'model',),
    b'TACT': (u'model',),
    b'TERM': (u'model',),
    b'TREE': (u'iconPath', u'model'),
    b'TXST': (u'baseImage', u'normalMap', u'environmentMapMask', u'growMap',
              u'parallaxMap', u'environmentMap', u'minWidth', u'maxWidth',
              u'minHeight', u'maxHeight', u'depth', u'shininess',
              u'parallaxScale', u'parallaxPasses', u'decalFlags', u'redDecal',
              u'greenDecal', u'blueDecal', u'flags'),
    b'WEAP': (u'iconPath', u'smallIconPath', u'model', u'shellCasingModel',
              u'scopeModel', u'worldModel', u'animationType', u'gripAnimation',
              u'reloadAnimation'),
}
graphicsFidTypes = {
    b'CREA': ('bodyPartData',),
    b'EFSH': (u'addonModels',),
    b'EXPL': ('imageSpaceModifier', 'light', 'impactDataset',
              'placedImpactObject'),
    b'IPCT': (u'textureSet',),
    b'IPDS': (u'stone', u'dirt', u'grass', u'metal', u'wood', u'organic',
              u'cloth', u'water', u'hollowMetal', u'organicBug',
              u'organicGlow'),
    b'MGEF': (u'light', u'effectShader', u'enchantEffect'),
    b'PROJ': (u'light', u'muzzleFlash', u'explosion'),
    b'WEAP': ('scopeEffect', 'impactDataset', 'firstPersonModel'),
}
graphicsModelAttrs = (u'model', u'shellCasingModel', u'scopeModel',
                      u'worldModel', u'maleBody', u'maleWorld', u'femaleBody',
                      u'femaleWorld')

#------------------------------------------------------------------------------
# Import Inventory
#------------------------------------------------------------------------------
inventoryTypes = (b'CREA',b'NPC_',b'CONT',)

#------------------------------------------------------------------------------
# Import Text
#------------------------------------------------------------------------------
text_types = {
    b'AMMO': ('short_name',),
    b'AVIF': ('description', 'short_name'),
    b'BOOK': ('book_text',),
    b'CLAS': ('description',),
    b'LSCR': ('description',),
    b'MESG': ('description',),
    b'MGEF': ('description',),
    b'NOTE': ('textTopic',),
    b'PERK': ('description',),
    # omit RACE - covered by R.Description
    b'TERM': ('description',),
}

#------------------------------------------------------------------------------
# Import Object Bounds
#------------------------------------------------------------------------------
object_bounds_types = {b'ACTI', b'ADDN', b'ALCH', b'AMMO', b'ARMA', b'ARMO',
                       b'ASPC', b'BOOK', b'COBJ', b'CONT', b'CREA', b'DOOR',
                       b'EXPL', b'FURN', b'GRAS', b'IDLM', b'INGR', b'KEYM',
                       b'LIGH', b'LVLC', b'LVLI', b'LVLN', b'MISC', b'MSTT',
                       b'NOTE', b'NPC_', b'PROJ', b'PWAT', b'SCOL', b'SOUN',
                       b'STAT', b'TACT', b'TERM', b'TREE', b'TXST', b'WEAP'}

#------------------------------------------------------------------------------
# Contents Checker
#------------------------------------------------------------------------------
# Entry types used for CONT, CREA, LVLI and NPC_
_common_entry_types = {b'ALCH', b'AMMO', b'ARMO', b'BOOK', b'KEYM', b'LVLI',
                       b'MISC', b'NOTE', b'WEAP'}
# These are marked as {?} in xEdit for FO3, absent for FO3's LVLI, and
# completely commented out in xEdit for FNV. Included for now just to be safe.
_common_entry_types |= {b'MSTT', b'STAT'}
cc_valid_types = {
    b'CONT': _common_entry_types,
    b'CREA': _common_entry_types,
    b'LVLC': {b'CREA', b'LVLC'},
    b'LVLN': {b'LVLN', b'NPC_'},
    b'LVLI': _common_entry_types - {b'MSTT', b'STAT'},
    b'NPC_': _common_entry_types,
}
cc_passes = (
    ((b'LVLC', b'LVLN', b'LVLI'), 'entries', 'listId'),
    ((b'CONT', b'CREA', b'NPC_'), 'items', 'item'),
)

#------------------------------------------------------------------------------
# Import Scripts
#------------------------------------------------------------------------------
# In valda's version: 'WEAP', 'ACTI', 'ALCH', 'ARMO', 'BOOK', 'CONT', 'CREA',
#                     'DOOR', 'FURN', 'INGR', 'KEYM', 'LIGH', 'MISC', 'NPC_',
#                     'QUST', 'TERM', 'TACT'
# In valda's FNV version, only 'CCRD' got added
# INGR and COBJ are unused - still including them, see e.g. APPA in Skyrim
scripts_types = {b'ACTI', b'ALCH', b'ARMO', b'BOOK', b'COBJ', b'CONT', b'CREA',
                 b'DOOR', b'FURN', b'INGR', b'KEYM', b'LIGH', b'MISC', b'NPC_',
                 b'QUST', b'TACT', b'TERM', b'WEAP'}

#------------------------------------------------------------------------------
# Import Destructible
#------------------------------------------------------------------------------
destructible_types = {b'ACTI', b'ALCH', b'AMMO', b'ARMO', b'BOOK', b'CONT',
                      b'CREA', b'DOOR', b'FURN', b'KEYM', b'LIGH', b'MISC',
                      b'MSTT', b'NPC_', b'PROJ', b'TACT', b'TERM', b'WEAP'}

#------------------------------------------------------------------------------
# Import Actors
#------------------------------------------------------------------------------
actor_importer_attrs = {
    b'CREA': {
        u'Actors.ACBS': (u'barterGold', u'calcMax', u'calcMin',
                         u'dispositionBase', u'fatigue',
                         u'flags.allowPCDialogue', u'flags.allowPickpocket',
                         u'flags.biped', u'flags.cantOpenDoors',
                         u'flags.essential', u'flags.flies', u'flags.immobile',
                         u'flags.invulnerable', u'flags.isGhost',
                         u'flags.noBloodDecal', u'flags.noBloodSpray',
                         u'flags.noCombatInWater', u'flags.noHead',
                         u'flags.noKnockDown', u'flags.noLeftArm',
                         u'flags.noLowLevel', u'flags.noRightArm',
                         u'flags.noRotatingHeadTrack', u'flags.noShadow',
                         u'flags.notPushable', u'flags.noVATSMelee',
                         u'flags.pcLevelOffset', u'flags.respawn',
                         u'flags.swims', u'flags.tiltFrontBack',
                         u'flags.tiltLeftRight', u'flags.walks',
                         u'flags.weaponAndShield', u'karma', u'level_offset',
                         u'speedMultiplier'),
        u'Actors.AIData': (u'aggression', u'aggroRadius',
                           u'aggroRadiusBehavior', u'assistance',
                           u'confidence', u'energyLevel', u'mood',
                           u'responsibility', u'services', u'trainLevel',
                           u'trainSkill'),
        u'Actors.CombatStyle': (u'combatStyle',),
        u'Actors.RecordFlags': (u'flags1',),
        u'Actors.Skeleton': (u'model',),
        u'Actors.Stats': (u'agility', u'charisma', u'combatSkill', u'damage',
                          u'endurance', u'health', u'intelligence', u'luck',
                          u'magicSkill', u'perception', u'stealthSkill',
                          u'strength'),
        u'Actors.Voice': (u'voice',),
        u'Creatures.Blood': (u'impactDataset',),
        u'Creatures.Type': (u'creatureType',),
        u'NPC.Class': (),
        u'NPC.Race': (),
    },
    b'NPC_': {
        u'Actors.ACBS': (u'barterGold', u'calcMax', u'calcMin',
                         u'dispositionBase', u'fatigue', u'flags.autoCalc',
                         u'flags.canBeAllRaces', u'flags.essential',
                         u'flags.female', u'flags.isChargenFacePreset',
                         u'flags.noBloodDecal', u'flags.noBloodSpray',
                         u'flags.noKnockDown', u'flags.noLowLevel',
                         u'flags.noRotatingHeadTrack', u'flags.notPushable',
                         u'flags.noVATSMelee', u'flags.pcLevelOffset',
                         u'flags.respawn', u'karma', u'level_offset',
                         u'speedMultiplier'),
        u'Actors.AIData': (u'aggression', u'aggroRadius',
                           u'aggroRadiusBehavior', u'assistance',
                           u'confidence', u'energyLevel', u'mood',
                           u'responsibility', u'services', u'trainLevel',
                           u'trainSkill'),
        u'Actors.CombatStyle': (u'combatStyle',),
        u'Actors.RecordFlags': (u'flags1',),
        u'Actors.Skeleton': (u'model',),
        u'Actors.Stats': (u'attributes', u'health', u'skillOffsets',
                          u'skillValues'),
        u'Actors.Voice': (u'voice',),
        u'Creatures.Blood': (),
        u'Creatures.Type': (),
        u'NPC.Class': (u'iclass',),
        u'NPC.Race': (u'race',),
    },
}
actor_types = (b'CREA', b'NPC_')

#------------------------------------------------------------------------------
# Import Spell Stats
#------------------------------------------------------------------------------
spell_stats_attrs = (u'eid', u'cost', u'level', u'spellType', u'flags')

#------------------------------------------------------------------------------
# Tweak Actors
#------------------------------------------------------------------------------
actor_tweaks = {
    u'QuietFeetPatcher',
    u'IrresponsibleCreaturesPatcher',
}

#------------------------------------------------------------------------------
# Tweak Names
#------------------------------------------------------------------------------
names_tweaks = {
    'NamesTweak_BodyPartCodes',
    'NamesTweak_Body_Armor_Fo3',
    'NamesTweak_Ingestibles_Fo3',
    'NamesTweak_Weapons_Fo3',
    'NamesTweak_AmmoWeight_Fo3',
    'NamesTweak_RenameCaps',
}
body_part_codes = (u'HAGPBFE', u'HBGPEFE')
gold_attrs = lambda _self_ignore, gm_master: {
    'eid': 'Caps001',
    'bounds.boundX1': -2,
    'bounds.boundY1': -2,
    'bounds.boundZ1': -1,
    'bounds.boundX2': 2,
    'bounds.boundY2': 2,
    'bounds.boundZ2': 0,
    'model.modPath': r'Clutter\Junk\NukaColaCap.NIF',
    'model.modb_p': None,
    'model.modt_p': None,
    'model.alternateTextures': None,
    'model.facegen_model_flags': None,
    'iconPath': r'Interface\Icons\PipboyImages\Items\items_nuka_cola_cap.dds',
    'pickupSound': (gm_master, 0x0864D8), # ITMBottlecapsUp
    'dropSound': (gm_master, 0x0864D7), # ITMBottlecapsDown
    'value': 1,
    'weight': 0.0,
}

#------------------------------------------------------------------------------
# Tweak Settings
#------------------------------------------------------------------------------
settings_tweaks = {
    u'GlobalsTweak_Timescale',
    u'GmstTweak_Camera_ChaseDistance_Fo3',
    u'GmstTweak_Compass_RecognitionDistance',
    u'GmstTweak_Actor_UnconsciousnessDuration',
    u'GmstTweak_Actor_MaxJumpHeight',
    u'GmstTweak_Camera_PCDeathTime',
    u'GmstTweak_World_CellRespawnTime',
    u'GmstTweak_CostMultiplier_Repair_Fo3',
    u'GmstTweak_Combat_MaxActors',
    u'GmstTweak_AI_MaxActiveActors',
    u'GmstTweak_Actor_MaxCompanions',
    u'GmstTweak_AI_MaxDeadActors',
    u'GmstTweak_Player_InventoryQuantityPrompt',
    u'GmstTweak_Gore_CombatDismemberPartChance',
    u'GmstTweak_Gore_CombatExplodePartChance',
    u'GmstTweak_LevelDifference_ItemMax',
    u'GmstTweak_Movement_BaseSpeed',
    u'GmstTweak_Movement_SneakMultiplier',
    u'GmstTweak_Combat_VATSPlayerDamageMultiplier',
    u'GmstTweak_Combat_AutoAimFix',
    u'GmstTweak_Player_PipBoyLightKeypressDelay',
    u'GmstTweak_Combat_VATSPlaybackDelay',
    u'GmstTweak_Combat_NPCDeathXPThreshold',
    u'GmstTweak_Hacking_MaximumNumberOfWords',
    u'GmstTweak_Visuals_ShellCameraDistance',
    u'GmstTweak_Visuals_ShellLitterTime',
    u'GmstTweak_Visuals_ShellLitterCount',
    u'GmstTweak_Hacking_TerminalSpeedAdjustment',
    u'GmstTweak_Player_MaxDraggableWeight',
    u'GmstTweak_Prompt_Activate_Tes4',
    u'GmstTweak_Prompt_Open_Tes4',
    u'GmstTweak_Prompt_Read_Tes4',
    u'GmstTweak_Prompt_Sit_Tes4',
    u'GmstTweak_Prompt_Take_Tes4',
    u'GmstTweak_Prompt_Talk_Tes4',
    u'GmstTweak_Combat_SpeakOnHitChance',
    u'GmstTweak_Combat_SpeakOnHitThreshold',
    u'GmstTweak_Combat_SpeakOnPowerAttackChance',
    u'GmstTweak_Combat_MaxAllyHitsInCombat',
    u'GmstTweak_Combat_MaxAllyHitsOutOfCombat',
    u'GmstTweak_Combat_MaxFriendHitsInCombat',
    u'GmstTweak_Combat_MaxFriendHitsOutOfCombat',
}

#------------------------------------------------------------------------------
# Tweak Assorted
#------------------------------------------------------------------------------
##: Mostly mirrored from valda's version - some of these seem to make no sense
# (e.g. I can't find anything regarding FO3/FNV suffering from the fog bug).
assorted_tweaks = {
    u'AssortedTweak_ArmorPlayable',
    u'AssortedTweak_FogFix',
    u'AssortedTweak_NoLightFlicker',
    u'AssortedTweak_WindSpeed',
    u'AssortedTweak_SetSoundAttenuationLevels',
    u'AssortedTweak_LightFadeValueFix',
    u'AssortedTweak_TextlessLSCRs',
    u'AssortedTweak_PotionWeightMinimum',
    u'AssortedTweak_UniformGroundcover',
    u'AssortedTweak_GunsUseISAnimation',
    u'AssortedTweak_BookWeight',
}
##: Taken from valda's version, investigate
nonplayable_biped_flags = {u'pipboy'}
not_playable_flag = (u'generalFlags', u'notPlayable')
static_attenuation_rec_type = b'SOUN'

#------------------------------------------------------------------------------
# Import Relations
#------------------------------------------------------------------------------
relations_attrs = (u'faction', u'mod', u'group_combat_reaction')

#------------------------------------------------------------------------------
# Import Enchantment Stats
#------------------------------------------------------------------------------
ench_stats_attrs = (u'itemType', u'chargeAmount', u'enchantCost', u'flags')

#------------------------------------------------------------------------------
# Import Effect Stats
#------------------------------------------------------------------------------
mgef_stats_attrs = (u'flags', u'base_cost', u'associated_item', u'school',
                    u'resist_value', u'projectileSpeed', u'cef_enchantment',
                    u'cef_barter', u'effect_archetype', u'actorValue')

#------------------------------------------------------------------------------
# Import Races
#------------------------------------------------------------------------------
import_races_attrs = {
    b'RACE': {
        u'R.Body-F': (u'femaleUpperBody', u'femaleLeftHand',
                      u'femaleRightHand', u'femaleUpperBodyTexture'),
        u'R.Body-M': (u'maleUpperBody', u'maleLeftHand', u'maleRightHand',
                      u'maleUpperBodyTexture'),
        u'R.Body-Size-F': (u'femaleHeight', u'femaleWeight'),
        u'R.Body-Size-M': (u'maleHeight', u'maleWeight'),
        u'R.Description': (u'description',),
        u'R.Ears': (u'maleEars', u'femaleEars'),
        u'R.Eyes': (u'eyes', u'femaleLeftEye', u'femaleRightEye',
                    u'maleLeftEye', u'maleRightEye'),
        u'R.Hair': (u'hairs',),
        u'R.Head': (u'femaleHead', u'maleHead',),
        u'R.Mouth': (u'maleMouth', u'femaleMouth', u'maleTongue',
                     u'femaleTongue'),
        u'R.Skills': (u'skills',),
        u'R.Teeth': (u'femaleTeethLower', u'femaleTeethUpper',
                     u'maleTeethLower', u'maleTeethUpper'),
        u'R.Voice-F': (u'femaleVoice',),
        u'R.Voice-M': (u'maleVoice',),
    },
}

#------------------------------------------------------------------------------
# Import Enchantments
#------------------------------------------------------------------------------
enchantment_types = {b'ARMO', b'CREA', b'EXPL', b'NPC_', b'WEAP'}

#------------------------------------------------------------------------------
# Tweak Races
#------------------------------------------------------------------------------
race_tweaks = {
    u'RaceTweak_PlayableHeadParts',
    u'RaceTweak_MergeSimilarRaceHairs',
    u'RaceTweak_MergeSimilarRaceEyes',
    u'RaceTweak_PlayableEyes',
    u'RaceTweak_PlayableHairs',
    u'RaceTweak_GenderlessHairs',
    u'RaceTweak_AllEyes',
    u'RaceTweak_AllHairs',
}
race_tweaks_need_collection = True

#------------------------------------------------------------------------------
# NPC Checker
#------------------------------------------------------------------------------
# Note that we use _x to avoid exposing these to the dynamic importer
def _fid(_x): return None, _x # None <=> game master
_standard_eyes = [_fid(_x) for _x in (0x4252, 0x4253, 0x4254, 0x4255, 0x4256)]
default_eyes = {
    #--FalloutNV.esm
    # Caucasian
    _fid(0x000019): _standard_eyes,
    # Hispanic
    _fid(0x0038e5): _standard_eyes,
    # Asian
    _fid(0x0038e6): _standard_eyes,
    # Ghoul
    _fid(0x003b3e): [_fid(0x35e4f)],
    # AfricanAmerican
    _fid(0x00424a): _standard_eyes,
    # AfricanAmerican Child
    _fid(0x0042be): _standard_eyes,
    # AfricanAmerican Old
    _fid(0x0042bf): _standard_eyes,
    # Asian Child
    _fid(0x0042c0): _standard_eyes,
    # Asian Old
    _fid(0x0042c1): _standard_eyes,
    # Caucasian Child
    _fid(0x0042c2): _standard_eyes,
    # Caucasian Old
    _fid(0x0042c3): _standard_eyes,
    # Hispanic Child
    _fid(0x0042c4): _standard_eyes,
    # Hispanic Old
    _fid(0x0042c5): _standard_eyes,
    # Caucasian Raider
    _fid(0x04bb8d): [_fid(0x4cb10)],
    # Hispanic Raider
    _fid(0x04bf70): [_fid(0x4cb10)],
    # Asian Raider
    _fid(0x04bf71): [_fid(0x4cb10)],
    # AfricanAmerican Raider
    _fid(0x04bf72): [_fid(0x4cb10)],
    # Hispanic Old Aged
    _fid(0x0987dc): _standard_eyes,
    # Asian Old Aged
    _fid(0x0987dd): _standard_eyes,
    # AfricanAmerican Old Aged
    _fid(0x0987de): _standard_eyes,
    # Caucasian Old Aged
    _fid(0x0987df): _standard_eyes,
}
# Clean this up, no need to keep it around now
del _fid

#------------------------------------------------------------------------------
# Timescale Checker
#------------------------------------------------------------------------------
default_wp_timescale = 30
