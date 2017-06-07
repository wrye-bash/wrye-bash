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
"""BAIN backbone classes."""

import collections
import copy
import errno
import os
import re
import sys
import time
from binascii import crc32
from functools import partial, wraps
from itertools import groupby, imap
from operator import itemgetter, attrgetter

from . import imageExts, DataStore, BestIniFile, InstallerConverter, AFile
from .. import balt # YAK!
from .. import bush, bass, bolt, env, load_order, archives
from ..archives import readExts, defaultExt, list_archive, compress7z, \
    countFilesInArchive, extractCommand, extract7z, compressionSettings
from ..bolt import Path, deprint, formatInteger, round_size, GPath, \
    AbstractError, sio, ArgumentError, SubProgress, StateError

os_sep = unicode(os.path.sep)

class Installer(object):
    """Object representing an installer archive, its user configuration, and
    its installation state."""

    type_string = _(u'Unrecognized')
    #--Member data
    persistent = ('archive', 'order', 'group', 'modified', 'size', 'crc',
        'fileSizeCrcs', 'type', 'isActive', 'subNames', 'subActives',
        'dirty_sizeCrc', 'comments', 'extras_dict', 'packageDoc', 'packagePic',
        'src_sizeCrcDate', 'hasExtraData', 'skipVoices', 'espmNots', 'isSolid',
        'blockSize', 'overrideSkips', 'remaps', 'skipRefresh', 'fileRootIdex')
    volatile = ('data_sizeCrc', 'skipExtFiles', 'skipDirFiles', 'status',
        'missingFiles', 'mismatchedFiles', 'project_refreshed',
        'mismatchedEspms', 'unSize', 'espms', 'underrides', 'hasWizard',
        'espmMap', 'hasReadme', 'hasBCF', 'hasBethFiles', '_dir_dirs_files')
    __slots__ = persistent + volatile
    #--Package analysis/porting.
    docDirs = {u'screenshots'}
    #--Will be skipped even if hasExtraData == True (bonus: skipped also on
    # scanning the game Data directory)
    dataDirsMinus = {u'bash', u'--'}
    try:
        reDataFile = re.compile(ur'(\.(esp|esm|' + bush.game.bsa_extension +
                                ur'|ini))$', re.I | re.U)
    except AttributeError: # YAK
        reDataFile = re.compile(ur'(\.(esp|esm|bsa|ini))$', re.I | re.U)
    docExts = {u'.txt', u'.rtf', u'.htm', u'.html', u'.doc', u'.docx', u'.odt',
               u'.mht', u'.pdf', u'.css', u'.xls', u'.xlsx', u'.ods', u'.odp',
               u'.ppt', u'.pptx'}
    reReadMe = re.compile(
        ur'^.*?([^\\]*)(read[ _]?me|lisez[ _]?moi)([^\\]*)'
        ur'(' +ur'|'.join(docExts) + ur')$', re.I | re.U)
    skipExts = {u'.exe', u'.py', u'.pyc', u'.7z', u'.zip', u'.rar', u'.db',
                u'.ace', u'.tgz', u'.tar', u'.gz', u'.bz2', u'.omod',
                u'.fomod', u'.tb2', u'.lzma', u'.manifest'}
    skipExts.update(set(readExts))
    scriptExts = {u'.txt', u'.ini', u'.cfg'}
    commonlyEditedExts = scriptExts | {u'.xml'}
    #--Regular game directories - needs update after bush.game has been set
    dataDirsPlus = docDirs | {u'bash patches', u'ini tweaks', u'docs'}
    @staticmethod
    def init_bain_dirs():
        """Initialize BAIN data directories on a per game basis."""
        Installer.dataDirsPlus |= bush.game.dataDirs | bush.game.dataDirsPlus
        InstallersData.installers_dir_skips.update(
            {bass.dirs['converters'].stail.lower(), u'bash'})
        user_skipped = bass.inisettings['SkippedBashInstallersDirs'].split(u'|')
        InstallersData.installers_dir_skips.update(
            skipped.lower() for skipped in user_skipped if skipped)

    tempList = Path.baseTempDir().join(u'WryeBash_InstallerTempList.txt')

    #--Class Methods ----------------------------------------------------------
    @staticmethod
    def getGhosted():
        """Returns map of real to ghosted files in mods directory."""
        dataDir = bass.dirs['mods']
        ghosts = [x for x in dataDir.list() if x.cs[-6:] == u'.ghost']
        return dict((x.root,x) for x in ghosts if not dataDir.join(x).root.exists())

    @staticmethod
    def final_update(new_sizeCrcDate, old_sizeCrcDate, pending, pending_size,
                     progress, recalculate_all_crcs, rootName):
        """Clear old_sizeCrcDate and update it with new_sizeCrcDate after
        calculating crcs for pending."""
        #--Force update?
        if recalculate_all_crcs:
            pending.update(new_sizeCrcDate)
            pending_size += sum(x[0] for x in new_sizeCrcDate.itervalues())
        changed = bool(pending) or (len(new_sizeCrcDate) != len(old_sizeCrcDate))
        #--Update crcs?
        Installer.calc_crcs(pending, pending_size, rootName,
                            new_sizeCrcDate, progress)
        # drop _asFile
        old_sizeCrcDate.clear()
        for rpFile, (size, crc, date, _asFile) in new_sizeCrcDate.iteritems():
            old_sizeCrcDate[rpFile] = (size, crc, date)
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
        for rpFile, (size, _crc, date, asFile) in iter(sorted(pending.items())):
            progress(done, progress_msg + rpFile.s)
            sub = bolt.SubProgress(progress, done, done + size + 1)
            sub.setFull(size + 1)
            crc = 0L
            try:
                with open(asFile, 'rb') as ins:
                    insTell = ins.tell
                    for block in iter(partial(ins.read, 2097152), ''):
                        crc = crc32(block, crc) # 2MB at a time, probably ok
                        sub(insTell())
            except IOError:
                deprint(_(u'Failed to calculate crc for %s - please report '
                          u'this, and the following traceback:') % asFile,
                        traceback=True)
                continue
            crc &= 0xFFFFFFFF
            done += size + 1
            new_sizeCrcDate[rpFile] = (size, crc, date, asFile)

    #--Initialization, etc ----------------------------------------------------
    def initDefault(self):
        """Initialize everything to default values."""
        self.archive = u''
        #--Persistent: set by _refreshSource called by refreshBasic
        self.modified = 0 #--Modified date
        self.size = -1 #--size of archive file
        self.crc = 0 #--crc of archive
        self.isSolid = False #--package only - solid 7z archive
        self.blockSize = None #--package only - set here and there
        self.fileSizeCrcs = [] #--list of tuples for _all_ files in installer
        #--For InstallerProject's, cache if refresh projects is skipped
        self.src_sizeCrcDate = {}
        #--Set by refreshBasic
        self.fileRootIdex = 0 # unused - just used in setstate
        self.type = 0 #--Package type: 0: unset/invalid; 1: simple; 2: complex
        self.subNames = []
        self.subActives = []
        self.extras_dict = {} # hack to add more persistent attributes
        #--Set by refreshDataSizeCrc
        self.dirty_sizeCrc = {}
        self.packageDoc = self.packagePic = None
        #--User Only
        self.skipVoices = False
        self.hasExtraData = False
        self.overrideSkips = False
        self.skipRefresh = False    # Projects only
        self.comments = u''
        self.group = u'' #--Default from abstract. Else set by user.
        self.order = -1 #--Set by user/interface.
        self.isActive = False
        self.espmNots = set() #--Lowercase esp/m file names that user has decided not to install.
        self.remaps = {}
        #--Volatiles (not pickled values)
        #--Volatiles: directory specific
        self.project_refreshed = False
        self._dir_dirs_files = None
        #--Volatile: set by refreshDataSizeCrc
        self.hasWizard = False
        self.hasBCF = False
        self.espmMap = collections.defaultdict(list)
        self.hasReadme = False
        self.hasBethFiles = False
        self.data_sizeCrc = {}
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
        return formatInteger(number)

    def size_string(self, marker_string=u''):
        return round_size(self.size)

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
        del self.remaps[oldName]
        path = GPath(currentName)
        if path in self.espmNots:
            self.espmNots.discard(path)
            self.espmNots.add(GPath(oldName))

    def resetAllEspmNames(self):
        for espm in self.remaps.keys():
            # Need to use .keys(), since 'resetEspmName' will use
            # del self.remaps[oldName], changing the dictionary size.
            self.resetEspmName(self.remaps[espm])

    def getEspmName(self,currentName):
        for old in self.remaps:
            if self.remaps[old] == currentName:
                return old
        return currentName

    def setEspmName(self,currentName,newName):
        oldName = self.getEspmName(currentName)
        self.remaps[oldName] = newName
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

    def __getstate__(self):
        """Used by pickler to save object state."""
        getter = object.__getattribute__
        return tuple(getter(self,x) for x in self.persistent)

    def __setstate__(self,values):
        """Used by unpickler to recreate object."""
        self.initDefault() # runs on __init__ called by __reduce__
        map(self.__setattr__,self.persistent,values)
        rescan = False
        if not isinstance(self.extras_dict, dict):
            self.extras_dict = {}
            if self.fileRootIdex: # we need to add 'root_path' key
                rescan = True
        elif self.fileRootIdex and not self.extras_dict.get('root_path', u''):
            rescan = True ##: for people that used my wip branch, drop on 307
        package_path = bass.dirs['installers'].join(self.archive)
        exists = package_path.exists()
        if not exists: # the pickled package was deleted outside bash
            pass # don't do anything should be deleted from our data soon
        elif rescan:
            dest_scr = self.refreshBasic(bolt.Progress(),
                                         recalculate_project_crc=False)
        else: dest_scr = self.refreshDataSizeCrc()
        if exists and self.overrideSkips:
            InstallersData.overridden_skips.update(dest_scr.keys())

    def __copy__(self):
        """Create a copy of self -- works for subclasses too (assuming
        subclasses don't add new data members)."""
        clone = self.__class__(GPath(self.archive))
        copier = copy.copy
        getter = object.__getattribute__
        setter = object.__setattr__
        for attr in Installer.__slots__:
            setter(clone,attr,copier(getter(self,attr)))
        return clone

    #--refreshDataSizeCrc, err, framework -------------------------------------
    # Those files/folders will be always skipped by refreshDataSizeCrc()
    _silentSkipsStart = (
        u'--', u'omod conversion data%s' % os_sep, u'fomod%s' % os_sep,
        u'wizard images%s' % os_sep)
    _silentSkipsEnd = (
        u'%sthumbs.db' % os_sep, u'%sdesktop.ini' % os_sep, u'config')

    # global skips that can be overridden en masse by the installer
    _global_skips = []
    _global_start_skips = []
    _global_skip_extensions = set()
    # executables - global but if not skipped need additional processing
    _executables_ext = {u'.dll', u'.dlx'} | {u'.asi'} | {u'.jar'}
    _executables_process = {}
    _goodDlls = _badDlls = None
    @staticmethod
    def goodDlls():
        if Installer._goodDlls is None:
            Installer._goodDlls = collections.defaultdict(list)
            Installer._goodDlls.update(
                bass.settings['bash.installers.goodDlls'])
        return Installer._goodDlls
    @staticmethod
    def badDlls():
        if Installer._badDlls is None:
            Installer._badDlls = collections.defaultdict(list)
            Installer._badDlls.update(bass.settings['bash.installers.badDlls'])
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
        if bass.settings['bash.installers.skipTESVBsl']:
            Installer._global_skip_extensions.add('.bsl')
        # skips files starting with...
        if bass.settings['bash.installers.skipDistantLOD']:
            Installer._global_start_skips.append(u'distantlod')
        if bass.settings['bash.installers.skipLandscapeLODMeshes']:
            meshes_lod = os_sep.join((u'meshes', u'landscape', u'lod'))
            Installer._global_start_skips.append(meshes_lod)
        if bass.settings['bash.installers.skipScreenshots']:
            Installer._global_start_skips.append(u'screenshots')
        # LOD textures
        skipLODTextures = bass.settings[
            'bash.installers.skipLandscapeLODTextures']
        skipLODNormals = bass.settings[
            'bash.installers.skipLandscapeLODNormals']
        skipAllTextures = skipLODTextures and skipLODNormals
        tex_gen = os_sep.join((u'textures', u'landscapelod', u'generated'))
        if skipAllTextures:
            Installer._global_start_skips.append(tex_gen)
        elif skipLODTextures: Installer._global_skips.append(
            lambda f: f.startswith(tex_gen) and not f.endswith(u'_fn.dds'))
        elif skipLODNormals: Installer._global_skips.append(
            lambda f: f.startswith(tex_gen) and f.endswith(u'_fn.dds'))
        # Skipped extensions
        skipObse = not bass.settings['bash.installers.allowOBSEPlugins']
        if skipObse:
            Installer._global_start_skips.append(
                bush.game.se.shortName.lower() + os_sep)
            Installer._global_skip_extensions |= Installer._executables_ext
        if bass.settings['bash.installers.skipImages']:
            Installer._global_skip_extensions |= imageExts
        Installer._init_executables_skips()

    @staticmethod
    def init_attributes_process():
        """Populate _attributes_process with functions which decide if the
        file is to be skipped while at the same time update self hasReadme,
        hasWizard, hasBCF attributes."""
        reReadMeMatch = Installer.reReadMe.match
        docs_ = u'Docs' + os_sep
        def _process_docs(self, fileLower, full, fileExt, file_relative, sub):
            maReadMe = reReadMeMatch(fileLower)
            if maReadMe: self.hasReadme = full
            # let's hope there is no trailing separator - Linux: test fileLower, full are os agnostic
            rsplit = fileLower.rsplit(os_sep, 1)
            parentDir, fname = (u'', rsplit[0]) if len(rsplit) == 1 else rsplit
            if not self.overrideSkips and bass.settings[
                'bash.installers.skipDocs'] and not (
                        fname in bush.game.dontSkip) and not (
                        fileExt in bush.game.dontSkipDirs.get(parentDir, [])):
                return None # skip
            dest = file_relative
            if not parentDir:
                archiveRoot = GPath(self.archive).sroot if isinstance(self,
                        InstallerArchive) else self.archive
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
            if len(rootLower) > 1: return file_relative ##: maybe skip ??
            file_relative = self.remaps.get(file_relative, file_relative)
            if file_relative not in self.espmMap[sub]: self.espmMap[
                sub].append(file_relative)
            pFile = GPath(file_relative)
            self.espms.add(pFile)
            if pFile in self.espmNots: return None # skip
            return file_relative
        Installer._attributes_process[u'.esm'] = \
        Installer._attributes_process[u'.esp'] = _remap_espms
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
        skipEspmVoices = not self.skipVoices and set(
            x.cs for x in self.espmNots)
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
        def __skipExecutable(checkOBSE, fileLower, full, archiveRoot, size,
                             crc, desc, ext, exeDir, dialogTitle):
            if not fileLower.startswith(exeDir): return True
            if fileLower in badDlls and [archiveRoot, size, crc] in badDlls[
                fileLower]: return True
            if not checkOBSE or fileLower in goodDlls and [
                archiveRoot, size, crc] in goodDlls[fileLower]: return False
            message = Installer._dllMsg(fileLower, full, archiveRoot,
                                        desc, ext, badDlls, goodDlls)
            if not balt.askYes(balt.Link.Frame,message, dialogTitle):
                badDlls[fileLower].append([archiveRoot,size,crc])
                bass.settings['bash.installers.badDlls'] = Installer._badDlls
                return True
            goodDlls[fileLower].append([archiveRoot,size,crc])
            bass.settings['bash.installers.goodDlls'] = Installer._goodDlls
            return False
        if bush.game.se.shortName:
            _obse = partial(__skipExecutable,
                    desc=_(u'%s plugin DLL') % bush.game.se.shortName,
                    ext=(_(u'a dll')),
                    exeDir=(bush.game.se.shortName.lower() + os_sep),
                    dialogTitle=bush.game.se.shortName + _(u' DLL Warning'))
            Installer._executables_process[u'.dll'] = \
            Installer._executables_process[u'.dlx'] = _obse
        if bush.game.sd.shortName:
            _asi = partial(__skipExecutable,
                   desc=_(u'%s plugin ASI') % bush.game.sd.longName,
                   ext=(_(u'an asi')),
                   exeDir=(bush.game.sd.installDir.lower() + os_sep),
                   dialogTitle=bush.game.sd.longName + _(u' ASI Warning'))
            Installer._executables_process[u'.asi'] = _asi
        if bush.game.sp.shortName:
            _jar = partial(__skipExecutable,
                   desc=_(u'%s patcher JAR') % bush.game.sp.longName,
                   ext=(_(u'a jar')),
                   exeDir=(bush.game.sp.installDir.lower() + os_sep),
                   dialogTitle=bush.game.sp.longName + _(u' JAR Warning'))
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
        """Update self.data_sizeCrc and related variables and return
        dest_src map for install operation. data_sizeCrc is a dict from paths
        to size and crc tuples that maps paths _relative to the Data dir_ - so
        the locations the files will end up to if installed.

        WIP rewrite
        Used:
         - in __setstate__ to construct the installers from Installers.dat,
         used once (and in full refresh ?)
         - in refreshBasic, after refreshing persistent attributes - track
         call graph from here should be the path that needs optimization (
         irefresh, ShowPanel ?)
         - in InstallersPanel.refreshCurrent()
         - in 2 subclasses' install() and InstallerProject.syncToData()
         - in _Installers_Skip._refreshInstallers()
         - in _RefreshingLink (override skips, HasExtraData, skip voices)
         - in Installer_CopyConflicts
        """
        type_    = self.type
        #--Init to empty
        self.hasWizard = self.hasBCF = self.hasReadme = False
        self.packageDoc = self.packagePic = None # = self.extras_dict['readMe']
        for attr in {'skipExtFiles','skipDirFiles','espms'}:
            object.__getattribute__(self,attr).clear()
        dest_src = {}
        #--Bad archive?
        if type_ not in {1,2}: return dest_src
        archiveRoot = GPath(self.archive).sroot if isinstance(self,
                InstallerArchive) else self.archive
        docExts = self.docExts
        docDirs = self.docDirs
        dataDirsPlus = self.dataDirsPlus
        dataDirsMinus = self.dataDirsMinus
        skipExts = self.skipExts
        unSize = 0
        bethFiles = bush.game.bethDataFiles
        skips, global_skip_ext = self._init_skips()
        if self.overrideSkips:
            renameStrings = False
            bethFilesSkip = False
        else:
            renameStrings = bass.settings['bash.installers.renameStrings'] \
                if bush.game.esp.stringsFiles else False
            bethFilesSkip = not bass.settings[
                'bash.installers.autoRefreshBethsoft']
        if renameStrings:
            from . import oblivionIni
            lang = oblivionIni.get_ini_language()
        else: lang = u''
        languageLower = lang.lower()
        hasExtraData = self.hasExtraData
        if type_ == 2: # exclude u'' from active subpackages
            activeSubs = set(
                x for x, y in zip(self.subNames[1:], self.subActives[1:]) if y)
        data_sizeCrc = {}
        skipDirFiles = self.skipDirFiles
        skipDirFilesAdd = skipDirFiles.add
        skipDirFilesDiscard = skipDirFiles.discard
        skipExtFilesAdd = self.skipExtFiles.add
        commonlyEditedExts = Installer.commonlyEditedExts
        espmMap = self.espmMap = collections.defaultdict(list)
        reModExtMatch = bass.reModExt.match
        reReadMeMatch = Installer.reReadMe.match
        #--Scan over fileSizeCrcs
        root_path = self.extras_dict.get('root_path', u'')
        rootIdex = len(root_path)
        for full,size,crc in self.fileSizeCrcs:
            if rootIdex: # exclude all files that are not under root_dir
                if not full.startswith(root_path): continue
            file = full[rootIdex:]
            fileLower = file.lower()
            if fileLower.startswith( # skip top level '--', 'fomod' etc
                    Installer._silentSkipsStart) or fileLower.endswith(
                    Installer._silentSkipsEnd): continue
            sub = u''
            if type_ == 2: #--Complex archive
                split = file.split(os_sep, 1)
                if len(split) > 1:
                    # redefine file, excluding the subpackage directory
                    sub,file = split
                    fileLower = file.lower()
                    if fileLower.startswith(Installer._silentSkipsStart):
                        continue # skip subpackage level '--', 'fomod' etc
                if sub not in activeSubs:
                    if sub == u'':
                        skipDirFilesAdd(file)
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
                        skipDirFilesDiscard(file)
                        continue
                    elif fileExt in defaultExt and (fileLower[-7:-3] == u'-bcf' or u'-bcf-' in fileLower):
                        self.hasBCF = full
                        skipDirFilesDiscard(file)
                        continue
                    elif fileExt in docExts and sub == u'':
                        if not self.hasReadme:
                            if reReadMeMatch(file):
                                self.hasReadme = full
                                skipDirFilesDiscard(file)
                                skip = False
                    elif fileLower in bethFiles:
                        self.hasBethFiles = True
                        skipDirFilesDiscard(file)
                        skipDirFilesAdd(_(u'[Bethesda Content]') + u' ' + file)
                        continue
                    elif not rootLower and reModExtMatch(fileExt):
                        #--Remap espms as defined by the user
                        if file in self.remaps:
                            file = self.remaps[file]
                            # fileLower = file.lower() # not needed will skip
                        if file not in sub_esps: sub_esps.append(file)
                    if skip:
                        continue
            sub_esps = espmMap[sub] # add sub key to the espmMap
            rootLower,fileExt = splitExt(fileLower)
            rootLower = rootLower.split(os_sep, 1)
            if len(rootLower) == 1: rootLower = u''
            else: rootLower = rootLower[0]
            fileStartsWith = fileLower.startswith
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
                    self, fileLower, full, fileExt, file, sub)
                if dest is None: continue
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
                    if sub_esps and sub_esps[-1].lower() == fileLower:
                        del sub_esps[-1] # added in extensions processing
                        self.espms.discard(GPath(file)) #dont show in espm list
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
            if dest is None: dest = file
            if rootLower in docDirs:
                dest = os_sep.join((u'Docs', file[len(rootLower) + 1:]))
            elif (renameStrings and fileStartsWith(u'strings' + os_sep) and
                  fileExt in {u'.strings',u'.dlstrings',u'.ilstrings'}):
                langSep = fileLower.rfind(u'_')
                extSep = fileLower.rfind(u'.')
                lang = fileLower[langSep+1:extSep]
                if lang != languageLower:
                    dest = u''.join((file[:langSep],u'_',lang,file[extSep:]))
                    # Check to ensure not overriding an already provided
                    # language file for that language
                    key = GPath(dest)
                    if key in data_sizeCrc:
                        dest = file
            elif rootLower in dataDirsPlus:
                pass
            elif not rootLower:
                if fileLower == u'package.jpg':
                    dest = self.packagePic = u''.join(
                        (u'Docs' + os_sep, archiveRoot, u'.package.jpg'))
                elif fileExt in imageExts:
                    dest = os_sep.join((u'Docs', file))
            if fileExt in commonlyEditedExts: ##: will track all the txt files in Docs/
                InstallersData.track(bass.dirs['mods'].join(dest))
            #--Save
            key = GPath(dest)
            data_sizeCrc[key] = (size,crc)
            dest_src[key] = full
            unSize += size
        self.unSize = unSize
        (self.data_sizeCrc,old_sizeCrc) = (data_sizeCrc,self.data_sizeCrc)
        #--Update dirty?
        if self.isActive and data_sizeCrc != old_sizeCrc:
            dirty_sizeCrc = self.dirty_sizeCrc
            for file,sizeCrc in old_sizeCrc.iteritems():
                if file not in dirty_sizeCrc and sizeCrc != data_sizeCrc.get(file):
                    dirty_sizeCrc[file] = sizeCrc
        #--Done (return dest_src for install operation)
        return dest_src

    def _find_root_index(self, _os_sep=os_sep, skips_start=_silentSkipsStart):
        # basically just care for skips and complex/simple packages
        #--Sort file names
        split = os.path.split
        sort_keys_dict = dict(
            (x, split(x[0].lower())) for x in self.fileSizeCrcs)
        self.fileSizeCrcs.sort(key=sort_keys_dict.__getitem__)
        #--Find correct starting point to treat as BAIN package
        self.extras_dict.clear() # if more keys are added be careful cleaning
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
                root = layoutSetdefault(dirName,{'dirs':{},'files':False})
                for frag in frags[1:-1]:
                    root = root['dirs'].setdefault(frag,{'dirs':{},'files':False})
                # the last frag is a file, so its parent dir has files
                root['files'] = True
        else:
            if not layout: return
            rootStr = layout.keys()[0]
            if rootStr.lower() in dataDirsPlus: return
            root = layout[rootStr]
            rootStr = u''.join((rootStr, _os_sep))
            while True:
                if root['files']:
                    # There are files in this folder, call it the starting point
                    break
                rootDirs = root['dirs']
                rootDirKeys = rootDirs.keys()
                if len(rootDirKeys) == 1:
                    # Only one subfolder, see if it's either 'Data', or an accepted
                    # Data sub-folder
                    rootDirKey = rootDirKeys[0]
                    rootDirKeyL = rootDirKey.lower()
                    if rootDirKeyL in dataDirsPlus or rootDirKeyL == u'data':
                        # Found suitable starting point
                        break
                    # Keep looking deeper
                    root = rootDirs[rootDirKey]
                    rootStr = u''.join((rootStr, rootDirKey, _os_sep))
                else:
                    # Multiple folders, stop here even if it's no good
                    break
            self.extras_dict['root_path'] = rootStr # keeps case
            self.fileRootIdex = len(rootStr)

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
            return {}
        self._find_root_index()
        # fileRootIdex now points to the start in the file strings to ignore
        #--Type, subNames
        type_ = 0
        subNameSet = set()
        subNameSet.add(u'') # set(u'') == set() (unicode is iterable), so add
        reDataFileSearch = self.reDataFile.search
        dataDirsPlus = self.dataDirsPlus
        root_path = self.extras_dict.get('root_path', u'')
        for full, size, crc in self.fileSizeCrcs:#break if type=1 else churn on
            frags = full.split(_os_sep)
            if root_path: # exclude all files that are not under root_dir
                if frags[0] != root_path[:-1]: continue # chop off os_sep
                frags = frags[1:]
            nfrags = len(frags)
            f0_lower = frags[0].lower()
            #--Type 1 ? break ! data files/dirs are not allowed in type 2 top
            if (nfrags == 1 and reDataFileSearch(f0_lower) or
                nfrags > 1 and f0_lower in dataDirsPlus):
                type_ = 1
                break
            #--Else churn on to see if we have a Type 2 package
            elif not frags[0] in subNameSet and not \
                    f0_lower.startswith(skips_start) and (
                (nfrags > 2 and frags[1].lower() in dataDirsPlus) or
                (nfrags == 2 and reDataFileSearch(frags[1]))):
                subNameSet.add(frags[0])
                type_ = 2
        self.type = type_
        #--SubNames, SubActives
        if type_ == 2:
            self.subNames = sorted(subNameSet,key=unicode.lower)
            actives = set(x for x,y in zip(self.subNames,self.subActives) if (y or x == u''))
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
        data_sizeCrc = self.data_sizeCrc
        data_sizeCrcDate = installersData.data_sizeCrcDate
        abnorm_sizeCrc = installersData.abnorm_sizeCrc
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
            for file,sizeCrc in data_sizeCrc.iteritems():
                sizeCrcDate = data_sizeCrcDate.get(file)
                if not sizeCrcDate:
                    missing.add(file)
                elif sizeCrc != sizeCrcDate[:2]:
                    mismatched.add(file)
                    if not file.shead and bass.reModExt.search(file.s):
                        misEspmed.add(file)
                if sizeCrc == abnorm_sizeCrc.get(file):
                    underrides.add(file)
            if missing: status = -10
            elif misEspmed: status = 10
            elif mismatched: status = 20
            else: status = 30
        #--Clean Dirty
        dirty_sizeCrc = self.dirty_sizeCrc
        for file,sizeCrc in dirty_sizeCrc.items():
            sizeCrcDate = data_sizeCrcDate.get(file)
            if (not sizeCrcDate or sizeCrc != sizeCrcDate[:2] or
                sizeCrc == data_sizeCrc.get(file)
                ):
                del dirty_sizeCrc[file]
        #--Done
        (self.status,oldStatus) = (status,self.status)
        (self.underrides,oldUnderrides) = (underrides,self.underrides)
        return self.status != oldStatus or self.underrides != oldUnderrides

    #--Utility methods --------------------------------------------------------
    def size_or_mtime_changed(self, apath):
        return (self.size, self.modified) != apath.size_mtime()

    def _installer_rename(self, data, newName):
        """Rename package or project."""
        g_path = GPath(self.archive)
        if newName != g_path:
            newPath = bass.dirs['installers'].join(newName)
            if not newPath.exists():
                DataStore._rename_operation(data, g_path, newName)
                #--Add the new archive to Bash and remove old one
                data[newName] = self
                del data[g_path]
                #--Update the iniInfos & modInfos for 'installer'
                from . import modInfos, iniInfos
                mfiles = [x for x in modInfos.table.getColumn('installer') if
                          modInfos.table[x]['installer'] == self.archive]
                ifiles = [x for x in iniInfos.table.getColumn('installer') if
                          iniInfos.table[x]['installer'] == self.archive]
                self.archive = newName.s # don't forget to rename !
                for i in mfiles:
                    modInfos.table[i]['installer'] = self.archive
                for i in ifiles:
                    iniInfos.table[i]['installer'] = self.archive
                return True, bool(mfiles), bool(ifiles)
        return False, False, False

    def open_readme(self): pass
    def open_wizard(self): pass
    def wizard_file(self): raise AbstractError

    def __repr__(self):
        return self.__class__.__name__ + u"<" + repr(self.archive) + u">"

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
        """Install specified files to Oblivion\Data directory."""
        raise AbstractError

    def _move(self, count, progress, stageDataDir):
        # TODO: Find the operation that does not properly close the Oblivion\Data dir.
        # The addition of \\Data and \\* are a kludgy fix for a bug. An operation that is sometimes executed
        # before this locks the Oblivion\Data dir (only for Oblivion, Skyrim is fine)  so it can not be opened
        # with write access. It can be reliably reproduced by deleting the Table.dat file and then trying to
        # install a mod for Oblivion.
        try:
            if count:
                destDir = bass.dirs['mods'].head + u'\\Data'
                stageDataDir += u'\\*'
                env.shellMove(stageDataDir, destDir, progress.getParent())
        finally:
            #--Clean up staging dir
            bass.rmTempDir()

    def listSource(self):
        """Return package structure as text."""
        with sio() as out:
            log = bolt.LogFile(out)
            log.setHeader(u'%s ' % self.archive + _(u'Package Structure:'))
            log(u'[spoiler][xml]\n', False)
            apath = bass.dirs['installers'].join(self.archive)
            self._list_package(apath, log)
            log(u'[/xml][/spoiler]')
            return bolt.winNewLines(log.out.getvalue())

    @staticmethod
    def _list_package(apath, log): raise AbstractError

    def renameInstaller(self, name_new, data):
        """Rename installer and return a three tuple specifying if a refresh in
        mods and ini lists is needed.
        :rtype: tuple
        """
        raise AbstractError

