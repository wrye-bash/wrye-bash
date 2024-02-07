# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, either version 3
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <https://www.gnu.org/licenses/>.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""BAIN Converters aka BCFs"""

from __future__ import annotations

import io
import os
import pickle
import sys
from collections import defaultdict
from itertools import chain

from .. import archives, bolt
from ..archives import defaultExt, readExts
from ..bolt import DataDict, Path, PickleDict, SubProgress, \
    forward_compat_path_to_fn_list, top_level_files, GPath_no_norm
from ..exception import ArgumentError, StateError
from ..wbtemp import TempDir, TempFile

converters_dir: Path | None = None
installers_dir: Path | None = None

class ConvertersData(DataDict):
    """Converters Data singleton, initialized in InstallersData."""

    def __init__(self, bain_data_dir, converters_dir_, dup_bcfs_dir,
                 corrupt_bcfs_dir, installers_dir_):
        super().__init__({})
        global converters_dir, installers_dir
        converters_dir = converters_dir_
        installers_dir = installers_dir_
        self.dup_bcfs_dir = dup_bcfs_dir
        self.corrupt_bcfs_dir = corrupt_bcfs_dir
        #--Persistent data
        self.converterFile = PickleDict(bain_data_dir.join(u'Converters.dat'))
        self.srcCRC_converters = defaultdict(list)
        self.bcfCRC_converter = {}
        #--Volatile
        self.bcfPath_sizeCrcDate = {}

    def load(self):
        # Older Converters.dat pickle and expect bosh.InstallerConverter.
        # See InstallerConverter.__reduce__() for the expect part.
        sys.modules['bash.bosh'].InstallerConverter = InstallerConverter
        sys.modules['bash.bosh'].InstallerConverter.__module__ = 'bash.bosh'
        self.converterFile.load()
        convertData = self.converterFile.pickled_data
        self.bcfCRC_converter = convertData.get(u'bcfCRC_converter', {})
        self.srcCRC_converters = defaultdict(list, convertData.get(
            'srcCRC_converters', {}))
        convs = set(self.bcfCRC_converter.values())
        refs = set(chain(*self.srcCRC_converters.values()))
        if not ((has_scr := convs & refs) == convs):
            bolt.deprint(f'BCFs with no source: {len(convs - has_scr)}')
        if references_miss := refs - convs:
            bolt.deprint(f'missing BCFs for {len(references_miss)}')
            self.__prune_srcCRC(lambda c: c not in convs)
        #Partly reconstruct bcfPath_sizeCrcDate to avoid a full refresh on boot
        self.bcfPath_sizeCrcDate = {co.fullPath: (None, c, None) for c, co in
                                    self.bcfCRC_converter.items()}
        return True

    def save(self):
        pickle_dict = self.converterFile.pickled_data
        pickle_dict['bcfCRC_converter'] = self.bcfCRC_converter
        pickle_dict['srcCRC_converters'] = dict(self.srcCRC_converters)
        self.converterFile.save()

    #--Converters
    @staticmethod
    def validConverterName(fn_conv):
        ends_bcf = (lo := fn_conv.fn_body.lower())[-4:] == '-bcf'
        return fn_conv.fn_ext == defaultExt and ends_bcf or '-bcf-' in lo

    def refreshConverters(self, progress=None, fullRefresh=False):
        """Refresh converter status, and move duplicate BCFs out of the way."""
        #--Current converters
        bcfs_list = [bcf_arch for bcf_arch in top_level_files(converters_dir)
                     if self.validConverterName(bcf_arch)] # few files
        bcf_scd = self.bcfPath_sizeCrcDate
        if change := fullRefresh: # clear all data structures
            bcf_scd.clear()
            self.srcCRC_converters.clear()
            self.bcfCRC_converter.clear()
            pending_ = {*map(converters_dir.join, bcfs_list)}
        else:
            pending_ = set()
            newData = {}
            present_bcfs = [*map(converters_dir.join, bcfs_list)]
            for bcf_archive, bcfPath in [*zip(bcfs_list, present_bcfs)]:
                # on first run it needs to repopulate the bcfPath_sizeCrcDate
                cached_size, crc, mod_time = bcf_scd.get(
                    bcfPath, (None, None, None))
                size_mtime = bcfPath.size_mtime()
                if crc is None or (cached_size, mod_time) != size_mtime:
                    crc_changed = crc != (crc := bcfPath.crc)
                    bcf_scd[bcfPath] = (size_mtime[0], crc, size_mtime[1])
                    if crc_changed:
                        change = True  # added or changed - we must re-add it
                        pending_.add(bcfPath)
                        continue
                newData[crc] = self.bcfCRC_converter[crc] # should be unique
                newData[crc].fullPath = bcfPath ##: why???
            # Remove any converters that no longer exist
            for bcfPath in list(bcf_scd):
                if bcfPath not in present_bcfs:
                    change = True
                    self.removeConverter(bcfPath)
            old_new = set(newData.values())
            self.__prune_srcCRC(
                lambda c: c.fullPath not in present_bcfs or c not in old_new)
            #--New/update crcs?
            self.bcfCRC_converter = newData  # empty on first run
        if pending_:
            progress = progress or bolt.Progress()
            with progress:
                progress(0, _('Scanning Converters…'))
                progress.setFull(len(pending_))
                for index, bcfPath in enumerate(sorted(pending_)):
                    progress(index,
                             _('Scanning Converter…') + f'\n{bcfPath}')
                    path_crc = not fullRefresh and bcf_scd[bcfPath][1]
                    try:
                        converter = InstallerConverter.from_path(bcfPath,
                            cached_crc=path_crc)
                    except StateError: ##: we might get other errors here?
                        cor_dir = self.corrupt_bcfs_dir
                        try:
                            bcfPath.moveTo(cor_dir.join(bcfPath.tail))
                            if not fullRefresh: del bcf_scd[bcfPath]
                            bolt.deprint(f'{bcfPath} is corrupt, moved to '
                                         f'{cor_dir}', traceback=True)
                        except StateError:
                            bolt.deprint(f'{bcfPath} does not exist',
                                         traceback=True)
                        continue
                    change |= self.addConverter(converter, update_cache=False)
        return change

    def addConverter(self, converter: InstallerConverter, update_cache=True):
        """Links the new converter to installers"""
        #--Check if overriding an existing converter
        oldConverter = self.bcfCRC_converter.pop(converter.crc, None)
        if oldConverter:
            oldConverter.fullPath.moveTo(
                    self.dup_bcfs_dir.join(oldConverter.fullPath.tail))
            self.bcfPath_sizeCrcDate.pop(oldConverter.fullPath, None)
            self.removeConverter(oldConverter)
        #--Link converter to Bash
        for srcCRC in converter.srcCRCs:
            self.srcCRC_converters[srcCRC].append(converter)
        self.bcfCRC_converter[converter.crc] = converter
        if update_cache:
            s, m = converter.fullPath.size_mtime()
            self.bcfPath_sizeCrcDate[converter.fullPath] = (
                s, converter.crc, m)
        return True

    def removeConverter(self, oldConverter):
        """Unlink the old converter from installers and delete it."""
        if isinstance(oldConverter, Path):
            #--Removing by filepath
            _size, crc, _mod_time = self.bcfPath_sizeCrcDate.pop(oldConverter,
                (None, None, None))
            oldConverter = self.bcfCRC_converter.pop(crc, None)
        #--Sanity check
        if oldConverter is None: return
        #--Unlink the converter from Bash
        self.__prune_srcCRC(lambda conv: conv is oldConverter) ##: are we sure those are the same object??

    def __prune_srcCRC(self, remove_f):
        for srcCRC, parent_converters in list(self.srcCRC_converters.items()):
            for conv in parent_converters[:]:
                if remove_f(conv):
                    parent_converters.remove(conv)
            if not parent_converters:
                del self.srcCRC_converters[srcCRC]

