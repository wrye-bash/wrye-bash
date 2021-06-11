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
"""Encapsulates Linux-specific classes and methods."""

import os
import subprocess
import sys
import functools

from .common import WinAppInfo
from ..bolt import deprint, GPath, structs_cache, Path, dict_sort
from ..exception import EnvError

# API - Constants =============================================================
try:
    MAX_PATH = int(subprocess.check_output([u'getconf', u'PATH_MAX', u'/']))
except (ValueError, subprocess.CalledProcessError, OSError):
    deprint(u'calling getconf failed - error:', traceback=True)
    MAX_PATH = 4096

FO_MOVE = 1
FO_COPY = 2
FO_DELETE = 3
FO_RENAME = 4
FOF_NOCONFIRMMKDIR = 512

# TaskDialog is Windows-specific, so stub all this out (and raise if TaskDialog
# is used, see below)
TASK_DIALOG_AVAILABLE = False

BTN_OK = BTN_CANCEL = BTN_YES = BTN_NO = None
GOOD_EXITS = (BTN_OK, BTN_YES)

# Internals ===================================================================
def _getShellPath(folderKey): ##: mkdirs
    home = os.path.expanduser(u'~')
    return GPath({u'Personal': home,
                  u'Local AppData': home + u'/.local/share'}[folderKey])

def _get_error_info():
    return '\n'.join(f'  {k}: {v}' for k, v in dict_sort(os.environ))

# API - Functions =============================================================
##: Several of these should probably raise instead
def get_registry_path(_subkey, _entry, _test_path_callback):
    return None # no registry on Linux

def get_registry_game_paths(_submod):
    return [] # no registry on Linux

def get_win_store_game_info(_submod):
    return WinAppInfo() # no Windows Store on Linux

def get_personal_path():
    return _getShellPath(u'Personal'), _get_error_info()

def get_local_app_data_path():
    return _getShellPath(u'Local AppData'), _get_error_info()

def init_app_links(_apps_dir, _badIcons, _iconList):
    ##: Rework launchers so that they can work for Linux too
    # The 'shortcuts' concept is hard for users to grasp anyways (remember how
    # many people have trouble setting up a shortcut for QACing using xEdit!),
    # so a better design would be e.g. using our settings dialog to add new
    # launchers, similar to how MO2 does it
    return []

def testUAC(_gameDataPath):
    pass # Noop on Linux

def setUAC(_handle, _uac=True):
    pass # Noop on Linux

def is_uac():
    return False # Not a thing on Linux

@functools.lru_cache(maxsize=None) ##: cached in py 3.9
def getJava():
    try:
        java_home = GPath(os.environ[u'JAVA_HOME'])
        java_bin_path = java_home.join(u'bin', u'java')
        if java_bin_path.isfile(): return java_bin_path
    except KeyError: # no JAVA_HOME
        pass
    try:
        java_bin_path = subprocess.check_output(
            u'command -v java', shell=True,
            encoding=Path.sys_fs_enc).rstrip(u'\n')
    except subprocess.CalledProcessError:
        # Fall back to the likely correct path on most distros - but probably
        # Java is missing entirely if command can't find it
        java_bin_path = u'/usr/bin/java'
    return GPath(java_bin_path)

# TODO(inf) This method needs support for string fields and product versions
def get_file_version(filename):
    """A python replacement for win32api.GetFileVersionInfo that can be used
    on systems where win32api isn't available."""
    _WORD, _DWORD = u'<H', u'<I'
    def _read(target_fmt, file_obj, offset=0, count=1, absolute=False):
        """Read one or more chunks from the file, either a word or dword."""
        target_struct = structs_cache[target_fmt]
        file_obj.seek(offset, not absolute)
        result = [target_struct.unpack(file_obj.read(target_struct.size))[0]
                  for _x in range(count)] ##: array.fromfile(f, n)
        return result[0] if count == 1 else result
    def _find_version(file_obj, pos, offset):
        """Look through the RT_VERSION and return VS_VERSION_INFO."""
        def _pad(num):
            return num if num % 4 == 0 else num + 4 - (num % 4)
        file_obj.seek(pos + offset)
        len_, val_len, type_ = _read(_WORD, file_obj, count=3)
        info = u''
        for i in range(200):
            info += chr(_read(_WORD, file_obj))
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
        for section_num in range(section_count):
            section_pos = section_table_pos + 40 * section_num
            f.seek(section_pos)
            if f.read(8).rstrip(b'\x00') != b'.rsrc':  # section name_
                continue
            section_va = _read(_DWORD, f, offset=4)
            raw_data_pos = _read(_DWORD, f, offset=4)
            section_resources_pos = raw_data_pos + resources_va - section_va
            num_named, num_id = _read(_WORD, f, count=2, absolute=True,
                                      offset=section_resources_pos + 12)
            for resource_num in range(num_named + num_id):
                resource_pos = section_resources_pos + 16 + 8 * resource_num
                name_ = _read(_DWORD, f, offset=resource_pos, absolute=True)
                if name_ != 16: continue # RT_VERSION
                for i in range(3):
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

def fixup_taskbar_icon():
    pass ##: Probably not needed on Linux, only a Win7+ issue.

def mark_high_dpi_aware():
    pass ##: Equivalent on Linux? Not needed?

def python_tools_dir():
    # This is much more complicated on Linux than on Windows, since sys.prefix
    # only points to /usr here, so is useless
    for path_entry in sys.path:
        tools_path = os.path.join(path_entry, u'Tools')
        # Actually check for the files we really want
        try_paths = [os.path.join(tools_path, u'i18n', x)
                     for x in (u'msgfmt.py', u'pygettext.py')]
        if all(os.path.isfile(p) for p in try_paths):
            return tools_path
    # Fall back on /usr/lib/python*.* - this should never happen
    deprint(u'Failed to find Python Tools dir on sys.path')
    return u'/usr/lib/python%d.%d' % (sys.version_info.major,
                                      sys.version_info.minor)

def convert_separators(p):
    return p.replace(u'\\', u'/')

# API - Classes ===============================================================
class TaskDialog(object):
    def __init__(self, _title, _heading, _content, _buttons=(),
                 _main_icon=None, _parenthwnd=None, _footer=None):
        raise EnvError(u'TaskDialog')

# Linux is still mostly broken, so raise on import
raise ImportError(u'Wrye Bash only partially supports Linux at the moment. If '
                  u"you know what you're doing, edit linux.py to remove this "
                  u'raise statement.')
