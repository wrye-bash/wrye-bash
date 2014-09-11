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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2014 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This module contains all of the basic types used to read ESP/ESM mod files"""
import zlib
import StringIO
import os
import re
import struct
import copy
import cPickle
from operator import attrgetter

import bolt
from bolt import _unicode, _encode, sio, GPath

# Util Constants ---------------------------------------------------------------
#--Null strings (for default empty byte arrays)
null1 = '\x00'
null2 = null1*2
null3 = null1*3
null4 = null1*4

# Util Functions ---------------------------------------------------------------
#--Type coercion
def _coerce(value, newtype, base=None, AllowNone=False):
    try:
        if newtype is float:
            pack,unpack = struct.pack,struct.unpack
            #--Force standard precision
            return round(unpack('f',pack('f',float(value)))[0], 6)
        elif newtype is bool:
            if isinstance(value,basestring):
                retValue = value.strip().lower()
                if AllowNone and retValue == u'none': return None
                return retValue not in (u'',u'none',u'false',u'no',u'0',u'0.0')
            else: return bool(value)
        elif base: retValue = newtype(value, base)
        elif newtype is unicode: retValue = _unicode(value)
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

#--.NET Strings
def netString(x):
    """Encode a string into a .net string."""
    lenx = len(x)
    if lenx < 128:
        return struct.pack('b',lenx)+x
    elif lenx > 0x7FFF: #--Actually, probably fails earlier.
        raise bolt.UncodedError
    else:
        lenx = 0x80 | lenx & 0x7F | (lenx & 0xFF80) << 1
        return struct.pack('H',lenx)+x

#--Reference (fid)
def strFid(fid):
    """Returns a string representation of the fid."""
    if isinstance(fid,tuple):
        return u'(%s,0x%06X)' % (fid[0].s,fid[1])
    else:
        return u'%08X' % fid

def genFid(modIndex,objectIndex):
    """Generates a fid from modIndex and ObjectIndex."""
    return long(objectIndex) | (long(modIndex) << 24)

def getModIndex(fid):
    """Returns the modIndex portion of a fid."""
    return int(fid >> 24)

def getObjectIndex(fid):
    """Returns the objectIndex portion of a fid."""
    return int(fid & 0x00FFFFFFL)

def getFormIndices(fid):
    """Returns tuple of modIndex and ObjectIndex of fid."""
    return (int(fid >> 24),int(fid & 0x00FFFFFFL))

# Mod I/O Errors ---------------------------------------------------------------
#-------------------------------------------------------------------------------
class ModError(bolt.FileError):
    """Mod Error: File is corrupted."""
    pass

#-------------------------------------------------------------------------------
class ModReadError(ModError):
    """TES4 Error: Attempt to read outside of buffer."""
    def __init__(self,inName,recType,tryPos,maxPos):
        self.recType = recType
        self.tryPos = tryPos
        self.maxPos = maxPos
        if tryPos < 0:
            message = (u'%s: Attempted to read before (%d) beginning of file/buffer.'
                       % (recType,tryPos))
        else:
            message = (u'%s: Attempted to read past (%d) end (%d) of file/buffer.'
                       % (recType,tryPos,maxPos))
        ModError.__init__(self,inName.s,message)

#-------------------------------------------------------------------------------
class ModSizeError(ModError):
    """TES4 Error: Record/subrecord has wrong size."""
    def __init__(self,inName,recType,readSize,maxSize,exactSize=True):
        self.recType = recType
        self.readSize = readSize
        self.maxSize = maxSize
        self.exactSize = exactSize
        if exactSize:
            messageForm = u'%s: Expected size == %d, but got: %d '
        else:
            messageForm = u'%s: Expected size <= %d, but got: %d '
        ModError.__init__(self,inName.s,messageForm % (recType,readSize,maxSize))

#-------------------------------------------------------------------------------
class ModUnknownSubrecord(ModError):
    """TES4 Error: Unknown subrecord."""
    def __init__(self,inName,subType,recType):
        ModError.__init__(self,inName,u'Extraneous subrecord (%s) in %s record.'
                          % (subType,recType))

# Mod I/O ----------------------------------------------------------------------
#-------------------------------------------------------------------------------
class BaseRecordHeader(object):
    """Virtual base class that all game types must implement.
    The minimal implementations must have the following attributes:

    recType
    size

    if recType == 'GRUP', the following additional attributes must exist
     groupType
     label (already decoded)
     stamp

    if recType != 'GRUP', the following addition attributes must exist
     flags1
     fid
     flags2

    All other data may be store in any manner, as they will not be
    accessed by the ModReader/ModWriter"""

    def __init__(self,recType,arg1,arg2,arg3):
        """args1-arg3 correspond to the attrs above, depending on recType"""
        pass

    @staticmethod
    def unpack(ins):
        """Return a RecordHeader object by reading the input stream."""
        raise bolt.AbstractError

    def pack(self):
        """Return the record header packed into a string to be written to file"""
        raise bolt.AbstractError

#------------------------------------------------------------------------------
class ModReader:
    """Wrapper around a TES4 file in read mode.
    Will throw a ModReaderror if read operation fails to return correct size.

    **ModReader.recHeader must be set to the game's specific RecordHeader
      class type, for ModReader to use.**
    """
    recHeader = BaseRecordHeader

    def __init__(self,inName,ins):
        """Initialize."""
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
    def __exit__(self,*args,**kwdargs): self.ins.close()

    def setStringTable(self,table={}):
        if table is None:
            self.hasStrings = False
            self.table = {}
        else:
            self.hasStrings = True
            self.strings = table

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
            raise ModReadError(self.inName,recType,newPos,self.size)
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
            return (filePos == self.size)
        elif filePos > endPos:
            raise ModError(self.inName,u'Exceeded limit of: '+recType)
        else:
            return (filePos == endPos)

    #--Read/Unpack ----------------------------------------
    def read(self,size,recType='----'):
        """Read from file."""
        endPos = self.ins.tell() + size
        if endPos > self.size:
            raise ModSizeError(self.inName,recType,endPos,self.size)
        return self.ins.read(size)

    def readLString(self,size,recType='----'):
        """Read translatible string.  If the mod has STRINGS file, this is a
        uint32 to lookup the string in the string table.  Otherwise, this is a
        zero-terminated string."""
        if self.hasStrings:
            if size != 4:
                endPos = self.ins.tell() + size
                raise ModReadError(self.inName,recType,endPos,self.size)
            id, = self.unpack('I',4,recType)
            if id == 0: return u''
            else: return self.strings.get(id,u'LOOKUP FAILED!') #--Same as Skyrim
        else:
            return self.readString(size,recType)

    def readString16(self,size,recType='----'):
        """Read wide pascal string: uint16 is used to indicate length."""
        strLen, = self.unpack('H',2,recType)
        return self.readString(strLen,recType)

    def readString32(self,size,recType='----'):
        """Read wide pascal string: uint32 is used to indicate length."""
        strLen, = self.unpack('I',4,recType)
        return self.readString(strLen,recType)

    def readString(self,size,recType='----'):
        """Read string from file, stripping zero terminator."""
        return u'\n'.join(_unicode(x,bolt.pluginEncoding,avoidEncodings=('utf8','utf-8')) for x in
                          bolt.cstrip(self.read(size,recType)).split('\n'))

    def readStrings(self,size,recType='----'):
        """Read strings from file, stripping zero terminator."""
        return [_unicode(x,bolt.pluginEncoding,avoidEncodings=('utf8','utf-8')) for x in
                self.read(size,recType).rstrip(null1).split(null1)]

    def unpack(self,format,size,recType='----'):
        """Read file and unpack according to struct format."""
        endPos = self.ins.tell() + size
        if endPos > self.size:
            raise ModReadError(self.inName,recType,endPos,self.size)
        return struct.unpack(format,self.ins.read(size))

    def unpackRef(self,recType='----'):
        """Read a ref (fid)."""
        return self.unpack('I',4)[0]

    def unpackRecHeader(self): return ModReader.recHeader.unpack(self)

    def unpackSubHeader(self,recType='----',expType=None,expSize=0):
        """Unpack a subrecord header.  Optionally checks for match with expected
        type and size."""
        selfUnpack = self.unpack
        (type,size) = selfUnpack('4sH',6,recType+'.SUB_HEAD')
        #--Extended storage?
        while type == 'XXXX':
            size = selfUnpack('I',4,recType+'.XXXX.SIZE.')[0]
            type = selfUnpack('4sH',6,recType+'.XXXX.TYPE')[0] #--Throw away size (always == 0)
        #--Match expected name?
        if expType and expType != type:
            raise ModError(self.inName,
                u'%s: Expected %s subrecord, but found %s instead.'
                % (recType,expType,type))
        #--Match expected size?
        if expSize and expSize != size:
            raise ModSizeError(self.inName,recType+'.'+type,size,expSize,True)
        return (type,size)

    #--Find data ------------------------------------------
    def findSubRecord(self,subType,recType='----'):
        """Finds subrecord with specified type."""
        atEnd = self.atEnd
        unpack = self.unpack
        seek = self.seek
        while not atEnd():
            (type,size) = unpack('4sH',6,recType+'.SUB_HEAD')
            if type == subType:
                return self.read(size,recType+'.'+subType)
            else:
                seek(size,1,recType+'.'+type)
        #--Didn't find it?
        else:
            return None

#-------------------------------------------------------------------------------
class ModWriter:
    """Wrapper around a TES4 output stream.  Adds utility functions."""
    def __init__(self,out):
        """Initialize."""
        self.out = out

    # with statement
    def __enter__(self): return self
    def __exit__(self,*args,**kwdargs): self.out.close()

    #--Stream Wrapping ------------------------------------
    def write(self,data): self.out.write(data)
    def tell(self): return self.out.tell()
    def seek(self,offset,whence=os.SEEK_SET): return self.out.seek(offset,whence)
    def getvalue(self): return self.out.getvalue()
    def close(self): self.out.close()

    #--Additional functions -------------------------------
    def pack(self,format,*data):
        self.out.write(struct.pack(format,*data))

    def packSub(self,type,data,*values):
        """Write subrecord header and data to output stream.
        Call using either packSub(type,data) or packSub(type,format,values).
        Will automatically add a prefacing XXXX size subrecord to handle data
        with size > 0xFFFF."""
        try:
            if data is None: return
            structPack = struct.pack
            if values: data = structPack(data,*values)
            outWrite = self.out.write
            lenData = len(data)
            if lenData <= 0xFFFF:
                outWrite(structPack('=4sH',type,lenData))
                outWrite(data)
            else:
                outWrite(structPack('=4sHI','XXXX',4,lenData))
                outWrite(structPack('=4sH',type,0))
                outWrite(data)
        except Exception as e:
            print e
            print self,type,data,values

    def packSub0(self,type,data):
        """Write subrecord header plus zero terminated string to output
        stream."""
        if data is None: return
        elif isinstance(data,unicode):
            data = _encode(data,firstEncoding=bolt.pluginEncoding)
        lenData = len(data) + 1
        outWrite = self.out.write
        structPack = struct.pack
        if lenData < 0xFFFF:
            outWrite(structPack('=4sH',type,lenData))
        else:
            outWrite(structPack('=4sHI','XXXX',4,lenData))
            outWrite(structPack('=4sH',type,0))
        outWrite(data)
        outWrite('\x00')

    def packRef(self,type,fid):
        """Write subrecord header and fid reference."""
        if fid is not None: self.out.write(struct.pack('=4sHI',type,4,fid))

    def writeGroup(self,size,label,groupType,stamp):
        if type(label) is str:
            self.pack('=4sI4sII','GRUP',size,label,groupType,stamp)
        elif type(label) is tuple:
            self.pack('=4sIhhII','GRUP',size,label[1],label[0],groupType,stamp)
        else:
            self.pack('=4s4I','GRUP',size,label,groupType,stamp)

# Mod Record Elements ----------------------------------------------------------
#-------------------------------------------------------------------------------
# Constants
FID = 'FID' #--Used by MelStruct classes to indicate fid elements.

#-------------------------------------------------------------------------------
class MelObject(object):
    """An empty class used by group and structure elements for data storage."""
    def __eq__(self,other):
        """Operator: =="""
        return isinstance(other,MelObject) and self.__dict__ == other.__dict__

    def __ne__(self,other):
        """Operator: !="""
        return not isinstance(other,MelObject) or self.__dict__ != other.__dict__

#-----------------------------------------------------------------------------
class MelBase:
    """Represents a mod record raw element. Typically used for unknown elements.
    Also used as parent class for other element types."""

    def __init__(self,type,attr,default=None):
        """Initialize."""
        self.subType, self.attr, self.default = type, attr, default
        self._debug = False

    def debug(self,on=True):
        """Sets debug flag on self."""
        self._debug = on
        return self

    def getSlotsUsed(self):
        return (self.attr,)

    def parseElements(self,*elements):
        """Parses elements and returns attrs,defaults,actions,formAttrs where:
        * attrs is tuple of attibute (names)
        * formAttrs is tuple of attributes that have fids,
        * defaults is tuple of default values for attributes
        * actions is tuple of callables to be used when loading data
        Note that each element of defaults and actions matches corresponding attr element.
        Used by struct subclasses.
        """
        formAttrs = []
        lenEls = len(elements)
        attrs,defaults,actions = [0]*lenEls,[0]*lenEls,[0]*lenEls
        formAttrsAppend = formAttrs.append
        for index,element in enumerate(elements):
            if not isinstance(element,tuple): element = (element,)
            if element[0] == FID:
                formAttrsAppend(element[1])
            elif callable(element[0]):
                actions[index] = element[0]
            attrIndex = (1 if callable(element[0]) or element[0] in (FID,0)
                         else 0)
            attrs[index] = element[attrIndex]
            defaults[index] = (element[-1] if len(element)-attrIndex == 2
                               else 0)
        return map(tuple,(attrs,defaults,actions,formAttrs))

    def getDefaulters(self,defaulters,base):
        """Registers self as a getDefault(attr) provider."""
        pass

    def getLoaders(self,loaders):
        """Adds self as loader for type."""
        loaders[self.subType] = self

    def hasFids(self,formElements):
        """Include self if has fids."""
        pass

    def setDefault(self,record):
        """Sets default value for record instance."""
        record.__setattr__(self.attr,self.default)

    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        record.__setattr__(self.attr,ins.read(size,readId))
        if self._debug: print u'%s' % record.__getattribute__(self.attr)

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        value = record.__getattribute__(self.attr)
        if value != None: out.packSub(self.subType,value)

    def mapFids(self,record,function,save=False):
        """Applies function to fids. If save is True, then fid is set
        to result of function."""
        raise bolt.AbstractError

#------------------------------------------------------------------------------
class MelFid(MelBase):
    """Represents a mod record fid element."""

    def hasFids(self,formElements):
        """Include self if has fids."""
        formElements.add(self)

    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        record.__setattr__(self.attr,ins.unpackRef(readId))
        if self._debug: print u'  %08X' % (record.__getattribute__(self.attr),)

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        try:
            value = record.__getattribute__(self.attr)
        except AttributeError:
            value = None
        if value is not None: out.packRef(self.subType,value)

    def mapFids(self,record,function,save=False):
        """Applies function to fids. If save is true, then fid is set
        to result of function."""
        attr = self.attr
        try:
            fid = record.__getattribute__(attr)
        except AttributeError:
            fid = None
        result = function(fid)
        if save: record.__setattr__(attr,result)

#------------------------------------------------------------------------------
class MelFids(MelBase):
    """Represents a mod record fid elements."""

    def hasFids(self,formElements):
        """Include self if has fids."""
        formElements.add(self)

    def setDefault(self,record):
        """Sets default value for record instance."""
        record.__setattr__(self.attr,[])

    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        fid = ins.unpackRef(readId)
        record.__getattribute__(self.attr).append(fid)
        if self._debug: print u' ',hex(fid)

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        type = self.subType
        outPackRef = out.packRef
        for fid in record.__getattribute__(self.attr):
            outPackRef(type,fid)

    def mapFids(self,record,function,save=False):
        """Applies function to fids. If save is true, then fid is set
        to result of function."""
        fids = record.__getattribute__(self.attr)
        for index,fid in enumerate(fids):
            result = function(fid)
            if save: fids[index] = result

#------------------------------------------------------------------------------
class MelFidList(MelFids):
    """Represents a listmod record fid elements. The only difference from
    MelFids is how the data is stored. For MelFidList, the data is stored
    as a single subrecord rather than as separate subrecords."""

    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        if not size: return
        fids = ins.unpack(`size/4`+'I',size,readId)
        record.__setattr__(self.attr,list(fids))
        if self._debug:
            for fid in fids:
                print u'  %08X' % fid

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        fids = record.__getattribute__(self.attr)
        if not fids: return
        out.packSub(self.subType,`len(fids)`+'I',*fids)

#------------------------------------------------------------------------------
class MelSortedFidList(MelFidList):
    """MelFidList that sorts the order of the Fids before writing them.  They are not sorted after modification, only just prior to writing."""

    def __init__(self, type, attr, sortKeyFn = lambda x: x, default=None):
        """sortKeyFn - function to pass to list.sort(key = ____) to sort the FidList
           just prior to writing.  Since the FidList will already be converted to short Fids
           at this point we're sorting 4-byte values,  not (FileName, 3-Byte) tuples."""
        MelFidList.__init__(self, type, attr, default)
        self.sortKeyFn = sortKeyFn

    def dumpData(self, record, out):
        fids = record.__getattribute__(self.attr)
        if not fids: return
        fids.sort(key=self.sortKeyFn)
        # NOTE: fids.sort sorts from lowest to highest, so lowest values FormID will sort first
        #       if it should be opposite, use this instead:
        #  fids.sort(key=self.sortKeyFn, reverse=True)
        out.packSub(self.subType, `len(fids)` + 'I', *fids)

