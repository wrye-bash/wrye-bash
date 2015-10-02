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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2015 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This module defines objects and functions for working with Oblivion
files and environment. It does not provide interface functions which are instead
provided by separate modules: bish for CLI and bash/basher for GUI."""

# Localization ----------------------------------------------------------------
#--Not totally clear on this, but it seems to safest to put locale first...
from functools import wraps
import locale; locale.setlocale(locale.LC_ALL,u'')
#locale.setlocale(locale.LC_ALL,'German')
#locale.setlocale(locale.LC_ALL,'Japanese_Japan.932')
import time

# Imports ---------------------------------------------------------------------
#--Python
import cPickle
import collections
import copy
import datetime
import os
import re
import string
import struct
import sys
from types import NoneType, FloatType, IntType, LongType, BooleanType, \
    StringType, UnicodeType, ListType, DictType, TupleType
from operator import attrgetter
import subprocess
from subprocess import Popen, PIPE

#--Local
import balt
import bolt
import bush
import bass
from bolt import BoltError, AbstractError, ArgumentError, StateError, \
    PermissionError, FileError
from bolt import LString, GPath, Flags, DataDict, SubProgress, cstrip, \
    deprint, sio, Path
from bolt import decode, encode
# cint
from _ctypes import POINTER
from ctypes import cast, c_ulong
from cint import ObCollection, CBash, ObBaseRecord
from brec import MreRecord, ModReader, ModError, ModWriter, getModIndex, \
    genFid, getObjectIndex, getFormIndices
from record_groups import MobWorlds, MobDials, MobICells, \
    MobObjects, MobBase
import loot
import libbsa

import patcher # for configIsCBash()

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

allTags = bush.game.allTags
allTagsSet = set(allTags)
oldTags = sorted((u'Merge',))
oldTagsSet = set(oldTags)

reOblivion = re.compile(
    u'^(Oblivion|Nehrim)(|_SI|_1.1|_1.1b|_1.5.0.8|_GOTY non-SI).esm$', re.U)

undefinedPath = GPath(u'C:\\not\\a\\valid\\path.exe')
undefinedPaths = {GPath(u'C:\\Path\\exe.exe'), undefinedPath}

#--Unicode
exe7z = u'7z.exe' # this should be moved to bolt (or bass ?) but still set here

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
    return decode(locale.format('%d',int(value),True),locale.getpreferredencoding())

def formatDate(value):
    """Convert time to string formatted to to locale's default date/time."""
    return decode(time.strftime('%c',time.localtime(value)),locale.getpreferredencoding())

def unformatDate(date, formatStr):
    """Basically a wrapper around time.strptime. Exists to get around bug in
    strptime for Japanese locale."""
    try:
        return time.strptime(date, '%c')
    except ValueError:
        if formatStr == '%c' and u'Japanese' in locale.getlocale()[0]:
            date = re.sub(u'^([0-9]{4})/([1-9])', r'\1/0\2', date, flags=re.U)
            return time.strptime(date, '%c')
        else:
            raise

# Singletons, Constants -------------------------------------------------------
#--Constants
#..Bit-and this with the fid to get the objectindex.
oiMask = 0xFFFFFFL

#--File Singletons
gameInis = None
oblivionIni = None
modInfos  = None  #--ModInfos singleton
saveInfos = None #--SaveInfos singleton
iniInfos = None #--INIInfos singleton
bsaInfos = None #--BSAInfos singleton
screensData = None #--ScreensData singleton
messages = None #--Message archive singleton
configHelpers = None #--Config Helper files (LOOT Master List, etc.)
lootDb = None #--LootDb singleton
load_order = None #--can't import yet as I need bosh.dirs to be initialized

def listArchiveContents(fileName):
    command = ur'"%s" l -slt -sccUTF-8 "%s"' % (exe7z, fileName)
    ins, err = Popen(command, stdout=PIPE, stdin=PIPE, startupinfo=startupinfo).communicate()
    return ins

# Util Classes ----------------------------------------------------------------
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
            try:
                with self.oldPath.open('r') as ins:
                    self.data.update(cPickle.load(ins))
                result = 1
            except EOFError:
                pass
        #--Update paths
        # def textDump(path):
        #     deprint(u'Text dump:',path)
        #     with path.open('w',encoding='utf-8-sig') as out:
        #         for key,value in self.data.iteritems():
        #             out.write(u'= %s:\n  %s\n' % (key,value))
        #textDump(self.path+'.old.txt')
        if not self.vdata.get('boltPaths',False):
            self.updatePaths()
            self.vdata['boltPaths'] = True
        #textDump(self.path+'.new.txt')
        #--Done
        return result

    def updatePaths(self): # CRUFT ?
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
             # TODO(ut) since I imported Path from bolt (was from cint) I get
             # unresolved attribute for Path._path (in x._path below) - should
             # be older Path class - CRUFT pickled ?
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

#--Header tags
reVersion = re.compile(ur'^(version[:\.]*|ver[:\.]*|rev[:\.]*|r[:\.\s]+|v[:\.\s]+) *([-0-9a-zA-Z\.]*\+?)',re.M|re.I|re.U)

#--Mod Extensions
reComment = re.compile(u'#.*',re.U)
reExGroup = re.compile(u'(.*?),',re.U)
reModExt  = re.compile(ur'\.es[mp](.ghost)?$',re.I|re.U)
reEsmExt  = re.compile(ur'\.esm(.ghost)?$',re.I|re.U)
reEspExt  = re.compile(ur'\.esp(.ghost)?$',re.I|re.U)
reBSAExt  = re.compile(ur'\.bsa(.ghost)?$',re.I|re.U)
reEssExt  = re.compile(ur'\.ess$',re.I|re.U)
reSaveExt = re.compile(ur'(quicksave(\.bak)+|autosave(\.bak)+|\.(es|fo)[rs])$',re.I|re.U)
reCsvExt  = re.compile(ur'\.csv$',re.I|re.U)
reINIExt  = re.compile(ur'\.ini$',re.I|re.U)
reQuoted  = re.compile(ur'^"(.*)"$',re.U)
reTesNexus = re.compile(ur'(.*?)(?:-(\d{1,6})(?:\.tessource)?(?:-bain)?(?:-\d{0,6})?(?:-\d{0,6})?(?:-\d{0,6})?(?:-\w{0,16})?(?:\w)?)?(\.7z|\.zip|\.rar|\.7z\.001|)$',re.I|re.U)
reTESA = re.compile(ur'(.*?)(?:-(\d{1,6})(?:\.tessource)?(?:-bain)?)?(\.7z|\.zip|\.rar|)$',re.I|re.U)
reSplitOnNonAlphaNumeric = re.compile(ur'\W+',re.U)

# Util Functions --------------------------------------------------------------
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
        return modInfos.getOrdered(self)

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
        balt.shellMove(filePath.temp, filePath, parent=None)
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
                raise FileError(self.name,u'Unsupported file version: %X' % self.version)
            #--Plugins
            self.plugins = []
            type, = unpack('=B',1)
            if type != 0:
                raise FileError(self.name,u'Expected plugins record, but got %d.' % type)
            count, = unpack('=I',4)
            for x in range(count):
                espid,index,modLen = unpack('=2BI',6)
                modName = GPath(decode(ins.read(modLen)))
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
                modName = encode(modName.cs)
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
            self.pcName = decode(cstrip(self.pcName))
            self.pcLocation = decode(cstrip(self.pcLocation),bolt.pluginEncoding,avoidEncodings=('utf8','utf-8'))
            self.masters = [GPath(decode(x)) for x in self.masters]
        #--Errors
        except:
            deprint(u'save file error:',traceback=True)
            raise SaveFileError(path.tail,u'File header is corrupted.')

    def writeMasters(self,path):
        """Rewrites masters of existing save file."""
        if not path.exists():
            raise SaveFileError(path.head,u'File does not exist.')
        with path.open('rb') as ins:
            with path.temp.open('wb') as out:
                oldMasters = bush.game.ess.writeMasters(ins,out,self)
        oldMasters = [GPath(decode(x)) for x in oldMasters]
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
            self.pcName = decode(cstrip(ins.read(pcNameSize)))
            self.postNameHeader = ins.read(gameHeaderSize-5-pcNameSize)

            #--Masters
            del self.masters[:]
            numMasters, = ins.unpack('B',1)
            for count in range(numMasters):
                size, = ins.unpack('B',1)
                self.masters.append(GPath(decode(ins.read(size))))

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
            pcName = encode(self.pcName)
            pack('=IIB',5+len(pcName)+1+len(self.postNameHeader),
                self.saveNum, len(pcName)+1)
            out.write(pcName)
            out.write('\x00')
            out.write(self.postNameHeader)
            #--Masters
            pack('B',len(self.masters))
            for master in self.masters:
                name = encode(master.s)
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
                                stringData = decode(ins.read(stringLength))
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
                                        keyStr = decode(key)
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
                                        dataStr = decode(data)
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
                                log(_(u'      Name  : %s') % decode(newName))
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
                                hudFileName = decode(ins.read(len(chunkBuff) - ins.tell()))
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
                                hudFontName = decode(ins.read(hudFontNameLen))
                                hudFontHeight,hudFontWidth,hudWeight,hudItalic,hudFontR,hudFontG,hudFontB, = unpack('=IIhBBBB',14)
                                hudText = decode(ins.read(len(chunkBuff) - ins.tell()))
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
def _delete(itemOrItems, **kwargs):
    confirm = kwargs.pop('confirm', False)
    recycle = kwargs.pop('recycle', True)
    balt.shellDelete(itemOrItems, confirm=confirm, recycle=recycle)

class CoSaves:
    """Handles co-files (.pluggy, .obse, .skse) for saves."""
    reSave  = re.compile(r'\.ess(f?)$',re.I)

    @staticmethod
    def getPaths(savePath):
        """Returns cofile paths."""
        maSave = CoSaves.reSave.search(savePath.s)
        if maSave: savePath = savePath.root
        first = maSave and maSave.group(1) or u''
        return tuple(savePath + ext + first for ext in
                     (u'.pluggy', u'.' + bush.game.se.shortName.lower()))

    def __init__(self,savePath,saveName=None):
        """Initialize with savePath."""
        if saveName: savePath = savePath.join(saveName)
        self.savePath = savePath
        self.paths = CoSaves.getPaths(savePath)

    def delete(self, **kwargs): # not a DataDict subclass
        """Delete cofiles."""
        paths = filter(lambda pa: pa.exists(), self.paths)
        #--Backups
        backBase = kwargs['backupDir']
        backpaths = filter(lambda b: b.exists(),
                           (backBase.join(p.tail) for p in paths))
        backpaths += filter(lambda bf: bf.exists(),
                            (p + u'f' for p in backpaths))
        _delete(paths + tuple(backpaths), **kwargs)

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
            fileNames = [decode(x) for x in ins.read(lenFileNames).split('\x00')[:-1]]
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

    @staticmethod
    def updateAIText(files=None):
        """Update aiText with specified files (or remove, if files == None)."""
        aiPath = dirs['app'].join(u'ArchiveInvalidation.txt')
        if not files:
            aiPath.remove()
            return
        #--Archive invalidation
        aiText = re.sub(ur'\\',u'/',u'\n'.join(files))
        with aiPath.open('w') as f:
            f.write(aiText)

    @staticmethod
    def resetOblivionBSAMTimes():
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
        self.resetOblivionBSAMTimes()
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
        self.resetOblivionBSAMTimes()
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
                    settings_ = deleted_settings
                else:
                    stripped = line
                    settings_ = ini_settings
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
                section = settings_.setdefault(sectionKey,{})
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
                balt.shellCopy(source, aiBsa, allowUndo=True, autoRename=True)
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
            self.modName = decode(file.readNetString()) # Mod name
            self.major = file.readInt32() # Mod major version - getting weird numbers here though
            self.minor = file.readInt32() # Mod minor version
            self.author = decode(file.readNetString()) # author
            self.email = decode(file.readNetString()) # email
            self.website = decode(file.readNetString()) # website
            self.desc = decode(file.readNetString()) # description
            if self.version >= 2:
                self.ftime = file.readInt64() # creation time
            else:
                self.ftime = decode(file.readNetString())
            self.compType = file.readByte() # Compression type. 0 = lzma, 1 = zip
            if self.version >= 1:
                self.build = file.readInt32()
            else:
                self.build = -1

    def writeInfo(self, path, filename, readme, script):
        with path.open('w') as file:
            file.write(encode(filename))
            file.write('\n\n[basic info]\n')
            file.write('Name: ')
            file.write(encode(filename[:-5]))
            file.write('\nAuthor: ')
            file.write(encode(self.author))
            file.write('\nVersion:') # TODO, fix this?
            file.write('\nContact: ')
            file.write(encode(self.email))
            file.write('\nWebsite: ')
            file.write(encode(self.website))
            file.write('\n\n')
            file.write(encode(self.desc))
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
        extractDir = stageBaseDir = Path.tempDir()
        stageDir = stageBaseDir.join(outDir.tail)

        try:
            # Get contents of archive
            sizes,total = self.getOmodContents()

            # Extract the files
            reExtracting = re.compile(ur'Extracting\s+(.+)',re.U)
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
            balt.shellMove(stageDir, outDir.head, parent=None,
                           askOverwrite=True, allowUndo=True, autoRename=True)
        except Exception as e:
            # Error occurred, see if final output dir needs deleting
            balt.shellDeletePass(outDir, parent=progress.getParent())
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
def _cache(lord_func):
    """Decorator to make sure I sync Plugins cache with load_order cache
    whenever I change (or attempt to change) the latter.

    All this syncing is error prone. WIP !
    """
    @wraps(lord_func)
    def _plugins_cache_wrapper(*args, **kwargs):
        e = None
        try:
            return lord_func(*args, **kwargs)
        except:
            e = sys.exc_info()
            raise
        finally:
            try:
                args[0].LoadOrder, args[0].selected = list(
                    args[0].lord.loadOrder), list(args[0].lord.activeOrdered)
            except AttributeError: # lord is None, exception thrown in init
                raise e[0], e[1], e[2]
    return _plugins_cache_wrapper

