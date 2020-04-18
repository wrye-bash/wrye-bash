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
"""Houses basic building blocks for creating record definitions. Somewhat
higher-level building blocks can be found in common_subrecords.py."""

from __future__ import division, print_function
import struct

from .utils_constants import FID, null1
from .. import bolt, exception
from ..bolt import decode, encode

#------------------------------------------------------------------------------
class MelObject(object):
    """An empty class used by group and structure elements for data storage."""
    def __eq__(self,other):
        """Operator: =="""
        return isinstance(other,MelObject) and self.__dict__ == other.__dict__

    def __ne__(self,other):
        """Operator: !="""
        return not isinstance(other,MelObject) or self.__dict__ != other.__dict__

    def __repr__(self):
        """Carefully try to show as much info about ourselves as possible."""
        to_show = []
        if hasattr(self, '__slots__'):
            for obj_attr in self.__slots__:
                # attrs starting with _ are internal - union types,
                # distributor states, etc.
                if not obj_attr.startswith(u'_') and hasattr(self, obj_attr):
                    to_show.append(
                        u'%s: %r' % (obj_attr, getattr(self, obj_attr)))
        return u'<%s>' % u', '.join(sorted(to_show)) # is sorted() needed here?

#------------------------------------------------------------------------------
class MelBase(object):
    """Represents a mod record raw element. Typically used for unknown elements.
    Also used as parent class for other element types."""

    def __init__(self, subType, attr, default=None):
        self.subType, self.attr, self.default = subType, attr, default

    def getSlotsUsed(self):
        return self.attr,

    @staticmethod
    def parseElements(*elements):
        # type: (list[None|unicode|tuple]) -> list[tuple]
        """Parses elements and returns attrs,defaults,actions,formAttrs where:
        * attrs is tuple of attributes (names)
        * formAttrs is tuple of attributes that have fids,
        * defaults is tuple of default values for attributes
        * actions is tuple of callables to be used when loading data
        Note that each element of defaults and actions matches corresponding attr element.
        Used by struct subclasses.

        Example call:
        parseElements('level', ('unused1', null2), (FID, 'listId', None),
                      ('count', 1), ('unused2', null2))
        """
        formAttrs = []
        lenEls = len(elements)
        attrs,defaults,actions = [0]*lenEls,[0]*lenEls,[0]*lenEls
        formAttrsAppend = formAttrs.append
        for index,element in enumerate(elements):
            if not isinstance(element,tuple): element = (element,)
            el_0 = element[0]
            attrIndex = el_0 == 0
            if el_0 == FID:
                formAttrsAppend(element[1])
                attrIndex = 1
            elif callable(el_0):
                actions[index] = el_0
                attrIndex = 1
            attrs[index] = element[attrIndex]
            if len(element) - attrIndex == 2:
                defaults[index] = element[-1] # else leave to 0
        return map(tuple,(attrs,defaults,actions,formAttrs))

    def getDefaulters(self,defaulters,base):
        """Registers self as a getDefault(attr) provider."""
        pass

    def getDefault(self):
        """Returns a default copy of object."""
        raise exception.AbstractError()

    def getLoaders(self,loaders):
        """Adds self as loader for type."""
        loaders[self.subType] = self

    def hasFids(self,formElements):
        """Include self if has fids."""
        pass

    def setDefault(self,record):
        """Sets default value for record instance."""
        record.__setattr__(self.attr,self.default)

    def loadData(self, record, ins, sub_type, size_, readId):
        """Reads data from ins into record attribute."""
        record.__setattr__(self.attr, ins.read(size_, readId))

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        value = record.__getattribute__(self.attr)
        if value is not None: out.packSub(self.subType,value)

    def mapFids(self,record,function,save=False):
        """Applies function to fids. If save is True, then fid is set
        to result of function."""
        raise exception.AbstractError

    @property
    def signatures(self):
        """Returns a set containing all the signatures (aka subTypes) that
        could belong to this element. For most elements, this is just a single
        one, but groups and unions return multiple here.

        :rtype: set[str]"""
        return {self.subType}

    @property
    def static_size(self):
        """Returns an integer denoting the number of bytes this element is
        going to take. Raises an AbstractError if the element can't know this
        (e.g. MelBase or MelNull).

        :rtype: int"""
        raise exception.AbstractError()

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
    def __init__(self, element, counts):
        """Creates a new MelCounter.

        :param element: The element that stores the counter's value.
        :type element: MelStruct
        :param counts: The attribute name that this counter counts.
        :type counts: str"""
        self.element = element
        self.counted_attr = counts

    def getSlotsUsed(self):
        return self.element.getSlotsUsed()

    def getLoaders(self, loaders):
        loaders[self.element.subType] = self

    def setDefault(self, record):
        self.element.setDefault(record)

    def loadData(self, record, ins, sub_type, size_, readId):
        self.element.loadData(record, ins, sub_type, size_, readId)

    def dumpData(self, record, out):
        # Count the counted type first, then check if we should even dump
        val_len = len(getattr(record, self.counted_attr, []))
        if val_len:
            # We should dump, so update the counter and do it
            setattr(record, self.element.attrs[0], val_len)
            self.element.dumpData(record, out)

    @property
    def signatures(self):
        return self.element.signatures

    @property
    def static_size(self):
        return self.element.static_size

