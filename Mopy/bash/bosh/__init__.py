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

############# bush.game must be set by the time you import bosh ! #############

# Imports ---------------------------------------------------------------------
#--Python
import cPickle
import collections
import copy
import errno
import os
import re
import string
import struct
import sys
import time
import traceback
from collections import OrderedDict
from functools import wraps
from itertools import imap
from operator import attrgetter

from ._mergeability import isPBashMergeable, isCBashMergeable
from .mods_metadata import ConfigHelpers
from .. import bass, bolt, balt, bush, env, load_order, archives
from .. import patcher # for configIsCBash()
from ..archives import readExts
from ..bass import dirs, inisettings, tooldirs, reModExt
from ..bolt import BoltError, AbstractError, ArgumentError, StateError, \
    PermissionError, FileError, CancelError, SkipError
from ..bolt import GPath, Flags, DataDict, SubProgress, cstrip, \
    deprint, sio, Path
from ..bolt import decode, encode
from ..brec import MreRecord, ModReader, ModError, ModWriter, getObjectIndex, \
    getFormIndices
from ..cint import CBashApi
from ..parsers import LoadFactory, ModFile

#--Settings
settings = None
try:
    allTags = bush.game.allTags
    allTagsSet = set(allTags)
except AttributeError: # 'NoneType' object has no attribute 'allTags'
    pass
oldTags = sorted((u'Merge',))
oldTagsSet = set(oldTags)

reOblivion = re.compile(
    u'^(Oblivion|Nehrim)(|_SI|_1.1|_1.1b|_1.5.0.8|_GOTY non-SI).esm$', re.U)

undefinedPath = GPath(u'C:\\not\\a\\valid\\path.exe')
empty_path = GPath(u'')
undefinedPaths = {GPath(u'C:\\Path\\exe.exe'), undefinedPath}

# Singletons, Constants -------------------------------------------------------
#--Constants
#..Bit-and this with the fid to get the objectindex.
oiMask = 0xFFFFFFL

#--Singletons
gameInis = None    # type: tuple[OblivionIni]
oblivionIni = None # type: OblivionIni
modInfos  = None   # type: ModInfos
saveInfos = None   # type: SaveInfos
iniInfos = None    # type: INIInfos
bsaInfos = None    # type: BSAInfos
screensData = None # type: ScreensData
#--Config Helper files (LOOT Master List, etc.)
configHelpers = None # type: mods_metadata.ConfigHelpers

#--Header tags
reVersion = re.compile(
  ur'^(version[:.]*|ver[:.]*|rev[:.]*|r[:.\s]+|v[:.\s]+) *([-0-9a-zA-Z.]*\+?)',
  re.M | re.I | re.U)

#--Mod Extensions
reExGroup = re.compile(u'(.*?),',re.U)
_reEsmExt  = re.compile(ur'\.esm(.ghost)?$', re.I | re.U)
reEspExt  = re.compile(ur'\.esp(.ghost)?$',re.I|re.U)
__exts = ur'((\.(' + ur'|'.join(ext[1:] for ext in readExts) + ur'))|)$'
reTesNexus = re.compile(ur'(.*?)(?:-(\d{1,6})(?:\.tessource)?(?:-bain)'
    ur'?(?:-\d{0,6})?(?:-\d{0,6})?(?:-\d{0,6})?(?:-\w{0,16})?(?:\w)?)?'
    + __exts, re.I | re.U)
reTESA = re.compile(ur'(.*?)(?:-(\d{1,6})(?:\.tessource)?(?:-bain)?)?'
    + __exts, re.I | re.U)
del __exts
imageExts = {u'.gif', u'.jpg', u'.png', u'.jpeg', u'.bmp', u'.tif'}

#------------------------------------------------------------------------------
# Save I/O --------------------------------------------------------------------
#------------------------------------------------------------------------------
class SaveFileError(FileError):
    """TES4 Save File Error: File is corrupted."""
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
        self._plugins = None
        self.other = None
        self.valid = False

    def mapMasters(self,masterMap):
        """Update plugin names according to masterMap."""
        if not self.valid: raise FileError(self.name,"File not initialized.")
        self._plugins = [(x, y, masterMap.get(z,z)) for x,y,z in self._plugins]

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
            self._plugins = []
            type, = unpack('=B',1)
            if type != 0:
                raise FileError(self.name,u'Expected plugins record, but got %d.' % type)
            count, = unpack('=I',4)
            for x in range(count):
                espid,index,modLen = unpack('=2BI',6)
                modName = GPath(decode(ins.read(modLen)))
                self._plugins.append((espid, index, modName))
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
            pack('=I', len(self._plugins))
            for (espid,index,modName) in self._plugins:
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
        self._plugins = None
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
            self._plugins = []
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
                self._plugins.append(plugin)
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
            pack('=I', len(self._plugins))
            for (opcodeBase,chunks) in self._plugins:
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
        for (opcodeBase,chunks) in self._plugins:
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
        self._plugins = newPlugins

    def safeSave(self):
        """Save data to file safely."""
        self.save(self.path.temp,self.path.mtime)
        self.path.untemp()

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
        if iref >= len(self.fids): raise ModError(self.fileInfo.name,
                                                  u'IRef from Mars.')
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
        if obseFile._plugins is not None:
            for (opcodeBase,chunks) in obseFile._plugins:
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
                            self._handle_pluggy(chunkBuff, chunkTypeNum,
                                                chunkVersion, espMap, ins, log,
                                                unpack)

    @staticmethod
    def _handle_pluggy(chunkBuff, chunkTypeNum, chunkVersion, espMap, ins, log,
                       unpack):
        if chunkTypeNum == 1:
            #--Pluggy TypeESP
            log(_(u'    Pluggy ESPs'))
            log(_(u'    EID   ID    Name'))
            while ins.tell() < len(chunkBuff):
                if chunkVersion == 2:
                    espId, modId, = unpack('=BB', 2)
                    log(u'    %02X    %02X' % (espId, modId))
                    espMap[modId] = espId
                else:  #elif chunkVersion == 1"
                    espId, modId, modNameLen, = unpack('=BBI', 6)
                    modName = ins.read(modNameLen)
                    log(u'    %02X    %02X    %s' % (espId, modId, modName))
                    espMap[modId] = modName  # was [espId]
        elif chunkTypeNum == 2:
            #--Pluggy TypeSTR
            log(_(u'    Pluggy String'))
            strId, modId, strFlags, = unpack('=IBB', 6)
            strData = ins.read(len(chunkBuff) - ins.tell())
            log(u'      ' + _(u'StrID :') + u' %u' % strId)
            log(u'      ' + _(u'ModID :') + u' %02X %s' % (
                modId, espMap[modId] if modId in espMap else u'ERROR',))
            log(u'      ' + _(u'Flags :') + u' %u' % strFlags)
            log(u'      ' + _(u'Data  :') + u' %s' % strData)
        elif chunkTypeNum == 3:
            #--Pluggy TypeArray
            log(_(u'    Pluggy Array'))
            arrId, modId, arrFlags, arrSize, = unpack('=IBBI', 10)
            log(_(u'      ArrID : %u') % (arrId,))
            log(_(u'      ModID : %02X %s') % (
                modId, espMap[modId] if modId in espMap else u'ERROR',))
            log(_(u'      Flags : %u') % (arrFlags,))
            log(_(u'      Size  : %u') % (arrSize,))
            while ins.tell() < len(chunkBuff):
                elemIdx, elemType, = unpack('=IB', 5)
                elemStr = ins.read(4)
                if elemType == 0:  #--Integer
                    elem, = struct.unpack('=i', elemStr)
                    log(u'        [%u]  INT  %d' % (elemIdx, elem,))
                elif elemType == 1:  #--Ref
                    elem, = struct.unpack('=I', elemStr)
                    log(u'        [%u]  REF  %08X' % (elemIdx, elem,))
                elif elemType == 2:  #--Float
                    elem, = struct.unpack('=f', elemStr)
                    log(u'        [%u]  FLT  %08X' % (elemIdx, elem,))
        elif chunkTypeNum == 4:
            #--Pluggy TypeName
            log(_(u'    Pluggy Name'))
            refId, = unpack('=I', 4)
            refName = ins.read(len(chunkBuff) - ins.tell())
            newName = u''
            for c in refName:
                ch = c if (c >= chr(0x20)) and (c < chr(0x80)) else '.'
                newName = newName + ch
            log(_(u'      RefID : %08X') % refId)
            log(_(u'      Name  : %s') % decode(newName))
        elif chunkTypeNum == 5:
            #--Pluggy TypeScr
            log(_(u'    Pluggy ScreenSize'))
            #UNTESTED - uncomment following line to skip this record type
            #continue
            scrW, scrH, = unpack('=II', 8)
            log(_(u'      Width  : %u') % scrW)
            log(_(u'      Height : %u') % scrH)
        elif chunkTypeNum == 6:
            #--Pluggy TypeHudS
            log(u'    ' + _(u'Pluggy HudS'))
            #UNTESTED - uncomment following line to skip this record type
            #continue
            hudSid, modId, hudFlags, hudRootID, hudShow, hudPosX, hudPosY, \
            hudDepth, hudScaleX, hudScaleY, hudAlpha, hudAlignment, \
            hudAutoScale, = unpack('=IBBBBffhffBBB', 29)
            hudFileName = decode(ins.read(len(chunkBuff) - ins.tell()))
            log(u'      ' + _(u'HudSID :') + u' %u' % hudSid)
            log(u'      ' + _(u'ModID  :') + u' %02X %s' % (
                modId, espMap[modId] if modId in espMap else u'ERROR',))
            log(u'      ' + _(u'Flags  :') + u' %02X' % hudFlags)
            log(u'      ' + _(u'RootID :') + u' %u' % hudRootID)
            log(u'      ' + _(u'Show   :') + u' %02X' % hudShow)
            log(u'      ' + _(u'Pos    :') + u' %f,%f' % (hudPosX, hudPosY,))
            log(u'      ' + _(u'Depth  :') + u' %u' % hudDepth)
            log(u'      ' + _(u'Scale  :') + u' %f,%f' % (
                hudScaleX, hudScaleY,))
            log(u'      ' + _(u'Alpha  :') + u' %02X' % hudAlpha)
            log(u'      ' + _(u'Align  :') + u' %02X' % hudAlignment)
            log(u'      ' + _(u'AutoSc :') + u' %02X' % hudAutoScale)
            log(u'      ' + _(u'File   :') + u' %s' % hudFileName)
        elif chunkTypeNum == 7:
            #--Pluggy TypeHudT
            log(_(u'    Pluggy HudT'))
            #UNTESTED - uncomment following line to skip this record type
            #continue
            hudTid, modId, hudFlags, hudShow, hudPosX, hudPosY, hudDepth, \
                = unpack('=IBBBffh', 17)
            hudScaleX, hudScaleY, hudAlpha, hudAlignment, hudAutoScale, \
            hudWidth, hudHeight, hudFormat, = unpack('=ffBBBIIB', 20)
            hudFontNameLen, = unpack('=I', 4)
            hudFontName = decode(ins.read(hudFontNameLen))
            hudFontHeight, hudFontWidth, hudWeight, hudItalic, hudFontR, \
            hudFontG, hudFontB, = unpack('=IIhBBBB', 14)
            hudText = decode(ins.read(len(chunkBuff) - ins.tell()))
            log(u'      ' + _(u'HudTID :') + u' %u' % hudTid)
            log(u'      ' + _(u'ModID  :') + u' %02X %s' % (
                modId, espMap[modId] if modId in espMap else u'ERROR',))
            log(u'      ' + _(u'Flags  :') + u' %02X' % hudFlags)
            log(u'      ' + _(u'Show   :') + u' %02X' % hudShow)
            log(u'      ' + _(u'Pos    :') + u' %f,%f' % (hudPosX, hudPosY,))
            log(u'      ' + _(u'Depth  :') + u' %u' % hudDepth)
            log(u'      ' + _(u'Scale  :') + u' %f,%f' % (
                hudScaleX, hudScaleY,))
            log(u'      ' + _(u'Alpha  :') + u' %02X' % hudAlpha)
            log(u'      ' + _(u'Align  :') + u' %02X' % hudAlignment)
            log(u'      ' + _(u'AutoSc :') + u' %02X' % hudAutoScale)
            log(u'      ' + _(u'Width  :') + u' %u' % hudWidth)
            log(u'      ' + _(u'Height :') + u' %u' % hudHeight)
            log(u'      ' + _(u'Format :') + u' %u' % hudFormat)
            log(u'      ' + _(u'FName  :') + u' %s' % hudFontName)
            log(u'      ' + _(u'FHght  :') + u' %u' % hudFontHeight)
            log(u'      ' + _(u'FWdth  :') + u' %u' % hudFontWidth)
            log(u'      ' + _(u'FWeigh :') + u' %u' % hudWeight)
            log(u'      ' + _(u'FItal  :') + u' %u' % hudItalic)
            log(u'      ' + _(u'FRGB   :') + u' %u,%u,%u' % (
                hudFontR, hudFontG, hudFontB,))
            log(u'      ' + _(u'FText  :') + u' %s' % hudText)

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
    try:
        reSave = re.compile(ur'\.' + bush.game.ess.ext[1:] + '(f?)$',
                            re.I | re.U)
    except AttributeError: # 'NoneType' object has no attribute 'ess'
        pass

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

    def _recopy(self, savePath, saveName, pathFunc):
        """Renames/copies cofiles depending on supplied pathFunc."""
        if saveName: savePath = savePath.join(saveName)
        newPaths = CoSaves.getPaths(savePath)
        for oldPath,newPath in zip(self.paths,newPaths):
            if newPath.exists(): newPath.remove() ##: dont like it, investigate
            if oldPath.exists(): pathFunc(oldPath,newPath)

    def copy(self,savePath,saveName=None):
        """Copies cofiles."""
        self._recopy(savePath, saveName, bolt.Path.copyTo)

    def move(self,savePath,saveName=None):
        """Renames cofiles."""
        self._recopy(savePath, saveName, bolt.Path.moveTo)

    @staticmethod
    def get_new_paths(old_path, new_path):
        return zip(CoSaves.getPaths(old_path), CoSaves.getPaths(new_path))

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
            (inisettings['OblivionTexturesBSAName'].stail, 1138162634),
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