class Plugins:
    """Singleton wrapper around load_order.py, owned by modInfos - nothing
       else should access it directly and nothing else should access load_order
       directly - only via this class (except usingTxtFile() for now). Mainly
       exposes _LoadOrder_ and _selected_ caches used by modInfos to manipulate
       the load order/active and then save at once. May disappear in a later
       iteration of the load order API."""
    def __init__(self):
        if dirs['saveBase'] == dirs['app']: #--If using the game directory as rather than the appdata dir.
            self.dir = dirs['app']
        else:
            self.dir = dirs['userApp']
        # Plugins cache, manipulated by code which changes load order/active
        self.LoadOrder = [] # the masterlist load order (always sorted)
        self.selected = []  # list of the currently active plugins (not always in order)
        self.lord = None    # WIP: valid LoadOrder object, must be kept in sync with load_order._current_load_order
        #--Create dirs/files if necessary
        self.dir.makedirs()

    @_cache
    def saveActive(self, active=None):
        """Write data to Plugins.txt file.

        Always call AFTER setting the load order - make sure we unghost
        ourselves so ctime of the unghosted mods is not set."""
        self.lord = load_order.SetActivePlugins(
            self.lord.lorder(active if active else self.selected),
            self.lord.loadOrder)

    @_cache
    def saveLoadOrder(self, _selected=None):
        """Write data to loadorder.txt file (and update plugins.txt too)."""
        self.lord = load_order.SaveLoadOrder(self.LoadOrder, acti=_selected)

    def saveLoadAndActive(self):
        self.saveLoadOrder(_selected=self.selected)

    def removeMods(self, plugins, savePlugins=False):
        """Removes the specified mods from the load order."""
        # Use set to remove any duplicates
        plugins = set(plugins,)
        # Remove mods from cache
        self.LoadOrder = [x for x in self.LoadOrder if x not in plugins]
        self.selected  = [x for x in self.selected  if x not in plugins]
        # Refresh liblo
        if savePlugins: self.saveLoadAndActive()

    def renameInLo(self, newName, oldName):
        oldIndex = self.LoadOrder.index(oldName)
        self.removeMods([oldName], savePlugins=False)
        self.LoadOrder.insert(oldIndex, newName)

    @_cache
    def refreshLoadOrder(self,forceRefresh=False):
        """Reload for plugins.txt or masterlist.txt changes."""
        oldLord = self.lord
        if forceRefresh or load_order.haveLoFilesChanged():
            self.lord = load_order.GetLo()
        return oldLord != self.lord

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
class _AFileInfo:
    """Abstract File."""
    def __init__(self,dir,name):
        self.dir = GPath(dir)
        self.name = GPath(name)
        path = self.getPath()
        if path.exists():
            self.ctime = path.ctime
            self.mtime = path.mtime
            self.size = path.size
        else:
            self.ctime = time.time()
            self.mtime = time.time()
            self.size = 0

    def getPath(self):
        """Returns joined dir and name."""
        return self.dir.join(self.name)

    def sameAs(self,fileInfo):
        """Return true if other fileInfo refers to same file as this fileInfo."""
        return ((self.size == fileInfo.size) and
                (self.mtime == fileInfo.mtime) and
                (self.ctime == fileInfo.ctime) and
                (self.name == fileInfo.name))

    def setmtime(self,mtime=0):
        """Sets mtime. Defaults to current value (i.e. reset)."""
        mtime = int(mtime or self.mtime)
        path = self.getPath()
        path.mtime = mtime
        self.mtime = path.mtime

class FileInfo(_AFileInfo):
    """Abstract TES4/TES4GAME File."""

    def __init__(self, dir, name):
        _AFileInfo.__init__(self, dir, name)
        self.bashDir = self.getFileInfos().bashDir
        self.header = None
        self.masterNames = tuple()
        self.masterOrder = tuple()
        self.madeBackup = False
        #--Ancillary storage
        self.extras = {}

    def getFileInfos(self):
        """Returns modInfos or saveInfos depending on fileInfo type."""
        raise AbstractError

    #--File type tests
    #--Note that these tests only test extension, not the file data.
    def isMod(self):
        return reModExt.search(self.name.s)
    def isEsm(self):
        if not self.isMod(): return False
        if self.header:
            return int(self.header.flags1) & 1 == 1
        else:
            return bool(reEsmExt.search(self.name.s)) and False
    def isInvertedMod(self):
        """Extension indicates esp/esm, but byte setting indicates opposite."""
        return (self.isMod() and self.header and
                self.name.cext != (u'.esp',u'.esm')[int(self.header.flags1) & 1])

    def isEss(self):
        return self.name.cext == bush.game.ess.ext

    def refresh(self):
        path = self.getPath()
        self.ctime = path.ctime
        self.mtime = path.mtime
        self.size  = path.size
        if self.header: self.getHeader() # if not header remains None

    def getHeader(self):
        """Read header for file."""
        pass

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
        self.masterOrder = tuple(modInfos.getOrdered(self.masterNames))
        if self.masterOrder != self.masterNames:
            return 20
        else:
            return status

    def writeHeader(self):
        """Writes header to file, overwriting old header."""
        raise AbstractError

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

    def getNextSnapshot(self):
        """Returns parameters for next snapshot."""
        if not self in self.getFileInfos().data.values():
            raise StateError(u"Can't get snapshot parameters for file outside main directory.")
        destDir = self.bashDir.join(u'Snapshots')
        destDir.makedirs()
        (root,ext) = self.name.rootExt
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

#------------------------------------------------------------------------------
reReturns = re.compile(u'\r{2,}',re.U)
reBashTags = re.compile(ur'{{ *BASH *:[^}]*}}\s*\n?',re.U)

class ModInfo(FileInfo):
    """An esp/m file."""

    def __init__(self, dir, name):
        self.isGhost = endsInGhost = (name.cs[-6:] == u'.ghost')
        if endsInGhost: name = GPath(name.s[:-6])
        else: # refreshFile() path
            absPath = GPath(dir).join(name)
            self.isGhost = \
                not absPath.exists() and (absPath + u'.ghost').exists()
        FileInfo.__init__(self, dir, name)

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

    def cachedCrc(self, recalculate=False):
        """Stores a cached crc, for quicker execution."""
        path = self.getPath()
        size = path.size
        mtime = path.getmtime()
        cached_mtime = modInfos.table.getItem(self.name, 'crc_mtime')
        cached_size = modInfos.table.getItem(self.name, 'crc_size')
        if recalculate or mtime != cached_mtime or size != cached_size:
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
        if modInfos.isActiveCached(self.name): return _(u'Active')
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
        if not (modInfos.isActiveCached(self.name) and maExGroup):
            return False
        else:
            exGroup = maExGroup.group(1)
            return len(modInfos.exGroup_mods[exGroup]) > 1

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

    # Ghosting and ghosting related overrides ---------------------------------
    def sameAs(self, fileInfo):
        try:
            return FileInfo.sameAs(self, fileInfo) and (
                self.isGhost == fileInfo.isGhost)
        except AttributeError: #fileInfo has no isGhost attribute - not ModInfo
            return False

    def getPath(self):
        """Return joined dir and name, adding .ghost if the file is ghosted."""
        path = FileInfo.getPath(self)
        if self.isGhost: path += u'.ghost'
        return path

    def setGhost(self,isGhost):
        """Sets file to/from ghost mode. Returns ghost status at end."""
        normal = self.dir.join(self.name)
        ghost = normal + u'.ghost'
        # Refresh current status - it may have changed due to things like
        # libloadorder automatically unghosting plugins when activating them.
        # Libloadorder only un-ghosts automatically, so if both the normal
        # and ghosted version exist, treat the normal as the real one.
        #  TODO(ut): both should never exist simultaneously
        if normal.exists(): self.isGhost = False
        elif ghost.exists(): self.isGhost = True
        # Current status == what we want it?
        if isGhost == self.isGhost: return isGhost
        # Current status != what we want, so change it
        try:
            if not normal.editable() or not ghost.editable():
                return self.isGhost
            oldCtime = self.ctime
            if isGhost: normal.moveTo(ghost)
            else: ghost.moveTo(normal)
            self.isGhost = isGhost
            self.ctime = oldCtime
        except:
            deprint(u'Failed to %sghost file %s' % ((u'un', u'')[isGhost],
                (ghost.s, normal.s)[isGhost]), traceback=True)
        return self.isGhost

    #--Bash Tags --------------------------------------------------------------
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
        if reBashTags.search(description):
            description = reBashTags.sub(strKeys,description)
        else:
            description = description + u'\n' + strKeys
        if len(description) > 511: return False
        self.writeDescription(description)
        return True

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
        """Read header from file set self.header and return it."""
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
        return self.header # to honor the method's name

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
        FileInfo.__init__(self,*args,**kwdargs) ##: has a lot of stuff that has nothing to do with inis !
        self._status = None

    @property
    def status(self):
        if self._status is None: self.getStatus()
        return self._status

    def getFileInfos(self):
        return iniInfos

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

#------------------------------------------------------------------------------
class SaveInfo(FileInfo):
    def getFileInfos(self):
        """Returns modInfos or saveInfos depending on fileInfo type."""
        return saveInfos

    def getStatus(self):
        status = FileInfo.getStatus(self)
        masterOrder = self.masterOrder
        #--File size?
        if status > 0 or len(masterOrder) > len(modInfos.activeCached):
            return status
        #--Current ordering?
        if masterOrder != modInfos.activeCached[:len(masterOrder)]:
            return status
        elif masterOrder == modInfos.activeCached:
            return -20
        else:
            return -10

    def getHeader(self):
        """Read header from file set self.header and return it."""
        try:
            self.header = SaveHeader(self.getPath())
            #--Master Names/Order
            self.masterNames = tuple(self.header.masters)
            self.masterOrder = tuple() #--Reset to empty for now
        except struct.error, rex:
            raise SaveFileError(self.name,u'Struct.error: %s' % rex)
        return self.header # to honor the method's name

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

    def resetMTime(self,mtime=u'01-01-2006 00:00:00'):
        mtime = time.mktime(time.strptime(mtime,u'%m-%d-%Y %H:%M:%S'))
        self.setmtime(mtime)

#------------------------------------------------------------------------------
class TrackedFileInfos(DataDict):
    """Similar to FileInfos, but doesn't use a PickleDict to save information
       about the tracked files at all.

       Uses absolute paths - the caller is responsible for passing them.
       """
    # DEPRECATED: hack introduced to track BAIN installed files AND game inis
    dir = GPath(u'') # a mess with paths

    def __init__(self, factory=_AFileInfo):
        self.factory = factory
        self.data = {}

    def refreshTracked(self):
        data = self.data
        changed = set()
        for name in data.keys():
            fileInfo = self.factory(self.dir, name)
            filePath = fileInfo.getPath()
            if not filePath.exists(): # untrack
                self.data.pop(name, None)
                changed.add(name)
            elif not fileInfo.sameAs(data[name]):
                data[name] = fileInfo
                changed.add(name)
        return changed

    def track(self, absPath, factory=None): # cf FileInfos.refreshFile
        factory = factory or self.factory
        fileInfo = factory(self.dir, absPath)
        # fileInfo.getHeader() #ModInfo: will blow if absPath doesn't exist
        self[absPath] = fileInfo

#------------------------------------------------------------------------------
class FileInfos(DataDict):
    def _initDB(self, dir_):
        self.dir = dir_ #--Path
        self.data = {} # populated in refresh ()
        self.corrupted = {} #--errorMessage = corrupted[fileName]
        self.bashDir = self.getBashDir() # should be a property
        self.table = bolt.Table(PickleDict(self.bashDir.join(u'Table.dat'),
                                           self.bashDir.join(u'Table.pkl')))
        #--Update table keys... # CRUFT (178)
        tableData = self.table.data
        for key in self.table.data.keys():
            if not isinstance(key,bolt.Path):
                del tableData[key]

    def __init__(self, dir_, factory=FileInfo, dirdef=None):
        """Init with specified directory and specified factory type."""
        self.dirdef = dirdef
        self.factory=factory
        self._initDB(dir_)

    def getBashDir(self):
        """Returns Bash data storage directory."""
        return self.dir.join(u'Bash')

    #--Refresh File
    def refreshFile(self,fileName):
        try:
            fileInfo = self.factory(self.dir,fileName)
            fileInfo.getHeader()
            self[fileName] = fileInfo
        except FileError, error:
            self.corrupted[fileName] = error.message
            self.pop(fileName, None)
            raise

    #--Refresh
    def _names(self): # performance intensive - dirdef stuff needs rethinking
        if self.dirdef:
            # Default items
            names = {x for x in self.dirdef.list() if
                     self.dirdef.join(x).isfile() and self.rightFileType(x)}
        else:
            names = set()
        if self.dir.exists():
            # Normal folder items
            names |= {x for x in self.dir.list() if
                      self.dir.join(x).isfile() and self.rightFileType(x)}
        return list(names)

    def refresh(self):
        """Refresh from file directory."""
        data = self.data
        oldNames = set(data) | set(self.corrupted)
        newNames = set()
        _added = set()
        _updated = set()
        names = self._names()
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
                    if isAdded: _added.add(name)
                    elif isUpdated: _updated.add(name)
            newNames.add(name)
        _deleted = oldNames - newNames
        for name in _deleted:
            # Can run into multiple pops if one of the files is corrupted
            data.pop(name, None); self.corrupted.pop(name, None)
        if _deleted:
            # items deleted outside Bash
            for d in set(self.table.keys()) &  set(_deleted):
                del self.table[d]
        return bool(_added) or bool(_updated) or bool(_deleted)

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
        try:
            if fileInfo.isGhost: newPath += u'.ghost'
        except AttributeError: pass # not a mod info
        oldPath = fileInfo.getPath()
        balt.shellMove(oldPath, newPath, parent=None)
        #--FileInfo
        fileInfo.name = newName
        #--FileInfos
        self[newName] = self[oldName]
        del self[oldName]
        self.table.moveRow(oldName,newName)
        #--Done
        fileInfo.madeBackup = False

    #--Delete
    def delete(self, fileName, **kwargs):
        """Deletes member file."""
        if not isinstance(fileName,(list,set)):
            fileNames = [fileName]
        else:
            fileNames = fileName
        doRefresh = kwargs.pop('doRefresh', True)
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
            backRoot = backBase.join(fileName)
            for backPath in (backRoot,backRoot+u'f'):
                toDeleteAppend(backPath)
        #--Now do actual deletions
        toDelete = [x for x in toDelete if x.exists()]
        try:
            _delete(toDelete, **kwargs)
        finally:
            #--Table
            for filePath, modname in tableUpdate.iteritems():
                if not filePath.exists(): self.table.delRow(modname)
                else: del tableUpdate[filePath] # item was not deleted
            #--Refresh
            if doRefresh:
                self.delete_Refresh(tableUpdate.values())

    def _updateBain(self, deleted):
        """Track deleted inis and mods so BAIN can update its UI.
        :param deleted: make sure those are deleted before calling this method
        """
        for d in map(self.dir.join, deleted): # we need absolute paths
            InstallersData.track(d, factory=self.factory)

    def delete_Refresh(self, deleted): self.refresh()

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

    #--Move Exists
    @staticmethod
    def moveIsSafe(fileName,destDir):
        """Bool: Safe to move file to destDir."""
        return not destDir.join(fileName).exists()

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
        dir_ = dirs['modsBash'].join(u'INI Data')
        dir_.makedirs()
        return dir_

    def delete_Refresh(self, deleted):
        FileInfos.delete_Refresh(self, deleted)
        deleted = set(d for d in deleted if not self.dir.join(d).exists())
        self._updateBain(deleted)

