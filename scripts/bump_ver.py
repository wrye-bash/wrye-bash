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
"""Bump the various version numbers in Wrye Bash."""
import logging
import os
import re
import sys

import pyfiglet
from helpers.utils import MOPY_PATH, commit_changes, edit_wb_file, \
    open_wb_file, edit_bass_version, mk_logfile, run_script

_LOGGER = logging.getLogger(__name__)
_LOGFILE = mk_logfile(__file__)

sys.path.insert(0, str(MOPY_PATH))
from bash import bass

def _setup_new_version(parser):
    parser.add_argument('new_version', type=str, nargs='?', metavar='ver',
        default=str(int(float(bass.AppVersion)) + 1),
        help='The version to bump to. Defaults to the current version plus '
             'one.')

def main(args):
    new_ver = args.new_version
    _LOGGER.info(f'Bumping Wrye Bash version to {new_ver}')
    files_bumped = []
    # bash/bass.py: Bump the AppVersion definition
    _LOGGER.info('Editing version in bass.py')
    edit_bass_version(new_ver, _LOGGER)
    files_bumped.append(MOPY_PATH / 'bash' / 'bass.py')
    # Docs/*.html: Bump the version footers
    def edit_readme(readme_ma):
        return (f'{readme_ma.group(1)}<div id="version">Wrye Bash '
                f'v{new_ver}</div>')
    _LOGGER.info('Editing version in readmes')
    for readme_name in ('Wrye Bash Advanced Readme.html',
                        'Wrye Bash General Readme.html',
                        'Wrye Bash Technical Readme.html',
                        'Wrye Bash Version History.html'):
        _LOGGER.debug(f'Editing version in readmes: {readme_name}')
        edit_wb_file('Docs', readme_name,
            trigger_regex=re.compile(r'^(\s+)<div id=\"version\">Wrye Bash '
                                     r'v\d+(?:\.\d+)?</div>'),
            edit_callback=edit_readme, logger=_LOGGER)
        files_bumped.append(MOPY_PATH / 'Docs' / readme_name)
    # bash_default.ini and bash_default_russian.ini: Use pyfiglet to generate a
    # new header
    fmt_header = [f';#  {l}' for l in pyfiglet.figlet_format(
        f'Bash.ini {new_ver}', font='big').rstrip().splitlines()]
    _LOGGER.info('Editing version in default INIs')
    for b_ini_name in ('bash_default.ini',
                       'bash_default_Russian.ini'):
        _LOGGER.debug(f'Editing version in default INIs: {b_ini_name}')
        with open_wb_file(b_ini_name, logger=_LOGGER) as bd_ini:
            # Skip the first 6 lines (the header)
            ini_rest = bd_ini.read().splitlines()[6:]
            bd_ini.seek(0, os.SEEK_SET)
            bd_ini.truncate(0)
            bd_ini.write('\n'.join(fmt_header + ini_rest) + '\n')
        files_bumped.append(MOPY_PATH / b_ini_name)
    _LOGGER.debug('Writing commit with changed files')
    commit_changes(changed_paths=files_bumped,
        commit_msg=f'Bump Wrye Bash version to {new_ver}')
    _LOGGER.info(f'Version successfully bumped to {new_ver}')

if __name__ == '__main__':
    run_script(main, __doc__, _LOGFILE, _LOGGER,
        custom_setup=_setup_new_version)
