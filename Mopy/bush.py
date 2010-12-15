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
#  Wrye Bash copyright (C) 2005, 2006, 2007, 2008, 2009 Wrye
#
# =============================================================================

"""This module defines static data for use by other modules in the Wrye Bash package.
Its use should generally be restricted to large chunks of data and/or chunks of data
that are used by multiple objects."""

# Imports ---------------------------------------------------------------------
import struct
import ctypes

from bolt import _,GPath

# Installer -------------------------------------------------------------------
bethDataFiles = set((
    #--Vanilla
    'oblivion.esm',
    'oblivion_1.1.esm',
    'oblivion_si.esm',
    'oblivion_1.1.esm.ghost',
    'oblivion_si.esm.ghost',
    'oblivion - meshes.bsa',
    'oblivion - misc.bsa',
    'oblivion - sounds.bsa',
    'oblivion - textures - compressed.bsa',
    'oblivion - textures - compressed.bsa.orig',
    'oblivion - voices1.bsa',
    'oblivion - voices2.bsa',
    #--Shivering Isles
    'dlcshiveringisles.esp',
    'dlcshiveringisles - meshes.bsa',
    'dlcshiveringisles - sounds.bsa',
    'dlcshiveringisles - textures.bsa',
    'dlcshiveringisles - voices.bsa',
    ))

# Balo Canonical Groups -------------------------------------------------------
baloGroups = (
    ('Root',),
    ('Library',1),
    ('Cosmetic',),
    ('Clothing',),
    ('Weapon',),
    ('Tweak',2,-1),
    ('Overhaul',4,-1),
    ('Misc.',1),
    ('Magic',2),
    ('NPC',),
    ('Home',1),
    ('Place',1),
    ('Quest',3,-1),
    ('Last',1,-1),
    )

# Tes3 Group/Top Types -------------------------------------------------------------
groupTypes = [
    _('Top (Type)'),
    _('World Children'),
    _('Int Cell Block'),
    _('Int Cell Sub-Block'),
    _('Ext Cell Block'),
    _('Ext Cell Sub-Block'),
    _('Cell Children'),
    _('Topic Children'),
    _('Cell Persistent Childen'),
    _('Cell Temporary Children'),
    _('Cell Visible Distant Children'),
]

#--Top types in Oblivion order.
topTypes = ['GMST', 'GLOB', 'CLAS', 'FACT', 'HAIR', 'EYES', 'RACE', 'SOUN', 'SKIL',
    'MGEF', 'SCPT', 'LTEX', 'ENCH', 'SPEL', 'BSGN', 'ACTI', 'APPA', 'ARMO', 'BOOK',
    'CLOT', 'CONT', 'DOOR', 'INGR', 'LIGH', 'MISC', 'STAT', 'GRAS', 'TREE', 'FLOR',
    'FURN', 'WEAP', 'AMMO', 'NPC_', 'CREA', 'LVLC', 'SLGM', 'KEYM', 'ALCH', 'SBSP',
    'SGST', 'LVLI', 'WTHR', 'CLMT', 'REGN', 'CELL', 'WRLD', 'DIAL', 'QUST', 'IDLE',
    'PACK', 'CSTY', 'LSCR', 'LVSP', 'ANIO', 'WATR', 'EFSH']

#--Dict mapping 'ignored' top types to un-ignored top types.
topIgTypes = dict([(struct.pack('I',(struct.unpack('I',type)[0]) | 0x1000),type) for type in topTypes])

recordTypes = set(topTypes + 'GRUP,TES4,ROAD,REFR,ACHR,ACRE,PGRD,LAND,INFO'.split(','))

# Id Functions ----------------------------------------------------------------
def getIdFunc(modName):
    return lambda x: (GPath(modName),x)

ob = getIdFunc('Oblivion.esm')
cobl = getIdFunc('Cobl Main.esm')

# Race Info -------------------------------------------------------------------
raceNames = {
    0x23fe9 : _('Argonian'),
    0x224fc : _('Breton'),
    0x191c1 : _('Dark Elf'),
    0x19204 : _('High Elf'),
    0x00907 : _('Imperial'),
    0x22c37 : _('Khajiit'),
    0x224fd : _('Nord'),
    0x191c0 : _('Orc'),
    0x00d43 : _('Redguard'),
    0x00019 : _('Vampire'),
    0x223c8 : _('Wood Elf'),
    }

raceShortNames = {
    0x23fe9 : 'Arg',
    0x224fc : 'Bre',
    0x191c1 : 'Dun',
    0x19204 : 'Alt',
    0x00907 : 'Imp',
    0x22c37 : 'Kha',
    0x224fd : 'Nor',
    0x191c0 : 'Orc',
    0x00d43 : 'Red',
    0x223c8 : 'Bos',
    }

raceHairMale = {
    0x23fe9 : 0x64f32, #--Arg
    0x224fc : 0x90475, #--Bre
    0x191c1 : 0x64214, #--Dun
    0x19204 : 0x7b792, #--Alt
    0x00907 : 0x90475, #--Imp
    0x22c37 : 0x653d4, #--Kha
    0x224fd : 0x1da82, #--Nor
    0x191c0 : 0x66a27, #--Orc
    0x00d43 : 0x64215, #--Red
    0x223c8 : 0x690bc, #--Bos
    }

raceHairFemale = {
    0x23fe9 : 0x64f33, #--Arg
    0x224fc : 0x1da83, #--Bre
    0x191c1 : 0x1da83, #--Dun
    0x19204 : 0x690c2, #--Alt
    0x00907 : 0x1da83, #--Imp
    0x22c37 : 0x653d0, #--Kha
    0x224fd : 0x1da83, #--Nor
    0x191c0 : 0x64218, #--Orc
    0x00d43 : 0x64210, #--Red
    0x223c8 : 0x69473, #--Bos
    }

# Default Eyes/Hair -----------------------------------------------------------
standardEyes = [ob(x) for x in (0x27306,0x27308,0x27309)] + [cobl(x) for x in (0x000821, 0x000823, 0x000825, 0x000828, 0x000834, 0x000837, 0x000839, 0x00084F, )]

