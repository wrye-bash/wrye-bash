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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Common methods used by all platforms."""

from __future__ import annotations

import datetime
import os
import stat
import sys
from dataclasses import dataclass, field

from .. import bolt

__all__ = ['clear_read_only', 'WinAppVersionInfo', 'WinAppInfo',
           'get_game_version_fallback', 'get_win_store_game_paths',
           'real_sys_prefix']

def clear_read_only(filepath): # copied from bolt
    os.chmod(u'%s' % filepath, stat.S_IWUSR | stat.S_IWOTH)

# Windows store dataclasses
@dataclass
class WinAppVersionInfo(object):
    __slots__ = ('full_name', 'mutable_location', 'install_location',
                 '_version', 'install_time', 'entry_point')
    full_name: str
    install_location: bolt.Path
    mutable_location: bolt.Path
    # NOTE: the version parsed here is from the package name or app manifest
    # which do not agree in general with the canonical "game version" found in
    # the executable.  We store it only as a fallback in case the Windows Store
    # changes (again) to where we cannot parse the EXE for the real version.
    _version: str | tuple
    install_time: datetime.datetime
    entry_point: str

@dataclass
class WinAppInfo(object):
    ## There are three names used for Windows Apps:
    ## app_name: The most human readable form
    ##   ex: `BethesdaSofworks.SkyrimSE-PC`
    ## package_name: The application name along with publisher id
    ##   ex: `BethesdaSoftworks.Skyrim_PC_3275kfvn8vcwc`
    ## full_name: The unique app name, includes version and platform
    ##   ex: `BethesdaSoftworks.TESMorrowind-PC_1.0.0.0_x86__3275kfvn8vcwc`
    publisher_name : str = ''
    publisher_id : str = ''
    app_name : str = ''
    versions: dict[str, WinAppVersionInfo] = field(init=False,
                                                   default_factory=dict)

    @property
    def installed(self):
        return bool(self.versions)

    def get_installed_version(self):
        """Get the most recently installed version of the app."""
        if self.installed:
            return sorted(self.versions.values(),
                          key=lambda x: x.install_time)[-1]
        return None

    def __repr__(self):
        return f'WinAppInfo(publisher_name={self.publisher_name}, ' \
               f'publisher_id={self.publisher_id}, app_name={self.app_name},' \
               f' versions:{len(self.versions)})'

def get_game_version_fallback(test_path, ws_info):
    """A fallback method of determining the game version for Windows Store
       games.  The version returned by this method is not consistent with the
       usual executable version, so this should only be used in the even that
       a permission error prevents parsing the game file for version
       information.  This may happen at a developer's whim: Bethesda's games
       originally could not be parsed, but were later updated so they could be
       parsed."""
    warn_msg = _(u'Warning: %(game_file)s could not be parsed for version '
                 u'information.') % {'game_file': test_path}
    if ws_info.installed:
        bolt.deprint(warn_msg + u' ' +
            _(u'A fallback has been used, but may not be accurate.'))
        return ws_info.get_installed_version()._version
    else:
        bolt.deprint(warn_msg + u' ' +
            _(u'This is not a Windows Store game, your system likely needs '
              u'to be configured for file permissions.  See the Wrye Bash '
              u'General Readme for more information.'))
        return 0, 0, 0, 0

def get_win_store_game_paths(submod):
    """Check Windows Store-supplied game paths for the game detection
    file(s)."""
    # delayed import to pull in the right version, and avoid circular imports
    from . import get_win_store_game_info
    app_info = get_win_store_game_info(submod)
    # Select the most recently installed entry
    installed_version = app_info.get_installed_version()
    if installed_version:
        first_location = installed_version.mutable_location
        if submod.Ws.game_language_dirs:
            language_locations = [first_location.join(l)
                                  for l in submod.Ws.game_language_dirs]
            return [p for p in language_locations if p.is_dir()]
        else:
            return [first_location]
    else:
        return []

def real_sys_prefix():
    if hasattr(sys, 'real_prefix'):  # running in virtualenv
        return sys.real_prefix
    elif hasattr(sys, 'base_prefix'):  # running in venv
        return sys.base_prefix
    else:
        return sys.prefix
