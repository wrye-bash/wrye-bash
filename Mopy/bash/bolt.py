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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from __future__ import annotations

import builtins
import collections
import copy
import datetime
import io
import os
import pickle
import platform
import re
import shutil
import stat
import struct
import subprocess
import sys
import textwrap
import traceback as _traceback
import webbrowser
from collections.abc import Callable, Iterable
from contextlib import contextmanager, redirect_stdout
from enum import Enum
from functools import partial
from itertools import chain
from keyword import iskeyword
from operator import attrgetter
from typing import ClassVar, Self, TypeVar, get_type_hints, overload, Iterator
from zlib import crc32

try:
    import chardet
except ImportError:
    chardet = None # We will raise an error on boot in bash._import_deps

try:
    from reflink import reflink, ReflinkImpossibleError
except ImportError:
    # Optional, no reflink copies will be possible if missing
    reflink = ReflinkImpossibleError = None

from . import exception
from .wbtemp import TempFile

# structure aliases, mainly introduced to reduce uses of 'pack' and 'unpack'
struct_pack = struct.pack
struct_unpack = struct.unpack
struct_error = struct.error
struct_calcsize = struct.calcsize

#-- To make commands executed with Popen hidden
startupinfo = None
os_name = os.name ##: usages probably belong to env
if os_name == u'nt':
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

# Typing ----------------------------------------------------------------------
K = TypeVar('K')
V = TypeVar('V')

# Unicode ---------------------------------------------------------------------
#--decode unicode strings
#  This is only useful when reading fields from mods, as the encoding is not
#  known.  For normal filesystem interaction, these functions are not needed
encodingOrder = (
    u'ascii',    # Plain old ASCII (0-127)
    u'gbk',      # GBK (simplified Chinese + some)
    u'cp932',    # Japanese
    u'cp949',    # Korean
    u'cp1252',   # English (extended ASCII)
    u'utf8',
    u'cp500',
    u'UTF-16LE',
)
if os_name == u'nt':
    encodingOrder += (u'mbcs',)

_encodingSwap = {
    # The encoding detector reports back some encodings that
    # are subsets of others.  Use the better encoding when
    # given the option
    # 'reported encoding':'actual encoding to use',
    u'GB2312': u'gbk',        # Simplified Chinese
    u'SHIFT_JIS': u'cp932',   # Japanese
    u'windows-1252': u'cp1252',
    u'windows-1251': u'cp1251',
    u'utf-8': u'utf8',
}

# Preferred encoding to use when decoding/encoding strings in plugin files
# None = auto
# setting it tries the specified encoding first
pluginEncoding = None

# Encodings that we can't use because Python doesn't even support them
_blocked_encodings = {u'EUC-TW'}

def getbestencoding(bitstream):
    """Tries to detect the encoding a bitstream was saved in.  Uses Mozilla's
       detection library to find the best match (heuristics)"""
    if not bitstream:
        # Default to UTF-8 if the stream we're given is empty and hence no
        # inference can be made (chardet returns None, which breaks when passed
        # to decode())
        return 'utf8', 1.0
    # If we're fed a really big stream, go through it 16 KB at a time so as to
    # not time out (really only here so we don't freeze on boot when we get
    # malformed data fed in, no bytestring we pass in under normal
    # circumstances is *this* large)
    if len(bitstream) > 16384:
        bitstream_view = io.BytesIO(bitstream)
        result = result_sentinel = {
            'encoding': None,
            'confidence': 0.0,
            'language': None,
        }
        while block := bitstream_view.read(16384):
            result = chardet.detect(block)
            # If we got a useful result out of chardet here, we're done and can
            # return it
            if result != result_sentinel:
                break
    else:
        result = chardet.detect(bitstream)
    encoding_, confidence = result[u'encoding'], result[u'confidence']
    encoding_ = _encodingSwap.get(encoding_,encoding_)
    return encoding_, confidence

def decoder(byte_str, encoding=None, avoidEncodings=()) -> str:
    """Decode a byte string to unicode, using heuristics on encoding."""
    if isinstance(byte_str, str) or byte_str is None: return byte_str
    # Try the user specified encoding first
    if encoding:
        # TODO(ut) monkey patch
        if encoding == u'cp65001':
            encoding = u'utf-8'
        try: return str(byte_str, encoding)
        except UnicodeDecodeError: pass
    # Try to detect the encoding next
    encoding, confidence = getbestencoding(byte_str)
    if encoding and confidence >= 0.55 and (
            encoding not in avoidEncodings or confidence == 1.0) and (
            encoding not in _blocked_encodings):
        try: return str(byte_str, encoding)
        except UnicodeDecodeError: pass
    # If even that fails, fall back to the old method, trial and error
    for encoding in encodingOrder:
        try: return str(byte_str, encoding)
        except UnicodeDecodeError: pass
    raise UnicodeDecodeError(u'Text could not be decoded using any method')

def encode(text_str, encodings=encodingOrder, firstEncoding=None,
           returnEncoding=False):
    """Encode unicode string to byte string, using heuristics on encoding."""
    if isinstance(text_str, bytes) or text_str is None:
        if returnEncoding: return text_str, None
        else: return text_str
    # Try user specified encoding
    if firstEncoding:
        try:
            text_str = text_str.encode(firstEncoding)
            if returnEncoding: return text_str, firstEncoding
            else: return text_str
        except UnicodeEncodeError:
            pass
    goodEncoding = None
    # Try the list of encodings in order
    for encoding in encodings:
        try:
            test_encoded = text_str.encode(encoding)
            detectedEncoding = getbestencoding(test_encoded)
            if detectedEncoding[0] == encoding:
                # This encoding also happens to be detected
                # By the encoding detector as the same thing,
                # which means use it!
                if returnEncoding: return test_encoded, encoding
                else: return test_encoded
            # The encoding detector didn't detect it, but
            # it works, so save it for later
            if not goodEncoding: goodEncoding = (test_encoded, encoding)
        except UnicodeEncodeError:
            pass
    # Non of the encodings also where detectable via the
    # detector, so use the first one that encoded without error
    if goodEncoding:
        if returnEncoding: return goodEncoding
        else: return goodEncoding[0]
    raise UnicodeEncodeError(f'Text could not be encoded using any of the '
                             f'following encodings: {encodings}')

def encode_complex_string(string_val: str, max_size: int | None = None,
        min_size: int | None = None,
        preferred_encoding: str | None = None) -> bytes:
    """Handles encoding of a string that must satisfy certain conditions. Any
    of the keyword arguments may be omitted, in which case they will simply not
    apply.

    :param string_val: The unicode string to encode.
    :param max_size: The maximum size (in bytes) of the encoded string. If the
        result of encoding string_val is longer than this, it will be
        truncated.
    :param min_size: The minimum size (in bytes) of the encoded string. If the
        result of encoding string_val is shorter than this, it will be
        right-padded with null bytes.
    :param preferred_encoding: The encoding to try first. Defaults to
        bolt.pluginEncoding.
    :return: The encoded string."""
    preferred_encoding = preferred_encoding or pluginEncoding
    bytes_val = encode(to_win_newlines(string_val.rstrip()),
        firstEncoding=preferred_encoding)
    if max_size is not None:
        bytes_val = bytes_val[:max_size]
    if min_size is not None and (num_nulls := min_size - len(bytes_val)) > 0:
        bytes_val += b'\x00' * num_nulls
    return bytes_val

def failsafe_underscore(s: str):
    """A version of _() that doesn't fail when gettext has not been set up yet.
    Use as "from bolt import failsafe_underscore as _".

    Used by e.g. ini_files, which has to be used very early during boot for
    correct case sensitivity handling in INIs, so the gettext translation
    function may not be set up yet."""
    try:
        return builtins._(s)
    except AttributeError:
        return s # We're being invoked very early in boot

class Tee:
    """Similar to the Unix utility tee, this class redirects writes etc. to two
    separate IO streams. The name comes from T-splitters (often called tees),
    which combine or divide streams of fluid.

    Note that it is currently pretty geared for its use case of handling the
    BashBugDump, e.g. it lacks methods for closing/reading/etc."""
    def __init__(self, stream_a, stream_b):
        self._stream_a = stream_a
        self._stream_b = stream_b

    def flush(self) -> None:
        self._stream_a.flush()
        self._stream_b.flush()

    def write(self, s: str) -> int:
        self._stream_a.write(s)
        return self._stream_b.write(s)

def to_unix_newlines(s: str) -> str:
    """Replaces non-Unix newlines in the specified string with Unix newlines.
    Handles both CR-LF (Windows) and pure CR (macOS)."""
    return s.replace('\r\n', '\n').replace('\r', '\n')

def to_win_newlines(s):
    """Converts LF (Unix) newlines to CR-LF (Windows) newlines."""
    return reUnixNewLine.sub('\r\n', s)

def remove_newlines(s: str) -> str:
    """Removes all newlines (whether they are in LF, CR-LF or CR form) from the
    specified string."""
    return to_unix_newlines(s).replace('\n', '')

# The current OS's path seperator, escaped for use in regexes
os_sep_re = re.escape(os.path.sep)

def conv_obj(o, conv_enc=u'utf-8', __list_types=frozenset((list, set, tuple))):
    """Converts an object containing bytestrings to an equivalent object that
    contains decoded versions of those bytestrings instead. Decoding is done
    by trying the specified encoding first, then falling back on the regular
    'guess and try' logic."""
    if isinstance(o, dict):
        new_dict = o.copy()
        new_dict.clear()
        new_dict.update(((conv_obj(k, conv_enc), conv_obj(v, conv_enc))
                         for k, v in o.items()))
        return new_dict
    elif type(o) in __list_types:
        return type(o)(conv_obj(e, conv_enc) for e in o)
    elif isinstance(o, bytes):
        return decoder(o, encoding=conv_enc)
    else:
        return o

def timestamp(): return datetime.datetime.now().strftime(u'%Y-%m-%d %H.%M.%S')

##: Keep an eye on https://github.com/python/cpython/issues/75930
def round_size(size_bytes):
    """Returns the specified size in bytes as a human-readable size string."""
    ##: Maybe offer an option to switch between KiB and KB?
    prefix_pt2 = u'B' # if bass.settings[...] else u'iB'
    size_bytes /= 1024 # Don't show bytes
    for prefix_pt1 in (u'K', u'M', u'G', u'T', u'P', u'E', u'Z', u'Y'):
        if size_bytes < 1024:
            # Show a single decimal digit, but never show trailing zeroes
            return f'{f"{size_bytes:.1f}".rstrip("0").rstrip(".")} ' \
                   f'{prefix_pt1 + prefix_pt2}'
        size_bytes /= 1024
    return _(u'<very large>') # ;)

# Decode/encode dicts
class SigToStr(dict):
    """Dict of decoded record signatures - will decode unknown keys."""
    __slots__ = ()

    def __missing__(self, key):
        try:
            return self.setdefault(key, key.decode('iso-8859-1'))
        except AttributeError:
            return key

_sig_to_str = SigToStr()
sig_to_str = _sig_to_str.__getitem__

class StrToSig(dict):
    """Dict of encoded record strings - will encode unknown keys in *ascii*."""
    __slots__ = ()

    def __missing__(self, key):
        return self.setdefault(key, key.encode('ascii'))

_str_to_sig = StrToSig()
str_to_sig = _str_to_sig.__getitem__

# Helpers ---------------------------------------------------------------------
def sortFiles(files, __split=os.path.split):
    """Utility function. Sorts files by directory, then file name."""
    return sorted(files, key=lambda x: __split(x.lower()))

def str_or_none(uni_str):
    return None if uni_str.lower() == u'none' else uni_str

def int_or_none(uni_str):
    try:
        return int(uni_str)
    except ValueError:
        return None

def int_or_zero(uni_str):
    try:
        return int(uni_str)
    except ValueError:
        return 0

def float_or_none(uni_str):
    try: ##: is this needed (elsewhere also?)?
        return Rounder(float(uni_str))
    except ValueError:
        return None

