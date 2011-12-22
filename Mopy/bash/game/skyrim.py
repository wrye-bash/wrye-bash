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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2011 Wrye Bash Team
#
# =============================================================================

"""This modules defines static data for use by bush, when
   TES V: Skyrim is set at the active game."""

import struct
from .. import brec
from .. import bolt
from ..brec import *

#--Name of the game
name = u'Skyrim'
altName = u'Wrye Smash'

#--exe to look for to see if this is the right game
exe = u'TESV.exe'

#--Registry keys to read to find the install location
regInstallKeys = [
    (u'Bethesda Softworks\\Skyrim',u'Installed Path'),
    ]

#--patch information
patchURL = u'' # Update via steam
patchTip = u'Update via Steam'

#--Creation Kit Set information
class cs:
    shortName = u'CK'                # Abbreviated name
    longName = u'Creation Kit'       # Full name
    exe = u'CreationKit.exe'         # Executable to run
    seArgs = u'-editor'              # Argument to pass to the SE to load the CS
    imageName = u'tescs%s.png'       # Image name template for the status bar

#--Script Extender information
class se:
    shortName = u'SKSE'                      # Abbreviated name
    longName = u'Skyrim Script Extender'     # Full name
    exe = u'skse_loader.exe'                 # Exe to run
    steamExe = u'skse_loader.exe'            # Exe to run if a steam install
    url = u'http://skse.silverlock.org/'     # URL to download from
    urlTip = u'http://skse.silverlock.org/'  # Tooltip for mouse over the URL

#--Graphics Extender information
class ge:
    shortName = u''
    longName = u''
    exe = u'**DNE**'
    url = u''
    urlTip = u''

#--4gb Launcher
class laa:
    # Skyrim has a 4gb Launcher, but as of patch 1.3.10, it is
    # no longer required (Bethsoft updated TESV.exe to already
    # be LAA)
    name = u''
    exe = u'**DNE**'
    launchesSE = False

