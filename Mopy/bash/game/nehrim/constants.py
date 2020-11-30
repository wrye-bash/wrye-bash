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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

# Import all constants from Oblivion, then edit them as needed

from ..oblivion.constants import *

bethDataFiles = {
    u'nehrim.esm',
    u'translation.esp',
    u'l - misc.bsa',
    u'l - voices.bsa',
    u'n - meshes.bsa',
    u'n - misc.bsa',
    u'n - sounds.bsa',
    u'n - textures1.bsa',
    u'n - textures2.bsa',
}

#------------------------------------------------------------------------------
# Race Records
#------------------------------------------------------------------------------
# Note that we use _x to avoid exposing these to the dynamic importer
def _neh(_x): return u'Nehrim.esm', _x
_standard_eyes = [_neh(_x) for _x in (0x27306, 0x27308, 0x27309)]
default_eyes = {
    _neh(0x224FC):  _standard_eyes, # Alemanne
    _neh(0x18D9E5): [_neh(_x) for _x in (
        0x47EF, 0x18D9D9, 0x18D9DA, 0x18D9DB, 0x18D9DC, 0x18D9DD, 0x18D9DE,
        0x18D9DF, 0x18D9E0, 0x18D9E1, 0x18D9E2)], # Half-Aeterna
    _neh(0x224FD):  _standard_eyes, # Normanne
}
# Clean these up, no need to keep them around now
del _neh

#------------------------------------------------------------------------------
# Tweak Actors
#------------------------------------------------------------------------------
actor_tweaks = {
    u'VanillaNPCSkeletonPatcher',
    u'NoBloodCreaturesPatcher',
    u'QuietFeetPatcher',
    u'IrresponsibleCreaturesPatcher',
}

#------------------------------------------------------------------------------
# Tweak Assorted
#------------------------------------------------------------------------------
nirnroots = _(u'Vynroots')
