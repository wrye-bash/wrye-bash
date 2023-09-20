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
"""This module starts the Wrye Bash application in console mode. Basically,
it runs some initialization functions and then starts the main application
loop."""

import atexit
import locale
import os
import platform
import shutil
import sys
import traceback
from configparser import ConfigParser

from . import bass, bolt, exception, wbtemp

# NO OTHER LOCAL IMPORTS HERE (apart from the ones above) !
basher = None # need to share it in _close_dialog_windows
bass.is_standalone = hasattr(sys, u'frozen')
_bugdump_handle = None
# The one and only wx
_wx = None

def _early_setup():
    """Executes (very) early setup by changing working directory and installing
    the BashBugDump hooks."""
    # Install a hook to handle unraisable error messages (at least when a tty
    # is attached)
    def unraisable_hook(unraisable):
        def _print(s):
            print(s, file=sys.__stderr__)
        _print(f'An unraisable exception occurred: {unraisable.exc_value!r}')
        _print(f'Affected object: {unraisable.object!r}')
        if unraisable.exc_traceback:
            _print('Traceback:')
            for tb_line in traceback.format_tb(unraisable.exc_traceback):
                _print(tb_line.rstrip()) # Drop newlines, print will add them
    sys.unraisablehook = unraisable_hook
    # ensure we are in the correct directory so relative paths will work
    # properly
    if bass.is_standalone:
        pathToProg = os.path.dirname(sys.executable)
    else:
        pathToProg = os.path.dirname(sys.argv[0])
    if pathToProg:
        os.chdir(pathToProg)
    global _bugdump_handle
    _bugdump_handle = open(os.path.join(os.getcwd(), 'BashBugDump.log'), 'w',
        buffering=1, encoding='utf-8')
    _install_bugdump()

def _install_bugdump():
    """Replaces sys.stdout/sys.stderr with tees that copy the output into the
    BashBugDump as well."""
    if sys.stdout:
        sys.stdout = bolt.Tee(sys.stdout, _bugdump_handle)
    else:
        sys.stdout = _bugdump_handle
    if sys.stderr:
        sys.stderr = bolt.Tee(sys.stderr, _bugdump_handle)
    else:
        sys.stderr = _bugdump_handle

# Wx --------------------------------------------------------------------------
# locale/image calls in wx work once an App object is instantiated and in scope
bash_app = None  ##: typing
def _import_wx():
    """Import wxpython or show a tkinter error and exit if unsuccessful."""
    try:
        global _wx
        import wx as _wx
        # Hacky fix for loading older settings that pickled classes from
        # moved/deleted wx modules
        from wx import _core
        sys.modules[u'wx._gdi'] = _core
        class _BaseApp(_wx.App):
            def MainLoop(self, restore_stdio=True):
                """Not sure what RestoreStdio does so I omit the call in game
                selection dialog.""" # TODO: check standalone also
                rv = _wx.PyApp.MainLoop(self)
                if restore_stdio: self.RestoreStdio()
                return rv
            def InitLocale(self):
                if sys.platform.startswith('win') and sys.version_info > (3,8):
                    locale.setlocale(locale.LC_CTYPE, 'C') # pass?
        # Initialize the App instance once
        global bash_app
        bash_app = _BaseApp(bass.is_standalone)
        if bass.is_standalone:
            # No console on the standalone version, so we have wxPython take
            # over. However, we don't want it to grab the stdout stream (since
            # that's where all the boring debug printing goes that the user can
            # view just fine in the BashBugDump)
            sys.stdout = sys.__stdout__
            _install_bugdump()
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
        import win32api
        import win32com
    except ImportError:
        # Only a dependency on Windows, so skip on other operating systems
        if bolt.os_name == u'nt':
            deps_msg += u'- pywin32\n'
    try:
        import ifileoperation
    except ImportError:
        # Only a dependency on Windows, so skip on other operating systems
        if bolt.os_name == 'nt':
            deps_msg += '- ifileoperation\n'
    try:
        import yaml
    except ImportError:
        deps_msg += u'- PyYAML\n'
    try:
        import vdf
    except ImportError:
        deps_msg += '- vdf\n'
    if deps_msg:
        deps_msg += u'\n'
        if bass.is_standalone:
            # Dependencies are always present in standalone, so this probably
            # means an MSVC redist is missing
            deps_msg += _('This most likely means you are missing a certain '
                          'version of the Microsoft Visual C++ '
                          'Redistributable. Try installing the latest x64 '
                          'version.')
        else:
            deps_msg += _('Ensure you have installed these dependencies '
                          'properly. Should the error still occur, check '
                          'your installed Microsoft Visual C++ '
                          'Redistributables and try installing the latest '
                          'x64 version.')
        _show_boot_popup(_('The following dependencies could not be located '
                           'or failed to load:') + u'\n\n' + deps_msg)

