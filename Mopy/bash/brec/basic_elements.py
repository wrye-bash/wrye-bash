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
"""Houses basic building blocks for creating record definitions. Somewhat
higher-level building blocks can be found in common_subrecords.py."""
from __future__ import annotations

from itertools import repeat
from typing import BinaryIO

from . import utils_constants
from .utils_constants import FID, ZERO_FID, FixedString, get_structs, \
    int_unpacker, null1, GetAttrer, SlottedType, FormId
from .. import bolt, exception, bush
from ..bolt import Rounder, attrgetter_cache, decoder, encode, sig_to_str, \
    struct_calcsize, struct_error, structs_cache, PluginStr, ChardetStr

#------------------------------------------------------------------------------
class _MelObjectType(SlottedType):
    """Metaclass responsible for adding comparison attributes to its
    instances. It will filter out attributes whose names start by '_',
    'unknown' or 'unused'."""

    def __new__(cls, name, bases, classdict, *,
                __ignored=('_', 'unknown', 'unused')):
        new = super(_MelObjectType, cls).__new__(cls, name, bases, classdict)
        comp_attrs = classdict.get('compare_attrs') or new.__slots__
        # ignore unknown/unused attributes in MelObject comparisons
        comp_attrs = (c for c in comp_attrs if not c.startswith(__ignored))
        if acts := classdict.get('compare_actions'): # iterated separately
            comp_attrs = (c for c in comp_attrs if c not in acts)
        new.compare_attrs = frozenset(comp_attrs)
        return new

class MelObject(GetAttrer, metaclass=_MelObjectType):
    """An empty class used by group and structure elements for data storage.
    Compares equal based on a set of compare_attrs class variable."""

    def __eq__(self, other):
        """Operator: =="""
        try:
            comp_att = type(self).compare_attrs
            return type(other).compare_attrs == comp_att and all(
                getattr(self, a) == getattr(other, a) for a in comp_att)
        except AttributeError:
            return False

    def __ne__(self, other):
        """Operator: !="""
        return not (self == other)

    def __hash__(self):
        raise TypeError(f'unhashable type: {type(self)}')

    def __bool__(self):
        """The code used to check if hasattr(record, mel_obj_attr) - since
        the MelObject instance will be created in GetAttrer.__getattr__,
        hasattr will return True. This is a hacky way to check if the MelObject
        instance is an empty instance just created."""
        # fixme check also the mel_providers_dict?
        bolt.deprint(f'__bool__ called on {self!r}')
        for a in self.__class__.melSet.defaulters:
            if getattr(self, a) is not None:
                return True
        for a in self.__class__.melSet.listers:
            if getattr(self, a): # != []
                return True
        return False

    def __repr__(self):
        """Carefully try to show as much info about ourselves as possible."""
        to_show = [f'{obj_attr}: {obj_val!r}' for obj_attr in self.__slots__ if
                   (obj_val := getattr(self, obj_attr)) is not None]
        return f'<{", ".join(to_show)}>'

class AttrsCompare(MelObject):
    """MelObject that applies an action before comparing (like str.lower())."""
    compare_actions = {} # attrs --> functions applied to them before comparing

    def __eq__(self, other):
        """Operator: =="""
        try:
            return super().__eq__(other) and all(
                act(getattr(self, a)) == act(getattr(other, a)) for a, act in
                type(self).compare_actions.items())
        except AttributeError:
            return False

class Subrecord(object):
    """A subrecord. Base class defines the subrecord format and packing."""
    # TODO(ut): WIP! mel_sig does not make sense for all subclasses
    # Format used by sub-record headers. Morrowind uses a different one.
    sub_header_fmt = u'=4sH'
    # precompiled unpacker for sub-record headers
    sub_header_unpack = structs_cache[sub_header_fmt].unpack
    # Size of sub-record headers. Morrowind has a different one.
    sub_header_size = 6
    __slots__ = (u'mel_sig',)

    def packSub(self, out: BinaryIO, binary_data: bytes):
        """Write subrecord header and data to output stream."""
        try:
            self._dump_bytes(out, binary_data, len(binary_data))
        except Exception:
            bolt.deprint(f'{self!r}: Failed packing: '
              f'{getattr(self, "mel_sig", "<no mel_sig>")!r}, {binary_data!r}')
            raise

    def _dump_bytes(self, out, binary_data, lenData):
        """Dump binary header and data to `out` bytestream. Will
        automatically add a prefacing XXXX size subrecord to handle data
        with size > 0xFFFF."""
        outWrite = out.write
        if lenData > 0xFFFF:
            MelXXXX(lenData).dumpData(u'record', out)
            lenData = 0
        outWrite(structs_cache[Subrecord.sub_header_fmt].pack(self.mel_sig,
                                                              lenData))
        outWrite(binary_data)

