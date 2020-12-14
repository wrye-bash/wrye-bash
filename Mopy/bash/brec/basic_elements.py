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
"""Houses basic building blocks for creating record definitions. Somewhat
higher-level building blocks can be found in common_subrecords.py."""

from __future__ import division, print_function
from collections import Counter
from itertools import chain

from .utils_constants import FID, null1, _make_hashable, FixedString, \
    _int_unpacker, get_structs
from .. import bolt, exception
from ..bolt import decoder, encode, structs_cache, struct_calcsize, \
    struct_error

#------------------------------------------------------------------------------
class MelObject(object):
    """An empty class used by group and structure elements for data storage."""
    __slots__ = ()
    _cache_misses = Counter()
    _key_errors = Counter()

    def __eq__(self,other):
        """Operator: =="""
        type_other = type(other)
        type_self = type(self)
        return type_self is type_other and type_self.__slots__ == \
            type_other.__slots__ and all(
            getattr(self, a) == getattr(other, a) for a in type_self.__slots__)

    def __ne__(self,other):
        """Operator: !="""
        type_other = type(other)
        type_self = type(self)
        return type_self is not type_other or type_self.__slots__ != \
            type_other.__slots__ or any(
            getattr(self, a) != getattr(other, a) for a in type_self.__slots__)

    def __hash__(self):  # FIXME: slow, cache?
        return hash(_make_hashable(
            {k: g for k, g in ((a, getattr(self, a)) for a in self.__slots__)
             if g is not None}))

    def __repr__(self):
        """Carefully try to show as much info about ourselves as possible."""
        to_show = []
        for obj_attr in self.__slots__:
            # attrs starting with _ are internal - union types,
            # distributor states, etc.
            if not obj_attr.startswith(u'_') and getattr(self,
                                                         obj_attr) is not None:
                to_show.append(u'%s: %r' % (obj_attr, getattr(self, obj_attr)))
        return u'<%s>' % u', '.join(sorted(to_show)) # is sorted() needed here?

class AttrsCompare(MelObject):
    """MelObject that compares equal based on a set of compare_attrs."""
    compare_attrs = frozenset() # these attrs must resolve to str or None
    __slots__ = ()

    ## FIXME drop lower()
    def __eq__(self, other, __g=getattr):
        return all((s and s.lower()) == (o and o.lower())
            for x in self.compare_attrs
                for s, o in [[__g(self, x), __g(other, x)]]) \
            if isinstance(other, type(self)) else NotImplemented

    def __ne__(self, oth, __g=getattr):
        return any((s and s.lower()) != (o and o.lower())
            for x in self.compare_attrs
                for s, o in [[__g(self, x), __g(oth, x)]]) \
            if isinstance(oth, type(self)) else NotImplemented

    def __hash__(self, __g=getattr):
        return hash(_make_hashable({k: (v and v.lower()) for
             k, v in ((k, (__g(self, k, None))) for k in self.compare_attrs)}))

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

    def packSub(self, out, binary_data):
        # type: (file, bytes) -> None
        """Write subrecord header and data to output stream."""
        try:
            self._dump_bytes(out, binary_data, len(binary_data))
        except Exception:
            bolt.deprint(u'%r: Failed packing: %r, %r' % (
                self, self.mel_sig, binary_data))
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

def unpackSubHeader(ins, recType='----', expType=None, expSize=0, # PY3: ,*,
                    __unpacker=_int_unpacker, __sr=Subrecord):
    """Unpack a subrecord header. Optionally checks for match with expected
    type and size."""
    ins_unpack = ins.unpack
    mel_sig, mel_size = ins_unpack(__sr.sub_header_unpack,
        __sr.sub_header_size, recType + b'.SUB_HEAD')
    #--Extended storage?
    if mel_sig == b'XXXX':
        mel_size = ins_unpack(__unpacker, 4, recType + b'.XXXX.SIZE.')[0]
        mel_sig = ins_unpack(__sr.sub_header_unpack, __sr.sub_header_size,
            recType + b'.XXXX.TYPE')[0] # Throw away size here (always == 0)
    #--Match expected name?
    if expType and expType != mel_sig:
        raise exception.ModError(ins.inName, u'%s: Expected %s subrecord, '
            u'but found %s instead.' % (recType, expType, mel_sig))
    #--Match expected size?
    if expSize and expSize != mel_size:
        raise exception.ModSizeError(ins.inName, recType + '.' + mel_sig,
                                     (expSize,), mel_size)
    return mel_sig, mel_size

