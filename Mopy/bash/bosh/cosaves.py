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
"""Script extender cosave files. They are composed of a header and script
extender plugin chunks which, in turn are composed of chunks. We need to
read them to log stats and write them to remap espm masters. We only handle
renaming of the masters of the xSE plugin chunk itself and of the Pluggy
chunk."""
from __future__ import annotations

__author__ = u'Infernio'

import io
import string
from typing import get_type_hints
from zlib import crc32

from ..bolt import AFile, GPath, Path, decoder, deprint, encode, pack_4s, \
    pack_byte, pack_double, pack_float, pack_int, pack_int_signed, \
    pack_short, struct_error, struct_pack, struct_unpack, unpack_4s, \
    unpack_byte, unpack_double, unpack_float, unpack_int, unpack_int_signed, \
    unpack_short, unpack_spaced_string, unpack_str16, unpack_str32, \
    GPath_no_norm
from ..exception import BoltError, CosaveError, InvalidCosaveError, \
    UnsupportedCosaveError
from ..wbtemp import TempFile

# TODO(inf) All the chunk_length stuff needs to be reworked: first encode all
#  unicode strings, then measure the length of the byte sequence, then dump.
#  This then also means we can drop all the *_length methods entirely - nice
#  bit of refactoring

#------------------------------------------------------------------------------
# Utilities
_cosave_encoding = u'cp1252' # TODO Do Pluggy files use this encoding as well?
# decoder() / encode() with _cosave_encoding as encoding
def _cosave_decode(byte_str: bytes) -> str:
    return decoder(byte_str, encoding=_cosave_encoding)
def _cosave_encode(uni_str: str) -> bytes:
    return encode(uni_str, firstEncoding=_cosave_encoding)
# Convenient methods for reading and writing that use the methods from above
def _unpack_cosave_str16(ins): return _cosave_decode(unpack_str16(ins))
def _pack_cosave_str16(out, uni_str: str):
    pack_short(out, len(uni_str))
    out.write(_cosave_encode(uni_str))
def _unpack_cosave_str32(ins): return _cosave_decode(unpack_str32(ins))
def _pack_cosave_str32(out, uni_str: str):
    pack_int(out, len(uni_str))
    out.write(_cosave_encode(uni_str))
def _unpack_cosave_space_str(ins):
    return _cosave_decode(unpack_spaced_string(ins))
def _pack_cosave_space_str(out, uni_str: str):
    out.write(_cosave_encode(uni_str).replace(b' ', b'\x07') + b' ')

class _Remappable(object):
    """Mixin for objects inside cosaves that have to be updated when the names
    of one or more plugin files referenced in the cosave has been changed."""
    __slots__ = ()

    def remap_plugins(self, fnmod_rename: dict[str, str]):
        """Remaps the names of relevant plugin entries in this object.

        :param fnmod_rename: A dictionary containing the renames: key is the
            name of the plugin before the renaming, value is the name
            afterwards."""
        raise NotImplementedError

class _Dumpable(object):
    """Mixin for objects inside cosaves that can be dumped to a log."""
    __slots__ = ()

    def dump_to_log(self, log, save_masters_):
        """Dumps information from this object into the specified log.

        :param log: A bolt.Log instance to write to.
        :param save_masters_: A list of the masters of the save file that this
            object's cosave belongs to."""
        raise NotImplementedError

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
        raise NotImplementedError

    def entry_length(self) -> int:
        """Calculates the length of this entry, i.e. the length of the data
        that this entry abstracts over. Pluggy entries do not implement this,
        since Pluggy cosaves don't include any size or length fields for which
        this would be meaningful.

        :return: The calculated length (in bytes)."""
        raise NotImplementedError

#------------------------------------------------------------------------------
# Headers
class _AHeader(_Dumpable):
    """Abstract base class for cosave headers."""
    savefile_tag = u'OVERRIDE'
    __slots__ = ()

    def __init__(self, ins, cosave_name):
        """The base constructor for headers checks if the expected save file
        tag for this header matches the actual tag found in the file.

        :param ins: The input stream to read from.
        :param cosave_name: The filename of the cosave for error messages."""
        actual_tag = _cosave_decode(ins.read(len(self.savefile_tag)))
        if actual_tag != self.savefile_tag:
            raise InvalidCosaveError(cosave_name,
                                     f'Header tag wrong: got {actual_tag}, '
                                     f'but expected {self.savefile_tag}')

    def write_header(self, out):
        """Writes this header to the specified output stream. The base method
        just writes the save file tag.

        :param out: The output stream to write to."""
        out.write(_cosave_encode(self.savefile_tag))

    def dump_to_log(self, log, save_masters_):
        log.setHeader(_('%(cosave_file_tag)s Header') % {
            'cosave_file_tag': self.savefile_tag})
        log('=' * 40)

class _xSEHeader(_AHeader):
    """Header for xSE cosaves."""
    __slots__ = ('format_version', 'se_version', 'se_minor_version',
                 'game_version', 'num_plugin_chunks')

    # num_plugin_chunks is the number of xSE plugin chunks contained in the
    # cosave. Note that xSE itself also counts as one!
    def __init__(self, ins, cosave_path):
        super().__init__(ins, cosave_path)
        self.format_version = unpack_int(ins)
        self.se_version = unpack_short(ins)
        self.se_minor_version = unpack_short(ins)
        self.game_version = unpack_int(ins)
        self.num_plugin_chunks = unpack_int(ins)

    def write_header(self, out):
        super().write_header(out)
        pack_int(out, self.format_version)
        pack_short(out, self.se_version)
        pack_short(out, self.se_minor_version)
        pack_int(out, self.game_version)
        pack_int(out, self.num_plugin_chunks)

    def dump_to_log(self, log, save_masters_):
        super().dump_to_log(log, save_masters_)
        log('  ' + _('Format version: %(co_format_ver)s') % {
            'co_format_ver': f'0x{self.format_version:08X}',
        })
        log('  ' + _('%(co_file_tag)s version: '
                     '%(co_main_record_ver)s') % {
            'co_file_tag': self.savefile_tag,
            'co_main_record_ver': f'{self.se_version}.{self.se_minor_version}',
        })
        log('  ' + _('Game version: %(stored_game_ver)s') % {
            'stored_game_ver': self.game_version})

class _PluggyHeader(_AHeader):
    """Header for pluggy cosaves. Just checks save file tag and version."""
    savefile_tag = u'PluggySave'
    _max_supported_version = 0x01050001
    _min_supported_version = 0x01040000
    __slots__ = ('_pluggy_format_version',)

    def __init__(self, ins, cosave_path):
        super().__init__(ins, cosave_path)
        self._pluggy_format_version = unpack_int(ins)
        if self._pluggy_format_version > self._max_supported_version:
            raise UnsupportedCosaveError(cosave_path,
                f'Version of pluggy save file format is too new - only '
                f'versions <= 1.6.0000 are supported.')
        elif self._pluggy_format_version < self._min_supported_version:
            raise UnsupportedCosaveError(cosave_path,
                'Version of pluggy save file format is too old - only '
                'versions >= 1.4.0000 are supported.')

    def write_header(self, out):
        super().write_header(out)
        pack_int(out, self._max_supported_version)

    def dump_to_log(self, log, save_masters_):
        super().dump_to_log(log, save_masters_)
        log('  ' + _('Pluggy file format version: %(co_format_ver)s') % {
            'co_format_ver': f'0x{self._pluggy_format_version:08X}'})

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
    fully_decoded = False
    __slots__ = (u'chunk_type', u'chunk_version', u'data_len', u'chunk_data')

    def __init__(self, ins, chunk_type: str):
        self.chunk_type = chunk_type
        self.chunk_version = unpack_int(ins)
        self.data_len = unpack_int(ins)
        # If we haven't fully decoded this chunk, treat it as a binary blob
        if not self.fully_decoded:
            self.chunk_data = ins.read(self.data_len)

    def write_chunk(self, out):
        # Don't forget to reverse signature when writing again
        pack_4s(out, _cosave_encode(self.chunk_type[::-1]))
        pack_int(out, self.chunk_version)
        pack_int(out, self.chunk_length())
        # If we haven't fully decoded this chunk, treat it as a binary blob
        if not self.fully_decoded:
            out.write(self.chunk_data)

    def chunk_length(self):
        """Calculates the length of this chunk, i.e. the length of the data
        that follows after this chunk's header. Fully decoded chunks must
        override this, otherwise an AbstractError will be raised.

        :return: The calculated length (in bytes)."""
        # Let's be defensive here - will minimally slow us down to check this,
        # but enforcing your API is good practice
        if self.fully_decoded: raise NotImplementedError
        return len(self.chunk_data)

    def __repr__(self):
        return (f'{self.chunk_type} chunk: v{self.chunk_version}, '
                f'{self.data_len} bytes')

