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

"""This modules defines static data for use by bush, when Fallout 4 is set as
   the active game."""

import re
import struct
import itertools
from .constants import *
from .records import MreHeader
from ... import brec
from ...brec import BaseRecordHeader, ModError

#--Name of the game to use in UI.
displayName = u'Fallout 4'
#--Name of the game's filesystem folder.
fsName = u'Fallout4'
#--Alternate display name to use instead of "Wrye Bash for ***"
altName = u'Wrye Flash'
#--Name of game's default ini file.
defaultIniFile = u'Fallout4_default.ini'

#--Exe to look for to see if this is the right game
exe = u'Fallout4.exe'

#--Registry keys to read to find the install location
regInstallKeys = (u'Bethesda Softworks\\Fallout4', u'Installed Path')

#--patch information
## URL to download patches for the main game.
# Update via steam
patchURL = u''
patchTip = u'Update via Steam'

#--URL to the Nexus site for this game
nexusUrl = u'http://www.nexusmods.com/fallout4/'
nexusName = u'Fallout 4 Nexus'
nexusKey = 'bash.installers.openFallout4Nexus.continue'

# Bsa info
allow_reset_bsa_timestamps = False

#--Creation Kit Set information
class cs:
    ## TODO:  When the Fallout 4 Creation Kit is actually released, double check
    ## that the filename is correct, and create an actual icon
    shortName = u'FO4CK'                 # Abbreviated name
    longName = u'Fallout 4 Creation Kit' # Full name
    exe = u'FO4CK.exe'                   # Executable to run
    seArgs = None                        # u'-editor'
    imageName = u'creationkit%s.png'     # Image name template for the status bar

#--Script Extender information
class se:
    ## TODO: verify filenames once F4SE is released
    shortName = u'F4SE'                      # Abbreviated name
    longName = u'Fallout 4 Script Extender'  # Full name
    exe = u'f4se_loader.exe'                 # Exe to run
    steamExe = u'f4se_steam_loader.dll'      # Exe to run if a steam install
    url = u'http://f4se.silverlock.org/'     # URL to download from
    urlTip = u'http://f4se.silverlock.org/'  # Tooltip for mouse over the URL

#--Script Dragon
class sd:
    shortName = u''
    longName = u''
    installDir = u''

#--SkyProc Patchers
class sp:
    shortName = u''
    longName = u''
    installDir = u''

#--Quick shortcut for combining the SE and SD names
se_sd = se.shortName

#--Graphics Extender information
class ge:
    shortName = u''
    longName = u''
    ## exe is treated specially here.  If it is a string, then it should
    ## be the path relative to the root directory of the game
    ## if it is list, each list element should be an iterable to pass to Path.join
    ## relative to the root directory of the game.  In this case, each filename
    ## will be tested in reverse order.  This was required for Oblivion, as the newer
    ## OBGE has a different filename than the older OBGE
    exe = u'**DNE**'
    url = u''
    urlTip = u''

#--4gb Launcher
class laa:
    # Skyrim has a 4gb Launcher, but as of patch 1.3.10, it is
    # no longer required (Bethsoft updated TESV.exe to already
    # be LAA)
    name = u''
    exe = u'**DNE**'       # Executable to run
    launchesSE = False

# Files BAIN shouldn't skip
dontSkip = (
# Nothing so far
)

# Directories where specific file extensions should not be skipped by BAIN
dontSkipDirs = {
    # This rule is to allow mods with string translation enabled.
    'interface\\translations':['.txt']
}

#Folders BAIN should never check
SkipBAINRefresh = {
    #Use lowercase names
    u'fo4edit backups',
}

#--Some stuff dealing with INI files
class ini:
    #--True means new lines are allowed to be added via INI Tweaks
    #  (by default)
    allowNewLines = True

    #--INI Entry to enable BSA Redirection
    bsaRedirection = (u'',u'')

