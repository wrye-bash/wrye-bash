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

"""This module starts the Wrye Bash application in console mode. Basically,
it runs some initialization functions and then starts the main application
loop."""

# Imports ---------------------------------------------------------------------

import atexit
import locale
import os
import platform
import shutil
import sys
import traceback
from configparser import ConfigParser
# Local
from . import bass, bolt, exception
# NO OTHER LOCAL IMPORTS HERE (apart from the ones above) !
basher = None # need to share it in _close_dialog_windows
bass.is_standalone = hasattr(sys, u'frozen')
_bugdump_handle = None
# The one and only wx
_wx = None

def _early_setup(debug):
    """Executes (very) early setup by changing working directory and debug
    mode.

    :param debug: True if debug mode is enabled."""
    # ensure we are in the correct directory so relative paths will work
    # properly
    if bass.is_standalone:
        pathToProg = os.path.dirname(sys.executable)
    else:
        pathToProg = os.path.dirname(sys.argv[0])
    if pathToProg:
        os.chdir(pathToProg)
    bolt.deprintOn = debug
    # useful for understanding context of bug reports
    if debug or bass.is_standalone:
        # Standalone stdout is NUL no matter what.   Redirect it to stderr.
        # Also, setup stdout/stderr to the debug log if debug mode /
        # standalone before wxPython is up
        global _bugdump_handle
        _bugdump_handle = open(
            os.path.join(os.getcwd(), u'BashBugDump.log'), u'w', buffering=1,
            encoding=u'utf-8')
        sys.stdout = _bugdump_handle
        sys.stderr = _bugdump_handle

# Wx --------------------------------------------------------------------------
# locale/image calls in wx work once an App object is instantiated and in scope
bash_app = None  ##: typing
def _import_wx(debug):
    """Import wxpython or show a tkinter error and exit if unsuccessful."""
    try:
        global _wx
        import wx as _wx
        # Hacky fix for loading older settings that pickled classes from
        # moved/deleted wx modules
        from wx import _core
        sys.modules[u'wx._gdi'] = _core
        # Hack see: https://discuss.wxpython.org/t/wxpython4-1-1-python3-8-locale-wxassertionerror/35168/3
        class _LocaleApp(_wx.App):
            def InitLocale(self):
                if sys.platform.startswith('win') and sys.version_info > (3,8):
                    locale.setlocale(locale.LC_ALL, 'C')
            def MainLoop(self, restore_stdio=True):
                """Not sure what RestoreStdio does so I omit the call in game
                selection dialog.""" # TODO: check standalone also
                rv = _wx.PyApp.MainLoop(self)
                if restore_stdio: self.RestoreStdio()
                return rv
        # Initialize the App instance once
        global bash_app
        bash_app = _LocaleApp(not debug) # redirect std out
        # Disable image loading errors - wxPython is missing the actual flag
        # constants for some reason, so just use 0 (no flags)
        _wx.Image.SetDefaultLoadFlags(0)
        return _wx.version()
    except Exception: ##: tighten this except
        but_kwargs = {u'text': u"QUIT",
                      u'fg': u'red'}  # foreground button color
        msg = u'\n'.join([dump_environment(), u'', u'Unable to load wx:',
                          traceback.format_exc(), u'Exiting.'])
        _tkinter_error_dial(msg, but_kwargs)

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
                          u'Redistributable. Try installing the 2010 x64 '
                          u'version.')
        else:
            deps_msg += _(u'Ensure you have installed these dependencies '
                          u'properly. Should the error still occur, check '
                          u'your installed Microsoft Visual C++ '
                          u'Redistributables and try installing the 2010 x64 '
                          u'version.')
        _show_boot_popup(_(u'The following dependencies could not be located '
                           u'or failed to load:') + u'\n\n' + deps_msg)

#------------------------------------------------------------------------------
def assure_single_instance(instance):
    """Ascertain that only one instance of Wrye Bash is running. Must only be
    called after setup_locale and balt is imported.

    If this is the second instance running, then display an error message and
    exit. 'instance' must stay alive for the whole execution of the program.
    See: https://wxpython.org/Phoenix/docs/html/wx.SingleInstanceChecker.html

    :type instance: wx.SingleInstanceChecker"""
    if instance.IsAnotherRunning():
        bolt.deprint(u'Only one instance of Wrye Bash can run. Exiting.')
        from . import balt
        balt.showOk(None, _(u'Only one instance of Wrye Bash can run.'),
                    title=u'Wrye Bash')
        sys.exit(1)

