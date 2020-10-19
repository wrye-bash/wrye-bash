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

"""This module acts as the central import point for brec, a package housing
classes used to build up the PBash record definitions for each game, as well as
shared definitions for some common records and subrecords. Any code outside the
brec package should import from here, so that classes may be moved around
without breaking third-party code."""

from .advanced_elements import *
from .basic_elements import *
from .common_records import *
from .common_subrecords import *
from .mod_io import *
from .record_groups import *
from .record_structs import *
from .utils_constants import *

# HACK for now - _coerce will disappear in parsers ABC merge
from .utils_constants import _coerce
