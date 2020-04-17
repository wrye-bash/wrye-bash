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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

# Import all constants from FO3 then edit them as needed
from ..fallout3.constants import *

#--Game ESM/ESP/BSA files
#  These filenames need to be in lowercase,
bethDataFiles = {
    #--Vanilla
    u'falloutnv.esm',
    u'fallout - invalidation.bsa',
    u'fallout - meshes.bsa',
    u'fallout - meshes2.bsa',
    u'fallout - misc.bsa',
    u'fallout - sound.bsa',
    u'fallout - textures.bsa',
    u'fallout - textures2.bsa',
    u'fallout - voices1.bsa',
    #--Preorder Packs
    u'caravanpack.esm',
    u'caravanpack - main.bsa',
    u'classicpack.esm',
    u'classicpack - main.bsa',
    u'mercenarypack.esm',
    u'mercenarypack - main.bsa',
    u'tribalpack.esm',
    u'tribalpack - main.bsa',
    #--DLCs
    u'deadmoney.esm',
    u'deadmoney - main.bsa',
    u'deadmoney - sounds.bsa',
    u'gunrunnersarsenal.esm',
    u'gunrunnersarsenal - main.bsa',
    u'gunrunnersarsenal - sounds.bsa',
    u'honesthearts.esm',
    u'honesthearts - main.bsa',
    u'honesthearts - sounds.bsa',
    u'oldworldblues.esm',
    u'oldworldblues - main.bsa',
    u'oldworldblues - sounds.bsa',
    u'lonesomeroad.esm',
    u'lonesomeroad - main.bsa',
    u'lonesomeroad - sounds.bsa',
}

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

    # extended by NVSE
    1024: (u'GetNVSEVersion', 0, 0),
    1025: (u'GetNVSERevision', 0, 0),
    1026: (u'GetNVSEBeta', 0, 0),
    1028: (u'GetWeight', 2, 0),
    1076: (u'GetWeaponHasScope', 2, 0),
    1089: (u'ListGetFormIndex', 2, 2),
    1107: (u'IsKeyPressed', 1, 1),
    1131: (u'IsControlPressed', 1, 1),
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

    # Added by nvse_plugin_ExtendedActorVariable
    4352: (u'GetExtendedActorVariable', 2, 0),
    4353: (u'GetBaseExtendedActorVariable', 2, 0),
    4355: (u'GetModExtendedActorVariable', 2, 0),

    # Added by nvse_extender
    4420: (u'NX_GetEVFl', 0, 0),
    4426: (u'NX_GetQVEVFl', 2, 1),

    # Added by lutana_nvse
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

    # Added by JIP NVSE Plugin
    5637: (u'GetIsPoisoned', 0, 0),
    5708: (u'IsEquippedWeaponSilenced', 0, 0),
    5709: (u'IsEquippedWeaponScoped', 0, 0),
    5947: (u'GetActorLightAmount', 0, 0),
    5951: (u'GetGameDifficulty', 0, 0),
    5962: (u'GetPCDetectionState', 0, 0),
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
    6070: (u'GetHasContact', 2, 0),
    6072: (u'GetHasContactBase', 2, 0),
    6073: (u'GetHasContactType', 1, 0),
    6124: (u'IsSpellTargetAlt', 2, 0),
    6167: (u'IsIdlePlayingEx', 2, 0),
    6186: (u'IsInCharGen', 0, 0),
    6192: (u'GetWaterImmersionPerc', 0, 0),
    6204: (u'IsFleeing', 0, 0),
    6217: (u'GetTargetUnreachable', 0, 0),
})

# Remove functions with different indices in FNV
del condition_function_data[1082] # IsKeyPressed, 1107 in FNV
del condition_function_data[1165] # GetWeaponHasScope, 1076 in FNV
del condition_function_data[1166] # IsControlPressed, 1131 in FNV
del condition_function_data[1213] # GetFOSEBeta, 1026 in FNV

#--List of GMST's in the main plugin (FalloutNV.esm) that have 0x00000000
#  as the form id.  Any GMST as such needs its Editor Id listed here.
gmstEids = gmstEids + ['fActorStrengthEncumbranceMult']

