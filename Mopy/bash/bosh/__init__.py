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
from binascii import crc32
from collections import OrderedDict
from functools import wraps, partial
from itertools import groupby
from operator import attrgetter, itemgetter

from .mods_metadata import ConfigHelpers
from .. import bass, bolt, balt, bush, env, load_order, libbsa, archives
from .. import patcher # for configIsCBash()
from ..archives import defaultExt, readExts, compressionSettings, \
    countFilesInArchive
from ..bass import dirs, inisettings, tooldirs, reModExt
from ..bolt import BoltError, AbstractError, ArgumentError, StateError, \
    PermissionError, FileError, formatInteger, round_size, CancelError, \
    SkipError
from ..bolt import GPath, Flags, DataDict, SubProgress, cstrip, \
    deprint, sio, Path
from ..bolt import decode, encode
from ..brec import MreRecord, ModReader, ModError, ModWriter, getObjectIndex, \
    getFormIndices
from ..cint import ObCollection, CBashApi
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
def _delete(itemOrItems, **kwargs):
    confirm = kwargs.pop('confirm', False)
    recycle = kwargs.pop('recycle', True)
    env.shellDelete(itemOrItems, confirm=confirm, recycle=recycle)

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
    _with_ctime = False # HACK ctime may not be needed

    def __init__(self, abs_path, load_cache=False):
        self._abs_path = GPath(abs_path)
        #--Settings cache
        try:
            if self._with_ctime:
                self._file_size, self._file_mod_time, self.ctime = \
                    self.abs_path.size_mtime_ctime()
            else:
                self._file_size, self._file_mod_time = \
                    self.abs_path.size_mtime()
        except OSError:
            self._file_size = self._file_mod_time = 0
            if self._with_ctime: self.ctime = 0

    @property
    def abs_path(self): return self._abs_path

    @abs_path.setter
    def abs_path(self, val): self._abs_path = val

    def needs_update(self, _reset_cache=True):
        try:
            psize, pmtime = self.abs_path.size_mtime()
        except OSError:
            return False # we should not call needs_update on deleted files
        if self._file_size != psize or self._file_mod_time != pmtime:
            if _reset_cache:
                self._reset_cache(psize, pmtime)
            return True
        return False

    def _reset_cache(self, psize, pmtime):
        self._file_size, self._file_mod_time = psize, pmtime

#------------------------------------------------------------------------------
from .ini_files import IniFile, OBSEIniFile, DefaultIniFile, OblivionIni
def BestIniFile(path):
    """:rtype: IniFile"""
    for game_ini in gameInis:
        if path == game_ini.abs_path:
            return game_ini
    INICount = IniFile.formatMatch(path)
    OBSECount = OBSEIniFile.formatMatch(path)
    if INICount >= OBSECount:
        return IniFile(path)
    else:
        return OBSEIniFile(path)

#------------------------------------------------------------------------------
class PluginsFullError(BoltError):
    """Usage Error: Attempt to add a mod to plugins when plugins is full."""
    def __init__(self,message=_(u'Load list is full.')):
        BoltError.__init__(self,message)

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
class _AFileInfo(AFile):
    """Abstract File."""
    _with_ctime = True # HACK ctime may not be needed

    def __init__(self, parent_dir, name, load_cache=False):
        self.dir = GPath(parent_dir)
        self.name = GPath(name) # ghost must be lopped off
        super(_AFileInfo, self).__init__(self.dir.join(name), load_cache)

    ##: DEPRECATED-------------------------------------------------------------
    def getPath(self): return self.abs_path
    @property
    def mtime(self): return self._file_mod_time
    @property
    def size(self): return self._file_size
    #--------------------------------------------------------------------------

    def sameAs(self,fileInfo):
        """Return true if other fileInfo refers to same file as this fileInfo."""
        return ((self.size == fileInfo.size) and
                (self.mtime == fileInfo.mtime) and
                (self.ctime == fileInfo.ctime) and
                (self.name == fileInfo.name))

    def setmtime(self, set_time=0):
        """Sets mtime. Defaults to current value (i.e. reset)."""
        set_time = int(set_time or self.mtime)
        self.abs_path.mtime = set_time
        self._file_mod_time = set_time
        return set_time

    def __repr__(self):
        return self.__class__.__name__ + u"<" + repr(self.name) + u">"

class FileInfo(_AFileInfo):
    """Abstract TES4/TES4GAME File."""

    def __init__(self, parent_dir, name):
        _AFileInfo.__init__(self, parent_dir, name)
        self.header = None
        self.masterNames = tuple()
        self.masterOrder = tuple()
        self.madeBackup = False
        #--Ancillary storage
        self.extras = {}

    def getFileInfos(self):
        """Return one of the FileInfos singletons depending on fileInfo type.
        :rtype: FileInfos"""
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
            return bool(_reEsmExt.search(self.name.s)) and False
    def isInvertedMod(self):
        """Extension indicates esp/esm, but byte setting indicates opposite."""
        return (self.isMod() and self.header and
                self.name.cext != (u'.esp',u'.esm')[int(self.header.flags1) & 1])

    def info_refresh(self):
        self._file_size, self._file_mod_time, self.ctime = \
            self.abs_path.size_mtime_ctime()
        if self.header: self.readHeader() # if not header remains None

    def readHeader(self):
        """Read header from file and set self.header attribute."""
        pass

    def getHeaderError(self):
        """Read header for file. But detects file error and returns that."""
        try: self.readHeader()
        except FileError as error:
            return error.message
        else:
            return None

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
                                   load_order.loIndexCached(
            self.masterOrder[-1]) > load_order.loIndexCached(self.name)
        if self.masterOrder != self.masterNames and loads_before_its_masters:
            return 22
        elif loads_before_its_masters:
            return 21
        elif self.masterOrder != self.masterNames:
            return 20
        else:
            return status

    def writeHeader(self):
        """Writes header to file, overwriting old header."""
        raise AbstractError

    def coCopy(self,oldPath,newPath):
        """Copies co files corresponding to oldPath to newPath.
        Provided so that SaveFileInfo can override for its cofiles."""
        pass

class _BackupMixin(FileInfo): # this should become a real mixin - under #336

    def _doBackup(self,backupDir,forceBackup=False):
        """Creates backup(s) of file, places in backupDir."""
        #--Skip backup?
        if not self in self.getFileInfos().values(): return
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
        backupDir = self.backup_dir
        self._doBackup(backupDir,forceBackup)
        #--Done
        self.madeBackup = True

    def _backup_paths(self):
        return [(self.backup_dir.join(self.name), self.getPath())]

    def revert_backup(self):
        backup_paths = self._backup_paths()
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

class ModInfo(_BackupMixin, FileInfo):
    """An esp/m file."""

    def __init__(self, parent_dir, name):
        self.isGhost = endsInGhost = (name.cs[-6:] == u'.ghost')
        if endsInGhost: name = GPath(name.s[:-6])
        else: # refreshFile() path
            absPath = GPath(parent_dir).join(name)
            self.isGhost = \
                not absPath.exists() and (absPath + u'.ghost').exists()
        FileInfo.__init__(self, parent_dir, name)

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
            crc = path.crc
            if crc != modInfos.table.getItem(self.name,'crc'):
                modInfos.table.setItem(self.name,'crc',crc)
                modInfos.table.setItem(self.name,'ignoreDirty',False)
            modInfos.table.setItem(self.name,'crc_mtime',mtime)
            modInfos.table.setItem(self.name,'crc_size',size)
        else:
            crc = modInfos.table.getItem(self.name,'crc')
        return crc

    def setmtime(self, set_time=0):
        """Sets mtime. Defaults to current value (i.e. reset)."""
        set_time = FileInfo.setmtime(self, set_time)
        # Prevent re-calculating the File CRC
        modInfos.table.setItem(self.name,'crc_mtime', set_time)

    # Ghosting and ghosting related overrides ---------------------------------
    def sameAs(self, fileInfo):
        try:
            return FileInfo.sameAs(self, fileInfo) and (
                self.isGhost == fileInfo.isGhost)
        except AttributeError: #fileInfo has no isGhost attribute - not ModInfo
            return False

    @property
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

    def getDirtyMessage(self):
        """Returns a dirty message from LOOT."""
        if modInfos.table.getItem(self.name,'ignoreDirty',False):
            return False,u''
        return configHelpers.getDirtyMessage(self.name)

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
    def txt_status(self):
        if load_order.isActiveCached(self.name): return _(u'Active')
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
        return modInfos.hasBadMasterNames(self.name)

    def isMissingStrings(self):
        return modInfos.isMissingStrings(self.name)

    def isExOverLoaded(self):
        """True if belongs to an exclusion group that is overloaded."""
        maExGroup = reExGroup.match(self.name.s)
        if not (load_order.isActiveCached(self.name) and maExGroup):
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

    def getStringsPaths(self,language=u'English'):
        """If Strings Files are available as loose files, just point to
        those, otherwise extract needed files from BSA if needed."""
        baseDirJoin = self.getPath().head.join
        files = []
        sbody,ext = self.name.sbody,self.name.ext
        for _dir, join, format_str in bush.game.esp.stringsFiles:
            fname = format_str % {'body': sbody, 'ext': ext,
                                  'language': language}
            assetPath = GPath(u'').join(*join).join(fname)
            files.append(assetPath)
        extract = set()
        paths = set()
        #--Check for Loose Files first
        for filepath in files:
            loose = baseDirJoin(filepath)
            if not loose.exists():
                extract.add(filepath)
            else:
                paths.add(loose)
        #--If there were some missing Loose Files
        if extract:
            bsaPaths = modInfos.extra_bsas(self)
            bsaFiles = {}
            targetJoin = dirs['bsaCache'].join
            for filepath in extract:
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
                    if bsaFile.IsAssetInBSA(filepath):
                        target = targetJoin(path.tail)
                        #--Extract
                        try:
                            bsaFile.ExtractAsset(filepath,target)
                        except libbsa.LibbsaError as e:
                            raise ModError(self.name,u"Could not extract Strings File from '%s': %s" % (path.stail,e))
                        paths.add(target.join(filepath))
                        found = True
                if not found:
                    raise ModError(self.name,u"Could not locate Strings File '%s'" % filepath.stail)
        return paths

    def hasResources(self):
        """Returns (hasBsa,hasVoices) booleans according to presence of
        corresponding resources."""
        voicesPath = self.dir.join(u'Sound',u'Voice',self.name)
        return [self.hasBsa(),voicesPath.exists()]

#------------------------------------------------------------------------------
class INIInfo(FileInfo):
    """DEPRECATED ! IniInfos should contain IniFiles directly !!"""
    def __init__(self,*args,**kwdargs):
        FileInfo.__init__(self,*args,**kwdargs) ##: has a lot of stuff that has nothing to do with inis !
        self._status = None
        self.__ini_file = None

    @property
    def ini_info_file(self): # init once when we need it
        if self.__ini_file is None:
            self.__ini_file = BestIniFile(self.getPath())
        return self.__ini_file

    @ini_info_file.setter
    def ini_info_file(self, val):
        self.__ini_file = val

    @property
    def tweak_status(self):
        if self._status is None: self.getStatus()
        return self._status

    @property
    def is_default_tweak(self):
        return isinstance(self.ini_info_file, DefaultIniFile)

    def getFileInfos(self): return iniInfos

    def read_ini_lines(self): return self.ini_info_file.read_ini_lines()

    _obse_ini_types = {OBSEIniFile}
    def _incompatible(self, other):
        if type(self.ini_info_file) not in self._obse_ini_types:
            return type(other) in self._obse_ini_types
        return type(other) not in self._obse_ini_types

    def getStatus(self, target_ini=None):
        """Returns status of the ini tweak:
        20: installed (green with check)
        15: mismatches (green with dot) - mismatches are with another tweak from same installer that is applied
        10: mismatches (yellow)
        0: not installed (green)
        -10: invalid tweak file (red).
        Also caches the value in self._status"""
        infos = iniInfos
        target_ini = target_ini or infos.ini
        tweak_settings = self.ini_info_file.getSettings()
        if self._incompatible(target_ini) or not tweak_settings:
            self._status = -10
            return -10
        match = False
        mismatch = 0
        ini_settings = target_ini.getSettings()
        this = infos.table.getItem(self.getPath().tail, 'installer')
        for section_key in tweak_settings:
            if section_key not in ini_settings:
                self._status = -10
                return -10
            target_section = ini_settings[section_key]
            tweak_section = tweak_settings[section_key]
            for item in tweak_section:
                if item not in target_section:
                    self._status = -10
                    return -10
                if tweak_section[item][0] != target_section[item][0]:
                    if mismatch < 2:
                        # Check to see if the mismatch is from another
                        # ini tweak that is applied, and from the same installer
                        mismatch = 2
                        if this is None: continue
                        for name, ini_info in infos.iteritems():
                            if self is ini_info: continue
                            other = infos.table.getItem(name, 'installer')
                            if this != other: continue
                            # It's from the same installer
                            other_ini_file = ini_info.ini_info_file
                            if self._incompatible(other_ini_file): continue
                            value = other_ini_file.getSetting(
                                section_key, item, None)
                            if value == target_section[item][0]:
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

    def reset_status(self): self._status = None

    def listErrors(self):
        """Returns ini tweak errors as text."""
        ini_infos_ini = iniInfos.ini
        text = [u'%s:' % self.getPath().stail]
        if self._incompatible(ini_infos_ini):
            text.append(u' '+_(u'Format mismatch:') + u'\n  ')
            if type(self.ini_info_file) in self._obse_ini_types:
                text.append(_(u'Target format: INI') + u'\n  ' +
                            _(u'Tweak format: Batch Script'))
            else:
                text.append(_(u'Target format: Batch Script') + u'\n  ' +
                            _(u'Tweak format: INI'))
        else:
            tweak_settings = self.ini_info_file.getSettings()
            ini_settings = ini_infos_ini.getSettings()
            if len(tweak_settings) == 0:
                if type(self.ini_info_file) not in self._obse_ini_types:
                    text.append(_(u' No valid INI format lines.'))
                else:
                    text.append(_(u' No valid Batch Script format lines.'))
            else:
                for key in tweak_settings:
                    if key not in ini_settings:
                        text.append(u' [%s] - %s' % (key,_(u'Invalid Header')))
                    else:
                        for item in tweak_settings[key]:
                            if item not in ini_settings[key]:
                                text.append(u' [%s] %s' % (key, item))
        if len(text) == 1:
            text.append(u' None')
        with sio() as out:
            log = bolt.LogFile(out)
            for line in text:
                log(line)
            return bolt.winNewLines(log.out.getvalue())

#------------------------------------------------------------------------------
class SaveInfo(_BackupMixin, FileInfo):
    def getFileInfos(self): return saveInfos

    def getStatus(self):
        status = FileInfo.getStatus(self)
        masterOrder = self.masterOrder
        #--File size?
        if status > 0 or len(masterOrder) > len(load_order.activeCached()):
            return status
        #--Current ordering?
        if masterOrder != load_order.activeCached()[:len(masterOrder)]:
            return status
        elif masterOrder == load_order.activeCached():
            return -20
        else:
            return -10

    def readHeader(self):
        """Read header from file and set self.header attribute."""
        try:
            self.header = SaveHeader(self.getPath())
            #--Master Names/Order
            self.masterNames = tuple(self.header.masters)
            self.masterOrder = tuple() #--Reset to empty for now
        except struct.error as rex:
            raise SaveFileError(self.name,u'Struct.error: %s' % rex)

    def coCopy(self,oldPath,newPath):
        """Copies co files corresponding to oldPath to newPath."""
        CoSaves(oldPath).copy(newPath)

    def coSaves(self):
        """Returns CoSaves instance corresponding to self."""
        return CoSaves(self.getPath())

    def _backup_paths(self):
        save_paths = super(SaveInfo, self)._backup_paths()
        save_paths.extend(CoSaves.get_new_paths(*save_paths[0]))
        return save_paths

#------------------------------------------------------------------------------
from . import bsa_files
from .bsa_files import BSAError

try:
    _bsa_type = bsa_files.get_bsa_type(bush.game.fsName)
except AttributeError:
    _bsa_type = bsa_files.ABsa

class BSAInfo(_BackupMixin, FileInfo, _bsa_type):
    _default_mtime = time.mktime(
        time.strptime(u'01-01-2006 00:00:00', u'%m-%d-%Y %H:%M:%S'))

    def __init__(self, parent_dir, bsa_name):
        super(BSAInfo, self).__init__(parent_dir, bsa_name)
        self._reset_bsa_mtime()

    def getFileInfos(self): return bsaInfos

    def needs_update(self, _reset_cache=True):
        changed = super(BSAInfo, self).needs_update(_reset_cache)
        self._reset_bsa_mtime()
        return changed

    def _reset_cache(self, psize, pmtime):
        super(BSAInfo, self)._reset_cache(pmtime, psize)
        self._assets = self.__class__._assets

    def _reset_bsa_mtime(self):
        if bush.game.allow_reset_bsa_timestamps and inisettings[
            'ResetBSATimestamps']:
            if self._file_mod_time != self._default_mtime:
                self.setmtime(self._default_mtime)

