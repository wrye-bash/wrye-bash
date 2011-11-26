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

#--Name of the game
name = 'Oblivion'

#--Exe to look for to see if this is the right game
exe = 'Oblivion.exe'

#--Name of the script extender launcher
scriptExtenderName = 'OBSE'
scriptExtender = 'obse_loader.exe'
scriptExtenderSteam = 'obse_1_2_416.dll'

#--Wrye Bash capabilities with this game
canBash = True
canEditSaves = True

#--The main plugin Wrye Bash should look for
masterFiles = [
    r'Oblivion.esm',
    r'Nehrim.esm',
    ]

#--INI files that should show up in the INI Edits tab
iniFiles = [
    r'Oblivion.ini',
    ]

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

#--Valid ESM/ESP header versions
validHeaderVersions = (0.8,1.0)

#--Class to use to read the TES4 record
tes4ClassName = 'MreTes4'

#--How to unpack the record header
unpackRecordHeader = ('4s4I',20,'REC_HEAD')
