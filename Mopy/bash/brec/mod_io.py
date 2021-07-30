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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Houses very low-level classes for reading and writing bytes in plugin
files."""
import os
from io import BytesIO

# no local imports beyond this, imported everywhere in brec
from .utils_constants import _int_unpacker, group_types, null1, strFid
from .. import bolt
from ..bolt import decoder, struct_pack, struct_unpack, structs_cache, \
    sig_to_str
from ..exception import ModError, ModReadError, ModSizeError

#------------------------------------------------------------------------------
# Headers ---------------------------------------------------------------------
##: Ideally this would sit in record_structs, but circular imports...
class RecordHeader(object):
    """Fixed size structure serving as header for the records or fencepost
    for groups of records."""
    rec_header_size = 24 # Record header size, e.g. 20 for Oblivion
    # Record pack format, e.g. 4sIIII for Oblivion
    # Given as a list here, where each string matches one subrecord in the
    # header. See rec_pack_format_str below as well.
    rec_pack_format = [u'=4s', u'I', u'I', u'I', u'I', u'I']
    # rec_pack_format as a format string. Use for pack_head / unpack calls.
    rec_pack_format_str = u''.join(rec_pack_format)
    # precompiled unpacker for record headers
    header_unpack = structs_cache[rec_pack_format_str].unpack
    # http://en.uesp.net/wiki/Tes5Mod:Mod_File_Format#Groups
    pack_formats = {0: u'=4sI4s3I'} # Top Type
    pack_formats.update({x: u'=4s5I' for x in {1, 6, 7, 8, 9, 10}}) # Children
    pack_formats.update({x: u'=4sIi3I' for x in {2, 3}})  #Interior Cell Blocks
    pack_formats.update({x: u'=4sIhh3I' for x in {4, 5}}) #Exterior Cell Blocks
    #--Top types in order of the main ESM
    top_grup_sigs = []
    #--Record Types: all recognized record types (not just the top types)
    valid_header_sigs = set()
    #--Plugin form version, we must pack this in the TES4 header
    plugin_form_version = 0
    is_top_group_header = False
    __slots__ = (u'recType', u'size', u'extra')

    ##: The way we represent form versions in memory needs rethinking
    @property
    def form_version(self):
        if self.plugin_form_version == 0 : return 0
        return struct_unpack(u'=2h', struct_pack(u'=I', self.extra))[0]

class RecHeader(RecordHeader):
    """Fixed size structure defining next record."""
    __slots__ = (u'flags1', u'fid', u'flags2')

    def __init__(self, recType=b'TES4', size=0, arg1=0, arg2=0, arg3=0, arg4=0):
        """Fixed size structure defining next record.

        :param recType: signature of record -TES4, GMST, KYWD, etc
        :param size: size of current record, not entire file
        :param arg1: the record flags
        :param arg2: Record FormID, TES4 records have FormID of 0
        :param arg3: Record possible version control in CK
        :param arg4: 2h, form_version, unknown"""
        self.recType = recType
        self.size = size
        self.flags1 = arg1
        self.fid = arg2
        self.flags2 = arg3
        self.extra = arg4

    def pack_head(self, __rh=RecordHeader):
        """Return the record header packed into a bitstream to be written to
        file."""
        pack_args = [__rh.rec_pack_format_str, self.recType, self.size,
                     self.flags1, self.fid, self.flags2]
        if __rh.plugin_form_version:
            extra1, extra2 = struct_unpack(u'=2h',
                                           struct_pack(u'=I', self.extra))
            extra1 = __rh.plugin_form_version
            self.extra = \
                struct_unpack(u'=I', struct_pack(u'=2h', extra1, extra2))[0]
            pack_args.append(self.extra)
        return struct_pack(*pack_args)

    def skip_blob(self, ins):
        # type: (ModReader) -> None
        """Skip the record - ins must be positioned at the beginning of the
        record data, ie call this immediately after unpacking self."""
        ins.seek(self.size, 1, self.recType) # aka self.blob_size()

    def blob_size(self):
        """The size of the blob this header is heading"""
        return self.size

    def __repr__(self):
        return f'<Record Header: [{sig_to_str(self.recType)}:' \
               f'{strFid(self.fid)}] v{self.form_version:d}>'

class GrupHeader(RecordHeader):
    """Fixed size structure serving as a fencepost in the plugin file,
    signaling a block of same type records ahead."""
    __slots__ = (u'label', u'groupType', u'stamp')

    def __init__(self, grup_size=0, grup_records_sig=b'', arg2=0, arg3=0,
                 arg4=0):
        """Fixed size structure serving as a fencepost in the plugin file,
        signaling a block of same type records ahead.

        :param grup_size: size of current GRUP in bytes, including the size of
                          this header
        :param grup_records_sig: type of records to follow, GMST, KYWD, etc
        :param arg2: Group Type 0 to 10 see UESP Wiki
        :param arg3: 2h, possible time stamp, unknown
        :param arg4: 0 for known mods (2h, form_version, unknown ?)"""
        self.recType = b'GRUP'
        self.size = grup_size
        self.label = grup_records_sig
        self.groupType = arg2
        self.stamp = arg3
        self.extra = arg4

    def pack_head(self, __rh=RecordHeader):
        """Return the record header packed into a bitstream to be written to
        file. We decide what kind of GRUP we have based on the type of
        label, hacky but to redo this we must revisit records code."""
        if isinstance(self.label, tuple):
            pack_args = [__rh.pack_formats[4], b'GRUP', self.size,
                         self.label[0], self.label[1], self.groupType,
                         self.stamp]
        else:
            pack_args = [__rh.pack_formats[1], b'GRUP', self.size,
                         self.label, self.groupType, self.stamp]
        if __rh.plugin_form_version:
            pack_args.append(self.extra)
        return struct_pack(*pack_args)

    def skip_blob(self, ins): # won't be called often, no need for inlines
        # type: (ModReader) -> None
        """Skip the group - ins must be positioned at the beginning of the
        block of group records, ie call this immediately after unpacking self.
        """
        # label is an int for MobDials groupType == 7
        ins.seek(self.blob_size(), 1, u'GRUP', self.label)

    def blob_size(self):
        """The size of the grup blob this header is heading."""
        return self.size - self.__class__.rec_header_size

    def __repr__(self):
        return f'<GRUP Header: {group_types[self.groupType]}, ' \
               f'{sig_to_str(self.label)}>'

class TopGrupHeader(GrupHeader):
    """Fixed size structure signaling a top level group of records."""
    __slots__ = ()
    is_top_group_header = True

    def __init__(self, grup_size=0, grup_records_sig=b'', arg3=0, arg4=0):
        super(TopGrupHeader, self).__init__(grup_size, grup_records_sig, 0,
                                            arg3, arg4)

    def pack_head(self, __rh=RecordHeader):
        pack_args = [__rh.pack_formats[0], b'GRUP', self.size,
                     self.label, self.groupType, self.stamp]
        if __rh.plugin_form_version:
            pack_args.append(self.extra)
        return struct_pack(*pack_args)

def unpack_header(ins, __rh=RecordHeader):
    """Header factory."""
    # args = header_sig, size, uint0, uint1, uint2[, uint3]
    header_sig, *args = ins.unpack(__rh.header_unpack, __rh.rec_header_size,
                                   u'REC_HEADER')
    #--Bad type?
    if header_sig not in __rh.valid_header_sigs:
        raise ModError(ins.inName, u'Bad header type: %r' % header_sig)
    #--Record
    if header_sig != b'GRUP':
        return RecHeader(header_sig, *args)
    #--Top Group
    elif args[2] == 0: #groupType == 0 (Top Type)
        str0 = struct_pack(u'I', args[1])
        if str0 in __rh.top_grup_sigs:
            args = list(args)
            args[1] = str0
            del args[2]
            return TopGrupHeader(*args)
        else:
            raise ModError(ins.inName, u'Bad Top GRUP type: %r' % str0)
    return GrupHeader(*args)

#------------------------------------------------------------------------------
# Low-level reading/writing ---------------------------------------------------
class ModReader(object):
    """Wrapper around a TES4 file in read mode.
    Will throw a ModReaderror if read operation fails to return correct size.
    """

    def __init__(self,inName,ins):
        self.inName = inName
        self.ins = ins
        #--Get ins size
        curPos = ins.tell()
        ins.seek(0,os.SEEK_END)
        self.size = ins.tell()
        ins.seek(curPos)
        self.strings = {}
        self.hasStrings = False

    # with statement
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_value, exc_traceback): self.ins.close()

    def setStringTable(self, string_table):
        self.hasStrings = bool(string_table)
        self.strings = string_table or {} # table may be None

    #--I/O Stream -----------------------------------------
    def seek(self, offset, whence=os.SEEK_SET, *debug_strs):
        """File seek."""
        if whence == os.SEEK_CUR:
            newPos = self.ins.tell() + offset
        elif whence == os.SEEK_END:
            newPos = self.size + offset
        else:
            newPos = offset
        if newPos < 0 or newPos > self.size:
            raise ModReadError(self.inName, debug_strs, newPos, self.size)
        self.ins.seek(offset, whence)

    def tell(self):
        """File tell."""
        return self.ins.tell()

    def close(self):
        """Close file."""
        self.ins.close()

    def atEnd(self, endPos=-1, *debug_strs):
        """Return True if current read position is at EOF."""
        filePos = self.ins.tell()
        if endPos == -1:
            return filePos == self.size
        elif filePos > endPos:
            raise ModReadError(self.inName, debug_strs, filePos, endPos)
        else:
            return filePos == endPos

    #--Read/Unpack ----------------------------------------
    def read(self, size, *debug_strs):
        """Read from file."""
        endPos = self.ins.tell() + size
        if endPos > self.size:
            target_size = size - (endPos - self.size)
            raise ModSizeError(self.inName, debug_strs, (target_size,), size)
        return self.ins.read(size)

    def readLString(self, size, *debug_strs):
        """Read translatable string. If the mod has STRINGS files, this is a
        uint32 to lookup the string in the string table. Otherwise, this is a
        zero-terminated string."""
        __unpacker = _int_unpacker
        if self.hasStrings:
            if size != 4:
                endPos = self.ins.tell() + size
                raise ModReadError(self.inName, debug_strs, endPos, self.size)
            id_, = self.unpack(__unpacker, 4, *debug_strs)
            if id_ == 0: return u''
            else: return self.strings.get(id_,u'LOOKUP FAILED!') #--Same as Skyrim
        else:
            return self.readString(size, *debug_strs)

    def readString32(self, *debug_str):
        """Read wide pascal string: uint32 is used to indicate length."""
        __unpacker = _int_unpacker
        strLen, = self.unpack(__unpacker, 4, debug_str)
        return self.readString(strLen, *debug_str)

    def readString(self, size, *debug_strs):
        """Read string from file, stripping zero terminator."""
        return u'\n'.join(decoder(x,bolt.pluginEncoding,avoidEncodings=(u'utf8',u'utf-8')) for x in
                          bolt.cstrip(self.read(size, *debug_strs)).split(b'\n'))

    def readStrings(self, size, *debug_strs):
        """Read strings from file, stripping zero terminator."""
        return [decoder(x,bolt.pluginEncoding,avoidEncodings=(u'utf8',u'utf-8')) for x in
                self.read(size, *debug_strs).rstrip(null1).split(null1)]

    def unpack(self, struct_unpacker, size, *debug_strs):
        """Read size bytes from the file and unpack according to format of
        struct_unpacker."""
        endPos = self.ins.tell() + size
        if endPos > self.size:
            raise ModReadError(self.inName, debug_strs, endPos, self.size)
        return struct_unpacker(self.ins.read(size))

    def unpackRef(self, __unpacker=_int_unpacker):
        """Read a ref (fid)."""
        return self.unpack(__unpacker, 4)[0]

    def unpackRecHeader(self, __head_unpack=unpack_header):
        return __head_unpack(self)

class FastModReader(BytesIO):
    """BytesIO-derived class that mimics ModReader, but runs at lightning
    speed."""
    def __init__(self, in_name, initial_bytes):
        super(FastModReader, self).__init__(initial_bytes)
        # Mirror ModReader.inName - name of the input file
        self.inName = in_name
        # Mirror ModReader.size - size of the input file
        self.size = len(initial_bytes)
        # Mirror ModReader.ins - the actual open file that we wrap
        self.ins = self

    def __enter__(self): return self

    def unpack(self, struct_unpacker, size, *debug_strs):
        """Mirror ModReader.unpack."""
        read_data = self.read(size)
        if len(read_data) != size:
            raise ModReadError(self.inName, debug_strs,
                               self.tell() - len(read_data), self.size)
        return struct_unpacker(read_data)
