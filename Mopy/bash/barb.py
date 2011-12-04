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
#  Wrye Bash copyright (C) 2005, 2006, 2007, 2008, 2009 Wrye
#
# =============================================================================

# Rollback library.

import os
import re
import datetime
import cPickle
import cStringIO
import StringIO
from subprocess import Popen, PIPE
import bash
import bosh
import basher
import bolt
from bosh import startupinfo, dirs
from bolt import _, BoltError, AbstractError, StateError, GPath, Progress, deprint, bUseUnicode
from balt import askSave, askYes, askOpen, askWarning, showError, showWarning, showInfo

if bUseUnicode:
    stringBuffer = StringIO.StringIO
else:
    stringBuffer = cStringIO.StringIO
#------------------------------------------------------------------------------
class BackupCancelled(BoltError):
# user cancelled operation
    def __init__(self,message=_('Cancelled')):
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class BaseBackupSettings:
    def __init__(self, parent=None, path=None, quit=False):
        if path != None and path.ext == '' and not path.exists(): path = None
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
        self.verApp = basher.settings['bash.readme'][1].split('.')[0]
        self.files = {}
        self.tmp = None

    def __del__(self):
        if self.tmp and self.tmp.exists(): self.tmp.rmtree('~tmp')

    def maketmp(self):
        # create a ~tmp directory
        self.tmp = self.dir.join('~tmp')
        if self.tmp.exists(): self.tmp.rmtree('~tmp')
        self.tmp.makedirs()

    def Apply(self):
        raise AbstractError

    def PromptFile(self):
        raise AbstractError
        return False

    def PromptConfirm(self,msg=None):
        raise AbstractError
        return False

    def PromptMismatch(self):
        raise AbstractError
        return False

    def CmpDataVersion(self):
        return cmp(self.verDat, basher.settings['bash.version'])

    def CmpAppVersion(self):
        # Changed to prompt updating on any version change
        return cmp(self.verApp.split('.'), basher.settings['bash.readme'][1].split('.'))

    def SameDataVersion(self):
        return not self.CmpDataVersion()

    def SameAppVersion(self):
        return not self.CmpAppVersion()

