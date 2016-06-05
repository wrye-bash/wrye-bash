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
"""Thin python wrapper around libbsa.

To use outside of Bash replace the Bash imports below with:
class Path: pass
def GPath(x): return u'' if x is None else unicode(x, 'utf8')
"""
from ctypes import *
import os
import platform
from bolt import Path, GPath

_libbsa = None
version = None
BSAHandle, LibbsaError = None, None

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
    """Call to reload libbsa, pointing to a different path to the dll."""

    # If path is a directory, auto choose DLL based on platform
    if os.path.isdir(path):
        if '64bit' in platform.architecture():
            path = os.path.join(path,u'libbsa64.dll')
        else:
            path = os.path.join(path,u'libbsa32.dll')

    global _libbsa, BSAHandle, LibbsaError

    # First unload any libbsa dll previously loaded
    del _libbsa, BSAHandle, LibbsaError
    _libbsa = None

    if not os.path.exists(path):
        BSAHandle, LibbsaError = None, None
        return

    try:
        # CDLL doesn't play with unicode path strings nicely on windows :(
        # Use this workaround
        handle = None
        if isinstance(path,unicode) and os.name in ('nt','ce'):
            LoadLibrary = windll.kernel32.LoadLibraryW
            handle = LoadLibrary(path)
        _libbsa = CDLL(path, handle=handle)
    except Exception as e:
        _libbsa = BSAHandle = LibbsaError = None
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

    # helpers
    def _uint(const): return c_uint.in_dll(_libbsa, const).value

    # utility unicode functions
    def _enc(x): return (x.encode('utf8') if isinstance(x,unicode)
                         else x.s.encode('utf8') if isinstance(x,Path)
                         else x)

    # =========================================================================
    # API Functions - Version
    # =========================================================================
    ## bool bsa_is_compatible(const unsigned int versionMajor,
    #                         const unsigned int versionMinor,
    #                         const unsigned int versionPatch)
    _Cbsa_is_compatible = _libbsa.bsa_is_compatible
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
            _libbsa.bsa_get_version(byref(verMajor), byref(verMinor), byref(verPatch))
        except:
            raise LibbsaVersionError(
                'libbsa.py is not compatible with the specified libbsa DLL ('
                '%i.%i.%i).' % verMajor % verMinor % verPatch)

    # =========================================================================
    # API Constants - BSA Version Flags
    # =========================================================================
    LIBBSA_VERSION_TES3 = _uint('LIBBSA_VERSION_TES3')
    LIBBSA_VERSION_TES4 = _uint('LIBBSA_VERSION_TES4')
    LIBBSA_VERSION_TES5 = _uint('LIBBSA_VERSION_TES5')
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
    LIBBSA_COMPRESS_LEVEL_0 = _uint('LIBBSA_COMPRESS_LEVEL_0')
    LIBBSA_COMPRESS_LEVEL_1 = _uint('LIBBSA_COMPRESS_LEVEL_1')
    LIBBSA_COMPRESS_LEVEL_2 = _uint('LIBBSA_COMPRESS_LEVEL_2')
    LIBBSA_COMPRESS_LEVEL_3 = _uint('LIBBSA_COMPRESS_LEVEL_3')
    LIBBSA_COMPRESS_LEVEL_4 = _uint('LIBBSA_COMPRESS_LEVEL_4')
    LIBBSA_COMPRESS_LEVEL_5 = _uint('LIBBSA_COMPRESS_LEVEL_5')
    LIBBSA_COMPRESS_LEVEL_6 = _uint('LIBBSA_COMPRESS_LEVEL_6')
    LIBBSA_COMPRESS_LEVEL_7 = _uint('LIBBSA_COMPRESS_LEVEL_7')
    LIBBSA_COMPRESS_LEVEL_8 = _uint('LIBBSA_COMPRESS_LEVEL_8')
    LIBBSA_COMPRESS_LEVEL_9 = _uint('LIBBSA_COMPRESS_LEVEL_9')

    # =========================================================================
    # API Constants - Return codes
    # =========================================================================
    LIBBSA_OK = _uint('LIBBSA_OK')
    LIBBSA_ERROR_INVALID_ARGS = _uint('LIBBSA_ERROR_INVALID_ARGS')
    LIBBSA_ERROR_NO_MEM = _uint('LIBBSA_ERROR_NO_MEM')
    LIBBSA_ERROR_FILESYSTEM_ERROR = _uint('LIBBSA_ERROR_FILESYSTEM_ERROR')
    LIBBSA_ERROR_BAD_STRING = _uint('LIBBSA_ERROR_BAD_STRING')
    LIBBSA_ERROR_ZLIB_ERROR = _uint('LIBBSA_ERROR_ZLIB_ERROR')
    LIBBSA_ERROR_PARSE_FAIL = _uint('LIBBSA_ERROR_PARSE_FAIL')
    errors = dict((name, value) for name, value in locals().iteritems() if
                  name.startswith('LIBBSA_ERROR_'))
    LIBBSA_RETURN_MAX = _uint('LIBBSA_RETURN_MAX')

    # =========================================================================
    # API Functions - Error Handling
    # =========================================================================
    ## unsigned int bsa_get_error_message(const uint8_t ** const details)
    _Cbsa_get_error_message = _libbsa.bsa_get_error_message
    _Cbsa_get_error_message.restype = c_uint
    _Cbsa_get_error_message.argtypes = [c_char_p_p]
    def GetLastErrorDetails():
        details = c_char_p()
        ret = _Cbsa_get_error_message(byref(details))
        if ret != LIBBSA_OK:
            raise Exception(u'An error occurred while getting the details of a libbsa error: %i' % ret)
        return unicode(details.value if details.value else 'None', 'utf8')

    class LibbsaError(Exception):
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

        def __repr__(self): return '<LibbsaError: %r>' % self.msg
        def __str__(self): return 'LibbsaError: %s' % self.msg

    def LibbsaErrorCheck(result):
        if result == LIBBSA_OK: return result
        elif DebugLevel > 0:
            print GetLastErrorDetails()
        raise LibbsaError(result)

    # =========================================================================
    # API Functions - Version
    # =========================================================================
    ## unsigned int bsa_get_version(unsigned int * const versionMajor,
    #                               unsigned int * const versionMinor,
    #                               unsigned int * const versionPatch)
    _Cbsa_get_version = _libbsa.bsa_get_version
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
    _Cbsa_open = _libbsa.bsa_open
    _Cbsa_open.restype = LibbsaErrorCheck
    _Cbsa_open.argtypes = [bsa_handle_p, c_char_p]
    ## unsigned int bsa_save(bsa_handle bh, const char * const path,
    #                        const unsigned int flags)
    _Cbsa_save = _libbsa.bsa_save
    _Cbsa_save.restype = LibbsaErrorCheck
    _Cbsa_save.argtypes = [bsa_handle, c_char_p, c_uint]
    ## void bsa_close(bsa_handle bh)
    _Cbsa_close = _libbsa.bsa_close
    _Cbsa_close.restype = None
    _Cbsa_close.argtypes = [bsa_handle]

    # =========================================================================
    # API Functions - Content Reading
    # =========================================================================
    ## unsigned int bsa_get_assets(bsa_handle bh,
    #                              const char * const contentPath,
    #                              char *** const assetPaths,
    #                              size_t * const numAssets)
    _Cbsa_get_assets = _libbsa.bsa_get_assets
    _Cbsa_get_assets.restype = LibbsaErrorCheck
    _Cbsa_get_assets.argtypes = [bsa_handle, c_char_p, c_char_p_p_p, c_size_t_p]
    ## unsigned int bsa_contains_asset(bsa_handle bh,
    #                                  const char * const assetPath,
    #                                  bool * const result)
    _Cbsa_contains_asset = _libbsa.bsa_contains_asset
    _Cbsa_contains_asset.restype = LibbsaErrorCheck
    _Cbsa_contains_asset.argtypes = [bsa_handle, c_char_p, c_bool_p]

    # =========================================================================
    # API Functions - Content Writing
    # =========================================================================
    ## These functions are still being written in libbsa, no point wrapping
    # them yet.

    # =========================================================================
    # API Functions - Content Extraction
    # =========================================================================
    ## unsigned int bsa_extract_assets(bsa_handle bh,
    #                                  const char * const contentPath,
    #                                  const char * const destPath,
    #                                  char *** const assetPaths,
    #                                  size_t * const numAssets)
    _Cbsa_extract_assets = _libbsa.bsa_extract_assets
    _Cbsa_extract_assets.restype = LibbsaErrorCheck
    _Cbsa_extract_assets.argtypes = [bsa_handle, c_char_p, c_char_p,
                                     c_char_p_p_p, c_size_t_p, c_bool]
    ## unsigned int bsa_extract_asset(bsa_handle bh, const char * assetPath,
    #                                 const char * destPath)
    _Cbsa_extract_asset = _libbsa.bsa_extract_asset
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

        # ---------------------------------------------------------------------
        # Content Reading
        # ---------------------------------------------------------------------
        def GetAssets(self, contentPath):
            assets = c_char_p_p()
            num = c_size_t()
            _Cbsa_get_assets(self._handle, _enc(contentPath), byref(assets), byref(num))
            return map(GPath, assets[:num.value])

        def IsAssetInBSA(self, assetPath):
            result = c_bool()
            _Cbsa_contains_asset(self._handle, _enc(assetPath), byref(result))
            return result.value

        # ---------------------------------------------------------------------
        # Content Writing
        # ---------------------------------------------------------------------
        ## These functions don't have wrappers yet, so no OO interface for them

        # ---------------------------------------------------------------------
        # Content Extraction
        # ---------------------------------------------------------------------
        def ExtractAssets(self, contentPath, destPath):
            assets = c_char_p_p()
            num = c_size_t()
            _Cbsa_extract_assets(self._handle, _enc(contentPath), _enc(destPath), byref(assets), byref(num), True)
            return map(GPath, assets[:num.value])

        def ExtractAsset(self, assetPath, destPath):
            _Cbsa_extract_asset(self._handle, _enc(assetPath), _enc(destPath),
                                True)
