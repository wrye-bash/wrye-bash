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
"""GameInfo override for TES III: Morrowind."""
import struct as _struct
from collections import defaultdict

from ..patch_game import GameInfo, PatchGame
from .. import WS_COMMON
from ... import brec

class MorrowindGameInfo(PatchGame):
    displayName = u'Morrowind'
    fsName = u'Morrowind'
    altName = u'Wrye Mash'
    game_icon = u'morrowind_%u.png'
    bash_root_prefix = u'Morrowind'
    bak_game_name = u'Morrowind'
    uses_personal_folders = False
    appdata_name = u'Morrowind'
    launch_exe = u'Morrowind.exe'
    game_detect_includes = [u'Morrowind.exe']
    game_detect_excludes = WS_COMMON
    version_detect_file = u'Morrowind.exe'
    master_file = u'Morrowind.esm'
    mods_dir = u'Data Files'
    taglist_dir = u'Morrowind'
    loot_dir = u'Morrowind'
    # This is according to xEdit's sources, but it doesn't make that key for me
    regInstallKeys = (u'Bethesda Softworks\\Morrowind', u'Installed Path')
    nexusUrl = u'https://www.nexusmods.com/morrowind/'
    nexusName = u'Morrowind Nexus'
    nexusKey = u'bash.installers.openMorrowindNexus.continue'

    using_txt_file = False
    plugin_name_specific_dirs = [] # Morrowind seems to have no such dirs

    class Ck(GameInfo.Ck):
        ck_abbrev = u'TESCS'
        long_name = u'Construction Set'
        exe = u'TES Construction Set.exe'
        image_name = u'tescs%s.png'

    # TODO(inf) MWSE and MGE are vastly different from the later game versions

    class Ini(GameInfo.Ini): # No BSA Redirection, TODO need BSA Invalidation
        default_ini_file = u'Morrowind.ini'
        dropdown_inis = [u'Morrowind.ini']
        screenshot_enabled_key = (u'General', u'Screen Shot Enable', u'1')
        screenshot_base_key = (u'General', u'Screen Shot Base Name',
                               u'ScreenShot')
        screenshot_index_key = (u'General', u'Screen Shot Index', u'0')
        supports_mod_inis = False

    class Bsa(GameInfo.Bsa):
        allow_reset_timestamps = True
        redate_dict = defaultdict(lambda: 1054674000, { # '2003-06-04'
            'Morrowind.bsa': 1020200400, # '2002-05-01'
            'Tribunal.bsa': 1036533600,  # '2002-11-06'
            'Bloodmoon.bsa': 1054587600, # '2003-06-03'
        })

    class Xe(GameInfo.Xe):
        full_name = u'TES3Edit'
        xe_key_prefix = u'tes3View'

    class Bain(GameInfo.Bain):
        data_dirs = GameInfo.Bain.data_dirs | {
            u'bookart',
            u'fonts',
            u'icons',
            u'mwse',
            u'shaders',
            u'splash',
        }
        skip_bain_refresh = {
            u'tes3edit backups',
            u'tes3edit cache',
        }
        # 'Mash' is not used by us, but kept here so we don't clean out Wrye
        # Mash table files
        wrye_bash_data_dirs = GameInfo.Bain.wrye_bash_data_dirs | {u'Mash'}

    class Esp(GameInfo.Esp):
        check_master_sizes = True
        max_lvl_list_size = 2 ** 32 - 1
        plugin_header_sig = b'TES3'
        stringsFiles = []
        validHeaderVersions = (1.2, 1.3)

    bethDataFiles = {
        #--Vanilla
        u'morrowind.esm',
        u'morrowind.bsa',
        u'tribunal.esm',
        u'tribunal.bsa',
        u'bloodmoon.esm',
        u'bloodmoon.bsa',
    }

    @classmethod
    def _dynamic_import_modules(cls, package_name):
        """morrowind has no patcher currently - read tweaks, vanilla_files"""
        super(PatchGame, cls)._dynamic_import_modules(package_name)

    @classmethod
    def init(cls):
        cls._dynamic_import_modules(__name__)
        from .records import MreActi, MreAlch, MreAppa, MreArmo, MreBody, \
            MreBook, MreBsgn, MreCell, MreClas, MreClot, MreCont, MreCrea, \
            MreDial, MreDoor, MreEnch, MreFact, MreGmst, MreGlob, MreInfo, \
            MreIngr, MreLand, MreLevc, MreLevi, MreLigh, MreLock, MreLtex, \
            MreMgef, MreMisc, MreNpc,  MrePgrd, MreProb, MreRace, MreRegn, \
            MreRepa, MreScpt, MreSkil, MreSndg, MreSoun, MreSpel, MreSscr, \
            MreStat, MreTes3, MreWeap
        # Setting RecordHeader class variables - Morrowind is special
        header_type = brec.RecordHeader
        header_type.rec_header_size = 16
        header_type.rec_pack_format = [u'=4s', u'I', u'I', u'I']
        header_type.rec_pack_format_str = u''.join(header_type.rec_pack_format)
        header_type.header_unpack = _struct.Struct(
            header_type.rec_pack_format_str).unpack
        from ...brec import Subrecord
        Subrecord.sub_header_fmt = u'=4sI'
        Subrecord.sub_header_unpack = _struct.Struct(
            Subrecord.sub_header_fmt).unpack
        Subrecord.sub_header_size = 8
        header_type.top_grup_sigs = [
            b'GMST', b'GLOB', b'CLAS', b'FACT', b'RACE', b'SOUN', b'SKIL',
            b'MGEF', b'SCPT', b'REGN', b'SSCR', b'BSGN', b'LTEX', b'STAT',
            b'DOOR', b'MISC', b'WEAP', b'CONT', b'SPEL', b'CREA', b'BODY',
            b'LIGH', b'ENCH', b'NPC_', b'ARMO', b'CLOT', b'REPA', b'ACTI',
            b'APPA', b'LOCK', b'PROB', b'INGR', b'BOOK', b'ALCH', b'LEVI',
            b'LEVC', b'CELL', b'LAND', b'PGRD', b'SNDG', b'DIAL', b'INFO']
        header_type.valid_header_sigs = set(
            header_type.top_grup_sigs + [b'TES3'])
        brec.MreRecord.type_class = {x.rec_sig: x for x in (
            MreActi, MreAlch, MreAppa, MreArmo, MreBody, MreBook, MreBsgn,
            MreCell, MreClas, MreClot, MreCont, MreCrea, MreDial, MreDoor,
            MreEnch, MreFact, MreGmst, MreGlob, MreInfo, MreIngr, MreLand,
            MreLevc, MreLevi, MreLigh, MreLock, MreLtex, MreMgef, MreMisc,
            MreNpc,  MrePgrd, MreProb, MreRace, MreRegn, MreRepa, MreScpt,
            MreSkil, MreSndg, MreSoun, MreSpel, MreSscr, MreStat, MreTes3,
            MreWeap,
        )}
        brec.MreRecord.simpleTypes = (
            set(brec.MreRecord.type_class) - {b'TES3', b'CELL', b'DIAL'})
        cls._validate_records()

GAME_TYPE = MorrowindGameInfo
