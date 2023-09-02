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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""Bsa files.

For the file format see:
http://www.uesp.net/wiki/Tes4Mod:BSA_File_Format
http://www.uesp.net/wiki/Tes5Mod:Archive_File_Format
"""
from __future__ import annotations

__author__ = 'Utumno'

import os
import typing
import zlib
from collections import defaultdict
from functools import partial
from itertools import chain, groupby
from operator import itemgetter
from struct import unpack_from as _unpack_from

import lz4.frame

from .dds_files import DDSFile, mk_dxgi_fmt
from ..bolt import AFile, Flags, Progress, deprint, struct_calcsize, \
    struct_error, struct_unpack, structs_cache, unpack_byte, unpack_int
from ..env import convert_separators
from ..exception import BSACompressionError, BSADecodingError, \
    BSADecompressionError, BSADecompressionSizeError, BSAError, BSAFlagError

_bsa_encoding = 'cp1252' # rumor has it that's the files/folders names encoding
path_sep = u'\\'

# Utilities -------------------------------------------------------------------
def _decode_path(byte_path: bytes, bsa_name: str):
    try:
        return byte_path.decode(_bsa_encoding).replace('/', path_sep)
    except UnicodeDecodeError:
        raise BSADecodingError(bsa_name, byte_path)

class _BsaCompressionType(object):
    """Abstractly represents a way of compressing and decompressing BSA
    records."""
    @staticmethod
    def compress_rec(decompressed_data, bsa_name):
        """Compresses the specified record data. Raises a BSAError if the
        underlying compression library raises an error. Returns the resulting
        compressed data."""
        raise NotImplementedError

    @staticmethod
    def decompress_rec(compressed_data, decompressed_size, bsa_name):
        """Decompresses the specified record data. Expects the specified
        number of bytes of decompressed data and raises a BSAError if a
        mismatch occurs or if the underlying compression library raises an
        error. Returns the resulting decompressed data."""
        raise NotImplementedError

# Note that I mirrored BSArch here by simply leaving zlib and lz4 at their
# defaults for compression
class _Bsa_zlib(_BsaCompressionType):
    """Implements BSA record compression and decompression using zlib. Used for
    all games but SSE."""
    @staticmethod
    def compress_rec(decompressed_data, bsa_name):
        try:
            return zlib.compress(decompressed_data)
        except zlib.error as e:
            raise BSACompressionError(bsa_name, u'zlib', e)

    @staticmethod
    def decompress_rec(compressed_data, decompressed_size, bsa_name):
        try:
            decompressed_data = zlib.decompress(compressed_data)
        except zlib.error as e:
            raise BSADecompressionError(bsa_name, u'zlib', e)
        if len(decompressed_data) != decompressed_size:
            raise BSADecompressionSizeError(
                bsa_name, u'zlib', decompressed_size, len(decompressed_data))
        return decompressed_data

class _Bsa_lz4(_BsaCompressionType):
    """Implements BSA record compression and decompression using lz4. Used
    only for SSE."""
    @staticmethod
    def compress_rec(decompressed_data, bsa_name):
        try:
            return lz4.frame.compress(decompressed_data, store_size=False)
        except RuntimeError as e: # No custom lz4 exception for frames...
            raise BSACompressionError(bsa_name, u'LZ4', e)

    @staticmethod
    def decompress_rec(compressed_data, decompressed_size, bsa_name):
        try:
            decompressed_data = lz4.frame.decompress(compressed_data)
        except RuntimeError as e: # No custom lz4 exception for frames...
            raise BSADecompressionError(bsa_name, u'LZ4', e)
        if len(decompressed_data) != decompressed_size:
            raise BSADecompressionSizeError(
                bsa_name, u'LZ4', decompressed_size, len(decompressed_data))
        return decompressed_data

# Table used in Bethesda's CRC algorithm for BA2 hashing
_BA2_CRC_TABLE = [
    0x00000000, 0x77073096, 0xEE0E612C, 0x990951BA, 0x076DC419, 0x706AF48F,
    0xE963A535, 0x9E6495A3, 0x0EDB8832, 0x79DCB8A4, 0xE0D5E91E, 0x97D2D988,
    0x09B64C2B, 0x7EB17CBD, 0xE7B82D07, 0x90BF1D91, 0x1DB71064, 0x6AB020F2,
    0xF3B97148, 0x84BE41DE, 0x1ADAD47D, 0x6DDDE4EB, 0xF4D4B551, 0x83D385C7,
    0x136C9856, 0x646BA8C0, 0xFD62F97A, 0x8A65C9EC, 0x14015C4F, 0x63066CD9,
    0xFA0F3D63, 0x8D080DF5, 0x3B6E20C8, 0x4C69105E, 0xD56041E4, 0xA2677172,
    0x3C03E4D1, 0x4B04D447, 0xD20D85FD, 0xA50AB56B, 0x35B5A8FA, 0x42B2986C,
    0xDBBBC9D6, 0xACBCF940, 0x32D86CE3, 0x45DF5C75, 0xDCD60DCF, 0xABD13D59,
    0x26D930AC, 0x51DE003A, 0xC8D75180, 0xBFD06116, 0x21B4F4B5, 0x56B3C423,
    0xCFBA9599, 0xB8BDA50F, 0x2802B89E, 0x5F058808, 0xC60CD9B2, 0xB10BE924,
    0x2F6F7C87, 0x58684C11, 0xC1611DAB, 0xB6662D3D, 0x76DC4190, 0x01DB7106,
    0x98D220BC, 0xEFD5102A, 0x71B18589, 0x06B6B51F, 0x9FBFE4A5, 0xE8B8D433,
    0x7807C9A2, 0x0F00F934, 0x9609A88E, 0xE10E9818, 0x7F6A0DBB, 0x086D3D2D,
    0x91646C97, 0xE6635C01, 0x6B6B51F4, 0x1C6C6162, 0x856530D8, 0xF262004E,
    0x6C0695ED, 0x1B01A57B, 0x8208F4C1, 0xF50FC457, 0x65B0D9C6, 0x12B7E950,
    0x8BBEB8EA, 0xFCB9887C, 0x62DD1DDF, 0x15DA2D49, 0x8CD37CF3, 0xFBD44C65,
    0x4DB26158, 0x3AB551CE, 0xA3BC0074, 0xD4BB30E2, 0x4ADFA541, 0x3DD895D7,
    0xA4D1C46D, 0xD3D6F4FB, 0x4369E96A, 0x346ED9FC, 0xAD678846, 0xDA60B8D0,
    0x44042D73, 0x33031DE5, 0xAA0A4C5F, 0xDD0D7CC9, 0x5005713C, 0x270241AA,
    0xBE0B1010, 0xC90C2086, 0x5768B525, 0x206F85B3, 0xB966D409, 0xCE61E49F,
    0x5EDEF90E, 0x29D9C998, 0xB0D09822, 0xC7D7A8B4, 0x59B33D17, 0x2EB40D81,
    0xB7BD5C3B, 0xC0BA6CAD, 0xEDB88320, 0x9ABFB3B6, 0x03B6E20C, 0x74B1D29A,
    0xEAD54739, 0x9DD277AF, 0x04DB2615, 0x73DC1683, 0xE3630B12, 0x94643B84,
    0x0D6D6A3E, 0x7A6A5AA8, 0xE40ECF0B, 0x9309FF9D, 0x0A00AE27, 0x7D079EB1,
    0xF00F9344, 0x8708A3D2, 0x1E01F268, 0x6906C2FE, 0xF762575D, 0x806567CB,
    0x196C3671, 0x6E6B06E7, 0xFED41B76, 0x89D32BE0, 0x10DA7A5A, 0x67DD4ACC,
    0xF9B9DF6F, 0x8EBEEFF9, 0x17B7BE43, 0x60B08ED5, 0xD6D6A3E8, 0xA1D1937E,
    0x38D8C2C4, 0x4FDFF252, 0xD1BB67F1, 0xA6BC5767, 0x3FB506DD, 0x48B2364B,
    0xD80D2BDA, 0xAF0A1B4C, 0x36034AF6, 0x41047A60, 0xDF60EFC3, 0xA867DF55,
    0x316E8EEF, 0x4669BE79, 0xCB61B38C, 0xBC66831A, 0x256FD2A0, 0x5268E236,
    0xCC0C7795, 0xBB0B4703, 0x220216B9, 0x5505262F, 0xC5BA3BBE, 0xB2BD0B28,
    0x2BB45A92, 0x5CB36A04, 0xC2D7FFA7, 0xB5D0CF31, 0x2CD99E8B, 0x5BDEAE1D,
    0x9B64C2B0, 0xEC63F226, 0x756AA39C, 0x026D930A, 0x9C0906A9, 0xEB0E363F,
    0x72076785, 0x05005713, 0x95BF4A82, 0xE2B87A14, 0x7BB12BAE, 0x0CB61B38,
    0x92D28E9B, 0xE5D5BE0D, 0x7CDCEFB7, 0x0BDBDF21, 0x86D3D2D4, 0xF1D4E242,
    0x68DDB3F8, 0x1FDA836E, 0x81BE16CD, 0xF6B9265B, 0x6FB077E1, 0x18B74777,
    0x88085AE6, 0xFF0F6A70, 0x66063BCA, 0x11010B5C, 0x8F659EFF, 0xF862AE69,
    0x616BFFD3, 0x166CCF45, 0xA00AE278, 0xD70DD2EE, 0x4E048354, 0x3903B3C2,
    0xA7672661, 0xD06016F7, 0x4969474D, 0x3E6E77DB, 0xAED16A4A, 0xD9D65ADC,
    0x40DF0B66, 0x37D83BF0, 0xA9BCAE53, 0xDEBB9EC5, 0x47B2CF7F, 0x30B5FFE9,
    0xBDBDF21C, 0xCABAC28A, 0x53B39330, 0x24B4A3A6, 0xBAD03605, 0xCDD70693,
    0x54DE5729, 0x23D967BF, 0xB3667A2E, 0xC4614AB8, 0x5D681B02, 0x2A6F2B94,
    0xB40BBE37, 0xC30C8EA1, 0x5A05DF1B, 0x2D02EF8D,
]
assert len(_BA2_CRC_TABLE) == 256

def _hash_ba2_string(ba2_string):
    """Calculates Bethesda's nonstandard CRC hash for the given string."""
    normalized_string = ba2_string.encode(u'ascii', u'ignore').lower()
    ret = 0
    for c in normalized_string:
        ret = (ret >> 8) ^ _BA2_CRC_TABLE[(ret ^ c) & 0xFF]
    return ret

