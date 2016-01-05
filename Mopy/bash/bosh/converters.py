# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2015 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""BAIN Converters aka BCFs"""

from . import defaultExt, InstallerConverter
from .. import bolt
from ..bolt import DataDict, PickleDict, GPath, Path

class ConvertersData(DataDict):
    """Converters Data singleton, initialized in InstallersData."""

    def __init__(self, bain_data_dir, converters_dir, dup_bcfs_dir,
                 corrupt_bcfs_dir):
        self.bashDir = bain_data_dir
        self.converters_dir = converters_dir
        self.dup_bcfs_dir = dup_bcfs_dir
        self.corrupt_bcfs_dir = corrupt_bcfs_dir
        #--Persistent data
        self.converterFile = PickleDict(self.bashDir.join(u'Converters.dat'))
        self.srcCRC_converters = {}
        self.bcfCRC_converter = {}
        #--Volatile
        self.bcfPath_sizeCrcDate = {}

    def load(self):
        self.converterFile.load()
        convertData = self.converterFile.data
        self.bcfCRC_converter = convertData.get('bcfCRC_converter', dict())
        self.srcCRC_converters = convertData.get('srcCRC_converters', dict())
        return True

    def save(self):
        self.converterFile.data['bcfCRC_converter'] = self.bcfCRC_converter
        self.converterFile.data['srcCRC_converters'] = self.srcCRC_converters
        self.converterFile.save()

    def refreshConvertersNeeded(self):
        """Return True if refreshConverters is necessary."""
        self._prune_converters()
        archives = set([])
        scanned = set([])
        convertersJoin = self.converters_dir.join
        converterGet = self.bcfPath_sizeCrcDate.get
        archivesAdd = archives.add
        scannedAdd = scanned.add
        for archive in self.converters_dir.list():
            apath = convertersJoin(archive)
            if apath.isfile() and self.validConverterName(archive):
                scannedAdd(apath)
        if len(scanned) != len(self.bcfPath_sizeCrcDate):
            return True
        for archive in scanned:
            size, crc, modified = converterGet(archive, (None, None, None))
            if crc is None or (size, modified) != (
                    archive.size, archive.mtime):
                return True
            archivesAdd(archive)
        #--Added/removed packages?
        return archives != set(self.bcfPath_sizeCrcDate)

    #--Converters
    @staticmethod
    def validConverterName(path):
        return path.cext in defaultExt and (
            path.csbody[-4:] == u'-bcf' or u'-bcf-' in path.csbody)

    def refreshConverters(self, progress=None, fullRefresh=False):
        """Refresh converter status, and move duplicate BCFs out of the way."""
        progress = progress or bolt.Progress()
        pending = set()
        bcfCRC_converter = self.bcfCRC_converter
        convJoin = self.converters_dir.join
        #--Current converters
        newData = dict()
        if fullRefresh:
            self.bcfPath_sizeCrcDate.clear()
            self.srcCRC_converters.clear()
        for archive in self.converters_dir.list():
            bcfPath = convJoin(archive)
            if bcfPath.isdir(): continue
            if self.validConverterName(archive):
                size, crc, modified = self.bcfPath_sizeCrcDate.get(bcfPath, (
                    None, None, None))
                if crc is None or (size, modified) != (
                        bcfPath.size, bcfPath.mtime):
                    crc = bcfPath.crc
                    (size, modified) = (bcfPath.size, bcfPath.mtime)
                    if crc in bcfCRC_converter and bcfPath != bcfCRC_converter[
                        crc].fullPath:
                        self.bcfPath_sizeCrcDate.pop(bcfPath, None)
                        if bcfCRC_converter[crc].fullPath.exists():
                            bcfPath.moveTo(
                                    self.dup_bcfs_dir.join(bcfPath.tail))
                        continue
                self.bcfPath_sizeCrcDate[bcfPath] = (size, crc, modified)
                if fullRefresh or crc not in bcfCRC_converter:
                    pending.add(archive)
                else:
                    newData[crc] = bcfCRC_converter[crc]
                    newData[crc].fullPath = bcfPath
        #--New/update crcs?
        self.bcfCRC_converter = newData
        pendingChanged = False
        if bool(pending):
            progress(0, _(u"Scanning Converters..."))
            progress.setFull(len(pending))
            for index, archive in enumerate(sorted(pending)):
                progress(index,
                         _(u'Scanning Converter...') + u'\n' + archive.s)
                pendingChanged |= self.addConverter(archive)
        changed = pendingChanged or (len(newData) != len(bcfCRC_converter))
        self._prune_converters()
        return changed

    def _prune_converters(self):
        """Remove any converters that no longer exist."""
        bcfPath_sizeCrcDate = self.bcfPath_sizeCrcDate
        for bcfPath in bcfPath_sizeCrcDate.keys():
            if not bcfPath.exists() or bcfPath.isdir():
                self.removeConverter(bcfPath)

    def addConverter(self, converter):
        """Links the new converter to installers"""
        if isinstance(converter, basestring):
            #--Adding a new file
            converter = GPath(converter).tail
        if isinstance(converter, InstallerConverter):
            #--Adding a new InstallerConverter
            newConverter = converter
        else:
            #--Adding a new file
            try:
                newConverter = InstallerConverter(converter)
            except:
                fullPath = self.converters_dir.join(converter)
                fullPath.moveTo(self.corrupt_bcfs_dir.join(converter.tail))
                del self.bcfPath_sizeCrcDate[fullPath]
                return False
        #--Check if overriding an existing converter
        oldConverter = self.bcfCRC_converter.get(newConverter.crc)
        if oldConverter:
            oldConverter.fullPath.moveTo(
                    self.dup_bcfs_dir.join(oldConverter.fullPath.tail))
            self.removeConverter(oldConverter)
        #--Link converter to Bash
        srcCRC_converters = self.srcCRC_converters
        [srcCRC_converters[srcCRC].append(newConverter) for srcCRC in
         newConverter.srcCRCs if srcCRC_converters.setdefault(
                srcCRC, [newConverter]) != [newConverter]]
        self.bcfCRC_converter[newConverter.crc] = newConverter
        self.bcfPath_sizeCrcDate[newConverter.fullPath] = (
            newConverter.fullPath.size, newConverter.crc,
            newConverter.fullPath.mtime)
        return True

    def removeConverter(self, converter):
        """Unlink the old converter from installers and delete it."""
        if isinstance(converter, Path):
            #--Removing by filepath
            converter = converter.stail
        if isinstance(converter, InstallerConverter):
            #--Removing existing converter
            oldConverter = self.bcfCRC_converter.pop(converter.crc, None)
            self.bcfPath_sizeCrcDate.pop(converter.fullPath, None)
        else:
            #--Removing by filepath
            bcfPath = self.converters_dir.join(converter)
            size, crc, modified = self.bcfPath_sizeCrcDate.pop(bcfPath, (
                None, None, None))
            if crc is not None:
                oldConverter = self.bcfCRC_converter.pop(crc, None)
        #--Sanity check
        if oldConverter is None: return
        #--Unlink the converter from Bash
        for srcCRC in self.srcCRC_converters.keys():
            for converter in self.srcCRC_converters[srcCRC][:]:
                if converter is oldConverter:
                    self.srcCRC_converters[srcCRC].remove(converter)
            if len(self.srcCRC_converters[srcCRC]) == 0:
                del self.srcCRC_converters[srcCRC]
        del oldConverter