defaultEyes = {
    #--Oblivion.esm
    ob(0x23FE9): #--Argonian
        [ob(0x3E91E)] + [cobl(x) for x in (0x01F407, 0x01F408, 0x01F40B, 0x01F40C, 0x01F410, 0x01F411, 0x01F414, 0x01F416, 0x01F417, 0x01F41A, 0x01F41B, 0x01F41E, 0x01F41F, 0x01F422, 0x01F424, )],
    ob(0x0224FC): #--Breton
        standardEyes,
    ob(0x0191C1): #--Dark Elf
        [ob(0x27307)] + [cobl(x) for x in (0x000861,0x000864,0x000851)],
    ob(0x019204): #--High Elf
        standardEyes,
    ob(0x000907): #--Imperial
        standardEyes,
    ob(0x022C37): #--Khajiit
        [ob(0x375c8)] + [cobl(x) for x in (0x00083B, 0x00083E, 0x000843, 0x000846, 0x000849, 0x00084C, )],
    ob(0x0224FD): #--Nord
        standardEyes,
    ob(0x0191C0): #--Orc
        [ob(0x2730A)]+[cobl(x) for x in (0x000853, 0x000855, 0x000858, 0x00085A, 0x00085C, 0x00085E, )],
    ob(0x000D43): #--Redguard
        standardEyes,
    ob(0x0223C8): #--Wood Elf
        standardEyes,
    #--Cobl
    cobl(0x07948): #--cobRaceAureal
        [ob(0x54BBA)],
    cobl(0x02B60): #--cobRaceHidden
        [cobl(x) for x in (0x01F43A, 0x01F438, 0x01F439, 0x0015A7, 0x01792C, 0x0015AC, 0x0015A8, 0x0015AB, 0x0015AA,)],
    cobl(0x07947): #--cobRaceMazken
        [ob(0x54BB9)],
    cobl(0x1791B): #--cobRaceOhmes
        [cobl(x) for x in (0x017901, 0x017902, 0x017903, 0x017904, 0x017905, 0x017906, 0x017907, 0x017908, 0x017909, 0x01790A, 0x01790B, 0x01790C, 0x01790D, 0x01790E, 0x01790F, 0x017910, 0x017911, 0x017912, 0x017913, 0x017914, 0x017915, 0x017916, 0x017917, 0x017918, 0x017919, 0x01791A, 0x017900,)],
    cobl(0x1F43C): #--cobRaceXivilai
        [cobl(x) for x in (0x01F437, 0x00531B, 0x00531C, 0x00531D, 0x00531E, 0x00531F, 0x005320, 0x005321, 0x01F43B, 0x00DBE1, )],
    }

