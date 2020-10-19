# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, either version 3
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <https://www.gnu.org/licenses/>.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This package contains the Oblivion specific patchers. This module
contains the data structures that are dynamically set on a per game basis in
bush."""
from ....patcher import PatcherInfo as pi
from .preservers import RoadImporter
from .special import AlchemicalCatalogs, SEWorldEnforcer, CoblExhaustion, \
    MFactMarker

_special_patchers = (
    (b'AlchemicalCatalogs', AlchemicalCatalogs),
    (b'SEWorldEnforcer', SEWorldEnforcer),
)
gameSpecificPatchers = {pname: pi(ptype, ptype.gui_cls_vars()) for
                        pname, ptype in _special_patchers}

_list_patchers =(
    (b'CoblExhaustion', CoblExhaustion, u'Exhaust'),
    (b'MFactMarker', MFactMarker, u'MFact'),
)
gameSpecificListPatchers = {pname: pi(ptype, ptype.gui_cls_vars(), ck)
                            for pname, ptype, ck in _list_patchers}

_import_patchers = (
    (b'RoadImporter', RoadImporter),
)
game_specific_import_patchers = {
    pname: pi(ptype,
              {u'patcher_type': ptype, u'_patcher_txt': ptype.patcher_text,
               u'patcher_name': ptype.patcher_name, u'autoKey': ptype.autoKey})
    for pname, ptype in _import_patchers
}
