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
"""Encapsulates Wrye Bash's temporary dir/files handling, including early boot
and the global .wbtemp directory.

Generally, you want to use TempDir or TempFile in a context handler. That way
you guarantee that the temporary files will get cleaned up, no matter how
complicated your flow of logic might get or even if an exception occurs.

If you need more control, use new_temp_dir and new_temp_file to create
temporary directories and files and clean them up manually with
cleanup_temp_dir and cleanup_temp_file.

If worst comes to worst, Wrye Bash's atexit hook should clean up all leftover
temp files when Wrye Bash closes. Sometimes this is unavoidable (see e.g.
Path.start()), but it's almost always better to be explicit and clean up your
temporary directories and files, if only to respect the user's disk usage."""
import shutil
import tempfile
import os
import platform
from pathlib import Path as PPath ##: To be obsoleted when we refactor Path
from textwrap import wrap

# *No other local imports!* This needs to be imported all over the place
from . import bass

# Internals -------------------------------------------------------------------
# The actual global .wbtemp folder we will be using
_wbtemp_dir: PPath | None = None
# Directories in the standard temporary directory that we created during early
# boot and hence are safe to clean up by us as well
_early_boot_dirs: set[PPath] = set()
# Sub-directories of the global directory that we created and hence are safe to
# clean up by us as well
_our_temp_dirs: set[PPath] = set()
# Sub-files of the global directory that we created and hence are safe to clean
# up by us as well
_our_temp_files: set[PPath] = set()

def _get_global_dir() -> PPath:
    """Get a base directory to use for generating unique sub-directories in.
    Designed to always be safe to call, even if WB's settings haven't been
    loaded yet.

    Note that we do not clean this directory itself up (only the
    sub-directories we later create), since several instances may use it at the
    same time. Safely cleaning it up would require us to hold locks, which
    would complicate things and require a new dependency."""
    global _wbtemp_dir
    if _wbtemp_dir is not None:
        # We already created a global dir, use that
        return _wbtemp_dir
    if not bass.dirs or bass.settings is None:
        # We're in early boot, use some standard temp directory for now
        early_boot_dir = PPath(tempfile.mkdtemp(prefix='WryeBash_'))
        _early_boot_dirs.add(early_boot_dir)
        return early_boot_dir
    def _reset_temp_dir_setting():
        nonlocal raw_configured_path
        raw_configured_path = default_global_temp_dir()
        bass.settings['bash.temp_dir'] = raw_configured_path
        os.makedirs(raw_configured_path, exist_ok=True)
    raw_configured_path = bass.settings['bash.temp_dir']
    if not raw_configured_path:
        # First launch of WB, initialize the default temp folder setting
        _reset_temp_dir_setting()
    configured_dir = PPath(raw_configured_path)
    try:
        configured_dir = configured_dir.resolve(strict=True)
    except FileNotFoundError:
        os.makedirs(configured_dir, exist_ok=True)
    try:
        wbtemp_readme = os.path.join(configured_dir, 'README.md')
        # Keep this construction here, it relies on _(), which won't have been
        # set up yet the time we first import this file
        readme_contents = (
        f'## {_("Wrye Bash Temporary Directory")}'
        + '\n\n' + '\n'.join(wrap(
            _('This folder is used by Wrye Bash to store temporary '
              'directories and files. As long as Wrye Bash always exits '
              'properly, this folder should remain empty (except for this '
              'README).')))
        + '\n\n' + '\n'.join(wrap(
            _('If all instances of Wrye Bash are closed and you still see '
              'directories and/or files in here, you can freely delete '
              'them.'))))
        # Unconditionally write out the readme since the language or readme
        # contents may have changed since it was last written - we have no way
        # to tell
        with open(wbtemp_readme, 'w', encoding='utf-8') as out:
            out.write(readme_contents)
    except OSError:
        # Failed to write the readme, this isn't a big deal - probably a race
        # condition with another instance
        pass
    _wbtemp_dir = configured_dir
    # Only hide on Windows, since on other platforms this would entail us
    # renaming the folder, which would fail and may not be desirable to a user
    # who just configured their path to be something else anyway
    if platform.system() == 'Windows':
        # Delayed import to avoid circular dependency
        from .env import set_file_hidden
        set_file_hidden(configured_dir)
    return configured_dir

