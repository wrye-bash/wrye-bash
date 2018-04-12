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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""Bsa files.

For the file format see:
http://www.uesp.net/wiki/Tes4Mod:BSA_File_Format
http://www.uesp.net/wiki/Tes5Mod:Archive_File_Format
"""

__author__ = u'Utumno'

import collections
import errno
import lz4.frame
import os
import struct
import zlib
from functools import partial
from itertools import groupby, imap
from operator import itemgetter
from .dds_files import DDSFile, mk_dxgi_fmt
from ..bolt import deprint, Progress, struct_pack, struct_unpack, \
    unpack_byte, unpack_string, unpack_int, Flags, AFile
from ..exception import AbstractError, BSAError, BSADecodingError, \
    BSAFlagError, BSACompressionError, BSADecompressionError, \
    BSADecompressionSizeError

_bsa_encoding = u'cp1252' #rumor has it that's the files/folders names encoding
path_sep = u'\\'

# Utilities -------------------------------------------------------------------
def _decode_path(string_path, bsa_name):
    try:
        return unicode(string_path, encoding=_bsa_encoding)
    except UnicodeDecodeError:
        raise BSADecodingError(bsa_name, string_path)

class _BsaCompressionType(object):
    """Abstractly represents a way of compressing and decompressing BSA
    records."""
    @staticmethod
    def compress_rec(decompressed_data, bsa_name):
        """Compresses the specified record data. Raises a BSAError if the
        underlying compression library raises an error. Returns the resulting
        compressed data."""
        raise AbstractError()

    @staticmethod
    def decompress_rec(compressed_data, decompressed_size, bsa_name):
        """Decompresses the specified record data. Expects the specified
        number of bytes of decompressed data and raises a BSAError if a
        mismatch occurs or if the underlying compression library raises an
        error. Returns the resulting decompressed data."""
        raise AbstractError()

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

# Headers ---------------------------------------------------------------------
class _Header(object):
    __slots__ = (u'file_id', u'version')
    formats = [(f, struct.calcsize(f)) for f in (u'4s', u'I')]
    bsa_magic = b'BSA\x00'

    def load_header(self, ins, bsa_name):
        for fmt, attr in zip(_Header.formats, _Header.__slots__):
            self.__setattr__(attr, struct_unpack(fmt[0], ins.read(fmt[1]))[0])
        # error checking
        if self.file_id != self.__class__.bsa_magic:
            raise BSAError(bsa_name, u'Magic wrong: got %r, expected %r' % (
                self.file_id, self.__class__.bsa_magic))

class BsaHeader(_Header):
    __slots__ = ( # in the order encountered in the header
         u'folder_records_offset', u'archive_flags', u'folder_count',
         u'file_count', u'total_folder_name_length', u'total_file_name_length',
         u'file_flags')
    formats = [(f, struct.calcsize(f)) for f in [u'I'] * 8]
    header_size = 36
    _archive_flags = Flags(0, Flags.getNames(
        u'include_directory_names',
        u'include_file_names',
        u'compressed_archive',
        u'retain_directory_names',
        u'retain_file_names',
        u'retain_file_name_offsets',
        u'xbox360_archive',
        u'retain_strings_during_startup',
        u'embed_file_names',
        u'xmem_codec',
    ))

    def load_header(self, ins, bsa_name):
        super(BsaHeader, self).load_header(ins, bsa_name)
        for fmt, attr in zip(BsaHeader.formats, BsaHeader.__slots__):
            self.__setattr__(attr, struct_unpack(fmt[0], ins.read(fmt[1]))[0])
        self.archive_flags = self._archive_flags(self.archive_flags)
        # error checking
        if self.folder_records_offset != self.__class__.header_size:
            raise BSAError(bsa_name, u'Header size wrong: %r. Should be %r' % (
                self.folder_records_offset, self.__class__.header_size))
        if not self.archive_flags.include_directory_names:
            raise BSAFlagError(bsa_name, u"'Has Names For Folders'", 1)
        if not self.archive_flags.include_file_names:
            raise BSAFlagError(bsa_name, u"'Has Names For Files'", 2)

    def is_compressed(self): return self.archive_flags.compressed_archive
    def embed_filenames(self): return self.archive_flags.embed_file_names

class Ba2Header(_Header):
    __slots__ = ( # in the order encountered in the header
        u'ba2_files_type', u'ba2_num_files', u'ba2_name_table_offset')
    formats = [(f, struct.calcsize(f)) for f in (u'4s', u'I', u'Q')]
    bsa_magic = b'BTDX'
    file_types = {b'GNRL', b'DX10'} # GNRL=General, DX10=Textures
    header_size = 24

    def load_header(self, ins, bsa_name):
        super(Ba2Header, self).load_header(ins, bsa_name)
        for fmt, attr in zip(Ba2Header.formats, Ba2Header.__slots__):
            self.__setattr__(attr, struct_unpack(fmt[0], ins.read(fmt[1]))[0])
        # error checking
        if not self.ba2_files_type in self.file_types:
            raise BSAError(bsa_name, u'Unrecognised file type: %r. Should be '
                                     u'%s' % (
                self.ba2_files_type, u' or '.join(self.file_types)))

class MorrowindBsaHeader(_Header):
    __slots__ = (u'file_id', u'hash_offset', u'file_count')
    formats = [(f, struct.calcsize(f)) for f in (u'4s', u'I', u'I')]
    bsa_magic = b'\x00\x01\x00\x00'

    def load_header(self, ins, bsa_name):
        for fmt, attr in zip(MorrowindBsaHeader.formats,
                             MorrowindBsaHeader.__slots__):
            self.__setattr__(attr, struct_unpack(fmt[0], ins.read(fmt[1]))[0])
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
    formats = [(u'Q', struct.calcsize(u'Q'))]

    def load_record(self, ins):
        fmt, fmt_siz = _HashedRecord.formats[0]
        self.record_hash, = struct_unpack(fmt, ins.read(fmt_siz))

    def load_record_from_buffer(self, memview, start):
        fmt, fmt_siz = _HashedRecord.formats[0]
        self.record_hash, = struct.unpack_from(fmt, memview, start)
        return start + fmt_siz

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
        for fmt, attr in zip(self.__class__.formats, self.__class__.__slots__):
            self.__setattr__(attr, struct_unpack(fmt[0], ins.read(fmt[1]))[0])

    def load_record_from_buffer(self, memview, start):
        start = super(_BsaHashedRecord, self).load_record_from_buffer(memview,
                                                                      start)
        for fmt, attr in zip(self.__class__.formats, self.__class__.__slots__):
            self.__setattr__(attr,
                             struct.unpack_from(fmt[0], memview, start)[0])
            start += fmt[1]
        return start

    @classmethod
    def total_record_size(cls):
        return super(_BsaHashedRecord, cls).total_record_size() + sum(
            f[1] for f in cls.formats)

class BSAFolderRecord(_BsaHashedRecord):
    __slots__ = (u'files_count', u'file_records_offset')
    formats = [(f, struct.calcsize(f)) for f in (u'I', u'I')]

class BSASkyrimSEFolderRecord(_BsaHashedRecord):
    __slots__ = (u'files_count', u'unknown_int', u'file_records_offset')
    formats = [(f, struct.calcsize(f)) for f in (u'I', u'I', u'Q')]

class BSAFileRecord(_BsaHashedRecord):
    __slots__ = (u'file_size_flags', u'raw_file_data_offset')
    formats = [(f, struct.calcsize(f)) for f in (u'I', u'I')]

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
    formats = [(f, struct.calcsize(f)) for f in (u'I', u'I')]

    def load_record(self, ins):
        for fmt, attr in zip(self.__class__.formats, self.__class__.__slots__):
            self.__setattr__(attr, struct_unpack(fmt[0], ins.read(fmt[1]))[0])

    def load_record_from_buffer(self, memview, start):
        for fmt, attr in zip(self.__class__.formats, self.__class__.__slots__):
            self.__setattr__(attr,
                             struct.unpack_from(fmt[0], memview, start)[0])
            start += fmt[1]
        return start

    def load_name(self, ins, bsa_name):
        """Loads the file name from the specified input stream."""
        read_name = b''
        while(True):
            candidate = ins.read(1)
            if candidate == b'\x00': break # null terminator
            read_name += candidate
        self.file_name = _decode_path(read_name, bsa_name)

    def load_name_from_buffer(self, memview, start, bsa_name):
        """Loads the file name from the specified memory buffer."""
        read_name = b''
        offset = 0
        while(True):
            candidate = memview[start + offset]
            if candidate == b'\x00': break # null terminator
            read_name += candidate
            offset += 1
        self.file_name = _decode_path(read_name, bsa_name)

    def load_hash(self, ins):
        """Loads the hash from the specified input stream."""
        super(BSAMorrowindFileRecord, self).load_record(ins)

    def load_hash_from_buffer(self, memview, start):
        """Loads the hash from the specified memory buffer."""
        super(BSAMorrowindFileRecord, self).load_record_from_buffer(memview,
                                                                    start)

    def __repr__(self):
        return super(BSAMorrowindFileRecord, self).__repr__() + (
                u': %r' % self.file_name)

class BSAOblivionFileRecord(BSAFileRecord):
    # Note: Here, we (ab)use the usage of zip() in _BsaHashedRecord.load_record
    # to make sure that the last slot, file_pos, is not read from the BSA - we
    # fill it manually in our load_record override. This is necessary to find
    # the positions of hashes for undo_alterations().
    __slots__ = (u'file_size_flags', u'raw_file_data_offset', u'file_pos')
    formats = [(f, struct.calcsize(f)) for f in (u'I', u'I')]

    def load_record(self, ins):
        self.file_pos = ins.tell()
        super(BSAOblivionFileRecord, self).load_record(ins)

# BA2s
class Ba2FileRecordGeneral(_BsaHashedRecord):
    # unused1 is always BAADF00D
    __slots__ = (u'file_extension', u'dir_hash', u'unknown1', u'offset',
                 u'packed_size', u'unpacked_size', u'unused1')
    formats = [(f, struct.calcsize(f)) for f in (u'4s', u'I', u'I', u'Q', u'I',
                                                 u'I', u'I')]

class Ba2FileRecordTexture(_BsaHashedRecord):
    # chunk_header_size is always 24, tex_chunks is reserved in slots but not
    # read via formats - see load_record below
    __slots__ = (u'file_extension', u'dir_hash', u'unknown_tex',
                 u'num_chunks', u'chunk_header_size', u'height', u'width',
                 u'num_mips', u'dxgi_format', u'cube_maps', u'tex_chunks')
    formats = [(f, struct.calcsize(f)) for f in (u'4s', u'I', u'B', u'B', u'H',
                                                 u'H', u'H', u'B', u'B', u'H')]

    def load_record(self, ins):
        super(Ba2FileRecordTexture, self).load_record(ins)
        self.dxgi_format = mk_dxgi_fmt(self.dxgi_format)
        self.tex_chunks = []
        for x in xrange(self.num_chunks):
            tex_chunk = Ba2TexChunk()
            tex_chunk.load_chunk(ins)
            self.tex_chunks.append(tex_chunk)

class Ba2TexChunk(object):
    """BA2 texture chunk, used in texture file records."""
    # unused1 is always BAADF00D
    __slots__ = (u'offset', u'packed_size', u'unpacked_size', u'start_mip',
                 u'end_mip', u'unused1')
    formats = [(f, struct.calcsize(f)) for f in (u'Q', u'I', u'I', u'H', u'H',
                                                 u'I')]

    def load_chunk(self, ins): ##: Centralize this, copy-pasted everywhere
        for fmt, attr in zip(Ba2TexChunk.formats, Ba2TexChunk.__slots__):
            self.__setattr__(attr, struct_unpack(fmt[0], ins.read(fmt[1]))[0])

    def __repr__(self):
        return u'Ba2TexChunk<mipmaps #%u to #%u>' % (
            self.start_mip, self.end_mip)

# Bsa content abstraction -----------------------------------------------------
class BSAFolder(object):
    """:type folder_assets: collections.OrderedDict[unicode, BSAFileRecord]"""

    def __init__(self, folder_record):
        self.folder_record = folder_record
        self.folder_assets = collections.OrderedDict() # keep files order

class Ba2Folder(object):

    def __init__(self):
        self.folder_assets = collections.OrderedDict() # keep files order

# Files -----------------------------------------------------------------------
def _makedirs_exists_ok(target_dir):
    try:
        os.makedirs(target_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

class ABsa(AFile):
    """:type bsa_folders: collections.OrderedDict[unicode, BSAFolder]"""
    header_type = BsaHeader
    _assets = frozenset()
    _compression_type = _Bsa_zlib # type: _BsaCompressionType

    def __init__(self, fullpath, load_cache=False, names_only=True):
        super(ABsa, self).__init__(fullpath)
        self.bsa_name = self.abs_path.stail
        self.bsa_header = self.__class__.header_type()
        self.bsa_folders = collections.OrderedDict() # keep folder order
        self._filenames = []
        self.total_names_length = 0 # reported wrongly at times - calculate it
        if load_cache: self.__load(names_only)

    def inspect_version(self):
        """Returns the version of this BSA."""
        with self.abs_path.open(u'rb') as ins:
            self.bsa_header.load_header(ins, self.bsa_name)
            return self.bsa_header.version

    def __load(self, names_only):
        try:
            if not names_only:
                self._load_bsa()
            else:
                self._load_bsa_light()
        except struct.error as e:
            raise BSAError(self.bsa_name, u'Error while unpacking: %r' % e)

    @staticmethod
    def _map_files_to_folders(asset_paths): # lowercase keys and values
        folder_file = []
        for a in asset_paths:
            split = a.rsplit(path_sep, 1)
            if len(split) == 1:
                split = [u'', split[0]]
            folder_file.append(split)
        # group files by folder
        folder_files_dict = {}
        folder_file.sort(key=itemgetter(0)) # sort first then group
        for key, val in groupby(folder_file, key=itemgetter(0)):
            folder_files_dict[key.lower()] = set(dest.lower() for _key, dest
                                                 in val)
        return folder_files_dict

    def extract_assets(self, asset_paths, dest_folder, progress=None):
        """Extracts certain assets from this BSA into the specified folder.

        :param asset_paths: An iterable specifying which files should be
            extracted.
        :param dest_folder: The folder into which the results should be
            extracted.
        :param progress: The progress callback to use. None if unwanted."""
        folder_files_dict = self._map_files_to_folders(
            imap(unicode.lower, asset_paths))
        del asset_paths # forget about this
        # load the bsa - this should be reworked to load only needed records
        self._load_bsa()
        folder_to_assets = self._map_assets_to_folders(folder_files_dict)
        # unload the bsa
        self.bsa_folders.clear()
        # get the data from the file
        global_compression = self.bsa_header.is_compressed()
        i = 0
        if progress:
            progress.setFull(len(folder_to_assets))
        with open(u'%s' % self.abs_path, u'rb') as bsa_file:
            for folder, file_records in folder_to_assets.iteritems():
                if progress:
                    progress(i, u'Extracting %s...\n%s' % (
                        self.bsa_name, folder))
                    i += 1
                # BSA paths always have backslashes, so we need to convert them
                # to the platform's path separators before we extract
                target_dir = os.path.join(dest_folder, *folder.split(u'\\'))
                _makedirs_exists_ok(target_dir)
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
                    with open(os.path.join(target_dir, filename),
                              u'wb') as out:
                        out.write(raw_data)

    def _map_assets_to_folders(self, folder_files_dict):
        folder_to_assets = collections.OrderedDict()
        for folder_path, bsa_folder in self.bsa_folders.iteritems():
            if folder_path.lower() not in folder_files_dict: continue
            # Has assets we need to extract. Keep order to avoid seeking
            # back and forth in the file
            folder_to_assets[folder_path] = file_records = []
            filenames = folder_files_dict[folder_path.lower()]
            for filename, filerecord in bsa_folder.folder_assets.iteritems():
                if filename.lower() not in filenames: continue
                file_records.append((filename, filerecord))
        return folder_to_assets

    # Abstract
    def _load_bsa(self): raise AbstractError()
    def _load_bsa_light(self): raise AbstractError()

    # API - delegates to abstract methods above
    def has_assets(self, asset_paths):
        return set(a.cs for a in asset_paths) & self.assets

    @property
    def assets(self):
        """Set of full paths in the bsa in lowercase.
        :rtype: frozenset[unicode]
        """
        if self._assets is self.__class__._assets:
            self.__load(names_only=True)
            self._assets = frozenset(imap(os.path.normcase, self._filenames))
            del self._filenames[:]
        return self._assets

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
        for folder_path, bsa_folder in self.bsa_folders.iteritems():
            for __ in xrange(bsa_folder.folder_record.files_count):
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
        for __ in xrange(folder_record.files_count):
            rec = cls.file_record_type()
            rec.load_record(bsa_file)
            file_records.append(rec)

    def _load_bsa_light(self):
        folder_records = [] # we need those to parse the folder names
        _filenames = []
        path_folder_record = collections.OrderedDict()
        read_file_record = partial(self._discard_file_records,
                                   folders=path_folder_record)
        file_names = self._read_bsa_file(folder_records, read_file_record)
        names_record_index = 0
        for folder_path, folder_record in path_folder_record.iteritems():
            for __ in xrange(folder_record.files_count):
                filename = _decode_path(
                    file_names[names_record_index], self.bsa_name)
                _filenames.append(path_sep.join((folder_path, filename)))
                names_record_index += 1
        self._filenames = _filenames

    def _read_bsa_file(self, folder_records, read_file_records):
        total_names_length = 0
        with open(u'%s' % self.abs_path, u'rb') as bsa_file: # accept string or Path
            # load the header from input stream
            self.bsa_header.load_header(bsa_file, self.bsa_name)
            # load the folder records from input stream
            for __ in xrange(self.bsa_header.folder_count):
                rec = self.__class__.folder_record_type()
                rec.load_record(bsa_file)
                folder_records.append(rec)
            # load the file record block
            for folder_record in folder_records:
                folder_path = u'?%d' % folder_record.record_hash # hack - untested
                name_size = unpack_byte(bsa_file)
                folder_path = _decode_path(
                    unpack_string(bsa_file, name_size - 1), self.bsa_name)
                total_names_length += name_size
                bsa_file.seek(1, 1) # discard null terminator
                read_file_records(bsa_file, folder_path, folder_record)
            if total_names_length != self.bsa_header.total_folder_name_length:
                deprint(u'%s reports wrong folder names length %d'
                    u' - actual: %d (number of folders is %d)' % (
                    self.abs_path, self.bsa_header.total_folder_name_length,
                    total_names_length, self.bsa_header.folder_count))
            self.total_names_length = total_names_length
            file_names = bsa_file.read( # has an empty string at the end
                self.bsa_header.total_file_name_length).split(b'\00')
            # close the file
        return file_names

    def _discard_file_records(self, bsa_file, folder_path, folder_record,
                              folders=None):
        bsa_file.seek(self.file_record_type.total_record_size() *
                      folder_record.files_count, 1)
        folders[folder_path] = folder_record

class BA2(ABsa):
    header_type = Ba2Header

    def extract_assets(self, asset_paths, dest_folder, progress=None):
        # map files to folders
        folder_files_dict = self._map_files_to_folders(asset_paths)
        del asset_paths # forget about this
        # load the bsa - this should be reworked to load only needed records
        self._load_bsa()
        my_header = self.bsa_header # type: Ba2Header
        is_dx10 = my_header.ba2_files_type == b'DX10'
        folder_to_assets = self._map_assets_to_folders(folder_files_dict)
        # unload the bsa
        self.bsa_folders.clear()
        # get the data from the file
        i = 0
        if progress:
            progress.setFull(len(folder_to_assets))
        with open(u'%s' % self.abs_path, u'rb') as bsa_file:
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
            for folder, file_records in folder_to_assets.iteritems():
                if progress:
                    progress(i, u'Extracting %s...\n%s' % (
                        self.bsa_name, folder))
                    i += 1
                # BSA paths always have backslashes, so we need to convert them
                # to the platform's path separators before we extract
                target_dir = os.path.join(dest_folder, *folder.split(u'\\'))
                _makedirs_exists_ok(target_dir)
                for filename, record in file_records:
                    if is_dx10:
                        # We're dealing with a DX10 BA2, need to combine all
                        # the texture chunks in the record first
                        dds_data = b''
                        for tex_chunk in record.tex_chunks:
                            dds_data += _read_rec_or_chunk(tex_chunk)
                        # Add a DDS header based on the data in the record,
                        # then dump the resulting DDS file - cf. BSArch
                        dds_file = DDSFile(u'')
                        _build_dds_header(dds_file, record)
                        dds_file.dds_contents = dds_data
                        raw_data = dds_file.dump_file()
                    else:
                        # Otherwise, we're dealing with a GNRL BA2, just
                        # read/decompress/write the record directly
                        raw_data = _read_rec_or_chunk(record)
                    with open(os.path.join(target_dir, filename),
                              u'wb') as out:
                        out.write(raw_data)

    def _load_bsa(self):
        with open(u'%s' % self.abs_path, u'rb') as bsa_file:
            # load the header from input stream
            my_header = self.bsa_header # type: Ba2Header
            my_header.load_header(bsa_file, self.bsa_name)
            # load the folder records from input stream
            if my_header.ba2_files_type == b'GNRL':
                file_record_type = Ba2FileRecordGeneral
            else:
                file_record_type = Ba2FileRecordTexture
            file_records = []
            for __ in xrange(my_header.ba2_num_files):
                rec = file_record_type()
                rec.load_record(bsa_file)
                file_records.append(rec)
            # load the file names block
            bsa_file.seek(my_header.ba2_name_table_offset)
            file_names_block = memoryview(bsa_file.read())
            # close the file
        current_folder_name = current_folder = None
        for index in xrange(my_header.ba2_num_files):
            name_size = struct.unpack_from(u'H', file_names_block)[0]
            filename = _decode_path(
                file_names_block[2:name_size + 2].tobytes(), self.bsa_name)
            file_names_block = file_names_block[name_size + 2:]
            folder_dex = filename.rfind(u'\\')
            if folder_dex == -1:
                folder_name = u''
            else:
                folder_name = filename[:folder_dex]
            if current_folder_name != folder_name:
                current_folder = self.bsa_folders.setdefault(folder_name,
                                                             Ba2Folder())
                current_folder_name = folder_name
            current_folder.folder_assets[filename[folder_dex + 1:]] = \
                file_records[index]

    def _load_bsa_light(self):
        my_header = self.bsa_header # type: Ba2Header
        with open(u'%s' % self.abs_path, u'rb') as bsa_file:
            # load the header from input stream
            my_header.load_header(bsa_file, self.bsa_name)
            # load the file names block
            bsa_file.seek(my_header.ba2_name_table_offset)
            file_names_block = memoryview(bsa_file.read())
            # close the file
        _filenames = []
        for index in xrange(my_header.ba2_num_files):
            name_size = struct.unpack_from(u'H', file_names_block)[0]
            filename = _decode_path(
                file_names_block[2:name_size + 2].tobytes(), self.bsa_name)
            _filenames.append(filename)
            file_names_block = file_names_block[name_size + 2:]
        self._filenames = _filenames

class MorrowindBsa(ABsa):
    header_type = MorrowindBsaHeader

    def _load_bsa_light(self):
        self.file_records = []
        with open(u'%s' % self.abs_path, u'rb') as bsa_file:
            # load the header from input stream
            self.bsa_header.load_header(bsa_file, self.bsa_name)
            # load each file record
            for x in xrange(self.bsa_header.file_count):
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
                file_record.load_name(bsa_file, self.bsa_name)
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
        i = 0
        if progress:
            progress.setFull(len(target_records))
        with open(u'%s' % self.abs_path, u'rb') as bsa_file:
            for file_record in target_records:
                rec_name = file_record.file_name
                if progress:
                    # No folder records, simulate them to avoid updating the
                    # progress bar too frequently
                    progress(i, u'Extracting %s...\n%s' % (
                        self.bsa_name, os.path.dirname(rec_name)))
                    i += 1
                # There is no compression for Morrowind BSAs, but all offsets
                # are relative to the final_offset we read earlier
                bsa_file.seek(self.final_offset + file_record.relative_offset)
                # Finally, simply read from the BSA file and write out the
                # result, making sure to create any needed directories
                raw_data = bsa_file.read(file_record.file_size)
                out_path = os.path.join(dest_folder, rec_name)
                _makedirs_exists_ok(os.path.dirname(out_path))
                with open(out_path, u'wb') as out:
                    out.write(raw_data)

class OblivionBsa(BSA):
    header_type = OblivionBsaHeader
    file_record_type = BSAOblivionFileRecord
    # A dictionary mapping file extensions to hash components. Used by Oblivion
    # when hashing file names for its BSAs.
    _bsa_ext_lookup = collections.defaultdict(int)
    for ext, hash_part in [(u'.kf', 0x80), (u'.nif', 0x8000),
                           (u'.dds', 0x8080), (u'.wav', 0x80000000)]:
        _bsa_ext_lookup[ext] = hash_part

    @staticmethod
    def calculate_hash(file_name):
        """Calculates the hash used by Oblivion BSAs for the provided file
        name.
        Based on Timeslips code with cleanup and pythonization.

        See here for more information:
        https://en.uesp.net/wiki/Tes4Mod:Hash_Calculation"""
        #--NOTE: fileName is NOT a Path object!
        root, ext = os.path.splitext(file_name.lower())
        chars = map(ord, root)
        hash_part_1 = chars[-1] | ((len(chars) > 2 and chars[-2]) or 0) << 8 \
                      | len(chars) << 16 | chars[0] << 24
        hash_part_1 |= OblivionBsa._bsa_ext_lookup[ext]
        uint_mask, hash_part_2, hash_part_3 = 0xFFFFFFFF, 0, 0
        for char in chars[1:-2]:
            hash_part_2 = ((hash_part_2 * 0x1003F) + char) & uint_mask
        for char in map(ord, ext):
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
        with open(self.abs_path.s, u'r+b') as bsa_file:
            reset_count = 0
            for folder_name, folder in self.bsa_folders.iteritems():
                for file_name, file_info in folder.folder_assets.iteritems():
                    rebuilt_hash = self.calculate_hash(file_name)
                    if file_info.record_hash != rebuilt_hash:
                        bsa_file.seek(file_info.file_pos)
                        bsa_file.write(struct_pack(_HashedRecord.formats[0][0],
                                                   rebuilt_hash))
                        reset_count += 1
                progress(progress.state + 1, u'Rebuilding Hashes...\n' +
                         folder_name)
        return reset_count

class SkyrimSeBsa(BSA):
    folder_record_type = BSASkyrimSEFolderRecord
    _compression_type = _Bsa_lz4

# Factory
def get_bsa_type(game_fsName):
    """:rtype: type"""
    if game_fsName == u'Morrowind':
        return MorrowindBsa
    elif game_fsName == u'Oblivion':
        return OblivionBsa
    elif game_fsName in (u'Enderal', u'Fallout3', u'FalloutNV', u'Skyrim'):
        return BSA
    elif game_fsName in (u'Skyrim Special Edition', u'Skyrim VR'):
        return SkyrimSeBsa
    elif game_fsName in (u'Fallout4', u'Fallout4VR'):
        # Hashes are I not Q in BA2s!
        _HashedRecord.formats = [(u'I', struct.calcsize(u'I'))]
        return BA2
