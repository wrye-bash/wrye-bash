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

"""This package contains the Fallout New Vegas specific patchers. This module
contains the data structures that are dynamically set on a per game basis in
bush."""
from ...fallout3.patcher import *

# Function Info ---------------------------------------------------------------
# 0: no param; 1: int param; 2: formid param; 3: float param
condition_function_data.update({ # new & changed functions in FNV
    398:  (u'IsLimbGone', 1, 1),
    420:  (u'GetObjectiveCompleted', 2, 1),
    421:  (u'GetObjectiveDisplayed', 2, 1),
    449:  (u'HasPerk', 2, 1),
    451:  (u'IsLastIdlePlayed', 0, 0),
    462:  (u'IsPlayerTagSkill', 2, 0),
    474:  (u'GetIsAlignment', 2, 0),
    480:  (u'GetIsUsedItemEquipType', 2, 0),
    531:  (u'IsInCriticalStage', 2, 0),
    573:  (u'GetReputation', 1, 1),
    574:  (u'GetReputationPct', 1, 1),
    575:  (u'GetReputationThreshold', 1, 1),
    586:  (u'IsHardcore', 0, 0),
    601:  (u'GetForceHitReaction', 0, 0),
    607:  (u'ChallengeLocked', 2, 0),
    610:  (u'GetCasinoWinningStage', 1, 0),
    612:  (u'PlayerInRegion', 2, 0),
    614:  (u'GetChallengeCompleted', 2, 0),
    619:  (u'IsAlwaysHardcore', 0, 0),

    # Added by NVSE - up to date with xNVSE v6.2.0
    1024: (u'GetNVSEVersion', 0, 0),
    1025: (u'GetNVSERevision', 0, 0),
    1026: (u'GetNVSEBeta', 0, 0),
    1028: (u'GetWeight', 2, 0),
    1029: (u'GetHealth', 2, 0),
    1030: (u'GetValue', 2, 0),
    1034: (u'GetType', 2, 0),
    1036: (u'GetEquipType', 2, 0),
    1038: (u'GetWeaponClipRounds', 2, 0),
    1039: (u'GetAttackDamage', 2, 0),
    1040: (u'GetWeaponType', 2, 0),
    1041: (u'GetWeaponMinSpread', 2, 0),
    1042: (u'GetWeaponSpread', 2, 0),
    1044: (u'GetWeaponSightFOV', 2, 0),
    1045: (u'GetWeaponMinRange', 2, 0),
    1046: (u'GetWeaponMaxRange', 2, 0),
    1047: (u'GetWeaponAmmoUse', 2, 0),
    1048: (u'GetWeaponActionPoints', 2, 0),
    1049: (u'GetWeaponCritDamage', 2, 0),
    1050: (u'GetWeaponCritChance', 2, 0),
    1052: (u'GetWeaponFireRate', 2, 0),
    1053: (u'GetWeaponAnimAttackMult', 2, 0),
    1054: (u'GetWeaponRumbleLeftMotor', 2, 0),
    1055: (u'GetWeaponRumbleRightMotor', 2, 0),
    1056: (u'GetWeaponRumbleDuration', 2, 0),
    1057: (u'GetWeaponRumbleWavelength', 2, 0),
    1058: (u'GetWeaponAnimShotsPerSec', 2, 0),
    1059: (u'GetWeaponAnimReloadTime', 2, 0),
    1060: (u'GetWeaponAnimJamTime', 2, 0),
    1061: (u'GetWeaponSkill', 2, 0),
    1062: (u'GetWeaponResistType', 2, 0),
    1063: (u'GetWeaponFireDelayMin', 2, 0),
    1064: (u'GetWeaponFireDelayMax', 2, 0),
    1065: (u'GetWeaponAnimMult', 2, 0),
    1066: (u'GetWeaponReach', 2, 0),
    1067: (u'GetWeaponIsAutomatic', 2, 0),
    1068: (u'GetWeaponHandGrip', 2, 0),
    1069: (u'GetWeaponReloadAnim', 2, 0),
    1070: (u'GetWeaponBaseVATSChance', 2, 0),
    1071: (u'GetWeaponAttackAnimation', 2, 0),
    1072: (u'GetWeaponNumProjectiles', 2, 0),
    1073: (u'GetWeaponAimArc', 2, 0),
    1074: (u'GetWeaponLimbDamageMult', 2, 0),
    1075: (u'GetWeaponSightUsage', 2, 0),
    1076: (u'GetWeaponHasScope', 2, 0),
    1089: (u'ListGetFormIndex', 2, 2),
    1098: (u'GetEquippedCurrentHealth', 1, 0),
    1102: (u'GetNumItems', 0, 0),
    1105: (u'GetCurrentHealth', 0, 0),
    1107: (u'IsKeyPressed', 1, 1),
    1131: (u'IsControlPressed', 1, 1),
    1144: (u'GetArmorAR', 2, 0),
    1145: (u'IsPowerArmor', 2, 0),
    1148: (u'IsQuestItem', 2, 0),
    1203: (u'GetArmorDT', 2, 0),
    1212: (u'GetWeaponRequiredStrength', 2, 0),
    1213: (u'GetWeaponRequiredSkill', 2, 0),
    1218: (u'GetAmmoSpeed', 2, 0),
    1219: (u'GetAmmoConsumedPercent', 2, 0),
    1254: (u'GetWeaponLongBursts', 2, 0),
    1256: (u'GetWeaponFlags1', 2, 0),
    1257: (u'GetWeaponFlags2', 2, 0),
    1266: (u'GetEquippedWeaponModFlags', 0, 0),
    1271: (u'HasOwnership', 2, 0),
    1272: (u'IsOwned', 2, 0),
    1274: (u'GetDialogueTarget', 2, 0),
    1275: (u'GetDialogueSubject', 2, 0),
    1276: (u'GetDialogueSpeaker', 2, 0),
    1278: (u'GetAgeClass', 2, 0),
    1286: (u'GetTokenValue', 2, 0),
    1288: (u'GetTokenRef', 2, 0),
    1291: (u'GetPaired', 2, 2),
    1292: (u'GetRespawn', 2, 0),
    1294: (u'GetPermanent', 2, 0),
    1297: (u'IsRefInList', 2, 2),
    1301: (u'GetPackageCount', 2, 0),
    1440: (u'IsPlayerSwimming', 0, 0),
    1441: (u'GetTFC', 0, 0),
    1475: (u'GetPerkRank', 2, 2),
    1476: (u'GetAltPerkRank', 2, 2),
    1541: (u'GetActorFIKstatus', 0, 0),

    # Added by nvse_plugin_ExtendedActorVariable (obsolete & unreleased)
    4352: (u'GetExtendedActorVariable', 2, 0),
    4353: (u'GetBaseExtendedActorVariable', 2, 0),
    4355: (u'GetModExtendedActorVariable', 2, 0),

    # Added by nvse_extender
    4420: (u'NX_GetEVFl', 0, 0),
    4426: (u'NX_GetQVEVFl', 2, 1),

    # Added by lutana_nvse (included in JIP)
    4612: (u'IsButtonPressed', 1, 0),
    4613: (u'GetLeftStickX', 0, 0),
    4614: (u'GetLeftStickY', 0, 0),
    4615: (u'GetRightStickX', 0, 0),
    4616: (u'GetRightStickY', 0, 0),
    4617: (u'GetLeftTrigger', 0, 0),
    4618: (u'GetRightTrigger', 0, 0),
    4708: (u'GetArmorClass', 2, 0),
    4709: (u'IsRaceInList', 2, 0),
    4758: (u'IsButtonDisabled', 1, 0),
    4761: (u'IsButtonHeld', 1, 0),
    4774: (u'IsTriggerDisabled', 1, 0),
    4777: (u'IsTriggerHeld', 1, 0),
    4822: (u'GetReferenceFlag', 1, 0),
    4832: (u'GetDistance2D', 2, 0),
    4833: (u'GetDistance3D', 2, 0),
    4843: (u'PlayerHasKey', 0, 0),
    4897: (u'ActorHasEffect', 2, 0),

    # Added by JIP NVSE Plugin - up to date with v56.31
    5637: (u'GetIsPoisoned', 0, 0),
    5708: (u'IsEquippedWeaponSilenced', 0, 0),
    5709: (u'IsEquippedWeaponScoped', 0, 0),
    5884: (u'IsPCInCombat', 0, 0),
    5894: (u'GetEncumbranceRate', 0, 0),
    5947: (u'GetActorLightAmount', 0, 0),
    5951: (u'GetGameDifficulty', 0, 0),
    5962: (u'GetPCDetectionState', 0, 0),
    5969: (u'GetPipboyRadio', 0, 0),
    5993: (u'IsAttacking', 0, 0),
    5994: (u'GetPCUsingScope', 0, 0),
    6010: (u'GetPCUsingIronSights', 0, 0),
    6012: (u'GetRadiationLevelAlt', 0, 0),
    6013: (u'IsInWater', 0, 0),
    6058: (u'GetAlwaysRun', 0, 0),
    6059: (u'GetAutoMove', 0, 0),
    6061: (u'GetIsRagdolled', 0, 0),
    6065: (u'AuxVarGetFltCond', 2, 1),
    6069: (u'IsInAir', 0, 0),
    6073: (u'GetHasContactType', 1, 0),
    6124: (u'IsSpellTargetAlt', 2, 0),
    6186: (u'IsInCharGen', 0, 0),
    6192: (u'GetWaterImmersionPerc', 0, 0),
    6204: (u'IsFleeing', 0, 0),
    6217: (u'GetTargetUnreachable', 0, 0),
    6268: (u'IsInKillCam', 0, 0),
    6301: (u'IsStickDisabled', 1, 0),
    6317: (u'GetHardcoreTracking', 0, 0),
    6321: (u'GetNoteRead', 2, 0),
    6361: (u'GetInFactionList', 2, 0),
    6368: (u'GetGroundMaterial', 0, 0),
    6391: (u'EquippedWeaponHasModType', 1, 0),

    # Added by TTW nvse plugin
    10247: (u'TTW_GetEquippedWeaponSkill', 0, 0),
})

