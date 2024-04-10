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

from .. import balt, bass, bolt, bosh, exception
from ..balt import AppendableLink, MultiLink, ItemLink, OneItemLink
from ..bass import Store
from ..gui import BusyCursor, DateAndTimeDialog, copy_text_to_clipboard
from ..localize import format_date
from ..wbtemp import TempFile

__all__ = ['File_Backup', 'File_Duplicate', 'File_JumpToSource', 'File_Redate',
           'File_ListMasters', 'File_RevertToBackup', 'Files_Unhide']

#------------------------------------------------------------------------------
# Files Links -----------------------------------------------------------------
#------------------------------------------------------------------------------
class Files_Unhide(ItemLink):
    """Unhide file(s). (Move files back to Data Files or Save directory.)"""
    _text = _('Unhide…')

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
                detail_item=next(iter(moved)), refresh_others=Store.SAVES.DO())
            self.window.SelectItemsNoCallback(moved, deselectOthers=True)

#------------------------------------------------------------------------------
# File Links ------------------------------------------------------------------
#------------------------------------------------------------------------------
class File_Duplicate(ItemLink):
    """Create a duplicate of the file - mod, save, bsa, etc."""
    _text = _('Duplicate…')
    _help = _('Make a copy of the selected files.')

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
            if len(self.selected) == 1: # ask the user for a filename
                # This directory may not exist yet (e.g. INI Tweaks)
                destDir.makedirs()
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
            fileInfo.copy_to(destDir.join(destName), save_lo_cache=dex == last)
            dests.append(destName)
        if dests:
            ##: refresh_infos=True for saves - would love to specify something
            # like refresh_only=dests - #353
            fileInfos.refresh()
            self.window.RefreshUI(redraw=dests, detail_item=dests[-1])
            self.window.SelectItemsNoCallback(dests)

    def _disallow_copy(self, fileInfo):
        """Method for checking if fileInfo may not be copied for some reason.
        Default behavior is to allow all copies."""
        return False

#------------------------------------------------------------------------------
class File_ListMasters(OneItemLink):
    """Copies list of masters to clipboard."""
    _text = _('List Masters…')

    @property
    def link_help(self):
        return _(u"Copies list of %(filename)s's masters to the clipboard.") % (
                        {u'filename': self.selected[0]})

    def Execute(self):
        list_of_mods = bosh.modInfos.getModList(fileInfo=self._selected_info)
        copy_text_to_clipboard(list_of_mods)
        self._showLog(list_of_mods, title=self._selected_item)

#------------------------------------------------------------------------------
class File_Backup(ItemLink):
    """Backup file."""
    _text = _('Backup')
    _help = _('Creates a backup of the selected files.')

    def Execute(self):
        for fileInfo in self.iselected_infos():
            fileInfo.makeBackup(forceBackup=True)

#------------------------------------------------------------------------------
class _RevertBackup(OneItemLink):

    def __init__(self, first=False):
        super().__init__()
        self._text = (_('Revert to First Backup…') if first else
                      _('Revert to Backup…'))
        self.first = first

    @property
    def _backup_path(self):
        return self._selected_info.backup_dir.join(
            self._selected_item) + ('f' if self.first else '')

    @property
    def link_help(self):
        return (_('Revert %(file)s to its first backup') if self.first else _(
            'Revert %(file)s to its last backup')) % {
            'file': self._selected_item}

    def _enable(self):
        return super()._enable() and self._backup_path.exists()

    @balt.conversation
    def Execute(self):
        #--Warning box
        sel_file = self._selected_item
        backup_date_fmt = format_date(self._backup_path.mtime)
        message = _('Revert %(target_file_name)s to backup dated '
                    '%(backup_date)s?') % {'target_file_name': sel_file,
                                           'backup_date': backup_date_fmt}
        if not self._askYes(message): return
        with BusyCursor(), TempFile() as known_good_copy:
            sel = self._selected_info
            # Make a temp copy first in case reverting to backup fails
            info_path = sel.abs_path
            sel.fs_copy(known_good_copy)
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
                    inf = self._data_store.new_info(sel_file, notify_bain=True)
                    inf.copy_persistent_attrs(sel)
        # don't refresh saves as neither selection state nor load order change
        self.window.RefreshUI(redraw=[sel_file])

class File_RevertToBackup(MultiLink):
    """Revert to last or first backup."""
    def _links(self):
        return [_RevertBackup(), _RevertBackup(first=True)]

#------------------------------------------------------------------------------
class File_Redate(ItemLink):
    """Move the selected files to start at a specified date."""
    _text = _('Redate…')
    _help = _('Changes the modification times of the selected files to start '
              'at a specified date.')

    @balt.conversation
    def Execute(self):
        if not (user_datetime := DateAndTimeDialog.display_dialog(self.window,
                warning_color=balt.colors['default.warn'],
                icon_bundle=balt.Resources.bashBlue)):
            return
        # Perform the redate process and refresh
        user_timestamp = user_datetime.timestamp()
        for to_redate in self._infos_to_redate():
            to_redate.setmtime(user_timestamp)
            user_timestamp += 60.0
        self._perform_refresh()
        self.window.RefreshUI(refresh_others=Store.SAVES.DO())

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
