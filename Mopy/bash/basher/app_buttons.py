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
import os
import subprocess
import webbrowser
from . import BashStatusBar
from .frames import ModChecker, DocBrowser
from .. import bosh, bolt, balt, bush
from ..balt import ItemLink, Link, Links, bitmapButton, Image, images, \
    SeparatorLink, tooltip, BoolLink, staticBitmap
from ..bolt import GPath
# TODO(ut): GetBitmapButton factor out duplicate code

modList = None

#------------------------------------------------------------------------------
#  StatusBar Links--------------------------------------------------------------
#------------------------------------------------------------------------------
class StatusBar_Hide(ItemLink):
    """The (single) link on the button's menu - hides the button."""
    def _initData(self, window, data):
        super(StatusBar_Hide, self)._initData(window, data)
        tip = window.GetToolTip().GetTip()
        self.text = _(u"Hide '%s'") % tip
        self.help = _(u"Hides %(buttonname)s's status bar button (can be"
            u" restored through the settings menu).") % ({'buttonname': tip})

    def Execute(self,event):
        sb = Link.Frame.GetStatusBar()
        sb.HideButton(self.window)

class StatusBar_Button(ItemLink):
    """Launch an application."""
    def __init__(self,uid=None,canHide=True,tip=u''):
        """ui: Unique identifier, used for saving the order of status bar icons
               and whether they are hidden/shown.
           canHide: True if this button is allowed to be hidden."""
        super(StatusBar_Button, self).__init__()
        self.mainMenu = Links()
        self.canHide = canHide
        self.gButton = None
        self._tip = tip
        if uid is None: uid = (self.__class__.__name__,tip)
        self.uid = uid

    def createButton(self, *args, **kwdargs):
        if len(args) < 11 and 'onRClick' not in kwdargs:
            kwdargs['onRClick'] = self.DoPopupMenu
        if len(args) < 9 and 'onClick' not in kwdargs:
            kwdargs['onClick'] = self.Execute
        if self.gButton is not None:
            self.gButton.Destroy()
        self.gButton = bitmapButton(*args, **kwdargs)
        return self.gButton

    def DoPopupMenu(self,event):
        if self.canHide:
            if len(self.mainMenu) == 0 or not isinstance(self.mainMenu[-1],StatusBar_Hide):
                if len(self.mainMenu) > 0:
                    self.mainMenu.append(SeparatorLink())
                self.mainMenu.append(StatusBar_Hide())
        if len(self.mainMenu) > 0:
            self.mainMenu.PopupMenu(self.gButton,Link.Frame,0)
        else:
            event.Skip()

    # Helper function to get OBSE version
    @property
    def obseVersion(self):
        if bosh.inisettings['SteamInstall']:
            file = bush.game.se.steamExe
        else:
            file = bush.game.se.exe
        version = bosh.dirs['app'].join(file).strippedVersion
        return u'.'.join([u'%s'%x for x in version])

