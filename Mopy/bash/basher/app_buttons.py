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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
import subprocess
import webbrowser
from . import BashStatusBar, BashFrame
from .frames import ModChecker, DocBrowser
from .. import bass, bosh, bolt, balt, bush, parsers, load_order
from ..balt import ItemLink, Link, Links, bitmapButton, \
    SeparatorLink, tooltip, BoolLink, staticBitmap
from ..bolt import GPath
from ..exception import AbstractError
from ..env import getJava

__all__ = ['Obse_Button', 'LAA_Button', 'AutoQuit_Button', 'Game_Button',
           'TESCS_Button', 'App_Button', 'Tooldir_Button', 'App_Tes4View',
           'App_BOSS', 'App_DocBrowser', 'App_ModChecker', 'App_Settings',
           'App_Help', 'App_Restart', 'App_GenPickle']

#------------------------------------------------------------------------------
# StatusBar Links--------------------------------------------------------------
#------------------------------------------------------------------------------
class _StatusBar_Hide(ItemLink):
    """The (single) link on the button's menu - hides the button."""
    def _initData(self, window, selection):
        super(_StatusBar_Hide, self)._initData(window, selection)
        tip_ = window.GetToolTip().GetTip()
        self._text = _(u"Hide '%s'") % tip_
        self._help = _(u"Hides %(buttonname)s's status bar button (can be"
            u" restored through the settings menu).") % ({'buttonname': tip_})

    def Execute(self): Link.Frame.statusBar.HideButton(self.window)

class StatusBar_Button(ItemLink):
    """Launch an application."""
    _tip = u''
    @property
    def sb_button_tip(self): return self._tip

    def __init__(self,uid=None,canHide=True,tip=u''):
        """ui: Unique identifier, used for saving the order of status bar icons
               and whether they are hidden/shown.
           canHide: True if this button is allowed to be hidden."""
        super(StatusBar_Button, self).__init__()
        self.mainMenu = Links()
        self.canHide = canHide
        self.gButton = None
        self._tip = tip or self.__class__._tip
        if uid is None: uid = (self.__class__.__name__, self._tip)
        self.uid = uid

    def IsPresent(self):
        """Due to the way status bar buttons are implemented debugging is a
        pain - I provided this base class method to early filter out non
        existent buttons."""
        return True

    def GetBitmapButton(self, window, style, **kwdargs):
        """Create and return gui button - you must define imageKey - WIP overrides"""
        btn_image = kwdargs.pop('image', None) or balt.images[self.imageKey %
                        bass.settings['bash.statusbar.iconSize']].GetBitmap()
        kwdargs['onRClick'] = kwdargs.pop('onRClick', None) or self.DoPopupMenu
        kwdargs['onBBClick'] = self.Execute
        if self.gButton is not None:
            self.gButton.Destroy()
        self.gButton = bitmapButton(window, btn_image, style=style,
                                    button_tip=self.sb_button_tip, **kwdargs)
        return self.gButton

    def DoPopupMenu(self,event):
        if self.canHide:
            if len(self.mainMenu) == 0 or not isinstance(self.mainMenu[-1],
                                                         _StatusBar_Hide):
                if len(self.mainMenu) > 0:
                    self.mainMenu.append(SeparatorLink())
                self.mainMenu.append(_StatusBar_Hide())
        if len(self.mainMenu) > 0:
            self.mainMenu.PopupMenu(self.gButton,Link.Frame,0)
        else:
            event.Skip()

    # Helper function to get OBSE version
    @property
    def obseVersion(self):
        if not bass.settings['bash.statusbar.showversion']: return u''
        if bass.inisettings['SteamInstall']:
            se_exe = bass.dirs['app'].join(bush.game.se.steam_exe)
        else:
            se_exe = bass.dirs['app'].join(bush.game.se.exe)
        if not se_exe.isfile(): return u''
        return u' ' + u'.'.join([u'%s' % x for x in se_exe.strippedVersion])

