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

"""The data model, complete with initialization functions. Main hierarchies
are the DataStore singletons and AFile subclasses populating the data
stores. bush.game must be set, to properly instantiate the data stores."""

# Imports ---------------------------------------------------------------------
#--Python
import cPickle
import collections
import errno
import os
import re
import string
import struct
import sys
import time
import traceback
from collections import OrderedDict
from functools import wraps, partial
from itertools import imap
#--Local
from ._mergeability import isPBashMergeable, isCBashMergeable
from .mods_metadata import ConfigHelpers
from .. import bass, bolt, balt, bush, env, load_order, archives
from .. import patcher # for configIsCBash()
from ..archives import readExts
from ..bass import dirs, inisettings, tooldirs
from ..bolt import GPath, DataDict, cstrip, deprint, sio, Path, decode, \
    unpack_many, unpack_byte, struct_pack, struct_unpack
from ..brec import MreRecord, ModReader
from ..cint import CBashApi
from ..exception import AbstractError, ArgumentError, BoltError, BSAError, \
    CancelError, FileError, ModError, NonExistentDriveError, PermissionError, \
    PluginsFullError, SaveFileError, SaveHeaderError, SkipError, StateError
from ..parsers import ModFile

# Singletons, Constants -------------------------------------------------------
#--Constants
oldTags = sorted((u'Merge',))
oldTagsSet = set(oldTags)
reOblivion = re.compile(
    u'^(Oblivion|Nehrim)(|_SI|_1.1|_1.1b|_1.5.0.8|_GOTY non-SI).esm$', re.U)

undefinedPath = GPath(u'C:\\not\\a\\valid\\path.exe')
empty_path = GPath(u'') # evaluates to False in boolean expressions
undefinedPaths = {GPath(u'C:\\Path\\exe.exe'), undefinedPath}
#..Bit-and this with the fid to get the objectindex.
oiMask = 0xFFFFFFL

#--Singletons
gameInis = None    # type: tuple[OblivionIni]
oblivionIni = None # type: OblivionIni
modInfos  = None   # type: ModInfos
saveInfos = None   # type: SaveInfos
iniInfos = None    # type: INIInfos
bsaInfos = None    # type: BSAInfos
screensData = None # type: ScreensData
#--Config Helper files (LOOT Master List, etc.)
configHelpers = None # type: mods_metadata.ConfigHelpers

#--Header tags
reVersion = re.compile(
  ur'^(version[:.]*|ver[:.]*|rev[:.]*|r[:.\s]+|v[:.\s]+) *([-0-9a-zA-Z.]*\+?)',
  re.M | re.I | re.U)

#--Mod Extensions
__exts = ur'((\.(' + ur'|'.join(ext[1:] for ext in readExts) + ur'))|)$'
reTesNexus = re.compile(ur'(.*?)(?:-(\d{1,6})(?:\.tessource)?(?:-bain)'
    ur'?(?:-\d{0,6})?(?:-\d{0,6})?(?:-\d{0,6})?(?:-\w{0,16})?(?:\w)?)?'
    + __exts, re.I | re.U)
reTESA = re.compile(ur'(.*?)(?:-(\d{1,6})(?:\.tessource)?(?:-bain)?)?'
    + __exts, re.I | re.U)
del __exts
imageExts = {u'.gif', u'.jpg', u'.png', u'.jpeg', u'.bmp', u'.tif'}

#------------------------------------------------------------------------------
class CoSaves:
    """Handles co-files (.pluggy, .obse, .skse) for saves."""
    reSave = None

    @staticmethod
    def getPaths(savePath):
        """Returns cofile paths."""
        if CoSaves.reSave is None:
            CoSaves.reSave = re.compile(re.escape(bush.game.ess.ext) + '(f?)$',
                                        re.I | re.U)
        maSave = CoSaves.reSave.search(savePath.s)
        if maSave: savePath = savePath.root
        first = maSave and maSave.group(1) or u''
        return tuple(savePath + ext + first for ext in
                     (u'.pluggy', u'.' + bush.game.se.shortName.lower()))

    def __init__(self,savePath,saveName=None):
        """Initialize with savePath."""
        if saveName: savePath = savePath.join(saveName)
        self.savePath = savePath
        self.paths = CoSaves.getPaths(savePath)

    def _recopy(self, savePath, saveName, pathFunc):
        """Renames/copies cofiles depending on supplied pathFunc."""
        if saveName: savePath = savePath.join(saveName)
        newPaths = CoSaves.getPaths(savePath)
        for oldPath,newPath in zip(self.paths,newPaths):
            if newPath.exists(): newPath.remove() ##: dont like it, investigate
            if oldPath.exists(): pathFunc(oldPath,newPath)

    def copy(self,savePath,saveName=None):
        """Copies cofiles."""
        self._recopy(savePath, saveName, bolt.Path.copyTo)

    def move(self,savePath,saveName=None):
        """Renames cofiles."""
        self._recopy(savePath, saveName, bolt.Path.moveTo)

    @staticmethod
    def get_new_paths(old_path, new_path):
        return zip(CoSaves.getPaths(old_path), CoSaves.getPaths(new_path))

# File System -----------------------------------------------------------------
#------------------------------------------------------------------------------
class BsaFile:
    """Represents a BSA archive file."""

    @staticmethod
    def getHash(fileName):
        """Returns tes4's two hash values for filename.
        Based on Timeslips code with cleanup and pythonization."""
        #--NOTE: fileName is NOT a Path object!
        root,ext = os.path.splitext(fileName.lower())
        #--Hash1
        chars = map(ord,root)
        hash1 = chars[-1] | ((len(chars)>2 and chars[-2]) or 0)<<8 | len(chars)<<16 | chars[0]<<24
        if   ext == u'.kf':  hash1 |= 0x80
        elif ext == u'.nif': hash1 |= 0x8000
        elif ext == u'.dds': hash1 |= 0x8080
        elif ext == u'.wav': hash1 |= 0x80000000
        #--Hash2
        uintMask, hash2, hash3 = 0xFFFFFFFF, 0, 0
        for char in chars[1:-2]:
            hash2 = ((hash2 * 0x1003F) + char ) & uintMask
        for char in map(ord,ext):
            hash3 = ((hash3 * 0x1003F) + char ) & uintMask
        hash2 = (hash2 + hash3) & uintMask
        #--Done
        return (hash2<<32) + hash1

    #--Instance Methods ------------------------------------------------------
    def __init__(self,path):
        self.path = path
        self.folderInfos = None

    def scan(self):
        """Reports on contents."""
        with open(self.path.s,'rb') as ins:
            #--Header
            ins.seek(4*4)
            (self.folderCount,self.fileCount,lenFolderNames,lenFileNames,fileFlags) = unpack_many(ins, '5I')
            #--FolderInfos (Initial)
            folderInfos = self.folderInfos = []
            for index in range(self.folderCount):
                hash,subFileCount,offset = unpack_many(ins, 'Q2I')
                folderInfos.append([hash,subFileCount,offset])
            #--Update folderInfos
            for index,folderInfo in enumerate(folderInfos):
                fileInfos = []
                folderName = cstrip(ins.read(unpack_byte(ins)))
                folderInfos[index].extend((folderName,fileInfos))
                for index in range(folderInfo[1]):
                    filePos = ins.tell()
                    hash,size,offset = unpack_many(ins, 'Q2I')
                    fileInfos.append([hash,size,offset,u'',filePos])
            #--File Names
            fileNames = [decode(x) for x in ins.read(lenFileNames).split('\x00')[:-1]]
            namesIter = iter(fileNames)
            for folderInfo in folderInfos:
                fileInfos = folderInfo[-1]
                for index,fileInfo in enumerate(fileInfos):
                    fileInfo[3] = namesIter.next()
        #--Done

    def report(self,printAll=False):
        """Report on contents."""
        folderInfos = self.folderInfos
        getHash = BsaFile.getHash
        print self.folderCount,self.fileCount,sum(len(info[-1]) for info in folderInfos)
        for folderInfo in folderInfos:
            printOnce = folderInfo[-2]
            for fileInfo in folderInfo[-1]:
                hash,fileName = fileInfo[0],fileInfo[3]
                trueHash = getHash(fileName)

    @staticmethod
    def updateAIText(files=None):
        """Update aiText with specified files (or remove, if files == None)."""
        aiPath = dirs['app'].join(u'ArchiveInvalidation.txt')
        if not files:
            aiPath.remove()
            return
        #--Archive invalidation
        aiText = re.sub(ur'\\',u'/',u'\n'.join(files))
        with aiPath.open('w') as f:
            f.write(aiText)

    @staticmethod
    def resetOblivionBSAMTimes():
        """Reset dates of bsa files to 'correct' values."""
        #--Fix the data of a few archive files
        bsaTimes = (
            (u'Oblivion - Meshes.bsa',1138575220),
            (u'Oblivion - Misc.bsa',1139433736),
            (u'Oblivion - Sounds.bsa',1138660560),
            (inisettings['OblivionTexturesBSAName'].stail, 1138162634),
            (u'Oblivion - Voices1.bsa',1138162934),
            (u'Oblivion - Voices2.bsa',1138166742),
            )
        for bsaFile,mtime in bsaTimes:
            dirs['mods'].join(bsaFile).mtime = mtime

    def reset(self):
        """Resets BSA archive hashes to correct values."""
        with open(self.path.s,'r+b') as ios:
            #--Rehash
            resetCount = 0
            folderInfos = self.folderInfos
            getHash = BsaFile.getHash
            for folderInfo in folderInfos:
                for fileInfo in folderInfo[-1]:
                    hash,size,offset,fileName,filePos = fileInfo
                    trueHash = getHash(fileName)
                    if hash != trueHash:
                        #print ' ',fileName,'\t',hex(hash-trueHash),hex(hash),hex(trueHash)
                        ios.seek(filePos)
                        ios.write(struct_pack('Q',trueHash))
                        resetCount += 1
        #--Done
        self.resetOblivionBSAMTimes()
        self.updateAIText()
        return resetCount

#------------------------------------------------------------------------------
class AFile(object):
    """Abstract file, supports caching - alpha."""
    _null_stat = (-1, None)

    def _stat_tuple(self): return self.abs_path.size_mtime()

    def __init__(self, fullpath, load_cache=False):
        self._abs_path = GPath(fullpath)
        #Set cache info (mtime, size[, ctime]) and reload if load_cache is True
        try:
            self._reset_cache(self._stat_tuple(), load_cache)
        except OSError:
            self._reset_cache(self._null_stat, load_cache=False)

    @property
    def abs_path(self): return self._abs_path

    @abs_path.setter
    def abs_path(self, val): self._abs_path = val

    def do_update(self):
        """Check cache, reset it if needed. Return True if reset else False."""
        try:
            stat_tuple = self._stat_tuple()
        except OSError:
            self._reset_cache(self._null_stat, load_cache=False)
            return False # we should not call do_update on deleted files
        if self._file_changed(stat_tuple):
            self._reset_cache(stat_tuple, load_cache=True)
            return True
        return False

    def _file_changed(self, stat_tuple):
        return (self._file_size, self._file_mod_time) != stat_tuple

    def _reset_cache(self, stat_tuple, load_cache):
        """Reset cache flags (size, mtime,...) and possibly reload the cache.
        :param load_cache: if True either load the cache (header in Mod and
        SaveInfo) or reset it so it gets reloaded later
        """
        self._file_size, self._file_mod_time = stat_tuple

    def __repr__(self): return self.__class__.__name__ + u"<" + repr(
        self.abs_path.stail) + u">"

#------------------------------------------------------------------------------
class MasterInfo:

    def _init_master_info(self):
        if self.modInfo:
            self.mtime = self.modInfo.mtime
            self.masterNames = self.modInfo.masterNames
        else:
            self.mtime = 0
            self.masterNames = tuple()

    def __init__(self, name):
        self.oldName = self.name = GPath(name)
        self.modInfo = modInfos.get(self.name,None)
        self.isGhost = self.modInfo and self.modInfo.isGhost
        self._init_master_info()

    def setName(self,name):
        self.name = GPath(name)
        self.modInfo = modInfos.get(self.name,None)
        self._init_master_info()

    def hasChanged(self):
        return self.name != self.oldName

    def isEsm(self):
        if self.modInfo:
            return self.modInfo.isEsm()
        else:
            return self.name.cext == u'.esm'

    def is_esml(self):
        if self.modInfo:
            return self.modInfo.is_esml()
        else:
            return self.name.cext == u'.esm' or self.name.cext == u'.esl'

    def hasTimeConflict(self):
        """True if has an mtime conflict with another mod."""
        if self.modInfo:
            return self.modInfo.hasTimeConflict()
        else:
            return False

    def hasActiveTimeConflict(self):
        """True if has an active mtime conflict with another mod."""
        if self.modInfo:
            return self.modInfo.hasActiveTimeConflict()
        else:
            return False

    def getBashTags(self):
        """Retrieve bash tags for master info if it's present in Data."""
        if self.modInfo:
            return self.modInfo.getBashTags()
        else:
            return set()

    def getStatus(self):
        if not self.modInfo:
            return 30
        else:
            return 0

    def __repr__(self):
        return self.__class__.__name__ + u"<" + repr(self.name) + u">"

#------------------------------------------------------------------------------
class FileInfo(AFile):
    """Abstract Mod, Save or BSA File. Features a half baked Backup API."""
    _null_stat = (-1, None, None)

    def _stat_tuple(self): return self.abs_path.size_mtime_ctime()

    def __init__(self, fullpath, load_cache=False):
        g_path = GPath(fullpath)
        self.dir = g_path.head
        self.name = g_path.tail # ghost must be lopped off
        self.header = None
        self.masterNames = tuple()
        self.masterOrder = tuple()
        self.madeBackup = False
        #--Ancillary storage
        self.extras = {}
        super(FileInfo, self).__init__(g_path, load_cache)

    def _reset_masters(self):
        #--Master Names/Order
        self.masterNames = tuple(self.header.masters)
        self.masterOrder = tuple() #--Reset to empty for now

    def _file_changed(self, stat_tuple):
        return (self._file_size, self._file_mod_time, self.ctime) != stat_tuple

    def _reset_cache(self, stat_tuple, load_cache):
        self._file_size, self._file_mod_time, self.ctime = stat_tuple
        if load_cache: self.readHeader()

    def mark_unchanged(self):
        self._reset_cache(self._stat_tuple(), load_cache=False)

    ##: DEPRECATED-------------------------------------------------------------
    def getPath(self): return self.abs_path
    @property
    def mtime(self): return self._file_mod_time
    @property
    def size(self): return self._file_size
    #--------------------------------------------------------------------------
    #--File type tests ##: Belong to ModInfo!
    #--Note that these tests only test extension, not the file data.
    def isMod(self):
        return ModInfos.rightFileType(self.name)

    def setmtime(self, set_time=0, crc_changed=False):
        """Sets mtime. Defaults to current value (i.e. reset)."""
        set_time = int(set_time or self.mtime)
        self.abs_path.mtime = set_time
        self._file_mod_time = set_time
        return set_time

    def readHeader(self):
        """Read header from file and set self.header attribute."""
        pass

    def getStatus(self):
        """Returns status of this file -- which depends on status of masters.
        0:  Good
        20, 22: Out of order master
        21, 22: Loads after its masters
        30: Missing master(s)."""
        #--Worst status from masters
        status = 30 if any( # if self.masterNames is empty returns False
            (m not in modInfos) for m in self.masterNames) else 0
        #--Missing files?
        if status == 30:
            return status
        #--Misordered?
        self.masterOrder = tuple(load_order.get_ordered(self.masterNames))
        loads_before_its_masters = self.isMod() and self.masterOrder and \
                                   load_order.cached_lo_index(
            self.masterOrder[-1]) > load_order.cached_lo_index(self.name)
        if self.masterOrder != self.masterNames and loads_before_its_masters:
            return 22
        elif loads_before_its_masters:
            return 21
        elif self.masterOrder != self.masterNames:
            return 20
        else:
            return status

    # Backup stuff - beta, see #292 -------------------------------------------
    def getFileInfos(self):
        """Return one of the FileInfos singletons depending on fileInfo type.
        :rtype: FileInfos"""
        raise AbstractError

    def _doBackup(self,backupDir,forceBackup=False):
        """Creates backup(s) of file, places in backupDir."""
        #--Skip backup?
        if not self in self.getFileInfos().values(): return
        if self.madeBackup and not forceBackup: return
        #--Backup
        self.getFileInfos().copy_info(self.name, backupDir)
        #--First backup
        firstBackup = backupDir.join(self.name) + u'f'
        if not firstBackup.exists():
            self.getFileInfos().copy_info(self.name, backupDir,
                                          firstBackup.tail)

    def tempBackup(self, forceBackup=True):
        """Creates backup(s) of file.  Uses temporary directory to avoid UAC issues."""
        self._doBackup(Path.baseTempDir().join(u'WryeBash_temp_backup'),forceBackup)

    def makeBackup(self, forceBackup=False):
        """Creates backup(s) of file."""
        backupDir = self.backup_dir
        self._doBackup(backupDir,forceBackup)
        #--Done
        self.madeBackup = True

    def backup_paths(self, first=False):
        """Return a list of tuples with backup paths and their restore
        destinations
        :rtype: list[tuple]""" ##: drop tuples use lists !
        return [(self.backup_dir.join(self.name) + (u'f' if first else u''),
                 self.getPath())]

    def revert_backup(self, first=False):
        backup_paths = self.backup_paths(first)
        for tup in backup_paths[1:]: # if cosaves do not exist shellMove fails!
            if not tup[0].exists(): backup_paths.remove(tup)
        env.shellCopy(*zip(*backup_paths))
        # do not change load order for timestamp games - rest works ok
        self.setmtime(self._file_mod_time, crc_changed=True)
        self.getFileInfos().new_info(self.name, notify_bain=True)

    def getNextSnapshot(self):
        """Returns parameters for next snapshot."""
        destDir = self.snapshot_dir
        destDir.makedirs()
        (root,ext) = self.name.root, self.name.ext
        separator = u'-'
        snapLast = [u'00']
        #--Look for old snapshots.
        reSnap = re.compile(u'^'+root.s+u'[ -]([0-9.]*[0-9]+)'+ext+u'$',re.U)
        for fileName in destDir.list():
            maSnap = reSnap.match(fileName.s)
            if not maSnap: continue
            snapNew = maSnap.group(1).split(u'.')
            #--Compare shared version numbers
            sharedNums = min(len(snapNew),len(snapLast))
            for index in range(sharedNums):
                (numNew,numLast) = (int(snapNew[index]),int(snapLast[index]))
                if numNew > numLast:
                    snapLast = snapNew
                    continue
            #--Compare length of numbers
            if len(snapNew) > len(snapLast):
                snapLast = snapNew
                continue
        #--New
        snapLast[-1] = (u'%0'+unicode(len(snapLast[-1]))+u'd') % (int(snapLast[-1])+1,)
        destName = root+separator+(u'.'.join(snapLast))+ext
        return destDir,destName,(root+u'*'+ext).s

    @property
    def backup_dir(self):
        return self.getFileInfos().bash_dir.join(u'Backups')

    @property
    def snapshot_dir(self):
        return self.getFileInfos().bash_dir.join(u'Snapshots')

