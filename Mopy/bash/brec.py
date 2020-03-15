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

"""This module contains all of the basic types used to read ESP/ESM mod files.
"""
from __future__ import division, print_function
import cPickle as pickle  # PY3
import copy
import os
import re
import struct
import zlib
from operator import attrgetter

from . import bolt
from . import exception
from .bolt import decode, encode, sio, GPath, struct_pack, struct_unpack

# Util Functions --------------------------------------------------------------
#--Type coercion
def _coerce(value, newtype, base=None, AllowNone=False):
    try:
        if newtype is float:
            #--Force standard precision
            return round(struct_unpack('f', struct_pack('f', float(value)))[0], 6)
        elif newtype is bool:
            if isinstance(value,basestring):
                retValue = value.strip().lower()
                if AllowNone and retValue == u'none': return None
                return retValue not in (u'',u'none',u'false',u'no',u'0',u'0.0')
            else: return bool(value)
        elif base: retValue = newtype(value, base)
        elif newtype is unicode: retValue = decode(value)
        else: retValue = newtype(value)
        if (AllowNone and
            (isinstance(retValue,str) and retValue.lower() == 'none') or
            (isinstance(retValue,unicode) and retValue.lower() == u'none')
            ):
            return None
        return retValue
    except (ValueError,TypeError):
        if newtype is int: return 0
        return None

#--Reference (fid)
def strFid(fid):
    """Returns a string representation of the fid."""
    if isinstance(fid,tuple):
        return u'(%s, %06X)' % (fid[0].s,fid[1])
    else:
        return u'%08X' % fid

def genFid(modIndex,objectIndex):
    """Generates a fid from modIndex and ObjectIndex."""
    return int(objectIndex) | (int(modIndex) << 24)

def getModIndex(fid):
    """Returns the modIndex portion of a fid."""
    return int(fid >> 24)

def getObjectIndex(fid):
    """Returns the objectIndex portion of a fid."""
    return int(fid & 0x00FFFFFF)

def getFormIndices(fid):
    """Returns tuple of modIndex and ObjectIndex of fid."""
    return int(fid >> 24),int(fid & 0x00FFFFFF)

# Mod I/O ---------------------------------------------------------------------
#------------------------------------------------------------------------------
class RecordHeader(object):
    """Pack or unpack the record's header."""
    rec_header_size = 24 # Record header size, e.g. 20 for Oblivion
    # Record pack format, e.g. 4sIIII for Oblivion
    # Given as a list here, where each string matches one subrecord in the
    # header. See rec_pack_format_str below as well.
    rec_pack_format = ['=4s', 'I', 'I', 'I', 'I', 'I']
    # rec_pack_format as a format string. Use for pack / unpack calls.
    rec_pack_format_str = ''.join(rec_pack_format)
    # Format used by sub-record headers. Morrowind uses a different one.
    sub_header_fmt = u'=4sH'
    # Size of sub-record headers. Morrowind has a different one.
    sub_header_size = 6
    # http://en.uesp.net/wiki/Tes5Mod:Mod_File_Format#Groups
    pack_formats = {0: '=4sI4s3I'} # Top Type
    pack_formats.update({x: '=4s5I' for x in {1, 6, 7, 8, 9, 10}}) # Children
    pack_formats.update({x: '=4sIi3I' for x in {2, 3}})  # Interior Cell Blocks
    pack_formats.update({x: '=4sIhh3I' for x in {4, 5}}) # Exterior Cell Blocks

    #--Top types in order of the main ESM
    topTypes = []
    #--Record Types: all recognized record types (not just the top types)
    recordTypes = set()
    #--Plugin form version, we must pack this in the TES4 header
    plugin_form_version = 0

    def __init__(self, recType='TES4', size=0, arg1=0, arg2=0, arg3=0, arg4=0):
        """RecordHeader defining different sets of attributes based on recType
        is a huge smell and must be fixed. The fact that Oblivion has different
        unpack formats than other games adds to complexity - we need a proper
        class or better add __slots__ and iterate over them in pack. Both
        issues should be fixed at once.
        :param recType: signature of record
                      : For GRUP this is always GRUP
                      : For Records this will be TES4, GMST, KYWD, etc
        :param size : size of current record, not entire file
        :param arg1 : For GRUP type of records to follow, GMST, KYWD, etc
                    : For Records this is the record flags
        :param arg2 : For GRUP Group Type 0 to 10 see UESP Wiki
                    : Record FormID, TES4 records have FormID of 0
        :param arg3 : For GRUP 2h, possible time stamp, unknown
                    : Record possible version control in CK
        :param arg4 : For GRUP 0 for known mods (2h, form_version, unknown ?)
                    : For Records 2h, form_version, unknown
        """
        self.recType = recType
        self.size = size
        if self.recType == 'GRUP':
            self.label = arg1
            self.groupType = arg2
            self.stamp = arg3
        else:
            self.flags1 = arg1
            self.fid = arg2
            self.flags2 = arg3
        self.extra = arg4

    @staticmethod
    def unpack(ins):
        """Return a RecordHeader object by reading the input stream."""
        # args = rec_type, size, uint0, uint1, uint2[, uint3]
        args = ins.unpack(RecordHeader.rec_pack_format_str,
                          RecordHeader.rec_header_size, 'REC_HEADER')
        #--Bad type?
        rec_type = args[0]
        if rec_type not in RecordHeader.recordTypes:
            raise exception.ModError(ins.inName,
                                     u'Bad header type: ' + repr(rec_type))
        #--Record
        if rec_type != 'GRUP':
            pass
        #--Top Group
        elif args[3] == 0: #groupType == 0 (Top Type)
            args = list(args)
            str0 = struct_pack('I', args[2])
            if str0 in RecordHeader.topTypes:
                args[2] = str0
            else:
                raise exception.ModError(ins.inName,
                                         u'Bad Top GRUP type: ' + repr(str0))
        return RecordHeader(*args)

    def pack(self):
        """Return the record header packed into a bitstream to be written to
        file. We decide what kind of GRUP we have based on the type of
        label, hacky but to redo this we must revisit records code."""
        if self.recType == 'GRUP':
            if isinstance(self.label, str):
                pack_args = [RecordHeader.pack_formats[0], self.recType,
                             self.size, self.label, self.groupType, self.stamp]
            elif isinstance(self.label, tuple):
                pack_args = [RecordHeader.pack_formats[4], self.recType,
                             self.size, self.label[0], self.label[1],
                             self.groupType, self.stamp]
            else:
                pack_args = [RecordHeader.pack_formats[1], self.recType,
                             self.size, self.label, self.groupType, self.stamp]
            if RecordHeader.plugin_form_version:
                pack_args.append(self.extra)
        else:
            pack_args = [RecordHeader.rec_pack_format_str, self.recType,
                         self.size, self.flags1, self.fid, self.flags2]
            if RecordHeader.plugin_form_version:
                extra1, extra2 = struct_unpack('=2h',
                                               struct_pack('=I', self.extra))
                extra1 = RecordHeader.plugin_form_version
                self.extra = \
                    struct_unpack('=I', struct_pack('=2h', extra1, extra2))[0]
                pack_args.append(self.extra)
        return struct_pack(*pack_args)

    @property
    def form_version(self):
        if self.plugin_form_version == 0 : return 0
        return struct_unpack('=2h', struct_pack('=I', self.extra))[0]

    def __repr__(self):
        if self.recType == 'GRUP':
            return u'<GRUP Header: %s v%u>' % (self.label, self.form_version)
        else:
            return u'<Record Header: %s v%u>' % (strFid(self.fid),
                                                  self.form_version)

#------------------------------------------------------------------------------
class ModReader(object):
    """Wrapper around a TES4 file in read mode.
    Will throw a ModReaderror if read operation fails to return correct size.
    """

    def __init__(self,inName,ins):
        self.inName = inName
        self.ins = ins
        #--Get ins size
        curPos = ins.tell()
        ins.seek(0,os.SEEK_END)
        self.size = ins.tell()
        ins.seek(curPos)
        self.strings = {}
        self.hasStrings = False

    # with statement
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_value, exc_traceback): self.ins.close()

    def setStringTable(self, table):
        self.hasStrings = bool(table)
        self.strings = table or {} # table may be None

    #--I/O Stream -----------------------------------------
    def seek(self,offset,whence=os.SEEK_SET,recType='----'):
        """File seek."""
        if whence == os.SEEK_CUR:
            newPos = self.ins.tell() + offset
        elif whence == os.SEEK_END:
            newPos = self.size + offset
        else:
            newPos = offset
        if newPos < 0 or newPos > self.size:
            raise exception.ModReadError(self.inName, recType, newPos, self.size)
        self.ins.seek(offset,whence)

    def tell(self):
        """File tell."""
        return self.ins.tell()

    def close(self):
        """Close file."""
        self.ins.close()

    def atEnd(self,endPos=-1,recType='----'):
        """Return True if current read position is at EOF."""
        filePos = self.ins.tell()
        if endPos == -1:
            return filePos == self.size
        elif filePos > endPos:
            raise exception.ModError(self.inName, u'Exceeded limit of: ' + recType)
        else:
            return filePos == endPos

    #--Read/Unpack ----------------------------------------
    def read(self,size,recType='----'):
        """Read from file."""
        endPos = self.ins.tell() + size
        if endPos > self.size:
            raise exception.ModSizeError(self.inName, recType, (endPos,),
                                         self.size)
        return self.ins.read(size)

    def readLString(self,size,recType='----'):
        """Read translatible string.  If the mod has STRINGS file, this is a
        uint32 to lookup the string in the string table.  Otherwise, this is a
        zero-terminated string."""
        if self.hasStrings:
            if size != 4:
                endPos = self.ins.tell() + size
                raise exception.ModReadError(self.inName, recType, endPos, self.size)
            id_, = self.unpack('I',4,recType)
            if id_ == 0: return u''
            else: return self.strings.get(id_,u'LOOKUP FAILED!') #--Same as Skyrim
        else:
            return self.readString(size,recType)

    def readString32(self, recType='----'):
        """Read wide pascal string: uint32 is used to indicate length."""
        strLen, = self.unpack('I',4,recType)
        return self.readString(strLen,recType)

    def readString(self,size,recType='----'):
        """Read string from file, stripping zero terminator."""
        return u'\n'.join(decode(x,bolt.pluginEncoding,avoidEncodings=('utf8','utf-8')) for x in
                          bolt.cstrip(self.read(size,recType)).split('\n'))

    def readStrings(self,size,recType='----'):
        """Read strings from file, stripping zero terminator."""
        return [decode(x,bolt.pluginEncoding,avoidEncodings=('utf8','utf-8')) for x in
                self.read(size,recType).rstrip(null1).split(null1)]

    def unpack(self,format,size,recType='----'):
        """Read file and unpack according to struct format."""
        endPos = self.ins.tell() + size
        if endPos > self.size:
            raise exception.ModReadError(self.inName, recType, endPos, self.size)
        return struct_unpack(format, self.ins.read(size))

    def unpackRef(self):
        """Read a ref (fid)."""
        return self.unpack('I',4)[0]

    def unpackRecHeader(self): return RecordHeader.unpack(self)

    def unpackSubHeader(self,recType='----',expType=None,expSize=0):
        """Unpack a subrecord header.  Optionally checks for match with expected
        type and size."""
        selfUnpack = self.unpack
        (rec_type, size) = selfUnpack(RecordHeader.sub_header_fmt,
                                      RecordHeader.sub_header_size,
                                      recType + u'.SUB_HEAD')
        #--Extended storage?
        while rec_type == 'XXXX':
            size = selfUnpack('I',4,recType+'.XXXX.SIZE.')[0]
            # Throw away size here (always == 0)
            rec_type = selfUnpack(RecordHeader.sub_header_fmt,
                                  RecordHeader.sub_header_size,
                                  recType + u'.XXXX.TYPE')[0]
        #--Match expected name?
        if expType and expType != rec_type:
            raise exception.ModError(self.inName, u'%s: Expected %s subrecord, but '
                           u'found %s instead.' % (recType, expType, rec_type))
        #--Match expected size?
        if expSize and expSize != size:
            raise exception.ModSizeError(self.inName, recType + '.' + rec_type,
                                         (expSize,), size)
        return rec_type,size

