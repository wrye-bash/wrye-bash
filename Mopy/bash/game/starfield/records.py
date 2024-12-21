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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module contains the Starfield record classes."""

from ...bolt import flag
from ...brec import AMreCell, AMreHeader, MelBase, MelFid, MelGroups, \
    MelNull, MelSet, MelSimpleArray, MelStruct, MelUInt32, AMreWrld

#------------------------------------------------------------------------------
# Starfield Records -----------------------------------------------------------
#------------------------------------------------------------------------------
class MreTes4(AMreHeader):
    """TES4 Record. File header."""
    rec_sig = b'TES4'
    _post_masters_sigs = {b'ONAM', b'SCRN', b'TNAM', b'BNAM', b'INTV', b'INCC',
                          b'CHGL'}
    next_object_default = 0x001

    class HeaderFlags(AMreHeader.HeaderFlags):
        optimized_file: bool = flag(4)
        localized: bool = flag(7)
        esl_flag: bool = flag(8)
        overlay_flag: bool = flag(9)
        mid_flag: bool = flag(10)
        blueprint_flag: bool = flag(11)

    melSet = MelSet(
        MelStruct(b'HEDR', ['f', '2I'], ('version', 0.96), 'numRecords',
                  ('nextObject', next_object_default), is_required=True),
        MelNull(b'OFST'), # obsolete
        MelNull(b'DELE'), # obsolete
        AMreHeader.MelAuthor(),
        AMreHeader.MelDescription(),
        AMreHeader.MelMasterNames(has_sizes=False),
        MelSimpleArray('overrides', MelFid(b'ONAM')),
        MelBase(b'SCRN', 'screenshot'),
        MelGroups('transient_types',
            MelSimpleArray('unknownTNAM', MelFid(b'TNAM'),
                prelude=MelUInt32(b'TNAM', 'form_type')),
        ),
        MelBase(b'BNAM', 'unknown_bnam'),
        MelUInt32(b'INTV', 'unknownINTV'),
        MelUInt32(b'INCC', 'interior_cell_count'),
        MelBase(b'CHGL', 'unknown_chgl'), # TODO(SF) fill out once decoded
    )

#------------------------------------------------------------------------------
class MreCell(AMreCell): ##: Implement once regular records are done
    """Cell."""
    ref_types = {b'ACHR', b'PARW', b'PBAR', b'PBEA', b'PCON', b'PFLA', b'PGRE',
                 b'PHZD', b'PMIS', b'REFR'}
    interior_temp_extra = [b'NAVM']

    class HeaderFlags(AMreCell.HeaderFlags):
        no_previs: bool = flag(7)
        partial_form: bool = flag(14)

#------------------------------------------------------------------------------
class MreWrld(AMreWrld): ##: Implement once regular records are done
    """Worldspace."""
    ref_types = MreCell.ref_types
    exterior_temp_extra = [b'LAND', b'NAVM']
    wrld_children_extra = [b'CELL'] # CELL for the persistent block

    class HeaderFlags(AMreWrld.HeaderFlags):
        partial_form: bool = flag(14)