#------------------------------------------------------------------------------
# App Links -------------------------------------------------------------------
#------------------------------------------------------------------------------
class App_Button(StatusBar_Button):
    """Launch an application."""
    obseButtons = []

    @property
    def version(self):
        if not self.isJava and self.IsPresent():
            version = self.exePath.strippedVersion
            if version != (0,):
                version = u'.'.join([u'%s'%x for x in version])
                return version
        return ''

    @property
    def tip(self):
        if not bosh.settings['bash.statusbar.showversion']: return self._tip
        else:
            return self._tip + u' ' + self.version

    @property
    def obseTip(self):
        if self._obseTip is not None:
            if not bosh.settings['bash.statusbar.showversion']: return self._obseTip % (dict(version=u''))
            else: return self._obseTip % (dict(version=self.version))
        else: return None

    @staticmethod
    def getJava():
        """Locate Java executable"""
        win = GPath(os.environ['SYSTEMROOT'])
        # Default location: Windows\System32\javaw.exe
        java = win.join(u'system32', u'javaw.exe')
        if not java.exists():
            # 1st possibility:
            #  - Bash is running as 32-bit
            #  - The only Java installed is 64-bit
            # Because Bash is 32-bit, Windows\System32 redirects to
            # Windows\SysWOW64.  So look in the ACTUAL System32 folder
            # by using Windows\SysNative
            java = win.join(u'sysnative', u'javaw.exe')
        if not java.exists():
            # 2nd possibility
            #  - Bash is running as 64-bit
            #  - The only Java installed is 32-bit
            # So javaw.exe would actually be in Windows\SysWOW64
            java = win.join(u'syswow64', u'javaw.exe')
        return java

    def __init__(self,exePathArgs,images,tip,obseTip=None,obseArg=None,workingDir=None,uid=None,canHide=True):
        """Initialize
        exePathArgs (string): exePath
        exePathArgs (tuple): (exePath,*exeArgs)
        exePathArgs (list):  [exePathArgs,altExePathArgs,...]
        images: [16x16,24x24,32x32] images
        """
        StatusBar_Button.__init__(self,uid,canHide,tip)
        if isinstance(exePathArgs, list):
            use = exePathArgs[0]
            for item in exePathArgs:
                if isinstance(item, tuple):
                    exePath = item[0]
                else:
                    exePath = item
                if exePath.exists():
                    # Use this one
                    use = item
                    break
            exePathArgs = use
        if isinstance(exePathArgs,tuple):
            self.exePath = exePathArgs[0]
            self.exeArgs = exePathArgs[1:]
        else:
            self.exePath = exePathArgs
            self.exeArgs = tuple()
        self.images = images
        if workingDir:
            self.workingDir = GPath(workingDir)
        else:
            self.workingDir = None
        #--Exe stuff
        if self.exePath and self.exePath.cext == u'.exe': #Sometimes exePath is "None"
            self.isExe = True
        else:
            self.isExe = False
        #--Java stuff
        if self.exePath and self.exePath.cext == u'.jar': #Sometimes exePath is "None"
            self.isJava = True
            self.java = self.getJava()
            self.jar = self.exePath
            self.appArgs = u''.join(self.exeArgs)
        else:
            self.isJava = False
        #--shortcut
        if self.exePath and self.exePath.cext == u'.lnk': #Sometimes exePath is "None"
            self.isShortcut = True
        else:
            self.isShortcut = False
        #--Folder
        if self.exePath and self.exePath.isdir():
            self.isFolder = True
        else:
            self.isFolder = False
        #--**SE stuff
        self._obseTip = obseTip
        self.obseArg = obseArg

    def IsPresent(self):
        if self.isJava:
            return self.java.exists() and self.jar.exists()
        else:
            if self.exePath in bosh.undefinedPaths:
                return False
            return self.exePath.exists()

    def GetBitmapButton(self,window,style=0):
        if self.IsPresent():
            size = bosh.settings['bash.statusbar.iconSize']
            idex = (size/8)-2
            self.createButton(window,self.images[idex].GetBitmap(),
                              style=style,tip=self.tip)
            if self.obseTip is not None:
                App_Button.obseButtons.append(self)
                exeObse = bosh.dirs['app'].join(bush.game.se.exe)
                if bosh.settings.get('bash.obse.on',False) and exeObse.exists():
                    self.gButton.SetToolTip(tooltip(self.obseTip))
            return self.gButton
        else:
            return None

    def ShowError(self,error):
        balt.showError(Link.Frame,
                       (u'%s'%error + u'\n\n' +
                        _(u'Used Path: ') + self.exePath.s + u'\n' +
                        _(u'Used Arguments: ') + u'%s' % (self.exeArgs,)),
                       _(u"Could not launch '%s'") % self.exePath.stail)

    def _showUnicodeError(self):
        balt.showError(Link.Frame, _(
            u'Execution failed, because one or more of the command line '
            u'arguments failed to encode.'),
                       _(u"Could not launch '%s'") % self.exePath.stail)

    def Execute(self,event,extraArgs=None,wait=False):
        if self.IsPresent():
            if self.isShortcut or self.isFolder:
                webbrowser.open(self.exePath.s)
            elif self.isJava:
                cwd = bolt.Path.getcwd()
                if self.workingDir:
                    self.workingDir.setcwd()
                else:
                    self.jar.head.setcwd()
                try:
                    subprocess.Popen((self.java.stail,u'-jar',self.jar.stail,self.appArgs), executable=self.java.s, close_fds=bolt.close_fds) #close_fds is needed for the one instance checker
                except UnicodeError:
                    self._showUnicodeError()
                except Exception as error:
                    self.ShowError(error)
                finally:
                    cwd.setcwd()
            elif self.isExe:
                exeObse = bosh.dirs['app'].join(bush.game.se.exe)
                exeLaa = bosh.dirs['app'].join(bush.game.laa.exe)
                if exeLaa.exists() and bosh.settings.get('bash.laa.on',True) and self.exePath.tail == bush.game.exe:
                    # Should use the LAA Launcher
                    exePath = exeLaa
                    args = [exePath.s]
                elif self.obseArg is not None and bosh.settings.get('bash.obse.on',False) and exeObse.exists():
                    if bosh.inisettings['SteamInstall'] and self.exePath.tail == u'Oblivion.exe':
                        exePath = self.exePath
                    else:
                        exePath = exeObse
                    args = [exePath.s]
                    if self.obseArg != u'':
                        args.append(u'%s' % self.obseArg)
                else:
                    exePath = self.exePath
                    args = [exePath.s]
                args.extend(self.exeArgs)
                if extraArgs: args.extend(extraArgs)
                Link.Frame.GetStatusBar().SetStatusText(u' '.join(args[1:]),1)
                cwd = bolt.Path.getcwd()
                if self.workingDir:
                    self.workingDir.setcwd()
                else:
                    exePath.head.setcwd()
                try:
                    popen = subprocess.Popen(args, close_fds=bolt.close_fds) #close_fds is needed for the one instance checker
                    if wait:
                        popen.wait()
                except UnicodeError:
                    self._showUnicodeError()
                except WindowsError as werr:
                    if werr.winerror != 740:
                        self.ShowError(werr)
                    try:
                        import win32api
                        win32api.ShellExecute(0,'runas',exePath.s,u'%s'%self.exeArgs,bosh.dirs['app'].s,1)
                    except:
                        self.ShowError(werr)
                except Exception as error:
                    self.ShowError(error)
                finally:
                    cwd.setcwd()
            else:
                dir_ = self.workingDir.s if self.workingDir else bolt.Path.getcwd().s
                args = u'"%s"' % self.exePath.s
                args += u' '.join([u'%s' % arg for arg in self.exeArgs])
                try:
                    import win32api
                    r, executable = win32api.FindExecutable(self.exePath.s)
                    executable = win32api.GetLongPathName(executable)
                    win32api.ShellExecute(0,u"open",executable,args,dir_,1)
                except Exception as error:
                    if isinstance(error,WindowsError) and error.winerror == 740:
                        # Requires elevated permissions
                        try:
                            import win32api
                            win32api.ShellExecute(0,'runas',executable,args,dir_,1)
                        except Exception as error:
                            self.ShowError(error)
                    else:
                        # Most likely we're here because FindExecutable failed (no file association)
                        # Or because win32api import failed.  Try doing it using os.startfile
                        # ...Changed to webbrowser.open because os.startfile is windows specific and is not cross platform compatible
                        cwd = bolt.Path.getcwd()
                        if self.workingDir:
                            self.workingDir.setcwd()
                        else:
                            self.exePath.head.setcwd()
                        try:
                            webbrowser.open(self.exePath.s)
                        except UnicodeError:
                            self._showUnicodeError()
                        except Exception as error:
                            self.ShowError(error)
                        finally:
                            cwd.setcwd()
        else:
            balt.showError(Link.Frame,
                           _(u'Application missing: %s') % self.exePath.s,
                           _(u"Could not launch '%s'" % self.exePath.stail)
                           )

