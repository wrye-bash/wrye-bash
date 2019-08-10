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


import argparse
import datetime
import glob
import logging
import os
import shutil
import sys
import tempfile
import time
import zipfile
from contextlib import contextmanager

import pygit2

import _winreg
import install_loot_api
import utils

try:
    import scandir
    _walkdir = scandir.walk
except ImportError:
    _walkdir = os.walk

LOGGER = logging.getLogger(__name__)

SCRIPTS_PATH = os.path.dirname(os.path.abspath(__file__))
LOGFILE = os.path.join(SCRIPTS_PATH, "build.log")
DIST_PATH = os.path.join(SCRIPTS_PATH, u"dist")
ROOT_PATH = os.path.abspath(os.path.join(SCRIPTS_PATH, u".."))
MOPY_PATH = os.path.join(ROOT_PATH, u"Mopy")
APPS_PATH = os.path.join(MOPY_PATH, u"Apps")

sys.path.insert(0, MOPY_PATH)
from bash import bass
try:
    import loot_api
except ImportError:
    loot_api = None

NSIS_VERSION = "3.04"
if sys.platform.lower().startswith("linux"):
    EXE_7z = u"7z"
else:
    EXE_7z = os.path.join(MOPY_PATH, u"bash", u"compiled", u"7z.exe")


class NonRepoAction(object):
    __slots__ = []

    # 'Enum' for options for non-repo files
    MOVE = "MOVE"
    COPY = "COPY"
    NONE = "NONE"


