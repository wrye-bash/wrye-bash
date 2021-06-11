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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""The env module encapsulates OS-specific classes and methods. This is the
central import point, always import directly from here to get the right
implementations for the current OS."""

import platform
import shutil
# First import the shared API
from .common import *

# Then check which OS we are running on and import *only* from there
if platform.system() == u'Windows':
    from .windows import *
elif platform.system() == u'Linux':
    from .linux import *
else:
    raise ImportError(u'Wrye Bash does not support %s yet' % platform.system())

##: Internals that could not easily be split between windows.py and linux.py
##: due to dependencies on constants that only exist in windows, but we
##: use as values for our generic versions.
try:
    from win32com.shell import shell, shellcon
except ImportError:
    shell = shellcon = None

from ..bolt import deprint, Path
from ..exception import CancelError, SkipError, AccessDeniedError, \
    DirectoryFileCollisionError, FileOperationError

# NOTE(lojack): AccessDenied can be a result of many error codes,
# According to
# https://msdn.microsoft.com/en-us/library/windows/desktop/bb762164%28v=vs.85%29.aspx
# If you recieve an error code not on that list, then you assume it is one of
# the default WinError.h error codes, in this case 5 is `ERROR_ACCESS_DENIED`.
# I actually DO get error code 5, when the game detection for WS games wasn't
# including the language directories (which caused us to attempt one directory
# too high in the tree).
_file_op_error_map = {
    # Returned for Windows Store games that need admin access
    5: AccessDeniedError,    # ERROR_ACCESS_DENIED
    17: AccessDeniedError,   # ERROR_INVALID_ACCESS
    120: AccessDeniedError,  # DE_ACCESSDENIEDSRC -> source AccessDenied
    # https://msdn.microsoft.com/en-us/library/windows/desktop/ms681383%28v=vs.85%29.aspx
    1223: CancelError,
}

def __copyOrMove(operation, source, target, renameOnCollision, parent):
    """WIP shutil move and copy adapted from #96"""
    # renameOnCollision - if True auto-rename on moving collision, else ask
    # TODO(241): renameOnCollision NOT IMPLEMENTED
    doIt = shutil.copytree if operation == FO_COPY else shutil.move
    for fileFrom, fileTo in zip(source, target):
        if fileFrom.isdir():
            dest_dir = fileTo.join(fileFrom.tail)
            if dest_dir.exists():
                if not dest_dir.isdir():
                    raise DirectoryFileCollisionError(fileFrom, dest_dir)
                # dir exists at target, copy contents individually/recursively
                source_paths, dests = [], []
                for content in os.listdir(fileFrom.s):
                    source_paths.append(fileFrom.join(content))
                    dests.append(dest_dir)
                __copyOrMove(operation, source_paths, dests, renameOnCollision, parent)
            else:  # dir doesn't exist at the target, copy it
                doIt(fileFrom.s, fileTo.s)
        # copy the file, overwrite as needed
        elif fileFrom.isfile():  # or os.path.islink(file):
            # move may not work if the target exists, copy instead and
            # overwrite as needed
            try:
                shutil.copy2(fileFrom.s, fileTo.s)
            except FileNotFoundError:
                # probably directory path does not exist, create it.
                fileTo.head.makedirs()
                shutil.copy2(fileFrom.s, fileTo.s)
            if operation == FO_MOVE: fileFrom.remove() # then remove original
    return {} ##: the renames map ?

