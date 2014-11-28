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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2014 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from operator import attrgetter
import re
import time
from .. import balt, bosh, bush, bolt
from . import ListBoxes, bashBlue
from ..balt import _Link, RadioLink, EnabledLink, AppendableLink, ChoiceLink, \
    Link
from ..bolt import CancelError, SkipError, GPath, BoltError
from ..bosh import formatDate

#------------------------------------------------------------------------------
# Files Links -----------------------------------------------------------------
#------------------------------------------------------------------------------
class Files_Open(_Link):
    """Opens data directory in explorer."""
    text = _(u'Open...')

    def _initData(self, window, data):
        super(Files_Open, self)._initData(window, data)
        self.help = _(u"Open '%s'") % window.data.dir.tail

    def Execute(self,event):
        """Handle selection."""
        dir = self.window.data.dir
        dir.makedirs()
        dir.start()

class Files_SortBy(RadioLink):
    """Sort files by specified key (sortCol)."""

    def __init__(self, sortCol, prefix=''):
        super(Files_SortBy, self).__init__()
        self.sortCol = sortCol
        self.sortName = bosh.settings['bash.colNames'][sortCol]
        self.prefix = prefix
        self.text = self.prefix + self.sortName
        self.help = _(u'Sort by %s') % self.sortName

    def _check(self): return self.window.sort == self.sortCol

    def Execute(self,event):
        if hasattr(self, 'gTank'):
            self.gTank.SortItems(self.sortCol,'INVERT')
        else:
            self.window.PopulateItems(self.sortCol,-1)

class Files_Unhide(_Link):
    """Unhide file(s). (Move files back to Data Files or Save directory.)"""
    text = _(u"Unhide...")

    def __init__(self, type_):
        super(Files_Unhide, self).__init__()
        self.type = type_
        self.help = _(u"Unhides hidden %ss.") % self.type

    def Execute(self,event):
        srcDir = bosh.dirs['modsBash'].join(u'Hidden')
        if self.type == 'mod':
            wildcard = bush.game.displayName+u' '+_(u'Mod Files')+u' (*.esp;*.esm)|*.esp;*.esm'
            destDir = self.window.data.dir
        elif self.type == 'save':
            wildcard = bush.game.displayName+u' '+_(u'Save files')+u' (*.ess)|*.ess'
            srcDir = self.window.data.bashDir.join(u'Hidden')
            destDir = self.window.data.dir
        elif self.type == 'installer':
            window = self.gTank
            wildcard = bush.game.displayName+u' '+_(u'Mod Archives')+u' (*.7z;*.zip;*.rar)|*.7z;*.zip;*.rar'
            destDir = bosh.dirs['installers']
            srcPaths = balt.askOpenMulti(window,_(u'Unhide files:'),srcDir, u'.Folder Selection.', wildcard)
        else:
            wildcard = u'*.*'
        isSave = (destDir == bosh.saveInfos.dir)
        #--File dialog
        srcDir.makedirs()
        if not self.type == 'installer':
            window = self.window
            srcPaths = balt.askOpenMulti(window,_(u'Unhide files:'),srcDir, u'', wildcard)
        if not srcPaths: return
        #--Iterate over Paths
        srcFiles = []
        destFiles = []
        coSavesMoves = {}
        for srcPath in srcPaths:
            #--Copy from dest directory?
            (newSrcDir,srcFileName) = srcPath.headTail
            if newSrcDir == destDir:
                balt.showError(window,_(u"You can't unhide files from this directory."))
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
                balt.showWarning(window,_(u"File skipped: %s. File is already present.")
                    % (srcFileName.s,))
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
            balt.shellMove(srcFiles,destFiles,window,False,False,False)
            for dest in coSavesMoves:
                coSavesMoves[dest].move(dest)
        except (CancelError,SkipError):
            pass
        Link.Frame.RefreshData()

#------------------------------------------------------------------------------
# File Links ------------------------------------------------------------------
#------------------------------------------------------------------------------
class File_Delete(_Link):
    """Delete the file and all backups."""
    text = _(u'Delete')

    def _initData(self, window, data):
        super(File_Delete, self)._initData(window, data)
        self.help = _(u"Delete %(filename)s.") % ({'filename': data[0]})

    def Execute(self,event):
        message = [u'',_(u'Uncheck files to skip deleting them if desired.')]
        message.extend(sorted(self.data))
        with ListBoxes(self.window,_(u'Delete Files'),
                     _(u'Delete these files? This operation cannot be undone.'),
                     [message]) as dialog:
            if dialog.ShowModal() == ListBoxes.ID_CANCEL: return
            id = dialog.ids[message[0]]
            checks = dialog.FindWindowById(id)
            if checks:
                for i,mod in enumerate(self.data):
                    if checks.IsChecked(i):
                        try:
                            self.window.data.delete(mod)
                        except BoltError as e:
                            balt.showError(self.window, _(u'%s') % e)
            self.window.RefreshUI()