#------------------------------------------------------------------------------
class Tooldir_Button(App_Button):
    """Just an App_Button that's path is in bosh.tooldirs
       Use this to automatically set the uid for the App_Button."""
    def __init__(self,toolKey,images,tip,obseTip=None,obseArg=None,workingDir=None,canHide=True):
        App_Button.__init__(self,bosh.tooldirs[toolKey],images,tip,obseTip,obseArg,workingDir,toolKey,canHide)

#------------------------------------------------------------------------------
class App_Tes4Gecko(App_Button): # CRUFT
    """Left in for unpickling compatibility reasons."""
    def __setstate__(self, state):
        self.__dict__.update(state)
        self.__class__ = App_Button

#------------------------------------------------------------------------------
class App_Tes5Gecko(App_Button): # CRUFT
    """Left in for unpickling compatibility reasons."""
    def __setstate__(self, state):
        self.__dict__.update(state)
        self.__class__ = App_Button

#------------------------------------------------------------------------------
class App_OblivionBookCreator(App_Button): # CRUFT
    """Left in for unpickling compatibility reasons."""
    def __setstate__(self, state):
        self.__dict__.update(state)
        self.__class__ = App_Button

#------------------------------------------------------------------------------
class _Mods_Tes4ViewExpert(BoolLink):
    """Toggle Tes4Edit expert mode (when launched via Bash)."""
    text, key = _(u'Tes4Edit Expert'), 'tes4View.iKnowWhatImDoing'

