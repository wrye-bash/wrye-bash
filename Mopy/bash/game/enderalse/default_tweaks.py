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
from ..enderal.default_tweaks import default_tweaks

# Add new Enderal SE-specific tweaks
add_tweaks = {
    'Save Game Compression, LZ4 ~Default [Enderal].ini': {
        'SaveGame': {'uiCompression': '2'}},
    'Save Game Compression, zlib [Enderal].ini': {
        'SaveGame': {'uiCompression': '1'}},
    'Save Game Compression, Off [Enderal].ini': {
        'SaveGame': {'uiCompression': '0'}},
}
default_tweaks.update(add_tweaks)