#--Save Game format stuff
class ess:
    # Save file capabilities
    canReadBasic = True         # All the basic stuff needed for the Saves Tab
    canEditMasters = True       # Adjusting save file masters
    canEditMore = False         # No advanced editing

    @staticmethod
    def load(ins,header):
        """Extract info from save file."""
        #--Header
        if ins.read(13) != 'TESV_SAVEGAME':
            raise Exception(u'Save file is not a Skyrim save game.')
        headerSize, = struct.unpack('I',ins.read(4))
        #--Name, location
        version,saveNumber,size = struct.unpack('2IH',ins.read(10))
        header.pcName = ins.read(size)
        header.pcLevel, = struct.unpack('I',ins.read(4))
        size, = struct.unpack('H',ins.read(2))
        header.pcLocation = ins.read(size)
        size, = struct.unpack('H',ins.read(2))
        header.gameDate = ins.read(size)
        hours,minutes,seconds = [int(x) for x in header.gameDate.split('.')]
        playSeconds = hours*60*60 + minutes*60 + seconds
        header.gameDays = float(playSeconds)/(24*60*60)
        header.gameTicks = playSeconds * 1000
        size, = struct.unpack('H',ins.read(2))
        ins.seek(ins.tell()+size+2+4+4+8) # raceEdid, unk0, unk1, unk2, ftime
        ssWidth, = struct.unpack('I',ins.read(4))
        ssHeight, = struct.unpack('I',ins.read(4))
        if ins.tell() != headerSize + 17:
            raise Exception(u'Save game header size (%s) not as expected (%s).' % (ins.tell()-17,headerSize))
        #--Image Data
        ssData = ins.read(3*ssWidth*ssHeight)
        header.image = (ssWidth,ssHeight,ssData)
        #--unknown
        unk3 = ins.read(1)
        #--Masters
        mastersSize, = struct.unpack('I',ins.read(4))
        mastersStart = ins.tell()
        del header.masters[:]
        numMasters, = struct.unpack('B',ins.read(1))
        for count in xrange(numMasters):
            size, = struct.unpack('H',ins.read(2))
            header.masters.append(ins.read(size))
        if ins.tell() != mastersStart + mastersSize:
            raise Exception(u'Save game masters size (%i) not as expected (%i).' % (ins.tell()-mastersStart,mastersSize))

    @staticmethod
    def writeMasters(ins,out,header):
        """Rewrites masters of existing save file."""
        def unpack(format,size): return struct.unpack(format,ins.read(size))
        def pack(format,*args): out.write(struct.pack(format,*args))
        #--Magic (TESV_SAVEGAME)
        out.write(ins.read(13))
        #--Header
        size, = unpack('I',4)
        pack('I',size)
        out.write(ins.read(size-8))
        ssWidth,ssHeight = unpack('2I',8)
        pack('2I',ssWidth,ssHeight)
        #--Screenshot
        out.write(ins.read(3*ssWidth*ssHeight))
        #--formVersion
        out.write(ins.read(1))
        #--plugin info
        oldSize, = unpack('I',4)
        newSize = 1 + sum(len(x)+2 for x in header.masters)
        pack('I',newSize)
        #  Skip old masters
        oldMasters = []
        numMasters, = unpack('B',1)
        pack('B',len(header.masters))
        for x in xrange(numMasters):
            size, = unpack('H',2)
            oldMasters.append(ins.read(size))
        #  Write new masters
        for master in header.masters:
            pack('H',len(master))
            out.write(master.s)
        #--Offsets
        offset = out.tell() - ins.tell()
        #--File Location Table
        for i in xrange(6):
            # formIdArrayCount offset, unkownTable3Offset,
            # globalDataTable1Offset, globalDataTable2Offset,
            # changeFormsOffset, globalDataTable3Offset
            oldOffset, = unpack('I',4)
            pack('I',oldOffset+offset)
        #--Copy the rest
        while True:
            buffer = ins.read(0x5000000)
            if not buffer: break
            out.write(buffer)
        return oldMasters

#--INI files that should show up in the INI Edits tab
iniFiles = [
    u'Skyrim.ini',
    u'SkyrimPrefs.ini',
    ]

#--INI setting to setup Save Profiles
saveProfilesKey = (u'General',u'SLocalSavePath')

#--The main plugin file Wrye Bash should look for
masterFiles = [
    u'Skyrim.esm',
    ]

#--Game ESM/ESP/BSA files
bethDataFiles = set((
    #--Vanilla
    u'skyrim.esm',
    u'update.esm',
    u'skyrim - animations.bsa',
    u'skyrim - interface.bsa',
    u'skyrim - meshes.bsa',
    u'skyrim - misc.bsa',
    u'skyrim - shaders.bsa',
    u'skyrim - sounds.bsa',
    u'skyrim - textures.bsa',
    u'skyrim - voices.bsa',
    u'skyrim - voicesextra.bsa',
    ))

#--Every file in the Data directory from Bethsoft
allBethFiles = set((
    #--Vanilla
    u'skyrim.esm',
    u'update.esm',
    u'skyrim - animations.bsa',
    u'skyrim - interface.bsa',
    u'skyrim - meshes.bsa',
    u'skyrim - misc.bsa',
    u'skyrim - shaders.bsa',
    u'skyrim - sounds.bsa',
    u'skyrim - textures.bsa',
    u'skyrim - voices.bsa',
    u'skyrim - voicesextra.bsa',
    u'interface\\translate_english.txt', #--probably need one for each language
    u'strings\\skyrim_english.dlstrings', #--same here
    u'strings\\skyrim_english.ilstrings',
    u'strings\\skryim_english.strings',
    u'strings\\update_english.dlstrings',
    u'strings\\update_english.ilstrings',
    u'strings\\update_english.strings',
    u'video\\bgs_logo.bik',
    ))