# Function Info ---------------------------------------------------------------
conditionFunctionData = ( #--0: no param; 1: int param; 2: formid param
    (153, 'CanHaveFlames', 0, 0),
    (127, 'CanPayCrimeGold', 0, 0),
    ( 14, 'GetActorValue', 1, 0),
    ( 61, 'GetAlarmed', 0, 0),
    (190, 'GetAmountSoldStolen', 0, 0),
    (  8, 'GetAngle', 1, 0),
    ( 81, 'GetArmorRating', 0, 0),
    (274, 'GetArmorRatingUpperBody', 0, 0),
    ( 63, 'GetAttacked', 0, 0),
    (264, 'GetBarterGold', 0, 0),
    (277, 'GetBaseActorValue', 1, 0),
    (229, 'GetClassDefaultMatch', 0, 0),
    ( 41, 'GetClothingValue', 0, 0),
    (122, 'GetCrime', 2, 1),
    (116, 'GetCrimeGold', 0, 0),
    (110, 'GetCurrentAIPackage', 0, 0),
    (143, 'GetCurrentAIProcedure', 0, 0),
    ( 18, 'GetCurrentTime', 0, 0),
    (148, 'GetCurrentWeatherPercent', 0, 0),
    (170, 'GetDayOfWeek', 0, 0),
    ( 46, 'GetDead', 0, 0),
    ( 84, 'GetDeadCount', 2, 0),
    (203, 'GetDestroyed', 0, 0),
    ( 45, 'GetDetected', 2, 0),
    (180, 'GetDetectionLevel', 2, 0),
    ( 35, 'GetDisabled', 0, 0),
    ( 39, 'GetDisease', 0, 0),
    ( 76, 'GetDisposition', 2, 0),
    (  1, 'GetDistance', 2, 0),
    (215, 'GetDoorDefaultOpen', 0, 0),
    (182, 'GetEquipped', 2, 0),
    ( 73, 'GetFactionRank', 2, 0),
    ( 60, 'GetFactionRankDifference', 2, 2),
    (128, 'GetFatiguePercentage', 0, 0),
    (288, 'GetFriendHit', 2, 0),
    (160, 'GetFurnitureMarkerID', 0, 0),
    ( 74, 'GetGlobalValue', 2, 0),
    ( 48, 'GetGold', 0, 0),
    ( 99, 'GetHeadingAngle', 2, 0),
    (318, 'GetIdleDoneOnce', 0, 0),
    (338, 'GetIgnoreFriendlyHits', 0, 0),
    ( 67, 'GetInCell', 2, 0),
    (230, 'GetInCellParam', 2, 2),
    ( 71, 'GetInFaction', 2, 0),
    ( 32, 'GetInSameCell', 2, 0),
    (305, 'GetInvestmentGold', 0, 0),
    (310, 'GetInWorldspace', 2, 0),
    ( 91, 'GetIsAlerted', 0, 0),
    ( 68, 'GetIsClass', 2, 0),
    (228, 'GetIsClassDefault', 2, 0),
    ( 64, 'GetIsCreature', 0, 0),
    (161, 'GetIsCurrentPackage', 2, 0),
    (149, 'GetIsCurrentWeather', 2, 0),
    (237, 'GetIsGhost', 0, 0),
    ( 72, 'GetIsID', 2, 0),
    (254, 'GetIsPlayableRace', 0, 0),
    (224, 'GetIsPlayerBirthsign', 2, 0),
    ( 69, 'GetIsRace', 2, 0),
    (136, 'GetIsReference', 2, 0),
    ( 70, 'GetIsSex', 1, 0),
    (246, 'GetIsUsedItem', 2, 0),
    (247, 'GetIsUsedItemType', 1, 0),
    ( 47, 'GetItemCount', 2, 0),
    (107, 'GetKnockedState', 0, 0),
    ( 80, 'GetLevel', 0, 0),
    ( 27, 'GetLineOfSight', 2, 0),
    (  5, 'GetLocked', 0, 0),
    ( 65, 'GetLockLevel', 0, 0),
    (320, 'GetNoRumors', 0, 0),
    (255, 'GetOffersServicesNow', 0, 0),
    (157, 'GetOpenState', 0, 0),
    (193, 'GetPCExpelled', 2, 0),
    (199, 'GetPCFactionAttack', 2, 0),
    (195, 'GetPCFactionMurder', 2, 0),
    (197, 'GetPCFactionSteal', 2, 0),
    (201, 'GetPCFactionSubmitAuthority', 2, 0),
    (249, 'GetPCFame', 0, 0),
    (132, 'GetPCInFaction', 2, 0),
    (251, 'GetPCInfamy', 0, 0),
    (129, 'GetPCIsClass', 2, 0),
    (130, 'GetPCIsRace', 2, 0),
    (131, 'GetPCIsSex', 1, 0),
    (312, 'GetPCMiscStat', 1, 0),
    (225, 'GetPersuasionNumber', 0, 0),
    ( 98, 'GetPlayerControlsDisabled', 0, 0),
    (365, 'GetPlayerInSEWorld',0,0),
    (362, 'GetPlayerHasLastRiddenHorse', 0, 0),
    (  6, 'GetPos', 1, 0),
    ( 56, 'GetQuestRunning', 2, 0),
    ( 79, 'GetQuestVariable', 2, 1),
    ( 77, 'GetRandomPercent', 0, 0),
    (244, 'GetRestrained', 0, 0),
    ( 24, 'GetScale', 0, 0),
    ( 53, 'GetScriptVariable', 2, 1),
    ( 12, 'GetSecondsPassed', 0, 0),
    ( 66, 'GetShouldAttack', 2, 0),
    (159, 'GetSitting', 0, 0),
    ( 49, 'GetSleeping', 0, 0),
    ( 58, 'GetStage', 2, 0),
    ( 59, 'GetStageDone', 2, 1),
    ( 11, 'GetStartingAngle', 1, 0),
    ( 10, 'GetStartingPos', 1, 0),
    ( 50, 'GetTalkedToPC', 0, 0),
    (172, 'GetTalkedToPCParam', 2, 0),
    (361, 'GetTimeDead', 0, 0),
    (315, 'GetTotalPersuasionNumber', 0, 0),
    (144, 'GetTrespassWarningLevel', 0, 0),
    (242, 'GetUnconscious', 0, 0),
    (259, 'GetUsedItemActivate', 0, 0),
    (258, 'GetUsedItemLevel', 0, 0),
    ( 40, 'GetVampire', 0, 0),
    (142, 'GetWalkSpeed', 0, 0),
    (108, 'GetWeaponAnimType', 0, 0),
    (109, 'GetWeaponSkillType', 0, 0),
    (147, 'GetWindSpeed', 0, 0),
    (154, 'HasFlames', 0, 0),
    (214, 'HasMagicEffect', 2, 0),
    (227, 'HasVampireFed', 0, 0),
    (353, 'IsActor', 0, 0),
    (314, 'IsActorAVictim', 0, 0),
    (313, 'IsActorEvil', 0, 0),
    (306, 'IsActorUsingATorch', 0, 0),
    (280, 'IsCellOwner', 2, 2),
    (267, 'IsCloudy', 0, 0),
    (150, 'IsContinuingPackagePCNear', 0, 0),
    (163, 'IsCurrentFurnitureObj', 2, 0),
    (162, 'IsCurrentFurnitureRef', 2, 0),
    (354, 'IsEssential', 0, 0),
    (106, 'IsFacingUp', 0, 0),
    (125, 'IsGuard', 0, 0),
    (282, 'IsHorseStolen', 0, 0),
    (112, 'IsIdlePlaying', 0, 0),
    (289, 'IsInCombat', 0, 0),
    (332, 'IsInDangerousWater', 0, 0),
    (300, 'IsInInterior', 0, 0),
    (146, 'IsInMyOwnedCell', 0, 0),
    (285, 'IsLeftUp', 0, 0),
    (278, 'IsOwner', 2, 0),
    (176, 'IsPCAMurderer', 0, 0),
    (175, 'IsPCSleeping', 0, 0),
    (171, 'IsPlayerInJail', 0, 0),
    (358, 'IsPlayerMovingIntoNewSpace', 0, 0),
    (339, 'IsPlayersLastRiddenHorse', 0, 0),
    (266, 'IsPleasant', 0, 0),
    ( 62, 'IsRaining', 0, 0),
    (327, 'IsRidingHorse', 0, 0),
    (287, 'IsRunning', 0, 0),
    (103, 'IsShieldOut', 0, 0),
    (286, 'IsSneaking', 0, 0),
    ( 75, 'IsSnowing', 0, 0),
    (223, 'IsSpellTarget', 2, 0),
    (185, 'IsSwimming', 0, 0),
    (141, 'IsTalking', 0, 0),
    (265, 'IsTimePassing', 0, 0),
    (102, 'IsTorchOut', 0, 0),
    (145, 'IsTrespassing', 0, 0),
    (329, 'IsTurnArrest', 0, 0),
    (111, 'IsWaiting', 0, 0),
    (101, 'IsWeaponOut', 0, 0),
    (309, 'IsXBox', 0, 0),
    (104, 'IsYielding', 0, 0),
    ( 36, 'MenuMode', 1, 0),
    ( 42, 'SameFaction', 2, 0),
    (133, 'SameFactionAsPC', 0, 0),
    ( 43, 'SameRace', 2, 0),
    (134, 'SameRaceAsPC', 0, 0),
    ( 44, 'SameSex', 2, 0),
    (135, 'SameSexAsPC', 0, 0),
    (323, 'WhichServiceMenu', 0, 0),
    )
allConditions = set(entry[0] for entry in conditionFunctionData)
fid1Conditions = set(entry[0] for entry in conditionFunctionData if entry[2] == 2)
fid2Conditions = set(entry[0] for entry in conditionFunctionData if entry[3] == 2)

# Magic Info ------------------------------------------------------------------
weaponTypes = (
    _('Blade (1 Handed)'),
    _('Blade (2 Handed)'),
    _('Blunt (1 Handed)'),
    _('Blunt (2 Handed)'),
    _('Staff'),
    _('Bow'),
    )

