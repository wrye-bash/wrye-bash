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
"""The env module encapsulates OS-specific classes and methods. This is the
central import point, always import directly from here to get the right
implementations for the current OS."""
from __future__ import annotations

import platform
from collections.abc import Iterable

# First import the shared API
from .common import *
from .common import file_operation as _default_file_operation
from ..bolt import os_name, GPath_no_norm, Path
from ..wbtemp import cleanup_temp_dir, new_temp_dir

_TShellWindow = '_AComponent | _Window | None'
_ConfirmationPrompt = Callable[[Any, str, str], bool] | None

# Then check which OS we are running on and import *only* from there
match platform.system():
    case 'Windows': from .windows import *
    case 'Linux': from .linux import *
    case 'Darwin': from .linux import * # let's not have a separate file yet
    case _: raise ImportError(f'Wrye Bash does not support '
                              f'{platform.system()} yet')

def _resolve(parent: _TShellWindow):
    """Resolve a parent window to a wx.Window for ifileoperation"""
    try:
        return parent._resolve(parent) # type: ignore
    except AttributeError:
        return parent   # type: ignore

# Higher level APIs using imported OS-specific ones ---------------------------
def to_os_path(questionable_path: os.PathLike | str) -> Path | None:
    """Convenience method for converting a path of unknown origin to a path
    compatible with this OS/FS. See normalize_ci_path and convert_separators
    for more information."""
    return normalize_ci_path(convert_separators(os.fspath(questionable_path)))

def shellDelete(files: Iterable[Path], parent: _TShellWindow = None, *,
                ask_confirm: _ConfirmationPrompt=None, recycle=False,
                __shell=True):
    operate = file_operation if __shell else _default_file_operation
    srcs_dsts = dict.fromkeys(files, GPath(''))
    try:
        return operate(FileOperationType.DELETE, srcs_dsts, allow_undo=recycle,
            ask_confirm=ask_confirm, silent=False, parent=_resolve(parent))
    except CancelError:
        if ask_confirm:
            # The user selected to cancel the operation, so don't raise the
            # error
            return None
        raise

def shellDeletePass(node: Path, parent: _TShellWindow = None, *, __shell=True):
    """Delete tmp dirs/files - ignore errors (but log them)."""
    if node.exists():
        try: shellDelete([node], parent, __shell=__shell)
        except OSError: deprint(f'Error deleting {node}:', traceback=True)

def shellMove(sources_dests: dict[Path, Path], parent: _TShellWindow = None, *,
        ask_confirm: _ConfirmationPrompt=None, allow_undo=False,
        auto_rename=False, silent=False, __shell=True):
    operate = file_operation if __shell else _default_file_operation
    return operate(FileOperationType.MOVE, sources_dests,
        parent=_resolve(parent), ask_confirm=ask_confirm, allow_undo=allow_undo,
        rename_on_collision=auto_rename, silent=silent)

def shellCopy(sources_dests: dict[Path, Path], parent: _TShellWindow = None, *,
        ask_confirm: _ConfirmationPrompt=None, allow_undo=False,
        auto_rename=False, __shell=True):
    operate = file_operation if __shell else _default_file_operation
    return operate(FileOperationType.COPY, sources_dests,
        allow_undo=allow_undo, ask_confirm=ask_confirm,
        rename_on_collision=auto_rename, silent=False, parent=_resolve(parent))

def shellMakeDirs(dirs: Iterable[Path], parent: _TShellWindow = None):
    if not dirs: return
    #--Skip dirs that already exist
    dirs = [x for x in dirs if not x.exists()]
    #--Check for dirs that are impossible to create (the drive they are
    #  supposed to be on doesn't exist)
    errorPaths = [d for d in dirs if not drive_exists(d)]
    if errorPaths:
        raise NotADirectoryError(errorPaths)
    if os_name == 'posix':
        return # drive_exists creates the directories on posix
    #--Checks complete, start working
    move_dirs: dict[Path, Path] = {}
    tempDirs: list[Path] = []
    try:
        for folder in dirs:
            # Attempt creating the directory via normal methods, only fall back
            # to shellMove if UAC or something else stopped it
            try:
                folder.makedirs()
            except: ##: tighten
                # Failed, try the UAC workaround
                tmpDir = GPath_no_norm(new_temp_dir())
                tempDirs.append(tmpDir)
                toMake = []
                while not folder.exists() and folder != folder.head:
                    # Need to test against dir == dir.head to prevent
                    # infinite recursion if the final bit doesn't exist
                    toMake.append(folder.tail)
                    folder = folder.head
                if not toMake:
                    continue
                toMake.reverse()
                move_dirs[toMake[0]] = folder.join(toMake[0])
                tmpDir.join(*toMake).makedirs()
        if move_dirs:
            # fromDirs will only get filled if folder.makedirs() failed
            shellMove(move_dirs, parent=parent)
    finally:
        for tmpDir in tempDirs:
            cleanup_temp_dir(tmpDir)