#------------------------------------------------------------------------------
class ModWriter(object):
    """Wrapper around a TES4 output stream.  Adds utility functions."""
    def __init__(self,out):
        self.out = out

    # with statement
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_value, exc_traceback): self.out.close()

    #--Stream Wrapping ------------------------------------
    def write(self,data): self.out.write(data)
    def tell(self): return self.out.tell()
    def seek(self,offset,whence=os.SEEK_SET): return self.out.seek(offset,whence)
    def getvalue(self): return self.out.getvalue()
    def close(self): self.out.close()

    #--Additional functions -------------------------------
    def pack(self,format,*data):
        self.out.write(struct_pack(format, *data))

    def packSub(self, sub_rec_type, data, *values):
        """Write subrecord header and data to output stream.
        Call using either packSub(sub_rec_type,data) or
        packSub(sub_rec_type,format,values).
        Will automatically add a prefacing XXXX size subrecord to handle data
        with size > 0xFFFF."""
        try:
            if data is None: return
            if values: data = struct_pack(data, *values)
            outWrite = self.out.write
            lenData = len(data)
            if lenData <= 0xFFFF:
                outWrite(struct_pack(RecordHeader.sub_header_fmt, sub_rec_type,
                                     lenData))
            else:
                outWrite(struct_pack('=4sHI', 'XXXX', 4, lenData))
                outWrite(struct_pack(RecordHeader.sub_header_fmt, sub_rec_type,
                                     0))
            outWrite(data)
        except Exception:
            bolt.deprint(u'%r: Failed packing: %s, %s, %s' % (
                self, sub_rec_type, data, values), traceback=True)

    def packSub0(self, sub_rec_type, data):
        """Write subrecord header plus zero terminated string to output
        stream."""
        if data is None: return
        elif isinstance(data,unicode):
            data = encode(data,firstEncoding=bolt.pluginEncoding)
        lenData = len(data) + 1
        outWrite = self.out.write
        if lenData < 0xFFFF:
            outWrite(struct_pack(RecordHeader.sub_header_fmt, sub_rec_type,
                                 lenData))
        else:
            outWrite(struct_pack('=4sHI', 'XXXX', 4, lenData))
            outWrite(struct_pack(RecordHeader.sub_header_fmt, sub_rec_type, 0))
        outWrite(data)
        outWrite('\x00')

    def packRef(self, sub_rec_type, fid):
        """Write subrecord header and fid reference."""
        if fid is not None:
            self.out.write(struct_pack('=4sHI', sub_rec_type, 4, fid))

    def writeGroup(self,size,label,groupType,stamp):
        if type(label) is str:
            self.pack('=4sI4sII','GRUP',size,label,groupType,stamp)
        elif type(label) is tuple:
            self.pack('=4sIhhII','GRUP',size,label[1],label[0],groupType,stamp)
        else:
            self.pack('=4s4I','GRUP',size,label,groupType,stamp)

    def write_string(self, sub_type, string_val, max_size=0, min_size=0,
                     preferred_encoding=None):
        """Writes out a string subrecord, properly encoding it beforehand and
        respecting max_size, min_size and preferred_encoding if they are
        set."""
        self.packSub0(sub_type, bolt.encode_complex_string(
            string_val, max_size, min_size, preferred_encoding))

#------------------------------------------------------------------------------
# Mod Record Elements ---------------------------------------------------------

# Constants
# Used by MelStruct classes to indicate fid elements.
FID = 'FID'
# Null strings (for default empty byte arrays)
null1 = '\x00'
null2 = null1 * 2
null3 = null1 * 3
null4 = null1 * 4

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

#-----------------------------------------------------------------------------
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
        :type couns: str"""
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
        :type couns: str"""
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
class MelSortedFidList(MelFidList):
    """MelFidList that sorts the order of the Fids before writing them. They
    are not sorted after modification, only just prior to writing."""

    def __init__(self, subType, attr, sortKeyFn=lambda x: x, default=None):
        """sortKeyFn - function to pass to list.sort(key = ____) to sort the FidList
           just prior to writing.  Since the FidList will already be converted to short Fids
           at this point we're sorting 4-byte values,  not (FileName, 3-Byte) tuples."""
        MelFidList.__init__(self, subType, attr, default)
        self.sortKeyFn = sortKeyFn

    def dumpData(self, record, out):
        fids = record.__getattribute__(self.attr)
        if not fids: return
        fids.sort(key=self.sortKeyFn)
        # NOTE: fids.sort sorts from lowest to highest, so lowest values FormID will sort first
        #       if it should be opposite, use this instead:
        #  fids.sort(key=self.sortKeyFn, reverse=True)
        out.packSub(self.subType, repr(len(fids)) + 'I', *fids)

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
class MelBounds(MelGroup):
    """Wrapper around MelGroup for the common task of defining OBND - Object
    Bounds. Uses MelGroup to avoid merging them when importing."""
    def __init__(self):
        MelGroup.__init__(self, 'bounds',
            MelStruct('OBND', '=6h', 'boundX1', 'boundY1', 'boundZ1',
                      'boundX2', 'boundY2', 'boundZ2')
        )

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
# Unions and Deciders
class ADecider(object):
    """A decider returns one of several possible values when called, based on
    parameters such as the record instance, sub type, or record size. See
    MelUnion's docstring for more information."""
    # Set this to True if your decider can handle a decide_dump call -
    # otherwise, the result of decide_load will be stored and reused during
    # dumpData, if that is possible. If not (e.g. for a newly created record),
    # then the union will pick some element in its dict - no guarantees made.
    can_decide_at_dump = False

    def decide_load(self, record, ins, sub_type, rec_size):
        """Called during loadData.

        :param record: The record instance we're assigning attributes to.
        :param ins: The ModReader instance used to read the record.
        :type ins: ModReader
        :param sub_type: The four-character subrecord signature.
        :type sub_type: str
        :param rec_size: The total size of the subrecord.
        :type rec_size: int
        :return: Any value this decider deems fitting for the parameters it is
            given."""
        raise exception.AbstractError()

    def decide_dump(self, record):
        """Called during dumpData.

        :param record: The record instance we're reading attributes from.
        :return: Any value this decider deems fitting for the parameters it is
            given."""
        if self.__class__.can_decide_at_dump:
            raise exception.AbstractError()

class ACommonDecider(ADecider):
    """Abstract class for deciders that can decide at both load and dump-time,
    based only on the record. Provides a single method, _decide_common, that
    the subclass has to implement."""
    can_decide_at_dump = True

    def decide_load(self, record, ins, sub_type, rec_size):
        return self._decide_common(record)

    def decide_dump(self, record):
        return self._decide_common(record)

    def _decide_common(self, record):
        """Performs the actual decisions for both loading and dumping."""
        raise exception.AbstractError()

class AttrExistsDecider(ACommonDecider):
    """Decider that returns True if an attribute with the specified name is
    present on the record."""
    def __init__(self, target_attr):
        """Creates a new AttrExistsDecider with the specified attribute.

        :param target_attr: The name of the attribute to check.
        :type target_attr: str"""
        self.target_attr = target_attr

    def _decide_common(self, record):
        return hasattr(record, self.target_attr)

class AttrValDecider(ACommonDecider):
    """Decider that returns an attribute value (may optionally apply a function
    to it first)."""
    # Internal sentinel value used for the assign_missing argument
    _assign_missing_sentinel = object()

    def __init__(self, target_attr, transformer=None,
                 assign_missing=_assign_missing_sentinel):
        """Creates a new AttrValDecider with the specified attribute and
        optional arguments.

        :param target_attr: The name of the attribute to return the value
            for.
        :type target_attr: str
        :param transformer: A function that takes a single argument, the value
            read from target_attr, and returns some other value. Can be used to
            e.g. return only the first character of an eid.
        :param assign_missing: Normally, an AttributeError is raised if the
            record does not have target_attr. If this is anything other than
            the sentinel value, an error will not be raised and this will be
            returned instead."""
        self.target_attr = target_attr
        self.transformer = transformer
        self.assign_missing = assign_missing

    def _decide_common(self, record):
        if self.assign_missing is not self._assign_missing_sentinel:
            # We have a valid assign_missing, default to it
            ret_val = getattr(record, self.target_attr, self.assign_missing)
        else:
            # Raises an AttributeError if target_attr is missing
            ret_val = getattr(record, self.target_attr)
        if self.transformer:
            ret_val = self.transformer(ret_val)
        return ret_val

class FlagDecider(ACommonDecider):
    """Decider that checks if certain flags are set."""
    def __init__(self, flags_attr, *required_flags):
        """Creates a new FlagDecider with the specified flag attribute and
        required flag names.

        :param flags_attr: The attribute that stores the flag value.
        :param required_flags: The names of all flags that have to be set."""
        self._flags_attr = flags_attr
        self._required_flags = required_flags

    def _decide_common(self, record):
        flags_val = getattr(record, self._flags_attr)
        check_flag = flags_val.__getattr__
        return all(check_flag(flag_name) for flag_name in self._required_flags)