class _xSEModListChunk(_xSEChunk, _Dumpable, _Remappable):
    """An abstract class for chunks that contain a list of mods (e.g. MODS or
    LIMD) """
    __slots__ = ('mod_names',)

    def __init__(self, ins, chunk_type):
        super().__init__(ins, chunk_type)
        self.mod_names: list[str] = []

    def read_mod_names(self, ins, mod_count: int):
        """Reads a list of mod names with length mod_count from the specified
        input stream. The result is saved in the mod_names variable.

        :param ins: The input stream to read from.
        :param mod_count: The number of mod names to read."""
        for x in range(mod_count):
            self.mod_names.append(_unpack_cosave_str16(ins))

    def write_mod_names(self, out):
        """Writes the saved list of mod names to the specified output stream.

        :param out: The output stream to write to."""
        for mod_name in self.mod_names:
            _pack_cosave_str16(out, mod_name)

    def chunk_length(self):
        # 2 bytes per mod name (for the length)
        total_len = len(self.mod_names) * 2
        total_len += sum(map(len, self.mod_names))
        return total_len

    def dump_to_log(self, log, save_masters_):
        for mod_name in self.mod_names:
            log(f'    - {mod_name}')

    def remap_plugins(self, fnmod_rename):
        self.mod_names = [fnmod_rename.get(x, x) for x in self.mod_names]

class _xSEChunkARVR(_xSEChunk, _Dumpable):
    """An ARVR (Array Variable) chunk. Only available in OBSE and NVSE. See
    ArrayVar.h in xSE's source code for the specification."""
    fully_decoded = True
    __slots__ = ('_key_type', 'mod_index', 'array_id', 'is_packed',
                 'references', 'elements')

    class _xSEEntryARVR(_ChunkEntry, _Dumpable):
        """A single ARVR entry. An ARVR chunk contains several of these."""
        __slots__ = ('_key_type', 'arvr_key', 'element_type', 'stored_data')
        arvr_key: float | str
        stored_data: int | float | str

        def __init__(self, ins, key_type: int):
            if key_type == 1:
                self.arvr_key = unpack_double(ins)
            elif key_type == 3:
                self.arvr_key = _unpack_cosave_str16(ins)
            else:
                raise RuntimeError(f'Unknown or unsupported key type '
                                   f'{key_type}.')
            self._key_type = key_type
            self.element_type = unpack_byte(ins)
            if self.element_type == 1:
                self.stored_data = unpack_double(ins)
            elif self.element_type in (2, 4):
                self.stored_data = unpack_int(ins)
            elif self.element_type == 3:
                self.stored_data = _unpack_cosave_str16(ins)
            else:
                raise RuntimeError(f'Unknown or unsupported element type '
                                   f'{self.element_type}.')

        def write_entry(self, out):
            if self._key_type == 1:
                pack_double(out, self.arvr_key)
            elif self._key_type == 3:
                _pack_cosave_str16(out, self.arvr_key)
            else:
                raise RuntimeError(f'Unknown or unsupported key type '
                                   f'{self._key_type}.')
            pack_byte(out, self.element_type)
            if self.element_type == 1:
                pack_double(out, self.stored_data)
            elif self.element_type in (2, 4):
                pack_int(out, self.stored_data)
            elif self.element_type == 3:
                _pack_cosave_str16(out, self.stored_data)
            else:
                raise RuntimeError(f'Unknown or unsupported element type '
                                   f'{self.element_type}.')

        def entry_length(self):
            # element_type is B, arvr_key is either d or H + string
            total_len = 1 + (8 if self._key_type == 1
                             else 2 + len(self.arvr_key))
            if self.element_type == 1:
                total_len += 8
            elif self.element_type in (2, 4):
                total_len += 4
            elif self.element_type == 3:
                total_len += 2 + len(self.stored_data)
            return total_len

        def dump_to_log(self, log, save_masters_):
            if self._key_type == 1:
                key_str = f'{self.arvr_key:f}'
            elif self._key_type == 3:
                key_str = self.arvr_key
            else:
                key_str = 'BAD'
            if self.element_type == 1:
                data_str = f'{self.stored_data:f}'
                type_str = 'NUM'
            elif self.element_type == 2:
                data_str = f'0x{self.stored_data:08X}'
                type_str = 'REF'
            elif self.element_type == 3:
                data_str = self.stored_data
                type_str = 'STR'
            elif self.element_type == 4:
                data_str = f'{self.stored_data:d}'
                type_str = 'ARR'
            else:
                data_str = 'UNKNOWN'
                type_str = 'BAD'
            log(f'    - [{key_str}]:{type_str} = {data_str}')

    def __init__(self, ins, chunk_type):
        super().__init__(ins, chunk_type)
        self.elements = []
        self.mod_index = unpack_byte(ins)
        self.array_id = unpack_int(ins)
        self.key_type = unpack_byte(ins)
        self.is_packed = unpack_byte(ins)
        if self.chunk_version >= 1:
            num_references = unpack_int(ins)
            self.references = []
            for x in range(num_references):
                self.references.append(unpack_byte(ins))
        num_elements = unpack_int(ins)
        for x in range(num_elements):
            self.elements.append(self._xSEEntryARVR(ins, self.key_type))

    @property
    def key_type(self):
        """Returns the key type of this ARVR chunk.

        :return: The key type of this ARVR chunk."""
        return self._key_type

    @key_type.setter
    def key_type(self, new_key_type: int):
        """Changes the key type of this ARVR chunk.

        :param new_key_type: The key type to change to."""
        self._key_type = new_key_type
        # Need to update the cached information in the entries too
        for element in self.elements:
            element._key_type = new_key_type

    def write_chunk(self, out):
        super().write_chunk(out)
        pack_byte(out, self.mod_index)
        pack_int(out, self.array_id)
        pack_byte(out, self.key_type)
        pack_byte(out, self.is_packed)
        if self.chunk_version >= 1:
            pack_int(out, len(self.references))
            for reference in self.references:
                pack_byte(out, reference)
        pack_int(out, len(self.elements))
        for element in self.elements:
            element.write_entry(out)

    def chunk_length(self):
        # The ones that are always there (3*B, 2*I)
        total_len = 11
        if self.chunk_version >= 1:
            # Every reference is a byte
            total_len += 4 + len(self.references)
        total_len += sum(map(lambda e: e.entry_length(), self.elements))
        return total_len

    def dump_to_log(self, log, save_masters):
        if self.mod_index == 255:
            log('   ' + _('Plugin: Save File (%(plugin_save_index)s)') % {
                'plugin_save_index': f'{self.mod_index:02X}'})
        else:
            log('   ' + _('Plugin: %(plugin_resolved_name)s '
                          '(%(plugin_save_index)s)') % {
                'plugin_resolved_name': save_masters[self.mod_index],
                'plugin_save_index': f'{self.mod_index:02X}'})
        log('   ' + _('ID: %(array_id)d') % {'array_id': self.array_id})
        if self.key_type == 1: # Numeric
            if self.is_packed:
                log('   ' + _('Type: Array'))
            else:
                log('   ' + _('Type: Map'))
        elif self.key_type == 3:
            log('   ' + _('Type: StringMap'))
        else:
            log('   ' + _('Type: Unknown'))
        if self.chunk_version >= 1:
            log('   ' + _('References:'))
            for refModID in self.references:
                if refModID == 255:
                    log(f"    - {_('Save File')} ({refModID:02X})")
                else:
                    log(f'    - {save_masters[refModID]} ({refModID:02X})')
        log('   ' + _('Size: %(num_elements)d') % {
            'num_elements': len(self.elements)})
        for element in self.elements:
            element.dump_to_log(log, save_masters)

