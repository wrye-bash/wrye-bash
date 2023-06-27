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
import shutil
import stat
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, TypeVar, Any

from .. import bolt
from ..bolt import GPath, Path, deprint

try:
    from send2trash import send2trash, TrashPermissionError
except ImportError:
    # Don't log on Windows, we use IFileOperation there
    if bolt.os_name != 'nt':
        deprint('send2trash missing, recycling will not be possible')
    send2trash = TrashPermissionError = None

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
            found_lgd_games[lgd_game['app_name']] = GPath(
                lgd_game['install_path'])
    except FileNotFoundError:
        pass # Legendary is not installed or no games are installed
    except (json.JSONDecodeError, KeyError):
        deprint('Failed to parse Legendary manifest file', traceback=True)
    return found_lgd_games

# Windows store dataclasses
@dataclass(slots=True)
class _LegacyWinAppVersionInfo:
    full_name: str
    install_location: Path
    mutable_location: Path
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
        main_location: Path) -> list[Path]:
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
        deprint(warn_msg + u' ' +
            _(u'A fallback has been used, but may not be accurate.'))
        return ws_info.get_installed_version()._version
    else:
        deprint(warn_msg + u' ' +
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

# API - Filesystem methods ====================================================
_StrPath = TypeVar('_StrPath', str, os.PathLike[str], covariant=True)
T = TypeVar('T')

class FileOperationType(Enum):
    MOVE = 'MOVE'
    COPY = 'COPY'
    RENAME = 'RENAME'
    DELETE = 'DELETE'

def _retry(operation: Callable[[], T], folder_to_make: Path) -> T:
    """Helper to auto-retry an operation if it fails due to a missing folder."""
    try:
        return operation()
    except FileNotFoundError:
        folder_to_make.makedirs()
        return operation()

def __copy_or_move(sources_dests: dict[Path, Path], rename_on_collision: bool,
                   ask_confirm, parent, move: bool) -> dict[str, str]:
    """Copy files using shutil."""
    # NOTE 1: Using stdlib methods we can't support `allow_undo`
    # NOTE 2: progress dialogs: NOT IMPLEMENTED (so `silent` is ignored)
    # TODO(241): rename_on_collision NOT IMPLEMENTED
    operation_results: dict[str, str] = {}
    for from_path, to_path in sources_dests.items():
        if from_path.is_dir():
            # Copying a directory: check for collision
            if to_path.is_file():
                raise NotADirectoryError(str(to_path))
            elif to_path.is_dir():
                # Collision: merge contents
                sub_items = {
                    from_path.join(sub_item): to_path.join(sub_item)
                    for sub_item in os.listdir(from_path)
                }
                sub_results = __copy_or_move(sub_items, rename_on_collision,
                                             ask_confirm, parent, move)
                if sub_results:
                    # At least some of the sub-items were copied
                    operation_results[os.fspath(from_path)] = os.fspath(to_path)
            else:
                # No Collision, let shutil do the work
                if move:
                    # NOTE: shutil.move: if the destination is a directory, the
                    # source is moved inside the directory. For moving a
                    # directory, this is always the case
                    shutil.move(from_path, to_path.head)
                else:
                    operation = functools.partial(shutil.copytree,
                                                  from_path, to_path)
                    _retry(operation, to_path.head)
                operation_results[os.fspath(from_path)] = os.fspath(to_path)
        elif from_path.is_file():
            # Copying a file: check for collisions if the user wants prompts
            if ask_confirm:
                if to_path.is_file():
                    msg = _('Overwrite %(destination)s with %(source)s?') % {
                        'destination': os.fspath(to_path),
                        'source': os.fspath(from_path)}
                    if not ask_confirm(parent, msg, _('Overwrite file?')):
                        continue
            # Perform the copy/move
            if move:
                # Move already makes intermediate directories
                shutil.move(from_path, to_path)
            else:
                operation = functools.partial(shutil.copy2, from_path, to_path)
                _retry(operation, to_path.head)
            operation_results[os.fspath(from_path)] = os.fspath(to_path)
        else:
            raise FileNotFoundError(os.fspath(from_path))
    return operation_results


def file_operation(operation: FileOperationType,
        sources_dests: dict[_StrPath, _StrPath], allow_undo=True,
        ask_confirm: Callable[[Any, str, str], bool] | None = None,
        rename_on_collision=False, silent=False, parent=None
    ) -> dict[str, str]:
    """file_operation API. Performs a filesystem operation on the specified
    files.

    NOTE: This generic version is still WIP: it doesn't support all the
    optional features, and returns an empty mapping for the results.

    :param operation: One of the FileOperationType enum values, corresponding
        to a move, copy, rename, or delete operation.
    :param sources_dests: A mapping of source paths to destinations. The format
        of destinations depends on the operation:
        - For FileOperationTYpe.DELETE: destinations are ignored, they may be
          anything.
        - For FileOperationType.COPY, MOVE: destinations should be the path to
          the full destination name (not the destination containing directory).
        - For FileOperationType.RENAME: destinations should be file names only,
          without directories.
        Destinations may be anything supporting the os.PathLike interface: str,
        bolt.Path, pathlib.Path, etc).  Parent directories for moves and copies
        will be created for you, without prompting.
    :param allow_undo: If possible, preserve undo information so the operation
        can be undone. For deletions, this will attempt to use the recylce bin.
    :param ask_confirm: show custom prompts if a callback (askYes) is passed.
        The callback takes a parent window, a message, and a title, and returns
        True if the user confirms the action, False otherwise.
    :param rename_on_collision: If True, automatically renames files on a move
        or copy when collisions occur.
    :param silent: If True, do not display progress dialogs.
    :param parent: The parent window for any dialogs.

    :return: A mapping of source file paths to their final new path.  For a
        deletion operation, the final path will be None.
        TOOD: Implement this.
    """
    if not sources_dests: # Nothing to operate on
        return {}
    abspath = os.path.abspath
    if operation is FileOperationType.DELETE:
        # allow_undo: use send2trash if present, otherwise we can't do anything
        #             about this with only stdlib
        # rename_on_collision: NOT IMPLEMENTED
        # silent: no real effect (no progress dialog in the implementation)
        source_paths = [GPath(abspath(x)) for x in sources_dests]
        if ask_confirm:
            message = _('Are you sure you want to permanently delete '
                        'these %(item_cnt)d items?') % {
                'item_cnt': len(source_paths)}
            message += u'\n\n' + u'\n'.join([f' * {x}' for x in source_paths])
            if not ask_confirm(parent, message, _('Delete Multiple Items')):
                return {}
        for to_delete in source_paths:
            if not to_delete.exists(): continue
            # Check if we can even do this (send2trash may not be installed)
            if allow_undo and send2trash:
                try:
                    send2trash(to_delete.s)
                    continue
                except TrashPermissionError:
                    # This happens if we have permission to delete the file,
                    # but do not have permission to create a trash directory
                    # for it on the device it's on - fall back to regular
                    # deletion there
                    deprint(f'Permission to create trash directory denied, '
                            f'permanently deleting the file ({to_delete}) '
                            f'instead', traceback=True)
            if to_delete.is_dir():
                to_delete.rmtree(to_delete.stail)
            else:
                to_delete.remove()
        return {}
    if operation is FileOperationType.RENAME:
        # We use move for renames, so convert the new name to a full path
        srcs_dsts = {
            (source_path := GPath(abspath(source))): source_path.head.join(target)
            for source, target in sources_dests.items()
        }
    else:
        srcs_dsts = {
            GPath(abspath(source)): GPath(abspath(target))
            for source, target in sources_dests.items()
        }
    return __copy_or_move(srcs_dsts, rename_on_collision, ask_confirm, parent,
                          move=(operation is FileOperationType.MOVE))