#--BAIN: Directories that are OK to install to
dataDirs = set((
    u'bash patches',
    u'interface',
    u'meshes',
    u'strings',
    u'textures',
    u'video',
    u'lodsettings',
    u'grass',
    u'scripts',
    u'shadersfx',
    u'music',
    u'sound',
    ))
dataDirsPlus = set((
    u'ini tweaks',
    u'skse',
    u'ini',
    ))

#--List of GMST's in the main plugin (Oblivion.esm) that have 0x00000000
#  as the form id.  Any GMST as such needs it Editor Id listed here.
gmstEids = [
    # None
    ]

#--Patchers available when building a Bashed Patch
patchers = (
    u'AliasesPatcher', u'PatchMerger',
    )

#--CBash patchers available when building a Bashed Patch
CBash_patchers = tuple()

#--Plugin format stuff
class esp:
    #--Wrye Bash capabilities
    canBash = True         # No Bashed Patch creation
    canCBash = False        # CBash cannot handle this game's records
    canEditHeader = True    # Can edit anything in the TES4 record

    #--Valid ESM/ESP header versions
    validHeaderVersions = (0.94,)

    #--Top types in Oblivion order.
    topTypes = ['GMST', 'KYWD', 'LCRT', 'AACT', 'TXST', 'GLOB', 'CLAS', 'FACT', 'HDPT',
        'HAIR', 'EYES', 'RACE', 'SOUN', 'ASPC', 'MGEF', 'SCPT', 'LTEX', 'ENCH', 'SPEL',
        'SCRL', 'ACTI', 'TACT', 'ARMO', 'BOOK', 'CONT', 'DOOR', 'INGR', 'LIGH', 'MISC',
        'APPA', 'STAT', 'SCOL', 'MSTT', 'PWAT', 'GRAS', 'TREE', 'CLDC', 'FLOR', 'FURN',
        'WEAP', 'AMMO', 'NPC_', 'LVLN', 'KEYM', 'ALCH', 'IDLM', 'COBJ', 'PROJ', 'HAZD',
        'SLGM', 'LVLI', 'WTHR', 'CLMT', 'SPGD', 'RFCT', 'REGN', 'NAVI', 'CELL', 'WRLD',
        'DIAL', 'QUST', 'IDLE', 'PACK', 'CSTY', 'LSCR', 'LVSP', 'ANIO', 'WATR', 'EFSH',
        'EXPL', 'DEBR', 'IMGS', 'IMAD', 'FLST', 'PERK', 'BPTD', 'ADDN', 'AVIF', 'CAMS',
        'CPTH', 'VTYP', 'MATT', 'IPCT', 'IPDS', 'ARMA', 'ECZN', 'LCTN', 'MESG', 'RGDL',
        'DOBJ', 'LGTM', 'MUSC', 'FSTP', 'FSTS', 'SMBN', 'SMQN', 'SMEN', 'DLBR', 'MUST',
        'DLVW', 'WOOP', 'SHOU', 'EQUP', 'RELA', 'SCEN', 'ASTP', 'OTFT', 'ARTO', 'MATO',
        'MOVT', 'SNDR', 'DUAL', 'SNCT', 'SOPM', 'COLL', 'CLFM', 'REVB',]

    #--Dict mapping 'ignored' top types to un-ignored top types.
    topIgTypes = dict([(struct.pack('I',(struct.unpack('I',type)[0]) | 0x1000),type) for type in topTypes])

    #-> this needs updating for Skyrim
    recordTypes = set(topTypes + 'GRUP,TES4,ROAD,REFR,ACHR,ACRE,PGRD,LAND,INFO'.split(','))

