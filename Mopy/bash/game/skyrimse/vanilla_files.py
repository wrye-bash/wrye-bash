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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module lists the files installed in the Data folder in a completely
vanilla Skyrim SE setup."""

# Import vanilla_files from Skyrim, then edit as needed
from ..skyrim.vanilla_files import vanilla_files

# remove removed files
vanilla_files -= {
    'Interface\\Translate_ENGLISH.txt',
    'LSData\\DtC6dal.dat',
    'LSData\\DtC6dl.dat',
    'LSData\\Wt8S9bs.dat',
    'LSData\\Wt8S9fs.dat',
    'LSData\\Wt16M9bs.dat',
    'LSData\\Wt16M9fs.dat',
    'shadersfx\\Lighting\\059\\P800C05.fxp',
    'shadersfx\\Lighting\\059\\V800400.fxp',
    'shadersfx\\Lighting\\059\\V800405.fxp',
    'shadersfx\\Lighting\\059\\VC00401.fxp',
    'Sound\\Voice\\Processing\\FonixData.cdf',
    'Strings\\Dawnguard_English.DLSTRINGS',
    'Strings\\Dawnguard_English.ILSTRINGS',
    'Strings\\Dawnguard_English.STRINGS',
    'Strings\\Dragonborn_English.DLSTRINGS',
    'Strings\\Dragonborn_English.ILSTRINGS',
    'Strings\\Dragonborn_English.STRINGS',
    'Strings\\Hearthfires_English.DLSTRINGS',
    'Strings\\Hearthfires_English.ILSTRINGS',
    'Strings\\Hearthfires_English.STRINGS',
    'Strings\\Skyrim_English.DLSTRINGS',
    'Strings\\Skyrim_English.ILSTRINGS',
    'Strings\\Skyrim_English.STRINGS',
    'Strings\\Update_English.DLSTRINGS',
    'Strings\\Update_English.ILSTRINGS',
    'Strings\\Update_English.STRINGS',
}

# add new ones
vanilla_files |= {
    'Scripts\\Source\\Backup\\QF_C00_0004B2D9_BACKUP_05272016_113428AM.psc',
    'Scripts\\Source\\Backup\\QF_C00JorrvaskrFight_000BC0BD_BACKUP_05272016_113715AM.psc',
}
