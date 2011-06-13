# -*- coding: utf-8 -*-
#
# bait/model/node_attributes.py
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

from .. import model
from ..util import debug_utils, enum


class StatusOkData(debug_utils.Dumpable):
    def __init__(self):
        self.status = model.Status.OK
        self.numBainFiles = 0
        self.installedFiles = 0
        self.bainMb = 0
        self.installedMb = 0
        self.freeBainMb = 0
        self.freeInstalledMb = 0

class StatusLoadingData(debug_utils.Dumpable):
    def __init__(self):
        self.status = model.Status.LOADING
        self.loadedPackages = 0
        self.totalPackages = 0
        self.loadedFiles = 0
        self.totalFiles = 0

class StatusDirtyData(debug_utils.Dumpable):
    def __init__(self):
        self.status = model.Status.DIRTY
        self.dirtyPackageNodeIds = []

class StatusUnstableData(debug_utils.Dumpable):
    def __init__(self):
        self.status = model.Status.UNSTABLE
        self.operations = [] # tuples of (operationId, nodeId)

class RootNodeAttributes(model._VersionedData):
    def __init__(self, statusData):
        model._VersionedData.__init__(self)
        self.nodeType = self, model.NodeTypes.ROOT
        self.statusData = statusData

class _TreeNodeAttributes(model._VersionedData):
    def __init__(self, nodeType):
        model._VersionedData.__init__(self)
        self.nodeType = nodeType
        self.parentNodeId = None
        self.label = None
        self.dirty = False

class PackageNodeAttributes(_TreeNodeAttributes):
    def __init__(self):
        _TreeNodeAttributes.__init__(self, model.NodeTypes.PACKAGE)
        self.installed = False
        self.hidden = False
        self.archive = False

class GroupNodeAttributes(_TreeNodeAttributes):
    def __init__(self):
        _TreeNodeAttributes.__init__(self, model.NodeTypes.GROUP)
        self.hasInstalled = False
        self.hasNotInstalled = False
        self.hasHidden = False

class SubPackageNodeAttributes(_TreeNodeAttributes):
    def __init__(self):
        _TreeNodeAttributes.__init__(self, model.NodeTypes.SUBPACKAGE)

class DirectoryNodeAttributes(_TreeNodeAttributes):
    def __init__(self):
        _TreeNodeAttributes.__init__(self, model.NodeTypes.DIRECTORY)

class FileNodeAttributes(_TreeNodeAttributes):
    def __init__(self):
        _TreeNodeAttributes.__init__(self, model.NodeTypes.FILE)