#------------------------------------------------------------------------------
class MelGroup(MelBase):
    """Represents a group record."""

    def __init__(self,attr,*elements):
        """Initialize."""
        self.attr,self.elements,self.formElements,self.loaders = attr,elements,set(),{}

    def debug(self,on=True):
        """Sets debug flag on self."""
        for element in self.elements: element.debug(on)
        return self

    def getDefaulters(self,defaulters,base):
        """Registers self as a getDefault(attr) provider."""
        defaulters[base+self.attr] = self
        for element in self.elements:
            element.getDefaulters(defaulters,base+self.attr+'.')

    def getLoaders(self,loaders):
        """Adds self as loader for subelements."""
        for element in self.elements:
            element.getLoaders(self.loaders)
        for type in self.loaders:
            loaders[type] = self

    def hasFids(self,formElements):
        """Include self if has fids."""
        for element in self.elements:
            element.hasFids(self.formElements)
        if self.formElements: formElements.add(self)

    def setDefault(self,record):
        """Sets default value for record instance."""
        record.__setattr__(self.attr,None)

    def getDefault(self):
        """Returns a default copy of object."""
        target = MelObject()
        for element in self.elements:
            element.setDefault(target)
        return target

    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        target = record.__getattribute__(self.attr)
        if target == None:
            target = self.getDefault()
            record.__setattr__(self.attr,target)
        slots = []
        slotsExtend = slots.extend
        for element in self.elements:
            slotsExtend(element.getSlotsUsed())
        target.__slots__ = slots
        self.loaders[type].loadData(target,ins,type,size,readId)

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        target = record.__getattribute__(self.attr)
        if not target: return
        for element in self.elements:
            element.dumpData(target,out)

    def mapFids(self,record,function,save=False):
        """Applies function to fids. If save is true, then fid is set
        to result of function."""
        target = record.__getattribute__(self.attr)
        if not target: return
        for element in self.formElements:
            element.mapFids(target,function,save)