#------------------------------------------------------------------------------
reBashTags = re.compile(ur'{{ *BASH *:[^}]*}}\s*\n?',re.U)

class ModInfo(FileInfo):
    """An esp/m/l file."""

    def __init__(self, fullpath, load_cache=False):
        self.isGhost = endsInGhost = (fullpath.cs[-6:] == u'.ghost')
        if endsInGhost: fullpath = GPath(fullpath.s[:-6])
        else: # new_info() path
            self.isGhost = \
                not fullpath.exists() and (fullpath + u'.ghost').exists()
        super(ModInfo, self).__init__(fullpath, load_cache)

    def _reset_cache(self, stat_tuple, load_cache):
        super(ModInfo, self)._reset_cache(stat_tuple, load_cache)
        # check if we have a cached crc for this file, use fresh mtime and size
        if load_cache: self.calculate_crc() # for added and hopefully updated

    def getFileInfos(self): return modInfos

    def isEsm(self):
        """Check if the mod info is a master file based on master flag -
        header must be set"""
        return int(self.header.flags1) & 1 == 1

    def is_esl(self):
        # game seems not to care about the flag, at least for load order
        return self.name.cext == u'.esl'

    def is_esml(self):
        return self.is_esl() or self.isEsm()

    def isInvertedMod(self):
        """Extension indicates esp/esm, but byte setting indicates opposite."""
        if self.name.cext not in (u'.esm', u'.esp'): # don't use for esls
            raise ArgumentError(
                u'isInvertedMod: %s - only esm/esp allowed' % self.name.ext)
        return (self.header and
            self.name.cext != (u'.esp', u'.esm')[int(self.header.flags1) & 1])

    def setType(self, esm_or_esp):
        """Sets the file's internal type."""
        if esm_or_esp not in (u'esm', u'esp'): # don't use for esls
            raise ArgumentError(
                u'setType: %s - only esm/esp allowed' % esm_or_esp)
        with self.getPath().open('r+b') as modFile:
            modFile.seek(8)
            flags1 = MreRecord.flags1_(struct_unpack('I', modFile.read(4))[0])
            flags1.esm = (esm_or_esp == u'esm')
            modFile.seek(8)
            modFile.write(struct_pack('=I', int(flags1)))
        self.header.flags1 = flags1
        self.setmtime(crc_changed=True)

    def calculate_crc(self, recalculate=False):
        cached_crc = modInfos.table.getItem(self.name, 'crc')
        if not recalculate:
            cached_mtime = modInfos.table.getItem(self.name, 'crc_mtime')
            cached_size = modInfos.table.getItem(self.name, 'crc_size')
            recalculate = cached_crc is None \
                          or self._file_mod_time != cached_mtime \
                          or self._file_size != cached_size
        path_crc = cached_crc
        if recalculate:
            path_crc = self.abs_path.crc
            if path_crc != cached_crc:
                modInfos.table.setItem(self.name,'crc',path_crc)
                modInfos.table.setItem(self.name,'ignoreDirty',False)
            modInfos.table.setItem(self.name, 'crc_mtime', self._file_mod_time)
            modInfos.table.setItem(self.name, 'crc_size', self._file_size)
        return path_crc, cached_crc

    def cached_mod_crc(self): # be sure it's valid before using it!
        return modInfos.table.getItem(self.name, 'crc')

    def crc_string(self):
        try:
            return u'%08X' % modInfos.table.getItem(self.name, 'crc')
        except TypeError: # None, should not happen so let it show
            return u'UNKNOWN!'

    def setmtime(self, set_time=0, crc_changed=False):
        """Set mtime and if crc_changed is True recalculate the crc."""
        set_time = FileInfo.setmtime(self, set_time)
        # Prevent re-calculating the File CRC
        if not crc_changed:
            modInfos.table.setItem(self.name,'crc_mtime', set_time)
        else:
            self.calculate_crc(recalculate=True)

    # Ghosting and ghosting related overrides ---------------------------------
    def do_update(self):
        self.isGhost, old_ghost = not self._abs_path.exists() and (
            self._abs_path + u'.ghost').exists(), self.isGhost
        # mark updated if ghost state changed but only reread header if needed
        changed = super(ModInfo, self).do_update()
        return changed or self.isGhost != old_ghost

    @FileInfo.abs_path.getter
    def abs_path(self):
        """Return joined dir and name, adding .ghost if the file is ghosted."""
        return (self._abs_path + u'.ghost') if self.isGhost else self._abs_path

    def setGhost(self,isGhost):
        """Sets file to/from ghost mode. Returns ghost status at end."""
        normal = self.dir.join(self.name)
        ghost = normal + u'.ghost'
        # Refresh current status - it may have changed due to things like
        # libloadorder automatically unghosting plugins when activating them.
        # Libloadorder only un-ghosts automatically, so if both the normal
        # and ghosted version exist, treat the normal as the real one.
        # Both should never exist simultaneously, Bash will warn in BashBugDump
        if normal.exists(): self.isGhost = False
        elif ghost.exists(): self.isGhost = True
        # Current status == what we want it?
        if isGhost == self.isGhost: return isGhost
        # Current status != what we want, so change it
        try:
            if not normal.editable() or not ghost.editable():
                return self.isGhost
            if isGhost: normal.moveTo(ghost)
            else: ghost.moveTo(normal)
            self.isGhost = isGhost
            # reset cache info as un/ghosting should not make do_update return True
            self.mark_unchanged()
        except:
            deprint(u'Failed to %sghost file %s' % ((u'un', u'')[isGhost],
                (ghost.s, normal.s)[isGhost]), traceback=True)
        return self.isGhost

    #--Bash Tags --------------------------------------------------------------
    def setBashTags(self,keys):
        """Sets bash keys as specified."""
        modInfos.table.setItem(self.name,'bashTags',keys)

    def setBashTagsDesc(self,keys):
        """Sets bash keys as specified."""
        keys = set(keys) #--Make sure it's a set.
        if keys == self.getBashTagsDesc(): return
        if keys:
            strKeys = u'{{BASH:'+(u','.join(sorted(keys)))+u'}}\n'
        else:
            strKeys = u''
        description = self.header.description or ''
        if reBashTags.search(description):
            description = reBashTags.sub(strKeys,description)
        else:
            description = description + u'\n' + strKeys
        if len(description) > 511: return False
        self.writeDescription(description)
        return True

    def getBashTags(self):
        """Returns any Bash flag keys."""
        return modInfos.table.getItem(self.name, 'bashTags', set())

    def getBashTagsDesc(self):
        """Returns any Bash flag keys."""
        description = self.header.description or u''
        maBashKeys = re.search(u'{{ *BASH *:([^}]+)}}',description,flags=re.U)
        if not maBashKeys:
            return set()
        else:
            bashTags = maBashKeys.group(1).split(u',')
            return set([tag.strip() for tag in
                        bashTags]) & bush.game.allTags - oldTagsSet

    def reloadBashTags(self):
        """Reloads bash tags from mod description and LOOT"""
        tags, removed, _userlist = configHelpers.getTagsInfoCache(self.name)
        tags |= self.getBashTagsDesc()
        tags -= removed
        # Filter and remove old tags
        tags &= bush.game.allTags
        if tags & oldTagsSet:
            tags -= oldTagsSet
            self.setBashTagsDesc(tags)
        self.setBashTags(tags)

    #--Header Editing ---------------------------------------------------------
    def _read_tes4_header(self, ins):
        tes4_rec_header = ins.unpackRecHeader()
        if tes4_rec_header.recType != bush.game_mod.MreHeader.classType:
            raise ModError(self.name, u'Expected %s, but got %s' % (
                bush.game_mod.MreHeader.classType, tes4_rec_header.recType))
        return tes4_rec_header

    def readHeader(self):
        """Read header from file and set self.header attribute."""
        with ModReader(self.name,self.getPath().open('rb')) as ins:
            try:
                tes4_rec_header = self._read_tes4_header(ins)
                self.header = bush.game_mod.MreHeader(tes4_rec_header,ins,True)
            except struct.error as rex:
                raise ModError(self.name,u'Struct.error: %s' % rex)
        if bush.game.fsName == u'Skyrim Special Edition':
            if tes4_rec_header.form_version != ModReader.recHeader.plugin_form_version:
                modInfos.sse_form43.add(self.name)
        self._reset_masters()

    def writeHeader(self):
        """Write Header. Actually have to rewrite entire file."""
        filePath = self.getPath()
        with filePath.open('rb') as ins:
            with filePath.temp.open('wb') as out:
                try:
                    #--Open original and skip over header
                    reader = ModReader(self.name,ins)
                    tes4_rec_header = self._read_tes4_header(reader)
                    reader.seek(tes4_rec_header.size,1)
                    #--Write new header
                    self.header.getSize()
                    self.header.dump(out)
                    #--Write remainder
                    outWrite = out.write
                    for block in iter(partial(ins.read, 0x5000000), ''):
                        outWrite(block)
                except struct.error as rex:
                    raise ModError(self.name,u'Struct.error: %s' % rex)
        #--Remove original and replace with temp
        filePath.untemp()
        self.setmtime(crc_changed=True)
        #--Merge info
        size,canMerge = modInfos.table.getItem(self.name,'mergeInfo',(None,None))
        if size is not None:
            modInfos.table.setItem(self.name,'mergeInfo',(filePath.size,canMerge))

    def writeDescription(self,description):
        """Sets description to specified text and then writes hedr."""
        description = description[:min(511,len(description))] # 511 + 1 for null = 512
        self.header.description = description
        self.header.setChanged()
        self.writeHeader()

    #--Helpers ----------------------------------------------------------------
    def isBP(self, __bp_authors={u'BASHED PATCH', u'BASHED LISTS'}):
        return self.header.author in __bp_authors ##: drop BASHED LISTS

    def txt_status(self):
        if load_order.cached_is_active(self.name): return _(u'Active')
        elif self.name in modInfos.merged: return _(u'Merged')
        elif self.name in modInfos.imported: return _(u'Imported')
        else: return _(u'Non-Active')

    def hasTimeConflict(self):
        """True if there is another mod with the same mtime."""
        return load_order.has_load_order_conflict(self.name)

    def hasActiveTimeConflict(self):
        """True if has an active mtime conflict with another mod."""
        return load_order.has_load_order_conflict_active(self.name)

    def hasBadMasterNames(self):
        """True if has a master with un unencodable name in cp1252."""
        try:
            for x in self.header.masters: x.s.encode('cp1252')
            return False
        except UnicodeEncodeError:
            return True

    @property
    def _modname(self):
        return modInfos.file_pattern.sub(u'', self.name.s)

    def mod_bsas(self, bsa_infos=None):
        """Return bsas from bsaInfos, that match plugin's name."""
        pattern = re.escape(self._modname)
        # games other than skyrim accept more general bsa names
        if bush.game.fsName != u'Skyrim': pattern +=  u'.*'
        reg = re.compile(pattern, re.I | re.U)
        # bsaInfos must be updated and contain all existing bsas
        if bsa_infos is None: bsa_infos = bsaInfos
        return [inf for bsa, inf in bsa_infos.iteritems() if reg.match(bsa.s)]

    def hasBsa(self):
        """Returns True if plugin has an associated BSA."""
        return bool(self.mod_bsas())

    def getIniPath(self):
        """Returns path to plugin's INI, if it were to exists."""
        return self.getPath().root.root + u'.ini' # chops off ghost if ghosted

    def _string_files_paths(self, lang):
        sbody, ext = self.name.sbody, self.name.ext
        for join, format_str in bush.game.esp.stringsFiles:
            fname = format_str % {'body': sbody, 'ext': ext, 'language': lang}
            assetPath = empty_path.join(*join).join(fname)
            yield assetPath

    def getStringsPaths(self, lang=u'English'):
        """If Strings Files are available as loose files, just point to
        those, otherwise extract needed files from BSA if needed."""
        baseDirJoin = self.getPath().head.join
        extract = set()
        paths = set()
        #--Check for Loose Files first
        for filepath in self._string_files_paths(lang):
            loose = baseDirJoin(filepath)
            if not loose.exists():
                extract.add(filepath)
            else:
                paths.add(loose)
        #--If there were some missing Loose Files
        if extract:
            bsa_assets = OrderedDict()
            for bsa_info in self._extra_bsas():
                try:
                    found_assets = bsa_info.has_assets(extract)
                except (BSAError, OverflowError):
                    deprint(u'Failed to parse %s' % bsa_info.name,
                            traceback=True)
                    continue
                if not found_assets: continue
                bsa_assets[bsa_info] = found_assets
                #extract contains Paths that compare equal to lowercase strings
                extract -= set(imap(unicode.lower, found_assets))
                if not extract:
                    break
            else: raise ModError(self.name, u"Could not locate Strings Files")
            for bsa, assets in bsa_assets.iteritems():
                out_path = dirs['bsaCache'].join(bsa.name)
                try:
                    bsa.extract_assets(assets, out_path.s)
                except BSAError as e:
                    raise ModError(self.name,
                                   u"Could not extract Strings File from "
                                   u"'%s': %s" % (bsa.name, e))
                paths.update(imap(out_path.join, assets))
        return paths

    def _extra_bsas(self):
        """Return a list of bsas to get assets from.
        :rtype: list[BSAInfo]
        """
        if self.name.cs in bush.game.vanilla_string_bsas: # lowercase !
            bsa_infos = [bsaInfos[b] for b in map(GPath,
                bush.game.vanilla_string_bsas[self.name.cs]) if b in bsaInfos]
        else:
            bsa_infos = self.mod_bsas() # first check bsa with same name
            for iniFile in modInfos.ini_files():
                for key in bush.game.resource_archives_keys:
                    extraBsas = map(GPath, (x.strip() for x in (
                        iniFile.getSetting(u'Archive', key, u'').split(u','))))
                    bsa_infos.extend(
                        bsaInfos[bsa] for bsa in extraBsas if bsa in bsaInfos)
        return bsa_infos

    def isMissingStrings(self, __debug=0):
        """True if the mod says it has .STRINGS files, but the files are
        missing."""
        if not self.header.flags1.hasStrings: return False
        lang = oblivionIni.get_ini_language()
        bsa_infos = self._extra_bsas()
        for assetPath in self._string_files_paths(lang):
            # Check loose files first
            if self.dir.join(assetPath).exists():
                continue
            # Check in BSA's next
            if __debug == 1:
                deprint(u'Scanning BSAs for string files for %s' % self.name)
                __debug = 2
            for bsa_info in bsa_infos:
                try:
                    if bsa_info.has_assets({assetPath}):
                        break # found
                except (BSAError, OverflowError):
                    print u'Failed to parse %s:\n%s' % (
                        bsa_info.name, traceback.format_exc())
                    continue
                if __debug == 2:
                    deprint(u'Asset %s not in %s' % (assetPath, bsa_info.name))
            else: # not found
                return True
        return False

    def hasResources(self):
        """Returns (hasBsa,hasVoices) booleans according to presence of
        corresponding resources."""
        voicesPath = self.dir.join(u'Sound',u'Voice',self.name)
        return [self.hasBsa(),voicesPath.exists()]

#------------------------------------------------------------------------------
from .ini_files import IniFile, OBSEIniFile, DefaultIniFile, OblivionIni
def get_game_ini(ini_path, is_abs=True):
    """:rtype: OblivionIni | None"""
    for game_ini in gameInis:
        game_ini_path = game_ini.abs_path
        if ini_path == ((is_abs and game_ini_path) or game_ini_path.stail):
            return game_ini
    return None

def BestIniFile(abs_ini_path):
    """:rtype: IniFile"""
    game_ini = get_game_ini(abs_ini_path)
    if game_ini:
        return game_ini
    INICount = IniFile.formatMatch(abs_ini_path)
    OBSECount = OBSEIniFile.formatMatch(abs_ini_path)
    if INICount >= OBSECount:
        return IniFile(abs_ini_path)
    else:
        return OBSEIniFile(abs_ini_path)

