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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2011 Wrye Bash Team
#
# =============================================================================

"""This modules defines static data for use by bush, when
   TES V: Skyrim is set at the active game."""

import struct
from .. import brec
from .. import bolt
from ..bolt import _encode
from ..brec import *

#--Name of the game
name = u'Skyrim'
altName = u'Wrye Smash'

#--exe to look for to see if this is the right game
exe = u'TESV.exe'

#--Registry keys to read to find the install location
regInstallKeys = [
    (u'Bethesda Softworks\\Skyrim',u'Installed Path'),
    ]

#--patch information
patchURL = u'' # Update via steam
patchTip = u'Update via Steam'

#--URL to the Nexus site for this game
nexusUrl = u'http://www.skyrimnexus.com/'

#--Creation Kit Set information
class cs:
    shortName = u'CK'                # Abbreviated name
    longName = u'Creation Kit'       # Full name
    exe = u'CreationKit.exe'         # Executable to run
    seArgs = u'-editor'              # Argument to pass to the SE to load the CS
    imageName = u'tescs%s.png'       # Image name template for the status bar

#--Script Extender information
class se:
    shortName = u'SKSE'                      # Abbreviated name
    longName = u'Skyrim Script Extender'     # Full name
    exe = u'skse_loader.exe'                 # Exe to run
    steamExe = u'skse_loader.exe'            # Exe to run if a steam install
    url = u'http://skse.silverlock.org/'     # URL to download from
    urlTip = u'http://skse.silverlock.org/'  # Tooltip for mouse over the URL

#--Script Dragon
class sd:
    shortName = u'SD'
    longName = u'Script Dragon'
    installDir = u'asi'

#--Quick shortcut for combining both the SE and SD names
se_sd = se.shortName+u'/'+sd.longName

#--Graphics Extender information
class ge:
    shortName = u''
    longName = u''
    exe = u'**DNE**'
    url = u''
    urlTip = u''

#--4gb Launcher
class laa:
    # Skyrim has a 4gb Launcher, but as of patch 1.3.10, it is
    # no longer required (Bethsoft updated TESV.exe to already
    # be LAA)
    name = u''
    exe = u'**DNE**'
    launchesSE = False

#--Some stuff dealing with INI files
class ini:
    #--True means new lines are allowed to be added via INI Tweaks
    #  (by default)
    allowNewLines = True

    #--INI Entry to enable BSA Redirection
    bsaRedirection = (u'',u'')

#--Save Game format stuff
class ess:
    # Save file capabilities
    canReadBasic = True         # All the basic stuff needed for the Saves Tab
    canEditMasters = True       # Adjusting save file masters
    canEditMore = False         # No advanced editing

    @staticmethod
    def load(ins,header):
        """Extract info from save file."""
        #--Header
        if ins.read(13) != 'TESV_SAVEGAME':
            raise Exception(u'Save file is not a Skyrim save game.')
        headerSize, = struct.unpack('I',ins.read(4))
        #--Name, location
        version,saveNumber,size = struct.unpack('2IH',ins.read(10))
        header.pcName = ins.read(size)
        header.pcLevel, = struct.unpack('I',ins.read(4))
        size, = struct.unpack('H',ins.read(2))
        header.pcLocation = ins.read(size)
        size, = struct.unpack('H',ins.read(2))
        header.gameDate = ins.read(size)
        hours,minutes,seconds = [int(x) for x in header.gameDate.split('.')]
        playSeconds = hours*60*60 + minutes*60 + seconds
        header.gameDays = float(playSeconds)/(24*60*60)
        header.gameTicks = playSeconds * 1000
        size, = struct.unpack('H',ins.read(2))
        ins.seek(ins.tell()+size+2+4+4+8) # raceEdid, unk0, unk1, unk2, ftime
        ssWidth, = struct.unpack('I',ins.read(4))
        ssHeight, = struct.unpack('I',ins.read(4))
        if ins.tell() != headerSize + 17:
            raise Exception(u'Save game header size (%s) not as expected (%s).' % (ins.tell()-17,headerSize))
        #--Image Data
        ssData = ins.read(3*ssWidth*ssHeight)
        header.image = (ssWidth,ssHeight,ssData)
        #--unknown
        unk3 = ins.read(1)
        #--Masters
        mastersSize, = struct.unpack('I',ins.read(4))
        mastersStart = ins.tell()
        del header.masters[:]
        numMasters, = struct.unpack('B',ins.read(1))
        for count in xrange(numMasters):
            size, = struct.unpack('H',ins.read(2))
            header.masters.append(ins.read(size))
        if ins.tell() != mastersStart + mastersSize:
            raise Exception(u'Save game masters size (%i) not as expected (%i).' % (ins.tell()-mastersStart,mastersSize))

    @staticmethod
    def writeMasters(ins,out,header):
        """Rewrites masters of existing save file."""
        def unpack(format,size): return struct.unpack(format,ins.read(size))
        def pack(format,*args): out.write(struct.pack(format,*args))
        #--Magic (TESV_SAVEGAME)
        out.write(ins.read(13))
        #--Header
        size, = unpack('I',4)
        pack('I',size)
        out.write(ins.read(size-8))
        ssWidth,ssHeight = unpack('2I',8)
        pack('2I',ssWidth,ssHeight)
        #--Screenshot
        out.write(ins.read(3*ssWidth*ssHeight))
        #--formVersion
        out.write(ins.read(1))
        #--plugin info
        oldSize, = unpack('I',4)
        newSize = 1 + sum(len(x)+2 for x in header.masters)
        pack('I',newSize)
        #  Skip old masters
        oldMasters = []
        numMasters, = unpack('B',1)
        pack('B',len(header.masters))
        for x in xrange(numMasters):
            size, = unpack('H',2)
            oldMasters.append(ins.read(size))
        #  Write new masters
        for master in header.masters:
            pack('H',len(master))
            out.write(master.s)
        #--Offsets
        offset = out.tell() - ins.tell()
        #--File Location Table
        for i in xrange(6):
            # formIdArrayCount offset, unkownTable3Offset,
            # globalDataTable1Offset, globalDataTable2Offset,
            # changeFormsOffset, globalDataTable3Offset
            oldOffset, = unpack('I',4)
            pack('I',oldOffset+offset)
        #--Copy the rest
        while True:
            buffer = ins.read(0x5000000)
            if not buffer: break
            out.write(buffer)
        return oldMasters

#--INI files that should show up in the INI Edits tab
iniFiles = [
    u'Skyrim.ini',
    u'SkyrimPrefs.ini',
    ]

#--INI setting to setup Save Profiles
saveProfilesKey = (u'General',u'SLocalSavePath')

#--The main plugin file Wrye Bash should look for
masterFiles = [
    u'Skyrim.esm',
    ]

#--Game ESM/ESP/BSA files
bethDataFiles = set((
    #--Vanilla
    u'skyrim.esm',
    u'update.esm',
    u'skyrim - animations.bsa',
    u'skyrim - interface.bsa',
    u'skyrim - meshes.bsa',
    u'skyrim - misc.bsa',
    u'skyrim - shaders.bsa',
    u'skyrim - sounds.bsa',
    u'skyrim - textures.bsa',
    u'skyrim - voices.bsa',
    u'skyrim - voicesextra.bsa',
    ))

#--Every file in the Data directory from Bethsoft
allBethFiles = set((
    #--Vanilla
    u'skyrim.esm',
    u'update.esm',
    u'skyrim - animations.bsa',
    u'skyrim - interface.bsa',
    u'skyrim - meshes.bsa',
    u'skyrim - misc.bsa',
    u'skyrim - shaders.bsa',
    u'skyrim - sounds.bsa',
    u'skyrim - textures.bsa',
    u'skyrim - voices.bsa',
    u'skyrim - voicesextra.bsa',
    u'interface\\translate_english.txt', #--probably need one for each language
    u'strings\\skyrim_english.dlstrings', #--same here
    u'strings\\skyrim_english.ilstrings',
    u'strings\\skryim_english.strings',
    u'strings\\update_english.dlstrings',
    u'strings\\update_english.ilstrings',
    u'strings\\update_english.strings',
    u'video\\bgs_logo.bik',
    ))

