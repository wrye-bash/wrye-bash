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
    def __init__(self, numInstalledFiles, installedMb, freeInstalledMb, numLibraryFiles,
                 libraryMb, freeLibraryMb):
        self.status = model.Status.OK
        self.installedFiles = numInstalledFiles
        self.installedMb = installedMb
        self.freeInstalledMb = freeInstalledMb
        self.numLibraryFiles = numLibraryFiles
        self.libraryMb = libraryMb
        self.freeLibraryMb = freeLibraryMb

class StatusLoadingData(debug_utils.Dumpable):
    def __init__(self, numLoadedFiles, totalFiles):
        self.status = model.Status.LOADING
        self.numLoadedFiles = numLoadedFiles
        self.totalFiles = totalFiles

class StatusDirtyData(debug_utils.Dumpable):
    def __init__(self, dirtyPackageNodeIds):
        self.status = model.Status.DIRTY
        self.dirtyPackageNodeIds = dirtyPackageNodeIds

class StatusUnstableData(debug_utils.Dumpable):
    def __init__(self, operations):
        self.status = model.Status.UNSTABLE
        self.operations = operations # tuples of (operationId, nodeId)

class RootNodeAttributes(model._VersionedData):
    def __init__(self, statusData, version=0):
        model._VersionedData.__init__(self, version)
        self.nodeType = model.NodeTypes.ROOT
        self.statusData = statusData

class ContextMenuIds(enum.Enum):
    __enumerables__ = ('UNKNOWN', 'PROJECT', 'ARCHIVE', 'GROUP', 'SUBPACKAGE',
                       'DIRECTORY', 'SELECTABLEFILE', 'UNSELECTABLEFILE', 'BSAFILE',
                       'INSTALLED_DATA')
    # for autocomplete
    PROJECT = None
    ARCHIVE = None
    GROUP = None
    SUBPACKAGE = None
    DIRECTORY = None
    SELECTABLEFILE = None
    UNSELECTABLEFILE = None
    BSAFILE = None
    INSTALLED_DATA = None

class _TreeNodeAttributes(model._VersionedData):
    def __init__(self, nodeType, label, parentNodeId, contextMenuId, isDirty, isInstalled,
                 isNotInstalled, isHidden, isNew, hasMissingDeps, version):
        model._VersionedData.__init__(self, version)
        self.nodeType = nodeType
        self.label = label
        self.parentNodeId = parentNodeId
        self.contextMenuId = contextMenuId
        self.isDirty = isDirty
        self.isInstalled = isInstalled
        self.isNotInstalled = isNotInstalled
        self.isHidden = isHidden
        self.isNew = isNew
        self.hasMissingDeps = hasMissingDeps

class _PackageTreeNodeAttributes(_TreeNodeAttributes):
    def __init__(self, nodeType, label, parentNodeId, contextMenuId, isDirty, isInstalled,
                 isNotInstalled, isHidden, isNew, hasMissingDeps, isUnrecognized,
                 isCorrupt, updateAvailable, version):
        _TreeNodeAttributes.__init__(self, nodeType, label, parentNodeId, contextMenuId,
                                     isDirty, isInstalled, isNotInstalled, isHidden,
                                     isNew, hasMissingDeps, version)
        self.isUnrecognized = isUnrecognized
        self.isCorrupt = isCorrupt
        self.updateAvailable = updateAvailable

class PackageNodeAttributes(_PackageTreeNodeAttributes):
    def __init__(self, label, parentNodeId, contextMenuId, isDirty=False,
                 isInstalled=False, isNotInstalled=False, isHidden=False, isNew=False,
                 hasMissingDeps=False, isUnrecognized=False, isCorrupt=False,
                 updateAvailable=False, alwaysVisible=False, isArchive=False,
                 hasWizard=False, hasMatched=False, hasMismatched=False, hasMissing=False,
                 hasSubpackages=False, version=0):
        _PackageTreeNodeAttributes.__init__(self, model.NodeTypes.PACKAGE, label,
                                            parentNodeId, contextMenuId, isDirty,
                                            isInstalled, isNotInstalled, isHidden, isNew,
                                            hasMissingDeps, isUnrecognized, isCorrupt,
                                            updateAvailable, version)
        self.isArchive = isArchive
        self.hasWizard = hasWizard
        self.hasMatched = hasMatched
        self.hasMismatched = hasMismatched
        self.hasMissing = hasMissing
        self.hasSubpackages = hasSubpackages
        self.alwaysVisible = alwaysVisible

class GroupNodeAttributes(_PackageTreeNodeAttributes):
    def __init__(self, label, parentNodeId, contextMenuId, isDirty=False, isNew=False,
                 hasMissingDeps=False, isUnrecognized=False, isCorrupt=False,
                 updateAvailable=False, version=0):
        _PackageTreeNodeAttributes.__init__(self, model.NodeTypes.GROUP, label,
                                            parentNodeId, contextMenuId, isDirty, False,
                                            False, False, isNew, hasMissingDeps,
                                            isUnrecognized, isCorrupt, updateAvailable,
                                            version)

class SubPackageNodeAttributes(_TreeNodeAttributes):
    def __init__(self):
        _TreeNodeAttributes.__init__(self, model.NodeTypes.SUBPACKAGE)

class DirectoryNodeAttributes(_TreeNodeAttributes):
    def __init__(self, label, parentNodeId, contextMenuId, isNew=False, version=0):
        _TreeNodeAttributes.__init__(self, model.NodeTypes.DIRECTORY, label, parentNodeId,
                                     contextMenuId, False, False, False, False, isNew,
                                     False, version)

class FileNodeAttributes(_TreeNodeAttributes):
    def __init__(self, label, parentNodeId, contextMenuId, isDirty=False,
                 isInstalled=False, isNotInstalled=False, isNew=False,
                 hasMissingDeps=False, crc=None,
                 pendingOperation=model.AnnealOperationIds.NONE, packageNodeId=None,
                 isMatched=False, isMismatched=False, isMissing=False, hasConflicts=False,
                 isMasked=False, isCruft=False, isPlugin=False, isResource=False,
                 isOther=False, version=0):
        _TreeNodeAttributes.__init__(self, model.NodeTypes.FILE, label, parentNodeId,
                                     contextMenuId, isDirty, isInstalled, isNotInstalled,
                                     False, isNew, hasMissingDeps, version)
        self.crc = crc
        self.pendingOperation = pendingOperation
        self.packageNodeId = packageNodeId
        self.isMatched = isMatched
        self.isMismatched = isMismatched
        self.isMissing = isMissing
        self.hasConflicts = hasConflicts
        self.isMasked = isMasked
        self.isCruft = isCruft
        self.isPlugin = isPlugin
        self.isResource = isResource
        self.isOther = isOther
