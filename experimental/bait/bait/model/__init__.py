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


ROOT_NODE_ID = impl.nodeCounter.next()

NODE_TYPE_ROOT = 0x01
NODE_TYPE_PACKAGE = 0x02
NODE_TYPE_GROUP = 0x04
NODE_TYPE_SUBPACKAGE = 0x08
NODE_TYPE_DIRECTORY = 0x10
NODE_TYPE_FILE = 0x20

ERROR_PERMISSIONS_READ = 1
ERROR_PERMISSIONS_WRITE = 2
ERROR_DISK_FULL = 3
# TODO: ...

# for node updates, the tuple is: (updateType, nodeType, nodeId, version)
# for error, the tuple is: (UPDATE_TYPE_ERROR, errorCode, resourceName)
UPDATE_TYPE_ATTRIBUTES = 0x01
UPDATE_TYPE_CHILDREN = 0x02
UPDATE_TYPE_DETAILS = 0x04
UPDATE_TYPE_ERROR = 0x08


class _VersionedData:
    """version gets incremented for every change to the data.  clients can check the
    version to ensure an update is for data newer than what it already has"""
    def __init__(self):
        self.version = 0
