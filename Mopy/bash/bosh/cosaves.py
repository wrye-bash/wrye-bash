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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Script extender cosave files. They are composed of a header and script
extender plugin chunks which, in turn are composed of chunks. We need to
read them to log stats and write them to remap espm masters. We only handle
renaming of the masters of the xSE plugin chunk itself and of the Pluggy chunk.
"""

import binascii
import re
import string
from itertools import imap
from . import AFile, bak_file_pattern
from ..bolt import sio, decode, encode, struct_pack, struct_unpack, \
    unpack_string, unpack_int, unpack_short, unpack_4s, unpack_byte, \
    unpack_str16, unpack_float, unpack_double, unpack_int_signed, unpack_str32
from ..exception import AbstractError, FileError, BoltError

__author__ = 'Infernio'

#------------------------------------------------------------------------------
# Utilities
def _pack(buff, fmt, *args): buff.write(struct_pack(fmt, *args))
_cosave_encoding = u'cp1252' # TODO Do Pluggy files use this encoding as well?
# decode() / encode() with _cosave_encoding as encoding
def _cosave_decode(byte_str): return decode(byte_str,
                                            encoding=_cosave_encoding)
def _cosave_encode(uni_str): return encode(uni_str,
                                           firstEncoding=_cosave_encoding)
# Convenient methods for reading and writing that use the methods from above
def _unpack_cosave_str16(ins): return _cosave_decode(unpack_str16(ins))
def _pack_cosave_str16(out, uni_str):
    _pack(out, '=H', len(uni_str))
    out.write(_cosave_encode(uni_str))
def _unpack_cosave_str32(ins): return _cosave_decode(unpack_str32(ins))
def _pack_cosave_str32(out, uni_str):
    _pack(out, '=I', len(uni_str))
    out.write(_cosave_encode(uni_str))

class _Remappable(object):
    """Mixin for objects inside cosaves that have to be updated when the names
    of one or more plugin files referenced in the cosave has been changed."""
    __slots__ = ()

    def remap_plugins(self, plugin_renames):
        """Remaps the names of relevant plugin entries in this object.

        :param plugin_renames: A dictionary containing the renames: key is the
            name of the plugin before the renaming, value is the name
            afterwards."""
        raise AbstractError()

class _Dumpable(object):
    """Mixin for objects inside cosaves that can be dumped to a log."""
    __slots__ = ()

    def dump_to_log(self, log, save_masters):
        """Dumps information from this object into the specified log.

        :param log: A bolt.Log instance to write to.
        :param save_masters: A list of the masters of the save file that this
            object's cosave belongs to."""
        raise AbstractError()

class _ChunkEntry(object):
    """Base class for chunk entries, which are an abstraction layer over a
    struct of data that is stored in a list inside a chunk. For example, a PLGN
    chunk stores several entries, all of which feature a byte, a short (if the
    byte is 0xFE) and a string. To make this more readable and understandable,
    a class called _xSEEntryPLGN is used to abstract away some complexity."""
    __slots__ = ()

    def write_entry(self, out):
        """Writes this entry to the specified output stream. This has to be
        implemented.

        :param out: The output stream to write to."""
        raise AbstractError()

    def entry_length(self):
        """Calculates the length of this entry, i.e. the length of the data
        that this entry abstracts over. Pluggy entries do not implement this,
        since Pluggy cosaves don't include any size or length fields for which
        this would be meaningful.

        :return: The calculated length (in bytes)."""
        raise AbstractError()

#------------------------------------------------------------------------------
# Headers
class _AHeader(_Dumpable):
    """Abstract base class for cosave headers."""
    savefile_tag = u'OVERRIDE'
    __slots__ = ()

    def __init__(self, ins, cosave_path):
        """The base constructor for headers checks if the expected save file
        tag for this header matches the actual tag found in the file.

        :param ins: The input stream to read from.
        :param cosave_path: The path to the cosave."""
        actual_tag = _cosave_decode(unpack_string(ins, len(self.savefile_tag)))
        if actual_tag != self.savefile_tag:
            raise FileError(cosave_path.tail, u'Header tag wrong: got %s, but '
                                              u'expected %s' %
                            (actual_tag, self.savefile_tag))

    def write_header(self, out):
        """Writes this header to the specified output stream. The base method
        just writes the save file tag.

        :param out: The output stream to write to."""
        out.write(_cosave_encode(self.savefile_tag))

    def dump_to_log(self, log, save_masters):
        log.setHeader(_(u'%s Header') % self.savefile_tag)
        log(u'=' * 40)

class _xSEHeader(_AHeader):
    """Header for xSE cosaves."""
    __slots__ = ('format_version', 'se_version', 'se_minor_version',
                 'game_version', 'num_plugin_chunks')

    # num_plugin_chunks is the number of xSE plugin chunks contained in the
    # cosave. Note that xSE itself also counts as one!
    def __init__(self, ins, cosave_path):
        super(_xSEHeader, self).__init__(ins, cosave_path)
        self.format_version = unpack_int(ins)
        self.se_version = unpack_short(ins)
        self.se_minor_version = unpack_short(ins)
        self.game_version = unpack_int(ins)
        self.num_plugin_chunks = unpack_int(ins)

    def write_header(self, out):
        super(_xSEHeader, self).write_header(out)
        _pack(out, '=I', self.format_version)
        _pack(out, '=H', self.se_version)
        _pack(out, '=H', self.se_minor_version)
        _pack(out, '=I', self.game_version)
        _pack(out, '=I', self.num_plugin_chunks)

    def dump_to_log(self, log, save_masters):
        super(_xSEHeader, self).dump_to_log(log, save_masters)
        log(_(u'  Format version:   0x%08X') % self.format_version)
        log(_(u'  %s version:      %u.%u') % (self.savefile_tag,
                                              self.se_version,
                                              self.se_minor_version))
        log(_(u'  Game version:     0x%08X') % self.game_version)

class _PluggyHeader(_AHeader):
    """Header for pluggy cosaves. Just checks save file tag and version."""
    savefile_tag = u'PluggySave'
    _max_supported_version = 0x01050001
    _min_supported_version = 0x01040000
    __slots__ = ()

    def __init__(self, ins, cosave_path):
        super(_PluggyHeader, self).__init__(ins, cosave_path)
        version = unpack_int(ins)
        if version > self._max_supported_version:
            raise FileError(cosave_path.tail, u'Version of pluggy save file'
                                              u'format is too new - only'
                                              u'versions up to 1.6.0000 are'
                                              u'supported.')
        elif version < self._min_supported_version:
            raise FileError(cosave_path.tail, u'Version of pluggy save file'
                                              u'format is too old - only'
                                              u'versions >= 1.4.0000 are'
                                              u'supported.')

    def write_header(self, out):
        super(_PluggyHeader, self).write_header(out)
        _pack(out, '=I', self._max_supported_version)

    def dump_to_log(self, log, save_masters):
        super(_PluggyHeader, self).dump_to_log(log, save_masters)
        log(_(u'  Pluggy file format version: 0x%08X') %
            self._max_supported_version)

#------------------------------------------------------------------------------
# Chunks
class _AChunk(object):
    """Abstract base class for chunks."""
    __slots__ = ()

    def write_chunk(self, out):
        """Writes this chunk to the specified output stream.

        :param out: The output stream to write to."""

