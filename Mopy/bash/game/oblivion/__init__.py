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

"""This modules defines static data for use by bush, when
   TES IV: Oblivion is set at the active game."""

import struct
from .constants import *
from .default_tweaks import default_tweaks
from ... import brec
from .records import MreActi, MreAlch, MreAmmo, MreAnio, MreAppa, MreArmo, \
    MreBook, MreBsgn, MreClas, MreClot, MreCont, MreCrea, MreDoor, MreEfsh, \
    MreEnch, MreEyes, MreFact, MreFlor, MreFurn, MreGras, MreHair, MreIngr, \
    MreKeym, MreLigh, MreLscr, MreLvlc, MreLvli, MreLvsp, MreMgef, MreMisc, \
    MreNpc, MrePack, MreQust, MreRace, MreScpt, MreSgst, MreSlgm, MreSoun, \
    MreSpel, MreStat, MreTree, MreWatr, MreWeap, MreWthr, MreClmt, MreCsty, \
    MreIdle, MreLtex, MreRegn, MreSbsp, MreSkil, MreAchr, MreAcre, \
    MreCell, MreGmst, MreRefr, MreRoad, MreHeader, MreWrld, MreDial, MreInfo
from ...brec import MreGlob, BaseRecordHeader, ModError

#--Name of the game to use in UI.
displayName = u'Oblivion'
#--Name of the game's filesystem folder.
fsName = u'Oblivion'
#--Alternate display name to use instead of "Wrye Bash for ***"
altName = u'Wrye Bash'
#--Name of game's default ini file.
defaultIniFile = u'Oblivion_default.ini'

#--Exe to look for to see if this is the right game
exe = u'Oblivion.exe'

#--Registry keys to read to find the install location
regInstallKeys = (u'Bethesda Softworks\\Oblivion', u'Installed Path')

#--patch information
patchURL = u'http://www.elderscrolls.com/downloads/updates_patches.htm'
patchTip = u'http://www.elderscrolls.com/'

#--URL to the Nexus site for this game
nexusUrl = u'http://oblivion.nexusmods.com/'
nexusName = u'TES Nexus'
nexusKey = 'bash.installers.openTesNexus.continue'

# Bsa info
allow_reset_bsa_timestamps = True
bsa_extension = ur'bsa'

# Load order info
using_txt_file = False

#--Construction Set information
class cs:
    shortName = u'TESCS'            # Abbreviated name
    longName = u'Construction Set'  # Full name
    exe = u'TESConstructionSet.exe' # Executable to run
    seArgs = u'-editor'             # Argument to pass to the SE to load the CS
    imageName = u'tescs%s.png'      # Image name template for the status bar

#--Script Extender information
class se:
    shortName = u'OBSE'                      # Abbreviated name
    longName = u'Oblivion Script Extender'   # Full name
    exe = u'obse_loader.exe'                 # Exe to run
    steamExe = u'obse_1_2_416.dll'           # Exe to run if a steam install
    url = u'http://obse.silverlock.org/'     # URL to download from
    urlTip = u'http://obse.silverlock.org/'  # Tooltip for mouse over the URL

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
    shortName = u'OBGE'
    longName = u'Oblivion Graphics Extender'
    exe = [(u'Data',u'obse',u'plugins',u'obge.dll'),
           (u'Data',u'obse',u'plugins',u'obgev2.dll'),
           ]
    url = u'http://oblivion.nexusmods.com/mods/30054'
    urlTip = u'http://oblivion.nexusmods.com/'

#--4gb Launcher
class laa:
    name = u''           # Name
    exe = u'**DNE**'     # Executable to run
    launchesSE = False  # Whether the launcher will automatically launch the SE as well

# Files BAIN shouldn't skip
dontSkip = (
# Nothing so far
)

# Directories where specific file extensions should not be skipped by BAIN
dontSkipDirs = {
# Nothing so far
}

#Folders BAIN should never check
SkipBAINRefresh = {
    u'tes4edit backups',
    u'bgsee',
    u'conscribe logs',
    #Use lowercase names
}

#--Some stuff dealing with INI files
class ini:
    #--True means new lines are allowed to be added via INI Tweaks
    #  (by default)
    allowNewLines = False

    #--INI Entry to enable BSA Redirection
    bsaRedirection = (u'Archive',u'sArchiveList')