#------------------------------------------------------------------------------
class MelGroups(MelGroup):
    """Represents an array of group record."""

    def __init__(self,attr,*elements):
        """Initialize. Must have at least one element."""
        MelGroup.__init__(self,attr,*elements)
        self.type0 = self.elements[0].subType

    def setDefault(self,record):
        """Sets default value for record instance."""
        record.__setattr__(self.attr,[])

    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        if type == self.type0:
            target = self.getDefault()
            record.__getattribute__(self.attr).append(target)
        else:
            target = record.__getattribute__(self.attr)[-1]
        slots = []
        for element in self.elements:
            slots.extend(element.getSlotsUsed())
        target.__slots__ = slots
        self.loaders[type].loadData(target,ins,type,size,readId)

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        elements = self.elements
        for target in record.__getattribute__(self.attr):
            for element in elements:
                element.dumpData(target,out)

    def mapFids(self,record,function,save=False):
        """Applies function to fids. If save is true, then fid is set
        to result of function."""
        formElements = self.formElements
        for target in record.__getattribute__(self.attr):
            for element in formElements:
                element.mapFids(target,function,save)

#------------------------------------------------------------------------------
class MelNull(MelBase):
    """Represents an obsolete record. Reads bytes from instream, but then
    discards them and is otherwise inactive."""

    def __init__(self,type):
        """Initialize."""
        self.subType = type
        self._debug = False

    def getSlotsUsed(self):
        return ()

    def setDefault(self,record):
        """Sets default value for record instance."""
        pass

    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        junk = ins.read(size,readId)
        if self._debug: print u' ',record.fid,unicode(junk)

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        pass