#------------------------------------------------------------------------------
class _Mods_Tes5ViewExpert(BoolLink):
    """Toggle Tes5Edit expert mode (when launched via Bash)."""
    text, key = _(u'Tes5Edit Expert'), 'tes5View.iKnowWhatImDoing'

class App_Tes4View(App_Button):
    """Allow some extra args for Tes4View."""

# arguments
# -fixup (wbAllowInternalEdit true default)
# -nofixup (wbAllowInternalEdit false)
# -showfixup (wbShowInternalEdit true default)
# -hidefixup (wbShowInternalEdit false)
# -skipbsa (wbLoadBSAs false)
# -forcebsa (wbLoadBSAs true default)
# -fixuppgrd
# -IKnowWhatImDoing
# -FNV
#  or name begins with FNV
# -FO3
#  or name begins with FO3
# -TES4
#  or name begins with TES4
# -TES5
#  or name begins with TES5
# -lodgen
#  or name ends with LODGen.exe
#  (requires TES4 mode)
# -masterupdate
#  or name ends with MasterUpdate.exe
#  (requires FO3 or FNV)
#  -filteronam
#  -FixPersistence
#  -NoFixPersistence
# -masterrestore
#  or name ends with MasterRestore.exe
#  (requires FO3 or FNV)
# -edit
#  or name ends with Edit.exe
# -translate
#  or name ends with Trans.exe
    def __init__(self,*args,**kwdargs):
        App_Button.__init__(self,*args,**kwdargs)
        if bush.game.fsName == 'Skyrim':
            self.mainMenu.append(_Mods_Tes5ViewExpert())
        elif bush.game.fsName == 'Oblivion' or bush.game.fsName == 'Nehrim':
            self.mainMenu.append(_Mods_Tes4ViewExpert())

    def IsPresent(self):
        if self.exePath in bosh.undefinedPaths or not self.exePath.exists():
            testPath = bosh.tooldirs['Tes4ViewPath']
            if testPath not in bosh.undefinedPaths and testPath.exists():
                self.exePath = testPath
                return True
            return False
        return True

    def Execute(self,event):
        extraArgs = []
        if balt.getKeyState_Control():
            extraArgs.append(u'-FixupPGRD')
        if balt.getKeyState_Shift():
            extraArgs.append(u'-skipbsa')
        if bush.game.fsName == 'Oblivion' or bush.game.fsName == 'Nehrim':
            if bosh.settings['tes4View.iKnowWhatImDoing']:
                extraArgs.append(u'-IKnowWhatImDoing')
        if bush.game.fsName == 'Skyrim':
            if bosh.settings['tes5View.iKnowWhatImDoing']:
                extraArgs.append(u'-IKnowWhatImDoing')
        App_Button.Execute(self,event,tuple(extraArgs))