def combine_dicts(dict_a: dict[K, V], dict_b: dict[K, V],
        f: Callable[[V, V], V]) -> dict[K, V]:
    """Merge two dictionaries, but combine their values (as opposed to the
    last-added value overwriting all earlier values with the same key).

    :param dict_a: The first dict to merge.
    :param dict_b: The second dict to merge.
    :param f: A function taking one value from dict_a and one from dict_b and
        returning the combined result."""
    return {**dict_a, **dict_b,
            **{k: f(dict_a[k], dict_b[k]) for k in dict_a.keys() & dict_b}}

def reverse_dict(source_dict: dict[K, V]) -> dict[V, K]:
    """Create a dict that represents the reverse/inverse mapping of the
    specified dict. If a -> b in target_dict, then b -> a in the returned
    dict.

    Note that this is meant for 1-to-1 mappings - if you have two keys with the
    same value, you'll lose the first key! See reverse_dict_multi for a method
    that avoids this problem."""
    return {v: k for k, v in source_dict.items()}

def reverse_dict_multi(source_dict: dict[K, V]) -> dict[V, set[K]]:
    """Create a dict that represents the reverse/inverse mapping of the
    specified dict, with support for duplicate values in the source dict. See
    also reverse_dict for simple 1-to-1 mappings."""
    ret = {}
    for k, v in source_dict.items():
        ret.setdefault(v, set()).add(k)
    return ret

def flatten_multikey_dict(multikey_dict: dict[K | tuple[K, ...], V]) \
        -> dict[K, V]:
    """Create a flattened version of the specified multikey dict. A multikey
    dict is one where keys may be of type K or of type tuple[K, ...], where
    each tuple key is called a multikey - any key in this tuple can be used for
    accessing the associated value. Before such a dict can be used for regular
    lookups, however, it first needs to be fed into this method."""
    flattened_dict = {}
    for mk_index, mk_values in multikey_dict.items():
        if not isinstance(mk_index, tuple):
            mk_index = (mk_index,)
        for split_index in mk_index:
            if split_index in flattened_dict:
                raise SyntaxError(f"Invalid multikey dict: Duplicate key "
                                  f"'{split_index!r}'")
            flattened_dict[split_index] = mk_values
    return flattened_dict

def gen_enum_parser(enum_type: type[Enum]):
    """Create a dict that maps the values of the specified enum to the matching
    enum entries. Useful e.g. for when the enum's values represent information
    inside a file and you want to parse that information into enum entries."""
    return {e.value: e for e in enum_type.__members__.values()}

_not_cached = object()

# Still 2x faster on 3.12 - PY3.13: retest?
class fast_cached_property:
    """Similar to functools.cached_property, but ~2x faster because it lacks
    that decorator's runtime error checking."""
    def __init__(self, wrapped_func):
        self._wrapped_func = wrapped_func
        self._wrapped_attr = None # set later

    def __set_name__(self, owner, name):
        self._wrapped_attr = name

    def __get__(self, instance, owner=None):
        try:
            wrapped_val = instance.__dict__[self._wrapped_attr]
        except KeyError:
            wrapped_val = self._wrapped_func(instance)
            instance.__dict__[self._wrapped_attr] = wrapped_val
        return wrapped_val

class classproperty:
    """Defines a property on the class rather than an instance. Does not
    support writing to the property though."""
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, obj, owner):
        return self.fget(owner)

# JSON parsing ----------------------------------------------------------------
class JsonParsable:
    """Base class for classes that will be parsed from JSON based on their type
    annotations and a special '_parsers' class var (see below). Call
    parse_single or parse_many to create instances.

    Note: this *MUST* be used together with @dataclass!"""
    # Specifies special handling for any number of attributes in the parsed
    # JSON dict. Each 'parser' is a function taking the JSON dict and the
    # attribute being parsed and returning the parsed object
    _parsers: dict[str, callable] = {}
    __slots__ = ()

    def __init__(self, **_kwargs): # To make PyCharm shut up
        super().__init__()

    @classmethod
    def parse_single(cls, json_dict: dict) -> Self:
        """Parses an instance of this JSON parsable from the specified
        JSON-sourced dict."""
        if json_dict is None:
            return None # Handle optional parsables
        inst_args = {}
        for cls_attr, cls_type_str in cls.__annotations__.items():
            attr_parser = cls._parsers.get(cls_attr)
            if attr_parser is None:
                # No special parser, access JSON dict directly
                parsed_obj = json_dict[cls_attr]
            else:
                parsed_obj = attr_parser(json_dict, cls_attr)
            inst_args[cls_attr] = parsed_obj
        return cls(**inst_args)

    @classmethod
    def parse_many(cls, json_list: list[dict]) -> list[Self]:
        """Parses multiple instances of this JSON parsable from the specified
        JSON-sourced list of dicts."""
        return [cls.parse_single(d) for d in json_list]

def json_remap(remap_attr: str):
    """Simple JSON parser that uses a different attribute for accessing the
    JSON dict. Used to avoid bad names (e.g. name) and builtins (e.g. id)."""
    def _remap_func(json_dict, _cls_attr):
        return json_dict[remap_attr]
    return _remap_func

# LowStrings ------------------------------------------------------------------
class CIstr(str):
    """See: http://stackoverflow.com/q/43122096/281545"""
    __slots__ = ()

    #--Hash/Compare
    def __hash__(self):
        return hash(self.lower())
    def __eq__(self, other):
        if isinstance(other, CIstr):
            return self.lower() == other.lower()
        return NotImplemented
    def __ne__(self, other):
        if isinstance(other, CIstr):
            return self.lower() != other.lower()
        return NotImplemented
    def __lt__(self, other):
        if isinstance(other, CIstr):
            return self.lower() < other.lower()
        return NotImplemented
    def __ge__(self, other):
        if isinstance(other, CIstr):
            return self.lower() >= other.lower()
        return NotImplemented
    def __gt__(self, other):
        if isinstance(other, CIstr):
            return self.lower() > other.lower()
        return NotImplemented
    def __le__(self, other):
        if isinstance(other, CIstr):
            return self.lower() <= other.lower()
        return NotImplemented
    #--repr
    def __repr__(self):
        return f'{type(self).__name__}({super(CIstr, self).__repr__()})'

class FName(str):
    """Class modeling the case insensitive key in data stores, usually a
    filename. It only accepts an instance of type str in its constructor.
    FName is-a str as it is being used mostly as a plain str instance, apart
    from comparisons. It compares case insensitive with both FName and str
    which has a catch: classes that compare with str will compare with FName,
    while FName won't compare with those. Special code was added to bolt.Path
    for that purpose, but there is no way to make this work with types in the
    wild. Note:
      - currently we triple storage for each string (self, cache key and
      fn_body). Apart from bsas code fn_body appears rarely
      - we added no other special methods like __add__ or slice operations
      to return FName - too much magic
      - pickling: eventually we want to pickle strings as string type and
      convert to internal format on load. Reason: backwards and forward
      compatibility. Of course on unpickling we must ensure __new__ is called.
      - __slots__ is not an option for variable length builtin overrides,
      keep an eye for that.
    """
    _filenames_cache: dict[str, FName] = {}
    _hash: int # Lazily cached since it's needed so often

    def __new__(cls, unicode_str: None | FName | str, *args,
                __cache=_filenames_cache, **kwargs):
        if type(unicode_str) is FName or unicode_str is None:
            return unicode_str
        try:
            return __cache[unicode_str]
        except KeyError:
            if type(unicode_str) is not str:
                raise ValueError(f'{unicode_str!r} type is '
                                 f'{type(unicode_str)} - a str is required')
            return __cache.setdefault(unicode_str, super().__new__(
                cls, unicode_str, *args, **kwargs))

    @fast_cached_property
    def _lower(self): return super().lower()

    def lower(self): return self._lower

    @fast_cached_property
    def fn_ext(self):
        return FName('' if (dot := self.rfind('.')) == -1 else self[dot:])

    @fast_cached_property
    def fn_body(self):
        return FName(self[:-len(self.fn_ext)]) if self.fn_ext else self

    def __reduce__(self):##: [backwards compat] drop in 312+ (GPath_no_norm -> str)
        return GPath_no_norm, (str(self),)

    def __deepcopy__(self, memodict={}):
        return self # immutable

    def __copy__(self):
        return self # immutable

    #--Hash/Compare
    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            self._hash = hash(self._lower)
            return self._hash
    def __eq__(self, other):
        try:
            return self._lower == other._lower # (self is other) or self...
        except AttributeError:
            # this will blow if other is not a str even if it defines lower
            return other is not None and self._lower == str.lower(other)
    def __ne__(self, other):
        try:
            return self._lower != other._lower
        except AttributeError:
            return other is None or self._lower != str.lower(other)
    def __lt__(self, other):
        try:
            return self._lower < other._lower
        except AttributeError:
            return self._lower < str.lower(other)
    def __ge__(self, other):
        try:
            return self._lower >= other._lower
        except AttributeError:
            return self._lower >= str.lower(other)
    def __gt__(self, other):
        try:
            return self._lower > other._lower
        except AttributeError:
            return self._lower > str.lower(other)
    def __le__(self, other):
        try:
            return self._lower <= other._lower
        except AttributeError:
            return self._lower <= str.lower(other)
    #--repr
    def __repr__(self):
        return f'{type(self).__name__}({super().__repr__()})'

class LowerDict(dict):
    """Dictionary that transforms its keys to CIstr instances.
    See: https://stackoverflow.com/a/43457369/281545
    """
    __slots__ = () # no __dict__ - that would be redundant

    @staticmethod # because this doesn't make sense as a global function.
    def _process_args(mapping=(), **kwargs):
        if hasattr(mapping, u'items'):
            mapping = mapping.items()
        return ((CIstr(k), v) for k, v in chain(mapping, kwargs.items()))

    def __init__(self, mapping=(), **kwargs):
        # dicts take a mapping or iterable as their optional first argument
        super().__init__(self._process_args(mapping, **kwargs))

    def __getitem__(self, k):
        return super().__getitem__(CIstr(k) if type(k) is str else k)

    def __setitem__(self, k, v):
        return super().__setitem__(CIstr(k) if type(k) is str else k, v)

    def __delitem__(self, k):
        return super().__delitem__(CIstr(k) if type(k) is str else k)

    def copy(self): # don't delegate w/ super - dict.copy() -> dict :(
        return type(self)(self)

    def get(self, k, default=None):
        return super().get(CIstr(k) if type(k) is str else k, default)

    def setdefault(self, k, default=None):
        return super().setdefault(CIstr(k) if type(k) is str else k, default)

    __no_default = object()
    def pop(self, k, v=__no_default):
        if v is LowerDict.__no_default:
            # super will raise KeyError if no default and key does not exist
            return super().pop(CIstr(k) if type(k) is str else k)
        return super().pop(CIstr(k) if type(k) is str else k, v)

    def update(self, mapping=(), **kwargs):
        super().update(self._process_args(mapping, **kwargs))

    def __contains__(self, k):
        return super().__contains__(CIstr(k) if type(k) is str else k)

    @classmethod
    def fromkeys(cls, keys, v=None):
        return super().fromkeys(
            (CIstr(k) if type(k) is str else k for k in keys), v)

    def __repr__(self):
        return f'{type(self).__name__}({super().__repr__()})'

class FNDict(dict):
    """Dictionary that transforms its keys to FName instances. Only str keys
    are accepted - FName will do the type check."""
    __slots__ = () # no __dict__ - that would be redundant

    @staticmethod # because this doesn't make sense as a global function.
    def _process_args(mapping=(), **kwargs):
        if hasattr(mapping, u'items'):
            mapping = mapping.items()
        return ((FName(k), v) for k, v in chain(mapping, kwargs.items()))

    def __init__(self, mapping=(), **kwargs):
        # dicts take a mapping or iterable as their optional first argument
        super().__init__(self._process_args(mapping, **kwargs))

    def __getitem__(self, k):
        return super().__getitem__(FName(k))

    def __setitem__(self, k, v):
        return super().__setitem__(FName(k), v)

    def __delitem__(self, k):
        return super().__delitem__(FName(k))

    def copy(self): # don't delegate w/ super - dict.copy() -> dict :(
        return type(self)(self)

    def get(self, k, default=None):
        return super().get(FName(k), default)

    def setdefault(self, k, default=None):
        return super().setdefault(FName(k), default)

    __no_default = object()
    def pop(self, k, v=__no_default):
        if v is FNDict.__no_default:
            # super will raise KeyError if no default and key does not exist
            return super().pop(FName(k))
        return super().pop(FName(k), v)

    def update(self, mapping=(), **kwargs):
        super().update(self._process_args(mapping, **kwargs))

    def __contains__(self, k):
        return super().__contains__(FName(k))

    @classmethod
    def fromkeys(cls, keys, v=None):
        return super(FNDict, cls).fromkeys((FName(k) for k in keys), v)

    def __repr__(self):
        return f'{type(self).__name__}({super().__repr__()})'

    def __reduce__(self): #[backwards compat]we 'd rather not save custom types
        return dict, (dict(self),)

