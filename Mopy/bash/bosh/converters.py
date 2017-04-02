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

import cPickle
import re
import sys

from ..archives import defaultExt, readExts, compressionSettings, \
    compressCommand, extractCommand
from .. import bolt, archives, bass
from ..bolt import DataDict, PickleDict, GPath, Path, StateError, sio, \
    SubProgress, ArgumentError

converters_dir = None
installers_dir = None

class ConvertersData(DataDict):
    """Converters Data singleton, initialized in InstallersData."""

    def __init__(self, bain_data_dir, converters_dir_, dup_bcfs_dir,
                 corrupt_bcfs_dir, installers_dir_):
        global converters_dir, installers_dir
        converters_dir = converters_dir_
        installers_dir = installers_dir_
        self.dup_bcfs_dir = dup_bcfs_dir
        self.corrupt_bcfs_dir = corrupt_bcfs_dir
        #--Persistent data
        self.converterFile = PickleDict(bain_data_dir.join(u'Converters.dat'))
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
        archives_set = set()
        scanned = set()
        convertersJoin = converters_dir.join
        converterGet = self.bcfPath_sizeCrcDate.get
        archivesAdd = archives_set.add
        scannedAdd = scanned.add
        for bcf_archive in converters_dir.list():
            apath = convertersJoin(bcf_archive)
            if apath.isfile() and self.validConverterName(bcf_archive):
                scannedAdd(apath)
        if len(scanned) != len(self.bcfPath_sizeCrcDate):
            return True
        for bcf_archive in scanned:
            size, crc, modified = converterGet(bcf_archive, (None, None, None))
            if crc is None or (size, modified) != bcf_archive.size_mtime():
                return True
            archivesAdd(bcf_archive)
        #--Added/removed packages?
        return archives_set != set(self.bcfPath_sizeCrcDate)

    #--Converters
    @staticmethod
    def validConverterName(path_name):
        return path_name.cext in defaultExt and (
            path_name.csbody[-4:] == u'-bcf' or u'-bcf-' in path_name.csbody)

    def refreshConverters(self, progress=None, fullRefresh=False):
        """Refresh converter status, and move duplicate BCFs out of the way."""
        progress = progress or bolt.Progress()
        pending = set()
        bcfCRC_converter = self.bcfCRC_converter
        convJoin = converters_dir.join
        #--Current converters
        newData = dict()
        if fullRefresh:
            self.bcfPath_sizeCrcDate.clear()
            self.srcCRC_converters.clear()
        for bcf_archive in converters_dir.list():
            bcfPath = convJoin(bcf_archive)
            if bcfPath.isdir(): continue
            if self.validConverterName(bcf_archive):
                size, crc, modified = self.bcfPath_sizeCrcDate.get(bcfPath, (
                    None, None, None))
                size_mtime = bcfPath.size_mtime()
                if crc is None or (size, modified) != size_mtime:
                    crc = bcfPath.crc
                    (size, modified) = size_mtime
                    if crc in bcfCRC_converter and bcfPath != bcfCRC_converter[
                        crc].fullPath:
                        self.bcfPath_sizeCrcDate.pop(bcfPath, None)
                        if bcfCRC_converter[crc].fullPath.exists():
                            bcfPath.moveTo(
                                    self.dup_bcfs_dir.join(bcfPath.tail))
                        continue
                self.bcfPath_sizeCrcDate[bcfPath] = (size, crc, modified)
                if fullRefresh or crc not in bcfCRC_converter:
                    pending.add(bcf_archive)
                else:
                    newData[crc] = bcfCRC_converter[crc]
                    newData[crc].fullPath = bcfPath
        #--New/update crcs?
        self.bcfCRC_converter = newData
        pendingChanged = False
        if bool(pending):
            progress(0, _(u"Scanning Converters..."))
            progress.setFull(len(pending))
            for index, bcf_archive in enumerate(sorted(pending)):
                progress(index,
                         _(u'Scanning Converter...') + u'\n' + bcf_archive.s)
                pendingChanged |= self.addConverter(bcf_archive)
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
                fullPath = converters_dir.join(converter)
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
        s, m = newConverter.fullPath.size_mtime()
        self.bcfPath_sizeCrcDate[newConverter.fullPath] = (
            s, newConverter.crc, m)
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
            bcfPath = converters_dir.join(converter)
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

