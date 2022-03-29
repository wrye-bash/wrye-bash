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
from . import utils_constants
from .utils_constants import int_unpacker, group_types, null1, FormId, FID, \
    ZERO_FID
from .. import bolt, bush
from ..bolt import decoder, struct_pack, struct_unpack, structs_cache, \
    sig_to_str
from ..exception import ModError, ModReadError, ModSizeError, StateError

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
    pack_formats = {0: '=4sI4s3I'} # Top Group
    pack_formats.update({x: '=4s5I' for x in {1, 6, 7, 8, 9, 10}}) # Children
    pack_formats.update({x: '=4sIi3I' for x in {2, 3}})  # Interior Cell Blocks
    pack_formats.update({x: '=4sIhh3I' for x in {4, 5}}) # Exterior Cell Blocks
    #--Top types in order of the main ESM
    top_grup_sigs = []
    #--Record Types: all recognized record types (not just the top types)
    valid_header_sigs = set()
    #--Plugin form version, we must pack this in the TES4 header
    plugin_form_version = 0
    # A set of record types for which to skip upgrading to the latest Form
    # Version, usually because it's impossible
    skip_form_version_upgrade = set()
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

    def __init__(self, recType=b'TES4', size=0, arg1=0, arg2=0, arg3=0, arg4=0,
                 _entering_context=False):
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
        # FID call will blow as no FORM_ID global is defined when
        # _entering_context - setting FORM_ID to FormId would be more implicit
        self.fid = utils_constants.FID(arg2) if not _entering_context else arg2
        self.flags2 = arg3
        self.extra = arg4

    def pack_head(self, __rh=RecordHeader):
        """Return the record header packed into a bitstream to be written to
        file."""
        pack_args = [__rh.rec_pack_format_str, self.recType, self.size,
                     self.flags1, self.fid.dump(), self.flags2]
        if __rh.plugin_form_version:
            # Upgrade to latest form version unless we were told to skip that
            if self.recType not in __rh.skip_form_version_upgrade:
                extra1, extra2 = struct_unpack('=2h', struct_pack(
                    '=I', self.extra))
                extra1 = __rh.plugin_form_version
                self.extra = struct_unpack('=I', struct_pack(
                    '=2h', extra1, extra2))[0]
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
               f'{self.fid}] v{self.form_version:d}>'

class GrupHeader(RecordHeader):
    """Fixed size structure serving as a fencepost in the plugin file,
    signaling a block of same type records ahead."""
    __slots__ = (u'label', u'groupType', u'stamp')

    def __init__(self, grup_size=0, grup_label=b'', arg2=0, arg3=0, arg4=0):
        """Fixed size structure serving as a fencepost in the plugin file,
        signaling a block of same type records ahead.

        :param grup_size: size of current GRUP in bytes, including the size of
                          this header
        :param grup_label: sig of records to follow (GMST, KYWD, etc) or
                           FormId of parent (cell, dial, world) or grid coords
        :param arg2: Group Type 0 to 10 see UESP Wiki
        :param arg3: 2h, possible time stamp, unknown
        :param arg4: 0 for known mods (2h, form_version, unknown ?)"""
        self.recType = b'GRUP'
        self.size = grup_size
        self.label = grup_label
        self.groupType = arg2
        self.stamp = arg3
        self.extra = arg4

    def pack_head(self, __rh=RecordHeader):
        """Pack the record header to bytes to write to a file."""
        pack_args = self._pack_args(__rh)
        if __rh.plugin_form_version:
            pack_args.append(self.extra)
        return struct_pack(*pack_args)

    def _pack_args(self, __rh):
        return [__rh.pack_formats[1], b'GRUP', self.size, self.label,
                self.groupType, self.stamp]

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

    def __init__(self, grup_size=0, grup_label=b'', arg3=0, arg4=0):
        super().__init__(grup_size, grup_label, 0, arg3, arg4)

    def _pack_args(self, __rh):
        return [__rh.pack_formats[0], b'GRUP', self.size, self.label,
                self.groupType, self.stamp]

class ChildrenGrupHeader(GrupHeader):
    """Children of a CELL/WRLD/DIAL top record - label is fid of parent."""
    label: utils_constants.FormId
    __slots__ = ()

    def _pack_args(self, __rh):
        return [__rh.pack_formats[1], b'GRUP', self.size, self.label.dump(),
                self.groupType, self.stamp]

