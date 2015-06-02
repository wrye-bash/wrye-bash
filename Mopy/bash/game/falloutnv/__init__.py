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

"""This modules defines static data for use by bush, when TES V:
   Skyrim is set at the active game."""
import re
import struct
from constants import *
from ... import brec
from records import *
from ...brec import MreGlob, BaseRecordHeader, ModError

#--Name of the game to use in UI.
displayName = u'Fallout New Vegas'
#--Name of the game's filesystem folder.
fsName = u'FalloutNV'
#--Alternate display name to use instead of "Wrye Bash for ***"
altName = u'Wrye Flash NV'
#--Name of game's default ini file.
defaultIniFile = u'Fallout_default.ini'

#--Exe to look for to see if this is the right game
exe = u'FalloutNV.exe'

#--Registry keys to read to find the install location
regInstallKeys = (u'Bethesda Softworks\\FalloutNV',u'Installed Path')
#--patch information
## URL to download patches for the main game.
patchURL = u''
## Tooltip to display over the URL when displayed
patchTip = u''

#--URL to the Nexus site for this game
nexusUrl = u'http://www.nexusmods.com/newvegas/'
nexusName = u'New Vegas Nexus'
nexusKey = u'bash.installers.openNewVegasNexus'

#--Garden of Eden Creation Kit information
class cs:
    shortName = u'GECK'                  # Abbreviated name
    longName = u'Garden of Eden Creation Kit'                   # Full name
    exe = u'GECK.exe'                   # Executable to run
    seArgs = u'-editor'                     # Argument to pass to the SE to load the CS
    imageName = u'geck%s.png'                  # Image name template for the status bar

#--Script Extender information
class se:
    shortName = u'NVSE'                      # Abbreviated name
    longName = u'Fallout Script Extender'   # Full name
    exe = u'nvse_loader.exe'                 # Exe to run
    steamExe = u'nvse_loader.dll'           # Exe to run if a steam install
    url = u'http://nvse.silverlock.org/'     # URL to download from
    urlTip = u'http://nvse.silverlock.org/'  # Tooltip for mouse over the URL

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
se_sd = u''

#--Graphics Extender information
class ge:
    shortName = u''
    longName = u''
    exe = u''
    url = u''
    urlTip = u''

#--4gb Launcher
class laa:
    name = u''           # Display name of the launcher
    exe = u'*DNE*'       # Executable to run
    launchesSE = False   # Whether the launcher will automatically launch the SE

# Files BAIN shouldn't skip
dontSkip = (
# Nothing so far
)

# Directories where specific file extensions should not be skipped by BAIN
dontSkipDirs = {
# Nothing so far
}

#--Folders BAIN should never CRC check in the Data directory
SkipBAINRefresh = {
    #Use lowercase names
    u'fnvedit backups',
}

#--Some stuff dealing with INI files
class ini:
    #--True means new lines are allowed to be added via INI Tweaks
    #  (by default)
    allowNewLines = False

    #--INI Entry to enable BSA Redirection
    # bsaRedirection = (u'Archive',u'sArchiveList')
    bsaRedirection = (u'',u'')

