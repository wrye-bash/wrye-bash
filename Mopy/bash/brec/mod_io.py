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
"""Houses very low-level classes for reading and writing bytes in plugin
files."""

from __future__ import division, print_function
import os
import struct

# no local imports beyond this, imported everywhere in brec
from .utils_constants import _int_unpacker, null1, strFid
from .. import bolt, exception
from ..bolt import decode, encode, struct_pack, struct_unpack

#------------------------------------------------------------------------------
# Headers ---------------------------------------------------------------------
##: Ideally this would sit in mod_structs, but circular imports...
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
    header_unpack = struct.Struct(rec_pack_format_str).unpack
    # Format used by sub-record headers. Morrowind uses a different one.
    sub_header_fmt = u'=4sH'
    # precompiled unpacker for sub-record headers
    sub_header_unpack = struct.Struct(sub_header_fmt).unpack
    # Size of sub-record headers. Morrowind has a different one.
    sub_header_size = 6
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
    __slots__ = (u'recType', u'size', u'extra')

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

    def __repr__(self):
        return u'<Record Header: %s v%u>' % (
            strFid(self.fid), self.form_version)

class GrupHeader(RecordHeader):
    """Fixed size structure serving as a fencepost in the plugin file,
    signaling a block of same type records ahead."""
    __slots__ = (u'label', u'groupType', u'stamp')

    def __init__(self, recType=b'GRUP', size=0, arg1=0, arg2=0, arg3=0, arg4=0):
        """Fixed size structure serving as a fencepost in the plugin file,
        signaling a block of same type records ahead.

        :param recType: signature of record - for GRUP this is always GRUP
        :param size: size of current record, not entire file
        :param arg1: type of records to follow, GMST, KYWD, etc
        :param arg2: Group Type 0 to 10 see UESP Wiki
        :param arg3: 2h, possible time stamp, unknown
        :param arg4: 0 for known mods (2h, form_version, unknown ?)"""
        self.recType = recType
        self.size = size
        self.label = arg1
        self.groupType = arg2
        self.stamp = arg3
        self.extra = arg4

    def pack_head(self, __rh=RecordHeader):
        """Return the record header packed into a bitstream to be written to
        file. We decide what kind of GRUP we have based on the type of
        label, hacky but to redo this we must revisit records code."""
        if isinstance(self.label, str):
            pack_args = [__rh.pack_formats[0], self.recType, self.size,
                         self.label, self.groupType, self.stamp]
        elif isinstance(self.label, tuple):
            pack_args = [__rh.pack_formats[4], self.recType, self.size,
                         self.label[0], self.label[1], self.groupType,
                         self.stamp]
        else:
            pack_args = [__rh.pack_formats[1], self.recType, self.size,
                         self.label, self.groupType, self.stamp]
        if __rh.plugin_form_version:
            pack_args.append(self.extra)
        return struct_pack(*pack_args)

    def __repr__(self):
        return u'<GRUP Header: %s v%u>' % (self.label, self.form_version)