# Headers ---------------------------------------------------------------------
class _Header(object):
    __slots__ = (u'file_id', u'version')
    formats = [(f, struct_calcsize(f)) for f in (u'4s', u'I')]
    bsa_magic = b'BSA\x00'

    def load_header(self, ins, bsa_name):
        for (fmt, fmt_siz), a in zip(_Header.formats, _Header.__slots__):
            setattr(self, a, struct_unpack(fmt, ins.read(fmt_siz))[0])
        # error checking
        if self.file_id != self.__class__.bsa_magic:
            raise BSAError(bsa_name, f'Magic wrong: got {self.file_id!r}, '
                                     f'expected {self.__class__.bsa_magic}')

class BsaHeader(_Header):
    __slots__ = ( # in the order encountered in the header
         u'folder_records_offset', u'archive_flags', u'folder_count',
         u'file_count', u'total_folder_name_length', u'total_file_name_length',
         u'file_flags')
    formats = [(f, struct_calcsize(f)) for f in [u'I'] * 8]
    header_size = 36

    class _archive_flags(Flags):
        include_directory_names: bool
        include_file_names: bool
        compressed_archive: bool
        retain_directory_names: bool
        retain_file_names: bool
        retain_file_name_offsets: bool
        xbox360_archive: bool
        retain_strings_during_startup: bool
        embed_file_names: bool
        xmem_codec: bool

    def load_header(self, ins, bsa_name):
        super(BsaHeader, self).load_header(ins, bsa_name)
        for (fmt, fmt_siz), a in zip(BsaHeader.formats, BsaHeader.__slots__):
            setattr(self, a, struct_unpack(fmt, ins.read(fmt_siz))[0])
        self.archive_flags = self._archive_flags(self.archive_flags)
        # error checking
        if self.folder_records_offset != self.__class__.header_size:
            msg = f'Header size wrong: {self.folder_records_offset}. Should ' \
                  f'be {self.__class__.header_size}'
            raise BSAError(bsa_name, msg)
        if not self.archive_flags.include_directory_names:
            raise BSAFlagError(bsa_name, "'Has Names For Folders'", 1)
        if not self.archive_flags.include_file_names:
            raise BSAFlagError(bsa_name, "'Has Names For Files'", 2)

    def is_compressed(self): return self.archive_flags.compressed_archive
    def embed_filenames(self): return self.archive_flags.embed_file_names