#------------------------------------------------------------------------------
class ModInfos(FileInfos):
    """Collection of modinfos. Represents mods in the Oblivion\Data directory."""
    #--------------------------------------------------------------------------
    # Load Order stuff is almost all handled in the Plugins class again
    #--------------------------------------------------------------------------
    def __init__(self):
        FileInfos.__init__(self,dirs['mods'],ModInfo)
        #--MTime resetting
        self.mtimes = self.table.getColumn('mtime')
        self.mtimesReset = [] #--Files whose mtimes have been reset.
        self.mergeScanned = [] #--Files that have been scanned for mergeability.
        #--Selection state (merged, imported)
        self.plugins = Plugins()
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
        self.mtime_mods = collections.defaultdict(list)
        self.mtime_selected = collections.defaultdict(list)
        self.exGroup_mods = collections.defaultdict(list)
        self.mergeable = set() #--Set of all mods which can be merged.
        self.bad_names = set() #--Set of all mods with names that can't be saved to plugins.txt
        self.missing_strings = set() #--Set of all mods with missing .STRINGS files
        self.new_missing_strings = set() #--Set of new mods with missing .STRINGS files
        self.activeBad = set() #--Set of all mods with bad names that are active
        self.merged = set() #--For bash merged files
        self.imported = set() #--For bash imported files
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
        # removed/extra mods in plugins.txt - set in load_order.py,
        # used in RefreshData
        self.selectedBad = set()
        self.selectedExtra = []

    @property
    def lockLO(self):
        return settings.getChanged('bosh.modInfos.resetMTimes', True)
    def lockLOSet(self, val):
        settings['bosh.modInfos.resetMTimes'] = val
        if val: self._resetMTimes()
        else: self.mtimes.clear()

    #--Load Order utility methods - be sure cache is valid when using them-----
    def isActiveCached(self, mod):
        """Return true if the mod is in the current active mods cache."""
        return mod in self.plugins.lord.active
    @property
    def activeCached(self):
        """Return the currently cached active mods in load order as a tuple.
        :rtype : tuple
        """
        return self.plugins.lord.activeOrdered
    def loIndexCached(self, mod): return self.plugins.lord.lindex(mod)
    def loIndexCachedOrMax(self, mod):
        try: return self.loIndexCached(mod)
        except KeyError:
            return sys.maxint # sort mods that do not have a load order LAST
    def activeIndexCached(self, mod): return self.plugins.lord.activeIndex(mod)
    def hexIndexString(self, masterName):
        return u'%02X' % (self.activeIndexCached(masterName),) \
            if self.isActiveCached(masterName) else u''

    def dropItems(self, dropItem, firstItem, lastItem): # MUTATES plugins CACHE
        # Calculating indexes through order.index() cause we may be called in
        # a row before saving the modified load order
        order = self.plugins.LoadOrder
        newPos = order.index(dropItem)
        if newPos <= 0: return False
        start = order.index(firstItem)
        stop = order.index(lastItem) + 1  # excluded
        # Can't move the game's master file anywhere else but position 0
        master = self.masterName
        if master in order[start:stop]: return False
        # List of names to move removed and then reinserted at new position
        toMove = order[start:stop]
        del order[start:stop]
        order[newPos:newPos] = toMove
        return True

    def getBashDir(self):
        """Returns Bash data storage directory."""
        return dirs['modsBash']

    #--Refresh-----------------------------------------------------------------
    def _OBMMWarn(self):
        obmmWarn = settings.setdefault('bosh.modInfos.obmmWarn', 0)
        if self.lockLO and obmmWarn == 0 and dirs['app'].join(
                u'obmm').exists(): settings['bosh.modInfos.obmmWarn'] = 1
        return settings['bosh.modInfos.obmmWarn'] == 1 # must warn

    def canSetTimes(self):
        """Returns a boolean indicating if mtime setting is allowed."""
        ##: canSetTimes() will trigger a prompt if OBMM is installed so I keep
        # it in refresh(): bin the OBMM warn and instead add a warn In lockLO
        if self._OBMMWarn(): return False
        if not self.lockLO: return False
        if settings.dictFile.readOnly: return False
        if load_order.usingTxtFile(): return False
        #--Else
        return True

    def _names(self):
        names = FileInfos._names(self)
        names.sort(key=lambda x: x.cext == u'.ghost')
        return names

    def refresh(self, scanData=True, _modTimesChange=False):
        """Update file data for additions, removals and date changes."""
        # TODO: make sure that calling two times this in a row second time
        # ALWAYS returns False - was not true when autoghost run !
        hasChanged = scanData and FileInfos.refresh(self)
        if self.canSetTimes() and hasChanged:
            self._resetMTimes()
        _modTimesChange = _modTimesChange and not load_order.usingTxtFile()
        hasChanged += self.plugins.refreshLoadOrder(
            forceRefresh=hasChanged or _modTimesChange)
        hasGhosted = self.autoGhost(force=False)
        if hasChanged or _modTimesChange: self.refreshInfoLists()
        self.reloadBashTags()
        hasNewBad = self.refreshBadNames()
        hasMissingStrings = self.refreshMissingStrings()
        self.setOblivionVersions()
        return bool(hasChanged) or hasGhosted or hasNewBad or hasMissingStrings

    def refreshBadNames(self):
        """Refreshes which filenames cannot be saved to plugins.txt
        It seems that Skyrim and Oblivion read plugins.txt as a cp1252
        encoded file, and any filename that doesn't decode to cp1252 will
        be skipped."""
        bad = self.bad_names = set()
        activeBad = self.activeBad = set()
        for fileName in self.data:
            if self.isBadFileName(fileName.s):
                if self.isActiveCached(fileName):
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
        for fileName, fileInfo in self.iteritems():
            if fileInfo.isMissingStrings():
                bad.add(fileName)
        new = bad - oldBad
        self.missing_strings = bad
        self.new_missing_strings = new
        return bool(new)

    def _resetMTimes(self):
        """Remember/reset mtimes of member files."""
        if not self.canSetTimes(): return
        del self.mtimesReset[:]
        try:
            for fileName, fileInfo in sorted(self.iteritems(),key=lambda x: x[1].mtime):
                oldMTime = int(self.mtimes.get(fileName,fileInfo.mtime))
                self.mtimes[fileName] = oldMTime
                if fileInfo.mtime != oldMTime and oldMTime  > 0:
                    #deprint(fileInfo.name, oldMTime - fileInfo.mtime)
                    fileInfo.setmtime(oldMTime)
                    self.mtimesReset.append(fileName)
        except:
            self.mtimesReset = [u'FAILED',fileName]

    def autoGhost(self,force=False):
        """Automatically turn inactive files to ghosts.

        Should be called when deactivating mods - will have an effect if
        bash.mods.autoGhost is true, or if force parameter is true (in which
        case, if autoGhost is False, it will actually unghost all ghosted
        mods). If both the mod and its ghost exist, the mod is not active and
        this method runs while autoGhost is on, the normal version will be
        moved to the ghost.
        :param force: set to True only in Mods_AutoGhost, so if fired when
        toggling bash.mods.autoGhost to False we forcibly unghost all mods
        """
        changed = []
        toGhost = settings.get('bash.mods.autoGhost',False)
        if force or toGhost:
            allowGhosting = self.table.getColumn('allowGhosting')
            for mod, modInfo in self.iteritems():
                modGhost = toGhost and not self.isActiveCached(mod) \
                           and allowGhosting.get(mod, True)
                oldGhost = modInfo.isGhost
                newGhost = modInfo.setGhost(modGhost)
                if newGhost != oldGhost:
                    changed.append(mod)
        return changed

    def refreshInfoLists(self):
        """Refreshes various mod info lists (mtime_mods, mtime_selected,
        exGroup_mods, imported, exported) - call after refreshing from Data
        AND having latest load order."""
        #--Mod mtimes
        mtime_mods = self.mtime_mods
        mtime_mods.clear()
        self.bashed_patches.clear()
        for modName, modInfo in self.iteritems():
            mtime_mods[modInfo.mtime].append(modName)
            if modInfo.header.author == u"BASHED PATCH":
                self.bashed_patches.add(modName)
        #--Selected mtimes and Refresh overLoaded too..
        mtime_selected = self.mtime_selected
        mtime_selected.clear()
        self.exGroup_mods.clear()
        for modName in self.activeCached:
            mtime = modInfos[modName].mtime
            mtime_selected[mtime].append(modName)
            maExGroup = reExGroup.match(modName.s)
            if maExGroup:
                exGroup = maExGroup.group(1)
                self.exGroup_mods[exGroup].append(modName)
        #--Refresh merged/imported lists.
        self.merged,self.imported = self.getSemiActive(set(self.activeCached))

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
                        canMerge = isCBashMergeable(fileInfo)
                    else:
                        canMerge = isPBashMergeable(fileInfo)
                except Exception, e:
                    # deprint (_(u"Error scanning mod %s (%s)") % (fileName, e))
                    # canMerge = False #presume non-mergeable.
                    raise


                #can't be above because otherwise if the mergeability had already been set true this wouldn't unset it.
                if fileName == u"Oscuro's_Oblivion_Overhaul.esp":
                    canMerge = False
            # noinspection PySimplifyBooleanCheck
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
        for modName, mod in self.iteritems():
            autoTag = self.table.getItem(modName, 'autoBashTags')
            if autoTag is None and self.table.getItem(
                    modName, 'bashTags') is None:
                # A new mod, set autoBashTags to True (default)
                self.table.setItem(modName, 'autoBashTags', True)
                autoTag = True
            elif autoTag is None:
                # An old mod that had manual bash tags added, disable autoBashTags
                self.table.setItem(modName, 'autoBashTags', False)
            if autoTag:
                mod.reloadBashTags()

    #--Mod selection ----------------------------------------------------------
    def getOrdered(self, modNames):
        """Return a list containing modNames' elements sorted into load order.

        If some elements do not have a load order they are appended to the list
        in alphabetical, case insensitive order (used also to resolve
        modification time conflicts).
        :param modNames: an iterable containing bolt.Paths
        :rtype : list
        """
        modNames = list(modNames)
        modNames.sort() # resolve time conflicts or no load order
        modNames.sort(key=self.loIndexCachedOrMax)
        return modNames

    def getSemiActive(self,masters):
        """Return (merged,imported) mods made semi-active by Bashed Patch.

        If no bashed patches are present in 'masters' then return empty sets.
        Else for each bashed patch use its config (if present) to find mods
        it merges or imports."""
        merged,imported = set(),set()
        patches = masters & self.bashed_patches
        for patchName in patches:
            patchConfigs = self.table.getItem(patchName, 'bash.patch.configs')
            if not patchConfigs: continue
            patcherstr = 'CBash_PatchMerger' if patcher.configIsCBash(
                patchConfigs) else 'PatchMerger'
            if patchConfigs.get(patcherstr,{}).get('isEnabled'):
                configChecks = patchConfigs[patcherstr]['configChecks']
                for modName in configChecks:
                    if configChecks[modName] and modName in self:
                        merged.add(modName)
            imported.update(filter(lambda x: x in self,
                                   patchConfigs.get('ImportedMods', tuple())))
        return merged,imported

    def selectExact(self,modNames):
        """Selects exactly the specified set of mods."""
        modsSet, allMods = set(modNames), set(self.plugins.LoadOrder)
        #--Ensure plugins that cannot be deselected stay selected
        modsSet.update(map(GPath, bush.game.nonDeactivatableFiles))
        #--Deselect/select plugins
        missingSet = modsSet - allMods
        toSelect = modsSet - missingSet
        listToSelect = self.getOrdered(toSelect)
        extra = listToSelect[255:]
        #--Save
        self.plugins.selected = listToSelect[:255]
        # we should unghost ourselves so that ctime is properly set
        for s in toSelect: self[s].setGhost(False)
        self.plugins.saveActive()
        self.refreshInfoLists()
        self.autoGhost(force=False) # ghost inactive
        #--Done/Error Message
        message = u''
        if missingSet:
            message += _(u'Some mods were unavailable and were skipped:')+u'\n* '
            message += u'\n* '.join(x.s for x in missingSet)
        if extra:
            if missingSet: message += u'\n'
            message += _(u'Mod list is full, so some mods were skipped:')+u'\n'
            message += u'\n* '.join(x.s for x in extra)
        return message

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
                if fileInfo.name in self: #--In case is bashed patch (cf getSemiActive)
                    present.add(fileInfo.name)
                merged,imported = self.getSemiActive(present)
            else:
                log.setHeader(head+_(u'Active Mod Files:'))
                masters = set(self.activeCached)
                merged,imported = self.merged,self.imported
            allMods = masters | merged | imported
            allMods = self.getOrdered([x for x in allMods if x in self])
            #--List
            modIndex = 0
            if not wtxt: log(u'[spoiler][xml]\n', appendNewline=False)
            for name in allMods:
                if name in masters:
                    prefix = bul+u'%02X' % modIndex
                    modIndex += 1
                elif name in merged:
                    prefix = bul+u'++'
                else:
                    prefix = bul+sImported
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

    @staticmethod
    def _tagsies(modInfo, tagList):
        mname = modInfo.name
        def tags(msg, iterable, tagsList):
            return tagsList + u'  * ' + msg + u', '.join(iterable) + u'\n'
        if not modInfos.table.getItem(mname, 'autoBashTags') and \
               modInfos.table.getItem(mname, 'bashTags', u''):
            tagList = tags(_(u'From Manual (if any this overrides '
                u'Description/LOOT sourced tags): '), sorted(
                modInfos.table.getItem(mname, 'bashTags', u'')), tagList)
        if modInfo.getBashTagsDesc():
            tagList = tags(_(u'From Description: '),
                           sorted(modInfo.getBashTagsDesc()), tagList)
        if configHelpers.getBashTags(mname):
            tagList = tags(_(u'From LOOT Masterlist and or userlist: '),
                           sorted(configHelpers.getBashTags(mname)), tagList)
        if configHelpers.getBashRemoveTags(mname):
            tagList = tags(_(u'Removed by LOOT Masterlist and or userlist: '),
                      sorted(configHelpers.getBashRemoveTags(mname)), tagList)
        return tags(_(u'Result: '), sorted(modInfo.getBashTags()), tagList)

    @staticmethod
    def getTagList(mod_list=None):
        """Return the list as wtxt of current bash tags (but don't say which
        ones are applied via a patch) - either for all mods in the data folder
        or if specified for one specific mod."""
        tagList = u'=== '+_(u'Current Bash Tags')+u':\n'
        tagList += u'[spoiler][xml]\n'
        if mod_list:
            for modInfo in mod_list:
                tagList += u'\n* ' + modInfo.name.s + u'\n'
                if modInfo.getBashTags():
                    tagList = ModInfos._tagsies(modInfo, tagList)
                else: tagList += u'    '+_(u'No tags')
        else:
            # sort output by load order
            lindex = lambda t: modInfos.loIndexCached(t[0])
            for path, modInfo in sorted(modInfos.iteritems(), key=lindex):
                if modInfo.getBashTags():
                    tagList += u'\n* ' + modInfo.name.s + u'\n'
                    tagList = ModInfos._tagsies(modInfo, tagList)
        tagList += u'[/xml][/spoiler]'
        return tagList

    @staticmethod
    def askResourcesOk(fileInfo, parent, title, bsaAndVoice, bsa, voice):
        if not fileInfo.isMod(): return True
        hasBsa, hasVoices = fileInfo.hasResources()
        if (hasBsa, hasVoices) == (False,False): return True
        mPath, name = fileInfo.name, fileInfo.name.s
        if hasBsa and hasVoices: msg = bsaAndVoice % (mPath.sroot, name, name)
        elif hasBsa: msg = bsa % (mPath.sroot, name)
        else: msg = voice % name # hasVoices
        return balt.askWarning(parent, msg, title + name)

    #--Mod Specific -----------------------------------------------------------
    def rightFileType(self,fileName):
        """Bool: File is a mod."""
        return reModExt.search(fileName.s)

    #--Refresh File
    def refreshFile(self,fileName):
        try:
            FileInfos.refreshFile(self,fileName)
        finally:
            self.refreshInfoLists()

    #--Active mods management -------------------------------------------------
    def select(self, fileName, doSave=True, modSet=None, children=None,
               _activated=None):
        """Adds file to selected."""
        plugins = self.plugins
        if _activated is None: _activated = set()
        try:
            if len(plugins.selected) == 255:
                raise PluginsFullError(u'%s: Trying to activate more than 255 mods' % fileName)
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
                    self.select(master, False, modSet, children, _activated)
            # Unghost
            self[fileName].setGhost(False)
            #--Select in plugins
            if fileName not in plugins.selected:
                plugins.selected.append(fileName)
                _activated.add(fileName)
            return self.getOrdered(_activated or [])
        finally:
            if doSave: plugins.saveActive()

    def unselect(self,fileName,doSave=True):
        """Remove mods and their children from selected, can only raise if
        doSave=True."""
        if not isinstance(fileName, (set, list)): fileName = {fileName}
        fileNames = set(fileName)
        sel = set(self.plugins.selected)
        diff = sel - fileNames
        if len(diff) == len(sel): return
        #--Unselect self
        sel = diff
        #--Unselect children
        children = set()
        def _children(parent):
            for selFile in sel:
                if selFile in children: continue # if no more => no more in sel
                for master in self[selFile].header.masters:
                    if master == parent:
                        children.add(selFile)
                        break
        for fileName in fileNames: _children(fileName)
        while children:
            child = children.pop()
            sel.remove(child)
            _children(child)
        self.plugins.selected = self.getOrdered(sel)
        #--Save
        if doSave: self.plugins.saveActive()

    def selectAll(self):
        toActivate = set(self.activeCached)
        try:
            def _select(m):
                if not m in toActivate:
                    self.select(m, doSave=False)
                    toActivate.add(m)
            mods = self.keys()
            # first select the bashed patch(es) and their masters
            for mod in mods: ##: usually results in exclusion group violation
                if self.isBP(mod): _select(mod)
            # then activate mods not tagged NoMerge or Deactivate or Filter
            def _activatable(modName):
                tags = modInfos[modName].getBashTags()
                return not (u'Deactivate' in tags or u'Filter' in tags)
            mods = filter(_activatable, mods)
            mergeable = set(self.mergeable)
            for mod in mods:
                if not mod in mergeable: _select(mod)
            # then activate as many of the remaining mods as we can
            for mod in mods:
                if mod in mergeable: _select(mod)
            self.plugins.saveActive(active=toActivate)
        except PluginsFullError:
            deprint(u'select All: 255 mods activated', traceback=True)
            self.plugins.saveActive(active=toActivate)
            raise
        except BoltError:
            toActivate.clear()
            deprint(u'select All: saveActive failed', traceback=True)
            raise
        finally:
            if toActivate:
                self.refreshInfoLists() # no modtimes changes, just active

    #-- Helpers ---------------------------------------------------------------
    def isBP(self, modName): return self[modName].header.author in (
            u'BASHED PATCH', u'BASHED LISTS')

    @staticmethod
    def isBadFileName(modName):
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
        if load_order.usingTxtFile():
            return False
        else:
            mtime = self[modName].mtime
            return len(self.mtime_mods[mtime]) > 1

    def hasActiveTimeConflict(self,modName):
        """True if there is another mod with the same mtime."""
        if load_order.usingTxtFile():
            return False
        elif not self.isActiveCached(modName): return False
        else:
            mtime = self[modName].mtime
            return len(self.mtime_selected[mtime]) > 1

    def getFreeTime(self, startTime, defaultTime='+1', reverse=False):
        """Tries to return a mtime that doesn't conflict with a mod. Returns defaultTime if it fails."""
        if load_order.usingTxtFile():
            # Doesn't matter - LO isn't determined by mtime
            return time.time()
        else:
            haskey = self.mtime_mods.has_key
            step = -1 if reverse else 1
            endTime = startTime + step * 1000 #1000 is an arbitrary limit
            for testTime in xrange(startTime, endTime, step):
                if not haskey(testTime):
                    return testTime
            return defaultTime

    __max_time = -1
    def timestamp(self):
        """Hack to install mods last in load order (done by liblo when txt
        method used, when mod times method is used make sure we get the latest
        mod time). The mod times stuff must be moved to load_order.py."""
        if not load_order.usingTxtFile():
            maxi = max([x.mtime for x in self.values()] + [self.__max_time])
            maxi = [maxi + 60]
            def timestamps(p):
                if reModExt.search(p.s):
                    self.__max_time = p.mtime = maxi[-1]
                    maxi[-1] += 60 # space at one minute intervals
        else:
            # noinspection PyUnusedLocal
            def timestamps(p): pass
        return timestamps

    @staticmethod # this belongs to load_order.py !
    def usingTxtFile(): return load_order.usingTxtFile()

    def calculateLO(self, mods=None): # excludes corrupt mods
        if mods is None: mods = self.keys()
        mods = sorted(mods) # sort case insensitive (for time conflicts)
        mods.sort(key=lambda x: self[x].mtime)
        mods.sort(key=lambda x: not self[x].isEsm())
        return mods

    #--Mod move/delete/rename -------------------------------------------------
    def rename(self,oldName,newName):
        """Renames member file from oldName to newName."""
        isSelected = self.isActiveCached(oldName)
        if isSelected: self.unselect(oldName, doSave=False) # will save later
        FileInfos.rename(self,oldName,newName)
        self.plugins.renameInLo(newName, oldName)
        if isSelected: self.select(newName, doSave=False)
        # Save to disc (load order and plugins.txt)
        self.plugins.saveLoadAndActive()
        self.refreshInfoLists()

    def delete(self, fileName, **kwargs):
        """Delete member file."""
        if not isinstance(fileName, (set, list)): fileName = {fileName}
        for f in fileName:
            if f.s in bush.game.masterFiles: raise bolt.BoltError(
                u"Cannot delete the game's master file(s).")
        self.unselect(fileName, doSave=False)
        FileInfos.delete(self, fileName, **kwargs)

    def delete_Refresh(self, deleted):
        # adapted from refresh() (avoid refreshing from the data directory)
        deleted = set(d for d in deleted if not self.dir.join(d).exists())
        if not deleted: return
        for name in deleted:
            self.pop(name, None)
            if self.mtimes.has_key(name): del self.mtimes[name]
        self.plugins.removeMods(deleted, savePlugins=True)
        self.refreshInfoLists()
        self._updateBain(deleted)

    def move(self,fileName,destDir,doRefresh=True):
        """Moves member file to destDir."""
        self.unselect(fileName, doSave=True)
        FileInfos.move(self,fileName,destDir,doRefresh)

    #--Mod info/modify --------------------------------------------------------
    def getVersion(self, fileName):
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

    #--Oblivion 1.1/SI Swapping -----------------------------------------------
    def setOblivionVersions(self):
        """Set current (and available) master game esm(s) - oblivion only."""
        self.voAvailable.clear()
        for name,info in self.iteritems():
            maOblivion = reOblivion.match(name.s)
            if maOblivion and info.size in self.size_voVersion:
                self.voAvailable.add(self.size_voVersion[info.size])
        if self.masterName in self:
            self.voCurrent = self.size_voVersion.get(
                self[self.masterName].size, None)
        else: self.voCurrent = None # just in case

    def _retry(self, old, new):
        return balt.askYes(self,
            _(u'Bash encountered an error when renaming %s to %s.') + u'\n\n' +
            _(u'The file is in use by another process such as TES4Edit.') +
            u'\n' + _(u'Please close the other program that is accessing %s.')
            + u'\n\n' + _(u'Try again?') % (old.s, new.s, old.s),
            _(u'File in use'))

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
            while werr.winerror == 32 and self._retry(basePath, oldPath):
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
            while werr.winerror == 32 and self._retry(newPath, basePath):
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

    def swapPluginsAndMasterVersion(self, arcSaves, newSaves):
    # does not really belong here, but then where ?
        """Save current plugins into arcSaves directory, load plugins from
        newSaves directory and set oblivion version."""
        arcPath, newPath = (dirs['saveBase'].join(saves) for saves in
                            (arcSaves, newSaves))
        load_order.swap(arcPath, newPath)
        # Swap Oblivion version to memorized version
        voNew = saveInfos.profiles.setItemDefault(newSaves, 'vOblivion',
                                                  self.voCurrent)
        if voNew in self.voAvailable: self.setOblivionVersion(voNew)