#--Mod I/O
class RecordHeader(brec.BaseRecordHeader):
    size = 24

    def __init__(self,recType='TES4',size=0,arg1=0,arg2=0,arg3=0,extra=0):
        self.recType = recType
        self.size = size
        if recType == 'GRUP':
            self.label = arg1
            self.groupType = arg2
            self.stamp = arg3
        else:
            self.flags1 = arg1
            self.fid = arg2
            self.flags2 = arg3
        self.extra = extra

    @staticmethod
    def unpack(ins):
        """Returns a RecordHeader object by reading the niput stream."""
        type,size,uint0,uint1,uint2,uint3 = ins.unpack('=4s5I',24,'REC_HEADER')
        #--Bad type?
        if type not in esp.recordTypes:
            raise brec.ModError(ins.inName,u'Bad header type: '+type)
        #--Record
        if type != 'GRUP':
            pass
        #--Top Group
        elif uint1 == 0: #groupType == 0 (Top Type)
            str0 = struct.pack('I',uint0)
            if str0 in esp.topTypes:
                uint0 = str0
            elif str0 in esp.topIgTypes:
                uint0 = esp.topIgTypes[str0]
            else:
                raise brec.ModError(ins.inName,u'Bad Top GRUP type: '+str0)
        #--Other groups
        return RecordHeader(type,size,uint0,uint1,uint2,uint3)

    def pack(self):
        """Return the record header packed into a bitstream to be written to file."""
        if self.recType == 'GRUP':
            if isinstance(self.label,str):
                return struct.pack('=4sI4sIII',self.recType,self.size,
                                   self.label,self.groupType,self.stamp,
                                   self.extra)
            elif isinstance(self.label,tuple):
                return struct.pack('=4sIhhIII',self.recType,self.size,
                                   self.label[0],self.label[1],self.groupType,
                                   self.stamp,self.extra)
            else:
                return struct.pack('=4s5I',self.recType,self.size,self.label,
                                   self.groupType,self.stamp,self.extra)
        else:
            return struct.pack('=4s5I',self.recType,self.size,self.flags1,
                               self.fid,self.flags2,self.extra)
#--Set ModReader to use the correct record header
brec.ModReader.recHeader = RecordHeader

