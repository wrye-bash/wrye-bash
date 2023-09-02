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
from copy import deepcopy
from os.path import join as _j

from .. import WS_COMMON_FILES
from ..fallout3 import Fallout3GameInfo
from ..gog_game import GOGMixin
from ..windows_store_game import WindowsStoreMixin
from ...bolt import DefaultFNDict, FName, classproperty

_GOG_IDS = [1454587428]

class FalloutNVGameInfo(Fallout3GameInfo):
    """GameInfo override for Fallout New Vegas."""
    displayName = u'Fallout New Vegas'
    fsName = u'FalloutNV'
    altName = u'Wrye Flash NV'
    game_icon = u'falloutnv_%u.png'
    bash_root_prefix = u'FalloutNV'
    bak_game_name = u'FalloutNV'
    my_games_name = u'FalloutNV'
    appdata_name = u'FalloutNV'
    launch_exe = u'FalloutNV.exe'
    game_detect_includes = {'FalloutNV.exe'}
    game_detect_excludes = (set(GOGMixin.get_unique_filenames(_GOG_IDS)) |
                            WS_COMMON_FILES | {'EOSSDK-Win32-Shipping.dll'})
    version_detect_file = u'FalloutNV.exe'
    master_file = FName(u'FalloutNV.esm')
    taglist_dir = u'FalloutNV'
    loot_dir = u'FalloutNV'
    loot_game_name = 'FalloutNV'
    boss_game_name = u'FalloutNV'
    registry_keys = [(r'Bethesda Softworks\FalloutNV', 'Installed Path')]
    nexusUrl = u'https://www.nexusmods.com/newvegas/'
    nexusName = u'New Vegas Nexus'
    nexusKey = u'bash.installers.openNewVegasNexus.continue'

    class Se(Fallout3GameInfo.Se):
        se_abbrev = u'NVSE'
        long_name = u'New Vegas Script Extender'
        exe = u'nvse_loader.exe'
        ver_files = [u'nvse_loader.exe', u'nvse_steam_loader.dll']
        plugin_dir = u'NVSE'
        cosave_tag = u'NVSE'
        cosave_ext = u'.nvse'
        url = u'http://nvse.silverlock.org/'
        url_tip = u'http://nvse.silverlock.org/'

    class Bsa(Fallout3GameInfo.Bsa):
        redate_dict = DefaultFNDict(lambda: 1136066400, { # '2006-01-01'
            u'Fallout - Meshes.bsa': 1104530400,    # '2005-01-01'
            u'Fallout - Meshes2.bsa': 1104616800,   # '2005-01-02'
            u'Fallout - Misc.bsa': 1104703200,      # '2005-01-03'
            u'Fallout - Sound.bsa': 1104789600,     # '2005-01-04'
            u'Fallout - Textures.bsa': 1104876000,  # '2005-01-05'
            u'Fallout - Textures2.bsa': 1104962400, # '2005-01-06'
            u'Fallout - Voices1.bsa': 1105048800,   # '2005-01-07'
        })

    class Xe(Fallout3GameInfo.Xe):
        full_name = u'FNVEdit'
        xe_key_prefix = u'fnvView'

    class Bain(Fallout3GameInfo.Bain):
        data_dirs = (Fallout3GameInfo.Bain.data_dirs - {'fose'}) | {'nvse'}
        no_skip = Fallout3GameInfo.Bain.no_skip | {
            'aaid.txt', # 3P: Auto Activate Invisible Doors
            _j('uio', 'supported.txt'), # 3P: UIO - User Interface Organizer
        }
        no_skip_dirs = Fallout3GameInfo.Bain.no_skip_dirs | {
            # 3P: JIP LN's Script Runner
            _j('nvse', 'plugins', 'scripts'): {'.txt'},
        }
        skip_bain_refresh = {'fnvedit backups', 'fnvedit cache'}

    class Esp(Fallout3GameInfo.Esp):
        validHeaderVersions = (0.94, 1.32, 1.33, 1.34)

    allTags = Fallout3GameInfo.allTags | {'WeaponMods'}
    patchers = Fallout3GameInfo.patchers | {'ImportWeaponModifications'}

    bethDataFiles = {
        'caravanpack - main.bsa',
        'caravanpack.esm',
        'caravanpack.nam',
        'classicpack - main.bsa',
        'classicpack.esm',
        'classicpack.nam',
        'deadmoney - main.bsa',
        'deadmoney - sounds.bsa',
        'deadmoney.esm',
        'deadmoney.nam',
        'fallout - invalidation.bsa',
        'fallout - meshes.bsa',
        'fallout - meshes2.bsa',
        'fallout - misc.bsa',
        'fallout - sound.bsa',
        'fallout - textures.bsa',
        'fallout - textures2.bsa',
        'fallout - voices1.bsa',
        'falloutnv.esm',
        'falloutnv_lang.esp', # non-Steam versions only
        'gunrunnersarsenal - main.bsa',
        'gunrunnersarsenal - sounds.bsa',
        'gunrunnersarsenal.esm',
        'gunrunnersarsenal.nam',
        'honesthearts - main.bsa',
        'honesthearts - sounds.bsa',
        'honesthearts.esm',
        'honesthearts.nam',
        'lonesomeroad - main.bsa',
        'lonesomeroad - sounds.bsa',
        'lonesomeroad.esm',
        'lonesomeroad.nam',
        'mercenarypack - main.bsa',
        'mercenarypack.esm',
        'mercenarypack.nam',
        'oldworldblues - main.bsa',
        'oldworldblues - sounds.bsa',
        'oldworldblues.esm',
        'oldworldblues.nam',
        'tribalpack - main.bsa',
        'tribalpack.esm',
        'tribalpack.nam',
        'update.bsa',
    }

    # Function Info ---------------------------------------------------------------
    # 0: no param; 1: int param; 2: FormID param; 3: float param
    condition_function_data = Fallout3GameInfo.condition_function_data | {
        # new & changed functions in FNV
        398:  ('IsLimbGone', 1, 1),
        420:  ('GetObjectiveCompleted', 2, 1),
        421:  ('GetObjectiveDisplayed', 2, 1),
        449:  ('HasPerk', 2, 1),
        451:  ('IsLastIdlePlayed', 0, 0),
        462:  ('IsPlayerTagSkill', 2, 0),
        474:  ('GetIsAlignment', 2, 0),
        480:  ('GetIsUsedItemEquipType', 2, 0),
        531:  ('IsInCriticalStage', 2, 0),
        573:  ('GetReputation', 1, 1),
        574:  ('GetReputationPct', 1, 1),
        575:  ('GetReputationThreshold', 1, 1),
        586:  ('IsHardcore', 0, 0),
        601:  ('GetForceHitReaction', 0, 0),
        607:  ('ChallengeLocked', 2, 0),
        610:  ('GetCasinoWinningStage', 1, 0),
        612:  ('PlayerInRegion', 2, 0),
        614:  ('GetChallengeCompleted', 2, 0),
        619:  ('IsAlwaysHardcore', 0, 0),
        # Added by (x)NVSE - up to date with xNVSE v6.2.9
        1024: ('GetNVSEVersion', 0, 0),
        1025: ('GetNVSERevision', 0, 0),
        1026: ('GetNVSEBeta', 0, 0),
        1028: ('GetWeight', 2, 0),
        1029: ('GetHealth', 2, 0),
        1030: ('GetValue', 2, 0),
        1034: ('GetType', 2, 0),
        1036: ('GetEquipType', 2, 0),
        1038: ('GetWeaponClipRounds', 2, 0),
        1039: ('GetAttackDamage', 2, 0),
        1040: ('GetWeaponType', 2, 0),
        1041: ('GetWeaponMinSpread', 2, 0),
        1042: ('GetWeaponSpread', 2, 0),
        1044: ('GetWeaponSightFOV', 2, 0),
        1045: ('GetWeaponMinRange', 2, 0),
        1046: ('GetWeaponMaxRange', 2, 0),
        1047: ('GetWeaponAmmoUse', 2, 0),
        1048: ('GetWeaponActionPoints', 2, 0),
        1049: ('GetWeaponCritDamage', 2, 0),
        1050: ('GetWeaponCritChance', 2, 0),
        1052: ('GetWeaponFireRate', 2, 0),
        1053: ('GetWeaponAnimAttackMult', 2, 0),
        1054: ('GetWeaponRumbleLeftMotor', 2, 0),
        1055: ('GetWeaponRumbleRightMotor', 2, 0),
        1056: ('GetWeaponRumbleDuration', 2, 0),
        1057: ('GetWeaponRumbleWavelength', 2, 0),
        1058: ('GetWeaponAnimShotsPerSec', 2, 0),
        1059: ('GetWeaponAnimReloadTime', 2, 0),
        1060: ('GetWeaponAnimJamTime', 2, 0),
        1061: ('GetWeaponSkill', 2, 0),
        1062: ('GetWeaponResistType', 2, 0),
        1063: ('GetWeaponFireDelayMin', 2, 0),
        1064: ('GetWeaponFireDelayMax', 2, 0),
        1065: ('GetWeaponAnimMult', 2, 0),
        1066: ('GetWeaponReach', 2, 0),
        1067: ('GetWeaponIsAutomatic', 2, 0),
        1068: ('GetWeaponHandGrip', 2, 0),
        1069: ('GetWeaponReloadAnim', 2, 0),
        1070: ('GetWeaponBaseVATSChance', 2, 0),
        1071: ('GetWeaponAttackAnimation', 2, 0),
        1072: ('GetWeaponNumProjectiles', 2, 0),
        1073: ('GetWeaponAimArc', 2, 0),
        1074: ('GetWeaponLimbDamageMult', 2, 0),
        1075: ('GetWeaponSightUsage', 2, 0),
        1076: ('GetWeaponHasScope', 2, 0),
        1089: ('ListGetFormIndex', 2, 2),
        1098: ('GetEquippedCurrentHealth', 1, 0),
        1102: ('GetNumItems', 0, 0),
        1105: ('GetCurrentHealth', 0, 0),
        1107: ('IsKeyPressed', 1, 1),
        1131: ('IsControlPressed', 1, 1),
        1144: ('GetArmorAR', 2, 0),
        1145: ('IsPowerArmor', 2, 0),
        1148: ('IsQuestItem', 2, 0),
        1203: ('GetArmorDT', 2, 0),
        1212: ('GetWeaponRequiredStrength', 2, 0),
        1213: ('GetWeaponRequiredSkill', 2, 0),
        1218: ('GetAmmoSpeed', 2, 0),
        1219: ('GetAmmoConsumedPercent', 2, 0),
        1254: ('GetWeaponLongBursts', 2, 0),
        1256: ('GetWeaponFlags1', 2, 0),
        1257: ('GetWeaponFlags2', 2, 0),
        1266: ('GetEquippedWeaponModFlags', 0, 0),
        1271: ('HasOwnership', 2, 0),
        1272: ('IsOwned', 2, 0),
        1274: ('GetDialogueTarget', 2, 0),
        1275: ('GetDialogueSubject', 2, 0),
        1276: ('GetDialogueSpeaker', 2, 0),
        1278: ('GetAgeClass', 2, 0),
        1286: ('GetTokenValue', 2, 0),
        1288: ('GetTokenRef', 2, 0),
        1291: ('GetPaired', 2, 2),
        1292: ('GetRespawn', 2, 0),
        1294: ('GetPermanent', 2, 0),
        1297: ('IsRefInList', 2, 2),
        1301: ('GetPackageCount', 2, 0),
        1440: ('IsPlayerSwimming', 0, 0),
        1441: ('GetTFC', 0, 0),
        1475: ('GetPerkRank', 2, 2),
        1476: ('GetAltPerkRank', 2, 2),
        1541: ('GetActorFIKstatus', 0, 0),
        1587: ('GetWeaponRegenRate', 2, 0),
        1590: ('CallFunctionCond', 2, 1),
        # Added by nvse_plugin_ExtendedActorVariable (obsolete & unreleased)
        4352: ('GetExtendedActorVariable', 2, 0),
        4353: ('GetBaseExtendedActorVariable', 2, 0),
        4355: ('GetModExtendedActorVariable', 2, 0),
        # Added by nvse_extender
        4420: ('NX_GetEVFl', 0, 0),
        4426: ('NX_GetQVEVFl', 2, 1),
        # Added by lutana_nvse (included in JIP)
        4612: ('IsButtonPressed', 1, 0),
        4613: ('GetLeftStickX', 0, 0),
        4614: ('GetLeftStickY', 0, 0),
        4615: ('GetRightStickX', 0, 0),
        4616: ('GetRightStickY', 0, 0),
        4617: ('GetLeftTrigger', 0, 0),
        4618: ('GetRightTrigger', 0, 0),
        4708: ('GetArmorClass', 2, 0),
        4709: ('IsRaceInList', 2, 0),
        4758: ('IsButtonDisabled', 1, 0),
        4761: ('IsButtonHeld', 1, 0),
        4774: ('IsTriggerDisabled', 1, 0),
        4777: ('IsTriggerHeld', 1, 0),
        4822: ('GetReferenceFlag', 1, 0),
        4832: ('GetDistance2D', 2, 0),
        4833: ('GetDistance3D', 2, 0),
        4843: ('PlayerHasKey', 0, 0),
        4897: ('ActorHasEffect', 2, 0),
        # Added by JIP NVSE Plugin - up to date with v56.76
        5637: ('GetIsPoisoned', 0, 0),
        5708: ('IsEquippedWeaponSilenced', 0, 0),
        5709: ('IsEquippedWeaponScoped', 0, 0),
        5884: ('IsPCInCombat', 0, 0),
        5894: ('GetEncumbranceRate', 0, 0),
        5947: ('GetActorLightAmount', 0, 0),
        5951: ('GetGameDifficulty', 0, 0),
        5962: ('GetPCDetectionState', 0, 0),
        5969: ('GetPipboyRadio', 0, 0),
        5993: ('IsAttacking', 0, 0),
        5994: ('GetPCUsingScope', 0, 0),
        6010: ('GetPCUsingIronSights', 0, 0),
        6012: ('GetRadiationLevelAlt', 0, 0),
        6013: ('IsInWater', 0, 0),
        6058: ('GetAlwaysRun', 0, 0),
        6059: ('GetAutoMove', 0, 0),
        6061: ('GetIsRagdolled', 0, 0),
        6065: ('AuxVarGetFltCond', 2, 1),
        6069: ('IsInAir', 0, 0),
        6073: ('GetHasContactType', 1, 0),
        6124: ('IsSpellTargetAlt', 2, 0),
        6167: ('IsIdlePlayingEx', 0, 0),
        6186: ('IsInCharGen', 0, 0),
        6192: ('GetWaterImmersionPerc', 0, 0),
        6204: ('IsFleeing', 0, 0),
        6217: ('GetTargetUnreachable', 0, 0),
        6268: ('IsInKillCam', 0, 0),
        6301: ('IsStickDisabled', 1, 0),
        6317: ('GetHardcoreTracking', 0, 0),
        6321: ('GetNoteRead', 2, 0),
        6361: ('GetInFactionList', 2, 0),
        6368: ('GetGroundMaterial', 0, 0),
        6391: ('EquippedWeaponHasModType', 1, 0),
        6426: ('IsSpellTargetList', 2, 0),
        # Added by JohnnyGuitar NVSE - up to date with v4.85
        8501: ('GetBaseScale', 0, 0),
        8549: ('GetQuestFailed', 2, 0),
        8623: ('GetLocationSpecificLoadScreensOnly', 0, 0),
        # Added by TTW nvse plugin
        10247: ('TTW_GetEquippedWeaponSkill', 0, 0),
    }
    # Remove functions with different indices in FNV
    del condition_function_data[1082] # IsKeyPressed, 1107 in FNV
    del condition_function_data[1165] # GetWeaponHasScope, 1076 in FNV
    del condition_function_data[1166] # IsControlPressed, 1131 in FNV

    #--------------------------------------------------------------------------
    # Import Names
    #--------------------------------------------------------------------------
    names_types = Fallout3GameInfo.names_types | {
        b'CCRD', b'CHAL', b'CHIP', b'CMNY', b'CSNO', b'IMOD', b'RCCT', b'RCPE',
        b'REPU',
    }

    #--------------------------------------------------------------------------
    # Import Stats
    #--------------------------------------------------------------------------
    stats_csv_attrs = Fallout3GameInfo.stats_csv_attrs | {
        b'AMMO': ('eid', 'weight', 'value', 'speed', 'clipRounds',
                  'projPerShot'),
        b'ARMA': ('eid', 'weight', 'value', 'health', 'dr', 'dt'),
        b'ARMO': ('eid', 'weight', 'value', 'health', 'dr', 'dt'),
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
            'semiAutomaticFireDelayMax', 'strengthReq', 'regenRate',
            'killImpulse', 'impulseDist', 'skillReq', 'criticalDamage',
            'criticalMultiplier', 'vatsSkill', 'vatsDamMult', 'vatsAp'),
    }
    stats_attrs = {r: tuple(x for x in a if x != 'eid')
                   for r, a in stats_csv_attrs.items()}

    #--------------------------------------------------------------------------
    # Import Sounds
    #--------------------------------------------------------------------------
    sounds_attrs = Fallout3GameInfo.sounds_attrs | {
        b'STAT': ('passthroughSound',),
    }
    sounds_fid_attrs = Fallout3GameInfo.sounds_fid_attrs | {
        b'ASPC': ('sound_dawn_default_loop', 'sound_afternoon', 'sound_dusk',
                  'sound_night', 'sound_walla', 'use_sound_from_region'),
        b'CONT': ('sound', 'sound_close', 'sound_random_looping'),
        b'KEYM': ('sound_pickup', 'sound_drop', 'sound_random_looping'),
        b'MISC': ('sound_pickup', 'sound_drop', 'sound_random_looping'),
        b'STAT': ('sound_random_looping',),
        b'WEAP': ('sound_pickup', 'sound_drop', 'sound_gun_shoot_3d',
                  'sound_gun_shoot_dist', 'soundGunShot2D',
                  'soundGunShot3DLooping', 'soundMeleeSwingGunNoAmmo',
                  'soundBlock', 'idleSound', 'equipSound', 'unequipSound',
                  'sound_mod1_shoot_3d', 'sound_mod1_shoot_dist',
                  'sound_mod1_shoot_2d'),
    }

    #--------------------------------------------------------------------------
    # Import Graphics
    #--------------------------------------------------------------------------
    graphicsTypes = Fallout3GameInfo.graphicsTypes | {
        b'CCRD': ('iconPath', 'smallIconPath', 'model', 'textureFace',
                  'textureBack'),
        b'CHAL': ('iconPath', 'smallIconPath'),
        b'CHIP': ('iconPath', 'smallIconPath', 'model'),
        b'CMNY': ('iconPath', 'smallIconPath', 'model'),
        b'CSNO': ('chipModels', 'slotMachineModel', 'blackjackTableModel',
                  'extraBlackjackTableModel', 'rouletteTableModel',
                  'slotReelTextures', 'blackjackDecks'),
        b'IMOD': ('iconPath', 'smallIconPath', 'model'),
        b'REPU': ('iconPath', 'smallIconPath'),
        b'WEAP': ('iconPath', 'smallIconPath', 'model', 'shellCasingModel',
                  'scopeModel', 'worldModel', 'modelWithMods',
                  'firstPersonModelWithMods', 'animationType', 'gripAnimation',
                  'reloadAnimation'),
    }

    #--------------------------------------------------------------------------
    # Import Text
    #--------------------------------------------------------------------------
    text_types = Fallout3GameInfo.text_types | {
        b'ACTI': ('activation_prompt',),
        b'AMMO': ('short_name', 'abbreviation'),
        b'CHAL': ('description',),
        b'IMOD': ('description',),
    }

    #--------------------------------------------------------------------------
    # Import Object Bounds
    #--------------------------------------------------------------------------
    object_bounds_types = Fallout3GameInfo.object_bounds_types | {
        b'CCRD', b'CHIP', b'CMNY', b'IMOD',
    }

    #--------------------------------------------------------------------------
    # Contents Checker
    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
    # Import Scripts
    #--------------------------------------------------------------------------
    scripts_types = Fallout3GameInfo.scripts_types | {
        b'AMMO', b'CCRD', b'CHAL', b'IMOD',
    }

    #--------------------------------------------------------------------------
    # Import Destructible
    #--------------------------------------------------------------------------
    destructible_types = Fallout3GameInfo.destructible_types | {
        b'CHIP', b'IMOD',
    }

    #--------------------------------------------------------------------------
    # Import Actors
    #--------------------------------------------------------------------------
    actor_importer_attrs = deepcopy(Fallout3GameInfo.actor_importer_attrs)
    actor_importer_attrs[b'NPC_']['Actors.ACBS'] += (
        'npc_flags.auto_calc_service',)

    #--------------------------------------------------------------------------
    # Tweak Assorted
    #--------------------------------------------------------------------------
    assorted_tweaks= Fallout3GameInfo.assorted_tweaks | {
        'AssortedTweak_ArrowWeight'}

    #--------------------------------------------------------------------------
    # Tweak Settings
    #--------------------------------------------------------------------------
    settings_tweaks = Fallout3GameInfo.settings_tweaks | {
        'GmstTweak_Actor_StrengthEncumbranceMultiplier'}

    #--------------------------------------------------------------------------
    # Tweak Names
    #--------------------------------------------------------------------------
    names_tweaks = ((Fallout3GameInfo.names_tweaks |
                    {'NamesTweak_AmmoWeight_Fnv'}) -
                    {'NamesTweak_AmmoWeight_Fo3'})

    @classmethod
    def _dynamic_import_modules(cls, package_name):
        super(FalloutNVGameInfo, cls)._dynamic_import_modules(package_name)
        from .patcher import preservers
        cls.game_specific_import_patchers = {
            'ImportWeaponModifications':
                preservers.ImportWeaponModificationsPatcher,
        }

    top_groups = [
        b'GMST', b'TXST', b'MICN', b'GLOB', b'CLAS', b'FACT', b'HDPT', b'HAIR',
        b'EYES', b'RACE', b'SOUN', b'ASPC', b'MGEF', b'SCPT', b'LTEX', b'ENCH',
        b'SPEL', b'ACTI', b'TACT', b'TERM', b'ARMO', b'BOOK', b'CONT', b'DOOR',
        b'INGR', b'LIGH', b'MISC', b'STAT', b'SCOL', b'MSTT', b'PWAT', b'GRAS',
        b'TREE', b'FURN', b'WEAP', b'AMMO', b'NPC_', b'CREA', b'LVLC', b'LVLN',
        b'KEYM', b'ALCH', b'IDLM', b'NOTE', b'COBJ', b'PROJ', b'LVLI', b'WTHR',
        b'CLMT', b'REGN', b'NAVI', b'DIAL', b'QUST', b'IDLE', b'PACK', b'CSTY',
        b'LSCR', b'ANIO', b'WATR', b'EFSH', b'EXPL', b'DEBR', b'IMGS', b'IMAD',
        b'FLST', b'PERK', b'BPTD', b'ADDN', b'AVIF', b'RADS', b'CAMS', b'CPTH',
        b'VTYP', b'IPCT', b'IPDS', b'ARMA', b'ECZN', b'MESG', b'RGDL', b'DOBJ',
        b'LGTM', b'MUSC', b'IMOD', b'REPU', b'RCPE', b'RCCT', b'CHIP', b'CSNO',
        b'LSCT', b'MSET', b'ALOC', b'CHAL', b'AMEF', b'CCRD', b'CMNY', b'CDCK',
        b'DEHY', b'HUNG', b'SLPD', b'CELL', b'WRLD',
    ]

    @classmethod
    def init(cls, _package_name=None):
        super().init(_package_name or __name__)

    @classmethod
    def _import_records(cls, package_name, plugin_form_vers=None):
        # import our records from falloutnv.records as it imports fallout3 ones
        super()._import_records(__name__)