def unpack_header(ins, __rh=RecordHeader):
    """Header factory."""
    # args = header_sig, size, uint0, uint1, uint2[, uint3]
    args = ins.unpack(__rh.header_unpack, __rh.rec_header_size, 'REC_HEADER')
    #--Bad type?
    header_sig = args[0]
    if header_sig not in __rh.valid_header_sigs:
        raise exception.ModError(ins.inName,
                                 u'Bad header type: %r' % header_sig)
    #--Record
    if header_sig != b'GRUP':
        return RecHeader(*args)
    #--Top Group
    elif args[3] == 0: #groupType == 0 (Top Type)
        str0 = struct_pack('I', args[2])
        if str0 in __rh.top_grup_sigs:
            args = list(args)
            args[2] = str0
        else:
            raise exception.ModError(ins.inName,
                                     u'Bad Top GRUP type: %r' % str0)
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

    def setStringTable(self, table):
        self.hasStrings = bool(table)
        self.strings = table or {} # table may be None

    #--I/O Stream -----------------------------------------
    def seek(self,offset,whence=os.SEEK_SET,recType='----'):
        """File seek."""
        if whence == os.SEEK_CUR:
            newPos = self.ins.tell() + offset
        elif whence == os.SEEK_END:
            newPos = self.size + offset
        else:
            newPos = offset
        if newPos < 0 or newPos > self.size:
            raise exception.ModReadError(self.inName, recType, newPos, self.size)
        self.ins.seek(offset,whence)

    def tell(self):
        """File tell."""
        return self.ins.tell()

    def close(self):
        """Close file."""
        self.ins.close()

    def atEnd(self,endPos=-1,recType='----'):
        """Return True if current read position is at EOF."""
        filePos = self.ins.tell()
        if endPos == -1:
            return filePos == self.size
        elif filePos > endPos:
            raise exception.ModError(self.inName, u'Exceeded limit of: ' + recType)
        else:
            return filePos == endPos

    #--Read/Unpack ----------------------------------------
    def read(self,size,recType='----'):
        """Read from file."""
        endPos = self.ins.tell() + size
        if endPos > self.size:
            raise exception.ModSizeError(self.inName, recType, (endPos,),
                                         self.size)
        return self.ins.read(size)

    def readLString(self, size, recType='----', __unpacker=_int_unpacker):
        """Read translatable string. If the mod has STRINGS files, this is a
        uint32 to lookup the string in the string table. Otherwise, this is a
        zero-terminated string."""
        if self.hasStrings:
            if size != 4:
                endPos = self.ins.tell() + size
                raise exception.ModReadError(self.inName, recType, endPos, self.size)
            id_, = self.unpack(__unpacker, 4, recType)
            if id_ == 0: return u''
            else: return self.strings.get(id_,u'LOOKUP FAILED!') #--Same as Skyrim
        else:
            return self.readString(size,recType)

    def readString32(self, recType='----', __unpacker=_int_unpacker):
        """Read wide pascal string: uint32 is used to indicate length."""
        strLen, = self.unpack(__unpacker, 4, recType)
        return self.readString(strLen,recType)

    def readString(self,size,recType='----'):
        """Read string from file, stripping zero terminator."""
        return u'\n'.join(decode(x,bolt.pluginEncoding,avoidEncodings=('utf8','utf-8')) for x in
                          bolt.cstrip(self.read(size,recType)).split('\n'))

    def readStrings(self,size,recType='----'):
        """Read strings from file, stripping zero terminator."""
        return [decode(x,bolt.pluginEncoding,avoidEncodings=('utf8','utf-8')) for x in
                self.read(size,recType).rstrip(null1).split(null1)]

    def unpack(self, struct_unpacker, size, recType='----'):
        """Read size bytes from the file and unpack according to format of
        struct_unpacker."""
        endPos = self.ins.tell() + size
        if endPos > self.size:
            raise exception.ModReadError(self.inName, recType, endPos, self.size)
        return struct_unpacker(self.ins.read(size))

    def unpackRef(self, __unpacker=_int_unpacker):
        """Read a ref (fid)."""
        return self.unpack(__unpacker, 4)[0]

    def unpackRecHeader(self, __head_unpack=unpack_header):
        return __head_unpack(self)

    def unpackSubHeader(self, recType='----', expType=None, expSize=0,
                         __unpacker=_int_unpacker, __rh=RecordHeader):
        """Unpack a subrecord header. Optionally checks for match with expected
        type and size."""
        selfUnpack = self.unpack
        (rec_type, size) = selfUnpack(__rh.sub_header_unpack,
                                      __rh.sub_header_size,
                                      recType + '.SUB_HEAD')
        #--Extended storage?
        while rec_type == 'XXXX':
            size = selfUnpack(__unpacker, 4, recType + '.XXXX.SIZE.')[0]
            # Throw away size here (always == 0)
            rec_type = selfUnpack(__rh.sub_header_unpack,
                                  __rh.sub_header_size,
                                  recType + '.XXXX.TYPE')[0]
        #--Match expected name?
        if expType and expType != rec_type:
            raise exception.ModError(self.inName, u'%s: Expected %s subrecord, but '
                           u'found %s instead.' % (recType, expType, rec_type))
        #--Match expected size?
        if expSize and expSize != size:
            raise exception.ModSizeError(self.inName, recType + '.' + rec_type,
                                         (expSize,), size)
        return rec_type,size