#------------------------------------------------------------------------------
# xSE Chunks
class _xSEChunk(_AChunk):
    """Base class for xSE chunks. Not abstract, this actually implements
    fallback read/write functionality that treats unknown chunks as binary
    blobs."""
    # Whether or not we've fully decoded this chunk. If that is the case, the
    # fallback functionality is disabled.
    _fully_decoded = False
    __slots__ = ('chunk_type', 'chunk_version', 'chunk_data')

    def __init__(self, ins, chunk_type):
        self.chunk_type = chunk_type
        self.chunk_version = unpack_int(ins)
        data_len = unpack_int(ins)
        # If we haven't fully decoded this chunk, treat it as a binary blob
        if not self._fully_decoded:
            self.chunk_data = ins.read(data_len)

    def write_chunk(self, out):
        # Don't forget to reverse signature when writing again
        _pack(out, '=4s', _cosave_encode(self.chunk_type[::-1]))
        _pack(out, '=I', self.chunk_version)
        _pack(out, '=I', self.chunk_length())
        # If we haven't fully decoded this chunk, treat it as a binary blob
        if not self._fully_decoded:
            out.write(self.chunk_data)

    # TODO(inf) This is a prime target for refactoring in 308+
    # A lot of it could be auto-calculated
    def chunk_length(self):
        """Calculates the length of this chunk, i.e. the length of the data
        that follows after this chunk's header. Fully decoded chunks must
        override this, otherwise an AbstractError will be raised.

        :return: The calculated length (in bytes)."""
        # Let's be defensive here - will minimally slow us down to check this,
        # but enforcing your API is good practice
        if self._fully_decoded: raise AbstractError()
        return len(self.chunk_data)

class _xSEModListChunk(_xSEChunk, _Dumpable, _Remappable):
    """An abstract class for chunks that contain a list of mods (e.g. MODS or
    LIMD) """
    __slots__ = ('mod_names',)

    def __init__(self, ins, chunk_type):
        super(_xSEModListChunk, self).__init__(ins, chunk_type)
        self.mod_names = []

    def read_mod_names(self, ins, mod_count):
        """
        Reads a list of mod names with length mod_count from the specified
        input stream. The result is saved in the mod_names variable.

        :param ins: The input stream to read from.
        :param mod_count: The number of mod names to read.
        """
        for x in xrange(mod_count):
            self.mod_names.append(_unpack_cosave_str16(ins))

    def write_mod_names(self, out):
        """
        Writes the saved list of mod names to the specified output stream.

        :param out: The output stream to write to.
        """
        for mod_name in self.mod_names:
            _pack_cosave_str16(out, mod_name)

    def chunk_length(self):
        # 2 bytes per mod name (for the length)
        total_len = len(self.mod_names) * 2
        total_len += sum(imap(len, self.mod_names))
        return total_len

    def dump_to_log(self, log, save_masters):
        for mod_name in self.mod_names:
            log(_(u'    - %s') % mod_name)

    def remap_plugins(self, plugin_renames):
        self.mod_names = [plugin_renames.get(x, x) for x in self.mod_names]

class _xSEChunkARVR(_xSEChunk, _Dumpable):
    """An ARVR (Array Variable) chunk. Only available in OBSE and NVSE. See
    ArrayVar.h in xSE's source code for the specification."""
    _fully_decoded = True
    __slots__ = ('_key_type', 'mod_index', 'array_id', 'is_packed',
                 'references', 'elements')

    class _xSEEntryARVR(_ChunkEntry, _Dumpable):
        """A single ARVR entry. An ARVR chunk contains several of these."""
        __slots__ = ('_key_type', 'key', 'element_type', 'stored_data')

        def __init__(self, ins, key_type):
            if key_type == 1:
                self.key = unpack_double(ins)
            elif key_type == 3:
                self.key = _unpack_cosave_str16(ins)
            else:
                raise RuntimeError(u'Unknown or unsupported key type %u.' %
                                   key_type)
            self._key_type = key_type
            self.element_type = unpack_byte(ins)
            if self.element_type == 1:
                self.stored_data = unpack_double(ins)
            elif self.element_type in (2, 4):
                self.stored_data = unpack_int(ins)
            elif self.element_type == 3:
                self.stored_data = _unpack_cosave_str16(ins)
            else:
                raise RuntimeError(u'Unknown or unsupported element type %u.' %
                                   self.element_type)

        def write_entry(self, out):
            if self._key_type == 1:
                _pack(out, '=d', self.key)
            elif self._key_type == 3:
                _pack_cosave_str16(out, self.key)
            else:
                raise RuntimeError(u'Unknown or unsupported key type %u.' %
                                   self._key_type)
            _pack(out, '=B', self.element_type)
            if self.element_type == 1:
                _pack(out, '=d', self.stored_data)
            elif self.element_type in (2, 4):
                _pack(out, '=I', self.stored_data)
            elif self.element_type == 3:
                _pack_cosave_str16(out, self.stored_data)
            else:
                raise RuntimeError(u'Unknown or unsupported element type %u.' %
                                   self.element_type)

        def entry_length(self):
            # element_type is B, key is either d or H + str
            total_len = 1 + (8 if self._key_type == 1 else 2 + len(self.key))
            if self.element_type == 1:
                total_len += 8
            elif self.element_type in (2, 4):
                total_len += 4
            elif self.element_type == 3:
                total_len += 2 + len(self.stored_data)
            return total_len

        def dump_to_log(self, log, save_masters):
            if self._key_type == 1:
                key_str = u'%f' % self.key
            elif self._key_type == 3:
                key_str = self.key
            else:
                key_str = u'BAD'
            if self.element_type == 1:
                data_str = u'%f' % self.stored_data
                type_str = u'NUM'
            elif self.element_type == 2:
                data_str = u'0x%08X' % self.stored_data
                type_str = u'REF'
            elif self.element_type == 3:
                data_str = self.stored_data
                type_str = u'STR'
            elif self.element_type == 4:
                data_str = u'%u' % self.stored_data
                type_str = u'ARR'
            else:
                data_str = u'UNKNOWN'
                type_str = u'BAD'
            log(u'    - [%s]:%s = %s' % (key_str, type_str, data_str))

    def __init__(self, ins, chunk_type):
        super(_xSEChunkARVR, self).__init__(ins, chunk_type)
        self.elements = []
        self.mod_index = unpack_byte(ins)
        self.array_id = unpack_int(ins)
        self.key_type = unpack_byte(ins)
        self.is_packed = unpack_byte(ins)
        if self.chunk_version >= 1:
            num_references = unpack_int(ins)
            self.references = []
            for x in xrange(num_references):
                self.references.append(unpack_byte(ins))
        num_elements = unpack_int(ins)
        for x in xrange(num_elements):
            self.elements.append(self._xSEEntryARVR(ins, self.key_type))

    @property
    def key_type(self):
        """Returns the key type of this ARVR chunk.

        :return: The key type of this ARVR chunk."""
        return self._key_type

    @key_type.setter
    def key_type(self, new_key_type):
        """Changes the key type of this ARVR chunk.

        :param new_key_type: The key type to change to."""
        self._key_type = new_key_type
        # Need to update the cached information in the entries too
        for element in self.elements:
            element._key_type = new_key_type

    def write_chunk(self, out):
        super(_xSEChunkARVR, self).write_chunk(out)
        _pack(out, '=B', self.mod_index)
        _pack(out, '=I', self.array_id)
        _pack(out, '=B', self.key_type)
        _pack(out, '=B', self.is_packed)
        if self.chunk_version >= 1:
            _pack(out, '=I', len(self.references))
            for reference in self.references:
                _pack(out, '=B', reference)
        _pack(out, '=I', len(self.elements))
        for element in self.elements:
            element.write_entry(out)

    def chunk_length(self):
        # The ones that are always there (3*B, 2*I)
        total_len = 11
        if self.chunk_version >= 1:
            # Every reference is a byte
            total_len += 4 + len(self.references)
        total_len += sum(imap(lambda e: e.entry_length(), self.elements))
        return total_len

    def dump_to_log(self, log, save_masters):
        if self.mod_index == 255:
            log(_(u'   Mod :  %02X (Save File)') % self.mod_index)
        else:
            log(_(u'   Mod :  %02X (%s)') % (
                self.mod_index, save_masters[self.mod_index].s))
        log(_(u'   ID  :  %u') % self.array_id)
        if self.key_type == 1: #Numeric
            if self.is_packed:
                log(_(u'   Type:  Array'))
            else:
                log(_(u'   Type:  Map'))
        elif self.key_type == 3:
            log(_(u'   Type:  StringMap'))
        else:
            log(_(u'   Type:  Unknown'))
        if self.chunk_version >= 1:
            log(u'   Refs:')
            for refModID in self.references:
                if refModID == 255:
                    log(_(u'    - %02X (Save File)') % refModID)
                else:
                    log(u'    - %02X (%s)' % (refModID,
                                              save_masters[refModID].s))
        log(_(u'   Size:  %u') % len(self.elements))
        for element in self.elements:
            element.dump_to_log(log, save_masters)