def exit_cleanup():
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
                cmd_line = f'{exe} {cli}'
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
            print(f'cmd line: {cmd_line}')
            print()
            raise

def dump_environment(wxver=None):
    """Dumps information about the environment. Must only be called after
    _import_wx and _import_deps."""
    # Note that we can't dump pywin32 because it doesn't contain a version
    # field in its modules
    import chardet, lz4, yaml
    try:
        import fitz
        pymupdf_ver = (f'{fitz.VersionBind}; bundled MuPDF version: '
                       f'{fitz.VersionFitz}')
    except ImportError:
        pymupdf_ver = 'not found'
    wx_ver = wxver or 'not found'
    # Now that we have checked all dependencies (including potentially missing
    # ones), we can build the environment dump
    fse = bolt.Path.sys_fs_enc
    msg = [
        f'Using Wrye Bash Version {bass.AppVersion}'
        f'{u" (Standalone)" if bass.is_standalone else u""}',
        f'OS info: {platform.platform()}, running on '
        f'{platform.processor() or u"<unknown>"}',
        f'Python version: {sys.version}',
        'Dependency versions:',
        f' - chardet: {chardet.__version__}',
        f' - PyMuPDF: {pymupdf_ver}',
        f' - python-lz4: {lz4.version.version}; bundled LZ4 version: '
        f'{lz4.library_version_string()}',
        f' - PyYAML: {yaml.__version__}',
        f' - wxPython: {wx_ver}',
        # Standalone: stdout will actually be pointing to stderr, which has no
        # 'encoding' attribute and stdin will be None
        f'Input encoding: {sys.stdin.encoding if sys.stdin else None}; '
        f'output encoding: {getattr(sys.stdout, u"encoding", None)}',
        f'Filesystem encoding: {fse}'
        f'{(u" - using %s" % bolt.Path.sys_fs_enc) if not fse else u""}',
        f'Command line: {sys.argv}',
    ]
    for m in msg:
        bolt.deprint(m)
    return u'\n'.join(msg)

def _bash_ini_parser(bash_ini_path):
    bash_ini_parser = None
    if bash_ini_path is not None and os.path.exists(bash_ini_path):
        bash_ini_parser = ConfigParser()
        # bash.ini is always compatible with UTF-8 (Russian INI is UTF-8,
        # English INI is ASCII)
        bash_ini_parser.read(bash_ini_path, encoding='utf-8')
    return bash_ini_parser

# Main ------------------------------------------------------------------------
def main(opts):
    """Run the Wrye Bash main loop.

    :param opts: command line arguments
    :type opts: Namespace"""
    # Change working dir and logging
    _early_setup(opts.debug)
    # wx is needed to initialize locale, so that's first
    wxver = _import_wx(opts.debug)
    try:
        # Next, initialize locale so that we can show a translated error
        # message if WB crashes
        from . import localize
        wx_locale = localize.setup_locale(opts.language, _wx)
        if not bass.is_standalone and (not _rightWxVersion(wxver) or
                                       not _rightPythonVersion()): return
        # Both of these must come early, before we begin showing wx-based GUI
        from . import env
        env.mark_high_dpi_aware()
        env.fixup_taskbar_icon()
        # The rest of boot relies on Mopy-based directories being set, so those
        # come next
        from . import initialization
        initialization.init_dirs_mopy()
        # Early setup is done, delegate to the main init method
        _main(opts, wx_locale, wxver)
    except Exception:
        caught_exc = traceback.format_exc()
        try:
            # Check if localize succeeded in setting up translations, otherwise
            # monkey patch in a noop underscore
            # noinspection PyUnboundLocalVariable
            _(u'')
        except NameError:
            def _(x): return x
        msg = u'\n'.join([
            _(u'Wrye Bash encountered an error.'),
            _(u'Please post the information below to the official thread at'),
            _(u'https://afkmods.com/index.php?/topic/4966-wrye-bash-all-games'),
            _(u'or to the Wrye Bash Discord at'),
            _(u'https://discord.gg/NwWvAFR'),
            u'', caught_exc,
        ])
        _show_boot_popup(msg)

