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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
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
    commit_changes,  edit_bass_version, cp, mv, rm, run_script, mk_logfile, \
    run_subprocess, download_file, with_args, setup_log

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

# These have to be kept in sync with excludes in macros.nsh (search for
# 'Excludes' in that file)
_IGNORES_MANUAL = {
    '*.log',
    '*.pyc',
    'Mopy/bash.ini',
    'Mopy/bash/tests',
    'Mopy/redist',
}
_IGNORES_STANDALONE = _IGNORES_MANUAL | {
    '*.py',
    '*.pyw',
    '*.pyd',
    '*.bat',
    '*.template',
    'Mopy/bash/basher',
    'Mopy/bash/bosh',
    'Mopy/bash/brec',
    'Mopy/bash/env',
    'Mopy/bash/game',
    'Mopy/bash/gui',
    'Mopy/bash/patcher',
}


sys.path.insert(0, str(MOPY_PATH))
from bash import bass

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
        dest='version',
        help="Build with the nightly release format 'VERSION.TIMESTAMP' "
             "[default].",
    )
    version_group.add_argument(
        '-p',
        '--production',
        action='store_const',
        const=bass.AppVersion,
        dest='version',
        help="Build with the production release format 'VERSION'.",
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
    parser.set_defaults(version=nightly_version)

# PyInstaller thinks it's fine to setup logging on import...
def _setup_pyinstaller_logger(logfile):
    root_logger = logging.getLogger()
    stupid_handler = root_logger.handlers[0]
    stupid_formatter = stupid_handler.formatter
    root_logger.removeHandler(stupid_handler)
    file_handler = logging.FileHandler(logfile)
    file_handler.setFormatter(stupid_formatter)
    logging.getLogger('PyInstaller').addHandler(file_handler)

def _get_version_info(version):
    """Generates version strings from the passed parameter. Returns a string
    used for the 'File Version' property of the built standalone release. For
    example, a version of 291 would with default padding would return
    '291.0.0.0'"""
    production_regex = r'\d{3,}(?:\.\d)?$'
    nightly_regex = r'(\d{3,})\.(\d{12})$'
    version = str(version)
    if re.match(production_regex, version) is not None:
        file_version = f'{version}.0.0.0'
    else:
        ma_version = re.match(nightly_regex, version)
        assert ma_version is not None
        timestamp = ma_version.group(2)
        file_version = (f'{ma_version.group(1)}.{timestamp[:4]}.'
                        f'{timestamp[4:8]}.{timestamp[8:12]}')
    _LOGGER.debug(f'Using file version: {file_version}')
    return file_version

def _pack_7z(dest_7z, *args):
    cmd_7z = [_EXE_7Z, 'a', '-m0=lzma2', '-mx9', dest_7z, 'Mopy/'] + list(args)
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

def _pack_manual(version):
    """ Packages the manual (python source) version. """
    archive_ = DIST_PATH / f'Wrye Bash {version} - Python Source.7z'
    files_to_include = {
        ROOT_PATH / 'Readme.md':        MOPY_PATH / 'Readme.md',
        ROOT_PATH / 'requirements.txt': MOPY_PATH / 'requirements.txt',
        WBSA_PATH / 'bash.ico':         MOPY_PATH / 'bash.ico',
    }
    for orig, target in files_to_include.items():
        cp(orig, target)
    try:
        _pack_7z(archive_, *['-xr!' + a for a in _IGNORES_MANUAL])
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

def _pack_standalone(version):
    """ Packages the standalone version. """
    dest_7z = DIST_PATH / f'Wrye Bash {version} - Standalone Executable.7z'
    _pack_7z(dest_7z, *['-xr!' + a for a in _IGNORES_STANDALONE])

def _pack_installer(nsis_path, version, file_version):
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
    run_subprocess([nsis_path, '/NOCD', f'/DWB_NAME=Wrye Bash {version}',
                    f'/DWB_OUTPUT={DIST_PATH}',
                    f'/DWB_FILEVERSION={file_version}',
                    f'/DWB_CLEAN_MOPY={MOPY_PATH}', script_path], _LOGGER)

@contextmanager
def _update_file_version(version, commit=False):
    bass_path = MOPY_PATH / 'bash' / 'bass.py'
    tmpdir = Path(tempfile.mkdtemp())
    bck_path = tmpdir / 'bass.py'
    cp(bass_path, bck_path)
    _LOGGER.debug(f'Bumping bass.py version to {version}')
    edit_bass_version(version, _LOGGER)
    if commit:
        _LOGGER.debug('Commit of version change requested')
        commit_changes(changed_paths=[bass_path], commit_msg=version)
    try:
        yield
    finally:
        if not commit:
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

def _check_timestamp(build_version):
    """Checks whether the current nightly timestamp is the same as the previous
    nightly build. Returns False if it's the same, True otherwise. Happens when
    a build is triggered too quickly after the previous one."""
    nightly_re = re.compile(r'\d{3,}\.\d{12}')
    # check whether we're building a nightly
    nightly_version = nightly_re.match(build_version)
    try:
        # check whether the previous build is also a nightly
        previous_version = nightly_re.search(str(next(DIST_PATH.iterdir())))
    except (OSError, IndexError):
        # if no output folder exists or nothing exists in output folder
        previous_version = None
    if None not in (nightly_version, previous_version):
        nightly_version = nightly_version.group(0)
        previous_version = previous_version.group(0)
        if nightly_version == previous_version:
            answer = input('Current timestamp is equal to the previous build. '
                           'Continue? [y/N]\n> ')
            if not answer or not answer.lower().startswith('y'):
                return False
    return True

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

def main(args):
    setup_log(_LOGGER, args)
    _setup_pyinstaller_logger(args.logfile)
    rm(DIST_PATH)
    _LOGGER.info(f'Building on Python {sys.version}')
    # check nightly timestamp is different than previous
    if not _check_timestamp(args.version):
        raise OSError('Aborting build due to equal nightly timestamps.')
    with (_handle_apps_folder(), _compile_translations(args),
          _update_file_version(args.version, args.commit)):
        # Get repository files
        version_info = _get_version_info(args.version)
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
                _pack_manual(args.version)
            if _NOT_WINDOWS:
                _LOGGER.info('Non-Windows OS detected, skipping '
                             'standalone and installer distributables.')
                return
            if not args.standalone and not args.installer:
                return
            with _build_executable():
                if args.standalone:
                    _LOGGER.info('Creating standalone distributable...')
                    _pack_standalone(args.version)
                if args.installer:
                    _LOGGER.info('Creating installer distributable...')
                    _pack_installer(args.nsis, args.version, version_info)
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
