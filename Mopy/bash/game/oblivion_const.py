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

#--Game ESM/ESP/BSA files
#  These filenames need to be in lowercase,
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
    # Section 1: Vanilla files
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
    # Section 2: SI
    u'DLCShiveringIsles - Meshes.bsa',
    u'DLCShiveringIsles - Textures.bsa',
    u'DLCShiveringIsles - Sounds.bsa',
    u'DLCShiveringIsles - Voices.bsa',
    u'DLCShiveringIsles.esp',
    u'Textures\\Effects\\TerrainNoise.dds',
    # Section 3: DLCs
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