#------------------------------------------------------------------------------
class INIInfo(IniFile):
    """Ini info, adding cached status and functionality to the ini files."""
    _status = None

    def _reset_cache(self, stat_tuple, load_cache):
        super(INIInfo, self)._reset_cache(stat_tuple, load_cache)
        if load_cache: self._status = None

    @property
    def tweak_status(self):
        if self._status is None: self.getStatus()
        return self._status

    @property
    def is_default_tweak(self): return False

    def _incompatible(self, other):
        if not isinstance(self, OBSEIniFile):
            return isinstance(other, OBSEIniFile)
        return not isinstance(other, OBSEIniFile)

    def is_applicable(self, stat=None):
        stat = stat or self.tweak_status
        return stat != -20 and (
            bass.settings['bash.ini.allowNewLines'] or stat != -10)

    def getStatus(self, target_ini=None):
        """Returns status of the ini tweak:
        20: installed (green with check)
        15: mismatches (green with dot) - mismatches are with another tweak from same installer that is applied
        10: mismatches (yellow)
        0: not installed (green)
        -10: tweak file contains new sections/settings
        -20: incompatible tweak file (red)
        Also caches the value in self._status"""
        infos = iniInfos
        target_ini = target_ini or infos.ini
        tweak_settings = self.get_ci_settings()
        def _status(s):
            self._status = s
            return s
        if self._incompatible(target_ini) or not tweak_settings:
            return _status(-20)
        match = False
        mismatch = 0
        ini_settings = target_ini.get_ci_settings()
        self_installer = infos.table.getItem(self.abs_path.tail, 'installer')
        for section_key in tweak_settings:
            if section_key not in ini_settings:
                return _status(-10)
            target_section = ini_settings[section_key]
            tweak_section = tweak_settings[section_key]
            for item in tweak_section:
                if item not in target_section:
                    return _status(-10)
                if tweak_section[item][0] != target_section[item][0]:
                    if mismatch < 2:
                        # Check to see if the mismatch is from another ini
                        # tweak that is applied, and from the same installer
                        mismatch = 2
                        if self_installer is None: continue
                        for name, ini_info in infos.iteritems():
                            if self is ini_info: continue
                            if self_installer != infos.table.getItem(
                                    name, 'installer'): continue
                            # It's from the same installer
                            if self._incompatible(ini_info): continue
                            value = ini_info.getSetting(section_key, item, None)
                            if value == target_section[item][0]:
                                # The other tweak has the setting we're worried about
                                mismatch = 1
                                break
                else:
                    match = True
        if not match:
            return _status(0)
        elif not mismatch:
            return _status(20)
        elif mismatch == 1:
            return _status(15)
        elif mismatch == 2:
            return _status(10)

    def reset_status(self): self._status = None

    def listErrors(self):
        """Returns ini tweak errors as text."""
        ini_infos_ini = iniInfos.ini
        errors = [u'%s:' % self.abs_path.stail]
        if self._incompatible(ini_infos_ini):
            errors.append(u' ' + _(u'Format mismatch:'))
            if isinstance(self, OBSEIniFile):
                errors.append(u'  '+ _(u'Target format: INI') +
                            u'\n  ' + _(u'Tweak format: Batch Script'))
            else:
                errors.append(u'  ' + _(u'Target format: Batch Script') +
                            u'\n  ' + _(u'Tweak format: INI'))
        else:
            tweak_settings = self.get_ci_settings()
            ini_settings = ini_infos_ini.get_ci_settings()
            if len(tweak_settings) == 0:
                if not isinstance(self, OBSEIniFile):
                    errors.append(_(u' No valid INI format lines.'))
                else:
                    errors.append(_(u' No valid Batch Script format lines.'))
            else:
                missing_settings = []
                for key in tweak_settings:
                    if key not in ini_settings:
                        errors.append(u' [%s] - %s' % (key,_(u'Invalid Header')))
                    else:
                        for item in tweak_settings[key]:
                            if item not in ini_settings[key]:
                                missing_settings.append(
                                    u'  [%s] %s' % (key, item))
                if missing_settings:
                    errors.append(u' ' + _(u'Settings missing from target ini:'))
                    errors.extend(missing_settings)
        if len(errors) == 1:
            errors.append(u' None')
        with sio() as out:
            log = bolt.LogFile(out)
            for line in errors:
                log(line)
            return bolt.winNewLines(log.out.getvalue())

#------------------------------------------------------------------------------
from .save_headers import get_save_header_type, SaveFileHeader
from ._saves import PluggyFile
from . import cosaves

class SaveInfo(FileInfo):
    _cosave_type = None  # type: cosaves.ACoSaveFile

    @property
    def cosave_type(self):
        if self._cosave_type is None:
            SaveInfo._cosave_type = cosaves.get_cosave_type(bush.game.fsName)
        return self._cosave_type

    def getFileInfos(self): return saveInfos

    def getStatus(self):
        status = FileInfo.getStatus(self)
        masterOrder = self.masterOrder
        #--File size?
        if status > 0 or len(masterOrder) > len(load_order.cached_active_tuple()):
            return status
        #--Current ordering?
        if masterOrder != load_order.cached_active_tuple()[:len(masterOrder)]:
            return status
        elif masterOrder == load_order.cached_active_tuple():
            return -20
        else:
            return -10

    def readHeader(self):
        """Read header from file and set self.header attribute."""
        try:
            self.header = get_save_header_type(bush.game.fsName)(self.abs_path)
        except SaveHeaderError as e:
            raise SaveFileError, (self.name, e.message), sys.exc_info()[2]
        self._reset_masters()

    def write_masters(self):
        """Rewrites masters of existing save file."""
        if not self.abs_path.exists():
            raise SaveFileError(self.abs_path.head, u'File does not exist.')
        with self.abs_path.open('rb') as ins:
            with self.abs_path.temp.open('wb') as out:
                oldMasters = self.header.writeMasters(ins, out)
        oldMasters = [GPath(decode(x)) for x in oldMasters]
        self.abs_path.untemp()
        #--Cosaves
        masterMap = dict(
            (x, y) for x, y in zip(oldMasters, self.header.masters) if x != y)
        #--Pluggy file?
        pluggyPath = CoSaves.getPaths(self.abs_path)[0]
        if masterMap and pluggyPath.exists():
            pluggy = PluggyFile(pluggyPath)
            pluggy.load()
            pluggy.mapMasters(masterMap)
            pluggy.safeSave()
        #--OBSE/SKSE file?
        cosave = self.get_cosave()
        if cosave is not None:
            cosave.map_masters(masterMap)
            cosave.write_cosave_safe()

    def get_cosave_tags(self):
        """Return strings expressing whether cosaves exist and are correct."""
        cPluggy, cObse = (u'', u'')
        pluggy = self.name.root + u'.pluggy'
        obse = self._get_se_cosave_path()
        if pluggy.exists():
            cPluggy = u'XP'[abs(pluggy.mtime - self.mtime) < 10]
        if obse and obse.exists():
            cObse = u'XO'[abs(obse.mtime - self.mtime) < 10]
        return cObse, cPluggy

    def backup_paths(self, first=False):
        save_paths = super(SaveInfo, self).backup_paths(first)
        save_paths.extend(CoSaves.get_new_paths(*save_paths[0]))
        return save_paths

    def get_cosave(self):
        """:rtype: cosaves.ACoSaveFile"""
        cosave_path = self._get_se_cosave_path()
        if cosave_path is None: return None
        try:
            return self.cosave_type(cosave_path) # type: cosaves.ACoSaveFile
        except (OSError, IOError, FileError) as e:
            if isinstance(e, FileError) or (
                isinstance(e, (OSError, IOError)) and e.errno != errno.ENOENT):
                deprint(u'Failed to open %s' % cosave_path, traceback=True)
            return None

    def _get_se_cosave_path(self):
        if self.cosave_type is None: return None
        return self.getPath().root + u'.' + self.cosave_type.signature.lower()

#------------------------------------------------------------------------------
class DataStore(DataDict):
    store_dir = empty_path # where the datas sit, static except for SaveInfos

    def delete(self, delete_keys, **kwargs):
        """Deletes member file(s)."""
        full_delete_paths, delete_info = self.files_to_delete(delete_keys,
            raise_on_master_deletion=kwargs.pop(
                'raise_on_master_deletion', True))
        try:
            self._delete_operation(full_delete_paths, delete_info, **kwargs)
        finally:
            #--Refresh
            if kwargs.pop('doRefresh', True):
                self.delete_refresh(full_delete_paths, delete_info,
                                    check_existence=True)

    def files_to_delete(self, filenames, **kwargs):
        raise AbstractError

    def _delete_operation(self, paths, delete_info, **kwargs):
        confirm = kwargs.pop('confirm', False)
        recycle = kwargs.pop('recycle', True)
        env.shellDelete(paths, confirm=confirm, recycle=recycle)

    def delete_refresh(self, deleted, deleted2, check_existence):
        raise AbstractError

    def refresh(self): raise AbstractError
    def save(self): pass # for Screenshots
    # Renaming
    def rename_info(self, oldName, newName):
        try:
            return self._rename_operation(oldName, newName)
        except (CancelError, OSError, IOError):
            deprint(u'Renaming %s to %s failed' % (oldName, newName),
                    traceback=True)
            # When using moveTo I would get "WindowsError:[Error 32]The process
            # cannot access ..." -  the code below was reverting the changes.
            # With shellMove I mostly get CancelError so below not needed -
            # except if a save is locked and user presses Skip - so cosaves are
            # renamed! Error handling is still a WIP
            for old, new in self._get_rename_paths(oldName, newName):
                if new.exists() and not old.exists():
                    # some cosave move failed, restore files
                    new.moveTo(old)
                if new.exists() and old.exists():
                    # move copies then deletes, so the delete part failed
                    new.remove()
            raise

    def _rename_operation(self, oldName, newName):
        rename_paths = self._get_rename_paths(oldName, newName)
        for tup in rename_paths[1:]: # if cosaves do not exist shellMove fails!
            if not tup[0].exists(): rename_paths.remove(tup)
        env.shellMove(*zip(*rename_paths))

    def _get_rename_paths(self, oldName, newName):
        return [tuple(map(self.store_dir.join, (oldName, newName)))]

    @property
    def bash_dir(self):
        """Return the folder where Bash persists its data - create it on init!
        :rtype: bolt.Path"""
        raise AbstractError

    @property
    def hidden_dir(self):
        """Return the folder where Bash should move the file info to hide it
        :rtype: bolt.Path"""
        return self.bash_dir.join(u'Hidden')

    def get_hide_dir(self, name): return self.hidden_dir

    def move_infos(self, sources, destinations, window, bash_frame):
        # hasty hack for Files_Unhide, must absorb move_info
        try:
            env.shellMove(sources, destinations, parent=window)
        except (CancelError, SkipError):
            pass
        return set(d.tail for d in destinations if d.exists())

class TableFileInfos(DataStore):
    _bain_notify = True # notify BAIN on deletions/updates ?
    file_pattern = None # subclasses must define this !

    def _initDB(self, dir_):
        self.store_dir = dir_ #--Path
        self.store_dir.makedirs()
        self.bash_dir.makedirs() # self.store_dir may need be set
        self.data = {} # populated in refresh ()
        # the type of the table keys is always bolt.Path
        self.table = bolt.Table(
            bolt.PickleDict(self.bash_dir.join(u'Table.dat')))

    def __init__(self, dir_, factory=AFile):
        """Init with specified directory and specified factory type."""
        self.factory=factory
        self._initDB(dir_)

    def new_info(self, fileName, _in_refresh=False, owner=None,
                 notify_bain=False):
        """Create, add to self and return a new info using self.factory.
        It will try to read the file to cache its header etc, so use on
        existing files. WIP, in particular _in_refresh must go, but that
        needs rewriting corrupted handling."""
        info = self[fileName] = self.factory(self.store_dir.join(fileName),
                                             load_cache=True)
        if owner is not None:
            self.table.setItem(fileName, 'installer', owner)
        if notify_bain:
            self._notify_bain(changed={info.abs_path})
        return info

    def _names(self): # performance intensive
        return {x for x in self.store_dir.list() if
                self.store_dir.join(x).isfile() and self.rightFileType(x)}

    #--Right File Type?
    @classmethod
    def rightFileType(cls, fileName):
        """Check if the filetype (extension) is correct for subclass.
        :type fileName: bolt.Path | basestring
        :rtype: _sre.SRE_Match | None
        """
        return cls.file_pattern.search(u'%s' % fileName)

    #--Delete
    def files_to_delete(self, fileNames, **kwargs):
        abs_delete_paths = []
        #--Cache table updates
        tableUpdate = {}
        #--Go through each file
        for fileName in fileNames:
            try:
                fileInfo = self[fileName]
            except KeyError: # corrupted
                fileInfo = self.factory(self.store_dir.join(fileName))
            #--File
            filePath = fileInfo.abs_path
            abs_delete_paths.append(filePath)
            self._additional_deletes(fileInfo, abs_delete_paths)
            #--Table
            tableUpdate[filePath] = fileName
        #--Now do actual deletions
        abs_delete_paths = set(x for x in abs_delete_paths if x.exists())
        return abs_delete_paths, tableUpdate

    def _update_deleted_paths(self, deleted_keys, paths_to_keys,
                              check_existence):
        """Must be called BEFORE we remove the keys from self."""
        if paths_to_keys is None: # we passed the keys in, get the paths
            paths_to_keys = {self[n].abs_path: n for n in deleted_keys}
        if check_existence:
            for filePath in paths_to_keys.keys():
                if filePath.exists():
                    del paths_to_keys[filePath] # item was not deleted
        self._notify_bain(deleted=paths_to_keys)
        return paths_to_keys.values()

    def _notify_bain(self, deleted=frozenset(), changed=frozenset()):
        """We need absolute paths for deleted and changed!
        :type deleted: set[bolt.Path]
        :type changed: set[bolt.Path]"""
        if self.__class__._bain_notify:
            from .bain import InstallersData
            InstallersData.notify_external(deleted=deleted, changed=changed)

    def _additional_deletes(self, fileInfo, toDelete): pass

    def save(self):
        # items deleted outside Bash
        for deleted in set(self.table.keys()) - set(self.keys()):
            del self.table[deleted]
        self.table.save()

class FileInfos(TableFileInfos):
    """Common superclass for mod, saves and bsa infos."""

    def _initDB(self, dir_):
        super(FileInfos, self)._initDB(dir_)
        self.corrupted = {} #--errorMessage = corrupted[fileName]

    #--Refresh File
    def new_info(self, fileName, _in_refresh=False, owner=None,
                 notify_bain=False):
        try:
            fileInfo = super(FileInfos, self).new_info(fileName, owner=owner,
                                                       notify_bain=notify_bain)
            self.corrupted.pop(fileName, None)
            return fileInfo
        except FileError as error:
            if not _in_refresh: # if refresh just raise so we print the error
                self.corrupted[fileName] = error.message
                self.pop(fileName, None)
            raise

    #--Refresh
    def refresh(self, refresh_infos=True, booting=False):
        """Refresh from file directory."""
        oldNames = set(self.data) | set(self.corrupted)
        _added = set()
        _updated = set()
        newNames = self._names()
        for name in newNames: #--Might have '.ghost' lopped off.
            oldInfo = self.get(name) # None if name was in corrupted or new one
            try:
                if oldInfo is not None:
                    if oldInfo.do_update(): # will reread the header
                        _updated.add(name)
                else: # added or known corrupted, get a new info
                    self.new_info(name, _in_refresh=True,
                                  notify_bain=not booting)
                    _added.add(name)
            except FileError as e: # old still corrupted, or new(ly) corrupted
                if not name in self.corrupted \
                        or self.corrupted[name] != e.message:
                    deprint(u'Failed to load %s: %s' % (name, e.message)) #, traceback=True)
                    self.corrupted[name] = e.message
                self.pop(name, None)
        _deleted = oldNames - newNames
        self.delete_refresh(_deleted, None, check_existence=False,
                            _in_refresh=True)
        if _updated:
            self._notify_bain(changed={self[n].abs_path for n in _updated})
        change = bool(_added) or bool(_updated) or bool(_deleted)
        if not change: return change
        return _added, _updated, _deleted

    def delete_refresh(self, deleted_keys, paths_to_keys, check_existence,
                       _in_refresh=False):
        """Special case for the saves, inis, mods and bsas.
        :param deleted_keys: must be the data store keys and not full paths
        :param paths_to_keys: a dict mapping full paths to the keys
        """
        #--Table
        deleted = self._update_deleted_paths(deleted_keys, paths_to_keys,
                                             check_existence)
        if not deleted: return deleted
        for name in deleted:
            self.pop(name, None); self.corrupted.pop(name, None)
            self.table.pop(name, None)
        return deleted

    def _get_rename_paths(self, oldName, newName): # FIXME(ut): rename backups
        return [(self[oldName].getPath(), self.store_dir.join(newName))]

    def _additional_deletes(self, fileInfo, toDelete):
        #--Backups
        for backPath, __path in fileInfo.backup_paths():
            toDelete.extend([backPath, backPath + u'f'])

    #--Rename
    def _rename_operation(self, oldName, newName):
        """Renames member file from oldName to newName."""
        #--Update references
        fileInfo = self[oldName]
        #--File system
        super(FileInfos, self)._rename_operation(oldName, newName)
        #--FileInfo
        fileInfo.name = newName
        fileInfo.abs_path = self.store_dir.join(newName)
        #--FileInfos
        self[newName] = self[oldName]
        del self[oldName]
        self.table.moveRow(oldName,newName)
        # self[newName].mark_unchanged() # not needed with shellMove !
        #--Done
        fileInfo.madeBackup = False ##: #292 - backups are left behind

    #--Move
    def move_info(self, fileName, destDir):
        """Moves member file to destDir. Will overwrite! The client is
        responsible for calling delete_refresh of the data store."""
        destDir.makedirs()
        srcPath = self[fileName].getPath()
        destPath = destDir.join(fileName)
        srcPath.moveTo(destPath)

    #--Copy
    def copy_info(self, fileName, destDir, destName=empty_path, set_mtime=None):
        """Copies member file to destDir. Will overwrite! Will update
        internal self.data for the file if copied inside self.dir but the
        client is responsible for calling the final refresh of the data store.
        See usages.

        :param set_mtime: if None self[fileName].mtime is copied to destination
        """
        destDir.makedirs()
        if not destName: destName = fileName
        srcPath = self[fileName].getPath()
        if destDir == self.store_dir and destName in self.data:
            destPath = self[destName].getPath()
        else:
            destPath = destDir.join(destName)
        srcPath.copyTo(destPath) # will set destPath.mtime to the srcPath one
        if destDir == self.store_dir:
            # TODO(ut) : pass the info in and load_cache=False
            self.new_info(destName, notify_bain=True)
            self.table.copyRow(fileName, destName)
            if set_mtime is not None:
                if set_mtime == '+1':
                    set_mtime = srcPath.mtime + 1
                self[destName].setmtime(set_mtime) # correctly update table
        return set_mtime

