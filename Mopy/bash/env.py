# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2015 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""WIP module to encapsulate environment access - currently OS dependent stuff.
"""
import errno
import os as _os
import re as _re
import shutil as _shutil
import stat
import struct

from bolt import GPath, deprint, Path, decode
from exception import BoltError, CancelError, SkipError, AccessDeniedError, \
    DirectoryFileCollisionError, InvalidPathsError, FileOperationError, \
    NonExistentDriveError

try:
    import _winreg as winreg
except ImportError: # we're on linux
    winreg = None
try:
    import win32gui
except ImportError: # linux
    win32gui = None
try:
    import win32api
except ImportError:
    win32api = None

def get_registry_path(subkey, entry, exe):
    """Check registry for a path to a program."""
    if not winreg: return None
    for hkey in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for wow6432 in (u'', u'Wow6432Node\\'):
            try:
                key = winreg.OpenKey(hkey,
                                     u'Software\\%s%s' % (wow6432, subkey))
                value = winreg.QueryValueEx(key, entry)
            except OSError:
                continue
            if value[1] != winreg.REG_SZ: continue
            installPath = GPath(value[0])
            if not installPath.exists(): continue
            exePath = installPath.join(exe)
            if not exePath.exists(): continue
            return installPath
    return None

def get_game_path(submod):
    """Check registry supplied game paths for the game.exe."""
    subkey, entry = submod.regInstallKeys
    return get_registry_path(subkey, entry, submod.exe)

try: # Python27\Lib\site-packages\win32comext\shell
    from win32com.shell import shell, shellcon
    from win32com.shell.shellcon import FO_DELETE, FO_MOVE, FO_COPY, FO_RENAME

    def _getShellPath(shellKey):
        path = shell.SHGetFolderPath(0, shellKey, None, 0)
        return path
except ImportError:
    shell = shellcon = None
    FO_MOVE = 1
    FO_COPY = 2
    FO_DELETE = 3
    FO_RENAME = 4
    reEnv = _re.compile(u'%(\w+)%', _re.U)
    envDefs = _os.environ

    def subEnv(match):
        key = match.group(1).upper()
        if not envDefs.get(key):
            raise BoltError(u'Can\'t find user directories in windows registry'
                    u'.\n>> See "If Bash Won\'t Start" in bash docs for help.')
        return envDefs[key]

    def _getShellPath(folderKey): ##: mkdirs
        if not winreg:  # Linux HACK
            home = _os.path.expanduser("~")
            return {'Personal': home,
                    'Local AppData': home + u'/.local/share'}[folderKey]
        regKey = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r'Software\Microsoft\Windows\CurrentVersion'
                                r'\Explorer\User Shell Folders')
        try:
            path = winreg.QueryValueEx(regKey, folderKey)[0]
        except WindowsError:
            raise BoltError(u'Can\'t find user directories in windows registry'
                    u'.\n>> See "If Bash Won\'t Start" in bash docs for help.')
        regKey.Close()
        path = reEnv.sub(subEnv, path)
        return path

try:
    import win32com.client as win32client
except ImportError:
    win32client = None

def clear_read_only(filepath): # copied from bolt
    _os.chmod(u'%s' % filepath, stat.S_IWUSR | stat.S_IWOTH)

def get_personal_path():
    if shell and shellcon:
        path = _getShellPath(shellcon.CSIDL_PERSONAL)
        sErrorInfo = _(u"Folder path extracted from win32com.shell.")
    else:
        path = _getShellPath('Personal')
        sErrorInfo = __get_error_info()
    return GPath(path), sErrorInfo

def get_local_app_data_path():
    if shell and shellcon:
        path = _getShellPath(shellcon.CSIDL_LOCAL_APPDATA)
        sErrorInfo = _(u"Folder path extracted from win32com.shell.")
    else:
        path = _getShellPath('Local AppData')
        sErrorInfo = __get_error_info()
    return GPath(path), sErrorInfo

def __get_error_info():
    try:
        sErrorInfo = u'\n'.join(u'  %s: %s' % (key, envDefs[key])
                                for key in sorted(envDefs))
    except UnicodeDecodeError:
        deprint(u'Error decoding _os.environ', traceback=True)
        sErrorInfo = u'\n'.join(u'  %s: %s' % (key, decode(envDefs[key]))
                                for key in sorted(envDefs))
    return sErrorInfo

__folderIcon = None # cached here
def _get_default_app_icon(idex, target):
    # Use the default icon for that file type
    if winreg is None:
        return u'not\\a\\path', idex
    try:
        if target.isdir():
            global __folderIcon
            if not __folderIcon:
                # Special handling of the Folder icon
                folderkey = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, u'Folder')
                iconkey = winreg.OpenKey(folderkey, u'DefaultIcon')
                filedata = winreg.EnumValue(iconkey, 0)
                # filedata == ('', u'%SystemRoot%\\System32\\shell32.dll,3', 2)
                filedata = filedata[1]
                __folderIcon = filedata
            else:
                filedata = __folderIcon
        else:
            file_association = winreg.QueryValue(winreg.HKEY_CLASSES_ROOT,
                                                 target.cext)
            pathKey = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT,
                                     u'%s\\DefaultIcon' % file_association)
            filedata = winreg.EnumValue(pathKey, 0)[1]
            winreg.CloseKey(pathKey)
        if _os.path.isabs(filedata) and _os.path.isfile(filedata):
            icon = filedata
        else:
            icon, idex = filedata.split(u',')
            icon = _os.path.expandvars(icon)
        if not _os.path.isabs(icon):
            # Get the correct path to the dll
            for dir_ in _os.environ['PATH'].split(u';'):
                test = _os.path.join(dir_, icon)
                if _os.path.exists(test):
                    icon = test
                    break
    except: # TODO(ut) comment the code above - what exception can I get here?
        deprint(_(u'Error finding icon for %s:') % target.s, traceback=True)
        icon = u'not\\a\\path'
    return icon, idex

def _get_app_links(apps_dir):
    """Scan Mopy/Apps folder for shortcuts (.lnk files). Windows only !

    :param apps_dir: the absolute Path to Mopy/Apps folder
    :return: a dictionary of shortcut properties tuples keyed by the
    absolute Path of the Apps/.lnk shortcut
    """
    if win32client is None: return {}
    links = {}
    try:
        sh = win32client.Dispatch('WScript.Shell')
        for lnk in apps_dir.list():
            lnk = apps_dir.join(lnk)
            if lnk.cext == u'.lnk' and lnk.isfile():
                shortcut = sh.CreateShortCut(lnk.s)
                description = shortcut.Description
                if not description:
                    description = u' '.join((_(u'Launch'), lnk.sbody))
                links[lnk] = (shortcut.TargetPath, shortcut.IconLocation,
                              # shortcut.WorkingDirectory, shortcut.Arguments,
                              description)
    except:
        deprint(_(u"Error initializing links:"), traceback=True)
    return links

def init_app_links(apps_dir, badIcons, iconList):
    init_params = []
    for path, (target, icon, description) in _get_app_links(
            apps_dir).iteritems():
        if target.lower().find(ur'installer\{') != -1: # msi shortcuts: dc0c8de
            target = path
        else:
            target = GPath(target)
        if not target.exists(): continue
        # Target exists - extract path, icon and description
        # First try a custom icon #TODO(ut) docs - also comments methods here!
        fileName = u'%s%%i.png' % path.sbody
        customIcons = [apps_dir.join(fileName % x) for x in (16, 24, 32)]
        if customIcons[0].exists():
            icon = customIcons
        # Next try the shortcut specified icon
        else:
            icon, idex = icon.split(u',')
            if icon == u'':
                if target.cext == u'.exe':
                    if win32gui and win32gui.ExtractIconEx(target.s, -1):
                        # -1 queries num of icons embedded in the exe
                        icon = target
                    else: # generic exe icon, hardcoded and good to go
                        icon, idex = _os.path.expandvars(
                            u'%SystemRoot%\\System32\\shell32.dll'), u'2'
                else:
                    icon, idex = _get_default_app_icon(idex, target)
            icon = GPath(icon)
            if icon.exists():
                fileName = u';'.join((icon.s, idex))
                icon = iconList(fileName)
                # Last, use the 'x' icon
            else:
                icon = badIcons
        init_params.append((path, icon, description))
    return init_params

def test_permissions(path, permissions='rwcd'):
    """Test file permissions for a path:
        r = read permission
        w = write permission
        c = file creation permission
        d = file deletion permission"""
    return True # Temporarily disabled, for testing purposes
    path = GPath(path)
    permissions = permissions.lower()
    def getTemp(path_):  # Get a temp file name
        if path_.isdir():
            tmp = path_.join(u'temp.temp')
        else:
            tmp = path_.temp
        while tmp.exists():
            tmp = tmp.temp
        return tmp
    def getSmallest():  # Get the smallest file in the directory
        if path.isfile(): return path
        smallsize = -1
        ret = None
        for node in path.list():
            node = path.join(node)
            if not node.isfile(): continue
            size = node.size
            if smallsize == -1 or size < smallsize:
                smallsize = size
                ret = node
        return ret
    #--Test read permissions
    try:
        smallestFile = None
        path_exists = path.exists()
        if 'r' in permissions and path_exists:
            smallestFile = getSmallest()
            if smallestFile:
                with smallestFile.open('rb'):
                    pass
        #--Test write permissions
        if 'w' in permissions and path_exists:
            smallestFile = smallestFile or getSmallest()
            if smallestFile:
                with smallestFile.open('ab'):
                    pass
        #--Test file creation permission (only for directories)
        if 'c' in permissions:
            if path.isdir() or not path_exists:
                if not path_exists:
                    path.makedirs()
                    removeAtEnd = True
                else:
                    removeAtEnd = False
                temp = getTemp(path)
                with temp.open('wb'):
                    pass
                temp.remove()
                if removeAtEnd:
                    path.removedirs()
        #--Test file deletion permission
        if 'd' in permissions and path_exists:
            smallestFile = smallestFile or getSmallest()
            if smallestFile:
                temp = getTemp(smallestFile)
                smallestFile.copyTo(temp)
                smallestFile.remove()
                temp.moveTo(smallestFile)
    except Exception as e:
        if getattr(e, 'errno', 0) == 13:
            return False # Access denied
        elif getattr(e, 'winerror', 0) == 183:
            return False # Cannot create file if already exists
        else:
            raise
    return True

# OS agnostic get file version function and helper functions
def get_file_version(filename):
    """Return the version of a dll/exe, using the native win32 functions
    if available and otherwise a pure python implementation that works
    on Linux. The return value is a 4-int tuple, for example (1.9.32.0)."""
    if win32api is None:
        return _linux_get_file_version_info(filename)
    else:
        info = win32api.GetFileVersionInfo(filename, u'\\')
        ms = info['FileVersionMS']
        ls = info['FileVersionLS']
        return win32api.HIWORD(ms), win32api.LOWORD(ms), \
               win32api.HIWORD(ls), win32api.LOWORD(ls)

def _linux_get_file_version_info(filename):
    """A python replacement for win32api.GetFileVersionInfo that can be used
    on systems where win32api isn't available."""
    _WORD, _DWORD = (('H', 2), ('I', 4))
    def _read(fmt, file_obj, offset=0, count=1, absolute=False):
        """Read one or more chunks from the file, either a word or dword."""
        file_obj.seek(offset, not absolute)
        result = [struct.unpack('<' + fmt[0], file_obj.read(fmt[1]))[0]
                  for _ in xrange(count)]
        return result[0] if count == 1 else result
    def _find_version(file_obj, pos, offset):
        """Look through the RT_VERSION and return VS_VERSION_INFO."""
        def _pad(num):
            return num if num % 4 == 0 else num + 4 - (num % 4)
        file_obj.seek(pos + offset)
        len_, val_len, type_ = _read(_WORD, file_obj, count=3)
        info = u''
        for i in xrange(200):
            info += unichr(_read(_WORD, file_obj))
            if info[-1] == u'\x00': break
        offset = _pad(file_obj.tell()) - pos
        file_obj.seek(pos + offset)
        if type_ == 0: # binary data
            if info[:-1] == 'VS_VERSION_INFO':
                file_v = _read(_WORD, file_obj, count=4, offset=8)
                # prod_v = _read(_WORD, f, count=4) # this isn't used
                return 0, (file_v[1], file_v[0], file_v[3], file_v[2])
                # return 0, {'FileVersionMS': (file_v[1], file_v[0]),
                #            'FileVersionLS': (file_v[3], file_v[2]),
                #            'ProductVersionMS': (prod_v[1], prod_v[0]),
                #            'ProductVersionLS': (prod_v[3], prod_v[2])}
            offset += val_len
        else: # text data (utf-16)
            offset += val_len * 2
        while offset < len_:
            offset, result = _find_version(file_obj, pos, offset)
            if result is not None:
                return 0, result
        return _pad(offset), None
    version_pos = None
    with open(filename, 'rb') as f:
        f.seek(_read(_DWORD, f, offset=60))
        section_count = _read(_WORD, f, offset=6)
        optional_header_size = _read(_WORD, f, offset=12)
        optional_header_pos = f.tell() + 2
        # jump to the datatable and check the third entry
        resources_va = _read(_DWORD, f, offset=98 + 2*8)
        section_table_pos = optional_header_pos + optional_header_size
        for section_num in xrange(section_count):
            section_pos = section_table_pos + 40 * section_num
            f.seek(section_pos)
            if f.read(8).rstrip('\x00') != '.rsrc':  # section name
                continue
            section_va = _read(_DWORD, f, offset=4)
            raw_data_pos = _read(_DWORD, f, offset=4)
            section_resources_pos = raw_data_pos + resources_va - section_va
            num_named, num_id = _read(_WORD, f, count=2, absolute=True,
                                      offset=section_resources_pos + 12)
            for resource_num in xrange(num_named + num_id):
                resource_pos = section_resources_pos + 16 + 8 * resource_num
                name = _read(_DWORD, f, offset=resource_pos, absolute=True)
                if name != 16: continue # RT_VERSION
                for i in xrange(3):
                    res_offset = _read(_DWORD, f)
                    if i < 2:
                        res_offset &= 0x7FFFFFFF
                    ver_dir = section_resources_pos + res_offset
                    f.seek(ver_dir + (20 if i < 2 else 0))
                version_va = _read(_DWORD, f)
                version_pos = raw_data_pos + version_va - section_va
                break
        if version_pos is not None:
            return _find_version(f, version_pos, 0)[1]
        return None

