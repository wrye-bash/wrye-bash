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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from os.path import join as _j

from .. import WS_COMMON_FILES, GameInfo
from ..gog_game import GOGMixin
from ..patch_game import PatchGame
from ..windows_store_game import WindowsStoreMixin
from ...bolt import DefaultFNDict, FName, classproperty

_GOG_IDS = [1454315831]

class Fallout3GameInfo(PatchGame):
    """GameInfo override for Fallout 3."""
    displayName = u'Fallout 3'
    fsName = u'Fallout3'
    altName = u'Wrye Flash'
    game_icon = u'fallout3_%u.png'
    bash_root_prefix = u'Fallout3'
    bak_game_name = u'Fallout3'
    template_dir = u'Fallout3'
    my_games_name = u'Fallout3'
    appdata_name = u'Fallout3'
    launch_exe = u'Fallout3.exe'
    game_detect_includes = {'Fallout3.exe'}
    game_detect_excludes = (set(GOGMixin.get_unique_filenames(_GOG_IDS)) |
                            WS_COMMON_FILES | {'FalloutLauncherEpic.exe'})
    version_detect_file = u'Fallout3.exe'
    master_file = FName('Fallout3.esm')
    taglist_dir = u'Fallout3'
    loot_dir = u'Fallout3'
    loot_game_name = 'Fallout3'
    boss_game_name = u'Fallout3'
    registry_keys = [(r'Bethesda Softworks\Fallout3', 'Installed Path')]
    nexusUrl = u'https://www.nexusmods.com/fallout3/'
    nexusName = u'Fallout 3 Nexus'
    nexusKey = u'bash.installers.openFallout3Nexus.continue'

    using_txt_file = False
    plugin_name_specific_dirs = GameInfo.plugin_name_specific_dirs + [
        _j('textures', 'characters', 'bodymods'),
        _j('textures', 'characters', 'facemods'),
    ]

    class Ck(GameInfo.Ck):
        ck_abbrev = u'GECK'
        long_name = u'Garden of Eden Creation Kit'
        exe = u'GECK.exe'
        se_args = u'-editor'
        image_name = u'geck%s.png'

    class Se(GameInfo.Se):
        se_abbrev = u'FOSE'
        long_name = u'Fallout 3 Script Extender'
        exe = u'fose_loader.exe'
        # There is no fose_steam_loader.dll, so we have to list all included
        # DLLs, since people could delete any DLL not matching the game version
        # they're using
        ver_files = [u'fose_loader.exe', u'fose_1_7ng.dll', u'fose_1_7.dll',
                     u'fose_1_6.dll', u'fose_1_5.dll', u'fose_1_4b.dll',
                     u'fose_1_4.dll', u'fose_1_1.dll', u'fose_1_0.dll']
        plugin_dir = u'FOSE'
        cosave_tag = u'FOSE'
        cosave_ext = u'.fose'
        url = u'http://fose.silverlock.org/'
        url_tip = u'http://fose.silverlock.org/'
        limit_fixer_plugins = [u'mod_limit_fix.dll']

    class Ini(GameInfo.Ini):
        allow_new_lines = False
        bsa_redirection_key = (u'Archive', u'sArchiveList')
        default_ini_file = u'Fallout_default.ini'
        dropdown_inis = [u'Fallout.ini', u'FalloutPrefs.ini']
        supports_mod_inis = False

    class Ess(GameInfo.Ess):
        can_safely_remove_masters = True
        ext = '.fos'

    class Bsa(GameInfo.Bsa):
        allow_reset_timestamps = True
        redate_dict = DefaultFNDict(lambda: 1136066400, { # '2006-01-01'
            'Fallout - MenuVoices.bsa': 1104530400,  # '2005-01-01',
            'Fallout - Meshes.bsa': 1104616800,      # '2005-01-02',
            'Fallout - Misc.bsa': 1104703200,        # '2005-01-03',
            'Fallout - Sound.bsa': 1104789600,       # '2005-01-04',
            'Fallout - Textures.bsa': 1104876000,    # '2005-01-05',
            'Fallout - Voices.bsa': 1104962400,      # '2005-01-06',
        })
        # ArchiveInvalidation Invalidated, which we shipped unmodified for a
        # long time, uses an Oblivion BSA with version 0x67, so we have to
        # accept those here as well
        valid_versions = {0x67, 0x68}

    class Xe(GameInfo.Xe):
        full_name = u'FO3Edit'
        xe_key_prefix = u'fo3View'

    class Bain(GameInfo.Bain):
        data_dirs = GameInfo.Bain.data_dirs | {
            'config', # 3P: mod config files (INIs)
            'distantlod',
            'docs',
            'facegen',
            'fonts',
            'fose', # 3P: FOSE
            'menus',
            'uio', # 3P: User Interface Organizer
            'scripts',
            'shaders',
            'trees',
        }
        keep_data_dirs = {'lsdata'}
        keep_data_files = {'fallout - ai!.bsa'}
        lod_meshes_dir = _j('meshes', 'landscape', 'lod')
        lod_textures_dir = _j('textures', 'landscape', 'lod')
        no_skip = GameInfo.Bain.no_skip | {
            # 3P: UIO - User Interface Organizer
            _j('uio', 'private', 'menus_list.txt'),
            _j('uio', 'private', 'supported.txt'),
        }
        no_skip_dirs = GameInfo.Bain.no_skip_dirs | {
            _j('uio', 'public'): {'.txt'}, # 3P: UIO - User Interface Organizer
        }
        skip_bain_refresh = {'fo3edit backups', 'fo3edit cache'}
        wrye_bash_data_files = {'archiveinvalidationinvalidated!.bsa'}

    class Esp(GameInfo.Esp):
        canBash = True
        canEditHeader = True
        generate_temp_child_onam = True
        stringsFiles = []
        validHeaderVersions = (0.85, 0.94)

    allTags = PatchGame.allTags | {'NoMerge'}
    patchers = {
        'AliasPluginNames', 'ContentsChecker', 'FormIDLists', 'ImportActors',
        'ImportActorsAIPackages', 'ImportActorsFaces', 'ImportActorsFactions',
        'ImportActorsSpells', 'ImportCells', 'ImportDestructible',
        'ImportEffectStats', 'ImportEnchantments', 'ImportEnchantmentStats',
        'ImportGraphics', 'ImportInventory', 'ImportNames',
        'ImportObjectBounds', 'ImportRaces', 'ImportRacesRelations',
        'ImportRelations', 'ImportScripts', 'ImportSounds', 'ImportSpellStats',
        'ImportStats', 'ImportText', 'LeveledLists', 'MergePatches',
        'NpcChecker', 'RaceChecker', 'TimescaleChecker', 'TweakActors',
        'TweakAssorted', 'TweakNames', 'TweakRaces', 'TweakSettings',
    }

    weaponTypes = (
        _(u'Big gun'),
        _(u'Energy'),
        _(u'Small gun'),
        _(u'Melee'),
        _(u'Unarmed'),
        _(u'Thrown'),
        _(u'Mine'),
        )

    raceNames = {
        0x000019: _('Caucasian'),
        0x0038e5: _('Hispanic'),
        0x0038e6: _('Asian'),
        0x003b3e: _('Ghoul'),
        0x00424a: _('AfricanAmerican'),
        0x0042be: _('AfricanAmerican Child'),
        0x0042bf: _('AfricanAmerican Old'),
        0x0042c0: _('Asian Child'),
        0x0042c1: _('Asian Old'),
        0x0042c2: _('Caucasian Child'),
        0x0042c3: _('Caucasian Old'),
        0x0042c4: _('Hispanic Child'),
        0x0042c5: _('Hispanic Old'),
        0x04bb8d: _('Caucasian Raider'),
        0x04bf70: _('Hispanic Raider'),
        0x04bf71: _('Asian Raider'),
        0x04bf72: _('AfricanAmerican Raider'),
        0x0987dc: _('Hispanic Old Aged'),
        0x0987dd: _('Asian Old Aged'),
        0x0987de: _('AfricanAmerican Old Aged'),
        0x0987df: _('Caucasian Old Aged'),
   }

    raceShortNames = {
        0x000019: 'Cau',
        0x0038e5: 'His',
        0x0038e6: 'Asi',
        0x003b3e: 'Gho',
        0x00424a: 'Afr',
        0x0042be: 'AfC',
        0x0042bf: 'AfO',
        0x0042c0: 'AsC',
        0x0042c1: 'AsO',
        0x0042c2: 'CaC',
        0x0042c3: 'CaO',
        0x0042c4: 'HiC',
        0x0042c5: 'HiO',
        0x04bb8d: 'CaR',
        0x04bf70: 'HiR',
        0x04bf71: 'AsR',
        0x04bf72: 'AfR',
        0x0987dc: 'HOA',
        0x0987dd: 'AOA',
        0x0987de: 'FOA',
        0x0987df: 'COA',
    }

    raceHairMale = {
        0x000019: 0x014b90, #--Cau
        0x0038e5: 0x0a9d6f, #--His
        0x0038e6: 0x014b90, #--Asi
        0x003b3e: None, #--Gho
        0x00424a: 0x0306be, #--Afr
        0x0042be: 0x060232, #--AfC
        0x0042bf: 0x0306be, #--AfO
        0x0042c0: 0x060232, #--AsC
        0x0042c1: 0x014b90, #--AsO
        0x0042c2: 0x060232, #--CaC
        0x0042c3: 0x02bfdb, #--CaO
        0x0042c4: 0x060232, #--HiC
        0x0042c5: 0x02ddee, #--HiO
        0x04bb8d: 0x02bfdb, #--CaR
        0x04bf70: 0x02bfdb, #--HiR
        0x04bf71: 0x02bfdb, #--AsR
        0x04bf72: 0x0306be, #--AfR
        0x0987dc: 0x0987da, #--HOA
        0x0987dd: 0x0987da, #--AOA
        0x0987de: 0x0987d9, #--FOA
        0x0987df: 0x0987da, #--COA
    }

    raceHairFemale = {
        0x000019 : 0x05dc6b, #--Cau
        0x0038e5 : 0x05dc76, #--His
        0x0038e6 : 0x022e50, #--Asi
        0x003b3e : None, #--Gho
        0x00424a : 0x05dc78, #--Afr
        0x0042be : 0x05a59e, #--AfC
        0x0042bf : 0x072e39, #--AfO
        0x0042c0 : 0x05a5a3, #--AsC
        0x0042c1 : 0x072e39, #--AsO
        0x0042c2 : 0x05a59e, #--CaC
        0x0042c3 : 0x072e39, #--CaO
        0x0042c4 : 0x05a59e, #--HiC
        0x0042c5 : 0x072e39, #--HiO
        0x04bb8d : 0x072e39, #--CaR
        0x04bf70 : 0x072e39, #--HiR
        0x04bf71 : 0x072e39, #--AsR
        0x04bf72 : 0x072e39, #--AfR
        0x0987dc : 0x044529, #--HOA
        0x0987dd : 0x044529, #--AOA
        0x0987de : 0x044529, #--FOA
        0x0987df : 0x044529, #--COA
    }

    bethDataFiles = {
        'anchorage - main.bsa',
        'anchorage - sounds.bsa',
        'anchorage.esm',
        'brokensteel - main.bsa',
        'brokensteel - sounds.bsa',
        'brokensteel.esm',
        'fallout - menuvoices.bsa',
        'fallout - meshes.bsa',
        'fallout - misc.bsa',
        'fallout - sound.bsa',
        'fallout - textures.bsa',
        'fallout - voices.bsa',
        'fallout3.esm',
        'pointlookout - main.bsa',
        'pointlookout - sounds.bsa',
        'pointlookout.esm',
        'thepitt - main.bsa',
        'thepitt - sounds.bsa',
        'thepitt.esm',
        'zeta - main.bsa',
        'zeta - sounds.bsa',
        'zeta.esm',
    }

    # Function Info -----------------------------------------------------------
    # 0: no param; 1: int param; 2: FormID param; 3: float param
    condition_function_data = {
        1:    ('GetDistance', 2, 0),
        5:    ('GetLocked', 0, 0),
        6:    ('GetPos', 0, 0),
        8:    ('GetAngle', 0, 0),
        10:   ('GetStartingPos', 0, 0),
        11:   ('GetStartingAngle', 0, 0),
        12:   ('GetSecondsPassed', 0, 0),
        14:   ('GetActorValue', 2, 0),
        18:   ('GetCurrentTime', 0, 0),
        24:   ('GetScale', 0, 0),
        25:   ('IsMoving', 0, 0),
        26:   ('IsTurning', 0, 0),
        27:   ('GetLineOfSight', 2, 0),
        32:   ('GetInSameCell', 2, 0),
        35:   ('GetDisabled', 0, 0),
        36:   ('MenuMode', 1, 0),
        39:   ('GetDisease', 0, 0),
        40:   ('GetVampire', 0, 0),
        41:   ('GetClothingValue', 0, 0),
        42:   ('SameFaction', 2, 0),
        43:   ('SameRace', 2, 0),
        44:   ('SameSex', 2, 0),
        45:   ('GetDetected', 2, 0),
        46:   ('GetDead', 0, 0),
        47:   ('GetItemCount', 2, 0),
        48:   ('GetGold', 0, 0),
        49:   ('GetSleeping', 0, 0),
        50:   ('GetTalkedToPC', 0, 0),
        53:   ('GetScriptVariable', 2, 0),
        56:   ('GetQuestRunning', 2, 0),
        58:   ('GetStage', 2, 0),
        59:   ('GetStageDone', 2, 1),
        60:   ('GetFactionRankDifference', 2, 2),
        61:   ('GetAlarmed', 0, 0),
        62:   ('IsRaining', 0, 0),
        63:   ('GetAttacked', 0, 0),
        64:   ('GetIsCreature', 0, 0),
        65:   ('GetLockLevel', 0, 0),
        66:   ('GetShouldAttack', 2, 0),
        67:   ('GetInCell', 2, 0),
        68:   ('GetIsClass', 2, 0),
        69:   ('GetIsRace', 2, 0),
        70:   ('GetIsSex', 1, 0),
        71:   ('GetInFaction', 2, 0),
        72:   ('GetIsID', 2, 0),
        73:   ('GetFactionRank', 2, 0),
        74:   ('GetGlobalValue', 2, 0),
        75:   ('IsSnowing', 0, 0),
        76:   ('GetDisposition', 2, 0),
        77:   ('GetRandomPercent', 0, 0),
        79:   ('GetQuestVariable', 2, 0),
        80:   ('GetLevel', 0, 0),
        81:   ('GetArmorRating', 0, 0),
        84:   ('GetDeadCount', 2, 0),
        91:   ('GetIsAlerted', 0, 0),
        98:   ('GetPlayerControlsDisabled', 1, 1),
        99:   ('GetHeadingAngle', 2, 0),
        101:  ('IsWeaponOut', 0, 0),
        102:  ('IsTorchOut', 0, 0),
        103:  ('IsShieldOut', 0, 0),
        106:  ('IsFacingUp', 0, 0),
        107:  ('GetKnockedState', 0, 0),
        108:  ('GetWeaponAnimType', 0, 0),
        109:  ('IsWeaponSkillType', 2, 0),
        110:  ('GetCurrentAIPackage', 0, 0),
        111:  ('IsWaiting', 0, 0),
        112:  ('IsIdlePlaying', 0, 0),
        116:  ('GetMinorCrimeCount', 0, 0),
        117:  ('GetMajorCrimeCount', 0, 0),
        118:  ('GetActorAggroRadiusViolated', 0, 0),
        122:  ('GetCrime', 2, 1),
        123:  ('IsGreetingPlayer', 0, 0),
        125:  ('IsGuard', 0, 0),
        127:  ('HasBeenEaten', 0, 0),
        128:  ('GetFatiguePercentage', 0, 0),
        129:  ('GetPCIsClass', 2, 0),
        130:  ('GetPCIsRace', 2, 0),
        131:  ('GetPCIsSex', 1, 0),
        132:  ('GetPCInFaction', 2, 0),
        133:  ('SameFactionAsPC', 0, 0),
        134:  ('SameRaceAsPC', 0, 0),
        135:  ('SameSexAsPC', 0, 0),
        136:  ('GetIsReference', 2, 0),
        141:  ('IsTalking', 0, 0),
        142:  ('GetWalkSpeed', 0, 0),
        143:  ('GetCurrentAIProcedure', 0, 0),
        144:  ('GetTrespassWarningLevel', 0, 0),
        145:  ('IsTrespassing', 0, 0),
        146:  ('IsInMyOwnedCell', 0, 0),
        147:  ('GetWindSpeed', 0, 0),
        148:  ('GetCurrentWeatherPercent', 0, 0),
        149:  ('GetIsCurrentWeather', 2, 0),
        150:  ('IsContinuingPackagePCNear', 0, 0),
        153:  ('CanHaveFlames', 0, 0),
        154:  ('HasFlames', 0, 0),
        157:  ('GetOpenState', 0, 0),
        159:  ('GetSitting', 0, 0),
        160:  ('GetFurnitureMarkerID', 0, 0),
        161:  ('GetIsCurrentPackage', 2, 0),
        162:  ('IsCurrentFurnitureRef', 2, 0),
        163:  ('IsCurrentFurnitureObj', 2, 0),
        170:  ('GetDayOfWeek', 0, 0),
        172:  ('GetTalkedToPCParam', 2, 0),
        175:  ('IsPCSleeping', 0, 0),
        176:  ('IsPCAMurderer', 0, 0),
        180:  ('GetDetectionLevel', 2, 0),
        182:  ('GetEquipped', 2, 0),
        185:  ('IsSwimming', 0, 0),
        190:  ('GetAmountSoldStolen', 0, 0),
        192:  ('GetIgnoreCrime', 0, 0),
        193:  ('GetPCExpelled', 2, 0),
        195:  ('GetPCFactionMurder', 2, 0),
        197:  ('GetPCEnemyofFaction', 2, 0),
        199:  ('GetPCFactionAttack', 2, 0),
        203:  ('GetDestroyed', 0, 0),
        214:  ('HasMagicEffect', 2, 0),
        215:  ('GetDefaultOpen', 0, 0),
        219:  ('GetAnimAction', 0, 0),
        223:  ('IsSpellTarget', 2, 0),
        224:  ('GetVATSMode', 0, 0),
        225:  ('GetPersuasionNumber', 0, 0),
        226:  ('GetSandman', 0, 0),
        227:  ('GetCannibal', 0, 0),
        228:  ('GetIsClassDefault', 2, 0),
        229:  ('GetClassDefaultMatch', 0, 0),
        230:  ('GetInCellParam', 2, 2),
        235:  ('GetVatsTargetHeight', 0, 0),
        237:  ('GetIsGhost', 0, 0),
        242:  ('GetUnconscious', 0, 0),
        244:  ('GetRestrained', 0, 0),
        246:  ('GetIsUsedItem', 2, 0),
        247:  ('GetIsUsedItemType', 2, 0),
        254:  ('GetIsPlayableRace', 0, 0),
        255:  ('GetOffersServicesNow', 0, 0),
        258:  ('GetUsedItemLevel', 0, 0),
        259:  ('GetUsedItemActivate', 0, 0),
        264:  ('GetBarterGold', 0, 0),
        265:  ('IsTimePassing', 0, 0),
        266:  ('IsPleasant', 0, 0),
        267:  ('IsCloudy', 0, 0),
        274:  ('GetArmorRatingUpperBody', 0, 0),
        277:  ('GetBaseActorValue', 2, 0),
        278:  ('IsOwner', 2, 0),
        280:  ('IsCellOwner', 2, 2),
        282:  ('IsHorseStolen', 0, 0),
        285:  ('IsLeftUp', 0, 0),
        286:  ('IsSneaking', 0, 0),
        287:  ('IsRunning', 0, 0),
        288:  ('GetFriendHit', 0, 0),
        289:  ('IsInCombat', 0, 0),
        300:  ('IsInInterior', 0, 0),
        304:  ('IsWaterObject', 0, 0),
        306:  ('IsActorUsingATorch', 0, 0),
        309:  ('IsXBox', 0, 0),
        310:  ('GetInWorldspace', 2, 0),
        312:  ('GetPCMiscStat', 0, 0),
        313:  ('IsActorEvil', 0, 0),
        314:  ('IsActorAVictim', 0, 0),
        315:  ('GetTotalPersuasionNumber', 0, 0),
        318:  ('GetIdleDoneOnce', 0, 0),
        320:  ('GetNoRumors', 0, 0),
        323:  ('WhichServiceMenu', 0, 0),
        327:  ('IsRidingHorse', 0, 0),
        332:  ('IsInDangerousWater', 0, 0),
        338:  ('GetIgnoreFriendlyHits', 0, 0),
        339:  ('IsPlayersLastRiddenHorse', 0, 0),
        353:  ('IsActor', 0, 0),
        354:  ('IsEssential', 0, 0),
        358:  ('IsPlayerMovingIntoNewSpace', 0, 0),
        361:  ('GetTimeDead', 0, 0),
        362:  ('GetPlayerHasLastRiddenHorse', 0, 0),
        365:  ('IsChild', 0, 0),
        367:  ('GetLastPlayerAction', 0, 0),
        368:  ('IsPlayerActionActive', 1, 0),
        370:  ('IsTalkingActivatorActor', 2, 0),
        372:  ('IsInList', 2, 0),
        382:  ('GetHasNote', 2, 0),
        391:  ('GetHitLocation', 0, 0),
        392:  ('IsPC1stPerson', 0, 0),
        397:  ('GetCauseofDeath', 0, 0),
        398:  ('IsLimbGone', 1, 0),
        399:  ('IsWeaponInList', 2, 0),
        403:  ('HasFriendDisposition', 0, 0),
        # We set the second to 'unused' here to receive it as 4 bytes, which we
        # then handle inside _MelCtdaFo3.
        408:  ('GetVATSValue', 1, 0),
        409:  ('IsKiller', 2, 0),
        410:  ('IsKillerObject', 2, 0),
        411:  ('GetFactionCombatReaction', 2, 2),
        415:  ('Exists', 2, 0),
        416:  ('GetGroupMemberCount', 0, 0),
        417:  ('GetGroupTargetCount', 0, 0),
        427:  ('GetIsVoiceType', 0, 0),
        428:  ('GetPlantedExplosive', 0, 0),
        430:  ('IsActorTalkingThroughActivator', 0, 0),
        431:  ('GetHealthPercentage', 0, 0),
        433:  ('GetIsObjectType', 2, 0),
        435:  ('GetDialogueEmotion', 0, 0),
        436:  ('GetDialogueEmotionValue', 0, 0),
        438:  ('GetIsCreatureType', 1, 0),
        446:  ('GetInZone', 2, 0),
        449:  ('HasPerk', 2, 0),
        450:  ('GetFactionRelation', 2, 0),
        451:  ('IsLastIdlePlayed', 2, 0),
        454:  ('GetPlayerTeammate', 0, 0),
        455:  ('GetPlayerTeammateCount', 0, 0),
        459:  ('GetActorCrimePlayerEnemy', 0, 0),
        460:  ('GetActorFactionPlayerEnemy', 0, 0),
        464:  ('IsPlayerGrabbedRef', 2, 0),
        471:  ('GetDestructionStage', 0, 0),
        474:  ('GetIsAlignment', 1, 0),
        478:  ('GetThreatRatio', 2, 0),
        480:  ('GetIsUsedItemEquipType', 1, 0),
        489:  ('GetConcussed', 0, 0),
        492:  ('GetMapMarkerVisible', 0, 0),
        495:  ('GetPermanentActorValue', 2, 0),
        496:  ('GetKillingBlowLimb', 0, 0),
        500:  ('GetWeaponHealthPerc', 0, 0),
        503:  ('GetRadiationLevel', 0, 0),
        510:  ('GetLastHitCritical', 0, 0),
        515:  ('IsCombatTarget', 2, 0),
        518:  ('GetVATSRightAreaFree', 2, 0),
        519:  ('GetVATSLeftAreaFree', 2, 0),
        520:  ('GetVATSBackAreaFree', 2, 0),
        521:  ('GetVATSFrontAreaFree', 2, 0),
        522:  ('GetIsLockBroken', 0, 0),
        523:  ('IsPS3', 0, 0),
        524:  ('IsWin32', 0, 0),
        525:  ('GetVATSRightTargetVisible', 2, 0),
        526:  ('GetVATSLeftTargetVisible', 2, 0),
        527:  ('GetVATSBackTargetVisible', 2, 0),
        528:  ('GetVATSFrontTargetVisible', 2, 0),
        531:  ('IsInCriticalStage', 1, 0),
        533:  ('GetXPForNextLevel', 0, 0),
        546:  ('GetQuestCompleted', 2, 0),
        550:  ('IsGoreDisabled', 0, 0),
        555:  ('GetSpellUsageNum', 2, 0),
        557:  ('GetActorsInHigh', 0, 0),
        558:  ('HasLoaded3D', 0, 0),
        # extended by FOSE
        1024: ('GetFOSEVersion', 0, 0),
        1025: ('GetFOSERevision', 0, 0),
        1028: ('GetWeight', 2, 0),
        1082: ('IsKeyPressed', 1, 0),
        1165: ('GetWeaponHasScope', 2, 0),
        1166: ('IsControlPressed', 1, 0),
        1213: ('GetFOSEBeta', 0, 0),
    }
    getvatsvalue_index = 408

    #--------------------------------------------------------------------------
    # Leveled Lists
    #--------------------------------------------------------------------------
    leveled_list_types = {b'LVLC', b'LVLI', b'LVLN'}

    #--------------------------------------------------------------------------
    # Import Names
    #--------------------------------------------------------------------------
    names_types = {
        b'ACTI', b'ALCH', b'AMMO', b'ARMO', b'AVIF', b'BOOK', b'CLAS', b'COBJ',
        b'CONT', b'CREA', b'DOOR', b'ENCH', b'EYES', b'FACT', b'HAIR', b'INGR',
        b'KEYM', b'LIGH', b'MESG', b'MGEF', b'MISC', b'NOTE', b'NPC_', b'PERK',
        b'QUST', b'RACE', b'SPEL', b'TACT', b'TERM', b'WEAP',
    }

    #--------------------------------------------------------------------------
    # Import Prices
    #--------------------------------------------------------------------------
    pricesTypes = {b'ALCH', b'AMMO', b'ARMA', b'ARMO', b'BOOK', b'INGR',
                   b'KEYM', b'LIGH', b'MISC', b'WEAP'}

    #--------------------------------------------------------------------------
    # Import Stats
    #--------------------------------------------------------------------------
    # The contents of these tuples have to stay fixed because of CSV parsers
    stats_csv_attrs = {
        b'ALCH': ('eid', 'weight', 'value'),
        b'AMMO': ('eid', 'value', 'speed', 'clipRounds'),
        b'ARMA': ('eid', 'weight', 'value', 'health', 'dr'),
        b'ARMO': ('eid', 'weight', 'value', 'health', 'dr'),
        b'BOOK': ('eid', 'weight', 'value'),
        b'EYES': ('eid', 'flags'),
        b'HAIR': ('eid', 'flags'),
        b'HDPT': ('eid', 'flags'),
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
            'jamTime', 'aimArc', 'rumbleWavelength', 'limbDmgMult',
            'sightUsage', 'semiAutomaticFireDelayMin',
            'semiAutomaticFireDelayMax', 'criticalDamage',
            'criticalMultiplier'),
    }
    stats_attrs = {r: tuple(x for x in a if x != 'eid')
                   for r, a in stats_csv_attrs.items()}

    #--------------------------------------------------------------------------
    # Import Sounds
    #--------------------------------------------------------------------------
    sounds_attrs = {
        b'ASPC': ('environment_type',),
        ##: see sounds_attrs note in oblivion/__init__.py
        b'CREA': ('foot_weight', 'actor_sounds'),
        b'EXPL': ('expl_sound_level',),
        b'IPCT': ('ipct_sound_level',),
        b'PROJ': ('sound_level',),
        b'SOUN': ('soundFile', 'minDist', 'maxDist', 'freqAdj', 'flags',
                  'staticAtten', 'stopTime', 'startTime', 'point0', 'point1',
                  'point2', 'point3', 'point4', 'reverb', 'priority', 'xLoc',
                  'yLoc'),
        b'WEAP': ('sound_level',),
        # Has FormIDs, but will be filtered in AMreWthr.keep_fids
        b'WTHR': ('sounds',),
    }
    sounds_fid_attrs = {
        b'ACTI': ('sound', 'sound_activation'),
        b'ADDN': ('sound',),
        b'ALCH': ('sound_pickup', 'sound_drop', 'sound_consume'),
        b'ARMO': ('sound_pickup', 'sound_drop'),
        b'ASPC': ('sound', 'use_sound_from_region'),
        b'COBJ': ('sound_pickup', 'sound_drop'),
        b'CONT': ('sound', 'sound_close'),
        b'CREA': ('inherits_sounds_from',),
        b'DOOR': ('sound', 'sound_close', 'sound_looping'),
        b'EXPL': ('expl_sound1', 'expl_sound2'),
        b'IPCT': ('sound', 'ipct_sound2'),
        b'KEYM': ('sound_pickup', 'sound_drop'),
        b'LIGH': ('sound',),
        b'MGEF': ('castingSound', 'boltSound', 'hitSound', 'areaSound'),
        b'MISC': ('sound_pickup', 'sound_drop'),
        b'NOTE': ('sound_pickup', 'sound_drop', 'sound'),
        b'PROJ': ('sound', 'sound_countdown', 'sound_disable'),
        b'TACT': ('sound',),
        b'TERM': ('sound',),
        b'WATR': ('sound',),
        b'WEAP': ('sound_pickup', 'sound_drop', 'sound', 'soundGunShot2D',
                  'soundGunShot3DLooping', 'soundMeleeSwingGunNoAmmo',
                  'soundBlock', 'idleSound', 'equipSound', 'unequipSound'),
    }

    #--------------------------------------------------------------------------
    # Import Cells
    #--------------------------------------------------------------------------
    cellRecAttrs = {
        'C.Acoustic': ('acousticSpace',),
        'C.Climate': ('climate', 'flags.behaveLikeExterior'),
        'C.Encounter': ('encounterZone',),
        'C.ForceHideLand': ('cell_land_flags',),
        'C.ImageSpace': ('imageSpace',),
        ##: Patches unuseds?
        'C.Light': ('ambientRed', 'ambientGreen', 'ambientBlue', 'unused1',
                    'directionalRed', 'directionalGreen', 'directionalBlue',
                    'unused2', 'fogRed', 'fogGreen', 'fogBlue', 'unused3',
                    'fogNear', 'fogFar', 'directionalXY', 'directionalZ',
                    'directionalFade', 'fogClip', 'fogPower', 'lightTemplate',
                    'lightInheritFlags'),
        'C.MiscFlags': ('flags.isInterior', 'flags.invertFastTravel',
                        'flags.noLODWater', 'flags.handChanged'),
        'C.Music': ('music',),
        'C.Name': ('full',),
        'C.Owner': ('ownership', 'flags.publicPlace'),
        'C.RecordFlags': ('flags1',), # Yes seems funky but thats the way it is
        'C.Regions': ('regions',),
        'C.Water': ('water', 'waterHeight', 'waterNoiseTexture',
                    'flags.hasWater'),
    }

    #--------------------------------------------------------------------------
    # Import Graphics
    #--------------------------------------------------------------------------
    graphicsTypes = {
        b'ACTI': ('model',),
        b'ALCH': ('iconPath', 'smallIconPath', 'model'),
        b'AMMO': ('iconPath', 'smallIconPath', 'model'),
        b'ARMA': ('maleBody', 'maleWorld', 'maleIconPath', 'maleSmallIconPath',
                  'femaleBody', 'femaleWorld', 'femaleIconPath',
                  'femaleSmallIconPath', 'dnamFlags', 'biped_flags'),
        b'ARMO': ('maleBody', 'maleWorld', 'maleIconPath', 'maleSmallIconPath',
                  'femaleBody', 'femaleWorld', 'femaleIconPath',
                  'femaleSmallIconPath', 'dnamFlags', 'biped_flags'),
        b'AVIF': ('iconPath', 'smallIconPath'),
        b'BOOK': ('iconPath', 'smallIconPath', 'model'),
        b'BPTD': ('model',),
        b'CLAS': ('iconPath',),
        b'COBJ': ('iconPath', 'smallIconPath', 'model'),
        b'CONT': ('model',),
        b'CREA': ('model', 'bodyParts', 'model_list_textures'),
        b'DOOR': ('model',),
        b'EFSH': (
            'efsh_flags', 'particle_texture', 'fill_texture', 'holes_texture',
            'ms_source_blend_mode', 'ms_blend_operation', 'ms_z_test_function',
            'fill_color1_red', 'fill_color1_green', 'fill_color1_blue',
            'fill_alpha_fade_in_time', 'fill_full_alpha_time',
            'fill_alpha_fade_out_time', 'fill_persistent_alpha_ratio',
            'fill_alpha_pulse_amplitude', 'fill_alpha_pulse_frequency',
            'fill_texture_animation_speed_u', 'fill_texture_animation_speed_v',
            'ee_fall_off', 'ee_color_red', 'ee_color_green', 'ee_color_blue',
            'ee_alpha_fade_in_time', 'ee_full_alpha_time',
            'ee_alpha_fade_out_time', 'ee_persistent_alpha_ratio',
            'ee_alpha_pulse_amplitude', 'ee_alpha_pulse_frequency',
            'fill_full_alpha_ratio', 'ee_full_alpha_ratio',
            'ms_dest_blend_mode', 'ps_source_blend_mode', 'ps_blend_operation',
            'ps_z_test_function', 'ps_dest_blend_mode',
            'ps_particle_birth_ramp_up_time', 'ps_full_particle_birth_time',
            'ps_particle_birth_ramp_down_time', 'ps_full_particle_birth_ratio',
            'ps_persistent_particle_birth_ratio', 'ps_particle_lifetime',
            'ps_particle_lifetime_delta', 'ps_initial_speed_along_normal',
            'ps_acceleration_along_normal', 'ps_initial_velocity1',
            'ps_initial_velocity2', 'ps_initial_velocity3', 'ps_acceleration1',
            'ps_acceleration2', 'ps_acceleration3', 'ps_scale_key1',
            'ps_scale_key2', 'ps_scale_key1_time', 'ps_scale_key2_time',
            'color_key1_red', 'color_key1_green', 'color_key1_blue',
            'color_key2_red', 'color_key2_green', 'color_key2_blue',
            'color_key3_red', 'color_key3_green', 'color_key3_blue',
            'color_key1_alpha', 'color_key2_alpha', 'color_key3_alpha',
            'color_key1_time', 'color_key2_time', 'color_key3_time',
            'ps_initial_speed_along_normal_delta', 'ps_initial_rotation',
            'ps_initial_rotation_delta', 'ps_rotation_speed',
            'ps_rotation_speed_delta', 'holes_start_time', 'holes_end_time',
            'holes_start_value', 'holes_end_value', 'ee_width',
            'edge_color_red', 'edge_color_green', 'edge_color_blue',
            'explosion_wind_speed', 'texture_count_u', 'texture_count_v',
            'addon_models_fade_in_time', 'addon_models_fade_out_time',
            'addon_models_scale_start', 'addon_models_scale_end',
            'addon_models_scale_in_time', 'addon_models_scale_out_time'),
        b'EXPL': ('model',),
        b'EYES': ('iconPath',),
        b'FURN': ('model',),
        b'GRAS': ('model',),
        b'HAIR': ('iconPath', 'model'),
        b'HDPT': ('model',),
        b'INGR': ('iconPath', 'model'),
        b'IPCT': ('model', 'effect_duration', 'effect_orientation',
                  'angle_threshold', 'placement_radius', 'ipct_no_decal_data',
                  'decal_min_width', 'decal_max_width', 'decal_min_height',
                  'decal_max_height', 'decal_depth', 'decal_shininess',
                  'decal_parallax_scale', 'decal_parallax_passes',
                  'decal_flags', 'decal_color_red', 'decal_color_green',
                  'decal_color_blue'),
        b'KEYM': ('iconPath', 'smallIconPath', 'model'),
        b'LIGH': ('iconPath', 'model', 'light_radius', 'light_color_red',
                  'light_color_green', 'light_color_blue', 'light_flags',
                  'light_falloff', 'light_fov', 'light_fade'),
        b'LSCR': ('iconPath',),
        b'MGEF': ('iconPath', 'model'),
        b'MICN': ('iconPath', 'smallIconPath'),
        b'MISC': ('iconPath', 'smallIconPath', 'model'),
        b'MSTT': ('model',),
        b'NOTE': ('iconPath', 'smallIconPath', 'model', 'note_texture'),
        b'PERK': ('iconPath', 'smallIconPath'),
        b'PROJ': ('model', 'muzzleFlashDuration', 'fadeDuration',
                  'muzzleFlashPath'),
        b'PWAT': ('model',),
        b'STAT': ('model',),
        b'TACT': ('model',),
        b'TERM': ('model',),
        b'TREE': ('iconPath', 'model'),
        b'TXST': ('base_image_transparency_texture',
                  'normal_map_specular_texture',
                  'environment_map_mask_texture', 'glow_map_texture',
                  'parallax_map_texture', 'environment_map_texture',
                  'decal_min_width', 'decal_max_width', 'decal_min_height',
                  'decal_max_height', 'decal_depth', 'decal_shininess',
                  'decal_parallax_scale', 'decal_parallax_passes',
                  'decal_flags', 'decal_color_red', 'decal_color_green',
                  'decal_color_blue', 'txst_flags'),
        b'WEAP': ('iconPath', 'smallIconPath', 'model', 'shellCasingModel',
                  'scopeModel', 'worldModel', 'animationType', 'gripAnimation',
                  'reloadAnimation'),
    }
    graphicsFidTypes = {
        b'CREA': ('body_part_data',),
        b'EFSH': ('addon_models',),
        b'EXPL': ('image_space_modifier', 'expl_light', 'expl_impact_dataset',
                  'placed_impact_object'),
        b'IPCT': ('ipct_texture_set',),
        b'IPDS': ('impact_stone', 'impact_dirt', 'impact_grass', 'impact_metal',
                  'impact_wood', 'impact_organic', 'impact_cloth', 'impact_water',
                  'impact_hollow_metal', 'impact_organic_bug',
                  'impact_organic_glow'),
        b'MGEF': ('light', 'effectShader', 'enchantEffect'),
        b'PROJ': ('light', 'muzzleFlash', 'explosion'),
        b'WEAP': ('scopeEffect', 'impact_dataset', 'firstPersonModel'),
    }
    graphicsModelAttrs = {'model', 'shellCasingModel', 'scopeModel', 'worldModel',
                          'maleBody', 'maleWorld', 'femaleBody', 'femaleWorld'}

    #--------------------------------------------------------------------------
    # Import Inventory
    #--------------------------------------------------------------------------
    inventory_types = {b'CONT', b'CREA', b'NPC_'}

    #--------------------------------------------------------------------------
    # Import Text
    #--------------------------------------------------------------------------
    text_types = {
        b'AMMO': ('short_name',),
        b'AVIF': ('description', 'short_name'),
        b'BOOK': ('book_text',),
        b'CLAS': ('description',),
        b'LSCR': ('description',),
        b'MESG': ('description',),
        b'MGEF': ('description',),
        ##: This one *might* be a FormID. How on earth do we handle this?
        b'NOTE': ('note_contents',),
        b'PERK': ('description',),
        # omit RACE - covered by R.Description
        b'TERM': ('description',),
    }

    #--------------------------------------------------------------------------
    # Import Object Bounds
    #--------------------------------------------------------------------------
    object_bounds_types = {
        b'ACTI', b'ADDN', b'ALCH', b'AMMO', b'ARMA', b'ARMO', b'ASPC', b'BOOK',
        b'COBJ', b'CONT', b'CREA', b'DOOR', b'EXPL', b'FURN', b'GRAS', b'IDLM',
        b'INGR', b'KEYM', b'LIGH', b'LVLC', b'LVLI', b'LVLN', b'MISC', b'MSTT',
        b'NOTE', b'NPC_', b'PROJ', b'PWAT', b'SCOL', b'SOUN', b'STAT', b'TACT',
        b'TERM', b'TREE', b'TXST', b'WEAP',
    }

    #--------------------------------------------------------------------------
    # Contents Checker
    #--------------------------------------------------------------------------
    # Entry types used for CONT, CREA, LVLI and NPC_
    _common_entry_types = {b'ALCH', b'AMMO', b'ARMO', b'BOOK', b'KEYM',
                           b'LVLI', b'MISC', b'NOTE', b'WEAP'}
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
        (leveled_list_types, 'entries', 'listId'),
        (inventory_types,    'items',   'item'),
    )

    #--------------------------------------------------------------------------
    # Import Scripts
    #--------------------------------------------------------------------------
    # INGR and COBJ are unused - still including them, see e.g. APPA in Skyrim
    scripts_types = {
        b'ACTI', b'ALCH', b'ARMO', b'BOOK', b'COBJ', b'CONT', b'CREA', b'DOOR',
        b'FURN', b'INGR', b'KEYM', b'LIGH', b'MISC', b'NPC_', b'QUST', b'TACT',
        b'TERM', b'WEAP'
    }

    #--------------------------------------------------------------------------
    # Import Destructible
    #--------------------------------------------------------------------------
    destructible_types = {
        b'ACTI', b'ALCH', b'AMMO', b'ARMO', b'BOOK', b'CONT', b'CREA', b'DOOR',
        b'FURN', b'KEYM', b'LIGH', b'MISC', b'MSTT', b'NPC_', b'PROJ', b'TACT',
        b'TERM', b'WEAP',
    }

    #--------------------------------------------------------------------------
    # Import Actors
    #--------------------------------------------------------------------------
    actor_importer_attrs = {
        b'CREA': {
            'Actors.ACBS': (
                'barter_gold', 'calc_max_level', 'calc_min_level',
                'disposition_base', 'fatigue',
                'crea_flags.crea_allow_pc_dialogue',
                'crea_flags.crea_allow_pickpocket', 'crea_flags.crea_biped',
                'crea_flags.crea_cant_open_doors', 'crea_flags.crea_essential',
                'crea_flags.crea_flies', 'crea_flags.crea_immobile',
                'crea_flags.crea_invulnerable', 'crea_flags.crea_is_ghost',
                'crea_flags.crea_no_blood_decal',
                'crea_flags.crea_no_blood_spray',
                'crea_flags.crea_no_combat_in_water', 'crea_flags.no_head',
                'crea_flags.crea_no_knockdowns', 'crea_flags.no_left_arm',
                'crea_flags.no_low_level', 'crea_flags.no_right_arm',
                'crea_flags.crea_no_rotating_head_track',
                'crea_flags.crea_no_shadow',
                'crea_flags.crea_not_pushable', 'crea_flags.no_vats_melee',
                'crea_flags.crea_respawn', 'crea_flags.crea_swims',
                'crea_flags.crea_tilt_front_back',
                'crea_flags.crea_tilt_left_right', 'crea_flags.crea_walks',
                'crea_flags.weapon_and_shield', 'karma', 'speed_multiplier',
                # This flag directly impacts how the level_offset is
                # calculated, so use a fused attribute to always carry them
                # forward together
                ('crea_flags.pc_level_offset', 'level_offset'),
            ),
            'Actors.AIData': (
                'ai_aggression', 'ai_aggro_radius', 'ai_aggro_radius_behavior',
                'ai_assistance', 'ai_confidence', 'ai_energy_level', 'ai_mood',
                'ai_responsibility', 'ai_service_flags', 'ai_train_level',
                'ai_train_skill',
            ),
            'Actors.Anims': ('animations',),
            'Actors.RecordFlags': ('flags1',),
            'Actors.Skeleton': ('model',),
            'Actors.Stats': (
                'agility', 'charisma', 'combat_skill', 'damage', 'endurance',
                'health', 'intelligence', 'luck', 'magic_skill', 'perception',
                'stealth_skill', 'strength',
            ),
            'Creatures.Type': ('creature_type',),
        },
        b'NPC_': {
            'Actors.ACBS': (
                'barter_gold', 'calc_max_level', 'calc_min_level',
                'disposition_base', 'fatigue', 'npc_flags.npc_auto_calc',
                'npc_flags.can_be_all_races', 'npc_flags.npc_essential',
                'npc_flags.npc_female', 'npc_flags.is_chargen_face_preset',
                'npc_flags.crea_no_blood_decal',
                'npc_flags.crea_no_blood_spray',
                'npc_flags.crea_no_knockdowns', 'npc_flags.no_low_level',
                'npc_flags.crea_no_rotating_head_track',
                'npc_flags.crea_not_pushable', 'npc_flags.no_vats_melee',
                'npc_flags.npc_respawn', 'karma', 'speed_multiplier',
                ('npc_flags.pc_level_offset', 'level_offset'), # See above
            ),
            'Actors.AIData': (
                'ai_aggression', 'ai_aggro_radius', 'ai_aggro_radius_behavior',
                'ai_assistance', 'ai_confidence', 'ai_energy_level', 'ai_mood',
                'ai_responsibility', 'ai_service_flags', 'ai_train_level',
                'ai_train_skill',
            ),
            'Actors.Anims': ('animations',),
            'Actors.RecordFlags': ('flags1',),
            'Actors.Skeleton': ('model',),
            'Actors.Stats': ('attributes', 'health', 'skillOffsets',
                             'skillValues'),
            'Creatures.Type': (),
        },
    }
    actor_importer_fid_attrs = {
        b'CREA': {
            'Actors.CombatStyle': ('combat_style',),
            'Actors.DeathItem': ('death_item',),
            'Actors.Voice': ('voice',),
            'Creatures.Blood': ('impact_dataset',),
            'NPC.Class': (),
            'NPC.Race': (),
        },
        b'NPC_': {
            'Actors.CombatStyle': ('combat_style',),
            'Actors.DeathItem': ('death_item',),
            'Actors.Voice': ('voice',),
            'Creatures.Blood': (),
            'NPC.Class': ('npc_class',),
            'NPC.Race': ('race',),
        },
    }
    actor_types = {b'CREA', b'NPC_'}
    spell_types = {b'SPEL'}

    #--------------------------------------------------------------------------
    # Import Spell Stats
    #--------------------------------------------------------------------------
    # The contents of these tuples have to stay fixed because of CSV parsers
    spell_stats_attrs = spell_stats_csv_attrs = (
        'eid', 'cost', 'level', 'spellType', 'spell_flags')

    #--------------------------------------------------------------------------
    # Tweak Actors
    #--------------------------------------------------------------------------
    actor_tweaks = {
        'QuietFeetPatcher',
        'IrresponsibleCreaturesPatcher',
    }

    #--------------------------------------------------------------------------
    # Tweak Names
    #--------------------------------------------------------------------------
    names_tweaks = {
        'NamesTweak_BodyPartCodes',
        'NamesTweak_Body_Armor_Fo3',
        'NamesTweak_Ingestibles_Fo3',
        'NamesTweak_Weapons_Fo3',
        'NamesTweak_AmmoWeight_Fo3',
        'NamesTweak_RenameCaps',
    }
    body_part_codes = ('HAGPBFE', 'HBGPEFE')
    gold_attrs = lambda self: {
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
        'sound_pickup': self.master_fid(0x0864D8), # ITMBottlecapsUp
        'sound_drop': self.master_fid(0x0864D7), # ITMBottlecapsDown
        'value': 1,
        'weight': 0.0,
    }

    #--------------------------------------------------------------------------
    # Tweak Settings
    #--------------------------------------------------------------------------
    settings_tweaks = {
        'GlobalsTweak_Timescale',
        'GmstTweak_Camera_ChaseDistance_Fo3',
        'GmstTweak_Compass_RecognitionDistance',
        'GmstTweak_Actor_UnconsciousnessDuration',
        'GmstTweak_Actor_MaxJumpHeight',
        'GmstTweak_Camera_PCDeathTime',
        'GmstTweak_World_CellRespawnTime',
        'GmstTweak_CostMultiplier_Repair_Fo3',
        'GmstTweak_Combat_MaxActors',
        'GmstTweak_AI_MaxActiveActors',
        'GmstTweak_Actor_MaxCompanions',
        'GmstTweak_AI_MaxDeadActors',
        'GmstTweak_Player_InventoryQuantityPrompt',
        'GmstTweak_Gore_CombatDismemberPartChance',
        'GmstTweak_Gore_CombatExplodePartChance',
        'GmstTweak_LevelDifference_ItemMax',
        'GmstTweak_Movement_BaseSpeed',
        'GmstTweak_Movement_SneakMultiplier',
        'GmstTweak_Combat_VATSPlayerDamageMultiplier',
        'GmstTweak_Combat_AutoAimFix',
        'GmstTweak_Player_PipBoyLightKeypressDelay',
        'GmstTweak_Combat_VATSPlaybackDelay',
        'GmstTweak_Combat_NPCDeathXPThreshold',
        'GmstTweak_Hacking_MaximumNumberOfWords',
        'GmstTweak_Visuals_ShellCameraDistance',
        'GmstTweak_Visuals_ShellLitterTime',
        'GmstTweak_Visuals_ShellLitterCount',
        'GmstTweak_Hacking_TerminalSpeedAdjustment',
        'GmstTweak_Player_MaxDraggableWeight',
        'GmstTweak_Prompt_Activate_Tes4',
        'GmstTweak_Prompt_Open_Tes4',
        'GmstTweak_Prompt_Read_Tes4',
        'GmstTweak_Prompt_Sit_Tes4',
        'GmstTweak_Prompt_Take_Tes4',
        'GmstTweak_Prompt_Talk_Tes4',
        'GmstTweak_Combat_SpeakOnHitChance',
        'GmstTweak_Combat_SpeakOnHitThreshold',
        'GmstTweak_Combat_SpeakOnPowerAttackChance',
        'GmstTweak_Combat_MaxAllyHitsInCombat',
        'GmstTweak_Combat_MaxAllyHitsOutOfCombat',
        'GmstTweak_Combat_MaxFriendHitsInCombat',
        'GmstTweak_Combat_MaxFriendHitsOutOfCombat',
    }

    #--------------------------------------------------------------------------
    # Tweak Assorted
    #--------------------------------------------------------------------------
    ##: Mostly mirrored from valda's version - some of these seem to make no sense
    # (e.g. I can't find anything regarding FO3/FNV suffering from the fog bug).
    assorted_tweaks = {
        'AssortedTweak_ArmorPlayable',
        'AssortedTweak_FogFix',
        'AssortedTweak_NoLightFlicker',
        'AssortedTweak_WindSpeed',
        'AssortedTweak_SetSoundAttenuationLevels',
        'AssortedTweak_LightFadeValueFix',
        'AssortedTweak_TextlessLSCRs',
        'AssortedTweak_PotionWeightMinimum',
        'AssortedTweak_UniformGroundcover',
        'AssortedTweak_GunsUseISAnimation',
        'AssortedTweak_BookWeight',
    }
    static_attenuation_rec_type = b'SOUN'

    #--------------------------------------------------------------------------
    # Import Relations
    #--------------------------------------------------------------------------
    relations_attrs = ('faction', 'mod', 'group_combat_reaction')

    #--------------------------------------------------------------------------
    # Import Enchantment Stats
    #--------------------------------------------------------------------------
    ench_stats_attrs = ('item_type', 'charge_amount', 'enchantment_cost',
                        'enit_flags')

    #--------------------------------------------------------------------------
    # Import Effect Stats
    #--------------------------------------------------------------------------
    mgef_stats_attrs = ('flags', 'base_cost', 'school', 'resist_value',
                        'projectileSpeed', 'cef_enchantment', 'cef_barter',
                        'effect_archetype', 'actorValue')
    mgef_stats_fid_attrs = ('associated_item',)

    #--------------------------------------------------------------------------
    # Import Races
    #--------------------------------------------------------------------------
    import_races_attrs = {
        b'RACE': {
            'R.Body-F': ('femaleUpperBody', 'femaleLeftHand',
                         'femaleRightHand', 'femaleUpperBodyTexture'),
            'R.Body-M': ('maleUpperBody', 'maleLeftHand', 'maleRightHand',
                         'maleUpperBodyTexture'),
            'R.Body-Size-F': ('femaleHeight', 'femaleWeight'),
            'R.Body-Size-M': ('maleHeight', 'maleWeight'),
            'R.Description': ('description',),
            'R.Ears': ('maleEars', 'femaleEars'),
            # eyes has FormIDs, but will be filtered in AMreRace.keep_fids
            'R.Eyes': ('eyes', 'femaleLeftEye', 'femaleRightEye',
                       'maleLeftEye', 'maleRightEye'),
            # hairs has FormIDs, but will be filtered in AMreRace.keep_fids
            'R.Hair': ('hairs',),
            'R.Head': ('femaleHead', 'maleHead',),
            'R.Mouth': ('maleMouth', 'femaleMouth', 'maleTongue',
                        'femaleTongue'),
            'R.Skills': ('skills',),
            'R.Teeth': ('femaleTeethLower', 'femaleTeethUpper',
                        'maleTeethLower', 'maleTeethUpper'),
        },
    }
    import_races_fid_attrs = {
        b'RACE': {
            'R.Voice-F': ('femaleVoice',),
            'R.Voice-M': ('maleVoice',),
        },
    }

    #--------------------------------------------------------------------------
    # Import Enchantments
    #--------------------------------------------------------------------------
    enchantment_types = {b'ARMO', b'CREA', b'EXPL', b'NPC_', b'WEAP'}

    #--------------------------------------------------------------------------
    # Tweak Races
    #--------------------------------------------------------------------------
    race_tweaks = {
        'RaceTweak_PlayableHeadParts',
        'RaceTweak_MergeSimilarRaceHairs',
        'RaceTweak_MergeSimilarRaceEyes',
        'RaceTweak_PlayableEyes',
        'RaceTweak_PlayableHairs',
        'RaceTweak_GenderlessHairs',
        'RaceTweak_AllEyes',
        'RaceTweak_AllHairs',
    }
    race_tweaks_need_collection = True

    #--------------------------------------------------------------------------
    # NPC Checker
    #--------------------------------------------------------------------------
    _standard_eyes = [(None, x) for x in
                      (0x4252, 0x4253, 0x4254, 0x4255, 0x4256)]
    default_eyes = {
        #--FalloutNV.esm
        # Caucasian
        (None, 0x000019): _standard_eyes,
        # Hispanic
        (None, 0x0038e5): _standard_eyes,
        # Asian
        (None, 0x0038e6): _standard_eyes,
        # Ghoul
        (None, 0x003b3e): [(None, 0x35e4f)],
        # AfricanAmerican
        (None, 0x00424a): _standard_eyes,
        # AfricanAmerican Child
        (None, 0x0042be): _standard_eyes,
        # AfricanAmerican Old
        (None, 0x0042bf): _standard_eyes,
        # Asian Child
        (None, 0x0042c0): _standard_eyes,
        # Asian Old
        (None, 0x0042c1): _standard_eyes,
        # Caucasian Child
        (None, 0x0042c2): _standard_eyes,
        # Caucasian Old
        (None, 0x0042c3): _standard_eyes,
        # Hispanic Child
        (None, 0x0042c4): _standard_eyes,
        # Hispanic Old
        (None, 0x0042c5): _standard_eyes,
        # Caucasian Raider
        (None, 0x04bb8d): [(None, 0x4cb10)],
        # Hispanic Raider
        (None, 0x04bf70): [(None, 0x4cb10)],
        # Asian Raider
        (None, 0x04bf71): [(None, 0x4cb10)],
        # AfricanAmerican Raider
        (None, 0x04bf72): [(None, 0x4cb10)],
        # Hispanic Old Aged
        (None, 0x0987dc): _standard_eyes,
        # Asian Old Aged
        (None, 0x0987dd): _standard_eyes,
        # AfricanAmerican Old Aged
        (None, 0x0987de): _standard_eyes,
        # Caucasian Old Aged
        (None, 0x0987df): _standard_eyes,
    }

    #--------------------------------------------------------------------------
    # Timescale Checker
    #--------------------------------------------------------------------------
    default_wp_timescale = 30

    top_groups = [
        b'GMST', b'TXST', b'MICN', b'GLOB', b'CLAS', b'FACT', b'HDPT', b'HAIR',
        b'EYES', b'RACE', b'SOUN', b'ASPC', b'MGEF', b'SCPT', b'LTEX', b'ENCH',
        b'SPEL', b'ACTI', b'TACT', b'TERM', b'ARMO', b'BOOK', b'CONT', b'DOOR',
        b'INGR', b'LIGH', b'MISC', b'STAT', b'SCOL', b'MSTT', b'PWAT', b'GRAS',
        b'TREE', b'FURN', b'WEAP', b'AMMO', b'NPC_', b'CREA', b'LVLC', b'LVLN',
        b'KEYM', b'ALCH', b'IDLM', b'NOTE', b'PROJ', b'LVLI', b'WTHR', b'CLMT',
        b'COBJ', b'REGN', b'NAVI', b'CELL', b'WRLD', b'DIAL', b'QUST', b'IDLE',
        b'PACK', b'CSTY', b'LSCR', b'ANIO', b'WATR', b'EFSH', b'EXPL', b'DEBR',
        b'IMGS', b'IMAD', b'FLST', b'PERK', b'BPTD', b'ADDN', b'AVIF', b'RADS',
        b'CAMS', b'CPTH', b'VTYP', b'IPCT', b'IPDS', b'ARMA', b'ECZN', b'MESG',
        b'RGDL', b'DOBJ', b'LGTM', b'MUSC',
    ]

    @classmethod
    def init(cls, _package_name=None):
        super().init(_package_name or __name__)
        cls._import_records(__name__)

    @classmethod
    def _import_records(cls, package_name, plugin_form_vers=15):
        # We can't upgrade IMGS\DNAM (see definition), so skip upgrading form
        # version too
        from ... import brec as _brec_
        _brec_.RecordHeader.skip_form_version_upgrade = {b'IMGS'}
        super()._import_records(package_name, plugin_form_vers)
        cls.mergeable_sigs = set(cls.top_groups) - {b'CELL', b'DIAL', b'WRLD',
                                                    b'NAVI'}
        _brec_.RecordType.simpleTypes = cls.mergeable_sigs # that's what it did

