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
from ..oblivion import AOblivionGameInfo
from ..store_mixins import GOGMixin, SteamMixin
from ...bolt import DefaultFNDict, FName

_GOG_IDS = [1497007810]

class _ANehrimGameInfo(AOblivionGameInfo):
    """GameInfo override for Nehrim: At Fate's Edge."""
    display_name = 'Nehrim'
    game_icon = u'nehrim_%u.png'
    bash_root_prefix = u'Nehrim'
    bak_game_name = u'Nehrim'
    game_detect_includes = {'NehrimLauncher.exe'}
    game_detect_excludes = set(GOGMixin.get_unique_filenames(_GOG_IDS))
    master_file = FName('Nehrim.esm')
    loot_dir = u'Nehrim'
    loot_game_name = 'Nehrim'
    boss_game_name = u'Nehrim'
    nexusUrl = u'https://www.nexusmods.com/nehrim/'
    nexusName = u'Nehrim Nexus'
    nexusKey = u'bash.installers.openNehrimNexus.continue'
    check_legacy_paths = False

    class Bsa(AOblivionGameInfo.Bsa):
        redate_dict = DefaultFNDict(lambda: 1136066400, { # '2006-01-01'
            u'N - Textures1.bsa': 1104530400, # '2005-01-01'
            u'N - Textures2.bsa': 1104616800, # '2005-01-02'
            u'L - Voices.bsa': 1104703200,    # '2005-01-03'
            u'N - Meshes.bsa': 1104789600,    # '2005-01-04'
            u'N - Sounds.bsa': 1104876000,    # '2005-01-05'
            u'L - Misc.bsa': 1104962400,      # '2005-01-06'
            u'N - Misc.bsa': 1105048800,      # '2005-01-07'
        })

    # Oblivion minus Oblivion-specific patchers (Cobl Catalogs, Cobl
    # Exhaustion, Morph Factions and SEWorld Tests)
    patchers = {p for p in AOblivionGameInfo.patchers if p not in
                ('CoblCatalogs', 'CoblExhaustion', 'MorphFactions',
                 'SEWorldTests')}

    raceNames = {
        0x224fc:  _(u'Alemanne'),
        0x18d9e5: _(u'Half-Aeterna'),
        0x224fd:  _(u'Normanne'),
    }
    raceShortNames = {
        0x224fc:  u'Ale',
        0x18d9e5: u'Aet',
        0x224fd:  u'Nor',
    }
    raceHairMale = {
        0x224fc:  0x90475, #--Ale
        0x18d9e5: 0x5c6b,  #--Aet
        0x224fd:  0x1da82, #--Nor
    }
    raceHairFemale = {
        0x224fc:  0x1da83, #--Ale
        0x18d9e5: 0x3e1e,  #--Aet
        0x224fd:  0x1da83, #--Nor
    }

    bethDataFiles = {
        'l - misc.bsa',
        'l - voices.bsa',
        'n - meshes.bsa',
        'n - misc.bsa',
        'n - sounds.bsa',
        'n - textures1.bsa',
        'n - textures2.bsa',
        'nehrim.esm',
        'translation.esp',
    }

    nirnroots = _(u'Vynroots')

    #--------------------------------------------------------------------------
    # NPC Checker
    #--------------------------------------------------------------------------
    _standard_eyes = [(None, x) for x in # None <=> game master
                      (0x27306, 0x27308, 0x27309)]
    default_eyes = {
        (None, 0x224FC): _standard_eyes, # Alemanne
        (None, 0x18D9E5): [(None, x) for x in  (
            0x47EF, 0x18D9D9, 0x18D9DA, 0x18D9DB, 0x18D9DC, 0x18D9DD, 0x18D9DE,
            0x18D9DF, 0x18D9E0, 0x18D9E1, 0x18D9E2)], # Half-Aeterna
        (None, 0x224FD): _standard_eyes, # Normanne
    }

    #--------------------------------------------------------------------------
    # Tweak Actors
    #--------------------------------------------------------------------------
    actor_tweaks = {
        'VanillaNPCSkeletonPatcher',
        'NoBloodCreaturesPatcher',
        'QuietFeetPatcher',
        'IrresponsibleCreaturesPatcher',
    }

    @classmethod
    def _dynamic_import_modules(cls, package_name):
        # bypass setting the patchers in super class
        super(AOblivionGameInfo, cls)._dynamic_import_modules(package_name)
        # Only Import Roads is of any interest
        from ..oblivion.patcher import preservers
        cls.game_specific_import_patchers = {
            'ImportRoads': preservers.ImportRoadsPatcher,
        }

    @classmethod
    def init(cls, _package_name=None):
        super().init(_package_name or __name__)

class GOGNehrimGameInfo(GOGMixin, _ANehrimGameInfo):
    """GameInfo override for the GOG version of Nehrim."""
    _gog_game_ids = _GOG_IDS

class SteamNehrimGameInfo(SteamMixin, _ANehrimGameInfo):
    """GameInfo override for the Steam version of Nehrim."""
    class St(_ANehrimGameInfo.St):
        steam_ids = [1014940]

GAME_TYPE = {g.unique_display_name: g for g in (
    GOGNehrimGameInfo, SteamNehrimGameInfo)}
