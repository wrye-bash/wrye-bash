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


INSTALLERS_ROOT_NODE_ID = impl.nodeCounter.next()
TARGET_ROOT_NODE_ID     = impl.nodeCounter.next()

NODE_TYPE_GROUP = 0x01
NODE_TYPE_PROJECT_ROOT = 0x02
NODE_TYPE_SUBPROJECT = 0x04
NODE_TYPE_ARCHIVE = 0x08
NODE_TYPE_DIRECTORY = 0x10
NODE_TYPE_FILE = 0x20

UPDATE_TYPE_ATTRIBUTES = 1
UPDATE_TYPE_CHILDREN = 2
UPDATE_TYPE_DETAILS  = 3
UPDATE_TYPE_STATUS   = 4
UPDATE_TYPE_ERROR   = 5
