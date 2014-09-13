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

"""This module defines objects and functions for working with Oblivion
files and environment. It does not provide interface functions which are instead
provided by separate modules: bish for CLI and bash/basher for GUI."""

# Localization ----------------------------------------------------------------
#--Not totally clear on this, but it seems to safest to put locale first...
import locale; locale.setlocale(locale.LC_ALL,u'')
#locale.setlocale(locale.LC_ALL,'German')
#locale.setlocale(locale.LC_ALL,'Japanese_Japan.932')
import time
import operator

# Imports ---------------------------------------------------------------------
#--Python
import cPickle
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
import subprocess
from subprocess import Popen, PIPE
import codecs
import ctypes

#--Local
import balt
import bolt
import bush
from bolt import BoltError, AbstractError, ArgumentError, StateError, \
    UncodedError, PermissionError, FileError
from bolt import LString, GPath, Flags, DataDict, SubProgress, cstrip, \
    deprint, sio
from bolt import _unicode, _encode
from cint import *
from brec import *
from brec import _coerce # Since it wont get imported by the import * (it
# begins with _)
from chardet.universaldetector import UniversalDetector
from patcher.oblivion.record_groups import MobWorlds, MobDials, MobICells, \
    MobObjects, MobBase
import loot
import libbsa
import liblo

startupinfo = bolt.startupinfo

#--Settings
dirs = {} #--app, user, mods, saves, userApp
tooldirs = {}
inisettings = {}
defaultExt = u'.7z'
writeExts = dict({u'.7z':u'7z',u'.zip':u'zip'})
readExts = {u'.rar', u'.7z.001', u'.001'}
readExts.update(set(writeExts))
noSolidExts = {u'.zip'}
settings = None
installersWindow = None

allTags = bush.game.allTags
allTagsSet = set(allTags)
oldTags = sorted((u'Merge',))
oldTagsSet = set(oldTags)

reOblivion = re.compile(
    u'^(Oblivion|Nehrim)(|_SI|_1.1|_1.1b|_1.5.0.8|_GOTY non-SI).esm$', re.U)

undefinedPath = GPath(u'C:\\not\\a\\valid\\path.exe')
undefinedPaths = {GPath(u'C:\\Path\\exe.exe'), undefinedPath}

#--Default settings
settingDefaults = {
    'bosh.modInfos.resetMTimes':True,
    }

#--Unicode
exe7z = u'7z.exe'

def getPatchesPath(fileName):
    """Choose the correct Bash Patches path for the file."""
    if dirs['patches'].join(fileName).isfile():
        return dirs['patches'].join(fileName)
    else:
        return dirs['defaultPatches'].join(fileName)

def getPatchesList():
    """Get a basic list of potential Bash Patches."""
    return set(dirs['patches'].list()) | set(dirs['defaultPatches'].list())

def formatInteger(value):
    """Convert integer to string formatted to locale."""
    return _unicode(locale.format('%d',int(value),True),locale.getpreferredencoding())

def formatDate(value):
    """Convert time to string formatted to to locale's default date/time."""
    return _unicode(time.strftime('%c',time.localtime(value)),locale.getpreferredencoding())

def unformatDate(str,format):
    """Basically a wrapper around time.strptime. Exists to get around bug in
    strptime for Japanese locale."""
    try:
        return time.strptime(str,'%c')
    except ValueError:
        if format == '%c' and u'Japanese' in locale.getlocale()[0]:
            str = re.sub(u'^([0-9]{4})/([1-9])',r'\1/0\2',str,flags=re.U)
            return time.strptime(str,'%c')
        else:
            raise

# Singletons, Constants -------------------------------------------------------
#--Constants
#..Bit-and this with the fid to get the objectindex.
oiMask = 0xFFFFFFL
question = False

#--File Singletons
gameInis = None
oblivionIni = None
modInfos  = None  #--ModInfos singleton
saveInfos = None #--SaveInfos singleton
iniInfos = None #--INIInfos singleton
bsaInfos = None #--BSAInfos singleton
trackedInfos = None #--TrackedFileInfos singleton
screensData = None #--ScreensData singleton
bsaData = None #--bsaData singleton
messages = None #--Message archive singleton
configHelpers = None #--Config Helper files (LOOT Master List, etc.)
lootDb = None #--LootDb singleton
lo = None #--LibloHandle singleton
links = None

def listArchiveContents(fileName):
    command = ur'"%s" l -slt -sccUTF-8 "%s"' % (exe7z, fileName)
    ins, err = Popen(command, stdout=PIPE, stdin=PIPE, startupinfo=startupinfo).communicate()
    return ins

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
class PickleDict(bolt.PickleDict):
    """Dictionary saved in a pickle file. Supports older bash pickle file formats."""
    def __init__(self,path,oldPath=None,readOnly=False):
        bolt.PickleDict.__init__(self,path,readOnly)
        self.oldPath = oldPath or GPath(u'')

    def exists(self):
        """See if pickle file exists."""
        return bolt.PickleDict.exists(self) or self.oldPath.exists()

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
                with self.oldPath.open('r') as ins:
                    self.data.update(cPickle.load(ins))
                result = 1
            except EOFError:
                pass
        #--Update paths
        def textDump(path):
            deprint(u'Text dump:',path)
            with path.open('w',encoding='utf-8-sig') as out:
                for key,value in self.data.iteritems():
                    out.write(u'= %s:\n  %s\n' % (key,value))
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
        basicTypes = {NoneType, FloatType, IntType, LongType, BooleanType,
                      StringType, UnicodeType}
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
                xnew = None #--Hopefully this will work for few old incompatibilities.
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
reGroup = re.compile(ur'^Group: *(.*)',re.M|re.U)
reRequires = re.compile(ur'^Requires: *(.*)',re.M|re.U)
reReqItem = re.compile(ur'^([a-zA-Z]+) *([\d]*\.?[\d]*)$',re.U)
reVersion = re.compile(ur'^(version[:\.]*|ver[:\.]*|rev[:\.]*|r[:\.\s]+|v[:\.\s]+) *([-0-9a-zA-Z\.]*\+?)',re.M|re.I|re.U)

#--Mod Extensions
reComment = re.compile(u'#.*',re.U)
reExGroup = re.compile(u'(.*?),',re.U)
reImageExt = re.compile(ur'\.(gif|jpg|bmp|png)$',re.I|re.U)
reModExt  = re.compile(ur'\.es[mp](.ghost)?$',re.I|re.U)
reEsmExt  = re.compile(ur'\.esm(.ghost)?$',re.I|re.U)
reEspExt  = re.compile(ur'\.esp(.ghost)?$',re.I|re.U)
reBSAExt  = re.compile(ur'\.bsa(.ghost)?$',re.I|re.U)
reEssExt  = re.compile(ur'\.ess$',re.I|re.U)
reSaveExt = re.compile(ur'(quicksave(\.bak)+|autosave(\.bak)+|\.es[rs])$',re.I|re.U)
reCsvExt  = re.compile(ur'\.csv$',re.I|re.U)
reINIExt  = re.compile(ur'\.ini$',re.I|re.U)
reQuoted  = re.compile(ur'^"(.*)"$',re.U)
reGroupHeader = re.compile(ur'^(\+\+|==)',re.U)
reTesNexus = re.compile(ur'(.*?)(?:-(\d{1,6})(?:\.tessource)?(?:-bain)?(?:-\d{0,6})?(?:-\d{0,6})?(?:-\d{0,6})?(?:-\w{0,16})?(?:\w)?)?(\.7z|\.zip|\.rar|\.7z\.001|)$',re.I|re.U)
reTESA = re.compile(ur'(.*?)(?:-(\d{1,6})(?:\.tessource)?(?:-bain)?)?(\.7z|\.zip|\.rar|)$',re.I|re.U)
reSplitOnNonAlphaNumeric = re.compile(ur'\W+',re.U)


# Util Functions --------------------------------------------------------------
# Groups
reSplitModGroup = re.compile(ur'^(.+?)([-+]\d+)?$',re.U)

def splitModGroup(offGroup):
    """Splits a full group name into a group name and an integer offset.
    E.g. splits 'Overhaul+1' into ('Overhaul',1)."""
    if not offGroup: return u'',0
    maSplitModGroup = reSplitModGroup.match(offGroup)
    group = maSplitModGroup.group(1)
    offset = int(maSplitModGroup.group(2) or 0)
    return group,offset

def joinModGroup(group,offset):
    """Combines a group and offset into a full group name."""
    if offset < 0:
        return group+unicode(offset)
    elif offset > 0:
        return group+u'+'+unicode(offset)
    else:
        return group

def PrintFormID(fid):
    # PBash short Fid
    if isinstance(fid,(long,int)):
        print '%08X' % fid
    # PBash long FId
    elif isinstance(fid, tuple):
        print '(%s, %06X)' % (fid[0],fid[1])
    # CBash / other(error)
    else:
        print repr(fid)

# Mod Blocks, File ------------------------------------------------------------
#------------------------------------------------------------------------------
class MasterMapError(BoltError):
    """Attempt to map a fid when mapping does not exist."""
    def __init__(self,modIndex):
        BoltError.__init__(self,u'No valid mapping for mod index 0x%02X' % modIndex)

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
        if isinstance(recClass,basestring):
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
            (self.recTypes & {'REFR', 'ACHR', 'ACRE', 'PGRD', 'LAND'}) or
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
class ModFile:
    """TES4 file representation."""
    def __init__(self, fileInfo,loadFactory=None):
        self.fileInfo = fileInfo
        self.loadFactory = loadFactory or LoadFactory(True)
        #--Variables to load
        self.tes4 = bush.game.MreHeader(ModReader.recHeader())
        self.tes4.setChanged()
        self.strings = bolt.StringTable()
        self.tops = {} #--Top groups.
        self.topsSkipped = set() #--Types skipped
        self.longFids = False
        #--Cached data
        self.mgef_school = None
        self.mgef_name = None
        self.hostileEffects = None

    def __getattr__(self,topType):
        """Returns top block of specified topType, creating it, if necessary."""
        if topType in self.tops:
            return self.tops[topType]
        elif topType in bush.game.esp.topTypes:
            topClass = self.loadFactory.getTopClass(topType)
            self.tops[topType] = topClass(ModReader.recHeader('GRUP',0,topType,0,0),self.loadFactory)
            self.tops[topType].setChanged()
            return self.tops[topType]
        elif topType == '__repr__':
            raise AttributeError
        else:
            raise ArgumentError(u'Invalid top group type: '+topType)

    def load(self,unpack=False,progress=None,loadStrings=True):
        """Load file."""
        progress = progress or bolt.Progress()
        progress.setFull(1.0)
        #--Header
        with ModReader(self.fileInfo.name,self.fileInfo.getPath().open('rb')) as ins:
            header = ins.unpackRecHeader()
            self.tes4 = bush.game.MreHeader(header,ins,True)
            #--Strings
            self.strings.clear()
            if unpack and self.tes4.flags1[7] and loadStrings:
                stringsProgress = SubProgress(progress,0,0.1) # Use 10% of progress bar for strings
                lang = oblivionIni.getSetting(u'General',u'sLanguage',u'English')
                stringsPaths = self.fileInfo.getStringsPaths(lang)
                stringsProgress.setFull(max(len(stringsPaths),1))
                for i,path in enumerate(stringsPaths):
                    self.strings.loadFile(path,SubProgress(stringsProgress,i,i+1),lang)
                    stringsProgress(i)
                ins.setStringTable(self.strings)
                subProgress = SubProgress(progress,0.1,1.0)
            else:
                ins.setStringTable(None)
                subProgress = progress
            #--Raw data read
            subProgress.setFull(ins.size)
            insAtEnd = ins.atEnd
            insRecHeader = ins.unpackRecHeader
            selfGetTopClass = self.loadFactory.getTopClass
            selfTopsSkipAdd = self.topsSkipped.add
            insSeek = ins.seek
            insTell = ins.tell
            selfLoadFactory = self.loadFactory
            selfTops = self.tops
            while not insAtEnd():
                #--Get record info and handle it
                header = insRecHeader()
                type = header.recType
                if type != 'GRUP' or header.groupType != 0:
                    raise ModError(self.fileInfo.name,u'Improperly grouped file.')
                label,size = header.label,header.size
                topClass = selfGetTopClass(label)
                try:
                    if topClass:
                        selfTops[label] = topClass(header,selfLoadFactory)
                        selfTops[label].load(ins,unpack and (topClass != MobBase))
                    else:
                        selfTopsSkipAdd(label)
                        insSeek(size-header.__class__.size,1,type + '.' + label)
                except:
                    print u'Error in',self.fileInfo.name.s
                    deprint(u' ',traceback=True)
                    break
                subProgress(insTell())
        #--Done Reading

    def load_unpack(self):
        """Unpacks blocks."""
        factoryTops = self.loadFactory.topTypes
        selfTops = self.tops
        for type in bush.game.esp.topTypes:
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
        if re.match(ur'\s*[yY]',raw_input(u'\nSave changes to '+fileName.s+u' [y\n]?: '),flags=re.U):
            self.safeSave()
            print fileName.s,u'saved.'
        else:
            print fileName.s,u'not saved.'

    def safeSave(self):
        """Save data to file safely.  Works under UAC."""
        self.fileInfo.tempBackup()
        filePath = self.fileInfo.getPath()
        self.save(filePath.temp)
        filePath.temp.mtime = self.fileInfo.mtime
        balt.shellMove(filePath.temp,filePath,None,False,False,False)
        self.fileInfo.extras.clear()

    def save(self,outPath=None):
        """Save data to file.
        outPath -- Path of the output file to write to. Defaults to original file path."""
        if not self.loadFactory.keepAll: raise StateError(u"Insufficient data to write file.")
        outPath = outPath or self.fileInfo.getPath()
        with ModWriter(outPath.open('wb')) as out:
            #--Mod Record
            self.tes4.setChanged()
            self.tes4.numRecords = sum(block.getNumRecords() for block in self.tops.values())
            self.tes4.getSize()
            self.tes4.dump(out)
            #--Blocks
            selfTops = self.tops
            for type in bush.game.esp.topTypes:
                if type in selfTops:
                    selfTops[type].dump(out)

    def getLongMapper(self):
        """Returns a mapping function to map short fids to long fids."""
        masters = self.tes4.masters+[self.fileInfo.name]
        maxMaster = len(masters)-1
        def mapper(fid):
            if fid is None: return None
            if isinstance(fid,tuple): return fid
            mod,object = int(fid >> 24),int(fid & 0xFFFFFFL)
            return masters[min(mod,maxMaster)],object
        return mapper

    def getShortMapper(self):
        """Returns a mapping function to map long fids to short fids."""
        masters = self.tes4.masters+[self.fileInfo.name]
        indices = dict([(name,index) for index,name in enumerate(masters)])
        gLong = self.getLongMapper()
        def mapper(fid):
            if fid is None: return None
            if isinstance(fid, (long, int)):
                fid = gLong(fid)
            modName,object = fid
            mod = indices[modName]
            return (long(mod) << 24 ) | long(object)
        return mapper

    def convertToLongFids(self,types=None):
        """Convert fids to long format (modname,objectindex)."""
        mapper = self.getLongMapper()
        if types is None: types = self.tops.keys()
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
        if not self.longFids: raise StateError(u"ModFile fids not in long form.")
        for fname in bush.game.masterFiles:
            if dirs['mods'].join(fname).exists():
                masters = MasterSet([GPath(fname)])
                break
        for block in self.tops.values():
            block.updateMasters(masters)
        return masters.getOrdered()

    def getMgefSchool(self,refresh=False):
        """Return a dictionary mapping magic effect code to magic effect school.
        This is intended for use with the patch file when it records for all magic effects.
        If magic effects are not available, it will revert to bush.py version."""
        if self.mgef_school and not refresh:
            return self.mgef_school
        mgef_school = self.mgef_school = bush.mgef_school.copy()
        if 'MGEF' in self.tops:
            for record in self.MGEF.getActiveRecords():
                if isinstance(record,MreRecord.type_class['MGEF']):
                    mgef_school[record.eid] = record.school
        return mgef_school

    def getMgefHostiles(self,refresh=False):
        """Return a set of hostile magic effect codes.
        This is intended for use with the patch file when it records for all magic effects.
        If magic effects are not available, it will revert to bush.py version."""
        if self.hostileEffects and not refresh:
            return self.hostileEffects
        hostileEffects = self.hostileEffects = bush.hostileEffects.copy()
        if 'MGEF' in self.tops:
            hostile = set()
            nonhostile = set()
            for record in self.MGEF.getActiveRecords():
                if isinstance(record,MreRecord.type_class['MGEF']):
                    if record.flags.hostile:
                        hostile.add(record.eid)
                        hostile.add(cast(record.eid, POINTER(c_ulong)).contents.value)
                    else:
                        nonhostile.add(record.eid)
                        nonhostile.add(cast(record.eid, POINTER(c_ulong)).contents.value)
            hostileEffects = (hostileEffects - nonhostile) | hostile
        return hostileEffects

    def getMgefName(self,refresh=False):
        """Return a dictionary mapping magic effect code to magic effect name.
        This is intended for use with the patch file when it records for all magic effects.
        If magic effects are not available, it will revert to bush.py version."""
        if self.mgef_name and not refresh:
            return self.mgef_name
        mgef_name = self.mgef_name = bush.mgef_name.copy()
        if 'MGEF' in self.tops:
            for record in self.MGEF.getActiveRecords():
                if isinstance(record,MreRecord.type_class['MGEF']):
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
        for attr in self.__slots__:
            self.__setattr__(attr,None)
        if data: self.load(flags,data)

    def getDefault(self,attr):
        """Returns a default version. Only supports acbs."""
        assert(attr == 'acbs')
        acbs = SreNPC.ACBS()
        (acbs.flags, acbs.baseSpell, acbs.fatigue, acbs.barterGold, acbs.level,
                acbs.calcMin, acbs.calcMax) = (0,0,0,0,1,0,0)
        acbs.flags = bush.game.MreNpc._flags(acbs.flags)
        return acbs

    def load(self,flags,data):
        """Loads variables from data."""
        with sio(data) as ins:
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
                acbs.flags = bush.game.MreNpc._flags(acbs.flags)
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

    def getFlags(self):
        """Returns current flags set."""
        flags = SreNPC.flags()
        for attr in SreNPC.__slots__:
            if attr != 'unused2':
                flags.__setattr__(attr,self.__getattribute__(attr) is not None)
        return int(flags)

    def getData(self):
        """Returns self.data."""
        with sio() as out:
            def pack(format,*args):
                out.write(struct.pack(format,*args))
            #--Form
            if self.form is not None:
                pack('I',self.form)
            #--Attributes
            if self.attributes is not None:
                pack('8B',*self.attributes)
            #--Acbs
            if self.acbs is not None:
                acbs = self.acbs
                pack('=I3Hh2H',int(acbs.flags), acbs.baseSpell, acbs.fatigue, acbs.barterGold, acbs.level,
                    acbs.calcMin, acbs.calcMax)
            #--Factions
            if self.factions is not None:
                pack('H',len(self.factions))
                for faction in self.factions:
                    pack('=Ib',*faction)
            #--Spells
            if self.spells is not None:
                num = len(self.spells)
                pack('H',num)
                pack('%dI' % num,*self.spells)
            #--AI Data
            if self.ai is not None:
                out.write(self.ai)
            #--Health
            if self.health is not None:
                pack('H2s',self.health,self.unused2)
            #--Modifiers
            if self.modifiers is not None:
                pack('H',len(self.modifiers))
                for modifier in self.modifiers:
                    pack('=Bf',*modifier)
            #--Full
            if self.full is not None:
                pack('B',len(self.full))
                out.write(self.full)
            #--Skills
            if self.skills is not None:
                pack('21B',*self.skills)
            #--Done
            return out.getvalue()

    def getTuple(self,fid,version):
        """Returns record as a change record tuple."""
        return fid,35,self.getFlags(),version,self.getData()

    def dumpText(self,saveFile):
        """Returns informal string representation of data."""
        with sio() as buff:
            fids = saveFile.fids
            if self.form is not None:
                buff.write(u'Form:\n  %d' % self.form)
            if self.attributes is not None:
                buff.write(u'Attributes\n  strength %3d\n  intelligence %3d\n  willpower %3d\n  agility %3d\n  speed %3d\n  endurance %3d\n  personality %3d\n  luck %3d\n' % tuple(self.attributes))
            if self.acbs is not None:
                buff.write(u'ACBS:\n')
                for attr in SreNPC.ACBS.__slots__:
                    buff.write(u'  %s %s\n' % (attr,getattr(self.acbs,attr)))
            if self.factions is not None:
                buff.write(u'Factions:\n')
                for faction in self.factions:
                    buff.write(u'  %8X %2X\n' % (fids[faction[0]],faction[1]))
            if self.spells is not None:
                buff.write(u'Spells:\n')
                for spell in self.spells:
                    buff.write(u'  %8X\n' % fids[spell])
            if self.ai is not None:
                buff.write(_(u'AI')+u':\n  ' + self.ai + u'\n')
            if self.health is not None:
                buff.write(u'Health\n  %s\n' % self.health)
                buff.write(u'Unused2\n  %s\n' % self.unused2)
            if self.modifiers is not None:
                buff.write(u'Modifiers:\n')
                for modifier in self.modifiers:
                    buff.write(u'  %s\n' % modifier)
            if self.full is not None:
                buff.write(u'Full:\n  %s\n' % self.full)
            if self.skills is not None:
                buff.write(u'Skills:\n  armorer %3d\n  athletics %3d\n  blade %3d\n  block %3d\n  blunt %3d\n  handToHand %3d\n  heavyArmor %3d\n  alchemy %3d\n  alteration %3d\n  conjuration %3d\n  destruction %3d\n  illusion %3d\n  mysticism %3d\n  restoration %3d\n  acrobatics %3d\n  lightArmor %3d\n  marksman %3d\n  mercantile %3d\n  security %3d\n  sneak %3d\n  speechcraft  %3d\n' % tuple(self.skills))
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
        with self.path.open('rb') as ins:
            buff = ins.read(size-4)
            crc32, = struct.unpack('=i',ins.read(4))
        crcNew = binascii.crc32(buff)
        if crc32 != crcNew:
            raise FileError(self.name,u'CRC32 file check failed. File: %X, Calc: %X' % (crc32,crcNew))
        #--Header
        with sio(buff) as ins:
            def unpack(format,size):
                return struct.unpack(format,ins.read(size))
            if ins.read(10) != 'PluggySave':
                raise FileError(self.name,u'File tag != "PluggySave"')
            self.version, = unpack('I',4)
            #--Reject versions earlier than 1.02
            if self.version < 0x01020000:
                raise FileError(self.name,u'Unsupported file verson: %I' % self.version)
            #--Plugins
            self.plugins = []
            type, = unpack('=B',1)
            if type != 0:
                raise FileError(self.name,u'Expected plugins record, but got %d.' % type)
            count, = unpack('=I',4)
            for x in range(count):
                espid,index,modLen = unpack('=2BI',6)
                modName = GPath(_unicode(ins.read(modLen)))
                self.plugins.append((espid,index,modName))
            #--Other
            self.other = ins.getvalue()[ins.tell():]
        deprint(struct.unpack('I',self.other[-4:]),self.path.size-8)
        #--Done
        self.valid = True

    def save(self,path=None,mtime=0):
        """Saves."""
        import binascii
        if not self.valid: raise FileError(self.name,u"File not initialized.")
        #--Buffer
        with sio() as buff:
            #--Save
            def pack(format,*args):
                buff.write(struct.pack(format,*args))
            buff.write('PluggySave')
            pack('=I',self.version)
            #--Plugins
            pack('=B',0)
            pack('=I',len(self.plugins))
            for (espid,index,modName) in self.plugins:
                modName = _encode(modName.cs)
                pack('=2BI',espid,index,len(modName))
                buff.write(modName)
            #--Other
            buff.write(self.other)
            #--End control
            buff.seek(-4,1)
            pack('=I',buff.tell())
            #--Save
            path = path or self.path
            mtime = mtime or path.exists() and path.mtime
            text = buff.getvalue()
            with path.open('wb') as out:
                out.write(text)
                out.write(struct.pack('i',binascii.crc32(text)))
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
        with self.path.open('rb') as ins:
            buff = ins.read(size)
        #--Header
        with sio(buff) as ins:
            def unpack(format,size):
                return struct.unpack(format,ins.read(size))
            self.signature = ins.read(4)
            if self.signature != 'OBSE':
                raise FileError(self.name,u'File signature != "OBSE"')
            self.formatVersion,self.obseVersion,self.obseMinorVersion,self.oblivionVersion, = unpack('IHHI',12)
            # if self.formatVersion < X:
            #   raise FileError(self.name,'Unsupported file version: %I' % self.formatVersion)
            #--Plugins
            numPlugins, = unpack('I',4)
            self.plugins = []
            for x in range(numPlugins):
                opcodeBase,numChunks,pluginLength, = unpack('III',12)
                pluginBuff = ins.read(pluginLength)
                with sio(pluginBuff) as pluginIns:
                    chunks = []
                    for y in range(numChunks):
                        chunkType = pluginIns.read(4)
                        chunkVersion,chunkLength, = struct.unpack('II',pluginIns.read(8))
                        chunkBuff = pluginIns.read(chunkLength)
                        chunk = (chunkType, chunkVersion, chunkBuff)
                        chunks.append(chunk)
                plugin = (opcodeBase,chunks)
                self.plugins.append(plugin)
        #--Done
        self.valid = True

    def save(self,path=None,mtime=0):
        """Saves."""
        if not self.valid: raise FileError(self.name,u"File not initialized.")
        #--Buffer
        with sio() as buff:
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
        with path.open('wb') as out:
            out.write(text)
        path.mtime = mtime

    def mapMasters(self,masterMap):
        """Update plugin names according to masterMap."""
        if not self.valid: raise FileError(self.name,u"File not initialized.")
        newPlugins = []
        for (opcodeBase,chunks) in self.plugins:
            newChunks = []
            if opcodeBase == 0x2330:
                for (chunkType,chunkVersion,chunkBuff) in chunks:
                    chunkTypeNum, = struct.unpack('=I',chunkType)
                    if chunkTypeNum == 1:
                        with sio(chunkBuff) as ins:
                            with sio() as buff:
                                def unpack(format,size):
                                    return struct.unpack(format,ins.read(size))
                                def pack(format,*args):
                                    buff.write(struct.pack(format,*args))
                                while ins.tell() < len(chunkBuff):
                                    espId,modId,modNameLen, = unpack('=BBI',6)
                                    modName = GPath(ins.read(modNameLen))
                                    modName = masterMap.get(modName,modName)
                                    pack('=BBI',espId,modId,len(modName.s))
                                    buff.write(modName.s.lower())
                                    chunkBuff = buff.getvalue()
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
        try:
            with path.open('rb') as ins:
                bush.game.ess.load(ins,self)
            self.pcName = _unicode(cstrip(self.pcName))
            self.pcLocation = _unicode(cstrip(self.pcLocation),bolt.pluginEncoding,avoidEncodings=('utf8','utf-8'))
            self.masters = [GPath(_unicode(x)) for x in self.masters]
        #--Errors
        except:
            deprint(u'save file error:',traceback=True)
            raise SaveFileError(path.tail,u'File header is corrupted.')
        #--Done
        ins.close()

    def writeMasters(self,path):
        """Rewrites masters of existing save file."""
        if not path.exists():
            raise SaveFileError(path.head,u'File does not exist.')
        with path.open('rb') as ins:
            with path.temp.open('wb') as out:
                oldMasters = bush.game.ess.writeMasters(ins,out,self)
        oldMasters = [GPath(_unicode(x)) for x in oldMasters]
        path.untemp()
        #--Cosaves
        masterMap = dict((x,y) for x,y in zip(oldMasters,self.masters) if x != y)
        #--Pluggy file?
        pluggyPath = CoSaves.getPaths(path)[0]
        if masterMap and pluggyPath.exists():
            pluggy = PluggyFile(pluggyPath)
            pluggy.load()
            pluggy.mapMasters(masterMap)
            pluggy.safeSave()
        #--OBSE/SKSE file?
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
        self.folderCount = 0
        self.fileCount = 0
        self.lenFolderNames = 0
        self.lenFileNames = 0
        self.fileFlags = 0
        if path: self.load(path)

    def load(self,path):
        """Extract info from save file."""
        with path.open('rb') as ins:
            try:
                #--Header
                ins.seek(4*4)
                (self.folderCount,self.fileCount,lenFolderNames,lenFileNames,fileFlags) = ins.unpack('5I',20)
            #--Errors
            except:
                raise BSAFileError(path.tail,u'File header is corrupted.')
        #--Done

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
        # TODO: This is Oblivion only code.  Needs to be refactored
        # out into oblivion.py, and a version implemented for skyrim as well
        import array
        path = self.fileInfo.getPath()
        with bolt.StructFile(path.s,'rb') as ins:
            #--Progress
            fileName = self.fileInfo.name
            progress = progress or bolt.Progress()
            progress.setFull(self.fileInfo.size)
            #--Header
            progress(0,_(u'Reading Header.'))
            self.header = ins.read(34)

            #--Save Header, pcName
            gameHeaderSize, = ins.unpack('I',4)
            self.saveNum,pcNameSize, = ins.unpack('=IB',5)
            self.pcName = _unicode(cstrip(ins.read(pcNameSize)))
            self.postNameHeader = ins.read(gameHeaderSize-5-pcNameSize)

            #--Masters
            del self.masters[:]
            numMasters, = ins.unpack('B',1)
            for count in range(numMasters):
                size, = ins.unpack('B',1)
                self.masters.append(GPath(_unicode(ins.read(size))))

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
            with sio() as buff:
                for count in range(4):
                    size, = ins.unpack('H',2)
                    insCopy(buff,size,2)
                insCopy(buff,4) #--Supposedly part of created info, but sticking it here since I don't decode it.
                self.preCreated = buff.getvalue()
            #--Created (ALCH,SPEL,ENCH,WEAP,CLOTH,ARMO, etc.?)
            modReader = ModReader(self.fileInfo.name,ins)
            createdNum, = ins.unpack('I',4)
            for count in xrange(createdNum):
                progress(ins.tell(),_(u'Reading created...'))
                header = ins.unpack('4s4I',20)
                self.created.append(MreRecord(ModReader.recHeader(*header),modReader))
            #--Pre-records: Quickkeys, reticule, interface, regions
            with sio() as buff:
                for count in range(4):
                    size, = ins.unpack('H',2)
                    insCopy(buff,size,2)
                self.preRecords = buff.getvalue()

            #--Records
            for count in xrange(recordsNum):
                progress(ins.tell(),_(u'Reading records...'))
                (fid,recType,flags,version,size) = ins.unpack('=IBIBH',12)
                data = ins.read(size)
                self.records.append((fid,recType,flags,version,data))

            #--Temp Effects, fids, worldids
            progress(ins.tell(),_(u'Reading fids, worldids...'))
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
        progress(progress.full,_(u'Finished reading.'))

    def save(self,outPath=None,progress=None):
        """Save data to file.
        outPath -- Path of the output file to write to. Defaults to original file path."""
        if not self.canSave: raise StateError(u"Insufficient data to write file.")
        outPath = outPath or self.fileInfo.getPath()
        with outPath.open('wb') as out:
            def pack(format,*data):
                out.write(struct.pack(format,*data))
            #--Progress
            fileName = self.fileInfo.name
            progress = progress or bolt.Progress()
            progress.setFull(self.fileInfo.size)
            #--Header
            progress(0,_(u'Writing Header.'))
            out.write(self.header)
            #--Save Header
            pcName = _encode(self.pcName)
            pack('=IIB',5+len(pcName)+1+len(self.postNameHeader),
                self.saveNum, len(pcName)+1)
            out.write(pcName)
            out.write('\x00')
            out.write(self.postNameHeader)
            #--Masters
            pack('B',len(self.masters))
            for master in self.masters:
                name = _encode(master.s)
                pack('B',len(name))
                out.write(name)
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
            progress(0.1,_(u'Writing created.'))
            modWriter = ModWriter(out)
            pack('I',len(self.created))
            for record in self.created:
                record.dump(modWriter)
            #--Pre-records
            out.write(self.preRecords)
            #--Records, temp effects, fids, worldspaces
            progress(0.2,_(u'Writing records.'))
            for fid,recType,flags,version,data in self.records:
                pack('=IBIBH',fid,recType,flags,version,len(data))
                out.write(data)
            #--Temp Effects, fids, worldids
            pack('I',len(self.tempEffects))
            out.write(self.tempEffects)
            #--Fids
            progress(0.9,_(u'Writing fids, worldids.'))
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
            progress(1.0,_(u'Writing complete.'))

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
        if self.fid_createdNum is None: self.indexCreated()
        recNum = self.fid_createdNum.get(fid)
        if recNum is None:
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
        if self.fid_recNum is None: self.indexRecords()
        recNum = self.fid_recNum.get(fid)
        if recNum is None:
            return default
        else:
            return self.records[recNum]

    def setRecord(self,record):
        """Sets records where record = (fid,recType,flags,version,data)."""
        if self.fid_recNum is None: self.indexRecords()
        fid = record[0]
        recNum = self.fid_recNum.get(fid,-1)
        if recNum == -1:
            self.records.append(record)
            self.fid_recNum[fid] = len(self.records)-1
        else:
            self.records[recNum] = record

    def removeRecord(self,fid):
        """Removes record if it exists. Returns True if record existed, false if not."""
        if self.fid_recNum is None: self.indexRecords()
        recNum = self.fid_recNum.get(fid)
        if recNum is None:
            return False
        else:
            del self.records[recNum]
            del self.fid_recNum[fid]
            return True

    def getShortMapper(self):
        """Returns a mapping function to map long fids to short fids."""
        indices = dict([(name,index) for index,name in enumerate(self.masters)])
        def mapper(fid):
            if fid is None: return None
            modName,object = fid
            mod = indices[modName]
            return (long(mod) << 24 ) | long(object)
        return mapper

    def getFid(self,iref,default=None):
        """Returns fid corresponding to iref."""
        if not iref: return default
        if iref >> 24 == 0xFF: return iref
        if iref >= len(self.fids): raise ModError(u'IRef from Mars.')
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
                return _(u'Missing Master ')+hex(modIndex)
        #--ABomb
        (tesClassSize,abombCounter,abombFloat) = self.getAbomb()
        log.setHeader(_(u'Abomb Counter'))
        log(_(u'  Integer:\t0x%08X') % abombCounter)
        log(_(u'  Float:\t%.2f') % abombFloat)
        #--FBomb
        log.setHeader(_(u'Fbomb Counter'))
        log(_(u'  Next in-game object: %08X') % struct.unpack('I',self.preGlobals[:4]))
        #--Array Sizes
        log.setHeader(u'Array Sizes')
        log(u'  %d\t%s' % (len(self.created),_(u'Created Items')))
        log(u'  %d\t%s' % (len(self.records),_(u'Records')))
        log(u'  %d\t%s' % (len(self.fids),_(u'Fids')))
        #--Created Types
        log.setHeader(_(u'Created Items'))
        createdHisto = {}
        id_created = {}
        for citem in self.created:
            count,size = createdHisto.get(citem.recType,(0,0))
            createdHisto[citem.recType] =  (count + 1,size + citem.size)
            id_created[citem.fid] = citem
        for type in sorted(createdHisto.keys()):
            count,size = createdHisto[type]
            log(u'  %d\t%d kb\t%s' % (count,size/1024,type))
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
        log.setHeader(_(u'Fids'))
        log(u'  Refed\tChanged\tMI    Mod Name')
        log(u'  %d\t\t     Lost Refs (Fid == 0)' % lostRefs)
        for modIndex,(irefed,changed) in enumerate(zip(idHist,changeHisto)):
            if irefed or changed:
                log(u'  %d\t%d\t%02X   %s' % (irefed,changed,modIndex,getMaster(modIndex)))
        #--Lost Changes
        if lostChanges:
            log.setHeader(_(u'LostChanges'))
            for id in sorted(lostChanges.keys()):
                type = lostChanges[id][1]
                log(hex(id)+saveRecTypes.get(type,unicode(type)))
        for type in sorted(typeModHisto.keys()):
            modHisto = typeModHisto[type]
            log.setHeader(u'%d %s' % (type,saveRecTypes.get(type,_(u'Unknown')),))
            for modIndex,count in enumerate(modHisto):
                if count: log(u'  %d\t%s' % (count,getMaster(modIndex)))
            log(u'  %d\tTotal' % (sum(modHisto),))
        objRefBases = dict((key,value) for key,value in objRefBases.iteritems() if value[0] > 100)
        log.setHeader(_(u'New ObjectRef Bases'))
        if objRefNullBases:
            log(u' Null Bases: %s' % objRefNullBases)
        if objRefBases:
            log(_(u' Count IRef     BaseId'))
            for iref in sorted(objRefBases.keys()):
                count,cumSize = objRefBases[iref]
                if iref >> 24 == 255:
                    parentid = iref
                else:
                    parentid = self.fids[iref]
                log(u'%6d %08X %08X %6d kb' % (count,iref,parentid,cumSize/1024))

    def logStatObse(self,log=None):
        """Print stats to log."""
        log = log or bolt.Log()
        obseFileName = self.fileInfo.getPath().root+u'.'+bush.game.se.shortName.lower()
        obseFile = ObseFile(obseFileName)
        obseFile.load()
        #--Header
        log.setHeader(_(u'Header'))
        log(u'=' * 80)
        log(_(u'  Format version:   %08X') % (obseFile.formatVersion,))
        log(_(u'  OBSE version:     %u.%u') % (obseFile.obseVersion,obseFile.obseMinorVersion,))
        log(_(u'  Oblivion version: %08X') % (obseFile.oblivionVersion,))
        #--Plugins
        if obseFile.plugins is not None:
            for (opcodeBase,chunks) in obseFile.plugins:
                log.setHeader(_(u'Plugin opcode=%08X chunkNum=%u') % (opcodeBase,len(chunks),))
                log(u'=' * 80)
                log(_(u'  Type  Ver   Size'))
                log(u'-' * 80)
                espMap = {}
                for (chunkType,chunkVersion,chunkBuff) in chunks:
                    chunkTypeNum, = struct.unpack('=I',chunkType)
                    if chunkType[0] >= ' ' and chunkType[3] >= ' ':
                        log(u'  %4s  %-4u  %08X' % (chunkType,chunkVersion,len(chunkBuff)))
                    else:
                        log(u'  %04X  %-4u  %08X' % (chunkTypeNum,chunkVersion,len(chunkBuff)))
                    with sio(chunkBuff) as ins:
                        def unpack(format,size):
                            return struct.unpack(format,ins.read(size))
                        if opcodeBase == 0x1400:  # OBSE
                            if chunkType == 'RVTS':
                                #--OBSE String
                                modIndex,stringID,stringLength, = unpack('=BIH',7)
                                stringData = ins.read(stringLength)
                                log(u'    '+_(u'Mod :')+u'  %02X (%s)' % (modIndex, self.masters[modIndex].s))
                                log(u'    '+_(u'ID  :')+u'  %u' % stringID)
                                log(u'    '+_(u'Data:')+u'  %s' % stringData)
                            elif chunkType == 'RVRA':
                                #--OBSE Array
                                modIndex,arrayID,keyType,isPacked, = unpack('=BIBB',7)
                                if modIndex == 255:
                                    log(_(u'    Mod :  %02X (Save File)') % modIndex)
                                else:
                                    log(_(u'    Mod :  %02X (%s)') % (modIndex, self.masters[modIndex].s))
                                log(_(u'    ID  :  %u') % arrayID)
                                if keyType == 1: #Numeric
                                    if isPacked:
                                        log(_(u'    Type:  Array'))
                                    else:
                                        log(_(u'    Type:  Map'))
                                elif keyType == 3:
                                    log(_(u'    Type:  StringMap'))
                                else:
                                    log(_(u'    Type:  Unknown'))
                                if chunkVersion >= 1:
                                    numRefs, = unpack('=I',4)
                                    if numRefs > 0:
                                        log(u'    Refs:')
                                        for x in range(numRefs):
                                            refModID, = unpack('=B',1)
                                            if refModID == 255:
                                                log(_(u'      %02X (Save File)') % refModID)
                                            else:
                                                log(u'      %02X (%s)' % (refModID, self.masters[refModID].s))
                                numElements, = unpack('=I',4)
                                log(_(u'    Size:  %u') % numElements)
                                for i in range(numElements):
                                    if keyType == 1:
                                        key, = unpack('=d',8)
                                        keyStr = u'%f' % key
                                    elif keyType == 3:
                                        keyLen, = unpack('=H',2)
                                        key = ins.read(keyLen)
                                        keyStr = _unicode(key)
                                    else:
                                        keyStr = 'BAD'
                                    dataType, = unpack('=B',1)
                                    if dataType == 1:
                                        data, = unpack('=d',8)
                                        dataStr = u'%f' % data
                                    elif dataType == 2:
                                        data, = unpack('=I',4)
                                        dataStr = u'%08X' % data
                                    elif dataType == 3:
                                        dataLen, = unpack('=H',2)
                                        data = ins.read(dataLen)
                                        dataStr = _unicode(data)
                                    elif dataType == 4:
                                        data, = unpack('=I',4)
                                        dataStr = u'%u' % data
                                    log(u'    [%s]:%s = %s' % (keyStr,(u'BAD',u'NUM',u'REF',u'STR',u'ARR')[dataType],dataStr))
                        elif opcodeBase == 0x2330:    # Pluggy
                            if chunkTypeNum == 1:
                                #--Pluggy TypeESP
                                log(_(u'    Pluggy ESPs'))
                                log(_(u'    EID   ID    Name'))
                                while ins.tell() < len(chunkBuff):
                                    if chunkVersion == 2:
                                        espId,modId, = unpack('=BB', 2)
                                        log(u'    %02X    %02X' % (espId,modId))
                                        espMap[modId] = espId
                                    else: #elif chunkVersion == 1"
                                        espId,modId,modNameLen, = unpack('=BBI',6)
                                        modName = ins.read(modNameLen)
                                        log(u'    %02X    %02X    %s' % (espId,modId,modName))
                                        espMap[modId] = modName # was [espId]
                            elif chunkTypeNum == 2:
                                #--Pluggy TypeSTR
                                log(_(u'    Pluggy String'))
                                strId,modId,strFlags, = unpack('=IBB',6)
                                strData = ins.read(len(chunkBuff) - ins.tell())
                                log(u'      '+_(u'StrID :')+u' %u' % strId)
                                log(u'      '+_(u'ModID :')+u' %02X %s' % (modId,espMap[modId] if modId in espMap else u'ERROR',))
                                log(u'      '+_(u'Flags :')+u' %u' % strFlags)
                                log(u'      '+_(u'Data  :')+u' %s' % strData)
                            elif chunkTypeNum == 3:
                                #--Pluggy TypeArray
                                log(_(u'    Pluggy Array'))
                                arrId,modId,arrFlags,arrSize, = unpack('=IBBI',10)
                                log(_(u'      ArrID : %u') % (arrId,))
                                log(_(u'      ModID : %02X %s') % (modId,espMap[modId] if modId in espMap else u'ERROR',))
                                log(_(u'      Flags : %u') % (arrFlags,))
                                log(_(u'      Size  : %u') % (arrSize,))
                                while ins.tell() < len(chunkBuff):
                                    elemIdx,elemType, = unpack('=IB',5)
                                    elemStr = ins.read(4)
                                    if elemType == 0: #--Integer
                                        elem, = struct.unpack('=i',elemStr)
                                        log(u'        [%u]  INT  %d' % (elemIdx,elem,))
                                    elif elemType == 1: #--Ref
                                        elem, = struct.unpack('=I',elemStr)
                                        log(u'        [%u]  REF  %08X' % (elemIdx,elem,))
                                    elif elemType == 2: #--Float
                                        elem, = struct.unpack('=f',elemStr)
                                        log(u'        [%u]  FLT  %08X' % (elemIdx,elem,))
                            elif chunkTypeNum == 4:
                                #--Pluggy TypeName
                                log(_(u'    Pluggy Name'))
                                refId, = unpack('=I',4)
                                refName = ins.read(len(chunkBuff) - ins.tell())
                                newName = u''
                                for i in range(len(refName)):
                                    ch = refName[i] if ((refName[i] >= chr(0x20)) and (refName[i] < chr(0x80))) else '.'
                                    newName = newName + ch
                                log(_(u'      RefID : %08X') % refId)
                                log(_(u'      Name  : %s') % _unicode(newName))
                            elif chunkTypeNum == 5:
                                #--Pluggy TypeScr
                                log(_(u'    Pluggy ScreenSize'))
                                #UNTESTED - uncomment following line to skip this record type
                                #continue
                                scrW,scrH, = unpack('=II',8)
                                log(_(u'      Width  : %u') % scrW)
                                log(_(u'      Height : %u') % scrH)
                            elif chunkTypeNum == 6:
                                #--Pluggy TypeHudS
                                log(u'    '+_(u'Pluggy HudS'))
                                #UNTESTED - uncomment following line to skip this record type
                                #continue
                                hudSid,modId,hudFlags,hudRootID,hudShow,hudPosX,hudPosY,hudDepth,hudScaleX,hudScaleY,hudAlpha,hudAlignment,hudAutoScale, = unpack('=IBBBBffhffBBB',29)
                                hudFileName = _unicode(ins.read(len(chunkBuff) - ins.tell()))
                                log(u'      '+_(u'HudSID :')+u' %u' % hudSid)
                                log(u'      '+_(u'ModID  :')+u' %02X %s' % (modId,espMap[modId] if modId in espMap else u'ERROR',))
                                log(u'      '+_(u'Flags  :')+u' %02X' % hudFlags)
                                log(u'      '+_(u'RootID :')+u' %u' % hudRootID)
                                log(u'      '+_(u'Show   :')+u' %02X' % hudShow)
                                log(u'      '+_(u'Pos    :')+u' %f,%f' % (hudPosX,hudPosY,))
                                log(u'      '+_(u'Depth  :')+u' %u' % hudDepth)
                                log(u'      '+_(u'Scale  :')+u' %f,%f' % (hudScaleX,hudScaleY,))
                                log(u'      '+_(u'Alpha  :')+u' %02X' % hudAlpha)
                                log(u'      '+_(u'Align  :')+u' %02X' % hudAlignment)
                                log(u'      '+_(u'AutoSc :')+u' %02X' % hudAutoScale)
                                log(u'      '+_(u'File   :')+u' %s' % hudFileName)
                            elif chunkTypeNum == 7:
                                #--Pluggy TypeHudT
                                log(_(u'    Pluggy HudT'))
                                #UNTESTED - uncomment following line to skip this record type
                                #continue
                                hudTid,modId,hudFlags,hudShow,hudPosX,hudPosY,hudDepth, = unpack('=IBBBffh',17)
                                hudScaleX,hudScaleY,hudAlpha,hudAlignment,hudAutoScale,hudWidth,hudHeight,hudFormat, = unpack('=ffBBBIIB',20)
                                hudFontNameLen, = unpack('=I',4)
                                hudFontName = _unicode(ins.read(hudFontNameLen))
                                hudFontHeight,hudFontWidth,hudWeight,hudItalic,hudFontR,hudFontG,hudFontB, = unpack('=IIhBBBB',14)
                                hudText = _unicode(ins.read(len(chunkBuff) - ins.tell()))
                                log(u'      '+_(u'HudTID :')+u' %u' % hudTid)
                                log(u'      '+_(u'ModID  :')+u' %02X %s' % (modId,espMap[modId] if modId in espMap else u'ERROR',))
                                log(u'      '+_(u'Flags  :')+u' %02X' % hudFlags)
                                log(u'      '+_(u'Show   :')+u' %02X' % hudShow)
                                log(u'      '+_(u'Pos    :')+u' %f,%f' % (hudPosX,hudPosY,))
                                log(u'      '+_(u'Depth  :')+u' %u' % hudDepth)
                                log(u'      '+_(u'Scale  :')+u' %f,%f' % (hudScaleX,hudScaleY,))
                                log(u'      '+_(u'Alpha  :')+u' %02X' % hudAlpha)
                                log(u'      '+_(u'Align  :')+u' %02X' % hudAlignment)
                                log(u'      '+_(u'AutoSc :')+u' %02X' % hudAutoScale)
                                log(u'      '+_(u'Width  :')+u' %u' % hudWidth)
                                log(u'      '+_(u'Height :')+u' %u' % hudHeight)
                                log(u'      '+_(u'Format :')+u' %u' % hudFormat)
                                log(u'      '+_(u'FName  :')+u' %s' % hudFontName)
                                log(u'      '+_(u'FHght  :')+u' %u' % hudFontHeight)
                                log(u'      '+_(u'FWdth  :')+u' %u' % hudFontWidth)
                                log(u'      '+_(u'FWeigh :')+u' %u' % hudWeight)
                                log(u'      '+_(u'FItal  :')+u' %u' % hudItalic)
                                log(u'      '+_(u'FRGB   :')+u' %u,%u,%u' % (hudFontR,hudFontG,hudFontB,))
                                log(u'      '+_(u'FText  :')+u' %s' % hudText)

    def findBloating(self,progress=None):
        """Analyzes file for bloating. Returns (createdCounts,nullRefCount)."""
        nullRefCount = 0
        createdCounts = {}
        progress = progress or bolt.Progress()
        progress.setFull(len(self.created)+len(self.records))
        #--Created objects
        progress(0,_(u'Scanning created objects'))
        fullAttr = 'full'
        for citem in self.created:
            if fullAttr in citem.__class__.__slots__:
                full = citem.__getattribute__(fullAttr)
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
        progress(len(self.created),_(u'Scanning change records.'))
        fids = self.fids
        for record in self.records:
            fid,recType,flags,version,data = record
            if recType == 49 and fid >> 24 == 0xFF and (flags & 2):
                iref, = struct.unpack('I',data[4:8])
                if iref >> 24 != 0xFF and fids[iref] == 0:
                    nullRefCount += 1
            progress.plus()
        return createdCounts,nullRefCount

    def removeBloating(self,uncreateKeys,removeNullRefs=True,progress=None):
        """Removes duplicated created items and null refs."""
        numUncreated = numUnCreChanged = numUnNulled = 0
        progress = progress or bolt.Progress()
        progress.setFull((len(uncreateKeys) and len(self.created))+len(self.records))
        uncreated = set()
        #--Uncreate
        if uncreateKeys:
            progress(0,_(u'Scanning created objects'))
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
        progress(progress.state,_(u'Scanning change records.'))
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
        return numUncreated,numUnCreChanged,numUnNulled

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
        return tesClassSize,abombCounter,abombFloat

    def setAbomb(self,value=0x41000000):
        """Resets abomb counter to specified value."""
        data = self.preCreated
        tesClassSize, = struct.unpack('H',data[:2])
        if tesClassSize < 4: return
        with sio() as buff:
            buff.write(data)
            buff.seek(2+tesClassSize-4)
            buff.write(struct.pack('I',value))
            self.preCreated = buff.getvalue()

#------------------------------------------------------------------------------
class CoSaves:
    """Handles co-files (.pluggy, .obse, .skse) for saves."""
    reSave  = re.compile(r'\.ess(f?)$',re.I)

    @staticmethod
    def getPaths(savePath):
        """Returns cofile paths."""
        maSave = CoSaves.reSave.search(savePath.s)
        if maSave: savePath = savePath.root
        first = maSave and maSave.group(1) or u''
        return tuple(savePath+ext+first
                     for ext in (u'.pluggy',u'.'+bush.game.se.shortName.lower()))

    def __init__(self,savePath,saveName=None):
        """Initialize with savePath."""
        if saveName: savePath = savePath.join(saveName)
        self.savePath = savePath
        self.paths = CoSaves.getPaths(savePath)

    def delete(self,askOk=False,dontRecycle=False):
        """Deletes cofiles."""
        for path in self.paths:
            if path.exists():
                balt.shellDelete(path,askOk=askOk,recycle=not dontRecycle)

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
        cPluggy,cObse = (u'',u'')
        save = self.savePath
        pluggy,obse = self.paths
        if pluggy.exists():
            cPluggy = u'XP'[abs(pluggy.mtime - save.mtime) < 10]
        if obse.exists():
            cObse = u'XO'[abs(obse.mtime - save.mtime) < 10]
        return cObse,cPluggy

# File System -----------------------------------------------------------------
#------------------------------------------------------------------------------
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
        if   ext == u'.kf':  hash1 |= 0x80
        elif ext == u'.nif': hash1 |= 0x8000
        elif ext == u'.dds': hash1 |= 0x8080
        elif ext == u'.wav': hash1 |= 0x80000000
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
        self.path = path
        self.folderInfos = None

    def scan(self):
        """Reports on contents."""
        with bolt.StructFile(self.path.s,'rb') as ins:
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
                    fileInfos.append([hash,size,offset,u'',filePos])
            #--File Names
            fileNames = [_unicode(x) for x in ins.read(lenFileNames).split('\x00')[:-1]]
            namesIter = iter(fileNames)
            for folderInfo in folderInfos:
                fileInfos = folderInfo[-1]
                for index,fileInfo in enumerate(fileInfos):
                    fileInfo[3] = namesIter.next()
        #--Done

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
        backupDir = modInfos.bashDir.join(u'Backups')
        backupDir.makedirs()
        backup = backupDir.join(self.path.tail)+u'f'
        if not backup.exists():
            progress(0,_(u"Backing up BSA file. This will take a while..."))
            self.path.copyTo(backup)

    def updateAIText(self,files=None):
        """Update aiText with specified files. (Or remove, if files == None.)"""
        aiPath = dirs['app'].join(u'ArchiveInvalidation.txt')
        if not files:
            aiPath.remove()
            return
        #--Archive invalidation
        aiText = re.sub(ur'\\',u'/',u'\n'.join(files))
        with aiPath.open('w'):
            write(aiText)

    def resetMTimes(self):
        """Reset dates of bsa files to 'correct' values."""
        #--Fix the data of a few archive files
        bsaTimes = (
            (u'Oblivion - Meshes.bsa',1138575220),
            (u'Oblivion - Misc.bsa',1139433736),
            (u'Oblivion - Sounds.bsa',1138660560),
            (inisettings['OblivionTexturesBSAName'].stail,1138162634),
            (u'Oblivion - Voices1.bsa',1138162934),
            (u'Oblivion - Voices2.bsa',1138166742),
            )
        for bsaFile,mtime in bsaTimes:
            dirs['mods'].join(bsaFile).mtime = mtime

    def reset(self,progress=None):
        """Resets BSA archive hashes to correct values."""
        with bolt.StructFile(self.path.s,'r+b') as ios:
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
        self.resetMTimes()
        self.updateAIText()
        return resetCount

    def invalidate(self,progress=None):
        """Invalidates entries in BSA archive and regenerates Archive Invalidation.txt."""
        reRepTexture = re.compile(ur'(?<!_[gn])\.dds',re.I|re.U)
        with bolt.StructFile(self.path.s,'r+b') as ios:
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
        self.resetMTimes()
        self.updateAIText(intxt)
        #--Done
        return reset,inval,intxt

#------------------------------------------------------------------------------
class IniFile(object):
    """Any old ini file."""
    reComment = re.compile(u';.*',re.U)
    reDeletedSetting = re.compile(ur';-\s*(\w.*?)\s*(;.*$|=.*$|$)',re.U)
    reSection = re.compile(ur'^\[\s*(.+?)\s*\]$',re.U)
    reSetting = re.compile(ur'(.+?)\s*=(.*)',re.U)
    encoding = 'utf-8'

    def __init__(self,path,defaultSection=u'General'):
        self.path = path
        self.defaultSection = defaultSection
        self.isCorrupted = False

    @staticmethod
    def formatMatch(path):
        count = 0
        with path.open('r') as file:
            for line in file:
                stripped = IniFile.reComment.sub('',line).strip()
                maSetting = IniFile.reSetting.match(stripped)
                if maSetting:
                    count += 1
                    continue
                maSection = IniFile.reSection.match(stripped)
                if maSection:
                    count += 1
                    continue
        return count

    def getSetting(self,section,key,default=None):
        """Gets a single setting from the file."""
        section,key = map(bolt.LString,(section,key))
        ini_settings,deleted_settings = self.getSettings()
        if section in ini_settings:
            return ini_settings[section].get(key,default)
        else:
            return default

    def getSettings(self):
        """Gets settings for self."""
        return self.getTweakFileSettings(self.path,True)

    def getTweakFileSettings(self,tweakPath,setCorrupted=False,lineNumbers=False):
        """Gets settings in a tweak file."""
        ini_settings = {}
        deleted_settings = {}
        if not tweakPath.exists() or tweakPath.isdir():
            return ini_settings,deleted_settings
        if tweakPath != self.path:
            encoding = 'utf-8'
        else:
            encoding = self.encoding
        reComment = self.reComment
        reSection = self.reSection
        reDeleted = self.reDeletedSetting
        reSetting = self.reSetting
        if lineNumbers:
            def makeSetting(match,lineNo): return match.group(2).strip(),lineNo
        else:
            def makeSetting(match,lineNo): return match.group(2).strip()
        #--Read ini file
        with tweakPath.open('r') as iniFile:
            sectionSettings = None
            section = None
            for i,line in enumerate(iniFile.readlines()):
                try:
                    line = unicode(line,encoding)
                except UnicodeDecodeError:
                    line = unicode(line,'cp1252')
                maDeleted = reDeleted.match(line)
                stripped = reComment.sub(u'',line).strip()
                maSection = reSection.match(stripped)
                maSetting = reSetting.match(stripped)
                if maSection:
                    section = LString(maSection.group(1))
                    sectionSettings = ini_settings.setdefault(section,{})
                elif maSetting:
                    if sectionSettings is None:
                        sectionSettings = ini_settings.setdefault(LString(self.defaultSection),{})
                        if setCorrupted: self.isCorrupted = True
                    sectionSettings[LString(maSetting.group(1))] = makeSetting(maSetting,i)
                elif maDeleted:
                    if not section: continue
                    deleted_settings.setdefault(section,{})[LString(maDeleted.group(1))] = i
        return ini_settings,deleted_settings

    def getTweakFileLines(self,tweakPath):
        """Get a line by line breakdown of the tweak file, in this format:
        [(fulltext,section,setting,value,status,ini_line_number)]
        where:
        fulltext = full line of text from the ini
        section = the section that is being edited
        setting = the setting that is being edited
        value = the value the setting is being set to
        status:
            -10: doesn't exist in the ini
              0: does exist, but it's a heading or something else without a value
             10: does exist, but value isn't the same
             20: does exist, and value is the same
        ini_line_number = line number in the ini that this tweak applies to"""
        lines = []
        if not tweakPath.exists() or tweakPath.isdir():
            return lines
        if tweakPath != self.path:
            encoding = 'utf-8'
        else:
            encoding = self.encoding
        iniSettings,deletedSettings = self.getTweakFileSettings(self.path,True,True)
        reComment = self.reComment
        reSection = self.reSection
        reDeleted = self.reDeletedSetting
        reSetting = self.reSetting
        #--Read ini file
        with tweakPath.open('r') as iniFile:
            section = LString(self.defaultSection)
            for i,line in enumerate(iniFile.readlines()):
                try:
                    line = unicode(line,encoding)
                except UnicodeDecodeError:
                    line = unicode(line,'cp1252')
                maDeletedSetting = reDeleted.match(line)
                stripped = reComment.sub(u'',line).strip()
                maSection = reSection.match(stripped)
                maSetting = reSetting.match(stripped)
                deleted = False
                setting = None
                value = LString(u'')
                status = 0
                lineNo = -1
                if maSection:
                    section = LString(maSection.group(1))
                    if section not in iniSettings:
                        status = -10
                elif maSetting:
                    if section in iniSettings:
                        setting = LString(maSetting.group(1))
                        if setting in iniSettings[section]:
                            value = LString(maSetting.group(2).strip())
                            lineNo = iniSettings[section][setting][1]
                            if iniSettings[section][setting][0] == value:
                                status = 20
                            else:
                                status = 10
                        else:
                            status = -10
                        setting = setting._s
                    else:
                        status = -10
                elif maDeletedSetting:
                    setting = LString(maDeletedSetting.group(1))
                    status = 20
                    if section in iniSettings and setting in iniSettings[section]:
                        lineNo = iniSettings[section][setting][1]
                        status = 10
                    elif section in deletedSettings and setting in deletedSettings[section]:
                        lineNo = deletedSettings[section][setting]
                    deleted = True
                else:
                    if stripped:
                        status = -10
                lines.append((line.rstrip(),section._s,setting,value._s,status,lineNo,deleted))
        return lines

    def saveSetting(self,section,key,value):
        """Changes a single setting in the file."""
        ini_settings = {section:{key:value}}
        self.saveSettings(ini_settings)

    def saveSettings(self,ini_settings,deleted_settings={}):
        """Applies dictionary of settings to ini file.
        Values in settings dictionary can be either actual values or
        full key=value line ending in newline char."""
        if not self.path.exists() or not self.path.isfile():
            return
        #--Ensure settings dicts are using LString's as keys
        ini_settings = dict((LString(x),dict((LString(u),v) for u,v in y.iteritems()))
            for x,y in ini_settings.iteritems())
        deleted_settings = dict((LString(x),set(LString(u) for u in y))
            for x,y in deleted_settings.iteritems())
        reDeleted = self.reDeletedSetting
        reComment = self.reComment
        reSection = self.reSection
        reSetting = self.reSetting
        #--Read init, write temp
        section = sectionSettings = None
        with self.path.open('r') as iniFile:
            with self.path.temp.open('w',encoding=self.encoding) as tmpFile:
                tmpFileWrite = tmpFile.write
                for line in iniFile:
                    try:
                        line = unicode(line,self.encoding)
                    except UnicodeDecodeError:
                        line = unicode(line,'cp1252')
                    maDeleted = reDeleted.match(line)
                    stripped = reComment.sub(u'',line).strip()
                    maSection = reSection.match(stripped)
                    maSetting = reSetting.match(stripped)
                    if maSection:
                        if section and ini_settings.get(section,{}):
                            # There are 'new' entries still to be added
                            for setting in ini_settings[section]:
                                value = ini_settings[section][setting]
                                if isinstance(value,basestring) and value[-1:] == u'\n':
                                    tmpFileWrite(value)
                                else:
                                    tmpFileWrite(u'%s=%s\n' % (setting,value))
                            del ini_settings[section]
                            tmpFileWrite(u'\n')
                        section = LString(maSection.group(1))
                        sectionSettings = ini_settings.get(section,{})
                    elif maSetting or maDeleted:
                        if maSetting: match = maSetting
                        else: match = maDeleted
                        setting = LString(match.group(1))
                        if sectionSettings and setting in sectionSettings:
                            value = sectionSettings[setting]
                            if isinstance(value,basestring) and value[-1:] == u'\n':
                                line = value
                            else:
                                line = u'%s=%s\n' % (setting,value)
                            del sectionSettings[setting]
                        elif section in deleted_settings and setting in deleted_settings[section]:
                            line = u';-'+line
                    tmpFileWrite(line)
                # Add remaining new entries
                if section and section in ini_settings:
                    # This will occur for the last INI section in the ini file
                    for setting in ini_settings[section]:
                        value = ini_settings[section][setting]
                        if isinstance(value,basestring) and value[-1:] == u'\n':
                            tmpFileWrite(value)
                        else:
                            tmpFileWrite(u'%s=%s\n' % (setting,value))
                    tmpFileWrite(u'\n')
                    del ini_settings[section]
                for section in ini_settings:
                    if ini_settings[section]:
                        tmpFileWrite(u'\n')
                        tmpFileWrite(u'[%s]\n' % section)
                        for setting in ini_settings[section]:
                            value = ini_settings[section][setting]
                            if isinstance(value,basestring) and value[-1:] == u'\n':
                                tmpFileWrite(value)
                            else:
                                tmpFileWrite(u'%s=%s\n' % (setting,value))
                        tmpFileWrite(u'\n')
        #--Done
        self.path.untemp()

    def applyTweakFile(self,tweakPath):
        """Read Ini tweak file and apply its settings to oblivion.ini.
        Note: Will ONLY apply settings that already exist."""
        if not self.path.exists() or not self.path.isfile():
            return
        if not tweakPath.exists() or not tweakPath.isfile():
            return
        if tweakPath != self.path:
            encoding = 'utf-8'
        else:
            encoding = self.encoding
        reDeleted = self.reDeletedSetting
        reComment = self.reComment
        reSection = self.reSection
        reSetting = self.reSetting
        #--Read Tweak file
        with tweakPath.open('r') as tweakFile:
            ini_settings = {}
            deleted_settings = {}
            section = sectionSettings = None
            for line in tweakFile:
                try:
                    line = unicode(line,encoding)
                except UnicodeDecodeError:
                    line = unicode(line,'cp1252')
                maDeleted = reDeleted.match(line)
                stripped = reComment.sub(u'',line).strip()
                maSection = reSection.match(stripped)
                maSetting = reSetting.match(stripped)
                if maSection:
                    section = LString(maSection.group(1))
                    sectionSettings = ini_settings[section] = {}
                elif maSetting:
                    if line[-1:] != u'\n': line += u'\r\n' #--Make sure has trailing new line
                    sectionSettings[LString(maSetting.group(1))] = line
                elif maDeleted:
                    deleted_settings.setdefault(section,set()).add(LString(maDeleted.group(1)))
        self.saveSettings(ini_settings,deleted_settings)

#------------------------------------------------------------------------------
def BestIniFile(path):
    if not path:
        return oblivionIni
    for ini in gameInis:
        if path == ini.path:
            return ini
    INICount = IniFile.formatMatch(path)
    OBSECount = OBSEIniFile.formatMatch(path)
    if INICount >= OBSECount:
        return IniFile(path)
    else:
        return OBSEIniFile(path)

class OBSEIniFile(IniFile):
    """OBSE Configuration ini file.  Minimal support provided, only can
    handle 'set' and 'setGS' statements."""
    reDeleted = re.compile(ur';-(\w.*?)$',re.U)
    reSet     = re.compile(ur'\s*set\s+(.+?)\s+to\s+(.*)', re.I|re.U)
    reSetGS   = re.compile(ur'\s*setGS\s+(.+?)\s+(.*)', re.I|re.U)

    def __init__(self,path,defaultSection=u''):
        """Change the default section to something that can't
        occur in a normal ini"""
        IniFile.__init__(self,path,u'')

    @staticmethod
    def formatMatch(path):
        count = 0
        with path.open('r') as file:
            for line in file:
                stripped = OBSEIniFile.reComment.sub(u'',line).strip()
                maSet = OBSEIniFile.reSet.match(stripped)
                if maSet:
                    count += 1
                    continue
                maSetGS = OBSEIniFile.reSetGS.match(stripped)
                if maSetGS:
                    count += 1
                    continue
        return count

    def getSetting(self,section,key,default=None):
        lstr = LString(section)
        if lstr == u'set': section = u']set['
        elif lstr == u'setGS': section = u']setGS['
        return IniFile.getSetting(self,section,key,default)

    def getTweakFileSettings(self,tweakPath,setCorrupted=False,lineNumbers=False):
        """Get the settings in the ini script."""
        ini_settings = {}
        deleted_settings = {}
        if not tweakPath.exists() or tweakPath.isdir():
            return ini_settings,deleted_settings
        reDeleted = self.reDeleted
        reComment = self.reComment
        reSet = self.reSet
        reSetGS = self.reSetGS
        with tweakPath.open('r') as iniFile:
            for i,line in enumerate(iniFile.readlines()):
                maDeleted = reDeleted.match(line)
                if maDeleted:  line = maDeleted.group(1)
                stripped = reComment.sub(u'',line).strip()
                maSet   = reSet.match(stripped)
                maSetGS = reSetGS.match(stripped)
                if maSet:
                    if not maDeleted:
                        section = ini_settings.setdefault(bolt.LString(u']set['),{})
                    else:
                        section = deleted_settings.setdefault(LString(u']set['),{})
                    if lineNumbers:
                        section[LString(maSet.group(1))] = (maSet.group(2).strip(),i)
                    else:
                        section[LString(maSet.group(1))] = maSet.group(2).strip()
                elif maSetGS:
                    if not maDeleted:
                        section = ini_settings.setdefault(bolt.LString(u']setGS['),{})
                    else:
                        section = deleted_settings.setdefault(LString(u']setGS['),{})
                    if lineNumbers:
                        section[LString(maSetGS.group(1))] = (maSetGS.group(2).strip(),i)
                    else:
                        section[LString(maSetGS.group(1))] = maSetGS.group(2).strip()
        return ini_settings,deleted_settings

    def getTweakFileLines(self,tweakPath):
        """Get a line by line breakdown of the tweak file, in this format:
        [(fulltext,section,setting,value,status,ini_line_number)]
        where:
        fulltext = full line of text from the ini
        setting = the setting that is being edited
        value = the value the setting is being set to
        status:
            -10: doesn't exist in the ini
              0: does exist, but it's a heading or something else without a value
             10: does exist, but value isn't the same
             20: deos exist, and value is the same
        ini_line_number = line number in the ini that this tweak applies to"""
        lines = []
        if not tweakPath.exists() or tweakPath.isdir():
            return lines
        iniSettings,deletedSettings = self.getTweakFileSettings(self.path,True,True)
        reDeleted = self.reDeleted
        reComment = self.reComment
        reSet = self.reSet
        reSetGS = self.reSetGS
        setSection = LString(u']set[')
        setGSSection = LString(u']setGS[')
        section = u''
        with tweakPath.open('r') as iniFile:
            for line in iniFile:
                # Check for deleted lines
                maDeleted = reDeleted.match(line)
                if maDeleted: stripped = maDeleted.group(1)
                else: stripped = line
                stripped = reComment.sub(u'',stripped).strip()
                # Check which kind it is - 'set' or 'setGS'
                for regex,section in [(reSet,setSection),
                                      (reSetGS,setGSSection)]:
                    match = regex.match(stripped)
                    if match:
                        groups = match.groups()
                        break
                else:
                    if stripped:
                        # Some other kind of line
                        lines.append((line.strip('\r\n'),u'',u'',u'',-10,-1,False))
                    else:
                        # Just a comment line
                        lines.append((line.strip('\r\n'),u'',u'',u'',0,-1,False))
                    continue
                status = 0
                setting = LString(groups[0].strip())
                value = LString(groups[1].strip())
                lineNo = -1
                if section in iniSettings and setting in iniSettings[section]:
                    item = iniSettings[section][setting]
                    lineNo = item[1]
                    if maDeleted:          status = 10
                    elif item[0] == value: status = 20
                    else:                  status = 10
                elif section in deletedSettings and setting in deletedSettings[section]:
                    item = deletedSettings[section][setting]
                    lineNo = item[1]
                    if maDeleted: status = 20
                    else:         status = 10
                else:
                    status = -10
                lines.append((line.strip(),section,setting,value,status,lineNo,bool(maDeleted)))
        return lines

    def saveSetting(self,section,key,value):
        lstr = LString(section)
        if lstr == u'set': section = u']set['
        elif lstr == u'setGS': section = u']setGS['
        IniFile.saveSetting(self,section,key,value)

    def saveSettings(self,ini_settings,deleted_settings={}):
        if not self.path.exists() or not self.path.isfile():
            return
        ini_settings = dict((LString(x),dict((LString(u),v) for u,v in y.iteritems()))
            for x,y in ini_settings.iteritems())
        deleted_settings = dict((LString(x),dict((LString(u),v) for u,v in y.iteritems()))
            for x,y in deleted_settings.iteritems())
        reDeleted = self.reDeleted
        reComment = self.reComment
        reSet = self.reSet
        reSetGS = self.reSetGS
        setSection = LString(u']set[')
        setGSSection = LString(u']setGS[')
        setFormat = u'set %s to %s\n'
        setGSFormat = u'setGS %s %s\n'
        section = {}
        with self.path.open('r') as iniFile:
            with self.path.temp.open('w') as tmpFile:
                # Modify/Delete existing lines
                for line in iniFile:
                    # Test if line is currently delted
                    maDeleted = reDeleted.match(line)
                    if maDeleted: stripped = maDeleted.group(1)
                    else: stripped = line
                    # Test what kind of line it is - 'set' or 'setGS'
                    stripped = reComment.sub(u'',line).strip()
                    for regex,sectionKey,format in [(reSet,setSection,setFormat),
                                                    (reSetGS,setGSSection,setGSFormat)]:
                        match = regex.match(stripped)
                        if match:
                            section = sectionKey
                            setting = LString(match.group(1))
                            break
                    else:
                        tmpFile.write(line)
                        continue
                    # Apply the modification
                    if section in ini_settings and setting in ini_settings[section]:
                        # Un-delete/modify it
                        value = ini_settings[section][setting]
                        del ini_settings[section][setting]
                        if isinstance(value,basestring) and value[-1:] == u'\n':
                            line = value
                        else:
                            line = format % (setting,value)
                    elif not maDeleted and section in deleted_settings and setting in deleted_settings[section]:
                        # It isn't deleted, but we want it deleted
                        line = u';-'+line
                    tmpFile.write(line)
                # Add new lines
                for sectionKey in ini_settings:
                    section = ini_settings[sectionKey]
                    for setting in section:
                        tmpFile.write(section[setting])
        self.path.untemp()

    def applyTweakFile(self,tweakPath):
        if not self.path.exists() or not self.path.isfile():
            return
        if not tweakPath.exists() or not tweakPath.isfile():
            return
        reDeleted = self.reDeleted
        reComent = self.reComment
        reSet = self.reSet
        reSetGS = self.reSetGS
        ini_settings = {}
        deleted_settings = {}
        setSection = LString(u']set[')
        setGSSection = LString(u']setGS[')
        with tweakPath.open('r') as tweakFile:
            for line in tweakFile:
                # Check for deleted lines
                maDeleted = reDeleted.match(line)
                if maDeleted:
                    stripped = maDeleted.group(1)
                    settings = deleted_settings
                else:
                    stripped = line
                    settings = ini_settings
                # Check which kind of line - 'set' or 'setGS'
                stripped = reComment.sub(u'',stripped).strip()
                for regex,sectionKey in [(reSet,setSection),
                                         (reSetGS,setGSSection)]:
                    match = regex.match(stripped)
                    if match:
                        setting = LString(match.group(1))
                        break
                else:
                    continue
                # Save the setting for applying
                section = settings.setdefault(sectionKey,{})
                if line[-1] != u'\n': line += u'\r\n'
                section[setting] = line
        self.saveSettings(ini_settings,deleted_settings)

#------------------------------------------------------------------------------
class OblivionIni(IniFile):
    """Oblivion.ini file."""
    bsaRedirectors = {u'archiveinvalidationinvalidated!.bsa',
                      u'..\\obmm\\bsaredirection.bsa'}
    encoding = 'cp1252'

    def __init__(self,name):
        # Use local copy of the oblivion.ini if present
        if dirs['app'].join(name).exists():
            IniFile.__init__(self,dirs['app'].join(name),u'General')
            # is bUseMyGamesDirectory set to 0?
            if self.getSetting(u'General',u'bUseMyGamesDirectory',u'1') == u'0':
                return
        # oblivion.ini was not found in the game directory or bUseMyGamesDirectory was not set."""
        # default to user profile directory"""
        IniFile.__init__(self,dirs['saveBase'].join(name),u'General')

    def ensureExists(self):
        """Ensures that Oblivion.ini file exists. Copies from default
        oblivion.ini if necessary."""
        if self.path.exists(): return
        srcPath = dirs['app'].join(bush.game.defaultIniFile)
        if srcPath.exists():
            srcPath.copyTo(self.path)

    def saveSettings(self,settings,deleted_settings={}):
        """Applies dictionary of settings to ini file.
        Values in settings dictionary can be either actual values or
        full key=value line ending in newline char."""
        self.ensureExists()
        IniFile.saveSettings(self,settings,deleted_settings)

    def applyTweakFile(self,tweakPath):
        """Read Ini tweak file and apply its settings to oblivion.ini.
        Note: Will ONLY apply settings that already exist."""
        self.ensureExists()
        IniFile.applyTweakFile(self,tweakPath)

    #--BSA Redirection --------------------------------------------------------
    def getBsaRedirection(self):
        """Returns True if BSA redirection is active."""
        section,key = bush.game.ini.bsaRedirection
        if not section or not key: return False
        self.ensureExists()
        sArchives = self.getSetting(section,key,u'')
        return bool([x for x in sArchives.split(u',') if x.strip().lower() in self.bsaRedirectors])

    def setBsaRedirection(self,doRedirect=True):
        """Activates or deactivates BSA redirection."""
        section,key = bush.game.ini.bsaRedirection
        if not section or not key: return
        aiBsa = dirs['mods'].join(u'ArchiveInvalidationInvalidated!.bsa')
        aiBsaMTime = time.mktime((2006, 1, 2, 0, 0, 0, 0, 2, 0))
        if aiBsa.exists() and aiBsa.mtime > aiBsaMTime:
            aiBsa.mtime = aiBsaMTime
        if doRedirect == self.getBsaRedirection():
            return
        if doRedirect and not aiBsa.exists():
            source = dirs['templates'].join(bush.game.fsName,u'ArchiveInvalidationInvalidated!.bsa')
            source.mtime = aiBsaMTime
            try:
                balt.shellCopy(source,aiBsa,askOverwrite=False)
            except (balt.AccessDeniedError,bolt.CancelError,bolt.SkipError):
                return
        sArchives = self.getSetting(section,key,u'')
        #--Strip existint redirectors out
        archives = [x.strip() for x in sArchives.split(u',') if x.strip().lower() not in self.bsaRedirectors]
        #--Add redirector back in?
        if doRedirect:
            archives.insert(0,u'ArchiveInvalidationInvalidated!.bsa')
        sArchives = u', '.join(archives)
        self.saveSetting(u'Archive',u'sArchiveList',sArchives)

#------------------------------------------------------------------------------
class OmodFile:
    """Class for extracting data from OMODs."""
    def __init__(self, path):
        self.path = path

    def readConfig(self,path):
        """Read info about the omod from the 'config' file"""
        with bolt.BinaryFile(path.s) as file:
            self.version = file.readByte() # OMOD version
            self.modName = _unicode(file.readNetString()) # Mod name
            self.major = file.readInt32() # Mod major version - getting weird numbers here though
            self.minor = file.readInt32() # Mod minor version
            self.author = _unicode(file.readNetString()) # author
            self.email = _unicode(file.readNetString()) # email
            self.website = _unicode(file.readNetString()) # website
            self.desc = _unicode(file.readNetString()) # description
            if self.version >= 2:
                self.ftime = file.readInt64() # creation time
            else:
                self.ftime = _unicode(file.readNetString())
            self.compType = file.readByte() # Compression type. 0 = lzma, 1 = zip
            if self.version >= 1:
                self.build = file.readInt32()
            else:
                self.build = -1

    def writeInfo(self, path, filename, readme, script):
        with path.open('w') as file:
            file.write(_encode(filename))
            file.write('\n\n[basic info]\n')
            file.write('Name: ')
            file.write(_encode(filename[:-5]))
            file.write('\nAuthor: ')
            file.write(_encode(self.author))
            file.write('\nVersion:') # TODO, fix this?
            file.write('\nContact: ')
            file.write(_encode(self.email))
            file.write('\nWebsite: ')
            file.write(_encode(self.website))
            file.write('\n\n')
            file.write(_encode(self.desc))
            file.write('\n\n')
            #fTime = time.gmtime(self.ftime) #-error
            #file.write('Date this omod was compiled: %s-%s-%s %s:%s:%s\n' % (fTime.tm_mon, fTime.tm_mday, fTime.tm_year, fTime.tm_hour, fTime.tm_min, fTime.tm_sec))
            file.write('Contains readme: %s\n' % ('yes' if readme else 'no'))
            file.write('Contains script: %s\n' % ('yes' if readme else 'no'))
            # Skip the reset that OBMM puts in

    def getOmodContents(self):
        """Return a list of the files and their uncompressed sizes, and the total uncompressed size of an archive"""
        # Get contents of archive
        filesizes = dict()
        totalSize = 0
        reFileSize = re.compile(ur'[0-9]{4}\-[0-9]{2}\-[0-9]{2}\s+[0-9]{2}\:[0-9]{2}\:[0-9]{2}.{6}\s+([0-9]+)\s+[0-9]+\s+(.+?)$',re.U)
        reFinalLine = re.compile(ur'\s+([0-9]+)\s+[0-9]+\s+[0-9]+\s+files.*',re.U)

        with self.path.unicodeSafe() as tempOmod:
            cmd7z = [exe7z, u'l', u'-r', u'-sccUTF-8', tempOmod.s]
            with subprocess.Popen(cmd7z, stdout=PIPE, stdin=PIPE, startupinfo=startupinfo).stdout as ins:
                for line in ins:
                    line = unicode(line,'utf8')
                    maFinalLine = reFinalLine.match(line)
                    if maFinalLine:
                        totalSize = int(maFinalLine.group(1))
                        break
                    maFileSize = reFileSize.match(line)
                    if maFileSize:
                        size = int(maFileSize.group(1))
                        name = maFileSize.group(2).strip().strip(u'\r')
                        filesizes[name] = size
        return filesizes,totalSize

    def extractToProject(self,outDir,progress=None):
        """Extract the contents of the omod to a project, with omod conversion data"""
        progress = progress if progress else bolt.Progress()
        extractDir = Path.tempDir(u'WryeBash_')
        stageBaseDir = Path.tempDir(u'WryeBash_')
        stageDir = stageBaseDir.join(outDir.tail)

        try:
            # Get contents of archive
            sizes,total = self.getOmodContents()

            # Extract the files
            reExtracting = re.compile(ur'Extracting\s+(.+)',re.U)
            reError = re.compile(ur'Error:',re.U)
            progress(0, self.path.stail+u'\n'+_(u'Extracting...'))

            subprogress = bolt.SubProgress(progress, 0, 0.4)
            current = 0
            with self.path.unicodeSafe() as tempOmod:
                cmd7z = [exe7z,u'e',u'-r',u'-sccUTF-8',tempOmod.s,u'-o%s' % extractDir.s]
                with subprocess.Popen(cmd7z, stdout=PIPE, stdin=PIPE, startupinfo=startupinfo).stdout as ins:
                    for line in ins:
                        line = unicode(line,'utf8')
                        maExtracting = reExtracting.match(line)
                        if maExtracting:
                            name = maExtracting.group(1).strip().strip(u'\r')
                            size = sizes[name]
                            subprogress(float(current)/total,self.path.stail+u'\n'+_(u'Extracting...')+u'\n'+name)
                            current += size

            # Get compression type
            progress(0.4,self.path.stail+u'\n'+_(u'Reading config'))
            self.readConfig(extractDir.join(u'config'))

            # Collect OMOD conversion data
            ocdDir = stageDir.join(u'omod conversion data')
            progress(0.46, self.path.stail+u'\n'+_(u'Creating omod conversion data')+u'\ninfo.txt')
            self.writeInfo(ocdDir.join(u'info.txt'), self.path.stail, extractDir.join(u'readme').exists(), extractDir.join(u'script').exists())
            progress(0.47, self.path.stail+u'\n'+_(u'Creating omod conversion data')+u'\nscript')
            if extractDir.join(u'script').exists():
                with bolt.BinaryFile(extractDir.join(u'script').s) as input:
                    with ocdDir.join(u'script.txt').open('w') as output:
                        output.write(input.readNetString())
            progress(0.48, self.path.stail+u'\n'+_(u'Creating omod conversion data')+u'\nreadme.rtf')
            if extractDir.join(u'readme').exists():
                with bolt.BinaryFile(extractDir.join(u'readme').s) as input:
                    with ocdDir.join(u'readme.rtf').open('w') as output:
                        output.write(input.readNetString())
            progress(0.49, self.path.stail+u'\n'+_(u'Creating omod conversion data')+u'\nscreenshot')
            if extractDir.join(u'image').exists():
                extractDir.join(u'image').moveTo(ocdDir.join(u'screenshot'))
            progress(0.5,self.path.stail+u'\n'+_(u'Creating omod conversion data')+u'\nconfig')
            extractDir.join(u'config').moveTo(ocdDir.join(u'config'))

            # Extract the files
            if self.compType == 0:
                extract = self.extractFiles7z
            else:
                extract = self.extractFilesZip

            pluginSize = sizes.get('plugins',0)
            dataSize = sizes.get('data',0)
            subprogress = bolt.SubProgress(progress, 0.5, 1)
            with stageDir.unicodeSafe() as tempOut:
                if extractDir.join(u'plugins.crc').exists() and extractDir.join(u'plugins').exists():
                    pluginProgress = bolt.SubProgress(subprogress, 0, float(pluginSize)/(pluginSize+dataSize))
                    extract(extractDir.join(u'plugins.crc'),extractDir.join(u'plugins'),tempOut,pluginProgress)
                if extractDir.join(u'data.crc').exists() and extractDir.join(u'data').exists():
                    dataProgress = bolt.SubProgress(subprogress, subprogress.state, 1)
                    extract(extractDir.join(u'data.crc'),extractDir.join(u'data'),tempOut,dataProgress)
                progress(1,self.path.stail+u'\n'+_(u'Extracted'))

            # Move files to final directory
            balt.shellMove(stageDir,outDir.head)
        except Exception as e:
            # Error occurred, see if final output dir needs deleting
            if outDir.exists():
                try:
                    balt.shellDelete(outDir,progress.getParent(),False,False)
                except:
                    pass
            raise
        finally:
            # Clean up temp directories
            extractDir.rmtree(safety=extractDir.stail)
            stageBaseDir.rmtree(safety=stageBaseDir.stail)

    def extractFilesZip(self, crcPath, dataPath, outPath, progress):
        fileNames, crcs, sizes = self.getFile_CrcSizes(crcPath)
        if len(fileNames) == 0: return

        # Extracted data stream is saved as a file named 'a'
        progress(0,self.path.tail+u'\n'+_(u'Unpacking %s') % dataPath.stail)
        cmd = [exe7z,u'e',u'-r',u'-sccUTF-8',dataPath.s,u'-o%s' % outPath.s]
        subprocess.call(cmd, startupinfo=startupinfo)

        # Split the uncompress stream into files
        progress(0.7,self.path.stail+u'\n'+_(u'Unpacking %s') % dataPath.stail)
        self.splitStream(outPath.join(u'a'), outPath, fileNames, sizes,
                         bolt.SubProgress(progress,0.7,1.0,len(fileNames))
                         )
        progress(1)

        # Clean up
        outPath.join(u'a').remove()

    def splitStream(self, streamPath, outDir, fileNames, sizes, progress):
        # Split the uncompressed stream into files
        progress(0, self.path.stail+u'\n'+_(u'Unpacking %s') % streamPath.stail)
        with streamPath.open('rb') as file:
            for i,name in enumerate(fileNames):
                progress(i,self.path.stail+u'\n'+_(u'Unpacking %s')%streamPath.stail+u'\n'+name)
                outFile = outDir.join(name)
                with outFile.open('wb') as output:
                    output.write(file.read(sizes[i]))
        progress(len(fileNames))

    def extractFiles7z(self, crcPath, dataPath, outPath, progress):
        fileNames, crcs, sizes = self.getFile_CrcSizes(crcPath)
        if len(fileNames) == 0: return
        totalSize = sum(sizes)

        # Extract data stream to an uncompressed stream
        subprogress = bolt.SubProgress(progress,0,0.3,full=dataPath.size)
        subprogress(0,self.path.stail+u'\n'+_(u'Unpacking %s') % dataPath.stail)
        with dataPath.open('rb') as file:
            done = 0
            with bolt.BinaryFile(outPath.join(dataPath.sbody+u'.tmp').s,'wb') as output:
                # Decoder properties
                output.write(file.read(5))
                done += 5
                subprogress(5)

                # Next 8 bytes are the size of the data stream
                for i in range(8):
                    out = totalSize >> (i*8)
                    output.writeByte(out & 0xFF)
                    done += 1
                    subprogress(done)

                # Now copy the data stream
                while file.tell() < dataPath.size:
                    output.write(file.read(512))
                    done += 512
                    subprogress(done)

        # Now decompress
        progress(0.3)
        cmd = [dirs['compiled'].join(u'lzma').s,u'd',outPath.join(dataPath.sbody+u'.tmp').s, outPath.join(dataPath.sbody+u'.uncomp').s]
        subprocess.call(cmd,startupinfo=startupinfo)
        progress(0.8)

        # Split the uncompressed stream into files
        self.splitStream(outPath.join(dataPath.sbody+u'.uncomp'), outPath, fileNames, sizes,
                         bolt.SubProgress(progress,0.8,1.0,full=len(fileNames))
                         )
        progress(1)

        # Clean up temp files
        outPath.join(dataPath.sbody+u'.uncomp').remove()
        outPath.join(dataPath.sbody+u'.tmp').remove()

    def getFile_CrcSizes(self, path):
        fileNames = list()
        crcs = list()
        sizes = list()

        with bolt.BinaryFile(path.s) as file:
            while file.tell() < path.size:
                fileNames.append(file.readNetString())
                crcs.append(file.readInt32())
                sizes.append(file.readInt64())
        return fileNames,crcs,sizes

#------------------------------------------------------------------------------
class PluginsFullError(BoltError):
    """Usage Error: Attempt to add a mod to plugins when plugins is full."""
    def __init__(self,message=_(u'Load list is full.')):
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class Plugins:
    """Plugins.txt and loadorder.txt file. Owned by modInfos.  Almost nothing
       else should access it directly.  Since migrating to libloadorder, this
       class now only really is used to detect if a refresh from libloadorder
       is required."""
    def __init__(self):
        if dirs['saveBase'] == dirs['app']: #--If using the game directory as rather than the appdata dir.
            self.dir = dirs['app']
        else:
            self.dir = dirs['userApp']
        self.pathPlugins = self.dir.join(u'plugins.txt')
        self.pathOrder = self.dir.join(u'loadorder.txt')
        self.mtimePlugins = 0
        self.sizePlugins = 0
        self.mtimeOrder = 0
        self.sizeOrder = 0
        self.LoadOrder = [] # the masterlist load order (always sorted)
        self.selected = []  # list of the currently active plugins (not always in order)
        #--Create dirs/files if necessary
        self.dir.makedirs()
        self.cleanLoadOrderFiles()

    def copyTo(self,toDir):
        """Save plugins.txt and loadorder.txt to a different directory (for backup)"""
        if self.pathPlugins.exists():
            self.pathPlugins.copyTo(toDir.join(u'plugins.txt'))
        if self.pathOrder.exists():
            self.pathOrder.copyTo(toDir.join(u'loadorder.txt'))

    def copyFrom(self,fromDir):
        """Move a different plugins.txt and loadorder.txt here for use."""
        move = fromDir.join(u'plugins.txt')
        if move.exists():
            move.copyTo(self.pathPlugins)
        move = fromDir.join(u'loadorder.txt')
        if move.exists():
            move.copyTo(self.pathOrder)

    def loadActive(self):
        """Get list of active plugins from plugins.txt through libloadorder which cleans out bad entries."""
        self.selected = lo.GetActivePlugins() # GPath list (but not sorted)
        if self.pathPlugins.exists():
            self.mtimePlugins = self.pathPlugins.mtime
            self.sizePlugins = self.pathPlugins.size
        else:
            self.mtimePlugins = 0
            self.sizePlugins = 0


    def loadLoadOrder(self):
        """Get list of all plugins from loadorder.txt through libloadorder."""
        self.LoadOrder = lo.GetLoadOrder()
        # game's master might be out of place (if using timestamps for load ordering) so move it up.
        if self.LoadOrder.index(modInfos.masterName) > 0:
            self.LoadOrder.remove(modInfos.masterName)
            self.LoadOrder.insert(0,modInfos.masterName)
        if lo.LoadOrderMethod == liblo.LIBLO_METHOD_TEXTFILE and self.pathOrder.exists():
            self.mtimeOrder = self.pathOrder.mtime
            self.sizeOrder = self.pathOrder.size
            if self.selected != modInfos.getOrdered(self.selected,False):
                modInfos.plugins.saveLoadOrder()
                self.selected = modInfos.getOrdered(self.selected,False)
                deprint("Mismatched Load Order Corrected")

    def save(self):
        """Write data to Plugins.txt file."""
        # liblo attempts to unghost files, no need to duplicate that here.
        lo.SetActivePlugins(modInfos.getOrdered(self.selected))
        self.mtimePlugins = self.pathPlugins.mtime
        self.sizePlugins = self.pathPlugins.size

    def saveLoadOrder(self):
        """Write data to loadorder.txt file (and update plugins.txt too)."""
        try:
            lo.SetLoadOrder(self.LoadOrder)
        except liblo.LibloError as e:
            if e.code == liblo.LIBLO_ERROR_INVALID_ARGS:
                raise bolt.BoltError(u'Cannot load plugins before masters.')
        # Now reset the mtimes cache or LockLO feature will revert intentional changes.
        for name in modInfos.mtimes:
            path = modInfos[name].getPath()
            if path.exists():
                modInfos.mtimes[name] = modInfos[name].getPath().mtime
        if lo.LoadOrderMethod == liblo.LIBLO_METHOD_TEXTFILE and self.pathOrder.exists():
            self.mtimeOrder = self.pathOrder.mtime
            self.sizeOrder = self.pathOrder.size


    def hasChanged(self):
        """True if plugins.txt or loadorder.txt file has changed."""
        if self.pathPlugins.exists() and (
            self.mtimePlugins != self.pathPlugins.mtime or
            self.sizePlugins != self.pathPlugins.size):
            return True
        if lo.LoadOrderMethod != liblo.LIBLO_METHOD_TEXTFILE:
            return True  # Until we find a better way, Oblivion always needs True
        return self.pathOrder.exists() and (
                self.mtimeOrder != self.pathOrder.mtime or
                self.sizeOrder != self.pathOrder.size)

    def removeMods(self, plugins, refresh=False):
        """Removes the specified mods from the load order."""
        # Use set to remove any duplicates
        plugins = set(plugins,)
        # Remove mods from cache
        self.LoadOrder = [x for x in self.LoadOrder if x not in plugins]
        self.selected  = [x for x in self.selected  if x not in plugins]
        # Refresh liblo
        if refresh:
            self.saveLoadOrder()
            self.save()

    def addMods(self, plugins, index=None, refresh=False):
        """Adds the specified mods to load order at the given index or at the bottom if none is given."""
        # Remove any duplicates
        plugins = set(plugins)
        # Add plugins
        for plugin in plugins:
            if plugin not in self.LoadOrder:
                if index is None:
                    self.LoadOrder.append(plugin)
                else:
                    self.LoadOrder.insert(index, plugin)
                    index += 1
        # Refresh liblo
        if refresh:
            self.saveLoadOrder()
            self.save()

    def refresh(self,forceRefresh=False):
        """Reload for plugins.txt or masterlist.txt changes."""
        hasChanged = self.hasChanged()
        if hasChanged or forceRefresh:
            self.loadActive()
            self.loadLoadOrder()
        return hasChanged

    def fixLoadOrder(self):
        """Fix inconsistencies between plugins.txt, loadorder.txt and actually installed mod files as well as impossible load orders"""
        loadOrder = set(self.LoadOrder)
        modFiles = set(modInfos.data.keys())
        removedFiles = loadOrder - modFiles
        addedFiles = modFiles - loadOrder
        # Remove non existent plugins from load order
        self.removeMods(removedFiles)
        # Add new plugins to load order
        indexFirstEsp = 0
        while indexFirstEsp < len(self.LoadOrder) and modInfos[self.LoadOrder[indexFirstEsp]].isEsm():
            indexFirstEsp += 1
        for mod in addedFiles:
            if modInfos.data[mod].isEsm():
                self.addMods([mod], indexFirstEsp)
                indexFirstEsp += 1
            else:
                self.addMods([mod])
        # Check to see if any esm files are loaded below an esp and reorder as neccessar
        for mod in self.LoadOrder[indexFirstEsp:]:
            if modInfos.data[mod].isEsm():
                self.LoadOrder.remove(mod)
                self.LoadOrder.insert(indexFirstEsp, mod)
                indexFirstEsp += 1
        # Save changes if necessary
        if removedFiles or addedFiles:
            self.saveLoadOrder()
            self.save()

    def cleanLoadOrderFiles(self):
        """Cleans all files relevant to the load ordering of non existant entries"""
        # This is primarily used to mask what is probably a bug in liblo that makes it fail if loadorder.txt contains a non existing .esm file entry.
        if lo.LoadOrderMethod == liblo.LIBLO_METHOD_TEXTFILE:
            loFiles = [x.s for x in (self.pathPlugins, self.pathOrder) if x.exists()]
            for loFile in loFiles:
                f = open(loFile, 'r')
                lines = f.readlines()
                f.close()
                f = open(loFile, 'w')
                for line in lines:
                    if dirs['mods'].join(line.strip()).exists():
                        f.write(line)
                f.close()

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
            self.author = u''
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
            self.author = u''
            self.masterNames = tuple()

    def hasChanged(self):
        return self.name != self.oldName

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
        self.isGhost = (name.cs[-6:] == u'.ghost')
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
        if self.isGhost: path += u'.ghost'
        return path

    def getFileInfos(self):
        """Returns modInfos or saveInfos depending on fileInfo type."""
        raise AbstractError

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
        return (self.isMod() and self.header and
                self.name.cext != (u'.esp',u'.esm')[int(self.header.flags1) & 1])

    def isEss(self):
        return self.name.cext == u'.ess'

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

    def _doBackup(self,backupDir,forceBackup=False):
        """Creates backup(s) of file, places in backupDir."""
        #--Skip backup?
        if not self in self.getFileInfos().data.values(): return
        if self.madeBackup and not forceBackup: return
        #--Backup Directory
        backupDir.makedirs()
        #--File Path
        original = self.getPath()
        #--Backup
        backup = backupDir.join(self.name)
        original.copyTo(backup)
        self.coCopy(original,backup)
        #--First backup
        firstBackup = backup+u'f'
        if not firstBackup.exists():
            original.copyTo(firstBackup)
            self.coCopy(original,firstBackup)

    def tempBackup(self, forceBackup=True):
        """Creates backup(s) of file.  Uses temporary directory to avoid UAC issues."""
        self._doBackup(Path.baseTempDir().join(u'WryeBash_temp_backup'),forceBackup)

    def makeBackup(self, forceBackup=False):
        """Creates backup(s) of file."""
        backupDir = self.bashDir.join(u'Backups')
        self._doBackup(backupDir,forceBackup)
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
            raise StateError(u"Can't get snapshot parameters for file outside main directory.")
        destDir = self.bashDir.join(u'Snapshots')
        destDir.makedirs()
        (root,ext) = self.name.rootExt
        destName = root+u'-00'+ext
        separator = u'-'
        snapLast = [u'00']
        #--Look for old snapshots.
        reSnap = re.compile(u'^'+root.s+u'[ -]([0-9\.]*[0-9]+)'+ext+u'$',re.U)
        for fileName in destDir.list():
            maSnap = reSnap.match(fileName.s)
            if not maSnap: continue
            snapNew = maSnap.group(1).split(u'.')
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
        snapLast[-1] = (u'%0'+unicode(len(snapLast[-1]))+u'd') % (int(snapLast[-1])+1,)
        destName = root+separator+(u'.'.join(snapLast))+ext
        return destDir,destName,(root+u'*'+ext).s

    def setGhost(self,isGhost):
        """Sets file to/from ghost mode. Returns ghost status at end."""
        normal = self.dir.join(self.name)
        ghost = normal+u'.ghost'
        # Refresh current status - it may have changed due to things like
        # libloadorder automatically unghosting plugins when activating them.
        # Libloadorder only un-ghosts automatically, so if both the normal
        # and ghosted version exist, treat the normal as the real one.
        if normal.exists():
            if self.isGhost:
                self.isGhost = False
                self.name = normal
        elif ghost.exists():
            if not self.isGhost:
                self.isGhost = True
                self.name = ghost
        # Current status == what we want it?
        if isGhost == self.isGhost:
            return isGhost
        # Current status != what we want, so change it
        try:
            if not normal.editable() or not ghost.editable(): return self.isGhost
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
        if type not in (u'esm',u'esp'):
            raise ArgumentError
        with self.getPath().open('r+b') as modFile:
            modFile.seek(8)
            flags1 = MreRecord._flags1(struct.unpack('I',modFile.read(4))[0])
            flags1.esm = (type == u'esm')
            modFile.seek(8)
            modFile.write(struct.pack('=I',int(flags1)))
        self.header.flags1 = flags1
        self.setmtime()

    def updateCrc(self):
        """Force update of stored crc"""
        path = self.getPath()
        size = path.size
        mtime = path.getmtime()
        crc = path.crc
        if crc != modInfos.table.getItem(self.name,'crc'):
            modInfos.table.setItem(self.name,'crc',crc)
            modInfos.table.setItem(self.name,'ignoreDirty',False)
        modInfos.table.setItem(self.name,'crc_mtime',mtime)
        modInfos.table.setItem(self.name,'crc_size',size)
        return crc

    def cachedCrc(self):
        """Stores a cached crc, for quicker execution."""
        path = self.getPath()
        size = path.size
        mtime = path.getmtime()
        if (mtime != modInfos.table.getItem(self.name,'crc_mtime') or
            size != modInfos.table.getItem(self.name,'crc_size')):
            crc = path.crc
            if crc != modInfos.table.getItem(self.name,'crc'):
                modInfos.table.setItem(self.name,'crc',crc)
                modInfos.table.setItem(self.name,'ignoreDirty',False)
            modInfos.table.setItem(self.name,'crc_mtime',mtime)
            modInfos.table.setItem(self.name,'crc_size',size)
        else:
            crc = modInfos.table.getItem(self.name,'crc')
        return crc

    def txt_status(self):
        if self.name in modInfos.ordered: return _(u'Active')
        elif self.name in modInfos.merged: return _(u'Merged')
        elif self.name in modInfos.imported: return _(u'Imported')
        else: return _(u'Non-Active')

    def hasTimeConflict(self):
        """True if has an mtime conflict with another mod."""
        return modInfos.hasTimeConflict(self.name)

    def hasActiveTimeConflict(self):
        """True if has an active mtime conflict with another mod."""
        return modInfos.hasActiveTimeConflict(self.name)

    def hasBadMasterNames(self):
        """True if has a master with un unencodable name in cp1252."""
        return modInfos.hasBadMasterNames(self.name)

    def isMissingStrings(self):
        return modInfos.isMissingStrings(self.name)

    def isExOverLoaded(self):
        """True if belongs to an exclusion group that is overloaded."""
        maExGroup = reExGroup.match(self.name.s)
        if not (modInfos.isSelected(self.name) and maExGroup):
            return False
        else:
            exGroup = maExGroup.group(1)
            return len(modInfos.exGroup_mods.get(exGroup,u'')) > 1

    def getBsaPath(self):
        """Returns path to plugin's BSA, if it were to exists."""
        return self.getPath().root.root+u'.bsa'

    def hasBsa(self):
        """Returns True if plugin has an associated BSA."""
        return self.getBsaPath().exists()

    def getStringsPaths(self,language=u'English'):
        """If Strings Files are available as loose files, just point to those, otherwise
           extract needed files from BSA if needed."""
        baseDirJoin = self.getPath().head.join
        files = []
        sbody,ext = self.name.sbody,self.name.ext
        language = oblivionIni.getSetting(u'General',u'sLanguage',u'English')
        for (dir,join,format) in bush.game.esp.stringsFiles:
            fname = format % {'body':sbody,
                              'ext':ext,
                              'language':language}
            assetPath = GPath(u'').join(*join).join(fname)
            files.append(assetPath)
        extract = set()
        paths = set()
        #--Check for Loose Files first
        for file in files:
            loose = baseDirJoin(file)
            if not loose.exists():
                extract.add(file)
            else:
                paths.add(loose)
        #--If there were some missing Loose Files
        if extract:
            bsaPaths = [self.getBsaPath()]
            for key in (u'sResourceArchiveList',u'sResourceArchiveList2'):
                extraBsa = oblivionIni.getSetting(u'Archive',key,u'').split(u',')
                extraBsa = [dirs['mods'].join(x.strip()) for x in extraBsa]
                extraBsa.reverse()
                bsaPaths.extend(extraBsa)
            bsaPaths = [x for x in bsaPaths if x.exists()]
            bsaFiles = {}
            targetJoin = dirs['bsaCache'].join
            for file in extract:
                found = False
                for path in bsaPaths:
                    bsaFile = bsaFiles.get(path,None)
                    if not bsaFile:
                        try:
                            bsaFile = libbsa.BSAHandle(path)
                            bsaFiles[path] = bsaFile
                        except:
                            deprint(u'   Error loading BSA file:',path.stail,traceback=True)
                            continue
                    if bsaFile.IsAssetInBSA(file):
                        target = targetJoin(path.tail)
                        #--Extract
                        try:
                            bsaFile.ExtractAsset(file,target)
                        except libbsa.LibbsaError as e:
                            raise ModError(self.name,u"Could not extract Strings File from '%s': %s" % (path.stail,e))
                        paths.add(target.join(file))
                        found = True
                if not found:
                    raise ModError(self.name,u"Could not locate Strings File '%s'" % file.stail)
        return paths

    def hasResources(self):
        """Returns (hasBsa,hasVoices) booleans according to presence of corresponding resources."""
        voicesPath = self.dir.join(u'Sound',u'Voice',self.name)
        return [self.hasBsa(),voicesPath.exists()]

    def setmtime(self,mtime=0):
        """Sets mtime. Defaults to current value (i.e. reset)."""
        mtime = int(mtime or self.mtime)
        FileInfo.setmtime(self,mtime)
        modInfos.mtimes[self.name] = mtime
        # Prevent re-calculating the File CRC
        modInfos.table.setItem(self.name,'crc_mtime',mtime)

    def writeNew(self,masters=[],mtime=0):
        """Creates a new file with the given name, masters and mtime."""
        header = bush.game.MreHeader((bush.game.MreHeader.classType,0,(self.isEsm() and 1 or 0),0,0))
        for master in masters:
            header.masters.append(master)
        header.setChanged()
        #--Write it
        with self.getPath().open('wb') as out:
            header.getSize()
            header.dump(out)
        self.setmtime(mtime)

    #--Bash Tags --------------------------------------------------------------
    def shiftBashTags(self):
        """Shifts bash keys from bottom to top."""
        description = self.header.description
        reReturns = re.compile(u'\r{2,}',re.U)
        reBashTags = re.compile(u'^(.+)({{BASH:[^}]*}})$',re.S|re.U)
        if reBashTags.match(description) or reReturns.search(description):
            description = reReturns.sub(u'\r',description)
            description = reBashTags.sub(ur'\2\n\1',description)
            self.writeDescription(description)

    def setBashTags(self,keys):
        """Sets bash keys as specified."""
        modInfos.table.setItem(self.name,'bashTags',keys)

    def setBashTagsDesc(self,keys):
        """Sets bash keys as specified."""
        keys = set(keys) #--Make sure it's a set.
        if keys == self.getBashTagsDesc(): return
        if keys:
            strKeys = u'{{BASH:'+(u','.join(sorted(keys)))+u'}}\n'
        else:
            strKeys = u''
        description = self.header.description or ''
        reBashTags = re.compile(ur'{{ *BASH *:[^}]*}}\s*\n?',re.U)
        if reBashTags.search(description):
            description = reBashTags.sub(strKeys,description)
        else:
            description = description + u'\n' + strKeys
        self.writeDescription(description)

    def getBashTags(self):
        """Returns any Bash flag keys."""
        tags = modInfos.table.getItem(self.name,'bashTags',set([]))
        return tags

    def getBashTagsDesc(self):
        """Returns any Bash flag keys."""
        description = self.header.description or u''
        maBashKeys = re.search(u'{{ *BASH *:([^}]+)}}',description,flags=re.U)
        if not maBashKeys:
            return None
        else:
            bashTags = maBashKeys.group(1).split(u',')
            return set([str.strip() for str in bashTags]) & allTagsSet - oldTagsSet

    def reloadBashTags(self):
        """Reloads bash tags from mod description and LOOT"""
        tags = (self.getBashTagsDesc() or set()) | (configHelpers.getBashTags(self.name) or set())
        tags -= (configHelpers.getBashRemoveTags(self.name) or set())
        # Filter and remove old tags
        tags = tags & allTagsSet
        if tags & oldTagsSet:
            tags -= oldTagsSet
            self.setBashTagsDesc(tags)
        self.setBashTags(tags)

    def getDirtyMessage(self):
        """Returns a dirty message from LOOT."""
        if modInfos.table.getItem(self.name,'ignoreDirty',False):
            return False,u''
        return configHelpers.getDirtyMessage(self.name)

    #--Header Editing ---------------------------------------------------------
    def getHeader(self):
        """Read header for file."""
        with ModReader(self.name,self.getPath().open('rb')) as ins:
            try:
                recHeader = ins.unpackRecHeader()
                if recHeader.recType != bush.game.MreHeader.classType:
                    raise ModError(self.name,u'Expected %s, but got %s'
                                   % (bush.game.MreHeader.classType,recHeader.recType))
                self.header = bush.game.MreHeader(recHeader,ins,True)
            except struct.error, rex:
                raise ModError(self.name,u'Struct.error: %s' % rex)
        #--Master Names/Order
        self.masterNames = tuple(self.header.masters)
        self.masterOrder = tuple() #--Reset to empty for now

    def writeHeader(self):
        """Write Header. Actually have to rewrite entire file."""
        filePath = self.getPath()
        with filePath.open('rb') as ins:
            with filePath.temp.open('wb') as out:
                try:
                    #--Open original and skip over header
                    reader = ModReader(self.name,ins)
                    recHeader = reader.unpackRecHeader()
                    if recHeader.recType != bush.game.MreHeader.classType:
                        raise ModError(self.name,u'Expected %s, but got %s'
                                       % (bush.game.MreHeader.classType,recHeader.recType))
                    reader.seek(recHeader.size,1)
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
                except struct.error, rex:
                    raise ModError(self.name,u'Struct.error: %s' % rex)
        #--Remove original and replace with temp
        filePath.untemp()
        self.setmtime()
        #--Merge info
        size,canMerge = modInfos.table.getItem(self.name,'mergeInfo',(None,None))
        if size is not None:
            modInfos.table.setItem(self.name,'mergeInfo',(filePath.size,canMerge))

    def writeDescription(self,description):
        """Sets description to specified text and then writes hedr."""
        description = description[:min(511,len(description))] # 511 + 1 for null = 512
        self.header.description = description
        self.header.setChanged()
        self.writeHeader()

    def writeAuthor(self,author):
        """Sets author to specified text and then writes hedr."""
        author = author[:min(511,len(author))] # 511 + 1 for null = 512
        self.header.author = author
        self.header.setChanged()
        self.writeHeader()

    def writeAuthorWB(self):
        """Marks author field with " [wb]" to indicate Wrye Bash modification."""
        author = self.header.author
        if u'[wm]' not in author and len(author) <= 27:
            self.writeAuthor(author+u' [wb]')

#------------------------------------------------------------------------------
class INIInfo(FileInfo):
    def __init__(self,*args,**kwdargs):
        FileInfo.__init__(self,*args,**kwdargs)
        self._status = None

    def _getStatus(self):
        if self._status is None: self.getStatus()
        return self._status
    status = property(_getStatus)

    def getFileInfos(self):
        return iniInfos

    def getHeader(self):
        pass

    def getStatus(self):
        """Returns status of the ini tweak:
        20: installed (green with check)
        15: mismatches (green with dot) - mismatches are with another tweak from same installer that is applied
        10: mismatches (yellow)
        0: not installed (green)
        -10: invalid tweak file (red).
        Also caches the value in self.status"""
        path = self.getPath()
        infos = self.getFileInfos()
        ini = infos.ini
        tweak,tweak_deleted = ini.getTweakFileSettings(path)
        if not tweak:
            self._status = -10
            return -10
        match = False
        mismatch = 0
        settings,deleted = ini.getSettings()
        for key in tweak:
            if key not in settings:
                self._status = -10
                return -10
            settingsKey = settings[key]
            tweakKey = tweak[key]
            for item in tweakKey:
                if item not in settingsKey:
                    self._status = -10
                    return -10
                if tweakKey[item] != settingsKey[item]:
                    if mismatch < 2:
                        # Check to see if the mismatch is from another
                        # ini tweak that is applied, and from the same installer
                        mismatch = 2
                        for info in infos.data:
                            if self is infos[info]: continue
                            this = infos.table.getItem(path.tail,'installer')
                            other = infos.table.getItem(info,'installer')
                            if this == other:
                                # It's from the same installer
                                other_settings,other_deletes = ini.getTweakFileSettings(infos[info].getPath())
                                value = other_settings.get(key,{}).get(item)
                                if value == settingsKey[item]:
                                    # The other tweak has the setting we're worried about
                                    mismatch = 1
                                    break
                else:
                    match = True
        if not match:
            self._status = 0
        elif not mismatch:
            self._status = 20
        elif mismatch == 1:
            self._status = 15
        elif mismatch == 2:
            self._status = 10
        return self._status

    def getLinesStatus(self):
        """Return a list of the lines and their statuses, in the form:
        [setting,value,status]
        for statuses:
        -10: highlight orange (not tweak not in ini)
          0: no highlight (header, in ini)
         10: highlight yellow (setting, in ini, but different)
         20: highlight green (setting, in ini, and same)"""
        ini = self.getFileInfos().ini
        tweak = self.getPath()
        ini_settings = ini.getSettings()
        tweak_settings,deleted_settings = ini.getTweakFileSettings(tweak)
        reComment = re.compile(u';.*',re.U)
        reSection = re.compile(ur'^\[\s*(.+?)\s*\]$',re.U)
        reSetting = re.compile(ur'(.+?)\s*=(.*)',re.U)
        section = LString(ini.defaultSection)

        lines = []

        with tweak.open('r') as tweakFile:
            for line in tweakFile:
                stripped = reComment.sub(u'',line).strip()
                maSection = reSection.match(stripped)
                maSetting = reSetting.match(stripped)
                if maSection:
                    section = LString(maSection.group(1))
                    if section in ini_settings:
                        lines.append((line.strip(u'\n\r'),u'',0))
                    else:
                        lines.append((line.strip(u'\n\r'),u'',-10))
                elif maSetting:
                    if section in ini_settings:
                        setting = LString(maSetting.group(1))
                        if setting in ini_settings[section]:
                            value = LString(maSetting.group(2).strip())
                            if value == ini_settings[section][setting]:
                                lines.append((maSetting.group(1),maSetting.group(2),20))
                            else:
                                lines.append((maSetting.group(1),maSetting.group(2),10))
                        else:
                            lines.append((maSetting.group(1),maSetting.group(2),-10))
                    else:
                        lines.append((maSetting.group(1),maSetting.group(2),-10))
                else:
                    lines.append((line.strip(u'\r\n'),u'',0))
        return lines

    def listErrors(self):
        """Returns ini tweak errors as text."""
        #--Setup
        path = self.getPath()
        ini = iniInfos.ini
        tweak,deletes = ini.getTweakFileSettings(path)
        settings,deleted_settings = ini.getSettings()
        text = [u'%s:' % path.stail]

        if len(tweak) == 0:
            tweak = BestIniFile(path)
            if isinstance(ini,(OblivionIni,IniFile)):
                # Target is a "true" INI format file
                if isinstance(tweak,(OblivionIni,IniFile)):
                    # Tweak is also a "true" INI format
                    text.append(_(u' No valid INI format lines.'))
                else:
                    text.append((u' '+_(u'Format mismatch:')
                                 + u'\n  ' +
                                 _(u'Target format: INI')
                                 + u'\n  ' +
                                 _(u'Tweak format: Batch Script')))
            else:
                if isinstance(tweak,OBSEIniFile):
                    text.append(_(u' No valid Batch Script format lines.'))
                else:
                    text.append((u' '+_(u'Format mismatch:')
                                 + u'\n  ' +
                                 _(u'Target format: Batch Script')
                                 + u'\n  ' +
                                 _(u'Tweak format: INI')))
        else:
            for key in tweak:
                if key not in settings:
                    text.append(u' [%s] - %s' % (key,_(u'Invalid Header')))
                else:
                    for item in tweak[key]:
                        if item not in settings[key]:
                            text.append(u' [%s] %s' % (key, item))
        if len(text) == 1:
            text.append(u' None')

        with sio() as out:
            log = bolt.LogFile(out)
            for line in text:
                log(line)
            return bolt.winNewLines(log.out.getvalue())

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
            raise SaveFileError(self.name,u'Struct.error: %s' % rex)

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
        return bsaInfos

    def getHeader(self):
        pass

    def resetMTime(self,mtime=u'01-01-2006 00:00:00'):
        mtime = time.mktime(time.strptime(mtime,u'%m-%d-%Y %H:%M:%S'))
        self.setmtime(mtime)

#------------------------------------------------------------------------------
class TrackedFileInfos(DataDict):
    """Similar to FileInfos, but doesn't use a PickleDict to save information
       about the tracked files at all."""
    def __init__(self,factory=FileInfo):
        self.factory = factory
        self.data = {}
        self.corrupted = {}

    def refreshFile(self,fileName):
        try:
            fileInfo = self.factory('',fileName)
            fileInfo.isGhost = not fileName.exists() and (fileName+u'.ghost').exists()
            fileInfo.getHeader()
            self.data[fileName] = fileInfo
        except FileError, error:
            self.corrupted[fileName] = error.message
            self.data.pop(fileName,None)
            raise

    def refresh(self):
        data = self.data
        changed = set()
        for name in data.keys():
            fileInfo = self.factory(u'',name)
            if not fileInfo.sameAs(data[name]):
                errorMsg = fileInfo.getHeaderError()
                if errorMsg:
                    self.corrupted[name] = errorMsg
                    data.pop(name,None)
                else:
                    data[name] = fileInfo
                    self.corrupted.pop(name,None)
                changed.add(name)
            filePath = fileInfo.getPath()
            if not filePath.exists():
                self.untrack(name)
        return changed

    def track(self,fileName):
        self.refreshFile(GPath(fileName))

    def untrack(self,fileName):
        self.data.pop(fileName,None)
        self.corrupted.pop(fileName,None)

    def clear(self):
        self.data = {}
        self.corrupted = {}

#------------------------------------------------------------------------------
class FileInfos(DataDict):
    def __init__(self,dir,factory=FileInfo, dirdef=None):
        """Init with specified directory and specified factory type."""
        self.dir = dir #--Path
        self.dirdef = dirdef
        self.factory=factory
        self.data = {}
        self.bashDir = self.getBashDir()
        self.table = bolt.Table(PickleDict(
            self.bashDir.join(u'Table.dat'),
            self.bashDir.join(u'Table.pkl')))
        self.corrupted = {} #--errorMessage = corrupted[fileName]
        #--Update table keys...
        tableData = self.table.data
        for key in self.table.data.keys():
            if not isinstance(key,bolt.Path):
                del tableData[key]

    def getBashDir(self):
        """Returns Bash data storage directory."""
        return self.dir.join(u'Bash')

    #--Refresh File
    def refreshFile(self,fileName):
        try:
            fileInfo = self.factory(self.dir,fileName)
            path = fileInfo.getPath()
            fileInfo.isGhost = not path.exists() and (path+u'.ghost').exists()
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
        if self.dirdef:
            # Default items
            names = {x for x in self.dirdef.list() if self.dirdef.join(x).isfile() and self.rightFileType(x)}
        else:
            names = set()
        if self.dir.exists():
            # Normal folder items
            names |= {x for x in self.dir.list() if self.dir.join(x).isfile() and self.rightFileType(x)}
        names = list(names)
        names.sort(key=lambda x: x.cext == u'.ghost')
        for name in names:
            if self.dirdef and not self.dir.join(name).isfile():
                fileInfo = self.factory(self.dirdef,name)
            else:
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
        for name in deleted:
            # Can run into multiple pops if one of the files is corrupted
            if name in data: data.pop(name)
        if deleted:
            # If an .esm file was deleted we need to clean the loadorder.txt file else liblo crashes
            modInfos.plugins.cleanLoadOrderFiles()
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
        if fileInfo.isGhost: newPath += u'.ghost'
        oldPath = fileInfo.getPath()
        balt.shellMove(oldPath,newPath,None,False,False,False)
        #--FileInfo
        fileInfo.name = newName
        #--FileInfos
        self[newName] = self[oldName]
        del self[oldName]
        self.table.moveRow(oldName,newName)
        #--Done
        fileInfo.madeBackup = False

    #--Delete
    def delete(self,fileName,doRefresh=True,askOk=False,dontRecycle=False):
        """Deletes member file."""
        if not isinstance(fileName,(list,set)):
            fileNames = [fileName]
        else:
            fileNames = fileName
        #--Files to delete
        toDelete = []
        toDeleteAppend = toDelete.append
        #--Cache table updates
        tableUpdate = {}
        #--Backups
        backBase = self.getBashDir().join(u'Backups')
        #--Go through each file
        for fileName in fileNames:
            fileInfo = self[fileName]
            #--File
            filePath = fileInfo.getPath()
            if filePath.body != fileName and filePath.tail != fileName.tail:
                # Prevent accidental deletion of Skyrim.esm/Oblivion.esm, but
                # Still works properly for ghosted files
                continue
            toDeleteAppend(filePath)
            #--Table
            tableUpdate[filePath] = fileName
            #--Misc. Editor backups (mods only)
            if fileInfo.isMod():
                for ext in (u'.bak',u'.tmp',u'.old',u'.ghost'):
                    backPath = filePath + ext
                    toDeleteAppend(backPath)
            #--Backups
            backRoot = backBase.join(fileInfo.name)
            for backPath in (backRoot,backRoot+u'f'):
                toDeleteAppend(backPath)
        #--Now do actual deletions
        toDelete = [x for x in toDelete if x.exists()]
        try:
            balt.shellDelete(toDelete,askOk=askOk,recycle=not dontRecycle)
        finally:
            #--Table
            for filePath in toDelete:
                if filePath in tableUpdate:
                    if not filePath.exists():
                        self.table.delRow(tableUpdate[filePath])
            #--Refresh
            if doRefresh:
                self.refresh()

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
class INIInfos(FileInfos):
    def __init__(self):
        FileInfos.__init__(self, dirs['tweaks'],INIInfo, dirs['defaultTweaks'])
        self.ini = oblivionIni

    def rightFileType(self,fileName):
        """Bool: File is an ini."""
        return reINIExt.search(fileName.s)

    def setBaseIni(self,ini):
        self.ini = ini

    def getBashDir(self):
        """Return directory to save info."""
        return dirs['modsBash'].join(u'INI Data')

#------------------------------------------------------------------------------
class ModInfos(FileInfos):
    """Collection of modinfos. Represents mods in the Oblivion\Data directory."""
    #--------------------------------------------------------------------------
    # Load Order stuff is almost all handled in the Plugins class again
    #--------------------------------------------------------------------------
    def swapOrder(self, leftName, rightName):
        """Swaps the Load Order of two mods"""
        order = self.plugins.LoadOrder
        # Dummy checks
        if leftName not in order or rightName not in order: return
        if self.masterName in {leftName,rightName}: return
        #--Swap
        leftIdex = order.index(leftName)
        rightIdex = order.index(rightName)
        order[leftIdex] = rightName
        order[rightIdex] = leftName
        #--Save
        self.plugins.saveLoadOrder()
        self.plugins.refresh(True)

    def __init__(self):
        FileInfos.__init__(self,dirs['mods'],ModInfo)
        #--MTime resetting
        self.lockLO = settings['bosh.modInfos.resetMTimes'] # Lock Load Order (previously Lock Times
        self.mtimes = self.table.getColumn('mtime')
        self.mtimesReset = [] #--Files whose mtimes have been reset.
        self.autoGrouped = {} #--Files that have been autogrouped.
        self.mergeScanned = [] #--Files that have been scanned for mergeability.
        #--Selection state (ordered, merged, imported)
        self.plugins = Plugins()
        self.ordered = tuple() # active mods in load order
        self.bashed_patches = set()
        #--Info lists/sets
        for fname in bush.game.masterFiles:
            if dirs['mods'].join(fname).exists():
                self.masterName = GPath(fname)
                break
        else:
            if len(bush.game.masterFiles) == 1:
                deprint(_(u'Missing master file; %s does not exist in an unghosted state in %s') % (fname, dirs['mods'].s))
            else:
                msg = bush.game.masterFiles[0]
                if len(bush.game.masterFiles) > 2:
                    msg += u', '.join(bush.game.masterFiles[1:-1])
                msg += u' or ' + bush.game.masterFiles[-1]
                deprint(_(u'Missing master file; Neither %s exists in an unghosted state in %s.  Presuming that %s is the correct masterfile.') % (msg, dirs['mods'].s, bush.game.masterFiles[0]))
            self.masterName = GPath(bush.game.masterFiles[0])
        self.mtime_mods = {}
        self.mtime_selected = {}
        self.exGroup_mods = {}
        self.mergeable = set() #--Set of all mods which can be merged.
        self.bad_names = set() #--Set of all mods with names that can't be saved to plugins.txt
        self.missing_strings = set() #--Set of all mods with missing .STRINGS files
        self.new_missing_strings = set() #--Set of new mods with missing .STRINGS files
        self.activeBad = set() #--Set of all mods with bad names that are active
        self.merged = set() #--For bash merged files
        self.imported = set() #--For bash imported files
        self.autoSorted = set() #--Files that are auto-sorted
        self.autoHeaders = set() #--Full balo headers
        self.autoGroups = {} #--Auto groups as read from group files.
        self.group_header = {}
        #--Oblivion version
        self.version_voSize = {
            u'1.1':        247388848, #--Standard
            u'1.1b':       247388894, # Arthmoor has this size.
            u'GOTY non-SI':247388812, # GOTY version
            u'1.0.7.5':    108369128, # Nehrim
            u'1.5.0.8':    115531891, # Nehrim Update
            u'SI':         277504985} # Shivering Isles 1.2
        self.size_voVersion = bolt.invertDict(self.version_voSize)
        self.voCurrent = None
        self.voAvailable = set()

    def getBashDir(self):
        """Returns Bash data storage directory."""
        return dirs['modsBash']

    #--Refresh-----------------------------------------------------------------
    def canSetTimes(self):
        """Returns a boolean indicating if mtime setting is allowed."""
        self.lockLO = settings['bosh.modInfos.resetMTimes']
        self.fullBalo = settings.get('bash.balo.full',False)
        obmmWarn = settings.setdefault('bosh.modInfos.obmmWarn',0)
        if self.lockLO and obmmWarn == 0 and dirs['app'].join(u'obmm').exists():
            settings['bosh.modInfos.obmmWarn'] = 1
        if not self.lockLO: return False
        if settings['bosh.modInfos.obmmWarn'] == 1: return False
        if settings.dictFile.readOnly: return False
        if lo.LoadOrderMethod == liblo.LIBLO_METHOD_TEXTFILE:
            return False
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
        hasChanged += self.plugins.refresh(forceRefresh=hasChanged)
        # If files have changed we might need to add/remove mods from load order
        if hasChanged: self.plugins.fixLoadOrder()
        hasGhosted = self.autoGhost()
        hasSorted = self.autoSort()
        self.refreshInfoLists()
        self.reloadBashTags()
        hasNewBad = self.refreshBadNames()
        hasMissingStrings = self.refreshMissingStrings()
        self.getOblivionVersions()
        return bool(hasChanged) or hasSorted or hasGhosted or hasNewBad or hasMissingStrings

    def refreshBadNames(self):
        """Refreshes which filenames cannot be saved to plugins.txt
        It seems that Skyrim and Oblivion read plugins.txt as a cp1252
        encoded file, and any filename that doesn't decode to cp1252 will
        be skipped."""
        bad = self.bad_names = set()
        activeBad = self.activeBad = set()
        for fileName in self.data:
            if self.isBadFileName(fileName.s):
                if fileName in self.ordered:
                    ## For now, we'll leave them active, until
                    ## we finish testing what the game will support
                    #self.unselect(fileName)
                    activeBad.add(fileName)
                else:
                    bad.add(fileName)
        return bool(activeBad)

    def refreshMissingStrings(self):
        """Refreshes which mods are supposed to have strings files,
           but are missing them (=CTD)."""
        oldBad = self.missing_strings
        bad = set()
        for fileName in self.data:
            if self.data[fileName].isMissingStrings():
                bad.add(fileName)
        new = bad - oldBad
        self.missing_strings = bad
        self.new_missing_strings = new
        return bool(new)

    def refreshHeaders(self):
        """Updates group_header."""
        group_header = self.group_header
        group_header.clear()
        mod_group = self.table.getColumn('group')
        for mod in self.data:
            group = mod_group.get(mod,None)
            if group and mod.s[:2] == u'++':
                group_header[group] = mod

    def resetMTimes(self):
        """Remember/reset mtimes of member files."""
        if not self.canSetTimes(): return
        del self.mtimesReset[:]
        try:
            for fileName, fileInfo in sorted(self.data.iteritems(),key=lambda x: x[1].mtime):
                oldMTime = int(self.mtimes.get(fileName,fileInfo.mtime))
                self.mtimes[fileName] = oldMTime
                if fileInfo.mtime != oldMTime and oldMTime  > 0:
                    #deprint(fileInfo.name, oldMTime - fileInfo.mtime)
                    fileInfo.setmtime(oldMTime)
                    self.mtimesReset.append(fileName)
        except:
            self.mtimesReset = [u'FAILED',fileName]

    def updateAutoGroups(self):
        """Update autogroup definitions."""
        self.autoGroups.clear()
        modGroups = ModGroups()
        for base in (u'Bash_Groups.csv',u'My_Groups.csv'):
            if getPatchesPath(base).exists(): modGroups.readFromText(getPatchesPath(base))
        self.autoGroups.update(modGroups.mod_group)

    def autoGhost(self,force=False):
        """Automatically inactive files to ghost."""
        changed = []
        allowGhosting = self.table.getColumn('allowGhosting')
        toGhost = settings.get('bash.mods.autoGhost',False)
        if force or toGhost:
            active = self.plugins.selected
            for mod in self.data:
                modInfo = self.data[mod]
                modGhost = toGhost and mod not in active and allowGhosting.get(mod,True)
                oldGhost = modInfo.isGhost
                newGhost = modInfo.setGhost(modGhost)
                if newGhost != oldGhost:
                    changed.append(mod)
        return changed

    def autoGroup(self):
        """Automatically assigns groups for currently ungrouped mods."""
        autoGroup = settings.get('bash.balo.autoGroup',True)
        if not self.autoGroups: self.updateAutoGroups()
        mod_group = self.table.getColumn('group')
        bashGroups = set(settings['bash.mods.groups'])
        for fileName in self.data:
            if not mod_group.get(fileName):
                group = u'NONE' #--Default
                if autoGroup:
                    if fileName in self.data and self.data[fileName].header:
                        maGroup = reGroup.search(self.data[fileName].header.description)
                        if maGroup: group = maGroup.group(1)
                    if group == u'NONE' and fileName in self.autoGroups:
                        group = self.autoGroups[fileName]
                    if group not in bashGroups:
                        group = u'NONE'
                    if group != u'NONE':
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
                if group != u'NONE': autoSorted.add(mod)
        #--Sort them
        changed = 0
        group_header = self.group_header
        if not group_header: return changed
        for group,header in self.group_header.iteritems():
            mods = group_mods.get(group,[])
            if group != u'NONE':
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
        self.bashed_patches.clear()
        selfKeys = self.keys()
        for modName in selfKeys:
            modInfo = modInfos[modName]
            mtime = modInfo.mtime
            mtime_mods.setdefault(mtime,[]).append(modName)
            if modInfo.header.author == u"BASHED PATCH":
                self.bashed_patches.add(modName)
        #--Selected mtimes and Refresh overLoaded too..
        mtime_selected = self.mtime_selected
        mtime_selected.clear()
        self.exGroup_mods.clear()
        for modName in self.ordered:
            mtime = modInfos[modName].mtime
            mtime_selected.setdefault(mtime,[]).append(modName)
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
            if size == modInfo.size:
                if canMerge: self.mergeable.add(name)
            elif reEsmExt.search(name.s):
                name_mergeInfo[name] = (modInfo.size,False)
            else:
                newMods.append(name)
        return newMods

    def rescanMergeable(self,names,progress,doCBash=None):
        """Will rescan specified mods."""
        if doCBash is None:
            doCBash = bool(CBash)
        elif doCBash and not bool(CBash):
            doCBash = False
        mod_mergeInfo = self.table.getColumn('mergeInfo')
        progress.setFull(max(len(names),1))
        for i,fileName in enumerate(names):
            progress(i,fileName.s)
            if not doCBash and reOblivion.match(fileName.s): continue
            fileInfo = self[fileName]
            if not bush.game.esp.canBash:
                canMerge = False
            else:
                try:
                    if doCBash:
                        canMerge = CBash_PatchFile.modIsMergeable(fileInfo)
                    else:
                        canMerge = PatchFile.modIsMergeable(fileInfo)
                except Exception, e:
                    # deprint (_(u"Error scanning mod %s (%s)") % (fileName, e))
                    # canMerge = False #presume non-mergeable.
                    raise


                #can't be above because otherwise if the mergeability had already been set true this wouldn't unset it.
                if fileName == u"Oscuro's_Oblivion_Overhaul.esp":
                    canMerge = False
            if canMerge == True:
                self.mergeable.add(fileName)
                mod_mergeInfo[fileName] = (fileInfo.size,True)
            else:
                if canMerge == u'\n.    '+_(u"Has 'NoMerge' tag."):
                    mod_mergeInfo[fileName] = (fileInfo.size,True)
                    self.mergeable.add(fileName)
                else:
                    mod_mergeInfo[fileName] = (fileInfo.size,False)
                    self.mergeable.discard(fileName)

    def reloadBashTags(self):
        """Reloads bash tags for all mods set to receive automatic bash tags."""
#        print "Output of ModInfos.data"
        for path in self.data:
            mod = self[path]
            autoTag = self.table.getItem(mod.name,'autoBashTags')
            if autoTag is None and self.table.getItem(mod.name,'bashTags') is None:
                # A new mod, set autoBashTags to True (default)
                self.table.setItem(mod.name,'autoBashTags',True)
                autoTag = True
            elif autoTag is None:
                # An old mod that had manual bash tags added, disable autoBashTags
                self.table.setItem(mod.name,'autoBashTags',False)
            if autoTag:
                mod.reloadBashTags()


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
                if group == u'Last':
                    offGroup_mtime[offGroup] = dateToTime(lastTime + diffTime*offset)
                else:
                    offGroup_mtime[offGroup] = dateToTime(nextTime)
                    nextTime += diffTime
                bashGroups.append(offGroup)
        deleted = added = 0
        #--Remove invalid group headers
        for offGroup,mod in group_header.iteritems():
            if offGroup not in offGroup_mtime:
                del group_header[offGroup]
                self.delete(mod,False)
                del self.data[mod]
                deleted += 1
        #--Add required group headers
        mod_group = self.table.getColumn('group')
        for offGroup in offGroup_mtime:
            if offGroup not in group_header:
                newName = GPath(u'++%s%s.esp' % (offGroup.upper(),u'='*(25-len(offGroup))))
                if newName not in self.data:
                    newInfo = ModInfo(self.dir,newName)
                    newInfo.mtime = time.time()
                    newFile = ModFile(newInfo,LoadFactory(True))
                    newFile.tes4.masters = [modInfos.masterName]
                    newFile.tes4.author = u'======'
                    newFile.tes4.description = _(u'Balo group header.')
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
        none = (u'NONE',0,0)
        last = (u'Last',-1,1)
        #--Already defined?
        if 'bash.balo.groups' in settings:
            groupInfos = list(settings['bash.balo.groups'])
        #--Anchor groups defined?
        elif self.group_header:
            deprint(u'by self.group_header')
            group_bounds = {}
            group_mtime = {}
            for offGroup,header in self.group_header.iteritems():
                group,offset = splitModGroup(offGroup)
                bounds = group_bounds.setdefault(group,[0,0])
                if offset < bounds[0]: bounds[0] = offset
                if offset > bounds[1]: bounds[1] = offset
                group_mtime[group] = self[header].mtime
            group_bounds.pop(u'NONE',None)
            lastBounds = group_bounds.pop(u'Last',None)
            if lastBounds:
                last = (u'Last',lastBounds[0],lastBounds[1])
            groupInfos = [(g,x,y) for g,(x,y) in group_bounds.iteritems()]
            groupInfos.sort(key=lambda a: group_mtime[a[0]])
        #--Default
        else:
            groupInfos = []
            for entry in bush.baloGroups:
                if entry[0] == u'Last': continue
                elif len(entry) == 1: entry += (0,0)
                elif len(entry) == 2: entry += (0,)
                groupInfos.append((entry[0],entry[2],entry[1]))
            groupInfos.append((u'NONE',0,0))
            groupInfos.append((u'Last',-1,1))
        #--None, Last Groups
        if groupInfos[-1][0] == u'Last':
            last = groupInfos.pop()
        if groupInfos[-1][0] == u'NONE':
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
                mod_group[mod] = u'' #--Will be set by self.autoGroup()
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
                mod_group[mod] = u'' #--Will be set by self.autoGroup()
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
        modNames = list(modNames)
        try:
            #modNames.sort()          # CDC Why a default sort? We want them in load order!  Is try even needed?
            data = self.plugins.LoadOrder
            modNames.sort(key=lambda a: (a in data) and data.index(a)) #--Sort on masterlist load order
        except:
            deprint(u'Error sorting modnames:',modNames,traceback=True)
            raise
        if asTuple: return tuple(modNames)
        else: return modNames

    def getSemiActive(self,masters):
        """Returns (merged,imported) mods made semi-active by Bashed Patch."""
        merged,imported = set(),set()
        for modName,modInfo in [(modName,self[modName]) for modName in masters]:
            if modInfo.header.author != u'BASHED PATCH': continue
            patchConfigs = self.table.getItem(modName,'bash.patch.configs',None)
            if not patchConfigs: continue
            patcherstr = 'CBash_PatchMerger' if CBash_PatchFile.configIsCBash(patchConfigs) else 'PatchMerger'
            if patchConfigs.get(patcherstr,{}).get('isEnabled'):
                configChecks = patchConfigs[patcherstr]['configChecks']
                for modName in configChecks:
                    if configChecks[modName]:
                        merged.add(modName)
            imported.update(patchConfigs.get('ImportedMods',tuple()))
        return merged,imported

    def selectExact(self,modNames):
        """Selects exactly the specified set of mods."""
        #--Ensure plugins that cannot be deselected stay selected
        for path in map(GPath, bush.game.nonDeactivatableFiles):
            if path not in modNames:
                modNames.append(path)
        #--Deselect/select plugins
        missing,extra = [],[]
        self.plugins.selected = list(modNames)
        for modName in modNames:
            if modName not in self.plugins.LoadOrder:
                missing.append(modName)
                self.plugins.selected.remove(modName)
        #--Save
        self.plugins.save()
        self.refreshInfoLists()
        self.autoGhost()
        #--Done/Error Message
        if missing or extra:
            message = u''
            if missing:
                message += _(u'Some mods were unavailable and were skipped:')+u'\n* '
                message += u'\n* '.join(x.s for x in missing)
            if extra:
                if missing: message += u'\n'
                message += _(u'Mod list is full, so some mods were skipped:')+u'\n'
                extra = set(modNames) - set(self.plugins.LoadOrder)
                message += u'\n* '.join(x.s for x in extra)
            return message
        else:
            return None

    def getModList(self,showCRC=False,showVersion=True,fileInfo=None,wtxt=False):
        """Returns mod list as text. If fileInfo is provided will show mod list
        for its masters. Otherwise will show currently loaded mods."""
        #--Setup
        with sio() as out:
            log = bolt.LogFile(out)
            head,bul,sMissing,sDelinquent,sImported = (
                u'=== ',
                u'* ',
                _(u'  * __Missing Master:__ '),
                _(u'  * __Delinquent Master:__ '),
                u'&bull; &bull;'
                ) if wtxt else (
                u'',
                u'',
                _(u'----> MISSING MASTER: '),
                _(u'----> Delinquent MASTER: '),
                u'**')
            if fileInfo:
                masters = set(fileInfo.header.masters)
                missing = sorted([x for x in masters if x not in self])
                log.setHeader(head+_(u'Missing Masters for %s: ') % fileInfo.name.s)
                for mod in missing:
                    log(bul+u'xx '+mod.s)
                log.setHeader(head+_(u'Masters for %s: ') % fileInfo.name.s)
                present = set(x for x in masters if x in self)
                if fileInfo.name in self: #--In case is bashed patch
                    present.add(fileInfo.name)
                merged,imported = self.getSemiActive(present)
            else:
                log.setHeader(head+_(u'Active Mod Files:'))
                masters = set(self.ordered)
                merged,imported = self.merged,self.imported
            headers = set(mod for mod in self.data if mod.s[0] in u'.=+')
            allMods = masters | merged | imported | headers
            allMods = self.getOrdered([x for x in allMods if x in self])
            #--List
            modIndex,header = 0, None
            if not wtxt: log(u'[spoiler][xml]\n', False)
            for name in allMods:
                if name in masters:
                    prefix = bul+u'%02X' % modIndex
                    modIndex += 1
                elif name in headers:
                    match = re.match(u'^[\.+= ]*(.*?)\.es[pm]',name.s,flags=re.U)
                    if match: name = GPath(match.group(1))
                    header = bul+u'==  ' +name.s
                    continue
                elif name in merged:
                    prefix = bul+u'++'
                else:
                    prefix = bul+sImported
                if header:
                    log(header)
                    header = None
                text = u'%s  %s' % (prefix,name.s,)
                if showVersion:
                    version = self.getVersion(name)
                    if version: text += _(u'  [Version %s]') % version
                if showCRC:
                    text +=_(u'  [CRC: %08X]') % (self[name].cachedCrc())
                log(text)
                if name in masters:
                    for master2 in self[name].header.masters:
                        if master2 not in self:
                            log(sMissing+master2.s)
                        elif self.getOrdered((name,master2))[1] == master2:
                            log(sDelinquent+master2.s)
            if not wtxt: log(u'[/xml][/spoiler]')
            return bolt.winNewLines(log.out.getvalue())

    def getTagList(self,modList=None):
        """Returns the list as wtxt of current bash tags (but doesn't say what ones are applied via a patch).
        Either for all mods in the data folder or if specified for one specific mod.
        """
        tagList = u'=== '+_(u'Current Bash Tags')+u':\n'
        tagList += u'[spoiler][xml]\n'
        if modList:
            for modInfo in modList:
                tagList += u'\n* ' + modInfo.name.s + u'\n'
                if modInfo.getBashTags():
                    if not modInfos.table.getItem(modInfo.name,'autoBashTags') and modInfos.table.getItem(modInfo.name,'bashTags',u''):
                        tagList += u'  * '+_(u'From Manual (if any this overrides Description/LOOT sourced tags): ') + u', '.join(sorted(modInfos.table.getItem(modInfo.name,'bashTags',u''))) + u'\n'
                    if modInfo.getBashTagsDesc():
                        tagList += u'  * '+_(u'From Description: ') + u', '.join(sorted(modInfo.getBashTagsDesc())) + u'\n'
                    if configHelpers.getBashTags(modInfo.name):
                        tagList += u'  * '+_(u'From LOOT Masterlist and or userlist: ') + u', '.join(sorted(configHelpers.getBashTags(modInfo.name))) + u'\n'
                    if configHelpers.getBashRemoveTags(modInfo.name):
                        tagList += u'  * '+_(u'Removed by LOOT Masterlist and or userlist: ') + u', '.join(sorted(configHelpers.getBashRemoveTags(modInfo.name))) + u'\n'
                    tagList += u'  * '+_(u'Result: ') + u', '.join(sorted(modInfo.getBashTags())) + u'\n'
                else: tagList += u'    '+_(u'No tags')
        else:
            # sort output by load order
            for modInfo in sorted(modInfos.data.values(),cmp=lambda x,y: cmp(x.mtime, y.mtime)):
                if modInfo.getBashTags():
                    tagList += u'\n* ' + modInfo.name.s + u'\n'
                    if not modInfos.table.getItem(modInfo.name,'autoBashTags') and modInfos.table.getItem(modInfo.name,'bashTags',u''):
                        tagList += u'  * '+_(u'From Manual (if any this overrides Description/LOOT sourced tags): ') + u', '.join(sorted(modInfos.table.getItem(modInfo.name,'bashTags',u''))) + u'\n'
                    if modInfo.getBashTagsDesc():
                        tagList += u'  * '+_(u'From Description: ') + u', '.join(sorted(modInfo.getBashTagsDesc())) + u'\n'
                    if configHelpers.getBashTags(modInfo.name):
                        tagList += u'  * '+_(u'From LOOT Masterlist and or userlist: ') + u', '.join(sorted(configHelpers.getBashTags(modInfo.name))) + u'\n'
                    if configHelpers.getBashRemoveTags(modInfo.name):
                        tagList += u'  * '+_(u'Removed by LOOT Masterlist and or userlist: ') + u', '.join(sorted(configHelpers.getBashRemoveTags(modInfo.name))) + u'\n'
                    tagList += u'  * '+_(u'Result: ') + u', '.join(sorted(modInfo.getBashTags())) + u'\n'
        tagList += u'[/xml][/spoiler]'
        return tagList

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
        return modFile in self.ordered

    def select(self,fileName,doSave=True,modSet=None,children=None):
        """Adds file to selected."""
        try:
            plugins = self.plugins
            children = (children or tuple()) + (fileName,)
            if fileName in children[:-1]:
                raise BoltError(u'Circular Masters: '+u' >> '.join(x.s for x in children))
            #--Select masters
            if modSet is None: modSet = set(self.keys())
            #--Check for bad masternames:
            #  Disabled for now
            ##if self.hasBadMasterNames(fileName):
            ##    return
            for master in self[fileName].header.masters:
                if master in modSet:
                    self.select(master,False,modSet,children)
            #--Select in plugins
            if fileName not in plugins.selected:
                plugins.selected.append(fileName)
        finally:
            if doSave:
                plugins.save()

    def unselect(self,fileName,doSave=True):
        """Removes file from selected."""
        #--Unselect self
        if fileName in self.plugins.selected:
            self.plugins.selected.remove(fileName)
        #--Unselect children
        for selFile in self.plugins.selected[:]:
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
            self.plugins.save()

    def isBadFileName(self,modName):
        """True if the name cannot be encoded to the proper format for plugins.txt"""
        try:
            modName.encode('cp1252')
            return False
        except UnicodeEncodeError:
            return True

    def isMissingStrings(self,modName):
        """True if the mod says it has .STRINGS files, but the files are missing."""
        modInfo = self.data[modName]
        if modInfo.header.flags1.hasStrings:
            language = oblivionIni.getSetting(u'General',u'sLanguage',u'English')
            sbody,ext = modName.sbody,modName.ext
            bsaPaths = [modInfo.getBsaPath()]
            for key in (u'sResourceArchiveList',u'sResourceArchiveList2'):
                extraBsa = oblivionIni.getSetting(u'Archive',key,u'').split(u',')
                extraBsa = [dirs['mods'].join(x.strip()) for x in extraBsa]
                bsaPaths.extend(extraBsa)
            bsaPaths = [x for x in bsaPaths if x.exists()]
            bsaFiles = {}
            for stringsFile in bush.game.esp.stringsFiles:
                dir,join,format = stringsFile
                fname = format % {'body':sbody,
                                  'ext':ext,
                                  'language':language}
                assetPath = GPath(u'').join(*join).join(fname)
                # Check loose files first
                if dirs[dir].join(assetPath).exists():
                    continue
                # Check in BSA's next
                found = False
                for path in bsaPaths:
                    if not path.exists():
                        continue
                    bsaFile = bsaFiles.get(path,None)
                    if not bsaFile:
                        try:
                            bsaFile = libbsa.BSAHandle(path)
                            bsaFiles[path] = bsaFile
                        except:
                            continue
                    if bsaFile.IsAssetInBSA(assetPath):
                        found = True
                        break
                if not found:
                    return True
        return False

    def hasBadMasterNames(self,modName):
        """True if there mod has master's with unencodable names."""
        masters = self[modName].header.masters
        try:
            for x in masters: x.s.encode('cp1252')
            return False
        except UnicodeEncodeError:
            return True

    def hasTimeConflict(self,modName):
        """True if there is another mod with the same mtime."""
        if lo.LoadOrderMethod == liblo.LIBLO_METHOD_TEXTFILE:
            return False
        else:
            mtime = self[modName].mtime
            mods = self.mtime_mods.get(mtime,[])
            return len(mods) > 1

    def hasActiveTimeConflict(self,modName):
        """True if there is another mod with the same mtime."""
        if lo.LoadOrderMethod == liblo.LIBLO_METHOD_TEXTFILE:
            return False
        elif not self.isSelected(modName): return False
        else:
            mtime = self[modName].mtime
            mods = self.mtime_selected.get(mtime,tuple())
            return len(mods) > 1

    def getFreeTime(self, startTime, defaultTime='+1', reverse=False):
        """Tries to return a mtime that doesn't conflict with a mod. Returns defaultTime if it fails."""
        if lo.LoadOrderMethod == liblo.LIBLO_METHOD_TEXTFILE:
            # Doesn't matter - LO isn't determined by mtime
            return time.time()
        else:
            haskey = self.mtime_mods.has_key
            if reverse:
                endTime = startTime - 1000
                step = -1
            else:
                endTime = startTime + 1000
                step = 1
            for testTime in xrange(startTime, endTime, step): #1000 is an arbitrary limit
                if not haskey(testTime):
                    return testTime
            return defaultTime

    #--Mod move/delete/rename -------------------------------------------------
    def rename(self,oldName,newName):
        """Renames member file from oldName to newName."""
        isSelected = self.isSelected(oldName)
        if isSelected: self.unselect(oldName)
        FileInfos.rename(self,oldName,newName)
        oldIndex = self.plugins.LoadOrder.index(oldName)
        self.plugins.removeMods([oldName], refresh=False)
        self.plugins.addMods([newName], index=oldIndex)
        #self.plugins.LoadOrder.remove(oldName)
        #self.plugins.LoadOrder.insert(oldIndex, newName)
        self.plugins.saveLoadOrder()
        self.refreshInfoLists()
        if isSelected: self.select(newName)

    def delete(self,fileName,doRefresh=True):
        """Deletes member file."""
        if fileName.s not in bush.game.masterFiles:
            self.unselect(fileName)
            FileInfos.delete(self,fileName,doRefresh)
        else:
            raise bolt.BoltError("Cannot delete the game's master file(s).")

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
        return (maVersion and maVersion.group(2)) or u''

    def getVersionFloat(self,fileName):
        """Extracts and returns version number for fileName from header.hedr.description."""
        version = self.getVersion(fileName)
        maVersion = re.search(ur'(\d+\.?\d*)',version,flags=re.U)
        if maVersion:
            return float(maVersion.group(1))
        else:
            return 0

#    def getRequires(self,fileName):
#        """Extracts and returns requirement dictionary for fileName from header.hedr.description."""
#        print "****************************** THIS FUNCTION WAS CALLED"
#        requires = {}
#        if not fileName in self.data or not self.data[fileName].header:
#            maRequires = reRequires.search(self.data[fileName].header.description)
#            if maRequires:
#                for item in map(string.strip,maRequires.group(1).split(u',')):
#                    maReqItem = reReqItem.match(item)
#                    key,value = ma
#                    if maReqItem:
#                        key,value = maReqItem.groups()
#                        requires[key] = float(value or 0)
#        return requires

    #--Oblivion 1.1/SI Swapping -----------------------------------------------
    def getOblivionVersions(self):
        """Returns tuple of Oblivion versions."""
        self.voAvailable.clear()
        for name,info in self.data.iteritems():
            maOblivion = reOblivion.match(name.s)
            if maOblivion and info.size in self.size_voVersion:
                self.voAvailable.add(self.size_voVersion[info.size])
        if self.masterName in self.data:
            self.voCurrent = self.size_voVersion.get(self.data[self.masterName].size,None)

    def setOblivionVersion(self,newVersion):
        """Swaps Oblivion.esm to to specified version."""
        #--Old info
        baseName = self.masterName
        newSize = self.version_voSize[newVersion]
        oldSize = self.data[baseName].size
        if newSize == oldSize: return
        if oldSize not in self.size_voVersion:
            raise StateError(u"Can't match current main ESM to known version.")
        oldName = GPath(baseName.sbody+u'_'+self.size_voVersion[oldSize]+u'.esm')
        if self.dir.join(oldName).exists():
            raise StateError(u"Can't swap: %s already exists." % oldName)
        newName = GPath(baseName.sbody+u'_'+newVersion+u'.esm')
        if newName not in self.data:
            raise StateError(u"Can't swap: %s doesn't exist." % newName)
        #--Rename
        baseInfo = self.data[baseName]
        newInfo = self.data[newName]
        basePath = baseInfo.getPath()
        newPath = newInfo.getPath()
        oldPath = self.dir.join(oldName)
        try:
            basePath.moveTo(oldPath)
        except WindowsError, werr:
            if werr.winerror != 32: raise
            while balt.askYes(self,(_(u'Bash encountered an error when renaming %s to %s.')
                                    + u'\n\n' +
                                    _(u'The file is in use by another process such as TES4Edit.')
                                    + u'\n' +
                                    _(u'Please close the other program that is accessing %s.')
                                    + u'\n\n' +
                                    _(u'Try again?')) % (basePath.s,oldPath.s,basePath.s),
                              _(u'Bash Patch - Rename Error')):
                try:
                    basePath.moveTo(oldPath)
                except WindowsError, werr:
                    continue
                break
            else:
                raise
        try:
            newPath.moveTo(basePath)
        except WindowsError, werr:
            if werr.winerror != 32: raise
            while balt.askYes(self,(_(u'Bash encountered an error when renaming %s to %s.')
                                    + u'\n\n' +
                                    _(u'The file is in use by another process such as TES4Edit.')
                                    + u'\n' +
                                    _(u'Please close the other program that is accessing %s.')
                                    + u'\n\n' +
                                    _(u'Try again?')) % (basePath.s,oldPath.s,basePath.s),
                              _(u'Bash Patch - Rename Error')):
                try:
                    newPath.moveTo(basePath)
                except WindowsError, werr:
                    continue
                break
            else:
                #Undo any changes
                oldPath.moveTo(basePath)
                raise
        basePath.mtime = baseInfo.mtime
        oldPath.mtime = newInfo.mtime
        self.mtimes[oldName] = newInfo.mtime
        if newInfo.isGhost:
            oldInfo = ModInfo(self.dir,oldName)
            oldInfo.setGhost(True)
        self.voCurrent = newVersion

#------------------------------------------------------------------------------
class SaveInfos(FileInfos):
    """SaveInfo collection. Represents save directory and related info."""
    #--Init
    def __init__(self):
        self.iniMTime = 0
        self.refreshLocalSave()
        FileInfos.__init__(self,self.dir,SaveInfo)
        self.profiles = bolt.Table(PickleDict(
            dirs['saveBase'].join(u'BashProfiles.dat'),
            dirs['userApp'].join(u'Profiles.pkl')))
        self.table = bolt.Table(PickleDict(self.bashDir.join(u'Table.dat')))

    #--Right File Type (Used by Refresh)
    def rightFileType(self,fileName):
        """Bool: File is a mod."""
        return reSaveExt.search(fileName.s)

    def refresh(self):
        if self.refreshLocalSave():
            self.data.clear()
            self.table.save()
            self.table = bolt.Table(PickleDict(
                self.bashDir.join(u'Table.dat'),
                self.bashDir.join(u'Table.pkl')))
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
        baseSaves = dirs['saveBase'].join(u'Saves')
        if baseSaves.exists():
            localSaveDirs = [x for x in baseSaves.list() if (x != u'Bash' and baseSaves.join(x).isdir())]
            # Filter out non-encodable names
            bad = []
            for dir in localSaveDirs:
                try:
                    dir.s.encode('cp1252')
                except UnicodeEncodeError:
                    bad.append(dir)
            localSaveDirs = [x for x in localSaveDirs if x not in bad]
        else:
            localSaveDirs = []
        localSaveDirs.sort()
        return localSaveDirs

    def refreshLocalSave(self):
        """Refreshes self.localSave and self.dir."""
        #--self.localSave is NOT a Path object.
        self.localSave = getattr(self,u'localSave',u'Saves\\')
        self.dir = dirs['saveBase'].join(self.localSave)
        self.bashDir = self.getBashDir()
        if oblivionIni.path.exists() and (oblivionIni.path.mtime != self.iniMTime):
            self.localSave = oblivionIni.getSetting(bush.game.saveProfilesKey[0],
                                                    bush.game.saveProfilesKey[1],
                                                    u'Saves\\')
            # Hopefully will solve issues with unicode usernames
            self.localSave = _unicode(self.localSave)
            self.iniMTime = oblivionIni.path.mtime
            return True
        else:
            return False

    def setLocalSave(self,localSave):
        """Sets SLocalSavePath in Oblivion.ini."""
        self.table.save()
        self.localSave = localSave
        oblivionIni.saveSetting(bush.game.saveProfilesKey[0],
                                bush.game.saveProfilesKey[1],
                                localSave)
        self.iniMTime = oblivionIni.path.mtime
        bashDir = dirs['saveBase'].join(localSave,u'Bash')
        self.table = bolt.Table(PickleDict(bashDir.join(u'Table.dat')))
        self.refresh()

    #--Enabled ----------------------------------------------------------------
    def isEnabled(self,fileName):
        """True if fileName is enabled)."""
        return fileName.cext == u'.ess'

    def enable(self,fileName,value=True):
        """Enables file by changing extension to 'ess' (True) or 'esr' (False)."""
        isEnabled = self.isEnabled(fileName)
        if isEnabled or value == isEnabled or re.match(u'(autosave|quicksave)',fileName.s,re.I|re.U):
            return fileName
        (root,ext) = fileName.rootExt
        newName = root + ((value and u'.ess') or u'.esr')
        self.rename(fileName,newName)
        return newName

#------------------------------------------------------------------------------
class BSAInfos(FileInfos):
    """SaveInfo collection. Represents save directory and related info."""
    #--Init
    def __init__(self):
        self.dir = dirs['mods']
        FileInfos.__init__(self,self.dir,BSAInfo)

    #--Right File Type (Used by Refresh)
    def rightFileType(self,fileName):
        """Bool: File is a mod."""
        return reBSAExt.search(fileName.s)

    def getBashDir(self):
        """Return directory to save info."""
        return dirs['modsBash'].join(u'BSA Data')

    def resetMTimes(self):
        for file in self.data:
            self[file].resetMTime()

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
        ruleBlockIds = (u'NOTES',u'CONFIG',u'SUGGEST',u'WARN')
        reComment = re.compile(ur'##.*',re.U)
        reBlock   = re.compile(ur'^>>\s+([A-Z]+)\s*(.*)',re.U)
        reMod     = re.compile(ur'\s*([\-\|]?)(.+?\.es[pm])(\s*\[[^\]]\])?',re.I|re.U)
        reRule    = re.compile(ur'^(x|o|\+|-|-\+)\s+([^/]+)\s*(\[[^\]]+\])?\s*//(.*)',re.U)
        reExists  = re.compile(ur'^(e)\s+([^/]+)//(.*)',re.U)
        reModVersion = re.compile(ur'(.+\.es[pm])\s*(\[[^\]]+\])?',re.I|re.U)

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
            if curBlockId is not None:
                if curBlockId == u'HEADER':
                    self.ruleSet.header = self.ruleSet.header.rstrip()
                elif curBlockId == u'ONLYONE':
                    self.ruleSet.onlyones.append(set(self.mods))
                elif curBlockId == u'ASSUME':
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
            ruleSet.header = u''
            del ruleSet.onlyones[:]
            del ruleSet.modGroups[:]

            def stripped(list):
                return [(x or u'').strip() for x in list]

            with rulePath.open('r',encoding='utf-8-sig') as ins:
                for line in ins:
                    line = reComment.sub(u'',line)
                    maBlock = reBlock.match(line)
                    #--Block changers
                    if maBlock:
                        newBlock,extra = stripped(maBlock.groups())
                        self.newBlock(newBlock)
                        if newBlock == u'HEADER':
                            self.ruleSet.header = (extra or u'')+u'\n'
                        elif newBlock in (u'ASSUME',u'IF'):
                            maModVersion = reModVersion.match(extra or u'')
                            if extra and reModVersion.match(extra):
                                self.mods = [[GPath(reModVersion.match(extra).group(1))]]
                                self.modNots = [False]
                            else:
                                self.mods = []
                                self.modNots = []
                    #--Block lists
                    elif self.curBlockId == u'HEADER':
                        self.ruleSet.header += line.rstrip()+u'\n'
                    elif self.curBlockId in (u'IF',u'ASSUME'):
                        maMod = reMod.match(line)
                        if maMod:
                            op,mod,version = stripped(maMod.groups())
                            mod = GPath(mod)
                            if op == u'|':
                                self.mods[-1].append(mod)
                            else:
                                self.mods.append([mod])
                                self.modNots.append(op == u'-')
                    elif self.curBlockId  == u'ONLYONE':
                        maMod = reMod.match(line)
                        if maMod:
                            if maMod.group(1): raise BoltError(
                                u"ONLYONE does not support %s operators." % maMod.group(1))
                            self.mods.append(GPath(maMod.group(2)))
                    elif self.curBlockId == u'NOTES':
                        self.group.notes += line.rstrip()+u'\n'
                    elif self.curBlockId in self.ruleBlockIds:
                        maRule = reRule.match(line)
                        maExists = reExists.match(line)
                        if maRule:
                            op,mod,version,text = maRule.groups()
                            self.addGroupRule(op,mod,text)
                        elif maExists and u'..' not in maExists.groups(2):
                            self.addGroupRule(*stripped(maExists.groups()))
                self.newBlock(None)

    #--------------------------------------------------------------------------
    def __init__(self):
        """Initialize ModRuleSet."""
        self.mtime = 0
        self.header = u''
        self.defineKeys = []
        self.onlyones = []
        self.modGroups = []

#------------------------------------------------------------------------------

class ConfigHelpers:
    """Encapsulates info from mod configuration helper files (LOOT masterlist, etc.)"""

    def __init__(self):
        """Initialialize."""
        #--LOOT masterlist or if that doesn't exist use the taglist

        libbsa.Init(dirs['compiled'].s)
        # That didn't work - Wrye Bash isn't installed correctly
        if not libbsa.libbsa:
            raise bolt.BoltError(u'The libbsa API could not be loaded.')
        deprint(u'Using libbsa API version:', libbsa.version)

        liblo.Init(dirs['compiled'].s)
        # That didn't work - Wrye Bash isn't installed correctly
        if not liblo.liblo:
            raise bolt.BoltError(u'The libloadorder API could not be loaded.')
        deprint(u'Using libloadorder API version:', liblo.version)

        loot.Init(dirs['compiled'].s)
        # That didn't work - Wrye Bash isn't installed correctly
        if not loot.LootApi:
            raise bolt.BoltError(u'The LOOT API could not be loaded.')
        deprint(u'Using LOOT API version:', loot.version)

        global lootDb
        lootDb = loot.LootDb(dirs['app'].s,bush.game.fsName)

        global lo
        lo = liblo.LibloHandle(dirs['app'].s,bush.game.fsName)
        if bush.game.fsName == u'Oblivion' and dirs['mods'].join(u'Nehrim.esm').isfile():
            lo.SetGameMaster(u'Nehrim.esm')
        liblo.RegisterCallback(liblo.LIBLO_WARN_LO_MISMATCH,
                              ConfigHelpers.libloLOMismatchCallback)

        # LOOT stores the masterlist/userlist in a %LOCALAPPDATA% subdirectory.
        self.lootMasterPath = dirs['userApp'].join(os.pardir,u'LOOT',bush.game.fsName,u'masterlist.yaml')
        self.lootUserPath = dirs['userApp'].join(os.pardir,u'LOOT',bush.game.fsName,u'userlist.yaml')
        self.lootMasterTime = None
        self.lootUserTime = None
        #--Bash Tags
        self.tagCache = {}
        #--Mod Rules
        self.name_ruleSet = {}
        #--Refresh
        self.refresh(True)

    @staticmethod
    def libloLOMismatchCallback():
        """Called whenever a mismatched loadorder.txt and plugins.txt is found"""
        # Force a rewrite of both plugins.txt and loadorder.txt
        # In other words, use what's in loadorder.txt to write plugins.txt
        # TODO: Check if this actually works.
        modInfos.plugins.loadLoadOrder()
        modInfos.plugins.saveLoadOrder()

    def refresh(self,firstTime=False):
        """Reloads tag info if file dates have changed."""
        path,userpath,mtime,utime = (self.lootMasterPath, self.lootUserPath, self.lootMasterTime, self.lootUserTime)
        #--Masterlist is present, use it
        if path.exists():
            if (path.mtime != mtime or
                (userpath.exists() and userpath.mtime != utime)):
                self.tagCache = {}
                try:
                    if userpath.exists():
                        lootDb.Load(path.s,userpath.s)
                        self.lootMasterTime = path.mtime
                        self.lootUserTime = userpath.mtime
                    else:
                        lootDb.Load(path.s)
                        self.lootMasterTime = path.mtime
                    return
                except loot.LootError:
                    deprint(u'An error occurred while using the LOOT API:',traceback=True)
            if not firstTime: return
        #--No masterlist, use the taglist
        taglist = dirs['defaultPatches'].join(u'taglist.yaml')
        if not taglist.exists():
            raise bolt.BoltError(u'Mopy\\Bash Patches\\'+bush.game.fsName+u'\\taglist.yaml could not be found.  Please ensure Wrye Bash is installed correctly.')
        try:
            self.tagCache = {}
            lootDb.Load(taglist.s)
        except loot.LootError:
            deprint(u'An error occurred while parsing taglist.yaml with the LOOT API.', traceback=True)
            raise bolt.BoltError(u'An error occurred while parsing taglist.yaml with the LOOT API.')

    def getBashTags(self,modName):
        """Retrieves bash tags for given file."""
        if modName not in self.tagCache:
            tags = lootDb.GetModBashTags(modName)
            self.tagCache[modName] = tags
            return tags[0]
        else:
            return self.tagCache[modName][0]

    def getBashRemoveTags(self,modName):
        """Retrieves bash tags for given file."""
        if modName not in self.tagCache:
            tags = lootDb.GetModBashTags(modName)
            self.tagCache[modName] = tags
            return tags[1]
        else:
            return self.tagCache[modName][1]

    def getDirtyMessage(self,modName):
        message,clean = lootDb.GetDirtyMessage(modName)
        cleanIt = clean == loot.loot_needs_cleaning_yes
        return cleanIt,message

    #--Mod Checker ------------------------------------------------------------
    def refreshRuleSets(self):
        """Reloads ruleSets if file dates have changed."""
        name_ruleSet = self.name_ruleSet
        reRulesFile = re.compile(u'Rules.txt$',re.I|re.U)
        ruleFiles = set(x for x in getPatchesList() if reRulesFile.search(x.s))
        for name in name_ruleSet.keys():
            if name not in ruleFiles: del name_ruleSet[name]
        for name in ruleFiles:
            path = getPatchesPath(name)
            ruleSet = name_ruleSet.get(name)
            if not ruleSet:
                ruleSet = name_ruleSet[name] = ModRuleSet()
            if path.mtime != ruleSet.mtime:
                ModRuleSet.RuleParser(ruleSet).parse(path)

    def checkMods(self,showModList=False,showRuleSets=False,showNotes=False,showConfig=True,showSuggest=True,showCRC=False,showVersion=True,showWarn=True,scanDirty=None):
        """Checks currently loaded mods against ruleset.
           scanDirty should be the instance of ModChecker, to scan."""
        active = set(modInfos.ordered)
        merged = modInfos.merged
        imported = modInfos.imported
        activeMerged = active | merged
        warning = u'=== <font color=red>'+_(u'WARNING:')+u'</font> '
        #--Header
        with sio() as out:
            log = bolt.LogFile(out)
            log.setHeader(u'= '+_(u'Check Mods'),True)
            log(_(u'This is a report on your currently active/merged mods.'))
            #--Mergeable/NoMerge/Deactivate tagged mods
            shouldMerge = active & modInfos.mergeable
            shouldDeactivateA = [x for x in active if u'Deactivate' in modInfos[x].getBashTags()]
            shouldDeactivateB = [x for x in active if u'NoMerge' in modInfos[x].getBashTags() and x in modInfos.mergeable]
            shouldActivateA = [x for x in imported if u'MustBeActiveIfImported' in modInfos[x].getBashTags() and x not in active]
            #--Mods with invalid TES4 version
            invalidVersion = [(x,unicode(round(modInfos[x].header.version,6))) for x in active if round(modInfos[x].header.version,6) not in bush.game.esp.validHeaderVersions]
            if True:
                #--Look for dirty edits
                shouldClean = {}
                scan = []
                for x in active:
                    dirtyMessage = modInfos[x].getDirtyMessage()
                    if dirtyMessage[0]:
                        shouldClean[x] = dirtyMessage[1]
                    elif scanDirty:
                        scan.append(modInfos[x])
                if scanDirty:
                    try:
                        with balt.Progress(_(u'Scanning for Dirty Edits...'),u'\n'+u' '*60,parent=scanDirty,abort=True) as progress:
                            ret = ModCleaner.scan_Many(scan,ModCleaner.ITM|ModCleaner.UDR,progress)
                            for i,mod in enumerate(scan):
                                udrs,itms,fog = ret[i]
                                if mod.name == GPath(u'Unofficial Oblivion Patch.esp'): itms.discard((GPath(u'Oblivion.esm'),0x00AA3C))
                                if mod.header.author in (u'BASHED PATCH',u'BASHED LISTS'): itms = set()
                                if udrs or itms:
                                    cleanMsg = []
                                    if udrs:
                                        cleanMsg.append(u'UDR(%i)' % len(udrs))
                                    if itms:
                                        cleanMsg.append(u'ITM(%i)' % len(itms))
                                    cleanMsg = u', '.join(cleanMsg)
                                    shouldClean[mod.name] = cleanMsg
                    except bolt.CancelError:
                        pass
            shouldCleanMaybe = [(x,modInfos[x].getDirtyMessage()[1]) for x in active if not modInfos[x].getDirtyMessage()[0] and modInfos[x].getDirtyMessage()[1] != u'']
            for mod in tuple(shouldMerge):
                if u'NoMerge' in modInfos[mod].getBashTags():
                    shouldMerge.discard(mod)
            if shouldMerge:
                log.setHeader(u'=== '+_(u'Mergeable'))
                log(_(u'Following mods are active, but could be merged into the bashed patch.'))
                for mod in sorted(shouldMerge):
                    log(u'* __'+mod.s+u'__')
            if shouldDeactivateB:
                log.setHeader(u'=== '+_(u'NoMerge Tagged Mods'))
                log(_(u'Following mods are tagged NoMerge and should be deactivated and imported into the bashed patch but are currently active.'))
                for mod in sorted(shouldDeactivateB):
                    log(u'* __'+mod.s+u'__')
            if shouldDeactivateA:
                log.setHeader(u'=== '+_(u'Deactivate Tagged Mods'))
                log(_(u'Following mods are tagged Deactivate and should be deactivated and imported into the bashed patch but are currently active.'))
                for mod in sorted(shouldDeactivateA):
                    log(u'* __'+mod.s+u'__')
            if shouldActivateA:
                log.setHeader(u'=== '+_(u'MustBeActiveIfImported Tagged Mods'))
                log(_(u'Following mods to work correctly have to be active as well as imported into the bashed patch but are currently only imported.'))
                for mod in sorted(shouldActivateA):
                    log(u'* __'+mod.s+u'__')
            if shouldClean:
                log.setHeader(u'=== '+_(u'Mods that need cleaning with TES4Edit'))
                log(_(u'Following mods have identical to master (ITM) records, deleted records (UDR), or other issues that should be fixed with TES4Edit.  Visit the [[!http://cs.elderscrolls.com/constwiki/index.php/TES4Edit_Cleaning_Guide|TES4Edit Cleaning Guide]] for more information.'))
                for mod in sorted(shouldClean.keys()):
                    log(u'* __'+mod.s+u':__  %s' % shouldClean[mod])
            if shouldCleanMaybe:
                log.setHeader(u'=== '+_(u'Mods with special cleaning instructions'))
                log(_(u'Following mods have special instructions for cleaning with TES4Edit'))
                for mod in sorted(shouldCleanMaybe):
                    log(u'* __'+mod[0].s+u':__  '+mod[1])
            elif scanDirty and not shouldClean:
                log.setHeader(u'=== '+_(u'Mods that need cleaning with TES4Edit'))
                log(_(u'Congratulations all mods appear clean.'))
            if invalidVersion:
                log.setHeader(u'=== '+_(u'Mods with non standard TES4 versions'))
                log(_(u"Following mods have a TES4 version that isn't recognized as one of the standard versions (0.8 and 1.0).  It is untested what effect this can have on the game, but presumably Oblivion will refuse to load anything above 1.0"))
                for mod in sorted(invalidVersion):
                    log(u'* __'+mod[0].s+u':__  '+mod[1])
            #--Missing/Delinquent Masters
            if showModList:
                log(u'\n'+modInfos.getModList(showCRC,showVersion,wtxt=True).strip())
            else:
                log.setHeader(warning+_(u'Missing/Delinquent Masters'))
                previousMods = set()
                for mod in modInfos.ordered:
                    loggedMod = False
                    for master in modInfos[mod].header.masters:
                        if master not in active:
                            label = _(u'MISSING')
                        elif master not in previousMods:
                            label = _(u'DELINQUENT')
                        else:
                            label = u''
                        if label:
                            if not loggedMod:
                                log(u'* '+mod.s)
                                loggedMod = True
                            log(u'  * __%s__ %s' %(label,master.s))
                    previousMods.add(mod)
            #--Rule Sets
            if showRuleSets:
                self.refreshRuleSets()
                for fileName in sorted(self.name_ruleSet):
                    ruleSet = self.name_ruleSet[fileName]
                    modRules = ruleSet.modGroups
                    log.setHeader(u'= ' + fileName.s[:-4],True)
                    if ruleSet.header: log(ruleSet.header)
                    #--One ofs
                    for modSet in ruleSet.onlyones:
                        modSet &= activeMerged
                        if len(modSet) > 1:
                            log.setHeader(warning+_(u'Only one of these should be active/merged'))
                            for mod in sorted(modSet):
                                log(u'* '+mod.s)
                    #--Mod Rules
                    for modGroup in ruleSet.modGroups:
                        if not modGroup.isActive(activeMerged): continue
                        modList = u' + '.join([x.s for x in modGroup.getActives(activeMerged)])
                        if showNotes and modGroup.notes:
                            log.setHeader(u'=== '+_(u'NOTES: ') + modList )
                            log(modGroup.notes)
                        if showConfig:
                            log.setHeader(u'=== '+_(u'CONFIGURATION: ') + modList )
                            #    + _(u'\nLegend: x: Active, +: Merged, -: Inactive'))
                            for ruleType,ruleMod,comment in modGroup.config:
                                if ruleType != u'o': continue
                                if ruleMod in active: bullet = u'x'
                                elif ruleMod in merged: bullet = u'+'
                                elif ruleMod in imported: bullet = u'*'
                                else: bullet = u'o'
                                log(u'%s __%s__ -- %s' % (bullet,ruleMod.s,comment))
                        if showSuggest:
                            log.setHeader(u'=== '+_(u'SUGGESTIONS: ') + modList)
                            for ruleType,ruleMod,comment in modGroup.suggest:
                                if ((ruleType == u'x' and ruleMod not in activeMerged) or
                                    (ruleType == u'+' and (ruleMod in active or ruleMod not in merged)) or
                                    (ruleType == u'-' and ruleMod in activeMerged) or
                                    (ruleType == u'-+' and ruleMod in active)
                                    ):
                                    log(u'* __%s__ -- %s' % (ruleMod.s,comment))
                                elif ruleType == u'e' and not dirs['mods'].join(ruleMod).exists():
                                    log(u'* '+comment)
                        if showWarn:
                            log.setHeader(warning + modList)
                            for ruleType,ruleMod,comment in modGroup.warn:
                                if ((ruleType == u'x' and ruleMod not in activeMerged) or
                                    (ruleType == u'+' and (ruleMod in active or ruleMod not in merged)) or
                                    (ruleType == u'-' and ruleMod in activeMerged) or
                                    (ruleType == u'-+' and ruleMod in active)
                                    ):
                                    log(u'* __%s__ -- %s' % (ruleMod.s,comment))
                                elif ruleType == u'e' and not dirs['mods'].join(ruleMod).exists():
                                    log(u'* '+comment)
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
        self.dictFile = PickleDict(dirs['saveBase'].join(u'Messages.dat'))
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
        with path.open('w',encoding='utf-8-sig') as out:
            out.write(bush.messagesHeader)
            for key in keys:
                out.write(self.data[key][3])
                out.write(u'\n<br />')
            out.write(u"\n</div></body></html>")

    def importArchive(self,path):
        """Import archive file into data."""
        #--Today, yesterday handling
        maPathDate = re.match(ur'(\d+)\.(\d+)\.(\d+)',path.stail,flags=re.U)
        dates = {'today':None,'yesterday':None,'previous':None}
        if maPathDate:
            year,month,day = map(int,maPathDate.groups())
            if year < 100: year += 2000
            dates['today'] = datetime.datetime(year,month,day)
            dates['yesterday'] = dates['today'] - datetime.timedelta(1)
        reRelDate = re.compile(ur'(Today|Yesterday), (\d+):(\d+) (AM|PM)',re.U)
        reAbsDateNew = re.compile(ur'(\d+) (\w+) (\d+) - (\d+):(\d+) (AM|PM)',re.U)
        reAbsDate = re.compile(ur'(\w+) (\d+) (\d+), (\d+):(\d+) (AM|PM)',re.U)
        month_int = dict((x,i+1) for i,x in
            enumerate(u'Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec'.split(u',')))
        month_int.update(dict((x,i+1) for i,x in
            enumerate(u'January,February,March,April,May,June,July,August,September,October,November,December'.split(u','))))
        def getTime(sentOn):
            maRelDate = reRelDate.search(sentOn)
            if not maRelDate:
                #date = time.strptime(sentOn,'%b %d %Y, %I:%M %p')[:-1]+(0,)
                maAbsDate = reAbsDate.match(sentOn)
                if maAbsDate:
                    month,day,year,hour,minute,ampm = maAbsDate.groups()
                else:
                    maAbsDate = reAbsDateNew.match(sentOn)
                    day,month,year,hour,minute,ampm = maAbsDate.groups()
                day,year,hour,minute = map(int,(day,year,hour,minute))
                month = month_int[month]
                hour = (hour,0)[hour==12] + (0,12)[ampm=='PM']
                date = (year,month,day,hour,minute,0,0,0,-1)
                dates['previous'] = datetime.datetime(year,month,day)
            else:
                if not dates['yesterday']:
                    dates['yesterday'] = dates['previous'] + datetime.timedelta(1)
                    dates['today'] = dates['yesterday'] + datetime.timedelta(1)
                strDay,hour,minute,ampm = maRelDate.groups()
                hour,minute = map(int,(hour,minute))
                hour = (hour,0)[hour==12] + (0,12)[ampm==u'PM']
                ymd = dates[strDay.lower()]
                date = ymd.timetuple()[0:3]+(hour,minute,0,0,0,0)
            return time.mktime(date)
        #--Html entity substitution
        from htmlentitydefs import name2codepoint
        def subHtmlEntity(match):
            entity = match.group(2)
            if match.group(1) == u"#":
                return unichr(int(entity)).encode()
            else:
                cp = name2codepoint.get(entity)
                if cp:
                    return unichr(cp).encode()
                else:
                    return match.group()
        #--Re's
        reHtmlEntity = re.compile(u"&(#?)(\d{1,5}|\w{1,8});",re.U)

        #New style re's
        reLineEndings   = re.compile(u"(?:\n)|(?:\r\n)",re.U)
        reBodyNew       = re.compile(u"<body id='ipboard_body'>",re.U)
        reTitleNew      = re.compile(u'<div id=["\']breadcrumb["\']>Bethesda Softworks Forums -> (.*?)</div>',re.U)
        reAuthorNew     = re.compile(u'<h3><a href=["\']http\://forums\.bethsoft\.com/index\.php\?/user/.*?/["\']>(.*?)</a></h3>',re.U)
        reDateNew       = re.compile(u'Sent (.*?)$',re.U)
        reMessageNew    = re.compile(u'<div class=["\']post entry-content["\']>',re.U)
        reEndMessageNew = re.compile(u'^        </div>$',re.U)
        #Old style re's
        reBody         = re.compile(u'<body>',re.U)
        reWrapper      = re.compile(u'<div id=["\']ipbwrapper["\']>',re.U) #--Will be removed
        reMessage      = re.compile(u'<div class="borderwrapm">',re.U)
        reMessageOld   = re.compile(u"<div class='tableborder'>",re.U)
        reTitle        = re.compile(u'<div class="maintitle">PM: (.+)</div>',re.U)
        reTitleOld     = re.compile(u'<div class=\'maintitle\'><img[^>]+>&nbsp;',re.U)
        reSignature    = re.compile(u'<div class="formsubtitle">',re.U)
        reSignatureOld = re.compile(u'<div class=\'pformstrip\'>',re.U)
        reSent         = re.compile(u'Sent (by|to) <b>(.+)</b> on (.+)</div>',re.U)
        #--Final setup, then parse the file
        (HEADER,BODY,MESSAGE,OLDSTYLE,NEWSTYLE,AUTHOR,DATE,MESSAGEBODY) = range(8)
        whichStyle = OLDSTYLE
        mode = HEADER
        buff = None
        subject = u"<No Subject>"
        author = None
        with path.open() as ins:
            for line in ins:
    ##            print mode,'>>',line,
                if mode == HEADER: #--header
                    if reBodyNew.search(line):
                        mode = BODY
                        whichStyle = NEWSTYLE
                    elif reBody.search(line):
                        mode = BODY
                        whichStyle = OLDSTYLE
                if mode != HEADER and whichStyle == OLDSTYLE:
                    line = reMessageOld.sub(u'<div class="borderwrapm">',line)
                    line = reTitleOld.sub(u'<div class="maintitle">',line)
                    line = reSignatureOld.sub(u'<div class="formsubtitle">',line)
                    if mode == BODY:
                        if reMessage.search(line):
                            subject = u"<No Subject>"
                            buff = sio()
                            buff.write(reWrapper.sub(u'',line))
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
                                messageKey = u'::'.join((subject,author,unicode(int(date))))
                                newSent = (_(u'Sent %s <b>%s</b> on %s</div>') % (direction,
                                    author,time.strftime(u'%b %d %Y, %I:%M %p',time.localtime(date))))
                                line = reSent.sub(newSent,line,1)
                                buff.write(line)
                                self.data[messageKey] = (subject,author,date,buff.getvalue())
                            buff.close()
                            buff = None
                            mode = BODY
                        else:
                            buff.write(line)
                elif mode != HEADER and whichStyle == NEWSTYLE:
                    if mode == BODY:
                        if reTitleNew.search(line):
                            subject = reTitleNew.search(line).group(1)
                            subject = reHtmlEntity.sub(subHtmlEntity,subject)
                            mode = AUTHOR
                    elif mode == AUTHOR:
                        if reAuthorNew.search(line):
                            author = reAuthorNew.search(line).group(1)
                            mode = DATE
                    elif mode == DATE:
                        if reDateNew.search(line):
                            date = reDateNew.search(line).group(1)
                            date = getTime(date)
                            mode = MESSAGE
                    elif mode == MESSAGE:
                        if reMessageNew.search(line):
                            buff = sio()
                            buff.write(u'<br /><div class="borderwrapm">\n')
                            buff.write(u'    <div class="maintitle">PM: %s</div>\n' % subject)
                            buff.write(u'    <div class="tablefill"><div class="postcolor">')
                            mode = MESSAGEBODY
                    elif mode == MESSAGEBODY:
                        if reEndMessageNew.search(line):
                            buff.write(u'    <div class="formsubtitle">Sent by <b>%s</b> on %s</div>\n' % (author,time.strftime('%b %d %Y, %I:%M %p',time.localtime(date))))
                            messageKey = u'::'.join((subject,author,unicode(int(date))))
                            self.data[messageKey] = (subject,author,date,buff.getvalue())
                            buff.close()
                            buff = None
                            mode = AUTHOR
                        else:
                            buff.write(reLineEndings.sub(u'',line))
        self.hasChanged = True
        self.save()

#------------------------------------------------------------------------------
class ModBaseData(PickleTankData, bolt.TankData, DataDict):
    """Mod database. (IN DEVELOPMENT.)
    The idea for this is to provide a mod database. However, I might not finish this."""

    def __init__(self):
        bolt.TankData.__init__(self,settings)
        PickleTankData.__init__(self,dirs['saveBase'].join(u'ModBase.dat'))
        #--Default settings. Subclasses should define these.
        self.tankKey = 'bash.modBase'
        self.tankColumns = ['Package','Author','Version','Tags']
        self.title = _(u'ModBase')
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
            return item,author,version,tags

    def getName(self,item):
        """Returns a string name of item for use in dialogs, etc."""
        return item

    def getGuiKeys(self,item):
        """Returns keys for icon and text and background colors."""
        textKey = backKey = None
        iconKey = u'karma%+d' % self.data[item][1]
        return iconKey,textKey,backKey

#------------------------------------------------------------------------------
class PeopleData(PickleTankData, bolt.TankData, DataDict):
    """Data for a People Tank."""
    def __init__(self):
        bolt.TankData.__init__(self,settings)
        PickleTankData.__init__(self,dirs['saveBase'].join(u'People.dat'))
        #--Default settings. Subclasses should define these.
        self.tankKey = 'bash.people'
        self.tankColumns = ['Name','Karma','Header']
        self.title = _(u'People')
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
        if item is None: return columns[:]
        labels,itemData = [],self.data[item]
        for column in columns:
            if column == 'Name': labels.append(item)
            elif column == 'Karma':
                karma = itemData[1]
                labels.append((u'-',u'+')[karma>=0]*abs(karma))
            elif column == 'Header':
                header = itemData[2].split(u'\n',1)[0][:75]
                labels.append(header)
        return labels

    def getName(self,item):
        """Returns a string name of item for use in dialogs, etc."""
        return item

    def getGuiKeys(self,item):
        """Returns keys for icon and text and background colors."""
        textKey = backKey = None
        iconKey = u'karma%+d' % self.data[item][1]
        return iconKey,textKey,backKey

    #--Operations
    def loadText(self,path):
        """Enter info from text file."""
        newNames,name,buffer = set(),None,None
        with path.open('r') as ins:
            reName = re.compile(ur'==([^=]+)=*$',re.U)
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
                if name: buffer = sio()
        if newNames: self.setChanged()
        return newNames

    def dumpText(self,path,names):
        """Dump to text file."""
        with path.open('w',encoding='utf-8-sig') as out:
            for name in sorted(names,key=string.lower):
                out.write(u'== %s %s\n' % (name,u'='*(75-len(name))))
                out.write(self.data[name][2].strip())
                out.write(u'\n\n')

#------------------------------------------------------------------------------
class ScreensData(DataDict):
    def __init__(self):
        self.dir = dirs['app']
        self.data = {} #--data[Path] = (ext,mtime)

    def refresh(self):
        """Refresh list of screenshots."""
        self.dir = dirs['app']
        ssBase = GPath(oblivionIni.getSetting(u'Display',u'SScreenShotBaseName',u'ScreenShot'))
        if ssBase.head:
            self.dir = self.dir.join(ssBase.head)
        newData = {}
        reImageExt = re.compile(ur'\.(bmp|jpg|jpeg|png|tif|gif)$',re.I|re.U)
        #--Loop over files in directory
        for fileName in self.dir.list():
            filePath = self.dir.join(fileName)
            maImageExt = reImageExt.search(fileName.s)
            if maImageExt and filePath.isfile():
                newData[fileName] = (maImageExt.group(1).lower(),filePath.mtime)
        changed = (self.data != newData)
        self.data = newData
        return changed

    def delete(self,fileName,askOk=True,dontRecycle=False):
        """Deletes member file."""
        dirJoin = self.dir.join
        if isinstance(fileName,(list,set)):
            filePath = [dirJoin(file) for file in fileName]
        else:
            filePath = [dirJoin(fileName)]
        deleted = balt.shellDelete(filePath,askOk=askOk,recycle=not dontRecycle)
        if deleted is not None:
            for file in filePath:
                del self.data[file.tail]

#------------------------------------------------------------------------------
class Installer(object):
    """Object representing an installer archive, its user configuration, and
    its installation state."""

    #--Member data
    persistent = ('archive','order','group','modified','size','crc',
        'fileSizeCrcs','type','isActive','subNames','subActives','dirty_sizeCrc',
        'comments','readMe','packageDoc','packagePic','src_sizeCrcDate','hasExtraData',
        'skipVoices','espmNots','isSolid','blockSize','overrideSkips','remaps',
        'skipRefresh','fileRootIdex')
    volatile = ('data_sizeCrc','skipExtFiles','skipDirFiles','status','missingFiles',
        'mismatchedFiles','refreshed','mismatchedEspms','unSize','espms',
        'underrides','hasWizard','espmMap','hasReadme','hasBCF','hasBethFiles')
    __slots__ = persistent+volatile
    #--Package analysis/porting.
    docDirs = {u'screenshots'}
    dataDirsMinus = {u'bash', u'replacers',
                     u'--'}  #--Will be skipped even if hasExtraData == True.
    reDataFile = re.compile(ur'(masterlist.txt|dlclist.txt|\.(esp|esm|bsa|ini))$',re.I|re.U)
    reReadMe = re.compile(ur'^.*?([^\\]*)(read[ _]?me|lisez[ _]?moi)([^\\]*)\.(txt|rtf|htm|html|doc|odt)$',re.I|re.U)
    skipExts = {u'.exe', u'.py', u'.pyc', u'.7z', u'.zip', u'.rar', u'.db',
                u'.ace', u'.tgz', u'.tar', u'.gz', u'.bz2', u'.omod',
                u'.fomod', u'.tb2', u'.lzma', u'.bsl'}
    skipExts.update(set(readExts))
    docExts = {u'.txt', u'.rtf', u'.htm', u'.html', u'.doc', u'.docx', u'.odt',
               u'.mht', u'.pdf', u'.css', u'.xls', u'.xlsx', u'.ods', u'.odp',
               u'.ppt', u'.pptx'}
    imageExts = {u'.gif', u'.jpg', u'.png', u'.jpeg', u'.bmp'}
    scriptExts = {u'.txt', u'.ini', u'.cfg'}
    commonlyEditedExts = scriptExts | {u'.xml'}
    #--Needs to be called after bush.game has been set
    @staticmethod
    def initData():
        Installer.dataDirs = bush.game.dataDirs
        Installer.dataDirsPlus = Installer.dataDirs | Installer.docDirs | bush.game.dataDirsPlus

    #--Temp Files/Dirs
    _tempDir = None
    @staticmethod
    def newTempDir():
        """Generates a new temporary directory name, sets it as the current Temp Dir."""
        Installer._tempDir = Path.tempDir(u'WryeBash_')
        return Installer._tempDir

    @staticmethod
    def rmTempDir():
        """Removes the current temporary directory, and sets the current Temp Dir to
           None - meaning a new one will be generated on getTempDir()"""
        if Installer._tempDir is None:
            return
        if Installer._tempDir.exists():
            Installer._tempDir.rmtree(safety=Installer._tempDir.stail)
        Installer._tempDir = None

    @staticmethod
    def getTempDir():
        """Returns current Temp Dir, generating one if needed."""
        return Installer._tempDir if Installer._tempDir is not None else Installer.newTempDir()

    @staticmethod
    def clearTemp():
        """Clear the current Temp Dir, but leave it as the current Temp dir still."""
        if Installer._tempDir is not None and Installer._tempDir.exists():
            try:
                Installer._tempDir.rmtree(safety=Installer._tempDir.stail)
            except:
                Installer._tempDir.rmtree(safety=Installer._tempDir.stail)

    tempList = Path.baseTempDir().join(u'WryeBash_InstallerTempList.txt')

    #--Class Methods ----------------------------------------------------------
    @staticmethod
    def getGhosted():
        """Returns map of real to ghosted files in mods directory."""
        dataDir = dirs['mods']
        ghosts = [x for x in dataDir.list() if x.cs[-6:] == u'.ghost']
        return dict((x.root,x) for x in ghosts if not dataDir.join(x).root.exists())

    @staticmethod
    def sortFiles(files):
        """Utility function. Sorts files by directory, then file name."""
        def sortKey(file):
            dirFile = os.path.split(file)
            if len(dirFile) == 1: dirFile.insert(0,u'')
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
        progress = progress if progress else bolt.Progress()
        new_sizeCrcDate = {}
        bethFiles = set() if settings['bash.installers.autoRefreshBethsoft'] else bush.game.bethDataFiles
        skipExts = Installer.skipExts
        asRoot = apRoot.s
        relPos = len(asRoot)+1
        pending = set()
        #--Scan for changed files
        progress(0,rootName+u': '+_(u'Pre-Scanning...'))
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
        obse = bush.game.se.shortName.lower()
        sd = bush.game.sd.installDir.lower()
        setSkipLod = settings['bash.installers.skipDistantLOD']
        setSkipScreen = settings['bash.installers.skipScreenshots']
        setSkipOBSE = not settings['bash.installers.allowOBSEPlugins']
        setSkipSD = bush.game.sd.shortName and setSkipOBSE
        setSkipDocs = settings['bash.installers.skipDocs']
        setSkipImages = settings['bash.installers.skipImages']
        transProgress = u'%s: '+_(u'Pre-Scanning...')+u'\n%s'
        dataDirsMinus = Installer.dataDirsMinus
        if inisettings['KeepLog'] > 1:
            try: log = inisettings['LogFile'].open('a',encoding='utf-8-sig')
            except: log = None
        else: log = None
        for asDir,sDirs,sFiles in os.walk(asRoot):
            progress(0.05,transProgress % (rootName,asDir[relPos:]))
            if rootIsMods and asDir == asRoot:
                newSDirs = (x for x in sDirs if x.lower() not in dataDirsMinus)
                if setSkipLod:
                    newSDirs = (x for x in newSDirs if x.lower() != u'distandlod')
                if setSkipScreen:
                    newSDirs = (x for x in newSDirs if x.lower() != u'screenshots')
                if setSkipOBSE:
                    newSDirs = (x for x in newSDirs if x.lower() != obse)
                if setSkipSD:
                    newSDirs = (x for x in newSDirs if x.lower() != sd)
                if setSkipDocs and setSkipImages:
                    newSDirs = (x for x in newSDirs if x.lower() != u'docs')
                newSDirs = [x for x in newSDirs if x.lower() not in bush.game.SkipBAINRefresh]
                sDirs[:] = [x for x in newSDirs]
                if log: log.write(u'(in refreshSizeCRCDate after accounting for skipping) sDirs = %s\n'%(sDirs[:]))
            dirDirsFilesAppend((asDir,sDirs,sFiles))
            if not (sDirs or sFiles): emptyDirsAdd(GPath(asDir))
        if log: log.close()
        progress(0,_(u"%s: Scanning...") % rootName)
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
                sFileLower = sFile.lower()
                ext = sFileLower[sFileLower.rfind(u'.'):]
                rpFile = rpDirJoin(sFile)
                if inModsRoot:
                    if ext in skipExts: continue
                    if not rsDir and sFileLower in bethFiles:
                        continue
                    rpFile = ghostGet(rpFile,rpFile)
                isEspm = not rsDir and ext in (u'.esp',u'.esm')
                apFile = apDirJoin(sFile)
                size = apFile.size
                date = apFile.mtime
                oSize,oCrc,oDate = oldGet(rpFile,(0,0,0))
                if not isEspm and size == oSize and date == oDate:
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
            totalSize = sum([apRootJoin(normGet(x,x)).size for x in pending])
            done = 0
            progress(0,rootName+u'\n'+_(u'Calculating CRCs...')+u'\n')
            # each mod increments the progress bar by at least one, even if it is size 0
            # add len(pending) to the progress bar max to ensure we don't hit 100% and cause the progress bar
            # to prematurely disappear
            progress.setFull(max(totalSize+len(pending),1))
            for rpFile in sorted(pending):
                progress(done,rootName+u'\n'+_(u'Calculating CRCs...')+u'\n'+rpFile.s)
                try:
                    apFile = apRootJoin(normGet(rpFile,rpFile))
                    size = apFile.size
                    crc = apFile.crcProgress(bolt.SubProgress(progress,done,done+max(size,1)))
                    date = apFile.mtime
                    done += size
                except WindowsError:
                    deprint(_(u'Failed to calculate crc for %s - please report this, and the following traceback:') % apFile.s, traceback=True)
                    continue
                new_sizeCrcDate[rpFile] = (size,crc,date)
        old_sizeCrcDate.clear()
        old_sizeCrcDate.update(new_sizeCrcDate)
        #--Done
        return changed

    #--Initization, etc -------------------------------------------------------
    def initDefault(self):
        """Inits everything to default values."""
        #--Package Only
        self.archive = u''
        self.modified = 0 #--Modified date
        self.size = 0 #--size of archive file
        self.crc = 0 #--crc of archive
        self.type = 0 #--Package type: 0: unset/invalid; 1: simple; 2: complex
        self.isSolid = False
        self.blockSize = None
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
        self.overrideSkips = False
        self.skipRefresh = False    # Projects only
        self.comments = u''
        self.group = u'' #--Default from abstract. Else set by user.
        self.order = -1 #--Set by user/interface.
        self.isActive = False
        self.espmNots = set() #--Lowercase esp/m file names that user has decided not to install.
        self.remaps = {}
        self.fileRootIdex = 0
        #--Volatiles (unpickled values)
        #--Volatiles: directory specific
        self.refreshed = False
        #--Volatile: set by refreshDataSizeCrc
        self.hasWizard = False
        self.hasBCF = False
        self.espmMap = {}
        self.readMe = self.packageDoc = self.packagePic = None
        self.hasReadme = False
        self.hasBethFiles = False
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

    def resetEspmName(self,currentName):
        oldName = self.getEspmName(currentName)
        del self.remaps[oldName]
        path = GPath(currentName)
        if path in self.espmNots:
            self.espmNots.discard(path)
            self.espmNots.add(GPath(oldName))

    def resetAllEspmNames(self):
        for espm in self.remaps.keys():
            # Need to use .keys(), since 'resetEspmName' will use
            # del self.remaps[oldName], changing the dictionary
            # size.
            self.resetEspmName(self.remaps[espm])

    def getEspmName(self,currentName):
        for old in self.remaps:
            if self.remaps[old] == currentName:
                return old
        return currentName

    def setEspmName(self,currentName,newName):
        oldName = self.getEspmName(currentName)
        self.remaps[oldName] = newName
        path = GPath(currentName)
        if path in self.espmNots:
            self.espmNots.discard(path)
            self.espmNots.add(GPath(newName))
        else:
            self.espmNots.discard(GPath(newName))

    def isEspmRenamed(self,currentName):
        return self.getEspmName(currentName) != currentName

    def __init__(self,archive):
        self.initDefault()
        self.archive = archive.stail

    def __getstate__(self):
        """Used by pickler to save object state."""
        getter = object.__getattribute__
        return tuple(getter(self,x) for x in self.persistent)

    def __setstate__(self,values):
        """Used by unpickler to recreate object."""
        self.initDefault()
        map(self.__setattr__,self.persistent,values)
        if self.dirty_sizeCrc is None:
            self.dirty_sizeCrc = {} #--Use empty dict instead.
        if hasattr(self,'fileSizeCrcs'):
            # Older pickle files didn't store filenames in unicode,
            # convert them here.
            self.fileSizeCrcs = [(_unicode(full),size,crc) for (full,size,crc) in self.fileSizeCrcs]
        self.refreshDataSizeCrc()

    def __copy__(self,iClass=None):
        """Create a copy of self -- works for subclasses too (assuming subclasses
        don't add new data members). iClass argument is to support Installers.updateDictFile"""
        iClass = iClass if iClass else self.__class__
        clone = iClass(GPath(self.archive))
        copier = copy.copy
        getter = object.__getattribute__
        setter = object.__setattr__
        for attr in Installer.__slots__:
            setter(clone,attr,copier(getter(self,attr)))
        return clone

    def refreshDataSizeCrc(self,checkOBSE=False):
        """Updates self.data_sizeCrc and related variables.
        Also, returns dest_src map for install operation."""
        if isinstance(self,InstallerArchive):
            archiveRoot = GPath(self.archive).sroot
        else:
            archiveRoot = self.archive
        reReadMe = self.reReadMe
        docExts = self.docExts
        imageExts = self.imageExts
        scriptExts = self.scriptExts
        docDirs = self.docDirs
        dataDirsPlus = self.dataDirsPlus
        dataDirsMinus = self.dataDirsMinus
        skipExts = self.skipExts
        packageFiles = {u'package.txt', u'package.jpg'}
        unSize = 0
        espmNots = self.espmNots
        bethFiles = bush.game.bethDataFiles
        if self.overrideSkips:
            skipVoices = False
            skipEspmVoices = None
            skipScreenshots = False
            skipDocs = False
            skipImages = False
            skipDistantLOD = False
            skipLandscapeLODMeshes = False
            skipLandscapeLODTextures = False
            skipLandscapeLODNormals = False
            renameStrings = False
            bethFilesSkip = set()
        else:
            skipVoices = self.skipVoices
            skipEspmVoices = set(x.cs for x in espmNots)
            skipScreenshots = settings['bash.installers.skipScreenshots']
            skipDocs = settings['bash.installers.skipDocs']
            skipImages = settings['bash.installers.skipImages']
            skipDistantLOD = settings['bash.installers.skipDistantLOD']
            skipLandscapeLODMeshes = settings['bash.installers.skipLandscapeLODMeshes']
            skipLandscapeLODTextures = settings['bash.installers.skipLandscapeLODTextures']
            skipLandscapeLODNormals = settings['bash.installers.skipLandscapeLODNormals']
            renameStrings = settings['bash.installers.renameStrings'] if bush.game.esp.stringsFiles else False
            bethFilesSkip = set() if settings['bash.installers.autoRefreshBethsoft'] else bush.game.bethDataFiles
        language = oblivionIni.getSetting(u'General',u'sLanguage',u'English') if renameStrings else u''
        languageLower = language.lower()
        skipObse = not settings['bash.installers.allowOBSEPlugins']
        obseDir = bush.game.se.shortName.lower()+u'\\'
        skipSd = bush.game.sd.shortName and skipObse
        sdDir = bush.game.sd.installDir.lower()+u'\\'
        skipSp = bush.game.sp.shortName and skipObse
        spDir = bush.game.sp.installDir.lower()+u'\\'
        hasExtraData = self.hasExtraData
        type = self.type
        if type == 2:
            allSubs = set(self.subNames[1:])
            activeSubs = set(x for x,y in zip(self.subNames[1:],self.subActives[1:]) if y)
        #--Init to empty
        self.hasWizard = False
        self.hasBCF = False
        self.readMe = self.packageDoc = self.packagePic = None
        self.hasReadme = False
        for attr in {'skipExtFiles','skipDirFiles','espms'}:
            object.__getattribute__(self,attr).clear()
        data_sizeCrc = {}
        remaps = self.remaps
        skipExtFiles = self.skipExtFiles
        skipDirFiles = self.skipDirFiles
        skipDirFilesAdd = skipDirFiles.add
        skipDirFilesDiscard = skipDirFiles.discard
        skipExtFilesAdd = skipExtFiles.add
        commonlyEditedExts = Installer.commonlyEditedExts
        if trackedInfos:
            dirsModsJoin = dirs['mods'].join
            _trackedInfosTrack = trackedInfos.track
            trackedInfosTrack = lambda a: _trackedInfosTrack(dirsModsJoin(a))
        else:
            trackedInfosTrack = lambda a: None
        goodDlls, badDlls = settings['bash.installers.goodDlls'],settings['bash.installers.badDlls']
        espms = self.espms
        espmsAdd = espms.add
        espmMap = self.espmMap = {}
        espmMapSetdefault = espmMap.setdefault
        reModExtMatch = reModExt.match
        reReadMeMatch = reReadMe.match
        splitExt = os.path.splitext
        dest_src = {}
        #--Bad archive?
        if type not in {1,2}: return dest_src
        #--Scan over fileSizeCrcs
        rootIdex = self.fileRootIdex
        for full,size,crc in self.fileSizeCrcs:
            file = full[rootIdex:]
            fileLower = file.lower()
            if fileLower.startswith((u'--',u'omod conversion data',u'fomod',u'wizard images')):
                continue
            sub = u''
            if type == 2: #--Complex archive
                sub = file.split(u'\\',1)
                if len(sub) == 1:
                    file, = sub
                    sub = u''
                else:
                    sub,file = sub
                if sub not in activeSubs:
                    if sub not in allSubs:
                        skipDirFilesAdd(file)
                    # Run a modified version of the normal checks, just
                    # looking for esp's for the wizard espmMap, wizard.txt
                    # and readme's
                    skip = True
                    fileLower = file.lower()
                    subList = espmMapSetdefault(sub,[])
                    subListAppend = subList.append
                    rootLower,fileExt = splitExt(fileLower)
                    rootLower = rootLower.split(u'\\',1)
                    if len(rootLower) == 1: rootLower = u''
                    else: rootLower = rootLower[0]
                    if fileLower == u'wizard.txt':
                        self.hasWizard = full
                        skipDirFilesDiscard(file)
                        continue
                    elif fileExt in defaultExt and (fileLower[-7:-3] == u'-bcf' or u'-bcf-' in fileLower):
                        ## Disabling Auto-BCF's for now, until the code for them can be updated to the latest
                        ## tempDir stuff
                        ## TODO: DO THIS!
                        #self.hasBCF = full
                        skipDirFilesDiscard(file)
                        continue
                    elif fileExt in docExts and sub == u'':
                        if not self.hasReadme:
                            if reReadMeMatch(file):
                                self.hasReadme = full
                                skipDirFilesDiscard(file)
                                skip = False
                    elif fileLower in bethFiles:
                        self.hasBethFiles = True
                        continue
                    elif not hasExtraData and rootLower and rootLower not in dataDirsPlus:
                        continue
                    elif hasExtraData and rootLower and rootLower in dataDirsMinus:
                        continue
                    elif fileExt in skipExts:
                        continue
                    elif not rootLower and reModExtMatch(fileExt):
                        #--Remap espms as defined by the user
                        if file in self.remaps: file = self.remaps[file]
                        if file not in subList: subListAppend(file)
                    if skip:
                        continue
                fileLower = file.lower()
            subList = espmMapSetdefault(sub,[])
            subListAppend = subList.append
            rootLower,fileExt = splitExt(fileLower)
            rootLower = rootLower.split(u'\\',1)
            if len(rootLower) == 1: rootLower = u''
            else: rootLower = rootLower[0]
            fileEndsWith = fileLower.endswith
            fileStartsWith = fileLower.startswith
            filePath = fileLower.split('\\')
            del filePath[-1]
            filePath = '\\'.join(filePath)
            #--Silent skips
            if fileEndsWith((u'thumbs.db',u'desktop.ini',u'config')):
                continue #--Silent skip
            elif skipDistantLOD and fileStartsWith(u'distantlod'):
                continue
            elif skipLandscapeLODMeshes and fileStartsWith(u'meshes\\landscape\\lod'):
                continue
            elif fileStartsWith(u'textures\\landscapelod\\generated'):
                if skipLandscapeLODNormals and fileEndsWith(u'_fn.dds'):
                    continue
                elif skipLandscapeLODTextures and not fileEndsWith(u'_fn.dds'):
                    continue
            elif skipVoices and fileStartsWith(u'sound\\voice'):
                continue
            elif skipScreenshots and fileStartsWith(u'screenshots'):
                continue
            elif fileLower == u'wizard.txt':
                self.hasWizard = full
                continue
            elif fileExt in defaultExt and (fileLower[-7:-3] == u'-bcf' or u'-bcf-' in fileLower):
                self.hasBCF = full
                continue
            elif skipImages and fileExt in imageExts:
                continue
            elif fileExt in docExts:
                if reReadMeMatch(file):
                    self.hasReadme = full
                if skipDocs and not (fileLower.split('\\')[-1] in bush.game.dontSkip) and not (fileExt in bush.game.dontSkipDirs.get(filePath, [])):
                    continue
            elif fileStartsWith(u'--'):
                continue
            elif skipObse and fileStartsWith(obseDir):
                continue
            elif fileExt in {u'.dll',u'.dlx'}:
                if skipObse: continue
                if not fileStartsWith(obseDir):
                    continue
                if fileLower in badDlls and [archiveRoot,size,crc] in badDlls[fileLower]: continue
                if not checkOBSE:
                    pass
                elif fileLower in goodDlls and [archiveRoot,size,crc] in goodDlls[fileLower]: pass
                elif checkOBSE:
                    message = u'\n'.join((
                        _(u'This installer (%s) has an %s plugin DLL.'),
                        _(u'The file is %s'),
                        _(u'Such files can be malicious and hence you should be very sure you know what this file is and that it is legitimate.'),
                        _(u'Are you sure you want to install this?'),
                        )) % (archiveRoot, bush.game.se.shortName, full)
                    if fileLower in goodDlls:
                        message += _(u' You have previously chosen to install a dll by this name but with a different size, crc and or source archive name.')
                    elif fileLower in badDlls:
                        message += _(u' You have previously chosen to NOT install a dll by this name but with a different size, crc and or source archive name - make extra sure you want to install this one before saying yes.')
                    if not balt.askYes(installersWindow,message,bush.game.se.shortName + _(u' DLL Warning')):
                        badDlls.setdefault(fileLower,[])
                        badDlls[fileLower].append([archiveRoot,size,crc])
                        continue
                    goodDlls.setdefault(fileLower,[])
                    goodDlls[fileLower].append([archiveRoot,size,crc])
            elif fileExt == u'.asi':
                if skipSd: continue
                if not fileStartsWith(sdDir): continue
                if fileLower in badDlls and [archiveRoot,size,crc] in badDlls[fileLower]: continue
                if not checkOBSE:
                    pass
                elif fileLower in goodDlls and [archiveRoot,size,crc] in goodDlls[fileLower]: pass
                elif checkOBSE:
                    message = u'\n'.join((
                        _(u'This installer (%s) has an %s plugin ASI.'),
                        _(u'The file is %s'),
                        _(u'Such files can be malicious and hence you should be very sure you know what this file is and that it is legitimate.'),
                        _(u'Are you sure you want to install this?'),
                        )) % (archiveRoot, bush.game.sd.longName, full)
                    if fileLower in goodDlls:
                        message += _(u' You have previously chosen to install an asi by this name but with a different size, crc and or source archive name.')
                    elif fileLower in badDlls:
                        message += _(u' You have previously chosen to NOT install an asi by this name but with a different size, crc, and or source archive name - make extra sure you want to install this one before saying yes.')
                    if not balt.askYes(installersWindow,message,bush.game.sd.longName + _(u' ASI Warning')):
                        badDlls.setdefault(fileLower,[])
                        badDlls[fileLower].append([archiveRoot,size,crc])
                        continue
                    goodDlls.setdefault(fileLower,[])
                    goodDlls[fileLower].append([archiveRoot,size,crc])
            elif fileExt == u'.jar':
                if skipSp: continue
                if not fileStartsWith(spDir): continue
                if fileLower in badDlls and [archiveRoot,size,crc] in badDlls[fileLower]: continue
                if not checkOBSE:
                    pass
                elif fileLower in goodDlls and [archiveRoot,size,crc] in goodDlls[fileLower]: pass
                elif checkOBSE:
                    message = u'\n'.join((
                        _(u'This installer (%s) has an %s patcher JAR.'),
                        _(u'The file is %s'),
                        _(u'Such files can be malicious and hence you should be very sure you know what this file is and that it is legitimate.'),
                        _(u'Are you sure you want to install this?'),
                        )) % (archiveRoot, bush.game.sp.longName, full)
                    if fileLower in goodDlls:
                        message += _(u' You have previously chosen to install a jar by this name but with a different size, crc and or source archive name.')
                    elif fileLower in badDlls:
                        message += _(u' You have previously chosen to NOT install a jar by this name but with a different size, crc, and or source archive name - make extra sure you want to install this one before saying yes.')
                    if not balt.askYes(installersWindow,message,bush.game.sp.longName + _(u' JAR Warning')):
                        badDlls.setdefault(fileLower,[])
                        badDlls[fileLower].append([archiveRoot,size,crc])
                        continue
                    goodDlls.setdefault(fileLower,[])
                    goodDlls[fileLower].append([archiveRoot,size,crc])
            #--Noisy skips
            elif fileLower in bethFilesSkip:
                self.hasBethFiles = True
                skipDirFilesAdd(full)
                continue
            elif not hasExtraData and rootLower and rootLower not in dataDirsPlus:
                skipDirFilesAdd(full)
                continue
            elif hasExtraData and rootLower and rootLower in dataDirsMinus:
                skipDirFilesAdd(full)
                continue
            elif fileExt in skipExts:
                skipExtFilesAdd(full)
                continue
            #--Bethesda Content?
            if fileLower in bethFiles:
                self.hasBethFiles = True
            #--Esps
            if not rootLower and reModExtMatch(fileExt):
                #--Remap espms as defined by the user
                file = remaps.get(file,file)
                if file not in subList: subListAppend(file)
                pFile = GPath(file)
                espmsAdd(pFile)
                if pFile in espmNots: continue
            if skipEspmVoices and fileStartsWith(u'sound\\voice\\'):
                farPos = file.find(u'\\',12)
                if farPos > 12 and fileLower[12:farPos] in skipEspmVoices:
                    continue
            #--Remap docs, strings
            dest = file
            if rootLower in docDirs:
                dest = u'\\'.join((u'Docs',file[len(rootLower)+1:]))
            elif (renameStrings and fileStartsWith(u'strings\\') and
                  fileExt in {u'.strings',u'.dlstrings',u'.ilstrings'}):
                langSep = fileLower.rfind(u'_')
                extSep = fileLower.rfind(u'.')
                lang = fileLower[langSep+1:extSep]
                if lang != languageLower:
                    dest = u''.join((file[:langSep],u'_',language,file[extSep:]))
                    # Check to ensure not overriding an already provided
                    # language file for that language
                    key = GPath(dest)
                    if key in data_sizeCrc:
                        dest = file
            elif rootLower in dataDirsPlus:
                pass
            elif not rootLower:
                maReadMe = reReadMeMatch(file)
                if fileLower in {u'masterlist.txt',u'dlclist.txt'}:
                    pass
                elif maReadMe:
                    if not (maReadMe.group(1) or maReadMe.group(3)):
                        dest = u''.join((u'Docs\\',archiveRoot,fileExt))
                    else:
                        dest = u''.join((u'Docs\\',file))
                    self.readMe = dest
                elif fileLower == u'package.txt':
                    dest = self.packageDoc = u''.join((u'Docs\\',archiveRoot,u'.package.txt'))
                elif fileLower == u'package.jpg':
                    dest = self.packagePic = u''.join((u'Docs\\',archiveRoot,u'.package.jpg'))
                elif fileExt in docExts:
                    dest = u''.join((u'Docs\\',file))
                elif fileExt in imageExts:
                    dest = u''.join((u'Docs\\',file))
            if fileExt in commonlyEditedExts:
                trackedInfosTrack(dest)
            #--Save
            key = GPath(dest)
            data_sizeCrc[key] = (size,crc)
            dest_src[key] = full
            unSize += size
        self.unSize = unSize
        settings['bash.installers.goodDlls'], settings['bash.installers.badDlls'] = goodDlls, badDlls
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
        #--Sort file names
        def fscSortKey(fsc):
            dirFile = fsc[0].lower().rsplit(u'\\',1)
            if len(dirFile) == 1: dirFile.insert(0,u'')
            return dirFile
        fileSizeCrcs = self.fileSizeCrcs
        sortKeys = dict((x,fscSortKey(x)) for x in fileSizeCrcs)
        fileSizeCrcs.sort(key=lambda x: sortKeys[x])
        #--Find correct staring point to treat as BAIN package
        dataDirs = self.dataDirsPlus
        layout = {}
        layoutSetdefault = layout.setdefault
        for file,size,crc in fileSizeCrcs:
            if file.startswith(u'--'): continue
            fileLower = file.lower()
            frags = fileLower.split(u'\\')
            if len(frags) == 1:
                # Files in the root of the package, start there
                rootIdex = 0
                break
            else:
                dirName = frags[0]
                if dirName not in layout and layout:
                    # A second directory in the archive root, start
                    # in the root
                    rootIdex = 0
                    break
                root = layoutSetdefault(dirName,{'dirs':{},'files':False})
                for frag in frags[1:-1]:
                    root = root['dirs'].setdefault(frag,{'dirs':{},'files':False})
                root['files'] = True
        else:
            if not layout:
                rootIdex = 0
            else:
                rootStr = layout.keys()[0]
                if rootStr in dataDirs:
                    rootIdex = 0
                else:
                    root = layout[rootStr]
                    rootStr = u''.join((rootStr,u'\\'))
                    while True:
                        if root['files']:
                            # There are files in this folder, call it the starting point
                            break
                        rootDirs = root['dirs']
                        rootDirKeys = rootDirs.keys()
                        if len(rootDirKeys) == 1:
                            # Only one subfolder, see if it's either 'Data', or an accepted
                            # Data sub-folder
                            rootDirKey = rootDirKeys[0]
                            if rootDirKey in dataDirs or rootDirKey == u'data':
                                # Found suitable starting point
                                break
                            # Keep looking deeper
                            root = rootDirs[rootDirKey]
                            rootStr = u''.join((rootStr,rootDirKey,u'\\'))
                        else:
                            # Multiple folders, stop here even if it's no good
                            break
                    rootIdex = len(rootStr)
        self.fileRootIdex = rootIdex
        # fileRootIdex now points to the start in the file strings
        # to ignore
        reDataFile = self.reDataFile
        #--Type, subNames
        type = 0
        subNameSet = set()
        subNameSetAdd = subNameSet.add
        subNameSetAdd(u'')
        reDataFileSearch = reDataFile.search
        for file,size,crc in fileSizeCrcs:
            file = file[rootIdex:]
            if type != 1:
                frags = file.split(u'\\')
                nfrags = len(frags)
                #--Type 1?
                if (nfrags == 1 and reDataFileSearch(frags[0]) or
                    nfrags > 1 and frags[0].lower() in dataDirs):
                    type = 1
                    break
                #--Type 2?
                elif nfrags > 2 and not frags[0].startswith(u'--') and frags[1].lower() in dataDirs:
                    subNameSetAdd(frags[0])
                    type = 2
                elif nfrags == 2 and not frags[0].startswith(u'--') and reDataFileSearch(frags[1]):
                    subNameSetAdd(frags[0])
                    type = 2
        self.type = type
        #--SubNames, SubActives
        if type == 2:
            self.subNames = sorted(subNameSet,key=unicode.lower)
            actives = set(x for x,y in zip(self.subNames,self.subActives) if (y or x == u''))
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
        return self.status != oldStatus or self.underrides != oldUnderrides

    def install(self,archive,destFiles,data_sizeCrcDate,progress=None):
        """Install specified files to Oblivion\Data directory."""
        raise AbstractError

    def listSource(self,archive):
        """Lists the folder structure of the installer."""
        raise AbstractError

#------------------------------------------------------------------------------
class InstallerConverter(object):
    """Object representing a BAIN conversion archive, and its configuration"""
    #--Temp Files/Dirs
    def __init__(self,srcArchives=None, data=None, destArchive=None, BCFArchive=None, blockSize=None, progress=None):
        #--Persistent variables are saved in the data tank for normal operations.
        #--persistBCF is read one time from BCF.dat, and then saved in Converters.dat to keep archive extractions to a minimum
        #--persistDAT has operational variables that are saved in Converters.dat
        #--Do NOT reorder persistBCF,persistDAT,addedPersist or you will break existing BCFs!
        #--Do NOT add new attributes to persistBCF, persistDAT.
        self.persistBCF = ['srcCRCs']
        self.persistDAT = ['crc','fullPath']
        #--Any new BCF persistent variables are not allowed. Additional work needed to support backwards compat.
        #--Any new DAT persistent variables must be appended to addedPersistDAT.
        #----They must be able to handle being set to None
        self.addedPersistDAT = []
        self.srcCRCs = set()
        self.crc = None
        #--fullPath is saved in Converters.dat, but it is also updated on every refresh in case of renaming
        self.fullPath = u'BCF: Missing!'
        #--Semi-Persistent variables are loaded only when and as needed. They're always read from BCF.dat
        #--Do NOT reorder settings,volatile,addedSettings or you will break existing BCFs!
        self.settings = ['comments','espmNots','hasExtraData','isSolid','skipVoices','subActives']
        self.volatile = ['convertedFiles','dupeCount']
        #--Any new saved variables, whether they're settings or volatile must be appended to addedSettings.
        #----They must be able to handle being set to None
        self.addedSettings = ['blockSize',]
        self.convertedFiles = []
        self.dupeCount = {}
        #--Cheap init overloading...
        if data is not None:
            #--Build a BCF from scratch
            self.fullPath = dirs['converters'].join(BCFArchive)
            self.build(srcArchives, data, destArchive, BCFArchive, blockSize, progress)
            self.crc = self.fullPath.crc
        elif isinstance(srcArchives,bolt.Path):
            #--Load a BCF from file
            self.fullPath = dirs['converters'].join(srcArchives)
            self.load()
            self.crc = self.fullPath.crc
        #--Else is loading from Converters.dat, called by __setstate__

    def __getstate__(self):
        """Used by pickler to save object state. Used for Converters.dat"""
        return tuple(map(self.__getattribute__, self.persistBCF + self.persistDAT + self.addedPersistDAT))

    def __setstate__(self,values):
        """Used by unpickler to recreate object. Used for Converters.dat"""
        self.__init__()
        map(self.__setattr__,self.persistBCF + self.persistDAT + self.addedPersistDAT, values)

    def load(self,fullLoad=False):
        """Loads BCF.dat. Called once when a BCF is first installed, during a fullRefresh, and when the BCF is applied"""
        if not self.fullPath.exists(): raise StateError(u"\nLoading %s:\nBCF doesn't exist." % self.fullPath.s)
        with self.fullPath.unicodeSafe() as path:
            # Temp rename if it's name wont encode correctly
            command = ur'"%s" x "%s" BCF.dat -y -so -sccUTF-8' % (exe7z, path.s)
            try:
                ins, err = Popen(command, stdout=PIPE, stdin=PIPE, startupinfo=startupinfo).communicate()
            except:
                raise StateError(u"\nLoading %s:\nBCF extraction failed." % self.fullPath.s)
            with sio(ins) as ins:
                setter = object.__setattr__
                # translate data types to new hierarchy
                class _Translator:
                    def __init__(self, streamToWrap):
                        self._stream = streamToWrap
                    def read(self, numBytes):
                        return self._translate(self._stream.read(numBytes))
                    def readline(self):
                        return self._translate(self._stream.readline())
                    def _translate(self, s):
                        return re.sub(u'^(bolt|bosh)$', ur'bash.\1', s,flags=re.U)
                translator = _Translator(ins)
                map(self.__setattr__, self.persistBCF, cPickle.load(translator))
                if fullLoad:
                    map(self.__setattr__, self.settings + self.volatile + self.addedSettings, cPickle.load(translator))

    def save(self, destInstaller):
        #--Dump settings into BCF.dat
        try:
            result = 0
            with Installer.getTempDir().join(u'BCF.dat').open('wb') as f:
                cPickle.dump(tuple(map(self.__getattribute__, self.persistBCF)), f,-1)
                cPickle.dump(tuple(map(self.__getattribute__, self.settings + self.volatile + self.addedSettings)), f,-1)
                result = f.close()
        except Exception as e:
            raise StateError(u'Error creating BCF.dat:\nError: %s' % e)
        finally:
            if result:
                raise StateError(u"Error creating BCF.dat:\nError Code: %s" % result)

    def apply(self,destArchive,crc_installer,progress=None,embedded=0L):
        """Applies the BCF and packages the converted archive"""
        #--Prepare by fully loading the BCF and clearing temp
        self.load(True)
        Installer.rmTempDir()
        tempDir = Installer.newTempDir()
        progress = progress if progress else bolt.Progress()
        progress(0,self.fullPath.stail+u'\n'+_(u'Extracting files...'))
        #--Extract BCF
        with self.fullPath.unicodeSafe() as tempPath:
            command = u'"%s" x "%s" -y -o"%s" -scsUTF-8 -sccUTF-8' % (exe7z,tempPath,tempDir.s)
            ins, err = Popen(command, stdout=PIPE, stdin=PIPE, startupinfo=startupinfo).communicate()
            ins = sio(ins)
            #--Error checking
            reError = re.compile(u'Error:',re.U)
            regMatch = reError.match
            errorLine = []
            for line in ins:
                line = unicode(line, 'utf8')
                if len(errorLine) or regMatch(line):
                    errorLine.append(line)
            result = ins.close()
        if result or errorLine:
            raise StateError(self.fullPath.s+u': Extraction failed:\n'+u'\n'.join(errorLine))
        #--Extract source archives
        lastStep = 0
        if embedded:
            if len(self.srcCRCs) != 1:
                raise StateError(u'Embedded BCF require multiple source archives!')
            realCRCs = self.srcCRCs
            srcCRCs = [embedded]
        else:
            srcCRCs = realCRCs = self.srcCRCs
        nextStep = step = 0.4 / len(srcCRCs)
        for srcCRC,realCRC in zip(srcCRCs,realCRCs):
            srcInstaller = crc_installer[srcCRC]
            files = srcInstaller.sortFiles([x[0] for x in srcInstaller.fileSizeCrcs])
            if not files: continue
            progress(0,srcInstaller.archive+u'\n'+_(u'Extracting files...'))
            tempCRC = srcInstaller.crc
            srcInstaller.crc = realCRC
            self.unpack(srcInstaller,files,SubProgress(progress,lastStep,nextStep))
            srcInstaller.crc = tempCRC
            lastStep = nextStep
            nextStep += step
        #--Move files around and pack them
        try:
            self.arrangeFiles(SubProgress(progress,lastStep,0.7))
        except bolt.StateError as e:
            self.hasBCF = False
        else:
            self.pack(Installer.getTempDir(),destArchive,dirs['installers'],SubProgress(progress,0.7,1.0))
            #--Lastly, apply the settings.
            #--That is done by the calling code, since it requires an InstallerArchive object to work on
        finally:
            try: tempDir.rmtree(safety=tempDir.s)
            except: pass
            Installer.rmTempDir()

    def applySettings(self,destInstaller):
        """Applies the saved settings to an Installer"""
        map(destInstaller.__setattr__, self.settings + self.addedSettings, map(self.__getattribute__, self.settings + self.addedSettings))

    def arrangeFiles(self,progress):
        """Copies and/or moves extracted files into their proper arrangement."""
        tempDir = Installer.getTempDir()
        destDir = Installer.newTempDir()
        progress(0,_(u"Moving files..."))
        progress.setFull(1+len(self.convertedFiles))
        #--Make a copy of dupeCount
        dupes = dict(self.dupeCount.iteritems())
        destJoin = destDir.join
        tempJoin = tempDir.join

        #--Move every file
        for index, (crcValue, srcDir_File, destFile) in enumerate(self.convertedFiles):
            srcDir = srcDir_File[0]
            srcFile = srcDir_File[1]
            if isinstance(srcDir,basestring):
                #--either 'BCF-Missing', or crc read from 7z l -slt
                srcFile = tempJoin(srcDir,srcFile)
            else:
                srcFile = tempJoin(u"%08X" % srcDir,srcFile)
            destFile = destJoin(destFile)
            if not srcFile.exists():
                raise StateError(u"%s: Missing source file:\n%s" % (self.fullPath.stail, srcFile.s))
            if destFile is None:
                raise StateError(u"%s: Unable to determine file destination for:\n%s" % (self.fullPath.stail, srcFile.s))
            numDupes = dupes[crcValue]
            #--Keep track of how many times the file is referenced by convertedFiles
            #--This allows files to be moved whenever possible, speeding file operations up
            if numDupes > 1:
                progress(index,_(u'Copying file...')+u'\n'+destFile.stail)
                dupes[crcValue] = numDupes - 1
                srcFile.copyTo(destFile)
            else:
                progress(index,_(u'Moving file...')+u'\n'+destFile.stail)
                srcFile.moveTo(destFile)
        #--Done with unpacked directory directory
        tempDir.rmtree(safety=tempDir.s)

    def build(self, srcArchives, data, destArchive, BCFArchive, blockSize, progress=None):
        """Builds and packages a BCF"""
        progress = progress if progress else bolt.Progress()
        #--Initialization
        Installer.rmTempDir()
        srcFiles = {}
        destFiles = []
        destInstaller = data[destArchive]
        self.missingFiles = []
        self.blockSize = blockSize
        subArchives = dict()
        srcAdd = self.srcCRCs.add
        convertedFileAppend = self.convertedFiles.append
        destFileAppend = destFiles.append
        missingFileAppend = self.missingFiles.append
        dupeGet = self.dupeCount.get
        srcGet = srcFiles.get
        subGet = subArchives.get
        lastStep = 0
        #--Get settings
        attrs = ['espmNots','hasExtraData','skipVoices','comments','subActives','isSolid']
        map(self.__setattr__, attrs, map(destInstaller.__getattribute__,attrs))
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
            tempDir = Installer.getTempDir()
            for crc in tempDir.list():
                fpath = tempDir.join(crc)
                for root,y,files in fpath.walk():
                    for file in files:
                        file = root.join(file)
                        archivedFiles[file.crc] = (crc,file.s[len(fpath)+1:])
            #--Add the extracted files to the source files list
            srcFiles.update(archivedFiles)
            Installer.rmTempDir()
        #--Make list of destination files
        for fileSizeCrc in destInstaller.fileSizeCrcs:
            fileName = fileSizeCrc[0]
            fileCRC = fileSizeCrc[2]
            destFileAppend((fileCRC, fileName))
            #--Note files that aren't in any of the source files
            if fileCRC not in srcFiles:
                missingFileAppend(fileName)
                srcFiles[fileCRC] = (u'BCF-Missing',fileName)
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
        sProgress(0,BCFArchive.s+u'\n'+_(u'Mapping files...'))
        sProgress.setFull(1+len(destFiles))
        #--Map the files
        for index, (fileCRC, fileName) in enumerate(destFiles):
            convertedFileAppend((fileCRC,srcGet(fileCRC),fileName))
            sProgress(index,BCFArchive.s+u'\n'+_(u'Mapping files...')+u'\n'+fileName)
        #--Build the BCF
        tempDir2 = Installer.newTempDir().join(u'BCF-Missing')
        if len(self.missingFiles):
            #--Unpack missing files
            Installer.rmTempDir()
            destInstaller.unpackToTemp(destArchive,self.missingFiles,SubProgress(progress,lastStep, lastStep + 0.2))
            lastStep += 0.2
            #--Move the temp dir to tempDir\BCF-Missing
            #--Work around since moveTo doesn't allow direct moving of a directory into its own subdirectory
            Installer.getTempDir().moveTo(tempDir2)
            tempDir2.moveTo(Installer.getTempDir().join(u'BCF-Missing'))
        #--Make the temp dir in case it doesn't exist
        tempDir = Installer.getTempDir()
        tempDir.makedirs()
        self.save(destInstaller)
        #--Pack the BCF
        #--BCF's need to be non-Solid since they have to have BCF.dat extracted and read from during runtime
        self.isSolid = False
        self.pack(tempDir,BCFArchive,dirs['converters'],SubProgress(progress, lastStep, 1.0))
        self.isSolid = destInstaller.isSolid

    def pack(self,srcFolder,destArchive,outDir,progress=None):
        """Creates the BAIN'ified archive and cleans up temp"""
        progress = progress if progress else bolt.Progress()
        #--Used solely for the progress bar
        length = sum([len(files) for x,y,files in os.walk(srcFolder.s)])
        #--Determine settings for 7z
        archiveType = writeExts.get(destArchive.cext)
        if not archiveType:
            #--Always fail back to using the defaultExt
            destArchive = GPath(destArchive.sbody + defaultExt).tail
            archiveType = writeExts.get(destArchive.cext)
        outFile = outDir.join(destArchive)

        if self.isSolid:
            if self.blockSize:
                solid = u'-ms=on -ms=%dm' % self.blockSize
            else:
                solid = u'-ms=on'
        else:
            solid = u'-ms=off'
        if inisettings['7zExtraCompressionArguments']:
            if u'-ms=on' in inisettings['7zExtraCompressionArguments']:
                solid = u' %s' % inisettings['7zExtraCompressionArguments']
            else: solid += u' %s' % inisettings['7zExtraCompressionArguments']

        command = u'"%s" a "%s" -t"%s" %s -y -r -o"%s" -scsUTF-8 -sccUTF-8 "%s"' % (exe7z, "%s" % outFile.temp.s, archiveType, solid, outDir.s, u"%s\\*" % srcFolder.s)

        progress(0,destArchive.s+u'\n'+_(u'Compressing files...'))
        progress.setFull(1+length)
        #--Pack the files
        ins = Popen(command, stdout=PIPE, stdin=PIPE, startupinfo=startupinfo).stdout
        #--Error checking and progress feedback
        reCompressing = re.compile(u'Compressing\s+(.+)',re.U)
        regMatch = reCompressing.match
        reError = re.compile(u'Error: (.*)',re.U)
        regErrMatch = reError.match
        errorLine = []
        index = 0
        for line in ins:
            line = unicode(line, 'utf8')
            maCompressing = regMatch(line)
            if len(errorLine) or regErrMatch(line):
                errorLine.append(line)
            if maCompressing:
                progress(index,destArchive.s+u'\n'+_(u'Compressing files...')+u'\n'+maCompressing.group(1).strip())
                index += 1
        result = ins.close()
        if result or errorLine:
            outFile.temp.remove()
            raise StateError(destArchive.s+u': Compression failed:\n'+u'\n'.join(errorLine))
        #--Finalize the file, and cleanup
        outFile.untemp()
        Installer.rmTempDir()

    def unpack(self,srcInstaller,fileNames,progress=None):
        """Recursive function: completely extracts the source installer to subTempDir.
        It does NOT clear the temp folder.  This should be done prior to calling the function.
        Each archive and sub-archive is extracted to its own sub-directory to prevent file thrashing"""
        #--Sanity check
        if not fileNames: raise ArgumentError(u"No files to extract for %s." % srcInstaller.s)
        tempDir = Installer.getTempDir()
        tempList = bolt.Path.baseTempDir().join(u'WryeBash_listfile.txt')
        #--Dump file list
        try:
            out = tempList.open('w',encoding='utf-8-sig')
            out.write(u'\n'.join(fileNames))
        finally:
            result = out.close()
            if result: raise StateError(u"Error creating file list for 7z:\nError Code: %s" % result)
            result = 0
        #--Determine settings for 7z
        installerCRC = srcInstaller.crc
        if isinstance(srcInstaller,InstallerArchive):
            srcInstaller = GPath(srcInstaller.archive)
            apath = dirs['installers'].join(srcInstaller)
        else:
            apath = srcInstaller
        subTempDir = tempDir.join(u"%08X" % installerCRC)
        if progress:
            progress(0,srcInstaller.s+u'\n'+_(u'Extracting files...'))
            progress.setFull(1+len(fileNames))
        command = u'"%s" x "%s" -y -o%s @%s -scsUTF-8 -sccUTF-8' % (exe7z, apath.s, subTempDir.s, tempList.s)
        #--Extract files
        ins = Popen(command, stdout=PIPE, stdin=PIPE, startupinfo=startupinfo).stdout
        #--Error Checking, and progress feedback
        #--Note subArchives for recursive unpacking
        subArchives = []
        reExtracting = re.compile(u'Extracting\s+(.+)',re.U)
        regMatch = reExtracting.match
        reError = re.compile(u'Error: (.*)',re.U)
        regErrMatch = reError.match
        errorLine = []
        index = 0
        for line in ins:
            maExtracting = regMatch(line)
            if len(errorLine) or regErrMatch(line):
                errorLine.append(line)
            if maExtracting:
                extracted = unicode(GPath(maExtracting.group(1).strip()), 'utf8')
                if progress:
                    progress(index,srcInstaller.s+u'\n'+_(u'Extracting files...')+u'\n'+extracted.s)
                if extracted.cext in readExts:
                    subArchives.append(subTempDir.join(extracted.s))
                index += 1
        result = ins.close()
        tempList.remove()
        # Clear ReadOnly flag if set
        cmd = ur'attrib -R "%s\*" /S /D' % subTempDir.s
        ins, err = Popen(cmd, stdout=PIPE, stdin=PIPE, startupinfo=startupinfo).communicate()
        if result or errorLine:
            raise StateError(srcInstaller.s+u': Extraction failed:\n'+u'\n'.join(errorLine))
        #--Done
        #--Recursively unpack subArchives
        if len(subArchives):
            for archive in subArchives:
                self.unpack(archive,[u'*'])

#------------------------------------------------------------------------------
class InstallerMarker(Installer):
    """Represents a marker installer entry.
    Currently only used for the '==Last==' marker"""
    __slots__ = tuple() #--No new slots

    def __init__(self,archive):
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
        oldstylefileSizeCrcs = []
        reList = re.compile(u'(Solid|Path|Size|CRC|Attributes|Method) = (.*?)(?:\r\n|\n)',re.U)
        file = size = crc = isdir = 0
        self.isSolid = False
        with archive.unicodeSafe() as tempArch:
            ins = listArchiveContents(tempArch.s)
            try:
                cumCRC = 0
                for line in ins.splitlines(True):
                    maList = reList.match(line)
                    if maList:
                        key,value = maList.groups()
                        if key == u'Solid': self.isSolid = (value[0] == u'+')
                        elif key == u'Path':
                            file = value.decode('utf8')
                        elif key == u'Size': size = int(value)
                        elif key == u'Attributes': isdir = (value[0] == u'D')
                        elif key == u'CRC' and value:
                            crc = int(value,16)
                        elif key == u'Method':
                            if file and not isdir and file != tempArch.s:
                                fileSizeCrcs.append((file,size,crc))
                                cumCRC += crc
                            file = size = crc = isdir = 0
                self.crc = cumCRC & 0xFFFFFFFFL
            except:
                deprint(u'error:',traceback=True)
                raise InstallerArchiveError(u"Unable to read archive '%s'." % archive.s)

    def unpackToTemp(self,archive,fileNames,progress=None,recurse=False):
        """Erases all files from self.tempDir and then extracts specified files
        from archive to self.tempDir.
        fileNames: File names (not paths)."""
        if not fileNames: raise ArgumentError(u'No files to extract for %s.' % archive.s)
        # expand wildcards in fileNames to get actual count of files to extract
        #--Dump file list
        with self.tempList.open('w',encoding='utf8') as out:
            out.write(u'\n'.join(fileNames))
        apath = dirs['installers'].join(archive)
        #--Ensure temp dir empty
        self.rmTempDir()
        with apath.unicodeSafe() as arch:
            args = u'"%s" -y -o%s @%s -scsUTF-8 -sccUTF-8' % (arch.s, self.getTempDir().s, self.tempList.s)
            if recurse:
                args += u' -r'
            command = u'"%s" l %s' % (exe7z, args)
            ins = Popen(command, stdout=PIPE, stdin=PIPE, startupinfo=startupinfo).stdout
            reExtracting = re.compile(ur'^Extracting\s+(.+)',re.U)
            reError = re.compile(u'^(Error:.+|.+     Data Error?|Sub items Errors:.+)',re.U)
            numFiles = 0
            errorLine = []
            for line in ins:
                line = unicode(line,'utf8')
                if len(errorLine) or reError.match(line):
                    errorLine.append(line.rstrip())
                # we'll likely get a few extra lines, but that's ok
                numFiles += 1
            if ins.close() or errorLine:
                if len(errorLine) > 10:
                    if bolt.deprintOn:
                        for line in errorLine:
                            print line
                    errorLine = [_(u'%(count)i errors.  Enable debug mode for a more verbose output.') % {'count':len(errorLine)}]
                raise StateError(u'%s: Extraction failed\n%s' % (archive.s,u'\n'.join(errorLine)))
            progress = progress or bolt.Progress()
            progress.state = 0
            progress.setFull(numFiles)
            #--Extract files
            command = u'"%s" x %s' % (exe7z, args)
            ins = Popen(command, stdout=PIPE, stdin=PIPE, startupinfo=startupinfo).stdout
            extracted = []
            index = 0
            for line in ins:
                line = unicode(line,'utf8')
#                deprint(line)
                maExtracting = reExtracting.match(line)
                if len(errorLine) or reError.match(line):
                    errorLine.append(line.rstrip())
                if maExtracting:
                    extracted.append(maExtracting.group(1).strip())
                    progress(index,archive.s+u'\n'+_(u'Extracting files...')+u'\n'+maExtracting.group(1).strip())
                    index += 1
            result = ins.close()
            self.tempList.remove()
            # Clear ReadOnly flag if set
            cmd = ur'attrib -R "%s\*" /S /D' % self.getTempDir().s
            ins, err = Popen(cmd, stdout=PIPE, stdin=PIPE, startupinfo=startupinfo).communicate()
            if result or errorLine:
                if len(errorLine) > 10:
                    if bolt.deprintOn:
                        for line in errorLine:
                            print line
                    errorLine = [_(u'%(count)i errors.  Enable debug mode for a more verbose output.') % {'count':len(errorLine)}]
                raise StateError(u'%s: Extraction failed\n%s' % (archive.s,u'\n'.join(errorLine)))
        #--Done -> don't clean out temp dir, it's going to be used soon

    def install(self,archive,destFiles,data_sizeCrcDate,progress=None):
        """Install specified files to Game\Data directory."""
        destFiles = set(destFiles)
        data_sizeCrc = self.data_sizeCrc
        dest_src = dict((x,y) for x,y in self.refreshDataSizeCrc(True).iteritems() if x in destFiles)
        if not dest_src: return 0
        #--Extract
        progress = progress if progress else bolt.Progress()
        progress(0,archive.s+u'\n'+_(u'Extracting files...'))
        self.unpackToTemp(archive,dest_src.values(),SubProgress(progress,0,0.9))
        #--Rearrange files
        progress(0.9,archive.s+u'\n'+_(u'Organizing files...'))
        unpackDir = self.getTempDir() #--returns directory used by unpackToTemp
        unpackDirJoin = unpackDir.join
        stageDir = self.newTempDir()  #--forgets the old temp dir, creates a new one
        stageDataDir = stageDir.join(u'Data')
        stageDataDirJoin = stageDataDir.join
        count = 0
        norm_ghost = Installer.getGhosted()
        norm_ghostGet = norm_ghost.get
        subprogress = SubProgress(progress,0.9,1.0)
        subprogress.setFull(max(len(dest_src),1))
        subprogressPlus = subprogress.plus
        data_sizeCrcDate_update = {}
        if lo.LoadOrderMethod == liblo.LIBLO_METHOD_TIMESTAMP:
            mtimes = set()
            mtimesAdd = mtimes.add
            def timestamps(x):
                if reModExt.search(x.s):
                    newTime = x.mtime
                    while newTime in mtimes:
                        newTime += 1
                    x.mtime = newTime
                    mtimesAdd(newTime)
        else:
            def timestamps(x):
                pass
        for dest,src in  dest_src.iteritems():
            size,crc = data_sizeCrc[dest]
            srcFull = unpackDirJoin(src)
            stageFull = stageDataDirJoin(norm_ghostGet(dest,dest))
            if srcFull.exists():
                timestamps(srcFull)
                data_sizeCrcDate_update[dest] = (size,crc,srcFull.mtime)
                count += 1
                # Move to staging directory
                srcFull.moveTo(stageFull)
                subprogressPlus()
        #--Clean up unpacked dir
        unpackDir.rmtree(safety=unpackDir.stail)
        #--Now Move
        try:
            if count:
                # TODO: Find the operation that does not properly close the Oblivion\Data dir.
                # The addition of \\Data and \\* are a kludgy fix for a bug. An operation that is sometimes executed
                # before this locks the Oblivion\Data dir (only for Oblivion, Skyrim is fine)  so it can not be opened
                # with write access. It can be reliably reproduced by deleting the Table.dat file and then trying to
                # install a mod for Oblivion.
                destDir = dirs['mods'].head + u'\\Data'
                stageDataDir += u'\\*'
                balt.shellMove(stageDataDir,destDir,progress.getParent(),False,False,False)
        finally:
            #--Clean up staging dir
            self.rmTempDir()
        #--Update Installers data
        data_sizeCrcDate.update(data_sizeCrcDate_update)
        return count

    def unpackToProject(self,archive,project,progress=None):
        """Unpacks archive to build directory."""
        progress = progress or bolt.Progress()
        files = self.sortFiles([x[0] for x in self.fileSizeCrcs])
        if not files: return 0
        #--Clear Project
        destDir = dirs['installers'].join(project)
        if destDir.exists(): destDir.rmtree(safety=u'Installers')
        #--Extract
        progress(0,project.s+u'\n'+_(u'Extracting files...'))
        self.unpackToTemp(archive,files,SubProgress(progress,0,0.9))
        #--Move
        progress(0.9,project.s+u'\n'+_(u'Moving files...'))
        count = 0
        tempDir = self.getTempDir()
        # Clear ReadOnly flag if set
        cmd = ur'attrib -R "%s\*" /S /D' % tempDir.s
        ins, err = Popen(cmd, stdout=PIPE, stdin=PIPE, startupinfo=startupinfo).communicate()
        tempDirJoin = tempDir.join
        destDirJoin = destDir.join
        for file in files:
            srcFull = tempDirJoin(file)
            destFull = destDirJoin(file)
            if srcFull.exists():
                srcFull.moveTo(destFull)
                count += 1
        self.rmTempDir()
        return count

    def listSource(self, archive):
        """Returns package structure as text."""
        #--Setup
        with sio() as out:
            log = bolt.LogFile(out)
            log.setHeader(_(u'Package Structure:'))
            log(u'[spoiler][xml]\n', False)
            reList = re.compile(u'(Solid|Path|Size|CRC|Attributes|Method) = (.*?)(?:\r\n|\n)')
            file = u''
            isdir = False
            apath = dirs['installers'].join(archive)
            with apath.unicodeSafe() as tempArch:
                ins = listArchiveContents(tempArch.s)
                #--Parse
                text = []
                for line in ins.splitlines(True):
                    maList = reList.match(line)
                    if maList:
                        key,value = maList.groups()
                        if key == u'Path':
                            file = value.decode('utf8')
                        elif key == u'Attributes':
                            isdir = (value[0] == u'D')
                            text.append((u'%s' % file, isdir))
                        elif key == u'Method':
                            file = u''
                            isdir = False
            text.sort()
            #--Output
            for line in text:
                dir = line[0]
                isdir = line[1]
                if isdir:
                    log(u'  ' * dir.count(os.sep) + os.path.split(dir)[1] + os.sep)
                else:
                    log(u'  ' * dir.count(os.sep) + os.path.split(dir)[1])
            log(u'[/xml][/spoiler]')
            return bolt.winNewLines(log.out.getvalue())

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
        destFiles = set(destFiles)
        data_sizeCrc = self.data_sizeCrc
        dest_src = dict((x,y) for x,y in self.refreshDataSizeCrc(True).iteritems() if x in destFiles)
        if not dest_src: return 0
        progress = progress if progress else bolt.Progress()
        progress.setFull(max(len(dest_src),1))
        progress(0,name.stail+u'\n'+_(u'Moving files...'))
        progressPlus = progress.plus
        #--Copy Files
        self.rmTempDir()
        stageDir = self.getTempDir()
        stageDataDir = stageDir.join(u'Data')
        stageDataDirJoin = stageDataDir.join
        norm_ghost = Installer.getGhosted()
        norm_ghostGet = norm_ghost.get
        srcDir = dirs['installers'].join(name)
        srcDirJoin = srcDir.join
        data_sizeCrcDate_update = {}
        if lo.LoadOrderMethod == liblo.LIBLO_METHOD_TIMESTAMP:
            mtimes = set()
            mtimesAdd = mtimes.add
            def timestamps(x):
                if reModExt.search(x.s):
                    newTime = x.mtime
                    while newTime in mtimes:
                        newTime += 1
                    x.mtime = newTime
                    mtimesAdd(newTime)
        else:
            def timestamps(*args):
                pass
        count = 0
        for dest,src in dest_src.iteritems():
            size,crc = data_sizeCrc[dest]
            srcFull = srcDirJoin(src)
            stageFull = stageDataDirJoin(norm_ghostGet(dest,dest))
            if srcFull.exists():
                srcFull.copyTo(stageFull)
                timestamps(stageFull)
                data_sizeCrcDate_update[dest] = (size,crc,stageFull.mtime)
                count += 1
                progressPlus()
        try:
            if count:
                destDir = dirs['mods'].head + u'\\Data'
                stageDataDir += u'\\*'
                balt.shellMove(stageDataDir,destDir,progress.getParent(),False,False,False)
        finally:
            #--Clean out staging dir
            self.rmTempDir()
        #--Update Installers data
        data_sizeCrcDate.update(data_sizeCrcDate_update)
        return count

    def syncToData(self,package,projFiles):
        """Copies specified projFiles from Oblivion\Data to project directory."""
        srcDir = dirs['mods']
        projFiles = set(projFiles)
        srcProj = tuple((x,y) for x,y in self.refreshDataSizeCrc().iteritems() if x in projFiles)
        if not srcProj: return 0,0
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
        return updated,removed

    def packToArchive(self,project,archive,isSolid,blockSize,progress=None,release=False):
        """Packs project to build directory. Release filters out development
        material from the archive"""
        progress = progress or bolt.Progress()
        length = len(self.fileSizeCrcs)
        if not length: return
        archiveType = writeExts.get(archive.cext)
        if not archiveType:
            archive = GPath(archive.sbody + defaultExt).tail
            archiveType = writeExts.get(archive.cext)
        outDir = dirs['installers']
        realOutFile = outDir.join(archive)
        outFile = outDir.join(u'bash_temp_nonunicode_name.tmp')
        num = 0
        while outFile.exists():
            outFile += unicode(num)
            num += 1
        project = outDir.join(project)
        with project.unicodeSafe() as projectDir:
            if archive.cext in noSolidExts:
                solid = u''
            else:
                if isSolid:
                    if blockSize:
                        solid = u'-ms=on -ms=%dm' % blockSize
                    else:
                        solid = u'-ms=on'
                else:
                    solid = u'-ms=off'
            if inisettings['7zExtraCompressionArguments']:
                if u'-ms=' in inisettings['7zExtraCompressionArguments']:
                    solid = u' '+inisettings['7zExtraCompressionArguments']
                else: solid += u' '+inisettings['7zExtraCompressionArguments']
            #--Dump file list
            with self.tempList.open('w',encoding='utf-8-sig') as out:
                if release:
                    out.write(u'*thumbs.db\n')
                    out.write(u'*desktop.ini\n')
                    out.write(u'--*\\')
            #--Compress
            command = u'"%s" a "%s" -t"%s" %s -y -r -o"%s" -i!"%s\\*" -x@%s -scsUTF-8 -sccUTF-8' % (exe7z, outFile.temp.s, archiveType, solid, outDir.s, projectDir.s, self.tempList.s)
            progress(0,archive.s+u'\n'+_(u'Compressing files...'))
            progress.setFull(1+length)
            ins = Popen(command, stdout=PIPE, stdin=PIPE, startupinfo=startupinfo).stdout
            reCompressing = re.compile(ur'Compressing\s+(.+)',re.U)
            regMatch = reCompressing.match
            reError = re.compile(u'Error: (.*)',re.U)
            regErrMatch = reError.match
            errorLine = []
            index = 0
            for line in ins:
                maCompressing = regMatch(line)
                if len(errorLine) or regErrMatch(line):
                    errorLine.append(unicode(line,'utf8'))
                if maCompressing:
                    progress(index,archive.s+u'\n'+_(u'Compressing files...')+u'\n%s' % unicode(maCompressing.group(1).strip(),'utf8'))
                    index += 1
            result = ins.close()
            self.tempList.remove()
            if result:
                outFile.temp.remove()
                raise StateError(archive.s+u': Compression failed:\n'+u'\n'.join(errorLine))
            outFile.untemp()
            outFile.moveTo(realOutFile)

    @staticmethod
    def createFromData(projectPath,files,progress=None):
        if not files: return
        progress = progress if progress else bolt.Progress()
        projectPath = GPath(projectPath)
        progress.setFull(len(files))
        srcJoin = dirs['mods'].join
        dstJoin = projectPath.join
        for i,file in enumerate(files):
            progress(i,file.s)
            srcJoin(file).copyTo(dstJoin(file))

    #--Omod Config ------------------------------------------------------------
    class OmodConfig:
        """Tiny little omod config class."""
        def __init__(self,name):
            self.name = name.s
            self.vMajor = 0
            self.vMinor = 1
            self.vBuild = 0
            self.author = u''
            self.email = u''
            self.website = u''
            self.abstract = u''

    def getOmodConfig(self,name):
        """Get obmm config file for project."""
        config = InstallerProject.OmodConfig(name)
        configPath = dirs['installers'].join(name,u'omod conversion data',u'config')
        if configPath.exists():
            with bolt.StructFile(configPath.s,'rb') as ins:
                ins.read(1) #--Skip first four bytes
                # OBMM can support UTF-8, so try that first, then fail back to
                config.name = _unicode(ins.readNetString(),encoding='utf-8')
                config.vMajor, = ins.unpack('i',4)
                config.vMinor, = ins.unpack('i',4)
                for attr in ('author','email','website','abstract'):
                    setattr(config,attr,_unicode(ins.readNetString(),encoding='utf-8'))
                ins.read(8) #--Skip date-time
                ins.read(1) #--Skip zip-compression
                #config['vBuild'], = ins.unpack('I',4)
        return config

    def writeOmodConfig(self,name,config):
        """Write obmm config file for project."""
        configPath = dirs['installers'].join(name,u'omod conversion data',u'config')
        configPath.head.makedirs()
        with bolt.StructFile(configPath.temp.s,'wb') as out:
            out.pack('B',4)
            out.writeNetString(config.name.encode('utf8'))
            out.pack('i',config.vMajor)
            out.pack('i',config.vMinor)
            for attr in ('author','email','website','abstract'):
                # OBMM reads it fine if in UTF-8, so we'll do that.
                out.writeNetString(getattr(config,attr).encode('utf-8'))
            out.write('\x74\x1a\x74\x67\xf2\x7a\xca\x88') #--Random date time
            out.pack('b',0) #--zip compression (will be ignored)
            out.write('\xFF\xFF\xFF\xFF')
        configPath.untemp()

    def listSource(self,archive):
        """Returns package structure as text."""
        def walkPath(dir, depth):
            for file in os.listdir(dir):
                path = os.path.join(dir, file)
            if os.path.isdir(path):
                log(u' ' * depth + file + u'\\')
                depth += 2
                walkPath(path, depth)
                depth -= 2
            else:
                log(u' ' * depth + file)
        #--Setup
        with sio() as out:
            log = bolt.LogFile(out)
            log.setHeader(_(u'Package Structure:'))
            log(u'[spoiler][xml]\n', False)
            apath = dirs['installers'].join(archive)

            walkPath(apath.s, 0)
            log(u'[/xml][/spoiler]')
            return bolt.winNewLines(log.out.getvalue())

#------------------------------------------------------------------------------
class InstallersData(bolt.TankData, DataDict):
    """Installers tank data. This is the data source for """
    status_color = {-20:'grey',-10:'red',0:'white',10:'orange',20:'yellow',30:'green'}
    type_textKey = {1:'default.text',2:'installers.text.complex'}

    def __init__(self):
        self.dir = dirs['installers']
        self.bashDir = dirs['bainData']
        #--Tank Stuff
        bolt.TankData.__init__(self,settings)
        self.tankKey = 'bash.installers'
        self.tankColumns = ['Package','Order','Modified','Size','Files']
        self.transColumns = [_(u'Package'),_(u'Order'),_(u'Modified'),_(u'Size'),_(u'Files')]
        self.title = _(u'Installers')
        #--Default Params
        self.defaultParam('columns',self.tankColumns)
        self.defaultParam('colWidths',{
            'Package':250,'Order':10,'Group':60,'Modified':60,'Size':40,'Files':20})
        self.defaultParam('colAligns',{'Order':'RIGHT','Size':'RIGHT','Files':'RIGHT','Modified':'RIGHT'})
        self.defaultParam('sashPos',550)
        #--Persistent data
        self.dictFile = PickleDict(self.bashDir.join(u'Installers.dat'))
        self.data = {}
        self.data_sizeCrcDate = {}
        self.crc_installer = {}
        self.converterFile = PickleDict(self.bashDir.join(u'Converters.dat'))
        self.srcCRC_converters = {}
        self.bcfCRC_converter = {}
        #--Volatile
        self.failedOmods = set()
        self.abnorm_sizeCrc = {} #--Normative sizeCrc, according to order of active packages
        self.bcfPath_sizeCrcDate = {}
        self.hasChanged = False
        self.loaded = False
        self.lastKey = GPath(u'==Last==')

    def addMarker(self,name):
        path = GPath(name)
        self.data[path] = InstallerMarker(path)

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
            progress(0,_(u"Loading Data..."))
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

    def getSorted(self,column,reverse,sortSpecial=True):
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
            else:
                getter = lambda x: object.__getattribute__(data[x],attr)
            items.sort(key=getter,reverse=reverse)
        #--Special sorters
        if sortSpecial:
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
        if item is None: return columns[:]
        labels,installer = [],self.data[item]
        marker = isinstance(installer, InstallerMarker)
        for column in columns:
            if column == 'Package':
                value = item.s
            elif column == 'Files':
                if not marker:
                    value = formatInteger(len(installer.fileSizeCrcs))
            else:
                value = object.__getattribute__(installer,column.lower())
                if column == 'Order':
                    value = unicode(value)
                elif marker:
                    value = u''
                elif column in ('Package','Group'):
                    pass
                elif column == 'Modified':
                    value = formatDate(value)
                elif column == 'Size':
                    if value == 0:
                        value = u'0 KB'
                    else:
                        value = formatInteger(max(value,1024)/1024)+u' KB'
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
            textKey = self.type_textKey.get(installer.type,'installers.text.invalid')
        #--Background
        backKey = (installer.skipDirFiles and 'installers.bkgd.skipped') or None
        if installer.dirty_sizeCrc:
            backKey = 'installers.bkgd.dirty'
        elif installer.underrides:
            backKey = 'installers.bkgd.outOfOrder'
        #--Icon
        iconKey = ('off','on')[installer.isActive]+'.'+self.status_color[installer.status]
        if installer.type < 0:
            iconKey = 'corrupt'
        elif isinstance(installer,InstallerProject):
            iconKey += '.dir'
        if settings['bash.installers.wizardOverlay'] and installer.hasWizard:
            iconKey += '.wiz'
        return iconKey,textKey,backKey

    def getMouseText(self,iconKey,textKey,backKey):
        """Returns mouse text to use, given the iconKey,textKey, and backKey."""
        text = ''
        if backKey == 'installers.bkgd.outOfOrder':
            text += _(u'Needs Annealing due to a change in Install Order.')
        elif backKey == 'installers.bkgd.dirty':
            text += _(u'Needs Annealing due to a change in configuration.')
        #--TODO: add mouse  mouse tips
        return text

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
        balt.shellDelete(apath,askOk=False)
        del self.data[item]

    def delete(self,items,askOk=False,dontRecycle=False):
        """Delete multiple installers.  Delete entry AND archive file itself."""
        toDelete = []
        toDeleteAppend = toDelete.append
        dirJoin = self.dir.join
        selfLastKey = self.lastKey
        for item in items:
            if item == selfLastKey: continue
            toDeleteAppend(dirJoin(item))
        #--Delete
        try:
            balt.shellDelete(toDelete,askOk=askOk,recycle=not dontRecycle)
        finally:
            for item in toDelete:
                if not item.exists():
                    del self.data[item.tail]

    def copy(self,item,destName,destDir=None):
        """Copies archive to new location."""
        if item == self.lastKey: return
        destDir = destDir or self.dir
        apath = self.dir.join(item)
        apath.copyTo(destDir.join(destName))
        if destDir == self.dir:
            self.data[destName] = installer = copy.copy(self.data[item])
            installer.isActive = False
            self.moveArchives([destName],self.data[item].order+1)
            self.refreshOrder()

    #--Refresh Functions --------------------------------------------------------
    def refreshInstallers(self,progress=None,fullRefresh=False):
        """Refresh installer data."""
        progress = progress or bolt.Progress()
        changed = False
        pending = set()
        projects = set()
        #--Current archives
        newData = {}
        for i in self.data.keys():
            if isinstance(self.data[i],InstallerMarker):
                newData[i] = self.data[i]
        installersJoin = dirs['installers'].join
        dataGet = self.data.get
        pendingAdd = pending.add
        for archive in dirs['installers'].list():
            if archive.s.lower().startswith((u'--',u'bash')): continue
            apath = installersJoin(archive)
            isdir = apath.isdir()
            if isdir: projects.add(archive)
            if (isdir and archive != dirs['converters'].stail) or archive.cext in readExts:
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
            progress(0,_(u"Scanning Packages..."))
            progressSetFull(len(subPending))
            for index,package in enumerate(sorted(subPending)):
                progress(index,_(u'Scanning Packages...')+u'\n'+package.s)
                installer = newDataGet(package)
                if not installer:
                    installer = newDataSetDefault(package,iClass(package))
                if installer.skipRefresh and isinstance(installer, InstallerProject) and not fullRefresh: continue
                apath = installersJoin(package)
                try: installer.refreshBasic(apath,SubProgress(progress,index,index+1))
                except InstallerArchiveError:
                    installer.type = -1
        self.data = newData
        self.crc_installer = dict((x.crc,x) for x in self.data.values() if isinstance(x, InstallerArchive))
        #--Apply embedded BCFs
        if settings['bash.installers.autoApplyEmbeddedBCFs']:
            changed |= self.applyEmbeddedBCFs(progress=progress)
        return changed

    def extractOmodsNeeded(self):
        """Returns true if .omod files are present, requiring extraction."""
        for file in dirs['installers'].list():
            if file.cext == u'.omod' and file not in self.failedOmods: return True
        return False

    def embeddedBCFsExist(self):
        """Return true if any InstallerArchive's have an embedded BCF file in them"""
        for file in self.data:
            installer = self.data[file]
            if installer.hasBCF and isinstance(installer,InstallerArchive):
                return True
        return False

    def applyEmbeddedBCFs(self,installers=None,destArchives=None,progress=bolt.Progress()):
        if not installers:
            installers = (self.data[x] for x in self.data)
            installers = [x for x in installers if x.hasBCF and isinstance(x,InstallerArchive)]
        if not installers: return False
        if not destArchives:
            destArchives = [GPath(x.archive) for x in installers]
        progress.setFull(max(len(installers),1))
        for i,installer in enumerate(installers):
            name = GPath(installer.archive)
            progress(i,name.s)
            #--Extract the embedded BCF and move it to the Converters folder
            Installer.rmTempDir()
            installer.unpackToTemp(name,[installer.hasBCF],progress)
            srcBcfFile = Installer.getTempDir().join(installer.hasBCF)
            bcfFile = dirs['converters'].join(u'temp-'+srcBcfFile.stail)
            srcBcfFile.moveTo(bcfFile)
            Installer.rmTempDir()
            #--Creat the converter, apply it
            destArchive = destArchives[i]
            converter = InstallerConverter(bcfFile.tail)
            converter.apply(destArchive,self.crc_installer,bolt.SubProgress(progress,0.0,0.99),installer.crc)
            #--Add the new archive to Bash
            if destArchive not in self:
                self[destArchive] = InstallerArchive(destArchive)
            #--Apply settings to the new archive
            iArchive = self[destArchive]
            converter.applySettings(iArchive)
            #--RefreshUI
            pArchive = dirs['installers'].join(destArchive)
            iArchive.refreshed = False
            iArchive.refreshBasic(pArchive,SubProgress(progress,0.99,1.0),True)
            if iArchive.hasBCF:
                # If applying the BCF created a new archive with an embedded BCF,
                # ignore the embedded BCF for now, so we don't end up in an infinite
                # loop
                iArchive.hasBCF = False
            bcfFile.remove()
        self.refresh(what='I')
        return True

    def refreshInstallersNeeded(self):
        """Returns true if refreshInstallers is necessary. (Point is to skip use
        of progress dialog when possible."""
        installers = set([])
        installersJoin = dirs['installers'].join
        dataGet = self.data.get
        installersAdd = installers.add
        for item in dirs['installers'].list():
            apath = installersJoin(item)
            if item.s.lower().startswith((u'bash',u'--')): continue
            if settings['bash.installers.autoRefreshProjects']:
                if (apath.isdir() and item != u'Bash' and item != dirs['converters'].stail) or (apath.isfile() and item.cext in readExts):
                    installer = dataGet(item)
                    if installer and installer.skipRefresh:
                        continue
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
        if settings['bash.installers.autoApplyEmbeddedBCFs'] and self.embeddedBCFsExist():
            return True
        elif settings['bash.installers.autoRefreshProjects']:
            return installers != set(x for x,y in self.data.iteritems() if not isinstance(y,InstallerMarker) and not (isinstance(y,InstallerProject) and y.skipRefresh))
        else:
            return installers != set(x for x,y in self.data.iteritems() if isinstance(y,InstallerArchive))

    def refreshConvertersNeeded(self):
        """Returns true if refreshConverters is necessary. (Point is to skip use
        of progress dialog when possible."""
        self.pruneConverters()
        archives = set([])
        scanned = set([])
        convertersJoin = dirs['converters'].join
        converterGet = self.bcfPath_sizeCrcDate.get
        bcfPath_sizeCrcDate = self.bcfPath_sizeCrcDate
        archivesAdd = archives.add
        scannedAdd = scanned.add
        for archive in dirs['converters'].list():
            apath = convertersJoin(archive)
            if apath.isfile() and self.validConverterName(archive):
                scannedAdd(apath)
        if len(scanned) != len(self.bcfPath_sizeCrcDate):
            return True
        for archive in scanned:
            size,crc,modified = converterGet(archive,(None,None,None))
            if crc is None or (size,modified) != (archive.size,archive.mtime):
                return True
            archivesAdd(archive)
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

    def validConverterName(self,path):
        return path.cext in defaultExt and (path.csbody[-4:] == u'-bcf' or u'-bcf-' in path.csbody)

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
            if self.validConverterName(archive):
                size,crc,modified = self.bcfPath_sizeCrcDate.get(bcfPath,(None,None,None))
                if crc is None or (size,modified) != (bcfPath.size,bcfPath.mtime):
                    crc = bcfPath.crc
                    (size,modified) = (bcfPath.size,bcfPath.mtime)
                    if crc in bcfCRC_converter and bcfPath != bcfCRC_converter[crc].fullPath:
                        self.bcfPath_sizeCrcDate.pop(bcfPath,None)
                        if bcfCRC_converter[crc].fullPath.exists():
                            bcfPath.moveTo(dirs['dupeBCFs'].join(bcfPath.tail))
                        continue
                self.bcfPath_sizeCrcDate[bcfPath] = (size, crc, modified)
                if fullRefresh or crc not in bcfCRC_converter:
                    pending.add(archive)
                else:
                    newData[crc] = bcfCRC_converter[crc]
                    newData[crc].fullPath = bcfPath
        #--New/update crcs?
        self.bcfCRC_converter = newData
        pendingChanged = False
        if bool(pending):
            progress(0,_(u"Scanning Converters..."))
            progress.setFull(len(pending))
            for index,archive in enumerate(sorted(pending)):
                progress(index,_(u'Scanning Converter...')+u'\n'+archive.s)
                pendingChanged |= self.addConverter(archive)
        changed = pendingChanged or (len(newData) != len(bcfCRC_converter))
        self.pruneConverters()
        return changed

    def pruneConverters(self):
        """Remove any converters that no longer exist."""
        bcfPath_sizeCrcDate = self.bcfPath_sizeCrcDate
        for bcfPath in bcfPath_sizeCrcDate.keys():
            if not bcfPath.exists() or bcfPath.isdir():
                self.removeConverter(bcfPath)

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
            try:
                newConverter = InstallerConverter(converter)
            except:
                fullPath = dirs['converters'].join(converter)
                fullPath.moveTo(dirs['corruptBCFs'].join(converter.tail))
                del self.bcfPath_sizeCrcDate[fullPath]
                return False
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
        return True

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
            size,crc,modified = self.bcfPath_sizeCrcDate.pop(bcfPath,(None,None,None))
            if crc is not None:
                oldConverter = self.bcfCRC_converter.pop(crc,None)
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
            elif i.head.cs == u'ini tweaks':
                iniInfos.table.setItem(i.tail, 'installer', value)

    def install(self,archives,progress=None,last=False,override=True):
        """Install selected archives.
        what:
            'MISSING': only missing files.
            Otherwise: all (unmasked) files.
        """
        progress = progress or bolt.Progress()
        tweaksCreated = set()
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
                for file in destFiles:
                    if file.cext in (u'.ini',u'.cfg') and not file.head.cs == u'ini tweaks':
                        oldCrc = self.data_sizeCrcDate.get(file,(None,None,None))[1]
                        newCrc = installer.data_sizeCrc.get(file,(None,None))[1]
                        if oldCrc is not None and newCrc is not None:
                            if newCrc != oldCrc:
                                target = dirs['mods'].join(file)
                                # Creat a copy of the old one
                                baseName = dirs['tweaks'].join(u'%s, ~Old Settings [%s].ini' % (target.sbody, target.sbody))
                                oldIni = baseName
                                num = 1
                                while oldIni.exists():
                                    if num == 1:
                                        suffix = u' - Copy'
                                    else:
                                        suffix = u' - Copy (%i)' % num
                                    num += 1
                                    oldIni = baseName.head.join(baseName.sbody+suffix+baseName.ext)
                                target.copyTo(oldIni)
                                tweaksCreated.add((oldIni,target))
                installer.install(archive,destFiles,self.data_sizeCrcDate,SubProgress(progress,index,index+1))
                InstallersData.updateTable(destFiles, archive.s)
            installer.isActive = True
            mask |= set(installer.data_sizeCrc)
        if tweaksCreated:
            # Edit the tweaks
            for (oldIni,target) in tweaksCreated:
                iniFile = BestIniFile(target)
                currSection = None
                lines = []
                for (text,section,setting,value,status,lineNo,deleted) in iniFile.getTweakFileLines(oldIni):
                    if status in (10,-10):
                        # A setting that exists in both INI's, but is different,
                        # or a setting that doesn't exist in the new INI.
                        if section == u']set[' or section == u']setGS[':
                            lines.append(text+u'\n')
                        elif section != currSection:
                            section = currSection
                            if not section: continue
                            lines.append(u'\n[%s]\n' % section)
                        elif not section:
                            continue
                        else:
                            lines.append(text+u'\n')
                # Re-write the tweak
                with oldIni.open('w') as file:
                    file.write(u'; INI Tweak created by Wrye Bash, using settings from old file.\n\n')
                    file.writelines(lines)
        self.refreshStatus()
        return tweaksCreated

    def removeFiles(self, removes, progress=None):
        """Performs the actual deletion of files and updating of internal data.clear
           used by 'uninstall' and 'anneal'."""
        data = self.data
        data_sizeCrcDatePop = self.data_sizeCrcDate.pop
        modsDirJoin = dirs['mods'].join
        emptyDirs = set()
        emptyDirsAdd = emptyDirs.add
        emptyDirsClear = emptyDirs.clear
        removedFiles = set()
        removedFilesAdd = removedFiles.add
        reModExtSearch = reModExt.search
        removedPlugins = set()
        removedPluginsAdd = removedPlugins.add
        #--Construct list of files to delete
        for file in removes:
            path = modsDirJoin(file)
            if path.exists():
                removedFilesAdd(path)
            ghostPath = path + u'.ghost'
            if ghostPath.exists():
                removedFilesAdd(ghostPath)
            if reModExtSearch(file.s):
                removedPluginsAdd(file)
                removedPluginsAdd(file + u'.ghost')
            emptyDirsAdd(path.head)
        #--Now determine which directories will be empty
        allRemoves = set(removedFiles)
        allRemovesAdd = allRemoves.add
        while emptyDirs:
            testDirs = set(emptyDirs)
            emptyDirsClear()
            for dir in sorted(testDirs, key=len, reverse=True):
                # Sorting by length, descending, ensure we always
                # are processing the deepest directories first
                items = set(map(dir.join, dir.list()))
                remaining = items - allRemoves
                if not remaining:
                    # If there are no items in this directory that will not
                    # be removed, this directory is also safe to remove.
                    removedFiles -= items
                    removedFilesAdd(dir)
                    allRemovesAdd(dir)
                    emptyDirsAdd(dir.head)
        #--Do the deletion
        if removedFiles:
            parent = progress.getParent() if progress else None
            balt.shellDelete(removedFiles, parent, False, False)
        #--Update InstallersData
        InstallersData.updateTable(removes, u'')
        for file in removes:
            data_sizeCrcDatePop(file, None)
        #--Remove mods from load order
        modInfos.plugins.removeMods(removedPlugins, True)

    def uninstall(self,unArchives,progress=None):
        """Uninstall selected archives."""
        if unArchives == 'ALL': unArchives = self.data
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
        #--Remove files, update InstallersData, update load order
        self.removeFiles(removes, progress)
        #--De-activate
        for archive in unArchives:
            data[archive].isActive = False
        #--Restore files
        restoreArchives = sorted(set(restores.itervalues()),key=getArchiveOrder,reverse=True)
        if settings['bash.installers.autoAnneal'] and restoreArchives:
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
        progress = progress if progress else bolt.Progress()
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
        #--Remove files, update InstallersData, update load order
        self.removeFiles(removes, progress)
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

    def clean(self,progress):
        data = self.data
        getArchiveOrder = lambda x: data[x].order
        installed = []
        for package in sorted(data,key=getArchiveOrder,reverse=True):
            installer = data[package]
            if installer.isActive:
                installed += installer.data_sizeCrc
        keepFiles = set(installed)
        keepFiles.update((GPath(f) for f in bush.game.allBethFiles))
        keepFiles.update((GPath(f) for f in bush.game.wryeBashDataFiles))
        keepFiles.update((GPath(f) for f in bush.game.ignoreDataFiles))
        data_sizeCrcDate = self.data_sizeCrcDate
        removes = set(data_sizeCrcDate) - keepFiles
        destDir = dirs['bainData'].join(u'Data Folder Contents (%s)' %(datetime.datetime.now().strftime(u'%d-%m-%Y %H%M.%S')))
        emptyDirs = set()
        skipPrefixes = [os.path.normcase(skipDir)+os.sep for skipDir in bush.game.wryeBashDataDirs]
        skipPrefixes.extend([os.path.normcase(skipDir)+os.sep for skipDir in bush.game.ignoreDataDirs])
        skipPrefixes.extend([os.path.normcase(skipPrefix) for skipPrefix in bush.game.ignoreDataFilePrefixes])
        for file in removes:
            # don't remove files in Wrye Bash-related directories
            skip = False
            for skipPrefix in skipPrefixes:
                if file.cs.startswith(skipPrefix):
                    skip = True
                    break
            if skip: continue
            path = dirs['mods'].join(file)
            try:
                if path.exists():
                    path.moveTo(destDir.join(file))
                else:
                    ghost = GPath(path.s+u'.ghost')
                    if ghost.exists():
                        ghost.moveTo(destDir.join(file))
            except:
                # It's not imperative that files get moved, so if errors happen, just ignore them.
                # Would could put a deprint in here so that when debug mode is enabled we at least
                # see that some files failed for some reason.
                pass
            data_sizeCrcDate.pop(file,None)
            emptyDirs.add(path.head)
        for emptyDir in emptyDirs:
            if emptyDir.isdir() and not emptyDir.list():
                emptyDir.removedirs()

    def getConflictReport(self,srcInstaller,mode):
        """Returns report of overrides for specified package for display on conflicts tab.
        mode: OVER: Overrides; UNDER: Underrides"""
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
        showBSA = settings['bash.installers.conflictsReport.showBSAConflicts']
        if not mismatched: return u''
        src_sizeCrc = srcInstaller.data_sizeCrc
        packConflicts = []
        bsaConflicts = []
        getArchiveOrder =  lambda x: data[x].order
        getBSAOrder = lambda x: list(modInfos.ordered).index(x[1].root + ".esp")
        # Calculate bsa conflicts
        if showBSA:
            # Create list of active BSA files in srcInstaller
            srcFiles = srcInstaller.data_sizeCrc
            srcBSAFiles = [x for x in srcFiles.keys() if x.ext == ".bsa"]
#            print("Ordered: {}".format(modInfos.ordered))
            activeSrcBSAFiles = [x for x in srcBSAFiles if x.root + ".esp" in modInfos.ordered]
            try:
                bsas = [(x, libbsa.BSAHandle(dirs['mods'].join(x.s))) for x in activeSrcBSAFiles]
#                print("BSA Paths: {}".format(bsas))
            except:
                deprint(u'   Error loading BSA srcFiles: ',activeSrcBSAFiles,traceback=True)
            # Create list of all assets in BSA files for srcInstaller
            srcBSAContents = []
            for x,y in bsas: srcBSAContents.extend(y.GetAssets('.+'))
#            print("srcBSAContents: {}".format(srcBSAContents))

            # Create a list of all active BSA Files except the ones in srcInstaller
            activeBSAFiles = []
            for package in self.data:
                installer = data[package]
                if installer.order == srcOrder: continue
                if not installer.isActive: continue
#                print("Current Package: {}".format(package))
                BSAFiles = [x for x in installer.data_sizeCrc if x.ext == ".bsa"]
                activeBSAFiles.extend([(package, x, libbsa.BSAHandle(dirs['mods'].join(x.s))) for x in BSAFiles if x.root + ".esp" in modInfos.ordered])
            # Calculate all conflicts and save them in bsaConflicts
#            print("Active BSA Files: {}".format(activeBSAFiles))
            for package, bsaPath, bsaHandle in sorted(activeBSAFiles,key=getBSAOrder):
                curAssets = bsaHandle.GetAssets('.+')
#                print("Current Assets: {}".format(curAssets))
                curConflicts = Installer.sortFiles([x.s for x in curAssets if x in srcBSAContents])
#                print("Current Conflicts: {}".format(curConflicts))
                if curConflicts: bsaConflicts.append((package, bsaPath, curConflicts))
#        print("BSA Conflicts: {}".format(bsaConflicts))
        # Calculate esp/esm conflicts
        for package in sorted(self.data,key=getArchiveOrder):
            installer = data[package]
            if installer.order == srcOrder: continue
            if not showInactive and not installer.isActive: continue
            if not showLower and installer.order < srcOrder: continue
            curConflicts = Installer.sortFiles([x.s for x,y in installer.data_sizeCrc.iteritems()
                if x in mismatched and y != src_sizeCrc[x]])
            if curConflicts: packConflicts.append((installer,package.s,curConflicts))
        #--Unknowns
        isHigher = -1
        # Generate report
        with sio() as buff:
            # Print BSA conflicts
            if showBSA:
                buff.write(u'= %s %s\n\n' % (_(u'BSA Conflicts'),u'='*40))
                for package, bsa, srcFiles in bsaConflicts:
                    order = getBSAOrder((None,bsa,None))
                    srcBSAOrder = getBSAOrder((None,activeSrcBSAFiles[0],None))
                    # Print partitions
                    if showLower and (order > srcBSAOrder) != isHigher:
                        isHigher = (order > srcBSAOrder)
                        buff.write(u'= %s %s\n' % ((_(u'Lower'),_(u'Higher'))[isHigher],u'='*40))
                    buff.write(u'==%d== %s : %s\n' % (order, package, bsa))
                    # Print files
                    for file in srcFiles:
                        buff.write(u'%s \n' % file)
                    buff.write(u'\n')
            isHigher = -1
            if showBSA: buff.write(u'= %s %s\n\n' % (_(u'Loose File Conflicts'),u'='*36))
            # Print loose file conflicts
            for installer,package,srcFiles in packConflicts:
                order = installer.order
                # Print partitions
                if showLower and (order > srcOrder) != isHigher:
                    isHigher = (order > srcOrder)
                    buff.write(u'= %s %s\n' % ((_(u'Lower'),_(u'Higher'))[isHigher],u'='*40))
                buff.write(u'==%d== %s\n'% (order,package))
                # Print srcFiles
                for file in srcFiles:
                    oldName = installer.getEspmName(file)
                    buff.write(oldName)
                    if oldName != file:
                        buff.write(u' -> ')
                        buff.write(file)
                    buff.write(u'\n')
                buff.write(u'\n')
            report = buff.getvalue()
        if not conflictsMode and not report and not srcInstaller.isActive:
            report = _(u"No Underrides. Mod is not completely un-installed.")
        return report

    def getPackageList(self,showInactive=True):
        """Returns package list as text."""
        #--Setup
        with sio() as out:
            log = bolt.LogFile(out)
            log.setHeader(_(u'Bain Packages:'))
            orderKey = lambda x: self.data[x].order
            allPackages = sorted(self.data,key=orderKey)
            #--List
            modIndex,header = 0, None
            log(u'[spoiler][xml]\n',False)
            for package in allPackages:
                prefix = u'%03d' % self.data[package].order
                if isinstance(self.data[package],InstallerMarker):
                    log(u'%s - %s' % (prefix,package.s))
                elif self.data[package].isActive:
                    log(u'++ %s - %s (%08X) (Installed)' % (prefix,package.s,self.data[package].crc))
                elif showInactive:
                    log(u'-- %s - %s (%08X) (Not Installed)' % (prefix,package.s,self.data[package].crc))
            log(u'[/xml][/spoiler]')
            return bolt.winNewLines(log.out.getvalue())

#------------------------------------------------------------------------------
class ModDetails:
    """Details data for a mods file. Similar to TesCS Details view."""
    def __init__(self,modInfo=None,progress=None):
        self.group_records = {} #--group_records[group] = [(fid0,eid0),(fid1,eid1),...]

    def readFromMod(self,modInfo,progress=None):
        """Extracts details from mod file."""
        def getRecordReader(ins,flags,size):
            """Decompress record data as needed."""
            if not MreRecord._flags1(flags).compressed:
                return ins,ins.tell()+size
            else:
                import zlib
                sizeCheck, = struct.unpack('I',ins.read(4))
                decomp = zlib.decompress(ins.read(size-4))
                if len(decomp) != sizeCheck:
                    raise ModError(self.inName,
                        u'Mis-sized compressed data. Expected %d, got %d.' % (size,len(decomp)))
                reader = ModReader(modInfo.name,sio(decomp))
                return reader,sizeCheck
        progress = progress or bolt.Progress()
        group_records = self.group_records = {}
        records = group_records[bush.game.MreHeader.classType] = []
        with ModReader(modInfo.name,modInfo.getPath().open('rb')) as ins:
            while not ins.atEnd():
                header = ins.unpackRecHeader()
                recType,size = header.recType,header.size
                if recType == 'GRUP':
                    label = header.label
                    progress(1.0*ins.tell()/modInfo.size,_(u"Scanning: ")+label)
                    records = group_records.setdefault(label,[])
                    if label in ('CELL','WRLD','DIAL'):
                        ins.seek(size-header.__class__.size,1)
                elif recType != 'GRUP':
                    eid = u''
                    nextRecord = ins.tell() + size
                    recs,endRecs = getRecordReader(ins,header.flags1,size)
                    while recs.tell() < endRecs:
                        (type,size) = recs.unpackSubHeader()
                        if type == 'EDID':
                            eid = recs.readString(size)
                            break
                        recs.seek(size,1)
                    records.append((header.fid,eid))
                    ins.seek(nextRecord)
        del group_records[bush.game.MreHeader.classType]

#------------------------------------------------------------------------------
class ModGroups:
    """Groups for mods with functions for importing/exporting from/to text file."""
    @staticmethod
    def filter(mods):
        """Returns non-group header mods."""
        return [x for x in mods if not reGroupHeader.match(x.s)]

    def __init__(self):
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
        with bolt.CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) >= 2 and reModExt.search(fields[0]):
                    mod,group = fields[:2]
                    mod_group[GPath(mod)] = group

    def writeToText(self,textPath):
        """Exports eids to specified text file."""
        textPath = GPath(textPath)
        mod_group = self.mod_group
        rowFormat = u'"%s","%s"\n'
        with textPath.open('w',encoding='utf-8-sig') as out:
            out.write(rowFormat % (_(u"Mod"),_(u"Group")))
            for mod in sorted(mod_group):
                out.write(rowFormat % (mod.s,mod_group[mod]))

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
            self.eid = self.pcName = u'generic'
            self.fggs_p = self.fgts_p = '\x00'*4*50
            self.fgga_p = '\x00'*4*30
            self.unused2 = null2
            self.health = self.unused3 = self.baseSpell = self.fatigue = self.level = 0
            self.skills = self.attributes = self.iclass = None
            self.factions = []
            self.modifiers = []
            self.spells = []

        def getGenderName(self):
            return self.gender and u'Female' or u'Male'

        def getRaceName(self):
            return bush.game.raceNames.get(self.race,_(u'Unknown'))

        def convertRace(self,fromRace,toRace):
            """Converts face from one race to another while preserving structure, etc."""
            for attr,num in (('fggs_p',50),('fgga_p',30),('fgts_p',50)):
                format = unicode(num)+u'f'
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
            raise SaveFileError(saveName,u'Failed to find pcName in PC ACHR record.')
        namePos2 = data.find(pcName,namePos+1)
        if namePos2 != -1:
            raise SaveFileError(saveName,
                u'Uncertain about position of face data, probably because '
                u'player character name is too short. Try renaming player '
                u'character in save game.')
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
        for attr in ('attributes','skills','health','unused2'):
            value = getattr(npc,attr)
            if value is not None:
                setattr(face,attr,value)
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
        namePos = PCFaces.save_getNamePos(saveFile.fileInfo.name,data,_encode(saveFile.pcName))
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
            raise StateError(u"Record %08X not found in %s." % (targetid,saveFile.fileInfo.name.s))
        if npc.recType != 'NPC_':
            raise StateError(u"Record %08X in %s is not an NPC." % (targetid,saveFile.fileInfo.name.s))
        #--Update masters
        for fid in (face.race, face.eye, face.hair):
            if not fid: continue
            maxMaster = len(face.masters)-1
            mod = getModIndex(fid)
            master = face.masters[min(mod,maxMaster)]
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
        if changeRecord is None: return
        fid,recType,recFlags,version,data = changeRecord
        npc = SreNPC(recFlags,data)
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
        #--Update masters
        for fid in (face.race, face.eye, face.hair, face.iclass):
            if not fid: continue
            maxMaster = len(face.masters)-1
            mod = getModIndex(fid)
            master = face.masters[min(mod,maxMaster)]
            if master not in saveFile.masters:
                saveFile.masters.append(master)
        masterMap = MasterMap(face.masters,saveFile.masters)

        #--Player ACHR
        #--Buffer for modified record data
        buff = sio()
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
        namePos = PCFaces.save_getNamePos(saveFile.fileInfo.name,oldData,_encode(saveFile.pcName))
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
        namePos = PCFaces.save_getNamePos(saveInfo.name,data,_encode(saveFile.pcName))
        raceRef,hairRef = struct.unpack('2I',data[namePos-22:namePos-14])
        if hairRef != 0: return False
        raceForm = raceRef and saveFile.fids[raceRef]
        gender, = struct.unpack('B',data[namePos-2])
        if gender:
            hairForm = bush.game.raceHairFemale.get(raceForm,0x1da83)
        else:
            hairForm = bush.game.raceHairMale.get(raceForm,0x90475)
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
        loadFactory = LoadFactory(False,MreRecord.type_class['NPC_'])
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
        loadFactory = LoadFactory(False,MreRecord.type_class['RACE'])
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
        loadFactory = LoadFactory(True,MreRecord.type_class['NPC_'])
        modFile = ModFile(modInfo,loadFactory)
        if modInfo.getPath().exists():
            modFile.load(True)
        #--Tes4
        tes4 = modFile.tes4
        if not tes4.author:
            tes4.author = u'[wb]'
        if not tes4.description:
            tes4.description = _(u'Face dump from save game.')
        if modInfos.masterName not in tes4.masters:
            tes4.masters.append(modInfos.masterName)
        masterMap = MasterMap(face.masters,tes4.masters+[modInfo.name])
        #--Eid
        npcEids = set([record.eid for record in modFile.NPC_.records])
        eidForm = u''.join((u"sg", bush.game.raceShortNames.get(face.race,u'Unk'),
            (face.gender and u'a' or u'u'), re.sub(ur'\W',u'',face.pcName),u'%02d'))
        count,eid = 0, eidForm % 0
        while eid in npcEids:
            count += 1
            eid = eidForm % count
        #--NPC
        npcid = genFid(len(tes4.masters),tes4.getNextObject())
        npc = MreRecord.type_class['NPC_'](ModReader.recHeader('NPC_',0,0x40000,npcid,0))
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
        with ModReader(self.modInfo.name,path.open('rb')) as ins:
            with path.temp.open('wb') as  out:
                def copy(size,back=False):
                    buff = ins.read(size)
                    out.write(buff)
                def copyPrev(size):
                    ins.seek(-size,1)
                    buff = ins.read(size)
                    out.write(buff)
                while not ins.atEnd():
                    progress(ins.tell())
                    header = ins.unpackRecHeader()
                    type,size = header.recType,header.size
                    #(type,size,str0,fid,uint2) = ins.unpackRecHeader()
                    copyPrev(header.__class__.size)
                    if type == 'GRUP':
                        if header.groupType != 0: #--Ignore sub-groups
                            pass
                        elif header.label not in ('CELL','WRLD'):
                            copy(size-header.__class__.size)
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
                                    fixedCells.add(header.fid)
                                out.write(struct.pack('=12s2f2l2f',color,near,far,rotXY,rotZ,fade,clip))
                    #--Non-Cells
                    else:
                        copy(size)
        #--Done
        if fixedCells:
            self.modInfo.makeBackup()
            path.untemp()
            self.modInfo.setmtime()
        else:
            path.temp.remove()

#------------------------------------------------------------------------------
class ModCleaner:
    """Class for cleaning ITM and UDR edits from mods.
       ITM detection requires CBash to work."""
    UDR     = 0x01  # Deleted references
    ITM     = 0x02  # Identical to master records
    FOG     = 0x04  # Nvidia Fog Fix
    ALL = UDR|ITM|FOG
    DEFAULT = UDR|ITM

    class UdrInfo(object):
        # UDR info
        # (UDR fid, UDR Type, UDR Parent Fid, UDR Parent Type, UDR Parent Parent Fid, UDR Parent Block, UDR Paren SubBlock)
        def __init__(self,fid,Type=None,parentFid=None,parentEid=u'',
                     parentType=None,parentParentFid=None,parentParentEid=u'',
                     pos=None):
            if isinstance(fid,ObBaseRecord):
                # CBash - passed in the record instance
                record = fid
                parent = record.Parent
                self.fid = record.fid
                self.type = record._Type
                self.parentFid = parent.fid
                self.parentEid = parent.eid
                if parent.IsInterior:
                    self.parentType = 0
                    self.parentParentFid = None
                    self.parentParentEid = u''
                    self.pos = None
                else:
                    self.parentType = 1
                    self.parentParentFid = parent.Parent.fid
                    self.parentParentEid = parent.Parent.eid
                    self.pos = (record.posX,record.posY)
            else:
                self.fid = fid
                self.type = Type
                self.parentFid = parentFid
                self.parentEid = parentEid
                self.parentType = parentType
                self.pos = pos
                self.parentParentFid = parentParentFid
                self.parentParentEid = parentParentEid

        def __cmp__(self,other):
            return cmp(self.fid,other.fid)

    def __init__(self,modInfo):
        self.modInfo = modInfo
        self.itm = set()    # Fids for Identical To Master records
        self.udr = set()    # Fids for Deleted Reference records
        self.fog = set()    # Fids for Cells needing the Nvidia Fog Fix

    def scan(self,what=ALL,progress=bolt.Progress(),detailed=False):
        """Scan this mod for dirty edits.
           return (UDR,ITM,FogFix)"""
        udr,itm,fog = ModCleaner.scan_Many([self.modInfo],what,progress,detailed)[0]
        if what & ModCleaner.UDR:
            self.udr = udr
        if what & ModCleaner.ITM:
            self.itm = itm
        if what & ModCleaner.FOG:
            self.fog = fog
        return udr,itm,fog

    @staticmethod
    def scan_Many(modInfos,what=DEFAULT,progress=bolt.Progress(),detailed=False):
        """Scan multiple mods for dirty edits"""
        if len(modInfos) == 0: return []
        if not settings['bash.CBashEnabled']:
            return ModCleaner._scan_Python(modInfos,what,progress,detailed)
        else:
            return ModCleaner._scan_CBash(modInfos,what,progress)

    def clean(self,what=UDR|FOG,progress=bolt.Progress(),reScan=False):
        """reScan:
             True: perform scans before cleaning
             False: only perform scans if itm/udr is empty
             """
        ModCleaner.clean_Many([self],what,progress,reScan)

    @staticmethod
    def clean_Many(cleaners,what,progress=bolt.Progress(),reScan=False):
        """Accepts either a list of ModInfo's or a list of ModCleaner's"""
        if isinstance(cleaners[0],ModInfos):
            reScan = True
            cleaners = [ModCleaner(x) for x in cleaners]
        if settings['bash.CBashEnabled']:
            #--CBash
            #--Scan?
            if reScan:
                ret = ModCleaner._scan_CBash([x.modInfo for x in cleaners],what,progress)
                for i,cleaner in enumerate(cleaners):
                    udr,itm,fog = ret[i]
                    if what & ModCleaner.UDR:
                        cleaner.udr = udr
                    if what & ModCleaner.ITM:
                        cleaner.itm = itm
                    if what & ModCleaner.FOG:
                        cleaner.fog = fog
            #--Clean
            ModCleaner._clean_CBash(cleaners,what,progress)
        else:
            ModCleaner._clean_Python(cleaners,what,progress)

    @staticmethod
    def _scan_CBash(modInfos,what,progress):
        """Scan multiple mods for problems"""
        if what & ModCleaner.ALL:
            # There are scans to do
            doUDR = bool(what & ModCleaner.UDR)
            doITM = bool(what & ModCleaner.ITM)
            doFog = bool(what & ModCleaner.FOG)
            # If there are more than 255 mods, we have to break it up into
            # smaller groups.  We'll do groups of 200 for now, to allow for
            # added files due to implicitly loading masters.
            modInfos = [x.modInfo if isinstance(x,ModCleaner) else x for x in modInfos]
            numMods = len(modInfos)
            if numMods > 255:
                ModsPerGroup = 200
                numGroups = numMods / ModsPerGroup
                if numMods % ModsPerGroup:
                    numGroups += 1
            else:
                ModsPerGroup = 255
                numGroups = 1
            progress.setFull(numGroups)
            ret = []
            for i in range(numGroups):
                #--Load
                progress(i,_(u'Loading...'))
                groupModInfos = modInfos[i*ModsPerGroup:(i+1)*ModsPerGroup]
                with ObCollection(ModsPath=dirs['mods'].s) as Current:
                    for mod in groupModInfos:
                        if len(mod.masterNames) == 0: continue
                        path = mod.getPath()
                        Current.addMod(path.stail)
                    Current.load()
                    #--Scan
                    subprogress1 = SubProgress(progress,i,i+1)
                    subprogress1.setFull(max(len(groupModInfos),1))
                    for j,modInfo in enumerate(groupModInfos):
                        subprogress1(j,_(u'Scanning...') + u'\n' + modInfo.name.s)
                        udr = set()
                        itm = set()
                        fog = set()
                        if len(modInfo.masterNames) > 0:
                            path = modInfo.getPath()
                            modFile = Current.LookupModFile(path.stail)
                            if modFile:
                                udrRecords = []
                                fogRecords = []
                                if doUDR:
                                    udrRecords += modFile.ACRES + modFile.ACHRS + modFile.REFRS
                                if doFog:
                                    fogRecords += modFile.CELL
                                if doITM:
                                    itm |= set([x.fid for x in modFile.GetRecordsIdenticalToMaster()])
                                total = len(udrRecords) + len(fogRecords)
                                subprogress2 = SubProgress(subprogress1,j,j+1)
                                subprogress2.setFull(max(total,1))
                                #--Scan UDR
                                for record in udrRecords:
                                    subprogress2.plus()
                                    if record.IsDeleted:
                                        udr.add(ModCleaner.UdrInfo(record))
                                #--Scan fog
                                for record in fogRecords:
                                    subprogress2.plus()
                                    if not (record.fogNear or record.fogFar or record.fogClip):
                                        fog.add(record.fid)
                                modFile.Unload()
                        ret.append((udr,itm,fog))
            return ret
        else:
            return [(set(),set(),set()) for x in range(len(modInfos))]

    @staticmethod
    def _scan_Python(modInfos,what,progress,detailed=False):
        if what & (ModCleaner.UDR|ModCleaner.FOG):
            # Python can't do ITM scanning
            doUDR = what & ModCleaner.UDR
            doFog = what & ModCleaner.FOG
            progress.setFull(max(len(modInfos),1))
            ret = []
            for i,modInfo in enumerate(modInfos):
                progress(i,_(u'Scanning...') + u'\n' + modInfo.name.s)
                itm = set()
                fog = set()
                #--UDR stuff
                udr = {}
                parents_to_scan = {}
                if len(modInfo.masterNames) > 0:
                    subprogress = SubProgress(progress,i,i+1)
                    if detailed:
                        subprogress.setFull(max(modInfo.size*2,1))
                    else:
                        subprogress.setFull(max(modInfo.size,1))
                    #--File stream
                    path = modInfo.getPath()
                    #--Scan
                    parentType = None
                    parentFid = None
                    parentParentFid = None
                    # Location (Interior = #, Exteror = (X,Y)
                    parentBlock = None
                    parentSubBlock = None
                    with ModReader(modInfo.name,path.open('rb')) as ins:
                        try:
                            insAtEnd = ins.atEnd
                            insTell = ins.tell
                            insUnpackRecHeader = ins.unpackRecHeader
                            insUnpackSubHeader = ins.unpackSubHeader
                            insRead = ins.read
                            insUnpack = ins.unpack
                            headerSize = ins.recHeader.size
                            structUnpack = struct.unpack
                            structPack = struct.pack
                            while not insAtEnd():
                                subprogress(insTell())
                                header = insUnpackRecHeader()
                                type,size = header.recType,header.size
                                #(type,size,flags,fid,uint2) = ins.unpackRecHeader()
                                if type == 'GRUP':
                                    groupType = header.groupType
                                    if groupType == 0 and header.label not in {'CELL','WRLD'}:
                                        # Skip Tops except for WRLD and CELL groups
                                        insRead(size-headerSize)
                                    elif detailed:
                                        if groupType == 1:
                                            # World Children
                                            parentParentFid = header.label
                                            parentType = 1 # Exterior Cell
                                            parentFid = None
                                        elif groupType == 2:
                                            # Interior Cell Block
                                            parentType = 0 # Interior Cell
                                            parentParentFid = parentFid = None
                                        elif groupType in {6,8,9,10}:
                                            # Cell Children, Cell Persisten Children,
                                            # Cell Temporary Children, Cell VWD Children
                                            parentFid = header.label
                                        else: # 3,4,5,7 - Topic Children
                                            pass
                                else:
                                    if doUDR and header.flags1 & 0x20 and type in (
                                        'ACRE',               #--Oblivion only
                                        'ACHR','REFR',        #--Both
                                        'NAVM','PHZD','PGRE', #--Skyrim only
                                        ):
                                        if not detailed:
                                            udr[header.fid] = ModCleaner.UdrInfo(header.fid)
                                        else:
                                            fid = header.fid
                                            udr[fid] = ModCleaner.UdrInfo(fid,type,parentFid,u'',parentType,parentParentFid,u'',None)
                                            parents_to_scan.setdefault(parentFid,set())
                                            parents_to_scan[parentFid].add(fid)
                                            if parentParentFid:
                                                parents_to_scan.setdefault(parentParentFid,set())
                                                parents_to_scan[parentParentFid].add(fid)
                                    if doFog and type == 'CELL':
                                        nextRecord = insTell() + size
                                        while insTell() < nextRecord:
                                            (nextType,nextSize) = insUnpackSubHeader()
                                            if nextType != 'XCLL':
                                                insRead(nextSize)
                                            else:
                                                color,near,far,rotXY,rotZ,fade,clip = insUnpack('=12s2f2l2f',nextSize,'CELL.XCLL')
                                                if not (near or far or clip):
                                                    fog.add(header.fid)
                                    else:
                                        insRead(size)
                            if parents_to_scan:
                                # Detailed info - need to re-scan for CELL and WRLD infomation
                                ins.seek(0)
                                baseSize = modInfo.size
                                while not insAtEnd():
                                    subprogress(baseSize+insTell())
                                    header = insUnpackRecHeader()
                                    type,size = header.recType,header.size
                                    if type == 'GRUP':
                                        if header.groupType == 0 and header.label not in {'CELL','WRLD'}:
                                            insRead(size-headerSize)
                                    else:
                                        fid = header.fid
                                        if fid in parents_to_scan:
                                            record = MreRecord(header,ins,True)
                                            record.loadSubrecords()
                                            eid = u''
                                            x,y = (0,0)
                                            for subrec in record.subrecords:
                                                if subrec.subType == 'EDID':
                                                    eid = _unicode(subrec.data)
                                                elif subrec.subType == 'XCLC':
                                                    pos = structUnpack('=2i',subrec.data[:8])
                                            for udrFid in parents_to_scan[fid]:
                                                if type == 'CELL':
                                                    udr[udrFid].parentEid = eid
                                                    if udr[udrFid].parentType == 1:
                                                        # Exterior Cell, calculate position
                                                        udr[udrFid].pos = pos
                                                elif type == 'WRLD':
                                                    udr[udrFid].parentParentEid = eid
                                        else:
                                            insRead(size)
                        except bolt.CancelError:
                            raise
                        except:
                            deprint(u'Error scanning %s, file read pos: %i:\n' % (modInfo.name.s,ins.tell()),traceback=True)
                            udr = itm = fog = None
                    #--Done
                ret.append((udr.values() if udr is not None else None,itm,fog))
            return ret
        else:
            return [(set(),set(),set()) for x in xrange(len(modInfos))]

    @staticmethod
    def _clean_CBash(cleaners,what,progress):
        if what & ModCleaner.ALL:
            # There are scans to do
            doUDR = bool(what & ModCleaner.UDR)
            doITM = bool(what & ModCleaner.ITM)
            doFog = bool(what & ModCleaner.FOG)
            # If there are more than 255 mods, we have to break it up into
            # smaller groups.  We'll do groups of 200 for now, to allow for
            # added files due to implicitly loading masters.
            numMods = len(cleaners)
            if numMods > 255:
                ModsPerGroup = 200
                numGroups = numMods / ModsPerGroup
                if numMods % ModsPerGroup:
                    numGroups += 1
            else:
                ModsPerGroup = 255
                numGroups = 1
            progress.setFull(numGroups)
            for i in range(numGroups):
                #--Load
                progress(i,_(u'Loading...'))
                groupCleaners = cleaners[i*ModsPerGroup:(i+1)*ModsPerGroup]
                with ObCollection(ModsPath=dirs['mods'].s) as Current:
                    for cleaner in groupCleaners:
                        if len(cleaner.modInfo.masterNames) == 0: continue
                        path = cleaner.modInfo.getPath()
                        Current.addMod(path.stail)
                    Current.load()
                    #--Clean
                    subprogress1 = SubProgress(progress,i,i+1)
                    subprogress1.setFull(max(len(groupCleaners),1))
                    for j,cleaner in enumerate(groupCleaners):
                        subprogress1(j,_(u'Cleaning...') + u'\n' + cleaner.modInfo.name.s)
                        path = cleaner.modInfo.getPath()
                        modFile = Current.LookupModFile(path.stail)
                        changed = False
                        if modFile:
                            total = sum([len(cleaner.udr)*doUDR,len(cleaner.fog)*doFog,len(cleaner.itm)*doITM])
                            subprogress2 = SubProgress(subprogress1,j,j+1)
                            subprogress2.setFull(max(total,1))
                            if doUDR:
                                for udr in cleaner.udr:
                                    fid = udr.fid
                                    subprogress2.plus()
                                    record = modFile.LookupRecord(fid)
                                    if record and record._Type in ('ACRE','ACHR','REFR') and record.IsDeleted:
                                        changed = True
                                        record.IsDeleted = False
                                        record.IsIgnored = True
                            if doFog:
                                for fid in cleaner.fog:
                                    subprogress2.plus()
                                    record = modFile.LookupRecord(fid)
                                    if record and record._Type == 'CELL':
                                        if not (record.fogNear or record.fogFar or record.fogClip):
                                            record.fogNear = 0.0001
                                            changed = True
                            if doITM:
                                for fid in cleaner.itm:
                                    subprogress2.plus()
                                    record = modFile.LookupRecord(fid)
                                    if record:
                                        record.DeleteRecord()
                                        changed = True
                            #--Save
                            if changed:
                                modFile.save(False)

    @staticmethod
    def _clean_Python(cleaners,what,progress):
        if what & (ModCleaner.UDR|ModCleaner.FOG):
            doUDR = what & ModCleaner.UDR
            doFog = what & ModCleaner.FOG
            progress.setFull(max(len(cleaners),1))
            #--Clean
            for i,cleaner in enumerate(cleaners):
                progress(i,_(u'Cleaning...')+u'\n'+cleaner.modInfo.name.s)
                subprogress = SubProgress(progress,i,i+1)
                subprogress.setFull(max(cleaner.modInfo.size,1))
                #--File stream
                path = cleaner.modInfo.getPath()
                #--Scan & clean
                with ModReader(cleaner.modInfo.name,path.open('rb')) as ins:
                    with path.temp.open('wb') as out:
                        def copy(size):
                            out.write(ins.read(size))
                        def copyPrev(size):
                            ins.seek(-size,1)
                            out.write(ins.read(size))
                        changed = False
                        while not ins.atEnd():
                            subprogress(ins.tell())
                            header = ins.unpackRecHeader()
                            type,size = header.recType,header.size
                            #(type,size,flags,fid,uint2) = ins.unpackRecHeader()
                            if type == 'GRUP':
                                if header.groupType != 0:
                                    pass
                                elif header.label not in ('CELL','WRLD'):
                                    copy(size-header.__class__.size)
                            else:
                                if doUDR and header.flags1 & 0x20 and type in {
                                    'ACRE',               #--Oblivion only
                                    'ACHR','REFR',        #--Both
                                    'NAVM','PGRE','PHZD', #--Skyrim only
                                    }:
                                    header.flags1 = (header.flags1 & ~0x20) | 0x1000
                                    out.seek(-header.__class__.size,1)
                                    out.write(header.pack())
                                    change = True
                                if doFog and type == 'CELL':
                                    nextRecord = ins.tell() + size
                                    while ins.tell() < nextRecord:
                                        subprogress(ins.tell())
                                        (nextType,nextSize) = ins.unpackSubHeader()
                                        copyPrev(6)
                                        if nextType != 'XCLL':
                                            copy(nextSize)
                                        else:
                                            color,near,far,rotXY,rotZ,fade,clip = ins.unpack('=12s2f2l2f',size,'CELL.XCLL')
                                            if not (near or far or clip):
                                                near = 0.0001
                                                changed = True
                                            out.write(struct.pack('=12s2f2l2f',color,near,far,rotXY,rotZ,fade,clip))
                                else:
                                    copy(size)
                #--Save
                if changed:
                    cleaner.modInfo.makeBackup()
                    try:
                        path.untemp()
                    except WindowsError, werr:
                        if werr.winerror != 32: raise
                        while balt.askYes(None,(_(u'Bash encountered an error when saving %s.')
                                                + u'\n\n' +
                                                _(u'The file is in use by another process such as TES4Edit.')
                                                + u'\n' +
                                                _(u'Please close the other program that is accessing %s.')
                                                + u'\n\n' +
                                                _(u'Try again?')
                                                ) % (path.stail,path.stail),path.stail+_(u' - Save Error')):
                            try:
                                path.untemp()
                            except WindowsError,werr:
                                continue
                            break
                        else:
                            raise
                    cleaner.modInfo.setmtime()
                else:
                    path.temp.remove()

#------------------------------------------------------------------------------
class SaveSpells:
    """Player spells of a savegame."""

    def __init__(self,saveInfo):
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
        loadFactory = LoadFactory(False,MreRecord.type_class['SPEL'])
        modFile = ModFile(modInfo,loadFactory)
        try: modFile.load(True)
        except ModError, err:
            deprint(_(u'skipped mod due to read error (%s)') % err)
            return
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

#------------------------------------------------------------------------------
class SaveEnchantments:
    """Player enchantments of a savegame."""

    def __init__(self,saveInfo):
        self.saveInfo = saveInfo
        self.saveFile = None
        self.createdEnchantments = []

    def load(self,progress=None):
        """Loads savegame and and extracts created enchantments from it."""
        progress = progress or bolt.Progress()
        saveFile = self.saveFile = SaveFile(self.saveInfo)
        saveFile.load(SubProgress(progress,0,0.4))
        #--Extract created enchantments
        createdEnchantments = self.createdEnchantments
        saveName = self.saveInfo.name
        progress(progress.full-1,saveName.s)
        for index,record in enumerate(saveFile.created):
            if record.recType == 'ENCH':
                record = record.getTypeCopy()
                record.getSize() #--Since type copy makes it changed.
                saveFile.created[index] = record
                self.createdEnchantments.append((index,record))

    def setCastWhenUsedEnchantmentNumberOfUses(self,uses):
        """Sets Cast When Used Enchantment number of uses (via editing the enchat cost)."""
        count = 0
        for (index, record) in self.createdEnchantments:
            if record.itemType in [1,2]:
                if uses == 0:
                    if record.enchantCost == 0: continue
                    record.enchantCost = 0
                else:
                    if record.enchantCost == max(record.chargeAmount/uses,1): continue
                    record.enchantCost = max(record.chargeAmount/uses,1)
                record.setChanged()
                record.getSize()
                count += 1
        self.saveFile.safeSave()

class Save_NPCEdits:
    """General editing of NPCs/player in savegame."""

    def __init__(self,saveInfo):
        self.saveInfo = saveInfo
        self.saveFile = SaveFile(saveInfo)

    def renamePlayer(self,newName):
        """rename the player in  a save file."""
        self.saveInfo.header.pcName = newName
        saveFile = self.saveFile
        saveFile.load()
        (fid,recType,recFlags,version,data) = saveFile.getRecord(7)
        npc = SreNPC(recFlags,data)
        npc.full = _encode(newName)
        saveFile.pcName = newName
        saveFile.setRecord(npc.getTuple(fid,version))
        saveFile.safeSave()

# Patchers 1 ------------------------------------------------------------------
#------------------------------------------------------------------------------
class PatchFile(ModFile):
    """Defines and executes patcher configuration."""
    #--Class
    mergeClasses = tuple()

    @staticmethod
    def initGameData():
        """Needs to be called after bush.game has been set"""
        PatchFile.mergeClasses = bush.game.mergeClasses

    @staticmethod
    def generateNextBashedPatch(wxParent=None):
        """Attempts to create a new bashed patch, numbered from 0 to 9.  If a lowered number bashed patch exists,
           will create the next in the sequence.  if wxParent is not None and we are unable to create a patch,
           displays a dialog error"""
        for num in xrange(10):
            modName = GPath(u'Bashed Patch, %d.esp' % num)
            if modName not in modInfos:
                patchInfo = ModInfo(modInfos.dir,GPath(modName))
                patchInfo.mtime = max([time.time()]+[info.mtime for info in modInfos.values()])
                patchFile = ModFile(patchInfo)
                patchFile.tes4.author = u'BASHED PATCH'
                patchFile.safeSave()
                modInfos.refresh()
                return modName
        else:
            if wxParent is not None:
                balt.showWarning(wxParent, u"Unable to create new bashed patch: 10 bashed patches already exist!")
        return None

    @staticmethod
    def modIsMergeable(modInfo,verbose=True):
        """Returns True or error message indicating whether specified mod is mergeable."""
        reasons = u''

        if modInfo.isEsm():
            if not verbose: return False
            reasons += u'\n.    '+_(u'Is esm.')
        #--Bashed Patch
        if modInfo.header.author == u"BASHED PATCH":
            if not verbose: return False
            reasons += u'\n.    '+_(u'Is Bashed Patch.')

        #--Bsa / voice?
        if modInfo.isMod() and tuple(modInfo.hasResources()) != (False,False):
            if not verbose: return False
            hasBsa, hasVoices = modInfo.hasResources()
            if hasBsa:
                reasons += u'\n.    '+_(u'Has BSA archive.')
            if hasVoices:
                reasons += u'\n.    '+_(u'Has associated voice directory (Sound\\Voice\\%s).') % modInfo.name.s

        #--Missing Strings Files?
        if modInfo.isMissingStrings():
            if not verbose: return False
            reasons += u'\n.    '+_(u'Missing String Translation Files (Strings\\%s_%s.STRINGS, etc).') % (
                modInfo.name.sbody, oblivionIni.getSetting('General','sLanguage',u'English'))

        #-- Check to make sure NoMerge tag not in tags - if in tags don't show up as mergeable.
        if u'NoMerge' in modInfos[GPath(modInfo.name.s)].getBashTags():
            if not verbose: return False
            reasons += u'\n.    '+_(u"Has 'NoMerge' tag.")
        #--Load test
        mergeTypes = set([recClass.classType for recClass in PatchFile.mergeClasses])
        modFile = ModFile(modInfo,LoadFactory(False,*mergeTypes))
        try:
            modFile.load(True,loadStrings=False)
        except ModError, error:
            if not verbose: return False
            reasons += u'\n.    %s.' % error
        #--Skipped over types?
        if modFile.topsSkipped:
            if not verbose: return False
            reasons += u'\n.    '+_(u'Unsupported types: ')+u', '.join(sorted(modFile.topsSkipped))+u'.'
        #--Empty mod
        elif not modFile.tops:
            if not verbose: return False
            reasons += u'\n.    '+ u'Empty mod.'
        #--New record
        lenMasters = len(modFile.tes4.masters)
        newblocks = []
        for type,block in modFile.tops.iteritems():
            for record in block.getActiveRecords():
                if record.fid >> 24 >= lenMasters:
                    if record.flags1.deleted: continue #if new records exist but are deleted just skip em.
                    if not verbose: return False
                    newblocks.append(type)
                    break
        if newblocks: reasons += u'\n.    '+_(u'New record(s) in block(s): ')+u', '.join(sorted(newblocks))+u'.'
        dependent = [curModInfo.name.s for curModInfo in modInfos.data.values() if curModInfo.header.author != u'BASHED PATCH' if GPath(modInfo.name.s) in curModInfo.header.masters]
        if dependent:
            if not verbose: return False
            reasons += u'\n.    '+_(u'Is a master of mod(s): ')+u', '.join(sorted(dependent))+u'.'
        if reasons: return reasons
        return True

    #--Instance
    def __init__(self,modInfo,patchers):
        """Initialization."""
        ModFile.__init__(self,modInfo,None)
        self.tes4.author = u'BASHED PATCH'
        self.tes4.masters = [modInfos.masterName]
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
        self.patcher_mod_skipcount = {}
        #--Config
        self.bodyTags = 'ARGHTCCPBS' #--Default bodytags
        #--Mods
        loadMods = [name for name in modInfos.ordered if bush.fullLoadOrder[name] < bush.fullLoadOrder[PatchFile.patchName]]
        if not loadMods:
            raise BoltError(u"No active mods dated before the bashed patch")
        self.setMods(loadMods, [])
        for patcher in self.patchers:
            patcher.initPatchFile(self,loadMods)

    def setMods(self,loadMods=None,mergeMods=None):
        """Sets mod lists and sets."""
        if loadMods is not None: self.loadMods = loadMods
        if mergeMods is not None: self.mergeMods = mergeMods
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
            progress(index,_(u'Preparing')+u'\n'+patcher.getName())
            patcher.initData(SubProgress(progress,index))
        progress(progress.full,_(u'Patchers prepared.'))

    def initFactories(self,progress):
        """Gets load factories."""
        progress(0,_(u"Processing."))
        def updateClasses(type_classes,newClasses):
            if not newClasses: return
            for item in newClasses:
                if not isinstance(item,basestring):
                    type_classes[item.classType] = item
                elif item not in type_classes:
                    type_classes[item] = item
        readClasses = {}
        writeClasses = {}
        updateClasses(readClasses, bush.game.readClasses)
        updateClasses(writeClasses, bush.game.writeClasses)
        for patcher in self.patchers:
            updateClasses(readClasses, (MreRecord.type_class[x] for x in patcher.getReadClasses()))
            updateClasses(writeClasses, (MreRecord.type_class[x] for x in patcher.getWriteClasses()))
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
            bashTags = modInfos[modName].getBashTags()
            if modName in self.loadMods and u'Filter' in bashTags:
                self.unFilteredMods.append(modName)
            try:
                loadFactory = (self.readFactory,self.mergeFactory)[modName in self.mergeSet]
                progress(index,modName.s+u'\n'+_(u'Loading...'))
                modInfo = modInfos[GPath(modName)]
                modFile = ModFile(modInfo,loadFactory)
                modFile.load(True,SubProgress(progress,index,index+0.5))
            except ModError as e:
                deprint('load error:', traceback=True)
                self.loadErrorMods.append((modName,e))
                continue
            try:
                #--Error checks
                if 'WRLD' in modFile.tops and modFile.WRLD.orphansSkipped:
                    self.worldOrphanMods.append(modName)
                if 'SCPT' in modFile.tops and modName != u'Oblivion.esm':
                    gls = modFile.SCPT.getRecord(0x00025811)
                    if gls and gls.compiledSize == 4 and gls.lastIndex == 0:
                        self.compiledAllMods.append(modName)
                pstate = index+0.5
                isMerged = modName in self.mergeSet
                doFilter = isMerged and u'Filter' in bashTags
                #--iiMode is a hack to support Item Interchange. Actual key used is InventOnly.
                iiMode = isMerged and bool({u'InventOnly', u'IIM'} & bashTags)
                if isMerged:
                    progress(pstate,modName.s+u'\n'+_(u'Merging...'))
                    self.mergeModFile(modFile,nullProgress,doFilter,iiMode)
                else:
                    progress(pstate,modName.s+u'\n'+_(u'Scanning...'))
                    self.scanModFile(modFile,nullProgress)
                for patcher in sorted(self.patchers,key=attrgetter('scanOrder')):
                    if iiMode and not patcher.iiMode: continue
                    progress(pstate,u'%s\n%s' % (modName.s,patcher.name))
                    patcher.scanModFile(modFile,nullProgress)
                # Clip max version at 1.0.  See explanation in the CBash version as to why.
                self.tes4.version = min(max(modFile.tes4.version, self.tes4.version),max(bush.game.esp.validHeaderVersions))
            except bolt.CancelError:
                raise
            except:
                print _(u"MERGE/SCAN ERROR:"),modName.s
                raise
        progress(progress.full,_(u'Load mods scanned.'))

    def mergeModFile(self,modFile,progress,doFilter,iiMode):
        """Copies contents of modFile into self."""
        mergeIds = self.mergeIds
        mergeIdsAdd = mergeIds.add
        loadSet = self.loadSet
        modFile.convertToLongFids()
        badForm = (GPath(u"Oblivion.esm"),0xA31D) #--DarkPCB record
        selfLoadFactoryRecTypes = self.loadFactory.recTypes
        selfMergeFactoryType_class = self.mergeFactory.type_class
        selfReadFactoryAddClass = self.readFactory.addClass
        selfLoadFactoryAddClass = self.loadFactory.addClass
        nullFid = (GPath(modInfos.masterName),0)
        for blockType,block in modFile.tops.iteritems():
            iiSkipMerge = iiMode and blockType not in ('LVLC','LVLI','LVSP')
            #--Make sure block type is also in read and write factories
            if blockType not in selfLoadFactoryRecTypes:
                recClass = selfMergeFactoryType_class[blockType]
                selfReadFactoryAddClass(recClass)
                selfLoadFactoryAddClass(recClass)
            patchBlock = getattr(self,blockType)
            patchBlockSetRecord = patchBlock.setRecord
            if not isinstance(patchBlock,MobObjects):
                raise BoltError(u"Merge unsupported for type: "+blockType)
            filtered = []
            filteredAppend = filtered.append
            loadSetIssuperset = loadSet.issuperset
            for record in block.getActiveRecords():
                fid = record.fid
                if fid == badForm: continue
                #--Include this record?
                if doFilter:
                    record.mergeFilter(loadSet)
                    masters = MasterSet()
                    record.updateMasters(masters)
                    if not loadSetIssuperset(masters):
                        continue
                filteredAppend(record)
                if iiSkipMerge: continue
                record = record.getTypeCopy()
                patchBlockSetRecord(record)
                if record.isKeyedByEid and fid == nullFid:
                    mergeIdsAdd(record.eid)
                else:
                    mergeIdsAdd(fid)
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
        log.setHeader(u'= '+self.fileInfo.name.s+u' '+u'='*30+u'#',True)
        log(u"{{CONTENTS=1}}")
        #--Load Mods and error mods
        log.setHeader(u'= '+_(u'Overview'),True)
        log.setHeader(u'=== '+_(u'Date/Time'))
        log(u'* '+formatDate(time.time()))
        log(u'* '+_(u'Elapsed Time: ') + 'TIMEPLACEHOLDER')
        if self.patcher_mod_skipcount:
            log.setHeader(u'=== '+_(u'Skipped Imports'))
            log(_(u"The following import patchers skipped records because the imported record required a missing or non-active mod to work properly. If this was not intentional, rebuild the patch after either deactivating the imported mods listed below or activating the missing mod(s)."))
            for patcher, mod_skipcount in self.patcher_mod_skipcount.iteritems():
                log (u'* '+_(u'%s skipped %d records:') % (patcher,sum(mod_skipcount.values())))
                for mod, skipcount in mod_skipcount.iteritems():
                    log (u'  * '+_(u'The imported mod, %s, skipped %d records.') % (mod,skipcount))
        if self.unFilteredMods:
            log.setHeader(u'=== '+_(u'Unfiltered Mods'))
            log(_(u"The following mods were active when the patch was built. For the mods to work properly, you should deactivate the mods and then rebuild the patch with the mods [[http://wrye.ufrealms.net/Wrye%20Bash.html#MergeFiltering|Merged]] in."))
            for mod in self.unFilteredMods: log (u'* '+mod.s)
        if self.loadErrorMods:
            log.setHeader(u'=== '+_(u'Load Error Mods'))
            log(_(u"The following mods had load errors and were skipped while building the patch. Most likely this problem is due to a badly formatted mod. For more info, see [[http://www.uesp.net/wiki/Tes4Mod:Wrye_Bash/Bashed_Patch#Error_Messages|Bashed Patch: Error Messages]]."))
            for (mod,e) in self.loadErrorMods: log (u'* '+mod.s+u': %s'%e)
        if self.worldOrphanMods:
            log.setHeader(u'=== '+_(u'World Orphans'))
            log(_(u"The following mods had orphaned world groups, which were skipped. This is not a major problem, but you might want to use Bash's [[http://wrye.ufrealms.net/Wrye%20Bash.html#RemoveWorldOrphans|Remove World Orphans]] command to repair the mods."))
            for mod in self.worldOrphanMods: log (u'* '+mod.s)
        if self.compiledAllMods:
            log.setHeader(u'=== '+_(u'Compiled All'))
            log(_(u"The following mods have an empty compiled version of genericLoreScript. This is usually a sign that the mod author did a __compile all__ while editing scripts. This may interfere with the behavior of other mods that intentionally modify scripts from Oblivion.esm. (E.g. Cobl and Unofficial Oblivion Patch.) You can use Bash's [[http://wrye.ufrealms.net/Wrye%20Bash.html#DecompileAll|Decompile All]] command to repair the mods."))
            for mod in self.compiledAllMods: log (u'* '+mod.s)
        log.setHeader(u'=== '+_(u'Active Mods'),True)
        for name in self.allMods:
            version = modInfos.getVersion(name)
            if name in self.loadMods:
                message = u'* %02X ' % (self.loadMods.index(name),)
            else:
                message = u'* ++ '
            if version:
                message += _(u'%s  [Version %s]') % (name.s,version)
            else:
                message += name.s
            log(message)
        #--Load Mods and error mods
        if self.aliases:
            log.setHeader(u'= '+_(u'Mod Aliases'))
            for key,value in sorted(self.aliases.iteritems()):
                log(u'* %s >> %s' % (key.s,value.s))
        #--Patchers
        self.keepIds |= self.mergeIds
        subProgress = SubProgress(progress,0,0.9,len(self.patchers))
        for index,patcher in enumerate(sorted(self.patchers,key=attrgetter('editOrder'))):
            subProgress(index,_(u'Completing')+u'\n%s...' % patcher.getName())
            patcher.buildPatch(log,SubProgress(subProgress,index))
        #--Trim records
        progress(0.9,_(u'Completing')+u'\n'+_(u'Trimming records...'))
        for block in self.tops.values():
            block.keepRecords(self.keepIds)
        progress(0.95,_(u'Completing')+u'\n'+_(u'Converting fids...'))
        #--Convert masters to short fids
        self.tes4.masters = self.getMastersUsed()
        self.convertToShortFids()
        progress(1.0,_(u"Compiled."))
        #--Description
        numRecords = sum([x.getNumRecords(False) for x in self.tops.values()])
        self.tes4.description = (_(u'Updated: ')+formatDate(time.time())
                                 + u'\n\n' +
                                 _(u'Records Changed: %d') % numRecords
                                 )

class CBash_PatchFile(ObModFile):
    """Defines and executes patcher configuration."""

    #--Class
    @staticmethod
    def configIsCBash(patchConfigs):
        for key in patchConfigs:
            if 'CBash' in key:
                return True
        return False

    @staticmethod
    def modIsMergeableNoLoad(modInfo,verbose):
        reasons = []

        if modInfo.isEsm():
            if not verbose: return False
            reasons.append(u'\n.    '+_(u'Is esm.'))
        #--Bashed Patch
        if modInfo.header.author == u'BASHED PATCH':
            if not verbose: return False
            reasons.append(u'\n.    '+_(u'Is Bashed Patch.'))

        #--Bsa / voice?
        if modInfo.isMod() and tuple(modInfo.hasResources()) != (False,False):
            if not verbose: return False
            hasBsa, hasVoices = modInfo.hasResources()
            if hasBsa:
                reasons.append(u'\n.    '+_(u'Has BSA archive.'))
            if hasVoices:
                reasons.append(u'\n.    '+_(u'Has associated voice directory (Sound\\Voice\\%s).') % modInfo.name.s)

        #-- Check to make sure NoMerge tag not in tags - if in tags don't show up as mergeable.
        tags = modInfos[modInfo.name].getBashTags()
        if u'NoMerge' in tags:
            if not verbose: return False
            reasons.append(u'\n.    '+_(u"Has 'NoMerge' tag."))
        if reasons: return reasons
        return True

    @staticmethod
    def modIsMergeableLoad(modInfo,verbose):
        allowMissingMasters = {u'Filter', u'IIM', u'InventOnly'}
        tags = modInfos[modInfo.name].getBashTags()
        reasons = []

        #--Load test
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            #MinLoad, InLoadOrder, AddMasters, TrackNewTypes, SkipAllRecords
            modFile = Current.addMod(modInfo.getPath().stail, Flags=0x00002129)
            Current.load()

            missingMasters = []
            nonActiveMasters = []
            masters = modFile.TES4.masters
            for master in masters:
                master = GPath(master)
                if not tags & allowMissingMasters:
                    if master not in modInfos:
                        if not verbose: return False
                        missingMasters.append(master.s)
                    elif not modInfos.isSelected(master):
                        if not verbose: return False
                        nonActiveMasters.append(master.s)
            #--masters not present in mod list?
            if len(missingMasters):
                if not verbose: return False
                reasons.append(u'\n.    '+_(u'Masters missing: ')+u'\n    * %s' % (u'\n    * '.join(sorted(missingMasters))))
            if len(nonActiveMasters):
                if not verbose: return False
                reasons.append(u'\n.    '+_(u'Masters not active: ')+u'\n    * %s' % (u'\n    * '.join(sorted(nonActiveMasters))))
            #--Empty mod
            if modFile.IsEmpty():
                if not verbose: return False
                reasons.append(u'\n.    '+_(u'Empty mod.'))
            #--New record
            else:
                if not tags & allowMissingMasters:
                    newblocks = modFile.GetNewRecordTypes()
                    if newblocks:
                        if not verbose: return False
                        reasons.append(u'\n.    '+_(u'New record(s) in block(s): %s.') % u', '.join(sorted(newblocks)))
            dependent = [curModInfo.name.s for curModInfo in modInfos.data.values() if curModInfo.header.author != u'BASHED PATCH' and modInfo.name.s in curModInfo.header.masters and curModInfo.name not in modInfos.mergeable]
            if dependent:
                if not verbose: return False
                reasons.append(u'\n.    '+_(u'Is a master of non-mergeable mod(s): %s.') % u', '.join(sorted(dependent)))
            if reasons: return reasons
            return True

    @staticmethod
    def modIsMergeable(modInfo,verbose=True):
        """Returns True or error message indicating whether specified mod is mergeable."""
        canmerge = CBash_PatchFile.modIsMergeableNoLoad(modInfo, verbose)
        if verbose:
            loadreasons = CBash_PatchFile.modIsMergeableLoad(modInfo, verbose)
            reasons = []
            if canmerge != True:
                reasons = canmerge
            if loadreasons != True:
                reasons.extend(loadreasons)
            if reasons: return u''.join(reasons)
            return True
        else:
            if canmerge == True:
                return CBash_PatchFile.modIsMergeableLoad(modInfo, verbose)
            return False

    #--Instance
    def __init__(self, patchName, patchers):
        """Initialization."""
        self.patchName = patchName
        #--New attrs
        self.aliases = {} #--Aliases from one mod name to another. Used by text file patchers.
        self.patchers = patchers
        self.mergeIds = set()
        self.loadErrorMods = []
        self.worldOrphanMods = []
        self.unFilteredMods = []
        self.compiledAllMods = []
        self.group_patchers = {}
        self.indexMGEFs = False
        self.mgef_school = bush.mgef_school.copy()
        self.mgef_name = bush.mgef_name.copy()
        self.hostileEffects = bush.hostileEffects.copy()
        self.scanSet = set()
        self.patcher_mod_skipcount = {}
        #--Config
        self.bodyTags = 'ARGHTCCPBS' #--Default bodytags
        self.races_vanilla = ['argonian','breton','dremora','dark elf','dark seducer', 'golden saint','high elf','imperial','khajiit','nord','orc','redguard','wood elf']
        self.races_data = {'EYES':[],'HAIR':[]}
        #--Mods
        loadMods = [name for name in modInfos.ordered if bush.fullLoadOrder[name] < bush.fullLoadOrder[CBash_PatchFile.patchName]]
        if not loadMods:
            raise BoltError(u"No active mods dated before the bashed patch")
        self.setMods(loadMods,[])
        for patcher in self.patchers:
            patcher.initPatchFile(self,loadMods)

    def setMods(self,loadMods=None,mergeMods=None):
        """Sets mod lists and sets."""
        if loadMods is not None: self.loadMods = loadMods
        if mergeMods is not None: self.mergeMods = mergeMods
        self.loadSet = set(self.loadMods)
        self.mergeSet = set(self.mergeMods)
        self.allMods = modInfos.getOrdered(self.loadSet|self.mergeSet)
        self.allSet = set(self.allMods)

    def initData(self,progress):
        """Gives each patcher a chance to get its source data."""
        if not len(self.patchers): return
        progress = progress.setFull(len(self.patchers))
        for index,patcher in enumerate(sorted(self.patchers,key=attrgetter('scanOrder'))):
            progress(index,_(u'Preparing')+u'\n'+patcher.getName())
            patcher.initData(self.group_patchers,SubProgress(progress,index))
        progress(progress.full,_(u'Patchers prepared.'))

    def mergeModFile(self,modFile,progress,doFilter,iiMode,group):
        """Copies contents of modFile group into self."""
        if iiMode and group not in ('LVLC','LVLI','LVSP'): return
        mergeIds = self.mergeIds
        badForm = FormID(GPath(u"Oblivion.esm"),0xA31D) #--DarkPCB record
        for record in getattr(modFile,group):
            #don't merge deleted items
            if record.IsDeleted and group not in ('REFRS','ACHRS','ACRES'):
                print group
                continue
            fid = record.fid
            if not fid.ValidateFormID(self): continue
            if fid == badForm: continue
            #--Include this record?
            if record.IsWinning():
                if record.HasInvalidFormIDs():
                    if doFilter:
                        record.mergeFilter(self)
                        if record.HasInvalidFormIDs():
                            print u"Debugging mergeModFile - Skipping", fid, u"in mod (", record.GetParentMod().ModName, u")due to failed merge filter"
                            dump_record(record)
                            print
                            continue
                    else:
                        print u"Debugging mergeModFile - Skipping", fid, u"in mod (", record.GetParentMod().ModName, u")due to invalid formIDs"
                        dump_record(record)
                        print
                        continue
                if record.IsDeleted and group in ('REFRS','ACHRS','ACRES'):
                    undelete = True
                    override = record.Conflicts()[1].CopyAsOverride(self, UseWinningParents=True)
                else:
                    undelete = False
                    override = record.CopyAsOverride(self, UseWinningParents=True)
                if override:
                    if undelete:
                        override.posZ -= 1000
                        override.IsInitiallyDisabled = True
                    mergeIds.add(override.fid)

    def buildPatch(self,progress):
        """Scans load+merge mods."""
        if not len(self.loadMods): return
        #Parent records must be processed before any children
        #EYES,HAIR must be processed before RACE
        groupOrder = ['GMST','GLOB','MGEF','CLAS','HAIR','EYES','RACE',
                      'SOUN','SKIL','SCPT','LTEX','ENCH','SPEL','BSGN',
                      'ACTI','APPA','ARMO','BOOK','CLOT','DOOR','INGR',
                      'LIGH','MISC','STAT','GRAS','TREE','FLOR','FURN',
                      'WEAP','AMMO','FACT','LVLC','LVLI','LVSP','NPC_',
                      'CREA','CONT','SLGM','KEYM','ALCH','SBSP','SGST',
                      'WTHR','QUST','IDLE','PACK','CSTY','LSCR','ANIO',
                      'WATR','EFSH','CLMT','REGN','DIAL','INFOS','WRLD',
                      'ROADS','CELL','CELLS','PGRDS','LANDS','ACHRS',
                      'ACRES','REFRS']

        iiModeSet = {u'InventOnly', u'IIM'}
        levelLists = {'LVLC', 'LVLI', 'LVSP'}
        nullProgress = bolt.Progress()

        IIMSet = set([modName for modName in (self.allSet|self.scanSet) if bool(modInfos[modName].getBashTags() & iiModeSet)])

        self.Current = ObCollection(ModsPath=dirs['mods'].s)

        #add order reordered
        #mods can't be added more than once, and a mod could be in both the loadSet and mergeSet or loadSet and scanSet
        #if it was added as a normal mod first, it isn't flagged correctly when later added as a merge mod
        #if it was added as a scan mod first, it isn't flagged correctly when later added as a normal mod
        for name in self.mergeSet:
            if bush.fullLoadOrder[name] < bush.fullLoadOrder[CBash_PatchFile.patchName]:
                self.Current.addMergeMod(modInfos[name].getPath().stail)
        for name in self.loadSet:
            if name not in self.mergeSet:
                if bush.fullLoadOrder[name] < bush.fullLoadOrder[CBash_PatchFile.patchName]:
                    self.Current.addMod(modInfos[name].getPath().stail)
        for name in self.scanSet:
            if name not in self.mergeSet and name not in self.loadSet:
                if bush.fullLoadOrder[name] < bush.fullLoadOrder[CBash_PatchFile.patchName]:
                    self.Current.addScanMod(modInfos[name].getPath().stail)
        self.patchName.temp.remove()
        patchFile = self.patchFile = self.Current.addMod(self.patchName.temp.s, CreateNew=True)
        self.Current.load()

        if self.Current.LookupModFileLoadOrder(self.patchName.temp.s) <= 0:
            print (_(u"Please copy this entire message and report it on the current official thread at http://forums.bethsoft.com/index.php?/forum/25-mods/.") +
                   u'\n' +
                   _(u'Also with:') +
                   u'\n' +
                   _(u'1. Your OS:') +
                   u'\n' +
                   _(u'2. Your installed MS Visual C++ redistributable versions:') +
                   u'\n' +
                   _(u'3. Your system RAM amount:') +
                   u'\n' +
                   _(u'4. How much memory Python.exe\pythonw.exe or Wrye Bash.exe is using') +
                   u'\n' +
                   _(u'5. and finally... if restarting Wrye Bash and trying again and building the CBash Bashed Patch right away works fine') +
                   u'\n')
            print self.Current.Debug_DumpModFiles()
            raise StateError()
        ObModFile.__init__(self, patchFile._ModID)

        self.TES4.author = u'BASHED PATCH'

        #With this indexing, MGEFs may be looped through twice if another patcher also looks through MGEFs
        #It's inefficient, but it really shouldn't be a problem since there are so few MGEFs.
        if self.indexMGEFs:
            mgefId_hostile = {}
            self.mgef_school.clear()
            self.mgef_name.clear()
            for modName in self.allMods:
                modFile = self.Current.LookupModFile(modName.s)
                for record in modFile.MGEF:
                    full = record.full
                    eid = record.eid
                    if full and eid:
                        eidRaw = eid.encode('cp1252')
                        mgefId = MGEFCode(eidRaw) if record.recordVersion is None else record.mgefCode
                        self.mgef_school[mgefId] = record.schoolType
                        self.mgef_name[mgefId] = full
                        mgefId_hostile[mgefId] = record.IsHostile
                    record.UnloadRecord()
            self.hostileEffects = set([mgefId for mgefId, hostile in mgefId_hostile.iteritems() if hostile])
        self.completeMods = modInfos.getOrdered(self.allSet|self.scanSet)
        group_patchers = self.group_patchers

        mod_patchers = group_patchers.get('MOD')
        if mod_patchers:
            mod_apply = [patcher.mod_apply for patcher in sorted(mod_patchers,key=attrgetter('editOrder')) if hasattr(patcher,'mod_apply')]
            del group_patchers['MOD']
            del mod_patchers
        else:
            mod_apply = []

        for modName in self.completeMods:
            modInfo = modInfos[modName]
            bashTags = modInfo.getBashTags()
            modFile = self.Current.LookupModFile(modInfo.getPath().stail)

            #--Error checks
            if modName in self.loadMods and u'Filter' in bashTags:
                self.unFilteredMods.append(modName)
            gls = modFile.LookupRecord(FormID(0x00025811))
            if gls and gls.compiledSize == 4 and gls.lastIndex == 0 and modName != GPath(u'Oblivion.esm'):
                self.compiledAllMods.append(modName)
            isScanned = modName in self.scanSet and modName not in self.loadSet and modName not in self.mergeSet
            if not isScanned:
                for patcher in mod_apply:
                    patcher(modFile, bashTags)

        numFinishers = 0
        for group, patchers in group_patchers.iteritems():
            for patcher in patchers:
                if hasattr(patcher,'finishPatch'):
                    numFinishers += 1
                    break

        progress = progress.setFull(len(groupOrder) + max(numFinishers,1))
        maxVersion = 0
        for index,group in enumerate(groupOrder):
            patchers = group_patchers.get(group, None)
            pstate = 0
            subProgress = SubProgress(progress,index)
            subProgress.setFull(max(len(self.completeMods),1))
            for modName in self.completeMods:
                if modName == self.patchName: continue
                modInfo = modInfos[modName]
                bashTags = modInfo.getBashTags()
                isScanned = modName in self.scanSet and modName not in self.loadSet and modName not in self.mergeSet
                isMerged = modName in self.mergeSet
                doFilter = isMerged and u'Filter' in bashTags
                #--iiMode is a hack to support Item Interchange. Actual key used is InventOnly.
                iiMode = isMerged and bool(iiModeSet & bashTags)
                iiFilter = IIMSet and not (iiMode or group in levelLists)
                modFile = self.Current.LookupModFile(modInfo.getPath().stail)
                modGName = modFile.GName

                if patchers:
                    subProgress(pstate,_(u'Patching...')+u'\n%s::%s' % (modName.s,group))
                    pstate += 1
                    #Filter the used patchers as needed
                    if iiMode:
                        applyPatchers = [patcher.apply for patcher in sorted(patchers,key=attrgetter('editOrder')) if hasattr(patcher,'apply') and patcher.iiMode if not patcher.applyRequiresChecked or (modGName in patcher.srcs)]
                        scanPatchers = [patcher.scan for patcher in sorted(patchers,key=attrgetter('scanOrder')) if hasattr(patcher,'scan') and patcher.iiMode if not patcher.scanRequiresChecked or (modGName in patcher.srcs)]
                    elif isScanned:
                        applyPatchers = [] #Scanned mods should never be copied directly into the bashed patch.
                        scanPatchers = [patcher.scan for patcher in sorted(patchers,key=attrgetter('scanOrder')) if hasattr(patcher,'scan') and patcher.allowUnloaded if not patcher.scanRequiresChecked or (modGName in patcher.srcs)]
                    else:
                        applyPatchers = [patcher.apply for patcher in sorted(patchers,key=attrgetter('editOrder')) if hasattr(patcher,'apply') if not patcher.applyRequiresChecked or (modGName in patcher.srcs)]
                        scanPatchers = [patcher.scan for patcher in sorted(patchers,key=attrgetter('scanOrder')) if hasattr(patcher,'scan') if not patcher.scanRequiresChecked or (modGName in patcher.srcs)]

                    #See if all the patchers were filtered out
                    if not (applyPatchers or scanPatchers): continue
                    for record in getattr(modFile, group):
                        #If conflicts is > 0, it will include all conflicts, even the record that called it
                        #(i.e. len(conflicts) will never equal 1)
                        #The winning record is at position 0, and the last record is the one most overridden
                        if doFilter:
                            if not record.fid.ValidateFormID(self): continue
                            if record.HasInvalidFormIDs():
                                record.mergeFilter(self)
                                if record.HasInvalidFormIDs():
                                    print u"Debugging buildPatch - Skipping", record.fid, u"in mod (", record.GetParentMod().ModName, u")due to failed merge filter"
                                    dump_record(record)
                                    print
                                    continue

                        if not isScanned and record.HasInvalidFormIDs():
                            print u"Debugging buildPatch - Skipping", record.fid, u"in mod (", record.GetParentMod().ModName, u")due to invalid formIDs"
                            dump_record(record)
                            print
                            continue

                        if iiFilter:
                            #InventOnly/IIM tags are a pain. They don't fit the normal patch model.
                            #They're basically a mixture of scanned and merged.
                            #This effectively hides all non-level list records from the other patchers
                            conflicts = [conflict for conflict in record.Conflicts() if conflict.GetParentMod().GName not in IIMSet]
                            isWinning = (len(conflicts) < 2 or conflicts[0] == record)
                        else:
                            #Prevents scanned records from being scanned twice if the scanned record loads later than the real winning record
                            # (once when the real winning record is applied, and once when the scanned record is later encountered)
                            if isScanned and record.IsWinning(True): #Not the most optimized, but works well enough
                                continue #doesn't work if the record's been copied into the patch...needs work
                            isWinning = record.IsWinning()

                        for patcher in applyPatchers if isWinning else scanPatchers:
                            patcher(modFile, record, bashTags)
                        record.UnloadRecord()
                if isMerged:
                    progress(index,modFile.ModName+u'\n'+_(u'Merging...')+u'\n'+group)
                    self.mergeModFile(modFile,nullProgress,doFilter,iiMode,group)
                maxVersion = max(modFile.TES4.version, maxVersion)
        # Force 1.0 as max TES4 version for now, as we don't expect any new esp format changes,
        # and if they do come about, we can always change this.  Plus this will solve issues where
        # Mod files mistakenly have the header version set > 1.0
        self.Current.ClearReferenceLog()
        self.TES4.version = min(maxVersion,max(bush.game.esp.validHeaderVersions))
        #Finish the patch
        progress(len(groupOrder))
        subProgress = SubProgress(progress,len(groupOrder))
        subProgress.setFull(max(numFinishers,1))
        pstate = 0
        for group, patchers in group_patchers.iteritems():
            finishPatchers = [patcher.finishPatch for patcher in sorted(patchers,key=attrgetter('editOrder')) if hasattr(patcher,'finishPatch')]
            if finishPatchers:
                subProgress(pstate,_(u'Final Patching...')+u'\n%s::%s' % (self.ModName,group))
                pstate += 1
                for patcher in finishPatchers:
                    patcher(self, subProgress)
        #--Fix UDR's
        progress(0,_(u'Cleaning...'))
        records = self.ACRES + self.ACHRS + self.REFRS
        progress.setFull(max(len(records),1))
        for i,record in enumerate(records):
            progress(i)
            if record.IsDeleted:
                record.IsDeleted = False
                record.IsIgnored = True
        #--Done
        progress(progress.full,_(u'Patchers applied.'))
        self.ScanCollection = None

    def buildPatchLog(self,patchName,log,progress):
        """Completes merge process. Use this when finished using buildPatch."""
        if not len(self.patchers): return
        log.setHeader(u'= '+patchName.s+u' '+u'='*30+u'#',True)
        log(u"{{CONTENTS=1}}")
        #--Load Mods and error mods
        log.setHeader(u'= '+_(u'Overview'),True)
        log.setHeader(u'=== '+_(u'Date/Time'))
        log(u'* '+formatDate(time.time()))
        log(u'* '+_(u'Elapsed Time: ') + 'TIMEPLACEHOLDER')
        if self.patcher_mod_skipcount:
            log.setHeader(u'=== '+_(u'Skipped Imports'))
            log(_(u"The following import patchers skipped records because the imported record required a missing or non-active mod to work properly. If this was not intentional, rebuild the patch after either deactivating the imported mods listed below or activating the missing mod(s)."))
            for patcher, mod_skipcount in self.patcher_mod_skipcount.iteritems():
                log(u'* '+_(u'%s skipped %d records:') % (patcher,sum(mod_skipcount.values())))
                for mod, skipcount in mod_skipcount.iteritems():
                    log (u'  * '+_(u'The imported mod, %s, skipped %d records.') % (mod,skipcount))

        if self.unFilteredMods:
            log.setHeader(u'=== '+_(u'Unfiltered Mods'))
            log(_(u"The following mods were active when the patch was built. For the mods to work properly, you should deactivate the mods and then rebuild the patch with the mods [[http://wrye.ufrealms.net/Wrye%20Bash.html#MergeFiltering|Merged]] in."))
            for mod in self.unFilteredMods: log (u'* '+mod.s)
        if self.loadErrorMods:
            log.setHeader(u'=== '+_(u'Load Error Mods'))
            log(_(u"The following mods had load errors and were skipped while building the patch. Most likely this problem is due to a badly formatted mod. For more info, see [[http://www.uesp.net/wiki/Tes4Mod:Wrye_Bash/Bashed_Patch#Error_Messages|Bashed Patch: Error Messages]]."))
            for (mod,e) in self.loadErrorMods: log (u'* '+mod.s+u': %s' % e)
        if self.worldOrphanMods:
            log.setHeader(u'=== '+_(u'World Orphans'))
            log(_(u"The following mods had orphaned world groups, which were skipped. This is not a major problem, but you might want to use Bash's [[http://wrye.ufrealms.net/Wrye%20Bash.html#RemoveWorldOrphans|Remove World Orphans]] command to repair the mods."))
            for mod in self.worldOrphanMods: log (u'* '+mod.s)
        if self.compiledAllMods:
            log.setHeader(u'=== '+_(u'Compiled All'))
            log(_(u"The following mods have an empty compiled version of genericLoreScript. This is usually a sign that the mod author did a __compile all__ while editing scripts. This may interfere with the behavior of other mods that intentionally modify scripts from Oblivion.esm. (E.g. Cobl and Unofficial Oblivion Patch.) You can use Bash's [[http://wrye.ufrealms.net/Wrye%20Bash.html#DecompileAll|Decompile All]] command to repair the mods."))
            for mod in self.compiledAllMods: log (u'* '+mod.s)
        log.setHeader(u'=== '+_(u'Active Mods'),True)
        for name in self.allMods:
            version = modInfos.getVersion(name)
            if name in self.loadMods:
                message = u'* %02X ' % (self.loadMods.index(name),)
            else:
                message = u'* ++ '
            if version:
                message += _(u'%s  [Version %s]') % (name.s,version)
            else:
                message += name.s
            log(message)
        #--Load Mods and error mods
        if self.aliases:
            log.setHeader(u'= '+_(u'Mod Aliases'))
            for key,value in sorted(self.aliases.iteritems()):
                log(u'* %s >> %s' % (key.s,value.s))
        #--Patchers
        subProgress = SubProgress(progress,0,0.9,len(self.patchers))
        for index,patcher in enumerate(sorted(self.patchers,key=attrgetter('editOrder'))):
            subProgress(index,_(u'Completing')+u'\n%s...' % patcher.getName())
            patcher.buildPatchLog(log)
        progress(1.0,_(u"Compiled."))
        #--Description
        numRecords = sum([len(x) for x in self.aggregates.values()])
        self.TES4.description = (_(u"Updated: %s") % formatDate(time.time()) +
                                 u'\n\n' +
                                 _(u'Records Changed: %d') % numRecords
                                 )

#------------------------------------------------------------------------------
from patcher.base import Patcher, CBash_Patcher, AListPatcher, AMultiTweaker, \
    AAliasesPatcher

class ListPatcher(AListPatcher,Patcher):

    def _patchesList(self):
        return dirs['patches'].list()

    def _patchFile(self):
        return PatchFile

class CBash_ListPatcher(AListPatcher,CBash_Patcher):
    unloadedText = u'\n\n'+_(u'Any non-active, non-merged mods in the'
                             u' following list will be IGNORED.')

    #--Config Phase -----------------------------------------------------------
    def _patchesList(self):
        return getPatchesList()

    def _patchFile(self):
        return CBash_PatchFile

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(CBash_ListPatcher, self).initPatchFile(patchFile,loadMods)
        self.srcs = self.getConfigChecked()
        self.isActive = bool(self.srcs)

    def getConfigChecked(self):
        """Returns checked config items in list order."""
        if self.allowUnloaded:
            return [item for item in self.configItems if
                    self.configChecks[item]]
        else:
            return [item for item in self.configItems if
                    self.configChecks[item] and (
                        item in self.patchFile.allMods or not reModExt.match(
                            item.s))]

#------------------------------------------------------------------------------
class MultiTweaker(AMultiTweaker,Patcher):

    def buildPatch(self,log,progress):
        """Applies individual tweaks."""
        if not self.isActive: return
        log.setHeader(u'= '+self.__class__.name,True)
        for tweak in self.enabledTweaks:
            tweak.buildPatch(log,progress,self.patchFile)

class CBash_MultiTweaker(AMultiTweaker,CBash_Patcher):
    #--Config Phase -----------------------------------------------------------
    def initData(self,group_patchers,progress):
        """Compiles material, i.e. reads source text, esp's, etc. as necessary."""
        if not self.isActive: return
        for tweak in self.enabledTweaks:
            for type_ in tweak.getTypes():
                group_patchers.setdefault(type_,[]).append(tweak)

    #--Patch Phase ------------------------------------------------------------
    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        log.setHeader(u'= '+self.__class__.name,True)
        for tweak in self.enabledTweaks:
            tweak.buildPatchLog(log)

class ADoublePatcher(AListPatcher):
    """docs - what's this about ?""" # TODO

    def getConfig(self,configs):
        """Get config from configs dictionary and/or set to default."""
        super(ADoublePatcher, self).getConfig(configs)
        self.tweaks = copy.deepcopy(self.__class__.tweaks)
        config = configs.setdefault(self.__class__.__name__,self.__class__.defaultConfig)
        for tweak in self.tweaks:
            tweak.getConfig(config)

    def saveConfig(self,configs):
        """Save config to configs dictionary."""
        #--Toss outdated configCheck data.
        super(ADoublePatcher, self).saveConfig(configs)
        config = configs[self.__class__.__name__]
        for tweak in self.tweaks:
            tweak.saveConfig(config)
        self.enabledTweaks = [tweak for tweak in self.tweaks if tweak.isEnabled]

class DoublePatcher(ADoublePatcher, ListPatcher): pass

class CBash_DoublePatcher(ADoublePatcher, CBash_ListPatcher): pass

# Patchers: 10 ----------------------------------------------------------------
#------------------------------------------------------------------------------
class AliasesPatcher(AAliasesPatcher,Patcher): pass

class CBash_AliasesPatcher(AAliasesPatcher,CBash_Patcher):
    #--Config Phase -----------------------------------------------------------
    def getConfig(self,configs):
        """Get config from configs dictionary and/or set to default."""
        super(CBash_AliasesPatcher,self).getConfig(configs)
        self.srcs = [] #so as not to fail screaming when determining load mods - but with the least processing required.

#------------------------------------------------------------------------------
class APatchMerger(AListPatcher):
    """Merges specified patches into Bashed Patch."""
    scanOrder = 10
    editOrder = 10
    group = _(u'General')
    name = _(u'Merge Patches')
    text = _(u"Merge patch mods into Bashed Patch.")
    autoRe = re.compile(ur"^UNDEFINED$",re.I|re.U)

    def getAutoItems(self):
        """Returns list of items to be used for automatic configuration."""
        autoItems = []
        for modInfo in modInfos.data.values():
            if modInfo.name in modInfos.mergeable and u'NoMerge' not in \
                    modInfo.getBashTags() and \
                            bush.fullLoadOrder[modInfo.name] < \
                            bush.fullLoadOrder[self._patchFile().patchName]:
                autoItems.append(modInfo.name)
        return autoItems

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(APatchMerger,self).initPatchFile(patchFile,loadMods)
        #--WARNING: Since other patchers may rely on the following update
        # during their initPatchFile section, it's important that PatchMerger
        # runs first or near first.
        self._setMods(patchFile)

    def _setMods(self, patchFile): raise AbstractError # override in subclasses

class PatchMerger(APatchMerger, ListPatcher):
    autoKey = u'Merge'

    def _setMods(self,patchFile):
        if self.isEnabled: #--Since other mods may rely on this
            patchFile.setMods(None,self.getConfigChecked())

class CBash_PatchMerger(APatchMerger, CBash_ListPatcher):
    autoKey = {u'Merge'}
    unloadedText = "" # Cbash only

    def _setMods(self,patchFile):
        if not self.isActive: return
        if self.isEnabled: #--Since other mods may rely on this
            patchFile.setMods(None,self.srcs)

#------------------------------------------------------------------------------
# TODO: MI for UpdateReferences - notice self.srcFiles =self.getConfigChecked()
# vs self.srcs = self.getConfigChecked() in CBash_ListPatcher.initPatchFile()
# plus unused vars, commented out code etc etc

class UpdateReferences(ListPatcher):
    """Imports Form Id replacers into the Bashed Patch."""
    scanOrder = 15
    editOrder = 15
    group = _(u'General')
    name = _(u'Replace Form IDs')
    text = _(u"Imports Form Id replacers from csv files into the Bashed Patch.")
    autoKey = u'Formids'
    canAutoItemCheck = False #--GUI: Whether new items are checked by default or not.

    #--Config Phase -----------------------------------------------------------
    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.srcFiles = self.getConfigChecked()
        self.isActive = bool(self.srcFiles)
        self.types = MreRecord.simpleTypes
        self.classes = self.types.union(
            {'CELL', 'WRLD', 'REFR', 'ACHR', 'ACRE'})
        self.old_new = {} #--Maps old fid to new fid
        self.old_eid = {} #--Maps old fid to old editor id
        self.new_eid = {} #--Maps new fid to new editor id

    def readFromText(self,textPath):
        """Reads replacment data from specified text file."""
        old_new,old_eid,new_eid = self.old_new,self.old_eid,self.new_eid
        aliases = self.patchFile.aliases
        with bolt.CsvReader(textPath) as ins:
            pack,unpack = struct.pack,struct.unpack
            for fields in ins:
                if len(fields) < 7 or fields[2][:2] != u'0x' or fields[6][:2] != u'0x': continue
                oldMod,oldObj,oldEid,newEid,newMod,newObj = fields[1:7]
                oldMod,newMod = map(GPath,(oldMod,newMod))
                oldId = (GPath(aliases.get(oldMod,oldMod)),int(oldObj,16))
                newId = (GPath(aliases.get(newMod,newMod)),int(newObj,16))
                old_new[oldId] = newId
                old_eid[oldId] = oldEid
                new_eid[newId] = newEid

    def initData(self,progress):
        """Get names from source files."""
        if not self.isActive: return
        progress.setFull(len(self.srcFiles))
        patchesList = getPatchesList()
        for srcFile in self.srcFiles:
            srcPath = GPath(srcFile)
            if srcPath not in patchesList: continue
            if getPatchesPath(srcFile).isfile():
                self.readFromText(getPatchesPath(srcFile))
            progress.plus()

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return tuple(self.classes) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return tuple(self.classes) if self.isActive else ()

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        if not self.isActive: return
        mapper = modFile.getLongMapper()
        patchCells = self.patchFile.CELL
        patchWorlds = self.patchFile.WRLD
        newRecords = []
        modFile.convertToLongFids(('CELL','WRLD','REFR','ACRE','ACHR'))
##        for type in self.types:
##            for record in getattr(modFile,type).getActiveRecords():
##                record = record.getTypeCopy(mapper)
##                if record.fid in self.old_new:
##                    getattr(self.patchFile,type).setRecord(record)
        if 'CELL' in modFile.tops:
            for cellBlock in modFile.CELL.cellBlocks:
                cellImported = False
                if cellBlock.cell.fid in patchCells.id_cellBlock:
                    patchCells.id_cellBlock[cellBlock.cell.fid].cell = cellBlock.cell
                    cellImported = True
                for record in cellBlock.temp:
                    if record.base in self.old_new:
                        if not cellImported:
                            patchCells.setCell(cellBlock.cell)
                            cellImported = True
                        for newRef in patchCells.id_cellBlock[cellBlock.cell.fid].temp:
                            if newRef.fid == record.fid:
                                loc = patchCells.id_cellBlock[cellBlock.cell.fid].temp.index(newRef)
                                patchCells.id_cellBlock[cellBlock.cell.fid].temp[loc] = record
                                break
                        else:
                            patchCells.id_cellBlock[cellBlock.cell.fid].temp.append(record)
                for record in cellBlock.persistent:
                    if record.base in self.old_new:
                        if not cellImported:
                            patchCells.setCell(cellBlock.cell)
                            cellImported = True
                        for newRef in patchCells.id_cellBlock[cellBlock.cell.fid].persistent:
                            if newRef.fid == record.fid:
                                loc = patchCells.id_cellBlock[cellBlock.cell.fid].persistent.index(newRef)
                                patchCells.id_cellBlock[cellBlock.cell.fid].persistent[loc] = record
                                break
                        else:
                            patchCells.id_cellBlock[cellBlock.cell.fid].persistent.append(record)
        if 'WRLD' in modFile.tops:
            for worldBlock in modFile.WRLD.worldBlocks:
                worldImported = False
                if worldBlock.world.fid in patchWorlds.id_worldBlocks:
                    patchWorlds.id_worldBlocks[worldBlock.world.fid].world = worldBlock.world
                    worldImported = True
                for cellBlock in worldBlock.cellBlocks:
                    cellImported = False
                    if worldBlock.world.fid in patchWorlds.id_worldBlocks and cellBlock.cell.fid in patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock:
                        patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].cell = cellBlock.cell
                        cellImported = True
                    for record in cellBlock.temp:
                        if record.base in self.old_new:
                            if not worldImported:
                                patchWorlds.setWorld(worldBlock.world)
                                worldImported = True
                            if not cellImported:
                                patchWorlds.id_worldBlocks[worldBlock.world.fid].setCell(cellBlock.cell)
                                cellImported = True
                            for newRef in patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].temp:
                                if newRef.fid == record.fid:
                                    loc = patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].temp.index(newRef)
                                    patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].temp[loc] = record
                                    break
                            else:
                                patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].temp.append(record)
                    for record in cellBlock.persistent:
                        if record.base in self.old_new:
                            if not worldImported:
                                patchWorlds.setWorld(worldBlock.world)
                                worldImported = True
                            if not cellImported:
                                patchWorlds.id_worldBlocks[worldBlock.world.fid].setCell(cellBlock.cell)
                                cellImported = True
                            for newRef in patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].persistent:
                                if newRef.fid == record.fid:
                                    loc = patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].persistent.index(newRef)
                                    patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].persistent[loc] = record
                                    break
                            else:
                                patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].persistent.append(record)

    def buildPatch(self,log,progress):
        """Adds merged fids to patchfile."""
        if not self.isActive: return
        old_new,old_eid,new_eid = self.old_new,self.old_eid,self.new_eid
        masters = self.patchFile
        keep = self.patchFile.getKeeper()
        count = CountDict()
        def swapper(oldId):
            newId = old_new.get(oldId,None)
            return newId if newId else oldId
##        for type in self.types:
##            for record in getattr(self.patchFile,type).getActiveRecords():
##                if record.fid in self.old_new:
##                    record.fid = swapper(record.fid)
##                    count.increment(record.fid[0])
####                    record.mapFids(swapper,True)
##                    record.setChanged()
##                    keep(record.fid)
        for cellBlock in self.patchFile.CELL.cellBlocks:
            for record in cellBlock.temp:
                if record.base in self.old_new:
                    record.base = swapper(record.base)
                    count.increment(cellBlock.cell.fid[0])
##                    record.mapFids(swapper,True)
                    record.setChanged()
                    keep(record.fid)
            for record in cellBlock.persistent:
                if record.base in self.old_new:
                    record.base = swapper(record.base)
                    count.increment(cellBlock.cell.fid[0])
##                    record.mapFids(swapper,True)
                    record.setChanged()
                    keep(record.fid)
        for worldBlock in self.patchFile.WRLD.worldBlocks:
            keepWorld = False
            for cellBlock in worldBlock.cellBlocks:
                for record in cellBlock.temp:
                    if record.base in self.old_new:
                        record.base = swapper(record.base)
                        count.increment(cellBlock.cell.fid[0])
##                        record.mapFids(swapper,True)
                        record.setChanged()
                        keep(record.fid)
                        keepWorld = True
                for record in cellBlock.persistent:
                    if record.base in self.old_new:
                        record.base = swapper(record.base)
                        count.increment(cellBlock.cell.fid[0])
##                        record.mapFids(swapper,True)
                        record.setChanged()
                        keep(record.fid)
                        keepWorld = True
            if keepWorld:
                keep(worldBlock.world.fid)

        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        for mod in self.getConfigChecked():
            log(u'* ' +mod.s)
        log(u'\n=== '+_(u'Records Patched'))
        for srcMod in modInfos.getOrdered(count.keys()):
            log(u'* %s: %d' % (srcMod.s,count[srcMod]))

from patcher.oblivion.utilities import CBash_FidReplacer

class CBash_UpdateReferences(CBash_ListPatcher):
    """Imports Form Id replacers into the Bashed Patch."""
    scanOrder = 15
    editOrder = 15
    group = _(u'General')
    name = _(u'Replace Form IDs')
    text = _(u"Imports FormId replacers from csv files into the Bashed Patch.")
    autoKey = {u'Formids'}
    canAutoItemCheck = False #--GUI: Whether new items are checked by default or not.
    unloadedText = u'\n\n'+_(u'Any non-active, non-merged mods referenced by files selected in the following list will be IGNORED.')

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ListPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.old = [] #--Maps old fid to new fid
        self.new = [] #--Maps old fid to new fid
        self.old_eid = {} #--Maps old fid to old editor id
        self.new_eid = {} #--Maps new fid to new editor id
        self.mod_count_old_new = {}

    def initData(self,group_patchers,progress):
        """Compiles material, i.e. reads source text, esp's, etc. as necessary."""
        if not self.isActive: return
        fidReplacer = CBash_FidReplacer(aliases=self.patchFile.aliases)
        progress.setFull(len(self.srcs))
        patchesList = getPatchesList()
        for srcFile in self.srcs:
            if not reModExt.search(srcFile.s):
                if srcFile not in patchesList: continue
                if getPatchesPath(srcFile).isfile():
                    fidReplacer.readFromText(getPatchesPath(srcFile))
            progress.plus()
        #--Finish
        self.old_new = fidReplacer.old_new
        self.old_eid.update(fidReplacer.old_eid)
        self.new_eid.update(fidReplacer.new_eid)
        self.isActive = bool(self.old_new)
        if not self.isActive: return

        for type_ in self.getTypes():
            group_patchers.setdefault(type_,[]).append(self)

    def getTypes(self):
        return ['MOD','FACT','RACE','MGEF','SCPT','LTEX','ENCH',
                'SPEL','BSGN','ACTI','APPA','ARMO','BOOK',
                'CLOT','CONT','DOOR','INGR','LIGH','MISC',
                'FLOR','FURN','WEAP','AMMO','NPC_','CREA',
                'LVLC','SLGM','KEYM','ALCH','SGST','LVLI',
                'WTHR','CLMT','REGN','CELLS','WRLD','ACHRS',
                'ACRES','REFRS','DIAL','INFOS','QUST','IDLE',
                'PACK','LSCR','LVSP','ANIO','WATR']

    #--Patch Phase ------------------------------------------------------------
    def mod_apply(self,modFile,bashTags):
        """Changes the mod in place without copying any records."""
        counts = modFile.UpdateReferences(self.old_new)
        #--Done
        if sum(counts):
            self.mod_count_old_new[modFile.GName] = [(count,self.old_eid[old_newId[0]],self.new_eid[old_newId[1]]) for count, old_newId in zip(counts, self.old_new.iteritems())]

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.GetRecordUpdatedReferences():
            override = record.CopyAsOverride(self.patchFile, UseWinningParents=True)
            if override:
                record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        mod_count_old_new = self.mod_count_old_new

        log.setHeader(u'= ' +self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        if not self.srcs:
            log(u". ~~%s~~" % _(u'None'))
        else:
            for srcFile in self.srcs:
                log(u"* " +srcFile.s)
        log(u'\n')
        for mod in modInfos.getOrdered(mod_count_old_new.keys()):
            entries = mod_count_old_new[mod]
            log(u'\n=== %s' % mod.s)
            entries.sort(key=itemgetter(1))
            log(u'  * '+_(u'Updated References: %d') % sum([count for count, old, new in entries]))
            log(u'\n'.join([u'    * %3d %s >> %s' % entry for entry in entries if entry[0] > 0]))

        self.old_new = {} #--Maps old fid to new fid
        self.old_eid = {} #--Maps old fid to old editor id
        self.new_eid = {} #--Maps new fid to new editor id
        self.mod_count_old_new = {}

# Patchers: 20 ----------------------------------------------------------------
#------------------------------------------------------------------------------
class AImportPatcher(AListPatcher):
    """Subclass for patchers in group Importer."""
    group = _(u'Importers')
    scanOrder = 20
    editOrder = 20
    masters = {}
    autoRe = re.compile(ur"^UNDEFINED$",re.I|re.U)

    def saveConfig(self,configs):
        """Save config to configs dictionary."""
        super(AImportPatcher, self).saveConfig(configs)
        if self.isEnabled:
            importedMods = [item for item,value in
                            self.configChecks.iteritems() if
                            value and reModExt.search(item.s)]
            configs['ImportedMods'].update(importedMods)

class ImportPatcher(AImportPatcher, ListPatcher):

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return tuple(
            x.classType for x in self.srcClasses) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return tuple(
            x.classType for x in self.srcClasses) if self.isActive else ()

class CBash_ImportPatcher(AImportPatcher, CBash_ListPatcher):
    scanRequiresChecked = True
    applyRequiresChecked = False

    def scan_more(self,modFile,record,bashTags):
        if modFile.GName in self.srcs:
            self.scan(modFile,record,bashTags)
        #Must check for "unloaded" conflicts that occur past the winning record
        #If any exist, they have to be scanned
        for conflict in record.Conflicts(True):
            if conflict != record:
                mod = conflict.GetParentMod()
                if mod.GName in self.srcs:
                    tags = modInfos[mod.GName].getBashTags()
                    self.scan(mod,conflict,tags)
            else: return

# TODO: The buildPatchLog() methods of CBash_ImportPatcher subclasses vary in such
# a degree that I can't extract a common - 6 are the same though - see CBash_CellImporter

#------------------------------------------------------------------------------
class CellImporter(ImportPatcher):
    """Merges changes to cells (climate, lighting, and water.)"""
    name = _(u'Import Cells')
    text = _(u"Import cells (climate, lighting, and water) from source mods.")
    tip = text
    autoKey = (u'C.Climate',u'C.Light',u'C.Water',u'C.Owner',u'C.Name',u'C.RecordFlags',u'C.Music')#,u'C.Maps')

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.cellData = {}
        self.sourceMods = self.getConfigChecked()
        self.isActive = bool(self.sourceMods)
        self.recAttrs = {
            u'C.Climate': ('climate',),
            u'C.Music': ('music',),
            u'C.Name': ('full',),
            u'C.Owner': ('ownership',),
            u'C.Water': ('water','waterHeight'),
            u'C.Light': ('ambientRed','ambientGreen','ambientBlue','unused1',
                        'directionalRed','directionalGreen','directionalBlue','unused2',
                        'fogRed','fogGreen','fogBlue','unused3',
                        'fogNear','fogFar','directionalXY','directionalZ',
                        'directionalFade','fogClip'),
            u'C.RecordFlags': ('flags1',), # Yes seems funky but thats the way it is
            }
        self.recFlags = {
            u'C.Climate': 'behaveLikeExterior',
            u'C.Music': '',
            u'C.Name': '',
            u'C.Owner': 'publicPlace',
            u'C.Water': 'hasWater',
            u'C.Light': '',
            u'C.RecordFlags': '',
            }

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('CELL','WRLD',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('CELL','WRLD',) if self.isActive else ()

    def initData(self,progress):
        """Get cells from source files."""
        if not self.isActive: return
        def importCellBlockData(cellBlock):
            if not cellBlock.cell.flags1.ignored:
                fid = cellBlock.cell.fid
                if fid not in tempCellData:
                    tempCellData[fid] = {}
                    tempCellData[fid+('flags',)] = {}
                for attr in attrs:
                    tempCellData[fid][attr] = cellBlock.cell.__getattribute__(attr)
                for flag in flags:
                    tempCellData[fid+('flags',)][flag] = cellBlock.cell.flags.__getattr__(flag)
        def checkMasterCellBlockData(cellBlock):
            if not cellBlock.cell.flags1.ignored:
                fid = cellBlock.cell.fid
                if fid not in tempCellData: return
                if fid not in cellData:
                    cellData[fid] = {}
                    cellData[fid+('flags',)] = {}
                for attr in attrs:
                    if tempCellData[fid][attr] != cellBlock.cell.__getattribute__(attr):
                        cellData[fid][attr] = tempCellData[fid][attr]
                for flag in flags:
                    if tempCellData[fid+('flags',)][flag] != cellBlock.cell.flags.__getattr__(flag):
                        cellData[fid+('flags',)][flag] = tempCellData[fid+('flags',)][flag]
        cellData = self.cellData
        # cellData['Maps'] = {}
        loadFactory = LoadFactory(False,MreRecord.type_class['CELL'],
                                        MreRecord.type_class['WRLD'])
        progress.setFull(len(self.sourceMods))
        cachedMasters = {}
        for srcMod in self.sourceMods:
            if srcMod not in modInfos: continue
            tempCellData = {'Maps':{}}
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            srcFile.convertToLongFids(('CELL','WRLD'))
            masters = srcInfo.header.masters
            bashTags = srcInfo.getBashTags()
            # print bashTags
            try:
                attrs = set(reduce(operator.add, (self.recAttrs[bashKey] for bashKey in bashTags if
                    bashKey in self.recAttrs)))
            except: attrs = set()
            flags = tuple(self.recFlags[bashKey] for bashKey in bashTags if
                bashKey in self.recAttrs and self.recFlags[bashKey] != u'')
            if 'CELL' in srcFile.tops:
                for cellBlock in srcFile.CELL.cellBlocks:
                    importCellBlockData(cellBlock)
            if 'WRLD' in srcFile.tops:
                for worldBlock in srcFile.WRLD.worldBlocks:
                    for cellBlock in worldBlock.cellBlocks:
                        importCellBlockData(cellBlock)
                    # if 'C.Maps' in bashTags:
                    #     if worldBlock.world.mapPath:
                    #         tempCellData['Maps'][worldBlock.world.fid] = worldBlock.world.mapPath
            for master in masters:
                if not master in modInfos: continue # or break filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = modInfos[master]
                    masterFile = ModFile(masterInfo,loadFactory)
                    masterFile.load(True)
                    masterFile.convertToLongFids(('CELL','WRLD'))
                    cachedMasters[master] = masterFile
                if 'CELL' in masterFile.tops:
                    for cellBlock in masterFile.CELL.cellBlocks:
                        checkMasterCellBlockData(cellBlock)
                if 'WRLD' in masterFile.tops:
                    for worldBlock in masterFile.WRLD.worldBlocks:
                        for cellBlock in worldBlock.cellBlocks:
                            checkMasterCellBlockData(cellBlock)
                        # if worldBlock.world.fid in tempCellData['Maps']:
                            # if worldBlock.world.mapPath != tempCellData['Maps'][worldBlock.world.fid]:
                                # cellData['Maps'][worldBlock.world.fid] = tempCellData['Maps'][worldBlock.world.fid]
            tempCellData = {}
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
                # if worldBlock.world.fid in cellData['Maps']:
                    # patchWorlds.setWorld(worldBlock.world)

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
            # if worldBlock.world.fid in cellData['Maps']:
                # if worldBlock.world.mapPath != cellData['Maps'][worldBlock.world.fid]:
                    # print worldBlock.world.mapPath
                    # worldBlock.world.mapPath = cellData['Maps'][worldBlock.world.fid]
                    # print worldBlock.world.mapPath
                    # worldBlock.world.setChanged()
                    # keepWorld = True
            if keepWorld:
                keep(worldBlock.world.fid)

        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        for mod in self.sourceMods:
            log(u'* ' +mod.s)
        log(u'\n=== '+_(u'Cells/Worlds Patched'))
        for srcMod in modInfos.getOrdered(count.keys()):
            log(u'* %s: %d' % (srcMod.s,count[srcMod]))

class CBash_CellImporter(CBash_ImportPatcher):
    """Merges changes to cells (climate, lighting, and water.)"""
    name = _(u'Import Cells')
    text = _(u"Import cells (climate, lighting, and water) from source mods.")
    tip = text
    autoKey = {u'C.Climate', u'C.Light', u'C.Water', u'C.Owner', u'C.Name',
               u'C.RecordFlags', u'C.Music'}  #,u'C.Maps'

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.fid_attr_value = {}
        self.mod_count = {}
        self.tag_attrs = {
            u'C.Climate': ('climate','IsBehaveLikeExterior'),
            u'C.Music': ('musicType',),
            u'C.Name': ('full',),
            u'C.Owner': ('owner','rank','globalVariable','IsPublicPlace'),
            u'C.Water': ('water','waterHeight','IsHasWater'),
            u'C.Light': ('ambientRed','ambientGreen','ambientBlue',
                        'directionalRed','directionalGreen','directionalBlue',
                        'fogRed','fogGreen','fogBlue',
                        'fogNear','fogFar','directionalXY','directionalZ',
                        'directionalFade','fogClip'),
            u'C.RecordFlags': ('flags1',), # Yes seems funky but thats the way it is
            }

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CELLS']

    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        for bashKey in bashTags & self.autoKey:
            attr_value = record.ConflictDetails(self.tag_attrs[bashKey])
            if not ValidateDict(attr_value, self.patchFile):
                mod_skipcount = self.patchFile.patcher_mod_skipcount.setdefault(self.name,{})
                mod_skipcount[modFile.GName] = mod_skipcount.setdefault(modFile.GName, 0) + 1
                continue
            self.fid_attr_value.setdefault(record.fid,{}).update(attr_value)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid

        prev_attr_value = self.fid_attr_value.get(recordId,None)
        if prev_attr_value:
            cur_attr_value = dict((attr,getattr(record,attr)) for attr in prev_attr_value)
            if cur_attr_value != prev_attr_value:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_attr_value.iteritems():
                        setattr(override,attr,value)
                    mod_count = self.mod_count
                    mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        mod_count = self.mod_count
        log.setHeader(u'= ' +self.__class__.name)
        log(u'* '+_(u'Cells/Worlds Patched: %d') % sum(mod_count.values()))
        for srcMod in modInfos.getOrdered(mod_count.keys()):
            log(u'  * %s: %d' % (srcMod.s,mod_count[srcMod]))
        self.mod_count = {}

#------------------------------------------------------------------------------
class GraphicsPatcher(ImportPatcher):
    """Merges changes to graphics (models and icons)."""
    name = _(u'Import Graphics')
    text = _(u"Import graphics (models, icons, etc.) from source mods.")
    tip = text
    autoKey = u'Graphics'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_data = {} #--Names keyed by long fid.
        self.srcClasses = set() #--Record classes actually provided by src mods/files.
        self.sourceMods = self.getConfigChecked()
        self.isActive = len(self.sourceMods) != 0
        self.classestemp = set()
        #--Type Fields
        recAttrs_class = self.recAttrs_class = {}
        recFidAttrs_class = self.recFidAttrs_class = {}
        for recClass in (MreRecord.type_class[x] for x in ('BSGN','LSCR','CLAS','LTEX','REGN')):
            recAttrs_class[recClass] = ('iconPath',)
        for recClass in (MreRecord.type_class[x] for x in ('ACTI','DOOR','FLOR','FURN','GRAS','STAT')):
            recAttrs_class[recClass] = ('model',)
        for recClass in (MreRecord.type_class[x] for x in ('ALCH','AMMO','APPA','BOOK','INGR','KEYM','LIGH','MISC','SGST','SLGM','WEAP','TREE')):
            recAttrs_class[recClass] = ('iconPath','model')
        for recClass in (MreRecord.type_class[x] for x in ('ARMO','CLOT')):
            recAttrs_class[recClass] = ('maleBody','maleWorld','maleIconPath','femaleBody','femaleWorld','femaleIconPath','flags')
        for recClass in (MreRecord.type_class[x] for x in ('CREA',)):
            recAttrs_class[recClass] = ('bodyParts','nift_p')
        for recClass in (MreRecord.type_class[x] for x in ('MGEF',)):
            recAttrs_class[recClass] = ('iconPath','model')
            recFidAttrs_class[recClass] = ('effectShader','enchantEffect','light')
        for recClass in (MreRecord.type_class[x] for x in ('EFSH',)):
            recAttrs_class[recClass] = ('particleTexture','fillTexture','flags','unused1','memSBlend',
                                        'memBlendOp','memZFunc','fillRed','fillGreen','fillBlue','unused2',
                                        'fillAIn','fillAFull','fillAOut','fillAPRatio','fillAAmp','fillAFreq',
                                        'fillAnimSpdU','fillAnimSpdV','edgeOff','edgeRed','edgeGreen',
                                        'edgeBlue','unused3','edgeAIn','edgeAFull','edgeAOut','edgeAPRatio',
                                        'edgeAAmp','edgeAFreq','fillAFRatio','edgeAFRatio','memDBlend',
                                        'partSBlend','partBlendOp','partZFunc','partDBlend','partBUp',
                                        'partBFull','partBDown','partBFRatio','partBPRatio','partLTime',
                                        'partLDelta','partNSpd','partNAcc','partVel1','partVel2','partVel3',
                                        'partAcc1','partAcc2','partAcc3','partKey1','partKey2','partKey1Time',
                                        'partKey2Time','key1Red','key1Green','key1Blue','unused4','key2Red',
                                        'key2Green','key2Blue','unused5','key3Red','key3Green','key3Blue',
                                        'unused6','key1A','key2A','key3A','key1Time','key2Time','key3Time')
        #--Needs Longs
        self.longTypes = {'BSGN', 'LSCR', 'CLAS', 'LTEX', 'REGN', 'ACTI',
                          'DOOR', 'FLOR', 'FURN', 'GRAS', 'STAT', 'ALCH',
                          'AMMO', 'APPA', 'BOOK', 'INGR', 'KEYM', 'LIGH',
                          'MISC', 'SGST', 'SLGM', 'WEAP', 'TREE', 'ARMO',
                          'CLOT', 'CREA', 'MGEF', 'EFSH'}

    def initData(self,progress):
        """Get graphics from source files."""
        if not self.isActive: return
        id_data = self.id_data
        recAttrs_class = self.recAttrs_class
        loadFactory = LoadFactory(False,*recAttrs_class.keys())
        longTypes = self.longTypes & set(x.classType for x in self.recAttrs_class)
        progress.setFull(len(self.sourceMods))
        cachedMasters = {}
        for index,srcMod in enumerate(self.sourceMods):
            temp_id_data = {}
            if srcMod not in modInfos: continue
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            masters = srcInfo.header.masters
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass,recAttrs in recAttrs_class.iteritems():
                if recClass.classType not in srcFile.tops: continue
                self.srcClasses.add(recClass)
                self.classestemp.add(recClass)
                recFidAttrs = self.recFidAttrs_class.get(recClass, None)
                for record in srcFile.tops[recClass.classType].getActiveRecords():
                    fid = mapper(record.fid)
                    if recFidAttrs:
                        attr_fidvalue = dict((attr,record.__getattribute__(attr)) for attr in recFidAttrs)
                        for fidvalue in attr_fidvalue.values():
                            if fidvalue and (fidvalue[0] is None or fidvalue[0] not in self.patchFile.loadSet):
                                #Ignore the record. Another option would be to just ignore the attr_fidvalue result
                                mod_skipcount = self.patchFile.patcher_mod_skipcount.setdefault(self.name,{})
                                mod_skipcount[srcMod] = mod_skipcount.setdefault(srcMod, 0) + 1
                                break
                        else:
                            temp_id_data[fid] = dict((attr,record.__getattribute__(attr)) for attr in recAttrs)
                            temp_id_data[fid].update(attr_fidvalue)
                    else:
                        temp_id_data[fid] = dict((attr,record.__getattribute__(attr)) for attr in recAttrs)
            for master in masters:
                if not master in modInfos: continue # or break filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = modInfos[master]
                    masterFile = ModFile(masterInfo,loadFactory)
                    masterFile.load(True)
                    masterFile.convertToLongFids(longTypes)
                    cachedMasters[master] = masterFile
                mapper = masterFile.getLongMapper()
                for recClass,recAttrs in recAttrs_class.iteritems():
                    if recClass.classType not in masterFile.tops: continue
                    if recClass not in self.classestemp: continue
                    for record in masterFile.tops[recClass.classType].getActiveRecords():
                        fid = mapper(record.fid)
                        if fid not in temp_id_data: continue
                        for attr, value in temp_id_data[fid].iteritems():
                            if value == record.__getattribute__(attr): continue
                            else:
                                if fid not in id_data: id_data[fid] = dict()
                                try:
                                    id_data[fid][attr] = temp_id_data[fid][attr]
                                except KeyError:
                                    id_data[fid].setdefault(attr,value)
            progress.plus()
        temp_id_data = None
        self.longTypes = self.longTypes & set(x.classType for x in self.srcClasses)
        self.isActive = bool(self.srcClasses)

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
            for record in modFile.tops[type].records:
                fid = record.fid
                if fid not in id_data: continue
                for attr,value in id_data[fid].iteritems():
                    if isinstance(record.__getattribute__(attr),basestring) and isinstance(value,basestring):
                        if record.__getattribute__(attr).lower() != value.lower():
                            break
                        continue
                    elif attr == 'model':
                        try:
                            if record.__getattribute__(attr).modPath.lower() != value.modPath.lower():
                                break
                            continue
                        except:
                            break #assume they are not equal (ie they aren't __both__ NONE)
                    if record.__getattribute__(attr) != value:
                        break
                else:
                    continue
                for attr,value in id_data[fid].iteritems():
                    record.__setattr__(attr,value)
                keep(fid)
                type_count[type] += 1
        id_data = None
        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        for mod in self.sourceMods:
            log(u'* '+mod.s)
        log(u'\n=== '+_(u'Modified Records'))
        for type,count in sorted(type_count.iteritems()):
            if count: log(u'* %s: %d' % (type,count))

class CBash_GraphicsPatcher(CBash_ImportPatcher):
    """Merges changes to graphics (models and icons)."""
    name = _(u'Import Graphics')
    text = _(u"Import graphics (models, icons, etc.) from source mods.")
    tip = text
    autoKey = {u'Graphics'}

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.fid_attr_value = {}
        self.class_mod_count = {}
        class_attrs = self.class_attrs = {}
        model = ('modPath','modb','modt_p')
        icon = ('iconPath',)
        class_attrs['BSGN'] = icon
        class_attrs['LSCR'] = icon
        class_attrs['CLAS'] = icon
        class_attrs['LTEX'] = icon
        class_attrs['REGN'] = icon
        class_attrs['ACTI'] = model
        class_attrs['DOOR'] = model
        class_attrs['FLOR'] = model
        class_attrs['FURN'] = model
        class_attrs['GRAS'] = model
        class_attrs['STAT'] = model
        class_attrs['ALCH'] = icon + model
        class_attrs['AMMO'] = icon + model
        class_attrs['APPA'] = icon + model
        class_attrs['BOOK'] = icon + model
        class_attrs['INGR'] = icon + model
        class_attrs['KEYM'] = icon + model
        class_attrs['LIGH'] = icon + model
        class_attrs['MISC'] = icon + model
        class_attrs['SGST'] = icon + model
        class_attrs['SLGM'] = icon + model
        class_attrs['WEAP'] = icon + model
        class_attrs['TREE'] = icon + model

        class_attrs['ARMO'] = ('maleBody_list',
                               'maleWorld_list',
                               'maleIconPath',
                               'femaleBody_list',
                               'femaleWorld_list',
                               'femaleIconPath', 'flags')
        class_attrs['CLOT'] = class_attrs['ARMO']

        class_attrs['CREA'] = ('bodyParts', 'nift_p')
        class_attrs['MGEF'] = icon + model + ('effectShader','enchantEffect','light')
        class_attrs['EFSH'] = ('fillTexturePath','particleTexturePath','flags','memSBlend','memBlendOp',
                               'memZFunc','fillRed','fillGreen','fillBlue','fillAIn','fillAFull',
                               'fillAOut','fillAPRatio','fillAAmp','fillAFreq','fillAnimSpdU',
                               'fillAnimSpdV','edgeOff','edgeRed','edgeGreen','edgeBlue','edgeAIn',
                               'edgeAFull','edgeAOut','edgeAPRatio','edgeAAmp','edgeAFreq',
                               'fillAFRatio','edgeAFRatio','memDBlend','partSBlend','partBlendOp',
                               'partZFunc','partDBlend','partBUp','partBFull','partBDown',
                               'partBFRatio','partBPRatio','partLTime','partLDelta','partNSpd',
                               'partNAcc','partVel1','partVel2','partVel3','partAcc1','partAcc2',
                               'partAcc3','partKey1','partKey2','partKey1Time','partKey2Time',
                               'key1Red','key1Green','key1Blue','key2Red','key2Green','key2Blue',
                               'key3Red','key3Green','key3Blue','key1A','key2A','key3A',
                               'key1Time','key2Time','key3Time')

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['BSGN','LSCR','CLAS','LTEX','REGN','ACTI','DOOR','FLOR',
                'FURN','GRAS','STAT','ALCH','AMMO','APPA','BOOK','INGR',
                'KEYM','LIGH','MISC','SGST','SLGM','WEAP','TREE','ARMO',
                'CLOT','CREA','MGEF','EFSH']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        attr_value = record.ConflictDetails(self.class_attrs[record._Type])
        if not ValidateDict(attr_value, self.patchFile):
            mod_skipcount = self.patchFile.patcher_mod_skipcount.setdefault(self.name,{})
            mod_skipcount[modFile.GName] = mod_skipcount.setdefault(modFile.GName, 0) + 1
            return
        self.fid_attr_value.setdefault(record.fid,{}).update(attr_value)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)

        prev_attr_value = self.fid_attr_value.get(record.fid,None)
        if prev_attr_value:
            cur_attr_value = dict((attr,getattr(record,attr)) for attr in prev_attr_value)
            if cur_attr_value != prev_attr_value:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_attr_value.iteritems():
                        setattr(override,attr,value)
                    class_mod_count = self.class_mod_count
                    class_mod_count.setdefault(record._Type,{})[modFile.GName] = class_mod_count.setdefault(record._Type,{}).get(modFile.GName,0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        class_mod_count = self.class_mod_count
        log.setHeader(u'= ' +self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        for mod in self.srcs:
            log(u'* '+mod.s)
        log(u'\n=== '+_(u'Modified Records'))
        for type in class_mod_count.keys():
            log(u'* '+_(u'Modified %s Records: %d') % (type,sum(class_mod_count[type].values())))
            for srcMod in modInfos.getOrdered(class_mod_count[type].keys()):
                log(u'  * %s: %d' % (srcMod.s,class_mod_count[type][srcMod]))
        self.class_mod_count = {}

#------------------------------------------------------------------------------
class ActorImporter(ImportPatcher):
    """Merges changes to actors."""
    name = _(u'Import Actors')
    text = _(u"Import Actor components from source mods.")
    tip = text
    autoKey = (u'Actors.AIData', u'Actors.Stats', u'Actors.ACBS', u'NPC.Class', u'Actors.CombatStyle', u'Creatures.Blood', u'NPC.Race', u'Actors.Skeleton')

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_data = {} #--Names keyed by long fid.
        self.srcClasses = set() #--Record classes actually provided by src mods/files.
        self.sourceMods = self.getConfigChecked()
        self.isActive = len(self.sourceMods) != 0
        self.classestemp = set()
        #--Type Fields
        recAttrs_class = self.recAttrs_class = {}
        self.actorClasses = (MreRecord.type_class['NPC_'],MreRecord.type_class['CREA'])
        for recClass in (MreRecord.type_class[x] for x in ('NPC_',)):
            self.recAttrs_class[recClass] = {
                u'Actors.AIData': ('aggression','confidence','energyLevel','responsibility','services','trainSkill','trainLevel'),
                u'Actors.Stats': ('skills','health','attributes'),
                u'Actors.ACBS': (('baseSpell','fatigue','level','calcMin','calcMax','flags.autoCalc','flags.pcLevelOffset'),
                                'barterGold','flags.female','flags.essential','flags.respawn','flags.noLowLevel',
                                'flags.noRumors','flags.summonable','flags.noPersuasion','flags.canCorpseCheck',
                                ),
                #u'Actors.ACBS': ('baseSpell','fatigue','barterGold','level','calcMin','calcMax','flags'),
                u'NPC.Class': ('iclass',),
                u'NPC.Race': ('race',),
                u'Actors.CombatStyle': ('combatStyle',),
                u'Creatures.Blood': (),
                u'Actors.Skeleton': ('model',),
                }
        for recClass in (MreRecord.type_class[x] for x in ('CREA',)):
            self.recAttrs_class[recClass] = {
                u'Actors.AIData': ('aggression','confidence','energyLevel','responsibility','services','trainSkill','trainLevel'),
                u'Actors.Stats': ('combat','magic','stealth','soul','health','attackDamage','strength','intelligence','willpower','agility','speed','endurance','personality','luck'),
                u'Actors.ACBS': (('baseSpell','fatigue','level','calcMin','calcMax','flags.pcLevelOffset',),
                                'barterGold','flags.biped','flags.essential','flags.weaponAndShield',
                                'flags.respawn','flags.swims','flags.flies','flags.walks','flags.noLowLevel',
                                'flags.noBloodSpray','flags.noBloodDecal','flags.noHead','flags.noRightArm',
                                'flags.noLeftArm','flags.noCombatInWater','flags.noShadow','flags.noCorpseCheck',
                                ),
                #u'Actors.ACBS': ('baseSpell','fatigue','barterGold','level','calcMin','calcMax','flags'),
                u'NPC.Class': (),
                u'NPC.Race': (),
                u'Actors.CombatStyle': ('combatStyle',),
                u'Creatures.Blood': ('bloodSprayPath','bloodDecalPath'),
                u'Actors.Skeleton': ('model',),
                }
        #--Needs Longs
        self.longTypes = {'CREA', 'NPC_'}

    def initData(self,progress):
        """Get graphics from source files."""
        if not self.isActive: return
        id_data = self.id_data
        recAttrs_class = self.recAttrs_class
        loadFactory = LoadFactory(False,MreRecord.type_class['NPC_'],
                                        MreRecord.type_class['CREA'])
        longTypes = self.longTypes & set(x.classType for x in self.actorClasses)
        progress.setFull(len(self.sourceMods))
        cachedMasters = {}
        for index,srcMod in enumerate(self.sourceMods):
            temp_id_data = {}
            if srcMod not in modInfos: continue
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            masters = srcInfo.header.masters
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for actorClass in self.actorClasses:
                if actorClass.classType not in srcFile.tops: continue
                self.srcClasses.add(actorClass)
                self.classestemp.add(actorClass)
                attrs = set(reduce(operator.add, (self.recAttrs_class[actorClass][bashKey] for bashKey in srcInfo.getBashTags() if bashKey in self.recAttrs_class[actorClass])))
                for record in srcFile.tops[actorClass.classType].getActiveRecords():
                    fid = mapper(record.fid)
                    temp_id_data[fid] = dict()
                    for attr in attrs:
                        if isinstance(attr,basestring):
                            temp_id_data[fid][attr] = reduce(getattr, attr.split('.'), record)
                        elif isinstance(attr,(list,tuple,set)):
                            temp_id_data[fid][attr] = dict((subattr,reduce(getattr, subattr.split('.'), record)) for subattr in attr)
            for master in masters:
                if not master in modInfos: continue # or break filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = modInfos[master]
                    masterFile = ModFile(masterInfo,loadFactory)
                    masterFile.load(True)
                    masterFile.convertToLongFids(longTypes)
                    cachedMasters[master] = masterFile
                mapper = masterFile.getLongMapper()
                for actorClass in self.actorClasses:
                    if actorClass.classType not in masterFile.tops: continue
                    if actorClass not in self.classestemp: continue
                    for record in masterFile.tops[actorClass.classType].getActiveRecords():
                        fid = mapper(record.fid)
                        if fid not in temp_id_data: continue
                        for attr, value in temp_id_data[fid].iteritems():
                            if isinstance(attr,basestring):
                                if value == reduce(getattr, attr.split('.'), record): continue
                                else:
                                    if fid not in id_data: id_data[fid] = dict()
                                    try:
                                        id_data[fid][attr] = temp_id_data[fid][attr]
                                    except KeyError:
                                        id_data[fid].setdefault(attr,value)
                            elif isinstance(attr,(list,tuple,set)):
                                temp_values = {}
                                keep = False
                                for subattr in attr:
                                    if value[subattr] != reduce(getattr, subattr.split('.'), record):
                                        keep = True
                                    temp_values[subattr] = value[subattr]
                                if keep:
                                    id_data.setdefault(fid,{})
                                    id_data[fid].update(temp_values)
            progress.plus()
        temp_id_data = None
        self.longTypes = self.longTypes & set(x.classType for x in self.srcClasses)
        self.isActive = bool(self.srcClasses)

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
                    if reduce(getattr,attr.split('.'),record) != value:
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
            for record in modFile.tops[type].records:
                fid = record.fid
                if fid not in id_data: continue
                for attr,value in id_data[fid].iteritems():
                    if reduce(getattr,attr.split('.'),record) != value:
                        break
                else:
                    continue
                for attr,value in id_data[fid].iteritems():
                    setattr(reduce(getattr,attr.split('.')[:-1],record),attr.split('.')[-1], value)
                keep(fid)
                type_count[type] += 1
        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        for mod in self.sourceMods:
            log(u'* '+mod.s)
        log(u'\n=== '+_(u'Modified Records'))
        for type,count in sorted(type_count.iteritems()):
            if count: log(u'* %s: %d' % (type,count))

class CBash_ActorImporter(CBash_ImportPatcher):
    """Merges changes to actors."""
    name = _(u'Import Actors')
    text = _(u"Import Actor components from source mods.")
    tip = text
    autoKey = {u'Actors.AIData', u'Actors.Stats', u'Actors.ACBS', u'NPC.Class',
               u'Actors.CombatStyle', u'Creatures.Blood', u'NPC.Race',
               u'Actors.Skeleton'}

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.fid_attr_value = {}
        self.class_mod_count = {}
        class_tag_attrs = self.class_tag_attrs = {}
        class_tag_attrs['NPC_'] = {
                u'Actors.AIData': ('aggression','confidence','energyLevel','responsibility','services','trainSkill','trainLevel'),
                u'Actors.Stats': ('armorer','athletics','blade','block','blunt','h2h','heavyArmor','alchemy',
                                 'alteration','conjuration','destruction','illusion','mysticism','restoration',
                                 'acrobatics','lightArmor','marksman','mercantile','security','sneak','speechcraft',
                                 'health',
                                 'strength','intelligence','willpower','agility','speed','endurance','personality','luck',),
                u'Actors.ACBS': (('baseSpell','fatigue','level','calcMin','calcMax','IsPCLevelOffset','IsAutoCalc',),
                                'barterGold','IsFemale','IsEssential','IsRespawn','IsNoLowLevel','IsNoRumors',
                                'IsSummonable','IsNoPersuasion','IsCanCorpseCheck',
                                ),
                u'NPC.Class': ('iclass',),
                u'NPC.Race': ('race',),
                u'Actors.CombatStyle': ('combatStyle',),
                u'Creatures.Blood': (),
                u'Actors.Skeleton': ('modPath','modb','modt_p'),
                }
        class_tag_attrs['CREA'] = {
                u'Actors.AIData': ('aggression','confidence','energyLevel','responsibility','services','trainSkill','trainLevel'),
                u'Actors.Stats': ('combat','magic','stealth','soulType','health','attackDamage','strength','intelligence','willpower',
                                 'agility','speed','endurance','personality','luck'),
                u'Actors.ACBS': (('baseSpell','fatigue','level','calcMin','calcMax','IsPCLevelOffset',),
                                'barterGold','IsBiped','IsEssential','IsWeaponAndShield','IsRespawn',
                                'IsSwims','IsFlies','IsWalks','IsNoLowLevel','IsNoBloodSpray','IsNoBloodDecal',
                                'IsNoHead','IsNoRightArm','IsNoLeftArm','IsNoCombatInWater','IsNoShadow',
                                'IsNoCorpseCheck',
                                ),
                u'NPC.Class': (),
                u'NPC.Race': (),
                u'Actors.CombatStyle': ('combatStyle',),
                u'Creatures.Blood': ('bloodSprayPath','bloodDecalPath'),
                u'Actors.Skeleton': ('modPath','modb','modt_p',),
                }

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CREA','NPC_']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        if modFile.GName == record.fid[0]: return
        for bashKey in bashTags & self.autoKey:
            attrs = self.class_tag_attrs[record._Type].get(bashKey, None)
            if attrs:
                attr_value = record.ConflictDetails(attrs)
                if not ValidateDict(attr_value, self.patchFile):
                    mod_skipcount = self.patchFile.patcher_mod_skipcount.setdefault(self.name,{})
                    mod_skipcount[modFile.GName] = mod_skipcount.setdefault(modFile.GName, 0) + 1
                    continue
                self.fid_attr_value.setdefault(record.fid,{}).update(attr_value)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        prev_attr_value = self.fid_attr_value.get(recordId,None)
        if prev_attr_value:
            cur_attr_value = dict((attr,getattr(record,attr)) for attr in prev_attr_value)
            if cur_attr_value != prev_attr_value:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_attr_value.iteritems():
                        setattr(override,attr,value)
                    class_mod_count = self.class_mod_count
                    class_mod_count.setdefault(record._Type,{})[modFile.GName] = class_mod_count.setdefault(record._Type,{}).get(modFile.GName,0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        class_mod_count = self.class_mod_count
        log.setHeader(u'= ' +self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        for mod in self.srcs:
            log(u'* '+mod.s)
        log(u'\n=== '+_(u'Modified Records'))
        for type in class_mod_count.keys():
            log(u'* '+_(u'Modified %s Records: %d') % (type,sum(class_mod_count[type].values())))
            for srcMod in modInfos.getOrdered(class_mod_count[type].keys()):
                log(u'  * %s: %d' % (srcMod.s,class_mod_count[type][srcMod]))
        self.class_mod_count = {}

#------------------------------------------------------------------------------
class KFFZPatcher(ImportPatcher):
    """Merges changes to actor animation lists."""
    name = _(u'Import Actors: Animations')
    text = _(u"Import Actor animations from source mods.")
    tip = text
    autoKey = u'Actors.Anims'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_data = {} #--Names keyed by long fid.
        self.srcClasses = set() #--Record classes actually provided by src mods/files.
        self.sourceMods = self.getConfigChecked()
        self.isActive = len(self.sourceMods) != 0
        self.classestemp = set()
        #--Type Fields
        recAttrs_class = self.recAttrs_class = {}
        for recClass in (MreRecord.type_class[x] for x in ('CREA','NPC_')):
            recAttrs_class[recClass] = ('animations',)
        #--Needs Longs
        self.longTypes = {'CREA', 'NPC_'}

    def initData(self,progress):
        """Get actor animation lists from source files."""
        if not self.isActive: return
        id_data = self.id_data
        recAttrs_class = self.recAttrs_class
        loadFactory = LoadFactory(False,*recAttrs_class.keys())
        longTypes = self.longTypes & set(x.classType for x in self.recAttrs_class)
        progress.setFull(len(self.sourceMods))
        cachedMasters = {}
        for index,srcMod in enumerate(self.sourceMods):
            temp_id_data = {}
            if srcMod not in modInfos: continue
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            masters = srcInfo.header.masters
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass,recAttrs in recAttrs_class.iteritems():
                if recClass.classType not in srcFile.tops: continue
                self.srcClasses.add(recClass)
                self.classestemp.add(recClass)
                for record in srcFile.tops[recClass.classType].getActiveRecords():
                    fid = mapper(record.fid)
                    temp_id_data[fid] = dict((attr,record.__getattribute__(attr)) for attr in recAttrs)
            for master in masters:
                if not master in modInfos: continue # or break filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = modInfos[master]
                    masterFile = ModFile(masterInfo,loadFactory)
                    masterFile.load(True)
                    masterFile.convertToLongFids(longTypes)
                    cachedMasters[master] = masterFile
                mapper = masterFile.getLongMapper()
                for recClass,recAttrs in recAttrs_class.iteritems():
                    if recClass.classType not in masterFile.tops: continue
                    if recClass not in self.classestemp: continue
                    for record in masterFile.tops[recClass.classType].getActiveRecords():
                        fid = mapper(record.fid)
                        if fid not in temp_id_data: continue
                        for attr, value in temp_id_data[fid].iteritems():
                            if value == record.__getattribute__(attr): continue
                            else:
                                if fid not in id_data: id_data[fid] = dict()
                                try:
                                    id_data[fid][attr] = temp_id_data[fid][attr]
                                except KeyError:
                                    id_data[fid].setdefault(attr,value)
            progress.plus()
        temp_id_data = None
        self.longTypes = self.longTypes & set(x.classType for x in self.srcClasses)
        self.isActive = bool(self.srcClasses)

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
        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        for mod in self.sourceMods:
            log(u'* ' +mod.s)
        log(u'\n=== '+_(u'Modified Records'))
        for type,count in sorted(type_count.iteritems()):
            if count: log(u'* %s: %d' % (type,count))

class CBash_KFFZPatcher(CBash_ImportPatcher):
    """Merges changes to actor animations."""
    name = _(u'Import Actors: Animations')
    text = _(u"Import Actor animations from source mods.")
    tip = text
    autoKey = {u'Actors.Anims'}

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.id_animations = {}
        self.mod_count = {}

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CREA','NPC_']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        animations = self.id_animations.setdefault(record.fid,[])
        animations.extend([anim for anim in record.animations if anim not in animations])

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        if recordId in self.id_animations and record.animations != self.id_animations[recordId]:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.animations = self.id_animations[recordId]
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        mod_count = self.mod_count
        log.setHeader(u'= ' +self.__class__.name)
        log(u'* '+_(u'Imported Animations: %d') % sum(mod_count.values()))
        for srcMod in modInfos.getOrdered(mod_count.keys()):
            log(u'  * %s: %d' % (srcMod.s,mod_count[srcMod]))
        self.mod_count = {}

#------------------------------------------------------------------------------
class NPCAIPackagePatcher(ImportPatcher):
    """Merges changes to the AI Packages of Actors."""
    name = _(u'Import Actors: AI Packages')
    text = _(u"Import Actor AI Package links from source mods.")
    tip = text
    autoKey = (u'Actors.AIPackages',u'Actors.AIPackagesForceAdd')

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.srcMods = self.getConfigChecked()
        self.isActive = len(self.srcMods) != 0
        self.data = {}
        self.longTypes = {'CREA', 'NPC_'}

    def initData(self,progress):
        """Get data from source files."""
        if not self.isActive: return
        longTypes = self.longTypes
        loadFactory = LoadFactory(False,MreRecord.type_class['CREA'],
                                        MreRecord.type_class['NPC_'])
        progress.setFull(len(self.srcMods))
        cachedMasters = {}
        data = self.data
        for index,srcMod in enumerate(self.srcMods):
            tempData = {}
            if srcMod not in modInfos: continue
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            masters = srcInfo.header.masters
            bashTags = srcInfo.getBashTags()
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass in (MreRecord.type_class[x] for x in ('NPC_','CREA')):
                if recClass.classType not in srcFile.tops: continue
                for record in srcFile.tops[recClass.classType].getActiveRecords():
                    fid = mapper(record.fid)
                    tempData[fid] = list(record.aiPackages)
            for master in reversed(masters):
                if not master in modInfos: continue # or break filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = modInfos[master]
                    masterFile = ModFile(masterInfo,loadFactory)
                    masterFile.load(True)
                    masterFile.convertToLongFids(longTypes)
                    cachedMasters[master] = masterFile
                mapper = masterFile.getLongMapper()
                for block in (MreRecord.type_class[x] for x in ('NPC_','CREA')):
                    if block.classType not in srcFile.tops: continue
                    if block.classType not in masterFile.tops: continue
                    for record in masterFile.tops[block.classType].getActiveRecords():
                        fid = mapper(record.fid)
                        if not fid in tempData: continue
                        if record.aiPackages == tempData[fid] and not u'Actors.AIPackagesForceAdd' in bashTags:
                            # if subrecord is identical to the last master then we don't care about older masters.
                            del tempData[fid]
                            continue
                        if fid in data:
                            if tempData[fid] == data[fid]['merged']: continue
                        recordData = {'deleted':[],'merged':tempData[fid]}
                        for pkg in list(record.aiPackages):
                            if not pkg in tempData[fid]:
                                recordData['deleted'].append(pkg)
                        if not fid in data:
                            data[fid] = recordData
                        else:
                            for pkg in recordData['deleted']:
                                if pkg in data[fid]['merged']:
                                    data[fid]['merged'].remove(pkg)
                                data[fid]['deleted'].append(pkg)
                            if data[fid]['merged'] == []:
                                for pkg in recordData['merged']:
                                    if pkg in data[fid]['deleted'] and not u'Actors.AIPackagesForceAdd' in bashTags: continue
                                    data[fid]['merged'].append(pkg)
                                continue
                            for index, pkg in enumerate(recordData['merged']):
                                if not pkg in data[fid]['merged']: # so needs to be added... (unless deleted that is)
                                    # find the correct position to add and add.
                                    if pkg in data[fid]['deleted'] and not u'Actors.AIPackagesForceAdd' in bashTags: continue #previously deleted
                                    if index == 0:
                                        data[fid]['merged'].insert(0,pkg) #insert as first item
                                    elif index == (len(recordData['merged'])-1):
                                        data[fid]['merged'].append(pkg) #insert as last item
                                    else: #figure out a good spot to insert it based on next or last recognized item (ugly ugly ugly)
                                        i = index - 1
                                        while i >= 0:
                                            if recordData['merged'][i] in data[fid]['merged']:
                                                slot = data[fid]['merged'].index(recordData['merged'][i])+1
                                                data[fid]['merged'].insert(slot, pkg)
                                                break
                                            i -= 1
                                        else:
                                            i = index + 1
                                            while i != len(recordData['merged']):
                                                if recordData['merged'][i] in data[fid]['merged']:
                                                    slot = data[fid]['merged'].index(recordData['merged'][i])
                                                    data[fid]['merged'].insert(slot, pkg)
                                                    break
                                                i += 1
                                    continue # Done with this package
                                elif index == data[fid]['merged'].index(pkg) or (len(recordData['merged'])-index) == (len(data[fid]['merged'])-data[fid]['merged'].index(pkg)): continue #pkg same in both lists.
                                else: #this import is later loading so we'll assume it is better order
                                    data[fid]['merged'].remove(pkg)
                                    if index == 0:
                                        data[fid]['merged'].insert(0,pkg) #insert as first item
                                    elif index == (len(recordData['merged'])-1):
                                        data[fid]['merged'].append(pkg) #insert as last item
                                    else:
                                        i = index - 1
                                        while i >= 0:
                                            if recordData['merged'][i] in data[fid]['merged']:
                                                slot = data[fid]['merged'].index(recordData['merged'][i]) + 1
                                                data[fid]['merged'].insert(slot, pkg)
                                                break
                                            i -= 1
                                        else:
                                            i = index + 1
                                            while i != len(recordData['merged']):
                                                if recordData['merged'][i] in data[fid]['merged']:
                                                    slot = data[fid]['merged'].index(recordData['merged'][i])
                                                    data[fid]['merged'].insert(slot, pkg)
                                                    break
                                                i += 1
            progress.plus()

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('NPC_','CREA',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('NPC_','CREA',) if self.isActive else ()

    def scanModFile(self, modFile, progress):
        """Add record from modFile."""
        if not self.isActive: return
        data = self.data
        mapper = modFile.getLongMapper()
        modName = modFile.fileInfo.name
        for type in ('NPC_','CREA'):
            patchBlock = getattr(self.patchFile,type)
            for record in getattr(modFile,type).getActiveRecords():
                fid = mapper(record.fid)
                if fid in data:
                    if list(record.aiPackages) != data[fid]['merged']:
                        patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress):
        """Applies delta to patchfile."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        data = self.data
        mod_count = {}
        for type in ('NPC_','CREA'):
            for record in getattr(self.patchFile,type).records:
                fid = record.fid
                if not fid in data: continue
                changed = False
                if record.aiPackages != data[fid]['merged']:
                    record.aiPackages = data[fid]['merged']
                    changed = True
                if changed:
                    keep(record.fid)
                    mod = record.fid[0]
                    mod_count[mod] = mod_count.get(mod,0) + 1
        #--Log
        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        for mod in self.srcMods:
            log(u'* '+mod.s)
        log(u'\n=== '+_(u'AI Package Lists Changed: %d') % sum(mod_count.values()))
        for mod in modInfos.getOrdered(mod_count):
            log(u'* %s: %3d' % (mod.s,mod_count[mod]))

class CBash_NPCAIPackagePatcher(CBash_ImportPatcher):
    """Merges changes to the AI Packages of Actors."""
    name = _(u'Import Actors: AI Packages')
    text = _(u"Import Actor AI Package links from source mods.")
    tip = text
    autoKey = {u'Actors.AIPackages', u'Actors.AIPackagesForceAdd'}
    scanRequiresChecked = False

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.previousPackages = {}
        self.mergedPackageList = {}
        self.mod_count = {}

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CREA','NPC_']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        aiPackages = record.aiPackages
        if not ValidateList(aiPackages, self.patchFile):
            mod_skipcount = self.patchFile.patcher_mod_skipcount.setdefault(self.name,{})
            mod_skipcount[modFile.GName] = mod_skipcount.setdefault(modFile.GName, 0) + 1
            return

        recordId = record.fid
        newPackages = bolt.MemorySet(aiPackages)
        self.previousPackages.setdefault(recordId,{})[modFile.GName] = newPackages

        if modFile.GName in self.srcs:
            masterPackages = self.previousPackages[recordId].get(recordId[0],None)
            # can't just do "not masterPackages ^ newPackages" since the order may have changed
            if masterPackages is not None and masterPackages == newPackages: return
            mergedPackages = self.mergedPackageList.setdefault(recordId,newPackages)
            if newPackages == mergedPackages: return #same as the current list, just skip.
            for master in reversed(modFile.TES4.masters):
                masterPath = GPath(master)
                masterPackages = self.previousPackages[recordId].get(masterPath,None)
                if masterPackages is None: continue

                # Get differences from master
                added = newPackages - masterPackages
                sameButReordered = masterPackages & newPackages
                prevDeleted = bolt.MemorySet(mergedPackages.discarded)
                newDeleted = masterPackages - newPackages

                # Merge those changes into mergedPackages
                mergedPackages |= newPackages
                if u'Actors.AIPackagesForceAdd' not in bashTags:
                    prevDeleted -= newPackages
                prevDeleted |= newDeleted
                mergedPackages -= prevDeleted
                self.mergedPackageList[recordId] = mergedPackages
                break

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        if recordId in self.mergedPackageList:
            mergedPackages = list(self.mergedPackageList[recordId])
            if record.aiPackages != mergedPackages:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    try:
                        override.aiPackages = mergedPackages
                    except:
                        newMergedPackages = []
                        for pkg in mergedPackages:
                            if not pkg[0] is None: newMergedPackages.append(pkg)
                        override.aiPackages = newMergedPackages
                    mod_count = self.mod_count
                    mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        mod_count = self.mod_count
        log.setHeader(u'= ' +self.__class__.name)
        log(u'* '+_(u'AI Package Lists Changed: %d') % sum(mod_count.values()))
        for srcMod in modInfos.getOrdered(mod_count.keys()):
            log(u'  * %s: %d' % (srcMod.s,mod_count[srcMod]))
        self.mod_count = {}

#------------------------------------------------------------------------------
class DeathItemPatcher(ImportPatcher):
    """Merges changes to actor death items."""
    name = _(u'Import Actors: Death Items')
    text = _(u"Import Actor death items from source mods.")
    tip = text
    autoKey = u'Actors.DeathItem'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_data = {} #--Names keyed by long fid.
        self.srcClasses = set() #--Record classes actually provided by src
        # mods/files.
        self.sourceMods = self.getConfigChecked()
        self.isActive = len(self.sourceMods) != 0
        #--Type Fields
        recAttrs_class = self.recAttrs_class = {}
        for recClass in (MreRecord.type_class[x] for x in ('CREA','NPC_')):
            recAttrs_class[recClass] = ('deathItem',)
        #--Needs Longs
        self.longTypes = {'CREA', 'NPC_'}

    def initData(self,progress):
        """Get actor death items from source files."""
        if not self.isActive: return
        self.classestemp = set()
        id_data = self.id_data
        recAttrs_class = self.recAttrs_class
        loadFactory = LoadFactory(False,*recAttrs_class.keys())
        longTypes = self.longTypes & set(x.classType for x in self.recAttrs_class)
        progress.setFull(len(self.sourceMods))
        cachedMasters = {}
        for index,srcMod in enumerate(self.sourceMods):
            temp_id_data = {}
            if srcMod not in modInfos: continue
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            masters = srcInfo.header.masters
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass,recAttrs in recAttrs_class.iteritems():
                if recClass.classType not in srcFile.tops: continue
                self.srcClasses.add(recClass)
                self.classestemp.add(recClass)
                for record in srcFile.tops[recClass.classType].getActiveRecords():
                    fid = mapper(record.fid)
                    temp_id_data[fid] = dict((attr,record.__getattribute__(attr)) for attr in recAttrs)
            for master in masters:
                if not master in modInfos: continue # or break filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = modInfos[master]
                    masterFile = ModFile(masterInfo,loadFactory)
                    masterFile.load(True)
                    masterFile.convertToLongFids(longTypes)
                    cachedMasters[master] = masterFile
                mapper = masterFile.getLongMapper()
                for recClass,recAttrs in recAttrs_class.iteritems():
                    if recClass.classType not in masterFile.tops: continue
                    if recClass not in self.classestemp: continue
                    for record in masterFile.tops[recClass.classType].getActiveRecords():
                        fid = mapper(record.fid)
                        if fid not in temp_id_data: continue
                        for attr, value in temp_id_data[fid].iteritems():
                            if value == record.__getattribute__(attr): continue
                            else:
                                if fid not in id_data: id_data[fid] = dict()
                                try:
                                    id_data[fid][attr] = temp_id_data[fid][attr]
                                except KeyError:
                                    id_data[fid].setdefault(attr,value)
            progress.plus()
        temp_id_data = None
        self.longTypes = self.longTypes & set(x.classType for x in self.srcClasses)
        self.isActive = bool(self.srcClasses)

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
        """Merge last version of record with patched actor death item as needed."""
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
        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        for mod in self.sourceMods:
            log(u'* ' + mod.s)
        log(u'\n=== '+_(u'Modified Records'))
        for type,count in sorted(type_count.items()):
            if count: log(u'* %s: %d' % (type,count))

class CBash_DeathItemPatcher(CBash_ImportPatcher):
    """Imports actor death items."""
    name = _(u'Import Actors: Death Items')
    text = _(u"Import Actor death items from source mods.")
    tip = text
    autoKey = {u'Actors.DeathItem'}

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.id_deathItem = {}
        self.mod_count = {}

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CREA','NPC_']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        deathitem = record.ConflictDetails(('deathItem',))
        if deathitem:
            if deathitem['deathItem'].ValidateFormID(self.patchFile):
                self.id_deathItem[record.fid] = deathitem['deathItem']
            else:
                #Ignore the record. Another option would be to just ignore the invalid formIDs
                mod_skipcount = self.patchFile.patcher_mod_skipcount.setdefault(self.name,{})
                mod_skipcount[modFile.GName] = mod_skipcount.setdefault(modFile.GName, 0) + 1

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        if recordId in self.id_deathItem and record.deathItem != self.id_deathItem[recordId]:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.deathItem = self.id_deathItem[recordId]
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        mod_count = self.mod_count
        log.setHeader(u'= ' +self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        for mod in self.srcs:
            log(u'* '+mod.s)
        log(u'* '+_(u'Imported Death Items: %d') % sum(mod_count.values()))
        for srcMod in modInfos.getOrdered(mod_count.keys()):
            log(u'  * %s: %d' % (srcMod.s,mod_count[srcMod]))
        self.mod_count = {}

#------------------------------------------------------------------------------
from patcher.oblivion.utilities import ActorFactions, CBash_ActorFactions

class ImportFactions(ImportPatcher):
    """Import factions to creatures and NPCs."""
    name = _(u'Import Factions')
    text = _(u"Import factions from source mods/files.")
    autoKey = u'Factions'

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
            patchesList = getPatchesList()
            if reModExt.search(srcFile.s):
                if srcPath not in modInfos: continue
                srcInfo = modInfos[GPath(srcFile)]
                actorFactions.readFromMod(srcInfo)
            else:
                if srcPath not in patchesList: continue
                actorFactions.readFromText(getPatchesPath(srcFile))
            progress.plus()
        #--Finish
        id_factions= self.id_factions
        for type,aFid_factions in actorFactions.type_id_factions.iteritems():
            if type not in ('CREA','NPC_'): continue
            self.activeTypes.append(type)
            for longid,factions in aFid_factions.iteritems():
                self.id_factions[longid] = factions
        self.isActive = bool(self.activeTypes)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return tuple(self.activeTypes) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return tuple(self.activeTypes) if self.isActive else()

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
        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods/Files'))
        for file in self.srcFiles:
            log(u'* '+file.s)
        log(u'\n=== '+_(u'Refactioned Actors'))
        for type,count in sorted(type_count.iteritems()):
            if count: log(u'* %s: %d' % (type,count))

class CBash_ImportFactions(CBash_ImportPatcher):
    """Import factions to creatures and NPCs."""
    name = _(u'Import Factions')
    text = _(u"Import factions from source mods/files.")
    autoKey = {u'Factions'}

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.id_factions = {}
        self.csvId_factions = {}
        self.class_mod_count = {}

    def initData(self,group_patchers,progress):
        """Compiles material, i.e. reads source text, esp's, etc. as necessary."""
        if not self.isActive: return
        CBash_ImportPatcher.initData(self,group_patchers,progress)
        actorFactions = CBash_ActorFactions(aliases=self.patchFile.aliases)
        progress.setFull(len(self.srcs))
        patchesList = getPatchesList()
        for srcFile in self.srcs:
            srcPath = GPath(srcFile)
            if not reModExt.search(srcFile.s):
                if srcPath not in patchesList: continue
                actorFactions.readFromText(getPatchesPath(srcFile))
            progress.plus()
        #--Finish
        csvId_factions = self.csvId_factions
        for group,aFid_factions in actorFactions.group_fid_factions.iteritems():
            if group not in ('CREA','NPC_'): continue
            for fid,factions in aFid_factions.iteritems():
                csvId_factions[fid] = factions

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CREA','NPC_']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        if modFile.GName == record.fid[0]: return
        factions = record.ConflictDetails(('factions_list',))
        if factions:
            masterRecord = self.patchFile.Current.LookupRecords(record.fid)[-1]
            masterFactions = masterRecord.factions_list
            masterDict = dict((x[0],x[1]) for x in masterFactions)
            # Initialize the factions list with what's in the master record
            self.id_factions.setdefault(record.fid, masterDict)
            # Only add/remove records if different than the master record
            thisFactions = factions['factions_list']
            masterFids = set([x[0] for x in masterFactions])
            thisFids = set([x[0] for x in thisFactions])
            removedFids = masterFids - thisFids
            addedFids = thisFids - masterFids
            # Add new factions
            self.id_factions[record.fid].update(dict((x[0],x[1]) for x in thisFactions if x[0] in addedFids))
            # Remove deleted factions
            for fid in removedFids:
                self.id_factions[record.fid].pop(fid,None)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        fid = record.fid
        if fid in self.csvId_factions:
            newFactions = set([(faction,rank) for faction, rank in self.csvId_factions[fid] if faction.ValidateFormID(self.patchFile)])
        elif fid in self.id_factions:
            newFactions = set([(faction,rank) for faction, rank in self.id_factions[fid].iteritems() if faction.ValidateFormID(self.patchFile)])
        else:
            return
        curFactions = set([(faction[0],faction[1]) for faction in record.factions_list if faction[0].ValidateFormID(self.patchFile)])
        changed = newFactions - curFactions
        removed = curFactions - newFactions
        if changed or removed:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                for faction,rank in changed:
                    for entry in override.factions:
                        if entry.faction == faction:
                            entry.rank = rank
                            break
                    else:
                        entry = override.create_faction()
                        entry.faction = faction
                        entry.rank = rank
                override.factions_list = [(faction,rank) for faction,rank in override.factions_list if (faction,rank) not in removed]
                class_mod_count = self.class_mod_count
                class_mod_count.setdefault(record._Type,{})[modFile.GName] = class_mod_count.setdefault(record._Type,{}).get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        class_mod_count = self.class_mod_count
        log.setHeader(u'= ' +self.__class__.name)
        for type in class_mod_count.keys():
            log(u'* '+_(u'Refactioned %s Records: %d') % (type,sum(class_mod_count[type].values()),))
            for srcMod in modInfos.getOrdered(class_mod_count[type].keys()):
                log(u'  * %s: %d' % (srcMod.s,class_mod_count[type][srcMod]))
        self.class_mod_count = {}

#------------------------------------------------------------------------------
from patcher.oblivion.utilities import FactionRelations, CBash_FactionRelations

class ImportRelations(ImportPatcher):
    """Import faction relations to factions."""
    name = _(u'Import Relations')
    text = _(u"Import relations from source mods/files.")
    autoKey = u'Relations'

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
            patchesList = getPatchesList()
            if reModExt.search(srcFile.s):
                if srcPath not in modInfos: continue
                srcInfo = modInfos[GPath(srcFile)]
                factionRelations.readFromMod(srcInfo)
            else:
                if srcPath not in patchesList: continue
                factionRelations.readFromText(getPatchesPath(srcFile))
            progress.plus()
        #--Finish
        for fid, relations in factionRelations.id_relations.iteritems():
            if fid and (fid[0] is not None and fid[0] in self.patchFile.loadSet):
                filteredRelations = [relation for relation in relations if relation[0] and (relation[0][0] is not None and relation[0][0] in self.patchFile.loadSet)]
                if filteredRelations:
                    self.id_relations[fid] = filteredRelations

        self.isActive = bool(self.id_relations)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('FACT',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('FACT',) if self.isActive else ()

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
        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods/Files'))
        for file in self.srcFiles:
            log(u'* '+file.s)
        log(u'\n=== '+_(u'Modified Factions: %d') % type_count['FACT'])

class CBash_ImportRelations(CBash_ImportPatcher):
    """Import faction relations to factions."""
    name = _(u'Import Relations')
    text = _(u"Import relations from source mods/files.")
    autoKey = {u'Relations'}
    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.fid_faction_mod = {}
        self.csvFid_faction_mod = {}
        self.mod_count = {}

    def initData(self,group_patchers,progress):
        """Compiles material, i.e. reads source text, esp's, etc. as necessary."""
        if not self.isActive: return
        CBash_ImportPatcher.initData(self,group_patchers,progress)
        factionRelations = CBash_FactionRelations(aliases=self.patchFile.aliases)
        progress.setFull(len(self.srcs))
        patchesList = getPatchesList()
        for srcFile in self.srcs:
            srcPath = GPath(srcFile)
            if not reModExt.search(srcFile.s):
                if srcPath not in patchesList: continue
                factionRelations.readFromText(getPatchesPath(srcFile))
            progress.plus()
        #--Finish
        self.csvFid_faction_mod.update(factionRelations.fid_faction_mod)

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['FACT']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        relations = record.ConflictDetails(('relations_list',))
        if relations:
            self.fid_faction_mod.setdefault(record.fid,{}).update(relations['relations_list'])

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        fid = record.fid
        if fid in self.csvFid_faction_mod:
            newRelations = set((faction,mod) for faction,mod in self.csvFid_faction_mod[fid].iteritems() if faction.ValidateFormID(self.patchFile))
        elif fid in self.fid_faction_mod:
            newRelations = set((faction,mod) for faction,mod in self.fid_faction_mod[fid].iteritems() if faction.ValidateFormID(self.patchFile))
        else:
            return
        curRelations = set(record.relations_list)
        changed = newRelations - curRelations
        if changed:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                for faction,mod in changed:
                    for relation in override.relations:
                        if relation.faction == faction:
                            relation.mod = mod
                            break
                    else:
                        relation = override.create_relation()
                        relation.faction,relation.mod = faction,mod
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        mod_count = self.mod_count
        log.setHeader(u'= ' +self.__class__.name)
        log(u'* '+_(u'Re-Relationed Records: %d') % sum(mod_count.values()))
        for srcMod in modInfos.getOrdered(mod_count.keys()):
            log(u'  * %s: %d' % (srcMod.s,mod_count[srcMod]))
        self.mod_count = {}

#------------------------------------------------------------------------------
class ImportScripts(ImportPatcher):
    """Imports attached scripts on objects."""
    name = _(u'Import Scripts')
    text = _(u"Import Scripts on containers, plants, misc, weapons etc. from source mods.")
    tip = text
    autoKey = u'Scripts'

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
        self.longTypes = {'WEAP', 'ACTI', 'ALCH', 'APPA', 'ARMO', 'BOOK',
                          'CLOT', 'CONT', 'CREA', 'DOOR', 'FLOR', 'FURN',
                          'INGR', 'KEYM', 'LIGH', 'MISC', 'NPC_', 'QUST',
                          'SGST', 'SLGM'}
        for recClass in (MreRecord.type_class[x] for x in self.longTypes):
            recAttrs_class[recClass] = ('script',)

    def initData(self,progress):
        """Get script links from source files."""
        if not self.isActive: return
        self.classestemp = set()
        id_data = self.id_data
        recAttrs_class = self.recAttrs_class
        loadFactory = LoadFactory(False,*recAttrs_class.keys())
        longTypes = self.longTypes & set(x.classType for x in self.recAttrs_class)
        progress.setFull(len(self.sourceMods))
        cachedMasters = {}
        for index,srcMod in enumerate(self.sourceMods):
            temp_id_data = {}
            if srcMod not in modInfos: continue
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            masters = srcInfo.header.masters
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass,recAttrs in recAttrs_class.iteritems():
                if recClass.classType not in srcFile.tops: continue
                self.srcClasses.add(recClass)
                self.classestemp.add(recClass)
                for record in srcFile.tops[recClass.classType].getActiveRecords():
                    fid = mapper(record.fid)
                    temp_id_data[fid] = dict((attr,record.__getattribute__(attr)) for attr in recAttrs)
            for master in masters:
                if not master in modInfos: continue # or break filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = modInfos[master]
                    masterFile = ModFile(masterInfo,loadFactory)
                    masterFile.load(True)
                    masterFile.convertToLongFids(longTypes)
                    cachedMasters[master] = masterFile
                mapper = masterFile.getLongMapper()
                for recClass,recAttrs in recAttrs_class.iteritems():
                    if recClass.classType not in masterFile.tops: continue
                    if recClass not in self.classestemp: continue
                    for record in masterFile.tops[recClass.classType].getActiveRecords():
                        fid = mapper(record.fid)
                        if fid not in temp_id_data: continue
                        for attr, value in temp_id_data[fid].iteritems():
                            if value == record.__getattribute__(attr): continue
                            else:
                                if fid not in id_data: id_data[fid] = dict()
                                try:
                                    id_data[fid][attr] = temp_id_data[fid][attr]
                                except KeyError:
                                    id_data[fid].setdefault(attr,value)
            progress.plus()
        temp_id_data = None
        self.longTypes = self.longTypes & set(x.classType for x in self.srcClasses)
        self.isActive = bool(self.srcClasses)

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
        """Merge last version of record with patched scripts link as needed."""
        if not self.isActive: return
        modFile = self.patchFile
        keep = self.patchFile.getKeeper()
        id_data = self.id_data
        type_count = {}
        for recClass in self.srcClasses:
            type = recClass.classType
            if type not in modFile.tops: continue
            type_count[type] = 0
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
        #cleanup to save memory
        id_data = None
        #logging
        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        for mod in self.sourceMods:
            log(u'* ' +mod.s)
        log(u'\n=== '+_(u'Modified Records'))
        for type,count in sorted(type_count.iteritems()):
            if count: log(u'* %s: %d' % (type,count))

class CBash_ImportScripts(CBash_ImportPatcher):
    """Imports attached scripts on objects."""
    name = _(u'Import Scripts')
    text = _(u"Import Scripts on containers, plants, misc, weapons etc from source mods.")
    tip = text
    autoKey = {u'Scripts'}

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.id_script = {}
        self.class_mod_count = {}

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['ACTI','ALCH','APPA','ARMO','BOOK','CLOT','CONT','CREA',
                'DOOR','FLOR','FURN','INGR','KEYM','LIGH','LVLC','MISC',
                'NPC_','QUST','SGST','SLGM','WEAP']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        script = record.ConflictDetails(('script',))
        if script:
            script = script['script']
            if script.ValidateFormID(self.patchFile):
                # Only save if different from the master record
                if record.GetParentMod().GName != record.fid[0]:
                    history = record.History()
                    if history and len(history) > 0:
                        masterRecord = history[0]
                        if masterRecord.GetParentMod().GName == record.fid[0] and masterRecord.script == record.script:
                            return # Same
                self.id_script[record.fid] = script
            else:
                #Ignore the record. Another option would be to just ignore the invalid formIDs
                mod_skipcount = self.patchFile.patcher_mod_skipcount.setdefault(self.name,{})
                mod_skipcount[modFile.GName] = mod_skipcount.setdefault(modFile.GName, 0) + 1

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        if recordId in self.id_script and record.script != self.id_script[recordId]:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.script = self.id_script[recordId]
                class_mod_count = self.class_mod_count
                class_mod_count.setdefault(record._Type,{})[modFile.GName] = class_mod_count.setdefault(record._Type,{}).get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        class_mod_count = self.class_mod_count
        log.setHeader(u'= ' +self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        for mod in self.srcs:
            log(u'* ' +mod.s)
        log(u'\n=== '+_(u'Modified Records'))
        for type in class_mod_count.keys():
            log(u'* '+_(u'Modified %s Records: %d') % (type,sum(class_mod_count[type].values())))
            for srcMod in modInfos.getOrdered(class_mod_count[type].keys()):
                log(u'  * %s: %d' % (srcMod.s,class_mod_count[type][srcMod]))
        self.class_mod_count = {}

#------------------------------------------------------------------------------
class ImportInventory(ImportPatcher):
    """Merge changes to actor inventories."""
    name = _(u'Import Inventory')
    text = _(u"Merges changes to NPC, creature and container inventories.")
    autoKey = (u'Invent',u'InventOnly')
    iiMode = True

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_deltas = {}
        self.srcMods = self.getConfigChecked()
        self.srcMods = [x for x in self.srcMods if (x in modInfos and x in patchFile.allMods)]
        self.inventOnlyMods = set(x for x in self.srcMods if
            (x in patchFile.mergeSet and {u'InventOnly', u'IIM'} & modInfos[x].getBashTags()))
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
        return ('NPC_','CREA','CONT',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('NPC_','CREA','CONT',) if self.isActive else ()

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
        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        for mod in self.srcMods:
            log(u'* '+mod.s)
        log(u'\n=== '+_(u'Inventories Changed: %d') % sum(mod_count.values()))
        for mod in modInfos.getOrdered(mod_count):
            log(u'* %s: %3d' % (mod.s,mod_count[mod]))

class CBash_ImportInventory(CBash_ImportPatcher):
    """Merge changes to actor inventories."""
    name = _(u'Import Inventory')
    text = _(u"Merges changes to NPC, creature and container inventories.")
    autoKey = {u'Invent', u'InventOnly'}
    iiMode = True

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.id_deltas = {}
        #should be redundant since this patcher doesn't allow unloaded
        #self.srcs = [x for x in self.srcs if (x in modInfos and x in patchFile.allMods)]
        self.inventOnlyMods = set(x for x in self.srcs if
            (x in patchFile.mergeSet and {u'InventOnly', u'IIM'} & modInfos[x].getBashTags()))
        self.class_mod_count = {}

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CREA','NPC_','CONT']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        #--Source mod?
        masters = record.History()
        if not masters: return
        entries = record.items_list
        modItems = set((item,count) for item,count in entries if item.ValidateFormID(self.patchFile))
        masterEntries = []
        id_deltas = self.id_deltas
        fid = record.fid
        for masterEntry in masters:
            masterItems = set((item,count) for item,count in masterEntry.items_list if item.ValidateFormID(self.patchFile))
            removeItems = masterItems - modItems
            addItems = modItems - masterItems
            if len(removeItems) or len(addItems):
                deltas = id_deltas.get(fid)
                if deltas is None: deltas = id_deltas[fid] = []
                deltas.append((set((item for item,count in removeItems)),addItems))

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        deltas = self.id_deltas.get(record.fid)
        if not deltas: return
        #If only the inventory is imported, the deltas have to be applied to
        #whatever record would otherwise be winning
        if modFile.GName in self.inventOnlyMods:
            conflicts = record.Conflicts()
            if conflicts:
                #If this isn't actually the winning record, use it.
                #This could be the case if a record was already copied into the patch
                if conflicts[0] != record:
                    record = conflicts[0]
                #Otherwise, use the previous one.
                else:
                    record = conflicts[1]

        removable = set(entry.item for entry in record.items)
        items = record.items_list
        for removeItems,addEntries in reversed(deltas):
            if removeItems:
                #--Skip if some items to be removed have already been removed
                if not removeItems.issubset(removable): continue
                items = [(item,count) for item,count in items if item not in removeItems]
                removable -= removeItems
            if addEntries:
                current = set(item for item,count in items)
                for item,count in addEntries:
                    if item not in current:
                        items.append((item,count))


        if len(items) != len(record.items_list) or set((item,count) for item,count in record.items_list) != set((item,count) for item,count in items):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.items_list = items
                class_mod_count = self.class_mod_count
                class_mod_count.setdefault(record._Type,{})[modFile.GName] = class_mod_count.setdefault(record._Type,{}).get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        class_mod_count = self.class_mod_count
        log.setHeader(u'= ' +self.__class__.name)
        for type in class_mod_count.keys():
            log(u'* '+_(u'%s Inventories Changed: %d') % (type,sum(class_mod_count[type].values())))
            for srcMod in modInfos.getOrdered(class_mod_count[type].keys()):
                log(u'  * %s: %d' % (srcMod.s,class_mod_count[type][srcMod]))
        self.class_mod_count = {}

#------------------------------------------------------------------------------
class ImportActorsSpells(ImportPatcher):
    """Merges changes to the spells lists of Actors."""
    name = _(u'Import Actors: Spells')
    text = _(u"Merges changes to NPC and creature spell lists.")
    tip = text
    autoKey = (u'Actors.Spells',u'Actors.SpellsForceAdd')

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.srcMods = self.getConfigChecked()
        self.isActive = len(self.srcMods) != 0
        self.data = {}
        self.longTypes = {'CREA', 'NPC_'}

    def initData(self,progress):
        """Get data from source files."""
        if not self.isActive: return
        longTypes = self.longTypes
        loadFactory = LoadFactory(False,MreRecord.type_class['CREA'],
                                        MreRecord.type_class['NPC_'])
        progress.setFull(len(self.srcMods))
        cachedMasters = {}
        data = self.data
        for index,srcMod in enumerate(self.srcMods):
            tempData = {}
            if srcMod not in modInfos: continue
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            masters = srcInfo.header.masters
            bashTags = srcInfo.getBashTags()
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass in (MreRecord.type_class[x] for x in ('NPC_','CREA')):
                if recClass.classType not in srcFile.tops: continue
                for record in srcFile.tops[recClass.classType].getActiveRecords():
                    fid = mapper(record.fid)
                    tempData[fid] = list(record.spells)
            for master in reversed(masters):
                if not master in modInfos: continue # or break filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = modInfos[master]
                    masterFile = ModFile(masterInfo,loadFactory)
                    masterFile.load(True)
                    masterFile.convertToLongFids(longTypes)
                    cachedMasters[master] = masterFile
                mapper = masterFile.getLongMapper()
                for block in (MreRecord.type_class[x] for x in ('NPC_','CREA')):
                    if block.classType not in srcFile.tops: continue
                    if block.classType not in masterFile.tops: continue
                    for record in masterFile.tops[block.classType].getActiveRecords():
                        fid = mapper(record.fid)
                        if not fid in tempData: continue
                        if record.spells == tempData[fid] and not u'Actors.SpellsForceAdd' in bashTags:
                            # if subrecord is identical to the last master then we don't care about older masters.
                            del tempData[fid]
                            continue
                        if fid in data:
                            if tempData[fid] == data[fid]['merged']: continue
                        recordData = {'deleted':[],'merged':tempData[fid]}
                        for spell in list(record.spells):
                            if not spell in tempData[fid]:
                                recordData['deleted'].append(spell)
                        if not fid in data:
                            data[fid] = recordData
                        else:
                            for spell in recordData['deleted']:
                                if spell in data[fid]['merged']:
                                    data[fid]['merged'].remove(spell)
                                data[fid]['deleted'].append(spell)
                            if data[fid]['merged'] == []:
                                for spell in recordData['merged']:
                                    if spell in data[fid]['deleted'] and not u'Actors.SpellsForceAdd' in bashTags: continue
                                    data[fid]['merged'].append(spell)
                                continue
                            for index, spell in enumerate(recordData['merged']):
                                if not spell in data[fid]['merged']: # so needs to be added... (unless deleted that is)
                                    # find the correct position to add and add.
                                    if spell in data[fid]['deleted'] and not u'Actors.SpellsForceAdd' in bashTags: continue #previously deleted
                                    if index == 0:
                                        data[fid]['merged'].insert(0,spell) #insert as first item
                                    elif index == (len(recordData['merged'])-1):
                                        data[fid]['merged'].append(spell) #insert as last item
                                    else: #figure out a good spot to insert it based on next or last recognized item (ugly ugly ugly)
                                        i = index - 1
                                        while i >= 0:
                                            if recordData['merged'][i] in data[fid]['merged']:
                                                slot = data[fid]['merged'].index(recordData['merged'][i])+1
                                                data[fid]['merged'].insert(slot, spell)
                                                break
                                            i -= 1
                                        else:
                                            i = index + 1
                                            while i != len(recordData['merged']):
                                                if recordData['merged'][i] in data[fid]['merged']:
                                                    slot = data[fid]['merged'].index(recordData['merged'][i])
                                                    data[fid]['merged'].insert(slot, spell)
                                                    break
                                                i += 1
                                    continue # Done with this package
                                elif index == data[fid]['merged'].index(spell) or (len(recordData['merged'])-index) == (len(data[fid]['merged'])-data[fid]['merged'].index(spell)): continue #spell same in both lists.
                                else: #this import is later loading so we'll assume it is better order
                                    data[fid]['merged'].remove(spell)
                                    if index == 0:
                                        data[fid]['merged'].insert(0,spell) #insert as first item
                                    elif index == (len(recordData['merged'])-1):
                                        data[fid]['merged'].append(spell) #insert as last item
                                    else:
                                        i = index - 1
                                        while i >= 0:
                                            if recordData['merged'][i] in data[fid]['merged']:
                                                slot = data[fid]['merged'].index(recordData['merged'][i]) + 1
                                                data[fid]['merged'].insert(slot, spell)
                                                break
                                            i -= 1
                                        else:
                                            i = index + 1
                                            while i != len(recordData['merged']):
                                                if recordData['merged'][i] in data[fid]['merged']:
                                                    slot = data[fid]['merged'].index(recordData['merged'][i])
                                                    data[fid]['merged'].insert(slot, spell)
                                                    break
                                                i += 1
            progress.plus()

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('NPC_','CREA',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('NPC_','CREA',) if self.isActive else ()

    def scanModFile(self, modFile, progress):
        """Add record from modFile."""
        if not self.isActive: return
        data = self.data
        mapper = modFile.getLongMapper()
        modName = modFile.fileInfo.name
        for type in ('NPC_','CREA'):
            patchBlock = getattr(self.patchFile,type)
            for record in getattr(modFile,type).getActiveRecords():
                fid = mapper(record.fid)
                if fid in data:
                    if list(record.spells) != data[fid]['merged']:
                        patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress):
        """Applies delta to patchfile."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        data = self.data
        mod_count = {}
        for type in ('NPC_','CREA'):
            for record in getattr(self.patchFile,type).records:
                fid = record.fid
                if not fid in data: continue
                changed = False
                mergedSpells = sorted(data[fid]['merged'])
                if sorted(list(record.spells)) != mergedSpells:
                    record.spells = mergedSpells
                    changed = True
                if changed:
                    keep(record.fid)
                    mod = record.fid[0]
                    mod_count[mod] = mod_count.get(mod,0) + 1
        #--Log
        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        for mod in self.srcMods:
            log(u'* '+mod.s)
        log(u'\n=== '+_(u'Spell Lists Changed: %d') % sum(mod_count.values()))
        for mod in modInfos.getOrdered(mod_count):
            log(u'* %s: %3d' % (mod.s,mod_count[mod]))

class CBash_ImportActorsSpells(CBash_ImportPatcher):
    """Merges changes to the spells lists of Actors."""
    name = _(u'Import Actors: Spells')
    text = _(u"Merges changes to NPC and creature spell lists.")
    tip = text
    autoKey = {u'Actors.Spells', u'Actors.SpellsForceAdd'}

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.id_spells = {}
        self.mod_count = {}

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CREA','NPC_']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        curData = {'deleted':[],'merged':[]}
        curspells = FormID.FilterValid(record.spells, self.patchFile)
        parentRecords = record.History()
        if parentRecords:
            parentSpells = FormID.FilterValid(parentRecords[-1].spells, self.patchFile)
            if parentSpells != curspells or u'Actors.SpellsForceAdd' in bashTags:
                for spell in parentSpells:
                    if spell not in curspells:
                        curData['deleted'].append(spell)
            curData['merged'] = curspells
            if not record.fid in self.id_spells:
                self.id_spells[record.fid] = curData
            else:
                id_spells = self.id_spells[record.fid]
                for spell in curData['deleted']:
                    if spell in id_spells['merged']:
                        id_spells['merged'].remove(spell)
                    id_spells['deleted'].append(spell)
                for spell in curData['merged']:
                    if spell in id_spells['merged']: continue #don't want to add 20 copies of the spell afterall
                    if not spell in id_spells['deleted'] or u'Actors.SpellsForceAdd' in bashTags:
                        id_spells['merged'].append(spell)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        mergedSpells = self.id_spells.get(recordId,None)
        if mergedSpells:
            if sorted(record.spells) != sorted(mergedSpells['merged']):
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.spells = mergedSpells['merged']
                    mod_count = self.mod_count
                    mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        mod_count = self.mod_count
        log.setHeader(u'= ' +self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        for mod in self.srcs:
            log(u'* '+mod.s)
        log(u'* '+_(u'Imported Spell Lists: %d') % sum(mod_count.values()))
        for srcMod in modInfos.getOrdered(mod_count.keys()):
            log(u'  * %s: %d' % (srcMod.s,mod_count[srcMod]))
        self.mod_count = {}

#------------------------------------------------------------------------------
from patcher.oblivion.utilities import FullNames, CBash_FullNames

class NamesPatcher(ImportPatcher):
    """Merged leveled lists mod file."""
    name = _(u'Import Names')
    text = _(u"Import names from source mods/files.")
    autoRe = bush.game.namesPatcherMaster
    autoKey = u'Names'

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
            patchesList = getPatchesList()
            if reModExt.search(srcFile.s):
                if srcPath not in modInfos: continue
                srcInfo = modInfos[GPath(srcFile)]
                fullNames.readFromMod(srcInfo)
            else:
                if srcPath not in patchesList: continue
                try:
                    fullNames.readFromText(getPatchesPath(srcFile))
                except UnicodeError as e:
                    print srcFile.stail,u'is not saved in UTF-8 format:', e
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
                if name != u'NO NAME':
                    id_full[longid] = name
        self.isActive = bool(self.activeTypes)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return tuple(self.activeTypes) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return tuple(self.activeTypes) if self.isActive else ()

    def scanModFile(self, modFile, progress):
        """Scan modFile."""
        if not self.isActive: return
        id_full = self.id_full
        modName = modFile.fileInfo.name
        mapper = modFile.getLongMapper()
        for type in self.activeTypes:
            if type not in modFile.tops: continue
            patchBlock = getattr(self.patchFile,type)
            if type == 'CELL':
                id_records = patchBlock.id_cellBlock
                activeRecords = (cellBlock.cell for cellBlock in modFile.CELL.cellBlocks if not cellBlock.cell.flags1.ignored)
                setter = patchBlock.setCell
            elif type == 'WRLD':
                id_records = patchBlock.id_worldBlocks
                activeRecords = (worldBlock.world for worldBlock in modFile.WRLD.worldBlocks if not worldBlock.world.flags1.ignored)
                setter = patchBlock.setWorld
            else:
                id_records = patchBlock.id_records
                activeRecords = modFile.tops[type].getActiveRecords()
                setter = patchBlock.setRecord
            for record in activeRecords:
                fid = record.fid
                if not record.longFids: fid = mapper(fid)
                if fid in id_records: continue
                if fid not in id_full: continue
                if record.full != id_full[fid]:
                    setter(record.getTypeCopy(mapper))

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
            if type == 'CELL':
                records = (cellBlock.cell for cellBlock in modFile.CELL.cellBlocks)
            elif type == 'WRLD':
                records = (worldBlock.world for worldBlock in modFile.WRLD.worldBlocks)
            else:
                records = modFile.tops[type].records
            for record in records:
                fid = record.fid
                if fid in id_full and record.full != id_full[fid]:
                    record.full = id_full[fid]
                    keep(fid)
                    type_count[type] += 1
        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods/Files'))
        for file in self.srcFiles:
            log(u'* '+file.s)
        log(u'\n=== '+_(u'Renamed Items'))
        for type,count in sorted(type_count.iteritems()):
            if count: log(u'* %s: %d' % (type,count))

class CBash_NamesPatcher(CBash_ImportPatcher):
    """Import names from source mods/files."""
    name = _(u'Import Names')
    text = _(u"Import names from source mods/files.")
    autoRe = re.compile(ur"^Oblivion.esm$",re.I|re.U)
    autoKey = {u'Names'}

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.id_full = {}
        self.csvId_full = {}
        self.class_mod_count = {}

    def initData(self,group_patchers,progress):
        """Compiles material, i.e. reads source text, esp's, etc. as necessary."""
        if not self.isActive: return
        CBash_ImportPatcher.initData(self,group_patchers,progress)
        fullNames = CBash_FullNames(aliases=self.patchFile.aliases)
        progress.setFull(len(self.srcs))
        patchesList = getPatchesList()
        for srcFile in self.srcs:
            srcPath = GPath(srcFile)
            if not reModExt.search(srcFile.s):
                if srcPath not in patchesList: continue
                fullNames.readFromText(getPatchesPath(srcFile))
            progress.plus()

        #--Finish
        csvId_full = self.csvId_full
        for group,fid_name in fullNames.group_fid_name.iteritems():
            if group not in validTypes: continue
            for fid,(eid,name) in fid_name.iteritems():
                if name != u'NO NAME':
                    csvId_full[fid] = name

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CLAS','FACT','HAIR','EYES','RACE','MGEF','ENCH',
                'SPEL','BSGN','ACTI','APPA','ARMO','BOOK','CLOT',
                'CONT','DOOR','INGR','LIGH','MISC','FLOR','FURN',
                'WEAP','AMMO','NPC_','CREA','SLGM','KEYM','ALCH',
                'SGST','WRLD','CELLS','DIAL','QUST']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        full = record.ConflictDetails(('full',))
        if full:
            self.id_full[record.fid] = full['full']

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        full = self.id_full.get(recordId, None)
        full = self.csvId_full.get(recordId, full)
        if full and record.full != full:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.full = full
                class_mod_count = self.class_mod_count
                class_mod_count.setdefault(record._Type,{})[modFile.GName] = class_mod_count.setdefault(record._Type,{}).get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        class_mod_count = self.class_mod_count
        log.setHeader(u'= ' +self.__class__.name)
        log(u'=== '+_(u'Source Mods/Files'))
        for file in self.srcs:
            log(u'* ' +file.s)
        log(u'\n=== '+_(u'Renamed Items'))
        for type in class_mod_count.keys():
            log(u'* '+_(u'Modified %s Records: %d') % (type,sum(class_mod_count[type].values())))
            for srcMod in modInfos.getOrdered(class_mod_count[type].keys()):
                log(u'  * %s: %d' % (srcMod.s,class_mod_count[type][srcMod]))
        self.class_mod_count = {}

#------------------------------------------------------------------------------
class NpcFacePatcher(ImportPatcher):
    """NPC Faces patcher, for use with TNR or similar mods."""
    name = _(u'Import NPC Faces')
    text = _(u"Import NPC face/eyes/hair from source mods. For use with TNR and similar mods.")
    autoRe = re.compile(ur"^TNR .*.esp$",re.I|re.U)
    autoKey = (u'NpcFaces',u'NpcFacesForceFullImport',u'Npc.HairOnly',u'Npc.EyesOnly')

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
        loadFactory = LoadFactory(False,MreRecord.type_class['NPC_'])
        progress.setFull(len(self.faceMods))
        cachedMasters = {}
        for index,faceMod in enumerate(self.faceMods):
            if faceMod not in modInfos: continue
            temp_faceData = {}
            faceInfo = modInfos[faceMod]
            faceFile = ModFile(faceInfo,loadFactory)
            masters = faceInfo.header.masters
            bashTags = faceInfo.getBashTags()
            faceFile.load(True)
            faceFile.convertToLongFids(('NPC_',))
            for npc in faceFile.NPC_.getActiveRecords():
                if npc.fid[0] in self.patchFile.loadSet:
                    attrs, fidattrs = [],[]
                    if u'Npc.HairOnly' in bashTags:
                        fidattrs += ['hair']
                        attrs = ['hairLength','hairRed','hairBlue','hairGreen']
                    if u'Npc.EyesOnly' in bashTags: fidattrs += ['eye']
                    if fidattrs:
                        attr_fidvalue = dict((attr,npc.__getattribute__(attr)) for attr in fidattrs)
                    else:
                        attr_fidvalue = dict((attr,npc.__getattribute__(attr)) for attr in ('eye','hair'))
                    for fidvalue in attr_fidvalue.values():
                        if fidvalue and (fidvalue[0] is None or fidvalue[0] not in self.patchFile.loadSet):
                            #Ignore the record. Another option would be to just ignore the attr_fidvalue result
                            mod_skipcount = self.patchFile.patcher_mod_skipcount.setdefault(self.name,{})
                            mod_skipcount[faceMod] = mod_skipcount.setdefault(faceMod, 0) + 1
                            break
                    else:
                        if not fidattrs: temp_faceData[npc.fid] = dict((attr,npc.__getattribute__(attr)) for attr in ('fggs_p','fgga_p','fgts_p','hairLength','hairRed','hairBlue','hairGreen','unused3'))
                        else: temp_faceData[npc.fid] = dict((attr,npc.__getattribute__(attr)) for attr in attrs)
                        temp_faceData[npc.fid].update(attr_fidvalue)
            if u'NpcFacesForceFullImport' in bashTags:
                for fid in temp_faceData:
                    faceData[fid] = temp_faceData[fid]
            else:
                for master in masters:
                    if not master in modInfos: continue # or break filter mods
                    if master in cachedMasters:
                        masterFile = cachedMasters[master]
                    else:
                        masterInfo = modInfos[master]
                        masterFile = ModFile(masterInfo,loadFactory)
                        masterFile.load(True)
                        masterFile.convertToLongFids(('NPC_',))
                        cachedMasters[master] = masterFile
                    mapper = masterFile.getLongMapper()
                    if 'NPC_' not in masterFile.tops: continue
                    for npc in masterFile.NPC_.getActiveRecords():
                        if npc.fid not in temp_faceData: continue
                        for attr, value in temp_faceData[npc.fid].iteritems():
                            if value == npc.__getattribute__(attr): continue
                            if npc.fid not in faceData: faceData[npc.fid] = dict()
                            try:
                                faceData[npc.fid][attr] = temp_faceData[npc.fid][attr]
                            except KeyError:
                                faceData[npc.fid].setdefault(attr,value)
            progress.plus()

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('NPC_',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('NPC_',) if self.isActive else ()

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
                changed = False
                for attr, value in faceData[npc.fid].iteritems():
                    if value != npc.__getattribute__(attr):
                        npc.__setattr__(attr,value)
                        changed = True
                if changed:
                    npc.setChanged()
                    keep(npc.fid)
                    count += 1
        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        for mod in self.faceMods:
            log(u'* '+mod.s)
        log(u'\n=== '+_(u'Faces Patched: %d') % count)

class CBash_NpcFacePatcher(CBash_ImportPatcher):
    """NPC Faces patcher, for use with TNR or similar mods."""
    name = _(u'Import NPC Faces')
    text = _(u"Import NPC face/eyes/hair from source mods. For use with TNR and similar mods.")
    autoRe = re.compile(ur"^TNR .*.esp$",re.I|re.U)
    autoKey = {u'NpcFaces', u'NpcFacesForceFullImport', u'Npc.HairOnly',
               u'Npc.EyesOnly'}

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.id_face = {}
        self.faceData = ('fggs_p','fgga_p','fgts_p','eye','hair','hairLength','hairRed','hairBlue','hairGreen','fnam')
        self.mod_count = {}

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['NPC_']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        attrs = []
        if u'NpcFacesForceFullImport' in bashTags:
            face = dict((attr,getattr(record,attr)) for attr in self.faceData)
            if ValidateDict(face, self.patchFile):
                self.id_face[record.fid] = face
            else:
                #Ignore the record. Another option would be to just ignore the invalid formIDs
                mod_skipcount = self.patchFile.patcher_mod_skipcount.setdefault(self.name,{})
                mod_skipcount[modFile.GName] = mod_skipcount.setdefault(modFile.GName, 0) + 1
            return
        elif u'NpcFaces' in bashTags:
            attrs = self.faceData
        else:
            if u'Npc.HairOnly' in bashTags:
                attrs = ['hair', 'hairLength','hairRed','hairBlue','hairGreen']
            if u'Npc.EyesOnly' in bashTags:
                attrs += ['eye']
        if not attrs:
            return
        face = record.ConflictDetails(attrs)

        if ValidateDict(face, self.patchFile):
            fid = record.fid
            # Only save if different from the master record
            if record.GetParentMod().GName != fid[0]:
                history = record.History()
                if history and len(history) > 0:
                    masterRecord = history[0]
                    if masterRecord.GetParentMod().GName == record.fid[0]:
                        for attr, value in face.iteritems():
                            if getattr(masterRecord,attr) != value:
                                break
                        else:
                            return
            self.id_face.setdefault(fid,{}).update(face)
        else:
            #Ignore the record. Another option would be to just ignore the invalid formIDs
            mod_skipcount = self.patchFile.patcher_mod_skipcount.setdefault(self.name,{})
            mod_skipcount[modFile.GName] = mod_skipcount.setdefault(modFile.GName, 0) + 1

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)

        recordId = record.fid
        prev_face_value = self.id_face.get(recordId,None)
        if prev_face_value:
            cur_face_value = dict((attr,getattr(record,attr)) for attr in prev_face_value)
            if cur_face_value != prev_face_value:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_face_value.iteritems():
                        setattr(override,attr,value)
                    mod_count = self.mod_count
                    mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        mod_count = self.mod_count
        log.setHeader(u'= ' +self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        for mod in self.srcs:
            log(u'* ' +mod.s)
        log(u'* '+_(u'Faces Patched: %d') % sum(mod_count.values()))
        for srcMod in modInfos.getOrdered(mod_count.keys()):
            log(u'  * %s: %d' % (srcMod.s,mod_count[srcMod]))
        self.mod_count = {}

#------------------------------------------------------------------------------
class RoadImporter(ImportPatcher):
    """Imports roads."""
    name = _(u'Import Roads')
    text = _(u"Import roads from source mods.")
    tip = text
    autoKey = u'Roads'

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
        loadFactory = LoadFactory(False,MreRecord.type_class['CELL'],
                                        MreRecord.type_class['WRLD'],
                                        MreRecord.type_class['ROAD'])
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
        return ('CELL','WRLD','ROAD',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('CELL','WRLD','ROAD',) if self.isActive else ()

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
        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        for mod in self.sourceMods:
            log(u'* '+mod.s)
        log(u'\n=== '+_(u'Worlds Patched'))
        for modWorld in sorted(worldsPatched):
            log(u'* %s: %s' % modWorld)

class CBash_RoadImporter(CBash_ImportPatcher):
    """Imports roads."""
    name = _(u'Import Roads')
    text = _(u"Import roads from source mods.")
    tip = text
    autoKey = {u'Roads'}
    #The regular patch routine doesn't allow merging of world records. The CBash patch routine does.
    #So, allowUnloaded isn't needed for this patcher to work. The same functionality could be gained by merging the tagged record.
    #It is needed however so that the regular patcher and the CBash patcher have the same behavior.
    #The regular patcher has to allow unloaded mods because it can't otherwise force the road record to be merged
    #This isn't standard behavior for import patchers, but consistency between patchers is more important.

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.id_ROAD = {}
        self.mod_count = {}

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['ROADS']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        self.id_ROAD[record.fid] = record

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        #If a previous road was scanned, and it is replaced by a new road
        curRoad = record
        newRoad = self.id_ROAD.get(recordId, None)
        if newRoad:
            #Roads and pathgrids are complex records...
            #No good way to tell if the roads are equal.
            #A direct comparison can prove equality, but not inequality
            if curRoad.pgrp_list == newRoad.pgrp_list and curRoad.pgrr_list == newRoad.pgrr_list:
                return
            #So some records that are actually equal won't pass the above test and end up copied over
            #Bloats the patch a little, but won't hurt anything.
            if newRoad.fid.ValidateFormID(self.patchFile):
                copyRoad = newRoad #Copy the new road over
            elif curRoad and curRoad.fid.ValidateFormID(self.patchFile):
                copyRoad = curRoad #Copy the current road over (its formID is acceptable)
            else:
                #Ignore the record.
                mod_skipcount = self.patchFile.patcher_mod_skipcount.setdefault(self.name,{})
                mod_skipcount[modFile.GName] = mod_skipcount.setdefault(modFile.GName, 0) + 1
                return

            override = copyRoad.CopyAsOverride(self.patchFile, UseWinningParents=True) #Copies the road over (along with the winning version of its parents if needed)
            if override:
                #Copy the new road values into the override (in case the CopyAsOverride returned a record pre-existing in the patch file)
                for copyattr in newRoad.copyattrs:
                    setattr(override, copyattr, getattr(newRoad, copyattr))
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        mod_count = self.mod_count
        log.setHeader(u'= ' +self.__class__.name)
        log(u'* '+_(u'Roads Imported: %d') % sum(mod_count.values()))
        for srcMod in modInfos.getOrdered(mod_count.keys()):
            log(u'  * %s: %d' % (srcMod.s,mod_count[srcMod]))
        self.mod_count = {}

#------------------------------------------------------------------------------
class SoundPatcher(ImportPatcher):
    """Imports sounds from source mods into patch."""
    name = _(u'Import Sounds')
    text = _(u"Import sounds (from Magic Effects, Containers, Activators, Lights, Weathers and Doors) from source mods.")
    tip = text
    autoKey = u'Sound'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_data = {} #--Names keyed by long fid.
        self.srcClasses = set() #--Record classes actually provided by src mods/files.
        self.sourceMods = self.getConfigChecked()
        self.isActive = len(self.sourceMods) != 0
        self.classestemp = set()
        #--Type Fields
        recAttrs_class = self.recAttrs_class = {}
        for recClass in (MreRecord.type_class[x] for x in ('MGEF',)):
            recAttrs_class[recClass] = ('castingSound','boltSound','hitSound','areaSound')
        for recClass in (MreRecord.type_class[x] for x in ('ACTI','LIGH')):
            recAttrs_class[recClass] = ('sound',)
        for recClass in (MreRecord.type_class[x] for x in ('WTHR',)):
            recAttrs_class[recClass] = ('sounds',)
        for recClass in (MreRecord.type_class[x] for x in ('CONT',)):
            recAttrs_class[recClass] = ('soundOpen','soundClose')
        for recClass in (MreRecord.type_class[x] for x in ('DOOR',)):
            recAttrs_class[recClass] = ('soundOpen','soundClose','soundLoop')
        #--Needs Longs
        self.longTypes = {'MGEF', 'ACTI', 'LIGH', 'WTHR', 'CONT', 'DOOR'}

    def initData(self,progress):
        """Get sounds from source files."""
        if not self.isActive: return
        id_data = self.id_data
        recAttrs_class = self.recAttrs_class
        loadFactory = LoadFactory(False,*recAttrs_class.keys())
        longTypes = self.longTypes & set(x.classType for x in self.recAttrs_class)
        progress.setFull(len(self.sourceMods))
        cachedMasters = {}
        for index,srcMod in enumerate(self.sourceMods):
            temp_id_data = {}
            if srcMod not in modInfos: continue
            srcInfo = modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            masters = srcInfo.header.masters
            srcFile.load(True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass,recAttrs in recAttrs_class.iteritems():
                if recClass.classType not in srcFile.tops: continue
                self.srcClasses.add(recClass)
                self.classestemp.add(recClass)
                for record in srcFile.tops[recClass.classType].getActiveRecords():
                    fid = mapper(record.fid)
                    temp_id_data[fid] = dict((attr,record.__getattribute__(attr)) for attr in recAttrs)
            for master in masters:
                if not master in modInfos: continue # or break filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = modInfos[master]
                    masterFile = ModFile(masterInfo,loadFactory)
                    masterFile.load(True)
                    masterFile.convertToLongFids(longTypes)
                    cachedMasters[master] = masterFile
                mapper = masterFile.getLongMapper()
                for recClass,recAttrs in recAttrs_class.iteritems():
                    if recClass.classType not in masterFile.tops: continue
                    if recClass not in self.classestemp: continue
                    for record in masterFile.tops[recClass.classType].getActiveRecords():
                        fid = mapper(record.fid)
                        if fid not in temp_id_data: continue
                        for attr, value in temp_id_data[fid].iteritems():
                            if value == record.__getattribute__(attr): continue
                            else:
                                if fid not in id_data: id_data[fid] = dict()
                                try:
                                    id_data[fid][attr] = temp_id_data[fid][attr]
                                except KeyError:
                                    id_data[fid].setdefault(attr,value)
            progress.plus()
        temp_id_data = None
        self.longTypes = self.longTypes & set(x.classType for x in self.srcClasses)
        self.isActive = bool(self.srcClasses)

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
                for attr,value in id_data[fid].iteritems():
                    if record.__getattribute__(attr) != value:
                        break
                else:
                    continue
                for attr,value in id_data[fid].iteritems():
                    record.__setattr__(attr,value)
                keep(fid)
                type_count[type] += 1
        id_data = None
        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        for mod in self.sourceMods:
            log(u'* ' +mod.s)
        log(u'\n=== '+_(u'Modified Records'))
        for type,count in sorted(type_count.iteritems()):
            if count: log(u'* %s: %d' % (type,count))

class CBash_SoundPatcher(CBash_ImportPatcher):
    """Imports sounds from source mods into patch."""
    name = _(u'Import Sounds')
    text = _(u"Import sounds (from Activators, Containers, Creatures, Doors, Lights, Magic Effects and Weathers) from source mods.")
    tip = text
    autoKey = {u'Sound'}

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.fid_attr_value = {}
        self.class_mod_count = {}
        class_attrs = self.class_attrs = {}
        class_attrs['ACTI'] = ('sound',)
        class_attrs['CONT'] = ('soundOpen','soundClose')
        class_attrs['CREA'] = ('footWeight','inheritsSoundsFrom','sounds_list')
        class_attrs['DOOR'] = ('soundOpen','soundClose','soundLoop')
        class_attrs['LIGH'] = ('sound',)
        class_attrs['MGEF'] = ('castingSound','boltSound','hitSound','areaSound')
##        class_attrs['REGN'] = ('sound','sounds_list')
        class_attrs['WTHR'] = ('sounds_list',)

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['ACTI','CONT','CREA','DOOR','LIGH','MGEF','WTHR']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        conflicts = record.ConflictDetails(self.class_attrs[record._Type])
        if conflicts:
            if ValidateDict(conflicts, self.patchFile):
                self.fid_attr_value.setdefault(record.fid,{}).update(conflicts)
            else:
                #Ignore the record. Another option would be to just ignore the invalid formIDs
                mod_skipcount = self.patchFile.patcher_mod_skipcount.setdefault(self.name,{})
                mod_skipcount[modFile.GName] = mod_skipcount.setdefault(modFile.GName, 0) + 1

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        prev_attr_value = self.fid_attr_value.get(recordId,None)
        if prev_attr_value:
            cur_attr_value = dict((attr,getattr(record,attr)) for attr in prev_attr_value)
            if cur_attr_value != prev_attr_value:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_attr_value.iteritems():
                        setattr(override,attr,value)
                    class_mod_count = self.class_mod_count
                    class_mod_count.setdefault(record._Type,{})[modFile.GName] = class_mod_count.setdefault(record._Type,{}).get(modFile.GName,0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        class_mod_count = self.class_mod_count
        log.setHeader(u'= ' +self.__class__.name)
        log(u'=== '+_(u'Source Mods'))
        for mod in self.srcs:
            log(u'* '+mod.s)
        log(u'\n=== '+_(u'Modified Records'))
        for type in class_mod_count.keys():
            log(u'* '+_(u'Modified %s Records: %d') % (type,sum(class_mod_count[type].values())))
            for srcMod in modInfos.getOrdered(class_mod_count[type].keys()):
                log(u'  * %s: %d' % (srcMod.s,class_mod_count[type][srcMod]))
        self.class_mod_count = {}

#------------------------------------------------------------------------------
from patcher.oblivion.utilities import ItemStats, CBash_ItemStats

class StatsPatcher(ImportPatcher):
    """Import stats from mod file."""
    scanOrder = 28
    editOrder = 28 #--Run ahead of bow patcher
    name = _(u'Import Stats')
    text = _(u"Import stats from any pickupable items from source mods/files.")
    autoKey = u'Stats'

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.srcFiles = self.getConfigChecked()
        self.isActive = bool(self.srcFiles)
        #--To be filled by initData
        self.fid_attr_value = {} #--Stats keyed by long fid.
        self.activeTypes = [] #--Types ('ARMO', etc.) of data actually provided by src mods/files.
        self.class_attrs = {}

    def initData(self,progress):
        """Get stats from source files."""
        if not self.isActive: return
        itemStats = ItemStats(aliases=self.patchFile.aliases)
        progress.setFull(len(self.srcFiles))
        for srcFile in self.srcFiles:
            srcPath = GPath(srcFile)
            patchesList = getPatchesList()
            if reModExt.search(srcFile.s):
                if srcPath not in modInfos: continue
                srcInfo = modInfos[GPath(srcFile)]
                itemStats.readFromMod(srcInfo)
            else:
                if srcPath not in patchesList: continue
                itemStats.readFromText(getPatchesPath(srcFile))
            progress.plus()

        #--Finish
        for group,nId_attr_value in itemStats.class_fid_attr_value.iteritems():
            self.activeTypes.append(group)
            for id, attr_value in nId_attr_value.iteritems():
                del attr_value['eid']
            self.fid_attr_value.update(nId_attr_value)
            self.class_attrs[group] = itemStats.class_attrs[group][1:]

        self.isActive = bool(self.activeTypes)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return tuple(self.activeTypes) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return tuple(self.activeTypes) if self.isActive else ()

    def scanModFile(self, modFile, progress):
        """Add affected items to patchFile."""
        if not self.isActive: return
        fid_attr_value = self.fid_attr_value
        mapper = modFile.getLongMapper()
        for group in self.activeTypes:
            if group not in modFile.tops: continue
            attrs = self.class_attrs[group]
            patchBlock = getattr(self.patchFile,group)
            id_records = patchBlock.id_records
            for record in getattr(modFile,group).getActiveRecords():
                longid = record.fid
                if not record.longFids: longid = mapper(longid)
                if longid in id_records: continue
                itemStats = fid_attr_value.get(longid,None)
                if not itemStats: continue
                oldValues = dict(zip(attrs,map(record.__getattribute__,attrs)))
                if oldValues != itemStats:
                    patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress):
        """Adds merged lists to patchfile."""
        if not self.isActive: return
        patchFile = self.patchFile
        keep = self.patchFile.getKeeper()
        fid_attr_value = self.fid_attr_value
        allCounts = []
        for group in self.activeTypes:
            if group not in patchFile.tops: continue
            attrs = self.class_attrs[group]
            count,counts = 0,{}
            for record in patchFile.tops[group].records:
                fid = record.fid
                itemStats = fid_attr_value.get(fid,None)
                if not itemStats: continue
                oldValues = dict(zip(attrs,map(record.__getattribute__,attrs)))
                if oldValues != itemStats:
                    for attr, value in itemStats.iteritems():
                        setattr(record,attr,value)
                    keep(fid)
                    count += 1
                    counts[fid[0]] = 1 + counts.get(fid[0],0)
            allCounts.append((group,count,counts))
        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods/Files'))
        for file in self.srcFiles:
            log(u'* ' +file.s)
        log(u'\n=== '+_(u'Modified Stats'))
        for type,count,counts in allCounts:
            if not count: continue
            typeName = {'ALCH':_(u'Potions'),
                        'AMMO':_(u'Ammo'),
                        'ARMO':_(u'Armors'),
                        'INGR':_(u'Ingredients'),
                        'MISC':_(u'Misc'),
                        'WEAP':_(u'Weapons'),
                        'SLGM':_(u'Soulgems'),
                        'SGST':_(u'Sigil Stones'),
                        'LIGH':_(u'Lights'),
                        'KEYM':_(u'Keys'),
                        'CLOT':_(u'Clothes'),
                        'BOOK':_(u'Books'),
                        'APPA':_(u'Apparatuses'),
                        }[type]
            log(u'* %s: %d' % (typeName,count))
            for modName in sorted(counts):
                log(u'  * %s: %d' % (modName.s,counts[modName]))

class CBash_StatsPatcher(CBash_ImportPatcher):
    """Import stats from mod file."""
    scanOrder = 28
    editOrder = 28 #--Run ahead of bow patcher
    name = _(u'Import Stats')
    text = _(u"Import stats from any pickupable items from source mods/files.")
    autoKey = {u'Stats'}

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.fid_attr_value = {}
        self.csvFid_attr_value = {}
        self.class_attrs = CBash_ItemStats.class_attrs
        self.class_mod_count = {}

    def initData(self,group_patchers,progress):
        """Compiles material, i.e. reads source text, esp's, etc. as necessary."""
        if not self.isActive: return
        CBash_ImportPatcher.initData(self,group_patchers,progress)
        itemStats = CBash_ItemStats(aliases=self.patchFile.aliases)
        progress.setFull(len(self.srcs))
        patchesList = getPatchesList()
        for srcFile in self.srcs:
            if not reModExt.search(srcFile.s):
                if srcFile not in patchesList: continue
                itemStats.readFromText(getPatchesPath(srcFile))
            progress.plus()

        #--Finish
        for group,nId_attr_value in itemStats.class_fid_attr_value.iteritems():
            if group not in validTypes: continue
            self.csvFid_attr_value.update(nId_attr_value)

        for group in self.getTypes():
            group_patchers.setdefault(group,[]).append(self)

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return self.class_attrs.keys()
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        conflicts = record.ConflictDetails(self.class_attrs[record._Type])
        if conflicts:
            if ValidateDict(conflicts, self.patchFile):
                self.fid_attr_value.setdefault(record.fid,{}).update(conflicts)
            else:
                #Ignore the record. Another option would be to just ignore the invalid formIDs
                mod_skipcount = self.patchFile.patcher_mod_skipcount.setdefault(self.name,{})
                mod_skipcount[modFile.GName] = mod_skipcount.setdefault(modFile.GName, 0) + 1

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        prev_attr_value = self.fid_attr_value.get(recordId, None)
        csv_attr_value = self.csvFid_attr_value.get(recordId, None)
        if csv_attr_value and ValidateDict(csv_attr_value, self.patchFile):
            prev_attr_value = csv_attr_value
        if prev_attr_value:
            cur_attr_value = dict((attr,getattr(record,attr)) for attr in prev_attr_value)
            if cur_attr_value != prev_attr_value:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_attr_value.iteritems():
                        setattr(override,attr,value)
                    class_mod_count = self.class_mod_count
                    class_mod_count.setdefault(record._Type,{})[modFile.GName] = class_mod_count.setdefault(record._Type,{}).get(modFile.GName,0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        class_mod_count = self.class_mod_count
        log.setHeader(u'= ' +self.__class__.name)
        log(u'=== '+_(u'Source Mods/Files'))
        for file in self.srcs:
            log(u'* '+file.s)
        log(u'\n=== '+_(u'Imported Stats'))
        for type in class_mod_count.keys():
            log(u'* '+_(u'Modified %s Records: %d') % (type,sum(class_mod_count[type].values())))
            for srcMod in modInfos.getOrdered(class_mod_count[type].keys()):
                log(u'  * %s: %d' % (srcMod.s,class_mod_count[type][srcMod]))
        self.class_mod_count = {}

#------------------------------------------------------------------------------
from patcher.oblivion.utilities import SpellRecords, CBash_SpellRecords

class SpellsPatcher(ImportPatcher):
    """Import spell changes from mod files."""
    scanOrder = 29
    editOrder = 29 #--Run ahead of bow patcher
    name = _(u'Import Spell Stats')
    text = _(u"Import stats from any spells from source mods/files.")
    autoKey = (u'Spells',u'SpellStats')

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.srcFiles = self.getConfigChecked()
        self.isActive = bool(self.srcFiles)
        #--To be filled by initData
        self.id_stat = {} #--Stats keyed by long fid.
        self.attrs = None #set in initData

    def initData(self,progress):
        """Get stats from source files."""
        if not self.isActive: return
        spellStats = SpellRecords(aliases=self.patchFile.aliases)
        self.attrs = spellStats.attrs
        progress.setFull(len(self.srcFiles))
        for srcFile in self.srcFiles:
            srcPath = GPath(srcFile)
            patchesList = getPatchesList()
            if reModExt.search(srcFile.s):
                if srcPath not in modInfos: continue
                srcInfo = modInfos[GPath(srcFile)]
                spellStats.readFromMod(srcInfo)
            else:
                if srcPath not in patchesList: continue
                spellStats.readFromText(getPatchesPath(srcFile))
            progress.plus()
        #--Finish
        self.id_stat.update(spellStats.fid_stats)
        self.isActive = bool(self.id_stat)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('SPEL',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('SPEL',) if self.isActive else ()

    def scanModFile(self, modFile, progress):
        """Add affected items to patchFile."""
        if not self.isActive or 'SPEL' not in modFile.tops:
            return
        id_stat = self.id_stat
        mapper = modFile.getLongMapper()
        attrs = self.attrs
        patchBlock = self.patchFile.SPEL
        id_records = patchBlock.id_records
        for record in modFile.SPEL.getActiveRecords():
            fid = record.fid
            if not record.longFids: fid = mapper(fid)
            if fid in id_records: continue
            spellStats = id_stat.get(fid)
            if not spellStats: continue
            oldValues = [getattr_deep(record, attr) for attr in attrs]
            if oldValues != spellStats:
                patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress):
        """Adds merged lists to patchfile."""
        if not self.isActive: return
        patchFile = self.patchFile
        keep = self.patchFile.getKeeper()
        id_stat = self.id_stat
        allCounts = []
        attrs = self.attrs
        count,counts = 0,{}
        for record in patchFile.SPEL.records:
            fid = record.fid
            spellStats = id_stat.get(fid)
            if not spellStats: continue
            oldValues = [getattr_deep(record, attr) for attr in attrs]
            if oldValues == spellStats: continue
            for attr,value in zip(attrs,spellStats):
                setattr_deep(record,attr,value)
            keep(fid)
            count += 1
            counts[fid[0]] = 1 + counts.get(fid[0],0)
        allCounts.append(('SPEL',count,counts))
        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods/Files'))
        for file in self.srcFiles:
            log(u'* '+file.s)
        log(u'\n=== '+_(u'Modified Stats'))
        for type,count,counts in allCounts:
            if not count: continue
            typeName = {'SPEL':_(u'Spells'),}[type]
            log(u'* %s: %d' % (typeName,count))
            for modName in sorted(counts):
                log(u'  * %s: %d' % (modName.s,counts[modName]))

class CBash_SpellsPatcher(CBash_ImportPatcher):
    """Import spell changes from mod files."""
    scanOrder = 29
    editOrder = 29 #--Run ahead of bow patcher
    name = _(u'Import Spell Stats')
    text = _(u"Import stats from any spells from source mods/files.")
    autoKey = {u'Spells', u'SpellStats'}

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ImportPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.id_stats = {}
        self.csvId_stats = {}
        self.mod_count = {}
        self.attrs = None #set in initData

    def initData(self,group_patchers,progress):
        """Compiles material, i.e. reads source text, esp's, etc. as necessary."""
        if not self.isActive: return
        CBash_ImportPatcher.initData(self,group_patchers,progress)
        spellStats = CBash_SpellRecords(aliases=self.patchFile.aliases)
        self.attrs = spellStats.attrs
        progress.setFull(len(self.srcs))
        patchesList = getPatchesList()
        for srcFile in self.srcs:
            srcPath = GPath(srcFile)
            if not reModExt.search(srcFile.s):
                if srcPath not in patchesList: continue
                spellStats.readFromText(getPatchesPath(srcFile))
            progress.plus()
        #--Finish
        self.csvId_stats.update(spellStats.fid_stats)

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['SPEL']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        conflicts = record.ConflictDetails(self.attrs)
        if conflicts:
            if ValidateDict(conflicts, self.patchFile):
                self.id_stats.setdefault(record.fid,{}).update(conflicts)
            else:
                #Ignore the record. Another option would be to just ignore the invalid formIDs
                mod_skipcount = self.patchFile.patcher_mod_skipcount.setdefault(self.name,{})
                mod_skipcount[modFile.GName] = mod_skipcount.setdefault(modFile.GName, 0) + 1

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        prev_values = self.id_stats.get(recordId, None)
        csv_values = self.csvId_stats.get(recordId, None)
        if csv_values and ValidateDict(csv_values, self.patchFile):
            prev_values = csv_values
        if prev_values:
            rec_values = dict((attr,getattr(record,attr)) for attr in prev_values)
            if rec_values != prev_values:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_values.iteritems():
                        setattr(override,attr,value)
                    mod_count = self.mod_count
                    mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        mod_count = self.mod_count
        log.setHeader(u'= ' +self.__class__.name)
        log(u'* '+_(u'Modified SPEL Stats: %d') % sum(mod_count.values()))
        for srcMod in modInfos.getOrdered(mod_count.keys()):
            log(u'  * %s: %d' % (srcMod.s,mod_count[srcMod]))
        self.mod_count = {}

# Patchers: 30 ----------------------------------------------------------------
################################### MOVED #####################################
# Patchers: 40 ----------------------------------------------------------------
class SpecialPatcher:
    """Provides default group, scan and edit orders."""
    group = _(u'Special')
    scanOrder = 40
    editOrder = 40

    def scan_more(self,modFile,record,bashTags):
        if modFile.GName in self.srcs:
            self.scan(modFile,record,bashTags)
        #Must check for "unloaded" conflicts that occur past the winning record
        #If any exist, they have to be scanned
        for conflict in record.Conflicts(True):
            if conflict != record:
                mod = conflict.GetParentMod()
                if mod.GName in self.srcs:
                    tags = modInfos[mod.GName].getBashTags()
                    self.scan(mod,conflict,tags)
            else: return

#------------------------------------------------------------------------------
class AlchemicalCatalogs(SpecialPatcher,Patcher):
    """Updates COBL alchemical catalogs."""
    name = _(u'Cobl Catalogs')
    text = (_(u"Update COBL's catalogs of alchemical ingredients and effects.") +
            u'\n\n' +
            _(u'Will only run if Cobl Main.esm is loaded.')
            )
    defaultConfig = {'isEnabled':True}

    #--Config Phase -----------------------------------------------------------
    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.isActive = (GPath(u'COBL Main.esm') in loadMods)
        self.id_ingred = {}

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('INGR',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('BOOK',) if self.isActive else ()

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
            mgef_name[mgef] = re.sub(_(u'(Attribute|Skill)'),u'',mgef_name[mgef])
        actorEffects = bush.genericAVEffects
        actorNames = bush.actorValues
        keep = self.patchFile.getKeeper()
        #--Book generatator
        def getBook(objectId,eid,full,value,iconPath,modelPath,modb_p):
            book = MreRecord.type_class['BOOK'](ModReader.recHeader('BOOK',0,0,0,0))
            book.longFids = True
            book.changed = True
            book.eid = eid
            book.full = full
            book.value = value
            book.weight = 0.2
            book.fid = keep((GPath(u'Cobl Main.esm'),objectId))
            book.text = u'<div align="left"><font face=3 color=4444>'
            book.text += _(u"Salan's Catalog of ")+u'%s\r\n\r\n' % full
            book.iconPath = iconPath
            book.model = book.getDefault('model')
            book.model.modPath = modelPath
            book.model.modb_p = modb_p
            book.modb = book
            self.patchFile.BOOK.setRecord(book)
            return book
        #--Ingredients Catalog
        id_ingred = self.id_ingred
        iconPath,modPath,modb_p = (u'Clutter\\IconBook9.dds',u'Clutter\\Books\\Octavo02.NIF','\x03>@A')
        for (num,objectId,full,value) in bush.ingred_alchem:
            book = getBook(objectId,u'cobCatAlchemIngreds%s'%num,full,value,iconPath,modPath,modb_p)
            with sio(book.text) as buff:
                buff.seek(0,os.SEEK_END)
                buffWrite = buff.write
                for eid,full,effects in sorted(id_ingred.values(),key=lambda a: a[1].lower()):
                    buffWrite(full+u'\r\n')
                    for mgef,actorValue in effects[:num]:
                        effectName = mgef_name[mgef]
                        if mgef in actorEffects: effectName += actorNames[actorValue]
                        buffWrite(u'  '+effectName+u'\r\n')
                    buffWrite(u'\r\n')
                book.text = re.sub(u'\r\n',u'<br>\r\n',buff.getvalue())
        #--Get Ingredients by Effect
        effect_ingred = {}
        for fid,(eid,full,effects) in id_ingred.iteritems():
            for index,(mgef,actorValue) in enumerate(effects):
                effectName = mgef_name[mgef]
                if mgef in actorEffects: effectName += actorNames[actorValue]
                if effectName not in effect_ingred: effect_ingred[effectName] = []
                effect_ingred[effectName].append((index,full))
        #--Effect catalogs
        iconPath,modPath,modb_p = (u'Clutter\\IconBook7.dds',u'Clutter\\Books\\Octavo01.NIF','\x03>@A')
        for (num,objectId,full,value) in bush.effect_alchem:
            book = getBook(objectId,u'cobCatAlchemEffects%s'%num,full,value,iconPath,modPath,modb_p)
            with sio(book.text) as buff:
                buff.seek(0,os.SEEK_END)
                buffWrite = buff.write
                for effectName in sorted(effect_ingred.keys()):
                    effects = [indexFull for indexFull in effect_ingred[effectName] if indexFull[0] < num]
                    if effects:
                        buffWrite(effectName+u'\r\n')
                        for (index,full) in sorted(effects,key=lambda a: a[1].lower()):
                            exSpace = u' ' if index == 0 else u''
                            buffWrite(u' %s%s %s\r\n'%(index + 1,exSpace,full))
                        buffWrite(u'\r\n')
                book.text = re.sub(u'\r\n',u'<br>\r\n',buff.getvalue())
        #--Log
        log.setHeader(u'= '+self.__class__.name)
        log(u'* '+_(u'Ingredients Cataloged: %d') % len(id_ingred))
        log(u'* '+_(u'Effects Cataloged: %d') % len(effect_ingred))

class CBash_AlchemicalCatalogs(SpecialPatcher,CBash_Patcher):
    """Updates COBL alchemical catalogs."""
    name = _(u'Cobl Catalogs')
    text = (_(u"Update COBL's catalogs of alchemical ingredients and effects.") +
            u'\n\n' +
            _(u'Will only run if Cobl Main.esm is loaded.')
            )
    unloadedText = ""
    srcs = [] #so as not to fail screaming when determining load mods - but with the least processing required.
    defaultConfig = {'isEnabled':True}

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_Patcher.initPatchFile(self,patchFile,loadMods)
        self.isActive = GPath(u'Cobl Main.esm') in loadMods
        if not self.isActive: return
        patchFile.indexMGEFs = True
        self.id_ingred = {}
        self.effect_ingred = {}
        self.SEFF = MGEFCode('SEFF')
        self.DebugPrintOnce = 0

    def getTypes(self):
        return ['INGR']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.full:
            SEFF = self.SEFF
            for effect in record.effects:
                if effect.name == SEFF:
                    return
            self.id_ingred[record.fid] = (record.eid, record.full, record.effects_list)

    def finishPatch(self,patchFile,progress):
        """Edits the bashed patch file directly."""
        subProgress = SubProgress(progress)
        subProgress.setFull(len(bush.effect_alchem) + len(bush.ingred_alchem))
        pstate = 0
        #--Setup
        try:
            coblMod = patchFile.Current.LookupModFile(u'Cobl Main.esm')
        except KeyError, error:
            print u"CBash_AlchemicalCatalogs:finishPatch"
            print error[0]
            return

        mgef_name = patchFile.mgef_name.copy()
        for mgef in mgef_name:
            mgef_name[mgef] = re.sub(_(u'(Attribute|Skill)'),u'',mgef_name[mgef])
        actorEffects = bush.genericAVEffects
        actorNames = bush.actorValues
        #--Book generator
        def getBook(patchFile, objectId):
            book = coblMod.LookupRecord(FormID(GPath(u'Cobl Main.esm'),objectId))
            #There have been reports of this patcher failing, hence the sanity checks
            if book:
                if book.recType != 'BOOK':
                    print PrintFormID(fid)
                    print patchFile.Current.Debug_DumpModFiles()
                    print book
                    raise StateError(u"Cobl Catalogs: Unable to lookup book record in Cobl Main.esm!")
                book = book.CopyAsOverride(self.patchFile)
                if not book:
                    print PrintFormID(fid)
                    print patchFile.Current.Debug_DumpModFiles()
                    print book
                    book = coblMod.LookupRecord(FormID(GPath(u'Cobl Main.esm'),objectId))
                    print book
                    print book.text
                    print
                    raise StateError(u"Cobl Catalogs: Unable to create book!")
            return book
        #--Ingredients Catalog
        id_ingred = self.id_ingred
        for (num,objectId,full,value) in bush.ingred_alchem:
            subProgress(pstate, _(u'Cataloging Ingredients...')+u'\n%s' % full)
            pstate += 1
            book = getBook(patchFile, objectId)
            if not book: continue
            with sio() as buff:
                buff.write(u'<div align="left"><font face=3 color=4444>' + _(u"Salan's Catalog of ")+u"%s\r\n\r\n" % full)
                for eid,full,effects_list in sorted(id_ingred.values(),key=lambda a: a[1].lower()):
                    buff.write(full+u'\r\n')
                    for effect in effects_list[:num]:
                        mgef = effect[0] #name field
                        try:
                            effectName = mgef_name[mgef]
                        except KeyError:
                            if not self.DebugPrintOnce:
                                self.DebugPrintOnce = 1
                                print patchFile.Current.Debug_DumpModFiles()
                                print
                                print u'mgef_name:', mgef_name
                                print
                                print u'mgef:', mgef
                                print
                                if mgef in bush.mgef_name:
                                    print u'mgef found in bush.mgef_name'
                                else:
                                    print u'mgef not found in bush.mgef_name'
                            if mgef in bush.mgef_name:
                                effectName = re.sub(_(u'(Attribute|Skill)'),u'',bush.mgef_name[mgef])
                            else:
                                effectName = u'Unknown Effect'
                        if mgef in actorEffects: effectName += actorNames[effect[5]] #actorValue field
                        buff.write(u'  '+effectName+u'\r\n')
                    buff.write(u'\r\n')
                book.text = re.sub(u'\r\n',u'<br>\r\n',buff.getvalue())
        #--Get Ingredients by Effect
        effect_ingred = self.effect_ingred = {}
        for fid,(eid,full,effects_list) in id_ingred.iteritems():
            for index,effect in enumerate(effects_list):
                mgef, actorValue = effect[0], effect[5]
                try:
                    effectName = mgef_name[mgef]
                except KeyError:
                    if not self.DebugPrintOnce:
                        self.DebugPrintOnce = 1
                        print patchFile.Current.Debug_DumpModFiles()
                        print
                        print u'mgef_name:', mgef_name
                        print
                        print u'mgef:', mgef
                        print
                        if mgef in bush.mgef_name:
                            print u'mgef found in bush.mgef_name'
                        else:
                            print u'mgef not found in bush.mgef_name'
                    if mgef in bush.mgef_name:
                        effectName = re.sub(_(u'(Attribute|Skill)'),u'',bush.mgef_name[mgef])
                    else:
                        effectName = u'Unknown Effect'
                if mgef in actorEffects: effectName += actorNames[actorValue]
                effect_ingred.setdefault(effectName, []).append((index,full))
        #--Effect catalogs
        for (num,objectId,full,value) in bush.effect_alchem:
            subProgress(pstate, _(u'Cataloging Effects...')+u'\n%s' % full)
            book = getBook(patchFile,objectId)
            with sio() as buff:
                buff.write(u'<div align="left"><font face=3 color=4444>' + _(u"Salan's Catalog of ")+u"%s\r\n\r\n" % full)
                for effectName in sorted(effect_ingred.keys()):
                    effects = [indexFull for indexFull in effect_ingred[effectName] if indexFull[0] < num]
                    if effects:
                        buff.write(effectName+u'\r\n')
                        for (index,full) in sorted(effects,key=lambda a: a[1].lower()):
                            exSpace = u' ' if index == 0 else u''
                            buff.write(u' %s%s %s\r\n' % (index + 1,exSpace,full))
                        buff.write(u'\r\n')
                book.text = re.sub(u'\r\n',u'<br>\r\n',buff.getvalue())
            pstate += 1

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        id_ingred = self.id_ingred
        effect_ingred = self.effect_ingred
        log.setHeader(u'= '+self.__class__.name)
        log(u'* '+_(u'Ingredients Cataloged: %d') % len(id_ingred))
        log(u'* '+_(u'Effects Cataloged: %d') % len(effect_ingred))

#------------------------------------------------------------------------------
class CoblExhaustion(SpecialPatcher,ListPatcher):
    """Modifies most Greater power to work with Cobl's power exhaustion feature."""
    name = _(u'Cobl Exhaustion')
    text = (_(u"Modify greater powers to use Cobl's Power Exhaustion feature.") +
            u'\n\n' +
            _(u'Will only run if Cobl Main v1.66 (or higher) is active.')
            )
    autoKey = u'Exhaust'
    canAutoItemCheck = False #--GUI: Whether new items are checked by default or not.

    #--Config Phase -----------------------------------------------------------
    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.cobl = GPath(u'Cobl Main.esm')
        self.srcFiles = self.getConfigChecked()
        self.isActive = bool(self.srcFiles) and (self.cobl in loadMods and modInfos.getVersionFloat(self.cobl) > 1.65)
        self.id_exhaustion = {}

    def readFromText(self,textPath):
        """Imports type_id_name from specified text file."""
        aliases = self.patchFile.aliases
        id_exhaustion = self.id_exhaustion
        textPath = GPath(textPath)
        with bolt.CsvReader(textPath) as ins:
            reNum = re.compile(ur'\d+',re.U)
            for fields in ins:
                if len(fields) < 4 or fields[1][:2] != u'0x' or not reNum.match(fields[3]): continue
                mod,objectIndex,eid,time = fields[:4]
                mod = GPath(mod)
                longid = (aliases.get(mod,mod),int(objectIndex[2:],16))
                id_exhaustion[longid] = int(time)

    def initData(self,progress):
        """Get names from source files."""
        if not self.isActive: return
        progress.setFull(len(self.srcFiles))
        for srcFile in self.srcFiles:
            srcPath = GPath(srcFile)
            patchesList = getPatchesList()
            if srcPath not in patchesList: continue
            self.readFromText(getPatchesPath(srcFile))
            progress.plus()

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('SPEL',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('SPEL',) if self.isActive else ()

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
            scriptEffect.full = u"Power Exhaustion"
            scriptEffect.script = exhaustId
            scriptEffect.school = 2
            scriptEffect.visual = null4
            scriptEffect.flags.hostile = False
            effect.scriptEffect = scriptEffect
            record.effects.append(effect)
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1
        #--Log
        log.setHeader(u'= '+self.__class__.name)
        log(u'* '+_(u'Powers Tweaked: %d') % sum(count.values()))
        for srcMod in modInfos.getOrdered(count.keys()):
            log(u'  * %s: %d' % (srcMod.s,count[srcMod]))

class CBash_CoblExhaustion(SpecialPatcher,CBash_ListPatcher):
    """Modifies most Greater power to work with Cobl's power exhaustion feature."""
    name = _(u'Cobl Exhaustion')
    text = (_(u"Modify greater powers to use Cobl's Power Exhaustion feature.") +
            u'\n\n' +
            _(u'Will only run if Cobl Main v1.66 (or higher) is active.')
            )
    autoKey = {u'Exhaust'}
    canAutoItemCheck = False #--GUI: Whether new items are checked by default or not.
    unloadedText = ""

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ListPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.cobl = GPath(u'Cobl Main.esm')
        self.isActive = (self.cobl in loadMods and modInfos.getVersionFloat(self.cobl) > 1.65)
        self.id_exhaustion = {}
        self.mod_count = {}
        self.SEFF = MGEFCode('SEFF')
        self.exhaustionId = FormID(self.cobl, 0x05139B)

    def initData(self,group_patchers,progress):
        """Compiles material, i.e. reads source text, esp's, etc. as necessary."""
        if not self.isActive: return
        for type in self.getTypes():
            group_patchers.setdefault(type,[]).append(self)
        progress.setFull(len(self.srcs))
        for srcFile in self.srcs:
            srcPath = GPath(srcFile)
            patchesList = getPatchesList()
            if srcPath not in patchesList: continue
            self.readFromText(getPatchesPath(srcFile))
            progress.plus()

    def getTypes(self):
        return ['SPEL']

    def readFromText(self,textPath):
        """Imports type_id_name from specified text file."""
        aliases = self.patchFile.aliases
        id_exhaustion = self.id_exhaustion
        textPath = GPath(textPath)
        with bolt.CsvReader(textPath) as ins:
            reNum = re.compile(ur'\d+',re.U)
            for fields in ins:
                if len(fields) < 4 or fields[1][:2] != u'0x' or not reNum.match(fields[3]): continue
                mod,objectIndex,eid,time = fields[:4]
                mod = GPath(mod)
                longid = FormID(aliases.get(mod,mod),int(objectIndex[2:],16))
                id_exhaustion[longid] = int(time)

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.IsPower:
            #--Skip this one?
            duration = self.id_exhaustion.get(record.fid,0)
            if not duration: return
            for effect in record.effects:
                if effect.name == self.SEFF and effect.script == self.exhaustionId:
                    return
            #--Okay, do it
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.full = u'+' + override.full
                override.IsLesserPower = True
                effect = override.create_effect()
                effect.name = self.SEFF
                effect.duration = duration
                effect.full = u'Power Exhaustion'
                effect.script = self.exhaustionId
                effect.IsDestruction = True
                effect.visual = MGEFCode(None,None)
                effect.IsHostile = False

                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        mod_count = self.mod_count
        log.setHeader(u'= '+self.__class__.name)
        log(u'* '+_(u'Powers Tweaked: %d') % (sum(mod_count.values()),))
        for srcMod in modInfos.getOrdered(mod_count.keys()):
            log(u'  * %s: %d' % (srcMod.s,mod_count[srcMod]))
        self.mod_count = {}

#------------------------------------------------------------------------------
class ListsMerger(SpecialPatcher,ListPatcher):
    """Merged leveled lists mod file."""
    scanOrder = 45
    editOrder = 45
    name = _(u'Leveled Lists')
    text = (_(u"Merges changes to leveled lists from ACTIVE/MERGED MODS ONLY.") +
            u'\n\n' +
            _(u'Advanced users may override Relev/Delev tags for any mod (active or inactive) using the list below.')
            )
    tip = _(u"Merges changes to leveled lists from all active mods.")
    choiceMenu = (u'Auto',u'----',u'Delev',u'Relev') #--List of possible choices for each config item. Item 0 is default.
    autoKey = (u'Delev',u'Relev')
    forceAuto = False
    forceItemCheck = True #--Force configChecked to True for all items
    iiMode = True
    selectCommands = False
    defaultConfig = {'isEnabled':True,'autoIsChecked':True,'configItems':[],'configChecks':{},'configChoices':{}}

    #--Static------------------------------------------------------------------
    @staticmethod
    def getDefaultTags():
        tags = {}
        for fileName in (u'Leveled Lists.csv',u'My Leveled Lists.csv'):
            textPath = dirs['patches'].join(fileName)
            if textPath.exists():
                with bolt.CsvReader(textPath) as reader:
                    for fields in reader:
                        if len(fields) < 2 or not fields[0] or fields[1] not in (u'DR',u'R',u'D',u'RD',u''): continue
                        tags[GPath(fields[0])] = fields[1]
        return tags

    #--Config Phase -----------------------------------------------------------
    def getChoice(self,item):
        """Get default config choice."""
        choice = self.configChoices.get(item)
        if not isinstance(choice,set): choice = {u'Auto'}
        if u'Auto' in choice:
            if item in modInfos:
                bashTags = modInfos[item].getBashTags()
                choice = {u'Auto'} | ({u'Delev', u'Relev'} & bashTags)
        self.configChoices[item] = choice
        return choice

    def getItemLabel(self,item):
        """Returns label for item to be used in list"""
        choice = map(itemgetter(0),self.configChoices.get(item,tuple()))
        if isinstance(item,bolt.Path): item = item.s
        if choice:
            return u'%s [%s]' % (item,u''.join(sorted(choice)))
        else:
            return item

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.srcMods = set(self.getConfigChecked()) & set(loadMods)
        self.listTypes = bush.game.listTypes
        self.type_list = dict([(type,{}) for type in self.listTypes])
        self.masterItems = {}
        self.mastersScanned = set()
        self.levelers = None #--Will initialize later
        self.empties = set()
        OverhaulCompat = False
        OOOMods = {GPath(u"Oscuro's_Oblivion_Overhaul.esm"),
                   GPath(u"Oscuro's_Oblivion_Overhaul.esp")}
        FransMods = {GPath(u"Francesco's Leveled Creatures-Items Mod.esm"),
                     GPath(u"Francesco.esp")}
        WCMods = {GPath(u"Oblivion Warcry.esp"),
                  GPath(u"Oblivion Warcry EV.esp")}
        TIEMods = {GPath(u"TIE.esp")}
        if GPath(u"Unofficial Oblivion Patch.esp") in self.srcMods:
            if (OOOMods|WCMods) & self.srcMods:
                OverhaulCompat = True
            elif FransMods & self.srcMods:
                if TIEMods & self.srcMods:
                    pass
                else:
                    OverhaulCompat = True
        if OverhaulCompat:
            self.OverhaulUOPSkips = set([
                (GPath(u'Oblivion.esm'),x) for x in [
                    0x03AB5D,   # VendorWeaponBlunt
                    0x03C7F1,   # LL0LootWeapon0Magic4Dwarven100
                    0x03C7F2,   # LL0LootWeapon0Magic7Ebony100
                    0x03C7F3,   # LL0LootWeapon0Magic5Elven100
                    0x03C7F4,   # LL0LootWeapon0Magic6Glass100
                    0x03C7F5,   # LL0LootWeapon0Magic3Silver100
                    0x03C7F7,   # LL0LootWeapon0Magic2Steel100
                    0x03E4D2,   # LL0NPCWeapon0MagicClaymore100
                    0x03E4D3,   # LL0NPCWeapon0MagicClaymoreLvl100
                    0x03E4DA,   # LL0NPCWeapon0MagicWaraxe100
                    0x03E4DB,   # LL0NPCWeapon0MagicWaraxeLvl100
                    0x03E4DC,   # LL0NPCWeapon0MagicWarhammer100
                    0x03E4DD,   # LL0NPCWeapon0MagicWarhammerLvl100
                    0x0733EA,   # ArenaLeveledHeavyShield,
                    0x0C7615,   # FGNPCWeapon0MagicClaymoreLvl100
                    0x181C66,   # SQ02LL0NPCWeapon0MagicClaymoreLvl100
                    0x053877,   # LL0NPCArmor0MagicLightGauntlets100
                    0x053878,   # LL0NPCArmor0MagicLightBoots100
                    0x05387A,   # LL0NPCArmor0MagicLightCuirass100
                    0x053892,   # LL0NPCArmor0MagicLightBootsLvl100
                    0x053893,   # LL0NPCArmor0MagicLightCuirassLvl100
                    0x053894,   # LL0NPCArmor0MagicLightGauntletsLvl100
                    0x053D82,   # LL0LootArmor0MagicLight5Elven100
                    0x053D83,   # LL0LootArmor0MagicLight6Glass100
                    0x052D89,   # LL0LootArmor0MagicLight4Mithril100
                    ]
                ])
        else:
            self.OverhaulUOPSkips = set()

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return self.listTypes

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return self.listTypes

    def scanModFile(self, modFile, progress):
        """Add lists from modFile."""
        #--Level Masters (complete initialization)
        if self.levelers is None:
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
        isRelev = (u'Relev' in configChoice)
        isDelev = (u'Delev' in configChoice)
        #--Scan
        for type in self.listTypes:
            levLists = self.type_list[type]
            newLevLists = getattr(modFile,type)
            for newLevList in newLevLists.getActiveRecords():
                listId = newLevList.fid
                if listId in self.OverhaulUOPSkips and modName == u'Unofficial Oblivion Patch.esp':
                    levLists[listId].mergeOverLast = True
                    continue
                isListOwner = (listId[0] == modName)
                #--Items, delevs and relevs sets
                newLevList.items = items = set([entry.listId for entry in newLevList.entries])
                if not isListOwner:
                    #--Relevs
                    newLevList.relevs = items.copy() if isRelev else set()
                    #--Delevs: all items in masters minus current items
                    newLevList.delevs = delevs = set()
                    if isDelev:
                        id_masterItems = self.masterItems.get(listId)
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
        log.setHeader(u'= '+self.__class__.name,True)
        log.setHeader(u'=== '+_(u'Delevelers/Relevelers'))
        for leveler in (self.levelers or []):
            log(u'* '+self.getItemLabel(leveler))
        #--Save to patch file
        for label, type in ((_(u'Creature'),'LVLC'), (_(u'Actor'),'LVLN'), (_(u'Item'),'LVLI'), (_(u'Spell'),'LVSP')):
            if type not in self.listTypes: continue
            log.setHeader(u'=== '+_(u'Merged %s Lists') % label)
            patchBlock = getattr(self.patchFile,type)
            levLists = self.type_list[type]
            for record in sorted(levLists.values(),key=attrgetter('eid')):
                if not record.mergeOverLast: continue
                fid = keep(record.fid)
                patchBlock.setRecord(levLists[fid])
                log(u'* '+record.eid)
                for mod in record.mergeSources:
                    log(u'  * ' + self.getItemLabel(mod))
        #--Discard empty sublists
        for label, type in ((_(u'Creature'),'LVLC'), (_(u'Actor'),'LVLN'), (_(u'Item'),'LVLI'), (_(u'Spell'),'LVSP')):
            if type not in self.listTypes: continue
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
            log.setHeader(u'=== '+_(u'Empty %s Sublists') % label)
            for eid in sorted(removed,key=string.lower):
                log(u'* '+eid)
            log.setHeader(u'=== '+_(u'Empty %s Sublists Removed') % label)
            for eid in sorted(cleaned,key=string.lower):
                log(u'* '+eid)

class CBash_ListsMerger(SpecialPatcher,CBash_ListPatcher):
    """Merged leveled lists mod file."""
    scanOrder = 45
    editOrder = 45
    name = _(u'Leveled Lists')
    text = (_(u"Merges changes to leveled lists from ACTIVE/MERGED MODS ONLY.") +
            u'\n\n' +
            _(u'Advanced users may override Relev/Delev tags for any mod (active or inactive) using the list below.')
            )
    tip = _(u"Merges changes to leveled lists from all active mods.")
    choiceMenu = (u'Auto',u'----',u'Delev',u'Relev') #--List of possible choices for each config item. Item 0 is default.
    autoKey = {u'Delev', u'Relev'}
    forceAuto = False
    forceItemCheck = True #--Force configChecked to True for all items
    iiMode = True
    selectCommands = False
    allowUnloaded = False
    scanRequiresChecked = False
    applyRequiresChecked = False
    defaultConfig = {'isEnabled':True,'autoIsChecked':True,'configItems':[],'configChecks':{},'configChoices':{}}

    #--Static------------------------------------------------------------------
    @staticmethod
    def getDefaultTags():
        tags = {}
        for fileName in (u'Leveled Lists.csv',u'My Leveled Lists.csv'):
            textPath = getPatchesPath(fileName)
            if textPath.exists():
                with bolt.CsvReader(textPath) as reader:
                    for fields in reader:
                        if len(fields) < 2 or not fields[0] or fields[1] not in (u'DR',u'R',u'D',u'RD',u''): continue
                        tags[GPath(fields[0])] = fields[1]
        return tags

    #--Config Phase -----------------------------------------------------------
    def getChoice(self,item):
        """Get default config choice."""
        choice = self.configChoices.get(item)
        if not isinstance(choice,set): choice = {u'Auto'}
        if u'Auto' in choice:
            if item in modInfos:
                choice = {u'Auto'}
                bashTags = modInfos[item].getBashTags()
                for key in (u'Delev',u'Relev'):
                    if key in bashTags: choice.add(key)
        self.configChoices[item] = choice
        return choice

    def getItemLabel(self,item):
        """Returns label for item to be used in list"""
        choice = map(itemgetter(0),self.configChoices.get(item,tuple()))
        if isinstance(item,bolt.Path): item = item.s
        if choice:
            return u'%s [%s]' % (item,u''.join(sorted(choice)))
        else:
            return item

    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ListPatcher.initPatchFile(self,patchFile,loadMods)
        self.isActive = True
        self.id_delevs = {}
        self.id_list = {}
        self.id_attrs = {}
        self.mod_count = {}
        self.empties = set()
        importMods = set(self.srcs) & set(loadMods)
        OverhaulCompat = False
        OOOMods = {GPath(u"Oscuro's_Oblivion_Overhaul.esm"),
                   GPath(u"Oscuro's_Oblivion_Overhaul.esp")}
        FransMods = {GPath(u"Francesco's Leveled Creatures-Items Mod.esm"),
                     GPath(u"Francesco.esp")}
        WCMods = {GPath(u"Oblivion Warcry.esp"),
                  GPath(u"Oblivion Warcry EV.esp")}
        TIEMods = {GPath(u"TIE.esp")}
        if GPath(u"Unofficial Oblivion Patch.esp") in importMods:
            if (OOOMods|WCMods) & importMods:
                OverhaulCompat = True
            elif FransMods & importMods:
                if TIEMods & importMods:
                    pass
                else:
                    OverhaulCompat = True
        if OverhaulCompat:
            self.OverhaulUOPSkips = set([
                FormID(GPath(u'Oblivion.esm'),x) for x in [
                    0x03AB5D,   # VendorWeaponBlunt
                    0x03C7F1,   # LL0LootWeapon0Magic4Dwarven100
                    0x03C7F2,   # LL0LootWeapon0Magic7Ebony100
                    0x03C7F3,   # LL0LootWeapon0Magic5Elven100
                    0x03C7F4,   # LL0LootWeapon0Magic6Glass100
                    0x03C7F5,   # LL0LootWeapon0Magic3Silver100
                    0x03C7F7,   # LL0LootWeapon0Magic2Steel100
                    0x03E4D2,   # LL0NPCWeapon0MagicClaymore100
                    0x03E4D3,   # LL0NPCWeapon0MagicClaymoreLvl100
                    0x03E4DA,   # LL0NPCWeapon0MagicWaraxe100
                    0x03E4DB,   # LL0NPCWeapon0MagicWaraxeLvl100
                    0x03E4DC,   # LL0NPCWeapon0MagicWarhammer100
                    0x03E4DD,   # LL0NPCWeapon0MagicWarhammerLvl100
                    0x0733EA,   # ArenaLeveledHeavyShield,
                    0x0C7615,   # FGNPCWeapon0MagicClaymoreLvl100
                    0x181C66,   # SQ02LL0NPCWeapon0MagicClaymoreLvl100
                    0x053877,   # LL0NPCArmor0MagicLightGauntlets100
                    0x053878,   # LL0NPCArmor0MagicLightBoots100
                    0x05387A,   # LL0NPCArmor0MagicLightCuirass100
                    0x053892,   # LL0NPCArmor0MagicLightBootsLvl100
                    0x053893,   # LL0NPCArmor0MagicLightCuirassLvl100
                    0x053894,   # LL0NPCArmor0MagicLightGauntletsLvl100
                    0x053D82,   # LL0LootArmor0MagicLight5Elven100
                    0x053D83,   # LL0LootArmor0MagicLight6Glass100
                    0x052D89,   # LL0LootArmor0MagicLight4Mithril100
                    ]
                ])
        else:
            self.OverhaulUOPSkips = set()

    def getTypes(self):
        return ['LVLC','LVLI','LVSP']

    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        recordId = record.fid
        if recordId in self.OverhaulUOPSkips and modFile.GName == GPath('Unofficial Oblivion Patch.esp'):
            return
        script = record.script
        if script and not script.ValidateFormID(self.patchFile):
            script = None
        template = record.template
        if template and not template.ValidateFormID(self.patchFile):
            template = None
        curList = [(level, listId, count) for level, listId, count in record.entries_list if listId.ValidateFormID(self.patchFile)]
        if recordId not in self.id_list:
            #['level', 'listId', 'count']
            self.id_list[recordId] = curList
            self.id_attrs[recordId] = [record.chanceNone, script, template, (record.flags or 0)]
        else:
            mergedList = self.id_list[recordId]
            configChoice = self.configChoices.get(modFile.GName,tuple())
            isRelev = u'Relev' in configChoice
            isDelev = u'Delev' in configChoice
            delevs = self.id_delevs.setdefault(recordId, set())
            curItems = set([listId for level, listId, count in curList])
            if isRelev:
                #Can add and set the level/count of items, but not delete items
                #Ironically, the first step is to delete items that the list will add right back
                #This is an easier way to update level/count than actually checking if they need changing

                #Filter out any records that may have their level/count updated
                mergedList = [entry for entry in mergedList if entry[1] not in curItems] #entry[1] = listId
                #Add any new records as well as any that were filtered out
                mergedList += curList
                #Remove the added items from the deleveled list
                delevs -= curItems
                self.id_attrs[recordId] = [record.chanceNone, script, template, (record.flags or 0)]
            else:
                #Can add new items, but can't change existing ones
                items = set([entry[1] for entry in mergedList]) #entry[1] = listId
                mergedList += [(level, listId, count) for level, listId, count in curList if listId not in items]
                mergedAttrs = self.id_attrs[recordId]
                self.id_attrs[recordId] = [record.chanceNone or mergedAttrs[0], script or mergedAttrs[1], template or mergedAttrs[2], (record.flags or 0) | mergedAttrs[3]]
            #--Delevs: all items in masters minus current items
            if isDelev:
                deletedItems = set([listId for master in record.History() for level, listId, count in master.entries_list if listId.ValidateFormID(self.patchFile)]) - curItems
                delevs |= deletedItems

            #Remove any items that were deleveled
            mergedList = [entry for entry in mergedList if entry[1] not in delevs] #entry[1] = listId
            self.id_list[recordId] = mergedList
            self.id_delevs[recordId] = delevs

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        recordId = record.fid
        merged = recordId in self.id_list
        if merged:
            self.scan(modFile,record,bashTags)
            mergedList = self.id_list[recordId]
            mergedAttrs = self.id_attrs[recordId]
            newList = [(level, listId, count) for level, listId, count in record.entries_list if listId.ValidateFormID(self.patchFile)]
            script = record.script
            if script and not script.ValidateFormID(self.patchFile):
                script = None
            template = record.template
            if template and not template.ValidateFormID(self.patchFile):
                template = None
            newAttrs = [record.chanceNone, script, template, (record.flags or 0)]
        #Can't tell if any sublists are actually empty until they've all been processed/merged
        #So every level list gets copied into the patch, so that they can be checked after the regular patch process
        #They'll get deleted from the patch there as needed.
        override = record.CopyAsOverride(self.patchFile)
        if override:
            if merged and (newAttrs != mergedAttrs or sorted(newList, key=itemgetter(1)) != sorted(mergedList, key=itemgetter(1))):
                override.chanceNone, override.script, override.template, override.flags = mergedAttrs
                override.entries_list = mergedList
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
            record.UnloadRecord()
            record._RecordID = override._RecordID

    def finishPatch(self,patchFile, progress):
        """Edits the bashed patch file directly."""
        if self.empties is None: return
        subProgress = SubProgress(progress)
        subProgress.setFull(len(self.getTypes()))
        pstate = 0
        #Clean up any empty sublists
        empties = self.empties
        emptiesAdd = empties.add
        emptiesDiscard = empties.discard
        for type in self.getTypes():
            subProgress(pstate, _(u'Looking for empty %s sublists...')%type + u'\n')
            #Remove any empty sublists
            madeChanges = True
            while madeChanges:
                madeChanges = False
                oldEmpties = empties.copy()
                for record in getattr(patchFile,type):
                    recordId = record.fid
                    items = set([entry.listId for entry in record.entries])
                    if items:
                        emptiesDiscard(recordId)
                    else:
                        emptiesAdd(recordId)
                    toRemove = empties & items
                    if toRemove:
                        madeChanges = True
                        cleanedEntries = [entry for entry in record.entries if entry.listId not in toRemove]
                        record.entries = cleanedEntries
                        if cleanedEntries:
                            emptiesDiscard(recordId)
                        else:
                            emptiesAdd(recordId)
                if oldEmpties != empties:
                    oldEmpties = empties.copy()
                    madeChanges = True

            #Remove any identical to winning lists, except those that were merged into the patch
            for record in getattr(patchFile,type):
                conflicts = record.Conflicts()
                numConflicts = len(conflicts)
                if numConflicts:
                    curConflict = 1 #Conflict at 0 will be the patchfile. No sense comparing it to itself.
                    #Find the first conflicting record that wasn't merged
                    while curConflict < numConflicts:
                        prevRecord = conflicts[curConflict]
                        if prevRecord.GetParentMod().GName not in patchFile.mergeSet:
                            break
                        curConflict += 1
                    else:
                        continue
                    #If the record in the patchfile matches the previous non-merged record, delete it.
                    #Ordering doesn't matter, hence the conversion to sets
                    if set(prevRecord.entries_list) == set(record.entries_list) and [record.chanceNone, record.script, record.template, record.flags] == [prevRecord.chanceNone, prevRecord.script, prevRecord.template, prevRecord.flags]:
                        record.DeleteRecord()
            pstate += 1
        self.empties = None

    def buildPatchLog(self,log):
        """Will write to log."""
        #--Log
        mod_count = self.mod_count
        log.setHeader(u'= ' +self.__class__.name)
        log(u'* '+_(u'Modified LVL: %d') % (sum(mod_count.values()),))
        for srcMod in modInfos.getOrdered(mod_count.keys()):
            log(u'  * %s: %d' % (srcMod.s,mod_count[srcMod]))
        self.mod_count = {}

#------------------------------------------------------------------------------
class MFactMarker(SpecialPatcher,ListPatcher):
    """Mark factions that player can acquire while morphing."""
    name = _(u'Morph Factions')
    text = (_(u"Mark factions that player can acquire while morphing.") +
            u'\n\n' +
            _(u"Requires Cobl 1.28 and Wrye Morph or similar.")
            )
    autoRe = re.compile(ur"^UNDEFINED$",re.I|re.U)
    autoKey = 'MFact'
    canAutoItemCheck = False #--GUI: Whether new items are checked by default or not.

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.id_info = {} #--Morphable factions keyed by fid
        self.srcFiles = self.getConfigChecked()
        self.isActive = bool(self.srcFiles) and GPath(u"Cobl Main.esm") in modInfos.ordered
        self.mFactLong = (GPath(u"Cobl Main.esm"),0x33FB)

    def initData(self,progress):
        """Get names from source files."""
        if not self.isActive: return
        aliases = self.patchFile.aliases
        id_info = self.id_info
        for srcFile in self.srcFiles:
            textPath = getPatchesPath(srcFile)
            if not textPath.exists(): continue
            with bolt.CsvReader(textPath) as ins:
                for fields in ins:
                    if len(fields) < 6 or fields[1][:2] != u'0x':
                        continue
                    mod,objectIndex = fields[:2]
                    mod = GPath(mod)
                    longid = (aliases.get(mod,mod),int(objectIndex,0))
                    morphName = fields[4].strip()
                    rankName = fields[5].strip()
                    if not morphName: continue
                    if not rankName: rankName = _(u'Member')
                    id_info[longid] = (morphName,rankName)

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('FACT',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('FACT',) if self.isActive else ()

    def scanModFile(self, modFile, progress):
        """Scan modFile."""
        if not self.isActive: return
        id_info = self.id_info
        modName = modFile.fileInfo.name
        mapper = modFile.getLongMapper()
        patchBlock = self.patchFile.FACT
        if modFile.fileInfo.name == GPath(u"Cobl Main.esm"):
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
                        rank.insigniaPath = u'Menus\\Stats\\Cobl\\generic%02d.dds' % rank.rank
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
        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods/Files'))
        for file in self.srcFiles:
            log(u'* ' +file.s)
        log(u'\n=== '+_(u'Morphable Factions'))
        for mod in sorted(changed):
            log(u'* %s: %d' % (mod.s,changed[mod]))

class CBash_MFactMarker(SpecialPatcher,CBash_ListPatcher):
    """Mark factions that player can acquire while morphing."""
    name = _(u'Morph Factions')
    text = (_(u"Mark factions that player can acquire while morphing.") +
            u'\n\n' +
            _(u"Requires Cobl 1.28 and Wrye Morph or similar.")
            )
    autoRe = re.compile(ur"^UNDEFINED$",re.I|re.U)
    autoKey = {'MFact'}
    unloadedText = u""
    canAutoItemCheck = False #--GUI: Whether new items are checked by default or not.

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_ListPatcher.initPatchFile(self,patchFile,loadMods)
        if not self.isActive: return
        self.cobl = GPath(u'Cobl Main.esm')
        self.isActive = self.cobl in loadMods and modInfos.getVersionFloat(self.cobl) > 1.27
        self.id_info = {} #--Morphable factions keyed by fid
        self.mFactLong = FormID(self.cobl,0x33FB)
        self.mod_count = {}
        self.mFactable = set()

    def initData(self,group_patchers,progress):
        """Compiles material, i.e. reads source text, esp's, etc. as necessary."""
        if not self.isActive: return
        for type in self.getTypes():
            group_patchers.setdefault(type,[]).append(self)
        progress.setFull(len(self.srcs))
        for srcFile in self.srcs:
            srcPath = GPath(srcFile)
            patchesList = getPatchesList()
            if srcPath not in patchesList: continue
            self.readFromText(getPatchesPath(srcFile))
            progress.plus()

    def getTypes(self):
        return ['FACT']

    def readFromText(self,textPath):
        """Imports id_info from specified text file."""
        aliases = self.patchFile.aliases
        id_info = self.id_info
        textPath = GPath(textPath)
        if not textPath.exists(): return
        with bolt.CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 6 or fields[1][:2] != u'0x':
                    continue
                mod,objectIndex = fields[:2]
                mod = GPath(mod)
                longid = FormID(aliases.get(mod,mod),int(objectIndex,0))
                morphName = fields[4].strip()
                rankName = fields[5].strip()
                if not morphName: continue
                if not rankName: rankName = _(u'Member')
                id_info[longid] = (morphName,rankName)

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        id_info = self.id_info
        recordId = record.fid
        mFactLong = self.mFactLong
        if recordId in id_info and recordId != mFactLong:
            self.mFactable.add(recordId)
            if mFactLong not in [relation.faction for relation in record.relations]:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.IsHiddenFromPC = False
                    relation = override.create_relation()
                    relation.faction = mFactLong
                    relation.mod = 10
                    mname,rankName = id_info[recordId]
                    override.full = mname
                    ranks = override.ranks or [override.create_rank()]
                    for rank in ranks:
                        if not rank.male: rank.male = rankName
                        if not rank.female: rank.female = rank.male
                        if not rank.insigniaPath:
                            rank.insigniaPath = u'Menus\\Stats\\Cobl\\generic%02d.dds' % rank.rank
                    mod_count = self.mod_count
                    mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def finishPatch(self,patchFile,progress):
        """Edits the bashed patch file directly."""
        mFactable = self.mFactable
        if not mFactable: return
        subProgress = SubProgress(progress)
        subProgress.setFull(max(len(mFactable),1))
        pstate = 0
        coblMod = patchFile.Current.LookupModFile(self.cobl.s)

        record = coblMod.LookupRecord(self.mFactLong)
        if record.recType != 'FACT':
            print PrintFormID(self.mFactLong)
            print patchFile.Current.Debug_DumpModFiles()
            print record
            raise StateError(u"Cobl Morph Factions: Unable to lookup morphable faction record in Cobl Main.esm!")

        override = record.CopyAsOverride(patchFile)
        if override:
            override.relations = None
            pstate = 0
            for faction in mFactable:
                subProgress(pstate, _(u'Marking Morphable Factions...')+u'\n')
                relation = override.create_relation()
                relation.faction = faction
                relation.mod = 10
                pstate += 1
        mFactable.clear()

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        mod_count = self.mod_count
        log.setHeader(u'= '+self.__class__.name)
        log(u'=== '+_(u'Source Mods/Files'))
        for file in self.srcs:
            log(u'* '+file.s)
        log(u'\n=== '+_(u'Morphable Factions'))
        for srcMod in modInfos.getOrdered(mod_count.keys()):
            log(u'* %s: %d' % (srcMod.s,mod_count[srcMod]))
        self.mod_count = {}

#------------------------------------------------------------------------------
class SEWorldEnforcer(SpecialPatcher,Patcher):
    """Suspends Cyrodiil quests while in Shivering Isles."""
    name = _(u'SEWorld Tests')
    text = _(u"Suspends Cyrodiil quests while in Shivering Isles. I.e. re-instates GetPlayerInSEWorld tests as necessary.")
    defaultConfig = {'isEnabled':True}

    #--Config Phase -----------------------------------------------------------
    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.cyrodiilQuests = set()
        if GPath(u'Oblivion.esm') in loadMods:
            loadFactory = LoadFactory(False,MreRecord.type_class['QUST'])
            modInfo = modInfos[GPath(u'Oblivion.esm')]
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
        return ('QUST',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('QUST',) if self.isActive else ()

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        if not self.isActive: return
        if modFile.fileInfo.name == GPath(u'Oblivion.esm'): return
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
        log(u'==='+_(u'Quests Patched: %d') % (len(patched),))

class CBash_SEWorldEnforcer(SpecialPatcher,CBash_Patcher):
    """Suspends Cyrodiil quests while in Shivering Isles."""
    name = _(u'SEWorld Tests')
    text = _(u"Suspends Cyrodiil quests while in Shivering Isles. I.e. re-instates GetPlayerInSEWorld tests as necessary.")
    scanRequiresChecked = True
    applyRequiresChecked = False
    defaultConfig = {'isEnabled':True}

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_Patcher.initPatchFile(self,patchFile,loadMods)
        self.cyrodiilQuests = set()
        self.srcs = [GPath(u'Oblivion.esm')]
        self.isActive = self.srcs[0] in loadMods
        self.mod_eids = {}

    def getTypes(self):
        return ['QUST']

    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        for condition in record.conditions:
            if condition.ifunc == 365 and condition.compValue == 0:
                self.cyrodiilQuests.add(record.fid)
                return

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        if modFile.GName in self.srcs: return

        recordId = record.fid
        if recordId in self.cyrodiilQuests:
            for condition in record.conditions:
                if condition.ifunc == 365: return #--365: playerInSeWorld
            else:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    conditions = override.conditions
                    condition = override.create_condition()
                    condition.ifunc = 365
                    conditions.insert(0,condition)
                    override.conditions = conditions
                    self.mod_eids.setdefault(modFile.GName,[]).append(override.eid)
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        mod_eids = self.mod_eids
        log.setHeader(u'= ' +self.__class__.name)
        log(u'\n=== '+_(u'Quests Patched'))
        for mod,eids in mod_eids.iteritems():
            log(u'* %s: %d' % (mod.s,len(eids)))
            for eid in sorted(eids):
                log(u'  * %s' % eid)
        self.mod_eids = {}

#------------------------------------------------------------------------------
class ContentsChecker(SpecialPatcher,Patcher):
    """Checks contents of leveled lists, inventories and containers for correct content types."""
    scanOrder = 50
    editOrder = 50
    name = _(u'Contents Checker')
    text = _(u"Checks contents of leveled lists, inventories and containers for correct types.")
    defaultConfig = {'isEnabled':True}

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        Patcher.initPatchFile(self,patchFile,loadMods)
        self.contType_entryTypes = {
            'LVSP':'LVSP,SPEL'.split(','),
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
        return tuple(self.contTypes + self.entryTypes) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return tuple(self.contTypes) if self.isActive else ()

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
                    log(u"\n=== "+type)
                    for contId in sorted(id_removed):
                        log(u'* ' + id_eid[contId])
                        for removedId in sorted(id_removed[contId]):
                            mod,index = removedId
                            log(u'  . %s: %06X' % (mod.s,index))

class CBash_ContentsChecker(SpecialPatcher,CBash_Patcher):
    """Checks contents of leveled lists, inventories and containers for correct content types."""
    scanOrder = 50
    editOrder = 50
    name = _(u'Contents Checker')
    text = _(u"Checks contents of leveled lists, inventories and containers "
             u"for correct types.")
    srcs = [] #so as not to fail screaming when determining load mods - but
    # with the least processing required.
    defaultConfig = {'isEnabled':True}

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        """Prepare to handle specified patch mod. All functions are called after this."""
        CBash_Patcher.initPatchFile(self,patchFile,loadMods)
        self.isActive = True
        self.type_validEntries = {'LVSP': {'LVSP', 'SPEL'},
                                'LVLC': {'LVLC', 'NPC_', 'CREA'},
                                'LVLI': {'LVLI', 'ALCH', 'AMMO', 'APPA',
                                         'ARMO', 'BOOK', 'CLOT', 'INGR',
                                         'KEYM', 'LIGH', 'MISC', 'SGST',
                                         'SLGM', 'WEAP'},
                                'CONT': {'LVLI', 'ALCH', 'AMMO', 'APPA',
                                         'ARMO', 'BOOK', 'CLOT', 'INGR',
                                         'KEYM', 'LIGH', 'MISC', 'SGST',
                                         'SLGM', 'WEAP'},
                                'CREA': {'LVLI', 'ALCH', 'AMMO', 'APPA',
                                         'ARMO', 'BOOK', 'CLOT', 'INGR',
                                         'KEYM', 'LIGH', 'MISC', 'SGST',
                                         'SLGM', 'WEAP'},
                                'NPC_': {'LVLI', 'ALCH', 'AMMO', 'APPA',
                                         'ARMO', 'BOOK', 'CLOT', 'INGR',
                                         'KEYM', 'LIGH', 'MISC', 'SGST',
                                         'SLGM', 'WEAP'}}
        self.listTypes = {'LVSP', 'LVLC', 'LVLI'}
        self.containerTypes = {'CONT', 'CREA', 'NPC_'}
        self.mod_type_id_badEntries = {}
        self.knownGood = set()

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['CONT','CREA','NPC_','LVLI','LVLC','LVSP']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        type = record._Type
        Current = self.patchFile.Current
        badEntries = set()
        goodEntries = []
        knownGood = self.knownGood
        knownGoodAdd = knownGood.add
        goodAppend = goodEntries.append
        badAdd = badEntries.add
        validEntries = self.type_validEntries[type]
        if type in self.listTypes:
            topattr, subattr = ('entries','listId')
        else: #Is a container type
            topattr, subattr = ('items','item')

        for entry in getattr(record,topattr):
            entryId = getattr(entry,subattr)
            #Cache known good entries to decrease execution time
            if entryId in knownGood:
                goodAppend(entry)
            else:
                if entryId.ValidateFormID(self.patchFile):
                    entryRecords = Current.LookupRecords(entryId)
                else:
                    entryRecords = None
                if not entryRecords:
                    badAdd((_(u'NONE'),entryId,None,_(u'NONE')))
                else:
                    entryRecord = entryRecords[0]
                    if entryRecord.recType in validEntries:
                        knownGoodAdd(entryId)
                        goodAppend(entry)
                    else:
                        badAdd((entryRecord.eid,entryId,entryRecord.GetParentMod().GName,entryRecord.recType))
                        entryRecord.UnloadRecord()

        if badEntries:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                setattr(override, topattr, goodEntries)
                type_id_badEntries = self.mod_type_id_badEntries.setdefault(modFile.GName, {})
                id_badEntries = type_id_badEntries.setdefault(type, {})
                id_badEntries[record.eid] = badEntries.copy()
                record.UnloadRecord()
                record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        if not self.isActive: return
        #--Log
        mod_type_id_badEntries = self.mod_type_id_badEntries
        log.setHeader(u'= ' +self.__class__.name)
        for mod, type_id_badEntries in mod_type_id_badEntries.iteritems():
            log(u'\n=== %s' % mod.s)
            for type,id_badEntries in type_id_badEntries.iteritems():
                log(u'  * '+_(u'Cleaned %s: %d') % (type,len(id_badEntries)))
                for id, badEntries in id_badEntries.iteritems():
                    log(u'    * %s : %d' % (id,len(badEntries)))
                    for entry in sorted(badEntries, key=itemgetter(0)):
                        longId = entry[1]
                        if entry[2]:
                            modName = entry[2].s
                        else:
                            try:
                                modName = longId[0].s
                            except:
                                log(u'        . '+_(u'Unloaded Object or Undefined Reference'))
                                continue
                        log(u'        . '+_(u'Editor ID: "%s", Object ID %06X: Defined in mod "%s" as %s') % (entry[0],longId[1],modName,entry[3]))
        self.mod_type_id_badEntries = {}

# Initialization --------------------------------------------------------------

#  Import win32com, in case it's necessary
try:
        from win32com.shell import shell, shellcon
        def getShellPath(shellKey):
            path = shell.SHGetFolderPath (0, shellKey, None, 0)
            return GPath(path)
except ImportError:
        shell = shellcon = None
        reEnv = re.compile(u'%(\w+)%',re.U)
        envDefs = os.environ
        def subEnv(match):
            key = match.group(1).upper()
            if not envDefs.get(key):
                raise BoltError(u"Can't find user directories in windows registry.\n>> See \"If Bash Won't Start\" in bash docs for help.")
            return envDefs[key]
        def getShellPath(folderKey):
            import _winreg
            regKey = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER,
                u'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\User Shell Folders')
            try:
                path = _winreg.QueryValueEx(regKey,folderKey)[0]
            except WindowsError:
                raise BoltError(u"Can't find user directories in windows registry.\n>> See \"If Bash Won't Start\" in bash docs for help.")
            regKey.Close()
            path = reEnv.sub(subEnv,path)
            return GPath(path)

def testPermissions(path,permissions='rwcd'):
    """Test file permissions for a path:
        r = read permission
        w = write permission
        c = file creation permission
        d = file deletion permission"""
    return True # Temporarily disabled, for testing purposes
    path = GPath(path)
    permissions = permissions.lower()
    def getTemp(path):  # Get a temp file name
        if path.isdir():
            temp = path.join(u'temp.tmp')
        else:
            temp = path.temp
        while temp.exists():
            temp = temp.temp
        return temp
    def getSmallest(path):  # Get the smallest file in the directory,
        if path.isfile(): return path
        smallsize = -1
        ret = None
        for file in path.list():
            file = path.join(file)
            if not file.isfile(): continue
            size = file.size
            if size < smallsize and smallsize >= 0:
                smallsize = size
                ret = file
        return ret
    #--Test read permissions
    try:
        if 'r' in permissions and path.exists():
            file = getSmallest(path)
            if file:
                with path.open('rb') as file:
                    pass
        #--Test write permissions
        if 'w' in permissions and path.exists():
            file = getSmallest(path)
            if file:
                with file.open('ab') as file:
                    pass
        #--Test file creation permission (only for directories)
        if 'c' in permissions:
            if path.isdir() or not path.exists():
                if not path.exists():
                    path.makedirs()
                    removeAtEnd = True
                else:
                    removeAtEnd = False
                temp = getTemp(path)
                with temp.open('wb') as file:
                    pass
                temp.remove()
                if removeAtEnd:
                    path.removedirs()
        #--Test file deletion permission
        if 'd' in permissions and path.exists():
            file = getSmallest(path)
            if file:
                temp = getTemp(file)
                file.copyTo(temp)
                file.remove()
                temp.moveTo(file)
    except Exception, e:
        if getattr(e,'errno',0) == 13: # Access denied
            return False
        elif getattr(e,'winerror',0) == 183: # Cannot create file if already exists
            return False
        else: raise
    return True

def getOblivionPath(bashIni, path):
    if path:
        # Already handled by bush.setGame, but we don't want to use
        # The sOblivionPath ini entry if a path was specified on the
        # command line
        pass
    elif bashIni and bashIni.has_option(u'General', u'sOblivionPath') and not bashIni.get(u'General', u'sOblivionPath') == u'.':
        path = GPath(bashIni.get(u'General', u'sOblivionPath').strip())
        # Validate it:
        oldMode = bush.game.displayName
        ret = bush.setGame('',path.s)
        if ret != False:
            deprint(u'Warning: The path specified for sOblivionPath in bash.ini does not point to a valid game directory.  Continuing startup in %s mode.' % bush.game.displayName)
        elif oldMode != bush.game.displayName:
            deprint(u'Set game mode to %s based on sOblivionPath setting in bash.ini' % bush.game.displayName)
    path = bush.gamePath
    #--If path is relative, make absolute
    if not path.isabs(): path = dirs['mopy'].join(path)
    #--Error check
    if not path.join(bush.game.exe).exists():
        raise BoltError(
            u"Install Error\nFailed to find %s in %s.\nNote that the Mopy folder should be in the same folder as %s." % (bush.game.exe, path, bush.game.exe))
    return path

def getPersonalPath(bashIni, path):
    #--Determine User folders from Personal and Local Application Data directories
    #  Attempt to pull from, in order: Command Line, Ini, win32com, Registry
    if path:
        path = GPath(path)
        sErrorInfo = _(u"Folder path specified on command line (-p)")
    elif bashIni and bashIni.has_option(u'General', u'sPersonalPath') and not bashIni.get(u'General', u'sPersonalPath') == u'.':
        path = GPath(bashIni.get('General', 'sPersonalPath').strip())
        sErrorInfo = _(u"Folder path specified in bash.ini (%s)") % u'sPersonalPath'
    elif shell and shellcon:
        path = getShellPath(shellcon.CSIDL_PERSONAL)
        sErrorInfo = _(u"Folder path extracted from win32com.shell.")
    else:
        path = getShellPath('Personal')
        sErrorInfo = u'\n'.join(u'  %s: %s' % (key,envDefs[key]) for key in sorted(envDefs))
    #  If path is relative, make absolute
    if not path.isabs():
        path = dirs['app'].join(path)
    #  Error check
    if not path.exists():
        raise BoltError(u"Personal folder does not exist.\nPersonal folder: %s\nAdditional info:\n%s"
            % (path.s, sErrorInfo))
    return path

def getLocalAppDataPath(bashIni, path):
    #--Determine User folders from Personal and Local Application Data directories
    #  Attempt to pull from, in order: Command Line, Ini, win32com, Registry
    if path:
        path = GPath(path)
        sErrorInfo = _(u"Folder path specified on command line (-l)")
    elif bashIni and bashIni.has_option(u'General', u'sLocalAppDataPath') and not bashIni.get(u'General', u'sLocalAppDataPath') == u'.':
        path = GPath(bashIni.get(u'General', u'sLocalAppDataPath').strip())
        sErrorInfo = _(u"Folder path specified in bash.ini (%s)") % u'sLocalAppDataPath'
    elif shell and shellcon:
        path = getShellPath(shellcon.CSIDL_LOCAL_APPDATA)
        sErrorInfo = _(u"Folder path extracted from win32com.shell.")
    else:
        path = getShellPath('Local AppData')
        sErrorInfo = u'\n'.join(u'  %s: %s' % (key,envDefs[key]) for key in sorted(envDefs))
    #  If path is relative, make absolute
    if not path.isabs():
        path = dirs['app'].join(path)
    #  Error check
    if not path.exists():
        raise BoltError(u"Local AppData folder does not exist.\nLocal AppData folder: %s\nAdditional info:\n%s"
            % (path.s, sErrorInfo))
    return path

def getOblivionModsPath(bashIni):
    if bashIni and bashIni.has_option(u'General',u'sOblivionMods'):
        path = GPath(bashIni.get(u'General',u'sOblivionMods').strip())
        src = [u'[General]', u'sOblivionMods']
    else:
        path = GPath(u'..\\%s Mods' % bush.game.fsName)
        src = u'Relative Path'
    if not path.isabs(): path = dirs['app'].join(path)
    return path, src

def getBainDataPath(bashIni):
    if bashIni and bashIni.has_option(u'General',u'sInstallersData'):
        path = GPath(bashIni.get(u'General',u'sInstallersData').strip())
        src = [u'[General]', u'sInstallersData']
        if not path.isabs(): path = dirs['app'].join(path)
    else:
        path = dirs['installers'].join(u'Bash')
        src = u'Relative Path'
    return path, src

def getBashModDataPath(bashIni):
    if bashIni and bashIni.has_option(u'General',u'sBashModData'):
        path = GPath(bashIni.get(u'General',u'sBashModData').strip())
        if not path.isabs(): path = dirs['app'].join(path)
        src = [u'[General]', u'sBashModData']
    else:
        path, src = getOblivionModsPath(bashIni)
        path = path.join(u'Bash Mod Data')
    return path, src

def getLegacyPath(newPath, oldPath, srcNew=None, srcOld=None):
    return (oldPath,newPath)[newPath.isdir() or not oldPath.isdir()]

def getLegacyPathWithSource(newPath, oldPath, newSrc, oldSrc=None):
    if newPath.isdir() or not oldPath.isdir():
        return newPath, newSrc
    else:
        return oldPath, oldSrc

def testUAC(oblivionPath):
    print 'testing UAC'
    #--Bash Ini
    bashIni = None
    if GPath(u'bash.ini').exists():
        try:
            bashIni = ConfigParser.ConfigParser()
            bashIni.read(u'bash.ini')
        except:
            bashIni = None

    dir = getOblivionPath(bashIni,oblivionPath).join(u'Data')
    tempDir = bolt.Path.tempDir(u'WryeBash_')
    tempFile = tempDir.join(u'_tempfile.tmp')
    dest = dir.join(u'_tempfile.tmp')
    with tempFile.open('wb') as out:
        pass
    try:
        balt.fileOperation(balt.FO_MOVE,tempFile,dest,False,False,False,True,None)
    except balt.AccessDeniedError:
        return True
    finally:
        tempDir.rmtree(safety=tempDir.stail)
        if dest.exists():
            try:
                balt.shellDelete(dest,None,False,False)
            except:
                pass
    return False

def initDirs(bashIni, personal, localAppData, oblivionPath):
    #--Mopy directories
    dirs['mopy'] = bolt.Path.getcwd().root
    dirs['bash'] = dirs['mopy'].join(u'bash')
    dirs['compiled'] = dirs['bash'].join(u'compiled')
    dirs['l10n'] = dirs['bash'].join(u'l10n')
    dirs['db'] = dirs['bash'].join(u'db')
    dirs['templates'] = dirs['mopy'].join(u'templates')
    dirs['images'] = dirs['bash'].join(u'images')

    #--Oblivion (Application) Directories
    dirs['app'] = getOblivionPath(bashIni,oblivionPath)
    dirs['mods'] = dirs['app'].join(u'Data')
    dirs['builds'] = dirs['app'].join(u'Builds')
    dirs['patches'] = dirs['mods'].join(u'Bash Patches')
    dirs['defaultPatches'] = dirs['mopy'].join(u'Bash Patches',bush.game.fsName)
    dirs['tweaks'] = dirs['mods'].join(u'INI Tweaks')
    dirs['defaultTweaks'] = dirs['mopy'].join(u'INI Tweaks',bush.game.fsName)

    #  Personal
    personal = getPersonalPath(bashIni,personal)
    dirs['saveBase'] = personal.join(u'My Games',bush.game.fsName)

    #  Local Application Data
    localAppData = getLocalAppDataPath(bashIni,localAppData)
    dirs['userApp'] = localAppData.join(bush.game.fsName)

    # Use local paths if bUseMyGamesDirectory=0 in Oblivion.ini
    global gameInis
    global oblivionIni
    gameInis = [OblivionIni(x) for x in bush.game.iniFiles]
    oblivionIni = gameInis[0]
    try:
        if oblivionIni.getSetting(u'General',u'bUseMyGamesDirectory',u'1') == u'0':
            # Set the save game folder to the Oblivion directory
            dirs['saveBase'] = dirs['app']
            # Set the data folder to sLocalMasterPath
            dirs['mods'] = dirs['app'].join(oblivionIni.getSetting(u'General', u'SLocalMasterPath',u'Data\\'))
            # these are relative to the mods path so they must be updated too
            dirs['patches'] = dirs['mods'].join(u'Bash Patches')
            dirs['tweaks'] = dirs['mods'].join(u'INI Tweaks')
    except:
        # Error accessing folders for Oblivion.ini
        # We'll show an error later
        pass

    #--Mod Data, Installers
    oblivionMods, oblivionModsSrc = getOblivionModsPath(bashIni)
    dirs['modsBash'], modsBashSrc = getBashModDataPath(bashIni)
    dirs['modsBash'], modsBashSrc = getLegacyPathWithSource(
        dirs['modsBash'], dirs['app'].join(u'Data',u'Bash'),
        modsBashSrc, u'Relative Path')

    dirs['installers'] = oblivionMods.join(u'Bash Installers')
    dirs['installers'] = getLegacyPath(dirs['installers'],dirs['app'].join(u'Installers'))

    dirs['bainData'], bainDataSrc = getBainDataPath(bashIni)

    dirs['bsaCache'] = dirs['bainData'].join(u'BSA Cache')

    dirs['converters'] = dirs['installers'].join(u'Bain Converters')
    dirs['dupeBCFs'] = dirs['converters'].join(u'--Duplicates')
    dirs['corruptBCFs'] = dirs['converters'].join(u'--Corrupt')

    #--Test correct permissions for the directories
    badPermissions = []
    for dir in dirs:
        if not testPermissions(dirs[dir]):
            badPermissions.append(dirs[dir])
    if not testPermissions(oblivionMods):
        badPermissions.append(oblivionMods)
    if len(badPermissions) > 0:
        # Do not have all the required permissions for all directories
        # TODO: make this gracefully degrade.  IE, if only the BAIN paths are
        # bad, just disable BAIN.  If only the saves path is bad, just disable
        # saves related stuff.
        msg = balt.fill(_(u'Wrye Bash cannot access the following paths:'))
        msg += u'\n\n'+ u'\n'.join([u' * '+dir.s for dir in badPermissions]) + u'\n\n'
        msg += balt.fill(_(u'See: "Wrye Bash.html, Installation - Windows Vista/7" for information on how to solve this problem.'))
        raise PermissionError(msg)

    # create bash user folders, keep these in order
    try:
        keys = ('modsBash', 'installers', 'converters', 'dupeBCFs',
                'corruptBCFs', 'bainData', 'bsaCache')
        balt.shellMakeDirs([dirs[key] for key in keys])
    except BoltError as e:
        # BoltError is thrown by shellMakeDirs if any of the directories
        # cannot be created due to residing on a non-existing drive.
        # Find which keys are causing the errors
        badKeys = set()     # List of dirs[key] items that are invalid
        # First, determine which dirs[key] items are causing it
        for key in keys:
            if dirs[key] in e.message:
                badKeys.add(key)
        # Now, work back from those to determine which setting created those
        msg = (_(u'Error creating required Wrye Bash directories.') + u'  ' +
               _(u'Please check the settings for the following paths in your bash.ini, the drive does not exist')
               + u':\n\n')
        relativePathError = []
        if 'modsBash' in badKeys:
            if isinstance(modsBashSrc, list):
                msg += (u' '.join(modsBashSrc) + u'\n    '
                        + dirs['modsBash'].s + u'\n')
            else:
                relativePathError.append(dirs['modsBash'])
        if {'installers', 'converters', 'dupeBCFs', 'corruptBCFs'} & badKeys:
            # All derived from oblivionMods -> getOblivionModsPath
            if isinstance(oblivionModsSrc, list):
                msg += (u' '.join(oblivionModsSrc) + u'\n    '
                        + oblivionMods.s + u'\n')
            else:
                relativePathError.append(oblivionMods)
        if {'bainData', 'bsaCache'} & badKeys:
            # Both derived from 'bainData' -> getBainDataPath
            # Sometimes however, getBainDataPath falls back to oblivionMods,
            # So check to be sure we haven't already added a message about that
            if bainDataSrc != oblivionModsSrc:
                if isinstance(bainDataSrc, list):
                    msg += (u' '.join(bainDataSrc) + u'\n    '
                            + dirs['bainData'].s + u'\n')
                else:
                    relativePathError.append(dirs['bainData'])
        if relativePathError:
            msg += (u'\n' +
                    _(u'A path error was the result of relative paths.')
                    + u'  ' +
                    _(u'The following paths are causing the errors, however usually a relative path should be fine.')
                    + u'  ' +
                    _(u'Check your setup to see if you are using symbolic links or NTFS Junctions')
                    + u':\n\n')
            msg += u'\n'.join(relativePathError)
        raise BoltError(msg)

    # Setup LOOT API
    global configHelpers
    configHelpers = ConfigHelpers()

def initLinks(appDir):
    #-- Other tools
    global links
    links = {}
    try:
        import win32com.client
        sh = win32com.client.Dispatch('WScript.Shell')
        shCreateShortCut = sh.CreateShortCut
        appDirJoin = appDir.join
        for file in appDir.list():
            file = appDirJoin(file)
            if file.isfile() and file.cext == u'.lnk':
                fileS = file.s
                shortcut = shCreateShortCut(fileS)
                description = shortcut.Description
                if not description:
                    description = u' '.join((_(u'Launch'),file.sbody))
                links[fileS] = (shortcut.TargetPath,shortcut.WorkingDirectory,shortcut.Arguments,shortcut.IconLocation,description)
    except:
        deprint(_(u"Error initializing links:"),traceback=True)

def initDefaultTools():
    #-- Other tool directories
    #   First to default path
    pf = [GPath(u'C:\\Program Files'),GPath(u'C:\\Program Files (x86)')]
    def pathlist(*args): return [x.join(*args) for x in pf]

    # BOSS can be in any number of places.
    # Detect locally installed (into game folder) BOSS
    if dirs['app'].join(u'BOSS',u'BOSS.exe').exists():
        tooldirs['boss'] = dirs['app'].join(u'BOSS').join(u'BOSS.exe')
    else:
        tooldirs['boss'] = GPath(u'C:\\**DNE**')
        # Detect globally installed (into Program Files) BOSS
        try:
            import _winreg
            for hkey in (_winreg.HKEY_CURRENT_USER, _winreg.HKEY_LOCAL_MACHINE):
                for wow6432 in (u'',u'Wow6432Node\\'):
                    try:
                        key = _winreg.OpenKey(hkey,u'Software\\%sBoss' % wow6432)
                        value = _winreg.QueryValueEx(key,u'Installed Path')
                    except:
                        continue
                    if value[1] != _winreg.REG_SZ: continue
                    installedPath = GPath(value[0])
                    if not installedPath.exists(): continue
                    tooldirs['boss'] = installedPath.join(u'BOSS.exe')
                    break
                else:
                    continue
                break
        except ImportError:
            pass

    tooldirs['Tes4FilesPath'] = dirs['app'].join(u'Tools',u'TES4Files.exe')
    tooldirs['Tes4EditPath'] = dirs['app'].join(u'TES4Edit.exe')
    tooldirs['Tes5EditPath'] = dirs['app'].join(u'TES5Edit.exe')
    tooldirs['Tes4LodGenPath'] = dirs['app'].join(u'TES4LodGen.exe')
    tooldirs['Tes4GeckoPath'] = dirs['app'].join(u'Tes4Gecko.jar')
    tooldirs['Tes5GeckoPath'] = pathlist(u'Dark Creations',u'TESVGecko',u'TESVGecko.exe')
    tooldirs['OblivionBookCreatorPath'] = dirs['mods'].join(u'OblivionBookCreator.jar')
    tooldirs['NifskopePath'] = pathlist(u'NifTools',u'NifSkope',u'Nifskope.exe')
    tooldirs['BlenderPath'] = pathlist(u'Blender Foundation',u'Blender',u'blender.exe')
    tooldirs['GmaxPath'] = GPath(u'C:\\GMAX').join(u'gmax.exe')
    tooldirs['MaxPath'] = pathlist(u'Autodesk',u'3ds Max 2010',u'3dsmax.exe')
    tooldirs['MayaPath'] = undefinedPath
    tooldirs['PhotoshopPath'] = pathlist(u'Adobe',u'Adobe Photoshop CS3',u'Photoshop.exe')
    tooldirs['GIMP'] = pathlist(u'GIMP-2.0',u'bin',u'gimp-2.6.exe')
    tooldirs['ISOBL'] = dirs['app'].join(u'ISOBL.exe')
    tooldirs['ISRMG'] = dirs['app'].join(u'Insanitys ReadMe Generator.exe')
    tooldirs['ISRNG'] = dirs['app'].join(u'Random Name Generator.exe')
    tooldirs['ISRNPCG'] = dirs['app'].join(u'Random NPC.exe')
    tooldirs['NPP'] = pathlist(u'Notepad++',u'notepad++.exe')
    tooldirs['Fraps'] = GPath(u'C:\\Fraps').join(u'Fraps.exe')
    tooldirs['Audacity'] = pathlist(u'Audacity',u'Audacity.exe')
    tooldirs['Artweaver'] = pathlist(u'Artweaver 1.0',u'Artweaver.exe')
    tooldirs['DDSConverter'] = pathlist(u'DDS Converter 2',u'DDS Converter 2.exe')
    tooldirs['PaintNET'] = pathlist(u'Paint.NET',u'PaintDotNet.exe')
    tooldirs['Milkshape3D'] = pathlist(u'MilkShape 3D 1.8.4',u'ms3d.exe')
    tooldirs['Wings3D'] = pathlist(u'wings3d_1.2',u'Wings3D.exe')
    tooldirs['BSACMD'] = pathlist(u'BSACommander',u'bsacmd.exe')
    tooldirs['MAP'] = dirs['app'].join(u'Modding Tools',u'Interactive Map of Cyrodiil and Shivering Isles 3.52',u'Mapa v 3.52.exe')
    tooldirs['OBMLG'] = dirs['app'].join(u'Modding Tools',u'Oblivion Mod List Generator',u'Oblivion Mod List Generator.exe')
    tooldirs['OBFEL'] = pathlist(u'Oblivion Face Exchange Lite',u'OblivionFaceExchangeLite.exe')
    tooldirs['ArtOfIllusion'] = pathlist(u'ArtOfIllusion',u'Art of Illusion.exe')
    tooldirs['ABCAmberAudioConverter'] = pathlist(u'ABC Amber Audio Converter',u'abcaudio.exe')
    tooldirs['GimpShop'] = pathlist(u'GIMPshop',u'bin',u'gimp-2.2.exe')
    tooldirs['PixelStudio'] = pathlist(u'Pixel',u'Pixel.exe')
    tooldirs['TwistedBrush'] = pathlist(u'Pixarra',u'TwistedBrush Open Studio',u'tbrush_open_studio.exe')
    tooldirs['PhotoScape'] = pathlist(u'PhotoScape',u'PhotoScape.exe')
    tooldirs['Photobie'] = pathlist(u'Photobie',u'Photobie.exe')
    tooldirs['PhotoFiltre'] = pathlist(u'PhotoFiltre',u'PhotoFiltre.exe')
    tooldirs['PaintShopPhotoPro'] = pathlist(u'Corel',u'Corel PaintShop Photo Pro',u'X3',u'PSPClassic',u'Corel Paint Shop Pro Photo.exe')
    tooldirs['Dogwaffle'] = pathlist(u'project dogwaffle',u'dogwaffle.exe')
    tooldirs['GeneticaViewer'] = pathlist(u'Spiral Graphics',u'Genetica Viewer 3',u'Genetica Viewer 3.exe')
    tooldirs['LogitechKeyboard'] = pathlist(u'Logitech',u'GamePanel Software',u'G-series Software',u'LGDCore.exe')
    tooldirs['AutoCad'] = pathlist(u'Autodesk Architectural Desktop 3',u'acad.exe')
    tooldirs['Genetica'] = pathlist(u'Spiral Graphics',u'Genetica 3.5',u'Genetica.exe')
    tooldirs['IrfanView'] = pathlist(u'IrfanView',u'i_view32.exe')
    tooldirs['XnView'] = pathlist(u'XnView',u'xnview.exe')
    tooldirs['FastStone'] = pathlist(u'FastStone Image Viewer',u'FSViewer.exe')
    tooldirs['Steam'] = pathlist(u'Steam',u'steam.exe')
    tooldirs['EVGAPrecision'] = pathlist(u'EVGA Precision',u'EVGAPrecision.exe')
    tooldirs['IcoFX'] = pathlist(u'IcoFX 1.6',u'IcoFX.exe')
    tooldirs['AniFX'] = pathlist(u'AniFX 1.0',u'AniFX.exe')
    tooldirs['WinMerge'] = pathlist(u'WinMerge',u'WinMergeU.exe')
    tooldirs['FreeMind'] = pathlist(u'FreeMind',u'Freemind.exe')
    tooldirs['MediaMonkey'] = pathlist(u'MediaMonkey',u'MediaMonkey.exe')
    tooldirs['Inkscape'] = pathlist(u'Inkscape',u'inkscape.exe')
    tooldirs['FileZilla'] = pathlist(u'FileZilla FTP Client',u'filezilla.exe')
    tooldirs['RADVideo'] = pathlist(u'RADVideo',u'radvideo.exe')
    tooldirs['EggTranslator'] = pathlist(u'Egg Translator',u'EggTranslator.exe')
    tooldirs['Sculptris'] = pathlist(u'sculptris',u'Sculptris.exe')
    tooldirs['Mudbox'] = pathlist(u'Autodesk',u'Mudbox2011',u'mudbox.exe')
    tooldirs['Tabula'] = dirs['app'].join(u'Modding Tools',u'Tabula',u'Tabula.exe')
    tooldirs['MyPaint'] = pathlist(u'MyPaint',u'mypaint.exe')
    tooldirs['Pixia'] = pathlist(u'Pixia',u'pixia.exe')
    tooldirs['DeepPaint'] = pathlist(u'Right Hemisphere',u'Deep Paint',u'DeepPaint.exe')
    tooldirs['CrazyBump'] = pathlist(u'Crazybump',u'CrazyBump.exe')
    tooldirs['xNormal'] = pathlist(u'Santiago Orgaz',u'xNormal',u'3.17.3',u'x86',u'xNormal.exe')
    tooldirs['SoftimageModTool'] = GPath(u'C:\\Softimage').join(u'Softimage_Mod_Tool_7.5',u'Application',u'bin',u'XSI.bat')
    tooldirs['SpeedTree'] = undefinedPath
    tooldirs['Treed'] = pathlist(u'gile[s]',u'plugins',u'tree[d]',u'tree[d].exe')
    tooldirs['WinSnap'] = pathlist(u'WinSnap',u'WinSnap.exe')
    tooldirs['PhotoSEAM'] = pathlist(u'PhotoSEAM',u'PhotoSEAM.exe')
    tooldirs['TextureMaker'] = pathlist(u'Texture Maker',u'texturemaker.exe')
    tooldirs['MaPZone'] = pathlist(u'Allegorithmic',u'MaPZone 2.6',u'MaPZone2.exe')
    tooldirs['NVIDIAMelody'] = pathlist(u'NVIDIA Corporation',u'Melody',u'Melody.exe')
    tooldirs['WTV'] = pathlist(u'WindowsTextureViewer',u'WTV.exe')
    tooldirs['Switch'] = pathlist(u'NCH Swift Sound',u'Switch',u'switch.exe')
    tooldirs['Freeplane'] = pathlist(u'Freeplane',u'freeplane.exe')

def initDefaultSettings():
    #other settings from the INI:
    inisettings['EnableUnicode'] = False
    if 'steam' in dirs['app'].cs:
        inisettings['SteamInstall'] = True
    else:
        inisettings['SteamInstall'] = False
    inisettings['ScriptFileExt']=u'.txt'
    inisettings['KeepLog'] = 0
    inisettings['LogFile'] = dirs['mopy'].join(u'bash.log')
    inisettings['EnableBalo'] = False
    inisettings['ResetBSATimestamps'] = True
    inisettings['EnsurePatchExists'] = True
    inisettings['OblivionTexturesBSAName'] = GPath(u'Oblivion - Textures - Compressed.bsa')
    inisettings['ShowDevTools'] = False
    inisettings['Tes4GeckoJavaArg'] = u'-Xmx1024m'
    inisettings['OblivionBookCreatorJavaArg'] = u'-Xmx1024m'
    inisettings['ShowTextureToolLaunchers'] = True
    inisettings['ShowModelingToolLaunchers'] = True
    inisettings['ShowAudioToolLaunchers'] = True
    inisettings['7zExtraCompressionArguments'] = u''
    inisettings['AutoItemCheck'] = True
    inisettings['SkipHideConfirmation'] = False
    inisettings['SkipResetTimeNotifications'] = False
    inisettings['AutoSizeListColumns'] = 0
    inisettings['SoundSuccess'] = GPath(u'')
    inisettings['SoundError'] = GPath(u'')
    inisettings['EnableSplashScreen'] = True
    inisettings['PromptActivateBashedPatch'] = True

def initOptions(bashIni):
    initDefaultTools()
    initDefaultSettings()

    defaultOptions = {}
    type_key = {str:u's',unicode:u's',list:u's',int:u'i',bool:u'b',bolt.Path:u's'}
    allOptions = [tooldirs,inisettings]
    unknownSettings = {}
    for settingsDict in allOptions:
        for defaultKey,defaultValue in settingsDict.iteritems():
            settingType = type(defaultValue)
            readKey = type_key[settingType] + defaultKey
            defaultOptions[readKey.lower()] = (defaultKey,settingsDict)

    # if bash.ini exists update the settings from there:
    if bashIni:
        for section in bashIni.sections():
            options = bashIni.items(section)
            for key,value in options:
                usedKey, usedSettings = defaultOptions.get(key,(key[1:],unknownSettings))
                defaultValue = usedSettings.get(usedKey,u'')
                settingType = type(defaultValue)
                if settingType in (bolt.Path,list):
                    if value == u'.': continue
                    value = GPath(value)
                    if not value.isabs():
                        value = dirs['app'].join(value)
                elif settingType is bool:
                    if value == u'.': continue
                    value = bashIni.getboolean(section,key)
                else:
                    value = settingType(value)
                compDefaultValue = defaultValue
                compValue = value
                if settingType in (str,unicode):
                    compDefaultValue = compDefaultValue.lower()
                    compValue = compValue.lower()
                    if compValue in (_(u'-option(s)'),_(u'tooltip text'),_(u'default')):
                        compValue = compDefaultValue
                if settingType is list:
                    if compValue != compDefaultValue[0]:
                        usedSettings[usedKey] = value
                elif compValue != compDefaultValue:
                    usedSettings[usedKey] = value

    tooldirs['Tes4ViewPath'] = tooldirs['Tes4EditPath'].head.join(u'TES4View.exe')
    tooldirs['Tes4TransPath'] = tooldirs['Tes4EditPath'].head.join(u'TES4Trans.exe')

def initLogFile():
    if inisettings['KeepLog'] == 0:
        if inisettings['LogFile'].exists():
            os.remove(inisettings['LogFile'].s)
    else:
        with inisettings['LogFile'].open('a', encoding='utf-8-sig') as log:
            log.write(
                _(u'%s Wrye Bash ini file read, Keep Log level: %d, initialized.') % (datetime.datetime.now(),inisettings['KeepLog'])
                + u'\r\n')

def initBosh(personal='',localAppData='',oblivionPath=''):
    #--Bash Ini
    bashIni = None
    if GPath(u'bash.ini').exists():
        bashIni = ConfigParser.ConfigParser()
        bashIni.read(u'bash.ini')

    initDirs(bashIni,personal,localAppData, oblivionPath)
    initOptions(bashIni)
    initLogFile()
    Installer.initData()
    PatchFile.initGameData()

def initSettings(readOnly=False):
    global settings
    try:
        settings = bolt.Settings(PickleDict(
            dirs['saveBase'].join(u'BashSettings.dat'),
            dirs['userApp'].join(u'bash config.pkl'),
            readOnly))
    except cPickle.UnpicklingError, err:
        usebck = balt.askYes(None,_(u"Error reading the Bash Settings database (the error is: '%s'). This is probably not recoverable with the current file. Do you want to try the backup BashSettings.dat? (It will have all your UI choices of the time before last that you used Wrye Bash.") % err,_(u"Settings Load Error"))
        if usebck:
            try:
                settings = bolt.Settings(PickleDict(
                    dirs['saveBase'].join(u'BashSettings.dat.bak'),
                    dirs['userApp'].join(u'bash config.pkl'),
                    readOnly))
            except cPickle.UnpicklingError, err:
                delete = balt.askYes(None,_(u"Error reading the BackupBash Settings database (the error is: '%s'). This is probably not recoverable with the current file. Do you want to delete the corrupted settings and load Wrye Bash without your saved UI settings?. (Otherwise Wrye Bash won't start up)") % err,_(u"Settings Load Error"))
                if delete:
                    dirs['saveBase'].join(u'BashSettings.dat').remove()
                    settings = bolt.Settings(PickleDict(
                    dirs['saveBase'].join(u'BashSettings.dat'),
                    dirs['userApp'].join(u'bash config.pkl'),
                    readOnly))
                else:raise
        else:
            delete = balt.askYes(None,_(u"Do you want to delete the corrupted settings and load Wrye Bash without your saved UI settings?. (Otherwise Wrye Bash won't start up)"),_(u"Settings Load Error"))
            if delete:
                dirs['saveBase'].join(u'BashSettings.dat').remove()
                settings = bolt.Settings(PickleDict(
                dirs['saveBase'].join(u'BashSettings.dat'),
                dirs['userApp'].join(u'bash config.pkl'),
                readOnly))
            else: raise
    # No longer pulling version out of the readme, but still need the old cached value for upgrade check!
    if 'bash.readme' in settings:
        settings['bash.version'] = _(settings['bash.readme'][1])
        del settings['bash.readme']
    settings.loadDefaults(settingDefaults)

# Main ------------------------------------------------------------------------
if __name__ == '__main__':
    print _(u'Compiled')