# NB: AccessDeniedError is not 5 but 120 as seen in:
# https://msdn.microsoft.com/en-us/library/windows/desktop/bb762164%28v=vs.85%29.aspx
FileOperationErrorMap = {120: AccessDeniedError,
# https://msdn.microsoft.com/en-us/library/windows/desktop/ms681383%28v=vs.85%29.aspx
                         1223: CancelError,}

def __copyOrMove(operation, source, target, renameOnCollision, parent):
    """WIP shutil move and copy adapted from #96"""
    # renameOnCollision - if True auto-rename on moving collision, else ask
    # TODO(241): renameOnCollision NOT IMPLEMENTED
    doIt = _shutil.copytree if operation == FO_COPY else _shutil.move
    for fileFrom, fileTo in zip(source, target):
        if fileFrom.isdir():
            dest_dir = fileTo.join(fileFrom.tail)
            if dest_dir.exists():
                if not dest_dir.isdir():
                    raise DirectoryFileCollisionError(fileFrom, dest_dir)
                # dir exists at target, copy contents individually/recursively
                srcs, dests = [], []
                for content in _os.listdir(fileFrom.s):
                    srcs.append(fileFrom.join(content))
                    dests.append(dest_dir)
                __copyOrMove(operation, srcs, dests, renameOnCollision, parent)
            else:  # dir doesn't exist at the target, copy it
                doIt(fileFrom.s, fileTo.s)
        # copy the file, overwrite as needed
        elif fileFrom.isfile():  # or os.path.islink(file):
            # move may not work if the target exists, copy instead and
            # overwrite as needed
            try:
                _shutil.copy2(fileFrom.s, fileTo.s)
            except IOError as e:
                if e.errno != errno.ENOENT: raise
                # probably directory path does not exist, create it.
                fileTo.head.makedirs()
                _shutil.copy2(fileFrom.s, fileTo.s)
            if operation == FO_MOVE: fileFrom.remove() # then remove original
    return {} ##: the renames map ?