#--Save Game format stuff
class ess:
    # Save file capabilities
    canReadBasic = True         # All the basic stuff needed for the Saves Tab
    canEditMasters = True       # Adjusting save file masters
    canEditMore = False         # No advanced editing

    # Save file extension.
    ext = u'.fos';

    @staticmethod
    def load(ins,header):
        """Extract basic info from save file.close
           At a minimum, this should set the following
           attrubutes in 'header':
            pcName
            pcLevel
            pcLocation
            gameDate
            gameDays
            gameTicks (seconds*1000)
            image (ssWidth,ssHeight,ssData)
            masters
        """
        if ins.read(11) != 'FO3SAVEGAME':
            raise Exception(u'Save file is not a Fallout New Vegas save game.')
        headerSize, = struct.unpack('I',ins.read(4))
        unknown,delim = struct.unpack('Ic',ins.read(5))
        header.language = ins.read(64)
        delim, = struct.unpack('c',ins.read(1))
        ssWidth,delim1,ssHeight,delim2,ssDepth,delim3 = struct.unpack('=IcIcIc',ins.read(15))
        #--Name, nickname, level, location, playtime
        size,delim = struct.unpack('Hc',ins.read(3))
        header.pcName = ins.read(size)
        delim, = struct.unpack('c',ins.read(1))
        size,delim = struct.unpack('Hc',ins.read(3))
        header.pcNick = ins.read(size)
        delim, = struct.unpack('c',ins.read(1))
        header.pcLevel,delim = struct.unpack('Ic',ins.read(5))
        size,delim = struct.unpack('Hc',ins.read(3))
        header.pcLocation = ins.read(size)
        delim, = struct.unpack('c',ins.read(1))
        size,delim = struct.unpack('Hc',ins.read(3))
        header.playTime = ins.read(size)
        delim, = struct.unpack('c',ins.read(1))
        #--Image Data
        ssData = ins.read(3*ssWidth*ssHeight)
        header.image = (ssWidth,ssHeight,ssData)
        #--Masters
        unknown,masterListSize = struct.unpack('=BI',ins.read(5))
        if unknown != 0x1B:
            raise Exception(u'%s: Unknown byte is not 0x1B.' % path)
        del header.masters[:]
        numMasters,delim = struct.unpack('Bc',ins.read(2))
        for count in range(numMasters):
            size,delim = struct.unpack('Hc',ins.read(3))
            header.masters.append(ins.read(size))
            delim, = struct.unpack('c',ins.read(1))


    @staticmethod
    def writeMasters(ins,out,header):
        """Rewrites masters of existing save file."""
        def unpack(format,size):
            return struct.unpack(format,ins.read(size))
        def pack(format,*args):
            out.write(struct.pack(format,*args))
        #--Header
        out.write(ins.read(11))
        #--SaveGameHeader
        size, = unpack('I',4)
        pack('I',size)
        out.write(ins.read(65))
        ssWidth,delim1,ssHeight,delim2 = unpack('=IcIc',10)
        pack('=IcIc',ssWidth,delim1,ssHeight,delim2)
        out.write(ins.read(size-80))
        #--Image Data
        out.write(ins.read(3*ssWidth*ssHeight))
        #--Skip old masters
        unknown,oldMasterListSize = unpack('=BI',5)
        if unknown != 0x1B:
            raise Exception(u'%s: Unknown byte is not 0x1B.' % path)
        numMasters,delim = unpack('Bc',2)
        oldMasters = []
        for count in range(numMasters):
            size,delim = unpack('Hc',3)
            oldMasters.append(ins.read(size))
            delim, = unpack('c',1)
        #--Write new masters
        newMasterListSize = 2 + (4 * len(header.masters))
        for master in header.masters:
            newMasterListSize += len(master)
        pack('=BI',unknown,newMasterListSize)
        pack('Bc',len(header.masters),'|')
        for master in header.masters:
            pack('Hc',len(master),'|')
            out.write(master.s)
            pack('c','|')
        #--Fids Address
        offset = out.tell() - ins.tell()
        fidsAddress, = unpack('I',4)
        pack('I',fidsAddress+offset)
        #--???? Address
        unknownAddress, = unpack('I',4)
        pack('I',unknownAddress+offset)
        #--???? Address
        unknownAddress, = unpack('I',4)
        pack('I',unknownAddress+offset)
        #--???? Address
        unknownAddress, = unpack('I',4)
        pack('I',unknownAddress+offset)
        #--???? Address
        unknownAddress, = unpack('I',4)
        pack('I',unknownAddress+offset)
        #--Copy remainder
        while True:
            buffer= ins.read(0x5000000)
            if not buffer: break
            out.write(buffer)
        return oldMasters

#--INI files that should show up in the INI Edits tab
iniFiles = [
    u'Fallout.ini',
    u'FalloutPrefs.ini',
    ]

#--INI setting to setup Save Profiles
saveProfilesKey = (u'General',u'SLocalSavePath')

#--The main plugin Wrye Bash should look for
masterFiles = [
    u'FalloutNV.esm',
    ]
#--Plugin files that can't be deactivated
nonDeactivatableFiles = []

namesPatcherMaster = re.compile(ur"^FalloutNV.esm$",re.I|re.U)