def _main(opts, wx_locale, wxver):
    """Run the Wrye Bash main loop.

    This function is marked private because it should be inside a try-except
    block. Call main() from the outside.

    :param opts: command line arguments
    :param wx_locale: The wx.Locale object that we ended up using."""
    # Initialize gui, our wrapper above wx (also balt, temp module) and
    # load the window icon resources
    from . import gui, balt
    # Now we have an App instance we can init Resources
    balt.load_app_icons()
    # Check for some non-critical dependencies (e.g. lz4) and warn if
    # they're missing now that we can show nice app icons
    _import_deps()
    # barg doesn't import anything else, so can be imported whenever we want
    from . import barg
    bass.sys_argv = barg.convert_to_long_options(sys.argv)
    if opts.debug:
        dump_environment(wxver)
    # Check if there are other instances of Wrye Bash running
    instance = _wx.SingleInstanceChecker(u'Wrye Bash') # must stay alive !
    assure_single_instance(instance)
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
        except (exception.BoltError, exception.StateError, OSError):
            bolt.deprint(u'Failed to restore backup', traceback=True)
            restore_ = None
    # The rest of backup/restore functionality depends on setting the game
    try:
        bashIni, bush_game, game_ini_path = _detect_game(opts, bash_ini_path)
        if not bush_game: return
        if restore_:
            try:
                restore_.restore_settings(
                    bush_game.bak_game_name, bush_game.my_games_name,
                    bush_game.bash_root_prefix, bush_game.mods_dir)
                # we currently disallow backup and restore on the same boot
                if opts.quietquit: return
            except (exception.BoltError, OSError, shutil.Error):
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
        from . import env
        env.testUAC(bush_game.gamePath.join(bush_game.mods_dir))
        global basher # share this instance with _close_dialog_windows
        from . import basher
    except (exception.BoltError, ImportError, OSError):
        msg = u'\n'.join([_(u'Error! Unable to start Wrye Bash.'), u'\n', _(
            u'Please ensure Wrye Bash is correctly installed.'), u'\n',
                          traceback.format_exc()])
        _show_boot_popup(msg)
        return # _show_boot_popup calls sys.exit, this gets pycharm to shut up
    atexit.register(exit_cleanup)
    basher.InitSettings()
    basher.InitLinks()
    basher.InitImages()
    #--Start application
    if opts.debug and bass.is_standalone:
        # Special case for py2exe version
        # Regain control of stdout/stderr from wxPython - TODO(inf) needed?
        sys.stdout = _bugdump_handle
        sys.stderr = _bugdump_handle
    bapp = basher.BashApp(bash_app)
    # Set the window title for stdout/stderr messages
    bash_app.SetOutputWindowAttributes(u'Wrye Bash stdout/stderr:')
    # Need to reference the locale object somewhere, so let's do it on the App
    bash_app.locale = wx_locale
    if env.is_uac():
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
            bkf = barb.BackupSettings.backup_filename(bush_game.bak_game_name)
            settings_file = gui.FileSave.display_dialog(
                frame, title=_(u'Backup Bash Settings'), defaultDir=base_dir,
                wildcard=u'*.7z', defaultFile=bkf)
        if settings_file:
            with gui.BusyCursor():
                backup = barb.BackupSettings(
                    settings_file, bush_game.bak_game_name,
                    bush_game.my_games_name, bush_game.bash_root_prefix,
                    bush_game.mods_dir)
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
    frame = bapp.Init() # Link.Frame is set here !
    frame.ensureDisplayed()
    frame.bind_refresh()
    bash_app.MainLoop()

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
    game_infos = bush.detect_and_set_game(opts.oblivionPath, bashIni)
    if game_infos is not None:  # None == success
        if len(game_infos) == 0:
            _show_boot_popup(_(
                u'Wrye Bash could not find a game to manage. Make sure to '
                u'launch games you installed through Steam once and enable '
                u'mods on games you installed through the Windows '
                u'Store.') + u'\n\n' + _(
                u'You can also use the -o command line argument or bash.ini '
                u'to specify the path manually.'))
            return None
        retCode = _select_game_popup(game_infos)
        if not retCode:
            bolt.deprint(u'No games were found or selected. Aborting.')
            return None
        # Add the game to the command line, so we use it if we restart
        gname, gm_path = retCode
        bass.update_sys_argv([u'--oblivionPath', f'{gm_path}'])
        bush.detect_and_set_game(opts.oblivionPath, bashIni, gname, gm_path)
    return bush.game

