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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""GameInfo override for TES V: Skyrim VR."""

from ..skyrimse import SkyrimSEGameInfo

class SkyrimVRGameInfo(SkyrimSEGameInfo):
    displayName = u'Skyrim VR'
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
    registry_keys = [(r'Bethesda Softworks\Skyrim VR', 'Installed Path')]

    espm_extensions = SkyrimSEGameInfo.espm_extensions - {u'.esl'}
    check_esl = False

    class Se(SkyrimSEGameInfo.Se):
        se_abbrev = u'SKSEVR'
        long_name = u'Skyrim VR Script Extender'
        exe = u'sksevr_loader.exe'
        ver_files = [u'sksevr_loader.exe', u'sksevr_steam_loader.dll']

    class Ini(SkyrimSEGameInfo.Ini):
        default_ini_file = u'Skyrim.ini' # yes, that's the default one
        dropdown_inis = [u'SkyrimVR.ini', u'SkyrimPrefs.ini']
        resource_override_key = u'sVrResourceArchiveList'
        resource_override_defaults = [u'Skyrim_VR - Main.bsa']

    class Xe(SkyrimSEGameInfo.Xe):
        full_name = u'TES5VREdit'
        xe_key_prefix = u'tes5vrview'

    class Bain(SkyrimSEGameInfo.Bain):
        skip_bain_refresh = {u'tes5vredit backups', u'tes5vredit cache'}

    allTags = SkyrimSEGameInfo.allTags | {u'NoMerge'}
    patchers = SkyrimSEGameInfo.patchers | {u'MergePatches'}

    bethDataFiles = SkyrimSEGameInfo.bethDataFiles | {
        'skyrimvr.esm',
        'skyrim_vr - main.bsa',
    }

    @classmethod
    def init(cls, _package_name=None):
        super().init(_package_name or __name__)

GAME_TYPE = SkyrimVRGameInfo