# API - Temporary Directories -------------------------------------------------
##: We will probably want all these APIs to return pathlib.Path objects in the
# future (once Path is refactored) - would let us get rid of many stupid
# GPath_no_norm calls done on the returned strings right now
def new_temp_dir(*, temp_prefix='', temp_suffix='', base_dir='') -> str:
    """Create a new, unique, temporary directory. The caller is responsible for
    cleaning it up via cleanup_temp_dir once done.

    Use only when absolutely needed, TempDir is almost always a better
    choice."""
    ntd = tempfile.mkdtemp(dir=base_dir or _get_global_dir(),
        prefix=f'{temp_prefix}_' if temp_prefix else '', suffix=temp_suffix)
    _our_temp_dirs.add(PPath(ntd))
    return ntd

def cleanup_temp_dir(temp_dir: str | os.PathLike) -> None:
    """Clean up a temporary directory created via new_temp_dir. Will raise an
    error if called on a directory that wasn't created via new_temp_dir or if
    it is called twice on the same directory.

    Use only when absolutely needed, TempDir is almost always a better
    choice."""
    fixed_path = PPath(temp_dir)
    try:
        _our_temp_dirs.remove(fixed_path)
    except KeyError:
        # 'from None' to drop the unhelpful KeyError traceback
        if not fixed_path.is_dir():
            raise RuntimeError(
                f'cleanup_temp_dir may have been called twice on the same '
                f'directory or on a file (offending path: '
                f'{temp_dir})') from None
        raise RuntimeError(
            f"Refusing to delete directory that wasn't created by this "
            f"instance's new_temp_dir (offending path: {temp_dir})") from None
    try:
        shutil.rmtree(fixed_path)
    except FileNotFoundError:
        pass # Already cleaned up (e.g. by moving it somewhere else)

class TempDir:
    """Convenient and error-resistant way to create and clean up a unique
    temporary directory with a context handler."""
    def __init__(self, *, temp_prefix='', temp_suffix='', base_dir=''):
        self._temp_prefix = temp_prefix
        self._temp_suffix = temp_suffix
        self._base_dir = base_dir

    def __enter__(self):
        self._temp_dir = new_temp_dir(temp_prefix=self._temp_prefix,
            temp_suffix=self._temp_suffix, base_dir=self._base_dir)
        return self._temp_dir

    def __exit__(self, exc_type, exc_val, exc_tb):
        cleanup_temp_dir(self._temp_dir)

# API - Temporary Files -------------------------------------------------------
def new_temp_file(*, temp_prefix='', temp_suffix='.dat', base_dir='') -> str:
    """Create a new, unique, temporary file. The caller is responsible for
    cleaning it up via cleanup_temp_file once done.

    Use only when absolutely needed, TempFile is almost always a better
    choice."""
    ntf_fd, ntf = tempfile.mkstemp(dir=base_dir or _get_global_dir(),
        prefix=f'{temp_prefix}_' if temp_prefix else '', suffix=temp_suffix)
    _our_temp_files.add(PPath(ntf))
    os.close(ntf_fd)
    return ntf

def cleanup_temp_file(temp_file: str | os.PathLike) -> None:
    """Clean up a temporary file created via new_temp_file. Will raise an error
    if called on a file that wasn't created via new_temp_file or if it is
    called twice on the same file.

    Use only when absolutely needed, TempFile is almost always a better
    choice."""
    fixed_path = PPath(temp_file)
    try:
        _our_temp_files.remove(fixed_path)
    except KeyError:
        # 'from None' to drop the unhelpful KeyError traceback
        if not fixed_path.is_file():
            raise RuntimeError(
                f'cleanup_temp_file may have been called twice on the same '
                f'file or on a directory (offending path: '
                f'{temp_file})') from None
        raise RuntimeError(
            f"Refusing to delete file that wasn't created by this instance's "
            f"new_temp_file (offending path: {temp_file})") from None
    try:
        os.remove(fixed_path)
    except FileNotFoundError:
        pass # Already cleaned up (e.g. by moving it somewhere else)