#--Save Game format stuff
class ess:
    # Save file capabilities
    canReadBasic = True         # All the basic stuff needed for the Saves Tab
    canEditMasters = False      # Adjusting save file masters
    canEditMore = False         # No advanced editing
    ext = u'.fos'               # Save file extension

    @staticmethod
    def load(ins,header):
        """Extract info from save file."""
        #--Header
        if ins.read(12) != 'FO4_SAVEGAME':
            raise Exception(u'Save file is not a Fallout 4 save game.')
        headerSize, = struct.unpack('I',ins.read(4))
        #--Name, location
        version,saveNumber,size = struct.unpack('2IH',ins.read(10))
        header.pcName = ins.read(size)
        header.pcLevel, = struct.unpack('I',ins.read(4))
        size, = struct.unpack('H',ins.read(2))
        header.pcLocation = ins.read(size)
        size, = struct.unpack('H',ins.read(2))
        header.gameDate = ins.read(size)
        # gameDate format: Xd.Xh.Xm.X days.X hours.X minutes
        days,hours,minutes,_days,_hours,_minutes = header.gameDate.split('.')
        days = int(days[:-1])
        hours = int(hours[:-1])
        minutes = int(minutes[:-1])
        header.gameDays = float(days) + float(hours)/24 + float(minutes)/(24*60)
        # Assuming still 1000 ticks per second
        header.gameTicks = (days*24*60*60 + hours*60*60 + minutes*60) * 1000
        size, = struct.unpack('H',ins.read(2))
        ins.seek(ins.tell()+size+2+4+4+8) # raceEdid, unk0, unk1, unk2, ftime
        ssWidth, = struct.unpack('I',ins.read(4))
        ssHeight, = struct.unpack('I',ins.read(4))
        if ins.tell() != headerSize + 16:
            raise Exception(u'Save game header size (%s) not as expected (%s).' % (ins.tell()-16,headerSize))
        #--Image Data
        # Fallout 4 is in 32bit RGB, Bash is expecting 24bit RGB
        ssData = ins.read(4*ssWidth*ssHeight)
        # pick out only every 3 bytes, drop the 4th (alpha channel)
        ## TODO: Setup Bash to use the alpha data
        #ssAlpha = ''.join(itertools.islice(ssData, 0, None, 4))
        ssData = ''.join(itertools.compress(ssData, itertools.cycle(reversed(range(4)))))
        header.image = (ssWidth,ssHeight,ssData)
        #--unknown
        unk3 = ins.read(1)
        size, = struct.unpack('H',ins.read(2))
        gameVersion = ins.read(size)
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
        #--Magic (FO4_SAVEGAME)
        out.write(ins.read(12))
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
        ## TODO: See if this is needed for FO4
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
    u'Fallout4.ini',
    u'Fallout4Prefs.ini',
    ]

#--INI setting to setup Save Profiles
saveProfilesKey = (u'General',u'SLocalSavePath')

#--The main plugin Wrye Bash should look for
masterFiles = [
    u'Fallout4.esm',
    ]

namesPatcherMaster = re.compile(ur"^Fallout4.esm$",re.I|re.U)

#The pickle file for this game. Holds encoded GMST IDs from the big list below.
pklfile = ur'bash\db\Fallout4_ids.pkl'

#--BAIN: Directories that are OK to install to
dataDirs = {
    u'interface',
    u'lodsettings',
    u'materials',
    u'meshes',
    u'misc',
    u'music',
    u'programs',
    u'scripts',
    u'seq',
    u'shadersfx',
    u'sound',
    u'strings',
    u'textures',
    u'video',
    u'vis',
}
dataDirsPlus = {
    u'f4se',
    u'ini',
}

# Installer -------------------------------------------------------------------
# ensure all path strings are prefixed with 'r' to avoid interpretation of
#   accidental escape sequences
wryeBashDataFiles = {
    u'Bashed Patch.esp',
    u'Bashed Patch, 0.esp',
    u'Bashed Patch, 1.esp',
    u'Bashed Patch, 2.esp',
    u'Bashed Patch, 3.esp',
    u'Bashed Patch, 4.esp',
    u'Bashed Patch, 5.esp',
    u'Bashed Patch, 6.esp',
    u'Bashed Patch, 7.esp',
    u'Bashed Patch, 8.esp',
    u'Bashed Patch, 9.esp',
    u'Bashed Patch, CBash.esp',
    u'Bashed Patch, Python.esp',
    u'Bashed Patch, Warrior.esp',
    u'Bashed Patch, Thief.esp',
    u'Bashed Patch, Mage.esp',
    u'Bashed Patch, Test.esp',
    u'Docs\\Bash Readme Template.html',
    u'Docs\\wtxt_sand_small.css',
    u'Docs\\wtxt_teal.css',
    u'Docs\\Bash Readme Template.txt',
    u'Docs\\Bashed Patch, 0.html',
    u'Docs\\Bashed Patch, 0.txt',
}

wryeBashDataDirs = {
    u'Bash Patches',
    u'INI Tweaks'
}

ignoreDataFiles = set()
ignoreDataFilePrefixes = set()
ignoreDataDirs = set()

#--Tags supported by this game
allTags = sorted(set())

#--Gui patcher classes available when building a Bashed Patch
patchers = tuple()

#--CBash Gui patcher classes available when building a Bashed Patch
CBash_patchers = tuple()

# Magic Info ------------------------------------------------------------------
weaponTypes = tuple()

# Race Info -------------------------------------------------------------------
raceNames = dict()
raceShortNames = dict()
raceHairMale = dict()
raceHairFemale = dict()