class File_Duplicate(_Link):
    """Create a duplicate of the file."""

    def _initData(self, window, data):
        super(File_Duplicate, self)._initData(window, data)
        self.text = (_(u'Duplicate'),_(u'Duplicate...'))[len(data) == 1]
        self.help = _(u"Make a copy of '%s'") % (data[0])

    def Execute(self,event):
        data = self.data
        for item in data:
            fileName = GPath(item)
            fileInfos = self.window.data
            fileInfo = fileInfos[fileName]
            #--Mod with resources?
            #--Warn on rename if file has bsa and/or dialog
            if fileInfo.isMod() and tuple(fileInfo.hasResources()) != (False,False):
                hasBsa, hasVoices = fileInfo.hasResources()
                modName = fileInfo.name
                if hasBsa and hasVoices:
                    message = (_(u"This mod has an associated archive (%s.bsa) and an associated voice directory (Sound\\Voices\\%s), which will not be attached to the duplicate mod.")
                               + u'\n\n' +
                               _(u'Note that the BSA archive may also contain a voice directory (Sound\\Voices\\%s), which would remain detached even if a duplicate archive were also created.')
                               ) % (modName.sroot,modName.s,modName.s)
                elif hasBsa:
                    message = (_(u'This mod has an associated archive (%s.bsa), which will not be attached to the duplicate mod.')
                               + u'\n\n' +
                               _(u'Note that this BSA archive may contain a voice directory (Sound\\Voices\\%s), which would remain detached even if a duplicate archive were also created.')
                               ) % (modName.sroot,modName.s)
                else: #hasVoices
                    message = _(u'This mod has an associated voice directory (Sound\\Voice\\%s), which will not be attached to the duplicate mod.') % modName.s
                if not balt.askWarning(self.window,message,_(u'Duplicate ')+fileName.s):
                    continue
            #--Continue copy
            (root,ext) = fileName.rootExt
            if ext.lower() == u'.bak': ext = u'.ess'
            (destDir,wildcard) = (fileInfo.dir, u'*'+ext)
            destName = GPath(root+u' Copy'+ext)
            destPath = destDir.join(destName)
            count = 0
            while destPath.exists() and count < 1000:
                count += 1
                destName = GPath(root + u' Copy %d'  % count + ext)
                destPath = destDir.join(destName)
            destName = destName.s
            destDir.makedirs()
            if len(data) == 1:
                destPath = balt.askSave(self.window,_(u'Duplicate as:'), destDir,destName,wildcard)
                if not destPath: return
                destDir,destName = destPath.headTail
            if (destDir == fileInfo.dir) and (destName == fileName):
                balt.showError(self.window,_(u"Files cannot be duplicated to themselves!"))
                continue
            if fileInfo.isMod():
                newTime = bosh.modInfos.getFreeTime(fileInfo.getPath().mtime)
            else:
                newTime = '+1'
            fileInfos.copy(fileName,destDir,destName,mtime=newTime)
            if destDir == fileInfo.dir:
                fileInfos.table.copyRow(fileName,destName)
                if fileInfos.table.getItem(fileName,'mtime'):
                    fileInfos.table.setItem(destName,'mtime',newTime)
                if fileInfo.isMod():
                    fileInfos.autoSort()
            self.window.RefreshUI()

class File_Hide(_Link):
    """Hide the file. (Move it to Bash/Hidden directory.)"""
    text = _(u'Hide')

    def _initData(self, window, data):
        super(File_Hide, self)._initData(window, data)
        self.help = _(u"Move %(filename)s to the Bash/Hidden directory.") % (
            {'filename': data[0]})

    def Execute(self,event):
        if not bosh.inisettings['SkipHideConfirmation']:
            message = _(u'Hide these files? Note that hidden files are simply moved to the Bash\\Hidden subdirectory.')
            if not balt.askYes(self.window,message,_(u'Hide Files')): return
        #--Do it
        destRoot = self.window.data.bashDir.join(u'Hidden')
        fileInfos = self.window.data
        fileGroups = fileInfos.table.getColumn('group')
        for fileName in self.data:
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
            if not self.window.data.moveIsSafe(fileName,destDir):
                message = (_(u'A file named %s already exists in the hidden files directory. Overwrite it?')
                    % fileName.s)
                if not balt.askYes(self.window,message,_(u'Hide Files')): continue
            #--Do it
            self.window.data.move(fileName,destDir,False)
        #--Refresh stuff
        Link.Frame.RefreshData()