#------------------------------------------------------------------------------
class InstallerMarker(Installer):
    """Represents a marker installer entry."""
    __slots__ = tuple() #--No new slots
    type_string = _(u'Marker')

    def __init__(self,archive):
        Installer.__init__(self,archive)
        self.modified = time.time()

    def __reduce__(self):
        from . import InstallerMarker as boshInstallerMarker
        return boshInstallerMarker, (GPath(self.archive),), tuple(
            imap(self.__getattribute__, self.persistent))

    @property
    def num_of_files(self): return -1

    @staticmethod
    def number_string(number, marker_string=u''): return marker_string

    def size_string(self, marker_string=u''): return marker_string

    def structure_string(self): return _(u'Structure: N/A')

    def _refreshSource(self, progress, recalculate_project_crc):
        """Marker: size is -1, fileSizeCrcs empty, modified = creation time."""
        pass

    def install(self, destFiles, progress=None):
        """Install specified files to Oblivion\Data directory."""
        pass

    def renameInstaller(self, name_new, data):
        archive = GPath(self.archive)
        if name_new == archive:
            return False, False, False
        #--Add the marker to Bash and remove old one
        self.archive = name_new.s
        data[name_new] = self
        del data[archive]
        return True, False, False

    def refreshBasic(self, progress, recalculate_project_crc=True):
        return {}