#--BAIN: Directories that are OK to install to
dataDirs = set((
    u'bash patches',
    u'interface',
    u'meshes',
    u'strings',
    u'textures',
    u'video',
    u'lodsettings',
    u'grass',
    u'scripts',
    u'shadersfx',
    u'music',
    u'sound',
    ))
dataDirsPlus = set((
    u'ini tweaks',
    u'skse',
    u'ini',
    u'asi',
    ))

# Function Info ----------------------------------------------------------------
conditionFunctionData = ( #--0: no param; 1: int param; 2 formid param
    (  0, 'GetWantBlocking', 0, 0),
    (  1, 'GetDistance', 2, 0),
    (  5, 'GetLocked', 0, 0),
    (  6, 'GetPos', 1, 0),
    (  8, 'GetAngle', 1, 0),
    ( 10, 'GetStartingPos', 1, 0),
    ( 11, 'GetStartingAngle', 1, 0),
    ( 12, 'GetSecondsPassed', 0, 0),
    ( 14, 'GetActorValue', 1, 0),
    ( 18, 'GetCurrentTime', 0, 0),
    ( 24, 'GetScale', 0, 0),
    ( 25, 'IsMoving', 0, 0),
    ( 26, 'IsTurning', 0, 0),
    ( 27, 'GetLineOfSight', 2, 0),
    ( 31, 'GetButtonPressed', 0, 0),
    ( 32, 'GetInSameCell', 2, 0),
    ( 35, 'GetDisabled', 0, 0),
    ( 36, 'MenuMode', 1, 0),
    ( 39, 'GetDisease', 0, 0),
    ( 41, 'GetClothingValue', 0, 0),
    ( 42, 'SameFction', 2, 0),
    ( 43, 'SameRace', 2, 0),
    ( 44, 'SameSex', 2, 0),
    ( 45, 'GetDetected', 2, 0),
    ( 46, 'GetDead', 0, 0),
    ( 47, 'GetItemCount', 2, 0),
    ( 48, 'GetGold', 0, 0),
    ( 49, 'GetSleeping', 0, 0),
    ( 50, 'GetTalkedToPC', 0, 0),
    ( 53, 'GetScriptVariable', 2, 1),
    ( 56, 'GetQuestRunning', 2, 0),
    ( 58, 'GetStage', 2, 0),
    ( 59, 'GetStageDone', 2, 1),
    ( 60, 'GetFactionRankDifference', 2, 2),
    ( 61, 'GetAlarmed', 0, 0),
    ( 62, 'IsRaining', 0, 0),
    ( 63, 'GetAttacked', 0, 0),
    ( 64, 'GetIsCreature', 0, 0),
    ( 65, 'GetLockLevel', 0, 0),
    ( 66, 'GetShouldAttack', 2, 0),
    ( 67, 'GetInCell', 2, 0),
    ( 68, 'GetIsClass', 2, 0),
    ( 69, 'GetIsRace', 2, 0),
    ( 70, 'GetIsSex', 2, 0),
    ( 71, 'GetInFaction', 2, 0),
    ( 72, 'GetIsID', 2, 0),
    ( 73, 'GetFactionRank', 2, 0),
    ( 74, 'GetGlobalValue', 2, 0),
    ( 75, 'IsSnowing', 0, 0),
    ( 77, 'GetRandomPercent', 0, 0),
    ( 79, 'GetQuestVvariable', 2, 1),
    ( 80, 'GetLevel', 0, 0),
    ( 81, 'IsRotating', 0, 0),
    ( 83, 'GetLeveledEncounterValue', 1, 0),
    ( 84, 'GetDeadCount', 2, 0),
    ( 91, 'GetIsAlerted', 0, 0),
    ( 98, 'GetPlayerControlsDisabled', 0, 0),
    ( 99, 'GetHeadingAngle', 2, 0),
    (101, 'IsWeaponMagicOut', 0, 0),
    (102, 'IsTorchOut', 0, 0),
    (103, 'IsShieldOut', 0, 0),
    (105, 'IsActionRef', 2, 0),
    (106, 'IsFacingUp', 0, 0),
    (107, 'GetKnockedState', 0, 0),
    (108, 'GetWeaponAnimType', 0, 0),
    (109, 'IsWeaponSkillType', 1, 0),
    (110, 'GetCurrentAIPackage', 0, 0),
    (111, 'IsWaiting', 0, 0),
    (112, 'IsIdlePlaying', 0, 0),
    (116, 'IsIntimidatedbyPlayer', 0, 0),
    (117, 'IsPlayerInRegion', 2, 0),
    (118, 'GetActorAggroRadiusViolated', 0, 0),
    (119, 'GetCrimeKnown', 1, 2),
    (122, 'GetCrime', 2, 1),
    (123, 'IsGreetingPlayer', 0, 0),
    (125, 'IsGuard', 0, 0),
    (127, 'HasBeenEaten', 0, 0),
    (128, 'GetStaminaPercentage', 0, 0),
    (129, 'GetPCIsClass', 2, 0),
    (130, 'GetPCIsRace', 2, 0),
    (131, 'GetPCIsSex', 2, 0),
    (132, 'GetPCInFaction', 2, 0),
    (133, 'SameFactionAsPC', 0, 0),
    (134, 'SameRaceAsPC', 0, 0),
    (135, 'SameSexAsPC', 0, 0),
    (136, 'GetIsReference', 2, 0),
    (141, 'IsTalking', 0, 0),
    (142, 'GetWalkSpeed', 0, 0),
    (143, 'GetCurrentAIProcedure', 0, 0),
    (144, 'GetTrespassWarningLevel', 0, 0),
    (145, 'IsTresPassing', 0, 0),
    (146, 'IsInMyOwnedCell', 0, 0),
    (147, 'GetWindSpeed', 0, 0),
    (148, 'GetCurrentWeatherPercent', 0, 0),
    (149, 'GetIsCurrentWeather', 2, 0),
    (150, 'IsContinuingPackagePCNear', 0, 0),
    (152, 'GetIsCrimeFaction', 2, 0),
    (153, 'CanHaveFlames', 0, 0),
    (154, 'HasFlames', 0, 0),
    (157, 'GetOpenState', 0, 0),
    (159, 'GetSitting', 0, 0),
    (160, 'GetFurnitureMarkerID', 0, 0),
    (161, 'GetIsCurrentPackage', 2, 0),
    (162, 'IsCurrentFurnitureRef', 2, 0),
    (163, 'IsCurrentFurnitureObj', 2, 0),
    (167, 'GetFactionReaction', 2, 2),
    (170, 'GetDayOfWeek', 0, 0),
    (172, 'GetTalkedToPCParam', 2, 0),
    (175, 'IsPCSleeping', 0, 0),
    (176, 'IsPCAMurderer', 0, 0),
    (180, 'HasSameEditorLocAsRef', 2, 2),
    (181, 'HasSameEditorLocAsRefAlias', 2, 2),
    (182, 'GetEquiped', 2, 0),
    (185, 'IsSwimming', 0, 0),
    (188, 'GetPCSleepHours', 0, 0),
    (190, 'GetAmountSoldStolen', 0, 0),
    (192, 'GetIgnoreCrime', 0, 0),
    (193, 'GetPCExpelled', 2, 0),
    (195, 'GetPCFactionMurder', 2, 0),
    (197, 'GetPCEnemyofFaction', 2, 0),
    (199, 'GetPCFactionAttack', 2, 0),
    (203, 'GetDestroyed', 0, 0),
    (205, 'GetActionRef', 0, 0),
    (206, 'GetSelf', 0, 0),
    (207, 'GetContainer', 0, 0),
    (208, 'GetForceRun', 0, 0),
    (210, 'GetForceSneak', 0, 0),
    (214, 'HasMagicEffect', 2, 0),
    (215, 'GetDefaultOpen', 0, 0),
    (219, 'GetAnimAction', 0, 0),
    (223, 'IsSpellTarget', 2, 0),
    (224, 'GetVATSMode', 0, 0),
    (225, 'GetPersuationNumber', 0, 0),
    (226, 'GetVampireFeed', 0, 0),
    (227, 'GetCannibal', 0, 0),
    (228, 'GetIsClassDefault', 2, 0),
    (229, 'GetClassDefaultMatch', 0, 0),
    (230, 'GetInCellParam', 2, 2),
    (232, 'GetCombatTarget', 0, 0),
    (233, 'GetPackageTarget', 0, 0),
    (235, 'GetVatsTargetHeight', 0, 0),
    (237, 'GetIsGhost', 0, 0),
    (242, 'GetUnconscious', 0, 0),
    (244, 'GetRestrained', 0, 0),
    (246, 'GetIsUsedItem', 2, 0),
    (247, 'GetIsUsedItemType', 2, 0),
    (248, 'IsScenePlaying', 2, 0),
    (249, 'IsInDialogWithPlayer', 0, 0),
    (250, 'GetLocationCleared', 2, 0),
    (254, 'GetIsPlayableRace', 0, 0),
    (255, 'GetOffersServicesNow', 0, 0),
    (256, 'GetGameSetting', 1, 0),
    (258, 'HasAssociationType', 2, 2),
    (259, 'HasFamilyRelationship', 2, 0),
    (261, 'HasParentRelationship', 2, 0),
    (262, 'IsWarningAbout', 2, 0),
    (263, 'IsWeaponOut', 0, 0),
    (264, 'HasSpell', 2, 0),
    (265, 'IsTimePassing', 0, 0),
    (266, 'IsPleasant', 0, 0),
    (267, 'IsCloudy', 0, 0),
    (274, 'IsSmallBump', 0, 0),
    (275, 'GetParentRef', 0, 0),
    (277, 'GetBaseActorValue', 1, 0),
    (278, 'IsOwner', 2, 0),
    (280, 'IsCellOwner', 2, 2),
    (282, 'IsHorseStolen', 0, 0),
    (285, 'IsLeftUp', 0, 0),
    (286, 'IsSneaking', 0, 0),
    (287, 'IsRunning', 0, 0),
    (288, 'GetFriendHit', 0, 0),
    (289, 'IsInCombat', 1, 0),
    (296, 'IsAnimPlaying', 2, 0),
    (300, 'IsInInterior', 0, 0),
    (303, 'IsActorsAIOff', 0, 0),
    (304, 'IsWaterObject', 0, 0),
    (305, 'GetPlayerAction', 0, 0),
    (306, 'IsActorUsingATorch', 0, 0),
    (309, 'IsXBox', 0, 0),
    (310, 'GetInWorldspace', 2, 0),
    (312, 'GetPCMiscStat', 1, 0),
    (313, 'GetPairedAnimation', 0, 0),
    (314, 'IsActorAVictim', 0, 0),
    (315, 'GetTotalPersuationNumber', 0, 0),
    (318, 'GetIdleDoneOnce', 0, 0),
    (320, 'GetNoRumors', 0, 0),
    (323, 'GetCombatState', 0, 0),
    (325, 'GetWithinPackageLocation', 2, 0),
    (327, 'IsRidingHorse', 0, 0),
    (329, 'IsFleeing', 0, 0),
    (332, 'IsInDangerousWater', 0, 0),
    (338, 'GetIgnoreFriendlyHits', 0, 0),
    (339, 'IsPlayersLastRiddenHorse', 0, 0),
    (353, 'IsActor', 0, 0),
    (354, 'IsEssential', 0, 0),
    (358, 'IsPlayerMovingIntoNewSpace', 0, 0),
    (359, 'GetInCurrentLoc', 2, 0),
    (360, 'GetInCurrentLocAlias', 2, 0),
    (361, 'GetTimeDead', 0, 0),
    (362, 'HasLinkedRef', 2, 0),
    (363, 'GetLinkedRef', 2, 0),
    (365, 'IsChild', 0, 0),
    (366, 'GetStolenItemValueNoCrime', 2, 0),
    (367, 'GetLastPlayerAction', 0, 0),
    (368, 'IsPlayerActionActive', 1, 0),
    (370, 'IsTalkingActivatorActor', 2, 0),
    (372, 'IsInList', 2, 0),
    (373, 'GetStolenItemValue', 2, 0),
    (375, 'GetCrimeGoldViolent', 2, 0),
    (376, 'GetCrimeGoldNonviolent', 2, 0),
    (378, 'HasShout', 2, 0),
    (381, 'GetHasNote', 2, 0),
    (387, 'GetObjectiveFailed', 2, 1),
    (390, 'GetHitLocation', 0, 0),
    (391, 'IsPC1stPerson', 0, 0),
    (396, 'GetCauseofDeath', 0, 0),
    (397, 'IsLimbGone', 1, 0),
    (398, 'IsWeaponInList', 2, 0),
    (402, 'IsBribedbyPlayer', 0, 0),
    (403, 'GetRelationshipRank', 2, 0),
    (407, 'GetVATSValue', 1, 1),
    (408, 'IsKiller', 2, 0),
    (409, 'IsKillerObject', 2, 0),
    (410, 'GetFactionCombatReaction', 2, 2),
    (414, 'Exists', 2, 0),
    (415, 'GetGroupMemberCount', 0, 0),
    (416, 'GetGroupTargetCount', 0, 0),
    (419, 'GetObjectiveCompleted', 2, 1),
    (420, 'GetObjectiveDisplayed', 2, 1),
    (425, 'GetIsFormType', 2, 0),
    (426, 'GetIsVoiceType', 2, 0),
    (427, 'GetPlantedExplosive', 0, 0),
    (429, 'IsScenePackageRunning', 0, 0),
    (430, 'GetHealthPercentage', 0, 0),
    (432, 'GetIsObjectType', 2, 0),
    (434, 'GetDialogEmotion', 0, 0),
    (435, 'GetDialogEmotionValue', 0, 0),
    (437, 'GetIsCreatureType', 1, 0),
    (444, 'GetInCurrentLocFormList', 2, 0),
    (445, 'GetInZone', 2, 0),
    (446, 'GetVelocity', 1, 0),
    (447, 'GetGraphVariableFloat', 1, 0),
    (448, 'HasPerk', 2, 0),
    (449, 'GetFactionRelation', 2, 0),
    (450, 'IsLastIdlePlayed', 2, 0),
    (453, 'GetPlayerTeammate', 0, 0),
    (458, 'GetActorCrimePlayerEnemy', 0, 0),
    (459, 'GetCrimeGold', 2, 0),
    (462, 'GetPlayerGrabbedRef', 0, 0),
    (463, 'IsPlayerGrabbedRef', 2, 0),
    (465, 'GetKeywordItemCount', 2, 0),
    (467, 'GetBroadcastState', 0, 0),
    (470, 'GetDestructionStage', 0, 0),
    (473, 'GetIsAlignment', 2, 0),
    (476, 'IsProtected', 0, 0),
    (477, 'GetThreatRatio', 2, 0),
    (479, 'GetIsUsedItemEquipType', 2, 0),
    (480, 'GetPlayerName', 0, 0),
    (487, 'IsCarryable', 0, 0),
    (488, 'GetConcussed', 0, 0),
    (491, 'GetMapMarkerVisible', 0, 0),
    (494, 'GetPermanentActorValue', 1, 0),
    (495, 'GetKillingBlowLimb', 0, 0),
    (497, 'CanPayCrimeGold', 2, 0),
    (499, 'GetDaysInJail', 0, 0),
    (500, 'EPAlchemyGetMakingPoison', 0, 0),
    (501, 'EPAlchemyEffectHasKeyword', 2, 0),
    (503, 'GetAllowWorldInteractions', 0, 0),
    (508, 'GetLastHitCritical', 0, 0),
    (513, 'IsCombatTarget', 2, 0),
    (515, 'GetVATSRightAreaFree', 2, 0),
    (516, 'GetVATSLeftAreaFree', 2, 0),
    (517, 'GetVATSBackAreaFree', 2, 0),
    (518, 'GetVATSFrontAreaFree', 2, 0),
    (519, 'GetIsLockBroken', 0, 0),
    (520, 'IsPS3', 0, 0),
    (521, 'IsWin32', 0, 0),
    (522, 'GetVATSRightTargetVisible', 2, 0),
    (523, 'GetVATSLeftTargetVisible', 2, 0),
    (524, 'GetVATSBackTargetVisible', 2, 0),
    (525, 'GetVATSFrontTargetVisible', 2, 0),
    (528, 'IsInCriticalStage', 2, 0),
    (530, 'GetXPForNextLevel', 0, 0),
    (533, 'GetInfamy', 2, 0),
    (534, 'GetInfamyViolent', 2, 0),
    (535, 'GetInfamyNonViolent', 2, 0),
    (543, 'GetQuestCompleted', 2, 0),
    (547, 'IsGoreDisabled', 0, 0),
    (550, 'IsSceneActionComplete', 2, 1),
    (552, 'GetSpellUsageNum', 2, 0),
    (554, 'GetActorsInHigh', 0, 0),
    (555, 'HasLoaded3D', 0, 0),
    (559, 'IsImageSpaceActive', 2, 0),
    (560, 'HasKeyword', 2, 0),
    (561, 'HasRefType', 2, 0),
    (562, 'LocationHasKeyword', 2, 0),
    (563, 'LocationHasRefType', 2, 0),
    (565, 'GetIsEditorLocation', 2, 0),
    (566, 'GetIsAliasRef', 2, 0),
    (567, 'GetIsEditorLocAlias', 2, 0),
    (568, 'IsSprinting', 0, 0),
    (569, 'IsBlocking', 0, 0),
    (570, 'HasEquippedSpell', 2, 0),
    (571, 'GetCurrentCastingType', 2, 0),
    (572, 'GetCurrentDeliveryType', 2, 0),
    (574, 'GetAttackState', 0, 0),
    (575, 'GetAliasedRef', 2, 0),
    (576, 'GetEventData', 2, 2),
    (577, 'IsCloserToAThanB', 2, 2),
    (579, 'GetEquippedShout', 2, 0),
    (580, 'IsBleedingOut', 0, 0),
    (584, 'GetRelativeAngle', 2, 1),
    (589, 'GetMovementDirection', 0, 0),
    (590, 'IsInScene', 0, 0),
    (591, 'GetRefTypeDeadCount', 2, 2),
    (592, 'GetRefTypeAliveCount', 2, 2),
    (594, 'GetIsFlying', 0, 0),
    (595, 'IsCurrentSpell', 2, 2),
    (596, 'SpellHasKeyword', 2, 2),
    (597, 'GetEquippedItemType', 2, 0),
    (598, 'GetLocationAliasCleared', 2, 0),
    (600, 'GetLocAliasRefTypeDeadCount', 2, 2),
    (601, 'GetLocAliasRefTypeAliveCount', 2, 2),
    (602, 'IsWardState', 2, 0),
    (603, 'IsInSameCurrentLocAsRef', 2, 2),
    (604, 'IsInSameCurrentLocAsRefAlias', 2, 2),
    (605, 'LocAliasIsLocation', 2, 2),
    (606, 'GetKeywordDataForLocation', 2, 2),
    (608, 'GetKeywordDataForAlias', 2, 2),
    (610, 'LocAliasHasKeyword', 2, 2),
    (611, 'IsNullPackageData', 1, 0),
    (612, 'GetNumericPackageData', 1, 0),
    (613, 'IsFurnitureAnimType', 2, 0),
    (614, 'IsFurnitureEntryType', 2, 0),
    (615, 'GetHighestRelationshipRank', 0, 0),
    (616, 'GetLowestRelationshipRank', 0, 0),
    (617, 'HasAssociationTypeAny', 2, 0),
    (618, 'HasFamilyRelationshipAny', 0, 0),
    (619, 'GetPathingTargetOffset', 1, 0),
    (620, 'GetPathingTargetAngleOffset', 1, 0),
    (621, 'GetPathingTargetSpeed', 0, 0),
    (622, 'GetPathingTargetSpeedAngle', 1, 0),
    (623, 'GetMovementSpeed', 0, 0),
    (624, 'GetInContainer', 2, 0),
    (625, 'IsLocationLoaded', 2, 0),
    (626, 'IsLocAliasLoaded', 2, 0),
    (627, 'IsDualCasting', 0, 0),
    (629, 'GetVMQuestVariable', 2, 1),
    (630, 'GetVMScriptVariable', 2, 1),
    (631, 'IsEnteringInteractionQuick', 0, 0),
    (632, 'IsCasting', 0, 0),
    (633, 'GetFlyingState', 0, 0),
    (635, 'IsInFavorState', 0, 0),
    (636, 'HasTwoHandedWeaponEquipped', 0, 0),
    (637, 'IsExitingInstant', 0, 0),
    (638, 'IsInFriendStatewithPlayer', 0, 0),
    (639, 'GetWithinDistance', 2, 1),
    (640, 'GetActorValuePercent', 1, 0),
    (641, 'IsUnique', 0, 0),
    (642, 'GetLastBumpDirection', 0, 0),
    (644, 'IsInFurnitureState', 2, 0),
    (645, 'GetIsInjured', 0, 0),
    (646, 'GetIsCrashLandRequest', 0, 0),
    (647, 'GetIsHastyLandRequest', 0, 0),
    (650, 'IsLinkedTo', 2, 2),
    (651, 'GetKeywordDataForCurrentLocation', 2, 0),
    (652, 'GetInSharedCrimeFaction', 2, 0),
    (653, 'GetBribeAmount', 0, 0),
    (654, 'GetBribeSuccess', 0, 0),
    (655, 'GetIntimidateSuccess', 0, 0),
    (656, 'GetArrestedState', 0, 0),
    (657, 'GetArrestingActor', 0, 0),
    (659, 'EPTemperingItemIsEnchanted', 0, 0),
    (660, 'EPTemperingItemHasKeyword', 2, 0),
    (661, 'GetReceivedGiftValue', 0, 0),
    (662, 'GetGiftGivenValue', 0, 0),
    (664, 'GetReplacedItemType', 2, 0),
    (672, 'IsAttacking', 0, 0),
    (673, 'IsPowerAttacking', 0, 0),
    (674, 'IsLastHostileActor', 0, 0),
    (675, 'GetGraphVariableInt', 1, 0),
    (676, 'GetCurrentShoutVariation', 0, 0),
    (678, 'ShouldAttackKill', 2, 0),
    (680, 'GetActivationHeight', 0, 0),
    (681, 'EPModSkillUsage_IsAdvancedSkill', 1, 0),
    (682, 'WornHasKeyword', 2, 0),
    (683, 'GetPathingCurrentSpeed', 0, 0),
    (684, 'GetPathingCurrentSpeedAngle', 1, 0),
    (691, 'EPModSkillUsage_AdvancedObjectHasKeyword', 2, 0),
    (692, 'EPModSkillUsage_IsAdvancedAction', 2, 0),
    (693, 'EPMagic_SpellHasKeyword', 2, 0),
    (694, 'GetNoBleedoutRecovery', 0, 0),
    (696, 'EPMagic_SpellHasSkill', 1, 0),
    (697, 'IsAttackType', 2, 0),
    (698, 'IsAllowedToFly', 0, 0),
    (699, 'HasMagicEffectKeyword', 2, 0),
    (700, 'IsCommandedActor', 0, 0),
    (701, 'IsStaggered', 0, 0),
    (702, 'IsRecoiling', 0, 0),
    (703, 'IsExitingInteractionQuick', 0, 0),
    (704, 'IsPathing', 0, 0),
    (705, 'GetShouldHelp', 2, 0),
    (706, 'HasBoundWeaponEquipped', 2, 0),
    (707, 'GetCombatTargetHasKeyword', 2, 0),
    (709, 'GetCombatGroupMemberCount', 0, 0),
    (710, 'IsIgnoringCombat', 0, 0),
    (711, 'GetLightLevel', 0, 0),
    (713, 'SpellHasCastingPerk', 2, 0),
    (714, 'IsBeingRidden', 0, 0),
    (715, 'IsUndead', 0, 0),
    (716, 'GetRealHoursPassed', 0, 0),
    (718, 'IsUnlockedDoor', 0, 0),
    (719, 'IsHostileToActor', 2, 0),
    (720, 'GetTargetHeight', 0, 0),
    (721, 'IsPoison', 0, 0),
    (722, 'WornApparelHasKeywordCount', 2, 0),
    (723, 'GetItemHealthPercent', 0, 0),
    (724, 'EffectWasDualCast', 0, 0),
    (725, 'GetKnockStateEnum', 0, 0),
    )