def _fileOperation(operation, source, target=None, allowUndo=True,
                   confirm=True, renameOnCollision=False, silent=False,
                   parent=None, __shell=True):
    """Docs WIP

    :param operation: one of FO_MOVE, FO_COPY, FO_DELETE, FO_RENAME
    :param source: a Path, string or an iterable of those (yak, only accept
       iterables)
    :param target: as above, if iterable must have the same length as source
    :param allowUndo: FOF_ALLOWUNDO: "Preserve undo information, if possible"
    :param confirm: the opposite of FOF_NOCONFIRMATION ("Respond with Yes to
        All for any dialog box that is displayed")
    :param renameOnCollision: FOF_RENAMEONCOLLISION
    :param silent: FOF_SILENT ("Do not display a progress dialog box")
    :param parent: HWND to the dialog's parent window
    .. seealso:
        `SHFileOperation <http://msdn.microsoft.com/en-us/library/windows
        /desktop/bb762164(v=vs.85).aspx>`
    """
    if not source:
        return {}
    abspath = os.path.abspath
    # source may be anything - see SHFILEOPSTRUCT - accepts list or item
    if isinstance(source, (Path, (str, bytes))):
        source = [abspath(u'%s' % source)]
    else:
        source = [abspath(u'%s' % x) for x in source]
    # target may be anything ...
    target = target if target else u'' # abspath(u''): cwd (must be Mopy/)
    if isinstance(target, (Path, (str, bytes))):
        target = [abspath(u'%s' % target)]
    else:
        target = [abspath(u'%s' % x) for x in target]
    _source = source; _target = target
    if __shell and shell is not None:
        # flags
        flgs = shellcon.FOF_WANTMAPPINGHANDLE # enables mapping return value !
        flgs |= FOF_NOCONFIRMMKDIR # never ask user for creating dirs
        flgs |= (len(target) > 1) * shellcon.FOF_MULTIDESTFILES
        if allowUndo: flgs |= shellcon.FOF_ALLOWUNDO
        if not confirm: flgs |= shellcon.FOF_NOCONFIRMATION
        if renameOnCollision: flgs |= shellcon.FOF_RENAMEONCOLLISION
        if silent: flgs |= shellcon.FOF_SILENT
        # null terminated strings
        source = u'\x00'.join(source) # nope: + u'\x00'
        target = u'\x00'.join(target)
        # get the handle to parent window to feed to win api
        parent = parent.GetHandle() if parent else None
        # See SHFILEOPSTRUCT for deciphering return values
        # result: a windows error code (or 0 for success)
        # aborted: True if any operations aborted, False otherwise
        # mapping: maps the old and new names of the renamed files
        result, aborted, mapping = shell.SHFileOperation(
                (parent, operation, source, target, flgs, None, None))
        if result == 0:
            if aborted: raise SkipError()
            return dict(mapping)
        elif result == 2 and operation == FO_DELETE:
            # Delete failed because file didnt exist
            return dict(mapping)
        else:
            if result == 124:
                deprint(u'Invalid paths:\nsource: %s\ntarget: %s\nRetrying' % (
                    source.replace(u'\x00', u'\n'),
                    target.replace(u'\x00', u'\n')))
                return _fileOperation(operation, _source, _target, allowUndo,
                                      confirm, renameOnCollision, silent,
                                      parent, __shell=False)
            raise _file_op_error_map.get(result, FileOperationError(result))
    else: # Use custom dialogs and such
        from .. import balt # TODO(ut): local import, env should be above balt...
        source = [GPath(s) for s in source]
        target = [GPath(s) for s in target]
        if operation == FO_DELETE:
            # allowUndo - no effect, can't use recycle bin this way
            # confirm - ask if confirm is True
            # renameOnCollision - no effect, deleting files
            # silent - no real effect (we don't show visuals deleting this way)
            if confirm:
                message = _(u'Are you sure you want to permanently delete '
                            u'these %(count)d items?') % {u'count':len(source)}
                message += u'\n\n' + u'\n'.join([u' * %s' % x for x in source])
                if not balt.askYes(parent,message,_(u'Delete Multiple Items')):
                    return {}
            # Do deletion
            for toDelete in source:
                if not toDelete.exists(): continue
                if toDelete.isdir():
                    toDelete.rmtree(toDelete.stail)
                else:
                    toDelete.remove()
            return {}
        # allowUndo - no effect, we're not going to manually track file moves
        # confirm - no real effect when moving
        # silent - no real effect, since we're not showing visuals
        return __copyOrMove(operation, source, target, renameOnCollision,
                            parent)

# Higher level APIs implemented by using the imported OS-specific ones above
def shellDelete(files, parent=None, confirm=False, recycle=False):
    try:
        return _fileOperation(FO_DELETE, files, target=None, allowUndo=recycle,
                              confirm=confirm, renameOnCollision=True,
                              silent=False, parent=parent)
    except CancelError:
        if confirm:
            return None
        raise

def shellDeletePass(node, parent=None):
    """Delete tmp dirs/files - ignore errors (but log them)."""
    if node.exists():
        try: shellDelete(node, parent=parent, confirm=False, recycle=False)
        except OSError: deprint(u'Error deleting %s:' % node, traceback=True)

def shellMove(filesFrom, filesTo, parent=None, askOverwrite=False,
              allowUndo=False, autoRename=False, silent=False):
    return _fileOperation(FO_MOVE, filesFrom, filesTo, parent=parent,
                          confirm=askOverwrite, allowUndo=allowUndo,
                          renameOnCollision=autoRename, silent=silent)

def shellCopy(filesFrom, filesTo, parent=None, askOverwrite=False,
              allowUndo=False, autoRename=False):
    return _fileOperation(FO_COPY, filesFrom, filesTo, allowUndo=allowUndo,
                          confirm=askOverwrite, renameOnCollision=autoRename,
                          silent=False, parent=parent)

def shellMakeDirs(dirs, parent=None):
    if not dirs: return
    dirs = [dirs] if not isinstance(dirs, (list, tuple, set)) else dirs
    #--Skip dirs that already exist
    dirs = [x for x in dirs if not x.exists()]
    #--Check for dirs that are impossible to create (the drive they are
    #  supposed to be on doesn't exist
    def _filterUnixPaths(path):
        return (os.name != u'posix' and not path.s.startswith(u'\\')
                and not path.drive().exists())
    errorPaths = [d for d in dirs if _filterUnixPaths(d)]
    if errorPaths:
        raise NonExistentDriveError(errorPaths)
    #--Checks complete, start working
    tempDirs, fromDirs, toDirs = [], [], []
    try:
        for folder in dirs:
            # Attempt creating the directory via normal methods, only fall back
            # to shellMove if UAC or something else stopped it
            try:
                folder.makedirs()
            except:
                # Failed, try the UAC workaround
                tmpDir = Path.tempDir()
                tempDirs.append(tmpDir)
                toMake = []
                toMakeAppend = toMake.append
                while not folder.exists() and folder != folder.head:
                    # Need to test against dir == dir.head to prevent
                    # infinite recursion if the final bit doesn't exist
                    toMakeAppend(folder.tail)
                    folder = folder.head
                if not toMake:
                    continue
                toMake.reverse()
                base = tmpDir.join(toMake[0])
                toDir = folder.join(toMake[0])
                tmpDir.join(*toMake).makedirs()
                fromDirs.append(base)
                toDirs.append(toDir)
        if fromDirs:
            # fromDirs will only get filled if folder.makedirs() failed
            shellMove(fromDirs, toDirs, parent=parent)
    finally:
        for tmpDir in tempDirs:
            tmpDir.rmtree(safety=tmpDir.stail)
