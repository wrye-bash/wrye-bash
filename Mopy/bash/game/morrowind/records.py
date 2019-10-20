# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module contains the Morrowind record classes. Also contains records
and subrecords used for the saves - see MorrowindSaveHeader for more
information."""
from ... import bolt
from ...bolt import cstrip, decode
from ...brec import MelBase, MelGroup, MelSet, MelString, MelStruct, \
    MelArray, MreHeaderBase, MelUnion, SaveDecider, MelNull, MelSequential

# Utilities
def _decode_raw(target_str):
    """Adapted from MelUnicode.loadData. ##: maybe move to bolt/brec?"""
    return u'\n'.join(
        decode(x, avoidEncodings=(u'utf8', u'utf-8')) for x
        in cstrip(target_str).split(b'\n'))

class MelSavesOnly(MelSequential):
    """Record element that only loads contents if the input file is a save
    file."""
    def __init__(self, *elements):
        super(MelSavesOnly, self).__init__(*(MelUnion({
            True: element,
            False: MelNull(b'ANY')
        }, decider=SaveDecider()) for element in elements))

class MelMWId(MelString):
    """Wraps MelString to define a common NAME handler."""
    def __init__(self):
        MelString.__init__(self, b'NAME', u'mw_id')

# Shared (plugins + saves) record classes
class MreTes3(MreHeaderBase):
    """TES3 Record. File header."""
    classType = b'TES3'

    class MelTes3Hedr(MelStruct):
        """Wrapper around MelStruct to handle the author and description
        fields, which are padded to 32 and 256 bytes, respectively, with null
        bytes."""
        def loadData(self, record, ins, sub_type, size_, readId):
            super(MreTes3.MelTes3Hedr, self).loadData(record, ins, sub_type,
                                                      size_, readId)
            # Strip off the null bytes and convert to unicode
            record.author = _decode_raw(record.author)
            record.description = _decode_raw(record.description)

        def dumpData(self, record, out):
            # Store the original values in case we dump more than once
            orig_author = record.author
            orig_desc = record.description
            # Encode and enforce limits, then dump out
            record.author = bolt.encode_complex_string(
                record.author, max_size=32, min_size=32)
            record.description = bolt.encode_complex_string(
                record.description, max_size=256, min_size=256)
            super(MreTes3.MelTes3Hedr, self).dumpData(record, out)
            # Restore the original values again, see comment above
            record.author = orig_author
            record.description = orig_desc

    melSet = MelSet(
        MelTes3Hedr(b'HEDR', u'fI32s256sI', (u'version', 1.3), u'esp_flags',
                    u'author', u'description', u'numRecords'),
        MreHeaderBase.MelMasterNames(),
        MelSavesOnly(
            # Wrye Mash calls unknown1 'day', but that seems incorrect?
            MelStruct(b'GMDT', u'6f64sf32s', u'pc_curr_health',
                      u'pc_max_health', u'unknown1', u'unknown2', u'unknown3',
                      u'unknown4', u'curr_cell', u'unknown5', u'pc_name'),
            MelBase(b'SCRD', u'unknown_scrd'), # likely screenshot-related
            MelArray(u'screenshot_data',
                # Yes, the correct order is bgra
                MelStruct(b'SCRS', u'4B', u'blue', u'green', u'red', u'alpha'),
            ),
        ),
    )
    __slots__ = melSet.getSlotsUsed()
