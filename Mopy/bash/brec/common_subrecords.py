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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Builds on the basic elements defined in base_elements.py to provide
definitions for some commonly needed subrecords."""

from __future__ import division, print_function
import struct
from itertools import product

from .advanced_elements import AttrValDecider, MelArray, MelTruncatedStruct, \
    MelUnion
from .basic_elements import MelBase, MelFid, MelGroup, MelGroups, MelLString, \
    MelNull, MelSequential, MelString, MelStruct, MelUInt32
from .utils_constants import _int_unpacker, null1, null3, null4
from .. import bolt
from ..bolt import encode, struct_pack

#------------------------------------------------------------------------------
def mel_cdta_unpackers(sizes_list, pad=u'I'): ##: see if MelUnion can't do this better
    """Return compiled structure objects for each combination of size and
    condition value (?).

    :rtype: dict[unicode, struct.Struct]"""
    sizes_list = sorted(sizes_list)
    _formats = {u'11': u'II', u'10': u'Ii', u'01': u'iI', u'00': u'ii'}
    _formats = {u'%s%d' % (k, s): u'%s%s' % (
        f, u''.join([pad] * ((s - sizes_list[0]) // 4))) for (k, f), s in
                product(_formats.items(), sizes_list)}
    _formats = {k: struct.Struct(v) for (k, v) in _formats.items()}
    return _formats

#------------------------------------------------------------------------------
class MelBounds(MelGroup):
    """Wrapper around MelGroup for the common task of defining OBND - Object
    Bounds. Uses MelGroup to avoid merging them when importing."""
    def __init__(self):
        MelGroup.__init__(self, 'bounds',
            MelStruct('OBND', '=6h', 'boundX1', 'boundY1', 'boundZ1',
                      'boundX2', 'boundY2', 'boundZ2')
        )

#------------------------------------------------------------------------------
class MelReferences(MelGroups):
    """Handles mixed sets of SCRO and SCRV for scripts, quests, etc."""
    def __init__(self):
        MelGroups.__init__(self, 'references', MelUnion({
            'SCRO': MelFid('SCRO', 'reference'),
            'SCRV': MelUInt32('SCRV', 'reference'),
        }))

#------------------------------------------------------------------------------
class MelCoordinates(MelTruncatedStruct):
    """Skip dump if we're in an interior."""
    def dumpData(self, record, out):
        if not record.flags.isInterior:
            MelTruncatedStruct.dumpData(self, record, out)

#------------------------------------------------------------------------------
class MelColorInterpolator(MelArray):
    """Wrapper around MelArray that defines a time interpolator - an array
    of five floats, where each entry in the array describes a point on a curve,
    with 'time' as the X axis and 'red', 'green', 'blue' and 'alpha' as the Y
    axis."""
    def __init__(self, sub_type, attr):
        MelArray.__init__(self, attr,
            MelStruct(sub_type, '5f', 'time', 'red', 'green', 'blue', 'alpha'),
        )

#------------------------------------------------------------------------------
# xEdit calls this 'time interpolator', but that name doesn't really make sense
# Both this class and the color interpolator above interpolate over time
class MelValueInterpolator(MelArray):
    """Wrapper around MelArray that defines a value interpolator - an array
    of two floats, where each entry in the array describes a point on a curve,
    with 'time' as the X axis and 'value' as the Y axis."""
    def __init__(self, sub_type, attr):
        MelArray.__init__(self, attr,
            MelStruct(sub_type, '2f', 'time', 'value'),
        )

#------------------------------------------------------------------------------
class MelEdid(MelString):
    """Handles an Editor ID (EDID) subrecord."""
    def __init__(self):
        MelString.__init__(self, 'EDID', 'eid')

#------------------------------------------------------------------------------
class MelFull(MelLString):
    """Handles a name (FULL) subrecord."""
    def __init__(self):
        MelLString.__init__(self, 'FULL', 'full')