class ExteriorGrupHeader(GrupHeader):
    """Exterior Cell Sub/Block - label is Grid Y, X (Note the reverse order)"""
    label: (int, int)
    __slots__ = ()

    def _pack_args(self, __rh):
        return [__rh.pack_formats[4], b'GRUP', self.size, *self.label,
                self.groupType, self.stamp]

def unpack_header(ins, *, __rh=RecordHeader, _entering_context=False,
                  __children=frozenset({1, 6, 7, 8, 9, 10}),
                  __exterior=frozenset({4, 5}),
                  __packer=structs_cache['I'].pack,
                  __unpacker=structs_cache['2h'].unpack):
    """Header factory. For GRUP headers it will unpack the 'label' according
    to groupType."""
    # args = header_sig, size, uint0, uint1, uint2[, uint3]
    header_sig, *args = ins.unpack(__rh.header_unpack, __rh.rec_header_size,
                                   u'REC_HEADER')
    #--Bad type?
    if header_sig not in __rh.valid_header_sigs:
        raise ModError(ins.inName, f'Bad header type: '
                                   f'{sig_to_str(header_sig)}')
    #--Record
    if header_sig != b'GRUP':
        return RecHeader(header_sig, *args, _entering_context=_entering_context)
    #--Top Group
    grup_size, grup_label, grup_type, *rest = args
    if grup_type == 0: # groupType == 0 (Top Type)
        str0 = __packer(grup_label)
        if str0 in __rh.top_grup_sigs:
            return TopGrupHeader(grup_size, str0, *rest) # grup type omitted
        raise ModError(ins.inName, f'Bad Top GRUP type: {sig_to_str(str0)}')
    if grup_type in __children: # cell and dialog children, label is parent FID
        return ChildrenGrupHeader(grup_size, FID(grup_label), grup_type, *rest)
    if grup_type in __exterior: # exterior cell (sub)block
        yx_coords = __unpacker(__packer(grup_label)) # type: (int, int)
        return ExteriorGrupHeader(grup_size, yx_coords, grup_type, *rest)
    return GrupHeader(*args)

#------------------------------------------------------------------------------
# Low-level reading/writing ---------------------------------------------------
class ModReader(object):
    """Wrapper around a TES4 file in read mode.
    Will throw a ModReaderror if read operation fails to return correct size.
    """

    def __init__(self, inName, ins, ins_size=None):
        self.inName = inName
        self.ins = ins
        #--Get ins size
        if ins_size is None:
            curPos = ins.tell()
            ins.seek(0, os.SEEK_END)
            ins_size = ins.tell()
            ins.seek(curPos)
        self.size = ins_size
        self.strings = {}
        self.hasStrings = False
        self.debug_offset = 0

    # with statement
    def __enter__(self):
        self.form_id_type = utils_constants.FORM_ID
        if self.form_id_type is None: # else we are called in the context of another reader (DUH)
            utils_constants.FORM_ID = FormId # keep fids in short format
        return self
    def __exit__(self, exc_type, exc_value, exc_traceback):
        utils_constants.FORM_ID = self.form_id_type
        self.ins.close()

    @classmethod
    def from_info(cls, mod_info):
        """Boilerplate for creating a ModReader wrapping a mod_info."""
        return cls(mod_info.fn_key, mod_info.abs_path.open('rb'))

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

    def tell_debug(self):
        """ONLY USE WHEN DEBUGGING! Gives the true index into the underlying
        file. This is necessary because we wrap the original stream for
        decompressed data using ByteIOs."""
        return self.tell() + self.debug_offset

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
    def read(self, size, *debug_strs, file_offset=None):
        """Read from file."""
        endPos = (file_offset if file_offset is not None else self.ins.tell()
                  ) + size
        if endPos > self.size:
            target_size = size - (endPos - self.size)
            raise ModSizeError(self.inName, debug_strs, (target_size,), size)
        return self.ins.read(size)

    def readLString(self, size, *debug_strs, __unpacker=int_unpacker):
        """Read translatable string. If the mod has STRINGS files, this is a
        uint32 to lookup the string in the string table. Otherwise, this is a
        zero-terminated string."""
        if self.hasStrings:
            if size != 4:
                endPos = self.ins.tell() + size
                raise ModReadError(self.inName, debug_strs, endPos, self.size)
            id_, = self.unpack(__unpacker, 4, *debug_strs)
            if id_ == 0: return ''
            return self.strings.get(id_, 'LOOKUP FAILED!') #--Same as Skyrim
        else:
            return self.readString(size, *debug_strs)

    def readString32(self, *debug_str, __unpacker=int_unpacker):
        """Read wide pascal string: uint32 is used to indicate length."""
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

    def unpackRecHeader(self, __head_unpack=unpack_header):
        return __head_unpack(self)

    def __repr__(self):
        return f'{type(self).__name__}({self.inName})'

