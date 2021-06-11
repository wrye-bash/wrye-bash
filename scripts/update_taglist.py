#!/usr/bin/env python2
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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This script generates taglist.yaml files in 'Mopy/taglists' game
subdirectories using the LOOT masterlists."""

import argparse
import logging
import os
import sys

import utils

LOGGER = logging.getLogger(__name__)

MASTERLIST_VERSION = u'0.15'

SCRIPTS_PATH = os.path.dirname(os.path.abspath(__file__))
LOGFILE = os.path.join(SCRIPTS_PATH, u'taglist.log')
MOPY_PATH = os.path.abspath(os.path.join(SCRIPTS_PATH, u'..', u'Mopy'))
sys.path.append(MOPY_PATH)

GAME_DATA = {
    # Maps game name in the Mopy/taglists folder to LOOT repo name
    u'Enderal': u'enderal',
    u'Fallout3': u'fallout3',
    u'FalloutNV': u'falloutnv',
    u'Fallout4': u'fallout4',
    u'Morrowind': u'morrowind',
    u'Oblivion': u'oblivion',
    u'Skyrim': u'skyrim',
    u'SkyrimSE': u'skyrimse',
}

def setup_parser(parser):
    parser.add_argument(
        u'-l',
        u'--logfile',
        default=LOGFILE,
        help=u'Where to store the log. '
             u'[default: {}]'.format(utils.relpath(LOGFILE)),
    )
    parser.add_argument(
        u'-mv',
        u'--masterlist-version',
        default=MASTERLIST_VERSION,
        help=u'Which loot masterlist version to download '
             u'[default: {}].'.format(MASTERLIST_VERSION),
    )

def download_masterlist(repository, version, dl_path):
    url = u'https://raw.githubusercontent.com/loot/{}/v{}/masterlist.yaml'
    url = url.format(repository, version)
    LOGGER.info(u'Downloading {} masterlist...'.format(repository))
    LOGGER.debug(u'Download url: {}'.format(url))
    LOGGER.debug(u'Downloading {} masterlist to {}'.format(
        repository, dl_path))
    utils.download_file(url, dl_path)

def all_taglists_present():
    for game_name, _repository in GAME_DATA.items():
        taglist_path = os.path.join(MOPY_PATH, u'taglists', game_name,
            u'taglist.yaml')
        if not os.path.isfile(taglist_path):
            return False
    return True

def main(verbosity=logging.INFO, logfile=LOGFILE,
         masterlist_version=MASTERLIST_VERSION):
    utils.setup_log(LOGGER, verbosity=verbosity, logfile=logfile)
    for game_name, repository in GAME_DATA.items():
        game_dir = os.path.join(MOPY_PATH, u'taglists', game_name)
        taglist_path = os.path.join(game_dir, u'taglist.yaml')
        if not os.path.exists(game_dir):
            os.makedirs(game_dir)
        download_masterlist(repository, masterlist_version, taglist_path)
        LOGGER.info(u'{} masterlist downloaded.'.format(game_name))

if __name__ == u'__main__':
    argparser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    utils.setup_common_parser(argparser)
    setup_parser(argparser)
    parsed_args = argparser.parse_args()
    open(parsed_args.logfile, u'w').close()
    main(parsed_args.verbosity, parsed_args.logfile,
         parsed_args.masterlist_version)
