#!/usr/bin/env python2
# -*- coding: utf-8 -*-

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

"""
Builds and packages Wrye Bash.

Creates three different types of distributables:
 - Manual     - the python source files, requires Wrye Bash's development
                dependencies to run;
 - Standalone - a portable distributable with the pre-built executable;
 - Installer  - a binary distribution containing a custom installer.

Most steps of the build process can be customized, see the options below.
"""

from __future__ import absolute_import, print_function
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
import _winreg as winreg  # PY3
from contextlib import contextmanager

import pygit2

import utils


LOGGER = logging.getLogger(__name__)

SCRIPTS_PATH = os.path.dirname(os.path.abspath(__file__))
LOGFILE = os.path.join(SCRIPTS_PATH, "build.log")
WBSA_PATH = os.path.join(SCRIPTS_PATH, u"build", u"standalone")
DIST_PATH = os.path.join(SCRIPTS_PATH, u"dist")
ROOT_PATH = os.path.abspath(os.path.join(SCRIPTS_PATH, u".."))
MOPY_PATH = os.path.join(ROOT_PATH, u"Mopy")
APPS_PATH = os.path.join(MOPY_PATH, u"Apps")
NSIS_PATH = os.path.join(SCRIPTS_PATH, u"build", u"nsis")

sys.path.insert(0, MOPY_PATH)
from bash import bass

NSIS_VERSION = "3.04"
if sys.platform.lower().startswith("linux"):
    EXE_7z = u"7z"
else:
    EXE_7z = os.path.join(MOPY_PATH, u"bash", u"compiled", u"7z.exe")


def setup_parser(parser):
    version_group = parser.add_mutually_exclusive_group()
    nightly_version = "{}.{}".format(
        bass.AppVersion.split('.')[0], datetime.datetime.utcnow().strftime("%Y%m%d%H%M")
    )
    version_group.add_argument(
        "-n",
        "--nightly",
        action="store_const",
        const=nightly_version,
        dest="version",
        help="Build with the nightly release format 'VERSION.TIMESTAMP' [default].",
    )
    version_group.add_argument(
        "-p",
        "--production",
        action="store_const",
        const=bass.AppVersion,
        dest="version",
        help="Build with the production release format 'VERSION'.",
    )
    parser.add_argument(
        "-c",
        "--commit",
        action="store_true",
        dest="commit",
        help="Create a commit with the version used to build."
    )
    parser.add_argument(
        "--no-standalone",
        action="store_false",
        dest="standalone",
        help="Don't package a standalone version.",
    )
    parser.add_argument(
        "--no-manual",
        action="store_false",
        dest="manual",
        help="Don't package a manual version.",
    )
    parser.add_argument(
        "--no-installer",
        action="store_false",
        dest="installer",
        help="Don't package an installer version.",
    )
    parser.add_argument(
        "--nsis",
        default=None,
        dest="nsis",
        help="Specify a custom path to the NSIS root folder.",
    )
    parser.set_defaults(version=nightly_version)


def get_version_info(version):
    """
    Generates version strings from the passed parameter.
    Returns the a string used for the 'File Version' property of the built WBSA.
    For example, a version of 291 would with default padding would return '291.0.0.0'
    """
    production_regex = r"\d{3,}$"
    nightly_regex = r"(\d{3,})\.(\d{12})$"
    version = str(version)
    if re.match(production_regex, version) is not None:
        file_version = "{}.0.0.0".format(version)
    else:
        match = re.match(nightly_regex, version)
        assert match is not None
        timestamp = match.group(2)
        file_version = "{}.{}.{}.{}".format(
            match.group(1),
            timestamp[:4],
            timestamp[4:8],
            timestamp[8:12]
        )
    LOGGER.debug("Using file version: {}".format(file_version))
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


def pack_7z(archive, *args):
    cmd_7z = [EXE_7z, "a", "-m0=lzma2", "-mx9", archive, "Mopy/"] + list(args)
    utils.run_subprocess(cmd_7z, LOGGER, cwd=ROOT_PATH)