#The pickle file for this game. Holds encoded GMST IDs from the big list below.
pklfile = ur'bash\db\FalloutNV_ids.pkl'

#--Game ESM/ESP/BSA files
#  These filenames need to be in lowercase,
# bethDataFiles = set()
# Moved to skyrim_const

#--Every file in the Data directory from Bethsoft
# allBethFiles = set()
# Moved to skyrim_const

#--BAIN: Directories that are OK to install to
dataDirs = {
    u'bash patches',
    u'distantlod',
    u'docs',
    u'facegen',
    u'fonts',
    u'menus',
    u'meshes',
    u'music',
    u'shaders',
    u'sound',
    u'textures',
    u'trees',
    u'video',
    }
dataDirsPlus = {
    u'streamline',
    u'_tejon',
    u'ini tweaks',
    u'scripts',
    u'pluggy',
    u'ini',
    u'nvse'
    }

# Installer -------------------------------------------------------------------
# ensure all path strings are prefixed with 'r' to avoid interpretation of
#   accidental escape sequences
wryeBashDataFiles = {
    ur'Bashed Patch.esp',
    ur'Bashed Patch, 0.esp',
    ur'Bashed Patch, 1.esp',
    ur'Bashed Patch, 2.esp',
    ur'Bashed Patch, 3.esp',
    ur'Bashed Patch, 4.esp',
    ur'Bashed Patch, 5.esp',
    ur'Bashed Patch, 6.esp',
    ur'Bashed Patch, 7.esp',
    ur'Bashed Patch, 8.esp',
    ur'Bashed Patch, 9.esp',
    ur'Bashed Patch, CBash.esp',
    ur'Bashed Patch, Python.esp',
    ur'Bashed Patch, FCOM.esp',
    ur'Bashed Patch, Warrior.esp',
    ur'Bashed Patch, Thief.esp',
    ur'Bashed Patch, Mage.esp',
    ur'Bashed Patch, Test.esp',
    ur'ArchiveInvalidationInvalidated!.bsa'
    ur'Fallout - AI!.bsa'
}
wryeBashDataDirs = {
    ur'Bash Patches',
    ur'INI Tweaks'
}
ignoreDataFiles = {
#    ur'NVSE\Plugins\Construction Set Extender.dll',
#    ur'NVSE\Plugins\Construction Set Extender.ini'
}
ignoreDataFilePrefixes = {
}
ignoreDataDirs = {
#    ur'NVSE\Plugins\ComponentDLLs\CSE',
    ur'LSData'
}


#--Bash Tags supported by this game
# 'Body-F', 'Body-M', 'Body-Size-M', 'Body-Size-F', 'C.Climate', 'C.Light', 'C.Music', 'C.Name', 'C.RecordFlags',
# 'C.Owner', 'C.Water','Deactivate', 'Delev', 'Eyes', 'Factions', 'Relations', 'Filter', 'Graphics', 'Hair',
# 'IIM', 'Invent', 'Names', 'NoMerge', 'NpcFaces', 'R.Relations', 'Relev', 'Scripts', 'ScriptContents', 'Sound',
# 'Stats', 'Voice-F', 'Voice-M', 'R.Teeth', 'R.Mouth', 'R.Ears', 'R.Head', 'R.Attributes-F',
# 'R.Attributes-M', 'R.Skills', 'R.Description', 'Roads', 'Actors.Anims',
# 'Actors.AIData', 'Actors.DeathItem', 'Actors.AIPackages', 'Actors.AIPackagesForceAdd', 'Actors.Stats',
# 'Actors.ACBS', 'NPC.Class', 'Actors.CombatStyle', 'Creatures.Blood',
# 'NPC.Race','Actors.Skeleton', 'NpcFacesForceFullImport', 'MustBeActiveIfImported',
# 'Deflst', 'Destructible', 'WeaponMods'
allTags = sorted((
    u'C.Acoustic', u'C.Climate', u'C.Encounter', u'C.ImageSpace' ,u'C.Light',
    u'C.Music', u'C.Name', u'C.Owner', u'C.RecordFlags',
	u'C.Water', u'Deactivate', u'Deflst', u'Delev', u'Destructible',
	u'Factions', u'Filter', u'Graphics', u'Invent', u'Names', u'NoMerge',
	u'Relations', u'Relev', u'Sound', u'Stats', u'WeaponMods',
    ))