#------------------------------------------------------------------------------
class BackupSettings(BaseBackupSettings):
    def __init__(self, parent=None, path=None, quit=False, backup_images=None):
        BaseBackupSettings.__init__(self,parent,path,quit)
        for path, name, tmpdir in (
              (dirs['mopy'],                      'bash.ini',             'Oblivion\\Mopy'),
              (dirs['mods'].join('Bash'),         'Table',                'Oblivion\\Data\\Bash'),
              (dirs['mods'].join('Docs'),         'Bash Readme Template', 'Oblivion\\Data\\Docs'),
              (dirs['mods'].join('Docs'),         'Bashed Lists',         'Oblivion\\Data\\Docs'),
              (dirs['mods'].join('Docs'),         'wtxt_sand_small.css',  'Oblivion\\Data\\Docs'),
              (dirs['mods'].join('Docs'),         'wtxt_teal.css',        'Oblivion\\Data\\Docs'),
              (dirs['modsBash'],                  'Table',                'Oblivion Mods\\Bash Mod Data'),
              (dirs['modsBash'].join('INI Data'), 'Table',                'Oblivion Mods\\Bash Mod Data\\INI Data'),
              (dirs['installers'].join('Bash'),   'Converters',           'Oblivion Mods\\Bash Installers\\Bash'),
              (dirs['installers'].join('Bash'),   'Installers',           'Oblivion Mods\\Bash Installers\\Bash'),
              (dirs['userApp'],                   'Profiles',             'LocalAppData\\Oblivion'),
              (dirs['userApp'],                   'bash config',          'LocalAppData\\Oblivion'),
              (dirs['saveBase'],                  'BashProfiles',         'My Games\\Oblivion'),
              (dirs['saveBase'],                  'BashSettings',         'My Games\\Oblivion'),
              (dirs['saveBase'],                  'Messages',             'My Games\\Oblivion'),
              (dirs['saveBase'],                  'ModeBase',             'My Games\\Oblivion'),
              (dirs['saveBase'],                  'People',               'My Games\\Oblivion'),
                ):
            tmpdir = GPath(tmpdir)
            for ext in ('','.dat','.pkl','.html','.txt'): # hack so the above file list can be shorter, could include rogue files but not very likely
                tpath = tmpdir.join(name+ext)
                fpath = path.join(name+ext)
                if fpath.exists(): self.files[tpath] = fpath
                if fpath.backup.exists(): self.files[tpath.backup] = fpath.backup
            #end for
        #end for

        #backup all files in Mopy\Data, Data\Bash Patches and Data\INI Tweaks
        for path, tmpdir in (
              (dirs['l10n'],                              'Oblivion\\Mopy\\bash\\l10n'),
              (dirs['mods'].join('Bash Patches'),         'Oblivion\\Data\\Bash Patches'),
              (dirs['mods'].join('INI Tweaks'),           'Oblivion\\Data\\INI Tweaks'),
                ):
            tmpdir = GPath(tmpdir)
            for name in path.list():
                if path.join(name).isfile():
                    self.files[tmpdir.join(name)] = path.join(name)

        #backup image files if told to
        if backup_images == 1: #changed images only
            tmpdir = GPath('Oblivion\\Mopy\\bash\\images')
            path = dirs['images']
            for name in path.list():
                fullname = path.join(name)
                if fullname.isfile():
                    changed = True
                    for ver_list in bolt.images_list:
                        if name.s in bolt.images_list[ver_list] and bolt.images_list[ver_list][name.s] == fullname.size:
                            changed = False
                    if changed and not name.s.lower() == 'thumbs.db':
                        self.files[tmpdir.join(name)] = fullname
        elif backup_images == 2: #all images
            tmpdir = GPath('Oblivion\\Mopy\\bash\\images')
            path = dirs['images']
            for name in path.list():
                if path.join(name).isfile() and not name.s.lower() == 'thumbs.db':
                    self.files[tmpdir.join(name)] = path.join(name)

        #backup save profile settings
        savedir = GPath('My Games\\Oblivion')
        profiles = [''] + [x for x in dirs['saveBase'].join('Saves').list() if dirs['saveBase'].join('Saves',x).isdir() and str(x).lower() != 'bash']
        for profile in profiles:
            tpath = savedir.join('Saves',profile,'plugins.txt')
            fpath = dirs['saveBase'].join('Saves',profile,'plugins.txt')
            if fpath.exists(): self.files[tpath] = fpath
            for ext in ('.dat','.pkl'):
                tpath = savedir.join('Saves',profile,'Bash','Table'+ext)
                fpath = dirs['saveBase'].join('Saves',profile,'Bash','Table'+ext)
                if fpath.exists(): self.files[tpath] = fpath
                if fpath.backup.exists(): self.files[tpath.backup] = fpath.backup
            #end for
        #end for

    def Apply(self):
        if not self.PromptFile(): return

        deprint('')
        deprint(_('BACKUP BASH SETTINGS: ') + self.dir.join(self.archive).s)

        # copy all files to ~tmp backup dir
        for tpath,fpath in self.files.iteritems():
            deprint(tpath.s + ' <-- ' + fpath.s)
            fpath.copyTo(self.tmp.join(tpath))
        #end for

        # dump the version info and file listing
        out = self.tmp.join('backup.dat').open('wb')
        cPickle.dump(self.verDat, out, -1) #data version, if this doesn't match the installed data version, do not allow restore
        cPickle.dump(self.verApp, out, -1) #app version, if this doesn't match the installer app version, warn the user on restore
        out.close()

        # create the backup archive
        try:
            pack7z(self.dir.join(self.archive),self.tmp)
        except StateError, e:
            raise
            return
        #end try
        basher.settings['bash.backupPath'] = self.dir
        self.InfoSuccess()

    def PromptFile(self):
        #prompt for backup filename
        #returns False if user cancels
        if self.archive == None or self.dir.join(self.archive).exists():
            dt = datetime.datetime.now()
            file = 'Backup Bash Settings v%s (%s).7z' % (self.verApp,dt.strftime('%d-%m-%Y %H%M.%S'))
            if not self.quit:
                path = askSave(self.parent,_('Backup Bash Settings'),self.dir,file,'*.7z')
                if not path: return False
                self.dir = path.head
                self.archive = path.tail
            elif not self.archive:
                self.archive = file
        #end if
        self.maketmp()
        return True

    def PromptConfirm(self,msg=None):
        msg = msg or _('Do you want to backup your Bash settings now?')
        return askYes(self.parent,msg,_('Backup Bash Settings?'))

    def PromptMismatch(self):
        #returns False if same app version or old version == 0 (as in not previously installed) or user cancels
        if basher.settings['bash.readme'][1] == '0': return False
        return not self.SameAppVersion() and self.PromptConfirm(
            _('A different version of Wrye Bash was previously installed.\n') +
            _('Previous Version: %s\n') % (basher.settings['bash.readme'][1]) +
            _('Current Version: %s\n') % (self.verApp) +
            _('Do you want to create a backup of your Bash settings before they are overwritten?'))

    def PromptContinue(self):
        #returns False if user quits
        return not askYes(self.parent,
            _('You did not create a backup of the Bash settings.\n') +
            _('If you continue, your current settings may be overwritten.\n') +
            _('Do you want to quit Wrye Bash now?'),
            _('No backup created!'))

    def PromptQuit(self):
        #returns True if user quits
        return askYes(self.parent,
            _('There was an error while trying to backup the Bash settings!\n') +
            _('If you continue, your current settings may be overwritten.\n') +
            _('Do you want to quit Wrye Bash now?'),
            _('Unable to create backup!'))

    def WarnFailed(self):
        showWarning(self.parent,
            _('There was an error while trying to backup the Bash settings!\n') +
            _('No backup was created.'),
            _('Unable to create backup!'))

    def InfoSuccess(self):
        if self.quit: return
        showInfo(self.parent,
            _('Your Bash settings have been backed up successfully.\n') +
            _('Backup Path: %s\n') % (self.dir.join(self.archive).s),
            _('Backup File Created'))

