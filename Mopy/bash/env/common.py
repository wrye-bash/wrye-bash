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
"""Common code used by all platforms, as well as shared helper code used
internally by various platforms. Helper methods and classes must be prefixed
with an underscore so they don't get exposed to the rest of the codebase."""

from __future__ import annotations

__all__ = ['FileOperationType', 'clear_read_only', 'file_operation',
           'get_egs_game_paths', 'get_game_version_fallback',
           'get_legacy_ws_game_paths', 'is_case_sensitive', 'set_cwd']

import datetime
import functools
import json
import os
import shutil
import stat
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import Enum
from functools import partial
from pathlib import Path as PPath ##: To be obsoleted when we refactor Path
from typing import TypeVar, Any

from .. import bolt, bass # bass for _AppLauncher.find_launcher
from ..bolt import deprint, undefinedPath
from ..bolt import Path as _Path
from ..bolt import GPath as _GPath
from ..wbtemp import TempDir

try:
    from send2trash import send2trash, TrashPermissionError
except ImportError:
    # Don't log on Windows, we use IFileOperation there
    if bolt.os_name != 'nt':
        deprint('send2trash missing, recycling will not be possible')
    send2trash = TrashPermissionError = None

try:
    import vdf
except ImportError:
    vdf = None # We will raise an error on boot in bash._import_deps

# Internals ===================================================================
_StrPath = TypeVar('_StrPath', str, os.PathLike[str], covariant=True)

@functools.cache
def _find_legendary_games():
    """Reads the manifests from the third-party Legendary launcher to find all
    games installed via the Epic Games Store."""
    found_lgd_games = {}
    # Look at the XDG location first (Linux only, won't be defined on all Linux
    # systems and obviously not on Windows)
    user_config_path = os.getenv('XDG_CONFIG_HOME')
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
            found_lgd_games[lgd_game['app_name']] = _GPath(
                lgd_game['install_path'])
    except FileNotFoundError:
        pass # Legendary is not installed or no games are installed
    except (json.JSONDecodeError, KeyError):
        deprint('Failed to parse Legendary manifest file', traceback=True)
    return found_lgd_games

##: This typing assumes a VDF root node is always a dict, is that correct?
@functools.cache
def _parse_vdf(vdf_path: _StrPath, *, vdf_root: str) -> dict | None:
    """Parse the specified KeyValues file (.vdf or .acf extension, so generally
    just called 'VDF') and return its root node."""
    try:
        with open(vdf_path, 'rb') as ins:
            # Checked all the VDFs shipped by Steam. Some are ASCII, some are
            # UTF-8, some are UTF-8 with BOM and some are binary data. Let's go
            # with this for now and hope this file will never be binary
            vdf_data = bolt.decoder(ins.read())
    except OSError:
        # Be silent about this, often just means someone transferred a Steam
        # library to another location/computer and some games haven't been
        # reinstalled yet
        return None
    except UnicodeDecodeError:
        deprint(f'Failed to parse {vdf_path}: failed to determine its '
                f'encoding', traceback=True)
        return None
    try:
        # Do this in its own try because vdf does not use a custom error type -
        # don't want to accidentally catch a SyntaxError from decoder(), for
        # example
        parsed_vdf = vdf.loads(vdf_data)
    except SyntaxError:
        deprint(f'Failed to parse {vdf_path}: file has invalid syntax',
            traceback=True)
        return None
    vdf_root = parsed_vdf.get(vdf_root)
    if vdf_root is None:
        deprint(f"Failed to parse {vdf_path}: expected root node "
                f"'{vdf_root}', but got '{next(iter(parsed_vdf))}' "
                f"instead", traceback=True)
        return None
    return vdf_root

def _parse_version_string(full_ver):
    # xSE uses commas in its version fields, so use this 'heuristic'
    split_on = ',' if ',' in full_ver else '.'
    try:
        return tuple([int(part) for part in full_ver.split(split_on)])
    except ValueError:
        return 0, 0, 0, 0

@functools.cache
def _get_steam_manifests(steam_path: _StrPath) -> dict[int, str]:
    """Read the libraryfolders.vdf file used by Steam for storing the Steam
    library folder locations and return the installed app IDs along with the
    paths at which the corresponding manifests are stored."""
    lf_vdf_path = os.path.join(steam_path, 'config', 'libraryfolders.vdf')
    lf_dict = _parse_vdf(lf_vdf_path, vdf_root='libraryfolders')
    if lf_dict is None:
        return {}
    steam_manifests = {}
    for library_folder_info in lf_dict.values():
        if not (library_folder_info and isinstance(library_folder_info, dict)):
            continue
        lf_path = library_folder_info.get('path')
        if not lf_path or not isinstance(lf_path, str): continue
        lf_apps = library_folder_info.get('apps')
        if not lf_apps or not isinstance(lf_apps, dict): continue
        for steam_game_id in lf_apps.keys():
            try:
                steam_manifests[int(steam_game_id)] = os.path.join(lf_path,
                    'steamapps', f'appmanifest_{steam_game_id}.acf')
            except ValueError:
                continue
    return steam_manifests

