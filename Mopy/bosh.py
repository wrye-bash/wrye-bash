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
#  Wrye Bash copyright (C) 2005, 2006, 2007, 2008, 2009 Wrye
#
# =============================================================================

"""This module defines provides objects and functions for working with Oblivion
files and environment. It does not provide interface functions which instead
provided by separate modules: bish for CLI and bash/basher for GUI."""

# Localization ----------------------------------------------------------------
#--Not totally clear on this, but it seems to safest to put locale first...
import locale; locale.setlocale(locale.LC_ALL,'')
#locale.setlocale(locale.LC_ALL,'German')
#locale.setlocale(locale.LC_ALL,'Japanese_Japan.932')
import time
import operator

def formatInteger(value):
    """Convert integer to string formatted to locale."""
    return locale.format('%d',int(value),1)

def formatDate(value):
    """Convert time to string formatted to to locale's default date/time."""
    localtime = time.localtime(value)
    return time.strftime('%c',localtime)

def unformatDate(str,format):
    """Basically a wrapper around time.strptime. Exists to get around bug in
    strptime for Japanese locale."""
    try:
        return time.strptime(str,'%c')
    except ValueError:
        if format == '%c' and 'Japanese' in locale.getlocale()[0]:
            str = re.sub('^([0-9]{4})/([1-9])',r'\1/0\2',str)
            return time.strptime(str,'%c')
        else:
            raise

# Imports ---------------------------------------------------------------------
#--Python
import cPickle
import cStringIO
import ConfigParser
import copy
import datetime
import math
import os
import random
import re
import shutil
import string
import struct
import sys
from types import *
from operator import attrgetter,itemgetter

#--Local
import balt
import bolt
import bush
from bolt import BoltError, AbstractError, ArgumentError, StateError, UncodedError
from bolt import _, LString, GPath, Flags, DataDict, SubProgress, cstrip, deprint, delist

# Singletons, Constants -------------------------------------------------------
#--Constants
#..Bit-and this with the fid to get the objectindex.
oiMask = 0xFFFFFFL

#--File Singletons
oblivionIni = None
modInfos  = None  #--ModInfos singleton
saveInfos = None #--SaveInfos singleton
iniInfos = None #--INIInfos singleton
BSAInfos = None #--BSAInfos singleton
screensData = None #--ScreensData singleton
bsaData = None #--bsaData singleton
messages = None #--Message archive singleton
configHelpers = None #--Config Helper files (Boss Master List, etc.)

#--Settings
dirs = {} #--app, user, mods, saves, userApp
inisettings = {}
defaultExt = '.7z'
writeExts = dict({'.7z':'7z','.zip':'zip'})
readExts = set(('.rar',))
readExts.update(set(writeExts))
noSolidExts = set(('.zip',))
settings  = None

#--Default settings
settingDefaults = {
    'bosh.modInfos.resetMTimes':True,
    }

# Errors ----------------------------------------------------------------------
#------------------------------------------------------------------------------
class FileError(BoltError):
    """TES4/Tes4SaveFile Error: File is corrupted."""
    def __init__(self,inName,message):
        BoltError.__init__(self,message)
        self.inName = inName

    def __str__(self):
        if self.inName:
            return self.inName.s+': '+self.message
        else:
            return _('Unknown File: ')+self.message

#------------------------------------------------------------------------------
class FileEditError(BoltError):
    """Unable to edit a file"""
    def __init__(self,filePath,message=None):
        message = message or _("Unable to edit file %s.") % filePath.s
        BoltError.__init__(self,message)
        self.filePath = filePath

# Util Classes ----------------------------------------------------------------
#------------------------------------------------------------------------------
class CountDict(dict):
    """Used for storing counts. Just adds an increment function."""
    def increment(self,key,inc=1):
        """Increment specified key by 1, after initializing to zero if necessary."""
        if not inc: return
        if not key in self: self[key] = 0
        self[key] += inc

#------------------------------------------------------------------------------
class Path(str):
    """OBSOLETE. This has been replaced by bolt.Path. Retained for backward
    compatibility with old pickle files."""
    def __init__(self, path):
        """Initialize."""
        raise "Path necromancy!"

    def __getstate__(self):
        """Used by pickler. State is determined by underlying string, so return psempty tuple."""
        return (0,) #--Pseudo empty. If tuple were actually empty, then setstate wouldn't be run.

    def __setstate__(self,state):
        """Used by unpickler. Ignore state and reset from value of underlying string."""
        path = str(self)
        self._path = path
        self._pathLC = path.lower()
        self._pathNormLC = os.path.normpath(path).lower()

    def __repr__(self):
        return "bosh.Path("+repr(self._path)+")"

#------------------------------------------------------------------------------
class PickleDict(bolt.PickleDict):
    """Dictionary saved in a pickle file. Supports older bash pickle file formats."""
    def __init__(self,path,oldPath=None,readOnly=False):
        """Initialize."""
        bolt.PickleDict.__init__(self,path,readOnly)
        self.oldPath = oldPath or GPath('')

    def exists(self):
        """See if pickle file exists."""
        return (bolt.PickleDict.exists(self) or self.oldPath.exists())

    def load(self):
        """Loads vdata and data from file or backup file.

        If file does not exist, or is corrupt, then reads from backup file. If
        backup file also does not exist or is corrupt, then no data is read. If
        no data is read, then self.data is cleared.

        If file exists and has a vdata header, then that will be recorded in
        self.vdata. Otherwise, self.vdata will be empty.

        Returns:
          0: No data read (files don't exist and/or are corrupt)
          1: Data read from file
          2: Data read from backup file
        """
        result = bolt.PickleDict.load(self)
        if not result and self.oldPath.exists():
            ins = None
            try:
                ins = self.oldPath.open('r')
                self.data.update(cPickle.load(ins))
                ins.close()
                result = 1
            except EOFError:
                if ins: ins.close()
        #--Update paths
        def textDump(path):
            deprint('Text dump:',path)
            out = path.open('w')
            for key,value in self.data.iteritems():
                out.write('= '+`key`+':\n  '+`value`+'\n')
            out.close()
        #textDump(self.path+'.old.txt')
        if not self.vdata.get('boltPaths',False):
            self.updatePaths()
            self.vdata['boltPaths'] = True
        #textDump(self.path+'.new.txt')
        #--Done
        return result

    def updatePaths(self):
        """Updates paths from bosh.Path to bolt.Path."""
        import wx
        basicTypes = set((NoneType,FloatType,IntType,LongType,BooleanType,StringType,UnicodeType))
        SetType = type(set())
        done = {}
        changed = set()
        def update(x):
            xid = id(x)
            xtype = type(x)
            if xid in done:
                return done[xid]
            elif xtype in basicTypes:
                return x
            elif xtype == ListType:
                xnew = [update(value) for value in x]
                x[:] = xnew
                xnew = x
            elif xtype == SetType:
                xnew = set(update(value) for value in x)
                xnew.discard(None) #--In case it got added in else clause.
                x.clear()
                x.update(xnew)
                xnew = x
            elif xtype == DictType:
                xnew = dict((update(key),update(value)) for key,value in x.iteritems())
                xnew.pop(None,None) #--In case it got added in else clause.
                x.clear()
                x.update(xnew)
                xnew = x
            elif xtype == TupleType:
                xnew = tuple(update(value) for value in x)
            elif isinstance(x,wx.Point): #--Replace old wx.Points w nice python tuples.
                xnew = x.Get()
            elif isinstance(x,Path):
                changed.add(x._path)
                xnew = GPath(x._path)
            else:
                #raise StateError('Unknown type: %s %s' % (xtype,x))
                xnew = None #--Hopefully this will work for few old incompatibilties.
            return done.setdefault(xid,xnew)
        update(self.data)

    def save(self):
        """Save to pickle file."""
        saved = bolt.PickleDict.save(self)
        if saved:
            self.oldPath.remove()
            self.oldPath.backup.remove()
        return saved

# Util Constants --------------------------------------------------------------
#--Null strings (for default empty byte arrays)
null1 = '\x00'
null2 = null1*2
null3 = null1*3
null4 = null1*4

#--Header tags
reGroup = re.compile(r'^Group: *(.*)',re.M)
reRequires = re.compile(r'^Requires: *(.*)',re.M)
reReqItem = re.compile(r'^([a-zA-Z]+) *([0-9]*\.?[0-9]*)$')
reVersion = re.compile(r'^(Version:?) *([-0-9a-zA-Z\.]*\+?)',re.M)

#--Mod Extensions
reComment = re.compile('#.*')
reExGroup = re.compile('(.*?),')
reImageExt = re.compile(r'\.(gif|jpg|bmp|png)$',re.I)
reModExt  = re.compile(r'\.es[mp](.ghost)?$',re.I)
reEsmExt  = re.compile(r'\.esm(.ghost)?$',re.I)
reEspExt  = re.compile(r'\.esp(.ghost)?$',re.I)
reBSAExt  = re.compile(r'\.bsa(.ghost)?$',re.I)
reEssExt  = re.compile(r'\.ess$',re.I)
reSaveExt = re.compile(r'(quicksave(\.bak)+|autosave(\.bak)+|\.es[rs])$',re.I)
reCsvExt  = re.compile(r'\.csv$',re.I)
reINIExt  = re.compile(r'\.ini$',re.I)
reQuoted  = re.compile(r'^"(.*)"$')
reGroupHeader = re.compile(r'^(\+\+|==)')
reTesNexus = re.compile(r'-(\d{4,6})(\.tessource)?(-bain)?\.(7z|zip|rar)$',re.I)
reTESA = re.compile(r'-(\d{1,6})(\.tessource)?(-bain)?\.(7z|zip|rar)$',re.I)
reSplitOnNonAlphaNumeric = re.compile(r'\W+')


# Util Functions --------------------------------------------------------------
# .Net strings
def netString(x):
    """Encode a string into a .net string."""
    lenx = len(x)
    if lenx < 128:
        return struct.pack('b',lenx)+x
    elif lenx > 0x7FFF: #--Actually probably fails earlier.
        raise UncodedError
    else:
        lenx =  x80 | lenx & 0x7f | (lenx & 0xff80) << 1
        return struct.pack('H',lenx)+x

# Groups
reSplitModGroup = re.compile(r'^(.+?)([-+]\d+)?$')

def splitModGroup(offGroup):
    """Splits a full group name into a group name and an integer offset.
    E.g. splits 'Overhaul+1' into ('Overhaul',1)."""
    if not offGroup: return ('',0)
    maSplitModGroup = reSplitModGroup.match(offGroup)
    group = maSplitModGroup.group(1)
    offset = int(maSplitModGroup.group(2) or 0)
    return (group,offset)

def joinModGroup(group,offset):
    """Combines a group and offset into a full group name."""
    if offset < 0:
        return group+`offset`
    elif offset > 0:
        return group+'+'+`offset`
    else:
        return group

# Reference (Fid)
def strFid(fid):
    """Returns a string representation of the fid."""
    if isinstance(fid,tuple):
        return '(%s,0x%06X)' % (fid[0].s,fid[1])
    else:
        return '%08X' % fid

def genFid(modIndex,objectIndex):
    """Generates fid from modIndex and ObjectIndex."""
    return long(objectIndex) | (long(modIndex) << 24 )

def getModIndex(fid):
    """Return the modIndex portion of a fid."""
    return int(fid >> 24)

def getObjectIndex(fid):
    """Return the objectIndex portion of a fid."""
    return int(fid & 0xFFFFFFL)

def getFormIndices(fid):
    """Returns tuple of modindex and objectindex of fid."""
    return (int(fid >> 24),int(fid & 0xFFFFFFL))

# Mod I/O --------------------------------------------------------------------
#------------------------------------------------------------------------------
class ModError(FileError):
    """Mod Error: File is corrupted."""
    pass

#------------------------------------------------------------------------------
class ModReadError(ModError):
    """TES4 Error: Attempt to read outside of buffer."""
    def __init__(self,inName,recType,tryPos,maxPos):
        self.recType = recType
        self.tryPos = tryPos
        self.maxPos = maxPos
        if tryPos < 0:
            message = (_('%s: Attempted to read before (%d) beginning of file/buffer.')
                % (recType,tryPos))
        else:
            message = (_('%s: Attempted to read past (%d) end (%d) of file/buffer.') %
                (recType,tryPos,maxPos))
        ModError.__init__(self,inName.s,message)

#------------------------------------------------------------------------------
class ModSizeError(ModError):
    """TES4 Error: Record/subrecord has wrong size."""
    def __init__(self,inName,recType,readSize,maxSize,exactSize=True):
        self.recType = recType
        self.readSize = readSize
        self.maxSize = maxSize
        self.exactSize = exactSize
        if exactSize:
            messageForm = _('%s: Expected size == %d, but got: %d ')
        else:
            messageForm = _('%s: Expected size <= %d, but got: %d ')
        ModError.__init__(self,inName.s,messageForm % (recType,readSize,maxSize))


#------------------------------------------------------------------------------
class ModUnknownSubrecord(ModError):
    """TES4 Error: Uknown subrecord."""
    def __init__(self,inName,subType,recType):
        ModError.__init__(self,_('Extraneous subrecord (%s) in %s record.')
            % (subType,recType))

#------------------------------------------------------------------------------
class ModReader:
    """Wrapper around an TES4 file in read mode.
    Will throw a ModReadError if read operation fails to return correct size."""
    def __init__(self,inName,ins):
        """Initialize."""
        self.inName = inName
        self.ins = ins
        #--Get ins size
        curPos = ins.tell()
        ins.seek(0,2)
        self.size = ins.tell()
        ins.seek(curPos)

    #--IO Stream ------------------------------------------
    def seek(self,offset,whence=0,recType='----'):
        """File seek."""
        if whence == 1:
            newPos = self.ins.tell()+offset
        elif whence == 2:
            newPos = self.size + offset
        else:
            newPos = offset
        if newPos < 0 or newPos > self.size:
            raise ModReadError(self.inName, recType,newPos,self.size)
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
            raise ModError(self.inName, _('Exceded limit of: ')+recType)
        else:
            return (filePos == endPos)

    #--Read/unpack ----------------------------------------
    def read(self,size,recType='----'):
        """Read from file."""
        endPos = self.ins.tell() + size
        if endPos > self.size:
            raise ModSizeError(self.inName, recType,endPos,self.size)
        return self.ins.read(size)

    def readString(self,size,recType='----'):
        """Read string from file, stripping zero terminator."""
        return cstrip(self.read(size,recType))

    def readStrings(self,size,recType='----'):
        """Read strings from file, stripping zero terminator."""
        return self.read(size,recType).rstrip(null1).split(null1)
    
    def unpack(self,format,size,recType='----'):
        """Read file and unpack according to struct format."""
        endPos = self.ins.tell() + size
        if endPos > self.size:
            raise ModReadError(self.inName, recType,endPos,self.size)
        return struct.unpack(format,self.ins.read(size))

    def unpackRef(self,recType='----'):
        """Read a ref (fid)."""
        return self.unpack('I',4)[0]

    def unpackRecHeader(self):
        """Unpack a record header."""
        (type,size,uint0,uint1,uint2) = self.unpack('4s4I',20,'REC_HEAD')
        #--Bad?
        if type not in bush.recordTypes:
            raise ModError(self.inName,_('Bad header type: ')+type)
        #print (type,size,uint0,uint1,uint2)
        #--Record
        if type != 'GRUP':
            return (type,size,uint0,uint1,uint2)
        #--Top Group
        elif uint1 == 0:
            str0 = struct.pack('I',uint0)
            if str0 in bush.topTypes:
                return (type,size,str0,uint1,uint2)
            elif str0 in bush.topIgTypes:
                return (type,size,bush.topIgTypes[str0],uint1,uint2)
            else:
                raise ModError(self.inName,_('Bad Top GRUP type: ')+str0)
        #--Other groups
        else:
            return (type,size,uint0,uint1,uint2)

    def unpackSubHeader(self,recType='----',expType=None,expSize=0):
        """Unpack a subrecord header. Optionally checks for match with expected type and size."""
        selfUnpack = self.unpack
        (type,size) = selfUnpack('4sH',6,recType+'.SUB_HEAD')
        #--Extended storage?
        while type == 'XXXX':
            size = selfUnpack('I',4,recType+'.XXXX.SIZE.')[0]
            type = selfUnpack('4sH',6,recType+'.XXXX.TYPE')[0] #--Throw away size (always == 0)
        #--Match expected name?
        if expType and expType != type:
            raise ModError(self.inName,_('%s: Expected %s subrecord, but found %s instead.')
                % (recType,expType,type))
        #--Match expected size?
        if expSize and expSize != size:
            raise ModSizeError(self.inName,recType+'.'+type,size,expSize,True)
        return (type,size)

    #--Find data ------------------------------------------
    def findSubRecord(self,subType,recType='----'):
        """Finds subrecord with specified type."""
        selfAtEnd = self.atEnd
        selfUnpack = self.unpack
        selfSeek = self.seek
        while not selfAtEnd():
            (type,size) = selfUnpack('4sH',6,recType+'.SUB_HEAD')
            if type == subType:
                return self.read(size,recType+'.'+subType)
            else:
                selfSeek(size,1,recType+'.'+type)
        #--Didn't find it?
        else:
            return None

#------------------------------------------------------------------------------
class ModWriter:
    """Wrapper around an TES4 output stream. Adds utility functions."""
    reValidType = re.compile('^[A-Z]{4}$')

    def __init__(self,out):
        """Initialize."""
        self.out = out

    #--Stream Wrapping
    def write(self,data):
        self.out.write(data)

    def tell(self):
        return self.out.tell()

    def seek(self,offset,whence=0):
        return self.out.seek(offset,whence)

    def getvalue(self):
        return self.out.getvalue()

    def close(self):
        self.out.close()

    #--Additional functions.
    def pack(self,format,*data):
        self.out.write(struct.pack(format,*data))

    def packSub(self,type,data,*values):
        """Write subrecord header and data to output stream.
        Call using either packSub(type,data), or packSub(type,format,values).
        Will automatically add a prefacing XXXX size subrecord to handle data
        with size > 0xFFFF."""
        #if not ModWriter.reValidType.match(type): raise _('Invalid type: ') + `type`
        try:
            if data == None: return
            structPack = struct.pack
            if values: data = structPack(data,*values)
            outWrite = self.out.write
            if len(data) <= 0xFFFF:
                outWrite(structPack('=4sH',type,len(data)))
                outWrite(data)
            else:
                outWrite(structPack('=4sHI','XXXX',4,len(data)))
                outWrite(structPack('=4sH',type,0))
                outWrite(data)
        except Exception, e:
            print e
            print self,type,data,values

    def packSub0(self,type,data):
        """Write subrecord header plus zero terminated string to output stream."""
        #if not ModWriter.reValidType.match(type): raise _('Invalid type: ') + `type`
        if data == None: return
        lenData = len(data) + 1
        outWrite = self.out.write
        structPack = struct.pack
        if lenData <= 0xFFFF:
            outWrite(structPack('=4sH',type,lenData))
        else:
            outWrite(structPack('=4sHI','XXXX',4,lenData))
            outWrite(structPack('=4sH',type,0))
        outWrite(data)
        outWrite('\x00')

    def packRef(self,type,fid):
        """Write subrecord header and fid reference."""
        #if not ModWriter.reValidType.match(type): raise _('Invalid type: ') + `type`
        if fid != None: self.out.write(struct.pack('=4sHI',type,4,fid))

    def writeGroup(self,size,label,groupType,stamp):
        if type(label) is str:
            self.pack('=4sI4sII','GRUP',size,label,groupType,stamp)
        elif type(label) is tuple:
            self.pack('=4sIhhII','GRUP',size,label[1],label[0],groupType,stamp)
        else:
            self.pack('=4s4I','GRUP',size,label,groupType,stamp)


# Mod Record Elements ---------------------------------------------------------
# Constants
FID = 'FID' #--Used by MelStruct classes to indicate fid elements.

#------------------------------------------------------------------------------
class MelObject(object):
    """An empty class used by group and structure elements for data storage."""
    def __eq__(self,other):
        """Operator: =="""
        return isinstance(other,MelObject) and self.__dict__ == other.__dict__

    def __ne__(self,other):
        """Operator: !="""
        return not (isinstance(other,MelObject) and self.__dict__ == other.__dict__)

#------------------------------------------------------------------------------
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
        attrs,defaults,actions = [0]*len(elements),[0]*len(elements),[0]*len(elements)
        formAttrsAppend = formAttrs.append
        for index,element in enumerate(elements):
            if not isinstance(element,tuple): element = (element,)
            if element[0] == FID:
                formAttrsAppend(element[1])
            elif callable(element[0]):
                actions[index] = element[0]
            attrIndex = (0,1)[callable(element[0]) or element[0] in (FID,0)]
            attrs[index] = element[attrIndex]
            defaults[index] = (0,element[-1])[len(element)-attrIndex == 2]
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
        if self._debug: print `record.__getattribute__(self.attr)`

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        value = record.__getattribute__(self.attr)
        if value != None: out.packSub(self.subType,value)

    def mapFids(self,record,function,save=False):
        """Applies function to fids. If save is True, then fid is set
        to result of function."""
        raise AbstractError
    def getDelta(self,newRecord,oldRecord):
        if getattr(newRecord,self.attr,None) != getattr(oldRecord,self.attr,None):
            return [(self.attr, getattr(oldRecord,self.attr,None), getattr(newRecord,self.attr,None))]
        return None
#------------------------------------------------------------------------------
class MelFid(MelBase):
    """Represents a mod record fid element."""

    def hasFids(self,formElements):
        """Include self if has fids."""
        formElements.add(self)

    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        record.__setattr__(self.attr,ins.unpackRef(readId))
        if self._debug: print '  %08X' % (record.__getattribute__(self.attr),)

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
        if self._debug: print ' ',hex(fid)

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
                print '  %08X' % fid

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        fids = record.__getattribute__(self.attr)
        if not fids: return
        out.packSub(self.subType,`len(fids)`+'I',*fids)

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
    def getDelta(self,newRecord,oldRecord):
        if getattr(newRecord,self.attr,None) is None and getattr(oldRecord,self.attr,None) is None:
            return None
        delta = []
        def listCompare(self,newList,oldList):
            if oldList is None:
                added = newList
                removed = []
            elif newList is None:
                added = []
                removed = oldList
            else:
                added = bolt.listSubtract(newList,oldList)
                removed = bolt.listSubtract(oldList,newList)
            if len(added) == 0 and len(removed) == 0:
                return [],[],[]
            newValues = dict([(getattr(item,item.__slots__[0]), item) for item in added])
            oldValues = dict([(getattr(item,item.__slots__[0]), item) for item in removed])
            removed += added
            added = []
            changed = []
            for item in newValues:
                if item in oldValues:
                    changed.append((oldValues[item],newValues[item]))
                    removed.remove(newValues[item])
                    removed.remove(oldValues[item])
                else:
                    added.append(newValues[item])
                    removed.remove(newValues[item])
            return added, removed, changed
        added,removed,changed = listCompare(self,getattr(newRecord,self.attr,None),getattr(oldRecord,self.attr,None))
        for item in added:
            subDelta = []
            for slot in item.__slots__:
                subDelta.append((slot, None,getattr(item,slot,None)))
            delta.append((self.attr,getattr(item,item.__slots__[0]),subDelta[:]))
        for item in removed:
            subDelta = []
            for slot in item.__slots__:
                subDelta.append((slot,getattr(item,slot,None), None))
            delta.append((self.attr,getattr(item,item.__slots__[0]),subDelta[:]))
        for item in changed:
            subDelta = []
            for slot in item[0].__slots__:
                if getattr(item[0],slot,None) != getattr(item[1],slot,None):
                    subDelta.append((slot, getattr(item[0],slot,None),getattr(item[1],slot,None)))
            delta.append((self.attr,getattr(item[0],item[0].__slots__[0]),subDelta[:]))
        if len(delta) > 0: return delta
        return None

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
        if self._debug: print ' ',record.fid,`junk`

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
        if self._debug: print ' ',strFid(record.fid),strFid(xpci),full

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
        if self._debug: print ' ',record.__getattribute__(self.attr)

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        value = record.__getattribute__(self.attr)
        if value != None:
            if self.maxSize:
                value = bolt.winNewLines(value.rstrip())
                value = value[:min(self.maxSize,len(value))]
            out.packSub0(self.subType,value)

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
        if self._debug: print ' ',value

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        strings = record.__getattribute__(self.attr)
        if strings:
            out.packSub0(self.subType,null1.join(strings)+null1)

#------------------------------------------------------------------------------
class MelStruct(MelBase):
    """Represents a structure record."""

    def __init__(self,type,format,*elements):
        """Initialize."""
        self.subType, self.format = type,format
        self.attrs,self.defaults,self.actions,self.formAttrs = self.parseElements(*elements)
        self._debug = False

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
        if self._debug:
            print ' ',zip(self.attrs,unpacked)
            if len(unpacked) != len(self.attrs):
                print ' ',unpacked

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        values = []
        valuesAppend = values.append
        getter = record.__getattribute__
        for attr,action in zip(self.attrs,self.actions):
            value = getter(attr)
            if action: value = value.dump()
            valuesAppend(value)
        try:
            out.packSub(self.subType,self.format,*values)
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
    def getDelta(self,newRecord,oldRecord):
        delta = []
        for attr in self.attrs:
            if getattr(newRecord,attr,None) != getattr(oldRecord,attr,None):
                delta.append((attr, getattr(oldRecord,attr,None), getattr(newRecord,attr,None)))
        if len(delta) > 0: return delta
        return None
#------------------------------------------------------------------------------
class MelStructs(MelStruct):
    """Represents array of structured records."""

    def __init__(self,type,format,attr,*elements):
        """Initialize."""
        MelStruct.__init__(self,type,format,*elements)
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
            
    def getDelta(self,newRecord,oldRecord):
        if getattr(newRecord,self.attr,None) is None and getattr(oldRecord,self.attr,None) is None:
            return None
        delta = []
        def listCompare(self,newList,oldList):
            if oldList is None:
                added = newList
                removed = []
            elif newList is None:
                added = []
                removed = oldList
            else:
                added = bolt.listSubtract(newList,oldList)
                removed = bolt.listSubtract(oldList,newList)
            if len(added) == 0 and len(removed) == 0:
                return [],[],[]
            newValues = dict([(getattr(item,self.attrs[0]), item) for item in added])
            oldValues = dict([(getattr(item,self.attrs[0]), item) for item in removed])
            removed += added
            added = []
            changed = []
            for item in newValues:
                if item in oldValues:
                    changed.append((oldValues[item],newValues[item]))
                    removed.remove(newValues[item])
                    removed.remove(oldValues[item])
                else:
                    added.append(newValues[item])
                    removed.remove(newValues[item])
            return added, removed, changed
        added,removed,changed = listCompare(self,getattr(newRecord,self.attr,None),getattr(oldRecord,self.attr,None))
        for item in added:
            subDelta = []
            for slot in self.attrs:
                subDelta.append((slot, None,getattr(item,slot,None)))
            delta.append((self.attr,getattr(item,self.attrs[0]),subDelta[:]))
        for item in removed:
            subDelta = []
            for slot in self.attrs:
                subDelta.append((slot,getattr(item,slot,None), None))
            delta.append((self.attr,getattr(item,self.attrs[0]),subDelta[:]))
            print 'hrm'
            print delta
            sys.exit()
        for item in changed:
            subDelta = []
            for slot in self.attrs:
                if getattr(item[0],slot,None) != getattr(item[1],slot,None):
                    subDelta.append((slot, getattr(item[0],slot,None),getattr(item[1],slot,None)))
            delta.append((self.attr,getattr(item[0],self.attrs[0]),subDelta[:]))
        if len(delta) > 0: return delta
        return None
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
        for x in range(size/itemSize):
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

#------------------------------------------------------------------------------
# Common/Special Elements

#------------------------------------------------------------------------------
class MelConditions(MelStructs):
    """Represents a set of quest/dialog conditions. Difficulty is that FID state
    of parameters depends on function index."""
    def __init__(self):
        """Initialize."""
        MelStructs.__init__(self,'CTDA','B3sfIii4s','conditions',
            'operFlag',('unused1',null3),'compValue','ifunc','param1','param2',('unused2',null4))

    def getLoaders(self,loaders):
        """Adds self as loader for type."""
        loaders[self.subType] = self
        loaders['CTDT'] = self #--Older CTDT type for ai package records.

    def getDefault(self):
        """Returns a default copy of object."""
        target = MelStructs.getDefault(self)
        target.form12 = 'ii'
        return target

    def hasFids(self,formElements):
        """Include self if has fids."""
        formElements.add(self)

    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        if type == 'CTDA' and size != 24:
            raise ModSizeError(ins.inName,readId,24,size,True)
        if type == 'CTDT' and size != 20:
            raise ModSizeError(ins.inName,readId,20,size,True)
        target = MelObject()
        record.conditions.append(target)
        target.__slots__ = self.attrs
        unpacked1 = ins.unpack('B3sfI',12,readId)
        (target.operFlag,target.unused1,target.compValue,ifunc) = unpacked1
        #--Get parameters
        if ifunc not in bush.allConditions:
            raise BoltError(_('Unknown condition function: %d') % ifunc)
        form1 = 'iI'[ifunc in bush.fid1Conditions]
        form2 = 'iI'[ifunc in bush.fid2Conditions]
        form12 = form1+form2
        unpacked2 = ins.unpack(form12,8,readId)
        (target.param1,target.param2) = unpacked2
        if size == 24:
            target.unused2 = ins.read(4)
        else:
            target.unused2 = null4
        (target.ifunc,target.form12) = (ifunc,form12)
        if self._debug:
            unpacked = unpacked1+unpacked2
            print ' ',zip(self.attrs,unpacked)
            if len(unpacked) != len(self.attrs):
                print ' ',unpacked

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        for target in record.conditions:
##            format = 'B3sfI'+target.form12+'4s'
            out.packSub('CTDA','B3sfI'+target.form12+'4s',
                target.operFlag, target.unused1, target.compValue,
                target.ifunc, target.param1, target.param2, target.unused2)

    def mapFids(self,record,function,save=False):
        """Applies function to fids. If save is true, then fid is set
        to result of function."""
        for target in record.conditions:
            form12 = target.form12
            if form12[0] == 'I':
                result = function(target.param1)
                if save: target.param1 = result
            if form12[1] == 'I':
                result = function(target.param2)
                if save: target.param2 = result

#------------------------------------------------------------------------------
class MelEffects(MelGroups):
    """Represents ingredient/potion/enchantment/spell effects."""

    #--Class Data
    seFlags = Flags(0x0L,Flags.getNames('hostile'))
    class MelEffectsScit(MelStruct):
        """Subclass to support alternate format."""
        def __init__(self):
            MelStruct.__init__(self,'SCIT','II4sB3s',(FID,'script',None),('school',0),
                ('visual','REHE'),(MelEffects.seFlags,'flags',0x0L),('unused1',null3))
        def loadData(self,record,ins,type,size,readId):
            #--Alternate formats
            if size == 16:
                attrs,actions = self.attrs,self.actions
                unpacked = ins.unpack(self.format,size,readId)
            elif size == 12:
                attrs,actions = ('script','school','visual'),(0,0,0)
                unpacked = ins.unpack('II4s',size,readId)
                record.unused1 = null3
            else: #--size == 4
                #--The script fid for MS40TestSpell doesn't point to a valid script.
                #--But it's not used, so... Not a problem! It's also t
                record.unused1 = null3
                attrs,actions = ('script',),(0,)
                unpacked = ins.unpack('I',size,readId)
                if unpacked[0] & 0xFF000000L:
                    unpacked = (0L,) #--Discard bogus MS40TestSpell fid
            #--Unpack
            record.__slots__ = self.attrs
            setter = record.__setattr__
            for attr,value,action in zip(attrs,unpacked,actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print ' ',unpacked

    #--Instance methods
    def __init__(self,attr='effects'):
        """Initialize elements."""
        MelGroups.__init__(self,attr,
            MelStruct('EFID','4s',('name','REHE')),
            MelStruct('EFIT','4s4Ii',('name','REHE'),'magnitude','area','duration','recipient','actorValue'),
            MelGroup('scriptEffect',
                MelEffects.MelEffectsScit(),
                MelString('FULL','full'),
                ),
            )

#------------------------------------------------------------------------------
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
        types = MelModel.typeSets[(0,index-1)[index>0]]
        MelGroup.__init__(self,attr,
            MelString(types[0],'modPath'),
            MelBase(types[1],'modb_p'), ### Bound Radius, Float
            MelBase(types[2],'modt_p'),) ###Texture Files Hashes, Byte Array

    def debug(self,on=True):
        """Sets debug flag on self."""
        for element in self.elements[:2]: element.debug(on)
        return self

#------------------------------------------------------------------------------
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

#------------------------------------------------------------------------------
class MelOwnership(MelGroup):
    """Handles XOWN, XRNK, and XGLB for cells and cell children."""

    def __init__(self):
        """Initialize."""
        MelGroup.__init__(self, 'ownership',
            MelFid('XOWN','owner'),
            MelOptStruct('XRNK','i',('rank',None)),
            MelFid('XGLB','global'),
        )

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        if record.ownership and record.ownership.owner:
            MelGroup.dumpData(self,record,out)

#------------------------------------------------------------------------------
class MelScrxen(MelFids):
    """Handles mixed sets of SCRO and SCRV for scripts, quests, etc."""

    def getLoaders(self,loaders):
        loaders['SCRV'] = self
        loaders['SCRO'] = self

    def loadData(self,record,ins,type,size,readId):
        isFid = (type == 'SCRO')
        if isFid: value = ins.unpackRef(readId)
        else: value, = ins.unpack('I',4,readId)
        record.__getattribute__(self.attr).append((isFid,value))

    def dumpData(self,record,out):
        for isFid,value in record.__getattribute__(self.attr):
            if isFid: out.packRef('SCRO',value)
            else: out.packSub('SCRV','I',value)

    def mapFids(self,record,function,save=False):
        scrxen = record.__getattribute__(self.attr)
        for index,(isFid,value) in enumerate(scrxen):
            if isFid:
                result = function(value)
                if save: scrxen[index] = (isFid,result)

#------------------------------------------------------------------------------
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
        if _debug: print '\n>>>> %08X' % record.fid
        insAtEnd = ins.atEnd
        insSubHeader = ins.unpackSubHeader
##        fullLoad = self.full0.loadData
        while not insAtEnd(endPos,recType):
            (type,size) = insSubHeader(recType)
            if _debug: print type,size
            readId = recType + '.' + type
            try:
                if type not in loaders:
                    raise ModError(ins.inName,_('Unexpected subrecord: ')+readId)
                #--Hack to handle the fact that there can be two types of FULL in spell/ench/ingr records.
                elif doFullTest and type == 'FULL':
                    self.full0.loadData(record,ins,type,size,readId)
                else:
                    loaders[type].loadData(record,ins,type,size,readId)
                doFullTest = doFullTest and (type != 'EFID')
            except:
                eid = getattr(record,'eid','<<NO EID>>')
                print 'Loading: %08X..%s..%s.%s..%d..' % (record.fid,eid,record.recType,type,size)
                raise
        if _debug: print '<<<<',getattr(record,'eid','[NO EID]')

    def dumpData(self,record, out):
        """Dumps state into out. Called by getSize()."""
        for element in self.elements:
            try:
                element.dumpData(record,out)
            except:
                print 'Dumping:',getattr(record,'eid','<<NO EID>>'),record.fid,element
                for attr in record.__slots__:
                    if hasattr(record,attr):
                        print "> %s: %s" % (attr,getattr(record,attr))
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
        if not record.longFids: raise StateError(_("Fids not in long format"))
        def updater(fid):
            masters.add(fid)
        updater(record.fid)
        for element in self.formElements:
            element.mapFids(record,updater)

    def getReport(self):
        """Returns a report of structure."""
        buff = cStringIO.StringIO()
        for element in self.elements:
            element.report(None,buff,'')
        return buff.getvalue()
    def getDeltas(self,newRecord,oldRecord):
        deltas = []
        for element in self.elements:
            delta = element.getDelta(newRecord,oldRecord)
            if delta != None: deltas.extend(delta)
        return deltas
# Flags
#------------------------------------------------------------------------------
class MelBipedFlags(Flags):
    """Biped flags element. Includes biped flag set by default."""
    mask = 0xFFFF
    def __init__(self,default=0L,newNames=None):
        names = Flags.getNames('head', 'hair', 'upperBody', 'lowerBody', 'hand', 'foot', 'rightRing', 'leftRing', 'amulet', 'weapon', 'backWeapon', 'sideWeapon', 'quiver', 'shield', 'torch', 'tail')
        if newNames: names.update(newNames)
        Flags.__init__(self,default,names)

# Mod Records 0 ---------------------------------------------------------------
#------------------------------------------------------------------------------
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
        out = ModWriter(cStringIO.StringIO())
        self.dumpData(out)
        #--Done
        self.data = out.getvalue()
        data.close()
        self.size = len(self.data)
        self.setChanged(False)
        return self.size

    def dumpData(self,out):
        """Dumps state into out. Called by getSize()."""
        raise AbstractError

    def dump(self,out):
        if self.changed: raise StateError(_('Data changed: ')+ self.subType)
        if not self.data: raise StateError(_('Data undefined: ')+self.subType)
        out.packSub(self.subType,self.data)

#------------------------------------------------------------------------------
class MreRecord(object):
    """Generic Record."""
    subtype_attr = {'EDID':'eid','FULL':'full','MODL':'model'}
    _flags1 = Flags(0L,Flags.getNames(
        ( 0,'esm'),
        ( 5,'deleted'),
        ( 6,'borderRegion'),
        ( 7,'turnFireOff'),
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
    __slots__ = ['recType','size','fid','flags2','flags1','changed','subrecords','data','inName','longFids',]
    #--Set at end of class data definitions.
    type_class = None
    simpleTypes = None

    def __init__(self,header,ins=None,unpack=False):
        (self.recType,self.size,flags1,self.fid,self.flags2) = header
        self.flags1 = MreRecord._flags1(flags1)
        self.longFids = False #--False: Short (numeric); True: Long (espname,objectindex)
        self.changed = False
        self.subrecords = None
        self.data = ''
        self.inName = ins and ins.inName
        if ins: self.load(ins,unpack)

    def __repr__(self):
        if hasattr(self,'eid') and self.eid is not None:
            eid=' '+self.eid
        else:
            eid=''
        return '<%s object: %s (%s)%s>' % (`type(self)`.split("'")[1], self.recType, strFid(self.fid), eid)

    def getHeader(self):
        """Returns header tuple."""
        return (self.recType,self.size,int(self.flags1),self.fid,self.flags2)

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
        import zlib
        size, = struct.unpack('I',self.data[:4])
        decomp = zlib.decompress(self.data[4:])
        if len(decomp) != size:
            raise ModError(self.inName,
                _('Mis-sized compressed data. Expected %d, got %d.') % (size,len(decomp)))
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
                reader = self.getReader()
                self.loadData(reader,reader.size)
                reader.close()
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
        reader = self.getReader()
        recType = self.recType
        readAtEnd = reader.atEnd
        readSubHeader = reader.unpackSubHeader
        subAppend = self.subrecords.append
        while not readAtEnd(reader.size,recType):
            (type,size) = readSubHeader(recType)
            subAppend(MreSubrecord(type,size,reader))
        reader.close()

    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if converting to short format."""
        raise AbstractError(self.recType)

    def updateMasters(self,masters):
        """Updates set of master names according to masters actually used."""
        raise AbstractError(self.recType)

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
        if self.longFids: raise StateError(
            _('Packing Error: %s %s: Fids in long format.') % self.recType,self.fid)
        #--Pack data and return size.
        out = ModWriter(cStringIO.StringIO())
        self.dumpData(out)
        data = out.getvalue()
        self.data = out.getvalue()
        out.close()
        if self.flags1.compressed:
            import zlib
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
            raise StateError('Subrecords not unpacked. [%s: %s %08X]' %
                (self.inName, self.recType, self.fid))
        for subrecord in self.subrecords:
            subrecord.dump(out)

    def dump(self,out):
        """Dumps all data to output stream."""
        if self.changed: raise StateError(_('Data changed: ')+ self.recType)
        if not self.data and not self.flags1.deleted and self.size > 0:
            raise StateError(_('Data undefined: ')+self.recType+' '+hex(self.fid))
        out.write(struct.pack('=4s4I',self.recType,self.size,int(self.flags1),self.fid,self.flags2))
        if self.size > 0: out.write(self.data)

    def getReader(self):
        """Returns a ModReader wrapped around (decompressed) self.data."""
        return ModReader(self.inName,cStringIO.StringIO(self.getDecompressed()))

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
                    value = cstrip(subrecord.data)
                    break
        #--No subrecords, but have data.
        elif self.data:
            reader = self.getReader()
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
                    value = cstrip(readRead(size))
                    break
            reader.close()
        #--Return it
        return value

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
    def getDelta(self, oldRecord):
        if getattr(self,'flags1',None) != getattr(oldRecord,'flags1',None):
            delta = [('flags1', getattr(oldRecord,'flags1',None), getattr(self,'flags1',None))]
        else: delta = []
        delta.extend(self.melSet.getDeltas(self,oldRecord))
        return delta

#------------------------------------------------------------------------------
class MreActor(MelRecord):
    """Creatures and NPCs."""

    def mergeFilter(self,modSet):
        """Filter out items that don't come from specified modSet.
        Filters spells, factions and items."""
        if not self.longFids: raise StateError(_("Fids not in long format"))
        self.spells = [x for x in self.spells if x[0] in modSet]
        self.factions = [x for x in self.factions if x.faction[0] in modSet]
        self.items = [x for x in self.items if x.item[0] in modSet]

#------------------------------------------------------------------------------
class MreLeveledList(MelRecord):
    """Leveled item/creature/spell list.."""
    _flags = Flags(0,Flags.getNames('calcFromAllLevels','calcForEachItem','useAllSpells'))
    #--Special load classes
    class MelLevListLvld(MelStruct):
        """Subclass to support alternate format."""
        def loadData(self,record,ins,type,size,readId):
            MelStruct.loadData(self,record,ins,type,size,readId)
            if record.chanceNone > 127:
                record.flags.calcFromAllLevels = True
                record.chanceNone &= 127

    class MelLevListLvlo(MelStructs):
        """Subclass to support alternate format."""
        def loadData(self,record,ins,type,size,readId):
            target = self.getDefault()
            record.__getattribute__(self.attr).append(target)
            target.__slots__ = self.attrs
            format,attrs = ((self.format,self.attrs),('iI',('level','listId'),))[size==8]####might be h2sI
            unpacked = ins.unpack(format,size,readId)
            setter = target.__setattr__
            map(setter,attrs,unpacked)
    #--Element Set
    melSet = MelSet(
        MelString('EDID','eid'),
        MelLevListLvld('LVLD','B','chanceNone'),
        MelStruct('LVLF','B',(_flags,'flags',0L)),
        MelFid('SCRI','script'),
        MelFid('TNAM','template'),
        MelLevListLvlo('LVLO','h2sIh2s','entries','level',('unused1',null2),(FID,'listId',None),('count',1),('unused2',null2)),
        MelNull('DATA'),
        )
    __slots__ = (MelRecord.__slots__ + melSet.getSlotsUsed() +
        ['mergeOverLast','mergeSources','items','delevs','relevs'])

    def __init__(self,header,ins=None,unpack=False):
        """Initialize."""
        MelRecord.__init__(self,header,ins,unpack)
        self.mergeOverLast = False #--Merge overrides last mod merged
        self.mergeSources = None #--Set to list by other functions
        self.items  = None #--Set of items included in list
        self.delevs = None #--Set of items deleted by list (Delev and Relev mods)
        self.relevs = None #--Set of items relevelled by list (Relev mods)

    def mergeFilter(self,modSet):
        """Filter out items that don't come from specified modSet."""
        if not self.longFids: raise StateError(_("Fids not in long format"))
        self.entries = [entry for entry in self.entries if entry.listId[0] in modSet]

    def mergeWith(self,other,otherMod):
        """Merges newLevl settings and entries with self.
        Requires that: self.items, other.delevs and other.relevs be defined."""
        if not self.longFids: raise StateError(_("Fids not in long format"))
        if not other.longFids: raise StateError(_("Fids not in long format"))
        #--Relevel or not?
        if other.relevs:
            self.chanceNone = other.chanceNone
            self.script = other.script
            self.template = other.template
            self.flags = other.flags()
        else:
            self.chanceNone = other.chanceNone or self.chanceNone
            self.script   = other.script or self.script
            self.template = other.template or self.template
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
            self.entries.sort(key=attrgetter('level'))
        #--Is merged list different from other? (And thus written to patch.)
        if (self.chanceNone != other.chanceNone or
            self.script != other.script or
            self.template != other.template or
            #self.flags != other.flags or
            len(self.entries) != len(other.entries)
            ):
            self.mergeOverLast = True
        else:
            for selfEntry,otherEntry in zip(self.entries,other.entries):
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
        self.setChanged()

#------------------------------------------------------------------------------
class MreHasEffects:
    """Mixin class for magic items."""
    def getEffects(self):
        """Returns a summary of effects. Useful for alchemical catalog."""
        effects = []
        avEffects = bush.actorValueEffects
        effectsAppend = effects.append
        for effect in self.effects:
            mgef, actorValue = effect.name, effect.actorValue
            if mgef not in avEffects:
                actorValue = 0
            effectsAppend((mgef,actorValue))
        return effects

    def getEffectsSummary(self,mgef_school=None,mgef_name=None):
        """Return a text description of magic effects."""
        mgef_school = mgef_school or bush.mgef_school
        mgef_name = mgef_name or bush.mgef_name
        buff = cStringIO.StringIO()
        avEffects = bush.actorValueEffects
        aValues = bush.actorValues
        buffWrite = buff.write
        if self.effects:
            school = mgef_school[self.effects[0].name]
            buffWrite(bush.actorValues[20+school] + '\n')
        for index,effect in enumerate(self.effects):
            if effect.scriptEffect:
                effectName = effect.scriptEffect.full or 'Script Effect'
            else:
                effectName = mgef_name[effect.name]
                if effect.name in avEffects:
                    effectName = re.sub(_('(Attribute|Skill)'),aValues[effect.actorValue],effectName)
            buffWrite('o+*'[effect.recipient]+' '+effectName)
            if effect.magnitude: buffWrite(' '+`effect.magnitude`+'m')
            if effect.area: buffWrite(' '+`effect.area`+'a')
            if effect.duration > 1: buffWrite(' '+`effect.duration`+'d')
            buffWrite('\n')
        return buff.getvalue()

# Mod Records 1 ---------------------------------------------------------------
#------------------------------------------------------------------------------
class MreAchr(MelRecord): # Placed NPC
    classType = 'ACHR'
    _flags = Flags(0L,Flags.getNames('oppositeParent'))
    melSet=MelSet(
        MelString('EDID','eid'),
        MelFid('NAME','base'),
        MelXpci('XPCI'),
        MelBase('XLOD','xlod_p'), ### Float?
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),('unused1',null3)),
        MelFid('XMRC','merchantContainer'),
        MelFid('XHRS','horse'),
        MelBase('XRGD','xrgd_p'), ###Ragdoll Data, ByteArray
        MelOptStruct('XSCL','f',('scale',1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAcre(MelRecord): # Placed Creature
    classType = 'ACRE'
    _flags = Flags(0L,Flags.getNames('oppositeParent'))
    melSet=MelSet(
        MelString('EDID','eid'),
        MelFid('NAME','base'),
        MelOwnership(),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),('unused1',null3)),
        MelBase('XRGD','xrgd_p'), ###Ragdoll Data, ByteArray
        MelOptStruct('XSCL','f',('scale',1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreActi(MelRecord):
    """Activator record."""
    classType = 'ACTI'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelFid('SCRI','script'),
        MelFid('SNAM','sound'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAlch(MelRecord,MreHasEffects):
    """ALCH (potion) record."""
    classType = 'ALCH'
    _flags = Flags(0L,Flags.getNames('autoCalc','isFood'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFull0(),
        MelModel(),
        MelString('ICON','iconPath'),
        MelFid('SCRI','script'),
        MelStruct('DATA','f','weight'),
        MelStruct('ENIT','iB3s','value',(_flags,'flags',0L),('unused1',null3)),
        MelEffects(),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAmmo(MelRecord):
    """Ammo (arrow) record."""
    classType = 'AMMO'
    _flags = Flags(0L,Flags.getNames('notNormalWeapon'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelFid('ENAM','enchantment'),
        MelOptStruct('ANAM','H','enchantPoints'),
        MelStruct('DATA','fB3sIfH','speed',(_flags,'flags',0L),('unused1',null3),'value','weight','damage'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAnio(MelRecord):
    """Animation object record."""
    classType = 'ANIO'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelFid('DATA','animationId'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAppa(MelRecord):
    """Alchemical apparatus record."""
    classType = 'APPA'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelFid('SCRI','script'),
        MelStruct('DATA','=BIff',('apparatus',0),('value',25),('weight',1),('quality',10)),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArmo(MelRecord):
    """Armor record."""
    classType = 'ARMO'
    _flags = MelBipedFlags(0L,Flags.getNames((16,'hideRings'),(17,'hideAmulet'),(22,'notPlayable'),(23,'heavyArmor')))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelFid('SCRI','script'),
        MelFid('ENAM','enchantment'),
        MelOptStruct('ANAM','H','enchantPoints'),
        MelStruct('BMDT','I',(_flags,'flags',0L)),
        MelModel('maleBody',0),
        MelModel('maleWorld',2),
        MelString('ICON','maleIconPath'),
        MelModel('femaleBody',3),
        MelModel('femaleWorld',4),
        MelString('ICO2','femaleIconPath'),
        MelStruct('DATA','=HIIf','strength','value','health','weight'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreBook(MelRecord):
    """BOOK record."""
    classType = 'BOOK'
    _flags = Flags(0,Flags.getNames('isScroll','isFixed'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('DESC','text'),
        MelFid('SCRI','script'),
        MelFid('ENAM','enchantment'),
        MelOptStruct('ANAM','H','enchantPoints'),
        MelStruct('DATA', '=BbIf',(_flags,'flags',0L),('teaches',-1),'value','weight'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed() + ['modb']

#------------------------------------------------------------------------------
class MreBsgn(MelRecord):
    """Alchemical apparatus record."""
    classType = 'BSGN'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelString('ICON','iconPath'),
        MelString('DESC','text'),
        MelFids('SPLO','spells'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCell(MelRecord):
    """Cell record."""
    classType = 'CELL'
    cellFlags = Flags(0L,Flags.getNames((0, 'isInterior'),(1,'hasWater'),(2,'invertFastTravel'),
        (3,'forceHideLand'),(5,'publicPlace'),(6,'handChanged'),(7,'behaveLikeExterior')))
    class MelCoordinates(MelOptStruct):
        def dumpData(self,record,out):
            if not record.flags.isInterior:
                MelOptStruct.dumpData(self,record,out)

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelStruct('DATA','B',(cellFlags,'flags',0L)),
        MelOptStruct('XCLL','=3Bs3Bs3Bs2f2i2f','ambientRed','ambientGreen','ambientBlue',
            ('unused1',null1),'directionalRed','directionalGreen','directionalBlue',
            ('unused2',null1),'fogRed','fogGreen','fogBlue',
            ('unused3',null1),'fogNear','fogFar','directionalXY','directionalZ',
            'directionalFade','fogClip'),
        MelOptStruct('XCMT','B','music'),
        MelOwnership(),
        MelFid('XCCM','climate'),
        #--CS default for water is -2147483648, but by setting default here to -2147483649,
        #  we force the bashed patch to retain the value of the last mod.
        MelOptStruct('XCLW','f',('waterHeight',-2147483649)),
        MelFidList('XCLR','regions'),
        MelCoordinates('XCLC','ii',('posX',None),('posY',None)),
        MelFid('XCWT','water'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClas(MelRecord):
    """Class record."""
    classType = 'CLAS'
    _flags = Flags(0L,Flags.getNames(
        ( 0,'Playable'),
        ( 1,'Guard'),
        ))
    aiService = Flags(0L,Flags.getNames(
        (0,'weapons'),
        (1,'armor'),
        (2,'clothing'),
        (3,'books'),
        (4,'ingredients'),
        (7,'lights'),
        (8,'apparatus'),
        (10,'miscItems'),
        (11,'spells'),
        (12,'magicItems'),
        (13,'potions'),
        (14,'training'),
        (16,'recharge'),
        (17,'repair'),))
    class MelClasData(MelStruct):
        """Handle older trucated DATA for CLAS subrecords."""
        def loadData(self,record,ins,type,size,readId):
            if size == 52:
                MelStruct.loadData(self,record,ins,type,size,readId)
                return
            #--Else 42 byte record (skips trainSkill, trainLevel,unused1...
            unpacked = ins.unpack('2iI7i2I',size,readId)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelString('DESC','description'),
        MelString('ICON','iconPath'),
        MelClasData('DATA','2iI7i2IbB2s','primary1','primary2','specialization','major1','major2','major3','major4','major5','major6','major7',(_flags,'flags',0L),(aiService,'services',0L),('trainSkill',0),('trainLevel',0),('unused1',null2)),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClmt(MelRecord):
    """Climate record."""
    classType = 'CLMT'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStructA('WLST','Ii', 'Weather', (FID,'weather'), 'chance'),
        MelString('FNAM','sunPath'),
        MelString('GNAM','glarePath'),
        MelModel(),
        MelStruct('TNAM','6B','riseBegin','riseEnd','setBegin','setEnd','volatility','phaseLength'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()
#------------------------------------------------------------------------------
class MreClot(MelRecord):
    """Clothing record."""
    classType = 'CLOT'
    _flags = MelBipedFlags(0L,Flags.getNames((16,'hideRings'),(17,'hideAmulet'),(22,'notPlayable')))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelFid('SCRI','script'),
        MelFid('ENAM','enchantment'),
        MelOptStruct('ANAM','H','enchantPoints'),
        MelStruct('BMDT','I',(_flags,'flags',0L)),
        MelModel('maleBody',0),
        MelModel('maleWorld',2),
        MelString('ICON','maleIconPath'),
        MelModel('femaleBody',3),
        MelModel('femaleWorld',4),
        MelString('ICO2','femaleIconPath'),
        MelStruct('DATA','If','value','weight'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCont(MelRecord):
    """Container record."""
    classType = 'CONT'
    _flags = Flags(0,Flags.getNames(None,'respawns'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelFid('SCRI','script'),
        MelStructs('CNTO','Ii','items',(FID,'item'),'count'),
        MelStruct('DATA','=Bf',(_flags,'flags',0L),'weight'),
        MelFid('SNAM','soundOpen'),
        MelFid('QNAM','soundClose'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCrea(MreActor):
    """NPC Record. Non-Player Character."""
    classType = 'CREA'
    #--Main flags
    _flags = Flags(0L,Flags.getNames(
        ( 0,'biped'),
        ( 1,'essential'),
        ( 2,'weaponAndShield'),
        ( 3,'respawn'),
        ( 4,'swims'),
        ( 5,'flies'),
        ( 6,'walks'),
        ( 7,'pcLevelOffset'),
        ( 9,'noLowLevel'),
        (11,'noBloodSpray'),
        (12,'noBloodDecal'),
        (15,'noHead'),
        (16,'noRightArm'),
        (17,'noLeftArm'),
        (18,'noCombatInWater'),
        (19,'noShadow'),
        (20,'noCorpseCheck'),
        ))
#    #--AI Service flags
    aiService = Flags(0L,Flags.getNames(
        (0,'weapons'),
        (1,'armor'),
        (2,'clothing'),
        (3,'books'),
        (4,'ingredients'),
        (7,'lights'),
        (8,'apparatus'),
        (10,'miscItems'),
        (11,'spells'),
        (12,'magicItems'),
        (13,'potions'),
        (14,'training'),
        (16,'recharge'),
        (17,'repair'),))
    #--Mel Set
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelFids('SPLO','spells'),
        MelStrings('NIFZ','bodyParts'),
        MelBase('NIFT','nift_p'), ###Texture File hashes, Byte Array
        MelStruct('ACBS','=I3Hh2H',
            (_flags,'flags',0L),'baseSpell','fatigue','barterGold',
            ('level',1),'calcMin','calcMax'),
        MelStructs('SNAM','=IB3s','factions',
            (FID,'faction',None),'rank',('unused1','IFZ')),
        MelFid('INAM','deathItem'),
        MelFid('SCRI','script'),
        MelStructs('CNTO','Ii','items',(FID,'item',None),('count',1)),
        MelStruct('AIDT','=4BIbB2s',
            ('aggression',5),('confidence',50),('energyLevel',50),('responsibility',50),
            (aiService,'services',0L),'trainSkill','trainLevel',('unused1',null2)),
        MelFids('PKID','aiPackages'),
        MelStrings('KFFZ','animations'),
        MelStruct('DATA','=5BsH2sH8B','creatureType','combat','magic','stealth',
                  'soul',('unused2',null1),'health',('unused3',null2),'attackDamage','strength',
                  'intelligence','willpower','agility','speed','endurance',
                  'personality','luck'),
        MelStruct('RNAM','B','attackReach'),
        MelFid('ZNAM','combatStyle'),
        MelStruct('TNAM','f','turningSpeed'),
        MelStruct('BNAM','f','baseScale'),
        MelStruct('WNAM','f','footWeight'),
        MelFid('CSCR','inheritsSoundsFrom'),
        MelString('NAM0','bloodSprayPath'),
        MelString('NAM1','bloodDecalPath'),
        MelGroups('sounds',
            MelStruct('CSDT','I','type'),
            MelFid('CSDI','sound'),
            MelStruct('CSDC','B','chance'),
        ),
        )
    __slots__ = MreActor.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCsty(MelRecord):
    """CSTY Record. Combat Styles."""
    classType = 'CSTY'
    _flagsA = Flags(0L,Flags.getNames(
        ( 0,'advanced'),
        ( 1,'useChanceForAttack'),
        ( 2,'ignoreAllies'),
        ( 3,'willYield'),
        ( 4,'rejectsYields'),
        ( 5,'fleeingDisabled'),
        ( 6,'prefersRanged'),
        ( 7,'meleeAlertOK'),
        ))
    _flagsB = Flags(0L,Flags.getNames(
        ( 0,'doNotAcquire'),
        ))

    class MelCstdData(MelStruct):
        """Handle older trucated DATA for CSTD subrecord."""
        def loadData(self,record,ins,type,size,readId):
            if size == 124:
                MelStruct.loadData(self,record,ins,type,size,readId)
                return
            elif size == 120:
                #--Else 120 byte record (skips flagsB
                unpacked = ins.unpack('2B2s8f2B2s3fB3s2f5B3s2f2B2s7fB3sf',size,readId)
            elif size == 112:
                #--112 byte record (skips flagsB, rushChance, unused6, rushMult
                unpacked = ins.unpack('2B2s8f2B2s3fB3s2f5B3s2f2B2s7f',size,readId)
            elif size == 104:
                #--104 byte record (skips flagsB, rushChance, unused6, rushMult, rStand, groupStand
                #-- only one occurence (AndragilTraining
                unpacked = ins.unpack('2B2s8f2B2s3fB3s2f5B3s2f2B2s5f',size,readId)
            elif size == 92:
                #--92 byte record (skips flagsB, rushChance, unused6, rushMult, rStand, groupStand
                #--                mDistance, rDistance, buffStand
                #-- These records keep getting shorter and shorter...
                #-- This one is used by quite a few npcs
                unpacked = ins.unpack('2B2s8f2B2s3fB3s2f5B3s2f2B2s2f',size,readId)
            elif size == 84:
                #--84 byte record (skips flagsB, rushChance, unused6, rushMult, rStand, groupStand
                #--                mDistance, rDistance, buffStand, rMultOpt, rMultMax
                #-- This one is present once: VidCaptureNoAttacks and it isn't actually used.
                unpacked = ins.unpack('2B2s8f2B2s3fB3s2f5B3s2f2B2s',size,readId)
            else:
                raise "Unexpected size encountered for CSTD subrecord: %s" % size
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flagsA.getTrueAttrs()
    #--Mel Set
    melSet = MelSet(
        MelString('EDID','eid'),
        MelCstdData('CSTD', '2B2s8f2B2s3fB3s2f5B3s2f2B2s7fB3sfI', 'dodgeChance', 'lrChance',
                    ('unused1',null2), 'lrTimerMin', 'lrTimerMax', 'forTimerMin', 'forTimerMax',
                    'backTimerMin', 'backTimerMax', 'idleTimerMin', 'idleTimerMax',
                    'blkChance', 'atkChance', ('unused2',null2), 'atkBRecoil','atkBunc',
                    'atkBh2h', 'pAtkChance', ('unused3',null3), 'pAtkBRecoil', 'pAtkBUnc',
                    'pAtkNormal', 'pAtkFor', 'pAtkBack', 'pAtkL', 'pAtkR', ('unused4',null3),
                    'holdTimerMin', 'holdTimerMax', (_flagsA,'flagsA'), 'acroDodge',
                    ('unused5',null2), ('rMultOpt',1.0), ('rMultMax',1.0), ('mDistance',250.0), ('rDistance',1000.0),
                    ('buffStand',325.0), ('rStand',500.0), ('groupStand',325.0), ('rushChance',25),
                    ('unused6',null3), ('rushMult',1.0), (_flagsB,'flagsB')),
        MelOptStruct('CSAD', '21f', 'dodgeFMult', 'dodgeFBase', 'encSBase', 'encSMult',
                     'dodgeAtkMult', 'dodgeNAtkMult', 'dodgeBAtkMult', 'dodgeBNAtkMult',
                     'dodgeFAtkMult', 'dodgeFNAtkMult', 'blockMult', 'blockBase',
                     'blockAtkMult', 'blockNAtkMult', 'atkMult','atkBase', 'atkAtkMult',
                     'atkNAtkMult', 'atkBlockMult', 'pAtkFBase', 'pAtkFMult'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()
#------------------------------------------------------------------------------
class MreDial(MelRecord):
    """Dialog record."""
    classType = 'DIAL'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFids('QSTI','quests'), ### QSTRs?
        MelString('FULL','full'),
        MelStruct('DATA','B','dialType'),
    )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed() + ['infoStamp','infos']

    def __init__(self,header,ins=None,unpack=False):
        """Initialize."""
        MelRecord.__init__(self,header,ins,unpack)
        self.infoStamp = 0 #--Stamp for info GRUP
        self.infos = []

    def loadInfos(self,ins,endPos,infoClass):
        """Load infos from ins. Called from MobDials."""
        infos = self.infos
        recHead = ins.unpackRecHeader
        infosAppend = infos.append
        while not ins.atEnd(endPos,'INFO Block'):
            #--Get record info and handle it
            header = recHead()
            recType = header[0]
            if recType == 'INFO':
                info = infoClass(header,ins,True)
                infosAppend(info)
            else:
                raise ModError(ins.inName, _('Unexpected %s record in %s group.')
                    % (recType,"INFO"))

    def dump(self,out):
        """Dumps self., then group header and then records."""
        MreRecord.dump(self,out)
        if not self.infos: return
        size = 20 + sum([20 + info.getSize() for info in self.infos])
        out.pack('4sIIII','GRUP',size,self.fid,7,self.infoStamp)
        for info in self.infos: info.dump(out)

    def updateMasters(self,masters):
        """Updates set of master names according to masters actually used."""
        MelRecord.updateMasters(self,masters)
        for info in self.infos:
            info.updateMasters(masters)

    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if converting to short format."""
        MelRecord.convertFids(self,mapper,toLong)
        for info in self.infos:
            info.convertFids(mapper,toLong)

#------------------------------------------------------------------------------
class MreDoor(MelRecord):
    """Container record."""
    classType = 'DOOR'
    _flags = Flags(0,Flags.getNames('oblivionGate','automatic','hidden','minimalUse'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelFid('SCRI','script'),
        MelFid('SNAM','soundOpen'),
        MelFid('ANAM','soundClose'),
        MelFid('BNAM','soundLoop'),
        MelStruct('FNAM','B',(_flags,'flags',0L)),
        MelFids('TNAM','destinations'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEfsh(MelRecord):
    """Effect shader record."""
    classType = 'EFSH'
    _flags = Flags(0L,Flags.getNames(
        ( 0,'noMemShader'),
        ( 3,'noPartShader'),
        ( 4,'edgeInverse'),
        ( 5,'memSkinOnly'),
        ))

    class MelEfshData(MelStruct):
        """Handle older trucated DATA for EFSH subrecord."""
        def loadData(self,record,ins,type,size,readId):
            if size == 224:
                MelStruct.loadData(self,record,ins,type,size,readId)
                return
            elif size == 96:
                #--Else 96 byte record (skips particle variables, and color keys
                # Only used twice in test shaders (0004b6d5, 0004b6d6)
                unpacked = ins.unpack('B3s3I3Bs9f3Bs8fI',size,readId)
            else:
                raise "Unexpected size encountered for EFSH subrecord: %s" % size
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('ICON','fillTexture'),
        MelString('ICO2','particleTexture'),
        MelEfshData('DATA','B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs6f',(_flags,'flags'),('unused1',null3),'memSBlend',
                    'memBlendOp','memZFunc','fillRed','fillGreen','fillBlue',('unused2',null1),
                    'fillAIn','fillAFull','fillAOut','fillAPRatio','fillAAmp',
                    'fillAFreq','fillAnimSpdU','fillAnimSpdV','edgeOff','edgeRed',
                    'edgeGreen','edgeBlue',('unused3',null1),'edgeAIn','edgeAFull',
                    'edgeAOut','edgeAPRatio','edgeAAmp','edgeAFreq','fillAFRatio',
                    'edgeAFRatio','memDBlend',('partSBlend',5),('partBlendOp',1),
                    ('partZFunc',4),('partDBlend',6),('partBUp',0.0),('partBFull',0.0),('partBDown',0.0),
                    ('partBFRatio',1.0),('partBPRatio',1.0),('partLTime',1.0),('partLDelta',0.0),('partNSpd',0.0),
                    ('partNAcc',0.0),('partVel1',0.0),('partVel2',0.0),('partVel3',0.0),('partAcc1',0.0),
                    ('partAcc2',0.0),('partAcc3',0.0),('partKey1',1.0),('partKey2',1.0),('partKey1Time',0.0),
                    ('partKey2Time',1.0),('key1Red',255),('key1Green',255),('key1Blue',255),('unused4',null1),
                    ('key2Red',255),('key2Green',255),('key2Blue',255),('unused5',null1),('key3Red',255),('key3Green',255),
                    ('key3Blue',255),('unused6',null1),('key1A',1.0),('key2A',1.0),('key3A',1.0),('key1Time',0.0),
                    ('key2Time',0.5),('key3Time',1.0)),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEnch(MelRecord,MreHasEffects):
    """Enchantment record."""
    classType = 'ENCH'
    _flags = Flags(0L,Flags.getNames('noAutoCalc'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFull0(), #--At least one mod has this. Odd.
        MelStruct('ENIT','3IB3s','itemType','chargeAmount','enchantCost',(_flags,'flags',0L),('unused1',null3)),
        #--itemType = 0: Scroll, 1: Staff, 2: Weapon, 3: Apparel
        MelEffects(),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEyes(MelRecord):
    """Eyes record."""
    classType = 'EYES'
    _flags = Flags(0L,Flags.getNames('playable',))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelString('ICON','iconPath'),
        MelStruct('DATA','B',(_flags,'flags')),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFact(MelRecord):
    """Faction record."""
    classType = 'FACT'
    _flags = Flags(0L,Flags.getNames('hiddenFromPC','evil','specialCombat'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelStructs('XNAM','Ii','relations',(FID,'faction'),'mod'),
        MelStruct('DATA','B',(_flags,'flags',0L)),
        MelOptStruct('CNAM','f',('crimeGoldMultiplier',None)),
        MelGroups('ranks',
            MelStruct('RNAM','i','rank'),
            MelString('MNAM','male'),
            MelString('FNAM','female'),
            MelString('INAM','insigniaPath'),),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFlor(MelRecord):
    """Flora (plant) record."""
    classType = 'FLOR'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelFid('SCRI','script'),
        MelFid('PFIG','ingredient'),
        MelStruct('PFPC','4B','spring','summer','fall','winter'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFurn(MelRecord):
    """Furniture record."""
    classType = 'FURN'
    _flags = Flags() #--Governs type of furniture and which anims are available
    #--E.g., whether it's a bed, and which of the bed entry/exit animations are available
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelFid('SCRI','script'),
        MelStruct('MNAM','I',(_flags,'activeMarkers',0L)), ####ByteArray
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreGlob(MelRecord):
    """Global record. Rather stupidly all values, despite their
    designation (short,long,float) are stored as floats -- which means that
    very large integers lose precision."""
    classType = 'GLOB'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('FNAM','s',('format','s')), #-'s','l','f' for short/long/float
        MelStruct('FLTV','f','value'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreGmst(MelRecord):
    """Gmst record"""
    oblivionIds = None
    classType = 'GMST'
    class MelGmstValue(MelBase):
        def loadData(self,record,ins,type,size,readId):
            format = record.eid[0] #-- s|i|f
            if format == 's':
                record.value = ins.readString(size,readId)
            else:
                record.value, = ins.unpack(format,size,readId)
        def dumpData(self,record,out):
            format = record.eid[0] #-- s|i|f
            if format == 's':
                out.packSub0(self.subType,record.value)
            else:
                out.packSub(self.subType,format,record.value)
    melSet = MelSet(
        MelString('EDID','eid'),
        MelGmstValue('DATA','value'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

    def getOblivionFid(self):
        """Returns Oblivion.esm fid in long format for specified eid."""
        myClass = self.__class__
        if not myClass.oblivionIds:
            myClass.oblivionIds = cPickle.load(GPath(r'Data\Oblivion_ids.pkl').open())['GMST']
        return (GPath('Oblivion.esm'), myClass.oblivionIds[self.eid])

#------------------------------------------------------------------------------
class MreGras(MelRecord):
    """Grass record."""
    classType = 'GRAS'
    _flags = Flags(0,Flags.getNames('vLighting','uScaling','fitSlope'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelStruct('DATA','3BsH2sI4fB3s','density','minSlope',
                  'maxSlope',('unused1',null1),'waterDistance',('unused2',null2),
                  'waterOp','posRange','heightRange','colorRange',
                  'wavePeriod',(_flags,'flags'),('unused3',null3)),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreHair(MelRecord):
    """Hair record."""
    classType = 'HAIR'
    _flags = Flags(0L,Flags.getNames('playable','notMale','notFemale','fixed'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelStruct('DATA','B',(_flags,'flags')),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()
#------------------------------------------------------------------------------
class MreIdle(MelRecord):
    """Idle record."""
    classType = 'IDLE'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelConditions(),
        MelStruct('ANAM','B','group'),
        MelStruct('DATA','II',(FID,'parent'),(FID,'prevId')),####Array?
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()
#------------------------------------------------------------------------------
class MreInfo(MelRecord):
    """Info (dialog entry) record."""
    classType = 'INFO'
    _flags = Flags(0,Flags.getNames(
        'goodbye','random','sayOnce',None,'infoRefusal','randomEnd','runForRumors'))
    class MelInfoData(MelStruct):
        """Support older 2 byte version."""
        def loadData(self,record,ins,type,size,readId):
            if size != 2:
                MelStruct.loadData(self,record,ins,type,size,readId)
                return
            unpacked = ins.unpack('2B',size,readId)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print (record.dialType,record.flags.getTrueAttrs(),record.unused1)

    class MelInfoSchr(MelStruct):
        """Print only if schd record is null."""
        def dumpData(self,record,out):
            if not record.schd_p:
                MelStruct.dumpData(self,record,out)
    #--MelSet
    melSet = MelSet(
        MelInfoData('DATA','2Bs','dialType',(_flags,'flags'),('unused1','\x02')),
        MelFid('QSTI','quests'),
        MelFid('TPIC','topic'),
        MelFid('PNAM','prevInfo'),
        MelFids('NAME','addTopics'),
        MelGroups('responses',
            MelStruct('TRDT','Ii4sB3s','emotionType','emotionValue',('unused1',null4),'responseNum',('unused2',null3)),
            MelString('NAM1','responseText'),
            MelString('NAM2','actorNotes'),
            ),
        MelConditions(),
        MelFids('TCLT','choices'),
        MelFids('TCLF','linksFrom'),
        MelBase('SCHD','schd_p'), #--Old format script header?
        MelInfoSchr('SCHR','4s4I',('unused2',null4),'numRefs','compiledSize','lastIndex','scriptType'),
        MelBase('SCDA','compiled_p'),
        MelString('SCTX','scriptText'),
        MelScrxen('SCRV/SCRO','references')
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIngr(MelRecord,MreHasEffects):
    """INGR (ingredient) record."""
    classType = 'INGR'
    _flags = Flags(0L,Flags.getNames('noAutoCalc','isFood'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFull0(),
        MelModel(),
        MelString('ICON','iconPath'),
        MelFid('SCRI','script'),
        MelStruct('DATA','f','weight'),
        MelStruct('ENIT','iB3s','value',(_flags,'flags',0L),('unused1',null3)),
        MelEffects(),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreKeym(MelRecord):
    """MISC (miscellaneous item) record."""
    classType = 'KEYM'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelFid('SCRI','script'),
        MelStruct('DATA','if','value','weight'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLigh(MelRecord):
    """Light source record."""
    classType = 'LIGH'
    _flags = Flags(0L,Flags.getNames('dynamic','canTake','negative','flickers',
        'unk1','offByDefault','flickerSlow','pulse','pulseSlow','spotLight','spotShadow'))
    #--Mel NPC DATA
    class MelLighData(MelStruct):
        """Handle older trucated DATA for LIGH subrecord."""
        def loadData(self,record,ins,type,size,readId):
            if size == 32:
                MelStruct.loadData(self,record,ins,type,size,readId)
                return
            elif size == 24:
                #--Else 24 byte record (skips value and weight...
                unpacked = ins.unpack('iI3BsIff',size,readId)
            else:
                raise "Unexpected size encountered for LIGH:DATA subrecord: %s" % size
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()
    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelFid('SCRI','script'),
        MelString('FULL','full'),
        MelString('ICON','iconPath'),
        MelLighData('DATA','iI3BsIffIf','duration','radius','red','green','blue',('unused1',null1),
            (_flags,'flags',0L),'falloff','fov','value','weight'),
        MelOptStruct('FNAM','f',('fade',None)),
        MelFid('SNAM','sound'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLscr(MelRecord):
    """Load screen."""
    classType = 'LSCR'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('ICON','iconPath'),
        MelString('DESC','text'),
        MelStructs('LNAM','2I2h','Locations',(FID,'direct'),(FID,'indirect'),'gridy','gridx'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLtex(MelRecord):
    """Landscape Texture."""
    _flags = Flags(0L,Flags.getNames(
        ( 0,'stone'),
        ( 1,'cloth'),
        ( 2,'dirt'),
        ( 3,'glass'),
        ( 4,'grass'),
        ( 5,'metal'),
        ( 6,'organic'),
        ( 7,'skin'),
        ( 8,'water'),
        ( 9,'wood'),
        (10,'heavyStone'),
        (11,'heavyMetal'),
        (12,'heavyWood'),
        (13,'chain'),
        (14,'snow'),))
    classType = 'LTEX'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('ICON','iconPath'),
        MelOptStruct('HNAM','3B',(_flags,'flags'),'friction','restitution'), ####flags are actually an enum....
        MelOptStruct('SNAM','B','specular'),
        MelFids('GNAM', 'grass'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLvlc(MreLeveledList):
    """LVLC record. Leveled list for creatures."""
    classType = 'LVLC'
    __slots__ = MreLeveledList.__slots__

#------------------------------------------------------------------------------
class MreLvli(MreLeveledList):
    """LVLI record. Leveled list for items."""
    classType = 'LVLI'
    __slots__ = MreLeveledList.__slots__

#------------------------------------------------------------------------------
class MreLvsp(MreLeveledList):
    """LVSP record. Leveled list for items."""
    classType = 'LVSP'
    __slots__ = MreLeveledList.__slots__

#------------------------------------------------------------------------------
class MreMgef(MelRecord):
    """MGEF (magic effect) record."""
    classType = 'MGEF'
    #--Main flags
    _flags = Flags(0L,Flags.getNames(
        ( 0,'hostile'),
        ( 1,'recover'),
        ( 2,'detrimental'),
        ( 3,'magnitude'),
        ( 4,'self'),
        ( 5,'touch'),
        ( 6,'target'),
        ( 7,'noDuration'),
        ( 8,'noMagnitude'),
        ( 9,'noArea'),
        (10,'fxPersist'),
        (11,'spellmaking'),
        (12,'enchanting'),
        (13,'noIngredient'),
        (16,'useWeapon'),
        (17,'useArmor'),
        (18,'useCreature'),
        (19,'useSkill'),
        (20,'useAttr'),
        (24,'useAV'),
        (25,'sprayType'),
        (26,'boltType'),
        (27,'noHitEffect'),))

    #--Mel NPC DATA
    class MelMgefData(MelStruct):
        """Handle older trucated DATA for DARK subrecord."""
        def loadData(self,record,ins,type,size,readId):
            if size == 64:
                MelStruct.loadData(self,record,ins,type,size,readId)
                return
            elif size == 36:
                #--Else is data for DARK record, read it all.
                unpacked = ins.unpack('IfIiiH2sIfI',size,readId)
            else:
                raise "Unexpected size encountered for MGEF:DATA subrecord: %s" % size
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelString('DESC','text'),
        MelString('ICON','iconPath'),
        MelModel(),
        MelMgefData('DATA','IfIiiH2sIf6I2f',
            (_flags,'flags'),'baseCost',(FID,'associated'),'school','resistValue','unk1',
            ('unused1',null2),(FID,'light'),'projectileSpeed',(FID,'effectShader'),(FID,'enchantEffect',0),
            (FID,'castingSound',0),(FID,'boltSound',0),(FID,'hitSound',0),(FID,'areaSound',0),
            ('cefEnchantment',0.0),('cefBarter',0.0)),
        MelStructA('ESCE','4s','counterEffects','effect'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMisc(MelRecord):
    """MISC (miscellaneous item) record."""
    classType = 'MISC'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelFid('SCRI','script'),
        MelStruct('DATA','if','value','weight'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreNpc(MreActor):
    """NPC Record. Non-Player Character."""
    classType = 'NPC_'
    #--Main flags
    _flags = Flags(0L,Flags.getNames(
        ( 0,'female'),
        ( 1,'essential'),
        ( 3,'respawn'),
        ( 4,'autoCalc'),
        ( 7,'pcLevelOffset'),
        ( 9,'noLowLevel'),
        (13,'noRumors'),
        (14,'summonable'),
        (15,'noPersuasion'),
        (20,'canCorpseCheck'),))
    #--AI Service flags
    aiService = Flags(0L,Flags.getNames(
        (0,'weapons'),
        (1,'armor'),
        (2,'clothing'),
        (3,'books'),
        (4,'ingredients'),
        (7,'lights'),
        (8,'apparatus'),
        (10,'miscItems'),
        (11,'spells'),
        (12,'magicItems'),
        (13,'potions'),
        (14,'training'),
        (16,'recharge'),
        (17,'repair'),))
    #--Mel NPC DATA
    class MelNpcData(MelStruct):
        """Convert npc stats into skills, health, attributes."""
        def loadData(self,record,ins,type,size,readId):
            unpacked = list(ins.unpack('=21BH2s8B',size,readId))
            recordSetAttr = record.__setattr__
            recordSetAttr('skills',unpacked[:21])
            recordSetAttr('health',unpacked[21])
            recordSetAttr('unused1',unpacked[22])
            recordSetAttr('attributes',unpacked[23:])
            if self._debug: print unpacked[:21],unpacked[21],unpacked[23:]
        def dumpData(self,record,out):
            """Dumps data from record to outstream."""
            recordGetAttr = record.__getattribute__
            values = recordGetAttr('skills')+[recordGetAttr('health')]+[recordGetAttr('unused1')]+recordGetAttr('attributes')
            out.packSub(self.subType,'=21BH2s8B',*values)
    #--Mel Set
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelStruct('ACBS','=I3Hh2H',
            (_flags,'flags',0L),'baseSpell','fatigue','barterGold',
            ('level',1),'calcMin','calcMax'),
        MelStructs('SNAM','=IB3s','factions',
            (FID,'faction',None),'rank',('unused1','ODB')),
        MelFid('INAM','deathItem'),
        MelFid('RNAM','race'),
        MelFids('SPLO','spells'),
        MelFid('SCRI','script'),
        MelStructs('CNTO','Ii','items',(FID,'item',None),('count',1)),
        MelStruct('AIDT','=4BIbB2s',
            ('aggression',5),('confidence',50),('energyLevel',50),('responsibility',50),
            (aiService,'services',0L),'trainSkill','trainLevel',('unused1',null2)),
        MelFids('PKID','aiPackages'),
        MelStrings('KFFZ','animations'),
        MelFid('CNAM','iclass'),
        MelNpcData('DATA','',('skills',[0]*21),'health',('unused2',null2),('attributes',[0]*8)),
        MelFid('HNAM','hair'),
        MelOptStruct('LNAM','f',('hairLength',None)),
        MelFid('ENAM','eye'), ####fid Array
        MelStruct('HCLR','3Bs','hairRed','hairBlue','hairGreen',('unused3',null1)),
        MelFid('ZNAM','combatStyle'),
        MelBase('FGGS','fggs_p'), ####FaceGen Geometry-Symmetric
        MelBase('FGGA','fgga_p'), ####FaceGen Geometry-Asymmetric
        MelBase('FGTS','fgts_p'), ####FaceGen Texture-Symmetric
        MelStruct('FNAM','H','fnam'), ####Byte Array
        )
    __slots__ = MreActor.__slots__ + melSet.getSlotsUsed()

    def setRace(self,race):
        """Set additional race info."""
        self.race = race
        #--Model
        if not self.model:
            self.model = self.getDefault('model')
        if race in (0x23fe9,0x223c7):
            self.model.modPath = r"Characters\_Male\SkeletonBeast.NIF"
        else:
            self.model.modPath = r"Characters\_Male\skeleton.nif"
        #--FNAM
        fnams = {
            0x23fe9 : 0x3cdc ,#--Argonian
            0x224fc : 0x1d48 ,#--Breton
            0x191c1 : 0x5472 ,#--Dark Elf
            0x19204 : 0x21e6 ,#--High Elf
            0x00907 : 0x358e ,#--Imperial
            0x22c37 : 0x5b54 ,#--Khajiit
            0x224fd : 0x03b6 ,#--Nord
            0x191c0 : 0x0974 ,#--Orc
            0x00d43 : 0x61a9 ,#--Redguard
            0x00019 : 0x4477 ,#--Vampire
            0x223c8 : 0x4a2e ,#--Wood Elf
            }
        self.fnam = fnams.get(race,0x358e)

#------------------------------------------------------------------------------
class MrePack(MelRecord):
    """AI package record."""
    classType = 'PACK'
    _flags = Flags(0,Flags.getNames(
        'offersServices','mustReachLocation','mustComplete','lockAtStart',
        'lockAtEnd','lockAtLocation','unlockAtStart','unlockAtEnd',
        'unlockAtLocation','continueIfPcNear','oncePerDay',None,
        'skipFallout','alwaysRun',None,None,
        None,'alwaysSneak','allowSwimming','allowFalls',
        'unequipArmor','unequipWeapons','defensiveCombat','useHorse',
        'noIdleAnims',))
    class MelPackPkdt(MelStruct):
        """Support older 4 byte version."""
        def loadData(self,record,ins,type,size,readId):
            if size != 4:
                MelStruct.loadData(self,record,ins,type,size,readId)
            else:
                record.flags,record.aiType,junk = ins.unpack('HBs',4,readId)
                record.flags = MrePack._flags(record.flags)
                record.unused1 = null3
                if self._debug: print (record.flags.getTrueAttrs(),record.aiType,record.unused1)
    class MelPackLT(MelStruct):
        """For PLDT and PTDT. Second element of both may be either an FID or a long,
        depending on value of first element."""
        def hasFids(self,formElements):
            formElements.add(self)
        def dumpData(self,record,out):
            if ((self.subType == 'PLDT' and (record.locType or record.locId)) or
                (self.subType == 'PTDT' and (record.targetType or record.targetId))):
                MelStruct.dumpData(self,record,out)
        def mapFids(self,record,function,save=False):
            """Applies function to fids. If save is true, then fid is set
            to result of function."""
            if self.subType == 'PLDT' and record.locType != 5:
                result = function(record.locId)
                if save: record.locId = result
            elif self.subType == 'PTDT' and record.targetType != 2:
                result = function(record.targetId)
                if save: record.targetId = result
    #--MelSet
    melSet = MelSet(
        MelString('EDID','eid'),
        MelPackPkdt('PKDT','IB3s',(_flags,'flags'),'aiType',('unused1',null3)),
        MelPackLT('PLDT','iIi','locType','locId','locRadius'),
        MelStruct('PSDT','2bBbi','month','day','date','time','duration'),
        MelPackLT('PTDT','iIi','targetType','targetId','targetCount'),
        MelConditions(),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreQust(MelRecord):
    """Quest record."""
    classType = 'QUST'
    _questFlags = Flags(0,Flags.getNames('startGameEnabled',None,'repeatedTopics','repeatedStages'))
    stageFlags = Flags(0,Flags.getNames('complete'))
    targetFlags = Flags(0,Flags.getNames('ignoresLocks'))

    #--CDTA loader
    class MelQustLoaders(DataDict):
        """Since CDTA subrecords occur in three different places, we need
        to replace ordinary 'loaders' dictionary with a 'dictionary' that will
        return the correct element to handle the CDTA subrecord. 'Correct'
        element is determined by which other subrecords have been encountered."""
        def __init__(self,loaders,quest,stages,targets):
            self.data = loaders
            self.type_ctda = {'EDID':quest, 'INDX':stages, 'QSTA':targets}
            self.ctda = quest #--Which ctda element loader to use next.
        def __getitem__(self,key):
            if key == 'CTDA': return self.ctda
            self.ctda = self.type_ctda.get(key, self.ctda)
            return self.data[key]

    #--MelSet
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFid('SCRI','script'),
        MelString('FULL','full'),
        MelString('ICON','iconPath'),
        MelStruct('DATA','BB',(_questFlags,'questFlags',0),'priority'),
        MelConditions(),
        MelGroups('stages',
            MelStruct('INDX','h','stage'),
            MelGroups('entries',
                MelStruct('QSDT','B',(stageFlags,'flags')),
                MelConditions(),
                MelString('CNAM','text'),
                MelStruct('SCHR','4s4I',('unused1',null4),'numRefs','compiledSize','lastIndex','scriptType'),
                MelBase('SCDA','compiled_p'),
                MelString('SCTX','scriptText'),
                MelScrxen('SCRV/SCRO','references')
                ),
            ),
        MelGroups('targets',
            MelStruct('QSTA','IB3s',(FID,'targetId'),(targetFlags,'flags'),('unused1',null3)),
            MelConditions(),
            ),
        )
    melSet.loaders = MelQustLoaders(melSet.loaders,*melSet.elements[5:8])
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRace(MelRecord):
    """Race record.

    This record is complex to read and write. Relatively simple problems are the VNAM
    which can be empty or zeroed depending on relationship between voices and
    the fid for the race.

    The face and body data is much more complicated, with the same subrecord types
    mapping to different attributes depending on preceding flag subrecords (NAM0, NAM1,
    NMAN, FNAM and INDX.) These are handled by using the MelRaceDistributor class
    to dynamically reassign melSet.loaders[type] as the flag records are encountered.

    It's a mess, but this is the shortest, clearest implementation that I could
    think of."""

    classType = 'RACE'
    _flags = Flags(0L,Flags.getNames('playable'))

    class MelRaceVoices(MelStruct):
        """Set voices to zero, if equal race fid. If both are zero, then don't skip dump."""
        def dumpData(self,record,out):
            if record.maleVoice == record.fid: record.maleVoice = 0L
            if record.femaleVoice == record.fid: record.femaleVoice = 0L
            if (record.maleVoice,record.femaleVoice) != (0,0):
                MelStruct.dumpData(self,record,out)

    class MelRaceModel(MelGroup):
        """Most face data, like a MelModel - MODT + ICON. Load is controlled by MelRaceDistributor."""
        def __init__(self,attr,index):
            MelGroup.__init__(self,attr,
                MelString('MODL','modPath'),
                MelBase('MODB','modb_p'),
                MelString('ICON','iconPath'),)
            self.index = index

        def dumpData(self,record,out):
            out.packSub('INDX','I',self.index)
            MelGroup.dumpData(self,record,out)

    class MelRaceIcon(MelString):
        """Most body data plus eyes for face. Load is controlled by MelRaceDistributor."""
        def __init__(self,attr,index):
            MelString.__init__(self,'ICON',attr)
            self.index = index
        def dumpData(self,record,out):
            out.packSub('INDX','I',self.index)
            MelString.dumpData(self,record,out)

    class MelRaceDistributor(MelNull):
        """Handles NAM0, NAM1, MNAM, FMAN and INDX records. Distributes load
        duties to other elements as needed."""
        def __init__(self):
            bodyAttrs = ('UpperBodyPath','LowerBodyPath','HandPath','FootPath','TailPath')
            self.attrs = {
                'MNAM':tuple('male'+text for text in bodyAttrs),
                'FNAM':tuple('female'+text for text in bodyAttrs),
                'NAM0':('head', 'maleEars', 'femaleEars', 'mouth',
                'teethLower', 'teethUpper', 'tongue', 'leftEye', 'rightEye',)
                }
            self.tailModelAttrs = {'MNAM':'maleTailModel','FNAM':'femaleTailModel'}
            self._debug = False

        def getSlotsUsed(self):
            return ('_loadAttrs',)

        def getLoaders(self,loaders):
            """Self as loader for structure types."""
            for type in ('NAM0','MNAM','FNAM','INDX'):
                loaders[type] = self

        def setMelSet(self,melSet):
            """Set parent melset. Need this so that can reassign loaders later."""
            self.melSet = melSet
            self.loaders = {}
            for element in melSet.elements:
                attr = element.__dict__.get('attr',None)
                if attr: self.loaders[attr] = element

        def loadData(self,record,ins,type,size,readId):
            if type in ('NAM0','MNAM','FNAM'):
                record._loadAttrs = self.attrs[type]
                attr = self.tailModelAttrs.get(type)
                if not attr: return
            else: #--INDX
                index, = ins.unpack('I',4,readId)
                attr = record._loadAttrs[index]
            element = self.loaders[attr]
            for type in ('MODL','MODB','ICON'):
                self.melSet.loaders[type] = element

    #--Mel Set
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelString('DESC','text'),
        MelFids('SPLO','spells'),
        MelStructs('XNAM','Ii','relations',(FID,'faction'),'mod'),
        MelStruct('DATA','14b2s4fI','skill1','skill1Boost','skill2','skill2Boost',
                  'skill3','skill3Boost','skill4','skill4Boost','skill5','skill5Boost',
                  'skill6','skill6Boost','skill7','skill7Boost',('unused1',null2),
                  'maleHeight','femaleHeight','maleWeight','femaleWeight',(_flags,'flags',0L)),
        MelRaceVoices('VNAM','2I',(FID,'maleVoice'),(FID,'femaleVoice')), #--0 same as race fid.
        MelOptStruct('DNAM','2I',(FID,'defaultHairMale',0L),(FID,'defaultHairFemale',0L)), #--0=None
        MelStruct('CNAM','B','defaultHairColor'), #--Int corresponding to GMST sHairColorNN
        MelOptStruct('PNAM','f','mainClamp'),
        MelOptStruct('UNAM','f','faceClamp'),
        #--Male: Str,Int,Wil,Agi,Spd,End,Per,luck; Female Str,Int,...
        MelStruct('ATTR','16B','maleStrength','maleIntelligence','maleWillpower',
                  'maleAgility','maleSpeed','maleEndurance','malePersonality',
                  'maleLuck','femaleStrength','femaleIntelligence',
                  'femaleWillpower','femaleAgility','femaleSpeed',
                  'femaleEndurance','femalePersonality','femaleLuck'),
        #--Begin Indexed entries
        MelBase('NAM0','_nam0',''), ####Face Data Marker, wbEmpty
        MelRaceModel('head',0),
        MelRaceModel('maleEars',1),
        MelRaceModel('femaleEars',2),
        MelRaceModel('mouth',3),
        MelRaceModel('teethLower',4),
        MelRaceModel('teethUpper',5),
        MelRaceModel('tongue',6),
        MelRaceModel('leftEye',7),
        MelRaceModel('rightEye',8),
        MelBase('NAM1','_nam1',''), ####Body Data Marker, wbEmpty
        MelBase('MNAM','_mnam',''), ####Male Body Data Marker, wbEmpty
        MelModel('maleTailModel'),
        MelRaceIcon('maleUpperBodyPath',0),
        MelRaceIcon('maleLowerBodyPath',1),
        MelRaceIcon('maleHandPath',2),
        MelRaceIcon('maleFootPath',3),
        MelRaceIcon('maleTailPath',4),
        MelBase('FNAM','_fnam',''), ####Female Body Data Marker, wbEmpty
        MelModel('femaleTailModel'),
        MelRaceIcon('femaleUpperBodyPath',0),
        MelRaceIcon('femaleLowerBodyPath',1),
        MelRaceIcon('femaleHandPath',2),
        MelRaceIcon('femaleFootPath',3),
        MelRaceIcon('femaleTailPath',4),
        #--Normal Entries
        MelFidList('HNAM','hairs'),
        MelFidList('ENAM','eyes'),
        MelBase('FGGS','fggs_p'), ####FaceGen Geometry-Symmetric
        MelBase('FGGA','fgga_p'), ####FaceGen Geometry-Asymmetric
        MelBase('FGTS','fgts_p'), ####FaceGen Texture-Symmetric
        MelStruct('SNAM','2s',('snam_p',null2)),
        #--Distributor for face and body entries.
        MelRaceDistributor(),
        )
    melSet.elements[-1].setMelSet(melSet)
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRefr(MelRecord):
    classType = 'REFR'
    _flags = Flags(0L,Flags.getNames('visible', 'canTravelTo'))
    _actFlags = Flags(0L,Flags.getNames('useDefault', 'activate','open','openByDefault'))
    _lockFlags = Flags(0L,Flags.getNames(None, None, 'leveledLock'))
    class MelRefrXloc(MelOptStruct):
        """Handle older trucated XLOC for REFR subrecord."""
        def loadData(self,record,ins,type,size,readId):
            if size == 16:
                MelStruct.loadData(self,record,ins,type,size,readId)
                return
            elif size == 12:
                #--Else is skipping unused2
                unpacked = ins.unpack('B3sIB3s',size,readId)
            else:
                raise "Unexpected size encountered for REFR:XLOC subrecord: %s" % size
            unpacked = unpacked[:-2] + self.defaults[len(unpacked)-2:-2] + unpacked[-2:]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    class MelRefrXmrk(MelStruct):
        """Handler for xmrk record. Conditionally loads next items."""
        def loadData(self,record,ins,type,size,readId):
            """Reads data from ins into record attribute."""
            junk = ins.read(size,readId)
            record.hasXmrk = True
            insTell = ins.tell
            insUnpack = ins.unpack
            pos = insTell()
            (type,size) = insUnpack('4sH',6,readId+'.FULL')
            while type in ['FNAM','FULL','TNAM']:
                if type == 'FNAM':
                    value = insUnpack('B',size,readId)
                    record.flags = MreRefr._flags(*value)
                elif type == 'FULL':
                    record.full = ins.readString(size,readId)
                elif type == 'TNAM':
                    record.markerType, record.unused5 = insUnpack('Bs',size,readId)
                pos = insTell()
                (type,size) = insUnpack('4sH',6,readId+'.FULL')
            ins.seek(pos)
            if self._debug: print ' ',record.flags,record.full,record.markerType
            
        def dumpData(self,record,out):
            if (record.flags,record.full,record.markerType,record.unused5) != self.defaults[1:]:
                record.hasXmrk = True
            if record.hasXmrk:
                try:
                    out.write(struct.pack('=4sH','XMRK',0))
                    out.packSub('FNAM','B',record.flags.dump())
                    value = record.full
                    if value != None:
                        out.packSub0('FULL',value)
                    out.packSub('TNAM','Bs',record.markerType, record.unused5)
                except struct.error:
                    print self.subType,self.format,record.flags,record.full,record.markerType
                    raise

    melSet = MelSet(
        MelString('EDID','eid'),
        MelFid('NAME','base'),
        MelOptStruct('XTEL','l6f',(FID,'destinationFid'),'destinationPosX','destinationPosY',
            'destinationPosZ','destinationRotX','destinationRotY','destinationRotZ'),
        MelRefrXloc('XLOC','B3sI4sB3s','lockLevel',('unused1',null3),(FID,'lockKey'),('unused2',null4),(_lockFlags,'lockFlags'),('unused3',null3)),
        MelOwnership(),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),('unused4',null3)),
        MelFid('XTRG','targetId'),
        MelBase('XSED','seed_p'),
        ####SpeedTree Seed, if it's a single byte then it's an offset into the list of seed values in the TREE record
        ####if it's 4 byte it's the seed value directly.
        MelOptStruct('XLOD','3f',('lod1',None),('lod2',None),('lod3',None)), ####Distant LOD Data, unknown
        MelOptStruct('XCHG','f',('charge',None)),
        MelOptStruct('XHLT','i',('health',None)),
        MelXpci('XPCI'), ####fid, unknown
        MelOptStruct('XLCM','i',('levelMod',None)),
        MelFid('XRTM','xrtm'), ####unknown
        MelOptStruct('XACT','I',(_actFlags,'actFlags',0L)), ####Action Flag
        MelOptStruct('XCNT','i','count'),
        MelRefrXmrk('XMRK','',('hasXmrk',False),(_flags,'flags',0L),'full','markerType',('unused5',null1)), ####Map Marker Start Marker, wbEmpty
        MelBase('ONAM','onam_p'), ####Open by Default, wbEmpty
        MelOptStruct('XSCL','f',('scale',1.0)),
        MelOptStruct('XSOL','B',('soul',None)), ####Was entirely missing. Confirmed by creating a test mod...it isn't present in any of the official esps
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRegn(MelRecord):
    """Road structure. Part of large worldspaces."""
    classType = 'REGN'
    _flags = Flags(0L,Flags.getNames(
        ( 2,'objects'),
        ( 3,'weather'),
        ( 4,'map'),
        ( 6,'grass'),
        ( 7,'sound'),))
    obflags = Flags(0L,Flags.getNames(
        ( 0,'conform'),
        ( 1,'paintVertices'),
        ( 2,'sizeVariance'),
        ( 3,'deltaX'),
        ( 4,'deltaY'),
        ( 5,'deltaZ'),
        ( 6,'Tree'),
        ( 7,'hugeRock'),))
    sdflags = Flags(0L,Flags.getNames(
        ( 0,'pleasant'),
        ( 1,'cloudy'),
        ( 2,'rainy'),
        ( 3,'snowy'),))

    ####Lazy hacks to correctly read/write regn data
    class MelRegnStructA(MelStructA):
        """Handler for regn record. Conditionally dumps next items."""
        def loadData(self,record,ins,type,size,readId):
            if record.entryType == 2 and self.subType == 'RDOT':
                MelStructA.loadData(self,record,ins,type,size,readId)
            elif record.entryType == 3 and self.subType == 'RDWT':
                MelStructA.loadData(self,record,ins,type,size,readId)
            elif record.entryType == 6 and self.subType == 'RDGS':
                MelStructA.loadData(self,record,ins,type,size,readId)
            elif record.entryType == 7 and self.subType == 'RDSD':
                MelStructA.loadData(self,record,ins,type,size,readId)
                
        def dumpData(self,record,out):
            """Conditionally dumps data."""
            if record.entryType == 2 and self.subType == 'RDOT':
                MelStructA.dumpData(self,record,out)
            elif record.entryType == 3 and self.subType == 'RDWT':
                MelStructA.dumpData(self,record,out)
            elif record.entryType == 6 and self.subType == 'RDGS':
                MelStructA.dumpData(self,record,out)
            elif record.entryType == 7 and self.subType == 'RDSD':
                MelStructA.dumpData(self,record,out)

    class MelRegnString(MelString):
        """Handler for regn record. Conditionally dumps next items."""
        def loadData(self,record,ins,type,size,readId):
            if record.entryType == 4 and self.subType == 'RDMP':
                MelString.loadData(self,record,ins,type,size,readId)
            elif record.entryType == 5 and self.subType == 'ICON':
                MelString.loadData(self,record,ins,type,size,readId)
                
        def dumpData(self,record,out):
            """Conditionally dumps data."""
            if record.entryType == 4 and self.subType == 'RDMP':
                MelString.dumpData(self,record,out)
            elif record.entryType == 5 and self.subType == 'ICON':
                MelString.dumpData(self,record,out)

    class MelRegnOptStruct(MelOptStruct):
        """Handler for regn record. Conditionally dumps next items."""
        def loadData(self,record,ins,type,size,readId):
            if record.entryType == 7 and self.subType == 'RDMD':
                MelOptStruct.loadData(self,record,ins,type,size,readId)
        
        def dumpData(self,record,out):
            """Conditionally dumps data."""
            if record.entryType == 7 and self.subType == 'RDMD':
                MelOptStruct.dumpData(self,record,out)

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('ICON','iconPath'),
        MelStruct('RCLR','3Bs','mapRed','mapBlue','mapGreen',('unused1',null1)),
        MelFid('WNAM','worldspace'),
        MelGroups('areas',
            MelStruct('RPLI','I','edgeFalloff'),
            MelStructA('RPLD','2f','points','posX','posY')),
        MelGroups('entries',
            MelStruct('RDAT', 'I2B2s','entryType', (_flags,'flags'), 'priority', ('unused1',null2)), ####flags actually an enum...
            MelRegnStructA('RDOT', 'IH2sf4B2H4s4f3H2s4s', 'objects', (FID,'objectId'), 'parentIndex',
            ('unused1',null2), 'density', 'clustering', 'minSlope', 'maxSlope',
            (obflags, 'flags'), 'radiusWRTParent', 'radius', ('unk1',null4),
            'maxHeight', 'sink', 'sinkVar', 'sizeVar', 'angleVarX',
            'angleVarY',  'angleVarZ', ('unused2',null2), ('unk2',null4)),
            MelRegnString('RDMP', 'mapName'),
            MelRegnString('ICON', 'iconPath'),  ####Obsolete? Only one record in oblivion.esm
            MelRegnStructA('RDGS', 'I4s', 'grasses', (FID,'grass'), ('unk1',null4)),
            MelRegnOptStruct('RDMD', 'I', ('musicType',None)),
            MelRegnStructA('RDSD', '3I', 'sounds', (FID, 'sound'), (sdflags, 'flags'), 'chance'),
            MelRegnStructA('RDWT', '2I', 'weather', (FID, 'weather'), 'chance')),
    )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRoad(MelRecord):
    """Road structure. Part of large worldspaces."""
    ####Could probably be loaded via MelStructA,
    ####but little point since it is too complex to manipulate
    classType = 'ROAD'
    melSet = MelSet(
        MelBase('PGRP','points_p'), 
        MelBase('PGRR','connections_p'),
    )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()
#------------------------------------------------------------------------------
class MreSbsp(MelRecord):
    """Subspace record."""
    classType = 'SBSP'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('DNAM','3f','sizeX','sizeY','sizeZ'),
    )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()
#------------------------------------------------------------------------------
class MreScpt(MelRecord):
    """Script record."""
    classType = 'SCPT'
    _flags = Flags(0L,Flags.getNames('isLongOrShort'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('SCHR','4s4I',('unused1',null4),'numRefs','compiledSize','lastIndex','scriptType'),
        #--Type: 0: Object, 1: Quest, 0x100: Magic Effect
        MelBase('SCDA','compiled_p'),
        MelString('SCTX','scriptText'),
        MelGroups('vars',
            MelStruct('SLSD','I12sB7s','index',('unused1',null4+null4+null4),(_flags,'flags',0L),('unused2',null4+null3)),
            MelString('SCVR','name')),
        MelScrxen('SCRV/SCRO','references'),
    )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSgst(MelRecord,MreHasEffects):
    """Sigil stone record."""
    classType = 'SGST'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFull0(),
        MelModel(),
        MelString('ICON','iconPath'),
        MelFid('SCRI','script'),
        MelEffects(),
        MelStruct('DATA','=BIf','uses','value','weight'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSkil(MelRecord):
    """Skill record."""
    classType = 'SKIL'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('INDX','i','skill'),
        MelString('DESC','description'),
        MelString('ICON','iconPath'),
        MelStruct('DATA','2iI2f','action','attribute','specialization',('use0',1.0),'use1'),
        MelString('ANAM','apprentice'),
        MelString('JNAM','journeyman'),
        MelString('ENAM','expert'),
        MelString('MNAM','master'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSlgm(MelRecord):
    """Soul gem record."""
    classType = 'SLGM'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelFid('SCRI','script'),
        MelStruct('DATA','If','value','weight'),
        MelStruct('SOUL','B',('soul',0)),
        MelStruct('SLCP','B',('capacity',1)),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSoun(MelRecord):
    """Sound record."""
    classType = 'SOUN'
    _flags = Flags(0L,Flags.getNames('randomFrequencyShift', 'playAtRandom',
        'environmentIgnored', 'randomLocation', 'loop','menuSound', '2d', '360LFE'))
    class MelSounSndd(MelStruct):
        """SNDD is an older version of SNDX. Allow it to read in, but not set defaults or write."""
        def loadData(self,record,ins,type,size,readId):
            MelStruct.loadData(self,record,ins,type,size,readId)
            record.staticAtten = 0
            record.stopTime = 0
            record.startTime = 0
        def getSlotsUsed(self):
            return ()
        def setDefault(self,record): return
        def dumpData(self,record,out): return
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FNAM','soundFile'),
        MelSounSndd('SNDD','=2BbsH2s','minDistance', 'maxDistance', 'freqAdjustment', ('unused1',null1),
            (_flags,'flags'), ('unused2',null2)),
        MelOptStruct('SNDX','=2BbsH2sh2B',('minDistance',None), ('maxDistance',None), ('freqAdjustment',None), ('unused1',null1),
            (_flags,'flags',None), ('unused2',null2), ('staticAtten',None),('stopTime',None),('startTime',None),)
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSpel(MelRecord,MreHasEffects):
    """Spell record."""
    classType = 'SPEL'
    class SpellFlags(Flags):
        """For SpellFlags, immuneSilence activates bits 1 AND 3."""
        def __setitem__(self,index,value):
            setter = Flags.__setitem__
            setter(self,index,value)
            if index == 1:
                setter(self,3,value)
    flags = SpellFlags(0L,Flags.getNames('noAutoCalc', 'immuneToSilence',
        'startSpell', None,'ignoreLOS','scriptEffectAlwaysApplies','disallowAbsorbReflect','touchExplodesWOTarget'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFull0(),
        MelStruct('SPIT','3IB3s','spellType','cost','level',(flags,'flags',0L),('unused1',null3)),
        # spellType = 0: Spell, 1: Disease, 3: Lesser Power, 4: Ability, 5: Poison
        MelEffects(),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreStat(MelRecord):
    """Static model record."""
    classType = 'STAT'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreTes4(MelRecord):
    """TES4 Record. File header."""
    classType = 'TES4' #--Used by LoadFactory
    #--Masters array element
    class MelTes4Name(MelBase):
        def setDefault(self,record):
            record.masters = []
        def loadData(self,record,ins,type,size,readId):
            name = GPath(ins.readString(size,readId))
            record.masters.append(name)
        def dumpData(self,record,out):
            pack1 = out.packSub0
            pack2 = out.packSub
            for name in record.masters:
                pack1('MAST',name.s)
                pack2('DATA','Q',0)
    #--Data elements
    melSet = MelSet(
        MelStruct('HEDR','f2I',('version',0.8),'numRecords',('nextObject',0xCE6)),
        MelBase('OFST','ofst_p',), #--Obsolete?
        MelBase('DELE','dele_p'), #--Obsolete?
        MelString('CNAM','author','',512),
        MelString('SNAM','description','',512),
        MelTes4Name('MAST','masters'),
        MelNull('DATA'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

    def getNextObject(self):
        """Gets next object index and increments it for next time."""
        self.changed = True
        self.nextObject += 1
        return (self.nextObject -1)

#------------------------------------------------------------------------------
class MreTree(MelRecord):
    """Tree record."""
    classType = 'TREE'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelStructA('SNAM','I','speedTree','seed'),
        MelStruct('CNAM','5fi2f', 'curvature','minAngle','maxAngle',
                  'branchDim','leafDim','shadowRadius','rockSpeed',
                  'rustleSpeed'),
        MelStruct('BNAM','2f','widthBill','heightBill'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWatr(MelRecord):
    """Water record."""
    classType = 'WATR'
    _flags = Flags(0L,Flags.getNames('causesDmg','reflective'))
    class MelWatrData(MelStruct):
        """Handle older trucated DATA for WATR subrecord."""
        def loadData(self,record,ins,type,size,readId):
            if size == 102:
                MelStruct.loadData(self,record,ins,type,size,readId)
                return
            elif size == 86:
                #--Else 86 byte record (skips dispVelocity,
                #-- dispFalloff, dispDampner, dispSize, and damage
                #-- Two junk? bytes are tacked onto the end
                #-- Hex editing and the CS confirms that it is NOT
                #-- damage, so it is probably just filler
                unpacked = ins.unpack('11f3Bs3Bs3BsB3s6f2s',size,readId)
            elif size == 62:
                #--Else 62 byte record (skips most everything
                #-- Two junk? bytes are tacked onto the end
                #-- No testing done, but assumed that its the same as the
                #-- previous truncated record.
                unpacked = ins.unpack('11f3Bs3Bs3BsB3s2s',size,readId)
            elif size == 42:
                #--Else 42 byte record (skips most everything
                #-- Two junk? bytes are tacked onto the end
                #-- No testing done, but assumed that its the same as the
                #-- previous truncated record.
                unpacked = ins.unpack('10f2s',size,readId)
            elif size == 2:
                #--Else 2 byte record (skips everything
                #-- Two junk? bytes are tacked onto the end
                #-- No testing done, but assumed that its the same as the
                #-- previous truncated record.
                unpacked = ins.unpack('2s',size,readId)
            else:
                raise "Unexpected size encountered for WATR subrecord: %s" % size
            unpacked = unpacked[:-1]
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('TNAM','texture'),
        MelStruct('ANAM','B','opacity'),
        MelStruct('FNAM','B',(_flags,'flags',0)),
        MelString('MNAM','material'),
        MelFid('SNAM','sound'),
        MelWatrData('DATA', '11f3Bs3Bs3BsB3s10fH',('windVelocity',0.100),
                    ('windDirection',90.0),('waveAmp',0.5),('waveFreq',1.0),('sunPower',50.0),
                    ('reflectAmt',0.5),('fresnelAmt',0.0250),('xSpeed',0.0),('ySpeed',0.0),
                    ('fogNear',27852.8),('fogFar',163840.0),('shallowRed',0),('shallowGreen',128),
                    ('shallowBlue',128),('unused1',null1),('deepRed',0),('deepGreen',0),
                    ('deepBlue',25),('unused2',null1),('reflRed',255),('reflGreen',255),
                    ('reflBlue',255),('unused3',null1),('blend',50),('unused4',null3),('rainForce',0.1000),
                    ('rainVelocity',0.6000),('rainFalloff',0.9850),('rainDampner',2.0000),
                    ('rainSize',0.0100),('dispForce',0.4000),('dispVelocity', 0.6000),
                    ('dispFalloff',0.9850),('dispDampner',10.0000),('dispSize',0.0500),('damage',0)),
        MelFidList('GNAM','relatedWaters'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWeap(MelRecord):
    """Weapon record."""
    classType = 'WEAP'
    _flags = Flags(0L,Flags.getNames('notNormalWeapon'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelFid('SCRI','script'),
        MelFid('ENAM','enchantment'),
        MelOptStruct('ANAM','H','enchantPoints'),
        MelStruct('DATA','I2f3IfH','weaponType','speed','reach',(_flags,'flags',0L),
            'value','health','weight','damage'),
        #--weaponType = 0: Blade 1Hand, 1: Blade 2Hand, 2: Blunt 1Hand, 3: Blunt 2Hand, 4: Staff, 5: Bow
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWrld(MelRecord):
    """Worldspace record."""
    classType = 'WRLD'
    _flags = Flags(0L,Flags.getNames('smallWorld','noFastTravel','oblivionWorldspace',None,'noLODWater'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelFid('WNAM','parent'),
        MelFid('CNAM','climate'),
        MelFid('NAM2','water'),
        MelString('ICON','mapPath'),
        MelOptStruct('MNAM','2i4h',('dimX',None),('dimY',None),('NWCellX',None),('NWCellY',None),('SECellX',None),('SECellY',None)),
        MelStruct('DATA','B',(_flags,'flags',0L)),
        MelTuple('NAM0','ff','unknown0',(None,None)),
        MelTuple('NAM9','ff','unknown9',(None,None)),
        MelOptStruct('SNAM','I','sound'),
        MelBase('OFST','ofst_p'),
    )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWthr(MelRecord):
    """Weather record."""
    classType = 'WTHR'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('CNAM','lowerLayer'),
        MelString('DNAM','upperLayer'),
        MelModel(),
        MelStructA('NAM0','3Bs3Bs3Bs3Bs','colors','riseRed','riseGreen','riseBlue',('unused1',null1),
                   'dayRed','dayGreen','dayBlue',('unused2',null1),
                   'setRed','setGreen','setBlue',('unused3',null1),
                   'nightRed','nightGreen','nightBlue',('unused4',null1),
                   ),
        MelStruct('FNAM','4f','fogDayNear','fogDayFar','fogNightNear','fogNightFar'),
        MelStruct('HNAM','14f',
            'eyeAdaptSpeed', 'blurRadius', 'blurPasses', 'emissiveMult',
            'targetLum', 'upperLumClamp', 'brightScale', 'brightClamp',
            'lumRampNoTex', 'lumRampMin', 'lumRampMax', 'sunlightDimmer',
            'grassDimmer', 'treeDimmer'),
        MelStruct('DATA','15B',
            'windSpeed','lowerCloudSpeed','upperCloudSpeed','transDelta',
            'sunGlare','sunDamage','rainFadeIn','rainFadeOut','boltFadeIn',
            'boltFadeOut','boltFrequency','weatherType','boltRed','boltBlue','boltGreen'),
        MelStructs('SNAM','2I','sounds',(FID,'sound'),'type'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

# MreRecord.type_class
MreRecord.type_class = dict((x.classType,x) for x in (
    MreAchr, MreAcre, MreActi, MreAlch, MreAmmo, MreAnio, MreAppa, MreArmo, MreBook, MreBsgn,
    MreCell, MreClas, MreClot, MreCont, MreCrea, MreDoor, MreEfsh, MreEnch, MreEyes, MreFact,
    MreFlor, MreFurn, MreGlob, MreGmst, MreGras, MreHair, MreIngr, MreKeym, MreLigh, MreLscr,
    MreLvlc, MreLvli, MreLvsp, MreMgef, MreMisc, MreNpc,  MrePack, MreQust, MreRace, MreRefr,
    MreRoad, MreScpt, MreSgst, MreSkil, MreSlgm, MreSoun, MreSpel, MreStat, MreTree, MreTes4,
    MreWatr, MreWeap, MreWrld, MreWthr, MreClmt, MreCsty, MreIdle, MreLtex, MreRegn, MreSbsp,
    MreDial, MreInfo
    ))
MreRecord.simpleTypes = (set(MreRecord.type_class) -
    set(('TES4','ACHR','ACRE','REFR','CELL','PGRD','ROAD','LAND','WRLD','INFO','DIAL')))

# Mod Blocks, File ------------------------------------------------------------
#------------------------------------------------------------------------------
class MasterMapError(BoltError):
    """Attempt to map a fid when mapping does not exist."""
    def __init__(self,modIndex):
        BoltError.__init__(self,_('No valid mapping for mod index 0x%02X') % modIndex)

#------------------------------------------------------------------------------
class MasterMap:
    """Serves as a map between two sets of masters."""
    def __init__(self,inMasters,outMasters):
        """Initiation."""
        map = {}
        outMastersIndex = outMasters.index
        for index,master in enumerate(inMasters):
            if master in outMasters:
                map[index] = outMastersIndex(master)
            else:
                map[index] = -1
        self.map = map

    def __call__(self,fid,default=-1):
        """Maps a fid from first set of masters to second. If no mapping
        is possible, then either returns default (if defined) or raises MasterMapError."""
        if not fid: return fid
        inIndex = int(fid >> 24)
        outIndex = self.map.get(inIndex,-2)
        if outIndex >= 0:
            return (long(outIndex) << 24 ) | (fid & 0xFFFFFFL)
        elif default != -1:
            return default
        else:
            raise MasterMapError(inIndex)

#------------------------------------------------------------------------------
class MasterSet(set):
    """Set of master names."""

    def add(self,element):
        """Add an element it's not empty. Special handling for tuple."""
        if isinstance(element,tuple):
            set.add(self,element[0])
        elif element:
            set.add(self,element)

    def getOrdered(self):
        """Returns masters in proper load order."""
        return list(modInfos.getOrdered(list(self)))

#------------------------------------------------------------------------------
class LoadFactory:
    """Factory for mod representation objects."""
    def __init__(self,keepAll,*recClasses):
        """Initialize."""
        self.keepAll = keepAll
        self.recTypes = set()
        self.topTypes = set()
        self.type_class = {}
        self.cellType_class = {}
        addClass = self.addClass
        for recClass in recClasses:
            addClass(recClass)

    def addClass(self,recClass):
        """Adds specified class."""
        cellTypes = ('WRLD','ROAD','CELL','REFR','ACHR','ACRE','PGRD','LAND')
        if isinstance(recClass,str):
            recType = recClass
            recClass = MreRecord
        else:
            recType = recClass.classType
        #--Don't replace complex class with default (MreRecord) class
        if recType in self.type_class and recClass == MreRecord:
            return
        self.recTypes.add(recType)
        self.type_class[recType] = recClass
        #--Top type
        if recType in cellTypes:
            topAdd = self.topTypes.add
            topAdd('CELL')
            topAdd('WRLD')
            if self.keepAll:
                setterDefault = self.type_class.setdefault
                for type in cellTypes:
                    setterDefault(type,MreRecord)
        elif recType == 'INFO':
            self.topTypes.add('DIAL')
        else:
            self.topTypes.add(recType)

    def getRecClass(self,type):
        """Returns class for record type or None."""
        default = (self.keepAll and MreRecord) or None
        return self.type_class.get(type,default)

    def getCellTypeClass(self):
        """Returns type_class dictionary for cell objects."""
        if not self.cellType_class:
            types = ('REFR','ACHR','ACRE','PGRD','LAND','CELL','ROAD')
            getterRecClass = self.getRecClass
            self.cellType_class.update((x,getterRecClass(x)) for x in types)
        return self.cellType_class

    def getUnpackCellBlocks(self,topType):
        """Returns whether cell blocks should be unpacked or not. Only relevant
        if CELL and WRLD top types are expanded."""
        return (
            self.keepAll or
            (self.recTypes & set(('REFR','ACHR','ACRE','PGRD','LAND'))) or
            (topType == 'WRLD' and 'LAND' in self.recTypes))

    def getTopClass(self,type):
        """Returns top block class for top block type, or None."""
        if type in self.topTypes:
            if   type == 'DIAL': return MobDials
            elif type == 'CELL': return MobICells
            elif type == 'WRLD': return MobWorlds
            else: return MobObjects
        elif self.keepAll:
            return MobBase
        else:
            return None

#------------------------------------------------------------------------------
class MobBase(object):
    """Group of records and/or subgroups. This basic implementation does not
    support unpacking, but can report its number of records and be written."""

    __slots__=['size','label','groupType','stamp','debug','data','changed','numRecords','loadFactory','inName']

    def __init__(self,header,loadFactory,ins=None,unpack=False):
        """Initialize."""
        (grup, self.size, self.label, self.groupType, self.stamp) = header
        self.debug = False
        self.data = None
        self.changed = False
        self.numRecords = -1
        self.loadFactory = loadFactory
        self.inName = ins and ins.inName
        if ins: self.load(ins,unpack)

    def load(self,ins=None,unpack=False):
        """Load data from ins stream or internal data buffer."""
        if self.debug: print 'GRUP load:',self.label
        #--Read, but don't analyze.
        if not unpack:
            self.data = ins.read(self.size-20,type)
        #--Analyze ins.
        elif ins is not None:
            self.loadData(ins, ins.tell()+self.size-20)
        #--Analyze internal buffer.
        else:
            reader = self.getReader()
            self.loadData(reader,reader.size)
            reader.close()
        #--Discard raw data?
        if unpack:
            self.data = None
            self.setChanged()

    def loadData(self,ins,endPos):
        """Loads data from input stream. Called by load()."""
        raise AbstractError

    def setChanged(self,value=True):
        """Sets changed attribute to value. [Default = True.]"""
        self.changed = value

    def getSize(self):
        """Returns size (incuding size of any group headers)."""
        if self.changed: raise AbstractError
        return self.size

    def getNumRecords(self,includeGroups=True):
        """Returns number of records, including self (if plusSelf), unless there's no
        subrecords, in which case, it returns 0."""
        if self.changed:
            raise AbstractError
        elif self.numRecords > -1: #--Cached value.
            return self.numRecords
        elif not self.data: #--No data >> no records, not even self.
            self.numRecords = 0
            return self.numRecords
        else:
            numSubRecords = 0
            reader = self.getReader()
            errLabel = bush.groupTypes[self.groupType]
            readerAtEnd = reader.atEnd
            readerRecHeader = reader.unpackRecHeader
            readerSeek = reader.seek
            while not readerAtEnd(reader.size,errLabel):
                header = readerRecHeader()
                type,size = header[0:2]
                if type == 'GRUP': size = 0
                readerSeek(size,1)
                numSubRecords += 1
            self.numRecords = numSubRecords + includeGroups
            return self.numRecords

    def dump(self,out):
        """Dumps record header and data into output file stream."""
        if self.changed:
            raise AbstractError
        if self.numRecords == -1:
            self.getNumRecords()
        if self.numRecords > 0:
            out.pack('4sI4sII','GRUP',self.size,self.label,self.groupType,self.stamp)
            out.write(self.data)

    def getReader(self):
        """Returns a ModReader wrapped around self.data."""
        return ModReader(self.inName,cStringIO.StringIO(self.data))

    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if converting to short format."""
        raise AbstractError

    def updateRecords(self,block,mapper,toLong):
        """Looks through all of the records in 'block', and updates any records in self that
        exist with the data in 'block'."""
        raise AbstractError

#------------------------------------------------------------------------------
class MobObjects(MobBase):
    """Represents a top level group consisting of one type of record only. I.e.
    all top groups except CELL, WRLD and DIAL."""

    def __init__(self,header,loadFactory,ins=None,unpack=False):
        """Initialize."""
        self.records = []
        self.id_records = {}
        MobBase.__init__(self,header,loadFactory,ins,unpack)

    def loadData(self,ins,endPos):
        """Loads data from input stream. Called by load()."""
        debug = self.debug
        expType = self.label
        recClass = self.loadFactory.getRecClass(expType)
        errLabel = expType+' Top Block'
        records = self.records
        insAtEnd = ins.atEnd
        insRecHeader = ins.unpackRecHeader
        recordsAppend = records.append
        while not insAtEnd(endPos,errLabel):
            #--Get record info and handle it
            header = insRecHeader()
            recType = header[0]
            if recType != expType:
                raise ModError(ins.inName,_('Unexpected %s record in %s group.')
                    % (recType,expType))
            record = recClass(header,ins,True)
            recordsAppend(record)
        self.setChanged()

    def getActiveRecords(self,getIgnored=True,getDeleted=True):
        """Returns non-ignored records."""
        return [record for record in self.records if not record.flags1.ignored]

    def getNumRecords(self,includeGroups=True):
        """Returns number of records, including self."""
        numRecords = len(self.records)
        if numRecords: numRecords += includeGroups #--Count self
        self.numRecords = numRecords
        return numRecords

    def getSize(self):
        """Returns size (incuding size of any group headers)."""
        if not self.changed:
            return self.size
        else:
            return 20 + sum((20 + record.getSize()) for record in self.records)

    def dump(self,out):
        """Dumps group header and then records."""
        if not self.changed:
            out.pack('4sI4sII','GRUP',self.size,self.label,0,self.stamp)
            out.write(self.data)
        else:
            size = self.getSize()
            if size == 20: return
            out.pack('4sI4sII','GRUP',size,self.label,0,self.stamp)
            for record in self.records:
                record.dump(out)

    def updateMasters(self,masters):
        """Updates set of master names according to masters actually used."""
        for record in self.records:
            record.updateMasters(masters)

    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if converting to short format."""
        for record in self.records:
            record.convertFids(mapper,toLong)
        self.id_records.clear()

    def indexRecords(self):
        """Indexes records by fid."""
        self.id_records.clear()
        for record in self.records:
            self.id_records[record.fid] = record

    def getRecord(self,fid,default=None):
        """Gets record with corresponding id.
        If record doesn't exist, returns None."""
        if not self.records: return default
        if not self.id_records: self.indexRecords()
        return self.id_records.get(fid,default)

    def getRecordByEid(self,eid,default=None):
        """Gets record by eid, or returns default."""
        if not self.records: return default
        for record in self.records:
            if record.eid == eid:
                return record
        else:
            return default

    def setRecord(self,record):
        """Adds record to record list and indexed."""
        if self.records and not self.id_records:
            self.indexRecords()
        fid = record.fid
        if fid in self.id_records:
            oldRecord = self.id_records[fid]
            index = self.records.index(oldRecord)
            self.records[index] = record
        else:
            self.records.append(record)
        self.id_records[fid] = record

    def keepRecords(self,keepIds):
        """Keeps records with fid in set keepIds. Discards the rest."""
        self.records = [record for record in self.records if record.fid in keepIds]
        self.id_records.clear()
        self.setChanged()

    def updateRecords(self,srcBlock,mapper,mergeIds):
        """Looks through all of the records in 'srcBlock', and updates any records in self that
        exist within the data in 'block'."""
        fids = set([record.fid for record in self.records])
        for record in srcBlock.getActiveRecords():
            if mapper(record.fid) in fids:
                record = record.getTypeCopy(mapper)
                self.setRecord(record)
                mergeIds.discard(record.fid)

#------------------------------------------------------------------------------
class MobDials(MobObjects):
    """DIAL top block of mod file."""

    def loadData(self,ins,endPos):
        """Loads data from input stream. Called by load()."""
        expType = self.label
        recClass = self.loadFactory.getRecClass(expType)
        errLabel = expType+' Top Block'
        records = self.records
        insAtEnd = ins.atEnd
        insRecHeader = ins.unpackRecHeader
        recordsAppend = records.append
        loadGetRecClass = self.loadFactory.getRecClass
        while not insAtEnd(endPos,errLabel):
            #--Get record info and handle it
            header = insRecHeader()
            recType = header[0]
            if recType == expType:
                record = recClass(header,ins,True)
                recordLoadInfos = record.loadInfos
                recordsAppend(record)
            elif recType == 'GRUP':
                (recType,size,label,groupType,stamp) = header
                if groupType == 7:
                    record.infoStamp = stamp
                    infoClass = loadGetRecClass('INFO')
                    recordLoadInfos(ins,ins.tell()+size-20,infoClass)
                else:
                    raise ModError(self.inName,'Unexpected subgroup %d in DIAL group.' % groupType)
            else:
                raise ModError(self.inName,_('Unexpected %s record in %s group.')
                    % (recType,expType))
        self.setChanged()

    def getSize(self):
        """Returns size of records plus group and record headers."""
        if not self.changed:
            return self.size
        size = 20
        for record in self.records:
            size += 20 + record.getSize()
            if record.infos:
                size += 20 + sum(20+info.getSize() for info in record.infos)
        return size

    def getNumRecords(self,includeGroups=1):
        """Returns number of records, including self plus info records."""
        self.numRecords = (
            len(self.records) + includeGroups*bool(self.records) +
            sum((includeGroups + len(x.infos)) for x in self.records if x.infos)
            )
        return self.numRecords

#-------------------------------------------------------------------------------
class MobCell(MobBase):
    """Represents cell block structure -- including the cell and all subrecords."""

    __slots__ = MobBase.__slots__ + ['cell','persistent','distant','temp','land','pgrd']

    def __init__(self,header,loadFactory,cell,ins=None,unpack=False):
        """Initialize."""
        self.cell=cell
        self.persistent=[]
        self.distant=[]
        self.temp=[]
        self.land=None
        self.pgrd=None
        MobBase.__init__(self,header,loadFactory,ins,unpack)

    def loadData(self,ins,endPos):
        """Loads data from input stream. Called by load()."""
        cellType_class = self.loadFactory.getCellTypeClass()
        persistent,temp,distant = self.persistent,self.temp,self.distant
        insAtEnd = ins.atEnd
        insRecHeader = ins.unpackRecHeader
        cellGet = cellType_class.get
        persistentAppend = persistent.append
        tempAppend = temp.append
        distantAppend = distant.append
        insSeek = ins.seek
        while not insAtEnd(endPos,'Cell Block'):
            subgroupLoaded=[False,False,False]
            header=insRecHeader()
            recType=header[0]
            recClass = cellGet(recType)
            if recType == 'GRUP':
                groupType=header[3]
                if groupType not in (8, 9, 10):
                    raise ModError(self.inName,'Unexpected subgroup %d in cell children group.' % groupType)
                if subgroupLoaded[groupType - 8]:
                    raise ModError(self.inName,'Extra subgroup %d in cell children group.' % groupType)
                else:
                    subgroupLoaded[groupType - 8] = True
            elif recType not in cellType_class:
                raise ModError(self.inName,'Unexpected %s record in cell children group.' % recType)
            elif not recClass:
                insSeek(header[1],1)
            elif recType in ('REFR','ACHR','ACRE'):
                record = recClass(header,ins,True)
                if   groupType ==  8: persistentAppend(record)
                elif groupType ==  9: tempAppend(record)
                elif groupType == 10: distantAppend(record)
            elif recType == 'LAND':
                self.land=recClass(header,ins,False)
            elif recType == 'PGRD':
                self.pgrd=recClass(header,ins,False)
        self.setChanged()

    def getSize(self):
        """Returns size (incuding size of any group headers)."""
        return 20 + self.cell.getSize() + self.getChildrenSize()

    def getChildrenSize(self):
        """Returns size of all childen, including the group header.  This does not include the cell itself."""
        size = self.getPersistentSize() + self.getTempSize() + self.getDistantSize()
        return size + 20*bool(size)

    def getPersistentSize(self):
        """Returns size of all persistent children, including the persistent children group."""
        size = sum(20 + x.getSize() for x in self.persistent)
        return size + 20*bool(size)

    def getTempSize(self):
        """Returns size of all temporary children, including the temporary children group."""
        size = sum(20 + x.getSize() for x in self.temp)
        if self.pgrd: size += 20 + self.pgrd.getSize()
        if self.land: size += 20 + self.land.getSize()
        return size + 20*bool(size)

    def getDistantSize(self):
        """Returns size of all distant children, including the distant children group."""
        size = sum(20 + x.getSize() for x in self.distant)
        return size + 20*bool(size)

    def getNumRecords(self,includeGroups=True):
        """Returns number of records, including self and all children."""
        count = 1 + includeGroups # Cell GRUP and CELL record
        if self.persistent:
            count += len(self.persistent) + includeGroups
        if self.temp or self.pgrd or self.land:
            count += len(self.temp) + includeGroups
            count += bool(self.pgrd) + bool(self.land)
        if self.distant:
            count += len(self.distant) + includeGroups
        return count

    def getBsb(self):
        """Returns tesfile block and sub-block indices for cells in this group.
        For interior cell, bsb is (blockNum,subBlockNum). For exterior cell, bsb is
        ((blockX,blockY),(subblockX,subblockY))."""
        cell = self.cell
        #--Interior cell
        if cell.flags.isInterior:
            baseFid = cell.fid & 0x00FFFFFF
            return (baseFid%10, baseFid%100//10)
        #--Exterior cell
        else:
            x,y = cell.posX,cell.posY
            if x is None: x = 0
            if y is None: y = 0
            return ((x//32, y//32), (x//8, y//8))

    def dump(self,out):
        """Dumps group header and then records."""
        self.cell.getSize()
        self.cell.dump(out)
        childrenSize = self.getChildrenSize()
        if not childrenSize: return
        out.writeGroup(childrenSize,self.cell.fid,6,self.stamp)
        if self.persistent:
            out.writeGroup(self.getPersistentSize(),self.cell.fid,8,self.stamp)
            for record in self.persistent:
                record.dump(out)
        if self.temp or self.pgrd or self.land:
            out.writeGroup(self.getTempSize(),self.cell.fid,9,self.stamp)
            if self.pgrd:
                self.pgrd.dump(out)
            if self.land:
                self.land.dump(out)
            for record in self.temp:
                record.dump(out)
        if self.distant:
            out.writeGroup(self.getDistantSize(),self.cell.fid,10,self.stamp)
            for record in self.distant:
                record.dump(out)

    #--Fid manipulation, record filtering ----------------------------------
    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if converting to short format."""
        self.cell.convertFids(mapper,toLong)
        for record in self.temp:
            record.convertFids(mapper,toLong)
        for record in self.persistent:
            record.convertFids(mapper,toLong)
        for record in self.distant:
            record.convertFids(mapper,toLong)
        if self.land:
            self.land.convertFids(mapper,toLong)
        if self.pgrd:
            self.pgrd.convertFids(mapper,toLong)

    def updateMasters(self,masters):
        """Updates set of master names according to masters actually used."""
        self.cell.updateMasters(masters)
        for record in self.persistent:
            record.updateMasters(masters)
        for record in self.distant:
            record.updateMasters(masters)
        for record in self.temp:
            record.updateMasters(masters)
        if self.land:
            self.land.updateMasters(masters)
        if self.pgrd:
            self.pgrd.updateMasters(masters)

    def updateRecords(self,srcBlock,mapper,mergeIds):
        """Updates any records in 'self' that exist in 'srcBlock'."""
        mergeDiscard = mergeIds.discard
        selfGetter = self.__getattribute__
        srcGetter = srcBlock.__getattribute__
        selfSetter = self.__setattr__
        for attr in ('cell','pgrd','land'):
            myRecord = selfGetter(attr)
            record = srcGetter(attr)
            if myRecord and record:
                if myRecord.fid != mapper(record.fid):
                    raise ArgumentError("Fids don't match! %08x, %08x" % (myRecord.fid, record.fid))
                if not record.flags1.ignored:
                    record = record.getTypeCopy(mapper)
                    selfSetter(attr,record)
                    mergeDiscard(record.fid)
        for attr in ('persistent','temp','distant'):
            recordList = selfGetter(attr)
            fids = dict((record.fid,index) for index,record in enumerate(recordList))
            for record in srcGetter(attr):
                if not record.flags1.ignored and mapper(record.fid) in fids:
                    record = record.getTypeCopy(mapper)
                    recordList[fids[record.fid]]=record
                    mergeDiscard(record.fid)

    def keepRecords(self,keepIds):
        """Keeps records with fid in set keepIds. Discards the rest."""
        if self.pgrd and self.pgrd.fid not in keepIds:
            self.pgrd = None
        if self.land and self.land.fid not in keepIds:
            self.land = None
        self.temp       = [x for x in self.temp if x.fid in keepIds]
        self.persistent = [x for x in self.persistent if x.fid in keepIds]
        self.distant    = [x for x in self.distant if x.fid in keepIds]
        if self.pgrd or self.land or self.persistent or self.temp or self.distant:
            keepIds.add(self.cell.fid)
        self.setChanged()

#-------------------------------------------------------------------------------
class MobCells(MobBase):
    """A block containing cells. Subclassed by MobWorld and MobICells.

    Note that "blocks" here only roughly match the file block structure.

    "Bsb" is a tuple of the file (block,subblock) labels. For interior cells, bsbs are tuples
    of two numbers, while for exterior cells, bsb labels are tuples of grid tuples."""

    def __init__(self,header,loadFactory,ins=None,unpack=False):
        """Initialize."""
        self.cellBlocks = [] #--Each cellBlock is a cell and it's related records.
        self.id_cellBlock = {}
        MobBase.__init__(self,header,loadFactory,ins,unpack)

    def indexRecords(self):
        """Indexes records by fid."""
        self.id_cellBlock = dict((x.cell.fid,x) for x in self.cellBlocks)

    def setCell(self,cell):
        """Adds record to record list and indexed."""
        if self.cellBlocks and not self.id_cellBlock:
            self.indexRecords()
        fid = cell.fid
        if fid in self.id_cellBlock:
            self.id_cellBlock[fid].cell = cell
        else:
            cellBlock = MobCell(('GRUP',0,0,6,self.stamp),self.loadFactory,cell)
            cellBlock.setChanged()
            self.cellBlocks.append(cellBlock)
            self.id_cellBlock[fid] = cellBlock

    def getUsedBlocks(self):
        """Returns a set of blocks that exist in this group."""
        return set(x.getBsb()[0] for x in self.cellBlocks)

    def getUsedSubblocks(self):
        """Returns a set of block/sub-blocks that exist in this group."""
        return set(x.getBsb() for x in self.cellBlocks)

    def getBsbSizes(self):
        """Returns the total size of the block, but also returns a dictionary containing the sizes
        of the individual block,subblocks."""
        bsbCellBlocks = [(x.getBsb(),x) for x in self.cellBlocks]
        bsbCellBlocks.sort(key = lambda x: x[1].cell.fid)
        bsbCellBlocks.sort(key = itemgetter(0))
        bsb_size = {}
        totalSize = 20
        bsb_setDefault = bsb_size.setdefault
        for bsb,cellBlock in bsbCellBlocks:
            cellBlockSize = cellBlock.getSize()
            totalSize += cellBlockSize
            bsb0 = (bsb[0],None) #--Block group
            bsb_setDefault(bsb0,20)
            if bsb_setDefault(bsb,20) == 20:
                bsb_size[bsb0] += 20
            bsb_size[bsb] += cellBlockSize
            bsb_size[bsb0] += cellBlockSize
        totalSize += 20 * len(bsb_size)
        return totalSize,bsb_size,bsbCellBlocks

    def dumpBlocks(self,out,bsbCellBlocks,bsb_size,blockGroupType,subBlockGroupType):
        """Dumps the cell blocks and their block and sub-block groups to out."""
        curBlock = None
        curSubblock = None
        stamp = self.stamp
        outWriteGroup = out.writeGroup
        for bsb,cellBlock in bsbCellBlocks:
            (block,subblock) = bsb
            bsb0 = (block,None)
            if block != curBlock:
                curBlock,curSubblock = bsb0
                outWriteGroup(bsb_size[bsb0],block,blockGroupType,stamp)
            if subblock != curSubblock:
                curSubblock = subblock
                outWriteGroup(bsb_size[bsb],subblock,subBlockGroupType,stamp)
            cellBlock.dump(out)

    def getNumRecords(self,includeGroups=1):
        """Returns number of records, including self and all children."""
        count = sum(x.getNumRecords(includeGroups) for x in self.cellBlocks)
        if count and includeGroups:
            count += 1 + len(self.getUsedBlocks()) + len(self.getUsedSubblocks())
        return count

    #--Fid manipulation, record filtering ----------------------------------
    def keepRecords(self,keepIds):
        """Keeps records with fid in set keepIds. Discards the rest."""
        #--Note: this call will add the cell to keepIds if any of its related records are kept.
        for cellBlock in self.cellBlocks: cellBlock.keepRecords(keepIds)
        self.cellBlocks = [x for x in self.cellBlocks if x.cell.fid in keepIds]
        self.id_cellBlock.clear()
        self.setChanged()

    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if converting to short format."""
        for cellBlock in self.cellBlocks:
            cellBlock.convertFids(mapper,toLong)

    def updateRecords(self,srcBlock,mapper,mergeIds):
        """Updates any records in 'self' that exist in 'srcBlock'."""
        if self.cellBlocks and not self.id_cellBlock:
            self.indexRecords()
        id_cellBlock = self.id_cellBlock
        id_Get = id_cellBlock.get
        for srcCellBlock in srcBlock.cellBlocks:
            fid = mapper(srcCellBlock.cell.fid)
            cellBlock = id_Get(fid)
            if cellBlock:
                cellBlock.updateRecords(srcCellBlock,mapper,mergeIds)

    def updateMasters(self,masters):
        """Updates set of master names according to masters actually used."""
        for cellBlock in self.cellBlocks:
            cellBlock.updateMasters(masters)

#-------------------------------------------------------------------------------
class MobICells(MobCells):
    """Tes4 top block for interior cell records."""

    def loadData(self,ins,endPos):
        """Loads data from input stream. Called by load()."""
        expType = self.label
        recCellClass = self.loadFactory.getRecClass(expType)
        errLabel = expType+' Top Block'
        cellBlocks = self.cellBlocks
        cell = None
        endBlockPos = endSubblockPos = 0
        unpackCellBlocks = self.loadFactory.getUnpackCellBlocks('CELL')
        insAtEnd = ins.atEnd
        insRecHeader = ins.unpackRecHeader
        cellBlocksAppend = cellBlocks.append
        selfLoadFactory = self.loadFactory
        insTell = ins.tell
        insSeek = ins.seek
        while not insAtEnd(endPos,errLabel):
            header = insRecHeader()
            recType = header[0]
            if recType == expType:
                if cell:
                    cellBlock = MobCell(header,selfLoadFactory,cell)
                    cellBlocksAppend(cellBlock)
                cell = recCellClass(header,ins,True)
                if insTell() > endBlockPos or insTell() > endSubblockPos:
                    raise ModError(self.inName,'Interior cell <%X> %s outside of block or subblock.' % (cell.fid, cell.eid))
            elif recType == 'GRUP':
                size,groupFid,groupType = header[1:4]
                if groupType == 2: # Block number
                    endBlockPos = insTell()+size+20
                elif groupType == 3: # Sub-block number
                    endSubblockPos = insTell()+size+20
                elif groupType == 6: # Cell Children
                    if cell:
                        if groupFid != cell.fid:
                            raise ModError(self.inName,'Cell subgroup (%X) does not match CELL <%X> %s.' %
                                (groupFid, cell.fid, cell.eid))
                        if unpackCellBlocks:
                            cellBlock = MobCell(header,selfLoadFactory,cell,ins,True)
                        else:
                            cellBlock = MobCell(header,selfLoadFactory,cell)
                            insSeek(header[1]-20,1)
                        cellBlocksAppend(cellBlock)
                        cell = None
                    else:
                        raise ModError(self.inName,'Extra subgroup %d in CELL group.' % groupType)
                else:
                    raise ModError(self.inName,'Unexpected subgroup %d in CELL group.' % groupType)
            else:
                raise ModError(self.inName,'Unexpected %s record in %s group.' % (recType,expType))
        self.setChanged()

    def dump(self,out):
        """Dumps group header and then records."""
        if not self.changed:
            out.writeGroup(*self.headers[1:])
            out.write(self.data)
        elif self.cellBlocks:
            (totalSize, bsb_size, blocks) = self.getBsbSizes()
            out.writeGroup(totalSize,self.label,self.groupType,self.stamp)
            self.dumpBlocks(out,blocks,bsb_size,2,3)

#-------------------------------------------------------------------------------
class MobWorld(MobCells):
    def __init__(self,header,loadFactory,world,ins=None,unpack=False):
        """Initialize."""
        self.world = world
        self.worldCellBlock = None
        self.road = None
        MobCells.__init__(self,header,loadFactory,ins,unpack)

    def loadData(self,ins,endPos):
        """Loads data from input stream. Called by load()."""
        cellType_class = self.loadFactory.getCellTypeClass()
        recCellClass = self.loadFactory.getRecClass('CELL')
        errLabel = 'World Block'
        cell = None
        block = None
        subblock = None
        cellBlocks = self.cellBlocks
        unpackCellBlocks = self.loadFactory.getUnpackCellBlocks('WRLD')
        insAtEnd = ins.atEnd
        insRecHeader = ins.unpackRecHeader
        cellGet = cellType_class.get
        insSeek = ins.seek
        insTell = ins.tell
        selfLoadFactory = self.loadFactory
        cellBlocksAppend = cellBlocks.append
        structUnpack = struct.unpack
        structPack = struct.pack
        while not insAtEnd(endPos,errLabel):
            #--Get record info and handle it
            header = insRecHeader()
            recType = header[0]
            recClass = cellGet(recType)
            if recType == 'ROAD':
                if not recClass: insSeek(header[1],1)
                else: self.road = recClass(header,ins,True)
            elif recType == 'CELL':
                if cell:
                    cellBlock = MobCell(header,selfLoadFactory,cell)
                    if block:
                        cellBlocksAppend(cellBlock)
                    else:
                        if self.worldCellBlock:
                            raise ModError(self.inName,'Extra exterior cell <%s> %s before block group.' % (hex(cell.fid), cell.eid))
                        self.worldCellBlock = cellBlock
                cell = recClass(header,ins,True)
                if block:
                    if insTell() > endBlockPos or insTell() > endSubblockPos:
                        raise ModError(self.inName,'Exterior cell <%s> %s after block or'
                                ' subblock.' % (hex(cell.fid), cell.eid))
            elif recType == 'GRUP':
                size,groupFid,groupType = header[1:4]
                if groupType == 4: # Exterior Cell Block
                    block = structUnpack('2h',structPack('I',groupFid))
                    block = (block[1],block[0])
                    endBlockPos = insTell() + size + 20
                elif groupType == 5: # Exterior Cell Sub-Block
                    subblock = structUnpack('2h',structPack('I',groupFid))
                    subblock = (subblock[1],subblock[0])
                    endSubblockPos = insTell() + size + 20
                elif groupType == 6: # Cell Children
                    if cell:
                        if groupFid != cell.fid:
                            raise ModError(self.inName,'Cell subgroup (%s) does not match CELL <%s> %s.' %
                                (hex(groupFid), hex(cell.fid), cell.eid))
                        if unpackCellBlocks:
                            cellBlock = MobCell(header,selfLoadFactory,cell,ins,True)
                        else:
                            cellBlock = MobCell(header,selfLoadFactory,cell)
                            insSeek(header[1]-20,1)
                        if block:
                            cellBlocksAppend(cellBlock)
                        else:
                            if self.worldCellBlock:
                                raise ModError(self.inName,'Extra exterior cell <%s> %s before block group.' % (hex(cell.fid), cell.eid))
                            self.worldCellBlock = cellBlock
                        cell = None
                    else:
                        raise ModError(self.inName,'Extra cell children subgroup in world children group.')
                else:
                    raise ModError(self.inName,'Unexpected subgroup %d in world children group.' % groupType)
            else:
                raise ModError(self.inName,'Unexpected %s record in world children group.' % recType)
        self.setChanged()

    def getNumRecords(self,includeGroups=True):
        """Returns number of records, including self and all children."""
        if not self.changed:
            return MobBase.getNumRecords(self)
        count = 1 + includeGroups #--world record & group
        count += bool(self.road)
        if self.worldCellBlock:
            count += self.worldCellBlock.getNumRecords(includeGroups)
        count += MobCells.getNumRecords(self,includeGroups)
        return count

    def dump(self,out):
        """Dumps group header and then records.  Returns the total size of the world block."""
        worldSize = self.world.getSize() + 20
        self.world.dump(out)
        if not self.changed:
            out.writeGroup(*self.headers[1:])
            out.write(self.data)
            return self.size + worldSize
        elif self.cellBlocks or self.road or self.worldCellBlock:
            (totalSize, bsb_size, blocks) = self.getBsbSizes()
            if self.road:
                totalSize += self.road.getSize() + 20
            if self.worldCellBlock:
                totalSize += self.worldCellBlock.getSize()
            out.writeGroup(totalSize,self.world.fid,1,self.stamp)
            if self.road:
                self.road.dump(out)
            if self.worldCellBlock:
                self.worldCellBlock.dump(out)
            self.dumpBlocks(out,blocks,bsb_size,4,5)
            return totalSize + worldSize
        else:
            return worldSize

    #--Fid manipulation, record filtering ----------------------------------
    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if converting to short format."""
        self.world.convertFids(mapper,toLong)
        if self.road:
            self.road.convertFids(mapper,toLong)
        if self.worldCellBlock:
            self.worldCellBlock.convertFids(mapper,toLong)
        MobCells.convertFids(self,mapper,toLong)

    def updateMasters(self,masters):
        """Updates set of master names according to masters actually used."""
        self.world.updateMasters(masters)
        if self.road:
            self.road.updateMasters(masters)
        if self.worldCellBlock:
            self.worldCellBlock.updateMasters(masters)
        MobCells.updateMasters(self,masters)

    def updateRecords(self,srcBlock,mapper,mergeIds):
        """Updates any records in 'self' that exist in 'srcBlock'."""
        selfGetter = self.__getattribute__
        srcGetter = srcBlock.__getattribute__
        selfSetter = self.__setattr__
        mergeDiscard = mergeIds.discard
        for attr in ('world','road'):
            myRecord = selfGetter(attr)
            record = srcGetter(attr)
            if myRecord and record:
                if myRecord.fid != mapper(record.fid):
                    raise ArgumentError("Fids don't match! %08x, %08x" % (myRecord.fid, record.fid))
                if not record.flags1.ignored:
                    record = record.getTypeCopy(mapper)
                    selfSetter(attr,record)
                    mergeDiscard(record.fid)
        if self.worldCellBlock and srcBlock.worldCellBlock:
            self.worldCellBlock.updateRecords(srcBlock.worldCellBlock,mapper,mergeIds)
        MobCells.updateRecords(self,srcBlock,mapper,mergeIds)

    def keepRecords(self,keepIds):
        """Keeps records with fid in set keepIds. Discards the rest."""
        if self.road and self.road.fid not in keepIds:
            self.road = None
        if self.worldCellBlock:
            self.worldCellBlock.keepRecords(keepIds)
            if self.worldCellBlock.cell.fid not in keepIds:
                self.worldCellBlock = None
        MobCells.keepRecords(self,keepIds)
        if self.road or self.worldCellBlock or self.cellBlocks:
            keepIds.add(self.world.fid)

#-------------------------------------------------------------------------------
class MobWorlds(MobBase):
    """Tes4 top block for world records and related roads and cells. Consists
    of world blocks."""

    def __init__(self,header,loadFactory,ins=None,unpack=False):
        """Initialize."""
        self.worldBlocks = []
        self.id_worldBlocks = {}
        self.orphansSkipped = 0
        MobBase.__init__(self,header,loadFactory,ins,unpack)

    def loadData(self,ins,endPos):
        """Loads data from input stream. Called by load()."""
        expType = self.label
        recWrldClass = self.loadFactory.getRecClass(expType)
        errLabel = expType + ' Top Block'
        worldBlocks = self.worldBlocks
        world = None
        insAtEnd = ins.atEnd
        insRecHeader = ins.unpackRecHeader
        insSeek = ins.seek
        selfLoadFactory = self.loadFactory
        worldBlocksAppend = worldBlocks.append
        while not insAtEnd(endPos,errLabel):
            #--Get record info and handle it
            header = insRecHeader()
            recType = header[0]
            if recType == expType:
                world = recWrldClass(header,ins,True)
            elif recType == 'GRUP':
                groupFid,groupType = header[2:4]
                if groupType != 1:
                    raise ModError(ins.inName,'Unexpected subgroup %d in CELL group.' % groupType)
                if not world:
                    #raise ModError(ins.inName,'Extra subgroup %d in WRLD group.' % groupType)
                    #--Orphaned world records. Skip over.
                    insSeek(header[1]-20,1)
                    self.orphansSkipped += 1
                    continue
                if groupFid != world.fid:
                    raise ModError(ins.inName,'WRLD subgroup (%s) does not match WRLD <%s> %s.' %
                        (hex(groupFid), hex(world.fid), world.eid))
                worldBlock = MobWorld(header,selfLoadFactory,world,ins,True)
                worldBlocksAppend(worldBlock)
                world = None
            else:
                raise ModError(ins.inName,'Unexpected %s record in %s group.' % (recType,expType))

    def getSize(self):
        """Returns size (incuding size of any group headers)."""
        return 20 + sum(x.getSize() for x in self.worldBlocks)

    def dump(self,out):
        """Dumps group header and then records."""
        if not self.changed:
            out.writeGroup(*self.headers[1:])
            out.write(self.data)
        else:
            if not self.worldBlocks: return
            worldHeaderPos = out.tell()
            out.writeGroup(0,self.label,0,self.stamp)
            totalSize = 20 + sum(x.dump(out) for x in self.worldBlocks)
            out.seek(worldHeaderPos + 4)
            out.pack('I', totalSize)
            out.seek(worldHeaderPos + totalSize)

    def getNumRecords(self,includeGroups=True):
        """Returns number of records, including self and all children."""
        count = sum(x.getNumRecords(includeGroups) for x in self.worldBlocks)
        return count + includeGroups*bool(count)

    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if converting to short format."""
        for worldBlock in self.worldBlocks:
            worldBlock.convertFids(mapper,toLong)

    def indexRecords(self):
        """Indexes records by fid."""
        self.id_worldBlocks = dict((x.world.fid,x) for x in self.worldBlocks)

    def updateMasters(self,masters):
        """Updates set of master names according to masters actually used."""
        for worldBlock in self.worldBlocks:
            worldBlock.updateMasters(masters)

    def updateRecords(self,srcBlock,mapper,mergeIds):
        """Updates any records in 'self' that exist in 'srcBlock'."""
        if self.worldBlocks and not self.id_worldBlocks:
            self.indexRecords()
        id_worldBlocks = self.id_worldBlocks
        idGet = id_worldBlocks.get
        for srcWorldBlock in srcBlock.worldBlocks:
            worldBlock = idGet(mapper(srcWorldBlock.world.fid))
            if worldBlock:
                worldBlock.updateRecords(srcWorldBlock,mapper,mergeIds)

    def setWorld(self,world):
        """Adds record to record list and indexed."""
        if self.worldBlocks and not self.id_worldBlocks:
            self.indexRecords()
        fid = world.fid
        if fid in self.id_worldBlocks:
            self.id_worldBlocks[fid].world = world
        else:
            worldBlock = MobWorld(('GRUP',0,0,1,self.stamp),self.loadFactory,world)
            worldBlock.setChanged()
            self.worldBlocks.append(worldBlock)
            self.id_worldBlocks[fid] = worldBlock

    def keepRecords(self,keepIds):
        """Keeps records with fid in set keepIds. Discards the rest."""
        for worldBlock in self.worldBlocks: worldBlock.keepRecords(keepIds)
        self.worldBlocks = [x for x in self.worldBlocks if x.world.fid in keepIds]
        self.id_worldBlocks.clear()
        self.setChanged()

#------------------------------------------------------------------------------
class ModFile:
    """TES4 file representation."""
    def __init__(self, fileInfo,loadFactory=None):
        """Initialize."""
        self.fileInfo = fileInfo
        self.loadFactory = loadFactory or LoadFactory(True)
        #--Variables to load
        self.tes4 = MreTes4(('TES4',0,0,0,0))
        self.tes4.setChanged()
        self.tops = {} #--Top groups.
        self.topsSkipped = set() #--Types skipped
        self.longFids = False
        #--Cached data
        self.mgef_school = None
        self.mgef_name = None

    def __getattr__(self,topType):
        """Returns top block of specified topType, creating it, if necessary."""
        if topType in self.tops:
            return self.tops[topType]
        elif topType in bush.topTypes:
            topClass = self.loadFactory.getTopClass(topType)
            self.tops[topType] = topClass(('GRUP',0,topType,0,0),self.loadFactory)
            self.tops[topType].setChanged()
            return self.tops[topType]
        elif topType == '__repr__':
            raise AttributeError
        else:
            raise ArgumentError(_('Invalid top group type: ')+topType)

    def load(self,unpack=False,progress=None):
        """Load file."""
        progress = progress or bolt.Progress()
        #--Header
        ins = ModReader(self.fileInfo.name,self.fileInfo.getPath().open('rb'))
        header = ins.unpackRecHeader()
        self.tes4 = MreTes4(header,ins,True)
        #--Raw data read
        insAtEnd = ins.atEnd
        insRecHeader = ins.unpackRecHeader
        selfGetTopClass = self.loadFactory.getTopClass
        selfTopsSkipAdd = self.topsSkipped.add
        insSeek = ins.seek
        selfLoadFactory = self.loadFactory
        while not insAtEnd():
            #--Get record info and handle it
            (type,size,label,groupType,stamp) = header = insRecHeader()
            if type != 'GRUP' or groupType != 0:
                raise ModError(self.fileInfo.name,_('Improperly grouped file.'))
            topClass = selfGetTopClass(label)
            if topClass:
                self.tops[label] = topClass(header,selfLoadFactory)
                self.tops[label].load(ins,unpack and (topClass != MobBase))
            else:
                selfTopsSkipAdd(label)
                insSeek(size-20,1,type + '.' + label)
        #--Done Reading
        ins.close()

    def load_unpack(self):
        """Unpacks blocks."""
        factoryTops = self.loadFactory.topTypes
        selfTops = self.tops
        for type in bush.topTypes:
            if type in selfTops and type in factoryTops:
                selfTops[type].load(None,True)

    def load_UI(self):
        """Convenience function. Loads, then unpacks, then indexes."""
        self.load()
        self.load_unpack()
        #self.load_index()

    def askSave(self,hasChanged=True):
        """CLI command. If hasSaved, will ask if user wants to save the file,
        and then save if the answer is yes. If hasSaved == False, then does nothing."""
        if not hasChanged: return
        fileName = self.fileInfo.name
        if re.match(r'\s*[yY]',raw_input('\nSave changes to '+fileName.s+' [y/n]?: ')):
            self.safeSave()
            print fileName.s,'saved.'
        else:
            print fileName.s,'not saved.'

    def safeSave(self):
        """Save data to file safely."""
        self.fileInfo.makeBackup()
        filePath = self.fileInfo.getPath()
        self.save(filePath.temp)
        filePath.untemp()
        self.fileInfo.setmtime()
        self.fileInfo.extras.clear()

    def save(self,outPath=None):
        """Save data to file.
        outPath -- Path of the output file to write to. Defaults to original file path."""
        if (not self.loadFactory.keepAll): raise StateError(_("Insufficient data to write file."))
        outPath = outPath or self.fileInfo.getPath()
        out = ModWriter(outPath.open('wb'))
        #--Mod Record
        self.tes4.setChanged()
        self.tes4.numRecords = sum(block.getNumRecords() for block in self.tops.values())
        self.tes4.getSize()
        self.tes4.dump(out)
        #--Blocks
        selfTops = self.tops
        for type in bush.topTypes:
            if type in selfTops:
                selfTops[type].dump(out)
        out.close()

    def getLongMapper(self):
        """Returns a mapping function to map short fids to long fids."""
        masters = self.tes4.masters+[self.fileInfo.name]
        maxMaster = len(masters)-1
        def mapper(fid):
            if fid == None: return None
            if isinstance(fid,tuple): return fid
            mod,object = int(fid >> 24),int(fid & 0xFFFFFFL)
            return (masters[min(mod,maxMaster)],object)
        return mapper

    def getShortMapper(self):
        """Returns a mapping function to map long fids to short fids."""
        masters = self.tes4.masters+[self.fileInfo.name]
        indices = dict([(name,index) for index,name in enumerate(masters)])
        def mapper(fid):
            if fid == None: return None
            modName,object = fid
            mod = indices[modName]
            return (long(mod) << 24 ) | long(object)
        return mapper

    def convertToLongFids(self,types=None):
        """Convert fids to long format (modname,objectindex)."""
        mapper = self.getLongMapper()
        if types == None: types = self.tops.keys()
        selfTops = self.tops
        for type in types:
            if type in selfTops:
                selfTops[type].convertFids(mapper,True)
        #--Done
        self.longFids = True

    def convertToShortFids(self):
        """Convert fids to short (numeric) format."""
        mapper = self.getShortMapper()
        selfTops = self.tops
        for type in selfTops:
            selfTops[type].convertFids(mapper,False)
        #--Done
        self.longFids = False

    def getMastersUsed(self):
        """Updates set of master names according to masters actually used."""
        if not self.longFids: raise StateError("ModFile fids not in long form.")
        masters = MasterSet([GPath('Oblivion.esm')]) #--Not so good for TCs. Fix later.
        for block in self.tops.values():
            block.updateMasters(masters)
        return masters.getOrdered()

    def getMgefSchool(self,refresh=False):
        """Return a dictionary mapping magic effect code to magic effect school.
        This is intended for use with the patch file when it records for all magic effects.
        If magic effects are not available, it will revert to busy.py version."""
        if self.mgef_school and not refresh:
            return self.mgef_school
        mgef_school = self.mgef_school = bush.mgef_school.copy()
        if 'MGEF' in self.tops:
            for record in self.MGEF.getActiveRecords():
                if isinstance(record,MreMgef):
                    mgef_school[record.eid] = record.school
        return mgef_school

    def getMgefName(self,refresh=False):
        """Return a dictionary mapping magic effect code to magic effect name.
        This is intended for use with the patch file when it records for all magic effects.
        If magic effects are not available, it will revert to busy.py version."""
        if self.mgef_name and not refresh:
            return self.mgef_name
        mgef_name = self.mgef_name = bush.mgef_name.copy()
        if 'MGEF' in self.tops:
            for record in self.MGEF.getActiveRecords():
                if isinstance(record,MreMgef):
                    mgef_name[record.eid] = record.full
        return mgef_name

# Save I/O --------------------------------------------------------------------
#------------------------------------------------------------------------------
class SaveFileError(FileError):
    """TES4 Save File Error: File is corrupted."""
    pass

class BSAFileError(FileError):
    """TES4 BSA File Error: File is corrupted."""
    pass
    
# Save Change Records ---------------------------------------------------------
class SreNPC(object):
    """NPC change record."""
    __slots__ = ('form','health','unused2','attributes','acbs','spells','factions','full','ai','skills','modifiers')
    flags = Flags(0L,Flags.getNames(
        (0,'form'),
        (2,'health'),
        (3,'attributes'),
        (4,'acbs'),
        (5,'spells'),
        (6,'factions'),
        (7,'full'),
        (8,'ai'),
        (9,'skills'),
        (28,'modifiers'),
        ))

    class ACBS(object):
        __slots__ = ['flags','baseSpell','fatigue','barterGold','level','calcMin','calcMax']

    def __init__(self,flags=0,data=None):
        """Initialize."""
        for attr in self.__slots__:
            self.__setattr__(attr,None)
        if data: self.load(flags,data)

    def getDefault(self,attr):
        """Returns a default version. Only supports acbs."""
        assert(attr == 'acbs')
        acbs = SreNPC.ACBS()
        (acbs.flags, acbs.baseSpell, acbs.fatigue, acbs.barterGold, acbs.level,
                acbs.calcMin, acbs.calcMax) = (0,0,0,0,1,0,0)
        acbs.flags = MreNpc._flags(acbs.flags)
        return acbs

    def load(self,flags,data):
        """Loads variables from data."""
        ins = cStringIO.StringIO(data)
        def unpack(format,size):
            return struct.unpack(format,ins.read(size))
        flags = SreNPC.flags(flags)
        if flags.form:
            self.form, = unpack('I',4)
        if flags.attributes:
            self.attributes = list(unpack('8B',8))
        if flags.acbs:
            acbs = self.acbs = SreNPC.ACBS()
            (acbs.flags, acbs.baseSpell, acbs.fatigue, acbs.barterGold, acbs.level,
                acbs.calcMin, acbs.calcMax) = unpack('=I3Hh2H',16)
            acbs.flags = MreNpc._flags(acbs.flags)
        if flags.factions:
            self.factions = []
            num, = unpack('H',2)
            for count in range(num):
                self.factions.append(unpack('=Ib',5))
        if flags.spells:
            num, = unpack('H',2)
            self.spells = list(unpack('%dI' % num,4*num))
        if flags.ai:
            self.ai = ins.read(4)
        if flags.health:
            self.health, self.unused2 = unpack('H2s',4)
        if flags.modifiers:
            num, = unpack('H',2)
            self.modifiers = []
            for count in range(num):
                self.modifiers.append(unpack('=Bf',5))
        if flags.full:
            size, = unpack('B',1)
            self.full = ins.read(size)
        if flags.skills:
            self.skills = list(unpack('21B',21))
        #--Done
        ins.close()

    def getFlags(self):
        """Returns current flags set."""
        flags = SreNPC.flags()
        for attr in SreNPC.__slots__:
            if attr != 'unused2': flags.__setattr__(attr,self.__getattribute__(attr) != None)
        return int(flags)

    def getData(self):
        """Returns self.data."""
        out = cStringIO.StringIO()
        def pack(format,*args):
            out.write(struct.pack(format,*args))
        #--Form
        if self.form != None:
            pack('I',self.form)
        #--Attributes
        if self.attributes != None:
            pack('8B',*self.attributes)
        #--Acbs
        if self.acbs != None:
            acbs = self.acbs
            pack('=I3Hh2H',int(acbs.flags), acbs.baseSpell, acbs.fatigue, acbs.barterGold, acbs.level,
                acbs.calcMin, acbs.calcMax)
        #--Factions
        if self.factions != None:
            pack('H',len(self.factions))
            for faction in self.factions:
                pack('=Ib',*faction)
        #--Spells
        if self.spells != None:
            num = len(self.spells)
            pack('H',num)
            pack('%dI' % num,*self.spells)
        #--AI Data
        if self.ai != None:
            out.write(self.ai)
        #--Health
        if self.health != None:
            pack('H2s',self.health,self.unused2)
        #--Modifiers
        if self.modifiers != None:
            pack('H',len(self.modifiers))
            for modifier in self.modifiers:
                pack('=Bf',*modifier)
        #--Full
        if self.full != None:
            pack('B',len(self.full))
            out.write(self.full)
        #--Skills
        if self.skills != None:
            pack('21B',*self.skills)
        #--Done
        return out.getvalue()

    def getTuple(self,fid,version):
        """Returns record as a change record tuple."""
        return (fid,35,self.getFlags(),version,self.getData())

    def dumpText(self,saveFile):
        """Returns informal string representation of data."""
        buff = cStringIO.StringIO()
        fids = saveFile.fids
        if self.form != None:
            buff.write('Form:\n  %d' % self.form)
        if self.attributes != None:
            buff.write('Attributes\n  strength %3d\n  intelligence %3d\n  willpower %3d\n  agility %3d\n  speed %3d\n  endurance %3d\n  personality %3d\n  luck %3d\n' % tuple(self.attributes))
        if self.acbs != None:
            buff.write('ACBS:\n')
            for attr in SreNPC.ACBS.__slots__:
                buff.write('  '+attr+' '+`getattr(self.acbs,attr)`+'\n')
        if self.factions != None:
            buff.write('Factions:\n')
            for faction in self.factions:
                buff.write('  %8X %2X\n' % (fids[faction[0]],faction[1]))
        if self.spells != None:
            buff.write('Spells:\n')
            for spell in self.spells:
                buff.write('  %8X\n' % fids[spell])
        if self.ai != None:
            buff.write('AI:\n  ' + self.ai + '\n')
        if self.health != None:
            buff.write('Health\n  '+`self.health`+'\n')
            buff.write('Unused2\n  '+`self.unused2`+'\n')
        if self.modifiers != None:
            buff.write('Modifiers:\n')
            for modifier in self.modifiers:
                buff.write('  %s\n' % `modifier`)
        if self.full != None:
            buff.write('Full:\n  '+`self.full`+'\n')
        if self.skills != None:
            buff.write('Skills:\n  armorer %3d\n  athletics %3d\n  blade %3d\n  block %3d\n  blunt %3d\n  handToHand %3d\n  heavyArmor %3d\n  alchemy %3d\n  alteration %3d\n  conjuration %3d\n  destruction %3d\n  illusion %3d\n  mysticism %3d\n  restoration %3d\n  acrobatics %3d\n  lightArmor %3d\n  marksman %3d\n  mercantile %3d\n  security %3d\n  sneak %3d\n  speechcraft  %3d\n' % tuple(self.skills))
        return buff.getvalue()

# Save File -------------------------------------------------------------------
#------------------------------------------------------------------------------
class PluggyFile:
    """Represents a .pluggy cofile for saves. Used for editing masters list."""
    def __init__(self,path):
        self.path = path
        self.name = path.tail
        self.tag = None
        self.version = None
        self.plugins = None
        self.other = None
        self.valid = False

    def mapMasters(self,masterMap):
        """Update plugin names according to masterMap."""
        if not self.valid: raise FileError(self.name,"File not initialized.")
        self.plugins = [(x,y,masterMap.get(z,z)) for x,y,z in self.plugins]

    def load(self):
        """Read file."""
        import binascii
        size = self.path.size
        ins = self.path.open('rb')
        buff = ins.read(size-4)
        crc32, = struct.unpack('=i',ins.read(4))
        ins.close()
        crcNew = binascii.crc32(buff)
        if crc32 != crcNew:
            raise FileError(self.name,'CRC32 file check failed. File: %X, Calc: %X' % (crc32,crcNew))
        #--Header
        ins = cStringIO.StringIO(buff)
        def unpack(format,size):
            return struct.unpack(format,ins.read(size))
        if ins.read(10) != 'PluggySave':
            raise FileError(self.name,'File tag != "PluggySave"')
        self.version, = unpack('I',4)
        #--Reject versions earlier than 1.02
        if self.version < 0x01020000:
            raise FileError(self.name,'Unsupported file verson: %I' % self.version)
        #--Plugins
        self.plugins = []
        type, = unpack('=B',1)
        if type != 0:
            raise FileError(self.name,'Expected plugins record, but got %d.' % type)
        count, = unpack('=I',4)
        for x in range(count):
            espid,index,modLen = unpack('=2BI',6)
            modName = GPath(ins.read(modLen))
            self.plugins.append((espid,index,modName))
        #--Other
        self.other = ins.getvalue()[ins.tell():]
        deprint(struct.unpack('I',self.other[-4:]),self.path.size-8)
        #--Done
        ins.close()
        self.valid = True

    def save(self,path=None,mtime=0):
        """Saves."""
        import binascii
        if not self.valid: raise FileError(self.name,"File not initialized.")
        #--Buffer
        buff = cStringIO.StringIO()
        #--Save
        def pack(format,*args):
            buff.write(struct.pack(format,*args))
        buff.write('PluggySave')
        pack('=I',self.version)
        #--Plugins
        pack('=B',0)
        pack('=I',len(self.plugins))
        for (espid,index,modName) in self.plugins:
            pack('=2BI',espid,index,len(modName))
            buff.write(modName.s.lower())
        #--Other
        buff.write(self.other)
        #--End control
        buff.seek(-4,1)
        pack('=I',buff.tell())
        #--Save
        path = path or self.path
        mtime = mtime or path.exists() and path.mtime
        text = buff.getvalue()
        out = path.open('wb')
        out.write(text)
        out.write(struct.pack('i',binascii.crc32(text)))
        out.close()
        path.mtime = mtime

    def safeSave(self):
        """Save data to file safely."""
        self.save(self.path.temp,self.path.mtime)
        self.path.untemp()

#------------------------------------------------------------------------------
class ObseFile:
    """Represents a .obse cofile for saves. Used for editing masters list."""
    def __init__(self,path):
        self.path = path
        self.name = path.tail
        self.signature = None
        self.formatVersion = None
        self.obseVersion = None
        self.obseMinorVersion = None
        self.oblivionVersion = None
        self.plugins = None
        self.valid = False

    def load(self):
        """Read file."""
        import binascii
        size = self.path.size
        ins = self.path.open('rb')
        buff = ins.read(size)
        ins.close()
        #--Header
        ins = cStringIO.StringIO(buff)
        def unpack(format,size):
            return struct.unpack(format,ins.read(size))
        self.signature = ins.read(4)
        if self.signature != 'OBSE':
            raise FileError(self.name,'File signature != "OBSE"')
        self.formatVersion,self.obseVersion,self.obseMinorVersion,self.oblivionVersion, = unpack('IHHI',12)
        # if self.formatVersion < X:
        #   raise FileError(self.name,'Unsupported file version: %I' % self.formatVersion)
        #--Plugins
        numPlugins, = unpack('I',4)
        self.plugins = []
        for x in range(numPlugins):
            opcodeBase,numChunks,pluginLength, = unpack('III',12)
            pluginBuff = ins.read(pluginLength)
            pluginIns = cStringIO.StringIO(pluginBuff)
            chunks = []            
            for y in range(numChunks):
                chunkType = pluginIns.read(4)
                chunkVersion,chunkLength, = struct.unpack('II',pluginIns.read(8))
                chunkBuff = pluginIns.read(chunkLength)
                chunk = (chunkType, chunkVersion, chunkBuff)
                chunks.append(chunk)
            pluginIns.close()
            plugin = (opcodeBase,chunks)
            self.plugins.append(plugin)
        #--Done
        ins.close()
        self.valid = True

    def save(self,path=None,mtime=0):
        """Saves."""
        if not self.valid: raise FileError(self.name,"File not initialized.")
        #--Buffer
        buff = cStringIO.StringIO()
        #--Save
        def pack(format,*args):
            buff.write(struct.pack(format,*args))
        buff.write('OBSE')
        pack('=I',self.formatVersion)
        pack('=H',self.obseVersion)
        pack('=H',self.obseMinorVersion)
        pack('=I',self.oblivionVersion)
        #--Plugins
        pack('=I',len(self.plugins))
        for (opcodeBase,chunks) in self.plugins:
            pack('=I',opcodeBase)
            pack('=I',len(chunks))
            pluginLength = 0
            pluginLengthPos = buff.tell()
            pack('=I',0)
            for (chunkType,chunkVersion,chunkBuff) in chunks:
                buff.write(chunkType)
                pack('=2I',chunkVersion,len(chunkBuff))
                buff.write(chunkBuff)
                pluginLength += 12 + len(chunkBuff)
            buff.seek(pluginLengthPos,0)
            pack('=I',pluginLength)
            buff.seek(0,2)
        #--Save
        path = path or self.path
        mtime = mtime or path.exists() and path.mtime
        text = buff.getvalue()
        out = path.open('wb')
        out.write(text)
        out.close()
        path.mtime = mtime

    def mapMasters(self,masterMap):
        """Update plugin names according to masterMap."""
        if not self.valid: raise FileError(self.name,"File not initialized.")
        newPlugins = []
        for (opcodeBase,chunks) in self.plugins:
            newChunks = []
            if (opcodeBase == 0x2330):
                for (chunkType,chunkVersion,chunkBuff) in chunks:
                    chunkTypeNum, = struct.unpack('=I',chunkType)
                    if (chunkTypeNum == 1):
                        ins = cStringIO.StringIO(chunkBuff)
                        def unpack(format,size):
                            return struct.unpack(format,ins.read(size))
                        buff = cStringIO.StringIO()
                        def pack(format,*args):
                            buff.write(struct.pack(format,*args))
                        while (ins.tell() < len(chunkBuff)):
                            espId,modId,modNameLen, = unpack('=BBI',6)
                            modName = GPath(ins.read(modNameLen))
                            modName = masterMap.get(modName,modName)
                            pack('=BBI',espId,modId,len(modName.s))
                            buff.write(modName.s.lower())
                        ins.close()
                        chunkBuff = buff.getvalue()
                        buff.close()
                    newChunks.append((chunkType,chunkVersion,chunkBuff))
            else:
                newChunks = chunks
            newPlugins.append((opcodeBase,newChunks))
        self.plugins = newPlugins

    def safeSave(self):
        """Save data to file safely."""
        self.save(self.path.temp,self.path.mtime)
        self.path.untemp()
        
#------------------------------------------------------------------------------
class SaveHeader:
    """Represents selected info from a Tes4SaveGame file."""
    def __init__(self,path=None):
        """Initialize."""
        self.pcName = None
        self.pcLocation = None
        self.gameDays = 0
        self.gameTicks = 0
        self.pcLevel = 0
        self.masters = []
        self.image = None
        if path: self.load(path)

    def load(self,path):
        """Extract info from save file."""
        ins = path.open('rb')
        try:
            #--Header
            ins.seek(34)
            headerSize, = struct.unpack('I',ins.read(4))
            #posMasters = 38 + headerSize
            #--Name, location
            ins.seek(38+4)
            size, = struct.unpack('B',ins.read(1))
            self.pcName = cstrip(ins.read(size))
            self.pcLevel, = struct.unpack('H',ins.read(2))
            size, = struct.unpack('B',ins.read(1))
            self.pcLocation = cstrip(ins.read(size))
            #--Image Data
            self.gameDays,self.gameTicks,self.gameTime,ssSize,ssWidth,ssHeight = struct.unpack('=fI16s3I',ins.read(36))
            ssData = ins.read(3*ssWidth*ssHeight)
            self.image = (ssWidth,ssHeight,ssData)
            #--Masters
            #ins.seek(posMasters)
            del self.masters[:]
            numMasters, = struct.unpack('B',ins.read(1))
            for count in range(numMasters):
                size, = struct.unpack('B',ins.read(1))
                self.masters.append(GPath(ins.read(size)))
        #--Errors
        except:
            raise SaveFileError(path.tail,_('File header is corrupted..'))
        #--Done
        ins.close()

    def writeMasters(self,path):
        """Rewrites masters of existing save file."""
        if not path.exists():
            raise SaveFileError(path.head,_('File does not exist.'))
        ins = path.open('rb')
        out = path.temp.open('wb')
        def unpack(format,size):
            return struct.unpack(format,ins.read(size))
        def pack(format,*args):
            out.write(struct.pack(format,*args))
        #--Header
        out.write(ins.read(34))
        #--SaveGameHeader
        size, = unpack('I',4)
        pack('I',size)
        out.write(ins.read(size))
        #--Skip old masters
        numMasters, = unpack('B',1)
        oldMasters = []
        for count in range(numMasters):
            size, = unpack('B',1)
            oldMasters.append(GPath(ins.read(size)))
        #--Write new masters
        pack('B',len(self.masters))
        for master in self.masters:
            pack('B',len(master))
            out.write(master.s)
        #--Fids Address
        offset = out.tell() - ins.tell()
        fidsAddress, = unpack('I',4)
        pack('I',fidsAddress+offset)
        #--Copy remainder
        while True:
            buffer= ins.read(0x5000000)
            if not buffer: break
            out.write(buffer)
        #--Cleanup
        ins.close()
        out.close()
        path.untemp()
        #--Cosaves
        masterMap = dict((x,y) for x,y in zip(oldMasters,self.masters) if x != y)
        #--Pluggy File?
        pluggyPath = CoSaves.getPaths(path)[0]
        if masterMap and pluggyPath.exists():
            pluggy = PluggyFile(pluggyPath)
            pluggy.load()
            pluggy.mapMasters(masterMap)
            pluggy.safeSave()
        #--OBSE File?
        obsePath = CoSaves.getPaths(path)[1]
        if masterMap and obsePath.exists():
            obse = ObseFile(obsePath)
            obse.load()
            obse.mapMasters(masterMap)
            obse.safeSave()

#------------------------------------------------------------------------------
class BSAHeader:
    """Represents selected info from a Tes4BSA file."""
    def __init__(self,path=None):
        """Initialize."""
        self.folderCount = 0
        self.fileCount = 0
        self.lenFolderNames = 0
        self.lenFileNames = 0
        self.fileFlags = 0
        if path: self.load(path)

    def load(self,path):
        """Extract info from save file."""
        ins = path.open('rb')
        try:
            #--Header
            ins.seek(4*4)
            (self.folderCount,self.fileCount,lenFolderNames,lenFileNames,fileFlags) = ins.unpack('5I',20)
        #--Errors
        except:
            raise BSAFileError(path.tail,_('File header is corrupted..'))
        #--Done
        ins.close()

#------------------------------------------------------------------------------
class SaveFile:
    """Represents a Tes4 Save file."""
    recordFlags = Flags(0L,Flags.getNames(
        'form','baseid','moved','havocMoved','scale','allExtra','lock','owner','unk8','unk9',
        'mapMarkerFlags','hadHavokMoveFlag','unk12','unk13','unk14','unk15',
        'emptyFlag','droppedItem','doorDefaultState','doorState','teleport',
        'extraMagic','furnMarkers','oblivionFlag','movementExtra','animation',
        'script','inventory','created','unk29','enabled'))

    def __init__(self,saveInfo=None,canSave=True):
        """Initialize."""
        self.fileInfo = saveInfo
        self.canSave = canSave
        #--File Header, Save Game Header
        self.header = None
        self.gameHeader = None
        self.pcName = None
        #--Masters
        self.masters = []
        #--Global
        self.globals = []
        self.created = []
        self.fid_createdNum = None
        self.preGlobals = None #--Pre-records, pre-globals
        self.preCreated = None #--Pre-records, pre-created
        self.preRecords = None #--Pre-records, pre
        #--Records, temp effects, fids, worldspaces
        self.records = [] #--(fid,recType,flags,version,data)
        self.fid_recNum = None
        self.tempEffects = None
        self.fids = None
        self.irefs = {}  #--iref = self.irefs[fid]
        self.worldSpaces = None

    def load(self,progress=None):
        """Extract info from save file."""
        import array
        path = self.fileInfo.getPath()
        ins = bolt.StructFile(path.s,'rb')
        #--Progress
        fileName = self.fileInfo.name
        progress = progress or bolt.Progress()
        progress.setFull(self.fileInfo.size)
        #--Header
        progress(0,_('Reading Header.'))
        self.header = ins.read(34)

        #--Save Header, pcName
        gameHeaderSize, = ins.unpack('I',4)
        self.saveNum,pcNameSize, = ins.unpack('=IB',5)
        self.pcName = cstrip(ins.read(pcNameSize))
        self.postNameHeader = ins.read(gameHeaderSize-5-pcNameSize)

        #--Masters
        del self.masters[:]
        numMasters, = ins.unpack('B',1)
        for count in range(numMasters):
            size, = ins.unpack('B',1)
            self.masters.append(GPath(ins.read(size)))

        #--Pre-Records copy buffer
        def insCopy(buff,size,backSize=0):
            if backSize: ins.seek(-backSize,1)
            buff.write(ins.read(size+backSize))

        #--"Globals" block
        fidsPointer,recordsNum = ins.unpack('2I',8)
        #--Pre-globals
        self.preGlobals = ins.read(8*4)
        #--Globals
        globalsNum, = ins.unpack('H',2)
        self.globals = [ins.unpack('If',8) for num in xrange(globalsNum)]
        #--Pre-Created (Class, processes, spectator, sky)
        buff = cStringIO.StringIO()
        for count in range(4):
            size, = ins.unpack('H',2)
            insCopy(buff,size,2)
        insCopy(buff,4) #--Supposedly part of created info, but sticking it here since I don't decode it.
        self.preCreated = buff.getvalue()
        #--Created (ALCH,SPEL,ENCH,WEAP,CLOTH,ARMO, etc.?)
        modReader = ModReader(self.fileInfo.name,ins)
        createdNum, = ins.unpack('I',4)
        for count in xrange(createdNum):
            progress(ins.tell(),_('Reading created...'))
            header = ins.unpack('4s4I',20)
            self.created.append(MreRecord(header,modReader))
        #--Pre-records: Quickkeys, reticule, interface, regions
        buff = cStringIO.StringIO()
        for count in range(4):
            size, = ins.unpack('H',2)
            insCopy(buff,size,2)
        self.preRecords = buff.getvalue()

        #--Records
        for count in xrange(recordsNum):
            progress(ins.tell(),_('Reading records...'))
            (fid,recType,flags,version,size) = ins.unpack('=IBIBH',12)
            data = ins.read(size)
            self.records.append((fid,recType,flags,version,data))

        #--Temp Effects, fids, worldids
        progress(ins.tell(),_('Reading fids, worldids...'))
        size, = ins.unpack('I',4)
        self.tempEffects = ins.read(size)
        #--Fids
        num, = ins.unpack('I',4)
        self.fids = array.array('I')
        self.fids.fromfile(ins,num)
        for iref,fid in enumerate(self.fids):
            self.irefs[fid] = iref

        #--WorldSpaces
        num, = ins.unpack('I',4)
        self.worldSpaces = array.array('I')
        self.worldSpaces.fromfile(ins,num)
        #--Done
        ins.close()
        progress(progress.full,_('Finished reading.'))

    def save(self,outPath=None,progress=None):
        """Save data to file.
        outPath -- Path of the output file to write to. Defaults to original file path."""
        if (not self.canSave): raise StateError(_("Insufficient data to write file."))
        outPath = outPath or self.fileInfo.getPath()
        out = outPath.open('wb')
        def pack(format,*data):
            out.write(struct.pack(format,*data))
        #--Progress
        fileName = self.fileInfo.name
        progress = progress or bolt.Progress()
        progress.setFull(self.fileInfo.size)
        #--Header
        progress(0,_('Writing Header.'))
        out.write(self.header)
        #--Save Header
        pack('=IIB',5+len(self.pcName)+1+len(self.postNameHeader),
            self.saveNum, len(self.pcName)+1)
        out.write(self.pcName+'\x00')
        out.write(self.postNameHeader)
        #--Masters
        pack('B',len(self.masters))
        for master in self.masters:
            pack('B',len(master))
            out.write(master.s)
        #--Fids Pointer, num records
        fidsPointerPos = out.tell()
        pack('I',0) #--Temp. Will write real value later.
        pack('I',len(self.records))
        #--Pre-Globals
        out.write(self.preGlobals)
        #--Globals
        pack('H',len(self.globals))
        for iref,value in self.globals:
            pack('If',iref,value)
        #--Pre-Created
        out.write(self.preCreated)
        #--Created
        progress(0.1,_('Writing created.'))
        modWriter = ModWriter(out)
        pack('I',len(self.created))
        for record in self.created:
            record.dump(modWriter)
        #--Pre-records
        out.write(self.preRecords)
        #--Records, temp effects, fids, worldspaces
        progress(0.2,_('Writing records.'))
        for fid,recType,flags,version,data in self.records:
            pack('=IBIBH',fid,recType,flags,version,len(data))
            out.write(data)
        #--Temp Effects, fids, worldids
        pack('I',len(self.tempEffects))
        out.write(self.tempEffects)
        #--Fids
        progress(0.9,_('Writing fids, worldids.'))
        fidsPos = out.tell()
        out.seek(fidsPointerPos)
        pack('I',fidsPos)
        out.seek(fidsPos)
        pack('I',len(self.fids))
        self.fids.tofile(out)
        #--Worldspaces
        pack('I',len(self.worldSpaces))
        self.worldSpaces.tofile(out)
        #--Done
        progress(1.0,_('Writing complete.'))
        out.close()

    def safeSave(self,progress=None):
        """Save data to file safely."""
        self.fileInfo.makeBackup()
        filePath = self.fileInfo.getPath()
        self.save(filePath.temp,progress)
        filePath.untemp()
        self.fileInfo.setmtime()

    def addMaster(self,master):
        """Adds master to masters list."""
        if master not in self.masters:
            self.masters.append(master)

    def indexCreated(self):
        """Fills out self.fid_recNum."""
        self.fid_createdNum = dict((x.fid,i) for i,x in enumerate(self.created))

    def removeCreated(self,fid):
        """Removes created if it exists. Returns True if record existed, false if not."""
        if self.fid_createdNum == None: self.indexCreated()
        recNum = self.fid_createdNum.get(fid)
        if recNum == None:
            return False
        else:
            del self.created[recNum]
            del self.fid_createdNum[fid]
            return True

    def indexRecords(self):
        """Fills out self.fid_recNum."""
        self.fid_recNum = dict((entry[0],index) for index,entry in enumerate(self.records))

    def getRecord(self,fid,default=None):
        """Returns recNum and record with corresponding fid."""
        if self.fid_recNum == None: self.indexRecords()
        recNum = self.fid_recNum.get(fid)
        if recNum == None:
            return default
        else:
            return self.records[recNum]

    def setRecord(self,record):
        """Sets records where record = (fid,recType,flags,version,data)."""
        if self.fid_recNum == None: self.indexRecords()
        fid = record[0]
        recNum = self.fid_recNum.get(fid,-1)
        if recNum == -1:
            self.records.append(record)
            self.fid_recNum[fid] = len(self.records)-1
        else:
            self.records[recNum] = record

    def removeRecord(self,fid):
        """Removes record if it exists. Returns True if record existed, false if not."""
        if self.fid_recNum == None: self.indexRecords()
        recNum = self.fid_recNum.get(fid)
        if recNum == None:
            return False
        else:
            del self.records[recNum]
            del self.fid_recNum[fid]
            return True

    def getShortMapper(self):
        """Returns a mapping function to map long fids to short fids."""
        indices = dict([(name,index) for index,name in enumerate(self.masters)])
        def mapper(fid):
            if fid == None: return None
            modName,object = fid
            mod = indices[modName]
            return (long(mod) << 24 ) | long(object)
        return mapper

    def getFid(self,iref,default=None):
        """Returns fid corresponding to iref."""
        if not iref: return default
        if iref >> 24 == 0xFF: return iref
        if iref >= len(self.fids): raise 'IRef from Mars.'
        return self.fids[iref]

    def getIref(self,fid):
        """Returns iref corresponding to fid, creating it if necessary."""
        iref = self.irefs.get(fid,-1)
        if iref < 0:
            self.fids.append(fid)
            iref = self.irefs[fid] = len(self.fids) - 1
        return iref

    #--------------------------------------------------------------------------
    def logStats(self,log=None):
        """Print stats to log."""
        log = log or bolt.Log()
        doLostChanges = False
        doUnknownTypes = False
        def getMaster(modIndex):
            if modIndex < len(self.masters):
                return self.masters[modIndex].s
            elif modIndex == 0xFF:
                return self.fileInfo.name.s
            else:
                return _('Missing Master ')+hex(modIndex)
        #--ABomb
        (tesClassSize,abombCounter,abombFloat) = self.getAbomb()
        log.setHeader(_('Abomb Counter'))
        log(_('  Integer:\t0x%08X') % abombCounter)
        log(_('  Float:\t%.2f') % abombFloat)
        #--FBomb
        log.setHeader(_('Fbomb Counter'))
        log(_('  Next in-game object: %08X') % struct.unpack('I',self.preGlobals[:4]))
        #--Array Sizes
        log.setHeader('Array Sizes')
        log('  %d\t%s' % (len(self.created),_('Created Items')))
        log('  %d\t%s' % (len(self.records),_('Records')))
        log('  %d\t%s' % (len(self.fids),_('Fids')))
        #--Created Types
        log.setHeader(_('Created Items'))
        createdHisto = {}
        id_created = {}
        for citem in self.created:
            count,size = createdHisto.get(citem.recType,(0,0))
            createdHisto[citem.recType] =  (count + 1,size + citem.size)
            id_created[citem.fid] = citem
        for type in sorted(createdHisto.keys()):
            count,size = createdHisto[type]
            log('  %d\t%d kb\t%s' % (count,size/1024,type))
        #--Fids
        lostRefs = 0
        idHist = [0]*256
        for fid in self.fids:
            if fid == 0:
                lostRefs += 1
            else:
                idHist[fid >> 24] += 1
        #--Change Records
        changeHisto = [0]*256
        modHisto = [0]*256
        typeModHisto = {}
        knownTypes = set(bush.saveRecTypes.keys())
        lostChanges = {}
        objRefBases = {}
        objRefNullBases = 0
        fids = self.fids
        for record in self.records:
            fid,type,flags,version,data = record
            if fid ==0xFEFFFFFF: continue #--Ignore intentional(?) extra fid added by patch.
            mod = fid >> 24
            if type not in typeModHisto:
                typeModHisto[type] = modHisto[:]
            typeModHisto[type][mod] += 1
            changeHisto[mod] += 1
            #--Lost Change?
            if doLostChanges and mod == 255 and not (48 <= type <= 51) and fid not in id_created:
                lostChanges[fid] = record
            #--Unknown type?
            if doUnknownTypes and type not in knownTypes:
                if mod < 255:
                    print type,hex(fid),getMaster(mod)
                    knownTypes.add(type)
                elif fid in id_created:
                    print type,hex(fid),id_created[fid].recType
                    knownTypes.add(type)
            #--Obj ref parents
            if type == 49 and mod == 255 and (flags & 2):
                iref, = struct.unpack('I',data[4:8])
                count,cumSize = objRefBases.get(iref,(0,0))
                count += 1
                cumSize += len(data) + 12
                objRefBases[iref] = (count,cumSize)
                if iref >> 24 != 255 and fids[iref] == 0:
                    objRefNullBases += 1
        saveRecTypes = bush.saveRecTypes
        #--Fids log
        log.setHeader(_('Fids'))
        log('  Refed\tChanged\tMI    Mod Name')
        log('  %d\t\t     Lost Refs (Fid == 0)' % (lostRefs))
        for modIndex,(irefed,changed) in enumerate(zip(idHist,changeHisto)):
            if irefed or changed:
                log('  %d\t%d\t%-3d   %s' % (irefed,changed,modIndex,getMaster(modIndex)))
        #--Lost Changes
        if lostChanges:
            log.setHeader(_('LostChanges'))
            for id in sorted(lostChanges.keys()):
                type = lostChanges[id][1]
                log(hex(id)+saveRecTypes.get(type,`type`))
        for type in sorted(typeModHisto.keys()):
            modHisto = typeModHisto[type]
            log.setHeader('%d %s' % (type,saveRecTypes.get(type,_('Unknown')),))
            for modIndex,count in enumerate(modHisto):
                if count: log('  %d\t%s' % (count,getMaster(modIndex)))
            log('  %d\tTotal' % (sum(modHisto),))
        objRefBases = dict((key,value) for key,value in objRefBases.iteritems() if value[0] > 100)
        log.setHeader(_('New ObjectRef Bases'))
        if objRefNullBases:
            log(' Null Bases: '+`objRefNullBases`)
        if objRefBases:
            log(_(' Count IRef     BaseId'))
            for iref in sorted(objRefBases.keys()):
                count,cumSize = objRefBases[iref]
                if iref >> 24 == 255:
                    parentid = iref
                else:
                    parentid = self.fids[iref]
                log('%6d %08X %08X %6d kb' % (count,iref,parentid,cumSize/1024))
    def logStatObse(self,log=None):
        """Print stats to log."""
        log = log or bolt.Log()
        obseFileName = self.fileInfo.getPath().root+'.obse'
        obseFile = ObseFile(obseFileName)
        obseFile.load()
        #--Header
        log.setHeader(_('Header'))
        log('=' * 80)
        log(_('  Format version:   %08X') % (obseFile.formatVersion,))
        log(_('  OBSE version:     %u.%u') % (obseFile.obseVersion,obseFile.obseMinorVersion,))
        log(_('  Oblivion version: %08X') % (obseFile.oblivionVersion,))
        #--Plugins
        if obseFile.plugins != None:
            for (opcodeBase,chunks) in obseFile.plugins:
                log.setHeader(_('Plugin opcode=%08X chunkNum=%u') % (opcodeBase,len(chunks),))
                log('=' * 80)
                log(_('  Type  Ver   Size'))
                log('-' * 80)
                espMap = {}
                for (chunkType,chunkVersion,chunkBuff) in chunks:
                    chunkTypeNum, = struct.unpack('=I',chunkType)
                    if (chunkType[0] >= ' ' and chunkType[3] >= ' '):
                        log(_('  %4s  %-4u  %08X') % (chunkType,chunkVersion,len(chunkBuff)))
                    else:
                        log(_('  %04X  %-4u  %08X') % (chunkTypeNum,chunkVersion,len(chunkBuff)))
                    ins = cStringIO.StringIO(chunkBuff)
                    def unpack(format,size):
                        return struct.unpack(format,ins.read(size))
                    if (opcodeBase == 0x1400):  # OBSE
                        if chunkType == 'RVTS':
                            #--OBSE String
                            modIndex,stringID,stringLength, = unpack('=BIH',7)
                            stringData = ins.read(stringLength)
                            log(_('    Mod :  %02X (%s)') % (modIndex, self.masters[modIndex].s))
                            log(_('    ID  :  %u') % stringID)
                            log(_('    Data:  %s') % stringData)
                        elif chunkType == 'RVRA':
                            #--OBSE Array                        
                            modIndex,arrayID,keyType,isPacked, = unpack('=BIBB',7)
                            if modIndex == 255:
                                log(_('    Mod :  %02X (Save File)') % (modIndex))
                            else:
                                log(_('    Mod :  %02X (%s)') % (modIndex, self.masters[modIndex].s))
                            log(_('    ID  :  %u') % arrayID)
                            if keyType == 1: #Numeric
                                if isPacked:
                                    log(_('    Type:  Array'))
                                else:
                                    log(_('    Type:  Map'))
                            elif keyType == 3:
                                log(_('    Type:  StringMap'))
                            else:
                                log(_('    Type:  Unknown'))
                            if chunkVersion >= 1:
                                numRefs, = unpack('=I',4)
                                if numRefs > 0:
                                    log('    Refs:')
                                    for x in range(numRefs):
                                        refModID, = unpack('=B',1)
                                        if refModID == 255:
                                            log(_('      %02X (Save File)') % (refModID))
                                        else:
                                            log(_('      %02X (%s)') % (refModID, self.masters[refModID].s))
                            numElements, = unpack('=I',4)
                            log(_('    Size:  %u') % numElements)
                            for i in range(numElements):
                                if keyType == 1:
                                    key, = unpack('=d',8)
                                    keyStr = '%d' % key
                                elif keyType == 3:
                                    keyLen, = unpack('=H',2)
                                    key = ins.read(keyLen)
                                    keyStr = key
                                else:
                                    keyStr = 'BAD'
                                dataType, = unpack('=B',1)
                                if dataType == 1:
                                    data, = unpack('=d',8)
                                    dataStr = '%d' % data
                                elif dataType == 2:
                                    data, = unpack('=I',4)
                                    dataStr = '%08X' % data
                                elif dataType == 3:
                                    dataLen, = unpack('=H',2)
                                    data = ins.read(dataLen)
                                    dataStr = data
                                elif dataType == 4:
                                    data, = unpack('=I',4)
                                    dataStr = '%u' % data
                                log(_('    [%s]:%s = %s') % (keyStr,('BAD','NUM','REF','STR','ARR')[dataType],dataStr))
                    elif (opcodeBase == 0x2330):    # Pluggy
                        if (chunkTypeNum == 1):
                            #--Pluggy TypeESP
                            log(_('    Pluggy ESPs'))
                            log(_('    EID   ID    Name'))
                            while (ins.tell() < len(chunkBuff)):
                                if chunkVersion == 2:
                                    espId,modId, = unpack('=BB', 2)
                                    log(_('    %02X    %02X') % (espId,modId))
                                    espMap[modId] = espId
                                else: #elif chunkVersion == 1"
                                    espId,modId,modNameLen, = unpack('=BBI',6)
                                    modName = ins.read(modNameLen)
                                    log(_('    %02X    %02X    %s') % (espId,modId,modName))
                                    espMap[modId] = modName # was [espId]
                        elif (chunkTypeNum == 2):
                            #--Pluggy TypeSTR
                            log(_('    Pluggy String'))
                            strId,modId,strFlags, = unpack('=IBB',6)
                            strData = ins.read(len(chunkBuff) - ins.tell())
                            log(_('      StrID : %u') % (strId,))
                            log(_('      ModID : %02X %s') % (modId,espMap[modId] if modId in espMap else 'ERROR',))
                            log(_('      Flags : %u') % (strFlags,))
                            log(_('      Data  : %s') % (strData,))
                        elif (chunkTypeNum == 3):
                            #--Pluggy TypeArray
                            log(_('    Pluggy Array'))
                            arrId,modId,arrFlags,arrSize, = unpack('=IBBI',10)
                            log(_('      ArrID : %u') % (arrId,))
                            log(_('      ModID : %02X %s') % (modId,espMap[modId] if modId in espMap else 'ERROR',))
                            log(_('      Flags : %u') % (arrFlags,))
                            log(_('      Size  : %u') % (arrSize,))
                            while (ins.tell() < len(chunkBuff)):
                                elemIdx,elemType, = unpack('=IB',5)
                                elemStr = ins.read(4)
                                if (elemType == 0): #--Integer
                                    elem, = struct.unpack('=i',elemStr)
                                    log(_('        [%u]  INT  %d') % (elemIdx,elem,))
                                elif (elemType == 1): #--Ref
                                    elem, = struct.unpack('=I',elemStr)
                                    log(_('        [%u]  REF  %08X') % (elemIdx,elem,))
                                elif (elemType == 2): #--Float
                                    elem, = struct.unpack('=f',elemStr)
                                    log(_('        [%u]  FLT  %08X') % (elemIdx,elem,))
                        elif (chunkTypeNum == 4):
                            #--Pluggy TypeName
                            log(_('    Pluggy Name'))
                            refId, = unpack('=I',4)
                            refName = ins.read(len(chunkBuff) - ins.tell())
                            newName = ''
                            for i in range(len(refName)):
                                ch = refName[i] if ((refName[i] >= chr(0x20)) and (refName[i] < chr(0x80))) else '.'
                                newName = newName + ch
                            log(_('      RefID : %08X') % (refId,))
                            log(_('      Name  : %s') % (newName,))
                        elif (chunkTypeNum == 5):
                            #--Pluggy TypeScr
                            log(_('    Pluggy ScreenSize'))
                            #UNTESTED - uncomment following line to skip this record type
                            #continue
                            scrW,scrH, = unpack('=II',8)
                            log(_('      Width  : %u') % (scrW,))
                            log(_('      Height : %u') % (scrH,))
                        elif (chunkTypeNum == 6):
                            #--Pluggy TypeHudS
                            log(_('    Pluggy HudS'))
                            #UNTESTED - uncomment following line to skip this record type
                            #continue
                            hudSid,modId,hudFlags,hoodRootID,hudShow,hudPosX,hudPosY,hudDepth,hudScaleX,hudScaleY,hudAlpha,hudAlignment,hudAutoScale, = unpack('=IBBBBffhffBBB',29)
                            hudFileName = ins.read(len(chunkBuff) - ins.tell())
                            log(_('      HudSID : %u') % (hudSid,))
                            log(_('      ModID  : %02X %s') % (modId,espMap[modId] if modId in espMap else 'ERROR',))
                            log(_('      Flags  : %02X') % (hudFlags,))
                            log(_('      RootID : %u') % (hudRootID,))
                            log(_('      Show   : %02X') % (hudShow,))
                            log(_('      Pos    : %f,%f') % (hudPosX,hudPosY,))
                            log(_('      Depth  : %u') % (hudDepth,))
                            log(_('      Scale  : %f,%f') % (hudScaleX,hudScaleY,))
                            log(_('      Alpha  : %02X') % (hudAlpha,))
                            log(_('      Align  : %02X') % (hudAlignment,))
                            log(_('      AutoSc : %02X') % (hudAutoScale,))
                            log(_('      File   : %s') % (hudFileName,))
                        elif (chunkTypeNum == 7):
                            #--Pluggy TypeHudT
                            log(_('    Pluggy HudT'))
                            #UNTESTED - uncomment following line to skip this record type
                            #continue
                            hudTid,modId,hudFlags,hudShow,hudPosX,hudPosY,hudDepth, = unpack('=IBBBffh',17)
                            hudScaleX,hudScaleY,hudAlpha,hudAlignment,hudAutoScale,hudWidth,hudHeight,hudFormat, = unpack('=ffBBBIIB',20)
                            hudFontNameLen, = unpack('=I',4)
                            hudFontName = ins.read(hudFontNameLen)
                            hudFontHeight,hudFontWidth,hudWeight,hudItalic,hudFontR,hudFontG,hudFontB, = unpack('=IIhBBBB',14)
                            hudText = ins.read(len(chunkBuff) - ins.tell())
                            log(_('      HudTID : %u') % (hudTid,))
                            log(_('      ModID  : %02X %s') % (modId,espMap[modId] if modId in espMap else 'ERROR',))
                            log(_('      Flags  : %02X') % (hudFlags,))
                            log(_('      Show   : %02X') % (hudShow,))
                            log(_('      Pos    : %f,%f') % (hudPosX,hudPosY,))
                            log(_('      Depth  : %u') % (hudDepth,))
                            log(_('      Scale  : %f,%f') % (hudScaleX,hudScaleY,))
                            log(_('      Alpha  : %02X') % (hudAlpha,))
                            log(_('      Align  : %02X') % (hudAlignment,))
                            log(_('      AutoSc : %02X') % (hudAutoScale,))
                            log(_('      Width  : %u') % (hudWidth,))
                            log(_('      Height : %u') % (hudHeight,))
                            log(_('      Format : %u') % (hudFormat,))
                            log(_('      FName  : %s') % (hudFontName,))
                            log(_('      FHght  : %u') % (hudFontHeight,))
                            log(_('      FWdth  : %u') % (hudFontWidth,))
                            log(_('      FWeigh : %u') % (hudWeight,))
                            log(_('      FItal  : %u') % (hudItalic,))
                            log(_('      FRGB   : %u,%u,%u') % (hudFontR,hudFontG,hudFontB,))
                            log(_('      FText  : %s') % (hudText,))
                    ins.close()
                    
    def findBloating(self,progress=None):
        """Analyzes file for bloating. Returns (createdCounts,nullRefCount)."""
        nullRefCount = 0
        createdCounts = {}
        progress = progress or bolt.Progress()
        progress.setFull(len(self.created)+len(self.records))
        #--Created objects
        progress(0,_('Scanning created objects'))
        for citem in self.created:
            if 'full' in citem.__class__.__slots__:
                full = citem.__getattribute__('full')
            else:
                full = citem.getSubString('FULL')
            if full:
                typeFull = (citem.recType,full)
                count = createdCounts.get(typeFull,0)
                createdCounts[typeFull] = count + 1
            progress.plus()
        for key in createdCounts.keys()[:]:
            minCount = (50,100)[key[0] == 'ALCH']
            if createdCounts[key] < minCount:
                del createdCounts[key]
        #--Change records
        progress(len(self.created),_('Scanning change records.'))
        fids = self.fids
        for record in self.records:
            fid,recType,flags,version,data = record
            if recType == 49 and fid >> 24 == 0xFF and (flags & 2):
                iref, = struct.unpack('I',data[4:8])
                if iref >> 24 != 0xFF and fids[iref] == 0:
                    nullRefCount += 1
            progress.plus()
        return (createdCounts,nullRefCount)

    def removeBloating(self,uncreateKeys,removeNullRefs=True,progress=None):
        """Removes duplicated created items and null refs."""
        numUncreated = numUnCreChanged = numUnNulled = 0
        progress = progress or bolt.Progress()
        progress.setFull((len(uncreateKeys) and len(self.created))+len(self.records))
        uncreated = set()
        #--Uncreate
        if uncreateKeys:
            progress(0,_('Scanning created objects'))
            kept = []
            for citem in self.created:
                if 'full' in citem.__class__.__slots__:
                    full = citem.__getattribute__('full')
                else:
                    full = citem.getSubString('FULL')
                if full and (citem.recType,full) in uncreateKeys:
                    uncreated.add(citem.fid)
                    numUncreated += 1
                else:
                    kept.append(citem)
                progress.plus()
            self.created = kept
        #--Change records
        progress(progress.state,_('Scanning change records.'))
        fids = self.fids
        kept = []
        for record in self.records:
            fid,recType,flags,version,data = record
            if fid in uncreated:
                numUnCreChanged += 1
            elif removeNullRefs and recType == 49 and fid >> 24 == 0xFF and (flags & 2):
                iref, = struct.unpack('I',data[4:8])
                if iref >> 24 != 0xFF and fids[iref] == 0:
                    numUnNulled += 1
                else:
                    kept.append(record)
            else:
                kept.append(record)
            progress.plus()
        self.records = kept
        return (numUncreated,numUnCreChanged,numUnNulled)

    def getCreated(self,*types):
        """Return created items of specified type(s)."""
        types = set(types)
        created = [x for x in self.created if x.recType in types]
        created.sort(key=attrgetter('fid'))
        created.sort(key=attrgetter('recType'))
        return created

    def getAbomb(self):
        """Gets animation slowing counter(?) value."""
        data = self.preCreated
        tesClassSize, = struct.unpack('H',data[:2])
        abombBytes = data[2+tesClassSize-4:2+tesClassSize]
        abombCounter, = struct.unpack('I',abombBytes)
        abombFloat, = struct.unpack('f',abombBytes)
        return (tesClassSize,abombCounter,abombFloat)

    def setAbomb(self,value=0x41000000):
        """Resets abomb counter to specified value."""
        data = self.preCreated
        tesClassSize, = struct.unpack('H',data[:2])
        if tesClassSize < 4: return
        buff = cStringIO.StringIO()
        buff.write(data)
        buff.seek(2+tesClassSize-4)
        buff.write(struct.pack('I',value))
        self.preCreated = buff.getvalue()
        buff.close()

#--------------------------------------------------------------------------------
class CoSaves:
    """Handles co-files (.pluggy, .obse) for saves."""
    reSave  = re.compile(r'\.ess(f?)$',re.I)

    @staticmethod
    def getPaths(savePath):
        """Returns cofile paths."""
        maSave = CoSaves.reSave.search(savePath.s)
        if maSave: savePath = savePath.root
        first = maSave and maSave.group(1) or ''
        return tuple(savePath+ext+first for ext in  ('.pluggy','.obse'))

    def __init__(self,savePath,saveName=None):
        """Initialize with savePath."""
        if saveName: savePath = savePath.join(saveName)
        self.savePath = savePath
        self.paths = CoSaves.getPaths(savePath)

    def delete(self):
        """Deletes cofiles."""
        for path in self.paths: path.remove()

    def recopy(self,savePath,saveName,pathFunc):
        """Renames/copies cofiles depending on supplied pathFunc."""
        if saveName: savePath = savePath.join(saveName)
        newPaths = CoSaves.getPaths(savePath)
        for oldPath,newPath in zip(self.paths,newPaths):
            if newPath.exists(): newPath.remove()
            if oldPath.exists(): pathFunc(oldPath,newPath)

    def copy(self,savePath,saveName=None):
        """Copies cofiles."""
        self.recopy(savePath,saveName,bolt.Path.copyTo)

    def move(self,savePath,saveName=None):
        """Renames cofiles."""
        self.recopy(savePath,saveName,bolt.Path.moveTo)

    def getTags(self):
        """Returns tags expressing whether cosaves exist and are correct."""
        cPluggy,cObse = ('','')
        save = self.savePath
        pluggy,obse = self.paths
        if pluggy.exists():
            cPluggy = 'XP'[abs(pluggy.mtime - save.mtime) < 10]
        if obse.exists():
            cObse = 'XO'[abs(obse.mtime - save.mtime) < 10]
        return (cObse,cPluggy)

# File System -----------------------------------------------------------------
#--------------------------------------------------------------------------------
class BsaFile:
    """Represents a BSA archive file."""

    @staticmethod
    def getHash(fileName):
        """Returns tes4's two hash values for filename.
        Based on Timeslips code with cleanup and pythonization."""
        #--NOTE: fileName is NOT a Path object!
        root,ext = os.path.splitext(fileName.lower())
        #--Hash1
        chars = map(ord,root)
        hash1 = chars[-1] | ((len(chars)>2 and chars[-2]) or 0)<<8 | len(chars)<<16 | chars[0]<<24
        if   ext == '.kf':  hash1 |= 0x80
        elif ext == '.nif': hash1 |= 0x8000
        elif ext == '.dds': hash1 |= 0x8080
        elif ext == '.wav': hash1 |= 0x80000000
        #--Hash2
        uintMask, hash2, hash3 = 0xFFFFFFFF, 0, 0
        for char in chars[1:-2]:
            hash2 = ((hash2 * 0x1003F) + char ) & uintMask
        for char in map(ord,ext):
            hash3 = ((hash3 * 0x1003F) + char ) & uintMask
        hash2 = (hash2 + hash3) & uintMask
        #--Done
        return (hash2<<32) + hash1

    #--Instance Methods ------------------------------------------------------
    def __init__(self,path):
        """Initialize."""
        self.path = path
        self.folderInfos = None

    def scan(self):
        """Reports on contents."""
        ins = bolt.StructFile(self.path.s,'rb')
        #--Header
        ins.seek(4*4)
        (self.folderCount,self.fileCount,lenFolderNames,lenFileNames,fileFlags) = ins.unpack('5I',20)
        #--FolderInfos (Initial)
        folderInfos = self.folderInfos = []
        for index in range(self.folderCount):
            hash,subFileCount,offset = ins.unpack('Q2I',16)
            folderInfos.append([hash,subFileCount,offset])
        #--Update folderInfos
        for index,folderInfo in enumerate(folderInfos):
            fileInfos = []
            folderName = cstrip(ins.read(ins.unpack('B',1)[0]))
            folderInfos[index].extend((folderName,fileInfos))
            for index in range(folderInfo[1]):
                filePos = ins.tell()
                hash,size,offset = ins.unpack('Q2I',16)
                fileInfos.append([hash,size,offset,'',filePos])
        #--File Names
        fileNames = ins.read(lenFileNames)
        fileNames = fileNames.split('\x00')[:-1]
        namesIter = iter(fileNames)
        for folderInfo in folderInfos:
            fileInfos = folderInfo[-1]
            for index,fileInfo in enumerate(fileInfos):
                fileInfo[3] = namesIter.next()
        #--Done
        ins.close()

    def report(self,printAll=False):
        """Report on contents."""
        folderInfos = self.folderInfos
        getHash = BsaFile.getHash
        print self.folderCount,self.fileCount,sum(len(info[-1]) for info in folderInfos)
        for folderInfo in folderInfos:
            printOnce = folderInfo[-2]
            for fileInfo in folderInfo[-1]:
                hash,fileName = fileInfo[0],fileInfo[3]
                trueHash = getHash(fileName)

    def firstBackup(self,progress):
        """Make first backup, just in case!"""
        backupDir = modInfos.bashDir.join('Backups')
        backupDir.makedirs()
        backup = backupDir.join(self.path.tail)+'f'
        if not backup.exists():
            progress(0,_("Backing up BSA file. This will take a while..."))
            self.path.copyTo(backup)

    def updateAIText(self,files=None):
        """Update aiText with specified files. (Or remove, if files == None.)"""
        aiPath = dirs['app'].join('ArchiveInvalidation.txt')
        if not files:
            aiPath.remove()
            return
        #--Archive invalidation
        aiText = re.sub(r'\\','/','\n'.join(files))
        aiPath.open('w').write(aiText)

    def resetMTimes(self):
        """Reset dates of bsa files to 'correct' values."""
        #--Fix the data of a few archive files
        bsaTimes = (
            ('Oblivion - Meshes.bsa',1138575220),
            ('Oblivion - Misc.bsa',1139433736),
            ('Oblivion - Sounds.bsa',1138660560),
            ('Oblivion - Textures - Compressed.bsa',1138162634),
            ('Oblivion - Voices1.bsa',1138162934),
            ('Oblivion - Voices2.bsa',1138166742),
            )
        for bsaFile,mtime in bsaTimes:
            dirs['mods'].join(bsaFile).mtime = mtime

    def reset(self,progress=None):
        """Resets BSA archive hashes to correct values."""
        ios = bolt.StructFile(self.path.s,'r+b')
        #--Rehash
        resetCount = 0
        folderInfos = self.folderInfos
        getHash = BsaFile.getHash
        for folderInfo in folderInfos:
            for fileInfo in folderInfo[-1]:
                hash,size,offset,fileName,filePos = fileInfo
                trueHash = getHash(fileName)
                if hash != trueHash:
                    #print ' ',fileName,'\t',hex(hash-trueHash),hex(hash),hex(trueHash)
                    ios.seek(filePos)
                    ios.pack('Q',trueHash)
                    resetCount += 1
        #--Done
        ios.close()
        self.resetMTimes()
        self.updateAIText()
        return resetCount

    def invalidate(self,progress=None):
        """Invalidates entries in BSA archive and regenerates Archive Invalidation.txt."""
        reRepTexture = re.compile(r'(?<!_[gn])\.dds',re.I)
        ios = bolt.StructFile(self.path.s,'r+b')
        #--Rehash
        reset,inval,intxt = [],[],[]
        folderInfos = self.folderInfos
        getHash = BsaFile.getHash
        trueHashes = set()
        def setHash(filePos,newHash):
            ios.seek(filePos)
            ios.pack('Q',newHash)
            return newHash
        for folderInfo in folderInfos:
            folderName = folderInfo[-2]
            #--Actual directory files
            diskPath = modInfos.dir.join(folderName)
            diskFiles = set(x.s.lower() for x in diskPath.list())
            trueHashes.clear()
            nextHash = 0 #--But going in reverse order, physical 'next' == loop 'prev'
            for fileInfo in reversed(folderInfo[-1]):
                hash,size,offset,fileName,filePos = fileInfo
                #--NOT a Path object.
                fullPath = os.path.join(folderName,fileName)
                trueHash = getHash(fileName)
                plusCE = trueHash + 0xCE
                plusE = trueHash + 0xE
                #--No invalidate?
                if not (fileName in diskFiles and reRepTexture.search(fileName)):
                    if hash != trueHash:
                        setHash(filePos,trueHash)
                        reset.append(fullPath)
                    nextHash = trueHash
                #--Invalidate one way or another...
                elif not nextHash or (plusCE < nextHash and plusCE not in trueHashes):
                    nextHash = setHash(filePos,plusCE)
                    inval.append(fullPath)
                elif plusE < nextHash and plusE not in trueHashes:
                    nextHash = setHash(filePos,plusE)
                    inval.append(fullPath)
                else:
                    if hash != trueHash:
                        setHash(filePos,trueHash)
                    nextHash = trueHash
                    intxt.append(fullPath)
                trueHashes.add(trueHash)
        #--Save/Cleanup
        ios.close()
        self.resetMTimes()
        self.updateAIText(intxt)
        #--Done
        return (reset,inval,intxt)

#--------------------------------------------------------------------------------
class OblivionIni:
    """Oblivion.ini file."""
    bsaRedirectors = set(('archiveinvalidationinvalidated!.bsa',r'..\obmm\bsaredirection.bsa'))

    def __init__(self):
        """Initialize."""
        self.path = dirs['saveBase'].join('Oblivion.ini')
        self.isCorrupted = False

    def ensureExists(self):
        """Ensures that Oblivion.ini file exists. Copies from default oblvion.ini if necessary."""
        if self.path.exists(): return
        srcPath = dirs['app'].join('Oblivion_default.ini')
        srcPath.copyTo(self.path)

    def getSetting(self,section,key,default=None):
        """Gets a single setting from the file."""
        section,key = map(bolt.LString,(section,key))
        settings = self.getSettings()
        if section in settings:
            return settings[section].get(key,default)
        else:
            return default

    def getSettings(self):
        """Gets settings for self."""
        reComment = re.compile(';.*')
        reSection = re.compile(r'^\[\s*(.+?)\s*\]$')
        reSetting = re.compile(r'(.+?)\s*=(.*)')
        #--Read ini file
        self.ensureExists()
        iniFile = self.path.open('r')
        settings = {} #settings[section][key] = value (stripped!)
        sectionSettings = None
        for line in iniFile:
            stripped = reComment.sub('',line).strip()
            maSection = reSection.match(stripped)
            maSetting = reSetting.match(stripped)
            if maSection:
                sectionSettings = settings[LString(maSection.group(1))] = {}
            elif maSetting:
                if sectionSettings == None:
                    sectionSettings = settings.setdefault(LString('General'),{})
                    self.isCorrupted = True
                sectionSettings[LString(maSetting.group(1))] = maSetting.group(2).strip()
        iniFile.close()
        return settings

    def getTweakFileSettings(self,tweakPath):
        """Gets settings in a tweak file."""
        reComment = re.compile(';.*')
        reSection = re.compile(r'^\[\s*(.+?)\s*\]$')
        reSetting = re.compile(r'(.+?)\s*=(.*)')
        #--Read ini file
        settings = {}
        if not tweakPath.exists() or tweakPath.isdir():
            return settings
        iniFile = tweakPath.open('r')
        sectionSettings = None
        for line in iniFile:
            stripped = reComment.sub('',line).strip()
            maSection = reSection.match(stripped)
            maSetting = reSetting.match(stripped)
            if maSection:
                sectionSettings = settings[LString(maSection.group(1))] = {}
            elif maSetting:
                if sectionSettings == None:
                    sectionSettings = settings.setdefault(LString('General'),{})
                sectionSettings[LString(maSetting.group(1))] = maSetting.group(2).strip()
        iniFile.close()
        return settings

    def saveSetting(self,section,key,value):
        """Changes a single setting in the file."""
        settings = {section:{key:value}}
        self.saveSettings(settings)

    def saveSettings(self,settings):
        """Applies dictionary of settings to ini file.
        Values in settings dictionary can be either actual values or
        full key=value line ending in newline char."""
        settings = dict((LString(x),dict((LString(u),v) for u,v in y.iteritems()))
            for x,y in settings.iteritems())
        reComment = re.compile(';.*')
        reSection = re.compile(r'^\[\s*(.+?)\s*\]$')
        reSetting = re.compile(r'(.+?)\s*=')
        #--Read init, write temp
        self.ensureExists()
        iniFile = self.path.open('r')
        tmpFile = self.path.temp.open('w')
        section = sectionSettings = None
        for line in iniFile:
            stripped = reComment.sub('',line).strip()
            maSection = reSection.match(stripped)
            maSetting = reSetting.match(stripped)
            if maSection:
                section = LString(maSection.group(1))
                sectionSettings = settings.get(section,{})
            elif maSetting and LString(maSetting.group(1)) in sectionSettings:
                key = LString(maSetting.group(1))
                value = sectionSettings[key]
                if isinstance(value,str) and value[-1] == '\n':
                    line = value
                else:
                    line = '%s=%s\n' % (key,value)
            tmpFile.write(line)
        tmpFile.close()
        iniFile.close()
        #--Done
        self.path.untemp()

    def applyTweakFile(self,tweakPath):
        """Read Ini tweak file and apply its settings to oblivion.ini.
        Note: Will ONLY apply settings that already exist."""
        reComment = re.compile(';.*')
        reSection = re.compile(r'^\[\s*(.+?)\s*\]$')
        reSetting = re.compile(r'(.+?)\s*=')
        #--Read Tweak file
        self.ensureExists()
        tweakFile = tweakPath.open('r')
        settings = {} #settings[section][key] = "key=value\n"
        sectionSettings = None
        for line in tweakFile:
            stripped = reComment.sub('',line).strip()
            maSection = reSection.match(stripped)
            maSetting = reSetting.match(stripped)
            if maSection:
                sectionSettings = settings[LString(maSection.group(1))] = {}
            elif maSetting:
                if line[-1:] != '\n': line += '\r\n' #--Make sure has trailing new line
                sectionSettings[LString(maSetting.group(1))] = line
        tweakFile.close()
        self.saveSettings(settings)

    #--BSA Redirection --------------------------------------------------------
    def getBsaRedirection(self):
        """Returns True if BSA redirection is active."""
        self.ensureExists()
        sArchives = self.getSetting('Archive','sArchiveList','')
        return bool([x for x in sArchives.split(',') if x.strip().lower() in self.bsaRedirectors])

    def setBsaRedirection(self,doRedirect=True):
        """Activates or deactivates BSA redirection."""
        aiBsa = dirs['mods'].join('ArchiveInvalidationInvalidated!.bsa')
        aiBsaMTime = time.mktime((2006, 1, 2, 0, 0, 0, 0, 2, 0))
        if aiBsa.exists() and aiBsa.mtime >  aiBsaMTime:
            aiBsa.mtime = aiBsaMTime
        if doRedirect == self.getBsaRedirection(): return
        sArchives = self.getSetting('Archive','sArchiveList','')
        #--Strip existint redirectors out
        archives = [x.strip() for x in sArchives.split(',') if x.strip().lower() not in self.bsaRedirectors]
        #--Add redirector back in?
        if doRedirect:
            archives.insert(0,'ArchiveInvalidationInvalidated!.bsa')
        sArchives = ', '.join(archives)
        self.saveSetting('Archive','sArchiveList',sArchives)

#------------------------------------------------------------------------------
class PluginsFullError(BoltError):
    """Usage Error: Attempt to add a mod to plugins when plugins is full."""
    def __init__(self,message=_('Load list is full.')):
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class Plugins:
    """Plugins.txt file. Owned by modInfos. Almost nothing else should access it directly."""
    def __init__(self):
        """Initialize."""
        self.dir = dirs['userApp']
        self.path = self.dir.join('Plugins.txt')
        self.mtime = 0
        self.size = 0
        self.selected = []
        self.selectedBad = [] #--In plugins.txt, but don't exist!
        self.selectedExtra = [] #--Where mod number would be greater than 255.
        #--Create dirs/files if necessary
        self.dir.makedirs()
        if not self.path.exists():
            self.save()

    def load(self):
        """Read data from plugins.txt file.
        NOTE: modInfos must exist and be up to date."""
        #--Read file
        self.mtime = self.path.mtime
        self.size = self.path.size
        ins = self.path.open('r')
        #--Load Files
        modNames = set()
        modsDir = dirs['mods']
        del self.selected[:]
        del self.selectedBad[:]
        for line in ins:
            modName = reComment.sub('',line).strip()
            if not modName: continue
            modName = GPath(modName)
            if modName in modNames: #--In case it's listed twice.
                pass
            elif len(self.selected) == 255:
                self.selectedExtra.append(modName)
            elif modName in modInfos:
                self.selected.append(modName)
            else:
                self.selectedBad.append(modName)
            modNames.add(modName)
        #--Done
        ins.close()

    def save(self):
        """Write data to Plugins.txt file."""
        self.selected.sort()
        out = self.path.open('w')
        out.write('# This file is used to tell Oblivion which data files to load.\n\n')
        for modName in self.selected:
            out.write(modName.s+'\n')
        out.close()
        self.mtime = self.path.mtime
        self.size = self.path.size

    def hasChanged(self):
        """True if plugins.txt file has changed."""
        return ((self.mtime != self.path.mtime) or
            (self.size != self.path.size) )

    def refresh(self,forceRefresh):
        """Load only if plugins.txt has changed."""
        hasChanged = forceRefresh or self.hasChanged()
        if hasChanged: self.load()
        return hasChanged

    def remove(self,fileName):
        """Remove specified mod from file list."""
        while fileName in self.selected:
            self.selected.remove(fileName)

#------------------------------------------------------------------------------
class MasterInfo:
    def __init__(self,name,size):
        self.oldName = self.name = GPath(name)
        self.modInfo = modInfos.get(self.name,None)
        self.isGhost = self.modInfo and self.modInfo.isGhost
        if self.modInfo:
            self.mtime = self.modInfo.mtime
            self.author = self.modInfo.header.author
            self.masterNames = self.modInfo.masterNames
        else:
            self.mtime = 0
            self.author = ''
            self.masterNames = tuple()

    def setName(self,name):
        self.name = GPath(name)
        self.modInfo = modInfos.get(self.name,None)
        if self.modInfo:
            self.mtime = self.modInfo.mtime
            self.author = self.modInfo.header.author
            self.masterNames = self.modInfo.masterNames
        else:
            self.mtime = 0
            self.author = ''
            self.masterNames = tuple()

    def hasChanged(self):
        return (self.name != self.oldName)

    def isEsm(self):
        if self.modInfo:
            return self.modInfo.isEsm()
        else:
            return reEsmExt.search(self.name.s)

    def hasTimeConflict(self):
        """True if has an mtime conflict with another mod."""
        if self.modInfo:
            return self.modInfo.hasTimeConflict()
        else:
            return False

    def hasActiveTimeConflict(self):
        """True if has an active mtime conflict with another mod."""
        if self.modInfo:
            return self.modInfo.hasActiveTimeConflict()
        else:
            return False

    def isExOverLoaded(self):
        """True if belongs to an exclusion group that is overloaded."""
        if self.modInfo:
            return self.modInfo.isExOverLoaded()
        else:
            return False

    def getStatus(self):
        if not self.modInfo:
            return 30
        else:
            return 0

#------------------------------------------------------------------------------
class FileInfo:
    """Abstract TES4/TES4GAME File."""
    def __init__(self,dir,name):
        self.isGhost = (name.cs[-6:] == '.ghost')
        if self.isGhost:
            name = GPath(name.s[:-6])
        self.dir = GPath(dir)
        self.name = GPath(name)
        self.bashDir = self.getFileInfos().bashDir
        path = self.getPath()
        if path.exists():
            self.ctime = path.ctime
            self.mtime = path.mtime
            self.size = path.size
        else:
            self.ctime = time.time()
            self.mtime = time.time()
            self.size = 0
        self.header = None
        self.masterNames = tuple()
        self.masterOrder = tuple()
        self.madeBackup = False
        #--Ancillary storage
        self.extras = {}

    def getPath(self):
        """Returns joined dir and name."""
        path = self.dir.join(self.name)
        if self.isGhost: path += '.ghost'
        return path

    def getFileInfos(self):
        """Returns modInfos or saveInfos depending on fileInfo type."""
        raise AbstractError

    def getRow(self):
        """Gets row of data regarding self from fileInfos."""
        return self.getFileInfos().table[self.name]

    #--File type tests
    #--Note that these tests only test extension, not the file data.
    def isMod(self):
        return reModExt.search(self.name.s)
    def isEsp(self):
        if not self.isMod(): return False
        if self.header:
            return int(self.header.flags1) & 1 == 0
        else:
            return reEspExt.search(self.name.s)
    def isEsm(self):
        if not self.isMod(): return False
        if self.header:
            return int(self.header.flags1) & 1 == 1
        else:
            return reEsmExt.search(self.name.s) and False
    def isInvertedMod(self):
        """Extension indicates esp/esm, but byte setting indicates opposite."""
        return self.isMod() and self.header and self.name.cext != ('.esp','.esm')[int(self.header.flags1) & 1]

    def isEss(self):
        return self.name.cext == '.ess'

    def sameAs(self,fileInfo):
        """Returns true if other fileInfo refers to same file as this fileInfo."""
        return (
            (self.size == fileInfo.size) and
            (self.mtime == fileInfo.mtime) and
            (self.ctime == fileInfo.ctime) and
            (self.name == fileInfo.name) and
            (self.isGhost == fileInfo.isGhost) )

    def refresh(self):
        path = self.getPath()
        self.ctime = path.ctime
        self.mtime = path.mtime
        self.size  = path.size
        if self.header: self.getHeader()

    def getHeader(self):
        """Read header for file."""
        raise AbstractError

    def getHeaderError(self):
        """Read header for file. But detects file error and returns that."""
        try: self.getHeader()
        except FileError, error:
            return error.message
        else:
            return None

    def getMasterStatus(self,masterName):
        """Returns status of a master. Called by getStatus."""
        #--Exists?
        if masterName not in modInfos:
            return 30
        #--Okay?
        else:
            return 0

    def getStatus(self):
        """Returns status of this file -- which depends on status of masters.
        0:  Good
        10: Out of order master
        30: Missing master(s)."""
        #--Worst status from masters
        if self.masterNames:
            status = max([self.getMasterStatus(masterName) for masterName in self.masterNames])
        else:
            status = 0
        #--Missing files?
        if status == 30:
            return status
        #--Misordered?
        self.masterOrder = modInfos.getOrdered(self.masterNames)
        if self.masterOrder != self.masterNames:
            return 20
        else:
            return status

    def writeHeader(self):
        """Writes header to file, overwriting old header."""
        raise AbstractError

    def setmtime(self,mtime=0):
        """Sets mtime. Defaults to current value (i.e. reset)."""
        mtime = int(mtime or self.mtime)
        path = self.getPath()
        path.mtime = mtime
        self.mtime = path.mtime

    def makeBackup(self, forceBackup=False):
        """Creates backup(s) of file."""
        #--Skip backup?
        if not self in self.getFileInfos().data.values(): return
        if self.madeBackup and not forceBackup: return
        #--Backup Directory
        backupDir = self.bashDir.join('Backups')
        backupDir.makedirs()
        #--File Path
        original = self.getPath()
        #--Backup
        backup = backupDir.join(self.name)
        original.copyTo(backup)
        self.coCopy(original,backup)
        #--First backup
        firstBackup = backup+'f'
        if not firstBackup.exists():
            original.copyTo(firstBackup)
            self.coCopy(original,firstBackup)
        #--Done
        self.madeBackup = True

    def coCopy(self,oldPath,newPath):
        """Copies co files corresponding to oldPath to newPath.
        Provided so that SaveFileInfo can override for its cofiles."""
        pass

    def getStats(self):
        """Gets file stats. Saves into self.stats."""
        stats = self.stats = {}
        raise AbstractError

    def getNextSnapshot(self):
        """Returns parameters for next snapshot."""
        if not self in self.getFileInfos().data.values():
            raise StateError(_("Can't get snapshot parameters for file outside main directory."))
        destDir = self.bashDir.join('Snapshots')
        destDir.makedirs()
        (root,ext) = self.name.rootExt
        destName = root+'-00'+ext
        separator = '-'
        snapLast = ['00']
        #--Look for old snapshots.
        reSnap = re.compile('^'+root.s+'[ -]([0-9\.]*[0-9]+)'+ext+'$')
        for fileName in destDir.list():
            maSnap = reSnap.match(fileName.s)
            if not maSnap: continue
            snapNew = maSnap.group(1).split('.')
            #--Compare shared version numbers
            sharedNums = min(len(snapNew),len(snapLast))
            for index in range(sharedNums):
                (numNew,numLast) = (int(snapNew[index]),int(snapLast[index]))
                if numNew > numLast:
                    snapLast = snapNew
                    continue
            #--Compare length of numbers
            if len(snapNew) > len(snapLast):
                snapLast = snapNew
                continue
        #--New
        snapLast[-1] = ('%0'+`len(snapLast[-1])`+'d') % (int(snapLast[-1])+1,)
        destName = root+separator+('.'.join(snapLast))+ext
        return (destDir,destName,(root+'*'+ext).s)

    def setGhost(self,isGhost):
        """Sets file to/from ghost mode. Returns ghost status at end."""
        if isGhost == self.isGhost:
            return isGhost
        normal = self.dir.join(self.name)
        ghost = normal+'.ghost'
        try:
            if isGhost: normal.moveTo(ghost)
            else: ghost.moveTo(normal)
            self.isGhost = isGhost
        except:
            pass
        return self.isGhost

#------------------------------------------------------------------------------
class ModInfo(FileInfo):
    """An esp/m file."""
    def getFileInfos(self):
        """Returns modInfos or saveInfos depending on fileInfo type."""
        return modInfos

    def setType(self,type):
        """Sets the file's internal type."""
        if type not in ('esm','esp'):
            raise ArgumentError
        modFile = self.getPath().open('r+b')
        modFile.seek(8)
        flags1 = MreRecord._flags1(struct.unpack('I',modFile.read(4))[0])
        flags1.esm = (type == 'esm')
        modFile.seek(8)
        modFile.write(struct.pack('=I',int(flags1)))
        modFile.close()
        self.header.flags1 = flags1
        self.setmtime()

    def hasTimeConflict(self):
        """True if has an mtime conflict with another mod."""
        return modInfos.hasTimeConflict(self.name)

    def hasActiveTimeConflict(self):
        """True if has an active mtime conflict with another mod."""
        return modInfos.hasActiveTimeConflict(self.name)

    def isExOverLoaded(self):
        """True if belongs to an exclusion group that is overloaded."""
        maExGroup = reExGroup.match(self.name.s)
        if not (modInfos.isSelected(self.name) and maExGroup):
            return False
        else:
            exGroup = maExGroup.group(1)
            return len(modInfos.exGroup_mods.get(exGroup,'')) > 1

    def hasResources(self):
        """Returns (hasBsa,hasVoices) booleans according to presence of corresponding resources."""
        bsaPath = self.getPath().root+'.bsa'
        voicesPath = self.dir.join('Sound','Voice',self.name)
        return [bsaPath.exists(),voicesPath.exists()]

    def setmtime(self,mtime=0):
        """Sets mtime. Defaults to current value (i.e. reset)."""
        mtime = int(mtime or self.mtime)
        FileInfo.setmtime(self,mtime)
        modInfos.mtimes[self.name] = mtime

    def writeNew(self,masters=[],mtime=0):
        """Creates a new file with the given name, masters and mtime."""
        header = MreTes4(('TES4',0,(self.isEsm() and 1 or 0),0,0))
        for master in masters:
            header.masters.append(master)
        header.setChanged()
        #--Write it
        out = self.getPath().open('wb')
        header.getSize()
        header.dump(out)
        out.close()
        self.setmtime(mtime)

    #--Bash Tags --------------------------------------------------------------
    def shiftBashTags(self):
        """Shifts bash keys from bottom to top."""
        description = self.header.description
        reReturns = re.compile('\r{2,}')
        reBashTags = re.compile('^(.+)({{BASH:[^}]*}})$',re.S)
        if reBashTags.match(description) or reReturns.search(description):
            description = reReturns.sub('\r',description)
            description = reBashTags.sub(r'\2\n\1',description)
            self.writeDescription(description)

    def setBashTags(self,keys):
        """Sets bash keys as specified."""
        modInfos.table.setItem(self.name,'bashTags',keys)

    def setBashTagsDesc(self,keys):
        """Sets bash keys as specified."""
        keys = set(keys) #--Make sure it's a set.
        if keys == self.getBashTagsDesc(): return
        if keys:
            strKeys = '{{BASH:'+(','.join(sorted(keys)))+'}}\n'
        else:
            strKeys = ''
        description = self.header.description or ''
        reBashTags = re.compile(r'{{ *BASH *:[^}]*}}\s*\n?')
        if reBashTags.search(description):
            description = reBashTags.sub(strKeys,description)
        else:
            description = strKeys+description
        self.writeDescription(description)

    def getBashTags(self):
        """Returns any Bash flag keys."""
        tags = self.getRow().get('bashTags')
        if tags is None: tags = self.getBashTagsDesc()
        if tags is None: tags = configHelpers.getBashTags(self.name)
        if tags is None: tags = set()
        #--Filter and return
        tags.discard('Merge')
        return tags

    def getBashTagsDesc(self):
        """Returns any Bash flag keys."""
        description = self.header.description or ''
        maBashKeys = re.search('{{ *BASH *:([^}]+)}}',description)
        if not maBashKeys:
            return None
        else:
            bashTags = maBashKeys.group(1).split(',')
            bashTags = [str.strip() for str in bashTags]
            return set(bashTags)

    #--Header Editing ---------------------------------------------------------
    def getHeader(self):
        """Read header for file."""
        ins = ModReader(self.name,self.getPath().open('rb'))
        try:
            recHeader = ins.unpackRecHeader()
            if recHeader[0] != 'TES4':
                raise ModError(self.name,_('Expected TES4, but got ')+recHeader[0])
            self.header = MreTes4(recHeader,ins,True)
            ins.close()
        except struct.error, rex:
            ins.close()
            raise ModError(self.name,_('Struct.error: ')+`rex`)
        except:
            ins.close()
            raise
        #--Master Names/Order
        self.masterNames = tuple(self.header.masters)
        self.masterOrder = tuple() #--Reset to empty for now

    def writeHeader(self):
        """Write Header. Actually have to rewrite entire file."""
        filePath = self.getPath()
        ins = filePath.open('rb')
        out = filePath.temp.open('wb')
        try:
            #--Open original and skip over header
            reader = ModReader(self.name,ins)
            recHeader = reader.unpackRecHeader()
            if recHeader[0] != 'TES4':
                raise ModError(self.name,_('Expected TES4, but got ')+recHeader[0])
            reader.seek(recHeader[1],1)
            #--Write new header
            self.header.getSize()
            self.header.dump(out)
            #--Write remainder
            insRead = ins.read
            outWrite = out.write
            while True:
                buffer= insRead(0x5000000)
                if not buffer: break
                outWrite(buffer)
            ins.close()
            out.close()
        except struct.error, rex:
            ins.close()
            out.close()
            raise ModError(self.name,_('Struct.error: ')+`rex`)
        except:
            ins.close()
            out.close()
            raise
        #--Remove original and replace with temp
        filePath.untemp()
        self.setmtime()
        #--Merge info
        size,canMerge = modInfos.table.getItem(self.name,'mergeInfo',(None,None))
        if size != None:
            modInfos.table.setItem(self.name,'mergeInfo',(filePath.size,canMerge))

    def writeDescription(self,description):
        """Sets description to specified text and then writes hedr."""
        description = description[:min(255,len(description))]
        self.header.description = description
        self.header.setChanged()
        self.writeHeader()

    def writeAuthor(self,author):
        """Sets author to specified text and then writes hedr."""
        author = author[:min(512,len(author))]
        self.header.author = author
        self.header.setChanged()
        self.writeHeader()

    def writeAuthorWB(self):
        """Marks author field with " [wb]" to indicate Wrye Bash modification."""
        author = self.header.author
        if '[wm]' not in author and len(author) <= 27:
            self.writeAuthor(author+' [wb]')

#------------------------------------------------------------------------------
class INIInfo(FileInfo):
    def getFileInfos(self):
        return iniInfos

    def getHeader(self):
        pass

    def getStatus(self):
        """Returns status of the ini tweak:
        20: installed (green)
        10: mismatches (yellow)
        0: not installed (white)
        -10: invalid tweak file (red)."""
        path = self.getPath()
        tweak = oblivionIni.getTweakFileSettings(path)
        settings = oblivionIni.getSettings()
        status = 20
        if len(tweak) == 0: status = -10
        for key in tweak:
            if key not in settings:
                status = -10
                break
            for item in tweak[key]:
                if item not in settings[key]:
                    status = -10
                    break
                if tweak[key][item] != settings[key][item]:
                    if status == 20:
                        status = 0
                else:
                    if status == 0:
                        status = 10
        return status
        
class SaveInfo(FileInfo):
    def getFileInfos(self):
        """Returns modInfos or saveInfos depending on fileInfo type."""
        return saveInfos

    def getStatus(self):
        status = FileInfo.getStatus(self)
        masterOrder = self.masterOrder
        #--File size?
        if status > 0 or len(masterOrder) > len(modInfos.ordered):
            return status
        #--Current ordering?
        if masterOrder != modInfos.ordered[:len(masterOrder)]:
            return status
        elif masterOrder == modInfos.ordered:
            return -20
        else:
            return -10

    def getHeader(self):
        """Read header for file."""
        try:
            self.header = SaveHeader(self.getPath())
            #--Master Names/Order
            self.masterNames = tuple(self.header.masters)
            self.masterOrder = tuple() #--Reset to empty for now
        except struct.error, rex:
            raise SaveFileError(self.name,_('Struct.error: ')+`rex`)

    def coCopy(self,oldPath,newPath):
        """Copies co files corresponding to oldPath to newPath."""
        CoSaves(oldPath).copy(newPath)

    def coSaves(self):
        """Returns CoSaves instance corresponding to self."""
        return CoSaves(self.getPath())

#------------------------------------------------------------------------------
class BSAInfo(FileInfo):
    def getFileInfos(self):
        """Returns modInfos or saveInfos depending on fileInfo type."""
        return BSAInfos

    def getStatus(self):
        status = FileInfo.getStatus(self)
        #masterOrder = self.masterOrder
        #--File size?
     #   if status > 0 or len(masterOrder) > len(modInfos.ordered):
      #      return status
        #--Current ordering?
       # if masterOrder != modInfos.ordered[:len(masterOrder)]:
        #    return status
        #elif masterOrder == modInfos.ordered:
        #    return -20
        #else:
        #    return -10
        return 20
        
    def getHeader(self):
        """Read header for file."""
        
        try:
            self.header = SaveHeader(self.getPath())
            #--Master Names/Order
            self.masterNames = tuple(self.header.masters)
            self.masterOrder = tuple() #--Reset to empty for now
        except struct.error, rex:
            raise SaveFileError(self.name,_('Struct.error: ')+`rex`)

    def coCopy(self,oldPath,newPath):
        """Copies co files corresponding to oldPath to newPath."""
        CoSaves(oldPath).copy(newPath)

    def coSaves(self):
        """Returns CoSaves instance corresponding to self."""
        return CoSaves(self.getPath())

#------------------------------------------------------------------------------
class FileInfos(DataDict):
    def __init__(self,dir,factory=FileInfo):
        """Init with specified directory and specified factory type."""
        self.dir = dir #--Path
        self.factory=factory
        self.data = {}
        self.bashDir = self.getBashDir()
        self.table = bolt.Table(PickleDict(
            self.bashDir.join('Table.dat'),
            self.bashDir.join('Table.pkl')))
        self.corrupted = {} #--errorMessage = corrupted[fileName]
        #--Update table keys...
        tableData = self.table.data
        for key in self.table.data.keys():
            if not isinstance(key,bolt.Path):
                del tableData[key]

    def getBashDir(self):
        """Returns Bash data storage directory."""
        return self.dir.join('Bash')

    #--Refresh File
    def refreshFile(self,fileName):
        try:
            fileInfo = self.factory(self.dir,fileName)
            path = fileInfo.getPath()
            fileInfo.isGhost = not path.exists() and (path+'.ghost').exists()
            fileInfo.getHeader()
            self.data[fileName] = fileInfo
        except FileError, error:
            self.corrupted[fileName] = error.message
            if fileName in self.data:
                del self.data[fileName]
            raise

    #--Refresh
    def refresh(self):
        """Refresh from file directory."""
        data = self.data
        oldNames = set(data)
        newNames = set()
        added = set()
        updated = set()
        self.dir.makedirs()
        #--Loop over files in directory
        names = [x for x in self.dir.list() if self.dir.join(x).isfile() and self.rightFileType(x)]
        names.sort(key=lambda x: x.cext == '.ghost')
        for name in names:
            fileInfo = self.factory(self.dir,name)
            name = fileInfo.name #--Might have '.ghost' lopped off.
            if name in newNames: continue #--Must be a ghost duplicate. Ignore it.
            oldInfo = self.data.get(name)
            isAdded = name not in oldNames
            isUpdated = not isAdded and not fileInfo.sameAs(oldInfo)
            if isAdded or isUpdated:
                errorMessage = fileInfo.getHeaderError()
                if errorMessage:
                    self.corrupted[name] = errorMessage
                    data.pop(name,None)
                    continue
                else:
                    data[name] = fileInfo
                    self.corrupted.pop(name,None)
                    if isAdded: added.add(name)
                    elif isUpdated: updated.add(name)
            newNames.add(name)
        deleted = oldNames - newNames
        for name in deleted: data.pop(name)
        return bool(added) or bool(updated) or bool(deleted)

    #--Right File Type? [ABSTRACT]
    def rightFileType(self,fileName):
        """Bool: filetype (extension) is correct for subclass. [ABSTRACT]"""
        raise AbstractError

    #--Rename
    def rename(self,oldName,newName):
        """Renames member file from oldName to newName."""
        #--Update references
        fileInfo = self[oldName]
        #--File system
        newPath = self.dir.join(newName)
        if fileInfo.isGhost: newPath += '.ghost'
        oldPath = fileInfo.getPath()
        oldPath.moveTo(newPath)
        #--FileInfo
        fileInfo.name = newName
        #--FileInfos
        self[newName] = self[oldName]
        del self[oldName]
        self.table.moveRow(oldName,newName)
        #--Done
        fileInfo.madeBackup = False

    #--Delete
    def delete(self,fileName,doRefresh=True):
        """Deletes member file."""
        fileInfo = self[fileName]
        #--File
        filePath = fileInfo.getPath()
        filePath.remove()
        #--Table
        self.table.delRow(fileName)
        #--Misc. Editor backups (mods only)
        if fileInfo.isMod():
            for ext in ('.bak','.tmp','.old','.ghost'):
                backPath = filePath + ext
                backPath.remove()
        #--Backups
        backRoot = self.getBashDir().join('Backups',fileInfo.name)
        for backPath in (backRoot,backRoot+'f'):
            backPath.remove()
        if doRefresh: self.refresh()

    #--Move Exists
    def moveIsSafe(self,fileName,destDir):
        """Bool: Safe to move file to destDir."""
        return not destDir.join(fileName).exists()

    #--Move
    def move(self,fileName,destDir,doRefresh=True):
        """Moves member file to destDir. Will overwrite!"""
        destDir.makedirs()
        srcPath = self[fileName].getPath()
        destPath = destDir.join(fileName)
        srcPath.moveTo(destPath)
        if doRefresh: self.refresh()

    #--Copy
    def copy(self,fileName,destDir,destName=None,mtime=False):
        """Copies member file to destDir. Will overwrite!"""
        destDir.makedirs()
        if not destName: destName = fileName
        srcPath = self.data[fileName].getPath()
        if destDir == self.dir and destName in self.data:
            destPath = self.data[destName].getPath()
        else:
            destPath = destDir.join(destName)
        srcPath.copyTo(destPath)
        if mtime:
            if mtime == True:
                mtime = srcPath.mtime
            elif mtime == '+1':
                mtime = srcPath.mtime + 1
            destPath.mtime = mtime
        self.refresh()

#------------------------------------------------------------------------------
class ResourceReplacer:
    """Resource Replacer. Used to apply and remove a set of resource (texture, etc.) replacement files."""
    #--Class data
    dirExts = {
        'distantlod': ['.cmp', '.lod'],
        'docs':['.txt','.html','.htm','.rtf','.doc','.gif','.jpg'],
        'facegen': ['.ctl'],
        'fonts': ['.fnt', '.tex'],
        'menus': ['.bat', '.html', '.scc', '.txt', '.xml'],
        'meshes': ['.egm', '.egt', '.fim', '.kf', '.kfm', '.nif', '.tri', '.txt'],
        'obse':['.dll','.dlx','.txt','.mp3'],
        'shaders': ['.sdp','.fx'],
        'sound': ['.lip', '.mp3', '.wav'],
        'textures': ['.dds', '.ifl', '.psd', '.txt'],
        'trees': ['.spt'],
        }

    def __init__(self,replacerDir,file):
        """Initialize"""
        self.replacerDir = replacerDir
        self.file = file
        self.rootDir = ''

    def isApplied(self):
        """Returns True if has been applied."""
        return self.file in settings['bosh.resourceReplacer.applied']

    def validate(self):
        """Does archive invalidation according to settings."""
        if settings.get('bash.replacers.autoEditBSAs',False):
            bsaPath = dirs['mods'].join('Oblivion - Textures - Compressed.bsa')
            bsaFile = BsaFile(bsaPath)
            bsaFile.scan()
            bsaFile.invalidate()

    def apply(self,progress=None):
        """Copy files to appropriate resource directories (Textures, etc.)."""
        progress = progress or bolt.Progress()
        progress.state,progress.full = 0,1
        progress(0,_("Getting sizes."))
        self.doRoot(self.countDir,progress) #--Updates progress.full
        self.doRoot(self.applyDir,progress)
        self.validate()
        settings.getChanged('bosh.resourceReplacer.applied').append(self.file)

    def remove(self,progress=None):
        """Uncopy files from appropriate resource directories (Textures, etc.)."""
        progress = progress or bolt.Progress()
        self.doRoot(self.removeDir,progress)
        self.validate()
        settings.getChanged('bosh.resourceReplacer.applied').remove(self.file)

    def doRoot(self,action,progress):
        """Copy/uncopy files to/from appropriate resource directories."""
        dirExts = ResourceReplacer.dirExts
        srcDir = self.rootDir = self.replacerDir.join(self.file)
        destDir = dirs['mods']
        action(srcDir,destDir,['.esp','.esm','.bsa'],progress)
        for srcFile in srcDir.list():
            srcPath  = srcDir.join(srcFile)
            if srcPath.isdir() and srcFile.cs in dirExts:
                destPath = destDir.join(srcFile)
                action(srcPath,destPath,dirExts[srcFile],progress)

    def sizeDir(self,srcDir,destDir,exts,progress):
        """Determine cumulative size of files to copy."""
        for srcFile in srcDir.list():
            srcExt = srcFile.cext
            srcPath  = srcDir.join(srcFile)
            destPath = destDir.join(srcFile)
            if srcExt in exts:
                progress.full += srcPath.size
            elif srcPath.isdir():
                self.sizeDir(srcPath,destPath,exts,progress)

    def countDir(self,srcDir,destDir,exts,progress):
        """Determine cumulative count of files to copy."""
        rootDir = self.rootDir
        for srcFile in srcDir.list():
            srcExt = srcFile.cext
            srcPath  = srcDir.join(srcFile)
            destPath = destDir.join(srcFile)
            if srcExt in exts:
                progress.full += 1
            elif srcDir != rootDir and srcPath.isdir():
                self.countDir(srcPath,destPath,exts,progress)

    def applyDir(self,srcDir,destDir,exts,progress):
        """Copy files to appropriate resource directories (Textures, etc.)."""
        rootDir = self.rootDir
        progress(progress.state,srcDir.s[len(rootDir.s)+1:])
        for srcFile in srcDir.list():
            srcExt = srcFile.cext
            srcPath  = srcDir.join(srcFile)
            destPath = destDir.join(srcFile)
            if srcExt in exts:
                destDir.makedirs()
                srcPath.copyTo(destPath)
                progress.plus()
            elif srcDir != rootDir and srcPath.isdir():
                self.applyDir(srcPath,destPath,exts,progress)

    def removeDir(self,srcDir,destDir,exts,progress):
        """Uncopy files from appropriate resource directories (Textures, etc.)."""
        rootDir = self.rootDir
        for srcFile in srcDir.list():
            srcExt = srcFile.cext
            srcPath  = srcDir.join(srcFile)
            destPath = destDir.join(srcFile)
            if destPath.exists():
                if srcExt in exts:
                    destPath.remove()
                elif srcDir != rootDir and srcPath.isdir():
                    self.removeDir(srcPath,destPath,exts,progress)

    @staticmethod
    def updateInvalidator():
        """Updates ArchiveInvalidator.txt file. Use this after adding/removing resources."""
        reRepTexture = re.compile(r'(?<!_[gn])\.dds',re.I)
        #--Get files to invalidate
        fileNames = []
        def addFiles(dirtuple):
            dirPath = dirs['mods'].join(*dirtuple)
            for fileName in dirPath.list():
                filetuple = dirtuple+(fileName.s,)
                if dirPath.join(fileName).isdir():
                    addFiles(filetuple)
                elif reRepTexture.search(fileName.s):
                    fileNames.append('/'.join(filetuple))
        if dirs['mods'].join('textures').exists():
            addFiles(('textures',))
        fileNames.sort(key=string.lower)
        #--Update file
        aiAppPath = dirs['app'].join('ArchiveInvalidation.txt')
        #--Update file?
        if fileNames:
            out = aiAppPath.open('w')
            for fileName in fileNames:
                out.write(fileName+'\n')
            out.close
        #--No files to invalidate, but ArchiveInvalidation.txt exists?
        elif aiAppPath.exists():
            aiAppPath.remove()
        #--Remove any duplicate AI.txt in the mod directory
        aiModsPath = dirs['mods'].join('ArchiveInvalidation.txt')
        aiModsPath.remove()
        #--Fix the data of a few archive files
        bsaTimes = (
            ('Oblivion - Meshes.bsa',1138575220),
            ('Oblivion - Misc.bsa',1139433736),
            ('Oblivion - Sounds.bsa',1138660560),
            ('Oblivion - Textures - Compressed.bsa',1138162634),
            ('Oblivion - Voices1.bsa',1138162934),
            ('Oblivion - Voices2.bsa',1138166742),
            )
        for bsaFile,mtime in bsaTimes:
            bsaPath = dirs['mods'].join(bsaFile)
            bsaPath.mtime = mtime

#------------------------------------------------------------------------------
class INIInfos(FileInfos):
    def __init__(self):
        FileInfos.__init__(self, dirs['mods'].join('INI Tweaks'),INIInfo)

    def rightFileType(self,fileName):
        """Bool: File is a mod."""
        return reINIExt.search(fileName.s)

    def getBashDir(self):
        """Return directory to save info."""
        return dirs['modsBash'].join('INI Data')
#------------------------------------------------------------------------------
class ModInfos(FileInfos):
    """Collection of modinfos. Represents mods in the Oblivion\Data directory."""

    def __init__(self):
        """Initialize."""
        FileInfos.__init__(self,dirs['mods'],ModInfo)
        #--MTime resetting
        self.lockTimes = settings['bosh.modInfos.resetMTimes']
        self.mtimes = self.table.getColumn('mtime')
        self.mtimesReset = [] #--Files whose mtimes have been reset.
        self.autoGrouped = {} #--Files that have been autogrouped.
        self.mergeScanned = [] #--Files that have been scanned for mergeability.
        #--Selection state (ordered, merged, imported)
        self.plugins = Plugins() #--Plugins instance.
        self.ordered = tuple() #--Active mods arranged in load order.
        #--Info lists/sets
        self.mtime_mods = {}
        self.mtime_selected = {}
        self.exGroup_mods = {}
        self.mergeable = set() #--Set of all mods which can be merged.
        self.merged = set() #--For bash merged files
        self.imported = set() #--For bash imported files
        self.autoSorted = set() #--Files that are auto-sorted
        self.autoHeaders = set() #--Full balo headers
        self.autoGroups = {} #--Auto groups as read from group files.
        self.group_header = {}
        #--Oblivion version
        self.version_voSize = {
            '1.1':int(_("247388848")), #--247388848
            'SI': int(_("277504985"))}
        self.size_voVersion = bolt.invertDict(self.version_voSize)
        self.voCurrent = None
        self.voAvailable = set()

    def getBashDir(self):
        """Returns Bash data storage directory."""
        return dirs['modsBash']

    #--Refresh-----------------------------------------------------------------
    def canSetTimes(self):
        """Returns a boolean indicating if mtime setting is allowed."""
        self.lockTimes = settings['bosh.modInfos.resetMTimes']
        self.fullBalo = settings.get('bash.balo.full',False)
        obmmWarn = settings.setdefault('bosh.modInfos.obmmWarn',0)
        if self.lockTimes and obmmWarn == 0 and dirs['app'].join('obmm').exists():
            settings['bosh.modInfos.obmmWarn'] = 1
        if not self.lockTimes: return False
        if settings['bosh.modInfos.obmmWarn'] == 1: return False
        if settings.dictFile.readOnly: return False
        #--Else
        return True

    def refresh(self,doAutoGroup=False,doInfos=True):
        """Update file data for additions, removals and date changes."""
        self.canSetTimes()
        hasChanged = doInfos and FileInfos.refresh(self)
        self.refreshHeaders()
        hasChanged += self.updateBaloHeaders()
        if hasChanged:
            self.resetMTimes()
        if self.fullBalo: self.autoGroup()
        hasChanged += self.plugins.refresh(hasChanged)
        hasGhosted = self.autoGhost()
        hasSorted = self.autoSort()
        self.refreshInfoLists()
        self.getOblivionVersions()
        return bool(hasChanged) or hasSorted or hasGhosted

    def refreshHeaders(self):
        """Updates group_header."""
        group_header = self.group_header
        group_header.clear()
        mod_group = self.table.getColumn('group')
        for mod in self.data:
            group = mod_group.get(mod,None)
            if group and mod.s[:2] == '++':
                group_header[group] = mod

    def resetMTimes(self):
        """Remember/reset mtimes of member files."""
        if not self.canSetTimes(): return
        del self.mtimesReset[:]
        for fileName, fileInfo in sorted(self.data.items(),key=lambda x: x[1].mtime):
            oldMTime = int(self.mtimes.get(fileName,fileInfo.mtime))
            self.mtimes[fileName] = oldMTime
            if fileInfo.mtime != oldMTime and oldMTime  > 0:
                #deprint(fileInfo.name, oldMTime - fileInfo.mtime)
                fileInfo.setmtime(oldMTime)
                self.mtimesReset.append(fileName)

    def updateAutoGroups(self):
        """Update autogroup definitions."""
        self.autoGroups.clear()
        modGroups = ModGroups()
        for base in ('Bash_Groups.csv','My_Groups.csv'):
            path = self.dir.join('Bash Patches',base)
            if path.exists(): modGroups.readFromText(path)
        self.autoGroups.update(modGroups.mod_group)

    def autoGhost(self,force=False):
        """Automatically inactive files to ghost."""
        hasChanged = False
        allowGhosting = self.table.getColumn('allowGhosting')
        toGhost = settings.get('bash.mods.autoGhost',False)
        if force or toGhost:
            active = set(self.ordered)
            for mod in self.data:
                modInfo = self.data[mod]
                modGhost = toGhost and mod not in active and allowGhosting.get(mod,True)
                oldGhost = modInfo.isGhost
                newGhost = modInfo.setGhost(modGhost)
                hasChanged |= (newGhost != oldGhost)
        return hasChanged

    def autoGroup(self):
        """Automatically assigns groups for currently ungrouped mods."""
        autoGroup = settings.get('bash.balo.autoGroup',True)
        if not self.autoGroups: self.updateAutoGroups()
        mod_group = self.table.getColumn('group')
        bashGroups = set(settings['bash.mods.groups'])
        for fileName in self.data:
            if not mod_group.get(fileName):
                group = 'NONE' #--Default
                if autoGroup:
                    if fileName in self.data and self.data[fileName].header:
                        maGroup = reGroup.search(self.data[fileName].header.description)
                        if maGroup: group = maGroup.group(1)
                    if group == 'NONE' and fileName in self.autoGroups:
                        group = self.autoGroups[fileName]
                    if group not in bashGroups:
                        group = 'NONE'
                    if group != 'NONE':
                        self.autoGrouped[fileName] = group
                mod_group[fileName] = group

    def autoSort(self):
        """Automatically sorts mods by group."""
        autoSorted = self.autoSorted
        autoSorted.clear()
        if not self.canSetTimes(): return False
        #--Balo headers
        headers = self.group_header.values()
        #--Get group_mods
        group_mods = {}
        mod_group = self.table.getColumn('group')
        for mod in self.data:
            group = mod_group.get(mod,None)
            if group and mod not in headers:
                if group not in group_mods:
                    group_mods[group] = []
                group_mods[group].append(mod)
                if group != 'NONE': autoSorted.add(mod)
        #--Sort them
        changed = 0
        group_header = self.group_header
        if not group_header: return changed
        for group,header in self.group_header.iteritems():
            mods = group_mods.get(group,[])
            if group != 'NONE':
                mods.sort(key=attrgetter('csroot'))
                mods.sort(key=attrgetter('cext'))
            else:
                mods.sort(key=lambda a: self[a].mtime)
            mtime = self.data[header].mtime + 60
            for mod in mods:
                modInfo = self.data[mod]
                if modInfo.mtime != mtime:
                    modInfo.setmtime(mtime)
                    changed += 1
                mtime += 60
        #--Auto headers
        self.autoHeaders.clear()
        if self.fullBalo:
            self.autoHeaders.update(headers)
            autoSorted |= self.autoHeaders
        return changed

    def refreshInfoLists(self):
        """Refreshes various mod info lists (mtime_mods, mtime_selected, exGroup_mods, imported, exported."""
        #--Ordered
        self.ordered = self.getOrdered(self.plugins.selected)
        #--Mod mtimes
        mtime_mods = self.mtime_mods
        mtime_mods.clear()
        for modName in self.keys():
            mtime = modInfos[modName].mtime
            mtime_mods.setdefault(mtime,[]).append(modName)
        #--Selected mtimes
        mtime_selected = self.mtime_selected
        mtime_selected.clear()
        for modName in self.ordered:
            mtime = modInfos[modName].mtime
            mtime_selected.setdefault(mtime,[]).append(modName)
        #--Refresh overLoaded too..
        self.exGroup_mods.clear()
        for modName in self.ordered:
            maExGroup = reExGroup.match(modName.s)
            if maExGroup:
                exGroup = maExGroup.group(1)
                mods = self.exGroup_mods.setdefault(exGroup,[])
                mods.append(modName)
        #--Refresh merged/imported lists.
        self.merged,self.imported = self.getSemiActive(self.ordered)

    def refreshMergeable(self):
        """Refreshes set of mergeable mods."""
        #--Mods that need to be refreshed.
        newMods = []
        self.mergeable.clear()
        name_mergeInfo = self.table.getColumn('mergeInfo')
        #--Add known/unchanged and esms
        for name in self.data:
            modInfo = self[name]
            size,canMerge = name_mergeInfo.get(name,(None,None))
            # Check to make sure NoMerge tag not in tags - if in tags don't show up as mergeable.
            descTags = modInfo.getBashTagsDesc()
            if descTags and 'NoMerge' in descTags: continue
            bashTags = modInfo.getBashTags()
            if bashTags and 'NoMerge' in bashTags: continue
            if size == modInfo.size:
                if canMerge: self.mergeable.add(name)
            elif reEsmExt.search(name.s):
                name_mergeInfo[name] = (modInfo.size,False)
            else:
                newMods.append(name)
        return newMods

    def rescanMergeable(self,names,progress):
        """Will rescan specified mods."""
        name_mergeInfo = self.table.getColumn('mergeInfo')
        for index,name in enumerate(names):
            progress(index,name.s)
            modInfo = self[name]
            canMerge = PatchFile.modIsMergeable(modInfo) == True
            name_mergeInfo[name] = (modInfo.size,canMerge)
            if canMerge: self.mergeable.add(name)
            else: self.mergeable.discard(name)

    #--Full Balo --------------------------------------------------------------
    def updateBaloHeaders(self):
        """Adds/removes balo headers as necessary. This is called by refresh(),
        after fileInfos have been updated."""
        if not self.canSetTimes(): return False
        if not self.fullBalo or not settings.get('bash.balo.groups'):
            return False
        group_header = self.group_header
        offGroup_mtime = {}
        diffTime = datetime.timedelta(10) #--10 days between groups
        nextTime = datetime.datetime(2006,4,1,2) #--Date of next group
        lastTime = datetime.datetime(2020,3,15,2) #--Date of Last group
        def dateToTime(dt):
            return int(time.mktime(dt.timetuple()))
        bashGroups = settings.getChanged('bash.mods.groups')
        del bashGroups[:]
        for group,lower,upper in settings['bash.balo.groups']:
            for offset in range(lower,upper+1):
                offGroup = joinModGroup(group,offset)
                if group == 'Last':
                    offGroup_mtime[offGroup] = dateToTime(lastTime + diffTime*offset)
                else:
                    offGroup_mtime[offGroup] = dateToTime(nextTime)
                    nextTime += diffTime
                bashGroups.append(offGroup)
        deleted = added = 0
        #--Remove invalid group headers
        for offGroup,mod in group_header.items():
            if offGroup not in offGroup_mtime:
                del group_header[offGroup]
                self.delete(mod,False)
                del self.data[mod]
                deleted += 1
        #--Add required group headers
        mod_group = self.table.getColumn('group')
        for offGroup in offGroup_mtime:
            if offGroup not in group_header:
                newName = GPath('++%s%s.esp' % (offGroup.upper(),'='*(25-len(offGroup))))
                if newName not in self.data:
                    newInfo = ModInfo(self.dir,newName)
                    newInfo.mtime = time.time()
                    newFile = ModFile(newInfo,LoadFactory(True))
                    newFile.tes4.masters = [GPath('Oblivion.esm')]
                    newFile.tes4.author = '======'
                    newFile.tes4.description = _('Balo group header.')
                    newFile.safeSave()
                    self[newName] = newInfo
                mod_group[newName] = offGroup
                group_header[offGroup] = newName
                added += 1
        #--Set header mtimes
        for offGroup,mtime in offGroup_mtime.iteritems():
            mod = group_header[offGroup]
            modInfo = self[mod]
            if modInfo.mtime != mtime:
                modInfo.setmtime(mtime)
        #--Done
        #delist('mods',[x.s for x in sorted(self.data.keys()])
        return bool(deleted + added)

    def getBaloGroups(self,editable=False):
        """Returns current balo groups. If not defined yet, returns default groups.
        Groups is list of entries, where entries are (groupName,lower,upper)."""
        none = ('NONE',0,0)
        last = ('Last',-1,1)
        #--Already defined?
        if 'bash.balo.groups' in settings:
            groupInfos = list(settings['bash.balo.groups'])
        #--Anchor groups defined?
        elif self.group_header:
            deprint('by self.group_header')
            group_bounds = {}
            group_mtime = {}
            for offGroup,header in self.group_header.iteritems():
                group,offset = splitModGroup(offGroup)
                bounds = group_bounds.setdefault(group,[0,0])
                if offset < bounds[0]: bounds[0] = offset
                if offset > bounds[1]: bounds[1] = offset
                group_mtime[group] = self[header].mtime
            group_bounds.pop('NONE',None)
            lastBounds = group_bounds.pop('Last',None)
            if lastBounds:
                last = ('Last',lastBounds[0],lastBounds[1])
            groupInfos = [(g,x,y) for g,(x,y) in group_bounds.iteritems()]
            groupInfos.sort(key=lambda a: group_mtime[a[0]])
        #--Default
        else:
            groupInfos = []
            for entry in bush.baloGroups:
                if entry[0] == 'Last': continue
                elif len(entry) == 1: entry += (0,0)
                elif len(entry) == 2: entry += (0,)
                groupInfos.append((entry[0],entry[2],entry[1]))
            groupInfos.append(('NONE',0,0))
            groupInfos.append(('Last',-1,1))
        #--None, Last Groups
        if groupInfos[-1][0] == 'Last':
            last = groupInfos.pop()
        if groupInfos[-1][0] == 'NONE':
            groupInfos.pop()
        groupInfos.append(none)
        groupInfos.append(last)
        #--Editable?
        if editable:
            headers = set(self.group_header.values())
            groupInfos = [[x,y,z,0,0,x] for x,y,z in groupInfos]
            group_info = dict((x[0],x) for x in groupInfos)
            mod_group = self.table.getColumn('group')
            #--Get range offsets actually in use by non-headers.
            for mod in self.data:
                if mod in headers: continue #--Ignore header mods
                group,offset = splitModGroup(mod_group.get(mod))
                if group not in group_info: continue
                info = group_info[group]
                info[3] = min(info[3],offset)
                info[4] = max(info[4],offset+1)
            #--Rationalize offset bounds (just in case)
            for info in groupInfos:
                info[1] = min(info[1],info[3])
                info[2] = max(info[2],info[4]-1)
        #--Done
        #delist('groupInfos',groupInfos)
        return groupInfos

    def setBaloGroups(self,groupInfos,removed):
        """Applies and remembers set of balo groups."""
        renames = dict((x[0],x[5]) for x in groupInfos if (x[0] and x[0] != x[5]))
        group_range = dict((x[5],(x[1],x[2])) for x in groupInfos)
        mod_group = self.table.getColumn('group')
        headers = set(self.group_header.values())
        #delist('renames',renames)
        #delist('group_range',group_range)
        #--Renamed/Deleted groups
        for mod in self.table.keys():
            offGroup = mod_group.get(mod)
            group,offset = splitModGroup(offGroup)
            newGroup = renames.get(group,group)
            if group in removed or newGroup not in group_range:
                if mod in headers: continue #--Will be deleted by autoSort().
                mod_group[mod] = '' #--Will be set by self.autoGroup()
            elif group != newGroup:
                mod_group[mod] = joinModGroup(newGroup,offset)
        #--Constrain to range
        for mod in self.table.keys():
            if mod in headers: continue
            offGroup = mod_group.get(mod)
            group,offset = splitModGroup(offGroup)
            if not group: continue
            lower,upper = group_range[group]
            if offset < lower or offset > upper:
                mod_group[mod] = '' #--Will be set by self.autoGroup()
        #--Save and autosort
        settings['bosh.modInfos.resetMTimes'] = self.lockTimes = True
        settings['bash.balo.full'] = self.fullBalo = True
        settings['bash.balo.groups'] = [(x[5],x[1],x[2]) for x in groupInfos]

    #--Mod selection ----------------------------------------------------------
    def circularMasters(self,stack,masters=None):
        stackTop = stack[-1]
        masters = masters or (stackTop in self.data and self.data[stackTop].masterNames)
        if not masters: return False
        for master in masters:
            if master in stack:
                return True
            if self.circularMasters(stack+[master]):
                return True
        return False

    def getOrdered(self,modNames,asTuple=True):
        """Sort list of mod names into their load order."""
        data = self.data
        modNames = list(modNames) #--Don't do an in-place sort.
        modNames.sort()
        modNames.sort(key=lambda a: (a in data) and data[a].mtime) #--Sort on modified
        modNames.sort(key=lambda a: a.cs[-1]) #--Sort on esm/esp
        if asTuple: return tuple(modNames)
        else: return modNames

    def getSemiActive(self,masters):
        """Returns (merged,imported) mods made semi-active by Bashed Patch."""
        merged,imported,nullDict = set(),set(),{}
        for modName,modInfo in [(modName,self[modName]) for modName in masters]:
            if modInfo.header.author != 'BASHED PATCH': continue
            patchConfigs = self.table.getItem(modName,'bash.patch.configs',None)
            if not patchConfigs: continue
            if patchConfigs.get('PatchMerger',nullDict).get('isEnabled'):
                configChecks = patchConfigs['PatchMerger']['configChecks']
                for modName in configChecks:
                    if configChecks[modName]: merged.add(modName)
            imported.update(patchConfigs.get('ImportedMods',tuple()))
        return (merged,imported)

    def selectExact(self,modNames):
        """Selects exactly the specified set of mods."""
        del self.plugins.selected[:]
        missing,extra = [],[]
        modSet = set(self.keys())
        for modName in modNames:
            if modName not in self:
                missing.append(modName)
                continue
            try:
                self.select(modName,False,modSet)
            except PluginsFullError:
                extra.append(modName)
        #--Save
        self.refreshInfoLists()
        self.plugins.save()
        self.autoGhost()
        #--Done/Error Message
        if missing or extra:
            message = ''
            if missing:
                message += _("Some mods were unavailable and were skipped:\n* ")
                message += '\n* '.join(x.s for x in missing)
            if extra:
                if missing: message += '\n'
                message += _("Mod list is full, so some mods were skipped:\n")
                message += '\n* '.join(x.s for x in extra)
            return message
        else:
            return None

    def getModList(self,fileInfo=None,wtxt=False):
        """Returns mod list as text. If fileInfo is provided will show mod list
        for its masters. Otherwise will show currently loaded mods."""
        #--Setup
        log = bolt.LogFile(cStringIO.StringIO())
        head = ('','=== ')[wtxt]
        bul = ('','* ')[wtxt]
        sMissing = (_('----> MISSING MASTER: '),_('  * __Missing Master:__ '))[wtxt]
        sDelinquent = (_('----> Delinquent MASTER: '),_('  * __Delinquent Master:__ '))[wtxt]
        sImported = ('**','&bull; &bull;')[wtxt]
        if not wtxt: log.out.write('[codebox]')
        if fileInfo:
            masters = set(fileInfo.header.masters)
            missing = sorted([x for x in masters if x not in self])
            log.setHeader(head+_('Missing Masters for: ')+fileInfo.name.s)
            for mod in missing:
                log(bul+'xx '+mod.s)
            log.setHeader(head+_('Masters for: ')+fileInfo.name.s)
            present = set(x for x in masters if x in self)
            if fileInfo.name in self: #--In case is bashed patch
                present.add(fileInfo.name)
            merged,imported = self.getSemiActive(present)
        else:
            log.setHeader(head+_('Active Mod Files:'))
            masters = set(self.ordered)
            merged,imported = self.merged,self.imported
        headers = set(mod for mod in self.data if mod.s[0] in '.=+')
        allMods = masters | merged | imported | headers
        allMods = self.getOrdered([x for x in allMods if x in self])
        #--List
        modIndex,header = 0, None
        for name in allMods:
            if name in masters:
                prefix = bul+'%02X' % (modIndex)
                modIndex += 1
            elif name in headers:
                match = re.match('^[\.+= ]*(.*?)\.es[pm]',name.s)
                if match: name = GPath(match.group(1))
                header = bul+'==  ' +name.s
                continue
            elif name in merged:
                prefix = bul+'++'
            else:
                prefix = bul+sImported
            version = self.getVersion(name)
            if header:
                log(header)
                header = None
            if version:
                log(_('%s  %s  [Version %s]') % (prefix,name.s,version))
            else:
                log('%s  %s' % (prefix,name.s))
            if name in masters:
                for master2 in self[name].header.masters:
                    if master2 not in self:
                        log(sMissing+master2.s)
                    elif self.getOrdered((name,master2))[1] == master2:
                        log(sDelinquent+master2.s)
        if not wtxt: log('[/codebox]')
        return bolt.winNewLines(log.out.getvalue())

    #--Mod Specific ----------------------------------------------------------
    def rightFileType(self,fileName):
        """Bool: File is a mod."""
        return reModExt.search(fileName.s)

    #--Refresh File
    def refreshFile(self,fileName):
        try:
            FileInfos.refreshFile(self,fileName)
        finally:
            self.refreshInfoLists()

    def isSelected(self,modFile):
        """True if modFile is selected (active)."""
        return (modFile in self.ordered)

    def select(self,fileName,doSave=True,modSet=None,children=None):
        """Adds file to selected."""
        try:
            plugins = self.plugins
            children = (children or tuple()) + (fileName,)
            if fileName in children[:-1]:
                raise BoltError(_('Circular Masters: ')+' >> '.join(x.s for x in children))
            #--Select masters
            if modSet == None: modSet = set(self.keys())
            for master in self[fileName].header.masters:
                if master in modSet:
                    self.select(master,False,modSet,children)
            #--Select in plugins
            if fileName not in plugins.selected:
                if len(plugins.selected) >= 255:
                    raise PluginsFullError
                plugins.selected.append(fileName)
        finally:
            if doSave:
                plugins.save()
                self.refreshInfoLists()
                self.autoGhost()

    def unselect(self,fileName,doSave=True):
        """Removes file from selected."""
        #--Unselect self
        plugins = self.plugins
        plugins.remove(fileName)
        #--Unselect children
        for selFile in plugins.selected[:]:
            #--Already unselected or missing?
            if not self.isSelected(selFile) or selFile not in self.data:
                continue
            #--One of selFile's masters?
            for master in self[selFile].header.masters:
                if master == fileName:
                    self.unselect(selFile,False)
                    break
        #--Save
        if doSave:
            self.refreshInfoLists()
            plugins.save()
            self.autoGhost()

    def hasTimeConflict(self,modName):
        """True if there is another mod with the same mtime."""
        mtime = self[modName].mtime
        mods = self.mtime_mods.get(mtime,tuple())
        return len(mods) > 1

    def hasActiveTimeConflict(self,modName):
        """True if there is another mod with the same mtime."""
        if not self.isSelected(modName): return False
        mtime = self[modName].mtime
        mods = self.mtime_selected.get(mtime,tuple())
        return len(mods) > 1

    #--Mod move/delete/rename -------------------------------------------------
    def rename(self,oldName,newName):
        """Renames member file from oldName to newName."""
        isSelected = self.isSelected(oldName)
        if isSelected: self.unselect(oldName)
        FileInfos.rename(self,oldName,newName)
        self.refreshInfoLists()
        if isSelected: self.select(newName)

    def delete(self,fileName,doRefresh=True):
        """Deletes member file."""
        self.unselect(fileName)
        FileInfos.delete(self,fileName,doRefresh)

    def move(self,fileName,destDir,doRefresh=True):
        """Moves member file to destDir."""
        self.unselect(fileName)
        FileInfos.move(self,fileName,destDir,doRefresh)

    #--Mod info/modify --------------------------------------------------------
    def getVersion(self,fileName,asFloat=False):
        """Extracts and returns version number for fileName from header.hedr.description."""
        if not fileName in self.data or not self.data[fileName].header:
            return ''
        maVersion = reVersion.search(self.data[fileName].header.description)
        return (maVersion and maVersion.group(2)) or ''

    def getVersionFloat(self,fileName):
        """Extracts and returns version number for fileName from header.hedr.description."""
        version = self.getVersion(fileName)
        maVersion = re.search(r'(\d+\.?\d*)',version)
        if maVersion:
            return float(maVersion.group(1))
        else:
            return 0

    def getRequires(self,fileName):
        """Extracts and returns requirement dictionary for fileName from header.hedr.description."""
        requires = {}
        if not fileName in self.data or not self.data[fileName].header:
            maRequires = reRequires.search(self.data[fileName].header.description)
            if maRequires:
                for item in map(string.strip,maRequires.group(1).split(',')):
                    maReqItem = reReqItem.match(item)
                    key,value = ma
                    if maReqItem:
                        key,value = maReqItem.groups()
                        requires[key] = float(value or 0)
        return requires

    #--Oblivion 1.1/SI Swapping -----------------------------------------------
    def getOblivionVersions(self):
        """Returns tuple of Oblivion versions."""
        reOblivion = re.compile('^Oblivion(|_SI|_1.1).esm$')
        self.voAvailable.clear()
        for name,info in self.data.iteritems():
            maOblivion = reOblivion.match(name.s)
            if maOblivion and info.size in self.size_voVersion:
                self.voAvailable.add(self.size_voVersion[info.size])
        self.voCurrent = self.size_voVersion.get(self.data[GPath('Oblivion.esm')].size,None)

    def setOblivionVersion(self,newVersion):
        """Swaps Oblivion.esm to to specified version."""
        #--Old info
        baseName = GPath('Oblivion.esm')
        newSize = self.version_voSize[newVersion]
        oldSize = self.data[baseName].size
        if newSize == oldSize: return
        if oldSize not in self.size_voVersion:
            raise StateError(_("Can't match current Oblivion.esm to known version."))
        oldName = GPath('Oblivion_'+self.size_voVersion[oldSize]+'.esm')
        if self.dir.join(oldName).exists():
            raise StateError(_("Can't swap: %s already exists.") % oldName)
        newName = GPath('Oblivion_'+newVersion+'.esm')
        if newName not in self.data:
            raise StateError(_("Can't swap: %s doesn't exist.") % newName)
        #--Rename
        baseInfo = self.data[baseName]
        newInfo = self.data[newName]
        basePath = baseInfo.getPath()
        newPath = newInfo.getPath()
        oldPath = self.dir.join(oldName)
        basePath.moveTo(oldPath)
        newPath.moveTo(basePath)
        basePath.mtime = baseInfo.mtime
        oldPath.mtime = newInfo.mtime
        self.mtimes[oldName] = newInfo.mtime
        if newInfo.isGhost:
            oldInfo = ModInfo(self.dir,oldName)
            oldInfo.setGhost(True)
        self.voCurrent = newVersion

    #--Resource Replacers -----------------------------------------------------
    def getResourceReplacers(self):
        """Returns list of ResourceReplacer objects for subdirectories of Replacers directory."""
        replacers = {}
        replacerDir = self.dir.join('Replacers')
        if not replacerDir.exists():
            return replacers
        if 'bosh.resourceReplacer.applied' not in settings:
            settings['bosh.resourceReplacer.applied'] = []
        for name in replacerDir.list():
            path = replacerDir.join(name)
            if path.isdir():
                replacers[name] = ResourceReplacer(replacerDir,name)
        return replacers

#------------------------------------------------------------------------------
class SaveInfos(FileInfos):
    """SaveInfo collection. Represents save directory and related info."""
    #--Init
    def __init__(self):
        self.iniMTime = 0
        self.refreshLocalSave()
        FileInfos.__init__(self,self.dir,SaveInfo)
        self.profiles = bolt.Table(PickleDict(
            dirs['saveBase'].join('BashProfiles.dat'),
            dirs['userApp'].join('Profiles.pkl')))
        self.table = bolt.Table(PickleDict(self.bashDir.join('Table.dat')))

    #--Right File Type (Used by Refresh)
    def rightFileType(self,fileName):
        """Bool: File is a mod."""
        return reSaveExt.search(fileName.s)

    def refresh(self):
        if self.refreshLocalSave():
            self.data.clear()
            self.table.save()
            self.table = bolt.Table(PickleDict(
                self.bashDir.join('Table.dat'),
                self.bashDir.join('Table.pkl')))
        return FileInfos.refresh(self)

    def delete(self,fileName):
        """Deletes savefile and associated pluggy file."""
        FileInfos.delete(self,fileName)
        CoSaves(self.dir,fileName).delete()

    def rename(self,oldName,newName):
        """Renames member file from oldName to newName."""
        FileInfos.rename(self,oldName,newName)
        CoSaves(self.dir,oldName).move(self.dir,newName)

    def copy(self,fileName,destDir,destName=None,mtime=False):
        """Copies savefile and associated pluggy file."""
        FileInfos.copy(self,fileName,destDir,destName,mtime)
        CoSaves(self.dir,fileName).copy(destDir,destName or fileName)

    def move(self,fileName,destDir,doRefresh=True):
        """Moves member file to destDir. Will overwrite!"""
        FileInfos.move(self,fileName,destDir,doRefresh)
        CoSaves(self.dir,fileName).move(destDir,fileName)

    #--Local Saves ------------------------------------------------------------
    def getLocalSaveDirs(self):
        """Returns a list of possible local save directories, NOT including the base directory."""
        baseSaves = dirs['saveBase'].join('Saves')
        if baseSaves.exists():
            localSaveDirs = [x for x in baseSaves.list() if (x != 'Bash' and baseSaves.join(x).isdir())]
        else:
            localSaveDirs = []
        localSaveDirs.sort()
        return localSaveDirs

    def refreshLocalSave(self):
        """Refreshes self.localSave and self.dir."""
        #--self.localSave is NOT a Path object.
        self.localSave = getattr(self,'localSave','Saves\\')
        self.dir = dirs['saveBase'].join(self.localSave)
        self.bashDir = self.getBashDir()
        if oblivionIni.path.exists() and (oblivionIni.path.mtime != self.iniMTime):
            self.localSave = oblivionIni.getSetting('General','SLocalSavePath','Saves\\')
            self.iniMTime = oblivionIni.path.mtime
            return True
        else:
            return False

    def setLocalSave(self,localSave):
        """Sets SLocalSavePath in Oblivion.ini."""
        self.table.save()
        self.localSave = localSave
        oblivionIni.saveSetting('General','SLocalSavePath',localSave)
        self.iniMTime = oblivionIni.path.mtime
        bashDir = dirs['saveBase'].join(localSave,'Bash')
        self.table = bolt.Table(PickleDict(bashDir.join('Table.dat')))
        self.refresh()

    #--Enabled ----------------------------------------------------------------
    def isEnabled(self,fileName):
        """True if fileName is enabled)."""
        return (fileName.cext == '.ess')

    def enable(self,fileName,value=True):
        """Enables file by changing extension to 'ess' (True) or 'esr' (False)."""
        isEnabled = self.isEnabled(fileName)
        if isEnabled or value == isEnabled or re.match('(autosave|quicksave)',fileName.s,re.I):
            return fileName
        (root,ext) = fileName.rootExt
        newName = root + ((value and '.ess') or '.esr')
        self.rename(fileName,newName)
        return newName

#------------------------------------------------------------------------------
class BSAInfos(FileInfos):
    """SaveInfo collection. Represents save directory and related info."""
    #--Init
    def __init__(self):
        self.iniMTime = 0
        self.dir = dirs['mods']
        FileInfos.__init__(self,self.dir,BSAInfo)
        self.profiles = bolt.Table(PickleDict(
            dirs['saveBase'].join('BashProfiles.dat'),
            dirs['userApp'].join('Profiles.pkl')))
        self.table = bolt.Table(PickleDict(self.bashDir.join('Table.dat')))

    #--Right File Type (Used by Refresh)
    def rightFileType(self,fileName):
        """Bool: File is a mod."""
        return reBSAExt.search(fileName.s)

    def refresh(self):
        if self.refreshLocalSave():
            self.data.clear()
            self.table.save()
            self.table = bolt.Table(PickleDict(
                self.bashDir.join('Table.dat'),
                self.bashDir.join('Table.pkl')))
        return FileInfos.refresh(self)

    def delete(self,fileName):
        """Deletes savefile and associated pluggy file."""
        FileInfos.delete(self,fileName)
        CoSaves(self.dir,fileName).delete()

    def rename(self,oldName,newName):
        """Renames member file from oldName to newName."""
        FileInfos.rename(self,oldName,newName)
        CoSaves(self.dir,oldName).move(self.dir,newName)

    def copy(self,fileName,destDir,destName=None,mtime=False):
        """Copies savefile and associated pluggy file."""
        FileInfos.copy(self,fileName,destDir,destName,mtime)
        CoSaves(self.dir,fileName).copy(destDir,destName or fileName)

    def move(self,fileName,destDir,doRefresh=True):
        """Moves member file to destDir. Will overwrite!"""
        FileInfos.move(self,fileName,destDir,doRefresh)
        CoSaves(self.dir,fileName).move(destDir,fileName)

    #--Local Saves ------------------------------------------------------------
    def getLocalSaveDirs(self):
        """Returns a list of possible local save directories, NOT including the base directory."""
        baseSaves = dirs['saveBase'].join('Saves')
        if baseSaves.exists():
            localSaveDirs = [x for x in baseSaves.list() if (x != 'Bash' and baseSaves.join(x).isdir())]
        else:
            localSaveDirs = []
        localSaveDirs.sort()
        return localSaveDirs

    def refreshLocalSave(self):
        """Refreshes self.localSave and self.dir."""
        #--self.localSave is NOT a Path object.
    #    self.localSave = getattr(self,'localSave','Saves\\')
        self.dir = dirs['mods']
        self.bashDir = self.getBashDir()
    #    if oblivionIni.path.exists() and (oblivionIni.path.mtime != self.iniMTime):
    #        self.localSave = oblivionIni.getSetting('General','SLocalSavePath','Saves\\')
    #        self.iniMTime = oblivionIni.path.mtime
    #    else:
    #        return False
        return True

    def setLocalSave(self,localSave):
        """Sets SLocalSavePath in Oblivion.ini."""
        self.table.save()
        self.localSave = localSave
        oblivionIni.saveSetting('General','SLocalSavePath',localSave)
        self.iniMTime = oblivionIni.path.mtime
        bashDir = dirs['saveBase'].join(localSave,'Bash')
        self.table = bolt.Table(PickleDict(bashDir.join('Table.dat')))
        self.refresh()

    #--Enabled ----------------------------------------------------------------
    def isEnabled(self,fileName):
        """True if fileName is enabled)."""
        return (fileName.cext == '.ess')

    def enable(self,fileName,value=True):
        """Enables file by changing extension to 'ess' (True) or 'esr' (False)."""
        isEnabled = self.isEnabled(fileName)
        if isEnabled or value == isEnabled or re.match('(autosave|quicksave)',fileName.s,re.I):
            return fileName
        (root,ext) = fileName.rootExt
        newName = root + ((value and '.ess') or '.esr')
        self.rename(fileName,newName)
        return newName

#------------------------------------------------------------------------------
class ReplacersData(DataDict):
    def __init__(self):
        """Initialize."""
        self.dir = dirs['mods'].join("Replacers")
        self.data = {}

    #--Refresh
    def refresh(self):
        """Refresh list of screenshots."""
        newData = modInfos.getResourceReplacers()
        changed = (set(self.data) != set(newData))
        self.data = newData
        return changed

# Mod Config Help -------------------------------------------------------------
#------------------------------------------------------------------------------
class ModRuleSet:
    """A set of rules to be used in analyzing active and/or merged mods for errors."""

    class ModGroup:
        """A set of specific mods and rules that affect them."""
        def __init__(self):
            self.modAnds = []
            self.modNots = []
            self.notes = ''
            self.config = []
            self.suggest = []
            self.warn = []

        def hasRules(self):
            return bool(self.notes or self.config or self.suggest or self.warn)

        def isActive(self,actives):
            """Determines if modgroup is active based on its set of mods."""
            if not self.modAnds: return False
            for modNot,mods in zip(self.modNots,self.modAnds):
                if modNot:
                    for mod in mods:
                        if mod in actives: return False
                else:
                    for mod in mods:
                        if mod in actives: break
                    else: return False
            return True

        def getActives(self,actives):
            """Returns list of active mods."""
            out = []
            for modNot,mods in zip(self.modNots,self.modAnds):
                for mod in mods:
                    if mod in actives:
                        out.append(mod)
            return out

    class RuleParser:
        """A class for parsing ruleset files."""
        ruleBlockIds = ('NOTES','CONFIG','SUGGEST','WARN')
        reComment = re.compile(r'##.*')
        reBlock   = re.compile(r'^>>\s+([A-Z]+)\s*(.*)')
        reMod     = re.compile(r'\s*([\-\|]?)(.+?\.es[pm])(\s*\[[^\]]\])?',re.I)
        reRule    = re.compile(r'^(x|o|\+|-|-\+)\s+([^/]+)\s*(\[[^\]]+\])?\s*//(.*)')
        reExists  = re.compile(r'^(e)\s+([^/]+)//(.*)')
        reModVersion = re.compile(r'(.+\.es[pm])\s*(\[[^\]]+\])?',re.I)

        def __init__(self,ruleSet):
            self.ruleSet = ruleSet
            #--Temp storage while parsing.
            self.assumed = []
            self.assumedNot = []
            self.curBlockId = None
            self.curDefineId = None
            self.mods = []
            self.modNots = []
            self.group = ModRuleSet.ModGroup()
            self.define = None

        def newBlock(self,newBlock=None):
            """Handle new blocks, finishing current block if present."""
            #--Subblock of IF block?
            if newBlock in self.ruleBlockIds:
                self.curBlockId = newBlock
                return
            curBlockId = self.curBlockId
            group = self.group
            if curBlockId != None:
                if curBlockId == 'HEADER':
                    self.ruleSet.header = self.ruleSet.header.rstrip()
                elif curBlockId == 'ONLYONE':
                    self.ruleSet.onlyones.append(set(self.mods))
                elif curBlockId == 'ASSUME':
                    self.assumed = self.mods[:]
                    self.assumedNot = self.modNots[:]
                elif curBlockId in self.ruleBlockIds and self.mods and group.hasRules():
                    group.notes = group.notes.rstrip()
                    group.modAnds = self.assumed + self.mods
                    group.modNots = self.assumedNot + self.modNots
                    self.ruleSet.modGroups.append(group)
            self.curBlockId = newBlock
            self.curDefineId = None
            del self.mods[:]
            del self.modNots[:]
            self.group = ModRuleSet.ModGroup()

        def addGroupRule(self,op,mod,comment):
            """Adds a new rule to the modGroup."""
            maModVersion = self.reModVersion.match(mod)
            if not maModVersion: return
            getattr(self.group,self.curBlockId.lower()).append((op,GPath(maModVersion.group(1)),comment))

        def parse(self,rulePath):
            """Parse supplied ruleset."""
            #--Constants
            reComment = self.reComment
            reBlock   = self.reBlock
            reMod     = self.reMod
            reRule    = self.reRule
            reExists  = self.reExists
            reModVersion = self.reModVersion
            ruleSet   = self.ruleSet

            #--Clear info
            ruleSet.mtime = rulePath.mtime
            ruleSet.header = ''
            del ruleSet.onlyones[:]
            del ruleSet.modGroups[:]

            def stripped(list):
                return [(x or '').strip() for x in list]

            ins = rulePath.open('r')
            for line in ins:
                line = reComment.sub('',line)
                maBlock = reBlock.match(line)
                #--Block changers
                if maBlock:
                    newBlock,extra = stripped(maBlock.groups())
                    self.newBlock(newBlock)
                    if newBlock == 'HEADER':
                        self.ruleSet.header = (extra or '')+'\n'
                    elif newBlock in ('ASSUME','IF'):
                        maModVersion = reModVersion.match(extra or '')
                        if extra and reModVersion.match(extra):
                            self.mods = [[GPath(reModVersion.match(extra).group(1))]]
                            self.modNots = [False]
                        else:
                            self.mods = []
                            self.modNots = []
                #--Block lists
                elif self.curBlockId == 'HEADER':
                    self.ruleSet.header += line.rstrip()+'\n'
                elif self.curBlockId in ('IF','ASSUME'):
                    maMod = reMod.match(line)
                    if maMod:
                        op,mod,version = stripped(maMod.groups())
                        mod = GPath(mod)
                        if op == '|':
                            self.mods[-1].append(mod)
                        else:
                            self.mods.append([mod])
                            self.modNots.append(op == '-')
                elif self.curBlockId  == 'ONLYONE':
                    maMod = reMod.match(line)
                    if maMod:
                        if maMod.group(1): raise BoltError(
                            _("ONLYONE does not support %s operators.") % maMod.group(1))
                        self.mods.append(GPath(maMod.group(2)))
                elif self.curBlockId == 'NOTES':
                    self.group.notes += line.rstrip()+'\n'
                elif self.curBlockId in self.ruleBlockIds:
                    maRule = reRule.match(line)
                    maExists = reExists.match(line)
                    if maRule:
                        op,mod,version,text = maRule.groups()
                        self.addGroupRule(op,mod,text)
                    elif maExists and '..' not in maExists.groups(2):
                        self.addGroupRule(*stripped(maExists.groups()))
            self.newBlock(None)
            ins.close()

    #--------------------------------------------------------------------------
    def __init__(self):
        """Initialize ModRuleSet."""
        self.mtime = 0
        self.header = ''
        self.defineKeys = []
        self.onlyones = []
        self.modGroups = []

#------------------------------------------------------------------------------
class ConfigHelpers:
    """Encapsulates info from mod configuration helper files (BOSS masterlist, etc.)"""

    def __init__(self):
        """Initialialize."""
        #--Bash Patches\Leveled Lists.csv
        self.patchesLLPath = dirs['patches'].join('Leveled Lists.csv')
        self.patchesLLTime = 0
        self.patchesLLTags = {}
        #--Boss Master List
        self.bossMasterPath = dirs['mods'].join('masterlist.txt')
        self.bossMasterTime = 0
        self.bossMasterTags = {}
        #--Mod Rules
        self.name_ruleSet = {}

    def refresh(self):
        """Reloads tag info if file dates have changed."""
        #--Bash Patches\Leveled Lists.csv
        path,mtime,tags = (self.patchesLLPath, self.patchesLLTime, self.patchesLLTags,)
        if path.exists() and path.mtime != mtime:
            tags.clear()
            mapper = {'D':'Delev','R':'Relev'}
            reader = bolt.CsvReader(path)
            for fields in reader:
                if len(fields) >= 2 and fields[0] and fields[1] in ('DR','R','D','RD',''):
                    tags[GPath(fields[0])] = tuple(mapper[x] for x in fields[1])
            reader.close()
            self.patchesLLTime = path.mtime
        #--Boss Master List
        path,mtime,tags = (self.bossMasterPath, self.bossMasterTime, self.bossMasterTags,)
        if path.exists() and path.mtime != mtime:
            tags.clear()
            ins = path.open('r')
            mod = None
            reFcomSwitch = re.compile('^[<>]')
            reComment = re.compile(r'^\\.*')
            reMod = re.compile(r'(\w.*?\.es[pm])',re.I)
            reBashTags = re.compile(r'%\s+{{BASH:([^}]+)}')
            for line in ins:
                line = reFcomSwitch.sub('',line)
                line = reComment.sub('',line)
                maMod = reMod.match(line)
                maBashTags = reBashTags.match(line)
                if maMod:
                    mod = maMod.group(1)
                elif maBashTags and mod:
                    modTags = maBashTags.group(1).split(',')
                    modTags = map(string.strip,modTags)
                    tags[GPath(mod)] = tuple(modTags)
            ins.close()
            self.bossMasterTime = path.mtime

    def getBashTags(self,modName):
        """Retrieves bash tags for given file."""
        if modName in self.bossMasterTags:
            return set(self.bossMasterTags[modName])
        if modName in self.patchesLLTags:
            return set(self.patchesLLTags[modName])

    #--Mod Checker ------------------------------------------------------------
    def refreshRuleSets(self):
        """Reloads ruleSets if file dates have changed."""
        name_ruleSet = self.name_ruleSet
        reRulesFile = re.compile('Rules.txt$',re.I)
        ruleFiles = set(x for x in dirs['patches'].list() if reRulesFile.search(x.s))
        for name in name_ruleSet.keys():
            if name not in ruleFiles: del name_ruleSet[name]
        for name in ruleFiles:
            path = dirs['patches'].join(name)
            ruleSet = name_ruleSet.get(name)
            if not ruleSet:
                ruleSet = name_ruleSet[name] = ModRuleSet()
            if path.mtime != ruleSet.mtime:
                ModRuleSet.RuleParser(ruleSet).parse(path)

    def checkMods(self,showModList=False,showNotes=False,showConfig=True,showSuggest=True,showWarn=True):
        """Checks currently loaded mods against ruleset."""
        active = set(modInfos.ordered)
        merged = modInfos.merged
        imported = modInfos.imported
        activeMerged = active | merged
        warning = _('=== <font color=red>WARNING:</font> ')
        #--Header
        log = bolt.LogFile(cStringIO.StringIO())
        log.setHeader(_('= Check Mods'),True)
        log(_("This is a report on your currently active/merged mods."))
        #--Mergeable
        shouldMerge = active & modInfos.mergeable
        for mod in tuple(shouldMerge):
            if 'NoMerge' in modInfos[mod].getBashTags():
                shouldMerge.discard(mod)
        if shouldMerge:
            log.setHeader(_("=== Mergeable"))
            log(_("Following mods are active, but could be merged into the bashed patch."))
            for mod in sorted(shouldMerge):
                log('* __'+mod.s+'__')
        #--Missing/Delinquent Masters
        if showModList:
            log('\n'+modInfos.getModList(wtxt=True).strip())
        else:
            log.setHeader(warning+_('Missing/Delinquent Masters'))
            previousMods = set()
            for mod in modInfos.ordered:
                loggedMod = False
                for master in modInfos[mod].header.masters:
                    if master not in active:
                        label = _('MISSING')
                    elif master not in previousMods:
                        label = _('DELINQUENT')
                    else:
                        label = ''
                    if label:
                        if not loggedMod:
                            log('* '+mod.s)
                            loggedMod = True
                        log('  * __%s__ %s' %(label,master.s))
                previousMods.add(mod)
        #--Rule Sets
        self.refreshRuleSets()
        for fileName in sorted(self.name_ruleSet):
            ruleSet = self.name_ruleSet[fileName]
            modRules = ruleSet.modGroups
            log.setHeader('= ' + fileName.s[:-4],True)
            if ruleSet.header: log(ruleSet.header)
            #--One ofs
            for modSet in ruleSet.onlyones:
                modSet &= activeMerged
                if len(modSet) > 1:
                    log.setHeader(warning+_('Only one of these should be active/merged'))
                    for mod in sorted(modSet):
                        log('* '+mod.s)
            #--Mod Rules
            for modGroup in ruleSet.modGroups:
                if not modGroup.isActive(activeMerged): continue
                modList = ' + '.join([x.s for x in modGroup.getActives(activeMerged)])
                if showNotes and modGroup.notes:
                    log.setHeader(_('=== NOTES: ') + modList )
                    log(modGroup.notes)
                if showConfig:
                    log.setHeader(_('=== CONFIGURATION: ') + modList )
                    #    + _('\nLegend: x: Active, +: Merged, -: Inactive'))
                    for ruleType,ruleMod,comment in modGroup.config:
                        if ruleType != 'o': continue
                        if ruleMod in active: bullet = 'x'
                        elif ruleMod in merged: bullet = '+'
                        elif ruleMod in imported: bullet = '*'
                        else: bullet = 'o'
                        log(_('%s __%s__ -- %s') % (bullet,ruleMod.s,comment))
                if showSuggest:
                    log.setHeader(_('=== SUGGESTIONS: ') + modList)
                    for ruleType,ruleMod,comment in modGroup.suggest:
                        if ((ruleType == 'x' and ruleMod not in activeMerged) or
                            (ruleType == '+' and (ruleMod in active or ruleMod not in merged)) or
                            (ruleType == '-' and ruleMod in activeMerged) or
                            (ruleType == '-+' and ruleMod in active)
                            ):
                            log(_('* __%s__ -- %s') % (ruleMod.s,comment))
                        elif ruleType == 'e' and not dirs['mods'].join(ruleMod).exists():
                            log('* '+comment)
                if showWarn:
                    log.setHeader(warning + modList)
                    for ruleType,ruleMod,comment in modGroup.warn:
                        if ((ruleType == 'x' and ruleMod not in activeMerged) or
                            (ruleType == '+' and (ruleMod in active or ruleMod not in merged)) or
                            (ruleType == '-' and ruleMod in activeMerged) or
                            (ruleType == '-+' and ruleMod in active)
                            ):
                            log(_('* __%s__ -- %s') % (ruleMod.s,comment))
                        elif ruleType == 'e' and not dirs['mods'].join(ruleMod).exists():
                            log('* '+comment)
        return log.out.getvalue()

# TankDatas -------------------------------------------------------------------
#------------------------------------------------------------------------------
class PickleTankData:
    """Mix in class for tank datas built on PickleDicts."""
    def __init__(self,path):
        """Initialize. Definite data from pickledict."""
        self.dictFile = PickleDict(path)
        self.data = self.dictFile.data
        self.hasChanged = False
        self.loaded = False

    def setChanged(self,hasChanged=True):
        """Mark as having changed."""
        self.hasChanged = hasChanged

    def refresh(self):
        """Refresh data."""
        if self.loaded:
            return False
        else:
            self.dictFile.load()
            self.loaded = True
            return True

    def save(self):
        """Saves to pickle file."""
        if self.hasChanged:
            self.dictFile.save()
            self.hasChanged = False

#------------------------------------------------------------------------------
class Messages(DataDict):
    """PM message archive."""
    def __init__(self):
        """Initialize."""
        self.dictFile = PickleDict(dirs['saveBase'].join('Messages.dat'))
        self.data = self.dictFile.data #--data[hash] = (subject,author,date,text)
        self.hasChanged = False
        self.loaded = False

    def refresh(self):
        if not self.loaded:
            self.dictFile.load()
            if len(self.data) == 1 and 'data' in self.data:
                realData = self.data['data']
                self.data.clear()
                self.data.update(realData)
            self.loaded = True

    def save(self):
        """Saves to pickle file."""
        self.dictFile.save()
        self.hasChanged = False

    def delete(self,key):
        """Delete entry."""
        del self.data[key]
        self.hasChanged = True

    def search(self,term):
        """Search entries for term."""
        term = term.strip()
        if not term: return None
        items = []
        reTerm = re.compile(term,re.I)
        for key,(subject,author,date,text) in self.data.iteritems():
            if (reTerm.search(subject) or
                reTerm.search(author) or
                reTerm.search(text)
                ):
                items.append(key)
        return items

    def writeText(self,path,*keys):
        """Return html text for each key."""
        out = path.open('w')
        out.write(bush.messagesHeader)
        for key in keys:
            out.write(self.data[key][3])
            out.write('\n<br />')
        out.write("\n</div></body></html>")
        out.close()

    def importArchive(self,path):
        """Import archive file into data."""
        #--Today, yesterday handling
        maPathDate = re.match(r'(\d+)\.(\d+)\.(\d+)',path.stail)
        dates = {'today':None,'yesterday':None,'previous':None}
        if maPathDate:
            year,month,day = map(int,maPathDate.groups())
            if year < 100: year = 2000+year
            dates['today'] = datetime.datetime(year,month,day)
            dates['yesterday'] = dates['today'] - datetime.timedelta(1)
        reRelDate = re.compile(r'(Today|Yesterday), (\d+):(\d+) (AM|PM)')
        reAbsDate = re.compile(r'(\w+) (\d+) (\d+), (\d+):(\d+) (AM|PM)')
        month_int = dict((x,i+1) for i,x in
            enumerate('Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec'.split(',')))
        def getTime(sentOn):
            maRelDate = reRelDate.search(sentOn)
            if not maRelDate:
                #date = time.strptime(sentOn,'%b %d %Y, %I:%M %p')[:-1]+(0,)
                maAbsDate = reAbsDate.match(sentOn)
                month,day,year,hour,minute,ampm = maAbsDate.groups()
                day,year,hour,minute = map(int,(day,year,hour,minute))
                month = month_int[month]
                hour = (hour,0)[hour==12] + (0,12)[ampm=='PM']
                date = (year,month,day,hour,minute,0,0,0,0)
                dates['previous'] = datetime.datetime(year,month,day)
            else:
                if not dates['yesterday']:
                    dates['yesterday'] = dates['previous'] + datetime.timedelta(1)
                    dates['today'] = dates['yesterday'] + datetime.timedelta(1)
                strDay,hour,minute,ampm = maRelDate.groups()
                hour,minute = map(int,(hour,minute))
                hour = (hour,0)[hour==12] + (0,12)[ampm=='PM']
                ymd = dates[strDay.lower()]
                date = ymd.timetuple()[0:3]+(hour,minute,0,0,0,0)
            return time.mktime(date)
        #--Html entity substitution
        from htmlentitydefs import name2codepoint
        def subHtmlEntity(match):
            entity = match.group(2)
            if match.group(1) == "#":
                return unichr(int(entity)).encode()
            else:
                cp = name2codepoint.get(entity)
                if cp:
                    return unichr(cp).encode()
                else:
                    return match.group()
        #--Re's
        reHtmlEntity = re.compile("&(#?)(\d{1,5}|\w{1,8});")
        reBody         = re.compile('<body>')
        reWrapper      = re.compile('<div id=["\']ipbwrapper["\']>') #--Will be removed
        reMessage      = re.compile('<div class="borderwrapm">')
        reMessageOld   = re.compile("<div class='tableborder'>")
        reTitle        = re.compile('<div class="maintitle">PM: (.+)</div>')
        reTitleOld     = re.compile('<div class=\'maintitle\'><img[^>]+>&nbsp;')
        reSignature    = re.compile('<div class="formsubtitle">')
        reSignatureOld = re.compile('<div class=\'pformstrip\'>')
        reSent         = re.compile('Sent (by|to) <b>(.+)</b> on (.+)</div>')
        #--Final setup, then parse the file
        (HEADER,BODY,MESSAGE) = range(3)
        mode = HEADER
        buff = None
        subject = "<No Subject>"
        ins = path.open()
        for line in ins:
            line = reMessageOld.sub('<div class="borderwrapm">',line)
            line = reTitleOld.sub('<div class="maintitle">',line)
            line = reSignatureOld.sub('<div class="formsubtitle">',line)
            #print mode,'>>',line,
            if mode == HEADER: #--header
                if reBody.search(line):
                    mode = BODY
            elif mode == BODY:
                if reMessage.search(line):
                    subject = "<No Subject>"
                    buff = cStringIO.StringIO()
                    buff.write(reWrapper.sub('',line))
                    mode = MESSAGE
            elif mode == MESSAGE:
                if reTitle.search(line):
                    subject = reTitle.search(line).group(1)
                    subject = reHtmlEntity.sub(subHtmlEntity,subject)
                    buff.write(line)
                elif reSignature.search(line):
                    maSent = reSent.search(line)
                    if maSent:
                        direction = maSent.group(1)
                        author = maSent.group(2)
                        date = getTime(maSent.group(3))
                        messageKey = '::'.join((subject,author,`int(date)`))
                        newSent = 'Sent %s <b>%s</b> on %s</div>' % (direction,
                            author,time.strftime('%b %d %Y, %I:%M %p',time.localtime(date)))
                        line = reSent.sub(newSent,line,1)
                        buff.write(line)
                        self.data[messageKey] = (subject,author,date,buff.getvalue())
                    buff.close()
                    buff = None
                    mode = BODY
                else:
                    buff.write(line)
        ins.close()
        self.hasChanged = True
        self.save()

#------------------------------------------------------------------------------
class ModBaseData(PickleTankData, bolt.TankData, DataDict):
    """Mod database. (IN DEVELOPMENT.)
    The idea for this is to provide a mod database. However, I might not finish this."""

    def __init__(self):
        """Initialize."""
        bolt.TankData.__init__(self,settings)
        PickleTankData.__init__(self,dirs['saveBase'].join('ModBase.dat'))
        #--Default settings. Subclasses should define these.
        self.tankKey = 'bash.modBase'
        self.tankColumns = ['Package','Author','Version','Tags']
        self.title = _('ModBase')
        self.defaultParam('columns',self.tankColumns[:])
        self.defaultParam('colWidths',{'Package':60,'Author':30,'Version':20})
        self.defaultParam('colAligns',{})

    #--Collection
    def getSorted(self,column,reverse):
        """Returns items sorted according to column and reverse."""
        data = self.data
        items = data.keys()
        if column == 'Package':
            items.sort(key=string.lower,reverse=reverse)
        else:
            iColumn = self.tankColumns.index(column) #--Column num for Version, tags
            items.sort(key=string.lower)
            items.sort(key=lambda x: data[x][iColumn],reverse=reverse)
        return items

    #--Item Info
    def getColumns(self,item=None):
        """Returns text labels for item or for row header if item == None.
        NOTE: Assumes fixed order of columns!"""
        if item is None:
            return self.tankColumns[:]
        else:
            author,version,karma,tags = self.data[item][1:5]
            return (item,author,version,tags)

    def getName(self,item):
        """Returns a string name of item for use in dialogs, etc."""
        return item

    def getGuiKeys(self,item):
        """Returns keys for icon and text and background colors."""
        textKey = backKey = None
        iconKey = 'karma%+d' % self.data[item][1]
        return (iconKey,textKey,backKey)

#------------------------------------------------------------------------------
class PeopleData(PickleTankData, bolt.TankData, DataDict):
    """Data for a People Tank."""
    def __init__(self):
        """Initialize."""
        bolt.TankData.__init__(self,settings)
        PickleTankData.__init__(self,dirs['saveBase'].join('People.dat'))
        #--Default settings. Subclasses should define these.
        self.tankKey = 'bash.people'
        self.tankColumns = ['Name','Karma','Header']
        self.title = _('People')
        self.defaultParam('columns',self.tankColumns[:])
        self.defaultParam('colWidths',{'Name':60,'Karma':20})
        self.defaultParam('colAligns',{'Karma':'CENTER'})

    #--Collection
    def getSorted(self,column,reverse):
        """Returns items sorted according to column and reverse."""
        data = self.data
        items = data.keys()
        if column == 'Name':
            items.sort(key=string.lower,reverse=reverse)
        elif column == 'Karma':
            items.sort(key=string.lower)
            items.sort(key=lambda x: data[x][1],reverse=reverse)
        elif column == 'Header':
            items.sort(key=string.lower)
            items.sort(key=lambda x: data[x][2][:50].lower(),reverse=reverse)
        return items

    #--Item Info
    def getColumns(self,item=None):
        """Returns text labels for item or for row header if item == None."""
        columns = self.getParam('columns',self.tankColumns)
        if item == None: return columns[:]
        labels,itemData = [],self.data[item]
        for column in columns:
            if column == 'Name': labels.append(item)
            elif column == 'Karma':
                karma = itemData[1]
                labels.append(('-','+')[karma>=0]*abs(karma))
            elif column == 'Header':
                header = itemData[2].split('\n',1)[0][:75]
                labels.append(header)
        return labels

    def getName(self,item):
        """Returns a string name of item for use in dialogs, etc."""
        return item

    def getGuiKeys(self,item):
        """Returns keys for icon and text and background colors."""
        textKey = backKey = None
        iconKey = 'karma%+d' % self.data[item][1]
        return (iconKey,textKey,backKey)

    #--Operations
    def loadText(self,path):
        """Enter info from text file."""
        newNames,name,buffer = set(),None,None
        ins = path.open('r')
        reName = re.compile(r'==([^=]+)=*$')
        for line in ins:
            maName = reName.match(line)
            if not maName:
                if buffer: buffer.write(line)
                continue
            if name:
                self.data[name] = (time.time(),0,buffer.getvalue().strip())
                newNames.add(name)
                buffer.close()
                buffer = None
            name = maName.group(1).strip()
            if name: buffer = cStringIO.StringIO()
        ins.close()
        if newNames: self.setChanged()
        return newNames

    def dumpText(self,path,names):
        """Dump to text file."""
        out = path.open('w')
        for name in sorted(names,key=string.lower):
            out.write('== %s %s\n' % (name,'='*(75-len(name))))
            out.write(self.data[name][2].strip())
            out.write('\n\n')
        out.close()

#------------------------------------------------------------------------------
class ScreensData(DataDict):
    def __init__(self):
        """Initialize."""
        self.dir = dirs['app']
        self.data = {} #--data[Path] = (ext,mtime)

    def refresh(self):
        """Refresh list of screenshots."""
        self.dir = dirs['app']
        ssBase = GPath(oblivionIni.getSetting('Display','SScreenShotBaseName','ScreenShot'))
        if ssBase.head:
            self.dir = self.dir.join(ssBase.head)
        newData = {}
        reImageExt = re.compile(r'\.(bmp|jpg)$',re.I)
        #--Loop over files in directory
        for fileName in self.dir.list():
            filePath = self.dir.join(fileName)
            maImageExt = reImageExt.search(fileName.s)
            if maImageExt and filePath.isfile():
                newData[fileName] = (maImageExt.group(1).lower(),filePath.mtime)
        changed = (self.data != newData)
        self.data = newData
        return changed

    def delete(self,fileName):
        """Deletes member file."""
        filePath = self.dir.join(fileName)
        filePath.remove()
        del self.data[fileName]

#------------------------------------------------------------------------------
class Installer(object):
    """Object representing an installer archive, its user configuration, and
    its installation state."""

    #--Member data
    persistent = ('archive','order','group','modified','size','crc',
        'fileSizeCrcs','type','isActive','subNames','subActives','dirty_sizeCrc',
        'comments','readMe','packageDoc','packagePic','src_sizeCrcDate','hasExtraData',
        'skipVoices','espmNots','isSolid')
    volatile = ('data_sizeCrc','skipExtFiles','skipDirFiles','status','missingFiles',
        'mismatchedFiles','refreshed','mismatchedEspms','unSize','espms','underrides', 'hasWizard', 'espmMap')
    __slots__ = persistent+volatile
    #--Package analysis/porting.
    docDirs = set(('screenshots',))
    dataDirs = set(('bash patches','distantlod','docs','facegen','fonts',
        'menus','meshes','music','shaders','sound', 'textures', 'trees','video'))
    dataDirsPlus = dataDirs | docDirs | set(('streamline','_tejon','ini tweaks','scripts'))
    dataDirsMinus = set(('bash','obse','replacers')) #--Will be skipped even if hasExtraData == True.
    reDataFile = re.compile(r'(masterlist.txt|dlclist.txt|\.(esp|esm|bsa))$',re.I)
    reReadMe = re.compile(r'^([^\\]*)(read[ _]?me|lisez[ _]?moi)([^\\]*)\.(txt|rtf|htm|html|doc|odt)$',re.I)
    skipExts = set(('.dll','.dlx','.exe','.py','.pyc','.7z','.zip','.rar','.db'))
    skipExts.update(set(readExts))
    docExts = set(('.txt','.rtf','.htm','.html','.doc','.docx','.odt','.mht','.pdf','.css','.xls'))
    imageExts = set(('.gif','.jpg','.png'))
    #--Temp Files/Dirs
    tempDir = GPath('InstallerTemp')
    tempList = GPath('InstallerTempList.txt')

    #--Class Methods ----------------------------------------------------------
    @staticmethod
    def getGhosted():
        """Returns map of real to ghosted files in mods directory."""
        dataDir = dirs['mods']
        ghosts = [x for x in dataDir.list() if x.cs[-6:] == '.ghost']
        return dict((x.root,x) for x in ghosts if not dataDir.join(x).root.exists())

    @staticmethod
    def clearTemp():
        """Clear temp install directory -- DO NOT SCREW THIS UP!!!"""
        Installer.tempDir.rmtree(safety='Temp')

    @staticmethod
    def sortFiles(files):
        """Utility function. Sorts files by directory, then file name."""
        def sortKey(file):
            dirFile = file.lower().rsplit('\\',1)
            if len(dirFile) == 1: dirFile.insert(0,'')
            return dirFile
        sortKeys = dict((x,sortKey(x)) for x in files)
        return sorted(files,key=lambda x: sortKeys[x])

    @staticmethod
    def refreshSizeCrcDate(apRoot,old_sizeCrcDate,progress=None,removeEmpties=False,fullRefresh=False):
        """Update old_sizeCrcDate for root directory.
        This is used both by InstallerProject's and by InstallersData."""
        rootIsMods = (apRoot == dirs['mods']) #--Filtered scanning for mods directory.
        norm_ghost = (rootIsMods and Installer.getGhosted()) or {}
        ghost_norm = dict((y,x) for x,y in norm_ghost.iteritems())
        rootName = apRoot.stail
        progress = progress or bolt.Progress()
        new_sizeCrcDate = {}
        bethFiles = bush.bethDataFiles
        skipExts = Installer.skipExts
        asRoot = apRoot.s
        relPos = len(apRoot.s)+1
        pending = set()
        #--Scan for changed files
        progress(0,_("%s: Pre-Scanning...") % rootName)
        progress.setFull(1)
        dirDirsFiles = []
        emptyDirs = set()
        dirDirsFilesAppend = dirDirsFiles.append
        emptyDirsAdd = emptyDirs.add
        oldGet = old_sizeCrcDate.get
        ghostGet = ghost_norm.get
        normGet = norm_ghost.get
        pendingAdd = pending.add
        apRootJoin = apRoot.join
        for asDir,sDirs,sFiles in os.walk(asRoot):
            progress(0.05,_("%s: Pre-Scanning...\n%s") % (rootName,asDir[relPos:]))
            if rootIsMods and asDir == asRoot:
                sDirs[:] = [x for x in sDirs if x.lower() not in Installer.dataDirsMinus]
                if inisettings['keepLog'] >= 1:
                    log = inisettings['logFile'].open("a")
                    log.write('(in refreshSizeCRCDate) sDirs = %s\n'%(sDirs[:]))
                    log.close()
                if settings['bash.installers.skipDistantLOD']:
                    sDirs[:] = [x for x in sDirs if x.lower() != 'distantlod']
                if settings['bash.installers.skipScreenshots']:
                    sDirs[:] = [x for x in sDirs if x.lower() != 'screenshots'] 
                if settings['bash.installers.skipDocs'] and settings['bash.installers.skipImages']:
                    sDirs[:] = [x for x in sDirs if x.lower() != 'docs']
                if inisettings['keepLog'] >= 1:
                    log = inisettings['logFile'].open("a")
                    log.write('(in refreshSizeCRCDate after accounting for skipping) sDirs = %s\n'%(sDirs[:]))
                    log.close()                    
            dirDirsFilesAppend((asDir,sDirs,sFiles))
            if not (sDirs or sFiles): emptyDirsAdd(GPath(asDir))
        progress(0,_("%s: Scanning...") % rootName)
        progress.setFull(1+len(dirDirsFiles))
        for index,(asDir,sDirs,sFiles) in enumerate(dirDirsFiles):
            progress(index)
            rsDir = asDir[relPos:]
            inModsRoot = rootIsMods and not rsDir
            apDir = GPath(asDir)
            rpDir = GPath(rsDir)
            rpDirJoin = rpDir.join
            apDirJoin = apDir.join
            for sFile in sFiles:
                #print '...',sFile
                ext = sFile[sFile.rfind('.'):].lower()
                rpFile = rpDirJoin(sFile)
                if inModsRoot:
                    if ext in skipExts: continue
                    if not rsDir and sFile.lower() in bethFiles: continue
                    rpFile = ghostGet(rpFile,rpFile)
                isEspm = not rsDir and (ext == '.esp' or ext == '.esm')
                apFile = apDirJoin(sFile)
                size = apFile.size
                date = apFile.mtime
                oSize,oCrc,oDate = oldGet(rpFile,(0,0,0))
                if size == oSize and (date == oDate or isEspm):
                    new_sizeCrcDate[rpFile] = (oSize,oCrc,oDate)
                else:
                    pendingAdd(rpFile)
        #--Remove empty dirs?
        if rootIsMods and settings['bash.installers.removeEmptyDirs']:
            for dir in emptyDirs:
                try: dir.removedirs()
                except OSError: pass
        #--Force update?
        if fullRefresh: pending |= set(new_sizeCrcDate)
        changed = bool(pending) or (len(new_sizeCrcDate) != len(old_sizeCrcDate))
        #--Update crcs?
        if pending:
            progress(0,_("%s\nCalculating CRCs...\n") % rootName)
            progress.setFull(1+len(pending))
            for index,rpFile in enumerate(sorted(pending)):
                progress(index,_("%s\nCalculating CRCs...\n%s") % (rootName,rpFile.s))
                #print rpFile.s
                apFile = apRootJoin(normGet(rpFile,rpFile))
                crc = apFile.crc
                size = apFile.size
                date = apFile.mtime
                new_sizeCrcDate[rpFile] = (size,crc,date)
        old_sizeCrcDate.clear()
        old_sizeCrcDate.update(new_sizeCrcDate)
        #--Done
        return changed

    #--Initization, etc -------------------------------------------------------
    def initDefault(self):
        """Inits everything to default values."""
        #--Package Only
        self.archive = ''
        self.modified = 0 #--Modified date
        self.size = 0 #--size of archive file
        self.crc = 0 #--crc of archive
        self.type = 0 #--Package type: 0: unset/invalid; 1: simple; 2: complex
        self.isSolid = 0
        self.fileSizeCrcs = []
        self.subNames = []
        self.src_sizeCrcDate = {} #--For InstallerProject's
        #--Dirty Update
        self.dirty_sizeCrc = {}
        #--Mixed
        self.subActives = []
        #--User Only
        self.skipVoices = False
        self.hasExtraData = False
        self.comments = ''
        self.group = '' #--Default from abstract. Else set by user.
        self.order = -1 #--Set by user/interface.
        self.isActive = False
        self.espmNots = set() #--Lowercase esp/m file names that user has decided not to install.
        #--Volatiles (unpickled values)
        #--Volatiles: directory specific
        self.refreshed = False
        #--Volatile: set by refreshDataSizeCrc
        self.hasWizard = False
        self.espmMap = {}
        self.readMe = self.packageDoc = self.packagePic = None
        self.data_sizeCrc = {}
        self.skipExtFiles = set()
        self.skipDirFiles = set()
        self.espms = set()
        self.unSize = 0
        #--Volatile: set by refreshStatus
        self.status = 0
        self.underrides = set()
        self.missingFiles = set()
        self.mismatchedFiles = set()
        self.mismatchedEspms = set()

    def __init__(self,archive):
        """Initialize."""
        self.initDefault()
        self.archive = archive.stail

    def __getstate__(self):
        """Used by pickler to save object state."""
        getter = object.__getattribute__
        return tuple(getter(self,x) for x in self.persistent)

    def __setstate__(self,values):
        """Used by unpickler to recreate object."""
        self.initDefault()
        setter = object.__setattr__
        for value,attr in zip(values,self.persistent):
            setter(self,attr,value)
        if self.dirty_sizeCrc == None:
            self.dirty_sizeCrc = {} #--Use empty dict instead.
        self.refreshDataSizeCrc()

    def __copy__(self,iClass=None):
        """Create a copy of self -- works for subclasses too (assuming subclasses
        don't add new data members). iClass argument is to support Installers.updateDictFile"""
        iClass = iClass or self.__class__
        clone = iClass(GPath(self.archive))
        copier = copy.copy
        getter = object.__getattribute__
        setter = object.__setattr__
        for attr in Installer.__slots__:
            setter(clone,attr,copier(getter(self,attr)))
        return clone

    def refreshDataSizeCrc(self):
        """Updates self.data_sizeCrc and related variables.
        Also, returns dest_src map for install operation."""
        if isinstance(self,InstallerArchive):
            archiveRoot = GPath(self.archive).sroot
        else:
            archiveRoot = self.archive
        reReadMe = self.reReadMe
        docExts = self.docExts
        imageExts = self.imageExts
        docDirs = self.docDirs
        dataDirsPlus = self.dataDirsPlus
        dataDirsMinus = self.dataDirsMinus
        skipExts = self.skipExts
        bethFiles = bush.bethDataFiles
        packageFiles = set(('package.txt','package.jpg'))
        unSize = 0
        espmNots = self.espmNots
        skipVoices = self.skipVoices
        if espmNots and not skipVoices:
            skipEspmVoices = set(x.cs for x in espmNots)
        else:
            skipEspmVoices = None
        skipScreenshots = settings['bash.installers.skipScreenshots']
        skipDocs = settings['bash.installers.skipDocs']
        skipImages = settings['bash.installers.skipImages']
        skipDistantLOD = settings['bash.installers.skipDistantLOD']
        hasExtraData = self.hasExtraData
        type = self.type
        if type == 2:
            allSubs = set(self.subNames[1:])
            activeSubs = set(x for x,y in zip(self.subNames[1:],self.subActives[1:]) if y)
        #--Init to empty
        self.hasWizard = False
        self.readMe = self.packageDoc = self.packagePic = None
        for attr in ('skipExtFiles','skipDirFiles','espms'):
            object.__getattribute__(self,attr).clear()
        data_sizeCrc = {}
        skipExtFiles = self.skipExtFiles
        skipDirFiles = self.skipDirFiles
        espms = self.espms
        dest_src = {}
        #--Bad archive?
        if type not in (1,2): return dest_src
        #--Scan over fileSizeCrcs
        for full,size,crc in self.fileSizeCrcs:
            file = full #--Default
            fileLower = file.lower()
            if full[:2] == '--' or fileLower[:20] == 'omod conversion data':
                continue
            sub = ''
            bSkip = False
            if type == 2: #--Complex archive
                subFile = full.split('\\',1)
                if len(subFile) == 2:
                    sub,file = subFile
                    if sub not in activeSubs:
                        if sub not in allSubs:
                            skipDirFiles.add(file)
                        bSkip = True
                    fileLower = file.lower()
            if sub not in self.espmMap:
                self.espmMap[sub] = []
            rootPos = file.find('\\')
            extPos = file.rfind('.')
            fileLower = file.lower()
            rootLower = (rootPos > 0 and fileLower[:rootPos]) or ''
            fileExt = (extPos > 0 and fileLower[extPos:]) or ''
            #--Silent skips
            if fileLower[-9:] == 'thumbs.db' or fileLower[-11:] == 'desktop.ini':
                continue #--Silent skip
            elif skipDistantLOD and fileLower[:10] == 'distantlod':
                continue
            elif skipVoices and fileLower[:11] == 'sound\\voice':
                continue
            elif skipScreenshots and fileLower[:11] == 'screenshots':
                continue
            elif fileLower == 'wizard.txt':
                self.hasWizard = True
                continue
            elif skipImages :
                if fileExt in imageExts :
                    continue
            elif skipDocs :
                if fileExt in docExts :
                    continue            
            elif file[:2] == '--':
                continue
            #--Noisy skips
            elif file in bethFiles:
                if not bSkip: skipDirFiles.add(full)
                continue
            elif not hasExtraData and rootLower and rootLower not in dataDirsPlus:
                if not bSkip: skipDirFiles.add(full)
                continue
            elif hasExtraData and rootLower and rootLower in dataDirsMinus:
                if not bSkip: skipDirFiles.add(full)
                continue
            elif fileExt in skipExts:
                if not bSkip: skipExtFiles.add(full)
                continue
            #--Esps
            if not rootLower and reModExt.match(fileExt):
                if file not in self.espmMap[sub]:
                    self.espmMap[sub].append(file)
                if bSkip: continue
                pFile = GPath(file)
                espms.add(pFile)
                if pFile in espmNots: continue
            elif bSkip: continue
            if skipEspmVoices and fileLower[:12] == 'sound\\voice\\':
                farPos = file.find('\\',12)
                if farPos > 12 and fileLower[12:farPos] in skipEspmVoices:
                    continue
            #--Remap docs
            dest = file
            if rootLower in docDirs:
                dest = 'Docs\\'+file[rootPos+1:]
            elif not rootLower:
                maReadMe = reReadMe.match(file)
                if fileLower == 'masterlist.txt' or fileLower == 'dlclist.txt':
                    pass
                elif maReadMe:
                    if not (maReadMe.group(1) or maReadMe.group(3)):
                        dest = 'Docs\\%s%s' % (archiveRoot,fileExt)
                    else:
                        dest = 'Docs\\'+file
                    self.readMe = dest
                elif fileLower == 'package.txt':
                    dest = self.packageDoc = 'Docs\\'+archiveRoot+'.package.txt'
                elif fileLower == 'package.jpg':
                    dest = self.packagePic = 'Docs\\'+archiveRoot+'.package.jpg'
                elif fileExt in docExts:
                    dest = 'Docs\\'+file
                elif fileExt in imageExts:
                    dest = 'Docs\\'+file
            #--Save
            key = GPath(dest)
            data_sizeCrc[key] = (size,crc)
            dest_src[key] = full
            unSize += size
        self.unSize = unSize
        (self.data_sizeCrc,old_sizeCrc) = (data_sizeCrc,self.data_sizeCrc)
        #--Update dirty?
        if self.isActive and data_sizeCrc != old_sizeCrc:
            dirty_sizeCrc = self.dirty_sizeCrc
            for file,sizeCrc in old_sizeCrc.iteritems():
                if file not in dirty_sizeCrc and sizeCrc != data_sizeCrc.get(file):
                    dirty_sizeCrc[file] = sizeCrc
        #--Done (return dest_src for install operation)
        return dest_src

    def refreshSource(self,archive,progress=None,fullRefresh=False):
        """Refreshes fileSizeCrcs, size, date and modified from source archive/directory."""
        raise AbstractError

    def refreshBasic(self,archive,progress=None,fullRefresh=False):
        """Extract file/size/crc info from archive."""
        self.refreshSource(archive,progress,fullRefresh)
        def fscSortKey(fsc):
            dirFile = fsc[0].lower().rsplit('\\',1)
            if len(dirFile) == 1: dirFile.insert(0,'')
            return dirFile
        fileSizeCrcs = self.fileSizeCrcs
        sortKeys = dict((x,fscSortKey(x)) for x in fileSizeCrcs)
        fileSizeCrcs.sort(key=lambda x: sortKeys[x])
        #--Type, subNames
        reDataFile = self.reDataFile
        dataDirs = self.dataDirs
        type = 0
        subNameSet = set()
        subNameSet.add('')
        for file,size,crc in fileSizeCrcs:
            fileLower = file.lower()
            if type != 1:
                frags = file.split('\\')
                nfrags = len(frags)
                #--Type 1?
                if (nfrags == 1 and reDataFile.search(frags[0]) or
                    nfrags > 1 and frags[0].lower() in dataDirs):
                    type = 1
                    break
                #--Type 2?
                elif nfrags > 2 and frags[1].lower() in dataDirs:
                    subNameSet.add(frags[0])
                    type = 2
                elif nfrags == 2 and reDataFile.search(frags[1]):
                    subNameSet.add(frags[0])
                    type = 2
        self.type = type
        #--SubNames, SubActives
        if type == 2:
            self.subNames = sorted(subNameSet,key=string.lower)
            actives = set(x for x,y in zip(self.subNames,self.subActives) if (y or x == ''))
            if len(self.subNames) == 2: #--If only one subinstall, then make it active.
                self.subActives = [True,True]
            else:
                self.subActives = [(x in actives) for x in self.subNames]
        else:
            self.subNames = []
            self.subActives = []
        #--Data Size Crc
        self.refreshDataSizeCrc()

    def refreshStatus(self,installers):
        """Updates missingFiles, mismatchedFiles and status.
        Status:
        20: installed (green)
        10: mismatches (yellow)
        0: unconfigured (white)
        -10: missing files (red)
        -20: bad type (grey)
        """
        data_sizeCrc = self.data_sizeCrc
        data_sizeCrcDate = installers.data_sizeCrcDate
        abnorm_sizeCrc = installers.abnorm_sizeCrc
        missing = self.missingFiles
        mismatched = self.mismatchedFiles
        misEspmed = self.mismatchedEspms
        underrides = set()
        status = 0
        missing.clear()
        mismatched.clear()
        misEspmed.clear()
        if self.type == 0:
            status = -20
        elif data_sizeCrc:
            for file,sizeCrc in data_sizeCrc.iteritems():
                sizeCrcDate = data_sizeCrcDate.get(file)
                if not sizeCrcDate:
                    missing.add(file)
                elif sizeCrc != sizeCrcDate[:2]:
                    mismatched.add(file)
                    if not file.shead and reModExt.search(file.s):
                        misEspmed.add(file)
                if sizeCrc == abnorm_sizeCrc.get(file):
                    underrides.add(file)
            if missing: status = -10
            elif misEspmed: status = 10
            elif mismatched: status = 20
            else: status = 30
        #--Clean Dirty
        dirty_sizeCrc = self.dirty_sizeCrc
        for file,sizeCrc in dirty_sizeCrc.items():
            sizeCrcDate = data_sizeCrcDate.get(file)
            if (not sizeCrcDate or sizeCrc != sizeCrcDate[:2] or
                sizeCrc == data_sizeCrc.get(file)
                ):
                del dirty_sizeCrc[file]
        #--Done
        (self.status,oldStatus) = (status,self.status)
        (self.underrides,oldUnderrides) = (underrides,self.underrides)
        return (self.status != oldStatus or self.underrides != oldUnderrides)

    def install(self,archive,destFiles,data_sizeCrcDate,progress=None):
        """Install specified files to Oblivion\Data directory."""
        raise AbstractError

#------------------------------------------------------------------------------
class InstallerConverter(object):
    """Object representing a BAIN conversion archive, and its configuration"""
    #--Temp Files/Dirs
    tempDir = GPath('InstallerTemp')
    tempList = GPath('InstallerTempList.txt')
    def __init__(self,srcArchives=None, data=None, destArchive=None, BCFArchive=None,progress=None):
        #--Persistent variables are saved in the data tank for normal operations.
        #--persistBCF is read one time from BCF.dat, and then saved in Converters.dat to keep archive extractions to a minimum
        #--persistDAT has operational variables that are saved in Converters.dat
        self.persistBCF = ['srcCRCs']
        self.persistDAT = ['crc','fullPath']
        self.srcCRCs = set()
        self.crc = None
        #--fullPath is saved in Converters.dat, but it is also updated on every refresh in case of renaming
        self.fullPath = 'BCF: Missing!'
        #--Semi-Persistent variables are loaded only when and as needed. They're always read from BCF.dat
        self.settings = ['comments','espmNots','hasExtraData','isSolid','skipVoices','subActives']
        self.volatile = ['convertedFiles','dupeCount']
        self.convertedFiles = []
        self.dupeCount = {}
        #--Cheap init overloading...
        if data != None:
            #--Build a BCF from scratch
            self.fullPath = dirs['converters'].join(BCFArchive)
            self.build(srcArchives, data, destArchive, BCFArchive,progress)
            self.crc = self.fullPath.crc
        elif isinstance(srcArchives,bolt.Path):
            #--Load a BCF from file
            self.fullPath = dirs['converters'].join(srcArchives)
            self.load()
            self.crc = self.fullPath.crc
        #--Else is loading from Converters.dat, called by __setstate__
        
    def __getstate__(self):
        """Used by pickler to save object state. Used for Converters.dat"""
        getter = object.__getattribute__
        attrs = self.persistBCF + self.persistDAT
        return tuple(getter(self,x) for x in attrs)

    def __setstate__(self,values):
        """Used by unpickler to recreate object. Used for Converters.dat"""
        self.__init__()
        setter = object.__setattr__
        attrs = self.persistBCF + self.persistDAT
        for value,attr in zip(values,attrs):
            setter(self,attr,value)

    def load(self,fullLoad=False):
        """Loads BCF.dat. Called once when a BCF is first installed, during a fullRefresh, and when the BCF is applied"""
        if not self.fullPath.exists(): raise StateError(_("\nLoading %s:\nBCF doesn't exist.") % self.fullPath.s)
        command = '7z.exe x "%s" BCF.dat -y -so' % self.fullPath.s
        try:
            ins = os.popen(command,'rb')
            values = cPickle.load(ins)
            setter = object.__setattr__
            for value,attr in zip(values,self.persistBCF):
                setter(self,attr,value)
            if fullLoad:
                values = cPickle.load(ins)
                for value,attr in zip(values,self.settings + self.volatile):
                    setter(self,attr,value)
            ins.close()
        except:
            if ins: ins.close()
            raise StateError(_("\nLoading %s:\nBCF extraction failed.") % self.fullPath.s)

    @staticmethod
    def clearTemp():
        """Clear temp install directory -- DO NOT SCREW THIS UP!!!"""
        InstallerConverter.tempDir.rmtree(safety='Temp')

    def apply(self,destArchive,crc_installer,progress=None):
        """Applies the BCF and packages the converted archive"""
        #--Prepare by fully loading the BCF and clearing temp
        self.load(True)
        self.clearTemp()
        progress = progress or bolt.Progress()
        progress(0,_("%s\nExtracting files...") % self.fullPath.stail)
        command = '7z.exe x "%s" -y -o"%s"' % (self.fullPath.s, self.tempDir.s)
        ins = os.popen(command,'r')
        #--Error checking
        reError = re.compile('Error:')
        regMatch = reError.match
        errorLine = []
        for line in ins:
            if len(errorLine) or regMatch(line):
                errorLine.append(line)
        result = ins.close()
        if result:
            raise StateError(_("%s: Extraction failed:\n%s") % (self.fullPath.s, "\n".join(errorLine)))
        #--Extract source archives
        lastStep = 0
        nextStep = step = 0.4 / len(self.srcCRCs)
        for srcCRC in self.srcCRCs:
            srcInstaller = crc_installer[srcCRC]
            files = srcInstaller.sortFiles([x[0] for x in srcInstaller.fileSizeCrcs])
            if not files: continue
            progress(0,srcInstaller.archive+_("\nExtracting files..."))
            self.unpack(srcInstaller,files,SubProgress(progress,lastStep,nextStep))
            lastStep = nextStep
            nextStep += step
        #--Move files around and pack them
        self.arrangeFiles(SubProgress(progress,lastStep,0.7))
        self.pack(self.tempDir.join("BCF-Temp"), destArchive,dirs['installers'],SubProgress(progress,0.7,1.0))
        #--Lastly, apply the settings.
        #--That is done by the calling code, since it requires an InstallerArchive object to work on
        
    def applySettings(self,destInstaller):
        """Applies the saved settings to an Installer"""
        setter = object.__setattr__
        getter = object.__getattribute__
        for attr in self.settings:
            setter(destInstaller,attr,getter(self,attr))

    def arrangeFiles(self,progress):
        """Copies and/or moves extracted files into their proper arrangement."""
        destDir = self.tempDir.join("BCF-Temp")
        progress(0,_("Moving files..."))
        progress.setFull(1+len(self.convertedFiles))
        #--Make a copy of dupeCount
        dupes = dict(self.dupeCount.items())
        destJoin = destDir.join
        tempJoin = self.tempDir.join
        #--Move every file
        for index, (crcValue, srcDir_File, destFile) in enumerate(self.convertedFiles):
            srcDir = srcDir_File[0]
            srcFile = srcDir_File[1]
            if isinstance(srcDir,basestring):
                #--either 'BCF-Missing', or crc read from 7z l -slt
                srcFile = tempJoin(srcDir,srcFile)
            else:
                srcFile = tempJoin("%08X" % srcDir,srcFile)
            destFile = destJoin(destFile)
            if not srcFile.exists() or destFile == None:
                raise StateError(_("%s: Missing file:\n%s") % (self.fullPath.stail, destFile))
                return
            numDupes = dupes[crcValue]
            #--Keep track of how many times the file is referenced by convertedFiles
            #--This allows files to be moved whenever possible, speeding file operations up
            if numDupes > 1:
                progress(index,_("Copying file...\n%s") % destFile.stail)
                dupes[crcValue] = numDupes - 1
                srcFile.copyTo(destFile)
            else:
                progress(index,_("Moving file...\n%s") % destFile.stail)                
                srcFile.moveTo(destFile)
                
    def build(self, srcArchives, data, destArchive, BCFArchive,progress=None):
        """Builds and packages a BCF"""
        progress = progress or bolt.Progress()
        #--Initialization
        self.clearTemp()
        srcFiles = {}
        destFiles = []
        destInstaller = data[destArchive]
        self.missingFiles = []
        subArchives = dict()
        srcAdd = self.srcCRCs.add
        convertedFileAppend = self.convertedFiles.append
        destFileAppend = destFiles.append
        missingFileAppend = self.missingFiles.append
        dupeGet = self.dupeCount.get
        srcGet = srcFiles.get
        subGet = subArchives.get
        setter = object.__setattr__
        getter = object.__getattribute__
        lastStep = 0
        #--Get settings
        for attr in ['espmNots','hasExtraData','skipVoices','comments','subActives','isSolid']:
            setter(self,attr,getter(destInstaller,attr))
        #--Make list of source files
        for installer in [data[x] for x in srcArchives]:
            installerCRC = installer.crc
            srcAdd(installerCRC)
            fileList = subGet(installerCRC,[])
            fileAppend = fileList.append
            for fileSizeCrc in installer.fileSizeCrcs:
                fileName = fileSizeCrc[0]
                fileCRC = fileSizeCrc[2]
                srcFiles[fileCRC] = (installerCRC,fileName)
                #--Note any subArchives
                if GPath(fileName).cext in readExts:
                    fileAppend(fileName)
            if len(fileList): subArchives[installerCRC] = fileList
        if len(subArchives):
            archivedFiles = dict()
            nextStep = step = 0.3 / len(subArchives)
            #--Extract any subArchives
            #--It would be faster to read them with 7z l -slt
            #--But it is easier to use the existing recursive extraction
            for index, (installerCRC) in enumerate(subArchives):
                installer = data.crc_installer[installerCRC]
                self.unpack(installer,subArchives[installerCRC],SubProgress(progress, lastStep, nextStep))
                lastStep = nextStep
                nextStep += step
            #--Note all extracted files
            for crc in os.listdir(self.tempDir.s):
                fpath = os.path.join(self.tempDir.s,crc)
                for root, y, files in os.walk(fpath):
                    for file in files:
                        file = GPath(os.path.join(root,file))
                        archivedFiles[file.crc] = (crc,file.s[len(fpath)+1:])
            #--Add the extracted files to the source files list
            srcFiles.update(archivedFiles)
            self.clearTemp()
        #--Make list of destination files
        for fileSizeCrc in destInstaller.fileSizeCrcs:
            fileName = fileSizeCrc[0]
            fileCRC = fileSizeCrc[2]
            destFileAppend((fileCRC, fileName))
            #--Note files that aren't in any of the source files
            if fileCRC not in srcFiles:
                missingFileAppend(fileName)
                srcFiles[fileCRC] = ('BCF-Missing',fileName)
            self.dupeCount[fileCRC] = dupeGet(fileCRC,0) + 1
        #--Monkey around with the progress step values
        #--Smooth the progress bar progression since some of the subroutines won't always run
        if lastStep == 0:
            if len(self.missingFiles):
                #--No subArchives, but files to pack
                sProgress = SubProgress(progress, lastStep, lastStep + 0.6)
                lastStep += 0.6
            else:
                #--No subroutines will run
                sProgress = SubProgress(progress, lastStep, lastStep + 0.8)
                lastStep += 0.8
        else:
            if len(self.missingFiles):
                #--All subroutines will run
                sProgress = SubProgress(progress, lastStep, lastStep + 0.3)
                lastStep += 0.3
            else:
                #--No files to pack, but subArchives were unpacked
                sProgress = SubProgress(progress, lastStep, lastStep + 0.5)
                lastStep += 0.5
        sProgress(0,_("%s\nMapping files...") % BCFArchive.s)
        sProgress.setFull(1+len(destFiles))
        #--Map the files
        for index, (fileCRC, fileName) in enumerate(destFiles):
            convertedFileAppend((fileCRC,srcGet(fileCRC),fileName))
            sProgress(index,_("%s\nMapping files...\n%s") % (BCFArchive.s,fileName))
        #--Build the BCF
        if len(self.missingFiles):
            #--Unpack missing files
            destInstaller.unpackToTemp(destArchive,self.missingFiles,SubProgress(progress,lastStep, lastStep + 0.2))
            lastStep += 0.2
            #--Move the temp dir to tempDir\BCF-Missing
            #--Work around since moveTo doesn't allow direct moving of a directory into its own subdirectory
            tempDir2 = GPath('BCF-Missing')
            destInstaller.tempDir.moveTo(tempDir2)
            tempDir2.moveTo(destInstaller.tempDir.join('BCF-Missing'))
        #--Make the temp dir in case it doesn't exist
        destInstaller.tempDir.makedirs()
        #--Dump settings into BCF.dat
        try:
            f = open(destInstaller.tempDir.join("BCF.dat").s, 'wb')
            cPickle.dump(tuple(getter(self,x) for x in self.persistBCF), f,-1)
            cPickle.dump(tuple(getter(self,x) for x in (self.settings + self.volatile)), f,-1)
            result = f.close()
        finally:
            if f: f.close()
            if result:
                raise StateError(_("Error creating BCF.dat:\nError Code: %s") % (result))
        #--Pack the BCF
        #--BCF's need to be non-Solid since they have to have BCF.dat extracted and read from during runtime
        self.isSolid = False
        self.pack(destInstaller.tempDir,BCFArchive,dirs['converters'],SubProgress(progress, lastStep, 1.0))
        self.isSolid = getter(destInstaller,'isSolid')

    def pack(self,srcFolder,destArchive,outDir,progress=None):
        """Creates the BAIN'ified archive and cleans up temp"""
        progress = progress or bolt.Progress()
        #--Used solely for the progress bar
        length = sum([len(files) for x,y,files in os.walk(srcFolder.s)])
        #--Determine settings for 7z
        archiveType = writeExts.get(destArchive.cext)
        if not archiveType:
            #--Always fail back to using the defaultExt
            destArchive = GPath(destArchive.sbody + defaultExt).tail
            archiveType = writeExts.get(destArchive.cext)
        outFile = outDir.join(destArchive)
        solid = ('off','on')[self.isSolid]
        command = '7z.exe a "%s" -t"%s" -ms="%s" -y -r -o"%s" "%s"' % ("%s" % outFile.temp.s, archiveType, solid, outDir.s, "%s\\*" % dirs['app'].join("Mopy",srcFolder).s)
        progress(0,_("%s\nCompressing files...") % destArchive.s)
        progress.setFull(1+length)
        #--Pack the files
        ins = os.popen(command,'r')
        #--Error checking and progress feedback
        reCompressing = re.compile('Compressing\s+(.+)')
        regMatch = reCompressing.match
        reError = re.compile('Error: (.*)')
        regErrMatch = reError.match
        errorLine = []
        index = 0
        for line in ins:
            maCompressing = regMatch(line)
            if len(errorLine) or regErrMatch(line):
                errorLine.append(line)
            if maCompressing:
                progress(index,destArchive.s+_("\nCompressing files...\n%s") % maCompressing.group(1).strip())
                index += 1
        result = ins.close()
        if result:
            outFile.temp.remove()
            raise StateError(_("%s: Compression failed:\n%s") % (destArchive.s, "\n".join(errorLine)))
        #--Finalize the file, and cleanup
        outFile.untemp()
        self.clearTemp()
        
    def unpack(self,srcInstaller,fileNames,progress=None):
        """Recursive function: completely extracts the source installer to subTempDir.
        It does NOT clear the temp folder.  This should be done prior to calling the function.
        Each archive and sub-archive is extracted to its own sub-directory to prevent file thrashing"""
        #--Sanity check
        if not fileNames: raise ArgumentError(_("No files to extract for %s.") % srcInstaller.s)
        #--Dump file list
        try:
            out = self.tempList.open('w')
            out.write('\n'.join(fileNames))
            result = out.close()
        finally:
            if out: out.close()
            if result: raise StateError(_("Error creating file list for 7z:\nError Code: %s") % (result))
            result = 0
        #--Determine settings for 7z
        installerCRC = srcInstaller.crc
        if isinstance(srcInstaller,InstallerArchive):
            srcInstaller = GPath(srcInstaller.archive)
            apath = dirs['installers'].join(srcInstaller)
        else:
            apath = srcInstaller
        subTempDir = GPath('InstallerTemp').join("%08X" % installerCRC)
        if progress:
            progress(0,_("%s\nExtracting files...") % srcInstaller.s)
            progress.setFull(1+len(fileNames))
        command = '7z.exe x "%s" -y -o"%s" @%s -scsWIN' % (apath.s, subTempDir.s, self.tempList.s)
        #--Extract files
        ins = os.popen(command,'r')
        #--Error Checking, and progress feedback
        #--Note subArchives for recursive unpacking
        subArchives = []
        reExtracting = re.compile('Extracting\s+(.+)')
        regMatch = reExtracting.match
        reError = re.compile('Error: (.*)')
        regErrMatch = reError.match
        errorLine = []
        index = 0
        for line in ins:
            maExtracting = regMatch(line)
            if len(errorLine) or regErrMatch(line):
                errorLine.append(line)
            if maExtracting:
                extracted = GPath(maExtracting.group(1).strip())
                if progress:
                    progress(index,_("%s\nExtracting files...\n%s") % (srcInstaller.s,extracted.s))
                if extracted.cext in readExts:
                    subArchives.append(self.tempDir.join("%08X" % installerCRC, extracted.s))
                index += 1
        result = ins.close()
        if result:
            raise StateError(_("%s: Extraction failed:\n%s") % (srcInstaller.s, "\n".join(errorLine)))
        #--Done
        self.tempList.remove()
        #--Recursively unpack subArchives
        if len(subArchives):
            for archive in subArchives:
                self.unpack(archive,['*'])

#------------------------------------------------------------------------------
class InstallerMarker(Installer):
    """Represents a marker installer entry.
    Currently only used for the '==Last==' marker"""
    __slots__ = tuple() #--No new slots

    def __init__(self,archive):
        """Initialize."""
        Installer.__init__(self,archive)
        self.modified = time.time()

    def refreshSource(self,archive,progress=None,fullRefresh=False):
        """Refreshes fileSizeCrcs, size, date and modified from source archive/directory."""
        pass

    def install(self,name,destFiles,data_sizeCrcDate,progress=None):
        """Install specified files to Oblivion\Data directory."""
        pass

#------------------------------------------------------------------------------
class InstallerArchiveError(bolt.BoltError): pass
#------------------------------------------------------------------------------
class InstallerArchive(Installer):
    """Represents an archive installer entry."""
    __slots__ = tuple() #--No new slots

    #--File Operations --------------------------------------------------------
    def refreshSource(self,archive,progress=None,fullRefresh=False):
        """Refreshes fileSizeCrcs, size, date and modified from source archive/directory."""
        #--Basic file info
        self.modified = archive.mtime
        self.size = archive.size
        #--Get fileSizeCrcs
        fileSizeCrcs = self.fileSizeCrcs = []
        reList = re.compile('(Solid|Path|Size|CRC|Attributes|Method) = (.*)')
        file = size = crc = isdir = 0
        self.isSolid = False
        ins = os.popen('7z.exe l -slt "%s"' % archive.s,'rt')
        cumCRC = 0
        for line in ins:
            maList = reList.match(line)
            if maList:
                key,value = maList.groups()
                if key == 'Solid': self.isSolid = (value[0] == '+')
                elif key == 'Path':
                    #--Should be able to twist 7z to export names in UTF-8, but can't (at
                    #  least not prior to 7z 9.04 with -sccs(?) argument?) So instead, 
                    #  assume file is encoded in cp437 and that we want to decode to cp1252.
                    #--Hopefully this will mostly resolve problem with german umlauts, etc.
                    #  It won't solve problems with non-european characters though.
                    try: file = value.decode('cp437').encode('cp1252')
                    except: pass
                elif key == 'Size': size = int(value)
                elif key == 'Attributes': isdir = (value[0] == 'D')
                elif key == 'CRC' and value:
                    crc = int(value,16)
                elif key == 'Method':
                    if file and not isdir:
                        fileSizeCrcs.append((file,size,crc))
                        cumCRC += crc
                    file = size = crc = isdir = 0
        self.crc = cumCRC & 0xFFFFFFFFL
        result = ins.close()
        if result:
            raise InstallerArchiveError('Unable to read archive %s (exit:%s).' % (archive.s,result))

    def unpackToTemp(self,archive,fileNames,progress=None):
        """Erases all files from self.tempDir and then extracts specified files
        from archive to self.tempDir.
        fileNames: File names (not paths)."""
        if not fileNames: raise ArgumentError(_("No files to extract for %s.") % archive.s)
        progress = progress or bolt.Progress()
        progress.state,progress.full = 0,len(fileNames)
        #--Dump file list
        out = self.tempList.open('w')
        out.write('\n'.join(fileNames))
        out.close()
        #--Extract files
        self.clearTemp()
        apath = dirs['installers'].join(archive)
        command = '7z.exe x "%s" -y -o%s @%s -scsWIN' % (apath.s, self.tempDir.s, self.tempList.s)
        ins = os.popen(command,'r')
        reExtracting = re.compile('Extracting\s+(.+)')
        reError = re.compile('Error:')
        extracted = []
        errorLine = []
        index = 0
        for line in ins:
            #print line,
            maExtracting = reExtracting.match(line)
            if len(errorLine) or reError.match(line):
                errorLine.append(line)
            if maExtracting:
                extracted.append(maExtracting.group(1).strip())
                progress(index,_("%s\nExtracting files...\n%s") % (archive.s, maExtracting.group(1).strip()))
                index += 1
        result = ins.close()
        if result:
            raise StateError(_("%s: Extraction failed\n%s") % (archive.s,"\n".join(errorLine)))
        #--Done
        self.tempList.remove()

    def install(self,archive,destFiles,data_sizeCrcDate,progress=None):
        """Install specified files to Oblivion\Data directory."""
        progress = progress or bolt.Progress()
        destDir = dirs['mods']
        destFiles = set(destFiles)
        norm_ghost = Installer.getGhosted()
        data_sizeCrc = self.data_sizeCrc
        dest_src = dict((x,y) for x,y in self.refreshDataSizeCrc().iteritems() if x in destFiles)
        if not dest_src: return 0
        #--Extract
        progress(0,archive.s+_("\nExtracting files..."))
        fileNames = [x[0] for x in dest_src.itervalues()]
        self.unpackToTemp(archive,dest_src.values(),SubProgress(progress,0,0.9))
        #--Move
        progress(0.9,archive.s+_("\nMoving files..."))
        count = 0
        tempDir = self.tempDir
        norm_ghost = Installer.getGhosted()
        for dest,src in dest_src.iteritems():
            size,crc = data_sizeCrc[dest]
            srcFull = tempDir.join(src)
            destFull = destDir.join(norm_ghost.get(dest,dest))
            if srcFull.exists():
                srcFull.moveTo(destFull)
                data_sizeCrcDate[dest] = (size,crc,destFull.mtime)
                count += 1
        self.clearTemp()
        return count

    def unpackToProject(self,archive,project,progress=None):
        """Unpacks archive to build directory."""
        progress = progress or bolt.Progress()
        files = self.sortFiles([x[0] for x in self.fileSizeCrcs])
        if not files: return 0
        #--Clear Project
        destDir = dirs['installers'].join(project)
        if destDir.exists(): destDir.rmtree(safety='Installers')
        #--Extract
        progress(0,project.s+_("\nExtracting files..."))
        self.unpackToTemp(archive,files,SubProgress(progress,0,0.9))
        #--Move
        progress(0.9,project.s+_("\nMoving files..."))
        count = 0
        tempDir = self.tempDir
        for file in files:
            srcFull = tempDir.join(file)
            destFull = destDir.join(file)
            if srcFull.exists():
                srcFull.moveTo(destFull)
                count += 1
        self.clearTemp()
        return count

#------------------------------------------------------------------------------
class InstallerProject(Installer):
    """Represents a directory/build installer entry."""
    __slots__ = tuple() #--No new slots

    def removeEmpties(self,name):
        """Removes empty directories from project directory."""
        empties = set()
        projectDir = dirs['installers'].join(name)
        for asDir,sDirs,sFiles in os.walk(projectDir.s):
            if not (sDirs or sFiles): empties.add(GPath(asDir))
        for empty in empties: empty.removedirs()
        projectDir.makedirs() #--In case it just got wiped out.

    def refreshSource(self,archive,progress=None,fullRefresh=False):
        """Refreshes fileSizeCrcs, size, date and modified from source archive/directory."""
        fileSizeCrcs = self.fileSizeCrcs = []
        src_sizeCrcDate = self.src_sizeCrcDate
        apRoot = dirs['installers'].join(archive)
        Installer.refreshSizeCrcDate(apRoot, src_sizeCrcDate,
            progress, True, fullRefresh)
        cumCRC = 0
##        cumDate = 0
        cumSize = 0
        for file in [x.s for x in self.src_sizeCrcDate]:
            size,crc,date = src_sizeCrcDate[GPath(file)]
            fileSizeCrcs.append((file,size,crc))
##            cumDate = max(date,cumDate)
            cumCRC += crc
            cumSize += size
        self.size = cumSize
        self.modified = apRoot.getmtime(True)
        self.crc = cumCRC & 0xFFFFFFFFL
        self.refreshed = True

    def install(self,name,destFiles,data_sizeCrcDate,progress=None):
        """Install specified files to Oblivion\Data directory."""
        destDir = dirs['mods']
        destFiles = set(destFiles)
        data_sizeCrc = self.data_sizeCrc
        dest_src = dict((x,y) for x,y in self.refreshDataSizeCrc().iteritems() if x in destFiles)
        if not dest_src: return 0
        #--Copy Files
        count = 0
        norm_ghost = Installer.getGhosted()
        srcDir = dirs['installers'].join(name)
        for dest,src in dest_src.iteritems():
            size,crc = data_sizeCrc[dest]
            srcFull = srcDir.join(src)
            destFull = destDir.join(norm_ghost.get(dest,dest))
            if srcFull.exists():
                srcFull.copyTo(destFull)
                data_sizeCrcDate[dest] = (size,crc,destFull.mtime)
                count += 1
        return count

    def syncToData(self,package,projFiles):
        """Copies specified projFiles from Oblivion\Data to project directory."""
        srcDir = dirs['mods']
        projFiles = set(projFiles)
        srcProj = tuple((x,y) for x,y in self.refreshDataSizeCrc().iteritems() if x in projFiles)
        if not srcProj: return (0,0)
        #--Sync Files
        updated = removed = 0
        norm_ghost = Installer.getGhosted()
        projDir = dirs['installers'].join(package)
        for src,proj in srcProj:
            srcFull = srcDir.join(norm_ghost.get(src,src))
            projFull = projDir.join(proj)
            if not srcFull.exists():
                projFull.remove()
                removed += 1
            else:
                srcFull.copyTo(projFull)
                updated += 1
        self.removeEmpties(package)
        return (updated,removed)

    def packToArchive(self,project,archive,isSolid,progress=None,release=False):
        """Packs project to build directory. Release filters out developement material from the archive"""
        progress = progress or bolt.Progress()
        length = len(self.fileSizeCrcs)
        if not length: return
        archiveType = writeExts.get(archive.cext)
        if not archiveType:
            archive = GPath(archive.sbody + defaultExt).tail
            archiveType = writeExts.get(archive.cext)
        outDir = dirs['installers']
        outFile = outDir.join(archive)
        project = outDir.join(project)
        if archive.cext in noSolidExts:
            solid = ''
        else:
            solid = ('-ms=off','-ms=on')[isSolid]
        #--Dump file list
        out = self.tempList.open('w')
        if release:
            out.write('*thumbs.db\n')
            out.write('*desktop.ini\n')
            out.write('--*\\')
        out.close()
        #--Compress
        command = '7z.exe a "%s" -t"%s" %s -y -r -o"%s" -i!"%s\\*" -x@%s -scsWIN' % (outFile.temp.s, archiveType, solid, outDir.s, project.s, self.tempList.s)
        progress(0,_("%s\nCompressing files...") % archive.s)
        progress.setFull(1+length)
        ins = os.popen(command,'r')
        reCompressing = re.compile('Compressing\s+(.+)')
        regMatch = reCompressing.match
        reError = re.compile('Error: (.*)')
        regErrMatch = reError.match
        errorLine = []
        index = 0
        for line in ins:
            maCompressing = regMatch(line)
            if len(errorLine) or regErrMatch(line):
                errorLine.append(line)
            if maCompressing:
                progress(index,archive.s+_("\nCompressing files...\n%s") % maCompressing.group(1).strip())
                index += 1
        result = ins.close()
        if result:
            outFile.temp.remove()
            raise StateError(_("%s: Compression failed:\n%s") % (archive.s, "\n".join(errorLine)))
        outFile.untemp()
        self.tempList.remove()
    #--Omod Config ------------------------------------------------------------
    class OmodConfig:
        """Tiny little omod config class."""
        def __init__(self,name):
            self.name = name.s
            self.vMajor = 0
            self.vMinor = 1
            self.vBuild = 0
            self.author = ''
            self.email = ''
            self.website = ''
            self.abstract = ''

    def getOmodConfig(self,name):
        """Get obmm config file for project."""
        config = InstallerProject.OmodConfig(name)
        configPath = dirs['installers'].join(name,'omod conversion data','config')
        if configPath.exists():
            ins = bolt.StructFile(configPath.s,'rb')
            ins.read(1) #--Skip first four bytes
            config.name = ins.readNetString()
            config.vMajor, = ins.unpack('i',4)
            config.vMinor, = ins.unpack('i',4)
            for attr in ('author','email','website','abstract'):
                setattr(config,attr,ins.readNetString())
            ins.read(8) #--Skip date-time
            ins.read(1) #--Skip zip-compression
            #config['vBuild'], = ins.unpack('I',4)
            ins.close()
        return config

    def writeOmodConfig(self,name,config):
        """Write obmm config file for project."""
        configPath = dirs['installers'].join(name,'omod conversion data','config')
        configPath.head.makedirs()
        out = bolt.StructFile(configPath.temp.s,'wb')
        out.pack('B',4)
        out.writeNetString(config.name)
        out.pack('i',config.vMajor)
        out.pack('i',config.vMinor)
        for attr in ('author','email','website','abstract'):
            out.writeNetString(getattr(config,attr))
        out.write('\x74\x1a\x74\x67\xf2\x7a\xca\x88') #--Random date time
        out.pack('b',0) #--zip compression (will be ignored)
        out.write('\xFF\xFF\xFF\xFF')
        out.close()
        configPath.untemp()

#------------------------------------------------------------------------------
class InstallersData(bolt.TankData, DataDict):
    """Installers tank data. This is the data source for """
    status_color = {-20:'grey',-10:'red',0:'white',10:'orange',20:'yellow',30:'green'}
    type_textKey = {1:'BLACK',2:'NAVY'}

    def __init__(self):
        """Initialize."""
        self.dir = dirs['installers']
        self.bashDir = self.dir.join('Bash')
        #--Tank Stuff
        bolt.TankData.__init__(self,settings)
        self.tankKey = 'bash.installers'
        self.tankColumns = ['Package','Order','Modified','Size','Files']
        self.title = _('Installers')
        #--Default Params
        self.defaultParam('columns',self.tankColumns)
        self.defaultParam('colWidths',{
            'Package':100,'Package':100,'Order':10,'Group':60,'Modified':60,'Size':40,'Files':20})
        self.defaultParam('colAligns',{'Order':'RIGHT','Size':'RIGHT','Files':'RIGHT','Modified':'RIGHT'})
        #--Persistent data
        self.dictFile = PickleDict(self.bashDir.join('Installers.dat'))
        self.data = {}
        self.data_sizeCrcDate = {}
        self.crc_installer = {}
        self.converterFile = PickleDict(self.bashDir.join('Converters.dat'))
        self.srcCRC_converters = {}
        self.bcfCRC_converter = {}
        #--Volatile
        self.abnorm_sizeCrc = {} #--Normative sizeCrc, according to order of active packages
        self.bcfPath_sizeCrcDate = {}
        self.hasChanged = False
        self.loaded = False
        self.lastKey = GPath('==Last==')
        
    def setChanged(self,hasChanged=True):
        """Mark as having changed."""
        self.hasChanged = hasChanged

    def refresh(self,progress=None,what='DIONSC',fullRefresh=False):
        """Refresh info."""
        progress = progress or bolt.Progress()
        #--MakeDirs
        self.bashDir.makedirs()
        #--Archive invalidation
        if settings.get('bash.bsaRedirection'):
            oblivionIni.setBsaRedirection(True)
        #--Refresh Data
        changed = False
        if not self.loaded:
            progress(0,_("Loading Data..."))
            self.dictFile.load()
            self.converterFile.load()
            data = self.dictFile.data
            convertData = self.converterFile.data
            self.bcfCRC_converter = convertData.get('bcfCRC_converter',dict())
            self.srcCRC_converters = convertData.get('srcCRC_converters',dict())
            self.data = data.get('installers',{})
            self.data_sizeCrcDate = data.get('sizeCrcDate',{})
            self.crc_installer = data.get('crc_installer',{})
            self.updateDictFile()
            self.loaded = True
            changed = True
        #--Last marker
        if self.lastKey not in self.data:
            self.data[self.lastKey] = InstallerMarker(self.lastKey)
        #--Refresh Other
        if 'D' in what:
            changed |= Installer.refreshSizeCrcDate(
                dirs['mods'], self.data_sizeCrcDate, progress,
                settings['bash.installers.removeEmptyDirs'], fullRefresh)
        if 'I' in what: changed |= self.refreshInstallers(progress,fullRefresh)
        if 'O' in what or changed: changed |= self.refreshOrder()
        if 'N' in what or changed: changed |= self.refreshNorm()
        if 'S' in what or changed: changed |= self.refreshStatus()
        if 'C' in what or changed: changed |= self.refreshConverters(progress,fullRefresh)
        #--Done
        if changed: self.hasChanged = True
        return changed

    def updateDictFile(self):
        """Updates self.data to use new classes."""
        if self.dictFile.vdata.get('version',0): return
        #--Update to version 1
        for name in self.data.keys():
            installer = self.data[name]
            if isinstance(installer,Installer):
                self.data[name] = installer.__copy__(InstallerArchive)
        self.dictFile.vdata['version'] = 1

    def save(self):
        """Saves to pickle file."""
        if self.hasChanged:
            self.dictFile.data['installers'] = self.data
            self.dictFile.data['sizeCrcDate'] = self.data_sizeCrcDate
            self.dictFile.data['crc_installer'] = self.crc_installer
            self.dictFile.save()
            self.converterFile.data['bcfCRC_converter'] = self.bcfCRC_converter
            self.converterFile.data['srcCRC_converters'] = self.srcCRC_converters
            self.converterFile.save()
            self.hasChanged = False

    def getSorted(self,column,reverse):
        """Returns items sorted according to column and reverse."""
        data = self.data
        items = data.keys()
        if column == 'Package':
            items.sort(reverse=reverse)
        elif column == 'Files':
            items.sort(key=lambda x: len(data[x].fileSizeCrcs),reverse=reverse)
        else:
            items.sort()
            attr = column.lower()
            if column in ('Package','Group'):
                getter = lambda x: object.__getattribute__(data[x],attr).lower()
                items.sort(key=getter,reverse=reverse)
            else:
                getter = lambda x: object.__getattribute__(data[x],attr)
                items.sort(key=getter,reverse=reverse)
        #--Special sorters
        if settings['bash.installers.sortStructure']:
            items.sort(key=lambda x: data[x].type)
        if settings['bash.installers.sortActive']:
            items.sort(key=lambda x: not data[x].isActive)
        if settings['bash.installers.sortProjects']:
            items.sort(key=lambda x: not isinstance(data[x],InstallerProject))
        return items

    #--Item Info
    def getColumns(self,item=None):
        """Returns text labels for item or for row header if item == None."""
        columns = self.getParam('columns')
        if item == None: return columns[:]
        labels,installer = [],self.data[item]
        for column in columns:
            if column == 'Package':
                labels.append(item.s)
            elif column == 'Files':
                labels.append(formatInteger(len(installer.fileSizeCrcs)))
            else:
                value = object.__getattribute__(installer,column.lower())
                if column in ('Package','Group'):
                    pass
                elif column == 'Order':
                    value = `value`
                elif column == 'Modified':
                    value = formatDate(value)
                elif column == 'Size':
                    value = formatInteger(value/1024)+' KB'
                else:
                    raise ArgumentError(column)
                labels.append(value)
        return labels

    def getGuiKeys(self,item):
        """Returns keys for icon and text and background colors."""
        installer = self.data[item]
        #--Text
        if installer.type == 2 and len(installer.subNames) == 2:
            textKey = self.type_textKey[1]
        else:
            textKey = self.type_textKey.get(installer.type,'GREY')
        #--Background
        backKey = (installer.skipDirFiles and 'bash.installers.skipped') or None
        if installer.dirty_sizeCrc:
            backKey = 'bash.installers.dirty'
        elif installer.underrides:
            backKey = 'bash.installers.outOfOrder'
        #--Icon
        iconKey = ('off','on')[installer.isActive]+'.'+self.status_color[installer.status]
        if installer.type < 0:
            iconKey = 'corrupt'
        elif isinstance(installer,InstallerProject):
            iconKey += '.dir'
        return (iconKey,textKey,backKey)

    def getName(self,item):
        """Returns a string name of item for use in dialogs, etc."""
        return item.s

    def getColumn(self,item,column):
        """Returns item data as a dictionary."""
        raise UncodedError

    def setColumn(self,item,column,value):
        """Sets item values from a dictionary."""
        raise UncodedError

    #--Dict Functions -----------------------------------------------------------
    def __delitem__(self,item):
        """Delete an installer. Delete entry AND archive file itself."""
        if item == self.lastKey: return
        installer = self.data[item]
        apath = self.dir.join(item)
        if isinstance(installer,InstallerProject):
            apath.rmtree(safety='Installers')
        else:
            apath.remove()
        del self.data[item]

    def copy(self,item,destName,destDir=None):
        """Copies archive to new location."""
        if item == self.lastKey: return
        destDir = destDir or self.dir
        apath = self.dir.join(item)
        apath.copyTo(destDir.join(destName))
        if destDir == self.dir:
            self.data[destName] = installer = copy.copy(self.data[item])
            installer.isActive = False
            self.refreshOrder()
            self.moveArchives([destName],self.data[item].order+1)

    #--Refresh Functions --------------------------------------------------------
    def refreshInstallers(self,progress=None,fullRefresh=False):
        """Refresh installer data."""
        progress = progress or bolt.Progress()
        changed = False
        pending = set()
        projects = set()
        #--Current archives
        newData = {}
        newData[self.lastKey] = self.data[self.lastKey]
        installersJoin = dirs['installers'].join
        dataGet = self.data.get
        pendingAdd = pending.add
        for archive in dirs['installers'].list():
            apath = installersJoin(archive)
            isdir = apath.isdir()
            if isdir: projects.add(archive)
            if (isdir and archive != 'Bash' and archive != dirs['converters'].stail) or archive.cext in readExts:
                installer = dataGet(archive)
                if not installer:
                    pendingAdd(archive)
                elif (isdir and not installer.refreshed) or (
                    (installer.size,installer.modified) != (apath.size,apath.mtime)):
                    newData[archive] = installer
                    pendingAdd(archive)
                else:
                    newData[archive] = installer
        if fullRefresh: pending |= set(newData)
        changed = bool(pending) or (len(newData) != len(self.data))
        #--New/update crcs?
        progressSetFull = progress.setFull
        newDataGet = newData.get
        newDataSetDefault = newData.setdefault
        for subPending,iClass in zip(
            (pending - projects, pending & projects),
            (InstallerArchive, InstallerProject)
            ):
            if not subPending: continue
            progress(0,_("Scanning Packages..."))
            progressSetFull(len(subPending))
            for index,package in enumerate(sorted(subPending)):
                progress(index,_("Scanning Packages...\n")+package.s)
                installer = newDataGet(package)
                if not installer:
                    installer = newDataSetDefault(package,iClass(package))
                apath = installersJoin(package)
                try: installer.refreshBasic(apath,SubProgress(progress,index,index+1))
                except InstallerArchiveError:
                    installer.type = -1
        self.data = newData
        self.crc_installer = dict((x.crc,x) for x in self.data.values())
        return changed

    def refreshInstallersNeeded(self):
        """Returns true if refreshInstallers is necessary. (Point is to skip use
        of progress dialog when possible."""
        installers = set([])
        installersJoin = dirs['installers'].join
        dataGet = self.data.get
        installersAdd = installers.add
        for item in dirs['installers'].list():
            apath = installersJoin(item)
            if settings['bash.installers.autoRefreshProjects']:
                if (apath.isdir() and item != 'Bash' and item != dirs['converters'].stail) or (apath.isfile() and item.cext in readExts):
                    installer = dataGet(item)
                    if not installer or (installer.size,installer.modified) != (apath.size,apath.getmtime(True)):
                        return True
                    installersAdd(item)
            else:
                if apath.isfile() and item.cext in readExts:
                    installer = dataGet(item)
                    if not installer or (installer.size,installer.modified) != (apath.size,apath.getmtime(True)):
                        return True
                    installersAdd(item)
        #--Added/removed packages?
        if settings['bash.installers.autoRefreshProjects']:
            return installers != set(x for x,y in self.data.iteritems() if not isinstance(y,InstallerMarker))
        else:
            return installers != set(x for x,y in self.data.iteritems() if isinstance(y,InstallerArchive))
    
    def refreshConvertersNeeded(self):
        """Returns true if refreshConverters is necessary. (Point is to skip use
        of progress dialog when possible."""
        if not len(self.bcfPath_sizeCrcDate):
            return True
        archives = set([])
        convertersJoin = dirs['converters'].join
        converterGet = self.bcfPath_sizeCrcDate.get
        bcfPath_sizeCrcDate = self.bcfPath_sizeCrcDate
        archivesAdd = archives.add
        for archive in dirs['converters'].list():
            apath = convertersJoin(archive)
            if apath.isfile() and archive.cext in (defaultExt):
                size,crc,modified = converterGet(apath,(None,None,None))
                if crc is None or (size,modified) != (apath.size,apath.mtime):
                    return True
                archivesAdd(apath)
        #--Added/removed packages?
        return archives != set(self.bcfPath_sizeCrcDate)
    
    def refreshOrder(self):
        """Refresh installer status."""
        changed = False
        data = self.data
        ordered,pending = [],[]
        orderedAppend = ordered.append
        pendingAppend = pending.append
        for archive,installer in self.data.iteritems():
            if installer.order >= 0:
                orderedAppend(archive)
            else:
                pendingAppend(archive)
        pending.sort()
        ordered.sort()
        ordered.sort(key=lambda x: data[x].order)
        if self.lastKey in ordered:
            index = ordered.index(self.lastKey)
            ordered[index:index] = pending
        else:
            ordered += pending
        order = 0
        for archive in ordered:
            if data[archive].order != order:
                data[archive].order = order
                changed = True
            order += 1
        return changed

    def refreshNorm(self):
        """Refresh self.abnorm_sizeCrc."""
        data = self.data
        active = [x for x in data if data[x].isActive]
        active.sort(key=lambda x: data[x].order)
        #--norm
        norm_sizeCrc = {}
        normUpdate = norm_sizeCrc.update
        for package in active:
            normUpdate(data[package].data_sizeCrc)
        #--Abnorm
        abnorm_sizeCrc = {}
        data_sizeCrcDate = self.data_sizeCrcDate
        dataGet = data_sizeCrcDate.get
        for path,sizeCrc in norm_sizeCrc.iteritems():
            sizeCrcDate = dataGet(path)
            if sizeCrcDate and sizeCrc != sizeCrcDate[:2]:
                abnorm_sizeCrc[path] = sizeCrcDate[:2]
        (self.abnorm_sizeCrc,oldAbnorm_sizeCrc) = (abnorm_sizeCrc,self.abnorm_sizeCrc)
        return abnorm_sizeCrc != oldAbnorm_sizeCrc

    def refreshStatus(self):
        """Refresh installer status."""
        changed = False
        for installer in self.data.itervalues():
            changed |= installer.refreshStatus(self)
        return changed

    def refreshConverters(self,progress=None,fullRefresh=False):
        """Refreshes converter status, and moves duplicate BCFs out of the way"""
        progress = progress or bolt.Progress()
        changed = False
        pending = set()
        bcfCRC_converter = self.bcfCRC_converter
        convJoin = dirs['converters'].join
        #--Current converters
        newData = dict()
        if fullRefresh:
            self.bcfPath_sizeCrcDate.clear()
            self.srcCRC_converters.clear()
        for archive in dirs['converters'].list():
            bcfPath = convJoin(archive)
            if bcfPath.isdir(): continue
            if archive.cext in (defaultExt) and archive.csbody[-4:] == '-bcf':
                size,crc,modified = self.bcfPath_sizeCrcDate.get(bcfPath,(None,None,None))
                if crc == None or (size,modified) != (bcfPath.size,bcfPath.mtime):
                    crc = bcfPath.crc
                    (size,modified) = (bcfPath.size,bcfPath.mtime)
                    if crc in bcfCRC_converter and bcfPath != bcfCRC_converter[crc].fullPath and bcfCRC_converter[crc].fullPath.exists():
                        bcfPath.moveTo(dirs['dupeBCFs'].join(bcfPath.tail))
                        self.bcfPath_sizeCrcDate.pop(bcfPath,None)
                        continue
                self.bcfPath_sizeCrcDate[bcfPath] = (size, crc, modified)
                if fullRefresh or crc not in bcfCRC_converter:
                    pending.add(archive)
                else:
                    newData[crc] = bcfCRC_converter[crc]
                    newData[crc].fullPath = bcfPath
        changed = bool(pending) or (len(newData) != len(bcfCRC_converter))
        #--New/update crcs?
        self.bcfCRC_converter = newData
        self.srcCRC_converters
        if bool(pending):
            progress(0,_("Scanning Converters..."))
            progress.setFull(len(pending))
            for index,archive in enumerate(sorted(pending)):
                progress(index,_("Scanning Converter...\n")+archive.s)
                self.addConverter(archive)
        self.pruneConverters()
        return changed

    def pruneConverters(self):
        """Remove any converters that no longer exist."""
        srcCRC_converters = self.srcCRC_converters
        for srcCRC in srcCRC_converters.keys():
            for converter in srcCRC_converters[srcCRC][:]:
                if not (isinstance(converter.fullPath,bolt.Path) and converter.fullPath.exists()):
                    srcCRC_converters[srcCRC].remove(converter)
                    self.removeConverter(converter)
            if len(self.srcCRC_converters[srcCRC]) == 0:
                del srcCRC_converters[srcCRC]

    def addConverter(self,converter):
        """Links the new converter to installers"""
        if isinstance(converter,basestring):
            #--Adding a new file
            converter = GPath(converter).tail
        if isinstance(converter,InstallerConverter):
            #--Adding a new InstallerConverter
            newConverter = converter
        else:
            #--Adding a new file
            newConverter = InstallerConverter(converter)
        #--Check if overriding an existing converter
        oldConverter = self.bcfCRC_converter.get(newConverter.crc)
        if oldConverter:
            oldConverter.fullPath.moveTo(dirs['dupeBCFs'].join(oldConverter.fullPath.tail))
            self.removeConverter(oldConverter)
        #--Link converter to Bash
        srcCRC_converters = self.srcCRC_converters
        [srcCRC_converters[srcCRC].append(newConverter) for srcCRC in newConverter.srcCRCs if srcCRC_converters.setdefault(srcCRC,[newConverter]) != [newConverter]]
        self.bcfCRC_converter[newConverter.crc] = newConverter
        self.bcfPath_sizeCrcDate[newConverter.fullPath] = (newConverter.fullPath.size, newConverter.crc, newConverter.fullPath.mtime)

    def removeConverter(self,converter):
        """Unlinks the old converter from installers and deletes it"""
        if isinstance(converter,bolt.Path):
            #--Removing by filepath
            converter = converter.stail
        if isinstance(converter,InstallerConverter):
            #--Removing existing converter
            oldConverter = self.bcfCRC_converter.pop(converter.crc,None)
            self.bcfPath_sizeCrcDate.pop(converter.fullPath,None)
        else:
            #--Removing by filepath
            bcfPath = dirs['converters'].join(converter)
            oldConverter = self.bcfCRC_converter.pop(bcfPath.crc,None)
            self.bcfPath_sizeCrcDate.pop(bcfPath,None)
        #--Sanity check
        if oldConverter is None: return
        #--Unlink the converter from Bash
        for srcCRC in self.srcCRC_converters.keys():
            for converter in self.srcCRC_converters[srcCRC][:]:
                if converter is oldConverter:
                    self.srcCRC_converters[srcCRC].remove(converter)
            if len(self.srcCRC_converters[srcCRC]) == 0:
                del self.srcCRC_converters[srcCRC]
        del oldConverter

    #--Operations -------------------------------------------------------------
    def moveArchives(self,moveList,newPos):
        """Move specified archives to specified position."""
        moveSet = set(moveList)
        data = self.data
        orderKey = lambda x: data[x].order
        newList = [x for x in sorted(data,key=orderKey) if x not in moveSet]
        moveList.sort(key=orderKey)
        newList[newPos:newPos] = moveList
        for index,archive in enumerate(newList):
            data[archive].order = index
        self.setChanged()

    @staticmethod
    def updateTable(destFiles, value):
        for i in destFiles:
            if reModExt.match(i.cext):
                modInfos.table.setItem(i, 'installer', value)
            elif i.head.cs == 'ini tweaks':
                iniInfos.table.setItem(i.tail, 'installer', value)

    def install(self,archives,progress=None,last=False,override=True):
        """Install selected archives.
        what:
            'MISSING': only missing files.
            Otherwise: all (unmasked) files.
        """
        progress = progress or bolt.Progress()
        #--Mask and/or reorder to last
        mask = set()
        if last:
            self.moveArchives(archives,len(self.data))
        else:
            maxOrder = max(self[x].order for x in archives)
            for installer in self.data.itervalues():
                if installer.order > maxOrder and installer.isActive:
                    mask |= set(installer.data_sizeCrc)
        #--Install archives in turn
        progress.setFull(len(archives))
        archives.sort(key=lambda x: self[x].order,reverse=True)
        for index,archive in enumerate(archives):
            progress(index,archive.s)
            installer = self[archive]
            destFiles = set(installer.data_sizeCrc) - mask
            if not override:
                destFiles &= installer.missingFiles
            if destFiles:
                installer.install(archive,destFiles,self.data_sizeCrcDate,SubProgress(progress,index,index+1))
                InstallersData.updateTable(destFiles, archive.s)
            installer.isActive = True
            mask |= set(installer.data_sizeCrc)
        self.refreshStatus()

    def uninstall(self,unArchives,progress=None):
        """Uninstall selected archives."""
        unArchives = set(unArchives)
        data = self.data
        data_sizeCrcDate = self.data_sizeCrcDate
        getArchiveOrder =  lambda x: self[x].order
        #--Determine files to remove and files to restore. Keep in mind that
        #  that multipe input archives may be interspersed with other archives
        #  that may block (mask) them from deleting files and/or may provide
        #  files that should be restored to make up for previous files. However,
        #  restore can be skipped, if existing files matches the file being
        #  removed.
        masked = set()
        removes = set()
        restores = {}
        #--March through archives in reverse order...
        for archive in sorted(data,key=getArchiveOrder,reverse=True):
            installer = data[archive]
            #--Uninstall archive?
            if archive in unArchives:
                for data_sizeCrc in (installer.data_sizeCrc,installer.dirty_sizeCrc):
                    for file,sizeCrc in data_sizeCrc.iteritems():
                        sizeCrcDate = data_sizeCrcDate.get(file)
                        if file not in masked and sizeCrcDate and sizeCrcDate[:2] == sizeCrc:
                            removes.add(file)
            #--Other active archive. May undo previous removes, or provide a restore file.
            #  And/or may block later uninstalls.
            elif installer.isActive:
                files = set(installer.data_sizeCrc)
                myRestores = (removes & files) - set(restores)
                for file in myRestores:
                    if installer.data_sizeCrc[file] != data_sizeCrcDate.get(file,(0,0,0))[:2]:
                        restores[file] = archive
                    removes.discard(file)
                masked |= files
        #--Remove files
        emptyDirs = set()
        modsDir = dirs['mods']
        InstallersData.updateTable(removes, '')
        for file in removes:
            path = modsDir.join(file)
            path.remove()
            (path+'.ghost').remove()
            del data_sizeCrcDate[file]
            emptyDirs.add(path.head)
        #--Remove empties
        for emptyDir in emptyDirs:
            if emptyDir.isdir() and not emptyDir.list():
                emptyDir.removedirs()
        #--De-activate
        for archive in unArchives:
            data[archive].isActive = False
        #--Restore files
        restoreArchives = sorted(set(restores.itervalues()),key=getArchiveOrder,reverse=True)
        if ['bash.installers.autoAnneal'] and restoreArchives:
            progress.setFull(len(restoreArchives))
            for index,archive in enumerate(restoreArchives):
                progress(index,archive.s)
                installer = data[archive]
                destFiles = set(x for x,y in restores.iteritems() if y == archive)
                if destFiles:
                    installer.install(archive,destFiles,data_sizeCrcDate,
                        SubProgress(progress,index,index+1))
                    InstallersData.updateTable(destFiles, archive.s)
        #--Done
        self.refreshStatus()

    def anneal(self,anPackages=None,progress=None):
        """Anneal selected packages. If no packages are selected, anneal all.
        Anneal will:
        * Correct underrides in anPackages.
        * Install missing files from active anPackages."""
        data = self.data
        data_sizeCrcDate = self.data_sizeCrcDate
        anPackages = set(anPackages or data)
        getArchiveOrder =  lambda x: data[x].order
        #--Get remove/refresh files from anPackages
        removes = set()
        for package in anPackages:
            installer = data[package]
            removes |= installer.underrides
            if installer.isActive:
                removes |= installer.missingFiles
                removes |= set(installer.dirty_sizeCrc)
            installer.dirty_sizeCrc.clear()
        #--March through packages in reverse order...
        restores = {}
        for package in sorted(data,key=getArchiveOrder,reverse=True):
            installer = data[package]
            #--Other active package. May provide a restore file.
            #  And/or may block later uninstalls.
            if installer.isActive:
                files = set(installer.data_sizeCrc)
                myRestores = (removes & files) - set(restores)
                for file in myRestores:
                    if installer.data_sizeCrc[file] != data_sizeCrcDate.get(file,(0,0,0))[:2]:
                        restores[file] = package
                    removes.discard(file)
        #--Remove files
        emptyDirs = set()
        modsDir = dirs['mods']
        InstallersData.updateTable(removes, '')
        for file in removes:
            path = modsDir.join(file)
            path.remove()
            (path+'.ghost').remove()
            data_sizeCrcDate.pop(file,None)
            emptyDirs.add(path.head)
        #--Remove empties
        for emptyDir in emptyDirs:
            if emptyDir.isdir() and not emptyDir.list():
                emptyDir.removedirs()
        #--Restore files
        restoreArchives = sorted(set(restores.itervalues()),key=getArchiveOrder,reverse=True)
        if restoreArchives:
            progress.setFull(len(restoreArchives))
            for index,package in enumerate(restoreArchives):
                progress(index,package.s)
                installer = data[package]
                destFiles = set(x for x,y in restores.iteritems() if y == package)
                if destFiles:
                    installer.install(package,destFiles,data_sizeCrcDate,
                        SubProgress(progress,index,index+1))
                    InstallersData.updateTable(destFiles, package.s)

    def getConflictReport(self,srcInstaller,mode):
        """Returns report of overrides for specified package for display on conflicts tab.
        mode: O: Overrides; U: Underrides"""
        data = self.data
        srcOrder = srcInstaller.order
        conflictsMode = (mode == 'OVER')
        if conflictsMode:
            #mismatched = srcInstaller.mismatchedFiles | srcInstaller.missingFiles
            mismatched = set(srcInstaller.data_sizeCrc)
        else:
            mismatched = srcInstaller.underrides
        showInactive = conflictsMode and settings['bash.installers.conflictsReport.showInactive']
        showLower = conflictsMode and settings['bash.installers.conflictsReport.showLower']
        if not mismatched: return ''
        src_sizeCrc = srcInstaller.data_sizeCrc
        packConflicts = []
        getArchiveOrder =  lambda x: data[x].order
        for package in sorted(self.data,key=getArchiveOrder):
            installer = data[package]
            if installer.order == srcOrder: continue
            if not showInactive and not installer.isActive: continue
            if not showLower and installer.order < srcOrder: continue
            curConflicts = Installer.sortFiles([x.s for x,y in installer.data_sizeCrc.iteritems()
                if x in mismatched and y != src_sizeCrc[x]])
            if curConflicts: packConflicts.append((installer.order,package.s,curConflicts))
        #--Unknowns
        isHigher = -1
        buff = cStringIO.StringIO()
        for order,package,files in packConflicts:
            if showLower and (order > srcOrder) != isHigher:
                isHigher = (order > srcOrder)
                buff.write('= %s %s\n' % ((_('Lower'),_('Higher'))[isHigher],'='*40))
            buff.write('==%d== %s\n'% (order,package))
            for file in files:
                buff.write(file)
                buff.write('\n')
            buff.write('\n')
        report = buff.getvalue()
        if not conflictsMode and not report and not srcInstaller.isActive:
            report = _("No Underrides. Mod is not completely un-installed.")
        return report
    def getPackageList(self):
        """Returns package list as text."""
        #--Setup
        log = bolt.LogFile(cStringIO.StringIO())
        log.out.write('[codebox]')
        log.setHeader(_('Bain Packages:'))
        orderKey = lambda x: self.data[x].order
        allPackages = sorted(self.data,key=orderKey)
        #--List
        modIndex,header = 0, None
        for package in allPackages:
            prefix = '%03d' % (self.data[package].order)
            if isinstance(self.data[package],InstallerMarker):
                log(_('%s - %s') % (prefix,package.s))
            else:
                log(_('%s - %s (%08X)') % (prefix,package.s,self.data[package].crc))
        log('[/codebox]')
        return bolt.winNewLines(log.out.getvalue())
# Utilities -------------------------------------------------------------------
#------------------------------------------------------------------------------
class ActorFactions:
    """Factions for npcs and creatures with functions for importing/exporting from/to mod/text file."""
    def __init__(self,aliases=None):
        """Initialize."""
        self.types = (MreCrea,MreNpc)
        self.type_id_factions = {'CREA':{},'NPC_':{}} #--factions = type_id_factions[type][longid]
        self.id_eid = {}
        self.aliases = aliases or {}
        self.gotFactions = set()

    def readFactionEids(self,modInfo):
        """Extracts faction editor ids from modInfo and its masters."""
        loadFactory= LoadFactory(False,MreFact)
        for modName in (modInfo.header.masters + [modInfo.name]):
            if modName in self.gotFactions: continue
            modFile = ModFile(modInfos[modName],loadFactory)
            modFile.load(True)
            mapper = modFile.getLongMapper()
            for record in modFile.FACT.getActiveRecords():
                self.id_eid[mapper(record.fid)] = record.eid
            self.gotFactions.add(modName)

    def readFromMod(self,modInfo):
        """Imports eids from specified mod."""
        self.readFactionEids(modInfo)
        type_id_factions,types,id_eid = self.type_id_factions,self.types,self.id_eid
        loadFactory= LoadFactory(False,*types)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        for type in (x.classType for x in types):
            typeBlock = modFile.tops.get(type,None)
            if not typeBlock: continue
            id_factions = type_id_factions[type]
            for record in typeBlock.getActiveRecords():
                longid = mapper(record.fid)
                if record.factions:
                    id_eid[longid] = record.eid
                    id_factions[longid] = [(mapper(x.faction),x.rank) for x in record.factions]

    def writeToMod(self,modInfo):
        """Exports eids to specified mod."""
        type_id_factions,types = self.type_id_factions,self.types
        loadFactory= LoadFactory(True,*types)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        shortMapper = modFile.getShortMapper()
        changed = {'CREA':0,'NPC':0}
        for type in (x.classType for x in types):
            id_factions = type_id_factions.get(type,None)
            typeBlock = modFile.tops.get(type,None)
            if not id_factions or not typeBlock: continue
            for record in typeBlock.records:
                longid = mapper(record.fid)
                if longid not in id_factions: continue
                newFactions = set(id_factions[longid])
                curFactions = set((mapper(x.faction),x.rank) for x in record.factions)
                changed = newFactions - curFactions
                if not changed: continue
                for faction,rank in changed:
                    faction = shortMapper(faction)
                    for entry in record.factions:
                        if entry.faction == faction:
                            entry.rank = rank
                            break
                    else:
                        entry = MelObject()
                        entry.faction = faction
                        entry.rank = rank
                        entry.unused1 = 'ODB'
                        record.factions.append(entry)
                    record.setChanged()
                changed[type] += 1
        #--Done
        if sum(changed.values()): modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Imports eids from specified text file."""
        type_id_factions,id_eid = self.type_id_factions, self.id_eid
        aliases = self.aliases
        ins = bolt.CsvReader(textPath)
        for fields in ins:
            if len(fields) < 8 or fields[3][:2] != '0x': continue
            type,aed,amod,aobj,fed,fmod,fobj,rank = fields[:9]
            amod = GPath(amod)
            fmod = GPath(fmod)
            aid = (aliases.get(amod,amod),int(aobj[2:],16))
            fid = (aliases.get(fmod,fmod),int(fobj[2:],16))
            rank = int(rank)
            id_factions = type_id_factions[type]
            factions = id_factions.get(aid)
            if factions is None:
                factions = id_factions[aid] = []
            for index,entry in enumerate(factions):
                if entry[0] == fid:
                    factions[index] = (fid,rank)
                    break
            else:
                factions.append((fid,rank))
        ins.close()

    def writeToText(self,textPath):
        """Exports eids to specified text file."""
        type_id_factions,id_eid = self.type_id_factions, self.id_eid
        headFormat = '"%s","%s","%s","%s","%s","%s","%s","%s"\n'
        rowFormat = '"%s","%s","%s","0x%06X","%s","%s","0x%06X","%s"\n'
        out = textPath.open('w')
        out.write(headFormat % (_('Type'),_('Actor Eid'),_('Actor Mod'),_('Actor Object'),_('Faction Eid'),_('Faction Mod'),_('Faction Object'),_('Rank')))
        for type in sorted(type_id_factions):
            id_factions = type_id_factions[type]
            for id in sorted(id_factions,key = lambda x: id_eid.get(x)):
                actorEid = id_eid.get(id,'Unknown')
                for faction, rank in sorted(id_factions[id],key=lambda x: id_eid.get(x[0])):
                    factionEid = id_eid.get(faction,'Unknown')
                    out.write(rowFormat % (type,actorEid,id[0].s,id[1],factionEid,faction[0].s,faction[1],rank))
        out.close()

#------------------------------------------------------------------------------
class ActorLevels:
    """Package: Functions for manipulating actor levels."""

    @staticmethod
    def dumpText(modInfo,outPath,progress=None):
        """Export NPC level data to text file."""
        progress = progress or bolt.Progress()
        #--Mod levels
        progress(0,_('Loading ')+modInfo.name.s)
        loadFactory= LoadFactory(False,MreNpc)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        offsetFlag = 0x80
        npcLevels = {}
        for npc in modFile.NPC_.records:
            if npc.flags.pcLevelOffset:
                npcLevels[npc.fid] = (npc.eid,npc.level,npc.calcMin, npc.calcMax)
        #--Oblivion Levels (for comparison)
        progress(0.25,_('Loading Oblivion.esm'))
        obFactory= LoadFactory(False,MreNpc)
        obInfo = modInfos[GPath('Oblivion.esm')]
        obFile = ModFile(obInfo,obFactory)
        obFile.load(True)
        obNPCs = {}
        for npc in obFile.NPC_.records:
            obNPCs[npc.fid] = npc
        #--File, column headings
        progress(0.75,_('Writing ')+outPath.stail)
        out = outPath.open('w')
        headings = (_('Fid'),_('EditorId'),_('Offset'),_('CalcMin'),_('CalcMax'),_(''),
            _('Old bOffset'),_('Old Offset'),_('Old CalcMin'),_('Old CalcMax'),)
        out.write('"'+('","'.join(headings))+'"\n')
        #--Sort by eid and print
        for fid in sorted(npcLevels.keys(),key=lambda a: npcLevels[a][0]):
            npcLevel = npcLevels[fid]
            out.write('"0x%08X","%s",%d,%d,%d' % ((fid,)+npcLevel))
            obNPC = obNPCs.get(fid,None)
            if obNPC:
                flagged = (obNPC.flags.pcLevelOffset and offsetFlag) and 1 or 0
                out.write(',,%d,%d,%d,%d' % (flagged,obNPC.level,obNPC.calcMin,obNPC.calcMax))
            out.write('\n')
        out.close()
        progress(1,_('Done'))

    @staticmethod
    def loadText(modInfo,inPath,progress=None):
        """Import NPC level data from text file."""
        inPath = GPath(inPath)
        progress = progress or bolt.Progress()
        #--Sort and print
        progress(0,_('Reading ')+inPath.stail)
        inNPCs = {}
        ins = bolt.CsvReader(inPath)
        for fields in ins:
            if '0x' not in fields[0]: continue
            inNPCs[int(fields[0],0)] = tuple(map(int,fields[2:5]))
        ins.close()
        #--Load Mod
        progress(0.25,_('Loading ')+modInfo.name.s)
        loadFactory= LoadFactory(True,MreNpc)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        offsetFlag = 0x80
        npcLevels = {}
        for npc in modFile.NPC_.records:
            if npc.fid in inNPCs:
                (npc.level, npc.calcMin, npc.calcMax) = inNPCs[npc.fid]
                npc.setChanged()
        progress(0.5,_('Saving ')+modInfo.name.s)
        modFile.safeSave()
        progress(1.0,_('Done'))

#------------------------------------------------------------------------------
class EditorIds:
    """Editor ids for records, with functions for importing/exporting from/to mod/text file."""
    def __init__(self,types=None,aliases=None):
        """Initialize."""
        self.type_id_eid = {} #--eid = eids[type][longid]
        self.old_new = {}
        if types:
            self.types = types
        else:
            self.types = set(MreRecord.simpleTypes)
            self.types.discard('CELL')
        self.aliases = aliases or {}

    def readFromMod(self,modInfo):
        """Imports eids from specified mod."""
        type_id_eid,types = self.type_id_eid,self.types
        classes = [MreRecord.type_class[x] for x in types]
        loadFactory= LoadFactory(False,*classes)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        for type in types:
            typeBlock = modFile.tops.get(type)
            if not typeBlock: continue
            if type not in type_id_eid: type_id_eid[type] = {}
            id_eid = type_id_eid[type]
            for record in typeBlock.getActiveRecords():
                longid = mapper(record.fid)
                if record.eid: id_eid[longid] = record.eid

    def writeToMod(self,modInfo):
        """Exports eids to specified mod."""
        type_id_eid,types = self.type_id_eid,self.types
        classes = [MreRecord.type_class[x] for x in types]
        loadFactory= LoadFactory(True,*classes)
        loadFactory.addClass(MreScpt)
        loadFactory.addClass(MreQust)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        changed = []
        for type in types:
            id_eid = type_id_eid.get(type,None)
            typeBlock = modFile.tops.get(type,None)
            if not id_eid or not typeBlock: continue
            for record in typeBlock.records:
                longid = mapper(record.fid)
                newEid = id_eid.get(longid)
                oldEid = record.eid
                if newEid and record.eid and newEid != oldEid:
                    record.eid = newEid
                    record.setChanged()
                    changed.append((oldEid,newEid))
        #--Update scripts
        old_new = dict(self.old_new)
        old_new.update(dict([(oldEid.lower(),newEid) for oldEid,newEid in changed]))
        changed.extend(self.changeScripts(modFile,old_new))
        #--Done
        if changed: modFile.safeSave()
        return changed

    def changeScripts(self,modFile,old_new):
        """Changes scripts in modfile according to changed."""
        changed = []
        if not old_new: return changed
        reWord = re.compile('\w+')
        def subWord(match):
            word = match.group(0)
            newWord = old_new.get(word.lower())
            if not newWord:
                return word
            else:
                return newWord
        #--Scripts
        for script in sorted(modFile.SCPT.records,key=attrgetter('eid')):
            if not script.scriptText: continue
            newText = reWord.sub(subWord,script.scriptText)
            if newText != script.scriptText:
                header = '\r\n\r\n; %s %s\r\n' % (script.eid,'-'*(77-len(script.eid)))
                script.scriptText = newText
                script.setChanged()
                changed.append((_("Script"),script.eid))
        #--Quest Scripts
        for quest in sorted(modFile.QUST.records,key=attrgetter('eid')):
            questChanged = False
            for stage in quest.stages:
                for entry in stage.entries:
                    oldScript = entry.scriptText
                    if not oldScript: continue
                    newScript = reWord.sub(subWord,oldScript)
                    if newScript != oldScript:
                        entry.scriptText = newScript
                        questChanged = True
            if questChanged:
                changed.append((_("Quest"),quest.eid))
                quest.setChanged()
        #--Done
        return changed

    def readFromText(self,textPath):
        """Imports eids from specified text file."""
        type_id_eid = self.type_id_eid
        aliases = self.aliases
        ins = bolt.CsvReader(textPath)
        reNewEid = re.compile('^[a-zA-Z][a-zA-Z0-9]+$')
        for fields in ins:
            if len(fields) < 4 or fields[2][:2] != '0x': continue
            type,mod,objectIndex,eid = fields[:4]
            mod = GPath(mod)
            longid = (aliases.get(mod,mod),int(objectIndex[2:],16))
            if not reNewEid.match(eid):
                continue
            elif type in type_id_eid:
                type_id_eid[type][longid] = eid
            else:
                type_id_eid[type] = {longid:eid}
            #--Explicit old to new def? (Used for script updating.)
            if len(fields) > 4:
                self.old_new[fields[4].lower()] = fields[3]
        ins.close()

    def writeToText(self,textPath):
        """Exports eids to specified text file."""
        type_id_eid = self.type_id_eid
        headFormat = '"%s","%s","%s","%s"\n'
        rowFormat = '"%s","%s","0x%06X","%s"\n'
        out = textPath.open('w')
        out.write(headFormat % (_('Type'),_('Mod Name'),_('ObjectIndex'),_('Editor Id')))
        for type in sorted(type_id_eid):
            id_eid = type_id_eid[type]
            for id in sorted(id_eid,key = lambda a: id_eid[a]):
                out.write(rowFormat % (type,id[0].s,id[1],id_eid[id]))
        out.close()

#------------------------------------------------------------------------------
class FactionRelations:
    """Faction relations."""
    def __init__(self,aliases=None):
        """Initialize."""
        self.id_relations = {} #--(otherLongid,otherDisp) = id_relation[longid]
        self.id_eid = {} #--For all factions.
        self.aliases = aliases or {}
        self.gotFactions = set()

    def readFactionEids(self,modInfo):
        """Extracts faction editor ids from modInfo and its masters."""
        loadFactory= LoadFactory(False,MreFact)
        for modName in (modInfo.header.masters + [modInfo.name]):
            if modName in self.gotFactions: continue
            modFile = ModFile(modInfos[modName],loadFactory)
            modFile.load(True)
            mapper = modFile.getLongMapper()
            for record in modFile.FACT.getActiveRecords():
                self.id_eid[mapper(record.fid)] = record.eid
            self.gotFactions.add(modName)

    def readFromMod(self,modInfo):
        """Imports faction relations from specified mod."""
        self.readFactionEids(modInfo)
        loadFactory= LoadFactory(False,MreFact)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        modFile.convertToLongFids(('FACT',))
        for record in modFile.FACT.getActiveRecords():
            #--Following is a bit messy. If already have relations for a given mod,
            #  want to do an in-place update. Otherwise do an append.
            relations = self.id_relations.get(record.fid)
            if relations == None:
                relations = self.id_relations[record.fid] = []
            other_index = dict((y[0],x) for x,y in enumerate(relations))
            for relation in record.relations:
                other,disp = relation.faction,relation.mod
                if other in other_index:
                    relations[other_index[other]] = (other,disp)
                else:
                    relations.append((other,disp))

    def readFromText(self,textPath):
        """Imports faction relations from specified text file."""
        id_relations,id_eid = self.id_relations, self.id_eid
        aliases = self.aliases
        ins = bolt.CsvReader(textPath)
        for fields in ins:
            if len(fields) < 7 or fields[2][:2] != '0x': continue
            med,mmod,mobj,oed,omod,oobj,disp = fields[:9]
            mid = (GPath(aliases.get(mmod,mmod)),int(mobj[2:],16))
            oid = (GPath(aliases.get(omod,omod)),int(oobj[2:],16))
            disp = int(disp)
            relations = id_relations.get(mid)
            if relations is None:
                relations = id_relations[mid] = []
            for index,entry in enumerate(relations):
                if entry[0] == oid:
                    relations[index] = (oid,disp)
                    break
            else:
                relations.append((oid,disp))
        ins.close()

    def writeToText(self,textPath):
        """Exports faction relations to specified text file."""
        id_relations,id_eid = self.id_relations, self.id_eid
        headFormat = '%s","%s","%s","%s","%s","%s","%s"\n'
        rowFormat = '"%s","%s","0x%06X","%s","%s","0x%06X","%s"\n'
        out = textPath.open('w')
        out.write(headFormat % (_('Main Eid'),_('Main Mod'),_('Main Object'),_('Other Eid'),_('Other Mod'),_('Other Object'),_('Disp')))
        for main in sorted(id_relations,key = lambda x: id_eid.get(x)):
            mainEid = id_eid.get(main,'Unknown')
            for other, disp in sorted(id_relations[main],key=lambda x: id_eid.get(x[0])):
                otherEid = id_eid.get(other,'Unknown')
                out.write(rowFormat % (mainEid,main[0].s,main[1],otherEid,other[0].s,other[1],disp))
        out.close()

#------------------------------------------------------------------------------
class FidReplacer:
    """Replaces one set of fids with another."""

    def __init__(self,types=None,aliases=None):
        """Initialize."""
        self.types = types or MreRecord.simpleTypes
        self.aliases = aliases or {} #--For aliasing mod names
        self.old_new = {} #--Maps old fid to new fid
        self.old_eid = {} #--Maps old fid to old editor id
        self.new_eid = {} #--Maps new fid to new editor id

    def readFromText(self,textPath):
        """Reads replacment data from specified text file."""
        old_new,old_eid,new_eid = self.old_new,self.old_eid,self.new_eid
        aliases = self.aliases
        ins = bolt.CsvReader(textPath)
        pack,unpack = struct.pack,struct.unpack
        for fields in ins:
            if len(fields) < 7 or fields[2][:2] != '0x' or fields[6][:2] != '0x': continue
            oldMod,oldObj,oldEid,newEid,newMod,newObj = fields[1:7]
            oldMod,newMod = map(GPath,(oldMod,newMod))
            oldId = (GPath(aliases.get(oldMod,oldMod)),int(oldObj,16))
            newId = (GPath(aliases.get(newMod,newMod)),int(newObj,16))
            old_new[oldId] = newId
            old_eid[oldId] = oldEid
            new_eid[newId] = newEid
        ins.close()

    def updateMod(self, modInfo,changeBase=False):
        """Updates specified mod file."""
        types = self.types
        classes = [MreRecord.type_class[type] for type in types]
        loadFactory= LoadFactory(True,*classes)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        #--Create  filtered versions of mappers.
        mapper = modFile.getShortMapper()
        masters = modFile.tes4.masters+[modFile.fileInfo.name]
        short = dict((oldId,mapper(oldId)) for oldId in self.old_eid if oldId[0] in masters)
        short.update((newId,mapper(newId)) for newId in self.new_eid if newId[0] in masters)
        old_eid = dict((short[oldId],eid) for oldId,eid in self.old_eid.iteritems() if oldId in short)
        new_eid = dict((short[newId],eid) for newId,eid in self.new_eid.iteritems() if newId in short)
        old_new = dict((short[oldId],short[newId]) for oldId,newId in self.old_new.iteritems()
            if (oldId in short and newId in short))
        if not old_new: return False
        #--Swapper function
        old_count = {}
        def swapper(oldId):
            newId = old_new.get(oldId,None)
            if newId:
                old_count.setdefault(oldId,0)
                old_count[oldId] += 1
                return newId
            else:
                return oldId
        #--Do swap on all records
        for type in types:
            for record in getattr(modFile,type).getActiveRecords():
                if changeBase: record.fid = swapper(record.fid)
                record.mapFids(swapper,True)
                record.setChanged()
        #--Done
        if not old_count: return False
        modFile.safeSave()
        entries = [(count,old_eid[oldId],new_eid[old_new[oldId]]) for oldId,count in
                old_count.iteritems()]
        entries.sort(key=itemgetter(1))
        return '\n'.join(['%3d %s >> %s' % entry for entry in entries])

#------------------------------------------------------------------------------
class FullNames:
    """Names for records, with functions for importing/exporting from/to mod/text file."""
    defaultTypes = set((
        'ALCH', 'AMMO', 'APPA', 'ARMO', 'BOOK', 'BSGN', 'CLAS', 'CLOT', 'CONT', 'CREA', 'DOOR',
        'EYES', 'FACT', 'FLOR', 'HAIR','INGR', 'KEYM', 'LIGH', 'MISC', 'NPC_', 'RACE', 'SGST',
        'SLGM', 'SPEL','WEAP',))

    def __init__(self,types=None,aliases=None):
        """Initialize."""
        self.type_id_name = {} #--(eid,name) = type_id_name[type][longid]
        self.types = types or FullNames.defaultTypes
        self.aliases = aliases or {}

    def readFromMod(self,modInfo):
        """Imports type_id_name from specified mod."""
        type_id_name,types = self.type_id_name, self.types
        classes = [MreRecord.type_class[x] for x in self.types]
        loadFactory= LoadFactory(False,*classes)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        for type in types:
            typeBlock = modFile.tops.get(type,None)
            if not typeBlock: continue
            if type not in type_id_name: type_id_name[type] = {}
            id_name = type_id_name[type]
            for record in typeBlock.getActiveRecords():
                longid = mapper(record.fid)
                full = record.full or (type != 'LIGH' and 'NO NAME')
                if record.eid and full:
                    id_name[longid] = (record.eid,full)

    def writeToMod(self,modInfo):
        """Exports type_id_name to specified mod."""
        type_id_name,types = self.type_id_name,self.types
        classes = [MreRecord.type_class[x] for x in self.types]
        loadFactory= LoadFactory(True,*classes)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        changed = {}
        for type in types:
            id_name = type_id_name.get(type,None)
            typeBlock = modFile.tops.get(type,None)
            if not id_name or not typeBlock: continue
            for record in typeBlock.records:
                longid = mapper(record.fid)
                full = record.full
                eid,newFull = id_name.get(longid,(0,0))
                if newFull and newFull not in (full,'NO NAME'):
                    record.full = newFull
                    record.setChanged()
                    changed[eid] = (full,newFull)
        if changed: modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Imports type_id_name from specified text file."""
        textPath = GPath(textPath)
        type_id_name = self.type_id_name
        aliases = self.aliases
        ins = bolt.CsvReader(textPath)
        for fields in ins:
            if len(fields) < 5 or fields[2][:2] != '0x': continue
            type,mod,objectIndex,eid,full = fields[:5]
            mod = GPath(mod)
            longid = (aliases.get(mod,mod),int(objectIndex[2:],16))
            if type in type_id_name:
                type_id_name[type][longid] = (eid,full)
            else:
                type_id_name[type] = {longid:(eid,full)}
        ins.close()

    def writeToText(self,textPath):
        """Exports type_id_name to specified text file."""
        textPath = GPath(textPath)
        type_id_name = self.type_id_name
        headFormat = '"%s","%s","%s","%s","%s"\n'
        rowFormat = '"%s","%s","0x%06X","%s","%s"\n'
        out = textPath.open('w')
        out.write(headFormat % (_('Type'),_('Mod Name'),_('ObjectIndex'),_('Editor Id'),_('Name')))
        for type in sorted(type_id_name):
            id_name = type_id_name[type]
            longids = id_name.keys()
            longids.sort(key=lambda a: id_name[a][0])
            longids.sort(key=itemgetter(0))
            for longid in longids:
                eid,name = id_name[longid]
                out.write(rowFormat % (type,longid[0].s,longid[1],eid,name))
        out.close()
#------------------------------------------------------------------------------
class SigilStoneDetails:
    """Details on SigilStones, with functions for importing/exporting from/to mod/text file."""
#just ignore me... or fix me to also export the effect data as Pacific Morrowind is attempting (with little luck).
    def __init__(self,types=None,aliases=None):
        """Initialize."""
        #--type_stats[type] = ...
        #--SFST: (eid, weight, value)
        self.type_stats = {'SGST':{},}
        self.type_attrs = {
            'SGST':('eid', 'full', 'model', 'iconPath', 'script', 'uses', 'value', 'weight', 'effects'),
            }
        self.aliases = aliases or {} #--For aliasing mod names

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        loadFactory= LoadFactory(False,MreSgst)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        for type in self.type_stats:
            stats, attrs = self.type_stats[type], self.type_attrs[type]
            for record in getattr(modFile,type).getActiveRecords():
                longid = mapper(record.fid)
                recordGetAttr = record.__getattribute__
                stats[longid] = tuple(recordGetAttr(attr) for attr in attrs)

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        loadFactory= LoadFactory(False,MreSgst)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        changed = {} #--changed[modName] = numChanged
        for type in self.type_stats:
            stats, attrs = self.type_stats[type], self.type_attrs[type]
            for record in getattr(modFile,type).getActiveRecords():
                longid = mapper(record.fid)
                itemStats = stats.get(longid,None)
                if not itemStats: continue
                map(record.__setattr__,attrs,itemStats)
                record.setChanged()
                changed[longid[0]] = 1 + changed.get(longid[0],0)
        if changed: modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Reads stats from specified text file."""
        Spells = [self.type_stats[type] for type in ('SGST',)]
        aliases = self.aliases
        ins = bolt.CsvReader(textPath)
        pack,unpack = struct.pack,struct.unpack
        sfloat = lambda a: unpack('f',pack('f',float(a)))[0] #--Force standard precision
        for fields in ins:
            if len(fields) < 3 or fields[2][:2] != '0x': continue
            type,modName,objectStr,eid = fields[0:4]
            modName = GPath(modName)
            longid = (GPath(aliases.get(modName,modName)),int(objectStr[2:],16))
            if type == 'SGST':
                Spells[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(name, model, icon, script, uses, value, weight, effects)
                    zip((sfloat,sfloat,sfloat,sfloat,sfloat,int,float,int,sfloat,),fields[4:12]))
        ins.close()

    def writeToText(self,textPath):
        """Writes stats to specified text file."""
        out = textPath.open('w')
        def getSortedIds(stats):
            longids = stats.keys()
            longids.sort(key=lambda a: stats[a][0])
            longids.sort(key=itemgetter(0))
            return longids
        for type,format,header in (
            #--Sigil Stones
            ('SGST', bolt.csvFormat('sssssifis')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Name'),_('Model'),_('Icon'),_('Script'),_('Uses'),_('Value'),_('Weight'),_('Effects')
                )) + '"\n')),
            ):
            stats = self.type_stats[type]
            if not stats: continue
            out.write(header)
            for longid in getSortedIds(stats):
                out.write('"%s","%s","0x%06X",' % (type,longid[0].s,longid[1]))
                out.write(format % stats[longid])
        out.close()

#------------------------------------------------------------------------------
class ItemStats:
    """Statistics for armor and weapons, with functions for importing/exporting from/to mod/text file."""

    def __init__(self,types=None,aliases=None):
        """Initialize."""
        #--type_stats[type] = ...
        #--AMMO: (eid, weight, value, damage, speed, epoints)
        #--ARMO: (eid, weight, value, health, strength)
        #--WEAP: (eid, weight, value, health, damage, speed, reach, epoints)
        self.type_stats = {'ALCH':{},'AMMO':{},'APPA':{},'ARMO':{},'BOOK':{},'CLOT':{},'INGR':{},'KEYM':{},'LIGH':{},'MISC':{},'SGST':{},'SLGM':{},'WEAP':{}}
        self.type_attrs = {
            'ALCH':('eid', 'weight', 'value'),
            'AMMO':('eid', 'weight', 'value', 'damage', 'speed', 'enchantPoints'),
            'APPA':('eid', 'weight', 'value', 'quality'),
            'ARMO':('eid', 'weight', 'value', 'health', 'strength'),
            'BOOK':('eid', 'weight', 'value', 'enchantPoints'),
            'CLOT':('eid', 'weight', 'value', 'enchantPoints'),
            'INGR':('eid', 'weight', 'value'),
            'KEYM':('eid', 'weight', 'value'),
            'LIGH':('eid', 'weight', 'value', 'duration'),
            'MISC':('eid', 'weight', 'value'),
            'SGST':('eid', 'weight', 'value', 'uses'),
            'SLGM':('eid', 'weight', 'value'),
            'WEAP':('eid', 'weight', 'value', 'health', 'damage', 'speed', 'reach', 'enchantPoints'),
            }
        self.aliases = aliases or {} #--For aliasing mod names

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        loadFactory= LoadFactory(False,MreAlch,MreAmmo,MreAppa,MreArmo,MreBook,MreClot,MreIngr,MreKeym,MreLigh,MreMisc,MreSgst,MreSlgm,MreWeap)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        for type in self.type_stats:
            stats, attrs = self.type_stats[type], self.type_attrs[type]
            for record in getattr(modFile,type).getActiveRecords():
                longid = mapper(record.fid)
                recordGetAttr = record.__getattribute__
                stats[longid] = tuple(recordGetAttr(attr) for attr in attrs)

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        loadFactory= LoadFactory(True,MreAlch,MreAmmo,MreAppa,MreArmo,MreBook,MreClot,MreIngr,MreKeym,MreLigh,MreMisc,MreSgst,MreSlgm,MreWeap)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        changed = {} #--changed[modName] = numChanged
        for type in self.type_stats:
            stats, attrs = self.type_stats[type], self.type_attrs[type]
            for record in getattr(modFile,type).getActiveRecords():
                longid = mapper(record.fid)
                itemStats = stats.get(longid,None)
                if not itemStats: continue
                map(record.__setattr__,attrs,itemStats)
                record.setChanged()
                changed[longid[0]] = 1 + changed.get(longid[0],0)
        if changed: modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Reads stats from specified text file."""
        alch, ammo, appa, armor, books, clothing, ingredients, keys, lights, misc, sigilstones, soulgems, weapons = [self.type_stats[type] for type in ('ALCH','AMMO','APPA','ARMO','BOOK','CLOT','INGR','KEYM','LIGH','MISC','SGST','SLGM','WEAP')]
        aliases = self.aliases
        ins = bolt.CsvReader(textPath)
        pack,unpack = struct.pack,struct.unpack
        sfloat = lambda a: unpack('f',pack('f',float(a)))[0] #--Force standard precision
        for fields in ins:
            if len(fields) < 3 or fields[2][:2] != '0x': continue
            type,modName,objectStr,eid = fields[0:4]
            modName = GPath(modName)
            longid = (GPath(aliases.get(modName,modName)),int(objectStr[2:],16))
            if type == 'ALCH':
                alch[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value)
                    zip((sfloat,int),fields[4:6]))
            elif type == 'AMMO':
                ammo[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value, damage, speed, enchantPoints)
                    zip((sfloat,int,int,sfloat,int),fields[4:9]))
            elif type == 'ARMO':
                armor[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value, health, strength)
                    zip((sfloat,int,int,int),fields[4:8]))
            elif type == 'BOOK':
               books[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value, echantPoints)
                    zip((sfloat,int,int,),fields[4:7]))
            elif type == 'CLOT':
                armor[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value, echantPoints)
                    zip((sfloat,int,int,),fields[4:7]))
            elif type == 'INGR':
                armor[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value)
                    zip((sfloat,int),fields[4:6]))
            elif type == 'KEYM':
                keys[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value)
                    zip((sfloat,int),fields[4:6]))
            elif type == 'LIGH':
               books[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value, duration)
                    zip((sfloat,int,int,),fields[4:7]))
            elif type == 'MISC':
                keys[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value)
                    zip((sfloat,int),fields[4:6]))
            elif type == 'SGST':
               books[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value, uses)
                    zip((sfloat,int,int,),fields[4:7]))
            elif type == 'SLGM':
                keys[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value)
                    zip((sfloat,int),fields[4:6]))
            elif type == 'WEAP':
                weapons[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value, health, damage, speed, reach, epoints)
                    zip((sfloat,int,int,int,sfloat,sfloat,int),fields[4:11]))
        ins.close()

    def writeToText(self,textPath):
        """Writes stats to specified text file."""
        out = textPath.open('w')
        def getSortedIds(stats):
            longids = stats.keys()
            longids.sort(key=lambda a: stats[a][0])
            longids.sort(key=itemgetter(0))
            return longids
        for type,format,header in (
            #--Alch
            ('ALCH', bolt.csvFormat('sfi')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Weight'),_('Value'))) + '"\n')),
            #Ammo
            ('AMMO', bolt.csvFormat('sfiifi')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Weight'),_('Value'),_('Damage'),_('Speed'),_('EPoints'))) + '"\n')),
            #--Armor
            ('ARMO', bolt.csvFormat('sfiii')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Weight'),_('Value'),_('Health'),_('AR'))) + '"\n')),
            #Books
            ('BOOK', bolt.csvFormat('sfii')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Weight'),_('Value'),_('EPoints'))) + '"\n')),
            #Clothing
            ('CLOT', bolt.csvFormat('sfii')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Weight'),_('Value'),_('EPoints'))) + '"\n')),
            #Ingredients
            ('INGR', bolt.csvFormat('sfi')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Weight'),_('Value'))) + '"\n')),
            #--Keys
            ('KEYM', bolt.csvFormat('sfi')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Weight'),_('Value'))) + '"\n')),
            #Lights
            ('LIGH', bolt.csvFormat('sfii')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Weight'),_('Value'),_('Duration'))) + '"\n')),
            #--Misc
            ('MISC', bolt.csvFormat('sfi')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Weight'),_('Value'))) + '"\n')),
            #Sigilstones
            ('SGST', bolt.csvFormat('sfii')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Weight'),_('Value'),_('Uses'))) + '"\n')),
            #Soulgems
            ('SLGM', bolt.csvFormat('sfi')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Weight'),_('Value'))) + '"\n')),
            #--Weapons
            ('WEAP', bolt.csvFormat('sfiiiffi')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Weight'),_('Value'),_('Health'),_('Damage'),
                _('Speed'),_('Reach'),_('EPoints'))) + '"\n')),
            ):
            stats = self.type_stats[type]
            if not stats: continue
            out.write(header)
            for longid in getSortedIds(stats):
                out.write('"%s","%s","0x%06X",' % (type,longid[0].s,longid[1]))
                out.write(format % stats[longid])
        out.close()

#------------------------------------------------------------------------------
class ItemPrices:
    """Statistics for armor and weapons, with functions for importing/exporting from/to mod/text file."""

    def __init__(self,types=None,aliases=None):
        """Initialize."""
        #--type_stats[type] = ...
        #--AMMO: (eid, weight, value, damage, speed, epoints)
        #--ARMO: (eid, weight, value, health, strength)
        #--WEAP: (eid, weight, value, health, damage, speed, reach, epoints)
        self.type_stats = {'ALCH':{},'AMMO':{},'APPA':{},'ARMO':{},'BOOK':{},'CLOT':{},'INGR':{},'KEYM':{},'LIGH':{},'MISC':{},'SGST':{},'SLGM':{},'WEAP':{}}
        self.type_attrs = {
            'ALCH':('value', 'eid', 'full'),
            'AMMO':('value', 'eid', 'full'),
            'APPA':('value', 'eid', 'full'),
            'ARMO':('value', 'eid', 'full'),
            'BOOK':('value', 'eid', 'full'),
            'CLOT':('value', 'eid', 'full'),
            'INGR':('value', 'eid', 'full'),
            'KEYM':('value', 'eid', 'full'),
            'LIGH':('value', 'eid', 'full'),
            'MISC':('value', 'eid', 'full'),
            'SGST':('value', 'eid', 'full'),
            'SLGM':('value', 'eid', 'full'),
            'WEAP':('value', 'eid', 'full'),
            }
        self.aliases = aliases or {} #--For aliasing mod names

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        loadFactory= LoadFactory(False,MreAlch,MreAmmo,MreAppa,MreArmo,MreBook,MreClot,MreIngr,MreKeym,MreLigh,MreMisc,MreSgst,MreSlgm,MreWeap)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        for type in self.type_stats:
            stats, attrs = self.type_stats[type], self.type_attrs[type]
            for record in getattr(modFile,type).getActiveRecords():
                longid = mapper(record.fid)
                recordGetAttr = record.__getattribute__
                stats[longid] = tuple(recordGetAttr(attr) for attr in attrs)

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        loadFactory= LoadFactory(True,MreAlch,MreAmmo,MreAppa,MreArmo,MreBook,MreClot,MreIngr,MreKeym,MreLigh,MreMisc,MreSgst,MreSlgm,MreWeap)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        changed = {} #--changed[modName] = numChanged
        for type in self.type_stats:
            stats, attrs = self.type_stats[type], self.type_attrs[type]
            for record in getattr(modFile,type).getActiveRecords():
                longid = mapper(record.fid)
                itemStats = stats.get(longid,None)
                if not itemStats: continue
                map(record.__setattr__,attrs,itemStats)
                record.setChanged()
                changed[longid[0]] = 1 + changed.get(longid[0],0)
        if changed: modFile.safeSave()
        return changed


    def writeToText(self,textPath):
        """Writes stats to specified text file."""
        out = textPath.open('w')
        def getSortedIds(stats):
            longids = stats.keys()
            longids.sort(key=lambda a: stats[a][0])
            longids.sort(key=itemgetter(0))
            return longids
        for type,format,header in (
            #--Alch
            ('ALCH', bolt.csvFormat('iss')+'\n',
                ('"' + '","'.join((_('Mod Name'),_('ObjectIndex'),
                _('Value'),_('Editor Id'),_('Name'))) + '"\n')),
            #Ammo
            ('AMMO', bolt.csvFormat('iss')+'\n',
                ('"' + '","'.join((_('Mod Name'),_('ObjectIndex'),
                _('Value'),_('Editor Id'),_('Name'))) + '"\n')),
            #--Armor
            ('ARMO', bolt.csvFormat('iss')+'\n',
                ('"' + '","'.join((_('Mod Name'),_('ObjectIndex'),
                _('Value'),_('Editor Id'),_('Name'))) + '"\n')),
            #Books
            ('BOOK', bolt.csvFormat('iss')+'\n',
                ('"' + '","'.join((_('Mod Name'),_('ObjectIndex'),
                _('Value'),_('Editor Id'),_('Name'))) + '"\n')),
            #Clothing
            ('CLOT', bolt.csvFormat('iss')+'\n',
                ('"' + '","'.join((_('Mod Name'),_('ObjectIndex'),
                _('Value'),_('Editor Id'),_('Name'))) + '"\n')),
            #Ingredients
            ('INGR', bolt.csvFormat('iss')+'\n',
                ('"' + '","'.join((_('Mod Name'),_('ObjectIndex'),
                _('Value'),_('Editor Id'),_('Name'))) + '"\n')),
            #--Keys
            ('KEYM', bolt.csvFormat('iss')+'\n',
                ('"' + '","'.join((_('Mod Name'),_('ObjectIndex'),
                _('Value'),_('Editor Id'),_('Name'))) + '"\n')),
            #Lights
            ('LIGH', bolt.csvFormat('iss')+'\n',
                ('"' + '","'.join((_('Mod Name'),_('ObjectIndex'),
                _('Value'),_('Editor Id'),_('Name'))) + '"\n')),
            #--Misc
            ('MISC', bolt.csvFormat('iss')+'\n',
                ('"' + '","'.join((_('Mod Name'),_('ObjectIndex'),
                _('Value'),_('Editor Id'),_('Name'))) + '"\n')),
            #Sigilstones
            ('SGST', bolt.csvFormat('iss')+'\n',
                ('"' + '","'.join((_('Mod Name'),_('ObjectIndex'),
                _('Value'),_('Editor Id'),_('Name'))) + '"\n')),
            #Soulgems
            ('SLGM', bolt.csvFormat('iss')+'\n',
                ('"' + '","'.join((_('Mod Name'),_('ObjectIndex'),
                _('Value'),_('Editor Id'),_('Name'))) + '"\n')),
            #--Weapons
            ('WEAP', bolt.csvFormat('iss')+'\n',
                ('"' + '","'.join((_('Mod Name'),_('ObjectIndex'),
                _('Value'),_('Editor Id'),_('Name'))) + '"\n')),
            ):
            stats = self.type_stats[type]
            if not stats: continue
            out.write(header)
            for longid in getSortedIds(stats):
                out.write('"%s","0x%06X",' % (longid[0].s,longid[1]))
                out.write(format % stats[longid])
        out.close()

#------------------------------------------------------------------------------
class CompleteItemData:
    """Statistics for armor and weapons, with functions for importing/exporting from/to mod/text file."""

    def __init__(self,types=None,aliases=None):
        """Initialize."""
        self.type_stats = {'ALCH':{},'AMMO':{},'APPA':{},'ARMO':{},'BOOK':{},'CLOT':{},'INGR':{},'KEYM':{},'LIGH':{},'MISC':{},'SGST':{},'SLGM':{},'WEAP':{}}
        self.type_attrs = {
            'ALCH':('eid', 'full', 'weight', 'value', 'iconPath'),
            'AMMO':('eid', 'full', 'weight', 'value', 'damage', 'speed', 'enchantPoints', 'iconPath'),
            'APPA':('eid', 'full', 'weight', 'value', 'quality', 'iconPath'),
            'ARMO':('eid', 'full', 'weight', 'value', 'health', 'strength', 'maleIconPath', 'femaleIconPath'),
            'BOOK':('eid', 'full', 'weight', 'value', 'enchantPoints', 'iconPath'),
            'CLOT':('eid', 'full', 'weight', 'value', 'enchantPoints', 'maleIconPath', 'femaleIconPath'),
            'INGR':('eid', 'full', 'weight', 'value', 'iconPath'),
            'KEYM':('eid', 'full', 'weight', 'value', 'iconPath'),
            'LIGH':('eid', 'full', 'weight', 'value', 'duration', 'iconPath'),
            'MISC':('eid', 'full', 'weight', 'value', 'iconPath'),
            'SGST':('eid', 'full', 'weight', 'value', 'uses', 'iconPath'),
            'SLGM':('eid', 'full', 'weight', 'value', 'iconPath'),
            'WEAP':('eid', 'full', 'weight', 'value', 'health', 'damage', 'speed', 'reach', 'enchantPoints', 'iconPath'),
            }
        self.aliases = aliases or {} #--For aliasing mod fulls
        self.model = {}
        self.Mmodel = {}
        self.Fmodel = {}
        self.MGndmodel = {}
        self.FGndmodel = {}

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        loadFactory= LoadFactory(False,MreAlch,MreAmmo,MreAppa,MreArmo,MreBook,MreClot,MreIngr,MreKeym,MreLigh,MreMisc,MreSgst,MreSlgm,MreWeap)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        for type in self.type_stats:
            stats, attrs = self.type_stats[type], self.type_attrs[type]
            for record in getattr(modFile,type).getActiveRecords():
                longid = mapper(record.fid)
                recordGetAttr = record.__getattribute__
                stats[longid] = tuple(recordGetAttr(attr) for attr in attrs)
                if type == 'ALCH' or type == 'AMMO' or type == 'APPA' or type == 'BOOK' or type == 'INGR' or type == 'KEYM' or type == 'LIGH' or type == 'MISC' or type == 'SGST' or type == 'SLGM' or type == 'WEAP':
                    if record.model:
                        self.model[longid] = record.model.modPath
                elif type == 'CLOT' or type == 'ARMO':
                    if record.maleBody:
                        self.Mmodel[longid] = record.maleBody.modPath
                    else:
                        self.Mmodel[longid] = 'NONE'
                    if record.maleWorld:
                        self.MGndmodel[longid] = record.maleWorld.modPath
                    else:
                        self.MGndmodel[longid] = 'NONE'
                    if record.femaleBody:
                        self.Fmodel[longid] = record.femaleBody.modPath
                    else:
                        self.Fmodel[longid] = 'NONE'
                    if record.femaleWorld:
                        self.FGndmodel[longid] = record.femaleWorld.modPath  
                    else:
                        self.FGndmodel[longid] = 'NONE'
                        
    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        loadFactory= LoadFactory(True,MreAlch,MreAmmo,MreAppa,MreArmo,MreBook,MreClot,MreIngr,MreKeym,MreLigh,MreMisc,MreSgst,MreSlgm,MreWeap)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        changed = {} #--changed[modName] = numChanged
        for type in self.type_stats:
            stats, attrs = self.type_stats[type], self.type_attrs[type]
            for record in getattr(modFile,type).getActiveRecords():
                longid = mapper(record.fid)
                itemStats = stats.get(longid,None)
                if not itemStats: continue
                map(record.__setattr__,attrs,itemStats)
                record.setChanged()
                changed[longid[0]] = 1 + changed.get(longid[0],0)
        if changed: modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Reads stats from specified text file."""
        alch, ammo, appa, armor, books, clothing, ingredients, keys, lights, misc, sigilstones, soulgems, weapons = [self.type_stats[type] for type in ('ALCH','AMMO','APPA','ARMO','BOOK','CLOT','INGR','KEYM','LIGH','MISC','SGST','SLGM','WEAP')]
        aliases = self.aliases
        ins = bolt.CsvReader(textPath)
        pack,unpack = struct.pack,struct.unpack
        sfloat = lambda a: unpack('f',pack('f',float(a)))[0] #--Force standard precision
        for fields in ins:
            if len(fields) < 3 or fields[2][:2] != '0x': continue
            type,modName,objectStr,eid = fields[0:4]
            modName = GPath(modName)
            longid = (GPath(aliases.get(modName,modName)),int(objectStr[2:],16))
            if type == 'ALCH':
                alch[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value)
                    zip((str,sfloat,int,str),fields[4:8]))
            elif type == 'AMMO':
                ammo[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value, damage, speed, enchantPoints)
                    zip((str,sfloat,int,int,sfloat,int,str),fields[4:11]))
            elif type == 'ARMO':
                armor[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value, health, strength)
                    zip((str,sfloat,int,int,int,str,str),fields[4:10]))
            elif type == 'BOOK':
               books[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value, echantPoints)
                    zip((str,sfloat,int,int,str),fields[4:9]))
            elif type == 'CLOT':
                armor[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value, echantPoints)
                    zip((str,sfloat,int,int,str,str),fields[4:10]))
            elif type == 'INGR':
                armor[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value)
                    zip((str,sfloat,int,str),fields[4:8]))
            elif type == 'KEYM':
                keys[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value)
                    zip((str,sfloat,int,str),fields[4:8]))
            elif type == 'LIGH':
               books[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value, duration)
                    zip((str,sfloat,int,int,str),fields[4:9]))
            elif type == 'MISC':
                keys[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value)
                    zip((str,sfloat,int,str),fields[4:8]))
            elif type == 'SGST':
               books[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value, uses)
                    zip((str,sfloat,int,int,str),fields[4:9]))
            elif type == 'SLGM':
                keys[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value)
                    zip((str,sfloat,int),fields[4:8]))
            elif type == 'WEAP':
                weapons[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(weight, value, health, damage, speed, reach, epoints)
                    zip((str,sfloat,int,int,int,sfloat,sfloat,int,str),fields[4:13]))
        ins.close()

    def writeToText(self,textPath):
        """Writes stats to specified text file."""
        out = textPath.open('w')
        def getSortedIds(stats):
            longids = stats.keys()
            longids.sort(key=lambda a: stats[a][0])
            longids.sort(key=itemgetter(0))
            return longids
        for type,format,header in (
            #--Alch
            ('ALCH', bolt.csvFormat('ssfiss')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Name'),_('Weight'),_('Value'),_('Icon Path'),_('Model'))) + '"\n')),
            #Ammo
            ('AMMO', bolt.csvFormat('ssfiifiss')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Name'),_('Weight'),_('Value'),_('Damage'),_('Speed'),_('EPoints'),_('Icon Path'),_('Model'))) + '"\n')),
            #--Armor
            ('ARMO', bolt.csvFormat('ssfiiissssss')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Name'),_('Weight'),_('Value'),_('Health'),
                _('AR'),_('Male Icon Path'),_('Female Icon Path'),_('Male Model Path'),
                _('Female Model Path'),_('Male World Model Path'),_('Female World Model Path'))) + '"\n')),
            #Books
            ('BOOK', bolt.csvFormat('ssfiiss')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Name'),_('Weight'),_('Value'),_('EPoints'),_('Icon Path'),_('Model'))) + '"\n')),
            #Clothing
            ('CLOT', bolt.csvFormat('ssfiissssss')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Name'),_('Weight'),_('Value'),_('EPoints'),
                _('Male Icon Path'),_('Female Icon Path'),_('Male Model Path'),
                _('Female Model Path'),_('Male World Model Path'),_('Female World Model Path'))) + '"\n')),
            #Ingredients
            ('INGR', bolt.csvFormat('ssfiss')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Name'),_('Weight'),_('Value'),_('Icon Path'),_('Model'))) + '"\n')),
            #--Keys
            ('KEYM', bolt.csvFormat('ssfiss')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Name'),_('Weight'),_('Value'),_('Icon Path'),_('Model'))) + '"\n')),
            #Lights
            ('LIGH', bolt.csvFormat('ssfiiss')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Name'),_('Weight'),_('Value'),_('Duration'),_('Icon Path'),_('Model'))) + '"\n')),
            #--Misc
            ('MISC', bolt.csvFormat('ssfiss')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Name'),_('Weight'),_('Value'),_('Icon Path'),_('Model'))) + '"\n')),
            #Sigilstones
            ('SGST', bolt.csvFormat('ssfiiss')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Name'),_('Weight'),_('Value'),_('Uses'),_('Icon Path'),_('Model'))) + '"\n')),
            #Soulgems
            ('SLGM', bolt.csvFormat('ssfiss')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Name'),_('Weight'),_('Value'),_('Icon Path'),_('Model'))) + '"\n')),
            #--Weapons
            ('WEAP', bolt.csvFormat('ssfiiiffiss')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Name'),_('Weight'),_('Value'),_('Health'),_('Damage'),
                _('Speed'),_('Reach'),_('EPoints'),_('Icon Path'),_('Model'))) + '"\n')),
            ):
            stats = self.type_stats[type]
            if not stats: continue
            out.write('\n'+header)
            for longid in getSortedIds(stats):
                out.write('"%s","%s","0x%06X",' % (type,longid[0].s,longid[1]))
                tempstats = list(stats[longid])
                if type == 'ARMO' or type == 'CLOT':
                    tempstats.append(self.Mmodel[longid])
                    tempstats.append(self.Fmodel[longid])
                    tempstats.append(self.MGndmodel[longid])
                    tempstats.append(self.FGndmodel[longid])
                else:
                    tempstats.append(self.model[longid])
                finalstats = tuple(tempstats)
                out.write(format % finalstats)
        out.close()

#------------------------------------------------------------------------------
class ScriptText:
    """Details on SigilStones, with functions for importing/exporting from/to mod/text file."""
    def __init__(self,types=None,aliases=None):
        """Initialize."""
        self.type_stats = {'SCPT':{},}
        self.type_attrs = {
            'SCPT':('eid', 'scriptText'),
            }
        self.aliases = aliases or {} #--For aliasing mod names

    def readFromMod(self,modInfo,file):
        """Reads stats from specified mod."""
        loadFactory= LoadFactory(False,MreScpt)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        progress = balt.Progress(_("Export Scripts"))
        for type in self.type_stats:
            y = len(getattr(modFile,type).getActiveRecords())
            z = 0
            ScriptTexts, attrs = self.type_stats[type], self.type_attrs[type]
            for record in getattr(modFile,type).getActiveRecords():
                z +=1
                progress((0.5/y*z),_("reading scripts in %s.")%(file))
                longid = mapper(record.fid)
                recordGetAttr = record.__getattribute__
                ScriptTexts[longid] = tuple(recordGetAttr(attr) for attr in attrs)
                #return stats
        progress = progress.Destroy()
                
    def writeToMod(self,modInfo,eid,newScriptText):
        """Writes scripts to specified mod."""
        loadFactory = LoadFactory(True,MreScpt)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        for type in self.type_stats:
            scriptData, attrs = self.type_stats[type], self.type_attrs[type]
            for record in getattr(modFile,type).getActiveRecords():
                if record.eid == eid:
                    if str(record.scriptText) != str(newScriptText):
                        record.scriptText = newScriptText
                        record.setChanged()
                        modFile.safeSave()
                        return True
                    else:
                        return False
            print "eid %s doesn't match any record." %(eid)
            return False

    def readFromText(self,textPath,modInfo):
        """Reads scripts from files in specified mods' directory in bashed patches folder."""
        aliases = self.aliases
        changedScripts = ''
        num = 0
        progress = balt.Progress(_("Import Scripts"))
        for root, dirs, files in os.walk(textPath):
            y = len(files)
            z = 0
            for name in files:
                z += 1
                progress(((1/y)*z),_("reading file %s.") % (name))
                text = open(os.path.join(root, name),"r")
                lines = text.readlines()
                modName,FormID,eid = lines[0][:-1],lines[1][:-1],lines[2][:-1]
                scriptText = ''
                for line in lines[3:]:
                    scriptText = (scriptText+line)
                text.close()
                changed = self.writeToMod(modInfo,eid,scriptText)
                if changed:
                    num += 1
                    changedScripts += eid+'\r\n'
        progress = progress.Destroy()
        if num == 0:
            return False
        changedScripts = 'Imported %d changed scripts from %s:\n'%(num,textPath)+changedScripts     
        return changedScripts

    def writeToText(self,textPath,skip,folder,deprefix):
        """Writes stats to specified text file."""
        progress = balt.Progress(_("Export Scripts"))
        def getSortedIds(ScriptTexts):
            longids = ScriptTexts.keys()
            longids.sort(key=lambda a: ScriptTexts[a][0])
            longids.sort(key=itemgetter(0))
            return longids
        scriptTexts = self.type_stats['SCPT']
        x = len(skip)
        exportedScripts = ''
        y = len(getSortedIds(scriptTexts))
        z = 0
        num = 0
        r = len(deprefix)    
        for longid in getSortedIds(scriptTexts):
            z += 1
            progress((0.5+0.5/y*z),_("exporting script %s.") % (scriptTexts[longid][0]))
            if x == 0 or skip.lower() != scriptTexts[longid][0][:x].lower():
                name = scriptTexts[longid][0]
                if r >= 1 and deprefix == name[:r]:
                    name = name[r:]
                num += 1
                outpath = dirs['patches'].join(folder+' Exported Scripts').join(name+inisettings['scriptFileExt'])
                out = outpath.open('wb')
                formid = '0x%06X' %(longid[1])
                out.write(longid[0].s+'\r\n'+formid+'\r\n'+scriptTexts[longid][0]+'\r\n'+scriptTexts[longid][1])
                out.close
                exportedScripts += scriptTexts[longid][0]+'\r\n'
        exportedScripts = 'Exported %d scripts from %s:\n'%(num,folder)+exportedScripts
        progress = progress.Destroy()
        return exportedScripts

#------------------------------------------------------------------------------
class SpellRecords:
    """Statistics for spells, with functions for importing/exporting from/to mod/text file."""

    def __init__(self,types=None,aliases=None):
        """Initialize."""
        #--type_stats[type] = ...
        #--SPEL: (eid, weight, value)
        self.type_stats = {'SPEL':{},}
        self.type_attrs = {
            'SPEL':('eid', 'full', 'cost', 'level', 'spellType'),
            }
        self.aliases = aliases or {} #--For aliasing mod names

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        loadFactory= LoadFactory(False,MreSpel)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        for type in self.type_stats:
            stats, attrs = self.type_stats[type], self.type_attrs[type]
            for record in getattr(modFile,type).getActiveRecords():
                longid = mapper(record.fid)
                recordGetAttr = record.__getattribute__
                stats[longid] = tuple(recordGetAttr(attr) for attr in attrs)

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        loadFactory= LoadFactory(False,MreSpel)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        changed = {} #--changed[modName] = numChanged
        for type in self.type_stats:
            stats, attrs = self.type_stats[type], self.type_attrs[type]
            for record in getattr(modFile,type).getActiveRecords():
                longid = mapper(record.fid)
                itemStats = stats.get(longid,None)
                if not itemStats: continue
                map(record.__setattr__,attrs,itemStats)
                record.setChanged()
                changed[longid[0]] = 1 + changed.get(longid[0],0)
        if changed: modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Reads stats from specified text file."""
        Spells = [self.type_stats[type] for type in ('SPEL',)]
        aliases = self.aliases
        ins = bolt.CsvReader(textPath)
        pack,unpack = struct.pack,struct.unpack
        sfloat = lambda a: unpack('f',pack('f',float(a)))[0] #--Force standard precision
        for fields in ins:
            if len(fields) < 3 or fields[2][:2] != '0x': continue
            type,modName,objectStr,eid = fields[0:4]
            modName = GPath(modName)
            longid = (GPath(aliases.get(modName,modName)),int(objectStr[2:],16))
            if type == 'SPEL':
                Spells[longid] = (eid,) + tuple(func(field) for func,field in
                    #--(name, cost, level, spelltype)
                    zip((sfloat,sfloat,int,int,sfloat,),fields[4:9]))
        ins.close()

    def writeToText(self,textPath):
        """Writes stats to specified text file."""
        out = textPath.open('w')
        def getSortedIds(stats):
            longids = stats.keys()
            longids.sort(key=lambda a: stats[a][0])
            longids.sort(key=itemgetter(0))
            return longids
        for type,format,header in (
            #--Spells
            ('SPEL', bolt.csvFormat('ssiis')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Name'),_('Cost'),_('Level'),_('Spell Type')
                )) + '"\n')),
            ):
            stats = self.type_stats[type]
            if not stats: continue
            out.write(header)
            for longid in getSortedIds(stats):
                out.write('"%s","%s","0x%06X",' % (type,longid[0].s,longid[1]))
                out.write(format % stats[longid])
        out.close()

#------------------------------------------------------------------------------
class ExportAlchInfo:
    """Updates COBL alchemical catalogs."""
    #name = _('Cobl Catalogs')
    #text = _("Update COBL's catalogs of alchemical ingredients and effects.\n\nWill only run if Cobl Main.esm is loaded.")

    #--Config Phase -----------------------------------------------------------
    #--Patch Phase ------------------------------------------------------------
    def __init__(self,types=None,aliases=None):
        """Initialize"""
        #Patcher.initPatchFile(self,patchFile,loadMods)
         # self.isActive = (GPath('COBL Main.esm') in loadMods)
        #self.id_ingred = {}
        self.type_stats = {'INGR':{},}
        self.type_attrs = {
            'INGR':('eid', 'full', 'weight', 'value', 'effects'),
        }
        self.aliases = aliases or {} #-- For aliasing mod names - why?

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        loadFactory= LoadFactory(False,MreIngr)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        for type in self.type_stats:
            stats, attrs = self.type_stats[type], self.type_attrs[type]
            for record in getattr(modFile,type).getActiveRecords():
                longid = mapper(record.fid)
                recordGetAttr = record.__getattribute__
                stats[longid] = tuple(recordGetAttr(attr) for attr in attrs)


    def writeToText(self,textPath):
        """Writes stats to specified text file."""
        out = textPath.open('w')
        def getSortedIds(stats):
            longids = stats.keys()
            longids.sort(key=lambda a: stats[a][0])
            longids.sort(key=itemgetter(0))
            return longids
        for type,format,header in (
            #--Ingredients
            ('INGR', bolt.csvFormat('ssfis')+'\n',
                ('"' + '","'.join((_('Type'),_('Mod Name'),_('ObjectIndex'),
                _('Editor Id'),_('Name'),_('Weight'),_('Value'),_('Effects'))) + '"\n')),
            ):
            stats = self.type_stats[type]
            if not stats: continue
            out.write(header)
            for longid in getSortedIds(stats):
                out.write('"%s","%s","0x%06X",' % (type,longid[0].s,longid[1]))
                out.write(format % stats[longid])
        out.close()


#        """Scans specified mod file to extract info. May add record to patch mod,
 #       but won't alter it."""
  #      if not self.isActive: return
   #     id_ingred = self.id_ingred
    #    mapper = modFile.getLongMapper()
     #   for record in modFile.INGR.getActiveRecords():
      #      if not record.full: continue #--Ingredient must have name!
       #     effects = record.getEffects()
        #    if not ('SEFF',0) in effects:
         #       id_ingred[mapper(record.fid)] = (record.eid, record.full, effects)

#    def buildPatch(self,log,progress):
 #       """Edits patch file as desired. Will write to log."""
  #      if not self.isActive: return
   #     #--Setup
    #    mgef_name = self.patchFile.getMgefName()
     #   for mgef in mgef_name:
      #      mgef_name[mgef] = re.sub(_('(Attribute|Skill)'),'',mgef_name[mgef])
       # actorEffects = bush.actorValueEffects
        #actorNames = bush.actorValues
#        keep = self.patchFile.getKeeper()
        #--Book generatator
 #       def getBook(objectId,eid,full,value,iconPath,modelPath,modb_p):
  #          book = MreBook(('BOOK',0,0,0,0))
   #         book.longFids = True
    #        book.changed = True
     #       book.eid = eid
      #      book.full = full
       #     book.value = value
        #    book.weight = 0.2
         #   book.fid = keep((GPath('Cobl Main.esm'),objectId))
          #  book.text = '<div align="left"><font face=3 color=4444>'
           # book.text += _("Salan's Catalog of %s\r\n\r\n") % full
            #book.iconPath = iconPath
#            book.model = book.getDefault('model')
 #           book.model.modPath = modelPath
  #          book.model.modb_p = modb_p
   #         book.modb = book
    #        self.patchFile.BOOK.setRecord(book)
     #       return book
        #--Ingredients Catalog
      #  id_ingred = self.id_ingred
       # iconPath,modPath,modb_p = ('Clutter\IconBook9.dds','Clutter\Books\Octavo02.NIF','\x03>@A')
        #for (num,objectId,full,value) in bush.ingred_alchem:
       #     book = getBook(objectId,'cobCatAlchemIngreds'+`num`,full,value,iconPath,modPath,modb_p)
         #   buff = cStringIO.StringIO()
          #  buff.write(book.text)
           # for eid,full,effects in sorted(id_ingred.values(),key=lambda a: a[1].lower()):
            #    buff.write(full+'\r\n')
             #   for mgef,actorValue in effects[:num]:
              #      effectName = mgef_name[mgef]
               #     if mgef in actorEffects: effectName += actorNames[actorValue]
#                #    buff.write('  '+effectName+'\r\n')
 #               buff.write('\r\n')
  #          book.text = re.sub('\r\n','<br>\r\n',buff.getvalue())
   #     #--Get Ingredients by Effect
    #    effect_ingred = {}
     #   for fid,(eid,full,effects) in id_ingred.iteritems():
      #      for index,(mgef,actorValue) in enumerate(effects):
       #         effectName = mgef_name[mgef]
        #        if mgef in actorEffects: effectName += actorNames[actorValue]
#                if effectName not in effect_ingred: effect_ingred[effectName] = []
 #               effect_ingred[effectName].append((index,full))
        #--Effect catalogs
  #      iconPath,modPath,modb_p = ('Clutter\IconBook7.dds','Clutter\Books\Octavo01.NIF','\x03>@A')
   #     for (num,objectId,full,value) in bush.effect_alchem:
    #        book = getBook(objectId,'cobCatAlchemEffects'+`num`,full,value,iconPath,modPath,modb_p)
     #       buff = cStringIO.StringIO()
      #      buff.write(book.text)
       #     for effectName in sorted(effect_ingred.keys()):
        #        effects = [indexFull for indexFull in effect_ingred[effectName] if indexFull[0] < num]
         #       if effects:
          #          buff.write(effectName+'\r\n')
           #         for (index,full) in sorted(effects,key=lambda a: a[1].lower()):
            #            exSpace = ('',' ')[index == 0]
             #           buff.write(' '+`index + 1`+exSpace+' '+full+'\r\n')
              #      buff.write('\r\n')
#            book.text = re.sub('\r\n','<br>\r\n',buff.getvalue())
        #--Log
 #       log.setHeader('= '+self.__class__.name)
  #      log(_('* Ingredients Cataloged: %d') % (len(id_ingred),))
   #     log(_('* Effects Cataloged: %d') % (len(effect_ingred)))

#------------------------------------------------------------------------------
class ModDetails:
    """Details data for a mods file. Similar to TesCS Details view."""
    def __init__(self,modInfo=None,progress=None):
        """Initialize."""
        self.group_records = {} #--group_records[group] = [(fid0,eid0),(fid1,eid1),...]

    def readFromMod(self,modInfo,progress=None):
        """Extracts details from mod file."""
        def getRecordReader(ins,flags,size):
            """Decompress record data as needed."""
            if not MreRecord._flags1(flags).compressed:
                return (ins,ins.tell()+size)
            else:
                import zlib
                sizeCheck, = struct.unpack('I',ins.read(4))
                decomp = zlib.decompress(ins.read(size-4))
                if len(decomp) != sizeCheck:
                    raise ModError(self.inName,
                        _('Mis-sized compressed data. Expected %d, got %d.') % (size,len(decomp)))
                reader = ModReader(modInfo.name,cStringIO.StringIO(decomp))
                return (reader,sizeCheck)
        progress = progress or bolt.Progress()
        group_records = self.group_records = {}
        records = group_records['TES4'] = []
        ins = ModReader(modInfo.name,modInfo.getPath().open('rb'))
        while not ins.atEnd():
            (type,size,str0,fid,uint2) = ins.unpackRecHeader()
            if type == 'GRUP':
                progress(1.0*ins.tell()/modInfo.size,_("Scanning: ")+str0)
                records = group_records.setdefault(str0,[])
                if str0 in ('CELL','WRLD','DIAL'):
                    ins.seek(size-20,1)
            elif type != 'GRUP':
                eid = ''
                nextRecord = ins.tell() + size
                recs,endRecs = getRecordReader(ins,str0,size)
                while recs.tell() < endRecs:
                    (type,size) = recs.unpackSubHeader()
                    if type == 'EDID':
                        eid = recs.readString(size)
                        break
                    ins.seek(size,1)
                records.append((fid,eid))
                ins.seek(nextRecord)
        ins.close()
        del group_records['TES4']

#------------------------------------------------------------------------------
class ModGroups:
    """Groups for mods with functions for importing/exporting from/to text file."""
    @staticmethod
    def filter(mods):
        """Returns non-group header mods."""
        return [x for x in mods if not reGroupHeader.match(x.s)]

    def __init__(self):
        """Initialize."""
        self.mod_group = {}

    def readFromModInfos(self,mods=None):
        """Imports mods/groups from modInfos."""
        column = modInfos.table.getColumn('group')
        mods = ModGroups.filter(mods or column.keys())
        groups = tuple(column.get(x) for x in mods)
        self.mod_group.update((x,y) for x,y in zip(mods,groups) if y)

    def writeToModInfos(self,mods=None):
        """Exports mod groups to modInfos."""
        mods = ModGroups.filter(mods or modInfos.table.data.keys())
        mod_group = self.mod_group
        column = modInfos.table.getColumn('group')
        changed = 0
        for mod in mods:
            if mod in mod_group and column.get(mod) != mod_group[mod]:
                column[mod] = mod_group[mod]
                changed += 1
        return changed

    def readFromText(self,textPath):
        """Imports mod groups from specified text file."""
        textPath = GPath(textPath)
        mod_group = self.mod_group
        ins = bolt.CsvReader(textPath)
        for fields in ins:
            if len(fields) >= 2 and reModExt.search(fields[0]):
               mod,group = fields[:2]
               mod_group[GPath(mod)] = group
        ins.close()

    def writeToText(self,textPath):
        """Exports eids to specified text file."""
        textPath = GPath(textPath)
        mod_group = self.mod_group
        rowFormat = '"%s","%s"\n'
        out = textPath.open('w')
        out.write(rowFormat % (_("Mod"),_("Group")))
        for mod in sorted(mod_group):
            out.write(rowFormat % (mod.s,mod_group[mod]))
        out.close()

#------------------------------------------------------------------------------
class PCFaces:
    """Package: Objects and functions for working with face data."""
    flags = Flags(0L,Flags.getNames('name','race','gender','hair','eye','iclass','stats','factions','modifiers','spells'))

    class PCFace(object):
        """Represents a face."""
        __slots__ = ('masters','eid','pcName','race','gender','eye','hair',
            'hairLength','hairRed','hairBlue','hairGreen','unused3','fggs_p','fgga_p','fgts_p','level','attributes',
            'skills','health','unused2','baseSpell','fatigue','iclass','factions','modifiers','spells')
        def __init__(self):
            self.masters = []
            self.eid = self.pcName = 'generic'
            self.fggs_p = self.fgts_p = '\x00'*4*50
            self.fgga_p = '\x00'*4*30
            self.unused2 = null2
            self.health = self.unused3 = self.baseSpell = self.fatigue = self.level = 0
            self.skills = self.attributes = self.iclass = None
            self.factions = []
            self.modifiers = []
            self.spells = []

        def getGenderName(self):
            return self.gender and 'Female' or 'Male'

        def getRaceName(self):
            return bush.raceNames.get(self.race,_('Unknown'))

        def convertRace(self,fromRace,toRace):
            """Converts face from one race to another while preserving structure, etc."""
            for attr,num in (('fggs_p',50),('fgga_p',30),('fgts_p',50)):
                format = `num`+'f'
                sValues = list(struct.unpack(format,getattr(self,attr)))
                fValues = list(struct.unpack(format,getattr(fromRace,attr)))
                tValues = list(struct.unpack(format,getattr(toRace,attr)))
                for index,(sValue,fValue,tValue) in enumerate(zip(sValues,fValues,tValues)):
                    sValues[index] = sValue + fValue - tValue
                setattr(self,attr,struct.pack(format,*sValues))

    # SAVES -------------------------------------------------------------------
    @staticmethod
    def save_getNamePos(saveName,data,pcName):
        """Safely finds position of name within save ACHR data."""
        namePos = data.find(pcName)
        if namePos == -1:
            raise SaveFileError(saveName,_('Failed to find pcName in PC ACHR record.'))
        namePos2 = data.find(pcName,namePos+1)
        if namePos2 != -1:
            raise SaveFileError(saveName,_(
                'Uncertain about position of face data, probably because '
                'player character name is too short. Try renaming player '
                'character in save game.'))
        return namePos

    # Save Get ----------------------------------------------------------------
    @staticmethod
    def save_getFace(saveFile):
        """DEPRECATED. Same as save_getPlayerFace(saveFile)."""
        return PCFaces.save_getPlayerFace(saveFile)

    @staticmethod
    def save_getFaces(saveFile):
        """Returns player and created faces from a save file or saveInfo."""
        if isinstance(saveFile,SaveInfo):
            saveInfo = saveFile
            saveFile = SaveFile(saveInfo)
            saveFile.load()
        faces = PCFaces.save_getCreatedFaces(saveFile)
        playerFace = PCFaces.save_getPlayerFace(saveFile)
        faces[7] = playerFace
        return faces

    @staticmethod
    def save_getCreatedFace(saveFile,targetid):
        """Gets a particular created face."""
        return PCFaces.save_getCreatedFaces(saveFile,targetid).get(targetid)

    @staticmethod
    def save_getCreatedFaces(saveFile,targetid=None):
        """Returns created faces from savefile. If fid is supplied, will only
        return created face with that fid.
        Note: Created NPCs do NOT use irefs!"""
        targetid = bolt.intArg(targetid)
        if isinstance(saveFile,SaveInfo):
            saveInfo = saveFile
            saveFile = SaveFile(saveInfo)
            saveFile.load()
        faces = {}
        for record in saveFile.created:
            if record.recType != 'NPC_': continue
            #--Created NPC record
            if targetid and record.fid != targetid: continue
            npc = record.getTypeCopy()
            face = faces[npc.fid] = PCFaces.PCFace()
            face.masters = saveFile.masters
            for attr in ('eid','race','eye','hair','hairLength',
                         'hairRed','hairBlue','hairGreen','unused3',
                         'fggs_p','fgga_p','fgts_p','level','skills',
                         'health','unused2','baseSpell', 'fatigue',
                         'attributes','iclass'):
                setattr(face,attr,getattr(npc,attr))
            face.gender = (0,1)[npc.flags.female]
            face.pcName = npc.full
            #--Changed NPC Record
            PCFaces.save_getChangedNpc(saveFile,record.fid,face)
        return faces

    @staticmethod
    def save_getChangedNpc(saveFile,fid,face=None):
        """Update face with data from npc change record."""
        face = face or PCFaces.PCFace()
        changeRecord = saveFile.getRecord(fid)
        if not changeRecord:
            return face
        fid,recType,recFlags,version,data = changeRecord
        npc = SreNPC(recFlags,data)
        if npc.acbs:
            face.gender = npc.acbs.flags.female
            face.level = npc.acbs.level
            face.baseSpell = npc.acbs.baseSpell
            face.fatigue = npc.acbs.fatigue
            #deprint('level,baseSpell,fatigue:',face.level,face.baseSpell,face.fatigue)
        for attr in ('attributes','skills','health','unused2'):
            value = getattr(npc,attr)
            if value != None:
                setattr(face,attr,value)
                #deprint(attr,value)
        #--Iref >> fid
        getFid = saveFile.getFid
        face.spells = [getFid(x) for x in (npc.spells or [])]
        face.factions = [(getFid(x),y) for x,y in (npc.factions or [])]
        face.modifiers = (npc.modifiers or [])[:]
        #delist('npc.spells:',[strFid(x) for x in face.spells])
        #delist('npc.factions:',face.factions)
        #delist('npc.modifiers:',face.modifiers)
        return face

    @staticmethod
    def save_getPlayerFace(saveFile):
        """Extract player face from save file."""
        if isinstance(saveFile,SaveInfo):
            saveInfo = saveFile
            saveFile = SaveFile(saveInfo)
            saveFile.load()
        face = PCFaces.PCFace()
        face.pcName = saveFile.pcName
        face.masters = saveFile.masters
        #--Player ACHR
        record = saveFile.getRecord(0x14)
        data = record[-1]
        namePos = PCFaces.save_getNamePos(saveFile.fileInfo.name,data,saveFile.pcName)
        (face.fggs_p, face.fgga_p, face.fgts_p, face.race, face.hair, face.eye,
            face.hairLength, face.hairRed, face.hairBlue, face.hairGreen, face.unused3, face.gender) = struct.unpack(
            '=200s120s200s3If3BsB',data[namePos-542:namePos-1])
        classPos = namePos+len(saveFile.pcName)+1
        face.iclass, = struct.unpack('I',data[classPos:classPos+4])
        #--Iref >> fid
        getFid = saveFile.getFid
        face.race = getFid(face.race)
        face.hair = getFid(face.hair)
        face.eye = getFid(face.eye)
        face.iclass = getFid(face.iclass)
        #--Changed NPC Record
        PCFaces.save_getChangedNpc(saveFile,7,face)
        #--Done
        return face

    # Save Set ----------------------------------------------------------------
    @staticmethod
    def save_setFace(saveInfo,face,flags=0L):
        """DEPRECATED. Write a pcFace to a save file."""
        saveFile = SaveFile(saveInfo)
        saveFile.load()
        PCFaces.save_setPlayerFace(saveFile,face,flags)
        saveFile.safeSave()

    @staticmethod
    def save_setCreatedFace(saveFile,targetid,face):
        """Sets created face in savefile to specified face.
        Note: Created NPCs do NOT use irefs!"""
        targetid = bolt.intArg(targetid)
        #--Find record
        for index,record in enumerate(saveFile.created):
            if record.fid == targetid:
                npc = record.getTypeCopy()
                saveFile.created[index] = npc
                break
        else:
            raise StateError("Record %08X not found in %s." % (targetid,saveFile.fileInfo.name.s))
        if npc.recType != 'NPC_':
            raise StateError("Record %08X in %s is not an NPC." % (targetid,saveFile.fileInfo.name.s))
        #--Update masters
        for fid in (face.race, face.eye, face.hair):
            if not fid: continue
            master = face.masters[getModIndex(fid)]
            if master not in saveFile.masters:
                saveFile.masters.append(master)
        masterMap = MasterMap(face.masters,saveFile.masters)
        #--Set face
        npc.full = face.pcName
        npc.flags.female = (face.gender & 0x1)
        npc.setRace(masterMap(face.race,0x00907)) #--Default to Imperial
        npc.eye = masterMap(face.eye,None)
        npc.hair = masterMap(face.hair,None)
        npc.hairLength = face.hairLength
        npc.hairRed = face.hairRed
        npc.hairBlue = face.hairBlue
        npc.hairGreen = face.hairGreen
        npc.unused3 = face.unused3
        npc.fggs_p = face.fggs_p
        npc.fgga_p = face.fgga_p
        npc.fgts_p = face.fgts_p
        #--Stats: Skip Level, baseSpell, fatigue and factions since they're discarded by game engine.
        if face.skills: npc.skills = face.skills
        if face.health:
            npc.health = face.health
            npc.unused2 = face.unused2
        if face.attributes: npc.attributes = face.attributes
        if face.iclass: npc.iclass = face.iclass
        npc.setChanged()
        npc.getSize()

        #--Change record?
        changeRecord = saveFile.getRecord(npc.fid)
        if changeRecord == None: return
        fid,recType,recFlags,version,data = changeRecord
        npc = SreNPC(recFlags,data)
        #deprint(SreNPC.flags(recFlags).getTrueAttrs())
        if not npc.acbs: npc.acbs = npc.getDefault('acbs')
        npc.acbs.flags.female = face.gender
        npc.acbs.level = face.level
        npc.acbs.baseSpell = face.baseSpell
        npc.acbs.fatigue = face.fatigue
        npc.modifiers = face.modifiers[:]
        #--Fid conversion
        getIref = saveFile.getIref
        npc.spells = [getIref(x) for x in face.spells]
        npc.factions = [(getIref(x),y) for x,y in face.factions]

        #--Done
        saveFile.setRecord(npc.getTuple(fid,version))

    @staticmethod
    def save_setPlayerFace(saveFile,face,flags=0L,morphFacts=None):
        """Write a pcFace to a save file."""
        flags = PCFaces.flags(flags)
        #deprint(flags.getTrueAttrs())
        #--Update masters
        for fid in (face.race, face.eye, face.hair, face.iclass):
            if not fid: continue
            master = face.masters[getModIndex(fid)]
            if master not in saveFile.masters:
                saveFile.masters.append(master)
        masterMap = MasterMap(face.masters,saveFile.masters)

        #--Player ACHR
        #--Buffer for modified record data
        buff = cStringIO.StringIO()
        def buffPack(format,*args):
            buff.write(struct.pack(format,*args))
        def buffPackRef(oldFid,doPack=True):
            newFid = oldFid and masterMap(oldFid,None)
            if newFid and doPack:
                newRef = saveFile.getIref(newFid)
                buff.write(struct.pack('I',newRef))
            else:
                buff.seek(4,1)
        oldRecord = saveFile.getRecord(0x14)
        oldData = oldRecord[-1]
        namePos = PCFaces.save_getNamePos(saveFile.fileInfo.name,oldData,saveFile.pcName)
        buff.write(oldData)
        #--Modify buffer with face data.
        buff.seek(namePos-542)
        buffPack('=200s120s200s',face.fggs_p, face.fgga_p, face.fgts_p)
        #--Race?
        buffPackRef(face.race,flags.race)
        #--Hair, Eyes?
        buffPackRef(face.hair,flags.hair)
        buffPackRef(face.eye,flags.eye)
        if flags.hair:
            buffPack('=f3Bs',face.hairLength,face.hairRed,face.hairBlue,face.hairGreen,face.unused3)
        else:
            buff.seek(8,1)
        #--Gender?
        if flags.gender:
            buffPack('B',face.gender)
        else:
            buff.seek(1,1)
        #--Name?
        if flags.name:
            postName = buff.getvalue()[buff.tell()+len(saveFile.pcName)+2:]
            buffPack('B',len(face.pcName)+1)
            buff.write(face.pcName+'\x00')
            buff.write(postName)
            buff.seek(-len(postName),1)
            saveFile.pcName = face.pcName
        else:
            buff.seek(len(saveFile.pcName)+2,1)
        #--Class?
        if flags.iclass and face.iclass:
            pos = buff.tell()
            newClass = masterMap(face.iclass)
            oldClass = saveFile.fids[struct.unpack('I',buff.read(4))[0]]
            customClass = saveFile.getIref(0x22843)
            if customClass not in (newClass,oldClass):
                buff.seek(pos)
                buffPackRef(newClass)

        newData = buff.getvalue()
        saveFile.setRecord(oldRecord[:-1]+(newData,))

        #--Player NPC
        (fid,recType,recFlags,version,data) = saveFile.getRecord(7)
        npc = SreNPC(recFlags,data)
        #--Gender
        if flags.gender and npc.acbs:
            npc.acbs.flags.female = face.gender
        #--Stats
        if flags.stats and npc.acbs:
            npc.acbs.level = face.level
            npc.acbs.baseSpell = face.baseSpell
            npc.acbs.fatigue = face.fatigue
            npc.attributes = face.attributes
            npc.skills = face.skills
            npc.health = face.health
            npc.unused2 = face.unused2
        #--Factions: Faction assignment doesn't work. (Probably stored in achr.)
        #--Modifiers, Spells, Name
        if flags.modifiers: npc.modifiers = face.modifiers[:]
        if flags.spells:
            #delist('Set PC Spells:',face.spells)
            npc.spells = [saveFile.getIref(x) for x in face.spells]
        npc.full = None
        saveFile.setRecord(npc.getTuple(fid,version))
        #--Save
        buff.close()

    # Save Misc ----------------------------------------------------------------
    @staticmethod
    def save_repairHair(saveInfo):
        """Repairs hair if it has been zeroed. (Which happens if hair came from a
        cosmetic mod that has since been removed.) Returns True if repaired, False
        if no repair was necessary."""
        saveFile = SaveFile(saveInfo)
        saveFile.load()
        record = saveFile.getRecord(0x14)
        data = record[-1]
        namePos = PCFaces.save_getNamePos(saveInfo.name,data,saveFile.pcName)
        raceRef,hairRef = struct.unpack('2I',data[namePos-22:namePos-14])
        if hairRef != 0: return False
        raceForm = raceRef and saveFile.fids[raceRef]
        gender, = struct.unpack('B',data[namePos-2])
        if gender:
            hairForm = bush.raceHairFemale.get(raceForm,0x1da83)
        else:
            hairForm = bush.raceHairMale.get(raceForm,0x90475)
        hairRef = saveFile.getIref(hairForm)
        data = data[:namePos-18]+struct.pack('I',hairRef)+data[namePos-14:]
        saveFile.setRecord(record[:-1]+(data,))
        saveFile.safeSave()
        return True

    # MODS --------------------------------------------------------------------
    @staticmethod
    def mod_getFaces(modInfo):
        """Returns an array of PCFaces from a mod file."""
        #--Mod File
        loadFactory = LoadFactory(False,MreNpc)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        faces = {}
        for npc in modFile.NPC_.getActiveRecords():
            face = PCFaces.PCFace()
            face.masters = modFile.tes4.masters + [modInfo.name]
            for field in ('eid','race','eye','hair','hairLength',
                          'hairRed','hairBlue','hairGreen','unused3',
                          'fggs_p','fgga_p','fgts_p','level','skills',
                          'health','unused2','baseSpell',
                          'fatigue','attributes','iclass'):
                setattr(face,field,getattr(npc,field))
            face.gender = npc.flags.female
            face.pcName = npc.full
            faces[face.eid] = face
            #print face.pcName, face.race, face.hair, face.eye, face.hairLength, face.hairRed, face.hairBlue, face.hairGreen, face.unused3
        return faces

    @staticmethod
    def mod_getRaceFaces(modInfo):
        """Returns an array of Race Faces from a mod file."""
        loadFactory = LoadFactory(False,MreRace)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        faces = {}
        for race in modFile.RACE.getActiveRecords():
            face = PCFaces.PCFace()
            face.masters = []
            for field in ('eid','fggs_p','fgga_p','fgts_p'):
                setattr(face,field,getattr(race,field))
            faces[face.eid] = face
        return faces

    @staticmethod
    def mod_addFace(modInfo,face):
        """Writes a pcFace to a mod file."""
        #--Mod File
        loadFactory = LoadFactory(True,MreNpc)
        modFile = ModFile(modInfo,loadFactory)
        if modInfo.getPath().exists():
            modFile.load(True)
        #--Tes4
        tes4 = modFile.tes4
        if not tes4.author:
            tes4.author = '[wb]'
        if not tes4.description:
            tes4.description = _('Face dump from save game.')
        if GPath('Oblivion.esm') not in tes4.masters:
            tes4.masters.append(GPath('Oblivion.esm'))
        masterMap = MasterMap(face.masters,tes4.masters+[modInfo.name])
        #--Eid
        npcEids = set([record.eid for record in modFile.NPC_.records])
        eidForm = ''.join(("sg", bush.raceShortNames.get(face.race,'Unk'),
            (face.gender and 'a' or 'u'), re.sub(r'\W','',face.pcName),'%02d'))
        count,eid = 0, eidForm % 0
        while eid in npcEids:
            count += 1
            eid = eidForm % count
        #--NPC
        npcid = genFid(len(tes4.masters),tes4.getNextObject())
        npc = MreNpc(('NPC_',0,0x40000,npcid,0))
        npc.eid = eid
        npc.full = face.pcName
        npc.flags.female = face.gender
        npc.iclass = masterMap(face.iclass,0x237a8) #--Default to Acrobat
        npc.setRace(masterMap(face.race,0x00907)) #--Default to Imperial
        npc.eye = masterMap(face.eye,None)
        npc.hair = masterMap(face.hair,None)
        npc.hairLength = face.hairLength
        npc.hairRed = face.hairRed
        npc.hairBlue = face.hairBlue
        npc.hairGreen = face.hairGreen
        npc.unused3 = face.unused3
        npc.fggs_p = face.fggs_p
        npc.fgga_p = face.fgga_p
        npc.fgts_p = face.fgts_p
        #--Stats
        npc.level = face.level
        npc.baseSpell = face.baseSpell
        npc.fatigue = face.fatigue
        if face.skills: npc.skills = face.skills
        if face.health:
            npc.health = face.health
            npc.unused2 = face.unused2
        if face.attributes: npc.attributes = face.attributes
        npc.setChanged()
        modFile.NPC_.records.append(npc)
        #--Save
        modFile.safeSave()
        return npc

#------------------------------------------------------------------------------
class CleanMod:
    """Fixes cells to avoid nvidia fog problem."""
    def __init__(self,modInfo):
        self.modInfo = modInfo
        self.fixedCells = set()

    def clean(self,progress):
        """Duplicates file, then walks through and edits file as necessary."""
        progress.setFull(self.modInfo.size)
        fixedCells = self.fixedCells
        fixedCells.clear()
        #--File stream
        path = self.modInfo.getPath()
        #--Scan/Edit
        ins = ModReader(self.modInfo.name,path.open('rb'))
        out = path.temp.open('wb')
        def copy(size,back=False):
            buff = ins.read(size)
            out.write(buff)
        def copyPrev(size):
            ins.seek(-size,1)
            buff = ins.read(size)
            out.write(buff)
        while not ins.atEnd():
            progress(ins.tell())
            (type,size,str0,fid,uint2) = ins.unpackRecHeader()
            copyPrev(20)
            if type == 'GRUP':
                if fid != 0: #--Ignore sub-groups
                    pass
                elif str0 not in ('CELL','WRLD'):
                    copy(size-20)
            #--Handle cells
            elif type == 'CELL':
                nextRecord = ins.tell() + size
                while ins.tell() < nextRecord:
                    (type,size) = ins.unpackSubHeader()
                    copyPrev(6)
                    if type != 'XCLL':
                        copy(size)
                    else:
                        color,near,far,rotXY,rotZ,fade,clip = ins.unpack('=12s2f2l2f',size,'CELL.XCLL')
                        if not (near or far or clip):
                            near = 0.0001
                            fixedCells.add(fid)
                        out.write(struct.pack('=12s2f2l2f',color,near,far,rotXY,rotZ,fade,clip))
            #--Non-Cells
            else:
                copy(size)
        #--Done
        ins.close()
        out.close()
        if fixedCells:
            self.modInfo.makeBackup()
            path.untemp()
            self.modInfo.setmtime()
        else:
            path.temp.remove()

#------------------------------------------------------------------------------
class UndeleteRefs:
    """Change refs in cells from deleted to initially disabled.."""
    def __init__(self,modInfo):
        self.modInfo = modInfo
        self.fixedRefs = set()

    def undelete(self,progress):
        """Duplicates file, then walks through and edits file as necessary."""
        progress.setFull(self.modInfo.size)
        fixedRefs = self.fixedRefs
        fixedRefs.clear()
        #--File stream
        path = self.modInfo.getPath()
        #--Scan/Edit
        ins = ModReader(self.modInfo.name,path.open('rb'))
        out = path.temp.open('wb')
        def copy(size,back=False):
            buff = ins.read(size)
            out.write(buff)
        def copyPrev(size):
            ins.seek(-size,1)
            buff = ins.read(size)
            out.write(buff)
        while not ins.atEnd():
            progress(ins.tell())
            (type,size,flags,fid,uint2) = ins.unpackRecHeader()
            copyPrev(20)
            if type == 'GRUP':
                if fid != 0: #--Ignore sub-groups
                    pass
                elif flags not in ('CELL','WRLD'):
                    copy(size-20)
            #--Handle cells
            else:
                if flags & 0x20 and type in ('ACHR','ACRE','REFR'):
                    flags = (flags & ~0x20) | 0x1000
                    out.seek(-20,1)
                    out.write(struct.pack('=4s4I',type,size,flags,fid,uint2))
                    fixedRefs.add(fid)
                copy(size)
        #--Done
        ins.close()
        out.close()
        if fixedRefs:
            self.modInfo.makeBackup()
            path.untemp()
            self.modInfo.setmtime()
        else:
            path.temp.remove()

#------------------------------------------------------------------------------
class SaveSpells:
    """Player spells of a savegame."""

    def __init__(self,saveInfo):
        """Initialize."""
        self.saveInfo = saveInfo
        self.saveFile = None
        self.allSpells = {} #--spells[(modName,objectIndex)] = (name,type)

    def load(self,progress=None):
        """Loads savegame and and extracts created spells from it and its masters."""
        progress = progress or bolt.Progress()
        saveFile = self.saveFile = SaveFile(self.saveInfo)
        saveFile.load(SubProgress(progress,0,0.4))
        progress = SubProgress(progress,0.4,1.0,len(saveFile.masters)+1)
        #--Extract spells from masters
        for index,master in enumerate(saveFile.masters):
            progress(index,master.s)
            if master in modInfos:
                self.importMod(modInfos[master])
        #--Extract created spells
        allSpells = self.allSpells
        saveName = self.saveInfo.name
        progress(progress.full-1,saveName.s)
        for record in saveFile.created:
            if record.recType == 'SPEL':
                allSpells[(saveName,getObjectIndex(record.fid))] = record.getTypeCopy()

    def importMod(self,modInfo):
        """Imports spell info from specified mod."""
        #--Spell list already extracted?
        if 'bash.spellList' in modInfo.extras:
            self.allSpells.update(modInfo.extras['bash.spellList'])
            return
        #--Else extract spell list
        loadFactory= LoadFactory(False,MreSpel)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        modFile.convertToLongFids(('SPEL',))
        spells = modInfo.extras['bash.spellList'] = dict(
            [(record.fid,record) for record in modFile.SPEL.getActiveRecords()])
        self.allSpells.update(spells)

    def getPlayerSpells(self):
        """Returns players spell list from savegame. (Returns ONLY spells. I.e., not abilities, etc.)"""
        saveFile = self.saveFile
        #--Get masters and npc spell fids
        masters = saveFile.masters[:]
        maxMasters = len(masters) - 1
        (fid,recType,recFlags,version,data) = saveFile.getRecord(7)
        npc = SreNPC(recFlags,data)
        pcSpells = {} #--pcSpells[spellName] = iref
        #--NPC doesn't have any spells?
        if not npc.spells:
            return pcSpells
        #--Get spell names to match fids
        for iref in npc.spells:
            if (iref >> 24) == 255:
                fid = iref
            else:
                fid = saveFile.fids[iref]
            modIndex,objectIndex = getFormIndices(fid)
            if modIndex == 255:
                master = self.saveInfo.name
            elif modIndex <= maxMasters:
                master = masters[modIndex]
            else: #--Bad fid?
                continue
            #--Get spell data
            record = self.allSpells.get((master,objectIndex),None)
            if record and record.full and record.spellType == 0 and fid != 0x136:
                pcSpells[record.full] = (iref,record)
        return pcSpells

    def removePlayerSpells(self,spellsToRemove):
        """Removes specified spells from players spell list."""
        (fid,recType,recFlags,version,data) = self.saveFile.getRecord(7)
        npc = SreNPC(recFlags,data)
        if npc.spells and spellsToRemove:
            #--Remove spells and save
            npc.spells = [iref for iref in npc.spells if iref not in spellsToRemove]
            self.saveFile.setRecord(npc.getTuple(fid,version))
            self.saveFile.safeSave()

# Patchers 1 ------------------------------------------------------------------
#------------------------------------------------------------------------------
class PatchFile(ModFile):
    """Defines and executes patcher configuration."""
    #--Class
    mergeClasses = (
        MreActi, MreAlch, MreAmmo, MreAnio, MreAppa, MreArmo, MreBook, MreBsgn, MreClas,
        MreClot, MreCont, MreCrea, MreDoor, MreEfsh, MreEnch, MreEyes, MreFact, MreFlor, MreFurn,
        MreGlob, MreGras, MreHair, MreIngr, MreKeym, MreLigh, MreLscr, MreLvlc, MreLvli,
        MreLvsp, MreMgef, MreMisc, MreNpc,  MrePack, MreQust, MreRace, MreScpt, MreSgst,
        MreSlgm, MreSoun, MreSpel, MreStat, MreTree, MreWatr, MreWeap, MreWthr,
        MreClmt, MreCsty, MreIdle, MreLtex, MreRegn, MreSbsp, MreSkil)

    @staticmethod
    def modIsMergeable(modInfo,progress=None):
        """Returns True or error message indicating whether specified mod is mergeable."""
        if reEsmExt.search(modInfo.name.s):
            return _("Is esm.")
        #--Bashed Patch
        if modInfo.header.author == "BASHED PATCH":
            return _("Is Bashed Patch.")
        #--Bsa?
        reBsa = re.compile(re.escape(modInfo.name.sroot)+'.*bsa$',re.I)
        for file in modInfos.dir.list():
            if reBsa.match(file.s):
                return _("Has BSA archive.")
        #--Load test
        mergeTypes = set([recClass.classType for recClass in PatchFile.mergeClasses])
        modFile = ModFile(modInfo,LoadFactory(False,*mergeTypes))
        try:
            modFile.load(True)
        except ModError, error:
            return str(error)
        #--Skipped over types?
        if modFile.topsSkipped:
            return _("Unsupported types: ") + ', '.join(sorted(modFile.topsSkipped))
        #--Empty mod
        if not modFile.tops:
            return _("Empty mod.")
        #--New record
        lenMasters = len(modFile.tes4.masters)
        for type,block in modFile.tops.iteritems():
            for record in block.getActiveRecords():
                if record.fid >> 24 >= lenMasters:
                    return _("New record %08X in block %s.") % (record.fid,type)
        #--Else
        return True

    #--Instance
    def __init__(self,modInfo,patchers):
        """Initialization."""
        ModFile.__init__(self,modInfo,None)
        self.tes4.author = 'BASHED PATCH'
        self.tes4.masters = [GPath('Oblivion.esm')]
        self.longFids = True
        #--New attrs
        self.aliases = {} #--Aliases from one mod name to another. Used by text file patchers.
        self.patchers = patchers
        self.keepIds = set()
        self.mergeIds = set()
        self.loadErrorMods = []
        self.worldOrphanMods = []
        self.unFilteredMods = []
        self.compiledAllMods = []
        #--Config
        self.bodyTags = 'ARGHTCCPBS' #--Default bodytags
        #--Mods
        patchTime = modInfo.mtime
        self.setMods([name for name in modInfos.ordered if modInfos[name].mtime < patchTime],[])
        for patcher in self.patchers:
            patcher.initPatchFile(self,self.loadMods)

    def setMods(self,loadMods=None,mergeMods=None):
        """Sets mod lists and sets."""
        if loadMods != None: self.loadMods = loadMods
        if mergeMods != None: self.mergeMods = mergeMods
        self.loadSet = set(self.loadMods)
        self.mergeSet = set(self.mergeMods)
        self.allMods = modInfos.getOrdered(self.loadSet|self.mergeSet)
        self.allSet = set(self.allMods)

    def getKeeper(self):
        """Returns a function to add fids to self.keepIds."""
        def keep(fid):
            self.keepIds.add(fid)
            return fid
        return keep

    def initData(self,progress):
        """Gives each patcher a chance to get its source data."""
        if not len(self.patchers): return
        progress = progress.setFull(len(self.patchers))
        for index,patcher in enumerate(self.patchers):
            progress(index,_("Preparing\n%s") % patcher.getName())
            patcher.initData(SubProgress(progress,index))
        progress(progress.full,_('Patchers prepared.'))

    def initFactories(self,progress):
        """Gets load factories."""
        progress(0,_("Processing."))
        def updateClasses(type_classes,newClasses):
            if not newClasses: return
            for item in newClasses:
                if not isinstance(item,str):
                    type_classes[item.classType] = item
                elif item not in type_classes:
                    type_classes[item] = item
        readClasses = {}
        writeClasses = {}
        updateClasses(readClasses,(MreMgef,MreScpt)) #--Need info from magic effects.
        updateClasses(writeClasses,(MreMgef,)) #--Need info from magic effects.
        for patcher in self.patchers:
            updateClasses(readClasses, patcher.getReadClasses())
            updateClasses(writeClasses,patcher.getWriteClasses())
        self.readFactory = LoadFactory(False,*readClasses.values())
        self.loadFactory = LoadFactory(True,*writeClasses.values())
        #--Merge Factory
        self.mergeFactory = LoadFactory(False,*PatchFile.mergeClasses)

    def scanLoadMods(self,progress):
        """Scans load+merge mods."""
        if not len(self.loadMods): return
        nullProgress = bolt.Progress()
        progress = progress.setFull(len(self.allMods))
        for index,modName in enumerate(self.allMods):
            if modName in self.loadMods and 'Filter' in modInfos[modName].getBashTags():
                self.unFilteredMods.append(modName)
            try:
                loadFactory = (self.readFactory,self.mergeFactory)[modName in self.mergeSet]
                progress(index,_("%s\nLoading...") % modName.s)
                modInfo = modInfos[GPath(modName)]
                modFile = ModFile(modInfo,loadFactory)
                modFile.load(True,SubProgress(progress,index,index+0.5))
            except ModError:
                self.loadErrorMods.append(modName)
                continue
            try:
                #--Error checks
                if 'WRLD' in modFile.tops and modFile.WRLD.orphansSkipped:
                    self.worldOrphanMods.append(modName)
                if 'SCPT' in modFile.tops and modName != 'Oblivion.esm':
                    gls = modFile.SCPT.getRecord(0x00025811)
                    if gls and gls.compiledSize == 4 and gls.lastIndex == 0:
                        self.compiledAllMods.append(modName)
                pstate = index+0.5
                bashTags = modFile.fileInfo.getBashTags()
                isMerged = modName in self.mergeSet
                doFilter = isMerged and 'Filter' in bashTags
                #--iiMod is a hack to support Item Interchange. Actual key used is InventOnly.
                iiMode = isMerged and bool(set(('InventOnly','IIM')) & bashTags)
                if isMerged:
                    progress(pstate,_("%s\nMerging...") % modName.s)
                    self.mergeModFile(modFile,nullProgress,doFilter,iiMode)
                else:
                    progress(pstate,_("%s\nScanning...") % modName.s)
                    self.scanModFile(modFile,nullProgress)
                for patcher in sorted(self.patchers,key=attrgetter('scanOrder')):
                    if iiMode and not patcher.iiMode: continue
                    progress(pstate,_("%s\n%s") % (modName.s,patcher.name))
                    patcher.scanModFile(modFile,nullProgress)#was modFile,nullProgress
                self.tes4.version = max(modFile.tes4.version, self.tes4.version)
            except:
                print _("MERGE/SCAN ERROR:"),modName.s
                raise
        progress(progress.full,_('Load mods scanned.'))

    def mergeModFile(self,modFile,progress,doFilter,iiMode):
        """Copies contents of modFile into self."""
        mergeIds = self.mergeIds
        loadSet = self.loadSet
        modFile.convertToLongFids()
        badForm = (GPath("Oblivion.esm"),0xA31D) #--DarkPCB record
        for blockType,block in modFile.tops.iteritems():
            iiSkipMerge = iiMode and blockType not in ('LVLC','LVLI','LVSP')
            #--Make sure block type is also in read and write factories
            if blockType not in self.loadFactory.recTypes:
                recClass = self.mergeFactory.type_class[blockType]
                self.readFactory.addClass(recClass)
                self.loadFactory.addClass(recClass)
            patchBlock = getattr(self,blockType)
            if not isinstance(patchBlock,MobObjects):
                raise BoltError(_("Merge unsupported for type: ")+blockType)
            filtered = []
            for record in block.getActiveRecords():
                if record.fid == badForm: continue
                #--Include this record?
                if not doFilter or record.fid[0] in loadSet:
                    filtered.append(record)
                    if doFilter: record.mergeFilter(loadSet)
                    if iiSkipMerge: continue
                    record = record.getTypeCopy()
                    patchBlock.setRecord(record)
                    mergeIds.add(record.fid)
            #--Filter records
            block.records = filtered
            block.indexRecords()

    def scanModFile(self,modFile,progress):
        """Scans file and overwrites own records with modfile records."""
        #--Keep all MGEFs
        modFile.convertToLongFids('MGEF')
        if 'MGEF' in modFile.tops:
            for record in modFile.MGEF.getActiveRecords():
                self.MGEF.setRecord(record.getTypeCopy())
        #--Merger, override.
        mergeIds = self.mergeIds
        mapper = modFile.getLongMapper()
        for blockType,block in self.tops.iteritems():
            if blockType in modFile.tops:
                block.updateRecords(modFile.tops[blockType],mapper,mergeIds)

    def buildPatch(self,log,progress):
        """Completes merge process. Use this when finished using scanLoadMods."""
        if not len(self.patchers): return
        log.setHeader('= '+self.fileInfo.name.s+' '+'='*30+'#',True)
        log("{{CONTENTS=1}}")
        #--Load Mods and error mods
        log.setHeader(_("= Overview"),True)
        log.setHeader(_("=== Date/Time"))
        log('* '+formatDate(time.time()))
        if self.unFilteredMods:
            log.setHeader(_("=== Unfiltered Mods"))
            log(_("The following mods were active when the patch was built. For the mods to work properly, you should deactivate the mods and then rebuild the patch with the mods [[http://wrye.ufrealms.net/Wrye%20Bash.html#MergeFiltering|Merged]] in."))
            for mod in self.unFilteredMods: log ('* '+mod.s)
        if self.loadErrorMods:
            log.setHeader(_("=== Load Error Mods"))
            log(_("The following mods had load errors and were skipped while building the patch. Most likely this problem is due to a badly formatted mod. For more info, see [[http://www.uesp.net/wiki/Tes4Mod:Wrye_Bash/Bashed_Patch#Error_Messages|Bashed Patch: Error Messages]]."))
            for mod in self.loadErrorMods: log ('* '+mod.s)
        if self.worldOrphanMods:
            log.setHeader(_("=== World Orphans"))
            log(_("The following mods had orphaned world groups, which were skipped. This is not a major problem, but you might want to use Bash's [[http://wrye.ufrealms.net/Wrye%20Bash.html#RemoveWorldOrphans|Remove World Orphans]] command to repair the mods."))
            for mod in self.worldOrphanMods: log ('* '+mod.s)
        if self.compiledAllMods:
            log.setHeader(_("=== Compiled All"))
            log(_("The following mods have an empty compiled version of genericLoreScript. This is usually a sign that the mod author did a __compile all__ while editing scripts. This may interfere with the behavior of other mods that intentionally modify scripts from Oblivion.esm. (E.g. Cobl and Unofficial Oblivion Patch.) You can use Bash's [[http://wrye.ufrealms.net/Wrye%20Bash.html#DecompileAll|Decompile All]] command to repair the mods."))
            for mod in self.compiledAllMods: log ('* '+mod.s)
        log.setHeader(_("=== Active Mods"),True)
        for name in self.allMods:
            version = modInfos.getVersion(name)
            if name in self.loadMods:
                message = '* %02X ' % (self.loadMods.index(name),)
            else:
                message = '* ++ '
            if version:
                message += _('%s  [Version %s]') % (name.s,version)
            else:
                message += name.s
            log(message)
        #--Load Mods and error mods
        if self.aliases:
            log.setHeader(_("= Mod Aliases"))
            for key,value in sorted(self.aliases.iteritems()):
                log('* %s >> %s' % (key.s,value.s))
        #--Patchers
        self.keepIds |= self.mergeIds
        subProgress = SubProgress(progress,0,0.9,len(self.patchers))
        for index,patcher in enumerate(sorted(self.patchers,key=attrgetter('editOrder'))):
            subProgress(index,_("Completing\n%s...") % (patcher.getName(),))
            patcher.buildPatch(log,SubProgress(subProgress,index))
        #--Trim records
        progress(0.9,_("Completing\nTrimming records..."))
        for block in self.tops.values():
            block.keepRecords(self.keepIds)
        progress(0.95,_("Completing\nConverting fids..."))
        #--Convert masters to short fids
        self.tes4.masters = self.getMastersUsed()
        self.convertToShortFids()
        progress(1.0,"Compiled.")
        #--Description
        numRecords = sum([x.getNumRecords(False) for x in self.tops.values()])
        self.tes4.description = _("Updated: %s\n\nRecords Changed: %d") % (formatDate(time.time()),numRecords)

#------------------------------------------------------------------------------
class Patcher:
    """Abstract base class for patcher elements."""
    scanOrder = 10
    editOrder = 10
    group = 'UNDEFINED'
    name = 'UNDEFINED'
    text = "UNDEFINED."
    tip = None
    defaultConfig = {'isEnabled':False}
    iiMode = False

    def getName(self):
        """Returns patcher name."""
        return self.__class__.name

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        """Initialization of common values to defaults."""
        self.patchFile = None
        self.scanOrder = self.__class__.scanOrder
        self.editOrder = self.__class__.editOrder
        self.isActive = True
        #--Gui stuff
        self.isEnabled = False #--Patcher is enabled.
        self.gConfigPanel = None

    def getConfig(self,configs):
        """Get config from configs dictionary and/or set to default."""
        config = configs.setdefault(self.__class__.__name__,{})
        for attr,default in self.__class__.defaultConfig.iteritems():
            value = copy.deepcopy(config.get(attr,default))
            setattr(self,attr,value)

    def saveConfig(self,configs):
        """Save config to configs dictionary."""
        config = configs[self.__class__.__name__] = {}
        for attr in self.__class__.defaultConfig:
            config[attr] = copy.deepcopy(getattr(self,attr))

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        self.patchFile = patchFile

    def initData(self,progress):
        """Compiles material, i.e. reads source text, esp's, etc. as necessary."""
        pass

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return None

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return None

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it. If adds record, should first convert it to long fids."""
        pass

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Should write to log."""
        pass

#------------------------------------------------------------------------------
class ListPatcher(Patcher):
    """Subclass for patchers that have GUI lists of objects."""
    #--Get/Save Config
    choiceMenu = None #--List of possible choices for each config item. Item 0 is default.
    defaultConfig = {'isEnabled':False,'autoIsChecked':True,'configItems':[],'configChecks':{},'configChoices':{}}
    defaultItemCheck = True #--GUI: Whether new items are checked by default or not.
    forceItemCheck = False #--Force configChecked to True for all items
    autoRe = re.compile('^UNDEFINED$') #--Compiled re used by getAutoItems
    autoKey = None
    forceAuto = True

    #--Config Phase -----------------------------------------------------------
    def getAutoItems(self):
        """Returns list of items to be used for automatic configuration."""
        autoItems = []
        autoRe = self.__class__.autoRe
        autoKey = self.__class__.autoKey
        if isinstance(autoKey,str):
            autoKey = set((autoKey,))
        autoKey = set(autoKey)
        self.choiceMenu = self.__class__.choiceMenu
        for modInfo in modInfos.data.values():
            if autoRe.match(modInfo.name.s) or (autoKey & modInfo.getBashTags()):
                autoItems.append(modInfo.name)
                if self.choiceMenu: self.getChoice(modInfo.name)
        reFile = re.compile('_('+('|'.join(autoKey))+r')\.csv$')
        for fileName in sorted(dirs['patches'].list()):
            if reFile.search(fileName.s):
                autoItems.append(fileName)
        return autoItems

    def getConfig(self,configs):
        """Get config from configs dictionary and/or set to default."""
        Patcher.getConfig(self,configs)
        if self.forceAuto:
            self.autoIsChecked = True
        #--Verify file existence
        newConfigItems = []
        patchesDir = dirs['patches'].list()
        for srcPath in self.configItems:
            if ((reModExt.search(srcPath.s) and srcPath in modInfos) or
                reCsvExt.search(srcPath.s) and srcPath in patchesDir):
                    newConfigItems.append(srcPath)
        self.configItems = newConfigItems
        if self.__class__.forceItemCheck:
            for item in self.configItems:
                self.configChecks[item] = True
        #--Make sure configChoices are set (if choiceMenu exists).
        if self.choiceMenu:
            for item in self.configItems:
                self.getChoice(item)
        #--AutoItems?
        if self.autoIsChecked:
            self.getAutoItems()

    def getChoice(self,item):
        """Get default config choice."""
        return self.configChoices.setdefault(item,self.choiceMenu[0])

    def getItemLabel(self,item):
        """Returns label for item to be used in list"""
        if isinstance(item,bolt.Path): item = item.s
        if self.choiceMenu:
            return '%s [%s]' % (item,self.getChoice(item))
        else:
            return item

    def sortConfig(self,items):
        """Return sorted items. Default assumes mods and sorts by load order."""
        return modInfos.getOrdered(items,False)

    def saveConfig(self,configs):
        """Save config to configs dictionary."""
        #--Toss outdated configCheck data.
        listSet = set(self.configItems)
        self.configChecks = dict([(key,value) for key,value in self.configChecks.iteritems() if key in listSet])
        self.configChoices = dict([(key,value) for key,value in self.configChoices.iteritems() if key in listSet])
        Patcher.saveConfig(self,configs)

    #--Patch Phase ------------------------------------------------------------
    def getConfigChecked(self):
        """Returns checked config items in list order."""
        return [item for item in self.configItems if self.configChecks[item]]

#------------------------------------------------------------------------------
class MultiTweakItem:
    """A tweak item, optionally with configuration choices."""
    def __init__(self,label,tip,key,*choices):
        """Initialize."""
        self.label = label
        self.tip = tip
        self.key = key
        self.choiceLabels = []
        self.choiceValues = []
        for choice in choices:
            self.choiceLabels.append(choice[0])
            self.choiceValues.append(choice[1:])
        #--Config
        self.isEnabled = False
        self.chosen = 0

    #--Config Phase -----------------------------------------------------------
    def getConfig(self,configs):
        """Get config from configs dictionary and/or set to default."""
        self.isEnabled,self.chosen = False,0
        if self.key in configs:
            self.isEnabled,value = configs[self.key]
            if value in self.choiceValues:
                self.chosen = self.choiceValues.index(value)

    def getListLabel(self):
        """Returns label to be used in list"""
        label = self.label
        if len(self.choiceLabels) > 1:
            label += ' [' + self.choiceLabels[self.chosen] + ']'
        return label

    def saveConfig(self,configs):
        """Save config to configs dictionary."""
        if self.choiceValues: value = self.choiceValues[self.chosen]
        else: value = None
        configs[self.key] = self.isEnabled,value

#------------------------------------------------------------------------------
class MultiTweaker(Patcher):
    """Combines a number of sub-tweaks which can be individually enabled and
    configured through a choice menu."""
    group = _('Tweakers')
    scanOrder = 20
    editOrder = 20

    #--Config Phase -----------------------------------------------------------
    def getConfig(self,configs):
        """Get config from configs dictionary and/or set to default."""
        config = configs.setdefault(self.__class__.__name__,{})
        self.isEnabled = config.get('isEnabled',False)
        self.tweaks = copy.deepcopy(self.__class__.tweaks)
        for tweak in self.tweaks:
            tweak.getConfig(config)

    def saveConfig(self,configs):
        """Save config to configs dictionary."""
        config = configs[self.__class__.__name__] = {}
        config['isEnabled'] = self.isEnabled
        for tweak in self.tweaks:
            tweak.saveConfig(config)
        self.enabledTweaks = [tweak for tweak in self.tweaks if tweak.isEnabled]
        self.isActive = len(self.enabledTweaks) > 0

# Patchers: 10 ----------------------------------------------------------------
#------------------------------------------------------------------------------
class AliasesPatcher(Patcher):
    """Specify mod aliases for patch files."""
    scanOrder = 10
    editOrder = 10
    group = _('General')
    name = _("Alias Mod Names")
    text = _("Specify mod aliases for reading CSV source files.")
    tip = None
    defaultConfig = {'isEnabled':True,'aliases':{}}

    #--Config Phase -----------------------------------------------------------
    def getConfig(self,configs):
        """Get config from configs dictionary and/or set to default."""
        Patcher.getConfig(self,configs)
        #--Update old configs to use Paths instead of strings.
        self.aliases = dict(map(GPath,item) for item in self.aliases.iteritems())

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        if self.isEnabled:
            self.patchFile.aliases = self.aliases

#------------------------------------------------------------------------------
class PatchMerger(ListPatcher):
    """Merges specified patches into Bashed Patch."""
    scanOrder = 10
    editOrder = 10
    group = _('General')
    name = _('Merge Patches')
    text = _("Merge patch mods into Bashed Patch.")
    autoRe = re.compile(r"^UNDEFINED$",re.I)
    autoKey = 'Merge'
    defaultItemCheck = True #--GUI: Whether new items are checked by default or not.

    def getAutoItems(self):
        """Returns list of items to be used for automatic configuration."""
        autoItems = []
        for modInfo in modInfos.data.values():
            if modInfo.name in modInfos.mergeable and 'NoMerge' not in modInfo.getBashTags():
                autoItems.append(modInfo.name)
        return autoItems

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        #--WARNING: Since other patchers may rely on the following update during
        #  their initPatchFile section, it's important that PatchMerger first or near first.
        if self.isEnabled: #--Since other mods may rely on this
            patchFile.setMods(None,self.getConfigChecked())

# Patchers: 20 ----------------------------------------------------------------
#------------------------------------------------------------------------------
class ImportPatcher(ListPatcher):
    """Subclass for patchers in group Importer."""
    group = _('Importers')
    scanOrder = 20
    editOrder = 20

    def saveConfig(self,configs):
        """Save config to configs dictionary."""
        ListPatcher.saveConfig(self,configs)
        if self.isEnabled:
            importedMods = [item for item,value in self.configChecks.iteritems() if value and reModExt.search(item.s)]
            configs['ImportedMods'].update(importedMods)

#------------------------------------------------------------------------------
class CellImporter(ImportPatcher):
    """Merges changes to cells (climate, lighting, and water.)"""
    name = _('Import Cells')
    text = _("Import cells (climate, lighting, and water) from source mods.")
    tip = text
    autoRe = re.compile(r"^UNDEFINED$",re.I)
    autoKey = ('C.Climate','C.Light','C.Water','C.Owner')
    defaultItemCheck = False #--GUI: Whether new items are checked by default or not.

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.cellData = {}
        self.sourceMods = self.getConfigChecked()
        self.isActive = bool(self.sourceMods)
        self.recAttrs = {
            'C.Climate': ('climate',),
            'C.Owner': ('ownership',),
            'C.Water': ('water','waterHeight'),
            'C.Light': ('ambientRed','ambientGreen','ambientBlue','unused1',
            'directionalRed','directionalGreen','directionalBlue','unused2',
            'fogRed','fogGreen','fogBlue','unused3',
            'fogNear','fogFar','directionalXY','directionalZ',
            'directionalFade','fogClip'),
            }
        self.recFlags = {
            'C.Climate': 'behaveLikeExterior',
            'C.Owner': 'publicPlace',
            'C.Water': 'hasWater',
            'C.Light': '',
            }

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (None,(MreCell,MreWrld))[self.isActive]

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (None,(MreCell,MreWrld))[self.isActive]

    def initData(self,progress):
        """Get cells from source files."""
        if not self.isActive: return
        def importCellBlockData(cellBlock):
            if not cellBlock.cell.flags1.ignored:
                fid = cellBlock.cell.fid
                if fid not in cellData:
                    cellData[fid] = {}
                    cellData[fid+('flags',)] = {}
                for attr in attrs:
                    cellData[fid][attr] = cellBlock.cell.__getattribute__(attr)
                for flag in flags:
                    cellData[fid+('flags',)][flag] = cellBlock.cell.flags.__getattr__(flag)
        cellData = self.cellData
        loadFactory = LoadFactory(False,MreCell,MreWrld)
        progress.setFull(len(self.sourceMods))
        for srcMod in self.sourceMods:
            if srcMod not in modInfos: continue
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            srcFile.convertToLongFids(('CELL','WRLD'))
            attrs = set(reduce(operator.add, (self.recAttrs[bashKey] for bashKey in srcInfo.getBashTags() if bashKey in self.recAttrs)))
            flags = tuple(self.recFlags[bashKey] for bashKey in srcInfo.getBashTags() if
                bashKey in self.recAttrs and self.recFlags[bashKey] != '')
            if 'CELL' in srcFile.tops:
                for cellBlock in srcFile.CELL.cellBlocks:
                    importCellBlockData(cellBlock)
            if 'WRLD' in srcFile.tops:
                for worldBlock in srcFile.WRLD.worldBlocks:
                    for cellBlock in worldBlock.cellBlocks:
                        importCellBlockData(cellBlock)
            progress.plus()

    def scanModFile(self, modFile, progress):
        """Add lists from modFile."""
        modName = modFile.fileInfo.name
        if not self.isActive or ('CELL' not in modFile.tops and 'WRLD' not in modFile.tops):
            return
        cellData = self.cellData
        patchCells = self.patchFile.CELL
        patchWorlds = self.patchFile.WRLD
        modFile.convertToLongFids(('CELL','WRLD'))
        if 'CELL' in modFile.tops:
            for cellBlock in modFile.CELL.cellBlocks:
                if cellBlock.cell.fid in cellData:
                    patchCells.setCell(cellBlock.cell)
        if 'WRLD' in modFile.tops:
            for worldBlock in modFile.WRLD.worldBlocks:
                for cellBlock in worldBlock.cellBlocks:
                    if cellBlock.cell.fid in cellData:
                        patchWorlds.setWorld(worldBlock.world)
                        patchWorlds.id_worldBlocks[worldBlock.world.fid].setCell(
                            cellBlock.cell)

    def buildPatch(self,log,progress):
        """Adds merged lists to patchfile."""
        def handleCellBlock(cellBlock):
            modified=False
            for attr,value in cellData[cellBlock.cell.fid].iteritems():
                if cellBlock.cell.__getattribute__(attr) != value:
                    cellBlock.cell.__setattr__(attr,value)
                    modified=True
            for flag,value in cellData[cellBlock.cell.fid+('flags',)].iteritems():
                if cellBlock.cell.flags.__getattr__(flag) != value:
                    cellBlock.cell.flags.__setattr__(flag,value)
                    modified=True
            if modified:
                cellBlock.cell.setChanged()
                keep(cellBlock.cell.fid)
            return modified

        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        cellData,count = self.cellData, CountDict()
        for cellBlock in self.patchFile.CELL.cellBlocks:
            if cellBlock.cell.fid in cellData and handleCellBlock(cellBlock):
                count.increment(cellBlock.cell.fid[0])
        for worldBlock in self.patchFile.WRLD.worldBlocks:
            keepWorld = False
            for cellBlock in worldBlock.cellBlocks:
                if cellBlock.cell.fid in cellData and handleCellBlock(cellBlock):
                    count.increment(cellBlock.cell.fid[0])
                    keepWorld = True
            if keepWorld:
                keep(worldBlock.world.fid)

        log.setHeader('= '+self.__class__.name)
        log(_("=== Source Mods"))
        for mod in self.sourceMods:
            log("* " +mod.s)
        log(_("\n=== Cells Patched"))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('* %s: %d' % (srcMod.s,count[srcMod]))

#------------------------------------------------------------------------------
class MapImporter(ImportPatcher):
    """Merges changes to cells (climate, lighting, and water.)"""
    name = _('Import World Maps')
    text = _("Import cells (climate, lighting, and water) from source mods.")
    tip = text
    autoRe = re.compile(r"^UNDEFINED$",re.I)
    autoKey = ('W.Maps',)
    defaultItemCheck = False #--GUI: Whether new items are checked by default or not.

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.cellData = {}
        self.sourceMods = self.getConfigChecked()
        self.isActive = bool(self.sourceMods)
        self.recAttrs = {
            'W.Maps': ('mapPath',),
            }
        self.recFlags = {
            'W.Maps': '',
            }

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (None,(MreWrld,))[self.isActive]

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (None,(MreWrld,))[self.isActive]

    def initData(self,progress):
        """Get cells from source files."""
        loadFactory = LoadFactory(False,MreWrld)
        progress.setFull(len(self.sourceMods))
        for srcMod in self.sourceMods:
            if srcMod not in modInfos: continue
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            srcFile.convertToLongFids(('WRLD',))
            attrs = set(reduce(operator.add, (self.recAttrs[bashKey] for bashKey in srcInfo.getBashTags() if bashKey in self.recAttrs)))
            flags = tuple(self.recFlags[bashKey] for bashKey in srcInfo.getBashTags() if
                bashKey in self.recAttrs and self.recFlags[bashKey] != '')
            if 'WRLD' in srcFile.tops:
                for worldBlock in srcFile.WRLD.worldBlocks:
                    progress.plus()

    def scanModFile(self, modFile, progress):
        """Add lists from modFile."""
        modName = modFile.fileInfo.name
        if not self.isActive or ('WRLD' not in modFile.tops):
            return
        patchWorlds = self.patchFile.WRLD
        modFile.convertToLongFids(('WRLD',))
        if 'WRLD' in modFile.tops:
            for worldBlock in modFile.WRLD.worldBlocks:
                patchWorlds.setWorld(worldBlock.world)
                
    def buildPatch(self,log,progress):
        """Adds merged lists to patchfile."""
        if not self.isActive: return
        for srcWorldBlock in srcBlock.worldBlocks:
            worldBlock = idGet(mapper(srcWorldBlock.world.fid))
            if worldBlock:
                worldBlock.updateRecords(srcWorldBlock,mapper,mergeIds)
        log.setHeader('= '+self.__class__.name)
        log(_("=== Source Mods"))
        for mod in self.sourceMods:
            log("* " +mod.s)
        log(_("\n=== Worlds Patched"))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('* %s: %d' % (srcMod.s,count[srcMod]))

#------------------------------------------------------------------------------
class GraphicsPatcher(ImportPatcher):
    """Merges changes to graphics (models and icons)."""
    name = _('Import Graphics')
    text = _("Import graphics (models, icons, etc.) from source mods.")
    tip = text
    autoRe = re.compile(r"^UNDEFINED$",re.I)
    autoKey = 'Graphics'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_data = {} #--Names keyed by long fid.
        self.srcClasses = set() #--Record classes actually provided by src mods/files.
        self.sourceMods = self.getConfigChecked()
        self.isActive = len(self.sourceMods) != 0
        #--Type Fields
        recAttrs_class = self.recAttrs_class = {}
        for recClass in (MreBsgn,MreLscr, MreClas, MreLtex, MreRegn):
            recAttrs_class[recClass] = ('iconPath',)
        for recClass in (MreActi, MreDoor, MreFlor, MreFurn, MreGras, MreStat):
            recAttrs_class[recClass] = ('model',)
        for recClass in (MreAlch, MreAmmo, MreAppa, MreBook, MreIngr, MreKeym, MreLigh, MreMisc, MreSgst, MreSlgm, MreWeap, MreTree):
            recAttrs_class[recClass] = ('iconPath','model')
        for recClass in (MreArmo, MreClot):
            recAttrs_class[recClass] = ('maleBody','maleWorld','maleIconPath','femaleBody','femaleWorld','femaleIconPath','flags')
        for recClass in (MreCrea,):
            recAttrs_class[recClass] = ('model','bodyParts','nift_p','bloodSprayPath','bloodDecalPath')
        for recClass in (MreMgef,):
            recAttrs_class[recClass] = ('iconPath','model','effectShader','enchantEffect','light')
        for recClass in (MreEfsh,):
            recAttrs_class[recClass] = ('particleTexture','fillTexture')
        #--Needs Longs
        self.longTypes = set(('BSGN','LSCR','CLAS','LTEX','REGN','ACTI','DOOR','FLOR','FURN','GRAS','STAT','ALCH','AMMO','BOOK','INGR','KEYM','LIGH','MISC','SGST','SLGM','WEAP','TREE','ARMO','CLOT','CREA','MGEF','EFSH'))

    def initData(self,progress):
        """Get graphics from source files."""
        if not self.isActive: return
        id_data = self.id_data
        recAttrs_class = self.recAttrs_class
        loadFactory = LoadFactory(False,*recAttrs_class.keys())
        longTypes = self.longTypes & set(x.classType for x in self.recAttrs_class)
        progress.setFull(len(self.sourceMods))
        for index,srcMod in enumerate(self.sourceMods):
            if srcMod not in modInfos: continue
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass,recAttrs in recAttrs_class.iteritems():
                if recClass.classType not in srcFile.tops: continue
                self.srcClasses.add(recClass)
                for record in srcFile.tops[recClass.classType].getActiveRecords():
                    fid = mapper(record.fid)
                    id_data[fid] = dict((attr,record.__getattribute__(attr)) for attr in recAttrs)
            progress.plus()
        self.longTypes = self.longTypes & set(x.classType for x in self.srcClasses)
        self.isActive = bool(self.srcClasses)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return None
        return self.srcClasses

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return None
        return self.srcClasses

    def scanModFile(self, modFile, progress):
        """Scan mod file against source data."""
        if not self.isActive: return
        id_data = self.id_data
        modName = modFile.fileInfo.name
        mapper = modFile.getLongMapper()
        if self.longTypes:
            modFile.convertToLongFids(self.longTypes)
        for recClass in self.srcClasses:
            type = recClass.classType
            if type not in modFile.tops: continue
            patchBlock = getattr(self.patchFile,type)
            for record in modFile.tops[type].getActiveRecords():
                fid = record.fid
                if not record.longFids: fid = mapper(fid)
                if fid not in id_data: continue
                for attr,value in id_data[fid].iteritems():
                    if record.__getattribute__(attr) != value:
                        patchBlock.setRecord(record.getTypeCopy(mapper))
                        break

    def buildPatch(self,log,progress):
        """Merge last version of record with patched graphics data as needed."""
        if not self.isActive: return
        modFile = self.patchFile
        keep = self.patchFile.getKeeper()
        id_data = self.id_data
        type_count = {}
        for recClass in self.srcClasses:
            type = recClass.classType
            if type not in modFile.tops: continue
            type_count[type] = 0
            #deprint(recClass,type,type_count[type])
            for record in modFile.tops[type].records:
                fid = record.fid
                if fid not in id_data: continue
                for attr,value in id_data[fid].iteritems():
                    if record.__getattribute__(attr) != value:
                        break
                else:
                    continue
                for attr,value in id_data[fid].iteritems():
                    record.__setattr__(attr,value)
                keep(fid)
                type_count[type] += 1
        log.setHeader('= '+self.__class__.name)
        log(_("=== Source Mods"))
        for mod in self.sourceMods:
            log("* " +mod.s)
        log(_("\n=== Modified Records"))
        for type,count in sorted(type_count.items()):
            if count: log("* %s: %d" % (type,count))

#------------------------------------------------------------------------------
class KFFZPatcher(ImportPatcher):
    """Merges changes to graphics (models and icons)."""
    name = _('Import Actors: Animations')
    text = _("Import Actor animations from source mods.")
    tip = text
    autoRe = re.compile(r"^UNDEFINED$",re.I)
    autoKey = 'Actors.Anims'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_data = {} #--Names keyed by long fid.
        self.srcClasses = set() #--Record classes actually provided by src mods/files.
        self.sourceMods = self.getConfigChecked()
        self.isActive = len(self.sourceMods) != 0
        #--Type Fields
        recAttrs_class = self.recAttrs_class = {}
        for recClass in (MreCrea,MreNpc):
            recAttrs_class[recClass] = ('animations',)
        #--Needs Longs
        self.longTypes = set(('CREA','NPC_'))

    def initData(self,progress):
        """Get graphics from source files."""
        if not self.isActive: return
        id_data = self.id_data
        recAttrs_class = self.recAttrs_class
        loadFactory = LoadFactory(False,*recAttrs_class.keys())
        longTypes = self.longTypes & set(x.classType for x in self.recAttrs_class)
        progress.setFull(len(self.sourceMods))
        for index,srcMod in enumerate(self.sourceMods):
            if srcMod not in modInfos: continue
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass,recAttrs in recAttrs_class.iteritems():
                if recClass.classType not in srcFile.tops: continue
                self.srcClasses.add(recClass)
                for record in srcFile.tops[recClass.classType].getActiveRecords():
                    fid = mapper(record.fid)
                    id_data[fid] = dict((attr,record.__getattribute__(attr)) for attr in recAttrs)
            progress.plus()
        self.longTypes = self.longTypes & set(x.classType for x in self.srcClasses)
        self.isActive = bool(self.srcClasses)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return None
        return self.srcClasses

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return None
        return self.srcClasses

    def scanModFile(self, modFile, progress):
        """Scan mod file against source data."""
        if not self.isActive: return
        id_data = self.id_data
        modName = modFile.fileInfo.name
        mapper = modFile.getLongMapper()
        if self.longTypes:
            modFile.convertToLongFids(self.longTypes)
        for recClass in self.srcClasses:
            type = recClass.classType
            if type not in modFile.tops: continue
            patchBlock = getattr(self.patchFile,type)
            for record in modFile.tops[type].getActiveRecords():
                fid = record.fid
                if not record.longFids: fid = mapper(fid)
                if fid not in id_data: continue
                for attr,value in id_data[fid].iteritems():
                    if record.__getattribute__(attr) != value:
                        patchBlock.setRecord(record.getTypeCopy(mapper))
                        break

    def buildPatch(self,log,progress):
        """Merge last version of record with patched graphics data as needed."""
        if not self.isActive: return
        modFile = self.patchFile
        keep = self.patchFile.getKeeper()
        id_data = self.id_data
        type_count = {}
        for recClass in self.srcClasses:
            type = recClass.classType
            if type not in modFile.tops: continue
            type_count[type] = 0
            #deprint(recClass,type,type_count[type])
            for record in modFile.tops[type].records:
                fid = record.fid
                if fid not in id_data: continue
                for attr,value in id_data[fid].iteritems():
                    if record.__getattribute__(attr) != value:
                        break
                else:
                    continue
                for attr,value in id_data[fid].iteritems():
                    record.__setattr__(attr,value)
                keep(fid)
                type_count[type] += 1
        log.setHeader('= '+self.__class__.name)
        log(_("=== Source Mods"))
        for mod in self.sourceMods:
            log("* " +mod.s)
        log(_("\n=== Modified Records"))
        for type,count in sorted(type_count.items()):
            if count: log("* %s: %d" % (type,count))

#------------------------------------------------------------------------------
class DeathItemPatcher(ImportPatcher):
    """Merges changes to graphics (models and icons)."""
    name = _('Import Actors: Death Items')
    text = _("Import Actor death items from source mods.")
    tip = text
    autoRe = re.compile(r"^UNDEFINED$",re.I)
    autoKey = 'Actors.DeathItem'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_data = {} #--Names keyed by long fid.
        self.srcClasses = set() #--Record classes actually provided by src mods/files.
        self.sourceMods = self.getConfigChecked()
        self.isActive = len(self.sourceMods) != 0
        #--Type Fields
        recAttrs_class = self.recAttrs_class = {}
        for recClass in (MreCrea,MreNpc):
            recAttrs_class[recClass] = ('deathItem',)
        #--Needs Longs
        self.longTypes = set(('CREA','NPC_'))

    def initData(self,progress):
        """Get graphics from source files."""
        if not self.isActive: return
        id_data = self.id_data
        recAttrs_class = self.recAttrs_class
        loadFactory = LoadFactory(False,*recAttrs_class.keys())
        longTypes = self.longTypes & set(x.classType for x in self.recAttrs_class)
        progress.setFull(len(self.sourceMods))
        for index,srcMod in enumerate(self.sourceMods):
            if srcMod not in modInfos: continue
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass,recAttrs in recAttrs_class.iteritems():
                if recClass.classType not in srcFile.tops: continue
                self.srcClasses.add(recClass)
                for record in srcFile.tops[recClass.classType].getActiveRecords():
                    fid = mapper(record.fid)
                    id_data[fid] = dict((attr,record.__getattribute__(attr)) for attr in recAttrs)
            progress.plus()
        self.longTypes = self.longTypes & set(x.classType for x in self.srcClasses)
        self.isActive = bool(self.srcClasses)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return None
        return self.srcClasses

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return None
        return self.srcClasses

    def scanModFile(self, modFile, progress):
        """Scan mod file against source data."""
        if not self.isActive: return
        id_data = self.id_data
        modName = modFile.fileInfo.name
        mapper = modFile.getLongMapper()
        if self.longTypes:
            modFile.convertToLongFids(self.longTypes)
        for recClass in self.srcClasses:
            type = recClass.classType
            if type not in modFile.tops: continue
            patchBlock = getattr(self.patchFile,type)
            for record in modFile.tops[type].getActiveRecords():
                fid = record.fid
                if not record.longFids: fid = mapper(fid)
                if fid not in id_data: continue
                for attr,value in id_data[fid].iteritems():
                    if record.__getattribute__(attr) != value:
                        patchBlock.setRecord(record.getTypeCopy(mapper))
                        break

    def buildPatch(self,log,progress):
        """Merge last version of record with patched graphics data as needed."""
        if not self.isActive: return
        modFile = self.patchFile
        keep = self.patchFile.getKeeper()
        id_data = self.id_data
        type_count = {}
        for recClass in self.srcClasses:
            type = recClass.classType
            if type not in modFile.tops: continue
            type_count[type] = 0
            #deprint(recClass,type,type_count[type])
            for record in modFile.tops[type].records:
                fid = record.fid
                if fid not in id_data: continue
                for attr,value in id_data[fid].iteritems():
                    if record.__getattribute__(attr) != value:
                        break
                else:
                    continue
                for attr,value in id_data[fid].iteritems():
                    record.__setattr__(attr,value)
                keep(fid)
                type_count[type] += 1
        log.setHeader('= '+self.__class__.name)
        log(_("=== Source Mods"))
        for mod in self.sourceMods:
            log("* " +mod.s)
        log(_("\n=== Modified Records"))
        for type,count in sorted(type_count.items()):
            if count: log("* %s: %d" % (type,count))

#------------------------------------------------------------------------------
class ImportFactions(ImportPatcher):
    """Import factions to creatures and NPCs."""
    name = _('Import Factions')
    text = _("Import factions from source mods/files.")
    defaultItemCheck = False #--GUI: Whether new items are checked by default or not.
    autoKey = 'Factions'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_factions= {} #--Factions keyed by long fid.
        self.activeTypes = [] #--Types ('CREA','NPC_') of data actually provided by src mods/files.
        self.srcFiles = self.getConfigChecked()
        self.isActive = bool(self.srcFiles)

    def initData(self,progress):
        """Get names from source files."""
        if not self.isActive: return
        actorFactions = ActorFactions(aliases=self.patchFile.aliases)
        progress.setFull(len(self.srcFiles))
        for srcFile in self.srcFiles:
            srcPath = GPath(srcFile)
            patchesDir = dirs['patches'].list()
            if reModExt.search(srcFile.s):
                if srcPath not in modInfos: continue
                srcInfo = modInfos[GPath(srcFile)]
                actorFactions.readFromMod(srcInfo)
            else:
                if srcPath not in patchesDir: continue
                actorFactions.readFromText(dirs['patches'].join(srcFile))
            progress.plus()
        #--Finish
        id_factions= self.id_factions
        for type,aFid_factions in actorFactions.type_id_factions.items():
            if type not in ('CREA','NPC_'): continue
            self.activeTypes.append(type)
            for longid,factions in aFid_factions.items():
                self.id_factions[longid] = factions
        self.isActive = bool(self.activeTypes)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return None
        return self.activeTypes

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return None
        return [MreRecord.type_class[type] for type in self.activeTypes]

    def scanModFile(self, modFile, progress):
        """Scan modFile."""
        if not self.isActive: return
        id_factions= self.id_factions
        modName = modFile.fileInfo.name
        mapper = modFile.getLongMapper()
        for type in self.activeTypes:
            if type not in modFile.tops: continue
            patchBlock = getattr(self.patchFile,type)
            id_records = patchBlock.id_records
            for record in modFile.tops[type].getActiveRecords():
                fid = record.fid
                if not record.longFids: fid = mapper(fid)
                if fid in id_records: continue
                if fid not in id_factions: continue
                patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress):
        """Make changes to patchfile."""
        if not self.isActive: return
        modFile = self.patchFile
        keep = self.patchFile.getKeeper()
        id_factions= self.id_factions
        type_count = {}
        for type in self.activeTypes:
            if type not in modFile.tops: continue
            type_count[type] = 0
            for record in modFile.tops[type].records:
                fid = record.fid
                if fid in id_factions:
                    newFactions = set(id_factions[fid])
                    curFactions = set((x.faction,x.rank) for x in record.factions)
                    changed = newFactions - curFactions
                    if not changed: continue
                    doKeep = False
                    for faction,rank in changed:
                        for entry in record.factions:
                            if entry.faction == faction:
                                if entry.rank != rank:
                                    entry.rank = rank
                                    doKeep = True
                                    keep(fid)
                                break
                        else:
                            entry = MelObject()
                            entry.faction = faction
                            entry.rank = rank
                            entry.unused1 = 'ODB'
                            record.factions.append(entry)
                            doKeep = True
                    if doKeep:
                        record.factions = [x for x in record.factions if x.rank != -1]
                        type_count[type] += 1
                        keep(fid)
        log.setHeader('= '+self.__class__.name)
        log(_("=== Source Mods/Files"))
        for file in self.srcFiles:
            log("* " +file.s)
        log(_("\n=== Refactioned Actors"))
        for type,count in sorted(type_count.items()):
            if count: log("* %s: %d" % (type,count))

#------------------------------------------------------------------------------
class ImportRelations(ImportPatcher):
    """Import faction relations to factions."""
    name = _('Import Relations')
    text = _("Import relations from source mods/files.")
    defaultItemCheck = False #--GUI: Whether new items are checked by default or not.
    autoKey = 'Relations'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_relations= {} #--[(otherLongid0,disp0),(...)] = id_relations[mainLongid].
        self.srcFiles = self.getConfigChecked()
        self.isActive = bool(self.srcFiles)

    def initData(self,progress):
        """Get names from source files."""
        if not self.isActive: return
        factionRelations = FactionRelations(aliases=self.patchFile.aliases)
        progress.setFull(len(self.srcFiles))
        for srcFile in self.srcFiles:
            srcPath = GPath(srcFile)
            patchesDir = dirs['patches'].list()
            if reModExt.search(srcFile.s):
                if srcPath not in modInfos: continue
                srcInfo = modInfos[GPath(srcFile)]
                factionRelations.readFromMod(srcInfo)
            else:
                if srcPath not in patchesDir: continue
                factionRelations.readFromText(dirs['patches'].join(srcFile))
            progress.plus()
        #--Finish
        self.id_relations = factionRelations.id_relations
        self.isActive = bool(self.id_relations)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (None,(MreFact,))[self.isActive]

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (None,(MreFact,))[self.isActive]

    def scanModFile(self, modFile, progress):
        """Scan modFile."""
        if not self.isActive: return
        id_relations= self.id_relations
        modName = modFile.fileInfo.name
        mapper = modFile.getLongMapper()
        for type in ('FACT',):
            if type not in modFile.tops: continue
            patchBlock = getattr(self.patchFile,type)
            id_records = patchBlock.id_records
            for record in modFile.tops[type].getActiveRecords():
                fid = record.fid
                if not record.longFids: fid = mapper(fid)
                if fid in id_records: continue
                if fid not in id_relations: continue
                patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress):
        """Make changes to patchfile."""
        if not self.isActive: return
        modFile = self.patchFile
        keep = self.patchFile.getKeeper()
        id_relations= self.id_relations
        type_count = {}
        for type in ('FACT',):
            if type not in modFile.tops: continue
            type_count[type] = 0
            for record in modFile.tops[type].records:
                fid = record.fid
                if fid in id_relations:
                    newRelations = set(id_relations[fid])
                    curRelations = set((x.faction,x.mod) for x in record.relations)
                    changed = newRelations - curRelations
                    if not changed: continue
                    doKeep = False
                    for faction,disp in changed:
                        for entry in record.relations:
                            if entry.faction == faction:
                                if entry.mod != disp:
                                    entry.mod = disp
                                    doKeep = True
                                    keep(fid)
                                break
                        else:
                            entry = MelObject()
                            entry.faction = faction
                            entry.mod = disp
                            record.relations.append(entry)
                            doKeep = True
                    if doKeep:
                        type_count[type] += 1
                        keep(fid)
        log.setHeader('= '+self.__class__.name)
        log(_("=== Source Mods/Files"))
        for file in self.srcFiles:
            log("* " +file.s)
        log(_("\n=== Modified Factions: %d") % type_count['FACT'])

#------------------------------------------------------------------------------
class ImportScripts(ImportPatcher):
    """Imports attached scripts on objects."""
    name = _('Import Scripts')
    text = _("Import Scripts on containers, plants, misc, weapons etc. from source mods.")
    tip = text
    autoRe = re.compile(r"^UNDEFINED$",re.I)
    autoKey = 'Scripts'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_data = {} #--Names keyed by long fid.
        self.srcClasses = set() #--Record classes actually provided by src mods/files.
        self.sourceMods = self.getConfigChecked()
        self.isActive = len(self.sourceMods) != 0
        #--Type Fields
        recAttrs_class = self.recAttrs_class = {}
        for recClass in (MreWeap,MreActi,MreAlch,MreAppa,MreArmo,MreBook,MreClot,MreCont,MreCrea,MreDoor,MreFlor,MreFurn,MreIngr,MreKeym,MreLigh,MreMisc,MreNpc,MreQust,MreSgst,MreSlgm,):
            recAttrs_class[recClass] = ('script',)
        self.longTypes = set(('WEAP','ACTI','ALCH','APPA','ARMO','BOOK','CLOT','CONT','CREA','DOOR','FLOR','FURN','INGR','KEYM','LIGH','MISC','NPC_','QUST','SGST','SLGM'))

    def initData(self,progress):
        """Get graphics from source files."""
        if not self.isActive: return
        id_data = self.id_data
        recAttrs_class = self.recAttrs_class
        loadFactory = LoadFactory(False,*recAttrs_class.keys())
        longTypes = self.longTypes & set(x.classType for x in self.recAttrs_class)
        progress.setFull(len(self.sourceMods))
        for index,srcMod in enumerate(self.sourceMods):
            if srcMod not in modInfos: continue
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass,recAttrs in recAttrs_class.iteritems():
                if recClass.classType not in srcFile.tops: continue
                self.srcClasses.add(recClass)
                for record in srcFile.tops[recClass.classType].getActiveRecords():
                    fid = mapper(record.fid)
                    id_data[fid] = dict((attr,record.__getattribute__(attr)) for attr in recAttrs)
            progress.plus()
        self.longTypes = self.longTypes & set(x.classType for x in self.srcClasses)
        self.isActive = bool(self.srcClasses)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return None
        return self.srcClasses

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return None
        return self.srcClasses

    def scanModFile(self, modFile, progress):
        """Scan mod file against source data."""
        if not self.isActive: return
        id_data = self.id_data
        modName = modFile.fileInfo.name
        mapper = modFile.getLongMapper()
        if self.longTypes:
            modFile.convertToLongFids(self.longTypes)
        for recClass in self.srcClasses:
            type = recClass.classType
            if type not in modFile.tops: continue
            patchBlock = getattr(self.patchFile,type)
            for record in modFile.tops[type].getActiveRecords():
                fid = record.fid
                if not record.longFids: fid = mapper(fid)
                if fid not in id_data: continue
                for attr,value in id_data[fid].iteritems():
                    if record.__getattribute__(attr) != value:
                        patchBlock.setRecord(record.getTypeCopy(mapper))
                        break

    def buildPatch(self,log,progress):
        """Merge last version of record with patched graphics data as needed."""
        if not self.isActive: return
        modFile = self.patchFile
        keep = self.patchFile.getKeeper()
        id_data = self.id_data
        type_count = {}
        for recClass in self.srcClasses:
            type = recClass.classType
            if type not in modFile.tops: continue
            type_count[type] = 0
            #deprint(recClass,type,type_count[type])
            for record in modFile.tops[type].records:
                fid = record.fid
                if fid not in id_data: continue
                for attr,value in id_data[fid].iteritems():
                    if record.__getattribute__(attr) != value:
                        break
                else:
                    continue
                for attr,value in id_data[fid].iteritems():
                    record.__setattr__(attr,value)
                keep(fid)
                type_count[type] += 1
        log.setHeader('= '+self.__class__.name)
        log(_("=== Source Mods"))
        for mod in self.sourceMods:
            log("* " +mod.s)
        log(_("\n=== Modified Records"))
        for type,count in sorted(type_count.items()):
            if count: log("* %s: %d" % (type,count))
#------------------------------------------------------------------------------
class ImportScriptContents(ImportPatcher):
    """Imports the contents of scripts -- currently only object/mgef scripts."""
    name = _('Import Script Contents')
    text = _("Import the actual contents of scripts scripts.")
    tip = text
    autoRe = re.compile(r"^UNDEFINED$",re.I)
    autoKey = 'ScriptContents'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_data = {} #--Names keyed by long fid.
        self.srcClasses = set() #--Record classes actually provided by src mods/files.
        self.sourceMods = self.getConfigChecked()
        self.isActive = len(self.sourceMods) != 0
        #--Type Fields
        recAttrs_class = self.recAttrs_class = {}
        for recClass in (MreScpt,):
            recAttrs_class[recClass] = ('numRefs','lastIndex','compiledSize','scriptType','compiled_p','scriptText','vars','references',) # invalid attributes for plain script: SCHR, 4s4I,SCDA,'SLSD','I12sB7s','index', 'SCVR', 'name', 
#        for recClass in (MreInfo,):
 #           recAttrs_class[recClass] = ('SCHD','schd_p','SCHR','4s4I','numRefs','compiledsize','lastIndex','scriptType','SCDA','compiled_p','SCTX','scriptText','SCRV/SCRO','references',)
        for recClass in (MreQust,):
            recAttrs_class[recClass] = ('stages',)# 'SCHD','schd_p','SCHR','4s4I','numRefs','compiledsize','lastIndex','scriptType','SCDA','compiled_p','SCTX','scriptText','SCRV/SCRO','references',)          
        self.longTypes = set(('SCPT','QUST','DIAL','INFO'))
#        MelGroups('stages',
#            MelStruct('INDX','h','stage'),
#            MelGroups('entries',
#                MelStruct('QSDT','B',(stageFlags,'flags')),
#                MelConditions(),
#                MelString('CNAM','text'),
#                MelStruct('SCHR','4s4I',('unused1',null4),'numRefs','compiledSize','lastIndex','scriptType'),
#                MelBase('SCDA','compiled_p'),
#                MelString('SCTX','scriptText'),
#                MelScrxen('SCRV/SCRO','references')
#                ),

        
    def initData(self,progress):
        """Get graphics from source files."""
        if not self.isActive: return
        id_data = self.id_data
        recAttrs_class = self.recAttrs_class
        loadFactory = LoadFactory(False,*recAttrs_class.keys())
        longTypes = self.longTypes & set(x.classType for x in self.recAttrs_class)
        progress.setFull(len(self.sourceMods))
        for index,srcMod in enumerate(self.sourceMods):
            if srcMod not in modInfos: continue
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass,recAttrs in recAttrs_class.iteritems():
                if recClass.classType not in srcFile.tops: continue
                self.srcClasses.add(recClass)
                for record in srcFile.tops[recClass.classType].getActiveRecords():
                    fid = mapper(record.fid)
                    id_data[fid] = dict((attr,record.__getattribute__(attr)) for attr in recAttrs)
            progress.plus()
        self.longTypes = self.longTypes & set(x.classType for x in self.srcClasses)
        self.isActive = bool(self.srcClasses)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return None
        return self.srcClasses

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return None
        return self.srcClasses

    def scanModFile(self, modFile, progress):
        """Scan mod file against source data."""
        if not self.isActive: return
        id_data = self.id_data
        modName = modFile.fileInfo.name
        mapper = modFile.getLongMapper()
        if self.longTypes:
            modFile.convertToLongFids(self.longTypes)
        for recClass in self.srcClasses:
            type = recClass.classType
            if type not in modFile.tops: continue
            patchBlock = getattr(self.patchFile,type)
            for record in modFile.tops[type].getActiveRecords():
                fid = record.fid
                if not record.longFids: fid = mapper(fid)
                if fid not in id_data: continue
                for attr,value in id_data[fid].iteritems():
                    if record.__getattribute__(attr) != value:
                        patchBlock.setRecord(record.getTypeCopy(mapper))
                        break

    def buildPatch(self,log,progress):
        """Merge last version of record with patched graphics data as needed."""
        if not self.isActive: return
        modFile = self.patchFile
        keep = self.patchFile.getKeeper()
        id_data = self.id_data
        type_count = {}
        for recClass in self.srcClasses:
            type = recClass.classType
            if type not in modFile.tops: continue
            type_count[type] = 0
            #deprint(recClass,type,type_count[type])
            for record in modFile.tops[type].records:
                fid = record.fid
                if fid not in id_data: continue
                for attr,value in id_data[fid].iteritems():
                    if record.__getattribute__(attr) != value:
                        break
                else:
                    continue
                for attr,value in id_data[fid].iteritems():
                    record.__setattr__(attr,value)
                keep(fid)
                type_count[type] += 1
        log.setHeader('= '+self.__class__.name)
        log(_("=== Source Mods"))
        for mod in self.sourceMods:
            log("* " +mod.s)
        log(_("\n=== Modified Records"))
        for type,count in sorted(type_count.items()):
            if count: log("* %s: %d" % (type,count))
#------------------------------------------------------------------------------
class ImportInventory(ImportPatcher):
    """Merge changes to actor inventories."""
    name = _('Import Inventory')
    text = _("Merges changes to NPC, creature and container inventories.")
    autoKey = ('Invent','InventOnly')
    defaultItemCheck = False #--GUI: Whether new items are checked by default or not.
    iiMode = True

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_deltas = {}
        self.srcMods = self.getConfigChecked()
        self.srcMods = [x for x in self.srcMods if (x in modInfos and x in patchFile.allMods)]
        self.inventOnlyMods = set(x for x in self.srcMods if
            (x in patchFile.mergeSet and set(('InventOnly','IIM')) & modInfos[x].getBashTags()))
        self.isActive = bool(self.srcMods)
        self.masters = set()
        for srcMod in self.srcMods:
            self.masters |= set(modInfos[srcMod].header.masters)
        self.allMods = self.masters | set(self.srcMods)
        self.mod_id_entries = {}
        self.touched = set()

    def initData(self,progress):
        """Get data from source files."""
        if not self.isActive or not self.srcMods: return
        loadFactory = LoadFactory(False,'CREA','NPC_','CONT')
        progress.setFull(len(self.srcMods))
        for index,srcMod in enumerate(self.srcMods):
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            mapper = srcFile.getLongMapper()
            for block in (srcFile.CREA, srcFile.NPC_, srcFile.CONT):
                for record in block.getActiveRecords():
                    self.touched.add(mapper(record.fid))
            progress.plus()

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (None,(MreNpc,MreCrea,MreCont))[self.isActive]

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (None,(MreNpc,MreCrea,MreCont))[self.isActive]

    def scanModFile(self, modFile, progress):
        """Add record from modFile."""
        if not self.isActive: return
        touched = self.touched
        id_deltas = self.id_deltas
        mod_id_entries = self.mod_id_entries
        mapper = modFile.getLongMapper()
        modName = modFile.fileInfo.name
        #--Master or source?
        if modName in self.allMods:
            id_entries = mod_id_entries[modName] = {}
            modFile.convertToLongFids(('NPC_','CREA','CONT'))
            for type in ('NPC_','CREA','CONT'):
                for record in getattr(modFile,type).getActiveRecords():
                    if record.fid in touched:
                        id_entries[record.fid] = record.items[:]
        #--Source mod?
        if modName in self.srcMods:
            id_entries = {}
            for master in modFile.tes4.masters:
                if master in mod_id_entries:
                    id_entries.update(mod_id_entries[master])
            for fid,entries in mod_id_entries[modName].iteritems():
                masterEntries = id_entries.get(fid)
                if masterEntries is None: continue
                masterItems = set(x.item for x in masterEntries)
                modItems = set(x.item for x in entries)
                removeItems = masterItems - modItems
                addItems = modItems - masterItems
                addEntries = [x for x in entries if x.item in addItems]
                deltas = self.id_deltas.get(fid)
                if deltas is None: deltas = self.id_deltas[fid] = []
                deltas.append((removeItems,addEntries))
        #--Keep record?
        if modFile.fileInfo.name not in self.inventOnlyMods:
            for type in ('NPC_','CREA','CONT'):
                patchBlock = getattr(self.patchFile,type)
                id_records = patchBlock.id_records
                for record in getattr(modFile,type).getActiveRecords():
                    fid = mapper(record.fid)
                    if fid in touched and fid not in id_records:
                        patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress):
        """Applies delta to patchfile."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        id_deltas = self.id_deltas
        mod_count = {}
        for type in ('NPC_','CREA','CONT'):
            for record in getattr(self.patchFile,type).records:
                changed = False
                deltas = id_deltas.get(record.fid)
                if not deltas: continue
                removable = set(x.item for x in record.items)
                for removeItems,addEntries in reversed(deltas):
                    if removeItems:
                        #--Skip if some items to be removed have already been removed
                        if not removeItems.issubset(removable): continue
                        record.items = [x for x in record.items if x.item not in removeItems]
                        removable -= removeItems
                        changed = True
                    if addEntries:
                        current = set(x.item for x in record.items)
                        for entry in addEntries:
                            if entry.item not in current:
                                record.items.append(entry)
                                changed = True
                if changed:
                    keep(record.fid)
                    mod = record.fid[0]
                    mod_count[mod] = mod_count.get(mod,0) + 1
        #--Log
        log.setHeader('= '+self.__class__.name)
        log(_("=== Source Mods"))
        for mod in self.srcMods:
            log("* " +mod.s)
        log(_("\n=== Inventories Changed: %d") % (sum(mod_count.values()),))
        for mod in modInfos.getOrdered(mod_count):
            log('* %s: %3d' % (mod.s,mod_count[mod]))
#------------------------------------------------------------------------------
class ImportSpells(ImportPatcher):
    """Merge changes to actor inventories."""
    name = _('Import Spells')
    text = _("Merges changes to NPC, creature spell lists.")
    autoKey = ('Spells','spellsOnly')
    defaultItemCheck = False #--GUI: Whether new items are checked by default or not.
    siMode = True

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_deltas = {}
        self.srcMods = self.getConfigChecked()
        self.srcMods = [x for x in self.srcMods if (x in modInfos and x in patchFile.allMods)]
        self.spellsOnlyMods = set(x for x in self.srcMods if
            (x in patchFile.mergeSet and set(('spellsOnly','SIM')) & modInfos[x].getBashTags()))
        self.isActive = bool(self.srcMods)
        self.masters = set()
        for srcMod in self.srcMods:
            self.masters |= set(modInfos[srcMod].header.masters)
        self.allMods = self.masters | set(self.srcMods)
        self.mod_id_entries = {}
        self.touched = set()

    def initData(self,progress):
        """Get data from source files."""
        if not self.isActive or not self.srcMods: return
        loadFactory = LoadFactory(False,'CREA','NPC_')
        progress.setFull(len(self.srcMods))
        for index,srcMod in enumerate(self.srcMods):
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            mapper = srcFile.getLongMapper()
            for block in (srcFile.CREA, srcFile.NPC_):
                for record in block.getActiveRecords():
                    self.touched.add(mapper(record.fid))
            progress.plus()

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (None,(MreNpc,MreCrea))[self.isActive]

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (None,(MreNpc,MreCrea))[self.isActive]

    def scanModFile(self, modFile, progress):
        """Add record from modFile."""
        if not self.isActive: return
        touched = self.touched
        id_deltas = self.id_deltas
        mod_id_entries = self.mod_id_entries
        mapper = modFile.getLongMapper()
        modName = modFile.fileInfo.name
        #--Master or source?
        if modName in self.allMods:
            id_entries = mod_id_entries[modName] = {}
            modFile.convertToLongFids(('NPC_','CREA'))
            for type in ('NPC_','CREA'):
                for record in getattr(modFile,type).getActiveRecords():
                    if record.fid in touched:
                        id_entries[record.fid] = record.spells[:]
        #--Source mod?
        if modName in self.srcMods:
            id_entries = {}
            for master in modFile.tes4.masters:
                if master in mod_id_entries:
                    id_entries.update(mod_id_entries[master])
            for fid,entries in mod_id_entries[modName].iteritems():
                masterEntries = id_entries.get(fid)
                if masterEntries is None: continue
                masterItems = set(x.spells for x in masterEntries)
                modItems = set(x.spells for x in entries)
                removeItems = masterItems - modItems
                addItems = modItems - masterItems
                addEntries = [x for x in entries if x.item in addItems]
                deltas = self.id_deltas.get(fid)
                if deltas is None: deltas = self.id_deltas[fid] = []
                deltas.append((removeItems,addEntries))
        #--Keep record?
        if modFile.fileInfo.name not in self.inventOnlyMods:
            for type in ('NPC_','CREA'):
                patchBlock = getattr(self.patchFile,type)
                id_records = patchBlock.id_records
                for record in getattr(modFile,type).getActiveRecords():
                    fid = mapper(record.fid)
                    if fid in touched and fid not in id_records:
                        patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress):
        """Applies delta to patchfile."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        id_deltas = self.id_deltas
        mod_count = {}
        for type in ('NPC_','CREA'):
            for record in getattr(self.patchFile,type).records:
                changed = False
                deltas = id_deltas.get(record.fid)
                if not deltas: continue
                removable = set(x.spells for x in record.spells)
                for removeItems,addEntries in reversed(deltas):
                    if removeItems:
                        #--Skip if some items to be removed have already been removed
                        if not removeItems.issubset(removable): continue
                        record.items = [x for x in record.spells if x.spells not in removeItems]
                        removable -= removeItems
                        changed = True
                    if addEntries:
                        current = set(x.spells for x in record.spells)
                        for entry in addEntries:
                            if entry.spells not in current:
                                record.spells.append(entry)
                                changed = True
                if changed:
                    keep(record.fid)
                    mod = record.fid[0]
                    mod_count[mod] = mod_count.get(mod,0) + 1
        #--Log
        log.setHeader('= '+self.__class__.name)
        log(_("=== Source Mods"))
        for mod in self.srcMods:
            log("* " +mod.s)
        log(_("\n=== Spell lists Changed: %d") % (sum(mod_count.values()),))
        for mod in modInfos.getOrdered(mod_count):
            log('* %s: %3d' % (mod.s,mod_count[mod]))
#------------------------------------------------------------------------------
class NamesPatcher(ImportPatcher):
    """Merged leveled lists mod file."""
    name = _('Import Names')
    text = _("Import names from source mods/files.")
    defaultItemCheck = False #--GUI: Whether new items are checked by default or not.
    autoRe = re.compile(r"^Oblivion.esm$",re.I)
    autoKey = 'Names'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_full = {} #--Names keyed by long fid.
        self.activeTypes = [] #--Types ('ALCH', etc.) of data actually provided by src mods/files.
        self.skipTypes = [] #--Unknown types that were skipped.
        self.srcFiles = self.getConfigChecked()
        self.isActive = bool(self.srcFiles)

    def initData(self,progress):
        """Get names from source files."""
        if not self.isActive: return
        fullNames = FullNames(aliases=self.patchFile.aliases)
        progress.setFull(len(self.srcFiles))
        for srcFile in self.srcFiles:
            srcPath = GPath(srcFile)
            patchesDir = dirs['patches'].list()
            if reModExt.search(srcFile.s):
                if srcPath not in modInfos: continue
                srcInfo = modInfos[GPath(srcFile)]
                fullNames.readFromMod(srcInfo)
            else:
                if srcPath not in patchesDir: continue
                fullNames.readFromText(dirs['patches'].join(srcFile))
            progress.plus()
        #--Finish
        id_full = self.id_full
        knownTypes = set(MreRecord.type_class.keys())
        for type,id_name in fullNames.type_id_name.iteritems():
            if type not in knownTypes:
                self.skipTypes.append(type)
                continue
            self.activeTypes.append(type)
            for longid,(eid,name) in id_name.iteritems():
                if name != 'NO NAME':
                    id_full[longid] = name
        self.isActive = bool(self.activeTypes)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return None
        return [MreRecord.type_class[type] for type in self.activeTypes]

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return None
        return [MreRecord.type_class[type] for type in self.activeTypes]

    def scanModFile(self, modFile, progress):
        """Scan modFile."""
        if not self.isActive: return
        id_full = self.id_full
        modName = modFile.fileInfo.name
        mapper = modFile.getLongMapper()
        for type in self.activeTypes:
            if type not in modFile.tops: continue
            patchBlock = getattr(self.patchFile,type)
            id_records = patchBlock.id_records
            for record in modFile.tops[type].getActiveRecords():
                fid = record.fid
                if not record.longFids: fid = mapper(fid)
                if fid in id_records: continue
                if fid not in id_full: continue
                if record.full != id_full[fid]:
                    patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress):
        """Make changes to patchfile."""
        if not self.isActive: return
        modFile = self.patchFile
        keep = self.patchFile.getKeeper()
        id_full = self.id_full
        type_count = {}
        for type in self.activeTypes:
            if type not in modFile.tops: continue
            type_count[type] = 0
            for record in modFile.tops[type].records:
                fid = record.fid
                if fid in id_full and record.full != id_full[fid]:
                    record.full = id_full[fid]
                    keep(fid)
                    type_count[type] += 1
        log.setHeader('= '+self.__class__.name)
        log(_("=== Source Mods/Files"))
        for file in self.srcFiles:
            log("* " +file.s)
        log(_("\n=== Renamed Items"))
        for type,count in sorted(type_count.iteritems()):
            if count: log("* %s: %d" % (type,count))

#------------------------------------------------------------------------------
class NpcFacePatcher(ImportPatcher):
    """NPC Faces patcher, for use with TNR or similar mods."""
    name = _('Import NPC Faces')
    text = _("Import NPC face/eyes/hair from source mods. For use with TNR and similar mods.")
    autoRe = re.compile(r"^TNR .*.esp$",re.I)
    autoKey = 'NpcFaces'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.faceData = {}
        self.faceMods = self.getConfigChecked()
        self.isActive = len(self.faceMods) != 0

    def initData(self,progress):
        """Get faces from TNR files."""
        if not self.isActive: return
        faceData = self.faceData
        loadFactory = LoadFactory(False,MreNpc)
        progress.setFull(len(self.faceMods))
        for index,faceMod in enumerate(self.faceMods):
            if faceMod not in modInfos: continue
            faceInfo = modInfos[faceMod]
            faceFile = ModFile(faceInfo,loadFactory)
            faceFile.load(True)
            faceFile.convertToLongFids(('NPC_',))
            for npc in faceFile.NPC_.getActiveRecords():
                if npc.fid[0] != faceMod:
                    faceData[npc.fid] = (npc.fggs_p,npc.fgga_p,npc.fgts_p,npc.eye,npc.hair,npc.hairLength,npc.hairRed,npc.hairBlue,npc.hairGreen,npc.unused3)
            progress.plus()

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (None,(MreNpc,))[self.isActive]

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (None,(MreNpc,))[self.isActive]

    def scanModFile(self, modFile, progress):
        """Add lists from modFile."""
        modName = modFile.fileInfo.name
        if not self.isActive or modName in self.faceMods or 'NPC_' not in modFile.tops:
            return
        mapper = modFile.getLongMapper()
        faceData,patchNpcs = self.faceData,self.patchFile.NPC_
        modFile.convertToLongFids(('NPC_',))
        for npc in modFile.NPC_.getActiveRecords():
            if npc.fid in faceData:
                patchNpcs.setRecord(npc)

    def buildPatch(self,log,progress):
        """Adds merged lists to patchfile."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        faceData, count = self.faceData, 0
        for npc in self.patchFile.NPC_.records:
            if npc.fid in faceData:
                (npc.fggs_p, npc.fgga_p, npc.fgts_p, npc.eye,npc.hair,
                    npc.hairLength, npc.hairRed, npc.hairBlue,
                    npc.hairGreen, npc.unused3) = faceData[npc.fid]
                npc.setChanged()
                keep(npc.fid)
                count += 1
        log.setHeader('= '+self.__class__.name)
        log(_("=== Source Mods"))
        for mod in self.faceMods:
            log("* " +mod.s)
        log(_("\n=== Faces Patched: %d") % count)

#------------------------------------------------------------------------------
class NpcRedguardPatcher(Patcher):
    """Changes all Redguard NPCs texture symetry for Better Redguard Compatibility."""
    group = _('Tweakers')
    name = _('Redguard Patcher')
    text = _("Nulls FGTS of all Redguard NPCs - for compatibility with Better Redguards.")

    #--Config Phase -----------------------------------------------------------
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return tuple()
        return (MreNpc,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return tuple()
        return (MreNpc,)

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch mod, 
        but won't alter it."""
        if not self.isActive: return
        #modName = modFile.fileInfo.name
        mapper = modFile.getLongMapper()
        modFile.convertToLongFids(('NPC_'))
        patchBlock = self.patchFile.NPC_
        id_records = patchBlock.id_records
        for record in modFile.NPC_.getActiveRecords():
            #race = record.race
            #if race in (0x000D43,): 
            patchBlock.setRecord(record.getTypeCopy(mapper))
                
    def buildPatch(self,log,progress):
        """Edits patch file as desired. Will write to log."""
        if not self.isActive: return
        race = {}
        count = {}
        keep = self.patchFile.getKeeper()
        for record in self.patchFile.NPC_.records:
            #race = race[npc.fid]
            #fgts_p = npc.fgts_p
            #if race == 0x000D43 :
            for attr in ('fgts_p',):
                setattr(self,'fgts_p','00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00')
                #fgts_p = '\x00'*4*50
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log.setHeader('= '+self.__class__.name)
        log(_('* %d Redquard NPCs Tweaked') % (sum(count.values()),))
        for srcMod in sorted(count.keys()):
            log('  * %3d %s' % (count[srcMod],srcMod))
#------------------------------------------------------------------------------
class NpcSkeletonChecker(Patcher):
    """Changes all Redguard NPCs texture symetry for Better Redguard Compatibility."""
    group = _('Tweakers')
    name = _('NPCSkeletonChecker')
    text = _("Nulls FGTS of all Redguard NPCs - for compatibility with Better Redguards.")

    #--Config Phase -----------------------------------------------------------
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return tuple()
        return (MreNpc,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return tuple()
        return (MreNpc,)

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch mod, 
        but won't alter it."""
        if not self.isActive: return
        #modName = modFile.fileInfo.name
        mapper = modFile.getLongMapper()
        modFile.convertToLongFids(('NPC_'))
        patchBlock = self.patchFile.NPC_
        id_records = patchBlock.id_records
        for record in modFile.NPC_.getActiveRecords():
            GetAttr = record.__getattribute__
            race = record.race
            model = record.model
            if model.modPath != 'Characters\_male\SkeletonBeast.nif':
                if (race in (0x3cdc,) or
                    race in (0x5b54,)
                    ):
                    patchBlock.setRecord(record.getTypeCopy(mapper))
            elif model.modPath == 'Characters\_male\SkeletonBeast.nif':
                if race in (0x224fc,0x191c1,0x19204,0x00907,0x224fd,0x00d43,0x00019,0x223c8):
                    patchBlock.setRecord(record.getTypeCopy(mapper))
                
    def buildPatch(self,log,progress):
        """Edits patch file as desired. Will write to log."""
        if not self.isActive: return
        count = {}
        keep = self.patchFile.getKeeper()
        for record in self.patchFile.NPC_.records:
            race = record.race
            model = record.model
            if (model.modPath != 'Characters\_male\SkeletonBeast.nif' and
                   model.modPath != 'Characters\_male\SkeletonBeast.NIF'
                    ):
                if (race == 0x3cdc or
                    race == 0x5b54
                    ):
                    model.modPath = 'Characters\_male\SkeletonBeast.nif'
                    model.modb_p = None #??
                    model.modt_p = None #??
            elif record.model.modPath == 'Characters\_male\SkeletonBeast.nif':
                if race in (0x224fc,0x191c1,0x19204,0x00907,0x224fd,0x00d43,0x00019,0x223c8):
                    model.modPath = 'Characters\_male\Skeleton.nif'
                    model.modb_p = None #??
                    model.modt_p = None #??             
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log.setHeader('= '+self.__class__.name)
        log(_('* %d Skeletons Tweaked') % (sum(count.values()),))
        for srcMod in sorted(count.keys()):
            log('  * %3d %s' % (count[srcMod],srcMod))
#------------------------------------------------------------------------------
class RoadImporter(ImportPatcher):
    """Imports roads."""
    name = _('Import Roads')
    text = _("Import roads from source mods.")
    tip = text
    autoRe = re.compile(r"^UNDEFINED$",re.I)
    autoKey = 'Roads'
    defaultItemCheck = False #--GUI: Whether new items are checked by default or not.

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.sourceMods = self.getConfigChecked()
        self.isActive = bool(self.sourceMods)
        self.world_road = {}

    def initData(self,progress):
        """Get cells from source files."""
        if not self.isActive: return
        loadFactory = LoadFactory(False,MreCell,MreWrld,MreRoad)
        progress.setFull(len(self.sourceMods))
        for srcMod in self.sourceMods:
            if srcMod not in modInfos: continue
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            srcFile.convertToLongFids(('WRLD','ROAD'))
            for worldBlock in srcFile.WRLD.worldBlocks:
                if worldBlock.road:
                    worldId = worldBlock.world.fid
                    road = worldBlock.road.getTypeCopy()
                    self.world_road[worldId] = road
        self.isActive = bool(self.world_road)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (None,(MreCell,MreWrld,MreRoad))[self.isActive]

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (None,(MreCell,MreWrld,MreRoad))[self.isActive]

    def scanModFile(self, modFile, progress):
        """Add lists from modFile."""
        if not self.isActive or 'WRLD' not in modFile.tops: return
        patchWorlds = self.patchFile.WRLD
        modFile.convertToLongFids(('CELL','WRLD','ROAD'))
        for worldBlock in modFile.WRLD.worldBlocks:
            if worldBlock.road:
                worldId = worldBlock.world.fid
                road = worldBlock.road.getTypeCopy()
                patchWorlds.setWorld(worldBlock.world)
                patchWorlds.id_worldBlocks[worldId].road = road

    def buildPatch(self,log,progress):
        """Adds merged lists to patchfile."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        worldsPatched = set()
        for worldBlock in self.patchFile.WRLD.worldBlocks:
            worldId = worldBlock.world.fid
            curRoad = worldBlock.road
            newRoad = self.world_road.get(worldId)
            if newRoad and (not curRoad or curRoad.points_p != newRoad.points_p
                or curRoad.connections_p != newRoad.connections_p
                ):
                worldBlock.road = newRoad
                keep(worldId)
                keep(newRoad.fid)
                worldsPatched.add((worldId[0].s,worldBlock.world.eid))
        log.setHeader('= '+self.__class__.name)
        log(_("=== Source Mods"))
        for mod in self.sourceMods:
            log("* " +mod.s)
        log(_("\n=== Worlds Patched"))
        for modWorld in sorted(worldsPatched):
            log('* %s: %s' % modWorld)

#------------------------------------------------------------------------------
class SoundPatcher(ImportPatcher):
    """Imports sounds from source mods into patch."""
    name = _('Import Sounds')
    text = _("Import sounds (from Magic Effects, Containers, Activators, Lights, Weathers and Doors) from source mods.")
    tip = text
    autoRe = re.compile(r"^UNDEFINED$",re.I)
    autoKey = 'Sound'
    defaultItemCheck = False #--GUI: Whether new items are checked by default or not.

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_data = {} #--Names keyed by long fid.
        self.srcClasses = set() #--Record classes actually provided by src mods/files.
        self.sourceMods = self.getConfigChecked()
        self.isActive = len(self.sourceMods) != 0
        #--Type Fields
        recAttrs_class = self.recAttrs_class = {}
        for recClass in (MreMgef,):
            recAttrs_class[recClass] = ('castingSound','boltSound','hitSound','areaSound')
        for recClass in (MreActi,MreLigh):
            recAttrs_class[recClass] = ('sound',)
        for recClass in (MreWthr,):
            recAttrs_class[recClass] = ('sound','sounds')
        for recClass in (MreCont,):
            recAttrs_class[recClass] = ('soundOpen','soundClose')
        for recClass in (MreDoor,):
            recAttrs_class[recClass] = ('soundOpen','soundClose','soundLoop')
        #--Needs Longs
        self.longTypes = set(('MGEF','ACTI','LIGH','WTHR','CONT','DOOR'))

    def initData(self,progress):
        """Get sounds from source files."""
        if not self.isActive: return
        id_data = self.id_data
        recAttrs_class = self.recAttrs_class
        loadFactory = LoadFactory(False,*recAttrs_class.keys())
        longTypes = self.longTypes & set(x.classType for x in self.recAttrs_class)
        progress.setFull(len(self.sourceMods))
        for index,srcMod in enumerate(self.sourceMods):
            if srcMod not in modInfos: continue
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass,recAttrs in recAttrs_class.items():
                if recClass.classType not in srcFile.tops: continue
                self.srcClasses.add(recClass)
                for record in srcFile.tops[recClass.classType].getActiveRecords():
                    fid = mapper(record.fid)
                    id_data[fid] = dict((attr,record.__getattribute__(attr)) for attr in recAttrs)
            progress.plus()
        self.longTypes = self.longTypes & set(x.classType for x in self.srcClasses)
        self.isActive = bool(self.srcClasses)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return None
        return self.srcClasses

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return None
        return self.srcClasses

    def scanModFile(self, modFile, progress):
        """Scan mod file against source data."""
        if not self.isActive: return
        id_data = self.id_data
        modName = modFile.fileInfo.name
        mapper = modFile.getLongMapper()
        if self.longTypes:
            modFile.convertToLongFids(self.longTypes)
        for recClass in self.srcClasses:
            type = recClass.classType
            if type not in modFile.tops: continue
            patchBlock = getattr(self.patchFile,type)
            for record in modFile.tops[type].getActiveRecords():
                fid = record.fid
                if not record.longFids: fid = mapper(fid)
                if fid not in id_data: continue
                for attr,value in id_data[fid].items():
                    if record.__getattribute__(attr) != value:
                        patchBlock.setRecord(record.getTypeCopy(mapper))
                        break

    def buildPatch(self,log,progress):
        """Merge last version of record with patched sound data as needed."""
        if not self.isActive: return
        modFile = self.patchFile
        keep = self.patchFile.getKeeper()
        id_data = self.id_data
        type_count = {}
        for recClass in self.srcClasses:
            type = recClass.classType
            if type not in modFile.tops: continue
            type_count[type] = 0
            #deprint(recClass,type,type_count[type])
            for record in modFile.tops[type].records:
                fid = record.fid
                if fid not in id_data: continue
                for attr,value in id_data[fid].items():
                    if record.__getattribute__(attr) != value:
                        break
                else:
                    continue
                for attr,value in id_data[fid].items():
                    record.__setattr__(attr,value)
                keep(fid)
                type_count[type] += 1
        log.setHeader('= '+self.__class__.name)
        log(_("=== Source Mods"))
        for mod in self.sourceMods:
            log("* " +mod.s)
        log(_("\n=== Modified Records"))
        for type,count in sorted(type_count.items()):
            if count: log("* %s: %d" % (type,count))

#------------------------------------------------------------------------------
class StatsPatcher(ImportPatcher):
    """Import stats from mod file."""
    scanOrder = 28
    editOrder = 28 #--Run ahead of bow patcher
    name = _('Import Stats')
    text = _("Import stats from any pickupable items from source mods/files.")
    defaultItemCheck = False #--GUI: Whether new items are checked by default or not.
    autoRe = re.compile(r"^UNDEFINED$",re.I)
    autoKey = 'Stats'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.srcFiles = self.getConfigChecked()
        self.isActive = bool(self.srcFiles)
        #--To be filled by initData
        self.id_stat = {} #--Stats keyed by long fid.
        self.activeTypes = [] #--Types ('ARMO', etc.) of data actually provided by src mods/files.
        self.typeFields = {}

    def initData(self,progress):
        """Get stats from source files."""
        if not self.isActive: return
        itemStats = ItemStats(aliases=self.patchFile.aliases)
        progress.setFull(len(self.srcFiles))
        for srcFile in self.srcFiles:
            srcPath = GPath(srcFile)
            patchesDir = dirs['patches'].list()
            if reModExt.search(srcFile.s):
                if srcPath not in modInfos: continue
                srcInfo = modInfos[GPath(srcFile)]
                itemStats.readFromMod(srcInfo)
            else:
                if srcPath not in patchesDir: continue
                itemStats.readFromText(dirs['patches'].join(srcFile))
            progress.plus()
        #--Finish
        id_stat = self.id_stat
        for type in itemStats.type_stats:
            typeStats = itemStats.type_stats[type]
            if typeStats:
                self.activeTypes.append(type)
                id_stat.update(typeStats)
                self.typeFields[type] = itemStats.type_attrs[type][1:]
        self.isActive = bool(self.activeTypes)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return None
        return [MreRecord.type_class[type] for type in self.activeTypes]

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return None
        return [MreRecord.type_class[type] for type in self.activeTypes]

    def scanModFile(self, modFile, progress):
        """Add affected items to patchFile."""
        if not self.isActive: return
        id_stat = self.id_stat
        mapper = modFile.getLongMapper()
        for type in self.activeTypes:
            if type not in modFile.tops: continue
            typeFields = self.typeFields[type]
            patchBlock = getattr(self.patchFile,type)
            id_records = patchBlock.id_records
            for record in modFile.tops[type].getActiveRecords():
                fid = record.fid
                if not record.longFids: fid = mapper(fid)
                if fid in id_records: continue
                stats = id_stat.get(fid)
                if not stats: continue
                modStats = tuple(record.__getattribute__(attr) for attr in typeFields)
                if modStats != stats[1:]:
                    patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress):
        """Adds merged lists to patchfile."""
        if not self.isActive: return
        patchFile = self.patchFile
        keep = self.patchFile.getKeeper()
        id_stat = self.id_stat
        allCounts = []
        for type in self.activeTypes:
            if type not in patchFile.tops: continue
            typeFields = self.typeFields[type]
            count,counts = 0,{}
            for record in patchFile.tops[type].records:
                fid = record.fid
                stats = id_stat.get(fid)
                if not stats: continue
                modStats = tuple(record.__getattribute__(attr) for attr in typeFields)
                if modStats == stats[1:]: continue
                for attr,value in zip(typeFields,stats[1:]):
                    record.__setattr__(attr,value)
                keep(fid)
                count += 1
                counts[fid[0]] = 1 + counts.get(fid[0],0)
            allCounts.append((type,count,counts))
        log.setHeader('= '+self.__class__.name)
        log(_("=== Source Mods/Files"))
        for file in self.srcFiles:
            log("* " +file.s)
        log(_("\n=== Modified Stats"))
        for type,count,counts in allCounts:
            if not count: continue
            typeName = {'ALCH':_('alch'),'AMMO':_('Ammo'),'ARMO':_('Armor'),'INGR':_('Ingr'),'MISC':_('Misc'),'WEAP':_('Weapons'),'SLGM':_('Soulgem'),'SGST':_('Sigil Stone'),'LIGH':_('Lights'),'KEYM':_('Keys'),'CLOT':_('Clothes'),'BOOK':_('Books'),'APPA':_('Apparatus')}[type]
            log("* %s: %d" % (typeName,count))
            for modName in sorted(counts):
                log("  * %s: %d" % (modName.s,counts[modName]))
#------------------------------------------------------------------------------
class SpellsPatcher(ImportPatcher):
    """Import spell changes from mod files."""
    scanOrder = 29
    editOrder = 29 #--Run ahead of bow patcher
    name = _('Import Spell Stats')
    text = _("Import stats from any spells from source mods/files.")
    defaultItemCheck = False #--GUI: Whether new items are checked by default or not.
    autoRe = re.compile(r"^UNDEFINED$",re.I)
    autoKey = 'Spells'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.srcFiles = self.getConfigChecked()
        self.isActive = bool(self.srcFiles)
        #--To be filled by initData
        self.id_stat = {} #--Stats keyed by long fid.
        self.activeTypes = [] #--Types ('Spells', etc.) of data actually provided by src mods/files.
        self.typeFields = {}

    def initData(self,progress):
        """Get stats from source files."""
        if not self.isActive: return
        itemStats = SpellRecords(aliases=self.patchFile.aliases)
        progress.setFull(len(self.srcFiles))
        for srcFile in self.srcFiles:
            srcPath = GPath(srcFile)
            patchesDir = dirs['patches'].list()
            if reModExt.search(srcFile.s):
                if srcPath not in modInfos: continue
                srcInfo = modInfos[GPath(srcFile)]
                itemStats.readFromMod(srcInfo)
            else:
                if srcPath not in patchesDir: continue
                itemStats.readFromText(dirs['patches'].join(srcFile))
            progress.plus()
        #--Finish
        id_stat = self.id_stat
        for type in itemStats.type_stats:
            typeStats = itemStats.type_stats[type]
            if typeStats:
                self.activeTypes.append(type)
                id_stat.update(typeStats)
                self.typeFields[type] = itemStats.type_attrs[type][1:]
        self.isActive = bool(self.activeTypes)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return None
        return [MreRecord.type_class[type] for type in self.activeTypes]

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return None
        return [MreRecord.type_class[type] for type in self.activeTypes]

    def scanModFile(self, modFile, progress):
        """Add affected items to patchFile."""
        if not self.isActive: return
        id_stat = self.id_stat
        mapper = modFile.getLongMapper()
        for type in self.activeTypes:
            if type not in modFile.tops: continue
            typeFields = self.typeFields[type]
            patchBlock = getattr(self.patchFile,type)
            id_records = patchBlock.id_records
            for record in modFile.tops[type].getActiveRecords():
                fid = record.fid
                if not record.longFids: fid = mapper(fid)
                if fid in id_records: continue
                stats = id_stat.get(fid)
                if not stats: continue
                modStats = tuple(record.__getattribute__(attr) for attr in typeFields)
                if modStats != stats[1:]:
                    patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress):
        """Adds merged lists to patchfile."""
        if not self.isActive: return
        patchFile = self.patchFile
        keep = self.patchFile.getKeeper()
        id_stat = self.id_stat
        allCounts = []
        for type in self.activeTypes:
            if type not in patchFile.tops: continue
            typeFields = self.typeFields[type]
            count,counts = 0,{}
            for record in patchFile.tops[type].records:
                fid = record.fid
                stats = id_stat.get(fid)
                if not stats: continue
                modStats = tuple(record.__getattribute__(attr) for attr in typeFields)
                if modStats == stats[1:]: continue
                for attr,value in zip(typeFields,stats[1:]):
                    record.__setattr__(attr,value)
                keep(fid)
                count += 1
                counts[fid[0]] = 1 + counts.get(fid[0],0)
            allCounts.append((type,count,counts))
        log.setHeader('= '+self.__class__.name)
        log(_("=== Source Mods/Files"))
        for file in self.srcFiles:
            log("* " +file.s)
        log(_("\n=== Modified Stats"))
        for type,count,counts in allCounts:
            if not count: continue
            typeName = {'SPEL':_('Spells'),}[type]
            log("* %s: %d" % (typeName,count))
            for modName in sorted(counts):
                log("  * %s: %d" % (modName.s,counts[modName]))
# Patchers: 30 ----------------------------------------------------------------
#------------------------------------------------------------------------------
class AssortedTweak_ArmorShows(MultiTweakItem):
    """Fix armor to show amulets/rings."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self,label,tip,key):
        MultiTweakItem.__init__(self,label,tip,key)
        self.hidesBit = {'armorShowsRings':16,'armorShowsAmulets':17}[key]

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreArmo,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreArmo,)

    def scanModFile(self,modFile,progress,patchFile):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.ARMO
        hidesBit = self.hidesBit
        for record in modFile.ARMO.getActiveRecords():
            if record.flags[hidesBit] and not record.flags.notPlayable:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        hidesBit = self.hidesBit
        for record in patchFile.ARMO.records:
            if record.flags[hidesBit] and not record.flags.notPlayable:
                record.flags[hidesBit] = False
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log.setHeader('=== '+self.label)
        log(_('* Armor Pieces Tweaked: %d') % (sum(count.values()),))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))

#------------------------------------------------------------------------------
class AssortedTweak_ClothingShows(MultiTweakItem):
    """Fix robes, gloves and the like to show amulets/rings."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self,label,tip,key):
        MultiTweakItem.__init__(self,label,tip,key)
        self.hidesBit = {'ClothingShowsRings':16,'ClothingShowsAmulets':17}[key]

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreClot,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreClot,)

    def scanModFile(self,modFile,progress,patchFile):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.CLOT
        hidesBit = self.hidesBit
        for record in modFile.CLOT.getActiveRecords():
            if record.flags[hidesBit] and not record.flags.notPlayable:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        hidesBit = self.hidesBit
        for record in patchFile.CLOT.records:
            if record.flags[hidesBit] and not record.flags.notPlayable:
                record.flags[hidesBit] = False
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log.setHeader('=== '+self.label)
        log(_('* Clothing Pieces Tweaked: %d') % (sum(count.values()),))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))

#------------------------------------------------------------------------------
class AssortedTweak_BowReach(MultiTweakItem):
    """Fix bows to have reach = 1.0."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        MultiTweakItem.__init__(self,_("Bow Reach Fix"),
            _('Fix bows with zero reach. (Zero reach causes CTDs.)'),
            'BowReach',
            ('1.0',  '1.0'),
            )

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreWeap,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreWeap,)

    def scanModFile(self,modFile,progress,patchFile):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.WEAP
        for record in modFile.WEAP.getActiveRecords():
            if record.weaponType == 5 and record.reach <= 0:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.WEAP.records:
            if record.weaponType == 5 and record.reach <= 0:
                record.reach = 1
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log.setHeader(_('=== Bow Reach Fix'))
        log(_('* Bows fixed: %d') % (sum(count.values()),))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))

#------------------------------------------------------------------------------
class VanillaNPCSkeletonPatcher(MultiTweakItem):
    """Changes all NPCs to use the vanilla beast race skeleton."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        MultiTweakItem.__init__(self,_("Vanilla Beast Skeleton Tweaker"),
            _('Avoids bug if an NPC is a beast race but has the regular skeleton.nif selected.'),
            'Vanilla Skeleton',
            ('1.0',  '1.0'),
            )

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreNpc,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreNpc,)

    def scanModFile(self,modFile,progress,patchFile):
        """Scans specified mod file to extract info. May add record to patch mod, 
        but won't alter it."""
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.NPC_
        for record in modFile.NPC_.getActiveRecords():
            record = record.getTypeCopy(mapper)
            model = record.model.modPath
            if model.lower() == r'characters\_male\skeleton.nif':
                patchRecords.setRecord(record)
                
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.NPC_.records:
            record.model.modPath = "Characters\_Male\SkeletonBeast.nif"
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log.setHeader(_('===Vanilla Beast Skeleton'))
        log(_('* %d Skeletons Tweaked') % (sum(count.values()),))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))
#------------------------------------------------------------------------------
class AssortedTweak_ConsistentRings(MultiTweakItem):
    """Sets rings to all work on same finger."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        MultiTweakItem.__init__(self,_("Right Hand Rings"),
            _('Fixes rings to unequip consistently by making them prefer the right hand.'),
            'ConsistentRings',
            ('1.0',  '1.0'),
            )

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreClot,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreClot,)

    def scanModFile(self,modFile,progress,patchFile):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.CLOT
        for record in modFile.CLOT.getActiveRecords():
            if record.flags.leftRing:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.CLOT.records:
            if record.flags.leftRing:
                record.flags.leftRing = False
                record.flags.rightRing = True
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log.setHeader(_('=== Right Hand Rings'))
        log(_('* Rings fixed: %d') % (sum(count.values()),))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))
#------------------------------------------------------------------------------
class AssortedTweak_ClothingPlayable(MultiTweakItem):
    """Sets all clothes to playable"""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        MultiTweakItem.__init__(self,_("All Clothing Playable"),
            _('Sets all clothing to be playable.'),
            'PlayableClothing',
            ('1.0',  '1.0'),
            )

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreClot,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreClot,)

    def scanModFile(self,modFile,progress,patchFile):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.CLOT
        for record in modFile.CLOT.getActiveRecords():
            if record.flags.notPlayable:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.CLOT.records:
            if record.flags.notPlayable:
			#If only the right ring and no other body flags probably a token that wasn't zeroed (which there are a lot of).
                if record.flags.leftRing != 0 or record.flags.foot != 0 or record.flags.hand != 0 or record.flags.amulet != 0 or record.flags.lowerBody != 0 or record.flags.upperBody != 0 or record.flags.head != 0 or record.flags.hair != 0 or record.flags.tail != 0:
                    record.flags.notPlayable = 0
                    keep(record.fid)
                    srcMod = record.fid[0]
                    count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log.setHeader(_('=== Playable Clothes'))
        log(_('* Clothes set as playable: %d') % (sum(count.values()),))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))
#------------------------------------------------------------------------------
class AssortedTweak_ArmorPlayable(MultiTweakItem):
    """Sets all armors to be playable"""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        MultiTweakItem.__init__(self,_("All Armor Playable"),
            _('Sets all armor to be playable.'),
            'PlayableArmor',
            ('1.0',  '1.0'),
            )

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreArmo,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreArmo,)

    def scanModFile(self,modFile,progress,patchFile):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.ARMO
        for record in modFile.ARMO.getActiveRecords():
            if record.flags.notPlayable:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.ARMO.records:
            if record.flags.notPlayable:
                # We only want to set playable if the record has at least one body flag... otherwise most likely a token.
                if record.flags.leftRing != 0 or record.flags.rightRing != 0 or record.flags.foot != 0 or record.flags.hand != 0 or record.flags.amulet != 0 or record.flags.lowerBody != 0 or record.flags.upperBody != 0 or record.flags.head != 0 or record.flags.hair != 0 or record.flags.tail != 0 or record.flags.shield != 0:
                    name = record.full
                    record.flags.notPlayable = 0
                    keep(record.fid)
                    srcMod = record.fid[0]
                    count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log.setHeader(_('=== Playable Armor'))
        log(_('* Armor pieces set as playable: %d') % (sum(count.values()),))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))
#------------------------------------------------------------------------------
class AssortedTweak_DarnBooks(MultiTweakItem):
    """DarNifies books."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        MultiTweakItem.__init__(self,_("DarNified Books"),
            _('Books will be reformatted for DarN UI.'),
            'DarnBooks',
            ('default',  'default'),
            )

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreBook,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreBook,)

    def scanModFile(self,modFile,progress,patchFile):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        maxWeight = self.choiceValues[self.chosen][0]
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.BOOK
        id_records = patchBlock.id_records
        for record in modFile.BOOK.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if not record.enchantment:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        reColor = re.compile(r'<font color="?([a-fA-F0-9]+)"?>',re.I+re.M)
        reTagInWord = re.compile(r'([a-z])<font face=1>',re.M)
        reFont1 = re.compile(r'(<?<font face=1( ?color=[0-9a-zA]+)?>)+',re.I+re.M)
        reDiv = re.compile(r'<div',re.I+re.M)
        reFont = re.compile(r'<font',re.I+re.M)
        keep = patchFile.getKeeper()
        reHead2 = re.compile(r'^(<<|\^\^|>>|)==\s*(\w[^=]+?)==\s*\r\n',re.M)
        reHead3 = re.compile(r'^(<<|\^\^|>>|)===\s*(\w[^=]+?)\r\n',re.M)
        reBold = re.compile(r'(__|\*\*|~~)')
        reAlign = re.compile(r'^(<<|\^\^|>>)',re.M)
        align_text = {'^^':'center','<<':'left','>>':'right'}
        self.inBold = False
        def replaceBold(mo):
            self.inBold = not self.inBold
            str = '<font face=3 color=%s>' % ('444444','440000')[self.inBold]
            return str
        def replaceAlign(mo):
            return '<div align=%s>' % align_text[mo.group(1)]
        for record in patchFile.BOOK.records:
            if record.text and not record.enchantment:
                text = record.text
                if reHead2.match(text):
                    inBold = False
                    text = reHead2.sub(r'\1<font face=1 color=220000>\2<font face=3 color=444444>\r\n',text)
                    text = reHead3.sub(r'\1<font face=3 color=220000>\2<font face=3 color=444444>\r\n',text)
                    text = reAlign.sub(replaceAlign,text)
                    text = reBold.sub(replaceBold,text)
                    text = re.sub(r'\r\n',r'<br>\r\n',text)
                else:
                    maColor = reColor.search(text)
                    if maColor:
                        color = maColor.group(1)
                    elif record.flags.isScroll:
                        color = '000000'
                    else:
                        color = '444444'
                    fontFace = '<font face=3 color='+color+'>'
                    text = reTagInWord.sub(r'\1',text)
                    text.lower()
                    if reDiv.search(text) and not reFont.search(text):
                        text = fontFace+text
                    else:
                        text = reFont1.sub(fontFace,text)
                if text != record.text:
                    record.text = text
                    keep(record.fid)
                    srcMod = record.fid[0]
                    count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log.setHeader('=== '+self.label)
        log(_('* Books DarNified: %d') % (sum(count.values()),))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))

#------------------------------------------------------------------------------
class AssortedTweak_FogFix(MultiTweakItem):
    """Fix fog in cell to be non-zero."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        MultiTweakItem.__init__(self,_("Nvidia Fog Fix"),
            _('Fix fog related Nvidia black screen problems.)'),
            'FogFix',
            ('0.0001',  '0.0001'),
            )

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreCell,MreWrld)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreCell,MreWrld)

    def scanModFile(self, modFile, progress,patchFile):
        """Add lists from modFile."""
        if 'CELL' not in modFile.tops: return
        patchCells = patchFile.CELL
        modFile.convertToLongFids(('CELL',))
        for cellBlock in modFile.CELL.cellBlocks:
            cell = cellBlock.cell
            if not (cell.fogNear or cell.fogFar or cell.fogClip):
                patchCells.setCell(cell)

    def buildPatch(self,log,progress,patchFile):
        """Adds merged lists to patchfile."""
        keep = patchFile.getKeeper()
        count = {}
        for cellBlock in patchFile.CELL.cellBlocks:
            for cellBlock in patchFile.CELL.cellBlocks:
                cell = cellBlock.cell
                if not (cell.fogNear or cell.fogFar or cell.fogClip):
                    cell.fogNear = 0.0001
                    keep(cell.fid)
                    count.setdefault(cell.fid[0],0)
                    count[cell.fid[0]] += 1
        #--Log
        log.setHeader(_('=== Nvidia Fog Fix'))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))

#------------------------------------------------------------------------------
class AssortedTweak_NoLightFlicker(MultiTweakItem):
    """Remove light flickering for low end machines."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        MultiTweakItem.__init__(self,_("No Light Flicker"),
            _('Remove flickering from lights. For use on low-end machines.'),
            'NoLightFlicker',
            ('1.0',  '1.0'),
            )
        self.flags = flags = MreLigh._flags()
        flags.flickers = flags.flickerSlow = flags.pulse = flags.pulseSlow = True

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreLigh,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreLigh,)

    def scanModFile(self,modFile,progress,patchFile):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        flickerFlags = self.flags
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.LIGH
        for record in modFile.LIGH.getActiveRecords():
            if record.flags & flickerFlags:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        flickerFlags = self.flags
        notFlickerFlags = ~flickerFlags
        keep = patchFile.getKeeper()
        for record in patchFile.LIGH.records:
            if int(record.flags & flickerFlags):
                record.flags &= notFlickerFlags
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log.setHeader(_('=== No Light Flicker'))
        log(_('* Lights unflickered: %d') % (sum(count.values()),))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))

#------------------------------------------------------------------------------
class AssortedTweak_PotionWeight(MultiTweakItem):
    """Reweighs standard potions down to 0.1."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        MultiTweakItem.__init__(self,_("Max Weight Potions"),
            _('Potion weight will be capped.'),
            'MaximumPotionWeight',
            (_('0.1'),  0.1),
            (_('0.2'),  0.2),
            (_('0.4'),  0.4),
            (_('0.6'),  0.6),
            )

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreAlch,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreAlch,)

    def scanModFile(self,modFile,progress,patchFile):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        maxWeight = self.choiceValues[self.chosen][0]
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.ALCH
        id_records = patchBlock.id_records
        for record in modFile.ALCH.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.weight > maxWeight and record.weight < 1:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        maxWeight = self.choiceValues[self.chosen][0]
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.ALCH.records:
            if record.weight > maxWeight and record.weight < 1 and not ('SEFF',0) in record.getEffects():
                record.weight = maxWeight
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log.setHeader(_('=== Reweigh Potions to Maximum Weight'))
        log(_('* Potions Reweighed by max weight potions: %d') % (sum(count.values()),))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))

#------------------------------------------------------------------------------
class AssortedTweak_PotionWeightMinimum(MultiTweakItem):
    """Reweighs any potions up to 4."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        MultiTweakItem.__init__(self,_("Minimum Weight Potions"),
            _('Potion weight will be floored.'),
            'MinimumPotionWeight',
            (_('1'),  1),
            (_('2'),  2),
            (_('3'),  3),
            (_('4'),  4),
            )

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreAlch,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreAlch,)

    def scanModFile(self,modFile,progress,patchFile):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        minWeight = self.choiceValues[self.chosen][0]
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.ALCH
        id_records = patchBlock.id_records
        for record in modFile.ALCH.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.weight < minWeight:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        minWeight = self.choiceValues[self.chosen][0]
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.ALCH.records:
            if record.weight < minWeight:
                record.weight = minWeight
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log.setHeader(_('=== Potions Reweighed to Mimimum Weight'))
        log(_('* Potions Reweighed by Minimum Weight Potions: %d') % (sum(count.values()),))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))

#------------------------------------------------------------------------------
class AssortedTweak_StaffWeight(MultiTweakItem):
    """Reweighs staffs."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        MultiTweakItem.__init__(self,_("Max Weight Staffs"),
            _('Staff weight will be capped.'),
            'StaffWeight',
            (_('1'),  1),
            (_('2'),  2),
            (_('3'),  3),
            (_('4'),  4),
            (_('5'),  5),
            (_('6'),  6),
            (_('7'),  7),
            (_('8'),  8),
            )

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreWeap,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreWeap,)

    def scanModFile(self,modFile,progress,patchFile):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        maxWeight = self.choiceValues[self.chosen][0]
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.WEAP
        id_records = patchBlock.id_records
        for record in modFile.WEAP.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.weaponType == 4 and record.weight > maxWeight:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        maxWeight = self.choiceValues[self.chosen][0]
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.WEAP.records:
            if record.weaponType == 4 and record.weight > maxWeight:
                record.weight = maxWeight
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log.setHeader(_('=== Reweigh Staffs'))
        log(_('* Staffs Reweighed: %d') % (sum(count.values()),))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))

#------------------------------------------------------------------------------
class AssortedTweaker(MultiTweaker):
    """Tweaks assorted stuff. Sub-tweaks behave like patchers themselves."""
    name = _('Tweak Assorted')
    text = _("Tweak various records in miscellaneous ways.")
    tweaks = sorted([
        AssortedTweak_ArmorShows(_("Armor Shows Amulets"),
            _("Prevents armor from hiding amulets."),
            'armorShowsAmulets',
            ),
        AssortedTweak_ArmorShows(_("Armor Shows Rings"),
            _("Prevents armor from hiding rings."),
            'armorShowsRings',
            ),
        AssortedTweak_ClothingShows(_("Clothing Shows Amulets"),
            _("Prevents Clothing from hiding amulets."),
            'ClothingShowsAmulets',
            ),
        AssortedTweak_ClothingShows(_("Clothing Shows Rings"),
            _("Prevents Clothing from hiding rings."),
            'ClothingShowsRings',
            ),
        AssortedTweak_ArmorPlayable(),
        AssortedTweak_ClothingPlayable(),
        AssortedTweak_BowReach(),
        AssortedTweak_ConsistentRings(),
        AssortedTweak_DarnBooks(),
        AssortedTweak_FogFix(),
        AssortedTweak_NoLightFlicker(),
        AssortedTweak_PotionWeight(),
        AssortedTweak_PotionWeightMinimum(),
        AssortedTweak_StaffWeight(),
        ],key=lambda a: a.label.lower())

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return None
        classTuples = [tweak.getReadClasses() for tweak in self.enabledTweaks]
        return sum(classTuples,tuple())

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return None
        classTuples = [tweak.getWriteClasses() for tweak in self.enabledTweaks]
        return sum(classTuples,tuple())

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        if not self.isActive: return
        for tweak in self.enabledTweaks:
            tweak.scanModFile(modFile,progress,self.patchFile)

    def buildPatch(self,log,progress):
        """Applies individual clothes tweaks."""
        if not self.isActive: return
        log.setHeader('= '+self.__class__.name,True)
        for tweak in self.enabledTweaks:
            tweak.buildPatch(log,progress,self.patchFile)

#------------------------------------------------------------------------------
class GlobalsTweak(MultiTweakItem):
    """set a global to specified value"""
    #--Patch Phase ------------------------------------------------------------
    def buildPatch(self,patchFile,keep,log):
        """Build patch."""
        value = self.choiceValues[self.chosen][0]
        for record in patchFile.GLOB.records:
            if record.eid.lower() == self.key:
                record.value = value
                keep(record.fid)
        log('* %s set to: %0.1f' % (self.label,value))

#------------------------------------------------------------------------------
class GlobalsTweaker(MultiTweaker):
    """Select values to set various globals to."""
    scanOrder = 29
    editOrder = 29
    name = _('Globals')
    text = _("Set globals to various values")
    tweaks = sorted([
        GlobalsTweak(_("Timescale"),
            _("Timescale will be set to:"),
            'timescale',
            (_('1'),1),
            (_('8'),8),
            (_('10'),10),
            (_('12'),12),
            (_('18'),18),
            (_('24'),24),
            (_('[30]'),30),
            (_('40'),40),
            ),
        GlobalsTweak(_("Thieves Guild: Quest Stealing Penalty"),
            _("The penalty (in Septims) for stealing while doing a Thieves Guild job:"),
            'tgpricesteal',
            (_('100'),100),
            (_('150'),150),
            (_('[200]'),200),
            (_('300'),300),
            (_('400'),400),
            ),
        GlobalsTweak(_("Thieves Guild: Quest Killing Penalty"),
            _("The penalty (in Septims) for killing while doing a Thieves Guild job:"),
            'tgpriceperkill',
            (_('250'),250),
            (_('500'),500),
            (_('[1000]'),1000),
            (_('1500'),1500),
            (_('2000'),2000),
            ),
        GlobalsTweak(_("Thieves Guild: Quest Attacking Penalty"),
            _("The penalty (in Septims) for attacking while doing a Thieves Guild job:"),
            'tgpriceattack',
            (_('100'),100),
            (_('250'),250),
            (_('[500]'),500),
            (_('750'),750),
            (_('1000'),1000),
            ),
        GlobalsTweak(_("Crime: Force Jail"),
            _("The amount of Bounty at which a jail sentence is mandatory"),
            'crimeforcejail',
            (_('1000'),1000),
            (_('2500'),2500),
            (_('[5000]'),5000),
            (_('7500'),7500),
            (_('10000'),10000),
            ),
        ],key=lambda a: a.label.lower())

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (None,(MreGlob,))[self.isActive]

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (None,(MreGlob,))[self.isActive]

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        if not self.isActive or 'GLOB' not in modFile.tops: return
        mapper = modFile.getLongMapper()
        patchRecords = self.patchFile.GLOB
        id_records = patchRecords.id_records
        for record in modFile.GLOB.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            for tweak in self.enabledTweaks:
                if record.eid.lower() == tweak.key:
                    record = record.getTypeCopy(mapper)
                    patchRecords.setRecord(record)
                    break

    def buildPatch(self,log,progress):
        """Applies individual clothes tweaks."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        log.setHeader('= '+self.__class__.name)
        for tweak in self.enabledTweaks:
            tweak.buildPatch(self.patchFile,keep,log)

#------------------------------------------------------------------------------
class ClothesTweak(MultiTweakItem):
    flags = {
        'hoods':   1<<1,
        'shirts':  1<<2,
        'pants':   1<<3,
        'gloves':  1<<4,
        'amulets': 1<<8,
        'rings2':  1<<16,
        'amulets2': 1<<17,
        #--Multi
        'robes':   (1<<2) + (1<<3),
        'rings':   (1<<6) + (1<<7),
        }

    #--Config Phase -----------------------------------------------------------
    def __init__(self,label,tip,key,*choices):
        MultiTweakItem.__init__(self,label,tip,key,*choices)
        typeKey = key[:key.find('.')]
        self.orTypeFlags = typeKey == 'rings'
        self.typeFlags = self.__class__.flags[typeKey]

    def isMyType(self,record):
        """Returns true to save record for late processing."""
        if record.flags.notPlayable: return False #--Ignore non-playable items.
        recTypeFlags = int(record.flags) & 0xFFFF
        myTypeFlags = self.typeFlags
        return (
            (recTypeFlags == myTypeFlags) or
            (self.orTypeFlags and (recTypeFlags & myTypeFlags == recTypeFlags))
            )

#------------------------------------------------------------------------------
class ClothesTweak_MaxWeight(ClothesTweak):
    """Enforce a max weight for specified clothes."""
    #--Patch Phase ------------------------------------------------------------
    def buildPatch(self,patchFile,keep,log):
        """Build patch."""
        tweakCount = 0
        maxWeight = self.choiceValues[self.chosen][0]
        superWeight = max(10,5*maxWeight) #--Guess is intentionally overweight
        for record in patchFile.CLOT.records:
            weight = record.weight
            if self.isMyType(record) and weight > maxWeight and weight < superWeight:
                record.weight = maxWeight
                keep(record.fid)
                tweakCount += 1
        log('* %s: [%0.1f]: %d' % (self.label,maxWeight,tweakCount))

#------------------------------------------------------------------------------
class ClothesTweak_Unblock(ClothesTweak):
    """Unlimited rings, amulets."""
    #--Config Phase -----------------------------------------------------------
    def __init__(self,label,tip,key,*choices):
        ClothesTweak.__init__(self,label,tip,key,*choices)
        self.unblockFlags = self.__class__.flags[key[key.rfind('.')+1:]]

    #--Patch Phase ------------------------------------------------------------
    def buildPatch(self,patchFile,keep,log):
        """Build patch."""
        tweakCount = 0
        for record in patchFile.CLOT.records:
            if self.isMyType(record) and int(record.flags & self.unblockFlags):
                record.flags &= ~self.unblockFlags
                keep(record.fid)
                tweakCount += 1
        log('* %s: %d' % (self.label,tweakCount))

#------------------------------------------------------------------------------
class ClothesTweaker(MultiTweaker):
    """Patches clothes in miscellaneous ways."""
    scanOrder = 31
    editOrder = 31
    name = _('Tweak Clothes')
    text = _("Tweak clothing weight and blocking.")
    tweaks = sorted([
        ClothesTweak_Unblock(_("Unlimited Amulets"),
            _("Wear unlimited number of amulets - but they won't display."),
            'amulets.unblock.amulets'),
        ClothesTweak_Unblock(_("Unlimited Rings"),
            _("Wear unlimited number of rings - but they won't display."),
            'rings.unblock.rings'),
        ClothesTweak_Unblock(_("Gloves Show Rings"),
            _("Gloves will always show rings. (Conflicts with Unlimited Rings.)"),
            'gloves.unblock.rings2'),
        ClothesTweak_Unblock(_("Robes Show Pants"),
            _("Robes will allow pants, greaves, skirts - but they'll clip."),
            'robes.unblock.pants'),
        ClothesTweak_Unblock(_("Robes Show Amulets"),
            _("Robes will always show amulets. (Conflicts with Unlimited Amulets.)"),
            'robes.show.amulets2'),
        ClothesTweak_MaxWeight(_("Max Weight Amulets"),
            _("Amulet weight will be capped."),
            'amulets.maxWeight',
            (_('0.0'),0),
            (_('0.1'),0.1),
            (_('0.2'),0.2),
            (_('0.5'),0.5),
            ),
        ClothesTweak_MaxWeight(_("Max Weight Rings"),
            _('Ring weight will be capped.'),
            'rings.maxWeight',
            (_('0.0'),0),
            (_('0.1'),0.1),
            (_('0.2'),0.2),
            (_('0.5'),0.5),
            ),
        ClothesTweak_MaxWeight(_("Max Weight Hoods"),
            _('Hood weight will be capped.'),
            'hoods.maxWeight',
            (_('0.2'),0.2),
            (_('0.5'),0.5),
            (_('1.0'),1.0),
            ),
        ],key=lambda a: a.label.lower())

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (None,(MreClot,))[self.isActive]

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (None,(MreClot,))[self.isActive]

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        if not self.isActive or 'CLOT' not in modFile.tops: return
        mapper = modFile.getLongMapper()
        patchRecords = self.patchFile.CLOT
        id_records = patchRecords.id_records
        for record in modFile.CLOT.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            for tweak in self.enabledTweaks:
                if tweak.isMyType(record):
                    record = record.getTypeCopy(mapper)
                    patchRecords.setRecord(record)
                    break

    def buildPatch(self,log,progress):
        """Applies individual clothes tweaks."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        log.setHeader('= '+self.__class__.name)
        for tweak in self.enabledTweaks:
            tweak.buildPatch(self.patchFile,keep,log)

#------------------------------------------------------------------------------
class GmstTweak(MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def buildPatch(self,patchFile,keep,log):
        """Build patch."""
        eids = ((self.key,),self.key)[isinstance(self.key,tuple)]
        for eid,value in zip(eids,self.choiceValues[self.chosen]):
            gmst = MreGmst(('GMST',0,0,0,0))
            gmst.eid,gmst.value,gmst.longFids = eid,value,True
            fid = gmst.fid = keep(gmst.getOblivionFid())
            patchFile.GMST.setRecord(gmst)
        if len(self.choiceLabels) > 1:
            log('* %s: %s' % (self.label,self.choiceLabels[self.chosen]))
        else:
            log('* ' + self.label)

#------------------------------------------------------------------------------
class GmstTweaker(MultiTweaker):
    """Tweaks miscellaneous gmsts in miscellaneous ways."""
    name = _('Tweak Settings')
    text = _("Tweak game settings.")
    tweaks = sorted([
        GmstTweak(_('Arrow: Litter Count'),
            _("Maximum number of spent arrows allowed in cell."),
            'iArrowMaxRefCount',
            ('[15]',15),
            ('25',25),
            ('35',35),
            ('50',50),
            ('100',100),
            ('500',500),
            ),
        GmstTweak(_('Arrow: Litter Time'),
            _("Time before spent arrows fade away from cells and actors."),
            'fArrowAgeMax',
            (_('1 Minute'),60),
            (_('[1.5 Minutes]'),90),
            (_('2 Minutes'),120),
            (_('3 Minutes'),180),
            (_('5 Minutes'),300),
            (_('10 Minutes'),600),
            (_('30 Minutes'),1800),
            (_('1 Hour'),3600),
            ),
        GmstTweak(_('Arrow: Recovery from Actor'),
            _("Chance that an arrow shot into an actor can be recovered."),
            'iArrowInventoryChance',
            ('[50%]',50),
            ('60%',60),
            ('70%',70),
            ('80%',80),
            ('90%',90),
            ('100%',100),
            ),
        GmstTweak(_('Arrow: Speed'),
            _("Speed of full power arrow."),
            'fArrowSpeedMult',
            (_('x 1.2'),1500*1.2),
            (_('x 1.4'),1500*1.4),
            (_('x 1.6'),1500*1.6),
            (_('x 1.8'),1500*1.8),
            (_('x 2.0'),1500*2.0),
            (_('x 2.2'),1500*2.2),
            (_('x 2.4'),1500*2.4),
            (_('x 2.6'),1500*2.6),
            (_('x 2.8'),1500*2.8),
            (_('x 3.0'),1500*3.0),
            ),
        GmstTweak(_('Camera: Chase Tightness'),
            _("Tightness of chase camera to player turning."),
            ('fChase3rdPersonVanityXYMult','fChase3rdPersonXYMult'),
            (_('x 1.5'),6,6),
            (_('x 2.0'),8,8),
            (_('x 3.0'),12,12),
            (_('x 5.0'),20,20),
            ),
        GmstTweak(_('Camera: Chase Distance'),
            _("Distance camera can be moved away from PC using mouse wheel."),
            ('fVanityModeWheelMax', 'fChase3rdPersonZUnitsPerSecond','fVanityModeWheelMult'),
            (_('x 1.5'),600*1.5, 300*1.5,0.15),
            (_('x 2'),  600*2,   300*2, 0.2),
            (_('x 3'),  600*3,   300*3, 0.3),
            (_('x 5'),  600*5,   1000,  0.3),
            (_('x 10'), 600*10,  2000,  0.3),
            ),
        GmstTweak(_('Magic: Chameleon Refraction'),
            _("Chameleon with transparency instead of refraction effect."),
            ('fChameleonMinRefraction','fChameleonMaxRefraction'),
            ('Zero',0,0),
            ('[Normal]',0.01,1),
            ('Full',1,1),
            ),
        GmstTweak(_('Compass: Disable'),
            _("No quest and/or points of interest markers on compass."),
            'iMapMarkerRevealDistance',
            (_('Quests'),1803),
            (_('POIs'),1802),
            (_('Quests and POIs'),1801),
            ),
        GmstTweak(_('Compass: POI Recognition'),
            _("Distance at which POI markers begin to show on compass."),
            'iMapMarkerVisibleDistance',
            (_('x 0.25'),3000),
            (_('x 0.50'),6000),
            (_('x 0.75'),9000),
            ),
        GmstTweak(_('Essential NPC Unconsciousness'),
            _("Time which essential NPCs stay unconscious."),
            'fEssentialDeathTime',
            (_('[10 Seconds]'),20),
            (_('20 Seconds'),20),
            (_('30 Seconds'),30),
            (_('1 Minute'),60),
            (_('1 1/2 Minutes'),1.5*60),
            (_('2 Minutes'),2*60),
            (_('3 Minutes'),3*60),
            (_('5 Minutes'),5*60),
            ),
        GmstTweak(_('Fatigue from Running/Encumbrance'),
            _("Fatigue cost of running and encumbrance."),
            ('fFatigueRunBase','fFatigueRunMult'),
            ('x 1.5',12,6),
            ('x 2',16,8),
            ('x 3',24,12),
            ('x 4',32,16),
            ('x 5',40,20),
            ),
        GmstTweak(_('Horse Turning Speed'),
            _("Speed at which horses turn."),
            'iHorseTurnDegreesPerSecond',
            (_('x 1.5'),68),
            (_('x 2.0'),90),
            ),
        GmstTweak(_('Jump Higher'),
            _("Maximum height player can jump to."),
            'fJumpHeightMax',
            (_('x 1.1'),164*1.1),
            (_('x 1.2'),164*1.2),
            (_('x 1.4'),164*1.4),
            (_('x 1.6'),164*1.6),
            (_('x 1.8'),164*1.8),
            (_('x 2.0'),164*2),
            (_('x 3.0'),164*3),
            ),
        GmstTweak(_('Camera: PC Death Time'),
            _("Time after player's death before reload menu appears."),
            'fPlayerDeathReloadTime',
            (_('15 Seconds'),15),
            (_('30 Seconds'),30),
            (_('1 Minute'),60),
            (_('5 Minute'),300),
            (_('Unlimited'),9999999),
            ),
        GmstTweak(_('Cell Respawn Time'),
            _("Time before unvisited cell respawns. But longer times increase save sizes."),
            'iHoursToRespawnCell',
            (_('1 Day'),24*1),
            (_('[3 Days]'),24*3),
            (_('5 Days'),24*5),
            (_('10 Days'),24*10),
            (_('20 Days'),24*20),
            (_('1 Month'),24*30),
            (_('6 Months'),24*182),
            (_('1 Year'),24*365),
            ),
        GmstTweak(_('Combat: Recharge Weapons'),
            _("Allow recharging weapons during combat."),
            ('iAllowRechargeDuringCombat'),
            (_('[Allow]'),1),
            (_('Disallow'),0),
            ),
        GmstTweak(_('Magic: Bolt Speed'),
            _("Speed of magic bolt/projectile."),
            'fMagicProjectileBaseSpeed',
            (_('x 1.2'),1000*1.2),
            (_('x 1.4'),1000*1.4),
            (_('x 1.6'),1000*1.6),
            (_('x 1.8'),1000*1.8),
            (_('x 2.0'),1000*2.0),
            (_('x 2.2'),1000*2.2),
            (_('x 2.4'),1000*2.4),
            (_('x 2.6'),1000*2.6),
            (_('x 2.8'),1000*2.8),
            (_('x 3.0'),1000*3.0),
            ),
        GmstTweak(_('Msg: Equip Misc. Item'),
            _("Message upon equipping misc. item."),
            ('sCantEquipGeneric'),
            (_('[None]'),' '),
            (_('.'),'.'),
            (_('Hmm...'),_('Hmm...')),
            ),
        GmstTweak(_('Cost Multiplier: Repair'),
            _("Cost factor for repairing items."),
            ('fRepairCostMult'),
            ('0.1',0.1),
            ('0.2',0.2),
            ('0.3',0.3),
            ('0.4',0.4),
            ('0.5',0.5),
            ('0.6',0.6),
            ('0.7',0.7),
            ('0.8',0.8),
            ('[0.9]',0.9),
            ('1.0',1.0),
            ),
        GmstTweak(_('Greeting Distance'),
            _("Distance at which NPCs will greet the player. Default: 150"),
            ('fAIMinGreetingDistance'),
            ('100',100),
            ('125',125),
            ('[150]',150),
            ),
        GmstTweak(_('Cost Multiplier: Recharge'),
            _("Cost factor for recharging items."),
            ('fRechargeGoldMult'),
            ('0.1',0.1),
            ('0.2',0.2),
            ('0.3',0.3),
            ('0.5',0.5),
            ('0.7',0.7),
            ('1.0',1.0),
            ('1.5',1.5),
            ('[2.0]',2.0),
            ),
        GmstTweak(_('Master of Mercantile extra gold amount'),
            _("How much more barter gold all merchants have for a master of mercantile."),
            'iPerkExtraBarterGoldMaster',
            ('300',300),
            ('400',400),
            ('[500]',500),
            ('600',600),
            ('800',800),
            ('1000',1000),
            ),
        GmstTweak(_('Combat: Max Actors'),
            _("Maximum number of actors that can actively be in combat with the player."),
            'iNumberActorsInCombatPlayer',
            ('[10]',10),
            ('15',15),
            ('20',20),
            ('30',30),
            ('40',40),
            ('50',50),
            ),
        GmstTweak(_('Crime Alarm Distance'),
            _("Distance from player that NPCs(guards) will be alerted of a crime."),
            'iCrimeAlarmRecDistance',
            ('6000',6000),
            ('[4000]',4000),
            ('3000',3000),
            ('2000',2000),
            ('1000',1000),
            ('500',500),
            ),
        GmstTweak(_('Cost Multiplier: Enchantment'),
            _("Cost factor for enchanting items, OOO default is 120, vanilla 10."),
            'fEnchantmentGoldMult',
            ('[10]',10),
            ('20',20),
            ('30',30),
            ('50',50),
            ('70',70),
            ('90',90),
            ('120',120),
            ('150',150),
            ),
        GmstTweak(_('Cost Multiplier: Spell Making'),
            _("Cost factor for making spells."),
            'fSpellmakingGoldMult',
            ('[3]',3),
            ('5',5),
            ('8',8),
            ('10',10),
            ('15',15),
            ),
        GmstTweak(_('Magic: Max Player Summons'),
            _("Maximum number of creatures the player can summon."),
            'iMaxPlayerSummonedCreatures',
            ('[1]',1),
            ('3',3),
            ('5',5),
            ('8',8),
            ('10',10),
            ),
        GmstTweak(_('Magic: Max NPC Summons'),
            _("Maximum number of creatures that each NPC can summon"),
            'iAICombatMaxAllySummonCount',
            ('1',1),
            ('[3]',3),
            ('5',5),
            ('8',8),
            ('10',10),
            ('15',15),
            ),          
        GmstTweak(_('Bounty: Attack'),
            _("Bounty for attacking a 'good' npc."),
            'iCrimeGoldAttackMin',
            ('300',300),
            ('400',400),
            ('[500]',500),
            ('650',650),
            ('800',800),
            ),
        GmstTweak(_('Bounty: Horse Theft'),
            _("Bounty for horse theft"),
            'iCrimeGoldStealHorse',
            ('100',100),
            ('200',200),
            ('[250]',250),
            ('300',300),
            ('450',450),
            ),
        GmstTweak(_('Bounty: Theft'),
           _("Bounty for stealing, as fraction of item value."),
            'fCrimeGoldSteal',
            ('1/4',0.25),
            ('[1/2]',0.5),
            ('3/4',0.75),
            ('1',1),
            ),
        GmstTweak(_('Combat: Alchemy'),
            _("Allow alchemy during combat."),
            'iAllowAlchemyDuringCombat',
            ('Allow',1),
            ('[Disallow]',0),
            ),
        GmstTweak(_('Combat: Repair'),
            _("Allow repairing armor/weapons during combat."),
            'iAllowRepairDuringCombat',
            ('Allow',1),
            ('[Disallow]',0),
            ),
        GmstTweak(_('Companions: Max Number'),
            _("Maximum number of actors following the player"),
            'iNumberActorsAllowedToFollowPlayer',
            ('2',2),
            ('4',4),
            ('[6]',6),
            ('8',8),
            ('10',10),
            ),
        GmstTweak(_('Training Max'),
            _("Maximum number of Training allowed by trainers."),
            'iTrainingSkills',
            ('1',1),
            ('[5]',5),
            ('8',8),
            ('10',10),
            ('20',20),
            ('unlimited',9999),
            ),
        GmstTweak(_('Combat: Maximum Armor Rating'),
            _("The Maximun amount of protection you will get from armor."),
            'fMaxArmorRating',
            ('50',50),
            ('75',75),
            ('[85]',85),
            ('90',90),
            ('95',95),
            ),
        ],key=lambda a: a.label.lower())
    #--Patch Phase ------------------------------------------------------------
    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (None,(MreGmst,))[self.isActive]

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Will write to log."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        log.setHeader('= '+self.__class__.name)
        for tweak in self.enabledTweaks:
            tweak.buildPatch(self.patchFile,keep,log)

#------------------------------------------------------------------------------
class NamesTweak_BodyTags(MultiTweakItem):
    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        MultiTweakItem.__init__(self,_("Body Part Codes"),
            _('Sets body part codes used by Armor/Clothes name tweaks. A: Amulet, R: Ring, etc.'),
            'bodyTags',
            ('ARGHTCCPBS','ARGHTCCPBS'),
            ('ABGHINOPSL','ABGHINOPSL'),
            )

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return tuple()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return tuple()

    def scanModFile(self,modFile,progress,patchFile):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        return

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        patchFile.bodyTags = self.choiceValues[self.chosen][0]

#------------------------------------------------------------------------------
class NamesTweak_Body(MultiTweakItem):
    """Names tweaker for armor and clothes."""

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreRecord.type_class[self.key],)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreRecord.type_class[self.key],)

    def scanModFile(self,modFile,progress,patchFile):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        mapper = modFile.getLongMapper()
        patchBlock = getattr(patchFile,self.key)
        id_records = patchBlock.id_records
        for record in getattr(modFile,self.key).getActiveRecords():
            if record.full and mapper(record.fid) not in id_records:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        format = self.choiceValues[self.chosen][0]
        showStat = '%02d' in format
        keep = patchFile.getKeeper()
        codes = getattr(patchFile,'bodyTags','ARGHTCCPBS')
        amulet,ring,gloves,head,tail,robe,chest,pants,shoes,shield = [
            x for x in codes]
        for record in getattr(patchFile,self.key).records:
            if not record.full: continue
            if record.full[0] in '+-=.()[]': continue
            flags = record.flags
            if flags.head or flags.hair: type = head
            elif flags.rightRing or flags.leftRing: type = ring
            elif flags.amulet: type = amulet
            elif flags.upperBody and flags.lowerBody: type = robe
            elif flags.upperBody: type = chest
            elif flags.lowerBody: type = pants
            elif flags.hand: type = gloves
            elif flags.foot: type = shoes
            elif flags.tail: type = tail
            elif flags.shield: type = shield
            else: continue
            if record.recType == 'ARMO':
                type += 'LH'[record.flags.heavyArmor]
            if showStat:
                record.full = format % (type,record.strength/100) + record.full
            else:
                record.full = format % type + record.full
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log(_('* %s: %d') % (self.label,sum(count.values())))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))

#------------------------------------------------------------------------------
class NamesTweak_Potions(MultiTweakItem):
    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        MultiTweakItem.__init__(self,_("Potions"),
            _('Label potions to sort by type and effect.'),
            'ALCH',
            (_('XD Illness'),  '%s '),
            (_('XD. Illness'), '%s. '),
            (_('XD - Illness'),'%s - '),
            (_('(XD) Illness'),'(%s) '),
            )

    #--Config Phase -----------------------------------------------------------
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreAlch,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreAlch,)

    def scanModFile(self,modFile,progress,patchFile):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.ALCH
        id_records = patchBlock.id_records
        for record in modFile.ALCH.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            record = record.getTypeCopy(mapper)
            patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        format = self.choiceValues[self.chosen][0]
        poisonEffects = bush.poisonEffects
        keep = patchFile.getKeeper()
        reOldLabel = re.compile('^(-|X) ')
        reOldEnd = re.compile(' -$')
        mgef_school = patchFile.getMgefSchool()
        for record in patchFile.ALCH.records:
            if not record.full: continue
            school = 6 #--Default to 6 (U: unknown)
            for index,effect in enumerate(record.effects):
                effectId = effect.name
                if index == 0:
                    if effect.scriptEffect:
                        school = effect.scriptEffect.school
                    else:
                        school = mgef_school.get(effectId,6)
                #--Non-hostile effect?
                if effect.scriptEffect:
                    if not effect.scriptEffect.flags.hostile:
                        isPoison = False
                        break
                elif effectId not in poisonEffects:
                    isPoison = False
                    break
            else:
                isPoison = True
            full = reOldLabel.sub('',record.full) #--Remove existing label
            full = reOldEnd.sub('',full)
            if record.flags.isFood:
                record.full = '.'+full
            else:
                label = ('','X')[isPoison] + 'ACDIMRU'[school]
                record.full = format % label + full
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log(_('* %s: %d') % (self.label,sum(count.values())))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))

#------------------------------------------------------------------------------
class NamesTweak_Scrolls(MultiTweakItem):
    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        MultiTweakItem.__init__(self,_("Notes and Scrolls"),
            _('Mark notes and scrolls to sort separately from books'),
            'scrolls',
            (_('~Fire Ball'),  '~'),
            (_('~D Fire Ball'),  '~%s '),
            (_('~D. Fire Ball'), '~%s. '),
            (_('~D - Fire Ball'),'~%s - '),
            (_('~(D) Fire Ball'),'~(%s) '),
            ('----','----'),
            (_('.Fire Ball'),  '.'),
            (_('.D Fire Ball'),  '.%s '),
            (_('.D. Fire Ball'), '.%s. '),
            (_('.D - Fire Ball'),'.%s - '),
            (_('.(D) Fire Ball'),'.(%s) '),
            )

    #--Config Phase -----------------------------------------------------------
    def saveConfig(self,configs):
        """Save config to configs dictionary."""
        MultiTweakItem.saveConfig(self,configs)
        rawFormat = self.choiceValues[self.chosen][0]
        self.orderFormat = ('~.','.~')[rawFormat[0] == '~']
        self.magicFormat = rawFormat[1:]

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreBook,MreEnch,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreBook,MreEnch)

    def scanModFile(self,modFile,progress,patchFile):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        mapper = modFile.getLongMapper()
        #--Scroll Enchantments
        if self.magicFormat:
            patchBlock = patchFile.ENCH
            id_records = patchBlock.id_records
            for record in modFile.ENCH.getActiveRecords():
                if mapper(record.fid) in id_records: continue
                if record.itemType == 0:
                    record = record.getTypeCopy(mapper)
                    patchBlock.setRecord(record)
        #--Books
        patchBlock = patchFile.BOOK
        id_records = patchBlock.id_records
        for record in modFile.BOOK.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.flags.isScroll and not record.flags.isFixed:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        reOldLabel = re.compile('^(\([ACDIMR]\d\)|\w{3,6}:) ')
        orderFormat, magicFormat = self.orderFormat, self.magicFormat
        keep = patchFile.getKeeper()
        id_ench = patchFile.ENCH.id_records
        mgef_school = patchFile.getMgefSchool()
        for record in patchFile.BOOK.records:
            if not record.full or not record.flags.isScroll or record.flags.isFixed: continue
            #--Magic label
            isEnchanted = bool(record.enchantment)
            if magicFormat and isEnchanted:
                school = 6 #--Default to 6 (U: unknown)
                enchantment = id_ench.get(record.enchantment)
                if enchantment and enchantment.effects:
                    effect = enchantment.effects[0]
                    effectId = effect.name
                    if effect.scriptEffect:
                        school = effect.scriptEffect.school
                    else:
                        school = mgef_school.get(effectId,6)
                record.full = reOldLabel.sub('',record.full) #--Remove existing label
                record.full = magicFormat % 'ACDIMRU'[school] + record.full
            #--Ordering
            record.full = orderFormat[isEnchanted] + record.full
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log(_('* %s: %d') % (self.label,sum(count.values())))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))

#------------------------------------------------------------------------------
class NamesTweak_Spells(MultiTweakItem):
    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        MultiTweakItem.__init__(self,_("Spells"),
            _('Label spells to sort by school and level.'),
            'SPEL',
            (_('Fire Ball'),  'NOTAGS'),
            ('----','----'),
            (_('D Fire Ball'),  '%s '),
            (_('D. Fire Ball'), '%s. '),
            (_('D - Fire Ball'),'%s - '),
            (_('(D) Fire Ball'),'(%s) '),
            ('----','----'),
            (_('D2 Fire Ball'),  '%s%d '),
            (_('D2. Fire Ball'), '%s%d. '),
            (_('D2 - Fire Ball'),'%s%d - '),
            (_('(D2) Fire Ball'),'(%s%d) '),
            )

    #--Config Phase -----------------------------------------------------------
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreSpel,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreSpel,)

    def scanModFile(self,modFile,progress,patchFile):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.SPEL
        id_records = patchBlock.id_records
        for record in modFile.SPEL.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.spellType == 0:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        format = self.choiceValues[self.chosen][0]
        removeTags = '%s' not in format
        showLevel = '%d' in format
        keep = patchFile.getKeeper()
        reOldLabel = re.compile('^(\([ACDIMR]\d\)|\w{3,6}:) ')
        mgef_school = patchFile.getMgefSchool()
        for record in patchFile.SPEL.records:
            if record.spellType != 0 or not record.full: continue
            school = 6 #--Default to 6 (U: unknown)
            if record.effects:
                effect = record.effects[0]
                effectId = effect.name
                if effect.scriptEffect:
                    school = effect.scriptEffect.school
                else:
                    school = mgef_school.get(effectId,6)
            newFull = reOldLabel.sub('',record.full) #--Remove existing label
            if not removeTags:
                if showLevel:
                    newFull = format % ('ACDIMRU'[school],record.level) + newFull
                else:
                    newFull = format % 'ACDIMRU'[school] + newFull
            if newFull != record.full:
                record.full = newFull
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log(_('* %s: %d') % (self.label,sum(count.values())))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))

#------------------------------------------------------------------------------
class NamesTweak_Weapons(MultiTweakItem):
    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        MultiTweakItem.__init__(self,_("Weapons"),
            _('Label ammo and weapons to sort by type and damage.'),
            'WEAP',
            (_('B Iron Bow'),  '%s '),
            (_('B. Iron Bow'), '%s. '),
            (_('B - Iron Bow'),'%s - '),
            (_('(B) Iron Bow'),'(%s) '),
            ('----','----'),
            (_('B08 Iron Bow'),  '%s%02d '),
            (_('B08. Iron Bow'), '%s%02d. '),
            (_('B08 - Iron Bow'),'%s%02d - '),
            (_('(B08) Iron Bow'),'(%s%02d) '),
            )

    #--Config Phase -----------------------------------------------------------
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreAmmo,MreWeap)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreAmmo,MreWeap)

    def scanModFile(self,modFile,progress,patchFile):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        mapper = modFile.getLongMapper()
        for blockType in ('AMMO','WEAP'):
            modBlock = getattr(modFile,blockType)
            patchBlock = getattr(patchFile,blockType)
            id_records = patchBlock.id_records
            for record in modBlock.getActiveRecords():
                if mapper(record.fid) not in id_records:
                    record = record.getTypeCopy(mapper)
                    patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        format = self.choiceValues[self.chosen][0]
        showStat = '%02d' in format
        keep = patchFile.getKeeper()
        for record in patchFile.AMMO.records:
            if not record.full: continue
            if record.full[0] in '+-=.()[]': continue
            if showStat:
                record.full = format % ('A',record.damage) + record.full
            else:
                record.full = format % 'A' + record.full
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1
        for record in patchFile.WEAP.records:
            if not record.full: continue
            if showStat:
                record.full = format % ('CDEFGB'[record.weaponType],record.damage) + record.full
            else:
                record.full = format % 'CDEFGB'[record.weaponType] + record.full
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log(_('* %s: %d') % (self.label,sum(count.values())))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))

#------------------------------------------------------------------------------
class NamesTweaker(MultiTweaker):
    """Tweaks record full names in various ways."""
    scanOrder = 32
    editOrder = 32
    name = _('Tweak Names')
    text = _("Tweak object names to show type and/or quality.")
    tweaks = sorted([
        NamesTweak_Body(_("Armor"),_("Rename armor to sort by type."),'ARMO',
            (_('BL Leather Boots'),  '%s '),
            (_('BL. Leather Boots'), '%s. '),
            (_('BL - Leather Boots'),'%s - '),
            (_('(BL) Leather Boots'),'(%s) '),
            ('----','----'),
            (_('BL02 Leather Boots'),  '%s%02d '),
            (_('BL02. Leather Boots'), '%s%02d. '),
            (_('BL02 - Leather Boots'),'%s%02d - '),
            (_('(BL02) Leather Boots'),'(%s%02d) '),
            ),
        NamesTweak_Body(_("Clothes"),_("Rename clothes to sort by type."),'CLOT',
            (_('P Grey Trowsers'),  '%s '),
            (_('P. Grey Trowsers'), '%s. '),
            (_('P - Grey Trowsers'),'%s - '),
            (_('(P) Grey Trowsers'),'(%s) '),
            ),
        NamesTweak_Potions(),
        NamesTweak_Scrolls(),
        NamesTweak_Spells(),
        NamesTweak_Weapons(),
        ],key=lambda a: a.label.lower())
    tweaks.insert(0,NamesTweak_BodyTags())

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return None
        classTuples = [tweak.getReadClasses() for tweak in self.enabledTweaks]
        return sum(classTuples,tuple())

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return None
        classTuples = [tweak.getWriteClasses() for tweak in self.enabledTweaks]
        return sum(classTuples,tuple())

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        if not self.isActive: return
        for tweak in self.enabledTweaks:
            tweak.scanModFile(modFile,progress,self.patchFile)

    def buildPatch(self,log,progress):
        """Applies individual clothes tweaks."""
        if not self.isActive: return
        log.setHeader('= '+self.__class__.name,True)
        for tweak in self.enabledTweaks:
            tweak.buildPatch(log,progress,self.patchFile)

# Patchers: 40 ----------------------------------------------------------------
class SpecialPatcher:
    """Provides default group, scan and edit orders."""
    group = _('Special')
    scanOrder = 40
    editOrder = 40

#------------------------------------------------------------------------------
class AlchemicalCatalogs(SpecialPatcher,Patcher):
    """Updates COBL alchemical catalogs."""
    name = _('Cobl Catalogs')
    text = _("Update COBL's catalogs of alchemical ingredients and effects.\n\nWill only run if Cobl Main.esm is loaded.")

    #--Config Phase -----------------------------------------------------------
    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.isActive = (GPath('COBL Main.esm') in loadMods)
        self.id_ingred = {}

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return tuple()
        return (MreIngr,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return tuple()
        return (MreBook,)

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        if not self.isActive: return
        id_ingred = self.id_ingred
        mapper = modFile.getLongMapper()
        for record in modFile.INGR.getActiveRecords():
            if not record.full: continue #--Ingredient must have name!
            effects = record.getEffects()
            if not ('SEFF',0) in effects:
                id_ingred[mapper(record.fid)] = (record.eid, record.full, effects)

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Will write to log."""
        if not self.isActive: return
        #--Setup
        mgef_name = self.patchFile.getMgefName()
        for mgef in mgef_name:
            mgef_name[mgef] = re.sub(_('(Attribute|Skill)'),'',mgef_name[mgef])
        actorEffects = bush.actorValueEffects
        actorNames = bush.actorValues
        keep = self.patchFile.getKeeper()
        #--Book generatator
        def getBook(objectId,eid,full,value,iconPath,modelPath,modb_p):
            book = MreBook(('BOOK',0,0,0,0))
            book.longFids = True
            book.changed = True
            book.eid = eid
            book.full = full
            book.value = value
            book.weight = 0.2
            book.fid = keep((GPath('Cobl Main.esm'),objectId))
            book.text = '<div align="left"><font face=3 color=4444>'
            book.text += _("Salan's Catalog of %s\r\n\r\n") % full
            book.iconPath = iconPath
            book.model = book.getDefault('model')
            book.model.modPath = modelPath
            book.model.modb_p = modb_p
            book.modb = book
            self.patchFile.BOOK.setRecord(book)
            return book
        #--Ingredients Catalog
        id_ingred = self.id_ingred
        iconPath,modPath,modb_p = ('Clutter\IconBook9.dds','Clutter\Books\Octavo02.NIF','\x03>@A')
        for (num,objectId,full,value) in bush.ingred_alchem:
            book = getBook(objectId,'cobCatAlchemIngreds'+`num`,full,value,iconPath,modPath,modb_p)
            buff = cStringIO.StringIO()
            buff.write(book.text)
            for eid,full,effects in sorted(id_ingred.values(),key=lambda a: a[1].lower()):
                buff.write(full+'\r\n')
                for mgef,actorValue in effects[:num]:
                    effectName = mgef_name[mgef]
                    if mgef in actorEffects: effectName += actorNames[actorValue]
                    buff.write('  '+effectName+'\r\n')
                buff.write('\r\n')
            book.text = re.sub('\r\n','<br>\r\n',buff.getvalue())
        #--Get Ingredients by Effect
        effect_ingred = {}
        for fid,(eid,full,effects) in id_ingred.iteritems():
            for index,(mgef,actorValue) in enumerate(effects):
                effectName = mgef_name[mgef]
                if mgef in actorEffects: effectName += actorNames[actorValue]
                if effectName not in effect_ingred: effect_ingred[effectName] = []
                effect_ingred[effectName].append((index,full))
        #--Effect catalogs
        iconPath,modPath,modb_p = ('Clutter\IconBook7.dds','Clutter\Books\Octavo01.NIF','\x03>@A')
        for (num,objectId,full,value) in bush.effect_alchem:
            book = getBook(objectId,'cobCatAlchemEffects'+`num`,full,value,iconPath,modPath,modb_p)
            buff = cStringIO.StringIO()
            buff.write(book.text)
            for effectName in sorted(effect_ingred.keys()):
                effects = [indexFull for indexFull in effect_ingred[effectName] if indexFull[0] < num]
                if effects:
                    buff.write(effectName+'\r\n')
                    for (index,full) in sorted(effects,key=lambda a: a[1].lower()):
                        exSpace = ('',' ')[index == 0]
                        buff.write(' '+`index + 1`+exSpace+' '+full+'\r\n')
                    buff.write('\r\n')
            book.text = re.sub('\r\n','<br>\r\n',buff.getvalue())
        #--Log
        log.setHeader('= '+self.__class__.name)
        log(_('* Ingredients Cataloged: %d') % (len(id_ingred),))
        log(_('* Effects Cataloged: %d') % (len(effect_ingred)))

#------------------------------------------------------------------------------
class CoblExhaustion(SpecialPatcher,ListPatcher):
    """Modifies most Greater power to work with Cobl's power exhaustion feature."""
    name = _('Cobl Exhaustion')
    text = _("Modify greater powers to use Cobl's Power Exhaustion feature.\n\nWill only run if Cobl Main v1.66 (or higher) is active.")
    autoKey = 'Exhaust'
    defaultItemCheck = False #--GUI: Whether new items are checked by default or not.

    #--Config Phase -----------------------------------------------------------
    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.cobl = GPath('Cobl Main.esm')
        self.srcFiles = self.getConfigChecked()
        self.isActive = bool(self.srcFiles) and (self.cobl in loadMods and modInfos.getVersionFloat(self.cobl) > 1.65)
        self.id_exhaustion = {}

    def readFromText(self,textPath):
        """Imports type_id_name from specified text file."""
        aliases = self.patchFile.aliases
        id_exhaustion = self.id_exhaustion
        textPath = GPath(textPath)
        ins = bolt.CsvReader(textPath)
        reNum = re.compile(r'\d+')
        for fields in ins:
            if len(fields) < 4 or fields[1][:2] != '0x' or not reNum.match(fields[3]): continue
            mod,objectIndex,eid,time = fields[:4]
            mod = GPath(mod)
            longid = (aliases.get(mod,mod),int(objectIndex[2:],16))
            id_exhaustion[longid] = int(time)
        ins.close()

    def initData(self,progress):
        """Get names from source files."""
        if not self.isActive: return
        progress.setFull(len(self.srcFiles))
        for srcFile in self.srcFiles:
            srcPath = GPath(srcFile)
            patchesDir = dirs['patches'].list()
            if srcPath not in patchesDir: continue
            self.readFromText(dirs['patches'].join(srcFile))
            progress.plus()

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return tuple()
        return (MreSpel,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return tuple()
        return (MreSpel,)

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        if not self.isActive: return
        mapper = modFile.getLongMapper()
        patchRecords = self.patchFile.SPEL
        for record in modFile.SPEL.getActiveRecords():
            if not record.spellType == 2: continue
            record = record.getTypeCopy(mapper)
            if record.fid in self.id_exhaustion:
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Will write to log."""
        if not self.isActive: return
        count = {}
        exhaustId = (self.cobl,0x05139B)
        keep = self.patchFile.getKeeper()
        for record in self.patchFile.SPEL.records:
            #--Skip this one?
            duration = self.id_exhaustion.get(record.fid,0)
            if not (duration and record.spellType == 2): continue
            isExhausted = False
            for effect in record.effects:
                if effect.name == 'SEFF' and effect.scriptEffect.script == exhaustId:
                    duration = 0
                    break
            if not duration: continue
            #--Okay, do it
            record.full = '+'+record.full
            record.spellType = 3 #--Lesser power
            effect = record.getDefault('effects')
            effect.name = 'SEFF'
            effect.duration = duration
            scriptEffect = record.getDefault('effects.scriptEffect')
            scriptEffect.full = _("Power Exhaustion")
            scriptEffect.script = exhaustId
            scriptEffect.school = 2
            scriptEffect.visual = '\x00\x00\x00\x00'
            scriptEffect.flags.hostile = False
            effect.scriptEffect = scriptEffect
            record.effects.append(effect)
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log.setHeader('= '+self.__class__.name)
        log(_('* Powers Tweaked: %d') % (sum(count.values()),))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))

#------------------------------------------------------------------------------
class ListsMerger(SpecialPatcher,ListPatcher):
    """Merged leveled lists mod file."""
    scanOrder = 45
    editOrder = 45
    name = _('Leveled Lists')
    text = _("Merges changes to leveled lists from ACTIVE/MERGED MODS ONLY.\n\nAdvanced users may override Relev/Delev tags for any mod (active or inactive) using the list below.")
    tip = _("Merges changes to leveled lists from all active mods.")
    choiceMenu = ('Auto','----','Delev','Relev') #--List of possible choices for each config item. Item 0 is default.
    autoKey = ('Delev','Relev')
    forceAuto = False
    forceItemCheck = True #--Force configChecked to True for all items
    iiMode = True

    #--Static------------------------------------------------------------------
    @staticmethod
    def getDefaultTags():
        tags = {}
        for fileName in ('Leveled Lists.csv','My Leveled Lists.csv'):
            textPath = dirs['patches'].join(fileName)
            if textPath.exists():
                reader = bolt.CsvReader(textPath)
                for fields in reader:
                    if len(fields) < 2 or not fields[0] or fields[1] not in ('DR','R','D','RD',''): continue
                    tags[GPath(fields[0])] = fields[1]
                reader.close()
        return tags

    #--Config Phase -----------------------------------------------------------
    def getChoice(self,item):
        """Get default config choice."""
        choice = self.configChoices.get(item)
        if not isinstance(choice,set): choice = set(('Auto',))
        if 'Auto' in choice:
            if item in modInfos:
                choice = set(('Auto',))
                bashTags = modInfos[item].getBashTags()
                for key in ('Delev','Relev'):
                    if key in bashTags: choice.add(key)
        self.configChoices[item] = choice
        return choice

    def getItemLabel(self,item):
        """Returns label for item to be used in list"""
        choice = map(itemgetter(0),self.configChoices.get(item,tuple()))
        if isinstance(item,bolt.Path): item = item.s
        if choice:
            return '%s [%s]' % (item,''.join(sorted(choice)))
        else:
            return item

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.listTypes = ('LVLC','LVLI','LVSP')
        self.type_list = dict([(type,{}) for type in self.listTypes])
        self.masterItems = {}
        self.mastersScanned = set()
        self.levelers = None #--Will initialize later

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreLvlc,MreLvli,MreLvsp)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreLvlc,MreLvli,MreLvsp)

    def scanModFile(self, modFile, progress):
        """Add lists from modFile."""
        #--Level Masters (complete initialization)
        if self.levelers == None:
            allMods = set(self.patchFile.allMods)
            self.levelers = [leveler for leveler in self.getConfigChecked() if leveler in allMods]
            self.delevMasters = set()
            for leveler in self.levelers:
                self.delevMasters.update(modInfos[leveler].header.masters)
        #--Begin regular scan
        modName = modFile.fileInfo.name
        modFile.convertToLongFids(self.listTypes)
        #--PreScan for later Relevs/Delevs?
        if modName in self.delevMasters:
            for type in self.listTypes:
                for levList in getattr(modFile,type).getActiveRecords():
                    masterItems = self.masterItems.setdefault(levList.fid,{})
                    masterItems[modName] = set([entry.listId for entry in levList.entries])
            self.mastersScanned.add(modName)
        #--Relev/Delev setup
        configChoice = self.configChoices.get(modName,tuple())
        isRelev = ('Relev' in configChoice)
        isDelev = ('Delev' in configChoice)
        #--Scan
        for type in self.listTypes:
            levLists = self.type_list[type]
            newLevLists = getattr(modFile,type)
            for newLevList in newLevLists.getActiveRecords():
                listId = newLevList.fid
                isListOwner = (listId[0] == modName)
                #--Items, delevs and relevs sets
                newLevList.items = items = set([entry.listId for entry in newLevList.entries])
                if not isListOwner:
                    #--Relevs
                    newLevList.relevs = (set(),items.copy())[isRelev]
                    #--Delevs: all items in masters minus current items
                    newLevList.delevs = delevs = set()
                    if isDelev:
                        id_masterItems = self.masterItems.get(newLevList.fid)
                        if id_masterItems:
                            for masterName in modFile.tes4.masters:
                                if masterName in id_masterItems:
                                    delevs |= id_masterItems[masterName]
                            delevs -= items
                            newLevList.items |= delevs
                #--Cache/Merge
                if isListOwner:
                    levList = copy.deepcopy(newLevList)
                    levList.mergeSources = []
                    levLists[listId] = levList
                elif listId not in levLists:
                    levList = copy.deepcopy(newLevList)
                    levList.mergeSources = [modName]
                    levLists[listId] = levList
                else:
                    levLists[listId].mergeWith(newLevList,modName)

    def buildPatch(self,log,progress):
        """Adds merged lists to patchfile."""
        keep = self.patchFile.getKeeper()
        #--Relevs/Delevs List
        log.setHeader('= '+self.__class__.name,True)
        log.setHeader(_('=== Delevelers/Relevelers'))
        for leveler in (self.levelers or []):
            log('* '+self.getItemLabel(leveler))
        #--Save to patch file
        for label, type in ((_('Creature'),'LVLC'), (_('Item'),'LVLI'), (_('Spell'),'LVSP')):
            log.setHeader(_('=== Merged %s Lists') % label)
            patchBlock = getattr(self.patchFile,type)
            levLists = self.type_list[type]
            for record in sorted(levLists.values(),key=attrgetter('eid')):
                if not record.mergeOverLast: continue
                fid = keep(record.fid)
                patchBlock.setRecord(levLists[fid])
                log('* '+record.eid)
                for mod in record.mergeSources:
                    log('  * ' + self.getItemLabel(mod))
        #--Discard empty sublists
        for label, type in ((_('Creature'),'LVLC'), (_('Item'),'LVLI'), (_('Spell'),'LVSP')):
            patchBlock = getattr(self.patchFile,type)
            levLists = self.type_list[type]
            #--Empty lists
            empties = []
            sub_supers = dict((x,[]) for x in levLists.keys())
            for record in sorted(levLists.values()):
                listId = record.fid
                if not record.items:
                    empties.append(listId)
                else:
                    subLists = [x for x in record.items if x in sub_supers]
                    for subList in subLists:
                        sub_supers[subList].append(listId)
            #--Clear empties
            removed = set()
            cleaned = set()
            while empties:
                empty = empties.pop()
                if empty not in sub_supers: continue
                for super in sub_supers[empty]:
                    record = levLists[super]
                    record.entries = [x for x in record.entries if x.listId != empty]
                    record.items.remove(empty)
                    patchBlock.setRecord(record)
                    if not record.items:
                        empties.append(super)
                    cleaned.add(record.eid)
                    removed.add(levLists[empty].eid)
                    keep(super)
            log.setHeader(_('=== Empty %s Sublists') % label)
            for eid in sorted(removed,key=string.lower):
                log('* '+eid)
            log.setHeader(_('=== Empty %s Sublists Removed') % label)
            for eid in sorted(cleaned,key=string.lower):
                log('* '+eid)

#------------------------------------------------------------------------------
class MFactMarker(SpecialPatcher,ListPatcher):
    """Mark factions that player can acquire while morphing."""
    name = _('Morph Factions')
    text = _("Mark factions that player can acquire while morphing.\n\nRequires Cobl 2.18 and Wrye Morph or similar.")
    autoRe = re.compile(r"^UNDEFINED$",re.I)
    autoKey = 'MFact'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_info = {} #--Morphable factions keyed by fid
        self.srcFiles = self.getConfigChecked()
        self.isActive = bool(self.srcFiles) and GPath("Cobl Main.esm") in modInfos.ordered
        self.mFactLong = (GPath("Cobl Main.esm"),0x33FB)

    def initData(self,progress):
        """Get names from source files."""
        if not self.isActive: return
        aliases = self.patchFile.aliases
        id_info = self.id_info
        for srcFile in self.srcFiles:
            textPath = dirs['patches'].join(srcFile)
            if not textPath.exists(): continue
            ins = bolt.CsvReader(textPath)
            for fields in ins:
                if len(fields) < 6 or fields[1][:2] != '0x':
                    continue
                mod,objectIndex = fields[:2]
                mod = GPath(mod)
                longid = (aliases.get(mod,mod),int(objectIndex,0))
                morphName = fields[4].strip()
                rankName = fields[5].strip()
                if not morphName: continue
                if not rankName: rankName = _('Member')
                id_info[longid] = (morphName,rankName)
            ins.close()

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (None,(MreFact,))[self.isActive]

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (None,(MreFact,))[self.isActive]

    def scanModFile(self, modFile, progress):
        """Scan modFile."""
        if not self.isActive: return
        id_info = self.id_info
        modName = modFile.fileInfo.name
        mapper = modFile.getLongMapper()
        patchBlock = self.patchFile.FACT
        if modFile.fileInfo.name == GPath("Cobl Main.esm"):
            modFile.convertToLongFids(('FACT',))
            record = modFile.FACT.getRecord(self.mFactLong)
            if record:
                patchBlock.setRecord(record.getTypeCopy())
        for record in modFile.FACT.getActiveRecords():
            fid = record.fid
            if not record.longFids: fid = mapper(fid)
            if fid in id_info:
                patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress):
        """Make changes to patchfile."""
        if not self.isActive: return
        mFactLong = self.mFactLong
        id_info = self.id_info
        modFile = self.patchFile
        keep = self.patchFile.getKeeper()
        changed = {}
        mFactable = []
        for record in modFile.FACT.getActiveRecords():
            if record.fid not in id_info: continue
            if record.fid == mFactLong: continue
            mFactable.append(record.fid)
            #--Update record if it doesn't have an existing relation with mFactLong
            if mFactLong not in [relation.faction for relation in record.relations]:
                record.flags.hiddenFromPC = False
                relation = record.getDefault('relations')
                relation.faction = mFactLong
                relation.mod = 10
                record.relations.append(relation)
                mname,rankName = id_info[record.fid]
                record.full = mname
                if not record.ranks:
                    record.ranks = [record.getDefault('ranks')]
                for rank in record.ranks:
                    if not rank.male: rank.male = rankName
                    if not rank.female: rank.female = rank.male
                    if not rank.insigniaPath:
                        rank.insigniaPath = r'Menus\Stats\Cobl\generic%02d.dds' % rank.rank
                keep(record.fid)
                mod = record.fid[0]
                changed[mod] = changed.setdefault(mod,0) + 1
        #--MFact record
        record = modFile.FACT.getRecord(mFactLong)
        if record:
            relations = record.relations
            del relations[:]
            for faction in mFactable:
                relation = record.getDefault('relations')
                relation.faction = faction
                relation.mod = 10
                relations.append(relation)
            keep(record.fid)
        log.setHeader('= '+self.__class__.name)
        log(_("=== Source Mods/Files"))
        for file in self.srcFiles:
            log("* " +file.s)
        log(_("\n=== Morphable Factions"))
        for mod in sorted(changed):
            log("* %s: %d" % (mod.s,changed[mod]))

#------------------------------------------------------------------------------
class PowerExhaustion(SpecialPatcher,Patcher):
    """Modifies most Greater power to work with Wrye's Power Exhaustion mod."""
    name = _('Power Exhaustion')
    text = _("Modify greater powers to work with Power Exhaustion mod.\n\nWill only run if Power Exhaustion mod is installed and active.")

    #--Config Phase -----------------------------------------------------------
    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.isActive = (GPath('Power Exhaustion.esp') in loadMods)
        self.id_exhaustion = bush.id_exhaustion

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return tuple()
        return (MreSpel,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return tuple()
        return (MreSpel,)

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        if not self.isActive: return
        mapper = modFile.getLongMapper()
        patchRecords = self.patchFile.SPEL
        for record in modFile.SPEL.getActiveRecords():
            if not record.spellType == 2: continue
            record = record.getTypeCopy(mapper)
            if record.fid in self.id_exhaustion or ('FOAT',5) in record.getEffects():
                patchRecords.setRecord(record)
                continue

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Will write to log."""
        if not self.isActive: return
        count = {}
        exhaustId = (GPath('Power Exhaustion.esp'),0xCE7)
        keep = self.patchFile.getKeeper()
        for record in self.patchFile.SPEL.records:
            #--Skip this one?
            if record.spellType != 2: continue
            if record.fid not in self.id_exhaustion and ('FOAT',5) not in record.getEffects():
                continue
            newEffects = []
            duration = self.id_exhaustion.get(record.fid,0)
            for effect in record.effects:
                if effect.name == 'FOAT' and effect.actorValue == 5 and effect.magnitude == 1:
                    duration = effect.duration
                else:
                    newEffects.append(effect)
            if not duration: continue
            record.effects = newEffects
            #--Okay, do it
            record.full = '+'+record.full
            record.spellType = 3 #--Lesser power
            effect = record.getDefault('effects')
            effect.name = 'SEFF'
            effect.duration = duration
            scriptEffect = record.getDefault('effects.scriptEffect')
            scriptEffect.full = _("Power Exhaustion")
            scriptEffect.name = exhaustId
            scriptEffect.school = 2
            scriptEffect.visual = '\x00\x00\x00\x00'
            scriptEffect.flags.hostile = False
            effect.scriptEffect = scriptEffect
            record.effects.append(effect)
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log.setHeader(_('= Power Exhaustion'))
        log(_('* Powers Tweaked: %d') % (sum(count.values()),))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))

#------------------------------------------------------------------------------
class RacePatcher(SpecialPatcher,ListPatcher):
    """Merged leveled lists mod file."""
    name = _('Race Records')
    text = _("Merge race eyes, hair, body, voice from ACTIVE AND/OR MERGED mods. Any non-active, non-merged mods in the following list will be IGNORED.")
    tip = _("Merge race eyes, hair, body, voice from mods.")
    autoRe = re.compile(r"^UNDEFINED$",re.I)
    autoKey = ('Hair','Eyes-D','Eyes-R','Eyes-E','Eyes','Body-M','Body-F',
        'Voice-M','Voice-F','R.Relations','R.Teeth','R.Mouth')
    forceAuto = True

    #--Config Phase -----------------------------------------------------------
    def getAutoItems(self):
        """Returns list of items to be used for automatic configuration."""
        autoItems = []
        autoRe = self.__class__.autoRe
        autoKey = set(self.__class__.autoKey)
        for modInfo in modInfos.data.values():
            if autoRe.match(modInfo.name.s) or (autoKey & set(modInfo.getBashTags())):
                autoItems.append(modInfo.name)
        return autoItems

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.raceData = {} #--Race eye meshes, hair,eyes
        #--Restrict srcMods to active/merged mods.
        self.srcMods = [x for x in self.getConfigChecked() if x in patchFile.allSet]
        self.isActive = True #--Always enabled to support eye filtering
        self.bodyKeys = ('Height','Weight','TailModel','UpperBodyPath','LowerBodyPath','HandPath','FootPath','TailPath')
        self.eyeKeys = set(('Eyes-D','Eyes-R','Eyes-E','Eyes'))
        #--Mesh tuple for each defined eye. Derived from race records.
        defaultMesh = (r'characters\imperial\eyerighthuman.nif', r'characters\imperial\eyelefthuman.nif')
        self.eye_mesh = {}
        self.scanTypes = set(('RACE','EYES','HAIR','NPC_'))

    def initData(self,progress):
        """Get data from source files."""
        if not self.isActive or not self.srcMods: return
        loadFactory = LoadFactory(False,MreRace)
        progress.setFull(len(self.srcMods))
        for index,srcMod in enumerate(self.srcMods):
            if srcMod not in modInfos: continue
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            bashTags = srcInfo.getBashTags()
            if 'RACE' not in srcFile.tops: continue
            srcFile.convertToLongFids(('RACE',))
            for race in srcFile.RACE.getActiveRecords():
                raceData = self.raceData.setdefault(race.fid,{})
                if 'Hair' in bashTags:
                    raceHair = raceData.setdefault('hairs',[])
                    for hair in race.hairs:
                        if hair not in raceHair: raceHair.append(hair)
                if self.eyeKeys & bashTags:
                    raceData['rightEye'] = race.rightEye
                    raceData['leftEye'] = race.leftEye
                    raceEyes = raceData.setdefault('eyes',[])
                    for eye in race.eyes:
                        if eye not in raceEyes: raceEyes.append(eye)
                if 'Voice-M' in bashTags:
                    raceData['maleVoice'] = race.maleVoice
                if 'Voice-F' in bashTags:
                    raceData['femaleVoice'] = race.femaleVoice
                if 'Body-M' in bashTags:
                    for key in ['male'+key for key in self.bodyKeys]:
                        raceData[key] = getattr(race,key)
                if 'Body-F' in bashTags:
                    for key in ['female'+key for key in self.bodyKeys]:
                        raceData[key] = getattr(race,key)
                if 'R.Teeth' in bashTags:
                    for key in ('teethLower','teethUpper'):
                        raceData[key] = getattr(race,key)
                if 'R.Mouth' in bashTags:
                    for key in ('mouth','tongue'):
                        raceData[key] = getattr(race,key)
                if 'R.Relations' in bashTags:
                    relations = raceData.setdefault('relations',{})
                    for x in race.relations:
                        relations[x.faction] = x.mod
            progress.plus()

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (None,(MreRace,MreEyes,MreHair,MreNpc))[self.isActive]

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (None,(MreRace,MreEyes,MreHair,MreNpc))[self.isActive]

    def scanModFile(self, modFile, progress):
        """Add appropriate records from modFile."""
        if not self.isActive: return
        eye_mesh = self.eye_mesh
        modName = modFile.fileInfo.name
        mapper = modFile.getLongMapper()
        if not (set(modFile.tops) & self.scanTypes): return
        modFile.convertToLongFids(('RACE','EYES','NPC_'))
        srcEyes = set([record.fid for record in modFile.EYES.getActiveRecords()])
        #--Eyes, Hair
        for type in ('EYES','HAIR'):
            patchBlock = getattr(self.patchFile,type)
            id_records = patchBlock.id_records
            for record in getattr(modFile,type).getActiveRecords():
                if record.fid not in id_records:
                    patchBlock.setRecord(record.getTypeCopy(mapper))
        #--Npcs with unassigned eyes
        patchBlock = self.patchFile.NPC_
        id_records = patchBlock.id_records
        for record in modFile.NPC_.getActiveRecords():
            if not record.eye and record.fid not in id_records:
                patchBlock.setRecord(record.getTypeCopy(mapper))
        #--Race block
        patchBlock = self.patchFile.RACE
        id_records = patchBlock.id_records
        for record in modFile.RACE.getActiveRecords():
            if record.fid not in id_records:
                patchBlock.setRecord(record.getTypeCopy(mapper))
            for eye in record.eyes:
                if eye in srcEyes:
                    eye_mesh[eye] = (record.rightEye.modPath.lower(),record.leftEye.modPath.lower())

    def buildPatch(self,log,progress):
        """Updates races as needed."""
        debug = False
        if not self.isActive: return
        patchFile = self.patchFile
        keep = patchFile.getKeeper()
        if 'RACE' not in patchFile.tops: return
        racesPatched = []
        racesSorted = []
        racesFiltered = []
        mod_npcsFixed = {}
        #--Import race info
        for race in patchFile.RACE.records:
            #~~print 'Building',race.eid
            raceData = self.raceData.get(race.fid,None)
            if not raceData: continue
            raceChanged = False
            #--Hair, Eyes
            if 'hairs' in raceData and (set(race.hairs) != set(raceData['hairs'])):
                race.hairs = raceData['hairs']
                raceChanged = True
            if 'eyes' in raceData and (
                race.rightEye.modPath != raceData['rightEye'].modPath or
                race.leftEye.modPath  != raceData['leftEye'].modPath or
                set(race.eyes) != set(raceData['eyes'])
                ):
                for attr in ('rightEye','leftEye','eyes'):
                    setattr(race,attr,raceData[attr])
                raceChanged = True
            #--Teeth
            if 'teethLower' in raceData and (
                race.teethLower != raceData['teethLower'] or
                race.teethUpper != raceData['teethUpper']
                ):
                race.teethLower = raceData['teethLower']
                race.teethUpper = raceData['teethUpper']
                raceChanged = True
            #--Mouth
            if 'mouth' in raceData and (
                race.mouth != raceData['mouth'] or
                race.tongue != raceData['tongue']
                ):
                race.mouth = raceData['mouth']
                race.tongue = raceData['tongue']
                raceChanged = True
            #--Gender info (voice, body data)
            for gender in ('male','female'):
                voiceKey = gender+'Voice'
                if voiceKey in raceData:
                    if getattr(race,voiceKey) != raceData[voiceKey]:
                        setattr(race,voiceKey,raceData[voiceKey])
                        raceChanged = True
                bodyKeys = [gender+key for key in self.bodyKeys]
                if gender+'FootPath' in raceData:
                    for key in bodyKeys:
                        if getattr(race,key) != raceData[key]:
                            setattr(race,key,raceData[key])
                            raceChanged = True
            #--Relations
            if 'relations' in raceData:
                relations = raceData['relations']
                oldRelations = set((x.faction,x.mod) for x in race.relations)
                newRelations = set(relations.items())
                if newRelations != oldRelations:
                    del race.relations[:]
                    for faction,mod in newRelations:
                        entry = MelObject()
                        entry.faction = faction
                        entry.mod = mod
                        race.relations.append(entry)
                    raceChanged = True
            #--Changed
            if raceChanged:
                racesPatched.append(race.eid)
                keep(race.fid)
        #--Eye Mesh filtering
        eye_mesh = self.eye_mesh
        blueEyeMesh = eye_mesh[(GPath('Oblivion.esm'),0x27308)]
        argonianEyeMesh = eye_mesh[(GPath('Oblivion.esm'),0x3e91e)]
        if debug:
            print '== Eye Mesh Filtering'
            print 'blueEyeMesh',blueEyeMesh
            print 'argonianEyeMesh',argonianEyeMesh
        for eye in (
            (GPath('Oblivion.esm'),0x1a), #--Reanimate
            (GPath('Oblivion.esm'),0x54bb9), #--Dark Seducer
            (GPath('Oblivion.esm'),0x54bba), #--Golden Saint
            (GPath('Oblivion.esm'),0x5fa43), #--Ordered
            ):
            eye_mesh.setdefault(eye,blueEyeMesh)
        def setRaceEyeMesh(race,rightPath,leftPath):
            race.rightEye.modPath = rightPath
            race.leftEye.modPath = leftPath
        for race in patchFile.RACE.records:
            if debug: print '===', race.eid
            if not race.eyes: continue #--Sheogorath. Assume is handled correctly.
            if not race.rightEye or not race.leftEye: continue #--WIPZ race?
            raceChanged = False
            mesh_eye = {}
            for eye in race.eyes:
                if eye not in eye_mesh:
                    raise StateError(_('Mesh undefined for eye %s in race %s') % (strFid(eye),race.eid,))
                mesh = eye_mesh[eye]
                if mesh not in mesh_eye:
                    mesh_eye[mesh] = []
                mesh_eye[mesh].append(eye)
            currentMesh = (race.rightEye.modPath.lower(),race.leftEye.modPath.lower())
            #print race.eid, mesh_eye
            maxEyesMesh = sorted(mesh_eye.keys(),key=lambda a: len(mesh_eye[a]))[0]
            #--Single eye mesh, but doesn't match current mesh?
            if len(mesh_eye) == 1 and currentMesh != maxEyesMesh:
                setRaceEyeMesh(race,*maxEyesMesh)
                raceChanged = True
            #--Multiple eye meshes (and playable)?
            if debug:
                for mesh,eyes in mesh_eye.iteritems():
                    print mesh
                    for eye in eyes: print ' ',strFid(eye)
            if len(mesh_eye) > 1 and race.flags.playable:
                #--If blueEyeMesh (mesh used for vanilla eyes) is present, use that.
                if blueEyeMesh in mesh_eye and currentMesh != argonianEyeMesh:
                    setRaceEyeMesh(race,*blueEyeMesh)
                    race.eyes = mesh_eye[blueEyeMesh]
                    raceChanged = True
                elif argonianEyeMesh in mesh_eye:
                    setRaceEyeMesh(race,*argonianEyeMesh)
                    race.eyes = mesh_eye[argonianEyeMesh]
                    raceChanged = True
                #--Else figure that current eye mesh is the correct one
                elif currentMesh in mesh_eye:
                    race.eyes = mesh_eye[currentMesh]
                    raceChanged = True
                #--Else use most popular eye mesh
                else:
                    setRaceEyeMesh(race,*maxEyesMeshes)
                    race.eyes = mesh_eye[maxEyesMesh]
                    raceChanged = True
            if raceChanged:
                racesFiltered.append(race.eid)
                keep(race.fid)
        #--Sort Eyes/Hair
        defaultEyes = {}
        defaultMaleHair = {}
        defaultFemaleHair = {}
        eyeNames  = dict((x.fid,x.full) for x in patchFile.EYES.records)
        hairNames = dict((x.fid,x.full) for x in patchFile.HAIR.records)
        maleHairs = set(x.fid for x in patchFile.HAIR.records if not x.flags.notMale)
        femaleHairs = set(x.fid for x in patchFile.HAIR.records if not x.flags.notFemale)
        for race in patchFile.RACE.records:
            if race.flags.playable and race.eyes:
                defaultEyes[race.fid] = [x for x in bush.defaultEyes.get(race.fid,[]) if x in race.eyes]
                if not defaultEyes[race.fid]:
                    defaultEyes[race.fid] = [race.eyes[0]]
                defaultMaleHair[race.fid] = [x for x in race.hairs if x in maleHairs]
                defaultFemaleHair[race.fid] = [x for x in race.hairs if x in femaleHairs]
                race.hairs.sort(key=lambda x: hairNames.get(x))
                race.eyes.sort(key=lambda x: eyeNames.get(x))
                racesSorted.append(race.eid)
                keep(race.fid)
        #--Npcs with unassigned eyes/hair
        for npc in patchFile.NPC_.records:
            raceEyes = defaultEyes.get(npc.race)
            if not npc.eye and raceEyes:
                #random.seed(npc.fid)
                npc.eye = random.choice(raceEyes)
                srcMod = npc.fid[0]
                if srcMod not in mod_npcsFixed: mod_npcsFixed[srcMod] = set()
                mod_npcsFixed[srcMod].add(npc.fid)
                keep(npc.fid)
            raceHair = ((defaultMaleHair,defaultFemaleHair)[npc.flags.female]).get(npc.race)
            if not npc.hair and raceHair:
                #random.seed(npc.fid)
                npc.hair = random.choice(raceHair)
                srcMod = npc.fid[0]
                if srcMod not in mod_npcsFixed: mod_npcsFixed[srcMod] = set()
                mod_npcsFixed[srcMod].add(npc.fid)
                keep(npc.fid)
        #--Done
        log.setHeader('= '+self.__class__.name)
        log(_("=== Source Mods"))
        for mod in self.srcMods:
            log("* " +mod.s)
        log(_("\n=== Merged"))
        if not racesPatched:
            log(_(". ~~None~~"))
        else:
            for eid in sorted(racesPatched):
                log("* "+eid)
        log(_("\n=== Eyes/Hair Sorted"))
        if not racesSorted:
            log(_(". ~~None~~"))
        else:
            for eid in sorted(racesSorted):
                log("* "+eid)
        log(_("\n=== Eye Meshes Filtered"))
        if not racesFiltered:
            log(_(". ~~None~~"))
        else:
            log(_("In order to prevent 'googly eyes', incompatible eyes have been removed from the following races."))
            for eid in sorted(racesFiltered):
                log("* "+eid)
        if mod_npcsFixed:
            log(_("\n=== Eyes/Hair Assigned for NPCs"))
            for srcMod in sorted(mod_npcsFixed):
                log("* %s: %d" % (srcMod.s,len(mod_npcsFixed[srcMod])))
#------------------------------------------------------------------------------
class MAONPCSkeletonPatcher(MultiTweakItem):
    """Changes all NPCs to use the right Mayu's Animation Overhaul Skeleton for use with MAO ."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        MultiTweakItem.__init__(self,_("Mayu's Animation Overhaul Skeleton Tweaker"),
            _('Changes all (modded and vanilla) NPCs to use the MAO skeletons.'),
            'MAO Skeleton',
            ('1.0',  '1.0'),
            )

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreNpc,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreNpc,)

    def scanModFile(self,modFile,progress,patchFile):
        """Scans specified mod file to extract info. May add record to patch mod, 
        but won't alter it."""
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.NPC_
        for record in modFile.NPC_.getActiveRecords():
            record = record.getTypeCopy(mapper)
            patchRecords.setRecord(record)
                
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.NPC_.records:
            model = record.model.modPath
            if model.lower() == r'characters\_male\skeletonsesheogorath.nif':
                record.model.modPath = r"Mayu's Projects[M]\Animation Overhaul\Vanilla\SkeletonSESheogorath.nif"
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
            else:
                record.model.modPath = r"Mayu's Projects[M]\Animation Overhaul\Vanilla\SkeletonBeast.nif"
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log.setHeader(_('===MAO Skeleton Setter'))
        log(_('* %d Skeletons Tweaked') % (sum(count.values()),))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))
#------------------------------------------------------------------------------
class RWALKNPCAnimationPatcher(MultiTweakItem):
    """Changes all NPCs to use the right Mayu's Animation Overhaul Skeleton for use with MAO ."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        MultiTweakItem.__init__(self,_("Use Mur Zuk's Sexy Walk on all female NPCs"),
            _("Changes all female NPCs to use Mur Zuk's Sexy Walk"),
            'Mur Zuk SWalk',
            ('1.0',  '1.0'),
            )

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreNpc,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreNpc,)

    def scanModFile(self,modFile,progress,patchFile):
        """Scans specified mod file to extract info. May add record to patch mod, 
        but won't alter it."""
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.NPC_
        for record in modFile.NPC_.getActiveRecords():
            record = record.getTypeCopy(mapper)
            patchRecords.setRecord(record)
                
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.NPC_.records:
            if record.flags.female == 1:
                record.animations = '0sexywalk01.kf'
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log.setHeader(_('===SWalk for Female NPCs'))
        log(_('* %d NPCs Tweaked') % (sum(count.values()),))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))
#------------------------------------------------------------------------------
class SWALKNPCAnimationPatcher(MultiTweakItem):
    """Changes all NPCs to use the right Mayu's Animation Overhaul Skeleton for use with MAO ."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        MultiTweakItem.__init__(self,_("Use Mur Zuk's Real Walk on all female NPCs"),
            _("Changes all female NPCs to use Mur Zuk's Real Walk"),
            'Mur Zuk RWalk',
            ('1.0',  '1.0'),
            )

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return (MreNpc,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return (MreNpc,)

    def scanModFile(self,modFile,progress,patchFile):
        """Scans specified mod file to extract info. May add record to patch mod, 
        but won't alter it."""
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.NPC_
        for record in modFile.NPC_.getActiveRecords():
            record = record.getTypeCopy(mapper)
            patchRecords.setRecord(record)
                
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.NPC_.records:
            if record.flags.female == 1:
                record.animations = '0realwalk01.kf'
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log.setHeader(_('===RWalk for Female NPCs'))
        log(_('* %d NPCs Tweaked') % (sum(count.values()),))
        for srcMod in modInfos.getOrdered(count.keys()):
            log('  * %s: %d' % (srcMod.s,count[srcMod]))
#------------------------------------------------------------------------------
class SkelTweaker(MultiTweaker):
    """Sets NPC Skeletons or animations to better work with mods or avoid bugs."""
    name = _('Set NPC Skeletons and animations.')
    text = _("Set NPC Skeletons and animations.")
    tweaks = sorted([
        MAONPCSkeletonPatcher(),
        VanillaNPCSkeletonPatcher(),
        #RWALKNPCAnimationPatcher(),
        #SWALKNPCAnimationPatcher(),
        ],key=lambda a: a.label.lower())

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return None
        classTuples = [tweak.getReadClasses() for tweak in self.enabledTweaks]
        return sum(classTuples,tuple())

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return None
        classTuples = [tweak.getWriteClasses() for tweak in self.enabledTweaks]
        return sum(classTuples,tuple())

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        if not self.isActive: return
        for tweak in self.enabledTweaks:
            tweak.scanModFile(modFile,progress,self.patchFile)

    def buildPatch(self,log,progress):
        """Applies individual clothes tweaks."""
        if not self.isActive: return
        log.setHeader('= '+self.__class__.name,True)
        for tweak in self.enabledTweaks:
            tweak.buildPatch(log,progress,self.patchFile)

#------------------------------------------------------------------------------
class SEWorldEnforcer(SpecialPatcher,Patcher):
    """Suspends Cyrodiil quests while in Shivering Isles."""
    name = _('SEWorld Tests')
    text = _("Suspends Cyrodiil quests while in Shivering Isles. I.e. re-instates GetPlayerInSEWorld tests as necessary.")

    #--Config Phase -----------------------------------------------------------
    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.cyrodiilQuests = set()
        if GPath('Oblivion.esm') in loadMods:
            loadFactory = LoadFactory(False,MreQust)
            modInfo = modInfos[GPath('Oblivion.esm')]
            modFile = ModFile(modInfo,loadFactory)
            modFile.load(True)
            mapper = modFile.getLongMapper()
            for record in modFile.QUST.getActiveRecords():
                for condition in record.conditions:
                    if condition.ifunc == 365 and condition.compValue == 0:
                        self.cyrodiilQuests.add(mapper(record.fid))
                        break
        self.isActive = bool(self.cyrodiilQuests)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return tuple()
        return (MreQust,)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return tuple()
        return (MreQust,)

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        if not self.isActive: return
        if modFile.fileInfo.name == GPath('Oblivion.esm'): return
        cyrodiilQuests = self.cyrodiilQuests
        mapper = modFile.getLongMapper()
        patchBlock = self.patchFile.QUST
        for record in modFile.QUST.getActiveRecords():
            fid = mapper(record.fid)
            if fid not in cyrodiilQuests: continue
            for condition in record.conditions:
                if condition.ifunc == 365: break #--365: playerInSeWorld
            else:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Will write to log."""
        if not self.isActive: return
        cyrodiilQuests = self.cyrodiilQuests
        patchFile = self.patchFile
        keep = patchFile.getKeeper()
        patched = []
        for record in patchFile.QUST.getActiveRecords():
            if record.fid not in cyrodiilQuests: continue
            for condition in record.conditions:
                if condition.ifunc == 365: break #--365: playerInSeWorld
            else:
                condition = record.getDefault('conditions')
                condition.ifunc = 365
                record.conditions.insert(0,condition)
                keep(record.fid)
                patched.append(record.eid)
        log.setHeader('= '+self.__class__.name)
        log(_('===Quests Patched: %d') % (len(patched),))
        
#------------------------------------------------------------------------------
class ContentsChecker(SpecialPatcher,Patcher):
    """Checks contents of leveled lists, inventories and containers for correct content types."""
    scanOrder = 50
    editOrder = 50
    name = _('Contents Checker')
    text = _("Checks contents of leveled lists, inventories and containers for correct types.")

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.contType_entryTypes = {
            'LVSP':'LVSP,SPEL,'.split(','),
            'LVLC':'LVLC,NPC_,CREA'.split(','),
            #--LVLI will also be applied for containers.
            'LVLI':'LVLI,ALCH,AMMO,APPA,ARMO,BOOK,CLOT,INGR,KEYM,LIGH,MISC,SGST,SLGM,WEAP'.split(','),
            }
        self.contType_entryTypes['CONT'] = self.contType_entryTypes['LVLI']
        self.contType_entryTypes['CREA'] = self.contType_entryTypes['LVLI']
        self.contType_entryTypes['NPC_'] = self.contType_entryTypes['LVLI']
        self.id_type = {}
        self.id_eid = {}
        #--Types
        self.contTypes = self.contType_entryTypes.keys()
        self.entryTypes = sum(self.contType_entryTypes.values(),[])

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return
        return [MreRecord.type_class[x] for x in self.contTypes] + self.contType_entryTypes.keys() + self.entryTypes

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return
        return [MreRecord.type_class[x] for x in self.contTypes]

    def scanModFile(self, modFile, progress):
        """Scan modFile."""
        if not self.isActive: return 
        modName = modFile.fileInfo.name
        mapper = modFile.getLongMapper()
        #--Remember types (only when first defined)
        id_type = self.id_type
        for type in self.entryTypes:
            if type not in modFile.tops: continue
            for record in modFile.tops[type].getActiveRecords():
                fid = record.fid
                if not record.longFids: fid = mapper(fid)
                if fid not in id_type:
                    id_type[fid] = type
##                if fid[0] == modName:
##                    id_type[fid] = type
        #--Save container types
        modFile.convertToLongFids(self.contTypes)
        for type in self.contTypes:
            if type not in modFile.tops: continue
            patchBlock = getattr(self.patchFile,type)
            id_records = patchBlock.id_records
            for record in modFile.tops[type].getActiveRecords():
                if record.fid not in id_records: 
                    patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress):
        """Make changes to patchfile."""
        if not self.isActive: return
        modFile = self.patchFile
        keep = self.patchFile.getKeeper()
        id_type = self.id_type
        id_eid = self.id_eid
        log.setHeader('= '+self.__class__.name)
        #--Lists
        for cAttr,eAttr,types in (
            ('entries','listId',('LVSP','LVLI','LVLC')),
            ('items','item',('CONT','CREA','NPC_')),
            ):
            for type in types:
                if type not in modFile.tops: continue
                entryTypes = set(self.contType_entryTypes[type])
                id_removed = {}
                for record in modFile.tops[type].records:
                    newEntries = []
                    oldEntries = getattr(record,cAttr)
                    for entry in oldEntries:
                        entryId = getattr(entry,eAttr)
                        if id_type.get(entryId) in entryTypes:
                            newEntries.append(entry)
                        else:
                            removed = id_removed.setdefault(record.fid,[])
                            removed.append(entryId)
                            id_eid[record.fid] = record.eid
                    if len(newEntries) != len(oldEntries):
                        setattr(record,cAttr,newEntries)
                        keep(record.fid)
                #--Log it
                if id_removed:
                    log("\n=== "+type)
                    for contId in sorted(id_removed):
                        log('* ' + id_eid[contId])
                        for removedId in sorted(id_removed[contId]):
                            mod,index = removedId
                            log('  . %s: %06X' % (mod.s,index))

# Initialization --------------------------------------------------------------
def initDirs(personal='',localAppData=''):
    try:
        from win32com.shell import shell, shellcon
    except ImportError:
        shell = shellcon = None
    #--Bash Ini
    bashIni = None
    if GPath('bash.ini').exists():
        bashIni = ConfigParser.ConfigParser()
        bashIni.read('bash.ini')
    #--Specified on command line.
    if personal or localAppData:
        if not personal: raise BoltError(_("-p command line argument is missing."))
        if not localAppData: raise BoltError(_("-l command line argument is missing."))
        personal = GPath(personal)
        localAppData = GPath(localAppData)
        for optKey,dirPath in (('-p',personal),('-l',localAppData)):
            if not dirPath.exists():
                raise BoltError(_("Error in %s argument: Non-existent directory:\n>> %s") % (optKey,dirPath))
        errorInfo = _("Folder paths specified on command line.")
    #--Try to use win32com module.
    elif shell and shellcon:
        def getShellPath(shellKey):
            path = shell.SHGetFolderPath (0, shellKey, None, 0)
            path = path.encode(locale.getpreferredencoding())
            return GPath(path)
        personal = getShellPath(shellcon.CSIDL_PERSONAL)
        localAppData = getShellPath(shellcon.CSIDL_LOCAL_APPDATA)
        errorInfo = _("Folder paths extracted from win32com.shell.")
    #--Otherwise try to read from registry.
    else:
        reEnv = re.compile('%(\w+)%')
        envDefs = os.environ
        def subEnv(match):
            key = match.group(1).upper()
            if not envDefs.get(key):
                raise BoltError(_("Can't find user directories in windows registry.\n>> See \"If Bash Won't Start\" in bash docs for help."))
            return envDefs[key]
        def getShellPath(folderKey):
            import _winreg
            regKey = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders')
            try:
                path = _winreg.QueryValueEx(regKey,folderKey)[0]
            except WindowsError:
                raise BoltError(_("Can't find user directories in windows registry.\n>> See \"If Bash Won't Start\" in bash docs for help."))
            regKey.Close()
            path = path.encode(locale.getpreferredencoding())
            path = reEnv.sub(subEnv,path)
            return GPath(path)
        personal = getShellPath('Personal')
        localAppData = getShellPath('Local AppData')
        errorInfo = '\n'.join('  '+key+': '+`envDefs[key]` for key in sorted(envDefs))

    #--User sub folders
    dirs['saveBase'] = personal.join(r'My Games','Oblivion')
    dirs['userApp'] = localAppData.join('Oblivion')

    #--App Directories... Assume bash is in right place.
    dirs['app'] = bolt.Path.getcwd().head
    dirs['mods'] = dirs['app'].join('Data')
    dirs['builds'] = dirs['app'].join('Builds')
    dirs['patches'] = dirs['mods'].join('Bash Patches')
    #-- Other tool directories 
    #   First to default path
    dirs['TES4FilesPath'] = dirs['app'].join('TES4Files.exe')
    dirs['TES4EditPath'] = dirs['app'].join('TES4Edit.exe')
    dirs['TES4LodGenPath'] = dirs['app'].join('TES4LodGen.exe')
    dirs['NifskopePath'] = GPath('C:\Program Files\NifTools\NifSkope\Nifskope.exe')
    dirs['BlenderPath'] = GPath(r'C:\Program Files\Blender Foundation\Blender\blender.exe')
    dirs['GmaxPath'] = GPath('C:\GMAX\gmax.exe')
    dirs['MaxPath'] = GPath('C:\something\dunnothedefaultpath.exe')
    dirs['MayaPath'] = GPath('C:\something\dunnothedefaultpath.exe')
    dirs['Photoshop'] = GPath('C:\Program Files\Adobe\Adobe Photoshop CS3\Photoshop.exe')
    dirs['GIMP'] = GPath('C:\something\dunnothedefaultpath.exe')
    dirs['ISOBL'] = dirs['app'].join('ISOBL.exe')
    dirs['ISRMG'] = dirs['app'].join('Insanitys ReadMe Generator.exe')
    dirs['ISRNG'] = dirs['app'].join('Random Name Generator.exe')
    dirs['ISRNPCG'] = dirs['app'].join('Random NPC.exe')
    # Then if bash.ini exists set from the settings in there:
    if bashIni:
        if bashIni.has_option('Tool Options','sTes4FilesPath'):
            dirs['TES4FilesPath'] = GPath(bashIni.get('Tool Options','sTes4FilesPath').strip())
            if not dirs['TES4FilesPath'].isabs():
                dirs['TES4FilesPath'] = dirs['app'].join(dirs['TES4FilesPath'])

        if bashIni.has_option('Tool Options','sTes4EditPath'):
            dirs['TES4EditPath'] = GPath(bashIni.get('Tool Options','sTes4EditPath').strip())
            if not dirs['TES4EditPath'].isabs():
                dirs['TES4EditPath'] = dirs['app'].join(dirs['TES4EditPath'])
            
        if bashIni.has_option('Tool Options','sTes4LodGenPath'):
            dirs['TES4LodGenPath'] = GPath(bashIni.get('Tool Options','sTes4LodGenPath').strip())
            if not dirs['TES4LodGenPath'].isabs():
                dirs['TES4LodGenPath'] = dirs['app'].join(dirs['TES4LodGenPath'])

        if bashIni.has_option('Tool Options','sNifskopePath'):
            dirs['NifskopePath'] = GPath(bashIni.get('Tool Options','sNifskopePath').strip())
            if not dirs['NifskopePath'].isabs():
                dirs['NifskopePath'] = dirs['app'].join(dirs['NifskopePath'])
                
        if bashIni.has_option('Tool Options','sBlenderPath'):
            dirs['BlenderPath'] = GPath(bashIni.get('Tool Options','sBlenderPath').strip())
            if not dirs['BlenderPath'].isabs():
                dirs['BlenderPath'] = dirs['app'].join(dirs['BlenderPath'])

        if bashIni.has_option('Tool Options','sGmaxPath'):
            dirs['GmaxPath'] = GPath(bashIni.get('Tool Options','sGmaxPath').strip())
            if not dirs['GmaxPath'].isabs():
                dirs['GmaxPath'] = dirs['app'].join(dirs['GmaxPath'])

        if bashIni.has_option('Tool Options','sMaxPath'):
            dirs['MaxPath'] = GPath(bashIni.get('Tool Options','sMaxPath').strip())
            if not dirs['MaxPath'].isabs():
                dirs['MaxPath'] = dirs['app'].join(dirs['MaxPath'])
                
        if bashIni.has_option('Tool Options','sMayaPath'):
            dirs['MayaPath'] = GPath(bashIni.get('Tool Options','sMayaPath').strip())
            if not dirs['MayaPath'].isabs():
                dirs['MayaPath'] = dirs['app'].join(dirs['MayaPath'])
            
        if bashIni.has_option('Tool Options','sPhotoshopPath'):
            dirs['Photoshop'] = GPath(bashIni.get('Tool Options','sPhotoshopPath').strip())
            if not dirs['Photoshop'].isabs():
                dirs['Photoshop'] = dirs['app'].join(dirs['Photoshop'])
            
        if bashIni.has_option('Tool Options','sGIMP'):
            dirs['GIMP'] = GPath(bashIni.get('Tool Options','sGIMP').strip())
            if not dirs['GIMP'].isabs():
                dirs['GIMP'] = dirs['app'].join(dirs['GIMP'])
            
        if bashIni.has_option('Tool Options','sISOBL'):
            dirs['ISOBL'] = GPath(bashIni.get('Tool Options','sISOBL').strip())
            if not dirs['ISOBL'].isabs():
                dirs['ISOBL'] = dirs['app'].join(dirs['ISOBL'])
            
        if bashIni.has_option('Tool Options','sISRMG'):
            dirs['ISRMG'] = GPath(bashIni.get('Tool Options','sISRMG').strip())
            if not dirs['ISRMG'].isabs():
                dirs['ISRMG'] = dirs['app'].join(dirs['ISRMG'])
            
        if bashIni.has_option('Tool Options','sISRNG'):
            dirs['ISRNG'] = GPath(bashIni.get('Tool Options','sISRNG').strip())
            if not dirs['ISRNG'].isabs():
                dirs['ISRNG'] = dirs['app'].join(dirs['ISRNG'])
            
        if bashIni.has_option('Tool Options','sISRNPCG'):
            dirs['ISRNPCG'] = GPath(bashIni.get('Tool Options','sISRNPCG').strip())
            if not dirs['ISRNPCG'].isabs():
                dirs['ISRNPCG'] = dirs['app'].join(dirs['ISRNPCG'])
            
    #--Mod Data, Installers
    if bashIni and bashIni.has_option('General','sOblivionMods'):
        oblivionMods = GPath(bashIni.get('General','sOblivionMods').strip())
    else:
        oblivionMods = GPath(r'..\Oblivion Mods')
    if not oblivionMods.isabs():
        oblivionMods = dirs['app'].join(oblivionMods)
    for key,oldDir,newDir in (
        ('modsBash', dirs['app'].join('Data','Bash'), oblivionMods.join('Bash Mod Data')),
        ('installers', dirs['app'].join('Installers'), oblivionMods.join('Bash Installers')),
        ):
        dirs[key] = (oldDir,newDir)[newDir.isdir() or not oldDir.isdir()]
        dirs[key].makedirs()
    dirs['converters'] = dirs['installers'].join('Bain Converters')
    dirs['converters'].makedirs()
    dirs['dupeBCFs'] = dirs['converters'].join('--Duplicates')
    dirs['dupeBCFs'].makedirs()
    #--Error checks
    if not personal.exists():
        raise BoltError(_("Personal folder does not exist\nPersonal folder: %s\nAdditional info:\n%s")
            % (personal.s,errorInfo))
    if not localAppData.exists():
        raise BoltError(_("Local app data folder does not exist.\nLocal app data folder: %s\nAdditional info:\n%s")
            % (localAppData.s, errorInfo))
    if not dirs['app'].join('Oblivion.exe').exists():
        print dirs['app'].join('Oblivion.exe')
        raise BoltError(_("Install Error\nFailed to find Oblivion.exe in %s.\nNote that the Mopy folder should be in the same folder as Oblivion.exe.") % dirs['app'])
        
    #other settings from the INI:
    inisettings['scriptFileExt']='.txt'
    inisettings['keepLog'] = 0
    inisettings['logFile'] = dirs['app'].join('Mopy').join('bash.log')
    if bashIni:
        if bashIni.has_option('Settings','sScriptFileExt'):
            inisettings['scriptFileExt'] = str(bashIni.get('Settings','sScriptFileExt').strip())
        if bashIni.has_option('Settings','iKeepLog'):
            inisettings['keepLog'] = int(bashIni.get('Settings','iKeepLog').strip())
        if bashIni.has_option('Settings','sLogFile'):
            inisettings['logFile'] = GPath(bashIni.get('Settings','sLogFile').strip())
            if not inisettings['logFile'].isabs():
                inisettings['logFile'] = dirs['app'].join(inisettings['logFile'])

    if inisettings['keepLog'] == 0:
        if inisettings['logFile'].exists():
            os.remove(inisettings['logFile'].s)
    else:
        log = inisettings['logFile'].open("a")
        log.write('%s Wrye Bash ini file read, Keep Log level: %d, initialized.\r\n'%(datetime.datetime.now(),inisettings['keepLog']))
        log.close()

def initSettings(readOnly=False):
    global settings
    settings = bolt.Settings(PickleDict(
        dirs['saveBase'].join('BashSettings.dat'),
        dirs['userApp'].join('bash config.pkl'),
        readOnly))
    settings.loadDefaults(settingDefaults)

# Main ------------------------------------------------------------------------
if __name__ == '__main__':
    print _('Compiled')
