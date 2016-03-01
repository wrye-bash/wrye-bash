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
import locale
locale.setlocale(locale.LC_ALL,u'')
#locale.setlocale(locale.LC_ALL,'German')
#locale.setlocale(locale.LC_ALL,'Japanese_Japan.932')
import time

# Imports ---------------------------------------------------------------------
#--Python
import cPickle
import collections
import copy
import os
import re
import string
import struct
import sys
from operator import attrgetter
from functools import wraps, partial
from binascii import crc32
from itertools import groupby

#--Local
from .. import bass, bolt, balt, bush, env
from .mods_metadata import ConfigHelpers, libbsa
from ..bass import dirs, inisettings, tooldirs
from .. import patcher # for configIsCBash()
from ..bolt import BoltError, AbstractError, ArgumentError, StateError, \
    PermissionError, FileError, formatInteger, round_size
from ..bolt import LString, GPath, Flags, DataDict, SubProgress, cstrip, \
    deprint, sio, Path
from ..bolt import decode, encode
from ..bolt import defaultExt, compressionSettings, countFilesInArchive, readExts
# cint
from ..cint import ObCollection, CBash
from ..brec import MreRecord, ModReader, ModError, ModWriter, getObjectIndex, \
    getFormIndices
from ..parsers import LoadFactory, ModFile

#--Settings
settings = None

allTags = bush.game.allTags
allTagsSet = set(allTags)
oldTags = sorted((u'Merge',))
oldTagsSet = set(oldTags)

reOblivion = re.compile(
    u'^(Oblivion|Nehrim)(|_SI|_1.1|_1.1b|_1.5.0.8|_GOTY non-SI).esm$', re.U)

undefinedPath = GPath(u'C:\\not\\a\\valid\\path.exe')
undefinedPaths = {GPath(u'C:\\Path\\exe.exe'), undefinedPath}

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
configHelpers = None #--Config Helper files (LOOT Master List, etc.)
load_order = None #--can't import yet as I need bass.dirs to be initialized

#--Header tags
reVersion = re.compile(ur'^(version[:\.]*|ver[:\.]*|rev[:\.]*|r[:\.\s]+|v[:\.\s]+) *([-0-9a-zA-Z\.]*\+?)',re.M|re.I|re.U)

#--Mod Extensions
reComment = re.compile(u'#.*',re.U)
reExGroup = re.compile(u'(.*?),',re.U)
reModExt  = re.compile(ur'\.es[mp](.ghost)?$',re.I|re.U)
reEsmExt  = re.compile(ur'\.esm(.ghost)?$',re.I|re.U)
reEspExt  = re.compile(ur'\.esp(.ghost)?$',re.I|re.U)
reBSAExt  = re.compile(ur'\.bsa(.ghost)?$',re.I|re.U)
reSaveExt = re.compile(ur'(quicksave(\.bak)+|autosave(\.bak)+|\.(es|fo)[rs])$',re.I|re.U)
reINIExt  = re.compile(ur'\.ini$',re.I|re.U)
reTesNexus = re.compile(ur'(.*?)(?:-(\d{1,6})(?:\.tessource)?(?:-bain)?(?:-\d{0,6})?(?:-\d{0,6})?(?:-\d{0,6})?(?:-\w{0,16})?(?:\w)?)?(\.7z|\.zip|\.rar|\.7z\.001|)$',re.I|re.U)
reTESA = re.compile(ur'(.*?)(?:-(\d{1,6})(?:\.tessource)?(?:-bain)?)?(\.7z|\.zip|\.rar|)$',re.I|re.U)

#------------------------------------------------------------------------------
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

    def _recopy(self, savePath, saveName, pathFunc):
        """Renames/copies cofiles depending on supplied pathFunc."""
        if saveName: savePath = savePath.join(saveName)
        newPaths = CoSaves.getPaths(savePath)
        for oldPath,newPath in zip(self.paths,newPaths):
            if newPath.exists(): newPath.remove()
            if oldPath.exists(): pathFunc(oldPath,newPath)

    def copy(self,savePath,saveName=None):
        """Copies cofiles."""
        self._recopy(savePath, saveName, bolt.Path.copyTo)

    def move(self,savePath,saveName=None):
        """Renames cofiles."""
        self._recopy(savePath, saveName, bolt.Path.moveTo)

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
            IniFile.__init__(self, dirs['app'].join(name), u'General')
            # is bUseMyGamesDirectory set to 0?
            if self.getSetting(u'General',u'bUseMyGamesDirectory',u'1') == u'0':
                return
        # oblivion.ini was not found in the game directory or bUseMyGamesDirectory was not set."""
        # default to user profile directory"""
        IniFile.__init__(self, dirs['saveBase'].join(name), u'General')

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
            source = dirs['templates'].join(bush.game.fsName, u'ArchiveInvalidationInvalidated!.bsa')
            source.mtime = aiBsaMTime
            try:
                env.shellCopy(source, aiBsa, allowUndo=True, autoRename=True)
            except (env.AccessDeniedError, bolt.CancelError, bolt.SkipError):
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
        return mtime

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
        except FileError as error:
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

    def getIniPath(self):
        """Returns path to plugin's INI, if it were to exists."""
        return self.getPath().root.root + u'.ini' # chops off ghost if ghosted

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
            bsaPaths = modInfos.extra_bsas(self, descending=True)
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
        mtime = FileInfo.setmtime(self,mtime)
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
            except struct.error as rex:
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
        except struct.error as rex:
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
            if not filePath.exists(): # untrack - runs on first run !!
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
        # the type of the table keys is always bolt.Path
        self.table = bolt.Table(
            bolt.PickleDict(self.bashDir.join(u'Table.dat')))

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
        except FileError as error:
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
            oldInfo = self.data.get(name) # None if name was in corrupted
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
        env.shellMove(oldPath, newPath, parent=None)
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
            return tableUpdate.values()

    def delete_Refresh(self, deleted): self.refresh()

    #--Move
    def move_info(self, fileName, destDir, doRefresh=True):
        """Moves member file to destDir. Will overwrite!"""
        destDir.makedirs()
        srcPath = self[fileName].getPath()
        destPath = destDir.join(fileName)
        srcPath.moveTo(destPath)
        if doRefresh: self.refresh()

    #--Copy
    def copy_info(self, fileName, destDir, destName=u'', set_mtime=None,
                  doRefresh=True):
        """Copies member file to destDir. Will overwrite!
        :param set_mtime: if None self[fileName].mtime is copied to destination
        """
        destDir.makedirs()
        if not destName: destName = fileName
        destName = GPath(destName)
        srcPath = self[fileName].getPath()
        if destDir == self.dir and destName in self.data:
            destPath = self.data[destName].getPath()
        else:
            destPath = destDir.join(destName)
        srcPath.copyTo(destPath) # will set destPath.mtime to the srcPath one
        if set_mtime is not None:
            if set_mtime == '+1':
                set_mtime = srcPath.mtime + 1
            destPath.mtime = set_mtime
        if doRefresh: self.refresh() ##: maybe avoid it (add copied info manually)
        if destDir == self.dir:
            self.table.copyRow(fileName, destName)
        return set_mtime

    #--Move Exists
    @staticmethod
    def moveIsSafe(fileName,destDir):
        """Bool: Safe to move file to destDir."""
        return not destDir.join(fileName).exists()

