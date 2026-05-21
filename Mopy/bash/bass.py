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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2026 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module just stores some data that all modules have to be able to access
without worrying about circular imports. Currently used to expose layout
and environment issues - do not modify or imitate (ut)."""
import copy
from typing import TYPE_CHECKING, NewType

if TYPE_CHECKING:
    from .bolt import Path
else:
    Path = NewType('Path', str)

# no imports

# The name of the locale we ended up with after localize.setup_locale()
active_locale = None
AppVersion = '316' # an integer or float (except if written from build.py)
is_standalone = False # whether or not we're on standalone
__app_version_tuple = None # cache the version as a tuple (with tag stripped)
version_tag = ''  # e.g., 'RC1' or a commit sha

def get_version_tuple():
    """Return the application version as a tuple of integers."""
    global __app_version_tuple
    if __app_version_tuple is None:
        from .bolt import LooseVersion
        __app_version_tuple = LooseVersion(AppVersion[:-(len(version_tag) + 1)]
            if version_tag else AppVersion) # can't use the tag in comparisons
    return __app_version_tuple

#--Global dictionaries - do _not_ reassign !
# Bash's directories - values are absolute Paths - populated in initDirs()
dirs: dict[str, Path] = {}
# settings read from the Mopy/bash.ini file in _parse_bash_ini()
inisettings = {}

# Settings read from the per-user boot-settings.toml file. Used to house things
# like locale and last chosen game, which we need before we set the game
boot_settings_defaults = {
    'Boot': {
        'locale': None,
        'last_game': None,
    },
}
boot_settings = copy.deepcopy(boot_settings_defaults)

# settings dictionary - belongs to a dedicated settings module below bolt - WIP !
settings: dict = None # bolt.Settings !

# restarting info
is_restarting = False # set to true so Bash is restarted via the exit hook
sys_argv = [] # set to the sys.argv used to start bash - modify when restarting

def update_sys_argv(arg):
    """Replace existing option with new one, option must be in *long* format"""
    if len(arg) == 2:
        try:
            option_index = sys_argv.index(arg[0])
            sys_argv[option_index + 1] = arg[1]
        except ValueError:
            sys_argv.extend(arg)
    else: # boolean switches like '--uac'
        if not arg[0] in sys_argv:
            sys_argv.append(arg[0])

def get_path_from_ini(option_key, dir_key='app'):
    if not (get_value := inisettings.get(option_key)):
        return get_value
    from .bolt import GPath
    return value if (value := GPath(get_value)).is_absolute() else dirs[
        dir_key].join(value)

# Boot stages WIP
mopy_dirs_initialized = bash_dirs_initialized = False
