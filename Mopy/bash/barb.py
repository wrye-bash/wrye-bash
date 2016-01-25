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

"""Rollback library."""

import cPickle
import bash
import bass
import bolt
import bosh
import bush
from . import images_list
from bolt import BoltError, AbstractError, GPath, deprint
from balt import askSave, askYes, askOpen, askWarning, showError, \
    showWarning, showInfo, Link, BusyCursor

#------------------------------------------------------------------------------
class BackupCancelled(BoltError):
# user cancelled operation
    def __init__(self,message=u'Cancelled'):
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class BaseBackupSettings:
    verApp = bass.AppVersion

    def __init__(self, parent=None, path=None, do_quit=False):
        if path is not None and path.ext == u'' and not path.exists():
            path = None
        if path is None: path = bosh.settings['bash.backupPath']
        if path is None: path = bass.dirs['modsBash']
        self.quit = do_quit
        self._dir = path
        self.archive = None
        if path.ext:
            self._dir = path.head
            self.archive = path.tail
        self.parent = parent
        self.verDat = bosh.settings['bash.version']
        self.files = {}
        self.tmp = None

    def __del__(self): ## FIXME: does not delete immediately - used to lead to
    # file not found as ~tmp was deleted in mid restore ....
        if self.tmp and self.tmp.exists(): self.tmp.rmtree(safety=u'WryeBash_')

    def maketmp(self):
        # create a ~tmp directory
        self.tmp = bolt.Path.tempDir()

    def Apply(self):
        raise AbstractError

    def PromptFile(self):
        raise AbstractError

    @staticmethod
    def PromptConfirm(msg=None):
        raise AbstractError

    def PromptMismatch(self):
        raise AbstractError

    def CmpDataVersion(self):
        return cmp(self.verDat, bosh.settings['bash.version'])

    def SameDataVersion(self):
        return not self.CmpDataVersion()

    @staticmethod
    def SameAppVersion():
        return not cmp(bass.AppVersion, bosh.settings['bash.version'])