# Forward compat functions - as we only want to pickle std types those stay
def forward_compat_path_to_fn(di, value_type=lambda x: x):
    try:
        return FNDict((f'{k}', value_type(v)) for k, v in di.items())
    except ValueError:
        return FNDict((str(f'{k}'), value_type(v)) for k, v in di.items())

def forward_compat_path_to_fn_list(li, ret_type=list):
    try:
        return ret_type(map(FName, map(str, li)))
    except ValueError: # tried to FName(str(path)) where type(path.s) == CIstr
        return ret_type(map(FName, map(str,  map(str, li))))

class DefaultLowerDict(LowerDict, collections.defaultdict):
    """LowerDict that inherits from defaultdict."""
    __slots__ = () # no __dict__ - that would be redundant

    def __init__(self, default_factory=None, mapping=(), **kwargs):
        # note we can't use LowerDict __init__ directly
        super(LowerDict, self).__init__(default_factory,
                                        self._process_args(mapping, **kwargs))

    def copy(self):
        return type(self)(self.default_factory, self)

    def __repr__(self):
        return f'{type(self).__name__}({self.default_factory}, ' \
               f'{super(collections.defaultdict, self).__repr__()})'

class DefaultFNDict(FNDict, collections.defaultdict):
    """FNDict that inherits from defaultdict."""
    __slots__ = () # no __dict__ - that would be redundant

    def __init__(self, default_factory=None, mapping=(), **kwargs):
        # note we can't use FNDict __init__ directly
        super(FNDict, self).__init__(default_factory,
                                     self._process_args(mapping, **kwargs))

    def copy(self):
        return type(self)(self.default_factory, self)

    def __repr__(self):
        return f'{type(self).__name__}({self.default_factory}, ' \
               f'{super(collections.defaultdict, self).__repr__()})'

class OrderedLowerDict(LowerDict, collections.OrderedDict):
    """LowerDict that inherits from OrderedDict."""
    __slots__ = () # no __dict__ - that would be redundant

#------------------------------------------------------------------------------
# cache attrgetter objects
class _AttrGettersCache(dict):
    __slots__ = ()
    def __missing__(self, ag_key):
        return self.setdefault(ag_key, attrgetter(ag_key) if isinstance(
            ag_key, str) else attrgetter(*ag_key))

attrgetter_cache = _AttrGettersCache()

# noinspection PyDefaultArgument
def setattr_deep(obj, attr, value, *, __attrgetters=attrgetter_cache,
        __split_cache={}):
    try:
        parent_attr, leaf_attr = __split_cache[attr]
    except KeyError:
        dot_dex = attr.rfind('.')
        if dot_dex > 0:
            parent_attr = attr[:dot_dex]
            leaf_attr = attr[dot_dex + 1:]
        else:
            parent_attr = ''
            leaf_attr = attr
        __split_cache[attr] = parent_attr, leaf_attr
    setattr(__attrgetters[parent_attr](obj) if parent_attr else obj,
        leaf_attr, value)

def top_level_files(directory): # faster than listdir then is_file
    return top_level_items(directory)[1]

def top_level_dirs(directory): # faster than listdir then isdir
    return top_level_items(directory)[0]

def top_level_items(directory):
    try:
        _directory, folders, files = next(os.walk(directory))
    except StopIteration: # thrown also if directory does not exist
        return [], []
    return map(FName, folders), map(FName, files)

# Paths -----------------------------------------------------------------------
#------------------------------------------------------------------------------
_gpaths: dict[str | os.PathLike[str], Path] = {}

@overload
def GPath(str_or_uni: None) -> None: ...
@overload
def GPath(str_or_uni: str | os.PathLike[str]) -> Path: ...
def GPath(str_or_uni: str | os.PathLike[str] | None) -> Path | None:
    """Path factory and cache."""
    if isinstance(str_or_uni, Path) or str_or_uni is None: return str_or_uni
    if not str_or_uni: return Path('') # needed, os.path.normpath('') = '.'!
    if str_or_uni in _gpaths: return _gpaths[str_or_uni]
    return _gpaths.setdefault(str_or_uni, Path(os.path.normpath(str_or_uni)))

##: generally points at file names, masters etc. using Paths, which they should
# not - hunt down and just use strings
def GPath_no_norm(str_or_uni):
    """Alternative to GPath that does not call normpath. It is up to the caller
    to ensure that the precondition name == os.path.normpath(name) holds for
    all values passed into this method. Only str instances accepted!

    :rtype: Path"""
    if str_or_uni in _gpaths: return _gpaths[str_or_uni]
    return _gpaths.setdefault(str_or_uni, Path(str_or_uni))

def GPathPurge():
    """Cleans out the _gpaths dictionary of any unused bolt.Path objects.
       We cannot use a weakref.WeakValueDictionary in this case for 2 reasons:
        1) bolt.Path, due to its class structure, cannot be made into weak
           references
        2) the objects would be deleted as soon as the last reference goes
           out of scope (not the behavior we want).  We want the object to
           stay alive as long as we will possibly be needing it, IE: as long
           as we're still on the same tab.
       So instead, we'll manually call our flushing function a few times:
        1) When switching tabs
        2) Prior to building a bashed patch
        3) Prior to saving settings files
    """
    for key in list(_gpaths):
        # Using list() allows us to modify the dictionary while iterating
        if sys.getrefcount(_gpaths[key]) == 2:
            # 1 for the reference in the _gpaths dictionary,
            # 1 for the temp reference passed to sys.getrefcount
            # meanin the object is not reference anywhere else
            del _gpaths[key]