magicEffects = {
    'ABAT': [5,_('Absorb Attribute'),0.95],
    'ABFA': [5,_('Absorb Fatigue'),6],
    'ABHE': [5,_('Absorb Health'),16],
    'ABSK': [5,_('Absorb Skill'),2.1],
    'ABSP': [5,_('Absorb Magicka'),7.5],
    'BA01': [1,_('Bound Armor Extra 01'),0],#--Formid == 0
    'BA02': [1,_('Bound Armor Extra 02'),0],#--Formid == 0
    'BA03': [1,_('Bound Armor Extra 03'),0],#--Formid == 0
    'BA04': [1,_('Bound Armor Extra 04'),0],#--Formid == 0
    'BA05': [1,_('Bound Armor Extra 05'),0],#--Formid == 0
    'BA06': [1,_('Bound Armor Extra 06'),0],#--Formid == 0
    'BA07': [1,_('Bound Armor Extra 07'),0],#--Formid == 0
    'BA08': [1,_('Bound Armor Extra 08'),0],#--Formid == 0
    'BA09': [1,_('Bound Armor Extra 09'),0],#--Formid == 0
    'BA10': [1,_('Bound Armor Extra 10'),0],#--Formid == 0
    'BABO': [1,_('Bound Boots'),12],
    'BACU': [1,_('Bound Cuirass'),12],
    'BAGA': [1,_('Bound Gauntlets'),8],
    'BAGR': [1,_('Bound Greaves'),12],
    'BAHE': [1,_('Bound Helmet'),12],
    'BASH': [1,_('Bound Shield'),12],
    'BRDN': [0,_('Burden'),0.21],
    'BW01': [1,_('Bound Order Weapon 1'),1],
    'BW02': [1,_('Bound Order Weapon 2'),1],
    'BW03': [1,_('Bound Order Weapon 3'),1],
    'BW04': [1,_('Bound Order Weapon 4'),1],
    'BW05': [1,_('Bound Order Weapon 5'),1],
    'BW06': [1,_('Bound Order Weapon 6'),1],
    'BW07': [1,_('Summon Staff of Sheogorath'),1],
    'BW08': [1,_('Bound Priest Dagger'),1],
    'BW09': [1,_('Bound Weapon Extra 09'),0],#--Formid == 0
    'BW10': [1,_('Bound Weapon Extra 10'),0],#--Formid == 0
    'BWAX': [1,_('Bound Axe'),39],
    'BWBO': [1,_('Bound Bow'),95],
    'BWDA': [1,_('Bound Dagger'),14],
    'BWMA': [1,_('Bound Mace'),91],
    'BWSW': [1,_('Bound Sword'),235],
    'CALM': [3,_('Calm'),0.47],
    'CHML': [3,_('Chameleon'),0.63],
    'CHRM': [3,_('Charm'),0.2],
    'COCR': [3,_('Command Creature'),0.6],
    'COHU': [3,_('Command Humanoid'),0.75],
    'CUDI': [5,_('Cure Disease'),1400],
    'CUPA': [5,_('Cure Paralysis'),500],
    'CUPO': [5,_('Cure Poison'),600],
    'DARK': [3,_('DO NOT USE - Darkness'),0],
    'DEMO': [3,_('Demoralize'),0.49],
    'DGAT': [2,_('Damage Attribute'),100],
    'DGFA': [2,_('Damage Fatigue'),4.4],
    'DGHE': [2,_('Damage Health'),12],
    'DGSP': [2,_('Damage Magicka'),2.45],
    'DIAR': [2,_('Disintegrate Armor'),6.2],
    'DISE': [2,_('Disease Info'),0], #--Formid == 0
    'DIWE': [2,_('Disintegrate Weapon'),6.2],
    'DRAT': [2,_('Drain Attribute'),0.7],
    'DRFA': [2,_('Drain Fatigue'),0.18],
    'DRHE': [2,_('Drain Health'),0.9],
    'DRSK': [2,_('Drain Skill'),0.65],
    'DRSP': [2,_('Drain Magicka'),0.18],
    'DSPL': [4,_('Dispel'),3.6],
    'DTCT': [4,_('Detect Life'),0.08],
    'DUMY': [2,_('Mehrunes Dagon'),0], #--Formid == 0
    'FIDG': [2,_('Fire Damage'),7.5],
    'FISH': [0,_('Fire Shield'),0.95],
    'FOAT': [5,_('Fortify Attribute'),0.6],
    'FOFA': [5,_('Fortify Fatigue'),0.04],
    'FOHE': [5,_('Fortify Health'),0.14],
    'FOMM': [5,_('Fortify Magicka Multiplier'),0.04],
    'FOSK': [5,_('Fortify Skill'),0.6],
    'FOSP': [5,_('Fortify Magicka'),0.15],
    'FRDG': [2,_('Frost Damage'),7.4],
    'FRNZ': [3,_('Frenzy'),0.04],
    'FRSH': [0,_('Frost Shield'),0.95],
    'FTHR': [0,_('Feather'),0.1],
    'INVI': [3,_('Invisibility'),40],
    'LGHT': [3,_('Light'),0.051],
    'LISH': [0,_('Shock Shield'),0.95],
    'LOCK': [0,_('DO NOT USE - Lock'),30],
    'MYHL': [1,_('Summon Mythic Dawn Helm'),110],
    'MYTH': [1,_('Summon Mythic Dawn Armor'),120],
    'NEYE': [3,_('Night-Eye'),22],
    'OPEN': [0,_('Open'),4.3],
    'PARA': [3,_('Paralyze'),475],
    'POSN': [2,_('Poison Info'),0],
    'RALY': [3,_('Rally'),0.03],
    'REAN': [1,_('Reanimate'),10],
    'REAT': [5,_('Restore Attribute'),38],
    'REDG': [4,_('Reflect Damage'),2.5],
    'REFA': [5,_('Restore Fatigue'),2],
    'REHE': [5,_('Restore Health'),10],
    'RESP': [5,_('Restore Magicka'),2.5],
    'RFLC': [4,_('Reflect Spell'),3.5],
    'RSDI': [5,_('Resist Disease'),0.5],
    'RSFI': [5,_('Resist Fire'),0.5],
    'RSFR': [5,_('Resist Frost'),0.5],
    'RSMA': [5,_('Resist Magic'),2],
    'RSNW': [5,_('Resist Normal Weapons'),1.5],
    'RSPA': [5,_('Resist Paralysis'),0.75],
    'RSPO': [5,_('Resist Poison'),0.5],
    'RSSH': [5,_('Resist Shock'),0.5],
    'RSWD': [5,_('Resist Water Damage'),0], #--Formid == 0
    'SABS': [4,_('Spell Absorption'),3],
    'SEFF': [0,_('Script Effect'),0],
    'SHDG': [2,_('Shock Damage'),7.8],
    'SHLD': [0,_('Shield'),0.45],
    'SLNC': [3,_('Silence'),60],
    'STMA': [2,_('Stunted Magicka'),0],
    'STRP': [4,_('Soul Trap'),30],
    'SUDG': [2,_('Sun Damage'),9],
    'TELE': [4,_('Telekinesis'),0.49],
    'TURN': [1,_('Turn Undead'),0.083],
    'VAMP': [2,_('Vampirism'),0],
    'WABR': [0,_('Water Breathing'),14.5],
    'WAWA': [0,_('Water Walking'),13],
    'WKDI': [2,_('Weakness to Disease'),0.12],
    'WKFI': [2,_('Weakness to Fire'),0.1],
    'WKFR': [2,_('Weakness to Frost'),0.1],
    'WKMA': [2,_('Weakness to Magic'),0.25],
    'WKNW': [2,_('Weakness to Normal Weapons'),0.25],
    'WKPO': [2,_('Weakness to Poison'),0.1],
    'WKSH': [2,_('Weakness to Shock'),0.1],
    'Z001': [1,_('Summon Rufio\'s Ghost'),13],
    'Z002': [1,_('Summon Ancestor Guardian'),33.3],
    'Z003': [1,_('Summon Spiderling'),45],
    'Z004': [1,_('Summon Flesh Atronach'),1],
    'Z005': [1,_('Summon Bear'),47.3],
    'Z006': [1,_('Summon Gluttonous Hunger'),61],
    'Z007': [1,_('Summon Ravenous Hunger'),123.33],
    'Z008': [1,_('Summon Voracious Hunger'),175],
    'Z009': [1,_('Summon Dark Seducer'),1],
    'Z010': [1,_('Summon Golden Saint'),1],
    'Z011': [1,_('Wabba Summon'),0],
    'Z012': [1,_('Summon Decrepit Shambles'),45],
    'Z013': [1,_('Summon Shambles'),87.5],
    'Z014': [1,_('Summon Replete Shambles'),150],
    'Z015': [1,_('Summon Hunger'),22],
    'Z016': [1,_('Summon Mangled Flesh Atronach'),22],
    'Z017': [1,_('Summon Torn Flesh Atronach'),32.5],
    'Z018': [1,_('Summon Stitched Flesh Atronach'),75.5],
    'Z019': [1,_('Summon Sewn Flesh Atronach'),195],
    'Z020': [1,_('Extra Summon 20'),0],
    'ZCLA': [1,_('Summon Clannfear'),75.56],
    'ZDAE': [1,_('Summon Daedroth'),123.33],
    'ZDRE': [1,_('Summon Dremora'),72.5],
    'ZDRL': [1,_('Summon Dremora Lord'),157.14],
    'ZFIA': [1,_('Summon Flame Atronach'),45],
    'ZFRA': [1,_('Summon Frost Atronach'),102.86],
    'ZGHO': [1,_('Summon Ghost'),22],
    'ZHDZ': [1,_('Summon Headless Zombie'),56],
    'ZLIC': [1,_('Summon Lich'),350],
    'ZSCA': [1,_('Summon Scamp'),30],
    'ZSKA': [1,_('Summon Skeleton Guardian'),32.5],
    'ZSKC': [1,_('Summon Skeleton Champion'),152],
    'ZSKE': [1,_('Summon Skeleton'),11.25],
    'ZSKH': [1,_('Summon Skeleton Hero'),66],
    'ZSPD': [1,_('Summon Spider Daedra'),195],
    'ZSTA': [1,_('Summon Storm Atronach'),125],
    'ZWRA': [1,_('Summon Faded Wraith'),87.5],
    'ZWRL': [1,_('Summon Gloom Wraith'),260],
    'ZXIV': [1,_('Summon Xivilai'),200],
    'ZZOM': [1,_('Summon Zombie'),16.67],
    }
