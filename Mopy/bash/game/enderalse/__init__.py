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
from ..gog_game import GOGMixin
from ..enderal import EnderalGameInfo
from ..skyrimse import SkyrimSEGameInfo

# We want the final chain of attribute lookups to be Enderal SE -> Enderal LE
# -> Skyrim SE -> Skyrim LE -> Defaults, i.e. the narrower overrides first
class EnderalSEGameInfo(EnderalGameInfo, SkyrimSEGameInfo):
    """GameInfo override for Enderal Special Edition."""
    displayName = u'Enderal Special Edition'
    fsName = u'Enderal Special Edition'
    game_icon = u'enderalse_%u.png'
    bash_root_prefix = u'EnderalSE'
    bak_game_name = u'Enderal Special Edition'
    my_games_name = u'Enderal Special Edition'
    appdata_name = u'Enderal Special Edition'
    # Enderal LE also has an Enderal Launcher.exe, but no SkyrimSE.exe. Skyrim
    # SE has SkyrimSE.exe, but no Enderal Launcher.exe
    game_detect_includes = {'Enderal Launcher.exe', 'SkyrimSE.exe'}
    loot_dir = u'Enderal Special Edition'
    loot_game_name = 'Enderal Special Edition'
    # This is in HKCU. There's also one in HKLM that uses 'SureAI\Enderal SE'
    # for some reason
    registry_keys = [(r'SureAI\EnderalSE', 'Install_Path')]
    nexusUrl = u'https://www.nexusmods.com/enderalspecialedition/'
    nexusName = u'Enderal Special Edition Nexus'
    nexusKey = u'bash.installers.openEnderalSENexus.continue'

    class Ini(EnderalGameInfo.Ini, SkyrimSEGameInfo.Ini):
        save_prefix = u'..\\Enderal Special Edition\\Saves'

    class Xe(EnderalGameInfo.Xe, SkyrimSEGameInfo.Xe):
        full_name = u'EnderalSEEdit'
        xe_key_prefix = u'enderalSEView'

    class Bain(EnderalGameInfo.Bain, SkyrimSEGameInfo.Bain):
        skip_bain_refresh = {u'enderalseedit backups', u'enderalseedit cache'}

    bethDataFiles = {
        'dawnguard.esm',
        'dragonborn.esm',
        'e - meshes.bsa',
        'e - scripts.bsa',
        'e - se.bsa',
        'e - sounds.bsa',
        'e - textures1.bsa',
        'e - textures2.bsa',
        'e - textures3.bsa',
        'enderal - forgotten stories.esm',
        'hearthfires.esm',
        'l - textures.bsa',
        'l - voices.bsa',
        'skyrim - animations.bsa',
        'skyrim - interface.bsa',
        'skyrim - meshes0.bsa',
        'skyrim - meshes1.bsa',
        'skyrim - misc.bsa',
        'skyrim - patch.bsa',
        'skyrim - shaders.bsa',
        'skyrim - sounds.bsa',
        'skyrim - textures0.bsa',
        'skyrim - textures1.bsa',
        'skyrim - textures2.bsa',
        'skyrim - textures3.bsa',
        'skyrim - textures4.bsa',
        'skyrim - textures5.bsa',
        'skyrim - textures6.bsa',
        'skyrim - textures7.bsa',
        'skyrim - textures8.bsa',
        'skyrim.esm',
        'skyui_se.bsa',
        'skyui_se.esp',
        'update.esm',
    }

    names_tweaks = (SkyrimSEGameInfo.names_tweaks |
                    {'NamesTweak_RenamePennies'} -
                    {'NamesTweak_RenameGold'})

    @classmethod
    def init(cls, _package_name=None):
        super().init(_package_name or __name__)

class GOGEnderalSEGameInfo(GOGMixin, EnderalSEGameInfo):
    """GameInfo override for the GOG version of Enderal Special Edition."""
    displayName = 'Enderal Special Edition (GOG)'
    my_games_name = 'Enderal Special Edition GOG'
    appdata_name = 'Enderal Special Edition GOG'
    registry_keys = [(r'GOG.com\Games\1708684988', 'path')]

    class Ini(EnderalSEGameInfo.Ini):
        save_prefix = '..\\Enderal Special Edition GOG\\Saves'

GAME_TYPE = {g.displayName: g for g in
             (EnderalSEGameInfo, GOGEnderalSEGameInfo)}
