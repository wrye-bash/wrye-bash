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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This module starts the Wrye Bash application in console mode. Basically,
it runs some initialization functions and then starts the main application
loop."""

# Imports ---------------------------------------------------------------------
from __future__ import print_function
import atexit
import codecs
import ctypes
import os
import platform
import shutil
import sys
import traceback
from ConfigParser import ConfigParser
# Local
from . import bass, bolt, env, exception, localize
# NO OTHER LOCAL IMPORTS HERE (apart from the ones above) !
basher = None # need to share it in _close_dialog_windows
bass.is_standalone = hasattr(sys, u'frozen')
_bugdump_handle = None

##: Would be nice to move balt.Resources earlier in boot to add the WB icon to
# the game select/error popups

def _early_setup(debug):
    """Executes (very) early setup by changing working directory and debug
    mode.

    :param debug: True if debug mode is enabled."""
    # ensure we are in the correct directory so relative paths will work
    # properly
    if bass.is_standalone:
        pathToProg = os.path.dirname(
            unicode(sys.executable, bolt.Path.sys_fs_enc))
    else:
        pathToProg = os.path.dirname(
            unicode(sys.argv[0], bolt.Path.sys_fs_enc))
    if pathToProg:
        os.chdir(pathToProg)
    bolt.deprintOn = debug
    # useful for understanding context of bug reports
    if debug or bass.is_standalone:
        # Standalone stdout is NUL no matter what.   Redirect it to stderr.
        # Also, setup stdout/stderr to the debug log if debug mode /
        # standalone before wxPython is up
        global _bugdump_handle
        # _bugdump_handle = io.open(os.path.join(os.getcwdu(),u'BashBugDump.log'),'w',encoding=u'utf-8')
        _bugdump_handle = codecs.getwriter(u'utf-8')(
            open(os.path.join(os.getcwdu(), u'BashBugDump.log'), u'w'))
        sys.stdout = _bugdump_handle
        sys.stderr = _bugdump_handle
    # Mark us as High DPI-aware on Windows
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(True)
    except (AttributeError, WindowsError):
        pass # Not on Windows or on Windows < 8.1

def _import_wx():
    """Import wxpython or show a tkinter error and exit if unsuccessful."""
    try:
        import wx as _wx
        # Hacky fix for loading older settings that pickled classes from
        # moved/deleted wx modules
        from wx import _core
        sys.modules[u'wx._gdi'] = _core
        # Disable image loading errors - wxPython is missing the actual flag
        # constants for some reason, so just use 0 (no flags)
        _wx.Image.SetDefaultLoadFlags(0)
    except Exception: ##: tighten this except
        but_kwargs = {u'text': u"QUIT",
                      u'fg': u'red'}  # foreground button color
        msg = u'\n'.join([dump_environment(), u'', u'Unable to load wx:',
                          traceback.format_exc(), u'Exiting.'])
        _tkinter_error_dial(msg, but_kwargs)
        sys.exit(1)

def _import_deps():
    """Import other required dependencies or show an error if they're
    missing. Must only be called after _import_wx and setup_locale."""
    deps_msg = u''
    try:
        import chardet
    except ImportError:
        deps_msg += u'- chardet\n'
    try:
        import lz4
    except ImportError:
        deps_msg += u'- python-lz4\n'
    try:
        import win32api, win32com
    except ImportError:
        # Only a dependency on Windows, so skip on other operating systems
        if os.name == u'nt':
            deps_msg += u'- pywin32\n'
    try:
        import yaml
    except ImportError:
        deps_msg += u'- PyYAML\n'
    if deps_msg:
        deps_msg += u'\n'
        if bass.is_standalone:
            # Dependencies are always present in standalone, so this probably
            # means an MSVC redist is missing
            deps_msg += _(u'This most likely means you are missing a certain '
                          u'version of the Microsoft Visual C++ '
                          u'Redistributable. Try installing some older ones.')
        else:
            deps_msg += _(u'Ensure you have installed these dependencies '
                          u'properly. Should the error still occur, check '
                          u'your installed Microsoft Visual C++ '
                          u'Redistributables and try installing some older '
                          u'ones.')
        _close_dialog_windows()
        _show_boot_popup(_(u'The following dependencies could not be located or '
                         u'failed to load:') + u'\n\n' + deps_msg)
        sys.exit(1)

#------------------------------------------------------------------------------
def assure_single_instance(instance):
    """Ascertain that only one instance of Wrye Bash is running. Must only be
    called after setup_locale and balt is imported.

    If this is the second instance running, then display an error message and
    exit. 'instance' must stay alive for the whole execution of the program.
    See: https://wxpython.org/Phoenix/docs/html/wx.SingleInstanceChecker.html

    :type instance: wx.SingleInstanceChecker"""
    if instance.IsAnotherRunning():
        import wx as _wx
        _wx.App(False)
        bolt.deprint(u'Only one instance of Wrye Bash can run. Exiting.')
        from . import balt
        balt.showOk(None, _(u'Only one instance of Wrye Bash can run.'),
                    title=u'Wrye Bash')
        sys.exit(1)

def exit_cleanup():
    from brec import MelObject, MelRecord
    bolt.deprint(u'MelRecord._missing_hits %s' % MelRecord._cache_misses)
    bolt.deprint(u'MelRecord._key_errors %s' % MelRecord._key_errors)
    bolt.deprint(u'MelObject_missing_hits %s' % MelObject._cache_misses)
    bolt.deprint(u'MelObject_key_errors %s' % MelObject._key_errors)
    # Cleanup temp installers directory
    import tempfile
    tmpDir = bolt.GPath(tempfile.tempdir)
    for file_ in tmpDir.list():
        if file_.cs.startswith(u'wryebash_'):
            file_ = tmpDir.join(file_)
            try:
                if file_.isdir():
                    file_.rmtree(safety=u'wryebash_')
                else:
                    file_.remove()
            except: ##: tighten this except
                pass
    # make sure to flush the BashBugDump.log
    if _bugdump_handle is not None:
        _bugdump_handle.close()
    if bass.is_restarting:
        cli = cmd_line = bass.sys_argv # list of cli args
        try:
            if u'--uac' in bass.sys_argv: ##: mostly untested - needs revamp
                import win32api
                if bass.is_standalone:
                    exe = cli[0]
                    cli = cli[1:]
                else:
                    exe = sys.executable
                exe = [u'%s', u'"%s"'][u' ' in exe] % exe
                cli = u' '.join([u'%s', u'"%s"'][u' ' in x] % x for x in cli)
                cmd_line = u'%s %s' % (exe, cli)
                win32api.ShellExecute(0, u'runas', exe, cli, None, True)
                return
            else:
                import subprocess
                cmd_line = ((bass.is_standalone and cli)
                            or [sys.executable] + cli)
                subprocess.Popen(cmd_line, # a list, no need to escape spaces
                                 close_fds=True)
        except Exception as error:
            print(error)
            print(u'Error Attempting to Restart Wrye Bash!')
            print(u'cmd line: %s' % (cmd_line, ))
            print()
            raise

def dump_environment():
    """Dumps information about the environment. Must only be called after
    _import_wx and _import_deps."""
    import wx as _wx
    import lz4
    import yaml
    fse = sys.getfilesystemencoding()
    msg = [
        u'Using Wrye Bash Version %s%s' % (bass.AppVersion,
            u' (Standalone)' if bass.is_standalone else u''),
        u'OS info: %s, running on %s' % (
            platform.platform(), platform.processor()),
        u'Python version: %s' % sys.version,
        u'wxPython version: %s' % _wx.version() if _wx is not None else \
            u'wxPython not found',
        u'python-lz4 version: %s; bundled LZ4 version: %s' % (
            lz4.version.version, lz4.library_version_string()),
        u'pyyaml version: %s' % yaml.__version__,
        # Standalone: stdout will actually be pointing to stderr, which has no
        # 'encoding' attribute
        u'Input encoding: %s; output encoding: %s' % (
            sys.stdin.encoding, getattr(sys.stdout, u'encoding', None)),
        u'Filesystem encoding: %s%s' % (fse,
            (u' - using %s' % bolt.Path.sys_fs_enc) if not fse else u''),
        u'Command line: %s' % sys.argv,
    ]
    if getattr(bolt, u'scandir', None) is not None:
        msg.append(u'Using scandir v%s' % bolt.scandir.__version__)
    for m in msg:
        bolt.deprint(m)
    return u'\n'.join(msg)

def _bash_ini_parser(bash_ini_path):
    bash_ini_parser = None
    if bash_ini_path is not None and os.path.exists(bash_ini_path):
        bash_ini_parser = ConfigParser()
        bash_ini_parser.read(bash_ini_path)
    return bash_ini_parser

# Main ------------------------------------------------------------------------
def main(opts):
    """Run the Wrye Bash main loop.

    :param opts: command line arguments
    :type opts: Namespace"""
    # Change working dir and logging
    _early_setup(opts.debug)
    # wx is needed to initialize locale, so that's first
    _import_wx()
    # Next, proceed to initialize the locale using wx
    wx_locale = localize.setup_locale(opts.language)
    # At this point, we can show a wx error popup, so do it all in a try
    try:
        # Initialize gui, our wrapper above wx (also balt, temp module)
        from . import gui, balt
        # Check for some non-critical dependencies (e.g. lz4) and warn if
        # they're missing
        _import_deps()
        # Early setup is done, delegate to the main init method
        _main(opts, wx_locale)
    except Exception:
        msg = u'\n'.join([
            _(u'Wrye Bash encountered an error.'),
            _(u'Please post the information below to the official thread at'),
            _(u'https://afkmods.com/index.php?/topic/4966-wrye-bash-all-games'),
            _(u'or to the Wrye Bash Discord at'),
            _(u'https://discord.gg/NwWvAFR'),
            u'',
            traceback.format_exc()
        ])
        _close_dialog_windows()
        _show_boot_popup(msg)
        sys.exit(1)

def _main(opts, wx_locale):
    """Run the Wrye Bash main loop.

    This function is marked private because it should be inside a try-except
    block. Call main() from the outside.

    :param opts: command line arguments
    :param wx_locale: The wx.Locale object that we ended up using."""
    import wx as _wx
    # barg is fine and balt/gui were initialized in main() already
    from . import barg, balt, gui
    bass.sys_argv = barg.convert_to_long_options(sys.argv)
    if opts.debug:
        dump_environment()
    # Check if there are other instances of Wrye Bash running
    instance = _wx.SingleInstanceChecker(u'Wrye Bash') # must stay alive !
    assure_single_instance(instance)
    #--Bash installation directories, set on boot, not likely to change
    from . import initialization
    initialization.init_dirs_mopy()
    # if HTML file generation was requested, just do it and quit
    if opts.genHtml is not None:
        ##: See if the encodes are actually necessary
        msg1 = _(u"generating HTML file from: '%s'") % opts.genHtml
        msg2 = _(u'done')
        try: print(msg1)
        except UnicodeError: print(msg1.encode(bolt.Path.sys_fs_enc))
        from . import belt ##: why import belt here?
        bolt.WryeText.genHtml(opts.genHtml)
        try: print(msg2)
        except UnicodeError: print(msg2.encode(bolt.Path.sys_fs_enc))
        return
    # We need the Mopy dirs to initialize restore settings instance
    bash_ini_path, restore_ = u'bash.ini', None
    # import barb, which does not import from bosh/bush
    from . import barb
    if opts.restore:
        try:
            restore_ = barb.RestoreSettings(opts.filename)
            restore_.extract_backup()
            # get the bash.ini from the backup, or None - use in _detect_game
            bash_ini_path = restore_.backup_ini_path()
        except (exception.BoltError, exception.StateError, OSError, IOError):
            bolt.deprint(u'Failed to restore backup', traceback=True)
            restore_ = None
    # The rest of backup/restore functionality depends on setting the game
    try:
        bashIni, bush_game, game_ini_path = _detect_game(opts, bash_ini_path)
        if not bush_game: return
        if restore_:
            try:
                restore_.restore_settings(bush_game.fsName,
                    bush_game.bash_root_prefix, bush_game.mods_dir)
                # we currently disallow backup and restore on the same boot
                if opts.quietquit: return
            except (exception.BoltError, OSError, IOError, shutil.Error):
                bolt.deprint(u'Failed to restore backup', traceback=True)
                restore_.restore_ini()
                # reset the game and ini - bush was already imported by
                # _detect_game -> _import_bush_and_set_game
                from . import bush
                bush.reset_bush_globals()
                bashIni, bush_game, game_ini_path = _detect_game(opts, u'bash.ini')
        ##: Break bosh-balt/gui coupling, though this doesn't actually cause
        # init problems (since we init those in main)
        from . import bosh
        bosh.initBosh(bashIni, game_ini_path)
        env.isUAC = env.testUAC(bush_game.gamePath.join(bush_game.mods_dir))
        global basher # share this instance with _close_dialog_windows
        from . import basher
    except (exception.BoltError, ImportError, OSError, IOError):
        msg = u'\n'.join([_(u'Error! Unable to start Wrye Bash.'), u'\n', _(
            u'Please ensure Wrye Bash is correctly installed.'), u'\n',
                          traceback.format_exc()])
        _close_dialog_windows()
        _show_boot_popup(msg)
        return
    atexit.register(exit_cleanup)
    basher.InitSettings()
    basher.InitLinks()
    basher.InitImages()
    #--Start application
    if opts.debug:
        if bass.is_standalone:
            # Special case for py2exe version
            app = basher.BashApp(False)
            # Regain control of stdout/stderr from wxPython - TODO(inf) needed?
            sys.stdout = _bugdump_handle
            sys.stderr = _bugdump_handle
        else:
            app = basher.BashApp(False)
    else:
        app = basher.BashApp(True)
    # Need to reference the locale object somewhere, so let's do it on the App
    app.locale = wx_locale
    if not bass.is_standalone and (
        not _rightWxVersion() or not _rightPythonVersion()): return
    if env.isUAC:
        uacRestart = opts.uac
        if not opts.noUac and not opts.uac:
            # Show a prompt asking if we should restart in Admin Mode
            message = _(
                u'Wrye Bash needs Administrator Privileges to make changes '
                u'to the %(gameName)s directory.  If you do not start Wrye '
                u'Bash with elevated privileges, you will be prompted at '
                u'each operation that requires elevated privileges.') % {
                          u'gameName': bush_game.displayName}
            uacRestart = balt.ask_uac_restart(message,
                                              title=_(u'UAC Protection'),
                                              mopy=bass.dirs[u'mopy'])
            if uacRestart: bass.update_sys_argv([u'--uac'])
        if uacRestart:
            bass.is_restarting = True
            return
    # Backup the Bash settings - we need settings being initialized to get
    # the previous version - we should read this from a file so we can move
    # backup higher up in the boot sequence.
    previous_bash_version = bass.settings[u'bash.version']
    # backup settings if app version has changed or on user request
    if opts.backup or barb.BackupSettings.new_bash_version_prompt_backup(
            balt, previous_bash_version):
        frame = None # balt.Link.Frame, not defined yet, no harm done
        base_dir = bass.settings[u'bash.backupPath'] or bass.dirs[u'modsBash']
        settings_file = (opts.backup and opts.filename) or None
        if not settings_file:
            settings_file = balt.askSave(frame,
                                         title=_(u'Backup Bash Settings'),
                                         defaultDir=base_dir,
                                         wildcard=u'*.7z',
                                         defaultFile=barb.BackupSettings.
                                         backup_filename(bush_game.fsName))
        if settings_file:
            with gui.BusyCursor():
                backup = barb.BackupSettings(settings_file, bush_game.fsName,
                    bush_game.bash_root_prefix, bush_game.mods_dir)
            try:
                with gui.BusyCursor():
                    backup.backup_settings(balt)
            except exception.StateError:
                if balt.askYes(frame, u'\n'.join([
                    _(u'There was an error while trying to backup the '
                      u'Bash settings!'),
                    _(u'If you continue, your current settings may be '
                        u'overwritten.'),
                    _(u'Do you want to quit Wrye Bash now?')]),
                                 title=_(u'Unable to create backup!')):
                    return  # Quit
    frame = app.Init() # Link.Frame is set here !
    frame.ensureDisplayed()
    frame.bind_refresh()
    app.MainLoop()

def _detect_game(opts, backup_bash_ini):
    # Read the bash.ini file either from Mopy or from the backup location
    bashIni = _bash_ini_parser(backup_bash_ini)
    # if uArg is None, then get the UserPath from the ini file
    user_path = opts.userPath or None  ##: not sure why this must be set first
    if user_path is None:
        ini_user_path = bass.get_ini_option(bashIni, u'sUserPath')
        if ini_user_path and not ini_user_path == u'.':
            user_path = ini_user_path
    if user_path:
        homedrive, homepath = os.path.splitdrive(user_path)
        os.environ[u'HOMEDRIVE'] = homedrive
        os.environ[u'HOMEPATH'] = homepath
    # Detect the game we're running for ---------------------------------------
    bush_game = _import_bush_and_set_game(opts, bashIni)
    if not bush_game:
        return None, None, None
    #--Initialize Directories to perform backup/restore operations
    #--They depend on setting the bash.ini and the game
    from . import initialization
    game_ini_path, init_warnings = initialization.init_dirs(
        bashIni, opts.personalPath, opts.localAppDataPath, bush_game)
    if init_warnings:
        warning_msg = _(u'The following (non-critical) warnings were found '
                        u'during initialization:')
        warning_msg += u'\n\n'
        warning_msg += u'\n'.join(u'- %s' % w for w in init_warnings)
        _show_boot_popup(warning_msg, is_critical=False)
    return bashIni, bush_game, game_ini_path

def _import_bush_and_set_game(opts, bashIni):
    from . import bush
    bolt.deprint(u'Searching for game to manage:')
    game_icons = bush.detect_and_set_game(opts.oblivionPath, bashIni)
    if game_icons is not None:  # None == success
        if len(game_icons) == 0:
            msgtext = _(u'Wrye Bash could not find a game to manage. Please '
                        u'use the -o command line argument to specify the '
                        u'game path.')
        else:
            msgtext = (_(u'Wrye Bash could not determine which game to '
                         u'manage. The following games have been detected, '
                         u'please select one to manage.') + u'\n\n' +
                       _(u'To prevent this message in the future, use the -o '
                         u'command line argument or the bash.ini to specify '
                         u'the game path.'))
        retCode = _select_game_popup(game_icons, bolt.text_wrap(msgtext, 65))
        if retCode is None:
            bolt.deprint(u'No games were found or selected. Aborting.')
            return None
        # Add the game to the command line, so we use it if we restart
        bass.update_sys_argv([u'--oblivionPath', bush.game_path(retCode).s])
        bush.detect_and_set_game(opts.oblivionPath, bashIni, retCode)
    return bush.game

def _show_boot_popup(msg, is_critical=True):
    """Shows an error message in a popup window. If is_critical, exit the
    application afterwards. Must only be called after _import_wx, setup_locale
    and gui is imported."""
    try:
        import wx as _wx
        from .gui import CancelButton, Color, LayoutOptions, \
            StartupDialog, TextArea, VLayout, CENTER
        class MessageBox(StartupDialog):
            def __init__(self, msg):
                popup_title = (_(u'Wrye Bash Error') if is_critical else
                               _(u'Wrye Bash Warning'))
                ##: Resizing is just discarded, maybe we could save it in
                # an early-boot file (see also #26)
                super(MessageBox, self).__init__(title=popup_title,
                                                 sizes_dict={})
                self.component_size = (400, 300)
                msg_text = TextArea(self, editable=False, no_border=True,
                                    init_text=msg, auto_tooltip=False)
                msg_text.set_background_color(Color(240, 240, 240))
                VLayout(item_border=5, items=[
                    (msg_text, LayoutOptions(expand=True, weight=1)),
                    (CancelButton(self, btn_label=_(u'Quit') if is_critical
                                                 else _(u'OK')),
                     LayoutOptions(h_align=CENTER)),
                ]).apply_to(self)
        print(msg) # Print msg into error log.
        _app = _wx.App(False)
        _app.locale = _wx.Locale(_wx.LANGUAGE_DEFAULT)
        MessageBox.display_dialog(msg)
        if is_critical: _wx.Exit()
    except Exception: ##: tighten these excepts?
        # Instantiating wx.App failed, fallback to tkinter.
        but_kwargs = {u'text': u'QUIT' if is_critical else u'OK',
                      u'fg': u'red'}  # foreground button color
        _tkinter_error_dial(msg, but_kwargs)

def _tkinter_error_dial(msg, but_kwargs):
    import Tkinter as tkinter  # PY3
    root_widget = tkinter.Tk()
    frame = tkinter.Frame(root_widget)
    frame.pack()
    button = tkinter.Button(frame, command=root_widget.destroy, pady=15,
                            borderwidth=5, relief=tkinter.GROOVE, **but_kwargs)
    button.pack(fill=tkinter.BOTH, expand=1, side=tkinter.BOTTOM)
    w = tkinter.Text(frame)
    w.insert(tkinter.END, msg)
    w.config(state=tkinter.DISABLED)
    w.pack()
    root_widget.mainloop()

def _close_dialog_windows():
    """Close any additional windows opened by wrye bash (e.g Splash, Dialogs).
    Must only be called after _import_wx.

    This will not close the main bash window (BashFrame) because closing that
    results in virtual function call exceptions."""
    import wx as _wx
    for window in _wx.GetTopLevelWindows():
        if basher is None or not isinstance(window, basher.BashFrame):
            if isinstance(window, _wx.Dialog):
                window.Destroy()
            window.Close()

class _AppReturnCode(object):
    def __init__(self): self.value = None
    def get(self): return self.value
    def set(self, value): self.value = value

def _select_game_popup(game_icons, msgtext):
    import wx as _wx
    from .gui import CancelImageButton, ImageButton, Label, ScrollableWindow, \
        TextAlignment, WindowFrame, VLayout
    class GameSelect(WindowFrame):
        def __init__(self, game_icons, callback):
            super(GameSelect, self).__init__(None, u'Wrye Bash')
            self.callback = callback
            # Setup the size - we give each button 38 pixels, 32 for the image
            # plus 6 for the borders. However, we limit the total size of the
            # display list at 600 pixels, where the scrollbar takes over
            self.set_min_size(420, 200)
            self.component_size = (420, min(600, 200 + len(game_icons) * 38))
            # Construct the window and add the static text
            scrl_win = ScrollableWindow(self)
            layout = VLayout(item_border=3, item_expand=True, items=[
                Label(scrl_win, msgtext, alignment=TextAlignment.CENTER),
            ])
            # Add the game buttons to the window
            for game_name, game_icon in sorted(game_icons.iteritems(),
                                               key=lambda k: k[0].lower()):
                layout.add(ImageButton(scrl_win, _wx.Bitmap(game_icon),
                                       btn_label=game_name))
            # Finally, append the 'Quit' button
            layout.add(CancelImageButton(scrl_win, btn_label=_(u'Quit')))
            layout.apply_to(scrl_win)
            # TODO(inf) de-wx! Probably best to rewrite this entirely
            self._native_widget.Bind(_wx.EVT_BUTTON, self.OnButton)

        def OnButton(self, event):
            if event.GetId() != _wx.ID_CANCEL:
                self.callback(self._native_widget.FindWindowById(
                    event.GetId()).GetLabel())
            self.close_win(True)
    _app = _wx.App(False)
    _app.locale = _wx.Locale(_wx.LANGUAGE_DEFAULT)
    retCode = _AppReturnCode()
    frame = GameSelect(game_icons, retCode.set)
    frame.show_frame()
    frame._native_widget.Center() # TODO(inf) de-wx!
    _app.MainLoop()
    del _app
    return retCode.get()

# Version checks --------------------------------------------------------------
def _rightWxVersion():
    """Shows a warning if the wrong wxPython version is installed. Must only be
    called after _import_wx, setup_locale and balt is imported."""
    import wx as _wx
    wxver = _wx.version()
    if not wxver.startswith(u'4.1'):
        from . import balt
        return balt.askYes(
            None, _(u'Warning: you appear to be using a non-supported version '
                    u'of wxPython (%s). This will cause problems! It is '
                    u'highly recommended you use a 4.1.x version. Do you '
                    u'still want to run Wrye Bash?') % wxver,
                    _(u'Warning: Non-Supported wxPython detected'))
    return True

def _rightPythonVersion():
    """Shows an error if the wrong Python version is installed. Must only be
    called after _import_wx, setup_locale and balt is imported."""
    sysVersion = sys.version_info[:3]
    if sysVersion < (2, 7) or sysVersion >= (3,):
        from . import balt
        balt.showError(
            None, _(u'Only Python 2.7 and newer is supported (%s.%s.%s '
                    u"detected). If you know what you're doing, install the "
                    u'Python version of Wrye Bash and edit this warning out. '
                    u'Wrye Bash will now exit.') % sysVersion,
            title=_(u'Incompatible Python version detected'))
        return False
    return True