#------------------------------------------------------------------------------
_conv_seps = None
class Path(os.PathLike):
    """Paths are immutable objects that represent file directory paths.
     May be just a directory, filename or full path."""

    #--Class Vars/Methods -------------------------------------------
    sys_fs_enc = sys.getfilesystemencoding() or u'mbcs'
    invalid_chars_re = re.compile(r'(.*)([/\\:*?"<>|]+)(.*)', re.I) # \\ needed

    @staticmethod
    def getNorm(str_or_path: str | bytes | Path) -> str:
        """Return the normpath for specified basename/Path object."""
        if isinstance(str_or_path, Path): return str_or_path._s
        elif not str_or_path: return u'' # and not maybe b''
        elif isinstance(str_or_path, bytes): str_or_path = decoder(str_or_path)
        return os.path.normpath(str_or_path)

    @staticmethod
    def getcwd():
        return Path(os.getcwd())

    @staticmethod
    def has_invalid_chars(path_str):
        ma_invalid_chars = Path.invalid_chars_re.match(path_str)
        if not ma_invalid_chars: return None
        return ma_invalid_chars.groups()[1]

    #--Instance stuff --------------------------------------------------
    #--Slots: _s is normalized path. All other slots are just pre-calced
    #  variations of it.
    __slots__ = ('_s', '_cs', '_sroot', '_shead', '_stail', '_ext',
                 '_cext', '_sbody', '_hash')
    # Since these are made on-the-fly, most type-checkers / IDEs will not
    # be able to infer the correct return type from .s, .cs, etc without these
    # hints.
    _cs: str
    _sroot: str
    _shead: str
    _stail: str
    _ext: str
    _cext: str
    _sbody: str
    _hash: int

    def __init__(self, norm_str: str):
        """Initialize with unicode - call only in GPath."""
        self._s = norm_str # path must be normalized
        self._cs = norm_str.lower()

    def __getstate__(self):
        """Used by pickler. _cs is redundant,so don't include."""
        return self._s

    def __setstate__(self, norm):
        """Used by unpickler. Reconstruct _cs."""
        # Older pickle files stored filename in bytes, not unicode
        norm = decoder(norm)  # decoder will check for unicode
        global _conv_seps
        try:
            self._s = _conv_seps(norm)
            self._cs = _conv_seps(norm.lower())
        except TypeError:
            from .env import convert_separators
            _conv_seps = convert_separators
            self._s = _conv_seps(norm)
            self._cs = _conv_seps(norm.lower())

    def __len__(self):
        return len(self._s)

    def __repr__(self):
        return f'bolt.Path({self._s!r})'

    def __str__(self):
        return self._s

    def __fspath__(self):
        return self._s

    #--Properties--------------------------------------------------------
    #--String/unicode versions.
    @property
    def s(self):
        """Path as string."""
        return self._s
    @property
    def cs(self):
        """Path as string in normalized case."""
        return self._cs
    @property
    def sroot(self):
        """Root as string."""
        try:
            return self._sroot
        except AttributeError:
            self._sroot, self._ext = os.path.splitext(self._s)
            return self._sroot
    @property
    def shead(self):
        """Head as string."""
        try:
            return self._shead
        except AttributeError:
            self._shead, self._stail = os.path.split(self._s)
            return self._shead
    @property
    def stail(self):
        """Tail as string."""
        try:
            return self._stail
        except AttributeError:
            self._shead, self._stail = os.path.split(self._s)
            return self._stail
    @property
    def sbody(self):
        """For alpha\beta.gamma returns beta as string."""
        try:
            return self._sbody
        except AttributeError:
            self._sbody = os.path.basename(self.sroot)
            return self._sbody

    #--Head, tail
    @property
    def headTail(self):
        """For alpha\beta.gamma returns (alpha,beta.gamma)"""
        return [GPath(self.shead), GPath(self.stail)]
    @property
    def head(self):
        """For alpha\beta.gamma, returns alpha."""
        return GPath(self.shead)
    @property
    def tail(self):
        """For alpha\beta.gamma, returns beta.gamma."""
        return GPath_no_norm(self.stail)
    @property
    def body(self):
        """For alpha\beta.gamma, returns beta."""
        return GPath_no_norm(self.sbody)

    #--Root, ext
    @property
    def root(self):
        """For alpha\beta.gamma returns alpha\beta"""
        return GPath(self.sroot)
    @property
    def ext(self):
        """Extension (including leading period, e.g. '.txt')."""
        try:
            return self._ext
        except AttributeError:
            self._sroot, self._ext = os.path.splitext(self._s)
            return self._ext
    @property
    def cext(self):
        """Extension in normalized case."""
        try:
            return self._cext
        except AttributeError:
            self._cext = self.ext.lower()
            return self._cext

    def replace_with_temp(self, temp_path: str | os.PathLike):
        """Replace this file with a temporary version created via TempFile or
        new_temp_file, optionally making a backup of this file first. Note that
        this *does not work for directories!* It is only intended for files.

        This also does not remove the temporary file from the internal caches
        so as to work with TempFile."""
        try:
            shutil.move(temp_path, self._s)
        except PermissionError:
            self.clearRO()
            shutil.move(temp_path, self._s)
        # Do *not* call cleanup_temp_file here! This method needs to work with
        # TempFile, which will already call cleanup_temp_file for us

    @property
    def backup(self):
        """Backup file path."""
        return self+u'.bak'

    #--size, atime
    @property
    def psize(self):
        """Size of file or directory."""
        if self.is_dir():
            join = os.path.join
            op_size = os.path.getsize
            try:
                return sum(sum(op_size(join(x, f)) for f in files)
                           for x, _y, files in os.walk(self._s))
            except ValueError:
                return 0
        else:
            return os.path.getsize(self._s)

    @property
    def atime(self):
        return os.path.getatime(self._s)

    #--Mtime
    def _getmtime(self):
        """Return mtime for path."""
        return os.path.getmtime(self._s)
    def _setmtime(self, new_time):
        os.utime(self._s, (self.atime, new_time))
    mtime = property(_getmtime, _setmtime, doc='Time file was last modified.')

    def size_mtime(self):
        lstat = os.lstat(self._s)
        return lstat.st_size, lstat.st_mtime

    def size_mtime_ctime(self):
        lstat = os.lstat(self._s)
        return lstat.st_size, lstat.st_mtime, lstat.st_ctime

    @property
    def stat(self):
        """File stats"""
        return os.stat(self._s)

    #--crc
    @property
    def crc(self):
        """Calculates and returns crc value for self."""
        crc = 0
        with self.open(u'rb') as ins:
            while block := ins.read(2097152): # 2MB at a time
                crc = crc32(block, crc)
        return crc

    #--Path stuff -------------------------------------------------------
    #--New Paths, subpaths
    def __add__(self,other):
        # you can't add to None: ValueError - that's good
        return GPath(self._s + Path.getNorm(other))
    def join(*args: str | os.PathLike[str]) -> Path:
        norms = [Path.getNorm(x) for x in args] # join(..,None,..) -> TypeError
        return GPath(os.path.join(*norms))

    def ilist(self) -> Iterator[FName] | list[FName]:
        """For directory: Return list of files - bit weird this returns
        FName but let's say Path and FName are friend classes."""
        try:
            return map(FName, os.listdir(self._s))
        except FileNotFoundError:
            return []

    def walk(self, topdown=True, onerror=None, *, relative=False):
        """Like os.walk."""
        if relative:
            start = len(self._s)
            for root_dir,dirs,files in os.walk(self._s, topdown, onerror):
                yield (GPath(root_dir[start:]),
                       [GPath_no_norm(x) for x in dirs],
                       [GPath_no_norm(x) for x in files])
        else:
            for root_dir,dirs,files in os.walk(self._s, topdown, onerror):
                yield (GPath(root_dir), ##: leaves the leading path separator?
                       [GPath_no_norm(x) for x in dirs],
                       [GPath_no_norm(x) for x in files])

    def relpath(self,path): # os.path.relpath(p,[s]): AttributeError if s==None
        return GPath(os.path.relpath(self._s,Path.getNorm(path)))

    def drive(self):
        """Returns the drive part of the path string."""
        return GPath(os.path.splitdrive(self._s)[0])

    #--File system info
    def exists(self):
        return os.path.exists(self._s)
    def is_dir(self):
        return os.path.isdir(self._s)
    def is_file(self):
        return os.path.isfile(self._s)
    def is_absolute(self):
        return os.path.isabs(self._s)

    #--File system manipulation
    @staticmethod
    def _onerror(func,path,exc_info):
        """shutil error handler: remove RO flag"""
        if not os.access(path,os.W_OK):
            os.chmod(path,stat.S_IWUSR|stat.S_IWOTH)
            func(path)
        else:
            raise

    def clearRO(self): ##: we need an (env) decorator for this one
        """Clears RO flag on self"""
        if not self.is_dir():
            os.chmod(self._s,stat.S_IWUSR|stat.S_IWOTH)
        else:
            clearReadOnly(self)

    ##: Deprecated, replace with regular open() where possible to help erode
    # Path dependencies all over WB
    def open(self,*args,**kwdargs):
        try:
            return open(self._s, *args, **kwdargs)
        except FileNotFoundError:
            # We rarely need to do this, so avoid the stat call from
            # os.path.exists unless it's unavoidable
            if self.shead and not os.path.exists(self.shead):
                os.makedirs(self.shead)
                return open(self._s, *args, **kwdargs)
            raise

    def makedirs(self):
        os.makedirs(self._s, exist_ok=True)

    def remove(self):
        try:
            os.remove(self._s)
        except FileNotFoundError:
            pass # does not exist
        except OSError:
            self.clearRO()
            os.remove(self._s)
    def removedirs(self, raise_error=True):
        try:
            os.removedirs(self._s)
        except FileNotFoundError:
            pass # does not exist
        except OSError:
            try:
                self.clearRO()
                os.removedirs(self._s)
            except OSError:
                if raise_error: raise

    def rmtree(self,safety=u'PART OF DIRECTORY NAME'):
        """Removes directory tree. As a safety factor, a part of the directory name must be supplied."""
        if self.is_dir() and safety and safety.lower() in self._cs:
            shutil.rmtree(self._s,onerror=Path._onerror)

    #--start, move, copy
    def start(self, exe_cli=None):
        """Starts file as if it had been doubleclicked in file explorer."""
        if self.cext == u'.exe':
            if not exe_cli:
                subprocess.Popen([self._s], close_fds=True)
            else:
                subprocess.Popen(exe_cli, executable=self._s, close_fds=True)
        else:
            if sys.platform == 'darwin':
                webbrowser.open(f'file://{self._s}')
            elif platform.system() == u'Windows':
                os.startfile(self._s)
            else: ##: TTT linux - WIP move this switch to env launch_file
                subprocess.call(['xdg-open', f'{self._s}'])
    def copyTo(self, dest_path, set_time=None):
        """Copy self to dest_path make dirs if necessary and preserve ftime."""
        dest_path = GPath(dest_path)
        if self.is_dir():
            raise exception.StateError(f'{self._s} is a directory.')
        try:
            copy_or_reflink(self._s, dest_path._s)
            dest_path.mtime = set_time or self.mtime
        except FileNotFoundError:
            if not (dest_par := dest_path.shead) or os.path.exists(dest_par):
                raise
            os.makedirs(dest_par)
            self.copyTo(dest_path, set_time)
    def moveTo(self, destName, *, check_exist=True):
        if check_exist and not self.exists():
            raise exception.StateError(f'{self._s} cannot be moved because it '
                                       f'does not exist.')
        destPath = GPath(destName)
        if destPath._cs == self._cs: return
        if destPath.exists(): ##: needed for dirs? (files will just replace)
            destPath.remove()
        try:
            shutil.move(self._s,destPath._s)
        except FileNotFoundError:
            if not (dest_par := destPath.shead) or os.path.exists(dest_par):
                raise
            os.makedirs(dest_par)
            shutil.move(self._s,destPath._s)
        except OSError:
            self.clearRO()
            shutil.move(self._s,destPath._s)

    #--Hash/Compare, based on the _cs attribute so case insensitive. NB: Paths
    # directly compare to str|Path|None and will blow for anything else
    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            self._hash = hash(self._cs)
            return self._hash
    def __eq__(self, other):
        try:
            return self._cs == other._cs
        except AttributeError:
            # Only compare with unicode or None - will blow on other types -
            # similar code in rest of the methods below
            if (typ := type(other)) is str:
                other = os.path.normpath(other).lower() if other else other
            elif other is not None:
                raise TypeError(
                    f'Comparing Path with {typ} not supported: {other!r}')
        return self._cs == other
    def __ne__(self, other):
        try:
            return self._cs != other._cs
        except AttributeError:
            if (typ := type(other)) is str:
                other = os.path.normpath(other).lower() if other else other
            elif other is not None:
                raise TypeError(
                    f'Comparing Path with {typ} not supported: {other!r}')
        return self._cs != other
    def __lt__(self, other):
        try:
            return self._cs < other._cs
        except AttributeError:
            if (typ := type(other)) is str:
                other = os.path.normpath(other).lower() if other else other
            else: raise TypeError(f'Comparing Path with {typ} not supported: '
                                  f'{other!r}')
        return self._cs < other
    def __ge__(self, other):
        try:
            return self._cs >= other._cs
        except AttributeError:
            if (typ := type(other)) is str:
                other = os.path.normpath(other).lower() if other else other
            else: raise TypeError(f'Comparing Path with {typ} not supported: '
                                  f'{other!r}')
        return self._cs >= other
    def __gt__(self, other):
        try:
            return self._cs > other._cs
        except AttributeError:
            if (typ := type(other)) is str:
                other = os.path.normpath(other).lower() if other else other
            else: raise TypeError(f'Comparing Path with {typ} not supported: '
                                  f'{other!r}')
        return self._cs > other
    def __le__(self, other):
        try:
            return self._cs <= other._cs
        except AttributeError:
            if (typ := type(other)) is str:
                other = os.path.normpath(other).lower() if other else other
            else: raise TypeError(f'Comparing Path with {typ} not supported: '
                                  f'{other!r}')
        return self._cs <= other

    # avoid setstate/getstate round trip
    def __deepcopy__(self, memodict={}):
        return self # immutable

    def __copy__(self):
        return self # immutable

undefinedPath = GPath(r'C:\not\a\valid\path.exe')

# We need to split every time we hit a new 'type' of component. So greedily
# match as many of one type as possible (except dots and dashes, since those
# are guaranteed to start a new component)
_component_re = re.compile(r'(\.|-|\d+|[^\d.-]+)')
_separators = frozenset({'.', '-'})
class LooseVersion:
    """A class for representing and comparing versions, where the term
    'version' refers to any and every possible string. The way this class works
    is pretty simple: there are three 'types' of components to a LooseVersion:

     - separators (dots and dashes)
     - digits
     - everything else

    Separators begin a new component to the version, but are not part of the
    version themselves. Digits are compared numerically, so 2 < 10. Everything
    else is compared alphabetically, so 'a' < 'm'. A whole version is compared
    by comparing the components in it as a tuple."""
    _parsed_version: tuple[int | str]

    def __init__ (self, ver_string: str):
        ver_components = _component_re.split(ver_string)
        parsed_version = []
        for ver_comp in ver_components:
            if not ver_comp or ver_comp in _separators:
                # Empty components and separators are not part of the version
                continue
            try:
                parsed_version.append(int(ver_comp))
            except ValueError:
                parsed_version.append(ver_comp)
        self._parsed_version = tuple(parsed_version)

    def __repr__(self):
        return '.'.join([str(c) for c in self._parsed_version])

    def __eq__(self, other):
        if not isinstance(other, LooseVersion):
            return NotImplemented
        return self._parsed_version == other._parsed_version

    def __lt__(self, other):
        if not isinstance(other, LooseVersion):
            return NotImplemented
        return self._parsed_version < other._parsed_version

    def __le__(self, other):
        if not isinstance(other, LooseVersion):
            return NotImplemented
        return self._parsed_version <= other._parsed_version

    def __gt__(self, other):
        if not isinstance(other, LooseVersion):
            return NotImplemented
        return self._parsed_version > other._parsed_version

    def __ge__(self, other):
        if not isinstance(other, LooseVersion):
            return NotImplemented
        return self._parsed_version >= other._parsed_version

def popen_common(popen_cmd, **kwargs):
    """Wrapper around subprocess.Popen with commonly needed parameters."""
    return subprocess.Popen(popen_cmd, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            startupinfo=startupinfo, **kwargs)

def clearReadOnly(dirPath):
    """Recursively (/S) clear ReadOnly flag if set - include folders (/D)."""
    if os_name == 'nt':
        cmd = fr'attrib -R "{dirPath}\*" /S /D'
        subprocess.call(cmd, startupinfo=startupinfo)
        return
    # elif platform.system() == u'Darwin':
    #     cmd = f'chflags -R nouchg {dirPath}'
    else: # https://stackoverflow.com/a/36285142/281545 - last & needed on mac
        cmds = (
            fr'find "{dirPath}" -not -executable -exec chmod a=rw {{}} \; &',
            fr'find "{dirPath}" -executable -exec chmod a=rwx {{}} \; &')
    for cmd in cmds: os.system(cmd) # returns 0 with the final &, 256 otherwise

# Util Constants --------------------------------------------------------------
#--Unix new lines
reUnixNewLine = re.compile(r'(?<!\r)\n', re.U)

# Util Classes ----------------------------------------------------------------
#------------------------------------------------------------------------------
_not_a_flag = object()  # sentinel for Flags typehints

def flag(index: int | None) -> bool:
    """Type erasing method for assigning Field index values."""
    return index    # type: ignore