def unpackSubHeader(ins, rsig, *, file_offset=0, __unpacker=int_unpacker,
                    __sr=Subrecord):
    """Unpack a subrecord header."""
    mel_sig, mel_size = ins.unpack(__sr.sub_header_unpack,
                                   __sr.sub_header_size, rsig, u'SUB_HEAD')
    # Extended storage - very rare, so don't optimize inlines etc. for it
    if mel_sig == b'XXXX':
        mel_sizes = []
        ins_unpack = ins.unpack
        pos = (file_offset or ins.tell()) - __sr.sub_header_size
        while mel_sig == b'XXXX': #it does happen to have two of those in a row
            mel_size = ins_unpack(__unpacker, 4, rsig, u'XXXX.SIZE')[0]
            mel_sig = ins_unpack(__sr.sub_header_unpack, __sr.sub_header_size,
                rsig, u'XXXX.TYPE')[0] # Throw away size here (always == 0)
            mel_sizes.append(mel_size)
        if len(mel_sizes) > 1:
            msg = f'{ins.inName}: {len(mel_sizes)} consecutive XXXX subrecords ' \
                  f'reading {sig_to_str(rsig)} starting at file position {pos}'
            if len(set(mel_sizes)) > 1:
                raise exception.ModError(ins.inName,
                    f'{msg} - differing sizes {mel_sizes}!')
            bolt.deprint(msg)
        mel_size = mel_sizes[0]
    return mel_sig, mel_size

class SubrecordBlob(Subrecord):
    """Basic implementation that reads all data without unpacking, adapted to
    current usages."""
    __slots__ = (u'mel_data',)

    def __init__(self, ins, record_sig, mel_sigs=frozenset()):
        # record_sig is the sig of parent record
        mel_sig, mel_size = unpackSubHeader(ins, record_sig)
        self.mel_sig = mel_sig
        if not mel_sigs or mel_sig in mel_sigs:
            self.mel_data = ins.read(mel_size, record_sig, self.mel_sig)
        else:
            self.mel_data = None
            ins.seek(mel_size, 1) # discard the data

    def __repr__(self):
        repr_args = (self.__class__.__name__, self.mel_sig)
        if self.mel_data:
            repr_fmt = u'%s<%s, %u bytes>'
            repr_args += (len(self.mel_data),)
        else:
            repr_fmt = u'%s<%s, skipped>'
        return repr_fmt % repr_args

#------------------------------------------------------------------------------
class MelBase(Subrecord):
    """Represents a mod record element which can be a subrecord, a field or a
    collection thereof. Instances of this class are actually parasitic
    organisms that need a record to go live. They do not hold any data
    themselves, they instead use the load_mel API to set host record
    attributes (from an input stream) and dumpData to dump those attributes
    (to an output stream). This is still WIP, as in separating de/serialization
    and record update business logic."""
    __slots__ = ('attr', 'set_default')

    def __init__(self, mel_sig: bytes, attr: str, *, set_default=None):
        """Passing a value for set_default will result in the MelBase
        instance dumping record.attr even if not loaded. Use sparingly!"""
        self.mel_sig, self.attr, self.set_default = mel_sig, attr, set_default

    def getSlotsUsed(self):
        return self.attr,

    def getDefaulters(self, mel_set_instance):
        # type: (MelSet) -> None
        """Register self as a default/mel_object provider.
        :param mel_set_instance: the record's/MelObject melSet whose structures
            we populate."""
        try:
            defaultrs = mel_set_instance.defaulters
            if self.attr in defaultrs and self.set_default != defaultrs[self.attr]:
                raise SyntaxError(f'{self} duplicate attr {self.attr}')
            defaultrs[self.attr] = self.set_default
        except AttributeError:
            """Mel does not have a self.attr attribute so we won't be needing a
            default value for it."""
            print(type(self)) # MelNull

    def getLoaders(self,loaders):
        """Adds self as loader for type."""
        loaders[self.mel_sig] = self

    def hasFids(self,formElements):
        """Include self if has fids."""
        pass

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        """Read the actual data (not the headers) from ins into record
        attribute."""
        setattr(record, self.attr, self.load_bytes(ins, size_, *debug_strs))

    def load_bytes(self, ins, size_, *debug_strs):
        """Deserialize a chunk of the binary data of given size_ - by
        default reads it in as is. Subclasses should deserialize to appropriate
        types."""
        return ins.read(size_, *debug_strs)

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        value = self.pack_subrecord_data(record)
        if value is not None: self.packSub(out, value)

    def pack_subrecord_data(self, record):
        """Get the mod element data stored in record and pack them to a bytes
        string ready to write to an output stream. In some cases another type
        is returned that must be packed by caller (see MelString). Return None
        to skip dumping. It may modify the record before dumping.

        :rtype: bytes | None"""
        return getattr(record, self.attr) # this better be bytes here

    def mapFids(self, record, function, save_fids=False):
        """Applies function to fids. If save_fids is True, then fid is set
        to result of function - see ReplaceFormIDsPatcher."""
        raise NotImplementedError(
            f'mapFids called on subrecord without FormIDs (signatures: '
            f'{sorted(self.signatures)})')

    def needs_sorting(self):
        """Returns True if this subrecord even needs sorting in the first
        place."""
        return False

    def sort_subrecord(self, record):
        """Sorts this subrecord. Does nothing by default, override if you need
        to sort."""

    @property
    def signatures(self) -> set[bytes]:
        """Returns a set containing all the signatures (aka mel_sigs) that
        could belong to this element. For most elements, this is just a single
        one, but groups and unions return multiple here."""
        return {self.mel_sig}

    @property
    def static_size(self) -> int:
        """Returns an integer denoting the number of bytes this element is
        going to take. Raises an AbstractError if the element can't know this
        (e.g. MelBase or MelNull)."""
        raise NotImplementedError

