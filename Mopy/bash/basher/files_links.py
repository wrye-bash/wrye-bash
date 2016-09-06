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

import re
from .. import bass, balt, bosh, bush, bolt, env
from ..bass import Resources
from ..balt import ItemLink, RadioLink, EnabledLink, ChoiceLink, Link, \
    OneItemLink
from ..bolt import CancelError, SkipError, GPath, formatDate

__all__ = ['Files_SortBy', 'Files_Unhide', 'Files_Open', 'File_Backup',
           'File_Duplicate', 'File_Snapshot', 'File_Hide',
           'File_RevertToBackup', 'File_RevertToSnapshot', 'File_ListMasters',
           'File_Open']

#------------------------------------------------------------------------------
# Files Links -----------------------------------------------------------------
#------------------------------------------------------------------------------
class Files_Open(ItemLink):
    """Opens data directory in explorer."""
    text = _(u'Open...')

    def _initData(self, window, selection):
        super(Files_Open, self)._initData(window, selection)
        self.help = _(u"Open '%s'") % window.data_store.store_dir.tail

    def Execute(self):
        """Handle selection."""
        dir_ = self.window.data_store.store_dir
        dir_.makedirs()
        dir_.start()

class Files_SortBy(RadioLink):
    """Sort files by specified key (sortCol)."""

    def __init__(self, sortCol):
        super(Files_SortBy, self).__init__()
        self.sortCol = sortCol
        self.text = bass.settings['bash.colNames'][sortCol]
        self.help = _(u'Sort by %s') % self.text

    def _check(self): return self.window.sort == self.sortCol

    def Execute(self): self.window.SortItems(self.sortCol, 'INVERT')

class Files_Unhide(ItemLink):
    """Unhide file(s). (Move files back to Data Files or Save directory.)"""
    text = _(u"Unhide...")

    def __init__(self, files_type):
        super(Files_Unhide, self).__init__()
        self.files_type = files_type # yak - move logic to the data model
        self.help = _(u"Unhides hidden %ss.") % files_type

    def Execute(self):
        srcDir = bass.dirs['modsBash'].join(u'Hidden')
        window = self.window
        destDir = None
        if self.files_type == 'mod':
            wildcard = bush.game.displayName+u' '+_(u'Mod Files')+u' (*.esp;*.esm)|*.esp;*.esm'
            destDir = window.data_store.store_dir
        elif self.files_type == 'save':
            wildcard = bush.game.displayName+u' '+_(u'Save files')+u' (*.ess)|*.ess'
            srcDir = window.data_store.bash_dir.join(u'Hidden')
            destDir = window.data_store.store_dir
        elif self.files_type == 'installer':
            wildcard = bush.game.displayName+u' '+_(u'Mod Archives')+u' (*.7z;*.zip;*.rar)|*.7z;*.zip;*.rar'
            destDir = bass.dirs['installers']
            srcPaths = self._askOpenMulti(
                title=_(u'Unhide files:'), defaultDir=srcDir,
                defaultFile=u'.Folder Selection.', wildcard=wildcard)
        else:
            wildcard = u'*.*'
        isSave = (destDir == bosh.saveInfos.store_dir)
        #--File dialog
        srcDir.makedirs()
        if not self.files_type == 'installer':
            srcPaths = self._askOpenMulti(_(u'Unhide files:'),
                                          defaultDir=srcDir, wildcard=wildcard)
        if not srcPaths: return
        #--Iterate over Paths
        srcFiles = []
        destFiles = []
        coSavesMoves = {}
        for srcPath in srcPaths:
            #--Copy from dest directory?
            (newSrcDir,srcFileName) = srcPath.headTail
            if newSrcDir == destDir:
                self._showError(
                    _(u"You can't unhide files from this directory."))
                return
            #--Folder selection?
            if srcFileName.csbody == u'.folder selection':
                if newSrcDir == srcDir:
                    #--Folder selection on the 'Hidden' folder
                    return
                (newSrcDir,srcFileName) = newSrcDir.headTail
                srcPath = srcPath.head
            #--File already unhidden?
            destPath = destDir.join(srcFileName)
            if destPath.exists():
                self._showWarning(_(u"File skipped: %s. File is already "
                                    u"present.") % (srcFileName.s,))
            #--Move it?
            else:
                srcFiles.append(srcPath)
                destFiles.append(destPath)
                if isSave:
                    coSavesMoves[destPath] = bosh.CoSaves(srcPath)
        #--Now move everything at once
        if not srcFiles:
            return
        try:
            env.shellMove(srcFiles, destFiles, parent=window)
            for dest in coSavesMoves:
                coSavesMoves[dest].move(dest)
        except (CancelError,SkipError):
            pass
        Link.Frame.RefreshData()