def _parse_steam_manifests(submod, steam_path: _StrPath | None):
    """Parse the Steam game manifests (appmanifest_*.acf files) for this game
    to determine the paths (if any) this game has been installed at via
    Steam."""
    if not (wanted_game_ids := submod.St.steam_ids) or steam_path is None:
        return []
    steam_manifests = _get_steam_manifests(steam_path)
    steam_paths = []
    for wanted_game_id in wanted_game_ids:
        wanted_manifest_path = steam_manifests.get(wanted_game_id)
        if not wanted_manifest_path: continue
        wanted_game_dict = _parse_vdf(wanted_manifest_path,
            vdf_root='AppState')
        if not wanted_game_dict: continue
        wanted_game_dir = wanted_game_dict.get('installdir')
        if not wanted_game_dir: continue
        steam_paths.append(os.path.join(os.path.dirname(wanted_manifest_path),
            'common', wanted_game_dir))
    return steam_paths

# Windows store dataclasses
@dataclass(slots=True)
class _LegacyWinAppVersionInfo:
    full_name: str
    install_location: _Path
    mutable_location: _Path
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
        main_location: _Path) -> list[_Path]:
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
    games. The version returned by this method is not consistent with the
    usual executable version, so this should only be used in the event that
    a permission error prevents parsing the game file for version
    information. This may happen at a developer's whim: Bethesda's games
    originally could not be parsed, but were later updated so they could be
    parsed. Single use in bush.game_version."""
    warn_msg = _(u'Warning: %(game_file)s could not be parsed for version '
                 u'information.') % {'game_file': test_path}
    if ws_info.installed:
        deprint(f'{warn_msg} ' + _(
            'A fallback has been used, but may not be accurate.'))
        return ws_info.get_installed_version()._version
    else:
        deprint(f'{warn_msg} ' + _(
            'This is not a legacy Windows Store game, your system likely '
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
_T = TypeVar('T')

class FileOperationType(Enum):
    MOVE = 'MOVE'
    COPY = 'COPY'
    RENAME = 'RENAME'
    DELETE = 'DELETE'

def _retry(operation: Callable[..., _T], from_path: _Path, to_path: _Path) -> _T:
    """Helper to auto-retry an operation if it fails due to a missing
    folder."""
    try:
        return operation(from_path, to_path)
    except OSError: # reflink may raise OSError instead of FileNotFoundError
        to_path.head.makedirs()
        return operation(from_path, to_path)

def __copy_or_move(sources_dests: dict[_Path, _Path | Iterable[_Path]],
        rename_on_collision: bool, ask_confirm, parent,
        move: bool) -> dict[str, str]:
    """Copy files using shutil."""
    # NOTE 1: Using stdlib methods we can't support `allow_undo`
    # NOTE 2: progress dialogs: NOT IMPLEMENTED (so `silent` is ignored)
    # TODO(241): rename_on_collision NOT IMPLEMENTED
    operation_results: dict[str, str] = {}
    for src_path, to_paths in sources_dests.items():
        if isinstance(to_paths, _Path):
            to_paths = [to_paths]
        for i, to_path in enumerate(to_paths):
            # If we're moving, all but the last operation needs to be a copy
            should_move = move and i + 1 >= len(to_paths)
            from_path_s = os.fspath(src_path)
            to_path_s = os.fspath(to_path)
            if src_path.is_dir():
                # Copying a directory: check for collision
                if to_path.is_file():
                    raise NotADirectoryError(to_path_s)
                elif to_path.is_dir():
                    # Collision: merge contents
                    sub_items = {
                        src_path.join(sub_item): to_path.join(sub_item)
                        for sub_item in os.listdir(src_path)
                    }
                    sub_results = __copy_or_move(sub_items,
                        rename_on_collision, ask_confirm, parent, should_move)
                    if sub_results:
                        # At least some of the sub-items were copied
                        operation_results[from_path_s] = to_path_s
                else:
                    # No Collision, let shutil do the work
                    if should_move:
                        # NOTE: shutil.move: if the destination is a directory,
                        # the source is moved inside the directory. For moving
                        # a directory, this is always the case
                        shutil.move(src_path, to_path)
                    else:
                        copy_op = partial(shutil.copytree,
                            copy_function=bolt.copy_or_reflink2)
                        _retry(copy_op, src_path, to_path)
                    operation_results[from_path_s] = to_path_s
            elif src_path.is_file():
                # Copying a file: check for collisions if the user wants
                # prompts
                if ask_confirm:
                    if to_path.is_file():
                        msg = _('Overwrite %(destination)s with '
                                '%(source)s?') % {'destination': to_path_s,
                                                  'source': from_path_s}
                        if not ask_confirm(parent, msg, _('Overwrite file?')):
                            continue
                # Perform the copy/move
                _retry(shutil.move if should_move else bolt.copy_or_reflink2,
                       src_path, to_path)
                operation_results[from_path_s] = to_path_s
            else:
                raise FileNotFoundError(from_path_s)
    return operation_results

def file_operation(operation: FileOperationType,
        sources_dests: dict[_StrPath, _StrPath | Iterable[_StrPath]],
        allow_undo=True,
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
          For COPY, the destination may be an iterable, in which case the file
          is copied to multiple targets.
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
        TODO: Implement this.
    """
    if not sources_dests: # Nothing to operate on
        return {}
    gpath_abs = lambda x: _GPath(os.path.abspath(x))
    sources_dests = {gpath_abs(k): v for k, v in sources_dests.items()}
    if operation is FileOperationType.DELETE:
        # allow_undo: use send2trash if present, otherwise we can't do anything
        #             about this with only stdlib
        # rename_on_collision: NOT IMPLEMENTED
        # silent: no real effect (no progress dialog in the implementation)
        if ask_confirm:
            message = _('Are you sure you want to permanently delete '
                        'these %(item_cnt)d items?') % {
                'item_cnt': len(sources_dests)}
            message += '\n\n' + '\n'.join([f' * {x}' for x in sources_dests])
            if not ask_confirm(parent, message, _('Delete Multiple Items')):
                return {}
        for to_delete in sources_dests:
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
            if to_delete.is_dir() and not os.path.islink(to_delete):
                # python would attempt to call rmtree on symlinks to dirs, and
                # raise
                to_delete.rmtree(to_delete.stail)
            else:
                to_delete.remove()
        return {}
    if operation is FileOperationType.RENAME:
        # We use move for renames, so convert the new name to a full path
        srcs_dsts = {src_path: src_path.head.join(target) for src_path, target
                     in sources_dests.items()}
    else:
        srcs_dsts = {src_path: gpath_abs(target) if isinstance(target, (
            str, os.PathLike)) else {*map(gpath_abs, target)} for
                     src_path, target in sources_dests.items()}
    return __copy_or_move(srcs_dsts, rename_on_collision, ask_confirm, parent,
                          move=(operation is FileOperationType.MOVE))

