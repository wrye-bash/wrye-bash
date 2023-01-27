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

from ...bolt import flag
from ...brec import AMreHeader, MelBase, MelFid, MelGroups, MelNull, MelSet, \
    MelSimpleArray, MelStruct, MelUInt32

# Only difference from FO4 is the default version, but this seems less hacky
# than adding a game var just for this and dynamically importing it in FO4
class MreTes4(AMreHeader):
    """TES4 Record. File header."""
    rec_sig = b'TES4'
    _post_masters_sigs = {b'ONAM', b'SCRN', b'TNAM', b'INTV', b'INCC'}

    class HeaderFlags(AMreHeader.HeaderFlags):
        localized: bool = flag(7)
        esl_flag: bool = flag(9)

    melSet = MelSet(
        MelStruct(b'HEDR', [u'f', u'2I'], (u'version', 0.95), u'numRecords',
                  (u'nextObject', 0x800)),
        MelNull(b'OFST'), # obsolete
        MelNull(b'DELE'), # obsolete
        AMreHeader.MelAuthor(),
        AMreHeader.MelDescription(),
        AMreHeader.MelMasterNames(),
        MelSimpleArray('overrides', MelFid(b'ONAM')),
        MelBase(b'SCRN', 'screenshot'),
        MelGroups('transient_types',
            MelSimpleArray('unknownTNAM', MelFid(b'TNAM'),
                prelude=MelUInt32(b'TNAM', 'form_type')),
        ),
        MelUInt32(b'INTV', 'unknownINTV'),
        MelUInt32(b'INCC', 'internal_cell_count'),
    )
