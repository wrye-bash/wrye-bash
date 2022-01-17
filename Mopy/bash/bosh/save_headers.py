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

"""Save files - beta - TODOs:
- that's the headers code only - write save classes (per game)
- rework encoding/decoding
"""

__author__ = u'Utumno'

import copy
import io
import sys
import zlib
from collections import OrderedDict
from functools import partial

import lz4.block

from .. import bolt
from ..bolt import decoder, cstrip, unpack_string, unpack_int, unpack_str8, \
    unpack_short, unpack_float, unpack_str16, unpack_byte, \
    unpack_str_int_delim, unpack_str16_delim, unpack_str_byte_delim, \
    unpack_many, encode, struct_unpack, pack_int, pack_byte, pack_short, \
    pack_float, pack_string, pack_str8, pack_bzstr8, structs_cache, \
    struct_error, remove_newlines
from ..exception import SaveHeaderError, AbstractError

# Utilities -------------------------------------------------------------------
def _pack_c(out, value, __pack=structs_cache[u'=c'].pack):
    out.write(__pack(value))
unpack_fstr16 = partial(unpack_string, string_len=16)

class SaveFileHeader(object):
    save_magic = b'OVERRIDE'
    # common slots Bash code expects from SaveHeader (added header_size and
    # turned image to a property)
    __slots__ = (u'header_size', u'pcName', u'pcLevel', u'pcLocation',
                 u'gameDays', u'gameTicks', u'ssWidth', u'ssHeight', u'ssData',
                 u'masters', u'_save_info', u'_mastersStart')
    # map slots to (seek position, unpacker) - seek position negative means
    # seek relative to ins.tell(), otherwise to the beginning of the file
    unpackers = OrderedDict()

    def __init__(self, save_inf, load_image=False, ins=None):
        self._save_info = save_inf
        self.ssData = None # lazily loaded at runtime
        self.read_save_header(load_image, ins)

    def read_save_header(self, load_image=False, ins=None):
        """Fully reads this save header, optionally loading the image as
        well."""
        try:
            if ins is None:
                with self._save_info.abs_path.open(u'rb') as ins:
                    self.load_header(ins, load_image)
            else:
                self.load_header(ins, load_image)
        #--Errors
        except (OSError, struct_error, OverflowError) as e:
            err_msg = f'Failed to read {self._save_info.abs_path}'
            bolt.deprint(err_msg, traceback=True)
            raise SaveHeaderError(err_msg) from e

    def load_header(self, ins, load_image=False):
        save_magic = unpack_string(ins, len(self.__class__.save_magic))
        if save_magic != self.__class__.save_magic:
            raise SaveHeaderError(f'Magic wrong: {save_magic!r} (expected '
                                  f'{self.__class__.save_magic!r})')
        for attr, (__pack, _unpack) in self.__class__.unpackers.items():
            setattr(self, attr, _unpack(ins))
        self.load_image_data(ins, load_image)
        self.load_masters(ins)
        # additional calculations - TODO(ut): rework decoding
        self.calc_time()
        self.pcName = remove_newlines(decoder(cstrip(self.pcName)))
        self.pcLocation = remove_newlines(decoder(
            cstrip(self.pcLocation), bolt.pluginEncoding,
            avoidEncodings=(u'utf8', u'utf-8')))
        self.masters = [bolt.GPath_no_norm(decoder(
            x, bolt.pluginEncoding, avoidEncodings=(u'utf8', u'utf-8')))
            for x in self.masters]

    def dump_header(self, out):
        raise AbstractError

    def load_image_data(self, ins, load_image=False):
        bpp = (4 if self.has_alpha else 3)
        image_size = bpp * self.ssWidth * self.ssHeight
        if load_image:
            self.ssData = bytearray(ins.read(image_size))
        else:
            ins.seek(image_size, 1)

    def load_masters(self, ins):
        self._mastersStart = ins.tell()
        self.masters = []
        numMasters = unpack_byte(ins)
        for count in range(numMasters):
            self.masters.append(unpack_str8(ins))

    def calc_time(self): pass

    @property
    def has_alpha(self):
        """Whether or not this save file has alpha."""
        return False

    @property
    def image_loaded(self):
        """Whether or not this save header has had its image loaded yet."""
        return self.ssData is not None

    @property
    def image_parameters(self):
        return self.ssWidth, self.ssHeight, self.ssData, self.has_alpha

    def writeMasters(self, ins, out):
        """Rewrites masters of existing save file."""
        out.write(ins.read(self._mastersStart))
        oldMasters = self._write_masters(ins, out)
        #--Copy the rest
        for block in iter(partial(ins.read, 0x5000000), b''):
            out.write(block)
        return oldMasters

    def _write_masters(self, ins, out):
        ins.seek(4, 1) # Discard oldSize
        pack_int(out, self._master_block_size())
        #--Skip old masters
        numMasters = unpack_byte(ins)
        oldMasters = self._dump_masters(ins, numMasters, out)
        #--Offsets
        offset = out.tell() - ins.tell()
        #--File Location Table
        for i in range(6):
            # formIdArrayCount offset, unkownTable3Offset,
            # globalDataTable1Offset, globalDataTable2Offset,
            # changeFormsOffset, globalDataTable3Offset
            oldOffset = unpack_int(ins)
            pack_int(out, oldOffset + offset)
        return oldMasters

    def _dump_masters(self, ins, numMasters, out):
        oldMasters = []
        for x in range(numMasters):
            oldMasters.append(unpack_str16(ins))
        #--Write new masters
        pack_byte(out, len(self.masters))
        for master in self.masters:
            pack_short(out, len(master))
            out.write(encode(master.s))
        return oldMasters

    def _master_block_size(self):
        return 1 + sum(len(x) + 2 for x in self.masters)

    @property
    def can_edit_header(self):
        """Whether or not this header can be edited - if False, it will still
        be read and displayed, but the Save/Cancel buttons will be disabled."""
        return True