mgef_school = dict((x,y) for x,[y,z,a] in magicEffects.items())
mgef_name = dict((x,z) for x,[y,z,a] in magicEffects.items())
mgef_basevalue = dict((x,a) for x,[y,z,a] in magicEffects.items())
mgef_school.update(dict((ctypes.cast(x, ctypes.POINTER(ctypes.c_ulong)).contents.value ,y) for x,[y,z,a] in magicEffects.items()))
mgef_name.update(dict((ctypes.cast(x, ctypes.POINTER(ctypes.c_ulong)).contents.value,z) for x,[y,z,a] in magicEffects.items()))
mgef_basevalue.update(dict((ctypes.cast(x, ctypes.POINTER(ctypes.c_ulong)).contents.value,a) for x,[y,z,a] in magicEffects.items()))

hostileEffects = set((
    'ABAT', #--Absorb Attribute
    'ABFA', #--Absorb Fatigue
    'ABHE', #--Absorb Health
    'ABSK', #--Absorb Skill
    'ABSP', #--Absorb Magicka
    'BRDN', #--Burden
    'DEMO', #--Demoralize
    'DGAT', #--Damage Attribute
    'DGFA', #--Damage Fatigue
    'DGHE', #--Damage Health
    'DGSP', #--Damage Magicka
    'DIAR', #--Disintegrate Armor
    'DIWE', #--Disintegrate Weapon
    'DRAT', #--Drain Attribute
    'DRFA', #--Drain Fatigue
    'DRHE', #--Drain Health
    'DRSK', #--Drain Skill
    'DRSP', #--Drain Magicka
    'FIDG', #--Fire Damage
    'FRDG', #--Frost Damage
    'FRNZ', #--Frenzy
    'PARA', #--Paralyze
    'SHDG', #--Shock Damage
    'SLNC', #--Silence
    'STMA', #--Stunted Magicka
    'STRP', #--Soul Trap
    'SUDG', #--Sun Damage
    'TURN', #--Turn Undead
    'WKDI', #--Weakness to Disease
    'WKFI', #--Weakness to Fire
    'WKFR', #--Weakness to Frost
    'WKMA', #--Weakness to Magic
    'WKNW', #--Weakness to Normal Weapons
    'WKPO', #--Weakness to Poison
    'WKSH', #--Weakness to Shock
    ))
hostileEffects |= set((ctypes.cast(x, ctypes.POINTER(ctypes.c_ulong)).contents.value for x in hostileEffects))

#Doesn't list mgefs that use actor values, but rather mgefs that have a generic name
#Ex: Absorb Attribute becomes Absorb Magicka if the effect's actorValue field contains 9
#    But it is actually using an attribute rather than an actor value
#Ex: Burden uses an actual actor value (encumbrance) but it isn't listed since its name doesn't change
genericAVEffects = set([
    'ABAT', #--Absorb Attribute (Use Attribute)
    'ABSK', #--Absorb Skill (Use Skill)
    'DGAT', #--Damage Attribute (Use Attribute)
    'DRAT', #--Drain Attribute (Use Attribute)
    'DRSK', #--Drain Skill (Use Skill)
    'FOAT', #--Fortify Attribute (Use Attribute)
    'FOSK', #--Fortify Skill (Use Skill)
    'REAT', #--Restore Attribute (Use Attribute)
    ])
genericAVEffects |= set((ctypes.cast(x, ctypes.POINTER(ctypes.c_ulong)).contents.value for x in genericAVEffects))

