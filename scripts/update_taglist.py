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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This script generates taglist.yaml files in 'Mopy/taglists' game
subdirectories using the LOOT API and masterlists."""

from __future__ import absolute_import
import argparse
import logging
import os
import shutil
import sys
import tempfile

# The loot module is still required here to handle writing out minimal lists
try:
    import loot
except ImportError:
    if os.name == u'nt':
        raise ImportError(u'libloot-python is missing')
    # On Linux, fake out libloot-python
    class loot(object):
        class GameType(object): # PY3: enum
            tes4 = 0
            tes5 = 1
            tes5se = 2
            fo3 = 3
            fonv = 4
            fo4 = 5
        class Version(object):
            @staticmethod
            def string(): return u'0.15'
        class WrapperVersion(object):
            @staticmethod
            def string(): return u'0.15'
        class LOOTDatabase(object):
            def __init__(self):
                self.masterlist = None
            def load_lists(self, ml):
                self.masterlist = ml
            def write_minimal_list(self, tl, _b):
                shutil.copy2(self.masterlist, tl)
        class GameHandle(object):
            @staticmethod
            def get_database(): return loot.LOOTDatabase()
        @staticmethod
        def create_game_handle(_a, _b): return loot.GameHandle()

import utils

LOGGER = logging.getLogger(__name__)

MASTERLIST_VERSION = u'0.15'

SCRIPTS_PATH = os.path.dirname(os.path.abspath(__file__))
LOGFILE = os.path.join(SCRIPTS_PATH, u'taglist.log')
MOPY_PATH = os.path.abspath(os.path.join(SCRIPTS_PATH, u'..', u'Mopy'))
sys.path.append(MOPY_PATH)

GAME_DATA = [
    ##: libloot-python has not been updated for MW yet
    #(u'Morrowind', u'Morrowind.esm', u'morrowind', loot.GameType.tes3),
    (u'Oblivion', u'Oblivion.esm', u'oblivion', loot.GameType.tes4),
    (u'Skyrim', u'Skyrim.esm', u'skyrim', loot.GameType.tes5),
    (u'SkyrimSE', u'Skyrim.esm', u'skyrimse', loot.GameType.tes5se),
    (u'Fallout3', u'Fallout3.esm', u'fallout3', loot.GameType.fo3),
    (u'FalloutNV', u'FalloutNV.esm', u'falloutnv', loot.GameType.fonv),
    (u'Fallout4', u'Fallout4.esm', u'fallout4', loot.GameType.fo4),
]

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

def mock_game_install(master_file_name):
    game_path = tempfile.mkdtemp()
    os.mkdir(os.path.join(game_path, u'Data'))
    open(os.path.join(game_path, u'Data', master_file_name), u'a').close()
    return game_path

def download_masterlist(repository, version, dl_path):
    url = u'https://raw.githubusercontent.com/loot/{}/v{}/masterlist.yaml'
    url = url.format(repository, version)
    LOGGER.info(u'Downloading {} masterlist...'.format(repository))
    LOGGER.debug(u'Download url: {}'.format(url))
    LOGGER.debug(u'Downloading {} masterlist to {}'.format(
        repository, dl_path))
    utils.download_file(url, dl_path)

def all_taglists_present():
    for game_name, _master_name, _repository, _game_type in GAME_DATA:
        taglist_path = os.path.join(MOPY_PATH, u'taglists', game_name,
            u'taglist.yaml')
        if not os.path.isfile(taglist_path):
            return False
    return True

def main(verbosity=logging.INFO, logfile=LOGFILE,
         masterlist_version=MASTERLIST_VERSION):
    utils.setup_log(LOGGER, verbosity=verbosity, logfile=logfile)
    LOGGER.debug(
        u'Loaded the LOOT API v{} using wrapper version {}'.format(
            loot.Version.string(), loot.WrapperVersion.string()
        )
    )
    for game_name, master_name, repository, game_type in GAME_DATA:
        game_install_path = mock_game_install(master_name)
        masterlist_path = os.path.join(game_install_path, u'masterlist.yaml')
        game_dir = os.path.join(MOPY_PATH, u'taglists', game_name)
        taglist_path = os.path.join(game_dir, u'taglist.yaml')
        if not os.path.exists(game_dir):
            os.makedirs(game_dir)
        download_masterlist(repository, masterlist_version, masterlist_path)
        loot_game = loot.create_game_handle(game_type, game_install_path)
        loot_db = loot_game.get_database()
        loot_db.load_lists(masterlist_path)
        loot_db.write_minimal_list(taglist_path, True)
        LOGGER.info(u'{} masterlist converted.'.format(game_name))
        shutil.rmtree(game_install_path)

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
