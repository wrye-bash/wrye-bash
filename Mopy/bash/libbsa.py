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


"""Python wrapper around libbsa"""


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

libbsa = None
version = None

# Version of libbsa this Python script is written for.
PythonLibbsaVersion = (2,0)

DebugLevel = 0
# DebugLevel
#  Set this for more or less feedback
#  0 - (default) no additional feedback
#  1 - print information about all return codes found

class LibbsaVersionError(Exception):
    """Exception thrown if the libbsa loaded is not
       compatible with libbsa.py"""
    pass

def Init(path):
    """Called automatically by importing libbsa.  Can also be called manually
       by the user to reload libbsa, pointing to a different path to the dll.
   """

    # If path is a directory, auto choose DLL based on platform
    if os.path.isdir(path):
        if '64bit' in platform.architecture():
            path = os.path.join(path,u'libbsa64.dll')
        else:
            path = os.path.join(path,u'libbsa32.dll')

    global libbsa

    # First unload any libbsa dll previously loaded
    del libbsa
    libbsa = None

    if not os.path.exists(path):
        return

    try:
        # CDLL doesn't play with unicode path strings nicely on windows :(
        # Use this workaround
        handle = None
        if isinstance(path,unicode) and os.name in ('nt','ce'):
            LoadLibrary = windll.kernel32.LoadLibraryW
            handle = LoadLibrary(path)
        libbsa = CDLL(path,handle=handle)
    except Exception as e:
        libbsa = None
        raise

    # Some types
    bsa_handle = c_void_p
    bsa_handle_p = POINTER(bsa_handle)
    c_uint_p = POINTER(c_uint)
    c_uint_p_p = POINTER(c_uint_p)
    c_bool_p = POINTER(c_bool)
    c_char_p_p = POINTER(c_char_p)
    c_char_p_p_p = POINTER(c_char_p_p)
    c_size_t_p = POINTER(c_size_t)
    class bsa_asset(Structure):
        _fields_ = [('sourcePath',c_char_p),
                    ('destPath',c_char_p),
                    ]
    bsa_asset_p = POINTER(bsa_asset)
    bsa_asset_p_p = POINTER(bsa_asset_p)
    def list_of_strings(strings):
        lst = (c_char_p * len(strings))()
        lst = cast(lst,c_char_p_p)
        for i,string in enumerate(strings):
            lst[i] = cast(create_string_buffer(string),c_char_p)
        return lst

    # utility unicode functions
    def _uni(x): return u'' if x is None else unicode(x,'utf8')
    def _enc(x): return (x.encode('utf8') if isinstance(x,unicode)
                         else x.s.encode('utf8') if isinstance(x,Path)
                         else x)

    # =========================================================================
    # API Functions - Version
    # =========================================================================
    ## bool bsa_is_compatible(const unsigned int versionMajor, const unsigned int versionMinor, const unsigned int versionPatch)
    _Cbsa_is_compatible = libbsa.bsa_is_compatible
    _Cbsa_is_compatible.restype = c_bool
    _Cbsa_is_compatible.argtypes = [c_uint, c_uint, c_uint]
    def IsCompatibleVersion(majorVersion, minorVersion, patchVersion=0):
        return True
        return _Cbsa_is_compatible(majorVersion,minorVersion,patchVersion)
    if not IsCompatibleVersion(*PythonLibbsaVersion):
        verMajor = c_uint()
        verMinor = c_uint()
        verPatch = c_uint()
        try:
            libbsa.bsa_get_version(byref(verMajor), byref(verMinor), byref(verPatch))
        except:
            raise LibbsaVersionError('libbsa.py is not compatible with the specified libbsa DLL (%i.%i.%i).' % verMajor % verMinor % verPatch)

    # =========================================================================
    # API Constants - BSA Version Flags
    # =========================================================================
    LIBBSA_VERSION_TES3 = c_uint.in_dll(libbsa,'LIBBSA_VERSION_TES3').value
    LIBBSA_VERSION_TES4 = c_uint.in_dll(libbsa,'LIBBSA_VERSION_TES4').value
    LIBBSA_VERSION_TES5 = c_uint.in_dll(libbsa,'LIBBSA_VERSION_TES5').value
    games = {
        'Morrowind':LIBBSA_VERSION_TES3,
        LIBBSA_VERSION_TES3:LIBBSA_VERSION_TES3,
        'Oblivion':LIBBSA_VERSION_TES4,
        'Fallout3':LIBBSA_VERSION_TES5,
        LIBBSA_VERSION_TES5:LIBBSA_VERSION_TES5,
        'FalloutNV':LIBBSA_VERSION_TES5,
        'Nehrim':LIBBSA_VERSION_TES4,
        LIBBSA_VERSION_TES4:LIBBSA_VERSION_TES4,
        'Skyrim':LIBBSA_VERSION_TES5,
        }

    # =========================================================================
    # API Constants - Compression Flags
    # =========================================================================
    LIBBSA_COMPRESS_LEVEL_0 = c_uint.in_dll(libbsa,'LIBBSA_COMPRESS_LEVEL_0').value
    LIBBSA_COMPRESS_LEVEL_1 = c_uint.in_dll(libbsa,'LIBBSA_COMPRESS_LEVEL_1').value
    LIBBSA_COMPRESS_LEVEL_2 = c_uint.in_dll(libbsa,'LIBBSA_COMPRESS_LEVEL_2').value
    LIBBSA_COMPRESS_LEVEL_3 = c_uint.in_dll(libbsa,'LIBBSA_COMPRESS_LEVEL_3').value
    LIBBSA_COMPRESS_LEVEL_4 = c_uint.in_dll(libbsa,'LIBBSA_COMPRESS_LEVEL_4').value
    LIBBSA_COMPRESS_LEVEL_5 = c_uint.in_dll(libbsa,'LIBBSA_COMPRESS_LEVEL_5').value
    LIBBSA_COMPRESS_LEVEL_6 = c_uint.in_dll(libbsa,'LIBBSA_COMPRESS_LEVEL_6').value
    LIBBSA_COMPRESS_LEVEL_7 = c_uint.in_dll(libbsa,'LIBBSA_COMPRESS_LEVEL_7').value
    LIBBSA_COMPRESS_LEVEL_8 = c_uint.in_dll(libbsa,'LIBBSA_COMPRESS_LEVEL_8').value
    LIBBSA_COMPRESS_LEVEL_9 = c_uint.in_dll(libbsa,'LIBBSA_COMPRESS_LEVEL_9').value

    # =========================================================================
    # API Constants - Return codes
    # =========================================================================
    errors = {}
    ErrorCallbacks = {}
    for name in ['OK',
                 'ERROR_INVALID_ARGS',
                 'ERROR_NO_MEM',
                 'ERROR_FILESYSTEM_ERROR',
                 'ERROR_BAD_STRING',
                 'ERROR_ZLIB_ERROR',
                 'ERROR_PARSE_FAIL',
                 ]:
        name = 'LIBBSA_'+name
        errors[name] = c_uint.in_dll(libbsa,name).value
        ErrorCallbacks[errors[name]] = None
    LIBBSA_RETURN_MAX = c_uint.in_dll(libbsa,'LIBBSA_RETURN_MAX').value
    globals().update(errors)

    # =========================================================================
    # API Functions - Error Handling
    # =========================================================================
    ## unsigned int bsa_get_error_message(const uint8_t ** const details)
    _Cbsa_get_error_message = libbsa.bsa_get_error_message
    _Cbsa_get_error_message.restype = c_uint
    _Cbsa_get_error_message.argtypes = [c_char_p_p]
    def GetLastErrorDetails():
        details = c_char_p()
        ret = _Cbsa_get_error_message(byref(details))
        if ret != LIBBSA_OK:
            raise Exception(u'An error occurred while getting the details of a libbsa error: %i' % (ret))
        return unicode(details.value,'utf8')

    def RegisterCallback(errorCode,callback):
        """Used to setup callback functions for whenever specific error codes
           are encountered"""
        ErrorCallbacks[errorCode] = callback

    class LibbsaError(Exception):
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

        def __repr__(self): return '<LibbsaError: %s>' % self.msg
        def __str__(self): return 'LibbsaError: %s' % self.msg

    def LibbsaErrorCheck(result):
        callback = ErrorCallbacks.get(result,None)
        if callback: callback()
        if result == LIBBSA_OK: return result
        elif DebugLevel > 0:
            print GetLastErrorDetails()
        raise LibbsaError(result)

    # =========================================================================
    # API Functions - Version
    # =========================================================================
    ## unsigned int bsa_get_version(unsigned int * const versionMajor, unsigned int * const versionMinor, unsigned int * const versionPatch)
    _Cbsa_get_version = libbsa.bsa_get_version
    _Cbsa_get_version.argtypes = [c_uint_p, c_uint_p, c_uint_p]
    global version
    version = c_char_p()
    try:
        verMajor = c_uint()
        verMinor = c_uint()
        verPatch = c_uint()
        _Cbsa_get_version(byref(verMajor),byref(verMinor),byref(verPatch))
        version = u'%i.%i.%i' % (verMajor.value,verMinor.value,verPatch.value)
    except LibbsaError as e:
        print u'Error getting libbsa version:', e
        version = u'Error'

    # =========================================================================
    # API Functions - Lifecycle Management
    # =========================================================================
    ## unsigned int bsa_open(bsa_handle * bh, const char * const path)
    _Cbsa_open = libbsa.bsa_open
    _Cbsa_open.restype = LibbsaErrorCheck
    _Cbsa_open.argtypes = [bsa_handle_p, c_char_p]
    ## unsigned int bsa_save(bsa_handle bh, const char * const path, const unsigned int flags)
    _Cbsa_save = libbsa.bsa_save
    _Cbsa_save.restype = LibbsaErrorCheck
    _Cbsa_save.argtypes = [bsa_handle, c_char_p, c_uint]
    ## void bsa_close(bsa_handle bh)
    _Cbsa_close = libbsa.bsa_close
    _Cbsa_close.restype = None
    _Cbsa_close.argtypes = [bsa_handle]

    # =========================================================================
    # API Functions - Content Reading
    # =========================================================================
    ## unsigned int bsa_get_assets(bsa_handle bh, const char * const contentPath, char *** const assetPaths, size_t * const numAssets)
    _Cbsa_get_assets = libbsa.bsa_get_assets
    _Cbsa_get_assets.restype = LibbsaErrorCheck
    _Cbsa_get_assets.argtypes = [bsa_handle, c_char_p, c_char_p_p_p, c_size_t_p]
    ## unsigned int bsa_contains_asset(bsa_handle bh, const char * const assetPath, bool * const result)
    _Cbsa_contains_asset = libbsa.bsa_contains_asset
    _Cbsa_contains_asset.restype = LibbsaErrorCheck
    _Cbsa_contains_asset.argtypes = [bsa_handle, c_char_p, c_bool_p]

    # =========================================================================
    # API Functions - Content Writing
    # =========================================================================
    ## These functions are still being written in libbsa, no point wrapping them yet.

    # =========================================================================
    # API Functions - Content Extraction
    # =========================================================================
    ## unsigned int bsa_extract_assets(bsa_handle bh, const char * const contentPath, const char * const destPath, char *** const assetPaths, size_t * const numAssets)
    _Cbsa_extract_assets = libbsa.bsa_extract_assets
    _Cbsa_extract_assets.restype = LibbsaErrorCheck
    _Cbsa_extract_assets.argtypes = [bsa_handle, c_char_p, c_char_p, c_char_p_p_p, c_size_t_p, c_bool]
    ## unsigned int bsa_extract_asset(bsa_handle bh, const char * assetPath, const char * destPath)
    _Cbsa_extract_asset = libbsa.bsa_extract_asset
    _Cbsa_extract_asset.restype = LibbsaErrorCheck
    _Cbsa_extract_asset.argtypes = [bsa_handle, c_char_p, c_char_p, c_bool]

    # =========================================================================
    # Class Wrapper
    # =========================================================================
    class BSAHandle(object):
        def __init__(self,path):
            self._handle = bsa_handle()
            _Cbsa_open(byref(self._handle),_enc(path))

        def __del__(self):
            if self._handle is not None:
                _Cbsa_close(self._handle)
                self._handle = None

        # 'with' statement
        def __enter__(self): return self
        def __exit__(self,exc_type,exc_value,traceback): self.__del__()

        # ---------------------------------------------------------------------
        # Content Reading
        # ---------------------------------------------------------------------
        def GetAssets(self, contentPath):
            assets = c_char_p_p()
            num = c_size_t()
            _Cbsa_get_assets(self._handle, _enc(contentPath), byref(assets), byref(num))
            return [GPath(_uni(assets[i])) for i in xrange(num.value)]

        def IsAssetInBSA(self, assetPath):
            result = c_bool()
            _Cbsa_contains_asset(self._handle, _enc(assetPath), byref(result))
            return result.value

        # ---------------------------------------------------------------------
        # Content Writing
        # ---------------------------------------------------------------------
        ## These functions don't have wrappers yet, so no OO interface for them.

        # ---------------------------------------------------------------------
        # Content Extraction
        # ---------------------------------------------------------------------
        def ExtractAssets(self, contentPath, destPath):
            assets = c_char_p_p()
            num = c_size_t()
            _Cbsa_extract_assets(self._handle, _enc(contentPath), _enc(destPath), byref(assets), byref(num), True)
            return [GPath(_uni(assets[i])) for i in xrange(num.value)]

        def ExtractAsset(self, assetPath, destPath):
            _Cbsa_extract_asset(self._handle, _enc(assetPath), _enc(destPath), True)

    # Put the locally defined functions, classes, etc into the module global namespace
    globals().update(locals())

# Initialize libbsa, assuming that libbsa32.dll and libbsa64.dll are in the same directory
# Call Init again with the path to these dll's if this assumption is incorrect.
# libbsa will be None if this is the case.
try:
    Init(os.getcwdu())
except LibbsaVersionError:
    pass