class Ba2Header(_Header):
    __slots__ = ( # in the order encountered in the header
        u'ba2_files_type', u'ba2_num_files', u'ba2_name_table_offset')
    formats = [(f, struct_calcsize(f)) for f in (u'4s', u'I', u'Q')]
    bsa_magic = b'BTDX'
    file_types = {b'GNRL', b'DX10'} # GNRL=General, DX10=Textures
    header_size = 24

    def load_header(self, ins, bsa_name):
        super(Ba2Header, self).load_header(ins, bsa_name)
        for (fmt, fmt_siz), a in zip(Ba2Header.formats, Ba2Header.__slots__):
            setattr(self, a, struct_unpack(fmt, ins.read(fmt_siz))[0])
        # error checking
        if self.ba2_files_type not in self.file_types:
            err_types = ' or '.join([s.decode('ascii')
                                     for s in self.file_types])
            raise BSAError(
                bsa_name, f'Unrecognised file type: {self.ba2_files_type!r}. '
                          f'Should be {err_types}')

class MorrowindBsaHeader(_Header):
    __slots__ = (u'file_id', u'hash_offset', u'file_count')
    formats = [(f, struct_calcsize(f)) for f in (u'4s', u'I', u'I')]
    bsa_magic = b'\x00\x01\x00\x00'

    def load_header(self, ins, bsa_name):
        for (fmt, fmt_siz), a in zip(MorrowindBsaHeader.formats,
                                     MorrowindBsaHeader.__slots__):
            setattr(self, a, struct_unpack(fmt, ins.read(fmt_siz))[0])
        self.version = None # Morrowind BSAs have no version
        # error checking
        if self.file_id != self.__class__.bsa_magic:
            raise BSAError(bsa_name, u'Magic wrong: got %r, expected %r' % (
                self.file_id, self.__class__.bsa_magic))

class OblivionBsaHeader(BsaHeader):
    __slots__ = ()

    def embed_filenames(self): return False

# Records ---------------------------------------------------------------------
class _HashedRecord(object):
    __slots__ = (u'record_hash',)
    formats = [(u'Q', struct_calcsize(u'Q'))]

    def load_record(self, ins): # make this into a cls static factory?
        f, f_size = _HashedRecord.formats[0]
        self.record_hash, = struct_unpack(f, ins.read(f_size))

    def load_record_from_buffer(self, memview, start):
        f, f_size = _HashedRecord.formats[0]
        self.record_hash, = _unpack_from(f, memview, start)
        return start + f_size

    @classmethod
    def total_record_size(cls):
        return _HashedRecord.formats[0][1]

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.record_hash == other.record_hash
        return NotImplemented
    def __ne__(self, other): return not (self == other)
    def __hash__(self): return self.record_hash
    def __lt__(self, other):
        if isinstance(other, self.__class__):
            return self.record_hash < other.record_hash
        return NotImplemented
    def __ge__(self, other): return not (self < other)
    def __gt__(self, other):
        if isinstance(other, self.__class__):
            return self.record_hash > other.record_hash
        return NotImplemented
    def __le__(self, other): return not (self > other)

    def __repr__(self): return repr(hex(self.record_hash))

# BSAs
class _BsaHashedRecord(_HashedRecord):
    __slots__ = ()

    def load_record(self, ins):
        super(_BsaHashedRecord, self).load_record(ins)
        ins_read = ins.read
        for (fmt, fmt_siz), a in zip(self.__class__.formats,
                                     self.__class__.__slots__):
            setattr(self, a, struct_unpack(fmt, ins_read(fmt_siz))[0])

    def load_record_from_buffer(self, memview, start):
        start = super(_BsaHashedRecord, self).load_record_from_buffer(memview,
                                                                      start)
        for (fmt, fmt_siz), a in zip(self.__class__.formats,
                                     self.__class__.__slots__):
            setattr(self, a, _unpack_from(fmt, memview, start)[0])
            start += fmt_siz
        return start

    @classmethod
    def total_record_size(cls):
        return super(_BsaHashedRecord, cls).total_record_size() + sum(
            f[1] for f in cls.formats)

