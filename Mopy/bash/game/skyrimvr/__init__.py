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
"""GameInfo override for TES V: Skyrim VR."""
from ..skyrimse import ASkyrimSEGameInfo
from ..store_mixins import SteamMixin

class _ASkyrimVRGameInfo(ASkyrimSEGameInfo):
    display_name = 'Skyrim VR'
    fsName = u'Skyrim VR'
    altName = u'Wrye VRash'
    game_icon = u'skyrimvr_%u.png'
    bash_root_prefix = u'Skyrim VR' # backwards compat :(
    bak_game_name = u'Skyrim VR'
    my_games_name = u'Skyrim VR'
    appdata_name = u'Skyrim VR'
    launch_exe = u'SkyrimVR.exe'
    game_detect_includes = {'SkyrimVR.exe'}
    game_detect_excludes = set()
    version_detect_file = u'SkyrimVR.exe'
    taglist_dir = 'SkyrimVR'
    loot_dir = u'Skyrim VR'
    loot_game_name = 'Skyrim VR'

    espm_extensions = ASkyrimSEGameInfo.espm_extensions - {'.esl'}
    check_esl = False

    class Se(ASkyrimSEGameInfo.Se):
        se_abbrev = u'SKSEVR'
        long_name = u'Skyrim VR Script Extender'
        exe = u'sksevr_loader.exe'
        ver_files = [u'sksevr_loader.exe', u'sksevr_steam_loader.dll']

    class Ini(ASkyrimSEGameInfo.Ini):
        default_ini_file = u'Skyrim.ini' # yes, that's the default one
        dropdown_inis = [u'SkyrimVR.ini', u'SkyrimPrefs.ini']
        resource_override_key = u'sVrResourceArchiveList'
        resource_override_defaults = [u'Skyrim_VR - Main.bsa']

    class Xe(ASkyrimSEGameInfo.Xe):
        full_name = u'TES5VREdit'
        xe_key_prefix = u'tes5vrview'

    class Bain(ASkyrimSEGameInfo.Bain):
        skip_bain_refresh = {u'tes5vredit backups', u'tes5vredit cache'}

    allTags = ASkyrimSEGameInfo.allTags | {'NoMerge'}
    patchers = ASkyrimSEGameInfo.patchers | {'MergePatches'}

    bethDataFiles = ASkyrimSEGameInfo.bethDataFiles | {
        'skyrimvr.esm',
        'skyrim_vr - main.bsa',
    }

    @classmethod
    def init(cls, _package_name=None):
        super().init(_package_name or __name__)

class SteamSkyrimVRGameInfo(SteamMixin, _ASkyrimVRGameInfo):
    """GameInfo override for the Steam version of Skyrim VR."""
    class St(_ASkyrimVRGameInfo.St):
        steam_ids = [611670]

GAME_TYPE = SteamSkyrimVRGameInfo