class File_ListMasters(EnabledLink):
    """Copies list of masters to clipboard."""
    text = _(u"List Masters...")

    def _initData(self, window, data):
        super(File_ListMasters, self)._initData(window, data)
        self.help = _(
            u"Copies list of %(filename)s's masters to the clipboard.") % (
                        {'filename': data[0]})

    def _enable(self): return len(self.data) == 1

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        text = bosh.modInfos.getModList(fileInfo=fileInfo)
        balt.copyToClipboard(text)
        balt.showLog(self.window,text,fileName.s,asDialog=False,fixedFont=False,icons=bashBlue)

class File_Redate(AppendableLink):
    """Move the selected files to start at a specified date."""
    text = _(u'Redate...')
    help = _(u"Move the selected files to start at a specified date.")

    def _append(self, window):
        return bosh.lo.LoadOrderMethod != bosh.liblo.LIBLO_METHOD_TEXTFILE

    def Execute(self,event):
        #--Get current start time.
        modInfos = self.window.data
        fileNames = [mod for mod in self.data if mod not in modInfos.autoSorted]
        if not fileNames: return
        #--Ask user for revised time.
        newTimeStr = balt.askText(self.window,_(u'Redate selected mods starting at...'),
            _(u'Redate Mods'),formatDate(int(time.time())))
        if not newTimeStr: return
        try:
            newTimeTup = bosh.unformatDate(newTimeStr,u'%c')
            newTime = int(time.mktime(newTimeTup))
        except ValueError:
            balt.showError(self.window,_(u'Unrecognized date: ')+newTimeStr)
            return
        except OverflowError:
            balt.showError(self,_(u'Bash cannot handle dates greater than January 19, 2038.)'))
            return
        #--Do it
        selInfos = [modInfos[fileName] for fileName in fileNames]
        selInfos.sort(key=attrgetter('mtime'))
        for fileInfo in selInfos:
            fileInfo.setmtime(newTime)
            newTime += 60
        #--Refresh
        modInfos.refresh(doInfos=False)
        modInfos.refreshInfoLists()
        self.window.RefreshUI()

class File_Sort(EnabledLink):
    """Sort the selected files."""
    text = _(u'Sort')
    help = _(u"Sort the selected files.")

    def _enable(self): return len(self.data) > 1

    def Execute(self,event):
        message = (_(u'Reorder selected mods in alphabetical order?  The first file will be given the date/time of the current earliest file in the group, with consecutive files following at 1 minute increments.')
                   + u'\n\n' +
                   _(u'Note that this operation cannot be undone.  Note also that some mods need to be in a specific order to work correctly, and this sort operation may break that order.')
                   )
        if not balt.askContinue(self.window,message,'bash.sortMods.continue',_(u'Sort Mods')):
            return
        #--Get first time from first selected file.
        modInfos = self.window.data
        fileNames = [mod for mod in self.data if mod not in modInfos.autoSorted]
        if not fileNames: return
        dotTimes = [modInfos[fileName].mtime for fileName in fileNames if fileName.s[0] in u'.=+']
        if dotTimes:
            newTime = min(dotTimes)
        else:
            newTime = min(modInfos[fileName].mtime for fileName in self.data)
        #--Do it
        fileNames.sort(key=lambda a: a.cext)
        fileNames.sort(key=lambda a: a.s[0] not in u'.=')
        for fileName in fileNames:
            modInfos[fileName].setmtime(newTime)
            newTime += 60
        #--Refresh
        modInfos.refresh(doInfos=False)
        modInfos.refreshInfoLists()
        self.window.RefreshUI()

class File_Snapshot(_Link):
    """Take a snapshot of the file."""
    help = _(u"Creates a snapshot copy of the current mod in a subdirectory (Bash\Snapshots).")

    def _initData(self, window, data):
        super(File_Snapshot, self)._initData(window, data)
        self.text = (_(u'Snapshot'),_(u'Snapshot...'))[len(data) == 1]

    def Execute(self,event):
        data = self.data
        for item in data:
            fileName = GPath(item)
            fileInfo = self.window.data[fileName]
            (destDir,destName,wildcard) = fileInfo.getNextSnapshot()
            destDir.makedirs()
            if len(data) == 1:
                destPath = balt.askSave(self.window,_(u'Save snapshot as:'),
                    destDir,destName,wildcard)
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
                newDescription = bosh.reVersion.sub(u'\\1 '+newVersion, fileHedr.description,1,flags=re.U)
                fileInfo.writeDescription(newDescription)
                self.window.details.SetFile(fileName)
            #--Copy file
            self.window.data.copy(fileName,destDir,destName)