#------------------------------------------------------------------------------
# App Links -------------------------------------------------------------------
#------------------------------------------------------------------------------
class App_Button(StatusBar_Button):
    """Launch an application."""
    obseButtons = []

    @property
    def version(self):
        if not bass.settings['bash.statusbar.showversion']: return u''
        if not self.isJava and self.IsPresent():
            version = self.exePath.strippedVersion
            if version != (0,):
                version = u'.'.join([u'%s'%x for x in version])
                return version
        return u''

    @property
    def sb_button_tip(self):
        if not bass.settings['bash.statusbar.showversion']: return self._tip
        else:
            return self._tip + u' ' + self.version

    @property
    def obseTip(self):
        if self._obseTip is None: return None
        return self._obseTip % (dict(version=self.version))

    def __init__(self, exePathArgs, images, tip, obseTip=None, obseArg=None,
                 workingDir=None, uid=None, canHide=True):
        """Initialize
        exePathArgs (string): exePath
        exePathArgs (tuple): (exePath,*exeArgs)
        exePathArgs (list):  [exePathArgs,altExePathArgs,...]
        images: [16x16,24x24,32x32] images
        """
        super(App_Button, self).__init__(uid, canHide, tip)
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
        self.workingDir = GPath(workingDir) if workingDir else None
        #--Exe stuff, note that sometimes exePath is None
        self.isExe = self.exePath and self.exePath.cext == u'.exe'
        #--Java stuff
        self.isJava = self.exePath and self.exePath.cext == u'.jar'
        if self.isJava:
            self.java = getJava()
            self.jar = self.exePath
            self.appArgs = u''.join(self.exeArgs)
        #--shortcut
        self.isShortcut = self.exePath and self.exePath.cext == u'.lnk'
        #--Folder
        self.isFolder = self.exePath and self.exePath.isdir()
        #--**SE stuff
        self._obseTip = obseTip
        self.obseArg = obseArg
        # used by App_Button.Execute(): be sure to set them _before_ calling it
        self.extraArgs = ()
        self.wait = False

    def IsPresent(self):
        if self.isJava:
            return self.java.exists() and self.jar.exists()
        else:
            if self.exePath in bosh.undefinedPaths:
                return False
            return self.exePath.exists()

    def GetBitmapButton(self, window, style, **kwdargs):
        if not self.IsPresent(): return None
        size = bass.settings['bash.statusbar.iconSize'] # 16, 24, 32
        idex = (size / 8) - 2 # 0, 1, 2, duh
        super(App_Button, self).GetBitmapButton(window, style=style,
              image=self.images[idex].GetBitmap())
        if self.obseTip is not None:
            App_Button.obseButtons.append(self)
            if BashStatusBar.obseButton.button_state:
                self.gButton.SetToolTip(tooltip(self.obseTip))
        return self.gButton

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

    def Execute(self):
        if not self.IsPresent():
            balt.showError(Link.Frame,
                           _(u'Application missing: %s') % self.exePath.s,
                           _(u"Could not launch '%s'" % self.exePath.stail)
                           )
            return
        if self.isShortcut or self.isFolder:
            webbrowser.open(self.exePath.s)
        elif self.isJava:
            cwd = bolt.Path.getcwd()
            if self.workingDir:
                self.workingDir.setcwd()
            else:
                self.jar.head.setcwd()
            try:
                subprocess.Popen(
                    (self.java.stail, u'-jar', self.jar.stail, self.appArgs),
                     executable=self.java.s, close_fds=True)
            except UnicodeError:
                self._showUnicodeError()
            except Exception as error:
                self.ShowError(error)
            finally:
                cwd.setcwd()
        elif self.isExe:
            exeObse = bass.dirs['app'].join(bush.game.se.exe)
            exeLaa = bass.dirs['app'].join(bush.game.laa.exe)
            if BashStatusBar.laaButton.button_state and \
                            self.exePath.tail == bush.game.launch_exe:
                # Should use the LAA Launcher
                exePath = exeLaa
                args = [exePath.s]
            elif self.obseArg is not None and \
                    BashStatusBar.obseButton.button_state:
                if bass.inisettings['SteamInstall'] and self.exePath.tail == u'Oblivion.exe':
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
            if self.extraArgs: args.extend(self.extraArgs)
            Link.Frame.SetStatusInfo(u' '.join(args[1:]))
            cwd = bolt.Path.getcwd()
            if self.workingDir:
                self.workingDir.setcwd()
            else:
                exePath.head.setcwd()
            try:
                popen = subprocess.Popen(args, close_fds=True)
                if self.wait:
                    popen.wait()
            except UnicodeError:
                self._showUnicodeError()
            except WindowsError as werr:
                if werr.winerror != 740:
                    self.ShowError(werr)
                try:
                    import win32api
                    win32api.ShellExecute(0,'runas', exePath.s,
                                          u'%s' % self.exeArgs,
                                          bass.dirs['app'].s, 1)
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

