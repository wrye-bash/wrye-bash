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

"""Rollback library.

Re: bass.AppVersion, bass.settings['bash.version']

The latter is read from the settings - so on upgrading Bash it's the version of
the previous Bash install, whereupon is based the backup-on-upgrade routine.
Later on, in basher.BashApp#InitVersion, bass.settings['bash.version'] is
set to bass.AppVersion. We save both in the settings we backup:
- bass.settings['bash.version'] is saved first and corresponds to the version
the settings were created with
- bass.AppVersion, saved second, is the version of Bash currently executing
the backup
"""

import cPickle
import os
from os.path import join as jo

import archives
import bass # for settings (duh!)
import bolt
import initialization
from bass import dirs, AppVersion
from bolt import GPath, deprint
from exception import BoltError, StateError

def _init_settings_files(fsName_):
    """Construct a dict mapping directory paths to setting files. Keys are
    tuples of absolute paths to directories, paired with the relative paths
    in the backup file. Values are sets of setting files in those paths,
    or empty, meaning we have to list those paths and backup everything."""
    if not initialization.bash_dirs_initialized:
        raise BoltError(u'_init_settings_files: Bash dirs are not initialized')
    settings_info = {
        (dirs['mopy'], jo(fsName_, u'Mopy')): {u'bash.ini', },
        (dirs['mods'].join(u'Bash'), jo(fsName_, u'Data', u'Bash')): {
            u'Table.dat', },
        (dirs['mods'].join(u'Docs'), jo(fsName_, u'Data', u'Docs')): {
            u'Bash Readme Template.txt', u'Bash Readme Template.html',
            u'My Readme Template.txt', u'My Readme Template.html',
            u'wtxt_sand_small.css', u'wtxt_teal.css', },
        (dirs['modsBash'], jo(fsName_ + u' Mods', u'Bash Mod Data')): {
            u'Table.dat', },
        (dirs['modsBash'].join(u'INI Data'),
         jo(fsName_ + u' Mods', u'Bash Mod Data', u'INI Data')): {
           u'Table.dat', },
        (dirs['bainData'],
         jo(fsName_ + u' Mods', u'Bash Installers', u'Bash')): {
           u'Converters.dat', u'Installers.dat', },
        (dirs['saveBase'], jo(u'My Games', fsName_)): {
            u'BashProfiles.dat', u'BashSettings.dat', u'BashLoadOrders.dat',
            u'People.dat', },
        # backup all files in Mopy\bash\l10n, Data\Bash Patches\ and
        # Data\INI Tweaks\
        (dirs['l10n'], jo(fsName_, u'Mopy', u'bash', u'l10n')): {},
        (dirs['mods'].join(u'Bash Patches'),
         jo(fsName_, u'Data', u'Bash Patches')): {},
        (dirs['mods'].join(u'INI Tweaks'),
         jo(fsName_, u'Data', u'INI Tweaks')): {},
    }
    for setting_files in settings_info.itervalues():
        for settings_file in set(setting_files):
            if settings_file.endswith(u'.dat'): # add corresponding bak file
                setting_files.add(settings_file + u'.bak')
    return settings_info

