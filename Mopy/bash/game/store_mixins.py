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
"""Module providing mixin classes to set some common defaults for games from
various stores."""
from . import GameInfo, WS_COMMON_FILES
from ..bolt import classproperty

class EGSMixin(GameInfo):
    """Mixin for variants of games that are installed via the Epic Games
    Store."""
    @classproperty
    def unique_display_name(cls):
        return f'{cls.display_name} (EGS)'

class GOGMixin(GameInfo):
    """Mixin for variants of games that are installed via GOG."""
    _gog_game_ids: list[int]

    @classproperty
    def unique_display_name(cls):
        return f'{cls.display_name} (GOG)'

    @classmethod
    def test_game_path(cls, test_path):
        return (super().test_game_path(test_path) and
                any(test_path.join(f).is_file()
                    for f in cls.get_unique_filenames(cls._gog_game_ids)))

    @classproperty
    def game_detect_excludes(cls):
        return super().game_detect_excludes - set(cls.get_unique_filenames(
            cls._gog_game_ids))

    @classproperty
    def gog_registry_keys(cls):
        return [(fr'GOG.com\Games\{gog_id}', 'path')
                for gog_id in cls._gog_game_ids]

    @staticmethod
    def get_unique_filenames(gog_game_ids):
        """Get a list of filenames that uniquely identify a GOG-bought game
        based on the specified game's GOG game IDs."""
        return [f'goggame-{gog_id}.ico' for gog_id in gog_game_ids]

class SteamMixin(GameInfo):
    """Mixin for variants of games that are installed via Steam."""
    @classproperty
    def unique_display_name(cls):
        return f'{cls.display_name} (Steam)'

class WindowsStoreMixin(GameInfo):
    """Mixin for variants of games that are installed via the Windows Store."""
    @classproperty
    def unique_display_name(cls):
        return f'{cls.display_name} (WS)'

    @classproperty
    def game_detect_includes(cls):
        return super().game_detect_includes | WS_COMMON_FILES

    @classproperty
    def game_detect_excludes(cls):
        return super().game_detect_excludes - WS_COMMON_FILES

    # Disable any tools that require hooking into the game's executable. Even
    # if the user manually installs these, they will not work, with no workable
    # solution found by the tool devs.
    class Se(GameInfo.Se):
        pass
    class Sd(GameInfo.Sd):
        pass