#------------------------------------------------------------------------------
class AFile(object):
    """Abstract file, supports caching - alpha."""
    _null_stat = (-1, None)

    def _stat_tuple(self): return self.abs_path.size_mtime()

    def __init__(self, abs_path, load_cache=False):
        self._abs_path = GPath(abs_path)
        #--Settings cache
        try:
            self._reset_cache(self._stat_tuple(), load_cache)
        except OSError:
            self._reset_cache(self._null_stat, load_cache=False)

    @property
    def abs_path(self): return self._abs_path

    @abs_path.setter
    def abs_path(self, val): self._abs_path = val

    def needs_update(self):
        try:
            stat_tuple = self._stat_tuple()
        except OSError:
            self._reset_cache(self._null_stat, load_cache=False)
            return False # we should not call needs_update on deleted files
        if self._file_changed(stat_tuple):
            self._reset_cache(stat_tuple, load_cache=True)
            return True
        return False

    def _file_changed(self, stat_tuple):
        return (self._file_size, self._file_mod_time) != stat_tuple

    def _reset_cache(self, stat_tuple, load_cache):
        """Reset cache flags (size, mtime,...) and possibly reload the cache.
        :param load_cache: if True either load the cache (header in Mod and
        SaveInfo) or reset it so it gets reloaded later
        """
        self._file_size, self._file_mod_time = stat_tuple

    def __repr__(self): return self.__class__.__name__ + u"<" + repr(
        self.abs_path.stail) + u">"

#------------------------------------------------------------------------------
class PluginsFullError(BoltError):
    """Usage Error: Attempt to add a mod to plugins when plugins is full."""
    def __init__(self,message=_(u'Load list is full.')):
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class MasterInfo:

    def _init_master_info(self):
        if self.modInfo:
            self.mtime = self.modInfo.mtime
            self.masterNames = self.modInfo.masterNames
        else:
            self.mtime = 0
            self.masterNames = tuple()

    def __init__(self, name):
        self.oldName = self.name = GPath(name)
        self.modInfo = modInfos.get(self.name,None)
        self.isGhost = self.modInfo and self.modInfo.isGhost
        self._init_master_info()

    def setName(self,name):
        self.name = GPath(name)
        self.modInfo = modInfos.get(self.name,None)
        self._init_master_info()

    def hasChanged(self):
        return self.name != self.oldName

    def isEsm(self):
        if self.modInfo:
            return self.modInfo.isEsm()
        else:
            return _reEsmExt.search(self.name.s)

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

    def getBashTags(self):
        """Retrieve bash tags for master info if it's present in Data."""
        if self.modInfo:
            return self.modInfo.getBashTags()
        else:
            return set()

    def getStatus(self):
        if not self.modInfo:
            return 30
        else:
            return 0

    def __repr__(self):
        return self.__class__.__name__ + u"<" + repr(self.name) + u">"

#------------------------------------------------------------------------------
class FileInfo(AFile):
    """Abstract Mod, Save or BSA File. Features a half baked Backup API."""
    _null_stat = (-1, None, None)

    def _stat_tuple(self): return self.abs_path.size_mtime_ctime()

    def __init__(self, parent_dir, name, load_cache=False):
        self.dir = GPath(parent_dir)
        self.name = GPath(name) # ghost must be lopped off
        self.header = None
        self.masterNames = tuple()
        self.masterOrder = tuple()
        self.madeBackup = False
        #--Ancillary storage
        self.extras = {}
        super(FileInfo, self).__init__(self.dir.join(name), load_cache)

    def _file_changed(self, stat_tuple):
        return (self._file_size, self._file_mod_time, self.ctime) != stat_tuple

    def _reset_cache(self, stat_tuple, load_cache):
        self._file_size, self._file_mod_time, self.ctime = stat_tuple
        if load_cache: self.readHeader()

    def mark_unchanged(self):
        self._reset_cache(self._stat_tuple(), load_cache=False)

    ##: DEPRECATED-------------------------------------------------------------
    def getPath(self): return self.abs_path
    @property
    def mtime(self): return self._file_mod_time
    @property
    def size(self): return self._file_size
    #--------------------------------------------------------------------------
    #--File type tests ##: Belong to ModInfo!
    #--Note that these tests only test extension, not the file data.
    def isMod(self):
        return reModExt.search(self.name.s)
    def isEsm(self):
        if not self.isMod(): return False
        if self.header:
            return int(self.header.flags1) & 1 == 1
        else:
            return bool(_reEsmExt.search(self.name.s)) and False
    def isInvertedMod(self):
        """Extension indicates esp/esm, but byte setting indicates opposite."""
        return (self.isMod() and self.header and
                self.name.cext != (u'.esp',u'.esm')[int(self.header.flags1) & 1])

    def setmtime(self, set_time=0):
        """Sets mtime. Defaults to current value (i.e. reset)."""
        set_time = int(set_time or self.mtime)
        self.abs_path.mtime = set_time
        self._file_mod_time = set_time
        return set_time

    def readHeader(self):
        """Read header from file and set self.header attribute."""
        pass

    def getStatus(self):
        """Returns status of this file -- which depends on status of masters.
        0:  Good
        20, 22: Out of order master
        21, 22: Loads after its masters
        30: Missing master(s)."""
        #--Worst status from masters
        status = 30 if any( # if self.masterNames is empty returns False
            (m not in modInfos) for m in self.masterNames) else 0
        #--Missing files?
        if status == 30:
            return status
        #--Misordered?
        self.masterOrder = tuple(load_order.get_ordered(self.masterNames))
        loads_before_its_masters = self.isMod() and self.masterOrder and \
                                   load_order.cached_lo_index(
            self.masterOrder[-1]) > load_order.cached_lo_index(self.name)
        if self.masterOrder != self.masterNames and loads_before_its_masters:
            return 22
        elif loads_before_its_masters:
            return 21
        elif self.masterOrder != self.masterNames:
            return 20
        else:
            return status

    # Backup stuff - beta, see #292 -------------------------------------------
    def getFileInfos(self):
        """Return one of the FileInfos singletons depending on fileInfo type.
        :rtype: FileInfos"""
        raise AbstractError

    def _doBackup(self,backupDir,forceBackup=False):
        """Creates backup(s) of file, places in backupDir."""
        #--Skip backup?
        if not self in self.getFileInfos().values(): return
        if self.madeBackup and not forceBackup: return
        #--Backup
        self.getFileInfos().copy_info(self.name, backupDir)
        #--First backup
        firstBackup = backupDir.join(self.name) + u'f'
        if not firstBackup.exists():
            self.getFileInfos().copy_info(self.name, backupDir,
                                          firstBackup.tail)

    def tempBackup(self, forceBackup=True):
        """Creates backup(s) of file.  Uses temporary directory to avoid UAC issues."""
        self._doBackup(Path.baseTempDir().join(u'WryeBash_temp_backup'),forceBackup)

    def makeBackup(self, forceBackup=False):
        """Creates backup(s) of file."""
        backupDir = self.backup_dir
        self._doBackup(backupDir,forceBackup)
        #--Done
        self.madeBackup = True

    def backup_paths(self, first=False):
        """Return a list of tuples with backup paths and their restore
        destinations
        :rtype: list[tuple]""" ##: drop tuples use lists !
        return [(self.backup_dir.join(self.name) + (u'f' if first else u''),
                 self.getPath())]

    def revert_backup(self, first=False):
        backup_paths = self.backup_paths(first)
        for tup in backup_paths[1:]: # if cosaves do not exist shellMove fails!
            if not tup[0].exists(): backup_paths.remove(tup)
        env.shellCopy(*zip(*backup_paths))
        # do not change load order for timestamp games - rest works ok
        self.setmtime(self._file_mod_time)
        self.getFileInfos().refreshFile(self.name)

    def getNextSnapshot(self):
        """Returns parameters for next snapshot."""
        destDir = self.snapshot_dir
        destDir.makedirs()
        (root,ext) = self.name.rootExt
        separator = u'-'
        snapLast = [u'00']
        #--Look for old snapshots.
        reSnap = re.compile(u'^'+root.s+u'[ -]([0-9.]*[0-9]+)'+ext+u'$',re.U)
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

    @property
    def backup_dir(self):
        return self.getFileInfos().bash_dir.join(u'Backups')

    @property
    def snapshot_dir(self):
        return self.getFileInfos().bash_dir.join(u'Snapshots')

#------------------------------------------------------------------------------
reReturns = re.compile(u'\r{2,}',re.U)
reBashTags = re.compile(ur'{{ *BASH *:[^}]*}}\s*\n?',re.U)

