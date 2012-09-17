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
name = u'Oblivion'
#--Alternate display name to use instead of "Wrye Bash for ***"
altName = u'Wrye Bash'

#--Exe to look for to see if this is the right game
exe = u'Oblivion.exe'

#--Registry keys to read to find the install location
regInstallKeys = [
    (u'Bethesda Softworks\\Oblivion',u'Installed Path'),
    ]

#--patch information
patchURL = u'http://www.elderscrolls.com/downloads/updates_patches.htm'
patchTip = u'http://www.elderscrolls.com/'

#--Construction Set information
class cs:
    shortName = u'TESCS'             # Abbreviated name
    longName = u'Construction Set'   # Full name
    exe = u'TESConstructionSet.exe'  # Executable to run
    seArgs = u'-editor'              # Argument to pass to the SE to load the CS
    imageName = u'tescs%s.png'       # Image name template for the status bar

#--Script Extender information
class se:
    shortName = u'OBSE'                      # Abbreviated name
    longName = u'Oblivion Script Extender'   # Full name
    exe = u'obse_loader.exe'                 # Exe to run
    steamExe = u'obse_1_2_416.dll'           # Exe to run if a steam install
    url = u'http://obse.silverlock.org/'     # URL to download from
    urlTip = u'http://obse.silverlock.org/'  # Tooltip for mouse over the URL

#--Graphics Extender information
class ge:
    shortName = u'OBGE'
    longName = u'Oblivion Graphics Extender'
    exe = [(u'Data',u'obse',u'plugins',u'obge.dll'),
           (u'Data',u'obse',u'plugins',u'obgev2.dll'),
           ]
    url = u'http://www.tesnexus.com/downloads/file.php?id=30054'
    urlTip = u'http://www.tesnexus.com/'

#--4gb Launcher
class laa:
    name = u''           # Name
    exe = u'**DNE**'     # Executable to run
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
    u'Oblivion.esm',
    u'Nehrim.esm',
    ]

#--INI files that should show up in the INI Edits tab
iniFiles = [
    u'Oblivion.ini',
    ]

#--INI setting to setup Save Profiles
saveProfilesKey = (u'General',u'SLocalSavePath')

#--Game ESM/ESP/BSA files
bethDataFiles = set((
    #--Vanilla
    u'oblivion.esm',
    u'oblivion_1.1.esm',
    u'oblivion_si.esm',
    u'oblivion_1.1.esm.ghost',
    u'oblivion_si.esm.ghost',
    u'oblivion - meshes.bsa',
    u'oblivion - misc.bsa',
    u'oblivion - sounds.bsa',
    u'oblivion - textures - compressed.bsa',
    u'oblivion - textures - compressed.bsa.orig',
    u'oblivion - voices1.bsa',
    u'oblivion - voices2.bsa',
    #--Shivering Isles
    u'dlcshiveringisles.esp',
    u'dlcshiveringisles - meshes.bsa',
    u'dlcshiveringisles - sounds.bsa',
    u'dlcshiveringisles - textures.bsa',
    u'dlcshiveringisles - voices.bsa',
    ))