def _pack_str8_1(out, val): # TODO: val = val.reencode(...)
    val = encode(val)
    pack_bzstr8(out, val)
    return len(val) + 2
class OblivionSaveHeader(SaveFileHeader):
    save_magic = b'TES4SAVEGAME'
    __slots__ = (u'major_version', u'minor_version', u'exe_time',
                 u'header_version', u'saveNum', u'gameTime', u'ssSize')

    ##: exe_time and gameTime are SYSTEMTIME structs, as described here:
    # https://docs.microsoft.com/en-us/windows/win32/api/minwinbase/ns-minwinbase-systemtime
    unpackers = OrderedDict([
        (u'major_version',  (pack_byte, unpack_byte)),
        (u'minor_version',  (pack_byte, unpack_byte)),
        (u'exe_time',       (pack_string, unpack_fstr16)),
        (u'header_version', (pack_int, unpack_int)),
        (u'header_size',    (pack_int, unpack_int)),
        (u'saveNum',        (pack_int, unpack_int)),
        (u'pcName',         (_pack_str8_1, unpack_str8)),
        (u'pcLevel',        (pack_short, unpack_short)),
        (u'pcLocation',     (_pack_str8_1, unpack_str8)),
        (u'gameDays',       (pack_float, unpack_float)),
        (u'gameTicks',      (pack_int, unpack_int)),
        (u'gameTime',       (pack_string, unpack_fstr16)),
        (u'ssSize',         (pack_int, unpack_int)),
        (u'ssWidth',        (pack_int, unpack_int)),
        (u'ssHeight',       (pack_int, unpack_int)),
    ])

    def _write_masters(self, ins, out):
        #--Skip old masters
        numMasters = unpack_byte(ins)
        oldMasters = []
        for x in range(numMasters):
            oldMasters.append(unpack_str8(ins))
        #--Write new masters
        self.__write_masters_ob(out)
        #--Fids Address
        offset = out.tell() - ins.tell()
        fidsAddress = unpack_int(ins)
        pack_int(out, fidsAddress + offset)
        return oldMasters

    def __write_masters_ob(self, out):
        pack_byte(out, len(self.masters))
        for master in self.masters:
            pack_str8(out, encode(master.s))

    def dump_header(self, out):
        out.write(self.__class__.save_magic)
        var_fields_size = 0
        for attr, (_pack, __unpack) in self.unpackers.items():
            ret = _pack(out, getattr(self, attr))
            if ret is not None:
                var_fields_size += ret
        # Update the header size before writing it out. Note that all fields
        # before saveNum do not count towards this
        # TODO(inf) We need a nicer way to do this (query size before dump) -
        #  ut: we need the binary string size here, header size must be
        #  updated when var fields change (like pcName)
        self.header_size = var_fields_size + 42 + len(self.ssData)
        self._mastersStart = out.tell()
        out.seek(34)
        self.unpackers[u'header_size'][0](out, self.header_size)
        out.seek(self._mastersStart)
        out.write(self.ssData)
        self.__write_masters_ob(out)

