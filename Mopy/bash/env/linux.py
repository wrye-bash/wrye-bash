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
"""Encapsulates Linux-specific classes and methods."""

import functools
import os
import subprocess
import sys
from collections import deque
from shutil import which

from .common import _AppLauncher, _find_legendary_games, _LegacyWinAppInfo, \
    _parse_steam_manifests, set_cwd, _parse_version_string
# some hiding as pycharm is confused in __init__.py by the import *
from ..bolt import GPath as _GPath
from ..bolt import GPath_no_norm as _GPath_no_norm
from ..bolt import Path as _Path
from ..bolt import deprint as _deprint
from ..exception import EnvError

# API - Constants =============================================================
FO_MOVE = 1
FO_COPY = 2
FO_DELETE = 3
FO_RENAME = 4
FOF_NOCONFIRMMKDIR = 512

# TODO(inf) We should use protontricks instead to launch within the right
#  prefix automatically - that way e.g. xEdit will Just Work(TM)
_WINEPATH = which('wine')

_STRINGS = which('strings')
if not _STRINGS:
    _deprint('strings not found, EXE version reading will not work. Try '
             'installing binutils')

# TaskDialog is Windows-specific, so stub all this out (and raise if TaskDialog
# is used, see below)
TASK_DIALOG_AVAILABLE = False

BTN_OK = BTN_CANCEL = BTN_YES = BTN_NO = None
GOOD_EXITS = (BTN_OK, BTN_YES)

# Internals ===================================================================
def _get_steamuser_path(submod, user_relative_path: str) -> str | None:
    """Helper for retrieving a path relative to a Proton prefix's steamuser
    directory. Also supports older Proton versions (which did not use
    'steamuser', but the actual user's name instead)."""
    if all_steam_ids := submod.St.steam_ids:
        compatdata_path = os.path.realpath(os.path.join(
            submod.gamePath, '..', '..', 'compatdata'))
        for st_id in all_steam_ids:
            # If this path does not exist, the game has not been launched yet
            # and we don't have a Proton prefix to work with
            users_path = os.path.join(compatdata_path, str(st_id), 'pfx',
                'drive_c', 'users')
            if not os.path.exists(users_path):
                continue
            # Newer Proton installations always create with the username
            # 'steamuser', so if that exists we've got it for sure
            candidate_path = os.path.join(users_path, 'steamuser',
                user_relative_path)
            if os.path.exists(candidate_path):
                return candidate_path
            # No good, it was created with some users' actual username. Filter
            # out 'Public', which is always present and does not contain the
            # files we're looking for
            all_user_filenames = [u for u in os.listdir(users_path)
                                  if u.lower() != 'public']
            if len(all_user_filenames) == 1:
                candidate_path = os.path.join(users_path,
                    all_user_filenames[0], user_relative_path)
                return candidate_path
            # More than one username in a Proton prefix? And none of them are
            # 'steamuser'? *Someone* should clean this up
            _deprint(f"Found >1 username ({', '.join(all_user_filenames)}) in "
                     f"a Proton prefix's users directory ({users_path}). You "
                     f"should probably clean this up.")
            for user_filename in all_user_filenames:
                candidate_path = os.path.join(users_path, user_filename,
                    user_relative_path)
                if os.path.exists(candidate_path):
                    # Use the first users' path that exists
                    return candidate_path
    return None

def _get_xdg_path(xdg_var: str) -> _Path | None:
    """Retrieve a path from an XDG environment variable. If no such variable is
    set, fall back to the corresponding legacy path. If that *also* doesn't
    exist, return None - user clearly has a weird, nonstandard Linux system and
    will have to use CLI or bash.ini to set the path."""
    if xdg_val := os.getenv(xdg_var):
        return _GPath(xdg_val)
    home_path = os.path.expanduser('~')
    # For this mapping, see:
    #  - https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
    #  - https://wiki.archlinux.org/title/XDG_user_directories
    return _GPath_no_norm({
        'XDG_CACHE_HOME':      f'{home_path}/.cache',
        'XDG_CONFIG_HOME':     f'{home_path}/.config',
        'XDG_DATA_HOME':       f'{home_path}/.local/share',
        'XDG_DESKTOP_DIR':     f'{home_path}/Desktop',
        'XDG_DOCUMENTS_DIR':   f'{home_path}/Documents',
        'XDG_DOWNLOAD_DIR':    f'{home_path}/Downloads',
        'XDG_MUSIC_DIR':       f'{home_path}/Music',
        'XDG_PICTURES_DIR':    f'{home_path}/Pictures',
        'XDG_PUBLICSHARE_DIR': f'{home_path}/Public',
        'XDG_STATE_HOME':      f'{home_path}/.local/state',
        'XDG_TEMPLATES_DIR':   f'{home_path}/Templates',
        'XDG_VIDEOS_DIR':      f'{home_path}/Videos',
    }.get(xdg_var))

