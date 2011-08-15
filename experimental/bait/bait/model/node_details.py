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
    def __init__(self, version=0):
        model._VersionedData.__init__(self, version)
        # TODO: general tab data

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