class GameDecider(ACommonDecider):
    """Decider that returns the name of the currently managed game."""
    def __init__(self):
        from . import bush
        self.game_fsName = bush.game.fsName

    def _decide_common(self, record):
        return self.game_fsName

class PartialLoadDecider(ADecider):
    """Partially loads a subrecord using a given loader, then rewinds the
    input stream and delegates to a given decider. Can decide at dump-time
    iff the given decider can as well."""
    def __init__(self, loader, decider):
        """Constructs a new PartialLoadDecider with the specified loader and
        decider.

        :param loader: The MelStruct instance to use for loading.
        :type loader: MelStruct
        :param decider: The decider to use after loading.
        :type decider: ADecider"""
        self._loader = loader
        # A bit hacky, but we need MelStruct to assign the attributes
        self._load_size = struct.calcsize(loader.format)
        self._decider = decider
        # This works because MelUnion._get_element_from_record does not use
        # self.__class__ to access can_decide_at_dump
        self.can_decide_at_dump = decider.can_decide_at_dump

    def decide_load(self, record, ins, sub_type, rec_size):
        starting_pos = ins.tell()
        # Make a deep copy so that no modifications from this decision will
        # make it to the actual record
        target = copy.deepcopy(record)
        self._loader.loadData(target, ins, sub_type, self._load_size,
                             'DECIDER.' + sub_type)
        ins.seek(starting_pos)
        # Use the modified record here to make the temporary changes visible to
        # the delegate decider
        return self._decider.decide_load(target, ins, sub_type, rec_size)

    def decide_dump(self, record):
        if not self.can_decide_at_dump:
            raise exception.AbstractError()
        # We can simply delegate here without doing anything else, since the
        # record has to have been loaded since then
        return self._decider.decide_dump(record)

class SaveDecider(ADecider):
    """Decider that returns True if the input file is a save."""
    def __init__(self):
        from . import bush
        self._save_ext = bush.game.Ess.ext

    def decide_load(self, record, ins, sub_type, rec_size):
        return ins.inName.cext == self._save_ext

class SignatureDecider(ADecider):
    """Very simple decider that just returns the subrecord type (aka
    signature). This is the default decider used by MelUnion."""
    def decide_load(self, record, ins, sub_type, rec_size):
        return sub_type

class SizeDecider(ADecider):
    """Decider that returns the size of the target subrecord."""
    def decide_load(self, record, ins, sub_type, rec_size):
        return rec_size

class MelUnion(MelBase):
    """Resolves to one of several record elements based on an ADecider.
    Defaults to a SignatureDecider.

    The decider is queried for a value, which is then used to perform a lookup
    in the element_mapping dict passed in. For example, consider this MelUnion,
    which showcases all features:
        MelUnion({
            'b': MelStruct('DATA', 'I', 'value'),
            'f': MelStruct('DATA', 'f', 'value'),
            's': MelLString('DATA', 'value'),
        }, decider=AttrValDecider(
            'eid', lambda eid: eid[0] if eid else 'i'),
            fallback=MelStruct('DATA', 'i', 'value')
        ),
    When a DATA subrecord is encountered, the union is asked to load it. It
    queries its decider, which in this case reads the 'eid' attribute (i.e. the
    EDID subrecord) and returns the first character of that attribute's value,
    defaulting to 'i' if it's empty. The union then looks up the returned value
    in its mapping. If it finds it (e.g. if it's 'b'), then it will delegate
    loading to the MelBase-derived object mapped to that value. Otherwise, it
    will check if a fallback element is available. If it is, then that one is
    used. Otherwise, an ArgumentError is raised.

    When dumping and mapping fids, a similar process occurs. The decider is
    asked if it is capable of deciding with the (more limited) information
    available at this time. If it can, it is queried and the result is once
    again used to look up in the mapping. If, however, the decider can't decide
    at this time, the union looks if this is a newly created record or one that
    has been read. In the former case, it just picks an arbitrary element to
    dump out. In the latter case, it reuses the previous decider result to look
    up the mapping.

    Note: This class does not (and likely won't ever be able to) support
    getDefaulters / getDefault."""
    # Incremented every time we construct a MelUnion - ensures we always make
    # unique attributes on the records
    _union_index = 0

    def __init__(self, element_mapping, decider=SignatureDecider(),
                 fallback=None):
        """Creates a new MelUnion with the specified element mapping and
        optional parameters. See the class docstring for extensive information
        on MelUnion usage.

        :param element_mapping: The element mapping.
        :type element_mapping: dict[object, MelBase]
        :param decider: An ADecider instance to use. Defaults to
            SignatureDecider.
        :type decider: ADecider
        :param fallback: The fallback element to use. Defaults to None, which
            will raise an error if the decider returns an unknown value.
        :type fallback: MelBase"""
        self.element_mapping = element_mapping
        self.fid_elements = set()
        if not isinstance(decider, ADecider):
            raise exception.ArgumentError(u'decider must be an ADecider')
        self.decider = decider
        self.decider_result_attr = '_union_type_%u' % MelUnion._union_index
        MelUnion._union_index += 1
        self.fallback = fallback
        self._possible_sigs = {s for element
                               in self.element_mapping.itervalues()
                               for s in element.signatures}

    def _get_element(self, decider_ret):
        """Retrieves the fitting element from element_mapping for the
        specified decider result.

        :param decider_ret: The result of the decide_* method that was
            invoked.
        :return: The matching record element to use."""
        element = self.element_mapping.get(decider_ret, self.fallback)
        if not element:
            raise exception.ArgumentError(
                u'Specified element mapping did not handle a decider return '
                u'value (%r) and there is no fallback' % decider_ret)
        return element

    def _get_element_from_record(self, record):
        """Retrieves the fitting element based on the specified record instance
        only. Small wrapper around _get_element to share code between dumpData
        and mapFids.

        :param record: The record instance we're dealing with.
        :return: The matching record element to use."""
        if self.decider.can_decide_at_dump:
            # If the decider can decide at dump-time, let it
            return self._get_element(self.decider.decide_dump(record))
        elif not hasattr(record, self.decider_result_attr):
            # We're dealing with a record that was just created, but the
            # decider can't be used - default to some element
            return next(self.element_mapping.itervalues())
        else:
            # We can use the result we decided earlier
            return self._get_element(
                getattr(record, self.decider_result_attr))

    def getSlotsUsed(self):
        # We need to reserve every possible slot, since we can't know what
        # we'll resolve to yet. Use a set to avoid duplicates.
        slots_ret = {self.decider_result_attr}
        for element in self.element_mapping.itervalues():
            slots_ret.update(element.getSlotsUsed())
        return tuple(slots_ret)

    def getLoaders(self, loaders):
        # We need to collect all signatures and assign ourselves for them all
        # to handle unions with different signatures
        temp_loaders = {}
        for element in self.element_mapping.itervalues():
            element.getLoaders(temp_loaders)
        for signature in temp_loaders.keys():
            loaders[signature] = self

    def hasFids(self, formElements):
        # Ask each of our elements, and remember the ones where we'd have to
        # actually forward the mapFids call. We can't just blindly call
        # mapFids, since MelBase.mapFids is abstract.
        for element in self.element_mapping.itervalues():
            temp_elements = set()
            element.hasFids(temp_elements)
            if temp_elements:
                self.fid_elements.add(element)
        if self.fid_elements: formElements.add(self)

    def setDefault(self, record):
        # Ask each element - but we *don't* want to set our _union_type
        # attributes here! If we did, then we'd have no way to distinguish
        # between a loaded and a freshly constructed record.
        for element in self.element_mapping.itervalues():
            element.setDefault(record)

    def mapFids(self, record, function, save=False):
        element = self._get_element_from_record(record)
        if element in self.fid_elements:
            element.mapFids(record, function, save)

    def loadData(self, record, ins, sub_type, size_, readId):
        # Ask the decider, and save the result for later - even if the decider
        # can decide at dump-time! Some deciders may want to have this as a
        # backup if they can't deliver a high-quality result.
        decider_ret = self.decider.decide_load(record, ins, sub_type, size_)
        setattr(record, self.decider_result_attr, decider_ret)
        self._get_element(decider_ret).loadData(record, ins, sub_type, size_,
                                                readId)

    def dumpData(self, record, out):
        self._get_element_from_record(record).dumpData(record, out)

    @property
    def signatures(self):
        return self._possible_sigs

    @property
    def static_size(self):
        stat_size = next(self.element_mapping.itervalues()).static_size
        if any(element.static_size != stat_size for element
               in self.element_mapping.itervalues()):
            raise exception.AbstractError() # The sizes are not all identical
        return stat_size

#------------------------------------------------------------------------------
class MelReferences(MelGroups):
    """Handles mixed sets of SCRO and SCRV for scripts, quests, etc."""
    def __init__(self):
        MelGroups.__init__(self, 'references', MelUnion({
            'SCRO': MelFid('SCRO', 'reference'),
            'SCRV': MelUInt32('SCRV', 'reference'),
        }))

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

    def __init__(self, subType, format, *elements, **kwdargs):
        dumpExtra = kwdargs.get('dumpExtra', None)
        self.subType, self.format = subType, format
        self.attrs,self.defaults,self.actions,self.formAttrs = MelBase.parseElements(*elements)
        if dumpExtra:
            self.attrs += (dumpExtra,)
            self.defaults += ('',)
            self.actions += (None,)
            self.formatLen = struct.calcsize(format)
        else:
            self.formatLen = -1

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
        readsize = self.formatLen if self.formatLen >= 0 else size_
        unpacked = ins.unpack(self.format,readsize,readId)
        setter = record.__setattr__
        for attr,value,action in zip(self.attrs,unpacked,self.actions):
            if action: value = action(value)
            setter(attr, value)
        if self.formatLen >= 0:
            # Dump remaining subrecord data into an attribute
            setter(self.attrs[-1], ins.read(size_ - self.formatLen))

    def dumpData(self,record,out):
        values = []
        valuesAppend = values.append
        getter = record.__getattribute__
        for attr,action in zip(self.attrs,self.actions):
            value = getter(attr)
            if action: value = value.dump()
            valuesAppend(value)
        if self.formatLen >= 0:
            extraLen = len(values[-1])
            format = self.format + repr(extraLen) + 's'
        else:
            format = self.format
        try:
            out.packSub(self.subType,format,*values)
        except struct.error:
            bolt.deprint(u'Failed to dump struct: %s (%r)' % (
                self.subType, self))
            raise

    def mapFids(self,record,function,save=False):
        getter = record.__getattribute__
        setter = record.__setattr__
        for attr in self.formAttrs:
            result = function(getter(attr))
            if save: setter(attr,result)

    @property
    def static_size(self):
        # dumpExtra means we can't know the size
        if self.formatLen == -1:
            return struct.calcsize(self.format)
        raise exception.AbstractError()

