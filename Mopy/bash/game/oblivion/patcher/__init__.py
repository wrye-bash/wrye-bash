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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This package contains the Oblivion specific patchers. This module
contains the data structures that are dynamically set on a per game basis in
bush."""
from ....patcher import PatcherInfo as pi
from .preservers import RoadImporter, CBash_RoadImporter
from .special import AlchemicalCatalogs, CBash_AlchemicalCatalogs, \
    SEWorldEnforcer, CBash_SEWorldEnforcer, CoblExhaustion, \
    CBash_CoblExhaustion, MFactMarker, CBash_MFactMarker

_special_patchers = (
    (b'AlchemicalCatalogs', AlchemicalCatalogs, u'CBash_AlchemicalCatalogs'),
    (b'CBash_AlchemicalCatalogs', CBash_AlchemicalCatalogs,
     u'AlchemicalCatalogs'),
    (b'SEWorldEnforcer', SEWorldEnforcer, u'CBash_SEWorldEnforcer'),
    (b'CBash_SEWorldEnforcer', CBash_SEWorldEnforcer, u'SEWorldEnforcer')
)
gameSpecificPatchers = {pname: pi(ptype, twin, ptype.gui_cls_vars()) for
                        pname, ptype, twin in _special_patchers}

_list_patchers =(
    (b'CoblExhaustion', CoblExhaustion, u'CBash_CoblExhaustion'),
    (b'CBash_CoblExhaustion', CBash_CoblExhaustion, u'CoblExhaustion'),
    (b'MFactMarker', MFactMarker, u'CBash_MFactMarker'),
    (b'CBash_MFactMarker', CBash_MFactMarker, u'MFactMarker')
)
gameSpecificListPatchers = {pname: pi(ptype, twin, ptype.gui_cls_vars()) for
                            pname, ptype, twin in _list_patchers}

_import_patchers = (
    (b'RoadImporter', RoadImporter, u'CBash_RoadImporter'),
    (b'CBash_RoadImporter', CBash_RoadImporter, u'RoadImporter')
)
game_specific_import_patchers = {
    pname: pi(ptype, twin,
              {u'patcher_type': ptype, u'_patcher_txt': ptype.patcher_text,
               u'patcher_name': ptype.patcher_name, u'autoKey': ptype.autoKey})
    for pname, ptype, twin in _import_patchers
}
