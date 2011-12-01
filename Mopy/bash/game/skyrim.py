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

#--Name of the game
name = 'Skyrim'
altName = 'Wrye Smash'

#--exe to look for to see if this is the right game
exe = 'TESV.exe'

#--Registry keys to read to find the install location
regInstallKeys = [
    ('Bethesda Softworks\Skyrim','Installed Path'),
    ]

#--patch information
patchURL = '' # Update via steam
patchTip = 'Update via Steam'

#--Creation Kit Set information
class cs:
    shortName = 'CK'                # Abbreviated name
    longName = 'Creation Kit'       # Full name
    exe = 'CreationKit.exe'         # Executable to run
    seArgs = '-editor'              # Argument to pass to the SE to load the CS
    imageName = 'tescs%s.png'       # Image name template for the status bar

#--Script Extender information
class se:
    shortName = 'SKSE'                      # Abbreviated name
    longName = 'Skyrim Script Extender'     # Full name
    exe = 'skse_loader.exe'                 # Exe to run
    steamExe = 'skse_loader.exe'            # Exe to run if a steam install
    url = 'http://skse.silverlock.org/'     # URL to download from
    urlTip = 'http://skse.silverlock.org/'  # Tooltip for mouse over the URL

#--Graphics Extender information
class ge:
    shortName = ''
    longName = ''
    exe = ''
    url = ''
    urlTip = ''

#--4gb Launcher
class laa:
    name = '4GB Launcher'           # Name
    exe = 'skyrim4gb.exe'           # Executable to run
    launchesSE = True               # Whether the launcher will automatically launch the SE as well

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
            raise Exception('Save file is not a Skyrim save game.')
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
            raise Exception('Save game header size (%s) not as expected (%s).' % (ins.tell()-17,headerSize))
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
            raise Exception('Save game masters size (%i) not as expected (%i).' % (ins.tell()-mastersStart,mastersSize))

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
    r'Skyrim.ini',
    r'SkyrimPrefs.ini',
    ]

#--INI setting to setup Save Profiles
saveProfilesKey = ('General','SLocalSavePath')

#--The main plugin file Wrye Bash should look for
masterFiles = [
    r'Skyrim.esm',
    ]

#--Game ESM/ESP/BSA files
bethDataFiles = set((
    #--Vanilla
    r'skyrim.esm',
    r'update.esm',
    r'skyrim - animations.bsa',
    r'skyrim - interface.bsa',
    r'skyrim - meshes.bsa',
    r'skyrim - misc.bsa',
    r'skyrim - shaders.bsa',
    r'skyrim - sounds.bsa',
    r'skyrim - textures.bsa',
    r'skyrim - voices.bsa',
    r'skyrim - voicesextra.bsa',
    ))

#--Every file in the Data directory from Bethsoft
allBethFiles = set((
    #--Vanilla
    r'skyrim.esm',
    r'update.esm',
    r'skyrim - animations.bsa',
    r'skyrim - interface.bsa',
    r'skyrim - meshes.bsa',
    r'skyrim - misc.bsa',
    r'skyrim - shaders.bsa',
    r'skyrim - sounds.bsa',
    r'skyrim - textures.bsa',
    r'skyrim - voices.bsa',
    r'skyrim - voicesextra.bsa',
    r'interface\translate_english.txt', #--probably need one for each language
    r'strings\skyrim_english.dlstrings', #--same here
    r'strings\skyrim_english.ilstrings',
    r'strings\skryim_english.strings',
    r'strings\update_english.dlstrings',
    r'strings\update_english.ilstrings',
    r'strings\update_english.strings',
    r'video\bgs_logo.bik',
    ))

#--BAIN: Directories that are OK to install to
dataDirs = set(('bash patches','interface','meshes','strings','textures',
    'video','lodsettings','grass','scripts','shadersfx','music','sound',))
dataDirsPlus = set(('ini tweaks','skse','ini'))

#--List of GMST's in the main plugin (Oblivion.esm) that have 0x00000000
#  as the form id.  Any GMST as such needs it Editor Id listed here.
gmstEids = [
    # None
    ]

#--Patchers available when building a Bashed Patch
patchers = (
    'AliasesPatcher', 'PatchMerger',
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

    #--Class to use to read the TES4 record
    tes4ClassName = 'MreTes5'

    #--Information on the ESP/ESM header format
    class header:
        format = '=4s5I'
        formatTopGrup = '=4sI4sIII'
        formatTupleGrup = '=4sIhhIII'
        size = 24
        attrs = ('recType','size','flags1','fid','flags2','unk')
        defaults = ('TES4',0,0,0,0,0)

    #--Extra read/write classes
    readClasses = tuple()
    writeClasses = tuple()

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

    #--class names for mergeable records
    mergeClasses = ('MreGlob','MreGmst',)