class _xSEChunkLIMD(_xSEModListChunk):
    """An LIMD (Light Mod Files) chunk. Available for SKSE64 and F4SE. This is
    the new version of the LMOD chunk. In contrast to LMOD, LIMD can store
    more than 255 light mods (up to 65535). However, for SKSE64, this chunk has
    now been deprecated, along with the MODS chunk, in favor of the PLGN chunk.
    New versions of SKSE64 no longer generate it. See Core_Serialization.cpp or
    InternalSerialization.cpp for its creation (no specification available)."""
    _fully_decoded = True
    __slots__ = ()

    def __init__(self, ins, chunk_type):
        super(_xSEChunkLIMD, self).__init__(ins, chunk_type)
        self.read_mod_names(ins, unpack_short(ins))

    def write_chunk(self, out):
        super(_xSEChunkLIMD, self).write_chunk(out)
        _pack(out, '=H', len(self.mod_names))
        self.write_mod_names(out)

    def chunk_length(self):
        return 2 + super(_xSEChunkLIMD, self).chunk_length()

    def dump_to_log(self, log, save_masters):
        log(_(u'   %u loaded light mods:') % len(self.mod_names))
        super(_xSEChunkLIMD, self).dump_to_log(log, save_masters)

class _xSEChunkLMOD(_xSEModListChunk):
    """An LMOD (Light Mod Files) chunk. Only available in SKSE64 and F4SE. This
    is the legacy version of the LIMD chunk, which is no longer generated by
    newer xSE versions. The difference is that this one only supported up to
    255 light mods, while the games themselves support more than that."""
    _fully_decoded = True
    __slots__ = ()

    def __init__(self, ins, chunk_type):
        super(_xSEChunkLMOD, self).__init__(ins, chunk_type)
        self.read_mod_names(ins, unpack_byte(ins))

    def write_chunk(self, out):
        super(_xSEChunkLMOD, self).write_chunk(out)
        _pack(out, '=B', len(self.mod_names))
        self.write_mod_names(out)

    def chunk_length(self):
        return 1 + super(_xSEChunkLMOD, self).chunk_length()

    def dump_to_log(self, log, save_masters):
        log(_(u'   %u loaded light mods:') % len(self.mod_names))
        super(_xSEChunkLMOD, self).dump_to_log(log, save_masters)

class _xSEChunkMODS(_xSEModListChunk):
    """A MODS (Mod Files) chunk. For SKSE64, this chunk has now been
    deprecated, along with the LIMD chunk, in favor of the PLGN chunk. New
    versions of SKSE64 no longer generate it. Otherwise, it is available for
    all script extenders. See Core_Serialization.cpp or
    InternalSerialization.cpp for its creation (no specification available)."""
    _fully_decoded = True
    __slots__ = ()

    def __init__(self, ins, chunk_type):
        super(_xSEChunkMODS, self).__init__(ins, chunk_type)
        self.read_mod_names(ins, unpack_byte(ins))

    def write_chunk(self, out):
        super(_xSEChunkMODS, self).write_chunk(out)
        _pack(out, '=B', len(self.mod_names))
        self.write_mod_names(out)

    def chunk_length(self):
        return 1 + super(_xSEChunkMODS, self).chunk_length()

    def dump_to_log(self, log, save_masters):
        log(_(u'   %u loaded mods:') % len(self.mod_names))
        super(_xSEChunkMODS, self).dump_to_log(log, save_masters)

class _xSEChunkPLGN(_xSEChunk, _Dumpable, _Remappable):
    """A PLGN (Plugin List) chunk. Contains a list of all loaded plugins (i.e.
    mod files, both regular ones and light ones) in the correct order.
    This is information that cannot be obtained from the normal save file,
    which stores two independent lists for regular mods and light mods. This
    chunk is used by Wrye Bash to display the correct save master order for
    SSE. Only available for SKSE64. See InternalSerialization.cpp for its
    creation (no specification available)."""
    _fully_decoded = True
    __slots__ = ('mod_entries',)

    class _xSEEntryPLGN(_ChunkEntry, _Dumpable, _Remappable):
        """A single PLGN entry. A PLGN chunk contains several of these."""
        __slots__ = ('mod_index', 'light_index', 'mod_name')

        def __init__(self, ins):
            self.mod_index = unpack_byte(ins)
            if self.mod_index == 0xFE:
                # This is a light mod (i.e. it has the ESL flag set)
                self.light_index = unpack_short(ins)
            self.mod_name = _unpack_cosave_str16(ins)

        def write_entry(self, out):
            _pack(out, '=B', self.mod_index)
            if self.mod_index == 0xFE:
                _pack(out, '=H', self.light_index)
            _pack_cosave_str16(out, self.mod_name)

        def entry_length(self):
            # mod_index is B, light_index and len(mod_name) are H
            total_len = 5 if self.mod_index == 0xFE else 3
            return total_len + len(self.mod_name)

        def dump_to_log(self, log, save_masters):
            if self.mod_index != 0xFE:
                log(u'    %02X       -                    %s' % (
                    self.mod_index, self.mod_name))
            else:
                log(u'    %02X       %04X             %s' % (
                    self.mod_index, self.light_index, self.mod_name))

        def remap_plugins(self, plugin_renames):
            self.mod_name = plugin_renames.get(self.mod_name, self.mod_name)

    def __init__(self, ins, chunk_type):
        super(_xSEChunkPLGN, self).__init__(ins, chunk_type)
        self.mod_entries = []
        for x in xrange(unpack_short(ins)):
            self.mod_entries.append(self._xSEEntryPLGN(ins))

    def write_chunk(self, out):
        super(_xSEChunkPLGN, self).write_chunk(out)
        _pack(out, '=H', len(self.mod_entries))
        for mod_entry in self.mod_entries:
            mod_entry.write_entry(out)

    def chunk_length(self):
        return 2 + sum(imap(lambda e: e.entry_length(), self.mod_entries))

    def dump_to_log(self, log, save_masters):
        log(_(u'   Current load order (%u plugins):') % len(self.mod_entries))
        log(_(u'    Index  Light Index  Plugin'))
        log(u'    ' + u'-' * 40)
        for mod_entry in self.mod_entries:
            mod_entry.dump_to_log(log, save_masters)

    def remap_plugins(self, plugin_renames):
        for mod_entry in self.mod_entries:
            mod_entry.remap_plugins(plugin_renames)

class _xSEChunkSTVR(_xSEChunk, _Dumpable):
    """An STVR (String Variable) chunk. Only available in OBSE and NVSE. See
    StringVar.h in xSE's source code for the specification."""
    _fully_decoded = True
    __slots__ = ('mod_index', 'string_id', 'string_data')

    def __init__(self, ins, chunk_type):
        super(_xSEChunkSTVR, self).__init__(ins, chunk_type)
        self.mod_index = unpack_byte(ins)
        self.string_id = unpack_int(ins)
        self.string_data = _unpack_cosave_str16(ins)

    def write_chunk(self, out):
        super(_xSEChunkSTVR, self).write_chunk(out)
        _pack(out, '=B', self.mod_index)
        _pack(out, '=I', self.string_id)
        _pack_cosave_str16(out, self.string_data)

    def chunk_length(self):
        return 7 + len(self.string_data)

    def dump_to_log(self, log, save_masters):
        log(_(u'   Mod : %02X (%s)') % (self.mod_index,
                                        save_masters[self.mod_index].s))
        log(_(u'   ID  : %u') % self.string_id)
        log(_(u'   Data: %s') % self.string_data)