allConditions = set(entry[0] for entry in conditionFunctionData)
fid1Conditions = set(entry[0] for entry in conditionFunctionData if entry[2] == 2)
fid2Conditions = set(entry[0] for entry in conditionFunctionData if entry[3] == 2)

#--List of GMST's in the main plugin (Skyrim.esm) that have 0x00000000
#  as the form id.  Any GMST as such needs it Editor Id listed here.
gmstEids = [
    # None
    ]

#--Tags supported by this game
allTags = sorted((u'Relev',u'Delev',u'Filter',u'NoMerge',u'Deactivate'))

#--Patchers available when building a Bashed Patch
patchers = (
    u'AliasesPatcher', u'PatchMerger', u'ListsMerger',
    )

# For ListsMerger
listTypes = ('LVLI','LVLN','LVSP',)

#--CBash patchers available when building a Bashed Patch
CBash_patchers = tuple()

#--Plugin format stuff
class esp:
    #--Wrye Bash capabilities
    canBash = True         # No Bashed Patch creation
    canCBash = False        # CBash cannot handle this game's records
    canEditHeader = True    # Can edit anything in the TES4 record

    #--Valid ESM/ESP header versions
    validHeaderVersions = (0.94,)

    #--Strings Files
    stringsFiles = [
        ('mods',(u'Strings',),u'%(body)s_%(language)s.STRINGS'),
        ('mods',(u'Strings',),u'%(body)s_%(language)s.DLSTRINGS'),
        ('mods',(u'Strings',),u'%(body)s_%(language)s.ILSTRINGS'),
        ]

    #--Top types in Skyrim order.
    topTypes = ['GMST', 'KYWD', 'LCRT', 'AACT', 'TXST', 'GLOB', 'CLAS', 'FACT', 'HDPT',
        'HAIR', 'EYES', 'RACE', 'SOUN', 'ASPC', 'MGEF', 'SCPT', 'LTEX', 'ENCH', 'SPEL',
        'SCRL', 'ACTI', 'TACT', 'ARMO', 'BOOK', 'CONT', 'DOOR', 'INGR', 'LIGH', 'MISC',
        'APPA', 'STAT', 'SCOL', 'MSTT', 'PWAT', 'GRAS', 'TREE', 'CLDC', 'FLOR', 'FURN',
        'WEAP', 'AMMO', 'NPC_', 'LVLN', 'KEYM', 'ALCH', 'IDLM', 'COBJ', 'PROJ', 'HAZD',
        'SLGM', 'LVLI', 'WTHR', 'CLMT', 'SPGD', 'RFCT', 'REGN', 'NAVI', 'CELL', 'WRLD',
        'DIAL', 'QUST', 'IDLE', 'PACK', 'CSTY', 'LSCR', 'LVSP', 'ANIO', 'WATR', 'EFSH',
        'EXPL', 'DEBR', 'IMGS', 'IMAD', 'FLST', 'PERK', 'BPTD', 'ADDN', 'AVIF', 'CAMS',
        'CPTH', 'VTYP', 'MATT', 'IPCT', 'IPDS', 'ARMA', 'ECZN', 'LCTN', 'MESG', 'RGDL',
        'DOBJ', 'LGTM', 'MUSC', 'FSTP', 'FSTS', 'SMBN', 'SMQN', 'SMEN', 'DLBR', 'MUST',
        'DLVW', 'WOOP', 'SHOU', 'EQUP', 'RELA', 'SCEN', 'ASTP', 'OTFT', 'ARTO', 'MATO',
        'MOVT', 'SNDR', 'DUAL', 'SNCT', 'SOPM', 'COLL', 'CLFM', 'REVB',]

    #--Dict mapping 'ignored' top types to un-ignored top types.
    topIgTypes = dict([(struct.pack('I',(struct.unpack('I',type)[0]) | 0x1000),type) for type in topTypes])

    #-> this needs updating for Skyrim
    recordTypes = set(topTypes + 'GRUP,TES4,ROAD,REFR,ACHR,ACRE,PGRD,LAND,INFO'.split(','))

