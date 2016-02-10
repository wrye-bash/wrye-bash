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

#--Game ESM/ESP/BSA files
#  These filenames need to be in lowercase,
bethDataFiles = {
    #--Vanilla
    u'fallout4.esm',
    u'fallout4 - animations.ba2',
    u'fallout4 - interface.ba2',
    u'fallout4 - materials.ba2',
    u'fallout4 - meshes.ba2',
    u'fallout4 - meshesextra.ba2',
    u'fallout4 - misc.ba2',
    u'fallout4 - shaders.ba2',
    u'fallout4 - sounds.ba2',
    u'fallout4 - startup.ba2',
    u'fallout4 - textures1.ba2',
    u'fallout4 - textures2.ba2',
    u'fallout4 - textures3.ba2',
    u'fallout4 - textures4.ba2',
    u'fallout4 - textures5.ba2',
    u'fallout4 - textures6.ba2',
    u'fallout4 - textures7.ba2',
    u'fallout4 - textures8.ba2',
    u'fallout4 - textures9.ba2',
    u'fallout4 - voices.ba2',
}

#--Every file in the Data directory from Bethsoft
allBethFiles = {
    # Section 1: Vanilla files
    u'Fallout4.esm',
    u'Fallout4.cdx',
    u'Fallout4 - Animations.ba2',
    u'Fallout4 - Geometry.csg',
    u'Fallout4 - Interface.ba2',
    u'Fallout4 - Materials.ba2',
    u'Fallout4 - Meshes.ba2',
    u'Fallout4 - MeshesExtra.ba2',
    u'Fallout4 - Misc.ba2',
    u'Fallout4 - Shaders.ba2',
    u'Fallout4 - Sounds.ba2',
    u'Fallout4 - Startup.ba2',
    u'Fallout4 - Textures1.ba2',
    u'Fallout4 - Textures2.ba2',
    u'Fallout4 - Textures3.ba2',
    u'Fallout4 - Textures4.ba2',
    u'Fallout4 - Textures5.ba2',
    u'Fallout4 - Textures6.ba2',
    u'Fallout4 - Textures7.ba2',
    u'Fallout4 - Textures8.ba2',
    u'Fallout4 - Textures9.ba2',
    u'Fallout4 - Voices.ba2',
    # Section 2: Strings Files
    u'Strings\\Fallout4_en.DLSTRINGS',
    u'Strings\\Fallout4_en.ILSTRINGS',
    u'Strings\\Fallout4_en.STRINGS',
    # Section 3: Video Clips
    u'Video\\AGILITY.bk2',
    u'Video\\CHARISMA.bk2',
    u'Video\\Endgame_FEMALE_A.bk2',
    u'Video\\Endgame_FEMALE_B.bk2',
    u'Video\\Endgame_MALE_A.bk2',
    u'Video\\Endgame_MALE_B.bk2',
    u'Video\\ENDURANCE.bk2',
    u'Video\\GameIntro_V3_B.bk2',
    u'Video\\INTELLIGENCE.bk2',
    u'Video\\Intro.bk2',
    u'Video\\LUCK.bk2',
    u'Video\\MainMenuLoop.bk2',
    u'Video\\PERCEPTION.bk2',
    u'Video\\STRENGTH.bk2',
    # Section 4: F4SE INI File
    u'F4SE\\f4se.ini',
    # Section 5: GECK files
}

# Function Info ---------------------------------------------------------------
conditionFunctionData = tuple()

allConditions = set(entry[0] for entry in conditionFunctionData)
fid1Conditions = set(entry[0] for entry in conditionFunctionData if entry[2] == 2)
fid2Conditions = set(entry[0] for entry in conditionFunctionData if entry[3] == 2)
# Skip 3 and 4 because it needs to be set per runOn
fid5Conditions = set(entry[0] for entry in conditionFunctionData if entry[4] == 2)

#--List of GMST's in the main plugin (Fallout4.esm) that have 0x00000000
#  as the form id.  Any GMST as such needs it Editor Id listed here.
gmstEids = [
    ## TODO: Initial inspection did not seem to have any null FormID GMST's,
    ## double check before enabling the GMST Tweaker
    ]

"""
GLOB record tweaks used by patcher.patchers.multitweak_settings.GmstTweaker

Each entry is a tuple in the following format:
  (DisplayText, MouseoverText, GLOB EditorID, Option1, Option2, ..., OptionN)
  -EditorID can be a plain string, or a tuple of multiple Editor IDs.  If
  it's a tuple, then Value (below) must be a tuple of equal length, providing
  values for each GLOB
Each Option is a tuple:
  (DisplayText, Value)
  - If you enclose DisplayText in brackets like this: _(u'[Default]'),
  then the patcher will treat this option as the default value.
  - If you use _(u'Custom') as the entry, the patcher will bring up a number
  input dialog

To make a tweak Enabled by Default, enclose the tuple entry for the tweak in
a list, and make a dictionary as the second list item with {'defaultEnabled
':True}. See the UOP Vampire face fix for an example of this (in the GMST
Tweaks)
"""
GlobalsTweaks = list()

"""
GMST record tweaks used by patcher.patchers.multitweak_settings.GmstTweaker

Each entry is a tuple in the following format:
  (DisplayText, MouseoverText, GMST EditorID, Option1, Option2, ..., OptionN)
  - EditorID can be a plain string, or a tuple of multiple Editor IDs. If
  it's a tuple, then Value (below) must be a tuple of equal length, providing
  values for each GMST
Each Option is a tuple:
  (DisplayText, Value)
  - If you enclose DisplayText in brackets like this: _(u'[Default]'),
  then the patcher will treat this option as the default value.
  - If you use _(u'Custom') as the entry, the patcher will bring up a number
  input dialog

To make a tweak Enabled by Default, enclose the tuple entry for the tweak in
a list, and make a dictionary as the second list item with {'defaultEnabled
':True}. See the UOP Vampire facefix for an example of this (in the GMST
Tweaks)
"""
GmstTweaks = list()