class InstallerConverter(object):
    """Object representing a BAIN conversion archive, and its configuration"""
    #--Persistent variables are saved in the data tank for normal operations.
    #--_persistBCF is read one time from BCF.dat, and then saved in
    #  Converters.dat to keep archive extractions to a minimum
    #--_persistDAT has operational variables that are saved in Converters.dat
    #--Do NOT reorder _persistBCF,_persistDAT,addedPersist or you will break
    #  existing BCFs!
    #--Do NOT add new attributes to _persistBCF, _persistDAT.
    _persistBCF = ['srcCRCs']
    _persistDAT = ['crc', 'fullPath']
    #--Any new BCF persistent variables are not allowed. Additional work
    #  needed to support backwards compat.
    #--Any new DAT persistent variables must be appended to _addedPersistDAT.
    #----They must be able to handle being set to None
    _addedPersistDAT = []

    def __init__(self, full_path='//\\Loading from __setstate__//\\'):
        self.srcCRCs = set()
        self.crc = None
        #--fullPath is saved in Converters.dat, but it is also updated on
        # every refresh in case of renaming
        self.fullPath: Path = full_path
        #--Semi-Persistent variables are loaded only when and as needed.
        # They're always read from BCF.dat
        #--Do NOT reorder settings,volatile,addedSettings or you will break
        # existing BCFs!
        self._converter_settings = [u'comments', u'espmNots', u'hasExtraData',
                                    u'isSolid', u'skipVoices', u'subActives']
        self.volatile = [u'convertedFiles', u'dupeCount']
        #--Any new saved variables, whether they're settings or volatile
        # must be appended to addedSettings.
        #----They must be able to handle being set to None
        self.addedSettings = [u'blockSize']
        self.convertedFiles = []
        self.dupeCount = {}

    @classmethod
    def from_path(cls, full_path, cached_crc=None):
        """Load a BCF from file."""
        ret = cls(full_path)
        ret.load()
        ret.crc = cached_crc or ret.fullPath.crc
        return ret

    @classmethod
    def from_scratch(cls, srcArchives, idata, destArchive, bcf_archive,
                     blockSize, progress):
        """Build a BCF from scratch."""
        ret = cls(converters_dir.join(bcf_archive))
        ret.build(srcArchives, idata, destArchive, bcf_archive, blockSize,
                  progress)
        ret.crc = ret.fullPath.crc
        return ret

    def __getstate__(self):
        """Used by pickler to save object state. Used for Converters.dat"""
        return tuple(getattr(self, a) for a in self._persistBCF +
                     self._persistDAT + self._addedPersistDAT)

    def __setstate__(self, values):
        """Used by unpickler to recreate object. Used for Converters.dat"""
        self.__init__()
        for a, v in zip(self._persistBCF + self._persistDAT +
                        self._addedPersistDAT, values):
            setattr(self, a, v)

    def __reduce__(self):
        return sys.modules['bash.bosh'].InstallerConverter, (), tuple(
            getattr(self, a) for a in
            self._persistBCF + self._persistDAT + self._addedPersistDAT)

    def load(self, fullLoad=False):
        """Load BCF.dat. Called once when a BCF is first installed, during a
        fullRefresh, and when the BCF is applied"""
        if not self.fullPath.exists(): raise StateError(
            f"\nLoading {self.fullPath}:\nBCF doesn't exist.")
        def translate(out):
            stream = io.BytesIO(out)
            # translate data types to new hierarchy
            _old_modules = {b'bolt', b'bosh'}
            class _Translator(object):
                def __init__(self, streamToWrap):
                    self._stream = streamToWrap
                def read(self, numBytes):
                    return self._translate(self._stream.read(numBytes))
                def readline(self):
                    return self._translate(self._stream.readline())
                @staticmethod
                def _translate(s):
                    return b'bash.' + s if s in _old_modules else s
            translator = _Translator(stream)
            for a, v in zip(self._persistBCF, pickle.load(
                    translator, encoding='bytes')):
                setattr(self, a, v)
            if fullLoad:
                for a, v in zip(self._converter_settings + self.volatile +
                                 self.addedSettings,
                                 pickle.load(translator, encoding='bytes')):
                    setattr(self, a, v)
        # Temp rename if its name wont encode correctly
        err_msg = f'\nLoading {self.fullPath}:\nBCF extraction failed.'
        archives.wrapPopenOut(self.fullPath, translate, errorMsg=err_msg)

    def save(self, conv_out):
        """Dump settings into BCF.dat"""
        def _dump(att, dat):
            pickle.dump(tuple(getattr(self, a) for a in att), dat, -1)
        try:
            with open(os.path.join(conv_out, 'BCF.dat'), 'wb') as f:
                _dump(self._persistBCF, f)
                _dump(self._converter_settings + self.volatile +
                      self.addedSettings, f)
        except Exception as e:
            raise StateError(f'Error creating BCF.dat:\nError: {e}') from e

    def apply(self, destArchive, crc_installer, progress=None, embedded=0):
        """Applies the BCF and packages the converted archive"""
        #--Prepare by fully loading the BCF and clearing temp
        self.load(True)
        #--Extract BCF
        if progress:
            progress(0, self.fullPath.stail + '\n' + _('Extracting files…'))
        #--Extract source archives
        lastStep = 0
        if embedded:
            if len(self.srcCRCs) != 1:
                raise StateError(
                    u'Embedded BCF requires multiple source archives!')
            realCRCs = self.srcCRCs
            srcCRCs = [embedded]
        else:
            srcCRCs = realCRCs = self.srcCRCs
        nextStep = step = 0.4 / len(srcCRCs)
        with TempDir() as tmp_extract, TempDir() as tmp_dest:
            # Don't pass progress in as we haven't got the count of BCF's files
            archives.extract7z(self.fullPath, tmp_extract)
            for srcCRC, realCRC in zip(srcCRCs, realCRCs):
                srcInstaller = crc_installer[srcCRC]
                files = bolt.sortFiles(
                    [x[0] for x in srcInstaller.fileSizeCrcs])
                if not files: continue
                progress(0, f'{srcInstaller}\n' + _('Extracting files…'))
                tempCRC = srcInstaller.crc
                srcInstaller.crc = realCRC
                self._unpack(srcInstaller, files, tmp_extract,
                    progress=SubProgress(progress, lastStep, nextStep))
                srcInstaller.crc = tempCRC
                lastStep = nextStep
                nextStep += step
            #--Move files around and pack them
            self._arrangeFiles(tmp_extract, tmp_dest,
                progress=SubProgress(progress, lastStep, 0.7))
            archives.compress7z(installers_dir.join(destArchive),
                GPath_no_norm(tmp_dest), SubProgress(progress, 0.7, 1.0),
                is_solid=self.isSolid, blockSize=self.blockSize)
            # Lastly, we need to apply the settings. That is done by the
            # calling code, since it requires an InstallerArchive object to
            # work on (see applySettings below and its usage in BAIN)

    def applySettings(self, destInstaller):
        """Applies the saved settings to an Installer"""
        for a in self._converter_settings + self.addedSettings:
            v = getattr(self, a)
            if a == 'espmNots':
                v = forward_compat_path_to_fn_list(v, ret_type=set)
            setattr(destInstaller, a, v)

    def _arrangeFiles(self, src_temp: str, dst_temp: str, *, progress):
        """Copy and/or move extracted files into their proper arrangement.
        Needs two temporary directories as arguments: a source directory
        containing the files to be arranged and a destination directory where
        the arranged files will be placed."""
        progress(0, _('Moving files…'))
        progress.setFull(1 + len(self.convertedFiles))
        dupes = self.dupeCount.copy()
        tempJoin = GPath_no_norm(src_temp).join
        destJoin = GPath_no_norm(dst_temp).join
        #--Move every file
        for index, (crcValue, srcDir_File, destFile) in enumerate(
                self.convertedFiles):
            srcDir, srcFile = srcDir_File
            #--srcDir is either 'BCF-Missing', or crc read from 7z l -slt
            srcDir = f'{srcDir:08X}' if isinstance(srcDir, int) else srcDir
            src_rel = os.path.join(srcDir, srcFile)
            src_full = tempJoin(src_rel)
            if not src_full.exists():
                raise StateError(_('%(bcf_rel)s: Missing source file:') % {
                    'bcf_rel': self.fullPath.stail} + f'\n{src_rel}')
            if destFile is None:
                raise StateError(_('%(bcf_rel)s: Unable to determine file '
                                   'destination for:') % {
                    'bcf_rel': self.fullPath.stail} + f'\n{src_rel}')
            numDupes = dupes[crcValue]
            #--Keep track of how many times the file is referenced by
            # convertedFiles
            #--This allows files to be moved whenever possible, speeding
            # file operations up
            dest_full = destJoin(destFile)
            if numDupes > 1:
                progress(index, _('Copying file…') + f'\n{destFile}')
                # Decrement so that the last usage can be a move
                dupes[crcValue] = numDupes - 1
                src_full.copyTo(dest_full)
            else:
                progress(index, _('Moving file…') + f'\n{destFile}')
                src_full.moveTo(dest_full)

    def build(self, srcArchives, idata, destArchive, bcf_archive, blockSize,
              progress=None, *, __read_ext=tuple(readExts)):
        """Builds and packages a BCF"""
        progress = progress if progress else bolt.Progress()
        #--Initialization
        srcFiles = {}
        destFiles = []
        destInstaller = idata[destArchive]
        self.bcf_missing_files = []
        self.blockSize = blockSize
        subArchives = defaultdict(list)
        convertedFileAppend = self.convertedFiles.append
        destFileAppend = destFiles.append
        dupeGet = self.dupeCount.get
        lastStep = 0
        #--Get settings
        attrs = self._converter_settings
        for a in attrs:
            setattr(self, a, getattr(destInstaller, a))
        #--Make list of source files
        for installer in [idata[x] for x in srcArchives]: # few items
            installerCRC = installer.crc
            self.srcCRCs.add(installerCRC)
            for fileName, __size, fileCRC in installer.fileSizeCrcs: # type: str, int, int
                srcFiles[fileCRC] = (installerCRC, fileName)
                #--Note any subArchives
                if fileName.endswith(__read_ext):
                    subArchives[installerCRC].append(fileName)
        if subArchives:
            crc_installer = {(inst := idata[ikey]).crc: inst for ikey in
                             idata.ipackages(idata)} #TODO(ut) what happens with duplicate crcs?
            archivedFiles = dict()
            nextStep = step = 0.3 / len(subArchives)
            #--Extract any subArchives
            #--It would be faster to read them with 7z l -slt
            #--But it is easier to use the existing recursive extraction
            with TempDir() as combined_temp_dir:
                for installerCRC, subs in subArchives.items():
                    installer = crc_installer[installerCRC]
                    self._unpack(installer, subs, combined_temp_dir,
                        progress=SubProgress(progress, lastStep, nextStep))
                    lastStep = nextStep
                    nextStep += step
                #--Note all extracted files
                for crc in combined_temp_dir.ilist():
                    fpath = combined_temp_dir.join(crc)
                    for root_dir, y, files in fpath.walk(): ##: replace with os walk!!
                        for file in files:
                            file = root_dir.join(file)
                            # crc is an FName, but we want to store strings
                            archivedFiles[file.crc] = (
                                str(crc), file.s[len(fpath)+1:]) # +1 for '/'
            #--Add the extracted files to the source files list
            srcFiles.update(archivedFiles)
        #--Make list of destination files
        bcf_missing = u'BCF-Missing'
        for fileName, __size, fileCRC in destInstaller.fileSizeCrcs:
            destFileAppend((fileCRC, fileName))
            #--Note files that aren't in any of the source files
            if fileCRC not in srcFiles:
                self.bcf_missing_files.append(fileName)
                srcFiles[fileCRC] = (bcf_missing, fileName)
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
        sProgress(0, f'{bcf_archive}\n' + _('Mapping files…'))
        sProgress.setFull(1 + len(destFiles))
        #--Map the files
        sprog_msg = f'{bcf_archive}\n' + _('Mapping files…') + '\n'
        for index, (fileCRC, fileName) in enumerate(destFiles):
            convertedFileAppend((fileCRC, srcFiles.get(fileCRC), fileName))
            sProgress(index, sprog_msg + fileName)
        #--Build the BCF
        with TempDir() as conv_out:
            if self.bcf_missing_files:
                # We have missing files that we need to extract
                unpack_dir = destInstaller.unpackToTemp(self.bcf_missing_files,
                    SubProgress(progress, lastStep, lastStep + 0.2))
                lastStep += 0.2
                unpack_dir.moveTo(os.path.join(conv_out, bcf_missing))
            self.save(conv_out)
            #--Pack the BCF
            #--BCF's need to be non-Solid since they have to have BCF.dat
            # extracted and read from during runtime
            self.isSolid = False
            archives.compress7z(converters_dir.join(bcf_archive),
                GPath_no_norm(conv_out), SubProgress(progress, lastStep, 1.0),
                is_solid=self.isSolid, blockSize=self.blockSize)
        ##: Why are we setting isSolid to False, then immediately overwriting
        # it here? The comment above claims that they "need to be non-Solid",
        # but this could mark them solid???
        self.isSolid = destInstaller.isSolid

    def _unpack(self, srcInstaller, fileNames, temp_dir: str, *, progress=None,
                __read_ext=tuple(readExts)):
        """Recursive function: completely extracts the source installer to
        a temporary directory. Each archive and sub-archive is extracted to its
        own sub-directory to prevent file thrashing. Requires the temp
        directory to which to extract as a parameter."""
        #--Sanity check
        if not fileNames: raise ArgumentError(
            f'No files to extract for {srcInstaller}.')
        with TempFile(temp_prefix='temp_list', temp_suffix='.txt') as tl:
            #--Dump file list
            try:
                with open(tl, 'w', encoding='utf-8') as out:
                    out.write('\n'.join(fileNames))
            except Exception as e:
                raise StateError(
                    f'Error creating file list for 7z:\nError: {e}') from e
            #--Determine settings for 7z
            installerCRC = srcInstaller.crc
            apath = srcInstaller if isinstance(
                srcInstaller, Path) else srcInstaller.abs_path
            tmp_sub = GPath_no_norm(temp_dir).join(f'{installerCRC:08X}')
            if progress:
                progress(0, f"{apath}\n{_('Extracting files…')}")
                progress.setFull(1 + len(fileNames))
            try:
                subArchives = archives.extract7z(apath, tmp_sub, progress,
                    read_exts=__read_ext, filelist_to_extract=tl)
            finally:
                ##: Why are we doing this at all? We have a ton of extract7z
                # calls, but only two do clearReadOnly afterwards
                bolt.clearReadOnly(tmp_sub)  ##: do this once
        #--Recursively unpack subArchives
        for sub_archive in subArchives:
            # it will also unpack the embedded BCF if any...
            self._unpack(tmp_sub.join(sub_archive), ['*'], temp_dir)