# Record Elements --------------------------------------------------------------
#-------------------------------------------------------------------------------
class MelVmad(MelBase):
    """Virtual Machine data (VMAD)"""
    class Vmad(object):
        __slots__ = ('version','unk','scripts',)
        def __init__(self):
            self.version = 5
            self.unk = 2
            self.scripts = {}
    class Script(object):
        __slots__ = ('unk','properties')
        def __init__(self):
            self.unk = 0
            self.properties = {}
    class Property(object):
        __slots__ = ('type','unk','value')
        def __init__(self):
            self.type = 1
            self.unk = 1
            self.value = 0

    def __init__(self,type='VMAD',attr='vmdata'):
        MelBase.__init__(self,type,attr)

    def hasFids(self,formElements):
        """Include self if has fids."""
        formElements.add(self)

    def setDefault(self,record):
        record.__setattr__(self.attr,MelVmad.Vmad())

    def getDefault(self):
        target = MelObject()
        return self.setDefault(target)

    def loadData(self,record,ins,type,size,readId):
        vmad = MelVmad.Vmad()
        # Header
        vmad.version,vmad.unk,scriptCount = ins.unpack('=3H',6,readId)
        # Scripts
        for x in xrange(scriptCount):
            script = MelVmad.Script()
            scriptName = ins.readString16(size,readId)
            script.unk,propertyCount = ins.unpack('=BH',3,readId)
            # Properties
            props = script.properties
            for y in xrange(propertyCount):
                prop = MelVmad.Property()
                propName = ins.readString16(size,readId)
                type,prop.unk = ins.unpack('=2B',2,readId)
                prop.type = type
                if type == 1:
                    # Object reference? (uint64?)
                    value = ins.unpack('=HHI',8,readId) # unk,unk,fid
                elif type == 2:
                    # String
                    value = ins.readString16(size,readId)
                elif type == 3:
                    # int32
                    value = ins.unpack('i',4,readId)
                elif type == 4:
                    # float
                    value = ins.unpack('f',4,readId)
                elif type == 5:
                    # bool (int8)
                    value = ins.unpack('b',1,readId)
                elif type == 11:
                    # array of object refs? (uint64s?)
                    count, = ins.unpack('I',4,readId)
                    value = list(ins.unpack(`count`+'Q',count*8,readId))
                elif type == 12:
                    # array of strings
                    count, = ins.unpack('I',4,readId)
                    value = [ins.readString16(size,readId) for z in xrange(count)]
                elif type == 13:
                    # array of int32's
                    count, = ins.unpack('I',4,readId)
                    value = ins.unpack(`count`+'i',count*4,readId)
                elif type == 14:
                    # array of float's
                    count, = ins.unpack('I',4,readId)
                    value = ins.unpack(`count`+'f',count*4,readId)
                elif type == 15:
                    # array of bools's (int8's)
                    count, = ins.unpack('I',4,readId)
                    value = ins.unpack(`count`+'b',count*1,readId)
                else:
                    raise Exception(u'Unrecognized VM Data property type: %i' % type)
                prop.value = value
                props[propName] = prop
            vmad.scripts[scriptName] = script
        record.__setattr__(self.attr,vmad)

    def dumpData(self,record,out):
        """Dumps data from record to outstream"""
        outPack = out.pack
        outWrite = out.write
        def packString(string):
            string = _encode(string)
            outPack('H',len(string))
            outWrite(string)
        vmad = record.__getattribute__(self.attr)
        # Header
        outPack('3h',vmad.version,vmad.unk,len(vmad.scripts))
        # Scripts
        for scriptName,script in vmad.scripts.iteritems():
            packString(scriptName)
            outPack('=BH',script.unk,len(script.properties))
            # Properties
            for propName,prop in script.properties.iteritems():
                packString(propName)
                type = prop.type
                outPack('2B',type,prop.unk)
                if type == 1:
                    # Object reference
                    outPack('=HHI',*prop.value)
                elif type == 2:
                    # String
                    packString(prop.value)
                elif type == 3:
                    # int32
                    outPack('i',prop.value)
                elif type == 4:
                    # float
                    outPack('f',prop.value)
                elif type == 5:
                    # bool (int8)
                    outPack('b',prop.value)
                elif type == 11:
                    # array of object references
                    num = len(prop.value)
                    outPack('=I'+`num`+'Q',num,*prop.value)
                elif type == 12:
                    # array of strings
                    num = len(prop.value)
                    outPack('I',num)
                    for string in prop.value:
                        packString(string)
                elif type == 13:
                    # array of int32's
                    num = len(prop.value)
                    outPack('=I'+`num`+'i',num,*prop.value)
                elif type == 14:
                    # array of float's
                    num = len(prop.value)
                    outPack('=I'+`num`+'f',num,*prop.value)
                elif type == 15:
                    # array of bools (int8)
                    num = len(prop.value)
                    outPack('=I'+`num`+'b',num,*prop.value)

    def mapFids(self,record,function,save=False):
        """Applies function to fids.  If save s true, then fid is set
           to result of function."""
        attr = self.attr
        vmad = record.__getattribute__(attr)
        for scriptName,script in vmad.scripts.iteritems():
            for propName,prop in script.properties.iteritems():
                if prop.type == 0:
                    value = prop.value
                    value = (value[0],value[1],function(value[2]))
                    if save:
                        prop.value = value

#-------------------------------------------------------------------------------
class MelBounds(MelStruct):
    def __init__(self):
        MelStruct.__init__(self,'OBND','=6h',
            'x1','y1','z1',
            'x2','y2','z2')

