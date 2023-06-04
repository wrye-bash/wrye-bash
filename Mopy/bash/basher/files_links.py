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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
import re

from .. import balt, bass, bolt, bosh, exception
from ..balt import AppendableLink, MultiLink, ItemLink, OneItemLink
from ..gui import BusyCursor, DateAndTimeDialog, copy_text_to_clipboard
from ..localize import format_date
from ..wbtemp import TempFile

__all__ = [u'Files_Unhide', u'File_Backup', u'File_Duplicate',
           u'File_Snapshot', u'File_RevertToBackup', u'File_RevertToSnapshot',
           'File_ListMasters', 'File_Redate', 'File_JumpToSource']

#------------------------------------------------------------------------------
# Files Links -----------------------------------------------------------------
#------------------------------------------------------------------------------
class Files_Unhide(ItemLink):
    """Unhide file(s). (Move files back to Data Files or Save directory.)"""
    _text = _(u'Unhide...')

    def __init__(self, files_help):
        super(Files_Unhide, self).__init__()
        self._help = files_help

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
                self._showError(_("You can't unhide files from this "
                                  "directory."))
                return
            # Validate that the file is valid and isn't already present
            if not self._data_store.rightFileType(srcFileName.s):
                self._showWarning(_('File skipped: %(skipped_file)s. File is '
                    'not valid.') % {'skipped_file': srcFileName})
                continue
            destPath = destDir.join(srcFileName)
            if destPath.exists() or (destPath + u'.ghost').exists():
                self._showWarning(_('File skipped: %(skipped_file)s. File is '
                    'already present.') % {'skipped_file': srcFileName})
                continue
            # File
            srcFiles.append(srcPath)
            destFiles.append(destPath)
        #--Now move everything at once
        if not srcFiles:
            return
        moved = self._data_store.move_infos(srcFiles, destFiles,
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

    _bsa_and_blocking_msg = _(
        'This plugin has an associated BSA (%(assoc_bsa_name)s) and an '
        'associated plugin-name-specific directory (e.g. %(pnd_example)s), '
        'which will not be attached to the duplicate plugin.') + '\n\n' + _(
        'Note that the BSA may also contain a plugin-name-specific directory, '
        'which would remain detached even if a duplicate BSA were also '
        'created.')
    _bsa_msg = _(
        'This plugin has an associated BSA (%(assoc_bsa_name)s), which will '
        'not be attached to the duplicate plugin.') + '\n\n' + _(
        'Note that the BSA may contain a plugin-name-specific directory '
        '(e.g. %(pnd_example)s), which would remain detached even if a '
        'duplicate BSA were also created.')
    _blocking_msg = _(
        'This plugin has an associated plugin-name-specific directory (e.g. '
        '%(pnd_example)s), which will not be attached to the duplicate '
        'plugin.')

    @balt.conversation
    def Execute(self):
        dests = []
        fileInfos = self._data_store
        pairs = [*self.iselected_pairs()]
        last = len(pairs) - 1
        for dex, (to_duplicate, fileInfo) in enumerate(pairs):
            if self._disallow_copy(fileInfo):
                continue # We can't copy this one for some reason, skip
            r, e = to_duplicate.fn_body, to_duplicate.fn_ext
            destName = fileInfo.unique_key(r, e, add_copy=True)
            destDir = fileInfo.info_dir
            # This directory may not exist yet (e.g. INI Tweaks)
            destDir.makedirs()
            if len(self.selected) == 1: # ask the user for a filename
                destPath = self._askSave(
                    title=_(u'Duplicate as:'), defaultDir=destDir,
                    defaultFile=destName, wildcard=f'*{e}')
                if not destPath: return
                destDir, destName = destPath.head, bolt.FName(destPath.stail)
                destName, root = fileInfo.validate_name(destName,
                    # check if exists if we duplicate into the store dir
                    check_store=destDir == fileInfo.info_dir)
                if root is None:
                    self._showError(destName)
                    return
            fileInfos.copy_info(to_duplicate, destDir, destName,
                                save_lo_cache=dex == last)
            dests.append(destName)
        if dests:
            ##: refresh_infos=True for saves - would love to specify something
            # like refresh_only=dests - #353
            fileInfos.refresh()
            self.window.RefreshUI(redraw=dests, detail_item=dests[-1],
                                  refreshSaves=False) #(dup) saves not affected
            self.window.SelectItemsNoCallback(dests)

    def _disallow_copy(self, fileInfo):
        """Method for checking if fileInfo may not be copied for some reason.
        Default behavior is to allow all copies."""
        return False

#------------------------------------------------------------------------------
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
        self._showLog(list_of_mods, title=self._selected_item,
                      fixedFont=False)

#------------------------------------------------------------------------------
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
            fileRoot = fileName.fn_body
            destRoot = destName.sroot
            fileVersion = bolt.getMatch(
                re.search(r'[ _]+v?([.\d]+)$', fileRoot), 1)
            snapVersion = bolt.getMatch(re.search(r'-[\d.]+$', destRoot))
            fileHedr = fileInfo.header
            if (fileVersion or snapVersion) and bosh.reVersion.search(fileHedr.description):
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
            self._data_store.copy_info(fileName, destDir, destName)

#------------------------------------------------------------------------------
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
        snapPath = self._askOpen(_('Revert %(target_file_name)s to '
                                   'snapshot:') % {
            'target_file_name': fileName}, defaultDir=srcDir,
            wildcard=wildcard)
        if not snapPath: return
        snapName = snapPath.tail
        #--Warning box
        message = (_('Revert %(target_file_name)s to snapshot '
                     '%(snapsnot_file_name)s dated %(snapshot_date)s?') % {
            'target_file_name': fileName, 'snapsnot_file_name': snapName,
            'snapshot_date': format_date(snapPath.mtime)})
        if not self._askYes(message, _(u'Revert to Snapshot')): return
        with BusyCursor(), TempFile() as known_good_copy:
            destPath = self._selected_info.abs_path
            current_mtime = destPath.mtime
            # Make a temp copy first in case reverting to snapshot fails
            destPath.copyTo(known_good_copy)
            snapPath.copyTo(destPath)
            # keep load order but recalculate the crc
            self._selected_info.setmtime(current_mtime, crc_changed=True)
            try:
                self._data_store.new_info(fileName, notify_bain=True)
            except exception.FileError:
                # Reverting to snapshot failed - may be corrupt
                bolt.deprint('Failed to revert to snapshot', traceback=True)
                self.window.panel.ClearDetails()
                if self._askYes(
                    _("Failed to revert %(target_file_name)s to snapshot "
                      "%(snapshot_file_name)s. The snapshot file may be "
                      "corrupt. Do you want to restore the original file "
                      "again? 'No' keeps the reverted, possibly broken "
                      "snapshot instead.") % {'target_file_name': fileName,
                                              'snapshot_file_name': snapName},
                        title=_('Revert to Snapshot - Error')):
                    # Restore the known good file again - no error check needed
                    destPath.replace_with_temp(known_good_copy)
                    self._data_store.new_info(fileName, notify_bain=True)
        # don't refresh saves as neither selection state nor load order change
        self.window.RefreshUI(redraw=[fileName], refreshSaves=False)

#------------------------------------------------------------------------------
class File_Backup(ItemLink):
    """Backup file."""
    _text = _(u'Backup')
    _help = _(u'Create a backup of the selected file(s).')

    def Execute(self):
        for fileInfo in self.iselected_infos():
            fileInfo.makeBackup(forceBackup=True)

#------------------------------------------------------------------------------
class _RevertBackup(OneItemLink):

    def __init__(self, first=False):
        super().__init__()
        self._text = _(u'Revert to First Backup...') if first else _(
            u'Revert to Backup...')
        self.first = first

    def _initData(self, window, selection):
        super()._initData(window, selection)
        self.backup_path = self._selected_info.backup_dir.join(
            self._selected_item) + (u'f' if self.first else u'')
        self._help = _(u'Revert %(file)s to its first backup') if self.first \
            else _(u'Revert %(file)s to its last backup')
        self._help %= {'file': self._selected_item}

    def _enable(self):
        return super()._enable() and self.backup_path.exists()

    @balt.conversation
    def Execute(self):
        #--Warning box
        sel_file = self._selected_item
        backup_date_fmt = format_date(self.backup_path.mtime)
        message = _('Revert %(target_file_name)s to backup dated '
                    '%(backup_date)s?') % {'target_file_name': sel_file,
                                           'backup_date': backup_date_fmt}
        if not self._askYes(message): return
        with BusyCursor(), TempFile() as known_good_copy:
            # Make a temp copy first in case reverting to backup fails
            info_path = self._selected_info.abs_path
            info_path.copyTo(known_good_copy)
            try:
                self._selected_info.revert_backup(self.first)
            except exception.FileError:
                # Reverting to backup failed - may be corrupt
                bolt.deprint('Failed to revert to backup', traceback=True)
                self.window.panel.ClearDetails()
                if self._askYes(_(
                        "Failed to revert %(target_file_name)s to backup "
                        "dated %(backup_date)s. The backup file may be "
                        "corrupt. Do you want to restore the original file "
                        "again? 'No' keeps the reverted, possibly broken "
                        "backup instead.") % {'target_file_name': sel_file,
                                              'backup_date': backup_date_fmt},
                        title=_('Revert to Backup - Error')):
                    # Restore the known good file again - no error check needed
                    info_path.replace_with_temp(known_good_copy)
                    self._data_store.new_info(sel_file, notify_bain=True)
        # don't refresh saves as neither selection state nor load order change
        self.window.RefreshUI(redraw=[sel_file], refreshSaves=False)

class File_RevertToBackup(MultiLink):
    """Revert to last or first backup."""
    def _links(self):
        return [_RevertBackup(), _RevertBackup(first=True)]

#------------------------------------------------------------------------------
class File_Redate(ItemLink):
    """Move the selected files to start at a specified date."""
    _text = _(u'Redate...')
    _help = _(u'Change the modification time(s) of the selected file(s) to '
              u'start at a specified date.')

    @balt.conversation
    def Execute(self):
        user_ok, user_datetime = DateAndTimeDialog.display_dialog(
            self.window, warning_color=balt.colors['default.warn'],
            icon_bundle=balt.Resources.bashBlue)
        if not user_ok: return
        # Perform the redate process and refresh
        user_timestamp = user_datetime.timestamp()
        for to_redate in self._infos_to_redate():
            to_redate.setmtime(user_timestamp)
            user_timestamp += 60.0
        self._perform_refresh()
        self.window.RefreshUI(refreshSaves=True)

    # Overrides for Mod_Redate
    def _infos_to_redate(self):
        """Returns an iterable of the FileInfo instances to redate."""
        return self.iselected_infos()

    def _perform_refresh(self):
        """Refreshes the data store - """
        self._data_store.refresh(refresh_infos=False)

#------------------------------------------------------------------------------
class File_JumpToSource(AppendableLink, OneItemLink):
    """Go to the Installers tab and highlight the file's installing package."""
    _text = _('Jump to Source')

    @property
    def link_help(self):
        return _('Jump to the package associated with %(filename)s. You '
                 'can Alt-Click on the file to the same effect.') % {
            'filename': self._selected_item}

    def _append(self, window):
        return (balt.Link.Frame.iPanel and
                bass.settings['bash.installers.enabled'])

    def _enable(self):
        return (super()._enable() and
                self.window.get_source(self._selected_item) is not None)

    def Execute(self):
        self.window.jump_to_source(self._selected_item)