#------------------------------------------------------------------------------
class INIInfos(FileInfos):
    def __init__(self):
        FileInfos.__init__(self, dirs['tweaks'], INIInfo, dirs['defaultTweaks'])
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

#------------------------------------------------------------------------------
class ModInfos(FileInfos):
    """Collection of modinfos. Represents mods in the Oblivion\Data directory."""
    #--------------------------------------------------------------------------
    # Load Order stuff is almost all handled in the Plugins class again
    #--------------------------------------------------------------------------
    def __init__(self):
        FileInfos.__init__(self, dirs['mods'], ModInfo)
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

    def masterWithVersion(self, masterName):
        if masterName == u'Oblivion.esm' and self.voCurrent:
            masterName += u' [' + self.voCurrent + u']'
        return masterName

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
        oldMergeable = set(self.mergeable)
        scanList = self.refreshMergeable()
        difMergeable = (oldMergeable ^ self.mergeable) & set(self.keys())
        if scanList:
            with balt.Progress(_(u'Mark Mergeable')+u' '*30) as progress:
                progress.setFull(len(scanList))
                self.rescanMergeable(scanList,progress)
        hasChanged += bool(scanList or difMergeable)
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
        for mpath, modInfo in self.iteritems():
            size, canMerge = name_mergeInfo.get(mpath, (None, None))
            if size == modInfo.size:
                if canMerge: self.mergeable.add(mpath)
            elif reEsmExt.search(mpath.s):
                name_mergeInfo[mpath] = (modInfo.size, False)
            else:
                newMods.append(mpath)
        return newMods

    def rescanMergeable(self,names,progress,doCBash=None):
        """Will rescan specified mods."""
        if doCBash is None:
            doCBash = bool(CBash)
        elif doCBash and not bool(CBash):
            doCBash = False
        is_mergeable = isCBashMergeable if doCBash else isPBashMergeable
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
                    canMerge = is_mergeable(fileInfo)
                except Exception as e:
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
            bsaPaths = self.extra_bsas(modInfo)
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

    def _ini_files(self, descending=False):
        if bush.game.fsName == u'Skyrim':
            iniPaths = (self[name].getIniPath() for name in self.activeCached)
            iniFiles = [IniFile(iniPath) for iniPath in iniPaths if
                        iniPath.exists()]
            if descending: iniFiles.reverse()
            iniFiles.append(oblivionIni)
        else:
            iniFiles = [oblivionIni]
        return iniFiles

    def extra_bsas(self, mod_info, descending=False):
        bsaPaths = [mod_info.getBsaPath()]
        iniFiles = self._ini_files(descending=descending)
        for iniFile in iniFiles:
            for key in (u'sResourceArchiveList', u'sResourceArchiveList2'):
                extraBsa = iniFile.getSetting(u'Archive', key, u'').split(u',')
                extraBsa = [x.strip() for x in extraBsa]
                extraBsa = [dirs['mods'].join(x) for x in extraBsa if x]
                if descending: extraBsa.reverse()
                bsaPaths.extend(extraBsa)
        return [x for x in bsaPaths if x.exists() and x.isfile()]

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

    def getFreeTime(self, startTime, defaultTime='+1'):
        """Tries to return a mtime that doesn't conflict with a mod. Returns defaultTime if it fails."""
        if load_order.usingTxtFile():
            # Doesn't matter - LO isn't determined by mtime
            return time.time()
        else:
            haskey = self.mtime_mods.has_key
            endTime = startTime + 1000 # 1000 (seconds) is an arbitrary limit
            while startTime < endTime:
                if not haskey(startTime):
                    return startTime
                startTime += 1 # step by one second intervals
            return defaultTime

    __max_time = -1
    def mod_timestamp(self):
        """Hack to install mods last in load order (done by liblo when txt
        method used, when mod times method is used make sure we get the latest
        mod time). The mod times stuff must be moved to load_order.py."""
        if not load_order.usingTxtFile():
            maxi = max([x.mtime for x in self.values()] + [self.__max_time])
            maxi = [maxi + 60]
            def timestamps(p):
                if reModExt.search(p.s):
                    self.__max_time = p.mtime = maxi[0]
                    maxi[0] += 60 # space at one minute intervals
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
        deleted = FileInfos.delete(self, fileName, **kwargs)
        # temporarily track deleted mods so BAIN can update its UI
        for d in map(self.dir.join, deleted): # we need absolute paths
            InstallersData.miscTrackedFiles.track(d, factory=self.factory)

    def delete_Refresh(self, deleted):
        # adapted from refresh() (avoid refreshing from the data directory)
        deleted = set(d for d in deleted if not self.dir.join(d).exists())
        if not deleted: return
        for name in deleted:
            self.pop(name, None)
        self.plugins.removeMods(deleted, savePlugins=True)
        self.refreshInfoLists()

    def copy_info(self, fileName, destDir, destName=u'', set_mtime=None,
                  doRefresh=True):
        """Copies modfile and updates mtime table column - not sure why."""
        set_mtime = FileInfos.copy_info(self, fileName, destDir, destName,
                                        set_mtime, doRefresh=doRefresh)
        if destDir == self.dir:
            if set_mtime is None:
                raise BoltError("Always specify mtime when copying to Data/")
            self.mtimes[GPath(destName)] = set_mtime

    def move_info(self, fileName, destDir, doRefresh=True):
        """Moves member file to destDir."""
        self.unselect(fileName, doSave=True)
        FileInfos.move_info(self, fileName, destDir, doRefresh)

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
        except WindowsError as werr:
            while werr.winerror == 32 and self._retry(basePath, oldPath):
                try:
                    basePath.moveTo(oldPath)
                except WindowsError as werr:
                    continue
                break
            else:
                raise
        try:
            newPath.moveTo(basePath)
        except WindowsError as werr:
            while werr.winerror == 32 and self._retry(newPath, basePath):
                try:
                    newPath.moveTo(basePath)
                except WindowsError as werr:
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
        FileInfos.__init__(self, dirs['saveBase'].join(self.localSave), SaveInfo)
        # Save Profiles database
        self.profiles = bolt.Table(bolt.PickleDict(
            dirs['saveBase'].join(u'BashProfiles.dat')))

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

    def copy_info(self, fileName, destDir, destName=u'', set_mtime=None,
                  doRefresh=True):
        """Copies savefile and associated pluggy file."""
        FileInfos.copy_info(self, fileName, destDir, destName, set_mtime,
                            doRefresh=doRefresh)
        CoSaves(self.dir,fileName).copy(destDir,destName or fileName)

    def move_info(self, fileName, destDir, doRefresh=True):
        """Moves member file to destDir. Will overwrite!"""
        FileInfos.move_info(self, fileName, destDir, doRefresh)
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

    @staticmethod
    def check_bsa_timestamps():
        if bush.game.fsName != 'Skyrim' and inisettings['ResetBSATimestamps']:
            if bsaInfos.refresh():
                bsaInfos.resetBSAMTimes()