class ModInfo(FileInfo):
    """An esp/m file."""

    def __init__(self, parent_dir, name, load_cache=False):
        self.isGhost = endsInGhost = (name.cs[-6:] == u'.ghost')
        if endsInGhost: name = GPath(name.s[:-6])
        else: # refreshFile() path
            absPath = GPath(parent_dir).join(name)
            self.isGhost = \
                not absPath.exists() and (absPath + u'.ghost').exists()
        super(ModInfo, self).__init__(parent_dir, name, load_cache)

    def getFileInfos(self): return modInfos

    def setType(self, esm_or_esp):
        """Sets the file's internal type."""
        if esm_or_esp not in (u'esm', u'esp'):
            raise ArgumentError
        with self.getPath().open('r+b') as modFile:
            modFile.seek(8)
            flags1 = MreRecord.flags1_(struct.unpack('I', modFile.read(4))[0])
            flags1.esm = (esm_or_esp == u'esm')
            modFile.seek(8)
            modFile.write(struct.pack('=I',int(flags1)))
        self.header.flags1 = flags1
        self.setmtime()

    def cachedCrc(self, recalculate=False):
        """Stores a cached crc, for quicker execution."""
        path = self.getPath()
        size, mtime = path.size_mtime()
        cached_mtime = modInfos.table.getItem(self.name, 'crc_mtime')
        cached_size = modInfos.table.getItem(self.name, 'crc_size')
        if recalculate or mtime != cached_mtime or size != cached_size:
            path_crc = path.crc
            if path_crc != modInfos.table.getItem(self.name,'crc'):
                modInfos.table.setItem(self.name,'crc',path_crc)
                modInfos.table.setItem(self.name,'ignoreDirty',False)
            modInfos.table.setItem(self.name,'crc_mtime',mtime)
            modInfos.table.setItem(self.name,'crc_size',size)
        else:
            path_crc = modInfos.table.getItem(self.name,'crc')
        return path_crc

    def setmtime(self, set_time=0):
        """Sets mtime. Defaults to current value (i.e. reset)."""
        set_time = FileInfo.setmtime(self, set_time)
        # Prevent re-calculating the File CRC
        modInfos.table.setItem(self.name,'crc_mtime', set_time)

    # Ghosting and ghosting related overrides ---------------------------------
    def needs_update(self):
        self.isGhost, old_ghost = not self._abs_path.exists() and (
            self._abs_path + u'.ghost').exists(), self.isGhost
        # mark updated if ghost state changed but only reread header if needed
        super(ModInfo, self).needs_update() or self.isGhost != old_ghost

    @FileInfo.abs_path.getter
    def abs_path(self):
        """Return joined dir and name, adding .ghost if the file is ghosted."""
        return (self._abs_path + u'.ghost') if self.isGhost else self._abs_path

    def setGhost(self,isGhost):
        """Sets file to/from ghost mode. Returns ghost status at end."""
        normal = self.dir.join(self.name)
        ghost = normal + u'.ghost'
        # Refresh current status - it may have changed due to things like
        # libloadorder automatically unghosting plugins when activating them.
        # Libloadorder only un-ghosts automatically, so if both the normal
        # and ghosted version exist, treat the normal as the real one.
        # Both should never exist simultaneously, Bash will warn in BashBugDump
        if normal.exists(): self.isGhost = False
        elif ghost.exists(): self.isGhost = True
        # Current status == what we want it?
        if isGhost == self.isGhost: return isGhost
        # Current status != what we want, so change it
        try:
            if not normal.editable() or not ghost.editable():
                return self.isGhost
            if isGhost: normal.moveTo(ghost)
            else: ghost.moveTo(normal)
            self.isGhost = isGhost
            # reset cache info as un/ghosting should not make needs_update True
            self.mark_unchanged()
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
        return modInfos.table.getItem(self.name, 'bashTags', set())

    def getBashTagsDesc(self):
        """Returns any Bash flag keys."""
        description = self.header.description or u''
        maBashKeys = re.search(u'{{ *BASH *:([^}]+)}}',description,flags=re.U)
        if not maBashKeys:
            return set()
        else:
            bashTags = maBashKeys.group(1).split(u',')
            return set([str.strip() for str in bashTags]) & allTagsSet - oldTagsSet

    def reloadBashTags(self):
        """Reloads bash tags from mod description and LOOT"""
        tags, removed, _userlist = configHelpers.getTagsInfoCache(self.name)
        tags |= self.getBashTagsDesc()
        tags -= removed
        # Filter and remove old tags
        tags &= allTagsSet
        if tags & oldTagsSet:
            tags -= oldTagsSet
            self.setBashTagsDesc(tags)
        self.setBashTags(tags)

    #--Header Editing ---------------------------------------------------------
    def readHeader(self):
        """Read header from file and set self.header attribute."""
        with ModReader(self.name,self.getPath().open('rb')) as ins:
            try:
                recHeader = ins.unpackRecHeader()
                if recHeader.recType != bush.game.MreHeader.classType:
                    raise ModError(self.name,u'Expected %s, but got %s'
                                   % (bush.game.MreHeader.classType,recHeader.recType))
                self.header = bush.game.MreHeader(recHeader,ins,True)
            except struct.error as rex:
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
                except struct.error as rex:
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

    #--Helpers ----------------------------------------------------------------
    def isBP(self, __bp_authors={u'BASHED PATCH', u'BASHED LISTS'}):
        return self.header.author in __bp_authors ##: drop BASHED LISTS

    def txt_status(self):
        if load_order.cached_is_active(self.name): return _(u'Active')
        elif self.name in modInfos.merged: return _(u'Merged')
        elif self.name in modInfos.imported: return _(u'Imported')
        else: return _(u'Non-Active')

    def hasTimeConflict(self):
        """True if there is another mod with the same mtime."""
        return load_order.has_load_order_conflict(self.name)

    def hasActiveTimeConflict(self):
        """True if has an active mtime conflict with another mod."""
        return load_order.has_load_order_conflict_active(self.name)

    def hasBadMasterNames(self):
        """True if has a master with un unencodable name in cp1252."""
        try:
            for x in self.header.masters: x.s.encode('cp1252')
            return False
        except UnicodeEncodeError:
            return True

    def isExOverLoaded(self):
        """True if belongs to an exclusion group that is overloaded."""
        maExGroup = reExGroup.match(self.name.s)
        if not (load_order.cached_is_active(self.name) and maExGroup):
            return False
        else:
            exGroup = maExGroup.group(1)
            return len(modInfos.exGroup_mods[exGroup]) > 1

    def getBsaPath(self):
        """Returns path to plugin's BSA, if it were to exists."""
        return self.getPath().root.root + u'.' + bush.game.bsa_extension

    def hasBsa(self):
        """Returns True if plugin has an associated BSA."""
        return self.getBsaPath().exists()

    def getIniPath(self):
        """Returns path to plugin's INI, if it were to exists."""
        return self.getPath().root.root + u'.ini' # chops off ghost if ghosted

    def _string_files_paths(self, language):
        sbody, ext = self.name.sbody, self.name.ext
        for join, format_str in bush.game.esp.stringsFiles:
            fname = format_str % {'body': sbody, 'ext': ext,
                                  'language': language}
            assetPath = empty_path.join(*join).join(fname)
            yield assetPath

    def getStringsPaths(self,language=u'English'):
        """If Strings Files are available as loose files, just point to
        those, otherwise extract needed files from BSA if needed."""
        baseDirJoin = self.getPath().head.join
        extract = set()
        paths = set()
        #--Check for Loose Files first
        for filepath in self._string_files_paths(language):
            loose = baseDirJoin(filepath)
            if not loose.exists():
                extract.add(filepath)
            else:
                paths.add(loose)
        #--If there were some missing Loose Files
        if extract:
            bsaPaths = self._extra_bsas()
            bsa_assets = OrderedDict()
            for path in bsaPaths:
                try:
                    bsa_info = bsaInfos[path.tail] # type: BSAInfo
                    found_assets = bsa_info.has_assets(extract)
                except (KeyError, BSAError, OverflowError) as e: # not existing or corrupted
                    if isinstance(e, (BSAError, OverflowError)):
                        deprint(u'Failed to parse %s' % path, traceback=True)
                    continue
                bsa_assets[bsa_info] = found_assets
                #extract contains Paths that compare equal to lowercase strings
                extract -= set(imap(unicode.lower, found_assets))
                if not extract:
                    break
            else: raise ModError(self.name, u"Could not locate Strings Files")
            for bsa, assets in bsa_assets.iteritems():
                out_path = dirs['bsaCache'].join(bsa.name)
                try:
                    bsa.extract_assets(assets, out_path.s)
                except BSAError as e:
                    raise ModError(self.name,
                                   u"Could not extract Strings File from "
                                   u"'%s': %s" % (bsa.name, e))
                paths.update(imap(out_path.join, assets))
        return paths

    def _extra_bsas(self):
        """Return a list of (existing) bsa paths to get assets from.
        :rtype: list[bolt.Path]
        """
        if self.name.cs in bush.game.vanilla_string_bsas: # lowercase !
            bsaPaths = map(dirs['mods'].join, bush.game.vanilla_string_bsas[
                self.name.cs])
        else:
            bsaPaths = [self.getBsaPath()] # first check bsa with same name
            for iniFile in modInfos.ini_files():
                for key in bush.game.resource_archives_keys:
                    extraBsa = iniFile.getSetting(u'Archive', key, u'').split(u',')
                    extraBsa = (x.strip() for x in extraBsa)
                    extraBsa = [dirs['mods'].join(x) for x in extraBsa if x]
                    bsaPaths.extend(extraBsa)
        return bsaPaths

    def isMissingStrings(self, __debug=0):
        """True if the mod says it has .STRINGS files, but the files are
        missing."""
        if not self.header.flags1.hasStrings: return False
        language = oblivionIni.get_ini_language()
        bsaPaths = self._extra_bsas()
        for assetPath in self._string_files_paths(language):
            # Check loose files first
            if self.dir.join(assetPath).exists():
                continue
            # Check in BSA's next
            found = False
            if __debug == 1:
                deprint(u'Scanning BSAs for string files for %s' % self.name)
                __debug = 2
            for path in bsaPaths:
                try:
                    bsa_info = bsaInfos[path.tail] # type: BSAInfo
                    if bsa_info.has_asset(assetPath):
                        found = True
                        break
                except (KeyError, BSAError, OverflowError) as e: # not existing or corrupted
                    if isinstance(e, (BSAError, OverflowError)):
                        print u'Failed to parse %s:\n%s' % (
                            path, traceback.format_exc())
                    elif __debug == 2: deprint(u'%s is not present' % path)
                    continue
                deprint(u'Asset %s not in %s' % (assetPath, path))
            if not found:
                return True
        return False

    def hasResources(self):
        """Returns (hasBsa,hasVoices) booleans according to presence of
        corresponding resources."""
        voicesPath = self.dir.join(u'Sound',u'Voice',self.name)
        return [self.hasBsa(),voicesPath.exists()]

#------------------------------------------------------------------------------
from .ini_files import IniFile, OBSEIniFile, DefaultIniFile, OblivionIni
def get_game_ini(ini_path, is_abs=True):
    """:rtype: OblivionIni | None"""
    for game_ini in gameInis:
        game_ini_path = game_ini.abs_path
        if ini_path == ((is_abs and game_ini_path) or game_ini_path.stail):
            return game_ini
    return None

def BestIniFile(abs_ini_path):
    """:rtype: IniFile"""
    game_ini = get_game_ini(abs_ini_path)
    if game_ini:
        return game_ini
    INICount = IniFile.formatMatch(abs_ini_path)
    OBSECount = OBSEIniFile.formatMatch(abs_ini_path)
    if INICount >= OBSECount:
        return IniFile(abs_ini_path)
    else:
        return OBSEIniFile(abs_ini_path)

#------------------------------------------------------------------------------
class INIInfo(IniFile):
    """Ini info, adding cached status and functionality to the ini files."""
    _status = None

    def _reset_cache(self, stat_tuple, load_cache):
        super(INIInfo, self)._reset_cache(stat_tuple, load_cache)
        if load_cache: self._status = None

    @property
    def tweak_status(self):
        if self._status is None: self.getStatus()
        return self._status

    @property
    def is_default_tweak(self): return False

    def _incompatible(self, other):
        if not isinstance(self, OBSEIniFile):
            return isinstance(other, OBSEIniFile)
        return not isinstance(other, OBSEIniFile)

    def is_applicable(self, stat=None):
        stat = stat or self.tweak_status
        return stat != -20 and (
            bass.settings['bash.ini.allowNewLines'] or stat != -10)

    def getStatus(self, target_ini=None):
        """Returns status of the ini tweak:
        20: installed (green with check)
        15: mismatches (green with dot) - mismatches are with another tweak from same installer that is applied
        10: mismatches (yellow)
        0: not installed (green)
        -10: tweak file contains new sections/settings
        -20: incompatible tweak file (red)
        Also caches the value in self._status"""
        infos = iniInfos
        target_ini = target_ini or infos.ini
        tweak_settings = self.getSettings()
        def _status(s):
            self._status = s
            return s
        if self._incompatible(target_ini) or not tweak_settings:
            return _status(-20)
        match = False
        mismatch = 0
        ini_settings = target_ini.getSettings()
        self_installer = infos.table.getItem(self.abs_path.tail, 'installer')
        for section_key in tweak_settings:
            if section_key not in ini_settings:
                return _status(-10)
            target_section = ini_settings[section_key]
            tweak_section = tweak_settings[section_key]
            for item in tweak_section:
                if item not in target_section:
                    return _status(-10)
                if tweak_section[item][0] != target_section[item][0]:
                    if mismatch < 2:
                        # Check to see if the mismatch is from another ini
                        # tweak that is applied, and from the same installer
                        mismatch = 2
                        if self_installer is None: continue
                        for name, ini_info in infos.iteritems():
                            if self is ini_info: continue
                            if self_installer != infos.table.getItem(
                                    name, 'installer'): continue
                            # It's from the same installer
                            if self._incompatible(ini_info): continue
                            value = ini_info.getSetting(section_key, item, None)
                            if value == target_section[item][0]:
                                # The other tweak has the setting we're worried about
                                mismatch = 1
                                break
                else:
                    match = True
        if not match:
            return _status(0)
        elif not mismatch:
            return _status(20)
        elif mismatch == 1:
            return _status(15)
        elif mismatch == 2:
            return _status(10)

    def reset_status(self): self._status = None

    def listErrors(self):
        """Returns ini tweak errors as text."""
        ini_infos_ini = iniInfos.ini
        text = [u'%s:' % self.abs_path.stail]
        if self._incompatible(ini_infos_ini):
            text.append(u' ' + _(u'Format mismatch:'))
            if isinstance(self, OBSEIniFile):
                text.append(u'  '+ _(u'Target format: INI') +
                            u'\n  ' + _(u'Tweak format: Batch Script'))
            else:
                text.append(u'  ' + _(u'Target format: Batch Script') +
                            u'\n  ' + _(u'Tweak format: INI'))
        else:
            tweak_settings = self.getSettings()
            ini_settings = ini_infos_ini.getSettings()
            if len(tweak_settings) == 0:
                if not isinstance(self, OBSEIniFile):
                    text.append(_(u' No valid INI format lines.'))
                else:
                    text.append(_(u' No valid Batch Script format lines.'))
            else:
                missing_settings = []
                for key in tweak_settings:
                    if key not in ini_settings:
                        text.append(u' [%s] - %s' % (key,_(u'Invalid Header')))
                    else:
                        for item in tweak_settings[key]:
                            if item not in ini_settings[key]:
                                missing_settings.append(
                                    u'  [%s] %s' % (key, item))
                if missing_settings:
                    text.append(u' ' + _(u'Settings missing from target ini:'))
                    text.extend(missing_settings)
        if len(text) == 1:
            text.append(u' None')
        with sio() as out:
            log = bolt.LogFile(out)
            for line in text:
                log(line)
            return bolt.winNewLines(log.out.getvalue())

#------------------------------------------------------------------------------
from .save_files import get_save_header_type, SaveHeaderError
class SaveInfo(FileInfo):
    def getFileInfos(self): return saveInfos

    def getStatus(self):
        status = FileInfo.getStatus(self)
        masterOrder = self.masterOrder
        #--File size?
        if status > 0 or len(masterOrder) > len(load_order.cached_active_tuple()):
            return status
        #--Current ordering?
        if masterOrder != load_order.cached_active_tuple()[:len(masterOrder)]:
            return status
        elif masterOrder == load_order.cached_active_tuple():
            return -20
        else:
            return -10

    def readHeader(self):
        """Read header from file and set self.header attribute."""
        try:
            self.header = get_save_header_type(bush.game.fsName)(self.abs_path)
            #--Master Names/Order
            self.masterNames = tuple(self.header.masters)
            self.masterOrder = tuple() #--Reset to empty for now
        except SaveHeaderError as e:
            raise SaveFileError, (self.name, e.message), sys.exc_info()[2]

    def write_masters(self):
        """Rewrites masters of existing save file."""
        if not self.abs_path.exists():
            raise SaveFileError(self.abs_path.head, u'File does not exist.')
        with self.abs_path.open('rb') as ins:
            with self.abs_path.temp.open('wb') as out:
                oldMasters = self.header.writeMasters(ins, out)
        oldMasters = [GPath(decode(x)) for x in oldMasters]
        self.abs_path.untemp()
        #--Cosaves
        masterMap = dict(
            (x, y) for x, y in zip(oldMasters, self.header.masters) if x != y)
        #--Pluggy file?
        pluggyPath = CoSaves.getPaths(self.abs_path)[0]
        if masterMap and pluggyPath.exists():
            pluggy = PluggyFile(pluggyPath)
            pluggy.load()
            pluggy.mapMasters(masterMap)
            pluggy.safeSave()
        #--OBSE/SKSE file?
        obsePath = CoSaves.getPaths(self.abs_path)[1]
        if masterMap and obsePath.exists():
            obse = ObseFile(obsePath)
            obse.load()
            obse.mapMasters(masterMap)
            obse.safeSave()

    def coSaves(self):
        """Returns CoSaves instance corresponding to self."""
        return CoSaves(self.getPath())

    def backup_paths(self, first=False):
        save_paths = super(SaveInfo, self).backup_paths(first)
        save_paths.extend(CoSaves.get_new_paths(*save_paths[0]))
        return save_paths

#------------------------------------------------------------------------------
from . import bsa_files
from .bsa_files import BSAError

try:
    _bsa_type = bsa_files.get_bsa_type(bush.game.fsName)
except AttributeError:
    _bsa_type = bsa_files.ABsa

