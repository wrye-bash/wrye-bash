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

"""Bsa files.

For the file format see:
http://www.uesp.net/wiki/Tes4Mod:BSA_File_Format
http://www.uesp.net/wiki/Tes5Mod:Archive_File_Format
"""

__author__ = 'Utumno'

import collections
import os
import struct
import sys
from functools import partial
from ..bolt import deprint

_bsa_encoding = 'cp1252' # rumor has it that's the files/folders names encoding

# Exceptions ------------------------------------------------------------------
class BSAError(Exception): pass

class BSAVersionError(BSAError):

    def __init__(self, version, expected_version):
        super(BSAVersionError, self).__init__(
            u'Unexpected version %r - expected %r' % (
                version, expected_version))

class BSAFlagError(BSAError):

    def __init__(self, msg, flag):
        super(BSAFlagError, self).__init__(msg +  u' (flag %d) unset' % flag)

class BSADecodingError(BSAError):

    def __init__(self, string):
        super(BSADecodingError, self).__init__(
            u'Undecodable string %r' % string)

def _decode_path(string_path):
    try:
        return unicode(string_path, encoding=_bsa_encoding)
    except UnicodeDecodeError:
        raise BSADecodingError(string_path)

# Headers ---------------------------------------------------------------------
class _Header(object):
    __slots__ = ('file_id', 'version')
    formats = ['4s', 'I']
    bsa_magic = 'BSA\x00'
    bsa_version = int('0x67', 16)

    def load_header(self, ins):
        for fmt, attr in zip(_Header.formats, _Header.__slots__):
            self.__setattr__(attr, struct.unpack(fmt, ins.read(
                struct.calcsize(fmt)))[0])
        # error checking
        if self.file_id != self.__class__.bsa_magic:
            raise BSAError(u'Magic wrong: %r' % self.file_id)

class BsaHeader(_Header):
    __slots__ = ( # in the order encountered in the header
         'folder_records_offset', 'archive_flags', 'folder_count',
         'file_count', 'total_folder_name_length', 'total_file_name_length',
         'file_flags')
    formats = ['I'] * 8
    header_size = 36

    def load_header(self, ins):
        super(BsaHeader, self).load_header(ins)
        for fmt, attr in zip(BsaHeader.formats, BsaHeader.__slots__):
            self.__setattr__(attr, struct.unpack(fmt, ins.read(
                struct.calcsize(fmt)))[0])
        # error checking
        if self.folder_records_offset != self.__class__.header_size:
            raise BSAError(u'Header size wrong: %r. Should be %r' % (
                self.folder_records_offset, self.__class__.header_size))
        if not self.has_names_for_folders():
            raise BSAFlagError(u'Bsa has not names for folders', 1)
        if not self.has_names_for_files():
            raise BSAFlagError(u'Bsa has not filename block', 2)

    def has_names_for_folders(self): return self.archive_flags & 1
    def has_names_for_files(self): return self.archive_flags & 2
    def is_compressed(self): return self.archive_flags & 4
    def is_xbox(self): return self.archive_flags & 64

class Ba2Header(_Header):
    __slots__ = ( # in the order encountered in the header
        'b2a_files_type', 'b2a_num_files', 'b2a_name_table_offset')
    formats = ['4s', 'I', 'Q']
    bsa_magic = 'BTDX'
    file_types = {'GNRL', 'DX10'} # GNRL=General, DX10=Textures
    bsa_version = int('0x01', 16)
    header_size = 24

    def load_header(self, ins):
        super(Ba2Header, self).load_header(ins)
        for fmt, attr in zip(Ba2Header.formats, Ba2Header.__slots__):
            self.__setattr__(attr, struct.unpack(fmt, ins.read(
                struct.calcsize(fmt)))[0])
        # error checking
        if not self.b2a_files_type in self.file_types:
            raise BSAError(u'Unrecognised file types: %r. Should be %s' % (
                self.b2a_files_type, u' or'.join(self.file_types)))

class OblivionBsaHeader(BsaHeader):
    __slots__ = ()

class SkyrimBsaHeader(BsaHeader):
    __slots__ = ()
    bsa_version = int('0x68', 16)

    def embed_filenames(self): return self.archive_flags & 0x100

