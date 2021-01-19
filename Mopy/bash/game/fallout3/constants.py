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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

#--Game ESM/ESP/BSA files
#  These filenames need to be in lowercase,
bethDataFiles = {
    #--Vanilla
    u'fallout3.esm',
    u'fallout - menuvoices.bsa',
    u'fallout - meshes.bsa',
    u'fallout - misc.bsa',
    u'fallout - sound.bsa',
    u'fallout - textures.bsa',
    u'fallout - voices.bsa',
    #-- DLC
    u'anchorage.esm',
    u'anchorage - main.bsa',
    u'anchorage - sounds.bsa',
    u'thepitt.esm',
    u'thepitt - main.bsa',
    u'thepitt - sounds.bsa',
    u'brokensteel.esm',
    u'brokensteel - main.bsa',
    u'brokensteel - sounds.bsa',
    u'pointlookout.esm',
    u'pointlookout - main.bsa',
    u'pointlookout - sounds.bsa',
    u'zeta.esm',
    u'zeta - main.bsa',
    u'zeta - sounds.bsa',
}

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
listTypes = ('LVLC','LVLI','LVLN')

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
pricesTypes = {'ALCH': {}, 'AMMO': {}, 'ARMO': {}, 'ARMA': {}, 'BOOK': {},
               'INGR': {}, 'KEYM': {}, 'LIGH': {}, 'MISC': {}, 'WEAP': {}}

#------------------------------------------------------------------------------
# Import Stats
#------------------------------------------------------------------------------
statsTypes = {
    'ALCH': ('eid', 'weight', 'value'),
    'AMMO': ('eid', 'value', 'speed', 'clipRounds'),
    'ARMA': ('eid', 'weight', 'value', 'health', 'ar'),
    'ARMO': ('eid', 'weight', 'value', 'health', 'ar'),
    'BOOK': ('eid', 'weight', 'value'),
    'INGR': ('eid', 'weight', 'value'),
    'KEYM': ('eid', 'weight', 'value'),
    'LIGH': ('eid', 'weight', 'value', 'duration'),
    'MISC': ('eid', 'weight', 'value'),
    'WEAP': ('eid', 'weight', 'value', 'health', 'damage','clipsize',
             'animationMultiplier','reach','ammoUse','minSpread','spread',
             'sightFov','baseVatsToHitChance','projectileCount','minRange',
             'maxRange','animationAttackMultiplier','fireRate',
             'overrideActionPoint','rumbleLeftMotorStrength',
             'rumbleRightMotorStrength','rumbleDuration',
             'overrideDamageToWeaponMult','attackShotsPerSec','reloadTime',
             'jamTime','aimArc','rambleWavelangth','limbDmgMult',
             'sightUsage','semiAutomaticFireDelayMin',
             'semiAutomaticFireDelayMax','criticalDamage',
             'criticalMultiplier'),
}