#--Plugin format stuff
class esp:
    #--Wrye Bash capabilities
    canBash = False         # Can create Bashed Patches
    canCBash = False        # CBash can handle this game's records
    canEditHeader = False   # Can edit anything in the TES4 record

    #--Valid ESM/ESP header versions
    validHeaderVersions = (0.95,)

    #--Strings Files
    stringsFiles = [
        ('mods',(u'Strings',),u'%(body)s_%(language)s.STRINGS'),
        ('mods',(u'Strings',),u'%(body)s_%(language)s.DLSTRINGS'),
        ('mods',(u'Strings',),u'%(body)s_%(language)s.ILSTRINGS'),
        ]

    #--Top types in Skyrim order.
    topTypes = ['GMST', 'KYWD', 'LCRT', 'AACT', 'TRNS', 'CMPO', 'TXST',
                'GLOB', 'DMGT', 'CLAS', 'FACT', 'HDPT', 'RACE', 'SOUN',
                'ASPC', 'MGEF', 'LTEX', 'ENCH', 'SPEL', 'ACTI', 'TACT',
                'ARMO', 'BOOK', 'CONT', 'DOOR', 'INGR', 'LIGH', 'MISC',
                'STAT', 'SCOL', 'MSTT', 'GRAS', 'TREE', 'FLOR', 'FURN',
                'WEAP', 'AMMO', 'NPC_', 'LVLN', 'KEYM', 'ALCH', 'IDLM',
                'NOTE', 'PROJ', 'HAZD', 'BNDS', 'TERM', 'LVLI', 'WTHR',
                'CLMT', 'SPGD', 'RFCT', 'REGN', 'NAVI', 'CELL', 'WRLD',
                'QUST', 'IDLE', 'PACK', 'CSTY', 'LSCR', 'ANIO', 'WATR',
                'EFSH', 'EXPL', 'DEBR', 'IMGS', 'IMAD', 'FLST', 'PERK',
                'BPTD', 'ADDN', 'AVIF', 'CAMS', 'CPTH', 'VTYP', 'MATT',
                'IPCT', 'IPDS', 'ARMA', 'ECZN', 'LCTN', 'MESG', 'DOBJ',
                'DFOB', 'LGTM', 'MUSC', 'FSTP', 'FSTS', 'SMBN', 'SMQN',
                'SMEN', 'MUST', 'DLVW', 'EQUP', 'RELA', 'ASTP', 'OTFT',
                'ARTO', 'MATO', 'MOVT', 'SNDR', 'SNCT', 'SOPM', 'COLL',
                'CLFM', 'REVB', 'PKIN', 'RFGP', 'AMDL', 'LAYR', 'COBJ',
                'OMOD', 'MSWP', 'ZOOM', 'INNR', 'KSSM', 'AECH', 'SCCO',
                'AORU', 'SCSN', 'STAG', 'NOCM', 'LENS', 'GDRY', 'OVIS',]


    #--Dict mapping 'ignored' top types to un-ignored top types.
    topIgTypes = dict([
            (struct.pack('I',(struct.unpack('I',type)[0]) | 0x1000),type)
            for type in topTypes
        ])

    #--Record types that don't appear at the top level (sub-GRUPs)
    recordTypes = (set(topTypes) |
                   {'GRUP','TES4','REFR','NAVM','PGRE','PHZD','LAND',
                       'PMIS','DLBR','DIAL','INFO','SCEN'})

#--Mod I/O
class RecordHeader(BaseRecordHeader):
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
        """Returns a RecordHeader object by reading the input stream."""
        rec_type,size,uint0,uint1,uint2,uint3 = ins.unpack('=4s5I',24,'REC_HEADER')
        #--Bad type?
        if rec_type not in esp.recordTypes:
            raise ModError(ins.inName,u'Bad header type: '+repr(rec_type))
        #--Record
        if rec_type != 'GRUP':
            pass
        #--Top Group
        elif uint1 == 0: #groupType == 0 (Top Type)
            str0 = struct.pack('I',uint0)
            if str0 in esp.topTypes:
                uint0 = str0
            elif str0 in esp.topIgTypes:
                uint0 = esp.topIgTypes[str0]
            else:
                raise ModError(ins.inName,u'Bad Top GRUP type: '+repr(str0))
        #--Other groups
        return RecordHeader(rec_type,size,uint0,uint1,uint2,uint3)

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

#--Mergeable record types
mergeClasses = tuple()

#--Extra read classes: these record types will always be loaded, even if
# patchers don't need them directly (for example, MGEF for magic effects info)
readClasses = tuple()
writeClasses = tuple()

def init():
    # Due to a bug with py2exe, 'reload' doesn't function properly.  Instead of
    # re-executing all lines within the module, it acts like another 'import'
    # statement - in otherwords, nothing happens.  This means any lines that
    # affect outside modules must do so within this function, which will be
    # called instead of 'reload'
    brec.ModReader.recHeader = RecordHeader

    #--Record Types
    brec.MreRecord.type_class = dict((x.classType,x) for x in (
        MreHeader,
        ))

    #--Simple records
    brec.MreRecord.simpleTypes = (
        set(brec.MreRecord.type_class) - {'TES4',})