def get_nsis_root(cmd_arg):
    """ Finds and returns the nsis root folder. """
    if cmd_arg is not None:
        LOGGER.debug("User provided NSIS path at {}".format(cmd_arg))
        return cmd_arg
    try:
        nsis_path = winreg.QueryValue(winreg.HKEY_LOCAL_MACHINE, r"Software\NSIS")
        LOGGER.debug("Found system NSIS path at {}".format(nsis_path))
        return nsis_path
    except WindowsError:
        pass
    if not os.path.isdir(NSIS_PATH):
        LOGGER.debug("Local NSIS not found at {}".format(NSIS_PATH))
        local_build_path = os.path.dirname(NSIS_PATH)
        nsis_url = (
            "https://sourceforge.net/projects/nsis/files/"
            "NSIS%203/{0}/nsis-{0}.zip/download".format(NSIS_VERSION)
        )
        dl_dir = tempfile.mkdtemp()
        nsis_zip = os.path.join(dl_dir, "nsis.zip")
        LOGGER.info("Downloading NSIS {}...".format(NSIS_VERSION))
        LOGGER.debug("Download url: {}".format(nsis_url))
        LOGGER.debug("Download NSIS to {}".format(nsis_zip))
        utils.download_file(nsis_url, nsis_zip)
        with zipfile.ZipFile(nsis_zip) as fzip:
            fzip.extractall(local_build_path)
        os.remove(nsis_zip)
        os.rename(
            os.path.join(local_build_path, "nsis-{}".format(NSIS_VERSION)),
            NSIS_PATH,
        )
        inetc_url = "https://nsis.sourceforge.io/mediawiki/images/c/c9/Inetc.zip"
        inetc_zip = os.path.join(dl_dir, "inetc.zip")
        LOGGER.info("Downloading inetc plugin...")
        LOGGER.debug("Download url: {}".format(inetc_url))
        LOGGER.debug("Download inetc plugin to {}".format(inetc_zip))
        utils.download_file(inetc_url, inetc_zip)
        with zipfile.ZipFile(inetc_zip) as fzip:
            fzip.extract("Plugins/x86-unicode/INetC.dll", NSIS_PATH)
        os.remove(inetc_zip)
    return NSIS_PATH


def pack_manual(version):
    """ Packages the manual (python source) version. """
    archive = os.path.join(
        DIST_PATH, u"Wrye Bash {} - Python Source.7z".format(version)
    )
    join = os.path.join
    files_to_include = {
        join(ROOT_PATH, u"Readme.md"): join(MOPY_PATH, u"Readme.md"),
        join(ROOT_PATH, u"requirements.txt"): join(MOPY_PATH, u"requirements.txt"),
        join(WBSA_PATH, u"bash.ico"): join(MOPY_PATH, u"bash.ico"),
    }
    for orig, target in files_to_include.items():
        cpy(orig, target)
    try:
        pack_7z(archive)
    finally:
        for path in files_to_include.values():
            rm(path)


@contextmanager
def build_executable(version, file_version):
    """ Builds the executable. """
    LOGGER.info("Building executable...")
    build_folder = os.path.join(MOPY_PATH, u"build")
    dist_folder = os.path.join(MOPY_PATH, u"dist")
    setup_orig = os.path.join(WBSA_PATH, u"setup.py")
    setup_target = os.path.join(MOPY_PATH, u"setup.py")
    exe_orig = os.path.join(dist_folder, u"Wrye Bash Launcher.exe")
    exe_target = os.path.join(MOPY_PATH, u"Wrye Bash.exe")
    cpy(setup_orig, setup_target)
    try:
        # Call the setup script
        utils.run_subprocess(
            [sys.executable, setup_target, "py2exe", "--version", file_version],
            LOGGER,
            cwd=MOPY_PATH
        )
        # Copy the exe's to the Mopy folder
        cpy(exe_orig, exe_target)
    finally:
        # Clean up py2exe generated files/folders
        rm(setup_target)
        rm(build_folder)
        rm(dist_folder)
    try:
        yield
    finally:
        rm(exe_target)


def pack_standalone(version):
    """ Packages the standalone version. """
    archive = os.path.join(
        DIST_PATH, u"Wrye Bash {} - Standalone Executable.7z".format(version)
    )
    ignores = (
        "*.py",
        "*.pyw",
        "*.pyd",
        "*.bat",
        "*.template",
        "Mopy/bash/basher",
        "Mopy/bash/bosh",
        "Mopy/bash/game",
        "Mopy/bash/patcher"
    )
    pack_7z(archive, *["-xr!" + a for a in ignores])


def pack_installer(nsis_path, version, file_version):
    """ Packages the installer version. """
    script_path = os.path.join(SCRIPTS_PATH, u"build", u"installer", u"main.nsi")
    if not os.path.exists(script_path):
        raise IOError(
            "Could not find nsis script '{}', aborting "
            "installer creation.".format(script_path)
        )
    nsis_root = get_nsis_root(nsis_path)
    nsis_path = os.path.join(nsis_root, "makensis.exe")
    if not os.path.isfile(nsis_path):
        raise IOError("Could not find 'makensis.exe', aborting installer creation.")
    inetc_path = os.path.join(nsis_root, "Plugins", "x86-unicode", "inetc.dll")
    if not os.path.isfile(inetc_path):
        raise IOError("Could not find NSIS Inetc plugin, aborting installer creation.")
    # Build the installer
    utils.run_subprocess(
        [
            nsis_path,
            "/NOCD",
            "/DWB_NAME=Wrye Bash {}".format(version),
            "/DWB_OUTPUT={}".format(DIST_PATH),
            "/DWB_FILEVERSION={}".format(file_version),
            "/DWB_CLEAN_MOPY={}".format(MOPY_PATH),
            script_path,
        ],
        LOGGER,
    )


