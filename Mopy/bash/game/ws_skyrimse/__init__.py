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
"""GameInfo override for the Windows Store version of Skyrim SE."""

from ..skyrimse import SkyrimSEGameInfo
from ..windows_store_game import WindowsStoreMixin

class WSSkyrimSEGameInfo(WindowsStoreMixin, SkyrimSEGameInfo):
    displayName = 'Skyrim Special Edition (WS)'
    my_games_name = 'Skyrim Special Edition MS'
    appdata_name = 'Skyrim Special Edition MS'

    class Ws(SkyrimSEGameInfo.Ws):
        legacy_publisher_name = 'Bethesda'
        win_store_name = 'BethesdaSoftworks.SkyrimSE-PC'

GAME_TYPE = WSSkyrimSEGameInfo