#------------------------------------------------------------------------------
class RestoreSettings(BaseBackupSettings):
    def __init__(self, parent=None, path=None, quit=False, restore_images=None):
        BaseBackupSettings.__init__(self,parent,path,quit)

        if not self.PromptFile():
            raise BackupCancelled()
            return
        #end if

        try:
            unpack7z(self.dir.join(self.archive), self.tmp)
        except StateError:
            self.WarnFailed()
            return
        #end try
        ins = self.tmp.join('backup.dat').open('rb')
        self.verDat = cPickle.load(ins)
        self.verApp = cPickle.load(ins)
        self.restore_images = restore_images
        ins.close()

    def Apply(self):
        if self.ErrorConflict():
            self.WarnFailed()
            return
        elif not self.PromptMismatch():
            raise BackupCancelled()
            return

        deprint('')
        deprint(_('RESTORE BASH SETTINGS: ') + self.dir.join(self.archive).s)

        # reinitialize bosh.dirs using the backup copy of bash.ini if it exists
        tmpBash = self.tmp.join('Oblivion\\Mopy\\bash.ini')
        opts, args = bash.opts, bash.extra

        bash.SetUserPath(tmpBash.s,opts.userPath)

        bashIni = bash.GetBashIni(tmpBash.s)
        bosh.initBosh(opts.personalPath,opts.localAppDataPath,opts.oblivionPath)

        # restore all the settings files
        restore_paths = (
                (dirs['mopy'],                              'Oblivion\\Mopy'),
                (dirs['mods'].join('Bash'),                 'Oblivion\\Data\\Bash'),
                (dirs['mods'].join('Bash Patches'),         'Oblivion\\Data\\Bash Patches'),
                (dirs['mods'].join('Docs'),                 'Oblivion\\Data\\Docs'),
                (dirs['mods'].join('INI Tweaks'),           'Oblivion\\Data\\INI Tweaks'),
                (dirs['modsBash'],                          'Oblivion Mods\\Bash Mod Data'),
                (dirs['modsBash'].join('INI Data'),         'Oblivion Mods\\Bash Mod Data\\INI Data'),
                (dirs['installers'].join('Bash'),           'Oblivion Mods\\Bash Installers\\Bash'),
                (dirs['userApp'],                           'LocalAppData\\Oblivion'),
                (dirs['saveBase'],                          'My Games\\Oblivion'),
                )
        if 293 >= self.verApp:
            # restore from old data paths
            restore_paths += (
                (dirs['l10n'],                              'Oblivion\\Data'),)
            if self.restore_images:
                restore_paths += (
                    (dirs['images'],                        'Oblivion\\Mopy\\images'),)
        else:
            restore_paths += (
                (dirs['l10n'],                              'Oblivion\\bash\\l10n'),)
            if self.restore_images:
                restore_paths += (
                    (dirs['images'],                        'Oblivion\\Mopy\\bash\\images'),)
        for fpath, tpath in restore_paths:
            path = self.tmp.join(tpath)
            if path.exists():
                for name in path.list():
                    if path.join(name).isfile():
                        deprint(GPath(tpath).join(name).s + ' --> ' + fpath.join(name).s)
                        path.join(name).copyTo(fpath.join(name))

        #restore savegame profile settings
        tpath = GPath('My Games\\Oblivion\\Saves')
        fpath = dirs['saveBase'].join('Saves')
        path = self.tmp.join(tpath)
        if path.exists():
            for root, folders, files in path.walk(True,None,True):
                root = GPath('.'+root.s)
                for name in files:
                    deprint(tpath.join(root,name).s + ' --> ' + fpath.join(root,name).s)
                    path.join(root,name).copyTo(fpath.join(root,name))

        # tell the user the restore is compete and warn about restart
        self.WarnRestart()
        if basher.bashFrame: # should always exist
            basher.bashFrame.Destroy()

    def PromptFile(self):
        #prompt for backup filename
        #returns False if user cancels
        if self.archive == None or not self.dir.join(self.archive).exists():
            path = askOpen(self.parent,_('Restore Bash Settings'),self.dir,'','*.7z')
            if not path: return False
            self.dir = path.head
            self.archive = path.tail
        #end if
        self.maketmp()
        return True

    def PromptConfirm(self,msg=None):
        # returns False if user cancels
        msg = msg or _('Do you want to restore your Bash settings from a backup?')
        return askYes(self.parent,msg,_('Restore Bash Settings?'))

    def PromptMismatch(self):
        # return True if same app version or user confirms
        return self.SameAppVersion() or askWarning(self.parent,
              _('The version of Bash used to create the selected backup file does not match the current Bash version!\n') +
              _('Backup v%s does not match v%s\n') % (self.verApp, basher.settings['bash.readme'][1]) +
              _('\n') +
              _('Do you want to restore this backup anyway?'),
              _('Warning: Version Mismatch!'))

    def ErrorConflict(self):
        #returns True if the data format doesn't match
        if self.CmpDataVersion() > 0:
            showError(self.parent,
                  _('The data format of the selected backup file is newer than the current Bash version!\n') +
                  _('Backup v%s is not compatible with v%s\n') % (self.verApp, basher.settings['bash.readme'][1]) +
                  _('\n') +
                  _('You cannot use this backup with this version of Bash.'),
                  _('Error: Version Conflict!'))
            return True
        #end if
        return False

    def WarnFailed(self):
        showWarning(self.parent,
            _('There was an error while trying to restore your settings from the backup file!\n') +
            _('No settings were restored.'),
            _('Unable to restore backup!'))

    def WarnRestart(self):
        if self.quit: return
        basher.appRestart = True
        showWarning(self.parent,
            _('Your Bash settings have been successfuly restored.\n') +
            _('Backup Path: %s\n') % (self.dir.join(self.archive).s) +
            _('\n') +
            _('Before the settings can take effect, Wrye Bash must restart.\n') +
            _('Click OK to restart now.'),
            _('Bash Settings Restored'))