class SkyrimSeBsaHeader(BsaHeader):
    __slots__ = ()
    bsa_version = int('0x69', 16)

# Records ---------------------------------------------------------------------
class _HashedRecord(object):
    __slots__ = ('hash',)
    formats = [('Q', struct.calcsize('Q'))]

    def load_record(self, ins):
        fmt = _HashedRecord.formats[0]
        self.hash = struct.unpack(fmt[0], ins.read(fmt[1]))[0]

    def load_record_from_buffer(self, memview, start):
        fmt = _HashedRecord.formats[0]
        self.hash = struct.unpack_from(fmt[0], memview, start)[0]
        return start + fmt[1]

    @classmethod
    def total_record_size(cls):
        return _HashedRecord.formats[0][1]

    def __eq__(self, other):
        if isinstance(other, self.__class__): return self.hash == other.hash
        return NotImplemented
    def __ne__(self, other): return not (self == other)
    def __hash__(self): return self.hash
    def __lt__(self, other):
        if isinstance(other, self.__class__): return self.hash < other.hash
        return NotImplemented
    def __ge__(self, other): return not (self < other)
    def __gt__(self, other):
        if isinstance(other, self.__class__): return self.hash > other.hash
        return NotImplemented
    def __le__(self, other): return not (self > other)

    def __repr__(self): return repr(hex(self.hash))

# BSAs
class _BsaHashedRecord(_HashedRecord):
    __slots__ = ()

    def load_record(self, ins):
        super(_BsaHashedRecord, self).load_record(ins)
        for fmt, attr in zip(self.__class__.formats, self.__class__.__slots__):
            self.__setattr__(attr, struct.unpack(fmt[0], ins.read(fmt[1]))[0])

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
    __slots__ = ('files_count', 'file_records_offset')
    formats = ['I', 'I']
    formats = list((f, struct.calcsize(f)) for f in formats)

class BSASkyrimSEFolderRecord(_BsaHashedRecord):
    __slots__ = ('files_count', 'unknown_int', 'file_records_offset')
    formats = ['I', 'I', 'Q']
    formats = list((f, struct.calcsize(f)) for f in formats)

class BSAFileRecord(_BsaHashedRecord):
    __slots__ = ('file_data_size', 'raw_file_data_offset')
    formats = ['I', 'I']
    formats = list((f, struct.calcsize(f)) for f in formats)

# BA2s
class _B2aFileRecordCommon(_HashedRecord):
    __slots__ = ('file_extension', 'dir_hash', )
    formats = ['4s', 'I']
    formats = list((f, struct.calcsize(f)) for f in formats)

    def load_record(self, ins):
        super(_B2aFileRecordCommon, self).load_record(ins)
        for fmt, attr in zip(_B2aFileRecordCommon.formats,
                             _B2aFileRecordCommon.__slots__):
            self.__setattr__(attr, struct.unpack(fmt[0], ins.read(fmt[1]))[0])

    def load_record_from_buffer(self, memview, start):
        start = super(_B2aFileRecordCommon, self).load_record_from_buffer(
            memview, start)
        for fmt, attr in zip(_B2aFileRecordCommon.formats,
                             _B2aFileRecordCommon.__slots__):
            self.__setattr__(attr,
                             struct.unpack_from(fmt[0], memview, start)[0])
            start += fmt[1]
        return start

    @classmethod
    def total_record_size(cls): # unused !
        return super(_B2aFileRecordCommon, cls).total_record_size()  + sum(
            f[1] for f in _B2aFileRecordCommon.formats) + sum(
            f[1] for f in cls.formats)

class B2aFileRecordGeneral(_B2aFileRecordCommon):
    __slots__ = ('unk0C', 'offset', 'packed_size', 'unpacked_size', 'unk20')
    formats = ['I', 'Q'] + ['I'] * 3
    formats = list((f, struct.calcsize(f)) for f in formats)

    def load_record(self, ins):
        super(B2aFileRecordGeneral, self).load_record(ins)
        for fmt, attr in zip(B2aFileRecordGeneral.formats,
                             B2aFileRecordGeneral.__slots__):
            self.__setattr__(attr, struct.unpack(fmt[0], ins.read(fmt[1]))[0])