#--Save Game format stuff
class ess:
    # Save file capabilities
    canReadBasic = True         # All the basic stuff needed for the Saves Tab
    canEditMasters = True       # Adjusting save file masters
    canEditMore = True          # advanced editing
    ext = u'.ess'               # Save file extension

    @staticmethod
    def load(ins,header):
        """Extract info from save file."""
        #--Header
        if ins.read(12) != 'TES4SAVEGAME':
            raise Exception(u'Save file is not an Oblivion save game.')
        ins.seek(34)
        headerSize, = struct.unpack('I',ins.read(4))
        #--Name, location
        ins.seek(42)
        size, = struct.unpack('B',ins.read(1))
        header.pcName = ins.read(size)
        header.pcLevel, = struct.unpack('H',ins.read(2))
        size, = struct.unpack('B',ins.read(1))
        header.pcLocation = ins.read(size)
        #--Image Data
        (header.gameDays,header.gameTicks,header.gameTime,ssSize,ssWidth,
         ssHeight) = struct.unpack('=fI16s3I',ins.read(36))
        ssData = ins.read(3*ssWidth*ssHeight)
        header.image = (ssWidth,ssHeight,ssData)
        #--Masters
        del header.masters[:]
        numMasters, = struct.unpack('B',ins.read(1))
        for count in xrange(numMasters):
            size, = struct.unpack('B',ins.read(1))
            header.masters.append(ins.read(size))

    @staticmethod
    def writeMasters(ins,out,header):
        """Rewrites masters of existing save file."""
        def unpack(fmt, size): return struct.unpack(fmt, ins.read(size))
        def pack(fmt, *args): out.write(struct.pack(fmt, *args))
        #--Header
        out.write(ins.read(34))
        #--SaveGameHeader
        size, = unpack('I',4)
        pack('I',size)
        out.write(ins.read(size))
        #--Skip old masters
        numMasters, = unpack('B',1)
        oldMasters = []
        for count in xrange(numMasters):
            size, = unpack('B',1)
            oldMasters.append(ins.read(size))
        #--Write new masters
        pack('B',len(header.masters))
        for master in header.masters:
            pack('B',len(master))
            out.write(master.s)
        #--Fids Address
        offset = out.tell() - ins.tell()
        fidsAddress, = unpack('I',4)
        pack('I',fidsAddress+offset)
        #--Copy remainder
        while True:
            buff = ins.read(0x5000000)
            if not buff: break
            out.write(buff)
        return oldMasters

#--INI files that should show up in the INI Edits tab
iniFiles = [
    u'Oblivion.ini',
    ]

#--INI setting to setup Save Profiles
saveProfilesKey = (u'General',u'SLocalSavePath')

#--The main plugin Wrye Bash should look for
masterFiles = [
    u'Oblivion.esm',
    u'Nehrim.esm',
    ]

#The pickle file for this game. Holds encoded GMST IDs from the big list below.
pklfile = ur'bash\db\Oblivion_ids.pkl'

#--BAIN: Directories that are OK to install to
dataDirs = {
    u'distantlod',
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
    u'scripts',
    u'pluggy',
    u'ini',
    u'obse',
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
    u'Bashed Patch, FCOM.esp',
    u'Bashed Patch, Warrior.esp',
    u'Bashed Patch, Thief.esp',
    u'Bashed Patch, Mage.esp',
    u'Bashed Patch, Test.esp',
    u'ArchiveInvalidationInvalidated!.bsa',
    u'Docs\\Bash Readme Template.html',
    u'Docs\\wtxt_sand_small.css',
    u'Docs\\wtxt_teal.css',
    u'Docs\\Bash Readme Template.txt'
}
wryeBashDataDirs = {
    u'Bash Patches',
    u'INI Tweaks'
}
ignoreDataFiles = {
    u'OBSE\\Plugins\\Construction Set Extender.dll',
    u'OBSE\\Plugins\\Construction Set Extender.ini'
}
ignoreDataFilePrefixes = {
    u'Meshes\\Characters\\_Male\\specialanims\\0FemaleVariableWalk_'
}
ignoreDataDirs = {
    u'OBSE\\Plugins\\ComponentDLLs\\CSE',
    u'LSData'
}