@functools.cache
def _get_steam_path() -> _Path | None:
    """Retrieve the path used by Steam."""
    # Resolve the .steam/root symlink, the user may have moved their Steam
    # install out of the default (.local/share/Steam) location
    try:
        steam_path = os.path.realpath(os.path.expanduser('~/.steam/root'),
            strict=True)
    except OSError:
        return None # Steam path doesn't exist
    return _GPath_no_norm(steam_path)

# API - Functions =============================================================
##: Several of these should probably raise instead
def drive_exists(dir_path: _Path):
    """Check if a drive exists by trying to create a dir."""
    try:
        dir_path.makedirs() # exist_ok=True - will create the directories!
        return True # TODO drive detection in posix - test in linux
    except PermissionError: # as e: # PE on mac
        return False # [Errno 13] Permission denied: '/Volumes/Samsung_T5'

@functools.cache
def find_egs_games():
    # No EGS on Linux, so use only Legendary
    return _find_legendary_games()

def get_registry_path(_subkey, _entry, _test_path_callback):
    return None # no registry on Linux

def get_gog_game_paths(_submod):
    ##: Implement reading from Heroic Games launcher (and maybe others like
    # Lutris?)
    return []

def get_disc_game_paths(_submod, _found_steam_paths, _found_gog_paths):
    # We can't detect this on Linux because there's no registry to pull from,
    # users will just have to tell us via -o/bash.ini
    return []

def get_legacy_ws_game_info(_submod):
    return _LegacyWinAppInfo() # no Windows Store on Linux

def get_ws_game_paths(_submod):
    return [] # no Windows Store on Linux

def get_steam_game_paths(submod):
    return [_GPath_no_norm(p) for p in
            _parse_steam_manifests(submod, _get_steam_path())]

def get_personal_path(submod):
    if sys.platform == 'darwin':
        return _GPath(os.path.expanduser('~')), _('Fallback to home dir)')
    if submod.St.steam_ids:
        proton_personal_path = _get_steamuser_path(submod, 'My Documents')
        # Let it blow if this is None - don't create random folders on Linux
        # for Windows games installed via Proton
        return (_GPath(proton_personal_path),
                _('Folder path retrieved via Proton prefix. Launch the game '
                  'through Steam to make sure its Proton prefix is created.'))
    return (_get_xdg_path('XDG_DOCUMENTS_DIR'),
            _('Folder path retrieved via $XDG_DOCUMENTS_DIR (or fallback to '
              '~/Documents)'))

def get_local_app_data_path(submod):
    if sys.platform == 'darwin':
        return _GPath(os.path.expanduser("~/.local/share")), _(
            'Fallback to ~/.local/share)')
    if submod.St.steam_ids:
        # Let it blow if this is None - don't create random folders on Linux
        # for Windows games installed via Proton
        proton_local_app_data_path = _get_steamuser_path(submod,
            os.path.join('AppData', 'Local'))
        return (_GPath(proton_local_app_data_path),
                _('Folder path retrieved via Proton prefix. Launch the game '
                  'through Steam to make sure its Proton prefix is created.'))
    return (_get_xdg_path('XDG_DATA_HOME'),
            _('Folder path retrieved via $XDG_DATA_HOME (or fallback to '
              '~/.local/share)'))

def init_app_links(_apps_dir):
    ##: Rework launchers so that they can work for Linux too
    # The 'shortcuts' concept is hard for users to grasp anyways (remember how
    # many people have trouble setting up a shortcut for QACing using xEdit!),
    # so a better design would be e.g. using our settings dialog to add new
    # launchers, similar to how MO2 does it - scratch that, I'm actually
    # thinking about making this a separate tab to make it *super* easy
    return []

def testUAC(_gameDataPath):
    pass # Noop on Linux

def setUAC(_handle, _uac=True):
    pass # Noop on Linux

def is_uac():
    return False # Not a thing on Linux

@functools.cache
def getJava():
    # Prefer the version indicated by JAVA_HOME
    try:
        java_home = _GPath(os.environ['JAVA_HOME'])
        java_bin_path = java_home.join('bin', 'java')
        if java_bin_path.is_file(): return java_bin_path
    except KeyError: # no JAVA_HOME
        pass
    java_bin_path = which('java') # Otherwise, look through the PATH
    if java_bin_path:
        return _GPath_no_norm(java_bin_path)
    # Fall back to the likely correct path on most distros - but probably
    # Java is missing entirely if which can't find it
    return _GPath('/usr/bin/java')