class BSAFolderRecord(_BsaHashedRecord):
    __slots__ = (u'files_count', u'file_records_offset')
    formats = [(f, struct_calcsize(f)) for f in (u'I', u'I')]

class BSASkyrimSEFolderRecord(_BsaHashedRecord):
    __slots__ = (u'files_count', u'unknown_int', u'file_records_offset')
    formats = [(f, struct_calcsize(f)) for f in (u'I', u'I', u'Q')]

class BSAFileRecord(_BsaHashedRecord):
    __slots__ = (u'file_size_flags', u'raw_file_data_offset')
    formats = [(f, struct_calcsize(f)) for f in (u'I', u'I')]

    def compression_toggle(self): return self.file_size_flags & 0x40000000

    def raw_data_size(self):
        if self.compression_toggle():
            return self.file_size_flags & (~0xC0000000) # negate all flags
        return self.file_size_flags

class BSAMorrowindFileRecord(_HashedRecord):
    """Morrowind BSAs have an array of sizes and offsets, then an array of name
    lengths, then an array of names and finally an array of hashes. These must
    all be loaded in order. Additionally, Morrowind has no folder records, so
    all these arrays correspond to a long list of file records."""
    # Note: We (ab)use the use of zip() here to reserve file_name without
    # actually loading it.
    __slots__ = (u'file_size', u'relative_offset', u'file_name')
    formats = [(f, struct_calcsize(f)) for f in (u'I', u'I')]

    def load_record(self, ins):
        for f, a in zip(self.__class__.formats, self.__class__.__slots__):
            setattr(self, a, struct_unpack(f[0], ins.read(f[1]))[0])

    def load_record_from_buffer(self, memview, start):
        for f, a in zip(self.__class__.formats, self.__class__.__slots__):
            setattr(self, a, _unpack_from(f[0], memview, start)[0])
            start += f[1]
        return start

    def load_hash(self, ins):
        """Loads the hash from the specified input stream."""
        super(BSAMorrowindFileRecord, self).load_record(ins)

    def load_hash_from_buffer(self, memview, start):
        """Loads the hash from the specified memory buffer."""
        super(BSAMorrowindFileRecord, self).load_record_from_buffer(memview,
                                                                    start)

    def __repr__(self):
        return f'{super().__repr__()}: {self.file_name}'

class BSAOblivionFileRecord(BSAFileRecord):
    # Note: Here, we (ab)use the usage of zip() in _BsaHashedRecord.load_record
    # to make sure that the last slot, file_pos, is not read from the BSA - we
    # fill it manually in our load_record override. This is necessary to find
    # the positions of hashes for undo_alterations().
    __slots__ = (u'file_size_flags', u'raw_file_data_offset', u'file_pos')
    formats = [(f, struct_calcsize(f)) for f in (u'I', u'I')]

    def load_record(self, ins):
        self.file_pos = ins.tell()
        super(BSAOblivionFileRecord, self).load_record(ins)

# BA2s
class Ba2FileRecordGeneral(_BsaHashedRecord):
    # unused1 is always BAADF00D
    __slots__ = (u'file_extension', u'dir_hash', u'unknown1', u'offset',
                 u'packed_size', u'unpacked_size', u'unused1')
    formats = [(f, struct_calcsize(f)) for f in (u'4s', u'I', u'I', u'Q', u'I',
                                                 u'I', u'I')]

class Ba2FileRecordTexture(_BsaHashedRecord):
    # chunk_header_size is always 24, tex_chunks is reserved in slots but not
    # read via formats - see load_record below
    __slots__ = (u'file_extension', u'dir_hash', u'unknown_tex',
                 u'num_chunks', u'chunk_header_size', u'height', u'width',
                 u'num_mips', u'dxgi_format', u'cube_maps', u'tex_chunks')
    formats = [(f, struct_calcsize(f)) for f in (u'4s', u'I', u'B', u'B', u'H',
                                                 u'H', u'H', u'B', u'B', u'H')]

    def load_record(self, ins):
        super(Ba2FileRecordTexture, self).load_record(ins)
        self.dxgi_format = mk_dxgi_fmt(self.dxgi_format)
        self.tex_chunks = []
        append_tex_chunk = self.tex_chunks.append
        for x in range(self.num_chunks):
            tex_chunk = Ba2TexChunk()
            tex_chunk.load_chunk(ins)
            append_tex_chunk(tex_chunk)

class Ba2TexChunk(object):
    """BA2 texture chunk, used in texture file records."""
    # unused1 is always BAADF00D
    __slots__ = (u'offset', u'packed_size', u'unpacked_size', u'start_mip',
                 u'end_mip', u'unused1')
    formats = [(f, struct_calcsize(f)) for f in (u'Q', u'I', u'I', u'H', u'H',
                                                 u'I')]

    def load_chunk(self, ins): ##: Centralize this, copy-pasted everywhere
        for (fmt, fmt_siz), a in zip(Ba2TexChunk.formats, Ba2TexChunk.__slots__):
            setattr(self, a, struct_unpack(fmt, ins.read(fmt_siz))[0])

    def __repr__(self):
        return f'Ba2TexChunk<mipmaps #{self.start_mip:d} to #{self.end_mip:d}>'

# Bsa content abstraction -----------------------------------------------------
class BSAFolder(object):
    folder_assets: dict[str, BSAFileRecord]

    def __init__(self, folder_record):
        self.folder_record = folder_record
        self.folder_assets = {} # keep files order

class BSAOblivionFolder(BSAFolder):
    folder_assets: dict[str, BSAOblivionFileRecord]

class Ba2Folder(object):

    def __init__(self):
        self.folder_assets = {} # keep files order