def _fileOperation(operation, source, target=None, allowUndo=True,
                   confirm=True, renameOnCollision=False, silent=False,
                   parent=None):
    """Docs WIP
    :param operation: one of FO_MOVE, FO_COPY, FO_DELETE, FO_RENAME
    :param source: a Path, basestring or an iterable of those (yak,
    only accept iterables)
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
    abspath = _os.path.abspath
    # source may be anything - see SHFILEOPSTRUCT - accepts list or item
    if isinstance(source, (Path, basestring)):
        source = [abspath(u'%s' % source)]
    else:
        source = [abspath(u'%s' % x) for x in source]
    # target may be anything ...
    target = target if target else u'' # abspath(u''): cwd (must be Mopy/)
    if isinstance(target, (Path, basestring)):
        target = [abspath(u'%s' % target)]
    else:
        target = [abspath(u'%s' % x) for x in target]
    if shell is not None:
        # flags
        flags = shellcon.FOF_WANTMAPPINGHANDLE # enables mapping return value !
        flags |= (len(target) > 1) * shellcon.FOF_MULTIDESTFILES
        if allowUndo: flags |= shellcon.FOF_ALLOWUNDO
        if not confirm: flags |= shellcon.FOF_NOCONFIRMATION
        if renameOnCollision: flags |= shellcon.FOF_RENAMEONCOLLISION
        if silent: flags |= shellcon.FOF_SILENT
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
                (parent, operation, source, target, flags, None, None))
        if result == 0:
            if aborted: raise SkipError()
            return dict(mapping)
        elif result == 2 and operation == FO_DELETE:
            # Delete failed because file didnt exist
            return dict(mapping)
        else:
            if result == 124:
                raise InvalidPathsError(source.replace(u'\x00', u'\n'),
                                         target.replace(u'\x00', u'\n'))
            raise FileOperationErrorMap.get(result, FileOperationError(result))
    else: # Use custom dialogs and such
        import balt # TODO(ut): local import, env should be above balt...
        source = map(GPath, source)
        target = map(GPath, target)
        if operation == FO_DELETE:
            # allowUndo - no effect, can't use recycle bin this way
            # confirm - ask if confirm is True
            # renameOnCollision - no effect, deleting files
            # silent - no real effect (we don't show visuals deleting this way)
            if confirm:
                message = _(u'Are you sure you want to permanently delete '
                            u'these %(count)d items?') % {'count':len(source)}
                message += u'\n\n' + '\n'.join([u' * %s' % x for x in source])
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

def shellDelete(files, parent=None, confirm=False, recycle=False):
    try:
        return _fileOperation(FO_DELETE, files, target=None, allowUndo=recycle,
                              confirm=confirm, renameOnCollision=True,
                              silent=False, parent=parent)
    except CancelError:
        if confirm:
            return None
        raise

def shellDeletePass(folder, parent=None):
    """Delete tmp dirs/files - ignore errors (but log them)."""
    if folder.exists():
        try: shellDelete(folder, parent=parent, confirm=False, recycle=False)
        except: deprint(u"Error deleting %s:" % folder, traceback=True)

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
        return _os.name != 'posix' and not path.s.startswith(u"\\")\
               and not path.drive().exists()
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

isUAC = False      # True if the game is under UAC protection

def setUAC(handle, uac=True):
    """Calls the Windows API to set a button as UAC"""
    if win32gui:
        win32gui.SendMessage(handle, 0x0000160C, None, uac)

def testUAC(gameDataPath):
    if _os.name != 'nt': # skip this when not in Windows
        return False
    print 'testing UAC' # TODO(ut): bypass in Linux !
    tmpDir = Path.tempDir()
    tempFile = tmpDir.join(u'_tempfile.tmp')
    dest = gameDataPath.join(u'_tempfile.tmp')
    with tempFile.open('wb'): pass # create the file
    try: # to move it into the Game/Data/ directory
        shellMove(tempFile, dest, askOverwrite=True, silent=True)
    except AccessDeniedError:
        return True
    finally:
        tmpDir.rmtree(safety=tmpDir.stail)
        shellDeletePass(dest)
    return False

def getJava():
    """Locate javaw.exe to launch jars from Bash."""
    if _os.name == 'posix':
        import subprocess
        java_bin_path = ''
        try:
            java_bin_path = subprocess.check_output('command -v java',
                                                    shell=True).rstrip('\n')
        except subprocess.CalledProcessError:
            pass # what happens when java doesn't exist?
        return GPath(java_bin_path)
    try:
        java_home = GPath(_os.environ['JAVA_HOME'])
        java = java_home.join('bin', u'javaw.exe')
        if java.exists(): return java
    except KeyError: # no JAVA_HOME
        pass
    win = GPath(_os.environ['SYSTEMROOT'])
    # Default location: Windows\System32\javaw.exe
    java = win.join(u'system32', u'javaw.exe')
    if not java.exists():
        # 1st possibility:
        #  - Bash is running as 32-bit
        #  - The only Java installed is 64-bit
        # Because Bash is 32-bit, Windows\System32 redirects to
        # Windows\SysWOW64.  So look in the ACTUAL System32 folder
        # by using Windows\SysNative
        java = win.join(u'sysnative', u'javaw.exe')
    if not java.exists():
        # 2nd possibility
        #  - Bash is running as 64-bit
        #  - The only Java installed is 32-bit
        # So javaw.exe would actually be in Windows\SysWOW64
        java = win.join(u'syswow64', u'javaw.exe')
    return java