@functools.cache
def get_file_version(filename, __ignored=((1, 0, 0, 0), (0, 0, 0, 0))):
    ver_candidate = (0, 0, 0, 0)
    if not _STRINGS:
        return ver_candidate
    # get the stringies, separated by newlines
    hexdump = subprocess.getoutput(
        f'"{_STRINGS}" -a -t x -e l "{filename}"').splitlines()
    # grep for fields. When we find one, we get the next line.
    for i, line in enumerate(hexdump):
        if 'FileVersion' in line or 'ProductVersion' in line:
            # strings gives us this for SSE-GOG:
            # 20f87b6 FileVersion
            # 20f87d0 1.6.659.0
            # So discard the first hex part. Note that xSE uses commas and
            # spaces for separation, so join them back together to a single
            # string (discarding the spaces)
            ver_candidate = _parse_version_string(
                ' '.join(hexdump[i + 1].strip().split(' ')[1:]))
            if ver_candidate not in __ignored:
                return ver_candidate
    return ver_candidate # unable to parse for some reason

def fixup_taskbar_icon():
    pass # Windows only

def mark_high_dpi_aware():
    pass # Windows only

def convert_separators(p):
    return p.replace(u'\\', u'/')

##: A more performant implementation would maybe cache folder contents or
# something similar, as it stands this is not usable for fixing BAIN on Linux
def canonize_ci_path(ci_path: os.PathLike | str) -> _Path | None:
    if os.path.exists(ci_path):
        # Fast path, but GPath it as we haven't normpathed it yet
        return _GPath(ci_path)
    # Find the longest prefix that exists in the filesystem - *some* prefix
    # must exist, even if it's only root
    path_prefix, ci_rem_part = os.path.split(os.path.normpath(ci_path))
    ci_remaining_parts = deque([ci_rem_part])
    while not os.path.exists(path_prefix):
        path_prefix, ci_rem_part = os.path.split(path_prefix)
        ci_remaining_parts.appendleft(ci_rem_part)
    constructed_path = path_prefix
    for ci_part in ci_remaining_parts:
        new_ci_path = os.path.join(constructed_path, ci_part)
        if os.path.exists(new_ci_path):
            # If this part exists with the correct case, keep going
            constructed_path = new_ci_path
        else:
            # Otherwise we have to list the entire folder and
            # case-insensitively look for a match
            ci_part_lower = ci_part.lower()
            for candidate_file in os.listdir(constructed_path):
                if candidate_file.lower() == ci_part_lower:
                    # We found a matching file, construct the new path with the
                    # right case and resume the outer loop
                    constructed_path = os.path.join(constructed_path,
                        candidate_file)
                    break
            else:
                # We can't find this part at all, so the whole path can't be
                # found -> None
                return None
    return _GPath_no_norm(constructed_path)

def set_file_hidden(file_to_hide: str | os.PathLike, is_hidden=True):
    # Let this fail noisily for now
    fth_head, fth_tail = os.path.split(file_to_hide)
    if is_hidden:
        if not fth_tail.startswith('.'):
            os.rename(file_to_hide, os.path.join(fth_head, f'.{fth_tail}'))
    else:
        if fth_tail.startswith('.'):
            os.rename(file_to_hide, os.path.join(fth_head,
                fth_tail.lstrip('.')))

def get_case_sensitivity_advice():
    return (_("On Linux, if your filesystem supports casefolding, you can "
              "utilize that feature. An ext4 filesystem that was created with "
              "the '-O casefold' option can use 'chattr +F' to mark the Data "
              "folder as case-insensitive, for example. Please check if your "
              "filesystem supports this and how to enable it.") + '\n\n' +
            _("You may use a loop device if your current filesystem does not "
              "support casefolding or try CIOPFS/CICPOFFS (FUSE), though "
              "those utilities are outdated and have known issues."))

# API - Classes ===============================================================
class TaskDialog(object):
    def __init__(self, title, heading, content, tsk_buttons=(),
                 main_icon=None, parenthwnd=None, footer=None):
        raise EnvError(u'TaskDialog')

class AppLauncher(_AppLauncher):
    def launch_app(self, exe_path, exe_args):
        kw = dict(close_fds=True, env=os.environ.copy())
        if os.access(exe_path, mode=os.X_OK):
            # we could run this if we tried so let's do it
            return subprocess.Popen([exe_path.s, *exe_args], **kw)
        # not executable, calling xdg-open to figure this out (can't pass args)
        return subprocess.Popen([which('xdg-open'), exe_path.s], **kw)

# Linux versions
class ExeLauncher(AppLauncher):
    """Win executable ending in .exe, run with wine/proton."""

    def launch_app(self, exe_path: _Path, exe_args):
        self._run_exe(exe_path, exe_args)

    @set_cwd
    def _run_exe(self, exe_path: _Path, exe_args: list[str]) -> subprocess.Popen:
        if exe_path.cext == '.exe':  # win exec, run with wine/proton
            return subprocess.Popen([_WINEPATH, exe_path.s, *exe_args],
                                    close_fds=True, env=os.environ.copy())
        return super().launch_app(exe_path, exe_args)

class LnkLauncher(AppLauncher):
    def allow_create(self):
        return False  # wanting to run a windows .lnk on linux is an overkill

def in_mo2_vfs() -> bool:
    return False # No native MO2 version