def is_case_sensitive(test_path):
    """Check if the specified path is case-sensitive."""
    with TempDir(base_dir=test_path) as temp_ci_test:
        ci_test_path = PPath(temp_ci_test)
        (ci_test_path / '.wb_case_test').touch()
        (ci_test_path / '.Wb_CaSe_TeSt').touch()
        return len(list(ci_test_path.iterdir())) == 2

# App launchers ---------------------------------------------------------------
def set_cwd(func):
    """Function decorator to switch current working dir."""
    @functools.wraps(func)
    def _switch_dir(self, exe_path: _Path, *args):
        cwd = os.getcwd()
        os.chdir(exe_path.head.s)
        try:
            return func(self, exe_path, *args)
        finally:
            os.chdir(cwd)
    return _switch_dir

class _AppLauncher:
    """Info on launching an App - currently windows/linux only."""
    # the initial path to the app launcher (checked for existence on
    # initialization)
    _app_path: _Path
    _exe_args: tuple # cli for the application
    _display_launcher: bool # whether to display the launcher

    def __init__(self, launcher_path: _Path, cli_args=(),
                 display_launcher=True, *args):
        super().__init__(*args)
        self._app_path = launcher_path
        self._display_launcher = display_launcher
        self._exe_args = cli_args

    @property
    def app_path(self):
        """The path to the app to launch which is not always the _app_path
        (see GameButton/TESCSButton/AppBOSS overrides and avoid adding any)."""
        return self._app_path

    def allow_create(self): #if self._app_path doesn't exist this must be False
        return self._display_launcher

    @classmethod
    def find_launcher(cls, app_exe, app_key, *, root_dirs: tuple | str = tuple(
            map(_GPath, (r'C:\Program Files', r'C:\Program Files (x86)'))),
            subfolders=()):
        """Check a list of paths to locate the app launcher - syscalls, so
        avoid.
        :param app_exe: the (currently exe) app launcher
        :param app_key: the ini key whose value is the path to the exe
        :param root_dirs: the root directories of the exe path
        :param subfolders: subdirs of root_dirs where app is located
        :return: a path to the exe and whether it exists."""
        if app_key is not None and (
                ini_tool_path := bass.get_path_from_ini(app_key.lower())):
            # override with the ini path *even* if it does not exist
            return ini_tool_path, ini_tool_path.exists()
        if app_exe is None:
            return undefinedPath, False
        if isinstance(root_dirs, str):
            # a key to bass dirs done this way to be able to define launchers
            # before bass.dirs is initialized
            root_dirs = [bass.dirs[root_dirs]]
        elif isinstance(root_dirs, _Path):
            root_dirs = [root_dirs]
        if isinstance(subfolders, str):
            subfolders = [(subfolders,)]
        elif isinstance(subfolders, tuple):
            subfolders = [subfolders]
        launcher = _GPath(app_exe)
        for rt in root_dirs:
            for subs in subfolders:
                if (launcher := rt.join(*subs, app_exe)).exists():
                    return launcher, True
        # the last one tested, should not matter because it does not exist
        return launcher, False

    def launch_app(self, exe_path, exe_args):
        raise NotImplementedError