# -----------------------------------------------------------------------------
class MelBaseR(MelBase):
    """A required subrecord whose contents are unknown/unused/unimportant.
    Often used for markers, which the game engine uses when parsing to keep
    track of where it is."""

    def __init__(self, mel_sig: bytes, attr: str, *, set_default=b''):
        super().__init__(mel_sig, attr, set_default=set_default)

# Simple static Fields --------------------------------------------------------
class MelNum(MelBase):
    """A simple static subrecord representing a number. Note attr defaults to
    '_unused' for usage in MelSimpleArray and similar tools where the attribute
    name does not matter. For everything else, you absolutely have to specify
    an attribute name."""
    _unpacker, packer, static_size = get_structs(u'I')
    __slots__ = ()

    def __init__(self, mel_sig, attr='_unused', *, set_default=None):
        super().__init__(mel_sig, attr, set_default=set_default)

    def load_bytes(self, ins, size_, *debug_strs):
        return ins.unpack(self._unpacker, size_, *debug_strs)[0]

    def pack_subrecord_data(self, record):
        """Will only be dumped if set by load_mel."""
        num = getattr(record, self.attr)
        return None if num is None else self.packer(num)

#------------------------------------------------------------------------------
class MelNull(MelBase):
    """Represents an obsolete record. Reads bytes from instream, but then
    discards them and is otherwise inactive."""

    def __init__(self, mel_sig):
        self.mel_sig = mel_sig

    def getSlotsUsed(self):
        return ()

    def getDefaulters(self, mel_set_instance):
        pass

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        ins.seek(size_, 1, *debug_strs)

    def dumpData(self,record,out):
        pass

#------------------------------------------------------------------------------
class MelSequential(MelBase):
    """Represents a sequential, which is simply a way for one record element to
    delegate loading to multiple other record elements. It basically behaves
    like MelGroup, but does not assign to an attribute."""
    def __init__(self, *elements):
        # Filter out None, produced by static deciders like fnv_only
        self.elements = [e for e in elements if e is not None]
        self.form_elements = set()
        self._sort_elements = []
        self._possible_sigs = {s for element in self.elements for s
                               in element.signatures}
        self._sub_loaders = {}

    def getDefaulters(self, mel_set_instance):
        for element in self.elements:
            element.getDefaulters(mel_set_instance)

    def getLoaders(self, loaders):
        # We need a copy of the loaders in case we're used in a distributor
        for element in self.elements:
            element.getLoaders(self._sub_loaders)
        loaders.update(self._sub_loaders)

    def getSlotsUsed(self):
        slots_ret = set()
        for element in self.elements:
            slots_ret.update(element.getSlotsUsed())
        return tuple(slots_ret)

    def hasFids(self, formElements):
        for element in self.elements:
            element.hasFids(self.form_elements)
        if self.form_elements: formElements.add(self)

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        # This will only ever be called if we're used in a distributor, regular
        # MelSet will just bypass us entirely. So just redirect to the right
        # sub-loader that we found in getLoaders
        self._sub_loaders[sub_type].load_mel(record, ins, sub_type, size_,
                                             *debug_strs)

    def dumpData(self, record, out):
        for element in self.elements:
            element.dumpData(record, out)

    def mapFids(self, record, function, save_fids=False):
        for element in self.form_elements:
            element.mapFids(record, function, save_fids)

    def needs_sorting(self):
        for element in self.elements:
            if element.needs_sorting():
                self._sort_elements.append(element)
        return bool(self._sort_elements)

    def sort_subrecord(self, record):
        for element in self._sort_elements:
            element.sort_subrecord(record)

    @property
    def signatures(self):
        return self._possible_sigs

    @property
    def static_size(self):
        return sum([element.static_size for element in self.elements])