#------------------------------------------------------------------------------
class Tooldir_Button(App_Button):
    """Just an App_Button that's path is in bosh.tooldirs
       Use this to automatically set the uid for the App_Button."""
    def __init__(self,toolKey,images,tip,obseTip=None,obseArg=None,workingDir=None,canHide=True):
        App_Button.__init__(self, bass.tooldirs[toolKey], images, tip, obseTip, obseArg, workingDir, toolKey, canHide)

#------------------------------------------------------------------------------
class _Mods_xEditExpert(BoolLink):
    """Toggle xEdit expert mode (when launched via Bash)."""

    def __init__(self):
        super(_Mods_xEditExpert, self).__init__()
        self._text, self.key = bush.game.xEdit_expert

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
        if bush.game.xEdit_expert:
            self.mainMenu.append(_Mods_xEditExpert())

    def IsPresent(self):
        if self.exePath in bosh.undefinedPaths or not self.exePath.exists():
            testPath = bass.tooldirs['Tes4ViewPath']
            if testPath not in bosh.undefinedPaths and testPath.exists():
                self.exePath = testPath
                return True
            return False
        return True

    def Execute(self):
        is_expert = bush.game.xEdit_expert and bass.settings[
            bush.game.xEdit_expert[1]]
        extraArgs = bass.inisettings[
            'xEditCommandLineArguments'].split() if is_expert else []
        if balt.getKeyState_Control():
            extraArgs.append(u'-FixupPGRD')
        if balt.getKeyState_Shift():
            extraArgs.append(u'-skipbsa')
        if is_expert:
            extraArgs.append(u'-IKnowWhatImDoing')
        self.extraArgs = tuple(extraArgs)
        super(App_Tes4View, self).Execute()

#------------------------------------------------------------------------------
class _Mods_BOSSDisableLockTimes(BoolLink):
    """Toggle Lock Load Order disabling when launching BOSS through Bash."""
    _text = _(u'BOSS Disable Lock Load Order')
    key = 'BOSS.ClearLockTimes'
    _help = _(u"If selected, will temporarily disable Bash's Lock Load Order"
             u" when running BOSS through Bash.")

#------------------------------------------------------------------------------
class _Mods_BOSSLaunchGUI(BoolLink):
    """If BOSS.exe is available then boss_gui.exe should be too."""
    _text, key, _help = _(u'Launch using GUI'), 'BOSS.UseGUI', \
                        _(u"If selected, Bash will run BOSS's GUI.")