#------------------------------------------------------------------------------
class SaveInfos(FileInfos):
    """SaveInfo collection. Represents save directory and related info."""

    def _setLocalSaveFromIni(self):
        """Read the current save profile from the oblivion.ini file and set
        local save attribute to that value."""
        if oblivionIni.path.exists() and (
            oblivionIni.path.mtime != self.iniMTime):
            # saveInfos 'singleton' is constructed in InitData after
            # bosh.oblivionIni is set (hopefully) - TODO(ut) test
            self.localSave = oblivionIni.getSetting(
                bush.game.saveProfilesKey[0], bush.game.saveProfilesKey[1],
                u'Saves\\')
            # Hopefully will solve issues with unicode usernames # TODO(ut) test
            self.localSave = decode(self.localSave) # encoding = 'cp1252' ?
            self.iniMTime = oblivionIni.path.mtime

    def __init__(self):
        self.iniMTime = 0
        self.localSave = u'Saves\\'
        self._setLocalSaveFromIni()
        FileInfos.__init__(self,dirs['saveBase'].join(self.localSave),SaveInfo)
        # Save Profiles database
        self.profiles = bolt.Table(PickleDict(
            dirs['saveBase'].join(u'BashProfiles.dat'),
            dirs['userApp'].join(u'Profiles.pkl')))

    def getBashDir(self):
        """Return the Bash save settings directory, creating it if it does
        not exist."""
        dir_ = FileInfos.getBashDir(self)
        dir_.makedirs()
        return dir_

    #--Right File Type (Used by Refresh)
    def rightFileType(self,fileName):
        """Bool: File is a save."""
        return reSaveExt.search(fileName.s)

    def refresh(self):
        self._refreshLocalSave()
        return FileInfos.refresh(self)

    def delete(self, fileName, **kwargs):
        """Deletes savefile and associated pluggy file."""
        FileInfos.delete(self, fileName, **kwargs)
        kwargs['confirm'] = False # ask only on save deletion
        kwargs['backupDir'] = self.getBashDir().join('Backups')
        CoSaves(self.dir,fileName).delete(**kwargs)

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
    @staticmethod
    def getLocalSaveDirs():
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

    def _refreshLocalSave(self):
        """Refreshes self.localSave and self.dir."""
        #--self.localSave is NOT a Path object.
        localSave = self.localSave
        self._setLocalSaveFromIni()
        if localSave == self.localSave: return # no change
        self.table.save()
        self._initDB(dirs['saveBase'].join(self.localSave))

    def setLocalSave(self, localSave, refreshSaveInfos=True):
        """Sets SLocalSavePath in Oblivion.ini."""
        self.table.save()
        self.localSave = localSave
        oblivionIni.saveSetting(bush.game.saveProfilesKey[0],
                                bush.game.saveProfilesKey[1],
                                localSave)
        self.iniMTime = oblivionIni.path.mtime
        self._initDB(dirs['saveBase'].join(self.localSave))
        if refreshSaveInfos: self.refresh()

    #--Enabled ----------------------------------------------------------------
    @staticmethod
    def isEnabled(fileName):
        """True if fileName is enabled)."""
        return fileName.cext == bush.game.ess.ext

    def enable(self,fileName,value=True):
        """Enables file by changing extension to 'ess' (True) or 'esr' (False)."""
        isEnabled = self.isEnabled(fileName)
        if value == isEnabled or re.match(u'(autosave|quicksave)', fileName.s,
                                          re.I | re.U):
            return fileName
        (root,ext) = fileName.rootExt
        newName = root + ((value and bush.game.ess.ext) or u'.esr')
        self.rename(fileName,newName)
        return newName

