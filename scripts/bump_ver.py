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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Bump the various version numbers in Wrye Bash."""
import argparse
import os
import re
import sys

import pyfiglet
from helpers.utils import MOPY_PATH, commit_changes

sys.path.insert(0, MOPY_PATH)
from bash import bass

def setup_parser(parser):
    parser.add_argument('new_version', type=int, nargs='?', metavar='ver',
        default=int(bass.AppVersion) + 1,
        help='The version to bump to. Defaults to the current version plus '
             'one.')

def open_wb_file(*parts):
    """Open a Wrye Bash source code file relative to the Mopy folder in
    read-write mode."""
    try:
        return open(os.path.join(MOPY_PATH, *parts), 'r+', encoding='utf-8')
    except FileNotFoundError:
        print(f'File {os.path.join(*parts)} not found, bump_ver.py probably '
              f'needs to be updated', file=sys.stderr)
        sys.exit(1)

def edit_wb_file(*parts, trigger_regex: re.Pattern, edit_callback):
    """Edit a Wrye Bash source code file relative to the Mopy folder. Look for
    lines matching trigger_regex and replace them with the result of calling
    edit_callback (with the resulting re.Match object passed to edit_callback
    as an argument)."""
    new_wbpy_lines = []
    with open_wb_file(*parts) as wbpy:
        wbpy_lines = wbpy.read().splitlines()
        for wbpy_line in wbpy_lines:
            if wbpy_ma := trigger_regex.match(wbpy_line):
                new_wbpy_lines.append(edit_callback(wbpy_ma))
            else:
                new_wbpy_lines.append(wbpy_line)
        if wbpy_lines == new_wbpy_lines:
            print(f'Nothing edited in file {os.path.join(*parts)}, '
                  f'bump_ver.py probably needs to be updated', file=sys.stderr)
            sys.exit(1)
        wbpy.seek(0, os.SEEK_SET)
        wbpy.truncate(0)
        wbpy.write('\n'.join(new_wbpy_lines) + '\n')

def main(args):
    new_ver = args.new_version
    files_bumped = []
    # bash/bass.py: Bump the AppVersion definition
    def edit_bass(bass_ma):
        return f"AppVersion = '{new_ver}'{bass_ma.group(1)}"
    edit_wb_file('bash', 'bass.py',
        trigger_regex=re.compile(r"^AppVersion = '\d+'(.+)$"),
        edit_callback=edit_bass)
    files_bumped.append(os.path.join(MOPY_PATH, 'bash', 'bass.py'))
    # Docs/*.html: Bump the version footers
    def edit_readme(readme_ma):
        return (f'{readme_ma.group(1)}<div id="version">Wrye Bash '
                f'v{new_ver}</div>')
    for readme_name in ('Wrye Bash Advanced Readme.html',
                        'Wrye Bash General Readme.html',
                        'Wrye Bash Technical Readme.html',
                        'Wrye Bash Version History.html'):
        edit_wb_file('Docs', readme_name,
            trigger_regex=re.compile(r'^(\s+)<div id=\"version\">Wrye Bash '
                                     r'v\d+</div>'),
            edit_callback=edit_readme)
        files_bumped.append(os.path.join(MOPY_PATH, 'Docs', readme_name))
    # bash_default.ini and bash_default_russian.ini: Use pyfiglet to generate a
    # new header
    fmt_header = [f';#  {l}' for l in pyfiglet.figlet_format(
        f'Bash.ini {new_ver}', font='big').rstrip().splitlines()]
    for b_ini_name in ('bash_default.ini',
                       'bash_default_Russian.ini'):
        with open_wb_file(b_ini_name) as bd_ini:
            # Skip the first 6 lines (the header)
            ini_rest = bd_ini.read().splitlines()[6:]
            bd_ini.seek(0, os.SEEK_SET)
            bd_ini.truncate(0)
            bd_ini.write('\n'.join(fmt_header + ini_rest) + '\n')
        files_bumped.append(os.path.join(MOPY_PATH, b_ini_name))
    commit_changes(changed_paths=files_bumped,
        commit_msg=f'Bump Wrye Bash version to {new_ver}')
    print(f'Version successfully bumped to {new_ver}.')

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    setup_parser(argparser)
    parsed_args = argparser.parse_args()
    main(parsed_args)