class TempFile:
    """Convenient and error-resistant way to create and clean up a unique
    temporary file with a context handler."""
    def __init__(self, *, temp_prefix='', temp_suffix='.dat', base_dir=''):
        self._temp_prefix = temp_prefix
        self._temp_suffix = temp_suffix
        self._base_dir = base_dir

    def __enter__(self):
        self._temp_file = new_temp_file(temp_prefix=self._temp_prefix,
            temp_suffix=self._temp_suffix, base_dir=self._base_dir)
        return self._temp_file

    def __exit__(self, exc_type, exc_val, exc_tb):
        cleanup_temp_file(self._temp_file)

# API - Misc ------------------------------------------------------------------
def default_global_temp_dir() -> str:
    r"""Returns the default global temporary directory for the current
    operating system, based on the Data folder used by the current game.

    On Windows, this will simply place one at the root of the drive used by the
    Data folder, e.g. G:\.wbtemp for G:\steam\steamapps\common\Skyrim\Data.
    However, if that drive is the same as the drive used for the global temp
    folder (generally (always?) C:), then we can just use the global temp
    folder.

    On Linux and macOS, this will look for the highest parent of the Data
    folder's path that has the same device ID and user ID, i.e. sits on the
    same device/filesystem and is owned by the same user."""
    data_folder_path = PPath(bass.dirs['mods'])
    def _default_global_win():
        df_drive = data_folder_path.drive
        global_temp = tempfile.gettempdir()
        gt_drive, _gt_path = os.path.splitdrive(global_temp)
        # If we're on the same drive as the global temp folder, we can
        # use that one to avoid cluttering the user's FS
        base_folder = (global_temp if df_drive == gt_drive
                       else data_folder_path.drive)
        return base_folder + os.sep + '.wbtemp'
    def _default_global_unix():
        # We have to use a file inside the Data folder, since the Data folder
        # itself may be a mount point and so belong to a different FS than its
        # *contents*, which is what we really care about
        dfp_contents = os.listdir(data_folder_path)
        if not dfp_contents:
            # If the Data folder is empty, we'll blow up later anyways because
            # the game master will be missing, so this doesn't really matter
            dfp_test_path = data_folder_path
        else:
            dfp_test_path = os.path.join(data_folder_path, dfp_contents[0])
        dfp_stat = os.stat(dfp_test_path)
        data_device_id = dfp_stat.st_dev
        data_uid = dfp_stat.st_uid
        max_path = data_folder_path
        while len(max_path.parts) > 1:
            mp_parent = max_path.parent
            mpp_stat = os.stat(mp_parent)
            if (mpp_stat.st_dev != data_device_id or
                    mpp_stat.st_uid != data_uid):
                # The next parent isn't on the same device/filesystem or isn't
                # owned by the same user anymore, stop at the current path
                break
            max_path = mp_parent
        return os.path.join(max_path, '.wbtemp')
    match platform.system():
        case 'Windows': return _default_global_win()
        case 'Linux': return _default_global_unix()
        case 'Darwin': return _default_global_unix()
        case _: raise RuntimeError(f'wbtemp.py does not support '
                                   f'{platform.system()} yet')

def cleanup_temp():
    """Remove all temp directories that were created by this instance of Wrye
    Bash. To be called by an atexit hook."""
    for otd in _our_temp_dirs:
        shutil.rmtree(otd)
    _our_temp_dirs.clear()
    for otf in _our_temp_files:
        os.remove(otf)
    _our_temp_files.clear()
    # Be sure to do these last since the earlier ones may sit inside these
    for ebd in _early_boot_dirs:
        shutil.rmtree(ebd)
    _early_boot_dirs.clear()