class SubrecordBlob(Subrecord):
    """Basic implementation that reads all data without unpacking, adapted to
    current usages."""
    __slots__ = (u'mel_data',)

    def __init__(self, ins, record_sig, mel_sigs=frozenset()):
        # record_sig is the sig of parent record
        mel_sig, mel_size = unpackSubHeader(ins)
        self.mel_sig = mel_sig
        if not mel_sigs or mel_sig in mel_sigs:
            self.mel_data = ins.read(mel_size, record_sig + self.mel_sig)
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
    (to an output stream). All the complexity of subrecords unpacking should
    be encapsulated here. The base class is typically used for unknown
    elements."""
    __slots__ = (u'attr', u'default')

    def __init__(self, mel_sig, attr, default=None):
        self.mel_sig, self.attr, self.default = mel_sig, attr, default

    def getSlotsUsed(self):
        return self.attr,

    def getDefaulters(self, mel_set_instance, mel_key):
        """Register self as a default/mel_object provider.
        :param mel_key: the key to the (possibly nested) mel_object factory
            (may contain dots)
        """
        try:
            defaultrs = mel_set_instance.defaulters
            if self.attr in defaultrs and self.default != defaultrs[self.attr]:
                raise SyntaxError(u'%s duplicate attr %s' % (self, self.attr))
            defaultrs[self.attr] = self.default
        except AttributeError:
            """Mel does not have a self.attr attribute so we won't be needing a
            default value for it."""
            print (type(self))# MelNull

    def getLoaders(self,loaders):
        """Adds self as loader for type."""
        loaders[self.mel_sig] = self

    def hasFids(self,formElements):
        """Include self if has fids."""
        pass

    def load_mel(self, record, ins, sub_type, size_, readId):
        """Read the actual data (not the headers) from ins into record
        attribute."""
        setattr(record, self.attr, ins.read(size_, readId))

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        value = self.pack_subrecord_data(record)
        if value is not None: self.packSub(out, value)

    def pack_subrecord_data(self, record):
        """Get the mod element data stored in record and pack them to a bytes
        string ready to write to an output stream. In some cases another type
        is returned that must be packed by caller (see MelString). Return None
        to skip dumping. It may modify the record before dumping.
        :rtype: basestring | None"""
        return getattr(record, self.attr) # this better be bytes here

    def mapFids(self,record,function,save=False):
        """Applies function to fids. If save is True, then fid is set
        to result of function."""
        raise exception.AbstractError(u'%r does not have FormIDs' % record)

    @property
    def signatures(self):
        """Returns a set containing all the signatures (aka mel_sigs) that
        could belong to this element. For most elements, this is just a single
        one, but groups and unions return multiple here.

        :rtype: set[bytes]"""
        return {self.mel_sig}

    @property
    def static_size(self):
        """Returns an integer denoting the number of bytes this element is
        going to take. Raises an AbstractError if the element can't know this
        (e.g. MelBase or MelNull).

        :rtype: int"""
        raise exception.AbstractError()

    def __repr__(self):
        return u'[%s]: %s' % (type(self).__name__, getattr(self, u'attr', None))

class MelCollection(MelBase):
    """Any old collection of mod elements."""
    def __init__(self, mel_sig, attr=u'', *elements):
        super(MelCollection, self).__init__(mel_sig, attr)

# Simple static Fields --------------------------------------------------------
class _MelNum(MelBase):
    """A simple static subrecord representing a number."""
    _unpacker, _packer, static_size = get_structs(u'I')
    __slots__ = ()

    def load_mel(self, record, ins, sub_type, size_, readId):
        setattr(record, self.attr, ins.unpack(self._unpacker, size_,
                                              readId)[0])
    _optionals = set()
    def pack_subrecord_data(self, record):
        try:
            return self._packer(getattr(record, self.attr))
        except AttributeError:
            print(u'%s AttributeError %s' % (record, self.attr))
        except struct_error:
            ##: struct.error raised when trying to pack None (so the default,
            # meaning the subrecord was not present so the Num is optional we
            # want to eventually use MelOpt*** for those
            key = (record.recType if hasattr(record,  u'recType') else
                   record.__slots__, self.attr)
            if not key in self._optionals:
                self._optionals.add(key)
                print(u'Optional: %s.%s ?' % key)
        return None

#------------------------------------------------------------------------------
class MelCounter(MelBase):
    """Wraps a MelStruct-derived object with one numeric element (meaning that
    it is compatible with e.g. MelUInt32). Just before writing, the wrapped
    element's value is updated to the len() of another element's value, e.g. a
    MelGroups instance. Additionally, dumping is skipped if the counter is
    falsy after updating.

    Does not support anything that seems at odds with that goal, in particular
    fids and defaulters. See also MelPartialCounter, which targets mixed
    structs."""
    def __init__(self, counter_mel, counts):
        """Creates a new MelCounter.

        :param counter_mel: The element that stores the counter's value.
        :type counter_mel: _MelField
        :param counts: The attribute name that this counter counts.
        :type counts: unicode"""
        self._counter_mel = counter_mel
        self.counted_attr = counts

    def getSlotsUsed(self):
        return self._counter_mel.getSlotsUsed()

    def getLoaders(self, loaders):
        loaders[self._counter_mel.mel_sig] = self

    def getDefaulters(self, mel_set_instance, mel_key):
        self._counter_mel.getDefaulters(mel_set_instance, mel_key)

    def load_mel(self, record, ins, sub_type, size_, readId):
        self._counter_mel.load_mel(record, ins, sub_type, size_, readId)

    def dumpData(self, record, out):
        # Count the counted type first, then check if we should even dump
        val_len = len(getattr(record, self.counted_attr, []))
        setattr(record, self._counter_mel.attr, val_len)
        if val_len:
            self._counter_mel.dumpData(record, out)

    @property
    def signatures(self):
        return self._counter_mel.signatures

    @property
    def static_size(self):
        return self._counter_mel.static_size

class MelPartialCounter(MelCounter):
    """Extends MelCounter to work for MelStruct's that contain more than just a
    counter. This means adding behavior for mapping fids, but dropping the
    conditional dumping behavior."""
    def __init__(self, counter_mel, counter, counts):
        """Creates a new MelPartialCounter.

        :param counter_mel: The element that stores the counter's value.
        :type counter_mel: MelStruct
        :param counter: The attribute name of the counter.
        :type counter: unicode
        :param counts: The attribute name that this counter counts.
        :type counts: unicode"""
        super(MelPartialCounter, self).__init__(counter_mel, counts)
        self.counter_attr = counter

    def hasFids(self, formElements):
        self._counter_mel.hasFids(formElements)

    def dumpData(self, record, out):
        # Count the counted type, then update and dump unconditionally
        setattr(record, self.counter_attr,
                len(getattr(record, self.counted_attr, [])))
        self._counter_mel.dumpData(record, out)

#------------------------------------------------------------------------------
# TODO(inf) DEPRECATED! - don't use for new usages -> MelGroups(MelFid)
#  instead. Same idea as with MelFidList.
class MelFids(MelBase):
    """Represents a mod record fid elements."""

    def hasFids(self,formElements):
        formElements.add(self)

    def getDefaulters(self, mel_set_instance, mel_key):
        if self.attr in mel_set_instance.listers:
            raise SyntaxError(
                u'%s duplicate attr %s' % (self, self.attr))
        mel_set_instance.listers.add(self.attr)

    def load_mel(self, record, ins, sub_type, size_, readId):
        fid = ins.unpackRef()
        getattr(record, self.attr).append(fid)

    def dumpData(self, record, out, __packer=structs_cache[u'I'].pack):
        for fid in getattr(record, self.attr):
            MelFid(self.mel_sig, '').packSub(out, __packer(fid))

    def mapFids(self,record,function,save=False):
        fids = getattr(record, self.attr)
        for index,fid in enumerate(fids):
            result = function(fid)
            if save: fids[index] = result

#------------------------------------------------------------------------------
class MelNull(MelBase):
    """Represents an obsolete record. Reads bytes from instream, but then
    discards them and is otherwise inactive."""

    def __init__(self, mel_sig):
        self.mel_sig = mel_sig

    def getSlotsUsed(self):
        return ()

    def getDefaulters(self, mel_set_instance, mel_key):
        pass

    def load_mel(self, record, ins, sub_type, size_, readId):
        ins.seek(size_, 1, readId)

    def dumpData(self,record,out):
        pass

#------------------------------------------------------------------------------
# TODO(inf) DEPRECATED! - don't use for new usages -> MelArray(MelFid) instead.
#  Not backwards-compatible (runtime interface differs), hence deprecation.
class MelFidList(MelFids):
    """Represents a listmod record fid elements. The only difference from
    MelFids is how the data is stored. For MelFidList, the data is stored
    as a single subrecord rather than as separate subrecords."""

    def load_mel(self, record, ins, sub_type, size_, readId):
        if not size_: return
        fids = ins.unpack(structs_cache[u'%dI' % (size_ // 4)].unpack, size_,
                          readId)
        setattr(record, self.attr, list(fids))

    def dumpData(self, record, out):
        fids = getattr(record, self.attr)
        if not fids: return
        fids_packed = structs_cache[u'%dI' % len(fids)].pack(*fids)
        self.packSub(out, fids_packed)

#------------------------------------------------------------------------------
class MelSequential(MelBase):
    """Represents a sequential, which is simply a way for one record element to
    delegate loading to multiple other record elements. It basically behaves
    like MelGroup, but does not assign to an attribute."""
    def __init__(self, *elements):
        self.elements, self.form_elements = elements, set()
        self._possible_sigs = {s for element in self.elements for s
                               in element.signatures}
        self._sub_loaders = {}

    def getDefaulters(self, mel_set_instance, mel_key):
        for element in self.elements:
            element.getDefaulters(mel_set_instance, mel_key)

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

    def load_mel(self, record, ins, sub_type, size_, readId):
        # This will only ever be called if we're used in a distributor, regular
        # MelSet will just bypass us entirely. So just redirect to the right
        # sub-loader that we found in getLoaders
        self._sub_loaders[sub_type].load_mel(record, ins, sub_type, size_,
                                             readId)

    def dumpData(self, record, out):
        for element in self.elements:
            element.dumpData(record, out)

    def mapFids(self, record, function, save=False):
        for element in self.form_elements:
            element.mapFids(record, function, save)

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

    def __init__(self, attr, *elements):
        """:type attr: unicode"""
        super(MelGroup, self).__init__(*elements)
        self.attr, self.loaders = attr, {}
        # set up the MelObject needed for this MelGroup
        from .record_structs import MelSet
        group_mel_set = MelSet(*elements)
        # def _attr(key):
        #     return u'%s.%s' % (self.attr, key) if self.attr else key
        # # mel_set_instance.mel_providers_dict[
        # #     _attr(self.attr)] = self._mel_object_type
        # for k, v in group_mel_set.mel_providers_dict.items():
        #     del group_mel_set.mel_providers_dict[k]
        #     group_mel_set.mel_providers_dict[_attr(k)] = v
        # self.mel_providers = group_mel_set.mel_providers_dict
        class _MelObject(self.__class__._mel_object_base_type):
            __slots__ = tuple(
                chain(group_mel_set.defaulters, group_mel_set.listers,
                      (m for m in group_mel_set.mel_providers_dict if
                       u'.' not in m)))
            mel_set_obj = group_mel_set
            def __getattr__(self, missing_attr, __mset=mel_set_obj):
                self.__class__._cache_misses[missing_attr] += 1
                if missing_attr in __mset.defaulters:
                    target = __mset.defaulters[missing_attr]
                elif missing_attr in __mset.listers:
                    target = []
                elif missing_attr in __mset.mel_providers_dict:
                    target = __mset.mel_providers_dict[missing_attr]()
                else:
                    if not missing_attr in self.__class__._key_errors:
                        # https://stackoverflow.com/a/33388198/281545
                        print(missing_attr)  # '__deepcopy__' !
                    self.__class__._key_errors[missing_attr] += 1
                    raise AttributeError(missing_attr)
                setattr(self, missing_attr, target)
                return target
        self._mel_object_type = _MelObject

    def getDefaulters(self, mel_set_instance, mel_key):
        if not mel_key:
            mel_set_instance.mel_providers_dict[self.attr] = self._mel_object_type
            # we are a top-level group so we need to directly set record attrs
            defaultrs = mel_set_instance.defaulters
            common_attrs = set(self._mel_object_type.mel_set_obj.defaulters) & set(
                defaultrs)
            if common_attrs:
                dups = set((a, defaultrs[a],
                            self._mel_object_type.mel_set_obj.defaulters[a]) for a
                           in common_attrs if defaultrs[a] !=
                           self._mel_object_type.mel_set_obj.defaulters[a])
                if dups:
                    raise SyntaxError(u'%s duplicate attr(s) %s' % (self, dups))
            defaultrs.update(self._mel_object_type.mel_set_obj.defaulters)
            common_listers = mel_set_instance.listers & \
                             self._mel_object_type.mel_set_obj.listers
            if common_listers:
                raise SyntaxError(
                    u'%s duplicate attr(s) %s' % (self, common_listers))
            mel_set_instance.listers.update(
                self._mel_object_type.mel_set_obj.listers)
            for k, v in self._mel_object_type.mel_set_obj.mel_providers_dict.items():
                mel_set_instance.mel_providers_dict[u'%s.%s' % (self.attr, k)] = v
        else: # we are a MelGroups nested inside a MelGroup inform parent Group
            for k, v in self._mel_object_type.mel_set_obj.mel_providers_dict.items():
                mel_set_instance.mel_providers_dict[u'%s.%s' % (mel_key, k)] = v

    def getLoaders(self,loaders):
        super(MelGroup, self).getLoaders(self.loaders)
        for type in self.loaders:
            loaders[type] = self

    def getSlotsUsed(self):
        return self.attr,

    def load_mel(self, record, ins, sub_type, size_, readId):
        target = getattr(record, self.attr)
        self.loaders[sub_type].load_mel(target, ins, sub_type, size_, readId)

    def dumpData(self,record,out):
        target = getattr(record, self.attr) # type: MelObject
        if not target: return
        super(MelGroup, self).dumpData(target, out) # call getattr on target

    def mapFids(self,record,function,save=False):
        target = getattr(record, self.attr)
        if not target: return
        super(MelGroup, self).mapFids(target, function, save)

#------------------------------------------------------------------------------
class MelGroups(MelGroup):
    """Represents an array of group record."""

    def __init__(self,attr,*elements):
        """Initialize. Must have at least one element."""
        super(MelGroups, self).__init__(attr, *elements)
        self._init_sigs = self.elements[0].signatures

    def getDefaulters(self, mel_set_instance, mel_key):
        mel_set_instance.listers.add(self.attr)
        def _att(attr):
            return u'%s.%s' % (mel_key, attr) if mel_key else attr
        super(MelGroups, self).getDefaulters(mel_set_instance, _att(self.attr))
        mel_set_instance.mel_providers_dict[
            _att(self.attr)] = self._mel_object_type
        # # mel_set_instance.mel_providers_dict.update(
        # #     (_att(k), v) for k, v in self.mel_providers.iteritems())

    def load_mel(self, record, ins, sub_type, size_, readId):
        if sub_type in self._init_sigs:
            # We've hit one of the initial signatures, make a new object
            target = self._new_object(record)
        else:
            # Add to the existing element
            target = getattr(record, self.attr)[-1]
        self.loaders[sub_type].load_mel(target, ins, sub_type, size_, readId)

    def _new_object(self, record):
        """Creates a new MelObject, initializes it and appends it to this
        MelGroups' attribute."""
        target = self._mel_object_type()
        getattr(record, self.attr).append(target)
        return target

    def dumpData(self,record,out):
        elements = self.elements
        for target in getattr(record, self.attr):
            for element in elements:
                element.dumpData(target,out)

    def mapFids(self,record,function,save=False):
        formElements = self.form_elements
        for target in getattr(record, self.attr):
            for element in formElements:
                element.mapFids(target,function,save)

    @property
    def static_size(self):
        raise exception.AbstractError()

