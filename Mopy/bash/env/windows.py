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
"""Encapsulates Windows-specific classes and methods."""

import os
import re
import sys
import datetime
import xml.etree.ElementTree as xml
import winreg
from ctypes import byref, c_wchar_p, c_void_p, POINTER, Structure, windll, \
    wintypes, WINFUNCTYPE, c_uint, c_long, Union, c_ushort, c_int, \
    c_longlong, c_ulong, c_wchar, sizeof, wstring_at, ARRAY
import functools
from uuid import UUID

import win32api
import win32com.client as win32client
import win32gui

from ..bolt import GPath, deprint, Path
from ..exception import AccessDeniedError, BoltError
from .common import  WinAppInfo, WinAppVersionInfo, real_sys_prefix

# API - Constants =============================================================
_isUAC = False

from ctypes.wintypes import MAX_PATH
from win32com.shell.shellcon import FO_DELETE, FO_MOVE, FO_COPY, \
    FO_RENAME, FOF_NOCONFIRMMKDIR

try:
    _indirect = windll.comctl32.TaskDialogIndirect
    _indirect.restype = c_void_p
    TASK_DIALOG_AVAILABLE = True
except AttributeError:
    TASK_DIALOG_AVAILABLE = False

# Button constants from TaskDialog - happen to mirror wxPython's
BTN_OK                          = 5100
BTN_CANCEL                      = 5101
BTN_YES                         = 5103
BTN_NO                          = 5104
GOOD_EXITS                      = (BTN_OK, BTN_YES)

# Internals ===================================================================
_re_env = re.compile(r'%(\w+)%', re.U)

def _subEnv(match):
    env_var = match.group(1).upper()
    # NOTE: On Python 3, this would be better as a try...except KeyError,
    # then raise BoltError(...) from None
    env_val = os.environ.get(env_var, None)
    if not env_val:
        raise BoltError(u"Can't find user directories in windows registry."
            u'\n>> See "If Bash Won\'t Start" in bash docs for help.')
    return env_val

def _getShellPath(folderKey):
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
    path = _re_env.sub(_subEnv, path)
    return path

__folderIcon = None # cached here
def _get_default_app_icon(idex, target):
    # Use the default icon for that file type
    if winreg is None: # FIXME(inf) linux.py
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
        if os.path.isabs(filedata) and os.path.isfile(filedata):
            icon = filedata
        else:
            icon, idex = filedata.split(u',')
            icon = os.path.expandvars(icon)
        if not os.path.isabs(icon):
            # Get the correct path to the dll
            for dir_ in os.environ[u'PATH'].split(u';'):
                test = os.path.join(dir_, icon)
                if os.path.exists(test):
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
    return _parse_version_string(full_ver)

def _parse_version_string(full_ver):
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

def _datetime_from_windows_filetime(filetime):
    """Convert a Windows 64-bit FileTime to a Python datetime object."""
    ## Maybe belongs in bolt?
    # Starting time for Windows FileTime is Jan 1, 1601, midnight
    time_zero = datetime.datetime(1601, 1, 1, 0, 0, 0)
    # FileTime is stored as 100's of nanoseconds
    delta = datetime.timedelta(microseconds=filetime / 10)
    try:
        return time_zero + delta
    except OverflowError:
        # Can occur if delta is very large
        return time_zero