#------------------------------------------------------------------------------
class BSAInfos(FileInfos):
    """BSAInfo collection. Represents bsa files in game's Data directory."""

    def __init__(self):
        self.dir = dirs['mods']
        FileInfos.__init__(self,self.dir,BSAInfo)

    #--Right File Type (Used by Refresh)
    def rightFileType(self,fileName):
        return reBSAExt.search(fileName.s)

    def getBashDir(self):
        """Return directory to save info."""
        return dirs['modsBash'].join(u'BSA Data')

    def resetBSAMTimes(self):
        for bsa in self.values(): bsa.resetMTime()

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

        loot.Init(dirs['compiled'].s)
        # That didn't work - Wrye Bash isn't installed correctly
        if not loot.LootApi:
            raise bolt.BoltError(u'The LOOT API could not be loaded.')
        deprint(u'Using LOOT API version:', loot.version)

        global lootDb
        lootDb = loot.LootDb(dirs['app'].s,bush.game.fsName)

        # LOOT stores the masterlist/userlist in a %LOCALAPPDATA% subdirectory.
        self.lootMasterPath = dirs['userApp'].join(os.pardir,u'LOOT',bush.game.fsName,u'masterlist.yaml')
        self.lootUserPath = dirs['userApp'].join(os.pardir,u'LOOT',bush.game.fsName,u'userlist.yaml')
        self.lootMasterTime = None
        self.lootUserTime = None
        self.tagList = dirs['defaultPatches'].join(u'taglist.yaml')
        self.tagListModTime = None
        #--Bash Tags
        self.tagCache = {}
        #--Mod Rules
        self.name_ruleSet = {}
        #--Refresh
        self.refreshBashTags()

    def refreshBashTags(self):
        """Reloads tag info if file dates have changed."""
        path, userpath = self.lootMasterPath, self.lootUserPath
        #--Masterlist is present, use it
        if path.exists():
            if (path.mtime != self.lootMasterTime or
                (userpath.exists() and userpath.mtime != self.lootUserTime)):
                self.tagCache = {}
                try:
                    if userpath.exists():
                        lootDb.Load(path.s,userpath.s)
                        self.lootMasterTime = path.mtime
                        self.lootUserTime = userpath.mtime
                    else:
                        lootDb.Load(path.s)
                        self.lootMasterTime = path.mtime
                    return # we are done
                except loot.LootError:
                    deprint(u'An error occurred while using the LOOT API:',
                            traceback=True)
        #--No masterlist or an error occured while reading it, use the taglist
        if not self.tagList.exists():
            raise bolt.BoltError(u'Mopy\\Bash Patches\\' + bush.game.fsName +
                u'\\taglist.yaml could not be found.  Please ensure Wrye '
                u'Bash is installed correctly.')
        if self.tagList.mtime == self.tagListModTime: return
        self.tagListModTime = self.tagList.mtime
        try:
            self.tagCache = {}
            lootDb.Load(self.tagList.s)
        except loot.LootError as e:
            raise bolt.BoltError, (u'An error occurred while parsing '
            u'taglist.yaml with the LOOT API: ' + str(e)), sys.exc_info()[2]

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
        active = set(modInfos.activeCached)
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
                for mod in modInfos.activeCached:
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
                        modsList = u' + '.join([x.s for x in modGroup.getActives(activeMerged)])
                        if showNotes and modGroup.notes:
                            log.setHeader(u'=== '+_(u'NOTES: ') + modsList )
                            log(modGroup.notes)
                        if showConfig:
                            log.setHeader(u'=== '+_(u'CONFIGURATION: ') + modsList )
                            #    + _(u'\nLegend: x: Active, +: Merged, -: Inactive'))
                            for ruleType,ruleMod,comment in modGroup.config:
                                if ruleType != u'o': continue
                                if ruleMod in active: bullet = u'x'
                                elif ruleMod in merged: bullet = u'+'
                                elif ruleMod in imported: bullet = u'*'
                                else: bullet = u'o'
                                log(u'%s __%s__ -- %s' % (bullet,ruleMod.s,comment))
                        if showSuggest:
                            log.setHeader(u'=== '+_(u'SUGGESTIONS: ') + modsList)
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
                            log.setHeader(warning + modsList)
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
        self.hasChanged = False ##: move to bolt.PickleDict
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

    def delete(self, key, **kwargs):
        """Delete entry."""
        del self.data[key]
        self.hasChanged = True

    def delete_Refresh(self, deleted): pass

    def search(self,term):
        """Search entries for term."""
        term = term.strip()
        if not term: return None
        items = []
        reTerm = re.compile(term,re.I)
        for key,(subject,author,date,text) in self.iteritems():
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
class PeopleData(PickleTankData, DataDict):
    """Data for a People UIList."""
    def __init__(self):
        PickleTankData.__init__(self, dirs['saveBase'].join(u'People.dat'))

    def delete(self, key, **kwargs): ##: ripped from MesageData - move to DataDict ?
        """Delete entry."""
        del self.data[key]
        self.hasChanged = True

    def delete_Refresh(self, deleted): pass

    #--Operations
    def loadText(self,path):
        """Enter info from text file."""
        newNames, name, buff = set(), None, None
        with path.open('r') as ins:
            reName = re.compile(ur'==([^=]+)=*$',re.U)
            for line in ins:
                maName = reName.match(line)
                if not maName:
                    if buff: buff.write(line)
                    continue
                if name:
                    self.data[name] = (time.time(), 0, buff.getvalue().strip())
                    newNames.add(name)
                    buff.close()
                    buff = None
                name = maName.group(1).strip()
                if name: buff = sio()
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
    reImageExt = re.compile(ur'\.(bmp|jpg|jpeg|png|tif|gif)$', re.I | re.U)

    def __init__(self):
        self.dir = dirs['app']
        self.data = {} #--data[Path] = (ext,mtime)

    def refresh(self):
        """Refresh list of screenshots."""
        self.dir = dirs['app']
        ssBase = GPath(oblivionIni.getSetting(u'Display',u'SScreenShotBaseName',u'ScreenShot')) ##: cache ?
        if ssBase.head:
            self.dir = self.dir.join(ssBase.head)
        newData = {}
        #--Loop over files in directory
        for fileName in self.dir.list():
            filePath = self.dir.join(fileName)
            maImageExt = self.reImageExt.search(fileName.s)
            if maImageExt and filePath.isfile():
                newData[fileName] = (maImageExt.group(1).lower(),filePath.mtime)
        changed = (self.data != newData)
        self.data = newData
        return changed

    def delete(self, fileName, **kwargs):
        """Deletes member file."""
        dirJoin = self.dir.join
        if isinstance(fileName,(list,set)):
            filePath = [dirJoin(file) for file in fileName]
        else:
            filePath = [dirJoin(fileName)]
        _delete(filePath, **kwargs)
        for item in filePath:
            if not item.exists(): del self.data[item.tail]

    def delete_Refresh(self, deleted): self.refresh()

#------------------------------------------------------------------------------
class Installer(object):
    """Object representing an installer archive, its user configuration, and
    its installation state."""

    #--Member data
    persistent = ('archive', 'order', 'group', 'modified', 'size', 'crc',
        'fileSizeCrcs', 'type', 'isActive', 'subNames', 'subActives',
        'dirty_sizeCrc', 'comments', 'readMe', 'packageDoc', 'packagePic',
        'src_sizeCrcDate', 'hasExtraData', 'skipVoices', 'espmNots', 'isSolid',
        'blockSize', 'overrideSkips', 'remaps', 'skipRefresh', 'fileRootIdex')
    volatile = ('data_sizeCrc', 'skipExtFiles', 'skipDirFiles', 'status',
        'missingFiles', 'mismatchedFiles', 'refreshed', 'mismatchedEspms',
        'unSize', 'espms', 'underrides', 'hasWizard', 'espmMap', 'hasReadme',
        'hasBCF', 'hasBethFiles')
    __slots__ = persistent + volatile
    #--Package analysis/porting.
    docDirs = {u'screenshots'}
    dataDirsMinus = {u'bash', u'replacers',
                     u'--'}  #--Will be skipped even if hasExtraData == True.
    reDataFile = re.compile(
        ur'(masterlist.txt|dlclist.txt|\.(esp|esm|bsa|ini))$', re.I | re.U)
    reReadMe = re.compile(
        ur'^.*?([^\\]*)(read[ _]?me|lisez[ _]?moi)([^\\]*)'
        ur'\.(txt|rtf|htm|html|doc|odt)$', re.I | re.U)
    reList = re.compile(
        u'(Solid|Path|Size|CRC|Attributes|Method) = (.*?)(?:\r\n|\n)')
    skipExts = {u'.exe', u'.py', u'.pyc', u'.7z', u'.zip', u'.rar', u'.db',
                u'.ace', u'.tgz', u'.tar', u'.gz', u'.bz2', u'.omod',
                u'.fomod', u'.tb2', u'.lzma', u'.manifest'}
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
        Installer._tempDir = Path.tempDir()
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
    def refreshSizeCrcDate(apRoot, old_sizeCrcDate, progress=None,
                           fullRefresh=False):
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

    #--Initialization, etc -------------------------------------------------------
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
            self.fileSizeCrcs = [(decode(full),size,crc) for (full,size,crc) in self.fileSizeCrcs]
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
        docDirs = self.docDirs
        dataDirsPlus = self.dataDirsPlus
        dataDirsMinus = self.dataDirsMinus
        skipExts = self.skipExts
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
            skipTESVBsl = False
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
            skipTESVBsl = settings['bash.installers.skipTESVBsl']
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
        type_    = self.type
        if type_ == 2:
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
        if InstallersData.miscTrackedFiles:
            dirsModsJoin = dirs['mods'].join
            _trackedInfosTrack = InstallersData.miscTrackedFiles.track
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
        if type_ not in {1,2}: return dest_src
        #--Scan over fileSizeCrcs
        rootIdex = self.fileRootIdex
        for full,size,crc in self.fileSizeCrcs:
            file = full[rootIdex:]
            fileLower = file.lower()
            if fileLower.startswith((u'--',u'omod conversion data',u'fomod',u'wizard images')):
                continue
            sub = u''
            if type_ == 2: #--Complex archive
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
            elif skipTESVBsl and fileExt == u'.bsl':
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
                    if not balt.askYes(balt.Link.Frame,message,bush.game.se.shortName + _(u' DLL Warning')):
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
                    if not balt.askYes(balt.Link.Frame,message,bush.game.sd.longName + _(u' ASI Warning')):
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
                    if not balt.askYes(balt.Link.Frame,message,bush.game.sp.longName + _(u' JAR Warning')):
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
        type_ = 0
        subNameSet = set()
        subNameSetAdd = subNameSet.add
        subNameSetAdd(u'')
        reDataFileSearch = reDataFile.search
        for file,size,crc in fileSizeCrcs:
            file = file[rootIdex:]
            if type_ != 1:
                frags = file.split(u'\\')
                nfrags = len(frags)
                #--Type 1?
                if (nfrags == 1 and reDataFileSearch(frags[0]) or
                    nfrags > 1 and frags[0].lower() in dataDirs):
                    type_ = 1
                    break
                #--Type 2?
                elif nfrags > 2 and not frags[0].startswith(u'--') and \
                                frags[1].lower() in dataDirs \
                 or nfrags == 2 and not frags[0].startswith(u'--') and \
                                reDataFileSearch(frags[1]):
                    subNameSetAdd(frags[0])
                    type_ = 2
        self.type = type_
        #--SubNames, SubActives
        if type_ == 2:
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

    #--ABSTRACT ---------------------------------------------------------------
    def refreshSource(self,archive,progress=None,fullRefresh=False):
        """Refreshes fileSizeCrcs, size, date and modified from source archive/directory."""
        raise AbstractError

    def install(self,archive,destFiles,data_sizeCrcDate,progress=None):
        """Install specified files to Oblivion\Data directory."""
        raise AbstractError

    def listSource(self,archive):
        """Lists the folder structure of the installer."""
        raise AbstractError

