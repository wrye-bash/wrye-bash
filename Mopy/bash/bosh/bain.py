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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""BAIN backbone classes."""

import collections
import copy
import io
import os
import re
import sys
import time
from binascii import crc32
from functools import partial, wraps
from itertools import groupby
from operator import itemgetter, attrgetter

from . import imageExts, DataStore, BestIniFile, InstallerConverter, \
    ModInfos, ListInfo
from .. import balt, gui # YAK!
from .. import bush, bass, bolt, env, archives
from ..archives import readExts, defaultExt, list_archive, compress7z, \
    extract7z, compressionSettings
from ..bolt import Path, deprint, round_size, GPath, SubProgress, CIstr, \
    LowerDict, AFile, dict_sort, GPath_no_norm, top_level_items
from ..exception import AbstractError, ArgumentError, BSAError, CancelError, \
    InstallerArchiveError, SkipError, StateError, FileError
from ..ini_files import OBSEIniFile

os_sep = os.path.sep

class Installer(ListInfo):
    """Object representing an installer archive, its user configuration, and
    its installation state."""
    #--Member data
    persistent = (u'archive', u'order', u'group', u'modified', u'fsize',
        u'crc', u'fileSizeCrcs', u'type', u'is_active', u'subNames',
        u'subActives', u'dirty_sizeCrc', u'comments', u'extras_dict',
        u'packageDoc', u'packagePic', u'src_sizeCrcDate', u'hasExtraData',
        u'skipVoices', u'espmNots', u'isSolid', u'blockSize', u'overrideSkips',
        u'_remaps', u'skipRefresh', u'fileRootIdex')
    volatile = (u'ci_dest_sizeCrc', u'skipExtFiles', u'skipDirFiles',
        u'status', u'missingFiles', u'mismatchedFiles', u'project_refreshed',
        u'mismatchedEspms', u'unSize', u'espms', u'underrides', u'hasWizard',
        u'espmMap', u'hasReadme', u'hasBCF', u'hasBethFiles',
        u'_dir_dirs_files', u'has_fomod_conf')

    __slots__ = persistent + volatile
    #--Package analysis/porting.
    type_string = _(u'Unrecognized')
    docDirs = {u'screenshots'}
    #--Will be skipped even if hasExtraData == True (bonus: skipped also on
    # scanning the game Data directory)
    dataDirsMinus = {u'bash', u'--'}
    docExts = {u'.txt', u'.rtf', u'.htm', u'.html', u'.doc', u'.docx', u'.odt',
               u'.mht', u'.pdf', u'.css', u'.xls', u'.xlsx', u'.ods', u'.odp',
               u'.ppt', u'.pptx'}
    reReadMe = re.compile(
        r'^.*?([^\\]*)(read[ _]?me|lisez[ _]?moi)([^\\]*)'
        u'(' + u'|'.join(docExts) + u')$', re.I | re.U)
    skipExts = {u'.exe', u'.py', u'.pyc', u'.7z', u'.zip', u'.rar', u'.db',
                u'.ace', u'.tgz', u'.tar', u'.gz', u'.bz2', u'.omod',
                u'.fomod', u'.tb2', u'.lzma', u'.manifest', u'.ckm',
                u'.vortex_backup'}
    skipExts.update(set(readExts))
    scriptExts = {u'.txt', u'.ini', u'.cfg'}
    commonlyEditedExts = scriptExts | {u'.xml'}
    #--Regular game directories - needs update after bush.game has been set
    dataDirsPlus = docDirs | {u'bash patches', u'bashtags', u'ini tweaks',
                              u'docs'}
    # Files that may be installed in top Data/ directory - note that all
    # top-level file extensions commonly found in the wild need to go here,
    # even ones we'll end up skipping, since this is for the detection of
    # archive 'types' - not actually deciding which get installed
    _top_files_extensions = bush.game.espm_extensions | {
        bush.game.Bsa.bsa_extension, u'.ini', u'.modgroups', u'.bsl', u'.ckm'}
    _re_top_extensions = re.compile(u'(?:' + u'|'.join(
        re.escape(ext) for ext in _top_files_extensions) + u')$', re.I)
    # Extensions of strings files - automatically built from game constants
    _strings_extensions = {os.path.splitext(x[1])[1].lower()
                           for x in bush.game.Esp.stringsFiles}
    # InstallersData singleton - consider this tmp
    instData = None # type: InstallersData

    @classmethod
    def is_archive(cls): return False
    @classmethod
    def is_project(cls): return False
    @classmethod
    def is_marker(cls): return False

    @classmethod
    def validate_filename_str(cls, name_str, allowed_exts=frozenset(),
                              use_default_ext=False):
        return super(Installer, cls).validate_filename_str(name_str,
            frozenset()) # block extension check

    @classmethod
    def get_store(cls): return cls.instData

    @staticmethod
    def init_bain_dirs():
        """Initialize BAIN data directories on a per game basis."""
        Installer.dataDirsPlus |= bush.game.Bain.data_dirs
        InstallersData.installers_dir_skips.update(
            {bass.dirs[u'converters'].stail.lower(), u'bash'})
        user_skipped = bass.inisettings[u'SkippedBashInstallersDirs'].split(u'|')
        InstallersData.installers_dir_skips.update(
            skipped.lower() for skipped in user_skipped if skipped)

    tempList = Path.baseTempDir().join(u'WryeBash_InstallerTempList.txt')

    #--Class Methods ----------------------------------------------------------
    @staticmethod
    def getGhosted():
        """Returns map of real to ghosted files in mods directory."""
        dataDir = bass.dirs[u'mods']
        inodes = dataDir.list()
        ghosts = [x.body for x in inodes if x.cext == u'.ghost']
        limbo = set(ghosts) & set(inodes) # they exist in both states
        return bolt.LowerDict(
            (x.s , x.s + u'.ghost') for x in ghosts if x not in limbo)

    @staticmethod
    def final_update(new_sizeCrcDate, old_sizeCrcDate, pending, pending_size,
                     progress, recalculate_all_crcs, rootName):
        """Clear old_sizeCrcDate and update it with new_sizeCrcDate after
        calculating crcs for pending."""
        #--Force update?
        if recalculate_all_crcs:
            pending.update(new_sizeCrcDate)
            pending_size += sum(x[0] for x in new_sizeCrcDate.values())
        changed = bool(pending) or (len(new_sizeCrcDate) != len(old_sizeCrcDate))
        #--Update crcs?
        Installer.calc_crcs(pending, pending_size, rootName,
                            new_sizeCrcDate, progress)
        # drop _asFile
        old_sizeCrcDate.clear()
        for rpFile, (siz, crc, date, _asFile) in new_sizeCrcDate.items():
            old_sizeCrcDate[rpFile] = (siz, crc, date)
        return changed

    @staticmethod
    def calc_crcs(pending, pending_size, rootName, new_sizeCrcDate, progress):
        if not pending: return
        done = 0
        progress_msg= rootName + u'\n' + _(u'Calculating CRCs...') + u'\n'
        progress(0, progress_msg)
        # each mod increments the progress bar by at least one, even if it
        # is size 0 - add len(pending) to the progress bar max to ensure we
        # don't hit 100% and cause the progress bar to prematurely disappear
        progress.setFull(pending_size + len(pending))
        for rpFile, (siz, _crc, date, asFile) in dict_sort(pending):
            progress(done, progress_msg + rpFile)
            sub = bolt.SubProgress(progress, done, done + siz + 1)
            sub.setFull(siz + 1)
            crc = 0
            try:
                with open(asFile, u'rb') as ins:
                    insTell = ins.tell
                    for block in iter(partial(ins.read, 2097152), b''):
                        crc = crc32(block, crc) # 2MB at a time, probably ok
                        sub(insTell())
            except OSError:
                deprint(u'Failed to calculate crc for %s - please report '
                        u'this, and the following traceback:' % asFile,
                        traceback=True)
                continue
            crc &= 0xFFFFFFFF
            done += siz + 1
            new_sizeCrcDate[rpFile] = (siz, crc, date, asFile)

    #--Initialization, etc ----------------------------------------------------
    def initDefault(self):
        """Initialize everything to default values."""
        self.archive = u''
        #--Persistent: set by _refreshSource called by refreshBasic
        self.modified = 0 #--Modified date
        self.fsize = -1 #--size of archive file
        self.crc = 0 #--crc of archive
        self.isSolid = False #--package only - solid 7z archive
        self.blockSize = None #--package only - set here and there
        self.fileSizeCrcs = [] #--list of tuples for _all_ files in installer
        #--For InstallerProject's, cache if refresh projects is skipped
        self.src_sizeCrcDate = bolt.LowerDict()
        #--Set by refreshBasic
        self.fileRootIdex = 0 # len of the root path including the final separator
        self.type = 0 #--Package type: 0: unset/invalid; 1: simple; 2: complex
        self.subNames = []
        self.subActives = []
        self.extras_dict = {} # hack to add more persistent attributes
        #--Set by refreshDataSizeCrc
        self.dirty_sizeCrc = bolt.LowerDict()
        self.packageDoc = self.packagePic = None
        #--User Only
        self.skipVoices = False
        self.hasExtraData = False
        self.overrideSkips = False
        self.skipRefresh = False    # Projects only
        self.comments = u''
        self.group = u'' #--Default from abstract. Else set by user.
        self.order = -1 #--Set by user/interface.
        self.is_active = False
        self.espmNots = set() #--Lowercase plugin file names that user has decided not to install.
        self._remaps = {}
        #--Volatiles (not pickled values)
        #--Volatiles: directory specific
        self.project_refreshed = False
        self._dir_dirs_files = None
        #--Volatile: set by refreshDataSizeCrc
        # LowerDict mapping destinations (relative to Data/ directory) of files
        # in this installer to their size and crc - built in refreshDataSizeCrc
        self.ci_dest_sizeCrc = bolt.LowerDict()
        self.has_fomod_conf = False
        self.hasWizard = False
        self.hasBCF = False
        self.espmMap = bolt.DefaultLowerDict(list)
        self.hasReadme = False
        self.hasBethFiles = False
        self.skipExtFiles = set()
        self.skipDirFiles = set()
        self.espms = set()
        self.unSize = 0
        #--Volatile: set by refreshStatus
        self.status = 0
        self.underrides = set()
        self.missingFiles = set()
        self.mismatchedFiles = set()
        self.mismatchedEspms = set()

    @property
    def num_of_files(self): return len(self.fileSizeCrcs)

    @staticmethod
    def number_string(number, marker_string=u''):
        return str(number)

    def size_string(self): return round_size(self.fsize)

    def size_info_str(self): return  _(u'Size:') + u' %s' % self.size_string()

    def structure_string(self):
        if self.type == 1:
            return _(u'Structure: Simple')
        elif self.type == 2:
            if len(self.subNames) == 2:
                return _(u'Structure: Complex/Simple')
            else:
                return _(u'Structure: Complex')
        elif self.type < 0:
            return _(u'Structure: Corrupt/Incomplete')
        else:
            return _(u'Structure: Unrecognized')

    def resetEspmName(self,currentName):
        oldName = self.getEspmName(currentName)
        del self._remaps[oldName]
        path = GPath(currentName)
        if path in self.espmNots:
            self.espmNots.discard(path)
            self.espmNots.add(GPath(oldName))

    def resetAllEspmNames(self):
        for remapped in list(self._remaps.values()):
            # Need to use list(), since 'resetEspmName' will use
            # del self._remaps[oldName], changing the dictionary size.
            self.resetEspmName(remapped)

    def getEspmName(self,currentName):
        for old, renamed in self._remaps.items():
            if renamed == currentName:
                return old
        return currentName

    def setEspmName(self,currentName,newName):
        oldName = self.getEspmName(currentName)
        self._remaps[oldName] = newName
        path = GPath(currentName)
        if path in self.espmNots:
            self.espmNots.discard(path)
            self.espmNots.add(GPath(newName))
        else:
            self.espmNots.discard(GPath(newName))

    def isEspmRenamed(self,currentName):
        return self.getEspmName(currentName) != currentName

    def __init__(self,archive):
        self.initDefault()
        self.archive = archive.stail

    def __reduce__(self):
        """Used by pickler to save object state."""
        raise AbstractError(f'{type(self)} must define __reduce__')

    def __setstate__(self,values):
        """Used by unpickler to recreate object."""
        try:
            self.__setstate(values)
        except:
            deprint(f'Failed loading {values[0]}', traceback=True)
            # init to default values and let it be picked for refresh in
            # InstallersData#scan_installers_dir
            self.initDefault()

    @property
    def abs_path(self):
        return bass.dirs[u'installers'].join(self.archive)

    def get_hide_dir(self): ##: Copy-pasted from InstallersData.hidden_dir!
        return bass.dirs[u'modsBash'].join(u'Hidden')

    def __setstate(self,values):
        self.initDefault() # runs on __init__ called by __reduce__
        for a, v in zip(self.persistent, values):
            setattr(self, a, v)
        rescan = False
        if not isinstance(self.extras_dict, dict):
            self.extras_dict = {}
            if self.fileRootIdex: # need to add 'root_path' key to extras_dict
                rescan = True
        if not self.abs_path.exists(): # pickled installer deleted outside bash
            return  # don't do anything should be deleted from our data soon
        if not isinstance(self.src_sizeCrcDate, bolt.LowerDict):
            self.src_sizeCrcDate = bolt.LowerDict(
                (u'%s' % x, y) for x, y in self.src_sizeCrcDate.items())
        if not isinstance(self.dirty_sizeCrc, bolt.LowerDict):
            self.dirty_sizeCrc = bolt.LowerDict(
                (u'%s' % x, y) for x, y in self.dirty_sizeCrc.items())
        if not isinstance(self.archive, str):
            deprint(f'{repr(self.archive)} in Installers.dat')
            self.archive = self.archive.decode('utf-8')
        if rescan:
            dest_scr = self.refreshBasic(bolt.Progress(),
                                         recalculate_project_crc=False)
        else:
            dest_scr = self.refreshDataSizeCrc()
        if self.overrideSkips:
            InstallersData.overridden_skips.update(dest_scr)

    def __copy__(self):
        """Create a copy of self -- works for subclasses too (assuming
        subclasses don't add new data members)."""
        clone = self.__class__(GPath(self.archive))
        copier = copy.copy
        getter = object.__getattribute__ ##: is the object. necessary?
        setter = object.__setattr__ ##: is the object. necessary?
        for attr in Installer.__slots__:
            setter(clone,attr,copier(getter(self,attr)))
        return clone

    #--refreshDataSizeCrc, err, framework -------------------------------------
    # Those files/folders will be always skipped by refreshDataSizeCrc()
    _silentSkipsStart = (
        u'--', u'omod conversion data' + os_sep, u'wizard images' + os_sep)
    _silentSkipsEnd = (u'thumbs.db', u'desktop.ini', u'meta.ini',
                       u'__folder_managed_by_vortex')

    # global skips that can be overridden en masse by the installer
    _global_skips = []
    _global_start_skips = []
    _global_skip_extensions = set()
    # executables - global but if not skipped need additional processing
    _executables_ext = {u'.dll', u'.dlx'} | {u'.asi'} | {u'.jar'}
    _executables_process = {}
    _goodDlls = _badDlls = None
    @staticmethod
    def goodDlls(force_recalc=False):
        if Installer._goodDlls is None or force_recalc:
            Installer._goodDlls = collections.defaultdict(list,
                bass.settings[u'bash.installers.goodDlls'])
        return Installer._goodDlls
    @staticmethod
    def badDlls(force_recalc=False):
        if Installer._badDlls is None or force_recalc:
            Installer._badDlls = collections.defaultdict(list,
                bass.settings[u'bash.installers.badDlls'])
        return Installer._badDlls
    # while checking for skips process some installer attributes
    _attributes_process = {}
    _extensions_to_process = set()

    @staticmethod
    def init_global_skips():
        """Update _global_skips with functions deciding if 'fileLower' (docs !)
        must be skipped, based on global settings. Should be updated on boot
        and on flipping skip settings - and nowhere else hopefully."""
        del Installer._global_skips[:]
        del Installer._global_start_skips[:]
        Installer._global_skip_extensions.clear()
        if bass.settings[u'bash.installers.skipTESVBsl']:
            Installer._global_skip_extensions.add(u'.bsl')
        if bass.settings[u'bash.installers.skipScriptSources']:
            Installer._global_skip_extensions.update(
                bush.game.Psc.source_extensions)
        # skips files starting with...
        if bass.settings[u'bash.installers.skipDistantLOD']:
            Installer._global_start_skips.append(u'distantlod')
        if bass.settings[u'bash.installers.skipLandscapeLODMeshes']:
            meshes_lod = os_sep.join((u'meshes', u'landscape', u'lod'))
            Installer._global_start_skips.append(meshes_lod)
        if bass.settings[u'bash.installers.skipScreenshots']:
            Installer._global_start_skips.append(u'screenshots')
        # LOD textures
        skipLODTextures = bass.settings[
            u'bash.installers.skipLandscapeLODTextures']
        skipLODNormals = bass.settings[
            u'bash.installers.skipLandscapeLODNormals']
        skipAllTextures = skipLODTextures and skipLODNormals
        tex_gen = os_sep.join((u'textures', u'landscapelod', u'generated'))
        if skipAllTextures:
            Installer._global_start_skips.append(tex_gen)
        elif skipLODTextures: Installer._global_skips.append(
            lambda f: f.startswith(tex_gen) and not f.endswith(u'_fn.dds'))
        elif skipLODNormals: Installer._global_skips.append(
            lambda f: f.startswith(tex_gen) and f.endswith(u'_fn.dds'))
        # Skipped extensions
        skipObse = not bass.settings[u'bash.installers.allowOBSEPlugins']
        if skipObse:
            Installer._global_start_skips.append(
                bush.game.Se.plugin_dir.lower() + os_sep)
            Installer._global_skip_extensions |= Installer._executables_ext
        if bass.settings[u'bash.installers.skipImages']:
            Installer._global_skip_extensions |= imageExts
        Installer._init_executables_skips()

    @staticmethod
    def init_attributes_process():
        """Populate _attributes_process with functions which decide if the
        file is to be skipped while at the same time update self hasReadme,
        hasWizard, hasBCF attributes. The functions return None to indicate
        that the file should be skipped, else the destination of the file
        relative to the Data/ dir. This invariably is the relative path of
        the file relative to the root of the package except for espms which
        support renaming (beta) and docs (also beta)."""
        reReadMeMatch = Installer.reReadMe.match
        docs_ = u'Docs' + os_sep
        def _process_docs(self, fileLower, full, fileExt, file_relative, sub):
            maReadMe = reReadMeMatch(fileLower)
            if maReadMe: self.hasReadme = full
            # let's hope there is no trailing separator - Linux: test fileLower, full are os agnostic
            rsplit = fileLower.rsplit(os_sep, 1)
            parentDir, fname = (u'', rsplit[0]) if len(rsplit) == 1 else rsplit
            if not self.overrideSkips and bass.settings[
                u'bash.installers.skipDocs'] and not (
                        fname in bush.game.Bain.no_skip) and not (
                        fileExt in bush.game.Bain.no_skip_dirs.get(
                parentDir, [])):
                return None # skip
            dest = file_relative
            if not parentDir:
                archiveRoot = GPath(
                    self.archive).sroot if self._valid_exts_re else self.archive
                if fileLower in {u'masterlist.txt', u'dlclist.txt'}:
                    self.skipDirFiles.add(full)
                    return None # we dont want to install those files
                elif maReadMe:
                    if not (maReadMe.group(1) or maReadMe.group(3)):
                        dest = u''.join((docs_, archiveRoot, fileExt))
                    else:
                        dest = u''.join((docs_, file_relative))
                    # self.extras_dict['readMe'] = dest
                elif fileLower == u'package.txt':
                    dest = self.packageDoc = u''.join(
                        (docs_, archiveRoot, u'.package.txt'))
                else:
                    dest = u''.join((docs_, file_relative))
            return dest
        for ext in Installer.docExts:
            Installer._attributes_process[ext] = _process_docs
        def _process_BCF(self, fileLower, full, fileExt, file_relative, sub):
            if fileLower[-7:-3] == u'-bcf' or u'-bcf-' in fileLower: # DOCS !
                self.hasBCF = full
                return None # skip
            return file_relative
        Installer._attributes_process[defaultExt] = _process_BCF # .7z
        def _process_txt(self, fileLower, full, fileExt, file_relative, sub):
            if fileLower == u'wizard.txt': # first check if it's the wizard.txt
                self.hasWizard = full
                return None # skip
            return _process_docs(self, fileLower, full, fileExt, file_relative,
                                 sub)
        Installer._attributes_process[u'.txt'] = _process_txt
        def _remap_espms(self, fileLower, full, fileExt, file_relative, sub):
            rootLower = file_relative.split(os_sep, 1)
            if len(rootLower) > 1:
                self.skipDirFiles.add(full)
                return None # we dont want to install those files
            if fileLower in bush.game.bethDataFiles:
                self.hasBethFiles = True
                if not self.overrideSkips and not bass.settings[
                    u'bash.installers.autoRefreshBethsoft']:
                    self.skipDirFiles.add(_(u'[Bethesda Content]') + u' ' +
                                          full)
                    return None # FIXME - after renames ?
            file_relative = self._remaps.get(file_relative, file_relative)
            if file_relative not in self.espmMap[sub]: self.espmMap[
                sub].append(file_relative)
            pFile = GPath(file_relative)
            self.espms.add(pFile)
            if pFile in self.espmNots: return None # skip
            return file_relative
        for extension in bush.game.espm_extensions:
            Installer._attributes_process[extension] = _remap_espms
        Installer._extensions_to_process = set(Installer._attributes_process)

    def _init_skips(self):
        voice_dir = os_sep.join((u'sound', u'voice')) + os_sep
        start = [voice_dir] if self.skipVoices else []
        skips, skip_ext = [], set()
        if not self.overrideSkips:
            skips = list(Installer._global_skips)
            start.extend(Installer._global_start_skips)
            skip_ext = Installer._global_skip_extensions
        if start: skips.append(lambda f: f.startswith((tuple(start))))
        skipEspmVoices = not self.skipVoices and {x.cs for x in self.espmNots}
        if skipEspmVoices:
            def _skip_espm_voices(fileLower):
                farPos = fileLower.startswith( # u'sound\\voice\\', 12 chars
                    voice_dir) and fileLower.find(os_sep, 12)
                return farPos > 12 and fileLower[12:farPos] in skipEspmVoices
            skips.append(_skip_espm_voices)
        return skips, skip_ext

    @staticmethod
    def _init_executables_skips():
        goodDlls = Installer.goodDlls()
        badDlls = Installer.badDlls()
        def __skipExecutable(checkOBSE, fileLower, full, archiveRoot, dll_size,
                             crc, desc, ext, exeDir, dialogTitle):
            if not fileLower.startswith(exeDir): return True
            if fileLower in badDlls and [archiveRoot, dll_size, crc] in \
                    badDlls[fileLower]: return True
            if not checkOBSE or fileLower in goodDlls and [archiveRoot,
                dll_size, crc] in goodDlls[fileLower]: return False
            message = Installer._dllMsg(fileLower, full, archiveRoot,
                                        desc, ext, badDlls, goodDlls)
            if not balt.askYes(balt.Link.Frame,message, dialogTitle):
                badDlls[fileLower].append([archiveRoot, dll_size, crc])
                bass.settings[u'bash.installers.badDlls'] = Installer._badDlls
                return True
            goodDlls[fileLower].append([archiveRoot, dll_size, crc])
            bass.settings[u'bash.installers.goodDlls'] = Installer._goodDlls
            return False
        if bush.game.Se.se_abbrev:
            _obse = partial(__skipExecutable,
                    desc=_(u'%s plugin DLL') % bush.game.Se.se_abbrev,
                    ext=(_(u'a dll')),
                    exeDir=(bush.game.Se.plugin_dir.lower() + os_sep),
                    dialogTitle=bush.game.Se.se_abbrev + _(u' DLL Warning'))
            Installer._executables_process[u'.dll'] = \
            Installer._executables_process[u'.dlx'] = _obse
        if bush.game.Sd.sd_abbrev:
            _asi = partial(__skipExecutable,
                   desc=_(u'%s plugin ASI') % bush.game.Sd.long_name,
                   ext=(_(u'an asi')),
                   exeDir=(bush.game.Sd.install_dir.lower() + os_sep),
                   dialogTitle=bush.game.Sd.long_name + _(u' ASI Warning'))
            Installer._executables_process[u'.asi'] = _asi
        if bush.game.Sp.sp_abbrev:
            _jar = partial(__skipExecutable,
                   desc=_(u'%s patcher JAR') % bush.game.Sp.long_name,
                   ext=(_(u'a jar')),
                   exeDir=(bush.game.Sp.install_dir.lower() + os_sep),
                   dialogTitle=bush.game.Sp.long_name + _(u' JAR Warning'))
            Installer._executables_process[u'.jar'] = _jar

    @staticmethod
    def _dllMsg(fileLower, full, archiveRoot, desc, ext, badDlls, goodDlls):
        message = u'\n'.join((
            _(u'This installer (%s) has an %s.'), _(u'The file is %s'),
            _(u'Such files can be malicious and hence you should be very '
              u'sure you know what this file is and that it is legitimate.'),
            _(u'Are you sure you want to install this?'),)) % (
                      archiveRoot, desc, full)
        if fileLower in goodDlls:
            message += _(u' You have previously chosen to install '
                         u'%s by this name but with a different size, '
                         u'crc and or source archive name.') % ext
        elif fileLower in badDlls:
            message += _(u' You have previously chosen to NOT '
                         u'install %s by this name but with a different '
                         u'size, crc and/or source archive name - make '
                         u'extra sure you want to install this one before '
                         u'saying yes.') % ext
        return message

    def refreshDataSizeCrc(self, checkOBSE=False, splitExt=os.path.splitext):
        """Update self.ci_dest_sizeCrc and related variables and return
        dest_src map for install operation. ci_dest_sizeCrc is a dict that maps
        CIstr paths _relative to the Data dir_ (the locations the files will
        end up to if installed) to (size, crc) tuples.

        WIP rewrite
        Used:
         - in __setstate__ to construct the installers from Installers.dat,
         used once (and in full refresh ?)
         - in refreshBasic, after refreshing persistent attributes - track
         call graph from here should be the path that needs optimization (
         irefresh, ShowPanel ?)
         - in InstallersPanel.refreshCurrent()
         - in 2 subclasses' install() and InstallerProject.sync_from_data()
         - in _Installers_Skip._do_installers_refresh()
         - in _RefreshingLink (override skips, HasExtraData, skip voices)
         - in Installer_CopyConflicts
        """
        bain_type    = self.type
        #--Init to empty
        self.has_fomod_conf = False
        self.hasWizard = self.hasBCF = self.hasReadme = False
        self.packageDoc = self.packagePic = None # = self.extras_dict['readMe']
        for attr in {'skipExtFiles','skipDirFiles','espms'}:
            ##: is the object. necessary?
            object.__getattribute__(self,attr).clear()
        dest_src = bolt.LowerDict()
        #--Bad archive?
        if bain_type not in {1,2}: return dest_src
        archiveRoot = GPath(
            self.archive).sroot if self._valid_exts_re else self.archive
        docExts = self.docExts
        dataDirsPlus = self.dataDirsPlus
        dataDirsMinus = self.dataDirsMinus
        skipExts = self.skipExts
        unSize = 0
        bethFiles = bush.game.bethDataFiles
        skips, global_skip_ext = self._init_skips()
        if self.overrideSkips:
            ##: We should split this - Override Skips & Override Redirects
            renameStrings = False
            bethFilesSkip = False
            redirect_scripts = False
        else:
            renameStrings = bush.game.Esp.stringsFiles and bass.settings[
                u'bash.installers.renameStrings']
            bethFilesSkip = not bass.settings[
                u'bash.installers.autoRefreshBethsoft']
            # No need to redirect if these get skipped anyways
            redirect_scripts = (
                    bush.game.Psc.source_redirects
                    and not bass.settings[u'bash.installers.skipScriptSources']
                    and bass.settings[u'bash.installers.redirect_scripts'])
        if renameStrings:
            from . import oblivionIni
            lang = oblivionIni.get_ini_language()
        else: lang = u''
        languageLower = lang.lower()
        hasExtraData = self.hasExtraData
        # exclude u'' from active subpackages
        activeSubs = (
            {x for x, y in zip(self.subNames[1:], self.subActives[1:]) if y}
            if bain_type == 2 else set())
        data_sizeCrc = bolt.LowerDict()
        skipDirFiles = self.skipDirFiles
        skipDirFilesAdd = skipDirFiles.add
        skipDirFilesDiscard = skipDirFiles.discard
        skipExtFilesAdd = self.skipExtFiles.add
        commonlyEditedExts = Installer.commonlyEditedExts
        espmMap = self.espmMap = bolt.DefaultLowerDict(list)
        plugin_extensions = bush.game.espm_extensions
        reReadMeMatch = Installer.reReadMe.match
        #--Scan over fileSizeCrcs
        root_path = self.extras_dict.get(u'root_path', u'')
        rootIdex = len(root_path)
        fm_active = self.extras_dict.get(u'fomod_active', False)
        fm_dict = self.extras_dict.get(u'fomod_dict', {})
        module_config = os.path.join(u'fomod', u'moduleconfig.xml')
        for full,size,crc in self.fileSizeCrcs:
            if rootIdex: # exclude all files that are not under root_dir
                if not full.startswith(root_path): continue
            file_relative = full[rootIdex:]
            fileLower = file_relative.lower()
            if fileLower.startswith( # skip top level '--', etc
                    Installer._silentSkipsStart) or fileLower.endswith(
                    Installer._silentSkipsEnd): continue
            elif fileLower == module_config:
                self.has_fomod_conf = full
                skipDirFilesDiscard(file_relative)
                continue
            fm_present = full in fm_dict
            if fm_active and fm_present:
                # Remap selected FOMOD files to usable paths
                file_relative = fm_dict[full]
                fileLower = file_relative.lower()
            sub = u''
            # Complex archive; skip the logic if FOMOD mode is active (since
            # subpackage selection doesn't (currently) work in FOMOD mode
            # anyways)
            if bain_type == 2 and not fm_active:
                split = file_relative.split(os_sep, 1)
                if len(split) > 1:
                    # redefine file, excluding the subpackage directory
                    sub,file_relative = split
                    fileLower = file_relative.lower()
                    if fileLower.startswith(Installer._silentSkipsStart):
                        continue # skip subpackage level '--', etc
                if sub not in activeSubs:
                    if sub == u'':
                        skipDirFilesAdd(file_relative)
                    # Run a modified version of the normal checks, just
                    # looking for esp's for the wizard espmMap, wizard.txt
                    # and readme's
                    rootLower,fileExt = splitExt(fileLower)
                    rootLower = rootLower.split(os_sep, 1)
                    if len(rootLower) == 1: rootLower = u''
                    else: rootLower = rootLower[0]
                    skip = True
                    sub_esps = espmMap[sub] # add sub key to the espmMap
                    if fileLower == u'wizard.txt':
                        self.hasWizard = full
                        skipDirFilesDiscard(file_relative)
                        continue
                    elif fileExt == defaultExt and (fileLower[-7:-3] == u'-bcf' or u'-bcf-' in fileLower):
                        self.hasBCF = full
                        skipDirFilesDiscard(file_relative)
                        continue
                    elif fileExt in docExts and sub == u'':
                        if not self.hasReadme:
                            if reReadMeMatch(file_relative):
                                self.hasReadme = full
                                skipDirFilesDiscard(file_relative)
                                skip = False
                    elif fileLower in bethFiles:
                        self.hasBethFiles = True
                        skipDirFilesDiscard(file_relative)
                        skipDirFilesAdd(_(u'[Bethesda Content]') + u' ' + file_relative)
                        continue
                    elif not rootLower and fileExt in plugin_extensions:
                        #--Remap espms as defined by the user
                        if file_relative in self._remaps:
                            file_relative = self._remaps[file_relative]
                            # fileLower = file.lower() # not needed will skip
                        if file_relative not in sub_esps: sub_esps.append(file_relative)
                    if skip:
                        continue
            sub_esps = espmMap[sub] #add sub key to the espmMap, needed in belt
            rootLower,fileExt = splitExt(fileLower)
            rootLower = rootLower.split(os_sep, 1)
            if len(rootLower) == 1: rootLower = u''
            else: rootLower = rootLower[0]
            #--Skips
            for lam in skips:
                if lam(fileLower):
                    _out = True
                    break
            else: _out = False
            if _out: continue
            dest = None # destination of the file relative to the Data/ dir
            # process attributes and define destination for docs and images
            # (if not skipped globally)
            if fileExt in Installer._extensions_to_process:
                dest = Installer._attributes_process[fileExt](
                    self, fileLower, full, fileExt, file_relative, sub)
                if dest is None: continue
            if fm_active and not fm_present:
                # Pretend all unselected FOMOD files don't exist, but only
                # after giving them a chance to process up above - that way
                # packages that include both a wizard and an FOMOD installer
                # will work (as well as BCFs)
                continue
            if fileExt in global_skip_ext: continue # docs treated above
            elif fileExt in Installer._executables_process: # and handle execs
                if Installer._executables_process[fileExt](
                        checkOBSE, fileLower, full, archiveRoot, size, crc):
                    continue
            #--Noisy skips
            if fileLower in bethFiles:
                self.hasBethFiles = True
                if bethFilesSkip:
                    skipDirFilesAdd(_(u'[Bethesda Content]') + u' ' + full)
                    continue
            elif not hasExtraData and rootLower and rootLower not in dataDirsPlus:
                skipDirFilesAdd(full)
                continue
            elif hasExtraData and rootLower and rootLower in dataDirsMinus:
                skipDirFilesAdd(full)
                continue
            elif fileExt in skipExts:
                skipExtFilesAdd(full)
                continue
            #--Remap docs, strings
            if dest is None: dest = file_relative
            dest = self._remap_files(
                dest, fileLower, rootLower, fileExt, file_relative,
                data_sizeCrc, archiveRoot, renameStrings, languageLower,
                redirect_scripts)
            if fileExt in commonlyEditedExts: ##: will track all the txt files in Docs/
                InstallersData.track(bass.dirs[u'mods'].join(dest))
            #--Save
            data_sizeCrc[dest] = (size,crc)
            dest_src[dest] = full
            unSize += size
        self.unSize = unSize
        (self.ci_dest_sizeCrc, old_sizeCrc) = (data_sizeCrc, self.ci_dest_sizeCrc)
        #--Update dirty?
        if self.is_active and data_sizeCrc != old_sizeCrc:
            dirty_sizeCrc = self.dirty_sizeCrc
            for filename,sizeCrc in old_sizeCrc.items():
                if filename not in dirty_sizeCrc and sizeCrc != data_sizeCrc.get(filename):
                    dirty_sizeCrc[filename] = sizeCrc
        #--Done (return dest_src for install operation)
        return dest_src

    def _find_root_index(self, _os_sep=os_sep, skips_start=_silentSkipsStart):
        # basically just care for skips and complex/simple packages
        # Sort file names as (dir_path, filename) pairs
        self.fileSizeCrcs.sort(key=lambda x: os.path.split(x[0].lower()))
        #--Find correct starting point to treat as BAIN package
        self.extras_dict.pop(u'root_path', None)
        self.fileRootIdex = 0
        dataDirsPlus = Installer.dataDirsPlus
        layout = {}
        layoutSetdefault = layout.setdefault
        for full, size, crc in self.fileSizeCrcs:
            fileLower = full.lower()
            if fileLower.startswith(skips_start): continue
            frags = full.split(_os_sep)
            if len(frags) == 1:
                # Files in the root of the package, start there
                break
            else:
                dirName = frags[0]
                if dirName not in layout and layout:
                    # A second directory in the archive root, start in the root
                    break
                root = layoutSetdefault(dirName,{u'dirs':{},u'files':False})
                for frag in frags[1:-1]:
                    root = root[u'dirs'].setdefault(frag,{u'dirs':{},u'files':False})
                # the last frag is a file, so its parent dir has files
                root[u'files'] = True
        else:
            if not layout: return
            rootStr = next(iter(layout))
            if rootStr.lower() in dataDirsPlus: return
            root = layout[rootStr]
            rootStr = u''.join((rootStr, _os_sep))
            data_dir = bush.game.mods_dir.lower()
            while True:
                if root[u'files']:
                    # There are files in this folder, call it the starting point
                    break
                rootDirs = root[u'dirs']
                if len(rootDirs) == 1:
                    # Only one subfolder, see if it's either the data folder,
                    # or an accepted Data sub-folder
                    rootDirKey = list(rootDirs)[0]
                    rootDirKeyL = rootDirKey.lower()
                    if rootDirKeyL in dataDirsPlus or rootDirKeyL == data_dir:
                        # Found suitable starting point
                        break
                    # Keep looking deeper
                    root = rootDirs[rootDirKey]
                    rootStr = u''.join((rootStr, rootDirKey, _os_sep))
                else:
                    # Multiple folders, stop here even if it's no good
                    break
            self.extras_dict[u'root_path'] = rootStr # keeps case
            self.fileRootIdex = len(rootStr)

    def _remap_files(self, dest, fileLower, rootLower, fileExt, file_relative,
                     data_sizeCrc, archiveRoot, renameStrings, languageLower,
                     redirect_scripts):
        """Renames and redirects files to other destinations in the Data
        folder."""
        # Redirect docs to the Docs folder
        if rootLower in self.docDirs:
            dest = os_sep.join((u'Docs', file_relative[len(rootLower) + 1:]))
        # Rename strings files if the option is set
        elif (renameStrings and fileExt in self._strings_extensions
              and fileLower.startswith(u'strings' + os_sep)):
            langSep = fileLower.rfind(u'_')
            extSep = fileLower.rfind(u'.')
            lang = fileLower[langSep + 1:extSep]
            if lang != languageLower:
                dest = u''.join((file_relative[:langSep], u'_', lang,
                                 file_relative[extSep:]))
                # Check to ensure not overriding an already provided language
                # file for that language
                if dest in data_sizeCrc:
                    dest = file_relative
        # Redirect script files that are in the wrong place
        elif redirect_scripts and fileExt in bush.game.Psc.source_extensions:
            for old_dir, new_dir in bush.game.Psc.source_redirects.items():
                if fileLower.startswith(old_dir + os_sep):
                    # Note us keeping the path separator in via slicing
                    dest = new_dir + fileLower[len(old_dir):]
                    break
        elif rootLower in self.dataDirsPlus: ##: needed?
            pass
        elif not rootLower:
            if fileLower == u'package.jpg':
                dest = self.packagePic = u''.join(
                    (u'Docs' + os_sep, archiveRoot, u'.package.jpg'))
            elif fileExt in imageExts:
                dest = os_sep.join((u'Docs', file_relative))
        return dest

    def refreshBasic(self, progress, recalculate_project_crc=True):
        return self._refreshBasic(progress, recalculate_project_crc)

    def _refreshBasic(self, progress, recalculate_project_crc=True,
                      _os_sep=os_sep, skips_start=tuple(
                s.replace(os_sep, u'') for s in _silentSkipsStart)):
        """Extract file/size/crc and BAIN structure info from installer."""
        try:
            self._refreshSource(progress, recalculate_project_crc)
        except InstallerArchiveError:
            self.type = -1 # size, modified and some of fileSizeCrcs may be set
            return bolt.LowerDict()
        self._find_root_index()
        # fileRootIdex now points to the start in the file strings to ignore
        #--Type, subNames
        bain_type = 0
        subNameSet = {u''}
        valid_ext = self.__class__._re_top_extensions.search
        dataDirsPlus = self.dataDirsPlus
        # hasExtraData is NOT taken into account when calculating package
        # structure or the root_path
        root_path = self.extras_dict.get(u'root_path', u'')
        for full, size, crc in self.fileSizeCrcs:#break if type=1 else churn on
            if root_path: # exclude all files that are not under root_dir
                if not full.startswith(root_path): continue
                full = full[self.fileRootIdex:]
            if full.lower().startswith(skips_start): continue
            frags = full.split(_os_sep)
            nfrags = len(frags)
            f0_lower = frags[0].lower()
            #--Type 1 ? break ! data files/dirs are not allowed in type 2 top
            if (nfrags == 1 and valid_ext(f0_lower) or
                nfrags > 1 and f0_lower in dataDirsPlus):
                bain_type = 1
                break
            #--Else churn on to see if we have a Type 2 package
            elif not frags[0] in subNameSet and not \
                    f0_lower.startswith(skips_start) and (
                    (nfrags > 2 and frags[1].lower() in dataDirsPlus) or
                    (nfrags == 2 and valid_ext(frags[1]))):
                subNameSet.add(frags[0])
                bain_type = 2
                # keep looking for a type one package - having a loose file or
                # a top directory with name in dataDirsPlus will turn this into
                # a type one package
        self.type = bain_type
        #--SubNames, SubActives
        if bain_type == 2:
            self.subNames = sorted(subNameSet,key=str.lower)
            actives = {x for x, y in zip(self.subNames, self.subActives)
                       if (y or x == u'')}
            if len(self.subNames) == 2: #--If only one subinstall, then make it active.
                self.subActives = [True,True] # that's a complex/simple package
            else:
                self.subActives = [(x in actives) for x in self.subNames]
        else:
            self.subNames = []
            self.subActives = []
        #--Data Size Crc
        return self.refreshDataSizeCrc()

    def refreshStatus(self, installersData):
        """Updates missingFiles, mismatchedFiles and status.
        Status:
        20: installed (green)
        10: mismatches (yellow)
        0: unconfigured (white)
        -10: missing files (red)
        -20: bad type (grey)
        """
        data_sizeCrc = self.ci_dest_sizeCrc
        data_sizeCrcDate = installersData.data_sizeCrcDate
        ci_underrides_sizeCrc = installersData.ci_underrides_sizeCrc
        missing = self.missingFiles
        mismatched = self.mismatchedFiles
        misEspmed = self.mismatchedEspms
        underrides = set()
        status = 0
        missing.clear()
        mismatched.clear()
        misEspmed.clear()
        if self.type == 0:
            status = -20
        elif data_sizeCrc:
            for filename,sizeCrc in data_sizeCrc.items():
                sizeCrcDate = data_sizeCrcDate.get(filename)
                if not sizeCrcDate:
                    missing.add(filename)
                elif sizeCrc != sizeCrcDate[:2]:
                    mismatched.add(filename)
                    if ModInfos.rightFileType(filename):
                        misEspmed.add(filename)
                if sizeCrc == ci_underrides_sizeCrc.get(filename):
                    underrides.add(filename)
            if missing: status = -10
            elif misEspmed: status = 10
            elif mismatched: status = 20
            else: status = 30
        #--Clean Dirty
        dirty_sizeCrc = self.dirty_sizeCrc
        for filename, sizeCrc in list(dirty_sizeCrc.items()):
            sizeCrcDate = data_sizeCrcDate.get(filename)
            if (not sizeCrcDate or sizeCrc != sizeCrcDate[:2] or
                sizeCrc == data_sizeCrc.get(filename)
                ):
                del dirty_sizeCrc[filename]
        #--Done
        (self.status,oldStatus) = (status,self.status)
        (self.underrides,oldUnderrides) = (underrides,self.underrides)
        return self.status != oldStatus or self.underrides != oldUnderrides

    #--Utility methods --------------------------------------------------------
    def packToArchive(self, project, fn_archive, isSolid, blockSize,
                      progress=None, release=False):
        """Packs project to build directory. Release filters out development
        material from the archive. Needed for projects and to repack archives
        when syncing from Data."""
        if not self.num_of_files: return
        fn_archive, archiveType, solid = compressionSettings(
            fn_archive, blockSize, isSolid)
        outDir = bass.dirs[u'installers']
        realOutFile = outDir.join(fn_archive)
        project = outDir.join(project)
        #--Dump file list
        ##: We don't use a BOM for tempList in unpackToTemp...
        with self.tempList.open(u'w', encoding=u'utf-8-sig') as out:
            if release:
                out.write(u'*thumbs.db\n')
                out.write(u'*desktop.ini\n')
                out.write(u'*meta.ini\n')
                out.write(u'--*\\')
        #--Compress
        try:
            compress7z(outDir, realOutFile, fn_archive, project, progress,
                       solid=solid, archiveType=archiveType,
                       temp_list=self.tempList)
        finally:
            self.tempList.remove()

    def _do_sync_data(self, proj_dir, delta_files, progress):
        """Performs a Sync from Data on the specified project directory with
        the specified missing or mismatched files."""
        data_dir_join = bass.dirs[u'mods'].join
        norm_ghost_get = Installer.getGhosted().get
        upt_numb = del_numb = 0
        proj_dir_join = proj_dir.join
        progress.setFull(len(delta_files))
        for rel_src, rel_dest in self.refreshDataSizeCrc().items():
            if rel_src not in delta_files: continue
            progress(del_numb + upt_numb,
                     _(u'Syncing from %s folder...') % bush.game.mods_dir +
                     u'\n' + rel_src)
            full_src = data_dir_join(norm_ghost_get(rel_src, rel_src))
            full_dest = proj_dir_join(rel_dest)
            if not full_src.exists():
                full_dest.remove()
                del_numb += 1
            else:
                full_src.copyTo(full_dest)
                upt_numb += 1
        if upt_numb or del_numb:
            # Remove empty directories from project directory
            empties = set()
            for asDir, sDirs, sFiles in os.walk(proj_dir.s):
                if not (sDirs or sFiles): empties.add(GPath(asDir))
            for empty in empties: empty.removedirs()
            proj_dir.makedirs()  #--In case it just got wiped out.
        return upt_numb, del_numb

    def size_or_mtime_changed(self, apath):
        return (self.fsize, self.modified) != apath.size_mtime()

    def open_readme(self): self._open_txt_file(self.hasReadme)
    def open_wizard(self): self._open_txt_file(self.hasWizard)
    def _open_txt_file(self, rel_path): raise AbstractError
    def wizard_file(self): raise AbstractError
    def fomod_file(self): raise AbstractError

    def __repr__(self):
        return u'%s<%r>' % (self.__class__.__name__, self.archive)

    def __str__(self):
        return self.archive

    #--ABSTRACT ---------------------------------------------------------------
    def _refreshSource(self, progress, recalculate_project_crc):
        """Refresh fileSizeCrcs, size, and modified from source
        archive/directory. fileSizeCrcs is a list of tuples, one for _each_
        file in the archive or project directory. _refreshSource is called
        in refreshBasic only. In projects the src_sizeCrcDate cache is used to
        avoid recalculating crc's.
        :param recalculate_project_crc: only used in InstallerProject override
        """
        raise AbstractError

    def install(self, destFiles, progress=None):
        """Install specified files to Data directory."""
        destFiles = set(destFiles)
        dest_src = self.refreshDataSizeCrc(True)
        for k in list(dest_src):
            if k not in destFiles: del dest_src[k]
        if not dest_src: return bolt.LowerDict(), set(), set(), set()
        progress = progress if progress else bolt.Progress()
        return self._install(dest_src, progress)

    def _install(self, dest_src, progress):
        raise AbstractError

    def _fs_install(self, dest_src, srcDirJoin, progress,
                    subprogressPlus, unpackDir):
        """Filesystem install, if unpackDir is not None we are installing
         an archive."""
        norm_ghostGet = Installer.getGhosted().get
        data_sizeCrcDate_update = bolt.LowerDict()
        data_sizeCrc = self.ci_dest_sizeCrc
        mods, inis, bsas = set(), set(), set()
        source_paths, dests = [], []
        add_source, add_dest = source_paths.append, dests.append
        installer_plugins = self.espms
        is_ini_tweak = InstallersData._is_ini_tweak
        join_data_dir = bass.dirs[u'mods'].join
        bsa_ext = bush.game.Bsa.bsa_extension
        for dest, src in dest_src.items():
            size,crc = data_sizeCrc[dest]
            # Work with ghosts lopped off internally and check the destination,
            # since plugins may have been renamed
            if (dest_path := GPath_no_norm(dest)) in installer_plugins:
                mods.add(dest_path)
            elif ini_name := is_ini_tweak(dest):
                inis.add(GPath_no_norm(ini_name))
            elif dest_path.cext == bsa_ext:
                bsas.add(dest_path)
            data_sizeCrcDate_update[dest] = (size, crc, -1) ##: HACK we must try avoid stat'ing the mtime
            add_source(srcDirJoin(src))
            # Append the ghost extension JIT since the FS operation below will
            # need the exact path to copy to
            add_dest(join_data_dir(norm_ghostGet(dest, dest)))
            subprogressPlus()
        #--Now Move
        try:
            if data_sizeCrcDate_update:
                fs_operation = env.shellMove if unpackDir else env.shellCopy
                fs_operation(source_paths, dests, progress.getParent())
        finally:
            #--Clean up unpack dir if we're an archive
            if unpackDir: bass.rmTempDir()
        #--Update Installers data
        return data_sizeCrcDate_update, mods, inis, bsas

    def listSource(self):
        """Return package structure as text."""
        log = bolt.LogFile(io.StringIO())
        log.setHeader(u'%s ' % self + _(u'Package Structure:'))
        log(u'[spoiler]\n', False)
        self._list_package(self.abs_path, log)
        log(u'[/spoiler]')
        return bolt.winNewLines(log.out.getvalue())

    @staticmethod
    def _list_package(apath, log): raise AbstractError

    def renameInstaller(self, name_new, idata_):
        """Rename installer and return a three tuple specifying if a refresh in
        mods and ini lists is needed. name_new must be tested (via unique name)
        otherwise we will overwrite! Currently only called in rename_operation
        from InstallersList.try_rename - this passes a unique name in.
        :rtype: tuple"""
        super(InstallersData, idata_).rename_operation(self, name_new)
        #--Update the iniInfos & modInfos for 'installer'
        from . import modInfos, iniInfos
        ##: self.archive still the old value (should be set in super but no "name" attr)
        mfiles = [x for x in modInfos.table.getColumn(u'installer') if
                  modInfos.table[x][u'installer'] == self.archive] ##: ci comparison!
        ifiles = [x for x in iniInfos.table.getColumn(u'installer') if
                  iniInfos.table[x][u'installer'] == self.archive]
        for i in mfiles:
            modInfos.table[i][u'installer'] = name_new.s
        for i in ifiles:
            iniInfos.table[i][u'installer'] = name_new.s
        return True, bool(mfiles), bool(ifiles)

    def sync_from_data(self, delta_files, progress):
        """Updates this installer according to the specified files in the Data
        directory.

        :param delta_files: The missing or mismatched files to sync.
        :type delta_files: set[bolt.CIstr]"""
        raise AbstractError

    # Factory -----------------------------------------------------------------
    @classmethod
    def refresh_installer(cls, package, idata, progress, install_order=None,
                          do_refresh=False, _index=None, _fullRefresh=False):
        installer = idata.get(package)
        if not installer:
            installer = idata[package] = cls(package)
            if install_order is not None:
                idata.moveArchives([package], install_order)
        if _index is not None:
            progress = SubProgress(progress, _index, _index + 1)
        installer.refreshBasic(progress, recalculate_project_crc=_fullRefresh)
        if progress: progress(1.0, _(u'Done'))
        if do_refresh:
            idata.irefresh(what=u'NS')
        return installer

#------------------------------------------------------------------------------
class InstallerMarker(Installer):
    """Represents a marker installer entry."""
    __slots__ = tuple() #--No new slots
    type_string = _(u'Marker')
    _is_filename = False

    @staticmethod
    def _new_name(base_name, count):
        cnt_str = (u' (%d)' % count) if count else u''
        return GPath_no_norm(u'==' + base_name.s.strip(u'=') + cnt_str + u'==')

    def unique_key(self, new_root, ext=u'', add_copy=False):
        new_name = GPath_no_norm(new_root + (_(u' Copy') if add_copy else u''))
        if new_name.s == self.ci_key.s: # allow change of case
            return None
        return self.unique_name(new_name)

    @classmethod
    def is_marker(cls): return True

    @classmethod
    def rename_area_idxs(cls, text_str, start=0, stop=None):
        """Markers, change the selection to not include the '=='."""
        if text_str[:2] == text_str[-2:] == u'==':
            return 2, len(text_str) - 2
        return 0, len(text_str)

    def __init__(self, marker_key):
        Installer.__init__(self, marker_key)
        self.modified = time.time()

    def __reduce__(self):
        from . import InstallerMarker as boshInstallerMarker
        return boshInstallerMarker, (GPath(self.archive),), tuple(
            getattr(self, a) for a in self.persistent)

    @property
    def num_of_files(self): return -1

    @staticmethod
    def number_string(number, marker_string=u''): return marker_string

    def size_string(self): return u''

    def size_info_str(self): return  _(u'Size:') + u' N/A\n'

    def structure_string(self): return _(u'Structure: N/A')

    def _refreshSource(self, progress, recalculate_project_crc):
        """Marker: size is -1, fileSizeCrcs empty, modified = creation time."""
        pass

    def install(self, destFiles, progress=None):
        """Install specified files to Data directory."""
        pass

    def renameInstaller(self, name_new, idata_):
        return True, False, False

    def refreshBasic(self, progress, recalculate_project_crc=True):
        return bolt.LowerDict()

#------------------------------------------------------------------------------
class InstallerArchive(Installer):
    """Represents an archive installer entry."""
    __slots__ = tuple() #--No new slots
    type_string = _(u'Archive')
    _valid_exts_re = r'(\.(?:' + '|'.join(
        ext[1:] for ext in archives.readExts) + '))'

    @classmethod
    def is_archive(cls): return True

    def size_info_str(self):
        if self.isSolid:
            if self.blockSize:
                sSolid = _(u'Solid, Block Size: %d MB') % self.blockSize
            elif self.blockSize is None:
                sSolid = _(u'Solid, Block Size: Unknown')
            else:
                sSolid = _(u'Solid, Block Size: 7z Default')
        else:
            sSolid = _(u'Non-solid')
        return _(u'Size: %s (%s)') % (self.size_string(), sSolid)

    @classmethod
    def validate_filename_str(cls, name_str, allowed_exts=archives.writeExts,
                              use_default_ext=False, __7z=archives.defaultExt):
        r, e = os.path.splitext(name_str)
        if allowed_exts and e.lower() not in allowed_exts:
            if not use_default_ext: # renaming as opposed to creating the file
                return _(u'%s does not have correct extension (%s).') % (
                    name_str, u', '.join(allowed_exts)), None
            msg = _(u'The %s extension is unsupported. Using %s instead.') % (
                e, __7z)
            name_str, e = r + __7z, __7z
        else: msg = u''
        name_path, root = super(Installer, cls).validate_filename_str(name_str,
                                                                      {e})
        if root is None:
            return name_path, None
        if msg: # propagate the msg for extension change
            return name_path, (root, msg)
        return name_path, root

    def __reduce__(self):
        from . import InstallerArchive as boshInstallerArchive
        return boshInstallerArchive, (GPath(self.archive),), tuple(
            getattr(self, a) for a in self.persistent)

    #--File Operations --------------------------------------------------------
    def _refreshSource(self, progress, recalculate_project_crc):
        """Refresh fileSizeCrcs, size, modified, crc, isSolid from archive."""
        #--Basic file info
        self.fsize, self.modified = self.abs_path.size_mtime() ##: aka _file_mod_time
        #--Get fileSizeCrcs
        fileSizeCrcs = self.fileSizeCrcs = []
        self.isSolid = False
        filepath = listed_size = listed_crc = isdir_ = cumCRC = 0
        def _parse_archive_line(key, value):
            nonlocal filepath, listed_size, listed_crc, isdir_, cumCRC
            if   key == u'Solid': self.isSolid = (value[0] == u'+')
            elif key == u'Path': filepath = value
            elif key == u'Size': listed_size = int(value)
            elif key == u'Attributes': isdir_ = value and (u'D' in value)
            elif key == u'CRC' and value: listed_crc = int(value,16)
            elif key == u'Method':
                if filepath and not isdir_ and filepath != \
                        self.abs_path.s:
                    fileSizeCrcs.append((filepath, listed_size, listed_crc))
                    cumCRC += listed_crc
                filepath = listed_size = listed_crc = isdir_ = 0
        try:
            list_archive(self.abs_path, _parse_archive_line)
            self.crc = cumCRC & 0xFFFFFFFF
        except:
            archive_msg = f"Unable to read archive '{self.abs_path}'."
            deprint(archive_msg, traceback=True)
            raise InstallerArchiveError(archive_msg)

    def unpackToTemp(self, fileNames, progress=None, recurse=False):
        """Erases all files from self.tempDir and then extracts specified files
        from archive to self.tempDir. progress will be zeroed so pass a
        SubProgress in.
        fileNames: File names (not paths)."""
        if not fileNames:
            raise ArgumentError(u'No files to extract for %s.' % self)
        # expand wildcards in fileNames to get actual count of files to extract
        #--Dump file list
        with self.tempList.open(u'w', encoding=u'utf8') as out:
            out.write(u'\n'.join(fileNames))
        #--Ensure temp dir empty
        bass.rmTempDir()
        if progress:
            progress.state = 0
            progress.setFull(len(fileNames))
        #--Extract files
        unpack_dir = bass.getTempDir()
        try:
            extract7z(self.abs_path, unpack_dir, progress, recursive=recurse,
                      filelist_to_extract=self.tempList.s)
        finally:
            self.tempList.remove()
            bolt.clearReadOnly(unpack_dir)
        #--Done -> don't clean out temp dir, it's going to be used soon
        return unpack_dir

    def _install(self, dest_src, progress):
        #--Extract
        progress(0, (u'%s\n' % self) + _(u'Extracting files...'))
        unpackDir = self.unpackToTemp(list(dest_src.values()),
                                      SubProgress(progress, 0, 0.9))
        #--Rearrange files
        progress(0.9, (u'%s\n' % self) + _(u'Organizing files...'))
        srcDirJoin = unpackDir.join
        subprogress = SubProgress(progress,0.9,1.0)
        subprogress.setFull(len(dest_src))
        subprogressPlus = subprogress.plus
        return self._fs_install(dest_src, srcDirJoin, progress,
                                subprogressPlus, unpackDir)

    def unpackToProject(self, project, progress=None):
        """Unpacks archive to build directory."""
        progress = progress or bolt.Progress()
        files = bolt.sortFiles([x[0] for x in self.fileSizeCrcs])
        if not files: return 0
        #--Clear Project
        destDir = bass.dirs[u'installers'].join(project)
        destDir.rmtree(safety=u'Installers')
        #--Extract
        progress(0, f'{project}\n' + _(u'Extracting files...'))
        unpack_dir = self.unpackToTemp(files, SubProgress(progress, 0, 0.9))
        #--Move
        progress(0.9, f'{project}\n' + _(u'Moving files...'))
        count = 0
        tempDirJoin = unpack_dir.join
        destDirJoin = destDir.join
        for file_ in files:
            srcFull = tempDirJoin(file_)
            destFull = destDirJoin(file_)
            try:
                srcFull.moveTo(destFull) # will try and clean read only flag
                count += 1
            except StateError: # Path does not exist
                pass
        bass.rmTempDir()
        return count

    @staticmethod
    def _list_package(apath, log):
        list_text = []
        filepath = u''
        def _parse_archive_line(key, value):
            nonlocal filepath
            if key == u'Path':
                filepath = value
            elif key == u'Attributes':
                list_text.append(  # attributes may be empty
                    (f'{filepath}', value and (u'D' in value)))
            elif key == u'Method':
                filepath = u''
        list_archive(apath, _parse_archive_line)
        list_text.sort()
        #--Output
        for node, isdir_ in list_text:
            log(u'  ' * node.count(os.sep) + os.path.split(node)[1] + (
                os.sep if isdir_ else u''))

    def _open_txt_file(self, rel_path):
        with gui.BusyCursor():
            # This is going to leave junk temp files behind...
            try:
                unpack_dir = self.unpackToTemp([rel_path])
                unpack_dir.join(rel_path).start()
            except OSError:
                # Don't clean up temp dir here.  Sometimes the editor
                # That starts to open the wizard.txt file is slower than
                # Bash, and the file will be deleted before it opens.
                # Just allow Bash's atexit function to clean it when quitting.
                pass

    def _extract_wizard_files(self, wizard_file_name, wizard_prog_title):
        with balt.Progress(wizard_prog_title, u'\n' + u' ' * 60,
                           abort=True) as progress:
            # Extract the wizard, and any images as well
            files_to_extract = [wizard_file_name]
            files_to_extract.extend(x for (x, _s, _c) in self.fileSizeCrcs if
                                    x.lower().endswith((
                                        u'bmp', u'jpg', u'jpeg', u'png',
                                        u'gif', u'pcx', u'pnm', u'tif',
                                        u'tiff', u'tga', u'iff', u'xpm',
                                        u'ico', u'cur', u'ani',)))
            unpack_dir = self.unpackToTemp(files_to_extract, progress,
                                           recurse=True)
        return unpack_dir.join(wizard_file_name)

    def wizard_file(self):
        return self._extract_wizard_files(self.hasWizard,
                                          _(u'Extracting wizard files...'))

    def fomod_file(self):
        return self._extract_wizard_files(self.has_fomod_conf,
                                          _(u'Extracting FOMOD files...'))

    def sync_from_data(self, delta_files, progress):
        # Extract to a temp project, then perform the sync as if it were a
        # regular project and finally repack
        unpack_dir = self.unpackToTemp([x[0] for x in self.fileSizeCrcs],
            recurse=True, progress=SubProgress(progress, 0.1, 0.4))
        upt_numb, del_numb = self._do_sync_data(
            unpack_dir, delta_files, progress=SubProgress(progress, 0.4, 0.5))
        self.packToArchive(unpack_dir, self.writable_archive_name(),
                           isSolid=True, blockSize=None,
                           progress=SubProgress(progress, 0.5, 1.0))
        bass.rmTempDir()
        return upt_numb, del_numb

    def writable_archive_name(self):
        """Returns a version of the name of this archive with the file
        extension changed to be writable (i.e. zip or 7z), if it isn't
        already."""
        archive_name = GPath(self.archive)
        new_ext = (archive_name.cext if archive_name.cext in archives.writeExts
                   else archives.defaultExt)
        return archive_name.root + new_ext

#------------------------------------------------------------------------------
class InstallerProject(Installer):
    """Represents a directory/build installer entry."""
    __slots__ = tuple() #--No new slots
    type_string = _(u'Project')

    @classmethod
    def is_project(cls): return True

    @staticmethod
    def _new_name(base_name, count):
        return f'{base_name} ({count})' if count else base_name

    def __reduce__(self):
        from . import InstallerProject as boshInstallerProject
        return boshInstallerProject, (GPath(self.archive),), tuple(
            getattr(self, a) for a in self.persistent)

    def _refresh_from_project_dir(self, progress=None,
                                  recalculate_all_crcs=False):
        """Update src_sizeCrcDate cache from project directory. Used by
        _refreshSource() to populate the project's src_sizeCrcDate with
        _all_ files present in the project dir. src_sizeCrcDate is then used
        to populate fileSizeCrcs, used to populate ci_dest_sizeCrc in
        refreshDataSizeCrc. Compare to InstallersData._refresh_from_data_dir.
        :return: max modification time for files/folders in project directory
        :rtype: int"""
        #--Scan for changed files
        apRoot = self.abs_path
        rootName = apRoot.stail
        progress = progress if progress else bolt.Progress()
        progress_msg = rootName + u'\n' + _(u'Scanning...')
        progress(0, progress_msg + u'\n')
        progress.setFull(1)
        asRoot = apRoot.s
        relPos = len(asRoot) + 1
        max_mtime = apRoot.mtime
        pending, pending_size = bolt.LowerDict(), 0
        new_sizeCrcDate = bolt.LowerDict()
        oldGet = self.src_sizeCrcDate.get
        walk = self._dir_dirs_files if self._dir_dirs_files is not None else os.walk(asRoot)
        for asDir, __sDirs, sFiles in walk:
            rsDir = asDir[relPos:]
            progress(0.05, progress_msg + (u'\n%s' % rsDir))
            get_mtime = os.path.getmtime(asDir)
            max_mtime = max_mtime if max_mtime >= get_mtime else get_mtime
            for sFile in sFiles:
                asFile = os.path.join(asDir, sFile)
                if len(asFile) > 255: continue # FIXME(inf) hacky workaround
                rpFile = os.path.join(rsDir, sFile)
                # below calls may now raise even if "werr.winerror = 123"
                lstat = os.lstat(asFile)
                size, date = lstat.st_size, lstat.st_mtime
                max_mtime = max_mtime if max_mtime >= date else date
                oSize, oCrc, oDate = oldGet(rpFile, (0, 0, 0))
                if size == oSize and date == oDate:
                    new_sizeCrcDate[rpFile] = (oSize, oCrc, oDate, asFile)
                else:
                    pending[rpFile] = (size, oCrc, date, asFile)
                    pending_size += size
        Installer.final_update(new_sizeCrcDate, self.src_sizeCrcDate, pending,
                               pending_size, progress, recalculate_all_crcs,
                               rootName)
        #--Done
        return max_mtime

    def size_or_mtime_changed(self, apath, _lstat=os.lstat):
        #FIXME(ut): getmtime(True) won't detect all changes - for instance COBL
        # has 3/25/2020 8:02:00 AM modification time if unpacked and no
        # amount of internal shuffling won't change its apath.getmtime(True)
        getM, join = os.path.getmtime, os.path.join
        c, proj_size = [], 0
        cExtend, cAppend = c.extend, c.append
        self._dir_dirs_files = []
        for root, d, files in os.walk(apath.s):
            cAppend(getM(root))
            lstats = [_lstat(join(root, f)) for f in files]
            cExtend(ls.st_mtime for ls in lstats)
            proj_size += sum(ls.st_size for ls in lstats)
            self._dir_dirs_files.append((root, [], files)) # dirs is unused
        if self.fsize != proj_size: return True
        # below is for the fix me - we need to add mtimes_str_crc extra persistent attribute to Installer
        # c.sort() # is this needed or os.walk will return the same order during program run
        # mtimes_str = b'.'.join([bytes(x) for x in c])
        # mtimes_str_crc = crc32(mtimes_str)
        try:
            mtime = max(c)
        except ValueError: # int(max([]))
            mtime = 0.0
        return self.modified != mtime

    def _refreshSource(self, progress, recalculate_project_crc):
        """Refresh src_sizeCrcDate, fileSizeCrcs, size, modified, crc from
        project directory, set project_refreshed to True."""
        self.modified = self._refresh_from_project_dir(progress,
                                                       recalculate_project_crc)
        cumCRC = 0
##        cumDate = 0
        cumSize = 0
        fileSizeCrcs = self.fileSizeCrcs = []
        for path, (size, crc, date) in self.src_sizeCrcDate.items():
            fileSizeCrcs.append((path, size, crc))
##            cumDate = max(date,cumDate)
            cumCRC += crc
            cumSize += size
        self.fsize = cumSize
        self.crc = cumCRC & 0xFFFFFFFF
        self.project_refreshed = True

    def _install(self, dest_src, progress):
        progress.setFull(len(dest_src))
        progress(0, (u'%s\n' % self) + _(u'Moving files...'))
        progressPlus = progress.plus
        #--Copy Files
        srcDirJoin = self.abs_path.join
        return self._fs_install(dest_src, srcDirJoin, progress, progressPlus,
                                None)

    def sync_from_data(self, delta_files, progress):
        return self._do_sync_data(self.abs_path, delta_files, progress)

    @staticmethod
    def _list_package(apath, log):
        def walkPath(folder, depth):
            r, folders, files = next(os.walk(folder))
            indent = u' ' * depth
            for f in sorted(files):
                log(f'{indent}{f}')
            for d in sorted(folders):
                log(f'{indent}{d}\\')
                depth += 2
                walkPath(os.path.join(r, d), depth)
                depth -= 2
        walkPath(apath.s, 0)

    def _open_txt_file(self, rel_path): self.abs_path.join(rel_path).start()

    def wizard_file(self): return self.abs_path.join(self.hasWizard)

    def fomod_file(self): return self.abs_path.join(self.has_fomod_conf)

def projects_walk_cache(func): ##: HACK ! Profile
    """Decorator to make sure I dont leak self._dir_dirs_files project cache.
    Must decorate all methods that may call size_or_mtime_changed (only
    called in scan_installers_dir). For self._dir_dirs_files to be of any use
    the call to scan_installers_dir must be followed by refreshBasic calls
    on the projects."""
    @wraps(func)
    def _projects_walk_cache_wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        finally:
            it = (self.values() if isinstance(self, InstallersData) else
                  self.listData.values())
            for project in it:
                if project.is_project():
                    project._dir_dirs_files = None
    return _projects_walk_cache_wrapper

#------------------------------------------------------------------------------
class InstallersData(DataStore):
    """Installers tank data. This is the data source for the InstallersList."""
    # track changes in installed mod inis etc _in the game Data/ dir_ and
    # deletions of mods/Ini Tweaks. Keys are absolute paths (so we can track
    # ini deletions from Data/Ini Tweaks as well as mods/xmls etc in Data/)
    _miscTrackedFiles = {}
    # we only scan Data dir on first refresh - therefore we need be informed
    # for updates/deletions that happen outside our control - mods/inis/bsas
    _externally_deleted = set()
    _externally_updated = set()
    # cache with paths in Data/ that would be skipped but are not, due to
    # an installer having the override skip etc flag on - when turning the skip
    # off leave the files here - will be cleaned on restart (files will show
    # as dirty till then, but to remove them we should examine all installers
    # that override skips - not worth the hassle)
    overridden_skips = set() # populate with CIstr !
    __clean_overridden_after_load = True
    installers_dir_skips = set()

    def __init__(self):
        self.store_dir = bass.dirs[u'installers']
        self.bash_dir.makedirs()
        #--Persistent data
        self.dictFile = bolt.PickleDict(self.bash_dir.join(u'Installers.dat'))
        self._data = {}
        self.data_sizeCrcDate = bolt.LowerDict()
        from . import converters
        self.converters_data = converters.ConvertersData(bass.dirs[u'bainData'],
            bass.dirs[u'converters'], bass.dirs[u'dupeBCFs'],
            bass.dirs[u'corruptBCFs'], bass.dirs[u'installers'])
        #--Volatile
        self.ci_underrides_sizeCrc = bolt.LowerDict() # underridden files
        self.bcfPath_sizeCrcDate = {}
        self.hasChanged = False
        self.loaded = False
        self.lastKey = GPath(u'==Last==')
        # Need to delay the main bosh import until here
        from . import InstallerArchive, InstallerProject
        self._inst_types = [InstallerArchive, InstallerProject]

    @property
    def bash_dir(self): return bass.dirs[u'bainData']

    @property
    def hidden_dir(self): return bass.dirs[u'modsBash'].join(u'Hidden')

    def add_marker(self, marker_name, order):
        from . import InstallerMarker
        self[marker_name] = InstallerMarker(marker_name)
        if order is None:
            order = self[self.lastKey].order
        self.moveArchives([marker_name], order)

    def setChanged(self,hasChanged=True):
        """Mark as having changed."""
        self.hasChanged = hasChanged

    def refresh(self, *args, **kwargs): return self.irefresh(*args, **kwargs)

    def irefresh(self, progress=None, what=u'DIONSC', fullRefresh=False,
                 refresh_info=None, deleted=None, pending=None, projects=None):
        progress = progress or bolt.Progress()
        #--Archive invalidation
        from . import oblivionIni, InstallerMarker, modInfos
        if bass.settings[u'bash.bsaRedirection'] and oblivionIni.abs_path.exists():
            oblivionIni.setBsaRedirection(True)
        #--Load Installers.dat if not loaded - will set changed to True
        changed = not self.loaded and self.__load(progress)
        #--Last marker
        if self.lastKey not in self:
            self[self.lastKey] = InstallerMarker(self.lastKey)
        if fullRefresh: # BAIN uses modInfos crc cache
            with gui.BusyCursor(): modInfos.refresh_crcs()
        #--Refresh Other - FIXME(ut): docs
        if u'D' in what:
            changed |= self._refresh_from_data_dir(progress, fullRefresh)
        if u'I' in what: changed |= self._refreshInstallers(
            progress, fullRefresh, refresh_info, deleted, pending, projects)
        if u'O' in what or changed: changed |= self.refreshOrder()
        if u'N' in what or changed: changed |= self.refreshNorm()
        if u'S' in what or changed: changed |= self.refreshInstallersStatus()
        if u'C' in what or changed: changed |= \
            self.converters_data.refreshConverters(progress, fullRefresh)
        #--Done
        if changed: self.hasChanged = True
        return changed

    def __load(self, progress):
        progress(0, _(u'Loading Data...'))
        self.dictFile.load()
        self.converters_data.load()
        pickl_data = self.dictFile.pickled_data
        self._data = pickl_data.get(u'installers', {})
        pickle = pickl_data.get(u'sizeCrcDate', {})
        self.data_sizeCrcDate = bolt.LowerDict(pickle) if not isinstance(
            pickle, bolt.LowerDict) else pickle
        # fixup: all markers had their archive attribute set to u'===='
        for key, value in self.items():
            if value.is_marker():
                value.archive = key.s
        self.loaded = True
        return True

    def save(self):
        """Saves to pickle file."""
        if self.hasChanged:
            self.dictFile.pickled_data[u'installers'] = self._data
            self.dictFile.pickled_data[u'sizeCrcDate'] = self.data_sizeCrcDate
            self.dictFile.vdata[u'version'] = 2
            self.dictFile.save()
            self.converters_data.save()
            self.hasChanged = False

    def rename_operation(self, member_info, newName):
        rename_tuple = member_info.renameInstaller(newName, self)
        if rename_tuple:
            del self[member_info.ci_key]
            member_info.archive = newName.s
            self[newName] = member_info
        return rename_tuple

    #--Dict Functions ---------------------------------------------------------
    def files_to_delete(self, filenames, **kwargs):
        toDelete = []
        markers = []
        for item in filenames:
            if item == self.lastKey: continue
            if self[item].is_marker(): markers.append(item)
            else: toDelete.append(self.store_dir.join(item))
        return toDelete, markers

    def _delete_operation(self, paths, markers, **kwargs):
        for m in markers: del self[m]
        super(InstallersData, self)._delete_operation(paths, markers, **kwargs)

    def delete_refresh(self, deleted, markers, check_existence):
        deleted = {item.tail for item in deleted
                   if not check_existence or not item.exists()}
        if deleted:
            self.irefresh(what=u'I', deleted=deleted)
        elif markers:
            self.refreshOrder()

    def copy_installer(self, item, destName):
        """Copies archive to new location."""
        if item == self.lastKey: return
        apath = self.store_dir.join(item)
        apath.copyTo(self.store_dir.join(destName))
        self[destName] = installer = copy.copy(self[item])
        installer.archive = destName.s
        installer.is_active = False
        self.moveArchives([destName], self[item].order + 1)

    def move_info(self, filename, destDir):
        # hasty method to use in UIList.hide(), see FileInfos.move_info()
        self.store_dir.join(filename).moveTo(destDir.join(filename))

    def move_infos(self, sources, destinations, window, bash_frame):
        moved = super(InstallersData, self).move_infos(sources, destinations,
                                                       window, bash_frame)
        self.irefresh(what=u'I', pending=moved)
        return moved

    #--Refresh Functions ------------------------------------------------------
    class _RefreshInfo(object):
        """Refresh info for Bash Installers directory."""
        def __init__(self, deleted=(), pending=(), projects=()):
            self.deleted = frozenset(deleted or ())   # deleted keys
            self.pending = frozenset(pending or ())   # new or updated keys
            self.projects = frozenset(projects or ()) # all project keys

        def refresh_needed(self):
            return bool(self.deleted or self.pending)

    @projects_walk_cache
    def _refreshInstallers(self, progress, fullRefresh, refresh_info, deleted,
                           pending, projects):
        """Update given installers or scan the installers' directory. Any of
        deleted, pending takes priority over refresh_info. If all refresh
        parameters are None, the Installers dir will be scanned for changes.
        Note that if any of those are not None "changed" will be always
        True, triggering the rest of the refreshes in irefresh. Once
        refresh_info is calculated, deleted are removed, refreshBasic is
        called on added/updated files.
        :type progress: bolt.Progress | None
        :type fullRefresh: bool
        :type refresh_info: InstallersData._RefreshInfo | None
        :type deleted: collections.Iterable[bolt.Path] | None
        :type pending: collections.Iterable[bolt.Path] | None
        :type projects: collections.Iterable[bolt.Path] | None
        """
        # TODO(ut):we need to return the refresh_info for more granular control
        # in irefresh and also add extra processing for deleted files
        progress = progress or bolt.Progress()
        #--Current archives
        if refresh_info is deleted is pending is None:
            refresh_info = self.scan_installers_dir(
                *top_level_items(bass.dirs[u'installers'].s), fullRefresh)
        elif refresh_info is None:
            refresh_info = self._RefreshInfo(deleted, pending, projects)
        changed = refresh_info.refresh_needed()
        for deleted in refresh_info.deleted:
            self.pop(deleted)
        pending, projects = refresh_info.pending, refresh_info.projects
        #--New/update crcs?
        for subPending, inst_type in zip(
                (pending - projects, pending & projects), self._inst_types):
            if not subPending: continue
            progress(0,_(u'Scanning Packages...'))
            progress.setFull(len(subPending))
            for index,package in enumerate(sorted(subPending)):
                progress(index, _(u'Scanning Packages...') + u'\n%s' % package)
                inst_type.refresh_installer(package, self, progress,
                    _index=index, _fullRefresh=fullRefresh)
        return changed

    def applyEmbeddedBCFs(self, installers=None, destArchives=None,
                          progress=bolt.Progress()):
        if installers is None:
            installers = [x for x in self.values() if
                          x.is_archive() and x.hasBCF]
        if not installers: return [], []
        if not destArchives:
            destArchives = [GPath(u'[Auto applied BCF] %s' % x) for x
                            in installers]
        progress.setFull(len(installers))
        pending = []
        for i, (installer, destArchive) in [*enumerate(zip(installers,
                destArchives))]: # we may modify installers below
            progress(i, installer.archive)
            #--Extract the embedded BCF and move it to the Converters folder
            unpack_dir = installer.unpackToTemp([installer.hasBCF],
                SubProgress(progress, i, i + 0.5))
            srcBcfFile = unpack_dir.join(installer.hasBCF)
            bcfFile = bass.dirs[u'converters'].join(u'temp-' + srcBcfFile.stail)
            srcBcfFile.moveTo(bcfFile)
            bass.rmTempDir()
            #--Create the converter, apply it
            converter = InstallerConverter(bcfFile.tail)
            try:
                msg = u'%s: ' % destArchive + _(
                    u'An error occurred while applying an Embedded BCF.')
                self.apply_converter(converter, destArchive,
                                     SubProgress(progress, i + 0.5, i + 1.0),
                                     msg, installer, pending,
                                     crc_installer={installer.crc: installer})
            except StateError:
                # maybe short circuit further attempts to extract
                # installer.hasBCF = False
                installers.remove(installer)
            finally: bcfFile.remove()
        self.irefresh(what=u'I', pending=pending)
        return pending, list(GPath(x.archive) for x in installers)

    def apply_converter(self, converter, destArchive, progress, msg,
                        installer=None, pending=None, show_warning=None,
                        position=-1, crc_installer=None):
        try:
            converter.apply(destArchive, crc_installer,
                            bolt.SubProgress(progress, 0.0, 0.99),
                            embedded=installer.crc if installer else 0)
            #--Add the new archive to Bash
            if destArchive not in self:
                self[destArchive] = InstallerArchive(destArchive)
                reorder = True
            else: reorder = False
            #--Apply settings from the BCF to the new InstallerArchive
            iArchive = self[destArchive]
            converter.applySettings(iArchive)
            if reorder and position >= 0:
                self.moveArchives([destArchive], position)
            elif reorder and installer: #embedded BCF, move after its installer
                self.moveArchives([destArchive], installer.order + 1)
            if pending is not None: # caller must take care of the else below !
                pending.append(destArchive)
            else:
                self.irefresh(what=u'I', pending=[destArchive])
                return iArchive
        except StateError:
            deprint(msg, traceback=True)
            if show_warning: show_warning(msg)
            raise # UI expects that

    def scan_installers_dir(self, folders, files, fullRefresh=False, *,
                            __skip_prefixes=(u'bash', u'--')):
        """March through the Bash Installers dir scanning for new and modified
        projects/packages, skipping as necessary. It will refresh projects on
        boot.
        :rtype: InstallersData._RefreshInfo"""
        pending, installers = set(), set()
        files = [GPath_no_norm(f) for f in files if
                 os.path.splitext(f)[-1].lower() in readExts and not f.lower().startswith(
                     __skip_prefixes)]
        folders = {GPath_no_norm(f) for f in folders if
            # skip Bash directories and user specified ones
            (low := f.lower()) not in self.installers_dir_skips and
            not low.startswith(__skip_prefixes)}
        if fullRefresh:
            pending = {*files, *folders}
        else:
            for items, is_proj in ((files, False), (folders, True)):
                for item in items:
                    installer = self.get(item)
                    # Project - autorefresh those only if specified
                    if is_proj and installer:
                        # refresh projects once on boot even if skipRefresh is on
                        if not installer.project_refreshed: # volatile
                            pending.add(item)
                            continue
                        elif installer.skipRefresh or not bass.settings[
                            u'bash.installers.autoRefreshProjects']:
                            installers.add(item) # installer is present
                            continue # and needs not refresh
                    if not installer or installer.size_or_mtime_changed(
                            installer.abs_path):
                        pending.add(item)
                    else: installers.add(item)
        deleted = set(self.ipackages(self)) - installers - pending
        refresh_info = self._RefreshInfo(deleted, pending, folders)
        return refresh_info

    def refreshConvertersNeeded(self):
        """Return True if refreshConverters is necessary. (Point is to skip
        use of progress dialog when possible)."""
        return self.converters_data.refreshConvertersNeeded()

    def refreshOrder(self):
        """Refresh installer status."""
        inOrder, pending = [], []
        # not specifying the key below results in double time
        for iname, installer in dict_sort(self):
            if installer.order >= 0:
                inOrder.append((iname, installer))
            else:
                pending.append((iname, installer))
        inOrder.sort(key=lambda x: x[1].order)
        for dex, (key, value) in enumerate(inOrder):
            if self.lastKey == key:
                inOrder[dex:dex] = pending
                break
        else:
            inOrder += pending
        changed = False
        for order, (iname, installer) in enumerate(inOrder):
            if installer.order != order:
                installer.order = order
                changed = True
        return changed

    def refreshNorm(self):
        """Populate self.ci_underrides_sizeCrc with all underridden files."""
        active_sorted = (x for x in self.sorted_values() if x.is_active)
        #--dict mapping all should-be-installed files to their attributes
        norm_sizeCrc = bolt.LowerDict()
        for package in active_sorted:
            norm_sizeCrc.update(package.ci_dest_sizeCrc)
        #--Abnorm
        ci_underrides_sizeCrc = bolt.LowerDict()
        dataGet = self.data_sizeCrcDate.get
        for path,sizeCrc in norm_sizeCrc.items():
            sizeCrcDate = dataGet(path)
            if sizeCrcDate and sizeCrc != sizeCrcDate[:2]: # file is installed
                # in data dir, but from a lower loading installer (or manually)
                ci_underrides_sizeCrc[path] = sizeCrcDate[:2]
        self.ci_underrides_sizeCrc, oldAbnorm_sizeCrc = \
            ci_underrides_sizeCrc, self.ci_underrides_sizeCrc
        return ci_underrides_sizeCrc != oldAbnorm_sizeCrc

    def refreshInstallersStatus(self):
        """Refresh installer status."""
        changed = False
        for installer in self.values():
            changed |= installer.refreshStatus(self)
        return changed

    def _refresh_from_data_dir(self, progress=None, recalculate_all_crcs=False):
        """Update self.data_sizeCrcDate, using current data_sizeCrcDate as a
        cache.

        Recalculates crcs for all espms in Data/ directory and all other
        files whose cached date or size has changed. Will skip directories (
        but not files) specified in Installer global skips and remove empty
        dirs if the setting is on."""
        #--Scan for changed files
        progress = progress if progress else bolt.Progress()
        progress_msg = bass.dirs[u'mods'].stail + u': ' + _(u'Pre-Scanning...')
        progress(0, progress_msg + u'\n')
        progress.setFull(1)
        dirDirsFiles, emptyDirs = [], set()
        dirDirsFilesAppend, emptyDirsAdd = dirDirsFiles.append, emptyDirs.add
        asRoot = bass.dirs[u'mods'].s
        relPos = len(asRoot) + 1
        for asDir, sDirs, sFiles in os.walk(asRoot):
            progress(0.05, progress_msg + (u'\n%s' % asDir[relPos:]))
            if not (sDirs or sFiles): emptyDirsAdd(GPath(asDir))
            if asDir == asRoot: InstallersData._skips_in_data_dir(sDirs)
            dirDirsFilesAppend((asDir, sDirs, sFiles))
        progress(0, _(u'%s: Scanning...') % bass.dirs[u'mods'].stail)
        new_sizeCrcDate, pending, pending_size = \
            self._process_data_dir(dirDirsFiles, progress)
        #--Remove empty dirs?
        if bass.settings[u'bash.installers.removeEmptyDirs']:
            for empty in emptyDirs:
                try: empty.removedirs()
                except OSError: pass
        changed = Installer.final_update(new_sizeCrcDate,
                                         self.data_sizeCrcDate, pending,
                                         pending_size, progress,
                                         recalculate_all_crcs,
                                         bass.dirs[u'mods'].stail)
        self.update_for_overridden_skips(progress=progress) #after final_update
        #--Done
        return changed

    def _process_data_dir(self, dirDirsFiles, progress):
        """Construct dictionaries mapping the paths in dirDirsFiles to
        filesystem attributes. Old data_SizeCrcDate is used to decide which
        files need their crc recalculated. Return a tuple containing:
        - new_sizeCrcDate and pending: two newly constructed dicts mapping
        paths to their size, date and absolute path and also the crc (for
        new_sizeCrcDate) if the cached value is valid (no change in mod time
        or size of the file)
        - the size of pending files used in displaying crc calculation progress
        Compare to similar code in InstallerProject._refresh_from_project_dir

        :param dirDirsFiles: list of tuples in the format of the output of walk
        """
        from . import modInfos # to get the crcs for espms
        progress.setFull(1 + len(dirDirsFiles))
        pending, pending_size = bolt.LowerDict(), 0
        new_sizeCrcDate = bolt.LowerDict()
        oldGet = self.data_sizeCrcDate.get
        ghost_norm_get = bolt.LowerDict(
            (y, x) for x, y in Installer.getGhosted().items()).get
        if bass.settings[u'bash.installers.autoRefreshBethsoft']:
            bethFiles = set()
        else:
            beth_keys = {*map(CIstr,
                              bush.game.bethDataFiles)} - self.overridden_skips
            bethFiles = LowerDict.fromkeys(beth_keys)
        skipExts = Installer.skipExts
        relPos = len(bass.dirs[u'mods'].s) + 1
        for index, (asDir, __sDirs, sFiles) in enumerate(dirDirsFiles):
            progress(index)
            rsDir = asDir[relPos:]
            for sFile in sFiles:
                top_level_espm = False
                if not rsDir:
                    rpFile = ghost_norm_get(sFile, sFile)
                    ext = rpFile[rpFile.rfind(u'.'):]
                    if ext.lower() in skipExts: continue
                    if rpFile in bethFiles: continue
                    top_level_espm = ext in bush.game.espm_extensions
                else: rpFile = os.path.join(rsDir, sFile)
                asFile = os.path.join(asDir, sFile)
                # below calls may now raise even if "werr.winerror = 123"
                oSize, oCrc, oDate = oldGet(rpFile, (0, 0, 0.0))
                if top_level_espm: # modInfos MUST BE UPDATED
                    try:
                        modInfo = modInfos[GPath(rpFile)]
                        new_sizeCrcDate[rpFile] = (modInfo.fsize,
                           modInfo.cached_mod_crc(), modInfo.mtime, asFile)
                        continue
                    except KeyError:
                        pass # corrupted/missing, let os.lstat decide
                try:
                    lstat = os.lstat(asFile)
                except FileNotFoundError:
                    continue # file does not exist
                lstat_size, date = lstat.st_size, lstat.st_mtime
                if lstat_size != oSize or date != oDate:
                    pending[rpFile] = (lstat_size, oCrc, date, asFile)
                    pending_size += lstat_size
                else:
                    new_sizeCrcDate[rpFile] = (oSize, oCrc, oDate, asFile)
        return new_sizeCrcDate, pending, pending_size

    def reset_refresh_flag_on_projects(self):
        for installer in self.values():
            if installer.is_project():
                installer.project_refreshed = False

    @staticmethod
    def _skips_in_data_dir(sDirs):
        """Skip some top level directories based on global settings - EVEN
        on a fullRefresh."""
        setSkipOBSE = not bass.settings[u'bash.installers.allowOBSEPlugins']
        setSkipDocs = bass.settings[u'bash.installers.skipDocs']
        setSkipImages = bass.settings[u'bash.installers.skipImages']
        newSDirs = (x for x in sDirs if
                    x.lower() not in Installer.dataDirsMinus)
        if bass.settings[u'bash.installers.skipDistantLOD']:
            newSDirs = (x for x in newSDirs if x.lower() != u'distantlod')
        if bass.settings[u'bash.installers.skipLandscapeLODMeshes']:
            newSDirs = (x for x in newSDirs if x.lower() != os.path.join(
                u'meshes', u'landscape', u'lod'))
        if bass.settings[u'bash.installers.skipScreenshots']:
            newSDirs = (x for x in newSDirs if x.lower() != u'screenshots')
        # LOD textures
        if bass.settings[u'bash.installers.skipLandscapeLODTextures'] and \
                bass.settings[u'bash.installers.skipLandscapeLODNormals']:
            newSDirs = (x for x in newSDirs if x.lower() != os.path.join(
                u'textures', u'landscapelod', u'generated'))
        if setSkipOBSE:
            newSDirs = (x for x in newSDirs if
                        x.lower() != bush.game.Se.plugin_dir.lower())
        if bush.game.Sd.sd_abbrev and setSkipOBSE:
            newSDirs = (x for x in newSDirs if
                        x.lower() != bush.game.Sd.install_dir.lower())
        if setSkipDocs and setSkipImages:
            newSDirs = (x for x in newSDirs if x.lower() != u'docs')
        newSDirs = (x for x in newSDirs if
                    x.lower() not in bush.game.Bain.skip_bain_refresh)
        sDirs[:] = [x for x in newSDirs]

    def update_data_SizeCrcDate(self, dest_paths, progress=None):
        """Update data_SizeCrcDate with info on given paths.
        :param progress: must be zeroed - message is used in _process_data_dir
        :param dest_paths: set of paths relative to Data/ - may not exist.
        :type dest_paths: set[str]"""
        root_files = []
        norm_ghost_get = Installer.getGhosted().get
        for data_path in dest_paths:
            sp = data_path.rsplit(os.sep, 1) # split into ['rel_path, 'file']
            if len(sp) == 1: # top level file
                data_path = norm_ghost_get(data_path, data_path)
                root_files.append((bass.dirs[u'mods'].s, data_path))
            else:
                root_files.append((bass.dirs[u'mods'].join(sp[0]).s, sp[1]))
        root_dirs_files = []
        root_files.sort(key=itemgetter(0)) # must sort on same key as groupby
        for key, val in groupby(root_files, key=itemgetter(0)):
            root_dirs_files.append((key, [], [j for i, j in val]))
        progress = progress or bolt.Progress()
        new_sizeCrcDate, pending, pending_size = self._process_data_dir(
            root_dirs_files, progress)
        deleted_or_pending = set(dest_paths) - set(new_sizeCrcDate)
        for d in deleted_or_pending: self.data_sizeCrcDate.pop(d, None)
        Installer.calc_crcs(pending, pending_size, bass.dirs[u'mods'].stail,
                            new_sizeCrcDate, progress)
        for rpFile, (size, crc, date, _asFile) in new_sizeCrcDate.items():
            self.data_sizeCrcDate[rpFile] = (size, crc, date)

    def update_for_overridden_skips(self, dont_skip=None, progress=None):
        if dont_skip is not None:
            dont_skip.difference_update(self.data_sizeCrcDate)
            self.overridden_skips |= dont_skip
        elif self.__clean_overridden_after_load: # needed on first load
            self.overridden_skips.difference_update(self.data_sizeCrcDate)
            self.__clean_overridden_after_load = False
        new_skips_overrides = self.overridden_skips - set(self.data_sizeCrcDate)
        progress = progress or bolt.Progress()
        progress(0, (
            _(u'%s: Skips overrides...') % bass.dirs[u'mods'].stail) + u'\n')
        self.update_data_SizeCrcDate(new_skips_overrides, progress)

    @staticmethod
    def track(abspath):
        InstallersData._miscTrackedFiles[abspath] = AFile(abspath)

    @staticmethod
    def notify_external(changed=frozenset(), deleted=frozenset(),
            renamed=None):
        """Notifies BAIN of changes in the Data folder done by something other
        than BAIN.

        :param changed: A set of file paths that have changed.
        :type deleted: set[bolt.Path]
        :param deleted: A set of file paths that have been deleted.
        :type changed: set[bolt.Path]
        :param renamed: A dict of file paths that were renamed. Maps old file
            paths to new ones. Currently only updates tracked changed/deleted
            paths.
        :type renamed: dict[Path, Path]"""
        if renamed is None: renamed = {}
        ext_updated = InstallersData._externally_updated
        ext_deleted = InstallersData._externally_deleted
        ext_updated.update(changed)
        ext_deleted.update(deleted)
        for renamed_old, renamed_new in renamed.items():
            for ext_tracker in (ext_updated, ext_deleted):
                if renamed_old in ext_tracker:
                    ext_tracker.discard(renamed_old)
                    ext_tracker.add(renamed_new)

    def refreshTracked(self):
        deleted, changed = set(InstallersData._externally_deleted), set(
            InstallersData._externally_updated)
        InstallersData._externally_updated.clear()
        InstallersData._externally_deleted.clear()
        for abspath, tracked in list(InstallersData._miscTrackedFiles.items()):
            if not abspath.exists(): # untrack - runs on first run !!
                InstallersData._miscTrackedFiles.pop(abspath, None)
                deleted.add(abspath)
            elif tracked.do_update():
                changed.add(abspath)
        do_refresh = False
        for apath in changed | deleted:
            # the Data dir - will give correct relative path for both
            # Ini tweaks and mods - those are keyed in data by rel path...
            relpath = apath.relpath(bass.dirs[u'mods'])
            # ghosts...
            path_key = (relpath.root.s if relpath.cs[-6:] == u'.ghost'
                        else relpath.s)
            if apath in deleted:
                do_refresh |= bool(self.data_sizeCrcDate.pop(path_key, None))
            else:
                s, m = apath.size_mtime()
                self.data_sizeCrcDate[path_key] = (s, apath.crc, m)
                do_refresh = True
        return do_refresh # Some tracked files changed, update installers status

    #--Operations -------------------------------------------------------------
    def moveArchives(self,moveList,newPos):
        """Move specified archives to specified position."""
        old_ordered = self.sorted_values(set(self) - set(moveList))
        new_ordered = self.sorted_values(moveList)
        if newPos >= len(self): newPos = len(old_ordered)
        for index, installer in enumerate(old_ordered[:newPos]):
            installer.order = index
        for index, installer in enumerate(new_ordered):
            installer.order = newPos + index
        for index, installer in enumerate(old_ordered[newPos:]):
            installer.order = newPos + len(new_ordered) + index
        self.setChanged()

    #--Install
    def _createTweaks(self, destFiles, installer, tweaksCreated):
        """Generate INI Tweaks when a CRC mismatch is detected while
        installing a mod INI (not ini tweak) in the Data/ directory.

        If the current CRC of the ini is different than the one BAIN is
        installing, a tweak file will be generated. Call me *before*
        installing the new inis then call _editTweaks() to populate the tweaks.
        """
        dest_files = (x for x in destFiles
                if x[-4:].lower() in (u'.ini', u'.cfg')
                # don't create ini tweaks for overridden ini tweaks...
                and os.path.split(x)[0].lower() != u'ini tweaks')
        for relPath in dest_files:
            oldCrc = self.data_sizeCrcDate.get(relPath, (None, None, None))[1]
            newCrc = installer.ci_dest_sizeCrc.get(relPath, (None, None))[1]
            if oldCrc is None or newCrc is None or newCrc == oldCrc: continue
            iniAbsDataPath = bass.dirs[u'mods'].join(relPath)
            # Create a copy of the old one
            co_path = f'{iniAbsDataPath.sbody}, ~Old Settings ' \
                      f'[{installer.ci_key}].ini'
            baseName = bass.dirs[u'ini_tweaks'].join(co_path)
            tweakPath = self.__tweakPath(baseName)
            iniAbsDataPath.copyTo(tweakPath)
            tweaksCreated.add((tweakPath, iniAbsDataPath))

    @staticmethod
    def __tweakPath(baseName):
        oldIni, num = baseName, 1
        while oldIni.exists():
            suffix = u' - Copy' + (u'' if num == 1 else u' (%i)' % num)
            oldIni = baseName.head.join(baseName.sbody + suffix + baseName.ext)
            num += 1
        return oldIni

    @staticmethod
    def _editTweaks(tweaksCreated):
        """Edit created ini tweaks with settings that differ and/or don't exist
        in the new ini."""
        removed = set()
        from . import iniInfos
        pseudosections = set(OBSEIniFile.ci_pseudosections.values())
        for (tweakPath, iniAbsDataPath) in tweaksCreated:
            iniFile = BestIniFile(iniAbsDataPath)
            currSection = None
            lines = []
            for (line_text, section, setting, value, status, lineNo,
                 deleted) in iniFile.analyse_tweak(BestIniFile(tweakPath)):
                if not line_text.rstrip():
                    continue # possible empty lines at the start
                if status in (10, -10):
                    # A setting that exists in both INI's, but is different,
                    # or a setting that doesn't exist in the new INI.
                    if section in pseudosections:
                        lines.append(line_text + u'\n')
                    elif section != currSection:
                        currSection = section
                        if not section: continue
                        lines.append(u'\n[%s]\n' % section)
                        # a section line may have 0 status - may be a setting ?
                        if setting is not None:
                            lines.append(line_text + u'\n')
                    elif not section:
                        continue
                    else:
                        lines.append(line_text + u'\n')
            if not lines: # avoid creating empty tweaks
                removed.add((tweakPath, iniAbsDataPath))
                tweakPath.remove()
                continue
            # Re-write the tweak. Use UTF-8 so that we can localize the
            # comment at the top
            with tweakPath.open(u'w', encoding=u'utf-8') as ini_:
                ini_.write(u'; %s\n\n' % (_(u'INI Tweak created by Wrye Bash '
                                            u'%s, using settings from old '
                                            u'file.') % bass.AppVersion))
                ini_.writelines(lines)
            # We notify BAIN below, although highly improbable the created ini
            # is included to a package
            iniInfos.new_info(tweakPath.tail, notify_bain=True)
        tweaksCreated -= removed

    def _install(self, packages, refresh_ui, progress=None, last=False,
                 override=True):
        """Install selected packages. If override is False install only
        missing files. Otherwise, all (unmasked) files."""
        progress = progress or bolt.Progress()
        tweaksCreated = set()
        #--Mask and/or reorder to last
        mask = set()
        if last:
            self.moveArchives(packages, len(self))
        to_install = {self[x] for x in packages}
        min_order = min(x.order for x in to_install)
        #--Install packages in turn
        progress.setFull(len(packages))
        index = 0
        for installer in self.sorted_values(reverse=True):
            if installer in to_install:
                progress(index,installer.archive)
                destFiles = set(installer.ci_dest_sizeCrc) - mask
                if not override:
                    destFiles &= installer.missingFiles
                if destFiles:
                    self._createTweaks(destFiles, installer, tweaksCreated)
                    self.__installer_install(installer, destFiles, index,
                                             progress, refresh_ui)
                index += 1 # increment after it's used in __installer_install
                installer.is_active = True
                if installer.order == min_order:
                    break # we are done
            #prevent lower packages from installing any files of this installer
            if installer.is_active: mask |= set(installer.ci_dest_sizeCrc)
        if tweaksCreated:
            self._editTweaks(tweaksCreated)
            refresh_ui[1] |= bool(tweaksCreated)
        return tweaksCreated

    def __installer_install(self, installer, destFiles, index, progress,
                            refresh_ui):
        sub_progress = SubProgress(progress, index, index + 1)
        data_sizeCrcDate_update, mods, inis, bsas = installer.install(
            destFiles, sub_progress)
        refresh_ui[0] |= bool(mods)
        refresh_ui[1] |= bool(inis)
        # refresh modInfos, iniInfos adding new/modified mods
        from . import bsaInfos, modInfos, iniInfos
        for mod in mods.copy(): # size may change during iteration
            try:
                modInfos.new_info(mod, owner=installer.archive)
            except FileError:
                mods.discard(mod)
        # Notify the bsaInfos cache of any new BSAs, since we may have
        # installed a localized plugin and the LO syncs below will check for
        # missing strings ##: Identical to mods loop above!
        for bsa in bsas:
            try:
                bsaInfos.new_info(bsa, owner=installer.archive)
            except FileError:
                pass # corrupt, but we won't need the bsas set again, so ignore
        modInfos.cached_lo_append_if_missing(mods)
        modInfos.refreshLoadOrder(unlock_lo=True)
        # now that we saved load order update missing mtimes for mods:
        for mod in mods:
            s, c, _d = data_sizeCrcDate_update[mod.s]
            data_sizeCrcDate_update[mod.s] = (s, c, modInfos[mod].mtime)
        # and for rest of the files - we do mods separately for ghosts
        self.data_sizeCrcDate.update((dest, (
            s, c, (d != -1 and d) or bass.dirs[u'mods'].join(dest).mtime)) for
            dest, (s, c, d) in data_sizeCrcDate_update.items())
        for ini_path in inis:
            iniInfos.new_info(ini_path, owner=installer.archive)

    def sorted_pairs(self, package_keys=None, reverse=False):
        """Return pairs of key, installer for package_keys in self, sorted by
        install order.
        :type package_keys: None | collections.Iterable[Path]
        :rtype: list[(Path, Installer)]
        """
        pairs = self if package_keys is None else {k: self[k] for k in
                                                   package_keys}
        return dict_sort(pairs, key_f=lambda k: pairs[k].order,
                         reverse=reverse)

    def sorted_values(self, package_keys=None, reverse=False):
        """Return installers for package_keys in self, sorted by install order.
        :type package_keys: None | collections.Iterable[Path]
        :rtype: list[Installer]
        """
        if package_keys is None: values = self.values()
        else: values = [self[k] for k in package_keys]
        return sorted(values, key=attrgetter('order'), reverse=reverse)

    def bain_install(self, packages, refresh_ui, progress=None, last=False,
                     override=True):
        try: return self._install(packages, refresh_ui, progress, last,
                                  override)
        finally: self.irefresh(what=u'NS')

    #--Uninstall, Anneal, Clean
    @staticmethod
    def _determineEmptyDirs(emptyDirs, removedFiles):
        allRemoves = set(removedFiles)
        allRemovesAdd, removedFilesAdd = allRemoves.add, removedFiles.add
        emptyDirsClear, emptyDirsAdd = emptyDirs.clear, emptyDirs.add
        exclude = {bass.dirs[u'mods'], bass.dirs[u'mods'].join(u'Docs')} # don't bother
        # with those (Data won't likely be removed and Docs we want it around)
        emptyDirs -= exclude
        while emptyDirs:
            testDirs = set(emptyDirs)
            emptyDirsClear()
            for folder in sorted(testDirs, key=len, reverse=True):
                # Sorting by length, descending, ensure we always
                # are processing the deepest directories first
                files = {folder.join(x) for x in folder.list()}
                remaining = files - allRemoves
                if not remaining: # If all items in this directory will be
                    # removed, this directory is also safe to remove.
                    removedFiles -= files
                    removedFilesAdd(folder)
                    allRemovesAdd(folder)
                    emptyDirsAdd(folder.head)
            emptyDirs -= exclude
        return removedFiles

    @staticmethod
    def _is_ini_tweak(ci_relPath):
        parts = ci_relPath.lower().split(os_sep)
        return len(parts) == 2 and parts[0] == u'ini tweaks' \
           and parts[1][-4:] == u'.ini' and parts[1]

    def _removeFiles(self, ci_removes, refresh_ui, progress=None):
        """Performs the actual deletion of files and updating of internal data,
           used by 'bain_uninstall' and 'bain_anneal'."""
        if not ci_removes: return
        modsDirJoin = bass.dirs[u'mods'].join
        emptyDirs = set()
        emptyDirsAdd = emptyDirs.add
        nonPlugins = set()
        from . import modInfos
        reModExtSearch = modInfos.rightFileType
        removedPlugins = set()
        removedInis = set()
        #--Construct list of files to delete
        norm_ghost_get = Installer.getGhosted().get
        for ci_relPath in ci_removes:
            path = modsDirJoin(norm_ghost_get(ci_relPath, ci_relPath))
            if path.exists():
                if reModExtSearch(ci_relPath):
                    removedPlugins.add(GPath_no_norm(str(ci_relPath)))
                elif ini_name := self._is_ini_tweak(ci_relPath):
                    removedInis.add(GPath_no_norm(ini_name))
                else:
                    nonPlugins.add(path)
                    emptyDirsAdd(path.head)
        #--Now determine which directories will be empty, replacing subsets of
        # removedFiles by their parent dir if the latter will be emptied
        nonPlugins = self._determineEmptyDirs(emptyDirs, nonPlugins)
        ex = None # if an exception is raised we must again check removes
        try: #--Do the deletion
            if nonPlugins:
                parent = progress.getParent() if progress else None
                env.shellDelete(nonPlugins, parent=parent)
            #--Delete mods and remove them from load order
            if removedPlugins:
                refresh_ui[0] = True
                modInfos.delete(removedPlugins, recycle=False,
                                raise_on_master_deletion=False)
            if removedInis:
                from . import iniInfos
                refresh_ui[1] = True
                iniInfos.delete(removedInis, recycle=False)
        except (CancelError, SkipError): ex = sys.exc_info()
        except:
            ex = sys.exc_info()
            raise
        finally:
            if ex:
                ci_removes = [f for f in ci_removes if
                              not modsDirJoin(norm_ghost_get(f, f)).exists()]
            #--Update InstallersData
            data_sizeCrcDatePop = self.data_sizeCrcDate.pop
            for ci_relPath in ci_removes:
                data_sizeCrcDatePop(ci_relPath, None)

    def __restore(self, installer, removes, restores, cede_ownership):
        """Populate restores dict with files to be restored by this
        installer, removing those from removes. In case a mod or ini belongs
        to another package, we must make sure we cede ownership, even if the
        mod or ini is not restored (restore takes care of that).

        Returns all of the files this installer would install. Used by
        'bain_uninstall' and 'bain_anneal'."""
        # get all destination files for this installer
        files = set(installer.ci_dest_sizeCrc)
        # keep those to be removed while not restored by a higher order package
        to_keep = (removes & files) - set(restores)
        g_path = GPath(installer.archive) if to_keep else None
        for dest_file in to_keep:
            if installer.ci_dest_sizeCrc[dest_file] != \
                    self.data_sizeCrcDate.get(dest_file,(0, 0, 0))[:2]:
                # restore it from this installer
                restores[dest_file] = g_path
            else:
                cede_ownership[installer.archive].add(dest_file)
            removes.discard(dest_file) # don't remove it anyway
        return files

    def bain_uninstall(self, unArchives, refresh_ui, progress=None):
        """Uninstall selected archives."""
        if unArchives == u'ALL': unArchives = frozenset(self.values())
        else: unArchives = frozenset(self[x] for x in unArchives)
        data_sizeCrcDate = self.data_sizeCrcDate
        #--Determine files to remove and files to restore. Keep in mind that
        #  multiple input archives may be interspersed with other archives that
        #  may block (mask) them from deleting files and/or may provide files
        #  that should be restored to make up for previous files. However,
        #  restore can be skipped, if existing files matches the file being
        #  removed.
        masked = set()
        removes = set()
        #--March through packages in reverse order...
        restores = bolt.LowerDict()
        _cede_ownership = collections.defaultdict(set)
        for installer in self.sorted_values(reverse=True):
            #--Uninstall archive?
            if installer in unArchives:
                for data_sizeCrc in (installer.ci_dest_sizeCrc,installer.dirty_sizeCrc):
                    for cistr_file,sizeCrc in data_sizeCrc.items():
                        sizeCrcDate = data_sizeCrcDate.get(cistr_file)
                        if cistr_file not in masked and sizeCrcDate and sizeCrcDate[:2] == sizeCrc:
                            removes.add(cistr_file)
            #--Other active archive. May undo previous removes, or provide a restore file.
            #  And/or may block later uninstalls.
            elif installer.is_active:
                masked |= self.__restore(installer, removes, restores,
                                         _cede_ownership)
        anneal = bass.settings[u'bash.installers.autoAnneal']
        self._remove_restore(removes, restores, refresh_ui, _cede_ownership,
                             progress, unArchives, anneal)

    def _remove_restore(self, removes, restores, refresh_ui, cede_ownership,
                        progress, unArchives=frozenset(), anneal=True):
        try:
            #--Remove files, update InstallersData, update load order
            self._removeFiles(removes, refresh_ui, progress)
            #--De-activate
            for inst in unArchives:
                inst.is_active = False
            #--Restore files
            if anneal:
                self._restoreFiles(restores, refresh_ui, progress)
            # Set the 'installer' column in mod and ini tables
            from . import modInfos, iniInfos
            for ikey, owned_files in cede_ownership.items():
                for fn_key in owned_files:
                    if modInfos.rightFileType(fn_key):
                        refresh_ui[0] = True
                        modInfos.table.setItem(GPath_no_norm(fn_key), u'installer', ikey)
                    elif ini_name := InstallersData._is_ini_tweak(fn_key):
                        refresh_ui[1] = True
                        iniInfos.table.setItem(GPath_no_norm(ini_name), u'installer', ikey)
        finally:
            self.irefresh(what=u'NS')

    def _restoreFiles(self, restores, refresh_ui, progress):
        installer_destinations = {}
        restores = dict_sort(restores, by_value=True)
        for key, group in groupby(restores, key=itemgetter(1)):
            installer_destinations[key] = {dest for dest, _key in group}
        if not installer_destinations: return
        progress.setFull(len(installer_destinations))
        installer_destinations = dict_sort(installer_destinations,
                                           key_f=lambda k: self[k].order)
        for index, (archive_path, destFiles) in enumerate(installer_destinations):
            progress(index, archive_path.s)
            if destFiles:
                installer = self[archive_path]
                self.__installer_install(installer, destFiles, index, progress,
                                         refresh_ui)

    def bain_anneal(self, anPackages, refresh_ui, progress=None):
        """Anneal selected packages. If no packages are selected, anneal all.
        Anneal will:
        * Correct underrides in anPackages.
        * Install missing files from active anPackages."""
        progress = progress if progress else bolt.Progress()
        anPackages = (self[package] for package in (anPackages or self))
        #--Get remove/refresh files from anPackages
        removes = set()
        for installer in anPackages:
            removes |= installer.underrides
            if installer.is_active:
                removes |= installer.missingFiles # re-added in __restore
                removes |= set(installer.dirty_sizeCrc)
            installer.dirty_sizeCrc.clear()
        #--March through packages in reverse order...
        restores = bolt.LowerDict()
        _cede_ownership = collections.defaultdict(set)
        for installer in self.sorted_values(reverse=True):
            #--Other active package. May provide a restore file.
            #  And/or may block later uninstalls.
            if installer.is_active:
                self.__restore(installer, removes, restores, _cede_ownership)
        self._remove_restore(removes, restores, refresh_ui, _cede_ownership,
                             progress)

    def get_clean_data_dir_list(self):
        keepFiles = set()
        for installer in self.sorted_values(reverse=True):
            if installer.is_active:
                keepFiles.update(installer.ci_dest_sizeCrc) # relative to Data/
        from . import modInfos
        # Collect all files that we definitely want to keep
        collected_strs = bush.game.vanilla_files
        collected_strs |= bush.game.bethDataFiles
        collected_strs |= bush.game.Bain.keep_data_files
        collected_strs |= bush.game.Bain.wrye_bash_data_files
        keepFiles.update((bolt.CIstr(f) for f in collected_strs))
        for bpatch in modInfos.bashed_patches: # type: bolt.Path
            keepFiles.add(bolt.CIstr(bpatch.s))
            bp_doc = modInfos.table.getItem(bpatch, u'doc')
            if bp_doc: # path is absolute, convert to relative to the Data/ dir
                try:
                    bp_doc = bp_doc.relpath(bass.dirs[u'mods'].s)
                except ValueError: # https://bugs.python.org/issue7195
                    # bp_doc on a different drive, will be skipped anyway
                    continue
                # Keep both versions of the BP doc (.txt and .html)
                keepFiles.add((bolt.CIstr(u'%s' % bp_doc)))
                keepFiles.add((bolt.CIstr(
                    bp_doc.root.s + (u'.txt' if bp_doc.cext == u'.html'
                                     else u'.html'))))
        removes = set(self.data_sizeCrcDate) - keepFiles
        # don't remove files in Wrye Bash-related directories or Ini Tweaks
        skipPrefixes = [skipDir.lower() + os.sep for skipDir in
                        bush.game.Bain.wrye_bash_data_dirs |
                        bush.game.Bain.keep_data_dirs]
        skipPrefixes.extend([skipPrefix.lower() for skipPrefix
                             in bush.game.Bain.keep_data_file_prefixes])
        skipPrefixes = tuple(skipPrefixes)
        filtered_removes = [f for f in removes
                            if not f.lower().startswith(skipPrefixes)]
        return filtered_removes

    def clean_data_dir(self, removes,  refresh_ui):
        destDir = bass.dirs[u'bainData'].join(u'%s Folder Contents (%s)' % (
            bush.game.mods_dir, bolt.timestamp()))
        try:
            from . import modInfos
            emptyDirs, mods = set(), set()
            norm_ghost_get = Installer.getGhosted().get
            for filename in removes:
                full_path = bass.dirs[u'mods'].join(
                    norm_ghost_get(filename, filename))
                try:
                    full_path.moveTo(destDir.join(filename)) # will drop .ghost
                    if modInfos.rightFileType(full_path):
                        mods.add(GPath(filename))
                        refresh_ui[0] = True
                    self.data_sizeCrcDate.pop(filename, None)
                    emptyDirs.add(full_path.head)
                except (StateError, OSError):
                    #It's not imperative that files get moved, so ignore errors
                    deprint(f'Clean Data: moving {full_path} to {destDir} '
                            f'failed', traceback=True)
            modInfos.delete_refresh(mods, None, check_existence=False)
            for emptyDir in emptyDirs:
                if emptyDir.is_dir() and not emptyDir.list():
                    emptyDir.removedirs()
        finally:
            self.irefresh(what=u'NS')

    #--Utils
    @staticmethod
    def _filter_installer_bsas(inst, active_bsas):
        return [k for k in active_bsas if k.name.s in inst.ci_dest_sizeCrc]

    @staticmethod
    def _parse_error(bsa_inf, reason):
        deprint(u'Error parsing %s [%s]' % (bsa_inf, reason), traceback=True)

    ##: Maybe cache the result? Can take a bit of time to calculate
    def find_conflicts(self, src_installer, active_bsas=None, bsa_cause=None,
                       list_overrides=True, include_inactive=False,
                       include_lower=True, include_bsas=True):
        """Returns all conflicts for the specified installer, filtering them by
        BSA (if enabled by the user) or loose file and whether they are lower
        or higher than the specified installer.

        :param src_installer: The installer to find conflicts for.
        :param active_bsas: The dict of currently active BSAs. Can be retrieved
            via bosh.modInfos.get_active_bsas(). Only needed if BSA conflicts
            are enabled (i.e. include_bsas is True).
        :Param bsa_cause: The dict of reasons BSAs were loaded. Retrieve
            alongside active_bsas from bosh.modInfos.get_active_bsas(). Only
            needed if BSA conflicts are enabled.
        :param list_overrides: Whether to list overrides (True) or underrides
            (False).
        :param include_inactive: Whether or not to include conflicts from
            inactive packages.
        :param include_lower: Whether or not to include conflicts with
            installers that have a lower order than src_installer.
        :param include_bsas: Whether or not to include BSA conflicts as well.
        :return: Four lists corresponding to the lower loose, higher loose,
            lower BSA and higher BSA conflicts. If BSA conflicts are not
            enabled, the last two will be empty."""
        srcOrder = src_installer.order
        showInactive = list_overrides and include_inactive
        showLower = list_overrides and include_lower
        if list_overrides:
            mismatched = set(src_installer.ci_dest_sizeCrc)
        else:
            mismatched = src_installer.underrides
        if not mismatched: return [], [], [], []
        src_sizeCrc = src_installer.ci_dest_sizeCrc
        # Calculate bsa conflicts
        lower_bsa, higher_bsa = [], []
        if include_bsas:
            # Calculate all conflicts and save them in lower_bsa and higher_bsa
            asset_to_bsa, src_assets = self.find_src_assets(src_installer,
                                                            active_bsas)
            remaining_bsas = copy.copy(active_bsas)
            def _process_bsa_conflicts(b_inf, b_source):
                try: # conflicting assets from this installer active bsas
                    curConflicts = b_inf.assets & src_assets
                except BSAError:
                    self._parse_error(b_inf, b_source)
                    return
                # We've used this BSA for a conflict, don't use it again
                del remaining_bsas[b_inf]
                if curConflicts:
                    lower_result, higher_result = set(), set()
                    add_to_lower = lower_result.add
                    add_to_higher = higher_result.add
                    for conflict in curConflicts:
                        orig_order = active_bsas[asset_to_bsa[conflict]]
                        curr_order = active_bsas[b_inf]
                        if curr_order == orig_order: continue
                        elif curr_order < orig_order:
                            if showLower: add_to_lower(conflict)
                        else:
                            add_to_higher(conflict)
                    if lower_result:
                        lower_bsa.append((b_source, b_inf,
                                          bolt.sortFiles(lower_result)))
                    if higher_result:
                        higher_bsa.append((b_source, b_inf,
                                           bolt.sortFiles(higher_result)))
            for package, installer in self.sorted_pairs():
                discard_bsas = installer.order == srcOrder or not (
                        showInactive or installer.is_active)
                for bsa_info in self._filter_installer_bsas(
                        installer, remaining_bsas):
                    if discard_bsas:
                        # Either comes from this installer or is from an
                        # inactive installer - either way, ignore it
                        ##: Support for inactive BSA conflicts
                        del remaining_bsas[bsa_info]
                    else:
                        _process_bsa_conflicts(bsa_info, package.s)
            # Check all left-over BSAs - they either came from an INI or from a
            # plugin file not managed by BAIN (e.g. a DLC)
            for rem_bsa in list(remaining_bsas):
                _process_bsa_conflicts(rem_bsa, bsa_cause[rem_bsa])
            def _sort_bsa_conflicts(bsa_conflict):
                return active_bsas[bsa_conflict[1]]
            lower_bsa.sort(key=_sort_bsa_conflicts)
            higher_bsa.sort(key=_sort_bsa_conflicts)
        # Calculate loose conflicts
        lower_loose, higher_loose = [], []
        for package, installer in self.sorted_pairs():
            if installer.order == srcOrder or not (
                        showInactive or installer.is_active): continue
            if not showLower and installer.order < srcOrder: continue
            curConflicts = bolt.sortFiles(
                [x for x, y in installer.ci_dest_sizeCrc.items()
                if x in mismatched and y != src_sizeCrc[x]])
            if curConflicts:
                if installer.order < srcOrder:
                    conflict_type = lower_loose
                else:
                    conflict_type = higher_loose
                conflict_type.append((installer, package.s, curConflicts))
        return lower_loose, higher_loose, lower_bsa, higher_bsa

    def find_src_assets(self, src_installer, active_bsas):
        """Map src_installer's active BSAs' assets to those BSAs, assigning
        the assets to the highest loading BSA. There's generally only one for
        Skyrim and older, one or two for SSE and any number of BSAs for FO4.

        :param src_installer: The installer from which to retrieve BSA assets.
        :param active_bsas: The set of active BSAs. Generally retrieved via
                            bosh.modInfos.get_active_bsas().
        :return: An OrderedDict containing a mapping from asset to BSA and the
                 relevant assets from the installer's BSAs in a set."""
        asset_to_bsa, src_assets = collections.OrderedDict(), set()
        for b in reversed(self._filter_installer_bsas(
                src_installer, active_bsas)):
            try:
                b_assets = b.assets - src_assets
            except BSAError:
                self._parse_error(b, src_installer.archive)
                continue
            if b_assets:
                for b_asset in b_assets:
                    asset_to_bsa[b_asset] = b
                src_assets |= b_assets
        return asset_to_bsa, src_assets

    _ini_origin = re.compile(r'(\w+\.ini) \((\w+)\)', re.I | re.U)
    def getConflictReport(self, srcInstaller, mode, modInfos):
        """Returns report of overrides for specified package for display on
        conflicts tab.

        :param srcInstaller: The installer to find conflicts for.
        :param mode: 'OVER': Overrides; 'UNDER': Underrides.
        :param modInfos: bosh.modInfos
        :return: A string containing the printable report of all conflicts."""
        list_overrides = (mode == u'OVER')
        if list_overrides:
            if not set(srcInstaller.ci_dest_sizeCrc): return u''
        else:
            if not srcInstaller.underrides: return u''
        include_inactive = bass.settings[
            u'bash.installers.conflictsReport.showInactive']
        include_lower = list_overrides and bass.settings[
            u'bash.installers.conflictsReport.showLower']
        include_bsas = bass.settings[
            u'bash.installers.conflictsReport.showBSAConflicts']
        ##: Add support for showing inactive & excluding lower BSAs
        if include_bsas:
            active_bsas, bsa_cause = modInfos.get_active_bsas()
        else:
            active_bsas, bsa_cause = None, None
        lower_loose, higher_loose, lower_bsa, higher_bsa = self.find_conflicts(
            srcInstaller, active_bsas, bsa_cause, list_overrides,
            include_inactive, include_lower, include_bsas)
        # Generate report
        buff = io.StringIO()
        # Print BSA conflicts
        if include_bsas:
            buff.write(u'= %s %s\n\n' % (_(u'Active BSA Conflicts'), u'=' * 40))
            # Print partitions - bsa loading order NOT installer order
            origin_ini_match = self._ini_origin.match
            def _print_bsa_conflicts(conflicts, title=_(u'Lower')):
                buff.write(u'= %s %s\n' % (title, u'=' * 40))
                for origin_, bsa_inf, confl_ in conflicts:
                    # If the origin is an INI, then active_bsas[bsa_inf]
                    # does not contain a meaningful result (will be an
                    # extremely large/small number)
                    ini_ma = origin_ini_match(origin_)
                    if ini_ma:
                        buff.write(u'==%s== %s : %s\n' % (
                            ini_ma.group(1), ini_ma.group(2), bsa_inf))
                    else:
                        buff.write(u'==%X== %s : %s\n' % (
                            active_bsas[bsa_inf], origin_, bsa_inf))
                    buff.write(u'\n'.join(confl_) + u'\n\n')
            if include_lower and lower_bsa:
                _print_bsa_conflicts(lower_bsa, _(u'Lower'))
            if higher_bsa:
                _print_bsa_conflicts(higher_bsa, _(u'Higher'))
            buff.write(u'= %s %s\n\n' % (_(u'Loose File Conflicts'), u'=' * 36))
        # Print loose file conflicts
        def _print_loose_conflicts(conflicts, title=_(u'Lower')):
            buff.write(f'= {title} {u"=" * 40}\n')
            for inst_, package_, confl_ in conflicts:
                buff.write(f'=={inst_.order:d}== {package_}\n')
                for src_file in confl_:
                    oldName = inst_.getEspmName(src_file)
                    buff.write(oldName)
                    if oldName != src_file:
                        buff.write(u' -> ')
                        buff.write(src_file)
                    buff.write(u'\n')
                buff.write(u'\n')
        if include_lower and lower_loose:
            _print_loose_conflicts(lower_loose, _(u'Lower'))
        if higher_loose:
            _print_loose_conflicts(higher_loose, _(u'Higher'))
        report = buff.getvalue()
        if not list_overrides and not report and not srcInstaller.is_active:
            report = _(u'No Underrides. Mod is not completely un-installed.')
        return report

    def getPackageList(self,showInactive=True):
        """Returns package list as text."""
        #--Setup
        log = bolt.LogFile(io.StringIO())
        log.setHeader(_(u'Bain Packages:'))
        #--List
        log(u'[spoiler]\n', False)
        for package, installer in self.sorted_pairs():
            prefix = u'%03d' % installer.order
            if installer.is_marker():
                log(u'%s - %s' % (prefix, package))
            elif installer.is_active:
                log(u'++ %s - %s (%08X) (Installed)' % (
                    prefix, package, installer.crc))
            elif showInactive:
                log(u'-- %s - %s (%08X) (Not Installed)' % (
                    prefix, package, installer.crc))
        log(u'[/spoiler]')
        return bolt.winNewLines(log.out.getvalue())

    def filterInstallables(self, installerKeys):
        """Return a sublist of installerKeys that can be installed -
        installerKeys must be in data or a KeyError is raised.
        :param installerKeys: an iterable of bolt.Path
        :return: a list of installable packages/projects bolt.Path
        """
        # type -> 0: unset/invalid; 1: simple; 2: complex
        return [k for k in self.ipackages(installerKeys) if
                self[k].type in (1, 2)]

    def ipackages(self, installerKeys):
        """Remove markers from installerKeys.
        :type installerKeys: collections.Iterable[bolt.Path]
        :rtype: list[bolt.Path]
        """
        return (x for x in installerKeys if not self[x].is_marker())

    def createFromData(self, projectPath, ci_files, progress):
        if not ci_files: return
        norm_ghost_get = Installer.getGhosted().get
        subprogress = SubProgress(progress, 0, 0.8, full=len(ci_files))
        srcJoin = bass.dirs[u'mods'].join
        dstJoin = self.store_dir.join(projectPath).join
        for i,filename in enumerate(ci_files):
            subprogress(i, filename)
            srcJoin(norm_ghost_get(filename, filename)).copyTo(
                dstJoin(filename))
        # Refresh, so we can manipulate the InstallerProject item
        self._inst_types[1].refresh_installer(projectPath, self, progress,
            do_refresh=True, install_order=len(self)) # install last
