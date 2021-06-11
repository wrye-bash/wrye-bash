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

"""Backup/restore Bash settings. Settings paths are defined in
_init_settings_files().

Re: bass.AppVersion, bass.settings[u'bash.version']

The latter is read from the settings - so on upgrading Bash it's the version of
the previous Bash install, whereupon is based the backup-on-upgrade routine.
Later on, in basher.BashApp#InitVersion, bass.settings[u'bash.version'] is
set to bass.AppVersion. We save both in the settings we backup:
- bass.settings[u'bash.version'] is saved first and corresponds to the version
the settings were created with
- bass.AppVersion, saved second, is the version of Bash currently executing
the backup
"""

import os
import pickle
from os.path import join as jo

from . import archives
from . import bass # for settings (duh!)
from . import bolt
from . import initialization
from .bass import dirs, AppVersion
from .bolt import GPath, deprint
from .exception import BoltError, StateError

def _init_settings_files(bak_name, mg_name, root_prefix, mods_folder):
    """Construct a dict mapping directory paths to setting files. Keys are
    tuples of absolute paths to directories, paired with the relative paths
    in the backup file. Values are sets of setting files in those paths,
    or empty, meaning we have to list those paths and backup everything.

    :param bak_name: bush.game.bak_game_name
    :param mg_name: bush.game.my_games_name
    :param root_prefix: bush.game.bash_root_prefix
    :param mods_folder: bush.game.mods_dir"""
    if not initialization.bash_dirs_initialized:
        raise BoltError(u'_init_settings_files: Bash dirs are not initialized')
    settings_info = {
        (dirs[u'mopy'], jo(bak_name, u'Mopy')): {u'bash.ini', },
        (dirs[u'mods'].join(u'Bash'), jo(bak_name, mods_folder, u'Bash')): {
            u'Table.dat', },
        (dirs[u'mods'].join(u'Docs'), jo(bak_name, mods_folder, u'Docs')): {
            u'Bash Readme Template.txt', u'Bash Readme Template.html',
            u'My Readme Template.txt', u'My Readme Template.html',
            u'wtxt_sand_small.css', u'wtxt_teal.css', },
        (dirs[u'modsBash'], jo(root_prefix + u' Mods', u'Bash Mod Data')): {
            u'Table.dat', },
        (dirs[u'modsBash'].join(u'INI Data'),
         jo(root_prefix + u' Mods', u'Bash Mod Data', u'INI Data')): {
           u'Table.dat', },
        (dirs[u'bainData'],
         jo(root_prefix + u' Mods', u'Bash Installers', u'Bash')): {
           u'Converters.dat', u'Installers.dat', },
        (dirs[u'saveBase'], jo(u'My Games', mg_name)): {
            u'BashProfiles.dat', u'BashSettings.dat', u'BashLoadOrders.dat'},
        # backup all files in Mopy\bash\l10n, Data\Bash Patches\,
        # Data\BashTags\ and Data\INI Tweaks\
        (dirs[u'l10n'], jo(bak_name, u'Mopy', u'bash', u'l10n')): {},
        (dirs[u'mods'].join(u'Bash Patches'),
         jo(bak_name, mods_folder, u'Bash Patches')): {},
        (dirs[u'mods'].join(u'BashTags'),
         jo(bak_name, mods_folder, u'BashTags')): {},
        (dirs[u'mods'].join(u'INI Tweaks'),
         jo(bak_name, mods_folder, u'INI Tweaks')): {},
    }
    for setting_files in settings_info.values():
        for settings_file in set(setting_files):
            if settings_file.endswith(u'.dat'): # add corresponding bak file
                setting_files.add(settings_file + u'.bak')
    return settings_info