class _xSEChunkDATA(_xSEModListChunk):
    """A DATA chunk. Added by SOS for Skyrim LE and SE. We need to read/write
    it because it contains a (terribly formatted) list of mod names. See
    Storage.cpp in the SOS download for its creation (no specification
    available)."""
    fully_decoded = True
    __slots__ = (u'sos_version', u'remaining_data')

    def __init__(self, ins, chunk_type):
        super().__init__(ins, chunk_type)
        # Avoid read_mod_names, these strings are space-terminated. Yep, that's
        # right. Not null-terminated or specified with a length, they are
        # *space-terminated*. Spaces in the file name are escaped to \x07
        # instead.
        start_pos = ins.tell()
        # The version is stored as a string of digits, e.g. '300004'
        self.sos_version = _unpack_cosave_space_str(ins)
        if self.chunk_version > 3:
            # New format in SSE, no longer uses the 'nomod' nonsense. Once
            # again, the number of mods is stored literally as a string of
            # digits, e.g. '153'.
            num_plugins = int(_unpack_cosave_space_str(ins))
            for x in range(num_plugins):
                self.mod_names.append(_unpack_cosave_space_str(ins))
        else:
            for x in range(256):
                # This chunk always has 256 mods listed, any excess ones
                # just get the string 'nomod' stored.
                read_string = _unpack_cosave_space_str(ins)
                if read_string.lower() != u'nomod':
                    self.mod_names.append(read_string)
        # Treat the remainder as a binary blob, no mod names in there
        read_size = ins.tell() - start_pos
        self.remaining_data = ins.read(self.data_len - read_size)

    def chunk_length(self):
        # stored_version & space separator between stored_version and either
        # the mods or the mod count (depending on chunk_version)
        total_len = len(self.sos_version) + 1
        if self.chunk_version > 3:
            total_len += len(self.mod_names) # space separators between mods
            # the mod count as a string & space separator between it and mods
            total_len += len(str(len(self.mod_names))) + 1
        else:
            total_len += 256 # space seperators between mods
            total_len += len(u'nomod') * (256 - len(self.mod_names)) # 'nomod's
        total_len += sum(map(len, self.mod_names)) # all present mods
        return total_len + len(self.remaining_data) # all other data

    def write_chunk(self, out):
        super().write_chunk(out)
        _pack_cosave_space_str(out, self.sos_version)
        # Avoid write_mod_names, see reasoning above
        if self.chunk_version > 3:
            _pack_cosave_space_str(out, str(len(self.mod_names)))
            for mod_name in self.mod_names:
                _pack_cosave_space_str(out, mod_name)
        else:
            # Note that we need to append the 'nomod's we removed during
            # loading here again
            all_mod_names = self.mod_names + [u'nomod'] * (
                    256 - len(self.mod_names))
            for mod_name in all_mod_names:
                _pack_cosave_space_str(out, mod_name)
        out.write(self.remaining_data)

    def dump_to_log(self, log, save_masters_):
        log('   ' + _('%(num_loaded_plugins)d loaded plugins:') % {
            'num_loaded_plugins': len(self.mod_names)})
        super().dump_to_log(log, save_masters_)

class _xSEChunkLIMD(_xSEModListChunk):
    """An LIMD (Light Mod Files) chunk. Available for SKSE64 and F4SE. This is
    the new version of the LMOD chunk. In contrast to LMOD, LIMD can store
    more than 255 light mods (up to 65535). This chunk has now been deprecated,
    along with the MODS chunk, in favor of the PLGN chunk. New versions of
    SKSE64/F4SE no longer generate it. See Core_Serialization.cpp or
    InternalSerialization.cpp for its creation (no specification available)."""
    fully_decoded = True
    __slots__ = ()

    def __init__(self, ins, chunk_type):
        super().__init__(ins, chunk_type)
        self.read_mod_names(ins, unpack_short(ins))

    def write_chunk(self, out):
        super().write_chunk(out)
        pack_short(out, len(self.mod_names))
        self.write_mod_names(out)

    def chunk_length(self):
        return 2 + super().chunk_length()

    def dump_to_log(self, log, save_masters_):
        log('   ' + _('%(num_loaded_lights)d loaded light plugins:') % {
            'num_loaded_lights': len(self.mod_names)})
        super().dump_to_log(log, save_masters_)

class _xSEChunkLMOD(_xSEModListChunk):
    """An LMOD (Light Mod Files) chunk. Only available in SKSE64 and F4SE. This
    is the legacy version of the LIMD chunk, which is no longer generated by
    newer xSE versions. The difference is that this one only supported up to
    255 light mods, while the games themselves support more than that."""
    fully_decoded = True
    __slots__ = ()

    def __init__(self, ins, chunk_type):
        super().__init__(ins, chunk_type)
        self.read_mod_names(ins, unpack_byte(ins))

    def write_chunk(self, out):
        super().write_chunk(out)
        pack_byte(out, len(self.mod_names))
        self.write_mod_names(out)

    def chunk_length(self):
        return 1 + super().chunk_length()

    def dump_to_log(self, log, save_masters_):
        log('   ' + _('%(num_loaded_lights)d loaded light plugins:') % {
            'num_loaded_lights': len(self.mod_names)})
        super().dump_to_log(log, save_masters_)

class _xSEChunkMODS(_xSEModListChunk):
    """A MODS (Mod Files) chunk. For SKSE64 and F4SE, this chunk has now been
    deprecated, along with the LIMD chunk, in favor of the PLGN chunk. New
    versions of SKSE64/F4SE no longer generate it. Otherwise, it is available
    for all script extenders. See Core_Serialization.cpp or
    InternalSerialization.cpp for its creation (no specification available)."""
    fully_decoded = True
    __slots__ = ()

    def __init__(self, ins, chunk_type):
        super().__init__(ins, chunk_type)
        self.read_mod_names(ins, unpack_byte(ins))

    def write_chunk(self, out):
        super().write_chunk(out)
        pack_byte(out, len(self.mod_names))
        self.write_mod_names(out)

    def chunk_length(self):
        return 1 + super().chunk_length()

    def dump_to_log(self, log, save_masters_):
        log('   ' + _('%(num_loaded_plugins)d loaded plugins:') % {
            'num_loaded_plugins': len(self.mod_names)})
        super().dump_to_log(log, save_masters_)