class _WindowsStoreFinder(object):
    developer_ids = {
        u'Bethesda': u'3275kfvn8vcwc'
    }

    def __init__(self):
        self.info_cache = {} # app_name -> WinAppInfo

    @staticmethod
    def _read_registry_string(reg_key, string_name):
        string_value, string_type = winreg.QueryValueEx(reg_key, string_name)
        if string_type == winreg.REG_SZ:
            return string_value
        else:
            return None

    @staticmethod
    def _read_registry_filetime(reg_key, filetime_name):
        filetime, value_type = winreg.QueryValueEx(reg_key, filetime_name)
        if value_type == winreg.REG_QWORD:
            return _datetime_from_windows_filetime(filetime)
        return datetime.datetime.fromtimestamp(0)

    @classmethod
    def _get_package_locations(cls, package_index):
        """Get all applicable information we wish to cache about a package."""
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                    r'SOFTWARE\Microsoft\Windows\CurrentVersion\AppModel'
                    r'\StateRepository\Cache\Package\Data') as pfn_key:
                with winreg.OpenKey(pfn_key, package_index) as index_key:
                    install_location = cls._read_registry_string(index_key,
                        u'InstalledLocation')
                    mutable_location = cls._read_registry_string(index_key,
                        u'MutableLocation')
                    return install_location, mutable_location
        except WindowsError:
            # Either on a windows version without windows apps, or the
            # specific app is not installed
            return None, None

    @staticmethod
    def _get_package_index(package_full_name):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                r'SOFTWARE\Microsoft\Windows\CurrentVersion\AppModel'
                r'\StateRepository\Cache\Package\Index'
                r'\PackageFullName') as pfn_key:
                with winreg.OpenKey(pfn_key, package_full_name) as index_key:
                    return winreg.EnumKey(index_key, 0)
        except WindowsError:
            # Windows version without apps, or not installed
            return None

    @staticmethod
    def _get_package_full_names(package_name):
        """Get all `package_full_name`s for this app."""
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT,
                r'Local Settings\Software\Microsoft\Windows\CurrentVersion'
                r'\AppModel\Repository\Families') as families_key:
                with winreg.OpenKey(families_key, package_name) as family_key:
                    num_families = winreg.QueryInfoKey(family_key)[0]
                    return [winreg.EnumKey(family_key, i)
                            for i in range(num_families)]
        except WindowsError:
            # Windows version without apps, or not installed
            return []

    @classmethod
    def _get_package_install_time(cls, package_name, full_name):
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT,
                r'Local Settings\Software\Microsoft\Windows\CurrentVersion'
                r'\AppModel\Repository\Families') as families_key:
                with winreg.OpenKey(families_key, package_name) as p_key:
                    with winreg.OpenKey(p_key, full_name) as pfn_key:
                        return cls._read_registry_filetime(pfn_key,
                                                           u'InstallTime')
        except (WindowsError, ValueError):
            # Windows version without the app store, or not installed
            # or InstallTime value wasn't of the right type
            pass
        return datetime.datetime.fromtimestamp(0)

    @staticmethod
    def _get_package_version_from_full_name(package_full_name):
        parts = package_full_name.split(u'_')
        # Expected format is {package_name}_{version}_{platform}__{publisher_id}
        if len(parts) != 5:
            return u'0.0.0.0'
        return parts[1]

    @staticmethod
    def _get_manifest_info(mutable_location, app_name):
        version = None
        entry_point = u''
        try:
            manifest = mutable_location.join(u'appxmanifest.xml')
            tree = xml.parse(manifest.s)
            root = tree.getroot()
            # AppxManifest.xml uses XML namespaces, don't try to hard to
            # extract the applicable namespace
            namespace = root.tag.split(u'}')[0].strip(u'{')
            version_template = u"{%s}Identity[@Version][@Name='%s']"
            entry_template = u'./{%s}Applications/{%s}Application[@Id]' \
                             u'[@EntryPoint][@Executable]'
            # First get the version
            identity = root.find(version_template % (namespace, app_name))
            if identity is not None:
                # NOTE: `if identity` throws a FutureWarning
                version = identity.get(u'Version')
            # Next get the entry point
            entry = root.find(entry_template % (namespace, namespace))
            if entry is not None:
                entry_point = entry.get(u'Id')
        except (xml.ParseError, OSError):
            # Parsing error, or the file doesn't exist
            pass
        return version, entry_point

    def get_app_info(self, app_name, publisher_name=None, publisher_id=None):
        """Public interface: returns a WinAppInfo object with all applicable
           information about the application."""
        if not publisher_id:
            publisher_id = self.developer_ids.get(publisher_name)
        if not publisher_id:
            # Not a common publisher name, need the publisher id
            return WinAppInfo()
        package_name = app_name + '_' + publisher_id
        try:
            return self.info_cache[package_name]
        except KeyError:
            # Not cached, look everything up
            pass
        app_info = WinAppInfo(publisher_name, publisher_id, package_name)
        # Gather all versions of the app
        package_full_names = self._get_package_full_names(package_name)
        for full_name in package_full_names:
            package_index = self._get_package_index(full_name)
            install_location, mutable_location = \
                self._get_package_locations(package_index)
            install_location = GPath(install_location)
            mutable_location = GPath(mutable_location)
            install_time = self._get_package_install_time(package_name,
                                                          full_name)
            version, entry_point = self._get_manifest_info(mutable_location,
                                                           app_name)
            if not version:
                version = self._get_package_version_from_full_name(full_name)
            version = _parse_version_string(version)
            version_info = WinAppVersionInfo(
                full_name, install_location, mutable_location, version,
                install_time, entry_point)
            app_info.versions[full_name] = version_info
        self.info_cache[package_name] = app_info
        return app_info

_win_store_finder = _WindowsStoreFinder()

# All code starting from the 'BEGIN MIT-LICENSED PART' comment and until the
# 'END MIT-LICENSED PART' comment is based on
# https://gist.github.com/mkropat/7550097 by Michael Kropat
# Modifications made for python3 compatibility and to conform to our code style
# BEGIN MIT-LICENSED PART =====================================================
# http://msdn.microsoft.com/en-us/library/windows/desktop/aa373931.aspx
class _GUID(Structure):
    _fields_ = [
        (u'Data1', wintypes.DWORD),
        (u'Data2', wintypes.WORD),
        (u'Data3', wintypes.WORD),
        (u'Data4', wintypes.BYTE * 8)
    ]

    def __init__(self, uuid_):
        super(_GUID, self).__init__()
        self.Data1, self.Data2, self.Data3, self.Data4[0], self.Data4[1], \
        rest = uuid_.fields
        for i in range(2, 8):
            self.Data4[i] = rest>>(8 - i - 1)*8 & 0xff