# Maps all decoded xSE chunk types to the classes that implement them
_xse_class_dict = {
    u'ARVR': _xSEChunkARVR,
    u'LIMD': _xSEChunkLIMD,
    u'LMOD': _xSEChunkLMOD,
    u'MODS': _xSEChunkMODS,
    u'PLGN': _xSEChunkPLGN,
    u'STVR': _xSEChunkSTVR,
}

def _get_xse_chunk(ins):
    """Read a 4-byte string from the specified input stream and return an
    instance of a matching xSE chunk class for that string. If no matching
    class is found, an instance of the generic _xSEChunk class is returned
    instead.

    :param ins: The input stream to read from.
    :return: A instance of a matching chunk class, or the generic one if no
        matching class was found."""
    # The chunk type strings are reversed in the cosaves
    ch_type = _cosave_decode(unpack_4s(ins))[::-1]
    ch_class = _xse_class_dict.get(ch_type, _xSEChunk)
    return ch_class(ins, ch_type)

class _xSEPluginChunk(_AChunk, _Remappable):
    """A single xSE chunk, composed of _xSEChunk objects."""
    __slots__ = ('plugin_signature', 'chunks', 'remappable_chunks')

    def __init__(self, ins, light=False):
        self.plugin_signature = unpack_int(ins) # aka opcodeBase on pre papyrus
        num_chunks = unpack_int(ins)
        ins.read(4) # discard the size, we'll generate it when writing
        self.chunks = []
        self.remappable_chunks = []
        if light:
            self._read_chunk(ins)
        else:
            for x in xrange(num_chunks):
                self._read_chunk(ins)

    def _read_chunk(self, ins):
        """Reads a single chunk from the specified input stream and appends it
        to self.chunks and, if the chunk is remappable, to
        self.remappable_chunks.

        :param ins: The input stream to read from."""
        new_chunk = _get_xse_chunk(ins)
        self.chunks.append(new_chunk)
        if isinstance(new_chunk, _Remappable):
            self.remappable_chunks.append(new_chunk)

    def write_chunk(self, out):
        # Don't forget to reverse signature when writing again
        _pack(out, '=I', self.plugin_signature)
        _pack(out, '=I', len(self.chunks))
        _pack(out, '=I', self.chunk_length())
        for chunk in self.chunks:
            chunk.write_chunk(out)

    def chunk_length(self):
        # Every chunk header has a string of length 4 (type) and two integers
        # (version and length)
        total_len = 12 * len(self.chunks)
        for chunk in self.chunks:
            total_len += chunk.chunk_length()
        return total_len

    def remap_plugins(self, plugin_renames):
        for xse_chunk in self.remappable_chunks:
            xse_chunk.remap_plugins(plugin_renames)

#------------------------------------------------------------------------------
# Pluggy Chunks
class _PluggyBlock(_AChunk, _Dumpable):
    """A single pluggy records block. This is the pluggy equivalent of xSE
    chunks."""
    __slots__ = ('record_type',)

    def __init__(self, record_type):
        self.record_type = record_type

    def write_chunk(self, out):
        _pack(out, '=B', self.record_type)

    def unique_identifier(self):
        """Retrieves a unique identifier for this block. In most cases, this
        should simply be a human-understandable name for the block. An
        exception are the array blocks, since they may occur multiple times.

        :return: A human-understandable, unique identifier for this block."""
        raise AbstractError()

class _PluggyPluginBlock(_PluggyBlock, _Remappable):
    """The plugin records block of a pluggy cosave. Contains a list of the
    save's masters. This is the only required block, it must be present and is
    always the first block in the cosave."""
    __slots__ = ('plugins',)

    class _PluggyEntryPlugin(_ChunkEntry, _Dumpable, _Remappable):
        """A single Plugin entry. A Plugin block contains several of these."""
        __slots__ = ('pluggy_id', 'game_id', 'plugin_name')

        def __init__(self, ins):
            self.pluggy_id = unpack_byte(ins)
            self.game_id = unpack_byte(ins)
            self.plugin_name = _unpack_cosave_str32(ins)

        def write_entry(self, out):
            _pack(out, '=B', self.pluggy_id)
            _pack(out, '=B', self.game_id)
            _pack_cosave_str32(out, self.plugin_name)

        def remap_plugins(self, plugin_renames):
            self.plugin_name = plugin_renames.get(self.plugin_name,
                                                  self.plugin_name)

        def dump_to_log(self, log, save_masters):
            log(u'    %02X    %02X    %s' % (self.pluggy_id, self.game_id,
                                             self.plugin_name))

    def __init__(self, ins, record_type):
        super(_PluggyPluginBlock, self).__init__(record_type)
        plugin_count = unpack_int(ins)
        self.plugins = []
        for x in xrange(plugin_count):
            self.plugins.append(self._PluggyEntryPlugin(ins))

    def write_chunk(self, out):
        super(_PluggyPluginBlock, self).write_chunk(out)
        _pack(out, '=I', len(self.plugins))
        for plugin in self.plugins:
            plugin.write_entry(out)

    def dump_to_log(self, log, save_masters):
        log(_(u'   %u loaded mods:') % len(self.plugins))
        log(_(u'   EID   ID    Name'))
        log(u'   ' + u'-' * 40)
        for plugin in self.plugins:
            plugin.dump_to_log(log, save_masters)

    def remap_plugins(self, plugin_renames):
        for plugin in self.plugins:
            plugin.remap_plugins(plugin_renames)

    def unique_identifier(self):
        return _(u'Plugin Block')

class _PluggyStringBlock(_PluggyBlock):
    """The string records block of a pluggy cosave. Contains string data from
    plugins that was saved. This is an optional block and, if present, follows
    directly after the plugin block."""
    __slots__ = ('stored_strings',)

    class _PluggyEntryString(_ChunkEntry, _Dumpable):
        """A single String entry. A String block contains several of these."""
        __slots__ = ('string_id', 'plugin_index', 'string_flags',
                     'string_data')

        def __init__(self, ins):
            self.string_id = unpack_int(ins)
            self.plugin_index = unpack_byte(ins)
            self.string_flags = unpack_byte(ins)
            self.string_data = _unpack_cosave_str32(ins)

        def write_entry(self, out):
            _pack(out, '=I', self.string_id)
            _pack(out, '=B', self.plugin_index)
            _pack(out, '=B', self.string_flags)
            _pack_cosave_str32(out, self.string_data)

        def dump_to_log(self, log, save_masters):
            log(_(u'    - ID    : %u') % self.string_id)
            log(_(u'      Owner : %02X') % self.plugin_index)
            log(_(u'      Flags : %u') % self.string_flags)
            log(_(u'      Data  : %s') % self.string_data)

    def __init__(self, ins, record_type):
        super(_PluggyStringBlock, self).__init__(record_type)
        string_count = unpack_int(ins)
        self.stored_strings = []
        for x in xrange(string_count):
            self.stored_strings.append(self._PluggyEntryString(ins))

    def write_chunk(self, out):
        super(_PluggyStringBlock, self).write_chunk(out)
        _pack(out, '=I', len(self.stored_strings))
        for stored_string in self.stored_strings:
            stored_string.write_entry(out)

    def dump_to_log(self, log, save_masters):
        log(_(u'   %u stored strings:') % len(self.stored_strings))
        for stored_string in self.stored_strings:
            stored_string.dump_to_log(log, save_masters)

    def unique_identifier(self):
        return _(u'String Block')