#--Mod I/O
class RecordHeader(brec.BaseRecordHeader):
    size = 24

    def __init__(self,recType='TES4',size=0,arg1=0,arg2=0,arg3=0,extra=0):
        self.recType = recType
        self.size = size
        if recType == 'GRUP':
            self.label = arg1
            self.groupType = arg2
            self.stamp = arg3
        else:
            self.flags1 = arg1
            self.fid = arg2
            self.flags2 = arg3
        self.extra = extra

    @staticmethod
    def unpack(ins):
        """Returns a RecordHeader object by reading the niput stream."""
        type,size,uint0,uint1,uint2,uint3 = ins.unpack('=4s5I',24,'REC_HEADER')
        #--Bad type?
        if type not in esp.recordTypes:
            raise brec.ModError(ins.inName,u'Bad header type: '+type)
        #--Record
        if type != 'GRUP':
            pass
        #--Top Group
        elif uint1 == 0: #groupType == 0 (Top Type)
            str0 = struct.pack('I',uint0)
            if str0 in esp.topTypes:
                uint0 = str0
            elif str0 in esp.topIgTypes:
                uint0 = esp.topIgTypes[str0]
            else:
                raise brec.ModError(ins.inName,u'Bad Top GRUP type: '+str0)
        #--Other groups
        return RecordHeader(type,size,uint0,uint1,uint2,uint3)

    def pack(self):
        """Return the record header packed into a bitstream to be written to file."""
        if self.recType == 'GRUP':
            if isinstance(self.label,str):
                return struct.pack('=4sI4sIII',self.recType,self.size,
                                   self.label,self.groupType,self.stamp,
                                   self.extra)
            elif isinstance(self.label,tuple):
                return struct.pack('=4sIhhIII',self.recType,self.size,
                                   self.label[0],self.label[1],self.groupType,
                                   self.stamp,self.extra)
            else:
                return struct.pack('=4s5I',self.recType,self.size,self.label,
                                   self.groupType,self.stamp,self.extra)
        else:
            return struct.pack('=4s5I',self.recType,self.size,self.flags1,
                               self.fid,self.flags2,self.extra)