#------------------------------------------------------------------------------
class _Mods_BOSSDisableLockTimes(BoolLink):
    """Toggle Lock Load Order disabling when launching BOSS through Bash."""
    text = _(u'BOSS Disable Lock Load Order')
    key = 'BOSS.ClearLockTimes'
    help = _(u"If selected, will temporarily disable Bash's Lock Load Order"
             u" when running BOSS through Bash.")

#------------------------------------------------------------------------------
class _Mods_BOSSLaunchGUI(BoolLink):
    """If BOSS.exe is available then BOSS GUI.exe should be too."""
    text, key, help = _(u'Launch using GUI'), 'BOSS.UseGUI', \
                      _(u"If selected, Bash will run BOSS's GUI.")

class App_BOSS(App_Button):
    """loads BOSS"""
    def __init__(self, *args, **kwdargs):
        App_Button.__init__(self, *args, **kwdargs)
        self.mainMenu.append(_Mods_BOSSLaunchGUI())
        self.mainMenu.append(_Mods_BOSSDisableLockTimes())

    def Execute(self,event,extraArgs=None):
        if bosh.settings['BOSS.UseGUI']:
            self.exePath = self.exePath.head.join(u'BOSS GUI.exe')
        wait = bool(bosh.settings['BOSS.ClearLockTimes'])
        extraArgs = []
        if balt.getKeyState(82) and balt.getKeyState_Shift():
            extraArgs.append(u'-r 2',) # Revert level 2 - BOSS version 1.6+
        elif balt.getKeyState(82):
            extraArgs.append(u'-r 1',) # Revert level 1 - BOSS version 1.6+
        if balt.getKeyState(83):
            extraArgs.append(u'-s',) # Silent Mode - BOSS version 1.6+
        if balt.getKeyState(67): #c - print crc calculations in BOSS log.
            extraArgs.append(u'-c',)
        if bosh.tooldirs['boss'].version >= (2,0,0,0):
            # After version 2.0, need to pass in the -g argument
            extraArgs.append(u'-g%s' % bush.game.fsName,)
        App_Button.Execute(self,event,tuple(extraArgs), wait)
        if bosh.settings['BOSS.ClearLockTimes']:
            # Clear the saved times from before
            bosh.modInfos.mtimes.clear()
            # And refresh to get the new times so WB will keep the order that BOSS specifies
            bosh.modInfos.refresh(doInfos=False)
            # Refresh UI, so WB is made aware of the changes to loadorder.txt
            modList.RefreshUI('ALL')

#------------------------------------------------------------------------------
class Oblivion_Button(App_Button):
    """Will close app on execute if autoquit is on."""
    @property
    def tip(self):
        if not bosh.settings['bash.statusbar.showversion']:
            tip = self._tip
        else:
            tip = self._tip + u' ' + self.version
        if bosh.dirs['app'].join(bush.game.laa.exe).exists() and bosh.settings.get('bash.laa.on',True):
            tip += u' + ' + bush.game.laa.name
        return tip

    @property
    def obseTip(self):
        # Oblivion (version)
        if bosh.settings['bash.statusbar.showversion']:
            tip = self._obseTip % (dict(version=self.version))
        else:
            tip = self._obseTip % (dict(version=''))
        # + OBSE
        tip += u' + %s %s' % (bush.game.se.shortName, self.obseVersion)
        # + LAA
        if bosh.dirs['app'].join(bush.game.laa.exe).exists() and bosh.settings.get('bash.laa.on',True):
            tip += u' + ' + bush.game.laa.name
        return tip

    def Execute(self,event):
        App_Button.Execute(self,event)
        if bosh.settings.get('bash.autoQuit.on',False):
            Link.Frame.Close(True)

