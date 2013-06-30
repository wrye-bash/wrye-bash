# -*- coding: utf-8 -*-
#
# bait/model/__init__.py
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

from . import impl
from ..util import debug_utils, enum


ROOT_NODE_ID = impl.nodeCounter.next()

class NodeTypes(enum.FlagEnum):
    __enumerables__ = (
        'UNKNOWN', 'ROOT', 'PACKAGE', 'GROUP', 'SUBPACKAGE', 'DIRECTORY', 'FILE')
    # so IDEs can autocomplete
    ROOT = None
    PACKAGE = None
    GROUP = None
    SUBPACKAGE = None
    DIRECTORY = None
    FILE = None

class Errors(enum.Enum):
    __enumerables__ = ('UNKNOWN', 'PERMISSIONS_READ', 'PERMISSIONS_WRITE', 'DISK_FULL')
    # for autocomplete
    PERMISSIONS_READ = None
    PERMISSIONS_WRITE = None
    DISK_FULL = None
    # TODO: ...

class Status(enum.Enum):
    __enumerables__ = ('UNKNOWN', 'OK', 'LOADING', 'DIRTY', 'UNSTABLE')
    # for autocomplete
    OK = None
    LOADING = None
    DIRTY = None
    UNSTABLE = None

class AnnealOperationIds(enum.Enum):
    __enumerables__ = ('NONE', 'COPY', 'OVERWRITE', 'DELETE')
    # for autocomplete
    NONE = None
    COPY = None
    OVERWRITE = None
    DELETE = None

class UpdateTypes(enum.FlagEnum):
    __enumerables__ = ('UNKNOWN', 'ATTRIBUTES', 'CHILDREN', 'DETAILS', 'ERROR')
    # for autocomplete
    ATTRIBUTES = None
    CHILDREN = None
    DETAILS = None
    ERROR = None

# for node updates, the tuple is: (updateType, nodeType, nodeId, version)
UPDATE_TUPLE_IDX_TYPE = 0
UPDATE_NODE_TUPLE_IDX_NODE_TYPE = 1
UPDATE_NODE_TUPLE_IDX_NODE_ID = 2
UPDATE_NODE_TUPLE_IDX_VERSION = 3

# for error, the tuple is: (UPDATE_TYPE_ERROR, errorCode, resourceName)
UPDATE_ERROR_TUPLE_IDX_CODE = 1
UPDATE_ERROR_TUPLE_IDX_RESOURCE_NAME = 2

class _VersionedData(debug_utils.Dumpable):
    """version gets incremented for every change to the data.  clients can check the
    version to ensure an update is for data newer than what it already has"""
    def __init__(self, version):
        self.version = version
