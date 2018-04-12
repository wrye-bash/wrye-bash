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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

# Import all constants from Skyrim SE then edit them as needed

from ..skyrimse.constants import *

bethDataFiles = {
    u'skyrim.esm',
    u'update.esm',
    u'dawnguard.esm',
    u'dragonborn.esm',
    u'hearthfires.esm',
    u'skyrimvr.esm',
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
    u'skyrim_vr - main.bsa'
}

# xEdit menu string and key for expert setting
xEdit_expert = (_(u'TES5VREdit Expert'), 'tes5vrview.iKnowWhatImDoing')