GmstTweaks = GmstTweaks[:]
GmstTweaks.insert(0, (
    _(u'Actor: Strength Encumbrance Multiplier'),
    _(u"Actor's Strength X this = Actor's Encumbrance capacity."),
        (u'fActorStrengthEncumbranceMult',),
        (u'1',            1.0),
        (u'3',            3.0),
        (u'[5]',          5.0),
        (u'8',            8.0),
        (u'10',           10.0),
        (u'20',           20.0),
        (_(u'Unlimited'), 999999.0),
        (_(u'Custom'),    5.0),
    ))

#------------------------------------------------------------------------------
# NamesPatcher
#------------------------------------------------------------------------------
namesTypes = namesTypes | {
    b'CCRD', b'CHAL', b'CHIP', b'CMNY', b'CSNO', b'IMOD', b'RCCT', b'RCPE',
    b'REPU',
}

#------------------------------------------------------------------------------
# StatsImporter
#------------------------------------------------------------------------------
statsTypes.update({
    b'AMMO': (u'eid', u'weight', u'value', u'speed', u'clipRounds',
              u'projPerShot'),
    b'ARMA': (u'eid', u'weight', u'value', u'health', u'ar', u'dt'),
    b'ARMO': (u'eid', u'weight', u'value', u'health', u'ar', u'dt'),
    b'WEAP': (
        u'eid', u'weight', u'value', u'health', u'damage', u'clipsize',
        u'animationMultiplier', u'reach', u'ammoUse', u'minSpread', u'spread',
        u'sightFov', u'baseVatsToHitChance', u'projectileCount', u'minRange',
        u'maxRange', u'animationAttackMultiplier', u'fireRate',
        u'overrideActionPoint', u'rumbleLeftMotorStrength',
        u'rumbleRightMotorStrength', u'rumbleDuration',
        u'overrideDamageToWeaponMult', u'attackShotsPerSec', u'reloadTime',
        u'jamTime', u'aimArc', u'rambleWavelangth', u'limbDmgMult',
        u'sightUsage', u'semiAutomaticFireDelayMin',
        u'semiAutomaticFireDelayMax', u'strengthReq', u'regenRate',
        u'killImpulse', u'impulseDist', u'skillReq', u'criticalDamage',
        u'criticalMultiplier', u'vatsSkill', u'vatsDamMult', u'vatsAp'),
})

##: Format needs rethinking - will be done in inf-312-parser-abc
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
        _(u'Editor Id'),_(u'Weight'),_(u'Value'),_(u'Health'),_(u'AR'),_(u'DT'))) + u'"\n')),
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
        _(u'Semi-Automatic Fire Delay Max'),_(u'Strength Req'), _(u'Regen Rate'),
        _(u'Kill Impulse'), _(u'Impulse Dist'), _(u'Skill Req'),_(u'Critical Damage'),
        _(u'Crit % Mult'),_(u'VATS Skill'), _(u'VATS Dam. Mult'),
        _(u'VATS AP'))) + u'"\n')),
)

#------------------------------------------------------------------------------
# SoundPatcher
#------------------------------------------------------------------------------
soundsTypes.update({
    b'CONT': (u'soundOpen', u'soundClose', u'soundRandomLooping'),
    b'WEAP': (
        u'pickupSound', u'dropSound', u'soundGunShot3D', u'soundGunShot2D',
        u'soundGunShot3DLooping', u'soundMeleeSwingGunNoAmmo', u'soundBlock',
        u'idleSound', u'equipSound', u'unequipSound', u'soundMod1Shoot3Ds',
        u'soundMod1Shoot2D', u'soundLevel')})

#------------------------------------------------------------------------------
# GraphicsPatcher
#------------------------------------------------------------------------------
graphicsLongsTypes = graphicsLongsTypes | {b'CCRD', b'CHIP', b'CMNY', b'CSNO',
                                           b'IMOD', b'REPU'}
graphicsTypes.update({
    b'CCRD': (u'iconPath', u'smallIconPath', u'model', u'textureFace',
              u'textureBack'),
    b'CHIP': (u'iconPath', u'smallIconPath', u'model'),
    b'CMNY': (u'iconPath', u'smallIconPath', u'model'),
    b'CSNO': (u'chipModels', u'slotMachineModel', u'blackjackTableModel',
              u'extraBlackjackTableModel', u'rouletteTableModel',
              u'slotReelTextures', u'blackjackDecks'),
    b'IMOD': (u'iconPath', u'smallIconPath', u'model'),
    b'REPU': (u'iconPath', u'smallIconPath'),
    b'WEAP': (
        u'iconPath', u'smallIconPath', u'model', u'objectEffect',
        u'shellCasingModel', u'scopeModel', u'scopeEffect', u'worldModel',
        u'modelWithMods', u'impactDataset', u'firstPersonModel',
        u'firstPersonModelWithMods', u'animationType', u'gripAnimation',
        u'reloadAnimation'),
})

