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
from ..skyrim import ASkyrimGameInfo
from ..store_mixins import SteamMixin

class AEnderalGameInfo(ASkyrimGameInfo):
    """GameInfo override for Enderal."""
    display_name = 'Enderal'
    fsName = u'Enderal'
    game_icon = u'enderal_%u.png'
    bash_root_prefix = u'Enderal'
    bak_game_name = u'Enderal'
    my_games_name = u'Enderal'
    appdata_name = u'Enderal'
    # Enderal SE also has an Enderal Launcher.exe, but no TESV.exe. Skyrim LE
    # has TESV.exe, but no Enderal Launcher.exe
    game_detect_includes = {'Enderal Launcher.exe', 'TESV.exe'}
    # This isn't exact (currently 1.5.0 when it should be 1.5.7), but it's the
    # closest we're going to get
    version_detect_file = u'Enderal Launcher.exe'
    taglist_dir = u'Enderal'
    loot_dir = u'Enderal'
    loot_game_name = 'Enderal'
    boss_game_name = u'' # BOSS does not support Enderal
    nexusUrl = u'https://www.nexusmods.com/enderal/'
    nexusName = u'Enderal Nexus'
    nexusKey = u'bash.installers.openEnderalNexus.continue'

    class Ini(ASkyrimGameInfo.Ini):
        default_ini_file = u'enderal_default.ini'
        dropdown_inis = [u'Enderal.ini', u'EnderalPrefs.ini']
        save_prefix = u'..\\Enderal\\Saves'

    class Xe(ASkyrimGameInfo.Xe):
        full_name = u'EnderalEdit'
        xe_key_prefix = u'enderalView'

    class Bain(ASkyrimGameInfo.Bain):
        skip_bain_refresh = {u'enderaledit backups', u'enderaledit cache'}

    raceNames = {
        0x13741 : _(u'Half Kilénian'),
        0x13742 : _(u'Half Aeterna'),
        0x13743 : _(u'Half Aeterna'),
        0x13746 : _(u'Half Arazealean'),
        0x13748 : _(u'Half Qyranian'),
    }
    raceShortNames = {
        0x13741 : u'Kil',
        0x13742 : u'Aet',
        0x13743 : u'Aet',
        0x13746 : u'Ara',
        0x13748 : u'Qyr',
    }
    # TODO(inf) Not updated yet - seem to only be needed for Oblivion-specific
    #  save code
    raceHairMale = {
        0x13741 : 0x90475, #--Kil
        0x13742 : 0x64214, #--Aet
        0x13743 : 0x7b792, #--Aet
        0x13746 : 0x1da82, #--Ara
        0x13748 : 0x64215, #--Qyr
    }
    raceHairFemale = {
        0x13741 : 0x1da83, #--Kil
        0x13742 : 0x1da83, #--Aet
        0x13743 : 0x690c2, #--Aet
        0x13746 : 0x1da83, #--Ara
        0x13748 : 0x64210, #--Qyr
    }

    bethDataFiles = {
        'e - meshes.bsa',
        'e - music.bsa',
        'e - scripts.bsa',
        'e - sounds.bsa',
        'e - textures1.bsa',
        'e - textures2.bsa',
        'e - textures3.bsa',
        'enderal - forgotten stories.esm',
        'l - textures.bsa',
        'l - voices.bsa',
        'skyrim - animations.bsa',
        'skyrim - interface.bsa',
        'skyrim - meshes.bsa',
        'skyrim - misc.bsa',
        'skyrim - shaders.bsa',
        'skyrim - sounds.bsa',
        'skyrim - textures.bsa',
        'skyrim.esm',
        'update.bsa',
        'update.esm',
    }

    nirnroots = _(u'Vynroots')

    names_tweaks = ((ASkyrimGameInfo.names_tweaks |
                    {'NamesTweak_RenamePennies'}) -
                    {'NamesTweak_RenameGold'})

    @classmethod
    def init(cls, _package_name=None):
        super().init(_package_name or __name__)

class SteamEnderalGameInfo(SteamMixin, AEnderalGameInfo):
    """GameInfo override for the Steam version of Enderal."""
    class St(AEnderalGameInfo.St):
        steam_ids = [933480]

GAME_TYPE = SteamEnderalGameInfo
