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
"""BAIN backbone classes."""
from __future__ import annotations

import collections
import copy
import io
import os
import re
import shutil
import sys
import time
from collections import defaultdict
from collections.abc import Iterable
from functools import partial
from itertools import chain, groupby
from operator import attrgetter, itemgetter
from zlib import crc32

from . import Corrupted, DataStore, ModInfos, RefrData, bain_image_exts, \
    best_ini_files, data_tracking_stores
from .converters import InstallerConverter
from .. import archives, bass, bolt, bush, env
from ..archives import compress7z, defaultExt, extract7z, list_archive, \
    readExts
from ..bass import Store
from ..bolt import AFile, CIstr, FName, GPath_no_norm, ListInfo, Path, \
    SubProgress, deprint, dict_sort, forward_compat_path_to_fn, \
    forward_compat_path_to_fn_list, round_size, top_level_items, \
    DefaultFNDict, copy_or_reflink2, AFileInfo
from ..exception import ArgumentError, BSAError, CancelError, FileError, \
    InstallerArchiveError, SkipError, StateError
from ..ini_files import OBSEIniFile, supported_ini_exts
from ..wbtemp import TempFile, cleanup_temp_dir, new_temp_dir

os_sep = os.path.sep ##: track

_fnames = Iterable[FName] | None

# Walk Data and project dir helpers - we don't want to refactor the common walk
# logic and pass a function to be called for each file - lots of overhead
def _remove_empty_dirs(root_dir):
    """Remove subdirs of root_dir that contain no files in any subfolder."""
    root_dir, folders, files = next(os.walk(root_dir))
    if not files and not folders:
        return True # empty
    possible_empty = []
    if folders:
        # root_dir should be an absolute path
        root_gpath = GPath_no_norm(root_dir)
        for fol in folders:
            if _remove_empty_dirs(fol_abs := root_gpath.join(fol)):
                possible_empty.append(fol_abs)
            else: files = True
    if files:
        for empty in possible_empty:
            empty.removedirs()
        return False
    return True

def _scandir_walk(apath, *, __root_len=None, __folders_times=None):
    """Recursively walk the project dir - only used in InstallerProject."""
    size_apath_date = bolt.LowerDict()
    if __root_len is None:
        __root_len = len(apath) + 1
    __folders_times = [apath.mtime] if __folders_times is None else \
        __folders_times
    for dirent in os.scandir(apath):
        if dirent.is_dir():
            __folders_times.append(dirent.stat().st_mtime)
            dir_walk, _ = _scandir_walk(dirent.path, __root_len=__root_len,
                                        __folders_times=__folders_times)
            size_apath_date.update(dir_walk)
        else:
            size_apath_date[dirent.path[__root_len:]] = (
                (st := dirent.stat()).st_size, dirent.path, st.st_mtime)
    return size_apath_date, __folders_times

def _walk_data_dirs(apath, siz_apath_mtime, new_sizeCrcDate, root_len,
                    oldGet, remove_empty):
    """Recursively walk the top directories of the Data/ dir. See
    _scandir_walk for a similar pattern -  note complications like
    empty dirs handling."""
    ##: add Subprogress for super accurate and slow progress bars
    nodes = [*os.scandir(apath)]
    if not nodes:
        return 0, 0
    has_files = 0
    possible_empty = []
    for dirent in nodes:
        if dirent.is_dir():
            subdir_files = _walk_data_dirs(dirent.path, siz_apath_mtime,
                new_sizeCrcDate, root_len, oldGet, remove_empty)
            if subdir_files:
                has_files = True
            elif remove_empty:
                possible_empty.append(dirent.path)
        else:
            # we don't delete folders that contain files (even 0-size ones)
            has_files = True
            rpFile = dirent.path[root_len:]
            oSize, oCrc, oDate = oldGet(rpFile) or (0, 0, 0.0)
            lstat_size, date = (st := dirent.stat()).st_size, st.st_mtime
            if lstat_size != oSize or date != oDate:
                siz_apath_mtime[rpFile] = (lstat_size,  dirent.path, date)
            else:
                new_sizeCrcDate[rpFile] = (oSize, oCrc, oDate)
    if possible_empty and has_files:
        for empty in possible_empty:
            GPath_no_norm(empty).removedirs(raise_error=False)
    # else let calling scope decide if we need to be removed
    return has_files