#------------------------------------------------------------------------------
class MelReadOnly(MelSequential):
    """A MelSequential that never writes out. Useful for obsolete elements that
    will be replaced by newer ones when dumping."""
    def dumpData(self, record, out): pass

#------------------------------------------------------------------------------
class MelGroup(MelSequential):
    """Represents a group of mod elements - complication is it calls its
    load/dump methods on a custom MelObject that needs to be set as
    default."""
    _mel_object_base_type = MelObject

    def __init__(self, attr: str, *elements):
        super(MelGroup, self).__init__(*elements)
        self.attr, self.loaders = attr, {}
        # set up the MelObject needed for this MelGroup
        from .record_structs import MelSet
        class _MelObject(self.__class__._mel_object_base_type):
            melSet = MelSet(*elements)
        self._mel_object_type = _MelObject

    def getDefaulters(self, mel_set_instance, mel_key=''):
        """In addition to parent method, populate the mel_providers_dict
        :param mel_key: the key to the (possibly nested) mel_object factory
            (may contain dots)."""
        mel_object_type = self._mel_object_type
        if not mel_key:
            mel_set_instance.mel_providers_dict[self.attr] = mel_object_type
            self.getDefaulters(mel_set_instance, self.attr)
        else: # we are a MelGroups nested inside a MelGroup inform parent Group
            for k, v in mel_object_type.melSet.mel_providers_dict.items():
                mel_set_instance.mel_providers_dict[f'{mel_key}.{k}'] = v

    def getLoaders(self,loaders):
        super(MelGroup, self).getLoaders(self.loaders)
        for loader_type in self.loaders:
            loaders[loader_type] = self

    def getSlotsUsed(self):
        return self.attr,

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        self.loaders[sub_type].load_mel(getattr(record, self.attr), ins,
                                        sub_type, size_, *debug_strs)

    def dumpData(self,record,out):
        if target := getattr(record, self.attr):
            super().dumpData(target, out) # call getattr on target

    def mapFids(self, record, function, save_fids=False):
        target = getattr(record, self.attr)
        if not target: return
        super(MelGroup, self).mapFids(target, function, save_fids)

    def sort_subrecord(self, record):
        target = getattr(record, self.attr)
        if not target: return ##: todo drop - avoid checking a MelObject truth value
        super().sort_subrecord(target)

#------------------------------------------------------------------------------
class MelGroups(MelGroup):
    """Represents an array of group record."""

    def __init__(self, attr: str, *elements):
        """Initialize. Must have at least one element."""
        super().__init__(attr, *elements)
        self._init_sigs = self.elements[0].signatures

    def getDefaulters(self, mel_set_instance, mel_key=''):
        mel_set_instance.listers.add(self.attr)
        att = f'{mel_key}.{self.attr}' if mel_key else self.attr
        super().getDefaulters(mel_set_instance, att)
        mel_set_instance.mel_providers_dict[att] = self._mel_object_type

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        if sub_type in self._init_sigs:
            # We've hit one of the initial signatures, make a new object
            target = self._new_object(record)
        else:
            # Add to the existing element
            target = getattr(record, self.attr)[-1]
        self.loaders[sub_type].load_mel(target, ins, sub_type, size_, *debug_strs)

    def _new_object(self, record):
        """Creates a new MelObject and appends it to this MelGroups' attribute.
        """
        target = self._mel_object_type()
        getattr(record, self.attr).append(target)
        return target

    def dumpData(self,record,out):
        elements = self.elements
        for target in getattr(record, self.attr):
            for element in elements:
                element.dumpData(target,out)

    def mapFids(self, record, function, save_fids=False):
        formElements = self.form_elements
        for target in getattr(record, self.attr):
            for element in formElements:
                element.mapFids(target, function, save_fids)

    def sort_subrecord(self, record):
        elements = self.elements
        for target in getattr(record, self.attr):
            for element in elements:
                element.sort_subrecord(target)

    @property
    def static_size(self):
        raise NotImplementedError