class App_BOSS(App_Button):
    """loads BOSS"""
    def __init__(self, *args, **kwdargs):
        App_Button.__init__(self, *args, **kwdargs)
        self.boss_path = self.exePath
        self.mainMenu.append(_Mods_BOSSLaunchGUI())
        self.mainMenu.append(_Mods_BOSSDisableLockTimes())

    def Execute(self):
        if bass.settings['BOSS.UseGUI']:
            self.exePath = self.boss_path.head.join(u'boss_gui.exe')
        else:
            self.exePath = self.boss_path
        self.wait = bool(bass.settings['BOSS.ClearLockTimes'])
        extraArgs = []
        if balt.getKeyState(82) and balt.getKeyState_Shift():
            extraArgs.append(u'-r 2',) # Revert level 2 - BOSS version 1.6+
        elif balt.getKeyState(82):
            extraArgs.append(u'-r 1',) # Revert level 1 - BOSS version 1.6+
        if balt.getKeyState(83):
            extraArgs.append(u'-s',) # Silent Mode - BOSS version 1.6+
        if balt.getKeyState(67): #c - print crc calculations in BOSS log.
            extraArgs.append(u'-c',)
        if bass.tooldirs['boss'].version >= (2, 0, 0, 0):
            # After version 2.0, need to pass in the -g argument
            extraArgs.append(u'-g%s' % bush.game.fsName,)
        self.extraArgs = tuple(extraArgs)
        super(App_BOSS, self).Execute()
        if bass.settings['BOSS.ClearLockTimes']:
            # Clear the saved times from before
            with load_order.Unlock():
                # Refresh to get the new load order that BOSS specified. If
                # on timestamp method scan the data dir, if not loadorder.txt
                # should have changed, refreshLoadOrder should detect that
                bosh.modInfos.refresh(
                    refresh_infos=not bosh.load_order.using_txt_file())
            # Refresh UI, so WB is made aware of the changes to load order
            BashFrame.modList.RefreshUI(refreshSaves=True, focus_list=False)

#------------------------------------------------------------------------------
class Game_Button(App_Button):
    """Will close app on execute if autoquit is on."""
    def __init__(self, exe_path_args, version_path, images, tip, obse_tip):
        super(Game_Button, self).__init__(
            exePathArgs=exe_path_args, images=images, tip=tip,
            obseTip=obse_tip, obseArg=u'', uid=u'Oblivion')
        self._version_path = version_path

    @property
    def sb_button_tip(self):
        tip_ = self._tip + u' ' + self.version if self.version else self._tip
        if BashStatusBar.laaButton.button_state:
            tip_ += u' + ' + bush.game.laa.name
        return tip_

    @property
    def obseTip(self):
        # Oblivion (version)
        tip_ = self._obseTip % (dict(version=self.version))
        # + OBSE
        tip_ += u' + %s%s' % (bush.game.se.se_abbrev, self.obseVersion)
        # + LAA
        if BashStatusBar.laaButton.button_state:
            tip_ += u' + ' + bush.game.laa.name
        return tip_

    def Execute(self):
        super(Game_Button, self).Execute()
        if bass.settings.get('bash.autoQuit.on',False):
            Link.Frame.Close(True)

    @property
    def version(self):
        if not bass.settings['bash.statusbar.showversion']: return u''
        version = self._version_path.strippedVersion
        if version != (0,):
            version = u'.'.join([u'%s'%x for x in version])
            return version
        return u''

#------------------------------------------------------------------------------
class TESCS_Button(App_Button):
    """CS button.  Needs a special Tooltip when OBSE is enabled."""
    @property
    def obseTip(self):
        # TESCS (version)
        tip_ = self._obseTip % (dict(version=self.version))
        if not self.obseArg: return tip_
        # + OBSE
        tip_ += u' + %s%s' % (bush.game.se.se_abbrev, self.obseVersion)
        # + CSE
        cse_path = bass.dirs['mods'].join(u'obse', u'plugins',
                                          u'Construction Set Extender.dll')
        if cse_path.exists():
            version = cse_path.strippedVersion
            if version != (0,):
                version = u'.'.join([u'%i'%x for x in version])
            else:
                version = u''
            tip_ += u' + CSE %s' % version
        return tip_

