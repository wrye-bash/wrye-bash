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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
import os
import shlex
import subprocess
import webbrowser

from . import BashStatusBar
from .frames import DocBrowser, PluginChecker
from .settings_dialog import SettingsDialog
from .. import balt, bass, bolt, bosh, bush, load_order
from ..balt import BoolLink, ItemLink, Link, SeparatorLink
from ..bass import Store
from ..env import get_game_version_fallback, getJava
from ..gui import ClickableImage, EventResult, get_key_down, get_shift_down, \
    Lazy, Links, WithDragEvents, showError
##: we need to move SB_Button to gui but we are blocked by Link
from ..gui.base_components import _AComponent

__all__ = ['Obse_Button', 'AutoQuit_Button', 'Game_Button',
           'TESCS_Button', 'App_xEdit', 'App_BOSS', 'App_Help', 'App_LOOT',
           'App_DocBrowser', 'App_PluginChecker', 'App_Settings',
           'App_Restart', 'app_button_factory']

#------------------------------------------------------------------------------
# StatusBar Buttons -----------------------------------------------------------
#------------------------------------------------------------------------------
class _StatusBar_Hide(ItemLink):
    """The (single) link on the button's menu - hides the button."""
    @property
    def link_text(self):
        return _("Hide '%(status_btn_name)s'") % {
            'status_btn_name': self.window.tooltip}

    @property
    def link_help(self):
        return _("Hides %(status_btn_name)s's status bar button (can be "
                 "restored through the settings menu).") % {
            'status_btn_name': self.window.tooltip}

    def Execute(self): Link.Frame.statusBar.HideButton(self.window.uid)

class StatusBar_Button(Lazy, WithDragEvents, ClickableImage):
    """Launch an application."""
    _tip = u''
    @property
    def sb_button_tip(self): return self._tip

    def __init__(self, uid=None, canHide=True, button_tip=u''):
        """uid: Unique identifier, used for saving the order of status bar
                icons and whether they are hidden/shown.
           canHide: True if this button is allowed to be hidden."""
        super().__init__()
        self.canHide = canHide
        self.mainMenu = self._init_menu(Links())
        self._tip = button_tip or self.__class__._tip # must be set see below
        self.uid = (self.__class__.__name__, self._tip) if uid is None else uid

    def _init_menu(self, bt_links):
        if self.canHide:
            if bt_links:
                bt_links.append_link(SeparatorLink())
            bt_links.append_link(_StatusBar_Hide())
        return bt_links

    def create_widget(self, parent, recreate=True, on_drag_start=None,
                      on_drag_end=None, on_drag_end_forced=None, on_drag=None):
        """Create and return gui button."""
        created = super().create_widget(recreate=recreate, parent=parent,
            wx_bitmap=self._btn_bmp(), btn_tooltip=self.sb_button_tip,
            on_drag_start=on_drag_start, on_drag_end=on_drag_end,
            on_drag_end_forced=on_drag_end_forced, on_drag=on_drag)
        if created:
            # DnD doesn't work with the EVT_BUTTON so we call sb_click directly
            # self.on_clicked.subscribe(self.sb_click)
            self.on_right_clicked.subscribe(self.DoPopupMenu)
        return created

    @_AComponent.tooltip.setter
    def tooltip(self, new_tooltip: str):
        if self._is_created():
            _AComponent.tooltip.fset(self, new_tooltip)

    def _btn_bmp(self):
        return balt.images[self.imageKey % bass.settings[
            'bash.statusbar.iconSize']].get_bitmap()

    def DoPopupMenu(self):
        if self.mainMenu:
            self.mainMenu.popup_menu(self, 0)
            return EventResult.FINISH ##: Kept it as such, test if needed

    # Helper function to get OBSE version
    @property
    def obseVersion(self):
        if not bass.settings[u'bash.statusbar.showversion']: return u''
        for ver_file in bush.game.Se.ver_files:
            ver_path = bass.dirs[u'app'].join(ver_file)
            if ver_path.exists():
                return ' ' + '.'.join([f'{x}' for x
                                       in ver_path.strippedVersion])
        else:
            return u''

    def sb_click(self):
        """Execute an action when clicking the button."""
        raise NotImplementedError