#------------------------------------------------------------------------------
class MelUnorderedGroups(MelGroups):
    """A version of MelGroups that does not use the usual 'initial sigs'
    mechanism. Instead any element in the group can start a new object if it's
    already been encountered while loading the current object. As an example,
    consider these two subrecord definitions:

        MelGroups('subs',
            MelUInt32(b'SUB1', 'sub1'),
            MelFloat(b'SUB2', 'sub2'),
        )

        MelUnorderedGroups('subs',
            MelUInt32(b'SUB1', 'sub1'),
            MelFloat(b'SUB2', 'sub2'),
        )

    Along with this series of subrecords (where the '()' notation is supposed
    to denote that the subrecord contains that data):

        SUB1(1), SUB2(1.0), SUB2(2.0), SUB1(2), SUB1(3)

    The result would look like this for the MelGroups one:

        <subs: [<sub1: 1, sub2: 2.0>, <sub1: 2, sub2: 0.0>,
                <sub1: 3, sub2: 0.0>]>

    But it would look like this for the MelUnorderedGroups one:

        <subs: [<sub1: 1, sub2: 1.0>, <sub1: 2, sub2: 2.0>,
                <sub1: 3, sub2: 0.0>]>

    With MelGroups, the second SUB2 overwrote the first one. With
    MelUnorderedGroups, the second SUB2 started a new object instead."""
    def getSlotsUsed(self):
        return '_found_sigs', *super().getSlotsUsed()

    def getDefaulters(self, mel_set_instance, mel_key=''):
        super().getDefaulters(mel_set_instance, mel_key)
        mel_set_instance.defaulters['_found_sigs'] = None

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        if not record._found_sigs or sub_type in record._found_sigs:
            # We just started loading or we hit this signature before. Either
            # way, we need an object and we need to reset the found signatures
            # to contain only this one
            target = self._new_object(record)
            record._found_sigs = {sub_type}
        else:
            # We haven't hit this signature yet, so add to the existing object
            target = getattr(record, self.attr)[-1]
            record._found_sigs.add(sub_type)
        self.loaders[sub_type].load_mel(target, ins, sub_type, size_,
            *debug_strs)

#------------------------------------------------------------------------------
class MelSimpleGroups(MelGroups):
    """A MelGroups of simple elements (currently MelNum) - override loading and
    dumping of the groups to avoid creating MelObjects."""
    def __init__(self, groups_attr, element: MelNum):
        if not isinstance(element, MelNum):
            raise SyntaxError(f'MelSimpleGroups only accepts MelNum, passed: '
                              f'{element!r}')
        self.mel_sig = element.mel_sig
        self._element = element
        super().__init__(groups_attr, element)

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        getattr(record, self.attr).append(self._element.load_bytes(
            ins, size_, *debug_strs))

    def mapFids(self, record, function, save_fids=False):
        if self.form_elements:
            groups_val = getattr(record, self.attr)
            mapped = [function(group_entry) for group_entry in groups_val]
            if save_fids:
                setattr(record, self.attr, mapped)

    def dumpData(self, record, out):
        pack_el = self._element.packer
        for target in getattr(record, self.attr):
            self.packSub(out, pack_el(target))

#------------------------------------------------------------------------------
class MelString(MelBase):
    """Represents a mod record string element. Will use bolt.pluginEncoding."""
    encoding: str | None = None # None -> default to bolt.pluginEncoding
    _wrapper_bytes_type = PluginStr

    ##: minSize seems unused
    def __init__(self, mel_sig: bytes, attr: str, *,
            maxSize: int | None = None, minSize: int | None = None,
            set_default=None):
        super().__init__(mel_sig, attr, set_default=set_default)
        self.maxSize = maxSize
        self.minSize = minSize

    def load_bytes(self, ins, size_, *debug_strs):
        return self._wrapper_bytes_type(ins.read(size_, *debug_strs))

    def packSub(self, out: BinaryIO, string_val: PluginStr,
                force_encoding=None):
        """Write out a string subrecord, properly encoding it beforehand and
        respecting maxSize, minSize and encoding if they are set."""
        byte_string = string_val.reencode(
            force_encoding or bolt.pluginEncoding, self.maxSize,self.minSize)
        # Null terminator is accounted for in _dump_bytes
        super().packSub(out, byte_string)

    def _dump_bytes(self, out, byte_string, lenData):
        # Add the null terminator to the encoded string
        super()._dump_bytes(out, byte_string + null1, lenData + 1)