#------------------------------------------------------------------------------
class BackupSettings(BaseBackupSettings):

    def __init__(self, parent=None, path=None, do_quit=False, backup_images=None):
        BaseBackupSettings.__init__(self, parent, path, do_quit)
        game, dirs = bush.game.fsName, bass.dirs
        for path, name, tmpdir in (
              (dirs['mopy'],                      u'bash.ini',             game+u'\\Mopy'),
              (dirs['mods'].join(u'Bash'),        u'Table',                game+u'\\Data\\Bash'),
              (dirs['mods'].join(u'Docs'),        u'Bash Readme Template', game+u'\\Data\\Docs'),
              (dirs['mods'].join(u'Docs'),        u'Bashed Lists',         game+u'\\Data\\Docs'),
              (dirs['mods'].join(u'Docs'),        u'wtxt_sand_small.css',  game+u'\\Data\\Docs'),
              (dirs['mods'].join(u'Docs'),        u'wtxt_teal.css',        game+u'\\Data\\Docs'),
              (dirs['modsBash'],                  u'Table',                game+u' Mods\\Bash Mod Data'),
              (dirs['modsBash'].join(u'INI Data'),u'Table',                game+u' Mods\\Bash Mod Data\\INI Data'),
              (dirs['bainData'],                  u'Converters',           game+u' Mods\\Bash Installers\\Bash'),
              (dirs['bainData'],                  u'Installers',           game+u' Mods\\Bash Installers\\Bash'),
              (dirs['userApp'],                   u'Profiles',             u'LocalAppData\\'+game),
              (dirs['userApp'],                   u'bash config',          u'LocalAppData\\'+game),
              (dirs['saveBase'],                  u'BashProfiles',         u'My Games\\'+game),
              (dirs['saveBase'],                  u'BashSettings',         u'My Games\\'+game),
              (dirs['saveBase'],                  u'Messages',             u'My Games\\'+game),
              (dirs['saveBase'],                  u'ModeBase',             u'My Games\\'+game),
              (dirs['saveBase'],                  u'People',               u'My Games\\'+game),
                ):
            tmpdir = GPath(tmpdir)
            for ext in (u'',u'.dat',u'.pkl',u'.html',u'.txt'): # hack so the above file list can be shorter, could include rogue files but not very likely
                tpath = tmpdir.join(name+ext)
                fpath = path.join(name+ext)
                if fpath.exists(): self.files[tpath] = fpath
                if fpath.backup.exists(): self.files[tpath.backup] = fpath.backup

        #backup all files in Mopy\Data, Data\Bash Patches\ and Data\INI Tweaks
        for path, tmpdir in (
              (dirs['l10n'],                      game+u'\\Mopy\\bash\\l10n'),
              (dirs['mods'].join(u'Bash Patches'),game+u'\\Data\\Bash Patches'),
              (dirs['mods'].join(u'INI Tweaks'),  game+u'\\Data\\INI Tweaks'),
                ):
            tmpdir = GPath(tmpdir)
            for name in path.list():
                if path.join(name).isfile():
                    self.files[tmpdir.join(name)] = path.join(name)

        #backup image files if told to
        def _isChanged(abs_path, rel_path):
            for ver_list in images_list.values():
                if  ver_list.get(rel_path.s, -1) == abs_path.size: return False
            return True
        if backup_images: # 1 is changed images only, 2 is all images
            onlyChanged = backup_images == 1
            tmpdir = GPath(game+u'\\Mopy\\bash\\images')
            path = dirs['images']
            for name in path.list():
                fullname = path.join(name)
                if fullname.isfile() and not name.s.lower() == u'thumbs.db' \
                        and (not onlyChanged or _isChanged(fullname, name)):
                    self.files[tmpdir.join(name)] = fullname

        #backup save profile settings
        savedir = GPath(u'My Games\\'+game)
        profiles = [u''] + bosh.SaveInfos.getLocalSaveDirs()
        for profile in profiles:
            pluginsTxt = (u'Saves', profile, u'plugins.txt')
            loadorderTxt = (u'Saves', profile, u'loadorder.txt')
            for txt in (pluginsTxt, loadorderTxt):
                tpath = savedir.join(*txt)
                fpath = dirs['saveBase'].join(*txt)
                if fpath.exists(): self.files[tpath] = fpath
            for ext in (u'.dat', u'.pkl'):
                table = (u'Saves', profile, u'Bash', u'Table' + ext)
                tpath = savedir.join(*table)
                fpath = dirs['saveBase'].join(*table)
                if fpath.exists(): self.files[tpath] = fpath
                if fpath.backup.exists():
                    self.files[tpath.backup] = fpath.backup

    def Apply(self):
        if not self.PromptFile(): return
        deprint(u'')
        deprint(_(u'BACKUP BASH SETTINGS: ') + self._dir.join(self.archive).s)
        with BusyCursor():
            # copy all files to ~tmp backup dir
            for tpath,fpath in self.files.iteritems():
                deprint(tpath.s + u' <-- ' + fpath.s)
                fpath.copyTo(self.tmp.join(tpath))
            # dump the version info and file listing
            with self.tmp.join(u'backup.dat').open('wb') as out:
                # data version, if this doesn't match the installed data
                # version, do not allow restore
                cPickle.dump(self.verDat, out, -1)
                # app version, if this doesn't match the installer app version,
                # warn the user on restore
                cPickle.dump(self.verApp, out, -1)
            # create the backup archive in 7z format WITH solid compression
            # may raise StateError
            command = bosh.compressCommand(self.archive, self._dir, self.tmp)
            bolt.compress7z(command, self._dir, self.archive, self.tmp)
            bosh.settings['bash.backupPath'] = self._dir
        self.InfoSuccess()

    def PromptFile(self):
        """Prompt for backup filename - return False if user cancels."""
        if self.archive is None or self._dir.join(self.archive).exists():
            filename = u'Backup Bash Settings %s (%s) v%s-%s.7z' % (
                bush.game.fsName, bolt.timestamp(), self.verDat, self.verApp)
            if not self.quit:
                path = askSave(self.parent, title=_(u'Backup Bash Settings'),
                               defaultDir=self._dir, defaultFile=filename,
                               wildcard=u'*.7z')
                if not path: return False
                self._dir = path.head
                self.archive = path.tail
            elif not self.archive:
                self.archive = filename
        self.maketmp()
        return True

    @staticmethod
    def PromptConfirm(msg=None):
        msg = msg or _(u'Do you want to backup your Bash settings now?')
        return askYes(Link.Frame, msg, _(u'Backup Bash Settings?'))

    @staticmethod
    def PromptMismatch():
        #returns False if same app version or old version == 0 (as in not previously installed) or user cancels
        if bosh.settings['bash.version'] == 0: return False
        return not BaseBackupSettings.SameAppVersion() and BackupSettings.PromptConfirm(
            _(u'A different version of Wrye Bash was previously installed.')+u'\n' +
            _(u'Previous Version: ')+(u'%s\n' % bosh.settings['bash.version']) +
            _(u'Current Version: ')+(u'%s\n' % bass.AppVersion) +
            _(u'Do you want to create a backup of your Bash settings before they are overwritten?'))

    def PromptContinue(self):
        #returns False if user quits
        return not askYes(self.parent,
            _(u'You did not create a backup of the Bash settings.')+u'\n' +
            _(u'If you continue, your current settings may be overwritten.')+u'\n' +
            _(u'Do you want to quit Wrye Bash now?'),
            _(u'No backup created!'))

    def PromptQuit(self):
        #returns True if user quits
        return askYes(self.parent,
            _(u'There was an error while trying to backup the Bash settings!')+u'\n' +
            _(u'If you continue, your current settings may be overwritten.')+u'\n' +
            _(u'Do you want to quit Wrye Bash now?'),
            _(u'Unable to create backup!'))

    def WarnFailed(self):
        showWarning(self.parent,
            _(u'There was an error while trying to backup the Bash settings!')+u'\n' +
            _(u'No backup was created.'),
            _(u'Unable to create backup!'))

    def InfoSuccess(self):
        if self.quit: return
        showInfo(self.parent,
            _(u'Your Bash settings have been backed up successfully.')+u'\n' +
            _(u'Backup Path: ')+self._dir.join(self.archive).s+u'\n',
            _(u'Backup File Created'))