class SkyrimSaveHeader(SaveFileHeader):
    """Valid Save Game Versions 8, 9, 12 (?)"""
    save_magic = b'TESV_SAVEGAME'
    # extra slots - only version is really used, gameDate used once (calc_time)
    # _formVersion distinguish between old and new save formats
    # _compressType of Skyrim SE saves - used to decide how to read/write them
    __slots__ = (u'gameDate', u'saveNumber', u'version', u'raceEid', u'pcSex',
                 u'pcExp', u'pcLvlExp', u'filetime', u'_formVersion',
                 u'_compressType', u'_sse_start', u'has_esl_masters')

    unpackers = OrderedDict([
        (u'header_size', (00, unpack_int)),
        (u'version',     (00, unpack_int)),
        (u'saveNumber',  (00, unpack_int)),
        (u'pcName',      (00, unpack_str16)),
        (u'pcLevel',     (00, unpack_int)),
        (u'pcLocation',  (00, unpack_str16)),
        (u'gameDate',    (00, unpack_str16)),
        (u'raceEid',     (00, unpack_str16)), # pcRace
        (u'pcSex',       (00, unpack_short)),
        (u'pcExp',       (00, unpack_float)),
        (u'pcLvlExp',    (00, unpack_float)),
        (u'filetime',    (00, lambda ins: unpack_string(ins, 8))),
        (u'ssWidth',     (00, unpack_int)),
        (u'ssHeight',    (00, unpack_int)),
    ])

    def __is_sse(self): return self.version == 12

    def _esl_block(self): return self.__is_sse() and self._formVersion >= 78

    @property
    def can_edit_header(self):
        ##: In order to re-enable this, we have to handle ESL and regular
        # masters separately when editing the masterlist
        return False

    @property
    def has_alpha(self):
        return self.__is_sse()

    def load_image_data(self, ins, load_image=False):
        if self.__is_sse():
            self._compressType = unpack_short(ins)
        if (actual := ins.tell() - 17) != self.header_size:
            raise SaveHeaderError(f'New Save game header size ({actual}) not '
                                  f'as expected ({self.header_size}).')
        super(SkyrimSaveHeader, self).load_image_data(ins, load_image)

    def load_masters(self, ins):
        # If on SSE, check _compressType and respond accordingly:
        #  0 means uncompressed
        #  1 means zlib
        #  2 means lz4
        if self.__is_sse() and self._compressType in (1, 2):
            self._sse_start = ins.tell()
            decompressed_size = unpack_int(ins)
            compressed_size = unpack_int(ins)
            sse_offset = ins.tell()
            ins = self._sse_decompress(ins, compressed_size, decompressed_size,
                light_decompression=True)
        else:
            sse_offset = 0
        self._formVersion = unpack_byte(ins)
        self._mastersStart = ins.tell() + sse_offset
        #--Masters
        self._load_masters_16(ins, sse_offset)

    def _load_masters_16(self, ins, sse_offset=0): # common for skyrim and FO4
        mastersSize = unpack_int(ins)
        self.masters = []
        numMasters = unpack_byte(ins)
        for count in range(numMasters):
            self.masters.append(unpack_str16(ins))
        # SSE / FO4 save format with esl block
        if self._esl_block():
            _num_esl_masters = unpack_short(ins)
            # Remember if we had ESL masters for the inacurracy warning
            self.has_esl_masters = _num_esl_masters > 0
            for count in range(_num_esl_masters):
                self.masters.append(unpack_str16(ins))
        else:
            self.has_esl_masters = False
        # Check for master's table size
        masters_size = ins.tell() + sse_offset - self._mastersStart - 4
        if masters_size != mastersSize:
            raise SaveHeaderError(f'Save game masters size ({masters_size}) '
                                  f'not as expected ({mastersSize}).')

    def _sse_compress(self, to_compress):
        """Compresses the specified data using either LZ4 or zlib, depending on
        self._compressType. Do not call for uncompressed files!"""
        try:
            if self._compressType == 2:
                # SSE uses default lz4 settings; store_size is not in docs, so:
                # noinspection PyArgumentList
                return lz4.block.compress(to_compress.getvalue(),
                                          store_size=False)
            else:
                # SSE uses zlib level 1
                return zlib.compress(to_compress.getvalue(), 1)
        except (zlib.error, lz4.block.LZ4BlockError) as e:
            raise SaveHeaderError(f'Failed to compress header: {e!r}')

    def _sse_decompress(self, ins, compressed_size, decompressed_size,
            light_decompression=False):
        """Decompresses the specified data using either LZ4 or zlib, depending
        on self._compressType. Do not call for uncompressed files!"""
        if self._compressType == 1:
            decompressor = self._sse_decompress_zlib
        else:
            if light_decompression:
                decompressor = self._sse_light_decompress_lz4
            else:
                decompressor = self._sse_decompress_lz4
        return decompressor(ins, compressed_size, decompressed_size)

    @staticmethod
    def _sse_decompress_zlib(ins, compressed_size, decompressed_size):
        try:
            decompressed_data = zlib.decompress(ins.read(compressed_size))
        except zlib.error as e:
            raise SaveHeaderError(f'zlib error while decompressing '
                                  f'zlib-compressed header: {e!r}')
        if len(decompressed_data) != decompressed_size:
            raise SaveHeaderError(
                f'zlib-decompressed header size incorrect - expected '
                f'{decompressed_size}, but got {len(decompressed_data)}.')
        return io.BytesIO(decompressed_data)

    @staticmethod
    def _sse_decompress_lz4(ins, compressed_size, decompressed_size):
        try:
            decompressed_data = lz4.block.decompress(
                ins.read(compressed_size), uncompressed_size=decompressed_size * 2)
        except lz4.block.LZ4BlockError as e:
            raise SaveHeaderError(f'LZ4 error while decompressing '
                                  f'lz4-compressed header: {e!r}')
        if (len_data := len(decompressed_data)) != decompressed_size:
            raise SaveHeaderError(f'lz4-decompressed header size incorrect - '
                f'expected {decompressed_size}, but got {len_data}.')
        return io.BytesIO(decompressed_data)

    @staticmethod
    def _sse_light_decompress_lz4(ins, _comp_size, _decomp_size):
        """Read the start of the LZ4 compressed data in the SSE savefile and
        stop when the whole master table is found.
        Return a file-like object that can be read by _load_masters_16
        containing the now decompressed master table.
        See https://fastcompression.blogspot.se/2011/05/lz4-explained.html
        for an LZ4 explanation/specification."""
        def _read_lsic_int():
            # type: () -> int
            """Read a compressed int from the stream.
            In short, add every byte to the output until a byte lower than
            255 is found, then add that as well and return the total sum.
            LSIC stands for linear small-integer code, taken from
            https://ticki.github.io/blog/how-lz4-works."""
            result = 0
            while True:  # there is no size limit to LSIC values
                num = unpack_byte(ins)
                result += num
                if num != 255:
                    return result
        uncompressed = b''
        masters_size = None  # type: int
        while True:  # parse and decompress each block here
            token = unpack_byte(ins)
            # How many bytes long is the literals-field?
            literal_length = token >> 4
            if literal_length == 15:  # add more if we hit max value
                literal_length += _read_lsic_int()
            # Read all the literals (which are good ol' uncompressed bytes)
            uncompressed += ins.read(literal_length)
            # The offset is how many bytes back in the uncompressed string the
            # start of the match-field (copied bytes) is
            offset = unpack_short(ins)
            # How many bytes long is the match-field?
            match_length = token & 0b1111
            if match_length == 15:
                match_length += _read_lsic_int()
            match_length += 4  # the match-field always gets an extra 4 bytes
            # The boundary of the match-field
            start_pos = len(uncompressed) - offset
            end_pos = start_pos + match_length
            # Matches can be overlapping (aka including not yet decompressed
            # data) so we can't jump the whole match_length directly
            while start_pos < end_pos:
                uncompressed += uncompressed[start_pos:min(start_pos + offset,
                                                           end_pos)]
                start_pos += offset
            # The masters table's size is found in bytes 1-5
            if masters_size is None and len(uncompressed) >= 5:
                masters_size = struct_unpack(u'I', uncompressed[1:5])[0]
            # Stop when we have the whole masters table
            if masters_size is not None:
                if len(uncompressed) >= masters_size + 5:
                    break
        # Wrap the decompressed data in a file-like object and return it
        return io.BytesIO(uncompressed)

    def calc_time(self):
        # gameDate format: hours.minutes.seconds
        hours, minutes, seconds = [int(x) for x in self.gameDate.split(b'.')]
        playSeconds = hours * 60 * 60 + minutes * 60 + seconds
        self.gameDays = float(playSeconds) / (24 * 60 * 60)
        self.gameTicks = playSeconds * 1000

    def writeMasters(self, ins, out):
        if not self.__is_sse() or self._compressType == 0:
            # Skyrim LE or uncompressed - can use the default implementation
            return super(SkyrimSaveHeader, self).writeMasters(ins, out)
        # Write out everything up until the compressed portion
        out.write(ins.read(self._sse_start))
        # Now we need to decompress the portion again
        decompressed_size = unpack_int(ins)
        compressed_size = unpack_int(ins)
        ins = self._sse_decompress(ins, compressed_size, decompressed_size)
        # Gather the data that will be compressed
        to_compress = io.BytesIO()
        pack_byte(to_compress, self._formVersion)
        ins.seek(1, 1) # skip the form version
        old_masters = self._write_masters(ins, to_compress)
        for block in iter(partial(ins.read, 0x5000000), b''):
            to_compress.write(block)
        # Compress the gathered data, write out the sizes and finally write out
        # the actual compressed data
        compressed_data = self._sse_compress(to_compress)
        pack_int(out, to_compress.tell())   # decompressed_size
        pack_int(out, len(compressed_data)) # compressed_size
        out.write(compressed_data)
        return old_masters

    def _dump_masters(self, ins, numMasters, out):
        # Store these two blocks distinctly, *never* combine them - that
        # destroys critical information since there is no way to tell ESL
        # status just from the name
        regular_masters = []
        esl_masters = []
        for x in range(numMasters):
            regular_masters.append(unpack_str16(ins))
        # SSE/FO4 format has separate ESL block
        has_esl_block = self._esl_block()
        if has_esl_block:
            _num_esl_masters = unpack_short(ins)
            for count in range(_num_esl_masters):
                esl_masters.append(unpack_str16(ins))
        # Write out the (potentially altered) masters - note that we have to
        # encode here, since we may be writing to BytesIO instead of a file
        num_regulars = len(regular_masters)
        pack_byte(out, num_regulars)
        for master in self.masters[:num_regulars]:
            pack_short(out, len(master))
            out.write(encode(master.s))
        if has_esl_block:
            pack_short(out, len(esl_masters))
            for master in self.masters[num_regulars:]:
                pack_short(out, len(master))
                out.write(encode(master.s))
        return regular_masters + esl_masters

    def _master_block_size(self):
        return (3 if self._esl_block() else 1) + sum(
            len(x) + 2 for x in self.masters)