class Flags:
    """Represents a flag field.  New Flags classes are defined by subclassing.

    When subclassing, simply typehint attribute names with `bool` to
    have these as aliases for bits in the Flags instance. Bit 0 refers to the
    least significant bit, and successive names increment from there. To
    override which bit an attribute maps to, set it using `= flag(bit)`.

    To support Flags types whose fields are determined at runtime, you can
    specify `= flag(None)` to indicate that the index should be incremented,
    but no name associated with that bit of the field. This is intended for
    usage with static deciders like `fnv_only` and `sse_only`."""
    __slots__ = ('_field',)
    _names: ClassVar[dict[str, int]] = {}

    @classmethod
    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        names_dict = {}
        current_index = 0
        hints = get_type_hints(cls)
        hints = ((att, hint) for att, hint in hints.items() if hint is bool)
        for attr, hint in hints: # we're only considering the 'bool' hints
            override = getattr(cls, attr, _not_a_flag)
            if override is not _not_a_flag:
                if override is None:
                    # None indicates just increment the index
                    current_index += 1
                    continue
                # Error checks
                if isinstance(override, int):
                    if override < 0:
                        raise ValueError(
                            f'{cls.__name__} flag field index must be a '
                            f'positive integer or None, got {override}')
                    current_index = override
                else:
                    raise TypeError(f'{cls.__name__} flag field index must '
                                    f'be an integer or None, got {override!r}')
            names_dict[attr] = current_index
            current_index += 1
        cls._names = names_dict

    #--Generation
    def __init__(self, value: int | Self = 0):
        """Set the internal int value."""
        object.__setattr__(self, u'_field', int(value))

    def __call__(self,newValue=None): ##: ideally drop in favor of copy (explicit)
        """Returns a clone of self, optionally with new value."""
        if newValue is not None:
            return self.__class__(int(newValue))
        else:
            return self.__class__(self._field)

    def __deepcopy__(self, memodict={}):
        newFlags = self.__class__(self._field)
        memodict[id(self)] = newFlags ##: huh?
        return newFlags

    def __copy__(self):
        return self.__class__(self._field)

    #--As hex string
    def hex(self):
        """Returns hex string of value."""
        return f'{self._field:08X}'
    def dump(self):
        """Returns value for packing"""
        return self._field

    #--As int
    def __int__(self):
        """Return as integer value for saving."""
        return self._field
    def __index__(self):
        """Same as __int__, needed for packing in python3."""
        return self._field

    #--As list
    def __getitem__(self, index):
        """Get value by index. E.g., flags[3]"""
        return bool((self._field >> index) & 1)

    def __setitem__(self,index,value):
        """Set value by index. E.g., flags[3] = True"""
        value = ((value or 0) and 1) << index
        mask = 1 << index
        self._field = ((self._field & ~mask) | value)

    #--As class
    def __getattribute__(self, attr_key: str):
        """Get value by flag name. E.g. flags.isQuestItem.
        Since some flag names may have values set on the class itself via
        `flagname = flag(bit)`, we can't use __getattr__ as accessing these
        won't raise AttributeError (which leads to __getattr__ being called).
        """
        try:
            index = type(self)._names[attr_key]
            return (super().__getattribute__('_field') >> index) & 1 == 1
        except KeyError:
            return super().__getattribute__(attr_key)

    def __setattr__(self, attr_key, value):
        """Set value by flag name. E.g., flags.isQuestItem = False"""
        if attr_key == u'_field':
            object.__setattr__(self, attr_key, value)
        else:
            self.__setitem__(self.__class__._names[attr_key], value)

    #--Native operations
    def __eq__( self, other):
        """Logical equals."""
        if isinstance(other,Flags):
            return self._field == other._field
        else:
            return self._field == other

    def __ne__( self, other):
        """Logical not equals."""
        if isinstance(other,Flags):
            return self._field != other._field
        else:
            return self._field != other

    def __and__(self,other):
        """Bitwise and."""
        if isinstance(other,Flags): other = other._field
        return self.__class__(self._field & other)

    def __invert__(self):
        """Bitwise inversion."""
        return self.__class__(~self._field)

    def __or__(self,other):
        """Bitwise or."""
        if isinstance(other,Flags): other = other._field
        return self.__class__(self._field | other)

    def __xor__(self,other):
        """Bitwise exclusive or."""
        if isinstance(other,Flags): other = other._field
        return self.__class__(self._field ^ other)

    def getTrueAttrs(self):
        """Returns attributes that are true."""
        trueNames = [flname for flname in self.__class__._names if
                     getattr(self, flname)]
        return tuple(trueNames)

    def __repr__(self):
        """Shows all set flags."""
        all_flags = u', '.join(self.getTrueAttrs()) if self._field else u'None'
        return f'0x{self.hex()} ({all_flags})'

class TrimmedFlags(Flags):
    """Flags subtype that will discard unnamed flags on __init__ and dump."""
    __slots__ = ()

    def __init__(self, value=0):
        super().__init__(value)
        self._clean_flags()

    def _clean_flags(self):
        """Remove all unnamed flags."""
        final_flags = 0
        for flg_name, flg_idx in self.__class__._names.items():
            if getattr(self, flg_name):
                final_flags |= 1 << flg_idx
        self._field = final_flags

    def dump(self):
        self._clean_flags()
        return super().dump()

#------------------------------------------------------------------------------
##: This seems highly unnecessary now, can we get rid of it?
class MasterSet(set):
    """Set of master names."""
    __slots__ = ()

    def add(self, element):
        """Add a long fid's mod name."""
        try:
            super().add(element.mod_fn)
        except AttributeError:
            if element is not None:
                raise

#------------------------------------------------------------------------------
class DataDict(object):
    """Mixin class that handles dictionary emulation, assuming that
    dictionary is its '_data' attribute."""

    def __init__(self, data_dict):
        self._data = data_dict # not final - see for instance InstallersData

    def __contains__(self,key):
        return key in self._data
    def __getitem__(self,key):
        """Return value for key or raise KeyError if not present."""
        return self._data[key]
    def __setitem__(self,key,value):
        self._data[key] = value
    def __delitem__(self,key):
        del self._data[key]
    def __len__(self):
        return len(self._data)
    def __iter__(self):
        return iter(self._data)
    def values(self):
        return self._data.values()
    def items(self):
        return self._data.items()
    def get(self,key,default=None):
        return self._data.get(key, default)
    def pop(self,key,default=None):
        return self._data.pop(key, default)

#------------------------------------------------------------------------------
class AFile(object):
    """Abstract file or folder, supports caching."""
    _null_stat = (-1, None)

    def __init__(self, fullpath, load_cache=False, *, raise_on_error=False,
                 **kwargs):
        self._file_key = GPath(fullpath) # abs path of the file but see ModInfo
        #Set cache info (ftime, size[, ctime]) and reload if load_cache is True
        try:
            self._reset_cache(self._stat_tuple(), load_cache=load_cache,
                              **kwargs)
        except OSError:
            if raise_on_error: raise
            self._reset_cache(self._null_stat, load_cache=False)

    def _stat_tuple(self): return self.abs_path.size_mtime()

    @property
    def abs_path(self): return self._file_key

    @abs_path.setter
    def abs_path(self, val): self._file_key = val

    def do_update(self, raise_on_error=False, force_update=False, **kwargs):
        """Check cache, reset it if needed. Return True if reset else False.
        If the stat call fails and this instance was previously stat'ed we
        consider the file deleted and return True except if raise_on_error is
        True, whereupon raise the OSError we got in stat(). If raise_on_error
        is False user must check if file exists.

        :param raise_on_error: If True, raise on errors instead of just
            resetting the cache and returning.
        :param **kwargs: various:
            - itsa_ghost: In ModInfos, if we have the ghosting info available,
              skip recalculating it.
            - progress: will be useful for installers
        """
        try:
            stat_tuple = self._stat_tuple()
        except OSError: # PY3: FileNotFoundError case?
            file_was_stated = self._file_changed(self._null_stat)
            self._reset_cache(self._null_stat, load_cache=False, **kwargs)
            if raise_on_error: raise
            return file_was_stated # file previously existed, we need to update
        if force_update or self._file_changed(stat_tuple):
            self._reset_cache(stat_tuple, load_cache=True, **kwargs)
            return True
        return False

    def needs_update(self):
        """Returns True if this file changed. Throws an OSError if it is
        deleted. Avoid all but simple uses - use do_update instead."""
        return self._file_changed(self._stat_tuple())

    def _file_changed(self, stat_tuple):
        return (self.fsize, self.ftime) != stat_tuple

    def _reset_cache(self, stat_tuple, **kwargs):
        """Reset cache flags (fsize, ftime,...) and possibly reload the cache.
        :param **kwargs: various
            - load_cache: if True either load the cache (header in Mod and
            SaveInfo) or reset it, so it gets reloaded later
        """
        self.fsize, self.ftime = stat_tuple

    def __repr__(self):
        return f'{self.__class__.__name__}<{self.abs_path.stail}>'

#------------------------------------------------------------------------------
class ListInfo:
    """Info object displayed in Wrye Bash list."""
    __slots__ = ('fn_key', )
    _valid_exts_re = ''
    _is_filename = True
    _has_digits = False

    def __init__(self, fn_key):
        self.fn_key = FName(fn_key)

    @classmethod
    def validate_filename_str(cls, name_str: str, allowed_exts=frozenset()):
        """Basic validation of list item name - those are usually filenames, so
        they should contain valid chars. We also optionally check for match
        with an extension group (apart from projects and markers). Returns
        a tuple - if the second element is None validation failed and the first
        element is the message to show - if not the meaning varies per override
        """
        if not name_str:
            return _('Name may not be empty.'), None
        char = cls._is_filename and Path.has_invalid_chars(name_str)
        if char:
            inv = _('%(new_name)s contains invalid character (%(bad_char)s).')
            return inv % {'new_name': name_str, 'bad_char': char}, None
        rePattern = cls._name_re(allowed_exts)
        maPattern = rePattern.match(name_str)
        if maPattern:
            ma_groups = maPattern.groups(default=u'')
            root = ma_groups[0]
            num_str = ma_groups[1] if cls._has_digits else None
            if not (root or num_str):
                pass # will return the error message at the end
            elif cls._has_digits: return FName(root), num_str
            else: return FName(name_str), root
        return (_('Bad extension or file root (%(ext_or_root)s).') % {
            'ext_or_root': name_str}), None

    def validate_name(self, name_str, check_store=True):
        # disallow extension change but not if no-extension info type
        check_ext = name_str and self.__class__._valid_exts_re
        if check_ext and not name_str.lower().endswith(
                self.fn_key.fn_ext.lower()):
            msg = _('%(bad_name_str)s: Incorrect file extension (must be '
                    '%(expected_ext)s).') % {
                'bad_name_str': name_str, 'expected_ext': self.fn_key.fn_ext}
            return msg, None
        return self.__class__.validate_filename_str(name_str)

    @classmethod
    def _name_re(cls, allowed_exts):
        exts_re = fr'(\.(?:{"|".join(e[1:] for e in allowed_exts)}))' \
            if allowed_exts else cls._valid_exts_re
        # The reason we do the regex like this is to support names like
        # foo.ess.ess.ess etc.
        exts_prefix = r'(?=.+\.)' if exts_re else ''
        final_regex = f'^{exts_prefix}(.*?)'
        if cls._has_digits: final_regex += r'(\d*)'
        final_regex += f'{exts_re}$'
        return re.compile(final_regex, re.I)

    # Generate unique filenames when duplicating files etc
    @staticmethod
    def _new_name(base_name, count): # only use in unique_name - count is > 0 !
        r, e = os.path.splitext(base_name)
        return f'{r} ({count}){e}'

    @classmethod
    def unique_name(cls, name_str, check_exists=False):
        base_name = name_str
        unique_counter = 0
        store = cls.get_store()
        while (store.store_dir.join(name_str).exists() if check_exists else
               name_str in store): # must wrap a FNDict
            unique_counter += 1
            name_str = cls._new_name(base_name, unique_counter)
        return FName(name_str)

    def unique_key(self, new_root, ext='', add_copy=False):
        """Generate a unique name based on fn_key. When copying or renaming."""
        if self.__class__._valid_exts_re and not ext:
            ext = self.fn_key.fn_ext
        new_name = new_root + (f" {_('Copy')}" if add_copy else '') + ext
        if new_name == self.fn_key: # new and old names are ci-same
            return None
        return self.unique_name(new_name)

    # Gui renaming stuff ------------------------------------------------------
    @classmethod
    def rename_area_idxs(cls, text_str, start=0, stop=None):
        """Return the selection span of item being renamed - usually to
        exclude the extension."""
        if cls._valid_exts_re and not start: # start == 0
            return 0, len(GPath(text_str[:stop]).sbody)
        return 0, len(text_str) # if selection not at start reset

    @classmethod
    def get_store(cls):
        raise NotImplementedError(f'{type(cls)} does not provide a data store')

    def __str__(self):
        """Alias for self.fn_key."""
        return self.fn_key

    def __repr__(self):
        return f'{self.__class__.__name__}<{self.fn_key}>'

