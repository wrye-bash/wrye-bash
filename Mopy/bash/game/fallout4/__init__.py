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

import struct
from .constants import *
from .default_tweaks import default_tweaks
from .records import MreHeader, MreLvli, MreLvln
from ... import brec
from ...brec import BaseRecordHeader
from ...exception import ModError

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
bsa_extension = ur'ba2'
supports_mod_inis = True
vanilla_string_bsas = {
    u'fallout4.esm': [u'Fallout4 - Interface.ba2'],
    u'dlcrobot.esm': [u'DLCRobot - Main.ba2'],
    u'dlcworkshop01.esm': [u'DLCworkshop01 - Main.ba2'],
    u'dlcworkshop02.esm': [u'DLCworkshop02 - Main.ba2'],
    u'dlcworkshop03.esm': [u'DLCworkshop03 - Main.ba2'],
    u'dlccoast.esm': [u'DLCCoast - Main.ba2'],
    u'dlcnukaworld.esm':  [u'DLCNukaWorld - Main.ba2'],
}
resource_archives_keys = (
    u'sResourceIndexFileList', u'sResourceStartUpArchiveList',
    u'sResourceArchiveList', u'sResourceArchiveList2',
    u'sResourceArchiveListBeta'
)

# plugin extensions
espm_extensions = {u'.esp', u'.esm', u'.esl'}

# Load order info
using_txt_file = True

#--Creation Kit Set information
class cs:
    ## TODO:  When the Fallout 4 Creation Kit is actually released, double check
    ## that the filename is correct, and create an actual icon
    shortName = u'FO4CK'                 # Abbreviated name
    longName = u'Creation Kit'           # Full name
    exe = u'CreationKit.exe'             # Executable to run
    seArgs = None                        # u'-editor'
    imageName = u'creationkit%s.png'     # Image name template for the status bar

#--Script Extender information
class se:
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
    canEditMasters = True       # Adjusting save file masters
    canEditMore = False         # No advanced editing
    ext = u'.fos'               # Save file extension

#--INI files that should show up in the INI Edits tab
iniFiles = [
    u'Fallout4.ini',
    u'Fallout4Prefs.ini',
    u'Fallout4Custom.ini',
    ]

#--INI setting to setup Save Profiles
saveProfilesKey = (u'General',u'SLocalSavePath')

#--The main plugin Wrye Bash should look for
masterFiles = [
    u'Fallout4.esm',
    ]

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
    u'tools', # bodyslide
    u'mcm',   # FO4 MCM
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
allTags = sorted((
    u'Delev', u'NoMerge', u'Relev',
    ))

#--Gui patcher classes available when building a Bashed Patch
patchers = (
    u'ListsMerger',
    )

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
    canBash = True          # Can create Bashed Patches
    canCBash = False        # CBash can handle this game's records
    canEditHeader = True    # Can edit anything in the TES4 record

    #--Valid ESM/ESP header versions
    validHeaderVersions = (0.95,)

    #--Strings Files
    stringsFiles = [
        ((u'Strings',), u'%(body)s_%(language)s.STRINGS'),
        ((u'Strings',), u'%(body)s_%(language)s.DLSTRINGS'),
        ((u'Strings',), u'%(body)s_%(language)s.ILSTRINGS'),
    ]

    #--Top types in Skyrim order.
    topTypes = ['GMST', 'KYWD', 'LCRT', 'AACT', 'TRNS', 'CMPO', 'TXST',
                'GLOB', 'DMGT', 'CLAS', 'FACT', 'HDPT', 'RACE', 'SOUN',
                'ASPC', 'MGEF', 'LTEX', 'ENCH', 'SPEL', 'ACTI', 'TACT',
                'ARMO', 'BOOK', 'CONT', 'DOOR', 'INGR', 'LIGH', 'MISC',
                'STAT', 'SCOL', 'MSTT', 'GRAS', 'TREE', 'FLOR', 'FURN',
                'WEAP', 'AMMO', 'NPC_', 'LVLN', 'KEYM', 'ALCH', 'IDLM',
                'NOTE', 'PROJ', 'HAZD', 'BNDS', 'TERM', 'GRAS', 'TREE',
                'FURN', 'WEAP', 'AMMO', 'NPC_', 'LVLN', 'KEYM', 'ALCH',
                'IDLM', 'NOTE', 'PROJ', 'HAZD', 'BNDS', 'LVLI', 'WTHR',
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

#------------------------------------------------------------------------------
# These Are normally not mergable but added to brec.MreRecord.type_class
#
#       MreCell,
#------------------------------------------------------------------------------
# These have undefined FormIDs Do not merge them
#
#       MreNavi, MreNavm,
#------------------------------------------------------------------------------
# These need syntax revision but can be merged once that is corrected
#
#       MreAchr, MreDial, MreLctn, MreInfo, MreFact, MrePerk,
#------------------------------------------------------------------------------
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
        MreLvli, MreLvln,
        ####### for debug
        MreHeader,
        ))

    #--Simple records
    brec.MreRecord.simpleTypes = (
        set(brec.MreRecord.type_class) - {'TES4',})