#-------------------------------------------------------------------------------
class MelString16(MelString):
    """Represents a mod record string element."""
    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        strLen = ins.unpack('H',2,readId)
        value = ins.readString(strLen,readId)
        record.__setattr__(self.attr,value)
        if self._debug: print u' ',record.__getattribute__(self.attr)

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        value = record.__getattribute__(self.attr)
        if value != None:
            if self.maxSize:
                value = bolt.winNewLines(value.rstrip())
                size = min(self.maxSize,len(value))
                test,encoding = _encode(value,returnEncoding=True)
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
                value = _encode(value)
            value = struct.pack('H',len(value))+value
            out.packSub0(self.subType,value)

#-------------------------------------------------------------------------------
class MelString32(MelString):
    """Represents a mod record string element."""
    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        strLen = ins.unpack('I',4,readId)
        value = ins.readString(strLen,readId)
        record.__setattr__(self.attr,value)
        if self._debug: print u' ',record.__getattribute__(self.attr)

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        value = record.__getattribute__(self.attr)
        if value != None:
            if self.maxSize:
                value = bolt.winNewLines(value.rstrip())
                size = min(self.maxSize,len(value))
                test,encoding = _encode(value,returnEncoding=True)
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
                value = _encode(value)
            value = struct.pack('I',len(value))+value
            out.packSub0(self.subType,value)

#-------------------------------------------------------------------------------
class MelMODS(MelBase):
    """MODS/MO2S/etc/DMDS subrecord"""
    def hasFids(self,formElements):
        """Include self if has fids."""
        formElements.add(self)

    def setDefault(self,record):
        """Sets default value for record instance."""
        record.__setattr__(self.attr,[])

    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        insUnpack = ins.unpack
        insRead32 = ins.readString32
        count, = insUnpack('I',4,readId)
        data = []
        dataAppend = data.append
        for x in xrange(count):
            string = ins.readString32(size,readId)
            fid = ins.unpackRef(readId)
            unk = ins.unpack('I',4,readId)
            dataAppend((string,fid,unk))
        record.__setattr__(self.attr,data)

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        structPack = struct.pack
        data = record.__getattribute__(self.attr)
        outData = structPack('I',len(data))
        for (string,fid,unk) in data:
            outData += structPack('I',len(string))
            outData += string
            outData += structPack('=2I',fid,unk)
        out.packSub(self.subType,outData)

    def mapFids(self,record,function,save=False):
        """Applies function to fids.  If save is true, then fid is set
           to result of function."""
        attr = self.attr
        data = [(string,function(fid),unk) for (string,fid,unk) in record.__getattribute__(attr)]
        if save: record.__setattr__(attr,data)

#-------------------------------------------------------------------------------
class MelBODT(MelStruct):
    """Body Type data"""
    btFlags = bolt.Flags(0L,bolt.Flags.getNames(
        (0, 'skin'),
        (1, 'head'),
        (2, 'chest'),
        (3, 'hands'),
        (4, 'beard'),
        (5, 'amulet'),
        (6, 'ring'),
        (7, 'feet'),
        #8 = unk
        (9, 'shield'),
        (10,'animal_skin'),
        (11,'underskin'),
        (12,'crown'),
        (13,'face'),
        (14,'dragon_head'),
        (15,'dragon_lwing'),
        (16,'dragon_rwing'),
        (17,'dragon_body'),
        ))
    otherFlags = bolt.Flags(0L,bolt.Flags.getNames(
        (4,'notPlayable'),
        ))
    armorTypes = {
        0:'Light Armor',
        1:'Heavy Armor',
        2:'Clothing',
        }
    def __init__(self,type='BODT'):
        MelStruct.__init__(self,type,'=3I',
                           (MelBODT.btFlags,'bodyFlags',0L),
                           (MelBODT.otherFlags,'otherFlags',0L),
                           ('armorType',0)
                           )

