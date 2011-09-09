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
import re

import bass
import barg
opts,extra = barg.parse()
bass.language = opts.language
import bolt
from bolt import _, GPath
basherImported = False
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
    if not basherImported:
        import basher, barb
    backup = None
    path = None
    quit = opts.backup and opts.quietquit
    if opts.backup: path = GPath(opts.filename)
    backup = barb.BackupSettings(basher.bashFrame,path, quit, opts.backup_images)
    if backup.PromptMismatch() or opts.backup:
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
    return quit

def cmdRestore():
    # restore settings on user request
    if not basherImported: import basher, barb
    backup = None
    path = None
    quit = opts.restore and opts.quietquit
    if opts.restore: path = GPath(opts.filename)
    if opts.restore:
        try:
            backup = barb.RestoreSettings(basher.bashFrame,path, quit, opts.backup_images)
            backup.Apply()
        except barb.BackupCancelled:
            pass
    del backup
    return quit

# -----------------------------------------------------------------------------
# adapted from: http://www.effbot.org/librarybook/msvcrt-example-3.py
def oneInstanceChecker():
    global pidpath, lockfd
    pidpath = bolt.Path.getcwd().root.join('pidfile.tmp')
    lockfd = None

    if opts.restarting: # wait up to 10 seconds for previous instance to close
        t = time()
        while (time()-t < 10) and pidpath.exists(): sleep(1)

    try:
        # if a stale pidfile exists, remove it (this will fail if the file is currently locked)
        if pidpath.exists(): os.remove(pidpath.s)
        lockfd = os.open(pidpath.s, os.O_CREAT|os.O_EXCL|os.O_RDWR)
        os.write(lockfd, "%d" % os.getpid())
    except OSError, e:
        # lock file exists and is currently locked by another process
        print _('already started')
        return False

    return True

def exit():
    try:
        os.close(lockfd)
        os.remove(pidpath.s)
    except OSError, e:
        print e

    try:
        # Cleanup temp installers directory
        import bosh
        bosh.Installer.tempDir.rmtree(bosh.Installer.tempDir.stail)
    except:
        pass

    if basherImported:
        from basher import appRestart
        if appRestart:
            exePath = GPath(sys.executable)
            sys.argv = [exePath.stail] + sys.argv + ['--restarting']
            # For some reason, quoting the sys.argv items caused it not to work for me.
            # Is this correct?
            #sys.argv = ['\"' + x + '\"' for x in sys.argv] #quote all args in sys.argv
            try:
                import subprocess
                subprocess.Popen(sys.argv, executable=exePath.s, close_fds=bolt.close_fds) #close_fds is needed for the one instance checker
            except Exception, error:
                print error
                print _("Error Attempting to Restart Wrye Bash!")
                print _("cmd line: "), exePath.s, sys.argv
                print
                raise

# Main ------------------------------------------------------------------------
def main():
    bolt.deprintOn = opts.debug
    if len(extra) > 0:
        return

    if opts.Psyco:
        try:
            import psyco
            psyco.full()
        except:
            pass
    if opts.unicode != '':
        bolt.bUseUnicode = int(opts.unicode)

    # ensure we are in the correct directory so relative paths will work properly
    if hasattr(sys,"frozen"):
        pathToProg = os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding()))
    else:
        pathToProg = os.path.dirname(unicode(sys.argv[0], sys.getfilesystemencoding()))
    if pathToProg:
        os.chdir(pathToProg)
    del pathToProg

    if opts.bashmon:
        # ensure the console is set up properly
        import ctypes
        ctypes.windll.kernel32.AllocConsole()
        sys.stdin = open('CONIN$', 'r')
        sys.stdout = open('CONOUT$', 'w', 0)
        sys.stderr = open('CONOUT$', 'w', 0)
        # run bashmon and exit
        import bashmon
        bashmon.monitor(0.25) #--Call monitor with specified sleep interval
        return

    #--Initialize Directories and some settings
    #  required before the rest has imported
    SetUserPath('bash.ini',opts.userPath)

    try:
        bolt.CBash = opts.mode
        import bosh
        bosh.initBosh(opts.personalPath,opts.localAppDataPath,opts.oblivionPath)
        bosh.exe7z = bosh.dirs['compiled'].join(bosh.exe7z).s

        # if HTML file generation was requested, just do it and quit
        if opts.genHtml is not None:
            print _("generating HTML file from: '%s'") % opts.genHtml
            import belt
            bolt.WryeText.genHtml(opts.genHtml)
            print _("done")
            return

        import basher
        import barb
        import balt
    except (bolt.PermissionError, bolt.BoltError), e:
        # try really hard to be able to show the error in the GUI
        try:
            if "basher" not in locals():
                # we get here if initBosh threw
                import basher
                import barb
                import balt
        except:
            raise e
        if opts.debug:
            if hasattr(sys,'frozen'):
                app = basher.BashApp()
            else:
                app = basher.BashApp(False)
            bolt.deprintOn = True
        else:
            app = basher.BashApp()
        balt.showError(None,str(e))
        app.MainLoop()
        raise e
    except (ImportError, StandardError), e:
        # try really hard to be able to show the error in any GUI
        try:
            import Tkinter
            root = Tkinter.Tk()
            frame = Tkinter.Frame(root)
            frame.pack()
            
            button = Tkinter.Button(frame, text="QUIT", fg="red", command=frame.quit, pady=15, borderwidth=5, relief=Tkinter.GROOVE)
            button.pack(fill=Tkinter.BOTH, expand=1, side=Tkinter.BOTTOM)
            
            w = Tkinter.Text(frame)
            w.insert(Tkinter.END, _("Error! Unable to start Wrye Bash.\n\n Please ensure Wrye Bash is correctly installed.\n\n\n%s") % (e,))
            w.config(state=Tkinter.DISABLED)
            w.pack()
            root.mainloop()
            return
        except StandardError, y:
            print y
            raise e

    if not oneInstanceChecker(): return
    atexit.register(exit)
    basher.InitSettings()
    basher.InitLinks()
    basher.InitImages()
    #--Start application
    if opts.debug:
        if hasattr(sys, 'frozen'):
            # Special case for py2exe version
            app = basher.BashApp()
        else:
            app = basher.BashApp(False)
    else:
        app = basher.BashApp()

    if sys.version[0:3] < '2.6': #nasty, may cause failure in oneInstanceChecker but better than bash failing to open things for no (user) apparent reason such as in 2.5.2 and under.
        bolt.close_fds = False
        if sys.version[0:3] == 2.5:
            run = balt.askYes(None,"Warning: You are using a python version prior to 2.6 and there may be some instances that failures will occur. Updating to Python 2.7x is recommended but not imperative. Do you still want to run Wrye Bash right now?","Warning OLD Python version detected")
        else:
            run = balt.askYes(None,"Warning: You are using a Python version prior to 2.5x which is totally out of date and ancient and Bash will likely not like it and may totally refuse to work. Please update to a more recent version of Python(2.7x is preferred). Do you still want to run Wrye Bash?", "Warning OLD Python version detected")
        if not run:
            return

    # process backup/restore options
    # quit if either is true, but only after calling both
    quit = cmdBackup()
    quit = cmdRestore() or quit
    if quit: return

    global basherImported
    basherImported = True

    app.Init()
    app.MainLoop()

if __name__ == '__main__':
    main()
