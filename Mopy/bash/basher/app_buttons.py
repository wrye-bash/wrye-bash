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
import shlex
import subprocess
import webbrowser

from .frames import DocBrowser, PluginChecker
from .settings_dialog import SettingsDialog
from .. import balt, bass, bolt, bosh, bush, load_order
from ..balt import BoolLink, ItemLink, Link, SeparatorLink, BashStatusBar
from ..bass import Store
from ..bolt import GPath, undefinedPath
from ..env import getJava, get_file_version, AppLauncher, get_registry_path, \
    ExeLauncher, LnkLauncher, set_cwd
from ..gui import ClickableImage, EventResult, get_key_down, get_shift_down, \
    Lazy, Links, WithDragEvents, get_image, showError
##: we need to move SB_Button to gui but we are blocked by Link
from ..gui.base_components import _AComponent

__all__ = ['ObseButton', 'AutoQuitButton', 'GameButton', 'TESCSButton',
           'AppXEdit', 'AppBOSS', 'HelpButton', 'AppLOOT', 'DocBrowserButton',
           'PluginCheckerButton', 'SettingsButton', 'RestartButton',
           'AppButton', 'LnkButton']

#------------------------------------------------------------------------------
# StatusBar Buttons -----------------------------------------------------------
#------------------------------------------------------------------------------
def _strip_version(exe_path=None, ver_tuple=()):
    """File version with leading and trailing zeros stripped - if
    bash.statusbar.showversion is True."""
    if not bass.settings['bash.statusbar.showversion']: return ''
    try:
        version = list(ver_tuple or get_file_version(exe_path.s))
        while version and version[0] == 0:
            version.pop(0)
        while version and version[-1] == 0:
            version.pop()
        return '.'.join([f'{x}' for x in version])
    except OSError:
        return ''

class StatusBarButton(Lazy, WithDragEvents, ClickableImage):
    """Launch an application."""
    _tip = u''
    imageKey = '' ##: this must be set - ideally provide an env dependent fallback

    def __init__(self, uid: str, canHide=True, button_tip=''):
        """uid: Unique identifier, used for saving the order of status bar
                icons and whether they are hidden/shown.
           canHide: True if this button is allowed to be hidden."""
        super().__init__()
        self.canHide = canHide
        self.mainMenu = self._init_menu(Links())
        # the _tip must be set and be as unique as uid - see SettingsDialog
        self._tip = button_tip or self.__class__._tip or uid
        self.uid = uid

    # we always need to pass a parent to those
    # noinspection PyMethodOverriding
    def native_init(self, parent, recreate=True, on_drag_start=None,
                    on_drag_end=None, on_drag_end_forced=None, on_drag=None):
        """Create and return gui button."""
        created = super().native_init(recreate=recreate, parent=parent,
            on_drag_start=on_drag_start, on_drag_end=on_drag_end,
            on_drag_end_forced=on_drag_end_forced, on_drag=on_drag)
        if created:
            self._set_img_and_tip()
            # DnD doesn't work with the EVT_BUTTON so we call sb_click directly
            # self.on_clicked.subscribe(self.sb_click)
            self.on_right_clicked.subscribe(self.DoPopupMenu)
        elif self._is_created(): # we are called from UnhideButton
            self.tooltip = self.sb_button_tip # reset the tooltip just in case
        return created

    @property
    def sb_button_tip(self): return self._tip

    def _init_menu(self, bt_links):
        if self.canHide:
            if bt_links:
                bt_links.append_link(SeparatorLink())
            bt_links.append_link(_StatusBar_Hide())
        return bt_links

    def _set_img_and_tip(self):
        # make sure allow_create is True when using this (for instance
        # exePath must exist to query version)
        self.tooltip = self.sb_button_tip
        self._set_button_image(self._btn_bmp())

    @_AComponent.tooltip.setter
    def tooltip(self, new_tooltip: str):
        if self._is_created():
            _AComponent.tooltip.fset(self, new_tooltip)

    def _btn_bmp(self):
        icon_size_ = BashStatusBar.icon_size - 8 or bass.settings[
            'bash.statusbar.iconSize']
        return get_image(self.imageKey % icon_size_)

    def DoPopupMenu(self):
        if self.mainMenu:
            self.mainMenu.popup_menu(self, 0)
            return EventResult.FINISH ##: Kept it as such, test if needed

    # Helper function to get OBSE version
    @property
    def obseVersion(self):
        for ver_file in bush.game.Se.ver_files:
            ver_path = bass.dirs[u'app'].join(ver_file)
            if ver := _strip_version(ver_path):
                return f' {ver}'
        return ''

    def sb_click(self):
        """Execute an action when clicking the button."""
        raise NotImplementedError

class _StatusBar_Hide(ItemLink):
    """The (single) link on the button's menu - hides the button."""
    window: StatusBarButton

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