# Files -----------------------------------------------------------------------
class ABsa(AFile):
    bsa_header: BsaHeader
    _assets: frozenset[str] = None
    _compression_type: _BsaCompressionType = _Bsa_zlib
    _folder_type = BSAFolder
    bsa_folders: defaultdict[str, _folder_type]

    def __init__(self, fullpath, load_cache=False, names_only=True):
        super(ABsa, self).__init__(fullpath)
        self.bsa_name = self.abs_path.stail
        self.bsa_header = typing.get_type_hints(self.__class__)['bsa_header']()
        self.bsa_folders = defaultdict(self._folder_type) # keep folder order
        self._filenames = []
        self.total_names_length = 0 # reported wrongly at times - calculate it
        if load_cache: self.__load(names_only)

    def inspect_version(self):
        """Returns the version of this BSA."""
        with self.abs_path.open(u'rb') as ins:
            try:
                self.bsa_header.load_header(ins, self.bsa_name)
            except struct_error as e:
                raise BSAError(self.bsa_name,
                               f'Error while unpacking header: {e!r}')
            return self.bsa_header.version

    def __load(self, names_only):
        try:
            if not names_only:
                self._load_bsa()
            else:
                self._load_bsa_light()
        except struct_error as e:
            raise BSAError(self.bsa_name, f'Error while unpacking: {e!r}')

    @staticmethod
    def _map_files_to_folders(asset_paths): # lowercase keys and values
        folder_file = []
        for a in asset_paths:
            split = a.rsplit(os.sep, 1)
            if len(split) == 1:
                split = ['', split[0]]
            folder_file.append(split)
        # group files by folder
        folder_files_dict = {}
        folder_file.sort(key=itemgetter(0)) # sort first then group
        for key, val in groupby(folder_file, key=itemgetter(0)):
            folder_files_dict[key.lower()] = {dest.lower() for _key, dest
                                              in val}
        return folder_files_dict

    def extract_assets(self, asset_paths, dest_folder, progress=None):
        """Extracts certain assets from this BSA into the specified folder.

        :param asset_paths: An iterable specifying which files should be
            extracted. Path separators in these *must* match the OS.
        :param dest_folder: The folder into which the results should be
            extracted.
        :param progress: The progress callback to use. None if unwanted."""
        folder_files_dict = self._map_files_to_folders(asset_paths)
        del asset_paths # forget about this
        # load the bsa - this should be reworked to load only needed records
        self._load_bsa()
        folder_to_assets = self._map_assets_to_folders(folder_files_dict)
        # unload the bsa
        self.bsa_folders.clear()
        # get the data from the file
        global_compression = self.bsa_header.is_compressed()
        if progress:
            progress.setFull(len(folder_to_assets))
        with open(self.abs_path, u'rb') as bsa_file:
            for i, (folder, file_records) in enumerate(folder_to_assets.items()):
                if progress:
                    progress(i, f'Extracting {self.bsa_name}...\n{folder}')
                # BSA paths always have backslashes, so we need to convert them
                # to the platform's path separators before we extract
                target_dir = os.path.join(dest_folder, *folder.split(path_sep))
                os.makedirs(target_dir, exist_ok=True)
                for filename, record in file_records:
                    data_size = record.raw_data_size()
                    bsa_file.seek(record.raw_file_data_offset)
                    if self.bsa_header.embed_filenames(): # use len(filename) ?
                        filename_len = unpack_byte(bsa_file)
                        bsa_file.seek(filename_len, 1) # discard filename
                        data_size -= filename_len + 1
                    if global_compression ^ record.compression_toggle():
                        # This is a compressed record, so decompress it
                        uncompressed_size = unpack_int(bsa_file)
                        data_size -= 4
                        try:
                            raw_data = self._compression_type.decompress_rec(
                                bsa_file.read(data_size), uncompressed_size,
                                self.bsa_name)
                        except BSAError:
                            # Ignore errors for Fallout - Misc.bsa - Bethesda
                            # probably used an old buggy zlib version when
                            # packing it (taken from BSArch sources)
                            if self.bsa_name == u'Fallout - Misc.bsa':
                                continue
                            else:
                                raise
                    else:
                        # This is an uncompressed record, just read it
                        raw_data = bsa_file.read(data_size)
                    with open(os.path.join(target_dir, filename), 'wb') as out:
                        out.write(raw_data)

    def _map_assets_to_folders(self, folder_files_dict):
        folder_to_assets = {}
        for folder_path, bsa_folder in self.bsa_folders.items():
            if folder_path.lower() not in folder_files_dict: continue
            # Has assets we need to extract. Keep order to avoid seeking
            # back and forth in the file
            folder_to_assets[folder_path] = file_records = []
            filenames = folder_files_dict[folder_path.lower()]
            for filename, filerecord in bsa_folder.folder_assets.items():
                if filename.lower() not in filenames: continue
                file_records.append((filename, filerecord))
        return folder_to_assets

    # Abstract
    def _load_bsa(self): raise NotImplementedError
    def _load_bsa_light(self): raise NotImplementedError

    # API - delegates to abstract methods above
    def has_assets(self, asset_paths):
        """Checks if this BSA has the requested assets and returns a list of
        assets out of those that it contains.

        :param asset_paths: The paths to check. Path separators in these *must*
            match the OS."""
        cached_assets = self.assets
        matched_assets = []
        add_asset = matched_assets.append
        for a in asset_paths:
            # self.assets uses OS path separators, so this is fine
            if a.lower() in cached_assets:
                add_asset(a)
        return matched_assets

    @property
    def assets(self) -> frozenset[str]:
        """Set of full paths in the bsa in lowercase and using the OS path
        separator."""
        wanted_assets = self._assets
        if wanted_assets is None:
            self.__load(names_only=True)
            self._assets = wanted_assets = frozenset(
                convert_separators(f.lower()) for f in self._filenames)
            del self._filenames[:]
        return wanted_assets