# Remove functions with different indices in FNV
del condition_function_data[1082] # IsKeyPressed, 1107 in FNV
del condition_function_data[1165] # GetWeaponHasScope, 1076 in FNV
del condition_function_data[1166] # IsControlPressed, 1131 in FNV
del condition_function_data[1213] # GetFOSEBeta, 1026 in FNV

#------------------------------------------------------------------------------
# Import Names
#------------------------------------------------------------------------------
namesTypes |= {b'CCRD', b'CHAL', b'CHIP', b'CMNY', b'CSNO', b'IMOD', b'RCCT',
               b'RCPE', b'REPU', }

#------------------------------------------------------------------------------
# Import Stats
#------------------------------------------------------------------------------
statsTypes.update({
    b'AMMO': (u'eid', u'weight', u'value', u'speed', u'clipRounds',
              u'projPerShot'),
    b'ARMA': (u'eid', u'weight', u'value', u'health', u'dr', u'dt'),
    b'ARMO': (u'eid', u'weight', u'value', u'health', u'dr', u'dt'),
    b'WEAP': (
        u'eid', u'weight', u'value', u'health', u'damage', u'clipsize',
        u'animationMultiplier', u'reach', u'ammoUse', u'minSpread', u'spread',
        u'sightFov', u'baseVatsToHitChance', u'projectileCount', u'minRange',
        u'maxRange', u'animationAttackMultiplier', u'fireRate',
        u'overrideActionPoint', u'rumbleLeftMotorStrength',
        u'rumbleRightMotorStrength', u'rumbleDuration',
        u'overrideDamageToWeaponMult', u'attackShotsPerSec', u'reloadTime',
        u'jamTime', u'aimArc', u'rumbleWavelength', u'limbDmgMult',
        u'sightUsage', u'semiAutomaticFireDelayMin',
        u'semiAutomaticFireDelayMax', u'strengthReq', u'regenRate',
        u'killImpulse', u'impulseDist', u'skillReq', u'criticalDamage',
        u'criticalMultiplier', u'vatsSkill', u'vatsDamMult', u'vatsAp'),
})

