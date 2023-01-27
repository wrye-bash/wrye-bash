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
"""Module providing a mixin class to set some common defaults for Windows Store
games."""
from . import WS_COMMON_FILES, GameInfo
from ..bolt import classproperty

class WindowsStoreMixin:
    registry_keys = []

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
    class Laa(GameInfo.Laa):
        pass