class BSA(ABsa):
    """Bsa file. Notes:
    - We require that include_directory_names and include_file_names are True.
    - consider using the filenames from data block in load_light, if they
    are embedded."""
    file_record_type = BSAFileRecord
    folder_record_type = BSAFolderRecord

    def _load_bsa(self):
        folder_records = [] # we need those to parse the folder names
        self.bsa_folders.clear()
        file_records = []
        read_file_record = partial(self._read_file_records, file_records,
                                   folders=self.bsa_folders)
        file_names = self._read_bsa_file(folder_records, read_file_record)
        names_record_index = file_records_index = 0
        for folder_path, bsa_folder in self.bsa_folders.items():
            for __ in range(bsa_folder.folder_record.files_count):
                rec = file_records[file_records_index]
                file_records_index += 1
                filename = _decode_path(
                    file_names[names_record_index], self.bsa_name)
                names_record_index += 1
                bsa_folder.folder_assets[filename] = rec

    @classmethod
    def _read_file_records(cls, file_records, bsa_file, folder_path,
                           folder_record, folders=None):
        folders[folder_path] = BSAFolder(folder_record)
        for __ in range(folder_record.files_count):
            rec = cls.file_record_type()
            rec.load_record(bsa_file)
            file_records.append(rec)

    def _load_bsa_light(self):
        folder_records = [] # we need those to parse the folder names
        folder_path_record: dict[str, BSAFolderRecord] = {}
        rs = self.file_record_type.total_record_size()
        def _discard_file_records(bsa_file, folder_name, folder_record,
                __rs=rs):
            bsa_file.seek(__rs * folder_record.files_count, 1)
            folder_path_record[folder_name] = folder_record
        file_names = self._read_bsa_file(folder_records, _discard_file_records)
        start = 0
        names_pairs = ((folder_path, file_names[start: (
            start := (start + folder_record.files_count))]) for
            folder_path, folder_record in folder_path_record.items())
        try:
            self._filenames = [*chain.from_iterable(
                # Inlined from _decode_path for startup performance - no
                # need to replace slashes though since these are file names
                (f'{fp}{path_sep}{fname.decode(_bsa_encoding)}' for
                 fname in fnames) for fp, fnames in names_pairs)]
        except UnicodeDecodeError:
            raise BSADecodingError(self.bsa_name, file_names)

    def _read_bsa_file(self, folder_records, read_file_records) -> list[bytes]:
        total_names_length = 0
        my_bsa_name = self.bsa_name
        with open(self.abs_path, u'rb') as bsa_file:
            bsa_seek = bsa_file.seek
            bsa_read = bsa_file.read
            # load the header from input stream
            self.bsa_header.load_header(bsa_file, my_bsa_name)
            # load the folder records from input stream
            folder_rec_type = self.__class__.folder_record_type
            append_folder_rec = folder_records.append
            for __ in range(self.bsa_header.folder_count):
                rec = folder_rec_type()
                rec.load_record(bsa_file)
                append_folder_rec(rec)
            # load the file record block
            for folder_record in folder_records:
                ##: This is unused - overwritten immediately afterwards. May
                # have been intended to be used though?
                #folder_path = u'?%d' % folder_record.record_hash # hack - untested
                name_size = unpack_byte(bsa_file)
                if not name_size:
                    # Files sit at root level - read nothing
                    folder_path = ''
                    # Size is summed as strlen() + 1, so use +1 for root
                    total_names_length += 1
                else:
                    folder_path = _decode_path(bsa_read(name_size - 1),
                        my_bsa_name)
                    bsa_seek(1, 1) # discard null terminator
                    total_names_length += name_size
                read_file_records(bsa_file, folder_path, folder_record)
            if total_names_length != self.bsa_header.total_folder_name_length:
                deprint(f'{self.abs_path} reports wrong folder names length '
                        f'{self.bsa_header.total_folder_name_length:d} - '
                        f'actual: {total_names_length:d} (number of folders '
                        f'is {self.bsa_header.folder_count:d})')
            self.total_names_length = total_names_length
            file_names = bsa_read( # has an empty string at the end
                self.bsa_header.total_file_name_length).split(b'\00')
            # close the file
        return file_names