#------------------------------------------------------------------------------
# Import Sounds
#------------------------------------------------------------------------------
soundsTypes.update({
    b'CONT': (u'soundOpen', u'soundClose', u'soundRandomLooping'),
    b'WEAP': (u'pickupSound', u'dropSound', u'soundGunShot3D',
              u'soundGunShot2D', u'soundGunShot3DLooping',
              u'soundMeleeSwingGunNoAmmo', u'soundBlock', u'idleSound',
              u'equipSound', u'unequipSound', u'soundMod1Shoot3Ds',
              u'soundMod1Shoot2D', u'soundLevel'),
})

#------------------------------------------------------------------------------
# Import Graphics
#------------------------------------------------------------------------------
graphicsTypes.update({
    b'CCRD': (u'iconPath', u'smallIconPath', u'model', u'textureFace',
              u'textureBack'),
    b'CHAL': (u'iconPath', u'smallIconPath'),
    b'CHIP': (u'iconPath', u'smallIconPath', u'model'),
    b'CMNY': (u'iconPath', u'smallIconPath', u'model'),
    b'CSNO': (u'chipModels', u'slotMachineModel', u'blackjackTableModel',
              u'extraBlackjackTableModel', u'rouletteTableModel',
              u'slotReelTextures', u'blackjackDecks'),
    b'IMOD': (u'iconPath', u'smallIconPath', u'model'),
    b'REPU': (u'iconPath', u'smallIconPath'),
    b'WEAP': (u'iconPath', u'smallIconPath', u'model', u'shellCasingModel',
              u'scopeModel', u'worldModel', u'modelWithMods',
              u'firstPersonModelWithMods', u'animationType', u'gripAnimation',
              u'reloadAnimation'),
})

