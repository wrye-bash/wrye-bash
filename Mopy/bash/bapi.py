# -*- coding: utf-8 -*-
# Python wrapper around BOSS's API libraries
# by Jacob Lojewski (aka Lojack)

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
PythonAPIVersion = (2,1)

DebugLevel = 0
# DebugLevel
#  Set this for more or less feedback
#  0 - (default) no additional feedback
#  1 - print a statement to stdout when any BOSS_API_WARN return code is found
#  2 - print information about all return codes found

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
        if '64bit' in platform.architecture():
            path = os.path.join(path,u'boss64.dll')
        else:
            path = os.path.join(path,u'boss32.dll')

    global BAPI

    # First unload any BOSS dll previously loaded
    del BAPI
    BAPI = None

    if not os.path.exists(path):
        return

    try:
        BAPI = CDLL(path)
    except Exception as e:
        BAPI = None
        raise

    # Some types
    boss_db = c_void_p
    boss_db_p = POINTER(boss_db)
    c_uint32_p = POINTER(c_uint32)
    c_uint32_p_p = POINTER(c_uint32_p)
    c_bool_p = POINTER(c_bool)
    c_uint8_p = c_char_p
    c_uint8_p_p = POINTER(c_uint8_p)
    c_uint8_p_p_p = POINTER(c_uint8_p_p)
    c_size_t_p = POINTER(c_size_t)
    class BashTag(Structure):
        _fields_ = [('id',c_uint32),
                    ('name',c_uint8_p),
                    ]
    BashTag_p = POINTER(BashTag)
    BashTag_p_p = POINTER(BashTag_p)
    def list_of_strings(strings):
        lst = (c_uint8_p * len(strings))()
        lst = cast(lst,c_uint8_p_p)
        for i,string in enumerate(strings):
            lst[i] = cast(create_string_buffer(string),c_uint8_p)
        return lst

    # utility unicode functions
    def _uni(x): return u'' if x is None else unicode(x,'utf8')
    def _enc(x): return (x.encode('utf8') if isinstance(x,unicode)
                         else x.s.encode('utf8') if isinstance(x,Path)
                         else x)

    # =========================================================================
    # API Functions - Version
    # =========================================================================
    ## bool IsCompatibleVersion(const uint32_t bossVersionMajor, const uint32_t bossVersionMinor, const uint32_t bossVersionPatch)
    _CIsCompatibleVersion = BAPI.IsCompatibleVersion
    _CIsCompatibleVersion.restype = c_bool
    _CIsCompatibleVersion.argtypes = [c_uint32, c_uint32, c_uint32]
    def IsCompatibleVersion(majorVersion, minorVersion, patchVersion=0):
        return True
        return _CIsCompatibleVersion(majorVersion,minorVersion,patchVersion)
    if not IsCompatibleVersion(*PythonAPIVersion):
        try:
            ver = c_uint8_p()
            BAPI.GetVersionString(byref(ver))
            ver = _uni(ver.value)
        except:
            ver = ''
        raise BossVersionError('bapi.py is not compatible with the specified BOSS API DLL (%s).' % ver)

    # =========================================================================
    # API Constants - Games
    # =========================================================================
    BOSS_API_GAME_OBLIVION = c_uint.in_dll(BAPI,'BOSS_API_GAME_OBLIVION').value
    BOSS_API_GAME_FALLOUT3 = c_uint.in_dll(BAPI,'BOSS_API_GAME_FALLOUT3').value
    BOSS_API_GAME_FALLOUTNV=c_uint.in_dll(BAPI,'BOSS_API_GAME_FALLOUTNV').value
    BOSS_API_GAME_NEHRIM = c_uint.in_dll(BAPI,'BOSS_API_GAME_NEHRIM').value
    BOSS_API_GAME_SKYRIM = c_uint.in_dll(BAPI,'BOSS_API_GAME_SKYRIM').value
    games = {
        'Oblivion':BOSS_API_GAME_OBLIVION,
        BOSS_API_GAME_OBLIVION:BOSS_API_GAME_OBLIVION,
        'Fallout 3':BOSS_API_GAME_FALLOUT3,
        BOSS_API_GAME_FALLOUT3:BOSS_API_GAME_FALLOUT3,
        'Fallout: New Vegas':BOSS_API_GAME_FALLOUTNV,
        BOSS_API_GAME_FALLOUTNV:BOSS_API_GAME_FALLOUTNV,
        'Nehrim':BOSS_API_GAME_NEHRIM,
        BOSS_API_GAME_NEHRIM:BOSS_API_GAME_NEHRIM,
        'Skyrim':BOSS_API_GAME_SKYRIM,
        BOSS_API_GAME_SKYRIM:BOSS_API_GAME_SKYRIM,
        }

    # =========================================================================
    # API Constants - Load Order Method
    # =========================================================================
    BOSS_API_LOMETHOD_TIMESTAMP = c_uint.in_dll(BAPI,'BOSS_API_LOMETHOD_TIMESTAMP').value
    BOSS_API_LOMETHOD_TEXTFILE = c_uint.in_dll(BAPI,'BOSS_API_LOMETHOD_TEXTFILE').value

    # =========================================================================
    # API Constants - Cleanliness
    # =========================================================================
    BOSS_API_CLEAN_NO = c_uint.in_dll(BAPI,'BOSS_API_CLEAN_NO').value
    BOSS_API_CLEAN_YES = c_uint.in_dll(BAPI,'BOSS_API_CLEAN_YES').value
    BOSS_API_CLEAN_UNKNOWN = c_uint.in_dll(BAPI,'BOSS_API_CLEAN_UNKNOWN').value

    # =========================================================================
    # API Constants - Return codes
    # =========================================================================
    errors = {}
    ErrorCallbacks = {}
    for name in ['OK',
                 'OK_NO_UPDATE_NECESSARY',
                 'WARN_BAD_FILENAME',
                 'WARN_LO_MISMATCH',
                 'ERROR_FILE_WRITE_FAIL',
                 'ERROR_FILE_DELETE_FAIL',
                 'ERROR_FILE_NOT_UTF8',
                 'ERROR_FILE_NOT_FOUND',
				 'ERROR_FILE_RENAME_FAIL',
                 'ERROR_TIMESTAMP_READ_FAIL',
                 'ERROR_TIMESTAMP_WRITE_FAIL',
                 'ERROR_PARSE_FAIL',
                 'ERROR_CONDITION_EVAL_FAIL',
                 'ERROR_NO_MEM',
                 'ERROR_INVALID_ARGS',
                 'ERROR_NETWORK_FAIL',
                 'ERROR_NO_INTERNET_CONNECTION',
                 'ERROR_NO_TAG_MAP',
                 'ERROR_PLUGINS_FULL',
                 'ERROR_GAME_NOT_FOUND',
                 'ERROR_REGEX_EVAL_FAIL',
                 ]:
        name = 'BOSS_API_'+name
        errors[name] = c_uint.in_dll(BAPI,name).value
        ErrorCallbacks[errors[name]] = None
    BOSS_API_RETURN_MAX = c_uint.in_dll(BAPI,'BOSS_API_RETURN_MAX').value
    globals().update(errors)

    # =========================================================================
    # API Functions - Error Handling
    # =========================================================================
    ## uint32_t GetLastErrorDetails(const uint8_t **details)
    _CGetLastErrorDetails = BAPI.GetLastErrorDetails
    _CGetLastErrorDetails.restype = c_uint32
    _CGetLastErrorDetails.argtypes = [c_uint8_p_p]
    def GetLastErrorDetails():
        details = c_uint8_p()
        ret = _CGetLastErrorDetails(byref(details))
        if ret != BOSS_API_OK:
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
        if result in {BOSS_API_OK,BOSS_API_OK_NO_UPDATE_NECESSARY}: return result
        elif result in {BOSS_API_WARN_BAD_FILENAME,BOSS_API_WARN_LO_MISMATCH}:
            if DebugLevel > 0:
                print GetLastErrorDetails()
            return result
        elif DebugLevel > 1:
            print GetLastErrorDetails()
        raise BossError(result)

    # =========================================================================
    # API Functions - Version
    # =========================================================================
    ## uint32_t GetVersionString(const uint8_t **bossVersionStr)
    _CGetVersionString = BAPI.GetVersionString
    _CGetVersionString.restype = BossErrorCheck
    _CGetVersionString.argtypes = [c_uint8_p_p]
    global version
    version = c_uint8_p()
    try:
        _CGetVersionString(byref(version))
        version = _uni(version.value)
    except BossError as e:
        print u'Error getting BOSS API version:', e
        version = u'Error'

    # =========================================================================
    # API Functions - Lifecycle Management
    # =========================================================================
    ## uint32_t CreateBossDb(boss_db *db, const uint32_t clientGame, const uint8_t *dataPath)
    _CCreateBossDb = BAPI.CreateBossDb
    _CCreateBossDb.restype = BossErrorCheck
    _CCreateBossDb.argtypes = [boss_db_p, c_uint32, c_uint8_p]
    ## void DestroyBossDb(boss_db db)
    _CDestroyBossDb = BAPI.DestroyBossDb
    _CDestroyBossDb.restype = None
    _CDestroyBossDb.argtypes = [boss_db]

    # =========================================================================
    # API Functions - Database Loading
    # =========================================================================
    ## uint32_t Load(boss_db db, const uint8_t *masterlistPath, const uint8_t *userlistPath)
    _CLoad = BAPI.Load
    _CLoad.restype = BossErrorCheck
    _CLoad.argtypes = [boss_db, c_uint8_p, c_uint8_p]
    ## uint32_t EvalConditionals(boss_db db)
    _CEvalConditionals = BAPI.EvalConditionals
    _CEvalConditionals.restype = BossErrorCheck
    _CEvalConditionals.argtypes = [boss_db]

    # =========================================================================
    # API Functions - Masterlist Updating
    # =========================================================================
    ## uint32_t UpateMasterlist(boss_db, const uint8_t *masterlistPath)
    _CUpdateMasterlist = BAPI.UpdateMasterlist
    _CUpdateMasterlist.restype = BossErrorCheck
    _CUpdateMasterlist.argtypes = [boss_db, c_uint8_p]

    # =========================================================================
    # API Functions - Plugin Sorting
    # =========================================================================
    ## uint32_t GetLoadOrderMethod(boss_db db, uint32_t *method);
    _CGetLoadOrderMethod = BAPI.GetLoadOrderMethod
    _CGetLoadOrderMethod.restype = c_uint32
    _CGetLoadOrderMethod.argtypes = [boss_db, c_uint32_p]

    ## uint32_t SortMods(boss_db db, const bool trialOnly, uint8_t ***sortedPlugins, size_t *listLength, size_t *lastRecPos)
    _CSortMods = BAPI.SortMods
    _CSortMods.restype = BossErrorCheck
    _CSortMods.argtypes = [boss_db, c_bool, c_uint8_p_p_p, c_size_t_p, c_size_t_p]
    ## uint32_t GetLoadOrder(boss_db db, uint8_t ***plugins, size_t *numPlugins)
    _CGetLoadOrder = BAPI.GetLoadOrder
    _CGetLoadOrder.restype = BossErrorCheck
    _CGetLoadOrder.argtypes = [boss_db, c_uint8_p_p_p, c_size_t_p]
    ## uint32_t SetLoadOrder(boss_db db, uint8_t **plugins, const size_t numPlugins)
    _CSetLoadOrder = BAPI.SetLoadOrder
    _CSetLoadOrder.restype = BossErrorCheck
    _CSetLoadOrder.argtypes = [boss_db, c_uint8_p_p, c_size_t]
    ## uint32_t GetActivePlugins(boss_db db, uint8_t ***plugins, size_t *numPlugins)
    _CGetActivePlugins = BAPI.GetActivePlugins
    _CGetActivePlugins.restype = BossErrorCheck
    _CGetActivePlugins.argtypes = [boss_db, c_uint8_p_p_p, c_size_t_p]
    ## uint32_t SetActivePlugins(boss_db db, uint8_t **plugins, const size_t numPlugins)
    _CSetActivePlugins = BAPI.SetActivePlugins
    _CSetActivePlugins.restype = BossErrorCheck
    _CSetActivePlugins.argtypes = [boss_db, c_uint8_p_p, c_size_t]
    ## uint32_t GetPluginLoadOrder(boss_db db, const uint8_t *plugin, size_t *index)
    _CGetPluginLoadOrder = BAPI.GetPluginLoadOrder
    _CGetPluginLoadOrder.restype = BossErrorCheck
    _CGetPluginLoadOrder.argtypes = [boss_db, c_uint8_p, c_size_t_p]
    ## uint32_t SetPluginLoadOrder(boss_db db, const uint8_t *plugin, size_t index)
    _CSetPluginLoadOrder = BAPI.SetPluginLoadOrder
    _CSetPluginLoadOrder.restype = BossErrorCheck
    _CSetPluginLoadOrder.argtypes = [boss_db, c_uint8_p, c_size_t]
    ## uint32_t GetIndexedPlugin(boss_db db, const size_t index, uint8_t **plugin)
    _CGetIndexedPlugin = BAPI.GetIndexedPlugin
    _CGetIndexedPlugin.restype = BossErrorCheck
    _CGetIndexedPlugin.argtypes = [boss_db, c_size_t, c_uint8_p_p]
    ## uint32_t SetPluginActive(boss_db db, const uint8_t *plugin, const bool active)
    _CSetPluginActive = BAPI.SetPluginActive
    _CSetPluginActive.restype = BossErrorCheck
    _CSetPluginActive.argtypes = [boss_db, c_uint8_p, c_bool]
    ## uint32_t IsPluginActive(boss_db db, const uint8_t *plugin, bool *isActive)
    _CIsPluginActive = BAPI.IsPluginActive
    _CIsPluginActive.restype = BossErrorCheck
    _CIsPluginActive.argtypes = [boss_db, c_uint8_p, c_bool_p]

    # =========================================================================
    # API Functions - Database Access
    # =========================================================================
    ## uint32_t GetBashTagMap(boss_db db, BashTag **tagMap, size_t *numTags)
    _CGetBashTagMap = BAPI.GetBashTagMap
    _CGetBashTagMap.restype = BossErrorCheck
    _CGetBashTagMap.argtypes = [boss_db, BashTag_p_p, c_size_t_p]
    ## uint32_t GetModBashTags(boss_db db, const uint8_t *plugin, uint32_t **tagIds_added, size_t *numTags_added, uint32_t **tagIds_removed, size_t *numTags_removed, bool *userlistModified)
    _CGetModBashTags = BAPI.GetModBashTags
    _CGetModBashTags.restype = BossErrorCheck
    _CGetModBashTags.argtypes = [boss_db, c_uint8_p, c_uint32_p_p, c_size_t_p, c_uint32_p_p, c_size_t_p, c_bool_p]
    ## uint32_t GetDirtyMessage(boss_db db, const uint8_t *plugin, uint8_t **message, uint32_t *needsCleaning)
    _CGetDirtyMessage = BAPI.GetDirtyMessage
    _CGetDirtyMessage.restype = BossErrorCheck
    _CGetDirtyMessage.argtypes = [boss_db, c_uint8_p, c_uint8_p_p, c_uint32_p]
    ## uint32_t DumpMinimal(boss_db db, const uint8_t *file, const bool overwrite)
    _CDumpMinimal = BAPI.DumpMinimal
    _CDumpMinimal.restype = BossErrorCheck
    _CDumpMinimal.argtypes = [boss_db, c_uint8_p, c_bool]

    # =========================================================================
    # Class Wrapper
    # =========================================================================
    class BossDb(object):
        def __init__(self,gamePath,game='Oblivion'):
            """ game can be one of the BOSS_API_GAME_*** codes, or one of the
                aliases defined above in the 'games' dictionary."""
            if isinstance(game,basestring):
                if game in games:
                    game = games[game]
                else:
                    raise Exception('Game "%s" is not recognized' % game)
            self.tags = {}   # BashTag map
            self._DB = boss_db()
            _CCreateBossDb(byref(self._DB),game,_enc(gamePath))
            # Get Load Order Method
            method = c_uint32()
            _CGetLoadOrderMethod(self._DB,byref(method))
            self._LOMethod = method.value

        @property
        def LoadOrderMethod(self): return self._LOMethod

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
            _CEvalConditionals(self._DB)
            self._GetBashTags()

        def EvalConditionals(self):
            _CEvalConditionals(self._DB)
            self._GetBashTags()

        def _GetBashTags(self):
            num = c_size_t()
            bashTags = BashTag_p()
            _CGetBashTagMap(self._DB, byref(bashTags), byref(num))
            self.tags = {bashTags[i].id:_uni(bashTags[i].name)
                         for i in xrange(num.value)}

        # ---------------------------------------------------------------------
        # Load Order management
        # ---------------------------------------------------------------------
        class LoadOrderList(list):
            """list-like object for manipulating load order"""
            def SetBossDb(self,db):
                self._DB = db # BossDb python class, not boss_db pointer

            # Block the following 'list' functions, since they don't make sense
            # for use with the BOSS API and Load Order
            ## LoadOrder[i] = x
            def __setitem__(self,key,value): raise Exception('BossDb.LoadOrder does not support item setting')
            ## del LoadOrder[i]
            def __delitem__(self,key): raise Exception('BossDb.LoadOrder does not support item deletion')
            ## LoadOrder += [s,3,5]
            ##  and other compound assignment operators
            def __iadd__(self,other): raise Exception('BossDb.LoadOrder does not support compound assignment')
            def __isub__(self,other): raise Exception('BossDb.LoadOrder does not support compound assignment')
            def __imul__(self,other): raise Exception('BossDb.LoadOrder does not support compound assignment')
            def __idiv__(self,other): raise Exception('BossDb.LoadOrder does not support compound assignment')
            def __itruediv__(self,other): raise Exception('BossDb.LoadOrder does not support compound assignment')
            def __ifloordiv__(self,other): raise Exception('BossDb.LoadOrder does not support compound assignment')
            def __imod__(self,other): raise Exception('BossDb.LoadOrder does not support compound assignment')
            def __ipow__(self,other): raise Exception('BossDb.LoadOrder does not support compound assignment')
            def __ilshift__(self,other): raise Exception('BossDb.LoadOrder does not support compound assignment')
            def __irshift__(self,other): raise Exception('BossDb.LoadOrder does not support compound assignment')
            def __iand__(self,other): raise Exception('BossDb.LoadOrder does not support compound assignment')
            def __ixor__(self,other): raise Exception('BossDb.LoadOrder does not support compound assignment')
            def __ior__(self,other): raise Exception('BossDb.LoadOrder does not support compound assignment')
            ## LoadOrder.append('ahalal')
            def append(self,item): raise Exception('BossDb.LoadOrder does not support append.')
            ## LoadOrder.extend(['kkjjhk','kjhaskjd'])
            def extend(self,items): raise Exception('BossDb.LoadOrder does not support extend.')
            def remove(self,item): raise Exception('BossDb.LoadOrder does not support remove.')
            def pop(self,item): raise Exception('BossDb.LoadOrder does not support pop.')
            ## TODO: Possibly make this call BOSS's auto-sorting
            def sort(self,*args,**kwdargs): raise Exception('BossDb.LoadOrder does not support sort.')
            def reverse(self,*args,**kwdargs): raise Exception('BossDb.LoadOrder does not support reverse.')

            # Override the following with custom functions
            def insert(self,i,x):
                # Change Load Order of single plugin
                self._DB.SetPluginLoadOrder(x, i)
            def index(self,x):
                # Get Load Order of single plugin
                return self._DB.GetPluginLoadOrder(x)
            def count(self,x):
                # 1 if the plugin is in the Load Order, 0 otherwise
                # (plugins can't be in the load order multiple times)
                return 1 if x in self else 0

        def GetLoadOrder(self):
            plugins = c_uint8_p_p()
            num = c_size_t()
            _CGetLoadOrder(self._DB, byref(plugins), byref(num))
            return [GPath(_uni(plugins[i])) for i in xrange(num.value)]
        def _GetLoadOrder(self):
            ret = self.LoadOrderList(self.GetLoadOrder())
            ret.SetBossDb(self)
            return ret
        def SetLoadOrder(self, plugins):
            plugins = [_enc(x) for x in plugins]
            num = len(plugins)
            plugins = list_of_strings(plugins)
            _CSetLoadOrder(self._DB, plugins, num)
        LoadOrder = property(_GetLoadOrder,SetLoadOrder)

        def SortMods(self,trialOnly=False):
            plugins = c_uint8_p_p()
            num = c_size_t()
            lastRec = c_size_t()
            _CSortMods(self._DB,byref(plugins),byref(num),byref(lastRec))
            return [GPath(_uni(plugins[i])) for i in xrange(num.value)]

        def GetPluginLoadOrder(self, plugin):
            plugin = _enc(plugin)
            index = c_size_t()
            _CGetPluginLoadOrder(self._DB,plugin,byref(index))
            return index.value

        def SetPluginLoadOrder(self, plugin, index):
            plugin = _enc(plugin)
            _CSetPluginLoadOrder(self._DB,plugin,index)

        def GetIndexedPlugin(self, index):
            plugin = c_uint8_p()
            _CGetIndexedPlugin(self._DB,index,byref(plugin))
            return GPath(_uni(plugin.value))

        # ---------------------------------------------------------------------
        # Active plugin management
        # ---------------------------------------------------------------------
        class ActivePluginsList(list):
            """list-like object for modiying which plugins are active.
               Currently, you cannot change the Load Order through this
               object, perhaps in the future."""
            def SetBossDb(self,db):
                self._DB = db

            def ReSync(self):
                """Resync's contents with the BOSS API"""
                list.__setslice__(self,0,len(self),self._DB.ActivePlugins)

            # Block the following 'list' functions, since they don't make sense
            # for use with the BOSS API and Active Plugins
            ## ActivePlugins[i] = x
            def __setitem__(self,key,value): raise Exception('BossDb.ActivePlugins does not support item setting')
            ## LoadOrder *= 3
            ##  and other compound assignment operators
            def __imul__(self,other): raise Exception('BossDb.ActivePlugins does not support compound assignment')
            def __idiv__(self,other): raise Exception('BossDb.ActivePlugins does not support compound assignment')
            def __itruediv__(self,other): raise Exception('BossDb.ActivePlugins does not support compound assignment')
            def __ifloordiv__(self,other): raise Exception('BossDb.ActivePlugins does not support compound assignment')
            def __imod__(self,other): raise Exception('BossDb.ActivePlugins does not support compound assignment')
            def __ipow__(self,other): raise Exception('BossDb.ActivePlugins does not support compound assignment')
            def __ilshift__(self,other): raise Exception('BossDb.ActivePlugins does not support compound assignment')
            def __irshift__(self,other): raise Exception('BossDb.ActivePlugins does not support compound assignment')
            def __iand__(self,other): raise Exception('BossDb.ActivePlugins does not support compound assignment')
            def __ixor__(self,other): raise Exception('BossDb.ActivePlugins does not support compound assignment')
            def __ior__(self,other): raise Exception('BossDb.ActivePlugins does not support compound assignment')
            def pop(self,item): raise Exception('BossDb.ActivePlugins does not support pop.')
            def sort(self,*args,**kwdargs): raise Exception('BossDb.ActivePlugins does not support sort.')
            def reverse(self,*args,**kwdargs): raise Exception('BossDb.ActivePlugins does not support reverse.')


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

            ## ActivePlugins.count('test.esp')
            def count(self,item):
                return 1 if item in self else 0

        def GetActivePlugins(self):
            plugins = c_uint8_p_p()
            num = c_size_t()
            try:
                _CGetActivePlugins(self._DB, byref(plugins), byref(num))
            except BossError as e:
                if e.code == BOSS_API_ERROR_FILE_NOT_FOUND:
                    self.SetActivePlugins([])
                    _CGetActivePlugins(self._DB, byref(plugins), byref(num))
                else:
                    raise
            return [GPath(_uni(plugins[i])) for i in xrange(num.value)]
        def _GetActivePlugins(self):
            ret = self.ActivePluginsList(self.GetActivePlugins())
            ret.SetBossDb(self)
            return ret
        def SetActivePlugins(self,plugins):
            plugins = [_enc(x) for x in plugins]
            num = len(plugins)
            plugins = list_of_strings(plugins)
            _CSetActivePlugins(self._DB, plugins, num)
        ActivePlugins = property(_GetActivePlugins,SetActivePlugins)

        def SetPluginActive(self,plugin,active=True):
            _CSetPluginActive(self._DB,_enc(plugin),active)

        def IsPluginActive(self,plugin):
            active = c_bool()
            _CIsPluginActive(self._DB,_enc(plugin),byref(active))
            return active.value

        # ---------------------------------------------------------------------
        # DB Access
        # ---------------------------------------------------------------------
        def GetModBashTags(self,plugin):
            tagIds_added = c_uint32_p()
            numAdded = c_size_t()
            tagIds_removed = c_uint32_p()
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
            message = c_uint8_p()
            clean = c_uint32()
            _CGetDirtyMessage(self._DB,_enc(plugin),byref(message),byref(clean))
            return (_uni(message.value),clean.value)
            
        def DumpMinimal(self,file,overwrite):
            _CDumpMinimal(self._DB,_enc(file),overwrite)

        # ---------------------------------------------------------------------
        # Utility Functions (not added by the API, pure Python)
        # ---------------------------------------------------------------------
        def FilterActive(self,plugins,active=True):
            """Given a list of plugins, returns the subset of that list,
               consisting of:
                - only active plugins if 'active' is True
                - only inactive plugins if 'active' is False"""
            return [x for x in plugins if self.IsPluginActive(x)]

        def FilterDirty(self,plugins,cleanCode=BOSS_API_CLEAN_YES):
            """Given a list of plugins, returns the subset of that list,
               consisting of plugins that meet the given BOSS_API_CLEAN_*
               code"""
            return [x for x in plugins if self.GetDirtyMessage(x)[1] == cleanCode]

        def DeactivatePlugins(self,plugins):
            for plugin in plugins:
                self.SetPluginActive(plugin,False)

        def GetOrdered(self,plugins):
            """Returns a list of the given plugins, sorted accoring to their
               load order"""
            return [x for x in self.LoadOrder if x in plugins]

    # Put the locally defined functions, classes, etc into the module global namespace
    globals().update(locals())

# Initialize BAPI, assuming that boss32.dll and boss64.dll are in the same directory
# Call Init again with the path to these dll's if this assumption is incorrect.
# BAPI will be None if this is the case.
try:
    Init(os.getcwdu())
except BossVersionError:
    pass