#------------------------------------------------------------------------------
class BackupSettings(object):
    def __init__(self, settings_file, fsName):
        self._backup_dest_file = settings_file # absolute path to dest 7z file
        self.files = {}
        for (bash_dir, tmpdir), setting_files in \
                _init_settings_files(fsName).iteritems():
            if not setting_files: # we have to backup everything in there
                setting_files = bash_dir.list()
            tmp_dir = GPath(tmpdir)
            for name in setting_files:
                fpath = bash_dir.join(name)
                if fpath.exists():
                    self.files[tmp_dir.join(name)] = fpath
        # backup save profile settings
        savedir = GPath(u'My Games').join(fsName)
        profiles = [u''] + initialization.getLocalSaveDirs()
        for profile in profiles:
            pluginsTxt = (u'Saves', profile, u'plugins.txt')
            loadorderTxt = (u'Saves', profile, u'loadorder.txt')
            for txt in (pluginsTxt, loadorderTxt):
                tpath = savedir.join(*txt)
                fpath = dirs['saveBase'].join(*txt)
                if fpath.exists(): self.files[tpath] = fpath
            table = (u'Saves', profile, u'Bash', u'Table.dat')
            tpath = savedir.join(*table)
            fpath = dirs['saveBase'].join(*table)
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
            _(u'Previous Version: ') + (u'%s' % previous_bash_version),
            _(u'Current Version: ') + (u'%s' % AppVersion),
            _(u'Do you want to create a backup of your Bash settings before '
              u'they are overwritten?')]))

    @staticmethod
    def backup_filename(fsName_):
        return u'Backup Bash Settings %s (%s) v%s-%s.7z' % (
            fsName_, bolt.timestamp(), bass.settings['bash.version'],
            AppVersion)

    def backup_settings(self, balt_):
        deprint(u'')
        deprint(_(u'BACKUP BASH SETTINGS: ') + self._backup_dest_file.s)
        temp_settings_backup_dir = bolt.Path.tempDir()
        try:
            self._backup_settings(temp_settings_backup_dir)
            self._backup_success(balt_)
        finally:
            if temp_settings_backup_dir:
                temp_settings_backup_dir.rmtree(safety=u'WryeBash_')

    def _backup_settings(self, temp_dir):
        # copy all files to ~tmp backup dir
        for tpath, fpath in self.files.iteritems():
            deprint(tpath.s + u' <-- ' + fpath.s)
            fpath.copyTo(temp_dir.join(tpath))
        # dump the version info and file listing
        with temp_dir.join(u'backup.dat').open('wb') as out:
            # Bash version the settings were saved with, if this is newer
            # than the installed settings version, do not allow restore
            cPickle.dump(bass.settings['bash.version'], out, -1)
            # app version, if this doesn't match the installed settings
            # version, warn the user on restore
            cPickle.dump(AppVersion, out, -1)
        # create the backup archive in 7z format WITH solid compression
        # may raise StateError
        backup_dir, dest7z = self._backup_dest_file.head, self._backup_dest_file.tail
        command = archives.compressCommand(dest7z, backup_dir, temp_dir)
        archives.compress7z(command, backup_dir, dest7z, temp_dir)
        bass.settings['bash.backupPath'] = backup_dir

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

    def __init__(self, settings_file=None):
        self._settings_file = settings_file
        self._saved_settings_version = self._settings_saved_with = None

    def _get_settings_versions(self, tmp_dir):
        if self._saved_settings_version is None:
            with tmp_dir.join(u'backup.dat').open('rb') as ins:
                # version of Bash that created the backed up settings
                self._saved_settings_version = cPickle.load(ins)
                # version of Bash that created the backup
                self._settings_saved_with = cPickle.load(ins)
        return self._saved_settings_version, self._settings_saved_with

    @staticmethod
    def restore_ini(tmp_dir):
        backup_bash_ini = RestoreSettings.bash_ini_path(tmp_dir)
        dest_dir = dirs['mopy']
        old_bash_ini = dest_dir.join(u'bash.ini')
        timestamped_old = u''.join(
            [old_bash_ini.root.s, u'(', bolt.timestamp(), u').ini'])
        try:
            old_bash_ini.moveTo(timestamped_old)
        except StateError: # does not exist
            timestamped_old = None
        if backup_bash_ini is not None:
            GPath(backup_bash_ini).copyTo(old_bash_ini)
        return backup_bash_ini, timestamped_old

    @staticmethod
    def remove_extract_dir(backup_dir):
        backup_dir.rmtree(safety=RestoreSettings.__tmpdir_prefix)

    @staticmethod
    def bash_ini_path(tmp_dir):
        # search for Bash ini
        for r, d, fs in bolt.walkdir(u'%s' % tmp_dir):
            for f in fs:
                if f == u'bash.ini':
                    return jo(r, f)
        return None

    @staticmethod
    def _get_backup_game(tmp_dir):
        """Get the game this backup was for - hack, this info belongs to backup.dat."""
        for node in os.listdir(u'%s' % tmp_dir):
            if node != u'My Games' and not node.endswith(
                    u'Mods') and os.path.isdir(tmp_dir.join(node).s):
                return node
        raise BoltError(u'%s does not contain a game dir' % tmp_dir)

    @staticmethod
    def extract_backup(backup_path):
        """Extract the backup file and return the tmp directory used. If
        the backup file is a dir we assume it was created by us before
        restarting."""
        backup_path = GPath(backup_path)
        if backup_path.isfile():
            temp_dir = bolt.Path.tempDir(prefix=RestoreSettings.__tmpdir_prefix)
            command = archives.extractCommand(backup_path, temp_dir)
            archives.extract7z(command, backup_path)
            return temp_dir
        elif backup_path.isdir():
            return backup_path
        raise BoltError(
            u'%s is not a valid backup location' % backup_path)

    def restore_settings(self, backup_path, fsName):
        temp_settings_restore_dir = self.extract_backup(backup_path)
        try:
            self._restore_settings(temp_settings_restore_dir, fsName)
        finally:
            if temp_settings_restore_dir:
                self.remove_extract_dir(temp_settings_restore_dir)

    def incompatible_backup_error(self, temp_dir, current_game):
        saved_settings_version, settings_saved_with = \
            self._get_settings_versions(temp_dir)
        if saved_settings_version > bass.settings['bash.version']:
            # Disallow restoring settings saved on a newer version of bash # TODO(ut) drop?
            return u'\n'.join([
                _(u'The data format of the selected backup file is newer than '
                  u'the current Bash version!'),
                _(u'Backup v%s is not compatible with v%s') % (
                    saved_settings_version, bass.settings['bash.version']),
                u'', _(u'You cannot use this backup with this version of '
                       u'Bash.')]), _(
                u'Error: Settings are from newer Bash version')
        else:
            game_name = RestoreSettings._get_backup_game(temp_dir)
            if game_name != current_game:
                return u'\n'.join(
                    [_(u'The selected backup file is for %(game_name)s while '
                       u'your current game is %(current_game)s') % locals(),
                     _(u'You cannot use this backup with this game.')]), _(
                    u'Error: Settings are from a different game')
        return u'', u''

    def incompatible_backup_warn(self, temp_dir):
        saved_settings_version, settings_saved_with = \
            self._get_settings_versions(temp_dir)
        if settings_saved_with != bass.settings['bash.version']:
            return u'\n'.join(
                [_(u'The version of Bash used to create the selected backup '
                   u'file does not match the current Bash version!'),
                 _(u'Backup v%s does not match v%s') % (
                     settings_saved_with, bass.settings['bash.version']), u'',
                 _(u'Do you want to restore this backup anyway?')]), _(
                u'Warning: Version Mismatch!')
        return u'', u''

    def _restore_settings(self, temp_dir, fsName):
        deprint(u'')
        deprint(_(u'RESTORE BASH SETTINGS: ') + self._settings_file.s)
        # restore all the settings files
        restore_paths = _init_settings_files(fsName).keys()
        for dest_dir, back_path in restore_paths:
            full_back_path = temp_dir.join(back_path)
            for name in full_back_path.list():
                if full_back_path.join(name).isfile():
                    deprint(GPath(back_path).join(
                        name).s + u' --> ' + dest_dir.join(name).s)
                    full_back_path.join(name).copyTo(dest_dir.join(name))
        # restore savegame profile settings
        back_path = GPath(u'My Games').join(fsName, u'Saves')
        saves_dir = dirs['saveBase'].join(u'Saves')
        full_back_path = temp_dir.join(back_path)
        if full_back_path.exists():
            for root_dir, folders, files_ in full_back_path.walk(True,None,True):
                root_dir = GPath(u'.'+root_dir.s)
                for name in files_:
                    deprint(back_path.join(root_dir,name).s + u' --> '
                            + saves_dir.join(root_dir, name).s)
                    full_back_path.join(root_dir, name).copyTo(
                        saves_dir.join(root_dir, name))

    @staticmethod
    def warn_message(balt_):
        if balt_ is None: return
        balt_.showWarning(balt_.Link.Frame, u'\n'.join([
            _(u'There was an error while trying to restore your settings from '
              u'the backup file!'), _(u'No settings were restored.')]),
                          _(u'Unable to restore backup!'))