#------------------------------------------------------------------------------
class ObseIniInfo(OBSEIniFile, INIInfo): pass

class DefaultIniInfo(DefaultIniFile, INIInfo):

    @property
    def is_default_tweak(self): return True

# noinspection PyUnusedLocal
def ini_info_factory(fullpath, load_cache='Ignored'):
    """INIInfos factory
    :param fullpath: fullpath to the ini file to wrap
    :param load_cache: dummy param used in INIInfos#new_info factory call
    :rtype: INIInfo"""
    INICount = IniFile.formatMatch(fullpath)
    OBSECount = OBSEIniFile.formatMatch(fullpath)
    if INICount >= OBSECount:
        return INIInfo(fullpath)
    else:
        return ObseIniInfo(fullpath)

class INIInfos(TableFileInfos):
    """:type _ini: IniFile
    :type data: dict[bolt.Path, IniInfo]"""
    file_pattern = re.compile(ur'\.ini$', re.I | re.U)

    def __init__(self):
        INIInfos._default_tweaks = dict(
            (GPath(k), DefaultIniInfo(k, v)) for k, v in
            bush.game_mod.default_tweaks.iteritems())
        super(INIInfos, self).__init__(dirs['tweaks'],
                                       factory=ini_info_factory)
        self._ini = None
        # Check the list of target INIs, remove any that don't exist
        # if _target_inis is not an OrderedDict choice won't be set correctly
        _target_inis = bass.settings['bash.ini.choices'] # type: OrderedDict
        choice = bass.settings['bash.ini.choice'] # type: int
        if isinstance(_target_inis, OrderedDict):
            try:
                previous_ini = _target_inis.keys()[choice]
            except IndexError:
                choice, previous_ini = -1, None
        else: # not an OrderedDict, updating from 306
            choice, previous_ini = -1, None
        for ini_name in _target_inis.keys():
            if ini_name == _(u'Browse...'): continue
            ini_path = _target_inis[ini_name]
            # If user started with non-translated, 'Browse...'
            # will still be in here, but in English.  It wont get picked
            # up by the previous check, so we'll just delete any non-Path
            # objects.  That will take care of it.
            if not isinstance(ini_path,bolt.Path) or not ini_path.isfile():
                if get_game_ini(ini_path):
                    continue # don't remove game inis even if missing
                del _target_inis[ini_name]
                if ini_name is previous_ini:
                    choice, previous_ini = -1, None
        csChoices = set(x.lower() for x in _target_inis)
        for iFile in gameInis: # add the game inis even if missing
            if iFile.abs_path.tail.cs not in csChoices:
                _target_inis[iFile.abs_path.stail] = iFile.abs_path
        if _(u'Browse...') not in _target_inis:
            _target_inis[_(u'Browse...')] = None
        self.__sort_target_inis()
        if previous_ini:
            choice = bass.settings['bash.ini.choices'].keys().index(
                previous_ini)
        bass.settings['bash.ini.choice'] = choice if choice >= 0 else 0
        self.ini = bass.settings['bash.ini.choices'].values()[
            bass.settings['bash.ini.choice']]

    @property
    def ini(self):
        return self._ini
    @ini.setter
    def ini(self, ini_path):
        """:type ini_path: bolt.Path"""
        if self._ini is not None and self._ini.abs_path == ini_path:
            return # nothing to do
        self._ini = BestIniFile(ini_path)
        for ini_info in self.itervalues(): ini_info.reset_status()

    @staticmethod
    def update_targets(targets_dict):
        """Update 'bash.ini.choices' with targets_dict then re-sort the dict
        of target INIs"""
        for existing_ini in bass.settings['bash.ini.choices']:
            targets_dict.pop(existing_ini, None)
        if targets_dict:
            bass.settings['bash.ini.choices'].update(targets_dict)
            # now resort
            INIInfos.__sort_target_inis()
        return targets_dict

    @staticmethod
    def __sort_target_inis():
        keys = bass.settings['bash.ini.choices'].keys()
        # Sort alphabetically
        keys.sort()
        # Sort Oblivion.ini to the top, and 'Browse...' to the bottom
        game_inis = bush.game.iniFiles
        len_inis = len(game_inis)
        keys.sort(key=lambda a: game_inis.index(a) if a in game_inis else (
                      len_inis + 1 if a == _(u'Browse...') else len_inis))
        bass.settings['bash.ini.choices'] = collections.OrderedDict(
            [(k, bass.settings['bash.ini.choices'][k]) for k in keys])

    def _refresh_infos(self):
        """Refresh from file directory."""
        oldNames=set(n for n, v in self.iteritems() if not v.is_default_tweak)
        _added = set()
        _updated = set()
        newNames = self._names()
        for name in newNames:
            oldInfo = self.get(name) # None if name was added
            if oldInfo is not None and not oldInfo.is_default_tweak:
                if oldInfo.do_update(): _updated.add(name)
            else: # added
                oldInfo = self.factory(self.store_dir.join(name))
                _added.add(name)
            self[name] = oldInfo
        _deleted = oldNames - newNames
        self.delete_refresh(_deleted, None, check_existence=False,
                            _in_refresh=True)
        # re-add default tweaks
        for k in self.keys():
            if k not in newNames: del self[k]
        set_keys = set(self.keys())
        for k, d in self._default_tweaks.iteritems():
            if k not in set_keys:
                default_info = self.setdefault(k, d) # type: DefaultIniInfo
                if k in _deleted: # we restore default over copy
                    _updated.add(k)
                    default_info.reset_status()
        if _updated:
            self._notify_bain(changed={self[n].abs_path for n in _updated})
        return _added, _deleted, _updated

    def refresh(self, refresh_infos=True, refresh_target=True):
        _added = _deleted = _updated = set()
        if refresh_infos:
            _added, _deleted, _updated = self._refresh_infos()
        changed = refresh_target and (
            self.ini.updated or self.ini.do_update())
        if changed: # reset the status of all infos and let RefreshUI set it
            self.ini.updated = False
            for ini_info in self.itervalues(): ini_info.reset_status()
        change = bool(_added) or bool(_updated) or bool(_deleted) or changed
        if not change: return change
        return _added, _updated, _deleted, changed

    @property
    def bash_dir(self): return dirs['modsBash'].join(u'INI Data')

    def delete_refresh(self, deleted_keys, paths_to_keys, check_existence,
                       _in_refresh=False):
        deleted = self._update_deleted_paths(deleted_keys, paths_to_keys,
                                             check_existence)
        if not deleted: return deleted
        for name in deleted:
            self.pop(name, None)
            self.table.delRow(name)
        set_keys = set(self.keys())
        if not _in_refresh: # readd default tweaks
            for k, d in self._default_tweaks.iteritems():
                if k not in set_keys:
                    default_info = self.setdefault(k, d) # type: DefaultIniInfo
                    default_info.reset_status()
        return deleted

    def get_tweak_lines_infos(self, tweakPath):
        tweak_lines = self[tweakPath].read_ini_lines()
        return self._ini.get_lines_infos(tweak_lines)

    def open_or_copy(self, tweak):
        info = self[tweak] # type: INIInfo
        if info.is_default_tweak:
            self._copy_to_new_tweak(info, tweak)
            return True # refresh
        else:
            info.abs_path.start()
            return False

    def _copy_to_new_tweak(self, info, new_tweak): ##: encoding....
        with open(self.store_dir.join(new_tweak).s, 'w') as ini_file:
            # writelines does not do what you'd expect, would concatenate lines
            ini_file.write('\n'.join(info.read_ini_lines()))
        self.new_info(new_tweak.tail, notify_bain=True)
        return self[new_tweak.tail]

    def duplicate_ini(self, tweak, new_tweak):
        """Duplicate tweak into new_tweak, copying current target settings"""
        if not new_tweak: return False
        # new_tweak is an abs path, join works ok relative to self.store_dir
        dup_info = self._copy_to_new_tweak(self[tweak], new_tweak)
        # Now edit it with the values from the target INI
        new_tweak_settings = bolt.LowerDict(dup_info.get_ci_settings())
        target_settings = self.ini.get_ci_settings()
        for section in new_tweak_settings:
            if section in target_settings:
                for setting in new_tweak_settings[section]:
                    if setting in target_settings[section]:
                        new_tweak_settings[section][setting] = \
                            target_settings[section][setting]
        for k,v in new_tweak_settings.items(): # drop line numbers
            new_tweak_settings[k] = dict( # saveSettings converts to LowerDict
                (sett, val[0]) for sett, val in v.iteritems())
        dup_info.saveSettings(new_tweak_settings)
        return True

def _lo_cache(lord_func):
    """Decorator to make sure I sync modInfos cache with load_order cache
    whenever I change (or attempt to change) the latter, and that I do
    refresh modInfos."""
    @wraps(lord_func)
    def _modinfos_cache_wrapper(self, *args, **kwargs):
        """Sync the ModInfos load order and active caches and refresh for
        load order or active changes.

        :type self: ModInfos
        :return: 1 if only load order changed, 2 if only active changed,
        3 if both changed else 0
        """
        try:
            old_lo, old_active = load_order.cached_lord.loadOrder, \
                                 load_order.cached_lord.activeOrdered
            lord_func(self, *args, **kwargs)
            lo, active = load_order.cached_lord.loadOrder, \
                         load_order.cached_lord.activeOrdered
            lo_changed = lo != old_lo
            active_changed = active != old_active
            active_set_changed = active_changed and (
                set(active) != set(old_active))
            if active_changed:
                self._refresh_mod_inis() # before _refreshMissingStrings !
                self._refreshBadNames()
                self._reset_info_sets()
                self._refreshMissingStrings()
            #if lo changed (including additions/removals) let refresh handle it
            if active_set_changed or (set(lo) - set(old_lo)): # new mods, ghost
                self.autoGhost(force=False)
            new_active = set(active) - set(old_active)
            for neu in new_active: # new active mods, unghost
                self[neu].setGhost(False)
            return (lo_changed and 1) + (active_changed and 2)
        finally:
            self._lo_wip, self._active_wip = list(
                load_order.cached_lord.loadOrder), list(
                load_order.cached_lord.activeOrdered)
    return _modinfos_cache_wrapper

