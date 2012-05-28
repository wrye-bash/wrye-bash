# -*- coding: utf-8 -*-
#
# bait/model/node_details.py
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


# TODO: flesh this file out more

class PackageNodeDetails(model._VersionedData):
    def __init__(self, isArchive=False, isHidden=False, isInstalled=False, packageBytes=0,
                 selectedBytes=0, lastModifiedTimestamp="", numFiles=0, numDirty=0,
                 numOverridden=0, numSkipped=0, numSelectedMatched=0,
                 numSelectedMismatched=0, numSelectedOverridden=0, numSelectedMissing=0,
                 numTotalSelected=0, numUnselectedMatched=0, numUnselectedMismatched=0,
                 numUnselectedOverridden=0, numUnselectedMissing=0,
                 numTotalUnselected=0, numTotalMatched=0, numTotalMismatched=0,
                 numTotalOverridden=0, numTotalMissing=0, numTotalSelectable=0,
                 imageFileHandle=None, version=0):
        model._VersionedData.__init__(self, version)
        self.isArchive = isArchive
        self.isHidden = isHidden
        self.isInstalled = isInstalled
        self.packageBytes = packageBytes
        self.selectedBytes = selectedBytes
        self.lastModifiedTimestamp = lastModifiedTimestamp
        self.numFiles = numFiles
        self.numDirty = numDirty
        self.numOverridden = numOverridden
        self.numSkipped = numSkipped
        self.numSelectedMatched = numSelectedMatched
        self.numSelectedMismatched = numSelectedMismatched
        self.numSelectedOverridden = numSelectedOverridden
        self.numSelectedMissing = numSelectedMissing
        self.numTotalSelected = numTotalSelected
        self.numUnselectedMatched = numUnselectedMatched
        self.numUnselectedMismatched = numUnselectedMismatched
        self.numUnselectedOverridden = numUnselectedOverridden
        self.numUnselectedMissing = numUnselectedMissing
        self.numTotalUnselected = numTotalUnselected
        self.numTotalMatched = numTotalMatched
        self.numTotalMismatched = numTotalMismatched
        self.numTotalOverridden = numTotalOverridden
        self.numTotalMissing = numTotalMissing
        self.numTotalSelectable = numTotalSelectable
        self.imageFileHandle = imageFileHandle

class FileNodeDetails(model._VersionedData):
    def __init__(self, version=0):
        model._VersionedData.__init__(self, version)
        self.size = 0
        self.crc = 0
        self.modDate = 0
        self.conflictingNodeIds = []
        self.conflictWinner = 0

class EspFileNodeDetails(FileNodeDetails):
    def __init__(self, version=0):
        FileNodeDetails.__init__(self, version)
        self.records = 0
        self.masters = [] # esp file names
        self.deps = [] # node Ids
        self.uninstalledDeps = [] # node Ids
        self.missingDeps = [] # file names

class BsaFileNodeDetails(FileNodeDetails):
    def __init__(self, version=0):
        FileNodeDetails.__init__(self, version)
        self.numFiles = 0

class ResourceFileNodeDetails(FileNodeDetails):
    def __init__(self, version=0):
        FileNodeDetails.__init__(self, version)
        self.thumbnailFilePath = None