#--Every file in the Data directory from Bethsoft
allBethFiles = set((
    #vanilla
    u'Credits.txt',
    u'Oblivion - Meshes.bsa',
    u'Oblivion - Misc.bsa',
    u'Oblivion - Sounds.bsa',
    u'Oblivion - Textures - Compressed.bsa',
    u'Oblivion - Voices1.bsa',
    u'Oblivion - Voices2.bsa',
    u'Oblivion.esm',
    u'Music\\Battle\\battle_01.mp3',
    u'Music\\Battle\\battle_02.mp3',
    u'Music\\Battle\\battle_03.mp3',
    u'Music\\Battle\\battle_04.mp3',
    u'Music\\Battle\\battle_05.mp3',
    u'Music\\Battle\\battle_06.mp3',
    u'Music\\Battle\\battle_07.mp3',
    u'Music\\Battle\\battle_08.mp3',
    u'Music\\Dungeon\\Dungeon_01_v2.mp3',
    u'Music\\Dungeon\\dungeon_02.mp3',
    u'Music\\Dungeon\\dungeon_03.mp3',
    u'Music\\Dungeon\\dungeon_04.mp3',
    u'Music\\Dungeon\\dungeon_05.mp3',
    u'Music\\Explore\\atmosphere_01.mp3',
    u'Music\\Explore\\atmosphere_03.mp3',
    u'Music\\Explore\\atmosphere_04.mp3',
    u'Music\\Explore\\atmosphere_06.mp3',
    u'Music\\Explore\\atmosphere_07.mp3',
    u'Music\\Explore\\atmosphere_08.mp3',
    u'Music\\Explore\\atmosphere_09.mp3',
    u'Music\\Public\\town_01.mp3',
    u'Music\\Public\\town_02.mp3',
    u'Music\\Public\\town_03.mp3',
    u'Music\\Public\\town_04.mp3',
    u'Music\\Public\\town_05.mp3',
    u'Music\\Special\\death.mp3',
    u'Music\\Special\\success.mp3',
    u'Music\\Special\\tes4title.mp3',
    u'Shaders\\shaderpackage001.sdp',
    u'Shaders\\shaderpackage002.sdp',
    u'Shaders\\shaderpackage003.sdp',
    u'Shaders\\shaderpackage004.sdp',
    u'Shaders\\shaderpackage005.sdp',
    u'Shaders\\shaderpackage006.sdp',
    u'Shaders\\shaderpackage007.sdp',
    u'Shaders\\shaderpackage008.sdp',
    u'Shaders\\shaderpackage009.sdp',
    u'Shaders\\shaderpackage010.sdp',
    u'Shaders\\shaderpackage011.sdp',
    u'Shaders\\shaderpackage012.sdp',
    u'Shaders\\shaderpackage013.sdp',
    u'Shaders\\shaderpackage014.sdp',
    u'Shaders\\shaderpackage015.sdp',
    u'Shaders\\shaderpackage016.sdp',
    u'Shaders\\shaderpackage017.sdp',
    u'Shaders\\shaderpackage018.sdp',
    u'Shaders\\shaderpackage019.sdp',
    u'Video\\2k games.bik',
    u'Video\\bethesda softworks HD720p.bik',
    u'Video\\CreditsMenu.bik',
    u'Video\\game studios.bik',
    u'Video\\Map loop.bik',
    u'Video\\Oblivion iv logo.bik',
    u'Video\\Oblivion Legal.bik',
    u'Video\\OblivionIntro.bik',
    u'Video\\OblivionOutro.bik',
    #SI
    u'DLCShiveringIsles - Meshes.bsa',
    u'DLCShiveringIsles - Textures.bsa',
    u'DLCShiveringIsles - Sounds.bsa',
    u'DLCShiveringIsles - Voices.bsa',
    u'DLCShiveringIsles.esp',
    u'Textures\\Effects\\TerrainNoise.dds',
    #DLCs
    u'DLCBattlehornCastle.bsa',
    u'DLCBattlehornCastle.esp',
    u'DLCFrostcrag.bsa',
    u'DLCFrostcrag.esp',
    u'DLCHorseArmor.bsa',
    u'DLCHorseArmor.esp',
    u'DLCMehrunesRazor.esp',
    u'DLCOrrery.bsa',
    u'DLCOrrery.esp',
    u'DLCSpellTomes.esp',
    u'DLCThievesDen.bsa',
    u'DLCThievesDen.esp',
    u'DLCVileLair.bsa',
    u'DLCVileLair.esp',
    u'Knights.bsa',
    u'Knights.esp',
    u'DLCList.txt',
    ))

#--BAIN: Directories that are OK to install to
dataDirs = set((
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
    u'video'))
dataDirsPlus = set((
    u'streamline',
    u'_tejon',
    u'ini tweaks',
    u'scripts',
    u'pluggy',
    u'ini',
    u'obse'))

#--List of GMST's in the main plugin (Oblivion.esm) that have 0x00000000
#  as the form id.  Any GMST as such needs it Editor Id listed here.
gmstEids = ['iTrainingSkills','fRepairCostMult','fCrimeGoldSteal',
    'iAllowAlchemyDuringCombat','iNumberActorsAllowedToFollowPlayer',
    'iAllowRepairDuringCombat','iMaxPlayerSummonedCreatures',
    'iAICombatMaxAllySummonCount','iAINumberActorsComplexScene',
    'fHostileActorExteriorDistance','fHostileActorInteriorDistance',
    'iVampirismAgeOffset','iRemoveExcessDeadCount',
    'iRemoveExcessDeadTotalActorCount',
    'iRemoveExcessDeadComplexTotalActorCount','iRemoveExcessDeadComplexCount',
    'fRemoveExcessDeadTime','fRemoveExcessComplexDeadTime',
    'iInventoryAskQuantityAt','iCrimeGoldPickpocket','iCrimeGoldTresspass',
    'sBloodTextureDefault','sBloodTextureExtra1','sBloodTextureExtra2',
    'sBloodParticleDefault','sBloodParticleExtra1','sBloodParticleExtra2',
    'iAllyHitAllowed','sAutoSaving','sFloraFailureMessage',
    'sFloraSuccessMessage','sQuickSaving','sFastTravelHorseatGate',
    'sLoadingArea','sQuickLoading','sNoCharge',
    'fAISocialchanceForConversationInterior',
    ]

