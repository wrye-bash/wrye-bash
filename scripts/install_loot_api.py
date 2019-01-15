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
Downloads and installs the LOOT Python API in the 'Mopy/' folder.
If necessary, will also download and install MSVC 2015.
"""

import argparse
import logging
import os
import platform
import sys
import tempfile

import _winreg
import utils

LOGGER = logging.getLogger(__name__)

LOOT_API_VERSION = "3.1.1"
LOOT_API_REVISION = "f97de90"

SCRIPTS_PATH = os.path.dirname(os.path.abspath(__file__))
LOGFILE = os.path.join(SCRIPTS_PATH, "loot.log")
MOPY_PATH = os.path.abspath(os.path.join(SCRIPTS_PATH, "..", "Mopy"))

sys.path.append(MOPY_PATH)
try:
    import loot_api
except ImportError:
    loot_api = None


def setup_parser(parser):
    parser.add_argument(
        "-lv",
        "--loot-version",
        default=LOOT_API_VERSION,
        help="Which version of the LOOT "
        "Python API to install [default: {}].".format(LOOT_API_VERSION),
    )
    parser.add_argument(
        "-lr",
        "--loot-revision",
        default=LOOT_API_REVISION,
        help="Which revision of the LOOT "
        "Python API to install [default: {}].".format(LOOT_API_REVISION),
    )
    parser.add_argument(
        "-lm",
        "--loot-msvc",
        help="The url of the msvc redistributable to download and install. "
        "If this is given then this redistributable is always installed "
        "regardless of the current one.",
    )


def is_msvc_redist_installed(major, minor, build):
    if platform.machine().endswith("64"):  # check if os is 64bit
        sub_key = "SOFTWARE\\Microsoft\\VisualStudio\\14.0\\VC\\Runtimes\\x64"
    else:
        sub_key = "SOFTWARE\\Microsoft\\VisualStudio\\14.0\\VC\\Runtimes\\x86"
    LOGGER.debug("Using MSVC registry key: {}".format(sub_key))
    try:
        key_handle = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, sub_key)
        runtime_installed = _winreg.QueryValueEx(key_handle, "Installed")[0]
        installed_major = _winreg.QueryValueEx(key_handle, "Major")[0]
        installed_minor = _winreg.QueryValueEx(key_handle, "Minor")[0]
        installed_build = _winreg.QueryValueEx(key_handle, "Bld")[0]
        if runtime_installed != 0:
            msg = "Found MSVC Redistributable version {0}.{1}.{2}".format(
                installed_major, installed_minor, installed_build
            )
            LOGGER.info(msg)
        return (
            runtime_installed != 0
            and installed_major >= major
            and installed_minor >= minor
            and installed_build >= build
        )
    except WindowsError as exc:
        LOGGER.debug("WindowsError during MSVC registry search: " + str(exc))
        return False


def install_msvc_redist(dl_dir, url=None):
    if url is None:
        url = (
            "https://download.microsoft.com/download/6/A/A/"
            "6AA4EDFF-645B-48C5-81CC-ED5963AEAD48/vc_redist.x86.exe"
        )
    LOGGER.info("Downloading MSVC Redist...")
    LOGGER.debug("Download url: {}".format(url))
    dl_file = os.path.join(dl_dir, "vc_redist.exe")
    LOGGER.debug("Downloading MSVC Redist to {}".format(dl_file))
    utils.download_file(url, dl_file)
    LOGGER.info("Installing the MSVC redistributable...")
    command = [dl_file, "/quiet"]
    utils.run_subprocess(command, LOGGER)
    os.remove(dl_file)


def is_loot_api_installed(version, revision):
    return (
        loot_api is not None
        and loot_api.WrapperVersion.string() == version
        and loot_api.WrapperVersion.revision == revision
    )


def install_loot_api(version, revision, dl_dir, destination_path):
    url = (
        "https://github.com/loot/loot-api-python/releases/"
        "download/{0}/loot_api_python-{0}-0-g{1}_master-win32.7z".format(
            version, revision
        )
    )
    archive_path = os.path.join(dl_dir, "loot_api.7z")
    seven_zip_folder = os.path.join(MOPY_PATH, "bash", "compiled")
    seven_zip_path = os.path.join(seven_zip_folder, "7z.exe")
    loot_api_dll = os.path.join(destination_path, "loot_api.dll")
    loot_api_pyd = os.path.join(destination_path, "loot_api.pyd")
    if os.path.exists(loot_api_dll):
        os.remove(loot_api_dll)
    if os.path.exists(loot_api_pyd):
        os.remove(loot_api_pyd)
    LOGGER.info("Downloading LOOT API Python wrapper...")
    LOGGER.debug("Download url: {}".format(url))
    LOGGER.debug("Downloading LOOT API Python wrapper to {}".format(archive_path))
    utils.download_file(url, archive_path)
    LOGGER.info(
        "Extracting LOOT API Python wrapper to " + utils.relpath(destination_path)
    )
    command = [
        seven_zip_path,
        "e",
        archive_path,
        "-y",
        "-o" + destination_path,
        "*/loot_api.dll",
        "*/loot_api.pyd",
    ]
    utils.run_subprocess(command, LOGGER)
    os.remove(archive_path)


def main(args):
    utils.setup_log(LOGGER, verbosity=args.verbosity, logfile=args.logfile)
    download_dir = tempfile.mkdtemp()
    # if url is given in command line, always dl and install
    if not is_msvc_redist_installed(14, 0, 24215) or args.loot_msvc is not None:
        install_msvc_redist(download_dir, args.loot_msvc)
    if is_loot_api_installed(args.loot_version, args.loot_revision):
        LOGGER.info(
            "Found LOOT API wrapper version {}.{}".format(
                args.loot_version, args.loot_revision
            )
        )
    else:
        install_loot_api(args.loot_version, args.loot_revision, download_dir, MOPY_PATH)
    os.rmdir(download_dir)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    utils.setup_common_parser(argparser)
    argparser.add_argument(
        "-l",
        "--logfile",
        default=LOGFILE,
        help="Where to store the log. [default: {}]".format(utils.relpath(LOGFILE)),
    )
    setup_parser(argparser)
    parsed_args = argparser.parse_args()
    open(parsed_args.logfile, "w").close()
    main(parsed_args)