# Language dirs, shared by EGS and WS versions
FNV_LANG_DIRS = ['Fallout New Vegas English', 'Fallout New Vegas French',
                 'Fallout New Vegas German', 'Fallout New Vegas Italian',
                 'Fallout New Vegas Spanish']

class EGSFalloutNVGameInfo(FalloutNVGameInfo):
    """GameInfo override for the Epic Games Store version of Fallout New
    Vegas."""
    displayName = 'Fallout New Vegas (EGS)'
    my_games_name = 'FalloutNV_Epic'
    appdata_name = 'FalloutNV_Epic'

    @classproperty
    def game_detect_includes(cls):
        return super().game_detect_includes | {'EOSSDK-Win32-Shipping.dll'}

    @classproperty
    def game_detect_excludes(cls):
        return super().game_detect_excludes - {'EOSSDK-Win32-Shipping.dll'}

    class Eg(FalloutNVGameInfo.Eg):
        egs_app_names = ['5daeb974a22a435988892319b3a4f476']
        egs_language_dirs = FNV_LANG_DIRS

class GOGFalloutNVGameInfo(GOGMixin, FalloutNVGameInfo):
    """GameInfo override for the GOG version of Fallout New Vegas."""
    displayName = 'Fallout New Vegas (GOG)'
    _gog_game_ids = _GOG_IDS
    # appdata_name and my_games_name use the original locations

class WSFalloutNVGameInfo(WindowsStoreMixin, FalloutNVGameInfo):
    """GameInfo override for the Windows Store version of Fallout New Vegas."""
    displayName = 'Fallout New Vegas (WS)'
    # appdata_name and my_games_name use the original locations

    class Ws(FalloutNVGameInfo.Ws):
        legacy_publisher_name = 'Bethesda'
        win_store_name = 'BethesdaSoftworks.FalloutNewVegas'
        ws_language_dirs = FNV_LANG_DIRS

GAME_TYPE = {g.displayName: g for g in
             (FalloutNVGameInfo, EGSFalloutNVGameInfo, GOGFalloutNVGameInfo,
              WSFalloutNVGameInfo)}