#------------------------------------------------------------------------------
class _StatefulButton(StatusBar_Button):
    _state_key = u'OVERRIDE' # bass settings key for button state (un/checked)
    _state_img_key = u'OVERRIDE' # image key with state and size placeholders
    _default_state = True

    @property
    def sb_button_tip(self): raise AbstractError

    def SetState(self, state=None):
        """Set state related info. If newState != None, sets to new state
        first. For convenience, returns state when done."""
        if state is None: #--Default
            self.button_state = self.button_state
        elif state == -1: #--Invert
            self.button_state = True ^ self.button_state
        if self.gButton:
            self.gButton.SetBitmapLabel(balt.images[self.imageKey %
                        bass.settings['bash.statusbar.iconSize']].GetBitmap())
            self.gButton.SetToolTip(tooltip(self.sb_button_tip))

    @property
    def button_state(self): return self._present and bass.settings.get(
        self._state_key, self._default_state)
    @button_state.setter
    def button_state(self, val):
        bass.settings[self._state_key] = val

    @property
    def imageKey(self): return self.__class__._state_img_key % (
        [u'off', u'on'][self.button_state], u'%d')

    @property
    def _present(self): return True

    def GetBitmapButton(self, window, style, **kwdargs):
        if not self._present: return None
        self.SetState()
        return super(_StatefulButton, self).GetBitmapButton(window, style,
                                                            **kwdargs)

    def Execute(self):
        """Invert state."""
        self.SetState(-1)

class Obse_Button(_StatefulButton):
    """Obse on/off state button."""
    _state_key = 'bash.obse.on'
    _state_img_key = u'checkbox.green.%s.%s'
    @property
    def _present(self): return bass.dirs['app'].join(bush.game.se.exe).exists()

    def SetState(self,state=None):
        super(Obse_Button, self).SetState(state)
        if bush.game.laa.launchesSE and not state and BashStatusBar.laaButton.gButton is not None:
            # 4GB Launcher automatically launches the SE, so turning of the SE
            # required turning off the 4GB Launcher as well
            BashStatusBar.laaButton.SetState(state)
        self.UpdateToolTips()
        return state

    @property
    def sb_button_tip(self): return ((_(u"%s%s Disabled"), _(u"%s%s Enabled"))[
        self.button_state]) % (bush.game.se.se_abbrev, self.obseVersion)

    def UpdateToolTips(self):
        tipAttr = ('sb_button_tip', 'obseTip')[self.button_state]
        for button in App_Button.obseButtons:
            button.gButton.SetToolTip(tooltip(getattr(button,tipAttr,u'')))

class LAA_Button(_StatefulButton):
    """4GB Launcher on/off state button."""
    _state_key = 'bash.laa.on'
    _state_img_key = u'checkbox.blue.%s.%s'
    @property
    def _present(self):
        return bass.dirs['app'].join(bush.game.laa.exe).exists()

    def SetState(self,state=None):
        super(LAA_Button, self).SetState(state)
        if bush.game.laa.launchesSE and BashStatusBar.obseButton.gButton is not None:
            if state:
                # If the 4gb launcher launches the SE, enable the SE when enabling this
                BashStatusBar.obseButton.SetState(state)
            else:
                # We need the obse button to update the tooltips anyway
                BashStatusBar.obseButton.UpdateToolTips()
        return state

    @property
    def sb_button_tip(self): return bush.game.laa.name + (
        _(u' Disabled'), _(u' Enabled'))[self.button_state]

#------------------------------------------------------------------------------
class AutoQuit_Button(_StatefulButton):
    """Button toggling application closure when launching Oblivion."""
    _state_key = 'bash.autoQuit.on'
    _state_img_key = u'checkbox.red.%s.%s'
    _default_state = False

    @property
    def imageKey(self): return self._state_img_key % (
        [u'off', u'x'][self.button_state], u'%d')

    @property
    def sb_button_tip(self): return (_(u"Auto-Quit Disabled"), _(u"Auto-Quit Enabled"))[
        self.button_state]

#------------------------------------------------------------------------------
class App_Help(StatusBar_Button):
    """Show help browser."""
    imageKey, _tip = u'help.%s', _(u"Help File")

    def Execute(self):
        html = bass.dirs['mopy'].join(u'Docs\Wrye Bash General Readme.html')
        if html.exists():
            html.start()
        else:
            balt.showError(Link.Frame, _(u'Cannot find General Readme file.'))