#------------------------------------------------------------------------------
class ModInfos(FileInfos):
    """Collection of modinfos. Represents mods in the Oblivion\Data directory."""

    def __init__(self):
        self.__class__.file_pattern = re.compile(ur'(' + '|'.join(
            map(re.escape, bush.game.espm_extensions)) + ur')(\.ghost)?$',
                                                 re.I | re.U)
        FileInfos.__init__(self, dirs['mods'], factory=ModInfo)
        #--Info lists/sets
        self.mergeScanned = [] #--Files that have been scanned for mergeability.
        for fname in bush.game.masterFiles:
            if dirs['mods'].join(fname).exists():
                self.masterName = GPath(fname)
                break
        else:
            if len(bush.game.masterFiles) == 1:
                deprint(_(u'Missing master file; %s does not exist in an unghosted state in %s') % (fname, dirs['mods'].s))
            else:
                msg = bush.game.masterFiles[0]
                if len(bush.game.masterFiles) > 2:
                    msg += u', '.join(bush.game.masterFiles[1:-1])
                msg += u' or ' + bush.game.masterFiles[-1]
                deprint(_(u'Missing master file; Neither %s exists in an unghosted state in %s.  Presuming that %s is the correct masterfile.') % (msg, dirs['mods'].s, bush.game.masterFiles[0]))
            self.masterName = GPath(bush.game.masterFiles[0])
        self.mergeable = set() #--Set of all mods which can be merged.
        self.bad_names = set() #--Set of all mods with names that can't be saved to plugins.txt
        self.missing_strings = set() #--Set of all mods with missing .STRINGS files
        self.new_missing_strings = set() #--Set of new mods with missing .STRINGS files
        self.activeBad = set() #--Set of all mods with bad names that are active
        self.sse_form43 = set()
        # sentinel for calculating info sets when needed in gui and patcher
        # code, **after** self is refreshed
        self.__calculate = object()
        self._reset_info_sets()
        #--Oblivion version
        self.version_voSize = {
            u'1.1':        247388848, #--Standard
            u'1.1b':       247388894, # Arthmoor has this size.
            u'GOTY non-SI':247388812, # GOTY version
            u'1.0.7.5':    108369128, # Nehrim
            u'1.5.0.8':    115531891, # Nehrim Update
            u'SI':         277504985} # Shivering Isles 1.2
        self.size_voVersion = {y:x for x, y in self.version_voSize.iteritems()}
        self.voCurrent = None
        self.voAvailable = set()
        # removed/extra mods in plugins.txt - set in load_order.py,
        # used in RefreshData
        self.selectedBad = set()
        self.selectedExtra = []
        load_order.initialize_load_order_handle(self)
        # Load order caches to manipulate, then call our save methods - avoid !
        self._active_wip = []
        self._lo_wip = []

    # merged, bashed_patches, imported caches
    def _reset_info_sets(self):
        self._merged = self._imported = self._bashed_patches = self.__calculate

    @property
    def imported(self):
        if self._imported is self.__calculate:
            self._merged, self._imported = self.getSemiActive()
        return self._imported

    @property
    def merged(self):
        if self._merged is self.__calculate:
            self._merged, self._imported = self.getSemiActive()
        return self._merged

    @property
    def bashed_patches(self):
        if self._bashed_patches is self.__calculate:
            self._bashed_patches = set(
                mname for mname, minf in self.iteritems() if minf.isBP())
        return self._bashed_patches

    # Load order API for the rest of Bash to use - if the load order or
    # active plugins changed, those methods run a refresh on modInfos data
    @_lo_cache
    def refreshLoadOrder(self, forceRefresh=False, forceActive=False):
        load_order.refresh_lo(cached=not forceRefresh,
                              cached_active=not forceActive)

    @_lo_cache
    def cached_lo_save_active(self, active=None):
        """Write data to Plugins.txt file.

        Always call AFTER setting the load order - make sure we unghost
        ourselves so ctime of the unghosted mods is not set."""
        load_order.save_lo(load_order.cached_lord.loadOrder,
                           load_order.cached_lord.lorder(
                        active if active is not None else self._active_wip))

    @_lo_cache
    def cached_lo_save_lo(self):
        """Save load order when active did not change."""
        load_order.save_lo(self._lo_wip)

    @_lo_cache
    def cached_lo_save_all(self):
        """Save load order and plugins.txt"""
        dex = {x: i for i, x in enumerate(self._lo_wip) if
               x in set(self._active_wip)}
        self._active_wip.sort(key=dex.__getitem__) # order in their load order
        load_order.save_lo(self._lo_wip, acti=self._active_wip)

    @_lo_cache
    def undo_load_order(self): load_order.undo_load_order()

    @_lo_cache
    def redo_load_order(self): load_order.redo_load_order()

    #--Load Order utility methods - be sure cache is valid when using them
    def cached_lo_insert_after(self, previous, new_mod):
        previous_index = self._lo_wip.index(previous)
        if not load_order.using_txt_file():
            # set the mtime to avoid reordering all subsequent mods
            try:
                next_mod = self._lo_wip[previous_index + 1]
            except IndexError: # last mod
                next_mod = None
            end_time = self[next_mod].mtime if next_mod else None
            start_time  = self[previous].mtime
            if end_time is not None and \
                    end_time <= start_time: # can happen on esm/esp boundary
                start_time = end_time - 60
            set_time = load_order.get_free_time(start_time, end_time=end_time)
            self[new_mod].setmtime(set_time)
        self._lo_wip[previous_index + 1:previous_index + 1] = [new_mod]

    def cached_lo_last_esm(self):
        last_esm = self.masterName
        for mod in self._lo_wip[1:]:
            if not self[mod].is_esml(): return last_esm
            last_esm = mod
        return last_esm

    def cached_lo_insert_at(self, first, modlist):
        # hasty method for Mod_OrderByName
        mod_set = set(modlist)
        first_dex = self._lo_wip.index(first)
        rest = self._lo_wip[first_dex:]
        del self._lo_wip[first_dex:]
        for mod in rest:
            if mod in mod_set: continue
            self._lo_wip.append(mod)
        self._lo_wip[first_dex:first_dex] = modlist

    def cached_lo_append_if_missing(self, mods):
        new = mods - set(self._lo_wip)
        if not new: return
        esms = set(x for x in new if self[x].is_esml())
        if esms:
            last = self.cached_lo_last_esm()
            for esm in esms:
                self.cached_lo_insert_after(last, esm)
                last = esm
            new -= esms
        self._lo_wip.extend(new)
        self.cached_lo_save_lo()

    @staticmethod
    def hexIndexString(mod):
        return u'%02X' % (load_order.cached_active_index(mod),) \
            if load_order.cached_is_active(mod) else u''

    def masterWithVersion(self, master_name):
        if master_name == u'Oblivion.esm' and self.voCurrent:
            master_name += u' [' + self.voCurrent + u']'
        return master_name

    def dropItems(self, dropItem, firstItem, lastItem): # MUTATES plugins CACHE
        # Calculating indexes through order.index() cause we may be called in
        # a row before saving the modified load order
        order = self._lo_wip
        newPos = order.index(dropItem)
        if newPos <= 0: return False
        start = order.index(firstItem)
        stop = order.index(lastItem) + 1  # excluded
        # Can't move the game's master file anywhere else but position 0
        master = self.masterName
        if master in order[start:stop]: return False
        # List of names to move removed and then reinserted at new position
        toMove = order[start:stop]
        del order[start:stop]
        order[newPos:newPos] = toMove
        return True

    @property
    def bash_dir(self): return dirs['modsBash']

    #--Refresh-----------------------------------------------------------------
    def _names(self):
        names = super(ModInfos, self)._names()
        unghosted_names = set()
        for name in sorted(names, key=lambda x: x.cext == u'.ghost'):
            if name.cs[-6:] == u'.ghost': name = GPath(name.s[:-6])
            if name in unghosted_names:
                deprint(u'Both %s and its ghost exist. The ghost will be '
                        u'ignored but this may lead to undefined behavior - '
                        u'please remove one or the other' % name)
            else: unghosted_names.add(name)
        return unghosted_names

    def refresh(self, refresh_infos=True, booting=False, _modTimesChange=False):
        """Update file data for additions, removals and date changes.

        See usages for how to use the refresh_infos and _modTimesChange params.
        _modTimesChange is not strictly needed after the lo rewrite, as
        games.Game#load_order_changed will always return True for timestamp
        games - kept to help track places in the code where timestamp load
        order may change.
         NB: if an operation we performed changed the load order we do not want
         lock load order to revert our own operation. So either call some of
         the set_load_order methods, or guard refresh (which only *gets* load
         order) with load_order.Unlock.
        """
        hasChanged = deleted = False
        # Scan the data dir, getting info on added, deleted and modified files
        if refresh_infos:
            change = FileInfos.refresh(self, booting=booting)
            if change: _added, _updated, deleted = change
            hasChanged = bool(change)
        # If refresh_infos is False and mods are added _do_ manually refresh
        _modTimesChange = _modTimesChange and not load_order.using_txt_file()
        lo_changed = self.refreshLoadOrder(
            forceRefresh=hasChanged or _modTimesChange, forceActive=deleted)
        self.reloadBashTags()
        # if active did not change, we must perform the refreshes below
        if lo_changed < 2: # in case ini files were deleted or modified
            self._refresh_mod_inis()
        if lo_changed < 2 and hasChanged:
            self._refreshBadNames()
            self._reset_info_sets()
        elif lo_changed < 2: # maybe string files were deleted...
            #we need a load order below: in skyrim we read inis in active order
            hasChanged += self._refreshMissingStrings()
        self._setOblivionVersions()
        oldMergeable = set(self.mergeable)
        scanList = self._refreshMergeable()
        difMergeable = (oldMergeable ^ self.mergeable) & set(self.keys())
        if scanList:
            self.rescanMergeable(scanList)
        hasChanged += bool(scanList or difMergeable)
        return bool(hasChanged) or lo_changed

    _plugin_inis = OrderedDict() # cache active mod inis in active mods order
    def _refresh_mod_inis(self):
        if not bush.game.supports_mod_inis: return
        iniPaths = (self[m].getIniPath() for m in load_order.cached_active_tuple())
        iniPaths = [p for p in iniPaths if p.isfile()]
        # delete non existent inis from cache
        for key in self._plugin_inis.keys():
            if key not in iniPaths:
                del self._plugin_inis[key]
        # update cache with new or modified files
        for iniPath in iniPaths:
            if iniPath not in self._plugin_inis or self._plugin_inis[
                iniPath].do_update():
                self._plugin_inis[iniPath] = IniFile(iniPath)
        self._plugin_inis = OrderedDict(
            [(k, self._plugin_inis[k]) for k in iniPaths])

    def _refreshBadNames(self):
        """Refreshes which filenames cannot be saved to plugins.txt
        It seems that Skyrim and Oblivion read plugins.txt as a cp1252
        encoded file, and any filename that doesn't decode to cp1252 will
        be skipped."""
        bad = self.bad_names = set()
        activeBad = self.activeBad = set()
        for fileName in self.data:
            if self.isBadFileName(fileName.s):
                if load_order.cached_is_active(fileName):
                    ## For now, we'll leave them active, until
                    ## we finish testing what the game will support
                    #self.lo_deactivate(fileName)
                    activeBad.add(fileName)
                else:
                    bad.add(fileName)
        return bool(activeBad)

    def _refreshMissingStrings(self):
        """Refreshes which mods are supposed to have strings files, but are
        missing them (=CTD). For Skyrim you need to have a valid load order."""
        oldBad = self.missing_strings
        self.missing_strings = set(
            k for k, v in self.iteritems() if v.isMissingStrings())
        self.new_missing_strings = self.missing_strings - oldBad
        return bool(self.new_missing_strings)

    def autoGhost(self,force=False):
        """Automatically turn inactive files to ghosts.

        Should be called when deactivating mods - will have an effect if
        bash.mods.autoGhost is true, or if force parameter is true (in which
        case, if autoGhost is False, it will actually unghost all ghosted
        mods). If both the mod and its ghost exist, the mod is not active and
        this method runs while autoGhost is on, the normal version will be
        moved to the ghost.
        :param force: set to True only in Mods_AutoGhost, so if fired when
        toggling bash.mods.autoGhost to False we forcibly unghost all mods
        """
        changed = []
        toGhost = bass.settings.get('bash.mods.autoGhost',False)
        if force or toGhost:
            allowGhosting = self.table.getColumn('allowGhosting')
            for mod, modInfo in self.iteritems():
                modGhost = toGhost and not load_order.cached_is_active(mod) \
                           and allowGhosting.get(mod, True)
                oldGhost = modInfo.isGhost
                newGhost = modInfo.setGhost(modGhost)
                if newGhost != oldGhost:
                    changed.append(mod)
        return changed

    def _refreshMergeable(self):
        """Refreshes set of mergeable mods."""
        #--Mods that need to be rescanned - call rescanMergeable !
        newMods = []
        self.mergeable.clear()
        name_mergeInfo = self.table.getColumn('mergeInfo')
        #--Add known/unchanged and esms - we need to scan dependent mods
        # first to account for mergeability of their masters
        for mpath, modInfo in sorted(self.items(),
                key=lambda tup: load_order.cached_lo_index(tup[0]),
                                     reverse=True):
            size, canMerge = name_mergeInfo.get(mpath, (None, None))
            # if esm bit was flipped size won't change, so check this first
            if modInfo.isEsm(): # modInfo must have its header set
                name_mergeInfo[mpath] = (modInfo.size, False)
                self.mergeable.discard(mpath)
            elif size == modInfo.size:
                if canMerge: self.mergeable.add(mpath)
            else:
                newMods.append(mpath)
        return newMods

    def rescanMergeable(self, names, prog=None, doCBash=None, verbose=False):
        with prog or balt.Progress(_(u"Mark Mergeable") + u' ' * 30) as prog:
            return self._rescanMergeable(names, prog, doCBash, verbose)

    def _rescanMergeable(self, names, progress, doCBash, verbose):
        """Will rescan specified mods."""
        if doCBash is None:
            doCBash = CBashApi.Enabled
        elif doCBash and not CBashApi.Enabled:
            doCBash = False
        is_mergeable = isCBashMergeable if doCBash else isPBashMergeable
        mod_mergeInfo = self.table.getColumn('mergeInfo')
        progress.setFull(max(len(names),1))
        result, tagged_no_merge = OrderedDict(), set()
        for i,fileName in enumerate(names):
            progress(i,fileName.s)
            if not doCBash and reOblivion.match(fileName.s): continue
            fileInfo = self[fileName]
            if not bush.game.esp.canBash:
                canMerge = False
            else:
                try:
                    canMerge = is_mergeable(fileInfo, self, verbose)
                except Exception as e:
                    # deprint (_(u"Error scanning mod %s (%s)") % (fileName, e))
                    # canMerge = False #presume non-mergeable.
                    raise
            result[fileName] = canMerge
            if not isinstance(canMerge, basestring) and canMerge: # True...
                self.mergeable.add(fileName)
                mod_mergeInfo[fileName] = (fileInfo.size,True)
            else:
                mod_mergeInfo[fileName] = (fileInfo.size,False)
                self.mergeable.discard(fileName)
            if fileName in self.mergeable and u'NoMerge' in fileInfo.getBashTags():
                tagged_no_merge.add(fileName)
        return result, tagged_no_merge

    def reloadBashTags(self):
        """Reloads bash tags for all mods set to receive automatic bash tags."""
        for modName, mod in self.iteritems():
            autoTag = self.table.getItem(modName, 'autoBashTags')
            if autoTag is None and self.table.getItem(
                    modName, 'bashTags') is None:
                # A new mod, set autoBashTags to True (default)
                self.table.setItem(modName, 'autoBashTags', True)
                autoTag = True
            elif autoTag is None:
                # An old mod that had manual bash tags added, disable autoBashTags
                self.table.setItem(modName, 'autoBashTags', False)
            if autoTag:
                mod.reloadBashTags()

    def refresh_crcs(self, mods=None): #TODO(ut) progress !
        if mods is None: mods = self.keys()
        pairs = {}
        for mod in mods:
            inf = self[mod]
            pairs[inf.name] = inf.calculate_crc(recalculate=True)
        return pairs

    #--Refresh File
    def new_info(self, fileName, _in_refresh=False, owner=None,
                 notify_bain=False):
        # we should refresh info sets if we manage to add the info, but also
        # if we fail, which might mean that some info got corrupted
        self._reset_info_sets()
        return super(ModInfos, self).new_info(fileName, _in_refresh, owner,
                                              notify_bain)

    #--Mod selection ----------------------------------------------------------
    def getSemiActive(self,masters=None):
        """Return (merged,imported) mods made semi-active by Bashed Patch.

        If no bashed patches are present in 'masters' then return empty sets.
        Else for each bashed patch use its config (if present) to find mods
        it merges or imports."""
        if masters is None: masters = set(load_order.cached_active_tuple())
        merged_,imported_ = set(),set()
        patches = masters & self.bashed_patches
        for patch in patches:
            patchConfigs = self.table.getItem(patch, 'bash.patch.configs')
            if not patchConfigs: continue
            patcherstr = 'CBash_PatchMerger' if patcher.configIsCBash(
                patchConfigs) else 'PatchMerger'
            if patchConfigs.get(patcherstr,{}).get('isEnabled'):
                config_checked = patchConfigs[patcherstr]['configChecks']
                for modName in config_checked:
                    if config_checked[modName] and modName in self:
                        merged_.add(modName)
            imported_.update(filter(lambda x: x in self,
                                    patchConfigs.get('ImportedMods', tuple())))
        return merged_,imported_

    def getModList(self,showCRC=False,showVersion=True,fileInfo=None,wtxt=False):
        """Returns mod list as text. If fileInfo is provided will show mod list
        for its masters. Otherwise will show currently loaded mods."""
        #--Setup
        with sio() as out:
            log = bolt.LogFile(out)
            head,bul,sMissing,sDelinquent,sImported = (
                u'=== ',
                u'* ',
                _(u'  * __Missing Master:__ '),
                _(u'  * __Delinquent Master:__ '),
                u'&bull; &bull;'
                ) if wtxt else (
                u'',
                u'',
                _(u'----> MISSING MASTER: '),
                _(u'----> Delinquent MASTER: '),
                u'**')
            if fileInfo:
                masters = set(fileInfo.header.masters)
                missing = sorted([x for x in masters if x not in self])
                log.setHeader(head+_(u'Missing Masters for %s: ') % fileInfo.name.s)
                for mod in missing:
                    log(bul+u'xx '+mod.s)
                log.setHeader(head+_(u'Masters for %s: ') % fileInfo.name.s)
                present = set(x for x in masters if x in self)
                if fileInfo.name in self: #--In case is bashed patch (cf getSemiActive)
                    present.add(fileInfo.name)
                merged,imported = self.getSemiActive(present)
            else:
                log.setHeader(head+_(u'Active Mod Files:'))
                masters = set(load_order.cached_active_tuple())
                merged,imported = self.merged,self.imported
            allMods = masters | merged | imported
            allMods = load_order.get_ordered([x for x in allMods if x in self])
            #--List
            modIndex = 0
            if not wtxt: log(u'[spoiler][xml]\n', appendNewline=False)
            for name in allMods:
                if name in masters:
                    prefix = bul+u'%02X' % modIndex
                    modIndex += 1
                elif name in merged:
                    prefix = bul+u'++'
                else:
                    prefix = bul+sImported
                text = u'%s  %s' % (prefix,name.s,)
                if showVersion:
                    version = self.getVersion(name)
                    if version: text += _(u'  [Version %s]') % version
                if showCRC:
                    text +=_(u'  [CRC: %s]') % (self[name].crc_string())
                log(text)
                if name in masters:
                    for master2 in self[name].header.masters:
                        if master2 not in self:
                            log(sMissing+master2.s)
                        elif load_order.get_ordered((name, master2))[1] == master2:
                            log(sDelinquent+master2.s)
            if not wtxt: log(u'[/xml][/spoiler]')
            return bolt.winNewLines(log.out.getvalue())

    @staticmethod
    def _tagsies(modInfo, tagList):
        mname = modInfo.name
        def _tags(msg, iterable, tagsList):
            return tagsList + u'  * ' + msg + u', '.join(iterable) + u'\n'
        if not modInfos.table.getItem(mname, 'autoBashTags') and \
               modInfos.table.getItem(mname, 'bashTags', u''):
            tagList = _tags(_(u'From Manual (if any this overrides '
                u'Description/LOOT sourced tags): '), sorted(
                modInfos.table.getItem(mname, 'bashTags', u'')), tagList)
        tags_desc = modInfo.getBashTagsDesc()
        if tags_desc:
            tagList = _tags(_(u'From Description: '), sorted(tags_desc),
                            tagList)
        tags, removed, _userlist = configHelpers.getTagsInfoCache(mname)
        if tags:
            tagList = _tags(_(u'From LOOT Masterlist and or userlist: '),
                            sorted(tags), tagList)
        if removed:
            tagList = _tags(_(u'Removed by LOOT Masterlist and or userlist: '),
                            sorted(removed), tagList)
        return _tags(_(u'Result: '), sorted(modInfo.getBashTags()), tagList)

    @staticmethod
    def getTagList(mod_list=None):
        """Return the list as wtxt of current bash tags (but don't say which
        ones are applied via a patch) - either for all mods in the data folder
        or if specified for one specific mod."""
        tagList = u'=== '+_(u'Current Bash Tags')+u':\n'
        tagList += u'[spoiler][xml]\n'
        if mod_list:
            for modInfo in mod_list:
                tagList += u'\n* ' + modInfo.name.s + u'\n'
                if modInfo.getBashTags():
                    tagList = ModInfos._tagsies(modInfo, tagList)
                else: tagList += u'    '+_(u'No tags')
        else:
            # sort output by load order
            lindex = lambda t: load_order.cached_lo_index(t[0])
            for path, modInfo in sorted(modInfos.iteritems(), key=lindex):
                if modInfo.getBashTags():
                    tagList += u'\n* ' + modInfo.name.s + u'\n'
                    tagList = ModInfos._tagsies(modInfo, tagList)
        tagList += u'[/xml][/spoiler]'
        return tagList

    @staticmethod
    def askResourcesOk(fileInfo, bsaAndVoice, bsa, voice):
        if not fileInfo.isMod():
            return u''
        hasBsa, hasVoices = fileInfo.hasResources()
        if (hasBsa, hasVoices) == (False,False):
            return u''
        mPath, name = fileInfo.name, fileInfo.name.s
        if hasBsa and hasVoices: msg = bsaAndVoice % (mPath.sroot, name, name)
        elif hasBsa: msg = bsa % (mPath.sroot, name)
        else: msg = voice % name # hasVoices
        return msg

    #--Active mods management -------------------------------------------------
    def lo_activate(self, fileName, doSave=True, _modSet=None, _children=None,
                    _activated=None):
        """Mutate _active_wip cache then save if needed."""
        if _activated is None: _activated = set()
        try:
            minfo = self[fileName]
            if not minfo.is_esl(): # don't check limit if activating an esl
                acti_filtered_espm = [x for x in self._active_wip if
                                      x.cext != u'.esl']
                if len(acti_filtered_espm) == load_order.max_espms:
                    raise PluginsFullError(u'%s: Trying to activate more than '
                        u'%d espms' % (fileName,load_order.max_espms))
            _children = (_children or tuple()) + (fileName,)
            if fileName in _children[:-1]:
                raise BoltError(u'Circular Masters: ' +u' >> '.join(x.s for x in _children))
            #--Select masters
            if _modSet is None: _modSet = set(self.keys())
            #--Check for bad masternames:
            #  Disabled for now
            ##if self[fileName].hasBadMasterNames():
            ##    return
            for master in minfo.header.masters:
                if master in _modSet: self.lo_activate(master, False, _modSet,
                                                       _children, _activated)
            #--Select in plugins
            if fileName not in self._active_wip:
                self._active_wip.append(fileName)
                _activated.add(fileName)
            return load_order.get_ordered(_activated or [])
        finally:
            if doSave: self.cached_lo_save_active()

    def lo_deactivate(self, fileName, doSave=True):
        """Remove mods and their children from _active_wip, can only raise if
        doSave=True."""
        if not isinstance(fileName, (set, list)): fileName = {fileName}
        notDeactivatable = load_order.must_be_active_if_present()
        fileNames = set(x for x in fileName if x not in notDeactivatable)
        old = sel = set(self._active_wip)
        diff = sel - fileNames
        if len(diff) == len(sel): return set()
        #--Unselect self
        sel = diff
        #--Unselect children
        children = set()
        def _children(parent):
            for selFile in sel:
                if selFile in children: continue # if no more => no more in sel
                for master in self[selFile].header.masters:
                    if master == parent:
                        children.add(selFile)
                        break
        for fileName in fileNames: _children(fileName)
        while children:
            child = children.pop()
            sel.remove(child)
            _children(child)
        self._active_wip = load_order.get_ordered(sel)
        #--Save
        if doSave: self.cached_lo_save_active()
        return old - sel # return deselected

    def lo_activate_all(self):
        toActivate = set(load_order.cached_active_tuple())
        try:
            def _add_to_activate(m):
                if not m in toActivate:
                    self.lo_activate(m, doSave=False)
                    toActivate.add(m)
            mods = load_order.get_ordered(self.keys())
            # first select the bashed patch(es) and their masters
            for mod in mods:
                if self[mod].isBP(): _add_to_activate(mod)
            # then activate mods not tagged NoMerge or Deactivate or Filter
            def _activatable(modName):
                tags = modInfos[modName].getBashTags()
                return not (u'Deactivate' in tags or u'Filter' in tags)
            mods = filter(_activatable, mods)
            mergeable = set(self.mergeable)
            for mod in mods:
                if not mod in mergeable: _add_to_activate(mod)
            # then activate as many of the remaining mods as we can
            for mod in mods:
                if mod in mergeable: _add_to_activate(mod)
        except PluginsFullError:
            deprint(u'select All: 255 mods activated', traceback=True)
            raise
        except BoltError:
            toActivate.clear()
            deprint(u'select All: cached_lo_save_active failed',traceback=True)
            raise
        finally:
            if toActivate: self.cached_lo_save_active(active=toActivate)

    def lo_activate_exact(self, modNames):
        """Activate exactly the specified set of mods."""
        modsSet, allMods = set(modNames), set(self.keys())
        #--Ensure plugins that cannot be deselected stay selected
        modsSet.update(load_order.must_be_active_if_present() & allMods)
        #--Deselect/select plugins
        missingSet = modsSet - allMods
        toSelect = modsSet - missingSet
        listToSelect = load_order.get_ordered(toSelect)
        acti_filtered_espm = [x for x in listToSelect if x.cext != u'.esl']
        skipped = acti_filtered_espm[load_order.max_espms:]
        #--Save
        if skipped:
            listToSelect = [x for x in listToSelect if x not in set(skipped)]
        self.cached_lo_save_active(active=listToSelect)
        #--Done/Error Message
        message = u''
        if missingSet:
            message += _(u'Some mods were unavailable and were skipped:')+u'\n* '
            message += u'\n* '.join(x.s for x in missingSet)
        if skipped:
            if missingSet: message += u'\n'
            message += _(u'Mod list is full, so some mods were skipped:')+u'\n'
            message += u'\n* '.join(x.s for x in skipped)
        return message

    #--Helpers ----------------------------------------------------------------
    @staticmethod
    def isBadFileName(modName):
        """True if the name cannot be encoded to the proper format for plugins.txt"""
        try:
            modName.encode('cp1252')
            return False
        except UnicodeEncodeError:
            return True

    def getDirtyMessage(self, modname):
        """Returns a dirty message from LOOT."""
        if self.table.getItem(modname, 'ignoreDirty', False):
            return False, u''
        return configHelpers.getDirtyMessage(modname)

    def ini_files(self):
        iniFiles = self._plugin_inis.values() # in active order
        iniFiles.reverse() # later loading inis override previous settings
        iniFiles.append(oblivionIni)
        return iniFiles

    def create_new_mod(self, newName, selected=(), masterless=False,
                       directory=empty_path, bashed_patch=False):
        directory = directory or self.store_dir
        new_name = GPath(newName)
        newInfo = self.factory(directory.join(new_name))
        newFile = ModFile(newInfo)
        if not masterless:
            newFile.tes4.masters = [self.masterName]
        if bashed_patch:
            newFile.tes4.author = u'BASHED PATCH'
        newFile.safeSave()
        if directory == self.store_dir:
            self.new_info(new_name, notify_bain=True) # notify just in case...
            last_selected = load_order.get_ordered(selected)[
                -1] if selected else self._lo_wip[-1]
            self.cached_lo_insert_after(last_selected, new_name)
            self.cached_lo_save_lo()
            self.refresh(refresh_infos=False)

    def generateNextBashedPatch(self, selected_mods):
        """Attempt to create a new bashed patch, numbered from 0 to 9.  If
        a lowered number bashed patch exists, will create the next in the
        sequence."""
        for num in xrange(10):
            modName = GPath(u'Bashed Patch, %d.esp' % num)
            if modName not in self:
                self.create_new_mod(modName, selected=selected_mods,
                                    masterless=True, bashed_patch=True)
                return modName
        return None

    def get_active_bsas(self):
        """Return active bsas and the order of their activator mods. If a mod
        activates more than one bsa, their relative order is undefined."""
        # TODO(ut): get those activated by inis
        active_bsas = OrderedDict()
        # bsaInfos must be updated
        bsas = dict(bsaInfos.iteritems())
        for j, mod in enumerate(load_order.cached_active_tuple()):
            mod_bsas = self[mod].mod_bsas(bsas)
            for b in mod_bsas:
                active_bsas[b] = j
                del bsas[b.name]
        return active_bsas

    @staticmethod
    def plugin_wildcard(file_str=_(u'Mod Files')):
        join_star = u';*'.join(bush.game.espm_extensions)
        return bush.game.displayName + u' ' + file_str + u' (*' + join_star \
               + u')|*' + join_star

    #--Mod move/delete/rename -------------------------------------------------
    def _lo_caches_remove_mods(self, to_remove):
        """Remove the specified mods from _lo_wip and _active_wip caches."""
        # Use set to remove any duplicates
        to_remove = set(to_remove, )
        # Remove mods from cache
        self._lo_wip = [x for x in self._lo_wip if x not in to_remove]
        self._active_wip  = [x for x in self._active_wip if x not in to_remove]

    def _rename_operation(self, oldName, newName):
        """Renames member file from oldName to newName."""
        isSelected = load_order.cached_is_active(oldName)
        if isSelected:
            self.lo_deactivate(oldName, doSave=False) # will save later
        super(ModInfos, self)._rename_operation(oldName, newName)
        # rename in load order caches
        oldIndex = self._lo_wip.index(oldName)
        self._lo_caches_remove_mods([oldName])
        self._lo_wip.insert(oldIndex, newName)
        if isSelected: self.lo_activate(newName, doSave=False)
        # Save to disc (load order and plugins.txt)
        self.cached_lo_save_all()

    def _get_rename_paths(self, oldName, newName):
        renames = super(ModInfos, self)._get_rename_paths(oldName, newName)
        if self[oldName].isGhost:
            renames[0] = (renames[0][0], renames[0][1] + u'.ghost')
        return renames

    #--Delete
    def files_to_delete(self, filenames, **kwargs):
        for f in set(filenames):
            if f.s in bush.game.masterFiles:
                if kwargs.pop('raise_on_master_deletion', True):
                    raise BoltError(
                        u"Cannot delete the game's master file(s).")
                else:
                    filenames.remove(f)
        self.lo_deactivate(filenames, doSave=False)
        return super(ModInfos, self).files_to_delete(filenames)

    def delete_refresh(self, deleted, paths_to_keys, check_existence,
                       _in_refresh=False):
        # adapted from refresh() (avoid refreshing from the data directory)
        deleted = super(ModInfos, self).delete_refresh(deleted, paths_to_keys,
                                                       check_existence)
        if not deleted: return
        # temporarily track deleted mods so BAIN can update its UI
        if _in_refresh: return
        self._lo_caches_remove_mods(deleted)
        self.cached_lo_save_all()
        self._refreshBadNames()
        self._reset_info_sets()
        self._refreshMissingStrings()
        self._refreshMergeable()

    def _additional_deletes(self, fileInfo, toDelete):
        super(ModInfos, self)._additional_deletes(fileInfo, toDelete)
        # Add ghosts - the file may exist in both states (bug, or user mistake)
        toDelete.append(self.store_dir.join(fileInfo.name + u'.ghost'))

    def move_info(self, fileName, destDir):
        """Moves member file to destDir."""
        self.lo_deactivate(fileName, doSave=False)
        FileInfos.move_info(self, fileName, destDir)

    def move_infos(self, sources, destinations, window, bash_frame):
        moved = super(ModInfos, self).move_infos(sources, destinations, window,
                                                 bash_frame)
        self.refresh() # yak, it should have an "added" parameter
        bash_frame.warn_corrupted(warn_saves=False)
        return moved

    def get_hide_dir(self, name):
        dest_dir =self.hidden_dir
        #--Use author subdirectory instead?
        mod_author = self[name].header.author
        if mod_author:
            authorDir = dest_dir.join(mod_author)
            if authorDir.isdir():
                return authorDir
        #--Use group subdirectory instead?
        file_group = self.table.getItem(name, 'group')
        if file_group:
            groupDir = dest_dir.join(file_group)
            if groupDir.isdir():
                return groupDir
        return dest_dir

    #--Mod info/modify --------------------------------------------------------
    def getVersion(self, fileName):
        """Extracts and returns version number for fileName from header.hedr.description."""
        if not fileName in self.data or not self.data[fileName].header:
            return ''
        maVersion = reVersion.search(self[fileName].header.description)
        return (maVersion and maVersion.group(2)) or u''

    def getVersionFloat(self,fileName):
        """Extracts and returns version number for fileName from header.hedr.description."""
        version = self.getVersion(fileName)
        maVersion = re.search(ur'(\d+\.?\d*)',version,flags=re.U)
        if maVersion:
            return float(maVersion.group(1))
        else:
            return 0

    #--Oblivion 1.1/SI Swapping -----------------------------------------------
    def _setOblivionVersions(self):
        """Set current (and available) master game esm(s) - oblivion only."""
        self.voAvailable.clear()
        for name,info in self.iteritems():
            maOblivion = reOblivion.match(name.s)
            if maOblivion and info.size in self.size_voVersion:
                self.voAvailable.add(self.size_voVersion[info.size])
        if self.masterName in self:
            self.voCurrent = self.size_voVersion.get(
                self[self.masterName].size, None)
        else: self.voCurrent = None # just in case

    def _retry(self, old, new):
        return balt.askYes(self,
            _(u'Bash encountered an error when renaming %s to %s.') + u'\n\n' +
            _(u'The file is in use by another process such as TES4Edit.') +
            u'\n' + _(u'Please close the other program that is accessing %s.')
            + u'\n\n' + _(u'Try again?') % (old.s, new.s, old.s),
            _(u'File in use'))

    def _get_version_paths(self, newVersion):
        baseName = self.masterName # Oblivion.esm, say it's currently SI one
        newSize = self.version_voSize[newVersion]
        oldSize = self[baseName].size
        if newSize == oldSize: return None, None
        if oldSize not in self.size_voVersion:
            raise StateError(u"Can't match current main ESM to known version.")
        oldName = GPath( # Oblivion_SI.esm: we will rename Oblivion.esm to this
            baseName.sbody + u'_' + self.size_voVersion[oldSize] + u'.esm')
        if self.store_dir.join(oldName).exists():
            raise StateError(u"Can't swap: %s already exists." % oldName)
        newName = GPath(baseName.sbody + u'_' + newVersion + u'.esm')
        if newName not in self.data:
            raise StateError(u"Can't swap: %s doesn't exist." % newName)
        return newName, oldName

    def setOblivionVersion(self,newVersion):
        """Swaps Oblivion.esm to to specified version."""
        # if new version is u'1.1' then newName is Path(Oblivion_1.1.esm)
        newName, oldName = self._get_version_paths(newVersion)
        if newName is None: return
        newInfo = self[newName]
        #--Rename
        baseInfo = self[self.masterName]
        master_time = baseInfo.mtime
        new_info_time = newInfo.mtime
        is_master_active = load_order.cached_is_active(self.masterName)
        is_new_info_active = load_order.cached_is_active(newName)
        # can't use ModInfos rename cause it will mess up the load order
        rename_operation = super(ModInfos, self)._rename_operation
        first_try = True
        while first_try or (werr.errno == errno.EACCES and
                self._retry(baseInfo.getPath(), self.store_dir.join(oldName))):
            first_try = False
            try:
                rename_operation(self.masterName, oldName)
            except OSError as werr: # can only occur if SHFileOperation
                # isn't called, yak - file operation API badly needed
                continue
            except CancelError:
                return
            break
        else:
            raise
        first_try = True
        while first_try or (werr.errno == errno.EACCES and
                self._retry(newInfo.getPath(), baseInfo.getPath())):
            first_try = False
            try:
                rename_operation(newName, self.masterName)
            except OSError as werr:
                continue
            except CancelError:
                #Undo any changes
                rename_operation(oldName, self.masterName)
                return
            break
        else:
            #Undo any changes
            rename_operation(oldName, self.masterName)
            raise
        # set mtimes to previous respective values
        self[self.masterName].setmtime(master_time)
        self[oldName].setmtime(new_info_time)
        oldIndex = self._lo_wip.index(newName)
        self._lo_caches_remove_mods([newName])
        self._lo_wip.insert(oldIndex, oldName)
        def _activate(active, mod):
            if active: self[mod].setGhost(False) # needed if autoGhost is False
            (self.lo_activate if active else self.lo_deactivate)(mod,
                                                                 doSave=False)
        _activate(is_new_info_active, oldName)
        _activate(is_master_active, self.masterName)
        # Save to disc (load order and plugins.txt)
        self.cached_lo_save_all() # sets ghost as needed iff autoGhost is True
        self.voCurrent = newVersion

    def swapPluginsAndMasterVersion(self, arcSaves, newSaves):
    # does not really belong here, but then where ?
        """Save current plugins into arcSaves directory, load plugins from
        newSaves directory and set oblivion version."""
        arcPath, newPath = (dirs['saveBase'].join(saves) for saves in
                            (arcSaves, newSaves))
        load_order.swap(arcPath, newPath)
        # Swap Oblivion version to memorized version
        voNew = saveInfos.profiles.setItemDefault(newSaves, 'vOblivion',
                                                  self.voCurrent)
        if voNew in self.voAvailable: self.setOblivionVersion(voNew)

