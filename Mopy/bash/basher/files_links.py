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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

import re
import time
from .. import balt, bosh, bush, bolt, exception
from ..balt import ItemLink, ChoiceLink, OneItemLink
from ..gui import BusyCursor, copy_text_to_clipboard
from ..localize import format_date, unformat_date

__all__ = [u'Files_Unhide', u'File_Backup', u'File_Duplicate',
           u'File_Snapshot', u'File_RevertToBackup', u'File_RevertToSnapshot',
           u'File_ListMasters', u'File_Redate']

#------------------------------------------------------------------------------
# Files Links -----------------------------------------------------------------
#------------------------------------------------------------------------------
class Files_Unhide(ItemLink):
    """Unhide file(s). (Move files back to Data Files or Save directory.)"""
    _text = _(u'Unhide...')

    def __init__(self, files_type):
        super(Files_Unhide, self).__init__()
        self._help = _(u'Unhides hidden %ss.') % files_type

    @balt.conversation
    def Execute(self):
        #--File dialog
        destDir, srcDir, srcPaths = self.window.unhide()
        if not srcPaths: return
        #--Iterate over Paths
        srcFiles = []
        destFiles = []
        for srcPath in srcPaths:
            #--Copy from dest directory?
            (newSrcDir,srcFileName) = srcPath.headTail
            if newSrcDir == destDir:
                self._showError(
                    _(u"You can't unhide files from this directory."))
                return
            #--File already unhidden?
            destPath = destDir.join(srcFileName)
            if destPath.exists() or (destPath + u'.ghost').exists():
                self._showWarning(_(u'File skipped: %s. File is already '
                                    u'present.') % (srcFileName,))
            #--Move it?
            else:
                srcFiles.append(srcPath)
                destFiles.append(destPath)
        #--Now move everything at once
        if not srcFiles:
            return
        moved = self.window.data_store.move_infos(srcFiles, destFiles,
            self.window, balt.Link.Frame)
        if moved:
            self.window.RefreshUI( # pick one at random to show details for
                detail_item=next(iter(moved)), refreshSaves=True)
            self.window.SelectItemsNoCallback(moved, deselectOthers=True)

#------------------------------------------------------------------------------
# File Links ------------------------------------------------------------------
#------------------------------------------------------------------------------
class File_Duplicate(ItemLink):
    """Create a duplicate of the file - mod, save, bsa, etc."""
    _text = _(u'Duplicate...')
    _help = _(u'Make a copy of the selected file(s).')

    _bsaAndBlocking = _(
        u'This mod has an associated archive (%s) and an associated '
        u'plugin-name-specific directory (e.g. Sound\\Voice\\%s), which will '
        u'not be attached to the duplicate mod.') + u'\n\n' + _(
        u'Note that the BSA archive may also contain a plugin-name-specific '
        u'directory, which would remain detached even if a duplicate archive '
        u'were also created.')
    _bsa = _(
        u'This mod has an associated archive (%s), which will not be attached '
        u'to the duplicate mod.') + u'\n\n' + _(
        u'Note that this BSA archive may contain a plugin-name-specific '
        u'directory (e.g. Sound\\Voice\\%s), which would remain detached even '
        u'if a duplicate archive were also created.')
    _blocking = _(
        u'This mod has an associated plugin-name-specific directory (e.g. '
        u'Sound\\Voice\\%s), which will not be attached to the duplicate '
        u'mod.')

    @balt.conversation
    def Execute(self):
        dests = []
        fileInfos = self.window.data_store
        for to_duplicate, fileInfo in self.iselected_pairs():
            #--Mod with resources? Warn on rename if file has bsa and/or dialog
            msg = fileInfo.askResourcesOk(
                bsaAndBlocking=self._bsaAndBlocking, bsa=self._bsa,
                blocking=self._blocking)
            if msg and not self._askWarning(msg, _(
                u'Duplicate %s') % fileInfo): continue
            #--Continue copy
            r, e = to_duplicate.root, to_duplicate.ext
            destName = fileInfo.unique_key(r, e, add_copy=True)
            destDir = fileInfo.dir
            if len(self.selected) == 1:
                destPath = self._askSave(
                    title=_(u'Duplicate as:'), defaultDir=destDir,
                    defaultFile=destName.s, wildcard=u'*%s' %e)
                if not destPath: return
                destDir, destName = destPath.headTail
                if destDir == fileInfo.dir: # FIXME validate (or ask save does that)?
                    if destName == to_duplicate:
                        self._showError(
                            _(u'Files cannot be duplicated to themselves!'))
                        continue
                    elif destName in fileInfos:
                        self._showError(_(u'%s exists!') % destPath)
                        continue
            fileInfos.copy_info(to_duplicate, destDir, destName)
            if fileInfo.isMod(): ##: move this inside copy_info
                fileInfos.cached_lo_insert_after(to_duplicate, destName)
            dests.append(destName)
        if dests:
            if fileInfo.isMod(): fileInfos.cached_lo_save_lo()
            ##: refresh_infos=True for saves - would love to specify something
            # like refresh_only=dests - #353
            fileInfos.refresh()
            self.window.RefreshUI(redraw=dests, detail_item=dests[-1],
                                  refreshSaves=False) #(dup) saves not affected
            self.window.SelectItemsNoCallback(dests)

