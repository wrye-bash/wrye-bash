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


"""Python wrapper around BOSS's API libraries"""


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

BAPI = None
version = None

# Version of BOSS API this Python script is written for.
PythonAPIVersion = (3,0)

DebugLevel = 0
# DebugLevel
#  Set this for more or less feedback
#  0 - (default) no additional feedback
#  1 - print information about all return codes found

class BossVersionError(Exception):
    """Exception thrown if the BOSS API loaded is not
       compatible with bapi.py"""
    pass

def Init(path):
    """Called automatically by importing bapi.  Can also be called manually
       by the user to reload BAPI, pointing to a different path to the dll.
   """

    # If path is a directory, auto choose DLL based on platform
    if os.path.isdir(path):
        #if '64bit' in platform.architecture():
        #    path = os.path.join(path,u'boss64.dll')
        #else:
            path = os.path.join(path,u'boss32.dll')

    global BAPI

    # First unload any BOSS dll previously loaded
    del BAPI
    BAPI = None

    if not os.path.exists(path):
        return

    try:
        # CDLL doesn't play with unicode path strings nicely on windows :(
        # Use this workaround
        handle = None
        if isinstance(path,unicode) and os.name in ('nt','ce'):
            LoadLibrary = windll.kernel32.LoadLibraryW
            handle = LoadLibrary(path)
        BAPI = CDLL(path,handle=handle)
    except Exception as e:
        BAPI = None
        raise

    # Some types
    boss_db = c_void_p
    boss_db_p = POINTER(boss_db)
    class boss_message(Structure):
        _fields_ = [('type', c_uint),
                    ('message', c_char_p),
                    ]
    c_char_p_p = POINTER(c_char_p)
    c_char_p_p_p = POINTER(c_char_p_p)
    c_uint_p = POINTER(c_uint)
    c_uint_p_p = POINTER(c_uint_p)
    c_size_t_p = POINTER(c_size_t)
    c_bool_p = POINTER(c_bool)
    boss_message_p = POINTER(boss_message)
    boss_message_p_p = POINTER(boss_message_p)

    # utility unicode functions
    def _uni(x): return u'' if x is None else unicode(x,'utf8')
    def _enc(x): return (x.encode('utf8') if isinstance(x,unicode)
                         else x.s.encode('utf8') if isinstance(x,Path)
                         else x)

    # =========================================================================
    # API Functions - Version
    # =========================================================================
    ## bool boss_is_compatible(const unsigned int versionMajor, const unsigned int versionMinor, const unsigned int versionPatch)
    _CIsCompatibleVersion = BAPI.boss_is_compatible
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
            BAPI.boss_get_version(byref(verMajor), byref(verMinor), byref(verPatch))
        except:
            raise BossVersionError('bapi.py is not compatible with the specified BOSS API DLL (%i.%i.%i).' % verMajor % verMinor % verPatch)

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
        name = 'boss_'+name
        errors[name] = c_uint.in_dll(BAPI,name).value
        ErrorCallbacks[errors[name]] = None
    boss_return_max = c_uint.in_dll(BAPI,'boss_return_max').value
    globals().update(errors)

    # =========================================================================
    # API Constants - Games
    # =========================================================================
    boss_game_tes4 = c_uint.in_dll(BAPI,'boss_game_tes4').value
    boss_game_tes5 = c_uint.in_dll(BAPI,'boss_game_tes5').value
    boss_game_fo3 = c_uint.in_dll(BAPI,'boss_game_fo3').value
    boss_game_fonv = c_uint.in_dll(BAPI,'boss_game_fonv').value
    games = {
        'Oblivion':boss_game_tes4,
        boss_game_tes4:boss_game_tes4,
        'Skyrim':boss_game_tes5,
        boss_game_tes5:boss_game_tes5,
        'Fallout 3':boss_game_fo3,
        boss_game_fo3:boss_game_fo3,
        'Fallout: New Vegas':boss_game_fonv,
        boss_game_fonv:boss_game_fonv,
        }
        
    # =========================================================================
    # API Constants - Message Types
    # =========================================================================
    boss_message_say = c_uint.in_dll(BAPI,'boss_message_say').value
    boss_message_warn = c_uint.in_dll(BAPI,'boss_message_warn').value
    boss_message_error = c_uint.in_dll(BAPI,'boss_message_error').value
    boss_message_tag = c_uint.in_dll(BAPI,'boss_message_tag').value
        
    # =========================================================================
    # API Constants - Languages
    # =========================================================================
    boss_lang_any = c_uint.in_dll(BAPI,'boss_lang_any').value
    boss_lang_english = c_uint.in_dll(BAPI,'boss_lang_english').value
    boss_lang_spanish = c_uint.in_dll(BAPI,'boss_lang_spanish').value
    boss_lang_russian = c_uint.in_dll(BAPI,'boss_lang_russian').value
        
    # =========================================================================
    # API Constants - Cleanliness
    # =========================================================================
    boss_needs_cleaning_no = c_uint.in_dll(BAPI,'boss_needs_cleaning_no').value
    boss_needs_cleaning_yes = c_uint.in_dll(BAPI,'boss_needs_cleaning_yes').value
    boss_needs_cleaning_unknown = c_uint.in_dll(BAPI,'boss_needs_cleaning_unknown').value

    # =========================================================================
    # API Functions - Error Handling
    # =========================================================================
    ## unsigned int boss_get_error_message(const char ** const message)
    _CGetLastErrorDetails = BAPI.boss_get_error_message
    _CGetLastErrorDetails.restype = c_uint
    _CGetLastErrorDetails.argtypes = [c_char_p_p]
    def GetLastErrorDetails():
        details = c_char_p()
        ret = _CGetLastErrorDetails(byref(details))
        if ret != boss_ok:
            raise Exception(u'An error occurred while getting the details of a BOSS API error: %i' % (ret))
        return unicode(details.value,'utf8')

    def RegisterCallback(errorCode,callback):
        """Used to setup callback functions for whenever specific error codes
           are encountered"""
        ErrorCallbacks[errorCode] = callback

    class BossError(Exception):
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

        def __repr__(self): return '<BossError: %s>' % self.msg
        def __str__(self): return 'BossError: %s' % self.msg

    def BossErrorCheck(result):
        callback = ErrorCallbacks.get(result,None)
        if callback: callback()
        if result == boss_ok: return result
        elif DebugLevel > 0:
            print GetLastErrorDetails()
        raise BossError(result)

    # =========================================================================
    # API Functions - Version
    # =========================================================================
    ## unsigned int boss_get_version(unsigned int * const versionMajor, unsigned int * const versionMinor, unsigned int * const versionPatch)
    _CGetVersionString = BAPI.boss_get_version
    _CGetVersionString.restype = BossErrorCheck
    _CGetVersionString.argtypes = [c_uint_p, c_uint_p, c_uint_p]
    global version
    version = c_char_p()
    try:
        verMajor = c_uint()
        verMinor = c_uint()
        verPatch = c_uint()
        _CGetVersionString(byref(verMajor),byref(verMinor),byref(verPatch))
        version = u'%i.%i.%i' % (verMajor.value,verMinor.value,verPatch.value)
    except BossError as e:
        print u'Error getting BOSS API version:', e
        version = u'Error'

    # =========================================================================
    # API Functions - Lifecycle Management
    # =========================================================================
    ## unsigned int boss_create_db (boss_db * const db, const unsigned int clientGame, const char * const gamePath)
    _CCreateBossDb = BAPI.boss_create_db
    _CCreateBossDb.restype = BossErrorCheck
    _CCreateBossDb.argtypes = [boss_db_p, c_uint, c_char_p]
    ## void boss_destroy_db(boss_db db)
    _CDestroyBossDb = BAPI.boss_destroy_db
    _CDestroyBossDb.restype = None
    _CDestroyBossDb.argtypes = [boss_db]

    # =========================================================================
    # API Functions - Database Loading
    # =========================================================================
    ## unsigned int boss_load_lists (boss_db db, const char * const masterlistPath,
    ##                                const char * const userlistPath)
    _CLoad = BAPI.boss_load_lists
    _CLoad.restype = BossErrorCheck
    _CLoad.argtypes = [boss_db, c_char_p, c_char_p]
    ## unsigned int boss_eval_lists (boss_db db, const unsigned int language)
    _CEvalConditionals = BAPI.boss_eval_lists
    _CEvalConditionals.restype = BossErrorCheck
    _CEvalConditionals.argtypes = [boss_db, c_uint]

    # =========================================================================
    # API Functions - Database Access
    # =========================================================================
    ## unsigned int boss_get_tag_map (boss_db db, char *** const tagMap, size_t * const numTags)
    _CGetBashTagMap = BAPI.boss_get_tag_map
    _CGetBashTagMap.restype = BossErrorCheck
    _CGetBashTagMap.argtypes = [boss_db, c_char_p_p_p, c_size_t_p]
    ## unsigned int boss_get_plugin_tags (boss_db db, const char * const plugin,
    ##                                        unsigned int ** const tags_added,
    ##                                        size_t * const numTags_added,
    ##                                        unsigned int ** const tags_removed,
    ##                                        size_t * const numTags_removed,
    ##                                        bool * const userlistModified)
    _CGetModBashTags = BAPI.boss_get_plugin_tags
    _CGetModBashTags.restype = BossErrorCheck
    _CGetModBashTags.argtypes = [boss_db, c_char_p, c_uint_p_p, c_size_t_p, c_uint_p_p, c_size_t_p, c_bool_p]
    ## boss_get_dirty_info (boss_db db, const char * const plugin,
    ##                                          unsigned int * const needsCleaning)
    _CGetDirtyMessage = BAPI.boss_get_dirty_info
    _CGetDirtyMessage.restype = BossErrorCheck
    _CGetDirtyMessage.argtypes = [boss_db, c_char_p, c_uint_p]
    ## unsigned int boss_write_minimal_list (boss_db db, const char * const outputFile, const bool overwrite)
    _CDumpMinimal = BAPI.boss_write_minimal_list
    _CDumpMinimal.restype = BossErrorCheck
    _CDumpMinimal.argtypes = [boss_db, c_char_p, c_bool]

    # =========================================================================
    # Class Wrapper
    # =========================================================================
    class BossDb(object):
        def __init__(self,gamePath,game='Oblivion'):
            """ game can be one of the boss_game_*** codes, or one of the
                aliases defined above in the 'games' dictionary."""
            if isinstance(game,basestring):
                if game in games:
                    game = games[game]
                else:
                    raise Exception('Game "%s" is not recognized' % game)
            self.tags = {}   # BashTag map
            self._DB = boss_db()
            print gamePath
            _CCreateBossDb(byref(self._DB),game,_enc(gamePath))

        def __del__(self):
            if self._DB is not None:
                _CDestroyBossDb(self._DB)
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
            _CEvalConditionals(self._DB, boss_lang_any)
            self._GetBashTags()
            
        def PlainLoad(self, masterlist, userlist=None):
            _CLoad(self._DB, _enc(masterlist), _enc(userlist) if userlist else None)

        def EvalConditionals(self):
            _CEvalConditionals(self._DB, boss_lang_any)
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
            if clean.value == boss_needs_cleaning_yes:
                return ('Contains dirty edits, needs cleaning.',clean.value)
            else:
                return ('',clean.value)
            
        def DumpMinimal(self,file,overwrite):
            _CDumpMinimal(self._DB,_enc(file),overwrite)

        # ---------------------------------------------------------------------
        # Utility Functions (not added by the API, pure Python)
        # ---------------------------------------------------------------------

        def FilterDirty(self,plugins,cleanCode=boss_needs_cleaning_yes):
            """Given a list of plugins, returns the subset of that list,
               consisting of plugins that meet the given boss_needs_cleaning_*
               code"""
            return [x for x in plugins if self.GetDirtyMessage(x)[1] == cleanCode]

    # Put the locally defined functions, classes, etc into the module global namespace
    globals().update(locals())

# Initialize BAPI, assuming that boss32.dll and boss64.dll are in the same directory
# Call Init again with the path to these dll's if this assumption is incorrect.
# BAPI will be None if this is the case.
try:
    Init(os.getcwdu())
except BossVersionError:
    pass