# Language dirs, shared by EGS and WS versions
FO3_LANG_DIRS = ['Fallout 3 GOTY English', 'Fallout 3 GOTY French',
                 'Fallout 3 GOTY German', 'Fallout 3 GOTY Italian',
                 'Fallout 3 GOTY Spanish']

class EGSFallout3GameInfo(Fallout3GameInfo):
    """GameInfo override for the Epic Games Store version of Fallout 3."""
    displayName = 'Fallout 3 (EGS)'
    # appdata_name and my_games_name use the original locations

    @classproperty
    def game_detect_includes(cls):
        return super().game_detect_includes | {'FalloutLauncherEpic.exe'}

    @classproperty
    def game_detect_excludes(cls):
        return super().game_detect_excludes - {'FalloutLauncherEpic.exe'}

    class Eg(Fallout3GameInfo.Eg):
        egs_app_names = ['adeae8bbfc94427db57c7dfecce3f1d4']
        egs_language_dirs = FO3_LANG_DIRS

class GOGFallout3GameInfo(GOGMixin, Fallout3GameInfo):
    """GameInfo override for the GOG version of Fallout 3."""
    displayName = 'Fallout 3 (GOG)'
    _gog_game_ids = _GOG_IDS
    # appdata_name and my_games_name use the original locations

class WSFallout3GameInfo(WindowsStoreMixin, Fallout3GameInfo):
    """GameInfo override for the Windows Store version of Fallout 3."""
    displayName = 'Fallout 3 (WS)'
    # appdata_name and my_games_name use the original locations

    class Ws(Fallout3GameInfo.Ws):
        legacy_publisher_name = 'Bethesda'
        win_store_name = 'BethesdaSoftworks.Fallout3'
        ws_language_dirs = FO3_LANG_DIRS

GAME_TYPE = {g.displayName: g for g in
             (Fallout3GameInfo, EGSFallout3GameInfo, GOGFallout3GameInfo,
              WSFallout3GameInfo)}