#------------------------------------------------------------------------------
class SaveInfos(FileInfos):
    """SaveInfo collection. Represents save directory and related info."""
    _bain_notify = False
    bak_file_pattern = re.compile(ur'(quick|auto)save(\.bak)+', re.I | re.U)

    def _setLocalSaveFromIni(self):
        """Read the current save profile from the oblivion.ini file and set
        local save attribute to that value."""
        # saveInfos singleton is constructed in InitData after bosh.oblivionIni
        self.localSave = oblivionIni.getSetting(
            bush.game.saveProfilesKey[0], bush.game.saveProfilesKey[1],
            u'Saves\\')
        # Hopefully will solve issues with unicode usernames # TODO(ut) test
        self.localSave = decode(self.localSave) # encoding = 'cp1252' ?

    def __init__(self):
        _ext = re.escape(bush.game.ess.ext)
        self.__class__.file_pattern = re.compile(
            ur'((quick|auto)save(\.bak)+|(' + # quick or auto save.bak(.bak...)
            _ext + ur'|' + _ext[:-1] + ur'r' + ur'))$', # enabled/disabled save
            re.I | re.U)
        self.localSave = u'Saves\\'
        self._setLocalSaveFromIni()
        super(SaveInfos, self).__init__(dirs['saveBase'].join(self.localSave),
                                        factory=SaveInfo)
        # Save Profiles database
        self.profiles = bolt.Table(bolt.PickleDict(
            dirs['saveBase'].join(u'BashProfiles.dat')))

    @property
    def bash_dir(self): return self.store_dir.join(u'Bash')

    def refresh(self, refresh_infos=True, booting=False):
        self._refreshLocalSave()
        return refresh_infos and FileInfos.refresh(self, booting=booting)

    def _additional_deletes(self, fileInfo, toDelete):
        toDelete.extend(CoSaves.getPaths(fileInfo.getPath()))
        # now add backups and cosaves backups
        super(SaveInfos, self)._additional_deletes(fileInfo, toDelete)

    def _get_rename_paths(self, oldName, newName):
        renames = [tuple(map(self.store_dir.join, (oldName, newName)))]
        renames.extend(CoSaves.get_new_paths(*renames[0]))
        return renames

    def copy_info(self, fileName, destDir, destName=empty_path, set_mtime=None):
        """Copies savefile and associated cosaves file(s)."""
        super(SaveInfos, self).copy_info(fileName, destDir, destName, set_mtime)
        CoSaves(self.store_dir, fileName).copy(destDir, destName or fileName)

    def move_infos(self, sources, destinations, window, bash_frame):
        # CoSaves sucks - operations should be atomic
        moved = super(SaveInfos, self).move_infos(sources, destinations,
                                                  window, bash_frame)
        for s, d in zip(sources, destinations):
            if d.tail in moved: CoSaves(s).move(d)
        for d in moved:
            try:
                self.new_info(d, notify_bain=True)
            except FileError:
                pass # will warn below
        bash_frame.warn_corrupted(warn_mods=False, warn_strings=False)
        return moved

    def move_info(self, fileName, destDir):
        """Moves member file to destDir. Will overwrite!"""
        FileInfos.move_info(self, fileName, destDir)
        CoSaves(self.store_dir, fileName).move(destDir, fileName)

    #--Local Saves ------------------------------------------------------------
    @staticmethod
    def getLocalSaveDirs():
        """Returns a list of possible local save directories, NOT including the base directory."""
        baseSaves = dirs['saveBase'].join(u'Saves')
        if baseSaves.exists():
            localSaveDirs = [x for x in baseSaves.list() if (x != u'Bash' and baseSaves.join(x).isdir())]
            # Filter out non-encodable names
            bad = set()
            for folder in localSaveDirs:
                try:
                    folder.s.encode('cp1252')
                except UnicodeEncodeError:
                    bad.add(folder)
            localSaveDirs = [x for x in localSaveDirs if x not in bad]
        else:
            localSaveDirs = []
        localSaveDirs.sort()
        return localSaveDirs

    def _refreshLocalSave(self):
        """Refreshes self.localSave and self.dir."""
        #--self.localSave is NOT a Path object.
        localSave = self.localSave
        self._setLocalSaveFromIni()
        if localSave == self.localSave: return # no change
        self.table.save()
        self._initDB(dirs['saveBase'].join(self.localSave))

    def setLocalSave(self, localSave, refreshSaveInfos=True):
        """Sets SLocalSavePath in Oblivion.ini."""
        self.table.save()
        if not oblivionIni.ask_create_target_ini(msg=_(
                u'Setting the save profile is done by editing the game ini.')):
            return
        self.localSave = localSave
        oblivionIni.saveSetting(bush.game.saveProfilesKey[0],
                                bush.game.saveProfilesKey[1],
                                localSave)
        self._initDB(dirs['saveBase'].join(self.localSave))
        if refreshSaveInfos: self.refresh()

    #--Enabled ----------------------------------------------------------------
    @staticmethod
    def is_save_enabled(fileName):
        """True if fileName is enabled."""
        return fileName.cext == bush.game.ess.ext

    def enable(self,fileName,value=True):
        """Enables file by changing extension to 'ess' (True) or 'esr' (False)."""
        enabled = self.is_save_enabled(fileName)
        if value == enabled or re.match(u'(autosave|quicksave)', fileName.s,
                                          re.I | re.U):
            return fileName
        newName = fileName.root + (
            bush.game.ess.ext if value else fileName.ext[:-1] + u'r')
        try:
            self.rename_info(fileName, newName)
            return newName
        except (CancelError, OSError, IOError):
            return fileName

