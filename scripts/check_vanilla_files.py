#!/usr/bin/env python2
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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module tests a game definition against all files in the target
directory.

To use, place this script in the Mopy folder, edit the script to import the
desired GameInfo class, and the test path to the desired location.

Requires the same python version and depenencies as those to run Wrye Bash."""
## Edit these to your desired values:
game_info_name = 'WSOblivionGameInfo'
# Should be an absolute path
game_path_name = r'C:\Program Files\ModifiableWindowsApps\Oblivion GOTY (PC)\Oblivion GOTY Spanish'

from pprint import pprint
import gettext

# Initialize translations before importing any Bash modules
gettext.NullTranslations().install()
from bash.bolt import Path
import bash.bush as bush

def import_game_type(game_info_name):
    import bash.game as game_init
    import pkgutil
    for importer, modname, ispkg in pkgutil.iter_modules(game_init.__path__):
        if not ispkg: continue # game support modules are packages
        # Equivalent of "from game import <modname>"
        try:
            module = __import__('bash.game',globals(),locals(),[modname],-1)
            game_module = getattr(module, modname)
            return getattr(game_module, game_info_name)
        except (ImportError, AttributeError) as e:
            continue

def get_file_list(test_path):
    if not test_path.isabs():
        test_path = Path.getcwd().join(test_path)
    all_files = set()
    for root, dirs, files in test_path.walk():
        for file in files:
            abs_path = root.join(file)
            rel_path = abs_path.relpath(test_path)
            all_files.add(rel_path)
    return all_files

def main():
    GAME_TYPE = import_game_type(game_info_name)
    if not GAME_TYPE:
        print(f'No game module found with {game_info_name}')
        return
    game_path = Path(game_path_name)
    bush.game = game_info = GAME_TYPE(game_path)
    game_info.init()
    vanilla_files = {Path(x) for x in game_info.vanilla_files}

    test_path = game_path.join(game_info.mods_dir)
    all_files = get_file_list(test_path.join())

    print(f'Files present in {test_path} that are not in vanilla_files:')
    new_files = all_files - vanilla_files
    new_files = {x.s for x in new_files}    # For better console output
    pprint(new_files)
    print()
    print(f'Files that are in vanilla_files that are not in {test_path}')
    missing_files = vanilla_files - all_files
    missing_files = {x.s for x in missing_files}
    pprint(missing_files)

if __name__ == '__main__':
    main()