def setup_parser(parser):
    parser.add_argument(
        "-l",
        "--logfile",
        default=LOGFILE,
        help="Where to store the log. [default: {}]".format(utils.relpath(LOGFILE)),
    )
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
    version_group.add_argument(
        "-r",
        "--release",
        dest="version",
        help="Specifies the release number for Wrye Bash that you are packaging.",
    )
    parser.add_argument(
        "-c",
        "--commit",
        action="store_true",
        dest="commit",
        help="Create a commit with the version used to build."
    )
    parser.add_argument(
        "-o",
        "--output",
        default=DIST_PATH,
        dest="output",
        help="Specifies the folder the distributables will be packaged "
        "in [default: {}].".format(utils.relpath(DIST_PATH)),
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
    parser.add_argument(
        "--non-repo",
        default=NonRepoAction.MOVE,
        action="store",
        choices=[NonRepoAction.MOVE, NonRepoAction.COPY, NonRepoAction.NONE],
        help="If non-repository files are detected during packaging of the "
        "*installer* version, the packaging script will deal with them in "
        "the following way: {MOVE} - move the non-repository files out of the "
        "source directory, and restore them after (recommended, default); "
        "{COPY} - make a copy of the repository files into a temporary directory, "
        "then build from there (slower); {NONE} - do nothing, causing those "
        "files to be included in the installer (HIGHLY DISCOURAGED).".format(
            COPY=NonRepoAction.COPY, MOVE=NonRepoAction.MOVE, NONE=NonRepoAction.NONE
        ),
    )
    parser.set_defaults(version=nightly_version)


def get_version_info(version, padding=4):
    """
    Generates version strings from the passed parameter.
    Returns the a string used for the 'File Version' property of the built WBSA.
    For example, a version of 291 would with default padding would return '291.0.0.0'
    """
    v = version.split(u".")
    if len(v) == 2:
        if len(v[1]) == 12 and float(v[1]) >= 201603171733L:  # 2016/03/17 17:33
            v, v1 = v[:1], v[1]
            v.extend((v1[:4], v1[4:8], v1[8:]))
    # If version is too short, pad it with 0's
    abspad = abs(padding)
    delta = abspad - len(v)
    if delta > 0:
        pad = ["0"] * delta
        if padding > 0:
            v.extend(pad)
        else:
            v = pad + v
    # If version is too long, warn and truncate
    if delta < 0:
        LOGGER.warning(
            "The version specified ({}) has too many version pieces."
            " The extra pieces will be truncated.".format(version)
        )
        v = v[:abspad]
    # Verify version pieces are actually integers, as non-integer values will
    # cause much of the 'Details' section of the built exe to be non-existant
    newv = []
    error = False
    for x in v:
        try:
            int(x)
            newv.append(x)
        except ValueError:
            error = True
            newv.append(u"0")
    if error:
        LOGGER.warning(
            "The version specified ({}) does not convert "
            "to integer values.".format(version)
        )
    file_version = u".".join(newv)
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


def real_sys_prefix():
    if hasattr(sys, "real_prefix"):  # running in virtualenv
        return sys.real_prefix
    elif hasattr(sys, "base_prefix"):  # running in venv
        return sys.base_prefix
    else:
        return sys.prefix


def pack_7z(file_list, archive, list_path):
    with open(list_path, "wb") as out:
        for node in sorted(file_list, key=unicode.lower):
            out.write(node)
            out.write("\n")
    cmd_7z = [EXE_7z, "a", "-m0=lzma2", "-mx9", archive, "@%s" % list_path]
    try:
        utils.run_subprocess(cmd_7z, LOGGER, cwd=ROOT_PATH)
    finally:
        rm(list_path)


def get_git_files(version):
    """
    Returns a list of files with paths relative to the Mopy directory, which
    can be used to ensure no non-repo files get included in the installers.
    This function will also print a warning if there are non-committed changes.

    Returns a list of all paths that git tracks plus Mopy/Apps (preserves case).
    """
    repo = pygit2.Repository(ROOT_PATH)
    if any(a is not pygit2.GIT_STATUS_IGNORED for a in repo.status().itervalues()):
        LOGGER.warning("Your repository is dirty (you have uncommitted changes).")
    branch_name = repo.head.shorthand
    if not branch_name.startswith(("rel-", "release-", "nightly")):
        LOGGER.warning(
            "You are building off branch '{}', which does not appear to be "
            "a release branch for version {}".format(branch_name, version)
        )
    else:
        LOGGER.info("Building off branch '{}'".format(branch_name))
    index = pygit2.Index()
    index.read_tree(repo.revparse_single("HEAD").tree)
    files = [
        unicode(os.path.normpath(entry.path))
        for entry in index
        if entry.path.lower().startswith(u"mopy")
        and os.path.isfile(os.path.join(ROOT_PATH, entry.path))
    ]
    # Special case: we want the Apps folder to be included, even though
    # it's not in the repository
    files.append(os.path.join(u"Mopy", u"Apps"))
    return files


def get_non_repo_files(repo_files):
    """
    Return a list of all files in the Mopy folder that should not be
    included in the installer. This list can be used to temporarily
    remove these files prior to running the NSIS scripts.
    """
    non_repo = []
    # Get a list of every directory and file actually present
    mopy_files = []
    mopy_dirs = []
    for root, dirs, files in _walkdir(MOPY_PATH):
        mopy_files.extend((os.path.join(root, x) for x in files))
        mopy_dirs.extend((os.path.join(root, x) for x in dirs))
    mopy_files = (os.path.normpath(x) for x in mopy_files)
    # We can ignore .pyc and .pyo files, since the NSIS scripts skip those
    mopy_files = (
        x for x in mopy_files
        if os.path.splitext(x)[1].lower() not in (u".pyc", u".pyo")
    )
    # We can also ignore Wrye Bash.exe, for the same reason
    mopy_files = (
        x for x in mopy_files if os.path.basename(x).lower() != u"wrye bash.exe"
    )
    # Pick out every file that doesn't belong
    unique_repo_files = set(repo_files)
    for fpath in mopy_files:
        if os.path.relpath(fpath, ROOT_PATH) not in unique_repo_files:
            non_repo.append(fpath)
    mopy_dirs = (os.path.normpath(x) for x in mopy_dirs)
    # Pick out every directory that doesn't contain repo files
    non_repo_dirs = []
    for mopy_dir in mopy_dirs:
        for tracked_file in repo_files:
            tracked_file = os.path.join(ROOT_PATH, tracked_file)
            if tracked_file.lower().startswith(mopy_dir.lower()):
                # It's good to keep
                break
        else:
            # It's not good to keep
            # Insert these at the beginning so they get handled first when
            # relocating
            non_repo_dirs.append(mopy_dir)
    if non_repo_dirs:
        non_repo_dirs.sort(key=unicode.lower)
        parent_dir = os.path.relpath(non_repo_dirs[0], MOPY_PATH)
        parent_dirs, parent_dir = [parent_dir], parent_dir.lower()
        for skip_dir in non_repo_dirs[1:]:
            new_parent = os.path.relpath(skip_dir, MOPY_PATH)
            if new_parent.lower().startswith(parent_dir):
                if new_parent[len(parent_dir)] == os.sep:
                    continue  # subdir keep only the top level dir
            parent_dirs.append(new_parent)
            parent_dir = new_parent.lower()
    else:
        parent_dirs = []
    # Lop off the "mopy/" part
    non_repo = (os.path.relpath(x, MOPY_PATH) for x in non_repo)
    tuple_parent_dirs = tuple(d.lower() + os.sep for d in parent_dirs)
    non_repo = [x for x in non_repo if not x.lower().startswith(tuple_parent_dirs)]
    # Insert parent_dirs at the beginning so they get handled first when relocating
    non_repo = parent_dirs + non_repo
    return non_repo


def move_non_repo_files(file_list, src_path, dst_path):
    """ Moves non-repository files/directories. """
    for path in file_list:
        src = os.path.join(src_path, path)
        dst = os.path.join(dst_path, path)
        dirname = os.path.dirname(dst)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        mv(src, dst)


def make_repo_copy(file_list, tmpdir):
    """
    Create a temporary copy of the necessary repository
    files to have a clean repository for building.
    """
    root_to_nsis = os.path.join(u"scripts", u"build", u"installer")
    orig_nsis = os.path.join(ROOT_PATH, root_to_nsis)
    temp_nsis = os.path.join(tmpdir, root_to_nsis)
    shutil.copytree(orig_nsis, temp_nsis)
    file_list.append(os.path.join(u"Mopy", u"Wrye Bash.exe"))
    for path in file_list:
        src = os.path.join(ROOT_PATH, path)
        dst = os.path.join(tmpdir, path)
        cpy(src, dst)


@contextmanager
def clean_repo(non_repo_action, file_list):
    tmpdir = tempfile.mkdtemp()
    clean_root_path = ROOT_PATH
    non_repo_files = get_non_repo_files(file_list)
    try:
        if non_repo_files:
            LOGGER.warning("Non-repository files are present in your source directory.")
            if non_repo_action == NonRepoAction.MOVE:
                LOGGER.info(
                    "You have chosen to move the non-repository "
                    "files out of the source directory temporarily."
                )
                move_non_repo_files(non_repo_files, MOPY_PATH, tmpdir)
            elif non_repo_action == NonRepoAction.COPY:
                LOGGER.info(
                    "You have chosen to make a temporary clean "
                    "copy of the repository to build with."
                )
                make_repo_copy(file_list, tmpdir)
                clean_root_path = tmpdir
            else:
                LOGGER.warning(
                    "You have chosen to not relocate them. These "
                    "files will be included in the installer!"
                )
                for fname in non_repo_files:
                    LOGGER.warning(fname)
        yield clean_root_path
    finally:
        if non_repo_files and non_repo_action == NonRepoAction.MOVE:
            move_non_repo_files(non_repo_files, tmpdir, MOPY_PATH)
        rm(tmpdir)


def get_nsis_root(cmd_arg):
    """ Finds and returns the nsis root folder. """
    if cmd_arg is not None:
        LOGGER.debug("User provided NSIS path at {}".format(cmd_arg))
        return cmd_arg
    try:
        if _winreg:
            nsis_path = _winreg.QueryValue(_winreg.HKEY_LOCAL_MACHINE, r"Software\NSIS")
            LOGGER.debug("Found system NSIS path at {}".format(nsis_path))
            return nsis_path
    except WindowsError:
        pass
    local_nsis_path = os.path.join(SCRIPTS_PATH, "build", "nsis")
    if not os.path.isdir(local_nsis_path):
        LOGGER.debug("Local NSIS not found at {}".format(local_nsis_path))
        local_build_path = os.path.dirname(local_nsis_path)
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
            local_nsis_path,
        )
        inetc_url = "https://nsis.sourceforge.io/mediawiki/images/c/c9/Inetc.zip"
        inetc_zip = os.path.join(dl_dir, "inetc.zip")
        LOGGER.info("Downloading inetc plugin...")
        LOGGER.debug("Download url: {}".format(inetc_url))
        LOGGER.debug("Download inetc plugin to {}".format(inetc_zip))
        utils.download_file(inetc_url, inetc_zip)
        with zipfile.ZipFile(inetc_zip) as fzip:
            fzip.extract("Plugins/x86-unicode/INetC.dll", local_nsis_path)
        os.remove(inetc_zip)
    return local_nsis_path