#------------------------------------------------------------------------------
class MelIcons(MelSequential):
    """Handles icon subrecords. Defaults to ICON and MICO, with attribute names
    'iconPath' and 'smallIconPath', since that's most common."""
    def __init__(self, icon_attr='iconPath', mico_attr='smallIconPath',
                 icon_sig='ICON', mico_sig='MICO'):
        """Creates a new MelIcons with the specified attributes.

        :param icon_attr: The attribute to use for the ICON subrecord. If
            falsy, this means 'do not include an ICON subrecord'.
        :param mico_attr: The attribute to use for the MICO subrecord. If
            falsy, this means 'do not include a MICO subrecord'."""
        final_elements = []
        if icon_attr: final_elements += [MelString(icon_sig, icon_attr)]
        if mico_attr: final_elements += [MelString(mico_sig, mico_attr)]
        MelSequential.__init__(self, *final_elements)

class MelIcons2(MelIcons):
    """Handles ICO2 and MIC2 subrecords. Defaults to attribute names
    'femaleIconPath' and 'femaleSmallIconPath', since that's most common."""
    def __init__(self, ico2_attr='femaleIconPath',
                 mic2_attr='femaleSmallIconPath'):
        MelIcons.__init__(self, icon_attr=ico2_attr, mico_attr=mic2_attr,
                          icon_sig='ICO2', mico_sig='MIC2')

class MelIcon(MelIcons):
    """Handles a standalone ICON subrecord, i.e. without any MICO subrecord."""
    def __init__(self, icon_attr='iconPath'):
        MelIcons.__init__(self, icon_attr=icon_attr, mico_attr='')

class MelIco2(MelIcons2):
    """Handles a standalone ICO2 subrecord, i.e. without any MIC2 subrecord."""
    def __init__(self, ico2_attr):
        MelIcons2.__init__(self, ico2_attr=ico2_attr, mic2_attr='')

#------------------------------------------------------------------------------
class MelWthrColors(MelStruct):
    """Used in WTHR for PNAM and NAM0 for all games but FNV."""
    def __init__(self, wthr_sub_sig):
        MelStruct.__init__(
            self, wthr_sub_sig, '3Bs3Bs3Bs3Bs', 'riseRed', 'riseGreen',
            'riseBlue', ('unused1', null1), 'dayRed', 'dayGreen',
            'dayBlue', ('unused2', null1), 'setRed', 'setGreen', 'setBlue',
            ('unused3', null1), 'nightRed', 'nightGreen', 'nightBlue',
            ('unused4', null1))

#------------------------------------------------------------------------------
# Oblivion and Fallout --------------------------------------------------------
#------------------------------------------------------------------------------
class MelRaceParts(MelNull):
    """Handles a subrecord array, where each subrecord is introduced by an
    INDX subrecord, which determines the meaning of the subrecord. The
    resulting attributes are set directly on the record.
    :type _indx_to_loader: dict[int, MelBase]"""
    def __init__(self, indx_to_attr, group_loaders):
        """Creates a new MelRaceParts element with the specified INDX mapping
        and group loaders.

        :param indx_to_attr: A mapping from the INDX values to the final
            record attributes that will be used for the subsequent
            subrecords.
        :type indx_to_attr: dict[int, str]
        :param group_loaders: A callable that takes the INDX value and
            returns an iterable with one or more MelBase-derived subrecord
            loaders. These will be loaded and dumped directly after each
            INDX."""
        self._last_indx = None # used during loading
        self._indx_to_attr = indx_to_attr
        # Create loaders for use at runtime
        self._indx_to_loader = {
            part_indx: MelGroup(part_attr, *group_loaders(part_indx))
            for part_indx, part_attr in indx_to_attr.iteritems()
        }
        self._possible_sigs = {s for element
                               in self._indx_to_loader.itervalues()
                               for s in element.signatures}

    def getLoaders(self, loaders):
        temp_loaders = {}
        for element in self._indx_to_loader.itervalues():
            element.getLoaders(temp_loaders)
        for signature in temp_loaders.keys():
            loaders[signature] = self

    def getSlotsUsed(self):
        return self._indx_to_attr.values()

    def setDefault(self, record):
        for element in self._indx_to_loader.itervalues():
            element.setDefault(record)

    def loadData(self, record, ins, sub_type, size_, readId,
                 __unpacker=_int_unpacker):
        if sub_type == 'INDX':
            self._last_indx, = ins.unpack(__unpacker, size_, readId)
        else:
            self._indx_to_loader[self._last_indx].loadData(
                record, ins, sub_type, size_, readId)

    def dumpData(self, record, out):
        for part_indx, part_attr in self._indx_to_attr.iteritems():
            if hasattr(record, part_attr): # only dump present parts
                out.packSub('INDX', '=I', part_indx)
                self._indx_to_loader[part_indx].dumpData(record, out)

    @property
    def signatures(self):
        return self._possible_sigs