# Record Elements --------------------------------------------------------------
#-------------------------------------------------------------------------------
class MelVmad(MelBase):
    """Virtual Machine data (VMAD)"""
    class Vmad(object):
        __slots__ = ('version','unk','scripts',)
        def __init__(self):
            self.version = 5
            self.unk = 2
            self.scripts = {}
    class Script(object):
        __slots__ = ('unk','properties')
        def __init__(self):
            self.unk = 0
            self.properties = {}
    class Property(object):
        __slots__ = ('type','unk','value')
        def __init__(self):
            self.type = 1
            self.unk = 1
            self.value = 0

    def __init__(self,type='VMAD',attr='vmdata'):
        MelBase.__init__(self,type,attr)

    def hasFids(self,formElements):
        """Include self if has fids."""
        formElements.add(self)

    def setDefault(self,record):
        record.__setattr__(self.attr,None)

    def getDefault(self):
        target = MelObject()
        return self.setDefault(target)

    def loadData(self,record,ins,type,size,readId):
        vmad = MelVmad.Vmad()
        # Header
        vmad.version,vmad.unk,scriptCount = ins.unpack('=3H',6,readId)
        # Scripts
        for x in xrange(scriptCount):
            script = MelVmad.Script()
            scriptName = ins.readString16(size,readId)
            script.unk,propertyCount = ins.unpack('=BH',3,readId)
            # Properties
            props = script.properties
            for y in xrange(propertyCount):
                prop = MelVmad.Property()
                propName = ins.readString16(size,readId)
                type,prop.unk = ins.unpack('=2B',2,readId)
                prop.type = type
                if type == 1:
                    # Object reference? (uint64?)
                    value = ins.unpack('=HHI',8,readId) # unk,unk,fid
                elif type == 2:
                    # String
                    value = ins.readString16(size,readId)
                elif type == 3:
                    # int32
                    value, = ins.unpack('i',4,readId)
                elif type == 4:
                    # float
                    value, = ins.unpack('f',4,readId)
                elif type == 5:
                    # bool (int8)
                    value, = ins.unpack('b',1,readId)
                elif type == 11:
                    # array of object refs? (uint64s?)
                    count, = ins.unpack('I',4,readId)
                    value = list(ins.unpack(`count`+'Q',count*8,readId))
                elif type == 12:
                    # array of strings
                    count, = ins.unpack('I',4,readId)
                    value = [ins.readString16(size,readId) for z in xrange(count)]
                elif type == 13:
                    # array of int32's
                    count, = ins.unpack('I',4,readId)
                    value = list(ins.unpack(`count`+'i',count*4,readId))
                elif type == 14:
                    # array of float's
                    count, = ins.unpack('I',4,readId)
                    value = list(ins.unpack(`count`+'f',count*4,readId))
                elif type == 15:
                    # array of bools's (int8's)
                    count, = ins.unpack('I',4,readId)
                    value = list(ins.unpack(`count`+'b',count*1,readId))
                else:
                    raise Exception(u'Unrecognized VM Data property type: %i' % type)
                prop.value = value
                props[propName] = prop
            vmad.scripts[scriptName] = script
        record.__setattr__(self.attr,vmad)

    def dumpData(self,record,out):
        """Dumps data from record to outstream"""
        vmad = record.__getattribute__(self.attr)
        if vmad is None: return
        structPack = struct.pack
        def packString(string):
            string = _encode(string)
            return structPack('H',len(string))+string
        # Header
        data = structPack('3h',vmad.version,vmad.unk,len(vmad.scripts))
        # Scripts
        for scriptName,script in vmad.scripts.iteritems():
            data += packString(scriptName)
            data += structPack('=BH',script.unk,len(script.properties))
            # Properties
            for propName,prop in script.properties.iteritems():
                data += packString(propName)
                type = prop.type
                data += structPack('2B',type,prop.unk)
                if type == 1:
                    # Object reference
                    data += structPack('=HHI',*prop.value)
                elif type == 2:
                    # String
                    data += packString(prop.value)
                elif type == 3:
                    # int32
                    data += structPack('i',prop.value)
                elif type == 4:
                    # float
                    data += structPack('f',prop.value)
                elif type == 5:
                    # bool (int8)
                    data += structPack('b',prop.value)
                elif type == 11:
                    # array of object references
                    num = len(prop.value)
                    data += structPack('=I'+`num`+'Q',num,*prop.value)
                elif type == 12:
                    # array of strings
                    num = len(prop.value)
                    data += structPack('I',num)
                    for string in prop.value:
                        data += packString(string)
                elif type == 13:
                    # array of int32's
                    num = len(prop.value)
                    data += structPack('=I'+`num`+'i',num,*prop.value)
                elif type == 14:
                    # array of float's
                    num = len(prop.value)
                    data += structPack('=I'+`num`+'f',num,*prop.value)
                elif type == 15:
                    # array of bools (int8)
                    num = len(prop.value)
                    data += structPack('=I'+`num`+'b',num,*prop.value)
        out.packSub(self.subType,data)

    def mapFids(self,record,function,save=False):
        """Applies function to fids.  If save s true, then fid is set
           to result of function."""
        attr = self.attr
        vmad = record.__getattribute__(attr)
        if vmad is None: return
        for scriptName,script in vmad.scripts.iteritems():
            for propName,prop in script.properties.iteritems():
                if prop.type == 0:
                    value = prop.value
                    value = (value[0],value[1],function(value[2]))
                    if save:
                        prop.value = value