class File_ListMasters(OneItemLink):
    """Copies list of masters to clipboard."""
    _text = _(u'List Masters...')

    @property
    def link_help(self):
        return _(u"Copies list of %(filename)s's masters to the clipboard.") % (
                        {u'filename': self.selected[0]})

    def Execute(self):
        list_of_mods = bosh.modInfos.getModList(fileInfo=self._selected_info)
        copy_text_to_clipboard(list_of_mods)
        self._showLog(list_of_mods, title=self._selected_item.s,
                      fixedFont=False)

class File_Snapshot(ItemLink):
    """Take a snapshot of the file."""
    _help = _(u'Creates a snapshot copy of the selected file(s) in a '
              u'subdirectory (Bash\Snapshots).')

    @property
    def link_text(self):
        return (_(u'Snapshot'), _(u'Snapshot...'))[len(self.selected) == 1]

    def Execute(self):
        for fileName, fileInfo in self.iselected_pairs():
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
            fileVersion = bolt.getMatch(
                re.search(r'[ _]+v?([.\d]+)$', fileRoot.s, re.U), 1)
            snapVersion = bolt.getMatch(
                re.search(r'-[\d.]+$', destRoot.s, re.U))
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

class File_RevertToSnapshot(OneItemLink):
    """Revert to Snapshot."""
    _text = _(u'Revert to Snapshot...')
    _help = _(u'Revert to a previously created snapshot from the '
              u'Bash/Snapshots dir.')

    @balt.conversation
    def Execute(self):
        """Revert to Snapshot."""
        fileName = self._selected_item
        #--Snapshot finder
        srcDir = self._selected_info.snapshot_dir
        wildcard = self._selected_info.getNextSnapshot()[2]
        #--File dialog
        srcDir.makedirs()
        snapPath = self._askOpen(_(u'Revert %s to snapshot:') % fileName,
                                 defaultDir=srcDir, wildcard=wildcard)
        if not snapPath: return
        snapName = snapPath.tail
        #--Warning box
        message = (_(u'Revert %s to snapshot %s dated %s?') % (
            fileName, snapName, format_date(snapPath.mtime)))
        if not self._askYes(message, _(u'Revert to Snapshot')): return
        with BusyCursor():
            destPath = self._selected_info.abs_path
            current_mtime = destPath.mtime
            # Make a temp backup first in case reverting to snapshot fails
            destPath.copyTo(destPath.temp)
            snapPath.copyTo(destPath)
            # keep load order but recalculate the crc
            self._selected_info.setmtime(current_mtime, crc_changed=True)
            try:
                self.window.data_store.new_info(fileName, notify_bain=True)
            except exception.FileError:
                # Reverting to snapshot failed - may be corrupt
                bolt.deprint(u'Failed to revert to snapshot', traceback=True)
                self.window.panel.ClearDetails()
                if self._askYes(
                    _(u'Failed to revert %s to snapshot %s. The snapshot file '
                      u'may be corrupt. Do you want to restore the original '
                      u"file again? 'No' keeps the reverted, possibly broken "
                      u'snapshot instead.') % (fileName, snapName),
                        title=_(u'Revert to Snapshot - Error')):
                    # Restore the known good file again - no error check needed
                    destPath.untemp()
                    self.window.data_store.new_info(fileName, notify_bain=True)
        # don't refresh saves as neither selection state nor load order change
        self.window.RefreshUI(redraw=[fileName], refreshSaves=False)

