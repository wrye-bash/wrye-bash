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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Temp module to encapsulate some shared dependencies left over from splitting
special.py."""

from ....bolt import GPath
from ....patcher.base import Abstract_Patcher

cobl_main = GPath(u'Cobl Main.esm')

class ExSpecial(Abstract_Patcher):
    """Those used to be subclasses of SpecialPatcher that did not make much
    sense as they did not use scan_more."""
    patcher_group = u'Special'
    patcher_order = 40
    patcher_name = u'UNDEFINED'
    patcher_desc = u'UNDEFINED'
    _config_key = None # type: str

    @classmethod
    def gui_cls_vars(cls):
        """Class variables for gui patcher classes created dynamically."""
        return {u'patcher_type': cls, u'patcher_desc': cls.patcher_desc,
                u'patcher_name': cls.patcher_name,
                u'_config_key': cls._config_key}