#------------------------------------------------------------------------------
from . import bsa_files

class BSAInfos(FileInfos):
    """BSAInfo collection. Represents bsa files in game's Data directory."""

    def __init__(self):
        self.__class__.file_pattern = re.compile(
            ur'\.' + bush.game.bsa_extension + ur'$', re.I | re.U)
        _bsa_type = bsa_files.get_bsa_type(bush.game.fsName)

        class BSAInfo(FileInfo, _bsa_type):
            _default_mtime = time.mktime(
                time.strptime(u'01-01-2006 00:00:00', u'%m-%d-%Y %H:%M:%S'))

            def __init__(self, fullpath, load_cache=False):
                try:  # Never load_cache for memory reasons - let it be
                    # loaded as needed
                    super(BSAInfo, self).__init__(fullpath, load_cache=False)
                except BSAError as e:
                    raise FileError, (GPath(fullpath).tail,
                                      e.__class__.__name__ + u' ' +
                                      e.message), \
                        sys.exc_info()[2]
                self._reset_bsa_mtime()

            def getFileInfos(self):
                return bsaInfos

            def do_update(self):
                changed = super(BSAInfo, self).do_update()
                self._reset_bsa_mtime()
                return changed

            def readHeader(self):  # just reset the cache
                self._assets = self.__class__._assets

            def _reset_bsa_mtime(self):
                if bush.game.allow_reset_bsa_timestamps and inisettings[
                    'ResetBSATimestamps']:
                    if self._file_mod_time != self._default_mtime:
                        self.setmtime(self._default_mtime)

        super(BSAInfos, self).__init__(dirs['mods'], factory=BSAInfo)

    @property
    def bash_dir(self): return dirs['modsBash'].join(u'BSA Data')

#------------------------------------------------------------------------------
class PeopleData(DataStore):
    """Data for a People UIList. Built on a PickleDict."""
    def __init__(self):
        self.dictFile = bolt.PickleDict(dirs['saveBase'].join(u'People.dat'))
        self.data = self.dictFile.data
        self.hasChanged = False ##: move to bolt.PickleDict
        self.loaded = False

    def setChanged(self,hasChanged=True):
        """Mark as having changed."""
        self.hasChanged = hasChanged

    def refresh(self):
        """Refresh data."""
        if self.loaded:
            return False
        else:
            self.dictFile.load()
            self.loaded = True
            return True

    def save(self):
        """Saves to pickle file."""
        if self.hasChanged:
            self.dictFile.save()
            self.hasChanged = False

    def delete(self, keys, **kwargs):
        """Delete entry."""
        for key in keys: del self[key]
        self.hasChanged = True

    def delete_refresh(self, deleted, deleted2, check_existence): pass

    #--Operations
    def loadText(self,path):
        """Enter info from text file."""
        newNames, name, buff = set(), None, None
        with path.open('r') as ins:
            reName = re.compile(ur'==([^=]+)=*$',re.U)
            for line in ins:
                maName = reName.match(line)
                if not maName:
                    if buff: buff.write(line)
                    continue
                if name:
                    self[name] = (time.time(), 0, buff.getvalue().strip())
                    newNames.add(name)
                    buff.close()
                    buff = None
                name = maName.group(1).strip()
                if name: buff = sio()
        if newNames: self.setChanged()
        return newNames

    def dumpText(self,path,names):
        """Dump to text file."""
        with path.open('w',encoding='utf-8-sig') as out:
            for name in sorted(names,key=string.lower):
                out.write(u'== %s %s\n' % (name,u'='*(75-len(name))))
                out.write(self[name][2].strip())
                out.write(u'\n\n')

#------------------------------------------------------------------------------
class ScreensData(DataStore):
    reImageExt = re.compile(
        ur'\.(' + ur'|'.join(ext[1:] for ext in imageExts) + ur')$',
        re.I | re.U)

    def __init__(self):
        self.store_dir = dirs['app']
        self.data = {} #--data[Path] = (ext,mtime)

    def refresh(self):
        """Refresh list of screenshots."""
        self.store_dir = dirs['app']
        ssBase = GPath(oblivionIni.getSetting(
            u'Display', u'SScreenShotBaseName', u'ScreenShot'))
        if ssBase.head:
            self.store_dir = self.store_dir.join(ssBase.head)
        newData = {}
        #--Loop over files in directory
        for fileName in self.store_dir.list():
            filePath = self.store_dir.join(fileName)
            maImageExt = self.reImageExt.search(fileName.s)
            if maImageExt and filePath.isfile():
                newData[fileName] = (maImageExt.group(1).lower(),filePath.mtime)
        changed = (self.data != newData)
        self.data = newData
        return changed

    def files_to_delete(self, filenames, **kwargs):
        toDelete = [self.store_dir.join(screen) for screen in filenames]
        return toDelete, None

    def delete_refresh(self, deleted, deleted2, check_existence):
        for item in deleted:
            if not item.exists(): del self[item.tail]

    def _rename_operation(self, oldName, newName):
        super(ScreensData, self)._rename_operation(oldName, newName)
        self[newName] = self[oldName]
        del self[oldName]

#------------------------------------------------------------------------------
from . import converters
from .converters import InstallerConverter
# Hack below needed as older Converters.dat expect bosh.InstallerConverter
# See InstallerConverter.__reduce__()
# noinspection PyRedeclaration
class InstallerConverter(InstallerConverter): pass
# same hack for Installers.dat...
from .bain import InstallerArchive, InstallerMarker, InstallerProject
# noinspection PyRedeclaration
class InstallerArchive(InstallerArchive): pass
# noinspection PyRedeclaration
class InstallerMarker(InstallerMarker): pass
# noinspection PyRedeclaration
class InstallerProject(InstallerProject): pass

# Initialization --------------------------------------------------------------
from ..env import get_personal_path, get_local_app_data_path

def getPersonalPath(bash_ini_, my_docs_path):
    #--Determine User folders from Personal and Local Application Data directories
    #  Attempt to pull from, in order: Command Line, Ini, win32com, Registry
    if my_docs_path:
        my_docs_path = GPath(my_docs_path)
        sErrorInfo = _(u"Folder path specified on command line (-p)")
    elif bash_ini_ and bash_ini_.has_option(u'General', u'sPersonalPath') and \
            not bash_ini_.get(u'General', u'sPersonalPath') == u'.':
        my_docs_path = GPath(bash_ini_.get('General', 'sPersonalPath').strip())
        sErrorInfo = _(
            u"Folder path specified in bash.ini (%s)") % u'sPersonalPath'
    else:
        my_docs_path, sErrorInfo = get_personal_path()
    #  If path is relative, make absolute
    if not my_docs_path.isabs():
        my_docs_path = dirs['app'].join(my_docs_path)
    #  Error check
    if not my_docs_path.exists():
        raise BoltError(u"Personal folder does not exist.\n"
                        u"Personal folder: %s\nAdditional info:\n%s"
                        % (my_docs_path.s, sErrorInfo))
    return my_docs_path

def getLocalAppDataPath(bash_ini_, app_data_local_path):
    #--Determine User folders from Personal and Local Application Data directories
    #  Attempt to pull from, in order: Command Line, Ini, win32com, Registry
    if app_data_local_path:
        app_data_local_path = GPath(app_data_local_path)
        sErrorInfo = _(u"Folder path specified on command line (-l)")
    elif bash_ini_ and bash_ini_.has_option(u'General', u'sLocalAppDataPath') and not bash_ini_.get(u'General', u'sLocalAppDataPath') == u'.':
        app_data_local_path = GPath(bash_ini_.get(u'General', u'sLocalAppDataPath').strip())
        sErrorInfo = _(u"Folder path specified in bash.ini (%s)") % u'sLocalAppDataPath'
    else:
        app_data_local_path, sErrorInfo = get_local_app_data_path()
    #  If path is relative, make absolute
    if not app_data_local_path.isabs():
        app_data_local_path = dirs['app'].join(app_data_local_path)
    #  Error check
    if not app_data_local_path.exists():
        raise BoltError(u"Local AppData folder does not exist.\nLocal AppData folder: %s\nAdditional info:\n%s"
                        % (app_data_local_path.s, sErrorInfo))
    return app_data_local_path

def getOblivionModsPath(bash_ini_):
    if bash_ini_ and bash_ini_.has_option(u'General', u'sOblivionMods'):
        ob_mods_path = GPath(bash_ini_.get(u'General', u'sOblivionMods').strip())
        src = [u'[General]', u'sOblivionMods']
    else:
        ob_mods_path = GPath(GPath(u'..').join(u'%s Mods' % bush.game.fsName))
        src = u'Relative Path'
    if not ob_mods_path.isabs(): ob_mods_path = dirs['app'].join(ob_mods_path)
    return ob_mods_path, src

def getBainDataPath(bash_ini_):
    if bash_ini_ and bash_ini_.has_option(u'General', u'sInstallersData'):
        idata_path = GPath(bash_ini_.get(u'General', u'sInstallersData').strip())
        src = [u'[General]', u'sInstallersData']
        if not idata_path.isabs(): idata_path = dirs['app'].join(idata_path)
    else:
        idata_path = dirs['installers'].join(u'Bash')
        src = u'Relative Path'
    return idata_path, src

def getBashModDataPath(bash_ini_):
    if bash_ini_ and bash_ini_.has_option(u'General', u'sBashModData'):
        mod_data_path = GPath(bash_ini_.get(u'General', u'sBashModData').strip())
        if not mod_data_path.isabs():
            mod_data_path = dirs['app'].join(mod_data_path)
        src = [u'[General]', u'sBashModData']
    else:
        mod_data_path, src = getOblivionModsPath(bash_ini_)
        mod_data_path = mod_data_path.join(u'Bash Mod Data')
    return mod_data_path, src

def getLegacyPath(newPath, oldPath, srcNew=None, srcOld=None):
    return (oldPath,newPath)[newPath.isdir() or not oldPath.isdir()]

def getLegacyPathWithSource(newPath, oldPath, newSrc, oldSrc=None):
    if newPath.isdir() or not oldPath.isdir():
        return newPath, newSrc
    else:
        return oldPath, oldSrc

from ..env import test_permissions # CURRENTLY DOES NOTHING !
def initDirs(bashIni_, personal, localAppData):
    #--Mopy directories
    dirs['mopy'] = bolt.Path.getcwd().root
    dirs['bash'] = dirs['mopy'].join(u'bash')
    dirs['compiled'] = dirs['bash'].join(u'compiled')
    dirs['l10n'] = dirs['bash'].join(u'l10n')
    dirs['db'] = dirs['bash'].join(u'db')
    dirs['templates'] = dirs['mopy'].join(u'templates')
    dirs['images'] = dirs['bash'].join(u'images')

    #--Oblivion (Application) Directories
    dirs['app'] = bush.gamePath
    dirs['mods'] = dirs['app'].join(u'Data')
    dirs['patches'] = dirs['mods'].join(u'Bash Patches')
    dirs['defaultPatches'] = dirs['mopy'].join(u'Bash Patches', bush.game.fsName)
    dirs['tweaks'] = dirs['mods'].join(u'INI Tweaks')

    #  Personal
    personal = getPersonalPath(bashIni_, personal)
    dirs['saveBase'] = personal.join(u'My Games', bush.game.fsName)

    #  Local Application Data
    localAppData = getLocalAppDataPath(bashIni_, localAppData)
    dirs['userApp'] = localAppData.join(bush.game.fsName)

    # Use local copy of the oblivion.ini if present
    global gameInis
    global oblivionIni
    data_oblivion_ini = dirs['app'].join(bush.game.iniFiles[0])
    use_data_dir = False
    if data_oblivion_ini.exists():
        oblivionIni = OblivionIni(data_oblivion_ini)
        # is bUseMyGamesDirectory set to 0?
        if oblivionIni.getSetting(u'General', u'bUseMyGamesDirectory', u'1') == u'0':
            use_data_dir = True
    if not use_data_dir: # FIXME that's what the code was doing - loaded the ini in saveBase and tried again ??
        # oblivion.ini was not found in the game directory or
        # bUseMyGamesDirectory was not set.  Default to user profile directory
        oblivionIni = OblivionIni(dirs['saveBase'].join(bush.game.iniFiles[0]))
        # is bUseMyGamesDirectory set to 0?
        if oblivionIni.getSetting(u'General', u'bUseMyGamesDirectory', u'1') == u'0':
            use_data_dir = True
    if use_data_dir:
        # Set the save game folder to the Oblivion directory
        dirs['saveBase'] = dirs['app']
        # Set the data folder to sLocalMasterPath
        dirs['mods'] = dirs['app'].join(
            oblivionIni.getSetting(u'General', u'SLocalMasterPath', u'Data'))
        # these are relative to the mods path so they must be updated too
        dirs['patches'] = dirs['mods'].join(u'Bash Patches')
        dirs['tweaks'] = dirs['mods'].join(u'INI Tweaks')
    gameInis = [oblivionIni]
    gameInis.extend(OblivionIni(dirs['saveBase'].join(x)) for x in bush.game.iniFiles[1:])
    #--Mod Data, Installers
    oblivionMods, oblivionModsSrc = getOblivionModsPath(bashIni_)
    dirs['modsBash'], modsBashSrc = getBashModDataPath(bashIni_)
    dirs['modsBash'], modsBashSrc = getLegacyPathWithSource(
        dirs['modsBash'], dirs['app'].join(u'Data', u'Bash'),
        modsBashSrc, u'Relative Path')

    dirs['installers'] = oblivionMods.join(u'Bash Installers')
    dirs['installers'] = getLegacyPath(dirs['installers'],
                                       dirs['app'].join(u'Installers'))

    dirs['bainData'], bainDataSrc = getBainDataPath(bashIni_)

    dirs['bsaCache'] = dirs['bainData'].join(u'BSA Cache')

    dirs['converters'] = dirs['installers'].join(u'Bain Converters')
    dirs['dupeBCFs'] = dirs['converters'].join(u'--Duplicates')
    dirs['corruptBCFs'] = dirs['converters'].join(u'--Corrupt')

    #--Test correct permissions for the directories
    badPermissions = [test_dir for test_dir in dirs.itervalues()
                      if not test_permissions(test_dir)] # DOES NOTHING !!!
    if not test_permissions(oblivionMods):
        badPermissions.append(oblivionMods)
    if badPermissions:
        # Do not have all the required permissions for all directories
        # TODO: make this gracefully degrade.  IE, if only the BAIN paths are
        # bad, just disable BAIN.  If only the saves path is bad, just disable
        # saves related stuff.
        msg = balt.fill(_(u'Wrye Bash cannot access the following paths:'))
        msg += u'\n\n' + u'\n'.join(
            [u' * ' + bad_dir.s for bad_dir in badPermissions]) + u'\n\n'
        msg += balt.fill(_(u'See: "Wrye Bash.html, Installation - Windows Vista/7" for information on how to solve this problem.'))
        raise PermissionError(msg)

    # create bash user folders, keep these in order
    keys = ('modsBash', 'installers', 'converters', 'dupeBCFs', 'corruptBCFs',
            'bainData', 'bsaCache')
    try:
        env.shellMakeDirs([dirs[key] for key in keys])
    except NonExistentDriveError as e:
        # NonExistentDriveError is thrown by shellMakeDirs if any of the
        # directories cannot be created due to residing on a non-existing
        # drive. Find which keys are causing the errors
        badKeys = set()     # List of dirs[key] items that are invalid
        # First, determine which dirs[key] items are causing it
        for key in keys:
            if dirs[key] in e.failed_paths:
                badKeys.add(key)
        # Now, work back from those to determine which setting created those
        msg = _(u'Error creating required Wrye Bash directories.') + u'  ' + _(
            u'Please check the settings for the following paths in your '
            u'bash.ini, the drive does not exist') + u':\n\n'
        relativePathError = []
        if 'modsBash' in badKeys:
            if isinstance(modsBashSrc, list):
                msg += (u' '.join(modsBashSrc) + u'\n    '
                        + dirs['modsBash'].s + u'\n')
            else:
                relativePathError.append(dirs['modsBash'])
        if {'installers', 'converters', 'dupeBCFs', 'corruptBCFs'} & badKeys:
            # All derived from oblivionMods -> getOblivionModsPath
            if isinstance(oblivionModsSrc, list):
                msg += (u' '.join(oblivionModsSrc) + u'\n    '
                        + oblivionMods.s + u'\n')
            else:
                relativePathError.append(oblivionMods)
        if {'bainData', 'bsaCache'} & badKeys:
            # Both derived from 'bainData' -> getBainDataPath
            # Sometimes however, getBainDataPath falls back to oblivionMods,
            # So check to be sure we haven't already added a message about that
            if bainDataSrc != oblivionModsSrc:
                if isinstance(bainDataSrc, list):
                    msg += (u' '.join(bainDataSrc) + u'\n    '
                            + dirs['bainData'].s + u'\n')
                else:
                    relativePathError.append(dirs['bainData'])
        if relativePathError:
            msg += u'\n' + _(u'A path error was the result of relative paths.')
            msg += u'  ' + _(u'The following paths are causing the errors, '
                             u'however usually a relative path should be fine.')
            msg += u'  ' + _(u'Check your setup to see if you are using '
                             u'symbolic links or NTFS Junctions') + u':\n\n'
            msg += u'\n'.join([u'%s' % x for x in relativePathError])
        raise BoltError(msg)

    # Setup LOOT API, needs to be done after the dirs are initialized
    global configHelpers
    configHelpers = ConfigHelpers()