#------------------------------------------------------------------------------
class AFileInfo(AFile, ListInfo):
    """List Info representing a file."""
    def __init__(self, fullpath, load_cache=False, **kwargs):
        ListInfo.__init__(self, fullpath.stail) # ghost must be lopped off
        super().__init__(fullpath, load_cache, **kwargs)

    def delete_paths(self):
        """Paths to delete when this item is deleted - abs_path comes first!"""
        return self.abs_path,

    def move_info(self, destDir):
        """Hasty method used in UIList.hide(). Will overwrite! The client is
        responsible for calling delete_refresh of the data store."""
        self.abs_path.moveTo(destDir.join(self.fn_key))

    def get_rename_paths(self, newName):
        """Return possible paths this file's renaming might affect (possibly
        omitting some that do not exist)."""
        return [(self.abs_path, self.get_store().store_dir.join(newName))]

    def validate_name(self, name_str, check_store=True):
        super_validate = super().validate_name(name_str,
            check_store=check_store)
        #--Else file exists?
        if check_store and self.info_dir.join(name_str).exists():
            return _('File %(bad_name_str)s already exists.') % {
                'bad_name_str': name_str}, None
        return super_validate

    @property
    def info_dir(self):
        return self.abs_path.head

#------------------------------------------------------------------------------
class PickleDict(object):
    """Dictionary saved in a pickle file.
    Note: self.vdata and self.data are not reassigned! (Useful for some clients.)"""
    def __init__(self, pkl_path, readOnly=False, load_pickle=False):
        """Initialize."""
        self._pkl_path = pkl_path
        self.backup = pkl_path.backup
        self.readOnly = readOnly
        self.vdata = {}
        self.pickled_data = {}
        if load_pickle: self.load()

    def exists(self):
        return self._pkl_path.exists() or self.backup.exists()

    class Mold(Exception):
        def __init__(self, moldedFile):
            msg = (f'Your settings in {moldedFile} come from an ancient Bash '
                   f'version. Please load them in 307 so they are converted '
                   f'to the newer format')
            super(PickleDict.Mold, self).__init__(msg)

    def load(self):
        """Loads vdata and data from file or backup file.

        If file does not exist, or is corrupt, then reads from backup file. If
        backup file also does not exist or is corrupt, then no data is read. If
        no data is read, then self.data is cleared.

        If file exists and has a vdata header, then that will be recorded in
        self.vdata. Otherwise, self.vdata will be empty.

        Returns:
          0: No data read (files don't exist and/or are corrupt)
          1: Data read from file
          2: Data read from backup file
        """
        self.vdata.clear()
        self.pickled_data.clear()
        cor = cor_name =  None
        def _perform_load():
            self.vdata.update(pickle.load(ins, encoding='bytes'))
            self.pickled_data.update(pickle.load(ins, encoding='bytes'))
        for path in (self._pkl_path, self.backup):
            if cor is not None:
                cor.moveTo(cor_name)
                cor = None
            try:
                resave = False
                with path.open(u'rb') as ins:
                    try:
                        firstPickle = pickle.load(ins, encoding='bytes')
                    except ValueError:
                        cor = path
                        cor_name = GPath(f'{path} ({timestamp()}).corrupted')
                        deprint(f'Unable to load {path} (will be moved to '
                                f'"{cor_name.tail}")', traceback=True)
                        continue  # file corrupt - try next file
                    if firstPickle == u'VDATA3':
                        _perform_load() # new format, simply load
                    elif firstPickle == b'VDATA2':
                        # old format, load and convert
                        _perform_load()
                        self.vdata = conv_obj(self.vdata)
                        self.pickled_data = conv_obj(self.pickled_data)
                        deprint(f'Converted {path} to VDATA3 format')
                        resave = True
                    else:
                        raise PickleDict.Mold(path)
                # Check if we need to resave the settings after conversion
                if resave:
                    # Make a permanent backup copy of the VDATA2 version before
                    # saving over it
                    path.copyTo(path.root + u'-vdata2.dat.bak')
                    self.save()
                return 1 + (path == self.backup)
            except (OSError, EOFError, ValueError,
                    pickle.UnpicklingError): #PY3:FileNotFound
                pass
        else:
            if cor is not None:
                cor.moveTo(cor_name)
        #--No files and/or files are corrupt
        return 0

    def save(self):
        """Save to pickle file.

        Three objects are writen - a version string and the vdata and
        pickled_data dictionaries, in this order. Current version string is
        VDATA3."""
        if self.readOnly: return False
        #--Pickle it
        with TempFile() as temp_pkl:
            with open(temp_pkl, 'wb') as out:
                for pkl in ('VDATA3', self.vdata, self.pickled_data):
                    pickle.dump(pkl, out, -1)
            try:
                self._pkl_path.copyTo(self._pkl_path.backup)
            except FileNotFoundError:
                pass # No settings file to back up yet, this is fine
            self._pkl_path.replace_with_temp(temp_pkl)
        return True

#------------------------------------------------------------------------------
class Settings(DataDict):
    """Settings/configuration dictionary with persistent storage.

    Default setting for configurations are either set in bulk (by the
    loadDefaults function) or are set as needed in the code (e.g., various
    auto-continue settings for bash). Only settings that have been changed from
    the default values are saved in persistent storage."""

    def __init__(self, dictFile):
        """Initialize. Read settings from dictFile."""
        self.dictFile = dictFile
        if self.dictFile:
            res = dictFile.load()
            self.vdata = dictFile.vdata.copy()
            super().__init__(dictFile.pickled_data.copy())
        else:
            self.vdata = {}
            super().__init__({})
        self._default_settings = {}

    def loadDefaults(self, default_settings):
        """Add default settings to dictionary."""
        self._default_settings = default_settings
        #--Clean colors dictionary
        if (color_dict := self.get(u'bash.colors', None)) is not None:
            currentColors = set(color_dict)
            defaultColors = set(default_settings[u'bash.colors'])
            invalidColors = currentColors - defaultColors
            missingColors = defaultColors - currentColors
            for key in invalidColors:
                del self[u'bash.colors'][key]
            for key in missingColors:
                self[u'bash.colors'][key] = default_settings[u'bash.colors'][key]
        # fill up missing settings from defaults, making sure we do not
        # modify the latter
        self._data = collections.ChainMap(self._data, copy.deepcopy(
            self._default_settings))

    def save(self):
        """Save to pickle file. Only key/values differing from defaults are
        saved."""
        dictFile = self.dictFile
        dictFile.vdata = self.vdata.copy()
        to_save = {}
        dflts = self._default_settings
        for sett_key, sett_val in self.items():
            if sett_key in dflts and dflts[sett_key] == sett_val:
                continue # not all settings are in defaults
            to_save[sett_key] = sett_val
        self.dictFile.pickled_data = to_save
        dictFile.save()

# Structure wrappers ----------------------------------------------------------
class _StructsCache(dict):
    __slots__ = ()
    def __missing__(self, key):
        return self.setdefault(key, struct.Struct(key))

structs_cache = _StructsCache()
def unpack_str16(ins, __unpack=structs_cache[u'H'].unpack) -> bytes:
    return ins.read(__unpack(ins.read(2))[0])
def unpack_str32(ins, __unpack=structs_cache[u'I'].unpack) -> bytes:
    return ins.read(__unpack(ins.read(4))[0])
def unpack_int(ins, __unpack=structs_cache[u'I'].unpack) -> int:
    return __unpack(ins.read(4))[0]
def pack_int(out, value: int, __pack=structs_cache[u'=I'].pack):
    out.write(__pack(value))
def unpack_int64(ins, __unpack=structs_cache['Q'].unpack) -> int:
    return __unpack(ins.read(8))[0]
def unpack_short(ins, __unpack=structs_cache[u'H'].unpack) -> int:
    return __unpack(ins.read(2))[0]
def pack_short(out, val: int, __pack=structs_cache[u'=H'].pack):
    out.write(__pack(val))
def unpack_float(ins, __unpack=structs_cache[u'f'].unpack) -> float:
    return __unpack(ins.read(4))[0]
def pack_float(out, val: float, __pack=structs_cache[u'=f'].pack):
    out.write(__pack(val))
def unpack_double(ins, __unpack=structs_cache[u'd'].unpack) -> float:
    return __unpack(ins.read(8))[0]
def pack_double(out, val: float, __pack=structs_cache[u'=d'].pack):
    out.write(__pack(val))
def unpack_byte(ins, __unpack=structs_cache[u'B'].unpack) -> int:
    return __unpack(ins.read(1))[0]
def pack_byte(out, val: int, __pack=structs_cache[u'=B'].pack):
    out.write(__pack(val))
def unpack_int_signed(ins, __unpack=structs_cache[u'i'].unpack) -> int:
    return __unpack(ins.read(4))[0]
def pack_int_signed(out, val: int, __pack=structs_cache[u'=i'].pack):
    out.write(__pack(val))
def unpack_int64_signed(ins, __unpack=structs_cache[u'q'].unpack) -> int:
    return __unpack(ins.read(8))[0]
def unpack_4s(ins, __unpack=structs_cache[u'4s'].unpack) -> bytes:
    return __unpack(ins.read(4))[0]
def pack_4s(out, val: bytes, __pack=structs_cache[u'=4s'].pack):
    out.write(__pack(val))
def unpack_str16_delim(ins, __unpack=structs_cache[u'Hc'].unpack) -> bytes:
    str_len = __unpack(ins.read(3))[0]
    # The actual string (including terminator) isn't stored for empty strings
    if not str_len: return b''
    str_value = ins.read(str_len)
    ins.seek(1, 1) # discard string terminator
    return str_value
def unpack_str_int_delim(ins, __unpack=structs_cache[u'Ic'].unpack) -> int:
    return __unpack(ins.read(5))[0]
def unpack_str_byte_delim(ins, __unpack=structs_cache[u'Bc'].unpack) -> int:
    return __unpack(ins.read(2))[0]
def unpack_str8(ins, __unpack=structs_cache[u'B'].unpack) -> bytes:
    return ins.read(__unpack(ins.read(1))[0])
def pack_str8(out, val: bytes, __pack=structs_cache[u'=B'].pack):
    pack_byte(out, len(val))
    out.write(val)
def pack_bzstr8(out, val: bytes, __pack=structs_cache[u'=B'].pack):
    pack_byte(out, len(val) + 1)
    out.write(val)
    out.write(b'\x00')
def pack_byte_signed(out, value: int, __pack=structs_cache[u'b'].pack):
    out.write(__pack(value))

def unpack_many(ins, fmt: str):
    return struct_unpack(fmt, ins.read(struct.calcsize(fmt)))

def unpack_spaced_string(ins, replacement_char=b'\x07') -> bytes:
    """Unpacks a space-terminated string. Occurs if someone used
    std::stringstream to convert struct data into strings. Obviously that means
    a replacement character is needed for spaces, which is \x07 by default."""
    wip_string = []
    while True:
        next_char = ins.read(1)
        if next_char == b' ': break
        wip_string.append(b' ' if next_char == replacement_char else next_char)
    return b''.join(wip_string)