statsHeaders = (
    #--Alch
    (u'ALCH',
        (u'"' + u'","'.join((_(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
        _(u'Editor Id'),_(u'Weight'),_(u'Value'))) + u'"\n')),
    #Ammo
    (u'AMMO',
        (u'"' + u'","'.join((_(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
        _(u'Editor Id'),_(u'Weight'),_(u'Value'),_(u'Speed'),_(u'Clip Rounds'),_(u'Proj/Shot'))) + u'"\n')),
    #--Armor
    (u'ARMO',
        (u'"' + u'","'.join((_(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
        _(u'Editor Id'),_(u'Weight'),_(u'Value'),_(u'Health'),_(u'AR'),_(u'DT'))) + u'"\n')),
    #--Armor Addon
    (u'ARMA',
        (u'"' + u'","'.join((_(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
        _(u'Editor Id'),_(u'Weight'),_(u'Value'),_(u'Health'),_(u'AR'))) + u'"\n')),
    #Books
    (u'BOOK',
        (u'"' + u'","'.join((_(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
        _(u'Editor Id'),_(u'Weight'),_(u'Value'))) + u'"\n')),
    #Ingredients
    (u'INGR',
        (u'"' + u'","'.join((_(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
       _(u'Editor Id'),_(u'Weight'),_(u'Value'))) + u'"\n')),
    #--Keys
    (u'KEYM',
        (u'"' + u'","'.join((_(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
        _(u'Editor Id'),_(u'Weight'),_(u'Value'))) + u'"\n')),
    #Lights
    (u'LIGH',
        (u'"' + u'","'.join((_(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
        _(u'Editor Id'),_(u'Weight'),_(u'Value'),_(u'Duration'))) + u'"\n')),
    #--Misc
    (u'MISC',
        (u'"' + u'","'.join((_(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
        _(u'Editor Id'),_(u'Weight'),_(u'Value'))) + u'"\n')),
    #--Weapons
    (u'WEAP',
        (u'"' + u'","'.join((_(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
        _(u'Editor Id'),_(u'Weight'),_(u'Value'),_(u'Health'),_(u'Damage'),
        _(u'Clip Size'),_(u'Animation Multiplier'),_(u'Reach'),_(u'Ammo Use'),
        _(u'Min Spread'),_(u'Spread'),_(u'Sight Fov'),
        _(u'Base VATS To-Hit Chance'), _(u'Projectile Count'),_(u'Min Range'),
        _(u'Max Range'), _(u'Animation Attack Multiplier'), _(u'Fire Rate'),
        _(u'Override - Action Point'), _(u'Rumble - Left Motor Strength'),
        _(u'rRmble - Right Motor Strength'), _(u'Rumble - Duration'),
        _(u'Override - Damage To Weapon Mult'), _(u'Attack Shots/Sec'),
        _(u'Reload Time'), _(u'Jam Time'), _(u'Aim Arc'), _(u'Ramble - Wavelangth'),
        _(u'Limb Dmg Mult'), _(u'Sight Usage'),_(u'Semi-Automatic Fire Delay Min'),
        _(u'Semi-Automatic Fire Delay Max'),_(u'Critical Damage'),
        _(u'Crit % Mult'))) + u'"\n')),
)

#------------------------------------------------------------------------------
# Import Sounds
#------------------------------------------------------------------------------
soundsTypes = {
    "ACTI": ('soundLooping','soundActivation',),
    "ADDN": ('ambientSound',),
    "ALCH": ('dropSound','pickupSound','soundConsume',),
    "ASPC": ('soundLooping','useSoundFromRegion',),
    "COBJ": ('pickupSound','dropSound',),
    "CONT": ('soundOpen','soundClose',),
    "CREA": ('footWeight','inheritsSoundsFrom','sounds'),
    "DOOR": ('soundOpen','soundClose','soundLoop',),
    "EXPL": ('soundLevel','sound1','sound2',),
    "IPCT": ('soundLevel','sound1','sound2',),
    "LIGH": ('sound',),
    "MGEF": ('castingSound','boltSound','hitSound','areaSound',),
    "PROJ": ('sound','soundCountDown','soundDisable','soundLevel',),
#    "REGN": ('entries.sounds',),
    "SOUN": ('soundFile','minDist','maxDist','freqAdj','flags','staticAtten',
             'stopTime','startTime','point0','point1','point2','point3',
             'point4','reverb','priority','xLoc','yLoc',),
    "TACT": ('sound',),
    "WATR": ('sound',),
    "WEAP": ('pickupSound','dropSound','soundGunShot3D','soundGunShot2D',
             'soundGunShot3DLooping','soundMeleeSwingGunNoAmmo','soundBlock','idleSound',
             'equipSound','unequipSound','soundLevel',),
    "WTHR": ('sounds',),
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
cell_float_attrs = {u'fogNear', u'fogFar', u'directionalFade', u'fogClip',
                    u'fogPower', u'waterHeight'}

#------------------------------------------------------------------------------
# Import Graphics
#------------------------------------------------------------------------------
graphicsTypes = {
    b'ACTI': (u'model',),
    b'ALCH': (u'iconPath', u'smallIconPath', u'model'),
    b'AMMO': (u'iconPath', u'smallIconPath', u'model'),
    b'ARMA': (u'maleBody', u'maleWorld', u'maleIconPath', u'maleSmallIconPath',
              u'femaleBody', u'femaleWorld', u'femaleIconPath',
              u'femaleSmallIconPath', u'dnamFlags'),
    b'ARMO': (u'maleBody', u'maleWorld', u'maleIconPath', u'maleSmallIconPath',
              u'femaleBody', u'femaleWorld', u'femaleIconPath',
              u'femaleSmallIconPath', u'dnamFlags'),
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
    b'FURN': (u'model',),
    b'GRAS': (u'model',),
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
    b'ARMO': (u'enchantment',),
    b'CREA': (u'enchantment', u'bodyPartData'),
    b'EFSH': (u'addonModels',),
    b'EXPL': (u'enchantment', u'imageSpaceModifier', u'light',
              u'impactDataset', u'placedImpactObject'),
    b'IPCT': (u'textureSet',),
    b'IPDS': (u'stone', u'dirt', u'grass', u'metal', u'wood', u'organic',
              u'cloth', u'water', u'hollowMetal', u'organicBug',
              u'organicGlow'),
    b'MGEF': (u'light', u'effectShader', u'enchantEffect'),
    b'NPC_': (u'enchantment',),
    b'PROJ': (u'light', u'muzzleFlash', u'explosion'),
    b'WEAP': (u'enchantment', u'scopeEffect', u'impactDataset',
              u'firstPersonModel'),
}
graphicsModelAttrs = (u'model', u'shellCasingModel', u'scopeModel',
                      u'worldModel', u'maleBody', u'maleWorld', u'femaleBody',
                      u'femaleWorld')

#------------------------------------------------------------------------------
# Import Inventory
#------------------------------------------------------------------------------
inventoryTypes = ('CREA','NPC_','CONT',)

#------------------------------------------------------------------------------
# Import Text
#------------------------------------------------------------------------------
text_types = {
    b'AVIF': (u'description',),
    b'BOOK': (u'book_text',),
    b'CLAS': (u'description',),
    b'LSCR': (u'description',),
    b'MESG': (u'description',),
    b'MGEF': (u'text',),
    b'NOTE': (u'textTopic',),
    b'PERK': (u'description',),
    # omit RACE - covered by R.Description
    b'TERM': (u'description',),
}

#------------------------------------------------------------------------------
# Import Object Bounds
#------------------------------------------------------------------------------
object_bounds_types = {'ACTI', 'ADDN', 'ALCH', 'AMMO', 'ARMA', 'ARMO', 'ASPC',
                       'BOOK', 'COBJ', 'CONT', 'CREA', 'DOOR', 'EXPL', 'FURN',
                       'GRAS', 'IDLM', 'INGR', 'KEYM', 'LIGH', 'LVLC', 'LVLI',
                       'LVLN', 'MISC', 'MSTT', 'NOTE', 'NPC_', 'PROJ', 'PWAT',
                       'SCOL', 'SOUN', 'STAT', 'TACT', 'TERM', 'TREE', 'TXST',
                       'WEAP'}

#------------------------------------------------------------------------------
# Contents Checker
#------------------------------------------------------------------------------
# Entry types used for CONT, CREA, LVLI and NPC_
_common_entry_types = {'ALCH', 'AMMO', 'ARMO', 'BOOK', 'KEYM', 'LVLI', 'MISC',
                       'NOTE', 'WEAP'}
# These are marked as {?} in xEdit for FO3, absent for FO3's LVLI, and
# completely commented out in xEdit for FNV. Included for now just to be safe.
_common_entry_types |= {'MSTT', 'STAT'}
cc_valid_types = {
    'CONT': _common_entry_types,
    'CREA': _common_entry_types,
    'LVLC': {'CREA', 'LVLC'},
    'LVLN': {'LVLN', 'NPC_'},
    'LVLI': _common_entry_types - {'MSTT', 'STAT'},
    'NPC_': _common_entry_types,
}
cc_passes = (
    (('LVLC', 'LVLN', 'LVLI'), 'entries', 'listId'),
    (('CONT', 'CREA', 'NPC_'), 'items', 'item'),
)

#------------------------------------------------------------------------------
# Import Scripts
#------------------------------------------------------------------------------
# In valda's version: 'WEAP', 'ACTI', 'ALCH', 'ARMO', 'BOOK', 'CONT', 'CREA',
#                     'DOOR', 'FURN', 'INGR', 'KEYM', 'LIGH', 'MISC', 'NPC_',
#                     'QUST', 'TERM', 'TACT'
# In valda's FNV version, only 'CCRD' got added
# INGR and COBJ are unused - still including them, see e.g. APPA in Skyrim
scripts_types = {'ACTI', 'ALCH', 'ARMO', 'BOOK', 'COBJ', 'CONT', 'CREA',
                 'DOOR', 'FURN', 'INGR', 'KEYM', 'LIGH', 'MISC', 'NPC_',
                 'QUST', 'TACT', 'TERM', 'WEAP'}

#------------------------------------------------------------------------------
# Import Destructible
#------------------------------------------------------------------------------
destructible_types = {'ACTI', 'ALCH', 'AMMO', 'ARMO', 'BOOK', 'CONT', 'CREA',
                      'DOOR', 'FURN', 'KEYM', 'LIGH', 'MISC', 'MSTT', 'NPC_',
                      'PROJ', 'TACT', 'TERM', 'WEAP'}

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
                         u'flags.weaponAndShield', u'karma', u'level',
                         u'speedMultiplier', u'templateFlags'),
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
                         u'flags.respawn', u'flags.useTemplate', u'karma',
                         u'level', u'speedMultiplier', u'templateFlags'),
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
        u'Creatures.Blood': (),
        u'Creatures.Type': (),
        u'NPC.Class': (u'iclass',),
        u'NPC.Race': (u'race',),
    },
}
actor_types = ('CREA', 'NPC_')

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
body_tags = u'HAGPBFE'

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
}
##: Taken from valda's version, investigate
nonplayable_biped_flags = {u'pipboy'}
not_playable_flag = (u'generalFlags', u'notPlayable')
static_attenuation_rec_type = b'SOUN'

#------------------------------------------------------------------------------
# Import Relations
#------------------------------------------------------------------------------
relations_attrs = (u'faction', u'mod', u'group_combat_reaction')
relations_csv_header = u'"%s","%s","%s","%s","%s","%s","%s","%s"\n' % (
    _(u'Main Eid'), _(u'Main Mod'), _(u'Main Object'), _(u'Other Eid'),
    _(u'Other Mod'), _(u'Other Object'), _(u'Modifier'),
    _(u'Group Combat Reaction'))
relations_csv_row_format = u'"%s","%s","0x%06X","%s","%s","0x%06X","%s","%s"\n'

#------------------------------------------------------------------------------
# Import Enchantment Stats
#------------------------------------------------------------------------------
ench_stats_attrs = (u'itemType', u'chargeAmount', u'enchantCost', u'flags')

#--------------------------------------------------------------------------
# Import Effect Stats
#--------------------------------------------------------------------------
mgef_stats_attrs = (u'flags', u'base_cost', u'associated_item', u'school',
                    u'resist_value', u'projectileSpeed', u'cef_enchantment',
                    u'cef_barter', u'effect_archetype', u'actorValue')

# Record type to name dictionary
record_type_name = {
    b'ALCH': _(u'Ingestibles'),
    b'AMMO': _(u'Ammo'),
    b'ARMA': _(u'Armature'),
    b'ARMO': _(u'Armors'),
    b'BOOK': _(u'Books'),
    b'INGR': _(u'Ingredients'),
    b'KEYM': _(u'Keys'),
    b'LIGH': _(u'Lights'),
    b'MISC': _(u'Misc'),
    b'WEAP': _(u'Weapons'),
}
