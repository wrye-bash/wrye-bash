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

from ..util import enum
from .. import model


class DetailsTabIds(enum.Enum):
    __enumerables__ = (
        'NONE', 'GENERAL', 'DIRTY', 'CONFLICTS', 'SELECTED', 'UNSELECTED', 'SKIPPED')
    # for autocomplete
    NONE = None
    GENERAL = None
    DIRTY = None
    CONFLICTS = None
    SELECTED = None
    UNSELECTED = None
    SKIPPED = None

class FilterIds(enum.FlagEnum):
    __enumerables__ = (
        'NONE',
        'PACKAGES_HIDDEN', 'PACKAGES_INSTALLED', 'PACKAGES_NOT_INSTALLED',
        'FILES_PLUGINS', 'FILES_RESOURCES', 'FILES_OTHER',
        'DIRTY_ADD', 'DIRTY_UPDATE', 'DIRTY_DELETE',
        'CONFLICTS_SELECTED', 'CONFLICTS_UNSELECTED', 'CONFLICTS_ACTIVE',
        'CONFLICTS_INACTIVE', 'CONFLICTS_HIGHER', 'CONFLICTS_LOWER', 'CONFLICTS_MATCHED',
        'CONFLICTS_MISMATCHED', 'SELECTED_MATCHED', 'SELECTED_MISMATCHED',
        'SELECTED_HAS_CONFLICTS', 'SELECTED_NO_CONFLICTS', 'SELECTED_MISSING',
        'UNSELECTED_MATCHED', 'UNSELECTED_MISMATCHED', 'UNSELECTED_HAS_CONFLICTS',
        'UNSELECTED_NO_CONFLICTS', 'UNSELECTED_MISSING',
        'SKIPPED_NONGAME', 'SKIPPED_MASKED')
    # for autocomplete
    NONE = None
    PACKAGES_HIDDEN = None
    PACKAGES_INSTALLED = None
    PACKAGES_NOT_INSTALLED = None
    FILES_PLUGINS = None
    FILES_RESOURCES = None
    FILES_OTHER = None
    DIRTY_ADD = None
    DIRTY_UPDATE = None
    DIRTY_DELETE = None
    CONFLICTS_SELECTED = None
    CONFLICTS_UNSELECTED = None
    CONFLICTS_ACTIVE = None
    CONFLICTS_INACTIVE = None
    CONFLICTS_HIGHER = None
    CONFLICTS_LOWER = None
    CONFLICTS_MATCHED = None
    CONFLICTS_MISMATCHED = None
    SELECTED_MATCHED = None
    SELECTED_MISMATCHED = None
    SELECTED_MISSING = None
    SELECTED_HAS_CONFLICTS = None
    SELECTED_NO_CONFLICTS = None
    UNSELECTED_MATCHED = None
    UNSELECTED_MISMATCHED = None
    UNSELECTED_MISSING = None
    UNSELECTED_HAS_CONFLICTS = None
    UNSELECTED_NO_CONFLICTS = None
    SKIPPED_NONGAME = None
    SKIPPED_MASKED = None

class AnnealOperations(model.Operations):
    pass