actorValues = [
    _('Strength'), #--00
    _('Intelligence'),
    _('Willpower'),
    _('Agility'),
    _('Speed'),
    _('Endurance'),
    _('Personality'),
    _('Luck'),
    _('Health'),
    _('Magicka'),

    _('Fatigue'), #--10
    _('Encumbrance'),
    _('Armorer'),
    _('Athletics'),
    _('Blade'),
    _('Block'),
    _('Blunt'),
    _('Hand To Hand'),
    _('Heavy Armor'),
    _('Alchemy'),

    _('Alteration'), #--20
    _('Conjuration'),
    _('Destruction'),
    _('Illusion'),
    _('Mysticism'),
    _('Restoration'),
    _('Acrobatics'),
    _('Light Armor'),
    _('Marksman'),
    _('Mercantile'),

    _('Security'), #--30
    _('Sneak'),
    _('Speechcraft'),
    'Aggression',
    'Confidence',
    'Energy',
    'Responsibility',
    'Bounty',
    'UNKNOWN 38',
    'UNKNOWN 39',

    'MagickaMultiplier', #--40
    'NightEyeBonus',
    'AttackBonus',
    'DefendBonus',
    'CastingPenalty',
    'Blindness',
    'Chameleon',
    'Invisibility',
    'Paralysis',
    'Silence',

    'Confusion', #--50
    'DetectItemRange',
    'SpellAbsorbChance',
    'SpellReflectChance',
    'SwimSpeedMultiplier',
    'WaterBreathing',
    'WaterWalking',
    'StuntedMagicka',
    'DetectLifeRange',
    'ReflectDamage',

    'Telekinesis', #--60
    'ResistFire',
    'ResistFrost',
    'ResistDisease',
    'ResistMagic',
    'ResistNormalWeapons',
    'ResistParalysis',
    'ResistPoison',
    'ResistShock',
    'Vampirism',

    'Darkness', #--70
    'ResistWaterDamage',
    ]

acbs = {
    'Armorer': 0,
    'Athletics': 1,
    'Blade': 2,
    'Block': 3,
    'Blunt': 4,
    'Hand to Hand': 5,
    'Heavy Armor': 6,
    'Alchemy': 7,
    'Alteration': 8,
    'Conjuration': 9,
    'Destruction': 10,
    'Illusion': 11,
    'Mysticism': 12,
    'Restoration': 13,
    'Acrobatics': 14,
    'Light Armor': 15,
    'Marksman': 16,
    'Mercantile': 17,
    'Security': 18,
    'Sneak': 19,
    'Speechcraft': 20,
    'Health': 21,
    'Strength': 25,
    'Intelligence': 26,
    'Willpower': 27,
    'Agility': 28,
    'Speed': 29,
    'Endurance': 30,
    'Personality': 31,
    'Luck': 32,
    }

 # Save File Info --------------------------------------------------------------
saveRecTypes = {
    6 : _('Faction'),
    19: _('Apparatus'),
    20: _('Armor'),
    21: _('Book'),
    22: _('Clothing'),
    25: _('Ingredient'),
    26: _('Light'),
    27: _('Misc. Item'),
    33: _('Weapon'),
    35: _('NPC'),
    36: _('Creature'),
    39: _('Key'),
    40: _('Potion'),
    48: _('Cell'),
    49: _('Object Ref'),
    50: _('NPC Ref'),
    51: _('Creature Ref'),
    58: _('Dialog Entry'),
    59: _('Quest'),
    61: _('AI Package'),
    }

# Alchemical Catalogs ---------------------------------------------------------
ingred_alchem = (
    (1,0xCED,_('Alchemical Ingredients I'),250),
    (2,0xCEC,_('Alchemical Ingredients II'),500),
    (3,0xCEB,_('Alchemical Ingredients III'),1000),
    (4,0xCE7,_('Alchemical Ingredients IV'),2000),
    )
effect_alchem = (
    (1,0xCEA,_('Alchemical Effects I'),500),
    (2,0xCE9,_('Alchemical Effects II'),1000),
    (3,0xCE8,_('Alchemical Effects III'),2000),
    (4,0xCE6,_('Alchemical Effects IV'),4000),
    )

# Power Exhaustion ------------------------------------------------------------
orrery = getIdFunc('DLCOrrery.esp')
id_exhaustion = {
    ob(0x014D23): 9, # AbPilgrimsGrace
    ob(0x022A43): 7, # BSLoverKiss
    ob(0x022A3A): 7, # BSRitualMaraGift
    ob(0x022A63): 7, # BSSerpent
    ob(0x022A66): 7, # BSShadowMoonshadow
    ob(0x022A6C): 7, # BSTower
    ob(0x0CB623): 7, # BSTowerWarden
    ob(0x06B69D): 7, # DoomstoneAetherius
    ob(0x06A8EE): 7, # DoomstoneApprentice
    ob(0x06A8EF): 7, # DoomstoneAtronach
    ob(0x06B6A3): 7, # DoomstoneDragon
    ob(0x06B69F): 7, # DoomstoneJode
    ob(0x06B69E): 7, # DoomstoneJone
    ob(0x06A8F2): 7, # DoomstoneLady
    ob(0x06A8F3): 7, # DoomstoneLord
    ob(0x06A8F5): 7, # DoomstoneLover
    ob(0x06A8ED): 7, # DoomstoneMage
    ob(0x06B6A1): 7, # DoomstoneMagnus
    ob(0x06B6B1): 7, # DoomstoneNirn
    ob(0x06A8EC): 7, # DoomstoneRitualMarasMercy
    ob(0x06A8EB): 7, # DoomstoneRitualMarasMilk
    ob(0x06A8F8): 7, # DoomstoneSerpent
    ob(0x06A8F6): 7, # DoomstoneShadow
    ob(0x06B6A2): 7, # DoomstoneShezarr
    ob(0x06B6A0): 7, # DoomstoneSithian
    ob(0x06A8F1): 7, # DoomstoneSteed
    ob(0x06A8F4): 7, # DoomstoneThief
    ob(0x06A8F7): 7, # DoomstoneTower
    ob(0x008E53): 7, # DoomstoneTowerArmor
    ob(0x06A8F0): 7, # DoomstoneWarrior
    ob(0x047AD0): 7, # PwRaceBretonShield
    ob(0x047AD5): 7, # PwRaceDarkElfGuardian
    ob(0x047ADE): 7, # PwRaceImperialAbsorbFatigue
    ob(0x047ADD): 7, # PwRaceImperialCharm
    ob(0x047ADF): 7, # PwRaceKhajiitDemoralize
    ob(0x047AE4): 7, # PwRaceNordFrostDamage
    ob(0x047AE3): 7, # PwRaceNordShield
    ob(0x047AD3): 7, # PwRaceOrcBerserk
    ob(0x047AE7): 7, # PwRaceRedguardFortify
    ob(0x047AE9): 7, # PwRaceWoodElfCommandCreature
    ob(0x03BEDB): 7, # VampireEmbraceofShadows
    ob(0x03BEDC): 7, # VampireReignofTerror
    ob(0x03BED9): 7, # VampireSeduction
    #--Shivering Isles
    ob(0x08F024): 7, # SE02BlessingDementia
    ob(0x08F023): 7, # SE02BlessingMania
    ob(0x03161E): 5, # SE07SaintSpell
    ob(0x03161D): 5, # SE07SeducerSpell
    ob(0x05DD22): 3, # SE14WeatherSpell
    ob(0x081C35): 7, # SE44Frenzy
    ob(0x018DBD): 6, # SEPwSummonDarkSeducer
    ob(0x014B35): 6, # SEPwSummonFleshAtronach
    ob(0x018DBC): 6, # SEPwSummonGoldenSaint
    ob(0x050C76): 3, # SE09PwGKHead1
    ob(0x050C77): 3, # SE09PwGKHead2
    ob(0x050C78): 3, # SE09PwGKHeart1
    ob(0x050C79): 3, # SE09PwGKHeart2
    ob(0x050C7A): 3, # SE09PwGKLeftArm1
    ob(0x050C7B): 3, # SE09PwGKLeftArm2
    ob(0x050C7C): 3, # SE09PwGKLeftArm3
    ob(0x050C82): 3, # SE09PwGKLegs1
    ob(0x050C83): 3, # SE09PwGKLegs2
    ob(0x050C7D): 3, # SE09PwGKRightArm1
    ob(0x050C7E): 3, # SE09PwGKRightArm2
    ob(0x050C7F): 3, # SE09PwGKRightArm3
    ob(0x050C80): 3, # SE09PwGKTorso1
    ob(0x050C81): 3, # SE09PwGKTorso2
    ob(0x08E93F): 3, # SESuicidePower

    #--Orrery
    orrery(0x11DC5F): 7, # Masser's Might
    orrery(0x11DC60): 7, # Masser's Grace
    orrery(0x11DC62): 7, # Secunda's Will
    orrery(0x11DC64): 7, # Secunda's Opportunity
    orrery(0x11DC66): 7, # Masser's Alacrity
    orrery(0x11DC68): 7, # Secunda's Magnetism
    orrery(0x11DC6A): 7, # Secunda's Brilliance
    orrery(0x11DC6C): 7, # Masser's Courage
    }

