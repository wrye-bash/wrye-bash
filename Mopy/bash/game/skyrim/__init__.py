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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2015 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This modules defines static data for use by bush, when TES V:
   Skyrim is set at the active game."""

from constants import bethDataFiles, allBethFiles
from ... import brec
from ...brec import *

#--Name of the game to use in UI.
displayName = u'Skyrim'
#--Name of the game's filesystem folder.
fsName = u'Skyrim'
#--Alternate display name to use instead of "Wrye Bash for ***"
altName = u'Wrye Smash'
#--Name of game's default ini file.
defaultIniFile = u'Skyrim_default.ini'

#--Exe to look for to see if this is the right game
exe = u'TESV.exe'

#--Registry keys to read to find the install location
regInstallKeys = [
    (u'Bethesda Softworks\\Skyrim',u'Installed Path'),
    ]

#--patch information
patchURL = u'' # Update via steam
patchTip = u'Update via Steam'

#--URL to the Nexus site for this game
nexusUrl = u'http://www.nexusmods.com/skyrim/'
nexusName = u'Skyrim Nexus'
nexusKey = 'bash.installers.openSkyrimNexus'

#--Creation Kit Set information
class cs:
    shortName = u'CK'                # Abbreviated name
    longName = u'Creation Kit'       # Full name
    exe = u'CreationKit.exe'         # Executable to run
    seArgs = None # u'-editor'       # Argument to pass to the SE to load the CS # Not yet needed
    imageName = u'creationkit%s.png' # Image name template for the status bar

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

#--SkyProc Patchers
class sp:
    shortName = u'SP'
    longName = u'SkyProc'
    installDir = u'SkyProc Patchers'

#--Quick shortcut for combining the SE and SD names
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

# Files BAIN shouldn't skip
dontSkip = (
       #These are all in the Interface folder. Apart from the skyui_ files, they are all present in vanilla.
       u'skyui_cfg.txt',
       u'skyui_translate.txt',
       u'credits.txt',
       u'credits_french.txt',
       u'fontconfig.txt',
       u'controlmap.txt',
       u'gamepad.txt',
       u'mouse.txt',
       u'keyboard_english.txt',
       u'keyboard_french.txt',
       u'keyboard_german.txt',
       u'keyboard_spanish.txt',
       u'keyboard_italian.txt',
)

# Directories where specific file extensions should not be skipped by BAIN
dontSkipDirs = {
                # This rule is to allow mods with string translation enabled.
                'interface\\translations':['.txt']
}

#Folders BAIN should never check
SkipBAINRefresh = {
    #Use lowercase names
    u'tes5edit backups',
}

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
    ext = u'.ess'               # Save file extension

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

#--The main plugin Wrye Bash should look for
masterFiles = [
    u'Skyrim.esm',
    u'Update.esm',
    ]

#--Plugin files that can't be deactivated
nonDeactivatableFiles = [
    u'Skyrim.esm',
    u'Update.esm',
    ]

namesPatcherMaster = re.compile(ur"^Skyrim.esm$",re.I|re.U)

#The pickle file for this game. Holds encoded GMST IDs from the big list below.
pklfile = r'bash\db\Skyrim_ids.pkl'

#--Game ESM/ESP/BSA files
#  These filenames need to be in lowercase,
# bethDataFiles = set()
# Moved to skyrim_const

#--Every file in the Data directory from Bethsoft
# allBethFiles = set()
# Moved to skyrim_const

#--BAIN: Directories that are OK to install to
dataDirs = {
    u'bash patches',
    u'dialogueviews',
    u'docs',
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
    u'seq',}
dataDirsPlus = {
    u'ini tweaks',
    u'skse',
    u'ini',
    u'asi',
    u'skyproc patchers',}

# Installer -------------------------------------------------------------------
# ensure all path strings are prefixed with 'r' to avoid interpretation of
#   accidental escape sequences
wryeBashDataFiles = {
    u'Bashed Patch.esp',
    u'Bashed Patch, 0.esp',
    u'Bashed Patch, 1.esp',
    u'Bashed Patch, 2.esp',
    u'Bashed Patch, 3.esp',
    u'Bashed Patch, 4.esp',
    u'Bashed Patch, 5.esp',
    u'Bashed Patch, 6.esp',
    u'Bashed Patch, 7.esp',
    u'Bashed Patch, 8.esp',
    u'Bashed Patch, 9.esp',
    u'Bashed Patch, CBash.esp',
    u'Bashed Patch, Python.esp',
    u'Bashed Patch, Warrior.esp',
    u'Bashed Patch, Thief.esp',
    u'Bashed Patch, Mage.esp',
    u'Bashed Patch, Test.esp',
    u'Docs\\Bash Readme Template.html',
    u'Docs\\wtxt_sand_small.css',
    u'Docs\\wtxt_teal.css',
    u'Docs\\Bash Readme Template.txt',
    u'Docs\\Bashed Patch, 0.html',
    u'Docs\\Bashed Patch, 0.txt',
}
wryeBashDataDirs = {
    u'Bash Patches',
    u'INI Tweaks'
}
ignoreDataFiles = {
}
ignoreDataFilePrefixes = {
}
ignoreDataDirs = {
    u'LSData'
}

#--List of GMST's in the main plugin (Skyrim.esm) that have 0x00000000
#  as the form id.  Any GMST as such needs it Editor Id listed here.
gmstEids = ['bAutoAimBasedOnDistance','fActionPointsAttackMagic','fActionPointsAttackRanged',
    'fActionPointsFOVBase','fActiveEffectConditionUpdateInterval','fActorAlertSoundTimer',
    'fActorAlphaFadeSeconds','fActorAnimZAdjust','fActorArmorDesirabilityDamageMult',
    'fActorArmorDesirabilitySkillMult','fActorLeaveWaterBreathTimer','fActorLuckSkillMult',
    'fActorStrengthEncumbranceMult','fActorSwimBreathBase','fActorTeleportFadeSeconds',
    'fActorWeaponDesirabilityDamageMult','fActorWeaponDesirabilitySkillMult','fAiAcquireKillBase',
    'fAiAcquireKillMult','fAIAcquireObjectDistance','fAiAcquirePickBase',
    'fAiAcquirePickMult','fAiAcquireStealBase','fAiAcquireStealMult',
    'fAIActivateHeight','fAIActivateReach','fAIActorPackTargetHeadTrackMod',
    'fAIAimBlockedHalfCircleRadius','fAIAimBlockedToleranceDegrees','fAIAwareofPlayerTimer',
    'fAIBestHeadTrackDistance','fAICombatFleeScoreThreshold','fAICombatNoAreaEffectAllyDistance',
    'fAICombatNoTargetLOSPriorityMult','fAICombatSlopeDifference','fAICombatTargetUnreachablePriorityMult',
    'fAICombatUnreachableTargetPriorityMult','fAICommentTimeWindow','fAIConversationExploreTime',
    'fAIDialogueDistance','fAIDistanceRadiusMinLocation','fAIDistanceTeammateDrawWeapon',
    'fAIDodgeDecisionBase','fAIDodgeFavorLeftRightMult','fAIDodgeVerticalRangedAttackMult',
    'fAIDodgeWalkChance','fAIEnergyLevelBase','fAIEngergyLevelMult',
    'fAIEscortFastTravelMaxDistFromPath','fAIEscortHysteresisWidth','fAIEscortStartStopDelayTime',
    'fAIEscortWaitDistanceExterior','fAIEscortWaitDistanceInterior','fAIExplosiveWeaponDamageMult',
    'fAIExplosiveWeaponRangeMult','fAIExteriorSpectatorDetection','fAIExteriorSpectatorDistance',
    'fAIFaceTargetAnimationAngle','fAIFindBedChairsDistance','fAIFleeConfBase',
    'fAIFleeConfMult','fAIFleeHealthMult','fAIFleeSuccessTimeout',
    'fAIHoldDefaultHeadTrackTimer','fAIHorseSearchDistance','fAIIdleAnimationDistance',
    'fAIIdleAnimationLargeCreatureDistanceMult','fAIIdleWaitTimeComplexScene','fAIInteriorHeadTrackMult',
    'fAIInteriorSpectatorDetection','fAIInteriorSpectatorDistance','fAILockDoorsSeenRecentlySeconds',
    'fAIMagicSpellMult','fAIMagicTimer','fAIMaxAngleRangeMovingToStartSceneDialogue','fAIMaxHeadTrackDistance',
    'fAIMaxHeadTrackDistanceFromPC','fAIMaxLargeCreatureHeadTrackDistance','fAIMaxSmileDistance',
    'fAIMaxWanderTime','fAIMeleeArmorMult','fAIMeleeHandMult',
    'fAIMeleeWeaponMult','fAIMinAngleRangeToStartSceneDialogue','fAIMinGreetingDistance',
    'fAIMinLocationHeight','fAIMoveDistanceToRecalcFollowPath','fAIMoveDistanceToRecalcTravelPath',
    'fAIMoveDistanceToRecalcTravelToActor','fAIPatrolHysteresisWidth','fAIPatrolMinSecondsAtNormalFurniture',
    'fAIPowerAttackCreatureChance','fAIPowerAttackKnockdownBonus','fAIPowerAttackNPCChance',
    'fAIPowerAttackRecoilBonus','fAIPursueDistanceLineOfSight','fAIRandomizeInitialLocationMinRadius',
    'fAIRangedWeaponMult','fAIRangMagicSpellMult','fAIRevertToScriptTracking',
    'fAIShoutRetryDelaySeconds','fAISocialTimerToWaitForEvent','fAISpectatorCommentTimer',
    'fAISpectatorShutdownDistance','fAISpectatorThreatDistExplosion','fAISpectatorThreatDistMelee',
    'fAISpectatorThreatDistMine','fAISpectatorThreatDistRanged','fAIStayonScriptHeadtrack',
    'fAItalktoNPCtimer','fAItalktosameNPCtimer','fAIUpdateMovementRestrictionsDistance',
    'fAIUseMagicToleranceDegrees','fAIUseWeaponAnimationTimeoutSeconds','fAIUseWeaponToleranceDegrees',
    'fAIWaitingforScriptCallback','fAIWalkAwayTimerForConversation','fAIWanderDefaultMinDist',
    'fAlchemyGoldMult','fAlchemyIngredientInitMult','fAlignEvilMaxKarma',
    'fAlignGoodMinKarma','fAlignMaxKarma','fAlignMinKarma',
    'fAlignVeryEvilMaxKarma','fAlignVeryGoodMinKarma','fAmbushOverRideRadiusforPlayerDetection',
    'fArmorRatingPCBase','fArmorWeightLightMaxMod','fArrowBounceBlockPercentage',
    'fArrowBounceLinearSpeed','fArrowBounceRotateSpeed','fArrowBowFastMult',
    'fArrowBowMinTime','fArrowBowSlowMult','fArrowFakeMass',
    'fArrowGravityBase','fArrowGravityMin','fArrowGravityMult',
    'fArrowMaxDistance','fArrowMinBowVelocity','fArrowMinDistanceForTrails',
    'fArrowMinPower','fArrowMinSpeedForTrails','fArrowMinVelocity',
    'fArrowOptimalDistance','fArrowSpeedMult','fArrowWeakGravity',
    'fArrowWobbleAmplitude','fArrowWobbleCurve','fArrowWobbleDuration',
    'fArrowWobblePeriod','fAttributeClassPrimaryBonus','fAttributeClassSecondaryBonus',
    'fAuroraFadeOutStart','fAutoAimMaxDegreesMelee','fAutoAimMaxDegreesVATS',
    'fAutomaticWeaponBurstCooldownTime','fAutomaticWeaponBurstFireTime','fAvoidPlayerDistance',
    'fBarterBuyMin','fBarterSellMax','fBeamWidthDefault',
    'fBigBumpSpeed','fBleedoutCheck','fBlockAmountHandToHandMult',
    'fBlockScoreNoShieldMult','fBlockSkillBase','fBloodSplatterCountBase',
    'fBloodSplatterCountDamageBase','fBloodSplatterCountDamageMult','fBloodSplatterCountRandomMargin',
    'fBodyMorphWeaponAdjustMult','fBowDrawTime','fBowHoldTimer',
    'fBowZoomStaminaRegenDelay','fBribeBase','fBribeMoralityMult',
    'fBribeMult','fBribeNPCLevelMult','fBSUnitsPerFoot',
    'fBuoyancyMultBody','fBuoyancyMultExtremity','fCameraShakeDistFadeDelta',
    'fCameraShakeDistFadeStart','fCameraShakeDistMin','fCameraShakeExplosionDistMult',
    'fCameraShakeFadeTime','fCameraShakeMultMin','fCameraShakeTime',
    'fCharacterControllerMultipleStepSpeed','fChaseDetectionTimerSetting','fCheckDeadBodyTimer',
    'fCheckPositionFallDistance','fClosetoPlayerDistance','fClothingArmorBase',
    'fClothingBase','fClothingClassScale','fClothingJewelryBase',
    'fClothingJewelryScale','fCombatAcquirePickupAnimationDelay','fCombatAcquireWeaponAmmoMinimumScoreMult',
    'fCombatAcquireWeaponAvoidTargetRadius','fCombatAcquireWeaponCloseDistanceMax','fCombatAcquireWeaponCloseDistanceMin',
    'fCombatAcquireWeaponDisarmedAcquireTime','fCombatAcquireWeaponDisarmedDistanceMax','fCombatAcquireWeaponDisarmedDistanceMin',
    'fCombatAcquireWeaponDisarmedTime','fCombatAcquireWeaponEnchantmentChargeMult','fCombatAcquireWeaponFindAmmoDistance',
    'fCombatAcquireWeaponMeleeScoreMult','fCombatAcquireWeaponMinimumScoreMult','fCombatAcquireWeaponMinimumTargetDistance',
    'fCombatAcquireWeaponRangedDistanceMax','fCombatAcquireWeaponRangedDistanceMin','fCombatAcquireWeaponReachDistance',
    'fCombatAcquireWeaponScoreCostMult','fCombatAcquireWeaponScoreRatioMax','fCombatAcquireWeaponSearchFailedDelay',
    'fCombatAcquireWeaponSearchRadiusBuffer','fCombatAcquireWeaponSearchSuccessDelay','fCombatAcquireWeaponTargetDistanceCheck',
    'fCombatAcquireWeaponUnarmedDistanceMax','fCombatAcquireWeaponUnarmedDistanceMin','fCombatActiveCombatantAttackRangeDistance',
    'fCombatActiveCombatantLastSeenTime','fCombatAdvanceInnerRadiusMid','fCombatAdvanceInnerRadiusMin',
    'fCombatAdvanceLastDamagedThreshold','fCombatAdvanceNormalAttackChance','fCombatAdvancePathRetryTime',
    'fCombatAdvanceRadiusStaggerMult','fCombatAimDeltaThreshold','fCombatAimLastSeenLocationTimeLimit',
    'fCombatAimMeleeHighPriorityUpdateTime','fCombatAimMeleeUpdateTime','fCombatAimProjectileBlockedTime',
    'fCombatAimProjectileGroundMinRadius','fCombatAimProjectileRandomOffset','fCombatAimProjectileUpdateTime',
    'fCombatAimTrackTargetUpdateTime','fCombatAngleTolerance','fCombatAnticipatedLocationCheckDistance',
    'fCombatAnticipateTime','fCombatApproachTargetSlowdownDecelerationMult','fCombatApproachTargetSlowdownDistance',
    'fCombatApproachTargetSlowdownUpdateTime','fCombatApproachTargetSlowdownVelocityAngle','fCombatApproachTargetSprintStopMovingRange',
    'fCombatApproachTargetSprintStopRange','fCombatApproachTargetUpdateTime','fCombatAreaHoldPositionMinimumRadius',
    'fCombatAreaStandardAttackedRadius','fCombatAreaStandardAttackedTime','fCombatAreaStandardCheckViewConeDistanceMax',
    'fCombatAreaStandardCheckViewConeDistanceMin','fCombatAreaStandardFlyingRadiusMult','fCombatAreaStandardRadius',
    'fCombatAttackAllowedOverrunDistance','fCombatAttackAnimationDrivenDelayTime','fCombatAttackAnticipatedDistanceMin',
    'fCombatAttackChanceBlockingMultMax','fCombatAttackChanceBlockingMultMin','fCombatAttackChanceBlockingSwingMult',
    'fCombatAttackChanceLastAttackBonus','fCombatAttackChanceLastAttackBonusTime','fCombatAttackChanceMax',
    'fCombatAttackChanceMin','fCombatAttackCheckTargetRangeDistance','fCombatAttackMovingAttackDistance',
    'fCombatAttackMovingAttackReachMult','fCombatAttackMovingStrikeAngleMult','fCombatAttackPlayerAnticipateMult',
    'fCombatAttackStationaryAttackDistance','fCombatAttackStrikeAngleMult','fCombatAvoidThreatsChance',
    'fCombatBackoffChance','fCombatBackoffMinDistanceMult','fCombatBashChanceMax',
    'fCombatBashChanceMin','fCombatBashTargetBlockingMult','fCombatBetweenAdvanceTimer',
    'fCombatBlockAttackChanceMax','fCombatBlockAttackChanceMin','fCombatBlockAttackReachMult',
    'fCombatBlockAttackStrikeAngleMult','fCombatBlockChanceMax','fCombatBlockChanceMin',
    'fCombatBlockMaxTargetRetreatVelocity','fCombatBlockStartDistanceMax','fCombatBlockStartDistanceMin',
    'fCombatBlockStopDistanceMax','fCombatBlockStopDistanceMin','fCombatBlockTimeMax',
    'fCombatBlockTimeMid','fCombatBlockTimeMin','fCombatBoltStickDepth',
    'fCombatBoundWeaponDPSBonus','fCombatBuffMaxTimer','fCombatBuffStandoffTimer',
    'fCombatCastConcentrationOffensiveMagicCastTimeMax','fCombatCastConcentrationOffensiveMagicCastTimeMin','fCombatCastConcentrationOffensiveMagicChanceMax',
    'fCombatCastConcentrationOffensiveMagicChanceMin','fCombatCastConcentrationOffensiveMagicWaitTimeMax','fCombatCastConcentrationOffensiveMagicWaitTimeMin',
    'fCombatCastImmediateOffensiveMagicChanceMax','fCombatCastImmediateOffensiveMagicChanceMin','fCombatCastImmediateOffensiveMagicHoldTimeAbsoluteMin',
    'fCombatCastImmediateOffensiveMagicHoldTimeMax','fCombatCastImmediateOffensiveMagicHoldTimeMin','fCombatCastImmediateOffensiveMagicHoldTimeMinDistance',
    'fCombatChangeProcessFaceTargetDistance','fCombatCircleAngleMax','fCombatCircleAngleMin',
    'fCombatCircleAnglePlayerMult','fCombatCircleChanceMax','fCombatCircleChanceMin',
    'fCombatCircleDistanceMax','fCombatCircleDistantChanceMax','fCombatCircleDistantChanceMin',
    'fCombatCircleMinDistanceMult','fCombatCircleMinDistanceRadiusMult','fCombatCircleMinMovementDistance',
    'fCombatCircleViewConeAngle','fCombatCloseRangeTrackTargetDistance','fCombatClusterUpdateTime',
    'fCombatCollectAlliesTimer','fCombatCoverAttackMaxWaitTime','fCombatCoverAttackOffsetDistance',
    'fCombatCoverAttackTimeMax','fCombatCoverAttackTimeMid','fCombatCoverAttackTimeMin',
    'fCombatCoverAvoidTargetRadius','fCombatCoverCheckCoverHeightMin','fCombatCoverCheckCoverHeightOffset',
    'fCombatCoverEdgeOffsetDistance','fCombatCoverLedgeOffsetDistance','fCombatCoverMaxRangeMult',
    'fCombatCoverMidPointMaxRangeBuffer','fCombatCoverMinimumActiveRange','fCombatCoverMinimumRange',
    'fCombatCoverObstacleMovedTime','fCombatCoverRangeMaxActiveMult','fCombatCoverRangeMaxBufferDistance',
    'fCombatCoverRangeMinActiveMult','fCombatCoverRangeMinBufferDistance','fCombatCoverReservationWidthMult',
    'fCombatCoverSearchDistanceMax','fCombatCoverSearchDistanceMin','fCombatCoverSearchFailedDelay',
    'fCombatCoverSecondaryThreatLastSeenTime','fCombatCoverSecondaryThreatMinDistance','fCombatCoverWaitLookOffsetDistance',
    'fCombatCoverWaitTimeMax','fCombatCoverWaitTimeMid','fCombatCoverWaitTimeMin',
    'fCombatDamageBonusMeleeSneakingMult','fCombatDamageScale','fCombatDeadActorHitConeMult',
    'fCombatDetectionDialogueMaxElapsedTime','fCombatDetectionDialogueMinElapsedTime','fCombatDetectionFleeingLostRemoveTime',
    'fCombatDetectionLostCheckNoticedDistance','fCombatDetectionLostRemoveDistance','fCombatDetectionLostRemoveDistanceTime',
    'fCombatDetectionLostRemoveTime','fCombatDetectionLostTimeLimit','fCombatDetectionLowDetectionDistance',
    'fCombatDetectionLowPriorityDistance','fCombatDetectionNoticedDistanceLimit','fCombatDetectionNoticedTimeLimit',
    'fCombatDetectionVeryLowPriorityDistance','fCombatDialogueAllyKilledDistanceMult','fCombatDialogueAllyKilledMaxElapsedTime',
    'fCombatDialogueAllyKilledMinElapsedTime','fCombatDialogueAttackDistanceMult','fCombatDialogueAvoidThreatDistanceMult',
    'fCombatDialogueAvoidThreatMaxElapsedTime','fCombatDialogueAvoidThreatMinElapsedTime','fCombatDialogueBashDistanceMult',
    'fCombatDialogueBleedoutDistanceMult','fCombatDialogueBleedOutMaxElapsedTime','fCombatDialogueBleedOutMinElapsedTime',
    'fCombatDialogueBlockDistanceMult','fCombatDialogueDeathDistanceMult','fCombatDialogueFleeDistanceMult',
    'fCombatDialogueFleeMaxElapsedTime','fCombatDialogueFleeMinElapsedTime','fCombatDialogueGroupStrategyDistanceMult',
    'fCombatDialogueHitDistanceMult','fCombatDialoguePowerAttackDistanceMult','fCombatDialogueTauntDistanceMult',
    'fCombatDisarmedFindBetterWeaponInitialTime','fCombatDisarmedFindBetterWeaponTime','fCombatDismemberedLimbVelocity',
    'fCombatDistanceMin','fCombatDiveBombChanceMax','fCombatDiveBombChanceMin',
    'fCombatDiveBombOffsetPercent','fCombatDiveBombSlowDownDistance','fCombatDodgeAccelerationMult',
    'fCombatDodgeAcceptableThreatScoreMult','fCombatDodgeAnticipateThreatTime','fCombatDodgeBufferDistance',
    'fCombatDodgeChanceMax','fCombatDodgeChanceMin','fCombatDodgeDecelerationMult',
    'fCombatDodgeMovingReactionTime','fCombatDodgeReactionTime','fCombatDPSBowSpeedMult',
    'fCombatDPSMeleeSpeedMult','fCombatEffectiveDistanceAnticipateTime','fCombatEnvironmentBloodChance',
    'fCombatFallbackChanceMax','fCombatFallbackChanceMin','fCombatFallbackDistanceMax',
    'fCombatFallbackDistanceMin','fCombatFallbackMaxAngle','fCombatFallbackMinMovementDistance',
    'fCombatFallbackWaitTimeMax','fCombatFallbackWaitTimeMin','fCombatFindAllyAttackLocationAllyRadius',
    'fCombatFindAllyAttackLocationDistanceMax','fCombatFindAllyAttackLocationDistanceMin','fCombatFindAttackLocationAvoidTargetRadius',
    'fCombatFindAttackLocationDistance','fCombatFindAttackLocationKeyAngle','fCombatFindAttackLocationKeyHeight',
    'fCombatFindBetterWeaponTime','fCombatFindLateralAttackLocationDistance','fCombatFindLateralAttackLocationIntervalMax',
    'fCombatFindLateralAttackLocationIntervalMin','fCombatFiringArcStationaryTurnMult','fCombatFlankingAngleOffset',
    'fCombatFlankingAngleOffsetCostMult','fCombatFlankingAngleOffsetMax','fCombatFlankingDirectionDistanceMult',
    'fCombatFlankingDirectionGoalAngleOffset','fCombatFlankingDirectionOffsetCostMult','fCombatFlankingDirectionRotateAngleOffset',
    'fCombatFlankingDistanceMax','fCombatFlankingDistanceMin','fCombatFlankingGoalAngleFarMax',
    'fCombatFlankingGoalAngleFarMaxDistance','fCombatFlankingGoalAngleFarMin','fCombatFlankingGoalAngleFarMinDistance',
    'fCombatFlankingGoalAngleNear','fCombatFlankingGoalCheckDistanceMax','fCombatFlankingGoalCheckDistanceMin',
    'fCombatFlankingGoalCheckDistanceMult','fCombatFlankingLocationGridSize','fCombatFlankingMaxTurnAngle',
    'fCombatFlankingMaxTurnAngleGoal','fCombatFlankingNearDistance','fCombatFlankingRotateAngle',
    'fCombatFlankingStalkRange','fCombatFlankingStalkTimeMax','fCombatFlankingStalkTimeMin',
    'fCombatFlankingStepDistanceMax','fCombatFlankingStepDistanceMin','fCombatFlankingStepDistanceMult',
    'fCombatFleeAllyDistanceMax','fCombatFleeAllyDistanceMin','fCombatFleeAllyRadius',
    'fCombatFleeCoverMinDistance','fCombatFleeCoverSearchRadius','fCombatFleeDistanceExterior',
    'fCombatFleeDistanceInterior','fCombatFleeDoorDistanceMax','fCombatFleeDoorTargetCheckDistance',
    'fCombatFleeInitialDoorRestrictChance','fCombatFleeLastDoorRestrictTime','fCombatFleeTargetAvoidRadius',
    'fCombatFleeTargetGatherRadius','fCombatFleeUseDoorChance','fCombatFleeUseDoorRestrictTime',
    'fCombatFlightEffectiveDistance','fCombatFlightMinimumRange','fCombatFlyingAttackChanceMax',
    'fCombatFlyingAttackChanceMin','fCombatFlyingAttackTargetDistanceThreshold','fCombatFollowRadiusBase',
    'fCombatFollowRadiusMin','fCombatFollowSneakFollowRadius','fCombatForwardAttackChance',
    'fCombatGiantCreatureReachMult','fCombatGrenadeBounceTimeMax','fCombatGrenadeBounceTimeMin',
    'fCombatGroundAttackChanceMax','fCombatGroundAttackChanceMin','fCombatGroupCombatStrengthUpdateTime',
    'fCombatGroupOffensiveMultMin','fCombatGuardFollowBufferDistance','fCombatGuardRadiusMin',
    'fCombatGuardRadiusMult','fCombatHideCheckViewConeDistanceMax','fCombatHideCheckViewConeDistanceMin',
    'fCombatHideFailedTargetDistance','fCombatHideFailedTargetLOSDistance','fCombatHitConeAngle',
    'fCombatHoverAngleLimit','fCombatHoverAngleMax','fCombatHoverAngleMin',
    'fCombatHoverChanceMax','fCombatHoverChanceMin','fCombatHoverTimeMax',
    'fCombatInTheWayTimer','fCombatInventoryDesiredRangeScoreMultMax','fCombatInventoryDesiredRangeScoreMultMid',
    'fCombatInventoryDesiredRangeScoreMultMin','fCombatInventoryDualWieldScorePenalty','fCombatInventoryEquipmentMinScoreMult',
    'fCombatInventoryEquippedScoreBonus','fCombatInventoryMaxRangeEquippedBonus','fCombatInventoryMaxRangeScoreMult',
    'fCombatInventoryMeleeEquipRange','fCombatInventoryMinEquipTimeBlock','fCombatInventoryMinEquipTimeDefault',
    'fCombatInventoryMinEquipTimeMagic','fCombatInventoryMinEquipTimeShout','fCombatInventoryMinEquipTimeStaff',
    'fCombatInventoryMinEquipTimeTorch','fCombatInventoryMinEquipTimeWeapon','fCombatInventoryMinRangeScoreMult',
    'fCombatInventoryMinRangeUnequippedBonus','fCombatInventoryOptimalRangePercent','fCombatInventoryRangedScoreMult',
    'fCombatInventoryResourceCurrentRequiredMult','fCombatInventoryResourceDesiredRequiredMult','fCombatInventoryResourceRegenTime',
    'fCombatInventoryShieldEquipRange','fCombatInventoryShoutMaxRecoveryTime','fCombatInventoryTorchEquipRange',
    'fCombatInventoryUpdateTimer','fCombatIronSightsDistance','fCombatIronSightsRangeMult',
    'fCombatItemBuffTimer','fCombatKillMoveDamageMult','fCombatLandingAvoidActorRadius',
    'fCombatLandingSearchDistance','fCombatLandingZoneDistance','fCombatLineOfSightTimer',
    'fCombatLocationTargetRadiusMin','fCombatLowFleeingTargetHitPercent','fCombatLowMaxAttackDistance',
    'fCombatLowTargetHitPercent','fCombatMagicArmorDistanceMax','fCombatMagicArmorDistanceMin',
    'fCombatMagicArmorMinCastTime','fCombatMagicBoundItemDistance','fCombatMagicBuffDuration',
    'fCombatMagicCloakDistanceMax','fCombatMagicCloakDistanceMin','fCombatMagicCloakMinCastTime',
    'fCombatMagicConcentrationAimVariance','fCombatMagicConcentrationFiringArcMult','fCombatMagicConcentrationMinCastTime',
    'fCombatMagicConcentrationScoreDuration','fCombatMagicDefaultLongDuration','fCombatMagicDefaultMinCastTime',
    'fCombatMagicDefaultShortDuration','fCombatMagicDisarmDistance','fCombatMagicDisarmRestrictTime',
    'fCombatMagicDrinkPotionWaitTime','fCombatMagicDualCastChance','fCombatMagicDualCastInterruptTime',
    'fCombatMagicImmediateAimVariance','fCombatMagicInvisibilityDistance','fCombatMagicInvisibilityMinCastTime',
    'fCombatMagicLightMinCastTime','fCombatMagicOffensiveMinCastTime','fCombatMagicParalyzeDistance',
    'fCombatMagicParalyzeMinCastTime','fCombatMagicParalyzeRestrictTime','fCombatMagicProjectileFiringArc',
    'fCombatMagicReanimateDistance','fCombatMagicReanimateMinCastTime','fCombatMagicReanimateRestrictTime',
    'fCombatMagicStaggerDistance','fCombatMagicSummonMinCastTime','fCombatMagicSummonRestrictTime',
    'fCombatMagicTacticalDuration','fCombatMagicTargetEffectMinCastTime','fCombatMagicWardAttackRangeDistance',
    'fCombatMagicWardAttackReachMult','fCombatMagicWardCooldownTime','fCombatMagicWardMagickaCastLimit',
    'fCombatMagicWardMagickaEquipLimit','fCombatMagicWardMinCastTime','fCombatMaintainOptimalDistanceMaxAngle',
    'fCombatMaintainRangeDistanceMin','fCombatMaxHoldScore','fCombatMaximumOptimalRangeMax',
    'fCombatMaximumOptimalRangeMid','fCombatMaximumOptimalRangeMin','fCombatMaximumProjectileRange',
    'fCombatMaximumRange','fCombatMeleeTrackTargetDistanceMax','fCombatMeleeTrackTargetDistanceMin',
    'fCombatMinEngageDistance','fCombatMissileImpaleDepth','fCombatMonitorBuffsTimer',
    'fCombatMoveToActorBufferDistance','fCombatMusicGroupThreatRatioMax','fCombatMusicGroupThreatRatioMin',
    'fCombatMusicGroupThreatRatioTimer','fCombatMusicNearCombatInnerRadius','fCombatMusicNearCombatOuterRadius',
    'fCombatMusicPlayerCombatStrengthCap','fCombatMusicPlayerNearStrengthMult','fCombatMusicStopTime',
    'fCombatMusicUpdateTime','fCombatOffensiveBashChanceMax','fCombatOffensiveBashChanceMin',
    'fCombatOptimalRangeMaxBufferDistance','fCombatOptimalRangeMinBufferDistance','fCombatOrbitTimeMax',
    'fCombatOrbitTimeMin','fCombatParalyzeTacticalDuration','fCombatPathingAccelerationMult',
    'fCombatPathingCurvedPathSmoothingMult','fCombatPathingDecelerationMult','fCombatPathingGoalRayCastPathDistance',
    'fCombatPathingIncompletePathMinDistance','fCombatPathingLocationCenterOffsetMult','fCombatPathingLookAheadDelta',
    'fCombatPathingNormalizedRotationSpeed','fCombatPathingRefLocationUpdateDistance','fCombatPathingRefLocationUpdateTimeDistanceMax',
    'fCombatPathingRefLocationUpdateTimeDistanceMin','fCombatPathingRefLocationUpdateTimeMax','fCombatPathingRefLocationUpdateTimeMin',
    'fCombatPathingRetryWaitTime','fCombatPathingRotationAccelerationMult','fCombatPathingStartRayCastPathDistance',
    'fCombatPathingStraightPathCheckDistance','fCombatPathingStraightRayCastPathDistance','fCombatPathingUpdatePathCostMult',
    'fCombatPerchAttackChanceMax','fCombatPerchAttackChanceMin','fCombatPerchAttackTimeMax',
    'fCombatPerchMaxTargetAngle','fCombatProjectileMaxRangeMult','fCombatProjectileMaxRangeOptimalMult',
    'fCombatRadiusMinMult','fCombatRangedAimVariance','fCombatRangedAttackChanceLastAttackBonus',
    'fCombatRangedAttackChanceLastAttackBonusTime','fCombatRangedAttackChanceMax','fCombatRangedAttackChanceMin',
    'fCombatRangedAttackHoldTimeAbsoluteMin','fCombatRangedAttackHoldTimeMax','fCombatRangedAttackHoldTimeMin',
    'fCombatRangedAttackHoldTimeMinDistance','fCombatRangedAttackMaximumHoldTime','fCombatRangedDistance',
    'fCombatRangedMinimumRange','fCombatRangedProjectileFiringArc','fCombatRangedStandoffTimer',
    'fCombatRelativeDamageMod','fCombatRestoreHealthPercentMax','fCombatRestoreHealthPercentMin',
    'fCombatRestoreHealthRestrictTime','fCombatRestoreMagickaPercentMax','fCombatRestoreMagickaPercentMin',
    'fCombatRestoreMagickaRestrictTime','fCombatRestoreStopCastThreshold','fCombatRoundAmount',
    'fCombatSearchAreaUpdateTime','fCombatSearchCenterRadius','fCombatSearchCheckDestinationDistanceMax',
    'fCombatSearchCheckDestinationDistanceMid','fCombatSearchCheckDestinationDistanceMin','fCombatSearchCheckDestinationTime',
    'fCombatSearchDoorDistance','fCombatSearchDoorDistanceLow','fCombatSearchDoorSearchRadius',
    'fCombatSearchExteriorRadiusMax','fCombatSearchExteriorRadiusMin','fCombatSearchIgnoreLocationRadius',
    'fCombatSearchInteriorRadiusMax','fCombatSearchInteriorRadiusMin','fCombatSearchInvestigateTime',
    'fCombatSearchLocationCheckDistance','fCombatSearchLocationCheckTime','fCombatSearchLocationInitialCheckTime',
    'fCombatSearchLocationInvestigateDistance','fCombatSearchLocationRadius','fCombatSearchLookTime',
    'fCombatSearchRadiusBufferDistance','fCombatSearchRadiusMemberDistance','fCombatSearchSightRadius',
    'fCombatSearchStartWaitTime','fCombatSearchUpdateTime','fCombatSearchWanderDistance',
    'fCombatSelectTargetSwitchUpdateTime','fCombatSelectTargetUpdateTime','fCombatShoutHeadTrackingAngleMovingMult',
    'fCombatShoutHeadTrackingAngleMult','fCombatShoutLongRecoveryTime','fCombatShoutMaxHeadTrackingAngle',
    'fCombatShoutReleaseTime','fCombatShoutShortRecoveryTime','fCombatSneakBowMult',
    'fCombatSneakCrossbowMult','fCombatSneakStaffMult','fCombatSpeakPowerAttackChance',
    'fCombatSpeakTauntChance','fCombatSpecialAttackChanceMax','fCombatSpecialAttackChanceMin',
    'fCombatSplashDamageMaxSpeed','fCombatSplashDamageMinDamage','fCombatSplashDamageMinRadius',
    'fCombatStaffTimer','fCombatStealthPointAttackedMaxValue','fCombatStealthPointDetectedEventMaxValue',
    'fCombatStealthPointMax','fCombatStealthPointRegenAlertWaitTime','fCombatStealthPointRegenLostWaitTime',
    'fCombatStepAdvanceDistance','fCombatStrafeChanceMax','fCombatStrafeChanceMin',
    'fCombatStrafeDistanceMax','fCombatStrafeDistanceMin','fCombatStrafeMinDistanceRadiusMult',
    'fCombatStrengthUpdateTime','fCombatSurroundDistanceMax','fCombatSurroundDistanceMin',
    'fCombatTargetEngagedLastSeenTime','fCombatTargetLocationAvoidNodeRadiusOffset','fCombatTargetLocationCurrentReservationDistanceMult',
    'fCombatTargetLocationMaxDistance','fCombatTargetLocationMinDistanceMult','fCombatTargetLocationPathingRadius',
    'fCombatTargetLocationRadiusSizeMult','fCombatTargetLocationRepositionAngleMult','fCombatTargetLocationSwimmingOffset',
    'fCombatTargetLocationWidthMax','fCombatTargetLocationWidthMin','fCombatTargetLocationWidthSizeMult',
    'fCombatTeammateFollowRadiusBase','fCombatTeammateFollowRadiusMin','fCombatThreatAnticipateTime',
    'fCombatThreatAvoidCost','fCombatThreatBufferRadius','fCombatThreatCacheVelocityTime',
    'fCombatThreatDangerousObjectHealth','fCombatThreatExplosiveObjectThreatTime','fCombatThreatExtrudeTime',
    'fCombatThreatExtrudeVelocityThreshold','fCombatThreatNegativeExtrudeTime','fCombatThreatSignificantScore',
    'fCombatThreatTimedExplosionLength','fCombatThreatUpdateTimeMax','fCombatThreatUpdateTimeMin',
    'fCombatThreatViewCone','fCombatUnreachableTargetCheckTime','fCombatVulnerabilityMod',
    'fCombatYieldRetryTime','fCombatYieldTime','fConeProjectileForceBase',
    'fConeProjectileForceMult','fConeProjectileForceMultAngular','fConeProjectileForceMultLinear',
    'fConeProjectileWaterScaleMult','fConfidenceCowardly','fConfidenceFoolhardy',
    'fConstructibleSkillUseConst','fConstructibleSkilluseExp','fConstructibleSkillUseMult',
    'fCoveredAdvanceMinAdvanceDistanceMax','fCoveredAdvanceMinAdvanceDistanceMin','fCoverEvaluationLastSeenExpireTime',
    'fCoverFiredProjectileExpireTime','fCoverFiringReloadClipPercent','fCoverWaitReloadClipPercent',
    'fCreatureDefaultTurningSpeed','fCrimeAlarmRespMult','fCrimeDispAttack',
    'fCrimeDispMurder','fCrimeDispPersonal','fCrimeDispPickpocket',
    'fCrimeDispSteal','fCrimeDispTresspass','fCrimeFavorMult',
    'fCrimeGoldSkillPenaltyMult','fCrimeGoldSteal','fCrimePersonalRegardMult',
    'fCrimeRegardMult','fCrimeSoundBase','fCrimeSoundMult',
    'fCrimeWitnessRegardMult','fDamageArmConditionBase','fDamageArmConditionMult',
    'fDamagePCSkillMin','fDamageSkillMax','fDamageSkillMin',
    'fDamageStrengthBase','fDamageStrengthMult','fDamageUnarmedPenalty',
    'fDamageWeaponMult','fDangerousObjectExplosionDamage','fDangerousObjectExplosionRadius',
    'fDangerousProjectileExplosionDamage','fDangerousProjectileExplosionRadius','fDaytimeColorExtension',
    'fDeadReactionDistance','fDeathForceMassBase','fDeathForceMassMult',
    'fDeathSoundMaxDistance','fDebrisFadeTime','fDebrisMaxVelocity',
    'fDebrisMinExtent','fDecapitateBloodTime','fDefaultAngleTolerance',
    'fDefaultHealth','fDefaultMagicka','fDefaultMass',
    'fDefaultRelaunchInterval','fDefaultStamina','fDemandBase',
    'fDemandMult','fDetectEventDistanceNPC','fDetectEventDistancePlayer',
    'fDetectEventDistanceVeryLoudMult','fDetectEventSneakDistanceVeryLoud','fDetectionActionTimer',
    'fDetectionCombatNonTargetDistanceMult','fDetectionCommentTimer','fDetectionEventExpireTime',
    'fDetectionLargeActorSizeMult','fDetectionLOSDistanceAngle','fDetectionLOSDistanceMultExterior',
    'fDetectionLOSDistanceMultInterior','fDetectionNightEyeBonus','fDetectionStateExpireTime',
    'fDetectionUpdateTimeMax','fDetectionUpdateTimeMaxComplex','fDetectionUpdateTimeMin',
    'fDetectionUpdateTimeMinComplex','fDetectionViewCone','fDetectProjectileDistanceNPC',
    'fDetectProjectileDistancePlayer','fDialogFocalDepthRange','fDialogFocalDepthStrength',
    'fDialogZoomInSeconds','fDialogZoomOutSeconds','fDifficultyDamageMultiplier',
    'fDifficultyDefaultValue','fDifficultyMaxValue','fDifficultyMinValue',
    'fDiffMultHPByPCE','fDiffMultHPByPCH','fDiffMultHPByPCN',
    'fDiffMultHPByPCVE','fDiffMultHPByPCVH','fDiffMultHPToPCE',
    'fDiffMultHPToPCH','fDiffMultHPToPCN','fDiffMultHPToPCVE',
    'fDiffMultHPToPCVH','fDiffMultXPE','fDiffMultXPN',
    'fDiffMultXPVE','fDisarmedPickupWeaponDistanceMult','fDistanceAutomaticallyActivateDoor',
    'fDistanceExteriorReactCombat','fDistanceFadeActorAutoLoadDoor','fDistanceInteriorReactCombat',
    'fDistanceProjectileExplosionDetection','fDistancetoPlayerforConversations','fDOFDistanceMult',
    'fDragonLandingZoneClearRadius','fDrinkRepeatRate','fDyingTimer',
    'fEffectShaderFillEdgeMinFadeRate','fEffectShaderParticleMinFadeRate','fEmbeddedWeaponSwitchChance',
    'fEmbeddedWeaponSwitchTime','fEnchantingCostExponent','fEnchantingSkillCostBase',
    'fEnchantingSkillCostMult','fEnchantingSkillCostScale','fEnchantmentGoldMult',
    'fEnemyHealthBarTimer','fEssentialDownCombatHealthRegenMult','fEssentialHealthPercentReGain',
    'fEssentialNonCombatHealRateBonus','fEssentialNPCMinimumHealth','fEvaluatePackageTimer',
    'fEvaluateProcedureTimer','fExplosionForceClutterUpBias','fExplosionForceKnockdownMinimum',
    'fExplosionKnockStateExplodeDownTime','fExplosionLOSBuffer','fExplosionLOSBufferDistance',
    'fExplosionMaxImpulse','fExplosiveProjectileBlockedResetTime','fExplosiveProjectileBlockedWaitTime',
    'fExpressionChangePerSec','fExpressionStrengthAdd','fEyePitchMaxOffsetEmotionSad',
    'fEyePitchMinOffsetEmotionAngry','fEyePitchMinOffsetEmotionHappy','fFallLegDamageMult',
    'fFastTravelSpeedMult','fFavorCostActivator','fFavorCostAttack',
    'fFavorCostAttackCrimeMult','fFavorCostLoadDoor','fFavorCostNonLoadDoor',
    'fFavorCostOwnedDoorMult','fFavorCostStealContainerCrime','fFavorCostStealContainerMult',
    'fFavorCostStealObjectMult','fFavorCostTakeObject','fFavorCostUnlockContainer',
    'fFavorCostUnlockDoor','fFavorEventStopDistance','fFavorEventTriggerDistance',
    'fFleeDoneDistanceExterior','fFleeDoneDistanceInterior','fFleeIsSafeTimer',
    'fFloatQuestMarkerFloatHeight','fFloatQuestMarkerMaxDistance','fFloatQuestMarkerMinDistance',
    'fFollowerSpacingAtDoors','fFollowExtraCatchUpSpeedMult','fFollowMatchSpeedZoneWidth',
    'fFollowRunMaxSpeedupMultiplier','fFollowSlowdownZoneWidth','fFollowStartSprintDistance',
    'fFollowStopZoneMinMult','fFollowWalkMaxSpeedupMultiplier','fFollowWalkMinSlowdownMultiplier',
    'fFollowWalkZoneMult','fFriendHitTimer','fFriendMinimumLastHitTime',
    'fFurnitureScaleAnimDurationNPC','fFurnitureScaleAnimDurationPlayer','fGameplayImpulseMinMass',
    'fGameplayImpulseMultTrap','fGameplayImpulseScale','fGameplaySpeakingEmotionMaxChangeValue',
    'fGetHitPainMult','fGrabMaxWeightRunning','fGrabMaxWeightWalking',
    'fGrenadeAgeMax','fGrenadeHighArcSpeedPercentage','fGrenadeThrowHitFractionThreshold',
    'fGunDecalCameraDistance','fGunReferenceSkill','fGunShellCameraDistance',
    'fGunShellLifetime','fGunShellRotateRandomize','fGunShellRotateSpeed',
    'fGunSpreadCrouchBase','fGunSpreadDriftBase','fGunSpreadHeadBase',
    'fGunSpreadHeadMult','fGunSpreadIronSightsBase','fGunSpreadIronSightsMult',
    'fGunSpreadNPCArmBase','fGunSpreadNPCArmMult','fGunSpreadRunBase',
    'fGunSpreadWalkBase','fGunSpreadWalkMult','fHandDamageSkillBase',
    'fHandDamageSkillMult','fHandDamageStrengthBase','fHandDamageStrengthMult',
    'fHandHealthMax','fHandHealthMin','fHandReachDefault',
    'fHazardDefaultTargetInterval','fHazardDropMaxDistance','fHazardMaxWaitTime',
    'fHazardMinimumSpawnInterval','fHazardSpacingMult','fHeadingMarkerAngleTolerance',
    'fHealthDataValue2','fHealthDataValue3','fHealthDataValue4',
    'fHealthDataValue5','fHealthDataValue6','fHealthRegenDelayMax',
    'fHorseMountOffsetX','fHorseMountOffsetY','fHostileActorExteriorDistance',
    'fHostileActorInteriorDistance','fHostileFlyingActorExteriorDistance','fIdleMarkerAngleTolerance',
    'fImpactShaderMaxMagnitude','fImpactShaderMinMagnitude','fIntimidateConfidenceMultAverage',
    'fIntimidateConfidenceMultBrave','fIntimidateConfidenceMultCautious','fIntimidateConfidenceMultCowardly',
    'fIntimidateConfidenceMultFoolhardy','fIntimidateSpeechcraftCurve','fInvisibilityMinRefraction',
    'fIronSightsDOFSwitchSeconds','fIronSightsFOVTimeChange','fItemPointsMult',
    'fItemRepairCostMult','fJumpDoubleMult','fJumpFallRiderMult',
    'fJumpFallSkillBase','fJumpFallSkillMult','fJumpMoveBase',
    'fJumpMoveMult','fKarmaModMurderingNonEvilCreature','fKarmaModMurderingNonEvilNPC',
    'fKillCamLevelBias','fKillCamLevelFactor','fKillCamLevelMaxBias',
    'fKillMoveMaxDuration','fKillWitnessesTimerSetting','fKnockbackAgilBase',
    'fKnockbackAgilMult','fKnockbackDamageBase','fKnockdownAgilBase',
    'fKnockdownAgilMult','fKnockdownBaseHealthThreshold','fKnockdownChance',
    'fKnockdownDamageBase','fKnockdownDamageMult','fLargeProjectilePickBufferSize',
    'fLargeProjectileSize','fLargeRefMinSize','fLeveledLockMult',
    'fLightRecalcTimer','fLightRecalcTimerPlayer','fLoadingWheelScale',
    'fLockLevelBase','fLockLevelMult','fLockpickBreakAdept',
    'fLockpickBreakApprentice','fLockPickBreakBase','fLockpickBreakExpert',
    'fLockpickBreakMaster','fLockPickBreakMult','fLockpickBreakNovice',
    'fLockpickBreakSkillBase','fLockpickBreakSkillMult','fLockPickQualityBase',
    'fLockPickQualityMult','fLockpickSkillSweetSpotBase','fLockSkillBase',
    'fLockSkillMult','fLockTrapGoOffBase','fLockTrapGoOffMult',
    'fLookDownDisableBlinkingAmt','fLowHealthTutorialPercentage','fLowLevelNPCBaseHealthMult',
    'fLowMagickaTutorialPercentage','fLowStaminaTutorialPercentage','fMagicAbsorbDistanceReachMult',
    'fMagicAccumulatingModifierEffectHoldDuration','fMagicAreaScale','fMagicBallMaximumDistance',
    'fMagicBallOptimalDistance','fMagicBarrierDepth','fMagicBarrierHeight',
    'fMagicBarrierSpacing','fMagicBoltDuration','fMagicBoltMaximumDistance',
    'fMagicBoltOptimalDistance','fMagicBoltSegmentLength','fMagicCasterPCSkillCostMult',
    'fMagicCasterSkillCostBase','fMagicCasterTargetUpdateInterval','fMagicCEEnchantMagOffset',
    'fMagicChainExplosionEffectivenessDelta','fMagicCloudAreaMin','fMagicCloudDurationMin',
    'fMagicCloudFindTargetTime','fMagicCloudLifeScale','fMagicCloudSizeScale',
    'fMagicCloudSlowdownRate','fMagicCloudSpeedBase','fMagicCloudSpeedScale',
    'fMagicCostScale','fMagicDefaultAccumulatingModifierEffectRate','fMagicDefaultCEBarterFactor',
    'fMagicDefaultTouchDistance','fMagicDiseaseTransferBase','fMagicDiseaseTransferMult',
    'fMagicDispelMagnitudeMult','fMagicDualCastingCostBase','fMagicDualCastingEffectivenessMult',
    'fMagicDualCastingTimeBase','fMagicDurMagBaseCostMult','fMagicEnchantmentChargeBase',
    'fMagicEnchantmentChargeMult','fMagicEnchantmentDrainBase','fMagicEnchantmentDrainMult',
    'fMagicExplosionAgilityMult','fMagicExplosionClutterMult','fMagicExplosionIncorporealMult',
    'fMagicExplosionIncorporealTime','fMagicExplosionPowerBase','fMagicExplosionPowerMax',
    'fMagicExplosionPowerMin','fMagicExplosionPowerMult','fMagicFogMaximumDistance',
    'fMagicFogOptimalDistance','fMagicGrabActorDrawSpeed','fMagicGrabActorMinDistance',
    'fMagicGrabActorRange','fMagicGrabActorThrowForce','fMagickaRegenDelayMax',
    'fMagickaReturnBase','fMagickaReturnMult','fMagicLesserPowerCooldownTimer',
    'fMagicLightRadiusBase','fMagicNightEyeAmbient','fMagicPlayerMinimumInvisibility',
    'fMagicPostDrawCastDelay','fMagicProjectileMaxDistance','fMagicResistActorSkillBase',
    'fMagicResistActorSkillMult','fMagicResistTargetWillpowerBase','fMagicResistTargetWillpowerMult',
    'fMagicSprayMaximumDistance','fMagicSprayOptimalDistance','fMagicSummonMaxAppearTime',
    'fMagicTelekinesisComplexMaxForce','fMagicTelekinesisComplexObjectDamping','fMagicTelekinesisComplexSpringDamping',
    'fMagicTelekinesisComplexSpringElasticity','fMagicTelekinesisDamageBase','fMagicTelekinesisDamageMult',
    'fMagicTelekinesisDualCastDamageMult','fMagicTelekinesisDualCastThrowMult','fMagicTelekinesisLiftPowerMult',
    'fMagicTelekinesisMaxForce','fMagicTelekinesisMoveAccelerate','fMagicTelekinesisMoveBase',
    'fMagicTelekinesisMoveMax','fMagicTelekinesisObjectDamping','fMagicTelekinesisSpringDamping',
    'fMagicTelekinesisSpringElasticity','fMagicTelekinesisThrow','fMagicTelekinesisThrowAccelerate',
    'fMagicTelekinesisThrowMax','fMagicTrackingLimit','fMagicTrackingLimitComplex',
    'fMagicTrackingMultBall','fMagicTrackingMultBolt','fMagicTrackingMultFog',
    'fMagicUnitsPerFoot','fMagicVACNoPartTargetedMult','fMagicVACPartTargetedMult',
    'fMapMarkerMaxPercentSize','fMapMarkerMinFadeAlpha','fMapMarkerMinPercentSize',
    'fMapQuestMarkerMaxPercentSize','fMapQuestMarkerMinFadeAlpha','fMapQuestMarkerMinPercentSize',
    'fMasserAngleShadowEarlyFade','fMasserSpeed','fMasserZOffset',
    'fMaximumWind','fMaxSandboxRescanSeconds','fMaxSellMult',
    'fMeleeMovementRestrictionsUpdateTime','fMeleeSweepViewAngleMult','fMinDistanceUseHorse',
    'fMineAgeMax','fMinesBlinkFast','fMinesBlinkMax',
    'fMinesBlinkSlow','fMinSandboxRescanSeconds','fModelReferenceEffectMaxWaitTime',
    'fmodifiedTargetAttackRange','fMotionBlur','fMountedMaxLookingDown',
    'fMoveCharRunBase','fMovementNearTargetAvoidCost','fMovementNearTargetAvoidRadius',
    'fMovementTargetAvoidCost','fMovementTargetAvoidRadius','fMovementTargetAvoidRadiusMult',
    'fMoveSprintMult','fMoveSwimMult','fMoveWeightMin',
    'fNPCAttributeHealthMult','fNPCBaseMagickaMult','fNPCGeneticVariation',
    'fObjectHitH2HReach','fObjectHitTwoHandReach','fObjectHitWeaponReach',
    'fObjectMotionBlur','fObjectWeightPickupDetectionMult','fOutOfBreathStaminaRegenDelay',
    'fPainDelay','fPCBaseHealthMult','fPCBaseMagickaMult',
    'fPerceptionMult','fPerkHeavyArmorExpertSpeedMult','fPerkHeavyArmorJourneymanDamageMult',
    'fPerkHeavyArmorMasterSpeedMult','fPerkHeavyArmorNoviceDamageMult','fPerkHeavyArmorSinkGravityMult',
    'fPerkLightArmorExpertSpeedMult','fPerkLightArmorJourneymanDamageMult','fPerkLightArmorMasterRatingMult',
    'fPerkLightArmorNoviceDamageMult','fPersAdmireAggr','fPersAdmireConf',
    'fPersAdmireEner','fPersAdmireIntel','fPersAdmirePers',
    'fPersAdmireResp','fPersAdmireStre','fPersAdmireWillp',
    'fPersBoastAggr','fPersBoastConf','fPersBoastEner',
    'fPersBoastIntel','fPersBoastPers','fPersBoastResp',
    'fPersBoastStre','fPersBoastWillp','fPersBullyAggr',
    'fPersBullyConf','fPersBullyEner','fPersBullyIntel',
    'fPersBullyPers','fPersBullyResp','fPersBullyStre',
    'fPersBullyWillp','fPersJokeAggr','fPersJokeConf',
    'fPersJokeEner','fPersJokeIntel','fPersJokePers',
    'fPersJokeResp','fPersJokeStre','fPersJokeWillp',
    'fPersuasionAccuracyMaxDisposition','fPersuasionAccuracyMaxSelect','fPersuasionAccuracyMinDispostion',
    'fPersuasionAccuracyMinSelect','fPersuasionBaseValueMaxDisposition','fPersuasionBaseValueMaxSelect',
    'fPersuasionBaseValueMinDispostion','fPersuasionBaseValueMinSelect','fPersuasionBaseValueShape',
    'fPersuasionMaxDisposition','fPersuasionMaxInput','fPersuasionMaxSelect',
    'fPersuasionMinDispostion','fPersuasionMinInput','fPersuasionMinPercentCircle',
    'fPersuasionMinSelect','fPersuasionShape','fPhysicsDamage1Damage',
    'fPhysicsDamage2Damage','fPhysicsDamage2Mass','fPhysicsDamage3Damage',
    'fPhysicsDamage3Mass','fPhysicsDamageSpeedBase','fPhysicsDamageSpeedMin',
    'fPhysicsDamageSpeedMult','fPickLevelBase','fPickLevelMult',
    'fPickNumBase','fPickNumMult','fPickPocketAmountBase',
    'fPickPocketDetected','fPickPocketWeightBase','fPickSpring1',
    'fPickSpring2','fPickSpring3','fPickSpring4',
    'fPickSpring5','fPickupItemDistanceFudge','fPickUpWeaponDelay',
    'fPickupWeaponDistanceMinMaxDPSMult','fPickupWeaponMeleeDistanceMax','fPickupWeaponMeleeDistanceMin',
    'fPickupWeaponMeleeWeaponDPSMult','fPickupWeaponMinDPSImprovementPercent','fPickupWeaponRangedDistanceMax',
    'fPickupWeaponRangedDistanceMin','fPickupWeaponRangedMeleeDPSRatioThreshold','fPickupWeaponTargetUnreachableDistanceMult',
    'fPickupWeaponUnarmedDistanceMax','fPickupWeaponUnarmedDistanceMin','fPlayerDropDistance',
    'fPlayerHealthHeartbeatFast','fPlayerHealthHeartbeatSlow','fPlayerMaxResistance',
    'fPlayerTargetCombatDistance','fPlayerTeleportFadeSeconds','fPotionGoldValueMult',
    'fPotionMortPestleMult','fPotionMortPestleMult','fPotionT1AleDurMult',
    'fPotionT1AleMagMult','fPotionT1CalDurMult','fPotionT1CalMagMult',
    'fPotionT1MagMult','fPotionT1RetDurMult','fPotionT1RetMagMult',
    'fPotionT2AleDurMult','fPotionT2CalDurMult','fPotionT2RetDurMult',
    'fPotionT3AleMagMult','fPotionT3CalMagMult','fPotionT3RetMagMult',
    'fPrecipWindMult','fProjectileCollisionImpulseScale','fProjectileDefaultTracerRange',
    'fProjectileDeflectionTime','fProjectileKnockMinMass','fProjectileKnockMultClutter',
    'fProjectileKnockMultProp','fProjectileKnockMultTrap','fProjectileMaxDistance',
    'fProjectileReorientTracerMin','fQuestCinematicCharacterFadeIn','fQuestCinematicCharacterFadeInDelay',
    'fQuestCinematicCharacterFadeOut','fQuestCinematicCharacterRemain','fQuestCinematicObjectiveFadeIn',
    'fQuestCinematicObjectiveFadeInDelay','fQuestCinematicObjectiveFadeOut','fQuestCinematicObjectivePauseTime',
    'fQuestCinematicObjectiveScrollTime','fRandomDoorDistance','fRechargeGoldMult',
    'fReEquipArmorTime','fReflectedAbsorbChanceReduction','fRefTranslationAlmostDonePercent',
    'fRegionGenNoiseFactor','fRegionGenTexGenMatch','fRegionGenTexGenNotMatch',
    'fRegionGenTexPlacedMatch','fRegionGenTexPlacedNotMatch','fRegionGenTreeSinkPower',
    'fRegionObjectDensityPower','fRelationshipBase','fRelationshipMult',
    'fRemoteCombatMissedAttack','fRemoveExcessComplexDeadTime','fRepairMax',
    'fRepairMin','fRepairScavengeMult','fRepairSkillBase',
    'fReservationExpirationSeconds','fResistArrestTimer','fRockitDamageBonusWeightMin',
    'fRockitDamageBonusWeightMult','fRoomLightingTransitionDuration','fRumbleBlockStrength',
    'fRumbleBlockTime','fRumbleHitBlockedStrength','fRumbleHitBlockedTime',
    'fRumbleHitStrength','fRumbleHitTime','fRumblePainStrength',
    'fRumblePainTime','fRumbleShakeRadiusMult','fRumbleShakeTimeMult',
    'fRumbleStruckStrength','fRumbleStruckTime','fSandboxBreakfastMax',
    'fSandboxBreakfastMin','fSandboxCylinderTop','fSandBoxDelayEvalSeconds',
    'fSandboxDurationMultSitting','fSandboxDurationMultSleeping','fSandboxDurationMultWandering',
    'fSandboxDurationRangeMult','fSandboxEnergyMult','fSandboxEnergyMultEatSitting',
    'fSandboxEnergyMultEatStanding','fSandboxEnergyMultFurniture','fSandboxEnergyMultSitting',
    'fSandboxEnergyMultSleeping','fSandboxEnergyMultWandering','fSandBoxExtraDialogueRange',
    'fSandBoxInterMarkerMinDist','fSandBoxSearchRadius','fSandboxSleepDurationMax',
    'fSandboxSleepDurationMin','fSandboxSleepStartMax','fSandboxSleepStartMin',
    'fSayOncePerDayInfoTimer','fScrollCostMult','fSecondsBetweenWindowUpdate',
    'fSecundaAngleShadowEarlyFade','fSecundaSpeed','fSecundaZOffset',
    'fSeenDataUpdateRadius','fShieldBashPCMin','fShieldBashSkillUseBase',
    'fShieldBashSkillUseMult','fShockBoltGrowWidth','fShockBoltsLength',
    'fShockBoltSmallWidth','fShockBoltsRadius','fShockBoltsRadiusStrength',
    'fShockBranchBoltsRadius','fShockBranchBoltsRadiusStrength','fShockBranchLifetime',
    'fShockBranchSegmentLength','fShockBranchSegmentVariance','fShockCastVOffset',
    'fShockCoreColorB','fShockCoreColorG','fShockCoreColorR',
    'fShockGlowColorB','fShockGlowColorG','fShockGlowColorR',
    'fShockSegmentLength','fShockSegmentVariance','fShockSubSegmentVariance',
    'fShoutTimeout','fSittingMaxLookingDown','fSkillUsageSneakHidden',
    'fSkyCellRefProcessDistanceMult','fSmallBumpSpeed','fSmithingArmorMax',
    'fSmithingConditionFactor','fSmithingWeaponMax','fSneakAmbushTargetMod',
    'fSneakAttackSkillUsageRanged','fSneakCombatMod','fSneakDetectionSizeLarge',
    'fSneakDetectionSizeNormal','fSneakDetectionSizeSmall','fSneakDetectionSizeVeryLarge',
    'fSneakDistanceAttenuationExponent','fSneakEquippedWeightBase','fSneakEquippedWeightMult',
    'fSneakLightMoveMult','fSneakLightRunMult','fSneakNoticeMin',
    'fSneakSizeBase','fSneakStealthBoyMult','fSortActorDistanceListTimer',
    'fSpecialLootMaxPCLevelBase','fSpecialLootMaxPCLevelMult','fSpecialLootMaxZoneLevelBase',
    'fSpecialLootMinPCLevelBase','fSpecialLootMinZoneLevelBase','fSpeechCraftBase',
    'fSpeechcraftFavorMax','fSpeechcraftFavorMin','fSpeechCraftMult',
    'fSpellCastingDetectionHitActorMod','fSpellCastingDetectionMod','fSpellmakingGoldMult',
    'fSplashScale1','fSplashScale2','fSplashScale3',
    'fSplashSoundLight','fSplashSoundOutMult','fSplashSoundTimer',
    'fSplashSoundVelocityMult','fSprayDecalsDistance','fSprayDecalsGravity',
    'fSprintEncumbranceMult','fStagger1WeapAR','fStagger1WeapMult',
    'fStagger2WeapAR','fStagger2WeapMult','fStaggerAttackBase',
    'fStaggerAttackMult','fStaggerBlockAttackBase','fStaggerBowAR',
    'fStaggerDaggerAR','fStaggerMassBase','fStaggerMassMult',
    'fStaggerMassOffsetMult','fStaggerMaxDuration','fStaggerRecoilingMult',
    'fStaggerRunningMult','fStaggerShieldMult','fStaminaBlockStaggerMult',
    'fStaminaRegenDelayMax','fStatsCameraNearDistance','fStatsHealthLevelMult',
    'fStatsHealthStartMult','fStatsLineScale','fStatsRotationRampTime',
    'fStatsRotationSpeedMax','fStatsSkillsLookAtX','fStatsSkillsLookAtY',
    'fStatsSkillsLookAtZ','fStatsStarCameraOffsetX','fStatsStarCameraOffsetY',
    'fStatsStarCameraOffsetZ','fStatsStarLookAtX','fStatsStarLookAtY',
    'fStatsStarLookAtZ','fStatsStarScale','fStatsStarZInitialOffset',
    'fSubmergedAngularDamping','fSubmergedLinearDampingH','fSubmergedLinearDampingV',
    'fSubmergedLODDistance','fSubmergedMaxSpeed','fSubmergedMaxWaterDistance',
    'fSubSegmentVariance','fSummonDistanceCheckThreshold','fSummonedCreatureSearchRadius',
    'fSunReduceGlareSpeed','fTakeBackTimerSetting','fTargetMovedCoveredMoveRepathLength',
    'fTargetMovedRepathLength','fTargetMovedRepathLengthLow','fTargetSearchRadius',
    'fTeammateAggroOnDistancefromPlayer','fTemperingSkillUseItemValConst','fTemperingSkillUseItemValExp',
    'fTemperingSkillUseItemValMult','fTimerForPlayerFurnitureEnter','fTimeSpanAfternoonEnd',
    'fTimeSpanAfternoonStart','fTimeSpanEveningEnd','fTimeSpanEveningStart',
    'fTimeSpanMidnightEnd','fTimeSpanMidnightStart','fTimeSpanMorningEnd',
    'fTimeSpanMorningStart','fTimeSpanNightEnd','fTimeSpanNightStart',
    'fTimeSpanSunriseEnd','fTimeSpanSunriseStart','fTimeSpanSunsetEnd',
    'fTimeSpanSunsetStart','fTorchEvaluationTimer','fTorchLightLevelInterior',
    'fTorchLightLevelMorning','fTorchLightLevelNight','fTrackEyeXY',
    'fTrackEyeZ','fTrackFudgeXY','fTrackFudgeZ',
    'fTrackJustAcquiredDuration','fTrackMaxZ','fTrackMinZ',
    'fTrackXY','fTrainingBaseCost','fTreeTrunkToFoliageMultiplier',
    'fTriggerAvoidPlayerDistance','fUnarmedCreatureDPSMult','fUnarmedDamageMult',
    'fUnarmedNPCDPSMult','fUnderwaterFullDepth','fValueofItemForNoOwnership',
    'fVATSAutomaticMeleeDamageMult','fVATSCameraMinTime','fVATSCamTransRBDownStart',
    'fVATSCamTransRBRampDown','fVATSCamTransRBRampup','fVATSCamZoomInTime',
    'fVATSCriticalChanceBonus','fVATSDestructibleMult','fVATSDOFSwitchSeconds',
    'fVATSGrenadeChanceMult','fVATSGrenadeDistAimZMult','fVATSGrenadeRangeMin',
    'fVATSGrenadeRangeMult','fVATSGrenadeSkillFactor','fVATSGrenadeSuccessExplodeTimer',
    'fVATSGrenadeSuccessMaxDistance','fVATSGrenadeTargetMelee','fVATSHitChanceMult',
    'fVATSImageSpaceTransitionTime','fVATSLimbSelectCamPanTime','fVATSMaxChance',
    'fVATSMaxEngageDistance','fVATSMeleeArmConditionBase','fVATSMeleeArmConditionMult',
    'fVATSMeleeChanceMult','fVATSMeleeMaxDistance','fVATSMeleeReachMult',
    'fVATSMoveCameraMaxSpeed','fVATSMoveCameraYPercent','fVATSSafetyMaxTime',
    'fVATSSafetyMaxTimeRanged','fVATSShotBurstTime','fVatsShotgunSpreadRatio',
    'fVATSSkillFactor','fVATSSmartCameraCheckStepCount','fVATSStealthMult',
    'fVATSTargetActorHeightPanMult','fVATSTargetFOVMinDist','fVATSTargetFOVMinFOV',
    'fVATSTargetScanRotateMult','fVATSTargetSelectCamPanTime','fVATSTargetTimeUpdateMult',
    'fVATSThrownWeaponRangeMult','fVoiceRateBase','fWardAngleForExplosions',
    'fWeaponBashMin','fWeaponBashPCMax','fWeaponBashPCMin',
    'fWeaponBashSkillUseBase','fWeaponBashSkillUseMult','fWeaponBlockSkillUseBase',
    'fWeaponBlockSkillUseMult','fWeaponBloodAlphaToRGBScale','fWeaponClutterKnockBipedScale',
    'fWeaponClutterKnockMaxWeaponMass','fWeaponClutterKnockMinClutterMass','fWeaponClutterKnockMult',
    'fWeaponConditionCriticalChanceMult','fWeaponConditionJam10','fWeaponConditionJam5',
    'fWeaponConditionJam6','fWeaponConditionJam7','fWeaponConditionJam8',
    'fWeaponConditionJam9','fWeaponConditionRateOfFire10','fWeaponConditionReloadJam1',
    'fWeaponConditionReloadJam10','fWeaponConditionReloadJam2','fWeaponConditionReloadJam3',
    'fWeaponConditionReloadJam4','fWeaponConditionReloadJam5','fWeaponConditionReloadJam6',
    'fWeaponConditionReloadJam7','fWeaponConditionReloadJam8','fWeaponConditionReloadJam9',
    'fWeaponConditionSpread10','fWeaponTwoHandedAnimationSpeedMult','fWeatherCloudSpeedMax',
    'fWeatherFlashAmbient','fWeatherFlashDirectional','fWeatherFlashDuration',
    'fWeatherTransMax','fWeatherTransMin','fWortalchmult',
    'fWortcraftChanceIntDenom','fWortcraftChanceLuckDenom','fWortcraftStrChanceDenom',
    'fWortcraftStrCostDenom','fWortStrMult','fXPPerSkillRank',
    'fZKeyComplexHelperMinDistance','fZKeyComplexHelperScale','fZKeyComplexHelperWeightMax',
    'fZKeyComplexHelperWeightMin','fZKeyHeavyWeight','fZKeyMaxContactDistance',
    'fZKeyMaxContactMassRatio','fZKeyMaxForceScaleHigh','fZKeyMaxForceScaleLow',
    'fZKeyMaxForceWeightLow','fZKeyObjectDamping','fZKeySpringDamping',
    'fZKeySpringElasticity','iActivatePickLength','iActorKeepTurnDegree',
    'iActorLuckSkillBase','iActorTorsoMaxRotation','iAICombatMaxAllySummonCount',
    'iAICombatMinDetection','iAICombatRestoreMagickaPercentage','iAIFleeMaxHitCount',
    'iAIMaxSocialDistanceToTriggerEvent','iAimingNumIterations','iAINPCRacePowerChance',
    'iAINumberActorsComplexScene','iAINumberDaysToStayBribed','iAINumberDaysToStayIntimidated',
    'iAlertAgressionMin','iAllowAlchemyDuringCombat','iAllowRechargeDuringCombat',
    'iAllowRepairDuringCombat','iAllyHitCombatAllowed','iAllyHitNonCombatAllowed',
    'iArmorBaseSkill','iArmorDamageBootsChance','iArmorDamageCuirassChance',
    'iArmorDamageGauntletsChance','iArmorDamageGreavesChance','iArmorDamageHelmChance',
    'iArmorDamageShieldChance','iArmorWeightBoots','iArmorWeightCuirass',
    'iArmorWeightGauntlets','iArmorWeightGreaves','iArmorWeightHelmet',
    'iArmorWeightShield','iArrestOnSightNonViolent','iArrestOnSightViolent',
    'iArrowMaxCount','iAttackOnSightNonViolent','iAttackOnSightViolent',
    'iAttractModeIdleTime','iAVDAutoCalcSkillMax','iAVDSkillStart',
    'iAvoidHurtingNonTargetsResponsibility','iBallisticProjectilePathPickSegments',
    'iBaseDisposition','iBoneLODDistMult','iClassAcrobat',
    'iClassAgent','iClassArcher',
    'iClassAssassin','iClassBarbarian','iClassBard',
    'iClassBattlemage','iClassCharactergenClass','iClassCrusader',
    'iClassHealer','iClassKnight','iClassMage',
    'iClassMonk','iClassNightblade','iClassPilgrim',
    'iClassPriest','iClassRogue','iClassScout',
    'iClassSorcerer','iClassSpellsword','iClassThief',
    'iClassWarrior','iClassWitchhunter','iCombatAimMaxIterations',
    'iCombatCastDrainMinimumValue','iCombatCrippledTorsoHitStaggerChance','iCombatFlankingAngleOffsetCount',
    'iCombatFlankingAngleOffsetGoalCount','iCombatFlankingDirectionOffsetCount','iCombatHighPriorityModifier',
    'iCombatHoverLocationCount','iCombatSearchDoorFailureMax','iCombatStealthPointSneakDetectionThreshold',
    'iCombatTargetLocationCount','iCombatTargetPlayerSoftCap','iCombatUnloadedActorLastSeenTimeLimit',
    'iCrimeAlarmLowRecDistance','iCrimeAlarmRecDistance','iCrimeCommentNumber',
    'iCrimeDaysInPrisonMod','iCrimeEnemyCoolDownTimer','iCrimeFavorBaseValue',
    'iCrimeGoldAttack','iCrimeGoldEscape','iCrimeGoldMinValue',
    'iCrimeGoldMurder','iCrimeGoldPickpocket','iCrimeGoldTrespass',
    'iCrimeMaxNumberofDaysinJail','iCrimeRegardBaseValue','iCrimeValueAttackValue',
    'iCurrentTargetBonus','iDebrisMaxCount','iDetectEventLightLevelExterior',
    'iDetectEventLightLevelInterior','iDialogueDispositionFriendValue','iDismemberBloodDecalCount',
    'iDispKaramMax','iDistancetoAttackedTarget','iFallLegDamageChance',
    'iFloraEmptyAlpha','iFloraFullAlpha','iFriendHitNonCombatAllowed',
    'iGameplayiSpeakingEmotionDeltaChange','iGameplayiSpeakingEmotionListenValue','iHairColor00',
    'iHairColor01','iHairColor02','iHairColor03',
    'iHairColor04','iHairColor05','iHairColor06',
    'iHairColor07','iHairColor08','iHairColor09',
    'iHairColor10','iHairColor11','iHairColor12',
    'iHairColor13','iHairColor14','iHairColor15',
    'iHorseTurnDegreesPerSecond','iHorseTurnDegreesRampUpPerSecond','iHoursToClearCorpses',
    'iInventoryAskQuantityAt','iKarmaMax','iKarmaMin',
    'iKillCamLevelOffset','iLargeProjectilePickCount','iLevCharLevelDifferenceMax',
    'iLevelUpReminder','iLevItemLevelDifferenceMax','iLightLevelExteriorMod',
    'iLockLevelMaxAverage','iLockLevelMaxEasy','iLockLevelMaxHard',
    'iLockLevelMaxImpossible','iLockLevelMaxVeryHard','iLowLevelNPCMaxLevel',
    'iMagicLightMaxCount','iMaxArrowsInQuiver','iMaxAttachedArrows',
    'iMaxCharacterLevel','iMaxSummonedCreatures','iMessageBoxMaxItems',
    'iMinClipSizeToAddReloadDelay','iMoodFaceValue','iNPCBasePerLevelHealthMult',
    'iNumberActorsAllowedToFollowPlayer','iNumberActorsGoThroughLoadDoorInCombat','iNumberActorsInCombatPlayer',
    'iNumberGuardsCrimeResponse','iNumExplosionDecalCDPoint','iPCStartSpellSkillLevel',
    'iPerkBlockStaggerChance','iPerkHandToHandBlockRecoilChance','iPerkHeavyArmorJumpSum',
    'iPerkHeavyArmorSinkSum','iPerkLightArmorMasterMinSum','iPerkMarksmanKnockdownChance',
    'iPerkMarksmanParalyzeChance','iPersuasionAngleMax','iPersuasionAngleMin',
    'iPersuasionBribeCrime','iPersuasionBribeGold','iPersuasionBribeRefuse',
    'iPersuasionBribeScale','iPersuasionDemandDisposition','iPersuasionDemandGold',
    'iPersuasionDemandRefuse','iPersuasionDemandScale','iPersuasionInner',
    'iPersuasionMiddle','iPersuasionOuter','iPersuasionPower1',
    'iPersuasionPower2','iPersuasionPower3','iPickPocketWarnings',
    'iPlayerCustomClass','iPlayerHealthHeartbeatFadeMS','iProjectileMaxRefCount',
    'iQuestReminderPipboyDisabledTime','iRegionGenClusterAttempts','iRegionGenClusterPasses',
    'iRegionGenRandomnessType','iRelationshipAcquaintanceValue','iRelationshipAllyValue',
    'iRelationshipArchnemesisValue','iRelationshipConfidantValue','iRelationshipEnemyValue',
    'iRelationshipFoeValue','iRelationshipFriendValue','iRelationshipLoverValue',
    'iRelationshipRivalValue','iRemoveExcessDeadComplexCount','iRemoveExcessDeadComplexTotalActorCount',
    'iRemoveExcessDeadTotalActorCount','iSecondsToSleepPerUpdate','iShockBranchNumBolts',
    'iShockBranchSegmentsPerBolt','iShockDebug','iShockNumBolts',
    'iShockSegmentsPerBolt','iShockSubSegments','iSkillPointsTagSkillMult',
    'iSkillUsageSneakFullDetection','iSkillUsageSneakMinDetection','iSneakSkillUseDistance',
    'iSoulLevelValueCommon','iSoulLevelValueGrand','iSoulLevelValueGreater',
    'iSoulLevelValueLesser','iSoulLevelValuePetty','iSoundLevelLoud',
    'iSoundLevelNormal','iSoundLevelVeryLoud','iSprayDecalsDebug',
    'iStandardEmotionValue','iStealWarnings','iTrainingExpertSkill',
    'iTrainingJourneymanCost','iTrainingJourneymanSkill','iTrainingMasterSkill',
    'iTrainingNumAllowedPerLevel','iTrespassWarnings','iUpdateESMVersion',
    'iVATSCameraHitDist','iVATSConcentratedFireBonus','iVoicePointsDefault',
    'iWeaponCriticalHitDropChance','iWortcraftMaxEffectsApprentice','iWortcraftMaxEffectsExpert',
    'iWortcraftMaxEffectsJourneyman','iWortcraftMaxEffectsMaster','iWortcraftMaxEffectsNovice',
    'iXPBase','iXPLevelHackComputerAverage','iXPLevelHackComputerEasy',
    'iXPLevelHackComputerHard','iXPLevelHackComputerVeryEasy','iXPLevelHackComputerVeryHard',
    'iXPLevelPickLockAverage','iXPLevelPickLockEasy','iXPLevelPickLockHard',
    'iXPLevelPickLockVeryEasy','iXPLevelPickLockVeryHard','iXPLevelSpeechChallengeAverage',
    'iXPLevelSpeechChallengeEasy','iXPLevelSpeechChallengeHard','iXPLevelSpeechChallengeVeryEasy',
    'iXPLevelSpeechChallengeVeryHard','iXPRewardDiscoverSecretArea','iXPRewardKillNPCAverage',
    'iXPRewardKillNPCEasy','iXPRewardKillNPCHard','iXPRewardKillNPCVeryEasy',
    'iXPRewardKillNPCVeryHard','iXPRewardKillOpponent','iXPRewardSpeechChallengeAverage',
    'iXPRewardSpeechChallengeEasy','iXPRewardSpeechChallengeHard','iXPRewardSpeechChallengeVeryHard',
    'sGenericCraftKeywordName01','sGenericCraftKeywordName02','sGenericCraftKeywordName03',
    'sGenericCraftKeywordName04','sGenericCraftKeywordName05','sGenericCraftKeywordName06',
    'sGenericCraftKeywordName07','sGenericCraftKeywordName08','sGenericCraftKeywordName09',
    'sGenericCraftKeywordName10','sInvalidTagString','sKinectAllyTooFarToTrade',
    'sKinectCantInit','sKinectNotCalibrated','sNoBolts',
    'sRSMFinishedWarning','sVerletCape','uiMuteMusicPauseTime',
    ]

#--GLOB record tweaks used by bosh's GmstTweaker
#  Each entry is a tuple in the following format:
#    (DisplayText, MouseoverText, GLOB EditorID, Option1, Option2, Option3, ..., OptionN)
#    -EditorID can be a plain string, or a tuple of multiple Editor IDs.  If it's a tuple,
#     then Value (below) must be a tuple of equal length, providing values for each GLOB
#  Each Option is a tuple:
#    (DisplayText, Value)
#    - If you enclose DisplayText in brackets like this: _(u'[Default]'), then the patcher
#      will treat this option as the default value.
#    - If you use _(u'Custom') as the entry, the patcher will bring up a number input dialog
#  To make a tweak Enabled by Default, enclose the tuple entry for the tweak in a list, and make
#  a dictionary as the second list item with {'defaultEnabled':True}.  See the UOP Vampire face
#  fix for an example of this (in the GMST Tweaks)
GlobalsTweaks = [
    (_(u'Timescale'),_(u'Timescale will be set to:'),
        u'timescale',
        (u'1',         1),
        (u'8',         8),
        (u'10',       10),
        (u'12',       12),
        (u'[20]',     20),
        (u'24',       24),
        (u'30',       30),
        (u'40',       40),
        (_(u'Custom'), 20),
        ),
    ]

#--GMST record tweaks used by bosh's GmstTweaker
#  Each entry is a tuple in the following format:
#    (DisplayText, MouseoverText, GMST EditorID, Option1, Option2, Option3, ..., OptionN)
#    -EditorID can be a plain string, or a tuple of multiple Editor IDs.  If it's a tuple,
#     then Value (below) must be a tuple of equal length, providing values for each GMST
#  Each Option is a tuple:
#    (DisplayText, Value)
#    - If you enclose DisplayText in brackets like this: _(u'[Default]'), then the patcher
#      will treat this option as the default value.
#    - If you use _(u'Custom') as the entry, the patcher will bring up a number input dialog
#  To make a tweak Enabled by Default, enclose the tuple entry for the tweak in a list, and make
#  a dictionary as the second list item with {'defaultEnabled':True}.  See the UOP Vampire face
#  fix for an example of this (in the GMST Tweaks)
GmstTweaks = [
    (_(u'Msg: Soul Captured!'),_(u'Message upon capturing a soul in a Soul Gem.'),
     u'sSoulCaptured',
     (_(u'[None]'),          u' '),
     (u'.',                  u'.'),
     (_(u'Custom'),       _(u' ')),
     ),
    (_(u'Actor Strength Encumbrance Multiplier'),_(u"Actor's Strength X this = Actor's Encumbrance capacity."),
        (u'fActorStrengthEncumbranceMult',),
        (u'1',                 1.0),
        (u'3',                 3.0),
        (u'[5]',               5.0),
        (u'8',                 8.0),
        (u'10',               10.0),
        (u'20',               20.0),
        (_(u'Unlimited'), 999999.0),
        (_(u'Custom'),         5.0),
        ),
    (_(u'AI: Max Active Actors'),_(u'Maximum actors whose AI can be active. Must be higher than Combat: Max Actors'),
        (u'iAINumberActorsComplexScene',),
        (u'[20]',               20),
        (u'25',                 25),
        (u'30',                 30),
        (u'35',                 35),
        (_(u'MMM Default: 40'), 40),
        (u'50',                 50),
        (u'60',                 60),
        (u'100',               100),
        (_(u'Custom'),          20),
        ),
    (_(u'Arrow: Recovery from Actor'),_(u'Chance that an arrow shot into an actor can be recovered.'),
        (u'iArrowInventoryChance',),
        (u'[33%]',     33),
        (u'50%',       50),
        (u'60%',       60),
        (u'70%',       70),
        (u'80%',       80),
        (u'90%',       90),
        (u'100%',     100),
        (_(u'Custom'), 33),
        ),
    (_(u'Arrow: Speed'),_(u'Speed of a full power arrow.'),
        (u'fArrowSpeedMult',),
        (u'[x 1.0]',                  1500.0),
        (u'x 1.2',                1500.0*1.2),
        (u'x 1.4',                1500.0*1.4),
        (u'x 1.6',                1500.0*1.6),
        (u'x 1.8',                1500.0*1.8),
        (u'x 2.0',                1500.0*2.0),
        (u'x 2.2',                1500.0*2.2),
        (u'x 2.4',                1500.0*2.4),
        (u'x 2.6',                1500.0*2.6),
        (u'x 2.8',                1500.0*2.8),
        (u'x 3.0',                1500.0*3.0),
        (_(u'Custom (base is 1500)'), 1500.0),
        ),
    (_(u'Cell: Respawn Time'),_(u'Time before unvisited cells respawn. Longer times increase save game size.'),
        (u'iHoursToRespawnCell',),
        (_(u'1 Day'),           24*1),
        (_(u'3 Days'),          24*3),
        (_(u'5 Days'),          24*5),
        (_(u'[10 Days]'),      24*10),
        (_(u'20 Days'),        24*20),
        (_(u'1 Month'),        24*30),
        (_(u'6 Months'),      24*182),
        (_(u'1 Year'),        24*365),
        (_(u'Custom (in hours)'), 240),
        ),
    (_(u'Cell: Respawn Time (Cleared)'),_(u'Time before a cleared cell will respawn. Longer times increase save game size.'),
        (u'iHoursToRespawnCellCleared',),
        (_(u'10 Days'),         24*10),
        (_(u'15 Days'),         24*15),
        (_(u'20 Days'),         24*20),
        (_(u'25 Days'),         24*25),
        (_(u'[30 Days]'),       24*30),
        (_(u'2 Months'),        24*60),
        (_(u'6 Months'),      24*180),
        (_(u'1 Year'),        24*365),
        (_(u'Custom (in hours)'), 720),
        ),
    (_(u'Combat: Alchemy'),_(u'Allow alchemy during combat.'),
        (u'iAllowAlchemyDuringCombat',),
        (_(u'Allow'),      1),
        (_(u'[Disallow]'), 0),
        ),
    (_(u'Combat: Max Actors'),_(u'Maximum number of actors that can actively be in combat with the player.'),
        (u'iNumberActorsInCombatPlayer',),
        (u'10',        10),
        (u'15',        15),
        (u'[20]',      20),
        (u'30',        30),
        (u'40',        40),
        (u'50',        50),
        (u'80',        80),
        (_(u'Custom'), 20),
        ),
    (_(u'Combat: Recharge Weapons'),_(u'Allow recharging weapons during combat.'),
        (u'iAllowRechargeDuringCombat',),
        (_(u'[Allow]'),  1),
        (_(u'Disallow'), 0),
        ),
    (_(u'Companions: Max Number'),_(u'Maximum number of actors following the player.'),
        (u'iNumberActorsAllowedToFollowPlayer',),
        (u'2',         2),
        (u'4',         4),
        (u'[6]',       6),
        (u'8',         8),
        (u'10',       10),
        (_(u'Custom'), 6),
        ),
    (_(u'Crime: Alarm Distance'),_(u'Distance from player that NPCs(guards) will be alerted of a crime.'),
        (u'iCrimeAlarmRecDistance',),
        (u'8000',      8000),
        (u'6000',      6000),
        (u'[4000]',    4000),
        (u'3000',      3000),
        (u'2000',      2000),
        (u'1000',      1000),
        (u'500',        500),
        (_(u'Custom'), 4000),
        ),
    (_(u'Crime: Assault Fine'),_(u'Fine in septims for committing an assault.'),
        (u'iCrimeGoldAttack',),
        (u'[40]',     40),
        (u'50',       50),
        (u'60',       60),
        (u'70',       70),
        (u'80',       80),
        (u'90',       90),
        (u'100',     100),
        (_(u'Custom'), 40),
        ),
    (_(u'Crime: Days in Prison'),_(u'Number of days to advance the calendar when serving prison time.'),
        (u'iCrimeDaysInPrisonMod',),
        (u'50',       50),
        (u'60',       60),
        (u'70',       70),
        (u'80',       80),
        (u'90',       90),
        (u'[100]',   100),
        (_(u'Custom'), 100),
        ),
    (_(u'Crime: Escape Jail'),_(u'Amount added to your bounty for escaping from jail.'),
        (u'iCrimeGoldEscape',),
        (u'[100]',   100),
        (u'125',     125),
        (u'150',     150),
        (u'175',     175),
        (u'200',     200),
        (_(u'Custom'), 100),
        ),
    (_(u'Crime: Murder Bounty'),_(u'Bounty for committing a witnessed murder.'),
        (u'iCrimeGoldMurder',),
        (u'500',      500),
        (u'750',      750),
        (u'[1000]',  1000),
        (u'1250',    1250),
        (u'1500',    1500),
        (_(u'Custom'), 1000),
        ),
    (_(u'Crime: Pickpocketing Fine'),_(u'Fine in septims for picpocketing.'),
        (u'iCrimeGoldPickpocket',),
        (u'5',          5),
        (u'8',          8),
        (u'10',        10),
        (u'[25]',      25),
        (u'50',        50),
        (u'100',      100),
        (_(u'Custom'), 25),
        ),
    (_(u'Crime: Trespassing Fine'),_(u'Fine in septims for trespassing.'),
        (u'iCrimeGoldTrespass',),
        (u'1',         1),
        (u'[5]',       5),
        (u'8',         8),
        (u'10',       10),
        (u'20',       20),
        (_(u'Custom'), 5),
        ),
    (_(u'Max Resistence'),_(u'Maximum level of resistence a player can have to various forms of magic and disease.'),
        (u'fPlayerMaxResistance',),
        (u'50%',       50),
        (u'60%',       60),
        (u'70%',       70),
        (u'80%',       80),
        (u'[85%]',     85),
        (u'90%',       90),
        (u'100%',     100),
        (_(u'Custom'), 85),
        ),
    (_(u'Max Summons'),_(u'Maximum number of allowed summoned creatures the player can call forth.'),
        (u'iMaxSummonedCreatures',),
        (u'[1]',              1),
        (u'2',                2),
        (u'3',                3),
        (u'4',                4),
        (u'5',                5),
        (_(u'Custom'),        1),
        ),
    (_(u'Max Training'),_(u'Maximum number of training sessions the player can have per level.'),
        (u'iTrainingNumAllowedPerLevel',),
        (u'3',         3),
        (u'4',         4),
        (u'[5]',       5),
        (u'8',         8),
        (u'10',       10),
        (_(u'Custom'), 5),
        ),
    (_(u'NPC Vertical Object Detection'),_(u'Change the vertical range in which NPCs detect objects. For custom values, fSandboxCylinderTop must be >= 0 and fSandboxCylinderBottom must be <= 0.'),
        (u'fSandboxCylinderTop',u'fSandboxCylinderBottom',),
        (u'[x 1.0]',   150,         -100),
        (u'x 2.0',     150*2.0, -100*2.0),
        (u'x 3.0',     150*3.0, -100*3.0),
        (u'x 4.0',     150*4.0, -100*4.0),
        (u'x 5.0',     150*5.0, -100*5.0),
        (_(u'Custom'), 150,         -100),
        ),
    ]

#--Tags supported by this game
allTags = sorted((u'Relev',u'Delev',u'Filter',u'NoMerge',u'Deactivate',u'Names',u'Stats'))

#--Gui patcher classes available when building a Bashed Patch
patchers = (
    u'AliasesPatcher', u'PatchMerger', u'ListsMerger', u'GmstTweaker',
    u'NamesPatcher', u'StatsPatcher'
    )

#--CBash Gui patcher classes available when building a Bashed Patch
CBash_patchers = tuple()

# For ListsMerger
listTypes = ('LVLI','LVLN','LVSP',)

namesTypes = {'ACTI', 'AMMO', 'ARMO', 'APPA', 'MISC',}
pricesTypes = {'AMMO':{},'ARMO':{},'APPA':{},'MISC':{}}
#-------------------------------------------------------------------------------
# StatsImporter
#-------------------------------------------------------------------------------
statsTypes = {
            'AMMO':('eid', 'value', 'damage'),
            'ARMO':('eid', 'weight', 'value', 'armorRating'),
            'APPA':('eid', 'weight', 'value'),
            'MISC':('eid', 'weight', 'value'),
            }
statsHeaders = (
                #--Ammo
                (u'AMMO',
                    (u'"' + u'","'.join((_(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
                    _(u'Editor Id'),_(u'Weight'),_(u'Value'))) + u'"\n')),
                #--Armo
                (u'ARMO',
                    (u'"' + u'","'.join((_(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
                    _(u'Editor Id'),_(u'Weight'),_(u'Value'),_('armorRating'))) + u'"\n')),
                (u'APPA',
                    (u'"' + u'","'.join((_(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
                    _(u'Editor Id'),_(u'Weight'),_(u'Value'))) + u'"\n')),
                (u'MISC',
                    (u'"' + u'","'.join((_(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
                    _(u'Editor Id'),_(u'Weight'),_(u'Value'))) + u'"\n')),
                )

# Mod Record Elements ----------------------------------------------------------
#-------------------------------------------------------------------------------
# Constants
FID = 'FID' #--Used by MelStruct classes to indicate fid elements.

# Magic Info ------------------------------------------------------------------
weaponTypes = (
    _(u'Blade (1 Handed)'),
    _(u'Blade (2 Handed)'),
    _(u'Blunt (1 Handed)'),
    _(u'Blunt (2 Handed)'),
    _(u'Staff'),
    _(u'Bow'),
    )

# Race Info -------------------------------------------------------------------
raceNames = {
    0x13740 : _(u'Argonian'),
    0x13741 : _(u'Breton'),
    0x13742 : _(u'Dark Elf'),
    0x13743 : _(u'High Elf'),
    0x13744 : _(u'Imperial'),
    0x13745 : _(u'Khajiit'),
    0x13746 : _(u'Nord'),
    0x13747 : _(u'Orc'),
    0x13748 : _(u'Redguard'),
    0x13749 : _(u'Wood Elf'),
    }

raceShortNames = {
    0x13740 : u'Arg',
    0x13741 : u'Bre',
    0x13742 : u'Dun',
    0x13743 : u'Alt',
    0x13744 : u'Imp',
    0x13745 : u'Kha',
    0x13746 : u'Nor',
    0x13747 : u'Orc',
    0x13748 : u'Red',
    0x13749 : u'Bos',
    }

raceHairMale = {
    0x13740 : 0x64f32, #--Arg
    0x13741 : 0x90475, #--Bre
    0x13742 : 0x64214, #--Dun
    0x13743 : 0x7b792, #--Alt
    0x13744 : 0x90475, #--Imp
    0x13745 : 0x653d4, #--Kha
    0x13746 : 0x1da82, #--Nor
    0x13747 : 0x66a27, #--Orc
    0x13748 : 0x64215, #--Red
    0x13749 : 0x690bc, #--Bos
    }

raceHairFemale = {
    0x13740 : 0x64f33, #--Arg
    0x13741 : 0x1da83, #--Bre
    0x13742 : 0x1da83, #--Dun
    0x13743 : 0x690c2, #--Alt
    0x13744 : 0x1da83, #--Imp
    0x13745 : 0x653d0, #--Kha
    0x13746 : 0x1da83, #--Nor
    0x13747 : 0x64218, #--Orc
    0x13748 : 0x64210, #--Red
    0x13749 : 0x69473, #--Bos
    }

#--Plugin format stuff
class esp:
    #--Wrye Bash capabilities
    canBash = True          # Can create Bashed Patches
    canCBash = False        # CBash can handle this game's records
    canEditHeader = True    # Can edit anything in the TES4 record

    #--Valid ESM/ESP header versions
    validHeaderVersions = (0.94, 1.70,)

    #--Strings Files
    stringsFiles = [
        ('mods',(u'Strings',),u'%(body)s_%(language)s.STRINGS'),
        ('mods',(u'Strings',),u'%(body)s_%(language)s.DLSTRINGS'),
        ('mods',(u'Strings',),u'%(body)s_%(language)s.ILSTRINGS'),
        ]

    #--Top types in Skyrim order.
    topTypes = ['GMST', 'KYWD', 'LCRT', 'AACT', 'TXST', 'GLOB', 'CLAS', 'FACT', 'HDPT',
                'HAIR', 'EYES', 'RACE', 'SOUN', 'ASPC', 'MGEF', 'SCPT', 'LTEX', 'ENCH',
                'SPEL', 'SCRL', 'ACTI', 'TACT', 'ARMO', 'BOOK', 'CONT', 'DOOR', 'INGR',
                'LIGH', 'MISC', 'APPA', 'STAT', 'SCOL', 'MSTT', 'PWAT', 'GRAS', 'TREE',
                'CLDC', 'FLOR', 'FURN', 'WEAP', 'AMMO', 'NPC_', 'LVLN', 'KEYM', 'ALCH',
                'IDLM', 'COBJ', 'PROJ', 'HAZD', 'SLGM', 'LVLI', 'WTHR', 'CLMT', 'SPGD',
                'RFCT', 'REGN', 'NAVI', 'CELL', 'WRLD', 'DIAL', 'QUST', 'IDLE', 'PACK',
                'CSTY', 'LSCR', 'LVSP', 'ANIO', 'WATR', 'EFSH', 'EXPL', 'DEBR', 'IMGS',
                'IMAD', 'FLST', 'PERK', 'BPTD', 'ADDN', 'AVIF', 'CAMS', 'CPTH', 'VTYP',
                'MATT', 'IPCT', 'IPDS', 'ARMA', 'ECZN', 'LCTN', 'MESG', 'RGDL', 'DOBJ',
                'LGTM', 'MUSC', 'FSTP', 'FSTS', 'SMBN', 'SMQN', 'SMEN', 'DLBR', 'MUST',
                'DLVW', 'WOOP', 'SHOU', 'EQUP', 'RELA', 'SCEN', 'ASTP', 'OTFT', 'ARTO',
                'MATO', 'MOVT', 'SNDR', 'DUAL', 'SNCT', 'SOPM', 'COLL', 'CLFM', 'REVB',]

    #--Dict mapping 'ignored' top types to un-ignored top types.
    topIgTypes = dict([(struct.pack('I',(struct.unpack('I',type)[0]) | 0x1000),type) for type in topTypes])

    #-> this needs updating for Skyrim
    recordTypes = set(topTypes + 'GRUP,TES4,REFR,ACHR,ACRE,LAND,INFO,NAVM,PHZD,PGRE'.split(','))

#------------------------------------------------------------------------------
from records import * # MUST BE HERE otherwise all hell breaks loose
#------------------------------------------------------------------------------
# Unused records, they have empty GRUP in skyrim.esm---------------------------
# CLDC ------------------------------------------------------------------------
#------------------------------------------------------------------------------
# Unused records, they have empty GRUP in skyrim.esm---------------------------
# HAIR ------------------------------------------------------------------------
#------------------------------------------------------------------------------
# Unused records, they have empty GRUP in skyrim.esm---------------------------
# PWAT ------------------------------------------------------------------------
#------------------------------------------------------------------------------
# Unused records, they have empty GRUP in skyrim.esm---------------------------
# RGDL ------------------------------------------------------------------------
#------------------------------------------------------------------------------
# Unused records, they have empty GRUP in skyrim.esm---------------------------
# SCOL ------------------------------------------------------------------------
#------------------------------------------------------------------------------
# Unused records, they have empty GRUP in skyrim.esm---------------------------
# SCPT ------------------------------------------------------------------------
#------------------------------------------------------------------------------
# These Are normally not mergable but added to brec.MreRecord.type_class
#
#       MreCell,
#------------------------------------------------------------------------------
# These have undefined FormIDs Do not merge them
#
#       MreNavi, MreNavm,
#------------------------------------------------------------------------------
# These need syntax revision but can be merged once that is corrected
#
#       MreAchr, MreDial, MreLctn, MreInfo, MreFact, MrePerk,
#------------------------------------------------------------------------------
#--Mergeable record types
mergeClasses = (
        MreAact, MreActi, MreAddn, MreAmmo, MreAnio, MreAppa, MreArma, MreArmo,
        MreArto, MreAspc, MreAstp, MreCobj, MreGlob, MreGmst, MreLvli, MreLvln,
        MreLvsp, MreMisc,
    )

#--Extra read classes: these record types will always be loaded, even if
# patchers don't need them directly (for example, MGEF for magic effects info)
# MreScpt is Oblivion/FO3/FNV Only
# MreMgef, has not been verified to be used here for Skyrim
readClasses = ()
writeClasses = ()

def init():
    # Due to a bug with py2exe, 'reload' doesn't function properly.  Instead of
    # re-executing all lines within the module, it acts like another 'import'
    # statement - in otherwords, nothing happens.  This means any lines that
    # affect outside modules must do so within this function, which will be
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
    brec.MreRecord.simpleTypes = (
        set(brec.MreRecord.type_class) - {'TES4',})