#-------------------------------------------------------------------------------
class MelBounds(MelStruct):
    def __init__(self):
        MelStruct.__init__(self,'OBND','=6h',
            'x1','y1','z1',
            'x2','y2','z2')

#-------------------------------------------------------------------------------
class MelKeywords(MelFidList):
    """Handle writing out the KSIZ subrecord for the KWDA subrecord"""
    def dumpData(self,record,out):
        keywords = record.__getattribute__(self.attr)
        if keywords:
            # Only write the KSIZ/KWDA subrecords if count > 0
            out.packSub('KSIZ','I',len(keywords))
            MelFidList.dumpData(self,record,out)

#-------------------------------------------------------------------------------
class MelComponents(MelStructs):
    """Handle writing COCT subrecord for the CNTO subrecord"""
    def dumpData(self,record,out):
        components = record.__getattribute__(self.attr)
        if components:
            # Only write the COCT/CNTO subrecords if count > 0
            out.packSub('COCT','I',len(components))
            MelStructs.dumpData(self,record,out)

#------------------------------------------------------------------------------
class MelString16(MelString):
    """Represents a mod record string element."""
    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        strLen = ins.unpack('H',2,readId)
        value = ins.readString(strLen,readId)
        record.__setattr__(self.attr,value)
        if self._debug: print u' ',record.__getattribute__(self.attr)

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        value = record.__getattribute__(self.attr)
        if value != None:
            if self.maxSize:
                value = bolt.winNewLines(value.rstrip())
                size = min(self.maxSize,len(value))
                test,encoding = _encode(value,returnEncoding=True)
                extra_encoded = len(test) - self.maxSize
                if extra_encoded > 0:
                    total = 0
                    i = -1
                    while total < extra_encoded:
                        total += len(value[i].encode(encoding))
                        i -= 1
                    size += i + 1
                    value = value[:size]
                    value = _encode(value,firstEncoding=encoding)
                else:
                    value = test
            else:
                value = _encode(value)
            value = struct.pack('H',len(value))+value
            out.packSub0(self.subType,value)

#-------------------------------------------------------------------------------
class MelString32(MelString):
    """Represents a mod record string element."""
    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        strLen = ins.unpack('I',4,readId)
        value = ins.readString(strLen,readId)
        record.__setattr__(self.attr,value)
        if self._debug: print u' ',record.__getattribute__(self.attr)

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        value = record.__getattribute__(self.attr)
        if value != None:
            if self.maxSize:
                value = bolt.winNewLines(value.rstrip())
                size = min(self.maxSize,len(value))
                test,encoding = _encode(value,returnEncoding=True)
                extra_encoded = len(test) - self.maxSize
                if extra_encoded > 0:
                    total = 0
                    i = -1
                    while total < extra_encoded:
                        total += len(value[i].encode(encoding))
                        i -= 1
                    size += i + 1
                    value = value[:size]
                    value = _encode(value,firstEncoding=encoding)
                else:
                    value = test
            else:
                value = _encode(value)
            value = struct.pack('I',len(value))+value
            out.packSub0(self.subType,value)

