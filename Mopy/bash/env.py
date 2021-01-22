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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""WIP module to encapsulate environment access - currently OS dependent stuff.
"""
from __future__ import print_function
import errno
import os as _os
import re as _re
import shutil as _shutil
import stat
from ctypes import byref, c_wchar_p, c_void_p, POINTER, Structure, windll, \
    wintypes
from uuid import UUID

from .bolt import GPath, deprint, Path, decoder, structs_cache
from .exception import BoltError, CancelError, SkipError, AccessDeniedError, \
    DirectoryFileCollisionError, FileOperationError, NonExistentDriveError

try:
    import _winreg as winreg  # PY3
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

def get_registry_path(subkey, entry, detection_file):
    """Check registry for a path to a program."""
    if not winreg: return None
    for hkey in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for wow6432 in (u'', u'Wow6432Node\\'):
            try:
                reg_key = winreg.OpenKey(
                    hkey, u'Software\\%s%s' % (wow6432, subkey), 0,
                    winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
                reg_val = winreg.QueryValueEx(reg_key, entry)
            except OSError:
                continue
            if reg_val[1] != winreg.REG_SZ: continue
            installPath = GPath(reg_val[0])
            if not installPath.exists(): continue
            exePath = installPath.join(detection_file)
            if not exePath.exists(): continue
            return installPath
    return None

def get_registry_game_path(submod):
    """Check registry supplied game paths for the game detection file."""
    subkey, entry = submod.regInstallKeys
    return get_registry_path(subkey, entry, submod.game_detect_file)

try: # Python27\Lib\site-packages\win32comext\shell
    from win32com.shell import shell, shellcon
    from win32com.shell.shellcon import FO_DELETE, FO_MOVE, FO_COPY, \
        FO_RENAME, FOF_NOCONFIRMMKDIR

    def _getShellPath(shellKey):
        path = shell.SHGetFolderPath(0, shellKey, None, 0)
        return path
except ImportError:
    shell = shellcon = None
    FO_MOVE = 1
    FO_COPY = 2
    FO_DELETE = 3
    FO_RENAME = 4
    FOF_NOCONFIRMMKDIR = 512
    reEnv = _re.compile(u'%(\w+)%', _re.U)
    envDefs = _os.environ

    def subEnv(match):
        env_var = match.group(1).upper()
        if not envDefs.get(env_var):
            raise BoltError(u"Can't find user directories in windows registry."
                u'\n>> See "If Bash Won\'t Start" in bash docs for help.')
        return envDefs[env_var]

    def _getShellPath(folderKey): ##: mkdirs
        if not winreg:  # Linux HACK
            home = _os.path.expanduser(u'~')
            return {u'Personal': home,
                    u'Local AppData': home + u'/.local/share'}[folderKey]
        regKey = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r'Software\Microsoft\Windows\CurrentVersion'
                                r'\Explorer\User Shell Folders')
        try:
            path = winreg.QueryValueEx(regKey, folderKey)[0]
        except WindowsError:
            raise BoltError(u"Can't find user directories in windows registry."
                            u'.\n>> See "If Bash Won\'t Start" in bash docs '
                            u'for help.')
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
        personal_path = get_known_path(FOLDERID.Documents)
        error_info = _(u'Folder path retrieved via SHGetKnownFolderPath')
    else:
        personal_path = _getShellPath(u'Personal')
        error_info = __get_error_info()
    return GPath(personal_path), error_info

def get_local_app_data_path():
    if shell and shellcon:
        local_path = get_known_path(FOLDERID.LocalAppData)
        error_info = _(u'Folder path retrieved via SHGetKnownFolderPath')
    else:
        local_path = _getShellPath(u'Local AppData')
        error_info = __get_error_info()
    return GPath(local_path), error_info

def __get_error_info():
    try:
        sErrorInfo = u'\n'.join(u'  %s: %s' % (key, envDefs[key])
                                for key in sorted(envDefs))
    except UnicodeDecodeError:
        deprint(u'Error decoding _os.environ', traceback=True)
        sErrorInfo = u'\n'.join(u'  %s: %s' % (key, decoder(envDefs[key]))
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
            for dir_ in _os.environ[u'PATH'].split(u';'):
                test = _os.path.join(dir_, icon)
                if _os.path.exists(test):
                    icon = test
                    break
    except: # TODO(ut) comment the code above - what exception can I get here?
        deprint(u'Error finding icon for %s:' % target, traceback=True)
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
        sh = win32client.Dispatch(u'WScript.Shell')
        for lnk in apps_dir.list():
            lnk = apps_dir.join(lnk)
            if lnk.cext == u'.lnk' and lnk.isfile():
                shortcut = sh.CreateShortCut(lnk.s)
                shortcut_descr = shortcut.Description
                if not shortcut_descr:
                    shortcut_descr = u' '.join((_(u'Launch'), lnk.sbody))
                links[lnk] = (shortcut.TargetPath, shortcut.IconLocation,
                              # shortcut.WorkingDirectory, shortcut.Arguments,
                              shortcut_descr)
    except:
        deprint(u'Error initializing links:', traceback=True)
    return links

def init_app_links(apps_dir, badIcons, iconList):
    init_params = []
    for path, (target, icon, shortcut_descr) in _get_app_links(
            apps_dir).iteritems():
        if target.lower().find(u'' r'installer\{') != -1: # msi shortcuts: dc0c8de
            target = path
        else:
            target = GPath(target)
        if not target.exists(): continue
        # Target exists - extract path, icon and shortcut_descr
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
                icon = iconList(GPath(fileName))
                # Last, use the 'x' icon
            else:
                icon = badIcons
        init_params.append((path, icon, shortcut_descr))
    return init_params

def test_permissions(path, permissions=u'rwcd'):
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
            node_size = node.size
            if smallsize == -1 or node_size < smallsize:
                smallsize = node_size
                ret = node
        return ret
    #--Test read permissions
    try:
        smallestFile = None
        path_exists = path.exists()
        if u'r' in permissions and path_exists:
            smallestFile = getSmallest()
            if smallestFile:
                with smallestFile.open(u'rb'):
                    pass
        #--Test write permissions
        if u'w' in permissions and path_exists:
            smallestFile = smallestFile or getSmallest()
            if smallestFile:
                with smallestFile.open(u'ab'):
                    pass
        #--Test file creation permission (only for directories)
        if u'c' in permissions:
            if path.isdir() or not path_exists:
                if not path_exists:
                    path.makedirs()
                    removeAtEnd = True
                else:
                    removeAtEnd = False
                perm_temp = getTemp(path)
                with perm_temp.open(u'wb'):
                    pass
                perm_temp.remove()
                if removeAtEnd:
                    path.removedirs()
        #--Test file deletion permission
        if u'd' in permissions and path_exists:
            smallestFile = smallestFile or getSmallest()
            if smallestFile:
                smallest_temp = getTemp(smallestFile)
                smallestFile.copyTo(smallest_temp)
                smallestFile.remove()
                smallest_temp.moveTo(smallestFile)
    except Exception as e:
        if getattr(e, u'errno', 0) == 13:
            return False # Access denied
        elif getattr(e, u'winerror', 0) == 183:
            return False # Cannot create file if already exists
        else:
            raise
    return True

# OS agnostic get file version function and helper functions
def get_file_version(filename):
    """
    Return the version of a dll/exe, using the native win32 functions
    if available and otherwise a pure python implementation that works
    on Linux.

    :param filename: The file from which the version should be read.
    :return A 4-int tuple, for example (1, 9, 32, 0).
    """
    # If it's a symbolic link (i.e. a user-added app), resolve it first
    if win32client and filename.endswith(u'.lnk'):
        sh = win32client.Dispatch(u'WScript.Shell')
        shortcut = sh.CreateShortCut(filename)
        filename = shortcut.TargetPath
    if win32api is None:
        # TODO(inf) The linux method needs support for string fields
        return _linux_get_file_version_info(filename)
    else:
        # These are ordered to maximize performance: fixed field with
        # FileVersion is almost always enough, so that's first. SSE needs the
        # string fields with ProductVersion, so that's the second one. After
        # that, we prefer the fixed one since it's faster.
        curr_ver = _query_fixed_field_version(filename, u'FileVersion')
        if not _should_ignore_ver(curr_ver):
            return curr_ver
        curr_ver = _query_string_field_version(filename, u'ProductVersion')
        if not _should_ignore_ver(curr_ver):
            return curr_ver
        curr_ver = _query_fixed_field_version(filename, u'ProductVersion')
        if not _should_ignore_ver(curr_ver):
            return curr_ver
        return _query_string_field_version(filename, u'FileVersion')

def _should_ignore_ver(test_ver):
    """
    Small helper method to determine whether or not a version should be
    ignored. Versions are ignored if they are 1.0.0.0 or 0.0.0.0.

    :param test_ver: The version to test. A tuple containing 4 integers.
    :return: True if the specified versiom should be ignored.
    """
    return test_ver == (1, 0, 0, 0) or test_ver == (0, 0, 0, 0)

def _query_string_field_version(file_name, version_prefix):
    """
    Retrieves the version with the specified prefix from the specified file via
    its string fields.

    :param file_name: The file from which the version should be read.
    :param version_prefix: The prefix to use. Can be either FileVersion or
    ProductVersion.
    :return: A 4-tuple of integers containing the version of the file.
    """
    # We need to ask for language and copepage first, before we can
    # query the actual version.
    l_query = u'\\VarFileInfo\\Translation'
    try:
        lang, codepage = win32api.GetFileVersionInfo(file_name, l_query)[0]
    except win32api.error:
        # File does not have a string field section
        return 0, 0, 0, 0
    ver_query = u'\\StringFileInfo\\%04X%04X\\%s' % (lang, codepage,
                                                     version_prefix)
    full_ver = win32api.GetFileVersionInfo(file_name, ver_query)
    # xSE uses commas in its version fields, so use this 'heuristic'
    split_on = u',' if u',' in full_ver else u'.'
    try:
        return tuple([int(part) for part in full_ver.split(split_on)])
    except ValueError:
        return 0, 0, 0, 0

def _query_fixed_field_version(file_name, version_prefix):
    """
    Retrieves the version with the specified prefix from the specified file via
    its fixed fields. This is faster than using the string fields, but not all
    EXEs set them (e.g. SkyrimSE.exe).

    :param file_name: The file from which the version should be read.
    :param version_prefix: The prefix to use. Can be either FileVersion or
    ProductVersion.
    :return: A 4-tuple of integers containing the version of the file.
    """
    try:
        info = win32api.GetFileVersionInfo(file_name, u'\\')
    except win32api.error:
        # File does not have a fixed field section
        return 0, 0, 0, 0
    ms = info[u'%sMS' % version_prefix]
    ls = info[u'%sLS' % version_prefix]
    return win32api.HIWORD(ms), win32api.LOWORD(ms), win32api.HIWORD(ls), \
           win32api.LOWORD(ls)

def _linux_get_file_version_info(filename):
    """A python replacement for win32api.GetFileVersionInfo that can be used
    on systems where win32api isn't available."""
    _WORD, _DWORD = structs_cache[u'<H'].unpack_from, structs_cache[
        u'<I'].unpack_from
    def _read(_struct_unp, file_obj, offset=0, count=1, absolute=False):
        """Read one or more chunks from the file, either a word or dword."""
        file_obj.seek(offset, not absolute)
        result = [_struct_unp(file_obj)[0] for x in xrange(count)] ##: array.fromfile(f, n)
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
            if info[:-1] == u'VS_VERSION_INFO':
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
    with open(filename, u'rb') as f:
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
            if f.read(8).rstrip(b'\x00') != b'.rsrc':  # section name_
                continue
            section_va = _read(_DWORD, f, offset=4)
            raw_data_pos = _read(_DWORD, f, offset=4)
            section_resources_pos = raw_data_pos + resources_va - section_va
            num_named, num_id = _read(_WORD, f, count=2, absolute=True,
                                      offset=section_resources_pos + 12)
            for resource_num in xrange(num_named + num_id):
                resource_pos = section_resources_pos + 16 + 8 * resource_num
                name_ = _read(_DWORD, f, offset=resource_pos, absolute=True)
                if name_ != 16: continue # RT_VERSION
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
        return ()

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
                source_paths, dests = [], []
                for content in _os.listdir(fileFrom.s):
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
                   parent=None, __shell=True):
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
            raise FileOperationErrorMap.get(result, FileOperationError(result))
    else: # Use custom dialogs and such
        from . import balt # TODO(ut): local import, env should be above balt...
        source = map(GPath, source)
        target = map(GPath, target)
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
        return (_os.name != u'posix' and not path.s.startswith(u'\\')
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

isUAC = False      # True if the game is under UAC protection

def setUAC(handle, uac=True):
    """Calls the Windows API to set a button as UAC"""
    if isUAC and win32gui:
        win32gui.SendMessage(handle, 0x0000160C, None, uac)

def testUAC(gameDataPath):
    if _os.name != u'nt': # skip this when not in Windows
        return False
    print(u'testing UAC')
    tmpDir = Path.tempDir()
    tempFile = tmpDir.join(u'_tempfile.tmp')
    dest = gameDataPath.join(u'_tempfile.tmp')
    with tempFile.open(u'wb'): pass # create the file
    try: # to move it into the Game/Data/ directory
        shellMove(tempFile, dest, silent=True)
    except AccessDeniedError:
        return True
    finally:
        shellDeletePass(tmpDir)
        shellDeletePass(dest)
    return False

def getJava():
    """Locate javaw.exe to launch jars from Bash."""
    if _os.name == u'posix':
        import subprocess
        java_bin_path = u''
        try:
            java_bin_path = subprocess.check_output(u'command -v java',
                                                    shell=True).rstrip(u'\n')
        except subprocess.CalledProcessError:
            pass # what happens when java doesn't exist?
        return GPath(java_bin_path)
    try:
        java_home = GPath(_os.environ[u'JAVA_HOME'])
        java = java_home.join(u'bin', u'javaw.exe')
        if java.exists(): return java
    except KeyError: # no JAVA_HOME
        pass
    win = GPath(_os.environ[u'SYSTEMROOT'])
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

# TODO(inf) Maybe move to windows.py? Circular dependency though...
# All code starting from the 'BEGIN MIT-LICENSED PART' comment and until the
# 'END MIT-LICENSED PART' comment is based on
# https://gist.github.com/mkropat/7550097 by Michael Kropat
# Modifications made for py3 compatibility and to conform to our code style
# BEGIN MIT-LICENSED PART =====================================================
# http://msdn.microsoft.com/en-us/library/windows/desktop/aa373931.aspx
# PY3: Verify that this struct actually needs unicode strings, not bytes
class GUID(Structure):
    _fields_ = [
        (u'Data1', wintypes.DWORD),
        (u'Data2', wintypes.WORD),
        (u'Data3', wintypes.WORD),
        (u'Data4', wintypes.BYTE * 8)
    ]

    def __init__(self, uuid_):
        super(GUID, self).__init__()
        self.Data1, self.Data2, self.Data3, self.Data4[0], self.Data4[1], \
        rest = uuid_.fields
        for i in range(2, 8):
            self.Data4[i] = rest>>(8 - i - 1)*8 & 0xff

# http://msdn.microsoft.com/en-us/library/windows/desktop/dd378457.aspx
class FOLDERID(object):
    AccountPictures         = UUID(u'{008ca0b1-55b4-4c56-b8a8-4de4b299d3be}')
    AdminTools              = UUID(u'{724EF170-A42D-4FEF-9F26-B60E846FBA4F}')
    ApplicationShortcuts    = UUID(u'{A3918781-E5F2-4890-B3D9-A7E54332328C}')
    CameraRoll              = UUID(u'{AB5FB87B-7CE2-4F83-915D-550846C9537B}')
    CDBurning               = UUID(u'{9E52AB10-F80D-49DF-ACB8-4330F5687855}')
    CommonAdminTools        = UUID(u'{D0384E7D-BAC3-4797-8F14-CBA229B392B5}')
    CommonOEMLinks          = UUID(u'{C1BAE2D0-10DF-4334-BEDD-7AA20B227A9D}')
    CommonPrograms          = UUID(u'{0139D44E-6AFE-49F2-8690-3DAFCAE6FFB8}')
    CommonStartMenu         = UUID(u'{A4115719-D62E-491D-AA7C-E74B8BE3B067}')
    CommonStartup           = UUID(u'{82A5EA35-D9CD-47C5-9629-E15D2F714E6E}')
    CommonTemplates         = UUID(u'{B94237E7-57AC-4347-9151-B08C6C32D1F7}')
    Contacts                = UUID(u'{56784854-C6CB-462b-8169-88E350ACB882}')
    Cookies                 = UUID(u'{2B0F765D-C0E9-4171-908E-08A611B84FF6}')
    Desktop                 = UUID(u'{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}')
    DeviceMetadataStore     = UUID(u'{5CE4A5E9-E4EB-479D-B89F-130C02886155}')
    Documents               = UUID(u'{FDD39AD0-238F-46AF-ADB4-6C85480369C7}')
    DocumentsLibrary        = UUID(u'{7B0DB17D-9CD2-4A93-9733-46CC89022E7C}')
    Downloads               = UUID(u'{374DE290-123F-4565-9164-39C4925E467B}')
    Favorites               = UUID(u'{1777F761-68AD-4D8A-87BD-30B759FA33DD}')
    Fonts                   = UUID(u'{FD228CB7-AE11-4AE3-864C-16F3910AB8FE}')
    GameTasks               = UUID(u'{054FAE61-4DD8-4787-80B6-090220C4B700}')
    History                 = UUID(u'{D9DC8A3B-B784-432E-A781-5A1130A75963}')
    ImplicitAppShortcuts    = UUID(u'{BCB5256F-79F6-4CEE-B725-DC34E402FD46}')
    InternetCache           = UUID(u'{352481E8-33BE-4251-BA85-6007CAEDCF9D}')
    Libraries               = UUID(u'{1B3EA5DC-B587-4786-B4EF-BD1DC332AEAE}')
    Links                   = UUID(u'{bfb9d5e0-c6a9-404c-b2b2-ae6db6af4968}')
    LocalAppData            = UUID(u'{F1B32785-6FBA-4FCF-9D55-7B8E7F157091}')
    LocalAppDataLow         = UUID(u'{A520A1A4-1780-4FF6-BD18-167343C5AF16}')
    LocalizedResourcesDir   = UUID(u'{2A00375E-224C-49DE-B8D1-440DF7EF3DDC}')
    Music                   = UUID(u'{4BD8D571-6D19-48D3-BE97-422220080E43}')
    MusicLibrary            = UUID(u'{2112AB0A-C86A-4FFE-A368-0DE96E47012E}')
    NetHood                 = UUID(u'{C5ABBF53-E17F-4121-8900-86626FC2C973}')
    OriginalImages          = UUID(u'{2C36C0AA-5812-4b87-BFD0-4CD0DFB19B39}')
    PhotoAlbums             = UUID(u'{69D2CF90-FC33-4FB7-9A0C-EBB0F0FCB43C}')
    PicturesLibrary         = UUID(u'{A990AE9F-A03B-4E80-94BC-9912D7504104}')
    Pictures                = UUID(u'{33E28130-4E1E-4676-835A-98395C3BC3BB}')
    Playlists               = UUID(u'{DE92C1C7-837F-4F69-A3BB-86E631204A23}')
    PrintHood               = UUID(u'{9274BD8D-CFD1-41C3-B35E-B13F55A758F4}')
    Profile                 = UUID(u'{5E6C858F-0E22-4760-9AFE-EA3317B67173}')
    ProgramData             = UUID(u'{62AB5D82-FDC1-4DC3-A9DD-070D1D495D97}')
    ProgramFiles            = UUID(u'{905e63b6-c1bf-494e-b29c-65b732d3d21a}')
    ProgramFilesX64         = UUID(u'{6D809377-6AF0-444b-8957-A3773F02200E}')
    ProgramFilesX86         = UUID(u'{7C5A40EF-A0FB-4BFC-874A-C0F2E0B9FA8E}')
    ProgramFilesCommon      = UUID(u'{F7F1ED05-9F6D-47A2-AAAE-29D317C6F066}')
    ProgramFilesCommonX64   = UUID(u'{6365D5A7-0F0D-45E5-87F6-0DA56B6A4F7D}')
    ProgramFilesCommonX86   = UUID(u'{DE974D24-D9C6-4D3E-BF91-F4455120B917}')
    Programs                = UUID(u'{A77F5D77-2E2B-44C3-A6A2-ABA601054A51}')
    Public                  = UUID(u'{DFDF76A2-C82A-4D63-906A-5644AC457385}')
    PublicDesktop           = UUID(u'{C4AA340D-F20F-4863-AFEF-F87EF2E6BA25}')
    PublicDocuments         = UUID(u'{ED4824AF-DCE4-45A8-81E2-FC7965083634}')
    PublicDownloads         = UUID(u'{3D644C9B-1FB8-4f30-9B45-F670235F79C0}')
    PublicGameTasks         = UUID(u'{DEBF2536-E1A8-4c59-B6A2-414586476AEA}')
    PublicLibraries         = UUID(u'{48DAF80B-E6CF-4F4E-B800-0E69D84EE384}')
    PublicMusic             = UUID(u'{3214FAB5-9757-4298-BB61-92A9DEAA44FF}')
    PublicPictures          = UUID(u'{B6EBFB86-6907-413C-9AF7-4FC2ABF07CC5}')
    PublicRingtones         = UUID(u'{E555AB60-153B-4D17-9F04-A5FE99FC15EC}')
    PublicUserTiles         = UUID(u'{0482af6c-08f1-4c34-8c90-e17ec98b1e17}')
    PublicVideos            = UUID(u'{2400183A-6185-49FB-A2D8-4A392A602BA3}')
    QuickLaunch             = UUID(u'{52a4f021-7b75-48a9-9f6b-4b87a210bc8f}')
    Recent                  = UUID(u'{AE50C081-EBD2-438A-8655-8A092E34987A}')
    RecordedTVLibrary       = UUID(u'{1A6FDBA2-F42D-4358-A798-B74D745926C5}')
    ResourceDir             = UUID(u'{8AD10C31-2ADB-4296-A8F7-E4701232C972}')
    Ringtones               = UUID(u'{C870044B-F49E-4126-A9C3-B52A1FF411E8}')
    RoamingAppData          = UUID(u'{3EB685DB-65F9-4CF6-A03A-E3EF65729F3D}')
    RoamedTileImages        = UUID(u'{AAA8D5A5-F1D6-4259-BAA8-78E7EF60835E}')
    RoamingTiles            = UUID(u'{00BCFC5A-ED94-4e48-96A1-3F6217F21990}')
    SampleMusic             = UUID(u'{B250C668-F57D-4EE1-A63C-290EE7D1AA1F}')
    SamplePictures          = UUID(u'{C4900540-2379-4C75-844B-64E6FAF8716B}')
    SamplePlaylists         = UUID(u'{15CA69B3-30EE-49C1-ACE1-6B5EC372AFB5}')
    SampleVideos            = UUID(u'{859EAD94-2E85-48AD-A71A-0969CB56A6CD}')
    SavedGames              = UUID(u'{4C5C32FF-BB9D-43b0-B5B4-2D72E54EAAA4}')
    SavedSearches           = UUID(u'{7d1d3a04-debb-4115-95cf-2f29da2920da}')
    Screenshots             = UUID(u'{b7bede81-df94-4682-a7d8-57a52620b86f}')
    SearchHistory           = UUID(u'{0D4C3DB6-03A3-462F-A0E6-08924C41B5D4}')
    SearchTemplates         = UUID(u'{7E636BFE-DFA9-4D5E-B456-D7B39851D8A9}')
    SendTo                  = UUID(u'{8983036C-27C0-404B-8F08-102D10DCFD74}')
    SidebarDefaultParts     = UUID(u'{7B396E54-9EC5-4300-BE0A-2482EBAE1A26}')
    SidebarParts            = UUID(u'{A75D362E-50FC-4fb7-AC2C-A8BEAA314493}')
    SkyDrive                = UUID(u'{A52BBA46-E9E1-435f-B3D9-28DAA648C0F6}')
    SkyDriveCameraRoll      = UUID(u'{767E6811-49CB-4273-87C2-20F355E1085B}')
    SkyDriveDocuments       = UUID(u'{24D89E24-2F19-4534-9DDE-6A6671FBB8FE}')
    SkyDrivePictures        = UUID(u'{339719B5-8C47-4894-94C2-D8F77ADD44A6}')
    StartMenu               = UUID(u'{625B53C3-AB48-4EC1-BA1F-A1EF4146FC19}')
    Startup                 = UUID(u'{B97D20BB-F46A-4C97-BA10-5E3608430854}')
    System                  = UUID(u'{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}')
    SystemX86               = UUID(u'{D65231B0-B2F1-4857-A4CE-A8E7C6EA7D27}')
    Templates               = UUID(u'{A63293E8-664E-48DB-A079-DF759E0509F7}')
    UserPinned              = UUID(u'{9E3995AB-1F9C-4F13-B827-48B24B6C7174}')
    UserProfiles            = UUID(u'{0762D272-C50A-4BB0-A382-697DCD729B80}')
    UserProgramFiles        = UUID(u'{5CD7AEE2-2219-4A67-B85D-6C9CE15660CB}')
    UserProgramFilesCommon  = UUID(u'{BCBD3057-CA5C-4622-B42D-BC56DB0AE516}')
    Videos                  = UUID(u'{18989B1D-99B5-455B-841C-AB7C74E4DDFC}')
    VideosLibrary           = UUID(u'{491E922F-5643-4AF4-A7EB-4E7A138D8174}')
    Windows                 = UUID(u'{F38BF404-1D43-42F2-9305-67DE0B28FC23}')

# http://msdn.microsoft.com/en-us/library/windows/desktop/bb762188.aspx
class UserHandle(object):
    current = wintypes.HANDLE(0)
    common  = wintypes.HANDLE(-1)

# http://msdn.microsoft.com/en-us/library/windows/desktop/ms680722.aspx
_CoTaskMemFree = windll.ole32.CoTaskMemFree
_CoTaskMemFree.restype= None
_CoTaskMemFree.argtypes = [c_void_p]

# http://msdn.microsoft.com/en-us/library/windows/desktop/bb762188.aspx
# http://web.archive.org/web/20111025090317/http://www.themacaque.com/?p=954
_SHGetKnownFolderPath = windll.shell32.SHGetKnownFolderPath
_SHGetKnownFolderPath.argtypes = [
    POINTER(GUID), wintypes.DWORD, wintypes.HANDLE, POINTER(c_wchar_p)
]

def get_known_path(known_folder_id, user_handle=UserHandle.current):
    kf_id = GUID(known_folder_id)
    pPath = c_wchar_p()
    S_OK = 0
    if _SHGetKnownFolderPath(byref(kf_id), 0, user_handle,
                             byref(pPath)) != S_OK:
        raise RuntimeError(u"Failed to retrieve known folder path '%r'" %
                           known_folder_id)
    path = pPath.value
    _CoTaskMemFree(pPath)
    return path
# END MIT-LICENSED PART =======================================================