class BA2(ABsa):
    bsa_header: Ba2Header
    _folder_type = Ba2Folder
    bsa_folders: defaultdict[str, _folder_type] # we need to repeat this

    def extract_assets(self, asset_paths, dest_folder, progress=None):
        # map files to folders
        folder_files_dict = self._map_files_to_folders(asset_paths)
        del asset_paths # forget about this
        # load the bsa - this should be reworked to load only needed records
        self._load_bsa()
        my_header = self.bsa_header
        is_dx10 = my_header.ba2_files_type == b'DX10'
        folder_to_assets = self._map_assets_to_folders(folder_files_dict)
        # unload the bsa
        self.bsa_folders.clear()
        # get the data from the file
        if progress:
            progress.setFull(len(folder_to_assets))
        with open(self.abs_path, u'rb') as bsa_file:
            def _read_rec_or_chunk(record):
                """Helper method, handles reading both compressed and
                uncompressed records (or texture chunks)."""
                bsa_file.seek(record.offset)
                if record.packed_size:
                    # This is a compressed record, so decompress it
                    return self._compression_type.decompress_rec(
                        bsa_file.read(record.packed_size),
                        record.unpacked_size, self.bsa_name)
                else:
                    # This is an uncompressed record, just read it
                    return bsa_file.read(record.unpacked_size)
            def _build_dds_header(dds_file, record):
                """Helper method, sets up a functional DDS header for the
                specified DDS file based on the specified record."""
                dds_file.dds_header.dw_height = record.height
                dds_file.dds_header.dw_width = record.width
                dds_file.dds_header.dw_mip_map_count = record.num_mips
                dds_file.dds_header.dw_depth = 1
                # 3 == DDS_DIMENSION_TEXTURE2D - PY3: enum!
                dds_file.dds_dxt10.resource_dimension = 3
                dds_file.dds_dxt10.array_size = 1
                if record.cube_maps == 2049:
                    dds_file.dds_header.dw_caps.DDSCAPS_COMPLEX = True
                    # All but DDSCAPS2_VOLUME or'd together
                    # Archive.exe sticks these into dwCaps, which is 100%
                    # wrong, but that's DDS for you...
                    dds_file.dds_header.dw_caps2 = 0xFE00
                    # 0x4 == DDS_RESOURCE_MISC_TEXTURECUBE
                    dds_file.dds_dxt10.misc_flag = 0x4
                # This needs to be last, it uses the header's width and height
                record.dxgi_format.setup_file(
                    dds_file, use_legacy_formats=True)
            for i, (folder, file_records) in enumerate(
                    folder_to_assets.items()):
                if progress:
                    progress(i, f'Extracting {self.bsa_name}...\n{folder}')
                # BSA paths always have backslashes, so we need to convert them
                # to the platform's path separators before we extract
                target_dir = os.path.join(dest_folder, *folder.split(path_sep))
                os.makedirs(target_dir, exist_ok=True)
                for filename, f_record in file_records:
                    if is_dx10:
                        # We're dealing with a DX10 BA2, need to combine all
                        # the texture chunks in the record first
                        dds_data = b''
                        for tex_chunk in f_record.tex_chunks:
                            dds_data += _read_rec_or_chunk(tex_chunk)
                        # Add a DDS header based on the data in the record,
                        # then dump the resulting DDS file - cf. BSArch
                        new_dds_file = DDSFile('')
                        _build_dds_header(new_dds_file, f_record)
                        new_dds_file.dds_contents = dds_data
                        raw_data = new_dds_file.dump_file()
                    else:
                        # Otherwise, we're dealing with a GNRL BA2, just
                        # read/decompress/write the record directly
                        raw_data = _read_rec_or_chunk(f_record)
                    with open(os.path.join(target_dir, filename), 'wb') as out:
                        out.write(raw_data)

    def _load_bsa(self):
        with open(self.abs_path, u'rb') as bsa_file:
            # load the header from input stream
            my_header = self.bsa_header
            my_header.load_header(bsa_file, self.bsa_name)
            # load the folder records from input stream
            if my_header.ba2_files_type == b'GNRL':
                file_record_type = Ba2FileRecordGeneral
            else:
                file_record_type = Ba2FileRecordTexture
            file_records = []
            for __ in range(my_header.ba2_num_files):
                rec = file_record_type()
                rec.load_record(bsa_file)
                file_records.append(rec)
            # load the file names block
            bsa_file.seek(my_header.ba2_name_table_offset)
            file_names_block = memoryview(bsa_file.read())
        for index in range(my_header.ba2_num_files):
            name_size = _unpack_from(u'H', file_names_block)[0]
            filename = _decode_path(
                file_names_block[2:name_size + 2].tobytes(), self.bsa_name)
            file_names_block = file_names_block[name_size + 2:]
            folder_dex = filename.rfind(path_sep)
            folder_name = '' if folder_dex == -1 else filename[:folder_dex]
            self.bsa_folders[folder_name].folder_assets[
                filename[folder_dex + 1:]] = file_records[index]

    def _load_bsa_light(self):
        my_header = self.bsa_header
        with open(self.abs_path, u'rb') as bsa_file:
            # load the header from input stream
            my_header.load_header(bsa_file, self.bsa_name)
            # load the file names block
            bsa_file.seek(my_header.ba2_name_table_offset)
            file_names_block = memoryview(bsa_file.read())
        filenames = []
        for index in range(my_header.ba2_num_files):
            name_size = _unpack_from(u'H', file_names_block)[0]
            filename = _decode_path(
                file_names_block[2:name_size + 2].tobytes(), self.bsa_name)
            filenames.append(filename)
            file_names_block = file_names_block[name_size + 2:]
        self._filenames = filenames

    def ba2_hash(self):
        """Calculates Bethesda's nonstandard CRC hash for the filename of this
        BA2. Only the filename needs to be compared, since the extension is
        always the same and the BA2s will always be in the same folder
        (Data)."""
        return _hash_ba2_string(self.abs_path.sbody)