def _warn_missing_bash_dir():
    """Check for some vital files that *must* be present (note that most dirs
    don't have to be present in certain scenarios: bash/compiled/* is optional
    on Linux, bash/taglists/* is completely optional and the Python files and
    dirs are gone in standalone builds)."""
    test_files = [bass.dirs['mopy'].join(*x) for x in (
        ('bash', 'l10n', 'de_DE.po'), ('bash', 'images', 'bash.svg'))]
    if any(not t.is_file() for t in test_files):
        msg = (_('Installation appears incomplete. Please reinstall Wrye Bash '
                 'so that all files are installed.') + '\n\n' +
               _('Correct installation will create a filled %(wb_folder)s '
                 'folder.') % {'wb_folder': os.path.join('Mopy', 'bash')})
        raise RuntimeError(msg)

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
        from . import gui
        gui.showOk(None, _('Only one instance of Wrye Bash can run.'),
                   title='Wrye Bash')
        sys.exit(1)

def exit_cleanup():
    wbtemp.cleanup_temp()
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
                exe = [f'{exe}', f'"{exe}"'][' ' in exe]
                cli = ' '.join([f'{x}', f'"{x}"'][' ' in x] for x in cli)
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
            # Use __stdout__ here, stdout/bugdump might have been closed
            print(error, file=sys.__stdout__)
            print('Error Attempting to Restart Wrye Bash!',file=sys.__stdout__)
            print(f'cmd line: {cmd_line}', file=sys.__stdout__)
            print(file=sys.__stdout__)
            raise