class MelPartialCounter(MelCounter):
    """Extends MelCounter to work for MelStruct's that contain more than just a
    counter. This means adding behavior for mapping fids, but dropping the
    conditional dumping behavior."""
    def __init__(self, element, counter, counts):
        """Creates a new MelPartialCounter.

        :param element: The element that stores the counter's value.
        :type element: MelStruct
        :param counter: The attribute name of the counter.
        :type counter: str
        :param counts: The attribute name that this counter counts.
        :type counts: str"""
        MelCounter.__init__(self, element, counts)
        self.counter_attr = counter

    def hasFids(self, formElements):
        self.element.hasFids(formElements)

    def dumpData(self, record, out):
        # Count the counted type, then update and dump unconditionally
        setattr(record, self.counter_attr,
                len(getattr(record, self.counted_attr, [])))
        self.element.dumpData(record, out)

#------------------------------------------------------------------------------
class MelFid(MelBase):
    """Represents a mod record fid element."""

    def hasFids(self,formElements):
        formElements.add(self)

    def loadData(self, record, ins, sub_type, size_, readId):
        record.__setattr__(self.attr,ins.unpackRef())

    def dumpData(self,record,out):
        try:
            value = record.__getattribute__(self.attr)
        except AttributeError:
            value = None
        if value is not None: out.packRef(self.subType,value)

    def mapFids(self,record,function,save=False):
        attr = self.attr
        try:
            fid = record.__getattribute__(attr)
        except AttributeError:
            fid = None
        result = function(fid)
        if save: record.__setattr__(attr,result)

    @property
    def static_size(self):
        return 4 # Always a uint32

#------------------------------------------------------------------------------
class MelFids(MelBase):
    """Represents a mod record fid elements."""

    def hasFids(self,formElements):
        formElements.add(self)

    def setDefault(self,record):
        record.__setattr__(self.attr,[])

    def loadData(self, record, ins, sub_type, size_, readId):
        fid = ins.unpackRef()
        record.__getattribute__(self.attr).append(fid)

    def dumpData(self,record,out):
        type = self.subType
        outPackRef = out.packRef
        for fid in record.__getattribute__(self.attr):
            outPackRef(type,fid)

    def mapFids(self,record,function,save=False):
        fids = record.__getattribute__(self.attr)
        for index,fid in enumerate(fids):
            result = function(fid)
            if save: fids[index] = result