#------------------------------------------------------------------------------
class MelString(MelBase):
    """Represents a mod record string element."""

    def __init__(self, mel_sig, attr, default=None, maxSize=0, minSize=0):
        super(MelString, self).__init__(mel_sig, attr, default)
        self.maxSize = maxSize
        self.minSize = minSize
        self.encoding = None # will default to bolt.pluginEncoding

    def load_mel(self, record, ins, sub_type, size_, readId):
        setattr(record, self.attr, ins.readString(size_, readId))

    def packSub(self, out, string_val):
        # type: (file, unicode) -> None
        """Writes out a string subrecord, properly encoding it beforehand and
        respecting max_size, min_size and preferred_encoding if they are
        set."""
        byte_string = bolt.encode_complex_string(string_val, self.maxSize,
            self.minSize, self.encoding)
        # len of data will be recalculated in MelString._dump_bytes
        super(MelString, self).packSub(out, byte_string)

    def _dump_bytes(self, out, byte_string, lenData):
        """Write a properly encoded string with a null terminator."""
        super(MelString, self)._dump_bytes(out, byte_string,
            lenData + 1) # add the len of null terminator
        out.write(null1) # then write it out

#------------------------------------------------------------------------------
class MelUnicode(MelString):
    """Like MelString, but instead of using bolt.pluginEncoding to read the
       string, it tries the encoding specified in the constructor instead"""
    def __init__(self, mel_sig, attr, default=None, maxSize=0, encoding=None):
        super(MelUnicode, self).__init__(mel_sig, attr, default, maxSize)
        self.encoding = encoding # None == automatic detection

    def load_mel(self, record, ins, sub_type, size_, readId):
        value = u'\n'.join(decoder(x,self.encoding,avoidEncodings=('utf8','utf-8'))
                           for x in bolt.cstrip(ins.read(size_, readId)).split('\n'))
        setattr(record, self.attr, value)