# http://msdn.microsoft.com/en-us/library/windows/desktop/dd378457.aspx
class _FOLDERID(object):
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
class _UserHandle(object):
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
    POINTER(_GUID), wintypes.DWORD, wintypes.HANDLE, POINTER(c_wchar_p)
]

def _get_known_path(known_folder_id, user_handle=_UserHandle.current):
    kf_id = _GUID(known_folder_id)
    pPath = c_wchar_p()
    S_OK = 0
    if _SHGetKnownFolderPath(byref(kf_id), 0, user_handle,
                             byref(pPath)) != S_OK:
        raise RuntimeError(u"Failed to retrieve known folder path '%r' - this "
                           u"is most likely caused by OneDrive, see General "
                           u"Readme" % known_folder_id)
    path = pPath.value
    _CoTaskMemFree(pPath)
    return path
# END MIT-LICENSED PART =======================================================

# All code from the 'BEGIN TASKDIALOG PART' comment to the 'END TASKDIALOG
# PART' comment is licensed under the following license:
#
#       taskdialog.py
#
#       Copyright © 2009 Te-jé Rodgers <contact@tejerodgers.com>
#
#       This file is part of Curtains
#
#       Curtains is free software; you can redistribute it and/or modify
#       it under the terms of the GNU Lesser General Public License as
#       published by the Free Software Foundation; either version 3 of the
#       License, or (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU Lesser General Public License for more details.
#
#       You should have received a copy of the GNU Lesser General Public
#       License along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.
#
# Edits have been made to it to fit Wrye Bash's code style and to port it to
# 64bit/python3.
# BEGIN TASKDIALOG PART =======================================================
_BUTTONID_OFFSET                 = 1000

#---Internal Flags. Leave these alone unless you know what you're doing---#
_ENABLE_HYPERLINKS               = 0x0001
_USE_HICON_MAIN                  = 0x0002
_USE_HICON_FOOTER                = 0x0004
_ALLOW_DIALOG_CANCELLATION       = 0x0008
_USE_COMMAND_LINKS               = 0x0010
_USE_COMMAND_LINKS_NO_ICON       = 0x0020
_EXPAND_FOOTER_AREA              = 0x0040
_EXPANDED_BY_DEFAULT             = 0x0080
_VERIFICATION_FLAG_CHECKED       = 0x0100
_SHOW_PROGRESS_BAR               = 0x0200
_SHOW_MARQUEE_PROGRESS_BAR       = 0x0400
_CALLBACK_TIMER                  = 0x0800
_POSITION_RELATIVE_TO_WINDOW     = 0x1000
_RTL_LAYOUT                      = 0x2000
_NO_DEFAULT_RADIO_BUTTON         = 0x4000
_CAN_BE_MINIMIZED                = 0x8000

#-------------Events---------------#
_CREATED                         = 0
_NAVIGATED                       = 1
_BUTTON_CLICKED                  = 2
_HYPERLINK_CLICKED               = 3
_TIMER                           = 4
_DESTROYED                       = 5
_RADIO_BUTTON_CLICKED            = 6
_DIALOG_CONSTRUCTED              = 7
_VERIFICATION_CLICKED            = 8
_HELP                            = 9
_EXPANDER_BUTTON_CLICKED         = 10

#-------Callback Type--------#
_PFTASKDIALOGCALLBACK = WINFUNCTYPE(c_void_p, c_void_p, c_uint, c_uint, c_long,
                                    c_long)

#-------Win32 Stucts/Unions--------#
# Callers do not have to worry about using these.
class _TASKDIALOG_BUTTON(Structure):
    _pack_ = 1
    _fields_ = [(u'nButtonID', c_int),
                (u'pszButtonText', c_wchar_p)]

class _FOOTERICON(Union):
    _pack_ = 1
    _fields_ = [(u'hFooterIcon', c_void_p),
                (u'pszFooterIcon', c_ushort)]

class _MAINICON(Union):
    _pack_ = 1
    _fields_ = [(u'hMainIcon', c_void_p),
                (u'pszMainIcon', c_ushort)]

class _TASKDIALOGCONFIG(Structure):
    _pack_ = 1
    _fields_ = [(u'cbSize', c_uint),
                (u'hwndParent', c_void_p),
                (u'hInstance', c_void_p),
                (u'dwFlags', c_uint),
                (u'dwCommonButtons', c_uint),
                (u'pszWindowTitle', c_wchar_p),
                (u'uMainIcon', _MAINICON),
                (u'pszMainInstruction', c_wchar_p),
                (u'pszContent', c_wchar_p),
                (u'cButtons', c_uint),
                (u'pButtons', POINTER(_TASKDIALOG_BUTTON)),
                (u'nDefaultButton', c_int),
                (u'cRadioButtons', c_uint),
                (u'pRadioButtons', POINTER(_TASKDIALOG_BUTTON)),
                (u'nDefaultRadioButton', c_int),
                (u'pszVerificationText', c_wchar_p),
                (u'pszExpandedInformation', c_wchar_p),
                (u'pszExpandedControlText', c_wchar_p),
                (u'pszCollapsedControlText', c_wchar_p),
                (u'uFooterIcon', _FOOTERICON),
                (u'pszFooter', c_wchar_p),
                (u'pfCallback', _PFTASKDIALOGCALLBACK),
                (u'lpCallbackData', c_longlong),
                (u'cxWidth', c_uint)]

    _anonymous_ = (u'uMainIcon', u'uFooterIcon',)

