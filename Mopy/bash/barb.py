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

# Rollback library.

import os
import re
import datetime
import cPickle
import StringIO
from subprocess import Popen, PIPE
import bash
import bass
import bosh
import basher
import bolt
import bush
from bosh import startupinfo, dirs
from bolt import BoltError, AbstractError, StateError, GPath, Progress, deprint
from balt import askSave, askYes, askOpen, askWarning, showError, showWarning, showInfo

#------------------------------------------------------------------------------
class BackupCancelled(BoltError):
# user cancelled operation
    def __init__(self,message=u'Cancelled'):
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class BaseBackupSettings:
    def __init__(self, parent=None, path=None, quit=False):
        if path != None and path.ext == u'' and not path.exists(): path = None
        if path == None: path = basher.settings['bash.backupPath']
        if path == None: path = dirs['modsBash']
        self.quit = quit
        self.dir = path
        self.archive = None
        if path.ext:
            self.dir = path.head
            self.archive = path.tail
        #end if
        self.parent = parent
        self.verDat = basher.settings['bash.version']
        self.verApp = bass.AppVersion
        self.files = {}
        self.tmp = None

    def __del__(self):
        if self.tmp and self.tmp.exists(): self.tmp.rmtree(u'~tmp')

    def maketmp(self):
        # create a ~tmp directory
        self.tmp = self.dir.join(u'~tmp')
        if self.tmp.exists(): self.tmp.rmtree(u'~tmp')
        self.tmp.makedirs()

    def Apply(self):
        raise AbstractError

    def PromptFile(self):
        raise AbstractError

    def PromptConfirm(self,msg=None):
        raise AbstractError

    def PromptMismatch(self):
        raise AbstractError

    def CmpDataVersion(self):
        return cmp(self.verDat, basher.settings['bash.version'])

    def CmpAppVersion(self):
        # Changed to prompt updating on any version change
        # Needs to check the cached value in settings for the initial upgrade check
        return cmp(self.verApp, basher.settings['bash.version'])

    def SameDataVersion(self):
        return not self.CmpDataVersion()

    def SameAppVersion(self):
        return not self.CmpAppVersion()

#------------------------------------------------------------------------------
class BackupSettings(BaseBackupSettings):
    def __init__(self, parent=None, path=None, quit=False, backup_images=None):
        BaseBackupSettings.__init__(self,parent,path,quit)
        game = bush.game.fsName
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
            #end for
        #end for

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
        if backup_images == 1: #changed images only
            tmpdir = GPath(game+u'\\Mopy\\bash\\images')
            path = dirs['images']
            for name in path.list():
                fullname = path.join(name)
                if fullname.isfile():
                    changed = True
                    for ver_list in bolt.images_list:
                        if name.s in bolt.images_list[ver_list] and bolt.images_list[ver_list][name.s] == fullname.size:
                            changed = False
                    if changed and not name.s.lower() == u'thumbs.db':
                        self.files[tmpdir.join(name)] = fullname
        elif backup_images == 2: #all images
            tmpdir = GPath(game+u'\\Mopy\\bash\\images')
            path = dirs['images']
            for name in path.list():
                if path.join(name).isfile() and not name.s.lower() == u'thumbs.db':
                    self.files[tmpdir.join(name)] = path.join(name)

        #backup save profile settings
        savedir = GPath(u'My Games\\'+game)
        profiles = [u''] + [x for x in dirs['saveBase'].join(u'Saves').list() if dirs['saveBase'].join(u'Saves',x).isdir() and x != u'bash']
        for profile in profiles:
            tpath = savedir.join(u'Saves',profile,u'plugins.txt')
            fpath = dirs['saveBase'].join(u'Saves',profile,u'plugins.txt')
            if fpath.exists(): self.files[tpath] = fpath
            for ext in (u'.dat',u'.pkl'):
                tpath = savedir.join(u'Saves',profile,u'Bash',u'Table'+ext)
                fpath = dirs['saveBase'].join(u'Saves',profile,u'Bash',u'Table'+ext)
                if fpath.exists(): self.files[tpath] = fpath
                if fpath.backup.exists(): self.files[tpath.backup] = fpath.backup
            #end for
        #end for

    def Apply(self):
        if not self.PromptFile(): return

        deprint(u'')
        deprint(_(u'BACKUP BASH SETTINGS: ') + self.dir.join(self.archive).s)

        # copy all files to ~tmp backup dir
        for tpath,fpath in self.files.iteritems():
            deprint(tpath.s + u' <-- ' + fpath.s)
            fpath.copyTo(self.tmp.join(tpath))
        #end for

        # dump the version info and file listing
        with self.tmp.join(u'backup.dat').open('wb') as out:
            cPickle.dump(self.verDat, out, -1) #data version, if this doesn't match the installed data version, do not allow restore
            cPickle.dump(self.verApp, out, -1) #app version, if this doesn't match the installer app version, warn the user on restore

        # create the backup archive
        try:
            pack7z(self.dir.join(self.archive),self.tmp)
        except StateError, e:
            raise
        #end try
        basher.settings['bash.backupPath'] = self.dir
        self.InfoSuccess()

    def PromptFile(self):
        #prompt for backup filename
        #returns False if user cancels
        if self.archive == None or self.dir.join(self.archive).exists():
            dt = datetime.datetime.now()
            file = u'Backup Bash Settings %s (%s) v%s-%s.7z' % (bush.game.fsName,dt.strftime(u'%Y-%m-%d %H.%M.%S'),self.verDat,self.verApp)
            if not self.quit:
                path = askSave(self.parent,_(u'Backup Bash Settings'),self.dir,file,u'*.7z')
                if not path: return False
                self.dir = path.head
                self.archive = path.tail
            elif not self.archive:
                self.archive = file
        #end if
        self.maketmp()
        return True

    def PromptConfirm(self,msg=None):
        msg = msg or _(u'Do you want to backup your Bash settings now?')
        return askYes(self.parent,msg,_(u'Backup Bash Settings?'))

    def PromptMismatch(self):
        #returns False if same app version or old version == 0 (as in not previously installed) or user cancels
        if basher.settings['bash.version'] == 0: return False
        return not self.SameAppVersion() and self.PromptConfirm(
            _(u'A different version of Wrye Bash was previously installed.')+u'\n' +
            _(u'Previous Version: ')+(u'%s\n' % basher.settings['bash.version']) +
            _(u'Current Version: ')+(u'%s\n' % self.verApp) +
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
            _(u'Backup Path: ')+self.dir.join(self.archive).s+u'\n',
            _(u'Backup File Created'))