class _xSEChunkPLGN(_xSEChunk, _Dumpable, _Remappable):
    """A PLGN (Plugin List) chunk. Contains a list of all loaded plugins (i.e.
    mod files, both regular ones and light ones) in the correct order.
    This is information that cannot be obtained from the normal save file,
    which stores two independent lists for regular mods and light mods. This
    chunk is used by Wrye Bash to display the correct save master order for
    SSE and FO4. Available for SKSE64 and F4SE. See InternalSerialization.cpp
    for its creation (no specification available)."""
    fully_decoded = True
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
            pack_byte(out, self.mod_index)
            if self.mod_index == 0xFE:
                pack_short(out, self.light_index)
            _pack_cosave_str16(out, self.mod_name)

        def entry_length(self):
            # mod_index is B, light_index and len(mod_name) are H
            total_len = 5 if self.mod_index == 0xFE else 3
            return total_len + len(self.mod_name)

        def dump_to_log(self, log, save_masters_):
            if self.mod_index != 0xFE:
                log(f'    {self.mod_index:02X} | - | {self.mod_name}')
            else:
                log(f'    {self.mod_index:02X} | {self.light_index:04X} | '
                    f'{self.mod_name}')

        def remap_plugins(self, fnmod_rename):
            self.mod_name = fnmod_rename.get(self.mod_name, self.mod_name)

    def __init__(self, ins, chunk_type):
        super().__init__(ins, chunk_type)
        self.mod_entries = []
        for x in range(unpack_short(ins)):
            self.mod_entries.append(self._xSEEntryPLGN(ins))

    def write_chunk(self, out):
        super().write_chunk(out)
        pack_short(out, len(self.mod_entries))
        for mod_entry in self.mod_entries:
            mod_entry.write_entry(out)

    def chunk_length(self):
        return 2 + sum(map(lambda e: e.entry_length(), self.mod_entries))

    def dump_to_log(self, log, save_masters_):
        log('   ' +
            _('Current load order (%(num_loaded_plugins)d plugins):') % {
                'num_loaded_plugins': len(self.mod_entries)})
        log(f"    {_('Index')} | {_('Light Index')} | {_('Plugin')}")
        log(f"    {'-' * 40}")
        for mod_entry in self.mod_entries:
            mod_entry.dump_to_log(log, save_masters_)

    def remap_plugins(self, fnmod_rename):
        for mod_entry in self.mod_entries:
            mod_entry.remap_plugins(fnmod_rename)

class _xSEChunkSTVR(_xSEChunk, _Dumpable):
    """An STVR (String Variable) chunk. Only available in OBSE and NVSE. See
    StringVar.h in xSE's source code for the specification."""
    fully_decoded = True
    __slots__ = ('mod_index', 'string_id', 'string_data')

    def __init__(self, ins, chunk_type):
        super().__init__(ins, chunk_type)
        self.mod_index = unpack_byte(ins)
        self.string_id = unpack_int(ins)
        self.string_data = _unpack_cosave_str16(ins)

    def write_chunk(self, out):
        super().write_chunk(out)
        pack_byte(out, self.mod_index)
        pack_int(out, self.string_id)
        _pack_cosave_str16(out, self.string_data)

    def chunk_length(self):
        return 7 + len(self.string_data)

    def dump_to_log(self, log, save_masters):
        log('   ' + _('Plugin: %(plugin_resolved_name)s '
                      '(%(plugin_save_index)s)') % {
            'plugin_resolved_name': save_masters[self.mod_index],
            'plugin_save_index': f'{self.mod_index:02X}'})
        log('   ' + _('ID: %(string_id)d') % {'string_id': self.string_id})
        log('   ' + _('Data: %(string_data)s') % {
            'string_data': self.string_data})

# Maps all decoded xSE chunk types implemented by xSE itself to the classes
# that read/write them
_xse_chunk_dict = {
    'ARVR': _xSEChunkARVR,
    'LIMD': _xSEChunkLIMD,
    'LMOD': _xSEChunkLMOD,
    'MODS': _xSEChunkMODS,
    'PLGN': _xSEChunkPLGN,
    'STVR': _xSEChunkSTVR,
}
# Maps plugin chunk signatures to dicts that map decoded xSE chunk types
# implemented by that plugin to the classes that read/write them
_xse_plugin_chunk_dict = {
    0x534F53: { # SOS
        'DATA': _xSEChunkDATA,
    },
}

def _get_xse_chunk(parent_sig: int, ins) -> _xSEChunk:
    """Read a 4-byte string from the specified input stream and return an
    instance of a matching xSE chunk class for that string. If no matching
    class is found, an instance of the generic _xSEChunk class is returned
    instead.

    :param parent_sig: The plugin signature (as an integer) of the plugin chunk
        that houses the chunk.
    :param ins: The input stream to read from.
    :return: A instance of a matching chunk class, or the generic one if no
        matching class was found."""
    # The chunk type strings are reversed in the cosaves
    ch_type = _cosave_decode(unpack_4s(ins))[::-1]
    ch_offset = ins.tell()
    try:
        # Look for a special override for this particular plugin chunk first
        if pchunk_dict := _xse_plugin_chunk_dict.get(parent_sig):
            if ch_class := pchunk_dict.get(ch_type):
                return ch_class(ins, ch_type)
        # Otherwise, fall back to the global xSE dictionary
        ch_class = _xse_chunk_dict.get(ch_type, _xSEChunk)
        return ch_class(ins, ch_type)
    except Exception:
        deprint(f'Error while reading cosave chunk {ch_type} at offset '
                f'{ch_offset}')
        raise

class _xSEPluginChunk(_AChunk, _Remappable):
    """A single xSE chunk, composed of _xSEChunk objects."""
    __slots__ = (u'plugin_signature', u'chunks', u'remappable_chunks',
                 u'orig_size')

    def __init__(self, ins, light=False):
        self.plugin_signature = unpack_int(ins) # aka opcodeBase on pre papyrus
        num_chunks = unpack_int(ins)
        self.orig_size = unpack_int(ins) # Store the size for testing
        self.chunks: list[_xSEChunk] = []
        self.remappable_chunks: list[_Remappable] = []
        if light:
            self._read_chunk(ins)
        else:
            for x in range(num_chunks):
                self._read_chunk(ins)

    def _read_chunk(self, ins):
        """Reads a single chunk from the specified input stream and appends it
        to self.chunks and, if the chunk is remappable, to
        self.remappable_chunks.

        :param ins: The input stream to read from."""
        new_chunk = _get_xse_chunk(self.plugin_signature, ins)
        self.chunks.append(new_chunk)
        if isinstance(new_chunk, _Remappable):
            self.remappable_chunks.append(new_chunk)

    def write_chunk(self, out):
        # Don't forget to reverse signature when writing again
        pack_int(out, self.plugin_signature)
        pack_int(out, len(self.chunks))
        pack_int(out, self.chunk_length())
        for chunk in self.chunks:
            chunk.write_chunk(out)

    def chunk_length(self):
        # Every chunk header has a string of length 4 (type) and two integers
        # (version and length)
        total_len = 12 * len(self.chunks)
        for chunk in self.chunks:
            total_len += chunk.chunk_length()
        return total_len

    def remap_plugins(self, fnmod_rename):
        for xse_chunk in self.remappable_chunks:
            xse_chunk.remap_plugins(fnmod_rename)

    def __repr__(self):
        ##: Extremely hacky, the proper method is _get_plugin_signature - but
        # that's in xSECosave and relies on the header...
        if self.plugin_signature in (0, 0x1400):
            from .. import bush
            decoded_psig = bush.game.Se.cosave_tag
        else:
            try:
                decoded_psig = struct_pack(
                    u'I', self.plugin_signature).decode(u'ascii')[::-1]
            except UnicodeDecodeError:
                decoded_psig = self.plugin_signature # Fall back to int display
        return (f'{decoded_psig} chunk: {len(self.chunks)} chunks, '
                f'{self.orig_size} bytes')