#-------------------------------------------------------------------------------
class MelMODS(MelBase):
    """MODS/MO2S/etc/DMDS subrecord"""
    def hasFids(self,formElements):
        """Include self if has fids."""
        formElements.add(self)

    def setDefault(self,record):
        """Sets default value for record instance."""
        record.__setattr__(self.attr,None)

    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        insUnpack = ins.unpack
        insRead32 = ins.readString32
        count, = insUnpack('I',4,readId)
        data = []
        dataAppend = data.append
        for x in xrange(count):
            string = ins.readString32(size,readId)
            fid = ins.unpackRef(readId)
            unk, = ins.unpack('I',4,readId)
            dataAppend((string,fid,unk))
        record.__setattr__(self.attr,data)

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        data = record.__getattribute__(self.attr)
        if data is not None:
            structPack = struct.pack
            data = record.__getattribute__(self.attr)
            outData = structPack('I',len(data))
            for (string,fid,unk) in data:
                outData += structPack('I',len(string))
                outData += _encode(string)
                outData += structPack('=2I',fid,unk)
            out.packSub(self.subType,outData)

    def mapFids(self,record,function,save=False):
        """Applies function to fids.  If save is true, then fid is set
           to result of function."""
        attr = self.attr
        data = record.__getattribute__(attr)
        if data is not None:
            data = [(string,function(fid),unk) for (string,fid,unk) in record.__getattribute__(attr)]
            if save: record.__setattr__(attr,data)

#-------------------------------------------------------------------------------
class MelBODT(MelStruct):
    """Body Type data"""
    btFlags = bolt.Flags(0L,bolt.Flags.getNames(
        (0, 'skin'),
        (1, 'head'),
        (2, 'chest'),
        (3, 'hands'),
        (4, 'beard'),
        (5, 'amulet'),
        (6, 'ring'),
        (7, 'feet'),
        #8 = unk
        (9, 'shield'),
        (10,'animal_skin'),
        (11,'underskin'),
        (12,'crown'),
        (13,'face'),
        (14,'dragon_head'),
        (15,'dragon_lwing'),
        (16,'dragon_rwing'),
        (17,'dragon_body'),
        ))
    otherFlags = bolt.Flags(0L,bolt.Flags.getNames(
        (4,'notPlayable'),
        ))
    armorTypes = {
        0:'Light Armor',
        1:'Heavy Armor',
        2:'Clothing',
        }
    def __init__(self,type='BODT'):
        MelStruct.__init__(self,type,'=3I',
                           (MelBODT.btFlags,'bodyFlags',0L),
                           (MelBODT.otherFlags,'otherFlags',0L),
                           ('armorType',0)
                           )

    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        if size == 8:
            # Version 20 of this subrecord type was only 8 bytes - omits 'armorType'
            unpacked = ins.unpack('=2I',size,readId) + (0,)
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if action: value = action(value)
                setter(attr,value)
            if self._debug:
                print u' ',zip(self.attrs,unpacked)
                if len(unpacked) != len(self.attrs):
                    print u' ',unpacked
        elif size != 12:
            raise ModSizeError(ins.inName,readId,12,size,True)
        else:
            MelStruct.loadData(self,record,ins,type,size,readId)

#-------------------------------------------------------------------------------
class MelModel(MelGroup):
    """Represents a model record."""
    typeSets = {
        'MODL': ('MODL','MODT','MODS'),
        'MOD2': ('MOD2','MO2T','MO2S'),
        'MOD3': ('MOD3','MO3T','MO3S'),
        'MOD4': ('MOD4','MO4T','MO4S'),
        'MOD5': ('MOD5','MO5T','MO5S'),
        'DMDL': ('DMDL','DMDT','DMDS'),
        }
    def __init__(self,attr='model',type='MODL'):
        """Initialize."""
        types = self.__class__.typeSets[type]
        MelGroup.__init__(self,attr,
            MelString(types[0],'modPath'),
            MelBase(types[1],'modt_p'),
            MelMODS(types[2],'mod_s'),
            )

    def debug(self,on=True):
        """Sets debug flag on self."""
        for element in self.elements[:2]: element.debug(on)
        return self

#-------------------------------------------------------------------------------
class MelConditions(MelStructs):
    """Represents a set of quest/dialog/etc conditions. Difficulty is that FID
    state of parameters depends on function index."""
    def __init__(self):
        """Initialize."""
        MelStructs.__init__(self,'CTDA','=B3sfH2sii4sII','conditions',
            'operFlag',('unused1',null3),'compValue',
            'ifunc',('unused2',null2),'param1','param2',
            ('unused3',null4),'reference','unknown')

    def getDefault(self):
        """Returns a default copy of object."""
        target = MelStructs.getDefault(self)
        target.form12 = 'ii'
        return target

    def hasFids(self,formElements):
        """Include self if has fids."""
        formElements.add(self)

    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        target = MelObject()
        record.conditions.append(target)
        target.__slots__ = self.attrs
        unpacked1 = ins.unpack('=B3sfH2s',12,readId)
        (target.operFlag,target.unused1,target.compValue,ifunc,target.unused2) = unpacked1
        #--Get parameters
        if ifunc not in allConditions:
            raise bolt.BoltError(u'Unknown condition function: %d\nparam1: %08X\nparam2: %08X' % (ifunc,ins.unpackRef(), ins.unpackRef()))
        form1 = 'I' if ifunc in fid1Conditions else 'i'
        form2 = 'I' if ifunc in fid2Conditions else 'i'
        form12 = form1+form2
        unpacked2 = ins.unpack(form12,8,readId)
        (target.param1,target.param2) = unpacked2
        target.unused3,target.reference,target.unused4 = ins.unpack('=4s2I',12,readId)
        (target.ifunc,target.form12) = (ifunc,form12)
        if self._debug:
            unpacked = unpacked1+unpacked2
            print u' ',zip(self.attrs,unpacked)
            if len(unpacked) != len(self.attrs):
                print u' ',unpacked

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        for target in record.conditions:
            ##format = 'B3sfI'+target.form12+'4s'
            out.packSub('CTDA','=B3sfH2s'+target.form12+'4s2I',
                target.operFlag, target.unused1, target.compValue,
                target.ifunc, target.unused2, target.param1,
                target.param2, target.unused3, target.reference, target.unused4)

    def mapFids(self,record,function,save=False):
        """Applies function to fids. If save is true, then fid is set
        to result of function."""
        for target in record.conditions:
            form12 = target.form12
            if form12[0] == 'I':
                result = function(target.param1)
                if save: target.param1 = result
            if form12[1] == 'I':
                result = function(target.param2)
                if save: target.param2 = result
            if target.reference:
                result = function(target.reference)
                if save: target.reference = result