#------------------------------------------------------------------------------
class MelRaceVoices(MelStruct):
    """Set voices to zero, if equal race fid. If both are zero, then skip
    dumping."""
    def dumpData(self, record, out):
        if record.maleVoice == record.fid: record.maleVoice = 0
        if record.femaleVoice == record.fid: record.femaleVoice = 0
        if (record.maleVoice, record.femaleVoice) != (0, 0):
            MelStruct.dumpData(self, record, out)

#------------------------------------------------------------------------------
class MelScriptVars(MelGroups):
    """Handles SLSD and SCVR combos defining script variables."""
    _var_flags = bolt.Flags(0, bolt.Flags.getNames('is_long_or_short'))

    def __init__(self):
        MelGroups.__init__(self, 'script_vars',
            MelStruct('SLSD', 'I12sB7s', 'var_index',
                      ('unused1', null4 + null4 + null4),
                      (self._var_flags, 'var_flags', 0),
                      ('unused2', null4 + null3)),
            MelString('SCVR', 'var_name'),
        )

#------------------------------------------------------------------------------
# Skyrim and Fallout ----------------------------------------------------------
#------------------------------------------------------------------------------
class MelMODS(MelBase):
    """MODS/MO2S/etc/DMDS subrecord"""
    def hasFids(self,formElements):
        formElements.add(self)

    def setDefault(self,record):
        record.__setattr__(self.attr,None)

    def loadData(self, record, ins, sub_type, size_, readId,
                 __unpacker=_int_unpacker):
        insUnpack = ins.unpack
        insRead32 = ins.readString32
        count, = insUnpack(__unpacker, 4, readId)
        data = []
        dataAppend = data.append
        for x in xrange(count):
            string = insRead32(readId)
            fid = ins.unpackRef()
            index, = insUnpack(__unpacker, 4, readId)
            dataAppend((string,fid,index))
        record.__setattr__(self.attr,data)

    def dumpData(self,record,out):
        data = record.__getattribute__(self.attr)
        if data is not None:
            data = record.__getattribute__(self.attr)
            outData = struct_pack('I', len(data))
            for (string,fid,index) in data:
                outData += struct_pack('I', len(string))
                outData += encode(string)
                outData += struct_pack('=2I', fid, index)
            out.packSub(self.subType,outData)

    def mapFids(self,record,function,save=False):
        attr = self.attr
        data = record.__getattribute__(attr)
        if data is not None:
            data = [(string,function(fid),index) for (string,fid,index) in record.__getattribute__(attr)]
            if save: record.__setattr__(attr,data)

#------------------------------------------------------------------------------
class MelRegnEntrySubrecord(MelUnion):
    """Wrapper around MelUnion to correctly read/write REGN entry data.
    Skips loading and dumping if entryType != entry_type_val.

    entry_type_val meanings:
      - 2: Objects
      - 3: Weather
      - 4: Map
      - 5: Land
      - 6: Grass
      - 7: Sound
      - 8: Imposter (FNV only)"""
    def __init__(self, entry_type_val, element):
        """:type entry_type_val: int"""
        MelUnion.__init__(self, {
            entry_type_val: element,
        }, decider=AttrValDecider('entryType'),
            fallback=MelNull('NULL')) # ignore