#------------------------------------------------------------------------------
# File Links ------------------------------------------------------------------
#------------------------------------------------------------------------------
class File_Duplicate(ItemLink):
    """Create a duplicate of the file - mod, save or bsa."""

    def _initData(self, window, selection):
        super(File_Duplicate, self)._initData(window, selection)
        self.text = (_(u'Duplicate'),_(u'Duplicate...'))[len(selection) == 1]
        self.help = _(u"Make a copy of '%s'") % (selection[0])

    _bsaAndVoice = _(u"This mod has an associated archive (%s.bsa) and an "
        u"associated voice directory (Sound\\Voices\\%s), which will not be "
        u"attached to the duplicate mod.") + u'\n\n' + _(u'Note that the BSA '
        u'archive may also contain a voice directory (Sound\\Voices\\%s), '
        u'which would remain detached even if a duplicate archive were also '
        u'created.')
    _bsa = _(u'This mod has an associated archive (%s.bsa), which will not be '
        u'attached to the duplicate mod.') + u'\n\n' + _(u'Note that this BSA '
        u'archive may contain a voice directory (Sound\\Voices\\%s), which '
        u'would remain detached even if a duplicate archive were also created.'
    )
    _voice = _(ur'This mod has an associated voice directory (Sound\Voice\%s),'
        u' which will not be attached to the duplicate mod.')

    def _askResourcesOk(self, fileInfo):
        return bosh.modInfos.askResourcesOk(fileInfo, parent=self.window,
          title=_(u'Duplicate '), bsaAndVoice=self._bsaAndVoice, bsa=self._bsa,
          voice=self._voice)

    @balt.conversation
    def Execute(self):
        dests = []
        fileInfos = self.window.data_store
        for to_duplicate in self.selected:
            fileInfo = fileInfos[to_duplicate]
            #--Mod with resources?
            #--Warn on rename if file has bsa and/or dialog
            if not self._askResourcesOk(fileInfo): continue
            #--Continue copy
            (root, ext) = to_duplicate.rootExt
            if ext.lower() == u'.bak': ext = bush.game.ess.ext
            (destDir, wildcard) = (fileInfo.dir, u'*' + ext)
            destName = self.window.new_path(GPath(root + u' Copy' + ext),
                                            destDir)
            destDir.makedirs()
            if len(self.selected) == 1:
                destPath = self._askSave(
                    title=_(u'Duplicate as:'), defaultDir=destDir,
                    defaultFile=destName.s, wildcard=wildcard)
                if not destPath: return
                destDir, destName = destPath.headTail
            if (destDir == fileInfo.dir) and (destName == to_duplicate):
                self._showError(
                    _(u"Files cannot be duplicated to themselves!"))
                continue
            fileInfos.copy_info(to_duplicate, destDir, destName)
            if fileInfo.isMod():
                fileInfos.cached_lo_insert_after(to_duplicate, destName)
            dests.append(destName)
        if dests:
            if fileInfo.isMod(): fileInfos.cached_lo_save_lo()
            fileInfos.refresh(scanData=False)
            self.window.RefreshUI(refreshSaves=False) #(dup) saves not affected
            self.window.SelectItemsNoCallback(dests)
            self.window.SelectAndShowItem(dests[-1])