#------------------------------------------------------------------------------
# Pluggy Chunks
class _PluggyBlock(_AChunk, _Dumpable):
    """A single pluggy records block. This is the pluggy equivalent of xSE
    chunks."""
    __slots__ = ('record_type',)

    def __init__(self, record_type: int):
        self.record_type = record_type

    def write_chunk(self, out):
        pack_byte(out, self.record_type)

    def unique_identifier(self) -> str:
        """Retrieves a unique identifier for this block. In most cases, this
        should simply be a human-understandable name for the block. An
        exception are the array blocks, since they may occur multiple times.

        :return: A human-understandable, unique identifier for this block."""
        raise NotImplementedError

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
            pack_byte(out, self.pluggy_id)
            pack_byte(out, self.game_id)
            _pack_cosave_str32(out, self.plugin_name)

        def remap_plugins(self, fnmod_rename):
            self.plugin_name = fnmod_rename.get(self.plugin_name,
                                                self.plugin_name)

        def dump_to_log(self, log, save_masters_):
            log(f'    {self.pluggy_id:02X} | {self.game_id:02X} | '
                f'{self.plugin_name}')

    def __init__(self, ins, record_type):
        super().__init__(record_type)
        plugin_count = unpack_int(ins)
        self.plugins = []
        for x in range(plugin_count):
            self.plugins.append(self._PluggyEntryPlugin(ins))

    def write_chunk(self, out):
        super().write_chunk(out)
        pack_int(out, len(self.plugins))
        for plugin in self.plugins:
            plugin.write_entry(out)

    def dump_to_log(self, log, save_masters_):
        log('   ' + _('%(num_loaded_plugins)d loaded plugins:') % {
            'num_loaded_plugins': len(self.plugins)})
        log(f"   {_('Pluggy ID')} | {_('Game ID')} | {_('Name')}")
        log(f"   {'-' * 40}")
        for plugin in self.plugins:
            plugin.dump_to_log(log, save_masters_)

    def remap_plugins(self, fnmod_rename):
        for plugin in self.plugins:
            plugin.remap_plugins(fnmod_rename)

    def unique_identifier(self):
        return _('Plugin Block')

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
            pack_int(out, self.string_id)
            pack_byte(out, self.plugin_index)
            pack_byte(out, self.string_flags)
            _pack_cosave_str32(out, self.string_data)

        def dump_to_log(self, log, save_masters_):
            log('    - ' + _('ID: %(string_id)d') % {
                'string_id': self.string_id})
            log('      ' + _('Owner: %(string_owner)s '
                             '(%(string_owner_index)s)') % {
                'string_owner': save_masters_[self.plugin_index],
                'string_owner_index': f'{self.plugin_index:02X}'})
            log('      ' + _('Flags: %(string_flags)s') % {
                'string_flags': f'0x{self.string_flags:02X}'})
            log('      ' + _('Data: %(string_data)s') % {
                'string_data': self.string_data})

    def __init__(self, ins, record_type):
        super().__init__(record_type)
        string_count = unpack_int(ins)
        self.stored_strings = []
        for x in range(string_count):
            self.stored_strings.append(self._PluggyEntryString(ins))

    def write_chunk(self, out):
        super().write_chunk(out)
        pack_int(out, len(self.stored_strings))
        for stored_string in self.stored_strings:
            stored_string.write_entry(out)

    def dump_to_log(self, log, save_masters_):
        log('   ' + _('%(num_stored_strings)d stored strings:') % {
            'num_stored_strings': len(self.stored_strings)})
        for stored_string in self.stored_strings:
            stored_string.dump_to_log(log, save_masters_)

    def unique_identifier(self):
        return _('String Block')

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
        entry_data: int | float

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
                raise RuntimeError(f'Unknown or unsupported entry type '
                                   f'{self.entry_type}.')

        def write_entry(self, out):
            pack_int(out, self.entry_index)
            pack_byte(out, self.entry_type)
            if self.entry_type == 0:
                pack_int_signed(out, self.entry_data)
            elif self.entry_type == 1:
                pack_int(out, self.entry_data)
            elif self.entry_type == 2:
                pack_float(out, self.entry_data)
            else:
                raise RuntimeError(f'Unknown or unsupported entry type '
                                   f'{self.entry_type}.')

        def dump_to_log(self, log, save_masters_):
            if self.entry_type == 0:
                log(f'     {self.entry_index}: {self.entry_data:d}')
            elif self.entry_type == 1:
                log(f'     {self.entry_index}: 0x{self.entry_data:08X}')
            elif self.entry_type == 2:
                log(f'     {self.entry_index}: {self.entry_data:f}')

    def __init__(self, ins, record_type):
        super().__init__(record_type)
        self.array_id = unpack_int(ins)
        self.plugin_index = unpack_byte(ins)
        self.array_flags = unpack_byte(ins)
        self.max_size = unpack_int(ins)
        self.array_entries = []
        for x in range(unpack_int(ins)):
            self.array_entries.append(self._PluggyEntryArray(ins))

    def write_chunk(self, out):
        super().write_chunk(out)
        pack_int(out, self.array_id)
        pack_byte(out, self.plugin_index)
        pack_byte(out, self.array_flags)
        pack_int(out, self.max_size)
        pack_int(out, len(self.array_entries))
        for array_entry in self.array_entries:
            array_entry.write_entry(out)

    def dump_to_log(self, log, save_masters_):
        log('    ' + _('Owner: %(array_owner)s (%(array_owner_index)s)') % {
            'array_owner': save_masters_[self.plugin_index],
            'array_owner_index': f'{self.plugin_index:02X}'})
        log('      ' + _('Flags: %(array_flags)s') % {
            'array_flags': f'0x{self.array_flags:02X}'})
        log('    ' + _('Maximum Size: %(max_array_size)d') % {
            'max_array_size': self.max_size})
        log('    ' + _('Current Size: %(curr_array_size)d') % {
            'curr_array_size': len(self.array_entries)})
        log('    ' + _('Contents:'))
        for array_entry in self.array_entries:
            array_entry.dump_to_log(log, save_masters_)

    def unique_identifier(self):
        return _('Array Block No. %(array_id)s') % {
            'array_id': self.array_id}

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
            pack_int(out, self.reference_id)
            _pack_cosave_str32(out, self.name_data)

        def dump_to_log(self, log, save_masters_):
            log('    - ' + _('Reference ID: %(reference_id)s') % {
                'reference_id': f'0x{self.reference_id:08X}'})
            printable_name = ''.join([c for c in self.name_data
                                      if c in string.printable])
            log('      ' + _('Name: %(printable_name)s') % {
                'printable_name': printable_name})

    def __init__(self, ins, record_type):
        super().__init__(record_type)
        name_count = unpack_int(ins)
        self.stored_names = []
        for x in range(name_count):
            self.stored_names.append(self._PluggyEntryName(ins))

    def write_chunk(self, out):
        super().write_chunk(out)
        pack_int(out, len(self.stored_names))
        for stored_name in self.stored_names:
            stored_name.write_entry(out)

    def dump_to_log(self, log, save_masters_):
        log('   ' + _('%(num_stored_names)d stored names:') % {
            'num_stored_names': len(self.stored_names)})
        for stored_name in self.stored_names:
            stored_name.dump_to_log(log, save_masters_)

    def unique_identifier(self):
        return _('Name Block')