#------------------------------------------------------------------------------
class RestoreSettings(BaseBackupSettings):
    def __init__(self, parent=None, path=None, do_quit=False, restore_images=None):
        BaseBackupSettings.__init__(self, parent, path, do_quit)
        if not self.PromptFile():
            raise BackupCancelled()
        command = bosh.extractCommand(self._dir.join(self.archive), self.tmp)
        bolt.extract7z(command, self._dir.join(self.archive))
        with self.tmp.join(u'backup.dat').open('rb') as ins:
            self.verDat = cPickle.load(ins)
            self.verApp = cPickle.load(ins)
            self.restore_images = restore_images

    def Apply(self):
        if self.ErrorConflict():
            self.WarnFailed()
            return
        elif not self.PromptMismatch():
            raise BackupCancelled()

        deprint(u'')
        deprint(_(u'RESTORE BASH SETTINGS: ') + self._dir.join(self.archive).s)

        # reinitialize bass.dirs using the backup copy of bash.ini if it exists
        game, dirs = bush.game.fsName, bass.dirs
        tmpBash = self.tmp.join(game+u'\\Mopy\\bash.ini')
        opts, args = bash.opts, bash.extra

        bash.SetUserPath(tmpBash.s,opts.userPath)

        bashIni = bass.GetBashIni(tmpBash.s, reload_=True)
        bosh.initBosh(opts.personalPath, opts.localAppDataPath,
                      opts.oblivionPath, bashIni)

        # restore all the settings files
        restore_paths = (
                (dirs['mopy'],                      game+u'\\Mopy'),
                (dirs['mods'].join(u'Bash'),        game+u'\\Data\\Bash'),
                (dirs['mods'].join(u'Bash Patches'),game+u'\\Data\\Bash Patches'),
                (dirs['mods'].join(u'Docs'),        game+u'\\Data\\Docs'),
                (dirs['mods'].join(u'INI Tweaks'),  game+u'\\Data\\INI Tweaks'),
                (dirs['modsBash'],                  game+u' Mods\\Bash Mod Data'),
                (dirs['modsBash'].join(u'INI Data'),game+u' Mods\\Bash Mod Data\\INI Data'),
                (dirs['bainData'],                  game+u' Mods\\Bash Installers\\Bash'),
                (dirs['userApp'],                   u'LocalAppData\\'+game),
                (dirs['saveBase'],                  u'My Games\\'+game),
                )
        if 293 >= self.verApp:
            # restore from old data paths
            restore_paths += (
                (dirs['l10n'],                      game+u'\\Data'),)
            if self.restore_images:
                restore_paths += (
                    (dirs['images'],                game+u'\\Mopy\\images'),)
        else:
            restore_paths += (
                (dirs['l10n'],                      game+u'\\bash\\l10n'),)
            if self.restore_images:
                restore_paths += (
                    (dirs['images'],                game+u'\\Mopy\\bash\\images'),)
        for fpath, tpath in restore_paths:
            path = self.tmp.join(tpath)
            if path.exists():
                for name in path.list():
                    if path.join(name).isfile():
                        deprint(GPath(tpath).join(name).s + u' --> '
                                + fpath.join(name).s)
                        path.join(name).copyTo(fpath.join(name))

        #restore savegame profile settings
        tpath = GPath(u'My Games\\'+game+u'\\Saves')
        fpath = dirs['saveBase'].join(u'Saves')
        path = self.tmp.join(tpath)
        if path.exists():
            for root, folders, files in path.walk(True,None,True):
                root = GPath(u'.'+root.s)
                for name in files:
                    deprint(tpath.join(root,name).s + u' --> '
                            + fpath.join(root,name).s)
                    path.join(root,name).copyTo(fpath.join(root,name))

        # tell the user the restore is compete and warn about restart
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
        self.maketmp()
        return True

    @staticmethod
    def PromptConfirm(msg=None):
        # returns False if user cancels
        msg = msg or _(u'Do you want to restore your Bash settings from a backup?')
        msg += u'\n\n' + _(u'This will force a restart of Wrye Bash once your settings are restored.')
        return askYes(Link.Frame, msg, _(u'Restore Bash Settings?'))

    def PromptMismatch(self):
        # return True if same app version or user confirms
        return BaseBackupSettings.SameAppVersion() or askWarning(self.parent,
              _(u'The version of Bash used to create the selected backup file does not match the current Bash version!')+u'\n' +
              _(u'Backup v%s does not match v%s') % (self.verApp, bosh.settings['bash.version']) + u'\n' +
              u'\n' +
              _(u'Do you want to restore this backup anyway?'),
              _(u'Warning: Version Mismatch!'))

    def ErrorConflict(self):
        #returns True if the data format doesn't match
        if self.CmpDataVersion() > 0:
            showError(self.parent,
                  _(u'The data format of the selected backup file is newer than the current Bash version!')+u'\n' +
                  _(u'Backup v%s is not compatible with v%s') % (self.verApp, bosh.settings['bash.version']) + u'\n' +
                  u'\n' +
                  _(u'You cannot use this backup with this version of Bash.'),
                  _(u'Error: Version Conflict!'))
            return True
        #end if
        return False

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

# Main ------------------------------------------------------------------------
if __name__ == '__main__':
    print _(u'Compiled')
