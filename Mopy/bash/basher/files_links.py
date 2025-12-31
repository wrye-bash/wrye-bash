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
from .. import balt, bass, bosh, bush
from ..balt import AppendableLink, MultiLink, ItemLink, OneItemLink
from ..bolt import FNDict, FName, RefrData
from ..bosh import DefaultIniInfo
from ..gui import BusyCursor, DateAndTimeDialog, copy_text_to_clipboard, \
    FileOpenMultiple
from ..localize import format_date

__all__ = ['File_Backup', 'File_Duplicate', 'File_JumpToSource', 'File_Redate',
           'File_ListMasters', 'File_RevertToBackup', 'Files_Unhide',
           'RestoreInfo']

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
        uil, dstore = self.window, self._data_store
        #--File dialog
        hide_d = dstore.hide_dir
        # Otherwise FileOpenMultiple will open some random directory
        hide_d.makedirs()
        wildcard = dstore.unhide_wildcard(with_ghosts=False)
        st_dir = dstore.store_dir
        srcPaths = FileOpenMultiple.display_dialog(uil, _('Unhide files:'),
            defaultDir=hide_d, wildcard=wildcard)
        if not srcPaths: return
        #--Iterate over Paths
        srcFiles = []
        for srcPath in srcPaths:
            #--Copy from dest directory?
            (newSrcDir,srcFileName) = srcPath.headTail
            if newSrcDir == st_dir:
                self._showError(_("You can't unhide files from this "
                                  "directory."))
                return
            # Validate that the file is valid and isn't already present
            if not dstore.check_filename(srcFileName.s): # True only if is_file
                self._showWarning(_('File skipped: %(skipped_file)s. File is '
                    'not valid.') % {'skipped_file': srcFileName})
                continue
            if not (inf := dstore.get_update_info(srcPath, is_proj=False)):
                self._showWarning(_('File skipped: %(skipped_file)s. File is '
                    'not valid.') % {'skipped_file': srcFileName})
                continue
            if (fn_key := inf.fn_key) in dstore:
                self._showWarning(_('File skipped: %(skipped_file)s. File is '
                    'already present.') % {'skipped_file': srcFileName})
                continue
            srcFiles.append((inf, fn_key, st_dir))
        #--Now move everything at once  #292: we ain't handling backups
        uil.try_rename(srcFiles, deselect=True)