class FormIdReadContext(ModReader):
    """Set the global FormId structures for this plugin - needs to read the
    plugin header to read off the masters list - so it consumes the start of
    the file stream on __enter__."""

    # with statement
    def __enter__(self, __head_unpack=unpack_header):
        self.form_id_type = utils_constants.FORM_ID
        if self.form_id_type is not None:
            raise StateError(f'Already in a ModReader context')
        # Header of the plugin file "header" record
        tes4_rec_header = unpack_header(self, _entering_context=True)
        if (rs := tes4_rec_header.recType) != (# generally has 'TES4' signature
                hs := bush.game.Esp.plugin_header_sig):
            raise ModError(self.inName, f'Expected {sig_to_str(hs)}, but got '
                                        f'{sig_to_str(rs)}')
        self.plugin_header = bush.game.plugin_header_class(
            tes4_rec_header, self, do_unpack=True)
        # convert the fid of the TES4 record (and the fid of its header)
        self.plugin_header.fid = tes4_rec_header.fid = ZERO_FID
        return self

class FormIdWriteContext:
    """Now we must translate the fids based on the masters of the mod we
    write."""

    def __init__(self, out_path=None, augmented_masters=None,
                 plugin_header=None):
        self._plugin_header = plugin_header
        self._out_path = out_path
        self._augmented_masters = augmented_masters

    def _get_indices(self):
        """Retrieve the indices to use for short-mapping a FormID in this
        context."""
        return {mname: i for i, mname in enumerate(self._augmented_masters)}

    def _get_short_mapper(self):
        # Set utils_constants.short_mapper based on this mod's masters
        indices = self._get_indices()
        has_expanded_range = bush.game.Esp.expanded_plugin_range
        if (has_expanded_range and len(self._augmented_masters) > 1 and
                self._plugin_header.version >= 1.0):
            # Plugin has at least one master, it may freely use the
            # expanded (0x000-0x800) range
            def _short_mapper(formid):
                return (indices[formid.mod_id] << 24) | formid.object_dex
        else:
            # 0x000-0x800 are reserved for hardcoded (engine) records
            def _short_mapper(formid):
                return ((object_id := formid.object_dex) >= 0x800 and indices[
                    formid.mod_id] << 24) | object_id
        return _short_mapper

    def __enter__(self, __head_unpack=unpack_header):
        utils_constants.short_mapper = self._get_short_mapper()
        self.__out = self._out_path and self._out_path.open('wb')
        return self.__out

    def __exit__(self, exc_type, exc_value, exc_traceback):
        utils_constants.short_mapper = None
        if self._out_path: self.__out.close()

class RemapWriteContext(FormIdWriteContext):
    """A write context that can resolve FormIDs from both a new and an old
    master list. Used when remapping masters."""
    def __init__(self, pre_remap_masters: list[bolt.FName], augmented_masters,
            out_path=None, plugin_header=None):
        # Need the previous masters, but not the file itself
        if len(pre_remap_masters) != len(augmented_masters) - 1:
            raise ValueError('RemapWriteContext needs pre-remap masters that '
                             'match the length of the augmented masters - 1')
        super().__init__(out_path, augmented_masters, plugin_header)
        self._prev_masters = pre_remap_masters

    def _get_indices(self):
        # Allow FormIDs to resolve both the new and the old masters - remapped
        # masters will resolve to the same index this way because the order
        # doesn't change when remapping
        indices = super()._get_indices()
        return indices | {mname: i for i, mname
                          in enumerate(self._prev_masters)}

class ShortFidWriteContext(FormIdWriteContext):
    """Don't translate - used when fids are loaded in short format. Used also
    when we do not actually write out but have to use clunky APIs like
    getSize."""

    def _get_short_mapper(self): return lambda formid: formid.short_fid

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

    def __enter__(self):
        utils_constants.FORM_ID = FormId
        return super().__enter__()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        utils_constants.FORM_ID = None
        super().__exit__(exc_type, exc_value, exc_traceback)

    def unpack(self, struct_unpacker, size, *debug_strs):
        """Mirror ModReader.unpack."""
        read_data = self.read(size)
        if len(read_data) != size:
            raise ModReadError(self.inName, debug_strs,
                               self.tell() - len(read_data), self.size)
        return struct_unpacker(read_data)
