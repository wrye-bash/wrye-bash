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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2014 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Thin python wrapper around libloadorder.

To use outside of Bash replace the Bash imports below with:

class Path: pass
class BoltError(Exception): pass
def GPath(x): return u'' if x is None else unicode(x, 'utf8')
def deprint(x, traceback=False):
    import tarceback
    traceback.print_exc()
"""

from ctypes import *
import os
import sys
from bolt import Path, GPath, BoltError, deprint

liblo = None
version = None

# Version of libloadorder this Python script is written for.
PythonLibloVersion = (7,5)

DebugLevel = 0
# DebugLevel
#  Set this for more or less feedback
#  0 - (default) no additional feedback
#  1 - print information about all return codes found

class LibloVersionError(Exception):
    """Exception thrown if the libloadorder loaded is not
       compatible with liblo.py"""
    pass

def Init(path):
    """Called automatically by importing liblo.  Can also be called manually
       by the user to reload libloadorder, pointing to a different path to the dll.
   """

    # If path is a directory, auto choose DLL based on platform
    if os.path.isdir(path):
        #if '64bit' in platform.architecture():
        #    path = os.path.join(path,u'libloadorder64.dll')
        #else:
            path = os.path.join(path,u'loadorder32.dll')

    global liblo
    # First unload any libloadorder dll previously loaded
    del liblo
    liblo = None

    if not os.path.exists(path):
        return None, None

    try:
        # CDLL doesn't play with unicode path strings nicely on windows :(
        # Use this workaround
        handle = None
        if isinstance(path,unicode) and os.name in ('nt','ce'):
            LoadLibrary = windll.kernel32.LoadLibraryW
            handle = LoadLibrary(path)
        liblo = CDLL(path,handle=handle)
    except Exception as e:
        liblo = None
        raise

    # Some types
    lo_game_handle = c_void_p
    lo_game_handle_p = POINTER(lo_game_handle)
    c_uint_p = POINTER(c_uint)
    c_bool_p = POINTER(c_bool)
    c_char_p_p = POINTER(c_char_p)
    c_char_p_p_p = POINTER(c_char_p_p)
    c_size_t_p = POINTER(c_size_t)

    # helpers
    def _uint(name): return c_uint.in_dll(liblo, name).value

    def list_of_strings(strings):
        lst = (c_char_p * len(strings))()
        lst = cast(lst,c_char_p_p)
        for i,string in enumerate(strings):
            lst[i] = cast(create_string_buffer(string),c_char_p)
        return lst

    # utility unicode functions
    def _enc(x): return (x.encode('utf8') if isinstance(x,unicode)
                         else x.s.encode('utf8') if isinstance(x,Path)
                         else x)

    # =========================================================================
    # API Functions - Version
    # =========================================================================
    ## bool lo_is_compatible(const unsigned int versionMajor, const unsigned int versionMinor, const unsigned int versionPatch)
    _Clo_is_compatible = liblo.lo_is_compatible
    _Clo_is_compatible.restype = c_bool
    _Clo_is_compatible.argtypes = [c_uint, c_uint, c_uint]
    def IsCompatibleVersion(majorVersion, minorVersion, patchVersion=0):
        return _Clo_is_compatible(majorVersion,minorVersion,patchVersion)
    if not IsCompatibleVersion(*PythonLibloVersion):
        verMajor = c_uint(0)
        verMinor = c_uint(0)
        verPatch = c_uint(0)
        try:
            liblo.lo_get_version(byref(verMajor), byref(verMinor), byref(verPatch))
        except:
            raise LibloVersionError('liblo.py is not compatible with the specified libloadorder DLL (%i.%i.%i).' % verMajor % verMinor % verPatch)

    # =========================================================================
    # API Constants - Games
    # =========================================================================
    LIBLO_GAME_TES4 = _uint('LIBLO_GAME_TES4')
    LIBLO_GAME_TES5 = _uint('LIBLO_GAME_TES5')
    LIBLO_GAME_FO3 = _uint('LIBLO_GAME_FO3')
    LIBLO_GAME_FNV = _uint('LIBLO_GAME_FNV')
    games = {
        'Oblivion':LIBLO_GAME_TES4,
        LIBLO_GAME_TES4:LIBLO_GAME_TES4,
        'Skyrim':LIBLO_GAME_TES5,
        LIBLO_GAME_TES5:LIBLO_GAME_TES5,
        'Fallout3':LIBLO_GAME_FO3,
        LIBLO_GAME_FO3:LIBLO_GAME_FO3,
        'FalloutNV':LIBLO_GAME_FNV,
        LIBLO_GAME_FNV:LIBLO_GAME_FNV,
        }

    # =========================================================================
    # API Constants - Load Order Method
    # =========================================================================
    LIBLO_METHOD_TIMESTAMP = _uint('LIBLO_METHOD_TIMESTAMP')
    LIBLO_METHOD_TEXTFILE = _uint('LIBLO_METHOD_TEXTFILE')

    # =========================================================================
    # API Constants - Return codes
    # =========================================================================
    LIBLO_OK = _uint('LIBLO_OK')
    LIBLO_WARN_BAD_FILENAME = _uint('LIBLO_WARN_BAD_FILENAME')
    LIBLO_ERROR_FILE_READ_FAIL = _uint('LIBLO_ERROR_FILE_READ_FAIL')
    LIBLO_ERROR_FILE_WRITE_FAIL = _uint('LIBLO_ERROR_FILE_WRITE_FAIL')
    LIBLO_ERROR_FILE_RENAME_FAIL = _uint('LIBLO_ERROR_FILE_RENAME_FAIL')
    LIBLO_ERROR_FILE_PARSE_FAIL = _uint('LIBLO_ERROR_FILE_PARSE_FAIL')
    LIBLO_ERROR_FILE_NOT_UTF8 = _uint('LIBLO_ERROR_FILE_NOT_UTF8')
    LIBLO_ERROR_FILE_NOT_FOUND = _uint('LIBLO_ERROR_FILE_NOT_FOUND')
    LIBLO_ERROR_TIMESTAMP_READ_FAIL = _uint('LIBLO_ERROR_TIMESTAMP_READ_FAIL')
    LIBLO_ERROR_NO_MEM = _uint('LIBLO_ERROR_NO_MEM')
    LIBLO_ERROR_TIMESTAMP_WRITE_FAIL = _uint(
        'LIBLO_ERROR_TIMESTAMP_WRITE_FAIL')
    LIBLO_WARN_LO_MISMATCH = _uint('LIBLO_WARN_LO_MISMATCH')
    LIBLO_WARN_INVALID_LIST = _uint('LIBLO_WARN_INVALID_LIST')
    LIBLO_ERROR_INVALID_ARGS = _uint('LIBLO_ERROR_INVALID_ARGS')
    errors = dict((name, value) for name, value in locals().iteritems() if
                  name.startswith('LIBLO_'))
    LIBLO_RETURN_MAX = _uint('LIBLO_RETURN_MAX')

    # =========================================================================
    # API Functions - Error Handling
    # =========================================================================
    ## uint32_t lo_get_error_message(const char ** const details)
    _Clo_get_error_message = liblo.lo_get_error_message
    _Clo_get_error_message.restype = c_uint
    _Clo_get_error_message.argtypes = [c_char_p_p]
    def GetLastErrorDetails():
        details = c_char_p()
        ret = _Clo_get_error_message(byref(details))
        if ret != LIBLO_OK:
            raise Exception(u'An error occurred while getting the details of a libloadorder error: %i' % ret)
        return unicode(details.value if details.value else 'None', 'utf8')

    class LibloError(Exception):
        def __init__(self,value):
            self.code = value
            for errorName, errorCode in errors.iteritems():
                if errorCode == value:
                    msg = errorName
                    break
            else: msg = 'UNKNOWN(%i)' % value
            msg += ':'
            try:
                msg += GetLastErrorDetails()
            except Exception as e:
                msg += 'GetLastErrorDetails FAILED (%s)' % e
            self.msg = msg
            Exception.__init__(self,msg)

        def __repr__(self): return '<LibloError: %r>' % self.msg
        def __str__(self): return 'LibloError: %s' % self.msg

    def LibloErrorCheck(result):
        if result == LIBLO_OK: return result
        elif DebugLevel > 0:
            print GetLastErrorDetails()
        raise LibloError(result)

    # =========================================================================
    # API Functions - Version
    # =========================================================================
    ## unsigned int lo_get_version(unsigned int * const versionMajor, unsigned int * const versionMinor, unsigned int * const versionPatch)
    _Clo_get_version = liblo.lo_get_version
    _Clo_get_version.restype = LibloErrorCheck
    _Clo_get_version.argtypes = [c_uint_p, c_uint_p, c_uint_p]
    global version
    try:
        verMajor = c_uint()
        verMinor = c_uint()
        verPatch = c_uint()
        _Clo_get_version(byref(verMajor),byref(verMinor),byref(verPatch))
        version = u'%i.%i.%i' % (verMajor.value,verMinor.value,verPatch.value)
    except LibloError as e:
        print u'Error getting libloadorder version:', e
        version = u'Error'

    # =========================================================================
    # API Functions - Lifecycle Management
    # =========================================================================
    ## unsigned int lo_create_handle(lo_game_handle * const gh, const unsigned int gameId, const char * const gamePath);
    _Clo_create_handle = liblo.lo_create_handle
    _Clo_create_handle.restype = LibloErrorCheck
    _Clo_create_handle.argtypes = [lo_game_handle_p, c_uint, c_char_p, c_char_p]
    ## void lo_destroy_handle(lo_game_handle gh);
    _Clo_destroy_handle = liblo.lo_destroy_handle
    _Clo_destroy_handle.restype = None
    _Clo_destroy_handle.argtypes = [lo_game_handle]
    ## unsigned int lo_set_game_master(lo_game_handle gh, const char * const masterFile);
    _Clo_set_game_master = liblo.lo_set_game_master
    _Clo_set_game_master.restype = LibloErrorCheck
    _Clo_set_game_master.argtypes = [lo_game_handle, c_char_p]

    # =========================================================================
    # API Functions - Load Order
    # =========================================================================
    ## unsigned int lo_get_load_order_method(lo_game_handle gh, unsigned int * const method);
    _Clo_get_load_order_method = liblo.lo_get_load_order_method
    _Clo_get_load_order_method.restype = LibloErrorCheck
    _Clo_get_load_order_method.argtypes = [lo_game_handle, c_uint_p]
    ## unsigned int lo_get_load_order(lo_game_handle gh, char *** const plugins, size_t * const numPlugins);
    _Clo_get_load_order = liblo.lo_get_load_order
    _Clo_get_load_order.restype = LibloErrorCheck
    _Clo_get_load_order.argtypes = [lo_game_handle, c_char_p_p_p, c_size_t_p]
    ## unsigned int lo_set_load_order(lo_game_handle gh, char ** const plugins, const size_t numPlugins);
    _Clo_set_load_order = liblo.lo_set_load_order
    _Clo_set_load_order.restype = LibloErrorCheck
    _Clo_set_load_order.argtypes = [lo_game_handle, c_char_p_p, c_size_t]

    # =========================================================================
    # API Functions - Active Plugins
    # =========================================================================
    ## unsigned int lo_get_active_plugins(lo_game_handle gh, char *** const plugins, size_t * const numPlugins);
    _Clo_get_active_plugins = liblo.lo_get_active_plugins
    _Clo_get_active_plugins.restype = LibloErrorCheck
    _Clo_get_active_plugins.argtypes = [lo_game_handle, c_char_p_p_p, c_size_t_p]
    ## unsigned int lo_set_active_plugins(lo_game_handle gh, char ** const plugins, const size_t numPlugins);
    _Clo_set_active_plugins = liblo.lo_set_active_plugins
    _Clo_set_active_plugins.restype = LibloErrorCheck
    _Clo_set_active_plugins.argtypes = [lo_game_handle, c_char_p_p, c_size_t]
    # ## unsigned int lo_set_plugin_active(lo_game_handle gh, const char * const plugin, const bool active);
    # _Clo_set_plugin_active = liblo.lo_set_plugin_active
    # _Clo_set_plugin_active.restype = LibloErrorCheck
    # _Clo_set_plugin_active.argtypes = [lo_game_handle, c_char_p, c_bool]
    # ## unsigned int lo_get_plugin_active(lo_game_handle gh, const char * const plugin, bool * const result);
    # _Clo_get_plugin_active = liblo.lo_get_plugin_active
    # _Clo_get_plugin_active.restype = LibloErrorCheck
    # _Clo_get_plugin_active.argtypes = [lo_game_handle, c_char_p, c_bool_p]

    # =========================================================================
    # API Functions - Misc
    # =========================================================================
    # # unsigned int lo_fix_plugin_lists(lo_game_handle gh);
    # _Clo_fix_plugin_lists = liblo.lo_fix_plugin_lists
    # _Clo_fix_plugin_lists.restype = LibloErrorCheck
    # _Clo_fix_plugin_lists.argtypes = [lo_game_handle]

    # =========================================================================
    # Class Wrapper
    # =========================================================================
    class LibloHandle(object):
        def __init__(self,gamePath,game='Oblivion',userPath=None):
            """ game can be one of the LIBLO_GAME_*** codes, or one of the
                aliases defined above in the 'games' dictionary."""
            if isinstance(game,basestring):
                if game in games:
                    game = games[game]
                else:
                    raise Exception('Game "%s" is not recognized' % game)
            self._DB = lo_game_handle()
            try:
                _Clo_create_handle(byref(self._DB),game,_enc(gamePath),userPath)
            except LibloError as err:
                if (err.code == LIBLO_WARN_LO_MISMATCH
                    or err.code == LIBLO_WARN_INVALID_LIST):
                    # If there is a Mismatch between loadorder.txt and
                    # plugins.txt, or one of them is invalid, finish
                    # initialization and fix the mismatch at a later time
                    pass
                else:
                    raise
            # Get Load Order Method
            method = c_uint32()
            _Clo_get_load_order_method(self._DB,byref(method))
            self._LOMethod = method.value

        def usingTxtFile(self):
            """Should be made private !"""
            return self._LOMethod == LIBLO_METHOD_TEXTFILE

        def SetGameMaster(self, plugin):
            _Clo_set_game_master(self._DB,_enc(plugin))

        def __del__(self):
            if self._DB is not None:
                _Clo_destroy_handle(self._DB)
                self._DB = None

        # ---------------------------------------------------------------------
        # Load Order management
        # ---------------------------------------------------------------------
        def GetLoadOrder(self):
            plugins = c_char_p_p()
            num = c_size_t()
            try:
                _Clo_get_load_order(self._DB, byref(plugins), byref(num))
            except LibloError as err:
                if err.code != LIBLO_WARN_INVALID_LIST: raise
                deprint(u'lo_get_load_order WARN_INVALID_LIST:',
                        traceback=True)
            return map(GPath, plugins[:num.value])
        def SetLoadOrder(self, plugins):
            plugins = [_enc(x) for x in plugins]
            num = len(plugins)
            plugins = list_of_strings(plugins)
            try:
                _Clo_set_load_order(self._DB, plugins, num)
            except LibloError as ex: # must notify the user that lo was not set
                deprint(u'lo_set_load_order failed:', traceback=True)
                raise BoltError(ex.msg), None, sys.exc_info()[2]


        # ---------------------------------------------------------------------
        # Active plugin management
        # ---------------------------------------------------------------------
        def GetActivePlugins(self):
            plugins = c_char_p_p()
            num = c_size_t()
            try:
                _Clo_get_active_plugins(self._DB, byref(plugins), byref(num))
            except LibloError as err:
                if err.code != LIBLO_WARN_INVALID_LIST: raise
                deprint(u'lo_get_active_plugins WARN_INVALID_LIST:',
                        traceback=True)
            return map(GPath, plugins[:num.value])
        def SetActivePlugins(self,plugins):
            plugins = [_enc(x) for x in plugins]
            num = len(plugins)
            plugins = list_of_strings(plugins)
            try:
                _Clo_set_active_plugins(self._DB, plugins, num)
            except LibloError as ex: # plugins.txt not written !
                deprint(u'lo_set_active_plugins failed:', traceback=True)
                raise BoltError(ex.msg), None, sys.exc_info()[2]

    # shadowing, must move LibloHandle, LibloError to module scope
    return LibloHandle, LibloError # return the public API

# Initialize libloadorder, assuming that loadorder32.dll and loadorder64.dll are in the same directory
# Call Init again with the path to these dll's if this assumption is incorrect.
# liblo will be None if this is the case.
try:
    LibloHandle, LibloError = Init(os.getcwdu())
except LibloVersionError:
    LibloHandle, LibloError = None, None