class _PluggyArrayBlock(_PluggyBlock):
    """An array records block of a pluggy cosave. Contains an array from a
    plugin that was saved. This is an optional block and, if present, one or
    more of these (one for each saved array) follow directly after the string
    block."""
    __slots__ = ('array_id', 'plugin_index', 'array_flags', 'max_size',
                 'array_entries')

    class _PluggyEntryArray(_ChunkEntry, _Dumpable):
        """A single Array entry. An Array block contains several of these."""
        __slots__ = ('entry_index', 'entry_type', 'entry_data')

        def __init__(self, ins):
            self.entry_index = unpack_int(ins)
            self.entry_type = unpack_byte(ins)
            if self.entry_type == 0:
                self.entry_data = unpack_int_signed(ins)
            elif self.entry_type == 1:
                self.entry_data = unpack_int(ins)
            elif self.entry_type == 2:
                self.entry_data = unpack_float(ins)
            else:
                raise RuntimeError(u'Unknown or unsupported entry type %u.' %
                                   self.entry_type)

        def write_entry(self, out):
            _pack(out, '=I', self.entry_index)
            _pack(out, '=B', self.entry_type)
            if self.entry_type == 0:
                data_format = 'i'
            elif self.entry_type == 1:
                data_format = 'I'
            elif self.entry_type == 2:
                data_format = 'f'
            else:
                raise RuntimeError(u'Unknown or unsupported entry type %u.' %
                                   self.entry_type)
            _pack(out, '=' + data_format, self.entry_data)

        def dump_to_log(self, log, save_masters):
            if self.entry_type == 0:
                format_string = u'     %u: %d'
            elif self.entry_type == 1:
                format_string = u'     %u: 0x%08X'
            elif self.entry_type == 2:
                format_string = u'     %u: %f'
            else:
                raise RuntimeError(u'Unknown or unsupported entry type %u.' %
                                   self.entry_type)
            log(format_string % (self.entry_index, self.entry_data))

    def __init__(self, ins, record_type):
        super(_PluggyArrayBlock, self).__init__(record_type)
        self.array_id = unpack_int(ins)
        self.plugin_index = unpack_byte(ins)
        self.array_flags = unpack_byte(ins)
        self.max_size = unpack_int(ins)
        self.array_entries = []
        for x in xrange(unpack_int(ins)):
            self.array_entries.append(self._PluggyEntryArray(ins))

    def write_chunk(self, out):
        super(_PluggyArrayBlock, self).write_chunk(out)
        _pack(out, '=I', self.array_id)
        _pack(out, '=B', self.plugin_index)
        _pack(out, '=B', self.array_flags)
        _pack(out, '=I', self.max_size)
        _pack(out, '=I', len(self.array_entries))
        for array_entry in self.array_entries:
            array_entry.write_entry(out)

    def dump_to_log(self, log, save_masters):
        log(_(u'    Owner    : %02X') % self.plugin_index)
        log(_(u'    Flags      : %u') % self.array_flags)
        log(_(u'    Max Size: %u') % self.max_size)
        log(_(u'    Cur Size : %u') % len(self.array_entries))
        log(_(u'    Contents:'))
        for array_entry in self.array_entries:
            array_entry.dump_to_log(log, save_masters)

    def unique_identifier(self):
        return _(u'Array Block #%u') % self.array_id

class _PluggyNameBlock(_PluggyBlock):
    """A name records block of a pluggy cosave. Contains one or more names that
    were saved. This is an optional block and, if present, it follows directly
    after the array blocks."""
    __slots__ = ('stored_names',)

    class _PluggyEntryName(_ChunkEntry, _Dumpable):
        """A single Name entry. A Name block contains several of these."""
        __slots__ = ('reference_id', 'name_data')

        def __init__(self, ins):
            self.reference_id = unpack_int(ins)
            self.name_data = _unpack_cosave_str32(ins)

        def write_entry(self, out):
            _pack(out, '=I', self.reference_id)
            _pack_cosave_str32(out, self.name_data)

        def dump_to_log(self, log, save_masters):
            log(_(u'    - RefID : 0x%08X') % self.reference_id)
            printable_name = u''
            for c in self.name_data:
                # Strip non-printable characters
                ch = c if c in string.printable else u''
                printable_name = printable_name + ch
            log(_(u'      Name  : %s') % printable_name)

    def __init__(self, ins, record_type):
        super(_PluggyNameBlock, self).__init__(record_type)
        name_count = unpack_int(ins)
        self.stored_names = []
        for x in xrange(name_count):
            self.stored_names.append(self._PluggyEntryName(ins))

    def write_chunk(self, out):
        super(_PluggyNameBlock, self).write_chunk(out)
        _pack(out, '=I', len(self.stored_names))
        for stored_name in self.stored_names:
            stored_name.write_entry(out)

    def dump_to_log(self, log, save_masters):
        log(_(u'   %u stored names:') % len(self.stored_names))
        for stored_name in self.stored_names:
            stored_name.dump_to_log(log, save_masters)

    def unique_identifier(self):
        return _(u'Name Block')

class _PluggyScreenInfoBlock(_PluggyBlock):
    """A screen information record block. This is an optional block and, if
    present, follows directly after the name block. Note that this block will
    only ever be present if there is at least one HudS or HudT block."""
    __slots__ = ('screen_width', 'screen_height')

    def __init__(self, ins, record_type):
        super(_PluggyScreenInfoBlock, self).__init__(record_type)
        self.screen_width = unpack_int(ins)
        self.screen_height = unpack_int(ins)

    def write_chunk(self, out):
        super(_PluggyScreenInfoBlock, self).write_chunk(out)
        _pack(out, '=I', self.screen_width)
        _pack(out, '=I', self.screen_height)

    def dump_to_log(self, log, save_masters):
        log(_(u'   Width : %u') % self.screen_width)
        log(_(u'   Height: %u') % self.screen_height)

    def unique_identifier(self):
        return _(u'ScreenInfo Block')

class _PluggyHudSBlock(_PluggyBlock):
    """A HUD Screen / Image records block. Contains information related to
    custom HUDs that was saved. This is an optional block and, if present,
    follows directly after the screen info block."""
    __slots__ = ('hud_entries',)

    class _PluggyEntryHudS(_ChunkEntry, _Dumpable):
        """A single HudS entry. A HudS block contains several of these."""
        __slots__ = ('hud_id', 'plugin_index', 'hud_flags', 'root_id',
                     'file_name', 'show_mode', 'pos_x', 'pos_y', 'depth',
                     'scale_x', 'scale_y', 'alpha', 'alignment', 'auto_scale')

        def __init__(self, ins):
            self.hud_id = unpack_int(ins)
            self.plugin_index = unpack_byte(ins)
            self.hud_flags = unpack_byte(ins)
            self.root_id = unpack_byte(ins)
            self.file_name = _unpack_cosave_str32(ins)
            self.show_mode = unpack_byte(ins)
            self.pos_x = unpack_int(ins)
            self.pos_y = unpack_int(ins)
            self.depth = unpack_short(ins)
            self.scale_x = unpack_int(ins)
            self.scale_y = unpack_int(ins)
            ins.read(4) # Discard, unused
            self.alpha = unpack_byte(ins)
            self.alignment = unpack_byte(ins)
            self.auto_scale = unpack_byte(ins)

        def write_entry(self, out):
            _pack(out, '=I', self.hud_id)
            _pack(out, '=B', self.plugin_index)
            _pack(out, '=B', self.hud_flags)
            _pack(out, '=B', self.root_id)
            _pack_cosave_str32(out, self.file_name)
            _pack(out, '=B', self.show_mode)
            _pack(out, '=I', self.pos_x)
            _pack(out, '=I', self.pos_y)
            _pack(out, '=H', self.depth)
            _pack(out, '=I', self.scale_x)
            _pack(out, '=I', self.scale_y)
            _pack(out, '=I', 0) # Need to write this, but it's unused
            _pack(out, '=B', self.alpha)
            _pack(out, '=B', self.alignment)
            _pack(out, '=B', self.auto_scale)

        def dump_to_log(self, log, save_masters):
            log(_(u'    - HUD ID    : %u') % self.hud_id)
            log(_(u'      Owner     : %02X') % self.plugin_index)
            log(_(u'      Flags     : %02X') % self.hud_flags)
            log(_(u'      Root ID   : %u') % self.root_id)
            log(_(u'      File      : %s') % self.file_name)
            log(_(u'      Show Mode : %02X') % self.show_mode)
            log(_(u'      X Position: %u') % self.pos_x)
            log(_(u'      Y Position: %u') % self.pos_y)
            log(_(u'      Depth     : %u') % self.depth)
            log(_(u'      X Scale   : %u') % self.scale_x)
            log(_(u'      Y Scale   : %u') % self.scale_y)
            log(_(u'      Alpha     : %02X') % self.alpha)
            log(_(u'      Alignment : %02X') % self.alignment)
            log(_(u'      Auto-Scale: %02X') % self.auto_scale)

    def __init__(self, ins, record_type):
        super(_PluggyHudSBlock, self).__init__(record_type)
        self.hud_entries = []
        for x in xrange(unpack_int(ins)):
            self.hud_entries.append(self._PluggyEntryHudS(ins))

    def write_chunk(self, out):
        super(_PluggyHudSBlock, self).write_chunk(out)
        _pack(out, '=I', len(self.hud_entries))
        for hud_entry in self.hud_entries:
            hud_entry.write_entry(out)

    def dump_to_log(self, log, save_masters):
        log(_(u'   %u HUD Screen entries:') % len(self.hud_entries))
        for hud_entry in self.hud_entries:
            hud_entry.dump_to_log(log, save_masters)

    def unique_identifier(self):
        return _(u'HudS Block')