#--Stock ICON IDs
_SIID_DOCNOASSOC         = 0
_SIID_DOCASSOC           = 1
_SIID_APPLICATION        = 2
_SIID_FOLDER             = 3
_SIID_FOLDEROPEN         = 4
_SIID_DRIVE525           = 5
_SIID_DRIVE35            = 6
_SIID_DRIVEREMOVE        = 7
_SIID_DRIVEFIXED         = 8
_SIID_DRIVENET           = 9
_SIID_DRIVENETDISABLED   = 10
_SIID_DRIVECD            = 11
_SIID_DRIVERAM           = 12
_SIID_WORLD              = 13
_SIID_SERVER             = 15
_SIID_PRINTER            = 16
_SIID_MYNETWORK          = 17
_SIID_FIND               = 22
_SIID_HELP               = 23
_SIID_SHARE              = 28
_SIID_LINK               = 29
_SIID_SLOWFILE           = 30
_SIID_RECYCLER           = 31
_SIID_RECYCLERFULL       = 32
_SIID_MEDIACDAUDIO       = 40
_SIID_LOCK               = 47
_SIID_AUTOLIST           = 49
_SIID_PRINTERNET         = 50
_SIID_SERVERSHARE        = 51
_SIID_PRINTERFAX         = 52
_SIID_PRINTERFAXNET      = 53
_SIID_PRINTERFILE        = 54
_SIID_STACK              = 55
_SIID_MEDIASVCD          = 56
_SIID_STUFFEDFOLDER      = 57
_SIID_DRIVEUNKNOWN       = 58
_SIID_DRIVEDVD           = 59
_SIID_MEDIADVD           = 60
_SIID_MEDIADVDRAM        = 61
_SIID_MEDIADVDRW         = 62
_SIID_MEDIADVDR          = 63
_SIID_MEDIADVDROM        = 64
_SIID_MEDIACDAUDIOPLUS   = 65
_SIID_MEDIACDRW          = 66
_SIID_MEDIACDR           = 67
_SIID_MEDIACDBURN        = 68
_SIID_MEDIABLANKCD       = 69
_SIID_MEDIACDROM         = 70
_SIID_AUDIOFILES         = 71
_SIID_IMAGEFILES         = 72
_SIID_VIDEOFILES         = 73
_SIID_MIXEDFILES         = 74
_SIID_FOLDERBACK         = 75
_SIID_FOLDERFRONT        = 76
_SIID_SHIELD             = 77
_SIID_WARNING            = 78
_SIID_INFO               = 79
_SIID_ERROR              = 80
_SIID_KEY                = 81
_SIID_SOFTWARE           = 82
_SIID_RENAME             = 83
_SIID_DELETE             = 84
_SIID_MEDIAAUDIODVD      = 85
_SIID_MEDIAMOVIEDVD      = 86
_SIID_MEDIAENHANCEDCD    = 87
_SIID_MEDIAENHANCEDDVD   = 88
_SIID_MEDIAHDDVD         = 89
_SIID_MEDIABLURAY        = 90
_SIID_MEDIAVCD           = 91
_SIID_MEDIADVDPLUSR      = 92
_SIID_MEDIADVDPLUSRW     = 93
_SIID_DESKTOPPC          = 94
_SIID_MOBILEPC           = 95
_SIID_USERS              = 96
_SIID_MEDIASMARTMEDIA    = 97
_SIID_MEDIACOMPACTFLASH  = 98
_SIID_DEVICECELLPHONE    = 99
_SIID_DEVICECAMERA       = 100
_SIID_DEVICEVIDEOCAMERA  = 101
_SIID_DEVICEAUDIOPLAYER  = 102
_SIID_NETWORKCONNECT     = 103
_SIID_INTERNET           = 104
_SIID_ZIPFILE            = 105
_SIID_SETTINGS           = 106
_SIID_DRIVEHDDVD         = 132
_SIID_DRIVEBD            = 133
_SIID_MEDIAHDDVDROM      = 134
_SIID_MEDIAHDDVDR        = 135
_SIID_MEDIAHDDVDRAM      = 136
_SIID_MEDIABDROM         = 137
_SIID_MEDIABDR           = 138
_SIID_MEDIABDRE          = 139
_SIID_CLUSTEREDDRIVE     = 140
_SIID_MAX_ICONS          = 175

