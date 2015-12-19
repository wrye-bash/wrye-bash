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
from bolt import GPath, BoltError, deprint # bin this ideally
import re as _re
import os as _os

try:
    import _winreg as winreg
except ImportError: # we're on linux
    winreg = None

def get_game_path(submod):
    """Check registry supplied game paths for the game.exe."""
    if not winreg: return None
    subkey, entry = submod.regInstallKeys
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
            exePath = installPath.join(submod.exe)
            if not exePath.exists(): continue
            return installPath
    return None

try: #  Import win32com, in case it's necessary
    from win32com.shell import shell, shellcon

    def _getShellPath(shellKey):
        path = shell.SHGetFolderPath(0, shellKey, None, 0)
        return path
except ImportError:
    shell = shellcon = None
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

def get_personal_path():
    if shell and shellcon:
        path = _getShellPath(shellcon.CSIDL_PERSONAL)
        sErrorInfo = _(u"Folder path extracted from win32com.shell.")
    else:
        path = _getShellPath('Personal')
        sErrorInfo = u'\n'.join(
                u'  %s: %s' % (key, envDefs[key]) for key in sorted(envDefs))
    return GPath(path), sErrorInfo

def get_local_app_data_path():
    if shell and shellcon:
        path = _getShellPath(shellcon.CSIDL_LOCAL_APPDATA)
        sErrorInfo = _(u"Folder path extracted from win32com.shell.")
    else:
        path = _getShellPath('Local AppData')
        sErrorInfo = u'\n'.join(
                u'  %s: %s' % (key, envDefs[key]) for key in sorted(envDefs))
    return GPath(path), sErrorInfo

__folderIcon = None # cached here
def get_default_app_icon(idex, target):
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
                filedata = filedata[1]
                __folderIcon = filedata
            else:
                filedata = __folderIcon
        else:
            icon_path = winreg.QueryValue(winreg.HKEY_CLASSES_ROOT,
                                          target.cext)
            pathKey = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT,
                                     u'%s\\DefaultIcon' % icon_path)
            filedata = winreg.EnumValue(pathKey, 0)[1]
            winreg.CloseKey(pathKey)
        icon, idex = filedata.split(u',')
        icon = _os.path.expandvars(icon)
        if not _os.path.isabs(icon):
            # Get the correct path to the dll
            for dir_ in _os.environ['PATH'].split(u';'):
                test = _os.path.join(dir_, icon)
                if _os.path.exists(test):
                    icon = test
                    break
    except OSError: # WAS except:
        deprint(_(u'Error finding icon for %s:') % target.s, traceback=True)
        icon = u'not\\a\\path'
    return icon, idex

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
    except Exception, e:
        if getattr(e, 'errno', 0) == 13:
            return False # Access denied
        elif getattr(e, 'winerror', 0) == 183:
            return False # Cannot create file if already exists
        else:
            raise
    return True