class Fallout4SaveHeader(SkyrimSaveHeader): # pretty similar to skyrim
    """Valid Save Game Versions 11, 12, 13, 15 (?)"""
    save_magic = b'FO4_SAVEGAME'
    __slots__ = ()

    def _esl_block(self): return self.version == 15 and self._formVersion >= 68

    @property
    def has_alpha(self):
        return True

    def load_image_data(self, ins, load_image=False):
        if (actual := ins.tell() - 16) != self.header_size:
            raise SaveHeaderError(f'New Save game header size ({actual}) not '
                                  f'as expected ({self.header_size}).')
        super(SkyrimSaveHeader, self).load_image_data(ins, load_image)

    def load_masters(self, ins):
        self._formVersion = unpack_byte(ins)
        unpack_str16(ins) # drop "gameVersion"
        self._mastersStart = ins.tell()
        #--Masters
        self._load_masters_16(ins)

    def calc_time(self):
        # gameDate format: Xd.Xh.Xm.X days.X hours.X minutes
        # russian game format: '0д.0ч.9м.0 д.0 ч.9 мин'
        # So handle it by concatenating digits until we hit a non-digit char
        def parse_int(gd_bytes):
            int_data = b''
            ##: PY3.10: Use iterbytes (PEP 467)
            for i in gd_bytes:
                c = i.to_bytes(1, sys.byteorder)
                if c.isdigit():
                    int_data += c
                else:
                    break # hit the end of the int
            return int(int_data)
        days, hours, minutes = [parse_int(x) for x in
                                self.gameDate.split(b'.')[:3]]
        self.gameDays = float(days) + float(hours) / 24 + float(minutes) / (
            24 * 60)
        # Assuming still 1000 ticks per second
        self.gameTicks = (days * 24 * 60 * 60 + hours * 60 * 60 + minutes
                             * 60) * 1000

    def writeMasters(self, ins, out):
        # Call the SaveFileHeader version - *not* the Skyrim one
        return super(SkyrimSaveHeader, self).writeMasters(ins, out)

