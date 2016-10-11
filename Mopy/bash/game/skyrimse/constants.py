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
allBethFiles -= {u'HighResTexturePack03.bsa', u'Skyrim - VoicesExtra.bsa',
                 u'HighResTexturePack03.esp', u'Skyrim - Voices.bsa',
                 u'HighResTexturePack02.esp', u'Skyrim - Textures.bsa',
                 u'HighResTexturePack01.bsa', u'HighResTexturePack02.bsa',
                 u'Skyrim - Meshes.bsa', u'HighResTexturePack01.esp'}

# add new ones
allBethFiles |= {u'Skyrim - Textures6.bsa', u'Skyrim - Patch.bsa',
                 u'Skyrim - Textures8.bsa', u'Skyrim - Textures5.bsa',
                 u'Skyrim - Textures2.bsa', u'Skyrim - Textures1.bsa',
                 u'Skyrim - Textures3.bsa', u'Skyrim - Textures0.bsa',
                 u'Skyrim - Textures7.bsa', u'Skyrim - Textures4.bsa',
                 u'Skyrim - Meshes1.bsa', u'Skyrim - Voices_en0.bsa',
                 u'Skyrim - Meshes0.bsa'}