class BSAInfo(FileInfo, _bsa_type):
    _default_mtime = time.mktime(
        time.strptime(u'01-01-2006 00:00:00', u'%m-%d-%Y %H:%M:%S'))

    def __init__(self, parent_dir, bsa_name, load_cache=False):
        try: # Never load_cache for memory reasons - let it be loaded as needed
            super(BSAInfo, self).__init__(parent_dir, bsa_name,
                                          load_cache=False)
        except BSAError as e:
            raise FileError, (GPath(bsa_name),
                e.__class__.__name__ + u' ' + e.message), sys.exc_info()[2]
        self._reset_bsa_mtime()

    def getFileInfos(self): return bsaInfos

    def needs_update(self):
        changed = super(BSAInfo, self).needs_update()
        self._reset_bsa_mtime()
        return changed

    def readHeader(self): # just reset the cache
        self._assets = self.__class__._assets

    def _reset_bsa_mtime(self):
        if bush.game.allow_reset_bsa_timestamps and inisettings[
            'ResetBSATimestamps']:
            if self._file_mod_time != self._default_mtime:
                self.setmtime(self._default_mtime)

    def is_bsa_active(self):
        """Return True if corresponding mod is active."""
        is_act = load_order.cached_is_active
        return is_act(self.name.root + '.esm') or is_act(self.name.root + '.esp')

    def active_bsa_index(self):
        """Return the index of the active bsa (the corresponding mod's
        index) or raise ValueError if the bsa is not active."""
        active_index = load_order.cached_active_tuple().index
        try:
            return active_index(self.name.root + '.esm')
        except ValueError:
            return active_index(self.name.root + '.esp')

#------------------------------------------------------------------------------
class DataStore(DataDict):
    store_dir = empty_path # where the datas sit, static except for SaveInfos

    def delete(self, delete_keys, **kwargs):
        """Deletes member file(s)."""
        full_delete_paths, delete_info = self.files_to_delete(delete_keys,
            raise_on_master_deletion=kwargs.pop(
                'raise_on_master_deletion', True))
        try:
            self._delete_operation(full_delete_paths, delete_info, **kwargs)
        finally:
            #--Refresh
            if kwargs.pop('doRefresh', True):
                self.delete_refresh(full_delete_paths, delete_info,
                                    check_existence=True)

    def files_to_delete(self, filenames, **kwargs):
        raise AbstractError

    def _delete_operation(self, paths, delete_info, **kwargs):
        confirm = kwargs.pop('confirm', False)
        recycle = kwargs.pop('recycle', True)
        env.shellDelete(paths, confirm=confirm, recycle=recycle)

    def delete_refresh(self, deleted, deleted2, check_existence):
        raise AbstractError

    def refresh(self): raise AbstractError
    def save(self): pass # for Screenshots
    # Renaming
    def rename_info(self, oldName, newName):
        try:
            return self._rename_operation(oldName, newName)
        except (CancelError, OSError, IOError):
            deprint(u'Renaming %s to %s failed' % (oldName, newName),
                    traceback=True)
            # When using moveTo I would get "WindowsError:[Error 32]The process
            # cannot access ..." -  the code below was reverting the changes.
            # With shellMove I mostly get CancelError so below not needed -
            # except if a save is locked and user presses Skip - so cosaves are
            # renamed! Error handling is still a WIP
            for old, new in self._get_rename_paths(oldName, newName):
                if new.exists() and not old.exists():
                    # some cosave move failed, restore files
                    new.moveTo(old)
                if new.exists() and old.exists():
                    # move copies then deletes, so the delete part failed
                    new.remove()
            raise

    def _rename_operation(self, oldName, newName):
        rename_paths = self._get_rename_paths(oldName, newName)
        for tup in rename_paths[1:]: # if cosaves do not exist shellMove fails!
            if not tup[0].exists(): rename_paths.remove(tup)
        env.shellMove(*zip(*rename_paths))

    def _get_rename_paths(self, oldName, newName):
        return [tuple(map(self.store_dir.join, (oldName, newName)))]

    @property
    def bash_dir(self):
        """Return the folder where Bash persists its data - create it on init!
        :rtype: bolt.Path"""
        raise AbstractError

    @property
    def hidden_dir(self):
        """Return the folder where Bash should move the file info to hide it
        :rtype: bolt.Path"""
        return self.bash_dir.join(u'Hidden')

    def get_hide_dir(self, name): return self.hidden_dir

    def move_infos(self, sources, destinations, window):
        # hasty hack for Files_Unhide, must absorb move_info
        try:
            env.shellMove(sources, destinations, parent=window)
        except (CancelError, SkipError):
            pass
        return set(d.tail for d in destinations if d.exists())

class TableFileInfos(DataStore):
    _notify_bain_on_delete = True
    file_pattern = None # subclasses must define this !

    def _initDB(self, dir_):
        self.store_dir = dir_ #--Path
        self.store_dir.makedirs()
        self.bash_dir.makedirs() # self.store_dir may need be set
        self.data = {} # populated in refresh ()
        # the type of the table keys is always bolt.Path
        self.table = bolt.Table(
            bolt.PickleDict(self.bash_dir.join(u'Table.dat')))

    def __init__(self, dir_, factory=AFile):
        """Init with specified directory and specified factory type."""
        self.factory=factory
        self._initDB(dir_)

    def refreshFile(self,fileName):
        self[fileName] = self.factory(self.store_dir, fileName)

    def _names(self): # performance intensive
        return {x for x in self.store_dir.list() if
                self.store_dir.join(x).isfile() and self.rightFileType(x)}

    #--Right File Type?
    @classmethod
    def rightFileType(cls, fileName):
        """Check if the filetype (extension) is correct for subclass.
        :type fileName: bolt.Path | basestring
        :rtype: _sre.SRE_Match | None
        """
        return cls.file_pattern.search(u'%s' % fileName)

    #--Delete
    def files_to_delete(self, fileNames, **kwargs):
        toDelete = []
        #--Cache table updates
        tableUpdate = {}
        #--Go through each file
        for fileName in fileNames:
            try:
                fileInfo = self[fileName]
            except KeyError: # corrupted
                fileInfo = self.factory(self.store_dir, fileName)
            #--File
            filePath = fileInfo.abs_path
            toDelete.append(filePath)
            self._additional_deletes(fileInfo, toDelete)
            #--Table
            tableUpdate[filePath] = fileName
        #--Now do actual deletions
        toDelete = [x for x in toDelete if x.exists()]
        return toDelete, tableUpdate

    def _update_deleted_paths(self, deleted_keys, paths_to_keys,
                              check_existence):
        """Must be called BEFORE we remove the keys from self."""
        if paths_to_keys is None: # we passed the keys in, get the paths
            paths_to_keys = {self[n].abs_path: n for n in deleted_keys}
        if check_existence:
            for filePath in paths_to_keys.keys():
                if filePath.exists():
                    del paths_to_keys[filePath] # item was not deleted
        if self.__class__._notify_bain_on_delete:
            from .bain import InstallersData
            for d in paths_to_keys: # we need absolute paths
                InstallersData.track(d)
        return paths_to_keys.values()

    def _additional_deletes(self, fileInfo, toDelete): pass

    def save(self):
        # items deleted outside Bash
        for deleted in set(self.table.keys()) - set(self.keys()):
            del self.table[deleted]
        self.table.save()

class FileInfos(TableFileInfos):
    """Common superclass for mod, saves and bsa infos."""

    def _initDB(self, dir_):
        super(FileInfos, self)._initDB(dir_)
        self.corrupted = {} #--errorMessage = corrupted[fileName]

    #--Refresh File
    def refreshFile(self, fileName, _in_refresh=False): # YAK - tmp _in_refresh
        try:
            fileInfo = self.factory(self.store_dir, fileName, load_cache=True)
            self[fileName] = fileInfo
            self.corrupted.pop(fileName, None)
        except FileError as error:
            if not _in_refresh: # if refresh just raise so we print the error
                self.corrupted[fileName] = error.message
                self.pop(fileName, None)
            raise

    #--Refresh
    def refresh(self, refresh_infos=True):
        """Refresh from file directory."""
        oldNames = set(self.data) | set(self.corrupted)
        _added = set()
        _updated = set()
        newNames = self._names()
        for name in newNames: #--Might have '.ghost' lopped off.
            oldInfo = self.get(name) # None if name was in corrupted or new one
            try:
                if oldInfo is not None:
                    if oldInfo.needs_update(): # will reread the header
                        _updated.add(name)
                else: # added or known corrupted, get a new info
                    self.refreshFile(name, _in_refresh=True)
                    _added.add(name)
            except FileError as e: # old still corrupted, or new(ly) corrupted
                if not name in self.corrupted \
                        or self.corrupted[name] != e.message:
                    deprint(u'Failed to load %s: %s' % (name, e.message)) #, traceback=True)
                    self.corrupted[name] = e.message
                self.pop(name, None)
        _deleted = oldNames - newNames
        self.delete_refresh(_deleted, None, check_existence=False,
                            _in_refresh=True)
        change = bool(_added) or bool(_updated) or bool(_deleted)
        if not change: return change
        return _added, _updated, _deleted

    def delete_refresh(self, deleted_keys, paths_to_keys, check_existence,
                       _in_refresh=False):
        """Special case for the saves, inis, mods and bsas.
        :param deleted_keys: must be the data store keys and not full paths
        :param paths_to_keys: a dict mapping full paths to the keys
        """
        #--Table
        deleted = self._update_deleted_paths(deleted_keys, paths_to_keys,
                                             check_existence)
        if not deleted: return deleted
        for name in deleted:
            self.pop(name, None); self.corrupted.pop(name, None)
            self.table.pop(name, None)
        return deleted

    def _get_rename_paths(self, oldName, newName): # FIXME(ut): rename backups
        return [(self[oldName].getPath(), self.store_dir.join(newName))]

    def _additional_deletes(self, fileInfo, toDelete):
        #--Backups
        for backPath, __path in fileInfo.backup_paths():
            toDelete.extend([backPath, backPath + u'f'])

    #--Rename
    def _rename_operation(self, oldName, newName):
        """Renames member file from oldName to newName."""
        #--Update references
        fileInfo = self[oldName]
        #--File system
        super(FileInfos, self)._rename_operation(oldName, newName)
        #--FileInfo
        fileInfo.name = newName
        fileInfo.abs_path = self.store_dir.join(newName)
        #--FileInfos
        self[newName] = self[oldName]
        del self[oldName]
        self.table.moveRow(oldName,newName)
        # self[newName].mark_unchanged() # not needed with shellMove !
        #--Done
        fileInfo.madeBackup = False ##: #292 - backups are left behind

    #--Move
    def move_info(self, fileName, destDir):
        """Moves member file to destDir. Will overwrite! The client is
        responsible for calling delete_refresh of the data store."""
        destDir.makedirs()
        srcPath = self[fileName].getPath()
        destPath = destDir.join(fileName)
        srcPath.moveTo(destPath)

    #--Copy
    def copy_info(self, fileName, destDir, destName=empty_path, set_mtime=None):
        """Copies member file to destDir. Will overwrite! Will update
        internal self.data for the file if copied inside self.dir but the
        client is responsible for calling the final refresh of the data store.
        See usages.

        :param set_mtime: if None self[fileName].mtime is copied to destination
        """
        destDir.makedirs()
        if not destName: destName = fileName
        srcPath = self[fileName].getPath()
        if destDir == self.store_dir and destName in self.data:
            destPath = self[destName].getPath()
        else:
            destPath = destDir.join(destName)
        srcPath.copyTo(destPath) # will set destPath.mtime to the srcPath one
        if destDir == self.store_dir:
            self.refreshFile(destName)
            self.table.copyRow(fileName, destName)
            if set_mtime is not None:
                if set_mtime == '+1':
                    set_mtime = srcPath.mtime + 1
                self[destName].setmtime(set_mtime) # correctly update table
        return set_mtime

#------------------------------------------------------------------------------
class ObseIniInfo(OBSEIniFile, INIInfo): pass

class DefaultIniInfo(DefaultIniFile, INIInfo):

    @property
    def is_default_tweak(self): return True

def ini_info_factory(parent_dir, filename):
    """:rtype: INIInfo"""
    fullpath = GPath(parent_dir).join(filename)
    INICount = IniFile.formatMatch(fullpath)
    OBSECount = OBSEIniFile.formatMatch(fullpath)
    if INICount >= OBSECount:
        return INIInfo(fullpath)
    else:
        return ObseIniInfo(fullpath)