class File_Hide(ItemLink):
    """Hide the file. (Move it to Bash/Hidden directory.)"""
    text = _(u'Hide')

    def _initData(self, window, selection):
        super(File_Hide, self)._initData(window, selection)
        self.help = _(u"Move %(filename)s to the Bash/Hidden directory.") % (
            {'filename': selection[0]})

    @balt.conversation
    def Execute(self):
        if not bass.inisettings['SkipHideConfirmation']:
            message = _(u'Hide these files? Note that hidden files are simply moved to the Bash\\Hidden subdirectory.')
            if not self._askYes(message, _(u'Hide Files')): return
        #--Do it
        destRoot = self.window.data_store.bash_dir.join(u'Hidden')
        fileInfos = self.window.data_store
        fileGroups = fileInfos.table.getColumn('group')
        for fileName in self.selected:
            destDir = destRoot
            #--Use author subdirectory instead?
            author = getattr(fileInfos[fileName].header,'author',u'NOAUTHOR') #--Hack for save files.
            authorDir = destRoot.join(author)
            if author and authorDir.isdir():
                destDir = authorDir
            #--Use group subdirectory instead?
            elif fileName in fileGroups:
                groupDir = destRoot.join(fileGroups[fileName])
                if groupDir.isdir():
                    destDir = groupDir
            if not self.window.data_store.moveIsSafe(fileName,destDir):
                message = (_(u'A file named %s already exists in the hidden '
                             u'files directory. Overwrite it?') % fileName.s)
                if not self._askYes(message, _(u'Hide Files')): continue
            #--Do it
            fileInfos.move_info(fileName, destDir)
        #--Refresh stuff
        fileInfos.delete_Refresh(self.selected, check_existence=True)
        self.window.RefreshUI(refreshSaves=True)

class File_ListMasters(OneItemLink):
    """Copies list of masters to clipboard."""
    text = _(u"List Masters...")

    def _initData(self, window, selection):
        super(File_ListMasters, self)._initData(window, selection)
        self.help = _(
            u"Copies list of %(filename)s's masters to the clipboard.") % (
                        {'filename': selection[0]})

    def Execute(self):
        text = bosh.modInfos.getModList(fileInfo=self._selected_info)
        balt.copyToClipboard(text)
        self._showLog(text, title=self._selected_item.s, fixedFont=False,
                      icons=Resources.bashBlue)

class File_Snapshot(ItemLink):
    """Take a snapshot of the file."""
    help = _(u"Creates a snapshot copy of the current mod in a subdirectory (Bash\Snapshots).")

    def _initData(self, window, selection):
        super(File_Snapshot, self)._initData(window, selection)
        self.text = (_(u'Snapshot'),_(u'Snapshot...'))[len(selection) == 1]

    def Execute(self):
        for item in self.selected:
            fileName = GPath(item)
            fileInfo = self.window.data_store[fileName]
            (destDir,destName,wildcard) = fileInfo.getNextSnapshot()
            destDir.makedirs()
            if len(self.selected) == 1:
                destPath = self._askSave(
                    title=_(u'Save snapshot as:'), defaultDir=destDir,
                    defaultFile=destName, wildcard=wildcard)
                if not destPath: return
                (destDir,destName) = destPath.headTail
            #--Extract version number
            fileRoot = fileName.root
            destRoot = destName.root
            fileVersion = bolt.getMatch(re.search(ur'[ _]+v?([\.\d]+)$',fileRoot.s,re.U),1)
            snapVersion = bolt.getMatch(re.search(ur'-[\d\.]+$',destRoot.s,re.U))
            fileHedr = fileInfo.header
            if fileInfo.isMod() and (fileVersion or snapVersion) and bosh.reVersion.search(fileHedr.description):
                if fileVersion and snapVersion:
                    newVersion = fileVersion+snapVersion
                elif snapVersion:
                    newVersion = snapVersion[1:]
                else:
                    newVersion = fileVersion
                newDescription = bosh.reVersion.sub(u'\\1 '+newVersion, fileHedr.description,1)
                fileInfo.writeDescription(newDescription)
                self.window.panel.SetDetails(fileName)
            #--Copy file
            self.window.data_store.copy_info(fileName, destDir, destName)