#------------------------------------------------------------------------------
class TESCS_Button(App_Button):
    """CS button.  Needs a special Tooltip when OBSE is enabled."""
    @property
    def obseTip(self):
        # TESCS (version)
        if bosh.settings['bash.statusbar.showversion']:
            tip = self._obseTip % (dict(version=self.version))
        else:
            tip = self._obseTip % (dict(version=''))
        if not self.obseArg: return tip
        # + OBSE
        tip += u' + %s %s' % (bush.game.se.shortName, self.obseVersion)
        # + CSE
        path = bosh.dirs['mods'].join(u'obse',u'plugins',u'Construction Set Extender.dll')
        if path.exists():
            version = path.strippedVersion
            if version != (0,):
                version = u'.'.join([u'%i'%x for x in version])
            else:
                version = u''
            tip += u' + CSE %s' % version
        return tip

#------------------------------------------------------------------------------
class Obse_Button(StatusBar_Button):
    """Obse on/off state button."""
    def SetState(self,state=None):
        """Sets state related info. If newState != none, sets to new state first.
        For convenience, returns state when done."""
        if state is None: #--Default
            state = bosh.settings.get('bash.obse.on',True)
        elif state == -1: #--Invert
            state = not bosh.settings.get('bash.obse.on',False)
        bosh.settings['bash.obse.on'] = state
        if bush.game.laa.launchesSE and not state and BashStatusBar.laaButton.gButton is not None:
            # 4GB Launcher automatically launches the SE, so turning of the SE
            # required turning off the 4GB Launcher as well
            BashStatusBar.laaButton.SetState(state)
        # BitmapButton
        image = images[(u'checkbox.green.off.%s'%bosh.settings['bash.statusbar.iconSize'],
                        u'checkbox.green.on.%s'%bosh.settings['bash.statusbar.iconSize'])[state]]
        tip = ((_(u"%s %s Disabled"),_(u"%s %s Enabled"))[state]) % (bush.game.se.shortName, self.obseVersion)
        self.gButton.SetBitmapLabel(image.GetBitmap())
        self.gButton.SetToolTip(tooltip(tip))
        self.UpdateToolTips(state)

    @staticmethod
    def UpdateToolTips(state=None):
        if state is None:
            state = bosh.settings.get('bash.obse.on',True)
        tipAttr = ('tip','obseTip')[state]
        for button in App_Button.obseButtons:
            button.gButton.SetToolTip(tooltip(getattr(button,tipAttr,u'')))
        return state

    def GetBitmapButton(self,window,style=0):
        exeObse = bosh.dirs['app'].join(bush.game.se.exe)
        if exeObse.exists():
            bitmap = images[u'checkbox.green.off.%s'%bosh.settings['bash.statusbar.iconSize']].GetBitmap()
            self.createButton(window,bitmap,style=style)
            self.SetState()
            return self.gButton
        else:
            return None

    def Execute(self,event):
        """Invert state."""
        self.SetState(-1)

