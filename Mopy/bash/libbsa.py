# -*- coding: utf-8 -*-
# Python wrapper around libbsa
# by WrinklyNinja, adapted from bapi.py by Jacob Lojewski (aka Lojack)

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
PythonLibbsaVersion = (1,0)

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
        libbsa = CDLL(path)
    except Exception as e:
        libbsa = None
        raise

    # Some types
    bsa_handle = c_void_p
    bsa_handle_p = POINTER(bsa_handle)
    c_uint32_p = POINTER(c_uint32)
    c_uint32_p_p = POINTER(c_uint32_p)
    c_bool_p = POINTER(c_bool)
    c_uint8_p = c_char_p
    c_uint8_p_p = POINTER(c_uint8_p)
    c_uint8_p_p_p = POINTER(c_uint8_p_p)
    c_size_t_p = POINTER(c_size_t)
    class bsa_asset(Structure):
        _fields_ = [('sourcePath',c_uint8_p),
                    ('destPath',c_uint8_p),
                    ]
    bsa_asset_p = POINTER(bsa_asset)
    bsa_asset_p_p = POINTER(bsa_asset_p)
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
    ## bool IsCompatibleVersion(const uint32_t versionMajor, const uint32_t versionMinor, const uint32_t versionPatch)
    _CIsCompatibleVersion = libbsa.IsCompatibleVersion
    _CIsCompatibleVersion.restype = c_bool
    _CIsCompatibleVersion.argtypes = [c_uint32, c_uint32, c_uint32]
    def IsCompatibleVersion(majorVersion, minorVersion, patchVersion=0):
        return True
        return _CIsCompatibleVersion(majorVersion,minorVersion,patchVersion)
    if not IsCompatibleVersion(*PythonLibbsaVersion):
        try:
            verMajor = c_uint32()
            verMinor = c_uint32()
            verPatch = c_uint32()
            libbsa.GetVersionNums(byref(verMajor), byref(verMinor), byref(verPatch))
            ver = _uni(ver.value)
        except:
            ver = ''
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
        LIBBSA_VERSION_TES4:LIBBSA_VERSION_TES4,
        'Fallout 3':LIBBSA_VERSION_TES5,
        LIBBSA_VERSION_TES5:LIBBSA_VERSION_TES5,
        'Fallout: New Vegas':LIBBSA_VERSION_TES5,
        LIBBSA_VERSION_TES5:LIBBSA_VERSION_TES5,
        'Nehrim':LIBBSA_VERSION_TES4,
        LIBBSA_VERSION_TES4:LIBBSA_VERSION_TES4,
        'Skyrim':LIBBSA_VERSION_TES5,
        LIBBSA_VERSION_TES5:LIBBSA_VERSION_TES5,
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
                 'ERROR_FILE_NOT_FOUND',
                 'ERROR_FILE_WRITE_FAIL',
                 'ERROR_FILE_READ_FAIL',
                 'ERROR_BAD_STRING',
                 'ERROR_ZLIB_ERROR',
                 ]:
        name = 'LIBBSA_'+name
        errors[name] = c_uint.in_dll(libbsa,name).value
        ErrorCallbacks[errors[name]] = None
    LIBBSA_RETURN_MAX = c_uint.in_dll(libbsa,'LIBBSA_RETURN_MAX').value
    globals().update(errors)

    # =========================================================================
    # API Functions - Error Handling
    # =========================================================================
    ## uint32_t GetLastErrorDetails(const uint8_t **details)
    _CGetLastErrorDetails = libbsa.GetLastErrorDetails
    _CGetLastErrorDetails.restype = c_uint32
    _CGetLastErrorDetails.argtypes = [c_uint8_p_p]
    def GetLastErrorDetails():
        details = c_uint8_p()
        ret = _CGetLastErrorDetails(byref(details))
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
    ## uint32_t GetVersionNums(uint32_t * versionMajor, uint32_t * versionMinor, uint32_t * versionPatch)
    _CGetVersionNums = libbsa.GetVersionNums
    _CGetVersionNums.argtypes = [c_uint32_p, c_uint32_p, c_uint32_p]
    global version
    version = c_uint8_p()
    try:
        verMajor = c_uint32()
        verMinor = c_uint32()
        verPatch = c_uint32()
        _CGetVersionNums(byref(verMajor),byref(verMinor),byref(verPatch))
        version = u'%i.%i.%i' % (verMajor.value,verMinor.value,verPatch.value)
    except LibbsaError as e:
        print u'Error getting libbsa version:', e
        version = u'Error'

    # =========================================================================
    # API Functions - Lifecycle Management
    # =========================================================================
    ## uint32_t OpenBSA(bsa_handle * bh, const uint8_t * path)
    _COpenBSA = libbsa.OpenBSA
    _COpenBSA.restype = LibbsaErrorCheck
    _COpenBSA.argtypes = [bsa_handle_p, c_uint8_p]
    ## uint32_t SaveBSA(bsa_handle bh, const uint8_t * path, const uint32_t flags)
    _CSaveBSA = libbsa.SaveBSA
    _CSaveBSA.restype = LibbsaErrorCheck
    _CSaveBSA.argtypes = [bsa_handle, c_uint8_p, c_uint32]
    ## void CloseBSA(bsa_handle bh)
    _CCloseBSA = libbsa.CloseBSA
    _CCloseBSA.restype = None
    _CCloseBSA.argtypes = [bsa_handle]

    # =========================================================================
    # API Functions - Content Reading
    # =========================================================================
    ## uint32_t GetAssets(bsa_handle bh, const uint8_t * contentPath, uint8_t *** assetPaths, size_t * numAssets)
    _CGetAssets = libbsa.GetAssets
    _CGetAssets.restype = LibbsaErrorCheck
    _CGetAssets.argtypes = [bsa_handle, c_uint8_p, c_uint8_p_p_p, c_size_t_p]
    ## uint32_t IsAssetInBSA(bsa_handle bh, const uint8_t * assetPath, bool * result)
    _CIsAssetInBSA = libbsa.IsAssetInBSA
    _CIsAssetInBSA.restype = LibbsaErrorCheck
    _CIsAssetInBSA.argtypes = [bsa_handle, c_uint8_p, c_bool_p]

    # =========================================================================
    # API Functions - Content Writing
    # =========================================================================
    ## These functions are still being written in libbsa, no point wrapping them yet.

    # =========================================================================
    # API Functions - Content Extraction
    # =========================================================================
    ## uint32_t ExtractAssets(bsa_handle bh, const uint8_t * contentPath, const uint8_t * destPath, uint8_t *** assetPaths, size_t * numAssets)
    _CExtractAssets = libbsa.ExtractAssets
    _CExtractAssets.restype = LibbsaErrorCheck
    _CExtractAssets.argtypes = [bsa_handle, c_uint8_p, c_uint8_p, c_uint8_p_p_p, c_size_t_p, c_bool]
    ## uint32_t ExtractAsset(bsa_handle bh, const uint8_t * assetPath, const uint8_t * destPath)
    _CExtractAsset = libbsa.ExtractAsset
    _CExtractAsset.restype = LibbsaErrorCheck
    _CExtractAsset.argtypes = [bsa_handle, c_uint8_p, c_uint8_p, c_bool]

    # =========================================================================
    # Class Wrapper
    # =========================================================================
    class BSAHandle(object):
        def __init__(self,path):
            self._handle = bsa_handle()
            _COpenBSA(byref(self._handle),_enc(path))

        def __del__(self):
            if self._handle is not None:
                _CCloseBSA(self._handle)
                self._handle = None

        # 'with' statement
        def __enter__(self): return self
        def __exit__(self,exc_type,exc_value,traceback): self.__del__()

        # ---------------------------------------------------------------------
        # Content Reading
        # ---------------------------------------------------------------------
        def GetAssets(self, contentPath):
            assets = c_uint8_p_p()
            num = c_size_t()
            _CGetAssets(self._handle, _enc(contentPath), byref(assets), byref(num))
            return [GPath(_uni(assets[i])) for i in xrange(num.value)]

        def IsAssetInBSA(self, assetPath):
            result = c_bool()
            _CIsAssetInBSA(self._handle, _enc(assetPath), byref(result))
            return result.value

        # ---------------------------------------------------------------------
        # Content Writing
        # ---------------------------------------------------------------------
        ## These functions don't have wrappers yet, so no OO interface for them.

        # ---------------------------------------------------------------------
        # Content Extraction
        # ---------------------------------------------------------------------
        def ExtractAssets(self, contentPath, destPath):
            assets = c_uint8_p_p()
            num = c_size_t()
            _CExtractAssets(self._handle, _enc(contentPath), _enc(destPath), byref(assets), byref(num), True)
            return [GPath(_uni(assets[i])) for i in xrange(num.value)]

        def ExtractAsset(self, assetPath, destPath):
            _CExtractAsset(self._handle, _enc(assetPath), _enc(destPath), True)

    # Put the locally defined functions, classes, etc into the module global namespace
    globals().update(locals())

# Initialize libbsa, assuming that libbsa32.dll and libbsa64.dll are in the same directory
# Call Init again with the path to these dll's if this assumption is incorrect.
# libbsa will be None if this is the case.
try:
    Init(os.getcwdu())
except LibbsaVersionError:
    pass
