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
from os.path import join as jo

import archives
import bash
import bass
import bolt
import bosh
import bush
from . import images_list
from bolt import GPath, deprint
from balt import askSave, askOpen, askWarning, showError, showWarning, \
    showInfo, Link, BusyCursor, askYes
from exception import AbstractError, BackupCancelled

opts = None # command line arguments used when launching Bash, set on bash

def init_settings_files():
    """Construct a dict mapping directory paths to setting files. Keys are
    tuples of absolute paths to directories, paired with the relative paths
    in the backup file. Values are sets of setting files in those paths,
    or empty, meaning we have to list those paths and backup everything."""
    game, dirs = bush.game.fsName, bass.dirs
    settings_info = {
        (dirs['mopy'], jo(game, u'Mopy')): {u'bash.ini', },
        (dirs['mods'].join(u'Bash'), jo(game, u'Data', u'Bash')): {
            u'Table.dat', },
        (dirs['mods'].join(u'Docs'), jo(game, u'Data', u'Docs')): {
            u'Bash Readme Template.txt', u'Bash Readme Template.html',
            u'My Readme Template.txt', u'My Readme Template.html',
            u'wtxt_sand_small.css', u'wtxt_teal.css', },
        (dirs['modsBash'], jo(game + u' Mods', u'Bash Mod Data')): {
            u'Table.dat', },
        (dirs['modsBash'].join(u'INI Data'),
         jo(game + u' Mods', u'Bash Mod Data', u'INI Data')): {
           u'Table.dat', },
        (dirs['bainData'], jo(game + u' Mods', u'Bash Installers', u'Bash')): {
           u'Converters.dat', u'Installers.dat', },
        (dirs['saveBase'], jo(u'My Games', game)): {
            u'BashProfiles.dat', u'BashSettings.dat', u'BashLoadOrders.dat',
            u'People.dat', },
        # backup all files in Mopy\bash\l10n, Data\Bash Patches\ and
        # Data\INI Tweaks\
        (dirs['l10n'], jo(game, u'Mopy', u'bash', u'l10n')): {},
        (dirs['mods'].join(u'Bash Patches'),
         jo(game, u'Data', u'Bash Patches')): {},
        (dirs['mods'].join(u'INI Tweaks'),
         jo(game, u'Data', u'INI Tweaks')): {},
    }
    for setting_files in settings_info.itervalues():
        for settings_file in set(setting_files):
            if settings_file.endswith(u'.dat'): # add corresponding bak file
                setting_files.add(settings_file + u'.bak')
    return settings_info

#------------------------------------------------------------------------------
class BaseBackupSettings:

    def __init__(self, parent=None, path=None, do_quit=False):
        path = GPath(path)
        if path is not None and path.ext == u'' and not path.exists():
            path = None
        if path is None: path = bass.settings['bash.backupPath']
        if path is None: path = bass.dirs['modsBash']
        self.quit = do_quit
        self._dir = path
        self.archive = None
        if path.ext:
            self._dir = path.head
            self.archive = path.tail
        self.parent = parent
        self.files = {}

    def Apply(self):
        raise AbstractError

    def PromptFile(self):
        raise AbstractError

def new_bash_version_prompt_backup():
    # return False if old version == 0 (as in not previously installed)
    if bass.settings['bash.version'] == 0: return False
    # return True if not same app version and user opts to backup settings
    return not SameAppVersion() and askYes(Link.Frame, u'\n'.join([
        _(u'A different version of Wrye Bash was previously installed.'),
        _(u'Previous Version: ') + (u'%s' % bass.settings['bash.version']),
        _(u'Current Version: ') + (u'%s' % bass.AppVersion),
        _(u'Do you want to create a backup of your Bash settings before '
          u'they are overwritten?')]))

def SameAppVersion(): return bass.AppVersion == bass.settings['bash.version']