#--Tags supported by this game
allTags = sorted((
    u'Body-F', u'Body-M', u'Body-Size-M', u'Body-Size-F', u'C.Climate',
    u'C.Light', u'C.Music', u'C.Name', u'C.RecordFlags', u'C.Owner',
    u'C.Water', u'Deactivate', u'Delev', u'Eyes', u'Factions', u'Relations',
    u'Filter', u'Graphics', u'Hair', u'IIM', u'Invent', u'Names', u'NoMerge',
    u'NpcFaces', u'R.Relations', u'Relev', u'Scripts', u'ScriptContents',
    u'Sound', u'SpellStats', u'Stats', u'Voice-F', u'Voice-M', u'R.Teeth',
    u'R.Mouth', u'R.Ears', u'R.Head', u'R.Attributes-F', u'R.Attributes-M',
    u'R.Skills', u'R.Description', u'R.AddSpells', u'R.ChangeSpells', u'Roads',
    u'Actors.Anims', u'Actors.AIData', u'Actors.DeathItem',
    u'Actors.AIPackages', u'Actors.AIPackagesForceAdd', u'Actors.Stats',
    u'Actors.ACBS', u'NPC.Class', u'Actors.CombatStyle', u'Creatures.Blood',
    u'Actors.Spells', u'Actors.SpellsForceAdd', u'NPC.Race',
    u'Actors.Skeleton', u'NpcFacesForceFullImport', u'MustBeActiveIfImported',
    u'Npc.HairOnly', u'Npc.EyesOnly')) ##, 'ForceMerge'

#--Gui patcher classes available when building a Bashed Patch
patchers = (
    'AliasesPatcher', 'AssortedTweaker', 'PatchMerger', 'AlchemicalCatalogs',
    'KFFZPatcher', 'ActorImporter', 'DeathItemPatcher', 'NPCAIPackagePatcher',
    'CoblExhaustion', 'UpdateReferences', 'CellImporter', 'ClothesTweaker',
    'GmstTweaker', 'GraphicsPatcher', 'ImportFactions', 'ImportInventory',
    'SpellsPatcher', 'TweakActors', 'ImportRelations', 'ImportScripts',
    'ImportActorsSpells', 'ListsMerger', 'MFactMarker', 'NamesPatcher',
    'NamesTweaker', 'NpcFacePatcher', 'RacePatcher', 'RoadImporter',
    'SoundPatcher', 'StatsPatcher', 'SEWorldEnforcer', 'ContentsChecker',
    )

#--CBash Gui patcher classes available when building a Bashed Patch
CBash_patchers = (
    'CBash_AliasesPatcher', 'CBash_AssortedTweaker', 'CBash_PatchMerger',
    'CBash_AlchemicalCatalogs', 'CBash_KFFZPatcher', 'CBash_ActorImporter',
    'CBash_DeathItemPatcher', 'CBash_NPCAIPackagePatcher',
    'CBash_CoblExhaustion', 'CBash_UpdateReferences', 'CBash_CellImporter',
    'CBash_ClothesTweaker', 'CBash_GmstTweaker', 'CBash_GraphicsPatcher',
    'CBash_ImportFactions', 'CBash_ImportInventory', 'CBash_SpellsPatcher',
    'CBash_TweakActors', 'CBash_ImportRelations', 'CBash_ImportScripts',
    'CBash_ImportActorsSpells', 'CBash_ListsMerger', 'CBash_MFactMarker',
    'CBash_NamesPatcher', 'CBash_NamesTweaker', 'CBash_NpcFacePatcher',
    'CBash_RacePatcher', 'CBash_RoadImporter', 'CBash_SoundPatcher',
    'CBash_StatsPatcher', 'CBash_SEWorldEnforcer', 'CBash_ContentsChecker',
    )

# Magic Info ------------------------------------------------------------------
weaponTypes = (
    _(u'Blade (1 Handed)'),
    _(u'Blade (2 Handed)'),
    _(u'Blunt (1 Handed)'),
    _(u'Blunt (2 Handed)'),
    _(u'Staff'),
    _(u'Bow'),
    )

