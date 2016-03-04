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
"""Thin python wrapper around LOOT's API library.

To use outside of Bash replace the Bash import below with:
class Path: pass
"""
from ctypes import *
import os
from bolt import Path

LootApi = None
version = None
LootDb, LootError = None, None

# Version of LOOT this Python script is written for.
PythonAPIVersion = (0,6)

DebugLevel = 0
# DebugLevel
#  Set this for more or less feedback
#  0 - (default) no additional feedback
#  1 - print information about all return codes found

LOOT_GAME_TES4 = LOOT_GAME_TES5 = LOOT_GAME_FO3 = LOOT_GAME_FONV = None

class LootVersionError(Exception):
    """Exception thrown if the LOOT API loaded is not
       compatible with loot.py"""
    pass

class LootGameError(Exception):
    """Exception thrown if the LOOT API does not support
       the specified game."""
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

    global LootApi, LootDb, LootError

    # First unload any LOOT dll previously loaded
    del LootApi, LootDb, LootError
    LootApi = None

    if not os.path.exists(path):
        LootDb, LootError = None, None
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
        LootApi = LootDb = LootError = None
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

    # helpers
    def _uint(const): return c_uint.in_dll(LootApi, const).value

    # utility unicode functions
    def _uni(x): return u'' if x is None else unicode(x,'utf8')
    def _enc(x): return (x.encode('utf8') if isinstance(x,unicode)
                         else x.s.encode('utf8') if isinstance(x,Path)
                         else x)

    # =========================================================================
    # API Functions - Version
    # =========================================================================
    ## bool loot_is_compatible(const unsigned int versionMajor,
    #                          const unsigned int versionMinor,
    #                          const unsigned int versionPatch)
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
    LOOT_OK = _uint('loot_ok')
    LOOT_ERROR_LIBLO_ERROR = _uint('loot_error_liblo_error')
    LOOT_ERROR_FILE_WRITE_FAIL = _uint('loot_error_file_write_fail')
    LOOT_ERROR_PARSE_FAIL = _uint('loot_error_parse_fail')
    LOOT_ERROR_CONDITION_EVAL_FAIL = _uint('loot_error_condition_eval_fail')
    LOOT_ERROR_REGEX_EVAL_FAIL = _uint('loot_error_regex_eval_fail')
    LOOT_ERROR_NO_MEM = _uint('loot_error_no_mem')
    LOOT_ERROR_INVALID_ARGS = _uint('loot_error_invalid_args')
    LOOT_ERROR_NO_TAG_MAP = _uint('loot_error_no_tag_map')
    LOOT_ERROR_PATH_NOT_FOUND = _uint('loot_error_path_not_found')
    LOOT_ERROR_NO_GAME_DETECTED = _uint('loot_error_no_game_detected')
    LOOT_ERROR_WINDOWS_ERROR = _uint('loot_error_windows_error')
    LOOT_ERROR_SORTING_ERROR = _uint('loot_error_sorting_error')
    errors = dict((name, value) for name, value in locals().iteritems() if
                  name.startswith('LOOT_ERROR_'))
    LOOT_RETURN_MAX = _uint('loot_return_max')

    # =========================================================================
    # API Constants - Games
    # =========================================================================
    global LOOT_GAME_TES4, LOOT_GAME_TES5, LOOT_GAME_FO3, LOOT_GAME_FONV
    LOOT_GAME_TES4 = _uint('loot_game_tes4')
    LOOT_GAME_TES5 = _uint('loot_game_tes5')
    LOOT_GAME_FO3 = _uint('loot_game_fo3')
    LOOT_GAME_FONV = _uint('loot_game_fonv')
    games = {
        'Oblivion': LOOT_GAME_TES4,
        LOOT_GAME_TES4: LOOT_GAME_TES4,
        'Skyrim': LOOT_GAME_TES5,
        LOOT_GAME_TES5: LOOT_GAME_TES5,
        'Fallout3': LOOT_GAME_FO3,
        LOOT_GAME_FO3: LOOT_GAME_FO3,
        'FalloutNV': LOOT_GAME_FONV,
        LOOT_GAME_FONV: LOOT_GAME_FONV,
    }

    # =========================================================================
    # API Constants - Message Types
    # =========================================================================
    LOOT_MESSAGE_SAY = _uint('loot_message_say')
    LOOT_MESSAGE_WARN = _uint('loot_message_warn')
    LOOT_MESSAGE_ERROR = _uint('loot_message_error')

    # =========================================================================
    # API Constants - Languages
    # =========================================================================
    LOOT_LANG_ANY = _uint('loot_lang_any')
    # Other language constants are unused by Bash, so omitted here.

    # =========================================================================
    # API Constants - Cleanliness
    # =========================================================================
    LOOT_NEEDS_CLEANING_NO = _uint('loot_needs_cleaning_no')
    LOOT_NEEDS_CLEANING_YES = _uint('loot_needs_cleaning_yes')
    LOOT_NEEDS_CLEANING_UNKNOWN = _uint('loot_needs_cleaning_unknown')

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
        if ret != LOOT_OK:
            raise Exception(u'An error occurred while getting the details of a LOOT API error: %i' % ret)
        return unicode(details.value if details.value else 'None', 'utf8')

    class LootError(Exception):
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
                msg += '%s' % e
            self.msg = msg
            Exception.__init__(self,msg)

        def __repr__(self): return '<LootError: %r>' % self.msg
        def __str__(self): return 'LootError: %s' % self.msg

    def LootErrorCheck(result):
        if result == LOOT_OK: return result
        elif DebugLevel > 0:
            print GetLastErrorDetails()
        raise LootError(result)

    # =========================================================================
    # API Functions - Version
    # =========================================================================
    ## unsigned int loot_get_version(unsigned int * const versionMajor,
    #                                unsigned int * const versionMinor,
    #                                unsigned int * const versionPatch)
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
    ## unsigned int loot_create_db (loot_db * const db,
    #                               const unsigned int clientGame,
    #                               const char * const gamePath)
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
    ## unsigned int loot_load_lists (loot_db db,
    #                                const char * const masterlistPath,
    #                                const char * const userlistPath)
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
    ## unsigned int loot_get_tag_map (loot_db db, char *** const tagMap,
    #                                 size_t * const numTags)
    _CGetBashTagMap = LootApi.loot_get_tag_map
    _CGetBashTagMap.restype = LootErrorCheck
    _CGetBashTagMap.argtypes = [loot_db, c_char_p_p_p, c_size_t_p]
    ## unsigned int loot_get_plugin_tags (loot_db db,
    #                                     const char * const plugin,
    #                                     unsigned int ** const tags_added,
    #                                     size_t * const numTags_added,
    #                                     unsigned int ** const tags_removed,
    #                                     size_t * const numTags_removed,
    #                                     bool * const userlistModified)
    _CGetModBashTags = LootApi.loot_get_plugin_tags
    _CGetModBashTags.restype = LootErrorCheck
    _CGetModBashTags.argtypes = [loot_db, c_char_p, c_uint_p_p, c_size_t_p, c_uint_p_p, c_size_t_p, c_bool_p]
    ## loot_get_dirty_info (loot_db db, const char * const plugin,
    #                       unsigned int * const needsCleaning)
    _CGetDirtyMessage = LootApi.loot_get_dirty_info
    _CGetDirtyMessage.restype = LootErrorCheck
    _CGetDirtyMessage.argtypes = [loot_db, c_char_p, c_uint_p]
    ## unsigned int loot_write_minimal_list (loot_db db,
    #                                        const char * const outputFile,
    #                                        const bool overwrite)
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
                    raise LootGameError('Game "%s" is not recognized' % game)
            self.tags = {}   # BashTag map
            self._DB = loot_db()
            # print gamePath
            _CCreateLootDb(byref(self._DB),game,_enc(gamePath))

        def __del__(self):
            if self._DB is not None:
                _CDestroyLootDb(self._DB)
                self._DB = None

        # ---------------------------------------------------------------------
        # Database Loading
        # ---------------------------------------------------------------------
        def Load(self, masterlist, userlist=None):
            # Load masterlist/userlist
            self.PlainLoad(masterlist, userlist)
            self.EvalConditionals()

        def PlainLoad(self, masterlist, userlist=None):
            _CLoad(self._DB, _enc(masterlist), _enc(userlist) if userlist else None)

        def EvalConditionals(self):
            _CEvalConditionals(self._DB, LOOT_LANG_ANY)
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
            return added, removed, userlist.value

        def GetDirtyMessage(self,plugin):
            clean = c_uint()
            _CGetDirtyMessage(self._DB,_enc(plugin),byref(clean))
            if clean.value == LOOT_NEEDS_CLEANING_YES:
                return True, 'Contains dirty edits, needs cleaning.'
            else:
                return False, ''

        def DumpMinimal(self, file_, overwrite):
            _CDumpMinimal(self._DB, _enc(file_), overwrite)

        # ---------------------------------------------------------------------
        # Utility Functions (not added by the API, pure Python)
        # ---------------------------------------------------------------------
        def FilterDirty(self,plugins,cleanCode=LOOT_NEEDS_CLEANING_YES):
            """Given a list of plugins, returns the subset of that list,
               consisting of plugins that meet the given loot_needs_cleaning_*
               code"""
            return [x for x in plugins if self.GetDirtyMessage(x)[1] == cleanCode]

# Initialize the LOOT API, assuming that loot32.dll and loot64.dll are in
# the same directory. Call Init again with the path to these dll's if this
# assumption is incorrect. LootApi will be None if this is the case.
try:
    Init(os.getcwdu())
except LootVersionError:
    LootDb, LootError = None, None