#------------------------------------------------------------------------------
class MelXpci(MelNull):
    """Handler for obsolete MelXpci record. Bascially just discards it."""
    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        xpci = ins.unpackRef(readId)
        #--Read ahead and get associated full as well.
        pos = ins.tell()
        (type,size) = ins.unpack('4sH',6,readId+'.FULL')
        if type == 'FULL':
            full = ins.read(size,readId)
        else:
            full = None
            ins.seek(pos)
        if self._debug: print u' ',strFid(record.fid),strFid(xpci),full

#------------------------------------------------------------------------------
class MelString(MelBase):
    """Represents a mod record string element."""

    def __init__(self,type,attr,default=None,maxSize=0):
        """Initialize."""
        MelBase.__init__(self,type,attr,default)
        self.maxSize = maxSize

    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        value = ins.readString(size,readId)
        record.__setattr__(self.attr,value)
        if self._debug: print u' ',record.__getattribute__(self.attr)

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        value = record.__getattribute__(self.attr)
        if value != None:
            firstEncoding = bolt.pluginEncoding
            if self.maxSize:
                value = bolt.winNewLines(value.rstrip())
                size = min(self.maxSize,len(value))
                test,encoding = _encode(value,firstEncoding=firstEncoding,returnEncoding=True)
                extra_encoded = len(test) - self.maxSize
                if extra_encoded > 0:
                    total = 0
                    i = -1
                    while total < extra_encoded:
                        total += len(value[i].encode(encoding))
                        i -= 1
                    size += i + 1
                    value = value[:size]
                    value = _encode(value,firstEncoding=encoding)
                else:
                    value = test
            else:
                value = _encode(value,firstEncoding=firstEncoding)
            out.packSub0(self.subType,value)