#------------------------------------------------------------------------------
def pack7z(dstFile, srcDir, progress=None):
    # archive srcdir to dstFile in 7z format without solid compression
    progress = progress or Progress()

    #--Used solely for the progress bar
    length = sum([len(files) for x,y,files in os.walk(srcDir.s)])

    if bosh.inisettings['EnableUnicode']:
        app7z = dirs['compiled'].join('7zUnicode.exe').s
    else:
        app7z = dirs['compiled'].join('7z.exe').s
    command = '"%s" a "%s" -y -r "%s\\*"' % (app7z, dstFile.temp.s, srcDir.s)

    progress(0,_("%s\nCompressing files...") % dstFile.s)
    progress.setFull(1+length)

    #--Pack the files
    ins = Popen(command, stdout=PIPE, startupinfo=startupinfo).stdout
    #--Error checking and progress feedback
    reCompressing = re.compile('Compressing\s+(.+)')
    regMatch = reCompressing.match
    reError = re.compile('Error: (.*)')
    regErrMatch = reError.match
    errorLine = []
    index = 0
    for line in ins:
        maCompressing = regMatch(line)
        if len(errorLine) or regErrMatch(line):
            errorLine.append(line)
        if maCompressing:
            progress(index,dstFile.s+_("\nCompressing files...\n%s") % maCompressing.group(1).strip())
            index += 1
        #end if
    #end for
    result = ins.close()
    if result:
        dstFile.temp.remove()
        raise StateError(_("%s: Compression failed:\n%s") % (dstFile.s, "\n".join(errorLine)))
    #end if
    #--Finalize the file, and cleanup
    dstFile.untemp()