#------------------------------------------------------------------------------
class ModWriter(object):
    """Wrapper around a TES4 output stream.  Adds utility functions."""
    def __init__(self,out):
        self.out = out

    # with statement
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_value, exc_traceback): self.out.close()

    #--Stream Wrapping ------------------------------------
    def write(self,data): self.out.write(data)
    def tell(self): return self.out.tell()
    def seek(self,offset,whence=os.SEEK_SET): return self.out.seek(offset,whence)
    def getvalue(self): return self.out.getvalue()
    def close(self): self.out.close()

    #--Additional functions -------------------------------
    def pack(self, *args):
        self.out.write(struct_pack(*args))

    def packSub(self, sub_rec_type, data, *values):
        """Write subrecord header and data to output stream.
        Call using either packSub(sub_rec_type,data) or
        packSub(sub_rec_type,format,values).
        Will automatically add a prefacing XXXX size subrecord to handle data
        with size > 0xFFFF."""
        try:
            if data is None: return
            if values: data = struct_pack(data, *values)
            outWrite = self.out.write
            lenData = len(data)
            if lenData <= 0xFFFF:
                outWrite(struct_pack(RecordHeader.sub_header_fmt, sub_rec_type,
                                     lenData))
            else:
                outWrite(struct_pack('=4sHI', 'XXXX', 4, lenData))
                outWrite(struct_pack(RecordHeader.sub_header_fmt, sub_rec_type,
                                     0))
            outWrite(data)
        except Exception:
            bolt.deprint(u'%r: Failed packing: %s, %s, %s' % (
                self, sub_rec_type, data, values))
            raise

    def packSub0(self, sub_rec_type, data, __rh=RecordHeader):
        """Write subrecord header plus zero terminated string to output
        stream."""
        if data is None: return
        elif isinstance(data,unicode):
            data = encode(data,firstEncoding=bolt.pluginEncoding)
        lenData = len(data) + 1
        outWrite = self.out.write
        if lenData < 0xFFFF:
            outWrite(struct_pack(__rh.sub_header_fmt, sub_rec_type, lenData))
        else:
            outWrite(struct_pack('=4sHI', 'XXXX', 4, lenData))
            outWrite(struct_pack(__rh.sub_header_fmt, sub_rec_type, 0))
        outWrite(data)
        outWrite('\x00')

    def packRef(self, sub_rec_type, fid):
        """Write subrecord header and fid reference."""
        if fid is not None:
            self.out.write(struct_pack('=4sHI', sub_rec_type, 4, fid))

    def writeGroup(self,size,label,groupType,stamp): # TODO the format strings
        # here are the Oblivion ones? use GrupHeader('GRUP',size,label,groupType,stamp).pack_head(self)?
        if type(label) is str:
            self.pack('=4sI4sII','GRUP',size,label,groupType,stamp)
        elif type(label) is tuple:
            self.pack('=4sIhhII','GRUP',size,label[1],label[0],groupType,stamp)
        else:
            self.pack('=4s4I','GRUP',size,label,groupType,stamp)

    def write_string(self, sub_type, string_val, max_size=0, min_size=0,
                     preferred_encoding=None):
        """Writes out a string subrecord, properly encoding it beforehand and
        respecting max_size, min_size and preferred_encoding if they are
        set."""
        self.packSub0(sub_type, bolt.encode_complex_string(
            string_val, max_size, min_size, preferred_encoding))