class _PluggyHudTBlock(_PluggyBlock):
    """A HUD Text records block. Contains information related to custom HUDs
    that was saved. This is an optional block and, if present, follows directly
    after the HudS block."""
    __slots__ = ('hud_entries',)

    class _PluggyEntryHudT(_ChunkEntry, _Dumpable):
        """A single HudT entry. A HudT block contains several of these."""
        __slots__ = ('hud_id', 'plugin_index', 'hud_flags', 'show_mode',
                     'pos_x', 'pos_y', 'depth', 'scale_x', 'scale_y', 'alpha',
                     'alignment', 'auto_scale', 'hud_width', 'hud_height',
                     'text_format', 'font_name', 'text_data', 'font_height',
                     'font_width', 'font_boldness', 'font_italic', 'font_red',
                     'font_green', 'font_blue')

        def __init__(self, ins):
            self.hud_id = unpack_int(ins)
            self.plugin_index = unpack_byte(ins)
            self.hud_flags = unpack_byte(ins)
            self.show_mode = unpack_byte(ins)
            self.pos_x = unpack_int(ins)
            self.pos_y = unpack_int(ins)
            self.depth = unpack_short(ins)
            self.scale_x = unpack_int(ins)
            self.scale_y = unpack_int(ins)
            ins.read(4) # Discard, unused
            self.alpha = unpack_byte(ins)
            self.alignment = unpack_byte(ins)
            self.auto_scale = unpack_byte(ins)
            self.hud_width = unpack_int(ins)
            self.hud_height = unpack_int(ins)
            self.text_format = unpack_byte(ins)
            self.font_name = _unpack_cosave_str32(ins)
            self.text_data = _unpack_cosave_str32(ins)
            self.font_height = unpack_int(ins)
            self.font_width = unpack_int(ins)
            self.font_boldness = unpack_short(ins)
            self.font_italic = unpack_byte(ins)
            self.font_red = unpack_byte(ins)
            self.font_green = unpack_byte(ins)
            self.font_blue = unpack_byte(ins)

        def write_entry(self, out):
            _pack(out, '=I', self.hud_id)
            _pack(out, '=B', self.plugin_index)
            _pack(out, '=B', self.hud_flags)
            _pack(out, '=I', self.pos_x)
            _pack(out, '=I', self.pos_y)
            _pack(out, '=H', self.depth)
            _pack(out, '=I', self.scale_x)
            _pack(out, '=I', self.scale_y)
            _pack(out, '=I', 0) # Need to write this, but it's unused
            _pack(out, '=B', self.alpha)
            _pack(out, '=B', self.alignment)
            _pack(out, '=B', self.auto_scale)
            _pack(out, '=I', self.hud_width)
            _pack(out, '=I', self.hud_height)
            _pack(out, '=B', self.text_format)
            _pack_cosave_str32(out, self.font_name)
            _pack_cosave_str32(out, self.text_data)
            _pack(out, '=I', self.font_height)
            _pack(out, '=I', self.font_width)
            _pack(out, '=H', self.font_boldness)
            _pack(out, '=B', self.font_italic)
            _pack(out, '=B', self.font_red)
            _pack(out, '=B', self.font_green)
            _pack(out, '=B', self.font_blue)

        def dump_to_log(self, log, save_masters):
            log(_(u'    - HUD ID    : %u') % self.hud_id)
            log(_(u'      Owner     : %02X') % self.plugin_index)
            log(_(u'      Flags     : %02X') % self.hud_flags)
            log(_(u'      Show Mode : %02X') % self.show_mode)
            log(_(u'      X Position: %u') % self.pos_x)
            log(_(u'      Y Position: %u') % self.pos_y)
            log(_(u'      Depth     : %u') % self.depth)
            log(_(u'      X Scale   : %u') % self.scale_x)
            log(_(u'      Y Scale   : %u') % self.scale_y)
            log(_(u'      Alpha     : %02X') % self.alpha)
            log(_(u'      Alignment : %02X') % self.alignment)
            log(_(u'      Auto-Scale: %02X') % self.auto_scale)
            log(_(u'      HUD Width  : %u') % self.hud_width)
            log(_(u'      HUD Height : %u') % self.hud_height)
            log(_(u'      Text Format: %u') % self.text_format)
            log(_(u'      Font Name  : %s') % self.font_name)
            log(_(u'      Text Data  : %s') % self.text_data)
            log(_(u'      Font Width : %u') % self.font_width)
            log(_(u'      Font Height: %u') % self.font_height)
            log(_(u'      Boldness   : %u') % self.font_boldness)
            log(_(u'      Italic     : %u') % self.font_italic)
            log(_(u'      Font Color : (%u, %u, %u)') % (self.font_red,
                                                         self.font_green,
                                                         self.font_blue))

    def __init__(self, ins, record_type):
        super(_PluggyHudTBlock, self).__init__(record_type)
        self.hud_entries = []
        for x in xrange(unpack_int(ins)):
            self.hud_entries.append(self._PluggyEntryHudT(ins))

    def write_chunk(self, out):
        super(_PluggyHudTBlock, self).write_chunk(out)
        _pack(out, '=I', len(self.hud_entries))
        for hud_entry in self.hud_entries:
            hud_entry.write_entry(out)

    def dump_to_log(self, log, save_masters):
        log(_(u'   %u HUD Text entries:') % len(self.hud_entries))
        for hud_entry in self.hud_entries:
            hud_entry.dump_to_log(log, save_masters)

    def unique_identifier(self):
        return _(u'HudT Block')