#------------------------------------------------------------------------------
# Race Patcher
#------------------------------------------------------------------------------
# Note that we use _x to avoid exposing these to the dynamic importer
def _fnv(_x): return u'FalloutNV.esm', _x
_standard_eyes = [_fnv(_x) for _x in (0x4252, 0x4253, 0x4254, 0x4255, 0x4256)]
default_eyes = {
    #--FalloutNV.esm
    # Caucasian
    _fnv(0x000019): _standard_eyes,
    # Hispanic
    _fnv(0x0038e5): _standard_eyes,
    # Asian
    _fnv(0x0038e6): _standard_eyes,
    # Ghoul
    _fnv(0x003b3e): [_fnv(0x35e4f)],
    # AfricanAmerican
    _fnv(0x00424a): _standard_eyes,
    # AfricanAmerican Child
    _fnv(0x0042be): _standard_eyes,
    # AfricanAmerican Old
    _fnv(0x0042bf): _standard_eyes,
    # Asian Child
    _fnv(0x0042c0): _standard_eyes,
    # Asian Old
    _fnv(0x0042c1): _standard_eyes,
    # Caucasian Child
    _fnv(0x0042c2): _standard_eyes,
    # Caucasian Old
    _fnv(0x0042c3): _standard_eyes,
    # Hispanic Child
    _fnv(0x0042c4): _standard_eyes,
    # Hispanic Old
    _fnv(0x0042c5): _standard_eyes,
    # Caucasian Raider
    _fnv(0x04bb8d): [_fnv(0x4cb10)],
    # Hispanic Raider
    _fnv(0x04bf70): [_fnv(0x4cb10)],
    # Asian Raider
    _fnv(0x04bf71): [_fnv(0x4cb10)],
    # AfricanAmerican Raider
    _fnv(0x04bf72): [_fnv(0x4cb10)],
    # Hispanic Old Aged
    _fnv(0x0987dc): _standard_eyes,
    # Asian Old Aged
    _fnv(0x0987dd): _standard_eyes,
    # AfricanAmerican Old Aged
    _fnv(0x0987de): _standard_eyes,
    # Caucasian Old Aged
    _fnv(0x0987df): _standard_eyes,
}
# Clean this up, no need to keep it around now
del _fnv

#------------------------------------------------------------------------------
# Text Patcher
#------------------------------------------------------------------------------
text_types.update({
    b'CHAL': (u'description',),
    b'IMOD': (u'description',),
})

#------------------------------------------------------------------------------
# Object Bounds Patcher
#------------------------------------------------------------------------------
object_bounds_types = object_bounds_types | {
    b'CCRD', b'CHIP', b'CMNY', b'IMOD',
}

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
# Scripts Patcher
#------------------------------------------------------------------------------
scripts_types = scripts_types | {b'AMMO', b'CCRD', b'CHAL', b'IMOD'}

#------------------------------------------------------------------------------
# Destructible Patcher
#------------------------------------------------------------------------------
destructible_types = destructible_types | {b'CHIP', b'IMOD'}

#------------------------------------------------------------------------------
# Actor Patchers
#------------------------------------------------------------------------------
actor_importer_attrs[b'NPC_'][u'Actors.ACBS'] = ( # FO3 + flags.autocalcService
    u'barterGold', u'calcMax', u'calcMin', u'dispositionBase', u'fatigue',
    u'flags.autoCalc', u'flags.autocalcService', u'flags.canBeAllRaces',
    u'flags.essential', u'flags.female', u'flags.isChargenFacePreset',
    u'flags.noBloodDecal', u'flags.noBloodSpray', u'flags.noKnockDown',
    u'flags.noLowLevel', u'flags.noRotatingHeadTrack', u'flags.notPushable',
    u'flags.noVATSMelee', u'flags.pcLevelOffset', u'flags.respawn',
    u'flags.useTemplate', u'karma', u'level', u'speedMultiplier',
    u'templateFlags')