# ActorImporter, AliasesPatcher, AssortedTweaker, CellImporter, ContentsChecker,
# DeathItemPatcher, DestructiblePatcher, FidListsMerger, GlobalsTweaker,
# GmstTweaker, GraphicsPatcher, ImportFactions, ImportInventory, ImportRelations,
# ImportScriptContents, ImportScripts, KFFZPatcher, ListsMerger, NamesPatcher,
# NamesTweaker, NPCAIPackagePatcher, NpcFacePatcher, PatchMerger, RacePatcher,
# RoadImporter, SoundPatcher, StatsPatcher, UpdateReferences, WeaponModsPatcher,
#--Patcher available when building a Bashed Patch (referenced by class name)
patchers = (
    u'AliasesPatcher', u'CellImporter', u'DestructiblePatcher', u'FidListsMerger',
    u'GmstTweaker', u'GraphicsPatcher', u'ImportFactions', u'ImportInventory',
	u'ImportRelations', u'ListsMerger', u'NamesPatcher', u'PatchMerger',
	u'SoundPatcher', u'StatsPatcher', u'WeaponModsPatcher',
    )

#--CBash patchers available when building a Bashed Patch
CBash_patchers = tuple()


# Magic Info ------------------------------------------------------------------
weaponTypes = (
    _(u'Big gun'),
    _(u'Energy'),
    _(u'Small gun'),
    _(u'Melee'),
    _(u'Unarmed'),
    _(u'Thrown'),
    _(u'Mine'),
    )

# Race Info -------------------------------------------------------------------
raceNames = {
    0x000019 : _(u'Caucasian'),
    0x0038e5 : _(u'Hispanic'),
    0x0038e6 : _(u'Asian'),
    0x003b3e : _(u'Ghoul'),
    0x00424a : _(u'AfricanAmerican'),
    0x0042be : _(u'AfricanAmerican Child'),
    0x0042bf : _(u'AfricanAmerican Old'),
    0x0042c0 : _(u'Asian Child'),
    0x0042c1 : _(u'Asian Old'),
    0x0042c2 : _(u'Caucasian Child'),
    0x0042c3 : _(u'Caucasian Old'),
    0x0042c4 : _(u'Hispanic Child'),
    0x0042c5 : _(u'Hispanic Old'),
    0x04bb8d : _(u'Caucasian Raider'),
    0x04bf70 : _(u'Hispanic Raider'),
    0x04bf71 : _(u'Asian Raider'),
    0x04bf72 : _(u'AfricanAmerican Raider'),
    0x0987dc : _(u'Hispanic Old Aged'),
    0x0987dd : _(u'Asian Old Aged'),
    0x0987de : _(u'AfricanAmerican Old Aged'),
    0x0987df : _(u'Caucasian Old Aged'),
    }

raceShortNames = {
    0x000019 : u'Cau',
    0x0038e5 : u'His',
    0x0038e6 : u'Asi',
    0x003b3e : u'Gho',
    0x00424a : u'Afr',
    0x0042be : u'AfC',
    0x0042bf : u'AfO',
    0x0042c0 : u'AsC',
    0x0042c1 : u'AsO',
    0x0042c2 : u'CaC',
    0x0042c3 : u'CaO',
    0x0042c4 : u'HiC',
    0x0042c5 : u'HiO',
    0x04bb8d : u'CaR',
    0x04bf70 : u'HiR',
    0x04bf71 : u'AsR',
    0x04bf72 : u'AfR',
    0x0987dc : u'HOA',
    0x0987dd : u'AOA',
    0x0987de : u'FOA',
    0x0987df : u'COA',
    }

