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
from ..enderal import AEnderalGameInfo
from ..skyrimse import ASkyrimSEGameInfo
from ..store_mixins import GOGMixin, SteamMixin

_GOG_IDS = [1708684988]

# We want the final chain of attribute lookups to be Enderal SE -> Enderal LE
# -> Skyrim SE -> Skyrim LE -> Defaults, i.e. the narrower overrides first
class _AEnderalSEGameInfo(AEnderalGameInfo, ASkyrimSEGameInfo):
    """GameInfo override for Enderal Special Edition."""
    display_name = 'Enderal Special Edition'
    fsName = u'Enderal Special Edition'
    game_icon = u'enderalse_%u.png'
    bash_root_prefix = u'EnderalSE'
    bak_game_name = u'Enderal Special Edition'
    my_games_name = u'Enderal Special Edition'
    appdata_name = u'Enderal Special Edition'
    # Enderal LE also has an Enderal Launcher.exe, but no SkyrimSE.exe. Skyrim
    # SE has SkyrimSE.exe, but no Enderal Launcher.exe
    game_detect_includes = {'Enderal Launcher.exe', 'SkyrimSE.exe'}
    game_detect_excludes = set(GOGMixin.get_unique_filenames(_GOG_IDS))
    loot_dir = u'Enderal Special Edition'
    loot_game_name = 'Enderal Special Edition'
    nexusUrl = u'https://www.nexusmods.com/enderalspecialedition/'
    nexusName = u'Enderal Special Edition Nexus'
    nexusKey = u'bash.installers.openEnderalSENexus.continue'

    class Ini(AEnderalGameInfo.Ini, ASkyrimSEGameInfo.Ini):
        save_prefix = u'..\\Enderal Special Edition\\Saves'

    class Xe(AEnderalGameInfo.Xe, ASkyrimSEGameInfo.Xe):
        full_name = u'EnderalSEEdit'
        xe_key_prefix = u'enderalSEView'

    class Bain(AEnderalGameInfo.Bain, ASkyrimSEGameInfo.Bain):
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

    # Override like this so that we get the SkyrimSE ammo tweak
    names_tweaks = (ASkyrimSEGameInfo.names_tweaks |
                    {'NamesTweak_RenamePennies'} -
                    {'NamesTweak_RenameGold'})

    @classmethod
    def init(cls, _package_name=None):
        super().init(_package_name or __name__)

class GOGEnderalSEGameInfo(GOGMixin, _AEnderalSEGameInfo):
    """GameInfo override for the GOG version of Enderal Special Edition."""
    my_games_name = 'Enderal Special Edition GOG'
    appdata_name = 'Enderal Special Edition GOG'
    _gog_game_ids = _GOG_IDS

    class Ini(_AEnderalSEGameInfo.Ini):
        save_prefix = '..\\Enderal Special Edition GOG\\Saves'

class SteamEnderalSEGameInfo(SteamMixin, _AEnderalSEGameInfo):
    """GameInfo override for the Steam version of Enderal SE."""
    class St(_AEnderalSEGameInfo.St):
        steam_ids = [976620]

GAME_TYPE = {g.unique_display_name: g for g in (
    GOGEnderalSEGameInfo, SteamEnderalSEGameInfo)}