#------------------------------------------------------------------------------
# Files
class ACosave(_Dumpable, _Remappable, AFile):
    """The abstract base class for all cosave files."""
    header_type = _AHeader
    cosave_ext = u''
    re_save = re.compile(u'') # parse savename to extract root component
    __slots__ = ('cosave_header', 'cosave_chunks', 'remappable_chunks',
                 'loading_state',)
    # loading_state is one of (0, 1, 2), where:
    #  0 means not loaded
    #  1 means the first cosave chunk (and the first chunk of that one, if
    #    applicable) has been loaded
    #  2 means the full cosave has been loaded

    def __init__(self, cosave_path):
        super(ACosave, self).__init__(cosave_path, raise_on_error=True)
        self.cosave_chunks = []
        self.remappable_chunks = []
        self.loading_state = 0 # cosaves are lazily initialized

    def read_cosave(self, light=False):
        """Reads the entire cosave, including header and body. If you have to
        control the entire loading procedure, you may have to override this.
        For example, the Pluggy save format is laid out in a way that requires
        skipping to the end to skip 12 bytes - otherwise, reading it is
        impossible.

        :param light: Whether or not to only load the first chunk of the file
            (and, if applicable, only the first chunk of that chunk)."""
        target_state = 1 if light else 2
        if self.loading_state < target_state:
            # Need to reset these to avoid adding duplicates
            self.cosave_chunks = []
            self.remappable_chunks = []
            with self.abs_path.open('rb') as ins:
                self._read_cosave_header(ins)
                self._read_cosave_body(ins, light)
            self.loading_state = target_state

    def _reset_cache(self, stat_tuple, load_cache):
        # Reset our loading state to 'unloaded', which will discard everything
        # when the next request is made to the cosave (see read_cosave above)
        self.loading_state = 0
        super(ACosave, self)._reset_cache(stat_tuple, load_cache)

    def _read_cosave_header(self, ins):
        """Reads and assigns the header of this cosave. You probably don't need
        to override this method.

        :param ins: The input stream to read from."""
        self.cosave_header = self.header_type(ins, self.abs_path)

    def _read_cosave_body(self, ins, light=False):
        """Reads the body of this cosave. The header is already read and
        assigned at this point, meaning that only the chunks have to be loaded.
        Some examples: for xSE cosaves, these are the 'plugin chunks'. For
        Pluggy cosaves, these are the 'record blocks'.

        The way to implement this method is to read and instantiate each chunk,
        and to then call _add_cosave_chunk() with the newly created chunk. This
        will properly set up the remappable_chunks list as well, allowing
        efficient remapping at runtime.

        :param ins: The input stream to read from.
        :param light: Whether or not to only load the first chunk of the file
            (and, if applicable, only the first cunk of that chunk)."""
        raise AbstractError()

    def _add_cosave_chunk(self, cosave_chunk):
        """Adds a new chunk to this cosave. Appends the specified chunk to the
        cosave_chunks list and, if it is remappable, to the remappable_chunks
        list.

        :param cosave_chunk: The chunk to add."""
        self.cosave_chunks.append(cosave_chunk)
        if isinstance(cosave_chunk, _Remappable):
            self.remappable_chunks.append(cosave_chunk)

    def write_cosave(self, out_path):
        """Writes this cosave to the specified path. Any changes that have been
        done to the cosave in-memory will be written out by this.

        :param out_path: The path to write to."""
        # We need the entire cosave to write
        self.read_cosave()

    def write_cosave_safe(self, out_path=u''):
        """Writes out any in-memory changes that have been made to this cosave
        to the specified path, first moving it to a temporary location to avoid
        overwriting the original file if something goes wrong.

        :param out_path: The path to write to. If empty or None, this cosave's
            own path is used instead."""
        out_path = out_path or self.abs_path
        self.write_cosave(out_path.temp)
        out_path.untemp()

    def get_master_list(self):
        """Retrieves a list of masters from this cosave. This will read an
        appropriate chunk and return a list of the masters from that chunk.

        :return: A list of the masters stored in this cosave."""

    def has_accurate_master_list(self, has_esl):
        """Checks whether or not this cosave contains an accurate master list -
        i.e. one that correctly represents the order of plugins as they were at
        the time that the save was taken. This is used to determine whether or
        not to use get_master_list for saves in SSE / FO4.

        :param has_esl: Whether or not the current game has ESL support. This
            should be set to the value of bush.game.has_esl.
        :return: True if the master list retrieved by get_master_list will be
            accurate."""

    def dump_to_log(self, log, save_masters):
        # We need the entire cosave to dump
        self.read_cosave()
        self.cosave_header.dump_to_log(log, save_masters)

    def remap_plugins(self, plugin_renames):
        # We need the entire cosave to remap
        self.read_cosave()
        for cosave_chunk in self.remappable_chunks:
            cosave_chunk.remap_plugins(plugin_renames)

    @classmethod
    def get_cosave_path(cls, save_path):
        """Return the cosave path corresponding to save_path. The save_path
        may be located in the backup directory and so it may end with an 'f'
        (for first backup) which should be appended to the cosave path also.

        :param save_path: The path to the save file that a cosave could belong
            to.
        :return: The path at which the cosave could exist.
        :rtype: bolt.Path"""
        maSave = cls.re_save.search(save_path.s)
        if maSave:
            first = maSave.group(2) or u''
            return save_path.root + cls.cosave_ext + first
        ma_bak = bak_file_pattern.search(save_path.s)
        if ma_bak:
            return save_path.head.join(ma_bak.group(1) + ma_bak.group(
                2) + cls.cosave_ext + ma_bak.group(3))
        raise BoltError(u'Invalid save path %s' % save_path)

class xSECosave(ACosave):
    """Represents an xSE cosave, with a .**se extension."""
    header_type = _xSEHeader
    _pluggy_signature = None # signature (aka opcodeBase) of Pluggy plugin
    _xse_signature = 0x1400 # signature (aka opcodeBase) of xSE plugin itself
    cosave_ext = u'' # set in the factory function
    __slots__ = ()

    def _read_cosave_body(self, ins, light=False):
        my_header = self.cosave_header # type: _xSEHeader
        if light:
            self._add_cosave_chunk(_xSEPluginChunk(ins, light))
        else:
            for x in xrange(my_header.num_plugin_chunks):
                self._add_cosave_chunk(_xSEPluginChunk(ins, light))

    def write_cosave(self, out_path):
        super(xSECosave, self).write_cosave(out_path)
        prev_mtime = self.abs_path.mtime
        with sio() as buff:
            # We have to update the number of chunks in the header here, since
            # that can't be done automatically
            my_header = self.cosave_header # type: _xSEHeader
            my_header.num_plugin_chunks = len(self.cosave_chunks)
            my_header.write_header(buff)
            for plugin_ch in self.cosave_chunks: # type: _xSEPluginChunk
                plugin_ch.write_chunk(buff)
            final_data = buff.getvalue()
        with out_path.open('wb') as out:
            out.write(final_data)
        out_path.mtime = prev_mtime

    def get_master_list(self):
        # We only need the first chunk to read the master list
        self.read_cosave(light=True)
        # The first chunk is either a PLGN chunk (on SKSE64) or a MODS one
        xse_chunks = self._get_xse_plugin().chunks
        first_chunk = xse_chunks[0]
        if first_chunk.chunk_type == u'PLGN':
            return [mod_entry.mod_name for mod_entry in
                    first_chunk.mod_entries]
        elif first_chunk.chunk_type == u'MODS':
            return first_chunk.mod_names
        raise FileError(self.abs_path.tail, u'Invalid or unsupported cosave: '
                                            u'First chunk was not PLGN or '
                                            u'MODS chunk.')

    def has_accurate_master_list(self, has_esl):
        if not has_esl:
            # On games without ESL support, we always have the MODS chunk,
            # which is accurate
            return True
        else:
            # Check the first chunk's signature. If and only if that signature
            # is PLGN can we accurately return a master list.
            self.read_cosave(light=True)
            first_ch = self._get_xse_plugin().chunks[0] # type: _xSEChunk
            return first_ch.chunk_type == u'PLGN'

    def dump_to_log(self, log, save_masters):
        super(xSECosave, self).dump_to_log(log, save_masters)
        for plugin_chunk in self.cosave_chunks: # type: _xSEPluginChunk
            plugin_sig = self._get_plugin_signature(plugin_chunk)
            log.setHeader(_(u'Plugin: %s, Total chunks: %u') % (
                plugin_sig, len(plugin_chunk.chunks)))
            log(u'=' * 40)
            log(_(u'  Type   Version  Size (in bytes)'))
            log(u'-' * 40)
            for chunk in plugin_chunk.chunks: # type: _xSEChunk
                log(u'  %4s  %-4u        %u' % (chunk.chunk_type,
                                                chunk.chunk_version,
                                                chunk.chunk_length()))
                if isinstance(chunk, _Dumpable):
                    chunk.dump_to_log(log, save_masters)

    # Helper methods
    def _get_plugin_signature(self, plugin_chunk):
        """Creates a human-readable version of the specified plugin chunk's
        signature.

        :param plugin_chunk: The plugin chunk whose signature should be
            processed.
        :return: A human-readable version of the plugin chunk's signature."""
        raw_sig = plugin_chunk.plugin_signature
        if raw_sig == self._xse_signature:
            readable_sig = self.cosave_header.savefile_tag
        elif raw_sig == self._pluggy_signature:
            readable_sig = u'Pluggy'
        else:
            # Reverse the result since xSE writes signatures backwards
            readable_sig = u''.join(
                [self._to_unichr(raw_sig, x) for x in [0, 8, 16, 24]])[::-1]
        return readable_sig + u' (0x%X)' % raw_sig

    @staticmethod
    def _to_unichr(target_int, shift):
        """Small helper method for _get_plugin_signature that interprets the
        result of shifting the specified integer by the specified shift amount
        and masking with 0xFF as a unichr. Additionally, if the result of that
        operation is not printable, an empty string is returned instead.

        :param target_int: The integer to shift and mask.
        :param shift: By how much (in bits) to shift.
        :return: The unichr representation of the result, or an empty
            string."""
        temp_char = unichr(target_int >> shift & 0xFF)
        if temp_char not in string.printable:
            temp_char = u''
        return temp_char

    def _get_xse_plugin(self):
        """Retrieves the plugin chunk for xSE itself from this cosave.

        :return: The plugin chunk for xSE itself."""
        for plugin_chunk in self.cosave_chunks: # type: _xSEPluginChunk
            if plugin_chunk.plugin_signature == self._xse_signature:
                return plugin_chunk
        # Something has gone seriously wrong, the xSE chunk _must_ be present
        raise FileError(self.abs_path.tail, u'Invalid cosave: xSE plugin '
                                            u'chunk is missing.')