raceHairMale = {
    0x000019 : 0x014b90, #--Cau
    0x0038e5 : 0x0a9d6f, #--His
    0x0038e6 : 0x014b90, #--Asi
    0x003b3e : None, #--Gho
    0x00424a : 0x0306be, #--Afr
    0x0042be : 0x060232, #--AfC
    0x0042bf : 0x0306be, #--AfO
    0x0042c0 : 0x060232, #--AsC
    0x0042c1 : 0x014b90, #--AsO
    0x0042c2 : 0x060232, #--CaC
    0x0042c3 : 0x02bfdb, #--CaO
    0x0042c4 : 0x060232, #--HiC
    0x0042c5 : 0x02ddee, #--HiO
    0x04bb8d : 0x02bfdb, #--CaR
    0x04bf70 : 0x02bfdb, #--HiR
    0x04bf71 : 0x02bfdb, #--AsR
    0x04bf72 : 0x0306be, #--AfR
    0x0987dc : 0x0987da, #--HOA
    0x0987dd : 0x0987da, #--AOA
    0x0987de : 0x0987d9, #--FOA
    0x0987df : 0x0987da, #--COA
    }

raceHairFemale = {
    0x000019 : 0x05dc6b, #--Cau
    0x0038e5 : 0x05dc76, #--His
    0x0038e6 : 0x022e50, #--Asi
    0x003b3e : None, #--Gho
    0x00424a : 0x05dc78, #--Afr
    0x0042be : 0x05a59e, #--AfC
    0x0042bf : 0x072e39, #--AfO
    0x0042c0 : 0x05a5a3, #--AsC
    0x0042c1 : 0x072e39, #--AsO
    0x0042c2 : 0x05a59e, #--CaC
    0x0042c3 : 0x072e39, #--CaO
    0x0042c4 : 0x05a59e, #--HiC
    0x0042c5 : 0x072e39, #--HiO
    0x04bb8d : 0x072e39, #--CaR
    0x04bf70 : 0x072e39, #--HiR
    0x04bf71 : 0x072e39, #--AsR
    0x04bf72 : 0x072e39, #--AfR
    0x0987dc : 0x044529, #--HOA
    0x0987dd : 0x044529, #--AOA
    0x0987de : 0x044529, #--FOA
    0x0987df : 0x044529, #--COA
    }

#--Plugin format stuff
class esp:
    #--Wrye Bash capabilities
    canBash = True          # Can create Bashed Patches
    canCBash = False        # CBash can handle this game's records
    canEditHeader = True    # Can edit anything in the TES4 record

    #--Valid ESM/ESP header versions
    validHeaderVersions = (0.94,1.32,1.33,1.34)

    #--Strings Files
    stringsFiles = []

    #--Top types in FalloutNV order.
    topTypes = ['GMST', 'TXST', 'MICN', 'GLOB', 'CLAS', 'FACT', 'HDPT', 'HAIR', 'EYES',
        'RACE', 'SOUN', 'ASPC', 'MGEF', 'SCPT', 'LTEX', 'ENCH', 'SPEL', 'ACTI', 'TACT',
        'TERM', 'ARMO', 'BOOK', 'CONT', 'DOOR', 'INGR', 'LIGH', 'MISC', 'STAT', 'SCOL',
        'MSTT', 'PWAT', 'GRAS', 'TREE', 'FURN', 'WEAP', 'AMMO', 'NPC_', 'CREA', 'LVLC',
        'LVLN', 'KEYM', 'ALCH', 'IDLM', 'NOTE', 'COBJ', 'PROJ', 'LVLI', 'WTHR', 'CLMT',
        'REGN', 'NAVI', 'DIAL', 'QUST', 'IDLE', 'PACK', 'CSTY', 'LSCR', 'ANIO', 'WATR',
        'EFSH', 'EXPL', 'DEBR', 'IMGS', 'IMAD', 'FLST', 'PERK', 'BPTD', 'ADDN', 'AVIF',
        'RADS', 'CAMS', 'CPTH', 'VTYP', 'IPCT', 'IPDS', 'ARMA', 'ECZN', 'MESG', 'RGDL',
        'DOBJ', 'LGTM', 'MUSC', 'IMOD', 'REPU', 'RCPE', 'RCCT', 'CHIP', 'CSNO', 'LSCT',
        'MSET', 'ALOC', 'CHAL', 'AMEF', 'CCRD', 'CMNY', 'CDCK', 'DEHY', 'HUNG', 'SLPD',
        'CELL', 'WRLD',]

    #--Dict mapping 'ignored' top types to un-ignored top types.
    topIgTypes = dict()

    #-> this needs updating for Skyrim
    recordTypes = set(
        topTypes + 'GRUP,TES4,ACHR,ACRE,INFO,LAND,NAVM,PGRE,PMIS,REFR'.split(
            ','))