#------------------------------------------------------------------------------
class RestoreSettings(BaseBackupSettings):
    def __init__(self, parent=None, path=None, quit=False, restore_images=None):
        BaseBackupSettings.__init__(self,parent,path,quit)

        if not self.PromptFile():
            raise BackupCancelled()
        #end if

        try:
            unpack7z(self.dir.join(self.archive), self.tmp)
        except StateError:
            self.WarnFailed()
            return
        #end try
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
        deprint(_(u'RESTORE BASH SETTINGS: ') + self.dir.join(self.archive).s)

        # reinitialize bosh.dirs using the backup copy of bash.ini if it exists
        game = bush.game.fsName
        tmpBash = self.tmp.join(game+u'\\Mopy\\bash.ini')
        opts, args = bash.opts, bash.extra

        bash.SetUserPath(tmpBash.s,opts.userPath)

        bashIni = bash.GetBashIni(tmpBash.s)
        bosh.initBosh(opts.personalPath,opts.localAppDataPath,opts.oblivionPath)

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
                        deprint(GPath(tpath).join(name).s + u' --> ' + fpath.join(name).s)
                        path.join(name).copyTo(fpath.join(name))

        #restore savegame profile settings
        tpath = GPath(u'My Games\\'+game+u'\\Saves')
        fpath = dirs['saveBase'].join(u'Saves')
        path = self.tmp.join(tpath)
        if path.exists():
            for root, folders, files in path.walk(True,None,True):
                root = GPath(u'.'+root.s)
                for name in files:
                    deprint(tpath.join(root,name).s + u' --> ' + fpath.join(root,name).s)
                    path.join(root,name).copyTo(fpath.join(root,name))

        # tell the user the restore is compete and warn about restart
        self.WarnRestart()
        if basher.bashFrame: # should always exist
            basher.bashFrame.Destroy()

    def PromptFile(self):
        #prompt for backup filename
        #returns False if user cancels
        if self.archive == None or not self.dir.join(self.archive).exists():
            path = askOpen(self.parent,_(u'Restore Bash Settings'),self.dir,u'',u'*.7z')
            if not path: return False
            self.dir = path.head
            self.archive = path.tail
        #end if
        self.maketmp()
        return True

    def PromptConfirm(self,msg=None):
        # returns False if user cancels
        msg = msg or _(u'Do you want to restore your Bash settings from a backup?')
        msg += u'\n\n' + _(u'This will force a restart of Wrye Bash once your settings are restored.')
        return askYes(self.parent,msg,_(u'Restore Bash Settings?'))

    def PromptMismatch(self):
        # return True if same app version or user confirms
        return self.SameAppVersion() or askWarning(self.parent,
              _(u'The version of Bash used to create the selected backup file does not match the current Bash version!')+u'\n' +
              _(u'Backup v%s does not match v%s') % (self.verApp, basher.settings['bash.version']) + u'\n' +
              u'\n' +
              _(u'Do you want to restore this backup anyway?'),
              _(u'Warning: Version Mismatch!'))

    def ErrorConflict(self):
        #returns True if the data format doesn't match
        if self.CmpDataVersion() > 0:
            showError(self.parent,
                  _(u'The data format of the selected backup file is newer than the current Bash version!')+u'\n' +
                  _(u'Backup v%s is not compatible with v%s') % (self.verApp, basher.settings['bash.version']) + u'\n' +
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
            _(u'Backup Path: ')+self.dir.join(self.archive).s+u'\n' +
            u'\n' +
            _(u'Before the settings can take effect, Wrye Bash must restart.')+u'\n' +
            _(u'Click OK to restart now.'),
            _(u'Bash Settings Restored'))
        basher.bashFrame.Restart()