#------------------------------------------------------------------------------
class MelLString(MelString):
    """Represents a mod record localized string."""
    def load_mel(self, record, ins, sub_type, size_, readId):
        setattr(record, self.attr, ins.readLString(size_, readId))

#------------------------------------------------------------------------------
class MelStrings(MelString):
    """Represents array of strings."""

    def getDefaulters(self, mel_set_instance, mel_key):
        mel_set_instance.listers.add(self.attr)

    def load_mel(self, record, ins, sub_type, size_, readId):
        setattr(record, self.attr, ins.readStrings(size_, readId))

    def packSub(self, out, strings, force_encoding=None):
        """Writes out a strings array subrecord, encoding and adding a null
        terminator to each string separately."""
        str_data = null1.join( # TODO use encode_complex_string?
            encode(x, firstEncoding=bolt.pluginEncoding) for x in strings)
        # call *MelBase* packSub which however will call MelString._dump_bytes
        super(MelString, self).packSub(out, str_data)

#------------------------------------------------------------------------------
class MelStruct(MelBase):
    """Represents a structure record."""

    def __init__(self, mel_sig, struct_format, *elements):
        """:type mel_sig: bytes
        :type struct_format: unicode"""
        # Sometimes subrecords have to preserve non-aligned sizes, check that
        # we don't accidentally pad those to alignment
        if (not struct_format.startswith(u'=') and
                struct_calcsize(struct_format) != struct_calcsize(
                    u'=' + struct_format)):
            raise SyntaxError(
                u"Automatic padding inserted for struct format '%s', this is "
                u"almost certainly not what you want. Prepend '=' to preserve "
                u"the unaligned size or manually pad with 'x' to avoid this "
                u"error." % struct_format)
        self.mel_sig = mel_sig
        self.attrs, self.defaults, self.actions, self.formAttrs = \
            parseElements(*elements)
        # Check for duplicate attrs - can't rely on MelSet.getSlotsUsed only,
        # since we may end up in a MelUnion which has to use a set to collect
        # its slots
        present_attrs = set()
        for a in self.attrs:
            if a in present_attrs:
                raise SyntaxError(u"Duplicate attribute '%s' in struct "
                                  u"definition" % a)
            present_attrs.add(a)
        _struct = structs_cache[struct_format]
        self._unpacker = _struct.unpack
        self._packer = _struct.pack
        self._static_size = _struct.size

    def getSlotsUsed(self):
        return self.attrs

    def hasFids(self,formElements):
        if self.formAttrs: formElements.add(self)

    def getDefaulters(self, mel_set_instance, mel_key):
        defaultrs = mel_set_instance.defaulters
        common_attrs = set(self.attrs) & set(defaultrs)
        dups = common_attrs & set((a, defaultrs[a], dflt) for a, dflt in
                                  zip(self.attrs, self.defaults) if
                                  a in common_attrs and defaultrs[a] != dflt)
        if dups:
            raise SyntaxError(u'%s duplicate attr(s) %s' % (self, dups))
        for attr,value,action in zip(self.attrs, self.defaults, self.actions):
            defaultrs[attr] = action(value) if action else value

    def load_mel(self, record, ins, sub_type, size_, readId):
        unpacked = ins.unpack(self._unpacker, size_, readId)
        for attr,value,action in zip(self.attrs,unpacked,self.actions):
            setattr(record, attr, action(value) if action else value)

    def pack_subrecord_data(self, record):
        # Just in case, apply the action to itself before dumping to handle
        # e.g. a FixedString getting assigned a unicode value. Worst case,
        # this is just a noop.
        values = [
            action(value).dump() if action else value for value, action in
            zip([getattr(record, a) for a in self.attrs], self.actions)]
        try:
            return self._packer(*values)
        except struct_error:
            return None

    def mapFids(self,record,function,save=False):
        for attr in self.formAttrs:
            result = function(getattr(record, attr))
            if save: setattr(record, attr, result)

    @property
    def static_size(self):
        return self._static_size