#------------------------------------------------------------------------------
class InstallerArchiveError(bolt.BoltError): pass

#------------------------------------------------------------------------------
class InstallerArchive(Installer):
    """Represents an archive installer entry."""
    __slots__ = tuple() #--No new slots
    type_string = _(u'Archive')

    def __reduce__(self):
        from . import InstallerArchive as boshInstallerArchive
        return boshInstallerArchive, (GPath(self.archive),), tuple(
            imap(self.__getattribute__, self.persistent))

    #--File Operations --------------------------------------------------------
    def _refreshSource(self, progress, recalculate_project_crc):
        """Refresh fileSizeCrcs, size, modified, crc, isSolid from archive."""
        #--Basic file info
        archive_path = bass.dirs['installers'].join(self.archive)
        self.size, self.modified = archive_path.size_mtime()
        #--Get fileSizeCrcs
        fileSizeCrcs = self.fileSizeCrcs = []
        self.isSolid = False
        class _li(object): # line info - we really want python's 3 'nonlocal'
            filepath = size = crc = isdir = cumCRC = 0
            __slots__ = ()
        def _parse_archive_line(key, value):
            if   key == u'Solid': self.isSolid = (value[0] == u'+')
            elif key == u'Path': _li.filepath = value.decode('utf8')
            elif key == u'Size': _li.size = int(value)
            elif key == u'Attributes': _li.isdir = value and (u'D' in value)
            elif key == u'CRC' and value: _li.crc = int(value,16)
            elif key == u'Method':
                if _li.filepath and not _li.isdir and _li.filepath != \
                        tempArch.s:
                    fileSizeCrcs.append((_li.filepath, _li.size, _li.crc))
                    _li.cumCRC += _li.crc
                _li.filepath = _li.size = _li.crc = _li.isdir = 0
        with archive_path.unicodeSafe() as tempArch:
            try:
                list_archive(tempArch, _parse_archive_line)
                self.crc = _li.cumCRC & 0xFFFFFFFFL
            except:
                archive_msg = u"Unable to read archive '%s'." % archive_path.s
                deprint(archive_msg, traceback=True)
                raise InstallerArchiveError(archive_msg)

    def unpackToTemp(self, fileNames, progress=None, recurse=False):
        """Erases all files from self.tempDir and then extracts specified files
        from archive to self.tempDir. progress will be zeroed so pass a
        SubProgress in.
        fileNames: File names (not paths)."""
        if not fileNames: raise ArgumentError(
            u'No files to extract for %s.' % self.archive)
        # expand wildcards in fileNames to get actual count of files to extract
        #--Dump file list
        with self.tempList.open('w',encoding='utf8') as out:
            out.write(u'\n'.join(fileNames))
        apath = bass.dirs['installers'].join(self.archive)
        #--Ensure temp dir empty
        bass.rmTempDir()
        with apath.unicodeSafe() as arch:
            if progress:
                progress.state = 0
                progress(0, u'%s\n' % self.archive + _(u'Counting files...') + u'\n')
                numFiles = countFilesInArchive(arch, self.tempList, recurse)
                progress.setFull(numFiles)
            #--Extract files
            unpack_dir = bass.getTempDir()
            command = extractCommand(arch, unpack_dir)
            command += u' @%s' % self.tempList.s
            if recurse: command += u' -r'
            try:
                extract7z(command, GPath(self.archive), progress)
            finally:
                self.tempList.remove()
                bolt.clearReadOnly(unpack_dir)
        #--Done -> don't clean out temp dir, it's going to be used soon
        return unpack_dir

    def install(self, destFiles, progress=None):
        """Install specified files to Game\Data directory."""
        destFiles = set(destFiles)
        data_sizeCrc = self.data_sizeCrc
        dest_src = dict((x,y) for x,y in self.refreshDataSizeCrc(True).iteritems() if x in destFiles)
        if not dest_src: return {}
        progress = progress if progress else bolt.Progress()
        #--Extract
        progress(0, self.archive + u'\n' + _(u'Extracting files...'))
        unpackDir = self.unpackToTemp(dest_src.values(),
                                      SubProgress(progress, 0, 0.9))
        #--Rearrange files
        progress(0.9, self.archive + u'\n' + _(u'Organizing files...'))
        unpackDirJoin = unpackDir.join
        stageDir = bass.newTempDir()  #--forgets the old temp dir, creates a new one
        subprogress = SubProgress(progress,0.9,1.0)
        subprogress.setFull(len(dest_src))
        subprogressPlus = subprogress.plus
        stageDataDir = stageDir.join(u'Data')
        stageDataDirJoin = stageDataDir.join
        norm_ghost = Installer.getGhosted() # some.espm -> some.espm.ghost
        norm_ghostGet = norm_ghost.get
        data_sizeCrcDate_update = {}
        timestamps = load_order.install_last()
        for dest, src in dest_src.iteritems():
            size,crc = data_sizeCrc[dest]
            srcFull = unpackDirJoin(src)
            stageFull = stageDataDirJoin(norm_ghostGet(dest,dest))
            if srcFull.exists():
                if bass.reModExt.search(srcFull.s): timestamps(srcFull)
                data_sizeCrcDate_update[dest] = (size,crc,srcFull.mtime)
                # Move to staging directory
                srcFull.moveTo(stageFull)
                subprogressPlus()
        #--Clean up unpacked dir
        unpackDir.rmtree(safety=unpackDir.stail)
        #--Now Move
        self._move(len(data_sizeCrcDate_update), progress, stageDataDir)
        #--Update Installers data
        return data_sizeCrcDate_update

    def unpackToProject(self, project, progress=None):
        """Unpacks archive to build directory."""
        progress = progress or bolt.Progress()
        files = bolt.sortFiles([x[0] for x in self.fileSizeCrcs])
        if not files: return 0
        #--Clear Project
        destDir = bass.dirs['installers'].join(project)
        if destDir.exists(): destDir.rmtree(safety=u'Installers')
        #--Extract
        progress(0,project.s+u'\n'+_(u'Extracting files...'))
        unpack_dir = self.unpackToTemp(files, SubProgress(progress, 0, 0.9))
        #--Move
        progress(0.9,project.s+u'\n'+_(u'Moving files...'))
        count = 0
        bolt.clearReadOnly(unpack_dir)
        tempDirJoin = unpack_dir.join
        destDirJoin = destDir.join
        for file_ in files:
            srcFull = tempDirJoin(file_)
            destFull = destDirJoin(file_)
            if srcFull.exists():
                srcFull.moveTo(destFull)
                count += 1
        bass.rmTempDir()
        return count

    @staticmethod
    def _list_package(apath, log):
        with apath.unicodeSafe() as tempArch:
            filepath = [u'']
            text = []
            def _parse_archive_line(key, value):
                if key == u'Path':
                    filepath[0] = value.decode('utf8')
                elif key == u'Attributes':
                    text.append( # attributes may be empty
                        (u'%s' % filepath[0], value and (u'D' in value)))
                elif key == u'Method':
                    filepath[0] = u''
            list_archive(tempArch, _parse_archive_line)
        text.sort()
        #--Output
        for node, isdir in text:
            log(u'  ' * node.count(os.sep) + os.path.split(node)[1] + (
                os.sep if isdir else u''))

    def renameInstaller(self, name_new, data):
        return self._installer_rename(data,
                                      name_new.root + GPath(self.archive).ext)

    def open_readme(self):
        with balt.BusyCursor():
            # This is going to leave junk temp files behind...
            unpack_dir = self.unpackToTemp([self.hasReadme])
        unpack_dir.join(self.hasReadme).start()

    def open_wizard(self):
        with balt.BusyCursor():
            # This is going to leave junk temp files behind...
            try:
                unpack_dir = self.unpackToTemp([self.hasWizard])
                unpack_dir.join(self.hasWizard).start()
            except:
                # Don't clean up temp dir here.  Sometimes the editor
                # That starts to open the wizard.txt file is slower than
                # Bash, and the file will be deleted before it opens.
                # Just allow Bash's atexit function to clean it when quitting.
                pass

    def wizard_file(self):
        with balt.Progress(_(u'Extracting wizard files...'), u'\n' + u' ' * 60,
                           abort=True) as progress:
            # Extract the wizard, and any images as well
            unpack_dir = self.unpackToTemp([self.hasWizard,
                u'*.bmp',            # BMP's
                u'*.jpg', u'*.jpeg', # JPEG's
                u'*.png',            # PNG's
                u'*.gif',            # GIF's
                u'*.pcx',            # PCX's
                u'*.pnm',            # PNM's
                u'*.tif', u'*.tiff', # TIFF's
                u'*.tga',            # TGA's
                u'*.iff',            # IFF's
                u'*.xpm',            # XPM's
                u'*.ico',            # ICO's
                u'*.cur',            # CUR's
                u'*.ani',            # ANI's
                ], bolt.SubProgress(progress,0,0.9), recurse=True)
        return unpack_dir.join(self.hasWizard)