class FalloutNVSaveHeader(SaveFileHeader):
    save_magic = b'FO3SAVEGAME'
    __slots__ = (u'language', u'save_number', u'pcNick', u'version',
                 u'gameDate')
    _masters_unknown_byte = 0x1B
    unpackers = OrderedDict([
        (u'header_size', (00, unpack_int)),
        (u'version',     (00, unpack_str_int_delim)),
        (u'language',    (00, lambda ins: unpack_many(ins, u'64sc')[0])),
        (u'ssWidth',     (00, unpack_str_int_delim)),
        (u'ssHeight',    (00, unpack_str_int_delim)),
        (u'save_number', (00, unpack_str_int_delim)),
        (u'pcName',      (00, unpack_str16_delim)),
        (u'pcNick',      (00, unpack_str16_delim)),
        (u'pcLevel',     (00, unpack_str_int_delim)),
        (u'pcLocation',  (00, unpack_str16_delim)),
        (u'gameDate',    (00, unpack_str16_delim)),
    ])

    def load_masters(self, ins):
        self._mastersStart = ins.tell()
        self._master_list_size(ins)
        self.masters = []
        numMasters = unpack_str_byte_delim(ins)
        for count in range(numMasters):
            self.masters.append(unpack_str16_delim(ins))

    def _master_list_size(self, ins):
        formVersion, masterListSize = unpack_many(ins, '=BI')
        if formVersion != self._masters_unknown_byte: raise SaveHeaderError(
            f'Unknown byte at position {ins.tell() - 4} is {formVersion!r} '
            f'not 0x{self._masters_unknown_byte:X}')
        return masterListSize

    def _write_masters(self, ins, out):
        self._master_list_size(ins) # discard old size
        pack_byte(out, self._masters_unknown_byte)
        pack_int(out, self._master_block_size())
        #--Skip old masters
        numMasters = unpack_str_byte_delim(ins) # get me the Byte
        oldMasters = self._dump_masters(ins, numMasters, out)
        #--Offsets
        offset = out.tell() - ins.tell()
        #--File Location Table
        for i in range(5):
            # formIdArrayCount offset and 5 others
            oldOffset = unpack_int(ins)
            pack_int(out, oldOffset + offset)
        return oldMasters

    def _dump_masters(self, ins, numMasters, out):
        oldMasters = []
        for count in range(numMasters):
            oldMasters.append(unpack_str16_delim(ins))
        # Write new masters - note the silly delimiters
        pack_byte(out, len(self.masters))
        _pack_c(out, b'|')
        for master in self.masters:
            pack_short(out, len(master))
            _pack_c(out, b'|')
            out.write(encode(master.s))
            _pack_c(out, b'|')
        return oldMasters

    def _master_block_size(self):
        return 2 + sum(len(x) + 4 for x in self.masters)

    def calc_time(self):
        # gameDate format: hours.minutes.seconds
        hours, minutes, seconds = [int(x) for x in self.gameDate.split(b'.')]
        playSeconds = hours * 60 * 60 + minutes * 60 + seconds
        self.gameDays = float(playSeconds) / (24 * 60 * 60)
        self.gameTicks = playSeconds * 1000