def parseElements(*elements):
    """Parses elements and returns attrs,defaults,actions,formAttrs where:
    * attrs is tuple of attributes (names)
    * formAttrs is set of attributes that have fids,
    * defaults is tuple of default values for attributes
    * actions is tuple of callables to be used when loading data
    Note that each element of defaults and actions matches corresponding attr element.
    Used by MelStruct and _MelField.

    Example call:
    parseElements('level', ('unused1', null2), (FID, 'listId', None),
                  ('count', 1), ('unused2', null2))

    :type elements: (list[None|unicode|tuple])"""
    formAttrs = set()
    lenEls = len(elements)
    attrs, defaults, actions = [0] * lenEls, [0] * lenEls, [0] * lenEls
    for index,element in enumerate(elements):
        if not isinstance(element,tuple):
            attrs[index] = element
        else:
            el_0 = element[0]
            attrIndex = el_0 == 0
            if el_0 == FID:
                formAttrs.add(element[1])
                attrIndex = 1
            elif callable(el_0):
                actions[index] = el_0
                attrIndex = 1
            attrs[index] = element[attrIndex]
            if len(element) - attrIndex == 2:
                defaults[index] = element[-1] # else leave to 0
    return tuple(attrs), tuple(defaults), tuple(actions), formAttrs

