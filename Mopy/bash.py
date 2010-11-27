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

"""This module starts the Wrye Bash application in console mode. Basically, it runs some
initialization functions and then starts the main application loop."""

# Imports ---------------------------------------------------------------------
import atexit
import os
from time import time, sleep
import sys
if sys.version[:3] == '2.4':
    import wxversion
    wxversion.select("2.5.3.1")
import getopt
import re

import bolt
from bolt import _, GPath
import barb
import bosh
import basher

# ----------------------------------------------------------------------------------
def ShowHelp():
    print _('SYNTAX:')
    print '\"' + GPath(sys.argv[0]).tail.s + '\"' + _(
          ' [-o OblivionPath] [-u userPath] [-p personalPath] [-l localAppDataPath] [-b backupFilePath] [-r backupFilePath] [-q] [-d] [0]')
    print '---------------------------------------------------------------------------'
    print _('For all arguments:')
    print _('Note that Python reads the backslash \"\\\" as an escape character,'
          + ' (that is, the backslash itself is ignored and the following character is read literally)'
          + ' so for any paths you\'ll want to either use two backslashes (C:\\\\Folder\\\\)'
          + ' or a forwardslash (C:/Folder/).')
    print
    print _('The -o, -u, -p and -l arguments can be set in the .ini file.')
    print _('Arguments have precedence over ini settings.'
          + ' You can use a mix of arguments and ini settings.'
          + ' Ini settings don\'t require a double backslash and can have relative paths.')
    print '---------------------------------------------------------------------------'
    print _('Oblivion directory argument (-o).')
    print _('-o OblivionPath: Specify Oblivion directory (containing Oblivion.exe).')
    print _('Use this argument if Bash is located outside of the Oblivion directory.')
    print _('Example: -o \"C:\\\\Games\\\\Oblivion\\\\\"')
    print '---------------------------------------------------------------------------'
    print _('User directory arguments (-u, -p, and -l).')
    print _('These arguments allow you to specify your user directories in several ways.'
          + ' These are only useful if the regular procedure for getting the user directory fails.'
          + ' And even in that case, the user is probably better off installing win32com.')
    print _('However, the arguments are:')
    print
    print _('-u userPath: Specify the user profile path. May help if HOMEDRIVE and/or HOMEPATH'
          + ' are missing from the user\'s environgment.')
    print _('Example: -u \"C:\\\\Documents and Settings\\\\Wrye\"')
    print
    print _('-p personalPath: Specify the user\'s personal directory.')
    print _('If you need to set this then you probably need to set -l too.')
    print _('Example: -p \"C:\\\\Documents and Settings\\\\Wrye\\\\My Documents\"')
    print
    print _('-l localAppDataPath: Specify the user\'s local application data directory.')
    print _('If you need to set this then you probably need to set -p too.')
    print _('Example: -l \"C:\\\\Documents and Settings\\\\Wrye\\\\Local Settings\\\\Application Data\"')
    print '---------------------------------------------------------------------------'
    print _('Quiet/Quit Mode:')
    print _('-q Close Bash after creating or restoring backup and do not display any prompts or message dialogs.')
    print _('Only used with -b and -r options. Otherwise ignored.')
    print '---------------------------------------------------------------------------'
    print _('Backup Bash Settings:')
    print _('-b backupFilePath: Backup all Bash settings to an archive file before the app launches.')
    print _('Example: -b \"C:\\\\Games\\\\Bash Backups\\\\BashBackupFile.7z\"')
    print _('Prompts the user for the backup file path if an empty string is given or'
          + ' the path does not end with \'.7z\' or the specified file already exists.')
    print
    print _('When the -q flag is used, no dialogs will be displayed and Bash will quit after completing the backup.')
    print _('  If backupFilePath does not specify a valid directory, the default directory will be used:')
    print _('    \'[Oblivion Mods]\\Bash Mod Data\\Bash Backup\'')
    print _('  If backupFilePath does not specify a filename, a default name including'
          + ' the Bash version and current timestamp will be used.')
    print _('    \'Backup Bash Settings vVER (DD-MM-YYYY hhmm.ss).7z\'')
    print '---------------------------------------------------------------------------'
    print _('Restore Bash Settings:')
    print _('-r backupFilePath: Restore all Bash settings from backup file before the app launches.')
    print _('Example: -r \"C:\\\\Games\\\\Bash Backups\\\\BashBackupFile.7z\"')
    print _('Bash will prompt the user for the backup file path if an empty string is given or'
          + ' the path does not end with \'.7z\' or the specified file does not exist.')
    print
    print _('When the -q flag is used, no dialogs will be displayed and Bash will quit after restoring the settings.')
    print _('  If backupFilePath is not valid, the user will be prompted for the backup file to restore.')
    print '---------------------------------------------------------------------------'
    print _('Debug argument:')
    print _('-d Send debug text to the console rather than to a newly created debug window.')
    print _('Useful if bash is crashing on startup or if you want to print a lot of'
          + ' information (e.g. while developing or debugging).')
    print '---------------------------------------------------------------------------'