# Repair Factions -------------------------------------------------------------
#--Formids for npcs which legitimately have no faction membership
repairFactions_legitNullSpells = set((
    #--MS47 Aleswell Invisibility
    0x0002F85F, #Sakeepa
    0x0002F861, #ShagolgroBumph
    0x0002F864, #DiramSerethi
    0x0002F865, #AdosiSerethi
    0x0002F866, #UrnsiSerethi
    ))

repairFactions_legitNullFactions = set((
    #0x00012106, #SEThadon (Between SE07 and SE12) Safer to leave in.
    #0x00012107, #SESyl (Between SE07 and SE12) Safer to leave in.
    #0x00031540, #Mirisa (Only in Cropsford, but doesn't hurt to leave her in it.)
    ))

repairFactions_legitDroppedFactions = set((
    (0x000034CC,0x000034B9), #UlrichLeland CheydinhalGuardFaction
    (0x000034CC,0x000034BB), #UlrichLeland CheydinhalCastleFaction
    (0x000055C2,0x00090E31), #CheydinhalGuardCastlePostDay01 CheydinhalCorruptGuardsFactionMS10
    (0x000055C4,0x00090E31), #CheydinhalGuardCastlePostNight01 CheydinhalCorruptGuardsFactionMS10
    (0x000055C5,0x00090E31), #CheydinhalGuardCastlePostNight02 CheydinhalCorruptGuardsFactionMS10
    (0x000055C7,0x00090E31), #CheydinhalGuardCityPatrolDay02 CheydinhalCorruptGuardsFactionMS10
    (0x000055C8,0x00090E31), #CheydinhalGuardCityPatrolNight01 CheydinhalCorruptGuardsFactionMS10
    (0x000055C9,0x00090E31), #CheydinhalGuardCityPatrolNight02 CheydinhalCorruptGuardsFactionMS10
    (0x000055CB,0x00090E31), #CheydinhalGuardCityPostDay02 CheydinhalCorruptGuardsFactionMS10
    (0x000055CC,0x00090E31), #CheydinhalGuardCityPostNight01 CheydinhalCorruptGuardsFactionMS10
    (0x000055CD,0x00090E31), #CheydinhalGuardCityPostNight02 CheydinhalCorruptGuardsFactionMS10
    (0x000055D2,0x00090E31), #CheydinhalGuardCastlePatrolDay01 CheydinhalCorruptGuardsFactionMS10
    (0x000055D3,0x00090E31), #CheydinhalGuardCastlePatrolNight01 CheydinhalCorruptGuardsFactionMS10
    (0x000055D4,0x00090E31), #CheydinhalGuardCountEscort CheydinhalCorruptGuardsFactionMS10
    (0x000055D5,0x00090E31), #CheydinhalGuardJailorDay CheydinhalCorruptGuardsFactionMS10
    (0x000055D6,0x00090E31), #CheydinhalGuardJailorNight CheydinhalCorruptGuardsFactionMS10
    (0x0000BD60,0x00091ADB), #Larthjar Prisoners
    (0x00012106,0x0001557F), #SEThadon SENewSheothBliss
    (0x00012106,0x0001AD45), #SEThadon SEManiaFaction
    (0x00012106,0x00056036), #SEThadon SE07ManiaHouseFaction
    (0x00012107,0x00013A69), #SESyl SENewSheothFaction
    (0x00012107,0x00015580), #SESyl SENewSheothCrucible
    (0x00012107,0x0001723D), #SESyl SE07ASylFaction
    (0x00012107,0x0001AD46), #SESyl SEDementiaFaction
    (0x00012107,0x0007E0CB), #SESyl SE07DementiaHouseFaction
    (0x0001CF76,0x00009275), #Seridur ICFaction
    (0x0001CF76,0x000947B9), #Seridur SeridurHouseFaction
    (0x0001CF76,0x000980DD), #Seridur OrderoftheVirtuousBlood
    (0x000222A8,0x00028D98), #ReynaldJemane ChorrolFaction
    (0x00023999,0x00028D98), #Jauffre ChorrolFaction
    (0x00023E86,0x000034B7), #GuilbertJemane NewlandsLodgeFaction
    (0x00023E86,0x000034BA), #GuilbertJemane CheydinhalFaction
    (0x00023F2A,0x0001EE1E), #Baurus BladesCG
    (0x00024165,0x0002228F), #Maglir FightersGuild
    (0x00024E0A,0x000272BE), #Jeelius MythicDawnPrisoner
    (0x00026D9A,0x00009275), #AudensAvidius ICFaction
    (0x00026D9A,0x0003486F), #AudensAvidius ImperialWatch
    (0x00026D9A,0x00083595), #AudensAvidius CourierCustomers
    (0x00026D9A,0x0018B117), #AudensAvidius ImperialLegion
    (0x0002AB4E,0x0002AB4D), #Umbacano UmbacanoFaction
    (0x0002AF3E,0x0002AEFA), #Srazirr ClaudeMaricThugFaction
    (0x0002CD21,0x00022296), #Falcar MagesGuild
    (0x0002D01E,0x00035EA9), #Jskar BrumaFaction
    (0x0002D8C0,0x00022296), #Kalthar MagesGuild
    (0x00032940,0x000C48A1), #MG16NecromancerMale1 MG16FortOntusMageFaction
    (0x00032941,0x000C48A1), #MG16NecromancerFemale2 MG16FortOntusMageFaction
    (0x00032943,0x000C48A1), #MG16NecromancerMale2 MG16FortOntusMageFaction
    (0x00033907,0x0003B3F6), #Martin KvatchFaction
    (0x00033B8B,0x000C48A1), #MG16NecromancerFemale3 MG16FortOntusMageFaction
    (0x00033B8D,0x000C48A1), #MG16NecromancerMale3 MG16FortOntusMageFaction
    (0x0003486E,0x00009275), #HieronymusLex ICFaction
    (0x0003486E,0x0003486F), #HieronymusLex ImperialWatch
    (0x00034E86,0x00029F82), #Cingor MythicDawn
    (0x00034EAD,0x00022296), #Caranya MagesGuild
    (0x0003529A,0x00024164), #MyvrynaArano ThievesGuild
    (0x0003529A,0x0003AB39), #MyvrynaArano ICWaterfrontResident
    (0x0003563B,0x00028E77), #Amusei SkingradFaction
    (0x00035649,0x00028E77), #MercatorHosidus SkingradFaction
    (0x00035649,0x0002A09C), #MercatorHosidus SkingradCastleFaction
    (0x00035ECB,0x00035EA9), #Jearl BrumaFaction
    (0x0003628D,0x00009274), #VelwynBenirus AnvilFaction
    (0x0004EF69,0x00090E31), #CheydinhalGuardCityPostDay03 CheydinhalCorruptGuardsFactionMS10
    (0x0004EFF9,0x00090E31), #CheydinhalGuardCityPostDay04 CheydinhalCorruptGuardsFactionMS10
    (0x0004EFFA,0x00090E31), #CheydinhalGuardCityPostNight04 CheydinhalCorruptGuardsFactionMS10
    ))

