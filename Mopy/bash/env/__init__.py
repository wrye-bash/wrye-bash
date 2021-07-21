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
"""The env module encapsulates OS-specific classes and methods. This is the
central import point, always import directly from here to get the right
implementations for the current OS."""

import platform
import shutil
from ..bolt import Path, GPath, deprint, os_name
from ..exception import CancelError, DirectoryFileCollisionError, \
    NonExistentDriveError
# First import the shared API
from .common import *

# Then check which OS we are running on and import *only* from there
shfo = None
op_system = platform.system()
if op_system == u'Windows':
    from .windows import *
elif op_system == u'Linux':
    from .linux import *
elif op_system == u'Darwin':
    # let's not have a separate file yet
    from .linux import *
else:
    raise ImportError(f'Wrye Bash does not support {op_system} yet')

# File operations WIP ---------------------------------------------------------
def __copyOrMove(operation, source, target, renameOnCollision, parent):
    """WIP shutil move and copy adapted from #96"""
    # renameOnCollision - if True auto-rename on moving collision, else ask
    # TODO(241): renameOnCollision NOT IMPLEMENTED
    doIt = shutil.copytree if operation == FO_COPY else shutil.move
    for fileFrom, fileTo in zip(source, target):
        if fileFrom.is_dir():
            dest_dir = fileTo.join(fileFrom.tail)
            if dest_dir.exists():
                if not dest_dir.is_dir():
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
        elif fileFrom.is_file():  # or os.path.islink(file):
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
    if __shell and shfo is not None:
        res = shfo(operation, source, target, allowUndo, confirm,
                   renameOnCollision, silent, parent)
        return _fileOperation(operation, source, target, allowUndo, confirm,
                              renameOnCollision, silent, parent,
                              __shell=False) if res is None else res
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
                if toDelete.is_dir():
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
    #--Skip dirs that already exist
    dirs = [x for x in dirs if not x.exists()]
    #--Check for dirs that are impossible to create (the drive they are
    #  supposed to be on doesn't exist)
    errorPaths = [d for d in dirs if not drive_exists(d)]
    if errorPaths:
        raise NonExistentDriveError(errorPaths)
    if os_name == 'posix':
        return # drive_exists creates the directories on posix
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
                while not folder.exists() and folder != folder.head:
                    # Need to test against dir == dir.head to prevent
                    # infinite recursion if the final bit doesn't exist
                    toMake.append(folder.tail)
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
