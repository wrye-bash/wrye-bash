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
import re
import traceback
import StringIO

import bass
import barg
opts,extra = barg.parse()
bass.language = opts.language
import bolt
from bolt import GPath, deprint
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
        if bashIni and bashIni.has_option(u'General', u'sUserPath') and not bashIni.get(u'General', u'sUserPath') == u'.':
            SetHomePath(bashIni.get(u'General', u'sUserPath'))

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
    pidpath = bolt.Path.getcwd().root.join(u'pidfile.tmp')
    lockfd = None

    if opts.restarting: # wait up to 10 seconds for previous instance to close
        t = time()
        while (time()-t < 10) and pidpath.exists(): sleep(1)

    try:
        # if a stale pidfile exists, remove it (this will fail if the file is currently locked)
        if pidpath.exists(): os.remove(pidpath.s)
        lockfd = os.open(pidpath.s, os.O_CREAT|os.O_EXCL|os.O_RDWR)
        os.write(lockfd, u"%d" % os.getpid())
    except OSError, e:
        # lock file exists and is currently locked by another process
        msg = _(u'Already started')
        try: print msg
        except UnicodeError: print msg.encode('mbcs')
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
            sys.argv = [exePath.stail] + sys.argv + [u'--restarting']
            try:
                import subprocess
                subprocess.Popen(sys.argv, executable=exePath.s, close_fds=bolt.close_fds) #close_fds is needed for the one instance checker
            except Exception, error:
                print error
                print u'Error Attempting to Restart Wrye Bash!'
                print u'cmd line: %s %s' %(exePath.s, sys.argv)
                print
                raise

def dump_environment():
    import locale
    print u"Wrye Bash starting"
    print u"Python version: %d.%d.%d" % (sys.version_info[0], sys.version_info[1], sys.version_info[2])
    try:
        import wx
        print u"wxPython version: %s" % wx.version()
    except ImportError:
        print u"wxPython not found"
    # Standalone: stdout will actually be pointing to stderr, which has no 'encoding' attribute
    print u"input encoding: %s; output encoding: %s; locale: %s" % (sys.stdin.encoding, getattr(sys.stdout,'encoding',None), locale.getdefaultlocale())