#------------------------------------------------------------------------------
# App Links -------------------------------------------------------------------
#------------------------------------------------------------------------------
class AppButton(AppLauncher, StatusBarButton):
    """Launch an application."""
    _obseTip = None

    def __init__(self, exePath, images, tip, uid, cli_args=(), canHide=True,
                 display_launcher=True):
        """images: [16x16,24x24,32x32] images"""
        super().__init__(exePath, cli_args, display_launcher, uid, canHide, tip)
        self.images = images
        # used by _App_Button.sb_click: be sure to set them _before_ calling it
        self.extraArgs = ()
        self.wait = False

    def _btn_bmp(self):
        iconSize = BashStatusBar.icon_size - 8 or bass.settings[ # 16, 24, 32
            'bash.statusbar.iconSize']
        return self.images[(iconSize // 8) - 2]  # 0, 1, 2

    @property
    def sb_button_tip(self):
        if (obse_tip := self._obseTip) and BashStatusBar.obseButton.button_state:
            return obse_tip
        return f'{self._tip} {app_ver}' if (
            app_ver := self._app_version) else self._tip

    @property
    def _app_version(self):
        return _strip_version(self.exePath)

    def sb_click(self):
        exeargs = [*self._exe_args, *self.extraArgs]
        Link.Frame.set_status_info(shlex.join([self.exePath.s, *exeargs]))
        try:
            self.launch_app(self.exePath, exeargs)
            return
        except UnicodeError:
            msg = _('Execution failed because one or more of the '
                    'command line arguments failed to encode.')
        except Exception as error:
            msg = (f'{error}\n\n' + _('Used Path: %(launched_exe_path)s') % {
                'launched_exe_path': self.exePath} + '\n' + _(
                'Used Arguments: %(launched_exe_args)s') % {
                       'launched_exe_args': shlex.join(exeargs)})
        error_title = _("Could Not Launch '%(launched_exe_name)s'") % {
            'launched_exe_name': self.exePath.stail}
        showError(Link.Frame, msg, title=error_title)

    @classmethod
    def app_button_factory(cls, app_key, app_launcher, path_kwargs, *args,
                           **kwargs):
        if kwargs.setdefault('display_launcher', True):
            exe_path, is_present = cls.find_launcher(app_launcher, app_key,
                                                     **path_kwargs)
            # App_Button is initialized once on boot, if the path doesn't exist
            # at this time then it will be detected on next launch of Bash
            kwargs['display_launcher'] &= is_present
        else: exe_path = undefinedPath # don't bother figuring that out
        if cls is not AppButton:
            return cls(exe_path, *args, **kwargs)
        if exe_path.cext == '.exe':
            return _ExeButton(exe_path, *args, **kwargs)
        if exe_path.cext == '.jar':
            return _JavaButton(exe_path, *args, **kwargs)
        if exe_path.cext == '.lnk':
            return LnkButton(exe_path, *args, **kwargs)
        if exe_path.is_dir():
            return _DirButton(exe_path, *args, **kwargs)
        return cls(exe_path, *args, **kwargs)

class _ExeButton(ExeLauncher, AppButton):

    def _run_exe(self, exe_path, exe_args):
        popen = subprocess.Popen([exe_path.s, *exe_args], close_fds=True)
        if self.wait:
            with balt.Progress(_('Waiting for %(other_process)s...') % {
                    'other_process': exe_path.stail}) as progress:
                progress(0, bolt.text_wrap(
                    _('Wrye Bash will be paused until you have completed '
                      'your work in %(other_process)s and closed '
                      'it.') % {'other_process': exe_path.stail}, 50))
                progress.setFull(1)
                popen.wait()

class _JavaButton(AppButton):
    """_App_Button pointing to a .jar file."""
    _java = getJava()

    @property
    def _app_version(self): return ''

    def allow_create(self):
        return self._java.exists() and super().allow_create()

    @set_cwd
    def launch_app(self, exe_path, exe_args):
        subprocess.Popen((self._java.stail, '-jar', exe_path.stail,
            shlex.join(exe_args)), executable=self._java.s, close_fds=True)

class LnkButton(LnkLauncher, AppButton): pass

class _DirButton(AppButton):

    def sb_click(self): webbrowser.open(self.exePath.s)

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
        self._xedit_link.sb_click(custom_args=(self._custom_arg,))

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

class AppXEdit(_ExeButton):
    """Launch xEdit, potentially with some extra args."""

    def _init_menu(self, bt_links):
        if bush.game.Xe.xe_key_prefix:
            bt_links.append_link(_Mods_xEditExpert())
            bt_links.append_link(_Mods_xEditSkipBSAs())
            bt_links.append_link(SeparatorLink())
            bt_links.append_link(_Mods_xEditQAC(self))
            bt_links.append_link(_Mods_xEditVQSC(self))
        return super()._init_menu(bt_links)

    def sb_click(self, *, custom_args: tuple[str, ...] = ()):
        """Computes arguments based on checked links and INI settings, then
        appends the specified custom arguments only for this launch."""
        xe_prefix = bush.game.Xe.xe_key_prefix
        is_expert = xe_prefix and bass.settings[
            f'{xe_prefix}.iKnowWhatImDoing']
        skip_bsas = xe_prefix and bass.settings[f'{xe_prefix}.skip_bsas']
        extra_args = [*shlex.split(bass.inisettings[
            'xEditCommandLineArguments'], posix=False), '-IKnowWhatImDoing'] \
            if is_expert else []
        if skip_bsas:
            extra_args.append('-skipbsa')
        self.extraArgs = (*extra_args, *custom_args)
        super().sb_click()

#------------------------------------------------------------------------------
class _Mods_SuspendLockLO(BoolLink):
    """Toggle Lock Load Order disabling when launching BOSS/LOOT through WB."""
    _text = _('Suspend Lock Load Order')
    _bl_key = 'BOSS.ClearLockTimes'
    _help = _("If enabled, will temporarily disable 'Lock Load Order' "
              "when running this program through Wrye Bash.")

class _AAppLOManager(_ExeButton):
    """Base class for load order managers like BOSS and LOOT."""
    _registry_keys = () # find the path for those in the registry

    @classmethod
    def find_launcher(cls, app_exe, *args, **kwargs):
        # Check game folder for a copy first
        launcher, is_present = super().find_launcher(app_exe, root_dirs='app',
                                                     *args, **kwargs)
        if not is_present:
            # Detect globally installed program (into Program Files)
            path_in_registry = get_registry_path(*cls._registry_keys,
                lambda p: p.join(app_exe).is_file())
            if path_in_registry:
                return path_in_registry.join(app_exe), True
        return launcher, is_present

    def _init_menu(self, bt_links):
        bt_links.append_link(_Mods_SuspendLockLO())
        return super()._init_menu(bt_links)

    def sb_click(self):
        self.wait = bool(bass.settings['BOSS.ClearLockTimes'])
        super().sb_click()
        if self.wait:
            # Refresh to get the new load order that the manager specified. If
            # on timestamp method scan the data dir, if not loadorder.txt
            # should have changed, refreshLoadOrder should detect that
            bosh.modInfos.refresh(refresh_infos=not bush.game.using_txt_file,
                                  unlock_lo=True)
            # Refresh UI, so WB is made aware of the changes to load order
            Link.Frame.distribute_ui_refresh(
                ui_refresh=Store.MODS.DO() | Store.SAVES.DO())

#------------------------------------------------------------------------------
class _Mods_BOSSLaunchGUI(BoolLink):
    """If BOSS.exe is available then boss_gui.exe should be too."""
    _text = _('Launch Using GUI')
    _bl_key = 'BOSS.UseGUI'
    _help = _("If enabled, Bash will run BOSS's GUI.")

class AppBOSS(_AAppLOManager):
    """Runs BOSS if it's present."""
    _registry_keys = ('Boss', 'Installed Path')

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
        if get_file_version(self.boss_path.s) >= (2, 0, 0, 0):
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

class AppLOOT(_AAppLOManager):
    """Runs LOOT if it's present."""
    _registry_keys = ('LOOT', 'Installed Path')

    def _init_menu(self, bt_links):
        bt_links.append_link(_Mods_LOOTAutoSort())
        return super()._init_menu(bt_links)

    # Run LOOT on linux - if we get more launchers like this we'll need a class
    def sb_click(self):
        curr_args = [f'--game={bush.game.loot_game_name}']
        if bass.settings['LOOT.AutoSort']:
            curr_args.append('--auto-sort')
        self.extraArgs = tuple(curr_args)
        super().sb_click()

    def allow_create(self): # runs on linux too
        return self._display_launcher

    @classmethod
    def find_launcher(cls, *args, **kwargs):
        if bolt.os_name == 'nt':
            return super().find_launcher(*args, **kwargs)
        return (p := GPath('/opt/loot/LOOT')), p.exists()

#------------------------------------------------------------------------------
class GameButton(_ExeButton):
    """Will close app on execute if autoquit is on."""
    _obseTip = _('Launch %(game_name)s %(app_version)s')

    def __init__(self, images):
        super().__init__(bass.dirs['app'].join(bush.game.launch_exe), images,
            _('Launch %(game_name)s') % {'game_name': bush.game.display_name},
            'Oblivion') # the uid
        self._obseTip = self._obseTip % {
            'game_name': bush.game.display_name,
            'app_version': self._app_version
        } + f' + {bush.game.Se.se_abbrev}{self.obseVersion}'

    def sb_click(self):
        if bush.ws_info.installed:
            version_info = bush.ws_info.get_installed_version()
            # Windows Store apps have to be launched entirely differently
            gm_cmd = (f'shell:AppsFolder\\{bush.ws_info.app_name}!'
                      f'{version_info.entry_point}')
            subprocess.Popen([u'start', gm_cmd], shell=True)
        else:
            old = self.exePath # Default to the regular launcher
            if BashStatusBar.obseButton.button_state:
                exe_xse = bush.game.Se.exe_path_sc()
                # Should use the xSE launcher if it's present
                self.exePath = old if exe_xse is None else exe_xse
            try:
                super().sb_click()
            finally:
                self.exePath = old
        if bass.settings.get(u'bash.autoQuit.on', False):
            Link.Frame.exit_wb()

    @property
    def _app_version(self):
        if not bass.settings['bash.statusbar.showversion']:
            return '' # check first to avoid the syscall
        return _strip_version(ver_tuple=(bush.game_version()))

    def allow_create(self):
        # Always possible to run, even if the EXE is missing/inaccessible
        return bush.ws_info.installed or super().allow_create()

#------------------------------------------------------------------------------
class TESCSButton(_ExeButton):
    """CS/CK button. Needs a special tooltip when OBSE is enabled."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, cli_args=bush.game.Ck.se_args, **kwargs)
        self._obseTip = _('Launch %(ck_name)s %(app_version)s') % {
            'ck_name': bush.game.Ck.long_name, 'app_version': self._app_version
        }
        if self._exe_args: # + OBSE
            self._obseTip += f' + {bush.game.Se.se_abbrev}{self.obseVersion}'
            # + CSE
            cse_path = bass.dirs['mods'].join('obse', 'plugins',
                'Construction Set Extender.dll')
            cse_version = f' {cse_ver}' if (
                cse_ver := _strip_version(cse_path)) else ''
            self._obseTip += f' + CSE{cse_version}'

    def sb_click(self):
        old = self.exePath
        if (self._exe_args and BashStatusBar.obseButton.button_state and (
                ##: does this work for Oblivion or use exe_path_sc here
                exe_xse := bass.dirs['app'].join(bush.game.Se.exe)).is_file()):
            # If the script extender for this game has CK support, the xSE
            # loader is present and xSE is enabled, use that executable and
            # pass the editor argument to it
            self.exePath = exe_xse
        try:
            super().sb_click()
        finally:
            self.exePath = old

#------------------------------------------------------------------------------
class _StatefulButton(StatusBarButton):
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
        self._set_img_and_tip()

class ObseButton(_StatefulButton):
    """Obse on/off state button."""
    _state_key = u'bash.obse.on'
    _state_img_key = u'checkbox.green.%s.%s'

    def allow_create(self):
        return (bool(bush.game.Se.se_abbrev)
                and bass.dirs['app'].join(bush.game.Se.exe).is_file())

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
class AutoQuitButton(_StatefulButton):
    """Button toggling application closure when launching Oblivion."""
    _state_key = u'bash.autoQuit.on'
    _state_img_key = u'checkbox.red.%s.%s'
    _default_state = False

    @property
    def sb_button_tip(self): return (
        _('Auto-Quit Disabled'), _('Auto-Quit Enabled'))[self.button_state]

#------------------------------------------------------------------------------
class HelpButton(StatusBarButton):
    """Show help browser."""
    imageKey, _tip = 'help.%s', _('Help')

    def sb_click(self):
        webbrowser.open(bolt.readme_url(mopy=bass.dirs[u'mopy']))

#------------------------------------------------------------------------------
class DocBrowserButton(StatusBarButton):
    """Show doc browser."""
    imageKey = 'doc_browser.%s'
    _tip = _('Doc Browser')

    def sb_click(self):
        if not Link.Frame.docBrowser:
            DocBrowser().show_frame()
        Link.Frame.docBrowser.raise_frame()

#------------------------------------------------------------------------------
class SettingsButton(StatusBarButton):
    """Show settings dialog."""
    imageKey, _tip = 'settings_button.%s', _('Settings')

    def sb_click(self):
        SettingsDialog.display_dialog()

    def DoPopupMenu(self):
        self.sb_click()

#------------------------------------------------------------------------------
class RestartButton(StatusBarButton):
    """Restart Wrye Bash"""
    _tip = _(u'Restart')
    imageKey = 'reload.%s'

    def allow_create(self): return bass.inisettings['ShowDevTools']

    def sb_click(self): Link.Frame.Restart()

#------------------------------------------------------------------------------
class PluginCheckerButton(StatusBarButton):
    """Show plugin checker."""
    _tip = _(u'Plugin Checker')
    imageKey = 'plugin_checker.%s'

    def sb_click(self):
        PluginChecker.create_or_raise()