#--Mod I/O
class RecordHeader(BaseRecordHeader):
    size = 24 # Size in bytes of a record header

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
        type,size,uint0,uint1,uint2,uint3 = ins.unpack('=4s5I',24,'REC_HEADER')
        #--Bad type?
        if type not in esp.recordTypes:
            raise ModError(ins.inName,u'Bad header type: '+repr(type))
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
                raise ModError(ins.inName,u'Bad Top GRUP type: '+repr(str0))
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

#------------------------------------------------------------------------------
# These Are normally not mergable but added to brec.MreRecord.type_class
#
#       MreCell,
#------------------------------------------------------------------------------
# These have undefined FormIDs Do not merge them
#
#
#------------------------------------------------------------------------------
# These need syntax revision but can be merged once that is corrected
#
#
#------------------------------------------------------------------------------
#--Mergeable record types

# Old Mergable from Valda's version
# MreActi, MreAlch, MreAloc, MreAmef, MreAmmo, MreAnio, MreAppa, MreArma, MreArmo, MreAspc, MreAvif,
# MreBook, MreBptd, MreBsgn, MreCcrd, MreCdck, MreChal, MreChip, MreClas, MreClmt, MreClot, MreCmny,
# MreCont, MreCrea, MreCsno, MreCsty, MreDebr, MreDehy, MreDobj, MreDoor, MreEczn, MreEfsh, MreEnch,
# MreExpl, MreEyes, MreFact, MreFlor, MreFlst, MreFurn, MreGlob, MreGras, MreHair, MreHdpt, MreHung,
# MreIdle, MreIdlm, MreImad, MreImod, MreIngr, MreIpct, MreIpds, MreKeym, MreLigh, MreLscr, MreLsct,
# MreLtex, MreLvlc, MreLvli, MreLvln, MreLvsp, MreMgef, MreMicn, MreMisc, MreMset, MreMstt, MreMusc,
# MreNote, MreNpc, MrePack, MrePerk, MreProj, MrePwat, MreQust, MreRace, MreRcct, MreRcpe, MreRegn,
# MreRepu, MreSbsp, MreScpt, MreSgst, MreSkil, MreSlgm, MreSlpd, MreSoun, MreSpel, MreStat, MreTact,
# MreTerm, MreTree, MreTxst, MreVtyp, MreWatr, MreWeap, MreWthr,

mergeClasses = (
        MreActi, MreAddn, MreAlch, MreAloc, MreAmef, MreAmmo, MreAnio, MreArma, MreArmo, MreAspc,
        MreAvif, MreBook, MreBptd, MreCams, MreCcrd, MreCdck, MreChal, MreChip, MreClas, MreClmt,
        MreCmny, MreCobj, MreCont, MreCpth, MreCrea, MreCsno, MreCsty, MreDebr, MreDehy, MreDobj,
        MreDoor, MreEczn, MreEfsh, MreEnch, MreExpl, MreEyes, MreFact, MreFlst, MreFurn, MreGlob,
        MreGras, MreHair, MreHdpt, MreHung, MreIdle, MreIdlm, MreImad, MreImgs, MreImod, MreIngr,
        MreIpct, MreIpds, MreKeym, MreLgtm, MreLigh, MreLscr, MreLsct, MreLtex, MreLvlc, MreLvli,
        MreLvln, MreMesg, MreMgef, MreMicn, MreMisc, MreMset, MreMstt, MreMusc, MreNote, MreNpc,
        MrePack, MrePerk, MreProj, MrePwat, MreQust, MreRace, MreRads, MreRcct, MreRcpe, MreRegn,
        MreRepu, MreRgdl, MreScol, MreScpt, MreSlpd, MreSoun, MreSpel, MreStat, MreTact, MreTerm,
        MreTree, MreTxst, MreVtyp, MreWatr, MreWeap, MreWthr,
    )

#--Extra read classes: these record types will always be loaded, even if patchers
#  don't need them directly (for example, for MGEF info)
readClasses = ()
writeClasses = ()


