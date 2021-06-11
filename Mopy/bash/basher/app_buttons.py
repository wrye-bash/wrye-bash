# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, either version 3
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <https://www.gnu.org/licenses/>.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
import os
import subprocess
import webbrowser
from . import BashStatusBar, BashFrame
from .frames import PluginChecker, DocBrowser
from .settings_dialog import SettingsDialog
from .. import bass, bosh, bolt, balt, bush, load_order
from ..balt import ItemLink, Link, Links, SeparatorLink, BoolLink
from ..env import getJava, get_game_version_fallback
from ..exception import AbstractError
from ..gui import ClickableImage, EventResult, staticBitmap, get_key_down, \
    get_shift_down

__all__ = [u'Obse_Button', u'LAA_Button', u'AutoQuit_Button', u'Game_Button',
           u'TESCS_Button', u'App_Tes4View', u'App_BOSS', u'App_Help',
           u'App_DocBrowser', u'App_PluginChecker', u'App_Settings',
           u'App_Restart', u'app_button_factory']

#------------------------------------------------------------------------------
# StatusBar Links--------------------------------------------------------------
#------------------------------------------------------------------------------
class _StatusBar_Hide(ItemLink):
    """The (single) link on the button's menu - hides the button."""
    @property
    def link_text(self):
        return _(u"Hide '%s'") % self.window.tooltip

    @property
    def link_help(self):
        return _(u"Hides %(buttonname)s's status bar button (can be restored "
                 u"through the settings menu).") % {
            u'buttonname': self.window.tooltip}

    def Execute(self): Link.Frame.statusBar.HideButton(self.window)

class StatusBar_Button(ItemLink):
    """Launch an application."""
    _tip = u''
    @property
    def sb_button_tip(self): return self._tip

    def __init__(self, uid=None, canHide=True, button_tip=u''):
        """ui: Unique identifier, used for saving the order of status bar icons
               and whether they are hidden/shown.
           canHide: True if this button is allowed to be hidden."""
        super(StatusBar_Button, self).__init__()
        self.mainMenu = Links()
        self.canHide = canHide
        self.gButton = None
        self._tip = button_tip or self.__class__._tip
        if uid is None: uid = (self.__class__.__name__, self._tip)
        self.uid = uid

    def IsPresent(self):
        """Due to the way status bar buttons are implemented debugging is a
        pain - I provided this base class method to early filter out non
        existent buttons."""
        return True

    def GetBitmapButton(self, window, image=None, onRClick=None):
        """Create and return gui button - you must define imageKey - WIP overrides"""
        btn_image = image or balt.images[self.imageKey % bass.settings[
            u'bash.statusbar.iconSize']].GetBitmap()
        if self.gButton is not None:
            self.gButton.destroy_component()
        self.gButton = ClickableImage(window, btn_image,
                                      btn_tooltip=self.sb_button_tip)
        self.gButton.on_clicked.subscribe(self.Execute)
        self.gButton.on_right_clicked.subscribe(onRClick or self.DoPopupMenu)
        return self.gButton

    def DoPopupMenu(self):
        if self.canHide:
            if len(self.mainMenu) == 0 or not isinstance(self.mainMenu[-1],
                                                         _StatusBar_Hide):
                if len(self.mainMenu) > 0:
                    self.mainMenu.append(SeparatorLink())
                self.mainMenu.append(_StatusBar_Hide())
        if len(self.mainMenu) > 0:
            self.mainMenu.popup_menu(self.gButton, 0)
            return EventResult.FINISH ##: Kept it as such, test if needed

    # Helper function to get OBSE version
    @property
    def obseVersion(self):
        if not bass.settings[u'bash.statusbar.showversion']: return u''
        for ver_file in bush.game.Se.ver_files:
            ver_path = bass.dirs[u'app'].join(ver_file)
            if ver_path.exists():
                return u' ' + u'.'.join([u'%s' % x for x
                                         in ver_path.strippedVersion])
        else:
            return u''

    def set_sb_button_tooltip(self): pass