#------------------------------------------------------------------------------
class MelFixedString(MelStruct):
    """Subrecord that stores a string of a constant length. Just a wrapper
    around a struct with a single FixedString element."""
    def __init__(self, signature, attr, str_length, default=b''):
        super(MelFixedString, self).__init__(signature, u'%us' % str_length,
            (FixedString(str_length, default), attr))

# Simple primitive type wrappers ----------------------------------------------
class MelFloat(_MelNum):
    """Float."""
    _unpacker, _packer, static_size = get_structs(u'=f')

class MelSInt8(_MelNum):
    """Signed 8-bit integer."""
    _unpacker, _packer, static_size = get_structs(u'=b')

class MelSInt16(_MelNum):
    """Signed 16-bit integer."""
    _unpacker, _packer, static_size = get_structs(u'=h')

class MelSInt32(_MelNum):
    """Signed 32-bit integer."""
    _unpacker, _packer, static_size = get_structs(u'=i')

class MelUInt8(_MelNum):
    """Unsigned 8-bit integer."""
    _unpacker, _packer, static_size = get_structs(u'=B')

class MelUInt16(_MelNum):
    """Unsigned 16-bit integer."""
    _unpacker, _packer, static_size = get_structs(u'=H')

class MelUInt32(_MelNum):
    """Unsigned 32-bit integer."""
    _unpacker, _packer, static_size = get_structs(u'=I')