#------------------------------------------------------------------------------
class InstallerProject(Installer):
    """Represents a directory/build installer entry."""
    __slots__ = tuple() #--No new slots
    type_string = _(u'Project')

    def __reduce__(self):
        from . import InstallerProject as boshInstallerProject
        return boshInstallerProject, (GPath(self.archive),), tuple(
            imap(self.__getattribute__, self.persistent))

    def _refresh_from_project_dir(self, progress=None,
                                  recalculate_all_crcs=False):
        """Update src_sizeCrcDate cache from project directory. Used by
        _refreshSource() to populate the project's src_sizeCrcDate with
        _all_ files present in the project dir. src_sizeCrcDate is then used
        to populate fileSizeCrcs, used to populate data_sizeCrc in
        refreshDataSizeCrc. Compare to InstallersData._refresh_from_data_dir.
        :return: max modification time for files/folders in project directory
        :rtype: int"""
        #--Scan for changed files
        apRoot = bass.dirs['installers'].join(self.archive)
        rootName = apRoot.stail
        progress = progress if progress else bolt.Progress()
        progress_msg = rootName + u'\n' + _(u'Scanning...')
        progress(0, progress_msg + u'\n')
        progress.setFull(1)
        asRoot = apRoot.s
        relPos = len(asRoot) + 1
        max_mtime = apRoot.mtime
        pending, pending_size = {}, 0
        new_sizeCrcDate = {}
        oldGet = self.src_sizeCrcDate.get
        walk = self._dir_dirs_files if self._dir_dirs_files is not None else os.walk(asRoot)
        for asDir, __sDirs, sFiles in walk:
            progress(0.05, progress_msg + (u'\n%s' % asDir[relPos:]))
            get_mtime = os.path.getmtime(asDir)
            max_mtime = max_mtime if max_mtime >= get_mtime else get_mtime
            rsDir = asDir[relPos:]
            for sFile in sFiles:
                rpFile = GPath(os.path.join(rsDir, sFile))
                asFile = os.path.join(asDir, sFile)
                # below calls may now raise even if "werr.winerror = 123"
                lstat = os.lstat(asFile)
                size, date = lstat.st_size, int(lstat.st_mtime)
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
        return int(max_mtime)

    def size_or_mtime_changed(self, apath, _lstat=os.lstat):
        #FIXME(ut): getmtime(True) won't detect all changes - for instance COBL
        # has 3/25/2020 8:02:00 AM modification time if unpacked and no
        # amount of internal shuffling won't change its apath.getmtime(True)
        getM, join = os.path.getmtime, os.path.join
        c, size = [], 0
        cExtend, cAppend = c.extend, c.append
        self._dir_dirs_files = []
        for root, d, files in os.walk(apath.s):
            cAppend(getM(root))
            stats = [_lstat(join(root, fi)) for fi in files]
            cExtend(fi.st_mtime for fi in stats)
            size += sum(fi.st_size for fi in stats)
            self._dir_dirs_files.append((root, [], files)) # dirs is unused
        if self.size != size: return True
        # below is for the fix me - we need to add mtimes_str_crc extra persistent attribute to Installer
        # c.sort() # is this needed or os.walk will return the same order during program run
        # mtimes_str = '.'.join(map(str, c))
        # mtimes_str_crc = crc32(mtimes_str)
        try:
            mtime = int(max(c))
        except ValueError: # int(max([]))
            mtime = 0
        return self.modified != mtime

    @staticmethod
    def removeEmpties(name):
        """Removes empty directories from project directory."""
        empties = set()
        projectDir = bass.dirs['installers'].join(name)
        for asDir,sDirs,sFiles in os.walk(projectDir.s):
            if not (sDirs or sFiles): empties.add(GPath(asDir))
        for empty in empties: empty.removedirs()
        projectDir.makedirs() #--In case it just got wiped out.

    def _refreshSource(self, progress, recalculate_project_crc):
        """Refresh src_sizeCrcDate, fileSizeCrcs, size, modified, crc from
        project directory, set project_refreshed to True."""
        self.modified = self._refresh_from_project_dir(progress,
                                                       recalculate_project_crc)
        cumCRC = 0
##        cumDate = 0
        cumSize = 0
        fileSizeCrcs = self.fileSizeCrcs = []
        for path, (size, crc, date) in self.src_sizeCrcDate.iteritems():
            fileSizeCrcs.append((path.s, size, crc))