#------------------------------------------------------------------------------
class MelUnicode(MelString):
    """Like MelString, but instead of using bolt.pluginEncoding to read the
       string, it tries the encoding specified in the constructor instead or
       falls back to chardet. **Only** use for MreHeaderBase author and
       description fields."""
    _wrapper_bytes_type = ChardetStr

    def __init__(self, mel_sig: bytes, attr: str, maxSize=None, *,
            encoding=None, set_default=None):
        super().__init__(mel_sig, attr, maxSize=maxSize,
            set_default=set_default)
        if encoding is not None: # None == automatic detection via ChardetStr
            class _PluginStr(PluginStr): # fixme cache?
                _preferred_encoding = encoding
            self._wrapper_bytes_type = _PluginStr

#------------------------------------------------------------------------------
class MelLString(MelString):
    """Represents a mod record localized string."""

    def load_bytes(self, ins, size_, *debug_strs):
        return ins.readLString(size_, *debug_strs)

#------------------------------------------------------------------------------
class MelStrings(MelString):
    """Represents array of strings."""

    def getDefaulters(self, mel_set_instance):
        mel_set_instance.listers.add(self.attr)

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        """>>>b'b\0a\0'.rstrip(b'\0').split(b'\0')
           ['b', 'a']"""
        value = [self._wrapper_bytes_type(x) for x in
                 ins.read(size_, *debug_strs).rstrip(null1).split(null1)]
        setattr(record, self.attr, value)

    def packSub(self, out, strings, force_encoding=None):
        """Writes out a strings array subrecord, encoding and adding a null
        terminator to each string separately."""
        if not strings:
            # Don't dump out a pointless terminator when we have zero strings
            return
        str_data = null1.join(
            x.reencode(force_encoding or bolt.pluginEncoding, self.maxSize) for
            x in strings)
        if not str_data:
            # Similarly, don't dump out a pointless terminator just because the
            # plugin we read it from had a pointless terminator
            return
        # MelStrings need an extra null separator or Oblivion will CTD. This
        # adds the null separator for the last string, then we...
        str_data += null1
        # ...call Subrecord.packSub which will call MelString._dump_bytes to
        # add the last null separator
        super(MelString, self).packSub(out, str_data)