class LAA_Button(Obse_Button):
    """4GB Launcher on/off state button."""
    def SetState(self,state=None):
        """Sets state related info.  If newState != none, sets to new state first.
        For convenience, returns state when done."""
        if state is None: #--Default
            state = bosh.settings.get('bash.laa.on',True)
        elif state == -1: #--Invert
            state = not bosh.settings.get('bash.laa.on',False)
        bosh.settings['bash.laa.on'] = state
        if bush.game.laa.launchesSE and BashStatusBar.obseButton.gButton is not None:
            if state:
                # If the 4gb launcher launches the SE, enable the SE when enabling this
                BashStatusBar.obseButton.SetState(state)
            else:
                # We need the obse button to update the tooltips anyway
                BashStatusBar.obseButton.UpdateToolTips()
        # BitmapButton
        image = images[(u'checkbox.blue.off.%s'%bosh.settings['bash.statusbar.iconSize'],
                        u'checkbox.blue.on.%s'%bosh.settings['bash.statusbar.iconSize'])[state]]
        tip = bush.game.laa.name + (_(u' Disabled'),_(u' Enabled'))[state]
        if self.gButton:
            self.gButton.SetBitmapLabel(image.GetBitmap())
            self.gButton.SetToolTip(tooltip(tip))
        return state

    def GetBitmapButton(self,window,style=0):
        exeLAA = bosh.dirs['app'].join(bush.game.laa.exe)
        if exeLAA.exists():
            bitmap = images[u'checkbox.blue.off.%s'%bosh.settings['bash.statusbar.iconSize']].GetBitmap()
            self.createButton(window,bitmap,style=style)
            self.SetState()
            return self.gButton
        else:
            return None

#------------------------------------------------------------------------------
class AutoQuit_Button(StatusBar_Button):
    """Button toggling application closure when launching Oblivion."""
    def SetState(self,state=None):
        """Sets state related info. If newState != none, sets to new state first.
        For convenience, returns state when done."""
        if state is None: #--Default
            state = bosh.settings.get('bash.autoQuit.on',False)
        elif state == -1: #--Invert
            state = not bosh.settings.get('bash.autoQuit.on',False)
        bosh.settings['bash.autoQuit.on'] = state
        image = images[(u'checkbox.red.off.%s'%bosh.settings['bash.statusbar.iconSize'],
                        u'checkbox.red.x.%s'%bosh.settings['bash.statusbar.iconSize'])[state]]
        tip = (_(u"Auto-Quit Disabled"),_(u"Auto-Quit Enabled"))[state]
        self.gButton.SetBitmapLabel(image.GetBitmap())
        self.gButton.SetToolTip(tooltip(tip))

    def GetBitmapButton(self,window,style=0):
        bitmap = images[u'checkbox.red.off.%s'%bosh.settings['bash.statusbar.iconSize']].GetBitmap()
        self.createButton(window,bitmap,style=style)
        self.SetState()
        return self.gButton

    def Execute(self,event):
        """Invert state."""
        self.SetState(-1)

#------------------------------------------------------------------------------
class App_Help(StatusBar_Button):
    """Show help browser."""
    def GetBitmapButton(self,window,style=0):
        self.createButton(
            window,
            images[u'help.%s'%bosh.settings['bash.statusbar.iconSize']].GetBitmap(),
            style=style,
            tip=_(u"Help File"))
        return self.gButton

    def Execute(self,event):
        """Handle menu selection."""
        html = bosh.dirs['mopy'].join(u'Docs\Wrye Bash General Readme.html')
        if html.exists():
            html.start()
        else:
            balt.showError(Link.Frame, _(u'Cannot find General Readme file.'))

#------------------------------------------------------------------------------
class App_DocBrowser(StatusBar_Button):
    """Show doc browser."""
    def GetBitmapButton(self,window,style=0):
        self.createButton(
            window,
            images[u'doc.%s'%bosh.settings['bash.statusbar.iconSize']].GetBitmap(),
            style=style,
            tip=_(u"Doc Browser"))
        return self.gButton

    def Execute(self,event):
        """Handle menu selection."""
        if not Link.Frame.docBrowser:
            DocBrowser().Show()
            bosh.settings['bash.modDocs.show'] = True
        #balt.ensureDisplayed(docBrowser)
        Link.Frame.docBrowser.Raise()

#------------------------------------------------------------------------------
class App_Settings(StatusBar_Button):
    """Show color configuration dialog."""
    def GetBitmapButton(self,window,style=0):
        self.createButton(
            window,
            Image(GPath(bosh.dirs['images'].join(u'settingsbutton%s.png'%bosh.settings['bash.statusbar.iconSize']))).GetBitmap(),
            style=style,
            tip=_(u'Settings'),
            onRClick=self.Execute)
        return self.gButton

    def Execute(self,event):
        BashStatusBar.SettingsMenu.PopupMenu(Link.Frame.GetStatusBar(),Link.Frame,None)