def init():
    # Due to a bug with py2exe, 'reload' doesn't function properly.  Instead of
    # re-executing all lines within the module, it acts like another 'import'
    # statement - in otherwords, nothing happens.  This means any lines that
    # affect outside modules must do so within this function, which will be
    # called instead of 'reload'

# From Valda's version
# MreAchr, MreAcre, MreActi, MreAlch, MreAloc, MreAmef, MreAmmo, MreAnio, MreAppa, MreArma,
# MreArmo, MreAspc, MreAvif, MreBook, MreBptd, MreBsgn, MreCcrd, MreCdck, MreChal,
# MreChip, MreClas, MreClmt, MreClot, MreCmny, MreCont, MreCrea, MreCsno, MreCsty, MreDebr,
# MreDehy, MreDial, MreDobj, MreDoor, MreEczn, MreEfsh, MreEnch, MreExpl, MreEyes, MreFact,
# MreFlor, MreFlst, MreFurn, MreGlob, MreGmst, MreGras, MreHair, MreHdpt, MreHung, MreIdle,
# MreIdlm, MreImad, MreImod, MreInfo, MreIngr, MreIpct, MreIpds, MreKeym, MreLigh, MreLscr,
# MreLsct, MreLtex, MreLvlc, MreLvli, MreLvln, MreLvsp, MreMgef, MreMicn, MreMisc, MreMset,
# MreMstt, MreMusc, MreNote, MreNpc, MrePack, MrePerk, MreProj, MrePwat, MreQust,
# MreRace, MreRcct, MreRcpe, MreRefr, MreRegn, MreRepu, MreRoad, MreSbsp, MreScpt, MreSgst,
# MreSkil, MreSlgm, MreSlpd, MreSoun, MreSpel, MreStat, MreTact, MreTerm, MreTes4, MreTree,
# MreTxst, MreVtyp, MreWatr, MreWeap, MreWthr,
# MreCell, MreWrld, MreNavm,

    brec.ModReader.recHeader = RecordHeader

    #--Record Types
    brec.MreRecord.type_class = dict((x.classType,x) for x in (
        MreActi, MreAddn, MreAlch, MreAloc, MreAmef, MreAmmo, MreAnio, MreArma, MreArmo, MreAspc,
        MreAvif, MreBook, MreBptd, MreCams, MreCcrd, MreCdck, MreChal, MreChip, MreClas, MreClmt,
        MreCmny, MreCobj, MreCont, MreCpth, MreCrea, MreCsno, MreCsty, MreDebr, MreDehy, MreDobj,
        MreDoor, MreEczn, MreEfsh, MreEnch, MreExpl, MreEyes, MreFact, MreFlst, MreFurn, MreGlob,
        MreGras, MreHair, MreHdpt, MreHung, MreIdle, MreIdlm, MreImad, MreImgs, MreImod, MreIngr,
        MreIpct, MreIpds, MreKeym, MreLgtm, MreLigh, MreLscr, MreLsct, MreLtex, MreLvlc, MreLvli,
        MreLvln, MreMesg, MreMgef, MreMicn, MreMisc, MreMset, MreMstt, MreMusc, MreNote, MreNpc,
        MrePack, MrePerk, MreProj, MrePwat, MreQust, MreRace, MreRads, MreRcct, MreRcpe, MreRegn,
        MreRepu, MreRgdl, MreScol, MreScpt, MreSlpd, MreSoun, MreSpel, MreStat, MreTact, MreTerm,
        MreTree, MreTxst, MreVtyp, MreWatr, MreWeap, MreWthr,
        # Not Mergable
        MreAchr, MreAcre, MreCell, MreDial, MreGmst, MreInfo, MreNavi, MreNavm, MrePgre, MrePmis,
        MreRefr, MreWrld,
        MreHeader,
        ))

    #--Simple records
    brec.MreRecord.simpleTypes = (
    # set(('TES4','ACHR','ACRE','REFR','CELL','PGRD','PGRE','LAND','WRLD','INFO','DIAL','NAVM')))
        set(brec.MreRecord.type_class) - {
        'TES4','ACHR','ACRE','CELL','DIAL','INFO','LAND','NAVI','NAVM','PGRE','PMIS','REFR','WRLD',
        })