#------------------------------------------------------------------------------
class MelUnicode(MelString):
    """Like MelString, but instead of using bolt.pluginEncoding to read the
       string, it tries the encoding specified in the constructor instead"""
    def __init__(self,type,attr,default=None,maxSize=0,encoding=None):
        MelString.__init__(self,type,attr,default,maxSize)
        self.encoding = encoding # None == automatic detection

    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute"""
        value = u'\n'.join(_unicode(x,self.encoding,avoidEncodings=('utf8','utf-8'))
                           for x in bolt.cstrip(ins.read(size,readId)).split('\n'))
        record.__setattr__(self.attr,value)

    def dumpData(self,record,out):
        value = record.__getattribute__(self.attr)
        if value != None:
            firstEncoding = self.encoding
            if self.maxSize:
                value = bolt.winNewLines(value.strip())
                size = min(self.maxSize,len(value))
                test,encoding = _encode(value,firstEncoding=firstEncoding,returnEncoding=True)
                extra_encoded = len(test) - self.maxSize
                if extra_encoded > 0:
                    total = 0
                    i = -1
                    while total < extra_encoded:
                        total += len(value[i].encode(encoding))
                        i -= 1
                    size += i + 1
                    value = value[:size]
                    value = _encode(value,firstEncoding=encoding)
                else:
                    value = test
            else:
                value = _encode(value,firstEncoding=firstEncoding)
            out.packSub0(self.subType,value)

#------------------------------------------------------------------------------
class MelLString(MelString):
    """Represents a mod record localized string."""
    def loadData(self,record,ins,type,size,readId):
        value = ins.readLString(size,readId)
        record.__setattr__(self.attr,value)
        if self._debug: print u' ',record.__getattribute__(self.attr)

#------------------------------------------------------------------------------
class MelStrings(MelString):
    """Represents array of strings."""

    def setDefault(self,record):
        """Sets default value for record instance."""
        record.__setattr__(self.attr,[])

    def getDefault(self):
        """Returns a default copy of object."""
        return []

    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        value = ins.readStrings(size,readId)
        record.__setattr__(self.attr,value)
        if self._debug: print u' ',value

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        strings = record.__getattribute__(self.attr)
        if strings:
            out.packSub0(self.subType,null1.join(_encode(x,firstEncoding=bolt.pluginEncoding) for x in strings)+null1)

#------------------------------------------------------------------------------
class MelStruct(MelBase):
    """Represents a structure record."""

    def __init__(self,type,format,*elements,**kwdargs):
        """Initialize."""
        dumpExtra = kwdargs.get('dumpExtra', None)
        self.subType, self.format = type,format
        self.attrs,self.defaults,self.actions,self.formAttrs = self.parseElements(*elements)
        self._debug = False
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
        """Include self if has fids."""
        if self.formAttrs: formElements.add(self)

    def setDefault(self,record):
        """Sets default value for record instance."""
        setter = record.__setattr__
        for attr,value,action in zip(self.attrs, self.defaults, self.actions):
            if action: value = action(value)
            setter(attr,value)

    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        unpacked = ins.unpack(self.format,size,readId)
        setter = record.__setattr__
        for attr,value,action in zip(self.attrs,unpacked,self.actions):
            if action: value = action(value)
            setter(attr,value)
        if self.formatLen >= 0:
            # Dump remaining subrecord data into an attribute
            setter(self.attrs[-1], ins.read(size-self.formatLen))
        if self._debug:
            print u' ',zip(self.attrs,unpacked)
            if len(unpacked) != len(self.attrs):
                print u' ',unpacked

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        values = []
        valuesAppend = values.append
        getter = record.__getattribute__
        for attr,action in zip(self.attrs,self.actions):
            value = getter(attr)
            if action: value = value.dump()
            valuesAppend(value)
        if self.formatLen >= 0:
            extraLen = len(values[-1])
            format = self.format + `extraLen` + 's'
        else:
            format = self.format
        try:
            out.packSub(self.subType,format,*values)
        except struct.error:
            print self.subType,self.format,values
            raise

    def mapFids(self,record,function,save=False):
        """Applies function to fids. If save is true, then fid is set
        to result of function."""
        getter = record.__getattribute__
        setter = record.__setattr__
        for attr in self.formAttrs:
            result = function(getter(attr))
            if save: setter(attr,result)


#------------------------------------------------------------------------------
class MelStructs(MelStruct):
    """Represents array of structured records."""

    def __init__(self,type,format,attr,*elements,**kwdargs):
        """Initialize."""
        MelStruct.__init__(self,type,format,*elements,**kwdargs)
        self.attr = attr

    def getSlotsUsed(self):
        return (self.attr,)

    def getDefaulters(self,defaulters,base):
        """Registers self as a getDefault(attr) provider."""
        defaulters[base+self.attr] = self

    def setDefault(self,record):
        """Sets default value for record instance."""
        record.__setattr__(self.attr,[])

    def getDefault(self):
        """Returns a default copy of object."""
        target = MelObject()
        setter = target.__setattr__
        for attr,value,action in zip(self.attrs, self.defaults, self.actions):
            if callable(action): value = action(value)
            setter(attr,value)
        return target

    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        target = MelObject()
        record.__getattribute__(self.attr).append(target)
        target.__slots__ = self.attrs
        MelStruct.loadData(self,target,ins,type,size,readId)

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        melDump = MelStruct.dumpData
        for target in record.__getattribute__(self.attr):
            melDump(self,target,out)

    def mapFids(self,record,function,save=False):
        """Applies function to fids. If save is true, then fid is set
        to result of function."""
        melMap = MelStruct.mapFids
        if not record.__getattribute__(self.attr): return
        for target in record.__getattribute__(self.attr):
            melMap(self,target,function,save)

#------------------------------------------------------------------------------
class MelStructA(MelStructs):
    """Represents a record with an array of fixed size repeating structured elements."""
    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        if size == 0:
            setattr(record, self.attr, None)
            return
        selfDefault = self.getDefault
        getter = record.__getattribute__
        recordAppend = record.__getattribute__(self.attr).append
        selfAttrs = self.attrs
        itemSize = struct.calcsize(self.format)
        melLoadData = MelStruct.loadData
        for x in xrange(size/itemSize):
            target = selfDefault()
            recordAppend(target)
            target.__slots__ = selfAttrs
            melLoadData(self,target,ins,type,itemSize,readId)

    def dumpData(self,record,out):
        if record.__getattribute__(self.attr) is not None:
            data = ''
            attrs = self.attrs
            format = self.format
            for x in record.__getattribute__(self.attr):
                data += struct.pack(format, *[getattr(x,item) for item in attrs])
            out.packSub(self.subType,data)

    def mapFids(self,record,function,save=False):
        """Applies function to fids. If save is true, then fid is set
        to result of function."""
        if record.__getattribute__(self.attr) is not None:
            melMap = MelStruct.mapFids
            for target in record.__getattribute__(self.attr):
                melMap(self,target,function,save)

#------------------------------------------------------------------------------
class MelTuple(MelBase):
    """Represents a fixed length array that maps to a single subrecord.
    (E.g., the stats array for NPC_ which maps to the DATA subrecord.)"""

    def __init__(self,type,format,attr,defaults):
        """Initialize."""
        self.subType, self.format, self.attr, self.defaults = type, format, attr, defaults
        self._debug = False

    def setDefault(self,record):
        """Sets default value for record instance."""
        record.__setattr__(self.attr,self.defaults[:])

    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        unpacked = ins.unpack(self.format,size,readId)
        record.__setattr__(self.attr,list(unpacked))
        if self._debug: print record.__getattribute__(self.attr)

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        #print self.subType,self.format,self.attr,record.__getattribute__(self.attr)
        out.packSub(self.subType,self.format,*record.__getattribute__(self.attr))

#-------------------------------------------------------------------------------
#-- Common/Special Elements
class MelFull0(MelString):
    """Represents the main full. Use this only when there are additional FULLs
    Which means when record has magic effects."""

    def __init__(self):
        """Initialize."""
        MelString.__init__(self,'FULL','full')

#------------------------------------------------------------------------------
class MelModel(MelGroup):
    """Represents a model record."""
    typeSets = (
        ('MODL','MODB','MODT'),
        ('MOD2','MO2B','MO2T'),
        ('MOD3','MO3B','MO3T'),
        ('MOD4','MO4B','MO4T'),)

    def __init__(self,attr='model',index=0):
        """Initialize. Index is 0,2,3,4 for corresponding type id."""
        types = self.__class__.typeSets[(0,index-1)[index>0]]
        MelGroup.__init__(self,attr,
            MelString(types[0],'modPath'),
            MelStruct(types[1],'f','modb'), ### Bound Radius, Float
            MelBase(types[2],'modt_p'),) ###Texture Files Hashes, Byte Array

    def debug(self,on=True):
        """Sets debug flag on self."""
        for element in self.elements[:2]: element.debug(on)
        return self

#-----------------------------------------------------------------------------
class MelOptStruct(MelStruct):
    """Represents an optional structure, where if values are null, is skipped."""

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        # TODO: Unfortunately, checking if the attribute is None is not
        # really effective.  Checking it to be 0,empty,etc isn't effective either.
        # It really just needs to check it against the default.
        recordGetAttr = record.__getattribute__
        for attr,default in zip(self.attrs,self.defaults):
            oldValue=recordGetAttr(attr)
            if oldValue is not None and oldValue != default:
                MelStruct.dumpData(self,record,out)
                break

# Mod Element Sets -------------------------------------------------------------
#-------------------------------------------------------------------------------
class MelSet:
    """Set of mod record elments."""

    def __init__(self,*elements):
        """Initialize."""
        self._debug = False
        self.elements = elements
        self.defaulters = {}
        self.loaders = {}
        self.formElements = set()
        self.firstFull = None
        self.full0 = None
        for element in self.elements:
            element.getDefaulters(self.defaulters,'')
            element.getLoaders(self.loaders)
            element.hasFids(self.formElements)
            if isinstance(element,MelFull0):
                self.full0 = element

    def debug(self,on=True):
        """Sets debug flag on self."""
        self._debug = on
        return self

    def getSlotsUsed(self):
        """This function returns all of the attributes used in record instances that use this instance."""
        slots = []
        slotsExtend = slots.extend
        for element in self.elements:
            slotsExtend(element.getSlotsUsed())
        return slots

    def initRecord(self,record,header,ins,unpack):
        """Initialize record."""
        for element in self.elements:
            element.setDefault(record)
        MreRecord.__init__(record,header,ins,unpack)

    def getDefault(self,attr):
        """Returns default instance of specified instance. Only useful for
        MelGroup, MelGroups and MelStructs."""
        return self.defaulters[attr].getDefault()

    def loadData(self,record,ins,endPos):
        """Loads data from input stream. Called by load()."""
        doFullTest = (self.full0 != None)
        recType = record.recType
        loaders = self.loaders
        _debug = self._debug
        #--Read Records
        if _debug: print u'\n>>>> %08X' % record.fid
        insAtEnd = ins.atEnd
        insSubHeader = ins.unpackSubHeader
##        fullLoad = self.full0.loadData
        while not insAtEnd(endPos,recType):
            (Type,size) = insSubHeader(recType)
            if _debug: print type,size
            readId = recType + '.' + Type
            try:
                if Type not in loaders:
                    raise ModError(ins.inName,u'Unexpected subrecord: '+repr(readId))
                #--Hack to handle the fact that there can be two types of FULL in spell/ench/ingr records.
                elif doFullTest and Type == 'FULL':
                    self.full0.loadData(record,ins,Type,size,readId)
                else:
                    loaders[Type].loadData(record,ins,Type,size,readId)
                doFullTest = doFullTest and (Type != 'EFID')
            except Exception, error:
                print error
                eid = getattr(record,'eid',u'<<NO EID>>')
                if not eid: eid = u'<<NO EID>>'
                print u'Error loading %s record and/or subrecord: %08X\n  eid = %s\n  subrecord = %s\n  subrecord size = %d\n  file pos = %d' % (repr(record.recType),record.fid,repr(eid),repr(Type),size,ins.tell())
                raise
        if _debug: print u'<<<<',getattr(record,'eid',u'[NO EID]')

    def dumpData(self,record, out):
        """Dumps state into out. Called by getSize()."""
        for element in self.elements:
            try:
                element.dumpData(record,out)
            except:
                bolt.deprint('error dumping data:',traceback=True)
                print u'Dumping:',getattr(record,'eid',u'<<NO EID>>'),record.fid,element
                for attr in record.__slots__:
                    if hasattr(record,attr):
                        print u"> %s: %s" % (attr,repr(getattr(record,attr)))
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
        if not record.longFids: raise bolt.StateError("Fids not in long format")
        def updater(fid):
            masters.add(fid)
        updater(record.fid)
        for element in self.formElements:
            element.mapFids(record,updater)

    def getReport(self):
        """Returns a report of structure."""
        buff = StringIO.StringIO()
        for element in self.elements:
            element.report(None,buff,u'')
        ret = buff.getvalue()
        buff.close()
        return ret

# Mod Records ------------------------------------------------------------------
#-------------------------------------------------------------------------------
class MreSubrecord:
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
        raise bolt.AbstractError

    def dump(self,out):
        if self.changed: raise bolt.StateError(u'Data changed: '+self.subType)
        if not self.data: raise bolt.StateError(u'Data undefined: '+self.subType)
        out.packSub(self.subType,self.data)

#------------------------------------------------------------------------------
class MreRecord(object):
    """Generic Record."""
    subtype_attr = {'EDID':'eid','FULL':'full','MODL':'model'}
    _flags1 = bolt.Flags(0L,bolt.Flags.getNames(
        ( 0,'esm'),
        ( 5,'deleted'),
        ( 6,'borderRegion'),
        ( 7,'turnFireOff'),
        ( 7,'hasStrings'),
        ( 9,'castsShadows'),
        (10,'questItem'),
        (10,'persistent'),
        (11,'initiallyDisabled'),
        (12,'ignored'),
        (15,'visibleWhenDistant'),
        (17,'dangerous'),
        (18,'compressed'),
        (19,'cantWait'),
        ))
    __slots__ = ['header','recType','fid','flags1','size','flags2','changed','subrecords','data','inName','longFids',]
    #--Set at end of class data definitions.
    type_class = None
    simpleTypes = None
    isKeyedByEid = False

    def __init__(self,header,ins=None,unpack=False):
        self.header = header
        self.recType = header.recType
        self.fid = header.fid
        self.flags1 = MreRecord._flags1(header.flags1)
        self.size = header.size
        self.flags2 = header.flags2
        self.longFids = False #--False: Short (numeric); True: Long (espname,objectindex)
        self.changed = False
        self.subrecords = None
        self.data = ''
        self.inName = ins and ins.inName
        if ins: self.load(ins,unpack)

    def __repr__(self):
        if hasattr(self,'eid') and self.eid is not None:
            eid=u' '+self.eid
        else:
            eid=u''
        return u'<%s object: %s (%s)%s>' % (unicode(type(self)).split(u"'")[1], self.recType, strFid(self.fid), eid)

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
            myCopy.load(unpack=True)
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
        size, = struct.unpack('I',self.data[:4])
        decomp = zlib.decompress(self.data[4:])
        if len(decomp) != size:
            raise ModError(self.inName,
                u'Mis-sized compressed data. Expected %d, got %d.'
                % (size,len(decomp)))
        return decomp

    def load(self,ins=None,unpack=False):
        """Load data from ins stream or internal data buffer."""
        type = self.recType
        #--Read, but don't analyze.
        if not unpack:
            self.data = ins.read(self.size,type)
        #--Unbuffered analysis?
        elif ins and not self.flags1.compressed:
            inPos = ins.tell()
            self.data = ins.read(self.size,type)
            ins.seek(inPos,0,type+'_REWIND')
            self.loadData(ins,inPos+self.size)
        #--Buffered analysis (subclasses only)
        else:
            if ins:
                self.data = ins.read(self.size,type)
            if not self.__class__ == MreRecord:
                with self.getReader() as reader:
                    self.loadData(reader,reader.size)
        #--Discard raw data?
        if unpack == 2:
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
        raise bolt.AbstractError(self.recType)

    def updateMasters(self,masters):
        """Updates set of master names according to masters actually used."""
        raise bolt.AbstractError(self.recType)

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
        if self.longFids: raise bolt.StateError(
            u'Packing Error: %s %s: Fids in long format.'
            % (self.recType,self.fid))
        #--Pack data and return size.
        with ModWriter(sio()) as out:
            self.dumpData(out)
            self.data = out.getvalue()
        if self.flags1.compressed:
            dataLen = len(self.data)
            comp = zlib.compress(self.data,6)
            self.data = struct.pack('=I',dataLen) + comp
        self.size = len(self.data)
        self.setChanged(False)
        return self.size

    def dumpData(self,out):
        """Dumps state into data. Called by getSize(). This default version
        just calls subrecords to dump to out."""
        if self.subrecords == None:
            raise bolt.StateError(u'Subrecords not unpacked. [%s: %s %08X]' %
                (self.inName, self.recType, self.fid))
        for subrecord in self.subrecords:
            subrecord.dump(out)

    def dump(self,out):
        """Dumps all data to output stream."""
        if self.changed: raise bolt.StateError(u'Data changed: '+self.recType)
        if not self.data and not self.flags1.deleted and self.size > 0:
            raise bolt.StateError(u'Data undefined: '+self.recType+u' '+hex(self.fid))
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
        """Returns the (stripped) string for a zero-terminated string record."""
        #--Common subtype expanded in self?
        attr = MreRecord.subtype_attr.get(subType)
        value = None #--default
        #--If not MreRecord, then will have info in data.
        if self.__class__ != MreRecord:
            if attr not in self.__slots__: return value
            return self.__getattribute__(attr)
        #--Subrecords available?
        if self.subrecords != None:
            for subrecord in self.subrecords:
                if subrecord.subType == subType:
                    value = bolt.cstrip(subrecord.data)
                    break
        #--No subrecords, but have data.
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
        #--Return it
        return _unicode(value)

#------------------------------------------------------------------------------
class MelRecord(MreRecord):
    """Mod record built from mod record elements."""
    melSet = None #--Subclasses must define as MelSet(*mels)
    __slots__ = MreRecord.__slots__

    def __init__(self,header,ins=None,unpack=False):
        """Initialize."""
        self.__class__.melSet.initRecord(self,header,ins,unpack)

    def getDefault(self,attr):
        """Returns default instance of specified instance. Only useful for
        MelGroup, MelGroups and MelStructs."""
        return self.__class__.melSet.getDefault(attr)

    def loadData(self,ins,endPos):
        """Loads data from input stream. Called by load()."""
        self.__class__.melSet.loadData(self,ins,endPos)

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

#-------------------------------------------------------------------------------
#-- Common Records

#-------------------------------------------------------------------------------
class MreHeaderBase(MelRecord):
    """File header.  Base class for all 'TES4' like records"""
    #--Masters array element
    class MelMasterName(MelBase):
        def setDefault(self,record): record.masters = []
        def loadData(self,record,ins,type,size,readId):
            # Don't use ins.readString, becuase it will try to use bolt.pluginEncoding
            # for the filename.  This is one case where we want to use Automatic
            # encoding detection
            name = _unicode(bolt.cstrip(ins.read(size,readId)),avoidEncodings=('utf8','utf-8'))
            name = GPath(name)
            record.masters.append(name)
        def dumpData(self,record,out):
            pack1 = out.packSub0
            pack2 = out.packSub
            for name in record.masters:
                pack1('MAST',_encode(name.s))
                pack2('DATA','Q',0)

    def getNextObject(self):
        """Gets next object index and increments it for next time."""
        self.changed = True
        self.nextObject += 1
        return (self.nextObject -1)

    __slots__ = MelRecord.__slots__

#-------------------------------------------------------------------------------
class MreGlob(MelRecord):
    """Global record.  Rather stupidly all values, despite their designation
       (short,long,float), are stored as floats -- which means that very large
       integers lose precision."""
    classType = 'GLOB'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('FNAM','s',('format','s')),
        MelStruct('FLTV','f','value'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#-------------------------------------------------------------------------------
class MreGmstBase(MelRecord):
    """Game Setting record.  Base class, each game should derive from this class
       and set class member 'Master' to the file name of the game's main master
       file."""
    Master = None
    Ids = None
    classType = 'GMST'
    class MelGmstValue(MelBase):
        def loadData(self,record,ins,type,size,readId):
            format = _encode(record.eid[0]) #-- s|i|f|b
            if format == u's':
                record.value = ins.readLString(size,readId)
                return
            elif format == u'b':
                format = u'I'
            record.value, = ins.unpack(format,size,readId)
        def dumpData(self,record,out):
            format = _encode(record.eid[0]) #-- s|i|f
            if format == u's':
                out.packSub0(self.subType,record.value)
                return
            elif format == u'b':
                format = u'I'
            out.packSub(self.subType,format,record.value)
    melSet = MelSet(
        MelString('EDID','eid'),
        MelGmstValue('DATA','value'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

    def getGMSTFid(self):
        """Returns <Oblivion/Skyrim/etc>.esm fid in long format for specified
           eid."""
        cls = self.__class__
        if not cls.Ids:
            try:
                fname = cls.Master+u'_ids.pkl'
                import bosh # Late import to avoid circular imports
                cls.Ids = cPickle.load(bosh.dirs['db'].join(fname).open())[cls.classType]
            except:
                old = bolt.deprintOn
                bolt.deprintOn = True
                bolt.deprint(u'Error loading %s:' % fname, traceback=True)
                raise
        return (GPath(cls.Master+u'.esm'),cls.Ids[self.eid])

#-------------------------------------------------------------------------------
class MreLeveledListBase(MelRecord):
    """Base type for leveled item/creature/npc/spells.
       it requires the base class to use the following:
       classAttributes:
          copyAttrs -> List of attributes to modify by copying when merging
       instanceAttributes:
          entries -> List of items, with the following attributes:
              listId
              level
              count
          chanceNone
          flags
    """
    _flags = bolt.Flags(0L,bolt.Flags.getNames('calcFromAllLevels','calcForEachItem','useAllSpells'))
    copyAttrs = ()
    __slots__ = (MelRecord.__slots__ +
        ['mergeOverLast','mergeSources','items','delevs','relevs'])

    def __init__(self,header,ins=None,unpack=False):
        """Initialize"""
        MelRecord.__init__(self,header,ins,unpack)
        self.mergeOverLast = False #--Merge overrides last mod merged
        self.mergeSources = None #--Set to list by other functions
        self.items  = None #--Set of items included in list
        self.delevs = None #--Set of items deleted by list (Delev and Relev mods)
        self.relevs = None #--Set of items relevelled by list (Relev mods)

    def mergeFilter(self,modSet):
        """Filter out items that don't come from specified modSet."""
        if not self.longFids: raise bolt.StateError(u'Fids not in long format')
        self.entries = [entry for entry in self.entries if entry.listId[0] in modSet]

    def mergeWith(self,other,otherMod):
        """Merges newLevl settings and entries with self.
        Requires that: self.items, other.delevs and other.relevs be defined."""
        if not self.longFids or not other.longFids:
            raise bolt.StateError(u'Fids not in long format')
        #--Relevel or not?
        if other.relevs:
            for attr in self.__class__.copyAttrs:
                self.__setattr__(attr,other.__getattribute__(attr))
            self.flags = other.flags()
        else:
            for attr in self.__class__.copyAttrs:
                self.__setattr__(attr,other.__getattribute__(attr) or
                                       self.__getattribute__(attr))
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
        if newItems:
            self.items |= newItems
            self.entries.sort(key=attrgetter('listId','level','count'))
        #--Is merged list different from other? (And thus written to patch.)
        if ((len(self.entries) != len(other.entries)) or
            (self.flags != other.flags)
            ):
            self.mergeOverLast = True
        else:
            for attr in self.__class__.copyAttrs:
                if self.__getattribute__(attr) != other.__getattribute__(attr):
                    self.mergeOverLast = True
                    break
            else:
                otherlist = other.entries
                otherlist.sort(key=attrgetter('listId','level','count'))
                for selfEntry,otherEntry in zip(self.entries,otherlist):
                    if (selfEntry.listId != otherEntry.listId or
                        selfEntry.level != otherEntry.level or
                        selfEntry.count != otherEntry.count):
                        self.mergeOverLast = True
                        break
                else:
                    self.mergeOverLast = False
        if self.mergeOverLast:
            self.mergeSources.append(otherMod)
        else:
            self.mergeSources = [otherMod]
        #--Done
        self.setChanged(self.mergeOverLast)