# Skyrim Records ---------------------------------------------------------------
#-------------------------------------------------------------------------------
class MreHeader(MreHeaderBase):
    """TES4 Record.  File header."""
    classType = 'TES4'

    #--Data elements
    melSet = MelSet(
        MelStruct('HEDR','f2I',('version',0.94),'numRecords',('nextObject',0xCE6)),
        MelUnicode('CNAM','author',u'',512),
        MelUnicode('SNAM','description',u'',512),
        MreHeaderBase.MelMasterName('MAST','masters'),
        MelNull('DATA'),
        MelBase('INTV','ingv_p'),
        MelFidList('ONAM','overrides'),
        )
    __slots__ = MreHeaderBase.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAact(MelRecord):
    """Action record."""
    classType = 'AACT'
    melSet = MelSet(
        MelString('EDID','eid'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreActi(MelRecord):
    """Activator."""
    classType = 'ACTI'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel(),
        MelBase('DEST','dest_p'),
        MelGroups('destructionData',
            MelBase('DSTD','dstd_p'),
            MelModel('model','DMDL'),
            ),
        MelBase('DSTF','dstf_p'), # Appears just to signal the end of the destruction data
        MelBase('PNAM','pnam_p'),
        MelOptStruct('VNAM','I',(FID,'pickupSound')),
        MelOptStruct('SNAM','I',(FID,'dropSound')),
        MelOptStruct('WNAM','I',(FID,'water')),
        MelNull('KSIZ'), # Handled by MelKeywords
        MelKeywords('KWDA','keywords'),
        MelLString('RNAM','rnam'),
        MelBase('FNAM','fnam_p'),
        MelOptStruct('KNAM','I',(FID,'keyword')),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAddn(MelRecord):
    """Addon"""
    classType = 'ADDN'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelModel(),
        MelBase('DATA','data_p'),
        MelBase('DNAM','flags'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArma(MelRecord):
    """Armor addon?"""
    classType = 'ARMA'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelBODT(),
        MelFid('RNAM','race'),
        MelBase('DNAM','dnam_p'),
        MelModel('male_model','MOD2'),
        MelModel('female_model','MOD3'),
        MelModel('male_model_1st','MOD4'),
        MelModel('female_model_1st','MOD5'),
        MelFids('MODL','races'),
        MelOptStruct('SNDD','I',(FID,'foodSound')),
        MelOptStruct('NAM0','I',(FID,'skin0')),
        MelOptStruct('NAM1','I',(FID,'skin1')),
        MelOptStruct('NAM2','I',(FID,'skin2')),
        MelOptStruct('NAM3','I',(FID,'skin3')),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArmo(MelRecord):
    """Armor"""
    classType = 'ARMO'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelLString('FULL','full'),
        MelOptStruct('EITM','I',(FID,'enchantment')),
        MelModel('model1','MOD2'),
        MelModel('model3','MOD4'),
        MelBODT(),
        MelOptStruct('ETYP','I',(FID,'equipType')),
        MelOptStruct('BIDS','I',(FID,'bashImpact')),
        MelOptStruct('BAMT','I',(FID,'material')),
        MelOptStruct('YNAM','I',(FID,'pickupSound')),
        MelOptStruct('ZNAM','I',(FID,'dropSound')),
        MelOptStruct('RNAM','I',(FID,'race')),
        MelNull('KSIZ'),
        MelKeywords('KWDA','keywords'),
        MelLString('DESC','description'),
        MelFids('MODL','addons'),
        MelStruct('DATA','=If','value','weight'),
        MelFid('TNAM','baseItem'),
        MelStruct('DNAM','I','armorRating'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAmmo(MelRecord):
    """Ammo record (arrows)"""
    classType = 'AMMO'
    # TODO: verify these flags for Skyrim
    _flags = bolt.Flags(0L,bolt.Flags.getNames('notNormalWeapon'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelLString('DESC','description'),
        MelNull('KSIZ'),
        MelKeywords('KWDA','keywords'),
        MelStruct('DATA','fIff','speed',(_flags,'flags',0L),'damage','weight'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAnio(MelRecord):
    """Anio record (Animated Object)"""
    classType = 'ANIO'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelString('BNAM','unk'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAppa(MelRecord):
    """Appa record (Alchemical Apparatus)"""
    classType = 'APPA'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelLString('FULL','full'),
        MelStruct('QUAL','I','quality'),
        MelLString('DESC','description'),
        MelBase('DATA','data_p'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArto(MelRecord):
    """Arto record (Art effect object)"""
    classType = 'ARTO'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelModel(),
        MelStruct('DNAM','I','flags'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAspc(MelRecord):
    """Aspc record (Acoustic Space)"""
    classType = 'ASPC'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelOptStruct('SNAM','I',(FID,'ambientSound')),
        MelOptStruct('RDAT','I',(FID,'regionData')),
        MelOptStruct('BNAM','I',(FID,'reverb')),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAstp(MelRecord):
    """Astp record (Association type)"""
    classType = 'ASTP'
    _flags = bolt.Flags(0L,bolt.Flags.getNames('related'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('MPRT','maleParent'),
        MelString('FPRT','femaleParent'),
        MelString('MCHT','maleChild'),
        MelString('FCHT','femaleChild'),
        MelStruct('DATA','I',(_flags,'flags',0L)),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCobj(MelRecord):
    """Constructible Object record (recipies)"""
    classType = 'COBJ'
    isKeyedByEid = True # NULL fids are acceptible
    melSet = MelSet(
        MelString('EDID','eid'),
        MelNull('COCT'), # Handled by MelComponents
        MelComponents('CNTO','=2I','components',(FID,'item',None),'count'),
        MelConditions(),
        MelFid('CNAM','resultingItem'),
        MelStruct('NAM1','H','resultingQuantity'),
        MelFid('BNAM','craftingStation'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreGmst(MreGmstBase):
    """Skyrim GMST record"""
    Master = u'Skyrim'
    isKeyedByEid = True # NULL fids are acceptable.

#------------------------------------------------------------------------------
class MreLeveledList(MreLeveledListBase):
    """Skryim Leveled item/creature/spell list."""

    class MelLevListLvlo(MelGroups):
        def __init__(self):
            MelGroups.__init__(self,'entries',
                MelStruct('LVLO','=3I','level',(FID,'listId',None),('count',1)),
                MelOptStruct('COED','=IQ',(FID,'owner'),'coed_unk'),
                )
        def dumpData(self,record,out):
            out.packSub('LLCT','B',len(record.entries))
            MelGroups.dumpData(self,record,out)

    __slots__ = MreLeveledListBase.__slots__

#------------------------------------------------------------------------------
class MreLvli(MreLeveledList):
    classType = 'LVLI'
    copyAttrs = ('chanceNone','glob',)

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelStruct('LVLD','B','chanceNone'),
        MelStruct('LVLF','B',(MreLeveledListBase._flags,'flags',0L)),
        MelNull('LLCT'),
        MreLeveledList.MelLevListLvlo(),
        MelOptStruct('LVLG','I',(FID,'glob')),
        )
    __slots__ = MreLeveledList.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLvln(MreLeveledList):
    classType = 'LVLN'
    copyAttrs = ('chanceNone','model','modt_p',)

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelStruct('LVLD','B','chanceNone'),
        MelStruct('LVLF','B',(MreLeveledListBase._flags,'flags',0L)),
        MelNull('LLCT'),
        MreLeveledList.MelLevListLvlo(),
        MelString('MODL','model'),
        MelBase('MODT','modt_p'),
        )
    __slots__ = MreLeveledList.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLvsp(MreLeveledList):
    classType = 'LVSP'
    copyAttrs = ('chanceNone',)

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelStruct('LVLD','B','chanceNone'),
        MelStruct('LVLF','B',(MreLeveledListBase._flags,'flags',0L)),
        MelNull('LLCT'),
        MreLeveledList.MelLevListLvlo(),
        )
    __slots__ = MreLeveledList.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMisc(MelRecord):
    """Misc. Item"""
    classType = 'MISC'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelLString('FULL','full'),
        MelString('ICON','icon'),
        MelModel(),
        MelNull('KSIZ'),
        MelKeywords('KWDA','keywords'),
        MelStruct('DATA','=If','value','weight'),
        MelOptStruct('YNAM','I',(FID,'pickupSound')),
        MelOptStruct('ZNAM','I',(FID,'dropSound')),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------

#--Mergeable record types
mergeClasses = (
    MreAact, MreActi, MreAmmo, MreAnio, MreAppa, MreArma, MreArmo, MreArto,
    MreAspc, MreAstp, MreCobj, MreGlob, MreGmst, MreLvli, MreLvln, MreLvsp,
    MreMisc,
    )

#--Extra read/write classes
readClasses = ()
writeClasses = ()

def init():
    # Due to a bug with py2exe, 'reload' doesn't function properly.  Instead of
    # re-executing all lines within the module, it acts like another 'import'
    # statement - in otherwords, nothing happens.  This means any lines that
    # affect outside modules must do so withing this function, which will be
    # called instead of 'reload'
    brec.ModReader.recHeader = RecordHeader

    #--Record Types
    brec.MreRecord.type_class = dict((x.classType,x) for x in (
        MreAact, MreActi, MreAddn, MreAmmo, MreAnio, MreAppa, MreArma, MreArmo,
        MreArto, MreAspc, MreAstp, MreCobj, MreGlob, MreGmst, MreLvli, MreLvln,
        MreLvsp, MreMisc,
        MreHeader,
        ))

    #--Simple records
    brec.MreRecord.simpleTypes = (set(brec.MreRecord.type_class) -
        set(('TES4')))