#------------------------------------------------------------------------------
class DataTable(DataDict):
    """Simple data table of rows and columns, saved in a pickle file. It is
    currently used by TableFileInfos to represent properties associated with
    mod/save/bsa/ini files, where each file is a row, and each property (e.g.
    modified date or 'mtime') is a column.

    The "table" is actually a dictionary of dictionaries. E.g.
        propValue = table['fileName']['propName']
    Rows are the first index ('fileName') and columns are the second index
    ('propName')."""

    def __init__(self, dictFile: PickleDict):
        """Initialize and read data from dictFile, if available."""
        self.dictFile = dictFile
        dictFile.load()
        self.vdata = dictFile.vdata
        self.dictFile.pickled_data = _data = forward_compat_path_to_fn(
            self.dictFile.pickled_data)
        super().__init__(_data)
        self.hasChanged = False ##: move to PickleDict

    def save(self):
        """Saves to pickle file."""
        dictFile = self.dictFile
        if self.hasChanged and not dictFile.readOnly:
            dictFile.pickled_data = self._data # note we reassign pickled_data
            self.hasChanged = not dictFile.save()

    #--Dictionary emulation
    def __setitem__(self,key,value):
        self._data[key] = value
        self.hasChanged = True
    def __delitem__(self,key):
        del self._data[key]
        self.hasChanged = True
    def pop(self,key,default=None):
        self.hasChanged = True
        return self._data.pop(key, default)

# Util Functions --------------------------------------------------------------
#------------------------------------------------------------------------------
def cmp_(x, y):
    """Compares x and y. For backwards compatibility since py3 drops cmp."""
    # TODO(lojack): Hunt down and rewrite any usages of this
    return (x > y) - (x < y)

class Rounder(float):
    """Float wrapper used for inexact comparison of float record elements."""
    __slots__ = ()

    #--Hash/Compare
    def __hash__(self):
        raise TypeError(f'unhashable type: {type(self)}')
    def __eq__(self, b, rel_tol=1e-06, abs_tol=1e-12):
        """Check if the two floats are equal to the sixth place (relatively)
        or to the twelfth place (absolutely). Note that these parameters
        were picked fairly arbitrarily, so feel free to tweak them if they
        turn out to be a problem.""" # PY3: drop in favor of math.isclose
        try:
            return abs(self - b) <= max(rel_tol * max(abs(self), abs(b)),
                                        abs_tol)
        except TypeError:
            return super(Rounder, self).__eq__(b)
    def __ne__(self, b, rel_tol=1e-06, abs_tol=1e-12):
        try:
            return abs(self - b) > max(rel_tol * max(abs(self), abs(b)),
                                       abs_tol)
        except TypeError:
            return super(Rounder, self).__ne__(b)
    def __lt__(self, other):
        return self != other and super(Rounder, self).__lt__(other)
    def __gt__(self, other):
        return self != other and super(Rounder, self).__gt__(other)
    def __le__(self, other):
        return self == other or super(Rounder, self).__lt__(other)
    def __ge__(self, other):
        return self == other or super(Rounder, self).__gt__(other)
    #--repr
    def __repr__(self):
        return f'{type(self).__name__}({super(Rounder, self).__repr__()})'
    def __str__(self):
        return f'{round(self, 6):.6f}'  # for writing out in csv

    # Action API --------------------------------------------------------------
    def dump(self): return self  ##: TODO round?

def cstrip(inString): # TODO(ut): hunt down and deprecate - it's O(n)+
    """Convert c-string (null-terminated string) to python string."""
    zeroDex = inString.find(b'\x00')
    if zeroDex == -1:
        return inString
    else:
        return inString[:zeroDex]

def text_wrap(text_to_wrap, width=60):
    """Wraps paragraph to width characters."""
    pars = [textwrap.fill(line, width) for line in text_to_wrap.split(u'\n')]
    return u'\n'.join(pars)

# Constants used for censoring the user's home directory (see below)
_USER_DIR = os.path.expanduser('~')
_CENSORED_DIR = os.path.join(os.path.split(_USER_DIR)[0], '*****')

def deprint(*args, traceback=False, trace=True, frame=1):
    """Prints message along with file and line location.
       Available keyword arguments:
       trace: (default True) - if a Truthy value, displays the module,
              line number, and function this was used from
       traceback: (default False) - if a Truthy value, prints any tracebacks
              for exceptions that have occurred.
       frame: (default 1) - With `trace`, determines the function caller's
              frame for getting the function name
    """
    if trace:
        # Warning: This may be CPython-only due to _getframe usage - if we ever
        # want to run on something besides CPython, add a fallback path that
        # uses the (much slower) inspect.stack() API
        parent_frame = sys._getframe(frame)
        code_obj = parent_frame.f_code
        msg = f'{os.path.basename(code_obj.co_filename)} ' \
              f'{parent_frame.f_lineno:4d} {code_obj.co_name}: '
    else:
        msg = u''
    try:
        msg += ' '.join([f'{x}' for x in args]) # OK, even with unicode args
    except UnicodeError:
        # If the args failed to convert to unicode for some reason
        # we still want the message displayed any way we can
        for x in args:
            try:
                msg += f' {x}'
            except UnicodeError:
                msg += f' {x!r}'
    # Print to stdout by default, but change to stderr if we have an error
    target_stream = sys.stdout
    if traceback:
        target_stream = sys.stderr
        exc_fmt = _traceback.format_exc()
        msg += f'\n{exc_fmt}'
    # Censor the user's home directory - we're on py3 now so no more need to
    # worry about unicode weirdness, this is now just a way for people to
    # unknowingly doxx themselves
    msg = msg.replace(_USER_DIR, _CENSORED_DIR)
    print(msg, flush=True, file=target_stream)

@contextmanager
def redirect_stdout_to_deprint(use_bytes=False):
    io_stream = (io.StringIO, io.BytesIO)[use_bytes]()
    with redirect_stdout(io_stream):
        yield
    # 1 = this function's frame
    # 2 = @contextmanager's frame
    # 3 = caller's frame
    # rstrip to remove newlines due to using io.<*>IO
    deprint(io_stream.getvalue().rstrip(), frame=3)

def getMatch(reMatch,group=0):
    """Returns the match or an empty string."""
    if reMatch: return reMatch.group(group)
    else: return u''

# Log/Progress ----------------------------------------------------------------
#------------------------------------------------------------------------------
class Log(object):
    """Log Callable. This is the abstract/null version. Useful version should
    override write functions.

    Log is divided into sections with headers. Header text is assigned (through
    setHeader), but isn't written until a message is written under it. I.e.,
    if no message are written under a given header, then the header itself is
    never written."""

    def __init__(self):
        """Initialize."""
        self.header = None
        self.prevHeader = None

    def setHeader(self,header,writeNow=False,doFooter=True):
        """Sets the header."""
        self.header = header
        if self.prevHeader:
            self.prevHeader += u'x'
        self.doFooter = doFooter
        if writeNow: self()

    def __call__(self,message=None,appendNewline=True):
        """Callable. Writes message, and if necessary, header and footer."""
        if self.header != self.prevHeader:
            if self.prevHeader and self.doFooter:
                self.writeFooter()
            if self.header:
                self.writeLogHeader(self.header)
            self.prevHeader = self.header
        if message: self.writeMessage(message,appendNewline)

    #--Abstract/null writing functions...
    def writeLogHeader(self, header):
        """Write header. Abstract/null version."""
        pass
    def writeFooter(self):
        """Write mess. Abstract/null version."""
        pass
    def writeMessage(self,message,appendNewline):
        """Write message to log. Abstract/null version."""
        pass

#------------------------------------------------------------------------------
class LogFile(Log):
    """Log that writes messages to file."""
    def __init__(self,out):
        self.out = out
        Log.__init__(self)

    def writeLogHeader(self, header):
        self.out.write(header+u'\n')

    def writeFooter(self):
        self.out.write(u'\n')

    def writeMessage(self,message,appendNewline):
        self.out.write(message)
        if appendNewline: self.out.write(u'\n')

#------------------------------------------------------------------------------
class Progress(object):
    """Progress Callable: Shows progress when called."""
    def __init__(self, full=1.0):
        if not full: raise exception.ArgumentError('Full must be non-zero!')
        self.message = ''
        self.full = 1.0 * full
        self.state = 0

    def getParent(self):
        return None

    def setFull(self, full):
        """Sets full and for convenience, returns self."""
        if not full: raise exception.ArgumentError('Full must be non-zero!')
        self.full = 1.0 * full
        return self

    def plus(self,increment=1):
        """Increments progress by 1."""
        self.__call__(self.state+increment)

    def __call__(self,state,message=u''):
        """Update progress with current state. Progress is state/full."""
        if self.full == 0:
            raise exception.ArgumentError('Full must be non-zero!')
        if message: self.message = message
        self._do_progress(1.0 * state / self.full, self.message)
        self.state = state

    def _do_progress(self, state, message):
        """Default _do_progress does nothing."""

    # __enter__ and __exit__ for use with the 'with' statement
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_value, exc_traceback): pass

#------------------------------------------------------------------------------
class SubProgress(Progress):
    """Sub progress goes from base to ceiling."""
    def __init__(self,parent,baseFrom=0.0,baseTo=u'+1',full=1.0,silent=False):
        """For creating a subprogress of another progress meter.
        progress: parent (base) progress meter
        baseFrom: Base progress when this progress == 0.
        baseTo: Base progress when this progress == full
          Usually a number. But string '+1' sets it to baseFrom + 1
        full: Full meter by this progress' scale."""
        Progress.__init__(self,full)
        if baseTo == u'+1': baseTo = baseFrom + 1
        if baseFrom < 0 or baseFrom >= baseTo:
            raise exception.ArgumentError(u'BaseFrom must be >= 0 and BaseTo must be > BaseFrom')
        self.parent = parent
        self.baseFrom = baseFrom
        self.scale = 1.0*(baseTo-baseFrom)
        self.silent = silent

    def __call__(self,state,message=u''):
        """Update progress with current state. Progress is state/full."""
        if self.silent: message = u''
        self.parent(self.baseFrom+self.scale*state/self.full,message)
        self.state = state

#------------------------------------------------------------------------------
def readCString(ins, file_path):
    """Read null terminated string, dropping the final null byte."""
    byte_list = []
    for b in iter(partial(ins.read, 1), b''):
        if b == b'\0': break
        byte_list.append(b)
    else:
        raise exception.FileError(file_path,
                                  u'Reached end of file while expecting null')
    return b''.join(byte_list)

class StringTable(dict):
    """For reading .STRINGS, .DLSTRINGS, .ILSTRINGS files."""
    encodings = {
        # Encoding to fall back to if UTF-8 fails, based on language
        # Default is 1252 (Western European), so only list languages
        # different than that
        u'russian': u'cp1251',
    }

    def loadFile(self, path, progress, lang=u'english'):
        formatted = path.cext != u'.strings'
        backupEncoding = self.encodings.get(lang.lower(), u'cp1252')
        try:
            # These may be extracted from a BSA, so their case may not match
            # what we expect at all
            from .env import canonize_ci_path
            canon_path = canonize_ci_path(path)
            with open(canon_path, u'rb') as ins:
                ins.seek(0, os.SEEK_END)
                eof = ins.tell()
                ins.seek(0)
                if eof < 8:
                    deprint(f"Warning: Strings file '{canon_path}' file size "
                            f"({canon_path}) is less than 8 bytes. 8 bytes "
                            f"are the minimum required by the expected "
                            f"format, assuming the Strings file is empty.")
                    return
                numIds,dataSize = unpack_many(ins, u'=2I')
                progress.setFull(max(numIds,1))
                stringsStart = 8 + (numIds*8)
                if stringsStart != eof-dataSize:
                    deprint(f"Warning: Strings file '{canon_path}' dataSize "
                            f"element ({dataSize}) results in a string start "
                            f"location of {eof - dataSize}, but the expected "
                            f"location is {stringsStart}")
                id_ = -1
                offset = -1
                for x in range(numIds):
                    try:
                        progress(x)
                        id_,offset = unpack_many(ins, u'=2I')
                        pos = ins.tell()
                        ins.seek(stringsStart + offset)
                        if formatted:
                            value = unpack_str32(ins) # TODO(ut): unpack_str32_null
                            # seems needed, strings are null terminated
                            value = cstrip(value)
                        else:
                            # drops the null byte
                            value = readCString(ins, canon_path)
                        try:
                            value = value.decode('utf-8')
                        except UnicodeDecodeError:
                            value = value.decode(backupEncoding)
                        ins.seek(pos)
                        self[id_] = value
                    except:
                        deprint('\n'.join(
                            ['Error reading string file:', f'id: {id_}',
                             f'offset: {offset}', f'filePos: {ins.tell()}']))
                        raise
        except:
            deprint(u'Error loading string file:', path.stail, traceback=True)
            return

