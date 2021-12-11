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
"""GameInfo override for TES IV: Oblivion."""
import struct as _struct
from collections import defaultdict
from os.path import join as _j

from ..patch_game import GameInfo, PatchGame
from .. import WS_COMMON
from ... import brec
from ...brec import MreGlob, MreLand

class OblivionGameInfo(PatchGame):
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
    # Set to this because that file does not exist in Nehrim, whereas
    # OblivionLauncher.exe and Oblivion.exe do
    game_detect_includes = [_j(u'Data', u'Oblivion.esm')]
    game_detect_excludes = WS_COMMON
    version_detect_file = u'Oblivion.exe'
    master_file = u'Oblivion.esm'
    taglist_dir = u'Oblivion'
    loot_dir = u'Oblivion'
    boss_game_name = u'Oblivion'
    regInstallKeys = (u'Bethesda Softworks\\Oblivion', u'Installed Path')
    nexusUrl = u'https://www.nexusmods.com/oblivion/'
    nexusName = u'Oblivion Nexus'
    nexusKey = u'bash.installers.openOblivionNexus.continue'

    patchURL = u'http://www.elderscrolls.com/downloads/updates_patches.htm'
    patchTip = u'http://www.elderscrolls.com/'

    using_txt_file = False
    has_standalone_pluggy = True

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
        supports_mod_inis = False

    class Ess(GameInfo.Ess):
        canEditMore = True
        can_safely_remove_masters = True

    class Bsa(GameInfo.Bsa):
        allow_reset_timestamps = True
        # Oblivion accepts the base name and literally *anything* after
        # that. E.g. MyModMeshes.bsa will load from a MyMod.esp plugin
        attachment_regex = u'.*'
        redate_dict = defaultdict(lambda: 1136066400, { # '2006-01-01',
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
            u'_tejon',
            u'distantlod',
            u'facegen',
            u'fonts',
            u'menus',
            u'obse',
            u'pluggy',
            u'scripts',
            u'shaders',
            u'streamline',
            u'trees',
        }
        keep_data_dirs = {
            _j(u'OBSE', u'Plugins', u'ComponentDLLs', u'CSE'),
            u'LSData'
        }
        keep_data_files = {
            _j(u'OBSE', u'Plugins', u'Construction Set Extender.dll'),
            _j(u'OBSE', u'Plugins', u'Construction Set Extender.ini'),
        }
        keep_data_file_prefixes = {
            _j(u'Meshes', u'Characters', u'_Male', u'specialanims',
                u'0FemaleVariableWalk_'),
        }
        skip_bain_refresh = {
            u'tes4edit backups',
            u'tes4edit cache',
            u'bgsee',
            u'conscribe logs',
        }
        wrye_bash_data_files = {u'ArchiveInvalidationInvalidated!.bsa'}

    class Esp(GameInfo.Esp):
        canBash = True
        canEditHeader = True
        validHeaderVersions = (0.8,1.0)
        stringsFiles = []
        biped_flag_names = (u'head', u'hair', u'upperBody', u'lowerBody',
                            u'hand', u'foot', u'rightRing', u'leftRing',
                            u'amulet', u'weapon', u'backWeapon', u'sideWeapon',
                            u'quiver', u'shield', u'torch', u'tail')
        reference_types = {b'ACHR', b'ACRE', b'REFR'}

    allTags = PatchGame.allTags | {u'IIM', u'NoMerge'}

    patchers = {
        u'AliasModNames', u'CoblCatalogs', u'CoblExhaustion',
        u'ContentsChecker', u'ImportActors', u'ImportActorsAIPackages',
        u'ImportActorsAnimations', u'ImportActorsDeathItems',
        u'ImportActorsFaces', u'ImportActorsFactions', u'ImportActorsSpells',
        u'ImportCells', u'ImportEffectsStats', u'ImportEnchantmentStats',
        u'ImportGraphics', u'ImportInventory', u'ImportNames',
        u'ImportRelations', u'ImportRoads', u'ImportScripts', u'ImportSounds',
        u'ImportSpellStats', u'ImportStats', u'ImportText', u'LeveledLists',
        u'MergePatches', u'MorphFactions', u'NpcChecker', u'ReplaceFormIDs',
        u'SEWorldTests', u'TweakActors', u'TweakAssorted', u'TweakClothes',
        u'TweakNames', u'TweakSettings', u'ImportRaces', u'ImportRacesSpells',
        u'ImportRacesRelations', u'EyeChecker', u'TweakRaces', u'RaceChecker',
        u'TimescaleChecker',
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
        #--Vanilla
        u'oblivion.esm',
        u'oblivion_1.1.esm',
        u'oblivion_si.esm',
        u'oblivion - meshes.bsa',
        u'oblivion - misc.bsa',
        u'oblivion - sounds.bsa',
        u'oblivion - textures - compressed.bsa',
        u'oblivion - textures - compressed.bsa.orig',
        u'oblivion - voices1.bsa',
        u'oblivion - voices2.bsa',
        #--Shivering Isles
        u'dlcshiveringisles.esp',
        u'dlcshiveringisles - meshes.bsa',
        u'dlcshiveringisles - sounds.bsa',
        u'dlcshiveringisles - textures.bsa',
        u'dlcshiveringisles - voices.bsa',
        #--Knights of the Nine - shipped with all WS versions
        u'knights.esp',
        u'knights.bsa',
    }

    @classmethod
    def _dynamic_import_modules(cls, package_name):
        super(OblivionGameInfo, cls)._dynamic_import_modules(package_name)
        # Do the imports *after setting the _constants_members*
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
    def init(cls):
        cls._dynamic_import_modules(__name__)
        from .records import MreActi, MreAlch, MreAmmo, MreAnio, MreAppa, \
            MreArmo, MreBook, MreBsgn, MreClas, MreClot, MreCont, MreCrea, \
            MreDoor, MreEfsh, MreEnch, MreEyes, MreFact, MreFlor, MreFurn, \
            MreGras, MreHair, MreIngr, MreKeym, MreLigh, MreLscr, MreLvlc, \
            MreLvli, MreLvsp, MreMgef, MreMisc, MreNpc, MrePack, MreQust, \
            MreRace, MreScpt, MreSgst, MreSlgm, MreSoun, MreSpel, MreStat, \
            MreTree, MreWatr, MreWeap, MreWthr, MreClmt, MreCsty, MreIdle, \
            MreLtex, MreRegn, MreSbsp, MreSkil, MreAchr, MreAcre, MreCell, \
            MreGmst, MreRefr, MreRoad, MreTes4, MreWrld, MreDial, MreInfo, \
            MrePgrd
        cls.mergeable_sigs = {clazz.rec_sig: clazz for clazz in (
            MreActi, MreAlch, MreAmmo, MreAnio, MreAppa, MreArmo, MreBook,
            MreBsgn, MreClas, MreClot, MreCont, MreCrea, MreDoor, MreEfsh,
            MreEnch, MreEyes, MreFact, MreFlor, MreFurn, MreGlob, MreGras,
            MreHair, MreIngr, MreKeym, MreLigh, MreLscr, MreLvlc, MreLvli,
            MreLvsp, MreMgef, MreMisc, MreNpc, MrePack, MreQust, MreRace,
            MreScpt, MreSgst, MreSlgm, MreSoun, MreSpel, MreStat, MreTree,
            MreWatr, MreWeap, MreWthr, MreClmt, MreCsty, MreIdle, MreLtex,
            MreRegn, MreSbsp, MreSkil, MreAchr, MreAcre, MreCell, MreGmst,
            MreRefr, MreRoad, MreWrld, MreDial, MreInfo, MreLand, MrePgrd,
        )}
        cls.readClasses = (b'MGEF', b'SCPT')
        cls.writeClasses = (b'MGEF',)
        # Setting RecordHeader class variables - Oblivion is special
        header_type = brec.RecordHeader
        header_type.rec_header_size = 20
        header_type.rec_pack_format = [u'=4s', u'I', u'I', u'I', u'I']
        header_type.rec_pack_format_str = u''.join(header_type.rec_pack_format)
        header_type.header_unpack = _struct.Struct(
            header_type.rec_pack_format_str).unpack
        header_type.pack_formats = {0: u'=4sI4s2I'}
        header_type.pack_formats.update(
            {x: u'=4s4I' for x in {1, 6, 7, 8, 9, 10}})
        header_type.pack_formats.update({x: u'=4sIi2I' for x in {2, 3}})
        header_type.pack_formats.update({x: u'=4sIhh2I' for x in {4, 5}})
        # Similar to other games
        header_type.top_grup_sigs = [
            b'GMST', b'GLOB', b'CLAS', b'FACT', b'HAIR', b'EYES', b'RACE',
            b'SOUN', b'SKIL', b'MGEF', b'SCPT', b'LTEX', b'ENCH', b'SPEL',
            b'BSGN', b'ACTI', b'APPA', b'ARMO', b'BOOK', b'CLOT', b'CONT',
            b'DOOR', b'INGR', b'LIGH', b'MISC', b'STAT', b'GRAS', b'TREE',
            b'FLOR', b'FURN', b'WEAP', b'AMMO', b'NPC_', b'CREA', b'LVLC',
            b'SLGM', b'KEYM', b'ALCH', b'SBSP', b'SGST', b'LVLI', b'WTHR',
            b'CLMT', b'REGN', b'CELL', b'WRLD', b'DIAL', b'QUST', b'IDLE',
            b'PACK', b'CSTY', b'LSCR', b'LVSP', b'ANIO', b'WATR', b'EFSH',
        ]
        header_type.valid_header_sigs = set(
            header_type.top_grup_sigs + [b'GRUP', b'TES4', b'ROAD', b'REFR',
                                         b'ACHR', b'ACRE', b'PGRD', b'LAND',
                                         b'INFO'])
        brec.MreRecord.type_class = {x.rec_sig: x for x in (
            MreAchr, MreAcre, MreActi, MreAlch, MreAmmo, MreAnio, MreAppa,
            MreArmo, MreBook, MreBsgn, MreCell, MreClas, MreClot, MreCont,
            MreCrea, MreDoor, MreEfsh, MreEnch, MreEyes, MreFact, MreFlor,
            MreFurn, MreGlob, MreGmst, MreGras, MreHair, MreIngr, MreKeym,
            MreLigh, MreLscr, MreLvlc, MreLvli, MreLvsp, MreMgef, MreMisc,
            MreNpc, MrePack, MreQust, MreRace, MreRefr, MreRoad, MreScpt,
            MreSgst, MreSkil, MreSlgm, MreSoun, MreSpel, MreStat, MreTree,
            MreTes4, MreWatr, MreWeap, MreWrld, MreWthr, MreClmt, MreCsty,
            MreIdle, MreLtex, MreRegn, MreSbsp, MreDial, MreInfo, MreLand,
            MrePgrd)}
        brec.MreRecord.simpleTypes = (set(brec.MreRecord.type_class) - {
            b'TES4', b'ACHR', b'ACRE', b'REFR', b'CELL', b'PGRD', b'ROAD',
            b'LAND', b'WRLD', b'INFO', b'DIAL'})
        cls._validate_records()

GAME_TYPE = OblivionGameInfo