def _show_boot_popup(msg, is_critical=True):
    """Shows an error message in a popup window. If is_critical, exit the
    application afterwards. Must only be called after _import_wx, setup_locale
    and gui is imported."""
    if is_critical:
        _close_dialog_windows()
    try:
        from .balt import Resources
        from .gui import CancelButton, Color, LayoutOptions, \
            StartupDialog, TextArea, VLayout, CENTER
        class MessageBox(StartupDialog):
            def __init__(self, msg):
                popup_title = (_(u'Wrye Bash Error') if is_critical else
                               _(u'Wrye Bash Warning'))
                ##: Resizing is just discarded, maybe we could save it in
                # an early-boot file (see also #26)
                # Using Resources.bashRed here is fine - at worst it's None,
                # which will fall back to the default icon
                super(MessageBox, self).__init__(title=popup_title,
                                                 sizes_dict={},
                                                 icon_bundle=Resources.bashRed)
                self.component_size = (400, 300)
                msg_text = TextArea(self, editable=False, init_text=msg,
                                    auto_tooltip=False)
                VLayout(item_border=5, items=[
                    (msg_text, LayoutOptions(expand=True, weight=1)),
                    (CancelButton(self, btn_label=_(u'Quit') if is_critical
                                                 else _(u'OK')),
                     LayoutOptions(h_align=CENTER)),
                ]).apply_to(self)
        print(msg) # Print msg into error log.
        MessageBox.display_dialog(msg)
        if is_critical: sys.exit(1)
    except Exception: ##: tighten these excepts?
        # Instantiating wx.App failed, fallback to tkinter.
        but_kwargs = {u'text': u'QUIT' if is_critical else u'OK',
                      u'fg': u'red'}  # foreground button color
        _tkinter_error_dial(msg, but_kwargs)

def _tkinter_error_dial(msg, but_kwargs):
    import tkinter
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
    sys.exit(1)

def _close_dialog_windows():
    """Close any additional windows opened by wrye bash (e.g Splash, Dialogs).
    Must only be called after _import_wx.

    This will not close the main bash window (BashFrame) because closing that
    results in virtual function call exceptions."""
    import wx as _wx
    import wx.adv as _adv
    for window in _wx.GetTopLevelWindows():
        if basher is None or not isinstance(window, basher.BashFrame):
            if isinstance(window, _wx.Dialog):
                window.Destroy()
            ##: Skip for SplashScreen because it may hard-crash Python with
            # code -1073740771 (0xC000041D) when we call anything on it
            if not isinstance(window, _adv.SplashScreen):
                window.Close()

class _AppReturnCode(object):
    def __init__(self): self.value = None
    def get(self): return self.value
    def set(self, value): self.value = value