#------------------------------------------------------------------------------
# Import Text
#------------------------------------------------------------------------------
text_types.update({
    b'CHAL': (u'description',),
    b'IMOD': (u'description',),
})

#------------------------------------------------------------------------------
# Import Object Bounds
#------------------------------------------------------------------------------
object_bounds_types |= {b'CCRD', b'CHIP', b'CMNY', b'IMOD', }

#------------------------------------------------------------------------------
# Contents Checker
#------------------------------------------------------------------------------
# Entry types used for CONT, CREA, LVLI and NPC_
_common_entry_types = {b'ALCH', b'AMMO', b'ARMO', b'BOOK', b'CCRD', b'CHIP',
                       b'CMNY', b'IMOD', b'KEYM', b'LIGH', b'LVLI', b'MISC',
                       b'NOTE', b'WEAP'}
cc_valid_types = {
    b'CONT': _common_entry_types,
    b'CREA': _common_entry_types,
    b'LVLC': {b'CREA', b'LVLC'},
    b'LVLN': {b'LVLN', b'NPC_'},
    b'LVLI': _common_entry_types,
    b'NPC_': _common_entry_types,
}

#------------------------------------------------------------------------------
# Import Scripts
#------------------------------------------------------------------------------
scripts_types |= {b'AMMO', b'CCRD', b'CHAL', b'IMOD'}

#------------------------------------------------------------------------------
# Import Destructible
#------------------------------------------------------------------------------
destructible_types |= {b'CHIP', b'IMOD'}

#------------------------------------------------------------------------------
# Import Actors
#------------------------------------------------------------------------------
actor_importer_attrs[b'NPC_'][u'Actors.ACBS'] = ( # FO3 + flags.autocalcService
    u'barterGold', u'calcMax', u'calcMin', u'dispositionBase', u'fatigue',
    u'flags.autoCalc', u'flags.autocalcService', u'flags.canBeAllRaces',
    u'flags.essential', u'flags.female', u'flags.isChargenFacePreset',
    u'flags.noBloodDecal', u'flags.noBloodSpray', u'flags.noKnockDown',
    u'flags.noLowLevel', u'flags.noRotatingHeadTrack', u'flags.notPushable',
    u'flags.noVATSMelee', u'flags.pcLevelOffset', u'flags.respawn', u'karma',
    u'level_offset', u'speedMultiplier')

#------------------------------------------------------------------------------
# Tweak Assorted
#------------------------------------------------------------------------------
assorted_tweaks |= {u'AssortedTweak_ArrowWeight'}

#------------------------------------------------------------------------------
# Tweak Settings
#------------------------------------------------------------------------------
settings_tweaks |= {u'GmstTweak_Actor_StrengthEncumbranceMultiplier'}

#------------------------------------------------------------------------------
# Tweak Names
#------------------------------------------------------------------------------
names_tweaks -= {u'NamesTweak_AmmoWeight_Fo3'}
names_tweaks |= {u'NamesTweak_AmmoWeight_Fnv'}