# Race Info -------------------------------------------------------------------
raceNames = {
    0x23fe9 : _(u'Argonian'),
    0x224fc : _(u'Breton'),
    0x191c1 : _(u'Dark Elf'),
    0x19204 : _(u'High Elf'),
    0x00907 : _(u'Imperial'),
    0x22c37 : _(u'Khajiit'),
    0x224fd : _(u'Nord'),
    0x191c0 : _(u'Orc'),
    0x00d43 : _(u'Redguard'),
    0x00019 : _(u'Vampire'),
    0x223c8 : _(u'Wood Elf'),
    }

raceShortNames = {
    0x23fe9 : u'Arg',
    0x224fc : u'Bre',
    0x191c1 : u'Dun',
    0x19204 : u'Alt',
    0x00907 : u'Imp',
    0x22c37 : u'Kha',
    0x224fd : u'Nor',
    0x191c0 : u'Orc',
    0x00d43 : u'Red',
    0x223c8 : u'Bos',
    }

raceHairMale = {
    0x23fe9 : 0x64f32, #--Arg
    0x224fc : 0x90475, #--Bre
    0x191c1 : 0x64214, #--Dun
    0x19204 : 0x7b792, #--Alt
    0x00907 : 0x90475, #--Imp
    0x22c37 : 0x653d4, #--Kha
    0x224fd : 0x1da82, #--Nor
    0x191c0 : 0x66a27, #--Orc
    0x00d43 : 0x64215, #--Red
    0x223c8 : 0x690bc, #--Bos
    }

raceHairFemale = {
    0x23fe9 : 0x64f33, #--Arg
    0x224fc : 0x1da83, #--Bre
    0x191c1 : 0x1da83, #--Dun
    0x19204 : 0x690c2, #--Alt
    0x00907 : 0x1da83, #--Imp
    0x22c37 : 0x653d0, #--Kha
    0x224fd : 0x1da83, #--Nor
    0x191c0 : 0x64218, #--Orc
    0x00d43 : 0x64210, #--Red
    0x223c8 : 0x69473, #--Bos
    }

#--Plugin format stuff
class esp:
    #--Wrye Bash capabilities
    canBash = True          # Can create Bashed Patches
    canCBash = True         # CBash can handle this game's records
    canEditHeader = True    # Can edit anything in the TES4 record

    #--Valid ESM/ESP header versions
    validHeaderVersions = (0.8,1.0)

    stringsFiles = []

    #--Top types in Oblivion order.
    topTypes = ['GMST', 'GLOB', 'CLAS', 'FACT', 'HAIR', 'EYES', 'RACE', 'SOUN',
                'SKIL', 'MGEF', 'SCPT', 'LTEX', 'ENCH', 'SPEL', 'BSGN', 'ACTI',
                'APPA', 'ARMO', 'BOOK', 'CLOT', 'CONT', 'DOOR', 'INGR', 'LIGH',
                'MISC', 'STAT', 'GRAS', 'TREE', 'FLOR', 'FURN', 'WEAP', 'AMMO',
                'NPC_', 'CREA', 'LVLC', 'SLGM', 'KEYM', 'ALCH', 'SBSP', 'SGST',
                'LVLI', 'WTHR', 'CLMT', 'REGN', 'CELL', 'WRLD', 'DIAL', 'QUST',
                'IDLE', 'PACK', 'CSTY', 'LSCR', 'LVSP', 'ANIO', 'WATR', 'EFSH']

    #--Dict mapping 'ignored' top types to un-ignored top types.
    topIgTypes = dict(
        [(struct.pack('I', (struct.unpack('I', type)[0]) | 0x1000), type) for
         type in topTypes])

    recordTypes = set(
        topTypes + 'GRUP,TES4,ROAD,REFR,ACHR,ACRE,PGRD,LAND,INFO'.split(','))

