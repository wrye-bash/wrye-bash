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
from ... import bolt

_GOG_IDS = [
    1458058109, # Game
    1242989820, # Package
]

class OblivionGameInfo(PatchGame):
    """GameInfo override for TES IV: Oblivion."""
    displayName = u'Oblivion'
    fsName = u'Oblivion'
    altName = u'Wrye Bash'
    game_icon = u'oblivion_%u.png'
    bash_root_prefix = u'Oblivion'
    bak_game_name = u'Oblivion'
    template_dir = u'Oblivion'
    bash_patches_dir = u'Oblivion'
    my_games_name = u'Oblivion'
    appdata_name = u'Oblivion'
    launch_exe = u'Oblivion.exe'
    game_detect_includes = {'OblivionLauncher.exe'}
    # NehrimLauncher.exe is here to make sure we don't ever detect Nehrim as
    # Oblivion
    game_detect_excludes = (set(GOGMixin.get_unique_filenames(_GOG_IDS)) |
                            WS_COMMON_FILES | {'NehrimLauncher.exe'})
    version_detect_file = u'Oblivion.exe'
    master_file = bolt.FName(u'Oblivion.esm')
    taglist_dir = u'Oblivion'
    loot_dir = u'Oblivion'
    loot_game_name = 'Oblivion'
    boss_game_name = u'Oblivion'
    registry_keys = [(r'Bethesda Softworks\Oblivion', 'Installed Path')]
    nexusUrl = u'https://www.nexusmods.com/oblivion/'
    nexusName = u'Oblivion Nexus'
    nexusKey = u'bash.installers.openOblivionNexus.continue'

    using_txt_file = False
    has_standalone_pluggy = True
    plugin_name_specific_dirs = GameInfo.plugin_name_specific_dirs + [
        _j('textures', 'faces'),
    ]
    check_legacy_paths = True

    @classmethod
    def check_loaded_mod(cls, patch_file, modFile):
        super().check_loaded_mod(patch_file, modFile)
        ##: Could we adapt this for FO3/FNV?
        mod_fn_key = modFile.fileInfo.fn_key
        if (scpt_block := modFile.tops.get(b'SCPT')) and mod_fn_key != cls.master_file:
            gls = scpt_block.id_records.get(cls.master_fid(0x00025811))
            if gls and gls.compiled_size == 4 and gls.last_index == 0:
                patch_file.compiledAllMods.append(mod_fn_key)

    class Ck(GameInfo.Ck):
        ck_abbrev = u'TESCS'
        long_name = u'Construction Set'
        exe = u'TESConstructionSet.exe'
        se_args = u'-editor'
        image_name = u'tescs%s.png'

    class Se(GameInfo.Se):
        se_abbrev = u'OBSE'
        long_name = u'Oblivion Script Extender'
        exe = u'obse_loader.exe'
        # Not sure why we need obse_1_2_416.dll, was there before refactoring
        ver_files = [u'obse_loader.exe', u'obse_steam_loader.dll',
                     u'obse_1_2_416.dll']
        plugin_dir = u'OBSE'
        cosave_tag = u'OBSE'
        cosave_ext = u'.obse'
        url = u'http://obse.silverlock.org/'
        url_tip = u'http://obse.silverlock.org/'
        limit_fixer_plugins = [u'mod_limit_fix.dll', u'Trifle.dll']

    class Ge(GameInfo.Ge):
        ge_abbrev = u'OBGE'
        long_name = u'Oblivion Graphics Extender'
        exe = [(u'obse', u'plugins', u'obge.dll'),
               (u'obse', u'plugins', u'obgev2.dll'),
               (u'obse', u'plugins', u'oblivionreloaded.dll'),
               ]
        url = u'https://www.nexusmods.com/oblivion/mods/30054'
        url_tip = u'https://www.nexusmods.com/oblivion'

    class Ini(GameInfo.Ini):
        allow_new_lines = False
        bsa_redirection_key = (u'Archive', u'sArchiveList')
        default_ini_file = u'Oblivion_default.ini'
        dropdown_inis = [u'Oblivion.ini']
        has_obse_inis = True
        supports_mod_inis = False

    class Ess(GameInfo.Ess):
        canEditMore = True
        can_safely_remove_masters = True

    class Bsa(GameInfo.Bsa):
        allow_reset_timestamps = True
        # Oblivion accepts the base name and literally *anything* after
        # that. E.g. MyModMeshes.bsa will load from a MyMod.esp plugin
        attachment_regex = u'.*'
        redate_dict = bolt.DefaultFNDict(lambda: 1136066400, { # '2006-01-01',
            u'Oblivion - Voices1.bsa': 1104616800, # '2005-01-02'
            u'Oblivion - Voices2.bsa': 1104703200, # '2005-01-03'
            u'Oblivion - Meshes.bsa': 1104789600,  # '2005-01-04'
            u'Oblivion - Sounds.bsa': 1104876000,  # '2005-01-05'
            u'Oblivion - Misc.bsa': 1104962400,    # '2005-01-06'
        })
        valid_versions = {0x67}

    class Xe(GameInfo.Xe):
        full_name = u'TES4Edit'
        xe_key_prefix = u'tes4View'

    class Bain(GameInfo.Bain):
        data_dirs = GameInfo.Bain.data_dirs | {
            '_tejon', # 3P: tejon's mods
            'config', # 3P: mod config files (INIs)
            'distantlod',
            'enhanced economy', # 3P: Enhanced Economy
            'facegen',
            'fonts',
            'knights - revelation music', # 3P: KotN Revelation
            'menus',
            'obse', # 3P: OBSE
            'pluggy', # 3P: Pluggy
            'scripts',
            'shaders',
            'streamline', # 3P: Streamline
            'trees',
        }
        keep_data_dirs = {
            _j('obse', 'plugins', 'componentdlls', 'cse'),
            'lsdata'
        }
        keep_data_files = {
            _j('obse', 'plugins', 'construction set extender.dll'),
            _j('obse', 'plugins', 'construction set extender.ini'),
        }
        keep_data_file_prefixes = {
            _j('meshes', 'characters', '_male', 'specialanims',
                '0femalevariablewalk_'),
        }
        lod_meshes_dir = _j('meshes', 'landscape', 'lod')
        lod_textures_dir = _j('textures', 'landscapelod', 'generated')
        lod_textures_normals_suffix = '_fn'
        no_skip_dirs = GameInfo.Bain.no_skip_dirs | {
            'enhanced economy': {'.txt'},
        }
        skip_bain_refresh = {
            u'tes4edit backups',
            u'tes4edit cache',
            u'bgsee',
            u'conscribe logs',
        }
        wrye_bash_data_files = {'archiveinvalidationinvalidated!.bsa'}

    class Esp(GameInfo.Esp):
        canBash = True
        canEditHeader = True
        sort_lvsp_after_spel = True
        stringsFiles = []
        validHeaderVersions = (0.8, 1.0)

    allTags = PatchGame.allTags | {'IIM', 'NoMerge'}
    patchers = {
        'AliasPluginNames', 'CoblCatalogs', 'CoblExhaustion',
        'ContentsChecker', 'ImportActors', 'ImportActorsAIPackages',
        'ImportActorsFaces', 'ImportActorsFactions', 'ImportActorsSpells',
        'ImportCells', 'ImportEffectStats', 'ImportEnchantments',
        'ImportEnchantmentStats', 'ImportGraphics', 'ImportInventory',
        'ImportNames', 'ImportRaces', 'ImportRacesRelations',
        'ImportRacesSpells', 'ImportRelations', 'ImportRoads', 'ImportScripts',
        'ImportSounds', 'ImportSpellStats', 'ImportStats', 'ImportText',
        'LeveledLists', 'MergePatches', 'MorphFactions', 'NpcChecker',
        'RaceChecker', 'ReplaceFormIDs', 'SEWorldTests', 'TimescaleChecker',
        'TweakActors', 'TweakAssorted', 'TweakClothes', 'TweakNames',
        'TweakRaces', 'TweakSettings',
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
        0x23fe9 : _(u'Argonian'),
        0x224fc : _(u'Breton'),
        0x191c1 : _(u'Dark Elf'),
        0x19204 : _(u'High Elf'),
        0x00907 : _(u'Imperial'),
        0x22c37 : _(u'Khajiit'),
        0x224fd : _(u'Nord'),
        0x191c0 : _(u'Orc'),
        0x00d43 : _(u'Redguard'),
        0x00019 : _(u'Vampire'),
        0x223c8 : _(u'Wood Elf'),
        }
    raceShortNames = {
        0x23fe9 : u'Arg',
        0x224fc : u'Bre',
        0x191c1 : u'Dun',
        0x19204 : u'Alt',
        0x00907 : u'Imp',
        0x22c37 : u'Kha',
        0x224fd : u'Nor',
        0x191c0 : u'Orc',
        0x00d43 : u'Red',
        0x223c8 : u'Bos',
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

    bethDataFiles = {
        'dlcbattlehorncastle.bsa',
        'dlcbattlehorncastle.esp',
        'dlcfrostcrag.bsa',
        'dlcfrostcrag.esp',
        'dlchorsearmor.bsa',
        'dlchorsearmor.esp',
        'dlcmehrunesrazor.esp',
        'dlcorrery.bsa',
        'dlcorrery.esp',
        'dlcshiveringisles - meshes.bsa',
        'dlcshiveringisles - sounds.bsa',
        'dlcshiveringisles - textures.bsa',
        'dlcshiveringisles - voices.bsa',
        'dlcshiveringisles.esp',
        'dlcspelltomes.esp',
        'dlcthievesden.bsa',
        'dlcthievesden.esp',
        'dlcvilelair.bsa',
        'dlcvilelair.esp',
        'knights.bsa',
        'knights.esp',
        'oblivion - meshes.bsa',
        'oblivion - misc.bsa',
        'oblivion - sounds.bsa',
        'oblivion - textures - compressed.bsa',
        'oblivion - textures - compressed.bsa.orig',
        'oblivion - voices1.bsa',
        'oblivion - voices2.bsa',
        'oblivion.esm',
        'oblivion_1.1b.esm',
        'oblivion_1.1.esm',
        'oblivion_gbr si.esm',
        'oblivion_goty non-si.esm',
        'oblivion_si.esm',
    }
    # Function Info -----------------------------------------------------------
    # 0: no param; 1: int param; 2: FormID param; 3: float param
    condition_function_data = {
        1:    ('GetDistance', 2, 0),
        5:    ('GetLocked', 0, 0),
        6:    ('GetPos', 1, 0),
        8:    ('GetAngle', 1, 0),
        10:   ('GetStartingPos', 1, 0),
        11:   ('GetStartingAngle', 1, 0),
        12:   ('GetSecondsPassed', 0, 0),
        14:   ('GetActorValue', 1, 0),
        18:   ('GetCurrentTime', 0, 0),
        24:   ('GetScale', 0, 0),
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
        53:   ('GetScriptVariable', 2, 1),
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
        79:   ('GetQuestVariable', 2, 1),
        80:   ('GetLevel', 0, 0),
        81:   ('GetArmorRating', 0, 0),
        84:   ('GetDeadCount', 2, 0),
        91:   ('GetIsAlerted', 0, 0),
        98:   ('GetPlayerControlsDisabled', 0, 0),
        99:   ('GetHeadingAngle', 2, 0),
        101:  ('IsWeaponOut', 0, 0),
        102:  ('IsTorchOut', 0, 0),
        103:  ('IsShieldOut', 0, 0),
        104:  ('IsYielding', 0, 0),
        106:  ('IsFacingUp', 0, 0),
        107:  ('GetKnockedState', 0, 0),
        108:  ('GetWeaponAnimType', 0, 0),
        109:  ('GetWeaponSkillType', 0, 0),
        110:  ('GetCurrentAIPackage', 0, 0),
        111:  ('IsWaiting', 0, 0),
        112:  ('IsIdlePlaying', 0, 0),
        116:  ('GetCrimeGold', 0, 0),
        122:  ('GetCrime', 2, 1),
        125:  ('IsGuard', 0, 0),
        127:  ('CanPayCrimeGold', 0, 0),
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
        171:  ('IsPlayerInJail', 0, 0),
        172:  ('GetTalkedToPCParam', 2, 0),
        175:  ('IsPCSleeping', 0, 0),
        176:  ('IsPCAMurderer', 0, 0),
        180:  ('GetDetectionLevel', 2, 0),
        182:  ('GetEquipped', 2, 0),
        185:  ('IsSwimming', 0, 0),
        190:  ('GetAmountSoldStolen', 0, 0),
        193:  ('GetPCExpelled', 2, 0),
        195:  ('GetPCFactionMurder', 2, 0),
        197:  ('GetPCFactionSteal', 2, 0),
        199:  ('GetPCFactionAttack', 2, 0),
        201:  ('GetPCFactionSubmitAuthority', 2, 0),
        203:  ('GetDestroyed', 0, 0),
        214:  ('HasMagicEffect', 2, 0),
        215:  ('GetDoorDefaultOpen', 0, 0),
        223:  ('IsSpellTarget', 2, 0),
        224:  ('GetIsPlayerBirthsign', 2, 0),
        225:  ('GetPersuasionNumber', 0, 0),
        227:  ('HasVampireFed', 0, 0),
        228:  ('GetIsClassDefault', 2, 0),
        229:  ('GetClassDefaultMatch', 0, 0),
        230:  ('GetInCellParam', 2, 2),
        237:  ('GetIsGhost', 0, 0),
        242:  ('GetUnconscious', 0, 0),
        244:  ('GetRestrained', 0, 0),
        246:  ('GetIsUsedItem', 2, 0),
        247:  ('GetIsUsedItemType', 1, 0),
        249:  ('GetPCFame', 0, 0),
        251:  ('GetPCInfamy', 0, 0),
        254:  ('GetIsPlayableRace', 0, 0),
        255:  ('GetOffersServicesNow', 0, 0),
        258:  ('GetUsedItemLevel', 0, 0),
        259:  ('GetUsedItemActivate', 0, 0),
        264:  ('GetBarterGold', 0, 0),
        265:  ('IsTimePassing', 0, 0),
        266:  ('IsPleasant', 0, 0),
        267:  ('IsCloudy', 0, 0),
        274:  ('GetArmorRatingUpperBody', 0, 0),
        277:  ('GetBaseActorValue', 1, 0),
        278:  ('IsOwner', 2, 0),
        280:  ('IsCellOwner', 2, 2),
        282:  ('IsHorseStolen', 0, 0),
        285:  ('IsLeftUp', 0, 0),
        286:  ('IsSneaking', 0, 0),
        287:  ('IsRunning', 0, 0),
        288:  ('GetFriendHit', 2, 0),
        289:  ('IsInCombat', 0, 0),
        300:  ('IsInInterior', 0, 0),
        305:  ('GetInvestmentGold', 0, 0),
        306:  ('IsActorUsingATorch', 0, 0),
        309:  ('IsXBox', 0, 0),
        310:  ('GetInWorldspace', 2, 0),
        312:  ('GetPCMiscStat', 1, 0),
        313:  ('IsActorEvil', 0, 0),
        314:  ('IsActorAVictim', 0, 0),
        315:  ('GetTotalPersuasionNumber', 0, 0),
        318:  ('GetIdleDoneOnce', 0, 0),
        320:  ('GetNoRumors', 0, 0),
        323:  ('WhichServiceMenu', 0, 0),
        327:  ('IsRidingHorse', 0, 0),
        329:  ('IsTurnArrest', 0, 0),
        332:  ('IsInDangerousWater', 0, 0),
        338:  ('GetIgnoreFriendlyHits', 0, 0),
        339:  ('IsPlayersLastRiddenHorse', 0, 0),
        353:  ('IsActor', 0, 0),
        354:  ('IsEssential', 0, 0),
        358:  ('IsPlayerMovingIntoNewSpace', 0, 0),
        361:  ('GetTimeDead', 0, 0),
        362:  ('GetPlayerHasLastRiddenHorse', 0, 0),
        365:  ('GetPlayerInSEWorld', 0, 0),
        # Extended by (x)OBSE
        1107: ('IsAmmo', 1, 0),
        1122: ('HasSpell', 2, 0),
        1124: ('IsClassSkill', 1, 2),
        1884: ('GetPCTrainingSessionsUsed', 2, 0),
        2213: ('GetPackageOffersServices', 2, 0),
        2214: ('GetPackageMustReachLocation', 2, 0),
        2215: ('GetPackageMustComplete', 2, 0),
        2216: ('GetPackageLockDoorsAtStart', 2, 0),
        2217: ('GetPackageLockDoorsAtEnd', 2, 0),
        2218: ('GetPackageLockDoorsAtLocation', 2, 0),
        2219: ('GetPackageUnlockDoorsAtStart', 2, 0),
        2220: ('GetPackageUnlockDoorsAtEnd', 2, 0),
        2221: ('GetPackageUnlockDoorsAtLocation', 2, 0),
        2222: ('GetPackageContinueIfPCNear', 2, 0),
        2223: ('GetPackageOncePerDay', 2, 0),
        2224: ('GetPackageSkipFalloutBehavior', 2, 0),
        2225: ('GetPackageAlwaysRun', 2, 0),
        2226: ('GetPackageAlwaysSneak', 2, 0),
        2227: ('GetPackageAllowSwimming', 2, 0),
        2228: ('GetPackageAllowFalls', 2, 0),
        2229: ('GetPackageArmorUnequipped', 2, 0),
        2230: ('GetPackageWeaponsUnequipped', 2, 0),
        2231: ('GetPackageDefensiveCombat', 2, 0),
        2232: ('GetPackageUseHorse', 2, 0),
        2233: ('GetPackageNoIdleAnims', 2, 0),
        2571: ('GetBaseAV3', 1, 0),
        2573: ('IsNaked', 1, 0),
        2578: ('IsDiseased', 0, 0),
    }

    # Known record types
    save_rec_types = {
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

    #--------------------------------------------------------------------------
    # Leveled Lists
    #--------------------------------------------------------------------------
    leveled_list_types = {b'LVLC', b'LVLI', b'LVSP'}

    #--------------------------------------------------------------------------
    # Import Prices
    #--------------------------------------------------------------------------
    names_types = {
        b'ACTI', b'ALCH', b'AMMO', b'APPA', b'ARMO', b'BOOK', b'BSGN', b'CLAS',
        b'CLOT', b'CONT', b'CREA', b'DOOR', b'ENCH', b'EYES', b'FACT', b'FLOR',
        b'HAIR', b'INGR', b'KEYM', b'LIGH', b'MGEF', b'MISC', b'NPC_', b'QUST',
        b'RACE', b'SGST', b'SLGM', b'SPEL', b'WEAP',
    }

    #--------------------------------------------------------------------------
    # Import Prices
    #--------------------------------------------------------------------------
    pricesTypes = {b'ALCH', b'AMMO', b'APPA', b'ARMO', b'BOOK', b'CLOT',
        b'INGR', b'KEYM', b'LIGH', b'MISC', b'SGST', b'SLGM', b'WEAP'}

    #--------------------------------------------------------------------------
    # Import Stats
    #--------------------------------------------------------------------------
    # The contents of these tuples have to stay fixed because of CSV parsers
    stats_csv_attrs = {
        b'ALCH': ('eid', 'weight', 'value'),
        b'AMMO': ('eid', 'weight', 'value', 'damage', 'speed',
                  'enchantPoints'),
        b'APPA': ('eid', 'weight', 'value', 'quality'),
        b'ARMO': ('eid', 'weight', 'value', 'health', 'strength'),
        b'BOOK': ('eid', 'weight', 'value', 'enchantPoints'),
        b'CLOT': ('eid', 'weight', 'value', 'enchantPoints'),
        b'EYES': ('eid', 'flags'),
        b'HAIR': ('eid', 'flags'),
        b'INGR': ('eid', 'weight', 'value'),
        b'KEYM': ('eid', 'weight', 'value'),
        b'LIGH': ('eid', 'weight', 'value', 'duration'),
        b'MISC': ('eid', 'weight', 'value'),
        b'SGST': ('eid', 'weight', 'value', 'uses'),
        b'SLGM': ('eid', 'weight', 'value'),
        b'WEAP': ('eid', 'weight', 'value', 'health', 'damage', 'speed',
                  'reach', 'enchantPoints'),
    }
    stats_attrs = {r: tuple(x for x in a if x != 'eid')
                   for r, a in stats_csv_attrs.items()}

    #--------------------------------------------------------------------------
    # Import Sounds
    #--------------------------------------------------------------------------
    sounds_attrs = {
        ##: actor_sounds here has FormIDs, but I don't think filtering it is wise?
        # The structure is complex and I don't know if a sound type entry
        # without any sounds would be valid or not. Leaving as is for now
        b'CREA': ('foot_weight', 'actor_sounds'),
        b'SOUN': ('soundFile', 'minDistance', 'maxDistance', 'freqAdjustment',
                  'staticAtten', 'stopTime', 'startTime'),
        # Has FormIDs, but will be filtered in AMreWthr.keep_fids
        b'WTHR': ('sounds',),
    }
    sounds_fid_attrs = {
        b'ACTI': ('sound',),
        b'CONT': ('sound', 'sound_close'),
        b'CREA': ('inherits_sounds_from',),
        b'DOOR': ('sound', 'sound_close', 'sound_looping'),
        b'LIGH': ('sound',),
        b'MGEF': ('castingSound', 'boltSound', 'hitSound', 'areaSound'),
        b'WATR': ('sound',),
    }

    #--------------------------------------------------------------------------
    # Import Cells
    #--------------------------------------------------------------------------
    cellRecAttrs = {
        'C.Climate': ('climate', 'flags.behaveLikeExterior'),
        ##: Patches unuseds?
        'C.Light': ('ambientRed', 'ambientGreen', 'ambientBlue', 'unused1',
                    'directionalRed', 'directionalGreen', 'directionalBlue',
                    'unused2', 'fogRed', 'fogGreen', 'fogBlue', 'unused3',
                    'fogNear', 'fogFar', 'directionalXY', 'directionalZ',
                    'directionalFade', 'fogClip'),
        'C.MiscFlags': ('flags.isInterior', 'flags.invertFastTravel',
                        'flags.forceHideLand', 'flags.handChanged'),
        'C.Music': ('music',),
        'C.Name': ('full',),
        'C.Owner': ('ownership', 'flags.publicPlace'),
        'C.RecordFlags': ('flags1',), # Yes seems funky but thats the way it is
        'C.Regions': ('regions',),
        'C.Water': ('water', 'waterHeight', 'flags.hasWater'),
    }

    #--------------------------------------------------------------------------
    # Import Graphics
    #--------------------------------------------------------------------------
    graphicsTypes = {
        b'ACTI': ('model',),
        b'ALCH': ('iconPath', 'model'),
        b'AMMO': ('iconPath', 'model'),
        b'APPA': ('iconPath', 'model'),
        b'ARMO': ('maleBody', 'maleWorld', 'maleIconPath', 'femaleBody',
                  'femaleWorld', 'femaleIconPath', 'biped_flags'),
        b'BOOK': ('iconPath', 'model'),
        b'BSGN': ('iconPath',),
        b'CLAS': ('iconPath',),
        b'CLOT': ('maleBody', 'maleWorld', 'maleIconPath', 'femaleBody',
                  'femaleWorld', 'femaleIconPath', 'biped_flags'),
        b'CONT': ('model',),
        b'CREA': ('bodyParts', 'model_list_textures'),
        b'DOOR': ('model',),
        b'EFSH': (
            'particle_texture', 'fill_texture', 'efsh_flags',
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
            'color_key1_time', 'color_key2_time', 'color_key3_time'),
        b'EYES': ('iconPath',),
        b'FLOR': ('model',),
        b'FURN': ('model',),
        b'GRAS': ('model',),
        b'HAIR': ('iconPath', 'model'),
        b'INGR': ('iconPath', 'model'),
        b'KEYM': ('iconPath', 'model'),
        b'LIGH': ('iconPath', 'model', 'light_radius', 'light_color_red',
                  'light_color_green', 'light_color_blue', 'light_flags',
                  'light_falloff', 'light_fov', 'light_fade'),
        b'LSCR': ('iconPath',),
        b'LTEX': ('iconPath',),
        b'MGEF': ('iconPath', 'model'),
        b'MISC': ('iconPath', 'model'),
        b'QUST': ('iconPath',),
        b'REGN': ('iconPath',),
        b'SGST': ('iconPath', 'model'),
        b'SKIL': ('iconPath',),
        b'SLGM': ('iconPath', 'model'),
        b'STAT': ('model',),
        b'TREE': ('iconPath', 'model'),
        b'WEAP': ('iconPath', 'model'),
    }
    graphicsFidTypes = {
        b'MGEF': ('light', 'effectShader', 'enchantEffect')
    }
    graphicsModelAttrs = {'model', 'maleBody', 'maleWorld', 'femaleBody',
                          'femaleWorld'}

    #--------------------------------------------------------------------------
    # Import Inventory
    #--------------------------------------------------------------------------
    inventory_types = {b'CONT', b'CREA', b'NPC_'}

    #--------------------------------------------------------------------------
    # NPC Checker
    #--------------------------------------------------------------------------
    _standard_eyes = [*((None, _x) for _x in (0x27306, 0x27308, 0x27309)),
        *(('Cobl Main.esm', _x) for _x in (0x000821, 0x000823, 0x000825,
                0x000828, 0x000834, 0x000837, 0x000839, 0x00084F))]
    default_eyes = {
        #--Oblivion.esm
        # Argonian
        (None, 0x23FE9): [(None, 0x3E91E), *(('Cobl Main.esm', _x) for _x in (
            0x01F407, 0x01F408, 0x01F40B, 0x01F40C, 0x01F410, 0x01F411,
            0x01F414, 0x01F416, 0x01F417, 0x01F41A, 0x01F41B, 0x01F41E,
            0x01F41F, 0x01F422, 0x01F424))],
        # Breton
        (None, 0x0224FC): _standard_eyes,
        # Dark Elf
        (None, 0x0191C1): [(None, 0x27307), *(('Cobl Main.esm', _x) for _x in
                                              (0x000861, 0x000864, 0x000851))],
        # High Elf
        (None, 0x019204): _standard_eyes,
        # Imperial
        (None, 0x000907): _standard_eyes,
        # Khajiit
        (None, 0x022C37): [(None, 0x375c8), *(('Cobl Main.esm', _x) for _x in (
            0x00083B, 0x00083E, 0x000843, 0x000846, 0x000849, 0x00084C))],
        # Nord
        (None, 0x0224FD): _standard_eyes,
        # Orc
        (None, 0x0191C0): [(None, 0x2730A), *(('Cobl Main.esm', _x) for _x in (
            0x000853, 0x000855, 0x000858, 0x00085A, 0x00085C, 0x00085E))],
        # Redguard
        (None, 0x000D43): _standard_eyes,
        # Wood Elf
        (None, 0x0223C8): _standard_eyes,
        #--Cobl Main.esm
        # cobRaceAureal
        ('Cobl Main.esm',  0x07948): [(None, 0x54BBA)],
        # cobRaceHidden
        ('Cobl Main.esm',  0x02B60): [('Cobl Main.esm', _x) for _x in (
            0x01F43A, 0x01F438, 0x01F439, 0x0015A7, 0x01792C, 0x0015AC,
            0x0015A8, 0x0015AB, 0x0015AA)],
        # cobRaceMazken
        ('Cobl Main.esm',  0x07947): [(None, 0x54BB9)],
        # cobRaceOhmes
        ('Cobl Main.esm',  0x1791B): [('Cobl Main.esm', _x) for _x in (
            0x017901, 0x017902, 0x017903, 0x017904, 0x017905, 0x017906,
            0x017907, 0x017908, 0x017909, 0x01790A, 0x01790B, 0x01790C,
            0x01790D, 0x01790E, 0x01790F, 0x017910, 0x017911, 0x017912,
            0x017913, 0x017914, 0x017915, 0x017916, 0x017917, 0x017918,
            0x017919, 0x01791A, 0x017900)],
        # cobRaceXivilai
        ('Cobl Main.esm',  0x1F43C): [('Cobl Main.esm', _x) for _x in (
            0x01F437, 0x00531B, 0x00531C, 0x00531D, 0x00531E, 0x00531F,
            0x005320, 0x005321, 0x01F43B, 0x00DBE1)],
    }

    #--------------------------------------------------------------------------
    # Import Text
    #--------------------------------------------------------------------------
    text_types = {
        b'BOOK': ('book_text',),
        b'BSGN': ('description',),
        b'CLAS': ('description',),
        b'LSCR': ('description',),
        b'MGEF': ('description',),
        # omit RACE - covered by R.Description
        b'SKIL': ('description',),
    }

    #--------------------------------------------------------------------------
    # Contents Checker
    #--------------------------------------------------------------------------
    # Entry types used for CONT, CREA, LVLI and NPC_
    _common_entry_types = {b'ALCH', b'AMMO', b'APPA', b'ARMO', b'BOOK',
                           b'CLOT', b'INGR', b'KEYM', b'LIGH', b'LVLI',
                           b'MISC', b'SGST', b'SLGM', b'WEAP'}
    cc_valid_types = {
        b'CONT': _common_entry_types,
        b'CREA': _common_entry_types,
        b'LVLC': {b'CREA', b'LVLC', b'NPC_'},
        b'LVLI': _common_entry_types,
        b'LVSP': {b'LVSP', b'SPEL'},
        b'NPC_': _common_entry_types,
    }
    cc_passes = (
        (leveled_list_types, 'entries', 'listId'),
        (inventory_types,    'items',   'item'),
    )

    #--------------------------------------------------------------------------
    # Import Scripts
    #--------------------------------------------------------------------------
    scripts_types = {b'ACTI', b'ALCH', b'APPA', b'ARMO', b'BOOK', b'CLOT',
        b'CONT', b'CREA', b'DOOR', b'FLOR', b'FURN', b'INGR', b'KEYM', b'LIGH',
        b'MISC', b'NPC_', b'QUST', b'SGST', b'SLGM', b'WEAP'}

    #--------------------------------------------------------------------------
    # Import Actors
    #--------------------------------------------------------------------------
    actor_importer_attrs = {
        b'CREA': {
            'Actors.ACBS': (
                'barter_gold', 'base_spell', 'calc_max_level',
                'calc_min_level', 'fatigue', 'crea_flags.crea_biped',
                'crea_flags.crea_essential', 'crea_flags.crea_flies',
                'crea_flags.crea_no_blood_decal',
                'crea_flags.crea_no_blood_spray',
                'crea_flags.crea_no_combat_in_water',
                'crea_flags.no_corpse_check', 'crea_flags.no_head',
                'crea_flags.no_left_arm', 'crea_flags.no_low_level',
                'crea_flags.no_right_arm', 'crea_flags.crea_no_shadow',
                'crea_flags.crea_respawn', 'crea_flags.crea_swims',
                'crea_flags.crea_walks', 'crea_flags.weapon_and_shield',
                # This flag directly impacts how the level_offset is
                # calculated, so use a fused attribute to always carry them
                # forward together
                ('crea_flags.pc_level_offset', 'level_offset'),
            ),
            'Actors.AIData': (
                'ai_aggression', 'ai_confidence', 'ai_energy_level',
                'ai_responsibility', 'ai_service_flags', 'ai_train_level',
                'ai_train_skill',
            ),
            'Actors.Anims': ('animations',),
            'Actors.RecordFlags': ('flags1',),
            'Actors.Skeleton': ('model',),
            'Actors.Stats': (
                'agility', 'attackDamage', 'combat_skill', 'endurance',
                'health', 'intelligence', 'luck', 'magic', 'personality',
                'soul', 'stealth', 'speed', 'strength', 'willpower',
            ),
            'Creatures.Blood': ('blood_decal_path', 'blood_spray_path'),
            'Creatures.Type': ('creature_type',),
        },
        b'NPC_': {
            'Actors.ACBS': (
                'barter_gold', 'base_spell', 'calc_max_level',
                'calc_min_level', 'fatigue', 'npc_flags.npc_auto_calc',
                'npc_flags.can_corpse_check', 'npc_flags.npc_essential',
                'npc_flags.npc_female', 'npc_flags.no_low_level',
                'npc_flags.no_persuasion', 'npc_flags.no_rumors',
                'npc_flags.npc_respawn', 'npc_flags.npc_summonable',
                ('npc_flags.pc_level_offset', 'level_offset'), # See above
            ),
            'Actors.AIData': (
                'ai_aggression', 'ai_confidence', 'ai_energy_level',
                'ai_responsibility', 'ai_service_flags', 'ai_train_skill',
                'ai_train_level',
            ),
            'Actors.Anims': ('animations',),
            'Actors.RecordFlags': ('flags1',),
            'Actors.Skeleton': ('model',),
            'Actors.Stats': ('attributes', 'health', 'skills',),
            'Creatures.Blood': (),
            'Creatures.Type': (),
        },
    }
    actor_importer_fid_attrs = {
        b'CREA': {
            'Actors.CombatStyle': ('combat_style',),
            'Actors.DeathItem': ('death_item',),
            'NPC.Class': (),
            'NPC.Race': (),
        },
        b'NPC_': {
            'Actors.CombatStyle': ('combat_style',),
            'Actors.DeathItem': ('death_item',),
            'NPC.Class': ('npc_class',),
            'NPC.Race': ('race',),
        }
    }
    actor_types = {b'CREA', b'NPC_'}

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
        'VORB_NPCSkeletonPatcher',
        'MAONPCSkeletonPatcher',
        'VanillaNPCSkeletonPatcher',
        'RedguardNPCPatcher',
        'NoBloodCreaturesPatcher',
        'AsIntendedImpsPatcher',
        'AsIntendedBoarsPatcher',
        'QuietFeetPatcher',
        'IrresponsibleCreaturesPatcher',
        'RWALKNPCAnimationPatcher',
        'SWALKNPCAnimationPatcher',
    }

    #--------------------------------------------------------------------------
    # Tweak Names
    #--------------------------------------------------------------------------
    names_tweaks = {
        'NamesTweak_BodyPartCodes',
        'NamesTweak_Body_Armor_Tes4',
        'NamesTweak_Body_Clothes',
        'NamesTweak_Ingestibles_Tes4',
        'NamesTweak_NotesScrolls',
        'NamesTweak_Spells',
        'NamesTweak_Weapons_Tes4',
        'NamesTweak_DwarvenToDwemer',
        'NamesTweak_DwarfsToDwarves',
        'NamesTweak_StaffsToStaves',
        'NamesTweak_FatigueToStamina',
        'NamesTweak_MarksmanToArchery',
        'NamesTweak_SecurityToLockpicking',
        'NamesTweak_AmmoWeight',
        'NamesTweak_RenameGold',
    }
    body_part_codes = ('ARGHTCCPBS', 'ABGHINOPSL')
    text_replacer_rpaths = {
        b'ALCH': ('full', 'effects[*].scriptEffect?.full'),
        b'AMMO': ('full',),
        b'APPA': ('full',),
        b'ARMO': ('full',),
        b'BOOK': ('full', 'book_text'),
        b'BSGN': ('full', 'description'),
        b'CLAS': ('full', 'description'),
        b'CLOT': ('full',),
        b'CONT': ('full',),
        b'CREA': ('full',),
        b'DOOR': ('full',),
        b'ENCH': ('full', 'effects[*].scriptEffect?.full',),
        b'EYES': ('full',),
        b'FACT': ('full',), ##: maybe add male_title/female_title?
        b'FLOR': ('full',),
        b'FURN': ('full',),
        b'GMST': ('value',),
        b'HAIR': ('full',),
        b'INGR': ('full', 'effects[*].scriptEffect?.full'),
        b'KEYM': ('full',),
        b'LIGH': ('full',),
        b'LSCR': ('description',),
        b'MGEF': ('full', 'description'),
        b'MISC': ('full',),
        b'NPC_': ('full',),
        b'QUST': ('full', 'stages[*].entries[*].text'),
        b'RACE': ('full', 'description'),
        b'SGST': ('full', 'effects[*].scriptEffect?.full'),
        b'SKIL': ('description', 'apprentice', 'journeyman', 'expert',
                  'master'),
        b'SLGM': ('full',),
        b'SPEL': ('full', 'effects[*].scriptEffect?.full'),
        b'WEAP': ('full',),
    }
    gold_attrs = lambda _self_ignore: {
        'eid': 'Gold001',
        'model.modPath': r'Clutter\goldCoin01.NIF',
        'model.modb': 1.0,
        'model.modt_p': None,
        'iconPath': r'Clutter\IconGold.dds',
        'value': 1,
        'weight': 0.0,
    }

    #--------------------------------------------------------------------------
    # Tweak Settings
    #--------------------------------------------------------------------------
    settings_tweaks = {
        'GlobalsTweak_Timescale',
        'GlobalsTweak_ThievesGuild_QuestStealingPenalty',
        'GlobalsTweak_ThievesGuild_QuestKillingPenalty',
        'GlobalsTweak_ThievesGuild_QuestAttackingPenalty',
        'GlobalsTweak_Crime_ForceJail',
        'GmstTweak_Arrow_LitterCount',
        'GmstTweak_Arrow_LitterTime',
        'GmstTweak_Arrow_RecoveryFromActor',
        'GmstTweak_Arrow_Speed',
        'GmstTweak_Camera_ChaseTightness',
        'GmstTweak_Camera_ChaseDistance',
        'GmstTweak_Magic_ChameleonRefraction',
        'GmstTweak_Compass_Disable',
        'GmstTweak_Compass_RecognitionDistance',
        'GmstTweak_Actor_UnconsciousnessDuration',
        'GmstTweak_Movement_FatigueFromRunningEncumbrance',
        'GmstTweak_Player_HorseTurningSpeed',
        'GmstTweak_Camera_PCDeathTime',
        'GmstTweak_World_CellRespawnTime',
        'GmstTweak_Combat_RechargeWeapons',
        'GmstTweak_Magic_BoltSpeed',
        'GmstTweak_Msg_EquipMiscItem',
        'GmstTweak_Msg_AutoSaving',
        'GmstTweak_Msg_HarvestFailure',
        'GmstTweak_Msg_HarvestSuccess',
        'GmstTweak_Msg_QuickSave',
        'GmstTweak_Msg_HorseStabled',
        'GmstTweak_Msg_NoFastTravel',
        'GmstTweak_Msg_LoadingArea',
        'GmstTweak_Msg_QuickLoad',
        'GmstTweak_Msg_NotEnoughCharge',
        'GmstTweak_CostMultiplier_Repair',
        'GmstTweak_Actor_GreetingDistance',
        'GmstTweak_CostMultiplier_Recharge',
        'GmstTweak_MasterOfMercantileExtraGoldAmount',
        'GmstTweak_Combat_MaxActors',
        'GmstTweak_Crime_AlarmDistance',
        'GmstTweak_Crime_PrisonDurationModifier',
        'GmstTweak_CostMultiplier_Enchantment',
        'GmstTweak_CostMultiplier_SpellMaking',
        'GmstTweak_AI_MaxActiveActors',
        'GmstTweak_Magic_MaxPlayerSummons',
        'GmstTweak_Combat_MaxAllyHitsInCombat_Tes4',
        'GmstTweak_Magic_MaxNPCSummons',
        'GmstTweak_Bounty_Assault',
        'GmstTweak_Bounty_HorseTheft',
        'GmstTweak_Bounty_Theft',
        'GmstTweak_Combat_Alchemy',
        'GmstTweak_Combat_Repair',
        'GmstTweak_Actor_MaxCompanions',
        'GmstTweak_Actor_TrainingLimit',
        'GmstTweak_Combat_MaximumArmorRating',
        'GmstTweak_Warning_InteriorDistanceToHostiles',
        'GmstTweak_Warning_ExteriorDistanceToHostiles',
        'GmstTweak_UOPVampireAgingAndFaceFix',
        'GmstTweak_AI_MaxDeadActors',
        'GmstTweak_Player_InventoryQuantityPrompt_Tes4',
        'GmstTweak_Bounty_Trespassing',
        'GmstTweak_Bounty_Pickpocketing',
        'GmstTweak_LevelDifference_CreatureMax',
        'GmstTweak_LevelDifference_ItemMax',
        'GmstTweak_Actor_StrengthEncumbranceMultiplier',
        'GmstTweak_Visuals_NPCBlood',
        'GmstTweak_AI_MaxSmileDistance',
        'GmstTweak_Player_MaxDraggableWeight',
        'GmstTweak_AI_ConversationChance',
        'GmstTweak_AI_ConversationChance_Interior',
        'GmstTweak_Crime_PickpocketingChance',
        'GmstTweak_Actor_MaxJumpHeight_Tes4',
        'GmstTweak_Bounty_Murder',
        'GmstTweak_Bounty_Jailbreak',
        'GmstTweak_Prompt_Activate_Tes4',
        'GmstTweak_Prompt_Open_Tes4',
        'GmstTweak_Prompt_Read_Tes4',
        'GmstTweak_Prompt_Sit_Tes4',
        'GmstTweak_Prompt_Take_Tes4',
        'GmstTweak_Prompt_Talk_Tes4',
        'GmstTweak_Msg_NoSoulGemLargeEnough',
        'GmstTweak_Combat_SpeakOnAttackChance',
        'GmstTweak_Combat_SpeakOnHitChance_Tes4',
        'GmstTweak_Combat_SpeakOnHitThreshold_Tes4',
        'GmstTweak_Combat_SpeakOnPowerAttackChance_Tes4',
        'GmstTweak_Combat_RandomTauntChance',
        'GmstTweak_LevelUp_SkillCount',
        'GmstTweak_Combat_MaxFriendHitsInCombat_Tes4',
    }

    #--------------------------------------------------------------------------
    # Import Relations
    #--------------------------------------------------------------------------
    relations_attrs = ('faction', 'mod') ##: mod?

    #--------------------------------------------------------------------------
    # Import Enchantment Stats
    #--------------------------------------------------------------------------
    ench_stats_attrs = ('item_type', 'charge_amount', 'enchantment_cost',
                        'enit_flags')

    #--------------------------------------------------------------------------
    # Import Effect Stats
    #--------------------------------------------------------------------------
    mgef_stats_attrs = ('flags', 'base_cost', 'school', 'resist_value',
                        'projectileSpeed', 'cef_enchantment', 'cef_barter')
    mgef_stats_fid_attrs = ('associated_item',)

    #--------------------------------------------------------------------------
    # Tweak Assorted
    #--------------------------------------------------------------------------
    assorted_tweaks = {
        'AssortedTweak_ArmorShows_Amulets',
        'AssortedTweak_ArmorShows_Rings',
        'AssortedTweak_ClothingShows_Amulets',
        'AssortedTweak_ClothingShows_Rings',
        'AssortedTweak_ArmorPlayable',
        'AssortedTweak_ClothingPlayable',
        'AssortedTweak_BowReach',
        'AssortedTweak_ConsistentRings',
        'AssortedTweak_DarnBooks',
        'AssortedTweak_FogFix',
        'AssortedTweak_NoLightFlicker',
        'AssortedTweak_PotionWeight',
        'AssortedTweak_PotionWeightMinimum',
        'AssortedTweak_StaffWeight',
        'AssortedTweak_SetCastWhenUsedEnchantmentCosts',
        'AssortedTweak_WindSpeed',
        'AssortedTweak_UniformGroundcover',
        'AssortedTweak_HarvestChance',
        'AssortedTweak_IngredientWeight',
        'AssortedTweak_ArrowWeight',
        'AssortedTweak_ScriptEffectSilencer',
        'AssortedTweak_DefaultIcons',
        'AssortedTweak_SetSoundAttenuationLevels',
        'AssortedTweak_SetSoundAttenuationLevels_NirnrootOnly',
        'AssortedTweak_FactioncrimeGoldMultiplier',
        'AssortedTweak_LightFadeValueFix',
        'AssortedTweak_SkyrimStyleWeapons',
        'AssortedTweak_TextlessLSCRs',
        'AssortedTweak_SEFFIcon',
        'AssortedTweak_BookWeight',
        'AssortedTweak_AttackSpeedStavesMinimum',
        'AssortedTweak_AttackSpeedStavesMaximum',
    }
    staff_condition = ('weaponType', 4)
    static_attenuation_rec_type = b'SOUN'

    #--------------------------------------------------------------------------
    # Import Races
    #--------------------------------------------------------------------------
    import_races_attrs = {
        b'RACE': {
            'R.Attributes-F': ('femaleStrength', 'femaleIntelligence',
                               'femaleWillpower', 'femaleAgility',
                               'femaleSpeed', 'femaleEndurance',
                               'femalePersonality', 'femaleLuck'),
            'R.Attributes-M': ('maleStrength', 'maleIntelligence',
                               'maleWillpower', 'maleAgility', 'maleSpeed',
                               'maleEndurance', 'malePersonality', 'maleLuck'),
            'R.Body-F': ('femaleTailModel', 'femaleUpperBodyPath',
                         'femaleLowerBodyPath', 'femaleHandPath',
                         'femaleFootPath', 'femaleTailPath'),
            'R.Body-M': ('maleTailModel', 'maleUpperBodyPath',
                         'maleLowerBodyPath', 'maleHandPath', 'maleFootPath',
                         'maleTailPath'),
            'R.Body-Size-F': ('femaleHeight', 'femaleWeight'),
            'R.Body-Size-M': ('maleHeight', 'maleWeight'),
            'R.Description': ('description',),
            'R.Ears': ('maleEars', 'femaleEars'),
            # eyes has FormIDs, but will be filtered in AMreRace.keep_fids
            'R.Eyes': ('eyes', 'leftEye', 'rightEye'),
            # hairs has FormIDs, but will be filtered in AMreRace.keep_fids
            'R.Hair': ('hairs',),
            'R.Head': ('head',),
            'R.Mouth': ('mouth', 'tongue'),
            'R.Skills': ('skills',),
            'R.Teeth': ('teethLower', 'teethUpper'),
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
    enchantment_types = {b'AMMO', b'ARMO', b'BOOK', b'CLOT', b'WEAP'}

    #--------------------------------------------------------------------------
    # Tweak Races
    #--------------------------------------------------------------------------
    race_tweaks = {
        'RaceTweak_BiggerOrcsAndNords',
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
    # Timescale Checker
    #--------------------------------------------------------------------------
    # Nehrim has a timescale of 10, but the Nehrim devs forgot to change the
    # wave periods for their grass to match, hence we keep
    # default_wp_timescale at 30 for Nehrim too
    default_wp_timescale = 30

    # Records info
    top_groups = [
        b'GMST', b'GLOB', b'CLAS', b'FACT', b'HAIR', b'EYES', b'RACE', b'SOUN',
        b'SKIL', b'MGEF', b'SCPT', b'LTEX', b'ENCH', b'SPEL', b'BSGN', b'ACTI',
        b'APPA', b'ARMO', b'BOOK', b'CLOT', b'CONT', b'DOOR', b'INGR', b'LIGH',
        b'MISC', b'STAT', b'GRAS', b'TREE', b'FLOR', b'FURN', b'WEAP', b'AMMO',
        b'NPC_', b'CREA', b'LVLC', b'SLGM', b'KEYM', b'ALCH', b'SBSP', b'SGST',
        b'LVLI', b'WTHR', b'CLMT', b'REGN', b'CELL', b'WRLD', b'DIAL', b'QUST',
        b'IDLE', b'PACK', b'CSTY', b'LSCR', b'LVSP', b'ANIO', b'WATR', b'EFSH',
    ]

    @classmethod
    def _dynamic_import_modules(cls, package_name):
        super(OblivionGameInfo, cls)._dynamic_import_modules(package_name)
        from .patcher import checkers, preservers
        cls.gameSpecificPatchers = {
            u'CoblCatalogs': checkers.CoblCatalogsPatcher,
            u'SEWorldTests': checkers.SEWorldTestsPatcher, }
        cls.gameSpecificListPatchers = {
            u'CoblExhaustion': preservers.CoblExhaustionPatcher,
            u'MorphFactions': preservers.MorphFactionsPatcher, }
        cls.game_specific_import_patchers = {
            u'ImportRoads': preservers.ImportRoadsPatcher, }

    @classmethod
    def init(cls, _package_name=None):
        super().init(_package_name or __name__)
        cls.readClasses = (b'MGEF', b'SCPT')
        cls.writeClasses = (b'MGEF',)
        # Setting RecordHeader class variables - Oblivion is special
        from ... import brec as _brec_
        header_type = _brec_.RecordHeader
        header_type.rec_header_size = 20
        header_type.rec_pack_format_str = '=4sIIII'
        header_type.header_unpack = bolt.structs_cache['=4sIIII'].unpack
        header_type.pack_formats = {0: u'=4sI4s2I'}
        header_type.pack_formats.update(
            {x: u'=4s4I' for x in {1, 6, 7, 8, 9, 10}})
        header_type.pack_formats.update({x: u'=4sIi2I' for x in {2, 3}})
        header_type.pack_formats.update({x: u'=4sIhh2I' for x in {4, 5}})
        cls._import_records(__name__, _brec=_brec_)

    @classmethod
    def _import_records(cls, package_name, plugin_form_vers=None, _brec=None):
        super()._import_records(package_name) # package name is oblivion here
        # in Oblivion we get them all except the TES4 record
        cls.mergeable_sigs = {*cls.top_groups, *_brec.RecordType.nested_to_top}

class GOGOblivionGameInfo(GOGMixin, OblivionGameInfo):
    """GameInfo override for the GOG version of Oblivion."""
    displayName = 'Oblivion (GOG)'
    _gog_game_ids = _GOG_IDS
    # appdata_name and my_games_name use the original locations
    check_legacy_paths = False

class WSOblivionGameInfo(WindowsStoreMixin, OblivionGameInfo):
    """GameInfo override for the Windows Store version of Oblivion."""
    displayName = 'Oblivion (WS)'
    # appdata_name and my_games_name use the original locations
    check_legacy_paths = False

    class Ws(OblivionGameInfo.Ws):
        legacy_publisher_name = 'Bethesda'
        win_store_name = 'BethesdaSoftworks.TESOblivion-PC'
        ws_language_dirs = ['Oblivion GOTY English',
                            'Oblivion GOTY French',
                            'Oblivion GOTY German',
                            'Oblivion GOTY Italian',
                            'Oblivion GOTY Spanish']

GAME_TYPE = {g.displayName: g for g in
             (OblivionGameInfo, GOGOblivionGameInfo, WSOblivionGameInfo)}