#------------------------------------------------------------------------------
# App Links -------------------------------------------------------------------
#------------------------------------------------------------------------------
class _App_Button(StatusBar_Button):
    """Launch an application."""
    obseButtons = []

    @property
    def version(self):
        if not bass.settings[u'bash.statusbar.showversion']: return u''
        if self.IsPresent():
            version = self.exePath.strippedVersion
            if version != (0,):
                version = u'.'.join([u'%s'%x for x in version])
                return version
        return u''

    def set_sb_button_tooltip(self):
        if self.gButton: self.gButton.tooltip = self.sb_button_tip

    @property
    def sb_button_tip(self):
        if not bass.settings[u'bash.statusbar.showversion']: return self._tip
        else:
            return self._tip + u' ' + self.version

    @property
    def obseTip(self):
        if self._obseTip is None: return None
        return self._obseTip % {u'version': self.version}

    def __init__(self, exePath, exeArgs, images, tip, obseTip=None, uid=None,
                 canHide=True):
        """images: [16x16,24x24,32x32] images"""
        super(_App_Button, self).__init__(uid, canHide, tip)
        self.exeArgs = exeArgs
        self.exePath = exePath
        self.images = images
        #--**SE stuff
        self._obseTip = obseTip
        # used by _App_Button.Execute(): be sure to set them _before_ calling it
        self.extraArgs = ()
        self.wait = False

    def IsPresent(self):
        return self.exePath not in bosh.undefinedPaths and \
               self.exePath.exists()

    def GetBitmapButton(self, window, image=None, onRClick=None):
        if not self.IsPresent(): return None
        iconSize = bass.settings[u'bash.statusbar.iconSize'] # 16, 24, 32
        idex = (iconSize // 8) - 2 # 0, 1, 2, duh
        super(_App_Button, self).GetBitmapButton(
            window, self.images[idex].GetBitmap(), onRClick)
        if self.obseTip is not None:
            _App_Button.obseButtons.append(self)
            if BashStatusBar.obseButton.button_state:
                self.gButton.tooltip = self.obseTip
        return self.gButton

    def ShowError(self,error):
        balt.showError(Link.Frame,
                       (f'{error}\n\n' +
                        _(u'Used Path: ') + f'{self.exePath}\n' +
                        _(u'Used Arguments: ') + f'{self.exeArgs}'),
                       _(u"Could not launch '%s'") % self.exePath.stail)

    def _showUnicodeError(self):
        balt.showError(Link.Frame, _(
            u'Execution failed, because one or more of the command line '
            u'arguments failed to encode.'),
                       _(u"Could not launch '%s'") % self.exePath.stail)

    def Execute(self):
        if not self.IsPresent():
            balt.showError(Link.Frame,
                           _(u'Application missing: %s') % self.exePath,
                           _(u"Could not launch '%s'") % self.exePath.stail)
            return
        self._app_button_execute()

    def _app_button_execute(self):
        dir_ = os.getcwd()
        args = f'"{self.exePath}"'
        args += u' '.join([f'{arg}' for arg in self.exeArgs])
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
                self.exePath.head.setcwd()
                try:
                    webbrowser.open(self.exePath.s)
                except UnicodeError:
                    self._showUnicodeError()
                except Exception as error:
                    self.ShowError(error)
                finally:
                    cwd.setcwd()

class _ExeButton(_App_Button):

    def _app_button_execute(self):
        self._run_exe(self.exePath, [self.exePath.s])

    def _run_exe(self, exe_path, exe_args):
        exe_args.extend(self.exeArgs)
        if self.extraArgs: exe_args.extend(self.extraArgs)
        Link.Frame.set_status_info(u' '.join(exe_args[1:]))
        cwd = bolt.Path.getcwd()
        exe_path.head.setcwd()
        try:
            ##: Same unicodeSafe problem here - see Path.start
            popen = subprocess.Popen(exe_args, close_fds=True)
            if self.wait:
                popen.wait()
        except UnicodeError:
            self._showUnicodeError()
        except WindowsError as werr:
            if werr.winerror != 740:
                self.ShowError(werr)
            try:
                import win32api
                win32api.ShellExecute(0, 'runas', exe_path.s,
                    u'%s' % self.exeArgs, bass.dirs[u'app'].s, 1)
            except:
                self.ShowError(werr)
        except Exception as error:
            self.ShowError(error)
        finally:
            cwd.setcwd()

class _JavaButton(_App_Button):
    """_App_Button pointing to a .jar file."""

    @property
    def version(self): return u''

    def __init__(self, exePath, exeArgs, *args, **kwargs):
        super(_JavaButton, self).__init__(exePath, exeArgs, *args, **kwargs)
        self.java = getJava()
        self.appArgs = u''.join(self.exeArgs)

    def IsPresent(self):
        return self.java.exists() and self.exePath.exists()

    def _app_button_execute(self):
        cwd = bolt.Path.getcwd()
        self.exePath.head.setcwd()
        try:
            subprocess.Popen(
                (self.java.stail, u'-jar', self.exePath.stail, self.appArgs),
                executable=self.java.s, close_fds=True)
        except UnicodeError:
            self._showUnicodeError()
        except Exception as error:
            self.ShowError(error)
        finally:
            cwd.setcwd()

class _LnkOrDirButton(_App_Button):

    def _app_button_execute(self): webbrowser.open(self.exePath.s)

def _parse_button_arguments(exePathArgs):
    """Expected formats:
        exePathArgs (string): exePath
        exePathArgs (tuple): (exePath,*exeArgs)
        exePathArgs (list):  [exePathArgs,altExePathArgs,...]"""
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
    if isinstance(exePathArgs, tuple):
        exePath = exePathArgs[0]
        exeArgs = exePathArgs[1:]
    else:
        exePath = exePathArgs
        exeArgs = tuple()
    return exePath, exeArgs

def app_button_factory(exePathArgs, *args, **kwargs):
    exePath, exeArgs = _parse_button_arguments(exePathArgs)
    if exePath and exePath.cext == u'.exe': # note: sometimes exePath is None
        return _ExeButton(exePath, exeArgs, *args, **kwargs)
    if exePath and exePath.cext == u'.jar':
        return _JavaButton(exePath, exeArgs, *args, **kwargs)
    if exePath and( exePath.cext == u'.lnk' or exePath.isdir()):
        return _LnkOrDirButton(exePath, exeArgs, *args, **kwargs)
    return _App_Button(exePath, exeArgs, *args, **kwargs)

#------------------------------------------------------------------------------
class _Mods_xEditExpert(BoolLink):
    """Toggle xEdit expert mode (when launched via Bash)."""
    _text = _(u'Expert Mode')
    _help = _(u'Launch %s in expert mode.') % bush.game.Xe.full_name
    _bl_key = bush.game.Xe.xe_key_prefix + u'.iKnowWhatImDoing'

class _Mods_xEditSkipBSAs(BoolLink):
    """Toggle xEdit skip bsa mode (when launched via Bash)."""
    _text = _(u'Skip BSAs')
    _help = _(u'Skip loading BSAs when opening %s. Will disable some of its '
              u'functions.') % bush.game.Xe.full_name
    _bl_key = bush.game.Xe.xe_key_prefix + u'.skip_bsas'

class App_Tes4View(_ExeButton):
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
    def __init__(self, *args, **kwdargs):
        exePath, exeArgs = _parse_button_arguments(args[0])
        super(App_Tes4View, self).__init__(exePath, exeArgs, *args[1:], **kwdargs)
        if bush.game.Xe.xe_key_prefix:
            self.mainMenu.append(_Mods_xEditExpert())
            self.mainMenu.append(_Mods_xEditSkipBSAs())

    def IsPresent(self): # FIXME(inf) What on earth is this? What's the point?? --> check C:\not\a\valid\path.exe in default.ini
        if not super().IsPresent():
            testPath = bass.tooldirs[u'Tes4ViewPath']
            if testPath not in bosh.undefinedPaths and testPath.exists():
                self.exePath = testPath
                return True
            return False
        return True

    def Execute(self):
        is_expert = bush.game.Xe.xe_key_prefix and bass.settings[
            bush.game.Xe.xe_key_prefix + u'.iKnowWhatImDoing']
        skip_bsas = bush.game.Xe.xe_key_prefix and bass.settings[
            bush.game.Xe.xe_key_prefix + u'.skip_bsas']
        extraArgs = bass.inisettings[
            u'xEditCommandLineArguments'].split() if is_expert else []
        if is_expert:
            extraArgs.append(u'-IKnowWhatImDoing')
        if skip_bsas:
            extraArgs.append(u'-skipbsa')
        self.extraArgs = tuple(extraArgs)
        super(App_Tes4View, self).Execute()

#------------------------------------------------------------------------------
class _Mods_BOSSDisableLockTimes(BoolLink):
    """Toggle Lock Load Order disabling when launching BOSS through Bash."""
    _text = _(u'BOSS Disable Lock Load Order')
    _bl_key = u'BOSS.ClearLockTimes'
    _help = _(u"If selected, will temporarily disable Bash's Lock Load Order "
              u'when running BOSS through Bash.')

#------------------------------------------------------------------------------
class _Mods_BOSSLaunchGUI(BoolLink):
    """If BOSS.exe is available then boss_gui.exe should be too."""
    _text, _bl_key, _help = _(u'Launch using GUI'), u'BOSS.UseGUI', \
                            _(u"If selected, Bash will run BOSS's GUI.")

class App_BOSS(_ExeButton):
    """loads BOSS"""
    def __init__(self, *args, **kwdargs):
        exePath, exeArgs = _parse_button_arguments(args[0])
        super(App_BOSS, self).__init__(exePath, exeArgs, *args[1:], **kwdargs)
        self.boss_path = self.exePath
        self.mainMenu.append(_Mods_BOSSLaunchGUI())
        self.mainMenu.append(_Mods_BOSSDisableLockTimes())

    def Execute(self):
        if bass.settings[u'BOSS.UseGUI']:
            self.exePath = self.boss_path.head.join(u'boss_gui.exe')
        else:
            self.exePath = self.boss_path
        self.wait = bool(bass.settings[u'BOSS.ClearLockTimes'])
        extraArgs = []
        ##: These should become right click options instead
        if get_key_down(u'R'):
            if get_shift_down():
                extraArgs.append(u'-r 2') # Revert level 2 - BOSS version 1.6+
            else:
                extraArgs.append(u'-r 1') # Revert level 1 - BOSS version 1.6+
        if get_key_down(u'S'):
            extraArgs.append(u'-s') # Silent Mode - BOSS version 1.6+
        if get_key_down(u'C'): # Print crc calculations in BOSS log.
            extraArgs.append(u'-c')
        if bass.tooldirs[u'boss'].version >= (2, 0, 0, 0):
            # After version 2.0, need to pass in the -g argument
            extraArgs.append(u'-g%s' % bush.game.boss_game_name)
        self.extraArgs = tuple(extraArgs)
        super(App_BOSS, self).Execute()
        if bass.settings[u'BOSS.ClearLockTimes']:
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
class Game_Button(_ExeButton):
    """Will close app on execute if autoquit is on."""
    def __init__(self, exe_path_args, version_path, images, tip, obse_tip):
        exePath, exeArgs = _parse_button_arguments(exe_path_args)
        super(Game_Button, self).__init__(exePath, exeArgs, images=images,
            tip=tip, obseTip=obse_tip, uid=u'Oblivion')
        self._version_path = version_path

    @property
    def sb_button_tip(self):
        tip_ = self._tip + u' ' + self.version if self.version else self._tip
        if BashStatusBar.laaButton.button_state:
            tip_ += u' + ' + bush.game.Laa.laa_name
        return tip_

    @property
    def obseTip(self):
        # Oblivion (version)
        tip_ = self._obseTip % {u'version': self.version}
        # + OBSE
        tip_ += u' + %s%s' % (bush.game.Se.se_abbrev, self.obseVersion)
        # + LAA
        if BashStatusBar.laaButton.button_state:
            tip_ += u' + ' + bush.game.Laa.laa_name
        return tip_

    def _app_button_execute(self):
        if bush.ws_info.installed:
            version_info = bush.ws_info.get_installed_version()
            # Windows Store apps have to be launched entirely differently
            gm_cmd = u'shell:AppsFolder\\%s!%s' % (
                bush.ws_info.app_name, version_info.entry_point)
            subprocess.Popen([u'start', gm_cmd], shell=True)
        else:
            exe_xse = bass.dirs[u'app'].join(bush.game.Se.exe)
            exe_laa = bass.dirs[u'app'].join(bush.game.Laa.exe)
            exe_path = self.exePath # Default to the regular launcher
            if BashStatusBar.laaButton.button_state:
                # Should use the LAA Launcher if it's present
                exe_path = (exe_laa if exe_laa.isfile() else exe_path)
            elif BashStatusBar.obseButton.button_state:
                # OBSE refuses to start when its EXE is launched on a Steam
                # installation
                if (bush.game.fsName != u'Oblivion'
                        or u'steam' not in bass.dirs[u'app'].cs):
                    # Should use the xSE launcher if it's present
                    exe_path = (exe_xse if exe_xse.isfile() else exe_path)
            self._run_exe(exe_path, [exe_path.s])
        if bass.settings.get(u'bash.autoQuit.on', False):
            Link.Frame.close_win(True)

    @property
    def version(self):
        if not bass.settings[u'bash.statusbar.showversion']: return u''
        try:
            version = self._version_path.strippedVersion
            if version == (0,) and bush.ws_info.installed:
                version = get_game_version_fallback(self._version_path,
                                                    bush.ws_info)
        except OSError:
            version = get_game_version_fallback(
                self._version_path, bush.ws_info)
        if version != (0,):
            version = u'.'.join([u'%s' % x for x in version])
            return version
        return u''

    def IsPresent(self):
        if bush.ws_info.installed:
            # Always possible to run, even if the EXE is missing/inaccessible
            return True
        return super(Game_Button, self).IsPresent()

#------------------------------------------------------------------------------
class TESCS_Button(_ExeButton):
    """CS/CK button. Needs a special tooltip when OBSE is enabled."""
    def __init__(self, ck_path, ck_images, ck_tip, ck_xse_tip, ck_xse_arg,
                 ck_uid=u'TESCS'):
        super(TESCS_Button, self).__init__(
            exePath=ck_path, exeArgs=(), images=ck_images, tip=ck_tip,
            obseTip=ck_xse_tip, uid=ck_uid)
        self.xse_args = (ck_xse_arg,) if ck_xse_arg else ()

    @property
    def obseTip(self):
        # CS/CK (version)
        tip_ = self._obseTip % {u'version': self.version}
        if not self.xse_args: return tip_
        # + OBSE
        tip_ += u' + %s%s' % (bush.game.Se.se_abbrev, self.obseVersion)
        # + CSE
        cse_path = bass.dirs[u'mods'].join(u'obse', u'plugins',
                                           u'Construction Set Extender.dll')
        if cse_path.exists():
            version = cse_path.strippedVersion
            if version != (0,):
                version = u'.'.join([u'%i'%x for x in version])
            else:
                version = u''
            tip_ += u' + CSE %s' % version
        return tip_

    def _app_button_execute(self):
        exe_xse = bass.dirs[u'app'].join(bush.game.Se.exe)
        if (self.xse_args and BashStatusBar.obseButton.button_state
                and exe_xse.isfile()):
            # If the script extender for this game has CK support, the xSE
            # loader is present and xSE is enabled, use that executable and
            # pass the editor argument to it
            self._run_exe(exe_xse, [exe_xse.s] + list(self.xse_args))
        else:
            # Fall back to the standard CK executable, with no arguments
            super(TESCS_Button, self)._app_button_execute()

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
            self.gButton.image = balt.images[self.imageKey % bass.settings[
                u'bash.statusbar.iconSize']].GetBitmap()
            self.gButton.tooltip = self.sb_button_tip

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

    def GetBitmapButton(self, window, image=None, onRClick=None):
        if not self._present: return None
        self.SetState()
        return super(_StatefulButton, self).GetBitmapButton(window, image,
                                                            onRClick)

    def IsPresent(self):
        return self._present

    def Execute(self):
        """Invert state."""
        self.SetState(-1)

class Obse_Button(_StatefulButton):
    """Obse on/off state button."""
    _state_key = u'bash.obse.on'
    _state_img_key = u'checkbox.green.%s.%s'
    @property
    def _present(self):
        return (bool(bush.game.Se.se_abbrev)
                and bass.dirs[u'app'].join(bush.game.Se.exe).exists())

    def SetState(self,state=None):
        super(Obse_Button, self).SetState(state)
        if bush.game.Laa.launchesSE and not state and BashStatusBar.laaButton.gButton is not None:
            # 4GB Launcher automatically launches the SE, so turning of the SE
            # required turning off the 4GB Launcher as well
            BashStatusBar.laaButton.SetState(state)
        self.UpdateToolTips()
        return state

    @property
    def sb_button_tip(self): return ((_(u'%s%s Disabled'), _(u'%s%s Enabled'))[
        self.button_state]) % (bush.game.Se.se_abbrev, self.obseVersion)

    def UpdateToolTips(self):
        tipAttr = (u'sb_button_tip', u'obseTip')[self.button_state]
        for button in _App_Button.obseButtons:
            button.gButton.tooltip = getattr(button, tipAttr, u'')

class LAA_Button(_StatefulButton):
    """4GB Launcher on/off state button."""
    _state_key = u'bash.laa.on'
    _state_img_key = u'checkbox.blue.%s.%s'
    @property
    def _present(self):
        return bass.dirs[u'app'].join(bush.game.Laa.exe).exists()

    def SetState(self,state=None):
        super(LAA_Button, self).SetState(state)
        if bush.game.Laa.launchesSE and BashStatusBar.obseButton.gButton is not None:
            if state:
                # If the 4gb launcher launches the SE, enable the SE when enabling this
                BashStatusBar.obseButton.SetState(state)
            else:
                # We need the obse button to update the tooltips anyway
                BashStatusBar.obseButton.UpdateToolTips()
        return state

    @property
    def sb_button_tip(self): return bush.game.Laa.laa_name + (
        _(u' Disabled'), _(u' Enabled'))[self.button_state]

#------------------------------------------------------------------------------
class AutoQuit_Button(_StatefulButton):
    """Button toggling application closure when launching Oblivion."""
    _state_key = u'bash.autoQuit.on'
    _state_img_key = u'checkbox.red.%s.%s'
    _default_state = False

    @property
    def imageKey(self): return self._state_img_key % (
        [u'off', u'x'][self.button_state], u'%d')

    @property
    def sb_button_tip(self): return (_(u'Auto-Quit Disabled'), _(u'Auto-Quit Enabled'))[
        self.button_state]

#------------------------------------------------------------------------------
class App_Help(StatusBar_Button):
    """Show help browser."""
    imageKey, _tip = u'help.%s', _(u'Help File')

    def Execute(self):
        webbrowser.open(bolt.readme_url(mopy=bass.dirs[u'mopy']))

#------------------------------------------------------------------------------
class App_DocBrowser(StatusBar_Button):
    """Show doc browser."""
    imageKey, _tip = u'doc.%s', _(u'Doc Browser')

    def Execute(self):
        if not Link.Frame.docBrowser:
            DocBrowser().show_frame()
            bass.settings[u'bash.modDocs.show'] = True
        Link.Frame.docBrowser.raise_frame()

#------------------------------------------------------------------------------
class App_Settings(StatusBar_Button):
    """Show settings dialog."""
    imageKey, _tip = u'settingsbutton.%s', _(u'Settings')

    def GetBitmapButton(self, window, image=None, onRClick=None):
        return super(App_Settings, self).GetBitmapButton(
            window, image, lambda: self.Execute())

    def Execute(self):
        SettingsDialog.display_dialog()

#------------------------------------------------------------------------------
class App_Restart(StatusBar_Button):
    """Restart Wrye Bash"""
    _tip = _(u'Restart')

    def GetBitmapButton(self, window, image=None, onRClick=None):
        iconSize = bass.settings[u'bash.statusbar.iconSize']
        return super(App_Restart, self).GetBitmapButton(window,
            staticBitmap(window, special=u'undo', size=(iconSize, iconSize)),
            onRClick)

    def Execute(self): Link.Frame.Restart()

#------------------------------------------------------------------------------
class App_PluginChecker(StatusBar_Button):
    """Show plugin checker."""
    _tip = _(u'Plugin Checker')
    imageKey = u'modchecker.%s'

    def Execute(self):
        PluginChecker.create_or_raise()
