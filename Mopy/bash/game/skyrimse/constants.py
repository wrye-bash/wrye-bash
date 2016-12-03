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

# Import all constants from skyrim then edit them as needed

from ..skyrim.constants import *

bethDataFiles = {
    u'skyrim.esm',
    u'update.esm',
    u'dawnguard.esm',
    u'dragonborn.esm',
    u'hearthfires.esm',
    u'skyrim - animations.bsa',
    u'skyrim - interface.bsa',
    u'skyrim - meshes0.bsa',
    u'skyrim - meshes1.bsa',
    u'skyrim - misc.bsa',
    u'skyrim - patch.bsa',
    u'skyrim - shaders.bsa',
    u'skyrim - sounds.bsa',
    u'skyrim - textures0.bsa',
    u'skyrim - textures1.bsa',
    u'skyrim - textures2.bsa',
    u'skyrim - textures3.bsa',
    u'skyrim - textures4.bsa',
    u'skyrim - textures5.bsa',
    u'skyrim - textures6.bsa',
    u'skyrim - textures7.bsa',
    u'skyrim - textures8.bsa',
    u'skyrim - voices_en0.bsa',
}

# remove removed from allBethFiles
allBethFiles -= {u'Update.bsa', u'Dawnguard.bsa', u'Dragonborn.bsa',
                 u'HearthFires.bsa', u'HighResTexturePack03.bsa',
                 u'Skyrim - VoicesExtra.bsa', u'HighResTexturePack03.esp',
                 u'Skyrim - Voices.bsa', u'HighResTexturePack02.esp',
                 u'Skyrim - Textures.bsa', u'HighResTexturePack01.bsa',
                 u'HighResTexturePack02.bsa', u'Skyrim - Meshes.bsa',
                 u'HighResTexturePack01.esp'
                 u'shadersfx\\Lighting\\059\\P800C05.fxp',
                 u'shadersfx\\Lighting\\059\\V800400.fxp',
                 u'shadersfx\\Lighting\\059\\V800405.fxp',
                 u'shadersfx\\Lighting\\059\\VC00401.fxp',
                 u'Sound\\Voice\\Processing\\FonixData.cdf',
                 u'Strings\\Dawnguard_English.DLSTRINGS',
                 u'Strings\\Dawnguard_English.ILSTRINGS',
                 u'Strings\\Dawnguard_English.STRINGS',
                 u'Strings\\Dragonborn_English.DLSTRINGS',
                 u'Strings\\Dragonborn_English.ILSTRINGS',
                 u'Strings\\Dragonborn_English.STRINGS',
                 u'Strings\\Hearthfires_English.DLSTRINGS',
                 u'Strings\\Hearthfires_English.ILSTRINGS',
                 u'Strings\\Hearthfires_English.STRINGS',
                 u'Strings\\Skyrim_English.DLSTRINGS',
                 u'Strings\\Skyrim_English.ILSTRINGS',
                 u'Strings\\Skyrim_English.STRINGS',
                 u'Strings\\Update_English.DLSTRINGS',
                 u'Strings\\Update_English.ILSTRINGS',
                 u'Strings\\Update_English.STRINGS',
                 u'Interface\\Translate_ENGLISH.txt',
                 u'LSData\\DtC6dal.dat',
                 u'LSData\\DtC6dl.dat',
                 u'LSData\\Wt16M9bs.dat',
                 u'LSData\\Wt16M9fs.dat',
                 u'LSData\\Wt8S9bs.dat',
                 u'LSData\\Wt8S9fs.dat'}

# add new ones
allBethFiles |= {u'Skyrim - Textures6.bsa', u'Skyrim - Patch.bsa',
                 u'Skyrim - Textures8.bsa', u'Skyrim - Textures5.bsa',
                 u'Skyrim - Textures2.bsa', u'Skyrim - Textures1.bsa',
                 u'Skyrim - Textures3.bsa', u'Skyrim - Textures0.bsa',
                 u'Skyrim - Textures7.bsa', u'Skyrim - Textures4.bsa',
                 u'Skyrim - Meshes1.bsa', u'Skyrim - Voices_en0.bsa',
                 u'Skyrim - Meshes0.bsa',
                 u'Scripts\\Source\\Backup\\QF_C00JorrvaskrFight_000BC0BD_BACKUP_05272016_113715AM.psc',
                 u'Scripts\\Source\\Backup\\QF_C00_0004B2D9_BACKUP_05272016_113428AM.psc'}

# xEdit menu string and key for expert setting
xEdit_expert = (_(u'SSEEdit Expert'), 'sseView.iKnowWhatImDoing')
