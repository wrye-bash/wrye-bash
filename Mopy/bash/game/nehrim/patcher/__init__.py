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

"""This package contains the Nehrim specific patchers. This module
contains the data structures that are dynamically set on a per game basis in
bush."""
from ...oblivion.patcher import *

# Only Import Roads is of any interest
gameSpecificPatchers = {}
gameSpecificListPatchers = {}

#------------------------------------------------------------------------------
# NPC Checker
#------------------------------------------------------------------------------
# Note that we use _x to avoid exposing these to the dynamic importer
def _fid(_x): return None, _x # None <=> game master
_standard_eyes = [_fid(_x) for _x in (0x27306, 0x27308, 0x27309)]
default_eyes = {
    _fid(0x224FC): _standard_eyes, # Alemanne
    _fid(0x18D9E5): [_fid(_x) for _x in (
        0x47EF, 0x18D9D9, 0x18D9DA, 0x18D9DB, 0x18D9DC, 0x18D9DD, 0x18D9DE,
        0x18D9DF, 0x18D9E0, 0x18D9E1, 0x18D9E2)], # Half-Aeterna
    _fid(0x224FD): _standard_eyes, # Normanne
}
# Clean this up, no need to keep it around now
del _fid

#------------------------------------------------------------------------------
# Tweak Actors
#------------------------------------------------------------------------------
actor_tweaks = {
    u'VanillaNPCSkeletonPatcher',
    u'NoBloodCreaturesPatcher',
    u'QuietFeetPatcher',
    u'IrresponsibleCreaturesPatcher',
}