#-------------------------------------------------------------------------------
class MelModel(MelGroup):
    """Represents a model record."""
    typeSets = {
        'MODL': ('MODL','MODT','MODS'),
        'MOD2': ('MOD2','MO2T','MO2S'),
        'MOD3': ('MOD3','MO3T','MO3S'),
        'MOD4': ('MOD4','MO4T','MO4S'),
        'MOD5': ('MOD5','MO5T','MO5S'),
        'DMDL': ('DMDL','DMDT','DMDS'),
        }
    def __init__(self,attr='model',type='MODL'):
        """Initialize."""
        types = self.__class__.typeSets[type]
        MelGroup.__init__(self,attr,
            MelString(types[0],'modPath'),
            MelBase(types[1],'modt_p'),
            MelMODS(types[2],'mod_s'),
            )

    def debug(self,on=True):
        """Sets debug flag on self."""
        for element in self.elements[:2]: element.debug(on)
        return self

#-------------------------------------------------------------------------------
class MelConditions(MelStructs):
    """Represents a set of quest/dialog/etc conditions. Difficulty is that FID
    state of parameters depends on function index."""
    def __init__(self):
        """Initialize."""
        MelStructs.__init__(self,'CTDA','=B3sfH2sii4sII','conditions',
            'operFlag',('unused1',null3),'compValue',
            'ifunc',('unused2',null2),'param1','param2',
            ('unused3',null4),'reference','unknown')

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
        target = MelObject()
        record.conditions.append(target)
        target.__slots__ = self.attrs
        unpacked1 = ins.unpack('=B3sfH2s',12,readId)
        (target.operFlag,target.unused1,target.compValue,ifunc,target.unused2) = unpacked1
        #--Get parameters
        if ifunc not in allConditions:
            raise bolt.BoltError(u'Unknown condition function: %d' % ifunc)
        form1 = 'I' if ifunc in fid1Conditions else 'i'
        form2 = 'I' if ifunc in fid2Conditions else 'i'
        form12 = form1+form2
        unpacked2 = ins.unpack(form12,8,readId)
        (target.param1,target.param2) = unpacked2
        target.unused3 = ins.read(4)
        target.unused3,target.reference = ins.unpack('=2I',8,readId)
        (target.ifunc,target.form12) = (ifunc,form12)
        if self._debug:
            unpacked = unpacked1+unpacked2
            print u' ',zip(self.attrs,unpacked)
            if len(unpacked) != len(self.attrs):
                print u' ',unpacked

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        for target in record.conditions:
            ##format = 'B3sfI'+target.form12+'4s'
            out.packSub('CTDA','=B3sfH2s'+target.form12+'4sII',
                target.operFlag, target.unused1, target.compValue,
                target.ifunc, target.unused2, target.param1, target.param2,
                target.unused3,target.reference)

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

