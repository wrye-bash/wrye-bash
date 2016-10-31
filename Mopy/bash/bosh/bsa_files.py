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

# Headers ---------------------------------------------------------------------
class _Header(object):
    __slots__ = ('file_id', 'version', )
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
         'file_flags',)
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
        'b2a_files_type', 'b2a_num_files', 'b2a_name_table_offset', )
    formats = ['4s'] + ['I'] + ['Q']
    bsa_magic = 'BTDX'
    file_types = {'GNRL', 'DX10'} # GNRL=General, DX10=Textures
    bsa_version = int('0x01', 16)

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
    formats = ['Q']

    def load_record(self, ins):
        fmt = _HashedRecord.formats[0]
        self.hash = struct.unpack(fmt, ins.read(struct.calcsize(fmt)))[0]

    def load_record_from_buffer(self, memview, start):
        fmt = _HashedRecord.formats[0]
        self.hash = struct.unpack_from(fmt, memview, start)[0]
        return start + struct.calcsize(fmt)

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

# BSAs
class _BsaHashedRecord(_HashedRecord):
    __slots__ = ()

    def load_record(self, ins):
        super(_BsaHashedRecord, self).load_record(ins)
        for fmt, attr in zip(self.__class__.formats, self.__class__.__slots__):
            self.__setattr__(attr, struct.unpack(fmt, ins.read(
                struct.calcsize(fmt)))[0])

    def load_record_from_buffer(self, memview, start):
        start = super(_BsaHashedRecord, self).load_record_from_buffer(memview,
                                                                      start)
        for fmt, attr in zip(self.__class__.formats, self.__class__.__slots__):
            self.__setattr__(attr, struct.unpack_from(fmt, memview, start)[0])
            start += struct.calcsize(fmt)
        return start

class BSAFolderRecord(_BsaHashedRecord):
    __slots__ = ('files_count', 'file_records_offset',)
    formats = ['I'] + ['I']

class BSAFileRecord(_BsaHashedRecord):
    __slots__ = ('file_data_size', 'raw_file_data_offset',)
    formats = ['I'] + ['I']


    def load_record_from_buffer(self, memview, start):
        self.hash = struct.unpack_from('Q', memview, start)[0]
        start += 8
        for attr in self.__class__.__slots__:
            self.__setattr__(attr, struct.unpack_from('I', memview, start)[0])
            start += 4
        return start

# Bsa content abstraction -----------------------------------------------------
class BSAFolder(object):

    def __init__(self, folder_record):
        self.folder_record = folder_record
        self.assets = collections.OrderedDict() # keep files order

    def __repr__(self):
        return repr(tuple(repr(a) for a in self.assets.itervalues()))

class BSAAsset(object):

    def __init__(self, filename, filerecord):
        self.filerecord = filerecord
        self.filename = filename

    def __repr__(self): return repr(self.filename)
    def __unicode__(self): return unicode(self.filename)

class BSA(object):
    header_type = BsaHeader

    def __init__(self, abs_path):
        self.bsa_header = self.__class__.header_type()
        folder_records = []
        self.bsa_folders = collections.OrderedDict() # keep folder order
        self._load_bsa(abs_path, folder_records)

    def _load_bsa(self, abs_path, folder_records):
        with open(abs_path, 'rb') as bsa_file:
            # load the header from input stream
            self.bsa_header.load_header(bsa_file)
            # load the folder records from input stream
            for __ in xrange(self.bsa_header.folder_count):
                rec = BSAFolderRecord()
                rec.load_record(bsa_file)
                folder_records.append(rec)
            # load the file record block to parse later
            has_folder_names = self.bsa_header.has_names_for_folders()
            file_records_block_size = 16 * self.bsa_header.file_count
            if has_folder_names:
                file_records_block_size += ( # one byte for each folder name's size
                    self.bsa_header.folder_count
                    + self.bsa_header.total_folder_name_length)
            file_records_block = memoryview(
                bsa_file.read(file_records_block_size))
            # load the file names block
            file_names = None
            if self.bsa_header.has_names_for_files():
                file_names = bsa_file.read(
                    self.bsa_header.total_file_name_length).split('\00')
            # close the file
        names_record_index = 0
        for folder_record in folder_records:
            folder_path = u'?%d' % folder_record.hash # hack - untested
            if has_folder_names:
                name_size = struct.unpack_from('B', file_records_block)[0]
                ## TODO: decode
                # discard null terminator below
                folder_path = unicode(
                    file_records_block[1:name_size].tobytes(),
                    encoding=_bsa_encoding)
                file_records_block = file_records_block[name_size + 1:]
            current_folder = self.bsa_folders.setdefault(
                folder_path, BSAFolder(folder_record)) # type: BSAFolder
            file_records_index = 0
            for __ in xrange(folder_record.files_count):
                rec = BSAFileRecord()
                file_records_index = rec.load_record_from_buffer(
                    file_records_block, file_records_index)
                file_name = u'?%d' % rec.hash
                if file_names is not None:
                    file_name = unicode(file_names[names_record_index],
                                        encoding=_bsa_encoding)
                    names_record_index += 1
                current_folder.assets[file_name] = BSAAsset(
                    os.path.sep.join((folder_path, file_name)), rec)
            file_records_block = file_records_block[file_records_index:]

class OblivionBsa(BSA):
    header_type = OblivionBsaHeader

class SkyrimBsa(BSA):
    header_type = SkyrimBsaHeader

class SkyrimSeBsa(BSA):
    header_type = SkyrimSeBsaHeader