#------------------------------------------------------------------------------
class BackupSettings(BaseBackupSettings):

    def __init__(self, parent=None, path=None, do_quit=False, backup_images=None):
        BaseBackupSettings.__init__(self, parent, path, do_quit)
        game, dirs = bush.game.fsName, bass.dirs
        for (bash_dir, tmpdir), settings in init_settings_files().iteritems():
            if not settings: # we have to backup everything in there
                settings = bash_dir.list()
            tmp_dir = GPath(tmpdir)
            for name in settings:
                fpath = bash_dir.join(name)
                if fpath.exists():
                    self.files[tmp_dir.join(name)] = fpath

        #backup image files if told to
        def _isChanged(ab_path, rel_path):
            for ver_list in images_list.values():
                if  ver_list.get(rel_path.s, -1) == ab_path.size: return False
            return True
        if backup_images: # 1 is changed images only, 2 is all images
            onlyChanged = backup_images == 1
            tmpdir = GPath(jo(game, u'Mopy', u'bash', u'images'))
            image_dir = dirs['images']
            for name in image_dir.list():
                fullname = image_dir.join(name)
                if fullname.isfile() and not name.s.lower() == u'thumbs.db' \
                        and (not onlyChanged or _isChanged(fullname, name)):
                    self.files[tmpdir.join(name)] = fullname

        #backup save profile settings
        savedir = GPath(u'My Games').join(game)
        profiles = [u''] + bosh.SaveInfos.getLocalSaveDirs()
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

    def Apply(self):
        if not self.PromptFile(): return
        deprint(u'')
        deprint(_(u'BACKUP BASH SETTINGS: ') + self._dir.join(self.archive).s)
        temp_settings_backup_dir = bolt.Path.tempDir()
        try:
            self._backup_settings(temp_settings_backup_dir)
        finally:
            if temp_settings_backup_dir:
                temp_settings_backup_dir.rmtree(safety=u'WryeBash_')

    def _backup_settings(self, temp_dir):
        with BusyCursor():
            # copy all files to ~tmp backup dir
            for tpath,fpath in self.files.iteritems():
                deprint(tpath.s + u' <-- ' + fpath.s)
                fpath.copyTo(temp_dir.join(tpath))
            # dump the version info and file listing
            with temp_dir.join(u'backup.dat').open('wb') as out:
                # Bash version the settings were saved with, if this is newer
                # than the installed settings version, do not allow restore
                cPickle.dump(bass.settings['bash.version'], out, -1)
                # app version, if this doesn't match the installed settings
                # version, warn the user on restore
                cPickle.dump(bass.AppVersion, out, -1)
            # create the backup archive in 7z format WITH solid compression
            # may raise StateError
            command = archives.compressCommand(self.archive, self._dir, temp_dir)
            archives.compress7z(command, self._dir, self.archive, temp_dir)
            bass.settings['bash.backupPath'] = self._dir
        if self.quit: return
        showInfo(self.parent, u'\n'.join([
            _(u'Your Bash settings have been backed up successfully.'),
            _(u'Backup Path: ') + self._dir.join(self.archive).s]),
            _(u'Backup File Created'))

    def PromptFile(self):
        """Prompt for backup filename - return False if user cancels."""
        if self.archive is None or self._dir.join(self.archive).exists():
            filename = u'Backup Bash Settings %s (%s) v%s-%s.7z' % (
                bush.game.fsName, bolt.timestamp(), bass.settings['bash.version'],
                bass.AppVersion)
            if not self.quit:
                path = askSave(self.parent, title=_(u'Backup Bash Settings'),
                               defaultDir=self._dir, defaultFile=filename,
                               wildcard=u'*.7z')
                if not path: return False
                self._dir = path.head
                self.archive = path.tail
            elif not self.archive:
                self.archive = filename
        return True

    def WarnFailed(self):
        showWarning(self.parent, u'\n'.join([
            _(u'There was an error while trying to backup the Bash settings!'),
            _(u'No backup was created.')]),
            _(u'Unable to create backup!'))

