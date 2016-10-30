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

# Headers
class BSAHeader(object):
    __slots__ = ( # in the order encountered in the header
        'file_id', 'version', 'folder_records_offset', 'archive_flags',
        'folder_count', 'file_count', 'total_folder_name_length',
        'total_file_name_length', 'file_flags', )
    formats = ['4s'] + ['I'] * 9
    bsa_magic = 'BSA\x00'
    header_size = 36

    def load_header(self, ins):
        for fmt, attr in zip(self.__class__.formats, BSAHeader.__slots__):
            self.__setattr__(attr, struct.unpack(fmt, ins.read(
                struct.calcsize(fmt)))[0])
        # error checking
        if self.file_id != self.__class__.bsa_magic:
            raise BSAError(u'Magic wrong: %r' % self.file_id)
        if self.folder_records_offset != self.__class__.header_size:
            raise BSAError(u'Header size wrong: %r. Should be %r' % (
                self.folder_records_offset, self.__class__.header_size))
        if self.version != self.__class__.bsa_version:
            raise BSAVersionError(self.version, self.__class__.version)

    def has_names_for_folders(self): return self.archive_flags & 1
    def has_names_for_files(self): return self.archive_flags & 2
    def is_compressed(self): return self.archive_flags & 4
    def is_xbox(self): return self.archive_flags & 64

class OblivionBSAHeader(BSAHeader):
    __slots__ = ()
    bsa_version = int('0x67', 16)

class _HashedRecord(object):
    __slots__ = ('hash',)

    def load_record(self, ins):
        self.hash = struct.unpack('Q', ins.read(8))[0]
        for attr in self.__class__.__slots__:
            self.__setattr__(attr, struct.unpack('I', ins.read(4))[0])

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

class BSAFolderRecord(_HashedRecord):
    __slots__ = ('files_count', 'file_records_offset',)

class BSAFileRecord(_HashedRecord):
    __slots__ = ('file_data_size', 'raw_file_data_offset',)

    def load_record_from_buffer(self, memview, start):
        self.hash = struct.unpack_from('Q', memview, start)[0]
        start += 8
        for attr in self.__class__.__slots__:
            self.__setattr__(attr, struct.unpack_from('I', memview, start)[0])
            start += 4
        return start

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
    header_type = BSAHeader

    def __init__(self, abs_path):
        self.bsa_header = self.__class__.header_type()
        folder_records = []
        self.bsa_folders = collections.OrderedDict() # keep folder order
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
    header_type = OblivionBSAHeader