class Fallout3SaveHeader(FalloutNVSaveHeader):
    save_magic = b'FO3SAVEGAME'
    __slots__ = ()
    _masters_unknown_byte = 0x15
    unpackers = copy.copy(FalloutNVSaveHeader.unpackers)
    del unpackers[u'language']

class MorrowindSaveHeader(SaveFileHeader):
    """Morrowind saves are identical in format to record definitions.
    Accordingly, we delegate loading the header to our existing mod API."""
    save_magic = b'TES3'
    __slots__ = (u'pc_curr_health', u'pc_max_health')

    def load_header(self, ins, load_image=False):
        # TODO(inf) A bit ugly, this is not a mod - maybe move readHeader out?
        from . import ModInfo
        save_info = ModInfo(self._save_info.abs_path, load_cache=True)
        ##: Figure out where some more of these are (e.g. level)
        self.header_size = save_info.header.size
        self.pcName = remove_newlines(save_info.header.pc_name)
        self.pcLevel = 0
        self.pcLocation = remove_newlines(save_info.header.curr_cell)
        self.gameDays = self.gameTicks = 0
        self.masters = save_info.masterNames[:]
        self.pc_curr_health = save_info.header.pc_curr_health
        self.pc_max_health = save_info.header.pc_max_health
        if load_image:
            # Read the image data - note that it comes as BGRA, which we
            # need to turn into RGB. Note that we disregard the alpha, seems to
            # make the image 100% black and is therefore unusable.
            out = io.BytesIO()
            for pxl in save_info.header.screenshot_data:
                out.write(
                    structs_cache[u'3B'].pack(pxl.red, pxl.green, pxl.blue))
            self.ssData = out.getvalue()
        self.ssHeight = self.ssWidth = 128 # fixed size for Morrowind

    @property
    def can_edit_header(self):
        # TODO(inf) Once we support writing Morrowind plugins, implement
        #  writeMasters properly and drop this override
        return False

# Factory
def get_save_header_type(game_fsName):
    """:rtype: type"""
    if game_fsName == u'Oblivion':
        return OblivionSaveHeader
    elif game_fsName in (u'Enderal', u'Skyrim',  u'Skyrim Special Edition',
                         u'Skyrim VR', u'Enderal Special Edition',
                         u'Skyrim Special Edition MS'):
        return SkyrimSaveHeader
    elif game_fsName in (u'Fallout4',  u'Fallout4VR', u'Fallout4 MS'):
        return Fallout4SaveHeader
    elif game_fsName == u'FalloutNV':
        return FalloutNVSaveHeader
    elif game_fsName == u'Fallout3':
        return Fallout3SaveHeader
    elif game_fsName == u'Morrowind':
        return MorrowindSaveHeader