# Messages Text ===============================================================
messagesHeader = """<html>
<head>
<meta http-equiv="content-type" content="text/html; charset=iso-8859-1" />
	<title>Private Message Archive</title>
	<style type="text/css">
		html{
			overflow-x: auto;
		}

		body{
			background-color: #fff;
			color: #000;
			font-family: Verdana, Tahoma, Arial, sans-serif;
			font-size: 11px;
			margin:0px;
			padding:0px;
			text-align:center;
			}

		a:link, a:visited, a:active{
			color: #000;
			text-decoration: underline;
		}

		a:hover{
			color: #465584;
			text-decoration:underline;
		}

		img{
			border: 0;
			vertical-align: middle;
		}

		#ipbwrapper{
			margin: 0 auto 0 auto;
			text-align: left;
			width: 95%;
		}

		.post1{
			background-color: #F5F9FD;
		}

		.post2{
			background-color: #EEF2F7;
		}

		/* Common elements */
		.row1{
			background-color: #F5F9FD;
		}

		.row1{
			background-color: #DFE6EF;
		}

		.row3{
			background-color: #EEF2F7;
		}

		.row2{
			background-color: #E4EAF2;
		}

		/* tableborders gives the white column / row lines effect */
		.plainborder{
			background-color: #F5F9FD
			border: 1px solid #345487;
		}

		.tableborder{
			background-color: #FFF;
			border: 1px solid #345487;
			margin: 0;
			padding: 0;
		}

		.tablefill{
			background-color: #F5F9FD;
			border: 1px solid #345487;
			padding: 6px;
		}

		.tablepad{
			background-color: #F5F9FD;
			padding:6px;
		}

		.tablebasic{
			border: 0;
			margin: 0;
			padding: 0;
			width:100%;
		}

		.pformstrip{
			background-color: #D1DCEB;
			color: #3A4F6C;
			font-weight: bold;
			margin-top:1px
			padding:7px;
		}

		#QUOTE{
			background-color: #FAFCFE;
			border: 1px solid #000;
			color: #465584;
			font-family: Verdana, Arial;
			font-size: 11px;
			padding: 2px;
		}

		#CODE{
			background-color: #FAFCFE;
			border: 1px solid #000;
			color: #465584;
			font-family: Courier, Courier New, Verdana, Arial;
			font-size: 11px;
			padding: 2px;
		}
		/* Main table top (dark blue gradient by default) */
		.maintitle{
			background-color: #D1DCEB;
			color: #FFF;
			font-weight: bold;
			padding:8px 0px 8px 5px;
			vertical-align:middle;
		}

		.maintitle a:link, .maintitle  a:visited, .maintitle  a:active{
			color: #fff;
			text-decoration: none;
		}

		.maintitle a:hover{
			text-decoration: underline;
		}

		/* Topic View elements */
		.signature{
			color: #339;
			font-size: 10px;
			line-height:150%;
		}

		.postdetails{
			font-size: 10px;
		}

		.postcolor{
			font-size: 12px;
			line-height: 160%;
		}
		/* Quote/Code formatting */
		.quotetop {
			color: #fff;
			background-color: #B1C9ED;
			margin: 1em;
			margin-bottom: 0;
			padding: 0.5em;
		}

        .quotemain {
            margin: 0 1em;
            padding: 0.5em;
            border: solid 1px #000;
        }

        .codetop {
            font-family: monospace;
            color: #fff;
            background-color: #A0A0A0;
            margin: 1em;
            margin-bottom: 0;
            padding: 0.5em;
        }

        .codemain {
            font-family: monospace;
            margin: 0 1em;
            padding: 0.5em;
            border: solid 1px #000;
        }
    </style>
</head>
<body><div id="ipbwrapper">\n"""