class _PluggyScreenInfoBlock(_PluggyBlock):
    """A screen information record block. This is an optional block and, if
    present, follows directly after the name block. Note that this block will
    only ever be present if there is at least one HudS or HudT block."""
    __slots__ = ('screen_width', 'screen_height')

    def __init__(self, ins, record_type):
        super().__init__(record_type)
        self.screen_width = unpack_int(ins)
        self.screen_height = unpack_int(ins)

    def write_chunk(self, out):
        super().write_chunk(out)
        pack_int(out, self.screen_width)
        pack_int(out, self.screen_height)

    def dump_to_log(self, log, save_masters_):
        log('   ' + _('Width: %(screen_width)d') % {
            'screen_width': self.screen_width})
        log('   ' + _('Height: %(screen_height)d') % {
            'screen_height': self.screen_height})

    def unique_identifier(self):
        return _('Screen Informations Block')

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
            ins.seek(4, 1) # Discard, unused
            self.alpha = unpack_byte(ins)
            self.alignment = unpack_byte(ins)
            self.auto_scale = unpack_byte(ins)

        def write_entry(self, out):
            pack_int(out, self.hud_id)
            pack_byte(out, self.plugin_index)
            pack_byte(out, self.hud_flags)
            pack_byte(out, self.root_id)
            _pack_cosave_str32(out, self.file_name)
            pack_byte(out, self.show_mode)
            pack_int(out, self.pos_x)
            pack_int(out, self.pos_y)
            pack_short(out, self.depth)
            pack_int(out, self.scale_x)
            pack_int(out, self.scale_y)
            pack_int(out, 0) # Need to write this, but it's unused
            pack_byte(out, self.alpha)
            pack_byte(out, self.alignment)
            pack_byte(out, self.auto_scale)

        def dump_to_log(self, log, save_masters_):
            log('    - ' + _('HUD ID: %(hud_id)d') % {'hud_id': self.hud_id})
            log('      ' + _('Owner: %(hud_owner)s (%(hud_owner_index)s)') % {
                'hud_owner': save_masters_[self.plugin_index],
                'hud_owner_index': f'{self.plugin_index:02X}'})
            log('      ' + _('Flags: %(hud_flags)s') % {
                'hud_flags': f'0x{self.hud_flags:02X}'})
            log('      ' + _('Root ID: %(hud_root_id)d') % {
                'hud_root_id': self.root_id})
            log('      ' + _('File: %(hud_file_name)s') % {
                'hud_file_name': self.file_name})
            log('      ' + _('Show Mode: %(hud_show_mode)s') % {
                'hud_show_mode': f'0x{self.show_mode:02X}'})
            log('      ' + _('X Position: %(hud_pos_x)d') % {
                'hud_pos_x': self.pos_x})
            log('      ' + _('Y Position: %(hud_pos_y)d') % {
                'hud_pos_y': self.pos_y})
            log('      ' + _('Depth: %(hud_depth)d') % {
                'hud_depth': self.depth})
            log('      ' + _('X Scale: %(hud_scale_x)d') % {
                'hud_scale_x': self.scale_x})
            log('      ' + _('Y Scale: %(hud_scale_y)d') % {
                'hud_scale_y': self.scale_y})
            log('      ' + _('Alpha: %(hud_alpha)s') % {
                'hud_alpha': f'0x{self.alpha:02X}'})
            log('      ' + _('Alignment: %(hud_alignment)s') % {
                'hud_alignment': f'0x{self.alignment:02X}'})
            log('      ' + _('Auto-Scale: %(hud_auto_scale)s') % {
                'hud_auto_scale': f'0x{self.auto_scale:02X}'})

    def __init__(self, ins, record_type):
        super().__init__(record_type)
        self.hud_entries = []
        for x in range(unpack_int(ins)):
            self.hud_entries.append(self._PluggyEntryHudS(ins))

    def write_chunk(self, out):
        super().write_chunk(out)
        pack_int(out, len(self.hud_entries))
        for hud_entry in self.hud_entries:
            hud_entry.write_entry(out)

    def dump_to_log(self, log, save_masters_):
        log('   ' + _('%(num_hud_screens)d HUD screen entries:') % {
            'num_hud_screens': len(self.hud_entries)})
        for hud_entry in self.hud_entries:
            hud_entry.dump_to_log(log, save_masters_)

    def unique_identifier(self):
        return _('HUD Screen/Image Block')

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
            ins.seek(4, 1) # Discard, unused
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
            pack_int(out, self.hud_id)
            pack_byte(out, self.plugin_index)
            pack_byte(out, self.hud_flags)
            pack_int(out, self.pos_x)
            pack_int(out, self.pos_y)
            pack_short(out, self.depth)
            pack_int(out, self.scale_x)
            pack_int(out, self.scale_y)
            pack_int(out, 0) # Need to write this, but it's unused
            pack_byte(out, self.alpha)
            pack_byte(out, self.alignment)
            pack_byte(out, self.auto_scale)
            pack_int(out, self.hud_width)
            pack_int(out, self.hud_height)
            pack_byte(out, self.text_format)
            _pack_cosave_str32(out, self.font_name)
            _pack_cosave_str32(out, self.text_data)
            pack_int(out, self.font_height)
            pack_int(out, self.font_width)
            pack_short(out, self.font_boldness)
            pack_byte(out, self.font_italic)
            pack_byte(out, self.font_red)
            pack_byte(out, self.font_green)
            pack_byte(out, self.font_blue)

        def dump_to_log(self, log, save_masters_):
            log('    - ' + _('HUD ID: %(hud_id)s') % {'hud_id': self.hud_id})
            log('      ' + _('Owner: %(hud_owner)s (%(hud_owner_index)s)') % {
                'hud_owner': save_masters_[self.plugin_index],
                'hud_owner_index': f'{self.plugin_index:02X}'})
            log('      ' + _('Flags: %(hud_flags)s') % {
                'hud_flags': f'0x{self.hud_flags:02X}'})
            log('      ' + _('Show Mode: %(hud_show_mode)s') % {
                'hud_show_mode': f'0x{self.show_mode:02X}'})
            log('      ' + _('X Position: %(hud_pos_x)d') % {
                'hud_pos_x': self.pos_x})
            log('      ' + _('Y Position: %(hud_pos_y)d') % {
                'hud_pos_y': self.pos_y})
            log('      ' + _('Depth: %(hud_depth)d') % {
                'hud_depth': self.depth})
            log('      ' + _('X Scale: %(hud_scale_x)d') % {
                'hud_scale_x': self.scale_x})
            log('      ' + _('Y Scale: %(hud_scale_y)d') % {
                'hud_scale_y': self.scale_y})
            log('      ' + _('Alpha: %(hud_alpha)s') % {
                'hud_alpha': f'0x{self.alpha:02X}'})
            log('      ' + _('Alignment: %(hud_alignment)s') % {
                'hud_alignment': f'0x{self.alignment:02X}'})
            log('      ' + _('Auto-Scale: %(hud_auto_scale)s') % {
                'hud_auto_scale': f'0x{self.auto_scale:02X}'})
            log('      ' + _('HUD Width: %(hud_width)d') % {
                'hud_width': self.hud_width})
            log('      ' + _('HUD Height: %(hud_height)d') % {
                'hud_height': self.hud_height})
            log('      ' + _('Text Format: %(hud_text_format)d') % {
                'hud_text_format': self.text_format})
            log('      ' + _('Font Name: %(hud_font_name)s') % {
                'hud_font_name': self.font_name})
            log('      ' + _('Text Data: %(hud_text_data)s') % {
                'hud_text_data': self.text_data})
            log('      ' + _('Font Width: %(hud_font_width)d') % {
                'hud_font_width': self.font_width})
            log('      ' + _('Font Height: %(hud_font_height)d') % {
                'hud_font_height': self.font_height})
            log('      ' + _('Boldness: %(hud_font_boldness)d') % {
                'hud_font_boldness': self.font_boldness})
            log('      ' + _('Italic: %(hud_font_italic)d') % {
                'hud_font_italic': self.font_italic})
            log('      ' + _('Font Color: (%(hud_font_red)d, '
                             '%(hud_font_green)d, %(hud_font_blue)d)') % {
                'hud_font_red': self.font_red,
                'hud_font_green': self.font_green,
                'hud_font_blue': self.font_blue})

    def __init__(self, ins, record_type):
        super().__init__(record_type)
        self.hud_entries = []
        for x in range(unpack_int(ins)):
            self.hud_entries.append(self._PluggyEntryHudT(ins))

    def write_chunk(self, out):
        super().write_chunk(out)
        pack_int(out, len(self.hud_entries))
        for hud_entry in self.hud_entries:
            hud_entry.write_entry(out)

    def dump_to_log(self, log, save_masters_):
        log('   ' + _('%(num_hud_texts)d HUD Text entries:') % {
            'num_hud_texts': len(self.hud_entries)})
        for hud_entry in self.hud_entries:
            hud_entry.dump_to_log(log, save_masters_)

    def unique_identifier(self):
        return _('HUD Text Block')