#--SHGetIconInfo flags
_SHGSI_ICONLOCATION  = 0x00000000 # you always get icon location
_SHGSI_ICON          = 0x00000100 # get handle to the icon
_SHGSI_LARGEICON     = 0x00000000 # get large icon
_SHGSI_SMALLICON     = 0x00000001 # get small icon
_SHGSI_SHELLICONSIZE = 0x00000004 # get shell icon size
_SHGSI_SYSICONINDEX  = 0x00004000 # get system icon index
_SHGSI_LINKOVERLAY   = 0x00008000 # get icon with a link overlay on it
_SHGSI_SELECTED      = 0x00010000 # get icon in selected state

class _SHSTOCKICONINFO(Structure):
    _pack_ = 1
    _fields_ = [(u'cbSize', c_ulong),
                (u'hIcon', c_void_p),
                (u'iSysImageIndex', c_int),
                (u'iIcon', c_int),
                (u'szPath', c_wchar*MAX_PATH)]

#------------------------------------------------------------------------------

#------Message codes------#
_SETISMARQUEE = 1127
_SETPBARRANGE = 1129
_SETPBARPOS = 1130
_SETMARQUEE = 1131
_SETELEMENT = 1132
_SETSHIELD = 1139
_UPDATEICON = 1140

_CONTENT = 0
_EX_INFO = 1
_FOOTER = 2
_HEADING = 3
# END TASKDIALOG PART =========================================================

# API - Functions =============================================================
def get_registry_path(subkey, entry, test_path_callback):
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
            if not test_path_callback(installPath): continue
            return installPath
    return None

def get_registry_game_paths(submod):
    """Check registry-supplied game paths for the game detection file(s)."""
    reg_keys = submod.regInstallKeys
    if not reg_keys:
        return [] # Game is not detectable via registry
    subkey, entry = reg_keys
    reg_path = get_registry_path(subkey, entry, submod.test_game_path)
    return [] if not reg_path else [reg_path]

def get_win_store_game_info(submod):
    """Get all information about a Windows Store application."""
    publisher_name = submod.Ws.publisher_name
    publisher_id = submod.Ws.publisher_id
    app_name = submod.Ws.win_store_name
    return _win_store_finder.get_app_info(
        app_name, publisher_name, publisher_id)

def get_personal_path():
    return (GPath(_get_known_path(_FOLDERID.Documents)),
            _(u'Folder path retrieved via SHGetKnownFolderPath'))

def get_local_app_data_path():
    return (GPath(_get_known_path(_FOLDERID.LocalAppData)),
            _(u'Folder path retrieved via SHGetKnownFolderPath'))

def init_app_links(apps_dir, badIcons, iconList):
    init_params = []
    for path, (target, icon, shortcut_descr) in _get_app_links(
            apps_dir).items():
        # msi shortcuts: dc0c8de
        if target.lower().find(r'installer\{') != -1:
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
                        icon, idex = os.path.expandvars(
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

def get_file_version(filename):
    """
    Return the version of a dll/exe, using the native win32 functions
    if available and otherwise a pure python implementation that works
    on Linux.

    :param filename: The file from which the version should be read.
    :return A 4-int tuple, for example (1, 9, 32, 0).
    """
    # If it's a symbolic link (i.e. a user-added app), resolve it first
    if filename.endswith(u'.lnk'):
        sh = win32client.Dispatch(u'WScript.Shell')
        shortcut = sh.CreateShortCut(filename)
        filename = shortcut.TargetPath
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

def testUAC(gameDataPath):
    deprint(u'Testing if game folder is UAC-protected')
    tmpDir = Path.tempDir()
    tempFile = tmpDir.join(u'_tempfile.tmp')
    dest = gameDataPath.join(u'_tempfile.tmp')
    with tempFile.open(u'wb'): pass # create the file
    from . import shellMove, shellDeletePass ##: ugh
    try: # to move it into the Data directory
        shellMove(tempFile, dest, silent=True)
    except AccessDeniedError:
        global _isUAC
        _isUAC = True
    finally:
        shellDeletePass(tmpDir)
        shellDeletePass(dest)

def setUAC(handle, uac=True):
    """Calls the Windows API to set a button as UAC"""
    if _isUAC and win32gui:
        win32gui.SendMessage(handle, 0x0000160C, None, uac)

@functools.lru_cache(maxsize=None) ##: cached in py 3.9
def getJava():
    """Locate javaw.exe to launch jars from Bash."""
    try:
        java_home = GPath(os.environ[u'JAVA_HOME'])
        java_bin_path = java_home.join(u'bin', u'javaw.exe')
        if java_bin_path.isfile(): return java_bin_path
    except KeyError: # no JAVA_HOME
        pass
    sys_root = GPath(os.environ[u'SYSTEMROOT'])
    # Default location: Windows\System32\javaw.exe
    java_bin_path = sys_root.join(u'system32', u'javaw.exe')
    if not java_bin_path.isfile():
        # 1st possibility:
        #  - Bash is running as 32-bit
        #  - The only Java installed is 64-bit
        # Because Bash is 32-bit, Windows\System32 redirects to
        # Windows\SysWOW64.  So look in the ACTUAL System32 folder
        # by using Windows\SysNative
        java_bin_path = sys_root.join(u'sysnative', u'javaw.exe')
    if not java_bin_path.isfile():
        # 2nd possibility
        #  - Bash is running as 64-bit
        #  - The only Java installed is 32-bit
        # So javaw.exe would actually be in Windows\SysWOW64
        java_bin_path = sys_root.join(u'syswow64', u'javaw.exe')
    return java_bin_path

def is_uac():
    """Returns True if the game is under UAC protection."""
    return _isUAC

def fixup_taskbar_icon():
    """On Windows 7+, if taskbar settings for taskbar buttons is set to 'Always
    combine, hide labels', then the taskbar icon will be grouped as a
    python.exe/pythonw.exe instance and will use that icon. We can tell Windows
    to not consider ourselves part of that group, and so use our own icon. See:
    https://stackoverflow.com/questions/1551605/how-to-set-applications-taskbar-icon-in-windows-7/1552105#1552105

    Note: this should be called before showing any top level windows."""
    appid = u'Wrye Bash'
    try:
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)
    except AttributeError:
        pass # On a pre-Win7