class INIInfos(TableFileInfos):
    """:type _ini: IniFile
    :type data: dict[bolt.Path, IniInfo]"""
    file_pattern = re.compile(ur'\.ini$', re.I | re.U)
    try:
        _default_tweaks = dict((GPath(k), DefaultIniInfo(k, v)) for k, v in
                               bush.game.default_tweaks.iteritems())
    except AttributeError:
        _default_tweaks = {}

    def __init__(self):
        super(INIInfos, self).__init__(dirs['tweaks'], ini_info_factory)
        self._ini = None
        # Check the list of target INIs, remove any that don't exist
        # if _target_inis is not an OrderedDict choice won't be set correctly
        _target_inis = settings['bash.ini.choices'] # type: OrderedDict
        choice = settings['bash.ini.choice'] # type: int
        if isinstance(_target_inis, OrderedDict):
            try:
                previous_ini = _target_inis.keys()[choice]
            except IndexError:
                choice, previous_ini = -1, None
        else: # not an OrderedDict, updating from 306
            choice, previous_ini = -1, None
        for ini_name in _target_inis.keys():
            if ini_name == _(u'Browse...'): continue
            ini_path = _target_inis[ini_name]
            # If user started with non-translated, 'Browse...'
            # will still be in here, but in English.  It wont get picked
            # up by the previous check, so we'll just delete any non-Path
            # objects.  That will take care of it.
            if not isinstance(ini_path,bolt.Path) or not ini_path.isfile():
                if get_game_ini(ini_path):
                    continue # don't remove game inis even if missing
                del _target_inis[ini_name]
                if ini_name is previous_ini:
                    choice, previous_ini = -1, None
        csChoices = set(x.lower() for x in _target_inis)
        for iFile in gameInis: # add the game inis even if missing
            if iFile.abs_path.tail.cs not in csChoices:
                _target_inis[iFile.abs_path.stail] = iFile.abs_path
        if _(u'Browse...') not in _target_inis:
            _target_inis[_(u'Browse...')] = None
        self.__sort_target_inis()
        if previous_ini:
            choice = bass.settings['bash.ini.choices'].keys().index(
                previous_ini)
        settings['bash.ini.choice'] = choice if choice >= 0 else 0
        self.ini = bass.settings['bash.ini.choices'].values()[
            settings['bash.ini.choice']]

    @property
    def ini(self):
        return self._ini
    @ini.setter
    def ini(self, ini_path):
        """:type ini_path: bolt.Path"""
        if self._ini is not None and self._ini.abs_path == ini_path:
            return # nothing to do
        self._ini = BestIniFile(ini_path)
        for ini_info in self.itervalues(): ini_info.reset_status()

    @staticmethod
    def update_targets(targets_dict):
        """Update 'bash.ini.choices' with targets_dict then re-sort the dict
        of target INIs"""
        for existing_ini in bass.settings['bash.ini.choices']:
            targets_dict.pop(existing_ini, None)
        if targets_dict:
            bass.settings['bash.ini.choices'].update(targets_dict)
            # now resort
            INIInfos.__sort_target_inis()
        return targets_dict

    @staticmethod
    def __sort_target_inis():
        keys = bass.settings['bash.ini.choices'].keys()
        # Sort alphabetically
        keys.sort()
        # Sort Oblivion.ini to the top, and 'Browse...' to the bottom
        game_inis = bush.game.iniFiles
        len_inis = len(game_inis)
        keys.sort(key=lambda a: game_inis.index(a) if a in game_inis else (
                      len_inis + 1 if a == _(u'Browse...') else len_inis))
        bass.settings['bash.ini.choices'] = collections.OrderedDict(
            [(k, bass.settings['bash.ini.choices'][k]) for k in keys])

    def _refresh_infos(self):
        """Refresh from file directory."""
        oldNames=set(n for n, v in self.iteritems() if not v.is_default_tweak)
        _added = set()
        _updated = set()
        newNames = self._names()
        for name in newNames:
            oldInfo = self.get(name) # None if name was added
            if oldInfo is not None and not oldInfo.is_default_tweak:
                if oldInfo.needs_update(): _updated.add(name)
            else: # added
                oldInfo = self.factory(self.store_dir, name)
                _added.add(name)
            self[name] = oldInfo
        _deleted = oldNames - newNames
        self.delete_refresh(_deleted, None, check_existence=False,
                            _in_refresh=True)
        # re-add default tweaks
        for k in self.keys():
            if k not in newNames: del self[k]
        set_keys = set(self.keys())
        for k, d in self._default_tweaks.iteritems():
            if k not in set_keys:
                default_info = self.setdefault(k, d) # type: DefaultIniInfo
                if k in _deleted: # we restore default over copy
                    _updated.add(k)
                    default_info.reset_status()
        return _added, _deleted, _updated

    def refresh(self, refresh_infos=True, refresh_target=True):
        _added = _deleted = _updated = set()
        if refresh_infos:
            _added, _deleted, _updated = self._refresh_infos()
        changed = refresh_target and (
            self.ini.updated or self.ini.needs_update())
        if changed: # reset the status of all infos and let RefreshUI set it
            self.ini.updated = False
            for ini_info in self.itervalues(): ini_info.reset_status()
        change = bool(_added) or bool(_updated) or bool(_deleted) or changed
        if not change: return change
        return _added, _updated, _deleted, changed

    @property
    def bash_dir(self): return dirs['modsBash'].join(u'INI Data')

    def delete_refresh(self, deleted_keys, paths_to_keys, check_existence,
                       _in_refresh=False):
        deleted = self._update_deleted_paths(deleted_keys, paths_to_keys,
                                             check_existence)
        if not deleted: return deleted
        for name in deleted:
            self.pop(name, None)
            self.table.delRow(name)
        set_keys = set(self.keys())
        if not _in_refresh: # readd default tweaks
            for k, d in self._default_tweaks.iteritems():
                if k not in set_keys:
                    default_info = self.setdefault(k, d) # type: DefaultIniInfo
                    default_info.reset_status()
        return deleted

    def get_tweak_lines_infos(self, tweakPath):
        tweak_lines = self[tweakPath].read_ini_lines()
        return self._ini.get_lines_infos(tweak_lines)

    def open_or_copy(self, tweak):
        info = self[tweak] # type: INIInfo
        if info.is_default_tweak:
            self._copy_to_new_tweak(info, tweak)
            self[tweak] = self.factory(self.store_dir, tweak)
            return True # refresh
        else:
            info.abs_path.start()
            return False

    def _copy_to_new_tweak(self, info, new_tweak): ##: encoding....
        with open(self.store_dir.join(new_tweak).s, 'w') as ini_file:
            # writelines does not do what you'd expect, would concatenate lines
            ini_file.write('\n'.join(info.read_ini_lines()))

    def duplicate_ini(self, tweak, new_tweak):
        """Duplicate tweak into new_tweak, copying current target settings"""
        if not new_tweak: return False
        # new_tweak is an abs path, join works ok relative to self.store_dir
        self._copy_to_new_tweak(self[tweak], new_tweak)
        new_info = self[new_tweak.tail] = self.factory(self.store_dir,
                                                       new_tweak)
        # Now edit it with the values from the target INI
        new_tweak_settings = copy.copy(new_info.getSettings())
        target_settings = self.ini.getSettings()
        for section in new_tweak_settings:
            if section in target_settings:
                for setting in new_tweak_settings[section]:
                    if setting in target_settings[section]:
                        new_tweak_settings[section][setting] = \
                            target_settings[section][setting]
        for k,v in new_tweak_settings.items(): # drop line numbers
            new_tweak_settings[k] = dict(
                (sett, val[0]) for sett, val in v.iteritems())
        new_info.saveSettings(new_tweak_settings)
        return True

def _lo_cache(lord_func):
    """Decorator to make sure I sync modInfos cache with load_order cache
    whenever I change (or attempt to change) the latter, and that I do
    refresh modInfos."""
    @wraps(lord_func)
    def _modinfos_cache_wrapper(self, *args, **kwargs):
        """Sync the ModInfos load order and active caches and refresh for
        load order or active changes.

        :type self: ModInfos
        :return: 1 if only load order changed, 2 if only active changed,
        3 if both changed else 0
        """
        try:
            old_lo, old_active = load_order.cached_lord.loadOrder, \
                                 load_order.cached_lord.activeOrdered
            lord_func(self, *args, **kwargs)
            lo, active = load_order.cached_lord.loadOrder, \
                         load_order.cached_lord.activeOrdered
            lo_changed = lo != old_lo
            active_changed = active != old_active
            active_set_changed = active_changed and (
                set(active) != set(old_active))
            if active_changed:
                self._refresh_mod_inis() # before _refreshMissingStrings !
                self._refreshBadNames()
                self._refreshInfoLists()
                self._refreshMissingStrings()
            #if lo changed (including additions/removals) let refresh handle it
            if active_set_changed or (set(lo) - set(old_lo)): # new mods, ghost
                self.autoGhost(force=False)
            new_active = set(active) - set(old_active)
            for neu in new_active: # new active mods, unghost
                self[neu].setGhost(False)
            return (lo_changed and 1) + (active_changed and 2)
        finally:
            self._lo_wip, self._active_wip = list(
                load_order.cached_lord.loadOrder), list(
                load_order.cached_lord.activeOrdered)
    return _modinfos_cache_wrapper