#------------------------------------------------------------------------------
class TrackedFileInfos(DataDict):
    """Similar to FileInfos, but doesn't use a PickleDict to save information
       about the tracked files at all.

       Uses absolute paths - the caller is responsible for passing them.
       """
    # DEPRECATED: hack introduced to track BAIN installed files
    tracked_dir = GPath(u'') # a mess with paths

    def __init__(self):
        self.data = {}

    def refreshTracked(self):
        changed = set()
        for name, tracked in self.items():
            fileInfo = _AFileInfo(self.tracked_dir, name)
            filePath = fileInfo.getPath()
            if not filePath.exists(): # untrack - runs on first run !!
                self.pop(name, None)
                changed.add(name)
            elif not fileInfo.sameAs(tracked):
                self[name] = fileInfo
                changed.add(name)
        return changed

    def track(self, absPath): # cf FileInfos.refreshFile
        fileInfo = _AFileInfo(self.tracked_dir, absPath)
        # fileInfo.readHeader() #ModInfo: will blow if absPath doesn't exist
        self[absPath] = fileInfo

#------------------------------------------------------------------------------
class _DataStore(DataDict):
    store_dir = empty_path # where the datas sit, static except for SaveInfos

    def delete(self, itemOrItems, **kwargs): raise AbstractError
    def delete_Refresh(self, deleted, check_existence=False):
        # Yak - absorb in refresh - add deleted parameter
        if check_existence:
            deleted = set(
                d for d in deleted if not self.store_dir.join(d).exists())
        return deleted
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

class FileInfos(_DataStore):
    """Common superclass for mod, ini, saves and bsa infos."""
    ##: we need a common API for this and TankData...
    file_pattern = None # subclasses must define this !
    def _initDB(self, dir_):
        self.store_dir = dir_ #--Path
        self.store_dir.makedirs()
        self.bash_dir.makedirs() # self.dir may need be set
        self.data = {} # populated in refresh ()
        self.corrupted = {} #--errorMessage = corrupted[fileName]
        # the type of the table keys is always bolt.Path
        self.table = bolt.Table(
            bolt.PickleDict(self.bash_dir.join(u'Table.dat')))

    def __init__(self, dir_, factory=FileInfo):
        """Init with specified directory and specified factory type."""
        self.factory=factory
        self._initDB(dir_)

    #--Refresh File
    def refreshFile(self,fileName):
        try:
            fileInfo = self.factory(self.store_dir, fileName)
            fileInfo.readHeader()
            self[fileName] = fileInfo
        except FileError as error:
            self.corrupted[fileName] = error.message
            self.pop(fileName, None)
            raise

    #--Refresh
    def _names(self): # performance intensive
        return {x for x in self.store_dir.list() if
                self.store_dir.join(x).isfile() and self.rightFileType(x)}

    def refresh(self, refresh_infos=True):
        """Refresh from file directory."""
        oldNames = set(self.data) | set(self.corrupted)
        newNames = set()
        _added = set()
        _updated = set()
        names = self._names()
        for name in names:
            fileInfo = self.factory(self.store_dir, name)
            name = fileInfo.name #--Might have '.ghost' lopped off.
            if name in newNames: continue #--Must be a ghost duplicate. Ignore it.
            oldInfo = self.get(name) # None if name was in corrupted
            isAdded = name not in oldNames
            dont_recheck = isUpdated = False
            if oldInfo is not None:
                isUpdated = not isAdded and not fileInfo.sameAs(oldInfo)
            elif not isAdded: # known corrupted - recheck
                dont_recheck = isUpdated = not fileInfo.getHeaderError()
            if isAdded or isUpdated:
                errorMessage = not dont_recheck and fileInfo.getHeaderError()
                if errorMessage:
                    self.corrupted[name] = errorMessage
                    self.pop(name,None)
                    continue
                else:
                    self[name] = fileInfo
                    self.corrupted.pop(name,None)
                    if isAdded: _added.add(name)
                    elif isUpdated: _updated.add(name)
            newNames.add(name) # will add known corrupted too
        _deleted = oldNames - newNames
        for name in _deleted:
            # Can run into multiple pops if one of the files is corrupted
            self.pop(name, None); self.corrupted.pop(name, None)
        if _deleted:
            # items deleted outside Bash
            for d in set(self.table.keys()) &  set(_deleted):
                del self.table[d]
        change = bool(_added) or bool(_updated) or bool(_deleted)
        if not change: return change
        return _added, _updated, _deleted

    #--Right File Type?
    @classmethod
    def rightFileType(cls, fileName):
        """Check if the filetype (extension) is correct for subclass.
        :type fileName: bolt.Path | basestring
        :rtype: _sre.SRE_Match | None
        """
        return cls.file_pattern.search(u'%s' % fileName)

    def _get_rename_paths(self, oldName, newName):
        return [(self[oldName].getPath(), self.store_dir.join(newName))]

    #--Rename
    def _rename_operation(self, oldName, newName):
        """Renames member file from oldName to newName."""
        #--Update references
        fileInfo = self[oldName]
        #--File system
        try:
            if fileInfo.isGhost: newName += u'.ghost'
        except AttributeError: pass # not a mod info
        super(FileInfos, self)._rename_operation(oldName, newName)
        #--FileInfo
        fileInfo.name = newName
        fileInfo.abs_path = self.store_dir.join(newName)
        #--FileInfos
        self[newName] = self[oldName]
        del self[oldName]
        self.table.moveRow(oldName,newName)
        #--Done
        fileInfo.madeBackup = False ##: #292

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
        backBase = self.bash_dir.join(u'Backups')
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

    def delete_Refresh(self, deleted, check_existence=False):
        deleted = super(FileInfos, self).delete_Refresh(deleted,
                                                        check_existence)
        if not deleted: return deleted
        for name in deleted:
            self.pop(name, None); self.corrupted.pop(name, None)
            self.table.pop(name, None)
        return deleted

    #--Move
    def move_info(self, fileName, destDir):
        """Moves member file to destDir. Will overwrite! The client is
        responsible for calling delete_Refresh of the data store."""
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

    def save(self):
        # items deleted outside Bash
        for deleted in set(self.table.keys()) - set(self.keys()):
            del self.table[deleted]
        self.table.save()

#------------------------------------------------------------------------------
class INIInfos(FileInfos):
    """:type _ini: IniFile
    :type data: dict[bolt.Path, IniInfo]"""
    file_pattern = re.compile(ur'\.ini$', re.I | re.U)
    try:
        _default_tweaks = dict((GPath(k), DefaultIniFile(k, v)) for k, v in
                               bush.game.default_tweaks.iteritems())
    except AttributeError:
        _default_tweaks = {}

    def __init__(self):
        FileInfos.__init__(self, dirs['tweaks'], INIInfo)
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
            path = _target_inis[ini_name]
            # If user started with non-translated, 'Browse...'
            # will still be in here, but in English.  It wont get picked
            # up by the previous check, so we'll just delete any non-Path
            # objects.  That will take care of it.
            if not isinstance(path,bolt.Path) or not path.isfile():
                for iFile in gameInis: # don't remove game inis even if missing
                    if iFile.abs_path == path: continue
                del _target_inis[ini_name]
                if ini_name is previous_ini:
                    choice, previous_ini = -1, None
        csChoices = [x.lower() for x in _target_inis]
        for iFile in gameInis: # add the game inis even if missing
            if iFile.abs_path.tail.cs not in csChoices:
                _target_inis[iFile.abs_path.stail] = iFile.abs_path
        if _(u'Browse...') not in _target_inis:
            _target_inis[_(u'Browse...')] = None
        settings['bash.ini.choices'] = _target_inis
        if previous_ini: choice = _target_inis.keys().index(previous_ini)
        settings['bash.ini.choice'] = choice
        if choice > 0:
            self.ini = _target_inis.values()[choice]
        else: self.ini = oblivionIni.abs_path

    @property
    def ini(self):
        return self._ini
    @ini.setter
    def ini(self, ini_path):
        """:type ini_path: bolt.Path"""
        if self._ini is not None and self._ini.abs_path == ini_path:
            return # nothing to do
        for iFile in gameInis:
            if iFile.abs_path == ini_path:
                self._ini = iFile
                break
        else:
            self._ini = BestIniFile(ini_path)
        for ini_info in self.itervalues(): ini_info.reset_status()

    def _refresh_infos(self):
        """Refresh from file directory."""
        oldNames=set(n for n, v in self.iteritems() if not v.is_default_tweak)
        _added = set()
        _updated = set()
        newNames = self._names()
        for name in newNames:
            oldInfo = self.get(name) # None if name was added
            if oldInfo is not None:
                if oldInfo.ini_info_file.needs_update(): _updated.add(name)
            else: # added
                oldInfo = self.factory(self.store_dir, name)
                _added.add(name)
            self[name] = oldInfo
        _deleted = oldNames - newNames
        for name in _deleted:
            self.pop(name, None)
            # items deleted outside Bash, otherwise delete_Refresh did this
            self.table.pop(name, None)
        # re-add default tweaks
        for k in self.keys():
            if k not in newNames: del self[k]
        set_keys = set(self.keys())
        for k, d in self._default_tweaks.iteritems():
            if k not in set_keys:
                default_info = self.setdefault(k, self.factory(u'', k))
                default_info.ini_info_file = d
                if k in _deleted: # we restore default over copy
                    _updated.add(k) # no need to reset status as is None
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
        elif _updated:
            for ini_info in _updated: self[ini_info].reset_status()
        # no need to reset status for added as it is already None
        change = bool(_added) or bool(_updated) or bool(_deleted) or changed
        if not change: return change
        return _added, _updated, _deleted, changed

    @property
    def bash_dir(self): return dirs['modsBash'].join(u'INI Data')

    def delete_Refresh(self, deleted, check_existence=False):
        deleted = FileInfos.delete_Refresh(self, deleted, check_existence)
        if not deleted: return deleted
        set_keys = set(self.keys())
        for k, d in self._default_tweaks.iteritems(): # readd default tweaks
            if k not in set_keys:
                default_info = self.setdefault(k, self.factory(u'', k))
                default_info.ini_info_file = d
        return deleted

    def get_tweak_lines_infos(self, tweakPath):
        tweak_lines = self[tweakPath].read_ini_lines()
        return self._ini.get_lines_infos(tweak_lines)

    def open_or_copy(self, tweak):
        info = self[tweak] # type: INIInfo
        if info.is_default_tweak:
            with open(self.store_dir.join(tweak).s, 'w') as ini_file:
                ini_file.write('\n'.join(info.ini_info_file.read_ini_lines()))
            self[tweak] = self.factory(self.store_dir, tweak)
            return True # refresh
        else:
            info.getPath().start()
            return False

    def duplicate_ini(self, tweak, new_tweak):
        """Duplicate tweak into new_tweak, copying current target settings"""
        if not new_tweak: return False
        info = self[tweak] # type: INIInfo
        with open(self.store_dir.join(new_tweak).s, 'w') as ini_file:
            ini_file.write('\n'.join(info.ini_info_file.read_ini_lines()))
        self[new_tweak.tail] = self.factory(self.store_dir, new_tweak)
        # Now edit it with the values from the target INI
        new_ini_file = self[new_tweak.tail].ini_info_file
        new_tweak_settings = copy.copy(new_ini_file.getSettings())
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
        new_ini_file.saveSettings(new_tweak_settings)
        return True