#------------------------------------------------------------------------------
class MelStruct(MelBase):
    """Represents a structure record."""

    def __init__(self, mel_sig: bytes, struct_formats: list[str], *elements,
                 is_required=None):
        """Parse elements and set attrs, defaults, actions, formAttrs where:
        * attrs is tuple of attributes (names)
        * formAttrs is set of attributes that have fids,
        * defaults is tuple of default values for attributes
        * actions is tuple of callables to be used when loading data
        Note that each element of defaults and actions matches corresponding
        attr element. Example elements:
        ('level', 'unused1', (FID, 'listId', None), ('count', 1), 'unused2')
        """
        if not isinstance(struct_formats, list):
            raise SyntaxError(f'Expected a list got "{struct_formats}"')
        self._is_required = is_required
        # Sometimes subrecords have to preserve non-aligned sizes, check that
        # we don't accidentally pad those to alignment
        struct_format = u''.join(struct_formats)
        if (struct_calcsize(struct_format) != struct_calcsize(
                u'=' + struct_format)):
            struct_format = f'={struct_format}'
        self.mel_sig = mel_sig
        self.attrs, self.defaults, self.actions, self.formAttrs = \
            self._parseElements(struct_formats, *elements)
        # Check for duplicate attrs - can't rely on MelSet.getSlotsUsed only,
        # since we may end up in a MelUnion which has to use a set to collect
        # its slots
        present_attrs = set()
        for a in self.attrs:
            if a in present_attrs:
                raise SyntaxError(
                    f"Duplicate attribute '{a}' in struct definition")
            present_attrs.add(a)
        self._unpacker, self._packer, self._static_size, = get_structs(
            struct_format)

    def getSlotsUsed(self):
        return self.attrs

    def hasFids(self,formElements):
        if self.formAttrs: formElements.add(self)

    def set_mel_struct_defaults(self, mel_obj):
        """Only used in get_mel_object_for_group - don't use."""
        for att, val in zip(self.attrs, self.defaults):
            setattr(mel_obj, att, val)
        for dex in self._action_dexes:
            act = self.actions[dex]
            if act is not FID: # copy the flags so we won't edit the default
                setattr(mel_obj, self.attrs[dex], act(self.defaults[dex]))

    def getDefaulters(self, mel_set_instance, *, __nones=repeat(None)):
        defaultrs = mel_set_instance.defaulters
        vals = self.defaults if self._is_required else __nones
        if dups := defaultrs.keys() & set(self.attrs):
            dups = set((a, defaultrs[a], dflt) for a, dflt in zip(
                self.attrs, vals) if a in dups and defaultrs[a] != dflt)
            if dups:
                raise SyntaxError(f'{self} duplicate attr(s) {dups}')
        for att, value in zip(self.attrs, vals):
            defaultrs[att] = value

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        unpacked = ins.unpack(self._unpacker, size_, *debug_strs)
        for att, val, action in zip(self.attrs, unpacked, self.actions):
            setattr(record, att, action(val) if action is not None else val)

    def pack_subrecord_data(self, record, *, __attrgetters=attrgetter_cache):
        values = [__attrgetters[a](record) for a in self.attrs]
        for dex in self._action_dexes:
            try:
                values[dex] = values[dex].dump()
            except AttributeError:
                if values[dex] is None: # assume all the rest are None
                    return None # don't dump this one, was not loaded
                # Apply the action to itself before dumping to handle
                # e.g. a FixedString getting assigned a unicode value.
                # Needed also when we read a flag say from a csv
                values[dex] = self.actions[dex](values[dex]).dump()
        try:
            return self._packer(*values)
        except struct_error:
            if any(v is None for v in values): # assume all the rest are None
                return
            bolt.deprint(f'Dumping {self} failed - values '
                         f'{dict(zip(self.attrs, values))}', traceback=True)
            raise

    def mapFids(self, record, function, save_fids=False):
        for attr in self.formAttrs:
            result = function(getattr(record, attr))
            if save_fids: setattr(record, attr, result)

    @property
    def static_size(self):
        return self._static_size

    def _parseElements(self, struct_formats, *elements, __zero_fid=ZERO_FID):
        formAttrs = set()
        lenEls = len(elements)
        attrs, deflts, actions = [0] * lenEls, [0] * lenEls, [None] * lenEls
        self._action_dexes = set()
        expanded_fmts = self._expand_formats(elements, struct_formats)
        for index, (element, fmt_str) in enumerate(zip(elements, expanded_fmts)):
            if not isinstance(element,tuple):
                attrs[index] = element
                if type(fmt_str) is int and fmt_str: # 0 for weird subclasses
                    deflts[index] = fmt_str * null1
                elif fmt_str == u'f':
                    actions[index] = Rounder
                    self._action_dexes.add(index)
            else:
                el_0 = element[0]
                attrIndex = el_0 == 0 ##: todo is this ever the case?
                if callable(el_0):
                    if el_0 is FID:
                        formAttrs.add(element[1])
                    actions[index] = el_0
                    attrIndex = 1
                    self._action_dexes.add(index)
                elif fmt_str == u'f':
                    # If el_0 is an action we entered the previous elif, so
                    # this does not overwrite an existing action
                    actions[index] = Rounder
                    self._action_dexes.add(index)
                attrs[index] = element[attrIndex]
                if len(element) - attrIndex == 2:
                    deflts[index] = element[-1] # else leave to 0
                elif type(fmt_str) is int and fmt_str: # 0 for weird subclasses
                    deflts[index] = fmt_str * null1
        for dex in self._action_dexes: # apply the actions to defaults once
            act = actions[dex]
            deflts[dex] = __zero_fid if act is FID else act(deflts[dex])
        return tuple(attrs), tuple(deflts), tuple(actions), formAttrs

    @staticmethod
    def _expand_formats(elements, struct_formats):
        """Expand struct_formats to match the elements - overrides point to
        a new class (MelStructured?)"""
        expanded_fmts = []
        for f in struct_formats:
            if f[-1] != 's':
                expanded_fmts.extend([f[-1]] * int(f[:-1] or 1))
            else:
                expanded_fmts.append(int(f[:-1] or 1))
        if len(expanded_fmts) != len(elements):
            raise SyntaxError(f'Format specifiers ({expanded_fmts}) do not '
                              f'match elements ({elements})')
        return expanded_fmts

#------------------------------------------------------------------------------
class MelFixedString(MelStruct):
    """Subrecord that stores a string of a constant length. Just a wrapper
    around a struct with a single FixedString element.""" ##: MelAction really
    def __init__(self, mel_sig, attr, str_length, *, set_default=None):
        el = (FixedString(str_length, set_default or ''), attr)
        super().__init__(mel_sig, [f'{str_length:d}s'], el)