#------------------------------------------------------------------------------
class BackupSettings(object):
    """Create a 7z backup file with the settings files used by Bash. We need
    bass.dirs initialized and also bass.settings - to get the version of the
    settings we backup (bass.settings[u'bash.version']). Creates a backup.dat
    file that stores those versions."""

    def __init__(self, settings_file, bak_name, mg_name, root_prefix,
                 mods_folder):
        self._backup_dest_file = GPath(settings_file) # absolute path to dest 7z file
        self.files = {}
        for (bash_dir, tmpdir), setting_files in _init_settings_files(
                bak_name, mg_name, root_prefix, mods_folder).items():
            if not setting_files: # we have to backup everything in there
                setting_files = bash_dir.list()
            tmp_dir = GPath(tmpdir)
            for fname in setting_files:
                fpath = bash_dir.join(fname)
                if fpath.exists():
                    self.files[tmp_dir.join(fname)] = fpath
        # backup save profile settings
        savedir = GPath(u'My Games').join(mg_name)
        profiles = [u''] + initialization.getLocalSaveDirs()
        for profile in profiles:
            pluginsTxt = (u'Saves', profile, u'plugins.txt')
            loadorderTxt = (u'Saves', profile, u'loadorder.txt')
            for txt in (pluginsTxt, loadorderTxt):
                tpath = savedir.join(*txt)
                fpath = dirs[u'saveBase'].join(*txt)
                if fpath.exists(): self.files[tpath] = fpath
            prof_table = (u'Saves', profile, u'Bash', u'Table.dat')
            tpath = savedir.join(*prof_table)
            fpath = dirs[u'saveBase'].join(*prof_table)
            if fpath.exists(): self.files[tpath] = fpath
            if fpath.backup.exists(): self.files[tpath.backup] = fpath.backup

    @staticmethod
    def new_bash_version_prompt_backup(balt_, previous_bash_version):
        # return False if old version == 0 (as in not previously installed)
        if previous_bash_version == 0 or AppVersion == previous_bash_version:
            return False
        # return True if not same app version and user opts to backup settings
        return balt_.askYes(balt_.Link.Frame, u'\n'.join([
            _(u'A different version of Wrye Bash was previously installed.'),
            _(u'Previous Version: ') + f'{previous_bash_version}',
            _(u'Current Version: ') + f'{AppVersion}',
            _(u'Do you want to create a backup of your Bash settings before '
              u'they are overwritten?')]), title=_(u'Create backup?'))

    @staticmethod
    def backup_filename(bak_name):
        return f'Backup Bash Settings {bak_name} ({bolt.timestamp()}) v' \
               f'{bass.settings[u"bash.version"]}-{AppVersion}.7z'

    @staticmethod
    def is_backup(backup_path):
        """Returns True if the specified path is a backup. Currently only
        checks if the file extension is 7z."""
        return backup_path.cext == u'.7z'

    def backup_settings(self, balt_):
        deprint(u'')
        deprint(u'BACKUP BASH SETTINGS: %s' % self._backup_dest_file)
        temp_settings_backup_dir = bolt.Path.tempDir()
        try:
            self._backup_settings(temp_settings_backup_dir)
            self._backup_success(balt_)
        finally:
            if temp_settings_backup_dir:
                temp_settings_backup_dir.rmtree(safety=u'WryeBash_')

    def _backup_settings(self, temp_dir):
        # copy all files to ~tmp backup dir
        for tpath, fpath in self.files.items():
            deprint(f'{tpath} <-- {fpath}')
            fpath.copyTo(temp_dir.join(tpath))
        # dump the version info and file listing
        with temp_dir.join(u'backup.dat').open(u'wb') as out:
            # Bash version the settings were saved with, if this is newer
            # than the installed settings version, do not allow restore
            pickle.dump(bass.settings[u'bash.version'], out, -1)
            # app version, if this doesn't match the installed settings
            # version, warn the user on restore
            pickle.dump(AppVersion, out, -1)
        # create the backup archive in 7z format WITH solid compression
        # may raise StateError
        backup_dir, dest7z = self._backup_dest_file.head, self._backup_dest_file.tail
        with backup_dir.join(dest7z).unicodeSafe() as safe_dest:
            command = archives.compressCommand(safe_dest, backup_dir, temp_dir)
            archives.compress7z(command, safe_dest, dest7z, temp_dir)
        bass.settings[u'bash.backupPath'] = backup_dir

    def _backup_success(self, balt_):
        if balt_ is None: return
        balt_.showInfo(balt_.Link.Frame, u'\n'.join([
            _(u'Your Bash settings have been backed up successfully.'),
            _(u'Backup Path: ') + self._backup_dest_file.s]),
                       _(u'Backup File Created'))

    @staticmethod
    def warn_message(balt_):
        if balt_ is None: return
        balt_.showWarning(balt_.Link.Frame, u'\n'.join([
            _(u'There was an error while trying to backup the Bash settings!'),
            _(u'No backup was created.')]), _(u'Unable to create backup!'))