class File_RevertToSnapshot(OneItemLink): # MODS LINK !
    """Revert to Snapshot."""
    text = _(u'Revert to Snapshot...')
    help = _(u"Revert to a previously created snapshot from the Bash/Snapshots dir.")

    @balt.conversation
    def Execute(self):
        """Revert to Snapshot."""
        fileName = self._selected_item
        #--Snapshot finder
        srcDir = self.window.data_store.bash_dir.join(u'Snapshots')
        wildcard = self._selected_info.getNextSnapshot()[2]
        #--File dialog
        srcDir.makedirs()
        snapPath = self._askOpen(_(u'Revert %s to snapshot:') % fileName.s,
                                 defaultDir=srcDir, wildcard=wildcard,
                                 mustExist=True)
        if not snapPath: return
        snapName = snapPath.tail
        #--Warning box
        message = (_(u"Revert %s to snapshot %s dated %s?") % (
            fileName.s, snapName.s, formatDate(snapPath.mtime)))
        if not self._askYes(message, _(u'Revert to Snapshot')): return
        with balt.BusyCursor():
            destPath = self._selected_info.getPath()
            current_mtime = destPath.mtime
            snapPath.copyTo(destPath)
            self._selected_info.setmtime(current_mtime) # keep load order
            try:
                self.window.data_store.refreshFile(fileName)
            except bosh.FileError:
                balt.showError(self,_(u'Snapshot file is corrupt!'))
                self.window.panel.ClearDetails()
            self.window.RefreshUI(files=[fileName], refreshSaves=False) # don't
            # refresh saves as neither selection state nor load order change

class File_Backup(ItemLink):
    """Backup file."""
    text = _(u'Backup')
    help = _(u"Create a backup of the selected file(s).")

    def Execute(self):
        for item in self.selected:
            fileInfo = self.window.data_store[item]
            fileInfo.makeBackup(True)

class File_Open(ItemLink):
    """Open specified file(s)."""
    text = _(u'Open...')

    def _initData(self, window, selection):
        super(File_Open, self)._initData(window, selection)
        self.help = _(u"Open '%s' with the system's default program.") % selection[
            0] if len(selection) == 1 else _(u'Open the selected files.')

    def Execute(self): self.window.OpenSelected(selected=self.selected)

class File_RevertToBackup(ChoiceLink):
    """Revert to last or first backup."""

    def _initData(self, window, selection):
        super(File_RevertToBackup, self)._initData(window, selection)
        #--Backup Files
        singleSelect = len(selection) == 1
        self.fileInfo = window.data_store[selection[0]]
        backup = self.fileInfo.bashDir.join(u'Backups', self.fileInfo.name)
        firstBackup = backup + u'f'
        #--Backup Item
        _self = self
        class _RevertBackup(EnabledLink):
            text = _(u'Revert to Backup')
            def _enable(self): return singleSelect and backup.exists()
            def Execute(self): return _self.revert(backup)
        #--First Backup item
        class _RevertFirstBackup(EnabledLink):
            text = _(u'Revert to First Backup')
            def _enable(self): return singleSelect and firstBackup.exists()
            def Execute(self): return _self.revert(firstBackup)
        self.extraItems =[_RevertBackup(), _RevertFirstBackup()]

    @balt.conversation
    def revert(self, backup):
        fileInfo = self.fileInfo
        fileName = fileInfo.name
        #--Warning box
        message = _(u"Revert %s to backup dated %s?") % (fileName.s,
            formatDate(backup.mtime))
        if self._askYes(message, _(u'Revert to Backup')):
            with balt.BusyCursor():
                dest = fileInfo.getPath() # care for ghosts !
                current_mtime = dest.mtime
                backup.copyTo(dest)
                fileInfo.setmtime(current_mtime) # do not change load order
                if fileInfo.isEss(): #--Handle CoSave (.pluggy and .obse) files.
                    bosh.CoSaves(backup).copy(dest)
                try:
                    self.window.data_store.refreshFile(fileName)
                except bosh.FileError:
                    self._showError(_(u'Old file is corrupt!'))
                self.window.RefreshUI(files=[fileName], refreshSaves=False)
