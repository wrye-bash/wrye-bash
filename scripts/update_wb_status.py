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
"""Update the latest.json file in the wb_status repository."""

import argparse
import json
import os
import sys

from helpers.utils import CHANGELOGS_PATH, WB_STATUS_PATH, commit_changes

def setup_parser(parser):
    parser.add_argument('new_version', type=str, metavar='ver',
        help='The new version that is to be released.')

def main(args):
    new_ver = args.new_version
    wanted_path = os.path.join(CHANGELOGS_PATH, f'Changelog - {new_ver}.b64')
    try:
        with open(wanted_path, 'r', encoding='utf-8') as ins:
            changelog_b64 = ins.read()
    except FileNotFoundError:
        print(f'Could not find generated changelog. Please run '
              f'generate_changelog.py and ensure it creates a file at '
              f'{wanted_path}', file=sys.stderr)
        sys.exit(1)
    latest_json_path = os.path.join(WB_STATUS_PATH, 'latest.json')
    try:
        with open(latest_json_path, 'rb') as ins:
            latest_old = json.load(ins)
    except FileNotFoundError:
        print('Could not find wb_status repo. Please clone it at the same '
              'level as the wrye-bash repo.', file=sys.stderr)
        sys.exit(2)
    # We have everything we need to construct the new latest.json
    latest_new = {
        'version': new_ver,
        'changes': changelog_b64,
        'downloads': latest_old['downloads'],
    }
    with open(latest_json_path, 'w', encoding='utf-8') as out:
        out.write(json.dumps(latest_new, indent=4) + '\n')
    commit_changes(changed_paths=[latest_json_path],
        commit_msg=f'Update to Wrye Bash v{new_ver}', repo_path=WB_STATUS_PATH)
    print(f'Sucessfully updated wb_status repo for v{new_ver}.')

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    setup_parser(argparser)
    parsed_args = argparser.parse_args()
    main(parsed_args)