def pack_manual(version, file_list, output_dir):
    """ Packages the manual (python source) version. """
    archive = os.path.join(
        output_dir, u"Wrye Bash {} - Python Source.7z".format(version)
    )
    list_path = os.path.join(output_dir, u"manual_list.txt")
    # We want every file for the manual version
    LOGGER.debug("Packaging manual distributable at {}".format(archive))
    file_list = list(file_list)
    root_files_to_include = ["Readme.md", "requirements.txt"]
    for fname in root_files_to_include:
        orig = os.path.join(ROOT_PATH, fname)
        target = os.path.join(MOPY_PATH, fname)
        cpy(orig, target)
        file_list.append(os.path.relpath(target, ROOT_PATH))
    try:
        pack_7z(file_list, archive, list_path)
    finally:
        for fname in root_files_to_include:
            target = os.path.join(MOPY_PATH, fname)
            rm(target)


def build_executable(version, file_version):
    """ Builds the executable. """
    # some paths we'll use
    wbsa = os.path.join(SCRIPTS_PATH, u"build", u"standalone")
    reshacker = os.path.join(wbsa, u"Reshacker.exe")
    reshacker_log = os.path.join(wbsa, u"Reshacker.log")
    upx = os.path.join(wbsa, u"upx.exe")
    icon = os.path.join(wbsa, u"bash.ico")
    manifest = os.path.join(wbsa, u"manifest.template")
    script = os.path.join(wbsa, u"setup.template")
    # for l10n
    msgfmt_src = os.path.join(real_sys_prefix(), u"Tools", u"i18n", u"msgfmt.py")
    pygettext_src = os.path.join(real_sys_prefix(), u"Tools", u"i18n", u"pygettext.py")
    msgfmt_dst = os.path.join(MOPY_PATH, u"bash", u"msgfmt.py")
    pygettext_dst = os.path.join(MOPY_PATH, u"bash", u"pygettext.py")
    # output folders/files
    exe = os.path.join(MOPY_PATH, u"Wrye Bash.exe")
    setup = os.path.join(MOPY_PATH, u"setup.py")
    dist = os.path.join(MOPY_PATH, u"dist")
    # check for build requirements
    for fpath in (script, manifest):
        if not os.path.isfile(fpath):
            raise IOError("Could not find '{}', aborting packaging.".format(fpath))
    # Read in the manifest file
    with open(manifest, "r") as man:
        manifest = '"""\n' + man.read() + '\n"""'
    # Include the game package and subpackages (because py2exe wont
    # automatically detect these)
    packages = "'bash.game'"  # notice the double quotes
    try:
        # Ensure comtypes is generated, so the required files for wx.lib.iewin
        # will get pulled in by py2exe
        LOGGER.info("Generating comtypes...")
        import wx
        import wx.lib.iewin

        # Write the setup script
        with open(script, "r") as ins:
            script = ins.read()
        script = script % dict(
            version=version,
            file_version=file_version,
            manifest=manifest,
            upx=None,
            upx_compression="-9",
            packages=packages,
        )
        with open(setup, "w") as out:
            out.write(script)
        # Copy the l10n files over
        cpy(msgfmt_src, msgfmt_dst)
        cpy(pygettext_src, pygettext_dst)
        # Call the setup script
        LOGGER.info("Running py2exe...")
        utils.run_subprocess(
            [sys.executable, setup, "py2exe", "-q"], LOGGER, cwd=MOPY_PATH
        )
        # Copy the exe's to the Mopy folder
        mv(os.path.join(dist, u"Wrye Bash Launcher.exe"), exe)
        # Insert the icon
        LOGGER.info("Adding icon to executable...")
        utils.run_subprocess(
            [
                reshacker,
                "-addoverwrite",
                exe + ",",
                exe + ",",
                icon + ",",
                "ICONGROUP,",
                "MAINICON,",
                "0",
            ],
            LOGGER,
        )
        # Also copy contents of Reshacker.log to the build log
        LOGGER.debug("--- RESHACKER LOG START ---")
        if os.path.isfile(reshacker_log):
            with open(reshacker_log, "r") as ins:
                for line in ins:
                    LOGGER.debug(line)
        LOGGER.debug("---  RESHACKER LOG END  ---")
        # Compress with UPX
        LOGGER.info("Compressing with UPX...")
        utils.run_subprocess([upx, "-9", exe], LOGGER)
    except:
        # On error, don't keep the built exe's
        rm(exe)
        raise
    finally:
        # Clean up left over files
        rm(msgfmt_dst)
        rm(pygettext_dst)
        rm(dist)
        rm(os.path.join(MOPY_PATH, u"build"))
        rm(os.path.join(wbsa, u"ResHacker.ini"))
        rm(reshacker_log)
        rm(setup)
        rm(os.path.join(MOPY_PATH, u"Wrye Bash.upx"))