#------------------------------------------------------------------------------
#  WIP: http://sevenzip.osdn.jp/chm/cmdline/switches/method.htm
reSolid = re.compile(ur'[-/]ms=[^\s]+', re.IGNORECASE)
def compressionSettings(archive, blockSize, isSolid):
    archiveType = writeExts.get(archive.cext)
    if not archiveType:
        #--Always fall back to using the defaultExt
        archive = GPath(archive.sbody + defaultExt).tail
        archiveType = writeExts.get(archive.cext)
    if archive.cext in noSolidExts: # zip
        solid = u''
    else:
        if isSolid:
            if blockSize:
                solid = u'-ms=on -ms=%dm' % blockSize
            else:
                solid = u'-ms=on'
        else:
            solid = u'-ms=off'
    userArgs = inisettings['7zExtraCompressionArguments']
    if userArgs:
        if reSolid.search(userArgs):
            if not solid: # zip, will blow if ms=XXX is passed in
                old = userArgs
                userArgs = reSolid.sub(u'', userArgs).strip()
                if old != userArgs: deprint(
                    archive.s + u': 7zExtraCompressionArguments ini option '
                                u'"' + old + u'" -> "' + userArgs + u'"')
            solid = userArgs
        else:
            solid += userArgs
    return archive, archiveType, solid

def compressCommand(destArchive, destDir, srcFolder, solid=u'-ms=on',
                    archiveType=u'7z'): # WIP - note solid on by default (7z)
    return [exe7z, u'a', destDir.join(destArchive).temp.s,
            u'-t%s' % archiveType] + solid.split() + [
            u'-y', u'-r', # quiet, recursive
            u'-o"%s"' % destDir.s,
            u'-scsUTF-8', u'-sccUTF-8', # encode output in unicode
            u"%s\\*" % srcFolder.s]

def extractCommand(archivePath, outDirPath):
    command = u'"%s" x "%s" -y -o"%s" -scsUTF-8 -sccUTF-8' % (
        exe7z, archivePath.s, outDirPath.s)
    return command

regErrMatch = re.compile(u'Error:', re.U).match

def countFilesInArchive(srcArch, listFilePath=None, recurse=False):
    """Count all regular files in srcArch (or only the subset in
    listFilePath)."""
    # http://stackoverflow.com/q/31124670/281545
    command = [exe7z, u'l', u'-scsUTF-8', u'-sccUTF-8', srcArch.s]
    if listFilePath: command += [u'@%s' % listFilePath.s]
    if recurse: command += [u'-r']
    proc = Popen(command, stdout=PIPE, stdin=PIPE if listFilePath else None,
                 startupinfo=startupinfo, bufsize=1)
    errorLine = line = u''
    with proc.stdout as out:
        for line in iter(out.readline, b''): # consider io.TextIOWrapper
            line = unicode(line, 'utf8')
            if regErrMatch(line):
                errorLine = line + u''.join(out)
                break
    returncode = proc.wait()
    msg = u'%s: Listing failed\n' % srcArch.s
    if returncode or errorLine:
        msg += u'7z.exe return value: ' + str(returncode) + u'\n' + errorLine
    elif not line: # should not happen
        msg += u'Empty output'
    else: msg = u''
    if msg: raise StateError(msg) # consider using CalledProcessError
    # number of files is reported in the last line - example:
    #                                3534900       325332  75 files, 29 folders
    return int(re.search(ur'(\d+)\s+files,\s+\d+\s+folders', line).group(1))

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
        """Load BCF.dat. Called once when a BCF is first installed, during a
        fullRefresh, and when the BCF is applied"""
        if not self.fullPath.exists(): raise StateError(
            u"\nLoading %s:\nBCF doesn't exist." % self.fullPath.s)
        def translate(out):
            with sio(out) as stream:
                # translate data types to new hierarchy
                class _Translator:
                    def __init__(self, streamToWrap):
                        self._stream = streamToWrap
                    def read(self, numBytes):
                        return self._translate(self._stream.read(numBytes))
                    def readline(self):
                        return self._translate(self._stream.readline())
                    @staticmethod
                    def _translate(s):
                        return re.sub(u'^(bolt|bosh)$', ur'bash.\1', s,
                                      flags=re.U)
                translator = _Translator(stream)
                map(self.__setattr__, self.persistBCF, cPickle.load(translator))
                if fullLoad:
                    map(self.__setattr__, self.settings + self.volatile + self.addedSettings, cPickle.load(translator))
        with self.fullPath.unicodeSafe() as path:
            # Temp rename if its name wont encode correctly
            command = ur'"%s" x "%s" BCF.dat -y -so -sccUTF-8' % (
                exe7z, path.s)
            bolt.wrapPopenOut(command, translate, errorMsg=
                u"\nLoading %s:\nBCF extraction failed." % self.fullPath.s)

    def save(self, destInstaller):
        #--Dump settings into BCF.dat
        def _dump(att, dat):
            cPickle.dump(tuple(map(self.__getattribute__, att)), dat, -1)
        try:
            with Installer.getTempDir().join(u'BCF.dat').open('wb') as f:
                _dump(self.persistBCF, f)
                _dump(self.settings + self.volatile + self.addedSettings, f)
        except Exception as e:
            raise StateError, (u'Error creating BCF.dat:\nError: %s' % e), \
                sys.exc_info()[2]

    def apply(self,destArchive,crc_installer,progress=None,embedded=0L):
        """Applies the BCF and packages the converted archive"""
        #--Prepare by fully loading the BCF and clearing temp
        self.load(True)
        Installer.rmTempDir()
        tmpDir = Installer.newTempDir()
        #--Extract BCF
        if progress: progress(0, self.fullPath.stail + u'\n' + _(
            u'Extracting files...'))
        with self.fullPath.unicodeSafe() as tempPath:
            command = extractCommand(tempPath, tmpDir)
            bolt.extract7z(command, tempPath, progress)
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
            self._unpack(srcInstaller,files,SubProgress(progress,lastStep,nextStep))
            srcInstaller.crc = tempCRC
            lastStep = nextStep
            nextStep += step
        #--Move files around and pack them
        try:
            self._arrangeFiles(SubProgress(progress, lastStep, 0.7))
        except bolt.StateError:
            self.hasBCF = False
            raise
        else:
            self.pack(Installer.getTempDir(),destArchive,dirs['installers'],SubProgress(progress,0.7,1.0))
            #--Lastly, apply the settings.
            #--That is done by the calling code, since it requires an InstallerArchive object to work on
        finally:
            try: tmpDir.rmtree(safety=tmpDir.s)
            except: pass
            Installer.rmTempDir()

    def applySettings(self,destInstaller):
        """Applies the saved settings to an Installer"""
        map(destInstaller.__setattr__, self.settings + self.addedSettings, map(self.__getattribute__, self.settings + self.addedSettings))

    def _arrangeFiles(self,progress):
        """Copies and/or moves extracted files into their proper arrangement."""
        tmpDir = Installer.getTempDir()
        destDir = Installer.newTempDir()
        progress(0,_(u"Moving files..."))
        progress.setFull(1+len(self.convertedFiles))
        #--Make a copy of dupeCount
        dupes = dict(self.dupeCount.iteritems())
        destJoin = destDir.join
        tempJoin = tmpDir.join

        #--Move every file
        for index, (crcValue, srcDir_File, destFile) in enumerate(self.convertedFiles):
            srcDir = srcDir_File[0]
            srcFile = srcDir_File[1]
            if isinstance(srcDir, (basestring, Path)):
                #--either 'BCF-Missing', or crc read from 7z l -slt
                srcDir = u'%s' % srcDir # Path defines __unicode__()
                srcFile = tempJoin(srcDir ,srcFile)
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
        tmpDir.rmtree(safety=tmpDir.s)

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
        attrs = self.settings
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
                self._unpack(installer,subArchives[installerCRC],SubProgress(progress, lastStep, nextStep))
                lastStep = nextStep
                nextStep += step
            #--Note all extracted files
            tmpDir = Installer.getTempDir()
            for crc in tmpDir.list():
                fpath = tmpDir.join(crc)
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
            destInstaller.unpackToTemp(destArchive, self.missingFiles,
                SubProgress(progress, lastStep, lastStep + 0.2))
            lastStep += 0.2
            #--Move the temp dir to tempDir\BCF-Missing
            #--Work around since moveTo doesn't allow direct moving of a directory into its own subdirectory
            Installer.getTempDir().moveTo(tempDir2)
            tempDir2.moveTo(Installer.getTempDir().join(u'BCF-Missing'))
        #--Make the temp dir in case it doesn't exist
        tmpDir = Installer.getTempDir()
        tmpDir.makedirs()
        self.save(destInstaller)
        #--Pack the BCF
        #--BCF's need to be non-Solid since they have to have BCF.dat extracted and read from during runtime
        self.isSolid = False
        self.pack(tmpDir,BCFArchive,dirs['converters'],SubProgress(progress, lastStep, 1.0))
        self.isSolid = destInstaller.isSolid

    def pack(self, srcFolder, destArchive, outDir, progress=None):
        """Creates the BAIN'ified archive and cleans up temp"""
        #--Determine settings for 7z
        destArchive, archiveType, solid = compressionSettings(
            destArchive, self.blockSize, self.isSolid)
        command = compressCommand(destArchive, outDir, srcFolder, solid,
                                  archiveType)
        bolt.compress7z(command, outDir, destArchive, srcFolder, progress)
        Installer.rmTempDir()

    def _unpack(self, srcInstaller, fileNames, progress=None):
        """Recursive function: completely extracts the source installer to subTempDir.
        It does NOT clear the temp folder.  This should be done prior to calling the function.
        Each archive and sub-archive is extracted to its own sub-directory to prevent file thrashing"""
        #--Sanity check
        if not fileNames: raise ArgumentError(u"No files to extract for %s." % srcInstaller.s)
        tmpDir = Installer.getTempDir()
        tempList = bolt.Path.baseTempDir().join(u'WryeBash_listfile.txt')
        #--Dump file list
        try:
            with tempList.open('w',encoding='utf-8-sig') as out:
                out.write(u'\n'.join(fileNames))
        except Exception as e:
            raise StateError, (u"Error creating file list for 7z:\nError: %s"
                               % e), sys.exc_info()[2]
        #--Determine settings for 7z
        installerCRC = srcInstaller.crc
        if isinstance(srcInstaller,InstallerArchive):
            srcInstaller = GPath(srcInstaller.archive)
            apath = dirs['installers'].join(srcInstaller)
        else:
            apath = srcInstaller
        subTempDir = tmpDir.join(u"%08X" % installerCRC)
        if progress:
            progress(0,srcInstaller.s+u'\n'+_(u'Extracting files...'))
            progress.setFull(1+len(fileNames))
        command = u'"%s" x "%s" -y -o%s @%s -scsUTF-8 -sccUTF-8' % (
            exe7z, apath.s, subTempDir.s, tempList.s)
        #--Extract files
        try:
            subArchives = bolt.extract7z(command, srcInstaller, progress,
                                         readExtensions=readExts)
        finally:
            tempList.remove()
            bolt.clearReadOnly(subTempDir) ##: do this once
        #--Recursively unpack subArchives
        for archive in map(subTempDir.join, subArchives):
            self._unpack(archive, [u'*'])

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
        reList = Installer.reList
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
            if progress:
                numFiles = countFilesInArchive(arch,
                                listFilePath=self.tempList, recurse=recurse)
                progress.state = 0
                progress.setFull(numFiles)
            #--Extract files
            args = u'"%s" -y -o%s @%s -scsUTF-8 -sccUTF-8' % (
                arch.s, self.getTempDir().s, self.tempList.s)
            if recurse: args += u' -r'
            command = u'"%s" x %s' % (exe7z, args)
            try:
                bolt.extract7z(command, archive, progress)
            finally:
                self.tempList.remove()
                bolt.clearReadOnly(self.getTempDir())
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
        timestamps = modInfos.timestamp()
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
                balt.shellMove(stageDataDir, destDir, progress.getParent())
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
        bolt.clearReadOnly(self.getTempDir())
        tempDirJoin = self.getTempDir().join
        destDirJoin = destDir.join
        for file_ in files:
            srcFull = tempDirJoin(file_)
            destFull = destDirJoin(file_)
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
            reList = Installer.reList
            file = u''
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
            text.sort()
            #--Output
            for line in text:
                dir = line[0]
                isdir = line[1]
                log(u'  ' * dir.count(os.sep) + os.path.split(dir)[1] + (
                    os.sep if isdir else u''))
            log(u'[/xml][/spoiler]')
            return bolt.winNewLines(log.out.getvalue())