class MorrowindBsa(ABsa):
    bsa_header: MorrowindBsaHeader

    def _load_bsa_light(self):
        self.file_records = []
        with open(self.abs_path, u'rb') as bsa_file:
            # load the header from input stream
            self.bsa_header.load_header(bsa_file, self.bsa_name)
            # load each file record
            for x in range(self.bsa_header.file_count):
                rec = BSAMorrowindFileRecord()
                rec.load_record(bsa_file)
                self.file_records.append(rec)
            # skip name offsets - we don't need them, since the strings are
            # null-terminated. Additionally, these seem to sometimes be
            # incorrect - perhaps created by bad tools?
            bsa_file.seek(4 * self.bsa_header.file_count, 1)
            # load names and hashes, also take the opportunity to fill
            # _filenames
            for file_record in self.file_records:
                read_name = b''
                while True:
                    candidate = bsa_file.read(1)
                    if candidate == b'\x00': break  # null terminator
                    read_name += candidate
                file_record.file_name = _decode_path(read_name, self.bsa_name)
                self._filenames.append(file_record.file_name)
            for file_record in self.file_records:
                file_record.load_hash(bsa_file)
            # remember the final offset, since the stored offsets are relative
            # to this
            self.final_offset = bsa_file.tell()

    _load_bsa = _load_bsa_light

    # We override this because Morrowind has no folder records, so we can
    # achieve better performance with a dedicated method
    def extract_assets(self, asset_paths, dest_folder, progress=None):
        # Speed up target_records construction
        if not isinstance(asset_paths, (frozenset, set)):
            asset_paths = frozenset(asset_paths)
        self._load_bsa()
        # Keep only the file records that correspond to asset_paths
        target_records = [x for x in self.file_records
                          if x.file_name in asset_paths]
        if progress:
            progress.setFull(len(target_records))
        with open(self.abs_path, u'rb') as bsa_file:
            for i, file_record in enumerate(target_records):
                rec_name = file_record.file_name
                if progress:
                    # No folder records, simulate them to avoid updating the
                    # progress bar too frequently
                    progress(i, f'Extracting {self.bsa_name}...\n'
                                f'{os.path.dirname(rec_name)}')
                # There is no compression for Morrowind BSAs, but all offsets
                # are relative to the final_offset we read earlier
                bsa_file.seek(self.final_offset + file_record.relative_offset)
                # Finally, simply read from the BSA file and write out the
                # result, making sure to create any needed directories
                raw_data = bsa_file.read(file_record.file_size)
                out_path = os.path.join(dest_folder, rec_name)
                target_dir = os.path.dirname(out_path)
                os.makedirs(target_dir, exist_ok=True)
                with open(out_path, u'wb') as out:
                    out.write(raw_data)

class OblivionBsa(BSA):
    bsa_header: OblivionBsaHeader
    file_record_type = BSAOblivionFileRecord
    _folder_type = BSAOblivionFolder
    bsa_folders: defaultdict[str, _folder_type] # for proper typing
    # A dictionary mapping file extensions to hash components. Used by Oblivion
    # when hashing file names for its BSAs.
    _bsa_ext_lookup = defaultdict(int, [('.kf', 0x80),
        ('.nif', 0x8000), ('.dds', 0x8080), ('.wav', 0x80000000)])

    @staticmethod
    def calculate_hash(filename):
        """Calculates the hash used by Oblivion BSAs for the provided file
        name.
        Based on Timeslips code with cleanup and pythonization.

        See here for more information:
        https://en.uesp.net/wiki/Tes4Mod:Hash_Calculation"""
        #--NOTE: fileName is NOT a Path object!
        root, ext = os.path.splitext(filename.lower())
        chars = [ord(x) for x in root]
        hash_part_1 = chars[-1] | ((len(chars) > 2 and chars[-2]) or 0) << 8 \
                      | len(chars) << 16 | chars[0] << 24
        hash_part_1 |= OblivionBsa._bsa_ext_lookup[ext]
        uint_mask, hash_part_2, hash_part_3 = 0xFFFFFFFF, 0, 0
        for char in chars[1:-2]:
            hash_part_2 = ((hash_part_2 * 0x1003F) + char) & uint_mask
        for char in (ord(x) for x in ext):
            hash_part_3 = ((hash_part_3 * 0x1003F) + char) & uint_mask
        hash_part_2 = (hash_part_2 + hash_part_3) & uint_mask
        return (hash_part_2 << 32) + hash_part_1

    def undo_alterations(self, progress=Progress()):
        """Undoes any alterations that previously applied BSA Alteration may
        have done to this BSA by recalculating all mismatched hashes.

        NOTE: In order for this method to do anything, the BSA must be fully
        loaded - that means you must either pass load_cache=True and
        names_only=False to the constructor, or call _load_bsa() (NOT
        _load_bsa_light() !) before calling this method.

        See this link for an in-depth overview of BSA Alteration and the
        problem it tries to solve:
        http://devnull.sweetdanger.com/archiveinvalidation.html

        :param progress: The progress indicator to use for this process."""
        progress.setFull(self.bsa_header.folder_count)
        with open(self.abs_path, 'r+b') as bsa_file:
            reset_count = 0
            for folder_name, folder in self.bsa_folders.items():
                for filename, file_info in folder.folder_assets.items():
                    rebuilt_hash = self.calculate_hash(filename)
                    if file_info.record_hash != rebuilt_hash:
                        bsa_file.seek(file_info.file_pos)
                        bsa_file.write(
                            structs_cache[_HashedRecord.formats[0][0]].pack(
                                rebuilt_hash))
                        reset_count += 1
                progress(progress.state + 1, 'Rebuilding Hashes...\n' +
                         folder_name)
        return reset_count

class SkyrimSeBsa(BSA):
    folder_record_type = BSASkyrimSEFolderRecord
    _compression_type = _Bsa_lz4

# Factory
def get_bsa_type(game_fsName) -> type[ABsa]:
    """Return the bsa type for this game."""
    if game_fsName == 'Morrowind':
        return MorrowindBsa
    elif game_fsName == 'Oblivion':
        return OblivionBsa
    elif game_fsName in ('Enderal', 'Fallout3', 'FalloutNV', 'Skyrim'):
        return BSA
    elif game_fsName in ('Skyrim Special Edition', 'Skyrim VR',
                         'Enderal Special Edition'):
        return SkyrimSeBsa
    # TODO(SF) verify BA2 has not changed
    elif game_fsName in ('Fallout4', 'Fallout4VR', 'Starfield'):
        # Hashes are I not Q in BA2s!
        _HashedRecord.formats = [('I', struct_calcsize('I'))]
        return BA2
    else:
        raise RuntimeError(f'BSAs not supported for {game_fsName} yet')
