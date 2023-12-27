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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from .. import MergeabilityCheck, ObjectIndexRange
from ..fallout4 import AFallout4GameInfo
from ..store_mixins import SteamMixin
from ... import bolt
from ...bolt import FName

class _AFallout4VRGameInfo(AFallout4GameInfo):
    """GameInfo override for Fallout 4 VR."""
    display_name = 'Fallout 4 VR'
    fsName = u'Fallout4VR'
    game_icon = u'fallout4vr_%u.png'
    altName = u'Wrye VRash'
    bash_root_prefix = u'Fallout4VR'
    bak_game_name = u'Fallout4VR'
    my_games_name = u'Fallout4VR'
    appdata_name = u'Fallout4VR'
    launch_exe = u'Fallout4VR.exe'
    game_detect_includes = {'Fallout4VR.exe'}
    game_detect_excludes = set()
    version_detect_file = u'Fallout4VR.exe'
    master_file = bolt.FName(u'Fallout4.esm')
    taglist_dir = 'Fallout4VR'
    loot_dir = u'Fallout4VR'
    loot_game_name = 'Fallout4VR'

    espm_extensions = AFallout4GameInfo.espm_extensions - {'.esl'}
    mergeability_checks = {MergeabilityCheck.MERGE}

    class Se(AFallout4GameInfo.Se):
        se_abbrev = u'F4SEVR'
        long_name = u'Fallout 4 VR Script Extender'
        exe = u'f4sevr_loader.exe'
        ver_files = [u'f4sevr_loader.exe', u'f4sevr_steam_loader.dll']

    class Ini(AFallout4GameInfo.Ini):
        default_ini_file = u'Fallout4.ini' ##: why not Fallout4_default.ini?
        dropdown_inis = AFallout4GameInfo.Ini.dropdown_inis + [
            u'Fallout4VrCustom.ini'] ##: why is this here?

    class Xe(AFallout4GameInfo.Xe):
        full_name = u'FO4VREdit'
        xe_key_prefix = u'fo4vrView'

    class Bain(AFallout4GameInfo.Bain):
        skip_bain_refresh = {u'fo4vredit backups', u'fo4vredit cache'}

    class Esp(AFallout4GameInfo.Esp):
        object_index_range = ObjectIndexRange.RESERVED
        master_limit = 255
        validHeaderVersions = (0.95,)

    bethDataFiles = AFallout4GameInfo.bethDataFiles | {
        'fallout4 - misc - beta.ba2',
        'fallout4 - misc - debug.ba2',
        'fallout4_vr - main.ba2',
        'fallout4_vr - shaders.ba2',
        'fallout4_vr - textures.ba2',
        'fallout4_vr.esm',
    }

    class Fallout4VR(AFallout4GameInfo.Fallout4):
        must_be_active_if_present = (
            *AFallout4GameInfo.Fallout4.must_be_active_if_present,
            FName('Fallout4_VR.esm'))
        # No ESLs, reset these back to their pre-ESL versions
        _ccc_filename = ''
        max_espms = 255
        max_esls = 0
    lo_handler = Fallout4VR

    @classmethod
    def init(cls, _package_name=None):
        super().init(_package_name or __name__)

class SteamFallout4VRGameInfo(SteamMixin, _AFallout4VRGameInfo):
    """GameInfo override for the Steam version of Fallout 4 VR."""
    class St(_AFallout4VRGameInfo.St):
        steam_ids = [611660]

GAME_TYPE = SteamFallout4VRGameInfo