# TankDatas -------------------------------------------------------------------
#------------------------------------------------------------------------------
class PickleTankData:
    """Mix in class for tank datas built on PickleDicts."""
    def __init__(self,path):
        """Initialize. Definite data from pickledict."""
        self.dictFile = bolt.PickleDict(path)
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
        'missingFiles', 'mismatchedFiles', 'project_refreshed',
        'mismatchedEspms', 'unSize', 'espms', 'underrides', 'hasWizard',
        'espmMap', 'hasReadme', 'hasBCF', 'hasBethFiles')
    __slots__ = persistent + volatile
    #--Package analysis/porting.
    docDirs = {u'screenshots'}
    dataDirsMinus = {u'bash',
                     u'--'}  #--Will be skipped even if hasExtraData == True.
    reDataFile = re.compile(
        ur'(masterlist.txt|dlclist.txt|\.(esp|esm|bsa|ini))$', re.I | re.U)
    docExts = {u'.txt', u'.rtf', u'.htm', u'.html', u'.doc', u'.docx', u'.odt',
               u'.mht', u'.pdf', u'.css', u'.xls', u'.xlsx', u'.ods', u'.odp',
               u'.ppt', u'.pptx'}
    reReadMe = re.compile(
        ur'^.*?([^\\]*)(read[ _]?me|lisez[ _]?moi)([^\\]*)'
        ur'\.(' +ur'|'.join(docExts) + ur')$', re.I | re.U)
    reList = re.compile(
        u'(Solid|Path|Size|CRC|Attributes|Method) = (.*?)(?:\r\n|\n)')
    reValidNamePattern = re.compile(ur'^([^/\\:*?"<>|]+?)(\d*)$', re.I | re.U)
    skipExts = {u'.exe', u'.py', u'.pyc', u'.7z', u'.zip', u'.rar', u'.db',
                u'.ace', u'.tgz', u'.tar', u'.gz', u'.bz2', u'.omod',
                u'.fomod', u'.tb2', u'.lzma', u'.manifest'}
    skipExts.update(set(readExts))
    imageExts = {u'.gif', u'.jpg', u'.png', u'.jpeg', u'.bmp'}
    scriptExts = {u'.txt', u'.ini', u'.cfg'}
    commonlyEditedExts = scriptExts | {u'.xml'}
    #--Needs to be called after bush.game has been set
    dataDirs = dataDirsPlus = ()
    @staticmethod
    def init_bain_dirs():
        """Initialize BAIN data directories on a per game basis."""
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
    def sortFiles(files, __split=os.path.split):
        """Utility function. Sorts files by directory, then file name."""
        sortKeys = dict((x, __split(x)) for x in files)
        return sorted(files, key=sortKeys.__getitem__)

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
        self.fileRootIdex = 0
        self.type = 0 #--Package type: 0: unset/invalid; 1: simple; 2: complex
        self.subNames = []
        self.subActives = []
        self.readMe = None # set by refreshDataSizeCrc (unused for now)
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
        dest_scr = self.refreshDataSizeCrc()
        if self.overrideSkips:
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
        u'--', u'omod conversion data', u'fomod', u'wizard images')
    _silentSkipsEnd = (u'thumbs.db', u'desktop.ini', u'config')

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
            Installer._global_start_skips.append(u'meshes\\landscape\\lod')
        if settings['bash.installers.skipScreenshots']:
            Installer._global_start_skips.append(u'screenshots')
        # LOD textures
        skipLODTextures = settings['bash.installers.skipLandscapeLODTextures']
        skipLODNormals = settings['bash.installers.skipLandscapeLODNormals']
        skipAllTextures = skipLODTextures and skipLODNormals
        if skipAllTextures:
            Installer._global_start_skips.append(u'textures\\landscapelod\\generated')
        elif skipLODTextures: Installer._global_skips.append(lambda f:  f.startswith(
            u'textures\\landscapelod\\generated') and not f.endswith(u'_fn.dds'))
        elif skipLODNormals: Installer._global_skips.append(lambda f:  f.startswith(
            u'textures\\landscapelod\\generated') and f.endswith(u'_fn.dds'))
        # Skipped extensions
        skipObse = not settings['bash.installers.allowOBSEPlugins']
        if skipObse:
            Installer._global_start_skips.append(bush.game.se.shortName.lower() + u'\\')
            Installer._global_skip_extensions |= Installer._executables_ext
        if settings['bash.installers.skipImages']:
            Installer._global_skip_extensions |= Installer.imageExts
        Installer._init_executables_skips()

    @staticmethod
    def init_attributes_process():
        """Populate _attributes_process with functions which decide if the
        file is to be skipped while at the same time update self hasReadme,
        hasWizard, hasBCF attributes."""
        reReadMeMatch = Installer.reReadMe.match
        sep = os.path.sep
        def _process_docs(self, fileLower, full, fileExt):
            if reReadMeMatch(fileLower): self.hasReadme = full
            # let's hope there is no trailing separator - Linux: test fileLower, full are os agnostic
            rsplit = fileLower.rsplit(sep, 1)
            parentDir, fname = (u'', rsplit[0]) if len(rsplit) == 1 else rsplit
            return not self.overrideSkips and settings[
                'bash.installers.skipDocs'] and not (
                fname in bush.game.dontSkip) and not (
                fileExt in bush.game.dontSkipDirs.get(parentDir, []))
        for ext in Installer.docExts:
            Installer._attributes_process[ext] = _process_docs
        def _process_BCF(self, fileLower, full, fileExt):
            if fileLower[-7:-3] == u'-bcf' or u'-bcf-' in fileLower: # DOCS !
                self.hasBCF = full
                return True
            return False
        Installer._attributes_process[defaultExt] = _process_BCF # .7z
        def _process_txt(self, fileLower, full, fileExt):
            if fileLower == u'wizard.txt': # first check if it's the wizard.txt
                self.hasWizard = full
                return True
            return _process_docs(self, fileLower, full, fileExt)
        Installer._attributes_process[u'.txt'] = _process_txt
        Installer._extensions_to_process = set(Installer._attributes_process)

    def _init_skips(self):
        start = [u'sound\\voice'] if self.skipVoices else []
        skips, skip_ext = [], set()
        if not self.overrideSkips: # DOCS !
            skips = list(Installer._global_skips)
            start.extend(Installer._global_start_skips)
            skip_ext = Installer._global_skip_extensions
        if start: skips.append(lambda f: f.startswith((tuple(start))))
        skipEspmVoices = not self.skipVoices and set(
                x.cs for x in self.espmNots)
        if skipEspmVoices:
            def _skip_espm_voices(fileLower):
                farPos = fileLower.startswith(
                    u'sound\\voice\\') and fileLower.find(u'\\', 12)
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
                    exeDir=(bush.game.se.shortName.lower() + u'\\'),
                    dialogTitle=bush.game.se.shortName + _(u' DLL Warning'))
            Installer._executables_process[u'.dll'] = \
            Installer._executables_process[u'.dlx'] = _obse
        if bush.game.sd.shortName:
            _asi = partial(__skipExecutable,
                   desc=_(u'%s plugin ASI') % bush.game.sd.longName,
                   ext=(_(u'an asi')),
                   exeDir=(bush.game.sd.installDir.lower() + u'\\'),
                   dialogTitle=bush.game.sd.longName + _(u' ASI Warning'))
            Installer._executables_process[u'.asi'] = _asi
        if bush.game.sp.shortName:
            _jar = partial(__skipExecutable,
                   desc=_(u'%s patcher JAR') % bush.game.sp.longName,
                   ext=(_(u'a jar')),
                   exeDir=(bush.game.sp.installDir.lower() + u'\\'),
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
        self.readMe = self.packageDoc = self.packagePic = None
        for attr in {'skipExtFiles','skipDirFiles','espms'}:
            object.__getattribute__(self,attr).clear()
        dest_src = {}
        #--Bad archive?
        if type_ not in {1,2}: return dest_src
        archiveRoot = GPath(self.archive).sroot if isinstance(self,
                InstallerArchive) else self.archive
        docExts = self.docExts
        imageExts = self.imageExts
        docDirs = self.docDirs
        dataDirsPlus = self.dataDirsPlus
        dataDirsMinus = self.dataDirsMinus
        skipExts = self.skipExts
        unSize = 0
        espmNots = self.espmNots
        bethFiles = bush.game.bethDataFiles
        skips, global_skip_ext = self._init_skips()
        if self.overrideSkips:
            renameStrings = False
            bethFilesSkip = set()
        else:
            renameStrings = settings['bash.installers.renameStrings'] if bush.game.esp.stringsFiles else False
            bethFilesSkip = set() if settings['bash.installers.autoRefreshBethsoft'] else bush.game.bethDataFiles
        language = oblivionIni.getSetting(u'General',u'sLanguage',u'English') if renameStrings else u''
        languageLower = language.lower()
        hasExtraData = self.hasExtraData
        if type_ == 2:
            allSubs = set(self.subNames[1:])
            activeSubs = set(x for x,y in zip(self.subNames[1:],self.subActives[1:]) if y)
        data_sizeCrc = {}
        remaps = self.remaps
        skipDirFiles = self.skipDirFiles
        skipDirFilesAdd = skipDirFiles.add
        skipDirFilesDiscard = skipDirFiles.discard
        skipExtFilesAdd = self.skipExtFiles.add
        commonlyEditedExts = Installer.commonlyEditedExts
        espmsAdd = self.espms.add
        espmMap = self.espmMap = collections.defaultdict(list)
        reModExtMatch = reModExt.match
        reReadMeMatch = Installer.reReadMe.match
        #--Scan over fileSizeCrcs
        rootIdex = self.fileRootIdex
        for full,size,crc in self.fileSizeCrcs:
            file = full[rootIdex:]
            fileLower = file.lower()
            if fileLower.startswith( # skip top level '--', 'fomod' etc
                    Installer._silentSkipsStart) or fileLower.endswith(
                    Installer._silentSkipsEnd): continue
            sub = u''
            if type_ == 2: #--Complex archive
                sub = file.split(u'\\',1)
                if len(sub) == 1:
                    sub = u''
                else: # redefine file, excluding the subpackage directory
                    sub,file = sub
                    fileLower = file.lower()
                    if fileLower.startswith(Installer._silentSkipsStart):
                        continue # skip subpackage level '--', 'fomod' etc
                if sub not in activeSubs:
                    if sub not in allSubs:
                        skipDirFilesAdd(file)
                    # Run a modified version of the normal checks, just
                    # looking for esp's for the wizard espmMap, wizard.txt
                    # and readme's
                    rootLower,fileExt = splitExt(fileLower)
                    rootLower = rootLower.split(u'\\',1)
                    if len(rootLower) == 1: rootLower = u''
                    else: rootLower = rootLower[0]
                    skip = True
                    subList = espmMap[sub]
                    subListAppend = subList.append
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
                        if file in self.remaps:
                            file = self.remaps[file]
                            # fileLower = file.lower() # not needed will skip
                        if file not in subList: subListAppend(file)
                    if skip:
                        continue
            subList = espmMap[sub]
            subListAppend = subList.append
            rootLower,fileExt = splitExt(fileLower)
            rootLower = rootLower.split(u'\\',1)
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
            if fileExt in Installer._extensions_to_process: # process attributes
                if Installer._attributes_process[fileExt](self, fileLower,
                                                          full, fileExt):
                    continue
            if fileExt in global_skip_ext: continue # docs treated above
            elif fileExt in Installer._executables_process: # and handle execs
                if Installer._executables_process[fileExt](
                        checkOBSE, fileLower, full, archiveRoot, size, crc):
                    continue
            #--Noisy skips
            if fileLower in bethFilesSkip:
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

    @staticmethod
    def _find_root_index(fileSizeCrcs):
        #--Sort file names
        def fscSortKey(fsc):
            dirFile = fsc[0].lower().rsplit(u'\\',1)
            if len(dirFile) == 1: dirFile.insert(0,u'')
            return dirFile
        sortKeys = dict((x,fscSortKey(x)) for x in fileSizeCrcs)
        fileSizeCrcs.sort(key=lambda x: sortKeys[x])
        #--Find correct starting point to treat as BAIN package
        dataDirs = Installer.dataDirsPlus
        layout = {}
        layoutSetdefault = layout.setdefault
        for file,size,crc in fileSizeCrcs:
            if file.startswith(u'--'): continue ##: also ignore other silent skips !!
            fileLower = file.lower()
            frags = fileLower.split(u'\\')
            if len(frags) == 1:
                # Files in the root of the package, start there
                rootIdex = 0
                break
            else:
                dirName = frags[0]
                if dirName not in layout and layout:
                    # A second directory in the archive root, start in the root
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
        return rootIdex

    def refreshBasic(self, archive, progress, recalculate_project_crc=True):
        """Extract file/size/crc and BAIN structure info from installer."""
        self._refreshSource(archive, progress, recalculate_project_crc)
        self.fileRootIdex = rootIdex = self._find_root_index(self.fileSizeCrcs)
        # fileRootIdex now points to the start in the file strings to ignore
        #--Type, subNames
        type_ = 0
        subNameSet = set()
        subNameSetAdd = subNameSet.add
        subNameSetAdd(u'')
        reDataFileSearch = self.reDataFile.search
        dataDirs = self.dataDirsPlus
        for file, size, crc in self.fileSizeCrcs:
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
    def match_valid_name(self, newName):
        return self.reValidNamePattern.match(newName)

    @staticmethod
    def _rename(archive, data, newName):
        """Rename package or project."""
        installer = data[archive]
        if newName != archive:
            newPath = dirs['installers'].join(newName)
            if not newPath.exists():
                oldPath = dirs['installers'].join(archive)
                try:
                    oldPath.moveTo(newPath)
                except (OSError, IOError):
                    deprint('Renaming %s to %s failed' % (oldPath, newPath),
                            traceback=True)
                    ##: WindowsError: [Error 32] The process cannot access...
                    if newPath.exists() and oldPath.exists():
                        newPath.remove()
                    raise
                installer.archive = newName.s
                #--Add the new archive to Bash and remove old one
                data[newName] = installer
                del data[archive]
                #--Update the iniInfos & modInfos for 'installer'
                mfiles = [x for x in modInfos.table.getColumn('installer') if
                          modInfos.table[x]['installer'] == oldPath.stail]
                ifiles = [x for x in iniInfos.table.getColumn('installer') if
                          iniInfos.table[x]['installer'] == oldPath.stail]
                for i in mfiles:
                    modInfos.table[i]['installer'] = newPath.stail
                for i in ifiles:
                    iniInfos.table[i]['installer'] = newPath.stail
                return True, bool(mfiles), bool(ifiles)
        return False, False, False

    #--ABSTRACT ---------------------------------------------------------------
    def _refreshSource(self, archive, progress, recalculate_project_crc):
        """Refresh fileSizeCrcs, size, and modified from source
        archive/directory. fileSizeCrcs is a list of tuples, one for _each_
        file in the archive or project directory. _refreshSource is called
        in refreshBasic only - so may be skipped if this is a project and
        skipRefresh is on. In projects the src_sizeCrcDate cache is used to
        avoid recalculating crc's.
        :param recalculate_project_crc: only used in InstallerProject override
        """
        raise AbstractError

    def install(self,archive,destFiles,data_sizeCrcDate,progress=None):
        """Install specified files to Oblivion\Data directory."""
        raise AbstractError

    def listSource(self,archive):
        """Lists the folder structure of the installer."""
        raise AbstractError

    def renameInstaller(self, archive, root, numStr, data):
        """Rename installer and return a three tuple specifying if a refresh in
        mods and ini lists is needed.
        :rtype: tuple
        """
        raise AbstractError

#------------------------------------------------------------------------------
class InstallerMarker(Installer):
    """Represents a marker installer entry.
    Currently only used for the '==Last==' marker"""
    __slots__ = tuple() #--No new slots

    def __init__(self,archive):
        Installer.__init__(self,archive)
        self.modified = time.time()

    @property
    def num_of_files(self): return -1

    @staticmethod
    def number_string(number, marker_string=u''): return marker_string

    def size_string(self, marker_string=u''): return marker_string

    def _refreshSource(self, archive, progress, recalculate_project_crc):
        """Marker: size is -1, fileSizeCrcs empty, modified = creation time."""
        pass

    def install(self,name,destFiles,data_sizeCrcDate,progress=None):
        """Install specified files to Oblivion\Data directory."""
        pass

    def renameInstaller(self, archive, root, numStr, data):
        installer = data[archive]
        newName = GPath(
            u'==' + root.strip(u'=') + numStr + archive.ext + u'==')
        if newName == archive:
            return False
        #--Add the marker to Bash and remove old one
        data[newName] = installer
        del data[archive]
        return True, False, False

    def refreshBasic(self, archive, progress, recalculate_project_crc=True):
        return {}

#------------------------------------------------------------------------------
class InstallerArchiveError(bolt.BoltError): pass

#------------------------------------------------------------------------------
class InstallerArchive(Installer):
    """Represents an archive installer entry."""
    __slots__ = tuple() #--No new slots
    reValidNamePattern = re.compile(
        ur'^([^/\\:*?"<>|]+?)(\d*)((\.(7z|rar|zip|001))+)$', re.I | re.U)

    #--File Operations --------------------------------------------------------
    def _refreshSource(self, archive, progress, recalculate_project_crc):
        """Refresh fileSizeCrcs, size, modified, crc, isSolid from archive."""
        #--Basic file info
        self.modified = archive.mtime
        self.size = archive.size
        #--Get fileSizeCrcs
        fileSizeCrcs = self.fileSizeCrcs = []
        reList = Installer.reList
        file = size = crc = isdir = 0
        self.isSolid = False
        with archive.unicodeSafe() as tempArch:
            ins = bolt.listArchiveContents(tempArch.s)
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
            command = u'"%s" x %s' % (bolt.exe7z, args)
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
        timestamps = modInfos.mod_timestamp()
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
                env.shellMove(stageDataDir, destDir, progress.getParent())
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
                ins = bolt.listArchiveContents(tempArch.s)
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
            for node, isdir in text:
                log(u'  ' * node.count(os.sep) + os.path.split(node)[1] + (
                    os.sep if isdir else u''))
            log(u'[/xml][/spoiler]')
            return bolt.winNewLines(log.out.getvalue())

    def renameInstaller(self, archive, root, numStr, data):
        newName = GPath(root + numStr + archive.ext)
        return self._rename(archive, data, newName)

#------------------------------------------------------------------------------
class InstallerProject(Installer):
    """Represents a directory/build installer entry."""
    __slots__ = tuple() #--No new slots

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
        for asDir, __sDirs, sFiles in os.walk(asRoot):
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

    @staticmethod
    def removeEmpties(name):
        """Removes empty directories from project directory."""
        empties = set()
        projectDir = dirs['installers'].join(name)
        for asDir,sDirs,sFiles in os.walk(projectDir.s):
            if not (sDirs or sFiles): empties.add(GPath(asDir))
        for empty in empties: empty.removedirs()
        projectDir.makedirs() #--In case it just got wiped out.

    def _refreshSource(self, archive, progress, recalculate_project_crc):
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
        timestamps = modInfos.mod_timestamp()
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
                env.shellMove(stageDataDir, destDir, progress.getParent())
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
            command = u'"%s" a "%s" -t"%s" %s -y -r -o"%s" -i!"%s\\*" -x@%s -scsUTF-8 -sccUTF-8' % (
                bolt.exe7z, outFile.temp.s, archiveType, solid, outDir.s, projectDir.s, self.tempList.s)
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

    def renameInstaller(self, archive, root, numStr, data):
        newName = GPath(root + numStr)
        return self._rename(archive, data, newName)

#------------------------------------------------------------------------------
from . import converters
from .converters import InstallerConverter
# Hack below needed as older Converters.dat expect bosh.InstallerConverter
# See InstallerConverter.__reduce__()
# noinspection PyRedeclaration
class InstallerConverter(InstallerConverter): pass

class InstallersData(DataDict):
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

    def __init__(self):
        self.dir = dirs['installers']
        self.bashDir = dirs['bainData']
        #--Persistent data
        self.dictFile = bolt.PickleDict(self.bashDir.join(u'Installers.dat'))
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
        #--Load Installers.dat if not loaded - will set changed to True
        changed = not self.loaded and self.__load(progress)
        #--Last marker
        if self.lastKey not in self.data:
            self.data[self.lastKey] = InstallerMarker(self.lastKey)
        #--Refresh Other - FIXME(ut): docs
        if 'D' in what:
            changed |= self._refresh_from_data_dir(progress, fullRefresh)
        if 'I' in what: changed |= self.refreshInstallers(progress,fullRefresh)
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

    def batchRename(self, selected, maPattern, refreshNeeded):
        root, numStr = maPattern.groups()[:2]
        num = int(numStr or  0)
        digits = len(str(num + len(selected)))
        if numStr: numStr.zfill(digits)
        for archive in selected:
            refreshNeeded.append(
                self[archive].renameInstaller(archive, root, numStr, self))
            num += 1
            numStr = unicode(num).zfill(digits)

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
            for m in markers: del self[m]
            _delete(toDelete, **kwargs)
        finally:
            refresh = bool(markers)
            for item in toDelete:
                if not item.exists():
                    del self[item.tail]
                    refresh = True
            if refresh: self.delete_Refresh(toDelete) # will "set changed" too

    def delete_Refresh(self, deleted): self.irefresh(what='ION')

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

    #--Refresh Functions ------------------------------------------------------
    def refreshInstallers(self,progress=None,fullRefresh=False):
        """Refresh installer data from the installers' directory."""
        progress = progress or bolt.Progress()
        pending = set()
        projects = set()
        #--Current archives
        newData = {}
        for k, v in self.items():
            if isinstance(v, InstallerMarker): newData[k] = v
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
                elif (isdir and not installer.project_refreshed) or (
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
        for subPending, iClass in zip((pending - projects, pending & projects),
                                      (InstallerArchive, InstallerProject)):
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
                try:
                    installer.refreshBasic(apath,
                            SubProgress(progress, index, index + 1),
                            recalculate_project_crc=False)
                except InstallerArchiveError:
                    installer.type = -1
        self.data = newData
        self.crc_installer = dict((x.crc,x) for x in self.data.values() if isinstance(x, InstallerArchive))
        #--Apply embedded BCFs
        if settings['bash.installers.autoApplyEmbeddedBCFs']:
            changed |= self.applyEmbeddedBCFs(progress=progress)
        return changed

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
            bcfFile = dirs['converters'].join(u'temp-' + srcBcfFile.stail)
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
            iArchive.project_refreshed = False
            iArchive.refreshBasic(pArchive, SubProgress(progress, 0.99, 1.0))
            # If applying the BCF created a new archive with an embedded BCF,
            # ignore the embedded BCF for now, so we don't end up in an
            # infinite loop
            iArchive.hasBCF = False
            bcfFile.remove()
        self.irefresh(what='I')
        return True

    def refreshInstallersNeeded(self, installers_paths=()):
        """Returns true if refreshInstallers is necessary. (Point is to skip use
        of progress dialog when possible."""
        installers = set([])
        installersJoin = dirs['installers'].join
        dataGet = self.data.get
        installersAdd = installers.add
        for item in installers_paths:
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
        """Return True if refreshConverters is necessary. (Point is to skip
        use of progress dialog when possible)."""
        return self.converters_data.refreshConvertersNeeded()

    def refreshOrder(self):
        """Refresh installer status."""
        inOrder, pending = [], []
        # not specifying the key below results in double time
        for archive, installer in sorted(self.iteritems(), key=lambda x: x[0]):
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
        active = [x for x in self.values() if x.isActive]
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
        self.update_for_overridden_skips() # after the final update !
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
                except Exception as e:
                    if isinstance(e, WindowsError) and e.errno == 2: ##: winerror also == 2
                        continue # file does not exist
                    raise
        return new_sizeCrcDate, pending, pending_size

    @staticmethod
    def _skips_in_data_dir(sDirs):
        """Skip some top level directories based on global settings - EVEN
        on a fullRefresh."""
        if inisettings['KeepLog'] > 1:
            try: log = inisettings['LogFile'].open('a', encoding='utf-8-sig')
            except: log = None
        else: log = None
        setSkipOBSE = not settings['bash.installers.allowOBSEPlugins']
        setSkipDocs = settings['bash.installers.skipDocs']
        setSkipImages = settings['bash.installers.skipImages']
        newSDirs = (x for x in sDirs if x.lower() not in Installer.dataDirsMinus)
        if settings['bash.installers.skipDistantLOD']:
            newSDirs = (x for x in newSDirs if x.lower() != u'distantlod')
        if settings['bash.installers.skipLandscapeLODMeshes']:
            newSDirs = (x for x in newSDirs if x.lower() != u'meshes\\landscape\\lod')
        if settings['bash.installers.skipScreenshots']:
            newSDirs = (x for x in newSDirs if x.lower() != u'screenshots')
        # LOD textures
        if settings['bash.installers.skipLandscapeLODTextures'] and settings[
            'bash.installers.skipLandscapeLODNormals']:
            newSDirs = (x for x in newSDirs if
                        x.lower() != u'textures\\landscapelod\\generated')
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

    def update_data_SizeCrcDate(self, dest_paths):
        """Update data_SizeCrcDate with info on given paths.
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
        root_files.sort()
        root_dirs_files = []
        for key, val in groupby(root_files, key=lambda t: t[0]):
            root_dirs_files.append((key, [], [j for i, j in val]))
        new_sizeCrcDate, pending, pending_size = self._process_data_dir(
            root_dirs_files, bolt.Progress())
        deleted = set(dest_paths) - set(new_sizeCrcDate)
        for d in deleted: self.data_sizeCrcDate.pop(d, None)
        Installer.calc_crcs(pending, pending_size, bass.dirs['mods'].stail,
                            new_sizeCrcDate, bolt.Progress()) ##: Progress !
        for rpFile, (size, crc, date, _asFile) in new_sizeCrcDate.iteritems():
            self.data_sizeCrcDate[rpFile] = (size, crc, date)

    def update_for_overridden_skips(self, dont_skip=None):
        if dont_skip is not None:
            dont_skip.difference_update(self.data_sizeCrcDate)
            self.overridden_skips |= dont_skip
        elif self.__clean_overridden_after_load:
            self.overridden_skips.difference_update(self.data_sizeCrcDate)
            self.__clean_overridden_after_load = False
        new_skips_overrides = self.overridden_skips - set(self.data_sizeCrcDate)
        self.update_data_SizeCrcDate(new_skips_overrides)

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

    def _install(self, archives, refresh_ui, progress=None, last=False,
                 override=True):
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
                mods_changed, inis_changed = InstallersData.updateTable(
                    destFiles, archive.s)
                refresh_ui[0] |= mods_changed
                refresh_ui[1] |= inis_changed
            installer.isActive = True
            mask |= set(installer.data_sizeCrc)
        if tweaksCreated:
            self._editTweaks(tweaksCreated)
        return tweaksCreated

    def bain_install(self, archives, refresh_ui, progress=None, last=False,
                     override=True):
        try: return self._install(archives, refresh_ui, progress, last,
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

    def __filter(self, archive, installer, removes, restores): ##: comments
        files = set(installer.data_sizeCrc)
        myRestores = (removes & files) - set(restores)
        for file in myRestores:
            if installer.data_sizeCrc[file] != \
                    self.data_sizeCrcDate.get(file,(0, 0, 0))[:2]:
                restores[file] = archive
            removes.discard(file)
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
        getArchiveOrder =  lambda tup: tup[1].order
        for archive, installer in sorted(self.iteritems(), key=getArchiveOrder,
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
        getArchiveOrder = lambda x: self[x].order
        restoreArchives = sorted(set(restores.itervalues()),
                                 key=getArchiveOrder, reverse=True)
        if not restoreArchives: return
        progress.setFull(len(restoreArchives))
        for index, archive in enumerate(restoreArchives):
            progress(index, archive.s)
            installer = self[archive]
            destFiles = set(x for x, y in restores.iteritems() if y == archive)
            if destFiles:
                installer.install(archive, destFiles, self.data_sizeCrcDate,
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
        getArchiveOrder =  lambda tup: tup[1].order
        for archive, installer in sorted(self.iteritems(), key=getArchiveOrder,
                                         reverse=True):
            #--Other active package. May provide a restore file.
            #  And/or may block later uninstalls.
            if installer.isActive:
                self.__filter(archive, installer, removes, restores)
        try:
            #--Remove files, update InstallersData, update load order
            self._removeFiles(removes, refresh_ui, progress)
            #--Restore files
            self._restoreFiles(restores, progress, refresh_ui)
        finally:
            self.irefresh(what='NS')

    def clean_data_dir(self, refresh_ui):
        getArchiveOrder = lambda x: x.order
        installed = []
        for installer in sorted(self.values(), key=getArchiveOrder,
                                reverse=True):
            if installer.isActive:
                installed += installer.data_sizeCrc
        keepFiles = set(installed)
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
        for file in removes:
            # don't remove files in Wrye Bash-related directories
            if file.cs.startswith(skipPrefixes): continue
            path = dirs['mods'].join(file)
            try:
                if path.exists():
                    path.moveTo(destDir.join(file))
                    if not refresh_ui[0]: refresh_ui[0] = isMod(path)
                else: # Try if it's a ghost - belongs to modInfos...
                    path = GPath(path.s + u'.ghost')
                    if path.exists():
                        path.moveTo(destDir.join(file))
                        refresh_ui[0] = True
                    else: continue # don't pop if file was not removed
                data_sizeCrcDate.pop(file,None)
                emptyDirs.add(path.head)
            except:
                # It's not imperative that files get moved, so ignore errors
                deprint(u'Clean Data: moving %s to % s failed' % (
                            path, destDir), traceback=True)
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
                activeBSAFiles.extend([(package, x, libbsa.BSAHandle(
                    dirs['mods'].join(x.s))) for x in BSAFiles if modInfos.isActiveCached(x.root + ".esp")])
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
        getArchiveOrder = lambda tup: tup[1].order
        for package, installer in sorted(self.iteritems(),key=getArchiveOrder):
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
        """Return a sublist of installerKeys that can be installed -
        installerKeys must be in data or a KeyError is raised.
        :param installerKeys: an iterable of bolt.Path
        :return: a list of installable packages/projects bolt.Path
        """
        def installable(x): # type: 0: unset/invalid; 1: simple; 2: complex
            return self[x].type in (1, 2) and isinstance(self[x],
                (InstallerArchive, InstallerProject))
        return filter(installable, installerKeys)

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
from ..env import get_personal_path, get_local_app_data_path

def getPersonalPath(bashIni, path):
    #--Determine User folders from Personal and Local Application Data directories
    #  Attempt to pull from, in order: Command Line, Ini, win32com, Registry
    if path:
        path = GPath(path)
        sErrorInfo = _(u"Folder path specified on command line (-p)")
    elif bashIni and bashIni.has_option(u'General', u'sPersonalPath') and not bashIni.get(u'General', u'sPersonalPath') == u'.':
        path = GPath(bashIni.get('General', 'sPersonalPath').strip())
        sErrorInfo = _(u"Folder path specified in bash.ini (%s)") % u'sPersonalPath'
    else:
        path, sErrorInfo = get_personal_path()
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
    else:
        path, sErrorInfo = get_local_app_data_path()
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
        path = GPath(GPath(u'..').join(u'%s Mods' % bush.game.fsName))
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

from ..env import test_permissions # CURRENTLY DOES NOTHING !
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
    dirs['defaultPatches'] = dirs['mopy'].join(u'Bash Patches', bush.game.fsName)
    dirs['tweaks'] = dirs['mods'].join(u'INI Tweaks')
    dirs['defaultTweaks'] = dirs['mopy'].join(u'INI Tweaks', bush.game.fsName)

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
    badPermissions = []
    for dir in dirs:
        if not test_permissions(dirs[dir]):
            badPermissions.append(dirs[dir])
    if not test_permissions(oblivionMods):
        badPermissions.append(oblivionMods)
    if badPermissions:
        # Do not have all the required permissions for all directories
        # TODO: make this gracefully degrade.  IE, if only the BAIN paths are
        # bad, just disable BAIN.  If only the saves path is bad, just disable
        # saves related stuff.
        msg = balt.fill(_(u'Wrye Bash cannot access the following paths:'))
        msg += u'\n\n'+ u'\n'.join([u' * '+dir.s for dir in badPermissions]) + u'\n\n'
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

def initBosh(personal='', localAppData='', oblivionPath='', bashIni=None):
    #--Bash Ini
    if not bashIni: bashIni = bass.GetBashIni()
    initDirs(bashIni,personal,localAppData, oblivionPath)
    global load_order
    from .. import load_order ##: move it from here - also called from restore settings
    load_order = load_order
    initOptions(bashIni)
    try:
        initLogFile()
    except IOError:
        deprint('Error creating log file', traceback=True)
    Installer.init_bain_dirs()
    bolt.exe7z = dirs['compiled'].join(bolt.exe7z).s

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
    if 'bash.readme' in settings:
        settings['bash.version'] = _(settings['bash.readme'][1])
        del settings['bash.readme']

# Main ------------------------------------------------------------------------
if __name__ == '__main__':
    print _(u'Compiled')
