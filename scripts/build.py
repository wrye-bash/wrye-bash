#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""
Builds and packages Wrye Bash.

Creates three different types of distributables:
 - Manual     - the python source files, requires Wrye Bash's development
                dependencies to run;
 - Standalone - a portable distributable with the pre-built executable;
 - Installer  - a binary distribution containing a custom installer.

Most steps of the build process can be customized, see the options below.
"""
import argparse
import datetime
import glob
import logging
import os
import re
import shutil
import sys
import tempfile
import zipfile
import winreg
from contextlib import contextmanager, suppress

import pygit2
import PyInstaller.__main__

import update_taglist
import utils
from utils import LooseVersion

LOGGER = logging.getLogger(__name__)

SCRIPTS_PATH = os.path.dirname(os.path.abspath(__file__))
LOGFILE = os.path.join(SCRIPTS_PATH, u'build.log')
TAGINFO = os.path.join(SCRIPTS_PATH, u'taginfo.txt')
WBSA_PATH = os.path.join(SCRIPTS_PATH, u'build', u'standalone')
DIST_PATH = os.path.join(SCRIPTS_PATH, u'dist')
ROOT_PATH = os.path.abspath(os.path.join(SCRIPTS_PATH, os.pardir))
MOPY_PATH = os.path.join(ROOT_PATH, u'Mopy')
APPS_PATH = os.path.join(MOPY_PATH, u'Apps')
NSIS_PATH = os.path.join(SCRIPTS_PATH, u'build', u'nsis')
TESTS_PATH = os.path.join(MOPY_PATH, u'bash', u'tests')
TAGLISTS_PATH = os.path.join(MOPY_PATH, u'taglists')
IDEA_PATH = os.path.join(ROOT_PATH, u'.idea')
VSCODE_PATH = os.path.join(ROOT_PATH, u'.vscode')

# List of files that should be preserved during the repo cleaning
#  NSIS_PATH, REDIST_PATH: Not tracked, should only be downloaded once
#  TAGLISTS_PATH, TAGINFO: Not tracked since it's specific to each developer,
#                          removing it would update the taglists every time
#  update_taglist.LOGFILE: Removing it breaks the update_taglist script if it's
#                          currently running (duh)
# IDEA_PATH, VSCODE_PATH: Annoying to remove, won't get included anyways and
#                         can break the 'git stash pop'
TO_PRESERVE = [NSIS_PATH, TAGLISTS_PATH, TAGINFO, update_taglist.LOGFILE,
               IDEA_PATH, VSCODE_PATH]

sys.path.insert(0, MOPY_PATH)
from bash import bass

NSIS_VERSION = u'3.08'
if sys.platform.lower().startswith(u'linux'):
    EXE_7z = u'7z'
else:
    EXE_7z = os.path.join(MOPY_PATH, u'bash', u'compiled', u'7z.exe')

def setup_parser(parser):
    version_group = parser.add_mutually_exclusive_group()
    nightly_version = f'{bass.AppVersion.split(u".")[0]}.' \
                      f'{datetime.datetime.utcnow().strftime(u"%Y%m%d%H%M")}'
    version_group.add_argument(
        u'-n',
        u'--nightly',
        action=u'store_const',
        const=nightly_version,
        dest=u'version',
        help=u"Build with the nightly release format 'VERSION.TIMESTAMP' [default].",
    )
    version_group.add_argument(
        u'-p',
        u'--production',
        action=u'store_const',
        const=bass.AppVersion,
        dest=u'version',
        help=u"Build with the production release format 'VERSION'.",
    )
    parser.add_argument(
        u'-c',
        u'--commit',
        action=u'store_true',
        dest=u'commit',
        help=u'Create a commit with the version used to build.'
    )
    parser.add_argument(
        u'--no-standalone',
        action=u'store_false',
        dest=u'standalone',
        help=u"Don't package a standalone version.",
    )
    parser.add_argument(
        u'--no-manual',
        action=u'store_false',
        dest=u'manual',
        help=u"Don't package a manual version.",
    )
    parser.add_argument(
        u'--no-installer',
        action=u'store_false',
        dest=u'installer',
        help=u"Don't package an installer version.",
    )
    parser.add_argument(
        u'--nsis',
        default=None,
        dest=u'nsis',
        help=u'Specify a custom path to the NSIS root folder.',
    )
    parser.add_argument(
        u'-u',
        u'--update-taglists',
        action=u'store_true',
        dest=u'force_tl_update',
        help=u'Forces an update of the bundled taglists.',
    )
    parser.set_defaults(version=nightly_version)

# PyInstaller thinks it's fine to setup logging on import...
def setup_pyinstaller_logger(logfile):
    root_logger = logging.getLogger()
    stupid_handler = root_logger.handlers[0]
    stupid_formatter = stupid_handler.formatter
    root_logger.removeHandler(stupid_handler)
    file_handler = logging.FileHandler(logfile)
    file_handler.setFormatter(stupid_formatter)
    logging.getLogger("PyInstaller").addHandler(file_handler)

def get_version_info(version):
    """
    Generates version strings from the passed parameter.
    Returns the a string used for the 'File Version' property of the built WBSA.
    For example, a version of 291 would with default padding would return '291.0.0.0'
    """
    production_regex = r'\d{3,}(?:\.\d)?$'
    nightly_regex = r'(\d{3,})\.(\d{12})$'
    version = str(version)
    if re.match(production_regex, version) is not None:
        file_version = f'{version}.0.0.0'
    else:
        match = re.match(nightly_regex, version)
        assert match is not None
        timestamp = match.group(2)
        file_version = f'{match.group(1)}.{timestamp[:4]}.{timestamp[4:8]}.' \
                       f'{timestamp[8:12]}'
    LOGGER.debug(f'Using file version: {file_version}')
    return file_version

def rm(node):
    """Removes a file or directory if it exists"""
    if os.path.isfile(node):
        os.remove(node)
    elif os.path.isdir(node):
        shutil.rmtree(node)

def mv(node, dst):
    """Moves a file or directory if it exists"""
    if os.path.exists(node):
        shutil.move(node, dst)

def cpy(src, dst):
    """Moves a file to a destination, creating the target
       directory as needed."""
    if os.path.isdir(src):
        if not os.path.exists(dst):
            os.makedirs(dst)
    else:
        # file
        dstdir = os.path.dirname(dst)
        if not os.path.exists(dstdir):
            os.makedirs(dstdir)
        shutil.copy2(src, dst)

def pack_7z(archive_, *args):
    cmd_7z = [EXE_7z, u'a', u'-m0=lzma2', u'-mx9', archive_, u'Mopy/'] + list(args)
    utils.run_subprocess(cmd_7z, LOGGER, cwd=ROOT_PATH)

def get_nsis_root(cmd_arg):
    """ Finds and returns the nsis root folder. """
    if cmd_arg is not None:
        LOGGER.debug(f'User provided NSIS path at {cmd_arg}')
        return cmd_arg
    try:
        nsis_path = winreg.QueryValue(winreg.HKEY_LOCAL_MACHINE, r'Software\NSIS')
        LOGGER.debug(f'Found system NSIS path at {nsis_path}')
        return nsis_path
    except WindowsError:
        pass
    if not os.path.isdir(NSIS_PATH):
        LOGGER.debug(f'Local NSIS not found at {NSIS_PATH}')
        local_build_path = os.path.dirname(NSIS_PATH)
        nsis_url = (
            f'https://sourceforge.net/projects/nsis/files/NSIS%203/'
            f'{NSIS_VERSION}/nsis-{NSIS_VERSION}.zip/download'
        )
        dl_dir = tempfile.mkdtemp()
        nsis_zip = os.path.join(dl_dir, u'nsis.zip')
        LOGGER.info(f'Downloading NSIS {NSIS_VERSION}...')
        LOGGER.debug(f'Download url: {nsis_url}')
        LOGGER.debug(f'Download NSIS to {nsis_zip}')
        utils.download_file(nsis_url, nsis_zip)
        with zipfile.ZipFile(nsis_zip) as fzip:
            fzip.extractall(local_build_path)
        os.remove(nsis_zip)
        os.rename(
            os.path.join(local_build_path, f'nsis-{NSIS_VERSION}'),
            NSIS_PATH,
        )
    return NSIS_PATH

def pack_manual(version):
    """ Packages the manual (python source) version. """
    archive_ = os.path.join(DIST_PATH,
                            f'Wrye Bash {version} - Python Source.7z')
    join = os.path.join
    files_to_include = {
        join(ROOT_PATH, u'Readme.md'): join(MOPY_PATH, u'Readme.md'),
        join(ROOT_PATH, u'requirements.txt'): join(MOPY_PATH, u'requirements.txt'),
        join(WBSA_PATH, u'bash.ico'): join(MOPY_PATH, u'bash.ico'),
    }
    ignores = (
        u'Mopy/bash/tests',
        u'Mopy/redist',
    )
    for orig, target in files_to_include.items():
        cpy(orig, target)
    try:
        pack_7z(archive_, *[u'-xr!' + a for a in ignores])
    finally:
        for path in files_to_include.values():
            rm(path)

@contextmanager
def build_executable():
    """ Builds the executable. """
    LOGGER.info(u'Building executable...')
    temp_path = os.path.join(WBSA_PATH, 'temp')
    dist_path = os.path.join(WBSA_PATH, 'dist')
    spec_path = os.path.join(WBSA_PATH, 'pyinstaller.spec')
    orig_exe = os.path.join(dist_path, 'Wrye Bash.exe')
    dest_exe = os.path.join(MOPY_PATH, 'Wrye Bash.exe')
    PyInstaller.__main__.run([
        '--clean',
        '--noconfirm',
        f'--distpath={dist_path}',
        f'--workpath={temp_path}',
        spec_path,
    ])
    # Copy the exe to the Mopy folder
    cpy(orig_exe, dest_exe)
    try:
        yield
    finally:
        rm(dest_exe)

def pack_standalone(version):
    """ Packages the standalone version. """
    archive_ = os.path.join(DIST_PATH,
                            f'Wrye Bash {version} - Standalone Executable.7z')
    ignores = (
        u'*.py',
        u'*.pyw',
        u'*.pyd',
        u'*.bat',
        u'*.template',
        u'Mopy/bash/basher',
        u'Mopy/bash/bosh',
        u'Mopy/bash/brec',
        u'Mopy/bash/env',
        u'Mopy/bash/game',
        u'Mopy/bash/gui',
        u'Mopy/bash/patcher',
        u'Mopy/bash/tests',
        u'Mopy/redist',
    )
    pack_7z(archive_, *[u'-xr!' + a for a in ignores])

def pack_installer(nsis_path, version, file_version):
    """ Packages the installer version. """
    script_path = os.path.join(SCRIPTS_PATH, u'build', u'installer', u'main.nsi')
    if not os.path.exists(script_path):
        raise OSError(f"Could not find nsis script '{script_path}', aborting "
                      f"installer creation.")
    nsis_root = get_nsis_root(nsis_path)
    nsis_path = os.path.join(nsis_root, u'makensis.exe')
    if not os.path.isfile(nsis_path):
        raise OSError(u"Could not find 'makensis.exe', aborting installer creation.")
    # Build the installer
    utils.run_subprocess(
        [
            nsis_path,
            u'/NOCD', f'/DWB_NAME=Wrye Bash {version}',
            f'/DWB_OUTPUT={DIST_PATH}',
            f'/DWB_FILEVERSION={file_version}',
            f'/DWB_CLEAN_MOPY={MOPY_PATH}',
            script_path,
        ],
        LOGGER,
    )

def get_repo_sig(repo):
    """Wrapper around pygit2 that shows a helpful error message to the user if
    their credentials have not been configured yet."""
    try:
        return repo.default_signature
    except KeyError:
        print(u'\n'.join([u'', # empty line before the error
            u'ERROR: You have not set up your git identity yet.',
            u'This is necessary for the git operations that the build script '
            u'uses.',
            u'You can configure them as follows:',
            u'   git config --global user.name "Your Name"',
            u'   git config --global user.email "you@example.com"']))
        sys.exit(1)

@contextmanager
def update_file_version(version, commit=False):
    fname = u'bass.py'
    orig_path = os.path.join(MOPY_PATH, u'bash', fname)
    tmpdir = tempfile.mkdtemp()
    bck_path = os.path.join(tmpdir, fname)
    cpy(orig_path, bck_path)
    with open(orig_path, u'r+') as fopen:
        content = fopen.read().replace(f"\nAppVersion = '{bass.AppVersion}'",
                                       f"\nAppVersion = '{version}'")
        fopen.seek(0)
        fopen.truncate(0)
        fopen.write(content)
        fopen.flush()
        os.fsync(fopen.fileno())
    if commit:
        repo = pygit2.Repository(ROOT_PATH)
        user = get_repo_sig(repo)
        parent = [repo.head.target]
        rel_path = os.path.relpath(orig_path, repo.workdir).replace(u'\\', u'/')
        if repo.status_file(rel_path) == pygit2.GIT_STATUS_WT_MODIFIED:
            repo.index.add(rel_path)
            tree = repo.index.write_tree()
            repo.create_commit(
                u'HEAD',
                user,
                user,
                version,
                tree,
                parent
            )
            repo.index.write()
    try:
        yield
    finally:
        if not commit:
            cpy(bck_path, orig_path)
        rm(tmpdir)

@contextmanager
def handle_apps_folder():
    apps_present = os.path.isdir(APPS_PATH)
    tmpdir = apps_present and tempfile.mkdtemp()
    if apps_present:
        LOGGER.debug(f'Moving Apps folder to {tmpdir}')
        shutil.move(APPS_PATH, tmpdir)
    os.makedirs(APPS_PATH)
    try:
        yield
    finally:
        if apps_present:
            for lnk in glob.glob(os.path.join(tmpdir, u'Apps', u'*')):
                shutil.copy(lnk, os.path.join(MOPY_PATH, u'Apps'))
            rm(tmpdir)
        else:
            rm(APPS_PATH)

def check_timestamp(build_version):
    """Checks whether the current nightly timestamp is the same as the previous
    nightly build. Returns False if it's the same, True otherwise. Happens when
    a build is triggered too quickly after the previous one."""
    nightly_re = re.compile(r'\d{3,}\.\d{12}')
    # check whether we're building a nightly
    nightly_version = nightly_re.match(build_version)
    try:
        # check whether the previous build is also a nightly
        previous_version = nightly_re.search(os.listdir(DIST_PATH)[0])
    except (WindowsError, IndexError):
        # if no output folder exists or nothing exists in output folder
        previous_version = None
    if None not in (nightly_version, previous_version):
        nightly_version = nightly_version.group(0)
        previous_version = previous_version.group(0)
        if nightly_version == previous_version:
            answer = input(
                u'Current timestamp is equal to the previous build. Continue? [y/N]\n> '
            )
            if not answer or answer.lower().startswith(u'n'):
                return False
    return True

def taglists_need_update():
    """Checks if we should update the taglists. Can be overriden via CLI
    argument."""
    last_ml_ver = u'0.0'
    try:
        with open(TAGINFO, u'r') as ins:
            last_ml_ver = ins.read()
    except OSError: pass # we'll have to update
    latest_ml_ver = update_taglist.MASTERLIST_VERSION
    if LooseVersion(last_ml_ver) < LooseVersion(latest_ml_ver):
        # LOOT version changed so the syntax probably changed too,
        # update them to be safe
        LOGGER.info(f'LOOT version changed since the last taglist update (was '
                    f'{last_ml_ver}, now {latest_ml_ver}), updating taglists')
        return True
    LOGGER.debug(f'LOOT version matches last taglist update (was '
                 f'{last_ml_ver}, now {latest_ml_ver})')
    if not update_taglist.all_taglists_present():
        LOGGER.info(u'One or more taglists are missing, updating taglists')
        return True
    LOGGER.debug(u'All taglists present, no update needed')
    return False

def main(args):
    setup_pyinstaller_logger(LOGFILE)
    utils.setup_log(LOGGER, verbosity=args.verbosity, logfile=LOGFILE)
    # check nightly timestamp is different than previous
    if not check_timestamp(args.version):
        raise OSError(u'Aborting build due to equal nightly timestamps.')
    with handle_apps_folder(), update_file_version(args.version, args.commit):
        # Get repository files
        version_info = get_version_info(args.version)
        # create distributable directory
        os.makedirs(DIST_PATH, exist_ok=True)
        # Copy the license so it's included in the built releases
        license_real = os.path.join(ROOT_PATH, u'LICENSE.md')
        license_temp = os.path.join(MOPY_PATH, u'LICENSE.md')
        try:
            cpy(license_real, license_temp)
            # Check if we need to update the LOOT taglists
            if args.force_tl_update or taglists_need_update():
                update_taglist.main()
                # Remember the last LOOT version we generated taglists for
                with open(TAGINFO, u'w') as out:
                    out.write(update_taglist.MASTERLIST_VERSION)
            if args.manual:
                LOGGER.info(u'Creating python source distributable...')
                pack_manual(args.version)
            if not args.standalone and not args.installer:
                return
            with build_executable():
                if args.standalone:
                    LOGGER.info(u'Creating standalone distributable...')
                    pack_standalone(args.version)
                if args.installer:
                    LOGGER.info(u'Creating installer distributable...')
                    pack_installer(args.nsis, args.version, version_info)
        finally:
            # Clean up the temp copy of the license
            rm(license_temp)

@contextmanager
def hold_files(*files):
    tmpdir = tempfile.mkdtemp()
    file_map = {}  # don't calculate paths twice
    for path in files:
        target = os.path.join(tmpdir, os.path.basename(path))
        with suppress(OSError):  # skip file if missing
            mv(path, target)
            file_map[path] = target
    try:
        yield
    finally:
        for orig, target in file_map.items():
            mv(target, orig)
        rm(tmpdir)

@contextmanager
def clean_repo():
    repo = pygit2.Repository(ROOT_PATH)
    if any(v != pygit2.GIT_STATUS_IGNORED for v in repo.status().values()):
        print(u'Your repository is dirty (you have uncommitted changes).')
    branch_name = repo.head.shorthand
    if not branch_name.startswith((u'rel-', u'release-', u'nightly')):
        print(f"You are building off branch '{branch_name}', which does not "
              f"appear to be a release branch")
    with hold_files(*TO_PRESERVE):
        # stash everything away
        # - stash modified files
        # - then stash ignored and untracked
        # - unstash modified files
        # and we have a clean repo!
        sig = get_repo_sig(repo)
        # Not unused, PyCharm is not smart enough to understand suppress
        mod_stashed = False
        unt_stashed = False
        with suppress(KeyError):
            repo.stash(sig, message=u'Modified')
            mod_stashed = True
        with suppress(KeyError):
            repo.stash(
                sig,
                message=u'Untracked + Ignored',
                include_untracked=True,
                include_ignored=True,
            )
            unt_stashed = True
        if mod_stashed:
            repo.stash_pop(index=[mod_stashed, unt_stashed].count(True) - 1)
    try:
        yield
    finally:
        if unt_stashed:
            # if we commit during the yield above
            # we need to update the git index
            # otherwise git will complain about the pop
            repo.status()
            repo.stash_pop(index=0)

if __name__ == u'__main__':
    argparser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    utils.setup_common_parser(argparser)
    setup_parser(argparser)
    parsed_args = argparser.parse_args()
    print(f'Building on Python {sys.version}')
    rm(LOGFILE)
    rm(DIST_PATH)
    with clean_repo():
        main(parsed_args)