# Simple primitive type wrappers ----------------------------------------------
class MelFloat(MelNum):
    """Float."""
    _unpacker, packer, static_size = get_structs(u'=f')

    def load_bytes(self, ins, size_, *debug_strs): ##: note we dont round on dump
        return Rounder(super().load_bytes(ins, size_, *debug_strs))

class MelSInt8(MelNum):
    """Signed 8-bit integer."""
    _unpacker, packer, static_size = get_structs(u'=b')

class MelSInt16(MelNum):
    """Signed 16-bit integer."""
    _unpacker, packer, static_size = get_structs(u'=h')

class MelSInt32(MelNum):
    """Signed 32-bit integer."""
    _unpacker, packer, static_size = get_structs(u'=i')

    def pack_subrecord_data(self, record):
        """Will only be dumped if set by load_mel."""
        attr = getattr(record, self.attr)
        try:
            return None if attr is None else self.packer(attr)
        except struct_error: ##: TODO HACK: fix the records code
            return self.packer(int(attr))

class MelUInt8(MelNum):
    """Unsigned 8-bit integer."""
    _unpacker, packer, static_size = get_structs(u'=B')

class MelUInt16(MelNum):
    """Unsigned 16-bit integer."""
    _unpacker, packer, static_size = get_structs(u'=H')

class MelUInt32(MelNum):
    """Unsigned 32-bit integer."""
    _unpacker, packer, static_size = get_structs(u'=I')

class _MelFlags(MelNum):
    """Integer flag field."""
    __slots__ = ('_flag_type',)

    def __init__(self, mel_sig, attr, flags_type, *, set_default=None):
        self._flag_type = flags_type
        dflt = None if set_default is None else flags_type(set_default)
        super().__init__(mel_sig, attr, set_default=dflt)

    def load_bytes(self, ins, size_, *debug_strs):
        return self._flag_type(
            ins.unpack(self._unpacker, size_, *debug_strs)[0])

    def packer(self, flag_val): # override class variable, access parent's
        return super(_MelFlags, self.__class__).packer(flag_val.dump())

class MelUInt8Flags(MelUInt8, _MelFlags): pass
class MelUInt16Flags(MelUInt16, _MelFlags): pass
class MelUInt32Flags(MelUInt32, _MelFlags): pass

class _MelBool(MelNum):
    """Boolean field."""
    __slots__ = ()

    def __init__(self, mel_sig, attr, *, set_default=None):
        super().__init__(mel_sig, attr, set_default=set_default)

    def load_bytes(self, ins, size_, *debug_strs):
        # Treat 0 as false, every other value as true...
        return super().load_bytes(ins, size_, *debug_strs) != 0

    def packer(self, bool_val: bool):
        # ...but only put out 0 and 1
        return super(_MelBool, self.__class__).packer(1 if bool_val else 0)

class MelUInt8Bool(MelUInt8, _MelBool): pass
class MelUInt16Bool(MelUInt16, _MelBool): pass
class MelUInt32Bool(MelUInt32, _MelBool): pass

#------------------------------------------------------------------------------
class MelXXXX(MelUInt32):
    """Represents an XXXX size field. Ignores record in load/dump"""

    def __init__(self, int_size):
        self.int_size = int_size
        self.mel_sig = b'XXXX'

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        self.int_size = self.load_bytes(ins, size_, *debug_strs)

    def pack_subrecord_data(self, record):
        return self.packer(self.int_size)

#------------------------------------------------------------------------------
class MelFid(MelUInt32):
    """Represents a mod record fid element."""
    def load_bytes(self, ins, size_, *debug_strs):
        return FID(super().load_bytes(ins, size_, *debug_strs))

    def packer(self, form_id):
        return super(MelFid, self.__class__).packer(
            utils_constants.short_mapper(form_id))

    def hasFids(self,formElements):
        formElements.add(self)

    def mapFids(self, record, function, save_fids=False):
        result = function(getattr(record, self.attr, None))
        if save_fids: setattr(record, self.attr, result)

#------------------------------------------------------------------------------
class MelPostMast(MelBase):
    """Elements that come after the masters in MreTes4/3 and are responsible
    for setting FORM_ID."""

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        if utils_constants.FORM_ID is None:
            in_overlay_plugin = bush.game.has_overlay_plugins and \
                                record.flags1.overlay_flag
            utils_constants.FORM_ID = FormId.from_masters(
                (*record.masters, ins.inName), in_overlay_plugin)
        super().load_mel(record, ins, sub_type, size_, *debug_strs)

class MelPostMastS(MelPostMast, MelStruct): pass
class MelPostMastI(MelPostMast, MelUInt32): pass