class _MelFlags(_MelNum):
    """Integer flag field."""
    __slots__ = (u'_flag_type',)

    def __init__(self, mel_sig, attr, flags_type):
        super(_MelFlags, self).__init__(mel_sig, attr, default=flags_type(0))
        self._flag_type = flags_type

    def load_mel(self, record, ins, sub_type, size_, readId):
        setattr(record, self.attr, self._flag_type(ins.unpack(
            self._unpacker, size_, readId)[0]))

    def pack_subrecord_data(self, record):
        return self._packer(getattr(record, self.attr).dump())

class MelUInt8Flags(MelUInt8, _MelFlags): pass
class MelUInt16Flags(MelUInt16, _MelFlags): pass
class MelUInt32Flags(MelUInt32, _MelFlags): pass

#------------------------------------------------------------------------------
class MelXXXX(MelUInt32):
    """Represents an XXXX size field. Ignores record in load/dump"""

    def __init__(self, int_size):
        self.int_size = int_size
        self.mel_sig = b'XXXX'

    def load_mel(self, record, ins, sub_type, size_, readId):
        self.int_size = ins.unpack(self._unpacker, size_, readId)[0]

    def pack_subrecord_data(self, record):
        return self._packer(self.int_size)

#------------------------------------------------------------------------------
class MelFid(MelUInt32):
    """Represents a mod record fid element."""

    def hasFids(self,formElements):
        formElements.add(self)

    def mapFids(self,record,function,save=False):
        attr = self.attr
        try:
            fid = getattr(record, attr)
        except AttributeError:
            fid = None
        result = function(fid)
        if save: setattr(record, attr, result)