#------------------------------------------------------------------------------
# App Links -------------------------------------------------------------------
#------------------------------------------------------------------------------
class _App_Button(StatusBar_Button):
    """Launch an application."""

    @property
    def version(self):
        if not bass.settings[u'bash.statusbar.showversion']: return u''
        if self.allow_create():
            version = self.exePath.strippedVersion
            if version != (0,):
                version = '.'.join([f'{x}' for x in version])
                return version
        return u''

    @property
    def sb_button_tip(self):
        if self._obseTip and BashStatusBar.obseButton.button_state:
            return self.obseTip
        if not bass.settings[u'bash.statusbar.showversion']: return self._tip
        else:
            return f'{self._tip} {self.version}'

    @property
    def obseTip(self):
        if self._obseTip is None: return None
        return self._obseTip % {'app_version': self.version}

    def __init__(self, exePath, exeArgs, images, tip, obse_tip=None, uid=None,
                 canHide=True):
        """images: [16x16,24x24,32x32] images"""
        super(_App_Button, self).__init__(uid, canHide, tip)
        self.exeArgs = exeArgs
        self.exePath = exePath
        self.images = images
        #--**SE stuff
        self._obseTip = obse_tip
        # used by _App_Button.sb_click: be sure to set them _before_ calling it
        self.extraArgs = ()
        self.wait = False

    def allow_create(self):
        return self.exePath != bolt.undefinedPath and self.exePath.exists()

    def _btn_bmp(self):
        iconSize = bass.settings['bash.statusbar.iconSize'] # 16, 24, 32
        idex = (iconSize // 8) - 2 # 0, 1, 2, duh
        return self.images[idex].get_bitmap()

    def ShowError(self, error=None, *, msg=None):
        if error is not None:
            msg = (f'{error}\n\n' + _('Used Path: %(launched_exe_path)s') % {
                'launched_exe_path': self.exePath} + '\n' + _(
                'Used Arguments: %(launched_exe_args)s') % {
                       'launched_exe_args': self.exeArgs})
        error_title = _("Could Not Launch '%(launched_exe_name)s'") % {
            'launched_exe_name': self.exePath.stail}
        showError(Link.Frame, msg, title=error_title)

    def _showUnicodeError(self):
        self.ShowError(msg=_('Execution failed because one or more of the '
                             'command line arguments failed to encode.'))

    def sb_click(self):
        if not self.allow_create():
            msg = _('Application missing: %(launched_exe_path)s')
            self.ShowError(msg=msg % {'launched_exe_path': self.exePath})
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
            popen = subprocess.Popen(exe_args, close_fds=True)
            if self.wait:
                with balt.Progress(_('Waiting for %(other_process)s...') % {
                    'other_process': exe_path.stail}) as progress:
                    progress(0, bolt.text_wrap(
                        _('Wrye Bash will be paused until you have completed '
                          'your work in %(other_process)s and closed '
                          'it.') % {'other_process': exe_path.stail}, 50))
                    progress.setFull(1)
                    popen.wait()
        except UnicodeError:
            self._showUnicodeError()
        except WindowsError as werr:
            if werr.winerror != 740:
                self.ShowError(werr)
            try:
                import win32api
                win32api.ShellExecute(0, 'runas', exe_path.s,
                    shlex.join(exe_args[1:]), exe_path.head.s, 1)
            except:
                self.ShowError(werr)
        except Exception as error:
            self.ShowError(error)
        finally:
            cwd.setcwd()

class _JavaButton(_App_Button):
    """_App_Button pointing to a .jar file."""
    _java = getJava()

    @property
    def version(self): return u''

    def allow_create(self):
        return self._java.exists() and super().allow_create()

    def _app_button_execute(self):
        cwd = bolt.Path.getcwd()
        self.exePath.head.setcwd()
        try:
            subprocess.Popen((self._java.stail, '-jar', self.exePath.stail,
                              ''.join(self.exeArgs)), executable=self._java.s,
                             close_fds=True)
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
                exe_Path = item[0]
            else:
                exe_Path = item
            if exe_Path.exists():
                # Use this one
                use = item
                break
        exePathArgs = use
    if isinstance(exePathArgs, tuple):
        exe_Path = exePathArgs[0]
        exeArgs = exePathArgs[1:]
    else:
        exe_Path = exePathArgs
        exeArgs = tuple()
    return exe_Path, exeArgs

def app_button_factory(exePathArgs, *args, **kwargs):
    exePath, exeArgs = _parse_button_arguments(exePathArgs)
    if exePath and exePath.cext == u'.exe': # note: sometimes exePath is None
        return _ExeButton(exePath, exeArgs, *args, **kwargs)
    if exePath and exePath.cext == u'.jar':
        return _JavaButton(exePath, exeArgs, *args, **kwargs)
    if exePath and( exePath.cext == u'.lnk' or exePath.is_dir()):
        return _LnkOrDirButton(exePath, exeArgs, *args, **kwargs)
    return _App_Button(exePath, exeArgs, *args, **kwargs)

#------------------------------------------------------------------------------
class _Mods_xEditExpert(BoolLink):
    """Toggle xEdit expert mode (when launched via Bash)."""
    _text = _('Expert Mode')
    _help = _('Launch %(xedit_name)s in expert mode.') % {
        'xedit_name': bush.game.Xe.full_name}
    _bl_key = bush.game.Xe.xe_key_prefix + '.iKnowWhatImDoing'

class _Mods_xEditSkipBSAs(BoolLink):
    """Toggle xEdit skip bsa mode (when launched via Bash)."""
    _text = _('Skip BSAs')
    _help = _('Skip loading BSAs when opening %(xedit_name)s. Will disable '
              'some of its functions.') % {
        'xedit_name': bush.game.Xe.full_name}
    _bl_key = bush.game.Xe.xe_key_prefix + '.skip_bsas'

class _AMods_xEditLaunch(ItemLink):
    """Base class for launching xEdit via link."""
    _custom_arg: str

    def __init__(self, parent_link):
        super().__init__()
        self._xedit_link = parent_link

    def Execute(self):
        self._xedit_link.launch_with_args(custom_args=(self._custom_arg,))

class _Mods_xEditQAC(_AMods_xEditLaunch):
    """Launch xEdit in QAC mode."""
    _text = _('Quick Auto Clean')
    _help = _('Launch %(xedit_name)s in QAC mode to clean a single '
              'plugin.') % {'xedit_name': bush.game.Xe.full_name}
    _custom_arg = '-qac'

class _Mods_xEditVQSC(_AMods_xEditLaunch):
    """Launch xEdit in VQSC mode."""
    _text = _('Very Quick Show Conflicts')
    _help = _('Launch %(xedit_name)s in VQSC mode to detect '
              'conflicts.') % {'xedit_name': bush.game.Xe.full_name}
    _custom_arg = '-vqsc'

class App_xEdit(_ExeButton):
    """Launch xEdit, potentially with some extra args."""
    def __init__(self, *args, **kwdargs):
        exePath, exeArgs = _parse_button_arguments(args[0])
        super().__init__(exePath, exeArgs, *args[1:], **kwdargs)

    def _init_menu(self, bt_links):
        if bush.game.Xe.xe_key_prefix:
            bt_links.append_link(_Mods_xEditExpert())
            bt_links.append_link(_Mods_xEditSkipBSAs())
            bt_links.append_link(SeparatorLink())
            bt_links.append_link(_Mods_xEditQAC(self))
            bt_links.append_link(_Mods_xEditVQSC(self))
        return super()._init_menu(bt_links)

    def allow_create(self): # FIXME(inf) What on earth is this? What's the point?? --> check C:\not\a\valid\path.exe in default.ini
        if not super().allow_create():
            testPath = bass.tooldirs[u'Tes4ViewPath']
            if testPath != bolt.undefinedPath and testPath.exists():
                self.exePath = testPath
                return True
            return False
        return True

    def sb_click(self):
        self.launch_with_args(custom_args=())

    def launch_with_args(self, custom_args: tuple[str, ...]):
        """Computes arguments based on checked links and INI settings, then
        appends the specified custom arguments only for this launch."""
        xe_prefix = bush.game.Xe.xe_key_prefix
        is_expert = xe_prefix and bass.settings[
            f'{xe_prefix}.iKnowWhatImDoing']
        skip_bsas = xe_prefix and bass.settings[f'{xe_prefix}.skip_bsas']
        extraArgs = bass.inisettings[
            'xEditCommandLineArguments'].split() if is_expert else []
        if is_expert:
            extraArgs.append('-IKnowWhatImDoing')
        if skip_bsas:
            extraArgs.append('-skipbsa')
        self.extraArgs = old_args = tuple(extraArgs)
        self.extraArgs += custom_args
        super().sb_click()
        self.extraArgs = old_args

#------------------------------------------------------------------------------
class _Mods_SuspendLockLO(BoolLink):
    """Toggle Lock Load Order disabling when launching BOSS/LOOT through WB."""
    _text = _('Suspend Lock Load Order')
    _bl_key = 'BOSS.ClearLockTimes'
    _help = _("If enabled, will temporarily disable 'Lock Load Order' "
              "when running this program through Wrye Bash.")

class _AApp_LOManager(_ExeButton):
    """Base class for load order managers like BOSS and LOOT."""
    def __init__(self, lom_path, *args, **kwargs):
        super().__init__(lom_path, (), *args, **kwargs)

    def _init_menu(self, bt_links):
        bt_links.append_link(_Mods_SuspendLockLO())
        return super()._init_menu(bt_links)

    def sb_click(self):
        self.wait = bool(bass.settings['BOSS.ClearLockTimes'])
        if self.wait:
            # Clear the saved times from before
            with load_order.Unlock():
                super().sb_click()
                # Refresh to get the new load order that the manager specified.
                # If on timestamp method scan the data dir, if not
                # loadorder.txt should have changed, refreshLoadOrder should
                # detect that
                bosh.modInfos.refresh(
                    refresh_infos=not bush.game.using_txt_file)
            # Refresh UI, so WB is made aware of the changes to load order
            Link.Frame.distribute_ui_refresh(
                ui_refresh=Store.MODS.DO() | Store.SAVES.DO())
        else:
            super().sb_click()

#------------------------------------------------------------------------------
class _Mods_BOSSLaunchGUI(BoolLink):
    """If BOSS.exe is available then boss_gui.exe should be too."""
    _text = _('Launch Using GUI')
    _bl_key = 'BOSS.UseGUI'
    _help = _("If enabled, Bash will run BOSS's GUI.")

class App_BOSS(_AApp_LOManager):
    """Runs BOSS if it's present."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.boss_path = self.exePath

    def _init_menu(self, bt_links):
        bt_links.append_link(_Mods_BOSSLaunchGUI())
        return super()._init_menu(bt_links)

    def sb_click(self):
        if bass.settings['BOSS.UseGUI']:
            self.exePath = self.boss_path.head.join('boss_gui.exe')
        else:
            self.exePath = self.boss_path
        curr_args = []
        ##: These should become right click options instead
        if get_key_down('R'):
            if get_shift_down():
                curr_args.append('-r 2') # Revert level 2 - BOSS version 1.6+
            else:
                curr_args.append('-r 1') # Revert level 1 - BOSS version 1.6+
        if get_key_down('S'):
            curr_args.append('-s') # Silent Mode - BOSS version 1.6+
        if get_key_down('C'): # Print crc calculations in BOSS log.
            curr_args.append('-c')
        if bass.tooldirs['boss'].version >= (2, 0, 0, 0):
            # After version 2.0, need to pass in the -g argument
            curr_args.append(f'-g{bush.game.boss_game_name}')
        self.extraArgs = tuple(curr_args)
        super().sb_click()

#------------------------------------------------------------------------------
class _Mods_LOOTAutoSort(BoolLink):
    _text = _('Auto-Sort')
    _bl_key = 'LOOT.AutoSort'
    _help = _('If enabled, LOOT will automatically sort the load order for '
              'the current game, then apply the result and quit.')

class App_LOOT(_AApp_LOManager):
    """Runs LOOT if it's present."""

    def _init_menu(self, bt_links):
        bt_links.append_link(_Mods_LOOTAutoSort())
        return super()._init_menu(bt_links)

    def sb_click(self):
        curr_args = [f'--game={bush.game.loot_game_name}']
        if bass.settings['LOOT.AutoSort']:
            curr_args.append('--auto-sort')
        self.extraArgs = tuple(curr_args)
        super().sb_click()

#------------------------------------------------------------------------------
class Game_Button(_ExeButton):
    """Will close app on execute if autoquit is on."""
    def __init__(self, exe_path_args, version_path, images, tip, obse_tip):
        exePath, exeArgs = _parse_button_arguments(exe_path_args)
        super(Game_Button, self).__init__(exePath, exeArgs, images=images,
            tip=tip, obse_tip=obse_tip, uid=u'Oblivion')
        self._version_path = version_path

    @property
    def sb_button_tip(self):
        if BashStatusBar.obseButton.button_state:
            return self.obseTip
        return f'{self._tip} {self.version}' if self.version else self._tip

    @property
    def obseTip(self):
        # Oblivion (version)
        tip_ = self._obseTip % {'game_name': bush.game.display_name,
                                'app_version': self.version}
        # + OBSE
        tip_ += f' + {bush.game.Se.se_abbrev}{self.obseVersion}'
        return tip_

    def _app_button_execute(self):
        if bush.ws_info.installed:
            version_info = bush.ws_info.get_installed_version()
            # Windows Store apps have to be launched entirely differently
            gm_cmd = (f'shell:AppsFolder\\{bush.ws_info.app_name}!'
                      f'{version_info.entry_point}')
            subprocess.Popen([u'start', gm_cmd], shell=True)
        else:
            exe_xse = bass.dirs[u'app'].join(bush.game.Se.exe)
            exe_path = self.exePath # Default to the regular launcher
            if BashStatusBar.obseButton.button_state:
                # OBSE refuses to start when its EXE is launched on a Steam
                # installation
                if (bush.game.fsName != u'Oblivion'
                        or u'steam' not in bass.dirs[u'app'].cs):
                    # Should use the xSE launcher if it's present
                    exe_path = (exe_xse if exe_xse.is_file() else exe_path)
            self._run_exe(exe_path, [exe_path.s])
        if bass.settings.get(u'bash.autoQuit.on', False):
            Link.Frame.exit_wb()

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
            version = '.'.join([f'{x}' for x in version])
            return version
        return u''

    def allow_create(self):
        # Always possible to run, even if the EXE is missing/inaccessible
        return bush.ws_info.installed or super().allow_create()

#------------------------------------------------------------------------------
class TESCS_Button(_ExeButton):
    """CS/CK button. Needs a special tooltip when OBSE is enabled."""
    def __init__(self, ck_path, ck_images, ck_tip, ck_xse_tip, ck_xse_arg,
                 ck_uid=u'TESCS'):
        super(TESCS_Button, self).__init__(
            exePath=ck_path, exeArgs=(), images=ck_images, tip=ck_tip,
            obse_tip=ck_xse_tip, uid=ck_uid)
        self.xse_args = (ck_xse_arg,) if ck_xse_arg else ()

    @property
    def obseTip(self):
        # CS/CK (version)
        tip_ = self._obseTip % {'ck_name': bush.game.Ck.long_name,
                                'app_version': self.version}
        if not self.xse_args: return tip_
        # + OBSE
        tip_ += f' + {bush.game.Se.se_abbrev}{self.obseVersion}'
        # + CSE
        cse_path = bass.dirs['mods'].join('obse', 'plugins',
            'Construction Set Extender.dll')
        if cse_path.exists():
            cse_version = ''
            if bass.settings['bash.statusbar.showversion']:
                cse_ver = cse_path.strippedVersion
                if cse_ver != (0,):
                    cse_version = ' ' + '.'.join([f'{x}' for x in cse_ver])
            tip_ += f' + CSE{cse_version}'
        return tip_

    def _app_button_execute(self):
        exe_xse = bass.dirs[u'app'].join(bush.game.Se.exe)
        if (self.xse_args and BashStatusBar.obseButton.button_state
                and exe_xse.is_file()):
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
    def sb_button_tip(self): raise NotImplementedError

    @property
    def button_state(self): return self.allow_create() and bass.settings.get(
        self._state_key, self._default_state)
    @button_state.setter
    def button_state(self, val):
        bass.settings[self._state_key] = val

    @property
    def imageKey(self): return self.__class__._state_img_key % (
        [u'off', u'on'][self.button_state], u'%d')

    def sb_click(self):
        """Invert state."""
        self.button_state = True ^ self.button_state
        # reset image and tooltip for the flipped state
        self.image = self._btn_bmp()
        self.tooltip = self.sb_button_tip

class Obse_Button(_StatefulButton):
    """Obse on/off state button."""
    _state_key = u'bash.obse.on'
    _state_img_key = u'checkbox.green.%s.%s'

    def allow_create(self):
        return (bool(bush.game.Se.se_abbrev)
                and bass.dirs[u'app'].join(bush.game.Se.exe).exists())

    def sb_click(self):
        super().sb_click()
        BashStatusBar.set_tooltips()

    @property
    def sb_button_tip(self):
        tip_to_fmt = (
            _('%(se_name)s%(se_ver)s Enabled') if self.button_state else
            _('%(se_name)s%(se_ver)s Disabled'))
        return tip_to_fmt % {'se_name': bush.game.Se.se_abbrev,
                             'se_ver': self.obseVersion}

#------------------------------------------------------------------------------
class AutoQuit_Button(_StatefulButton):
    """Button toggling application closure when launching Oblivion."""
    _state_key = u'bash.autoQuit.on'
    _state_img_key = u'checkbox.red.%s.%s'
    _default_state = False

    @property
    def sb_button_tip(self): return (
        _('Auto-Quit Disabled'), _('Auto-Quit Enabled'))[self.button_state]

#------------------------------------------------------------------------------
class App_Help(StatusBar_Button):
    """Show help browser."""
    imageKey, _tip = 'help.%s', _('Help')

    def sb_click(self):
        webbrowser.open(bolt.readme_url(mopy=bass.dirs[u'mopy']))

#------------------------------------------------------------------------------
class App_DocBrowser(StatusBar_Button):
    """Show doc browser."""
    imageKey = 'doc_browser.%s'
    _tip = _('Doc Browser')

    def sb_click(self):
        if not Link.Frame.docBrowser:
            DocBrowser().show_frame()
        Link.Frame.docBrowser.raise_frame()

#------------------------------------------------------------------------------
class App_Settings(StatusBar_Button):
    """Show settings dialog."""
    imageKey, _tip = 'settings_button.%s', _('Settings')

    def sb_click(self):
        SettingsDialog.display_dialog()

    def DoPopupMenu(self):
        self.sb_click()

#------------------------------------------------------------------------------
class App_Restart(StatusBar_Button):
    """Restart Wrye Bash"""
    _tip = _(u'Restart')
    imageKey = 'reload.%s'

    def sb_click(self): Link.Frame.Restart()

#------------------------------------------------------------------------------
class App_PluginChecker(StatusBar_Button):
    """Show plugin checker."""
    _tip = _(u'Plugin Checker')
    imageKey = 'plugin_checker.%s'

    def sb_click(self):
        PluginChecker.create_or_raise()