def dump_environment(wxver=None):
    """Dumps information about the environment. Must only be called after
    _import_wx and _import_deps."""
    # Note that we can't dump pywin32 because it doesn't contain a version
    # field in its modules
    try:
        import chardet
        chardet_ver = chardet.__version__
    except ImportError:
        chardet_ver = 'not found'
    try:
        import lxml
        lxml_ver = lxml.__version__
    except ImportError:
        lxml_ver = 'not found (optional)'
    try:
        import packaging
        packaging_ver = packaging.__version__
    except ImportError:
        packaging_ver = 'not found (optional)'
    try:
        import fitz
        pymupdf_ver = (f'{fitz.VersionBind}; bundled MuPDF version: '
                       f'{fitz.VersionFitz}')
    except ImportError:
        pymupdf_ver = 'not found (optional)'
    try:
        import lz4
        lz4_ver = (f'{lz4.version.version}; bundled LZ4 version: '
                   f'{lz4.library_version_string()}')
    except ImportError:
        lz4_ver = 'not found'
    try:
        import yaml
        yaml_ver = yaml.__version__
    except ImportError:
        yaml_ver = 'not found'
    try:
        import requests
        requests_ver = requests.__version__
    except ImportError:
        requests_ver = 'not found (optional)'
    try:
        import vdf
        vdf_ver = vdf.__version__
    except ImportError:
        vdf_ver = 'not found'
    try:
        import websocket
        websocket_client_ver = websocket.__version__
    except ImportError:
        websocket_client_ver = 'not found (optional)'
    wx_ver = wxver or 'not found'
    try:
        import ifileoperation
        ifileoperation_ver = ifileoperation.__version__
    except ImportError:
        ifileoperation_ver = 'not found'
    # Now that we have checked all dependencies (including potentially missing
    # ones), we can build the environment dump
    fse = bolt.Path.sys_fs_enc
    msg = [
        f'Using Wrye Bash Version {bass.AppVersion}'
        f'{u" (Standalone)" if bass.is_standalone else u""}',
        f'OS info: {platform.platform()}, running on '
        f'{platform.processor() or u"<unknown>"}',
        f'Python version: {sys.version}'.replace('\n', '\n\t'),
        'Dependency versions:',
        f' - chardet: {chardet_ver}',
    ]
    if bolt.os_name == 'nt': # Hide on non-Windows platforms
        msg.append(f' - ifileoperation: {ifileoperation_ver}')
    msg.extend([
        f' - lxml: {lxml_ver}',
        f' - packaging: {packaging_ver}',
        f' - PyMuPDF: {pymupdf_ver}',
        f' - python-lz4: {lz4_ver}',
        f' - PyYAML: {yaml_ver}',
        f' - requests: {requests_ver}',
        f' - vdf: {vdf_ver}',
        f' - websocket-client: {websocket_client_ver}',
        f' - wxPython: {wx_ver}',
        # Standalone: stdout will actually be pointing to stderr, which has no
        # 'encoding' attribute and stdin will be None
        f'Input encoding: {sys.stdin.encoding if sys.stdin else None}; '
        f'output encoding: {getattr(sys.stdout, u"encoding", None)}',
        f'Filesystem encoding: {fse}'
        f'{f" - using {bolt.Path.sys_fs_enc}" if not fse else ""}',
        f'Command line: {sys.argv}',
    ])
    bolt.deprint(msg := '\n\t'.join(msg))
    return msg

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
    if (os_system := platform.system()) != 'Windows' and not opts.unix:
        # Linux is still mostly broken, so raise on import
        raise ImportError(f'Wrye Bash only partially supports {os_system} at '
                          f"the moment. If you know what you're doing, use "
                          f"the --unix switch to bypass this raise statement.")
    # Change working dir and logging
    _early_setup()
    # wx is needed to initialize locale, so that's first
    wxver = _import_wx()
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
        # Make sure we actually have a functional 'bash' folder to work with
        _warn_missing_bash_dir()
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
    # load the window icon resources now that we have an app instance
    from . import balt, gui
    balt.load_app_icons()
    # Check for some non-critical dependencies (e.g. lz4) and warn if
    # they're missing now that we can show nice app icons
    _import_deps()
    # barg doesn't import anything else, so can be imported whenever we want
    from . import barg
    bass.sys_argv = barg.convert_to_long_options(sys.argv)
    dump_environment(wxver)
    # Check if there are other instances of Wrye Bash running
    instance = _wx.SingleInstanceChecker(u'Wrye Bash') # must stay alive !
    assure_single_instance(instance)
    # if HTML file generation was requested, just do it and quit
    if opts.genHtml is not None:
        ##: See if the encodes are actually necessary
        msg1 = _(f"Generating HTML file from '%(gen_target)s'") % {
            'gen_target': opts.genHtml}
        msg2 = _('Done')
        try: print(msg1)
        except UnicodeError: print(msg1.encode(bolt.Path.sys_fs_enc))
        ##: belt does bolt.codebox = WryeParser.codebox - FIXME decouple!
        # noinspection PyUnresolvedReferences
        from . import belt
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
        except (exception.BoltError, exception.StateError, OSError,
                NotImplementedError):
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
            except (exception.BoltError, OSError, shutil.Error,
                    NotImplementedError):
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
    except (exception.BoltError, ImportError, OSError, NotImplementedError):
        msg = u'\n'.join([_(u'Error! Unable to start Wrye Bash.'), u'\n', _(
            u'Please ensure Wrye Bash is correctly installed.'), u'\n',
                          traceback.format_exc()])
        _show_boot_popup(msg)
        return # _show_boot_popup calls sys.exit, this gets pycharm to shut up
    atexit.register(exit_cleanup)
    basher.InitSettings()
    # Status bar buttons are initialized in InitLinks and use images
    basher.InitImages()
    basher.InitLinks()
    #--Start application
    bapp = basher.BashApp(bash_app)
    # Set the window title for stdout/stderr messages
    bash_app.SetOutputWindowAttributes(u'Wrye Bash stdout/stderr:')
    # Need to reference the locale object somewhere, so let's do it on the App
    bash_app.locale = wx_locale
    if env.is_uac():
        uacRestart = opts.uac
        if not opts.noUac and not uacRestart:
            # Show a prompt asking if we should restart in Admin Mode
            message = _(
                'Wrye Bash needs Administrator Privileges to make changes to '
                'the %(gameName)s directory.  If you do not start Wrye Bash '
                'with elevated privileges, you will be prompted at each '
                'operation that requires elevated privileges.') % {
                    'gameName': bush_game.display_name}
            uacRestart = balt.ask_uac_restart(message, mopy=bass.dirs['mopy'])
        if uacRestart:
            bass.update_sys_argv(['--uac'])
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
                msg = [_('There was an error while trying to backup the Bash '
                         'settings!'),
                       _('If you continue, your current settings may be '
                         'overwritten.'),
                       _('Do you want to quit Wrye Bash now?')]
                if gui.askYes(frame, '\n'.join(msg),
                              title=_('Unable to create backup!')):
                    return  # Quit
    frame = bapp.Init() # Link.Frame is set here !
    frame.ensureDisplayed()
    frame.bind_refresh()
    # Start the update check in the background and pass control to wx's event
    # loop so that the daemon can send its event to the main thread
    frame.start_update_check()
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
        warning_msg = _('The following (non-critical) warnings were found '
                        'during initialization:')
        warning_msg += '\n\n'
        warning_msg += '\n'.join(f'- {w}' for w in init_warnings)
        _show_boot_popup(warning_msg, is_critical=False)
    return bashIni, bush_game, game_ini_path