#------------------------------------------------------------------------------
class App_DocBrowser(StatusBar_Button):
    """Show doc browser."""
    imageKey, _tip = u'doc.%s', _(u"Doc Browser")

    def Execute(self):
        if not Link.Frame.docBrowser:
            DocBrowser().Show()
            bass.settings['bash.modDocs.show'] = True
        #balt.ensureDisplayed(docBrowser)
        Link.Frame.docBrowser.Raise()

#------------------------------------------------------------------------------
class App_Settings(StatusBar_Button):
    """Show settings dialog."""
    imageKey, _tip = 'settingsbutton.%s', _(u'Settings')

    def GetBitmapButton(self, window, style, **kwdargs):
        return super(App_Settings, self).GetBitmapButton(
            window, style, onRClick=lambda __event: self.Execute())

    def Execute(self):
        BashStatusBar.SettingsMenu.PopupMenu(Link.Frame.statusBar, Link.Frame,
                                             None)

#------------------------------------------------------------------------------
class App_Restart(StatusBar_Button):
    """Restart Wrye Bash"""
    _tip = _(u"Restart")

    def GetBitmapButton(self, window, style, **kwdargs):
        size = bass.settings['bash.statusbar.iconSize']
        return super(App_Restart, self).GetBitmapButton(window, style,
            image=staticBitmap(window, special='undo', size=(size,size)))

    def Execute(self): Link.Frame.Restart()

#------------------------------------------------------------------------------
class App_GenPickle(StatusBar_Button):
    """Generate PKL File. Ported out of bish.py which wasn't working."""
    imageKey, _tip = 'pickle.%s', _(u"Generate PKL File")

    def Execute(self): self._update_pkl()

    @staticmethod
    def _update_pkl(fileName=None):
        """Update map of GMST eids to fids in bash\db\Oblivion_ids.pkl,
        based either on a list of new eids or the gmsts in the specified mod
        file. Updated pkl file is dropped in Mopy directory."""
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
        maxId = max(maxId, 0xf12345)
        maxOld = maxId
        print 'maxId', hex(maxId)
        #--Eid list? - if the GMST has a 00000000 eid when looking at it in
        # the CS with nothing but oblivion.esm loaded you need to add the
        # gmst to this list, rebuild the pickle and overwrite the old one.
        for eid in bush.game.gmstEids:
            if eid not in fids:
                maxId += 1
                fids[eid] = maxId
                print '%08X  %08X %s' % (0, maxId, eid)
        #--Source file
        if fileName:
            sorter = lambda a: a.eid
            loadFactory = parsers.LoadFactory(False, bush.game_mod.records.MreGmst)
            modInfo = bosh.modInfos[GPath(fileName)]
            modFile = parsers.ModFile(modInfo, loadFactory)
            modFile.load(True)
            for gmst in sorted(modFile.GMST.records, key=sorter):
                print gmst.eid, gmst.value
                if gmst.eid not in fids:
                    maxId += 1
                    fids[gmst.eid] = maxId
                    print '%08X  %08X %s' % (gmst.fid, maxId, gmst.eid)
        #--Changes?
        if maxId > maxOld:
            outData = {'GMST': fids}
            cPickle.dump(outData, GPath(bush.game.pklfile).open('w'))
            print _(u"%d new gmst ids written to " + bush.game.pklfile) % (
                (maxId - maxOld),)
        else:
            print _(u'No changes necessary. PKL data unchanged.')

#------------------------------------------------------------------------------
class App_ModChecker(StatusBar_Button):
    """Show mod checker."""
    imageKey, _tip = 'modchecker.%s', _(u"Mod Checker")

    def Execute(self):
        if not Link.Frame.modChecker:
            ModChecker().Show()
        #balt.ensureDisplayed(modChecker)
        Link.Frame.modChecker.Raise()