#------------------------------------------------------------------------------
# File Links ------------------------------------------------------------------
#------------------------------------------------------------------------------
class File_Duplicate(ItemLink):
    """Create a duplicate of the file - mod, save, bsa, etc."""
    _text = _('Duplicate…')
    _help = _('Make a copy of the selected files.')

    @balt.conversation
    def Execute(self):
        mod_previous = FNDict()
        fileInfos = self._data_store
        names = set(fileInfos)
        ren_args = []
        rd_def_ini = RefrData()
        for to_duplicate, fileInfo in self.iselected_pairs():
            if self._disallow_copy(fileInfo):
                continue # We can't copy this one for some reason, skip
            destDir, fn_dup = self._get_dup_filename(fileInfo, names,
              title=_('Duplicate as:'), wildcard=f'*{to_duplicate.fn_ext}')
            if not fn_dup: return
            # check if exists if we duplicate into the store dir
            if len(self.selected) == 1 and destDir == fileInfos.store_dir:
                # use the store (think ghosts)
                if fn_dup in self._data_store and not isinstance(
                        fileInfo, DefaultIniInfo):
                    self._showError(_('File %(bad_name_str)s already exists.'
                                      ) % {'bad_name_str': fn_dup})
                    return
            # we need to load_cache here - see _TabledInfo.__init__
            if inf := fileInfos.get_update_info(to_duplicate, copy_from=fileInfo,
                    dup_path=destDir.join(fn_dup), rd_def_ini=rd_def_ini):
                ren_args.append((inf, fn_dup, destDir))
                mod_previous[fn_dup] = to_duplicate
        if mod_previous or rd_def_ini:
            fnd = next(reversed(mod_previous or rd_def_ini.renames.values()))
            self.window.try_rename(ren_args, copy_inf=True, fn_detail=fnd,
                insert_after=mod_previous, refr_data=rd_def_ini)

    def _get_dup_filename(self, fileInfo, names=None, **kwargs):
        destDir = self._data_store.store_dir
        destName = fileInfo.unique_key(names=names)
        if len(self.selected) == 1: # ask the user for a filename
            destDir, destName = self._ask_dup_filename(destDir, fileInfo,
                filename=destName, **kwargs)
        return destDir, destName

    def _ask_dup_filename(self, destDir, fileInfo, filename, **kwargs):
        if destPath := self._askSave(**kwargs, defaultDir=destDir,
                                     defaultFile=filename):
            destDir, destName = destPath.head, FName(destPath.stail)
            destName, root = fileInfo.validate_name(destName)
            if root is not None:
                return destDir, destName
            self._showError(destName)
        return None, None

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
class RestoreInfo(OneItemLink):
    """Restore backups/snapshots"""

    @balt.conversation
    def Execute(self):
        #--Warning box
        if not self._ask_revert(): return
        with BusyCursor():
            sel_inf = self._selected_info
            # create an info in the backup directory and try loading it - note
            # we unlink 'bp_split_parent'!
            if not (inf := self._data_store.get_update_info(self._backup_path,
                    copy_from=sel_inf, exclude=True)):
                self._failed_msg()
                return
            ren_args = [(inf, self._selected_item, self._data_store.store_dir)]
            # in case the restored file is a BP: refresh in rename will try to
            # refresh info sets, but we don't back up the config so we can't
            # really detect changes in imported/merged - a (another) backup
            # edge case - as backup is half-baked anyway let's agree for now
            # that BPs remain BPs with the same config as before - if not,
            # manually run a mergeability scan after updating the config
            self.window.try_rename(ren_args, copy_inf=True,
                # no refresh saves as neither active mods nor load order change
                refr_saves=False, set_mtime={sel_inf.fn_key: sel_inf.ftime})

    @property
    def _backup_path(self): raise NotImplementedError

    def _ask_revert(self): raise NotImplementedError

    def _failed_msg(self): raise NotImplementedError

class _RevertBackup(RestoreInfo):

    def __init__(self, first=False):
        super().__init__()
        self._text = (_('Revert to First Backup…') if first else
                      _('Revert to Backup…'))
        self.first = first

    @property
    def _backup_path(self):
        return self._selected_info.backup_path(self.first)

    @property
    def link_help(self):
        msg = _('Revert %(file)s to its first backup') if self.first else _(
            'Revert %(file)s to its last backup')
        return msg % {'file': self._selected_item}

    def _enable(self):
        return super()._enable() and self._backup_path.exists()

    def _failed_msg(self):
        self._showError(
            _("Failed to revert %(target_file_name)s to backup dated "
              "%(backup_date)s. The backup file may be corrupt.") % {
                'target_file_name': self._selected_item,
                'backup_date': format_date(self._backup_path.mtime)},
            title=_('Revert to Backup - Error'))

    def _ask_revert(self):
        msg = _('Revert %(target_file_name)s to backup dated %(backup_date)s?')
        return self._askYes(msg % {'target_file_name': self._selected_item,
            'backup_date': format_date(self._backup_path.mtime)})

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
            to_redate.setmtime(user_timestamp, mark_redated=True)
            user_timestamp += 60.0
        rdata = self._data_store.refresh(False, unlock_lo=bush.game.mtime_lo)
        self.window.propagate_refresh(rdata)

    # Overrides for Mod_Redate
    def _infos_to_redate(self):
        """Returns an iterable of the FileInfo instances to redate."""
        return self.iselected_infos()

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