##            cumDate = max(date,cumDate)
            cumCRC += crc
            cumSize += size
        self.size = cumSize
        self.crc = cumCRC & 0xFFFFFFFFL
        self.project_refreshed = True

    def install(self, destFiles, progress=None):
        """Install specified files to Oblivion\Data directory."""
        destFiles = set(destFiles)
        data_sizeCrc = self.data_sizeCrc
        dest_src = dict((x,y) for x,y in self.refreshDataSizeCrc(True).iteritems() if x in destFiles)
        if not dest_src: return {}
        progress = progress if progress else bolt.Progress()
        progress.setFull(len(dest_src))
        progress(0, self.archive + u'\n' + _(u'Moving files...'))
        progressPlus = progress.plus
        #--Copy Files
        bass.rmTempDir()
        stageDir = bass.getTempDir()
        stageDataDir = stageDir.join(u'Data')
        stageDataDirJoin = stageDataDir.join
        norm_ghost = Installer.getGhosted() # some.espm -> some.espm.ghost
        norm_ghostGet = norm_ghost.get
        srcDir = bass.dirs['installers'].join(self.archive)
        srcDirJoin = srcDir.join
        data_sizeCrcDate_update = {}
        timestamps = load_order.install_last()
        for dest,src in dest_src.iteritems():
            size,crc = data_sizeCrc[dest]
            srcFull = srcDirJoin(src)
            stageFull = stageDataDirJoin(norm_ghostGet(dest,dest))
            if srcFull.exists():
                srcFull.copyTo(stageFull)
                if bass.reModExt.search(srcFull.s): timestamps(srcFull)
                data_sizeCrcDate_update[dest] = (size,crc,stageFull.mtime)
                progressPlus()
        self._move(len(data_sizeCrcDate_update), progress, stageDataDir)
        #--Update Installers data
        return data_sizeCrcDate_update

    def syncToData(self, projFiles):
        """Copies specified projFiles from Oblivion\Data to project
        directory.
        :type projFiles: set[bolt.Path]"""
        srcDir = bass.dirs['mods']
        srcProj = tuple(
            (x, y) for x, y in self.refreshDataSizeCrc().iteritems() if
            x in projFiles)
        if not srcProj: return 0,0
        #--Sync Files
        updated = removed = 0
        norm_ghost = Installer.getGhosted()
        projDir = bass.dirs['installers'].join(self.archive)
        for src,proj in srcProj:
            srcFull = srcDir.join(norm_ghost.get(src,src))
            projFull = projDir.join(proj)
            if not srcFull.exists():
                projFull.remove()
                removed += 1
            else:
                srcFull.copyTo(projFull)
                updated += 1
        self.removeEmpties(self.archive)
        return updated,removed

    def packToArchive(self,project,archive,isSolid,blockSize,progress=None,release=False):
        """Packs project to build directory. Release filters out development
        material from the archive"""
        length = len(self.fileSizeCrcs)
        if not length: return
        archive, archiveType, solid = compressionSettings(archive, blockSize,
                                                          isSolid)
        outDir = bass.dirs['installers']
        realOutFile = outDir.join(archive)
        outFile = outDir.join(u'bash_temp_nonunicode_name.tmp')
        num = 0
        while outFile.exists():
            outFile += unicode(num)
            num += 1
        project = outDir.join(project)
        with project.unicodeSafe() as projectDir:
            #--Dump file list
            with self.tempList.open('w',encoding='utf-8-sig') as out:
                if release:
                    out.write(u'*thumbs.db\n')
                    out.write(u'*desktop.ini\n')
                    out.write(u'--*\\')
            #--Compress
            command = u'"%s" a "%s" -t"%s" %s -y -r -o"%s" -i!"%s\\*" -x@%s -scsUTF-8 -sccUTF-8' % (
                archives.exe7z, outFile.temp.s, archiveType, solid, outDir.s, projectDir.s, self.tempList.s)
            try:
                compress7z(command, outDir, outFile.tail, projectDir, progress)
            finally:
                self.tempList.remove()
            outFile.moveTo(realOutFile)

    @staticmethod
    def createFromData(projectPath,files,progress=None):
        if not files: return
        progress = progress if progress else bolt.Progress()
        projectPath = bass.dirs['installers'].join(projectPath)
        progress.setFull(len(files))
        srcJoin = bass.dirs['mods'].join
        dstJoin = projectPath.join
        for i,file in enumerate(files):
            progress(i,file.s)
            srcJoin(file).copyTo(dstJoin(file))

    @staticmethod
    def _list_package(apath, log):
        def walkPath(folder, depth):
            for entry in os.listdir(folder):
                path = os.path.join(folder, entry)
                if os.path.isdir(path):
                    log(u' ' * depth + entry + u'\\')
                    depth += 2
                    walkPath(path, depth)
                    depth -= 2
                else:
                    log(u' ' * depth + entry)
        walkPath(apath.s, 0)

    def renameInstaller(self, name_new, data):
        return self._installer_rename(data, name_new)

    def open_readme(self):
        bass.dirs['installers'].join(self.archive, self.hasReadme).start()

    def open_wizard(self):
        bass.dirs['installers'].join(self.archive, self.hasWizard).start()

    def wizard_file(self):
        return bass.dirs['installers'].join(self.archive, self.hasWizard)

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
            it = self.itervalues() if isinstance(self, InstallersData) else \
                self.listData.itervalues()
            for project in it:
                if isinstance(project, InstallerProject):
                    project._dir_dirs_files = None
    return _projects_walk_cache_wrapper

