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
This script generates taglist.yaml files in 'Mopy/Bashed Patches' game
subdirectories using the LOOT API and masterlists. The script will skip
generating taglists for any games that do not have a folder in
'Mopy/Bashed Patches'
"""

import argparse
import logging
import os
import shutil
import sys
import tempfile

import install_loot_api
import utils

LOGGER = logging.getLogger(__name__)

MASTERLIST_VERSION = "0.14"

SCRIPTS_PATH = os.path.dirname(os.path.abspath(__file__))
LOGFILE = os.path.join(SCRIPTS_PATH, "taglist.log")
MOPY_PATH = os.path.abspath(os.path.join(SCRIPTS_PATH, u"..", u"Mopy"))
sys.path.append(MOPY_PATH)

try:
    import loot_api

    loot_api_installed = True
except ImportError:
    loot_api_installed = False


def setup_parser(parser):
    parser.add_argument(
        "-l",
        "--logfile",
        default=LOGFILE,
        help="Where to store the log. [default: {}]".format(utils.relpath(LOGFILE)),
    )
    parser.add_argument(
        "-mv",
        "--masterlist-version",
        default=MASTERLIST_VERSION,
        help="Which loot masterlist version to "
        "download [default: {}].".format(MASTERLIST_VERSION),
    )


def mock_game_install(master_file_name):
    game_path = tempfile.mkdtemp()
    os.mkdir(os.path.join(game_path, u"Data"))
    open(os.path.join(game_path, u"Data", master_file_name), "a").close()
    return game_path


def download_masterlist(repository, version, dl_path):
    url = "https://raw.githubusercontent.com/loot/{}/v{}/masterlist.yaml".format(
        repository, version
    )
    LOGGER.info("Downloading {} masterlist...".format(repository))
    LOGGER.debug("Download url: {}".format(url))
    LOGGER.debug("Downloading {} masterlist to {}".format(repository, dl_path))
    utils.download_file(url, dl_path)


def main(args):
    import loot_api

    utils.setup_log(LOGGER, verbosity=args.verbosity, logfile=args.logfile)
    LOGGER.debug(
        u"Loaded the LOOT API v{} using wrapper version {}".format(
            loot_api.Version.string(), loot_api.WrapperVersion.string()
        )
    )
    game_data = [
        (u"Oblivion", "Oblivion.esm", "oblivion", loot_api.GameType.tes4),
        (u"Skyrim", "Skyrim.esm", "skyrim", loot_api.GameType.tes5),
        (u"SkyrimSE", "Skyrim.esm", "skyrimse", loot_api.GameType.tes5se),
        (u"Fallout3", "Fallout3.esm", "fallout3", loot_api.GameType.fo3),
        (u"FalloutNV", "FalloutNV.esm", "falloutnv", loot_api.GameType.fonv),
        (u"Fallout4", "Fallout4.esm", "fallout4", loot_api.GameType.fo4),
    ]
    for game_name, master_name, repository, game_type in game_data:
        game_install_path = mock_game_install(master_name)
        masterlist_path = os.path.join(game_install_path, u"masterlist.yaml")
        game_dir = os.path.join(MOPY_PATH, u"Bash Patches", game_name)
        taglist_path = os.path.join(game_dir, u"taglist.yaml")
        if not os.path.exists(game_dir):
            LOGGER.error(
                u"Skipping taglist for {} as its output "
                u"directory does not exist".format(game_name)
            )
            continue
        download_masterlist(repository, args.masterlist_version, masterlist_path)
        loot_api.initialise_locale("")
        loot_game = loot_api.create_game_handle(game_type, game_install_path)
        loot_db = loot_game.get_database()
        loot_db.load_lists(masterlist_path)
        loot_db.write_minimal_list(taglist_path, True)
        LOGGER.info(u"{} masterlist converted.".format(game_name))
        shutil.rmtree(game_install_path)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    utils.setup_common_parser(argparser)
    setup_parser(argparser)
    if not loot_api_installed:
        loot_group = argparser.add_argument_group(
            title="loot api arguments",
            description="LOOT API could not be found and will be installed.",
        )
        install_loot_api.setup_parser(loot_group)
    parsed_args = argparser.parse_args()
    open(parsed_args.logfile, "w").close()
    if not loot_api_installed:
        install_loot_api.main(parsed_args)
        print
    main(parsed_args)