class B2aFileRecordTexture(_B2aFileRecordCommon):
    __slots__ = ('unk0C', 'num_of_chunks', 'chunk_header_size', 'height',
                 'width', 'num_mips', 'format', 'unk16')
    formats = ['B'] + ['B'] + ['H'] * 3 + ['B'] + ['B'] + ['H']#TODO(ut) verify
    formats = list((f, struct.calcsize(f)) for f in formats)

    def load_record(self, ins):
        super(B2aFileRecordTexture, self).load_record(ins)
        for fmt, attr in zip(B2aFileRecordGeneral.formats,
                             B2aFileRecordGeneral.__slots__):
            self.__setattr__(attr, struct.unpack(fmt[0], ins.read(fmt[1]))[0])

# Bsa content abstraction -----------------------------------------------------
class BSAFolder(object):

    def __init__(self, folder_record):
        self.folder_record = folder_record
        self.assets = collections.OrderedDict() # keep files order

class BSAAsset(object):

    def __init__(self, filename, filerecord):
        self.filerecord = filerecord
        self.filename = filename

    def __repr__(self): return repr(self.filename)
    def __unicode__(self): return unicode(self.filename)

class Ba2Folder(object):

    def __init__(self):
        self.assets = collections.OrderedDict() # keep files order

# Files -----------------------------------------------------------------------
class _BSA(object):
    header_type = BsaHeader

    def __init__(self, abs_path, names_only=True):
        self.bsa_header = self.__class__.header_type()
        self.bsa_folders = collections.OrderedDict() # keep folder order
        self._filenames = []
        self.total_names_length = 0 # reported wrongly at times - calculate it
        self.__load(abs_path, names_only)

    def __load(self, abs_path, names_only):
        try:
            if not names_only:
                self._load_bsa(abs_path)
            else:
                self.load_bsa_light(abs_path)
        except struct.error as e:
            raise BSAError, e.message, sys.exc_info()[2]

    # Abstract - _load_bsa is not used externally, may be removed
    def _load_bsa(self, abs_path): raise NotImplementedError
    def load_bsa_light(self, abs_path): raise NotImplementedError

class BSA(_BSA):
    """Bsa file. Notes:
    - We assume that has_names_for_files() is True, although we allow for
    has_names_for_folders() to be False (untested).
    - consider using the filenames from data block in load_light, if they
    are embedded."""
    file_record_type = BSAFileRecord
    folder_record_type = BSAFolderRecord

    def _load_bsa(self, abs_path):
        folder_records = [] # we need those to parse the folder names
        self.bsa_folders.clear()
        file_records = []
        read_file_record = partial(self._read_file_record, file_records,
                                   folders=self.bsa_folders)
        file_names = self._read_bsa_file(abs_path, folder_records,
                                         read_file_record)
        names_record_index = file_records_index = 0
        for folder_path, bsa_folder in self.bsa_folders.iteritems():
            for __ in xrange(bsa_folder.folder_record.files_count):
                rec = file_records[file_records_index]
                file_name = _decode_path(file_names[names_record_index])
                names_record_index += 1
                bsa_folder.assets[file_name] = BSAAsset(
                    os.path.sep.join((folder_path, file_name)), rec)

    @staticmethod
    def _read_file_record(file_records, bsa_file, folder_path,
                          folder_record, folders=None):
        folders[folder_path] = BSAFolder(folder_record)
        for __ in xrange(folder_record.files_count):
            rec = BSAFileRecord()
            rec.load_record(bsa_file)
            file_records.append(rec)

    def load_bsa_light(self, abs_path):
        folder_records = [] # we need those to parse the folder names
        _filenames = []
        path_folder_record = collections.OrderedDict()
        read_file_record = partial(self._discard_file_record,
                                   folders=path_folder_record)
        file_names = self._read_bsa_file(abs_path, folder_records,
                                         read_file_record)
        names_record_index = 0
        for folder_path, folder_record in path_folder_record.iteritems():
            for __ in xrange(folder_record.files_count):
                file_name = _decode_path(file_names[names_record_index])
                _filenames.append(os.path.sep.join((folder_path, file_name)))
                names_record_index += 1
        self._filenames = _filenames

    def _read_bsa_file(self, abs_path, folder_records, read_file_record):
        total_names_length = 0
        with open(u'%s' % abs_path, 'rb') as bsa_file: # accept string or Path
            # load the header from input stream
            self.bsa_header.load_header(bsa_file)
            # load the folder records from input stream
            for __ in xrange(self.bsa_header.folder_count):
                rec = self.__class__.folder_record_type()
                rec.load_record(bsa_file)
                folder_records.append(rec)
            # load the file record block
            for folder_record in folder_records:
                folder_path = u'?%d' % folder_record.hash # hack - untested
                if self.bsa_header.has_names_for_folders():
                    name_size = struct.unpack('B', bsa_file.read(1))[0]
                    folder_path = _decode_path(
                        struct.unpack('%ds' % (name_size - 1),
                                      bsa_file.read(name_size - 1))[0])
                    total_names_length += name_size
                    bsa_file.read(1) # discard null terminator
                read_file_record(bsa_file, folder_path, folder_record)
            if total_names_length != self.bsa_header.total_folder_name_length:
                deprint(u'%s reports wrong folder names length %d'
                        u' - actual: %d (number of folders is %d)' % (
                            abs_path, self.bsa_header.total_folder_name_length,
                            total_names_length, self.bsa_header.folder_count))
            self.total_names_length = total_names_length
            file_names = bsa_file.read( # has an empty string at the end
                self.bsa_header.total_file_name_length).split('\00')
            # close the file
        return file_names

    def _discard_file_record(self, bsa_file, folder_path, folder_record,
                             folders=None):
        bsa_file.read(folder_record.files_count *
            self.file_record_type.total_record_size())
        folders[folder_path] = folder_record