class PluggyCosave(ACosave):
    """Represents a Pluggy cosave, with a .pluggy extension."""
    header_type = _PluggyHeader
    cosave_ext = u'.pluggy'
    # Used to convert from block type int to block class
    # See pluggy file format specification for how these map
    _block_types = [_PluggyPluginBlock, _PluggyStringBlock, _PluggyArrayBlock,
                    _PluggyNameBlock, _PluggyScreenInfoBlock, _PluggyHudSBlock,
                    _PluggyHudTBlock]
    __slots__ = ('save_game_ticks',)

    def __init__(self, cosave_path):
        super(PluggyCosave, self).__init__(cosave_path)
        self.save_game_ticks = 0

    def read_cosave(self, light=False):
        target_state = 1 if light else 2
        if self.loading_state < target_state:
            # Need to reset these to avoid adding duplicates
            self.cosave_chunks = []
            self.remappable_chunks = []
            # The Pluggy file format requires reading a file twice: once all
            # but the last 12 bytes, which is used for reading the header and
            # chunks, and once all but the last 4 bytes, for a CRC check.
            total_size = self.abs_path.size
            with self.abs_path.open('rb') as ins:
                # This is what we'll read the header and chunks from later.
                buffered_data = ins.read(total_size - 12)
                # These are compared by Pluggy to the ones in the matching .ess
                # file - we need to preserve them so that we can write them out
                # later.
                self.save_game_ticks = unpack_int(ins)
                # Check if the 'end control' is correctly set to match the
                # specification.
                actual_position = ins.tell()
                expected_position = unpack_int(ins)
                if actual_position != expected_position:
                    raise FileError(self.abs_path.tail,
                                    u'Invalid cosave: End control position was'
                                    u' incorrect (expected %u, but  got %u).' %
                                    (expected_position, actual_position))
                # Finally, check if the stored CRC matches the actual CRC of
                # all preceding data.
                ins.seek(0)
                checksum_data = ins.read(total_size - 4)
                expected_crc = unpack_int_signed(ins)
            actual_crc = binascii.crc32(checksum_data)
            if actual_crc != expected_crc:
                raise FileError(self.abs_path.tail,
                                u'Invalid cosave: Checksum does not match '
                                u'(expected %X, but got %X).' %
                                (expected_crc, actual_crc))
            with sio(buffered_data) as ins:
                self._read_cosave_header(ins)
                self._read_cosave_body(ins, light)
            self.loading_state = target_state

    def _read_cosave_body(self, ins, light=False):
        # At this point, the last 12 bytes are gone, meaning that we can
        # use read()'s return value to find out if we've hit EOF.
        raw_type = ins.read(1)
        while raw_type:
            record_type = struct_unpack('=B', raw_type)[0]
            block_type = self._get_block_type(record_type)
            self._add_cosave_chunk(block_type(ins, record_type))
            raw_type = ins.read(1)

    def _get_block_type(self, record_type):
        """Returns the matching block type for the specified record type or
        raises an informative error if the record type is not known.

        :param record_type: An integer representing the read record type."""
        try:
            return self._block_types[record_type]
        except IndexError:
            raise FileError(self.abs_path.tail, u'Unknown pluggy record block '
                                                u'type %u.' % record_type)

    def write_cosave(self, out_path):
        super(PluggyCosave, self).write_cosave(out_path)
        with sio() as out:
            self.cosave_header.write_header(out)
            for pluggy_block in self.cosave_chunks: # type: _PluggyBlock
                pluggy_block.write_chunk(out)
            # Write out the 'footer': Savegame Ticks and End Control - Checksum
            # is written down below
            _pack(out, '=I', self.save_game_ticks)
            _pack(out, '=I', out.tell())
            final_data = out.getvalue()
        prev_mtime = self.abs_path.mtime
        with out_path.open('wb') as out:
            out.write(final_data)
            _pack(out, '=i', binascii.crc32(final_data))
        out_path.mtime = prev_mtime

    def get_master_list(self):
        # We only need the first chunk to read the master list
        self.read_cosave(light=True)
        first_block = self.cosave_chunks[0] # type: _PluggyPluginBlock
        if first_block.record_type != 0:
            raise FileError(self.abs_path.tail, u'Invalid cosave: First '
                                                u'Pluggy block is not the '
                                                u'plugin block.')
        return [plugin.plugin_name for plugin in first_block.plugins]

    def has_accurate_master_list(self, has_esl):
        # Pluggy cosaves always have an accurate list since they only exist for
        # Oblivion, which does not have ESLs.
        return True

    def dump_to_log(self, log, save_masters):
        super(PluggyCosave, self).dump_to_log(log, save_masters)
        for pluggy_block in self.cosave_chunks: # type: _PluggyBlock
            log.setHeader(pluggy_block.unique_identifier())
            log(u'=' * 40)
            pluggy_block.dump_to_log(log, save_masters)

# Factory
def get_cosave_types(game_fsName, save_regex, cosave_tag, cosave_ext):
    """Factory method for retrieving the cosave types for the current game.
    Also sets up some class variables for xSE and Pluggy signatures.

    :param game_fsName: bush.game.fsName, the name of the current game.
    :param save_regex: SaveInfos.file_pattern.
    :param cosave_tag: bush.game.se.cosave_tag, the magic tag used to mark the
        cosave. Empty string if this game doesn't have cosaves.
    :param cosave_ext: bush.game.se.cosave_ext, the extension for cosaves.
    :return: A list of types of cosaves supported by this game.
    :rtype: list[type[ACosave]]"""
    # Check if the game even has a script extender
    if not cosave_tag: return []
    # Assign things that concern all games with script extenders
    _xSEHeader.savefile_tag = cosave_tag
    xSECosave.cosave_ext = cosave_ext
    ACosave.re_save = save_regex
    cosave_types = [xSECosave]
    # Handle game-specific special cases
    if game_fsName == u'Oblivion':
        xSECosave._pluggy_signature = 0x2330
        cosave_types.append(PluggyCosave)
    elif game_fsName not in (u'Fallout3', u'FalloutNV'):
        # Games >= Skyrim have 0 as the xSE signature
        xSECosave._xse_signature = 0x0
    return cosave_types
