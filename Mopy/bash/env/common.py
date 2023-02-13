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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Common code used by all platforms, as well as shared helper code used
internally by various platforms. Helper methods and classes must be prefixed
with an underscore so they don't get exposed to the rest of the codebase."""

from __future__ import annotations

import datetime
import functools
import json
import os
import stat
from dataclasses import dataclass, field

from .. import bolt

# Internals ===================================================================
@functools.cache
def _find_legendary_games():
    """Reads the manifests from the third-party Legendary launcher to find all
    games installed via the Epic Games Store."""
    found_lgd_games = {}
    # Look at the XDG location first (Linux only, won't be defined on all Linux
    # systems and obviously not on Windows)
    user_config_path = os.environ.get('XDG_CONFIG_HOME')
    if not user_config_path:
        # Use the fallback location (which exists on Windows as well, and so is
        # the only location used there)
        user_config_path = os.path.join(os.path.expanduser('~'), '.config')
    lgd_installed_path = os.path.join(user_config_path, 'legendary',
        'installed.json')
    try:
        with open(lgd_installed_path, 'r', encoding='utf-8') as ins:
            lgd_installed_data = json.load(ins)
        for lgd_game in lgd_installed_data.values():
            found_lgd_games[lgd_game['app_name']] = bolt.GPath(
                lgd_game['install_path'])
    except FileNotFoundError:
        pass # Legendary is not installed or no games are installed
    except (json.JSONDecodeError, KeyError):
        bolt.deprint('Failed to parse Legendary manifest file', traceback=True)
    return found_lgd_games

# Windows store dataclasses
@dataclass(slots=True)
class _LegacyWinAppVersionInfo:
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
class _LegacyWinAppInfo:
    # There are three names used for Windows Apps:
    # app_name: The most human readable form
    #   ex: `BethesdaSofworks.SkyrimSE-PC`
    # package_name: The application name along with publisher id
    #   ex: `BethesdaSoftworks.Skyrim_PC_3275kfvn8vcwc`
    # full_name: The unique app name, includes version and platform
    #   ex: `BethesdaSoftworks.TESMorrowind-PC_1.0.0.0_x86__3275kfvn8vcwc`
    legacy_publisher_name : str = ''
    publisher_id : str = ''
    app_name : str = ''
    versions: dict[str, _LegacyWinAppVersionInfo] = field(init=False,
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
        return (f'_LegacyWinAppInfo('
                f'legacy_publisher_name={self.legacy_publisher_name},'
                f'publisher_id={self.publisher_id}, app_name={self.app_name}, '
                f'versions=<{len(self.versions)} version(s)>)')

def _get_language_paths(language_dirs: list[str],
        main_location: bolt.Path) -> list[bolt.Path]:
    """Utility function that checks a list of language dirs for a game and, if
    that list isn't empty, joins a main location path with all those dirs and
    returns a list of all such present language paths. If the list is empty, it
    just returns a list containing the main location path."""
    if language_dirs:
        language_locations = [main_location.join(l) for l in language_dirs]
        return [p for p in language_locations if p.is_dir()]
    else:
        return [main_location]

# API - Functions =============================================================
def clear_read_only(filepath): # copied from bolt
    os.chmod(f'{filepath}', stat.S_IWUSR | stat.S_IWOTH)

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
            _('This is not a legacy Windows Store game, your system likely '
              'needs to be configured for file permissions. See the Wrye Bash '
              'General Readme for more information.'))
        return 0, 0, 0, 0

def get_legacy_ws_game_paths(submod):
    """Check legacy Windows Store-supplied game paths for the game detection
    file(s)."""
    # Delayed import to pull in the right version, and avoid circular imports
    from . import get_legacy_ws_game_info
    app_info = get_legacy_ws_game_info(submod)
    # Select the most recently installed entry
    installed_version = app_info.get_installed_version()
    if installed_version:
        return _get_language_paths(submod.Ws.ws_language_dirs,
            installed_version.mutable_location)
    else:
        return []

def get_egs_game_paths(submod):
    """Check the Epic Games Store manifests to find if the specified game is
    installed via the EGS and return its install path."""
    if egs_anames := submod.Eg.egs_app_names:
        # Delayed import to pull in the right version
        from . import find_egs_games
        egs_games = find_egs_games()
        for egs_an in egs_anames:
            # Use the first AppName that's present
            if egs_an in egs_games:
                return _get_language_paths(submod.Eg.egs_language_dirs,
                    egs_games[egs_an])
    return []
