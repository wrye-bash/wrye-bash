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
"""GameInfo override for the Epic Games Store version of Skyrim SE."""
from ..skyrimse import SkyrimSEGameInfo
from ...bolt import classproperty

class EGSSkyrimSEGameInfo(SkyrimSEGameInfo):
    displayName = 'Skyrim Special Edition (EGS)'
    my_games_name = 'Skyrim Special Edition EPIC'
    appdata_name = 'Skyrim Special Edition EPIC'

    @classproperty
    def game_detect_includes(cls):
        return super().game_detect_includes | {'EOSSDK-Win64-Shipping.dll'}

    @classproperty
    def game_detect_excludes(cls):
        return super().game_detect_excludes - {'EOSSDK-Win64-Shipping.dll'}

    class Eg(SkyrimSEGameInfo.Eg):
        egs_app_names = ['5d600e4f59974aeba0259c7734134e27', # AE
                         'ac82db5035584c7f8a2c548d98c86b2c'] # SE

GAME_TYPE = EGSSkyrimSEGameInfo