class File_Backup(ItemLink):
    """Backup file."""
    _text = _(u'Backup')
    _help = _(u'Create a backup of the selected file(s).')

    def Execute(self):
        for fileInfo in self.iselected_infos():
            fileInfo.makeBackup(True)

class _RevertBackup(OneItemLink):

    def __init__(self, first=False):
        super(_RevertBackup, self).__init__()
        self._text = _(u'Revert to First Backup...') if first else _(
            u'Revert to Backup...')
        self.first = first

    def _initData(self, window, selection):
        super(_RevertBackup, self)._initData(window, selection)
        self.backup_path = self._selected_info.backup_dir.join(
            self._selected_item) + (u'f' if self.first else u'')
        self._help = _(u'Revert %(file)s to its first backup') if self.first \
            else _(u'Revert %(file)s to its last backup')
        self._help %= {'file': self._selected_item}

    def _enable(self):
        return super(_RevertBackup,
                     self)._enable() and self.backup_path.exists()

    @balt.conversation
    def Execute(self):
        #--Warning box
        sel_file = self._selected_item
        backup_date = format_date(self.backup_path.mtime)
        message = _(u'Revert %s to backup dated %s?') % (sel_file, backup_date)
        if not self._askYes(message): return
        with BusyCursor():
            # Make a temp backup first in case reverting to backup fails
            info_path = self._selected_info.abs_path
            info_path.copyTo(info_path.temp)
            try:
                self._selected_info.revert_backup(self.first)
            except exception.FileError:
                # Reverting to backup failed - may be corrupt
                bolt.deprint(u'Failed to revert to backup', traceback=True)
                self.window.panel.ClearDetails()
                if self._askYes(
                    _(u'Failed to revert %s to backup dated %s. The backup '
                      u'file may be corrupt. Do you want to restore the '
                      u"original file again? 'No' keeps the reverted, "
                      u'possibly broken backup instead.') % (sel_file,
                                                             backup_date),
                        title=_(u'Revert to Backup - Error')):
                    # Restore the known good file again - no error check needed
                    info_path.untemp()
                    self.window.data_store.new_info(sel_file, notify_bain=True)
        # don't refresh saves as neither selection state nor load order change
        self.window.RefreshUI(redraw=[sel_file], refreshSaves=False)

class File_RevertToBackup(ChoiceLink):
    """Revert to last or first backup."""
    extraItems = [_RevertBackup(), _RevertBackup(first=True)]

class File_Redate(ItemLink):
    """Move the selected files to start at a specified date."""
    _text = _(u'Redate...')
    _help = _(u'Change the modification time(s) of the selected file(s) to '
              u'start at a specified date.')

    @balt.conversation
    def Execute(self):
        # Ask user for revised time and parse it
        new_time_input = self._askText(
            _(u'Redate selected file(s) starting at...'),
            title=_(u'Redate Files'), default=format_date(time.time()))
        if not new_time_input: return
        try:
            new_time = time.mktime(unformat_date(new_time_input))
        except ValueError:
            self._showError(_(u'Unrecognized date: ') + new_time_input)
            return
        # Perform the redate process and refresh
        for to_redate in self._infos_to_redate():
            to_redate.setmtime(new_time)
            new_time += 60
        self._perform_refresh()
        self.window.RefreshUI(refreshSaves=True)

    # Overrides for Mod_Redate
    def _infos_to_redate(self):
        """Returns an iterable of the FileInfo instances to redate."""
        return self.iselected_infos()

    def _perform_refresh(self):
        """Refreshes the data store - """
        self.window.data_store.refresh(refresh_infos=False)