class BA2(_BSA):
    header_type = Ba2Header

    def _load_bsa(self, abs_path):
        with open(u'%s' % abs_path, 'rb') as bsa_file:
            # load the header from input stream
            self.bsa_header.load_header(bsa_file)
            # load the folder records from input stream
            if self.bsa_header.b2a_files_type == 'GNRL':
                file_record_type = B2aFileRecordGeneral
            else:
                file_record_type = B2aFileRecordTexture
            file_records = []
            for __ in xrange(self.bsa_header.b2a_num_files):
                rec = file_record_type()
                rec.load_record(bsa_file)
                file_records.append(rec)
            # load the file names block
            bsa_file.seek(self.bsa_header.b2a_name_table_offset)
            file_names_block = memoryview(bsa_file.read())
            # close the file
        current_folder_name = current_folder = None
        for index in xrange(self.bsa_header.b2a_num_files):
            name_size = struct.unpack_from('H', file_names_block)[0]
            file_name = _decode_path(
                file_names_block[2:name_size + 2].tobytes())
            file_names_block = file_names_block[name_size + 2:]
            folder_dex = file_name.rfind(u'\\')
            if folder_dex == -1:
                folder_name = u''
            else:
                folder_name = file_name[:folder_dex]
            if current_folder_name != folder_name:
                current_folder = self.bsa_folders.setdefault(folder_name,
                                                             Ba2Folder())
            current_folder.assets[file_name] = BSAAsset(file_name,
                                                        file_records[index])

    def load_bsa_light(self, abs_path):
        with open(u'%s' % abs_path, 'rb') as bsa_file:
            # load the header from input stream
            self.bsa_header.load_header(bsa_file)
            # load the file names block
            bsa_file.seek(self.bsa_header.b2a_name_table_offset)
            file_names_block = memoryview(bsa_file.read())
            # close the file
        _filenames = []
        for index in xrange(self.bsa_header.b2a_num_files):
            name_size = struct.unpack_from('H', file_names_block)[0]
            file_name = _decode_path(
                file_names_block[2:name_size + 2].tobytes())
            _filenames.append(file_name)
            file_names_block = file_names_block[name_size + 2:]
        self._filenames = _filenames

class OblivionBsa(BSA):
    header_type = OblivionBsaHeader

class SkyrimBsa(BSA):
    header_type = SkyrimBsaHeader

class SkyrimSeBsa(BSA):
    header_type = SkyrimSeBsaHeader
    folder_record_type = BSASkyrimSEFolderRecord

class Fallout4Ba2(BA2): pass