#------------------------------------------------------------------------------
# Files
class ACosave(_Dumpable, _Remappable, AFile):
    """The abstract base class for all cosave files."""
    cosave_header: _AHeader
    cosave_ext = u''
    parse_save_path = None # set in factory
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
        self.remappable_chunks: list[_Remappable] = []
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
            try:
                with self.abs_path.open(u'rb') as ins:
                    self._read_cosave_header(ins)
                    self._read_cosave_body(ins, light)
                self.loading_state = target_state
            except struct_error as e:
                raise CosaveError(self.abs_path.tail,
                                  f'Failed to read cosave: {e!r}')

    def _reset_cache(self, stat_tuple, **kwargs):
        # Reset our loading state to 'unloaded', which will discard everything
        # when the next request is made to the cosave (see read_cosave above)
        self.loading_state = 0
        super()._reset_cache(stat_tuple, **kwargs)

    def _read_cosave_header(self, ins):
        """Reads and assigns the header of this cosave. You probably don't need
        to override this method.

        :param ins: The input stream to read from."""
        self.cosave_header = get_type_hints(self.__class__)['cosave_header'](
            ins, self.abs_path.tail)

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
        raise NotImplementedError

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
        with TempFile() as tmp_path:
            self.write_cosave(GPath_no_norm(tmp_path))
            out_path.replace_with_temp(tmp_path)

    def get_master_list(self) -> list[str]:
        """Retrieves a list of masters from this cosave. This will read an
        appropriate chunk and return a list of the masters from that chunk.

        :return: A list of the masters stored in this cosave."""

    def has_accurate_master_list(self) -> bool:
        """Checks whether or not this cosave contains an accurate master list -
        i.e. one that correctly represents the order of plugins as they were at
        the time that the save was taken. This is used to determine whether or
        not to use get_master_list for saves in SSE / FO4.

        :return: True if the master list retrieved by get_master_list will be
            accurate."""

    def dump_to_log(self, log, save_masters_):
        # We need the entire cosave to dump
        self.read_cosave()
        self.cosave_header.dump_to_log(log, save_masters_)

    def remap_plugins(self, fnmod_rename):
        # We need the entire cosave to remap
        self.read_cosave()
        for cosave_chunk in self.remappable_chunks:
            cosave_chunk.remap_plugins(fnmod_rename)

    @classmethod
    def get_cosave_path(cls, save_path: Path) -> Path:
        """Return the cosave path corresponding to save_path. The save_path
        may be located in the backup directory and so it may end with an 'f'
        (for first backup) which should be appended to the cosave path also.

        :param save_path: The path to the save file that a cosave could belong
            to.
        :return: The path at which the cosave could exist."""
        sa_root, sa_ext = cls.parse_save_path(f'{save_path}')
        if sa_root and sa_ext:
            final_cs_path = sa_root + cls.cosave_ext
            # Handle backups that end with 'f' - we just need to append that
            # again at the extension of the final path
            ends_with_f = (sa_ext[-1] == u'f')
            if ends_with_f:
                sa_ext = sa_ext[:-1]
            # The cosave naming differs for baks: instead of <save>.**se, it's
            # <save>.**se.bak (or .bakf)
            if sa_ext == u'.bak':
                final_cs_path += sa_ext
            if ends_with_f:
                final_cs_path += u'f'
            return GPath(final_cs_path)
        raise BoltError(f'Invalid save path {save_path}')

