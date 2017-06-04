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
"""Tmp module, hence the underscore, to rip save classes out of bosh -
Oblivion only . We need this split into cosaves and proper saves module and
coded for rest of the games."""
# TODO: Oblivion only - we need to support rest of games - help needed
import struct
from operator import attrgetter

from .. import bolt, bush
from ..bolt import Flags, sio, GPath, decode, deprint, encode, \
    cstrip, SubProgress
from ..brec import ModReader, MreRecord, ModWriter, getObjectIndex, \
    getFormIndices
from ..exception import FileError, ModError, StateError
from ..parsers import LoadFactory, ModFile

#------------------------------------------------------------------------------
# Save I/O --------------------------------------------------------------------
#------------------------------------------------------------------------------

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
                (acbs.flags, acbs.baseSpell, acbs.fatigue, acbs.barterGold,
                 acbs.level, acbs.calcMin, acbs.calcMax) = unpack('=I3Hh2H',16)
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
                buff.write(
                    u'Attributes\n  strength %3d\n  intelligence %3d\n  '
                    u'willpower %3d\n  agility %3d\n  speed %3d\n  endurance '
                    u'%3d\n  personality %3d\n  luck %3d\n' % tuple(
                        self.attributes))
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
                buff.write(
                    u'Skills:\n  armorer %3d\n  athletics %3d\n  blade %3d\n '
                    u' block %3d\n  blunt %3d\n  handToHand %3d\n  '
                    u'heavyArmor %3d\n  alchemy %3d\n  alteration %3d\n  '
                    u'conjuration %3d\n  destruction %3d\n  illusion %3d\n  '
                    u'mysticism %3d\n  restoration %3d\n  acrobatics %3d\n  '
                    u'lightArmor %3d\n  marksman %3d\n  mercantile %3d\n  '
                    u'security %3d\n  sneak %3d\n  speechcraft  %3d\n' % tuple(
                        self.skills))
            return buff.getvalue()

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

# Save File -------------------------------------------------------------------
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
        if obseFile._plugins is None: return
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
class SaveSpells:
    """Player spells of a savegame."""

    def __init__(self,saveInfo):
        self.saveInfo = saveInfo
        self.saveFile = None
        self.allSpells = {} #--spells[(modName,objectIndex)] = (name,type)

    def load(self, modInfos, progress=None):
        """Load savegame and extract created spells from it and its masters."""
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
