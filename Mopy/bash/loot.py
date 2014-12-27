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
#  Wrye Bolt is distributed in the hope that it will be useful,
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


"""Python wrapper around LOOT's API library."""


from ctypes import *
import os
import platform

try:
    # Wrye Bash specific support
    import bolt
    from bolt import Path, GPath
except:
    class Path:
        pass
    def GPath(x): return x

LootApi = None
version = None

# Version of LOOT this Python script is written for.
PythonAPIVersion = (0,6)

DebugLevel = 0
# DebugLevel
#  Set this for more or less feedback
#  0 - (default) no additional feedback
#  1 - print information about all return codes found

class LootVersionError(Exception):
    """Exception thrown if the LOOT API loaded is not
       compatible with loot.py"""
    pass

def Init(path):
    """Called automatically by importing loot.  Can also be called manually
       by the user to reload the LOOT API, pointing to a different path to the dll.
   """

    # If path is a directory, auto choose DLL based on platform
    if os.path.isdir(path):
        #if '64bit' in platform.architecture():
        #    path = os.path.join(path,u'loot64.dll')
        #else:
            path = os.path.join(path,u'loot32.dll')

    global LootApi

    # First unload any LOOT dll previously loaded
    del LootApi
    LootApi = None

    if not os.path.exists(path):
        return

    try:
        # CDLL doesn't play with unicode path strings nicely on windows :(
        # Use this workaround
        handle = None
        if isinstance(path,unicode) and os.name in ('nt','ce'):
            LoadLibrary = windll.kernel32.LoadLibraryW
            handle = LoadLibrary(path)
        LootApi = CDLL(path,handle=handle)
    except Exception as e:
        LootApi = None
        raise

    # Some types
    loot_db = c_void_p
    loot_db_p = POINTER(loot_db)
    class loot_message(Structure):
        _fields_ = [('type', c_uint),
                    ('message', c_char_p),
                    ]
    c_char_p_p = POINTER(c_char_p)
    c_char_p_p_p = POINTER(c_char_p_p)
    c_uint_p = POINTER(c_uint)
    c_uint_p_p = POINTER(c_uint_p)
    c_size_t_p = POINTER(c_size_t)
    c_bool_p = POINTER(c_bool)
    loot_message_p = POINTER(loot_message)
    loot_message_p_p = POINTER(loot_message_p)

    # utility unicode functions
    def _uni(x): return u'' if x is None else unicode(x,'utf8')
    def _enc(x): return (x.encode('utf8') if isinstance(x,unicode)
                         else x.s.encode('utf8') if isinstance(x,Path)
                         else x)

    # =========================================================================
    # API Functions - Version
    # =========================================================================
    ## bool loot_is_compatible(const unsigned int versionMajor, const unsigned int versionMinor, const unsigned int versionPatch)
    _CIsCompatibleVersion = LootApi.loot_is_compatible
    _CIsCompatibleVersion.restype = c_bool
    _CIsCompatibleVersion.argtypes = [c_uint, c_uint, c_uint]
    def IsCompatibleVersion(majorVersion, minorVersion, patchVersion=0):
        return True
        return _CIsCompatibleVersion(majorVersion,minorVersion,patchVersion)
    if not IsCompatibleVersion(*PythonAPIVersion):
        verMajor = c_uint()
        verMinor = c_uint()
        verPatch = c_uint()
        try:
            LootApi.loot_is_compatible(byref(verMajor), byref(verMinor), byref(verPatch))
        except:
            raise LootVersionError('loot.py is not compatible with the specified LOOT DLL (%i.%i.%i).' % verMajor % verMinor % verPatch)

    # =========================================================================
    # API Constants - Return codes
    # =========================================================================
    errors = {}
    ErrorCallbacks = {}
    for name in ['ok',
                 'error_liblo_error',
                 'error_file_write_fail',
                 'error_parse_fail',
                 'error_condition_eval_fail',
                 'error_regex_eval_fail',
                 'error_no_mem',
                 'error_invalid_args',
                 'error_no_tag_map',
                 'error_path_not_found',
                 'error_no_game_detected',
                 'error_windows_error',
                 'error_sorting_error',
                 ]:
        name = 'loot_'+name
        errors[name] = c_uint.in_dll(LootApi,name).value
        ErrorCallbacks[errors[name]] = None
    loot_return_max = c_uint.in_dll(LootApi,'loot_return_max').value
    globals().update(errors)

    # =========================================================================
    # API Constants - Games
    # =========================================================================
    loot_game_tes4 = c_uint.in_dll(LootApi,'loot_game_tes4').value
    loot_game_tes5 = c_uint.in_dll(LootApi,'loot_game_tes5').value
    loot_game_fo3 = c_uint.in_dll(LootApi,'loot_game_fo3').value
    loot_game_fonv = c_uint.in_dll(LootApi,'loot_game_fonv').value
    games = {
        'Oblivion':loot_game_tes4,
        loot_game_tes4:loot_game_tes4,
        'Skyrim':loot_game_tes5,
        loot_game_tes5:loot_game_tes5,
        'Fallout3':loot_game_fo3,
        loot_game_fo3:loot_game_fo3,
        'FalloutNV':loot_game_fonv,
        loot_game_fonv:loot_game_fonv,
        }

    # =========================================================================
    # API Constants - Message Types
    # =========================================================================
    loot_message_say = c_uint.in_dll(LootApi,'loot_message_say').value
    loot_message_warn = c_uint.in_dll(LootApi,'loot_message_warn').value
    loot_message_error = c_uint.in_dll(LootApi,'loot_message_error').value

    # =========================================================================
    # API Constants - Languages
    # =========================================================================
    loot_lang_any = c_uint.in_dll(LootApi,'loot_lang_any').value
    # Other language constants are unused by Bash, so omitted here.

    # =========================================================================
    # API Constants - Cleanliness
    # =========================================================================
    loot_needs_cleaning_no = c_uint.in_dll(LootApi,'loot_needs_cleaning_no').value
    loot_needs_cleaning_yes = c_uint.in_dll(LootApi,'loot_needs_cleaning_yes').value
    loot_needs_cleaning_unknown = c_uint.in_dll(LootApi,'loot_needs_cleaning_unknown').value

    # =========================================================================
    # API Functions - Error Handling
    # =========================================================================
    ## unsigned int loot_get_error_message(const char ** const message)
    _CGetLastErrorDetails = LootApi.loot_get_error_message
    _CGetLastErrorDetails.restype = c_uint
    _CGetLastErrorDetails.argtypes = [c_char_p_p]
    def GetLastErrorDetails():
        details = c_char_p()
        ret = _CGetLastErrorDetails(byref(details))
        if ret != loot_ok:
            raise Exception(u'An error occurred while getting the details of a LOOT API error: %i' % (ret))
        return unicode(details.value,'utf8')

    def RegisterCallback(errorCode,callback):
        """Used to setup callback functions for whenever specific error codes
           are encountered"""
        ErrorCallbacks[errorCode] = callback

    class LootError(Exception):
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

        def __repr__(self): return '<LootError: %s>' % self.msg
        def __str__(self): return 'LootError: %s' % self.msg

    def LootErrorCheck(result):
        callback = ErrorCallbacks.get(result,None)
        if callback: callback()
        if result == loot_ok: return result
        elif DebugLevel > 0:
            print GetLastErrorDetails()
        raise LootError(result)

    # =========================================================================
    # API Functions - Version
    # =========================================================================
    ## unsigned int loot_get_version(unsigned int * const versionMajor, unsigned int * const versionMinor, unsigned int * const versionPatch)
    _CGetVersionString = LootApi.loot_get_version
    _CGetVersionString.restype = LootErrorCheck
    _CGetVersionString.argtypes = [c_uint_p, c_uint_p, c_uint_p]
    global version
    version = c_char_p()
    try:
        verMajor = c_uint()
        verMinor = c_uint()
        verPatch = c_uint()
        _CGetVersionString(byref(verMajor),byref(verMinor),byref(verPatch))
        version = u'%i.%i.%i' % (verMajor.value,verMinor.value,verPatch.value)
    except LootError as e:
        print u'Error getting LOOT API version:', e
        version = u'Error'

    # =========================================================================
    # API Functions - Lifecycle Management
    # =========================================================================
    ## unsigned int loot_create_db (loot_db * const db, const unsigned int clientGame, const char * const gamePath)
    _CCreateLootDb = LootApi.loot_create_db
    _CCreateLootDb.restype = LootErrorCheck
    _CCreateLootDb.argtypes = [loot_db_p, c_uint, c_char_p]
    ## void loot_destroy_db(loot_db db)
    _CDestroyLootDb = LootApi.loot_destroy_db
    _CDestroyLootDb.restype = None
    _CDestroyLootDb.argtypes = [loot_db]

    # =========================================================================
    # API Functions - Database Loading
    # =========================================================================
    ## unsigned int loot_load_lists (loot_db db, const char * const masterlistPath,
    ##                                const char * const userlistPath)
    _CLoad = LootApi.loot_load_lists
    _CLoad.restype = LootErrorCheck
    _CLoad.argtypes = [loot_db, c_char_p, c_char_p]
    ## unsigned int loot_eval_lists (loot_db db, const unsigned int language)
    _CEvalConditionals = LootApi.loot_eval_lists
    _CEvalConditionals.restype = LootErrorCheck
    _CEvalConditionals.argtypes = [loot_db, c_uint]

    # =========================================================================
    # API Functions - Database Access
    # =========================================================================
    ## unsigned int loot_get_tag_map (loot_db db, char *** const tagMap, size_t * const numTags)
    _CGetBashTagMap = LootApi.loot_get_tag_map
    _CGetBashTagMap.restype = LootErrorCheck
    _CGetBashTagMap.argtypes = [loot_db, c_char_p_p_p, c_size_t_p]
    ## unsigned int loot_get_plugin_tags (loot_db db, const char * const plugin,
    ##                                        unsigned int ** const tags_added,
    ##                                        size_t * const numTags_added,
    ##                                        unsigned int ** const tags_removed,
    ##                                        size_t * const numTags_removed,
    ##                                        bool * const userlistModified)
    _CGetModBashTags = LootApi.loot_get_plugin_tags
    _CGetModBashTags.restype = LootErrorCheck
    _CGetModBashTags.argtypes = [loot_db, c_char_p, c_uint_p_p, c_size_t_p, c_uint_p_p, c_size_t_p, c_bool_p]
    ## loot_get_dirty_info (loot_db db, const char * const plugin,
    ##                                          unsigned int * const needsCleaning)
    _CGetDirtyMessage = LootApi.loot_get_dirty_info
    _CGetDirtyMessage.restype = LootErrorCheck
    _CGetDirtyMessage.argtypes = [loot_db, c_char_p, c_uint_p]
    ## unsigned int loot_write_minimal_list (loot_db db, const char * const outputFile, const bool overwrite)
    _CDumpMinimal = LootApi.loot_write_minimal_list
    _CDumpMinimal.restype = LootErrorCheck
    _CDumpMinimal.argtypes = [loot_db, c_char_p, c_bool]

    # =========================================================================
    # Class Wrapper
    # =========================================================================
    class LootDb(object):
        def __init__(self,gamePath,game='Oblivion'):
            """ game can be one of the loot_game_*** codes, or one of the
                aliases defined above in the 'games' dictionary."""
            if isinstance(game,basestring):
                if game in games:
                    game = games[game]
                else:
                    raise Exception('Game "%s" is not recognized' % game)
            self.tags = {}   # BashTag map
            self._DB = loot_db()
            print gamePath
            _CCreateLootDb(byref(self._DB),game,_enc(gamePath))

        def __del__(self):
            if self._DB is not None:
                _CDestroyLootDb(self._DB)
                self._DB = None

        # 'with' statement
        def __enter__(self): return self
        def __exit__(self,exc_type,exc_value,traceback): self.__del__()

        # ---------------------------------------------------------------------
        # Database Loading
        # ---------------------------------------------------------------------
        def Load(self, masterlist, userlist=None):
            # Load masterlist/userlist
            _CLoad(self._DB, _enc(masterlist), _enc(userlist) if userlist else None)
            _CEvalConditionals(self._DB, loot_lang_any)
            self._GetBashTags()

        def PlainLoad(self, masterlist, userlist=None):
            _CLoad(self._DB, _enc(masterlist), _enc(userlist) if userlist else None)

        def EvalConditionals(self):
            _CEvalConditionals(self._DB, loot_lang_any)
            self._GetBashTags()

        def _GetBashTags(self):
            num = c_size_t()
            bashTags = c_char_p_p()
            _CGetBashTagMap(self._DB, byref(bashTags), byref(num))
            self.tags = {i:_uni(bashTags[i])
                         for i in xrange(num.value)}

        # ---------------------------------------------------------------------
        # DB Access
        # ---------------------------------------------------------------------
        def GetModBashTags(self,plugin):
            tagIds_added = c_uint_p()
            numAdded = c_size_t()
            tagIds_removed = c_uint_p()
            numRemoved = c_size_t()
            userlist = c_bool()
            _CGetModBashTags(self._DB, _enc(plugin),
                             byref(tagIds_added), byref(numAdded),
                             byref(tagIds_removed), byref(numRemoved),
                             byref(userlist))
            added = set([self.tags[tagIds_added[i]] for i in xrange(numAdded.value)])
            removed = set([self.tags[tagIds_removed[i]] for i in xrange(numRemoved.value)])
            return (added, removed, userlist.value)

        def GetDirtyMessage(self,plugin):
            clean = c_uint()
            _CGetDirtyMessage(self._DB,_enc(plugin),byref(clean))
            if clean.value == loot_needs_cleaning_yes:
                return ('Contains dirty edits, needs cleaning.',clean.value)
            else:
                return ('',clean.value)

        def DumpMinimal(self,file,overwrite):
            _CDumpMinimal(self._DB,_enc(file),overwrite)

        # ---------------------------------------------------------------------
        # Utility Functions (not added by the API, pure Python)
        # ---------------------------------------------------------------------

        def FilterDirty(self,plugins,cleanCode=loot_needs_cleaning_yes):
            """Given a list of plugins, returns the subset of that list,
               consisting of plugins that meet the given loot_needs_cleaning_*
               code"""
            return [x for x in plugins if self.GetDirtyMessage(x)[1] == cleanCode]

    # Put the locally defined functions, classes, etc into the module global namespace
    globals().update(locals())

# Initialize the LOOT API, assuming that loot32.dll and loot64.dll are in the same directory
# Call Init again with the path to these dll's if this assumption is incorrect.
# LootApi will be None if this is the case.
try:
    Init(os.getcwdu())
except LootVersionError:
    pass