#------------------------------------------------------------------------------
_esub_component = re.compile(r'\$(\d+)\(([^)]+)\)')
_rsub_component = re.compile(r'\\(\d+)')
_plain_component = re.compile(r'[^\\\$]+')

def build_esub(esub_str):
    r"""Builds an esub (enhanced substitution) callable and returns it. These
    expand normal re.sub syntax to allow the case of a match to be preserved,
    even while the letters change.

    The syntax looks like this:
        my_sub = build_esub('$1(s)tamina')
        print(re.sub(r'\b(f|F)atigue\b', my_sub, u'Fatigue'))
        # prints 'Stamina'

    The $1(s) part is what's important. The $1 identifies which regex group to
    target. The part in parentheses will be what the case of the group gets
    applied to."""
    # Callables we'll chain together at the end
    final_components = []
    i = 0
    while i < len(esub_str):
        esub_match = _esub_component.match(esub_str, i)
        if esub_match:
            # esub substitution - return the target string, with the case of
            # the wanted group's contents
            esub_group = int(esub_match.group(1))
            target_str = esub_match.group(2)
            def esub_impl(ma_obj, g=esub_group, s=target_str):
                wip_str = []
                wip_append = wip_str.append
                for t, o in zip(s, ma_obj.group(g)):
                    # Carry forward the target string, but keep the case
                    wip_append(t.upper() if o.isupper() else t.lower())
                # Add in the rest of the target string unchanged
                return u''.join(wip_str + list(s[len(wip_str):]))
            final_components.append(esub_impl)
            i = esub_match.end(0)
            continue # skip the other match attempts
        rsub_match = _rsub_component.match(esub_str, i)
        if rsub_match:
            # Regular substitution - return the wanted group's contents
            rsub_group = int(rsub_match.group(1))
            def rsub_impl(ma_obj, g=rsub_group):
                return ma_obj.group(g)
            final_components.append(rsub_impl)
            i = rsub_match.end(0)
            continue # skip the plain match attempt
        plain_match = _plain_component.match(esub_str, i)
        if plain_match:
            # Plain component, just return it unaltered (and make sure to
            # capture the value of group(0) so that plain_match can get GC'd)
            plain_contents = plain_match.group(0)
            final_components.append(lambda _ma_obj, p=plain_contents: p)
            i = plain_match.end(0)
            continue # skip the error check
        raise SyntaxError(f'Could not parse esub string {esub_str!r}')
    def final_impl(ma_obj):
        return u''.join(c(ma_obj) for c in final_components)
    return final_impl

#------------------------------------------------------------------------------
# We want record attributes to be ASCII
_valid_rpath_attr = re.compile(r'^[^\d\W]\w*\Z', re.ASCII)

class _ARP_Subpath(object):
    """Abstract base class for all subpaths of a larger record path."""
    __slots__ = ('_subpath_attr', '_next_subpath',)

    def __init__(self, sub_rpath: str, rest_rpath: str):
        if not _valid_rpath_attr.match(sub_rpath):
            raise SyntaxError(f"'{sub_rpath}' is not a valid subpath. "
                              f"Your record path likely contains a typo.")
        elif iskeyword(sub_rpath):
            raise SyntaxError(f"Record path subpaths may not be "
                              f"Python keywords (was '{sub_rpath}').")
        self._subpath_attr = sub_rpath
        self._next_subpath = _parse_rpath(rest_rpath)

    # See RecPath for documentation of these methods
    def rp_eval(self, record) -> list:
        raise NotImplementedError

    def rp_map(self, record, func, *args) -> None:
        raise NotImplementedError

class _RP_Subpath(_ARP_Subpath):
    """A simple, intermediate subpath. Simply forwards all calls to the next
    part of the record path."""
    def rp_eval(self, record) -> Iterable:
        try:
            return self._next_subpath.rp_eval(getattr(
                record, self._subpath_attr))
        except AttributeError: # if getattr returns None next rp_eval will blow
            return []

    def rp_map(self, record, func, *args) -> None:
        self._next_subpath.rp_map(getattr(record, self._subpath_attr), func,
                                  *args)

    def __repr__(self):
        return f'{self._subpath_attr}.{self._next_subpath!r}'

class _RP_LeafSubpath(_ARP_Subpath):
    """The final part of a record path. This is the part that actually gets
    and sets values. Those values must be str instances."""

    def rp_eval(self, record):
        rec_val = getattr(record, self._subpath_attr, None)
        return [rec_val] if rec_val is not None else []

    def rp_map(self, record, func, *args) -> None:
        s_attr = self._subpath_attr
        rec_val = getattr(record, s_attr, None)
        if rec_val is not None:
            setattr(record, s_attr, func(*args, rec_val))

    def __repr__(self):
        return self._subpath_attr

class _RP_IteratedSubpath(_ARP_Subpath):
    """An iterated part of a record path, corresponding to a record attribute
    that holds a list of (Mel) objects. A record path can't resolve to more
    than one value unless it involves at least one of these."""
    def __init__(self, sub_rpath, rest_rpath):
        if not rest_rpath: raise SyntaxError('A RecPath may not end with an '
                                             'iterated subpath.')
        super().__init__(sub_rpath, rest_rpath)

    def rp_eval(self, record) -> Iterable:
        eval_next = self._next_subpath.rp_eval
        return chain(*map(eval_next, getattr(record, self._subpath_attr)))

    def rp_map(self, record, func, *args) -> None:
        map_next = self._next_subpath.rp_map
        for rec_element in getattr(record, self._subpath_attr):
            map_next(rec_element, func, *args)

    def __repr__(self):
        return f'{self._subpath_attr}[*].{self._next_subpath!r}'

class _RP_OptionalSubpath(_RP_Subpath):
    """An optional part of a record path. If it doesn't exist, mapping and
    evaluating will simply not continue past this part."""
    def __init__(self, sub_rpath, rest_rpath):
        if not rest_rpath: raise SyntaxError('A RecPath may not end with an '
                                             'optional subpath.')
        super().__init__(sub_rpath, rest_rpath)

    def rp_eval(self, record) -> Iterable:
        try:
            return super().rp_eval(record)
        except AttributeError:
            return [] # Attribute did not exist, rest of the path evals to []

    def rp_map(self, record, func, *args) -> None:
        try:
            super().rp_map(record, func, *args)
        except AttributeError:
            pass # Attribute did not exist, can't map any further

    def __repr__(self):
        return f'{self._subpath_attr}?.{self._next_subpath!r}'

class RecPath(object):
    """Record paths (or 'rpaths' for short) provide a way to get and set
    attributes from a record, even if the way to those attributes is very
    complex (e.g. contains repeated or optional attributes). Does quite a bit
    of validation and preprocessing, making it much faster and safer than a
    'naive' solution. See the wiki page '[dev] Record Paths' for a full
    overview of syntax and usage. Current implementation supports paths to
    record attributes of type str, using None to signal the absence of the
    attribute."""
    __slots__ = ('_root_subpath',)

    def __init__(self, rpath_str: str):
        self._root_subpath = _parse_rpath(rpath_str)

    def rp_eval(self, record) -> Iterable:
        """Evaluates this record path for the specified record, returning a
        list of all attribute values that it resolved to."""
        return self._root_subpath.rp_eval(record)

    def rp_map(self, record, func, *args) -> None:
        """Maps the specified function over all the values that this record
        path points to and assigns the altered values to the corresponding
        attributes on the specified record. *args is an array of arguments
        for func that are passed first, followed by the record value, as in
        func(*args, rec_val)"""
        self._root_subpath.rp_map(record, func, *args)

    def __repr__(self):
        return repr(self._root_subpath)

def _parse_rpath(rpath_str: str) -> _ARP_Subpath | None:
    """Parses the given unicode string as an RPath subpath."""
    if not rpath_str: return None
    sub_rpath, rest_rpath = (rpath_str.split('.', 1) if '.' in rpath_str
                             else (rpath_str, None))
    # Iterated subpath
    if sub_rpath.endswith('[*]'):
        return _RP_IteratedSubpath(sub_rpath[:-3], rest_rpath)
    # Optional subpath
    elif sub_rpath.endswith('?'):
        return _RP_OptionalSubpath(sub_rpath[:-1], rest_rpath)
    else:
        return (_RP_Subpath if rest_rpath else
                _RP_LeafSubpath)(sub_rpath, rest_rpath)

#------------------------------------------------------------------------------
_digit_re = re.compile('([0-9]+)')

def natural_key():
    """Returns a sort key for 'natural' sort order, i.e. similar to how most
    file managers display it - a1.png, a2.png, a10.png. Can handle both strings
    and paths. Inspired by
    https://blog.codinghorror.com/sorting-for-humans-natural-sort-order/."""
    def _to_cmp(sub_str):
        """Helper function that prepares substrings for comparison."""
        return int(sub_str) if sub_str.isdigit() else sub_str.lower()
    return lambda curr_str: [_to_cmp(s) for s in
                             _digit_re.split(f'{curr_str}')]

def dict_sort(di, *, key_f=None, values_dex=(), by_value=False, reverse=False):
    """WIP wrap common dict sorting patterns - key_f if passed takes
    precedence, then values_dex then by_value. Copies the keys."""
    if key_f is None:
        if values_dex:
            key_f = lambda k: tuple(di[k][x] for x in values_dex)
        elif by_value:
            key_f = lambda k: di[k]
    for k_ in sorted(di, key=key_f, reverse=reverse):
        yield k_, di[k_]

#------------------------------------------------------------------------------
def readme_url(mopy, advanced=False, skip_local=False):
    """Return the URL of the WB readme based on the specified Mopy folder. Note
    that skip_local is ignored on non-Windows systems, as the bug it works
    around only exists on Windows."""
    readme_name = (u'Wrye Bash Advanced Readme.html' if advanced else
                   u'Wrye Bash General Readme.html')
    readme = mopy.join(u'Docs', readme_name)
    skip_local = skip_local and os_name == 'nt' # Windows-only bug
    if not skip_local and readme.is_file():
        readme = u'file:///' + readme.s.replace(u'\\', u'/')
    else:
        # Fallback to hosted version
        readme = f'http://wrye-bash.github.io/docs/{readme_name}'
    return readme.replace(u' ', u'%20')

# Reflinks --------------------------------------------------------------------
if reflink is not None:
    def copy_or_reflink(a: str | os.PathLike, b: str | os.PathLike):
        """Behaves like shutil.copyfile, but uses a reflink if possible. See
        https://en.wikipedia.org/wiki/Data_deduplication#reflink for more
        information."""
        a, b = os.fspath(a), os.fspath(b) # reflink needs strings
        try:
            reflink(a, b)
        except (OSError, ReflinkImpossibleError, NotImplementedError):
            shutil.copyfile(a, b)
    def copy_or_reflink2(a: str | os.PathLike, b: str | os.PathLike):
        """Behaves like shutil.copy2, but uses a reflink if possible. See
        https://en.wikipedia.org/wiki/Data_deduplication#reflink for more
        information."""
        a, b = os.fspath(a), os.fspath(b) # reflink needs strings
        try:
            # Don't alter b itself in case we need to fall back to copy2
            if os.path.isdir(final_b := b):
                final_b = os.path.join(final_b, os.path.basename(a))
            reflink(a, final_b)
            shutil.copystat(a, final_b)
        except (OSError, ReflinkImpossibleError, NotImplementedError):
            shutil.copy2(a, b)
else:
    def copy_or_reflink(a: str | os.PathLike, b: str | os.PathLike):
        """Behaves like shutil.copyfile, but uses a reflink if possible. See
        https://en.wikipedia.org/wiki/Data_deduplication#reflink for more
        information."""
        shutil.copyfile(a, b)
    def copy_or_reflink2(a: str | os.PathLike, b: str | os.PathLike):
        """Behaves like shutil.copy2, but uses a reflink if possible. See
        https://en.wikipedia.org/wiki/Data_deduplication#reflink for more
        information."""
        shutil.copy2(a, b)