#--Patchers available when building a Bashed Patch
patchers = (
    'AliasesPatcher', 'AssortedTweaker', 'PatchMerger', 'AlchemicalCatalogs',
    'KFFZPatcher', 'ActorImporter', 'DeathItemPatcher', 'NPCAIPackagePatcher',
    'CoblExhaustion', 'UpdateReferences', 'CellImporter', 'ClothesTweaker',
    'GlobalsTweaker', 'GmstTweaker', 'GraphicsPatcher', 'ImportFactions',
    'ImportInventory', 'SpellsPatcher', 'TweakActors', 'ImportRelations',
    'ImportScripts', 'ImportScriptContents', 'ImportActorsSpells',
    'ListsMerger', 'MFactMarker', 'NamesPatcher', 'NamesTweaker',
    'NpcFacePatcher', 'PowerExhaustion', 'RacePatcher', 'RoadImporter',
    'SoundPatcher', 'StatsPatcher', 'SEWorldEnforcer', 'ContentsChecker',
    )

#--CBash patchers available when building a Bashed Patch
CBash_patchers = (
    'CBash_AliasesPatcher', 'CBash_AssortedTweaker', 'CBash_PatchMerger',
    'CBash_AlchemicalCatalogs', 'CBash_KFFZPatcher', 'CBash_ActorImporter',
    'CBash_DeathItemPatcher', 'CBash_NPCAIPackagePatcher',
    'CBash_CoblExhaustion', 'CBash_UpdateReferences', 'CBash_CellImporter',
    'CBash_ClothesTweaker', 'CBash_GlobalsTweaker', 'CBash_GmstTweaker',
    'CBash_GraphicsPatcher', 'CBash_ImportFactions', 'CBash_ImportInventory',
    'CBash_SpellsPatcher', 'CBash_TweakActors', 'CBash_ImportRelations',
    'CBash_ImportScripts',
    ##    CBash_ImportScriptContents(),
    'CBash_ImportActorsSpells', 'CBash_ListsMerger', 'CBash_MFactMarker',
    'CBash_NamesPatcher', 'CBash_NamesTweaker', 'CBash_NpcFacePatcher',
    'CBash_PowerExhaustion', 'CBash_RacePatcher', 'CBash_RoadImporter',
    'CBash_SoundPatcher', 'CBash_StatsPatcher', 'CBash_SEWorldEnforcer',
    'CBash_ContentsChecker',
    ##    CBash_ForceMerger(),
    )

#--Plugin format stuff
class esp:
    #--Wrye Bash capabilities
    canBash = True          # Can create Bashed Patches
    canCBash = True         # CBash can handle this game's records
    canEditHeader = True    # Can edit anything in the TES4 record

    #--Valid ESM/ESP header versions
    validHeaderVersions = (0.8,1.0)

    #--Class to use to read the TES4 record
    tes4ClassName = 'MreTes4'

    #--Information on the ESP/ESM header format
    class header:   
        format = '=4s4I'
        formatTopGrup = '=4sI4sII'
        formatTupleGrup = '=4sIhhII'
        size = 20
        attrs = ('recType','size','flags1','fid','flags2')
        defaults = ('TES4',0,0,0,0)

    #--Extra read classes: need info from magic effects
    readClasses = ('MreMgef','MreScpt')
    writeClasses = ('MreMgef',)

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

    #--class names for mergeable records
    mergeClasses = ('MreActi', 'MreAlch', 'MreAmmo', 'MreAnio', 'MreAppa',
                    'MreArmo', 'MreBook', 'MreBsgn', 'MreClas', 'MreClot',
                    'MreCont', 'MreCrea', 'MreDoor', 'MreEfsh', 'MreEnch',
                    'MreEyes', 'MreFact', 'MreFlor', 'MreFurn', 'MreGlob',
                    'MreGras', 'MreHair', 'MreIngr', 'MreKeym', 'MreLigh',
                    'MreLscr', 'MreLvlc', 'MreLvli', 'MreLvsp', 'MreMgef',
                    'MreMisc', 'MreNpc',  'MrePack', 'MreQust', 'MreRace',
                    'MreScpt', 'MreSgst', 'MreSlgm', 'MreSoun', 'MreSpel',
                    'MreStat', 'MreTree', 'MreWatr', 'MreWeap', 'MreWthr',
                    'MreClmt', 'MreCsty', 'MreIdle', 'MreLtex', 'MreRegn',
                    'MreSbsp', 'MreSkil',)
