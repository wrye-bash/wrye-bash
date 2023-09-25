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
import struct as _struct

from .. import WS_COMMON_FILES, GameInfo
from ..patch_game import PatchGame
from ..store_mixins import GOGMixin, SteamMixin, WindowsStoreMixin
from ... import bolt

_GOG_IDS = [
    1435828767, # Game
    1432185303, # GOG Amazon Prime game
    1440163901, # Package
]

class _AMorrowindGameInfo(PatchGame):
    """GameInfo override for TES III: Morrowind."""
    display_name = 'Morrowind'
    fsName = u'Morrowind'
    altName = u'Wrye Mash'
    game_icon = u'morrowind_%u.png'
    bash_root_prefix = u'Morrowind'
    bak_game_name = u'Morrowind'
    uses_personal_folders = False
    appdata_name = u'Morrowind'
    launch_exe = u'Morrowind.exe'
    game_detect_includes = {'Morrowind.exe'}
    game_detect_excludes = (set(GOGMixin.get_unique_filenames(_GOG_IDS)) |
                            WS_COMMON_FILES)
    version_detect_file = u'Morrowind.exe'
    master_file = bolt.FName(u'Morrowind.esm')
    mods_dir = u'Data Files'
    taglist_dir = u'Morrowind'
    loot_dir = u'Morrowind'
    loot_game_name = 'Morrowind'
    nexusUrl = u'https://www.nexusmods.com/morrowind/'
    nexusName = u'Morrowind Nexus'
    nexusKey = u'bash.installers.openMorrowindNexus.continue'

    using_txt_file = False
    plugin_name_specific_dirs = [] # Morrowind seems to have no such dirs

    allTags = set() # no BP functionality yet

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
        redate_dict = bolt.DefaultFNDict(lambda: 1054674000, { # '2003-06-04'
            'Morrowind.bsa': 1020200400, # '2002-05-01'
            'Tribunal.bsa': 1036533600,  # '2002-11-06'
            'Bloodmoon.bsa': 1054587600, # '2003-06-03'
        })

    class Xe(GameInfo.Xe):
        full_name = u'TES3Edit'
        xe_key_prefix = u'tes3View'

    class Bain(GameInfo.Bain):
        data_dirs = GameInfo.Bain.data_dirs | {
            'animation', # 3P: Liztail's Animation Kit
            'bookart',
            'distantland', # 3P: MGE XE
            'fonts',
            'icons',
            'mwse', # 3P: MWSE
            'shaders',
            'splash',
        }
        # 'Mash' is not used by us, but kept here so we don't clean out Wrye
        # Mash table files
        keep_data_dirs = {'mash'}
        skip_bain_refresh = {
            u'tes3edit backups',
            u'tes3edit cache',
        }

    class Esp(GameInfo.Esp):
        check_master_sizes = True
        max_author_length = 32 # Does not have to have a null terminator
        max_desc_length = 256 # Does not have to have a null terminator
        max_lvl_list_size = 2 ** 32 - 1
        plugin_header_sig = b'TES3'
        stringsFiles = []
        validHeaderVersions = (1.2, 1.3)

    bethDataFiles = {
        'bloodmoon.bsa',
        'bloodmoon.esm',
        'morrowind.bsa',
        'morrowind.esm',
        'tribunal.bsa',
        'tribunal.esm',
    }

    top_groups = [
        b'GMST', b'GLOB', b'CLAS', b'FACT', b'RACE', b'SOUN', b'SKIL', b'MGEF',
        b'SCPT', b'REGN', b'SSCR', b'BSGN', b'LTEX', b'STAT', b'DOOR', b'MISC',
        b'WEAP', b'CONT', b'SPEL', b'CREA', b'BODY', b'LIGH', b'ENCH', b'NPC_',
        b'ARMO', b'CLOT', b'REPA', b'ACTI', b'APPA', b'LOCK', b'PROB', b'INGR',
        b'BOOK', b'ALCH', b'LEVI', b'LEVC', b'CELL', b'LAND', b'PGRD', b'SNDG',
        b'DIAL', b'INFO',
    ]

    @classmethod
    def init(cls, _package_name=None):
        super().init(_package_name or __name__)
        # Setting RecordHeader class variables - Morrowind is special
        from ... import brec as _brec_
        header_type = _brec_.RecordHeader
        header_type.rec_header_size = 16
        header_type.rec_pack_format_str = '=4sIII'
        header_type.header_unpack = bolt.structs_cache['=4sIII'].unpack
        sub = _brec_.Subrecord
        sub.sub_header_fmt = '=4sI'
        sub.sub_header_unpack = _struct.Struct(sub.sub_header_fmt).unpack
        sub.sub_header_size = 8
        cls._import_records(__name__)

class GOGMorrowindGameInfo(GOGMixin, _AMorrowindGameInfo):
    """GameInfo override for the GOG version of Morrowind."""
    _gog_game_ids = _GOG_IDS
    # Morrowind does not use the personal folders, so no my_games_name etc.

class SteamMorrowindGameInfo(SteamMixin, _AMorrowindGameInfo):
    """GameInfo override for the Steam version of Morrowind."""
    class St(_AMorrowindGameInfo.St):
        steam_ids = [22320]

class WSMorrowindGameInfo(WindowsStoreMixin, _AMorrowindGameInfo):
    """GameInfo override for the Windows Store version of Morrowind."""
    # Morrowind does not use the personal folders, so no my_games_name etc.

    class Ws(_AMorrowindGameInfo.Ws):
        legacy_publisher_name = 'Bethesda'
        win_store_name = 'BethesdaSoftworks.TESMorrowind-PC'
        ws_language_dirs = ['Morrowind GOTY English',
                            'Morrowind GOTY French',
                            'Morrowind GOTY German']

GAME_TYPE = {g.unique_display_name: g for g in (
    GOGMorrowindGameInfo, SteamMorrowindGameInfo, WSMorrowindGameInfo)}