@contextmanager
def update_file_version(version, commit=False):
    fname = "bass.py"
    orig_path = os.path.join(MOPY_PATH, "bash", fname)
    tmpdir = tempfile.mkdtemp()
    bck_path = os.path.join(tmpdir, fname)
    cpy(orig_path, bck_path)
    with open(orig_path, "r+") as fopen:
        content = fopen.read().replace(
            "\nAppVersion = u'{}'".format(bass.AppVersion),
            "\nAppVersion = u'{}'".format(version),
        )
        fopen.seek(0)
        fopen.truncate(0)
        fopen.write(content)
        fopen.flush()
        os.fsync(fopen.fileno())
    if commit:
        repo = pygit2.Repository(ROOT_PATH)
        user = repo.default_signature
        parent = [repo.head.target]
        rel_path = os.path.relpath(orig_path, repo.workdir).replace('\\', '/')
        if repo.status_file(rel_path) == pygit2.GIT_STATUS_WT_MODIFIED:
            repo.index.add(rel_path)
            tree = repo.index.write_tree()
            repo.create_commit(
                'HEAD',
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
        LOGGER.debug("Moving Apps folder to {}".format(tmpdir))
        shutil.move(APPS_PATH, tmpdir)
    os.makedirs(APPS_PATH)
    try:
        yield
    finally:
        if apps_present:
            for lnk in glob.glob(os.path.join(tmpdir, u"Apps", u"*")):
                shutil.copy(lnk, os.path.join(MOPY_PATH, u"Apps"))
            rm(tmpdir)
        else:
            rm(APPS_PATH)


# Checks whether the current nightly timestamp
#   is the same as the previous nightly build.
# Returns False if it's the same, True otherwise
# Happens when a build is triggered too quickly
#   after the previous one.
def check_timestamp(build_version):
    nightly_re = re.compile(r"\d{3,}\.\d{12}")
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
            # PY3: raw_input -> input
            answer = raw_input(
                "Current timestamp is equal to the previous build. Continue? [y/N]\n> "
            )
            if not answer or answer.lower().startswith("n"):
                return False
    return True


def main(args):
    utils.setup_log(LOGGER, verbosity=args.verbosity, logfile=LOGFILE)
    # check nightly timestamp is different than previous
    if not check_timestamp(args.version):
        raise OSError("Aborting build due to equal nightly timestamps.")
    with handle_apps_folder(), update_file_version(args.version, args.commit):
        # Get repository files
        version_info = get_version_info(args.version)
        # create distributable directory
        utils.mkdir(DIST_PATH, exists_ok=True)
        if args.manual:
            LOGGER.info("Creating python source distributable...")
            pack_manual(args.version)
        if not args.standalone and not args.installer:
            return
        with build_executable(args.version, version_info):
            if args.standalone:
                LOGGER.info("Creating standalone distributable...")
                pack_standalone(args.version)
            if args.installer:
                LOGGER.info("Creating installer distributable...")
                pack_installer(args.nsis, args.version, version_info)


@contextmanager
def hold_files(*files):
    tmpdir = tempfile.mkdtemp()
    file_map = {}  # don't calculate paths twice
    for path in files:
        target = os.path.join(tmpdir, os.path.basename(path))
        with utils.suppress(OSError):  # skip file if missing
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
        print("Your repository is dirty (you have uncommitted changes).")
    branch_name = repo.head.shorthand
    if not branch_name.startswith(("rel-", "release-", "nightly")):
        print(
            "You are building off branch '{}', which does not "
            "appear to be a release branch".format(branch_name)
        )
    with hold_files(NSIS_PATH):
        # stash everything away
        # - stash modified files
        # - then stash ignored and untracked
        # - unstash modified files
        # and we have a clean repo!
        sig = repo.default_signature
        mod_stashed = False
        unt_stashed = False
        with utils.suppress(KeyError):
            repo.stash(sig, message="Modified")
            mod_stashed = True
        with utils.suppress(KeyError):
            repo.stash(
                sig,
                message="Untracked + Ignored",
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


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    utils.setup_common_parser(argparser)
    setup_parser(argparser)
    parsed_args = argparser.parse_args()
    print("Building on Python {}".format(sys.version))
    if sys.version_info[0:3] < (2, 7, 12):
        raise OSError("You must run at least Python 2.7.12 to package Wrye Bash.")
    rm(LOGFILE)
    rm(DIST_PATH)
    with clean_repo():
        main(parsed_args)