def initDefaultTools():
    #-- Other tool directories
    #   First to default path
    pf = [GPath(u'C:\\Program Files'),GPath(u'C:\\Program Files (x86)')]
    def pathlist(*args): return [x.join(*args) for x in pf]

    # BOSS can be in any number of places.
    # Detect locally installed (into game folder) BOSS
    if dirs['app'].join(u'BOSS', u'BOSS.exe').exists():
        tooldirs['boss'] = dirs['app'].join(u'BOSS').join(u'BOSS.exe')
    else:
        tooldirs['boss'] = GPath(u'C:\\**DNE**')
        # Detect globally installed (into Program Files) BOSS
        path_in_registry = env.get_registry_path(u'Boss', u'Installed Path',
                                                 u'BOSS.exe')
        if path_in_registry:
            tooldirs['boss'] = path_in_registry

    tooldirs['Tes4FilesPath'] = dirs['app'].join(u'Tools', u'TES4Files.exe')
    tooldirs['Tes4EditPath'] = dirs['app'].join(u'TES4Edit.exe')
    tooldirs['Tes5EditPath'] = dirs['app'].join(u'TES5Edit.exe')
    tooldirs['SSEEditPath'] = dirs['app'].join(u'SSEEdit.exe')
    tooldirs['Fo4EditPath'] = dirs['app'].join(u'FO4Edit.exe')
    tooldirs['Tes4LodGenPath'] = dirs['app'].join(u'TES4LodGen.exe')
    tooldirs['Tes4GeckoPath'] = dirs['app'].join(u'Tes4Gecko.jar')
    tooldirs['Tes5GeckoPath'] = pathlist(u'Dark Creations',u'TESVGecko',u'TESVGecko.exe')
    tooldirs['OblivionBookCreatorPath'] = dirs['mods'].join(u'OblivionBookCreator.jar')
    tooldirs['NifskopePath'] = pathlist(u'NifTools',u'NifSkope',u'Nifskope.exe')
    tooldirs['BlenderPath'] = pathlist(u'Blender Foundation',u'Blender',u'blender.exe')
    tooldirs['GmaxPath'] = GPath(u'C:\\GMAX').join(u'gmax.exe')
    tooldirs['MaxPath'] = pathlist(u'Autodesk',u'3ds Max 2010',u'3dsmax.exe')
    tooldirs['MayaPath'] = undefinedPath
    tooldirs['PhotoshopPath'] = pathlist(u'Adobe',u'Adobe Photoshop CS3',u'Photoshop.exe')
    tooldirs['GIMP'] = pathlist(u'GIMP-2.0',u'bin',u'gimp-2.6.exe')
    tooldirs['ISOBL'] = dirs['app'].join(u'ISOBL.exe')
    tooldirs['ISRMG'] = dirs['app'].join(u'Insanitys ReadMe Generator.exe')
    tooldirs['ISRNG'] = dirs['app'].join(u'Random Name Generator.exe')
    tooldirs['ISRNPCG'] = dirs['app'].join(u'Random NPC.exe')
    tooldirs['NPP'] = pathlist(u'Notepad++',u'notepad++.exe')
    tooldirs['Fraps'] = GPath(u'C:\\Fraps').join(u'Fraps.exe')
    tooldirs['Audacity'] = pathlist(u'Audacity',u'Audacity.exe')
    tooldirs['Artweaver'] = pathlist(u'Artweaver 1.0',u'Artweaver.exe')
    tooldirs['DDSConverter'] = pathlist(u'DDS Converter 2',u'DDS Converter 2.exe')
    tooldirs['PaintNET'] = pathlist(u'Paint.NET',u'PaintDotNet.exe')
    tooldirs['Milkshape3D'] = pathlist(u'MilkShape 3D 1.8.4',u'ms3d.exe')
    tooldirs['Wings3D'] = pathlist(u'wings3d_1.2',u'Wings3D.exe')
    tooldirs['BSACMD'] = pathlist(u'BSACommander',u'bsacmd.exe')
    tooldirs['MAP'] = dirs['app'].join(u'Modding Tools', u'Interactive Map of Cyrodiil and Shivering Isles 3.52', u'Mapa v 3.52.exe')
    tooldirs['OBMLG'] = dirs['app'].join(u'Modding Tools', u'Oblivion Mod List Generator', u'Oblivion Mod List Generator.exe')
    tooldirs['OBFEL'] = pathlist(u'Oblivion Face Exchange Lite',u'OblivionFaceExchangeLite.exe')
    tooldirs['ArtOfIllusion'] = pathlist(u'ArtOfIllusion',u'Art of Illusion.exe')
    tooldirs['ABCAmberAudioConverter'] = pathlist(u'ABC Amber Audio Converter',u'abcaudio.exe')
    tooldirs['GimpShop'] = pathlist(u'GIMPshop',u'bin',u'gimp-2.2.exe')
    tooldirs['PixelStudio'] = pathlist(u'Pixel',u'Pixel.exe')
    tooldirs['TwistedBrush'] = pathlist(u'Pixarra',u'TwistedBrush Open Studio',u'tbrush_open_studio.exe')
    tooldirs['PhotoScape'] = pathlist(u'PhotoScape',u'PhotoScape.exe')
    tooldirs['Photobie'] = pathlist(u'Photobie',u'Photobie.exe')
    tooldirs['PhotoFiltre'] = pathlist(u'PhotoFiltre',u'PhotoFiltre.exe')
    tooldirs['PaintShopPhotoPro'] = pathlist(u'Corel',u'Corel PaintShop Photo Pro',u'X3',u'PSPClassic',u'Corel Paint Shop Pro Photo.exe')
    tooldirs['Dogwaffle'] = pathlist(u'project dogwaffle',u'dogwaffle.exe')
    tooldirs['GeneticaViewer'] = pathlist(u'Spiral Graphics',u'Genetica Viewer 3',u'Genetica Viewer 3.exe')
    tooldirs['LogitechKeyboard'] = pathlist(u'Logitech',u'GamePanel Software',u'G-series Software',u'LGDCore.exe')
    tooldirs['AutoCad'] = pathlist(u'Autodesk Architectural Desktop 3',u'acad.exe')
    tooldirs['Genetica'] = pathlist(u'Spiral Graphics',u'Genetica 3.5',u'Genetica.exe')
    tooldirs['IrfanView'] = pathlist(u'IrfanView',u'i_view32.exe')
    tooldirs['XnView'] = pathlist(u'XnView',u'xnview.exe')
    tooldirs['FastStone'] = pathlist(u'FastStone Image Viewer',u'FSViewer.exe')
    tooldirs['Steam'] = pathlist(u'Steam',u'steam.exe')
    tooldirs['EVGAPrecision'] = pathlist(u'EVGA Precision',u'EVGAPrecision.exe')
    tooldirs['IcoFX'] = pathlist(u'IcoFX 1.6',u'IcoFX.exe')
    tooldirs['AniFX'] = pathlist(u'AniFX 1.0',u'AniFX.exe')
    tooldirs['WinMerge'] = pathlist(u'WinMerge',u'WinMergeU.exe')
    tooldirs['FreeMind'] = pathlist(u'FreeMind',u'Freemind.exe')
    tooldirs['MediaMonkey'] = pathlist(u'MediaMonkey',u'MediaMonkey.exe')
    tooldirs['Inkscape'] = pathlist(u'Inkscape',u'inkscape.exe')
    tooldirs['FileZilla'] = pathlist(u'FileZilla FTP Client',u'filezilla.exe')
    tooldirs['RADVideo'] = pathlist(u'RADVideo',u'radvideo.exe')
    tooldirs['EggTranslator'] = pathlist(u'Egg Translator',u'EggTranslator.exe')
    tooldirs['Sculptris'] = pathlist(u'sculptris',u'Sculptris.exe')
    tooldirs['Mudbox'] = pathlist(u'Autodesk',u'Mudbox2011',u'mudbox.exe')
    tooldirs['Tabula'] = dirs['app'].join(u'Modding Tools', u'Tabula', u'Tabula.exe')
    tooldirs['MyPaint'] = pathlist(u'MyPaint',u'mypaint.exe')
    tooldirs['Pixia'] = pathlist(u'Pixia',u'pixia.exe')
    tooldirs['DeepPaint'] = pathlist(u'Right Hemisphere',u'Deep Paint',u'DeepPaint.exe')
    tooldirs['CrazyBump'] = pathlist(u'Crazybump',u'CrazyBump.exe')
    tooldirs['xNormal'] = pathlist(u'Santiago Orgaz',u'xNormal',u'3.17.3',u'x86',u'xNormal.exe')
    tooldirs['SoftimageModTool'] = GPath(u'C:\\Softimage').join(u'Softimage_Mod_Tool_7.5',u'Application',u'bin',u'XSI.bat')
    tooldirs['SpeedTree'] = undefinedPath
    tooldirs['Treed'] = pathlist(u'gile[s]',u'plugins',u'tree[d]',u'tree[d].exe')
    tooldirs['WinSnap'] = pathlist(u'WinSnap',u'WinSnap.exe')
    tooldirs['PhotoSEAM'] = pathlist(u'PhotoSEAM',u'PhotoSEAM.exe')
    tooldirs['TextureMaker'] = pathlist(u'Texture Maker',u'texturemaker.exe')
    tooldirs['MaPZone'] = pathlist(u'Allegorithmic',u'MaPZone 2.6',u'MaPZone2.exe')
    tooldirs['NVIDIAMelody'] = pathlist(u'NVIDIA Corporation',u'Melody',u'Melody.exe')
    tooldirs['WTV'] = pathlist(u'WindowsTextureViewer',u'WTV.exe')
    tooldirs['Switch'] = pathlist(u'NCH Swift Sound',u'Switch',u'switch.exe')
    tooldirs['Freeplane'] = pathlist(u'Freeplane',u'freeplane.exe')

def initDefaultSettings():
    #other settings from the INI:
    inisettings['EnableUnicode'] = False
    if 'steam' in dirs['app'].cs:
        inisettings['SteamInstall'] = True
    else:
        inisettings['SteamInstall'] = False
    inisettings['ScriptFileExt'] = u'.txt'
    inisettings['KeepLog'] = 0
    inisettings['LogFile'] = dirs['mopy'].join(u'bash.log')
    inisettings['ResetBSATimestamps'] = True
    inisettings['EnsurePatchExists'] = True
    inisettings['OblivionTexturesBSAName'] = GPath(u'Oblivion - Textures - Compressed.bsa')
    inisettings['ShowDevTools'] = False
    inisettings['Tes4GeckoJavaArg'] = u'-Xmx1024m'
    inisettings['OblivionBookCreatorJavaArg'] = u'-Xmx1024m'
    inisettings['ShowTextureToolLaunchers'] = True
    inisettings['ShowModelingToolLaunchers'] = True
    inisettings['ShowAudioToolLaunchers'] = True
    inisettings['7zExtraCompressionArguments'] = u''
    inisettings['AutoItemCheck'] = True
    inisettings['SkipHideConfirmation'] = False
    inisettings['SkipResetTimeNotifications'] = False
    inisettings['SoundSuccess'] = GPath(u'')
    inisettings['SoundError'] = GPath(u'')
    inisettings['EnableSplashScreen'] = True
    inisettings['PromptActivateBashedPatch'] = True
    inisettings['WarnTooManyFiles'] = True
    inisettings['SkippedBashInstallersDirs'] = u''

def initOptions(bashIni):
    initDefaultTools()
    initDefaultSettings()

    defaultOptions = {}
    type_key = {str:u's',unicode:u's',list:u's',int:u'i',bool:u'b',bolt.Path:u's'}
    allOptions = [tooldirs, inisettings]
    unknownSettings = {}
    for settingsDict in allOptions:
        for defaultKey,defaultValue in settingsDict.iteritems():
            settingType = type(defaultValue)
            readKey = type_key[settingType] + defaultKey
            defaultOptions[readKey.lower()] = (defaultKey,settingsDict)

    # if bash.ini exists update the settings from there:
    if bashIni:
        for section in bashIni.sections():
            options = bashIni.items(section)
            for key,value in options:
                usedKey, usedSettings = defaultOptions.get(key,(key[1:],unknownSettings))
                defaultValue = usedSettings.get(usedKey,u'')
                settingType = type(defaultValue)
                if settingType in (bolt.Path,list):
                    if value == u'.': continue
                    value = GPath(value)
                    if not value.isabs():
                        value = dirs['app'].join(value)
                elif settingType is bool:
                    if value == u'.': continue
                    value = bashIni.getboolean(section,key)
                else:
                    value = settingType(value)
                compDefaultValue = defaultValue
                compValue = value
                if settingType in (str,unicode):
                    compDefaultValue = compDefaultValue.lower()
                    compValue = compValue.lower()
                    if compValue in (_(u'-option(s)'),_(u'tooltip text'),_(u'default')):
                        compValue = compDefaultValue
                if settingType is list:
                    if compValue != compDefaultValue[0]:
                        usedSettings[usedKey] = value
                elif compValue != compDefaultValue:
                    usedSettings[usedKey] = value

    tooldirs['Tes4ViewPath'] = tooldirs['Tes4EditPath'].head.join(u'TES4View.exe')
    tooldirs['Tes4TransPath'] = tooldirs['Tes4EditPath'].head.join(u'TES4Trans.exe')

def initLogFile():
    if inisettings['KeepLog'] == 0: return
    with inisettings['LogFile'].open('a', encoding='utf-8-sig') as log:
        log.write(_(u'%s Wrye Bash ini file read, Keep Log level: %d, '
                    u'initialized.') % (
                  bolt.timestamp(), inisettings['KeepLog']) + u'\r\n')

def initBosh(personal=empty_path, localAppData=empty_path, bashIni=None):
    #--Bash Ini
    if not bashIni: bashIni = bass.GetBashIni()
    initDirs(bashIni, personal, localAppData)
    load_order.initialize_load_order_files()
    initOptions(bashIni)
    try:
        initLogFile()
    except IOError:
        deprint('Error creating log file', traceback=True)
    from .bain import Installer
    Installer.init_bain_dirs()
    if os.name == u'nt': # don't add local directory to binaries on linux
        archives.exe7z = dirs['compiled'].join(archives.exe7z).s

def initSettings(readOnly=False, _dat=u'BashSettings.dat',
                 _bak=u'BashSettings.dat.bak'):
    """Init user settings from files and load the defaults (also in basher)."""

    def _load(dat_file=_dat):
    # bolt.PickleDict.load() handles EOFError, ValueError falling back to bak
        return bolt.Settings( # calls PickleDict.load() and copies loaded data
            bolt.PickleDict(dirs['saveBase'].join(dat_file), readOnly))

    _dat = dirs['saveBase'].join(_dat)
    _bak = dirs['saveBase'].join(_bak)
    def _loadBakOrEmpty(delBackup=False, ignoreBackup=False):
        _dat.remove()
        if delBackup: _bak.remove()
        # bolt machinery will automatically load the backup - bypass it if
        # user did, by temporarily renaming the .bak file
        if ignoreBackup: _bak.moveTo(_bak.s + u'.ignore')
        # load the .bak file, or an empty settings dict saved to disc at exit
        loaded = _load()
        if ignoreBackup: GPath(_bak.s + u'.ignore').moveTo(_bak.s)
        return loaded
    #--Set bass.settings ------------------------------------------------------
    try:
        bass.settings = _load()
    except cPickle.UnpicklingError as err:
        msg = _(
            u"Error reading the Bash Settings database (the error is: '%s'). "
            u"This is probably not recoverable with the current file. Do you "
            u"want to try the backup BashSettings.dat? (It will have all your "
            u"UI choices of the time before last that you used Wrye Bash.")
        usebck = balt.askYes(None, msg % repr(err), _(u"Settings Load Error"))
        if usebck:
            try:
                bass.settings = _loadBakOrEmpty()
            except cPickle.UnpicklingError as err:
                msg = _(
                    u"Error reading the BackupBash Settings database (the "
                    u"error is: '%s'). This is probably not recoverable with "
                    u"the current file. Do you want to delete the corrupted "
                    u"settings and load Wrye Bash without your saved UI "
                    u"settings?. (Otherwise Wrye Bash won't start up)")
                delete = balt.askYes(None, msg % repr(err),
                                     _(u"Settings Load Error"))
                if delete: bass.settings = _loadBakOrEmpty(delBackup=True)
                else:raise
        else:
            msg = _(
                u"Do you want to delete the corrupted settings and load Wrye "
                u"Bash without your saved UI settings?. (Otherwise Wrye Bash "
                u"won't start up)")
            delete = balt.askYes(None, msg, _(u"Settings Load Error"))
            if delete: # ignore bak but don't delete
                bass.settings = _loadBakOrEmpty(ignoreBackup=True)
            else: raise
