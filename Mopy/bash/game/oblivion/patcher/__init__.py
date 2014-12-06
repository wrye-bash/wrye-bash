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

"""This package contains the Oblivion specific patchers. This module
contains the data structures that are dynamically set on a per game basis in
bush."""
from .special import *

gameSpecificPatchers = {
    # special
    "AlchemicalCatalogs": (AlchemicalCatalogs, 'CBash_AlchemicalCatalogs'),
    "CBash_AlchemicalCatalogs": (CBash_AlchemicalCatalogs, 'AlchemicalCatalogs'),
    "SEWorldEnforcer": (SEWorldEnforcer, 'CBash_SEWorldEnforcer'),
    "CBash_SEWorldEnforcer": (CBash_SEWorldEnforcer, 'SEWorldEnforcer'),
    }
gameSpecificListPatchers = {
    "CoblExhaustion": (CoblExhaustion, 'CBash_CoblExhaustion'),
    "CBash_CoblExhaustion": (CBash_CoblExhaustion, 'CoblExhaustion'),
    "MFactMarker": (MFactMarker, 'CBash_MFactMarker'),
    "CBash_MFactMarker": (CBash_MFactMarker, 'MFactMarker'),
    }