#--Mod I/O
class RecordHeader(BaseRecordHeader):
    size = 20

    def __init__(self,recType='TES4',size=0,arg1=0,arg2=0,arg3=0,*extra):
        self.recType = recType
        self.size = size
        if recType == 'GRUP':
            self.label = arg1
            self.groupType = arg2
            self.stamp = arg3
        else:
            self.flags1 = arg1
            self.fid = arg2
            self.flags2 = arg2
        self.extra = extra

    @staticmethod
    def unpack(ins):
        """Returns a RecordHeader object by reading the input stream."""
        rec_type,size,uint0,uint1,uint2 = ins.unpack('=4s4I',20,'REC_HEADER')
        #--Bad?
        if rec_type not in esp.recordTypes:
            raise ModError(ins.inName,u'Bad header type: '+repr(rec_type))
        #--Record
        if rec_type != 'GRUP':
            pass
        #--Top Group
        elif uint1 == 0: # groupType == 0 (Top Group)
            str0 = struct.pack('I',uint0)
            if str0 in esp.topTypes:
                uint0 = str0
            elif str0 in esp.topIgTypes:
                uint0 = esp.topIgTypes[str0]
            else:
                raise ModError(ins.inName,u'Bad Top GRUP type: '+repr(str0))
        return RecordHeader(rec_type,size,uint0,uint1,uint2)

    def pack(self):
        """Returns the record header packed into a string for writing to
        file."""
        if self.recType == 'GRUP':
            if isinstance(self.label, str):
                return struct.pack('=4sI4sII', self.recType, self.size,
                                   self.label, self.groupType, self.stamp)
            elif isinstance(self.label, tuple):
                return struct.pack('=4sIhhII', self.recType, self.size,
                                   self.label[0], self.label[1],
                                   self.groupType, self.stamp)
            else:
                return struct.pack('=4s4I', self.recType, self.size,
                                   self.label, self.groupType, self.stamp)
        else:
            return struct.pack('=4s4I', self.recType, self.size, self.flags1,
                               self.fid, self.flags2)

#------------------------------------------------------------------------------
#--Mergeable record types
mergeClasses = (
    MreActi, MreAlch, MreAmmo, MreAnio, MreAppa, MreArmo, MreBook, MreBsgn,
    MreClas, MreClot, MreCont, MreCrea, MreDoor, MreEfsh, MreEnch, MreEyes,
    MreFact, MreFlor, MreFurn, MreGlob, MreGras, MreHair, MreIngr, MreKeym,
    MreLigh, MreLscr, MreLvlc, MreLvli, MreLvsp, MreMgef, MreMisc, MreNpc,
    MrePack, MreQust, MreRace, MreScpt, MreSgst, MreSlgm, MreSoun, MreSpel,
    MreStat, MreTree, MreWatr, MreWeap, MreWthr, MreClmt, MreCsty, MreIdle,
    MreLtex, MreRegn, MreSbsp, MreSkil,
    )

#--Extra read classes: need info from magic effects
readClasses = (MreMgef, MreScpt,)
writeClasses = (MreMgef,)


def init():
    # Due to a bug with py2exe, 'reload' doesn't function properly.  Instead of
    # re-executing all lines within the module, it acts like another 'import'
    # statement - in otherwords, nothing happens.  This means any lines that
    # affect outside modules must do so within this function, which will be
    # called instead of 'reload'
    brec.ModReader.recHeader = RecordHeader

    #--Record Types
    brec.MreRecord.type_class = dict((x.classType,x) for x in (
        MreAchr, MreAcre, MreActi, MreAlch, MreAmmo, MreAnio, MreAppa, MreArmo,
        MreBook, MreBsgn, MreCell, MreClas, MreClot, MreCont, MreCrea, MreDoor,
        MreEfsh, MreEnch, MreEyes, MreFact, MreFlor, MreFurn, MreGlob, MreGmst,
        MreGras, MreHair, MreIngr, MreKeym, MreLigh, MreLscr, MreLvlc, MreLvli,
        MreLvsp, MreMgef, MreMisc, MreNpc, MrePack, MreQust, MreRace, MreRefr,
        MreRoad, MreScpt, MreSgst, MreSkil, MreSlgm, MreSoun, MreSpel, MreStat,
        MreTree, MreHeader, MreWatr, MreWeap, MreWrld, MreWthr, MreClmt,
        MreCsty, MreIdle, MreLtex, MreRegn, MreSbsp, MreDial, MreInfo,
        ))

    #--Simple records
    brec.MreRecord.simpleTypes = (
        set(brec.MreRecord.type_class) - {'TES4', 'ACHR', 'ACRE', 'REFR',
                                          'CELL', 'PGRD', 'ROAD', 'LAND',
                                          'WRLD', 'INFO', 'DIAL'})