#------------------------------------------------------------------------------
def pack7z(dstFile, srcDir, progress=None):
    # archive srcdir to dstFile in 7z format without solid compression
    progress = progress or Progress()

    #--Used solely for the progress bar
    length = sum([len(files) for x,y,files in os.walk(srcDir.s)])

    app7z = dirs['compiled'].join(u'7z.exe').s
    command = u'"%s" a "%s" -y -r "%s\\*"' % (app7z, dstFile.temp.s, srcDir.s)

    progress(0,dstFile.s+u'\n'+_(u'Compressing files...'))
    progress.setFull(1+length)

    #--Pack the files
    ins = Popen(command, stdout=PIPE, stdin=PIPE, startupinfo=startupinfo).stdout
    #--Error checking and progress feedback
    reCompressing = re.compile(ur'Compressing\s+(.+)',re.U)
    regMatch = reCompressing.match
    reError = re.compile(u'Error: (.*)',re.U)
    regErrMatch = reError.match
    errorLine = []
    index = 0
    for line in ins:
        line = unicode(line,'utf8')
        maCompressing = regMatch(line)
        if len(errorLine) or regErrMatch(line):
            errorLine.append(line)
        if maCompressing:
            progress(index,dstFile.s+u'\n'+_(u'Compressing files...')+u'\n'+maCompressing.group(1).strip())
            index += 1
        #end if
    #end for
    result = ins.close()
    if result:
        dstFile.temp.remove()
        raise StateError(dstFile.s+u': Compression failed:\n'+u'\n'.join(errorLine))
    #end if
    #--Finalize the file, and cleanup
    dstFile.untemp()

#------------------------------------------------------------------------------
def unpack7z(srcFile, dstDir, progress=None):
    # extract srcFile to dstDir
    progress = progress or Progress()

    # count the files in the archive
    length = 0
    reList = re.compile(u'Path = (.*?)(?:\r\n|\n)',re.U)
    command = ur'"%s" l -slt "%s"' % (dirs['compiled'].join(u'7z.exe').s, srcFile.s)
    ins, err = Popen(command, stdout=PIPE, stdin=PIPE, startupinfo=startupinfo).communicate()
    ins = StringIO.StringIO(ins)
    for line in ins: length += 1
    ins.close()

    if progress:
        progress(0,srcFile.s+u'\n'+_(u'Extracting files...'))
        progress.setFull(1+length)
    #end if

    app7z = dirs['compiled'].join(u'7z.exe').s
    command = u'"%s" x "%s" -y -o"%s"' % (app7z, srcFile.s, dstDir.s)

    #--Extract files
    ins = Popen(command, stdout=PIPE, stdin=PIPE, startupinfo=startupinfo).stdout
    #--Error Checking, and progress feedback
    #--Note subArchives for recursive unpacking
    reExtracting = re.compile(u'Extracting\s+(.+)',re.U)
    regMatch = reExtracting.match
    reError = re.compile(u'Error: (.*)',re.U)
    regErrMatch = reError.match
    errorLine = []
    index = 0
    for line in ins:
        line = unicode(line,'utf8')
        maExtracting = regMatch(line)
        if len(errorLine) or regErrMatch(line):
            errorLine.append(line)
        if maExtracting:
            extracted = GPath(maExtracting.group(1).strip())
            if progress:
                progress(index,srcFile.s+u'\n'+_(u'Extracting files...')+u'\n'+extracted.s)
            #end if
            index += 1
        #end if
    #end for
    result = ins.close()
    if result:
        raise StateError(srcFile.s+u': Extraction failed:\n'+u'\n'.join(errorLine))
    #end if

# Main ------------------------------------------------------------------------
if __name__ == '__main__':
    print _(u'Compiled')