def _import_bush_and_set_game(opts, bashIni):
    from . import bush
    bolt.deprint(u'Searching for game to manage:')
    game_infos = bush.detect_and_set_game(cli_game_dir=opts.oblivionPath,
        bash_ini_=bashIni)
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
        from .gui import CENTER, CancelButton, Color, LayoutOptions, \
            StartupDialogWindow, TextArea, VLayout
        class MessageBox(StartupDialogWindow):
            def __init__(self, msg):
                popup_title = (_(u'Wrye Bash Error') if is_critical else
                               _(u'Wrye Bash Warning'))
                ##: Resizing is just discarded, maybe we could save it in
                # an early-boot file (see also #26)
                # Using Resources.bashRed here is fine - at worst it's None,
                # which will fall back to the default icon
                super().__init__(title=popup_title, sizes_dict={},
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
    ##: Decouple game icon paths and move to popups.py once balt is refactored
    # enough
    from .balt import ImageWrapper, Resources
    from .gui import CENTER, CancelButton, DropDown, HLayout, HorizontalLine, \
        ImageButton, ImageDropDown, Label, LayoutOptions, SearchBar, Stretch, \
        TextAlignment, TextField, VBoxedLayout, VLayout, WindowFrame
    class SelectGamePopup(WindowFrame):
        _def_size = (500, 400)

        def __init__(self, game_infos, callback):
            super().__init__(None, title=_('Select Game'),
                icon_bundle=Resources.bashRed)
            self._callback = callback
            self._sorted_games = sorted(
                g.unique_display_name for g in game_infos)
            self._game_to_paths = {g.unique_display_name: ps for g, ps
                                  in game_infos.items()}
            self._game_to_info = {g.unique_display_name: g for g in game_infos}
            gi_join = bass.dirs['images'].join('games').join
            self._game_to_bitmap = {
                g.unique_display_name: ImageWrapper(gi_join(g.game_icon % 32),
                    iconSize=32).get_bitmap() for g in game_infos}
            # Construction of the actual GUI begins here
            game_search = SearchBar(self, hint=_('Search Games'))
            game_search.on_text_changed.subscribe(self._perform_search)
            self._game_dropdown = ImageDropDown(self, value=u'', choices=[u''])
            self._game_dropdown.on_combo_select.subscribe(self._select_game)
            self._lang_dropdown = DropDown(self, value=u'', choices=[u''])
            self._lang_dropdown.on_combo_select.subscribe(self._select_lang)
            self._game_path = TextField(self, editable=False)
            class _ImgCancelButton(CancelButton, ImageButton): pass
            quit_img = ImageWrapper(bass.dirs['images'].join('quit.svg'),
                iconSize=32)
            quit_button = _ImgCancelButton(self, quit_img.get_bitmap(),
                btn_label=_('Quit'))
            quit_button.on_clicked.subscribe(self._handle_quit)
            launch_img = ImageWrapper(bass.dirs['images'].join('bash.svg'),
                iconSize=32)
            self._launch_button = ImageButton(self, launch_img.get_bitmap(),
                btn_label=_('Launch'))
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
            search_lower = search_str.strip().lower()
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
    if not wxver.startswith('4.2'):
        from . import gui
        return gui.askYes(None, _(
            'Warning: you appear to be using a non-supported version of '
            'wxPython (%(curr_wx_ver)s). This will cause problems! It is '
            'highly recommended you use a %(supported_wx_series)s version. Do '
            'you still want to run Wrye Bash?') % {
            'curr_wx_ver': wxver, 'supported_wx_series': '4.2.x'},
            title=_('Unsupported wxPython Version Detected'))
    return True

def _rightPythonVersion():
    """Shows an error if the wrong Python version is installed. Must only be
    called after _import_wx, setup_locale and balt is imported."""
    sysVersion = sys.version_info[:3]
    if sysVersion < (3, 11) or sysVersion >= (4,):
        from . import gui
        gui.showError(None, _(
            "Only Python %(min_py_ver)s and newer is supported "
            "(%(curr_py_ver)s detected). If you know what you're doing, "
            "install the Python version of Wrye Bash and edit this warning "
            "out. Wrye Bash will now exit.") % {'min_py_ver': '3.11',
                                                'curr_py_ver': sysVersion},
            title=_('Unsupported Python Version Detected'))
        return False
    return True
