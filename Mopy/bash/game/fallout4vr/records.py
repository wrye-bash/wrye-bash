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
"""This module contains only the overrides of record classes needed for
FO4VR."""

from ...brec import MreHeaderBase, MelSet, MelStruct, MelBase, MelArray, MelFid

# Only difference from FO4 is the default version, but this seems less hacky
# than adding a game var just for this and dynamically importing it in FO4
class MreTes4(MreHeaderBase):
    """TES4 Record. File header."""
    rec_sig = b'TES4'

    melSet = MelSet(
        MelStruct(b'HEDR', [u'f', u'2I'], (u'version', 0.95), u'numRecords',
                  (u'nextObject', 0x800)),
        MelBase(b'TNAM', u'tnam_p'),
        MreHeaderBase.MelAuthor(),
        MreHeaderBase.MelDescription(),
        MreHeaderBase.MelMasterNames(),
        MelSimpleArray('overrides', MelFid(b'ONAM')),
        MelBase(b'SCRN', u'screenshot'),
        MelBase(b'INTV', u'unknownINTV'),
        MelBase(b'INCC', u'unknownINCC'),
    )
    __slots__ = melSet.getSlotsUsed()
