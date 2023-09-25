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
default_tweaks = {
    'Invalidate, Allow loose files [Starfield].ini': {
        'Archive': {'bInvalidateOlderFiles': '1',
                    'sResourceDataDirsFinal': ''}},
    'Invalidate, Disallow loose files ~Default [Starfield].ini': {
        'Archive': {'bInvalidateOlderFiles': '0',
                    'sResourceDataDirsFinal': 'STRINGS\\'}},
}