#------------------------------------------------------------------------------
class InstallersData(DataStore):
    """Installers tank data. This is the data source for the InstallersList."""
    # track changes in installed mod inis etc _in the game Data/ dir_ and
    # deletions of mods/Ini Tweaks. Keys are absolute paths (so we can track
    # ini deletions from Data/Ini Tweaks as well as mods/xmls etc in Data/)
    _miscTrackedFiles = {}
    # cache with paths in Data/ that would be skipped but are not, due to
    # an installer having the override skip etc flag on - when turning the skip
    # off leave the files here - will be cleaned on restart (files will show
    # as dirty till then, but to remove them we should examine all installers
    # that override skips - not worth the hassle)
    overridden_skips = set()
    __clean_overridden_after_load = True
    installers_dir_skips = set()

    def __init__(self):
        self.store_dir = bass.dirs['installers']
        self.bash_dir.makedirs()
        #--Persistent data
        self.dictFile = bolt.PickleDict(self.bash_dir.join(u'Installers.dat'))
        self.data = {}
        self.data_sizeCrcDate = {}
        self.crc_installer = {}
        from . import converters
        self.converters_data = converters.ConvertersData(bass.dirs['bainData'],
            bass.dirs['converters'], bass.dirs['dupeBCFs'],
            bass.dirs['corruptBCFs'], bass.dirs['installers'])
        #--Volatile
        self.abnorm_sizeCrc = {} #--Normative sizeCrc, according to order of active packages
        self.bcfPath_sizeCrcDate = {}
        self.hasChanged = False
        self.loaded = False
        self.lastKey = GPath(u'==Last==')

    @property
    def bash_dir(self): return bass.dirs['bainData']

    @property
    def hidden_dir(self): return bass.dirs['modsBash'].join(u'Hidden')

    def add_marker(self, name, order):
        from . import InstallerMarker
        self[name] = InstallerMarker(name)
        if order is None:
            order = self[self.lastKey].order
        self.moveArchives([name], order)

    def setChanged(self,hasChanged=True):
        """Mark as having changed."""
        self.hasChanged = hasChanged

    def refresh(self, *args, **kwargs): return self.irefresh(*args, **kwargs)

    def irefresh(self, progress=None, what='DIONSC', fullRefresh=False,
                 refresh_info=None, deleted=None, pending=None, projects=None):
        progress = progress or bolt.Progress()
        #--Archive invalidation
        from . import oblivionIni, InstallerMarker
        if bass.settings.get('bash.bsaRedirection') and oblivionIni.abs_path.exists():
            oblivionIni.setBsaRedirection(True)
        #--Load Installers.dat if not loaded - will set changed to True
        changed = not self.loaded and self.__load(progress)
        #--Last marker
        if self.lastKey not in self.data:
            self.data[self.lastKey] = InstallerMarker(self.lastKey)
        #--Refresh Other - FIXME(ut): docs
        if 'D' in what:
            changed |= self._refresh_from_data_dir(progress, fullRefresh)
        if 'I' in what: changed |= self._refreshInstallers(
            progress, fullRefresh, refresh_info, deleted, pending, projects)
        if 'O' in what or changed: changed |= self.refreshOrder()
        if 'N' in what or changed: changed |= self.refreshNorm()
        if 'S' in what or changed: changed |= self.refreshInstallersStatus()
        if 'C' in what or changed: changed |= \
            self.converters_data.refreshConverters(progress, fullRefresh)
        #--Done
        if changed: self.hasChanged = True
        return changed

    def __load(self, progress):
        progress(0, _(u"Loading Data..."))
        self.dictFile.load()
        self.converters_data.load()
        data = self.dictFile.data
        self.data = data.get('installers', {})
        self.data_sizeCrcDate = data.get('sizeCrcDate', {})
        self.crc_installer = data.get('crc_installer', {})
        # fixup: all markers had their archive attribute set to u'===='
        for key, value in self.iteritems():
            if isinstance(value, InstallerMarker):
                value.archive = key.s
        self.loaded = True
        return True

    def save(self):
        """Saves to pickle file."""
        if self.hasChanged:
            self.dictFile.data['installers'] = self.data
            self.dictFile.data['sizeCrcDate'] = self.data_sizeCrcDate
            self.dictFile.data['crc_installer'] = self.crc_installer
            self.dictFile.vdata['version'] = 1
            self.dictFile.save()
            self.converters_data.save()
            self.hasChanged = False

    def _rename_operation(self, oldName, newName):
        return self[oldName].renameInstaller(newName, self)

    #--Dict Functions ---------------------------------------------------------
    def files_to_delete(self, filenames, **kwargs):
        toDelete = []
        markers = []
        for item in filenames:
            if item == self.lastKey: continue
            if isinstance(self[item], InstallerMarker): markers.append(item)
            else: toDelete.append(self.store_dir.join(item))
        return toDelete, markers

    def _delete_operation(self, paths, markers, **kwargs):
        for m in markers: del self[m]
        super(InstallersData, self)._delete_operation(paths, markers, **kwargs)

    def delete_refresh(self, deleted, markers, check_existence):
        deleted = set(item.tail for item in deleted if
                      not check_existence or not item.exists())
        if deleted:
            self.irefresh(what='I', deleted=deleted)
        elif markers:
            self.refreshOrder()

    def copy_installer(self,item,destName,destDir=None):
        """Copies archive to new location."""
        if item == self.lastKey: return
        destDir = destDir or self.store_dir
        apath = self.store_dir.join(item)
        apath.copyTo(destDir.join(destName))
        if destDir == self.store_dir:
            self[destName] = installer = copy.copy(self[item])
            installer.archive = destName.s
            installer.isActive = False
            self.moveArchives([destName], self[item].order + 1)

    def move_info(self, filename, destDir):
        # hasty method to use in UIList.hide(), see FileInfos.move_info()
        self.store_dir.join(filename).moveTo(destDir.join(filename))

    def move_infos(self, sources, destinations, window):
        moved = super(InstallersData, self).move_infos(sources, destinations,
                                                       window)
        self.irefresh(what='I', pending=moved)
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
        called on added/updated files and crc_installer updated. If you
        don't need that last step you may directly call refreshBasic.
        :type progress: bolt.Progress | None
        :type fullRefresh: bool
        :type refresh_info: InstallersData._RefreshInfo | None
        :type deleted: collections.Iterable[bolt.Path] | None
        :type pending: collections.Iterable[bolt.Path] | None
        :type projects: collections.Iterable[bolt.Path] | None
        """
        # TODO(ut):we need to return the refresh_info for more granular control
        # in irefresh and also add extra processing for deleted files
        from . import InstallerArchive, InstallerProject # use the bosh types
        progress = progress or bolt.Progress()
        #--Current archives
        if refresh_info is deleted is pending is None:
            refresh_info = self.scan_installers_dir(bass.dirs['installers'].list(),
                                                    fullRefresh)
        elif refresh_info is None:
            refresh_info = self._RefreshInfo(deleted, pending, projects)
        changed = refresh_info.refresh_needed()
        for deleted in refresh_info.deleted:
            self.pop(deleted)
        pending, projects = refresh_info.pending, refresh_info.projects
        #--New/update crcs?
        for subPending, iClass in zip((pending - projects, pending & projects),
                                      (InstallerArchive, InstallerProject)):
            if not subPending: continue
            progress(0,_(u"Scanning Packages..."))
            progress.setFull(len(subPending))
            for index,package in enumerate(sorted(subPending)):
                progress(index,_(u'Scanning Packages...')+u'\n'+package.s)
                installer = self.get(package, None)
                if not installer:
                    installer = self.setdefault(package, iClass(package))
                installer.refreshBasic(SubProgress(progress, index, index + 1),
                                       recalculate_project_crc=fullRefresh)
        if changed: self.crc_installer = dict((x.crc, x) for x in
                        self.itervalues() if isinstance(x, InstallerArchive))
        return changed

    def applyEmbeddedBCFs(self, installers=None, destArchives=None,
                          progress=bolt.Progress()):
        if installers is None:
            installers = [x for x in self.itervalues() if
                          isinstance(x, InstallerArchive) and x.hasBCF]
        if not installers: return False
        if not destArchives:
            destArchives = [GPath(u'[Auto applied BCF] %s' % x.archive) for x
                            in installers]
        progress.setFull(len(installers))
        pending = []
        for i, (installer, destArchive) in enumerate(zip(installers,
                        destArchives)): # no izip - we may modify installers
            progress(i, installer.archive)
            #--Extract the embedded BCF and move it to the Converters folder
            bass.rmTempDir()
            unpack_dir = installer.unpackToTemp([installer.hasBCF],
                SubProgress(progress, i, i + 0.5))
            srcBcfFile = unpack_dir.join(installer.hasBCF)
            bcfFile = bass.dirs['converters'].join(u'temp-' + srcBcfFile.stail)
            srcBcfFile.moveTo(bcfFile)
            bass.rmTempDir()
            #--Create the converter, apply it
            converter = InstallerConverter(bcfFile.tail)
            try:
                msg = u'%s: ' % destArchive.s + _(
                    u'An error occurred while applying an Embedded BCF.')
                self.apply_converter(converter, destArchive,
                                     SubProgress(progress, i + 0.5, i + 1.0),
                                     msg, installer, pending)
            except StateError:
                # maybe short circuit further attempts to extract
                # installer.hasBCF = False
                installers.remove(installer)
            finally: bcfFile.remove()
        self.irefresh(what='I', pending=pending)
        return pending, list(GPath(x.archive) for x in installers)

    def apply_converter(self, converter, destArchive, progress, msg,
                        installer=None, pending=None, show_warning=None,
                        position=-1):
        try:
            converter.apply(destArchive, self.crc_installer,
                            bolt.SubProgress(progress, 0.0, 0.99),
                            embedded=installer.crc if installer else 0L)
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
                self.irefresh(what='I', pending=[destArchive])
                return iArchive
        except StateError:
            deprint(msg, traceback=True)
            if show_warning: show_warning(msg)

    def scan_installers_dir(self, installers_paths=(), fullRefresh=False):
        """March through the Bash Installers dir scanning for new and modified
        projects/packages, skipping as necessary.
        :rtype: InstallersData._RefreshInfo"""
        installers = set()
        installersJoin = bass.dirs['installers'].join
        pending, projects = set(), set()
        for item in installers_paths:
            if item.s.lower().startswith((u'bash',u'--')): continue
            apath = installersJoin(item)
            if apath.isfile() and item.cext in readExts:
                installer = self.get(item)
            elif apath.isdir(): # Project - autorefresh those only if specified
                if item.s.lower() in self.installers_dir_skips:
                    continue # skip Bash directories and user specified ones
                installer = self.get(item)
                projects.add(item)
                # refresh projects once on boot even if skipRefresh is on
                if installer and not installer.project_refreshed:
                    pending.add(item)
                    continue
                elif installer and not fullRefresh and (installer.skipRefresh
                       or not bass.settings['bash.installers.autoRefreshProjects']):
                    installers.add(item) # installer is present
                    continue # and needs not refresh
            else:
                continue ##: treat symlinks
            if fullRefresh or not installer or installer.size_or_mtime_changed(
                    apath):
                pending.add(item)
            else: installers.add(item)
        deleted = set(x for x, y in self.iteritems() if not isinstance(
            y, InstallerMarker)) - installers - pending
        refresh_info = self._RefreshInfo(deleted, pending, projects)
        return refresh_info

    def refreshConvertersNeeded(self):
        """Return True if refreshConverters is necessary. (Point is to skip
        use of progress dialog when possible)."""
        return self.converters_data.refreshConvertersNeeded()

    def refreshOrder(self):
        """Refresh installer status."""
        inOrder, pending = [], []
        # not specifying the key below results in double time
        for archive, installer in sorted(self.iteritems(), key=itemgetter(0)):
            if installer.order >= 0:
                inOrder.append((archive, installer))
            else:
                pending.append((archive, installer))
        inOrder.sort(key=lambda x: x[1].order)
        for dex, (key, value) in enumerate(inOrder):
            if self.lastKey == key:
                inOrder[dex:dex] = pending
                break
        else:
            inOrder += pending
        changed = False
        for order, (archive, installer) in enumerate(inOrder):
            if installer.order != order:
                installer.order = order
                changed = True
        return changed

    def refreshNorm(self):
        """Refresh self.abnorm_sizeCrc."""
        active_sorted = sorted([x for x in self.itervalues() if x.isActive],
                               key=attrgetter('order'))
        #--norm
        norm_sizeCrc = {}
        for package in active_sorted:
            norm_sizeCrc.update(package.data_sizeCrc)
        #--Abnorm
        abnorm_sizeCrc = {}
        dataGet = self.data_sizeCrcDate.get
        for path,sizeCrc in norm_sizeCrc.iteritems():
            sizeCrcDate = dataGet(path)
            if sizeCrcDate and sizeCrc != sizeCrcDate[:2]:
                abnorm_sizeCrc[path] = sizeCrcDate[:2]
        self.abnorm_sizeCrc, oldAbnorm_sizeCrc = \
            abnorm_sizeCrc, self.abnorm_sizeCrc
        return abnorm_sizeCrc != oldAbnorm_sizeCrc

    def refreshInstallersStatus(self):
        """Refresh installer status."""
        changed = False
        for installer in self.itervalues():
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
        progress_msg = bass.dirs['mods'].stail + u': ' + _(u'Pre-Scanning...')
        progress(0, progress_msg + u'\n')
        progress.setFull(1)
        dirDirsFiles, emptyDirs = [], set()
        dirDirsFilesAppend, emptyDirsAdd = dirDirsFiles.append, emptyDirs.add
        asRoot = bass.dirs['mods'].s
        relPos = len(asRoot) + 1
        for asDir, sDirs, sFiles in os.walk(asRoot):
            progress(0.05, progress_msg + (u'\n%s' % asDir[relPos:]))
            if not (sDirs or sFiles): emptyDirsAdd(GPath(asDir))
            if asDir == asRoot: InstallersData._skips_in_data_dir(sDirs)
            dirDirsFilesAppend((asDir, sDirs, sFiles))
        progress(0, _(u"%s: Scanning...") % bass.dirs['mods'].stail)
        new_sizeCrcDate, pending, pending_size = \
            self._process_data_dir(dirDirsFiles, progress)
        #--Remove empty dirs?
        if bass.settings['bash.installers.removeEmptyDirs']:
            for empty in emptyDirs:
                try: empty.removedirs()
                except OSError: pass
        changed = Installer.final_update(new_sizeCrcDate,
                                         self.data_sizeCrcDate, pending,
                                         pending_size, progress,
                                         recalculate_all_crcs,
                                         bass.dirs['mods'].stail)
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
        pending, pending_size = {}, 0
        new_sizeCrcDate = {}
        oldGet = self.data_sizeCrcDate.get
        norm_ghost = Installer.getGhosted()
        ghost_norm = dict((y, x) for x, y in norm_ghost.iteritems())
        bethFiles = set() if bass.settings[
            'bash.installers.autoRefreshBethsoft'] else bush.game.bethDataFiles
        skipExts = Installer.skipExts
        ghostGet = ghost_norm.get
        relPos = len(bass.dirs['mods'].s) + 1
        for index, (asDir, __sDirs, sFiles) in enumerate(dirDirsFiles):
            progress(index)
            rsDir = asDir[relPos:]
            for sFile in sFiles:
                top_level_espm = False
                if not rsDir:
                    rpFile = GPath(sFile) # relative Path to file
                    rpFile = ghostGet(rpFile, rpFile)
                    ext = rpFile.cs[rpFile.s.rfind(u'.'):]
                    if ext in skipExts: continue
                    if rpFile.cs in bethFiles: continue
                    top_level_espm = ext in {u'.esp', u'.esm'}
                else: rpFile = GPath(os.path.join(rsDir, sFile))
                asFile = os.path.join(asDir, sFile)
                # below calls may now raise even if "werr.winerror = 123"
                try:
                    oSize, oCrc, oDate = oldGet(rpFile, (0, 0, 0))
                    if top_level_espm: # modInfos MUST BE UPDATED
                        try:
                            modInfo = modInfos[rpFile]
                            new_sizeCrcDate[rpFile] = (modInfo.size,
                               modInfo.cached_mod_crc(), modInfo.mtime, asFile)
                            continue
                        except KeyError:
                            pass # corrupted/missing, let os.lstat decide
                    lstat = os.lstat(asFile)
                    size, date = lstat.st_size, int(lstat.st_mtime)
                    if size != oSize or date != oDate:
                        pending[rpFile] = (size, oCrc, date, asFile)
                        pending_size += size
                    else:
                        new_sizeCrcDate[rpFile] = (oSize, oCrc, oDate, asFile)
                except OSError as e:
                    if e.errno == errno.ENOENT: continue # file does not exist
                    raise
        return new_sizeCrcDate, pending, pending_size

    def reset_refresh_flag_on_projects(self):
        for installer in self.itervalues():
            if isinstance(installer, InstallerProject):
                installer.project_refreshed = False

    @staticmethod
    def _skips_in_data_dir(sDirs):
        """Skip some top level directories based on global settings - EVEN
        on a fullRefresh."""
        log = None
        if bass.inisettings['KeepLog'] > 1:
            try: log = bass.inisettings['LogFile'].open('a', encoding='utf-8-sig')
            except: pass
        setSkipOBSE = not bass.settings['bash.installers.allowOBSEPlugins']
        setSkipDocs = bass.settings['bash.installers.skipDocs']
        setSkipImages = bass.settings['bash.installers.skipImages']
        newSDirs = (x for x in sDirs if
                    x.lower() not in Installer.dataDirsMinus)
        if bass.settings['bash.installers.skipDistantLOD']:
            newSDirs = (x for x in newSDirs if x.lower() != u'distantlod')
        if bass.settings['bash.installers.skipLandscapeLODMeshes']:
            newSDirs = (x for x in newSDirs if x.lower() != os.path.join(
                u'meshes', u'landscape', u'lod'))
        if bass.settings['bash.installers.skipScreenshots']:
            newSDirs = (x for x in newSDirs if x.lower() != u'screenshots')
        # LOD textures
        if bass.settings['bash.installers.skipLandscapeLODTextures'] and \
                bass.settings['bash.installers.skipLandscapeLODNormals']:
            newSDirs = (x for x in newSDirs if x.lower() != os.path.join(
                u'textures', u'landscapelod', u'generated'))
        if setSkipOBSE:
            newSDirs = (x for x in newSDirs if
                        x.lower() != bush.game.se.shortName.lower())
        if bush.game.sd.shortName and setSkipOBSE:
            newSDirs = (x for x in newSDirs if
                        x.lower() != bush.game.sd.installDir.lower())
        if setSkipDocs and setSkipImages:
            newSDirs = (x for x in newSDirs if x.lower() != u'docs')
        newSDirs = (x for x in newSDirs if
                    x.lower() not in bush.game.SkipBAINRefresh)
        sDirs[:] = [x for x in newSDirs]
        if log:
            log.write(u'(in refreshSizeCRCDate after accounting for skipping) '
                      u'sDirs = %s\r\n' % (sDirs[:]))
            log.close()

    def update_data_SizeCrcDate(self, dest_paths, progress=None):
        """Update data_SizeCrcDate with info on given paths.
        :param progress: must be zeroed - message is used in _process_data_dir
        :param dest_paths: set of paths relative to Data/ - may not exist."""
        root_files = []
        norm_ghost = Installer.getGhosted()
        for path in dest_paths:
            sp = path.s.rsplit(os.sep, 1) # split into ['rel_path, 'file']
            if len(sp) == 1: # top level file
                name = norm_ghost.get(path, path)
                root_files.append((bass.dirs['mods'].s, name.s))
            else:
                root_files.append((bass.dirs['mods'].join(sp[0]).s, sp[1]))
        root_dirs_files = []
        root_files.sort(key=itemgetter(0)) # must sort on same key as groupby
        for key, val in groupby(root_files, key=itemgetter(0)):
            root_dirs_files.append((key, [], [j for i, j in val]))
        progress = progress or bolt.Progress()
        new_sizeCrcDate, pending, pending_size = self._process_data_dir(
            root_dirs_files, progress)
        deleted_or_pending = set(dest_paths) - set(new_sizeCrcDate)
        for d in deleted_or_pending: self.data_sizeCrcDate.pop(d, None)
        Installer.calc_crcs(pending, pending_size, bass.dirs['mods'].stail,
                            new_sizeCrcDate, progress)
        for rpFile, (size, crc, date, _asFile) in new_sizeCrcDate.iteritems():
            self.data_sizeCrcDate[rpFile] = (size, crc, date)

    def update_for_overridden_skips(self, dont_skip=None, progress=None):
        if dont_skip is not None:
            dont_skip.difference_update(self.data_sizeCrcDate)
            self.overridden_skips |= dont_skip
        elif self.__clean_overridden_after_load:
            self.overridden_skips.difference_update(self.data_sizeCrcDate)
            self.__clean_overridden_after_load = False
        new_skips_overrides = self.overridden_skips - set(self.data_sizeCrcDate)
        progress = progress or bolt.Progress()
        progress(0, (
            _(u"%s: Skips overrides...") % bass.dirs['mods'].stail) + u'\n')
        self.update_data_SizeCrcDate(new_skips_overrides, progress)

    @staticmethod
    def track(abspath):
        InstallersData._miscTrackedFiles[abspath] = AFile(abspath)

    @staticmethod
    def refreshTracked():
        changed = set()
        for abspath, tracked in InstallersData._miscTrackedFiles.items():
            if not abspath.exists(): # untrack - runs on first run !!
                InstallersData._miscTrackedFiles.pop(abspath, None)
                changed.add(abspath)
            elif tracked.needs_update():
                changed.add(abspath)
        return changed

    #--Operations -------------------------------------------------------------
    def moveArchives(self,moveList,newPos):
        """Move specified archives to specified position."""
        old_ordered = self.sorted_values(set(self.data) - set(moveList))
        new_ordered = self.sorted_values(moveList)
        if newPos >= len(self.keys()): newPos = len(old_ordered)
        for index, installer in enumerate(old_ordered[:newPos]):
            installer.order = index
        for index, installer in enumerate(new_ordered):
            installer.order = newPos + index
        for index, installer in enumerate(old_ordered[newPos:]):
            installer.order = newPos + len(new_ordered) + index
        self.setChanged()

    @staticmethod
    def updateTable(destFiles, value):
        """Set the 'installer' column in mod and ini tables for the
        destFiles."""
        mods_changed, inis_changed = False, False
        from . import modInfos, iniInfos
        for i in destFiles:
            if value and bass.reModExt.match(i.cext): # if value == u'' we come from delete !
                mods_changed = True
                modInfos.table.setItem(i, 'installer', value)
            elif i.head.cs == u'ini tweaks':
                inis_changed = True
                if value:
                    iniInfos.table.setItem(i.tail, 'installer', value)
                else: # installer is the only column used in iniInfos table
                    iniInfos.table.delRow(i.tail)
        return mods_changed, inis_changed

    #--Install
    def _createTweaks(self, destFiles, installer, tweaksCreated):
        """Generate INI Tweaks when a CRC mismatch is detected while
        installing a mod INI (not ini tweak) in the Data/ directory.

        If the current CRC of the ini is different than the one BAIN is
        installing, a tweak file will be generated. Call me *before*
        installing the new inis then call _editTweaks() to populate the tweaks.
        """
        dest_files = (x for x in destFiles if x .cext in (u'.ini', u'.cfg') and
                # don't create ini tweaks for overridden ini tweaks...
                x.head.cs != u'ini tweaks')
        for relPath in dest_files:
            oldCrc = self.data_sizeCrcDate.get(relPath, (None, None, None))[1]
            newCrc = installer.data_sizeCrc.get(relPath, (None, None))[1]
            if oldCrc is None or newCrc is None or newCrc == oldCrc: continue
            iniAbsDataPath = bass.dirs['mods'].join(relPath)
            # Create a copy of the old one
            baseName = bass.dirs['tweaks'].join(u'%s, ~Old Settings [%s].ini' % (
                iniAbsDataPath.sbody, installer.archive))
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
        for (tweakPath, iniAbsDataPath) in tweaksCreated:
            iniFile = BestIniFile(iniAbsDataPath)
            currSection = None
            lines = []
            with tweakPath.open('r') as tweak:
                tweak_lines = tweak.readlines()
            for (text, section, setting, value, status, lineNo,
                 deleted) in iniFile.get_lines_infos(tweak_lines):
                if status in (10, -10):
                    # A setting that exists in both INI's, but is different,
                    # or a setting that doesn't exist in the new INI.
                    if section == u']set[' or section == u']setGS[' or section == u']SetNumericGameSetting[':
                        lines.append(text + u'\n')
                    elif section != currSection:
                        section = currSection
                        if not section: continue
                        lines.append(u'\n[%s]\n' % section)
                    elif not section:
                        continue
                    else:
                        lines.append(text + u'\n')
            if not lines: # avoid creating empty tweaks
                removed.add((tweakPath, iniAbsDataPath))
                tweakPath.remove()
                continue
            # Re-write the tweak
            with tweakPath.open('w') as ini:
                ini.write(u'; INI Tweak created by Wrye Bash, using settings '
                          u'from old file.\n\n')
                ini.writelines(lines)
        tweaksCreated -= removed

    def _install(self, packages, refresh_ui, progress=None, last=False,
                 override=True):
        """Install selected packages.
        what:
            'MISSING': only missing files.
            Otherwise: all (unmasked) files.
        """
        progress = progress or bolt.Progress()
        tweaksCreated = set()
        #--Mask and/or reorder to last
        mask = set()
        if last:
            self.moveArchives(packages, len(self))
        else:
            maxOrder = max(self[x].order for x in packages)
            for installer in self.itervalues():
                if installer.order > maxOrder and installer.isActive:
                    mask |= set(installer.data_sizeCrc)
        #--Install packages in turn
        progress.setFull(len(packages))
        for index, installer in enumerate(
                self.sorted_values(packages, reverse=True)):
            progress(index,installer.archive)
            destFiles = set(installer.data_sizeCrc) - mask
            if not override:
                destFiles &= installer.missingFiles
            if destFiles:
                self._createTweaks(destFiles, installer, tweaksCreated)
                self.__installer_install(installer, destFiles, index, progress,
                                         refresh_ui)
            installer.isActive = True
            mask |= set(installer.data_sizeCrc)
        if tweaksCreated:
            self._editTweaks(tweaksCreated)
            refresh_ui[1] |= bool(tweaksCreated)
        return tweaksCreated

    def __installer_install(self, installer, destFiles, index, progress,
                            refresh_ui):
        sub_progress = SubProgress(progress, index, index + 1)
        data_sizeCrcDate_update = installer.install(destFiles, sub_progress)
        self.data_sizeCrcDate.update(data_sizeCrcDate_update)
        mods_changed, inis_changed = InstallersData.updateTable(destFiles,
            installer.archive)
        refresh_ui[0] |= mods_changed
        refresh_ui[1] |= inis_changed

    def sorted_pairs(self, package_keys=None, reverse=False):
        """Return pairs of key, installer for package_keys in self, sorted by
        install order.
        :type package_keys: None | collections.Iterable[Path]
        :rtype: list[(Path, Installer)]
        """
        if package_keys is None: pairs = self.items()
        else: pairs = [(k, self[k]) for k in package_keys]
        return sorted(pairs, key=lambda tup: tup[1].order, reverse=reverse)

    def sorted_values(self, package_keys=None, reverse=False):
        """Return installers for package_keys in self, sorted by install order.
        :type package_keys: None | collections.Iterable[Path]
        :rtype: list[Installer]
        """
        if package_keys is None: pairs = self.values()
        else: pairs = [self[k] for k in package_keys]
        return sorted(pairs, key=attrgetter('order'), reverse=reverse)

    def bain_install(self, packages, refresh_ui, progress=None, last=False,
                     override=True):
        try: return self._install(packages, refresh_ui, progress, last,
                                  override)
        finally: self.irefresh(what='NS')

    #--Uninstall, Anneal, Clean
    @staticmethod
    def _determineEmptyDirs(emptyDirs, removedFiles):
        allRemoves = set(removedFiles)
        allRemovesAdd, removedFilesAdd = allRemoves.add, removedFiles.add
        emptyDirsClear, emptyDirsAdd = emptyDirs.clear, emptyDirs.add
        exclude = {bass.dirs['mods'], bass.dirs['mods'].join(u'Docs')} # don't bother
        # with those (Data won't likely be removed and Docs we want it around)
        emptyDirs -= exclude
        while emptyDirs:
            testDirs = set(emptyDirs)
            emptyDirsClear()
            for folder in sorted(testDirs, key=len, reverse=True):
                # Sorting by length, descending, ensure we always
                # are processing the deepest directories first
                files = set(imap(folder.join, folder.list()))
                remaining = files - allRemoves
                if not remaining: # If all items in this directory will be
                    # removed, this directory is also safe to remove.
                    removedFiles -= files
                    removedFilesAdd(folder)
                    allRemovesAdd(folder)
                    emptyDirsAdd(folder.head)
            emptyDirs -= exclude
        return removedFiles

    def _removeFiles(self, removes, refresh_ui, progress=None):
        """Performs the actual deletion of files and updating of internal data.clear
           used by 'bain_uninstall' and 'bain_anneal'."""
        modsDirJoin = bass.dirs['mods'].join
        emptyDirs = set()
        emptyDirsAdd = emptyDirs.add
        removedFiles = set()
        removedFilesAdd = removedFiles.add
        reModExtSearch = bass.reModExt.search
        removedPlugins = set()
        removedPluginsAdd = removedPlugins.add
        #--Construct list of files to delete
        for relPath in removes:
            path = modsDirJoin(relPath)
            if path.exists():
                removedFilesAdd(path)
            if reModExtSearch(relPath.s):
                removedPluginsAdd(relPath)
            emptyDirsAdd(path.head)
        #--Now determine which directories will be empty, replacing subsets of
        # removedFiles by their parent dir if the latter will be emptied
        removedFiles = self._determineEmptyDirs(emptyDirs, removedFiles)
        nonPlugins = removedFiles - set(imap(modsDirJoin, removedPlugins))
        ex = None # if an exception is raised we must again check removes
        try: #--Do the deletion
            if nonPlugins:
                parent = progress.getParent() if progress else None
                env.shellDelete(nonPlugins, parent=parent)
            #--Delete mods and remove them from load order
            if removedPlugins:
                from . import modInfos
                refresh_ui[0] = True
                modInfos.delete(removedPlugins, doRefresh=False, recycle=False,
                                raise_on_master_deletion=False)
        except (bolt.CancelError, bolt.SkipError): ex = sys.exc_info()
        except:
            ex = sys.exc_info()
            raise
        finally:
            if ex:removes = [f for f in removes if not modsDirJoin(f).exists()]
            mods_changed, inis_changed = InstallersData.updateTable(removes,
                                                                    u'')
            refresh_ui[0] |= mods_changed
            refresh_ui[1] |= inis_changed
            #--Update InstallersData
            data_sizeCrcDatePop = self.data_sizeCrcDate.pop
            for relPath in removes:
                data_sizeCrcDatePop(relPath, None)

    def __restore(self, installer, removes, restores):
        """Populate restores dict with files to be restored by this
        installer, removing those from removes.

        Returns all of the files this installer would install. Used by
        'bain_uninstall' and 'bain_anneal'."""
        # get all destination files for this installer
        files = set(installer.data_sizeCrc)
        # keep those to be removed while not restored by a higher order package
        to_keep = (removes & files) - set(restores)
        for dest_file in to_keep:
            if installer.data_sizeCrc[dest_file] != \
                    self.data_sizeCrcDate.get(dest_file,(0, 0, 0))[:2]:
                # restore it from this installer
                restores[dest_file] = GPath(installer.archive)
            removes.discard(dest_file) # don't remove it anyway
        return files

    def bain_uninstall(self, unArchives, refresh_ui, progress=None):
        """Uninstall selected archives."""
        if unArchives == 'ALL': unArchives = self.data
        unArchives = set(unArchives)
        data_sizeCrcDate = self.data_sizeCrcDate
        #--Determine files to remove and files to restore. Keep in mind that
        #  multiple input archives may be interspersed with other archives that
        #  may block (mask) them from deleting files and/or may provide files
        #  that should be restored to make up for previous files. However,
        #  restore can be skipped, if existing files matches the file being
        #  removed.
        masked = set()
        removes = set()
        restores = {}
        #--March through archives in reverse order...
        for archive, installer in self.sorted_pairs(reverse=True):
            #--Uninstall archive?
            if archive in unArchives:
                for data_sizeCrc in (installer.data_sizeCrc,installer.dirty_sizeCrc):
                    for file,sizeCrc in data_sizeCrc.iteritems():
                        sizeCrcDate = data_sizeCrcDate.get(file)
                        if file not in masked and sizeCrcDate and sizeCrcDate[:2] == sizeCrc:
                            removes.add(file)
            #--Other active archive. May undo previous removes, or provide a restore file.
            #  And/or may block later uninstalls.
            elif installer.isActive:
                masked |= self.__restore(installer, removes, restores)
        try:
            #--Remove files, update InstallersData, update load order
            self._removeFiles(removes, refresh_ui, progress)
            #--De-activate
            for archive in unArchives:
                self[archive].isActive = False
            #--Restore files
            if bass.settings['bash.installers.autoAnneal']:
                self._restoreFiles(restores, refresh_ui, progress)
        finally:
            self.irefresh(what='NS')

    def _restoreFiles(self, restores, refresh_ui, progress):
        installer_destinations = {}
        restores = sorted(restores.items(), key=itemgetter(1))
        for key, group in groupby(restores, key=itemgetter(1)):
            installer_destinations[key] = set(dest for dest, _key in group)
        if not installer_destinations: return
        installer_destinations = sorted(installer_destinations.items(),
            key=lambda item: self[item[0]].order)
        progress.setFull(len(installer_destinations))
        for index, (archive, destFiles) in enumerate(installer_destinations):
            progress(index, archive.s)
            if destFiles:
                installer = self[archive]
                self.__installer_install(installer, destFiles, index, progress,
                                         refresh_ui)

    def bain_anneal(self, anPackages, refresh_ui, progress=None):
        """Anneal selected packages. If no packages are selected, anneal all.
        Anneal will:
        * Correct underrides in anPackages.
        * Install missing files from active anPackages."""
        progress = progress if progress else bolt.Progress()
        anPackages = set(anPackages or self.keys())
        #--Get remove/refresh files from anPackages
        removes = set()
        for package in anPackages:
            installer = self[package]
            removes |= installer.underrides
            if installer.isActive:
                removes |= installer.missingFiles
                removes |= set(installer.dirty_sizeCrc)
            installer.dirty_sizeCrc.clear()
        #--March through packages in reverse order...
        restores = {}
        for installer in self.sorted_values(reverse=True):
            #--Other active package. May provide a restore file.
            #  And/or may block later uninstalls.
            if installer.isActive:
                self.__restore(installer, removes, restores)
        try:
            #--Remove files, update InstallersData, update load order
            self._removeFiles(removes, refresh_ui, progress)
            #--Restore files
            self._restoreFiles(restores, refresh_ui, progress)
        finally:
            self.irefresh(what='NS')

    def clean_data_dir(self, refresh_ui):
        getArchiveOrder = lambda x: x.order
        keepFiles = set()
        for installer in sorted(self.values(), key=getArchiveOrder,
                                reverse=True):
            if installer.isActive:
                keepFiles.update(installer.data_sizeCrc)
        keepFiles.update((GPath(f) for f in bush.game.allBethFiles))
        keepFiles.update((GPath(f) for f in bush.game.wryeBashDataFiles))
        keepFiles.update((GPath(f) for f in bush.game.ignoreDataFiles))
        removes = set(self.data_sizeCrcDate) - keepFiles
        destDir = bass.dirs['bainData'].join(u'Data Folder Contents (%s)' %
            bolt.timestamp())
        skipPrefixes = [os.path.normcase(skipDir)+os.sep for skipDir in bush.game.wryeBashDataDirs]
        skipPrefixes.extend([os.path.normcase(skipDir)+os.sep for skipDir in bush.game.ignoreDataDirs])
        skipPrefixes.extend([os.path.normcase(skipPrefix) for skipPrefix in bush.game.ignoreDataFilePrefixes])
        skipPrefixes = tuple(skipPrefixes)
        try:
            self._clean_data_dir(self.data_sizeCrcDate, destDir, removes,
                                 skipPrefixes, refresh_ui)
        finally:
            self.irefresh(what='NS')

    @staticmethod
    def _clean_data_dir(data_sizeCrcDate, destDir, removes, skipPrefixes,
                        refresh_ui): # we do _not_ remove Ini Tweaks/*
        emptyDirs = set()
        def isMod(p): return bass.reModExt.search(p.s) is not None
        for filename in removes:
            # don't remove files in Wrye Bash-related directories
            if filename.cs.startswith(skipPrefixes): continue
            full_path = bass.dirs['mods'].join(filename)
            try:
                if full_path.exists():
                    full_path.moveTo(destDir.join(filename))
                    if not refresh_ui[0]: refresh_ui[0] = isMod(full_path)
                else: # Try if it's a ghost - belongs to modInfos...
                    full_path = GPath(full_path.s + u'.ghost')
                    if full_path.exists():
                        full_path.moveTo(destDir.join(filename))
                        refresh_ui[0] = True
                    else: continue # don't pop if file was not removed
                data_sizeCrcDate.pop(filename, None)
                emptyDirs.add(full_path.head)
            except:
                # It's not imperative that files get moved, so ignore errors
                deprint(u'Clean Data: moving %s to % s failed' % (
                            full_path, destDir), traceback=True)
        for emptyDir in emptyDirs:
            if emptyDir.isdir() and not emptyDir.list():
                emptyDir.removedirs()

    #--Utils
    def getConflictReport(self,srcInstaller,mode):
        """Returns report of overrides for specified package for display on conflicts tab.
        mode: OVER: Overrides; UNDER: Underrides"""
        srcOrder = srcInstaller.order
        conflictsMode = (mode == 'OVER')
        if conflictsMode:
            #mismatched = srcInstaller.mismatchedFiles | srcInstaller.missingFiles
            mismatched = set(srcInstaller.data_sizeCrc)
        else:
            mismatched = srcInstaller.underrides
        if not mismatched: return u''
        showInactive = conflictsMode and bass.settings['bash.installers.conflictsReport.showInactive']
        showLower = conflictsMode and bass.settings['bash.installers.conflictsReport.showLower']
        showBSA = bass.settings['bash.installers.conflictsReport.showBSAConflicts']
        src_sizeCrc = srcInstaller.data_sizeCrc
        packConflicts = []
        bsaConflicts = []
        # Calculate bsa conflicts
        if showBSA:
            from . import BSAError, BSAInfo, bsaInfos # yak! rework singletons
            def _get_active_bsas(data_sizeCrc):
                return (v for k, v in bsaInfos.iteritems() if
                        k in data_sizeCrc and v.is_bsa_active())
            # Map srcInstaller's active bsas' assets to those bsas, assigning
            # the assets to the highest loading bsa - 99% we have just one bsa
            src_bsa_to_assets, src_assets = collections.OrderedDict(), set()
            for b in sorted(_get_active_bsas(srcInstaller.data_sizeCrc),
                            key=BSAInfo.active_bsa_index, reverse=True):
                try:
                    b_assets = b.assets - src_assets
                except BSAError:
                    deprint(u'Error parsing %s [%s]' % (
                        b.name, srcInstaller.archive), traceback=True)
                    continue
                if b_assets:
                    src_bsa_to_assets[b] = b_assets
                    src_assets |= b_assets
            # Calculate all conflicts and save them in bsaConflicts
            for package, installer in self.sorted_pairs():
                if installer.order == srcOrder or (
                            not showInactive and not installer.isActive):
                    continue # check active installers different than src
                for bsa_info in _get_active_bsas(installer.data_sizeCrc):
                    try:
                        curAssets = bsa_info.assets
                    except BSAError:
                        deprint(u'Error parsing %s [%s]' % (
                            bsa_info.name, installer.archive), traceback=True)
                        continue
                    curConflicts = bolt.sortFiles(
                        [x for x in curAssets if x in src_assets])
                    if curConflicts:
                        bsaConflicts.append((package, bsa_info, curConflicts))
            bsaConflicts.sort(key=lambda tup: BSAInfo.active_bsa_index(tup[1]))
        # Calculate esp/esm conflicts
        for package, installer in self.sorted_pairs():
            if installer.order == srcOrder or (
                    not showInactive and not installer.isActive): continue
            if not showLower and installer.order < srcOrder: continue
            curConflicts = bolt.sortFiles(
                [x.s for x,y in installer.data_sizeCrc.iteritems()
                if x in mismatched and y != src_sizeCrc[x]])
            if curConflicts:
                packConflicts.append((installer, package.s, curConflicts))
        # Generate report
        with sio() as buff:
            # Print BSA conflicts
            if showBSA:
                buff.write(u'= %s %s\n\n' % (_(u'BSA Conflicts'), u'=' * 40))
                #map bsas (lowest loading bsas first) to their set of conflicts
                bsa_package_to_conflicts = collections.OrderedDict()
                for package, bsa, srcFiles in bsaConflicts:
                    src_bsa_to_confl = collections.defaultdict(list)
                    for confl in srcFiles:
                        for i, j in src_bsa_to_assets.iteritems():
                            if confl in j:
                                src_bsa_to_confl[i].append(confl)
                    bsa_package_to_conflicts[(bsa, package)] = src_bsa_to_confl
                # Print partitions - bsa loading order NOT installer order
                lower, higher = [], []
                for (bsa, package), (src_bsa_to_confl) in \
                        bsa_package_to_conflicts.iteritems():
                    bsa_order = bsa.active_bsa_index()
                    for src_bsa, confl in src_bsa_to_confl.iteritems():
                        partition = higher if (
                            src_bsa.active_bsa_index() < bsa_order) else lower
                        partition.append((bsa, package, confl))
                def _print_bsa_conflicts(conflicts, title=_(u'Lower')):
                    buff.write(u'= %s %s\n' % (title, u'=' * 40))
                    for bsa_, package_, confl_ in conflicts:
                        buff.write(u'==%X== %s : %s\n' % (
                            bsa_.active_bsa_index(), package_, bsa_.name))
                        buff.write(u'\n'.join(confl_) + u'\n\n')
                if showLower and lower:
                    _print_bsa_conflicts(lower, _(u'Lower'))
                if higher:
                    _print_bsa_conflicts(higher, _(u'Higher'))
            isHigher = -1
            if showBSA: buff.write(
                u'= %s %s\n\n' % (_(u'Loose File Conflicts'), u'=' * 36))
            # Print loose file conflicts
            for installer,package,srcFiles in packConflicts:
                order = installer.order
                # Print partitions
                if showLower and (order > srcOrder) != isHigher:
                    isHigher = (order > srcOrder)
                    buff.write(u'= %s %s\n' % ((_(u'Lower'),_(u'Higher'))[isHigher],u'='*40))
                buff.write(u'==%d== %s\n'% (order,package))
                # Print srcFiles
                for src_file in srcFiles:
                    oldName = installer.getEspmName(src_file)
                    buff.write(oldName)
                    if oldName != src_file:
                        buff.write(u' -> ')
                        buff.write(src_file)
                    buff.write(u'\n')
                buff.write(u'\n')
            report = buff.getvalue()
        if not conflictsMode and not report and not srcInstaller.isActive:
            report = _(u"No Underrides. Mod is not completely un-installed.")
        return report

    def getPackageList(self,showInactive=True):
        """Returns package list as text."""
        #--Setup
        with sio() as out:
            log = bolt.LogFile(out)
            log.setHeader(_(u'Bain Packages:'))
            #--List
            log(u'[spoiler][xml]\n',False)
            for package, installer in self.sorted_pairs():
                prefix = u'%03d' % installer.order
                if isinstance(installer, InstallerMarker):
                    log(u'%s - %s' % (prefix, package.s))
                elif installer.isActive:
                    log(u'++ %s - %s (%08X) (Installed)' % (
                        prefix, package.s, installer.crc))
                elif showInactive:
                    log(u'-- %s - %s (%08X) (Not Installed)' % (
                        prefix, package.s, installer.crc))
            log(u'[/xml][/spoiler]')
            return bolt.winNewLines(log.out.getvalue())

    def filterInstallables(self, installerKeys):
        """Return a sublist of installerKeys that can be installed -
        installerKeys must be in data or a KeyError is raised.
        :param installerKeys: an iterable of bolt.Path
        :return: a list of installable packages/projects bolt.Path
        """
        def installable(x): # type -> 0: unset/invalid; 1: simple; 2: complex
            return self[x].type in (1, 2) and isinstance(self[x],
                (InstallerArchive, InstallerProject))
        return filter(installable, installerKeys)

    def filterPackages(self, installerKeys):
        """Remove markers from installerKeys.
        :type installerKeys: collections.Iterable[bolt.Path]
        :rtype: list[bolt.Path]
        """
        def _package(x):
            return isinstance(self[x], (InstallerArchive, InstallerProject))
        return filter(_package, installerKeys)