#------------------------------------------------------------------------------
class InstallerProject(Installer):
    """Represents a directory/build installer entry."""
    __slots__ = tuple() #--No new slots

    @staticmethod
    def removeEmpties(name):
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
        Installer.refreshSizeCrcDate(apRoot, src_sizeCrcDate, progress,
                                     fullRefresh)
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
        timestamps = modInfos.timestamp()
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
                balt.shellMove(stageDataDir, destDir, progress.getParent())
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
        length = len(self.fileSizeCrcs)
        if not length: return
        archive, archiveType, solid = compressionSettings(archive, blockSize,
                                                          isSolid)
        outDir = dirs['installers']
        realOutFile = outDir.join(archive)
        outFile = outDir.join(u'bash_temp_nonunicode_name.tmp')
        num = 0
        while outFile.exists():
            outFile += unicode(num)
            num += 1
        project = outDir.join(project)
        with project.unicodeSafe() as projectDir:
            #--Dump file list
            with self.tempList.open('w',encoding='utf-8-sig') as out:
                if release:
                    out.write(u'*thumbs.db\n')
                    out.write(u'*desktop.ini\n')
                    out.write(u'--*\\')
            #--Compress
            command = u'"%s" a "%s" -t"%s" %s -y -r -o"%s" -i!"%s\\*" -x@%s -scsUTF-8 -sccUTF-8' % (exe7z, outFile.temp.s, archiveType, solid, outDir.s, projectDir.s, self.tempList.s)
            try:
                bolt.compress7z(command, outDir, outFile.tail, projectDir,
                                progress)
            finally:
                self.tempList.remove()
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
                config.name = decode(ins.readNetString(),encoding='utf-8')
                config.vMajor, = ins.unpack('i',4)
                config.vMinor, = ins.unpack('i',4)
                for attr in ('author','email','website','abstract'):
                    setattr(config,attr,decode(ins.readNetString(),encoding='utf-8'))
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
        def walkPath(folder, depth):
            for entry in os.listdir(folder):
                path = os.path.join(folder, entry)
                if os.path.isdir(path):
                    log(u' ' * depth + entry + u'\\')
                    depth += 2
                    walkPath(path, depth)
                    depth -= 2
                else:
                    log(u' ' * depth + entry)
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
class InstallersData(DataDict):
    """Installers tank data. This is the data source for the InstallersList."""
    miscTrackedFiles = TrackedFileInfos() # hack to track changes in installed
    # inis etc _in the Data/ dir_. Keys are absolute paths to those files

    def __init__(self):
        self.dir = dirs['installers']
        self.bashDir = dirs['bainData']
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

    @staticmethod
    def track(absPath, factory):
        InstallersData.miscTrackedFiles.track(absPath, factory)

    def addMarker(self,name):
        path = GPath(name)
        self[path] = InstallerMarker(path)
        self.irefresh(what='OS')

    def setChanged(self,hasChanged=True):
        """Mark as having changed."""
        self.hasChanged = hasChanged

    def refresh(self, *args, **kwargs): return self.irefresh(*args, **kwargs)

    def irefresh(self,progress=None,what='DIONSC',fullRefresh=False):
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
                dirs['mods'], self.data_sizeCrcDate, progress, fullRefresh)
        if 'I' in what: changed |= self.refreshInstallers(progress,fullRefresh)
        if 'O' in what or changed: changed |= self.refreshOrder()
        if 'N' in what or changed: changed |= self.refreshNorm()
        if 'S' in what or changed: changed |= self.refreshStatus()
        if 'C' in what or changed: changed |= self.refreshConverters(progress,fullRefresh)
        #--Done
        if changed: self.hasChanged = True
        return changed

    def updateDictFile(self): # CRUFT pickle
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

    #--Dict Functions -----------------------------------------------------------
    def delete(self, items, **kwargs):
        """Delete multiple installers. Delete entry AND archive file itself."""
        toDelete = []
        markers = []
        toDeleteAppend = toDelete.append
        dirJoin = self.dir.join
        selfLastKey = self.lastKey
        for item in items:
            if item == selfLastKey: continue
            if isinstance(self[item], InstallerMarker): markers.append(item)
            else: toDeleteAppend(dirJoin(item))
        #--Delete
        try:
            for m in markers: del self.data[m]
            _delete(toDelete, **kwargs)
        finally:
            refresh = bool(markers)
            for item in toDelete:
                if not item.exists():
                    del self.data[item.tail]
                    refresh = True
            if refresh: self.delete_Refresh(toDelete) # will "set changed" too

    def delete_Refresh(self, deleted): self.irefresh(what='ION') # unused as
    # Installers follow the _shellUI path and refresh in InstallersData.delete

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

    #--Refresh Functions ------------------------------------------------------
    def refreshInstallers(self,progress=None,fullRefresh=False):
        """Refresh installer data."""
        progress = progress or bolt.Progress()
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
        for installer in self.values():
            if installer.hasBCF and isinstance(installer,InstallerArchive):
                return True
        return False

    def applyEmbeddedBCFs(self,installers=None,destArchives=None,progress=bolt.Progress()):
        if not installers:
            installers = [x for x in self.values() if
                          x.hasBCF and isinstance(x, InstallerArchive)]
        if not installers: return False
        if not destArchives:
            destArchives = [GPath(x.archive) for x in installers]
        progress.setFull(len(installers))
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
            #--Create the converter, apply it
            destArchive = destArchives[i]
            converter = InstallerConverter(bcfFile.tail)
            try:
                converter.apply(destArchive, self.crc_installer,
                                bolt.SubProgress(progress, 0.0, 0.99),
                                installer.crc)
            except StateError:
                deprint(u'%s: ' % destArchive.s + _(u'An error occurred '
                        u'while applying an Embedded BCF.'), traceback=True)
                bcfFile.remove()
                continue
            ##: finally: bcfFile.remove() # ?
            #--Add the new archive to Bash
            if destArchive not in self:
                self[destArchive] = InstallerArchive(destArchive)
            #--Apply settings to the new archive
            iArchive = self[destArchive]
            converter.applySettings(iArchive)
            #--Refresh UI
            pArchive = dirs['installers'].join(destArchive)
            iArchive.refreshed = False
            iArchive.refreshBasic(pArchive,SubProgress(progress,0.99,1.0),True)
            # If applying the BCF created a new archive with an embedded BCF,
            # ignore the embedded BCF for now, so we don't end up in an
            # infinite loop
            iArchive.hasBCF = False
            bcfFile.remove()
        self.irefresh(what='I')
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
            return installers != set(x for x,y in self.iteritems() if not isinstance(y,InstallerMarker) and not (isinstance(y,InstallerProject) and y.skipRefresh))
        else:
            return installers != set(x for x,y in self.iteritems() if isinstance(y,InstallerArchive))

    def refreshConvertersNeeded(self):
        """Returns true if refreshConverters is necessary. (Point is to skip use
        of progress dialog when possible."""
        self.pruneConverters()
        archives = set([])
        scanned = set([])
        convertersJoin = dirs['converters'].join
        converterGet = self.bcfPath_sizeCrcDate.get
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
        inOrder, pending = [], []
        orderedAppend = inOrder.append
        pendingAppend = pending.append
        for archive,installer in self.iteritems():
            if installer.order >= 0:
                orderedAppend(archive)
            else:
                pendingAppend(archive)
        pending.sort()
        inOrder.sort()
        inOrder.sort(key=lambda x: data[x].order)
        if self.lastKey in inOrder:
            index = inOrder.index(self.lastKey)
            inOrder[index:index] = pending
        else:
            inOrder += pending
        order = 0
        for archive in inOrder:
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
        for installer in self.itervalues():
            changed |= installer.refreshStatus(self)
        return changed

    #--Converters
    @staticmethod
    def validConverterName(path):
        return path.cext in defaultExt and (path.csbody[-4:] == u'-bcf' or u'-bcf-' in path.csbody)

    def refreshConverters(self,progress=None,fullRefresh=False):
        """Refreshes converter status, and moves duplicate BCFs out of the way"""
        progress = progress or bolt.Progress()
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
        orderKey = lambda p: data[p].order
        newList = [x for x in sorted(data,key=orderKey) if x not in moveSet]
        moveList.sort(key=orderKey)
        newList[newPos:newPos] = moveList
        for index,archive in enumerate(newList):
            data[archive].order = index
        self.setChanged()

    @staticmethod
    def updateTable(destFiles, value):
        """Set the 'installer' column in mod and ini tables for the
        destFiles."""
        for i in destFiles:
            if value and reModExt.match(i.cext): # if value == u'' we come from delete !
                modInfos.table.setItem(i, 'installer', value)
            elif i.head.cs == u'ini tweaks':
                if value:
                    iniInfos.table.setItem(i.tail, 'installer', value)
                else: # installer is the only column used in iniInfos table
                    iniInfos.table.delRow(i.tail)

    #--Install
    def _createTweaks(self, destFiles, installer, tweaksCreated):
        """Generate INI Tweaks when a CRC mismatch is detected while
        installing a mod INI (not ini tweak) in the Data/ directory.

        If the current CRC of the ini is different than the one BAIN is
        installing, a tweak file will be generated. Call me *before*
        installing the new inis then call _editTweaks() to populate the tweaks.
        """
        for relPath in destFiles:
            if (not relPath.cext in (u'.ini', u'.cfg') or
                # don't create ini tweaks for overridden ini tweaks...
                relPath.head.cs == u'ini tweaks'): continue
            oldCrc = self.data_sizeCrcDate.get(relPath, (None, None, None))[1]
            newCrc = installer.data_sizeCrc.get(relPath, (None, None))[1]
            if oldCrc is None or newCrc is None or newCrc == oldCrc: continue
            iniAbsDataPath = dirs['mods'].join(relPath)
            # Create a copy of the old one
            baseName = dirs['tweaks'].join(u'%s, ~Old Settings [%s].ini' % (
                iniAbsDataPath.sbody, iniAbsDataPath.sbody))
            tweakPath = self.__tweakPath(baseName)
            iniAbsDataPath.copyTo(tweakPath)
            tweaksCreated.add((tweakPath, iniAbsDataPath))

    @staticmethod
    def __tweakPath(baseName):
        oldIni, num = baseName, 1
        while oldIni.exists():
            suffix = u' - Copy' + (u'' if num == 1 else u' (%i)' % num)
            oldIni = baseName.head.join(baseName.sbody + suffix + baseName.ext)
            num += 1
        return oldIni

    @staticmethod
    def _editTweaks(tweaksCreated):
        """Edit created ini tweaks with settings that differ and/or don't exist
        in the new ini."""
        removed = set()
        for (tweakPath, iniAbsDataPath) in tweaksCreated:
            iniFile = BestIniFile(iniAbsDataPath)
            currSection = None
            lines = []
            for (text, section, setting, value, status, lineNo,
                 deleted) in iniFile.getTweakFileLines(tweakPath):
                if status in (10, -10):
                    # A setting that exists in both INI's, but is different,
                    # or a setting that doesn't exist in the new INI.
                    if section == u']set[' or section == u']setGS[':
                        lines.append(text + u'\n')
                    elif section != currSection:
                        section = currSection
                        if not section: continue
                        lines.append(u'\n[%s]\n' % section)
                    elif not section:
                        continue
                    else:
                        lines.append(text + u'\n')
            if not lines: # avoid creating empty tweaks
                removed.add((tweakPath, iniAbsDataPath))
                tweakPath.remove()
                continue
            # Re-write the tweak
            with tweakPath.open('w') as ini:
                ini.write(u'; INI Tweak created by Wrye Bash, using settings '
                          u'from old file.\n\n')
                ini.writelines(lines)
        tweaksCreated -= removed

    def _install(self,archives,progress=None,last=False,override=True):
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
            for installer in self.itervalues():
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
                self._createTweaks(destFiles, installer, tweaksCreated)
                installer.install(archive, destFiles, self.data_sizeCrcDate,
                                  SubProgress(progress, index, index + 1))
                InstallersData.updateTable(destFiles, archive.s)
            installer.isActive = True
            mask |= set(installer.data_sizeCrc)
        if tweaksCreated:
            self._editTweaks(tweaksCreated)
        return tweaksCreated

    def install(self,archives,progress=None,last=False,override=True):
        try: return self._install(archives, progress, last, override)
        finally: self.irefresh(what='NS')

    #--Uninstall, Anneal, Clean
    @staticmethod
    def _determineEmptyDirs(emptyDirs, removedFiles):
        allRemoves = set(removedFiles)
        allRemovesAdd, removedFilesAdd = allRemoves.add, removedFiles.add
        emptyDirsClear, emptyDirsAdd = emptyDirs.clear, emptyDirs.add
        exclude = {dirs['mods'], dirs['mods'].join(u'Docs')} # don't bother
        # with those (Data won't likely be removed and Docs we want it around)
        emptyDirs -= exclude
        while emptyDirs:
            testDirs = set(emptyDirs)
            emptyDirsClear()
            for folder in sorted(testDirs, key=len, reverse=True):
                # Sorting by length, descending, ensure we always
                # are processing the deepest directories first
                files = set(map(folder.join, folder.list()))
                remaining = files - allRemoves
                if not remaining: # If all items in this directory will be
                    # removed, this directory is also safe to remove.
                    removedFiles -= files
                    removedFilesAdd(folder)
                    allRemovesAdd(folder)
                    emptyDirsAdd(folder.head)
            emptyDirs -= exclude
        return removedFiles

    def _removeFiles(self, removes, progress=None):
        """Performs the actual deletion of files and updating of internal data.clear
           used by 'uninstall' and 'anneal'."""
        modsDirJoin = dirs['mods'].join
        emptyDirs = set()
        emptyDirsAdd = emptyDirs.add
        removedFiles = set()
        removedFilesAdd = removedFiles.add
        reModExtSearch = reModExt.search
        removedPlugins = set()
        removedPluginsAdd = removedPlugins.add
        #--Construct list of files to delete
        for relPath in removes:
            path = modsDirJoin(relPath)
            if path.exists():
                removedFilesAdd(path)
            if reModExtSearch(relPath.s):
                removedPluginsAdd(relPath)
            emptyDirsAdd(path.head)
        #--Now determine which directories will be empty, replacing subsets of
        # removedFiles by their parent dir if the latter will be emptied
        removedFiles = self._determineEmptyDirs(emptyDirs, removedFiles)
        nonPlugins = removedFiles - set(map(modsDirJoin, removedPlugins))
        ex = None # if an exception is raised we must again check removes
        try: #--Do the deletion
            if nonPlugins:
                parent = progress.getParent() if progress else None
                balt.shellDelete(nonPlugins, parent=parent)
            #--Delete mods and remove them from load order
            if removedPlugins:
                modInfos.delete(removedPlugins, doRefresh=True, recycle=False)
                ##: HACK - because I short circuit ModInfos.refresh() via
                # delete_Refresh(), modList.RefreshUI won't be called leaving
                # stale entries in modList._gList._item_itemIdd - note that
                # deleting via the UIList calls modList.RefreshUI() which
                # cleans _gList internal dictionaries
                balt.Link.Frame.modList.RefreshUI(refreshSaves=True)
                # This is _less_ hacky than _not_ calling modInfos.delete().
                # Real solution: refresh should keep track of deleted, added,
                # modified - (ut)
        except (bolt.CancelError, bolt.SkipError): ex = sys.exc_info()
        except:
            ex = sys.exc_info()
            raise
        finally:
            if ex:removes = [f for f in removes if not modsDirJoin(f).exists()]
            InstallersData.updateTable(removes, u'')
            #--Update InstallersData
            data_sizeCrcDatePop = self.data_sizeCrcDate.pop
            for relPath in removes:
                data_sizeCrcDatePop(relPath, None)

    def __filter(self, archive, installer, removes, restores): ##: comments
        files = set(installer.data_sizeCrc)
        myRestores = (removes & files) - set(restores)
        for file in myRestores:
            if installer.data_sizeCrc[file] != \
                    self.data_sizeCrcDate.get(file,(0, 0, 0))[:2]:
                restores[file] = archive
            removes.discard(file)
        return files

    def uninstall(self,unArchives,progress=None):
        """Uninstall selected archives."""
        if unArchives == 'ALL': unArchives = self.data
        unArchives = set(unArchives)
        data = self.data
        data_sizeCrcDate = self.data_sizeCrcDate
        #--Determine files to remove and files to restore. Keep in mind that
        #  multiple input archives may be interspersed with other archives that
        #  may block (mask) them from deleting files and/or may provide files
        #  that should be restored to make up for previous files. However,
        #  restore can be skipped, if existing files matches the file being
        #  removed.
        masked = set()
        removes = set()
        restores = {}
        #--March through archives in reverse order...
        getArchiveOrder =  lambda tup: tup[1].order
        for archive, installer in sorted(data.iteritems(), key=getArchiveOrder,
                                         reverse=True):
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
                masked |= self.__filter(archive, installer, removes, restores)
        try:
            #--Remove files, update InstallersData, update load order
            self._removeFiles(removes, progress)
            #--De-activate
            for archive in unArchives:
                data[archive].isActive = False
            #--Restore files
            if settings['bash.installers.autoAnneal']:
                self._restoreFiles(restores, progress)
        finally:
            self.irefresh(what='NS')

    def _restoreFiles(self, restores, progress):
        getArchiveOrder = lambda x: self[x].order
        restoreArchives = sorted(set(restores.itervalues()),
                                 key=getArchiveOrder, reverse=True)
        if restoreArchives:
            progress.setFull(len(restoreArchives))
            for index,archive in enumerate(restoreArchives):
                progress(index,archive.s)
                installer = self[archive]
                destFiles = set(x for x,y in restores.iteritems() if y == archive)
                if destFiles:
                    installer.install(archive, destFiles, self.data_sizeCrcDate,
                        SubProgress(progress,index,index+1))
                    InstallersData.updateTable(destFiles, archive.s)

    def anneal(self,anPackages=None,progress=None):
        """Anneal selected packages. If no packages are selected, anneal all.
        Anneal will:
        * Correct underrides in anPackages.
        * Install missing files from active anPackages."""
        progress = progress if progress else bolt.Progress()
        data = self.data
        anPackages = set(anPackages or data)
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
        getArchiveOrder =  lambda tup: tup[1].order
        for archive, installer in sorted(data.iteritems(), key=getArchiveOrder,
                                         reverse=True):
            #--Other active package. May provide a restore file.
            #  And/or may block later uninstalls.
            if installer.isActive:
                self.__filter(archive, installer, removes, restores)
        try:
            #--Remove files, update InstallersData, update load order
            self._removeFiles(removes, progress)
            #--Restore files
            self._restoreFiles(restores, progress)
        finally:
            self.irefresh(what='NS')

    def clean(self, progress):  ##: add error handling/refresh remove ghosts
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

    #--Utils
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
        getArchiveOrder = lambda a: self[a].order
        getBSAOrder = lambda b: modInfos.activeCached.index(b[1].root + ".esp") ##: why list() ?
        # Calculate bsa conflicts
        if showBSA:
            # Create list of active BSA files in srcInstaller
            srcFiles = srcInstaller.data_sizeCrc
            srcBSAFiles = [x for x in srcFiles.keys() if x.ext == ".bsa"]