#------------------------------------------------------------------------------
class App_Restart(StatusBar_Button):
    """Restart Wrye Bash"""
    def GetBitmapButton(self,window,style=0):
        if self.gButton is not None: self.gButton.Destroy()
        size = bosh.settings['bash.statusbar.iconSize']
        self.gButton = bitmapButton(window,
            staticBitmap(window, special='undo', size=(size,size)),
            style=style,
            tip=_(u'Restart'),
            onClick = self.Execute,
            onRClick = self.DoPopupMenu)
        return self.gButton

    def Execute(self,event):
        Link.Frame.Restart()

#------------------------------------------------------------------------------
class App_GenPickle(StatusBar_Button):
    """Generate PKL File. Ported out of bish.py which wasn't working."""
    def GetBitmapButton(self,window,style=0):
        return self.createButton(
            window,
            Image(GPath(bosh.dirs['images'].join(u'pickle%s.png'%bosh.settings['bash.statusbar.iconSize']))).GetBitmap(),
            style=style,
            tip=_(u"Generate PKL File"))

    def Execute(self,event,fileName=None):
        """Updates map of GMST eids to fids in bash\db\Oblivion_ids.pkl, based either
        on a list of new eids or the gmsts in the specified mod file. Updated pkl file
        is dropped in Mopy directory."""
        #--Data base
        import cPickle
        try:
            fids = cPickle.load(GPath(bush.game.pklfile).open('r'))['GMST']
            if fids:
                maxId = max(fids.values())
            else:
                maxId = 0
        except:
            fids = {}
            maxId = 0
        maxId = max(maxId,0xf12345)
        maxOld = maxId
        print 'maxId',hex(maxId)
        #--Eid list? - if the GMST has a 00000000 eid when looking at it in the cs with nothing
        # but oblivion.esm loaded you need to add the gmst to this list, rebuild the pickle and overwrite the old one.
        for eid in bush.game.gmstEids:
            if eid not in fids:
                maxId += 1
                fids[eid] = maxId
                print '%08X  %08X %s' % (0,maxId,eid)
                #--Source file
        if fileName:
            sorter = lambda a: a.eid
            loadFactory = bosh.LoadFactory(False,bosh.MreGmst)
            modInfo = bosh.modInfos[GPath(fileName)]
            modFile = bosh.ModFile(modInfo,loadFactory)
            modFile.load(True)
            for gmst in sorted(modFile.GMST.records,key=sorter):
                print gmst.eid, gmst.value
                if gmst.eid not in fids:
                    maxId += 1
                    fids[gmst.eid] = maxId
                    print '%08X  %08X %s' % (gmst.fid,maxId,gmst.eid)
        #--Changes?
        if maxId > maxOld:
            outData = {'GMST':fids}
            cPickle.dump(outData,GPath(bush.game.pklfile).open('w'))
            print _(u"%d new gmst ids written to "+bush.game.pklfile) % ((maxId - maxOld),)
        else:
            print _(u'No changes necessary. PKL data unchanged.')

#------------------------------------------------------------------------------
class App_ModChecker(StatusBar_Button):
    """Show mod checker."""
    def GetBitmapButton(self,window,style=0):
        return self.createButton(
            window,
            Image(GPath(bosh.dirs['images'].join(u'ModChecker%s.png'%bosh.settings['bash.statusbar.iconSize']))).GetBitmap(),
            style=style,
            tip=_(u"Mod Checker"))

    def Execute(self,event):
        """Handle menu selection."""
        if not Link.Frame.modChecker:
            ModChecker().Show()
        #balt.ensureDisplayed(modChecker)
        Link.Frame.modChecker.Raise()
