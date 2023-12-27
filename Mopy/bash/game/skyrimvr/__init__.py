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
"""GameInfo override for TES V: Skyrim VR."""
from .. import MergeabilityCheck, ObjectIndexRange
from ..skyrimse import ASkyrimSEGameInfo
from ..store_mixins import SteamMixin
from ... import bass
from ...bolt import FName, classproperty

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
    mergeability_checks = {MergeabilityCheck.MERGE}

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

    class Esp(ASkyrimSEGameInfo.Esp):
        # All these will be restored again if the appropriate SKSE plugin is
        # installed, see init() below
        master_limit = 255
        object_index_range = ObjectIndexRange.RESERVED
        object_index_range_expansion_ver = 0.0
        validHeaderVersions = (0.94, 1.70)

    bethDataFiles = ASkyrimSEGameInfo.bethDataFiles | {
        'skyrimvr.esm',
        'skyrim_vr - main.bsa',
    }

    class SkyrimVR(ASkyrimSEGameInfo.SkyrimSE):
        must_be_active_if_present = (
            *ASkyrimSEGameInfo.SkyrimSE.must_be_active_if_present,
            FName('SkyrimVR.esm'))
        ##: This is nasty, figure out a way to get rid of it
        @classproperty
        def max_espms(cls):
            from ... import bush
            return 253 if bush.game.has_esl else 255

        @classproperty
        def max_esls(cls):
            from ... import bush
            return 4096 if bush.game.has_esl else 0
    lo_handler = SkyrimVR

    @classmethod
    def init(cls, _package_name=None):
        super().init(_package_name or __name__)

    @classmethod
    def post_init(cls):
        from ... import env
        esl_plugin_path = env.to_os_path(bass.dirs['mods'].join(
                cls.Se.plugin_dir, 'plugins', 'skyrimvresl.dll'))
        if esl_plugin_path and esl_plugin_path.is_file():
            # ESL-support plugin installed, enable ESL support in WB
            cls.espm_extensions |= {'.esl'}
            cls.mergeability_checks = {MergeabilityCheck.ESL_CHECK}
            cls.Esp.master_limit = 253
            cls.Esp.object_index_range = ObjectIndexRange.RESERVED
            cls.Esp.object_index_range_expansion_ver = 0.0
            cls.Esp.validHeaderVersions = (0.94, 1.70, 1.71)

class SteamSkyrimVRGameInfo(SteamMixin, _ASkyrimVRGameInfo):
    """GameInfo override for the Steam version of Skyrim VR."""
    class St(_ASkyrimVRGameInfo.St):
        steam_ids = [611670]

GAME_TYPE = SteamSkyrimVRGameInfo