def _select_game_popup(game_infos):
    from .balt import Resources
    from .gui import Label, TextAlignment, WindowFrame, VLayout, \
        ImageDropDown, LayoutOptions, SearchBar, VBoxedLayout, TextField, \
        HLayout, QuitButton, ImageButton, HorizontalLine, Stretch, DropDown, \
        CENTER
    ##: Decouple game icon paths and move to popups.py once balt is refactored
    # enough
    class SelectGamePopup(WindowFrame):
        _def_size = (500, 400)

        def __init__(self, game_infos, callback):
            super(SelectGamePopup, self).__init__(
                None, title=_(u'Select Game'), icon_bundle=Resources.bashRed)
            self._callback = callback
            self._sorted_games = sorted(g.displayName for g in game_infos)
            self._game_to_paths = {g.displayName: ps for g, ps
                                  in game_infos.items()}
            self._game_to_info = {g.displayName: g for g in game_infos}
            self._game_to_bitmap = {
                g.displayName: _wx.Bitmap(bass.dirs[u'images'].join(
                    g.game_icon % 32).s) for g in game_infos}
            # Construction of the actual GUI begins here
            game_search = SearchBar(self)
            game_search.on_text_changed.subscribe(self._perform_search)
            self._game_dropdown = ImageDropDown(self, value=u'', choices=[u''])
            self._game_dropdown.on_combo_select.subscribe(self._select_game)
            self._lang_dropdown = DropDown(self, value=u'', choices=[u''])
            self._lang_dropdown.on_combo_select.subscribe(self._select_lang)
            self._game_path = TextField(self, editable=False)
            quit_button = QuitButton(self)
            quit_button.on_clicked.subscribe(self._handle_quit)
            launch_img = bass.dirs[u'images'].join(u'bash_32_2.png').s
            self._launch_button = ImageButton(self, _wx.Bitmap(launch_img),
                                              btn_label=_(u'Launch'))
            self._launch_button.on_clicked.subscribe(self._handle_launch)
            # Start out with an empty search and the alphabetically first game
            # selected
            self._perform_search(search_str=u'')
            VLayout(item_expand=True, border=6, spacing=12, items=[
                Label(self, _(u'Please choose a game to manage.'),
                      alignment=TextAlignment.CENTER),
                game_search, self._game_dropdown,
                (VBoxedLayout(self, title=_(u'Game Details'), item_expand=True,
                              spacing=12, items=[
                    HLayout(spacing=6, items=[
                        (Label(self, _(u'Variant:')),
                         LayoutOptions(v_align=CENTER)),
                        (self._lang_dropdown,
                         LayoutOptions(expand=True, weight=1)),
                    ]),
                    HLayout(spacing=6, items=[
                        (Label(self, _(u'Install Path:')),
                         LayoutOptions(v_align=CENTER)),
                        (self._game_path,
                         LayoutOptions(expand=True, weight=1)),
                    ]),
                ]), LayoutOptions(weight=3)),
                HorizontalLine(self),
                (HLayout(item_expand=True, item_weight=1, items=[
                    quit_button, Stretch(), self._launch_button,
                ]), LayoutOptions(weight=1)),
            ]).apply_to(self)

        @property
        def _chosen_path(self):
            avail_paths = self._game_to_paths[self._game_dropdown.get_value()]
            if len(avail_paths) == 1:
                return avail_paths[0]
            else:
                chosen_lang = self._lang_dropdown.get_value()
                for p in avail_paths:
                    if chosen_lang in p.s:
                        return p
                return None # Should never happen

        def _perform_search(self, search_str):
            prev_choice = self._game_dropdown.get_value()
            search_lower = search_str.lower().strip()
            filtered_games = [g for g in self._sorted_games
                              if search_lower in g.lower()]
            with self._game_dropdown.pause_drawing():
                self._game_dropdown.set_choices(filtered_games)
                self._game_dropdown.set_bitmaps([self._game_to_bitmap[g]
                                                 for g in filtered_games])
                # Check if the previous choice can be restored now, otherwise
                # select the first game
                try:
                    new_choice = filtered_games.index(prev_choice)
                except ValueError:
                    new_choice = 0
                self._game_dropdown.set_selection(new_choice)
            # Enable the Launch button only if a game is selected
            new_selection = self._game_dropdown.get_value()
            self._launch_button.enabled = bool(new_selection)
            # Finally, update the game details to match the newly active game
            self._select_game(new_selection)

        def _select_game(self, selected_game):
            if not selected_game:
                # No game selected, clear the details
                self._lang_dropdown.set_choices([_(u'N/A')])
                self._lang_dropdown.set_selection(0)
                self._lang_dropdown.enabled = False
                self._game_path.text_content = u''
            else:
                # Enable the Language dropdown only if we >1 path for the newly
                # active game
                available_paths = self._game_to_paths[selected_game]
                if len(available_paths) > 1:
                    self._lang_dropdown.set_choices([p.stail for p
                                                     in available_paths])
                    self._lang_dropdown.set_selection(0)
                    self._lang_dropdown.enabled = True
                else:
                    self._lang_dropdown.set_choices([_(u'N/A')])
                    self._lang_dropdown.set_selection(0)
                    self._lang_dropdown.enabled = False
                # Set the path based on the default language
                self._select_lang()

        def _select_lang(self, _selected_lang=None):
            self._game_path.text_content = self._chosen_path.s

        def _handle_quit(self):
            self._callback(None)
            self.close_win(force_close=True)

        def _handle_launch(self):
            self._callback((self._game_dropdown.get_value(),
                            self._chosen_path))
            self.close_win(force_close=True)
    retCode = _AppReturnCode()
    frame = SelectGamePopup(game_infos, retCode.set)
    frame.show_frame(center=True)
    bash_app.MainLoop(restore_stdio=False)
    return retCode.get()

# Version checks --------------------------------------------------------------
def _rightWxVersion(wxver):
    """Shows a warning if the wrong wxPython version is installed. Must only be
    called after _import_wx, setup_locale and balt is imported."""
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
    if sysVersion < (3, 9) or sysVersion >= (4,):
        from . import balt
        balt.showError(
            None, _(u'Only Python 3.9 and newer is supported (%s.%s.%s '
                    u"detected). If you know what you're doing, install the "
                    u'Python version of Wrye Bash and edit this warning out. '
                    u'Wrye Bash will now exit.') % sysVersion,
            title=_(u'Incompatible Python version detected'))
        return False
    return True