#            print("Ordered: {}".format(modInfos.activeCached))
            activeSrcBSAFiles = [x for x in srcBSAFiles if modInfos.isActiveCached(x.root + ".esp")]
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
                activeBSAFiles.extend([(package, x, libbsa.BSAHandle(dirs['mods'].join(x.s))) for x in BSAFiles if modInfos.isActiveCached(x.root + ".esp")])
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

    def filterInstallables(self, installerKeys):
        def installable(x): # type: 0: unset/invalid; 1: simple; 2: complex
            return x in self and self[x].type in (1, 2) and isinstance(self[x],
                (InstallerArchive, InstallerProject))
        return filter(installable, installerKeys)

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

    def __init__(self):
        self.mod_group = {}

    def readFromModInfos(self,mods=None):
        """Imports mods/groups from modInfos."""
        column = modInfos.table.getColumn('group')
        mods = mods or column.keys()# if mods are None read groups for all mods
        groups = tuple(column.get(x) for x in mods)
        self.mod_group.update((x,y) for x,y in zip(mods,groups) if y)

    @staticmethod
    def assignedGroups():
        """Return all groups that are currently assigned to mods."""
        column = modInfos.table.getColumn('group')
        return set(x[1] for x in column.items() if x[1]) #x=(bolt.Path,'group')

    def writeToModInfos(self,mods=None):
        """Exports mod groups to modInfos."""
        mods = mods or modInfos.table.data.keys()
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
            self.unused2 = bass.null2
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
        namePos = PCFaces.save_getNamePos(saveFile.fileInfo.name,data,encode(saveFile.pcName))
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
        namePos = PCFaces.save_getNamePos(saveFile.fileInfo.name,oldData,encode(saveFile.pcName))
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
            buff.write(
                encode(face.pcName, firstEncoding=Path.sys_fs_enc) + '\x00')
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
        namePos = PCFaces.save_getNamePos(saveInfo.name,data,encode(saveFile.pcName))
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
                                                    eid = decode(subrec.data)
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

#------------------------------------------------------------------------------
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
        npc.full = encode(newName)
        saveFile.pcName = newName
        saveFile.setRecord(npc.getTuple(fid,version))
        saveFile.safeSave()

# Mergeability ----------------------------------------------------------------
##: belong to patcher/patch_files (?) but used in modInfos - cyclic imports
def isPBashMergeable(modInfo,verbose=True):
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
    mergeTypes = set([recClass.classType for recClass in bush.game.mergeClasses])
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
    dependent = [name.s for name, info in modInfos.iteritems()
                 if info.header.author != u'BASHED PATCH'
                 if modInfo.name in info.header.masters]
    if dependent:
        if not verbose: return False
        reasons += u'\n.    '+_(u'Is a master of mod(s): ')+u', '.join(sorted(dependent))+u'.'
    if reasons: return reasons
    return True

def _modIsMergeableNoLoad(modInfo,verbose):
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

def _modIsMergeableLoad(modInfo,verbose):
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
                elif not modInfos.isActiveCached(master):
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
        dependent = [name.s for name, info in modInfos.iteritems()
            if info.header.author != u'BASHED PATCH' and
            modInfo.name in info.header.masters and name not in modInfos.mergeable]
        if dependent:
            if not verbose: return False
            reasons.append(u'\n.    '+_(u'Is a master of non-mergeable mod(s): %s.') % u', '.join(sorted(dependent)))
        if reasons: return reasons
        return True

# noinspection PySimplifyBooleanCheck
def isCBashMergeable(modInfo,verbose=True):
    """Returns True or error message indicating whether specified mod is mergeable."""
    canmerge = _modIsMergeableNoLoad(modInfo, verbose)
    if verbose:
        loadreasons = _modIsMergeableLoad(modInfo, verbose)
        reasons = []
        if canmerge != True:
            reasons = canmerge
        if loadreasons != True:
            reasons.extend(loadreasons)
        if reasons: return u''.join(reasons)
        return True
    else:
        if canmerge == True:
            return _modIsMergeableLoad(modInfo, verbose)
        return False

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
        def getShellPath(folderKey): # move to env.py, mkdirs
            from bass import winreg
            if not winreg:  # unix _ HACK
                return GPath({'Personal'     : os.path.expanduser("~"),
                              'Local AppData': os.path.expanduser(
                                  "~") + u'/.local/share'}[folderKey])
            regKey = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                u'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\User Shell Folders')
            try:
                path = winreg.QueryValueEx(regKey,folderKey)[0]
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

def testUAC(gameDataPath):
    print 'testing UAC' # TODO(ut): bypass in Linux !
    tmpDir = bolt.Path.tempDir()
    tempFile = tmpDir.join(u'_tempfile.tmp')
    dest = gameDataPath.join(u'_tempfile.tmp')
    with tempFile.open('wb'): pass # create the file
    try: # to move it into the Game/Data/ directory
        balt.shellMove(tempFile, dest, askOverwrite=True, silent=True)
    except balt.AccessDeniedError:
        return True
    finally:
        tmpDir.rmtree(safety=tmpDir.stail)
        balt.shellDeletePass(dest)
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
    dirs['app'] = bush.gamePath
    dirs['mods'] = dirs['app'].join(u'Data')
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
            msg += u'\n'.join([u'%s' % x for x in relativePathError])
        raise BoltError(msg)

    # Setup LOOT API
    global configHelpers
    configHelpers = ConfigHelpers()

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
        from bass import winreg
        if not winreg: return
        for hkey in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for wow6432 in (u'',u'Wow6432Node\\'):
                try:
                    key = winreg.OpenKey(hkey,u'Software\\%sBoss' % wow6432)
                    value = winreg.QueryValueEx(key,u'Installed Path')
                except:
                    continue
                if value[1] != winreg.REG_SZ: continue
                installedPath = GPath(value[0])
                if not installedPath.exists(): continue
                tooldirs['boss'] = installedPath.join(u'BOSS.exe')
                break
            else:
                continue
            break

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
    inisettings['SoundSuccess'] = GPath(u'')
    inisettings['SoundError'] = GPath(u'')
    inisettings['EnableSplashScreen'] = True
    inisettings['PromptActivateBashedPatch'] = True
    inisettings['WarnTooManyFiles'] = True

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

def initBosh(personal='', localAppData='', oblivionPath='', bashIni=None):
    #--Bash Ini
    if not bashIni: bashIni = bass.GetBashIni()
    initDirs(bashIni,personal,localAppData, oblivionPath)
    global load_order, exe7z
    import load_order ##: move it from here - also called from restore settings
    load_order = load_order
    initOptions(bashIni)
    initLogFile()
    Installer.initData()
    exe7z = dirs['compiled'].join(exe7z).s

def initSettings(readOnly=False, _dat=u'BashSettings.dat',
                 _bak=u'BashSettings.dat.bak'):
    """Init user settings from files and load the defaults (also in basher)."""
    ##(178): drop .pkl support

    def _load(dat_file=_dat, oldPath=u'bash config.pkl'):
    # bolt.PickleDict.load() handles EOFError, ValueError falling back to bak
        return bolt.Settings( # calls PickleDict.load() and copies loaded data
            PickleDict(dirs['saveBase'].join(dat_file),
                       dirs['userApp'].join(oldPath), readOnly))

    _dat = dirs['saveBase'].join(_dat)
    _bak = dirs['saveBase'].join(_bak)
    def _loadBakOrEmpty(delBackup=False, ignoreBackup=False):
        _dat.remove()
        if delBackup: _bak.remove()
        # bolt machinery will automatically load the backup - bypass it if
        # user did, by temporarily renaming the .bak file
        if ignoreBackup: _bak.moveTo(_bak.s + u'.ignore')
        # load the .bak file, or an empty settings dict saved to disc at exit
        loaded = _load()
        if ignoreBackup: GPath(_bak.s + u'.ignore').moveTo(_bak.s)
        return loaded

    global settings
    try:
        settings = _load()
    except cPickle.UnpicklingError, err:
        msg = _(
            u"Error reading the Bash Settings database (the error is: '%s'). "
            u"This is probably not recoverable with the current file. Do you "
            u"want to try the backup BashSettings.dat? (It will have all your "
            u"UI choices of the time before last that you used Wrye Bash.")
        usebck = balt.askYes(None, msg % repr(err), _(u"Settings Load Error"))
        if usebck:
            try:
                settings = _loadBakOrEmpty()
            except cPickle.UnpicklingError, err:
                msg = _(
                    u"Error reading the BackupBash Settings database (the "
                    u"error is: '%s'). This is probably not recoverable with "
                    u"the current file. Do you want to delete the corrupted "
                    u"settings and load Wrye Bash without your saved UI "
                    u"settings?. (Otherwise Wrye Bash won't start up)")
                delete = balt.askYes(None, msg % repr(err),
                                     _(u"Settings Load Error"))
                if delete: settings = _loadBakOrEmpty(delBackup=True)
                else:raise
        else:
            msg = _(
                u"Do you want to delete the corrupted settings and load Wrye "
                u"Bash without your saved UI settings?. (Otherwise Wrye Bash "
                u"won't start up)")
            delete = balt.askYes(None, msg, _(u"Settings Load Error"))
            if delete: # ignore bak but don't delete
                settings = _loadBakOrEmpty(ignoreBackup=True)
            else: raise
    # No longer pulling version out of the readme, but still need the old
    # cached value for upgrade check! (!)
    if 'bash.readme' in settings:
        settings['bash.version'] = _(settings['bash.readme'][1])
        del settings['bash.readme']

# Main ------------------------------------------------------------------------
if __name__ == '__main__':
    print _(u'Compiled')