#------------------------------------------------------------------------------
class ModInfos(FileInfos):
    """Collection of modinfos. Represents mods in the Oblivion\Data directory."""
    file_pattern = reModExt

    def __init__(self):
        FileInfos.__init__(self, dirs['mods'], ModInfo)
        #--Info lists/sets
        self.mergeScanned = [] #--Files that have been scanned for mergeability.
        self.bashed_patches = set()
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
        self.size_voVersion = {y:x for x, y in self.version_voSize.iteritems()}
        self.voCurrent = None
        self.voAvailable = set()
        # removed/extra mods in plugins.txt - set in load_order.py,
        # used in RefreshData
        self.selectedBad = set()
        self.selectedExtra = []
        load_order.initialize_load_order_handle(self)
        # Load order caches to manipulate, then call our save methods - avoid !
        self._active_wip = []
        self._lo_wip = []

    # Load order API for the rest of Bash to use - if load order or active
    # changed methods run a refresh on modInfos data
    @_lo_cache
    def refreshLoadOrder(self, forceRefresh=False, forceActive=False):
        load_order.get_lo(cached=not forceRefresh, cached_active=not forceActive)

    @_lo_cache
    def cached_lo_save_active(self, active=None):
        """Write data to Plugins.txt file.

        Always call AFTER setting the load order - make sure we unghost
        ourselves so ctime of the unghosted mods is not set."""
        load_order.save_lo(load_order.cached_lord.loadOrder,
                           load_order.cached_lord.lorder(
                        active if active is not None else self._active_wip))

    @_lo_cache
    def cached_lo_save_lo(self):
        """Save load order when active did not change."""
        load_order.save_lo(self._lo_wip)

    @_lo_cache
    def cached_lo_save_all(self):
        """Save load order and plugins.txt"""
        dex = {x: i for i, x in enumerate(self._lo_wip) if
               x in set(self._active_wip)}
        self._active_wip.sort(key=dex.__getitem__) # order in their load order
        load_order.save_lo(self._lo_wip, acti=self._active_wip)

    @_lo_cache
    def undo_load_order(self): load_order.undo_load_order()

    @_lo_cache
    def redo_load_order(self): load_order.redo_load_order()

    #--Load Order utility methods - be sure cache is valid when using them
    def cached_lo_insert_after(self, previous, new_mod):
        previous_index = self._lo_wip.index(previous)
        if not load_order.using_txt_file():
            # set the mtime to avoid reordering all subsequent mods
            try:
                next_mod = self._lo_wip[previous_index + 1]
            except IndexError: # last mod
                next_mod = None
            end_time = self[next_mod].mtime if next_mod else None
            start_time  = self[previous].mtime
            if end_time is not None and \
                    end_time <= start_time: # can happen on esm/esp boundary
                start_time = end_time - 60
            set_time = load_order.get_free_time(start_time, end_time=end_time)
            self[new_mod].setmtime(set_time)
        self._lo_wip[previous_index + 1:previous_index + 1] = [new_mod]

    def cached_lo_last_esm(self):
        esm = self.masterName
        for mod in self._lo_wip[1:]:
            if not self[mod].isEsm(): return esm
            esm = mod
        return esm

    def cached_lo_insert_at(self, first, modlist):
        # hasty method for Mod_OrderByName
        mod_set = set(modlist)
        first_dex = self._lo_wip.index(first)
        rest = self._lo_wip[first_dex:]
        del self._lo_wip[first_dex:]
        for mod in rest:
            if mod in mod_set: continue
            self._lo_wip.append(mod)
        self._lo_wip[first_dex:first_dex] = modlist

    @staticmethod
    def hexIndexString(mod):
        return u'%02X' % (load_order.cached_active_index(mod),) \
            if load_order.cached_is_active(mod) else u''

    def masterWithVersion(self, master_name):
        if master_name == u'Oblivion.esm' and self.voCurrent:
            master_name += u' [' + self.voCurrent + u']'
        return master_name

    def dropItems(self, dropItem, firstItem, lastItem): # MUTATES plugins CACHE
        # Calculating indexes through order.index() cause we may be called in
        # a row before saving the modified load order
        order = self._lo_wip
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

    @property
    def bash_dir(self): return dirs['modsBash']

    #--Refresh-----------------------------------------------------------------
    def _names(self):
        names = super(ModInfos, self)._names()
        unghosted_names = set()
        for name in sorted(names, key=lambda x: x.cext == u'.ghost'):
            if name.cs[-6:] == u'.ghost': name = GPath(name.s[:-6])
            if name in unghosted_names:
                deprint(u'Both %s and its ghost exist. The ghost will be '
                        u'ignored but this may lead to undefined behavior - '
                        u'please remove one or the other' % name)
            else: unghosted_names.add(name)
        return unghosted_names

    def refresh(self, refresh_infos=True, _modTimesChange=False):
        """Update file data for additions, removals and date changes.

        See usages for how to use the refresh_infos and _modTimesChange params.
        _modTimesChange is not strictly needed after the lo rewrite,
        as get_lo will always recalculate it - kept to help track places in
        the code where timestamp load order may change.
         NB: if an operation we performed changed the load order we do not want
         lock load order to revert our own operation. So either call some of
         the set_load_order methods, or guard refresh (which only *gets* load
         order) with load_order.Unlock.
        """
        hasChanged = deleted = False
        # Scan the data dir, getting info on added, deleted and modified files
        if refresh_infos:
            change = FileInfos.refresh(self)
            if change: _added, _updated, deleted = change
            hasChanged = bool(change)
        # If refresh_infos is False and mods are added _do_ manually refresh
        _modTimesChange = _modTimesChange and not load_order.using_txt_file()
        lo_changed = self.refreshLoadOrder(
            forceRefresh=hasChanged or _modTimesChange, forceActive=deleted)
        self.reloadBashTags()
        # if active did not change, we must perform the refreshes below
        if lo_changed < 2: # in case ini files were deleted or modified
            self._refresh_mod_inis()
        if lo_changed < 2 and hasChanged:
            self._refreshBadNames()
            self._refreshInfoLists()
        elif lo_changed < 2: # maybe string files were deleted...
            #we need a load order below: in skyrim we read inis in active order
            hasChanged += self._refreshMissingStrings()
        self._setOblivionVersions()
        oldMergeable = set(self.mergeable)
        scanList = self._refreshMergeable()
        difMergeable = (oldMergeable ^ self.mergeable) & set(self.keys())
        if scanList:
            self.rescanMergeable(scanList)
        hasChanged += bool(scanList or difMergeable)
        return bool(hasChanged) or lo_changed

    _plugin_inis = OrderedDict() # cache active mod inis in active mods order
    def _refresh_mod_inis(self):
        if not bush.game.supports_mod_inis: return
        iniPaths = (self[m].getIniPath() for m in load_order.cached_active_tuple())
        iniPaths = [p for p in iniPaths if p.isfile()]
        # delete non existent inis from cache
        for key in self._plugin_inis.keys():
            if key not in iniPaths:
                del self._plugin_inis[key]
        # update cache with new or modified files
        for iniPath in iniPaths:
            if iniPath not in self._plugin_inis or self._plugin_inis[
                iniPath].needs_update():
                self._plugin_inis[iniPath] = IniFile(iniPath)
        self._plugin_inis = OrderedDict(
            [(k, self._plugin_inis[k]) for k in iniPaths])

    def _refreshBadNames(self):
        """Refreshes which filenames cannot be saved to plugins.txt
        It seems that Skyrim and Oblivion read plugins.txt as a cp1252
        encoded file, and any filename that doesn't decode to cp1252 will
        be skipped."""
        bad = self.bad_names = set()
        activeBad = self.activeBad = set()
        for fileName in self.data:
            if self.isBadFileName(fileName.s):
                if load_order.cached_is_active(fileName):
                    ## For now, we'll leave them active, until
                    ## we finish testing what the game will support
                    #self.lo_deactivate(fileName)
                    activeBad.add(fileName)
                else:
                    bad.add(fileName)
        return bool(activeBad)

    def _refreshMissingStrings(self):
        """Refreshes which mods are supposed to have strings files, but are
        missing them (=CTD). For Skyrim you need to have a valid load order."""
        oldBad = self.missing_strings
        self.missing_strings = set(
            k for k, v in self.iteritems() if v.isMissingStrings())
        self.new_missing_strings = self.missing_strings - oldBad
        return bool(self.new_missing_strings)

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
                modGhost = toGhost and not load_order.cached_is_active(mod) \
                           and allowGhosting.get(mod, True)
                oldGhost = modInfo.isGhost
                newGhost = modInfo.setGhost(modGhost)
                if newGhost != oldGhost:
                    changed.append(mod)
        return changed

    def _refreshInfoLists(self):
        """Refreshes various mod info lists (exGroup_mods, imported,
        exported) - call after refreshing from Data AND having latest load
        order."""
        #--Bashed patches
        self.bashed_patches.clear()
        for modName, modInfo in self.iteritems():
            if modInfo.isBP(): self.bashed_patches.add(modName)
        #--Refresh overLoaded
        self.exGroup_mods.clear()
        active_set = set(load_order.cached_active_tuple())
        for modName in active_set:
            maExGroup = reExGroup.match(modName.s)
            if maExGroup:
                exGroup = maExGroup.group(1)
                self.exGroup_mods[exGroup].append(modName)
        #--Refresh merged/imported lists.
        self.merged, self.imported = self.getSemiActive(active_set)

    def _refreshMergeable(self):
        """Refreshes set of mergeable mods."""
        #--Mods that need to be rescanned - call rescanMergeable !
        newMods = []
        self.mergeable.clear()
        name_mergeInfo = self.table.getColumn('mergeInfo')
        #--Add known/unchanged and esms - we need to scan dependent mods
        # first to account for mergeability of their masters
        for mpath, modInfo in sorted(self.items(),
                key=lambda tup: load_order.cached_lo_index(tup[0]),
                                     reverse=True):
            size, canMerge = name_mergeInfo.get(mpath, (None, None))
            # if esm bit was flipped size won't change, so check this first
            if modInfo.isEsm():
                name_mergeInfo[mpath] = (modInfo.size, False)
                self.mergeable.discard(mpath)
            elif size == modInfo.size:
                if canMerge: self.mergeable.add(mpath)
            else:
                newMods.append(mpath)
        return newMods

    def rescanMergeable(self, names, prog=None, doCBash=None, verbose=False):
        with prog or balt.Progress(_(u"Mark Mergeable") + u' ' * 30) as prog:
            return self._rescanMergeable(names, prog, doCBash, verbose)

    def _rescanMergeable(self, names, progress, doCBash, verbose):
        """Will rescan specified mods."""
        if doCBash is None:
            doCBash = CBashApi.Enabled
        elif doCBash and not CBashApi.Enabled:
            doCBash = False
        is_mergeable = isCBashMergeable if doCBash else isPBashMergeable
        mod_mergeInfo = self.table.getColumn('mergeInfo')
        progress.setFull(max(len(names),1))
        result, tagged_no_merge = OrderedDict(), set()
        for i,fileName in enumerate(names):
            progress(i,fileName.s)
            if not doCBash and reOblivion.match(fileName.s): continue
            fileInfo = self[fileName]
            if not bush.game.esp.canBash:
                canMerge = False
            else:
                try:
                    canMerge = is_mergeable(fileInfo, self, verbose)
                except Exception as e:
                    # deprint (_(u"Error scanning mod %s (%s)") % (fileName, e))
                    # canMerge = False #presume non-mergeable.
                    raise
            result[fileName] = canMerge
            if not isinstance(canMerge, basestring) and canMerge: # True...
                self.mergeable.add(fileName)
                mod_mergeInfo[fileName] = (fileInfo.size,True)
            else:
                mod_mergeInfo[fileName] = (fileInfo.size,False)
                self.mergeable.discard(fileName)
            if fileName in self.mergeable and u'NoMerge' in fileInfo.getBashTags():
                tagged_no_merge.add(fileName)
        return result, tagged_no_merge

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

    #--Refresh File
    def refreshFile(self, fileName, _in_refresh=False):
        try:
            FileInfos.refreshFile(self, fileName, _in_refresh)
        finally:
            self._refreshInfoLists() # not sure if needed here - track usages !

    #--Mod selection ----------------------------------------------------------
    def getSemiActive(self,masters):
        """Return (merged,imported) mods made semi-active by Bashed Patch.

        If no bashed patches are present in 'masters' then return empty sets.
        Else for each bashed patch use its config (if present) to find mods
        it merges or imports."""
        merged,imported = set(),set()
        patches = masters & self.bashed_patches
        for patch in patches:
            patchConfigs = self.table.getItem(patch, 'bash.patch.configs')
            if not patchConfigs: continue
            patcherstr = 'CBash_PatchMerger' if patcher.configIsCBash(
                patchConfigs) else 'PatchMerger'
            if patchConfigs.get(patcherstr,{}).get('isEnabled'):
                config_checked = patchConfigs[patcherstr]['configChecks']
                for modName in config_checked:
                    if config_checked[modName] and modName in self:
                        merged.add(modName)
            imported.update(filter(lambda x: x in self,
                                   patchConfigs.get('ImportedMods', tuple())))
        return merged,imported

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
                masters = set(load_order.cached_active_tuple())
                merged,imported = self.merged,self.imported
            allMods = masters | merged | imported
            allMods = load_order.get_ordered([x for x in allMods if x in self])
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
                        elif load_order.get_ordered((name, master2))[1] == master2:
                            log(sDelinquent+master2.s)
            if not wtxt: log(u'[/xml][/spoiler]')
            return bolt.winNewLines(log.out.getvalue())

    @staticmethod
    def _tagsies(modInfo, tagList):
        mname = modInfo.name
        def _tags(msg, iterable, tagsList):
            return tagsList + u'  * ' + msg + u', '.join(iterable) + u'\n'
        if not modInfos.table.getItem(mname, 'autoBashTags') and \
               modInfos.table.getItem(mname, 'bashTags', u''):
            tagList = _tags(_(u'From Manual (if any this overrides '
                u'Description/LOOT sourced tags): '), sorted(
                modInfos.table.getItem(mname, 'bashTags', u'')), tagList)
        tags_desc = modInfo.getBashTagsDesc()
        if tags_desc:
            tagList = _tags(_(u'From Description: '), sorted(tags_desc),
                            tagList)
        tags, removed, _userlist = configHelpers.getTagsInfoCache(mname)
        if tags:
            tagList = _tags(_(u'From LOOT Masterlist and or userlist: '),
                            sorted(tags), tagList)
        if removed:
            tagList = _tags(_(u'Removed by LOOT Masterlist and or userlist: '),
                            sorted(removed), tagList)
        return _tags(_(u'Result: '), sorted(modInfo.getBashTags()), tagList)

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
            lindex = lambda t: load_order.cached_lo_index(t[0])
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

    #--Active mods management -------------------------------------------------
    def lo_activate(self, fileName, doSave=True, _modSet=None, _children=None,
                    _activated=None):
        """Mutate _active_wip cache then save if needed."""
        if _activated is None: _activated = set()
        try:
            if len(self._active_wip) == 255:
                raise PluginsFullError(u'%s: Trying to activate more than 255 mods' % fileName)
            _children = (_children or tuple()) + (fileName,)
            if fileName in _children[:-1]:
                raise BoltError(u'Circular Masters: ' +u' >> '.join(x.s for x in _children))
            #--Select masters
            if _modSet is None: _modSet = set(self.keys())
            #--Check for bad masternames:
            #  Disabled for now
            ##if self[fileName].hasBadMasterNames():
            ##    return
            for master in self[fileName].header.masters:
                if master in _modSet: self.lo_activate(master, False, _modSet,
                                                       _children, _activated)
            #--Select in plugins
            if fileName not in self._active_wip:
                self._active_wip.append(fileName)
                _activated.add(fileName)
            return load_order.get_ordered(_activated or [])
        finally:
            if doSave: self.cached_lo_save_active()

    def lo_deactivate(self, fileName, doSave=True):
        """Remove mods and their children from _active_wip, can only raise if
        doSave=True."""
        if not isinstance(fileName, (set, list)): fileName = {fileName}
        notDeactivatable = load_order.must_be_active_if_present()
        fileNames = set(x for x in fileName if x not in notDeactivatable)
        old = sel = set(self._active_wip)
        diff = sel - fileNames
        if len(diff) == len(sel): return set()
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
        self._active_wip = load_order.get_ordered(sel)
        #--Save
        if doSave: self.cached_lo_save_active()
        return old - sel # return deselected

    def lo_activate_all(self):
        toActivate = set(load_order.cached_active_tuple())
        try:
            def _add_to_activate(m):
                if not m in toActivate:
                    self.lo_activate(m, doSave=False)
                    toActivate.add(m)
            mods = load_order.get_ordered(self.keys())
            # first select the bashed patch(es) and their masters
            for mod in mods: ##: usually results in exclusion group violation
                if self[mod].isBP(): _add_to_activate(mod)
            # then activate mods not tagged NoMerge or Deactivate or Filter
            def _activatable(modName):
                tags = modInfos[modName].getBashTags()
                return not (u'Deactivate' in tags or u'Filter' in tags)
            mods = filter(_activatable, mods)
            mergeable = set(self.mergeable)
            for mod in mods:
                if not mod in mergeable: _add_to_activate(mod)
            # then activate as many of the remaining mods as we can
            for mod in mods:
                if mod in mergeable: _add_to_activate(mod)
        except PluginsFullError:
            deprint(u'select All: 255 mods activated', traceback=True)
            raise
        except BoltError:
            toActivate.clear()
            deprint(u'select All: cached_lo_save_active failed',traceback=True)
            raise
        finally:
            if toActivate: self.cached_lo_save_active(active=toActivate)

    def lo_activate_exact(self, modNames):
        """Activate exactly the specified set of mods."""
        modsSet, allMods = set(modNames), set(self.keys())
        #--Ensure plugins that cannot be deselected stay selected
        modsSet.update(load_order.must_be_active_if_present() & allMods)
        #--Deselect/select plugins
        missingSet = modsSet - allMods
        toSelect = modsSet - missingSet
        listToSelect = load_order.get_ordered(toSelect)
        extra = listToSelect[255:]
        #--Save
        final_selection = listToSelect[:255]
        self.cached_lo_save_active(active=final_selection)
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

    #--Helpers ----------------------------------------------------------------
    @staticmethod
    def isBadFileName(modName):
        """True if the name cannot be encoded to the proper format for plugins.txt"""
        try:
            modName.encode('cp1252')
            return False
        except UnicodeEncodeError:
            return True

    def getDirtyMessage(self, modname):
        """Returns a dirty message from LOOT."""
        if self.table.getItem(modname, 'ignoreDirty', False):
            return False, u''
        return configHelpers.getDirtyMessage(modname)

    def ini_files(self):
        iniFiles = self._plugin_inis.values() # in active order
        iniFiles.reverse() # later loading inis override previous settings
        iniFiles.append(oblivionIni)
        return iniFiles

    def calculateLO(self, mods=None): # excludes corrupt mods
        if mods is None: mods = self.keys()
        mods = sorted(mods) # sort case insensitive (for time conflicts)
        mods.sort(key=lambda x: self[x].mtime)
        mods.sort(key=lambda x: not self[x].isEsm())
        return mods

    def create_new_mod(self, newName, selected=(), masterless=False,
                       directory=u'', bashed_patch=False):
        directory = directory or self.store_dir
        new_name = GPath(newName)
        newInfo = self.factory(directory, new_name)
        newFile = ModFile(newInfo)
        if not masterless:
            newFile.tes4.masters = [self.masterName]
        if bashed_patch:
            newFile.tes4.author = u'BASHED PATCH'
        newFile.safeSave()
        if directory == self.store_dir:
            self.refreshFile(new_name) # add to self, refresh size etc
            last_selected = load_order.get_ordered(selected)[
                -1] if selected else self._lo_wip[-1]
            self.cached_lo_insert_after(last_selected, new_name)
            self.cached_lo_save_lo()
            self.refresh(refresh_infos=False)

    def generateNextBashedPatch(self, selected_mods):
        """Attempt to create a new bashed patch, numbered from 0 to 9.  If
        a lowered number bashed patch exists, will create the next in the
        sequence."""
        for num in xrange(10):
            modName = GPath(u'Bashed Patch, %d.esp' % num)
            if modName not in self:
                self.create_new_mod(modName, selected=selected_mods,
                                    masterless=True, bashed_patch=True)
                return modName
        return None

    #--Mod move/delete/rename -------------------------------------------------
    def _lo_caches_remove_mods(self, to_remove):
        """Remove the specified mods from _lo_wip and _active_wip caches."""
        # Use set to remove any duplicates
        to_remove = set(to_remove, )
        # Remove mods from cache
        self._lo_wip = [x for x in self._lo_wip if x not in to_remove]
        self._active_wip  = [x for x in self._active_wip if x not in to_remove]

    def _rename_operation(self, oldName, newName):
        """Renames member file from oldName to newName."""
        isSelected = load_order.cached_is_active(oldName)
        if isSelected:
            self.lo_deactivate(oldName, doSave=False) # will save later
        super(ModInfos, self)._rename_operation(oldName, newName)
        # rename in load order caches
        oldIndex = self._lo_wip.index(oldName)
        self._lo_caches_remove_mods([oldName])
        self._lo_wip.insert(oldIndex, newName)
        if isSelected: self.lo_activate(newName, doSave=False)
        # Save to disc (load order and plugins.txt)
        self.cached_lo_save_all()

    def _get_rename_paths(self, oldName, newName):
        renames = super(ModInfos, self)._get_rename_paths(oldName, newName)
        if self[oldName].isGhost:
            renames[0] = (renames[0][0], renames[0][1] + u'.ghost')
        return renames

    #--Delete
    def files_to_delete(self, filenames, **kwargs):
        for f in set(filenames):
            if f.s in bush.game.masterFiles:
                if kwargs.pop('raise_on_master_deletion', True):
                    raise bolt.BoltError(
                        u"Cannot delete the game's master file(s).")
                else:
                    filenames.remove(f)
        self.lo_deactivate(filenames, doSave=False)
        return super(ModInfos, self).files_to_delete(filenames)

    def delete_refresh(self, deleted, paths_to_keys, check_existence,
                       _in_refresh=False):
        # adapted from refresh() (avoid refreshing from the data directory)
        deleted = super(ModInfos, self).delete_refresh(deleted, paths_to_keys,
                                                       check_existence)
        if not deleted: return
        # temporarily track deleted mods so BAIN can update its UI
        if _in_refresh: return
        self._lo_caches_remove_mods(deleted)
        self.cached_lo_save_all()
        self._refreshBadNames()
        self._refreshInfoLists()
        self._refreshMissingStrings()
        self._refreshMergeable()

    def _additional_deletes(self, fileInfo, toDelete):
        super(ModInfos, self)._additional_deletes(fileInfo, toDelete)
        #--Misc. Editor backups (mods only)
        for ext in (u'.bak', u'.tmp', u'.old', u'.ghost'):
            toDelete.append(fileInfo.name + ext)

    def move_info(self, fileName, destDir):
        """Moves member file to destDir."""
        self.lo_deactivate(fileName, doSave=False)
        FileInfos.move_info(self, fileName, destDir)

    def move_infos(self, sources, destinations, window):
        moved = super(ModInfos, self).move_infos(sources, destinations, window)
        self.refresh() # yak, it should have an "added" parameter
        balt.Link.Frame.warn_corrupted(warn_saves=False)
        return moved

    def get_hide_dir(self, name):
        dest_dir =self.hidden_dir
        #--Use author subdirectory instead?
        mod_author = self[name].header.author
        if mod_author:
            authorDir = dest_dir.join(mod_author)
            if authorDir.isdir():
                return authorDir
        #--Use group subdirectory instead?
        file_group = self.table.getItem(name, 'group')
        if file_group:
            groupDir = dest_dir.join(file_group)
            if groupDir.isdir():
                return groupDir
        return dest_dir

    #--Mod info/modify --------------------------------------------------------
    def getVersion(self, fileName):
        """Extracts and returns version number for fileName from header.hedr.description."""
        if not fileName in self.data or not self.data[fileName].header:
            return ''
        maVersion = reVersion.search(self[fileName].header.description)
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
    def _setOblivionVersions(self):
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

    def _get_version_paths(self, newVersion):
        baseName = self.masterName # Oblivion.esm, say it's currently SI one
        newSize = self.version_voSize[newVersion]
        oldSize = self[baseName].size
        if newSize == oldSize: return None, None
        if oldSize not in self.size_voVersion:
            raise StateError(u"Can't match current main ESM to known version.")
        oldName = GPath( # Oblivion_SI.esm: we will rename Oblivion.esm to this
            baseName.sbody + u'_' + self.size_voVersion[oldSize] + u'.esm')
        if self.store_dir.join(oldName).exists():
            raise StateError(u"Can't swap: %s already exists." % oldName)
        newName = GPath(baseName.sbody + u'_' + newVersion + u'.esm')
        if newName not in self.data:
            raise StateError(u"Can't swap: %s doesn't exist." % newName)
        return newName, oldName

    def setOblivionVersion(self,newVersion):
        """Swaps Oblivion.esm to to specified version."""
        # if new version is u'1.1' then newName is Path(Oblivion_1.1.esm)
        newName, oldName = self._get_version_paths(newVersion)
        if newName is None: return
        newInfo = self[newName]
        #--Rename
        baseInfo = self[self.masterName]
        master_time = baseInfo.mtime
        new_info_time = newInfo.mtime
        is_master_active = load_order.cached_is_active(self.masterName)
        is_new_info_active = load_order.cached_is_active(newName)
        # can't use ModInfos rename cause it will mess up the load order
        rename_operation = super(ModInfos, self)._rename_operation
        first_try = True
        while first_try or (werr.errno == errno.EACCES and
                self._retry(baseInfo.getPath(), self.store_dir.join(oldName))):
            first_try = False
            try:
                rename_operation(self.masterName, oldName)
            except OSError as werr: # can only occur if SHFileOperation
                # isn't called, yak - file operation API badly needed
                continue
            except CancelError:
                return
            break
        else:
            raise
        first_try = True
        while first_try or (werr.errno == errno.EACCES and
                self._retry(newInfo.getPath(), baseInfo.getPath())):
            first_try = False
            try:
                rename_operation(newName, self.masterName)
            except OSError as werr:
                continue
            except CancelError:
                #Undo any changes
                rename_operation(oldName, self.masterName)
                # return
            break
        else:
            #Undo any changes
            rename_operation(oldName, self.masterName)
            raise
        # set mtimes to previous respective values
        self[self.masterName].setmtime(master_time)
        self[oldName].setmtime(new_info_time)
        oldIndex = self._lo_wip.index(newName)
        self._lo_caches_remove_mods([newName])
        self._lo_wip.insert(oldIndex, oldName)
        def _activate(active, mod):
            if active: self[mod].setGhost(False) # needed if autoGhost is False
            (self.lo_activate if active else self.lo_deactivate)(mod,
                                                                 doSave=False)
        _activate(is_new_info_active, oldName)
        _activate(is_master_active, self.masterName)
        # Save to disc (load order and plugins.txt)
        self.cached_lo_save_all() # sets ghost as needed iff autoGhost is True
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
    _notify_bain_on_delete = False
    try:
        _ext = ur'\.' + bush.game.ess.ext[1:]
    except AttributeError: # 'NoneType' object has no attribute 'ess'
        _ext = u''
    file_pattern = re.compile(
        ur'((quick|auto)save(\.bak)+|(' + # quick or auto save.bak(.bak...) or
        _ext + ur'|' + _ext[:-1] + ur'r' + ur'))$', # enabled or disabled save
        re.I | re.U)
    del _ext
    bak_file_pattern = re.compile(ur'(quick|auto)save(\.bak)+', re.I | re.U)

    def _setLocalSaveFromIni(self):
        """Read the current save profile from the oblivion.ini file and set
        local save attribute to that value."""
        # saveInfos singleton is constructed in InitData after bosh.oblivionIni
        self.localSave = oblivionIni.getSetting(
            bush.game.saveProfilesKey[0], bush.game.saveProfilesKey[1],
            u'Saves\\')
        # Hopefully will solve issues with unicode usernames # TODO(ut) test
        self.localSave = decode(self.localSave) # encoding = 'cp1252' ?

    def __init__(self):
        self.localSave = u'Saves\\'
        self._setLocalSaveFromIni()
        super(SaveInfos, self).__init__(dirs['saveBase'].join(self.localSave),
                                        SaveInfo)
        # Save Profiles database
        self.profiles = bolt.Table(bolt.PickleDict(
            dirs['saveBase'].join(u'BashProfiles.dat')))

    @property
    def bash_dir(self): return self.store_dir.join(u'Bash')

    def refresh(self, refresh_infos=True):
        self._refreshLocalSave()
        return refresh_infos and FileInfos.refresh(self)

    def _additional_deletes(self, fileInfo, toDelete):
        toDelete.extend(CoSaves.getPaths(fileInfo.getPath()))
        # now add backups and cosaves backups
        super(SaveInfos, self)._additional_deletes(fileInfo, toDelete)

    def _get_rename_paths(self, oldName, newName):
        renames = [tuple(map(self.store_dir.join, (oldName, newName)))]
        renames.extend(CoSaves.get_new_paths(*renames[0]))
        return renames

    def copy_info(self, fileName, destDir, destName=empty_path, set_mtime=None):
        """Copies savefile and associated pluggy file."""
        FileInfos.copy_info(self, fileName, destDir, destName, set_mtime)
        CoSaves(self.store_dir, fileName).copy(destDir, destName or fileName)

    def move_infos(self, sources, destinations, window):
        # CoSaves sucks - operations should be atomic
        moved = super(SaveInfos,self).move_infos(sources, destinations, window)
        for s, d in zip(sources, destinations):
            if d.tail in moved: CoSaves(s).move(d)
        for d in moved:
            try:
                self.refreshFile(d)
            except FileError:
                pass # will warn below
        balt.Link.Frame.warn_corrupted(warn_mods=False, warn_strings=False)
        return moved

    def move_info(self, fileName, destDir):
        """Moves member file to destDir. Will overwrite!"""
        FileInfos.move_info(self, fileName, destDir)
        CoSaves(self.store_dir, fileName).move(destDir, fileName)

    #--Local Saves ------------------------------------------------------------
    @staticmethod
    def getLocalSaveDirs():
        """Returns a list of possible local save directories, NOT including the base directory."""
        baseSaves = dirs['saveBase'].join(u'Saves')
        if baseSaves.exists():
            localSaveDirs = [x for x in baseSaves.list() if (x != u'Bash' and baseSaves.join(x).isdir())]
            # Filter out non-encodable names
            bad = set()
            for folder in localSaveDirs:
                try:
                    folder.s.encode('cp1252')
                except UnicodeEncodeError:
                    bad.add(folder)
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
        if not oblivionIni.ask_create_target_ini(msg=_(
                u'Setting the save profile is done by editing the game ini.')):
            return
        self.localSave = localSave
        oblivionIni.saveSetting(bush.game.saveProfilesKey[0],
                                bush.game.saveProfilesKey[1],
                                localSave)
        self._initDB(dirs['saveBase'].join(self.localSave))
        if refreshSaveInfos: self.refresh()

    #--Enabled ----------------------------------------------------------------
    @staticmethod
    def is_save_enabled(fileName):
        """True if fileName is enabled."""
        return fileName.cext == bush.game.ess.ext

    def enable(self,fileName,value=True):
        """Enables file by changing extension to 'ess' (True) or 'esr' (False)."""
        enabled = self.is_save_enabled(fileName)
        if value == enabled or re.match(u'(autosave|quicksave)', fileName.s,
                                          re.I | re.U):
            return fileName
        (root,ext) = fileName.rootExt
        newName = root + (bush.game.ess.ext if value else ext[:-1] + u'r')
        try:
            self.rename_info(fileName, newName)
            return newName
        except (CancelError, OSError, IOError):
            return fileName