#------------------------------------------------------------------------------
class MelArray(MelBase):
    """Represents a single subrecord that consists of multiple fixed-size
    components. Note that only elements that properly implement static_size
    and fulfill len(self.signatures) == 1, i.e. ones that have a static size
    and resolve to only a single signature, can be used."""
    ##: MelFidList could be replaced with MelArray(MelFid), but that changes
    # the format of the generated attribute - rewriting usages is likely tough
    def __init__(self, array_attr, element):
        """Creates a new MelArray with the specified attribute and element.

        :param array_attr: The attribute name to give the entire array.
        :type array_attr: str
        :param element: The element that each entry in this array will be
            loaded and dumped by.
        :type element: MelBase"""
        try:
            self._element_size = element.static_size
        except exception.AbstractError:
            raise SyntaxError(u'MelArray may only be used with elements that '
                              u'have a static size')
        if len(element.signatures) != 1:
            raise SyntaxError(u'MelArray may only be used with elements that '
                              u'resolve to exactly one signature')
        # Use this instead of element.subType to support e.g. unions
        MelBase.__init__(self, next(iter(element.signatures)), array_attr)
        self._element = element
        # Underscore means internal usage only - e.g. distributor state
        self._element_attrs = [s for s in element.getSlotsUsed()
                              if not s.startswith('_')]

    class _DirectModWriter(ModWriter):
        """ModWriter that does not write out any subrecord headers."""
        def packSub(self, sub_rec_type, data, *values):
            if data is None: return
            if values: data = struct_pack(data, *values)
            self.out.write(data)

        def packSub0(self, sub_rec_type, data):
            self.out.write(data)
            self.out.write('\x00')

        def packRef(self, sub_rec_type, fid):
            if fid is not None: self.pack('I', fid)

    def hasFids(self, formElements):
        temp_elements = set()
        self._element.hasFids(temp_elements)
        if temp_elements: formElements.add(self)

    def setDefault(self, record):
        setattr(record, self.attr, [])

    def mapFids(self,record,function,save=False):
        array_val = getattr(record, self.attr)
        if array_val:
            map_entry = self._element.mapFids
            for arr_entry in array_val:
                map_entry(arr_entry, function, save)

    def loadData(self, record, ins, sub_type, size_, readId):
        append_entry = getattr(record, self.attr).append
        entry_slots = self._element_attrs
        entry_size = self._element_size
        load_entry = self._element.loadData
        for x in xrange(size_ // entry_size):
            arr_entry = MelObject()
            append_entry(arr_entry)
            arr_entry.__slots__ = entry_slots
            load_entry(arr_entry, ins, sub_type, entry_size, readId)

    def dumpData(self, record, out):
        array_val = getattr(record, self.attr)
        if not array_val: return # don't dump out empty arrays
        array_data = MelArray._DirectModWriter(sio())
        dump_entry = self._element.dumpData
        for arr_entry in array_val:
            dump_entry(arr_entry, array_data)
        out.packSub(self.subType, array_data.getvalue())

#------------------------------------------------------------------------------
class MelTruncatedStruct(MelStruct):
    """Works like a MelStruct, but automatically upgrades certain older,
    truncated struct formats."""
    def __init__(self, sub_sig, sub_fmt, *elements, **kwargs):
        """Creates a new MelTruncatedStruct with the specified parameters.

        :param sub_sig: The subrecord signature of this struct.
        :param sub_fmt: The format of this struct.
        :param elements: The element syntax of this struct. Passed to
            MelStruct.parseElements, see that method for syntax explanations.
        :param kwargs: Must contain an old_versions keyword argument, which
            specifies the older formats that are supported by this struct. The
            keyword argument is_optional can be supplied, which determines
            whether or not this struct should behave like MelOptStruct. May
            also contain any keyword arguments that MelStruct supports."""
        try:
            old_versions = kwargs.pop('old_versions')
        except KeyError:
            raise SyntaxError(u'MelTruncatedStruct requires an old_versions '
                              u'keyword argument')
        if type(old_versions) != set:
            raise SyntaxError(u'MelTruncatedStruct: old_versions must be a '
                              u'set')
        self._is_optional = kwargs.pop('is_optional', False)
        MelStruct.__init__(self, sub_sig, sub_fmt, *elements, **kwargs)
        self._all_formats = {struct.calcsize(alt_fmt): alt_fmt for alt_fmt
                             in old_versions}
        self._all_formats[struct.calcsize(sub_fmt)] = sub_fmt

    def loadData(self, record, ins, sub_type, size_, readId):
        # Try retrieving the format - if not possible, wrap the error to make
        # it more informative
        try:
            target_fmt = self._all_formats[size_]
        except KeyError:
            raise exception.ModSizeError(
                ins.inName, readId, tuple(self._all_formats.keys()), size_)
        # Actually unpack the struct and pad it with defaults if it's an older,
        # truncated version
        unpacked_val = ins.unpack(target_fmt, size_, readId)
        unpacked_val = self._pre_process_unpacked(unpacked_val)
        # Apply any actions and then set the attributes according to the values
        # we just unpacked
        setter = record.__setattr__
        for attr, value, action in zip(self.attrs, unpacked_val, self.actions):
            if callable(action): value = action(value)
            setter(attr, value)

    def _pre_process_unpacked(self, unpacked_val):
        """You may override this if you need to change the unpacked value in
        any way before it is used to assign attributes. By default, this
        performs the actual upgrading by appending default values to
        unpacked_val."""
        return unpacked_val + self.defaults[len(unpacked_val):]

    def dumpData(self, record, out):
        if self._is_optional:
            # If this struct is optional, compare the current values to the
            # defaults and skip the dump conditionally - basically the same
            # thing MelOptStruct does
            record_get_attr = record.__getattribute__
            for attr, default in zip(self.attrs, self.defaults):
                curr_val = record_get_attr(attr)
                if curr_val is not None and curr_val != default:
                    break
            else:
                return
        MelStruct.dumpData(self, record, out)

    @property
    def static_size(self):
        raise exception.AbstractError()

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
#-- Common/Special Elements
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
# Hack for allowing record imports from parent games - set per game
MelModel = None # type: type

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
# Mod Element Sets ------------------------------------------------------------
#------------------------------------------------------------------------------
class MelSet(object):
    """Set of mod record elments."""

    def __init__(self,*elements):
        self.elements = elements
        self.defaulters = {}
        self.loaders = {}
        self.formElements = set()
        self.firstFull = None
        for element in self.elements:
            element.getDefaulters(self.defaulters,'')
            element.getLoaders(self.loaders)
            element.hasFids(self.formElements)

    def getSlotsUsed(self):
        """This function returns all of the attributes used in record instances that use this instance."""
        return [s for element in self.elements for s in element.getSlotsUsed()]

    def initRecord(self, record, header, ins, do_unpack):
        """Initialize record, setting its attributes based on its elements."""
        for element in self.elements:
            element.setDefault(record)
        MreRecord.__init__(record, header, ins, do_unpack)

    def getDefault(self,attr):
        """Returns default instance of specified instance. Only useful for
        MelGroup and MelGroups."""
        return self.defaulters[attr].getDefault()

    def loadData(self,record,ins,endPos):
        """Loads data from input stream. Called by load()."""
        rec_type = record.recType
        loaders = self.loaders
        # Load each subrecord
        ins_at_end = ins.atEnd
        load_sub_header = ins.unpackSubHeader
        read_id_prefix = rec_type + '.'
        while not ins_at_end(endPos, rec_type):
            sub_type, sub_size = load_sub_header(rec_type)
            try:
                loaders[sub_type].loadData(record, ins, sub_type, sub_size,
                                           read_id_prefix + sub_type)
            except KeyError:
                # Wrap this error to make it more understandable
                self._handle_load_error(
                    exception.ModError(
                        ins.inName, u'Unexpected subrecord: %s' % (
                                read_id_prefix + sub_type)),
                    record, ins, sub_type, sub_size)
            except Exception as error:
                self._handle_load_error(error, record, ins, sub_type, sub_size)

    def _handle_load_error(self, error, record, ins, sub_type, sub_size):
        eid = getattr(record, 'eid', u'<<NO EID>>')
        bolt.deprint(u'Error loading %r record and/or subrecord: %08X' %
                     (record.recType, record.fid))
        bolt.deprint(u'  eid = %r' % eid)
        bolt.deprint(u'  subrecord = %r' % sub_type)
        bolt.deprint(u'  subrecord size = %d' % sub_size)
        bolt.deprint(u'  file pos = %d' % ins.tell())
        raise error

    def dumpData(self,record, out):
        """Dumps state into out. Called by getSize()."""
        for element in self.elements:
            try:
                element.dumpData(record,out)
            except:
                bolt.deprint(u'Error dumping data: ', traceback=True)
                bolt.deprint(u'Occurred while dumping '
                             u'<%(eid)s[%(signature)s:%(fid)s]>' % {
                    u'signature': record.recType,
                    u'fid': strFid(record.fid),
                    u'eid': (record.eid + u' ' if hasattr(record, 'eid')
                             and record.eid is not None else u''),
                })
                for attr in record.__slots__:
                    if hasattr(record, attr):
                        bolt.deprint(u'> %s: %s' % (
                            attr, repr(getattr(record, attr))))
                raise

    def mapFids(self,record,mapper,save=False):
        """Maps fids of subelements."""
        for element in self.formElements:
            element.mapFids(record,mapper,save)

    def convertFids(self,record, mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if converting to short format."""
        if record.longFids == toLong: return
        record.fid = mapper(record.fid)
        for element in self.formElements:
            element.mapFids(record,mapper,True)
        record.longFids = toLong
        record.setChanged()

    def updateMasters(self,record,masters):
        """Updates set of master names according to masters actually used."""
        if not record.longFids: raise exception.StateError("Fids not in long format")
        def updater(fid):
            masters.add(fid)
        updater(record.fid)
        for element in self.formElements:
            element.mapFids(record,updater)

    def with_distributor(self, distributor_config):
        # type: (dict) -> MelSet
        """Adds a distributor to this MelSet. See _MelDistributor for more
        information. Convenience method that avoids having to import and
        explicitly construct a _MelDistributor. This is supposed to be chained
        immediately after MelSet.__init__.

        :param distributor_config: The config to pass to the distributor.
        :return: self, for ease of construction."""
        # Make a copy, that way one distributor config can be used for multiple
        # record classes. _MelDistributor may modify its parameter, so not
        # making a copy wouldn't be safe in such a scenario.
        distributor = _MelDistributor(distributor_config.copy())
        self.elements += (distributor,)
        distributor.getLoaders(self.loaders)
        distributor.set_mel_set(self)
        return self

#------------------------------------------------------------------------------
class _MelDistributor(MelNull):
    """Implements a distributor that can handle duplicate record signatures.
    See the wiki page '[dev] Plugin Format: Distributors' for a detailed
    overview of this class and the semi-DSL it implements.

    :type _attr_to_loader: dict[str, MelBase]
    :type _sig_to_loader: dict[str, MelBase]
    :type _target_sigs: set[str]"""
    def __init__(self, distributor_config): # type: (dict) -> None
        # Maps attribute name to loader
        self._attr_to_loader = {}
        # Maps subrecord signature to loader
        self._sig_to_loader = {}
        # All signatures that this distributor targets
        self._target_sigs = set()
        self.distributor_config = distributor_config
        # Validate that the distributor config we were given has valid syntax
        # and resolve any shortcuts (e.g. the A|B syntax)
        self._pre_process()

    def _raise_syntax_error(self, error_msg):
        raise SyntaxError(u'Invalid distributor syntax: %s' % error_msg)

    def _pre_process(self):
        """Ensures that the distributor config defined above has correct syntax
        and resolves shortcuts (e.g. A|B syntax)."""
        if type(self.distributor_config) != dict:
            self._raise_syntax_error(
                u'distributor_config must be a dict (actual type: %s)' %
                type(self.distributor_config))
        mappings_to_iterate = [self.distributor_config] # TODO(inf) Proper name for dicts / mappings (scopes?)
        while mappings_to_iterate:
            mapping = mappings_to_iterate.pop()
            for signature_str in mapping.keys():
                if type(signature_str) != str:
                    self._raise_syntax_error(
                        u'All keys must be signature strings (offending key: '
                        u'%r)' % signature_str)
                # Resolve 'A|B' syntax
                signatures = signature_str.split('|')
                resolved_entry = mapping[signature_str]
                if not resolved_entry:
                    self._raise_syntax_error(
                        u'Mapped values may not be empty (offending value: '
                        u'%s)' % resolved_entry)
                # Delete the 'A|B' entry, not needed anymore
                del mapping[signature_str]
                for signature in signatures:
                    if len(signature) != 4:
                        self._raise_syntax_error(
                            u'Signature strings must have length 4 (offending '
                            u'string: %s)' % signature)
                    if signature in mapping:
                        self._raise_syntax_error(
                            u'Duplicate signature string (offending string: '
                            u'%s)' % signature)
                    # For each option in A|B|..|Z, make a new entry
                    mapping[signature] = resolved_entry
                re_type = type(resolved_entry)
                if re_type == dict:
                    # If the signature maps to a dict, recurse into it
                    mappings_to_iterate.append(resolved_entry)
                elif re_type == tuple:
                    # TODO(inf) Proper name for tuple values
                    if (len(resolved_entry) != 2
                            or type(resolved_entry[0]) != str
                            or type(resolved_entry[1]) != dict):
                        self._raise_syntax_error(
                            u'Tuples used as values must always have two '
                            u'elements - an attribute string and a dict '
                            u'(offending tuple: %r)' % resolved_entry)
                    # If the signature maps to a tuple, recurse into the
                    # dict stored in its second element
                    mappings_to_iterate.append(resolved_entry[1])
                elif re_type == list:
                    # If the signature maps to a list, ensure that each entry
                    # is correct
                    for seq_entry in resolved_entry:
                        if type(seq_entry) == tuple:
                            # Ensure that the tuple is correctly formatted
                            if (len(seq_entry) != 2
                                    or type(seq_entry[0]) != str
                                    or type(seq_entry[1]) != str):
                                self._raise_syntax_error(
                                    u'Sequential tuples must always have two '
                                    u'elements, both of them strings '
                                    u'(offending sequential entry: %r)' %
                                    seq_entry)
                        elif type(seq_entry) != str:
                            self._raise_syntax_error(
                                u'Sequential entries must either be '
                                u'tuples or strings (actual type: %r)' %
                                type(seq_entry))
                elif re_type != str:
                    self._raise_syntax_error(
                        u'Only dicts, lists, strings and tuples may occur as '
                        u'values (offending type: %r)' % re_type)

    def getLoaders(self, loaders):
        # We need a copy of the unmodified signature-to-loader dictionary
        self._sig_to_loader = loaders.copy()
        # We need to recursively descend into the distributor config to find
        # all relevant subrecord types
        self._target_sigs = set()
        mappings_to_iterate = [self.distributor_config]
        while mappings_to_iterate:
            mapping = mappings_to_iterate.pop()
            # The keys are always subrecord signatures
            for signature in mapping.keys():
                # We will definitely need this signature
                self._target_sigs.add(signature)
                resolved_entry = mapping[signature]
                re_type = type(resolved_entry)
                if re_type == dict:
                    # If the signature maps to a dict, recurse into it
                    mappings_to_iterate.append(resolved_entry)
                elif re_type == tuple:
                    # If the signature maps to a tuple, recurse into the
                    # dict stored in its second element
                    mappings_to_iterate.append(resolved_entry[1])
                elif re_type == list:
                    # If the signature maps to a list, record the signatures of
                    # each entry (str or tuple[str, str])
                    self._target_sigs.update([t[0] if type(t) == tuple else t
                                              for t in resolved_entry])
                # If it's not a dict, list or tuple, then this is a leaf node,
                # which means we've already recorded its type
        # Register ourselves for every type in the hierarchy, overriding
        # previous loaders when doing so
        for subrecord_type in self._target_sigs:
            loaders[subrecord_type] = self

    def getSlotsUsed(self):
        # _loader_state is the current state of our descent into the
        # distributor config, this is a tuple of strings marking the
        # subrecords we've visited.
        # _seq_index is only used when processing a sequential and marks
        # the index where we left off in the last loadData
        return '_loader_state', '_seq_index'

    def setDefault(self, record):
        record._loader_state = ()
        record._seq_index = None

    def set_mel_set(self, mel_set):
        """Sets parent MelSet. We use this to collect the attribute names
        from each loader."""
        self.mel_set = mel_set
        for element in mel_set.elements:
            # Underscore means internal usage only - e.g. distributor state
            el_attrs = [s for s in element.getSlotsUsed()
                        if not s.startswith('_')]
            for el_attr in el_attrs:
                self._attr_to_loader[el_attr] = element

    def _accepts_signature(self, dist_specifier, signature):
        """Internal helper method that checks if the specified signature is
        handled by the specified distribution specifier."""
        to_check = (dist_specifier[0] if type(dist_specifier) == tuple
                    else dist_specifier)
        return to_check == signature

    def _distribute_load(self, dist_specifier, record, ins, size_, readId):
        """Internal helper method that distributes a loadData call to the
        element loader pointed at by the specified distribution specifier."""
        if type(dist_specifier) == tuple:
            signature = dist_specifier[0]
            target_loader = self._attr_to_loader[dist_specifier[1]]
        else:
            signature = dist_specifier
            target_loader = self._sig_to_loader[dist_specifier]
        target_loader.loadData(record, ins, signature, size_, readId)

    def _apply_mapping(self, mapped_el, record, ins, signature, size_, readId):
        """Internal helper method that applies a single mapping element
        (mapped_el). This implements the correct loader state manipulations for
        that element and also distributes the loadData call to the correct
        loader, as specified by the mapping element and the current
        signature."""
        el_type = type(mapped_el)
        if el_type == dict:
            # Simple Scopes -----------------------------------------------
            # A simple scope - add the signature to the load state and
            # distribute the load by signature. That way we will descend
            # into this scope on the next loadData call.
            record._loader_state += (signature,)
            self._distribute_load(signature, record, ins, size_, readId)
        elif el_type == tuple:
            # Mixed Scopes ------------------------------------------------
            # A mixed scope - implement it like a simple scope, but
            # distribute the load by attribute name.
            record._loader_state += (signature,)
            self._distribute_load((signature, mapped_el[0]), record, ins,
                                  size_, readId)
        elif el_type == list:
            # Sequences, Pt. 2 --------------------------------------------
            # A sequence - add the signature to the load state, set the
            # sequence index to 1, and distribute the load to the element
            # specified by the first sequence entry.
            record._loader_state += (signature,)
            record._seq_index = 1 # we'll load the first element right now
            self._distribute_load(mapped_el[0], record, ins, size_,
                                  readId)
        else: # el_type == str, verified in _pre_process
            # Targets -----------------------------------------------------
            # A target - don't add the signature to the load state and
            # distribute the load by attribute name.
            self._distribute_load((signature, mapped_el), record, ins,
                                  size_, readId)

    def loadData(self, record, ins, sub_type, size_, readId):
        loader_state = record._loader_state
        seq_index = record._seq_index
        # First, descend as far as possible into the mapping. However, also
        # build up a tracker we can use to backtrack later on.
        descent_tracker = []
        current_mapping = self.distributor_config
        # Scopes --------------------------------------------------------------
        for signature in loader_state:
            current_mapping = current_mapping[signature]
            if type(current_mapping) == tuple: # handle mixed scopes
                current_mapping = current_mapping[1]
            descent_tracker.append((signature, current_mapping))
        # Sequences -----------------------------------------------------------
        # Then, check if we're in the middle of a sequence. If so,
        # current_mapping will actually be a list, namely the sequence we're
        # iterating over.
        if seq_index is not None:
            dist_specifier = current_mapping[seq_index]
            if self._accepts_signature(dist_specifier, sub_type):
                # We're good to go, call the next loader in the sequence and
                # increment the sequence index
                self._distribute_load(dist_specifier, record, ins, size_,
                                      readId)
                record._seq_index += 1
                return
            # The sequence is either over or we prematurely hit a non-matching
            # type - either way, stop distributing loads to it.
            record._seq_index = None
        # Next, check if the current mapping depth contains a specifier that
        # accepts our signature. If so, use that one to track and distribute.
        # If not, we have to backtrack.
        while descent_tracker:
            prev_sig, prev_mapping = descent_tracker.pop()
            # For each previous layer, check if it contains a specifier that
            # accepts our signature and use it if so.
            if sub_type in prev_mapping:
                # Calculate the new loader state - contains signatures for all
                # remaining scopes we haven't backtracked through yet plus the
                # one we just backtrackd into
                record._loader_state = tuple([x[0] for x in descent_tracker] +
                                             [prev_sig])
                self._apply_mapping(prev_mapping[sub_type], record, ins,
                                    sub_type, size_, readId)
                return
        # We didn't find anything during backtracking, so it must be in the top
        # scope. Wipe the loader state first and then apply the mapping.
        record._loader_state = ()
        self._apply_mapping(self.distributor_config[sub_type], record, ins,
                            sub_type, size_, readId)

    @property
    def signatures(self):
        return self._target_sigs

#------------------------------------------------------------------------------
# Mod Records -----------------------------------------------------------------
#------------------------------------------------------------------------------
class MreSubrecord(object):
    """Generic Subrecord."""
    def __init__(self,type,size,ins=None):
        self.changed = False
        self.subType = type
        self.size = size
        self.data = None
        self.inName = ins and ins.inName
        if ins: self.load(ins)

    def load(self,ins):
        self.data = ins.read(self.size,'----.'+self.subType)

    def setChanged(self,value=True):
        """Sets changed attribute to value. [Default = True.]"""
        self.changed = value

    def setData(self,data):
        """Sets data and size."""
        self.data = data
        self.size = len(data)

    def getSize(self):
        """Return size of self.data, after, if necessary, packing it."""
        if not self.changed: return self.size
        #--StringIO Object
        with ModWriter(sio()) as out:
            self.dumpData(out)
            #--Done
            self.data = out.getvalue()
        self.size = len(self.data)
        self.setChanged(False)
        return self.size

    def dumpData(self,out):
        """Dumps state into out. Called by getSize()."""
        raise exception.AbstractError

    def dump(self,out):
        if self.changed: raise exception.StateError(u'Data changed: ' + self.subType)
        if not self.data: raise exception.StateError(u'Data undefined: ' + self.subType)
        out.packSub(self.subType,self.data)

#------------------------------------------------------------------------------
class MreRecord(object):
    """Generic Record. flags1 are game specific see comments."""
    subtype_attr = {'EDID':'eid','FULL':'full','MODL':'model'}
    flags1_ = bolt.Flags(0, bolt.Flags.getNames(
        # {Sky}, {FNV} 0x00000000 ACTI: Collision Geometry (default)
        ( 0,'esm'), # {0x00000001}
        # {Sky}, {FNV} 0x00000004 ARMO: Not playable
        ( 2,'isNotPlayable'), # {0x00000004}
        # {FNV} 0x00000010 ????: Form initialized (Runtime only)
        ( 4,'formInitialized'), # {0x00000010}
        ( 5,'deleted'), # {0x00000020}
        # {Sky}, {FNV} 0x00000040 ACTI: Has Tree LOD
        # {Sky}, {FNV} 0x00000040 REGN: Border Region
        # {Sky}, {FNV} 0x00000040 STAT: Has Tree LOD
        # {Sky}, {FNV} 0x00000040 REFR: Hidden From Local Map
        # {TES4} 0x00000040 ????:  Actor Value
        # Constant HiddenFromLocalMap BorderRegion HasTreeLOD ActorValue
        ( 6,'borderRegion'), # {0x00000040}
        # {Sky} 0x00000080 TES4: Localized
        # {Sky}, {FNV} 0x00000080 PHZD: Turn Off Fire
        # {Sky} 0x00000080 SHOU: Treat Spells as Powers
        # {Sky}, {FNV} 0x00000080 STAT: Add-on LOD Object
        # {TES4} 0x00000080 ????:  Actor Value
        # Localized IsPerch AddOnLODObject TurnOffFire TreatSpellsAsPowers  ActorValue
        ( 7,'turnFireOff'), # {0x00000080}
        ( 7,'hasStrings'), # {0x00000080}
        # {Sky}, {FNV} 0x00000100 ACTI: Must Update Anims
        # {Sky}, {FNV} 0x00000100 REFR: Inaccessible
        # {Sky}, {FNV} 0x00000100 REFR for LIGH: Doesn't light water
        # MustUpdateAnims Inaccessible DoesntLightWater
        ( 8,'inaccessible'), # {0x00000100}
        # {Sky}, {FNV} 0x00000200 ACTI: Local Map - Turns Flag Off, therefore it is Hidden
        # {Sky}, {FNV} 0x00000200 REFR: MotionBlurCastsShadows
        # HiddenFromLocalMap StartsDead MotionBlur CastsShadows
        ( 9,'castsShadows'), # {0x00000200}
        # New Flag for FO4 and SSE used in .esl files
        ( 9, 'eslFile'), # {0x00000200}
        # {Sky}, {FNV} 0x00000400 LSCR: Displays in Main Menu
        # PersistentReference QuestItem DisplaysInMainMenu
        (10,'questItem'), # {0x00000400}
        (10,'persistent'), # {0x00000400}
        (11,'initiallyDisabled'), # {0x00000800}
        (12,'ignored'), # {0x00001000}
        # {FNV} 0x00002000 ????: No Voice Filter
        (13,'noVoiceFilter'), # {0x00002000}
        # {FNV} 0x00004000 STAT: Cannot Save (Runtime only) Ignore VC info
        (14,'cannotSave'), # {0x00004000}
        # {Sky}, {FNV} 0x00008000 STAT: Has Distant LOD
        (15,'visibleWhenDistant'), # {0x00008000}
        # {Sky}, {FNV} 0x00010000 ACTI: Random Animation Start
        # {Sky}, {FNV} 0x00010000 REFR light: Never fades
        # {FNV} 0x00010000 REFR High Priority LOD
        # RandomAnimationStart NeverFades HighPriorityLOD
        (16,'randomAnimationStart'), # {0x00010000}
        # {Sky}, {FNV} 0x00020000 ACTI: Dangerous
        # {Sky}, {FNV} 0x00020000 REFR light: Doesn't light landscape
        # {Sky} 0x00020000 SLGM: Can hold NPC's soul
        # {Sky}, {FNV} 0x00020000 STAT: Use High-Detail LOD Texture
        # {FNV} 0x00020000 STAT: Radio Station (Talking Activator)
        # {FNV} 0x00020000 STAT: Off limits (Interior cell)
        # Dangerous OffLimits DoesntLightLandscape HighDetailLOD CanHoldNPC RadioStation
        (17,'dangerous'), # {0x00020000}
        (18,'compressed'), # {0x00040000}
        # {Sky}, {FNV} 0x00080000 STAT: Has Currents
        # {FNV} 0x00080000 STAT: Platform Specific Texture
        # {FNV} 0x00080000 STAT: Dead
        # CantWait HasCurrents PlatformSpecificTexture Dead
        (19,'cantWait'), # {0x00080000}
        # {Sky}, {FNV} 0x00100000 ACTI: Ignore Object Interaction
        (20,'ignoreObjectInteraction'), # {0x00100000}
        # {???} 0x00200000 ????: Used in Memory Changed Form
        # {Sky}, {FNV} 0x00800000 ACTI: Is Marker
        (23,'isMarker'), # {0x00800000}
        # {FNV} 0x01000000 ????: Destructible (Runtime only)
        (24,'destructible'), # {0x01000000} {FNV}
        # {Sky}, {FNV} 0x02000000 ACTI: Obstacle
        # {Sky}, {FNV} 0x02000000 REFR: No AI Acquire
        (25,'obstacle'), # {0x02000000}
        # {Sky}, {FNV} 0x04000000 ACTI: Filter
        (26,'navMeshFilter'), # {0x04000000}
        # {Sky}, {FNV} 0x08000000 ACTI: Bounding Box
        # NavMesh BoundingBox
        (27,'boundingBox'), # {0x08000000}
        # {Sky}, {FNV} 0x10000000 STAT: Show in World Map
        # {FNV} 0x10000000 STAT: Reflected by Auto Water
        # {FNV} 0x10000000 STAT: Non-Pipboy
        # MustExitToTalk ShowInWorldMap NonPipboy',
        (28,'nonPipboy'), # {0x10000000}
        # {Sky}, {FNV} 0x20000000 ACTI: Child Can Use
        # {Sky}, {FNV} 0x20000000 REFR: Don't Havok Settle
        # {FNV} 0x20000000 REFR: Refracted by Auto Water
        # ChildCanUse DontHavokSettle RefractedbyAutoWater
        (29,'refractedbyAutoWater'), # {0x20000000}
        # {Sky}, {FNV} 0x40000000 ACTI: GROUND
        # {Sky}, {FNV} 0x40000000 REFR: NoRespawn
        # NavMeshGround NoRespawn
        (30,'noRespawn'), # {0x40000000}
        # {Sky}, {FNV} 0x80000000 REFR: MultiBound
        # MultiBound
        (31,'multiBound'), # {0x80000000}
        ))
    __slots__ = ['header','recType','fid','flags1','size','flags2','changed','subrecords','data','inName','longFids',]
    #--Set at end of class data definitions.
    type_class = None
    simpleTypes = None
    isKeyedByEid = False

    def __init__(self, header, ins=None, do_unpack=False):
        self.header = header
        self.recType = header.recType
        self.fid = header.fid
        self.flags1 = MreRecord.flags1_(header.flags1)
        self.size = header.size
        self.flags2 = header.flags2
        self.longFids = False #--False: Short (numeric); True: Long (espname,objectindex)
        self.changed = False
        self.subrecords = None
        self.data = ''
        self.inName = ins and ins.inName
        if ins: self.load(ins, do_unpack)

    def __repr__(self):
        return u'<%(eid)s[%(signature)s:%(fid)s]>' % {
            u'signature': self.recType,
            u'fid': strFid(self.fid),
            u'eid': (self.eid + u' ' if hasattr(self, 'eid')
                                     and self.eid is not None else u''),
        }

    def getHeader(self):
        """Returns header tuple."""
        return self.header

    def getBaseCopy(self):
        """Returns an MreRecord version of self."""
        baseCopy = MreRecord(self.getHeader())
        baseCopy.data = self.data
        return baseCopy

    def getTypeCopy(self,mapper=None):
        """Returns a type class copy of self, optionaly mapping fids to long."""
        if self.__class__ == MreRecord:
            fullClass = MreRecord.type_class[self.recType]
            myCopy = fullClass(self.getHeader())
            myCopy.data = self.data
            myCopy.load(do_unpack=True)
        else:
            myCopy = copy.deepcopy(self)
        if mapper and not myCopy.longFids:
            myCopy.convertFids(mapper,True)
        myCopy.changed = True
        myCopy.data = None
        return myCopy

    def mergeFilter(self,modSet):
        """This method is called by the bashed patch mod merger. The intention is
        to allow a record to be filtered according to the specified modSet. E.g.
        for a list record, items coming from mods not in the modSet could be
        removed from the list."""
        pass

    def getDecompressed(self):
        """Return self.data, first decompressing it if necessary."""
        if not self.flags1.compressed: return self.data
        size, = struct_unpack('I', self.data[:4])
        decomp = zlib.decompress(self.data[4:])
        if len(decomp) != size:
            raise exception.ModError(self.inName,
                u'Mis-sized compressed data. Expected %d, got %d.'
                                     % (size,len(decomp)))
        return decomp

    def load(self, ins=None, do_unpack=False):
        """Load data from ins stream or internal data buffer."""
        type = self.recType
        #--Read, but don't analyze.
        if not do_unpack:
            self.data = ins.read(self.size,type)
        #--Unbuffered analysis?
        elif ins and not self.flags1.compressed:
            inPos = ins.tell()
            self.data = ins.read(self.size,type)
            ins.seek(inPos,0,type+'_REWIND') # type+'_REWIND' is just for debug
            self.loadData(ins,inPos+self.size)
        #--Buffered analysis (subclasses only)
        else:
            if ins:
                self.data = ins.read(self.size,type)
            if not self.__class__ == MreRecord:
                with self.getReader() as reader:
                    # Check This
                    if ins and ins.hasStrings: reader.setStringTable(ins.strings)
                    self.loadData(reader,reader.size)
        #--Discard raw data?
        if do_unpack == 2:
            self.data = None
            self.changed = True

    def loadData(self,ins,endPos):
        """Loads data from input stream. Called by load().

        Subclasses should actually read the data, but MreRecord just skips over
        it (assuming that the raw data has already been read to itself. To force
        reading data into an array of subrecords, use loadSubrecords()."""
        ins.seek(endPos)

    def loadSubrecords(self):
        """This is for MreRecord only. It reads data into an array of subrecords,
        so that it can be handled in a simplistic way."""
        self.subrecords = []
        if not self.data: return
        with self.getReader() as reader:
            recType = self.recType
            readAtEnd = reader.atEnd
            readSubHeader = reader.unpackSubHeader
            subAppend = self.subrecords.append
            while not readAtEnd(reader.size,recType):
                (type,size) = readSubHeader(recType)
                subAppend(MreSubrecord(type,size,reader))

    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if converting to short format."""
        raise exception.AbstractError(self.recType)

    def updateMasters(self,masters):
        """Updates set of master names according to masters actually used."""
        raise exception.AbstractError(self.recType)

    def setChanged(self,value=True):
        """Sets changed attribute to value. [Default = True.]"""
        self.changed = value

    def setData(self,data):
        """Sets data and size."""
        self.data = data
        self.size = len(data)
        self.changed = False

    def getSize(self):
        """Return size of self.data, after, if necessary, packing it."""
        if not self.changed: return self.size
        if self.longFids: raise exception.StateError(
            u'Packing Error: %s %s: Fids in long format.'
            % (self.recType,self.fid))
        #--Pack data and return size.
        with ModWriter(sio()) as out:
            self.dumpData(out)
            self.data = out.getvalue()
        if self.flags1.compressed:
            dataLen = len(self.data)
            comp = zlib.compress(self.data,6)
            self.data = struct_pack('=I', dataLen) + comp
        self.size = len(self.data)
        self.setChanged(False)
        return self.size

    def dumpData(self,out):
        """Dumps state into data. Called by getSize(). This default version
        just calls subrecords to dump to out."""
        if self.subrecords is None:
            raise exception.StateError(u'Subrecords not unpacked. [%s: %s %08X]' %
                                       (self.inName, self.recType, self.fid))
        for subrecord in self.subrecords:
            subrecord.dump(out)

    def dump(self,out):
        """Dumps all data to output stream."""
        if self.changed: raise exception.StateError(u'Data changed: ' + self.recType)
        if not self.data and not self.flags1.deleted and self.size > 0:
            raise exception.StateError(u'Data undefined: ' + self.recType + u' ' + hex(self.fid))
        #--Update the header so it 'packs' correctly
        self.header.size = self.size
        if self.recType != 'GRUP':
            self.header.flags1 = self.flags1
            self.header.fid = self.fid
        out.write(self.header.pack())
        if self.size > 0: out.write(self.data)

    def getReader(self):
        """Returns a ModReader wrapped around (decompressed) self.data."""
        return ModReader(self.inName,sio(self.getDecompressed()))

    #--Accessing subrecords ---------------------------------------------------
    def getSubString(self,subType):
        """Returns the (stripped) string for a zero-terminated string
        record."""
        # Common subtype expanded in self?
        attr = MreRecord.subtype_attr.get(subType)
        value = None # default
        # If not MreRecord, then we will have info in data.
        if self.__class__ != MreRecord:
            if attr not in self.__slots__: return value
            return self.__getattribute__(attr)
        # Subrecords available?
        if self.subrecords is not None:
            for subrecord in self.subrecords:
                if subrecord.subType == subType:
                    value = bolt.cstrip(subrecord.data)
                    break
        # No subrecords, but we have data.
        elif self.data:
            with self.getReader() as reader:
                recType = self.recType
                readAtEnd = reader.atEnd
                readSubHeader = reader.unpackSubHeader
                readSeek = reader.seek
                readRead = reader.read
                while not readAtEnd(reader.size,recType):
                    (type,size) = readSubHeader(recType)
                    if type != subType:
                        readSeek(size,1)
                    else:
                        value = bolt.cstrip(readRead(size))
                        break
        return decode(value)

    def loadInfos(self,ins,endPos,infoClass):
        """Load infos from ins. Called from MobDials."""
        pass

#------------------------------------------------------------------------------
class MelRecord(MreRecord):
    """Mod record built from mod record elements."""
    melSet = None #--Subclasses must define as MelSet(*mels)
    __slots__ = []

    def __init__(self, header, ins=None, do_unpack=False):
        self.__class__.melSet.initRecord(self, header, ins, do_unpack)

    def getDefault(self,attr):
        """Returns default instance of specified instance. Only useful for
        MelGroup and MelGroups."""
        return self.__class__.melSet.getDefault(attr)

    def loadData(self,ins,endPos):
        """Loads data from input stream. Called by load()."""
        self.__class__.melSet.loadData(self, ins, endPos)

    def dumpData(self,out):
        """Dumps state into out. Called by getSize()."""
        self.__class__.melSet.dumpData(self,out)

    def mapFids(self,mapper,save):
        """Applies mapper to fids of sub-elements. Will replace fid with mapped value if save == True."""
        self.__class__.melSet.mapFids(self,mapper,save)

    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if converting to short format."""
        self.__class__.melSet.convertFids(self,mapper,toLong)

    def updateMasters(self,masters):
        """Updates set of master names according to masters actually used."""
        self.__class__.melSet.updateMasters(self,masters)

#------------------------------------------------------------------------------
#-- Common Records
#------------------------------------------------------------------------------
class MreHeaderBase(MelRecord):
    """File header.  Base class for all 'TES4' like records"""
    class MelMasterNames(MelBase):
        """Handles both MAST and DATA, but turns them into two separate lists.
        This is done to make updating the master list much easier."""
        def __init__(self):
            self._debug = False
            self.subType = b'MAST' # just in case something is expecting this

        def getLoaders(self, loaders):
            loaders[b'MAST'] = loaders[b'DATA'] = self

        def getSlotsUsed(self):
            return (u'masters', u'master_sizes')

        def setDefault(self, record):
            record.masters = []
            record.master_sizes = []

        def loadData(self, record, ins, sub_type, size_, readId):
            if sub_type == b'MAST':
                # Don't use ins.readString, because it will try to use
                # bolt.pluginEncoding for the filename. This is one case where
                # we want to use automatic encoding detection
                master_name = decode(bolt.cstrip(ins.read(size_, readId)),
                                     avoidEncodings=(u'utf8', u'utf-8'))
                record.masters.append(GPath(master_name))
            else: # sub_type == 'DATA'
                # DATA is the size for TES3, but unknown/unused for later games
                record.master_sizes.append(ins.unpack(u'Q', size_, readId)[0])

        def dumpData(self,record,out):
            pack1 = out.packSub0
            pack2 = out.packSub
            # Truncate or pad the sizes with zeroes as needed
            # TODO(inf) For Morrowind, this will have to query the files for
            #  their size and then store that
            num_masters = len(record.masters)
            num_sizes = len(record.master_sizes)
            record.master_sizes = record.master_sizes[:num_masters] + [0] * (
                    num_masters - num_sizes)
            for master_name, master_size in zip(record.masters,
                                                record.master_sizes):
                pack1(b'MAST', encode(master_name.s, firstEncoding=u'cp1252'))
                pack2(b'DATA', u'Q', master_size)

    def loadData(self, ins, endPos):
        super(MreHeaderBase, self).loadData(ins, endPos)
        num_masters = len(self.masters)
        num_sizes = len(self.master_sizes)
        # Just in case, truncate or pad the sizes with zeroes as needed
        self.master_sizes = self.master_sizes[:num_masters] + [0] * (
                num_masters - num_sizes)

    def getNextObject(self):
        """Gets next object index and increments it for next time."""
        self.changed = True
        self.nextObject += 1
        return self.nextObject -1

    __slots__ = []

#------------------------------------------------------------------------------
class MreGlob(MelRecord):
    """Global record.  Rather stupidly all values, despite their designation
       (short,long,float), are stored as floats -- which means that very large
       integers lose precision."""
    classType = 'GLOB'
    melSet = MelSet(
        MelEdid(),
        MelStruct('FNAM','s',('format','s')),
        MelFloat('FLTV', 'value'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreGmstBase(MelRecord):
    """Game Setting record.  Base class, each game should derive from this
    class."""
    Ids = None
    classType = 'GMST'

    melSet = MelSet(
        MelEdid(),
        MelUnion({
            u'b': MelUInt32('DATA', 'value'), # actually a bool
            u'f': MelFloat('DATA', 'value'),
            u's': MelLString('DATA', 'value'),
        }, decider=AttrValDecider(
            'eid', transformer=lambda eid: decode(eid[0]) if eid else u'i'),
            fallback=MelSInt32('DATA', 'value')
        ),
    )
    __slots__ = melSet.getSlotsUsed()

    def getGMSTFid(self):
        """Returns <Oblivion/Skyrim/etc>.esm fid in long format for specified
           eid."""
        cls = self.__class__
        from . import bosh # Late import to avoid circular imports
        if not cls.Ids:
            from . import bush
            fname = bush.game.pklfile
            try:
                with open(fname) as pkl_file:
                    cls.Ids = pickle.load(pkl_file)[cls.classType]
            except:
                old = bolt.deprintOn
                bolt.deprintOn = True
                bolt.deprint(u'Error loading %s:' % fname, traceback=True)
                bolt.deprintOn = old
                raise
        return bosh.modInfos.masterName,cls.Ids[self.eid]

#------------------------------------------------------------------------------
# WARNING: This is implemented and (should be) functional, but we do not import
# it! The reason is that LAND records are numerous and very big, so importing
# and adding this to mergeClasses would slow us down quite a bit.
class MreLand(MelRecord):
    """Land structure. Part of exterior cells."""
    classType = 'LAND'

    melSet = MelSet(
        MelBase('DATA', 'unknown'),
        MelBase('VNML', 'vertex_normals'),
        MelBase('VHGT', 'vertex_height_map'),
        MelBase('VCLR', 'vertex_colors'),
        MelGroups('layers',
            # Start a new layer each time we hit one of these
            MelUnion({
                'ATXT': MelStruct('ATXT', 'IBsh', (FID, 'atxt_texture'),
                                  'quadrant', 'unknown', 'layer'),
                'BTXT': MelStruct('BTXT', 'IBsh', (FID, 'btxt_texture'),
                                  'quadrant', 'unknown', 'layer'),
            }),
            # VTXT only exists for ATXT layers
            MelUnion({
                True:  MelBase('VTXT', 'alpha_layer_data'),
                False: MelNull('VTXT'),
            }, decider=AttrExistsDecider('atxt_texture')),
        ),
        MelArray('vertex_textures',
            MelFid('VTEX', 'vertex_texture'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLeveledListBase(MelRecord):
    """Base type for leveled item/creature/npc/spells.
       it requires the base class to use the following:
       classAttributes:
          top_copy_attrs -> List of attributes to modify by copying when
                            merging
          entry_copy_attrs -> List of attributes to modify by copying for each
                              list entry when merging
       instanceAttributes:
          entries -> List of items, with the following attributes:
              listId
              level
              count
          chanceNone
          flags
    """
    _flags = bolt.Flags(0,bolt.Flags.getNames(
        (0, 'calcFromAllLevels'),
        (1, 'calcForEachItem'),
        (2, 'useAllSpells'),
        (3, 'specialLoot'),
        ))
    top_copy_attrs = ()
    # TODO(inf) Only overriden for FO3/FNV right now - Skyrim/FO4?
    entry_copy_attrs = ('listId', 'level', 'count')
    __slots__ = ['mergeOverLast', 'mergeSources', 'items', 'delevs', 'relevs']
                # + ['flags', 'entries'] # define those in the subclasses

    def __init__(self, header, ins=None, do_unpack=False):
        MelRecord.__init__(self, header, ins, do_unpack)
        self.mergeOverLast = False #--Merge overrides last mod merged
        self.mergeSources = None #--Set to list by other functions
        self.items  = None #--Set of items included in list
        self.delevs = None #--Set of items deleted by list (Delev and Relev mods)
        self.relevs = None #--Set of items relevelled by list (Relev mods)

    def mergeFilter(self,modSet):
        """Filter out items that don't come from specified modSet."""
        if not self.longFids: raise exception.StateError(u'Fids not in long format')
        self.entries = [entry for entry in self.entries if entry.listId[0] in modSet]

    def mergeWith(self,other,otherMod):
        """Merges newLevl settings and entries with self.
        Requires that: self.items, other.delevs and other.relevs be defined."""
        if not self.longFids or not other.longFids:
            raise exception.StateError(u'Fids not in long format')
        #--Relevel or not?
        if other.relevs:
            for attr in self.__class__.top_copy_attrs:
                self.__setattr__(attr,other.__getattribute__(attr))
            self.flags = other.flags()
        else:
            for attr in self.__class__.top_copy_attrs:
                otherAttr = other.__getattribute__(attr)
                if otherAttr is not None:
                    self.__setattr__(attr, otherAttr)
            self.flags |= other.flags
        #--Remove items based on other.removes
        if other.delevs or other.relevs:
            removeItems = self.items & (other.delevs | other.relevs)
            self.entries = [entry for entry in self.entries if entry.listId not in removeItems]
            self.items = (self.items | other.delevs) - other.relevs
        hasOldItems = bool(self.items)
        #--Add new items from other
        newItems = set()
        entriesAppend = self.entries.append
        newItemsAdd = newItems.add
        for entry in other.entries:
            if entry.listId not in self.items:
                entriesAppend(entry)
                newItemsAdd(entry.listId)
        # Check if merging exceeded the 8-bit counter's limit and, if so,
        # truncate it back to 255 and warn
        if len(self.entries) > 255:
            # TODO(inf) In the future, offer an option to auto-split these into
            #  multiple sub-lists instead
            bolt.deprint(u'Merging changes from mod \'%s\' to leveled list %r '
                         u'caused it to exceed 255 entries. Truncating back '
                         u'to 255, you will have to fix this manually!' %
                         (otherMod.s, self))
            self.entries = self.entries[:255]
        entry_copy_attrs_key = attrgetter(*self.__class__.entry_copy_attrs)
        if newItems:
            self.items |= newItems
            self.entries.sort(key=entry_copy_attrs_key)
        #--Is merged list different from other? (And thus written to patch.)
        if ((len(self.entries) != len(other.entries)) or
                (self.flags != other.flags)):
            self.mergeOverLast = True
        else:
            my_val = self.__getattribute__
            other_val = other.__getattribute__
            # Check copy-attributes first, break if they are different
            for attr in self.__class__.top_copy_attrs:
                if my_val(attr) != other_val(attr):
                    self.mergeOverLast = True
                    break
            else:
                # Then, check the sort-attributes, same story
                otherlist = other.entries
                otherlist.sort(key=entry_copy_attrs_key)
                for selfEntry,otherEntry in zip(self.entries,otherlist):
                    my_val = selfEntry.__getattribute__
                    other_val = otherEntry.__getattribute__
                    for attr in self.__class__.entry_copy_attrs:
                        if my_val(attr) != other_val(attr):
                            break
                    else:
                        # attributes are identical, try next entry
                        continue
                    # attributes differ, no need to look at more entries
                    self.mergeOverLast = True
                    break
                else:
                    # Neither one had different attributes
                    self.mergeOverLast = False
        if self.mergeOverLast:
            self.mergeSources.append(otherMod)
        else:
            self.mergeSources = [otherMod]
        self.setChanged(self.mergeOverLast)

#------------------------------------------------------------------------------
class MreDial(MelRecord):
    """Dialog record."""
    classType = 'DIAL'
    __slots__ = ['infoStamp', 'infoStamp2', 'infos']

    def __init__(self, header, ins=None, do_unpack=False):
        MelRecord.__init__(self, header, ins, do_unpack)
        self.infoStamp = 0 #--Stamp for info GRUP
        self.infoStamp2 = 0 #--Stamp for info GRUP
        self.infos = []

    def loadInfos(self, ins, endPos, infoClass):
        read_header = ins.unpackRecHeader
        ins_at_end = ins.atEnd
        append_info = self.infos.append
        while not ins_at_end(endPos, 'INFO Block'):
            #--Get record info and handle it
            header = read_header()
            if header.recType == 'INFO':
                append_info(infoClass(header, ins, True))
            else:
                raise exception.ModError(ins.inName,
                  _(u'Unexpected %s record in %s group.') % (
                                             header.recType, u'INFO'))

    def dump(self,out):
        """Dumps self., then group header and then records."""
        MreRecord.dump(self,out)
        if not self.infos: return
        header_size = RecordHeader.rec_header_size
        dial_size = header_size + sum([header_size + info.getSize()
                                       for info in self.infos])
        # Not all pack targets may be needed - limit the unpacked amount to the
        # number of specified GRUP format entries
        pack_targets = ['GRUP', dial_size, self.fid, 7, self.infoStamp,
                        self.infoStamp2]
        out.pack(RecordHeader.rec_pack_format_str,
                 *pack_targets[:len(RecordHeader.rec_pack_format)])
        for info in self.infos: info.dump(out)

    def updateMasters(self,masters):
        MelRecord.updateMasters(self,masters)
        for info in self.infos:
            info.updateMasters(masters)

    def convertFids(self,mapper,toLong):
        MelRecord.convertFids(self,mapper,toLong)
        for info in self.infos:
            info.convertFids(mapper,toLong)

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

    def loadData(self, record, ins, sub_type, size_, readId):
        if sub_type == 'INDX':
            self._last_indx, = ins.unpack('I', size_, readId)
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

    def loadData(self, record, ins, sub_type, size_, readId):
        insUnpack = ins.unpack
        insRead32 = ins.readString32
        count, = insUnpack('I',4,readId)
        data = []
        dataAppend = data.append
        for x in xrange(count):
            string = insRead32(readId)
            fid = ins.unpackRef()
            index, = insUnpack('I',4,readId)
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

#------------------------------------------------------------------------------
class MreHasEffects(object):
    """Mixin class for magic items."""
    __slots__ = []

    def getEffects(self):
        """Returns a summary of effects. Useful for alchemical catalog."""
        from . import bush
        effects = []
        effectsAppend = effects.append
        for effect in self.effects:
            mgef, actorValue = effect.name, effect.actorValue
            if mgef not in bush.game.generic_av_effects:
                actorValue = 0
            effectsAppend((mgef,actorValue))
        return effects

    def getSpellSchool(self):
        """Returns the school based on the highest cost spell effect."""
        from . import bush
        spellSchool = [0,0]
        for effect in self.effects:
            school = bush.game.mgef_school[effect.name]
            effectValue = bush.game.mgef_basevalue[effect.name]
            if effect.magnitude:
                effectValue *=  effect.magnitude
            if effect.area:
                effectValue *=  (effect.area//10)
            if effect.duration:
                effectValue *=  effect.duration
            if spellSchool[0] < effectValue:
                spellSchool = [effectValue,school]
        return spellSchool[1]

    def getEffectsSummary(self):
        """Return a text description of magic effects."""
        from . import bush
        with sio() as buff:
            avEffects = bush.game.generic_av_effects
            aValues = bush.game.actor_values
            buffWrite = buff.write
            if self.effects:
                school = self.getSpellSchool()
                buffWrite(aValues[20+school] + u'\n')
            for index,effect in enumerate(self.effects):
                if effect.scriptEffect:
                    effectName = effect.scriptEffect.full or u'Script Effect'
                else:
                    effectName = bush.game.mgef_name[effect.name]
                    if effect.name in avEffects:
                        effectName = re.sub(_(u'(Attribute|Skill)'),aValues[effect.actorValue],effectName)
                buffWrite(u'o+*'[effect.recipient]+u' '+effectName)
                if effect.magnitude: buffWrite(u' %sm'%effect.magnitude)
                if effect.area: buffWrite(u' %sa'%effect.area)
                if effect.duration > 1: buffWrite(u' %sd'%effect.duration)
                buffWrite(u'\n')
            return buff.getvalue()