#------------------------------------------------------------------------------
class MelOptStruct(MelStruct):
    """Represents an optional structure that is only dumped if at least one
    value is not equal to the default."""

    def pack_subrecord_data(self, record):
        # TODO: Unfortunately, checking if the attribute is None is not
        # really effective.  Checking it to be 0,empty,etc isn't effective either.
        # It really just needs to check it against the default.
        for attr,default in zip(self.attrs,self.defaults):
            oldValue = getattr(record, attr)
            if oldValue is not None and oldValue != default:
                return super(MelOptStruct, self).pack_subrecord_data(record)
        return None

#------------------------------------------------------------------------------
# 'Opt' versions of the type wrappers above
class MelOptNum(_MelNum):
    """Represents an optional field that is only dumped if at least one
    value is not equal to the default."""

    def pack_subrecord_data(self, record):
        oldValue = getattr(record, self.attr)
        if oldValue is not None and oldValue != self.default:
            return super(MelOptNum, self).pack_subrecord_data(record)
        return None

class MelOptFloat(MelOptNum, MelFloat):
    """Optional float."""

class MelOptSInt8(MelOptNum, MelSInt8):
    """Optional signed 8-bit integer."""
    # Unused right now - keeping around for completeness' sake and to make
    # future usage simpler.

class MelOptSInt16(MelOptNum, MelSInt16):
    """Optional signed 16-bit integer."""

class MelOptSInt32(MelOptNum, MelSInt32):
    """Optional signed 32-bit integer."""

class MelOptUInt8(MelOptNum, MelUInt8):
    """Optional unsigned 8-bit integer."""

class MelOptUInt16(MelOptNum, MelUInt16):
    """Optional unsigned 16-bit integer."""

class MelOptUInt32(MelOptNum, MelUInt32):
    """Optional unsigned 32-bit integer."""

class MelOptFid(MelFid, MelOptUInt32):  # TODO(ut): as it stands it could be
    #   MelOptFid(MelFid) -> that's because MelFid is also used for optional
    #   fids all over the place
    """Optional FormID. Wrapper around MelOptUInt32 to avoid having to
    constantly specify the format."""

class MelOptUInt8Flags(MelOptUInt8, _MelFlags): pass
class MelOptUInt16Flags(MelOptUInt16, _MelFlags): pass
class MelOptUInt32Flags(MelOptUInt32, _MelFlags): pass