#------------------------------------------------------------------------------
class BSAInfos(FileInfos):
    """BSAInfo collection. Represents bsa files in game's Data directory."""
    try:
        file_pattern = re.compile(ur'\.' + bush.game.bsa_extension + ur'$',
                                  re.I | re.U)
    except AttributeError:
        pass

    def __init__(self): super(BSAInfos, self).__init__(dirs['mods'], BSAInfo)

    @property
    def bash_dir(self): return dirs['modsBash'].join(u'BSA Data')

#------------------------------------------------------------------------------
class PeopleData(DataStore):
    """Data for a People UIList. Built on a PickleDict."""
    def __init__(self):
        self.dictFile = bolt.PickleDict(dirs['saveBase'].join(u'People.dat'))
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

    def delete(self, keys, **kwargs):
        """Delete entry."""
        for key in keys: del self[key]
        self.hasChanged = True

    def delete_refresh(self, deleted, deleted2, check_existence): pass

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
                    self[name] = (time.time(), 0, buff.getvalue().strip())
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
                out.write(self[name][2].strip())
                out.write(u'\n\n')

#------------------------------------------------------------------------------
class ScreensData(DataStore):
    reImageExt = re.compile(
        ur'\.(' + ur'|'.join(ext[1:] for ext in imageExts) + ur')$',
        re.I | re.U)

    def __init__(self):
        self.store_dir = dirs['app']
        self.data = {} #--data[Path] = (ext,mtime)

    def refresh(self):
        """Refresh list of screenshots."""
        self.store_dir = dirs['app']
        ssBase = GPath(oblivionIni.getSetting(
            u'Display', u'SScreenShotBaseName', u'ScreenShot'))
        if ssBase.head:
            self.store_dir = self.store_dir.join(ssBase.head)
        newData = {}
        #--Loop over files in directory
        for fileName in self.store_dir.list():
            filePath = self.store_dir.join(fileName)
            maImageExt = self.reImageExt.search(fileName.s)
            if maImageExt and filePath.isfile():
                newData[fileName] = (maImageExt.group(1).lower(),filePath.mtime)
        changed = (self.data != newData)
        self.data = newData
        return changed

    def files_to_delete(self, filenames, **kwargs):
        toDelete = [self.store_dir.join(screen) for screen in filenames]
        return toDelete, None

    def delete_refresh(self, deleted, deleted2, check_existence):
        for item in deleted:
            if not item.exists(): del self[item.tail]

    def _rename_operation(self, oldName, newName):
        super(ScreensData, self)._rename_operation(oldName, newName)
        self[newName] = self[oldName]
        del self[oldName]