# Skyrim Records ---------------------------------------------------------------
#-------------------------------------------------------------------------------
class MreHeader(MreHeaderBase):
    """TES4 Record.  File header."""
    classType = 'TES4'

    #--Data elements
    melSet = MelSet(
        MelStruct('HEDR','f2I',('version',0.94),'numRecords',('nextObject',0xCE6)),
        MelString('CNAM','author',u'',512),
        MelString('SNAM','description',u'',512),
        MreHeaderBase.MelMasterName('MAST','masters'),
        MelNull('DATA'),
        MelBase('INTV','ingv_p'),
        MelBase('ONAM','onam_p'),
        )
    __slots__ = MreHeaderBase.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAact(MelRecord):
    """Action record."""
    classType = 'AACT'
    melSet = MelSet(
        MelString('EDID','eid'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreActi(MelRecord):
    """Activator."""
    classType = 'ACTI'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel(),
        MelBase('DEST','dest_p'),
        MelBase('DSTD','dstd_p'),
        MelModel('depletedModel','DMDL'),
        MelBase('PNAM','pnam_p'),
        MelFid('VNAM','pickupSound'),
        MelFid('SNAM','dropSound'),
        MelFid('WNAM','water'),
        MelGroup('keywords',
                 MelStruct('KSIZ','I','num'),
                 MelFidList('KWDA','keywords'),
                 ),
        MelLString('RNAM','rnam'),
        MelBase('FNAM','fnam_p'),
        MelFid('KNAM','keyword'),
        MelBase('DSTF','dstf_p'), #--Always 0, what is it for?
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAddn(MelRecord):
    """Addon"""
    classType = 'ADDN'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelModel(),
        MelBase('DATA','data_p'),
        MelBase('DNAM','dnam_p'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArma(MelRecord):
    """Armor addon?"""
    classType = 'ARMA'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelBODT(),
        MelFid('RNAM','race'),
        MelBase('DNAM','dnam_p'),
        MelModel('male_model','MOD2'),
        MelModel('female_model','MOD3'),
        MelModel('male_model_1st','MOD4'),
        MelModel('female_model_1st','MOD5'),
        MelFidList('MODL','races'),
        MelFid('SNDD','foodSound'),
        MelFid('NAM0','skin0'),
        MelFid('NAM1','skin1'),
        MelFid('NAM2','skin2'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArmo(MelRecord):
    """Armor"""
    classType = 'ARMO'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelLString('FULL','full'),
        MelFid('EITM','enchantment'),
        MelModel('model1','MOD2'),
        MelModel('model3','MOD4'),
        MelBODT(),
        MelFid('ETYP','equipType'),
        MelFid('BIDS','bashImpact'),
        MelFid('BAMT','material'),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelFid('RNAM','race'),
        MelGroup('keywords',
                 MelStruct('KSIZ','I','num'),
                 MelFidList('KWDA','keywords'),
                 ),
        MelLString('DESC','description'),
        MelFids('MODL','addons'),
        MelStruct('DATA','=If','value','weight'),
        MelFid('TNAM','baseItem'),
        MelStruct('DNAM','I','armorRating'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAmmo(MelRecord):
    """Ammo record (arrows)"""
    classType = 'AMMO'
    # TODO: verify these flags for Skyrim
    _flags = bolt.Flags(0L,bolt.Flags.getNames('notNormalWeapon'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelLString('DESC','description'),
        MelStruct('KSIZ','I','numKeywords'),
        MelFidList('KWDA','keywords'),
        MelStruct('DATA','fIff','speed',(_flags,'flags',0L),'damage','weight'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCobj(MelRecord):
    """Constructible Object record (recipies)"""
    classType = 'COBJ'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('COCT','I','componentCount'),
        MelStructs('CNTO','=2I','components',(FID,'item',None),'count'),
        MelBase('CTDA','conditions'), #MelConditions(),
        MelFid('CNAM','resultingItem'),
        MelStruct('NAM1','H','resultingQuantity'),
        MelFid('BNAM','craftingStation'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreGmst(MreGmstBase):
    """Skyrim GMST record"""
    Master = u'Skryim'

#------------------------------------------------------------------------------
class MreMisc(MelRecord):
    """Misc. Item"""
    classType = 'MISC'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel(),
        MelGroup('keywords',
                 MelStruct('KSIZ','I','num'),
                 MelFidList('KWDA','keywords'),
                 ),
        MelStruct('DATA','=If','value','weight'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------

#--Record Types
brec.MreRecord.type_class = dict((x.classType,x) for x in (
    MreAact, MreActi, MreAddn, MreAmmo, MreArma, MreArmo, MreCobj, MreGlob,
    MreGmst, MreMisc,
    MreHeader,
    ))

#--Simple records
brec.MreRecord.simpleTypes = (set(brec.MreRecord.type_class) -
    set(('TES4')))

#--Mergeable record types
mergeClasses = (
    MreAact, MreAmmo, MreArma, MreArmo, MreGlob, MreGmst, MreMisc,
    )

#--Extra read/write classes
readClasses = ()
writeClasses = ()