def _lo_cache(lord_func):
    """Decorator to make sure I sync modInfos cache with load_order cache
    whenever I change (or attempt to change) the latter."""
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
        self.size_voVersion = bolt.invertDict(self.version_voSize)
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
        return u'%02X' % (load_order.activeIndexCached(mod),) \
            if load_order.isActiveCached(mod) else u''

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
        names = FileInfos._names(self)
        return sorted(names, key=lambda x: x.cext == u'.ghost')

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
            with balt.Progress(_(u'Mark Mergeable')+u' '*30) as progress:
                progress.setFull(len(scanList))
                self.rescanMergeable(scanList,progress)
        hasChanged += bool(scanList or difMergeable)
        return bool(hasChanged) or lo_changed

    _plugin_inis = OrderedDict() # cache active mod inis in active mods order
    def _refresh_mod_inis(self):
        if not bush.game.supports_mod_inis: return
        iniPaths = (self[m].getIniPath() for m in load_order.activeCached())
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
                if load_order.isActiveCached(fileName):
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
        bad = set(fileName for fileName in self.keys() if
                  self.isMissingStrings(fileName))
        new = bad - oldBad
        self.missing_strings = bad
        self.new_missing_strings = new
        return bool(new)

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
                modGhost = toGhost and not load_order.isActiveCached(mod) \
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
            if modInfo.header.author == u"BASHED PATCH":
                self.bashed_patches.add(modName)
        #--Refresh overLoaded
        self.exGroup_mods.clear()
        active_set = set(load_order.activeCached())
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
        #--Add known/unchanged and esms
        for mpath, modInfo in self.iteritems():
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

    def rescanMergeable(self,names,progress,doCBash=None):
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
                    canMerge = is_mergeable(fileInfo)
                except Exception as e:
                    # deprint (_(u"Error scanning mod %s (%s)") % (fileName, e))
                    # canMerge = False #presume non-mergeable.
                    raise
            result[fileName] = canMerge
            # noinspection PySimplifyBooleanCheck
            if canMerge == True:
                self.mergeable.add(fileName)
                mod_mergeInfo[fileName] = (fileInfo.size,True)
            else:
                if canMerge == u'\n.    '+_(u"Has 'NoMerge' tag."):
                    mod_mergeInfo[fileName] = (fileInfo.size,True)
                    self.mergeable.add(fileName)
                    tagged_no_merge.add(fileName)
                else:
                    mod_mergeInfo[fileName] = (fileInfo.size,False)
                    self.mergeable.discard(fileName)
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
    def refreshFile(self,fileName):
        try:
            FileInfos.refreshFile(self,fileName)
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
                masters = set(load_order.activeCached())
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
            lindex = lambda t: load_order.loIndexCached(t[0])
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
    def lo_activate(self, fileName, doSave=True, modSet=None, children=None,
                    _activated=None):
        """Mutate _active_wip cache then save if needed."""
        if _activated is None: _activated = set()
        try:
            if len(self._active_wip) == 255:
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
                    self.lo_activate(master, False, modSet, children, _activated)
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
        toActivate = set(load_order.activeCached())
        try:
            def _add_to_activate(m):
                if not m in toActivate:
                    self.lo_activate(m, doSave=False)
                    toActivate.add(m)
            mods = load_order.get_ordered(self.keys())
            # first select the bashed patch(es) and their masters
            for mod in mods: ##: usually results in exclusion group violation
                if self.isBP(mod): _add_to_activate(mod)
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
        modInfo = self[modName]
        if modInfo.header.flags1.hasStrings:
            language = oblivionIni.get_ini_language()
            sbody,ext = modName.sbody,modName.ext
            bsaPaths = self.extra_bsas(modInfo, existing=False)
            for dir_, join, format_str in bush.game.esp.stringsFiles:
                fname = format_str % {'body': sbody, 'ext': ext,
                                      'language': language}
                assetPath = empty_path.join(*join).join(fname)
                # Check loose files first
                if dirs[dir_].join(assetPath).exists():
                    continue
                # Check in BSA's next
                found = False
                for path in bsaPaths:
                    try:
                        bsa_info = bsaInfos[path.tail] # type: BSAInfo
                        if bsa_info.has_asset(assetPath):
                            found = True
                            break
                    except KeyError: # not existing or corrupted
                        continue
                if not found:
                    return True
        return False

    def _ini_files(self):
        iniFiles = self._plugin_inis.values() # in active order
        iniFiles.reverse() # later loading inis override previous settings
        iniFiles.append(oblivionIni)
        return iniFiles

    def extra_bsas(self, mod_info, existing=True):
        """Return a list of (existing) bsa paths to get assets from.
        :rtype: list[bolt.Path]
        """
        if mod_info.name.s in bush.game.vanilla_string_bsas:
            bsaPaths = map(dirs['mods'].join, bush.game.vanilla_string_bsas[
                mod_info.name.s])
        else:
            bsaPaths = [mod_info.getBsaPath()] # first check bsa with same name
            for iniFile in self._ini_files():
                for key in (u'sResourceArchiveList', u'sResourceArchiveList2'): ##: per game keys !
                    extraBsa = iniFile.getSetting(u'Archive', key, u'').split(u',')
                    extraBsa = (x.strip() for x in extraBsa)
                    extraBsa = [dirs['mods'].join(x) for x in extraBsa if x]
                    bsaPaths.extend(extraBsa)
        return [x for x in bsaPaths if not existing or x.isfile()]

    def hasBadMasterNames(self,modName):
        """True if there mod has master's with unencodable names."""
        masters = self[modName].header.masters
        try:
            for x in masters: x.s.encode('cp1252')
            return False
        except UnicodeEncodeError:
            return True

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
        isSelected = load_order.isActiveCached(oldName)
        if isSelected: self.lo_deactivate(oldName, doSave=False) # will save later
        FileInfos._rename_operation(self, oldName, newName)
        # rename in load order caches
        oldIndex = self._lo_wip.index(oldName)
        self._lo_caches_remove_mods([oldName])
        self._lo_wip.insert(oldIndex, newName)
        if isSelected: self.lo_activate(newName, doSave=False)
        # Save to disc (load order and plugins.txt)
        self.cached_lo_save_all()

    def delete(self, fileName, **kwargs):
        """Delete member file."""
        if not isinstance(fileName, (set, list)): fileName = {fileName}
        for f in fileName:
            if f.s in bush.game.masterFiles: raise bolt.BoltError(
                u"Cannot delete the game's master file(s).")
        self.lo_deactivate(fileName, doSave=False)
        FileInfos.delete(self, fileName, **kwargs)

    def delete_Refresh(self, deleted, check_existence=False):
        # adapted from refresh() (avoid refreshing from the data directory)
        deleted = FileInfos.delete_Refresh(self, deleted, check_existence)
        if not deleted: return
        # temporarily track deleted mods so BAIN can update its UI
        for d in map(self.store_dir.join, deleted): # we need absolute paths
            InstallersData.miscTrackedFiles.track(d)
        self._lo_caches_remove_mods(deleted)
        self.cached_lo_save_all()
        self._refreshBadNames()
        self._refreshInfoLists()
        self._refreshMissingStrings()
        self._refreshMergeable()

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
        author = self[name].header.author
        if author:
            authorDir = dest_dir.join(author)
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

    def setOblivionVersion(self,newVersion):
        """Swaps Oblivion.esm to to specified version."""
        #--Old info
        baseName = self.masterName
        newSize = self.version_voSize[newVersion]
        oldSize = self[baseName].size
        if newSize == oldSize: return
        if oldSize not in self.size_voVersion:
            raise StateError(u"Can't match current main ESM to known version.")
        oldName = GPath(baseName.sbody+u'_'+self.size_voVersion[oldSize]+u'.esm')
        if self.store_dir.join(oldName).exists():
            raise StateError(u"Can't swap: %s already exists." % oldName)
        newName = GPath(baseName.sbody+u'_'+newVersion+u'.esm')
        if newName not in self.data:
            raise StateError(u"Can't swap: %s doesn't exist." % newName)
        #--Rename
        baseInfo = self[baseName]
        newInfo = self[newName]
        basePath = baseInfo.getPath()
        newPath = newInfo.getPath()
        oldPath = self.store_dir.join(oldName)
        try:
            basePath.moveTo(oldPath)
        except OSError as werr:
            while werr.errno == errno.EACCES and self._retry(basePath,oldPath):
                try:
                    basePath.moveTo(oldPath)
                except OSError as werr:
                    continue
                break
            else:
                raise
        try:
            newPath.moveTo(basePath)
        except OSError as werr:
            while werr.errno == errno.EACCES and self._retry(newPath,basePath):
                try:
                    newPath.moveTo(basePath)
                except OSError as werr:
                    continue
                break
            else:
                #Undo any changes
                oldPath.moveTo(basePath)
                raise
        basePath.mtime = baseInfo.mtime
        oldPath.mtime = newInfo.mtime
        if newInfo.isGhost:
            oldInfo = ModInfo(self.store_dir, oldName)
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
        FileInfos.__init__(self, dirs['saveBase'].join(self.localSave), SaveInfo)
        # Save Profiles database
        self.profiles = bolt.Table(bolt.PickleDict(
            dirs['saveBase'].join(u'BashProfiles.dat')))

    @property
    def bash_dir(self): return self.store_dir.join(u'Bash')

    def refresh(self, refresh_infos=True):
        self._refreshLocalSave()
        return refresh_infos and FileInfos.refresh(self)

    def delete(self, fileName, **kwargs):
        """Deletes savefile and associated pluggy file."""
        FileInfos.delete(self, fileName, **kwargs)
        kwargs['confirm'] = False # ask only on save deletion
        kwargs['backupDir'] = self.bash_dir.join('Backups')
        CoSaves(self.store_dir, fileName).delete(**kwargs)

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
        if not oblivionIni.ask_create_game_ini(msg=_(
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

    def __init__(self): FileInfos.__init__(self, dirs['mods'], BSAInfo)

    @property
    def bash_dir(self): return dirs['modsBash'].join(u'BSA Data')

    def refresh(self, refresh_infos=True):
        """Refresh from file directory."""
        oldNames = set(self.data) | set(self.corrupted)
        _added = set()
        _updated = set()
        newNames = self._names()
        for name in newNames:
            oldInfo = self.get(name) # None if name was in corrupted or new one
            isAdded = name not in oldNames
            isUpdated = False
            try:
                if oldInfo is not None:
                    isUpdated = not isAdded and oldInfo.needs_update()
                else: # added or known corrupted, get a new info
                    oldInfo = self.factory(self.store_dir, name)
                self[name] = oldInfo
                self.corrupted.pop(name,None)
                if isAdded: _added.add(name)
                elif isUpdated: _updated.add(name)
            except BSAError as e: # old still corrupted, or new(ly) corrupted
                self.corrupted[name] = e.message
                self.pop(name, None)
                continue
        _deleted = oldNames - newNames
        for name in _deleted:
            # Can run into multiple pops if one of the files is corrupted
            self.pop(name, None); self.corrupted.pop(name, None)
            # items deleted outside Bash, otherwise delete_Refresh did this
            self.table.pop(name, None)
        change = bool(_added) or bool(_updated) or bool(_deleted)
        if not change: return change
        return _added, _updated, _deleted

#------------------------------------------------------------------------------
class PeopleData(_DataStore):
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

    def delete(self, key, **kwargs):
        """Delete entry."""
        del self[key]
        self.hasChanged = True

    def delete_Refresh(self, deleted, check_existence=False): pass

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
class ScreensData(_DataStore):
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

    def delete(self, fileName, **kwargs):
        """Deletes member file."""
        dirJoin = self.store_dir.join
        if isinstance(fileName,(list,set)):
            filePath = [dirJoin(file) for file in fileName]
        else:
            filePath = [dirJoin(fileName)]
        _delete(filePath, **kwargs)
        for item in filePath:
            if not item.exists(): del self[item.tail]

    def delete_Refresh(self, deleted, check_existence=False): self.refresh()

    def _rename_operation(self, oldName, newName):
        super(ScreensData, self)._rename_operation(oldName, newName)
        self[newName] = self[oldName]
        del self[oldName]

#------------------------------------------------------------------------------
os_sep = unicode(os.path.sep)
class Installer(object):
    """Object representing an installer archive, its user configuration, and
    its installation state."""

    type_string = _(u'Unrecognized')
    #--Member data
    persistent = ('archive', 'order', 'group', 'modified', 'size', 'crc',
        'fileSizeCrcs', 'type', 'isActive', 'subNames', 'subActives',
        'dirty_sizeCrc', 'comments', 'extras_dict', 'packageDoc', 'packagePic',
        'src_sizeCrcDate', 'hasExtraData', 'skipVoices', 'espmNots', 'isSolid',
        'blockSize', 'overrideSkips', 'remaps', 'skipRefresh', 'fileRootIdex')
    volatile = ('data_sizeCrc', 'skipExtFiles', 'skipDirFiles', 'status',
        'missingFiles', 'mismatchedFiles', 'project_refreshed',
        'mismatchedEspms', 'unSize', 'espms', 'underrides', 'hasWizard',
        'espmMap', 'hasReadme', 'hasBCF', 'hasBethFiles', '_dir_dirs_files')
    __slots__ = persistent + volatile
    #--Package analysis/porting.
    docDirs = {u'screenshots'}
    #--Will be skipped even if hasExtraData == True (bonus: skipped also on
    # scanning the game Data directory)
    dataDirsMinus = {u'bash', u'--'}
    try:
        reDataFile = re.compile(ur'(\.(esp|esm|' + bush.game.bsa_extension +
                                ur'|ini))$', re.I | re.U)
    except AttributeError: # YAK
        reDataFile = re.compile(ur'(\.(esp|esm|bsa|ini))$', re.I | re.U)
    docExts = {u'.txt', u'.rtf', u'.htm', u'.html', u'.doc', u'.docx', u'.odt',
               u'.mht', u'.pdf', u'.css', u'.xls', u'.xlsx', u'.ods', u'.odp',
               u'.ppt', u'.pptx'}
    reReadMe = re.compile(
        ur'^.*?([^\\]*)(read[ _]?me|lisez[ _]?moi)([^\\]*)'
        ur'(' +ur'|'.join(docExts) + ur')$', re.I | re.U)
    skipExts = {u'.exe', u'.py', u'.pyc', u'.7z', u'.zip', u'.rar', u'.db',
                u'.ace', u'.tgz', u'.tar', u'.gz', u'.bz2', u'.omod',
                u'.fomod', u'.tb2', u'.lzma', u'.manifest'}
    skipExts.update(set(readExts))
    scriptExts = {u'.txt', u'.ini', u'.cfg'}
    commonlyEditedExts = scriptExts | {u'.xml'}
    #--Regular game directories - needs update after bush.game has been set
    dataDirsPlus = docDirs | {u'bash patches', u'ini tweaks', u'docs'}
    @staticmethod
    def init_bain_dirs():
        """Initialize BAIN data directories on a per game basis."""
        Installer.dataDirsPlus |= bush.game.dataDirs | bush.game.dataDirsPlus
        InstallersData.installers_dir_skips.update(
            {dirs['converters'].stail.lower(), u'bash'})
        user_skipped = inisettings['SkippedBashInstallersDirs'].split(u'|')
        InstallersData.installers_dir_skips.update(
            skipped.lower() for skipped in user_skipped if skipped)

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

    tempList = Path.baseTempDir().join(u'WryeBash_InstallerTempList.txt')

    #--Class Methods ----------------------------------------------------------
    @staticmethod
    def getGhosted():
        """Returns map of real to ghosted files in mods directory."""
        dataDir = dirs['mods']
        ghosts = [x for x in dataDir.list() if x.cs[-6:] == u'.ghost']
        return dict((x.root,x) for x in ghosts if not dataDir.join(x).root.exists())

    @staticmethod
    def sortFiles(files, __split=os.path.split):
        """Utility function. Sorts files by directory, then file name."""
        sort_keys_dict = dict((x, __split(x.lower())) for x in files)
        return sorted(files, key=sort_keys_dict.__getitem__)

    @staticmethod
    def final_update(new_sizeCrcDate, old_sizeCrcDate, pending, pending_size,
                      progress, recalculate_all_crcs, rootName):
        """Clear old_sizeCrcDate and update it with new_sizeCrcDate after
        calculating crcs for pending."""
        #--Force update?
        if recalculate_all_crcs:
            pending.update(new_sizeCrcDate)
            pending_size += sum(x[0] for x in new_sizeCrcDate.itervalues())
        changed = bool(pending) or (len(new_sizeCrcDate) != len(old_sizeCrcDate))
        #--Update crcs?
        Installer.calc_crcs(pending, pending_size, rootName,
                            new_sizeCrcDate, progress)
        old_sizeCrcDate.clear()
        for rpFile, (size, crc, date, _asFile) in new_sizeCrcDate.iteritems():
            old_sizeCrcDate[rpFile] = (size, crc, date)
        return changed

    @staticmethod
    def calc_crcs(pending, pending_size, rootName, new_sizeCrcDate, progress):
        if not pending: return
        done = 0
        progress_msg= rootName + u'\n' + _(u'Calculating CRCs...') + u'\n'
        progress(0, progress_msg)
        # each mod increments the progress bar by at least one, even if it
        # is size 0 - add len(pending) to the progress bar max to ensure we
        # don't hit 100% and cause the progress bar to prematurely disappear
        progress.setFull(pending_size + len(pending))
        for rpFile, (size, _crc, date, asFile) in iter(sorted(pending.items())):
            progress(done, progress_msg + rpFile.s)
            sub = bolt.SubProgress(progress, done, done + size + 1)
            sub.setFull(size + 1)
            crc = 0L
            try:
                with open(asFile, 'rb') as ins:
                    insRead = ins.read
                    insTell = ins.tell
                    while insTell() < size:
                        crc = crc32(insRead(2097152),
                                    crc) # 2MB at a time, probably ok
                        sub(insTell())
            except IOError:
                deprint(_(u'Failed to calculate crc for %s - please report '
                          u'this, and the following traceback:') % asFile,
                        traceback=True)
                continue
            crc &= 0xFFFFFFFF
            done += size + 1
            new_sizeCrcDate[rpFile] = (size, crc, date, asFile)

    #--Initialization, etc ----------------------------------------------------
    def initDefault(self):
        """Initialize everything to default values."""
        self.archive = u''
        #--Persistent: set by _refreshSource called by refreshBasic
        self.modified = 0 #--Modified date
        self.size = -1 #--size of archive file
        self.crc = 0 #--crc of archive
        self.isSolid = False #--package only - solid 7z archive
        self.blockSize = None #--package only - set here and there
        self.fileSizeCrcs = [] #--list of tuples for _all_ files in installer
        #--For InstallerProject's, cache if refresh projects is skipped
        self.src_sizeCrcDate = {}
        #--Set by refreshBasic
        self.fileRootIdex = 0 # unused - just used in setstate
        self.type = 0 #--Package type: 0: unset/invalid; 1: simple; 2: complex
        self.subNames = []
        self.subActives = []
        self.extras_dict = {} # hack to add more persistent attributes
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
        #--Volatiles (not pickled values)
        #--Volatiles: directory specific
        self.project_refreshed = False
        self._dir_dirs_files = None
        #--Volatile: set by refreshDataSizeCrc
        self.hasWizard = False
        self.hasBCF = False
        self.espmMap = collections.defaultdict(list)
        self.packageDoc = self.packagePic = None
        self.hasReadme = False
        self.hasBethFiles = False
        self.data_sizeCrc = {}
        self.skipExtFiles = set()
        self.skipDirFiles = set()
        self.espms = set()
        self.unSize = 0
        self.dirty_sizeCrc = {}
        #--Volatile: set by refreshStatus
        self.status = 0
        self.underrides = set()
        self.missingFiles = set()
        self.mismatchedFiles = set()
        self.mismatchedEspms = set()

    @property
    def num_of_files(self): return len(self.fileSizeCrcs)

    @staticmethod
    def number_string(number, marker_string=u''):
        return formatInteger(number)

    def size_string(self, marker_string=u''):
        return round_size(self.size)

    def structure_string(self):
        if self.type == 1:
            return _(u'Structure: Simple')
        elif self.type == 2:
            if len(self.subNames) == 2:
                return _(u'Structure: Complex/Simple')
            else:
                return _(u'Structure: Complex')
        elif self.type < 0:
            return _(u'Structure: Corrupt/Incomplete')
        else:
            return _(u'Structure: Unrecognized')

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
        rescan = False
        if not isinstance(self.extras_dict, dict):
            self.extras_dict = {}
            if self.fileRootIdex: # we need to add 'root_path' key
                rescan = True
        elif self.fileRootIdex and not self.extras_dict.get('root_path', u''):
            rescan = True ##: for people that used my wip branch, drop on 307
        package_path = bass.dirs['installers'].join(self.archive)
        exists = package_path.exists()
        if not exists: # the pickled package was deleted outside bash
            pass # don't do anything should be deleted from our data soon
        elif rescan:
            dest_scr = self.refreshBasic(bolt.Progress(),
                                         recalculate_project_crc=False)
        else: dest_scr = self.refreshDataSizeCrc()
        if exists and self.overrideSkips:
            InstallersData.overridden_skips.update(dest_scr.keys())

    def __copy__(self):
        """Create a copy of self -- works for subclasses too (assuming
        subclasses don't add new data members)."""
        clone = self.__class__(GPath(self.archive))
        copier = copy.copy
        getter = object.__getattribute__
        setter = object.__setattr__
        for attr in Installer.__slots__:
            setter(clone,attr,copier(getter(self,attr)))
        return clone

    #--refreshDataSizeCrc, err, framework -------------------------------------
    # Those files/folders will be always skipped by refreshDataSizeCrc()
    _silentSkipsStart = (
        u'--', u'omod conversion data%s' % os_sep, u'fomod%s' % os_sep,
        u'wizard images%s' % os_sep)
    _silentSkipsEnd = (
        u'%sthumbs.db' % os_sep, u'%sdesktop.ini' % os_sep, u'config')

    # global skips that can be overridden en masse by the installer
    _global_skips = []
    _global_start_skips = []
    _global_skip_extensions = set()
    # executables - global but if not skipped need additional processing
    _executables_ext = {u'.dll', u'.dlx'} | {u'.asi'} | {u'.jar'}
    _executables_process = {}
    _goodDlls = _badDlls = None
    @staticmethod
    def goodDlls():
        if Installer._goodDlls is None:
            Installer._goodDlls = collections.defaultdict(list)
            Installer._goodDlls.update(settings['bash.installers.goodDlls'])
        return Installer._goodDlls
    @staticmethod
    def badDlls():
        if Installer._badDlls is None:
            Installer._badDlls = collections.defaultdict(list)
            Installer._badDlls.update(settings['bash.installers.badDlls'])
        return Installer._badDlls
    # while checking for skips process some installer attributes
    _attributes_process = {}
    _extensions_to_process = set()

    @staticmethod
    def init_global_skips():
        """Update _global_skips with functions deciding if 'fileLower' (docs !)
        must be skipped, based on global settings. Should be updated on boot
        and on flipping skip settings - and nowhere else hopefully."""
        del Installer._global_skips[:]
        del Installer._global_start_skips[:]
        Installer._global_skip_extensions.clear()
        if settings['bash.installers.skipTESVBsl']:
            Installer._global_skip_extensions.add('.bsl')
        # skips files starting with...
        if settings['bash.installers.skipDistantLOD']:
            Installer._global_start_skips.append(u'distantlod')
        if settings['bash.installers.skipLandscapeLODMeshes']:
            meshes_lod = os_sep.join((u'meshes', u'landscape', u'lod'))
            Installer._global_start_skips.append(meshes_lod)
        if settings['bash.installers.skipScreenshots']:
            Installer._global_start_skips.append(u'screenshots')
        # LOD textures
        skipLODTextures = settings['bash.installers.skipLandscapeLODTextures']
        skipLODNormals = settings['bash.installers.skipLandscapeLODNormals']
        skipAllTextures = skipLODTextures and skipLODNormals
        tex_gen = os_sep.join((u'textures', u'landscapelod', u'generated'))
        if skipAllTextures:
            Installer._global_start_skips.append(tex_gen)
        elif skipLODTextures: Installer._global_skips.append(
            lambda f: f.startswith(tex_gen) and not f.endswith(u'_fn.dds'))
        elif skipLODNormals: Installer._global_skips.append(
            lambda f: f.startswith(tex_gen) and f.endswith(u'_fn.dds'))
        # Skipped extensions
        skipObse = not settings['bash.installers.allowOBSEPlugins']
        if skipObse:
            Installer._global_start_skips.append(bush.game.se.shortName.lower() + os_sep)
            Installer._global_skip_extensions |= Installer._executables_ext
        if settings['bash.installers.skipImages']:
            Installer._global_skip_extensions |= imageExts
        Installer._init_executables_skips()

    @staticmethod
    def init_attributes_process():
        """Populate _attributes_process with functions which decide if the
        file is to be skipped while at the same time update self hasReadme,
        hasWizard, hasBCF attributes."""
        reReadMeMatch = Installer.reReadMe.match
        docs_ = u'Docs' + os_sep
        def _process_docs(self, fileLower, full, fileExt, file_relative, sub):
            maReadMe = reReadMeMatch(fileLower)
            if maReadMe: self.hasReadme = full
            # let's hope there is no trailing separator - Linux: test fileLower, full are os agnostic
            rsplit = fileLower.rsplit(os_sep, 1)
            parentDir, fname = (u'', rsplit[0]) if len(rsplit) == 1 else rsplit
            if not self.overrideSkips and settings[
                'bash.installers.skipDocs'] and not (
                fname in bush.game.dontSkip) and not (
                fileExt in bush.game.dontSkipDirs.get(parentDir, [])):
                return None # skip
            dest = file_relative
            if not parentDir:
                archiveRoot = GPath(self.archive).sroot if isinstance(self,
                        InstallerArchive) else self.archive
                if fileLower in {u'masterlist.txt', u'dlclist.txt'}:
                    self.skipDirFiles.add(full)
                    return None # we dont want to install those files
                elif maReadMe:
                    if not (maReadMe.group(1) or maReadMe.group(3)):
                        dest = u''.join((docs_, archiveRoot, fileExt))
                    else:
                        dest = u''.join((docs_, file_relative))
                    # self.extras_dict['readMe'] = dest
                elif fileLower == u'package.txt':
                    dest = self.packageDoc = u''.join(
                        (docs_, archiveRoot, u'.package.txt'))
                else:
                    dest = u''.join((docs_, file_relative))
            return dest
        for ext in Installer.docExts:
            Installer._attributes_process[ext] = _process_docs
        def _process_BCF(self, fileLower, full, fileExt, file_relative, sub):
            if fileLower[-7:-3] == u'-bcf' or u'-bcf-' in fileLower: # DOCS !
                self.hasBCF = full
                return None # skip
            return file_relative
        Installer._attributes_process[defaultExt] = _process_BCF # .7z
        def _process_txt(self, fileLower, full, fileExt, file_relative, sub):
            if fileLower == u'wizard.txt': # first check if it's the wizard.txt
                self.hasWizard = full
                return None # skip
            return _process_docs(self, fileLower, full, fileExt, file_relative, sub)
        Installer._attributes_process[u'.txt'] = _process_txt
        def _remap_espms(self, fileLower, full, fileExt, file_relative, sub):
            rootLower = file_relative.split(os_sep, 1)
            if len(rootLower) > 1: return file_relative ##: maybe skip ??
            file_relative = self.remaps.get(file_relative, file_relative)
            if file_relative not in self.espmMap[sub]: self.espmMap[
                sub].append(file_relative)
            pFile = GPath(file_relative)
            self.espms.add(pFile)
            if pFile in self.espmNots: return None # skip
            return file_relative
        Installer._attributes_process[u'.esm'] = \
        Installer._attributes_process[u'.esp'] = _remap_espms
        Installer._extensions_to_process = set(Installer._attributes_process)

    def _init_skips(self):
        voice_dir = os_sep.join((u'sound', u'voice')) + os_sep
        start = [voice_dir] if self.skipVoices else []
        skips, skip_ext = [], set()
        if not self.overrideSkips:
            skips = list(Installer._global_skips)
            start.extend(Installer._global_start_skips)
            skip_ext = Installer._global_skip_extensions
        if start: skips.append(lambda f: f.startswith((tuple(start))))
        skipEspmVoices = not self.skipVoices and set(
                x.cs for x in self.espmNots)
        if skipEspmVoices:
            def _skip_espm_voices(fileLower):
                farPos = fileLower.startswith( # u'sound\\voice\\', 12 chars
                    voice_dir) and fileLower.find(os_sep, 12)
                return farPos > 12 and fileLower[12:farPos] in skipEspmVoices
            skips.append(_skip_espm_voices)
        return skips, skip_ext

    @staticmethod
    def _init_executables_skips():
        goodDlls = Installer.goodDlls()
        badDlls = Installer.badDlls()
        def __skipExecutable(checkOBSE, fileLower, full, archiveRoot, size,
                             crc, desc, ext, exeDir, dialogTitle):
            if not fileLower.startswith(exeDir): return True
            if fileLower in badDlls and [archiveRoot, size, crc] in badDlls[
                fileLower]: return True
            if not checkOBSE or fileLower in goodDlls and [
                archiveRoot, size, crc] in goodDlls[fileLower]: return False
            message = Installer._dllMsg(fileLower, full, archiveRoot,
                                        desc, ext, badDlls, goodDlls)
            if not balt.askYes(balt.Link.Frame,message, dialogTitle):
                badDlls[fileLower].append([archiveRoot,size,crc])
                settings['bash.installers.badDlls'] = Installer._badDlls
                return True
            goodDlls[fileLower].append([archiveRoot,size,crc])
            settings['bash.installers.goodDlls'] = Installer._goodDlls
            return False
        if bush.game.se.shortName:
            _obse = partial(__skipExecutable,
                    desc=_(u'%s plugin DLL') % bush.game.se.shortName,
                    ext=(_(u'a dll')),
                    exeDir=(bush.game.se.shortName.lower() + os_sep),
                    dialogTitle=bush.game.se.shortName + _(u' DLL Warning'))
            Installer._executables_process[u'.dll'] = \
            Installer._executables_process[u'.dlx'] = _obse
        if bush.game.sd.shortName:
            _asi = partial(__skipExecutable,
                   desc=_(u'%s plugin ASI') % bush.game.sd.longName,
                   ext=(_(u'an asi')),
                   exeDir=(bush.game.sd.installDir.lower() + os_sep),
                   dialogTitle=bush.game.sd.longName + _(u' ASI Warning'))
            Installer._executables_process[u'.asi'] = _asi
        if bush.game.sp.shortName:
            _jar = partial(__skipExecutable,
                   desc=_(u'%s patcher JAR') % bush.game.sp.longName,
                   ext=(_(u'a jar')),
                   exeDir=(bush.game.sp.installDir.lower() + os_sep),
                   dialogTitle=bush.game.sp.longName + _(u' JAR Warning'))
            Installer._executables_process[u'.jar'] = _jar

    @staticmethod
    def _dllMsg(fileLower, full, archiveRoot, desc, ext, badDlls, goodDlls):
        message = u'\n'.join((
            _(u'This installer (%s) has an %s.'), _(u'The file is %s'),
            _(u'Such files can be malicious and hence you should be very '
              u'sure you know what this file is and that it is legitimate.'),
            _(u'Are you sure you want to install this?'),)) % (
                  archiveRoot, desc, full)
        if fileLower in goodDlls:
            message += _(u' You have previously chosen to install '
                         u'%s by this name but with a different size, '
                         u'crc and or source archive name.') % ext
        elif fileLower in badDlls:
            message += _(u' You have previously chosen to NOT '
                         u'install %s by this name but with a different '
                         u'size, crc and/or source archive name - make '
                         u'extra sure you want to install this one before '
                         u'saying yes.') % ext
        return message

    def refreshDataSizeCrc(self, checkOBSE=False, splitExt=os.path.splitext):
        """Update self.data_sizeCrc and related variables and return
        dest_src map for install operation....

        WIP rewrite
        Used:
         - in __setstate__ to construct the installers from Installers.dat,
         used once (and in full refresh ?)
         - in refreshBasic, after refreshing persistent attributes - track
         call graph from here should be the path that needs optimization (
         irefresh, ShowPanel ?)
         - in InstallersPanel.refreshCurrent()
         - in 2 subclasses' install() and InstallerProject.syncToData()
         - in _Installers_Skip._refreshInstallers()
         - in _RefreshingLink (override skips, HasExtraData, skip voices)
         - in Installer_CopyConflicts
        """
        type_    = self.type
        #--Init to empty
        self.hasWizard = self.hasBCF = self.hasReadme = False
        self.packageDoc = self.packagePic = None # = self.extras_dict['readMe']
        for attr in {'skipExtFiles','skipDirFiles','espms'}:
            object.__getattribute__(self,attr).clear()
        dest_src = {}
        #--Bad archive?
        if type_ not in {1,2}: return dest_src
        archiveRoot = GPath(self.archive).sroot if isinstance(self,
                InstallerArchive) else self.archive
        docExts = self.docExts
        docDirs = self.docDirs
        dataDirsPlus = self.dataDirsPlus
        dataDirsMinus = self.dataDirsMinus
        skipExts = self.skipExts
        unSize = 0
        bethFiles = bush.game.bethDataFiles
        skips, global_skip_ext = self._init_skips()
        if self.overrideSkips:
            renameStrings = False
            bethFilesSkip = False
        else:
            renameStrings = settings['bash.installers.renameStrings'] if bush.game.esp.stringsFiles else False
            bethFilesSkip = not settings['bash.installers.autoRefreshBethsoft']
        language = oblivionIni.get_ini_language() if renameStrings else u''
        languageLower = language.lower()
        hasExtraData = self.hasExtraData
        if type_ == 2: # exclude u'' from active subpackages
            activeSubs = set(x for x,y in zip(self.subNames[1:],self.subActives[1:]) if y)
        data_sizeCrc = {}
        skipDirFiles = self.skipDirFiles
        skipDirFilesAdd = skipDirFiles.add
        skipDirFilesDiscard = skipDirFiles.discard
        skipExtFilesAdd = self.skipExtFiles.add
        commonlyEditedExts = Installer.commonlyEditedExts
        espmMap = self.espmMap = collections.defaultdict(list)
        reModExtMatch = reModExt.match
        reReadMeMatch = Installer.reReadMe.match
        #--Scan over fileSizeCrcs
        root_path = self.extras_dict.get('root_path', u'')
        rootIdex = len(root_path)
        for full,size,crc in self.fileSizeCrcs:
            if rootIdex: # exclude all files that are not under root_dir
                if not full.startswith(root_path): continue
            file = full[rootIdex:]
            fileLower = file.lower()
            if fileLower.startswith( # skip top level '--', 'fomod' etc
                    Installer._silentSkipsStart) or fileLower.endswith(
                    Installer._silentSkipsEnd): continue
            sub = u''
            if type_ == 2: #--Complex archive
                split = file.split(os_sep, 1)
                if len(split) > 1:
                    # redefine file, excluding the subpackage directory
                    sub,file = split
                    fileLower = file.lower()
                    if fileLower.startswith(Installer._silentSkipsStart):
                        continue # skip subpackage level '--', 'fomod' etc
                if sub not in activeSubs:
                    if sub == u'':
                        skipDirFilesAdd(file)
                    # Run a modified version of the normal checks, just
                    # looking for esp's for the wizard espmMap, wizard.txt
                    # and readme's
                    rootLower,fileExt = splitExt(fileLower)
                    rootLower = rootLower.split(os_sep, 1)
                    if len(rootLower) == 1: rootLower = u''
                    else: rootLower = rootLower[0]
                    skip = True
                    sub_esps = espmMap[sub] # add sub key to the espmMap
                    if fileLower == u'wizard.txt':
                        self.hasWizard = full
                        skipDirFilesDiscard(file)
                        continue
                    elif fileExt in defaultExt and (fileLower[-7:-3] == u'-bcf' or u'-bcf-' in fileLower):
                        self.hasBCF = full
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
                        skipDirFilesDiscard(file)
                        skipDirFilesAdd(_(u'[Bethesda Content]') + u' ' + file)
                        continue
                    elif not rootLower and reModExtMatch(fileExt):
                        #--Remap espms as defined by the user
                        if file in self.remaps:
                            file = self.remaps[file]
                            # fileLower = file.lower() # not needed will skip
                        if file not in sub_esps: sub_esps.append(file)
                    if skip:
                        continue
            sub_esps = espmMap[sub] # add sub key to the espmMap
            rootLower,fileExt = splitExt(fileLower)
            rootLower = rootLower.split(os_sep, 1)
            if len(rootLower) == 1: rootLower = u''
            else: rootLower = rootLower[0]
            fileStartsWith = fileLower.startswith
            #--Skips
            for lam in skips:
                if lam(fileLower):
                    _out = True
                    break
            else: _out = False
            if _out: continue
            dest = None # destination of the file relative to the Data/ dir
            # process attributes and define destination for docs and images
            # (if not skipped globally)
            if fileExt in Installer._extensions_to_process:
                dest = Installer._attributes_process[fileExt](
                    self, fileLower, full, fileExt, file, sub)
                if dest is None: continue
            if fileExt in global_skip_ext: continue # docs treated above
            elif fileExt in Installer._executables_process: # and handle execs
                if Installer._executables_process[fileExt](
                        checkOBSE, fileLower, full, archiveRoot, size, crc):
                    continue
            #--Noisy skips
            if fileLower in bethFiles:
                self.hasBethFiles = True
                if bethFilesSkip:
                    skipDirFilesAdd(_(u'[Bethesda Content]') + u' ' + full)
                    if sub_esps and sub_esps[-1].lower() == fileLower:
                        del sub_esps[-1] # added in extensions processing
                        self.espms.discard(GPath(file)) #dont show in espm list
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
            #--Remap docs, strings
            if dest is None: dest = file
            if rootLower in docDirs:
                dest = os_sep.join((u'Docs', file[len(rootLower) + 1:]))
            elif (renameStrings and fileStartsWith(u'strings' + os_sep) and
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
                if fileLower == u'package.jpg':
                    dest = self.packagePic = u''.join(
                        (u'Docs' + os_sep, archiveRoot, u'.package.jpg'))
                elif fileExt in imageExts:
                    dest = os_sep.join((u'Docs', file))
            if fileExt in commonlyEditedExts: ##: will track all the txt files in Docs/
                InstallersData.miscTrackedFiles.track(dirs['mods'].join(dest))
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

    def _find_root_index(self, _os_sep=os_sep, skips_start=_silentSkipsStart):
        # basically just care for skips and complex/simple packages
        #--Sort file names
        split = os.path.split
        sort_keys_dict = dict(
            (x, split(x[0].lower())) for x in self.fileSizeCrcs)
        self.fileSizeCrcs.sort(key=sort_keys_dict.__getitem__)
        #--Find correct starting point to treat as BAIN package
        self.extras_dict.clear() # if more keys are added be careful cleaning
        self.fileRootIdex = 0
        dataDirsPlus = Installer.dataDirsPlus
        layout = {}
        layoutSetdefault = layout.setdefault
        for full, size, crc in self.fileSizeCrcs:
            fileLower = full.lower()
            if fileLower.startswith(skips_start): continue
            frags = full.split(_os_sep)
            if len(frags) == 1:
                # Files in the root of the package, start there
                break
            else:
                dirName = frags[0]
                if dirName not in layout and layout:
                    # A second directory in the archive root, start in the root
                    break
                root = layoutSetdefault(dirName,{'dirs':{},'files':False})
                for frag in frags[1:-1]:
                    root = root['dirs'].setdefault(frag,{'dirs':{},'files':False})
                # the last frag is a file, so its parent dir has files
                root['files'] = True
        else:
            if not layout: return
            rootStr = layout.keys()[0]
            if rootStr.lower() in dataDirsPlus: return
            root = layout[rootStr]
            rootStr = u''.join((rootStr, _os_sep))
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
                    rootDirKeyL = rootDirKey.lower()
                    if rootDirKeyL in dataDirsPlus or rootDirKeyL == u'data':
                        # Found suitable starting point
                        break
                    # Keep looking deeper
                    root = rootDirs[rootDirKey]
                    rootStr = u''.join((rootStr, rootDirKey, _os_sep))
                else:
                    # Multiple folders, stop here even if it's no good
                    break
            self.extras_dict['root_path'] = rootStr # keeps case
            self.fileRootIdex = len(rootStr)

    def refreshBasic(self, progress, recalculate_project_crc=True):
        return self._refreshBasic(progress, recalculate_project_crc)

    def _refreshBasic(self, progress, recalculate_project_crc=True,
                     _os_sep=os_sep, skips_start=tuple(
                x.replace(os_sep, u'') for x in _silentSkipsStart)):
        """Extract file/size/crc and BAIN structure info from installer."""
        try:
            self._refreshSource(progress, recalculate_project_crc)
        except InstallerArchiveError:
            self.type = -1 # size, modified and some of fileSizeCrcs may be set
            return {}
        self._find_root_index()
        # fileRootIdex now points to the start in the file strings to ignore
        #--Type, subNames
        type_ = 0
        subNameSet = set()
        subNameSet.add(u'') # set(u'') == set() (unicode is iterable), so add
        reDataFileSearch = self.reDataFile.search
        dataDirsPlus = self.dataDirsPlus
        root_path = self.extras_dict.get('root_path', u'')
        for full, size, crc in self.fileSizeCrcs:#break if type=1 else churn on
            frags = full.split(_os_sep)
            if root_path: # exclude all files that are not under root_dir
                if frags[0] != root_path[:-1]: continue # chop off os_sep
                frags = frags[1:]
            nfrags = len(frags)
            f0_lower = frags[0].lower()
            #--Type 1 ? break ! data files/dirs are not allowed in type 2 top
            if (nfrags == 1 and reDataFileSearch(f0_lower) or
                nfrags > 1 and f0_lower in dataDirsPlus):
                type_ = 1
                break
            #--Else churn on to see if we have a Type 2 package
            elif not frags[0] in subNameSet and not \
                    f0_lower.startswith(skips_start) and (
                (nfrags > 2 and frags[1].lower() in dataDirsPlus) or
                (nfrags == 2 and reDataFileSearch(frags[1]))):
                subNameSet.add(frags[0])
                type_ = 2
        self.type = type_
        #--SubNames, SubActives
        if type_ == 2:
            self.subNames = sorted(subNameSet,key=unicode.lower)
            actives = set(x for x,y in zip(self.subNames,self.subActives) if (y or x == u''))
            if len(self.subNames) == 2: #--If only one subinstall, then make it active.
                self.subActives = [True,True] # that's a complex/simple package
            else:
                self.subActives = [(x in actives) for x in self.subNames]
        else:
            self.subNames = []
            self.subActives = []
        #--Data Size Crc
        return self.refreshDataSizeCrc()

    def refreshStatus(self, installersData):
        """Updates missingFiles, mismatchedFiles and status.
        Status:
        20: installed (green)
        10: mismatches (yellow)
        0: unconfigured (white)
        -10: missing files (red)
        -20: bad type (grey)
        """
        data_sizeCrc = self.data_sizeCrc
        data_sizeCrcDate = installersData.data_sizeCrcDate
        abnorm_sizeCrc = installersData.abnorm_sizeCrc
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

    #--Utility methods --------------------------------------------------------
    def size_or_mtime_changed(self, apath):
        return (self.size, self.modified) != apath.size_mtime()

    def _installer_rename(self, data, newName):
        """Rename package or project."""
        g_path = GPath(self.archive)
        if newName != g_path:
            newPath = dirs['installers'].join(newName)
            if not newPath.exists():
                _DataStore._rename_operation(data, g_path, newName)
                #--Add the new archive to Bash and remove old one
                data[newName] = self
                del data[g_path]
                #--Update the iniInfos & modInfos for 'installer'
                mfiles = [x for x in modInfos.table.getColumn('installer') if
                          modInfos.table[x]['installer'] == self.archive]
                ifiles = [x for x in iniInfos.table.getColumn('installer') if
                          iniInfos.table[x]['installer'] == self.archive]
                self.archive = newName.s # don't forget to rename !
                for i in mfiles:
                    modInfos.table[i]['installer'] = self.archive
                for i in ifiles:
                    iniInfos.table[i]['installer'] = self.archive
                return True, bool(mfiles), bool(ifiles)
        return False, False, False

    def open_readme(self): pass
    def open_wizard(self): pass
    def wizard_file(self): raise AbstractError

    def __repr__(self):
        return self.__class__.__name__ + u"<" + repr(self.archive) + u">"

    #--ABSTRACT ---------------------------------------------------------------
    def _refreshSource(self, progress, recalculate_project_crc):
        """Refresh fileSizeCrcs, size, and modified from source
        archive/directory. fileSizeCrcs is a list of tuples, one for _each_
        file in the archive or project directory. _refreshSource is called
        in refreshBasic only. In projects the src_sizeCrcDate cache is used to
        avoid recalculating crc's.
        :param recalculate_project_crc: only used in InstallerProject override
        """
        raise AbstractError

    def install(self, destFiles, data_sizeCrcDate, progress=None):
        """Install specified files to Oblivion\Data directory."""
        raise AbstractError

    def _move(self, count, progress, stageDataDir):
        # TODO: Find the operation that does not properly close the Oblivion\Data dir.
        # The addition of \\Data and \\* are a kludgy fix for a bug. An operation that is sometimes executed
        # before this locks the Oblivion\Data dir (only for Oblivion, Skyrim is fine)  so it can not be opened
        # with write access. It can be reliably reproduced by deleting the Table.dat file and then trying to
        # install a mod for Oblivion.
        try:
            if count:
                destDir = dirs['mods'].head + u'\\Data'
                stageDataDir += u'\\*'
                env.shellMove(stageDataDir, destDir, progress.getParent())
        finally:
            #--Clean up staging dir
            self.rmTempDir()

    def listSource(self):
        """Return package structure as text."""
        with sio() as out:
            log = bolt.LogFile(out)
            log.setHeader(u'%s ' % self.archive + _(u'Package Structure:'))
            log(u'[spoiler][xml]\n', False)
            apath = dirs['installers'].join(self.archive)
            self._list_package(apath, log)
            log(u'[/xml][/spoiler]')
            return bolt.winNewLines(log.out.getvalue())

    @staticmethod
    def _list_package(apath, log): raise AbstractError

    def renameInstaller(self, name_new, data):
        """Rename installer and return a three tuple specifying if a refresh in
        mods and ini lists is needed.
        :rtype: tuple
        """
        raise AbstractError

#------------------------------------------------------------------------------
class InstallerMarker(Installer):
    """Represents a marker installer entry."""
    __slots__ = tuple() #--No new slots
    type_string = _(u'Marker')

    def __init__(self,archive):
        Installer.__init__(self,archive)
        self.modified = time.time()

    @property
    def num_of_files(self): return -1

    @staticmethod
    def number_string(number, marker_string=u''): return marker_string

    def size_string(self, marker_string=u''): return marker_string

    def structure_string(self): return _(u'Structure: N/A')

    def _refreshSource(self, progress, recalculate_project_crc):
        """Marker: size is -1, fileSizeCrcs empty, modified = creation time."""
        pass

    def install(self, destFiles, data_sizeCrcDate, progress=None):
        """Install specified files to Oblivion\Data directory."""
        pass

    def renameInstaller(self, name_new, data):
        newName = GPath(u'==' + name_new.s.strip(u'=') + u'==')
        archive = GPath(self.archive)
        if newName == archive:
            return False
        #--Add the marker to Bash and remove old one
        self.archive = newName.s
        data[newName] = self
        del data[archive]
        return True, False, False

    def refreshBasic(self, progress, recalculate_project_crc=True):
        return {}

#------------------------------------------------------------------------------
class InstallerArchiveError(bolt.BoltError): pass

#------------------------------------------------------------------------------
class InstallerArchive(Installer):
    """Represents an archive installer entry."""
    __slots__ = tuple() #--No new slots
    type_string = _(u'Archive')

    #--File Operations --------------------------------------------------------
    def _refreshSource(self, progress, recalculate_project_crc):
        """Refresh fileSizeCrcs, size, modified, crc, isSolid from archive."""
        #--Basic file info
        archive_path = bass.dirs['installers'].join(self.archive)
        self.size, self.modified = archive_path.size_mtime()
        #--Get fileSizeCrcs
        fileSizeCrcs = self.fileSizeCrcs = []
        self.isSolid = False
        class _li(object): # line info - we really want python's 3 'nonlocal'
            filepath = size = crc = isdir = cumCRC = 0
            __slots__ = ()
        def _parse_archive_line(key, value):
            if   key == u'Solid': self.isSolid = (value[0] == u'+')
            elif key == u'Path': _li.filepath = value.decode('utf8')
            elif key == u'Size': _li.size = int(value)
            elif key == u'Attributes': _li.isdir = value and (value[0] == u'D')
            elif key == u'CRC' and value: _li.crc = int(value,16)
            elif key == u'Method':
                if _li.filepath and not _li.isdir and _li.filepath != \
                        tempArch.s:
                    fileSizeCrcs.append((_li.filepath, _li.size, _li.crc))
                    _li.cumCRC += _li.crc
                _li.filepath = _li.size = _li.crc = _li.isdir = 0
        with archive_path.unicodeSafe() as tempArch:
            try:
                archives.list_archive(tempArch, _parse_archive_line)
                self.crc = _li.cumCRC & 0xFFFFFFFFL
            except:
                archive_msg = u"Unable to read archive '%s'." % archive_path.s
                deprint(archive_msg, traceback=True)
                raise InstallerArchiveError(archive_msg)

    def unpackToTemp(self, fileNames, progress=None, recurse=False):
        """Erases all files from self.tempDir and then extracts specified files
        from archive to self.tempDir. progress will be zeroed so pass a
        SubProgress in.
        fileNames: File names (not paths)."""
        if not fileNames: raise ArgumentError(
            u'No files to extract for %s.' % self.archive)
        # expand wildcards in fileNames to get actual count of files to extract
        #--Dump file list
        with self.tempList.open('w',encoding='utf8') as out:
            out.write(u'\n'.join(fileNames))
        apath = dirs['installers'].join(self.archive)
        #--Ensure temp dir empty
        self.rmTempDir()
        with apath.unicodeSafe() as arch:
            if progress:
                progress.state = 0
                progress(0, u'%s\n' % self.archive + _(u'Counting files...') + u'\n')
                numFiles = countFilesInArchive(arch, self.tempList, recurse)
                progress.setFull(numFiles)
            #--Extract files
            command = archives.extractCommand(arch, self.getTempDir())
            command += u' @%s' % self.tempList.s
            if recurse: command += u' -r'
            try:
                archives.extract7z(command, GPath(self.archive), progress)
            finally:
                self.tempList.remove()
                bolt.clearReadOnly(self.getTempDir())
        #--Done -> don't clean out temp dir, it's going to be used soon

    def install(self, destFiles, data_sizeCrcDate, progress=None):
        """Install specified files to Game\Data directory."""
        destFiles = set(destFiles)
        data_sizeCrc = self.data_sizeCrc
        dest_src = dict((x,y) for x,y in self.refreshDataSizeCrc(True).iteritems() if x in destFiles)
        if not dest_src: return 0
        progress = progress if progress else bolt.Progress()
        #--Extract
        progress(0, self.archive + u'\n' + _(u'Extracting files...'))
        self.unpackToTemp(dest_src.values(), SubProgress(progress, 0, 0.9))
        #--Rearrange files
        progress(0.9, self.archive + u'\n' + _(u'Organizing files...'))
        unpackDir = self.getTempDir() #--returns directory used by unpackToTemp
        unpackDirJoin = unpackDir.join
        stageDir = self.newTempDir()  #--forgets the old temp dir, creates a new one
        subprogress = SubProgress(progress,0.9,1.0)
        subprogress.setFull(max(len(dest_src),1))
        subprogressPlus = subprogress.plus
        stageDataDir = stageDir.join(u'Data')
        stageDataDirJoin = stageDataDir.join
        norm_ghost = Installer.getGhosted() # some.espm -> some.espm.ghost
        norm_ghostGet = norm_ghost.get
        data_sizeCrcDate_update = {}
        timestamps = load_order.install_last()
        count = 0
        for dest,src in  dest_src.iteritems():
            size,crc = data_sizeCrc[dest]
            srcFull = unpackDirJoin(src)
            stageFull = stageDataDirJoin(norm_ghostGet(dest,dest))
            if srcFull.exists():
                if reModExt.search(srcFull.s): timestamps(srcFull)
                data_sizeCrcDate_update[dest] = (size,crc,srcFull.mtime)
                count += 1
                # Move to staging directory
                srcFull.moveTo(stageFull)
                subprogressPlus()
        #--Clean up unpacked dir
        unpackDir.rmtree(safety=unpackDir.stail)
        #--Now Move
        self._move(count, progress, stageDataDir)
        #--Update Installers data
        data_sizeCrcDate.update(data_sizeCrcDate_update)
        return count

    def unpackToProject(self, project, progress=None):
        """Unpacks archive to build directory."""
        progress = progress or bolt.Progress()
        files = self.sortFiles([x[0] for x in self.fileSizeCrcs])
        if not files: return 0
        #--Clear Project
        destDir = dirs['installers'].join(project)
        if destDir.exists(): destDir.rmtree(safety=u'Installers')
        #--Extract
        progress(0,project.s+u'\n'+_(u'Extracting files...'))
        self.unpackToTemp(files, SubProgress(progress, 0, 0.9))
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

    @staticmethod
    def _list_package(apath, log):
        with apath.unicodeSafe() as tempArch:
            filepath = [u'']
            text = []
            def _parse_archive_line(key, value):
                if key == u'Path':
                    filepath[0] = value.decode('utf8')
                elif key == u'Attributes':
                    text.append( # attributes may be empty
                        (u'%s' % filepath[0], value and (value[0] == u'D')))
                elif key == u'Method':
                    filepath[0] = u''
            archives.list_archive(tempArch, _parse_archive_line)
        text.sort()
        #--Output
        for node, isdir in text:
            log(u'  ' * node.count(os.sep) + os.path.split(node)[1] + (
                os.sep if isdir else u''))

    def renameInstaller(self, name_new, data):
        return self._installer_rename(data,
                                      name_new.root + GPath(self.archive).ext)

    def open_readme(self):
        with balt.BusyCursor():
            # This is going to leave junk temp files behind...
            self.unpackToTemp([self.hasReadme])
        self.getTempDir().join(self.hasReadme).start()

    def open_wizard(self):
        with balt.BusyCursor():
            # This is going to leave junk temp files behind...
            try:
                self.unpackToTemp([self.hasWizard])
                self.getTempDir().join(self.hasWizard).start()
            except:
                # Don't clean up temp dir here.  Sometimes the editor
                # That starts to open the wizard.txt file is slower than
                # Bash, and the file will be deleted before it opens.
                # Just allow Bash's atexit function to clean it when quitting.
                pass

    def wizard_file(self):
        with balt.Progress(_(u'Extracting wizard files...'), u'\n' + u' ' * 60,
                           abort=True) as progress:
            # Extract the wizard, and any images as well
            self.unpackToTemp([self.hasWizard,
                u'*.bmp',            # BMP's
                u'*.jpg', u'*.jpeg', # JPEG's
                u'*.png',            # PNG's
                u'*.gif',            # GIF's
                u'*.pcx',            # PCX's
                u'*.pnm',            # PNM's
                u'*.tif', u'*.tiff', # TIFF's
                u'*.tga',            # TGA's
                u'*.iff',            # IFF's
                u'*.xpm',            # XPM's
                u'*.ico',            # ICO's
                u'*.cur',            # CUR's
                u'*.ani',            # ANI's
                ], bolt.SubProgress(progress,0,0.9), recurse=True)
        return self.getTempDir().join(self.hasWizard)

#------------------------------------------------------------------------------
class InstallerProject(Installer):
    """Represents a directory/build installer entry."""
    __slots__ = tuple() #--No new slots
    type_string = _(u'Project')

    def _refresh_from_project_dir(self, progress=None,
                                  recalculate_all_crcs=False):
        """Update src_sizeCrcDate cache from project directory. Used by
        _refreshSource() to populate the project's src_sizeCrcDate with
        _all_ files present in the project dir. src_sizeCrcDate is then used
        to populate fileSizeCrcs, used to populate data_sizeCrc in
        refreshDataSizeCrc. Compare to InstallersData._refresh_from_data_dir.
        :return: max modification time for files/folders in project directory
        :rtype: int"""
        #--Scan for changed files
        apRoot = dirs['installers'].join(self.archive)
        rootName = apRoot.stail
        progress = progress if progress else bolt.Progress()
        progress_msg = rootName + u'\n' + _(u'Scanning...')
        progress(0, progress_msg + u'\n')
        progress.setFull(1)
        asRoot = apRoot.s
        relPos = len(asRoot) + 1
        max_mtime = apRoot.mtime
        pending, pending_size = {}, 0
        new_sizeCrcDate = {}
        oldGet = self.src_sizeCrcDate.get
        walk = self._dir_dirs_files if self._dir_dirs_files is not None else os.walk(asRoot)
        for asDir, __sDirs, sFiles in walk:
            progress(0.05, progress_msg + (u'\n%s' % asDir[relPos:]))
            get_mtime = os.path.getmtime(asDir)
            max_mtime = max_mtime if max_mtime >= get_mtime else get_mtime
            rsDir = asDir[relPos:]
            for sFile in sFiles:
                rpFile = GPath(os.path.join(rsDir, sFile))
                asFile = os.path.join(asDir, sFile)
                # below calls may now raise even if "werr.winerror = 123"
                size = os.path.getsize(asFile)
                get_mtime = os.path.getmtime(asFile)
                max_mtime = max_mtime if max_mtime >= get_mtime else get_mtime
                date = int(get_mtime)
                oSize, oCrc, oDate = oldGet(rpFile, (0, 0, 0))
                if size == oSize and date == oDate:
                    new_sizeCrcDate[rpFile] = (oSize, oCrc, oDate, asFile)
                else:
                    pending[rpFile] = (size, oCrc, date, asFile)
                    pending_size += size
        Installer.final_update(new_sizeCrcDate, self.src_sizeCrcDate, pending,
                               pending_size, progress, recalculate_all_crcs,
                               rootName)
        #--Done
        return int(max_mtime)

    def size_or_mtime_changed(self, apath, _lstat=os.lstat):
        #FIXME(ut): getmtime(True) won't detect all changes - for instance COBL
        # has 3/25/2020 8:02:00 AM modification time if unpacked and no
        # amount of internal shuffling won't change its apath.getmtime(True)
        getM, join = os.path.getmtime, os.path.join
        c, size = [], 0
        cExtend, cAppend = c.extend, c.append
        self._dir_dirs_files = []
        for root, d, files in os.walk(apath.s):
            cAppend(getM(root))
            stats = [_lstat(join(root, fi)) for fi in files]
            cExtend(fi.st_mtime for fi in stats)
            size += sum(fi.st_size for fi in stats)
            self._dir_dirs_files.append((root, [], files)) # dirs is unused
        if self.size != size: return True
        # below is for the fix me - we need to add mtimes_str_crc extra persistent attribute to Installer
        # c.sort() # is this needed or os.walk will return the same order during program run
        # mtimes_str = '.'.join(map(str, c))
        # mtimes_str_crc = crc32(mtimes_str)
        try:
            mtime = int(max(c))
        except ValueError: # int(max([]))
            mtime = 0
        return self.modified != mtime

    @staticmethod
    def removeEmpties(name):
        """Removes empty directories from project directory."""
        empties = set()
        projectDir = dirs['installers'].join(name)
        for asDir,sDirs,sFiles in os.walk(projectDir.s):
            if not (sDirs or sFiles): empties.add(GPath(asDir))
        for empty in empties: empty.removedirs()
        projectDir.makedirs() #--In case it just got wiped out.

    def _refreshSource(self, progress, recalculate_project_crc):
        """Refresh src_sizeCrcDate, fileSizeCrcs, size, modified, crc from
        project directory, set project_refreshed to True."""
        self.modified = self._refresh_from_project_dir(progress,
                                                       recalculate_project_crc)
        cumCRC = 0
##        cumDate = 0
        cumSize = 0
        fileSizeCrcs = self.fileSizeCrcs = []
        for path, (size, crc, date) in self.src_sizeCrcDate.iteritems():
            fileSizeCrcs.append((path.s, size, crc))
##            cumDate = max(date,cumDate)
            cumCRC += crc
            cumSize += size
        self.size = cumSize
        self.crc = cumCRC & 0xFFFFFFFFL
        self.project_refreshed = True

    def install(self, destFiles, data_sizeCrcDate, progress=None):
        """Install specified files to Oblivion\Data directory."""
        destFiles = set(destFiles)
        data_sizeCrc = self.data_sizeCrc
        dest_src = dict((x,y) for x,y in self.refreshDataSizeCrc(True).iteritems() if x in destFiles)
        if not dest_src: return 0
        progress = progress if progress else bolt.Progress()
        progress.setFull(max(len(dest_src),1))
        progress(0, self.archive + u'\n' + _(u'Moving files...'))
        progressPlus = progress.plus
        #--Copy Files
        self.rmTempDir()
        stageDir = self.getTempDir()
        stageDataDir = stageDir.join(u'Data')
        stageDataDirJoin = stageDataDir.join
        norm_ghost = Installer.getGhosted() # some.espm -> some.espm.ghost
        norm_ghostGet = norm_ghost.get
        srcDir = dirs['installers'].join(self.archive)
        srcDirJoin = srcDir.join
        data_sizeCrcDate_update = {}
        timestamps = load_order.install_last()
        count = 0
        for dest,src in dest_src.iteritems():
            size,crc = data_sizeCrc[dest]
            srcFull = srcDirJoin(src)
            stageFull = stageDataDirJoin(norm_ghostGet(dest,dest))
            if srcFull.exists():
                srcFull.copyTo(stageFull)
                if reModExt.search(srcFull.s): timestamps(srcFull)
                data_sizeCrcDate_update[dest] = (size,crc,stageFull.mtime)
                count += 1
                progressPlus()
        self._move(count, progress, stageDataDir)
        #--Update Installers data
        data_sizeCrcDate.update(data_sizeCrcDate_update)
        return count

    def syncToData(self, projFiles):
        """Copies specified projFiles from Oblivion\Data to project
        directory.
        :type projFiles: set[bolt.Path]"""
        srcDir = dirs['mods']
        srcProj = tuple(
            (x, y) for x, y in self.refreshDataSizeCrc().iteritems() if
            x in projFiles)
        if not srcProj: return 0,0
        #--Sync Files
        updated = removed = 0
        norm_ghost = Installer.getGhosted()
        projDir = dirs['installers'].join(self.archive)
        for src,proj in srcProj:
            srcFull = srcDir.join(norm_ghost.get(src,src))
            projFull = projDir.join(proj)
            if not srcFull.exists():
                projFull.remove()
                removed += 1
            else:
                srcFull.copyTo(projFull)
                updated += 1
        self.removeEmpties(self.archive)
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
            command = u'"%s" a "%s" -t"%s" %s -y -r -o"%s" -i!"%s\\*" -x@%s -scsUTF-8 -sccUTF-8' % (
                archives.exe7z, outFile.temp.s, archiveType, solid, outDir.s, projectDir.s, self.tempList.s)
            try:
                archives.compress7z(command, outDir, outFile.tail, projectDir,
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

    @staticmethod
    def _list_package(apath, log):
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
        walkPath(apath.s, 0)

    def renameInstaller(self, name_new, data):
        return self._installer_rename(data, name_new)

    def open_readme(self):
        bass.dirs['installers'].join(self.archive, self.hasReadme).start()

    def open_wizard(self):
        bass.dirs['installers'].join(self.archive, self.hasWizard).start()

    def wizard_file(self):
        return bass.dirs['installers'].join(self.archive, self.hasWizard)

#------------------------------------------------------------------------------
from . import converters
from .converters import InstallerConverter
# Hack below needed as older Converters.dat expect bosh.InstallerConverter
# See InstallerConverter.__reduce__()
# noinspection PyRedeclaration
class InstallerConverter(InstallerConverter): pass

def projects_walk_cache(func): ##: HACK ! Profile
    """Decorator to make sure I dont leak self._dir_dirs_files project cache.
    Must decorate all methods that may call size_or_mtime_changed (only
    called in scan_installers_dir). For self._dir_dirs_files to be of any use
    the call to scan_installers_dir must be followed by refreshBasic calls
    on the projects."""
    @wraps(func)
    def _projects_walk_cache_wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        finally:
            it = self.itervalues() if isinstance(self, InstallersData) else \
                self.listData.itervalues()
            for project in it:
                if isinstance(project, InstallerProject):
                    project._dir_dirs_files = None
    return _projects_walk_cache_wrapper

class InstallersData(_DataStore):
    """Installers tank data. This is the data source for the InstallersList."""
    # hack to track changes in installed mod inis etc _in the Data/ dir_ and
    # deletions of mods/Ini Tweaks. Keys are absolute paths (so we can track
    # ini deletions from Data/Ini Tweaks as well as mods/xmls etc in Data/)
    miscTrackedFiles = TrackedFileInfos()
    # cache with paths in Data/ that would be skipped but are not, due to
    # an installer having the override skip etc flag on - when turning the skip
    # off leave the files here - will be cleaned on restart (files will show
    # as dirty till then, but to remove them we should examine all installers
    # that override skips - not worth the hassle)
    overridden_skips = set()
    __clean_overridden_after_load = True
    installers_dir_skips = set()

    def __init__(self):
        self.store_dir = dirs['installers']
        self.bash_dir.makedirs()
        #--Persistent data
        self.dictFile = bolt.PickleDict(self.bash_dir.join(u'Installers.dat'))
        self.data = {}
        self.data_sizeCrcDate = {}
        self.crc_installer = {}
        self.converters_data = converters.ConvertersData(
            dirs['bainData'], dirs['converters'], dirs['dupeBCFs'],
            dirs['corruptBCFs'], dirs['installers'])
        #--Volatile
        self.abnorm_sizeCrc = {} #--Normative sizeCrc, according to order of active packages
        self.bcfPath_sizeCrcDate = {}
        self.hasChanged = False
        self.loaded = False
        self.lastKey = GPath(u'==Last==')

    @property
    def bash_dir(self): return dirs['bainData']

    @property
    def hidden_dir(self): return bass.dirs['modsBash'].join(u'Hidden')

    def add_marker(self, name, order):
        self[name] = InstallerMarker(name)
        if order is None:
            order = self[self.lastKey].order
        self.moveArchives([name], order)

    def setChanged(self,hasChanged=True):
        """Mark as having changed."""
        self.hasChanged = hasChanged

    def refresh(self, *args, **kwargs): return self.irefresh(*args, **kwargs)

    def irefresh(self, progress=None, what='DIONSC', fullRefresh=False,
                 refresh_info=None, deleted=None, pending=None, projects=None):
        progress = progress or bolt.Progress()
        #--Archive invalidation
        if settings.get('bash.bsaRedirection') and oblivionIni.abs_path.exists():
            oblivionIni.setBsaRedirection(True)
        #--Load Installers.dat if not loaded - will set changed to True
        changed = not self.loaded and self.__load(progress)
        #--Last marker
        if self.lastKey not in self.data:
            self.data[self.lastKey] = InstallerMarker(self.lastKey)
        #--Refresh Other - FIXME(ut): docs
        if 'D' in what:
            changed |= self._refresh_from_data_dir(progress, fullRefresh)
        if 'I' in what: changed |= self._refreshInstallers(
            progress, fullRefresh, refresh_info, deleted, pending, projects)
        if 'O' in what or changed: changed |= self.refreshOrder()
        if 'N' in what or changed: changed |= self.refreshNorm()
        if 'S' in what or changed: changed |= self.refreshInstallersStatus()
        if 'C' in what or changed: changed |= \
            self.converters_data.refreshConverters(progress, fullRefresh)
        #--Done
        if changed: self.hasChanged = True
        return changed

    def __load(self, progress):
        progress(0, _(u"Loading Data..."))
        self.dictFile.load()
        self.converters_data.load()
        data = self.dictFile.data
        self.data = data.get('installers', {})
        self.data_sizeCrcDate = data.get('sizeCrcDate', {})
        self.crc_installer = data.get('crc_installer', {})
        # fixup: all markers had their archive attribute set to u'===='
        for key, value in self.iteritems():
            if isinstance(value, InstallerMarker):
                value.archive = key.s
        self.loaded = True
        return True

    def save(self):
        """Saves to pickle file."""
        if self.hasChanged:
            self.dictFile.data['installers'] = self.data
            self.dictFile.data['sizeCrcDate'] = self.data_sizeCrcDate
            self.dictFile.data['crc_installer'] = self.crc_installer
            self.dictFile.vdata['version'] = 1
            self.dictFile.save()
            self.converters_data.save()
            self.hasChanged = False

    def _rename_operation(self, oldName, newName):
        return self[oldName].renameInstaller(newName, self)

    #--Dict Functions -----------------------------------------------------------
    def delete(self, items, **kwargs):
        """Delete multiple installers. Delete entry AND archive file itself."""
        toDelete = []
        markers = []
        for item in items:
            if item == self.lastKey: continue
            if isinstance(self[item], InstallerMarker): markers.append(item)
            else: toDelete.append(self.store_dir.join(item))
        #--Delete
        doRefresh = kwargs.pop('doRefresh', True)
        try:
            for m in markers: del self[m]
            _delete(toDelete, **kwargs)
        finally:
            if doRefresh:
                deleted = set(markers)
                deleted.update(
                    item.tail for item in toDelete if not item.exists())
                if deleted:
                    self.delete_Refresh(deleted) # markers are already popped

    def delete_Refresh(self, deleted, check_existence=False):
        deleted = super(InstallersData, self).delete_Refresh(deleted,
                                                             check_existence)
        if deleted: self.irefresh(what='I', deleted=deleted)

    def copy_installer(self,item,destName,destDir=None):
        """Copies archive to new location."""
        if item == self.lastKey: return
        destDir = destDir or self.store_dir
        apath = self.store_dir.join(item)
        apath.copyTo(destDir.join(destName))
        if destDir == self.store_dir:
            self[destName] = installer = copy.copy(self[item])
            installer.archive = destName.s
            installer.isActive = False
            self.moveArchives([destName], self[item].order + 1)

    def move_info(self, filename, destDir):
        # hasty method to use in UIList.hide(), see FileInfos.move_info()
        self.store_dir.join(filename).moveTo(destDir.join(filename))

    def move_infos(self, sources, destinations, window):
        moved = super(InstallersData, self).move_infos(sources, destinations,
                                                       window)
        self.irefresh(what='I', pending=moved)
        return moved

    #--Refresh Functions ------------------------------------------------------
    class _RefreshInfo(object):
        """Refresh info for Bash Installers directory."""
        def __init__(self, deleted=(), pending=(), projects=()):
            self.deleted = frozenset(deleted or ())   # deleted keys
            self.pending = frozenset(pending or ())   # new or updated keys
            self.projects = frozenset(projects or ()) # all project keys

        def refresh_needed(self):
            return bool(self.deleted or self.pending)

    @projects_walk_cache
    def _refreshInstallers(self, progress, fullRefresh, refresh_info, deleted,
                           pending, projects):
        """Update given installers or scan the installers' directory. Any of
        deleted, pending takes priority over refresh_info. If all refresh
        parameters are None, the Installers dir will be scanned for changes.
        Note that if any of those are not None "changed" will be always
        True, triggering the rest of the refreshes in irefresh. Once
        refresh_info is calculated, deleted are removed, refreshBasic is
        called on added/updated files and crc_installer updated. If you
        don't need that last step you may directly call refreshBasic.
        :type progress: bolt.Progress | None
        :type fullRefresh: bool
        :type refresh_info: InstallersData._RefreshInfo | None
        :type deleted: collections.Iterable[bolt.Path] | None
        :type pending: collections.Iterable[bolt.Path] | None
        :type projects: collections.Iterable[bolt.Path] | None
        """
        # TODO(ut):we need to return the refresh_info for more granular control
        # in irefresh and also add extra processing for deleted files
        progress = progress or bolt.Progress()
        #--Current archives
        if refresh_info is deleted is pending is None:
            refresh_info = self.scan_installers_dir(dirs['installers'].list(),
                                                    fullRefresh)
        elif refresh_info is None:
            refresh_info = self._RefreshInfo(deleted, pending, projects)
        changed = refresh_info.refresh_needed()
        for deleted in refresh_info.deleted:
            self.pop(deleted)
        pending, projects = refresh_info.pending, refresh_info.projects
        #--New/update crcs?
        progressSetFull = progress.setFull
        for subPending, iClass in zip((pending - projects, pending & projects),
                                      (InstallerArchive, InstallerProject)):
            if not subPending: continue
            progress(0,_(u"Scanning Packages..."))
            progressSetFull(len(subPending))
            for index,package in enumerate(sorted(subPending)):
                progress(index,_(u'Scanning Packages...')+u'\n'+package.s)
                installer = self.get(package, None)
                if not installer:
                    installer = self.setdefault(package, iClass(package))
                installer.refreshBasic(SubProgress(progress, index, index + 1),
                                       recalculate_project_crc=fullRefresh)
        if changed: self.crc_installer = dict((x.crc, x) for x in
                        self.itervalues() if isinstance(x, InstallerArchive))
        return changed

    def applyEmbeddedBCFs(self, installers=None, destArchives=None,
                          progress=bolt.Progress()):
        if installers is None:
            installers = [x for x in self.itervalues() if
                          isinstance(x, InstallerArchive) and x.hasBCF]
        if not installers: return False
        if not destArchives:
            destArchives = [GPath(u'[Auto applied BCF] %s' % x.archive) for x
                            in installers]
        progress.setFull(len(installers))
        pending = []
        for i, (installer, destArchive) in enumerate(zip(installers,
                        destArchives)): # no izip - we may modify installers
            progress(i, installer.archive)
            #--Extract the embedded BCF and move it to the Converters folder
            Installer.rmTempDir()
            installer.unpackToTemp([installer.hasBCF],
                                   SubProgress(progress, i, i + 0.5))
            srcBcfFile = Installer.getTempDir().join(installer.hasBCF)
            bcfFile = dirs['converters'].join(u'temp-' + srcBcfFile.stail)
            srcBcfFile.moveTo(bcfFile)
            Installer.rmTempDir()
            #--Create the converter, apply it
            converter = InstallerConverter(bcfFile.tail)
            try:
                msg = u'%s: ' % destArchive.s + _(
                    u'An error occurred while applying an Embedded BCF.')
                self.apply_converter(converter, destArchive,
                                     SubProgress(progress, i + 0.5, i + 1.0),
                                     msg, installer, pending)
            except StateError:
                # maybe short circuit further attempts to extract
                # installer.hasBCF = False
                installers.remove(installer)
            finally: bcfFile.remove()
        self.irefresh(what='I', pending=pending)
        return pending, list(GPath(x.archive) for x in installers)

    def apply_converter(self, converter, destArchive, progress, msg,
                        installer=None, pending=None, show_warning=None,
                        position=-1):
        try:
            converter.apply(destArchive, self.crc_installer,
                            bolt.SubProgress(progress, 0.0, 0.99),
                            embedded=installer.crc if installer else 0L)
            #--Add the new archive to Bash
            if destArchive not in self:
                self[destArchive] = InstallerArchive(destArchive)
                reorder = True
            else: reorder = False
            #--Apply settings from the BCF to the new InstallerArchive
            iArchive = self[destArchive]
            converter.applySettings(iArchive)
            if reorder and position >= 0:
                self.moveArchives([destArchive], position)
            elif reorder and installer: #embedded BCF, move after its installer
                self.moveArchives([destArchive], installer.order + 1)
            if pending is not None: # caller must take care of the else below !
                pending.append(destArchive)
            else:
                self.irefresh(what='I', pending=[destArchive])
                return iArchive
        except StateError:
            deprint(msg, traceback=True)
            if show_warning: show_warning(msg)

    def scan_installers_dir(self, installers_paths=(), fullRefresh=False):
        """March through the Bash Installers dir scanning for new and modified
        projects/packages, skipping as necessary.
        :rtype: InstallersData._RefreshInfo"""
        installers = set()
        installersJoin = dirs['installers'].join
        pending, projects = set(), set()
        for item in installers_paths:
            if item.s.lower().startswith((u'bash',u'--')): continue
            apath = installersJoin(item)
            if apath.isfile() and item.cext in readExts:
                installer = self.get(item)
            elif apath.isdir(): # Project - autorefresh those only if specified
                if item.s.lower() in self.installers_dir_skips:
                    continue # skip Bash directories and user specified ones
                installer = self.get(item)
                projects.add(item)
                # refresh projects once on boot even if skipRefresh is on
                if installer and not installer.project_refreshed:
                    pending.add(item)
                    continue
                elif installer and not fullRefresh and (installer.skipRefresh
                       or not settings['bash.installers.autoRefreshProjects']):
                    installers.add(item) # installer is present
                    continue # and needs not refresh
            else:
                continue ##: treat symlinks
            if fullRefresh or not installer or installer.size_or_mtime_changed(
                    apath):
                pending.add(item)
            else: installers.add(item)
        deleted = set(x for x, y in self.iteritems() if not isinstance(
            y, InstallerMarker)) - installers - pending
        refresh_info = self._RefreshInfo(deleted, pending, projects)
        return refresh_info

    def refreshConvertersNeeded(self):
        """Return True if refreshConverters is necessary. (Point is to skip
        use of progress dialog when possible)."""
        return self.converters_data.refreshConvertersNeeded()

    def refreshOrder(self):
        """Refresh installer status."""
        inOrder, pending = [], []
        # not specifying the key below results in double time
        for archive, installer in sorted(self.iteritems(), key=itemgetter(0)):
            if installer.order >= 0:
                inOrder.append((archive, installer))
            else:
                pending.append((archive, installer))
        inOrder.sort(key=lambda x: x[1].order)
        for dex, (key, value) in enumerate(inOrder):
            if self.lastKey == key:
                inOrder[dex:dex] = pending
                break
        else:
            inOrder += pending
        changed = False
        for order, (archive, installer) in enumerate(inOrder):
            if installer.order != order:
                installer.order = order
                changed = True
        return changed

    def refreshNorm(self):
        """Refresh self.abnorm_sizeCrc."""
        active = [x for x in self.itervalues() if x.isActive]
        active.sort(key=lambda pac: pac.order)
        #--norm
        norm_sizeCrc = {}
        normUpdate = norm_sizeCrc.update
        for package in active:
            normUpdate(package.data_sizeCrc)
        #--Abnorm
        abnorm_sizeCrc = {}
        dataGet = self.data_sizeCrcDate.get
        for path,sizeCrc in norm_sizeCrc.iteritems():
            sizeCrcDate = dataGet(path)
            if sizeCrcDate and sizeCrc != sizeCrcDate[:2]:
                abnorm_sizeCrc[path] = sizeCrcDate[:2]
        self.abnorm_sizeCrc, oldAbnorm_sizeCrc = \
            abnorm_sizeCrc, self.abnorm_sizeCrc
        return abnorm_sizeCrc != oldAbnorm_sizeCrc

    def refreshInstallersStatus(self):
        """Refresh installer status."""
        changed = False
        for installer in self.itervalues():
            changed |= installer.refreshStatus(self)
        return changed

    def _refresh_from_data_dir(self, progress=None, recalculate_all_crcs=False):
        """Update self.data_sizeCrcDate, using current data_sizeCrcDate as a
        cache.

        Recalculates crcs for all espms in Data/ directory and all other
        files whose cached date or size has changed. Will skip directories (
        but not files) specified in Installer global skips and remove empty
        dirs if the setting is on."""
        #--Scan for changed files
        progress = progress if progress else bolt.Progress()
        progress_msg = dirs['mods'].stail + u': ' + _(u'Pre-Scanning...')
        progress(0, progress_msg + u'\n')
        progress.setFull(1)
        dirDirsFiles, emptyDirs = [], set()
        dirDirsFilesAppend, emptyDirsAdd = dirDirsFiles.append, emptyDirs.add
        asRoot = dirs['mods'].s
        relPos = len(asRoot) + 1
        for asDir, sDirs, sFiles in os.walk(asRoot):
            progress(0.05, progress_msg + (u'\n%s' % asDir[relPos:]))
            if not (sDirs or sFiles): emptyDirsAdd(GPath(asDir))
            if asDir == asRoot: InstallersData._skips_in_data_dir(sDirs)
            dirDirsFilesAppend((asDir, sDirs, sFiles))
        progress(0, _(u"%s: Scanning...") % dirs['mods'].stail)
        new_sizeCrcDate, pending, pending_size = \
            self._process_data_dir(dirDirsFiles, progress)
        #--Remove empty dirs?
        if settings['bash.installers.removeEmptyDirs']:
            for empty in emptyDirs:
                try: empty.removedirs()
                except OSError: pass
        changed = Installer.final_update(new_sizeCrcDate,
                                         self.data_sizeCrcDate, pending,
                                         pending_size, progress,
                                         recalculate_all_crcs,
                                         dirs['mods'].stail)
        self.update_for_overridden_skips(progress=progress) #after final_update
        #--Done
        return changed

    def _process_data_dir(self, dirDirsFiles, progress):
        """Construct dictionaries mapping the paths in dirDirsFiles to
        filesystem attributes. Old data_SizeCrcDate is used to decide which
        files need their crc recalculated. Return a tuple containing:
        - new_sizeCrcDate and pending: two newly constructed dicts mapping
        paths to their size, date and absolute path and also the crc (for
        new_sizeCrcDate) if the cached value is valid (no change in mod time
        or size of the file)
        - the size of pending files used in displaying crc calculation progress
        Compare to similar code in InstallerProject._refresh_from_project_dir

        :param dirDirsFiles: list of tuples in the format of the output of walk
        """
        progress.setFull(1 + len(dirDirsFiles))
        pending, pending_size = {}, 0
        new_sizeCrcDate = {}
        oldGet = self.data_sizeCrcDate.get
        norm_ghost = Installer.getGhosted()
        ghost_norm = dict((y, x) for x, y in norm_ghost.iteritems())
        bethFiles = set() if settings[
            'bash.installers.autoRefreshBethsoft'] else bush.game.bethDataFiles
        skipExts = Installer.skipExts
        ghostGet = ghost_norm.get
        relPos = len(bass.dirs['mods'].s) + 1
        for index, (asDir, __sDirs, sFiles) in enumerate(dirDirsFiles):
            progress(index)
            rsDir = asDir[relPos:]
            for sFile in sFiles:
                sFileLower = sFile.lower()
                ext = sFileLower[sFileLower.rfind(u'.'):]
                top_level_espm = False
                if not rsDir:
                    if ext in skipExts: continue
                    if sFileLower in bethFiles: continue
                    top_level_espm = ext in {u'.esp', u'.esm'}
                    rpFile = GPath(os.path.join(rsDir, sFile))
                    rpFile = ghostGet(rpFile,rpFile)
                else: rpFile = GPath(os.path.join(rsDir, sFile))
                asFile = os.path.join(asDir, sFile)
                # below calls may now raise even if "werr.winerror = 123"
                try:
                    size = os.path.getsize(asFile)
                    get_mtime = os.path.getmtime(asFile)
                    date = int(get_mtime)
                    oSize, oCrc, oDate = oldGet(rpFile, (0, 0, 0))
                    if top_level_espm or size != oSize or date != oDate:
                        pending[rpFile] = (size, oCrc, date, asFile)
                        pending_size += size
                    else:
                        new_sizeCrcDate[rpFile] = (oSize, oCrc, oDate, asFile)
                except OSError as e:
                    if e.errno == errno.ENOENT: continue # file does not exist
                    raise
        return new_sizeCrcDate, pending, pending_size

    def reset_refresh_flag_on_projects(self):
        for installer in self.itervalues():
            if isinstance(installer, InstallerProject):
                installer.project_refreshed = False

    @staticmethod
    def _skips_in_data_dir(sDirs):
        """Skip some top level directories based on global settings - EVEN
        on a fullRefresh."""
        log = None
        if inisettings['KeepLog'] > 1:
            try: log = inisettings['LogFile'].open('a', encoding='utf-8-sig')
            except: pass
        setSkipOBSE = not settings['bash.installers.allowOBSEPlugins']
        setSkipDocs = settings['bash.installers.skipDocs']
        setSkipImages = settings['bash.installers.skipImages']
        newSDirs = (x for x in sDirs if x.lower() not in Installer.dataDirsMinus)
        if settings['bash.installers.skipDistantLOD']:
            newSDirs = (x for x in newSDirs if x.lower() != u'distantlod')
        if settings['bash.installers.skipLandscapeLODMeshes']:
            newSDirs = (x for x in newSDirs if x.lower() != os.path.join(
                u'meshes', u'landscape', u'lod'))
        if settings['bash.installers.skipScreenshots']:
            newSDirs = (x for x in newSDirs if x.lower() != u'screenshots')
        # LOD textures
        if settings['bash.installers.skipLandscapeLODTextures'] and settings[
            'bash.installers.skipLandscapeLODNormals']:
            newSDirs = (x for x in newSDirs if x.lower() != os.path.join(
                u'textures', u'landscapelod', u'generated'))
        if setSkipOBSE:
            newSDirs = (x for x in newSDirs if
                        x.lower() != bush.game.se.shortName.lower())
        if bush.game.sd.shortName and setSkipOBSE:
            newSDirs = (x for x in newSDirs if
                        x.lower() != bush.game.sd.installDir.lower())
        if setSkipDocs and setSkipImages:
            newSDirs = (x for x in newSDirs if x.lower() != u'docs')
        newSDirs = (x for x in newSDirs if
                    x.lower() not in bush.game.SkipBAINRefresh)
        sDirs[:] = [x for x in newSDirs]
        if log:
            log.write(u'(in refreshSizeCRCDate after accounting for skipping) '
                      u'sDirs = %s\r\n' % (sDirs[:]))
            log.close()

    def update_data_SizeCrcDate(self, dest_paths, progress=None):
        """Update data_SizeCrcDate with info on given paths.
        :param progress: must be zeroed - message is used in _process_data_dir
        :param dest_paths: set of paths relative to Data/ - may not exist."""
        root_files = []
        norm_ghost = Installer.getGhosted()
        for path in dest_paths:
            sp = path.s.rsplit(os.sep, 1) # split into ['rel_path, 'file']
            if len(sp) == 1: # top level file
                name = norm_ghost.get(path, path)
                root_files.append((bass.dirs['mods'].s, name.s))
            else:
                root_files.append((bass.dirs['mods'].join(sp[0]).s, sp[1]))
        root_dirs_files = []
        root_files.sort(key=itemgetter(0)) # must sort on same key as groupby
        for key, val in groupby(root_files, key=itemgetter(0)):
            root_dirs_files.append((key, [], [j for i, j in val]))
        progress = progress or bolt.Progress()
        new_sizeCrcDate, pending, pending_size = self._process_data_dir(
            root_dirs_files, progress)
        deleted_or_pending = set(dest_paths) - set(new_sizeCrcDate)
        for d in deleted_or_pending: self.data_sizeCrcDate.pop(d, None)
        Installer.calc_crcs(pending, pending_size, bass.dirs['mods'].stail,
                            new_sizeCrcDate, progress)
        for rpFile, (size, crc, date, _asFile) in new_sizeCrcDate.iteritems():
            self.data_sizeCrcDate[rpFile] = (size, crc, date)

    def update_for_overridden_skips(self, dont_skip=None, progress=None):
        if dont_skip is not None:
            dont_skip.difference_update(self.data_sizeCrcDate)
            self.overridden_skips |= dont_skip
        elif self.__clean_overridden_after_load:
            self.overridden_skips.difference_update(self.data_sizeCrcDate)
            self.__clean_overridden_after_load = False
        new_skips_overrides = self.overridden_skips - set(self.data_sizeCrcDate)
        progress = progress or bolt.Progress()
        progress(0, (_(u"%s: Skips overrides...") % dirs['mods'].stail)+ u'\n')
        self.update_data_SizeCrcDate(new_skips_overrides, progress)

    #--Operations -------------------------------------------------------------
    def moveArchives(self,moveList,newPos):
        """Move specified archives to specified position."""
        old_ordered = self.sorted_pairs(set(self.data) - set(moveList))
        new_ordered = self.sorted_pairs(moveList)
        if newPos >= len(self.keys()): newPos = len(self.keys()) - 1
        for index,(archive,installer) in enumerate(old_ordered[:newPos]):
            installer.order = index
        for index,(archive,installer) in enumerate(new_ordered):
            installer.order = newPos + index
        for index,(archive,installer) in enumerate(old_ordered[newPos:]):
            installer.order = newPos + len(new_ordered) + index
        self.setChanged()

    @staticmethod
    def updateTable(destFiles, value):
        """Set the 'installer' column in mod and ini tables for the
        destFiles."""
        mods_changed, inis_changed = False, False
        for i in destFiles:
            if value and reModExt.match(i.cext): # if value == u'' we come from delete !
                mods_changed = True
                modInfos.table.setItem(i, 'installer', value)
            elif i.head.cs == u'ini tweaks':
                inis_changed = True
                if value:
                    iniInfos.table.setItem(i.tail, 'installer', value)
                else: # installer is the only column used in iniInfos table
                    iniInfos.table.delRow(i.tail)
        return mods_changed, inis_changed

    #--Install
    def _createTweaks(self, destFiles, installer, tweaksCreated):
        """Generate INI Tweaks when a CRC mismatch is detected while
        installing a mod INI (not ini tweak) in the Data/ directory.

        If the current CRC of the ini is different than the one BAIN is
        installing, a tweak file will be generated. Call me *before*
        installing the new inis then call _editTweaks() to populate the tweaks.
        """
        dest_files = (x for x in destFiles if x .cext in (u'.ini', u'.cfg') and
                # don't create ini tweaks for overridden ini tweaks...
                x.head.cs != u'ini tweaks')
        for relPath in dest_files:
            oldCrc = self.data_sizeCrcDate.get(relPath, (None, None, None))[1]
            newCrc = installer.data_sizeCrc.get(relPath, (None, None))[1]
            if oldCrc is None or newCrc is None or newCrc == oldCrc: continue
            iniAbsDataPath = dirs['mods'].join(relPath)
            # Create a copy of the old one
            baseName = dirs['tweaks'].join(u'%s, ~Old Settings [%s].ini' % (
                iniAbsDataPath.sbody, installer.archive))
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
            with tweakPath.open('r') as tweak:
                tweak_lines = tweak.readlines()
            for (text, section, setting, value, status, lineNo,
                 deleted) in iniFile.get_lines_infos(tweak_lines):
                if status in (10, -10):
                    # A setting that exists in both INI's, but is different,
                    # or a setting that doesn't exist in the new INI.
                    if section == u']set[' or section == u']setGS[' or section == u']SetNumericGameSetting[':
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

    def _install(self, packages, refresh_ui, progress=None, last=False,
                 override=True):
        """Install selected packages.
        what:
            'MISSING': only missing files.
            Otherwise: all (unmasked) files.
        """
        progress = progress or bolt.Progress()
        tweaksCreated = set()
        #--Mask and/or reorder to last
        mask = set()
        if last:
            self.moveArchives(packages, len(self))
        else:
            maxOrder = max(self[x].order for x in packages)
            for installer in self.itervalues():
                if installer.order > maxOrder and installer.isActive:
                    mask |= set(installer.data_sizeCrc)
        #--Install packages in turn
        progress.setFull(len(packages))
        for index, (archive, installer) in enumerate(
                self.sorted_pairs(packages, reverse=True)):
            progress(index,archive.s)
            destFiles = set(installer.data_sizeCrc) - mask
            if not override:
                destFiles &= installer.missingFiles
            if destFiles:
                self._createTweaks(destFiles, installer, tweaksCreated)
                installer.install(destFiles, self.data_sizeCrcDate,
                                  SubProgress(progress, index, index + 1))
                mods_changed, inis_changed = InstallersData.updateTable(
                    destFiles, archive.s)
                refresh_ui[0] |= mods_changed
                refresh_ui[1] |= inis_changed
            installer.isActive = True
            mask |= set(installer.data_sizeCrc)
        if tweaksCreated:
            self._editTweaks(tweaksCreated)
            refresh_ui[1] |= bool(tweaksCreated)
        return tweaksCreated

    def sorted_pairs(self, package_keys=None, reverse=False):
        """Return pairs of key, installer for package_keys in self, sorted by
        install order.
        :type package_keys: None | collections.Iterable[Path]
        :rtype: list[(Path, Installer)]
        """
        if package_keys is None: package_keys = self.keys()
        pairs = [(installer, self[installer]) for installer in package_keys]
        return sorted(pairs, key=lambda tup: tup[1].order, reverse=reverse)

    def bain_install(self, packages, refresh_ui, progress=None, last=False,
                     override=True):
        try: return self._install(packages, refresh_ui, progress, last,
                                  override)
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

    def _removeFiles(self, removes, refresh_ui, progress=None):
        """Performs the actual deletion of files and updating of internal data.clear
           used by 'bain_uninstall' and 'bain_anneal'."""
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
                env.shellDelete(nonPlugins, parent=parent)
            #--Delete mods and remove them from load order
            if removedPlugins:
                refresh_ui[0] = True
                modInfos.delete(removedPlugins, doRefresh=False, recycle=False)
        except (bolt.CancelError, bolt.SkipError): ex = sys.exc_info()
        except:
            ex = sys.exc_info()
            raise
        finally:
            if ex:removes = [f for f in removes if not modsDirJoin(f).exists()]
            mods_changed, inis_changed = InstallersData.updateTable(removes,
                                                                    u'')
            refresh_ui[0] |= mods_changed
            refresh_ui[1] |= inis_changed
            #--Update InstallersData
            data_sizeCrcDatePop = self.data_sizeCrcDate.pop
            for relPath in removes:
                data_sizeCrcDatePop(relPath, None)

    def __restore(self, archive, installer, removes, restores):
        """Populate restores dict with files to be restored by this
        installer, removing those from removes.

        Returns all of the files this installer would install. Used by
        'bain_uninstall' and 'bain_anneal'."""
        # get all destination files for this installer
        files = set(installer.data_sizeCrc)
        # keep those to be removed while not restored by a higher order package
        myRestores = (removes & files) - set(restores)
        for dest_file in myRestores:
            if installer.data_sizeCrc[dest_file] != \
                    self.data_sizeCrcDate.get(dest_file,(0, 0, 0))[:2]:
                restores[dest_file] = archive
            removes.discard(dest_file)
        return files

    def bain_uninstall(self, unArchives, refresh_ui, progress=None):
        """Uninstall selected archives."""
        if unArchives == 'ALL': unArchives = self.data
        unArchives = set(unArchives)
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
        for archive, installer in self.sorted_pairs(reverse=True):
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
                masked |= self.__restore(archive, installer, removes, restores)
        try:
            #--Remove files, update InstallersData, update load order
            self._removeFiles(removes, refresh_ui, progress)
            #--De-activate
            for archive in unArchives:
                self[archive].isActive = False
            #--Restore files
            if settings['bash.installers.autoAnneal']:
                self._restoreFiles(restores, progress, refresh_ui)
        finally:
            self.irefresh(what='NS')

    def _restoreFiles(self, restores, progress, refresh_ui):
        installer_destinations = {}
        restores = sorted(restores.items(), key=itemgetter(1))
        for key, group in groupby(restores, key=itemgetter(1)):
            installer_destinations[key] = set(dest for dest, _key in group)
        if not installer_destinations: return
        installer_destinations = sorted(installer_destinations.items(),
            key=lambda item: self[item[0]].order)
        progress.setFull(len(installer_destinations))
        for index, (archive, destFiles) in enumerate(installer_destinations):
            progress(index, archive.s)
            if destFiles:
                installer = self[archive]
                installer.install(destFiles, self.data_sizeCrcDate,
                                  SubProgress(progress, index, index + 1))
                mods_changed, inis_changed = InstallersData.updateTable(
                     destFiles, archive.s)
                refresh_ui[0] |= mods_changed
                refresh_ui[1] |= inis_changed

    def bain_anneal(self, anPackages, refresh_ui, progress=None):
        """Anneal selected packages. If no packages are selected, anneal all.
        Anneal will:
        * Correct underrides in anPackages.
        * Install missing files from active anPackages."""
        progress = progress if progress else bolt.Progress()
        anPackages = set(anPackages or self.keys())
        #--Get remove/refresh files from anPackages
        removes = set()
        for package in anPackages:
            installer = self[package]
            removes |= installer.underrides
            if installer.isActive:
                removes |= installer.missingFiles
                removes |= set(installer.dirty_sizeCrc)
            installer.dirty_sizeCrc.clear()
        #--March through packages in reverse order...
        restores = {}
        for archive, installer in self.sorted_pairs(reverse=True):
            #--Other active package. May provide a restore file.
            #  And/or may block later uninstalls.
            if installer.isActive:
                self.__restore(archive, installer, removes, restores)
        try:
            #--Remove files, update InstallersData, update load order
            self._removeFiles(removes, refresh_ui, progress)
            #--Restore files
            self._restoreFiles(restores, progress, refresh_ui)
        finally:
            self.irefresh(what='NS')

    def clean_data_dir(self, refresh_ui):
        getArchiveOrder = lambda x: x.order
        keepFiles = set()
        for installer in sorted(self.values(), key=getArchiveOrder,
                                reverse=True):
            if installer.isActive:
                keepFiles.update(installer.data_sizeCrc)
        keepFiles.update((GPath(f) for f in bush.game.allBethFiles))
        keepFiles.update((GPath(f) for f in bush.game.wryeBashDataFiles))
        keepFiles.update((GPath(f) for f in bush.game.ignoreDataFiles))
        removes = set(self.data_sizeCrcDate) - keepFiles
        destDir = dirs['bainData'].join(u'Data Folder Contents (%s)' %
            bolt.timestamp())
        skipPrefixes = [os.path.normcase(skipDir)+os.sep for skipDir in bush.game.wryeBashDataDirs]
        skipPrefixes.extend([os.path.normcase(skipDir)+os.sep for skipDir in bush.game.ignoreDataDirs])
        skipPrefixes.extend([os.path.normcase(skipPrefix) for skipPrefix in bush.game.ignoreDataFilePrefixes])
        skipPrefixes = tuple(skipPrefixes)
        try:
            self._clean_data_dir(self.data_sizeCrcDate, destDir, removes,
                                 skipPrefixes, refresh_ui)
        finally:
            self.irefresh(what='NS')

    @staticmethod
    def _clean_data_dir(data_sizeCrcDate, destDir, removes, skipPrefixes,
                        refresh_ui): # we do _not_ remove Ini Tweaks/*
        emptyDirs = set()
        def isMod(p): return reModExt.search(p.s) is not None
        for filename in removes:
            # don't remove files in Wrye Bash-related directories
            if filename.cs.startswith(skipPrefixes): continue
            full_path = dirs['mods'].join(filename)
            try:
                if full_path.exists():
                    full_path.moveTo(destDir.join(filename))
                    if not refresh_ui[0]: refresh_ui[0] = isMod(full_path)
                else: # Try if it's a ghost - belongs to modInfos...
                    full_path = GPath(full_path.s + u'.ghost')
                    if full_path.exists():
                        full_path.moveTo(destDir.join(filename))
                        refresh_ui[0] = True
                    else: continue # don't pop if file was not removed
                data_sizeCrcDate.pop(filename, None)
                emptyDirs.add(full_path.head)
            except:
                # It's not imperative that files get moved, so ignore errors
                deprint(u'Clean Data: moving %s to % s failed' % (
                            full_path, destDir), traceback=True)
        for emptyDir in emptyDirs:
            if emptyDir.isdir() and not emptyDir.list():
                emptyDir.removedirs()

    #--Utils
    def getConflictReport(self,srcInstaller,mode):
        """Returns report of overrides for specified package for display on conflicts tab.
        mode: OVER: Overrides; UNDER: Underrides"""
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
        getBSAOrder = lambda b: load_order.activeCached().index(b[1].root + ".esp") ##: why list() ?
        # Calculate bsa conflicts
        if showBSA:
            def _filter_bsas(li): return filter(BSAInfos.rightFileType, li)
            is_act = load_order.isActiveCached
            def _bsa_mod_active(li): return [b for b in li if
                        is_act(b.root + ".esp")] ##: or is_act(b.root + ".esm")
            # Create list of active BSA files in srcInstaller
            srcBSAFiles = _filter_bsas(srcInstaller.data_sizeCrc)
            activeSrcBSAFiles = _bsa_mod_active(srcBSAFiles)
            bsas = [(x, bsaInfos[x]) for x in activeSrcBSAFiles if
                    x in bsaInfos.keys()]
            # Create list of all assets in BSA files for srcInstaller
            srcBSAContents = []
            for x,y in bsas: srcBSAContents.extend(y.assets)
            # Create a list of all active BSA Files except the ones in srcInstaller
            activeBSAFiles = []
            for package, installer in self.iteritems():
                if installer.order == srcOrder: continue
                if not installer.isActive: continue
#                print("Current Package: {}".format(package))
                inst_bsas = _filter_bsas(installer.data_sizeCrc)
                activeBSAFiles.extend([(package, x, bsaInfos[x])
                    for x in inst_bsas if x in bsaInfos.keys() and
                        load_order.isActiveCached(x.root + ".esp")])
            # Calculate all conflicts and save them in bsaConflicts
#            print("Active BSA Files: {}".format(activeBSAFiles))
            for package, bsaPath, bsa_info in sorted(activeBSAFiles,key=getBSAOrder):
                curAssets = bsa_info.assets
#                print("Current Assets: {}".format(curAssets))
                curConflicts = Installer.sortFiles([x for x in curAssets if x in srcBSAContents])
#                print("Current Conflicts: {}".format(curConflicts))
                if curConflicts: bsaConflicts.append((package, bsaPath, curConflicts))
#        print("BSA Conflicts: {}".format(bsaConflicts))
        # Calculate esp/esm conflicts
        for package, installer in self.sorted_pairs():
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
                    buff.write(u'==%X== %s : %s\n' % (order, package, bsa))
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
            #--List
            log(u'[spoiler][xml]\n',False)
            for package, installer in self.sorted_pairs():
                prefix = u'%03d' % installer.order
                if isinstance(installer, InstallerMarker):
                    log(u'%s - %s' % (prefix, package.s))
                elif installer.isActive:
                    log(u'++ %s - %s (%08X) (Installed)' % (
                        prefix, package.s, installer.crc))
                elif showInactive:
                    log(u'-- %s - %s (%08X) (Not Installed)' % (
                        prefix, package.s, installer.crc))
            log(u'[/xml][/spoiler]')
            return bolt.winNewLines(log.out.getvalue())

    def filterInstallables(self, installerKeys):
        """Return a sublist of installerKeys that can be installed -
        installerKeys must be in data or a KeyError is raised.
        :param installerKeys: an iterable of bolt.Path
        :return: a list of installable packages/projects bolt.Path
        """
        def installable(x): # type -> 0: unset/invalid; 1: simple; 2: complex
            return self[x].type in (1, 2) and isinstance(self[x],
                (InstallerArchive, InstallerProject))
        return filter(installable, installerKeys)

    def filterPackages(self, installerKeys):
        """Remove markers from installerKeys.
        :type installerKeys: collections.Iterable[bolt.Path]
        :rtype: list[bolt.Path]
        """
        def _package(x):
            return isinstance(self[x], (InstallerArchive, InstallerProject))
        return filter(_package, installerKeys)

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

# Mergeability ----------------------------------------------------------------
##: belong to patcher/patch_files (?) but used in modInfos - cyclic imports
def _is_mergeable_no_load(modInfo, verbose):
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

def pbash_mergeable_no_load(modInfo, verbose):
    reasons = _is_mergeable_no_load(modInfo, verbose)
    if isinstance(reasons, list):
        reasons = u''.join(reasons)
    elif not reasons:
        return False # non verbose mode
    else: # True
        reasons = u''
    #--Missing Strings Files?
    if modInfo.isMissingStrings():
        if not verbose: return False
        reasons += u'\n.    '+_(u'Missing String Translation Files (Strings\\%s_%s.STRINGS, etc).') % (
            modInfo.name.sbody, oblivionIni.get_ini_language())
    if reasons: return reasons
    return True

def isPBashMergeable(modInfo,verbose=True):
    """Returns True or error message indicating whether specified mod is mergeable."""
    reasons = pbash_mergeable_no_load(modInfo, verbose)
    if isinstance(reasons, unicode):
        pass
    elif not reasons:
        return False # non verbose mode
    else: # True
        reasons = u''
    #--Load test
    mergeTypes = set([recClass.classType for recClass in bush.game.mergeClasses])
    modFile = ModFile(modInfo, LoadFactory(False, *mergeTypes))
    try:
        modFile.load(True,loadStrings=False)
    except ModError as error:
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

def cbash_mergeable_no_load(modInfo, verbose):
    """Check if mod is mergeable without taking into account the rest of mods"""
    return _is_mergeable_no_load(modInfo, verbose)

def _modIsMergeableLoad(modInfo,verbose):
    """Check if mod is mergeable, loading it and taking into account the
    rest of mods."""
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
                elif not load_order.isActiveCached(master):
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
    if modInfo.name.s == u"Oscuro's_Oblivion_Overhaul.esp":
        if verbose: return u'\n.    ' + _(
            u'Marked non-mergeable at request of mod author.')
        return False
    canmerge = cbash_mergeable_no_load(modInfo, verbose)
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
    gameInis = [OblivionIni(x) for x in bush.game.iniFiles]
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

    #Setup libbsa and LOOT API, needs to be done after the dirs are initialized
    libbsa.Init(bass.dirs['compiled'].s)
    # That didn't work - Wrye Bash isn't installed correctly
    if libbsa.BSAHandle is None:
        raise bolt.BoltError(u'The libbsa API could not be loaded.')
    deprint(u'Using libbsa API version:', libbsa.version)
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