#------------------------------------------------------------------------------
from . import converters
from .converters import InstallerConverter
# Hack below needed as older Converters.dat expect bosh.InstallerConverter
# See InstallerConverter.__reduce__()
# noinspection PyRedeclaration
class InstallerConverter(InstallerConverter): pass
# same hack for Installers.dat...
from .bain import InstallerArchive, InstallerMarker, InstallerProject
# noinspection PyRedeclaration
class InstallerArchive(InstallerArchive): pass
# noinspection PyRedeclaration
class InstallerMarker(InstallerMarker): pass
# noinspection PyRedeclaration
class InstallerProject(InstallerProject): pass

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
        loadFactory = LoadFactory(False, MreRecord.type_class['SPEL'])
        modFile = ModFile(modInfo, loadFactory)
        try: modFile.load(True)
        except ModError as err:
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

# Initialization --------------------------------------------------------------
from ..env import get_personal_path, get_local_app_data_path

def getPersonalPath(bashIni, my_docs_path):
    #--Determine User folders from Personal and Local Application Data directories
    #  Attempt to pull from, in order: Command Line, Ini, win32com, Registry
    if my_docs_path:
        my_docs_path = GPath(my_docs_path)
        sErrorInfo = _(u"Folder path specified on command line (-p)")
    elif bashIni and bashIni.has_option(u'General', u'sPersonalPath') and \
            not bashIni.get(u'General', u'sPersonalPath') == u'.':
        my_docs_path = GPath(bashIni.get('General', 'sPersonalPath').strip())
        sErrorInfo = _(
            u"Folder path specified in bash.ini (%s)") % u'sPersonalPath'
    else:
        my_docs_path, sErrorInfo = get_personal_path()
    #  If path is relative, make absolute
    if not my_docs_path.isabs():
        my_docs_path = dirs['app'].join(my_docs_path)
    #  Error check
    if not my_docs_path.exists():
        raise BoltError(u"Personal folder does not exist.\n"
                        u"Personal folder: %s\nAdditional info:\n%s"
                        % (my_docs_path.s, sErrorInfo))
    return my_docs_path

def getLocalAppDataPath(bashIni, app_data_local_path):
    #--Determine User folders from Personal and Local Application Data directories
    #  Attempt to pull from, in order: Command Line, Ini, win32com, Registry
    if app_data_local_path:
        app_data_local_path = GPath(app_data_local_path)
        sErrorInfo = _(u"Folder path specified on command line (-l)")
    elif bashIni and bashIni.has_option(u'General', u'sLocalAppDataPath') and not bashIni.get(u'General', u'sLocalAppDataPath') == u'.':
        app_data_local_path = GPath(bashIni.get(u'General', u'sLocalAppDataPath').strip())
        sErrorInfo = _(u"Folder path specified in bash.ini (%s)") % u'sLocalAppDataPath'
    else:
        app_data_local_path, sErrorInfo = get_local_app_data_path()
    #  If path is relative, make absolute
    if not app_data_local_path.isabs():
        app_data_local_path = dirs['app'].join(app_data_local_path)
    #  Error check
    if not app_data_local_path.exists():
        raise BoltError(u"Local AppData folder does not exist.\nLocal AppData folder: %s\nAdditional info:\n%s"
                        % (app_data_local_path.s, sErrorInfo))
    return app_data_local_path

def getOblivionModsPath(bashIni):
    if bashIni and bashIni.has_option(u'General',u'sOblivionMods'):
        ob_mods_path = GPath(bashIni.get(u'General', u'sOblivionMods').strip())
        src = [u'[General]', u'sOblivionMods']
    else:
        ob_mods_path = GPath(GPath(u'..').join(u'%s Mods' % bush.game.fsName))
        src = u'Relative Path'
    if not ob_mods_path.isabs(): ob_mods_path = dirs['app'].join(ob_mods_path)
    return ob_mods_path, src

def getBainDataPath(bashIni):
    if bashIni and bashIni.has_option(u'General',u'sInstallersData'):
        idata_path = GPath(bashIni.get(u'General', u'sInstallersData').strip())
        src = [u'[General]', u'sInstallersData']
        if not idata_path.isabs(): idata_path = dirs['app'].join(idata_path)
    else:
        idata_path = dirs['installers'].join(u'Bash')
        src = u'Relative Path'
    return idata_path, src

def getBashModDataPath(bashIni):
    if bashIni and bashIni.has_option(u'General',u'sBashModData'):
        mod_data_path = GPath(bashIni.get(u'General', u'sBashModData').strip())
        if not mod_data_path.isabs():
            mod_data_path = dirs['app'].join(mod_data_path)
        src = [u'[General]', u'sBashModData']
    else:
        mod_data_path, src = getOblivionModsPath(bashIni)
        mod_data_path = mod_data_path.join(u'Bash Mod Data')
    return mod_data_path, src

def getLegacyPath(newPath, oldPath, srcNew=None, srcOld=None):
    return (oldPath,newPath)[newPath.isdir() or not oldPath.isdir()]

def getLegacyPathWithSource(newPath, oldPath, newSrc, oldSrc=None):
    if newPath.isdir() or not oldPath.isdir():
        return newPath, newSrc
    else:
        return oldPath, oldSrc

from ..env import test_permissions # CURRENTLY DOES NOTHING !
def initDirs(bashIni, personal, localAppData):
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
    dirs['defaultPatches'] = dirs['mopy'].join(u'Bash Patches', bush.game.fsName)
    dirs['tweaks'] = dirs['mods'].join(u'INI Tweaks')

    #  Personal
    personal = getPersonalPath(bashIni,personal)
    dirs['saveBase'] = personal.join(u'My Games', bush.game.fsName)

    #  Local Application Data
    localAppData = getLocalAppDataPath(bashIni,localAppData)
    dirs['userApp'] = localAppData.join(bush.game.fsName)

    # Use local paths if bUseMyGamesDirectory=0 in Oblivion.ini
    global gameInis
    global oblivionIni
    gameInis = tuple(OblivionIni(x) for x in bush.game.iniFiles)
    oblivionIni = gameInis[0]
    try:
        if oblivionIni.getSetting(u'General',u'bUseMyGamesDirectory',u'1') == u'0':
            # Set the save game folder to the Oblivion directory
            dirs['saveBase'] = dirs['app']
            # Set the data folder to sLocalMasterPath
            dirs['mods'] = dirs['app'].join(oblivionIni.getSetting(u'General', u'SLocalMasterPath', u'Data\\'))
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
        dirs['modsBash'], dirs['app'].join(u'Data', u'Bash'),
        modsBashSrc, u'Relative Path')

    dirs['installers'] = oblivionMods.join(u'Bash Installers')
    dirs['installers'] = getLegacyPath(dirs['installers'],
                                       dirs['app'].join(u'Installers'))

    dirs['bainData'], bainDataSrc = getBainDataPath(bashIni)

    dirs['bsaCache'] = dirs['bainData'].join(u'BSA Cache')

    dirs['converters'] = dirs['installers'].join(u'Bain Converters')
    dirs['dupeBCFs'] = dirs['converters'].join(u'--Duplicates')
    dirs['corruptBCFs'] = dirs['converters'].join(u'--Corrupt')

    #--Test correct permissions for the directories
    badPermissions = [test_dir for test_dir in dirs.itervalues()
                      if not test_permissions(test_dir)] # DOES NOTHING !!!
    if not test_permissions(oblivionMods):
        badPermissions.append(oblivionMods)
    if badPermissions:
        # Do not have all the required permissions for all directories
        # TODO: make this gracefully degrade.  IE, if only the BAIN paths are
        # bad, just disable BAIN.  If only the saves path is bad, just disable
        # saves related stuff.
        msg = balt.fill(_(u'Wrye Bash cannot access the following paths:'))
        msg += u'\n\n' + u'\n'.join(
            [u' * ' + bad_dir.s for bad_dir in badPermissions]) + u'\n\n'
        msg += balt.fill(_(u'See: "Wrye Bash.html, Installation - Windows Vista/7" for information on how to solve this problem.'))
        raise PermissionError(msg)

    # create bash user folders, keep these in order
    keys = ('modsBash', 'installers', 'converters', 'dupeBCFs', 'corruptBCFs',
            'bainData', 'bsaCache')
    try:
        env.shellMakeDirs([dirs[key] for key in keys])
    except env.NonExistentDriveError as e:
        # NonExistentDriveError is thrown by shellMakeDirs if any of the
        # directories cannot be created due to residing on a non-existing
        # drive. Find which keys are causing the errors
        badKeys = set()     # List of dirs[key] items that are invalid
        # First, determine which dirs[key] items are causing it
        for key in keys:
            if dirs[key] in e.failed_paths:
                badKeys.add(key)
        # Now, work back from those to determine which setting created those
        msg = _(u'Error creating required Wrye Bash directories.') + u'  ' + _(
            u'Please check the settings for the following paths in your '
            u'bash.ini, the drive does not exist') + u':\n\n'
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
            msg += u'\n' + _(u'A path error was the result of relative paths.')
            msg += u'  ' + _(u'The following paths are causing the errors, '
                             u'however usually a relative path should be fine.')
            msg += u'  ' + _(u'Check your setup to see if you are using '
                             u'symbolic links or NTFS Junctions') + u':\n\n'
            msg += u'\n'.join([u'%s' % x for x in relativePathError])
        raise BoltError(msg)

    # Setup LOOT API, needs to be done after the dirs are initialized
    global configHelpers
    configHelpers = ConfigHelpers()

def initDefaultTools():
    #-- Other tool directories
    #   First to default path
    pf = [GPath(u'C:\\Program Files'),GPath(u'C:\\Program Files (x86)')]
    def pathlist(*args): return [x.join(*args) for x in pf]

    # BOSS can be in any number of places.
    # Detect locally installed (into game folder) BOSS
    if dirs['app'].join(u'BOSS', u'BOSS.exe').exists():
        tooldirs['boss'] = dirs['app'].join(u'BOSS').join(u'BOSS.exe')
    else:
        tooldirs['boss'] = GPath(u'C:\\**DNE**')
        # Detect globally installed (into Program Files) BOSS
        from ..env import winreg
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

    tooldirs['Tes4FilesPath'] = dirs['app'].join(u'Tools', u'TES4Files.exe')
    tooldirs['Tes4EditPath'] = dirs['app'].join(u'TES4Edit.exe')
    tooldirs['Tes5EditPath'] = dirs['app'].join(u'TES5Edit.exe')
    tooldirs['SSEEditPath'] = dirs['app'].join(u'SSEEdit.exe')
    tooldirs['Fo4EditPath'] = dirs['app'].join(u'FO4Edit.exe')
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
    tooldirs['MAP'] = dirs['app'].join(u'Modding Tools', u'Interactive Map of Cyrodiil and Shivering Isles 3.52', u'Mapa v 3.52.exe')
    tooldirs['OBMLG'] = dirs['app'].join(u'Modding Tools', u'Oblivion Mod List Generator', u'Oblivion Mod List Generator.exe')
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
    tooldirs['Tabula'] = dirs['app'].join(u'Modding Tools', u'Tabula', u'Tabula.exe')
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
    inisettings['ScriptFileExt'] = u'.txt'
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
    inisettings['SkippedBashInstallersDirs'] = u''

def initOptions(bashIni):
    initDefaultTools()
    initDefaultSettings()

    defaultOptions = {}
    type_key = {str:u's',unicode:u's',list:u's',int:u'i',bool:u'b',bolt.Path:u's'}
    allOptions = [tooldirs, inisettings]
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
    if inisettings['KeepLog'] == 0: return
    with inisettings['LogFile'].open('a', encoding='utf-8-sig') as log:
        log.write(_(u'%s Wrye Bash ini file read, Keep Log level: %d, '
                    u'initialized.') % (
                  bolt.timestamp(), inisettings['KeepLog']) + u'\r\n')

def initBosh(personal=empty_path, localAppData=empty_path, bashIni=None):
    #--Bash Ini
    if not bashIni: bashIni = bass.GetBashIni()
    initDirs(bashIni, personal, localAppData)
    load_order.initialize_load_order_files()
    initOptions(bashIni)
    try:
        initLogFile()
    except IOError:
        deprint('Error creating log file', traceback=True)
    from .bain import Installer
    Installer.init_bain_dirs()
    archives.exe7z = dirs['compiled'].join(archives.exe7z).s

def initSettings(readOnly=False, _dat=u'BashSettings.dat',
                 _bak=u'BashSettings.dat.bak'):
    """Init user settings from files and load the defaults (also in basher)."""

    def _load(dat_file=_dat):
    # bolt.PickleDict.load() handles EOFError, ValueError falling back to bak
        return bolt.Settings( # calls PickleDict.load() and copies loaded data
            bolt.PickleDict(dirs['saveBase'].join(dat_file), readOnly))

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
    except cPickle.UnpicklingError as err:
        msg = _(
            u"Error reading the Bash Settings database (the error is: '%s'). "
            u"This is probably not recoverable with the current file. Do you "
            u"want to try the backup BashSettings.dat? (It will have all your "
            u"UI choices of the time before last that you used Wrye Bash.")
        usebck = balt.askYes(None, msg % repr(err), _(u"Settings Load Error"))
        if usebck:
            try:
                settings = _loadBakOrEmpty()
            except cPickle.UnpicklingError as err:
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
    bass.settings = settings
    if 'bash.readme' in settings:
        settings['bash.version'] = _(settings['bash.readme'][1])
        del settings['bash.readme']