def pack_standalone(version, file_list, output_dir):
    """ Packages the standalone version. """
    archive = os.path.join(
        output_dir, u"Wrye Bash {} - Standalone Executable.7z".format(version)
    )
    # We do not want any python files with the standalone
    # version, and we need to include the built EXEs
    file_list = [
        x
        for x in file_list
        if os.path.splitext(x)[1].lower()
        not in (u".py", u".pyw", u".pyd", u".bat", u".template")
    ]
    file_list.append(os.path.join(u"Mopy", u"Wrye Bash.exe"))
    list_path = os.path.join(output_dir, u"standalone_list.txt")
    LOGGER.debug("Packaging standalone distributable at {}".format(archive))
    pack_7z(file_list, archive, list_path)


def pack_installer(
    nsis_path, non_repo_action, version, file_list, file_version, output_dir
):
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
    with clean_repo(non_repo_action, file_list) as clean_root_path:
        root_to_mopy = os.path.relpath(MOPY_PATH, ROOT_PATH)
        root_to_script = os.path.relpath(script_path, ROOT_PATH)
        clean_mopy = os.path.join(clean_root_path, root_to_mopy)
        clean_script = os.path.join(clean_root_path, root_to_script)
        # Build the installer
        LOGGER.info("Running makensis.exe...")
        utils.run_subprocess(
            [
                nsis_path,
                "/NOCD",
                "/DWB_NAME=Wrye Bash {}".format(version),
                "/DWB_OUTPUT={}".format(output_dir),
                "/DWB_FILEVERSION={}".format(file_version),
                # pass the correct mopy dir for the script
                # to copy the right files in the installer
                "/DWB_CLEAN_MOPY={}".format(clean_mopy),
                clean_script,
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
            '\nAppVersion = u"{}"'.format(bass.AppVersion),
            '\nAppVersion = u"{}"'.format(version),
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


@contextmanager
def handle_executable(release_version, version_info):
    LOGGER.info("Building executable...")
    build_executable(release_version, version_info)
    try:
        yield
    finally:
        rm(os.path.join(MOPY_PATH, u"Wrye Bash.exe"))


def main(args):
    utils.setup_log(LOGGER, verbosity=args.verbosity, logfile=args.logfile)
    LOGGER.info("Building on Python {}".format(sys.version))
    if sys.version_info[0:3] < (2, 7, 12):
        raise OSError("You must run at least Python 2.7.12 to package Wrye Bash.")
    with handle_apps_folder(), update_file_version(args.version, args.commit):
        # Get repository files
        all_files = get_git_files(args.version)
        # Add the LOOT API binaries to all_files
        loot_dll = os.path.join(u"Mopy", u"loot_api.dll")
        loot_pyd = os.path.join(u"Mopy", u"loot_api.pyd")
        all_files.append(loot_dll)
        all_files.append(loot_pyd)
        version_info = get_version_info(args.version)
        # clean and create distributable directory
        if os.path.exists(args.output):
            shutil.rmtree(args.output)
        try:
            # Sometimes in Windows, if the dist directory was open in Windows
            # Explorer, this will cause an OSError: Accessed Denied, while
            # Explorer is renavigating as a result of the deletion.  So just
            # wait a second and try again.
            os.makedirs(args.output)
        except OSError:
            time.sleep(1)
            os.makedirs(args.output)
        if args.manual:
            LOGGER.info("Creating python source distributable...")
            pack_manual(args.version, all_files, args.output)
        if not args.standalone and not args.installer:
            return
        with handle_executable(args.version, version_info):
            if args.standalone:
                LOGGER.info("Creating standalone distributable...")
                pack_standalone(args.version, all_files, args.output)
            if args.installer:
                LOGGER.info("Creating installer distributable...")
                pack_installer(
                    args.nsis,
                    args.non_repo,
                    args.version,
                    all_files,
                    version_info,
                    args.output,
                )


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    utils.setup_common_parser(argparser)
    setup_parser(argparser)
    if loot_api is None:
        loot_group = argparser.add_argument_group(
            title="loot api arguments",
            description="LOOT API could not be found and will be installed.",
        )
        install_loot_api.setup_parser(loot_group)
    parsed_args = argparser.parse_args()
    open(parsed_args.logfile, "w").close()
    if loot_api is None:
        install_loot_api.main(parsed_args)
        print
    main(parsed_args)
