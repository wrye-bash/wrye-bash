# -*- coding: utf-8 -*-
#
# bait/presenter/__init__.py
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <http://www.gnu.org/licenses/>.
#
#  Wrye Bash Copyright (C) 2011 Myk Taylor
#
# =============================================================================

DETAILS_TAB_ID_GENERAL = 1
DETAILS_TAB_ID_DIRTY = 2
DETAILS_TAB_ID_CONFLICTS = 3
DETAILS_TAB_ID_SELECTED = 4
DETAILS_TAB_ID_UNSELECTED = 5
DETAILS_TAB_ID_SKIPPED = 6

FILTER_ID_PACKAGES_HIDDEN        =       0x1
FILTER_ID_PACKAGES_INSTALLED     =       0x2
FILTER_ID_PACKAGES_NOT_INSTALLED =       0x4
FILTER_ID_FILES_PLUGINS          =       0x8
FILTER_ID_FILES_RESOURCES        =      0x10
FILTER_ID_FILES_OTHER            =      0x20
FILTER_ID_DIRTY_ADD              =      0x40
FILTER_ID_DIRTY_UPDATE           =      0x80
FILTER_ID_DIRTY_DELETE           =     0x100
FILTER_ID_CONFLICTS_SELECTED     =     0x200
FILTER_ID_CONFLICTS_UNSELECTED   =     0x400
FILTER_ID_CONFLICTS_ACTIVE       =     0x800
FILTER_ID_CONFLICTS_INACTIVE     =    0x1000
FILTER_ID_CONFLICTS_HIGHER       =    0x2000
FILTER_ID_CONFLICTS_LOWER        =    0x4000
FILTER_ID_SELECTED_MATCHED       =    0x8000
FILTER_ID_SELECTED_MISMATCHED    =   0x10000
FILTER_ID_SELECTED_OVERRIDDEN    =   0x20000
FILTER_ID_SELECTED_MISSING       =   0x40000
FILTER_ID_UNSELECTED_MATCHED     =   0x80000
FILTER_ID_UNSELECTED_MISMATCHED  =  0x100000
FILTER_ID_UNSELECTED_OVERRIDDEN  =  0x200000
FILTER_ID_UNSELECTED_MISSING     =  0x400000
FILTER_ID_SKIPPED_NONGAME        =  0x800000
FILTER_ID_SKIPPED_MASKED         = 0x1000000

NODE_TYPE_GROUP = 1
NODE_TYPE_ARCHIVE = 2
NODE_TYPE_PROJECT = 3
NODE_TYPE_SUBPROJECT = 4
NODE_TYPE_DIRECTORY = 5
NODE_TYPE_FILE = 6
