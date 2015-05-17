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
def GPath(x): return u'' if x is None else unicode(x, 'utf8')
"""

from ctypes import *
import os
from bolt import Path, GPath

liblo = None
version = None

# Version of libloadorder this Python script is written for.
PythonLibloVersion = (4,0)

DebugLevel = 0
# DebugLevel
#  Set this for more or less feedback
#  0 - (default) no additional feedback
#  1 - print information about all return codes found

class LibloVersionError(Exception):
    """Exception thrown if the libloadorder loaded is not
       compatible with liblo.py"""
    pass

# API alpha - what is currently used in bash:
LIBLO_ERROR_INVALID_ARGS = None
LIBLO_WARN_LO_MISMATCH = None
LIBLO_OK = None
LibloError = None
LibloHandle = None
RegisterCallback = None

# TMP helper
class _raise(object):
    def __init__(self, oper): self.oper = oper
    def r(self, *args, **kwargs):
        raise Exception('Unsupported Operation: ' + self.oper)

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
    ##: global LIBLO_ERROR_INVALID_ARGS, \
    #     LIBLO_WARN_LO_MISMATCH,  LibloError, LibloHandle
    # First unload any libloadorder dll previously loaded
    del liblo
    liblo = None

    if not os.path.exists(path):
        return

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
    LIBLO_GAME_TES4 = c_uint.in_dll(liblo,'LIBLO_GAME_TES4').value
    LIBLO_GAME_TES5 = c_uint.in_dll(liblo,'LIBLO_GAME_TES5').value
    LIBLO_GAME_FO3 = c_uint.in_dll(liblo,'LIBLO_GAME_FO3').value
    LIBLO_GAME_FNV = c_uint.in_dll(liblo,'LIBLO_GAME_FNV').value
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
    LIBLO_METHOD_TIMESTAMP = c_uint.in_dll(liblo,'LIBLO_METHOD_TIMESTAMP').value
    LIBLO_METHOD_TEXTFILE = c_uint.in_dll(liblo,'LIBLO_METHOD_TEXTFILE').value

    # =========================================================================
    # API Constants - Return codes
    # =========================================================================
    errors = {}
    ErrorCallbacks = {}
    for name in ['OK',
                 'WARN_BAD_FILENAME',
                 'WARN_LO_MISMATCH',
                 'ERROR_FILE_READ_FAIL',
                 'ERROR_FILE_WRITE_FAIL',
                 'ERROR_FILE_RENAME_FAIL',
                 'ERROR_FILE_PARSE_FAIL',
                 'ERROR_FILE_NOT_UTF8',
                 'ERROR_FILE_NOT_FOUND',
                 'ERROR_TIMESTAMP_READ_FAIL',
                 'ERROR_TIMESTAMP_WRITE_FAIL',
                 'ERROR_NO_MEM',
                 'ERROR_INVALID_ARGS',
                 ]:
        name = 'LIBLO_'+name
        errors[name] = c_uint.in_dll(liblo,name).value
        ErrorCallbacks[errors[name]] = None
    LIBLO_RETURN_MAX = c_uint.in_dll(liblo,'LIBLO_RETURN_MAX').value
    globals().update(errors)

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
        return unicode(details.value,'utf8')

    def RegisterCallback(errorCode,callback):
        """Used to setup callback functions for whenever specific error codes
           are encountered"""
        ErrorCallbacks[errorCode] = callback

    class LibloError(Exception):
        def __init__(self,value):
            self.code = value
            msg = 'UNKNOWN(%i)' % value
            for code in errors:
                if errors[code] == value:
                    msg = code
                    break
            msg += ':'
            try:
                msg += GetLastErrorDetails()
            except Exception as e:
                msg += '%s' % e
            self.msg = msg
            Exception.__init__(self,msg)

        def __repr__(self): return '<LibloError: %s>' % self.msg
        def __str__(self): return 'LibloError: %s' % self.msg

    def LibloErrorCheck(result):
        callback = ErrorCallbacks.get(result,None)
        if callback: callback()
        if result == LIBLO_OK: return result
        elif DebugLevel > 0:
            print GetLastErrorDetails()
        raise LibloError(result)

    # =========================================================================
    # API Functions - Version
    # =========================================================================
    ## unsigned int lo_get_version(unsigned int * const versionMajor, unsigned int * const versionMinor, unsigned int * const versionPatch)
    _Clo_get_version = liblo.lo_get_version
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
    _Clo_create_handle.argtypes = [lo_game_handle_p, c_uint, c_char_p]
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
    ## unsigned int lo_get_plugin_position(lo_game_handle gh, const char * const plugin, size_t * const index);
    _Clo_get_plugin_position = liblo.lo_get_plugin_position
    _Clo_get_plugin_position.restype = LibloErrorCheck
    _Clo_get_plugin_position.argtypes = [lo_game_handle, c_char_p, c_size_t_p]
    ## unsigned int lo_set_plugin_position(lo_game_handle gh, const char * const plugin, size_t index);
    _Clo_set_plugin_position = liblo.lo_set_plugin_position
    _Clo_set_plugin_position.restype = LibloErrorCheck
    _Clo_set_plugin_position.argtypes = [lo_game_handle, c_char_p, c_size_t]
    ## unsigned int lo_get_indexed_plugin(lo_game_handle gh, const size_t index, char ** const plugin);
    _Clo_get_indexed_plugin = liblo.lo_get_indexed_plugin
    _Clo_get_indexed_plugin.restype = LibloErrorCheck
    _Clo_get_indexed_plugin.argtypes = [lo_game_handle, c_size_t, c_char_p_p]

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
    ## unsigned int lo_set_plugin_active(lo_game_handle gh, const char * const plugin, const bool active);
    _Clo_set_plugin_active = liblo.lo_set_plugin_active
    _Clo_set_plugin_active.restype = LibloErrorCheck
    _Clo_set_plugin_active.argtypes = [lo_game_handle, c_char_p, c_bool]
    ## unsigned int lo_get_plugin_active(lo_game_handle gh, const char * const plugin, bool * const result);
    _Clo_get_plugin_active = liblo.lo_get_plugin_active
    _Clo_get_plugin_active.restype = LibloErrorCheck
    _Clo_get_plugin_active.argtypes = [lo_game_handle, c_char_p, c_bool_p]

    # =========================================================================
    # Class Wrapper
    # =========================================================================
    class LibloHandle(object):
        def __init__(self,gamePath,game='Oblivion'):
            """ game can be one of the LIBLO_GAME_*** codes, or one of the
                aliases defined above in the 'games' dictionary."""
            if isinstance(game,basestring):
                if game in games:
                    game = games[game]
                else:
                    raise Exception('Game "%s" is not recognized' % game)
            self._DB = lo_game_handle()
            try:
                _Clo_create_handle(byref(self._DB),game,_enc(gamePath))
            except LibloError as err:
                if err.args[0].startswith("LIBLO_WARN_LO_MISMATCH"):
                    # If there is a Mismatch between loadorder.txt and plugns.txt finish initialization
                    # and fix the missmatch at a later time
                    pass
                else:
                    raise err
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

        # 'with' statement
        def __enter__(self): return self
        def __exit__(self,exc_type,exc_value,traceback): self.__del__()

        # ---------------------------------------------------------------------
        # Load Order management
        # ---------------------------------------------------------------------
        # Block the following 'list' functions, since they don't make sense
        # for use with libloadorder
        _verboten = dict((v, _raise(v)) for v in {'__setitem__', '__imul__',
            '__idiv__', '__itruediv__', '__ifloordiv__', '__imod__',
            '__ipow__', '__ilshift__', '__irshift__', '__iand__', '__ixor__',
            '__ior__', 'pop', 'sort', 'reverse'})
        class _lo_list(list): # DEPRECATED  helper class
            def __init__(self, *args, **kwargs):
                self._DB = kwargs.pop('db') # LibloHandle python class
                super(LibloHandle._lo_list, self).__init__(*args, **kwargs)

            def count(self,x):
                # 1 if the plugin is in the Load Order, 0 otherwise
                # (plugins can't be in the load order multiple times)
                super_count = super(LibloHandle._lo_list, self).count(x)
                assert super_count in {0, 1} # for #100
                return super_count
        for k, v in _verboten.iteritems(): setattr(_lo_list, k, v.r)

        class LoadOrderList(_lo_list):
            """list-like object for manipulating load order"""

            # list method overrides
            def insert(self,i,x):
                # Change Load Order of single plugin
                self._DB.SetPluginLoadOrder(x, i)
            def index(self,x):
                # Get Load Order of single plugin
                return self._DB.GetPluginLoadOrder(x)
        _verboten = dict((v, _raise(v)) for v in {'append', '__isub__',
            '__delitem__', '__iadd__', 'extend', 'remove'})
        for k, v in _verboten.iteritems(): setattr(LoadOrderList, k, v.r)
        del _verboten # we don't want this in globals()

        def GetLoadOrder(self):
            plugins = c_char_p_p()
            num = c_size_t()
            _Clo_get_load_order(self._DB, byref(plugins), byref(num))
            return map(GPath, plugins[:num.value])
        def _GetLoadOrder(self):
            return self.LoadOrderList(self.GetLoadOrder(), db=self)
        def SetLoadOrder(self, plugins):
            plugins = [_enc(x) for x in plugins]
            num = len(plugins)
            plugins = list_of_strings(plugins)
            _Clo_set_load_order(self._DB, plugins, num)
        LoadOrder = property(_GetLoadOrder,SetLoadOrder)

        def GetPluginLoadOrder(self, plugin):
            plugin = _enc(plugin)
            index = c_size_t()
            _Clo_get_plugin_position(self._DB,plugin,byref(index))
            return index.value

        def SetPluginLoadOrder(self, plugin, index):
            plugin = _enc(plugin)
            _Clo_set_plugin_position(self._DB,plugin,index)

        def GetIndexedPlugin(self, index):
            plugin = c_char_p()
            _Clo_get_indexed_plugin(self._DB,index,byref(plugin))
            return GPath(plugin.value)

        # ---------------------------------------------------------------------
        # Active plugin management
        # ---------------------------------------------------------------------
        class ActivePluginsList(_lo_list): # should be a set !
            """list-like object for modifying which plugins are active.
               Currently, you cannot change the Load Order through this
               object, perhaps in the future."""

            def ReSync(self):
                """Resync's contents with libloadorder"""
                list.__setslice__(self,0,len(self),self._DB.ActivePlugins)

            ## del ActivePlugins[i]
            def __delitem__(self,key):
                # Deactivate the plugin
                self._DB.SetPluginActive(self[key],False)
                self.ReSync()

            ## ActivePlugins += ['test.esp','another.esp']
            def __iadd__(self,other):
                for plugin in other:
                    self._DB.SetPluginActive(plugin,True)
                self.ReSync()
                return self
            ## ActivePlugins -= ['test.esp','another.esp']
            def __isub__(self,other):
                for plugin in other:
                    self._DB.SetPluginActive(plugin,False)
                self.ReSync()
                return self

            ## ActivePlugins.append('test.esp')
            def append(self,item):
                self._DB.SetPluginActive(item,True)
                self.ReSync()

            ## ActivePlugins.extend(['test.esp','another.esp'])
            def extend(self,items):
                for plugin in items:
                    self._DB.SetPluginActive(plugin,True)
                self.ReSync()

            ## ActivePlugins.remove('test.esp')
            def remove(self,item):
                self._DB.SetPluginActive(item,False)
                self.ReSync()

            ## ActivePlugins.insert('test.esp')
            def insert(self,index,item):
                self._DB.SetPluginActive(item,True)
                self.ReSync()

        def GetActivePlugins(self, lo_with_corrected_master=None):
            plugins = c_char_p_p()
            num = c_size_t()
            _Clo_get_active_plugins(self._DB, byref(plugins), byref(num))
            return self.GetOrdered(map(GPath, plugins[:num.value]), selfLoadOrder=lo_with_corrected_master)
        def _GetActivePlugins(self):
            return self.ActivePluginsList(self.GetActivePlugins(), db=self)
        def SetActivePlugins(self,plugins):
            plugins = [_enc(x) for x in plugins]
            if self._LOMethod == LIBLO_METHOD_TEXTFILE and u'Update.esm' not in plugins:
                plugins.append(u'Update.esm')
            num = len(plugins)
            plugins = list_of_strings(plugins)
            _Clo_set_active_plugins(self._DB, plugins, num)
        ActivePlugins = property(_GetActivePlugins,SetActivePlugins)

        def SetPluginActive(self,plugin,active=True):
            _Clo_set_plugin_active(self._DB,_enc(plugin),active)

        def IsPluginActive(self,plugin):
            active = c_bool()
            _Clo_get_plugin_active(self._DB,_enc(plugin),byref(active))
            return active.value

        # ---------------------------------------------------------------------
        # Utility Functions (not added by the API, pure Python)
        # ---------------------------------------------------------------------
        def FilterActive(self,plugins,active=True):
            """Given a list of plugins, returns the subset of that list,
               consisting of:
                - only active plugins if 'active' is True
                - only inactive plugins if 'active' is False"""
            return [x for x in plugins if self.IsPluginActive(x) ^ (not active)]

        def DeactivatePlugins(self,plugins):
            for plugin in plugins:
                self.SetPluginActive(plugin,False)

        def GetOrdered(self,plugins,selfLoadOrder=None):
            """Returns a list of the given plugins, sorted according to their
               load order"""
            selfLoadOrder = selfLoadOrder if selfLoadOrder else self.LoadOrder
            return [x for x in selfLoadOrder if x in plugins]

    # Put the locally defined functions, classes, etc into the module global namespace
    globals().update(locals())

# Initialize libloadorder, assuming that loadorder32.dll and loadorder64.dll are in the same directory
# Call Init again with the path to these dll's if this assumption is incorrect.
# liblo will be None if this is the case.
try:
    Init(os.getcwdu())
except LibloVersionError:
    pass
