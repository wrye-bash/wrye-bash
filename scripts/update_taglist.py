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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This script generates taglist.yaml files in 'Mopy/taglists' game
subdirectories using the LOOT masterlists."""

import logging

from helpers.utils import TAGLISTS_PATH, download_file, run_script, \
    mk_logfile, setup_log

_LOGGER = logging.getLogger(__name__)
_LOGFILE = mk_logfile(__file__)

_GAME_DATA = {
    # Maps game name in the Mopy/taglists folder to LOOT repo name
    'Enderal': 'enderal',
    'Fallout3': 'fallout3',
    'FalloutNV': 'falloutnv',
    'Fallout4': 'fallout4',
    'Fallout4VR': 'fallout4vr',
    'Morrowind': 'morrowind',
    'Oblivion': 'oblivion',
    'Skyrim': 'skyrim',
    'SkyrimSE': 'skyrimse',
    'SkyrimVR': 'skyrimvr',
    'Starfield': 'starfield',
}
MASTERLIST_VERSION = '0.21'

def _download_masterlist(repository, version, dl_path):
    url = (f'https://raw.githubusercontent.com/loot/{repository}/v{version}/'
           f'masterlist.yaml')
    _LOGGER.info(f'Downloading {repository} masterlist...')
    _LOGGER.debug(f'Download url: {url}')
    _LOGGER.debug(f'Downloading {repository} masterlist to {dl_path}')
    download_file(url, dl_path)

def _setup_masterlist(argparser):
    argparser.add_argument(
        '-m',
        '--masterlist-version',
        default=MASTERLIST_VERSION,
        help=f'Which LOOT masterlist version to download [default: '
             f'{MASTERLIST_VERSION}].',
    )

def all_taglists_present():
    for game_name in _GAME_DATA:
        taglist_path = TAGLISTS_PATH / game_name / 'taglist.yaml'
        if not taglist_path.is_file():
            return False
    return True

def main(args):
    setup_log(_LOGGER, args)
    for game_name, repository in _GAME_DATA.items():
        game_dir = TAGLISTS_PATH / game_name
        game_dir.mkdir(parents=True, exist_ok=True)
        taglist_path = game_dir / 'taglist.yaml'
        _download_masterlist(repository, args.masterlist_version, taglist_path)
        _LOGGER.info(f'{game_name} masterlist downloaded.')

if __name__ == '__main__':
    run_script(main, __doc__, _LOGFILE, custom_setup=_setup_masterlist)
