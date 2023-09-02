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
import re
from os.path import join as _j

from ..patch_game import GameInfo, PatchGame
from ... import bolt

class SkyrimGameInfo(PatchGame):
    """GameInfo override for TES V: Skyrim."""
    displayName = u'Skyrim'
    fsName = u'Skyrim'
    altName = u'Wrye Smash'
    game_icon = u'skyrim_%u.png'
    bash_root_prefix = u'Skyrim'
    bak_game_name = u'Skyrim'
    my_games_name = u'Skyrim'
    appdata_name = u'Skyrim'
    launch_exe = u'TESV.exe'
    # Set to this because TESV.exe also exists for Enderal
    game_detect_includes = {'SkyrimLauncher.exe'}
    version_detect_file = u'TESV.exe'
    master_file = bolt.FName(u'Skyrim.esm')
    taglist_dir = u'Skyrim'
    loot_dir = u'Skyrim'
    loot_game_name = 'Skyrim'
    boss_game_name = u'Skyrim'
    registry_keys = [(r'Bethesda Softworks\Skyrim', 'Installed Path')]
    nexusUrl = u'https://www.nexusmods.com/skyrim/'
    nexusName = u'Skyrim Nexus'
    nexusKey = u'bash.installers.openSkyrimNexus.continue'

    plugin_name_specific_dirs = GameInfo.plugin_name_specific_dirs + [
        _j(u'meshes', u'actors', u'character', u'facegendata', u'facegeom'),
        _j(u'textures', u'actors', u'character', u'facegendata', u'facetint')]

    class Ck(GameInfo.Ck):
        ck_abbrev = u'CK'
        long_name = u'Creation Kit'
        exe = u'CreationKit.exe'
        image_name = u'creationkit%s.png'

    class Se(GameInfo.Se):
        se_abbrev = u'SKSE'
        long_name = u'Skyrim Script Extender'
        exe = u'skse_loader.exe'
        ver_files = [u'skse_loader.exe', u'skse_steam_loader.dll']
        plugin_dir = u'SKSE'
        cosave_tag = u'SKSE'
        cosave_ext = u'.skse'
        url = u'http://skse.silverlock.org/'
        url_tip = u'http://skse.silverlock.org/'

    class Sd(GameInfo.Sd):
        sd_abbrev = u'SD'
        long_name = u'Script Dragon'
        install_dir = u'asi'

    class Sp(GameInfo.Sp):
        sp_abbrev = u'SP'
        long_name = u'SkyProc'
        install_dir = u'SkyProc Patchers'

    class Ini(GameInfo.Ini):
        default_ini_file = u'Skyrim_default.ini'
        dropdown_inis = [u'Skyrim.ini', u'SkyrimPrefs.ini']
        resource_archives_keys = (u'sResourceArchiveList',
                                  u'sResourceArchiveList2')

    class Bsa(GameInfo.Bsa):
        # Skyrim only accepts the base name
        attachment_regex = u''
        has_bsl = True
        valid_versions = {0x68}

    class Psc(GameInfo.Psc):
        source_extensions = {u'.psc'}
        # In SSE Bethesda made the mistake of packaging the CK's script source
        # as 'source/scripts' instead of 'scripts/source'. The CK even still
        # expects the sources to be in 'scripts/source', so you'd have to edit
        # its INI if you wanted to use 'source/scripts'. However, some modders
        # have nonetheless adopted this convention, so to support this we
        # redirect them to the correct path while scanning the package in BAIN.
        # Sits here because the situation then got worse - some modders have
        # started packaging 'source' dirs even in Skyrim LE.
        source_redirects = {
            _j(u'source', u'scripts'): _j(u'scripts', u'source'),
            u'source': _j(u'scripts', u'source'),
        }

    class Xe(GameInfo.Xe):
        full_name = u'TES5Edit'
        xe_key_prefix = u'tes5View'

    class Bain(GameInfo.Bain):
        data_dirs = GameInfo.Bain.data_dirs | {
            'asi', # 3P: Script Dragon
            'autobody', # 3P: AutoBody
            'calientetools', # 3P: BodySlide
            'dialogueviews',
            'dragonbornvoiceover', # 3P: Dragonborn Voice Over
            'dyndolod', # 3P: DynDOLOD
            'flm', # 3P: FormList Manipulator
            'grass',
            'interface',
            'kreate', # 3P: KreatE
            'lodsettings',
            'mapmarkers', # 3P: Common Marker Addon Project
            'mapweathers', # 3P: Unique Map Weather
            'mcm', # 3P: MCM Helper
            'mlq', # 3P: Lawbringer
            'nemesis_engine', # 3P: Nemesis Unlimited Behavior Engine
            'netscriptframework', # 3P: .NET Script Framework
            'osa', # 3P: OSA Animation Framework
            'platform', # 3P: Skyrim Platform
            'scripts',
            'seasons', # 3P: Seasons of Skyrim SKSE
            'seq',
            'shaders', # 3P: Community Shaders
            'shadersfx',
            'skse', # 3P: SKSE
            'skyproc patchers', # 3P: SkyProc
            'slanims', # 3P: SL Animation Loader
            'source', # see Psc.source_redirects above
            'strings',
            'tools', # 3P: FNIS
        }
        keep_data_dirs = {'lsdata'}
        no_skip = GameInfo.Bain.no_skip | {*(_j('interface', x) for x in (
            'controlmap.txt',
            'credits.txt',
            'credits_french.txt',
            'fontconfig.txt',
            'gamepad.txt',
            'keyboard_english.txt',
            'keyboard_french.txt',
            'keyboard_german.txt',
            'keyboard_italian.txt',
            'keyboard_spanish.txt',
            'mouse.txt',
            'skyui_cfg.txt', # 3P: SkyUI
            'skyui_translate.txt', # 3P: SkyUI
        )),
            # 3P: Vanilla, generated by FNIS
            _j('meshes', 'animationdatasinglefile.txt'),
            _j('meshes', 'animationsetdatasinglefile.txt'),
            # 3P: .NET Script Framework
            _j('netscriptframework', 'netscriptframework.config.txt'),
        }
        no_skip_dirs = GameInfo.Bain.no_skip_dirs | {
            # This rule is to allow mods with string translation enabled.
            _j('interface', 'translations'): {'.txt'},
            # 3P: .NET Script Framework
            _j('netscriptframework', 'plugins'): {'.txt'},
        }
        no_skip_regexes = (
            # 3P: FNIS - meshes\actors\character\animations\<mod name>\
            # FNIS_<mod name>_List.txt
            re.compile(bolt.os_sep_re.join([
                'meshes', 'actors', 'character', 'animations',
                f'[^{bolt.os_sep_re}]+', r'fnis_.+_list\.txt'])),
            # 3P: SKSE/skse64 Plugin Preloader - skse\plugins\
            # <SKSE plugin name>_preload.txt
            re.compile(bolt.os_sep_re.join([
                'skse', 'plugins', r'.+_preload\.txt'])),
            # 3P: Dynamic Animation Replacer - meshes\actors\<Project folder>\
            # animations\DynamicAnimationReplacer\_CustomConditions\<Priority>\
            # _conditions.txt
            re.compile(bolt.os_sep_re.join([
                'meshes', 'actors', '.+', 'animations',
                'dynamicanimationreplacer', '_customconditions', r'-?\d+',
                r'_conditions\.txt'])),
        )
        skip_bain_refresh = {u'tes5edit backups', u'tes5edit cache'}

    class Esp(GameInfo.Esp):
        canBash = True
        canEditHeader = True
        generate_temp_child_onam = True
        max_lvl_list_size = 255
        validHeaderVersions = (0.94, 1.70)

    allTags = PatchGame.allTags | {'NoMerge'}
    patchers = {
        'AliasPluginNames', 'ContentsChecker', 'ImportActors',
        'ImportActorsAIPackages', 'ImportActorsFactions', 'ImportActorsPerks',
        'ImportActorsSpells', 'ImportCells', 'ImportDestructible',
        'ImportEffectStats', 'ImportEnchantments', 'ImportEnchantmentStats',
        'ImportGraphics', 'ImportInventory', 'ImportKeywords', 'ImportNames',
        'ImportObjectBounds', 'ImportOutfits', 'ImportRaces',
        'ImportRacesSpells', 'ImportRelations', 'ImportSounds',
        'ImportSpellStats', 'ImportStats', 'ImportText', 'LeveledLists',
        'MergePatches', 'TimescaleChecker', 'TweakActors', 'TweakAssorted',
        'TweakNames', 'TweakRaces', 'TweakSettings',
    }

    weaponTypes = (
        _(u'Blade (1 Handed)'),
        _(u'Blade (2 Handed)'),
        _(u'Blunt (1 Handed)'),
        _(u'Blunt (2 Handed)'),
        _(u'Staff'),
        _(u'Bow'),
        )

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

    bethDataFiles = {
        'dawnguard.bsa',
        'dawnguard.esm',
        'dragonborn.bsa',
        'dragonborn.esm',
        'hearthfires.bsa',
        'hearthfires.esm',
        'highrestexturepack01.bsa',
        'highrestexturepack01.esp',
        'highrestexturepack02.bsa',
        'highrestexturepack02.esp',
        'highrestexturepack03.bsa',
        'highrestexturepack03.esp',
        'skyrim - animations.bsa',
        'skyrim - interface.bsa',
        'skyrim - meshes.bsa',
        'skyrim - misc.bsa',
        'skyrim - shaders.bsa',
        'skyrim - sounds.bsa',
        'skyrim - textures.bsa',
        'skyrim - voices.bsa',
        'skyrim - voicesextra.bsa',
        'skyrim.esm',
        'update.bsa',
        'update.esm',
    }

    # Function Info -----------------------------------------------------------
    # 0: no param; 1: int param; 2: FormID param; 3: float param
    # Third parameter is always sint32, so no need to specify here
    condition_function_data = {
        0:    ('GetWantBlocking', 0, 0),
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
        77:   ('GetRandomPercent', 0, 0),
        79:   ('GetQuestVariable', 2, 0),
        80:   ('GetLevel', 0, 0),
        81:   ('IsRotating', 0, 0),
        84:   ('GetDeadCount', 2, 0),
        91:   ('GetIsAlerted', 0, 0),
        98:   ('GetPlayerControlsDisabled', 1, 1),
        99:   ('GetHeadingAngle', 2, 0),
        101:  ('IsWeaponMagicOut', 0, 0),
        102:  ('IsTorchOut', 0, 0),
        103:  ('IsShieldOut', 0, 0),
        106:  ('IsFacingUp', 0, 0),
        107:  ('GetKnockedState', 0, 0),
        108:  ('GetWeaponAnimType', 0, 0),
        109:  ('IsWeaponSkillType', 2, 0),
        110:  ('GetCurrentAIPackage', 0, 0),
        111:  ('IsWaiting', 0, 0),
        112:  ('IsIdlePlaying', 0, 0),
        116:  ('IsIntimidatedbyPlayer', 0, 0),
        117:  ('IsPlayerInRegion', 0, 0),
        118:  ('GetActorAggroRadiusViolated', 0, 0),
        122:  ('GetCrime', 2, 1),
        123:  ('IsGreetingPlayer', 0, 0),
        125:  ('IsGuard', 0, 0),
        127:  ('HasBeenEaten', 0, 0),
        128:  ('GetStaminaPercentage', 0, 0),
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
        152:  ('GetIsCrimeFaction', 2, 0),
        153:  ('CanHaveFlames', 0, 0),
        154:  ('HasFlames', 0, 0),
        157:  ('GetOpenState', 0, 0),
        159:  ('GetSitting', 0, 0),
        161:  ('GetIsCurrentPackage', 2, 0),
        162:  ('IsCurrentFurnitureRef', 2, 0),
        163:  ('IsCurrentFurnitureObj', 2, 0),
        170:  ('GetDayOfWeek', 0, 0),
        172:  ('GetTalkedToPCParam', 2, 0),
        175:  ('IsPCSleeping', 0, 0),
        176:  ('IsPCAMurderer', 0, 0),
        180:  ('HasSameEditorLocAsRef', 2, 2),
        181:  ('HasSameEditorLocAsRefAlias', 1, 2),
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
        226:  ('GetVampireFeed', 0, 0),
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
        248:  ('IsScenePlaying', 2, 0),
        249:  ('IsInDialogueWithPlayer', 0, 0),
        250:  ('GetLocationCleared', 2, 0),
        254:  ('GetIsPlayableRace', 0, 0),
        255:  ('GetOffersServicesNow', 0, 0),
        258:  ('HasAssociationType', 2, 2),
        259:  ('HasFamilyRelationship', 2, 0),
        261:  ('HasParentRelationship', 2, 0),
        262:  ('IsWarningAbout', 2, 0),
        263:  ('IsWeaponOut', 0, 0),
        264:  ('HasSpell', 2, 0),
        265:  ('IsTimePassing', 0, 0),
        266:  ('IsPleasant', 0, 0),
        267:  ('IsCloudy', 0, 0),
        274:  ('IsSmallBump', 0, 0),
        277:  ('GetBaseActorValue', 2, 0),
        278:  ('IsOwner', 2, 0),
        280:  ('IsCellOwner', 2, 2),
        282:  ('IsHorseStolen', 0, 0),
        285:  ('IsLeftUp', 0, 0),
        286:  ('IsSneaking', 0, 0),
        287:  ('IsRunning', 0, 0),
        288:  ('GetFriendHit', 0, 0),
        289:  ('IsInCombat', 1, 0),
        300:  ('IsInInterior', 0, 0),
        304:  ('IsWaterObject', 0, 0),
        305:  ('GetPlayerAction', 0, 0),
        306:  ('IsActorUsingATorch', 0, 0),
        309:  ('IsXBox', 0, 0),
        310:  ('GetInWorldspace', 2, 0),
        312:  ('GetPCMiscStat', 0, 0),
        313:  ('GetPairedAnimation', 0, 0),
        314:  ('IsActorAVictim', 0, 0),
        315:  ('GetTotalPersuasionNumber', 0, 0),
        318:  ('GetIdleDoneOnce', 0, 0),
        320:  ('GetNoRumors', 0, 0),
        323:  ('GetCombatState', 0, 0),
        325:  ('GetWithinPackageLocation', 0, 0),
        327:  ('IsRidingMount', 0, 0),
        329:  ('IsFleeing', 0, 0),
        332:  ('IsInDangerousWater', 0, 0),
        338:  ('GetIgnoreFriendlyHits', 0, 0),
        339:  ('IsPlayersLastRiddenMount', 0, 0),
        353:  ('IsActor', 0, 0),
        354:  ('IsEssential', 0, 0),
        358:  ('IsPlayerMovingIntoNewSpace', 0, 0),
        359:  ('GetInCurrentLoc', 2, 0),
        360:  ('GetInCurrentLocAlias', 1, 0),
        361:  ('GetTimeDead', 0, 0),
        362:  ('HasLinkedRef', 2, 0),
        365:  ('IsChild', 0, 0),
        366:  ('GetStolenItemValueNoCrime', 2, 0),
        367:  ('GetLastPlayerAction', 0, 0),
        368:  ('IsPlayerActionActive', 1, 0),
        370:  ('IsTalkingActivatorActor', 2, 0),
        372:  ('IsInList', 2, 0),
        373:  ('GetStolenItemValue', 2, 0),
        375:  ('GetCrimeGoldViolent', 2, 0),
        376:  ('GetCrimeGoldNonviolent', 2, 0),
        378:  ('HasShout', 2, 0),
        381:  ('GetHasNote', 2, 0),
        390:  ('GetHitLocation', 0, 0),
        391:  ('IsPC1stPerson', 0, 0),
        396:  ('GetCauseofDeath', 0, 0),
        397:  ('IsLimbGone', 1, 0),
        398:  ('IsWeaponInList', 2, 0),
        402:  ('IsBribedbyPlayer', 0, 0),
        403:  ('GetRelationshipRank', 2, 0),
        # We set the second to 'unused' here to receive it as 4 bytes, which we
        # then handle inside _MelCtdaFo3.
        407:  ('GetVATSValue', 1, 0),
        408:  ('IsKiller', 2, 0),
        409:  ('IsKillerObject', 2, 0),
        410:  ('GetFactionCombatReaction', 2, 2),
        414:  ('Exists', 2, 0),
        415:  ('GetGroupMemberCount', 0, 0),
        416:  ('GetGroupTargetCount', 0, 0),
        426:  ('GetIsVoiceType', 2, 0),
        427:  ('GetPlantedExplosive', 0, 0),
        429:  ('IsScenePackageRunning', 0, 0),
        430:  ('GetHealthPercentage', 0, 0),
        432:  ('GetIsObjectType', 2, 0),
        434:  ('GetDialogueEmotion', 0, 0),
        435:  ('GetDialogueEmotionValue', 0, 0),
        437:  ('GetIsCreatureType', 1, 0),
        444:  ('GetInCurrentLocFormList', 2, 0),
        445:  ('GetInZone', 2, 0),
        446:  ('GetVelocity', 0, 0),
        447:  ('GetGraphVariableFloat', 0, 0),
        448:  ('HasPerk', 2, 0),
        449:  ('GetFactionRelation', 2, 0),
        450:  ('IsLastIdlePlayed', 2, 0),
        453:  ('GetPlayerTeammate', 0, 0),
        454:  ('GetPlayerTeammateCount', 0, 0),
        458:  ('GetActorCrimePlayerEnemy', 0, 0),
        459:  ('GetCrimeGold', 2, 0),
        463:  ('IsPlayerGrabbedRef', 2, 0),
        465:  ('GetKeywordItemCount', 2, 0),
        470:  ('GetDestructionStage', 0, 0),
        473:  ('GetIsAlignment', 2, 0),
        476:  ('IsProtected', 0, 0),
        477:  ('GetThreatRatio', 2, 0),
        479:  ('GetIsUsedItemEquipType', 2, 0),
        487:  ('IsCarryable', 0, 0),
        488:  ('GetConcussed', 0, 0),
        491:  ('GetMapMarkerVisible', 0, 0),
        493:  ('PlayerKnows', 0, 0),
        494:  ('GetPermanentActorValue', 2, 0),
        495:  ('GetKillingBlowLimb', 0, 0),
        497:  ('CanPayCrimeGold', 2, 0),
        499:  ('GetDaysInJail', 0, 0),
        500:  ('EPAlchemyGetMakingPoison', 0, 0),
        501:  ('EPAlchemyEffectHasKeyword', 2, 0),
        503:  ('GetAllowWorldInteractions', 0, 0),
        508:  ('GetLastHitCritical', 0, 0),
        513:  ('IsCombatTarget', 2, 0),
        515:  ('GetVATSRightAreaFree', 2, 0),
        516:  ('GetVATSLeftAreaFree', 2, 0),
        517:  ('GetVATSBackAreaFree', 2, 0),
        518:  ('GetVATSFrontAreaFree', 2, 0),
        519:  ('GetIsLockBroken', 0, 0),
        520:  ('IsPS3', 0, 0),
        521:  ('IsWin32', 0, 0),
        522:  ('GetVATSRightTargetVisible', 2, 0),
        523:  ('GetVATSLeftTargetVisible', 2, 0),
        524:  ('GetVATSBackTargetVisible', 2, 0),
        525:  ('GetVATSFrontTargetVisible', 2, 0),
        528:  ('IsInCriticalStage', 2, 0),
        530:  ('GetXPForNextLevel', 0, 0),
        533:  ('GetInfamy', 2, 0),
        534:  ('GetInfamyViolent', 2, 0),
        535:  ('GetInfamyNonViolent', 2, 0),
        543:  ('GetQuestCompleted', 2, 0),
        547:  ('IsGoreDisabled', 0, 0),
        550:  ('IsSceneActionComplete', 2, 1),
        552:  ('GetSpellUsageNum', 2, 0),
        554:  ('GetActorsInHigh', 0, 0),
        555:  ('HasLoaded3D', 0, 0),
        560:  ('HasKeyword', 2, 0),
        561:  ('HasRefType', 2, 0),
        562:  ('LocationHasKeyword', 2, 0),
        563:  ('LocationHasRefType', 2, 0),
        565:  ('GetIsEditorLocation', 2, 0),
        566:  ('GetIsAliasRef', 1, 0),
        567:  ('GetIsEditorLocAlias', 1, 0),
        568:  ('IsSprinting', 0, 0),
        569:  ('IsBlocking', 0, 0),
        570:  ('HasEquippedSpell', 2, 0),
        571:  ('GetCurrentCastingType', 2, 0),
        572:  ('GetCurrentDeliveryType', 2, 0),
        574:  ('GetAttackState', 0, 0),
        576:  ('GetEventData', 0, 2),
        577:  ('IsCloserToAThanB', 2, 2),
        579:  ('GetEquippedShout', 2, 0),
        580:  ('IsBleedingOut', 0, 0),
        584:  ('GetRelativeAngle', 2, 0),
        589:  ('GetMovementDirection', 0, 0),
        590:  ('IsInScene', 0, 0),
        591:  ('GetRefTypeDeadCount', 2, 2),
        592:  ('GetRefTypeAliveCount', 2, 2),
        594:  ('GetIsFlying', 0, 0),
        595:  ('IsCurrentSpell', 2, 2),
        596:  ('SpellHasKeyword', 2, 2),
        597:  ('GetEquippedItemType', 2, 0),
        598:  ('GetLocationAliasCleared', 1, 0),
        600:  ('GetLocAliasRefTypeDeadCount', 1, 2),
        601:  ('GetLocAliasRefTypeAliveCount', 1, 2),
        602:  ('IsWardState', 0, 0),
        603:  ('IsInSameCurrentLocAsRef', 2, 2),
        604:  ('IsInSameCurrentLocAsRefAlias', 1, 2),
        605:  ('LocAliasIsLocation', 1, 2),
        606:  ('GetKeywordDataForLocation', 2, 2),
        608:  ('GetKeywordDataForAlias', 1, 2),
        610:  ('LocAliasHasKeyword', 1, 2),
        611:  ('IsNullPackageData', 0, 0),
        612:  ('GetNumericPackageData', 0, 0),
        613:  ('IsFurnitureAnimType', 0, 0),
        614:  ('IsFurnitureEntryType', 0, 0),
        615:  ('GetHighestRelationshipRank', 0, 0),
        616:  ('GetLowestRelationshipRank', 0, 0),
        617:  ('HasAssociationTypeAny', 2, 0),
        618:  ('HasFamilyRelationshipAny', 0, 0),
        619:  ('GetPathingTargetOffset', 0, 0),
        620:  ('GetPathingTargetAngleOffset', 0, 0),
        621:  ('GetPathingTargetSpeed', 0, 0),
        622:  ('GetPathingTargetSpeedAngle', 0, 0),
        623:  ('GetMovementSpeed', 0, 0),
        624:  ('GetInContainer', 2, 0),
        625:  ('IsLocationLoaded', 2, 0),
        626:  ('IsLocAliasLoaded', 1, 0),
        627:  ('IsDualCasting', 0, 0),
        629:  ('GetVMQuestVariable', 2, 0),
        630:  ('GetVMScriptVariable', 2, 0),
        631:  ('IsEnteringInteractionQuick', 0, 0),
        632:  ('IsCasting', 0, 0),
        633:  ('GetFlyingState', 0, 0),
        635:  ('IsInFavorState', 0, 0),
        636:  ('HasTwoHandedWeaponEquipped', 0, 0),
        637:  ('IsExitingInstant', 0, 0),
        638:  ('IsInFriendStatewithPlayer', 0, 0),
        639:  ('GetWithinDistance', 2, 3),
        640:  ('GetActorValuePercent', 2, 0),
        641:  ('IsUnique', 0, 0),
        642:  ('GetLastBumpDirection', 0, 0),
        644:  ('IsInFurnitureState', 0, 0),
        645:  ('GetIsInjured', 0, 0),
        646:  ('GetIsCrashLandRequest', 0, 0),
        647:  ('GetIsHastyLandRequest', 0, 0),
        650:  ('IsLinkedTo', 2, 2),
        651:  ('GetKeywordDataForCurrentLocation', 2, 0),
        652:  ('GetInSharedCrimeFaction', 2, 0),
        654:  ('GetBribeSuccess', 0, 0),
        655:  ('GetIntimidateSuccess', 0, 0),
        656:  ('GetArrestedState', 0, 0),
        657:  ('GetArrestingActor', 0, 0),
        659:  ('EPTemperingItemIsEnchanted', 0, 0),
        660:  ('EPTemperingItemHasKeyword', 2, 0),
        664:  ('GetReplacedItemType', 2, 0),
        672:  ('IsAttacking', 0, 0),
        673:  ('IsPowerAttacking', 0, 0),
        674:  ('IsLastHostileActor', 0, 0),
        675:  ('GetGraphVariableInt', 0, 0),
        676:  ('GetCurrentShoutVariation', 0, 0),
        678:  ('ShouldAttackKill', 2, 0),
        680:  ('GetActivationHeight', 0, 0),
        681:  ('EPModSkillUsage_IsAdvanceSkill', 2, 0),
        682:  ('WornHasKeyword', 2, 0),
        683:  ('GetPathingCurrentSpeed', 0, 0),
        684:  ('GetPathingCurrentSpeedAngle', 0, 0),
        691:  ('EPModSkillUsage_AdvanceObjectHasKeyword', 2, 0),
        692:  ('EPModSkillUsage_IsAdvanceAction', 0, 0),
        693:  ('EPMagic_SpellHasKeyword', 2, 0),
        694:  ('GetNoBleedoutRecovery', 0, 0),
        696:  ('EPMagic_SpellHasSkill', 2, 0),
        697:  ('IsAttackType', 2, 0),
        698:  ('IsAllowedToFly', 0, 0),
        699:  ('HasMagicEffectKeyword', 2, 0),
        700:  ('IsCommandedActor', 0, 0),
        701:  ('IsStaggered', 0, 0),
        702:  ('IsRecoiling', 0, 0),
        703:  ('IsExitingInteractionQuick', 0, 0),
        704:  ('IsPathing', 0, 0),
        705:  ('GetShouldHelp', 2, 0),
        706:  ('HasBoundWeaponEquipped', 2, 0),
        707:  ('GetCombatTargetHasKeyword', 2, 0),
        709:  ('GetCombatGroupMemberCount', 0, 0),
        710:  ('IsIgnoringCombat', 0, 0),
        711:  ('GetLightLevel', 0, 0),
        713:  ('SpellHasCastingPerk', 2, 0),
        714:  ('IsBeingRidden', 0, 0),
        715:  ('IsUndead', 0, 0),
        716:  ('GetRealHoursPassed', 0, 0),
        718:  ('IsUnlockedDoor', 0, 0),
        719:  ('IsHostileToActor', 2, 0),
        720:  ('GetTargetHeight', 2, 0),
        721:  ('IsPoison', 0, 0),
        722:  ('WornApparelHasKeywordCount', 2, 0),
        723:  ('GetItemHealthPercent', 0, 0),
        724:  ('EffectWasDualCast', 0, 0),
        725:  ('GetKnockStateEnum', 0, 0),
        726:  ('DoesNotExist', 0, 0),
        730:  ('IsOnFlyingMount', 0, 0),
        731:  ('CanFlyHere', 0, 0),
        732:  ('IsFlyingMountPatrolQueued', 0, 0),
        733:  ('IsFlyingMountFastTravelling', 0, 0),
        734:  ('IsOverEncumbered', 0, 0),
        735:  ('GetActorWarmth', 0, 0),
        # extended by SKSE
        1024: ('GetSKSEVersion', 0, 0),
        1025: ('GetSKSEVersionMinor', 0, 0),
        1026: ('GetSKSEVersionBeta', 0, 0),
        1027: ('GetSKSERelease', 0, 0),
        1028: ('ClearInvalidRegistrations', 0, 0),
    }
    getvatsvalue_index = 407

    #--------------------------------------------------------------------------
    # Leveled Lists
    #--------------------------------------------------------------------------
    leveled_list_types = {b'LVLI', b'LVLN', b'LVSP'}

    #--------------------------------------------------------------------------
    # Import Names
    #--------------------------------------------------------------------------
    names_types = {
        b'ACTI', b'ALCH', b'AMMO', b'APPA', b'ARMO', b'AVIF', b'BOOK', b'CLAS',
        b'CLFM', b'CONT', b'DOOR', b'ENCH', b'EXPL', b'EYES', b'FACT', b'FLOR',
        b'FURN', b'HAZD', b'HDPT', b'INGR', b'KEYM', b'LCTN', b'LIGH', b'MESG',
        b'MGEF', b'MISC', b'MSTT', b'NPC_', b'PERK', b'PROJ', b'QUST', b'RACE',
        b'SCRL', b'SHOU', b'SLGM', b'SNCT', b'SPEL', b'TACT', b'TREE', b'WATR',
        b'WEAP', b'WOOP',
    }

    #--------------------------------------------------------------------------
    # Import Prices
    #--------------------------------------------------------------------------
    pricesTypes = {b'ALCH', b'AMMO', b'APPA', b'ARMO', b'BOOK', b'INGR',
                   b'KEYM', b'LIGH', b'MISC', b'SLGM', b'WEAP'}

    #--------------------------------------------------------------------------
    # Import Stats
    #--------------------------------------------------------------------------
    # The contents of these tuples have to stay fixed because of CSV parsers
    stats_csv_attrs = {
        b'ALCH': ('eid', 'weight', 'value'),
        b'AMMO': ('eid', 'value', 'damage'),
        b'APPA': ('eid', 'weight', 'value'),
        b'ARMO': ('eid', 'weight', 'value', 'armorRating'),
        b'BOOK': ('eid', 'weight', 'value'),
        b'EYES': ('eid', 'flags'),
        b'HDPT': ('eid', 'flags'),
        b'INGR': ('eid', 'weight', 'value'),
        b'KEYM': ('eid', 'weight', 'value'),
        b'LIGH': ('eid', 'weight', 'value', 'duration'),
        b'MISC': ('eid', 'weight', 'value'),
        b'SLGM': ('eid', 'weight', 'value'),
        # criticalEffect at the end since it's a FormID, to mirror how
        # APreserver will join the tuples
        b'WEAP': ('eid', 'weight', 'value', 'damage', 'speed', 'reach',
                  'enchantPoints', 'stagger', 'criticalDamage',
                  'criticalMultiplier', 'criticalEffect'),
    }
    stats_attrs = {r: tuple(x for x in a if x != 'eid')
                   for r, a in stats_csv_attrs.items()} | {
        b'WEAP': ('weight', 'value', 'damage', 'speed', 'reach',
                  'enchantPoints', 'stagger', 'criticalDamage',
                  'criticalMultiplier'),
    }
    stats_fid_attrs = {
        b'WEAP': ('criticalEffect',),
    }

    #--------------------------------------------------------------------------
    # Import Sounds
    #--------------------------------------------------------------------------
    sounds_attrs = {
        b'EXPL': ('expl_sound_level',),
        b'IPCT': ('ipct_sound_level',),
        # mgef_sounds has FormIDs, but will be filtered in MreMgef.keep_fids
        b'MGEF': ('casting_sound_level', 'mgef_sounds'),
        b'PROJ': ('sound_level',),
        b'SNCT': ('staticVolumeMultiplier',),
        # sound_files does not need to loop here
        b'SNDR': ('sound_files', 'looping_type', 'rumble_send_value',
                  'pct_frequency_shift', 'pct_frequency_variance',
                  'descriptor_priority', 'db_variance', 'staticAtten'),
        b'SOPM': ('reverbSendpct', 'outputType', 'ch0_l', 'ch0_r', 'ch0_c',
                  'ch0_lFE', 'ch0_rL', 'ch0_rR', 'ch0_bL', 'ch0_bR', 'ch1_l',
                  'ch1_r', 'ch1_c', 'ch1_lFE', 'ch1_rL', 'ch1_rR', 'ch1_bL',
                  'ch1_bR', 'ch2_l', 'ch2_r', 'ch2_c', 'ch2_lFE', 'ch2_rL',
                  'ch2_rR', 'ch2_bL', 'ch2_bR', 'minDistance', 'maxDistance',
                  'curve1', 'curve2', 'curve3', 'curve4', 'curve5'),
        b'WEAP': ('detectionSoundLevel',),
        # Has FormIDs, but will be filtered in AMreWthr.keep_fids
        b'WTHR': ('sounds',),
    }
    sounds_fid_attrs = {
        b'ACTI': ('sound', 'sound_activation'),
        b'ADDN': ('sound',),
        b'ALCH': ('sound_pickup', 'sound_drop', 'sound_consume'),
        b'AMMO': ('sound_pickup', 'sound_drop'),
        b'APPA': ('sound_pickup', 'sound_drop'),
        b'ARMA': ('footstep_sound',),
        b'ARMO': ('sound_pickup', 'sound_drop'),
        b'ASPC': ('sound', 'use_sound_from_region', 'environment_type'),
        b'BOOK': ('sound_pickup', 'sound_drop'),
        b'CONT': ('sound', 'sound_close'),
        b'DOOR': ('sound', 'sound_close', 'sound_looping'),
        b'EFSH': ('sound_ambient',),
        b'EXPL': ('expl_sound1', 'expl_sound2'),
        b'FLOR': ('sound',),
        b'HAZD': ('hazd_sound',),
        b'INGR': ('sound_pickup', 'sound_drop'),
        b'IPCT': ('sound', 'ipct_sound2'),
        b'KEYM': ('sound_pickup', 'sound_drop'),
        b'LIGH': ('sound',),
        b'MISC': ('sound_pickup', 'sound_drop'),
        b'MSTT': ('sound',),
        b'PROJ': ('sound', 'sound_countdown', 'sound_disable'),
        b'SCRL': ('sound_pickup', 'sound_drop'),
        b'SLGM': ('sound_pickup', 'sound_drop'),
        b'SNCT': ('parent',),
        b'SNDR': ('descriptor_category', 'output_model'),
        b'SOUN': ('soundDescriptor',),
        b'TACT': ('sound',),
        b'TREE': ('sound',),
        b'WATR': ('sound',),
        b'WEAP': ('sound_pickup', 'sound_drop', 'sound', 'attackSound2D',
                  'attackLoopSound', 'attackFailSound', 'idleSound',
                  'equipSound', 'unequipSound'),
    }

    #--------------------------------------------------------------------------
    # Import Cells
    #--------------------------------------------------------------------------
    cellRecAttrs = {
        'C.Acoustic': ('acousticSpace',),
        'C.Climate': ('climate', 'flags.showSky'),
        'C.Encounter': ('encounterZone',),
        'C.ForceHideLand': ('cell_land_flags',),
        'C.ImageSpace': ('imageSpace',),
        ##: Patches unused?
        'C.Light': ('ambientRed', 'ambientGreen', 'ambientBlue', 'unused1',
                    'directionalRed', 'directionalGreen', 'directionalBlue',
                    'unused2', 'fogRed', 'fogGreen', 'fogBlue', 'unused3',
                    'fogNear', 'fogFar', 'directionalXY', 'directionalZ',
                    'directionalFade', 'fogClip', 'fogPower', 'redXplus',
                    'greenXplus', 'blueXplus', 'unknownXplus', 'redXminus',
                    'greenXminus', 'blueXminus', 'unknownXminus', 'redYplus',
                    'greenYplus', 'blueYplus', 'unknownYplus', 'redYminus',
                    'greenYminus', 'blueYminus', 'unknownYminus', 'redZplus',
                    'greenZplus', 'blueZplus', 'unknownZplus', 'redZminus',
                    'greenZminus', 'blueZminus', 'unknownZminus', 'redSpec',
                    'greenSpec', 'blueSpec', 'unknownSpec', 'fresnelPower',
                    'fogColorFarRed', 'fogColorFarGreen', 'fogColorFarBlue',
                    'unused4', 'fogMax', 'lightFadeBegin', 'lightFadeEnd',
                    'inherits', 'lightTemplate',),
        'C.Location': ('location',),
        'C.LockList': ('lockList',),
        'C.MiscFlags': ('flags.isInterior', 'flags.cantFastTravel',
                        'flags.noLODWater', 'flags.handChanged'),
        'C.Music': ('music',),
        'C.Name': ('full',),
        'C.Owner': ('ownership', 'flags.publicPlace'),
        'C.RecordFlags': ('flags1',), # Yes seems funky but thats the way it is
        'C.Regions': ('regions',),
        'C.SkyLighting': ('skyFlags.useSkyLighting',),
        'C.Water': ('water', 'waterHeight', 'waterNoiseTexture',
                    'waterEnvironmentMap', 'flags.hasWater'),
    }
    cell_skip_interior_attrs = {'waterHeight'}

    #--------------------------------------------------------------------------
    # Import Graphics
    #--------------------------------------------------------------------------
    graphicsTypes = {
        b'ACTI': ('model',),
        b'ALCH': ('iconPath', 'model'),
        b'AMMO': ('iconPath', 'model'),
        b'APPA': ('iconPath', 'model'),
        b'ARMA': ('male_model', 'female_model', 'male_model_1st',
                  'female_model_1st', 'biped_flags'),
        b'ARMO': ('maleWorld', 'maleIconPath', 'femaleWorld', 'femaleIconPath',
                  'addons', 'biped_flags'),
        b'BOOK': ('iconPath', 'model'),
        b'CLAS': ('iconPath',),
        b'CONT': ('model',),
        b'DOOR': ('model',),
        b'EFSH': (
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
            'ps_persistent_particle_count', 'ps_particle_lifetime',
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
            'addon_models_scale_in_time', 'addon_models_scale_out_time',
            'fill_color2_red', 'fill_color2_green', 'fill_color2_blue',
            'fill_color3_red', 'fill_color3_green', 'fill_color3_blue',
            'fill_color1_scale', 'fill_color2_scale', 'fill_color3_scale',
            'fill_color1_time', 'fill_color2_time', 'fill_color3_time',
            'color_scale', 'birth_position_offset',
            'birth_position_offset_range_delta', 'psa_start_frame',
            'psa_start_frame_variation', 'psa_end_frame',
            'psa_loop_start_frame', 'psa_loop_start_variation',
            'psa_frame_count', 'psa_frame_count_variation', 'efsh_flags',
            'fill_texture_scale_u', 'fill_texture_scale_v', 'fill_texture',
            'particle_texture', 'holes_texture', 'membrane_palette_texture',
            'particle_palette_texture'),
        b'EXPL': ('model',),
        b'FLOR': ('model',),
        b'FURN': ('model',),
        b'GRAS': ('model',),
        b'HDPT': ('model', 'hdpt_texture_set', 'hdpt_color'),
        b'INGR': ('iconPath', 'model'),
        b'IPCT': ('model', 'effect_duration', 'effect_orientation',
                  'angle_threshold', 'placement_radius', 'ipct_no_decal_data',
                  'impact_result', 'decal_min_width', 'decal_max_width',
                  'decal_min_height', 'decal_max_height', 'decal_depth',
                  'decal_shininess', 'decal_parallax_scale',
                  'decal_parallax_passes', 'decal_flags', 'decal_color_red',
                  'decal_color_green', 'decal_color_blue'),
        b'KEYM': ('iconPath', 'model'),
        b'LIGH': ('iconPath', 'model', 'light_radius', 'light_color_red',
                  'light_color_green', 'light_color_blue', 'light_flags',
                  'light_falloff', 'light_fov', 'light_near_clip',
                  'light_fe_period', 'light_fe_intensity_amplitude',
                  'light_fe_movement_amplitude', 'light_fade'),
        b'LSCR': ('iconPath',),
        b'MGEF': ('dual_casting_scale',),
        b'MISC': ('iconPath', 'model'),
        b'PERK': ('iconPath',),
        b'PROJ': ('model', 'muzzleFlashDuration', 'fadeDuration',
                  'models'),
        b'SLGM': ('iconPath', 'model'),
        b'STAT': ('model',),
        b'TREE': ('model',),
        b'TXST': ('diffuse_texture', 'normal_gloss_texture',
                  'environment_mask_subsurface_tint_texture',
                  'glow_detail_map_texture', 'height_texture',
                  'environment_texture', 'multilayer_texture',
                  'backlight_mask_specular_texture', 'decal_min_width',
                  'decal_max_width', 'decal_min_height', 'decal_max_height',
                  'decal_depth', 'decal_shininess', 'decal_parallax_scale',
                  'decal_parallax_passes', 'decal_flags', 'decal_color_red',
                  'decal_color_green', 'decal_color_blue', 'txst_flags'),
        b'WEAP': ('model', 'model2', 'iconPath'),
        b'WTHR': ('wthrAmbientColors',),
    }
    graphicsFidTypes = {
        b'BOOK': ('inventory_art',),
        b'EFSH': ('addon_models',),
        b'EXPL': ('image_space_modifier', 'expl_light', 'expl_impact_dataset'),
        b'IPCT': ('ipct_texture_set', 'secondary_texture_set'),
        b'MGEF': ('menu_display_object', 'light', 'hit_shader',
                  'enchant_shader', 'projectile', 'explosion', 'casting_art',
                  'hit_effect_art', 'effect_impact_data', 'dual_casting_art',
                  'enchant_art', 'hit_visuals', 'enchant_visuals',
                  'effect_imad'),
        b'PROJ': ('light', 'muzzleFlash', 'explosion', 'decalData'),
        b'SCRL': ('menu_display_object',),
        b'SPEL': ('menu_display_object',),
        b'WEAP': ('firstPersonModelObject',),
    }
    graphicsModelAttrs = {'model', 'model2', 'male_model', 'female_model',
                          'male_model_1st', 'female_model_1st', 'maleWorld',
                          'femaleWorld'}

    #--------------------------------------------------------------------------
    # Import Inventory
    #--------------------------------------------------------------------------
    inventory_types = {b'COBJ', b'CONT', b'NPC_'}

    #--------------------------------------------------------------------------
    # Import Keywords
    #--------------------------------------------------------------------------
    keywords_types = {
        b'ACTI', b'ALCH', b'AMMO', b'ARMO', b'BOOK', b'FLOR', b'FURN', b'INGR',
        b'KEYM', b'LCTN', b'MGEF', b'MISC', b'NPC_', b'RACE', b'SCRL', b'SLGM',
        b'SPEL', b'TACT', b'WEAP',
    }

    #--------------------------------------------------------------------------
    # Import Text
    #--------------------------------------------------------------------------
    text_types = {
        b'ACTI': ('activate_text_override',),
        b'ALCH': ('description',),
        b'AMMO': ('description', 'short_name'),
        b'APPA': ('description',),
        b'ARMO': ('description',),
        b'ASTP': ('male_parent_title', 'female_parent_title',
                  'male_child_title', 'female_child_title'),
        b'AVIF': ('description', 'abbreviation'),
        b'BOOK': ('description', 'book_text'),
        b'CLAS': ('description',),
        b'COLL': ('description',),
        b'FLOR': ('activate_text_override',),
        b'LSCR': ('description',),
        b'MESG': ('description',),
        b'MGEF': ('magic_item_description',),
        b'NPC_': ('short_name',),
        b'PERK': ('description',),
        b'QUST': ('description',),
        # omit RACE - covered by R.Description
        b'SCRL': ('description',),
        b'SHOU': ('description',),
        b'SPEL': ('description',),
        b'WEAP': ('description',),
        b'WOOP': ('translation',),
    }

    #--------------------------------------------------------------------------
    # Import Object Bounds
    #--------------------------------------------------------------------------
    object_bounds_types = {
        b'ACTI', b'ADDN', b'ALCH', b'AMMO', b'APPA', b'ARMO', b'ARTO', b'ASPC',
        b'BOOK', b'CONT', b'DOOR', b'DUAL', b'ENCH', b'EXPL', b'FLOR', b'FURN',
        b'GRAS', b'HAZD', b'IDLM', b'INGR', b'KEYM', b'LIGH', b'LVLI', b'LVLN',
        b'LVSP', b'MISC', b'MSTT', b'NPC_', b'PROJ', b'SCRL', b'SLGM', b'SOUN',
        b'SPEL', b'STAT', b'TACT', b'TREE', b'TXST', b'WEAP',
    }

    #--------------------------------------------------------------------------
    # Contents Checker
    #--------------------------------------------------------------------------
    # Entry types used for COBJ, CONT, LVLI and NPC_
    _common_entry_types = {b'ALCH', b'AMMO', b'APPA', b'ARMO', b'BOOK',
                           b'INGR', b'KEYM', b'LIGH', b'LVLI', b'MISC',
                           b'SLGM', b'SCRL', b'WEAP'}
    cc_valid_types = {
        b'COBJ': _common_entry_types,
        b'CONT': _common_entry_types,
        b'LVLN': {b'LVLN', b'NPC_'},
        b'LVLI': _common_entry_types,
        b'LVSP': {b'LVSP', b'SPEL'},
        b'NPC_': _common_entry_types,
        b'OTFT': {b'ARMO', b'LVLI'},
    }
    cc_passes = (
        (leveled_list_types, 'entries', 'listId'),
        (inventory_types,    'items',   'item'),
        ({b'OTFT'},          'items'),
    )

    #--------------------------------------------------------------------------
    # Import Destructible
    #--------------------------------------------------------------------------
    destructible_types = {b'ACTI', b'ALCH', b'AMMO', b'APPA', b'ARMO', b'BOOK',
                          b'CONT', b'DOOR', b'FLOR', b'FURN', b'KEYM', b'LIGH',
                          b'MISC', b'MSTT', b'NPC_', b'PROJ', b'SCRL', b'SLGM',
                          b'TACT', b'WEAP'}

    #--------------------------------------------------------------------------
    # Import Actors
    #--------------------------------------------------------------------------
    actor_importer_attrs = {
        b'NPC_': {
            'Actors.ACBS': (
                'bleedout_override', 'calc_max_level', 'calc_min_level',
                'disposition_base', 'npc_flags.npc_auto_calc',
                'npc_flags.bleedout_override',
                'npc_flags.does_not_affect_stealth',
                'npc_flags.does_not_bleed', 'npc_flags.npc_essential',
                'npc_flags.npc_female', 'npc_flags.npc_invulnerable',
                'npc_flags.is_chargen_face_preset', 'npc_flags.npc_is_ghost',
                'npc_flags.looped_audio', 'npc_flags.looped_script',
                'npc_flags.opposite_gender_anims', 'npc_flags.npc_protected',
                'npc_flags.npc_respawn', 'npc_flags.simple_actor',
                'npc_flags.npc_summonable', 'npc_flags.npc_unique',
                'health_offset', 'magicka_offset', 'speed_multiplier',
                'stamina_offset',
                # This flag directly impacts how the level_offset is
                # calculated, so use a fused attribute to always carry them
                # forward together
                ('npc_flags.pc_level_offset', 'level_offset'),
            ),
            'Actors.AIData': (
                'ai_aggression', 'ai_aggro_radius_behavior', 'ai_assistance',
                'ai_attack', 'ai_confidence', 'ai_energy_level', 'ai_mood',
                'ai_responsibility', 'ai_warn', 'ai_warn_attack',
            ),
            'Actors.RecordFlags': ('flags1',),
            ##: This should probably be imported as one or two attributes,
            # meaning NPC_\DNAM should become a MelLists
            'Actors.Stats': (
                'alchemySO', 'alchemySV', 'alterationSO', 'alterationSV',
                'blockSO', 'blockSV', 'conjurationSO', 'conjurationSV',
                'destructionSO', 'destructionSV', 'enchantingSO',
                'enchantingSV', 'health', 'heavyArmorSO', 'heavyArmorSV',
                'illusionSO', 'illusionSV', 'lightArmorSO', 'lightArmorSV',
                'lockpickingSO', 'lockpickingSV', 'magicka', 'marksmanSO',
                'marksmanSV', 'oneHandedSO', 'oneHandedSV', 'pickpocketSO',
                'pickpocketSV', 'restorationSO', 'restorationSV', 'smithingSO',
                'smithingSV', 'sneakSO', 'sneakSV', 'speechcraftSO',
                'speechcraftSV', 'stamina', 'twoHandedSO', 'twoHandedSV',
            ),
        },
    }
    actor_importer_fid_attrs = {
        b'NPC_': {
            'Actors.CombatStyle': ('combat_style',),
            'Actors.DeathItem': ('death_item',),
            'Actors.Voice': ('voice',),
            'NPC.AIPackageOverrides': (
                'override_package_list_spectator',
                'override_package_list_observe_dead_body',
                'override_package_list_guard_warn',
                'override_package_list_combat',
            ),
            'NPC.AttackRace': ('attack_race',),
            'NPC.Class': ('npc_class',),
            'NPC.CrimeFaction': ('crime_faction',),
            'NPC.DefaultOutfit': ('default_outfit',),
            'NPC.Race': ('race',),
        }
    }

    #--------------------------------------------------------------------------
    # Import Spell Stats
    #--------------------------------------------------------------------------
    # The contents of these tuples have to stay fixed because of CSV parsers
    spell_stats_attrs = ('eid', 'cost', 'spellType', 'charge_time',
                         'cast_type', 'spell_target_type', 'castDuration',
                         'range', 'dataFlags')
    spell_stats_fid_attrs = ('halfCostPerk',)
    # halfCostPerk at the end since it's a FormID, to mirror how APreserver
    # will join the tuples
    spell_stats_csv_attrs = ('eid', 'cost', 'spellType', 'charge_time',
                             'cast_type', 'spell_target_type', 'castDuration',
                             'range', 'dataFlags', 'halfCostPerk')
    spell_stats_types = {b'SCRL', b'SPEL'}

    #--------------------------------------------------------------------------
    # Tweak Actors
    #--------------------------------------------------------------------------
    actor_tweaks = {
        'OppositeGenderAnimsPatcher_Female',
        'OppositeGenderAnimsPatcher_Male',
    }

    #--------------------------------------------------------------------------
    # Tweak Assorted
    #--------------------------------------------------------------------------
    assorted_tweaks = {
        'AssortedTweak_ArmorPlayable',
        'AssortedTweak_NoLightFlicker',
        'AssortedTweak_PotionWeight',
        'AssortedTweak_IngredientWeight',
        'AssortedTweak_PotionWeightMinimum',
        'AssortedTweak_StaffWeight',
        'AssortedTweak_HarvestChance',
        'AssortedTweak_WindSpeed',
        'AssortedTweak_UniformGroundcover',
        'AssortedTweak_SetSoundAttenuationLevels',
        'AssortedTweak_SetSoundAttenuationLevels_NirnrootOnly',
        'AssortedTweak_LightFadeValueFix',
        'AssortedTweak_TextlessLSCRs',
        'AssortedTweak_AllWaterDamages',
        'AssortedTweak_AbsorbSummonFix',
        'AssortedTweak_BookWeight',
        'AssortedTweak_AttackSpeedStavesMinimum',
        'AssortedTweak_AttackSpeedStavesMaximum',
    }
    staff_condition = ('animationType', 8)

    #--------------------------------------------------------------------------
    # Tweak Names
    #--------------------------------------------------------------------------
    names_tweaks = {
        'NamesTweak_BodyPartCodes',
        'NamesTweak_Body_Armor_Tes5',
        'NamesTweak_Scrolls',
        'NamesTweak_Spells_Tes5',
        'NamesTweak_Weapons_Tes5',
        'NamesTweak_DwarvenToDwemer',
        'NamesTweak_DwarfsToDwarves',
        'NamesTweak_StaffsToStaves',
        'NamesTweak_RenameGold',
    }
    body_part_codes = ('HAGBMRS', 'HBALMRS')
    text_replacer_rpaths = {
        b'ACTI': ('full', 'activate_text_override'),
        b'ALCH': ('full', 'description'),
        b'AMMO': ('full', 'description', 'short_name'),
        b'APPA': ('full', 'description'),
        b'ARMO': ('full', 'description'),
        b'ASTP': ('male_parent_title', 'female_parent_title',
                  'male_child_title', 'female_child_title'),
        b'AVIF': ('full', 'description', 'abbreviation'),
        b'BOOK': ('full', 'description', 'book_text'),
        b'CLAS': ('full', 'description'),
        b'CLFM': ('full',),
        b'COLL': ('description',),
        b'CONT': ('full',),
        b'DOOR': ('full',),
        b'ENCH': ('full',),
        b'EXPL': ('full',),
        b'EYES': ('full',),
        b'FACT': ('full', 'ranks[*].male_title', 'ranks[*].female_title'),
        b'FLOR': ('full', 'activate_text_override'),
        b'FURN': ('full',),
        b'GMST': ('value',),
        b'HAZD': ('full',),
        b'HDPT': ('full',),
        b'INGR': ('full',),
        b'KEYM': ('full',),
        b'LCTN': ('full',),
        b'LIGH': ('full',),
        b'LSCR': ('description',),
        b'MESG': ('full', 'description', 'menu_buttons[*].button_text'),
        b'MGEF': ('full', 'magic_item_description'),
        b'MISC': ('full',),
        b'MSTT': ('full',),
        b'NPC_': ('full', 'short_name'),
        b'PERK': ('full', 'description'),
        b'PROJ': ('full',),
        b'QUST': ('full', 'description',
                  'stages[*].log_entries[*].log_entry_text',
                  'objectives[*].display_text'),
        b'RACE': ('full', 'description'),
        b'SCRL': ('full', 'description'),
        b'SHOU': ('full', 'description'),
        b'SLGM': ('full',),
        b'SNCT': ('full',),
        b'SPEL': ('full', 'description'),
        b'TACT': ('full',),
        b'TREE': ('full',),
        b'WATR': ('full',),
        b'WEAP': ('full', 'description'),
        b'WOOP': ('full',),
    }
    gold_attrs = lambda self: {
        'eid': 'Gold001',
        'bounds.boundX1': -2,
        'bounds.boundY1': -2,
        'bounds.boundZ1': 0,
        'bounds.boundX2': 2,
        'bounds.boundY2': 2,
        'bounds.boundZ2': 0,
        'model.modPath': r'Clutter\Coin01.nif',
        'model.alternateTextures': None,
        'iconPath': r'Clutter\Coin01.dds',
        'sound_pickup': self.master_fid(0x03E952), # ITMGoldUpSD
        'sound_drop': self.master_fid(0x03E955), # ITMGoldDownSD
        'keywords': [self.master_fid(0x0914E9)], # VendorItemClutter
        'value': 1,
        'weight': 0.0,
    }

    #--------------------------------------------------------------------------
    # Tweak Settings
    #--------------------------------------------------------------------------
    settings_tweaks = {
        'GlobalsTweak_Timescale_Tes5',
        'GmstTweak_Msg_SoulCaptured',
        'GmstTweak_Actor_StrengthEncumbranceMultiplier',
        'GmstTweak_AI_MaxActiveActors_Tes5',
        'GmstTweak_Arrow_RecoveryFromActor_Tes5',
        'GmstTweak_Arrow_Speed',
        'GmstTweak_World_CellRespawnTime_Tes5',
        'GmstTweak_World_CellRespawnTime_Cleared',
        'GmstTweak_Combat_Alchemy',
        'GmstTweak_Combat_MaxActors_Tes5',
        'GmstTweak_Combat_RechargeWeapons',
        'GmstTweak_Actor_MaxCompanions',
        'GmstTweak_Crime_AlarmDistance',
        'GmstTweak_Bounty_Assault_Tes5',
        'GmstTweak_Crime_PrisonDurationModifier',
        'GmstTweak_Bounty_Jailbreak_Tes5',
        'GmstTweak_Bounty_Murder',
        'GmstTweak_Bounty_Pickpocketing',
        'GmstTweak_Bounty_Trespassing_Tes5',
        'GmstTweak_Magic_MaxResistance',
        'GmstTweak_Magic_MaxSummons',
        'GmstTweak_Actor_VerticalObjectDetection',
        'GmstTweak_Actor_MaxJumpHeight',
        'GmstTweak_Player_FastTravelTimeMultiplier',
        'GmstTweak_Combat_CriticalHitChance',
        'GmstTweak_Actor_UnconsciousnessDuration',
        'GmstTweak_Compass_RecognitionDistance',
        'GmstTweak_Player_HorseTurningSpeed',
        'GmstTweak_Camera_PCDeathTime',
        'GmstTweak_Actor_GreetingDistance',
        'GmstTweak_Bounty_HorseTheft_Tes5',
        'GmstTweak_Player_InventoryQuantityPrompt',
        'GmstTweak_Player_MaxDraggableWeight_Tes5',
        'GmstTweak_Warning_InteriorDistanceToHostiles',
        'GmstTweak_Warning_ExteriorDistanceToHostiles',
        'GmstTweak_Combat_MaximumArmorRating_Tes5',
        'GmstTweak_Arrow_MaxArrowsAttachedToNPC',
        'GmstTweak_Combat_DisableProjectileDodging',
        'GmstTweak_Combat_MaxAllyHitsInCombat',
        'GmstTweak_Combat_MaxAllyHitsOutOfCombat',
        'GmstTweak_Actor_MerchantRestockTime',
        'GmstTweak_Player_FallDamageThreshold',
        'GmstTweak_Player_SprintingCost',
        'GmstTweak_Visuals_MasserSize',
        'GmstTweak_Visuals_MasserSpeed',
        'GmstTweak_Visuals_SecundaSize',
        'GmstTweak_Visuals_SecundaSpeed',
        'GmstTweak_AI_BumpReactionDelay',
        'GmstTweak_Magic_MaxActiveRunes',
        'GmstTweak_Crime_PickpocketingChance',
        'GmstTweak_Actor_FasterShouts',
        'GmstTweak_Combat_FasterTwo_HandedWeapons',
        'GmstTweak_Actor_TrainingLimit_Tes5',
        'GmstTweak_Player_UnderwaterBreathControl',
        'GmstTweak_Combat_StealthDamageBonus',
        'GmstTweak_Msg_CannotEquipItemFix',
        'GmstTweak_Msg_AutoSaving',
        'GmstTweak_Msg_NoFastTravel',
        'GmstTweak_Msg_QuickLoad',
        'GmstTweak_Msg_QuickSave',
        'GmstTweak_Msg_NotEnoughCharge_Tes5',
        'GmstTweak_Msg_CarryingTooMuch',
        'GmstTweak_CostMultiplier_Enchantment',
        'GmstTweak_Magic_InvisibilityDetectionDifficulty',
        'GmstTweak_Bounty_Shapeshifting',
        'GmstTweak_SoulTrap_LesserSoulLevel',
        'GmstTweak_SoulTrap_CommonSoulLevel',
        'GmstTweak_SoulTrap_GreaterSoulLevel',
        'GmstTweak_SoulTrap_GrandSoulLevel',
        'GmstTweak_AI_ConversationChance_Tes5',
        'GmstTweak_AI_ConversationChance_Interior',
        'GmstTweak_AI_MaxDeadActors',
        'GmstTweak_Bounty_Theft',
        'GmstTweak_Prompt_Activate',
        'GmstTweak_Prompt_Open',
        'GmstTweak_Prompt_Read',
        'GmstTweak_Prompt_Sit',
        'GmstTweak_Prompt_Take',
        'GmstTweak_Prompt_Talk',
        'GmstTweak_Msg_NoSoulGemLargeEnough',
        'GmstTweak_Combat_SpeakOnHitChance',
        'GmstTweak_Combat_SpeakOnHitThreshold',
        'GmstTweak_Combat_MaxFriendHitsInCombat',
        'GmstTweak_Combat_MaxFriendHitsOutOfCombat',
    }

    #--------------------------------------------------------------------------
    # Import Relations
    #--------------------------------------------------------------------------
    relations_attrs = ('faction', 'mod', 'group_combat_reaction')

    #--------------------------------------------------------------------------
    # Import Enchantment Stats
    #--------------------------------------------------------------------------
    ench_stats_attrs = ('enchantment_cost', 'enit_flags', 'cast_type',
                        'enchantment_amount', 'enchantment_target_type',
                        'enchantment_type', 'charge_time')
    ench_stats_fid_attrs = ('base_enchantment', 'worn_restrictions')

    #--------------------------------------------------------------------------
    # Import Effect Stats
    #--------------------------------------------------------------------------
    mgef_stats_attrs = (
        'flags', 'base_cost', 'magic_skill', 'resist_value', 'taper_weight',
        'minimum_skill_level', 'spellmaking_area', 'spellmaking_casting_time',
        'taper_curve', 'taper_duration', 'second_av_weight',
        'effect_archetype', 'actorValue', 'casting_type', 'delivery',
        'second_av', 'skill_usage_multiplier', 'script_effect_ai_score',
        'script_effect_ai_delay_time')
    mgef_stats_fid_attrs = ('associated_item', 'equip_ability',
                            'perk_to_apply')

    #--------------------------------------------------------------------------
    # Import Races
    #--------------------------------------------------------------------------
    import_races_attrs = {
        b'RACE': {
            'R.Body-Size-F': ('femaleHeight', 'femaleWeight'),
            'R.Body-Size-M': ('maleHeight', 'maleWeight'),
            'R.Description': ('description',),
            'R.Skills': ('skills',),
            'R.Stats': ('starting_health', 'starting_magicka',
                        'starting_stamina', 'base_carry_weight',
                        'health_regen', 'magicka_regen', 'stamina_regen',
                        'unarmed_damage', 'unarmed_reach'),
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
    enchantment_types = {b'ARMO', b'EXPL', b'WEAP'}

    #--------------------------------------------------------------------------
    # Tweak Races
    #--------------------------------------------------------------------------
    race_tweaks = {
        'RaceTweak_PlayableHeadParts',
        'RaceTweak_GenderlessHeadParts',
        'RaceTweak_ForceBehaviorGraphGender_Female',
        'RaceTweak_ForceBehaviorGraphGender_Male',
        'RaceTweak_AllHeadParts',
    }

    #--------------------------------------------------------------------------
    # Timescale Checker
    #--------------------------------------------------------------------------
    # Same story as in Nehrim for Enderal too - devs changed timescale, but
    # forgot to adjust wave periods. So keep at 20 for Enderal.
    default_wp_timescale = 20

    # Record information
    top_groups = [
        b'GMST', b'KYWD', b'LCRT', b'AACT', b'TXST', b'GLOB', b'CLAS', b'FACT',
        b'HDPT', b'HAIR', b'EYES', b'RACE', b'SOUN', b'ASPC', b'MGEF', b'SCPT',
        b'LTEX', b'ENCH', b'SPEL', b'SCRL', b'ACTI', b'TACT', b'ARMO', b'BOOK',
        b'CONT', b'DOOR', b'INGR', b'LIGH', b'MISC', b'APPA', b'STAT', b'SCOL',
        b'MSTT', b'PWAT', b'GRAS', b'TREE', b'CLDC', b'FLOR', b'FURN', b'WEAP',
        b'AMMO', b'NPC_', b'LVLN', b'KEYM', b'ALCH', b'IDLM', b'COBJ', b'PROJ',
        b'HAZD', b'SLGM', b'LVLI', b'WTHR', b'CLMT', b'SPGD', b'RFCT', b'REGN',
        b'NAVI', b'CELL', b'WRLD', b'DIAL', b'QUST', b'IDLE', b'PACK', b'CSTY',
        b'LSCR', b'LVSP', b'ANIO', b'WATR', b'EFSH', b'EXPL', b'DEBR', b'IMGS',
        b'IMAD', b'FLST', b'PERK', b'BPTD', b'ADDN', b'AVIF', b'CAMS', b'CPTH',
        b'VTYP', b'MATT', b'IPCT', b'IPDS', b'ARMA', b'ECZN', b'LCTN', b'MESG',
        b'RGDL', b'DOBJ', b'LGTM', b'MUSC', b'FSTP', b'FSTS', b'SMBN', b'SMQN',
        b'SMEN', b'DLBR', b'MUST', b'DLVW', b'WOOP', b'SHOU', b'EQUP', b'RELA',
        b'SCEN', b'ASTP', b'OTFT', b'ARTO', b'MATO', b'MOVT', b'SNDR', b'DUAL',
        b'SNCT', b'SOPM', b'COLL', b'CLFM', b'REVB',
    ]

    @classmethod
    def init(cls, _package_name=None):
        super().init(_package_name or __name__)
        cls._import_records(__name__)

    @classmethod
    def _import_records(cls, package_name, plugin_form_vers=43):
        # package name is skyrim here
        super()._import_records(package_name, plugin_form_vers)
        cls.mergeable_sigs = set(cls.top_groups) - {
            b'RGDL', b'SCPT', b'CELL', b'SCEN', b'SCOL', b'HAIR', b'CLDC',
            b'DIAL', b'NAVI', b'PWAT', b'WRLD'}
        from ... import brec as _brec_
        _brec_.RecordType.simpleTypes = cls.mergeable_sigs # that's what it did

GAME_TYPE = SkyrimGameInfo