class Installer(ListInfo):
    """Object representing an installer archive, its user configuration, and
    its installation state."""
    #--Member data - do *not* add 'fn_key' in persistent
    persistent = ('order', 'group', 'ftime', 'fsize', 'crc',
        'fileSizeCrcs', 'bain_type', 'is_active', 'subNames', 'subActives',
        'dirty_sizeCrc', 'comments', 'extras_dict', 'packageDoc', 'packagePic',
        'src_sizeCrcDate', 'hasExtraData', 'skipVoices', 'espmNots', 'isSolid',
        'blockSize', 'overrideSkips', '_remaps', 'skipRefresh', 'fileRootIdex')
    volatile = ( # used when copying the installer do *not* add _file_key here
        'ci_dest_sizeCrc', 'skipExtFiles', 'skipDirFiles', 'status',
        'missingFiles', 'mismatchedFiles', 'project_refreshed', 'unSize',
        'espms', 'underrides', 'hasWizard', 'espmMap', 'hasReadme', 'hasBCF',
        'hasBethFiles', 'has_fomod_conf')

    #--Package analysis/porting.
    type_string = _('Unrecognized')
    screenshot_dirs = {'screenshots', 'screens', 'ss'}
    #--Will be skipped even if hasExtraData == True (bonus: skipped also on
    # scanning the game Data directory)
    dataDirsMinus = {'bash', '--'}
    docExts = {'.txt', '.rtf', '.htm', '.html', '.doc', '.docx', '.odt',
               '.mht', '.pdf', '.css', '.xls', '.xlsx', '.ods', '.odp',
               '.ppt', '.pptx', '.md', '.rst', '.url'}
    reReadMe = re.compile(
        f'^.*?([^{bolt.os_sep_re}]*)(read[ _]?me|lisez[ _]?moi)'
        f'([^{bolt.os_sep_re}]*)(' +
        '|'.join((f'\\{e}' for e in docExts)) + ')$', re.I)
    # Filename roots (i.e. filenames without extensions) that are common and
    # should be renamed by BAIN to avoid conflicts if they are used as doc
    # files (e.g. 'credits' means 'Credits.txt' etc. would be caught). May be
    # regexes too (which will be run on the filename root).
    _common_doc_roots = {'change[ _]?log', 'changes', 'credits', 'licen[cs]e',
                         'version[ _]?history'}
    re_common_docs = re.compile(f'^(.*)(?:{"|".join(_common_doc_roots)})(.*)$',
                                re.I)
    skipExts = ['.exe', '.py', '.pyc', '.7z', '.zip', '.rar', '.db', '.ace',
                '.tgz', '.tar', '.gz', '.bz2', '.omod', '.fomod', '.tb2',
                '.lzma', '.manifest', '.ckm', '.vortex_backup', '.ghost']
    skipExts = frozenset((*skipExts, *readExts))
    commonlyEditedExts = {'.cfg', '.ini', '.modgroups', '.toml', '.txt',
                          '.xml'}
    #--Regular game directories - needs update after bush.game has been set
    dataDirsPlus = {*screenshot_dirs, *bush.game.Bain.wrye_bash_data_dirs,
                    'docs'}
    # Files that may be installed in top Data/ directory - note that all
    # top-level file extensions commonly found in the wild need to go here,
    # even ones we'll end up skipping, since this is for the detection of
    # archive 'types' - not actually deciding which get installed
    _top_files_extensions = {'.bsl', '.ckm', '.csv', '.ini', '.modgroups',
        bush.game.Bsa.bsa_extension, *bush.game.espm_extensions}
    # Same as _top_files_extensions, plus doc extensions. Needed since we want
    # to allow top-level docs files in sub-packages, but we don't want them to
    # invalidate a type 2 package
    _top_files_plus_docs = _top_files_extensions | docExts
    _re_top_extensions = re.compile(
        f'(?:{"|".join(map(re.escape, _top_files_extensions))})$', re.I)
    _re_top_plus_docs = re.compile(
        f'(?:{"|".join(map(re.escape, _top_files_plus_docs))})$', re.I)
    # Extensions of strings files - automatically built from game constants
    _strings_extensions = {os.path.splitext(x[1])[1].lower()
                           for x in bush.game.Esp.stringsFiles}
    # InstallersData singleton - consider this tmp
    instData = None # type: InstallersData
    is_archive = is_project = is_marker = False ##: replace with inheritance if possible

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
        user_skipped = bass.inisettings['SkippedBashInstallersDirs'].split('|')
        InstallersData.installers_dir_skips.update(
            skipped.lower() for skipped in user_skipped if skipped)

    #--Class Methods ----------------------------------------------------------
    @staticmethod
    def getGhosted():
        """Returns map of real to ghosted files in mods directory."""
        dataDir = bass.dirs[u'mods']
        inodes = [*dataDir.ilist()] ##: will cache all of those as FName use glob?
        ghosts = [x.fn_body for x in inodes if x.fn_ext == u'.ghost']
        limbo = set(ghosts) & set(inodes) # they exist in both states
        return bolt.LowerDict(
            (x, x + u'.ghost') for x in ghosts if x not in limbo)

    @staticmethod
    def calc_crcs(to_calc, rootName, new_sizeCrcDate, progress):
        if not to_calc: return
        progress_msg = f'{rootName}\n' + _('Calculating CRCs…') + '\n'
        progress(0, progress_msg)
        progress.setFull(len(to_calc))
        for i, (rpFile, (siz, asFile, date)) in enumerate(dict_sort(to_calc)):
            progress(i, progress_msg + rpFile)
            final_crc = 0
            try:
                with open(asFile, u'rb') as ins:
                    while block := ins.read(2097152): # 2MB at a time
                        final_crc = crc32(block, final_crc)
            except OSError:
                deprint(
                    f'Failed to calculate crc for {asFile} - please report '
                    f'this, and the following traceback:', traceback=True)
            new_sizeCrcDate[rpFile] = (siz, final_crc, date) # crc = 0 on error

    #--Initialization, etc ----------------------------------------------------
    def __init__(self, fn_key, **kwargs):
        self.initDefault()
        ListInfo.__init__(self, f'{fn_key}')

    def initDefault(self):
        """Initialize everything to default values."""
        self.fn_key = FName('')
        #--Persistent: set by _fs_refresh called by _reset_cache
        self.ftime = 0 #--Modified date
        self.fsize = -1 #--size of archive file
        self.crc = 0 #--crc of archive
        self.isSolid = False #--archives only - solid 7z archive
        self.blockSize = None #--archives only - set here and there
        self.fileSizeCrcs = [] #--list of tuples for _all_ files in installer
        #--For InstallerProject's, cache if refresh projects is skipped
        self.src_sizeCrcDate = bolt.LowerDict() # also used to cache crc's.
        #--Set by _reset_cache
        self.fileRootIdex = 0 # len of the root path including the final separator
        # Package type: -1 -> corrupt; 0 -> unset/unrecognized; 1 -> simple;
        # 2 -> complex; 3 -> scattered
        self.bain_type = 0
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
        self.espmNots: set[FName] = set() #--Plugin FNames that user has decided not to install.
        self._remaps = bolt.FNDict() # Pickles to dict, equivalent to previous
        #--Volatiles (not pickled values)
        #--Volatiles: directory specific
        self.project_refreshed = False
        #--Volatile: set by refreshDataSizeCrc
        # LowerDict mapping destinations (relative to Data/ directory) of files
        # in this installer to their size and crc - built in refreshDataSizeCrc
        self.ci_dest_sizeCrc = bolt.LowerDict()
        self.has_fomod_conf = False
        self.hasWizard = False
        self.hasBCF = False
        self.espmMap: DefaultFNDict[FName, list[FName]] = DefaultFNDict(list)
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

    @property
    def num_of_files(self): return len(self.fileSizeCrcs)

    @staticmethod
    def number_string(number, marker_string=u''):
        return str(number)

    def size_string(self): return round_size(self.fsize)

    def size_info_str(self):
        return _('Size: %(package_size)s') % {
            'package_size': self.size_string()}

    # Accessors for encapsulating the semantic meaning of bain_type
    @property
    def has_recognized_structure(self):
        """Return True if this package has a recognized BAIN type (i.e. is not
        a corrupt or unrecognized package)."""
        return self.bain_type not in (-1, 0)

    @property
    def is_corrupt_package(self):
        """Return True if this package is corrupt, i.e. its data failed to
        load."""
        return self.bain_type == -1

    @property
    def is_simple_package(self):
        """Return True if this package is simple, i.e. it only contains some
        files and/or folders that should get directly placed into the Data
        folder."""
        return self.bain_type == 1

    @property
    def is_complex_package(self):
        """Return True if this package is complex, i.e. it contains a number of
        sub-packages that each behave like a simple package."""
        return self.bain_type == 2

    @property
    def is_scattered_package(self):
        """Return True if this package is scattered, i.e. it has no
        recognizable structure, but does include some kind of information to
        make sense of the chaos."""
        return self.bain_type == 3

    def structure_string(self):
        if self.is_simple_package:
            return _(u'Structure: Simple')
        elif self.is_complex_package:
            if len(self.subNames) == 2:
                return _(u'Structure: Complex/Simple')
            else:
                return _(u'Structure: Complex')
        elif self.is_scattered_package:
            # Currently the only type of scattered package we support
            return _('Structure: Scattered (FOMOD)')
        elif self.is_corrupt_package:
            return _(u'Structure: Corrupt/Incomplete')
        else:
            return _(u'Structure: Unrecognized')

    def log_package(self, log, showInactive):
        prefix = f'{self.order:03d}'
        package = self.fn_key
        if self.is_active:
            log(f'++ {prefix} - {package} ({self.crc:08X}) (Installed)')
        elif showInactive:
            log(f'-- {prefix} - {package} ({self.crc:08X}) (Not Installed)')

    def resetEspmName(self,currentName):
        oldName = self.getEspmName(currentName)
        del self._remaps[oldName]
        if currentName in self.espmNots:
            self.espmNots.discard(currentName)
            self.espmNots.add(FName(oldName))

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

    def setEspmName(self, currentName: FName, newName: FName):
        oldName = self.getEspmName(currentName)
        self._remaps[oldName] = newName
        if currentName in self.espmNots:
            self.espmNots.discard(currentName)
            self.espmNots.add(newName)
        else:
            self.espmNots.discard(newName)

    def isEspmRenamed(self,currentName):
        return self.getEspmName(currentName) != currentName

    def __reduce__(self):
        """Used by pickler to save object state."""
        bosh_clz = getattr(sys.modules['bash.bosh'], type(self).__name__)
        return bosh_clz, (self.fn_key,), (
            f'{self.fn_key}', *(getattr(self, a) for a in self.persistent))

    def __setstate__(self,values):
        """Used by unpickler to recreate object."""
        try:
            self.__setstate(values)
            return
        except FileNotFoundError as e:
            deprint(f'Pickled installer {values[0]} not found: {e}')
        except:
            deprint(f'Failed loading {values[0]}', traceback=True)
        self.fn_key = '' # reset self.fn_key to '' to remove self in __load()

    def get_hide_dir(self): ##: Copy-pasted from InstallersData.hidden_dir!
        return bass.dirs[u'modsBash'].join(u'Hidden')

    def __setstate(self,values):
        for a, v in zip(self.persistent, values[1:]):
            setattr(self, a, v)
        rescan = False
        ##: This is a whole load of backwards compat code - should be dropped
        # at some point in the (more or less far, depending on when the code
        # was added) future
        if not isinstance(self.extras_dict, dict):
            self.extras_dict = {}
            if self.fileRootIdex: # need to add 'root_path' key to extras_dict
                rescan = True
        if old_fm_dict := self.extras_dict.pop('fomod_dict', None):
            # Convert older version of the FOMOD handling dict, which did not
            # support multiple destinations for a single source file
            self.extras_dict['fomod_dict_v2'] = bolt.LowerDict(
                {k: {v} for k, v in old_fm_dict.items()})
        if isinstance(self.fn_key, bytes):
            deprint(f'{repr(self.fn_key)} in Installers.dat')
            self.fn_key = self.fn_key.decode('utf-8')
        if not isinstance(self.fn_key, FName):
            self.fn_key = FName(u'%s' % self.fn_key)
        if self.espmNots:
            self.espmNots = forward_compat_path_to_fn_list(self.espmNots,
                                                           ret_type=set)
        self._remaps = forward_compat_path_to_fn(self._remaps,
            value_type=lambda v: FName('%s' % v))  # Path -> FName
        if isinstance(self, _InstallerPackage):
            self._file_key = bass.dirs['installers'].join(self.fn_key)
            if not isinstance(self.src_sizeCrcDate, bolt.LowerDict):
                self.src_sizeCrcDate = bolt.LowerDict(
                    (u'%s' % x, y) for x, y in self.src_sizeCrcDate.items())
            if not isinstance(self.dirty_sizeCrc, bolt.LowerDict):
                self.dirty_sizeCrc = bolt.LowerDict(
                    (f'{x}', y) for x, y in self.dirty_sizeCrc.items())
            # on error __setstate__ resets fn_key -> entry dropped in __load()
            stat_tuple = self._stat_tuple()
            # refresh projects once on booting even if skipRefresh flag is
            # on but refresh archives only if changed
            rescan |= self.is_project or self._file_changed(stat_tuple)
            if rescan:
                dest_scr = self._reset_cache(stat_tuple)
            else:
                dest_scr = self.refreshDataSizeCrc()
            if self.overrideSkips:
                InstallersData.overridden_skips.update(dest_scr)

    #--refreshDataSizeCrc, err, framework -------------------------------------
    # Those files/folders will be always skipped by refreshDataSizeCrc()
    _silentSkipsStart = (
        '--', f'omod conversion data{os_sep}', f'wizard images{os_sep}')
    _silentSkipsEnd = (u'thumbs.db', u'desktop.ini', u'meta.ini',
                       u'__folder_managed_by_vortex')

    # global skips that can be overridden en masse by the installer
    _global_skips = []
    _global_start_skips = []
    _global_skip_extensions = set()
    # executables - global but if not skipped need additional processing
    _executables_ext = {'.dll', '.dlx', '.asi', '.jar'}
    _executables_process = {}
    _goodDlls = _badDlls = None
    @staticmethod
    def goodDlls(force_recalc=False):
        if force_recalc:
            Installer._goodDlls.clear()
            dlls = {k: [[FName(str(str(a))), b, c] for a, b, c in v] for k, v
                    in bass.settings['bash.installers.goodDlls'].items()}
            Installer._goodDlls.update(dlls)
        return Installer._goodDlls
    @staticmethod
    def badDlls(force_recalc=False):
        if force_recalc:
            Installer._badDlls.clear()
            dlls = {k: [[FName(str(str(a))), b, c] for a, b, c in v] for k, v
                    in bass.settings['bash.installers.badDlls'].items()}
            Installer._badDlls.update(dlls)
        return Installer._badDlls
    # while checking for skips process some installer attributes
    _attributes_process = {}

    @staticmethod
    def init_global_skips(ask_yes):
        """Update _global_skips with functions deciding if 'fileLower' (docs !)
        must be skipped, based on global settings. Should be updated on boot
        and on flipping skip settings - and nowhere else, hopefully."""
        del Installer._global_skips[:]
        del Installer._global_start_skips[:]
        Installer._global_skip_extensions.clear()
        if bass.settings[u'bash.installers.skipTESVBsl']:
            Installer._global_skip_extensions.add(u'.bsl')
        if bass.settings[u'bash.installers.skipScriptSources']:
            Installer._global_skip_extensions.update(
                bush.game.Psc.source_extensions)
        if bass.settings['bash.installers.skipPDBs']:
            Installer._global_skip_extensions.add('.pdb')
        # skips files starting with...
        if bass.settings[u'bash.installers.skipDistantLOD']:
            Installer._global_start_skips.append(u'distantlod')
        if bass.settings[u'bash.installers.skipLandscapeLODMeshes']:
            Installer._global_start_skips.append(bush.game.Bain.lod_meshes_dir)
        if bass.settings[u'bash.installers.skipScreenshots']:
            Installer._global_start_skips.extend(Installer.screenshot_dirs)
        # LOD textures
        skipLODTextures = bass.settings[
            u'bash.installers.skipLandscapeLODTextures']
        skipLODNormals = bass.settings[
            u'bash.installers.skipLandscapeLODNormals']
        skipAllTextures = skipLODTextures and skipLODNormals
        tex_gen = bush.game.Bain.lod_textures_dir
        normals_ext = f'{bush.game.Bain.lod_textures_normals_suffix}.dds'
        def _mk_lod_tex_func(normals):
            """Helper for generating a skip function fitting the current game
            and whether normal or diffuse textures are targeted."""
            if bush.game.fsName in ('Fallout3', 'FalloutNV'):
                if normals:
                    return lambda f: (f.startswith(tex_gen) and
                                      'normals' in f.split(os_sep))
                else:
                    return lambda f: (f.startswith(tex_gen) and
                                      'normals' not in f.split(os_sep))
            else:
                if normals:
                    return lambda f: (f.startswith(tex_gen) and
                                      f.endswith(normals_ext))
                else:
                    return lambda f: (f.startswith(tex_gen) and
                                      not f.endswith(normals_ext))
        if skipAllTextures:
            Installer._global_start_skips.append(tex_gen)
        elif skipLODTextures:
            Installer._global_skips.append(_mk_lod_tex_func(normals=False))
        elif skipLODNormals:
            Installer._global_skips.append(_mk_lod_tex_func(normals=True))
        # Skipped extensions
        skipObse = not bass.settings[u'bash.installers.allowOBSEPlugins']
        if skipObse:
            Installer._global_start_skips.append(
                bush.game.Se.plugin_dir.lower())
            Installer._global_skip_extensions |= Installer._executables_ext
        if bass.settings[u'bash.installers.skipImages']:
            Installer._global_skip_extensions |= bain_image_exts
        Installer._init_executables_skips(ask_yes)

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
        re_common_docs_match = Installer.re_common_docs.match
        docs_ = u'Docs' + os_sep
        ignore_doclike = {'masterlist.txt', 'dlclist.txt'}
        def _split_fr(file_relative):
            """Small helper for splitting up file_relative into parent
            directory and file name."""
            fr_split = file_relative.rsplit(os_sep, 1)
            return ('', fr_split[0]) if len(fr_split) == 1 else fr_split
        def _process_docs(self, fileLower, full, fileExt, file_relative, sub):
            maReadMe = reReadMeMatch(fileLower)
            if maReadMe and not self.hasReadme:
                self.hasReadme = full
            ##: Linux: test fileLower, full are os agnostic
            parent_dir, split_fn = _split_fr(file_relative)
            lower_parent = parent_dir.lower()
            lower_root = split_fn.lower()[:-len(fileExt)]
            package_root = self.fn_key.fn_body if self._valid_exts_re else \
                self.fn_key
            if lower_root in package_root.lower() and not self.hasReadme:
                # This is named similarly to the package (with a doc ext), so
                # probably a readme
                self.hasReadme = full
            if (not self.overrideSkips
                    and bass.settings['bash.installers.skipDocs']
                    and fileLower not in bush.game.Bain.no_skip
                    and fileExt not in bush.game.Bain.no_skip_dirs.get(
                        lower_parent, [])
                    and not any(nsr.match(fileLower) for nsr in
                                bush.game.Bain.no_skip_regexes)):
                return None # skip
            dest = file_relative
            if bass.settings['bash.installers.rename_docs']:
                dest_start = (parent_dir + os_sep) if parent_dir else ''
                # Rename docs with common names that will otherwise easily
                # conflict to more unique names (by including the package
                # name's root)
                if not parent_dir or lower_parent == 'docs':
                    ma_cd = re_common_docs_match(lower_root)
                    if ma_cd and not (ma_cd.group(1) or ma_cd.group(2)):
                        dest = dest_start + package_root + ' ' + split_fn
                    elif maReadMe and not (maReadMe.group(1) or
                                           maReadMe.group(3)):
                        dest = dest_start + package_root + fileExt
            if not parent_dir:
                if fileLower == 'package.txt':
                    dest = docs_ + package_root + '.package.txt'
                    self.packageDoc = dest
                elif fileLower in ignore_doclike:
                    self.skipDirFiles.add(full)
                    return None # we don't want to install those files
                elif bass.settings['bash.installers.redirect_docs']:
                    if (fileLower not in bush.game.Bain.no_skip
                            and not any(nsr.match(fileLower) for nsr in
                                        bush.game.Bain.no_skip_regexes)):
                        # Move top-level docs to the Docs folder
                        dest = docs_ + dest
            return dest
        attr_process = Installer._attributes_process
        for ext in Installer.docExts:
            attr_process [ext] = _process_docs
        def _process_BCF(self, fileLower, full, fileExt, file_relative, sub):
            if fileLower[-7:-3] == u'-bcf' or u'-bcf-' in fileLower: ##: DOCS!
                self.hasBCF = full
                return None # skip
            return file_relative
        attr_process[defaultExt] = _process_BCF # .7z
        def _process_txt(self, fileLower, full, fileExt, file_relative, sub):
            if fileLower == u'wizard.txt': # first check if it's the wizard.txt
                self.hasWizard = full
                return None # skip
            return _process_docs(self, fileLower, full, fileExt, file_relative,
                                 sub)
        attr_process['.txt'] = _process_txt
        def _process_csv(self, fileLower, full, fileExt, file_relative, sub):
            parent_dir, split_fn = _split_fr(file_relative)
            if (not parent_dir and
                    bass.settings['bash.installers.redirect_csvs']):
                return f'Bash Patches{os_sep}{split_fn}'
            return file_relative
        attr_process['.csv'] = _process_csv
        def _remap_espms(self, fileLower, full, fileExt, file_relative, sub):
            rootLower = file_relative.split(os_sep, 1)
            if len(rootLower) > 1:
                self.skipDirFiles.add(full)
                return None # we dont want to install those files
            if fileLower in bush.game.bethDataFiles:
                self.hasBethFiles = True
                if not self.overrideSkips and not bass.settings[
                    u'bash.installers.autoRefreshBethsoft']:
                    self.skipDirFiles.add(_('[Vanilla Content]') + f' {full}')
                    return None # FIXME - after renames ?
            fn_mod = FName(file_relative)
            fn_mod = self._remaps.get(fn_mod, fn_mod)
            if fn_mod not in self.espmMap[sub]: ##: why this check/ - renames?
                self.espmMap[sub].append(fn_mod)
            self.espms.add(fn_mod)
            if fn_mod in self.espmNots: return None # skip
            return str(fn_mod) # will end up in a LowerDict - so str
        for extension in bush.game.espm_extensions:
            attr_process[extension] = _remap_espms

    def _init_skips(self):
        voice_dir = os_sep.join(('sound', 'voice'))
        start = [voice_dir] if self.skipVoices else []
        skips, skip_ext = [], set()
        if not self.overrideSkips:
            skips = list(Installer._global_skips)
            start.extend(Installer._global_start_skips)
            skip_ext = Installer._global_skip_extensions
        if start:
            # Calculate these ahead of time
            start_tup = tuple(x + os_sep for x in start)
            skips.append(lambda f: f.startswith(start_tup))
        if not self.skipVoices and self.espmNots:
            def _skip_espm_voices(fileLower):
                farPos = fileLower.startswith( # 'sound\\voice\\', 12 chars
                    voice_dir) and fileLower.find(os_sep, 12)
                return farPos > 12 and fileLower[12:farPos] in self.espmNots
            skips.append(_skip_espm_voices)
        return skips, skip_ext

    @staticmethod
    def _init_executables_skips(ask_yes):
        if force_recalc := (Installer._goodDlls is Installer._badDlls is None):
            Installer._goodDlls = defaultdict(list)
            Installer._badDlls = defaultdict(list)
        goodDlls = Installer.goodDlls(force_recalc)
        badDlls = Installer.badDlls(force_recalc)
        def __skipExecutable(checkOBSE, fileLower, full, archiveRoot, dll_size,
                             crc, exeDir):
            if not fileLower.startswith(exeDir): return True
            if fileLower in badDlls and [archiveRoot, dll_size, crc] in \
                    badDlls[fileLower]: return True
            if not checkOBSE or fileLower in goodDlls and [archiveRoot,
                dll_size, crc] in goodDlls[fileLower]: return False
            message = Installer._dllMsg(fileLower, full, archiveRoot,
                                        badDlls, goodDlls)
            ##: was balt.Link.Frame <=> None?
            if not ask_yes(None, message, _('Executable Binary Warning')):
                badDlls[fileLower].append([archiveRoot, dll_size, crc])
                bass.settings[u'bash.installers.badDlls'] = Installer._badDlls
                return True
            goodDlls[fileLower].append([archiveRoot, dll_size, crc])
            bass.settings[u'bash.installers.goodDlls'] = Installer._goodDlls
            return False
        if bush.game.Se.se_abbrev:
            _obse = partial(__skipExecutable,
                    exeDir=(bush.game.Se.plugin_dir.lower() + os_sep))
            Installer._executables_process['.dll'] = \
            Installer._executables_process['.dlx'] = _obse
        if bush.game.Sd.sd_abbrev:
            _asi = partial(__skipExecutable,
                   exeDir=(bush.game.Sd.install_dir.lower() + os_sep))
            Installer._executables_process['.asi'] = _asi
        if bush.game.Sp.sp_abbrev:
            _jar = partial(__skipExecutable,
                   exeDir=(bush.game.Sp.install_dir.lower() + os_sep))
            Installer._executables_process['.jar'] = _jar

    @staticmethod
    def _dllMsg(fileLower, full, archiveRoot, badDlls, goodDlls):
        message = [_('This package (%(source_package)s) contains an '
                     'executable binary file (%(executable_name)s). Such '
                     'files can be malicious and hence you should be very '
                     'sure you know what this file is and that it is '
                     'legitimate. Are you sure you want to install this?') % {
            'source_package': archiveRoot, 'executable_name': full}]
        if fileLower in goodDlls:
            message.append(_('You have previously chosen to install an '
                             'executable binary with the same name, but with '
                             'a different size, CRC and/or source package '
                             'name.'))
        elif fileLower in badDlls:
            message.append(_('You have previously chosen NOT to install an '
                             'executable binary with the same name, but with '
                             'a different size, CRC and/or source archive '
                             'name.'))
            message.append(_('Make EXTRA sure you want to install this one '
                             'before saying yes.'))
        return '\n\n'.join(message)

    def refreshDataSizeCrc(self, checkOBSE=False, *, splitExt=os.path.splitext,
                           __skip_exts: set[str] = skipExts):
        """Update self.ci_dest_sizeCrc and related variables and return
        dest_src map for install operation. ci_dest_sizeCrc is a dict that maps
        CIstr paths _relative to the Data dir_ (the locations the files will
        end up to if installed) to (size, crc) tuples.

        WIP rewrite
        Used:
         - in __setstate__ to construct the installers from Installers.dat,
         used once (and in full refresh ?)
         - in _reset_cache, after refreshing persistent attributes - track
         call graph from here should be the path that needs optimization (
         irefresh, ShowPanel ?)
         - in InstallersPanel.refreshCurrent()
         - in 2 subclasses' install() and InstallerProject.sync_from_data()
         - in _Installers_Skip._do_installers_refresh()
         - in _RefreshingLink (override skips, HasExtraData, skip voices)
         - in Installer_CopyConflicts
        """
        # Init to empty - this has to reset everything that this method might
        # touch so that the early return from bad archives works correctly
        self.has_fomod_conf = self.hasBethFiles = False
        self.hasWizard = self.hasBCF = self.hasReadme = False
        self.packageDoc = self.packagePic = None
        self.unSize = 0
        for inst_attr in {'skipExtFiles', 'skipDirFiles', 'espms'}:
            ##: is the object. necessary?
            object.__getattribute__(self, inst_attr).clear()
        dest_src = bolt.LowerDict()
        if not self.has_recognized_structure:
            # If an archive became unrecognized, mark everything that was in it
            # as dirty and clear the destination dict
            if self.is_active:
                dirty_sizeCrc = self.dirty_sizeCrc
                for filename, sizeCrc in self.ci_dest_sizeCrc.items():
                    if filename not in dirty_sizeCrc:
                        dirty_sizeCrc[filename] = sizeCrc
            self.ci_dest_sizeCrc.clear()
            return dest_src
        archiveRoot = self.fn_key.fn_body if self._valid_exts_re else \
            self.fn_key
        docExts = self.docExts
        dataDirsPlus = self.dataDirsPlus
        dataDirsMinus = self.dataDirsMinus
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
            language_lower = oblivionIni.get_ini_language(
                bush.game.Ini.default_game_lang).lower()
        else:
            language_lower = ''
        hasExtraData = self.hasExtraData
        # exclude '' from active sub-packages
        activeSubs = (
            {x for x, y in zip(self.subNames[1:], self.subActives[1:]) if y}
            if self.is_complex_package else set())
        data_sizeCrc = bolt.LowerDict()
        skipDirFiles = self.skipDirFiles
        skipDirFilesAdd = skipDirFiles.add
        skipDirFilesDiscard = skipDirFiles.discard
        skipExtFilesAdd = self.skipExtFiles.add
        commonlyEditedExts = Installer.commonlyEditedExts
        espmMap = self.espmMap = bolt.DefaultFNDict(list)
        plugin_extensions = bush.game.espm_extensions
        # FIXME DROP: reReadMeMatch = Installer.reReadMe.match
        #--Scan over fileSizeCrcs
        root_path = self.extras_dict.get(u'root_path', u'')
        rootIdex = len(root_path)
        fm_active = self.extras_dict.get(u'fomod_active', False)
        fm_dict = self.extras_dict.get('fomod_dict_v2', {})
        module_config = os.path.join(u'fomod', u'moduleconfig.xml')
        iprocess = Installer._attributes_process
        for full, cached_size, crc in self.fileSizeCrcs:
            if rootIdex: # exclude all files that are not under root_dir
                if not full.startswith(root_path): continue
            full_rel = full[rootIdex:]
            full_rel_lower = full_rel.lower()
            if (full_rel_lower.startswith(Installer._silentSkipsStart) or
                    full_rel_lower.endswith(Installer._silentSkipsEnd)):
                # Skip top level '--', etc.
                continue
            elif full_rel_lower == module_config:
                self.has_fomod_conf = full
                skipDirFilesDiscard(full_rel)
                continue
            fm_present = full in fm_dict
            if fm_active and fm_present:
                # Remap selected FOMOD files to usable paths - note fm_dict may
                # map to >1 output file
                files_to_process = fm_dict[full]
            else:
                files_to_process = [full_rel]
            for file_relative in files_to_process:
                fileLower = file_relative.lower()
                sub = ''
                # Complex archive; skip the logic if FOMOD mode is active
                # (since sub-package selection doesn't (currently) work in
                # FOMOD mode anyways)
                if self.is_complex_package and not fm_active:
                    split = file_relative.split(os_sep, 1)
                    if len(split) > 1:
                        # redefine file, excluding the sub-package directory
                        sub,file_relative = split
                        fileLower = file_relative.lower()
                        if fileLower.startswith(Installer._silentSkipsStart):
                            continue # skip sub-package level '--', etc
                    if sub not in activeSubs:
                        if sub == '':
                            skipDirFilesAdd(file_relative)
                        # Run a modified version of the normal checks, just
                        # looking for esp's for the wizard espmMap, wizard.txt
                        # and readme's
                        rootLower,fileExt = splitExt(fileLower)
                        rootLower = rootLower.split(os_sep, 1)
                        if len(rootLower) == 1: rootLower = ''
                        else: rootLower = rootLower[0]
                        skip = True
                        sub_esps = espmMap[sub] # add sub key to the espmMap
                        if fileLower == 'wizard.txt':
                            self.hasWizard = full
                            skipDirFilesDiscard(file_relative)
                            continue
                        elif fileExt == defaultExt and (
                                fileLower[-7:-3] == '-bcf' or
                                '-bcf-' in fileLower):
                            self.hasBCF = full
                            skipDirFilesDiscard(file_relative)
                            continue
                        elif fileExt in docExts and sub == '':
                            skipDirFilesDiscard(file_relative)
                            skip = False
                        elif fileLower in bethFiles:
                            self.hasBethFiles = True
                            skipDirFilesDiscard(file_relative)
                            skipDirFilesAdd(_('[Vanilla Content]') + ' ' +
                                            file_relative)
                            continue
                        elif not rootLower and fileExt in plugin_extensions:
                            #--Remap plugins as defined by the user
                            if file_relative in self._remaps:
                                file_relative = self._remaps[file_relative]
                                # No need to update fileLower, will skip
                            else:
                                file_relative = FName(file_relative)
                            ##: do we need this test? see also _remap_espms
                            if file_relative not in sub_esps:
                                sub_esps.append(file_relative)
                            ##: _remap_espms adds also to self.espms - should we do this here too?
                        if skip:
                            continue
                # Add sub key to the espmMap, needed in belt
                espmMap.setdefault(sub, [])
                rootLower,fileExt = splitExt(fileLower)
                rootLower = rootLower.split(os_sep, 1)
                if len(rootLower) == 1:
                    rootLower = ''
                else:
                    rootLower = rootLower[0]
                #--Skips
                for lam in skips:
                    if lam(fileLower):
                        _out = True
                        break
                else:
                    _out = False
                if _out:
                    continue
                dest = None # destination of the file relative to the Data/ dir
                # process attributes and define destination for docs and images
                # (if not skipped globally)
                if fileExt in iprocess:
                    # we don't use EAFP in case a KeyError is raised in callee
                    dest = iprocess[fileExt](
                        self, fileLower, full, fileExt, file_relative, sub)
                    if dest is None:
                        continue
                if fm_active and not fm_present:
                    # Pretend all unselected FOMOD files don't exist, but only
                    # after giving them a chance to process up above - that way
                    # packages that include both a wizard and an FOMOD
                    # installer will work (as well as BCFs)
                    continue
                if fileExt in global_skip_ext: continue # docs treated above
                elif fileExt in Installer._executables_process: # and handle execs
                    if Installer._executables_process[fileExt](checkOBSE,
                            fileLower, full, archiveRoot, cached_size, crc):
                        continue
                #--Noisy skips
                if fileLower in bethFiles:
                    self.hasBethFiles = True
                    if bethFilesSkip:
                        skipDirFilesAdd(_('[Vanilla Content]') + ' ' + full)
                        continue
                elif (not hasExtraData and rootLower and
                      rootLower not in dataDirsPlus):
                    skipDirFilesAdd(full)
                    continue
                elif hasExtraData and rootLower and rootLower in dataDirsMinus:
                    skipDirFilesAdd(full)
                    continue
                elif fileExt in __skip_exts:
                    skipExtFilesAdd(full)
                    continue
                #--Remap docs, strings
                if dest is None: dest = file_relative
                dest = self._remap_files(
                    dest, fileLower, rootLower, fileExt, file_relative,
                    data_sizeCrc, archiveRoot, renameStrings, language_lower,
                    redirect_scripts)
                if fileExt in commonlyEditedExts:
                    ##: will track all the txt files in Docs/
                    InstallersData.track(bass.dirs['mods'].join(dest))
                #--Save
                data_sizeCrc[dest] = (cached_size, crc)
                dest_src[dest] = full
                unSize += cached_size
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
        for full, _cached_size, crc in self.fileSizeCrcs:
            fileLower = full.lower()
            if fileLower.startswith(skips_start): continue
            frags = full.split(_os_sep)
            if len(frags) == 1:
                # Files in the root of the package, start there
                break
            else:
                dirName = frags[0]
                if dirName.lower() == 'fomod':
                    # Special case: fomod dir is the root -> scattered
                    break
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
                    # an accepted Data sub-folder, or an fomod folder (in which
                    # case this is a scattered package)
                    rootDirKey = list(rootDirs)[0]
                    rootDirKeyL = rootDirKey.lower()
                    if (rootDirKeyL in dataDirsPlus or
                            rootDirKeyL == data_dir or
                            rootDirKeyL == 'fomod'):
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
                     data_sizeCrc, archiveRoot, renameStrings, language_lower,
                     redirect_scripts):
        """Renames and redirects files to other destinations in the Data
        folder."""
        # Redirect docs to the Docs folder
        if rootLower in self.screenshot_dirs:
            dest = os_sep.join((u'Docs', file_relative[len(rootLower) + 1:]))
        # Rename strings files if the option is set
        elif (renameStrings and fileExt in self._strings_extensions
              and fileLower.startswith(u'strings' + os_sep)):
            langSep = fileLower.rfind(u'_')
            extSep = fileLower.rfind(u'.')
            lang = fileLower[langSep + 1:extSep]
            if lang != language_lower:
                dest = ''.join((file_relative[:langSep], '_', lang,
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
            elif fileExt in bain_image_exts:
                dest = os_sep.join(('Docs', file_relative))
        return dest

    def refreshStatus(self, installersData):
        """Updates missingFiles, mismatchedFiles and status.
        Status:
        30: installed (green)
        20: mismatches (yellow)
        10: mismatches (orange)
        0: unconfigured (white)
        -10: missing files (red)
        -20: bad type (grey)
        """
        data_sizeCrc = self.ci_dest_sizeCrc
        get_cached = installersData.data_sizeCrcDate.get
        ci_underrides_sizeCrc = installersData.ci_underrides_sizeCrc
        missing = self.missingFiles
        mismatched = self.mismatchedFiles
        underrides = set()
        status = 0
        missing.clear()
        mismatched.clear()
        if not self.has_recognized_structure:
            status = -20
        elif data_sizeCrc:
            for filename,sizeCrc in data_sizeCrc.items():
                sizeCrcDate = get_cached(filename)
                if not sizeCrcDate:
                    missing.add(filename)
                elif sizeCrc != sizeCrcDate[:2]:
                    mismatched.add(filename)
                if sizeCrc == ci_underrides_sizeCrc.get(filename):
                    underrides.add(filename)
            if missing: status = -10
            elif any(ModInfos.rightFileType(f) for f in mismatched):
                status = 10
            elif mismatched: status = 20
            else: status = 30
        #--Clean Dirty
        dirty_sizeCrc = self.dirty_sizeCrc
        for filename, sizeCrc in list(dirty_sizeCrc.items()):
            sizeCrcDate = get_cached(filename)
            if (not sizeCrcDate or sizeCrc != sizeCrcDate[:2] or
                sizeCrc == data_sizeCrc.get(filename)
                ):
                del dirty_sizeCrc[filename]
        #--Done
        changed = self.status != status or self.underrides != underrides
        self.status, self.underrides = status, underrides
        return changed

    #--Utility methods --------------------------------------------------------
    def packToArchive(self, project, fn_archive, isSolid, blockSize,
                      progress=None, release=False):
        """Packs project to build directory. Release filters out development
        material from the archive. Needed for projects and to repack archives
        when syncing from Data."""
        if not self.num_of_files: return
        outDir = bass.dirs['installers']
        #--Dump file list
        with TempFile(temp_prefix='temp_list', temp_suffix='.txt') as tl:
            with open(tl, 'w', encoding='utf-8') as out:
                if release:
                    out.write('*thumbs.db\n')
                    out.write('*desktop.ini\n')
                    out.write('*meta.ini\n')
                    out.write('--*\\')
            compress7z(outDir.join(fn_archive), outDir.join(project), progress,
                       is_solid=isSolid, temp_list=tl, blockSize=blockSize)

class _InstallerPackage(Installer, AFileInfo):
    """Installer that corresponds to a file system node (archive or folder)."""

    def __init__(self, fn_key, progress=None, load_cache=False):
        super().__init__(fn_key) # will call Installer -> ListInfo __init__
        self._file_key = bass.dirs['installers'].join(self.fn_key)
        if load_cache: # load from disc, useful when adding a new installer
            AFile.__init__(self, self._file_key, progress=progress)

    def _reset_cache(self, stat_tuple=None, *, __skips_start=tuple(
            s.replace(os_sep, '') for s in Installer._silentSkipsStart),
            __os_sep=os_sep, **kwargs):
        """Extract file/size/crc and BAIN structure info from installer."""
        try:
            self._fs_refresh(kwargs.pop('progress', bolt.Progress()),
                             stat_tuple or self._stat_tuple(), **kwargs)
        except InstallerArchiveError:
            # size, modified and some of fileSizeCrcs may be set
            self.bain_type = -1
            return bolt.LowerDict()
        self._find_root_index()
        # fileRootIdex now points to the start in the file strings to ignore
        #--Type, subNames
        found_bain_type = 0
        subNameSet = {''}
        valid_top_ext = self.__class__._re_top_extensions.search
        valid_sub_top_ext = self.__class__._re_top_plus_docs.search
        dataDirsPlus = self.dataDirsPlus
        # hasExtraData is NOT taken into account when calculating package
        # structure or the root_path
        root_path = self.extras_dict.get('root_path', '')
        module_config = os.path.join('fomod', 'moduleconfig.xml')
        found_module_config = False
        # break if type is 1 else churn on
        for full, _cached_size, crc in self.fileSizeCrcs:
            if root_path: # exclude all files that are not under root_dir
                if not full.startswith(root_path): continue
                full = full[self.fileRootIdex:]
            if (full_lower := full.lower()).startswith(__skips_start):
                continue
            if full_lower.endswith(module_config):
                found_module_config = True
            frags = full.split(__os_sep)
            nfrags = len(frags)
            f0_lower = frags[0].lower()
            #--Type 1? break! data files/dirs are not allowed in type 2 top
            if (nfrags == 1 and valid_top_ext(f0_lower) or
                nfrags > 1 and f0_lower in dataDirsPlus):
                found_bain_type = 1
                break
            #--Else churn on to see if we have a Type 2 package
            elif not frags[0] in subNameSet and not \
                    f0_lower.startswith(__skips_start) and (
                    (nfrags > 2 and frags[1].lower() in dataDirsPlus) or
                    (nfrags == 2 and valid_sub_top_ext(frags[1]))):
                subNameSet.add(frags[0])
                found_bain_type = 2
                # keep looking for a type 1 package - having a loose file or a
                # top directory with name in dataDirsPlus will turn this into a
                # type 1 package
        if found_bain_type == 0 and found_module_config:
            # Type 3 - scattered, but we've got an FOMOD to guide us
            found_bain_type = 3
        self.bain_type = found_bain_type
        #--SubNames, SubActives
        if self.is_complex_package:
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

    def _fs_refresh(self, progress, stat_tuple, **kwargs):
        """Refresh fileSizeCrcs, fsize, and ftime from source
        archive/directory. Only called in _reset_cache. kwargs:
            - recalculate_project_crc: only used in InstallerProject override
        """
        raise NotImplementedError

    #--ABSTRACT ---------------------------------------------------------------
    def install(self, destFiles: set[CIstr], progress=None):
        """Install specified files to Data directory."""
        dest_src = self.refreshDataSizeCrc(True)
        for k in list(dest_src):
            if k not in destFiles: del dest_src[k]
        if not dest_src: return bolt.LowerDict(), set(), set(), set()
        progress = progress if progress else bolt.Progress()
        return self._install(dest_src, progress)

    def _install(self, dest_src, progress):
        raise NotImplementedError

    def _fs_install(self, dest_src, srcDirJoin, progress, subprogressPlus,
                    unpackDir):
        """Filesystem install, if unpackDir is not None we are installing
         an archive."""
        data_sizeCrcDate_update = bolt.LowerDict()
        data_sizeCrc = self.ci_dest_sizeCrc
        stores = data_tracking_stores()
        store_to_paths = defaultdict(set)
        sources_dests = defaultdict(set)
        join_data_dir = bass.dirs[u'mods'].join
        for dest, src in dest_src.items():
            dest_size, crc = data_sizeCrc[dest]
            # Work with ghosts lopped off internally and check the destination,
            # since plugins may have been renamed
            for store in stores:
                if fname_key := store.data_path_to_info(dest, would_be=True):
                    try: # FName
                        dest_path = store.store_dir.join(fname_key)
                    except TypeError: # info is present, possibly ghosted
                        dest_path = fname_key.abs_path
                        fname_key = fname_key.fn_key
                    store_to_paths[store].add((fname_key, dest))
                    break
            else:
                dest_path = join_data_dir(dest)
            data_sizeCrcDate_update[dest] = [dest_size, crc, -1]
            # Append the ghost extension JIT since the FS operation below will
            # need the exact path to copy to
            sources_dests[srcDirJoin(src)].add(dest_path)
            subprogressPlus()
        #--Now Move
        try:
            if data_sizeCrcDate_update:
                fs_operation = env.shellMove if unpackDir else env.shellCopy
                fs_operation(sources_dests, progress.getParent())
        finally:
            #--Clean up unpack dir if we're an archive
            if unpackDir:
                cleanup_temp_dir(unpackDir)
        # Update relevant data stores, adding new/modified files
        refresh_ui = defaultdict(bool)
        for store, owned_files in store_to_paths.items():
            lo_append = []
            for (owned_file, dest) in owned_files:
                try:
                    inf = store.new_info(owned_file, owner=self.fn_key,
                         # we refresh info sets in cached_lo_append_if_missing
                         _in_refresh=True)
                    data_sizeCrcDate_update[dest][2] = inf.ftime
                    lo_append.append(owned_file)
                except FileError as error: # repeated from refresh
                    store.corrupted[owned_file] = Corrupted(owned_file,
                                                            error.message)
                    store.pop(owned_file, None)
            if lo_append:
                refresh_ui[store.unique_store_key] = True
                if store.unique_store_key is Store.MODS:
                    store.cached_lo_append_if_missing(lo_append)
                    store.refreshLoadOrder(unlock_lo=True)
        #--Update Installers data
        return data_sizeCrcDate_update, refresh_ui

    def listSource(self):
        """Return package structure as text."""
        log = bolt.LogFile(io.StringIO())
        log.setHeader(f'{self} ' + _('Package Structure:'))
        log('[spoiler]\n', False) ##: do we need these spoiler tags?
        self._list_package(self.abs_path, log)
        log('[/spoiler]')
        return log.out.getvalue()

    @staticmethod
    def _list_package(apath, log):
        raise NotImplementedError

    def sync_from_data(self, delta_files: set[CIstr], progress):
        """Updates this installer according to the specified files in the Data
        directory.

        :param delta_files: The missing or mismatched files to sync.
        :param progress: A progress dialog to use when syncing."""
        raise NotImplementedError

    def _do_sync_data(self, proj_dir, delta_files: set[CIstr], progress):
        """Performs a Sync From Data on the specified project directory with
        the specified missing or mismatched files."""
        data_dir_join = bass.dirs[u'mods'].join
        norm_ghost_get = Installer.getGhosted().get
        upt_numb = del_numb = 0
        proj_dir_join = proj_dir.join
        progress.setFull(len(delta_files))
        for rel_src, rel_dest in self.refreshDataSizeCrc().items():
            if rel_src not in delta_files: continue
            progress(del_numb + upt_numb,
                     _('Syncing from %(data_folder)s folder…') % {
                         'data_folder': bush.game.mods_dir} + f'\n{rel_src}')
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
            _remove_empty_dirs(proj_dir)
        return upt_numb, del_numb

    def open_readme(self): self._open_txt_file(self.hasReadme)
    def open_wizard(self): self._open_txt_file(self.hasWizard)
    def open_fomod_conf(self): self._open_txt_file(self.has_fomod_conf)
    def _open_txt_file(self, rel_path): raise NotImplementedError

    def _make_wizard_file_dir(self, wizard_file_name, progress):
        """Abstract method that should return a directory containing the
        specified wizard file and all files needed to run it.
        :param progress: only used for archives where we unpack to dir."""
        raise NotImplementedError

    def get_wizard_file_dir(self, progress):
        """Return a path to a directory containing all files needed for a
        BAIN wizard to run."""
        return self._make_wizard_file_dir(self.hasWizard, progress)

    def get_fomod_file_dir(self, progress):
        """Return a path to a directory containing all files needed for an
        FOMOD to run."""
        return self._make_wizard_file_dir(self.has_fomod_conf, progress)

#------------------------------------------------------------------------------
class InstallerMarker(Installer):
    """Represents a marker installer entry."""
    type_string = _('Marker')
    _is_filename = False
    is_marker = True

    @staticmethod
    def _new_name(base_name, count):
        return f'=={base_name.strip("=")}{f" ({count})"}=='

    def unique_key(self, new_root, ext=u'', add_copy=False):
        new_name = new_root + (f" {_('Copy')}" if add_copy else '')
        if f'{new_name}' == f'{self.fn_key}': # allow change of case
            return None
        return self.unique_name(new_name)

    @classmethod
    def rename_area_idxs(cls, text_str, start=0, stop=None):
        """Markers, change the selection to not include the '=='."""
        if text_str[:2] == text_str[-2:] == u'==':
            return 2, len(text_str) - 2
        return 0, len(text_str)

    def initDefault(self):
        super().initDefault()
        self.ftime = time.time()

    @property
    def num_of_files(self): return -1

    @staticmethod
    def number_string(number, marker_string=u''): return marker_string

    def size_string(self): return u''

    def size_info_str(self): return _('Size: N/A')

    def structure_string(self): return _('Structure: N/A')

    def log_package(self, log, showInactive):
        log(f'{f"{self.order:03d}"} - {self.fn_key}')

#------------------------------------------------------------------------------
class InstallerArchive(_InstallerPackage):
    """Represents an archive installer entry."""
    type_string = _('Archive')
    _valid_exts_re = fr'(\.(?:{"|".join(e[1:] for e in archives.readExts)}))'
    is_archive = True

    def size_info_str(self):
        if self.isSolid:
            if self.blockSize:
                sSolid = _('Solid, Block Size: %(block_size)s') % {
                    'block_size': f'{self.blockSize}MB'}
            elif self.blockSize is None:
                sSolid = _('Solid, Block Size: Unknown')
            else:
                sSolid = _('Solid, Block Size: 7z Default')
        else:
            sSolid = _('Non-solid')
        return _('Size: %(package_size)s (%(package_solid)s)') % {
            'package_size': self.size_string(), 'package_solid': sSolid}

    @classmethod
    def validate_filename_str(cls, name_str, allowed_exts=archives.writeExts,
                              use_default_ext=False, __7z=archives.defaultExt):
        r, e = os.path.splitext(name_str)
        if allowed_exts and e.lower() not in allowed_exts:
            if not use_default_ext: # renaming as opposed to creating the file
                msg = _('%(invalid_name)s does not have correct extension '
                        '(%(allowed_extensions)s).') % {
                    'invalid_name': name_str,
                    'allowed_extensions': ', '.join(allowed_exts)}
                return msg, None
            msg = _('The %(invalid_extension)s extension is unsupported. '
                    'Using %(default_extension)s instead.') % {
                'invalid_extension': e, 'default_extension': __7z}
            name_str, e = r + __7z, __7z
        else:
            msg = ''
        # Skip Installer's validate_filename_str
        name_path, root = super(Installer, cls).validate_filename_str(
            name_str, {e})
        if root is None:
            return name_path, None
        if msg: # propagate the msg for extension change
            return name_path, (root, msg)
        return name_path, root

    #--File Operations --------------------------------------------------------
    def _fs_refresh(self, progress, stat_tuple, **kwargs):
        """Refresh fileSizeCrcs, fsize, ftime, crc, isSolid from archive."""
        #--Basic file info
        super(Installer, self)._reset_cache(stat_tuple)
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
        """Extract specified files from archive to a temporary directory.
        progress will be zeroed so pass a SubProgress in. Returns the path of
        the temporary directory the files were extracted to, the caller is
        responsible for cleaning it up.

        :param fileNames: File names (not paths)."""
        if not fileNames:
            raise ArgumentError(f'No files to extract for {self}.')
        if progress:
            progress.state = 0
            progress.setFull(len(fileNames))
        with TempFile(temp_prefix='temp_list', temp_suffix='.txt') as tl:
            with open(tl, 'w', encoding='utf8') as out:
                out.write('\n'.join(fileNames))
            unpack_dir = new_temp_dir()
            try:
                extract7z(self.abs_path, unpack_dir, progress,
                    recursive=recurse, filelist_to_extract=tl)
            finally:
                ##: Why are we doing this at all? We have a ton of extract7z
                # calls, but only two do clearReadOnly afterwards
                bolt.clearReadOnly(unpack_dir)
        return GPath_no_norm(unpack_dir)

    def _install(self, dest_src, progress):
        #--Extract
        progress(0, ('%s\n' % self) + _('Extracting files…'))
        unpackDir = self.unpackToTemp(list(dest_src.values()),
                                      SubProgress(progress, 0, 0.9))
        #--Rearrange files
        progress(0.9, ('%s\n' % self) + _('Organizing files…'))
        srcDirJoin = unpackDir.join
        subprogress = SubProgress(progress,0.9,1.0)
        subprogress.setFull(len(dest_src))
        subprogressPlus = subprogress.plus
        return self._fs_install(dest_src, srcDirJoin, progress,
                                subprogressPlus, unpackDir)

    def unpackToProject(self, project, progress):
        """Unpacks archive to build directory."""
        files = bolt.sortFiles([x[0] for x in self.fileSizeCrcs])
        if not files: return 0
        #--Clear Project
        destDir = bass.dirs[u'installers'].join(project)
        destDir.rmtree(safety=u'Installers')
        #--Extract
        progress(0, f'{project}\n' + _('Extracting files…'))
        unpack_dir = self.unpackToTemp(files, SubProgress(progress, 0, 0.9))
        #--Move
        progress(0.9, f'{project}\n' + _('Moving files…'))
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
        cleanup_temp_dir(unpack_dir)
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
            log(u'  ' * node.count(os_sep) + os.path.split(node)[1] + (
                os_sep if isdir_ else u''))

    def _open_txt_file(self, rel_path):
        # Let the atexit handler clean up these temp files. Some editors do
        # not appreciate us pulling the file out from under them and we
        # can't exactly make WB wait for the editor to close
        try:
            unpack_dir = self.unpackToTemp([rel_path])
            unpack_dir.join(rel_path).start()
        except OSError:
            pass

    def _make_wizard_file_dir(self, wizard_file_name, progress):
        with progress:
            # Extract the wizard, and any images as well
            files_to_extract = [wizard_file_name]
            image_exts = ('bmp', 'jpg', 'jpeg', 'png', 'gif', 'pcx', 'pnm',
                'tif', 'tiff', 'tga', 'iff', 'xpm', 'ico', 'cur', 'ani')
            files_to_extract.extend(x for (x, _s, _c) in self.fileSizeCrcs if
                                    x.lower().endswith(image_exts))
            unpack_dir = self.unpackToTemp(files_to_extract, progress,
                                           recurse=True)
        # Cleaned up by the wizard GUI clients
        return unpack_dir

    def sync_from_data(self, delta_files: set[CIstr], progress):
        # Extract to a temp project, then perform the sync as if it were a
        # regular project and finally repack
        unpack_dir = self.unpackToTemp([x[0] for x in self.fileSizeCrcs],
            recurse=True, progress=SubProgress(progress, 0.1, 0.4))
        upt_numb, del_numb = self._do_sync_data(
            unpack_dir, delta_files, progress=SubProgress(progress, 0.4, 0.5))
        self.packToArchive(unpack_dir, self.writable_archive_name(),
                           isSolid=True, blockSize=None,
                           progress=SubProgress(progress, 0.5, 1.0))
        cleanup_temp_dir(unpack_dir)
        return upt_numb, del_numb

    def writable_archive_name(self):
        """Returns a version of the name of this archive with the file
        extension changed to be writable (i.e. zip or 7z), if it isn't
        already."""
        if self.fn_key.fn_ext in archives.writeExts:
            return self.fn_key
        return FName(self.fn_key.fn_body + archives.defaultExt)

#------------------------------------------------------------------------------
class InstallerProject(_InstallerPackage):
    """Represents a directory/build installer entry."""
    type_string = _('Project')
    is_project = True

    @staticmethod
    def _new_name(base_name, count):
        return f'{base_name} ({count})'

    # AFile API - InstallerProject is a folder not a file, special handling
    def do_update(self, raise_on_error=False, force_update=False, **kwargs):
        # refresh projects once on boot, even if skipRefresh is on
        force_update |= not self.project_refreshed
        if not force_update and (self.skipRefresh or not bass.settings[
                'bash.installers.autoRefreshProjects']):
            return False
        return super().do_update(raise_on_error=True, # don't call on deleted!
                                 force_update=force_update, **kwargs)

    def _fs_copy(self, dest_path, **kwargs):
        # does not preserve mtimes so next do_update will return True?
        shutil.copytree(self.abs_path.s, dest_path.s, ##: are .s needed?
                        copy_function=copy_or_reflink2)

    def _file_changed(self, stat_tuple):
        """Check if the total size and/or max mod time changed, then check
        the cached mod times/sizes of all files."""
        size_apath_date, proj_size, max_mtime = stat_tuple
        cached = self.src_sizeCrcDate
        return self.ftime != max_mtime or self.fsize != proj_size or \
            cached.keys() != size_apath_date.keys() or any( # keep := below!
                (sap := size_apath_date[k])[0] != s or sap[2] != d for
                k, (s, _c, d) in cached.items())

    @property
    def _null_stat(self): return bolt.LowerDict(), -1, 0.0

    def _stat_tuple(self):
        """Return the total project size, the max modification time of the
        files/folders and a dict that maps relative (to the project root) paths
        to size/apath/mtime. The latter should suffice to detect changes but
        max_time and total size are easier to check."""
        size_apath_date, folders_times = _scandir_walk(self.abs_path)
        try:
            max_node_mtime = max(
                chain(folders_times, (v[2] for v in size_apath_date.values())))
        except ValueError: # int(max([]))
            max_node_mtime = 0.0
        return size_apath_date, sum(
            v[0] for v in size_apath_date.values()), max_node_mtime

    def _fs_refresh(self, progress, stat_tuple,
                    recalculate_project_crc=False, **kwargs):
        """Refresh src_sizeCrcDate, fileSizeCrcs, fsize, ftime,
        crc from project directory, set project_refreshed to True."""
        #--Scan for changed files
        # populate the project's src_sizeCrcDate with _all_ files present in
        # the project dir. src_sizeCrcDate is then used to populate
        # fileSizeCrcs, used to populate ci_dest_sizeCrc in
        # refreshDataSizeCrc. Compare to InstallersData._refresh_from_data_dir.
        rootName = self.abs_path.stail
        progress = progress if progress else bolt.Progress()
        progress_msg = f'{rootName}\n%s\n' % _('Scanning…')
        progress(0, progress_msg)
        progress.setFull(1)
        size_apath_date, proj_size, max_node_mtime = stat_tuple
        if recalculate_project_crc:
            to_calc = size_apath_date
        else:
            oldGet = self.src_sizeCrcDate.get
            to_calc = bolt.LowerDict()
            for k, ls in size_apath_date.items():
                cached_val = oldGet(k)
                if not cached_val or (
                        cached_val[0] != ls[0] or cached_val[2] != ls[2]):
                    to_calc[k] = ls
                else:
                    size_apath_date[k] = cached_val
        #--Update crcs?
        Installer.calc_crcs(to_calc, rootName, size_apath_date, progress)
        self.src_sizeCrcDate = size_apath_date
        #--Done
        self.ftime = max_node_mtime
        self.fileSizeCrcs = [(path, src_size, crc) for path, (src_size, crc,
            _date) in self.src_sizeCrcDate.items()]
        self.fsize = proj_size
        self.crc = sum(tup[2] for tup in self.fileSizeCrcs) & 0xFFFFFFFF
        self.project_refreshed = True

    # Installer API -----------------------------------------------------------
    def _install(self, dest_src, progress):
        progress.setFull(len(dest_src))
        progress(0, f'{self}\n' + _('Moving files…'))
        progressPlus = progress.plus
        #--Copy Files
        srcDirJoin = self.abs_path.join
        return self._fs_install(dest_src, srcDirJoin, progress, progressPlus,
                                None)

    def sync_from_data(self, delta_files: set[CIstr], progress):
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
        walkPath(apath, 0)

    def _open_txt_file(self, rel_path): self.abs_path.join(rel_path).start()

    def _make_wizard_file_dir(self, wizard_file_name, progress):
        return self.abs_path # Wizard file already exists here

#------------------------------------------------------------------------------
class InstallersData(DataStore):
    """Installers tank data. This is the data source for the InstallersList."""
    # track changes in installed mod inis etc _in the game Data/ dir_ and
    # deletions of mods/INI Tweaks. Keys are absolute paths (so we can track
    # ini deletions from Data/INI Tweaks as well as mods/xmls etc in Data/)
    _miscTrackedFiles = {}
    # we only scan Data dir on first refresh - therefore we need be informed
    # for updates/deletions that happen outside our control - mods/inis/bsas
    _externally_deleted: set[Path] = set()
    _externally_updated: set[Path] = set()
    # cache with paths in Data/ that would be skipped but are not, due to
    # an installer having the override skip etc flag on - when turning the skip
    # off leave the files here - will be cleaned on restart (files will show
    # as dirty till then, but to remove them we should examine all installers
    # that override skips - not worth the hassle)
    overridden_skips: set[CIstr] = set() # populate with CIstr !
    __clean_overridden_after_load = True
    installers_dir_skips = set()
    file_pattern = re.compile(
        fr'\.(?:{"|".join(e[1:] for e in archives.readExts)})$', re.I)
    unique_store_key = Store.INSTALLERS
    _dir_key = 'installers'

    def __init__(self):
        self.set_store_dir()
        super().__init__()
        self.bash_dir.makedirs()
        #--Persistent data
        self.dictFile = bolt.PickleDict(self.bash_dir.join(u'Installers.dat'))
        self.data_sizeCrcDate = bolt.LowerDict()
        from . import converters
        self.converters_data = converters.ConvertersData(bass.dirs['bainData'],
            bass.dirs[u'converters'], bass.dirs[u'dupeBCFs'],
            bass.dirs[u'corruptBCFs'], bass.dirs[u'installers'])
        #--Volatile
        self.ci_underrides_sizeCrc = bolt.LowerDict() # underridden files
        self.hasChanged = False
        self.loaded = False
        self.lastKey = FName(u'==Last==')
        self._inst_types = [InstallerArchive, InstallerProject,
                            InstallerMarker]

    @property
    def bash_dir(self): return bass.dirs[u'bainData']

    @property
    def hidden_dir(self): return bass.dirs[u'modsBash'].join(u'Hidden')

    def new_info(self, fileName, progress=None, *, is_proj=True, is_mark=False,
            install_order=None, do_refresh=True, _index=None, load_cache=True):
        """Create, add to self and return a new _InstallerPackage.
        :param fileName: the filename of the package to create
        :param is_proj: create a project if True otherwise an archive
        :param is_mark: used to add a marker, progress arguments are ignored
        :param progress: to pass to _InstallerPackage._reset_cache
        :param install_order: if given move the package to this position
        :param do_refresh: if False client should refresh Norm and status
        :param _index: if given create a subprogress
        :param load_cache: if True load call _reset_cache in __init__
        """
        if not is_mark:
            progress = progress if _index is None else SubProgress(
                progress, _index, _index + 1)
            info = self[fileName] = self._inst_types[is_proj](
                fileName, progress=progress, load_cache=load_cache)
        else:
            info = self[fileName] = self._inst_types[2](fileName)
            if install_order is None:
                install_order = self[self.lastKey].order
        if install_order is not None:
            self.moveArchives([fileName], install_order)
        if progress and not is_mark: progress(1.0, _('Done'))
        if do_refresh and not is_mark:
            self.refresh_ns()
        return info

    @classmethod
    def rightFileType(cls, fileName: bolt.FName | str):
        ##: What about projects? Do we have to just return True here?
        return cls.file_pattern.search(fileName)

    def refresh(self, *args, **kwargs): ##: we should not be using this, track
        return self.irefresh(*args, **kwargs)

    def irefresh(self, progress=None, what=u'DIONSC', fullRefresh=False,
            # installers refresh context parameters
            refresh_info: RefrData | None = None, *,
            added_archives: _fnames = ()) -> RefrData:
        """Refresh context parameters are used for updating installers. Note
        that if any of those are not None "changed" will be always True,
        triggering the rest of the refreshes in irefresh."""
        #--Archive invalidation
        from . import modInfos, oblivionIni, bsaInfos
        if (bass.settings['bash.bsaRedirection'] and
                oblivionIni.abs_path.exists()):
            ##: What about all the other stuff the "BSA Redirection" link does?
            bsaInfos.set_bsa_redirection(do_redirect=True)
        #--Load Installers.dat if not loaded - will set changed to True
        changes = (fresh_load := not self.loaded) and self.__load(progress)
        #--Last marker
        if self.lastKey not in self:
            self[self.lastKey] = InstallerMarker(self.lastKey)
        if fullRefresh: # BAIN uses modInfos crc cache
            sub = SubProgress(progress, 0.0, 0.05) if progress else progress
            modInfos.refresh_crcs(progress=sub)
        #--Refresh Other - FIXME(ut): docs
        if u'D' in what:
            changes |= self._refresh_from_data_dir(progress, fullRefresh)
        if 'I' in what:
            progress = progress or bolt.Progress()
            # if we are passed a refresh_info, update_installers was
            # already called, and we only need to update for deleted
            if refresh_info is None:
                if added_archives: # if added we are passed existing installers
                    refresh_info = RefrData(to_add=set(added_archives))
                    # call update_installers to update those
                    dirs_files = set(added_archives), ()
                else: # we really need to scan installers
                    dirs_files = top_level_items(bass.dirs['installers'])
                if dirs_files:
                    progress(0, _('Scanning Packages…'))
                    refresh_info = self.update_installers(*dirs_files,
                        fullRefresh, progress, refresh_info=refresh_info,
                    fresh_load=fresh_load) # avoid re-stating freshly unpickled
            for del_item in refresh_info.to_del:
                self.pop(del_item)
            changes |= bool(refresh_info)
        if refresh_info is None: refresh_info = RefrData()
        if 'O' in what or changes:
            reordered = self.refreshOrder()
            refresh_info.redraw.update(reordered)
            changes |= bool(reordered)
        if 'N' in what or changes:
            #--dict mapping all should-be-installed files to their attributes
            norm_sizeCrc = bolt.LowerDict()
            for package in (x for x in self.sorted_values() if x.is_active):
                norm_sizeCrc.update(package.ci_dest_sizeCrc)
            # Populate self.ci_underrides_sizeCrc with all underridden files -
            # files installed in data dir, but from a lower loading installer
            # (or manually)
            ci_underrides_sizeCrc = bolt.LowerDict()
            for path, sizeCrc in norm_sizeCrc.items():
                try:
                    if sizeCrc != (data_sc := self.data_sizeCrcDate[path][:2]):
                        ci_underrides_sizeCrc[path] = data_sc
                except KeyError: pass # file is not installed in data dir
            changes |= self.ci_underrides_sizeCrc != ci_underrides_sizeCrc
            self.ci_underrides_sizeCrc = ci_underrides_sizeCrc
        if 'S' in what or changes:
            st_changed = {k for k, v in self.items() if v.refreshStatus(self)}
            refresh_info.redraw.update(st_changed)
            changes |= bool(st_changed)
        if 'C' in what or changes:
            self.converters_data.refreshConverters(progress, fullRefresh)
        #--Done
        if changes: self.hasChanged = True # todo use refresh_info here?
        return refresh_info

    def refresh_ns(self, *args, **kwargs):
        self.irefresh(*args, **kwargs, what='NS')

    def refresh_n(self, *args, **kwargs):
        self.irefresh(*args, **kwargs, what='N')

    def __load(self, progress):
        progress = progress or bolt.Progress()
        progress(0, _('Loading Data…'))
        # that's what happens when you pickle non builtins :shrug:
        for clz in self._inst_types:
            setattr(sys.modules['bash.bosh'], clz.__name__, clz)
            getattr(sys.modules['bash.bosh'], # needed for reduce!
                    clz.__name__).__module__ = 'bash.bosh'
        self.dictFile.load()
        pickl_data = self.dictFile.pickled_data
        pickl_data.pop('crc_installer', None) # remove unused dict
        self.converters_data.load()
        self._data = pickl_data.get(u'installers', {})
        if not isinstance(self._data, bolt.FNDict):
            self._data = forward_compat_path_to_fn(self._data)
        pickle = pickl_data.get(u'sizeCrcDate', {})
        self.data_sizeCrcDate = bolt.LowerDict(pickle) if not isinstance(
            pickle, bolt.LowerDict) else pickle
        # fixup: all markers had their fn_key attribute set to '===='
        for fn_inst, inst in list(self.items()):
            if inst.is_marker:
                inst.fn_key = fn_inst
            elif not inst.fn_key: # __setstate blew, probably installer deleted
                del self[fn_inst]
        self.loaded = True
        return True

    def save_pickle(self):
        """Saves to pickle file."""
        if self.hasChanged:
            self.dictFile.pickled_data[u'installers'] = self._data
            self.dictFile.pickled_data[u'sizeCrcDate'] = self.data_sizeCrcDate
            self.dictFile.vdata[u'version'] = 2
            self.dictFile.save()
            self.converters_data.save()
            self.hasChanged = False

    def rename_operation(self, member_info, name_new, store_refr=None):
        """Rename installer and update store_refr if owned files need be
        redrawn. name_new must be tested (via unique name) otherwise we will
        overwrite!"""
        if member_info.is_marker:
            del self[old := member_info.fn_key]
            new = member_info.fn_key = FName(name_new) ##: make sure newName is fn
            self[new] = member_info
            return {old: new}, {}
        ren_keys, ren_paths = super().rename_operation(member_info, name_new)
        # Update the ownership information for relevant data stores
        old_key = next(iter(ren_keys))
        for store in data_tracking_stores():
            if not store.tracks_ownership: continue
            owned = [v for v in store.values() if str( # str due to Paths
                v.get_table_prop('installer')) == old_key]
            if owned:
                store_refr[store] = True
            for v in owned:
                v.set_table_prop('installer', '%s' % name_new)
        return ren_keys, ren_paths

    #--Dict Functions ---------------------------------------------------------
    def _delete_operation(self, infos, *, recycle=True):
        toDelete = []
        markers = [inst.fn_key for inst in infos if
                   inst.is_marker or toDelete.append(inst)] # or None
        super()._delete_operation(toDelete, recycle=recycle)
        for m in markers: del self[m]

    def delete_refresh(self, infos, check_existence):
        del_insts = [inst for inst in infos if not inst.is_marker]
        markers = len(del_insts) < len(infos)
        if check_existence:
            del_insts = {i for i in del_insts if not i.abs_path.exists()}
        if del_insts: # markers are popped in _delete_operation
            self.irefresh(what='I', refresh_info=RefrData({
                i.fn_key for i in del_insts}))
        elif markers:
            self.refreshOrder()

    def filter_essential(self, fn_items: Iterable[FName]):
        # The ==Last== marker must always be present
        return {i: self[i] for i in fn_items if i != self.lastKey}

    def filter_unopenable(self, fn_items: Iterable[FName]):
        # Can't open markers since they're virtual
        return {i: self[i] for i in fn_items if not self[i].is_marker}

    def add_info(self, file_info, destName, **kwargs):
        clone = self.new_info(destName,
            is_proj=file_info.is_project, install_order=file_info.order + 1,
            do_refresh=False, # we only need to call refresh_n()
            load_cache=False) # don't load from disc - copy all attributes over
        atts = (*Installer.persistent, *Installer.volatile) # drop fn_key
        for att in atts:
            setattr(clone, att, copy.copy(getattr(file_info, att)))
        clone.is_active = False # make sure we mark as inactive
        self.refresh_n() # no need to change installer status here

    def move_infos(self, sources, destinations, window, bash_frame):
        moved = super().move_infos(sources, destinations, window, bash_frame)
        self.irefresh(what='I', added_archives=moved)
        return moved

    def reorder_packages(self, partial_order: list[FName]) -> str:
        """Changes the BAIN package order to match the specified partial order
        as much as possible. Heavily based on lo_reorder. Does not refresh, you
        will have to do that afterwards.

        :return: An error message to be shown to the user, or an empty string
            if nothing noteworthy happened."""
        present_packages = set(self)
        partial_packages = set(partial_order)
        # Packages in the partial order that are missing from the Bash
        # Installers folder
        excess_packages = partial_packages - present_packages
        filtered_order = [p for p in partial_order if p not in excess_packages]
        remaining_packages = present_packages - set(filtered_order)
        current_order = self.sorted_keys()
        collected_packages = []
        left_off = 0
        while remaining_packages:
            for i, curr_package in enumerate(current_order[left_off:]):
                # Look for continuous segments that are missing from the
                # filtered partial package order
                if curr_package in remaining_packages:
                    collected_packages.append(curr_package)
                    remaining_packages.remove(curr_package)
                elif collected_packages:
                    # We've hit a package that's common between current and
                    # filtered orders after a continuous segment, look up the
                    # shared package and insert the packages in the same order
                    # they have in the current order into the filtered order
                    index_in_filtered = filtered_order.index(curr_package)
                    for coll_package in reversed(collected_packages):
                        filtered_order.insert(index_in_filtered, coll_package)
                    left_off += i + 1
                    collected_packages = []
                    break # Restart the for loop
            else:
                # Exited the loop without breaking -> some extra plugins should
                # be appended at the end
                filtered_order.extend(collected_packages)
        for i, p in enumerate(filtered_order):
            self[p].order = i
        message = ''
        if excess_packages:
            message += _('Some packages could not be found and were '
                         'skipped:') + '\n* '
            message += '\n* '.join(excess_packages)
        return message

    # Getters
    def sorted_pairs(self, package_keys: Iterable[FName] | None = None,
            reverse=False) -> Iterable[tuple[FName, Installer]]:
        """Return pairs of key, installer for package_keys in self, sorted by
        install order."""
        pairs = self if package_keys is None else {k: self[k] for k in
                                                   package_keys}
        return dict_sort(pairs, key_f=lambda k: pairs[k].order,
                         reverse=reverse)

    def sorted_keys(self, package_keys: Iterable[FName] | None = None,
            reverse=False) -> list[FName]:
        """Return FName keys for package_keys in self, sorted by install
        order."""
        p_keys = package_keys or self
        return sorted(p_keys, key=lambda k: self[k].order, reverse=reverse)

    def sorted_values(self, package_keys: Iterable[FName] | None = None,
            reverse=False) -> list[Installer]:
        """Return installers for package_keys in self, sorted by install
        order."""
        if package_keys is None: values = self.values()
        else: values = [self[k] for k in package_keys]
        return sorted(values, key=attrgetter('order'), reverse=reverse)

    #--Refresh Functions ------------------------------------------------------
    def applyEmbeddedBCFs(self, installers=None, destArchives=None,
                          progress=bolt.Progress()):
        if installers is None:
            installers = [x for x in self.values() if
                          x.is_archive and x.hasBCF]
        if not installers: return [], []
        if not destArchives:
            destArchives = [FName(f'[Auto-applied BCF] {x}') for x
                            in installers]
        progress.setFull(len(installers))
        dest_archives = []
        for i, (destArchive, installer) in enumerate(zip(destArchives,
                list(installers))): # we may modify installers below
            progress(i, installer.fn_key)
            #--Extract the embedded BCF and move it to the Converters folder
            unpack_dir = installer.unpackToTemp([installer.hasBCF],
                SubProgress(progress, i, i + 0.5))
            srcBcfFile = unpack_dir.join(installer.hasBCF)
            bcfFile = bass.dirs['converters'].join(f'temp-{srcBcfFile.stail}')
            srcBcfFile.moveTo(bcfFile)
            cleanup_temp_dir(unpack_dir)
            #--Create the converter, apply it
            converter = InstallerConverter.from_path(bcfFile)
            try:
                msg = f'{destArchive}: ' + _(
                    u'An error occurred while applying an Embedded BCF.')
                self.apply_converter(converter, destArchive,
                                     SubProgress(progress, i + 0.5, i + 1.0),
                                     msg, installer, dest_archives,
                                     crc_installer={installer.crc: installer})
            except StateError:
                # maybe short circuit further attempts to extract
                # installer.hasBCF = False
                installers.remove(installer)
            finally: bcfFile.remove()
        self.irefresh(what='I', added_archives=dest_archives)
        return dest_archives, [x.fn_key for x in installers]

    def apply_converter(self, converter, destArchive, progress, msg,
                        installer=None, dest_archives=None, show_warning=None,
                        position=-1, crc_installer=None):
        try:
            converter.apply(destArchive, crc_installer, progress,
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
            if dest_archives is not None: # caller must call irefresh on those!
                dest_archives.append(destArchive)
            else:
                self.irefresh(what='I', added_archives=[destArchive])
                return iArchive
        except StateError as e:
            deprint(msg, traceback=True)
            if show_warning:
                show_warning(f'{msg}\n\n{e.message}')
            raise # UI expects that

    def update_installers(self, folders, files, fullRefresh, progress, *,
            refresh_info: RefrData | None = None, fresh_load=False,
            __skip_prefixes=('bash', '--')) -> RefrData:
        """Update installer info on given folders and files, adding new and
        updating modified projects/packages, skipping as necessary."""
        installers = set()
        if scanning := (refresh_info is None):
            # we are called with a listing of installers dir - filter packages
            files = [f for f in files if f.fn_ext in readExts
                     and not f.lower().startswith(__skip_prefixes)]
            folders = {f for f in folders if
                # skip Bash directories and user specified ones
                (low := f.lower()) not in self.installers_dir_skips and
                not low.startswith(__skip_prefixes)}
            refresh_info = RefrData()
            if not (files or folders):
                return refresh_info
        progress.setFull(len(files) + len(folders))
        index = 0
        for items, is_proj in ((files, False), (folders, True)):
            for item in items:
                progress(index, _('Scanning Packages…') + f'\n{item}')
                index += 1
                inst = self.get(item)
                if inst is None or inst.fn_key != item:
                    if inst: # some rename bug - corrupted
                        refresh_info.redraw.add(item)
                        deprint(f'{item} invalid idata key: {inst.fn_key}')
                        del self[item]  # delete the stored installer
                    else: refresh_info.to_add.add(item)
                    # refresh_info will notify callers to call irefresh('N')
                    self.new_info(item, progress, is_proj=is_proj,
                                  _index=index - 1, do_refresh=False)
                    continue
                # if we just loaded __setstate just updated existing Installers
                if not fresh_load and inst.do_update(force_update=fullRefresh,
                        progress=SubProgress(progress, index - 1, index),
                        recalculate_project_crc=fullRefresh):
                    refresh_info.redraw.add(item)
                else: installers.add(item)
        if scanning:
            exist = installers | refresh_info.to_add | refresh_info.redraw
            refresh_info.to_del = set(self.ipackages(self)) - exist
        return refresh_info

    def refreshOrder(self):
        """Refresh installer status."""
        inOrder, ordering = [], []
        # not specifying the key below results in double time
        for iname, installer in dict_sort(self):
            if installer.order >= 0:
                inOrder.append((iname, installer))
            else:
                ordering.append((iname, installer))
        inOrder.sort(key=lambda x: x[1].order)
        for dex, (key, value) in enumerate(inOrder):
            if self.lastKey == key:
                inOrder[dex:dex] = ordering
                break
        else:
            inOrder.extend(ordering)
        change = set()
        for order, (iname, installer) in enumerate(inOrder):
            if installer.order != order:
                installer.order = order
                change.add(iname)
        return change

    def _refresh_from_data_dir(self, progress, recalculate_all_crcs):
        """Update self.data_sizeCrcDate, using current data_sizeCrcDate as a
        cache.

        Recalculates crcs for all plugins in Data/ directory and all other
        files whose cached date or size has changed. Will skip directories
        (but not files) specified in Installer global skips and remove empty
        dirs if the setting is on."""
        progress = progress if progress else bolt.Progress()
        mods_dir = bass.dirs['mods']
        # Scan top level files and folders in the Data dir - for plugins use
        # modInfos cache, for other files (bsas etc.) use data_sizeCrcDate
        progress_msg = f'{(dirname := mods_dir.stail)}: ' + '%s\n' % _(
            'Pre-Scanning…')
        progress.setFull(1)
        progress(0, progress_msg)
        data_dirs = {} # collect those and filter them after
        oldGet = self.data_sizeCrcDate.get
        siz_apath_mtime = bolt.LowerDict()
        new_sizeCrcDate = bolt.LowerDict()
        from . import modInfos # to get the crcs for plugins
        # these should be already updated (fullRefresh explicitly calls
        # modInfos.refresh and so does RefreshData when tabbing in)
        plugins_scd = bolt.LowerDict()
        non_ghosts = set()
        for dirent in os.scandir(mods_dir):
            rpFile = dirent.name
            if dirent.is_dir():
                data_dirs[rpFile] = dirent.path
            else:
                if (low := rpFile[rpFile.rfind('.'):].lower()) == '.ghost':
                    rpFile = rpFile[:-6]
                    if rpFile.lower() in non_ghosts: # limbo ghosts skip them
                        continue
                    low = rpFile[rpFile.rfind('.'):].lower()
                if low in Installer.skipExts: continue
                try:
                    modInfo = modInfos[rpFile] # modInfos MUST BE UPDATED
                    non_ghosts.add(rpFile.lower())
                    plugins_scd[rpFile] = (modInfo.fsize,
                        modInfo.cached_mod_crc(), modInfo.ftime)
                    continue
                except KeyError:
                    pass # not a mod or corrupted (we still need the crc)
                oSize, oCrc, oDate = oldGet(rpFile) or (0, 0, 0.0)
                lstat_size, date = (st := dirent.stat()).st_size, st.st_mtime
                if lstat_size != oSize or date != oDate:
                    siz_apath_mtime[rpFile] = (lstat_size,  dirent.path, date)
                else:
                    new_sizeCrcDate[rpFile] = (oSize, oCrc, oDate)
        dirs_paths = InstallersData._skips_in_data_dir(data_dirs)
        root_len = len(mods_dir) + 1 # compute relative paths to the Data dir
        progress_msg = f'{dirname}: ' + '%s\n' % _('Scanning…')
        progress.setFull(1 + len(dirs_paths))
        #--Remove empty dirs?
        remove_empty = bass.settings['bash.installers.removeEmptyDirs']
        for dex, (top_dir, dir_path) in enumerate(dict_sort(dirs_paths)):
            progress(dex, f'{progress_msg}{top_dir}')
            has_files = _walk_data_dirs(dir_path, siz_apath_mtime,
                new_sizeCrcDate, root_len, oldGet, remove_empty)
            if remove_empty and not has_files:
                GPath_no_norm(dir_path).removedirs(raise_error=False)
        #--Force update?
        # don't add this logic to _walk_data_dirs it would slow usual case down
        if recalculate_all_crcs:
            siz_apath_mtime.update(
                (k, (v[0], os.path.join(mods_dir, k), v[2])) for k, v in
                new_sizeCrcDate.items())
            new_sizeCrcDate = plugins_scd # already calculated in fullRefresh +ghosts
        else:
            new_sizeCrcDate.update(plugins_scd)
        change = bool(siz_apath_mtime) or (
                    len(new_sizeCrcDate) != len(self.data_sizeCrcDate))
        #--Update crcs?
        Installer.calc_crcs(siz_apath_mtime, dirname, new_sizeCrcDate,
                            progress)
        self.data_sizeCrcDate = new_sizeCrcDate
        self.update_for_overridden_skips(progress=progress) #after final_update
        #--Done
        return change

    def reset_refresh_flag_on_projects(self):
        for installer in self.values():
            if installer.is_project:
                installer.project_refreshed = False

    @staticmethod
    def _skips_in_data_dir(sDirs: dict):
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
            newSDirs = (x for x in newSDirs if x.lower()
                        not in Installer.screenshot_dirs)
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
        return {x: sDirs[x] for x in newSDirs}

    def update_data_SizeCrcDate(self, dest_paths: set[str], progress=None):
        """Update data_SizeCrcDate with info on given paths - paths are given
        by refreshDataCrcDate, so they should not end in ghost.
        :param progress: must be zeroed - message is used in _process_data_dir
        :param dest_paths: set of paths relative to Data/ - may not exist."""
        _pjoin = os.path.join
        inst_dir = bass.dirs['mods'].s # should be normalized
        root_files = []
        for data_dest in dest_paths:
            sp = data_dest.rsplit(os_sep, 1) # split into ['rel_path, 'file']
            root_files.append((inst_dir if len(sp) == 1  # top level file
                               else _pjoin(inst_dir, sp[0]), sp[-1]))
        root_files.sort(key=itemgetter(0)) # must sort on same key as groupby
        root_dirs_files = [(key, [j for i, j in val]) for key, val in
                           groupby(root_files, key=itemgetter(0))]
        progress = progress or bolt.Progress()
        from . import modInfos  # to get the crcs for plugins
        progress.setFull(1 + len(root_dirs_files))
        siz_apath_mtime = bolt.LowerDict()
        new_sizeCrcDate = bolt.LowerDict()
        oldGet = self.data_sizeCrcDate.get
        relPos = len(inst_dir) + 1
        norm_ghost_get = Installer.getGhosted().get
        for index, (asDir, sFiles) in enumerate(root_dirs_files):
            progress(index)
            top_level = len(asDir) <= relPos  # < should be enough
            for sFile in sFiles:
                if top_level:
                    rpFile = sFile
                    try:
                        modInfo = modInfos[rpFile] # modInfos MUST BE UPDATED
                        new_sizeCrcDate[rpFile] = (modInfo.fsize,
                            modInfo.cached_mod_crc(), modInfo.ftime)
                        continue
                    except KeyError:
                        pass # not a mod/corrupted/missing, let os.lstat decide
                    asFile = _pjoin(asDir, norm_ghost_get(sFile, sFile))
                else:
                    asFile = _pjoin(asDir, sFile)
                    rpFile = asFile[relPos:]
                try:
                    lstat = os.lstat(asFile)
                except FileNotFoundError:
                    continue  # file does not exist
                oSize, oCrc, oDate = oldGet(rpFile) or (0, 0, 0.0)
                lstat_size, date = lstat.st_size, lstat.st_mtime
                if lstat_size != oSize or date != oDate:
                    siz_apath_mtime[rpFile] = (lstat_size, asFile, date)
                else:
                    new_sizeCrcDate[rpFile] = (oSize, oCrc, oDate)
        deleted_or_pending = set(dest_paths) - set(new_sizeCrcDate)
        for d in deleted_or_pending: self.data_sizeCrcDate.pop(d, None)
        Installer.calc_crcs(siz_apath_mtime, bass.dirs['mods'].stail,
            new_sizeCrcDate, progress)
        self.data_sizeCrcDate.update(new_sizeCrcDate)

    def update_for_overridden_skips(self, dont_skip=None, progress=None):
        if dont_skip is not None:
            dont_skip.difference_update(self.data_sizeCrcDate)
            self.overridden_skips |= dont_skip
        elif self.__clean_overridden_after_load: # needed on first load
            self.overridden_skips.difference_update(self.data_sizeCrcDate)
            self.__clean_overridden_after_load = False
        new_skips_overrides = (self.overridden_skips -
                               self.data_sizeCrcDate.keys())
        progress = progress or bolt.Progress()
        progress(0, _('%(data_folder)s: Skips overrides…') % {
            'data_folder': bush.game.mods_dir} + '\n')
        self.update_data_SizeCrcDate(new_skips_overrides, progress)

    @staticmethod
    def track(abspath):
        InstallersData._miscTrackedFiles[abspath] = AFile(abspath)

    @classmethod
    def notify_external(cls, altered: set[Path] = frozenset(),
                        del_set: set[Path] = frozenset(),
                        renamed: dict[Path, Path] = None):
        """Notifies BAIN of changes in the Data folder done by something other
        than BAIN.

        :param altered: A set of file paths that have changed.
        :param del_set: A set of file paths that have been deleted.
        :param renamed: A dict of file paths that were renamed. Maps old file
            paths to new ones. Currently, only updates tracked changed/deleted
            paths."""
        if renamed is None: renamed = {}
        cls._externally_updated.update(altered)
        cls._externally_deleted.update(del_set)
        for ext_tracker in (cls._externally_updated, cls._externally_deleted):
            if renamed_keys := (renamed.keys() & ext_tracker):
                ext_tracker.difference_update(renamed_keys) # remove old paths
                ext_tracker.update(
                    v for k, v in renamed.items() if k in renamed_keys)

    def refreshTracked(self):
        del_paths = set(InstallersData._externally_deleted)
        altered = dict.fromkeys(InstallersData._externally_updated)
        InstallersData._externally_updated.clear()
        InstallersData._externally_deleted.clear()
        for apath, tracked in list(InstallersData._miscTrackedFiles.items()):
            try:
                if tracked.do_update(raise_on_error=True):
                    altered[apath] = tracked.fsize, tracked.ftime
                    # if we uninstalled then reinstalled without leaving Bash
                    del_paths.discard(apath)
            except OSError: # untrack - runs on first run !!
                InstallersData._miscTrackedFiles.pop(apath, None)
                del_paths.add(apath)
        do_refresh = False
        def _path_key():
            # the Data dir - will give correct relative path for both
            # Ini tweaks and mods - those are keyed in data by rel path...
            relpath = apath.relpath(bass.dirs['mods'])
            # ghosts...
            return relpath.root.s if relpath.cs[-6:] == '.ghost' else relpath.s
        for apath in del_paths:
            do_refresh |= bool(self.data_sizeCrcDate.pop(_path_key(), None))
        for apath, siz_tim in altered.items():
            s, m = siz_tim or apath.size_mtime()
            self.data_sizeCrcDate[_path_key()] = (s, apath.crc, m)
            do_refresh = True
        return do_refresh #Some tracked files changed, update installers status

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
        self.hasChanged = True

    #--Install
    def _createTweaks(self, destFiles, installer, tweaksCreated):
        """Generate INI Tweaks when a CRC mismatch is detected while
        installing a mod INI (not ini tweak) in the Data/ directory.

        If the current CRC of the ini is different than the one BAIN is
        installing, a tweak file will be generated. Call me *before*
        installing the new inis then call _editTweaks() to populate the tweaks.
        """
        dest_files = (x for x in destFiles
                if x[-4:].lower() in supported_ini_exts
                # don't create ini tweaks for overridden ini tweaks...
                and os.path.split(x)[0].lower() != u'ini tweaks')
        for relPath in dest_files:
            try:
                oldCrc = self.data_sizeCrcDate[relPath][1]
                newCrc = installer.ci_dest_sizeCrc[relPath][1]
            except KeyError:
                continue
            if newCrc == oldCrc: continue
            iniAbsDataPath = bass.dirs[u'mods'].join(relPath)
            # Create a copy of the old one
            co_path = f'{iniAbsDataPath.sbody}, ~Old Settings ' \
                      f'[{installer.fn_key}]{iniAbsDataPath.cext}'
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
            # Pass in both INIs - they must have the same format, and at least
            # one of them is almost certainly not empty
            bif = best_ini_files([iniAbsDataPath, tweakPath])
            data_ini, tweak_ini = bif[iniAbsDataPath], bif[tweakPath]
            currSection = None
            lines = []
            for (line_text, section, setting, value, status, lineNo,
                 _deleted) in data_ini.analyse_tweak(tweak_ini):
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
            with tweakPath.open('w', encoding='utf-8') as ini_:
                msg = _('INI Tweak created by Wrye Bash %(wb_version)s, using '
                        'settings from old file.')
                ini_.write(f'; {msg}\n\n' % {'wb_version': bass.AppVersion})
                ini_.writelines(lines)
            # We notify BAIN below, although highly improbable the created ini
            # is included to a package
            iniInfos.new_info(tweakPath.stail, notify_bain=True)
        tweaksCreated -= removed

    def _installer_install(self, installer, destFiles, index, progress):
        """Wrap installer.install to update data_sizeCrcDate."""
        sub_progress = SubProgress(progress, index, index + 1)
        data_sizeCrcDate_update, refresh_ui_ = installer.install(
            destFiles, sub_progress)
        # update mtime for the rest of the files
        for dest, (s, c, d) in data_sizeCrcDate_update.items():
            self.data_sizeCrcDate[dest] = (
                s, c, bass.dirs['mods'].join(dest).mtime if d == -1 else d)
        return refresh_ui_

    def bain_install(self, packages, refresh_ui, progress=None, last=False,
                     override=True):
        """Install selected packages. If override is False install only
        missing files. Otherwise, all (unmasked) files."""
        try:
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
            for inst in self.sorted_values(reverse=True):
                if inst in to_install:
                    progress(index, inst.fn_key)
                    destFiles = inst.ci_dest_sizeCrc.keys() - mask
                    if not override:
                        destFiles &= inst.missingFiles
                    if destFiles:
                        self._createTweaks(destFiles, inst, tweaksCreated)
                        refresh_ui.update(self._installer_install(
                            inst, destFiles, index, progress))
                    index += 1 # increment after it's used in _installer_install
                    inst.is_active = True
                    if inst.order == min_order:
                        break  # we are done
                #prevent lower packages from installing any files of this installer
                if inst.is_active: mask |= set(inst.ci_dest_sizeCrc)
            if tweaksCreated:
                self._editTweaks(tweaksCreated)
                refresh_ui |= Store.INIS.IF(tweaksCreated)
            return tweaksCreated
        finally:
            self.refresh_ns()

    #--Uninstall, Anneal, Clean
    @staticmethod
    def _determineEmptyDirs(emptyDirs: set[Path], removedFiles):
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
                files = {folder.join(x) for x in folder.ilist()}
                remaining = files - allRemoves
                if not remaining: # If all items in this directory will be
                    # removed, this directory is also safe to remove.
                    removedFiles -= files
                    removedFilesAdd(folder)
                    allRemovesAdd(folder)
                    emptyDirsAdd(folder.head)
            emptyDirs -= exclude
        return removedFiles

    def _removeFiles(self, ci_removes, refresh_ui, progress=None):
        """Performs the actual deletion of files and updating of internal data,
           used by 'bain_uninstall' and 'bain_anneal'."""
        if not ci_removes: return
        mods_dir_join = bass.dirs[u'mods'].join
        empty_dir_candidates = set()
        removed_tracked = [(s, set()) for s in data_tracking_stores()]
        removed_untracked = set()
        remove_paths = {}
        #--Construct list of files to delete
        for ci_rel_path in ci_removes:
            for store, removed_files in removed_tracked:
                if store_info := store.data_path_to_info(ci_rel_path):
                    removed_files.add(store_info.fn_key)
                    path = store_info.abs_path # it exists as the info exists
                    break
            else:
                path = mods_dir_join(ci_rel_path)
                if path.exists():
                    removed_untracked.add(path)
                    empty_dir_candidates.add(path.head)
            remove_paths[ci_rel_path] = path
        #--Now determine which directories will be empty, replacing subsets of
        # removedFiles by their parent dir if the latter will be emptied
        removed_untracked = self._determineEmptyDirs(
            empty_dir_candidates, removed_untracked)
        ex = None # if an exception is raised we must again check removes
        try:
            # Delete files that no data store cares about
            if removed_untracked:
                parent = progress.getParent() if progress else None
                env.shellDelete(removed_untracked, parent=parent)
            # Delegate deletion of files that data stores care about to those
            # data stores
            for store, removed_files in removed_tracked:
                refresh_ui[store.unique_store_key] = bool(removed_files)
                store.delete(removed_files, recycle=False)
        except (CancelError, SkipError): ex = sys.exc_info()
        except:
            ex = sys.exc_info()
            raise
        finally:
            removed = (v for v in remove_paths.values() if not v.exists()) \
                if ex else remove_paths.values()
            # store.delete might have updated _externally_deleted so reset it
            InstallersData._externally_deleted.update(removed)
            self.refreshTracked()

    def __restore(self, installer, removes, restores, cede_ownership):
        """Populate restores dict with files to be restored by this
        installer, removing those from removes. Used by 'bain_uninstall' and
        'bain_anneal'. In case a mod or ini belongs to another package,
        we must make sure we cede ownership, even if the mod or ini is not
        restored (restore takes care of that). Return *all* the files this
        installer would install."""
        # get all destination files for this installer
        dest_sc = installer.ci_dest_sizeCrc
        # keep those to be removed while not restored by a higher order package
        to_keep = (removes & dest_sc.keys()) - restores.keys()
        for ci_dest in to_keep:
            # We don't want to remove it right now, only if no higher package
            # has it either -> that's checked later
            removes.discard(ci_dest)
            try:
                version_in_data = self.data_sizeCrcDate[ci_dest]
            except KeyError:
                # The file isn't present in the Data folder at all -> missing
                # file, restore it from this package
                restores[ci_dest] = installer.fn_key
            else:
                if installer.ci_dest_sizeCrc[ci_dest] != version_in_data[:2]:
                    # This package has a different version than the one in the
                    # Data folder, restore that one
                    restores[ci_dest] = installer.fn_key
                else: # don't mind the FName(str()) below - done seldom
                    # This package has the same version as the one in the Data
                    # folder, so simply take ownership of the existing file
                    cede_ownership[installer.fn_key].add(FName(str(ci_dest)))
        return set(dest_sc)

    def bain_uninstall_all(self, refresh_ui, progress=None):
        """Uninstall all present packages."""
        self._do_uninstall(frozenset(self.values()), refresh_ui, progress)

    def bain_uninstall(self, unArchives, refresh_ui, progress=None):
        """Uninstall selected packages."""
        self._do_uninstall(frozenset(self[x] for x in unArchives), refresh_ui,
            progress)

    def _do_uninstall(self, unArchives, refresh_ui, progress):
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
        _cede_ownership = defaultdict(set)
        for installer in self.sorted_values(reverse=True):
            #--Uninstall archive?
            if installer in unArchives:
                for data_sizeCrc in (installer.ci_dest_sizeCrc,installer.dirty_sizeCrc):
                    for ci_file, sizeCrc in data_sizeCrc.items():
                        try:
                            if ci_file not in masked and self.data_sizeCrcDate[
                                    ci_file][:2] == sizeCrc:
                                removes.add(ci_file)
                        except KeyError:
                            pass
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
            # Set the 'installer' column for files that track their owner
            stores = data_tracking_stores()
            for ikey, owned_files in cede_ownership.items():
                for owned_path in owned_files:
                    for store in stores:
                        if store_info := store.data_path_to_info(owned_path):
                            if store.tracks_ownership:
                                store_info.set_table_prop(
                                    'installer', f'{ikey}')
                            refresh_ui[store.unique_store_key] = True ## todo refreshdata
                            # Each file may only belong to one data store
                            break
        finally:
            self.refresh_ns()

    def _restoreFiles(self, restores, refresh_ui, progress):
        installer_destinations = {}
        restores = dict_sort(restores, by_value=True)
        for key, group in groupby(restores, key=itemgetter(1)):
            installer_destinations[key] = {dest for dest, _key in group}
        if not installer_destinations: return
        progress.setFull(len(installer_destinations))
        installer_destinations = dict_sort(installer_destinations,
                                           key_f=lambda k: self[k].order)
        for index, (fn_inst, destFiles) in enumerate(installer_destinations):
            progress(index, fn_inst)
            if destFiles:
                refresh_ui.update(self._installer_install(
                    self[fn_inst], destFiles, index, progress))

    def bain_anneal(self, anPackages, refresh_ui, progress=None):
        """Anneal selected packages. If no packages are selected, anneal all.
        Anneal will:
        * Correct underrides in anPackages.
        * Install missing files from active anPackages."""
        progress = progress if progress else bolt.Progress()
        anPackages = (self[package] for package in
                      (anPackages or self.filterInstallables(self)))
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
        _cede_ownership = defaultdict(set)
        for installer in self.sorted_values(reverse=True):
            #--Other active package. May provide a restore file.
            #  And/or may block later uninstalls.
            if installer.is_active:
                self.__restore(installer, removes, restores, _cede_ownership)
        self._remove_restore(removes, restores, refresh_ui, _cede_ownership,
                             progress)

    def get_clean_data_dir_list(self):
        ci_keep_files = set(chain.from_iterable(
            installer.ci_dest_sizeCrc for installer in # relative to Data/
            self.sorted_values(reverse=True) if installer.is_active))
        # Collect all files that we definitely want to keep
        bain = bush.game.Bain
        ci_keep_files.update(map(CIstr, chain(bush.game.vanilla_files,
            bush.game.bethDataFiles, bain.keep_data_files,
            bain.wrye_bash_data_files)))
        from . import modInfos
        for bpatch in modInfos.bashed_patches: # type: FName
            ci_keep_files.add(CIstr(bpatch))
            bp_doc = modInfos[bpatch].get_table_prop('doc')
            if bp_doc: # path is absolute, convert to relative to the Data/ dir
                try:
                    bp_doc = bp_doc.relpath(bass.dirs[u'mods'])
                except ValueError:
                    # https://github.com/python/cpython/issues/51444
                    # bp_doc on a different drive, will be skipped anyway
                    continue
                # Keep both versions of the BP doc (.txt and .html)
                ci_keep_files.add(CIstr(u'%s' % bp_doc))
                ci_keep_files.add(CIstr(bp_doc.root.s + (
                    u'.txt' if bp_doc.cext == u'.html' else u'.html')))
        ci_removes = self.data_sizeCrcDate.keys() - ci_keep_files
        # Don't remove files in Wrye Bash-related directories or INI Tweaks
        skip_start = (*bain.keep_data_file_prefixes, *(f'{skipDir}{os_sep}' for
            skipDir in bain.wrye_bash_data_dirs | bain.keep_data_dirs))
        return [f for f in ci_removes if not f.lower().startswith(skip_start)]

    def clean_data_dir(self, ci_removes, refresh_ui):
        destDir = bass.dirs['bainData'].join(
            f'{bush.game.mods_dir} Folder Contents ({bolt.timestamp()})')
        try:
            emptyDirs = set()
            stores = data_tracking_stores()
            store_del = defaultdict(set)
            for ci_rel_path in ci_removes:
                for store in stores:
                    if store_inf := store.data_path_to_info(str(ci_rel_path)):
                        full_path = store_inf.abs_path
                        break
                else:
                    store = None
                    full_path = bass.dirs['mods'].join(ci_rel_path)
                try:
                    full_path.moveTo(destDir.join(ci_rel_path)) # will drop .ghost
                    if store is not None:
                        store_del[store].add(store_inf.fn_key)
                    self.data_sizeCrcDate.pop(ci_rel_path, None)
                    emptyDirs.add(full_path.head)
                except (StateError, OSError):
                    #It's not imperative that files get moved, so ignore errors
                    deprint(f'Clean Data: moving {full_path} to {destDir} '
                            f'failed', traceback=True)
            for store, del_keys in store_del.items():
                store.delete_refresh(del_keys, check_existence=False)
                refresh_ui |= store.unique_store_key.DO()
            for emptyDir in emptyDirs:
                if emptyDir.is_dir() and not [*emptyDir.ilist()]:
                    emptyDir.removedirs()
        finally:
            self.refresh_ns()

    #--Utils
    @staticmethod
    def _filter_installer_bsas(inst, active_bsas):
        return [k for k in active_bsas if k.fn_key in inst.ci_dest_sizeCrc]

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
        :param bsa_cause: The dict of reasons BSAs were loaded. Retrieve
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
                        _process_bsa_conflicts(bsa_info, package)
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
                conflict_type.append((installer, package, curConflicts))
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
                self._parse_error(b, src_installer.fn_key)
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
        if include_bsas: # get the load order of all active BSAs
            active_bsas, bsa_cause = modInfos.get_bsa_lo()
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
        log.setHeader(_('BAIN Packages:'))
        #--List
        log(u'[spoiler]\n', False)
        for inst in self.sorted_values():
            inst.log_package(log, showInactive)
        log(u'[/spoiler]')
        return log.out.getvalue()

    def filterInstallables(self, installerKeys: Iterable[FName]):
        """Return a sublist of installerKeys that can be installed -
        installerKeys must be in data or a KeyError is raised.

        :return: A list of installable packages/projects"""
        return [k for k in self.ipackages(installerKeys) if
                self[k].has_recognized_structure]

    def ipackages(self, installerKeys: Iterable[FName]) -> Iterable[FName]:
        """Remove markers from installerKeys."""
        return (x for x in installerKeys if not self[x].is_marker)

    def createFromData(self, projectPath, ci_files: list[CIstr], progress,
                       mod_infos):
        if not ci_files: return
        subprogress = SubProgress(progress, 0, 0.8, full=len(ci_files))
        srcJoin = bass.dirs[u'mods'].join
        dstJoin = self.store_dir.join(projectPath).join
        for i, ci_rel_path in enumerate(ci_files):
            subprogress(i, ci_rel_path)
            try:
                srcJoin(ci_rel_path).copyTo(dstJoin(ci_rel_path))
            except FileNotFoundError: # modInfos MUST BE UPDATED
                if minf := mod_infos.get(str(ci_rel_path)): # try the ghost
                    minf.copy_to(dstJoin(ci_rel_path))
                else: raise
        # Refresh, so we can manipulate the InstallerProject item
        self.new_info(projectPath, progress,
                      install_order=len(self)) # install last