def mark_high_dpi_aware():
    """Marks the current process as High DPI-aware."""
    try:
        windll.shcore.SetProcessDpiAwareness(True)
    except (AttributeError, WindowsError):
        pass  # We are on an unsupported Windows version

def python_tools_dir():
    """Returns the absolute path to the Tools directory of the currently used
    Python installation."""
    return os.path.join(real_sys_prefix(), u'Tools') # easy on Windows

def convert_separators(p):
    """Converts other OS's path separators to separators for this OS."""
    return p.replace(u'/', u'\\')

# API - Classes ===============================================================
# The same note about the taskdialog license from above applies to the section
# below.
#
# BEGIN TASKDIALOG PART =======================================================
class TaskDialog(object):
    """Wrapper class for the Win32 task dialog."""

    stock_icons = {u'warning': 65535, u'error': 65534, u'information': 65533,
                   u'shield': 65532}
    stock_buttons = {u'ok': 0x01,  #1
                     u'yes': 0x02,  #2
                     u'no': 0x04,  #4
                     u'cancel': 0x08,  #8
                     u'retry': 0x10,  #16
                     u'close': 0x20}  #32
    stock_button_ids = {u'ok': 1, u'cancel': 2, u'retry': 4, u'yes': 6,
                        u'no': 7, u'close': 8}

    def __init__(self, title, heading, content, buttons=(), main_icon=None,
                 parenthwnd=None, footer=None):
        """Initialize the dialog."""
        self.__events = {_CREATED:[],
                         _NAVIGATED:[],
                         _BUTTON_CLICKED:[],
                         _HYPERLINK_CLICKED:[],
                         _TIMER:[],
                         _DESTROYED:[],
                         _RADIO_BUTTON_CLICKED:[],
                         _DIALOG_CONSTRUCTED:[],
                         _VERIFICATION_CLICKED:[],
                         _HELP:[],
                         _EXPANDER_BUTTON_CLICKED:[]}
        self.__stockb_indices = []
        self.__shield_buttons = []
        self.__handle = None
        # properties
        self._title = title
        self._heading = heading
        self._content = content
        self._footer = footer
        # main icon
        self._main_is_stock = main_icon in self.stock_icons
        self._main_icon = self.stock_icons[
            main_icon] if self._main_is_stock else main_icon
        # buttons
        buttons = list(buttons)
        self.set_buttons(buttons)
        # parent handle
        self._parent = parenthwnd

    def close(self):
        """Close the task dialog."""
        windll.user32.SendMessageW(self.__handle, 0x0010, 0, 0)

    def bind(self, task_dialog_event, func):
        """Bind a function to one of the task dialog events."""
        if task_dialog_event not in self.__events:
            raise Exception(u'The control does not support the event.')
        self.__events[task_dialog_event].append(func)
        return self

    @property
    def heading(self): return self._heading
    @heading.setter
    def heading(self, heading):
        """Set the heading / main instruction of the dialog."""
        self._heading = heading
        if self.__handle is not None:
            self.__update_element_text(_HEADING, heading)

    @property
    def content(self): return self._content
    @content.setter
    def content(self, content):
        """Set the text content or message that the dialog conveys."""
        self._content = content
        if self.__handle is not None:
            self.__update_element_text(_CONTENT, content)

    @property
    def footer(self): return self._footer
    @footer.setter
    def footer(self, footer):
        """Set the footer text of the dialog."""
        self._footer = footer
        if self.__handle is not None:
            self.__update_element_text(_FOOTER, footer)

    def set_buttons(self, buttons, convert_stock_buttons=True):
        """

           Set the buttons on the dialog using the list of strings in *buttons*
           where each string is the label for a new button.

           See the official documentation.

        """
        self._buttons = buttons
        self._conv_stock = convert_stock_buttons
        return self

    def set_radio_buttons(self, buttons, default=0):
        """

           Add radio buttons to the dialog using the list of strings in
           *buttons*.

        """
        self._radio_buttons = buttons
        self._default_radio = default
        return self

    def set_footer_icon(self, icon):
        """Set the icon that appears in the footer of the dialog."""
        self._footer_is_stock = icon in self.stock_icons
        self._footer_icon = self.stock_icons[
            icon] if self._footer_is_stock else icon
        return self

    def set_expander(self, expander_data, expanded=False, at_footer=False):
        """Set up a collapsible control that can reveal further information
        about the task that the dialog performs."""
        if len(expander_data) != 3: return self
        self._expander_data = expander_data
        self._expander_expanded = expanded
        self._expands_at_footer = at_footer
        return self

    def set_rangeless_progress_bar(self, ticks=50):
        """Set the progress bar on the task dialog as a marquee progress
        bar."""
        self._marquee_progress_bar = True
        self._marquee_speed = ticks
        return self

    def set_progress_bar(self, callback, low=0, high=100, pos=0):
        """Set the progress bar on the task dialog as a marquee progress
        bar."""
        _range = (high << 16) | low
        self._progress_bar = {u'func':callback, u'range': _range, u'pos':pos}
        return self

    def set_check_box(self, cbox_label, checked=False):
        """Set up a verification check box that appears on the task dialog."""
        self._cbox_label = cbox_label
        self._cbox_checked = checked
        return self

    def set_width(self, width):
        """Set the width, in pixels, of the taskdialog."""
        self._width = width
        return self

    def show(self, command_links=False, centered=True, can_cancel=False,
             can_minimize=False, hyperlinks=True, additional_flags=0):
        """Build and display the dialog box."""
        conf = self.__configure(command_links, centered, can_cancel,
                                can_minimize, hyperlinks, additional_flags)
        button = c_int()
        radio = c_int()
        checkbox = c_int()
        _indirect(byref(conf), byref(button), byref(radio), byref(checkbox))
        if button.value >= _BUTTONID_OFFSET:
            button = self.__custom_buttons[button.value - _BUTTONID_OFFSET][0]
        else:
            for stock_btn, stock_val in self.stock_button_ids.items():
                if stock_val == button.value:
                    button = stock_btn
                    break
            else:
                button = 0
        if getattr(self, u'_radio_buttons', False):
            radio = self._radio_buttons[radio.value]
        else:
            radio = radio.value
        checkbox = not (checkbox.value == 0)
        return button, radio, checkbox

    ###############################
    # Windows windll.user32 calls #
    ###############################
    def __configure(self, c_links, centered, close, minimize, h_links,
                    additional_flags):
        conf = _TASKDIALOGCONFIG()

        if c_links and getattr(self, u'_buttons', []):
            additional_flags |= _USE_COMMAND_LINKS
        if centered:
            additional_flags |= _POSITION_RELATIVE_TO_WINDOW
        if close:
            additional_flags |= _ALLOW_DIALOG_CANCELLATION
        if minimize:
            additional_flags |= _CAN_BE_MINIMIZED
        if h_links:
            additional_flags |= _ENABLE_HYPERLINKS

        conf.cbSize = sizeof(_TASKDIALOGCONFIG)
        conf.hwndParent = self._parent
        conf.pszWindowTitle = self._title
        conf.pszMainInstruction = self._heading
        conf.pszContent = self._content

        # FIXME(ut): unpythonic, as the builder pattern above
        attributes = dir(self)

        if u'_width' in attributes:
            conf.cxWidth = self._width

        if self._footer:
            conf.pszFooter = self._footer
        if u'_footer_icon' in attributes:
            if self._footer_is_stock:
                conf.uFooterIcon.pszFooterIcon = self._footer_icon
            else:
                conf.uFooterIcon.hFooterIcon = self._footer_icon
                additional_flags |= _USE_HICON_FOOTER
        if self._main_icon is not None:
            if self._main_is_stock:
                conf.uMainIcon.pszMainIcon = self._main_icon
            else:
                conf.uMainIcon.hMainIcon = self._main_icon
                additional_flags |= _USE_HICON_MAIN

        if u'_buttons' in attributes:
            custom_buttons = []
            # Enumerate through button list
            for i, button in enumerate(self._buttons):
                text, elevated, default = self.__parse_button(button)
                if text.lower() in self.stock_buttons and self._conv_stock:
                    # This is a stock button.
                    conf.dwCommonButtons = (conf.dwCommonButtons
                                            |self.stock_buttons[text.lower()])

                    bID = self.stock_button_ids[text.lower()]
                    if elevated:
                        self.__shield_buttons.append(bID)
                    if default:
                        conf.nDefaultButton = bID
                else:
                    custom_buttons.append((text, default, elevated))

            conf.cButtons = len(custom_buttons)
            array_type = ARRAY(_TASKDIALOG_BUTTON, conf.cButtons)
            c_array = array_type()
            for i, tup in enumerate(custom_buttons):
                c_array[i] = _TASKDIALOG_BUTTON(i + _BUTTONID_OFFSET, tup[0])
                if tup[1]:
                    conf.nDefaultButton = i + _BUTTONID_OFFSET
                if tup[2]:
                    self.__shield_buttons.append(i + _BUTTONID_OFFSET)
            conf.pButtons = c_array
            self.__custom_buttons = custom_buttons

        if u'_radio_buttons' in attributes:
            conf.cRadioButtons = len(self._radio_buttons)
            array_type = ARRAY(_TASKDIALOG_BUTTON, conf.cRadioButtons)
            c_array = array_type()
            for i, button in enumerate(self._radio_buttons):
                c_array[i] = _TASKDIALOG_BUTTON(i, button)
            conf.pRadioButtons = c_array

            if self._default_radio is None:
                additional_flags |= _NO_DEFAULT_RADIO_BUTTON
            else:
                conf.nDefaultRadioButton = self._default_radio

        if u'_expander_data' in attributes:
            conf.pszCollapsedControlText = self._expander_data[0]
            conf.pszExpandedControlText = self._expander_data[1]
            conf.pszExpandedInformation = self._expander_data[2]

            if self._expander_expanded:
                additional_flags |= _EXPANDED_BY_DEFAULT
            if self._expands_at_footer:
                additional_flags |= _EXPAND_FOOTER_AREA

        if u'_cbox_label' in attributes:
            conf.pszVerificationText = self._cbox_label
            if self._cbox_checked:
                additional_flags |= _VERIFICATION_FLAG_CHECKED

        if u'_marquee_progress_bar' in attributes:
            additional_flags |= _SHOW_MARQUEE_PROGRESS_BAR
            additional_flags |= _CALLBACK_TIMER

        if u'_progress_bar' in attributes:
            additional_flags |= _SHOW_PROGRESS_BAR
            additional_flags |= _CALLBACK_TIMER

        conf.dwFlags = additional_flags
        conf.pfCallback = _PFTASKDIALOGCALLBACK(self.__callback)
        return conf

    @staticmethod
    def __parse_button(text):
        elevation = False
        default = False
        if text.startswith(u'+') and len(text) > 1:
            text = text[1:]
            elevation = True
        elif text.startswith(r'\+'):
            text = text[1:]
        if text.startswith(u'+\\') and text.isupper():
            text = text[0] + text[2:]
        elif text.startswith(u'\\') and text.isupper():
            text = text[1:]
        elif text.isupper():
            default = True
            splits = text.partition(u'&')
            if splits[0] == u'':
                text = splits[1] + splits[2].capitalize()
            else:
                text = splits[0].capitalize() + splits[1] + splits[2]
        return text, elevation, default

    def __callback(self, handle, notification, wparam, lparam, refdata):
        args = [self]
        if notification == _CREATED:
            self.__handle = handle
            for bID in self.__shield_buttons:
                windll.user32.SendMessageW(self.__handle, _SETSHIELD, bID, 1)
            if getattr(self, u'_marquee_progress_bar', False):
                self.__set_marquee_speed()
        elif notification == _BUTTON_CLICKED:
            if wparam >= _BUTTONID_OFFSET:
                button = self.__custom_buttons[wparam - _BUTTONID_OFFSET][0]
                args.append(button)
            else:
                for stock_btn, stock_val in self.stock_button_ids.items():
                    if stock_val == wparam:
                        button = stock_btn
                        break
                else:
                    button = 0
                args.append(button)
        elif notification == _HYPERLINK_CLICKED:
            args.append(wstring_at(lparam))
        elif notification == _RADIO_BUTTON_CLICKED:
            if getattr(self, u'_radio_buttons', False):
                radio = self._radio_buttons[wparam]
            else:
                radio = wparam
            args.append(radio)
        elif notification == _VERIFICATION_CLICKED:
            args.append(wparam)
        elif notification == _EXPANDER_BUTTON_CLICKED:
            if wparam == 0:
                collapsed = True
            else:
                collapsed = False
            args.append(collapsed)
        elif notification == _DESTROYED:
            self.__handle = None
        elif notification == _TIMER:
            args.append(wparam)
            if getattr(self, u'_progress_bar', False):
                callback = self._progress_bar[u'func']
                new_pos = callback(self)
                self._progress_bar[u'pos'] = new_pos
                self.__update_progress_bar()
        for func in self.__events[notification]:
            func(*args)

    def __set_marquee_speed(self):
        windll.user32.SendMessageW(self.__handle, _SETMARQUEE,
                                   1, self._marquee_speed)

    def __update_element_text(self, element, text):
        if self.__handle is None:
            raise Exception(u'Dialog is not yet created, or has been '
                            u'destroyed.')
        windll.user32.SendMessageW(self.__handle, _SETELEMENT, element, text)

    def __update_progress_bar(self):
        windll.user32.SendMessageW(self.__handle, _SETPBARRANGE, 0,
                                   self._progress_bar[u'range'])
        windll.user32.SendMessageW(self.__handle, _SETPBARPOS,
                                   self._progress_bar[u'pos'], 0)
# END TASKDIALOG PART =========================================================