class InstallerConverter(object):
    """Object representing a BAIN conversion archive, and its configuration"""

    def __init__(self, srcArchives=None, data=None, destArchive=None,
                 BCFArchive=None, blockSize=None, progress=None):
        #--Persistent variables are saved in the data tank for normal
        # operations.
        #--persistBCF is read one time from BCF.dat, and then saved in
        # Converters.dat to keep archive extractions to a minimum
        #--persistDAT has operational variables that are saved in
        # Converters.dat
        #--Do NOT reorder persistBCF,persistDAT,addedPersist or you will
        # break existing BCFs!
        #--Do NOT add new attributes to persistBCF, persistDAT.
        self.persistBCF = ['srcCRCs']
        self.persistDAT = ['crc', 'fullPath']
        #--Any new BCF persistent variables are not allowed. Additional work
        #  needed to support backwards compat.
        #--Any new DAT persistent variables must be appended to
        # addedPersistDAT.
        #----They must be able to handle being set to None
        self.addedPersistDAT = []
        self.srcCRCs = set()
        self.crc = None
        #--fullPath is saved in Converters.dat, but it is also updated on
        # every refresh in case of renaming
        self.fullPath = u'BCF: Missing!'
        #--Semi-Persistent variables are loaded only when and as needed.
        # They're always read from BCF.dat
        #--Do NOT reorder settings,volatile,addedSettings or you will break
        # existing BCFs!
        self.settings = ['comments', 'espmNots', 'hasExtraData', 'isSolid',
                         'skipVoices', 'subActives']
        self.volatile = ['convertedFiles', 'dupeCount']
        #--Any new saved variables, whether they're settings or volatile
        # must be appended to addedSettings.
        #----They must be able to handle being set to None
        self.addedSettings = ['blockSize', ]
        self.convertedFiles = []
        self.dupeCount = {}
        #--Cheap init overloading...
        if data is not None:
            #--Build a BCF from scratch
            self.fullPath = converters_dir.join(BCFArchive)
            self.build(srcArchives, data, destArchive, BCFArchive, blockSize,
                       progress)
            self.crc = self.fullPath.crc
        elif isinstance(srcArchives, bolt.Path):
            #--Load a BCF from file
            self.fullPath = converters_dir.join(srcArchives)
            self.load()
            self.crc = self.fullPath.crc
        #--Else is loading from Converters.dat, called by __setstate__

    def __getstate__(self):
        """Used by pickler to save object state. Used for Converters.dat"""
        return tuple(map(self.__getattribute__, self.persistBCF + self.persistDAT + self.addedPersistDAT))

    def __setstate__(self, values):
        """Used by unpickler to recreate object. Used for Converters.dat"""
        self.__init__()
        map(self.__setattr__,self.persistBCF + self.persistDAT + self.addedPersistDAT, values)

    def __reduce__(self):
        from . import InstallerConverter as boshInstallerConverter
        return boshInstallerConverter, (), tuple(map(self.__getattribute__,
                self.persistBCF + self.persistDAT + self.addedPersistDAT))

    def load(self, fullLoad=False):
        """Load BCF.dat. Called once when a BCF is first installed, during a
        fullRefresh, and when the BCF is applied"""
        if not self.fullPath.exists(): raise StateError(
                u"\nLoading %s:\nBCF doesn't exist." % self.fullPath.s)
        def translate(out):
            with sio(out) as stream:
                # translate data types to new hierarchy
                class _Translator:
                    def __init__(self, streamToWrap):
                        self._stream = streamToWrap
                    def read(self, numBytes):
                        return self._translate(self._stream.read(numBytes))
                    def readline(self):
                        return self._translate(self._stream.readline())
                    @staticmethod
                    def _translate(s):
                        return re.sub(u'^(bolt|bosh)$', ur'bash.\1', s,
                                      flags=re.U)
                translator = _Translator(stream)
                map(self.__setattr__, self.persistBCF, cPickle.load(translator))
                if fullLoad:
                    map(self.__setattr__, self.settings + self.volatile + self.addedSettings, cPickle.load(translator))
        with self.fullPath.unicodeSafe() as converter_path:
            # Temp rename if its name wont encode correctly
            command = ur'"%s" x "%s" BCF.dat -y -so -sccUTF-8' % (
                archives.exe7z, converter_path.s)
            archives.wrapPopenOut(command, translate, errorMsg=
                u"\nLoading %s:\nBCF extraction failed." % self.fullPath.s)

    def save(self, destInstaller):
        #--Dump settings into BCF.dat
        def _dump(att, dat):
            cPickle.dump(tuple(map(self.__getattribute__, att)), dat, -1)
        try:
            with bass.getTempDir().join(u'BCF.dat').open('wb') as f:
                _dump(self.persistBCF, f)
                _dump(self.settings + self.volatile + self.addedSettings, f)
        except Exception as e:
            raise StateError, (u'Error creating BCF.dat:\nError: %s' % e), \
                sys.exc_info()[2]

    def apply(self, destArchive, crc_installer, progress=None, embedded=0L):
        """Applies the BCF and packages the converted archive"""
        #--Prepare by fully loading the BCF and clearing temp
        self.load(True)
        bass.rmTempDir()
        tmpDir = bass.newTempDir()
        #--Extract BCF
        if progress: progress(0, self.fullPath.stail + u'\n' + _(
                u'Extracting files...'))
        with self.fullPath.unicodeSafe() as tempPath:
            command = extractCommand(tempPath, tmpDir)
            archives.extract7z(command, tempPath, progress)
        #--Extract source archives
        lastStep = 0
        if embedded:
            if len(self.srcCRCs) != 1:
                raise StateError(
                    u'Embedded BCF require multiple source archives!')
            realCRCs = self.srcCRCs
            srcCRCs = [embedded]
        else:
            srcCRCs = realCRCs = self.srcCRCs
        nextStep = step = 0.4 / len(srcCRCs)
        for srcCRC, realCRC in zip(srcCRCs, realCRCs):
            srcInstaller = crc_installer[srcCRC]
            files = bolt.sortFiles([x[0] for x in srcInstaller.fileSizeCrcs])
            if not files: continue
            progress(0,
                     srcInstaller.archive + u'\n' + _(u'Extracting files...'))
            tempCRC = srcInstaller.crc
            srcInstaller.crc = realCRC
            self._unpack(srcInstaller, files,
                         SubProgress(progress, lastStep, nextStep))
            srcInstaller.crc = tempCRC
            lastStep = nextStep
            nextStep += step
        #--Move files around and pack them
        try:
            self._arrangeFiles(SubProgress(progress, lastStep, 0.7))
        except bolt.StateError:
            raise
        else:
            self.pack(bass.getTempDir(), destArchive, installers_dir,
                      SubProgress(progress, 0.7, 1.0))
            #--Lastly, apply the settings.
            #--That is done by the calling code, since it requires an
            # InstallerArchive object to work on
        finally:
            try: tmpDir.rmtree(safety=tmpDir.s)
            except: pass
            bass.rmTempDir()

    def applySettings(self, destInstaller):
        """Applies the saved settings to an Installer"""
        map(destInstaller.__setattr__, self.settings + self.addedSettings,
            map(self.__getattribute__, self.settings + self.addedSettings))

    def _arrangeFiles(self,progress):
        """Copy and/or move extracted files into their proper arrangement."""
        tmpDir = bass.getTempDir()
        destDir = bass.newTempDir()
        progress(0, _(u"Moving files..."))
        progress.setFull(1 + len(self.convertedFiles))
        #--Make a copy of dupeCount
        dupes = dict(self.dupeCount.iteritems())
        destJoin = destDir.join
        tempJoin = tmpDir.join

        #--Move every file
        for index, (crcValue, srcDir_File, destFile) in enumerate(
                self.convertedFiles):
            srcDir = srcDir_File[0]
            srcFile = srcDir_File[1]
            if isinstance(srcDir, (basestring, Path)):
                #--either 'BCF-Missing', or crc read from 7z l -slt
                srcDir = u'%s' % srcDir # Path defines __unicode__()
                srcFile = tempJoin(srcDir, srcFile)
            else:
                srcFile = tempJoin(u"%08X" % srcDir, srcFile)
            destFile = destJoin(destFile)
            if not srcFile.exists():
                raise StateError(u"%s: Missing source file:\n%s" % (
                    self.fullPath.stail, srcFile.s))
            if destFile is None:
                raise StateError(
                    u"%s: Unable to determine file destination for:\n%s" % (
                    self.fullPath.stail, srcFile.s))
            numDupes = dupes[crcValue]
            #--Keep track of how many times the file is referenced by
            # convertedFiles
            #--This allows files to be moved whenever possible, speeding
            # file operations up
            if numDupes > 1:
                progress(index, _(u'Copying file...') + u'\n' + destFile.stail)
                dupes[crcValue] = numDupes - 1
                srcFile.copyTo(destFile)
            else:
                progress(index, _(u'Moving file...') + u'\n' + destFile.stail)
                srcFile.moveTo(destFile)
        #--Done with unpacked directory directory
        tmpDir.rmtree(safety=tmpDir.s)

    def build(self, srcArchives, data, destArchive, BCFArchive, blockSize,
              progress=None):
        """Builds and packages a BCF"""
        progress = progress if progress else bolt.Progress()
        #--Initialization
        bass.rmTempDir()
        srcFiles = {}
        destFiles = []
        destInstaller = data[destArchive]
        self.bcf_missing_files = []
        self.blockSize = blockSize
        subArchives = dict()
        srcAdd = self.srcCRCs.add
        convertedFileAppend = self.convertedFiles.append
        destFileAppend = destFiles.append
        missingFileAppend = self.bcf_missing_files.append
        dupeGet = self.dupeCount.get
        srcGet = srcFiles.get
        subGet = subArchives.get
        lastStep = 0
        #--Get settings
        attrs = self.settings
        map(self.__setattr__, attrs, map(destInstaller.__getattribute__,attrs))
        #--Make list of source files
        for installer in [data[x] for x in srcArchives]:
            installerCRC = installer.crc
            srcAdd(installerCRC)
            fileList = subGet(installerCRC, [])
            fileAppend = fileList.append
            for fileName, __size, fileCRC in installer.fileSizeCrcs:
                srcFiles[fileCRC] = (installerCRC, fileName)
                #--Note any subArchives
                if GPath(fileName).cext in readExts:
                    fileAppend(fileName)
            if len(fileList): subArchives[installerCRC] = fileList
        if len(subArchives):
            archivedFiles = dict()
            nextStep = step = 0.3 / len(subArchives)
            #--Extract any subArchives
            #--It would be faster to read them with 7z l -slt
            #--But it is easier to use the existing recursive extraction
            for index, (installerCRC) in enumerate(subArchives):
                installer = data.crc_installer[installerCRC]
                self._unpack(installer, subArchives[installerCRC],
                             SubProgress(progress, lastStep, nextStep))
                lastStep = nextStep
                nextStep += step
            #--Note all extracted files
            tmpDir = bass.getTempDir()
            for crc in tmpDir.list():
                fpath = tmpDir.join(crc)
                for root_dir, y, files in fpath.walk():
                    for file in files:
                        file = root_dir.join(file)
                        archivedFiles[file.crc] = (crc, file.s[len(fpath)+1:])
            #--Add the extracted files to the source files list
            srcFiles.update(archivedFiles)
            bass.rmTempDir()
        #--Make list of destination files
        for fileName, __size, fileCRC in destInstaller.fileSizeCrcs:
            destFileAppend((fileCRC, fileName))
            #--Note files that aren't in any of the source files
            if fileCRC not in srcFiles:
                missingFileAppend(fileName)
                srcFiles[fileCRC] = (u'BCF-Missing', fileName)
            self.dupeCount[fileCRC] = dupeGet(fileCRC, 0) + 1
        #--Monkey around with the progress step values
        #--Smooth the progress bar progression since some of the subroutines
        #  won't always run
        if lastStep == 0:
            if len(self.bcf_missing_files):
                #--No subArchives, but files to pack
                sProgress = SubProgress(progress, lastStep, lastStep + 0.6)
                lastStep += 0.6
            else:
                #--No subroutines will run
                sProgress = SubProgress(progress, lastStep, lastStep + 0.8)
                lastStep += 0.8
        else:
            if len(self.bcf_missing_files):
                #--All subroutines will run
                sProgress = SubProgress(progress, lastStep, lastStep + 0.3)
                lastStep += 0.3
            else:
                #--No files to pack, but subArchives were unpacked
                sProgress = SubProgress(progress, lastStep, lastStep + 0.5)
                lastStep += 0.5
        sProgress(0, BCFArchive.s + u'\n' + _(u'Mapping files...'))
        sProgress.setFull(1 + len(destFiles))
        #--Map the files
        for index, (fileCRC, fileName) in enumerate(destFiles):
            convertedFileAppend((fileCRC, srcGet(fileCRC), fileName))
            sProgress(index, BCFArchive.s + u'\n' + _(
                    u'Mapping files...') + u'\n' + fileName)
        #--Build the BCF
        tempDir2 = bass.newTempDir().join(u'BCF-Missing')
        if len(self.bcf_missing_files):
            #--Unpack missing files
            bass.rmTempDir()
            destInstaller.unpackToTemp(self.bcf_missing_files,
                SubProgress(progress, lastStep, lastStep + 0.2))
            lastStep += 0.2
            #--Move the temp dir to tempDir\BCF-Missing
            #--Work around since moveTo doesn't allow direct moving of a
            # directory into its own subdirectory
            bass.getTempDir().moveTo(tempDir2)
            tempDir2.moveTo(bass.getTempDir().join(u'BCF-Missing'))
        #--Make the temp dir in case it doesn't exist
        tmpDir = bass.getTempDir()
        tmpDir.makedirs()
        self.save(destInstaller)
        #--Pack the BCF
        #--BCF's need to be non-Solid since they have to have BCF.dat
        # extracted and read from during runtime
        self.isSolid = False
        self.pack(tmpDir, BCFArchive, converters_dir,
                  SubProgress(progress, lastStep, 1.0))
        self.isSolid = destInstaller.isSolid

    def pack(self, srcFolder, destArchive, outDir, progress=None):
        """Creates the BAIN'ified archive and cleans up temp"""
        #--Determine settings for 7z
        destArchive, archiveType, solid = compressionSettings(destArchive,
                self.blockSize, self.isSolid)
        command = compressCommand(destArchive, outDir, srcFolder, solid,
                                  archiveType)
        archives.compress7z(command, outDir, destArchive, srcFolder, progress)
        bass.rmTempDir()

    def _unpack(self, srcInstaller, fileNames, progress=None):
        """Recursive function: completely extracts the source installer to
        subTempDir. It does NOT clear the temp folder.  This should be done
        prior to calling the function. Each archive and sub-archive is
        extracted to its own sub-directory to prevent file thrashing"""
        #--Sanity check
        if not fileNames: raise ArgumentError(
                u"No files to extract for %s." % srcInstaller.s)
        tmpDir = bass.getTempDir()
        tempList = bolt.Path.baseTempDir().join(u'WryeBash_listfile.txt')
        #--Dump file list
        try:
            with tempList.open('w', encoding='utf-8-sig') as out:
                out.write(u'\n'.join(fileNames))
        except Exception as e:
            raise StateError, (u"Error creating file list for 7z:\nError: %s"
                               % e), sys.exc_info()[2]
        #--Determine settings for 7z
        installerCRC = srcInstaller.crc
        from . import InstallerArchive
        if isinstance(srcInstaller, InstallerArchive):
            srcInstaller = GPath(srcInstaller.archive)
            apath = installers_dir.join(srcInstaller)
        else:
            apath = srcInstaller
        subTempDir = tmpDir.join(u"%08X" % installerCRC)
        if progress:
            progress(0, srcInstaller.s + u'\n' + _(u'Extracting files...'))
            progress.setFull(1 + len(fileNames))
        command = archives.extractCommand(apath, subTempDir)
        command += u' @%s' % tempList.s
        #--Extract files
        try:
            subArchives = archives.extract7z(command, srcInstaller, progress,
                                             readExtensions=readExts)
        finally:
            tempList.remove()
            bolt.clearReadOnly(subTempDir) ##: do this once
        #--Recursively unpack subArchives
        for archive in map(subTempDir.join, subArchives):
            self._unpack(archive, [u'*'])