#------------------------------------------------------------------------------
def unpack7z(srcFile, dstDir, progress=None):
    # extract srcFile to dstDir
    progress = progress or Progress()

    # count the files in the archive
    length = 0
    reList = re.compile('Path = (.*?)(?:\r\n|\n)')
    if bosh.inisettings['EnableUnicode']:
        command = r'"%s" l -slt "%s"' % (dirs['compiled'].join('7zUnicode.exe').s, srcFile.s)
    else:
        command = r'"%s" l -slt "%s"' % (dirs['compiled'].join('7z.exe').s, srcFile.s)
    ins, err = Popen(command, stdout=PIPE, startupinfo=startupinfo).communicate()
    ins = stringBuffer(ins)
    for line in ins: length += 1
    ins.close()

    if progress:
        progress(0,_("%s\nExtracting files...") % srcFile.s)
        progress.setFull(1+length)
    #end if

    if bosh.inisettings['EnableUnicode']:
        app7z = dirs['compiled'].join('7zUnicode.exe').s
    else:
        app7z = dirs['compiled'].join('7z.exe').s
    command = '"%s" x "%s" -y -o"%s"' % (app7z, srcFile.s, dstDir.s)

    #--Extract files
    ins = Popen(command, stdout=PIPE, startupinfo=startupinfo).stdout
    #--Error Checking, and progress feedback
    #--Note subArchives for recursive unpacking
    reExtracting = re.compile('Extracting\s+(.+)')
    regMatch = reExtracting.match
    reError = re.compile('Error: (.*)')
    regErrMatch = reError.match
    errorLine = []
    index = 0
    for line in ins:
        maExtracting = regMatch(line)
        if len(errorLine) or regErrMatch(line):
            errorLine.append(line)
        if maExtracting:
            extracted = GPath(maExtracting.group(1).strip())
            if progress:
                progress(index,_("%s\nExtracting files...\n%s") % (srcFile.s,extracted.s))
            #end if
            index += 1
        #end if
    #end for
    result = ins.close()
    if result:
        raise StateError(_("%s: Extraction failed:\n%s") % (srcFile.s, "\n".join(errorLine)))
    #end if

# Main ------------------------------------------------------------------------
if __name__ == '__main__':
    print _('Compiled')