# Main ------------------------------------------------------------------------
def main():
    if hasattr(sys,'frozen'):
        # Standalone stdout is NUL, no matter what.  Reassign it to stderr so the output
        # goes to 'Wrye Bash.exe.txt'
        sys.stdout = sys.stderr
        # Also, save it for later, to regain control from wxPython
        old_stderr = sys.stderr
    bolt.deprintOn = opts.debug
    if len(extra) > 0:
        return

    # useful for understanding context of bug reprots
    if opts.debug: dump_environment()

    if opts.Psyco:
        try:
            import psyco
            psyco.full()
        except:
            pass

    # ensure we are in the correct directory so relative paths will work properly
    if hasattr(sys,"frozen"):
        pathToProg = os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding()))
    else:
        pathToProg = os.path.dirname(unicode(sys.argv[0], sys.getfilesystemencoding()))
    if pathToProg:
        os.chdir(pathToProg)
    del pathToProg

    # Detect the game we're running for
    import bush
    if opts.debug:
        print u'Searching for game to manage:'
    ret = bush.setGame(opts.gameName,opts.oblivionPath)
    if ret != False: # False == success
        if len(ret) != 1:
            if hasattr(sys,'frozen'):
                # Standalone is guaranteed to have wxPython, so use that
                import wx

                class AppReturnCode(object):
                    def __init__(self,default=None):
                        self.value = default

                    def get(self): return self.value
                    def set(self,value): self.value = value

                class GameSelect(wx.Frame):
                    def __init__(self,gameNames,callback):
                        wx.Frame.__init__(self,None,wx.ID_ANY,'Wrye Bash')
                        self.callback = callback
                        self.panel = panel = wx.Panel(self,wx.ID_ANY)
                        sizer = wx.BoxSizer(wx.VERTICAL)
                        sizer.Add(wx.TextCtrl(panel,wx.ID_ANY,
                                              _(u"Wrye Bash could not determine which game to manage.  The following games have been detected, please select one to manage.")
                                              + u'\n\n' +
                                              _(u'To preven this message in the future, use the -g command line argument to specify the game'),
                                              style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_BESTWRAP),
                                  1,wx.GROW|wx.ALL,5)
                        for gameName in gameNames:
                            gameName = gameName[0].upper() + gameName[1:]
                            sizer.Add(wx.Button(panel,wx.ID_ANY,gameName),0,wx.GROW|wx.ALL^wx.TOP,5)
                        button = wx.Button(panel,wx.ID_CANCEL)
                        button.SetDefault()
                        sizer.Add(button,0,wx.GROW|wx.ALL^wx.TOP,5)
                        self.Bind(wx.EVT_BUTTON,self.OnButton)
                        panel.SetSizer(sizer)

                    def OnButton(self,event):
                        if event.GetId() != wx.ID_CANCEL:
                            self.callback(self.FindWindowById(event.GetId()).GetLabel())
                        self.Close(True)
                _app = wx.App(False)
                retCode = AppReturnCode()
                frame = GameSelect(ret,retCode.set)
                frame.Show()
                frame.Center()
                _app.MainLoop()
                del _app
                if retCode.get() is None: return
                bush.setGame(retCode.get(),opts.oblivionPath)
            else:
                # Python mode, use Tkinter here, since we don't know for sure if wx is present
                import Tkinter
                root = Tkinter.Tk()
                frame = Tkinter.Frame(root)
                frame.pack()

                class onQuit(object):
                    def __init__(self):
                        self.canceled = False

                    def onClick(self):
                        self.canceled = True
                        root.destroy()
                quit = onQuit()

                button = Tkinter.Button(frame,text=_(u'Quit'),fg='red',command=quit.onClick,pady=15,borderwidth=5,relief=Tkinter.GROOVE)
                button.pack(fill=Tkinter.BOTH,expand=1,side=Tkinter.BOTTOM)
                class onClick(object):
                    def __init__(self,gameName):
                        self.gameName = gameName

                    def onClick(self):
                        bush.setGame(self.gameName,opts.oblivionPath)
                        root.destroy()
                for gameName in ret:
                    text = gameName[0].upper() + gameName[1:]
                    command = onClick(gameName).onClick
                    button = Tkinter.Button(frame,text=text,command=command,pady=15,borderwidth=5,relief=Tkinter.GROOVE)
                    button.pack(fill=Tkinter.BOTH,expand=1,side=Tkinter.BOTTOM)
                w = Tkinter.Text(frame)
                w.insert(Tkinter.END, _(u'Wrye Bash could not determine which game to manage.  The following games have been detected, please select one to manage.')
                                      + u'\n\n' +
                                      _(u'To preven this message in the future, use the -g command line argument to specify the game'))
                w.config(state=Tkinter.DISABLED)
                w.pack()
                root.mainloop()
                if quit.canceled:
                    return
                del Tkinter # Unload TKinter, it's not needed anymore
        else:
            bush.setGame(ret[0],opts.oblivionPath)

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
    SetUserPath(u'bash.ini',opts.userPath)

    try:
        # Force Python mode if CBash can't work with this game
        bolt.CBash = opts.mode if bush.game.esp.canCBash else 1
        import bosh
        bosh.initBosh(opts.personalPath,opts.localAppDataPath,opts.oblivionPath)
        bosh.exe7z = bosh.dirs['compiled'].join(bosh.exe7z).s

        # if HTML file generation was requested, just do it and quit
        if opts.genHtml is not None:
            msg1 = _(u"generating HTML file from: '%s'") % opts.genHtml
            msg2 = _(u'done')
            try: print msg1
            except UnicodeError: print msg1.encode('mbcs')
            import belt
            bolt.WryeText.genHtml(opts.genHtml)
            try: print msg2
            except UnicodeError: print msg2.encode('mbcs')
            return

        import basher
        import barb
        import balt
    except (bolt.PermissionError, bolt.BoltError), e:
        # try really hard to be able to show the error in the GUI
        try:
            if 'basher' not in locals():
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
        balt.showError(None,u'%s'%e)
        app.MainLoop()
        raise e
    except (ImportError, StandardError), e:
        # try really hard to be able to show the error in any GUI
        try:
            import Tkinter
            root = Tkinter.Tk()
            frame = Tkinter.Frame(root)
            frame.pack()

            button = Tkinter.Button(frame, text=_(u"QUIT"), fg="red", command=root.destroy, pady=15, borderwidth=5, relief=Tkinter.GROOVE)
            button.pack(fill=Tkinter.BOTH, expand=1, side=Tkinter.BOTTOM)

            o = StringIO.StringIO()
            traceback.print_exc(file=o)
            msg = o.getvalue()
            o.close()
            w = Tkinter.Text(frame)
            w.insert(Tkinter.END, _(u'Error! Unable to start Wrye Bash.')
                                  + u'\n\n' +
                                  _(u'Please ensure Wrye Bash is correctly installed.')
                                  + u'\n\n\n%s' % (msg,))
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
            # Regain control of stdout/stderr from wxPython
            sys.stdout = old_stderr
            sys.stderr = old_stderr
        else:
            app = basher.BashApp(False)
    else:
        app = basher.BashApp()

    if sys.version[0:3] < u'2.6': #nasty, may cause failure in oneInstanceChecker but better than bash failing to open things for no (user) apparent reason such as in 2.5.2 and under.
        bolt.close_fds = False
        if sys.version[0:3] == u'2.5':
            run = balt.askYes(None,
                              _(u"Warning: You are using a python version prior to 2.6 and there may be some instances that failures will occur.  Updating to Python 2.7x is recommended but not imperative.  Do you still want to run Wrye Bash right now?"),
                              _(u"Warning OLD Python version detected")
                              )
        else:
            run = balt.askYes(None,
                              _(u"Warning: You are using a Python version prior to 2.5x which is totally out of date and ancient and Bash will likely not like it and may totally refuse to work.  Please update to a more recent version of Python(2.7x is preferred).  Do you still want to run Wrye Bash?"),
                              _(u"Warning OLD Python version detected")
                              )
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