#------------------------------------------------------------------------------
class RestoreSettings(object):
    """Class responsible for restoring settings from a 7z backup file
    created by BackupSettings. We need bass.dirs initialized to restore the
    settings, which depends on the bash.ini - so this exports also functions
    to restore the backed up ini, if it exists. Restoring the settings must
    be done on boot as soon as we are able to initialize bass#dirs."""
    __tmpdir_prefix = u'RestoreSettingsWryeBash_'
    __unset = object()

    def __init__(self, settings_file):
        self._settings_file = GPath(settings_file)
        self._saved_settings_version = self._settings_saved_with = None
        # bash.ini handling
        self._timestamped_old = self.__unset
        self._bash_ini_path = self.__unset
        # extract folder
        self._extract_dir = self.__unset

    # Restore API -------------------------------------------------------------
    def extract_backup(self):
        """Extract the backup file and return the tmp directory used. If
        the backup file is a dir we assume it was created by us before
        restarting."""
        if self._settings_file.isfile():
            temp_dir = bolt.Path.tempDir(prefix=RestoreSettings.__tmpdir_prefix)
            with self._settings_file.unicodeSafe() as safe_settings:
                archives.extract7z(safe_settings, temp_dir)
            self._extract_dir = temp_dir
        elif self._settings_file.isdir():
            self._extract_dir = self._settings_file
        else:
            raise BoltError(
                f'{self._settings_file} is not a valid backup location')
        return self._extract_dir

    def backup_ini_path(self):
        """Get the path to the backup bash.ini if it exists - must be run
        before restore_settings is called, as we need the Bash ini to
        initialize bass.dirs."""
        if self._extract_dir is self.__unset: raise BoltError(
            u'backup_ini_path: you must extract the settings file first')
        for r, d, fs in os.walk(u'%s' % self._extract_dir):
            for f in fs:
                if f == u'bash.ini':
                    self._bash_ini_path = jo(r, f)
                    return self._bash_ini_path
        else: self._bash_ini_path = None

    def restore_settings(self, bak_name, mg_name, root_prefix, mods_folder):
        if self._bash_ini_path is self.__unset: raise BoltError(
            u'restore_settings: you must handle bash ini first')
        if self._extract_dir is self.__unset: raise BoltError(
            u'restore_settings: you must extract the settings file first')
        try:
            self._restore_settings(bak_name, mg_name, root_prefix, mods_folder)
        finally:
            self.remove_extract_dir(self._extract_dir)

    def _restore_settings(self, bak_name, mg_name, root_prefix, mods_folder):
        deprint(u'')
        deprint(f'RESTORE BASH SETTINGS: {self._settings_file}')
        # backup previous Bash ini if it exists
        old_bash_ini = dirs[u'mopy'].join(u'bash.ini')
        self._timestamped_old = u''.join(
            [old_bash_ini.root.s, u'(', bolt.timestamp(), u').ini'])
        try:
            old_bash_ini.moveTo(self._timestamped_old)
            deprint(f'Existing bash.ini moved to {self._timestamped_old}')
        except StateError: # does not exist
            self._timestamped_old = None
        # restore all the settings files
        def _restore_file(dest_dir_, back_path_, *end_path):
            deprint(f'{back_path_.join(*end_path)} --> '
                    f'{dest_dir_.join(*end_path)}')
            full_back_path.join(*end_path).copyTo(dest_dir_.join(*end_path))
        restore_paths = list(_init_settings_files(bak_name, mg_name,
                                                  root_prefix, mods_folder))
        for dest_dir, back_path in restore_paths:
            full_back_path = self._extract_dir.join(back_path)
            for fname in full_back_path.list():
                if full_back_path.join(fname).isfile():
                    _restore_file(dest_dir, GPath(back_path), fname)
        # restore savegame profile settings
        back_path = GPath(u'My Games').join(mg_name, u'Saves')
        saves_dir = dirs[u'saveBase'].join(u'Saves')
        full_back_path = self._extract_dir.join(back_path)
        if full_back_path.exists():
            for root_dir, folders, files_ in full_back_path.walk(True, None,
                                                                 True):
                root_dir = GPath(u'.%s' % root_dir)
                for fname in files_:
                    _restore_file(saves_dir, back_path, root_dir, fname)

    # Validation --------------------------------------------------------------
    def incompatible_backup_error(self, curr_bak_name):
        saved_settings_version, settings_saved_with = \
            self._get_settings_versions()
        if saved_settings_version > bass.settings[u'bash.version']:
            # Disallow restoring settings saved on a newer version of bash # TODO(ut) drop?
            return u'\n'.join([
                _(u'The data format of the selected backup file is newer than '
                  u'the current Bash version!'),
                _(u'Backup v%s is not compatible with v%s') % (
                    saved_settings_version, bass.settings[u'bash.version']),
                u'', _(u'You cannot use this backup with this version of '
                       u'Bash.')]), _(
                u'Error: Settings are from newer Bash version')
        else:
            game_name = self._get_backup_game()
            if game_name != curr_bak_name:
                return u'\n'.join(
                    [_(u'The selected backup file is for %(game_name)s while '
                       u'your current game is %(current_game)s') % locals(),
                     _(u'You cannot use this backup with this game.')]), _(
                    u'Error: Settings are from a different game')
        return u'', u''

    def incompatible_backup_warn(self):
        saved_settings_version, settings_saved_with = \
            self._get_settings_versions()
        if settings_saved_with != bass.settings[u'bash.version']:
            return u'\n'.join(
                [_(u'The version of Bash used to create the selected backup '
                   u'file does not match the current Bash version!'),
                 _(u'Backup v%s does not match v%s') % (
                     settings_saved_with, bass.settings[u'bash.version']), u'',
                 _(u'Do you want to restore this backup anyway?')]), _(
                u'Warning: Version Mismatch!')
        return u'', u''

    def _get_settings_versions(self):
        if self._extract_dir is self.__unset: raise BoltError(
            u'_get_settings_versions: you must extract the settings file '
            u'first')
        if self._saved_settings_version is None:
            backup_dat = self._extract_dir.join(u'backup.dat')
            try:
                with backup_dat.open(u'rb') as ins:
                    # version of Bash that created the backed up settings
                    self._saved_settings_version = pickle.load(
                        ins, encoding='bytes')
                    # version of Bash that created the backup
                    self._settings_saved_with = pickle.load(
                        ins, encoding='bytes')
            except (OSError, pickle.UnpicklingError, EOFError) as e:
                raise BoltError(f'Failed to read {backup_dat}') from e
        return self._saved_settings_version, self._settings_saved_with

    def _get_backup_game(self):
        """Get the game this backup was for - hack, this info belongs to backup.dat."""
        for node in os.listdir(u'%s' % self._extract_dir):
            if node != u'My Games' and not node.endswith(
                    u'Mods') and os.path.isdir(self._extract_dir.join(node).s):
                return node
        raise BoltError(f'{self._extract_dir} does not contain a game dir')

    # Dialogs and cleanup/error handling --------------------------------------
    @staticmethod
    def remove_extract_dir(backup_dir):
        backup_dir.rmtree(safety=RestoreSettings.__tmpdir_prefix)

    def restore_ini(self):
        if self._timestamped_old is self.__unset:
            return # we did not move bash.ini
        if self._timestamped_old is not None:
            bolt.deprint(u'Restoring bash.ini')
            GPath(self._timestamped_old).copyTo(u'bash.ini')
        elif self._bash_ini_path:
            # remove bash.ini as it is the one from the backup
            bolt.GPath(u'bash.ini').remove()

    @staticmethod
    def warn_message(balt_, msg=u''):
        if balt_ is None: return
        balt_.showWarning(balt_.Link.Frame, u'\n'.join([
            _(u'There was an error while trying to restore your settings from '
              u'the backup file!'), msg, _(u'No settings were restored.')]),
                          _(u'Unable to restore backup!'))
