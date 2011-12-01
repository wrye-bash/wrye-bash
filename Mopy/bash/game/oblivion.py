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
   TES IV: Oblivion is set at the active game."""

import struct

#--Name of the game
name = 'Oblivion'
#--Alternate display name to use instead of "Wrye Bash for ***"
altName = 'Wrye Bash'

#--Exe to look for to see if this is the right game
exe = 'Oblivion.exe'

#--Registry keys to read to find the install location
regInstallKeys = [
    ('Bethesda Softworks\Oblivion','Installed Path'),
    ]

#--patch information
patchURL = 'http://www.elderscrolls.com/downloads/updates_patches.htm'
patchTip = 'http://www.elderscrolls.com/'

#--Construction Set information
class cs:
    shortName = 'TESCS'             # Abbreviated name
    longName = 'Construction Set'   # Full name
    exe = 'TESConstructionSet.exe'  # Executable to run
    seArgs = '-editor'              # Argument to pass to the SE to load the CS
    imageName = 'tescs%s.png'       # Image name template for the status bar

#--Script Extender information
class se:
    shortName = 'OBSE'                      # Abbreviated name
    longName = 'Oblivion Script Extender'   # Full name
    exe = 'obse_loader.exe'                 # Exe to run
    steamExe = 'obse_1_2_416.dll'           # Exe to run if a steam install
    url = 'http://obse.silverlock.org/'     # URL to download from
    urlTip = 'http://obse.silverlock.org/'  # Tooltip for mouse over the URL

#--Graphics Extender information
class ge:
    shortName = 'OBGE'
    longName = 'Oblivion Graphics Extender'
    exe = [('Data','obse','plugins','obge.dll'),
           ('Data','obse','plugins','obgev2.dll'),
           ]
    url = 'http://www.tesnexus.com/downloads/file.php?id=30054'
    urlTip = 'http://www.tesnexus.com/'

#--4gb Launcher
class laa:
    name = ''           # Name
    exe = '**DNE**'     # Executable to run
    launchesSE = False  # Whether the launcher will automatically launch the SE as well

#--Save Game format stuff
class ess:
    # Save file capabilities
    canReadBasic = True         # All the basic stuff needed for the Saves Tab
    canEditMasters = True       # Adjusting save file masters
    canEditMore = True          # advanced editing

    @staticmethod
    def load(ins,header):
        """Extract info from save file."""
        #--Header
        if ins.read(12) != 'TES4SAVEGAME':
            raise Exception('Save file is not an Oblivion save game.')
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
        """Rewrites mastesr of existing save file."""
        def unpack(format,size): return struct.unpack(format,ins.read(size))
        def pack(format,*args): out.write(struct.pack(format,*args))
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
            buffer = ins.read(0x5000000)
            if not buffer: break
            out.write(buffer)
        return oldMasters

#--The main plugin Wrye Bash should look for
masterFiles = [
    r'Oblivion.esm',
    r'Nehrim.esm',
    ]

#--INI files that should show up in the INI Edits tab
iniFiles = [
    r'Oblivion.ini',
    ]

#--INI setting to setup Save Profiles
saveProfilesKey = ('General','SLocalSavePath')

#--Game ESM/ESP/BSA files
bethDataFiles = set((
    #--Vanilla
    r'oblivion.esm',
    r'oblivion_1.1.esm',
    r'oblivion_si.esm',
    r'oblivion_1.1.esm.ghost',
    r'oblivion_si.esm.ghost',
    r'oblivion - meshes.bsa',
    r'oblivion - misc.bsa',
    r'oblivion - sounds.bsa',
    r'oblivion - textures - compressed.bsa',
    r'oblivion - textures - compressed.bsa.orig',
    r'oblivion - voices1.bsa',
    r'oblivion - voices2.bsa',
    #--Shivering Isles
    r'dlcshiveringisles.esp',
    r'dlcshiveringisles - meshes.bsa',
    r'dlcshiveringisles - sounds.bsa',
    r'dlcshiveringisles - textures.bsa',
    r'dlcshiveringisles - voices.bsa',
    ))

#--Every file in the Data directory from Bethsoft
allBethFiles = set((
    #vanilla
    r'Credits.txt',
    r'Oblivion - Meshes.bsa',
    r'Oblivion - Misc.bsa',
    r'Oblivion - Sounds.bsa',
    r'Oblivion - Textures - Compressed.bsa',
    r'Oblivion - Voices1.bsa',
    r'Oblivion - Voices2.bsa',
    r'Oblivion.esm',
    r'Music\Battle\battle_01.mp3',
    r'Music\Battle\battle_02.mp3',
    r'Music\Battle\battle_03.mp3',
    r'Music\Battle\battle_04.mp3',
    r'Music\Battle\battle_05.mp3',
    r'Music\Battle\battle_06.mp3',
    r'Music\Battle\battle_07.mp3',
    r'Music\Battle\battle_08.mp3',
    r'Music\Dungeon\Dungeon_01_v2.mp3',
    r'Music\Dungeon\dungeon_02.mp3',
    r'Music\Dungeon\dungeon_03.mp3',
    r'Music\Dungeon\dungeon_04.mp3',
    r'Music\Dungeon\dungeon_05.mp3',
    r'Music\Explore\atmosphere_01.mp3',
    r'Music\Explore\atmosphere_03.mp3',
    r'Music\Explore\atmosphere_04.mp3',
    r'Music\Explore\atmosphere_06.mp3',
    r'Music\Explore\atmosphere_07.mp3',
    r'Music\Explore\atmosphere_08.mp3',
    r'Music\Explore\atmosphere_09.mp3',
    r'Music\Public\town_01.mp3',
    r'Music\Public\town_02.mp3',
    r'Music\Public\town_03.mp3',
    r'Music\Public\town_04.mp3',
    r'Music\Public\town_05.mp3',
    r'Music\Special\death.mp3',
    r'Music\Special\success.mp3',
    r'Music\Special\tes4title.mp3',
    r'Shaders\shaderpackage001.sdp',
    r'Shaders\shaderpackage002.sdp',
    r'Shaders\shaderpackage003.sdp',
    r'Shaders\shaderpackage004.sdp',
    r'Shaders\shaderpackage005.sdp',
    r'Shaders\shaderpackage006.sdp',
    r'Shaders\shaderpackage007.sdp',
    r'Shaders\shaderpackage008.sdp',
    r'Shaders\shaderpackage009.sdp',
    r'Shaders\shaderpackage010.sdp',
    r'Shaders\shaderpackage011.sdp',
    r'Shaders\shaderpackage012.sdp',
    r'Shaders\shaderpackage013.sdp',
    r'Shaders\shaderpackage014.sdp',
    r'Shaders\shaderpackage015.sdp',
    r'Shaders\shaderpackage016.sdp',
    r'Shaders\shaderpackage017.sdp',
    r'Shaders\shaderpackage018.sdp',
    r'Shaders\shaderpackage019.sdp',
    r'Video\2k games.bik',
    r'Video\bethesda softworks HD720p.bik',
    r'Video\CreditsMenu.bik',
    r'Video\game studios.bik',
    r'Video\Map loop.bik',
    r'Video\Oblivion iv logo.bik',
    r'Video\Oblivion Legal.bik',
    r'Video\OblivionIntro.bik',
    r'Video\OblivionOutro.bik',
    #SI
    r'DLCShiveringIsles - Meshes.bsa',
    r'DLCShiveringIsles - Textures.bsa',
    r'DLCShiveringIsles - Sounds.bsa',
    r'DLCShiveringIsles - Voices.bsa',
    r'DLCShiveringIsles.esp',
    r'Textures\Effects\TerrainNoise.dds',
    #DLCs
    r'DLCBattlehornCastle.bsa',
    r'DLCBattlehornCastle.esp',
    r'DLCFrostcrag.bsa',
    r'DLCFrostcrag.esp',
    r'DLCHorseArmor.bsa',
    r'DLCHorseArmor.esp',
    r'DLCMehrunesRazor.esp',
    r'DLCOrrery.bsa',
    r'DLCOrrery.esp',
    r'DLCSpellTomes.esp',
    r'DLCThievesDen.bsa',
    r'DLCThievesDen.esp',
    r'DLCVileLair.bsa',
    r'DLCVileLair.esp',
    r'Knights.bsa',
    r'Knights.esp',
    r'DLCList.txt',
    ))

#--BAIN: Directories that are OK to install to
dataDirs = set(('bash patches','distantlod','docs','facegen','fonts',
    'menus','meshes','music','shaders','sound', 'textures', 'trees','video'))
dataDirsPlus = set(('streamline','_tejon','ini tweaks','scripts','pluggy','ini','obse'))

#--Plugin format stuff
class esp:
    #--Wrye Bash capabilities
    canBash = True          # Can create Bashed Patches
    canEditHeader = True    # Can edit anything in the TES4 record

    #--Valid ESM/ESP header versions
    validHeaderVersions = (0.8,1.0)

    #--Class to use to read the TES4 record
    tes4ClassName = 'MreTes4'

    #--Information on the ESP/ESM header format
    class header:   
        format = '4s4I'
        size = 20
        attrs = ('recType','size','flags1','fid','flags2')
        defaults = ('TES4',0,0,0,0)

    #--Top types in Oblivion order.
    topTypes = ['GMST', 'GLOB', 'CLAS', 'FACT', 'HAIR', 'EYES', 'RACE', 'SOUN', 'SKIL',
        'MGEF', 'SCPT', 'LTEX', 'ENCH', 'SPEL', 'BSGN', 'ACTI', 'APPA', 'ARMO', 'BOOK',
        'CLOT', 'CONT', 'DOOR', 'INGR', 'LIGH', 'MISC', 'STAT', 'GRAS', 'TREE', 'FLOR',
        'FURN', 'WEAP', 'AMMO', 'NPC_', 'CREA', 'LVLC', 'SLGM', 'KEYM', 'ALCH', 'SBSP',
        'SGST', 'LVLI', 'WTHR', 'CLMT', 'REGN', 'CELL', 'WRLD', 'DIAL', 'QUST', 'IDLE',
        'PACK', 'CSTY', 'LSCR', 'LVSP', 'ANIO', 'WATR', 'EFSH']

    #--Dict mapping 'ignored' top types to un-ignored top types.
    topIgTypes = dict([(struct.pack('I',(struct.unpack('I',type)[0]) | 0x1000),type) for type in topTypes])

    recordTypes = set(topTypes + 'GRUP,TES4,ROAD,REFR,ACHR,ACRE,PGRD,LAND,INFO'.split(','))