# ----------------------------------------------------------------------------------
def ParseArgs():
    #--Parse arguments
    optlist,args = getopt.getopt(sys.argv[1:],'o:u:p:l:b:r:qd',('restarting'))
    opts = dict(optlist)

    #strip options from sys.argv that should not be reinvoked on app restart
    try:
        for opt,argc in (('-b',1),('-r',1),('-q',0),('--restarting',0)):
            if opt in opts:
                if opt in sys.argv:
                    i = sys.argv.index(opt)
                    del sys.argv[i:i+argc+1]
                else:
                    reOpt = re.compile(re.escape(opt)+'.*$')
                    arg = [x for x in sys.argv if reOpt.match(x)]
                    raise Exception('Invalid command line option: \'' + arg[0] +'\'')

    except Exception, e:
        print e
        print
        ShowHelp()
        sys.exit(1)

    return (opts, args)

# ----------------------------------------------------------------------------------
def SetHomePath(homePath):
    drive,path = os.path.splitdrive(homePath)
    os.environ['HOMEDRIVE'] = drive
    os.environ['HOMEPATH'] = path

# ----------------------------------------------------------------------------------
def GetBashIni(iniPath):
    import ConfigParser
    bashIni = None
    if os.path.exists(iniPath):
        bashIni = ConfigParser.ConfigParser()
        bashIni.read(iniPath)
    return bashIni

# ----------------------------------------------------------------------------------
def SetUserPath(iniPath, uArg=None):
#if uArg is None, then get the UserPath from the ini file
    if uArg:
        SetHomePath(uArg)
    elif os.path.exists(iniPath):
        bashIni = GetBashIni(iniPath)
        if bashIni and bashIni.has_option('General', 'sUserPath') and not bashIni.get('General', 'sUserPath') == '.':
            SetHomePath(bashIni.get('General', 'sUserPath'))

# Backup/Restore --------------------------------------------------------------
def cmdBackup():
    # backup settings if app version has changed or on user request
    backup = None
    path = None
    quit = '-b' in opts and '-q' in opts
    if '-b' in opts: path = GPath(opts['-b'])
    backup = barb.BackupSettings(basher.bashFrame,path, quit)
    if backup.PromptMismatch() or '-b' in opts:
        try:
            backup.Apply()
        except bolt.StateError:
            if backup.SameAppVersion():
                backup.WarnFailed()
            elif backup.PromptQuit():
                return False
        except barb.BackupCancelled:
            if not backup.SameAppVersion() and not backup.PromptContinue():
                return False
    del backup
    return not quit

def cmdRestore():
    # restore settings on user request
    backup = None
    path = None
    quit = '-r' in opts and '-q' in opts
    if '-r' in opts: path = GPath(opts['-r'])
    if '-r' in opts:
        try:
            backup = barb.RestoreSettings(basher.bashFrame,path, quit)
            backup.Apply()
        except barb.BackupCancelled:
            pass
    del backup
    return not quit

# -----------------------------------------------------------------------------
# adapted from: http://www.effbot.org/librarybook/msvcrt-example-3.py
def oneInstanceChecker():
    global pidpath, lockfd
    pidpath = bosh.dirs['mopy'].join('pidfile.tmp')
    lockfd = None

    if '--restarting' in opts: # wait up to 10 seconds for previous instance to close
        t = time()
        while (time()-t < 10) and pidpath.exists(): sleep(1)
            
    try:
        # if a stale pidfile exists, remove it (this will fail if the file is currently locked)
        if pidpath.exists(): os.remove(pidpath.s)
        lockfd = os.open(pidpath.s, os.O_CREAT|os.O_EXCL|os.O_RDWR)
        os.write(lockfd, "%d" % os.getpid())
    except OSError, e:
        # lock file exists and is currently locked by another process
        print 'already started'
        return False

    return True

def exit():
    try:
        os.close(lockfd)
        os.remove(pidpath.s)
    except OSError, e:
        print e

    if basher.appRestart:
        exePath = GPath(sys.executable)
        sys.argv = [exePath.stail] + sys.argv + ['--restarting']
        sys.argv = ['\"' + x + '\"' for x in sys.argv] #quote all args in sys.argv
        try:
            os.spawnv(os.P_NOWAIT, exePath.s, sys.argv)
        except Exception as error:
            print error
            print _("Error Attempting to Restart Wrye Bash!")
            print _("cmd line: "), exePath.s, sys.argv
            print
            raise

# Main ------------------------------------------------------------------------
def main():
    global opts, args
    #import warnings
    #warnings.filterwarnings('error')

    #--Parse arguments
    opts, args = ParseArgs()

    #--Initialize Directories and some settings
    #  required before the rest has imported
    SetUserPath('bash.ini',opts.get('-u'))
    personal = opts.get('-p')
    localAppData = opts.get('-l')
    oblivionPath = opts.get('-o')
    
    bosh.initBosh(personal,localAppData,oblivionPath)

    if not oneInstanceChecker(): return
    atexit.register(exit)
    basher.InitSettings()
    basher.InitLinks()
    basher.InitImages()
    #--Start application
    if '-d' in opts or (args and args[0] == '0'):
        app = basher.BashApp(False)
        bolt.deprintOn = True
    else:
        app = basher.BashApp()

    # process backup/restore options
    quit = False # quit if either is true, but only after calling both
    quit = quit or not cmdBackup()
    quit = quit or not cmdRestore()
    if quit: return

    app.Init()
    app.MainLoop()

if __name__ == '__main__':
    try:
        if '-d' not in opts and '0' not in args:
            import psyco
            psyco.full()
    except:
        pass
    main()
