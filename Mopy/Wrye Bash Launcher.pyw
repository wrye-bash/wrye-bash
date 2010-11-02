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

"""This module starts the Wrye Bash application. Basically, it runs some
initialization functions, and then starts the main application loop.

bash [-o OblivionPath] [-u userPath] [-p personalPath] [-l localAppDataPath] [-b backupFilePath] [-r backupFilePath] [-q] [-d] [0]
----
For all arguments:
Note that Python reads the backslash "\" as an escape character,
(that is, the backslash itself is ignored and the following character is read literally)
so for any paths you'll want to either use two backslashes (C:\\Folder\\)
or a forwardslash (C:/Folder/).

All arguments except the -d Debug can be set in the .ini file.
Arguments have precedence over ini settings.
You can use a mix of arguments and ini settings.
Ini settings don't require a double backslash and can have relative paths.
----
Oblivion directory argument (-o).
-o OblivionPath: Specify Oblivion directory (containing Oblivion.exe).
Use this argument if Bash is located outside of the Oblivion directory.
Example: -o "C:\\Games\\Oblivion\\"
----
User directory arguments (-u, -p, and -l).
These arguments allow you to specify your user directories in several ways. These
are only useful if the regular procedure for getting the user directory fails.
And even in that case, the user is probably better off installing win32com.
However, the arguments are:

-u userPath: Specify the user profile path. May help if HOMEDRIVE and/or HOMEPATH
are missing from the user's environgment.
Example: -u "C:\\Documents and Settings\\Wrye"

-p personalPath: Specify the user's personal directory.
If you need to set this then you probably need to set -l too.
Example: -p "C:\\Documents and Settings\\Wrye\\My Documents"

-l localAppDataPath: Specify the user's local application data directory. 
If you need to set this then you probably need to set -p too.
Example: -l "C:\\Documents and Settings\\Wrye\\Local Settings\\Application Data"
---
Quiet/Quit Mode:
-q Close Bash after creating or restoring backup and do not display any prompts or message dialogs.
Only used with -b and -r options. Otherwise ignored.
---
Backup Bash Settings:
-b backupFilePath: Backup all Bash settings to an archive file before the app launches.
Example: -b "C:\\Games\\Bash Backups\\BashBackupFile.7z"
Prompts the user for the backup file path if an empty string is given or
the path does not end with '.7z' or the specified file already exists.

When the -q flag is used, no dialogs will be displayed and Bash will quit after completing the backup.
  If backupFilePath does not specify a valid directory, the default directory will be used:
    '[Oblivion Mods]\\Bash Mod Data\\Bash Backup'
  If backupFilePath does not specify a filename, a default name including the Bash version and current timestamp will be used.
    'Backup Bash Settings vVER (DD-MM-YYYY hhmm.ss).7z'
---
Restore Bash Settings:
-r backupFilePath: Restore all Bash settings from backup file before the app launches.
Example: -r "C:\\Games\\Bash Backups\\BashBackupFile.7z"
Bash will prompt the user for the backup file path if an empty string is given or
the path does not end with '.7z' or the specified file does not exist.

When the -q flag is used, no dialogs will be displayed and Bash will quit after restoring the settings.
  If backupFilePath is not valid, the user will be prompted for the backup file to restore.
----
Debug argument:
-d Send debug text to the console rather than to a newly created debug window.
Useful if bash is crashing on startup or if you want to print a lot of
information (e.g. while developing or debugging).
"""

# Imports ---------------------------------------------------------------------
import os
import sys
if sys.version[:3] == '2.4':
    import wxversion
    wxversion.select("2.5.3.1")
import barg
import bosh
from time import time, sleep


#--Parse arguments
opts, args = barg.ParseArgs()

#--Initialize Directories and some settings
#  required before the rest has imported
barg.SetUserPath('bash.ini',opts.get('-u'))
personal = opts.get('-p')
localAppData = opts.get('-l')
oblivionPath = opts.get('-o')

bosh.initBosh(personal,localAppData,oblivionPath)

import basher
import bolt
import atexit
import barb

# Backup/Restore --------------------------------------------------------------
def cmdBackup():
    # backup settings if app version has changed or on user request
    backup = None
    path = None
    quit = '-b' in opts and '-q' in opts
    if '-b' in opts: path = bolt.GPath(opts['-b'])
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
    if '-r' in opts: path = bolt.GPath(opts['-r'])
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
pidpath = bosh.dirs['mopy'].join('pidfile.tmp')
lockfd = None

def oneInstanceChecker():
    global lockfd
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
        exePath = bolt.GPath(sys.executable)
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
    #import warnings
    #warnings.filterwarnings('error')
    #--More Initialization
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
