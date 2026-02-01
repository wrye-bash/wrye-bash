#!/usr/bin/env python3
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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2026 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Build and package Wrye Bash.

Creates three different types of distributables:
 - Manual     - the python source files, requires Wrye Bash's development
                dependencies to run;
 - Standalone - a portable distributable with the pre-built executable;
 - Installer  - a binary distribution containing a custom installer.

Most steps of the build process can be customized, see the options below."""
import datetime
import logging
import os
import re
import shutil
import sys
import tempfile
import textwrap
from collections import defaultdict
from itertools import chain

try:
    import winreg
except ImportError:
    # Linux - unused there right now because we abort before trying to build
    # the executable
    winreg = None
import zipfile
from contextlib import contextmanager, suppress
from pathlib import Path

import compile_l10n
import PyInstaller.__main__
import update_taglist
from helpers.utils import APPS_PATH, DIST_PATH, MOPY_PATH, NSIS_PATH, \
    ROOT_PATH, SCRIPTS_PATH, TAGINFO, WBSA_PATH, L10N_PATH, LooseVersion, \
    edit_bass_version, cp, mv, rm, run_script, mk_logfile, run_subprocess, \
    download_file, with_args, setup_log, WBRepo

_LOGGER = logging.getLogger(__name__)
_LOGFILE = mk_logfile(__file__)

# Linux or macOS, we don't support anything but building the source
# distributable right now
_NOT_WINDOWS = os.name != 'nt'

_NSIS_VERSION = '3.11'
if _NOT_WINDOWS:
    _EXE_7Z = '7z'
else:
    _EXE_7Z = MOPY_PATH / 'bash' / 'compiled' / '7z.exe'

sys.path.insert(0, str(MOPY_PATH))
from bash import bass

# create the repo instance
_WB_REPO = WBRepo(ROOT_PATH)

_locs = {'uk_UA', 'zh_CN', 'ja_JP', 'pt_PT', 'sv_SE', 'ta', 'de_DE', 'zh_TW',
         'pt_BR', 'es_ES', 'it_IT', 'tr_TR', 'ru_RU'} ##:get those from weblate
def _filter_tracked(tracked) -> list[str]:
    # filter tracked files to include in manual package and add taglists/.mo
    # keep the files in Mopy only
    mopy_tr = [x for x in tracked if x.startswith('Mopy/') and
               not x.startswith(('Mopy/bash/l10n', 'Mopy/bash/tests'))]
    yamls = ('/'.join((pa := p.parts)[pa.index('Mopy'):]) for p in
             update_taglist.TAGLISTS_PATHS)
    mos = (f'Mopy/bash/l10n/{x}.mo' for x in _locs)
    return [*mopy_tr, *yamls, *mos, 'Mopy/LICENSE.md']

_min_sha_len = 7 # minimum length to keep from commit hash

def _setup_build_parser(parser):
    version_group = parser.add_mutually_exclusive_group()
    curr_datetime = datetime.datetime.now(datetime.UTC)
    nightly_version = (f'{bass.AppVersion.split(".")[0]}.'
                       f'{curr_datetime.strftime("%Y%m%d%H%M")}')
    version_group.add_argument(
        '-n',
        '--nightly',
        action='store_const',
        const=nightly_version,
        dest='build_version',
        help="Build with the nightly release format 'VERSION.TIMESTAMP' "
             "[default].",
    )
    version_group.add_argument(
        '-p',
        '--production',
        action='store_const',
        const=bass.AppVersion,
        dest='build_version',
        help="Build with the production release format 'VERSION'.",
    )
    parser.add_argument(
        '-t',
        '--version_tag',
        nargs='?', # zero or one arguments
        const=None, # if no argument is given, use None -> commit hash
        default='', # if not specified, don't tag
        dest='version_tag',
        help='Tag the version with the given string or the commit sha',
    )
    parser.add_argument(
        '--sha_len',
        default=_min_sha_len,
        dest='sha_len',
        type=int,
        help='Number of characters of the commit hash to use - also min len '
             'for a str to be considered a hash tag.',
    )
    parser.add_argument(
        '-c',
        '--commit',
        action='store_true',
        dest='commit',
        help='Create a commit with the version used to build.'
    )
    parser.add_argument(
        '--no-standalone',
        action='store_false',
        dest='standalone',
        help="Don't package a standalone version.",
    )
    parser.add_argument(
        '--no-manual',
        action='store_false',
        dest='manual',
        help="Don't package a manual version.",
    )
    parser.add_argument(
        '--no-installer',
        action='store_false',
        dest='installer',
        help="Don't package an installer version.",
    )
    parser.add_argument(
        '--nsis',
        default=None,
        dest='nsis',
        help='Specify a custom path to the NSIS root folder.',
    )
    parser.add_argument(
        '-u',
        '--update-taglists',
        action='store_true',
        dest='force_tl_update',
        help='Forces an update of the bundled taglists.',
    )
    parser.set_defaults(build_version=nightly_version)

# PyInstaller thinks it's fine to setup logging on import...
def _setup_pyinstaller_logger(logfile):
    root_logger = logging.getLogger()
    stupid_handler = root_logger.handlers[0]
    stupid_formatter = stupid_handler.formatter
    root_logger.removeHandler(stupid_handler)
    file_handler = logging.FileHandler(logfile)
    file_handler.setFormatter(stupid_formatter)
    logging.getLogger('PyInstaller').addHandler(file_handler)

def _pack_7z(dest_7z, keep):
    with tempfile.TemporaryDirectory() as tmpdir:
        include_file = Path(tmpdir) / 'files_to_include.txt'
        with include_file.open('w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(keep))
        cmd_7z = [_EXE_7Z, 'a', '-m0=lzma2', '-mx9', DIST_PATH / dest_7z,
                  f'-i@{include_file}']
        run_subprocess(cmd_7z, _LOGGER, cwd=ROOT_PATH)

def _get_nsis_root(cmd_arg):
    """Finds and returns the nsis root folder."""
    if cmd_arg is not None:
        _LOGGER.debug(f'User provided NSIS path at {cmd_arg}')
        return cmd_arg
    try:
        nsis_path = winreg.QueryValue(winreg.HKEY_LOCAL_MACHINE,
            r'Software\NSIS')
        _LOGGER.debug(f'Found system NSIS path at {nsis_path}')
        return nsis_path
    except WindowsError:
        pass
    if not NSIS_PATH.is_dir():
        _LOGGER.debug(f'Local NSIS not found at {NSIS_PATH}')
        local_build_path = NSIS_PATH.parent
        nsis_url = (f'https://sourceforge.net/projects/nsis/files/NSIS%203/'
                    f'{_NSIS_VERSION}/nsis-{_NSIS_VERSION}.zip/download')
        dl_dir = Path(tempfile.mkdtemp())
        nsis_zip = dl_dir / 'nsis.zip'
        _LOGGER.info(f'Downloading NSIS {_NSIS_VERSION}...')
        _LOGGER.debug(f'Download url: {nsis_url}')
        _LOGGER.debug(f'Download NSIS to {nsis_zip}')
        download_file(nsis_url, nsis_zip)
        with zipfile.ZipFile(nsis_zip) as fzip:
            fzip.extractall(local_build_path)
        rm(dl_dir)
        os.rename(local_build_path / f'nsis-{_NSIS_VERSION}', NSIS_PATH)
    return NSIS_PATH

def _pack_manual(build_vers, mopy_tr):
    """ Packages the manual (python source) version. """
    copied = {'Readme.md': ROOT_PATH, 'requirements.txt': ROOT_PATH,
              'bash.ico': WBSA_PATH}
    files_to_include = {di / fi: MOPY_PATH / fi for fi, di in copied.items()}
    try:
        for orig, target in files_to_include.items():
            cp(orig, target)
        _pack_7z(f'Wrye Bash {build_vers} - Python Source.7z',
                 [*mopy_tr, 'Mopy/Apps', *(f'Mopy/{a}' for a in copied), ''])
    finally:
        for path in files_to_include.values():
            rm(path)

@contextmanager
def _build_executable():
    """ Builds the executable. """
    _LOGGER.info('Building executable...')
    temp_path = WBSA_PATH / 'temp'
    dist_path = WBSA_PATH / 'dist'
    orig_exe =  dist_path / 'Wrye Bash.exe'
    dest_exe =  MOPY_PATH / 'Wrye Bash.exe'
    spec_path = os.fspath(WBSA_PATH / 'pyinstaller.spec')
    PyInstaller.__main__.run(['--clean', '--noconfirm',
                              f'--distpath={dist_path}',
                              f'--workpath={temp_path}', spec_path])
    cp(orig_exe, dest_exe) # Copy to Mopy folder, needed for packaging
    try:
        yield
    finally:
        rm(dest_exe)

def _pack_standalone(build_vers, mopy_tr):
    """ Packages the standalone version. """
    _pack_7z(f'Wrye Bash {build_vers} - Standalone Executable.7z',
             [*mopy_tr, 'Mopy/Apps', 'Mopy/Wrye Bash.exe', ''])

def _pack_installer(nsis_path, build_vers, file_version, mopy_tr):
    """ Packages the installer version. """
    script_path = SCRIPTS_PATH / 'build' / 'installer' / 'main.nsi'
    if not script_path.is_file():
        raise OSError(f"Could not find nsis script '{script_path}', aborting "
                      f"installer creation.")
    nsis_root = _get_nsis_root(nsis_path)
    nsis_path = nsis_root / 'makensis.exe'
    if not nsis_path.is_file():
        raise OSError("Could not find 'makensis.exe' in NSIS folder, aborting "
                      "installer creation.")
    files_macro = SCRIPTS_PATH / 'build' / 'installer' / 'InstallBashFiles.nsh'
    try:
        _write_nsis_macro(files_macro, mopy_tr)
         # Run the NSIS script to build the installer
        run_subprocess([nsis_path, '/NOCD', f'/DWB_NAME=Wrye Bash {build_vers}',
                        f'/DWB_OUTPUT={DIST_PATH}',
                        f'/DWB_FILEVERSION={file_version}',
                        f'/DWB_CLEAN_MOPY={MOPY_PATH}', script_path], _LOGGER)
    finally:
        files_macro.unlink(missing_ok=True)

def _write_nsis_macro(files_macro, tracked_files):
    """ Writes an NSIS macro file InstallBashFiles.nsh dynamically based on
    tracked_files.

    tracked_files: list of Posix relative paths inside Mopy/."""
    macro_lines = [
        '!ifmacrondef InstallBashFiles',
        '!macro InstallBashFiles GameDir RegPath',
        '    ; Parameters:',
        '    ;  GameDir - base directory for the game (one folder up from '
        'the Data directory)',
        '    ;  RegPath - Name of the registry string that will hold the '
        'path installing to', '', '    ; Install tracked files']
    # Group files by folder
    files_by_folder = defaultdict(list)
    for p in map(Path, tracked_files):
        files_by_folder[p.parent].append(p.name)
    # Generate SetOutPath + File lines
    for folder, files in sorted(files_by_folder.items()):
        nsis_folder = '${GameDir}\\Mopy'
        wb_clean_folder = '${WB_CLEAN_MOPY}'
        if folder != Path('.'):
            folder = str(folder).replace('/', '\\')[5:] # remove 'Mopy\'
            nsis_folder = f'{nsis_folder}\\{folder}'
            wb_clean_folder = f'{wb_clean_folder}\\{folder}'
        macro_lines.append(f'    SetOutPath "{nsis_folder}"')
        for fname in sorted(files):
            macro_lines.append(f'    File "{wb_clean_folder}\\{fname}"')
    # Standalone executable
    macro_lines.extend([
        '    ; Install the standalone only files',
        '    SetOutPath "${GameDir}\\Mopy"',
        '    File "${WB_CLEAN_MOPY}\\Wrye Bash.exe"',
        '    CreateDirectory "${GameDir}\\Mopy\\Apps"',
        '', '    ; Write registry key',
        '    WriteRegStr HKLM "SOFTWARE\\Wrye Bash" "${RegPath}" "${GameDir}"',
        '!macroend'])
    # Uninstall: remove new untracked files
    all_tracked = _WB_REPO.get_tracked_paths(None) # takes 17 secs locally
    untracked = all_tracked - tracked_files
    macro_lines.extend(_generate_removefiles_macro(tracked_files, untracked))
    macro_lines.extend(['!endif', ''])
    # Write macro to file
    files_macro.write_text('\n'.join(macro_lines), encoding='utf-8')
    _LOGGER.info(f'NSIS macro written to {files_macro}')

# curated legacy/dev/nightly artifacts (largely derived from the historical
# RemoveOldFiles macro) that may not show up in tracked(all) - tracked(head)
_MANUAL_EXACT_REMOVALS = [ # poxix paths relative to root dir
    # Old old files to delete (from before 294, the directory restructure)
    'Mopy/uninstall.exe',
    # Legacy: older Standalone produced non-standard compiled python file names
    # (when loading python files present)
    'Mopy/bash/balto', 'Mopy/bash/bapio', 'Mopy/bash/barbo', 'Mopy/bash/bargo',
    'Mopy/bash/bashero', 'Mopy/bash/basho', 'Mopy/bash/basso', 'Mopy/bash/belto',
    'Mopy/bash/bolto', 'Mopy/bash/bosho', 'Mopy/bash/breco', 'Mopy/bash/busho',
    'Mopy/bash/bwebo', 'Mopy/bash/cinto', 'Mopy/bash/libbsao',
    'Mopy/bash/windowso',
    # As of version 300: image files were moved to Mopy/bash/images/tools
    'Mopy/bash/images/krita16.png', 'Mopy/bash/images/krita24.png',
    'Mopy/bash/images/krita32.png',
    # As of 301: the following are obsolete
    'Mopy/bash/keywordWIZBAIN2o', 'Mopy/bash/keywordWIZBAINo',
    'Mopy/bash/settingsModuleo', 'Mopy/bash/wizSTCo',
    # As of 305: the following are obsolete
    'Mopy/w9xpopen.exe',
    # As of 307: the following are obsolete
    'Mopy/bash/images/readme/installers-wizard-1.jpg',
    'Mopy/bash/images/readme/installers-wizard-2.jpg',
    'Mopy/bash/images/readme/mods-feat-add-tags.png',
    'Mopy/bash/images/readme/mods-feat-change-mtime.png',
    'Mopy/bash/images/readme/mods-feat-del-tags.png',
    'Mopy/bash/images/readme/saves-2-rclick-save-5.png',
    'Mopy/bash/images/readme/saves-2-rclick-save-6.png',
    'Mopy/bash/images/readme/saves-2-rclick-save-7.png',
    # As of 308: translations use the .po extension and new names
    'Mopy/bash/l10n/Chinese (Simplified).mo',
    'Mopy/bash/l10n/Chinese (Traditional).mo', 'Mopy/bash/l10n/Italian.mo',
    'Mopy/bash/l10n/Japanese.mo', 'Mopy/bash/l10n/Russian.mo',
    'Mopy/bash/l10n/de.mo', 'Mopy/bash/l10n/pt_opt.mo',
    # The .po's for these were only temporarily on dev, then got renamed
    'Mopy/bash/l10n/sv.mo', 'Mopy/bash/l10n/tr.mo',
    # Manual taglist cleanup (folder naming variants included)
    'Mopy/taglists/Fallout4VR/taglist.yaml',
    'Mopy/taglists/SkyrimVR/taglist.yaml',
    'Mopy/Bash Patches/Enderal/taglist.txt',
    'Mopy/Bash Patches/Fallout3/taglist.txt',
    'Mopy/Bash Patches/FalloutNV/taglist.txt',
]
# Manual globs (Delete wildcards) - poxix paths
_MANUAL_GLOBS = ['Mopy/loot.*', 'Mopy/loot_api.*']
# Manual recursive directory removals (RMDir /r) - poxix paths
_MANUAL_RMDIR_RECURSIVE = ['Mopy/redist']
# Manual empty-directory removals (RMDir) - poxix paths
_MANUAL_RMDIR_EMPTY = []

def _generate_removefiles_macro(tracked_files, untracked_files,
        macro_name='RemoveOldFiles', path_var='${Path}'):
    untracked_mopy = {p for p in untracked_files if p.startswith('Mopy/')}
    delete_exact_parts = {tuple(p.split('/')) for p in chain(
        untracked_mopy, _MANUAL_EXACT_REMOVALS)}
    rmdir_empty = {tuple(p.split('/')) for p in _MANUAL_RMDIR_EMPTY}
    tracked_dirs, delete_dirs = set(), set() # len is 30, 93
    for paths, out_set in [
            ((p.split('/') for p in tracked_files), tracked_dirs),
            (delete_exact_parts, delete_dirs)]:
        for parts in paths:
            for i in range(2, len(parts)):
                out_set.add(tuple(parts[:i]))
    bytecode_dirs = sorted({*chain(tracked_dirs, delete_dirs, [('Mopy',)])},
        key=lambda t: (len(t), t), reverse=True) # len 111 okayish
    empty_dirs = sorted(set(chain(delete_dirs, rmdir_empty)) - tracked_dirs,
                        key=lambda t: (len(t), t), reverse=True) # len 80 ok
    bytecode_cleanup = chain.from_iterable((
        f'Delete "{path_var}\\{d}\\*.pyc"', f'Delete "{path_var}\\{d}\\*.pyo"',
        f'RMDir /r "{path_var}\\{d}\\__pycache__"',) for d in
        ('\\'.join(x) for x in bytecode_dirs))
    rmdir_recursive = (p.replace('/', '\\') for p in _MANUAL_RMDIR_RECURSIVE)
    delete_globs_paths = sorted(p.replace('/', '\\') for p in _MANUAL_GLOBS)
    dl = chain(('\\'.join(x) for x in sorted(delete_exact_parts,
                    key=lambda t: (len(t), t))), delete_globs_paths)
    out = ['', f'!macro {macro_name} Path', *chain(
        (f'Delete "{path_var}\\{p}"' for p in dl),
        (f'RMDir /r "{path_var}\\{d}"' for d in rmdir_recursive),
        # (f'RMDir "{path_var}\\{d}"' for d in
        #  ('\\'.join(x) for x in rmdir_empty)),
        bytecode_cleanup,
        (f'RMDir "{path_var}\\{d}"' for d in ('\\'.join(x) for x in empty_dirs
                                              ))), '!macroend']
    return out

@contextmanager
def _update_file_version(build_vers, do_commit=False):
    bass_path = MOPY_PATH / 'bash' / 'bass.py'
    tmpdir = Path(tempfile.mkdtemp())
    bck_path = tmpdir / 'bass.py'
    cp(bass_path, bck_path)
    _LOGGER.debug(f'Bumping bass.py version to {build_vers}')
    edit_bass_version(build_vers, _LOGGER)
    if do_commit:
        _LOGGER.debug('Commit of version change requested')
        _WB_REPO.commit_changes(changed_paths=[bass_path], commit_msg=build_vers)
    try:
        yield
    finally:
        if not do_commit:
            cp(bck_path, bass_path)
        rm(tmpdir)

@contextmanager
def _handle_apps_folder():
    tmpdir = Path(tempfile.mkdtemp()) if APPS_PATH.is_dir() else None
    if tmpdir is not None:
        _LOGGER.debug(f'Moving Apps folder to {tmpdir}')
        shutil.move(APPS_PATH, tmpdir)
    APPS_PATH.mkdir(parents=True)
    try:
        yield
    finally:
        if tmpdir is not None:
            for lnk in (tmpdir / 'Apps').glob('*'):
                cp(lnk, APPS_PATH / lnk.name)
            rm(tmpdir)
        else:
            rm(APPS_PATH)

def _check_version(args) -> tuple[str, str]:
    """Generate version strings from the passed parameters. build_vers
    currently is the major version, optionally followed by a minor version
    (either one digit or a twelve digits timestamp, dot separated). For
    file_version see VIProductVersion and VIAddVersionKey "File Version"
    in main.nsi."""
    if (len_sha := args.sha_len) < _min_sha_len:
        _LOGGER.warning(f'SHA length must be at least {_min_sha_len}')
        len_sha = _min_sha_len
    build_vers, vers_tag = args.build_version, args.version_tag
    # check whether we're building a nightly
    if is_nightly := re.fullmatch(r'(\d{3,})\.(\d{12})', build_vers):
        timestamp = is_nightly.group(2)
        file_version = (f'{is_nightly.group(1)}.{timestamp[:4]}.'
                        f'{timestamp[4:8]}.{timestamp[8:12]}')
    elif p_match := re.fullmatch(r'(\d{3,})(\.\d)?', build_vers):
        # '291' ('291.1') will return '291.0.0.0' ('291.1.0.0')
        file_version = f'{p_match.group(1)}{p_match.group(2) or ".0"}.0.0'
    else:
        raise ValueError(f'Invalid build version format: {build_vers}')
    # nsis expects VIProductVersion in 4-part numeric X.X.X.X format - no tags!
    _LOGGER.debug(f'Using file version: {file_version}')
    if is_sha := vers_tag is None: # use the sha of the commit we build from
        vers_tag = _WB_REPO.get_head_hash()[:len_sha]
    else:
        is_sha = re.fullmatch(f'[0-9a-f]{{{len_sha},40}}', vers_tag)
    bass.version_tag = vers_tag
    try:
        ask = '' # check whether the previous build is also a nightly/tagged
        if is_sha:
            if vers_tag in (prev_build := str(next(DIST_PATH.iterdir()))):
                ask = f'{vers_tag} in build: {prev_build}. Continue? [y/N]\n> '
        # check if the current nightly timestamp is the same as in the previous
        # nightly build. Happens when a build is triggered too quickly after
        # the previous one.
        if is_nightly and build_vers in str(next(DIST_PATH.iterdir())):
            ask = 'Current timestamp is equal to the previous build. '\
                  'Continue? [y/N]\n> '
        if ask and (input(ask) or 'n').lower()[0] != 'y':
            raise ValueError(f'{ask.split(" Continue?")[0]} Aborting.')
    except (OSError, StopIteration): # if dist folder doesn't exist or is empty
        pass
    return f'{build_vers}-{vers_tag}' if vers_tag else build_vers, file_version

def _taglists_need_update():
    """Checks if we should update the taglists. Can be overriden via CLI
    argument."""
    last_ml_ver = '0.0'
    try:
        with open(TAGINFO, 'r', encoding='utf-8') as ins:
            last_ml_ver = ins.read()
    except OSError: pass # we'll have to update
    latest_ml_ver = update_taglist.MASTERLIST_VERSION
    if LooseVersion(last_ml_ver) < LooseVersion(latest_ml_ver):
        # LOOT version changed so the syntax probably changed too,
        # update them to be safe
        _LOGGER.info(f'LOOT version changed since the last taglist update (was '
                    f'{last_ml_ver}, now {latest_ml_ver}), updating taglists')
        return True
    _LOGGER.debug(f'LOOT version matches last taglist update (was '
                 f'{last_ml_ver}, now {latest_ml_ver})')
    if not update_taglist.all_taglists_present():
        _LOGGER.info('One or more taglists are missing, updating taglists')
        return True
    _LOGGER.debug('All taglists present, no update needed')
    return False

@contextmanager
def _compile_translations(args):
    """Compile .po files to .mo files and hide the .po files temporarily."""
    _LOGGER.info('Compiling localizations...')
    compile_l10n_level = (logging.DEBUG if args.verbosity == logging.DEBUG else
                          max(args.verbosity, logging.WARNING))
    compile_l10n.main(with_args(args, verbosity=compile_l10n_level))
    hidden_folder = Path(tempfile.mkdtemp())
    for f in L10N_PATH.iterdir():
        if f.suffix in ('.po', '.pot'):
            mv(f, hidden_folder / f.name)
    try:
        yield
    finally:
        for f in hidden_folder.iterdir():
            mv(f, L10N_PATH / f.name)
        rm(hidden_folder)

@contextmanager
def _hold_files(*files: Path):
    tmpdir = Path(tempfile.mkdtemp())
    file_map = {}  # don't calculate paths twice
    for path in files:
        target = tmpdir / path.name
        with suppress(OSError):  # skip file if missing
            mv(path, target)
            file_map[path] = target
    try:
        yield
    finally:
        for orig, target in file_map.items():
            mv(target, orig)
        rm(tmpdir)

def main(args, *, __pys=('.py', '.pyw')):
    setup_log(_LOGGER, args)
    _setup_pyinstaller_logger(args.logfile)
    _LOGGER.info(f'Building on Python {sys.version}')
    # check nightly timestamp is different from previous, get version strings
    vers, file_version = _check_version(args)
    rm(DIST_PATH)
    tracked = _WB_REPO.get_tracked_paths(1)
    to_install = _filter_tracked(tracked)
    with (_handle_apps_folder(), _compile_translations(args),
          _update_file_version(vers, args.commit)):
        # create distributable directory
        DIST_PATH.mkdir(parents=True, exist_ok=True)
        # Copy the license so it's included in the built releases
        license_real = ROOT_PATH / 'LICENSE.md'
        license_temp = MOPY_PATH / 'LICENSE.md'
        try:
            cp(license_real, license_temp)
            # Check if we need to update the LOOT taglists
            if args.force_tl_update or _taglists_need_update():
                update_taglist.main(with_args(args,
                    masterlist_version=update_taglist.MASTERLIST_VERSION))
                # Remember the last LOOT version we generated taglists for
                with TAGINFO.open('w', encoding='utf-8') as out:
                    out.write(update_taglist.MASTERLIST_VERSION)
            if args.manual:
                _LOGGER.info('Creating python source distributable...')
                _pack_manual(vers, to_install)
            if _NOT_WINDOWS:
                _LOGGER.info('Non-Windows OS detected, skipping '
                             'standalone and installer distributables.')
                return
            if not args.standalone and not args.installer:
                return
            to_install = {f for f in to_install if not f.endswith(__pys)}
            with _build_executable():
                if args.standalone:
                    _LOGGER.info('Creating standalone distributable...')
                    _pack_standalone(vers, to_install)
                if args.installer:
                    _LOGGER.info('Creating installer distributable...')
                    _pack_installer(args.nsis, vers, file_version, to_install)
        finally:
            # Clean up the temp copy of the license
            rm(license_temp)

if __name__ == '__main__':
    temp_desc = __doc__
    if _NOT_WINDOWS:
        temp_desc += '\n\n' + '\n'.join(textwrap.wrap(
            'NOTE: On operating systems besides Windows, only building of '
            'source distributables is supported right now.', width=80))
    run_script(main, temp_desc, _LOGFILE, custom_setup=_setup_build_parser)
