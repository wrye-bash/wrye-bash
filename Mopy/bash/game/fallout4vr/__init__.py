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
from .. import ObjectIndexRange
from ..fallout4 import Fallout4GameInfo
from ... import bolt

class Fallout4VRGameInfo(Fallout4GameInfo):
    """GameInfo override for Fallout 4 VR."""
    displayName = u'Fallout 4 VR'
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
    registry_keys = [(r'Bethesda Softworks\Fallout 4 VR', 'Installed Path')]

    espm_extensions = Fallout4GameInfo.espm_extensions - {u'.esl'}
    check_esl = False

    class Se(Fallout4GameInfo.Se):
        se_abbrev = u'F4SEVR'
        long_name = u'Fallout 4 VR Script Extender'
        exe = u'f4sevr_loader.exe'
        ver_files = [u'f4sevr_loader.exe', u'f4sevr_steam_loader.dll']

    class Ini(Fallout4GameInfo.Ini):
        default_ini_file = u'Fallout4.ini' ##: why not Fallout4_default.ini?
        dropdown_inis = Fallout4GameInfo.Ini.dropdown_inis + [
            u'Fallout4VrCustom.ini'] ##: why is this here?

    class Xe(Fallout4GameInfo.Xe):
        full_name = u'FO4VREdit'
        xe_key_prefix = u'fo4vrView'

    class Bain(Fallout4GameInfo.Bain):
        skip_bain_refresh = {u'fo4vredit backups', u'fo4vredit cache'}

    class Esp(Fallout4GameInfo.Esp):
        object_index_range = ObjectIndexRange.RESERVED
        validHeaderVersions = (0.95,)

    allTags = Fallout4GameInfo.allTags | {'NoMerge'}
    patchers = Fallout4GameInfo.patchers | {'MergePatches'}

    bethDataFiles = Fallout4GameInfo.bethDataFiles | {
        'fallout4 - misc - beta.ba2',
        'fallout4 - misc - debug.ba2',
        'fallout4_vr - main.ba2',
        'fallout4_vr - shaders.ba2',
        'fallout4_vr - textures.ba2',
        'fallout4_vr.esm',
    }

    @classmethod
    def init(cls, _package_name=None):
        super().init(_package_name or __name__)

GAME_TYPE = Fallout4VRGameInfo