class File_RevertToSnapshot(EnabledLink):
    """Revert to Snapshot."""
    text = _(u'Revert to Snapshot...')
    help = _(u"Revert to a previously created snapshot from the Bash/Snapshots dir.")

    def _enable(self): return len(self.data) == 1

    def Execute(self,event):
        """Handle menu item selection."""
        fileInfo = self.window.data[self.data[0]]
        fileName = fileInfo.name
        #--Snapshot finder
        destDir = self.window.data.dir
        srcDir = self.window.data.bashDir.join(u'Snapshots')
        wildcard = fileInfo.getNextSnapshot()[2]
        #--File dialog
        srcDir.makedirs()
        snapPath = balt.askOpen(self.window,_(u'Revert %s to snapshot:') % fileName.s,
            srcDir, u'', wildcard,mustExist=True)
        if not snapPath: return
        snapName = snapPath.tail
        #--Warning box
        message = (_(u"Revert %s to snapshot %s dated %s?")
            % (fileInfo.name.s, snapName.s, formatDate(snapPath.mtime)))
        if not balt.askYes(self.window,message,_(u'Revert to Snapshot')): return
        with balt.BusyCursor():
            destPath = fileInfo.getPath()
            snapPath.copyTo(destPath)
            fileInfo.setmtime()
            try:
                self.window.data.refreshFile(fileName)
            except bosh.FileError:
                balt.showError(self,_(u'Snapshot file is corrupt!'))
                self.window.details.SetFile(None)
            self.window.RefreshUI(fileName)

class File_Backup(_Link):
    """Backup file."""
    text = _(u'Backup')
    help = _(u"Create a backup of the selected file(s).")

    def Execute(self,event):
        for item in self.data:
            fileInfo = self.window.data[item]
            fileInfo.makeBackup(True)

class File_Open(EnabledLink):
    """Open specified file(s)."""
    text = _(u'Open...')

    def _initData(self, window, data):
        super(File_Open, self)._initData(window, data)
        self.help = _(u"Open '%s' with the system's default program.") % data[
            0] if len(data) == 1 else _(u'Open the selected files.')

    def _enable(self): return len(self.data) > 0

    def Execute(self,event):
        """Handle selection."""
        dir = self.window.data.dir
        for file in self.data:
            dir.join(file).start()

class File_RevertToBackup(ChoiceLink):
    """Revert to last or first backup."""
    def __init__(self):
        super(File_RevertToBackup, self).__init__()
        self.idList = balt.IdList(6100, 0,'REVERT_BACKUP','REVERT_FIRST')
        self.extraActions = {self.idList.REVERT_BACKUP: self.Execute,
                            self.idList.REVERT_FIRST: self.Execute,}

    def _initData(self, window, data):
        super(File_RevertToBackup, self)._initData(window, data)
        #--Backup Files
        singleSelect = len(data) == 1
        self.fileInfo = window.data[data[0]]
        self.backup = backup = self.fileInfo.bashDir.join(u'Backups',self.fileInfo.name)
        self.firstBackup = firstBackup = self.backup +u'f'
        #--Backup Item
        class _RevertBackup(EnabledLink):
            text = _(u'Revert to Backup')
            id = self.idList.REVERT_BACKUP
            def _enable(self): return singleSelect and backup.exists()
        #--First Backup item
        class _RevertFirstBackup(EnabledLink):
            text = _(u'Revert to First Backup')
            id = self.idList.REVERT_FIRST
            def _enable(self): return singleSelect and firstBackup.exists()
        self.extraItems =[_RevertBackup(), _RevertFirstBackup()]

    def Execute(self,event):
        fileInfo = self.fileInfo
        fileName = fileInfo.name
        #--Backup/FirstBackup?
        if event.GetId() == self.idList.REVERT_BACKUP:
            backup = self.backup
        else:
            backup = self.firstBackup
        #--Warning box
        message = _(u"Revert %s to backup dated %s?") % (fileName.s,
            formatDate(backup.mtime))
        if balt.askYes(self.window,message,_(u'Revert to Backup')):
            with balt.BusyCursor():
                dest = fileInfo.dir.join(fileName)
                backup.copyTo(dest)
                fileInfo.setmtime()
                if fileInfo.isEss(): #--Handle CoSave (.pluggy and .obse) files.
                    bosh.CoSaves(backup).copy(dest)
                try:
                    self.window.data.refreshFile(fileName)
                except bosh.FileError:
                    balt.showError(self,_(u'Old file is corrupt!'))
                self.window.RefreshUI(fileName)