class xSECosave(ACosave):
    """Represents an xSE cosave, with a .**se extension."""
    cosave_header: _xSEHeader
    _pluggy_signature = None # signature (aka opcodeBase) of Pluggy plugin
    _xse_signature = 0x1400 # signature (aka opcodeBase) of xSE plugin itself
    cosave_ext = u'' # set in the factory function
    __slots__ = ()

    def _read_cosave_body(self, ins, light=False):
        if light:
            self._add_cosave_chunk(_xSEPluginChunk(ins, light))
        else:
            for x in range(self.cosave_header.num_plugin_chunks):
                self._add_cosave_chunk(_xSEPluginChunk(ins, light))

    def write_cosave(self, out_path):
        super(xSECosave, self).write_cosave(out_path)
        prev_mtime = self.abs_path.mtime
        buff = io.BytesIO()
        # We have to update the number of chunks in the header here, since
        # that can't be done automatically
        self.cosave_header.num_plugin_chunks = len(self.cosave_chunks)
        self.cosave_header.write_header(buff)
        for plugin_ch in self.cosave_chunks:
            plugin_ch.write_chunk(buff)
        with open(out_path, 'wb') as out:
            out.write(buff.getvalue())
        out_path.mtime = prev_mtime

    def get_master_list(self):
        # We only need the first chunk to read the master list
        self.read_cosave(light=True)
        # The first chunk is either a PLGN chunk (on SKSE64) or a MODS one
        xse_chunks = self._get_xse_plugin().chunks
        first_chunk = xse_chunks[0]
        if isinstance(first_chunk, _xSEChunkPLGN):
            return [mod_entry.mod_name for mod_entry in
                    first_chunk.mod_entries]
        elif isinstance(first_chunk, _xSEChunkMODS):
            return first_chunk.mod_names
        raise InvalidCosaveError(self.abs_path.tail,
            u'First chunk was not PLGN or MODS chunk.')

    def has_accurate_master_list(self):
        # Check the first chunk's signature. If and only if that signature
        # is PLGN can we accurately return a master list.
        self.read_cosave(light=True)
        first_ch = self._get_xse_plugin().chunks[0] # type: _xSEChunk
        return first_ch.chunk_type == u'PLGN'

    def dump_to_log(self, log, save_masters_):
        super().dump_to_log(log, save_masters_)
        for plugin_chunk in self.cosave_chunks: # type: _xSEPluginChunk
            plugin_sig = self._get_plugin_signature(plugin_chunk)
            log.setHeader(_('Plugin: %(co_plugin_sig)s, Total chunks: '
                            '%(num_co_plugin_chunks)d') % {
                'co_plugin_sig': plugin_sig,
                'num_co_plugin_chunks': len(plugin_chunk.chunks)})
            log('=' * 40)
            log(f"{_('Type')} | {_('Version')} | {_('Size (in bytes)')}")
            log('-' * 40)
            for chunk in plugin_chunk.chunks: # type: _xSEChunk
                log(f'{chunk.chunk_type:4s} | {chunk.chunk_version} | '
                    f'{chunk.chunk_length()}')
                if isinstance(chunk, _Dumpable):
                    chunk.dump_to_log(log, save_masters_)

    # Helper methods
    def _get_plugin_signature(self, plugin_chunk, with_raw=True):
        """Creates a human-readable version of the specified plugin chunk's
        signature.

        :param plugin_chunk: The plugin chunk whose signature should be
            processed.
        :param with_raw: If True, append the hexadecimal version of the
            signature as well.
        :return: A human-readable version of the plugin chunk's signature."""
        raw_sig = plugin_chunk.plugin_signature
        if raw_sig == self._xse_signature:
            readable_sig = self.cosave_header.savefile_tag
        elif raw_sig == self._pluggy_signature:
            readable_sig = 'Pluggy'
        else:
            # Reverse the result since xSE writes signatures backwards
            readable_sig = ''.join(
                [self._to_unichr(raw_sig, x) for x in [0, 8, 16, 24]])[::-1]
        return readable_sig + (f' (0x{raw_sig:X})' if with_raw else '')

    @staticmethod
    def _to_unichr(target_int: int, shift: int):
        """Small helper method for get_plugin_signature that interprets the
        result of shifting the specified integer by the specified shift amount
        and masking with 0xFF as a unichr. Additionally, if the result of that
        operation is not printable, an empty string is returned instead.

        :param target_int: The integer to shift and mask.
        :param shift: By how much (in bits) to shift.
        :return: The unichr representation of the result, or an empty
            string."""
        temp_char = chr(target_int >> shift & 0xFF)
        if temp_char not in string.printable:
            temp_char = u''
        return temp_char

    def _get_xse_plugin(self) -> _xSEPluginChunk:
        """Retrieves the plugin chunk for xSE itself from this cosave.

        :return: The plugin chunk for xSE itself."""
        for plugin_chunk in self.cosave_chunks:
            if plugin_chunk.plugin_signature == self._xse_signature:
                return plugin_chunk
        # Something has gone seriously wrong, the xSE chunk _must_ be present
        raise InvalidCosaveError(self.abs_path.tail,
            u'xSE plugin chunk is missing.')

class PluggyCosave(ACosave):
    """Represents a Pluggy cosave, with a .pluggy extension."""
    cosave_header: _PluggyHeader
    cosave_ext = u'.pluggy'
    # Used to convert from block type int to block class
    # See pluggy file format specification for how these map
    _block_types = [_PluggyPluginBlock, _PluggyStringBlock, _PluggyArrayBlock,
                    _PluggyNameBlock, _PluggyScreenInfoBlock, _PluggyHudSBlock,
                    _PluggyHudTBlock]
    __slots__ = ('save_game_ticks',)

    def __init__(self, cosave_path):
        super().__init__(cosave_path)
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
            total_size = self.abs_path.psize
            with self.abs_path.open(u'rb') as ins:
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
                    raise InvalidCosaveError(self.abs_path.tail,
                        f'End control position was incorrect (expected '
                        f'{expected_position}, but got {actual_position}).')
                # Finally, check if the stored CRC matches the actual CRC of
                # all preceding data.
                ins.seek(0)
                checksum_data = ins.read(total_size - 4)
                expected_crc = unpack_int_signed(ins)
            actual_crc = crc32(checksum_data)
            if actual_crc != expected_crc:
                raise InvalidCosaveError(self.abs_path.tail,
                    f'Checksum does not match (expected {expected_crc:08X}, '
                    f'but got {actual_crc:08X}).')
            try:
                ins = io.BytesIO(buffered_data)
                self._read_cosave_header(ins)
                self._read_cosave_body(ins, light)
            except struct_error as e:
                raise CosaveError(self.abs_path.tail,
                    f'Failed to read cosave: {e!r}')
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

    def _get_block_type(self, record_type: int):
        """Returns the matching block type for the specified record type or
        raises an informative error if the record type is not known.

        :param record_type: An integer representing the read record type."""
        try:
            return self._block_types[record_type]
        except IndexError:
            raise InvalidCosaveError(self.abs_path.tail,
                f'Unknown pluggy record block type {record_type}.')

    def write_cosave(self, out_path):
        super().write_cosave(out_path)
        out = io.BytesIO()
        self.cosave_header.write_header(out)
        for pluggy_block in self.cosave_chunks:
            pluggy_block.write_chunk(out)
        # Write out the 'footer': Savegame Ticks and End Control - Checksum
        # is written down below
        pack_int(out, self.save_game_ticks)
        pack_int(out, out.tell())
        final_data = out.getvalue()
        prev_mtime = self.abs_path.mtime
        with open(out_path, 'wb') as out:
            out.write(final_data)
            pack_int_signed(out, crc32(final_data))
        out_path.mtime = prev_mtime

    def get_master_list(self):
        # We only need the first chunk to read the master list
        self.read_cosave(light=True)
        first_block: _PluggyPluginBlock = self.cosave_chunks[0]
        if first_block.record_type != 0:
            raise InvalidCosaveError(self.abs_path.tail,
                u'First Pluggy block is not the plugin block.')
        return [plugin.plugin_name for plugin in first_block.plugins]

    def has_accurate_master_list(self):
        # Pluggy cosaves always have an accurate list since they only exist for
        # Oblivion, which does not have ESLs.
        return True

    def dump_to_log(self, log, save_masters_):
        super(PluggyCosave, self).dump_to_log(log, save_masters_)
        for pluggy_block in self.cosave_chunks:
            log.setHeader(pluggy_block.unique_identifier())
            log('=' * 40)
            pluggy_block.dump_to_log(log, save_masters_)

# Factory
def get_cosave_types(game_fsName, parse_save_path, cosave_tag,
        cosave_ext) -> list[type[ACosave]]:
    """Factory method for retrieving the cosave types for the current game.
    Also sets up some class variables for xSE and Pluggy signatures.

    :param game_fsName: bush.game.fsName, the name of the current game.
    :param parse_save_path: A function to parse valid save paths into root and
        extension.
    :param cosave_tag: bush.game.Se.cosave_tag, the magic tag used to mark the
        cosave. Empty string if this game doesn't have cosaves.
    :param cosave_ext: bush.game.Se.cosave_ext, the extension for cosaves.
    :return: A list of types of cosaves supported by this game."""
    # Check if the game even has a script extender
    if not cosave_tag: return []
    # Assign things that concern all games with script extenders
    _xSEHeader.savefile_tag = cosave_tag
    xSECosave.cosave_ext = cosave_ext
    ACosave.parse_save_path = parse_save_path
    cosave_types = [xSECosave]
    # Handle game-specific special cases
    if game_fsName == 'Oblivion':
        xSECosave._pluggy_signature = 0x2330
        cosave_types.append(PluggyCosave)
    # Games >= Skyrim have 0 as the xSE signature
    xSECosave._xse_signature = 0x1400 if game_fsName in (
        'Oblivion', 'Fallout3', 'FalloutNV') else 0x0
    return cosave_types
