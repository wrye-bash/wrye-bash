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
"""GameInfo override for the Windows Store version of Oblivion."""

from ..oblivion import OblivionGameInfo
from ..windows_store_game import WindowsStoreMixin

class WSOblivionGameInfo(WindowsStoreMixin, OblivionGameInfo):
    displayName = 'Oblivion (WS)'
    # `appdata_name` and `my_games_name` use the original locations, unlike
    # newer Windows Store games.
    check_legacy_paths = False

    class Ws(OblivionGameInfo.Ws):
        publisher_name = 'Bethesda'
        win_store_name = 'BethesdaSoftworks.TESOblivion-PC'
        game_language_dirs = ['Oblivion GOTY English',
                              'Oblivion GOTY French',
                              'Oblivion GOTY German',
                              'Oblivion GOTY Italian',
                              'Oblivion GOTY Spanish']

GAME_TYPE = WSOblivionGameInfo
