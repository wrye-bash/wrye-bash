import os
import re
import datetime
import cPickle
import cStringIO
from subprocess import Popen, PIPE

import bosh
import basher
from bosh import startupinfo, dirs
from bolt import _, BoltError, AbstractError, StateError, GPath, Progress, deprint
from balt import askSave, askYes, askOpen, askWarning, showError, showWarning, showInfo

#------------------------------------------------------------------------------
def VersionChanged():
    #--Check if the current app version is different from the last version used
    return basher.BashApp.GetVersion(None)[1] != basher.settings['bash.readme'][1]

#------------------------------------------------------------------------------
class BackupCancelled(BoltError):
# user cancelled operatioin
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
        self.verApp = basher.GetBashVersion()[1]
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

    def SameDataVersion(self):
        return self.verDat == basher.settings['bash.version']
        
    def SameAppVersion(self):
        return self.verApp == basher.settings['bash.readme'][1]

#------------------------------------------------------------------------------
class BackupSettings(BaseBackupSettings):
    def __init__(self, parent=None, path=None, quit=False):
        BaseBackupSettings.__init__(self,parent,path,quit)
        #end try
        for path, name, tmpdir in (
              (dirs['mopy'],                      'Bash.ini',     'Oblivion\\Mopy'),
              (dirs['mods'].join('Bash'),         'Table',        'Oblivion\\Data\\Bash'),
              (dirs['modsBash'],                  'Table',        'Oblivion Mods\\Bash Mod Data'),
              (dirs['modsBash'].join('INI Data'), 'Table',        'Oblivion Mods\\Bash Mod Data\\INI Data'),
              (dirs['installers'].join('Bash'),   'Converters',   'Oblivion Mods\\Bash Installers\\Bash'),
              (dirs['installers'].join('Bash'),   'Installers',   'Oblivion Mods\\Bash Installers\\Bash'),
              (dirs['userApp'],                   'Profiles',     'LocalAppData\\Oblivion'),
              (dirs['userApp'],                   'bash config',  'LocalAppData\\Oblivion'),
              (dirs['saveBase'],                  'BashProfiles', 'My Games\\Oblivion'),
              (dirs['saveBase'],                  'BashSettings', 'My Games\\Oblivion'),
              (dirs['saveBase'],                  'Messages',     'My Games\\Oblivion'),
              (dirs['saveBase'],                  'ModeBase',     'My Games\\Oblivion'),
              (dirs['saveBase'],                  'People',       'My Games\\Oblivion'),
                ):
            tmpdir = GPath(tmpdir)
            for ext in ('','.dat','.pkl','.html'): # hack so the above file list can be shorter
                tpath = tmpdir.join(name+ext)
                fpath = path.join(name+ext)
                if fpath.exists(): self.files[tpath] = fpath
                if fpath.backup.exists(): self.files[tpath.backup] = fpath.backup
            #end for
        #end for

        #backup save profile settings
        savedir = GPath('My Games\\Oblivion')
        profiles = [''] + [x for x in dirs['saveBase'].join('Saves').list() if dirs['saveBase'].join('Saves',x).isdir() and str(x).lower() != 'bash']
        for profile in profiles:
            for ext in ('.dat','.pkl'):
                tpath = savedir.join('Saves',profile,'Bash','Table'+ext)
                fpath = dirs['saveBase'].join('Saves',profile,'Bash','Table'+ext)
                if fpath.exists(): self.files[tpath] = fpath
                if fpath.backup.exists(): self.files[tpath.backup] = fpath.backup
            #end for
        #end for
    
    def Apply(self):
        if not self.PromptFile(): return

        # copy all files to ~tmp backup dir
        for tpath,fpath in self.files.iteritems():
            fpath.copyTo(self.tmp.join(tpath))
        #end for

        # dump the version info and file listing
        out = self.tmp.join('backup.dat').open('wb')
        cPickle.dump(self.verDat, out, -1) #data version, if this doesn't match the installed data version, do not allow restore
        cPickle.dump(self.verApp, out, -1) #app version, if this doesn't match the installer app version, warn the use on restore
        cPickle.dump(self.files, out, -1) # file dictionary
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
            path = askSave(self.parent,_('Backup Bash Settings'),self.dir,file,'*.7z')
            if not path: return False
            self.dir = path.head
            self.archive = path.tail
        #end if
        self.maketmp()
        return True

    def PromptConfirm(self,msg=None):
        msg = msg or _('Do you want to backup your Bash settings now?')
        return askYes(self.parent,msg,_('Backup Bash Settings?'))

    def PromptMismatch(self):
        #returns False if same app version or user cancels
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
    def __init__(self, parent=None, path=None, quit=False):
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
        self.files = cPickle.load(ins)
        ins.close()

    def Apply(self):
        if self.ErrorConflict():
            self.WarnFailed()
            return
        elif not self.PromptMismatch():
            raise BackupCancelled()
            return

        for tpath,fpath in self.files.iteritems():
            self.tmp.join(tpath).copyTo(fpath)
        #end for

#         basher.appRestart = True
        self.WarnQuit()
        if basher.bashFrame:
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
        if not self.SameDataVersion():
            showError(self.parent,
                  _('The data format of the selected backup file is different from the current Bash version!\n') +
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

    def WarnQuit(self):
        if self.quit: return
        showWarning(self.parent,
            _('Your Bash settings have been successfuly restored.\n') +
            _('Backup Path: %s\n') % (self.dir.join(self.archive).s) +
            _('\n') +
            _('Before the settings can take effect, you must restart Bash.\n') +
            _('Click OK to quit now.'),
            _('Bash Settings Restored'))

#------------------------------------------------------------------------------
def pack7z(dstFile, srcDir, progress=None):
    # archive srcdir to dstFile in 7z format without solid compression
    progress = progress or Progress()

    #--Used solely for the progress bar
    length = sum([len(files) for x,y,files in os.walk(srcDir.s)])

    app7z = dirs['mopy'].join('7z.exe').s
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
    command = r'"%s" l -slt "%s"' % (dirs['mopy'].join('7z.exe').s, srcFile.s)
    ins, err = Popen(command, stdout=PIPE, startupinfo=startupinfo).communicate()
    ins = cStringIO.StringIO(ins)
    for line in ins: length += 1
    ins.close()

    if progress:
        progress(0,_("%s\nExtracting files...") % srcFile.s)
        progress.setFull(1+length)
    #end if

    app7z = dirs['mopy'].join('7z.exe').s
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