#------------------------------------------------------------------------------
class MelNull(MelBase):
    """Represents an obsolete record. Reads bytes from instream, but then
    discards them and is otherwise inactive."""

    def __init__(self, subType):
        self.subType = subType

    def getSlotsUsed(self):
        return ()

    def setDefault(self,record):
        pass

    def loadData(self, record, ins, sub_type, size_, readId):
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

    def loadData(self, record, ins, sub_type, size_, readId):
        if not size_: return
        fids = ins.unpack(repr(size_ // 4) + 'I', size_, readId)
        record.__setattr__(self.attr,list(fids))

    def dumpData(self,record,out):
        fids = record.__getattribute__(self.attr)
        if not fids: return
        out.packSub(self.subType,repr(len(fids))+'I',*fids)

#------------------------------------------------------------------------------
class MelSequential(MelBase):
    """Represents a sequential, which is simply a way for one record element to
    delegate loading to multiple other record elements. It basically behaves
    like MelGroup, but does not assign to an attribute."""
    def __init__(self, *elements):
        self.elements, self.form_elements = elements, set()
        self._possible_sigs = {s for element in self.elements for s
                               in element.signatures}

    def getDefaulters(self, defaulters, base):
        for element in self.elements:
            element.getDefaulters(defaulters, base + '.')

    def getLoaders(self, loaders):
        for element in self.elements:
            element.getLoaders(loaders)

    def getSlotsUsed(self):
        slots_ret = set()
        for element in self.elements:
            slots_ret.update(element.getSlotsUsed())
        return tuple(slots_ret)

    def hasFids(self, formElements):
        for element in self.elements:
            element.hasFids(self.form_elements)
        if self.form_elements: formElements.add(self)

    def setDefault(self, record):
        for element in self.elements:
            element.setDefault(record)

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
    """Represents a group record."""
    def __init__(self,attr,*elements):
        """:type attr: str"""
        MelSequential.__init__(self, *elements)
        self.attr, self.loaders = attr, {}

    def getDefaulters(self,defaulters,base):
        defaulters[base+self.attr] = self
        MelSequential.getDefaulters(self, defaulters, base + self.attr)

    def getLoaders(self,loaders):
        MelSequential.getLoaders(self, self.loaders)
        for type in self.loaders:
            loaders[type] = self

    def getSlotsUsed(self):
        return self.attr,

    def setDefault(self,record):
        record.__setattr__(self.attr,None)

    def getDefault(self):
        target = MelObject()
        for element in self.elements:
            element.setDefault(target)
        return target

    def loadData(self, record, ins, sub_type, size_, readId):
        target = record.__getattribute__(self.attr)
        if target is None:
            target = self.getDefault()
            target.__slots__ = [s for element in self.elements for s in
                                element.getSlotsUsed()]
            record.__setattr__(self.attr,target)
        self.loaders[sub_type].loadData(target, ins, sub_type, size_, readId)

    def dumpData(self,record,out):
        target = record.__getattribute__(self.attr)
        if not target: return
        MelSequential.dumpData(self, target, out)

    def mapFids(self,record,function,save=False):
        target = record.__getattribute__(self.attr)
        if not target: return
        MelSequential.mapFids(self, target, function, save)

#------------------------------------------------------------------------------
class MelGroups(MelGroup):
    """Represents an array of group record."""

    def __init__(self,attr,*elements):
        """Initialize. Must have at least one element."""
        MelGroup.__init__(self,attr,*elements)
        self._init_sigs = self.elements[0].signatures

    def setDefault(self,record):
        record.__setattr__(self.attr,[])

    def loadData(self, record, ins, sub_type, size_, readId):
        if sub_type in self._init_sigs:
            # We've hit one of the initial signatures, make a new object
            target = self.getDefault()
            target.__slots__ = [s for element in self.elements for s in
                                element.getSlotsUsed()]
            record.__getattribute__(self.attr).append(target)
        else:
            # Add to the existing element
            target = record.__getattribute__(self.attr)[-1]
        self.loaders[sub_type].loadData(target, ins, sub_type, size_, readId)

    def dumpData(self,record,out):
        elements = self.elements
        for target in record.__getattribute__(self.attr):
            for element in elements:
                element.dumpData(target,out)

    def mapFids(self,record,function,save=False):
        formElements = self.form_elements
        for target in record.__getattribute__(self.attr):
            for element in formElements:
                element.mapFids(target,function,save)

    @property
    def static_size(self):
        raise exception.AbstractError()

#------------------------------------------------------------------------------
class MelString(MelBase):
    """Represents a mod record string element."""

    def __init__(self, subType, attr, default=None, maxSize=0):
        MelBase.__init__(self, subType, attr, default)
        self.maxSize = maxSize

    def loadData(self, record, ins, sub_type, size_, readId):
        value = ins.readString(size_, readId)
        record.__setattr__(self.attr,value)

    def dumpData(self,record,out):
        string_val = record.__getattribute__(self.attr)
        if string_val is not None:
            out.write_string(self.subType, string_val, max_size=self.maxSize)

#------------------------------------------------------------------------------
class MelUnicode(MelString):
    """Like MelString, but instead of using bolt.pluginEncoding to read the
       string, it tries the encoding specified in the constructor instead"""
    def __init__(self, subType, attr, default=None, maxSize=0, encoding=None):
        MelString.__init__(self, subType, attr, default, maxSize)
        self.encoding = encoding # None == automatic detection

    def loadData(self, record, ins, sub_type, size_, readId):
        value = u'\n'.join(decode(x,self.encoding,avoidEncodings=('utf8','utf-8'))
                           for x in bolt.cstrip(ins.read(size_, readId)).split('\n'))
        record.__setattr__(self.attr,value)

    def dumpData(self,record,out):
        string_val = record.__getattribute__(self.attr)
        if string_val is not None:
            out.write_string(self.subType, string_val, max_size=self.maxSize,
                             preferred_encoding=self.encoding)

#------------------------------------------------------------------------------
class MelLString(MelString):
    """Represents a mod record localized string."""
    def loadData(self, record, ins, sub_type, size_, readId):
        value = ins.readLString(size_, readId)
        record.__setattr__(self.attr,value)

#------------------------------------------------------------------------------
class MelStrings(MelString):
    """Represents array of strings."""

    def setDefault(self,record):
        record.__setattr__(self.attr,[])

    def getDefault(self):
        return []

    def loadData(self, record, ins, sub_type, size_, readId):
        value = ins.readStrings(size_, readId)
        record.__setattr__(self.attr,value)

    def dumpData(self,record,out):
        strings = record.__getattribute__(self.attr)
        if strings:
            out.packSub0(self.subType,null1.join(encode(x,firstEncoding=bolt.pluginEncoding) for x in strings)+null1)

#------------------------------------------------------------------------------
class MelStruct(MelBase):
    """Represents a structure record."""

    def __init__(self, subType, format, *elements):
        self.subType, self.format = subType, format
        self.attrs,self.defaults,self.actions,self.formAttrs = MelBase.parseElements(*elements)

    def getSlotsUsed(self):
        return self.attrs

    def hasFids(self,formElements):
        if self.formAttrs: formElements.add(self)

    def setDefault(self,record):
        setter = record.__setattr__
        for attr,value,action in zip(self.attrs, self.defaults, self.actions):
            if action: value = action(value)
            setter(attr,value)

    def loadData(self, record, ins, sub_type, size_, readId):
        unpacked = ins.unpack(self.format, size_, readId)
        setter = record.__setattr__
        for attr,value,action in zip(self.attrs,unpacked,self.actions):
            if action: value = action(value)
            setter(attr, value)

    def dumpData(self,record,out):
        values = []
        valuesAppend = values.append
        getter = record.__getattribute__
        for attr,action in zip(self.attrs,self.actions):
            value = getter(attr)
            if action: value = value.dump()
            valuesAppend(value)
        out.packSub(self.subType, self.format, *values)

    def mapFids(self,record,function,save=False):
        getter = record.__getattribute__
        setter = record.__setattr__
        for attr in self.formAttrs:
            result = function(getter(attr))
            if save: setter(attr,result)

    @property
    def static_size(self):
        return struct.calcsize(self.format)

#------------------------------------------------------------------------------
# Simple primitive type wrappers
class MelFloat(MelStruct):
    """Float. Wrapper around MelStruct to avoid having to constantly specify
    the format."""
    def __init__(self, signature, element):
        """:type signature: str"""
        MelStruct.__init__(self, signature, '=f', element)

class MelSInt8(MelStruct):
    """Signed 8-bit integer. Wrapper around MelStruct to avoid having to
    constantly specify the format."""
    def __init__(self, signature, element):
        """:type signature: str"""
        MelStruct.__init__(self, signature, '=b', element)

class MelSInt16(MelStruct):
    """Signed 16-bit integer. Wrapper around MelStruct to avoid having to
    constantly specify the format."""
    def __init__(self, signature, element):
        """:type signature: str"""
        MelStruct.__init__(self, signature, '=h', element)

class MelSInt32(MelStruct):
    """Signed 32-bit integer. Wrapper around MelStruct to avoid having to
    constantly specify the format."""
    def __init__(self, signature, element):
        """:type signature: str"""
        MelStruct.__init__(self, signature, '=i', element)

class MelUInt8(MelStruct):
    """Unsigned 8-bit integer. Wrapper around MelStruct to avoid having to
    constantly specify the format."""
    def __init__(self, signature, element):
        """:type signature: str"""
        MelStruct.__init__(self, signature, '=B', element)

class MelUInt16(MelStruct):
    """Unsigned 16-bit integer. Wrapper around MelStruct to avoid having to
    constantly specify the format."""
    def __init__(self, signature, element):
        """:type signature: str"""
        MelStruct.__init__(self, signature, '=H', element)

class MelUInt32(MelStruct):
    """Unsigned 32-bit integer. Wrapper around MelStruct to avoid having to
    constantly specify the format."""
    def __init__(self, signature, element):
        """:type signature: str"""
        MelStruct.__init__(self, signature, '=I', element)

#------------------------------------------------------------------------------
class MelOptStruct(MelStruct):
    """Represents an optional structure that is only dumped if at least one
    value is not equal to the default."""

    def dumpData(self, record, out):
        # TODO: Unfortunately, checking if the attribute is None is not
        # really effective.  Checking it to be 0,empty,etc isn't effective either.
        # It really just needs to check it against the default.
        recordGetAttr = record.__getattribute__
        for attr,default in zip(self.attrs,self.defaults):
            oldValue = recordGetAttr(attr)
            if oldValue is not None and oldValue != default:
                MelStruct.dumpData(self, record, out)
                break

#------------------------------------------------------------------------------
# 'Opt' versions of the type wrappers above
class MelOptFloat(MelOptStruct):
    """Optional float. Wrapper around MelOptStruct to avoid having to
    constantly specify the format."""
    def __init__(self, signature, element):
        """:type signature: str"""
        MelOptStruct.__init__(self, signature, '=f', element)

# Unused right now - keeping around for completeness' sake and to make future
# usage simpler.
class MelOptSInt8(MelOptStruct):
    """Optional signed 8-bit integer. Wrapper around MelOptStruct to avoid
    having to constantly specify the format."""
    def __init__(self, signature, element):
        """:type signature: str"""
        MelOptStruct.__init__(self, signature, '=b', element)

class MelOptSInt16(MelOptStruct):
    """Optional signed 16-bit integer. Wrapper around MelOptStruct to avoid
    having to constantly specify the format."""
    def __init__(self, signature, element):
        """:type signature: str"""
        MelOptStruct.__init__(self, signature, '=h', element)

class MelOptSInt32(MelOptStruct):
    """Optional signed 32-bit integer. Wrapper around MelOptStruct to avoid
    having to constantly specify the format."""
    def __init__(self, signature, element):
        """:type signature: str"""
        MelOptStruct.__init__(self, signature, '=i', element)

class MelOptUInt8(MelOptStruct):
    """Optional unsigned 8-bit integer. Wrapper around MelOptStruct to avoid
    having to constantly specify the format."""
    def __init__(self, signature, element):
        """:type signature: str"""
        MelOptStruct.__init__(self, signature, '=B', element)

class MelOptUInt16(MelOptStruct):
    """Optional unsigned 16-bit integer. Wrapper around MelOptStruct to avoid
    having to constantly specify the format."""
    def __init__(self, signature, element):
        """:type signature: str"""
        MelOptStruct.__init__(self, signature, '=H', element)

class MelOptUInt32(MelOptStruct):
    """Optional unsigned 32-bit integer. Wrapper around MelOptStruct to avoid
    having to constantly specify the format."""
    def __init__(self, signature, element):
        """:type signature: str"""
        MelOptStruct.__init__(self, signature, '=I', element)

class MelOptFid(MelOptUInt32):
    """Optional FormID. Wrapper around MelOptUInt32 to avoid having to
    constantly specify the format. Also supports specifying a default value."""
    _default_sentinel = object()

    def __init__(self, signature, attr, default_val=_default_sentinel):
        """:type signature: str
        :type attr: str"""
        if default_val is self._default_sentinel:
            MelOptUInt32.__init__(self, signature, (FID, attr))
        else:
            MelOptUInt32.__init__(self, signature, (FID, attr, default_val))
