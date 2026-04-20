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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2026 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from os.path import join as _j

from .. import GameInfo
from ..oblivion import AOblivionGameInfo
from ..store_mixins import SteamMixin
from ...bolt import FName
from ...games_lo import TextfileGame
from ...plugin_types import NoMasterFlag

class _AOblivionReGameInfo(AOblivionGameInfo):
    display_name = 'Oblivion Remastered'
    fsName = 'OblivionRE'
    altName = 'Wrye Bash Remastered'
    bash_root_prefix = 'OblivionRE'
    bak_game_name = 'OblivionRE'
    my_games_name = 'Oblivion Remastered'
    appdata_name = ''
    executable_dir = ['OblivionRemastered', 'Binaries', 'Win64']
    launch_exe = 'OblivionRemastered-Win64-Shipping.exe'
    game_detect_includes = {'OblivionRemastered'} # it's a folder for ORE
    game_detect_excludes = set()
    version_detect_file = 'OblivionRemastered-Win64-Shipping.exe'
    mods_dir_path = ['OblivionRemastered', 'Content', 'Dev', 'ObvData', 'Data']
    nexusUrl = 'https://www.nexusmods.com/oblivionremastered/'
    nexusName = 'Oblivion Remastered Nexus'
    nexusKey = 'bash.installers.openOblivionRemasteredNexus.continue'
    master_flags = NoMasterFlag # no master flag for ORE

    has_standalone_pluggy = False
    check_legacy_paths = False
    has_obmm = False

    @staticmethod
    def get_lo_dir(bass_dirs):
        # Plugins.txt is in the Data folder for this game
        return bass_dirs['mods']

    class Ck(GameInfo.Ck): # No CS/CK yet, maybe won't ever come
        pass

    class Se(AOblivionGameInfo.Se):
        se_abbrev = 'OBSE64'
        long_name = 'Oblivion Remastered Script Extender'
        exe = 'obse64_loader.exe'
        ver_files = ['obse64_loader.exe', 'obse64_0_411_140.dll']
        url = 'https://www.nexusmods.com/oblivionremastered/mods/282'
        url_tip = 'https://www.nexusmods.com/oblivionremastered/mods/282'
        limit_fixer_plugins = []

        @classmethod
        def exe_path_sc(cls, bass_dirs):
            # Skip the Steam-avoiding logic in AOblivionGameInfo.Se
            ##: Revisit all this in #703
            return super(AOblivionGameInfo.Se, cls).exe_path_sc(bass_dirs)

    class Ge(GameInfo.Ge):
        pass

    class Ini(AOblivionGameInfo.Ini):
        bsa_redirection_key = ('', '')
        default_ini_file = _j('OblivionRemastered', 'Content', 'Dev',
            'ObvData', 'Oblivion_default.ini')
        # TODO(OblivionRE): Is BSA redirection still needed?
        game_inis_in_my_documents = False
        has_obse_inis = True # TODO(OblivionRE): Are these INIs still a thing?
        save_profiles_key = ()

    class Ess(GameInfo.Ess):
        ext = '.sav'
        has_screenshots = False
        save_skips = {'Save_Settings.sav', 'Save_Settings.sav.bak',
                      'saves_meta.sav', 'saves_meta.sav.bak'}
        saves_dir = _j('Saved', 'SaveGames')

    class Xe(AOblivionGameInfo.Xe):
        full_name = 'TES4REdit'
        xe_key_prefix = 'tes4rView'

    # TODO(OblivionRE): Handle any necessary BAIN updates in #719
    class Bain(AOblivionGameInfo.Bain):
        data_dirs = AOblivionGameInfo.Bain.data_dirs - {
            # OBSE plugins have to go to
            # OblivionRemastered/Binaries/Win64/OBSE/Plugins, tackle in #719
            'obse',
            'pluggy', # 3P: Pluggy - hasn't been ported to Oblivion Remastered
        } | {
            'magicloader', # 3P: MagicLoader 2
            'syncmap', # 3P: UE4SS TesSyncMapInjector
        }
        keep_data_dirs = {'lsdata'}
        keep_data_files = set()
        skip_bain_refresh = AOblivionGameInfo.Bain.skip_bain_refresh - {
            'tes4edit backups',
            'tes4edit cache',
        } | {
            'tes4redit backups',
            'tes4redit cache',
        }
        wrye_bash_data_files = AOblivionGameInfo.Bain.wrye_bash_data_files | {
            'loadorder.txt', 'loadorder.txt.bak', 'plugins.txt.bak',
        }

    patchers = AOblivionGameInfo.patchers - {
        'RaceChecker',
    }

    #--------------------------------------------------------------------------
    # Tweak Actors
    #--------------------------------------------------------------------------
    actor_tweaks = {
        'AsIntendedBoarsPatcher',
        'AsIntendedImpsPatcher',
        'IrresponsibleCreaturesPatcher',
    }

    #--------------------------------------------------------------------------
    # Tweak Assorted
    #--------------------------------------------------------------------------
    assorted_tweaks = {
        'AssortedTweak_ArmorPlayable',
        'AssortedTweak_ArrowWeight',
        'AssortedTweak_AttackSpeedStavesMaximum',
        'AssortedTweak_AttackSpeedStavesMinimum',
        'AssortedTweak_BookWeight',
        'AssortedTweak_BowReach',
        'AssortedTweak_ClothingPlayable',
        'AssortedTweak_FactioncrimeGoldMultiplier',
        'AssortedTweak_HarvestChance',
        'AssortedTweak_IngredientWeight',
        'AssortedTweak_PotionWeight',
        'AssortedTweak_PotionWeightMinimum',
        'AssortedTweak_ScriptEffectSilencer',
        'AssortedTweak_SetCastWhenUsedEnchantmentCosts',
        'AssortedTweak_SkyrimStyleWeapons',
        'AssortedTweak_StaffWeight',
        'AssortedTweak_TextlessLSCRs',
    }

    #--------------------------------------------------------------------------
    # Tweak Names
    #--------------------------------------------------------------------------
    names_tweaks = set()

    #--------------------------------------------------------------------------
    # Tweak Races
    #--------------------------------------------------------------------------
    race_tweaks = {
        'RaceTweak_BiggerOrcsAndNords',
    }

    #--------------------------------------------------------------------------
    # Tweak Settings
    #--------------------------------------------------------------------------
    settings_tweaks = {
        'GlobalsTweak_Timescale',
        'GmstTweak_Actor_GreetingDistance',
        'GmstTweak_Actor_MaxJumpHeight_Tes4',
        'GmstTweak_Actor_TrainingLimit',
        'GmstTweak_Actor_UnconsciousnessDuration',
        'GmstTweak_AI_ConversationChance',
        'GmstTweak_AI_ConversationChance_Interior',
        'GmstTweak_AI_MaxActiveActors',
        'GmstTweak_Arrow_LitterCount',
        'GmstTweak_Arrow_Speed',
        'GmstTweak_Bounty_Assault',
        'GmstTweak_Bounty_HorseTheft',
        'GmstTweak_Bounty_Jailbreak',
        'GmstTweak_Bounty_Murder',
        'GmstTweak_Bounty_Pickpocketing',
        'GmstTweak_Bounty_Theft',
        'GmstTweak_Bounty_Trespassing',
        'GmstTweak_Combat_Alchemy',
        'GmstTweak_Combat_MaxActors',
        'GmstTweak_Combat_MaximumArmorRating',
        'GmstTweak_Combat_RechargeWeapons',
        'GmstTweak_Combat_Repair',
        'GmstTweak_Compass_RecognitionDistance',
        'GmstTweak_CostMultiplier_Enchantment',
        'GmstTweak_CostMultiplier_Recharge',
        'GmstTweak_CostMultiplier_Repair',
        'GmstTweak_CostMultiplier_SpellMaking',
        'GmstTweak_Crime_AlarmDistance',
        'GmstTweak_LevelDifference_CreatureMax',
        'GmstTweak_LevelDifference_ItemMax',
        'GmstTweak_LevelUp_SkillCount',
        'GmstTweak_Magic_BoltSpeed',
        'GmstTweak_Magic_MaxNPCSummons',
        'GmstTweak_Magic_MaxPlayerSummons',
        'GmstTweak_Movement_FatigueFromRunningEncumbrance',
        'GmstTweak_Player_HorseTurningSpeed',
        'GmstTweak_Player_InventoryQuantityPrompt_Tes4',
        'GmstTweak_Player_MaxDraggableWeight',
        'GmstTweak_Warning_ExteriorDistanceToHostiles',
        'GmstTweak_Warning_InteriorDistanceToHostiles',
        'GmstTweak_World_CellRespawnTime',
    }

    bethDataFiles = {
        'altardeluxe.bsa',
        'altardeluxe.esp',
        'altaresplocal.bsa',
        'altaresplocal.esp',
        'altarespmain.bsa',
        'altarespmain.esp',
        'altargymnavigation.esp',
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
        'oblivion - voices1.bsa',
        'oblivion - voices2.bsa',
        'oblivion.esm',
        'tamrielleveledregion.esp',
    }

    class _LoOblivionRe(TextfileGame):
        force_load_first = tuple(map(FName, (
            'DLCBattlehornCastle.esp',
            'DLCFrostcrag.esp',
            'DLCHorseArmor.esp',
            'DLCMehrunesRazor.esp',
            'DLCOrrery.esp',
            'DLCShiveringIsles.esp',
            'DLCSpellTomes.esp',
            'DLCThievesDen.esp',
            'DLCVileLair.esp',
            'Knights.esp',
            'AltarESPMain.esp',
            'AltarDeluxe.esp',
            'AltarESPLocal.esp',
        )))
        # Oblivion Remastered crashes if Oblivion.esm is not in plugins.txt
        _remove_game_master_from_plugins_txt = False

    lo_handler = _LoOblivionRe

    @classmethod
    def init(cls, _package_name=None):
        super().init(_package_name or __name__)

class SteamOblivionReGameInfo(SteamMixin, _AOblivionReGameInfo):
    class St(_AOblivionReGameInfo.St):
        steam_ids = [2623190]

GAME_TYPE = SteamOblivionReGameInfo