#------------------------------------------------------------------------------
class RestoreSettings(BaseBackupSettings):
    def __init__(self, parent=None, path=None, do_quit=False, restore_images=None):
        BaseBackupSettings.__init__(self, parent, path, do_quit)
        if not self.PromptFile():
            raise BackupCancelled()
        self.restore_images = restore_images

    def Apply(self):
        temp_settings_restore_dir = bolt.Path.tempDir()
        try:
            self._Apply(temp_settings_restore_dir)
        finally:
            if temp_settings_restore_dir:
                temp_settings_restore_dir.rmtree(safety=u'WryeBash_')

    def _Apply(self, temp_dir):
        command = archives.extractCommand(self._dir.join(self.archive), temp_dir)
        archives.extract7z(command, self._dir.join(self.archive))
        with temp_dir.join(u'backup.dat').open('rb') as ins:
            # version of Bash that created the backed up settings
            saved_settings_version = cPickle.load(ins)
            # version of Bash that created the backup
            settings_saved_with = cPickle.load(ins)
        if saved_settings_version > bass.settings['bash.version']:
            # Disallow restoring settings saved on a newer version of bash # TODO(ut) drop?
            showError(self.parent, u'\n'.join([
                _(u'The data format of the selected backup file is newer than '
                u'the current Bash version!'),
                _(u'Backup v%s is not compatible with v%s') % (
                    saved_settings_version, bass.settings['bash.version']),u'',
                _(u'You cannot use this backup with this version of Bash.')]),
                      _(u'Error: Settings are from newer Bash version'))
            self.WarnFailed()
            return
        elif settings_saved_with != bass.settings['bash.version'] and \
             askWarning(self.parent, u'\n'.join([
                 _(u'The version of Bash used to create the selected backup '
                   u'file does not match the current Bash version!'),
                 _(u'Backup v%s does not match v%s') % (
                     settings_saved_with, bass.settings['bash.version']), u'',
                 _(u'Do you want to restore this backup anyway?')]),
                                           _(u'Warning: Version Mismatch!')):
            raise BackupCancelled()

        deprint(u'')
        deprint(_(u'RESTORE BASH SETTINGS: ') + self._dir.join(self.archive).s)

        # reinitialize bass.dirs using the backup copy of bash.ini if it exists
        game, dirs = bush.game.fsName, bass.dirs
        tmpBash = temp_dir.join(game, u'Mopy', u'bash.ini')

        bash.SetUserPath(tmpBash.s,opts.userPath)

        bashIni = bass.GetBashIni(tmpBash.s, reload_=True)
        bosh.initBosh(opts.personalPath, opts.localAppDataPath, bashIni)

        # restore all the settings files
        restore_paths = init_settings_files().keys()
        if self.restore_images:
            restore_paths += [
                (dirs['images'], jo(game, u'Mopy', u'bash', u'images'))]
        for dest_dir, back_path in restore_paths:
            full_back_path = temp_dir.join(back_path)
            if full_back_path.exists():
                for name in full_back_path.list():
                    if full_back_path.join(name).isfile():
                        deprint(GPath(back_path).join(name).s + u' --> '
                                + dest_dir.join(name).s)
                        full_back_path.join(name).copyTo(dest_dir.join(name))

        #restore savegame profile settings
        back_path = GPath(u'My Games').join(game, u'Saves')
        saves_dir = dirs['saveBase'].join(u'Saves')
        full_back_path = temp_dir.join(back_path)
        if full_back_path.exists():
            for root_dir, folders, files in full_back_path.walk(True,None,True):
                root_dir = GPath(u'.'+root_dir.s)
                for name in files:
                    deprint(back_path.join(root_dir,name).s + u' --> '
                            + saves_dir.join(root_dir, name).s)
                    full_back_path.join(root_dir, name).copyTo(
                        saves_dir.join(root_dir, name))

        # tell the user the restore is complete and warn about restart
        self.WarnRestart()
        if Link.Frame: # should always exist
            Link.Frame.Destroy()

    def PromptFile(self):
        #prompt for backup filename
        #returns False if user cancels
        if self.archive is None or not self._dir.join(self.archive).exists():
            path = askOpen(self.parent,_(u'Restore Bash Settings'),self._dir,u'',u'*.7z')
            if not path: return False
            self._dir = path.head
            self.archive = path.tail
        return True

    def WarnFailed(self):
        showWarning(self.parent,
            _(u'There was an error while trying to restore your settings from the backup file!')+u'\n' +
            _(u'No settings were restored.'),
            _(u'Unable to restore backup!'))

    def WarnRestart(self):
        if self.quit: return
        showWarning(self.parent,
            _(u'Your Bash settings have been successfully restored.')+u'\n' +
            _(u'Backup Path: ')+self._dir.join(self.archive).s+u'\n' +
            u'\n' +
            _(u'Before the settings can take effect, Wrye Bash must restart.')+u'\n' +
            _(u'Click OK to restart now.'),
            _(u'Bash Settings Restored'))
        Link.Frame.Restart()
