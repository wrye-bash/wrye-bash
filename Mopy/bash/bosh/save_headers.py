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

"""Save files - beta - TODOs:
- that's the headers code only - write save classes (per game)
- rework encoding/decoding
- use the alpha data from the image
"""

from __future__ import division

__author__ = u'Utumno'

import copy
import itertools
import lz4.block
import StringIO
import struct
import zlib
from collections import OrderedDict
from functools import partial
from .. import bolt
from ..bolt import decode, cstrip, unpack_string, unpack_int, unpack_str8, \
    unpack_short, unpack_float, unpack_str16, unpack_byte, struct_pack, \
    unpack_str_int_delim, unpack_str16_delim_null, unpack_str_byte_delim, \
    unpack_many, encode
from ..exception import SaveHeaderError, raise_bolt_error

# Utilities -------------------------------------------------------------------
def _pack(out, fmt, pack_arg): out.write(struct_pack(fmt, pack_arg))

class SaveFileHeader(object):
    save_magic = 'OVERRIDE'
    # common slots Bash code expects from SaveHeader (added header_size and
    # turned image to a property)
    __slots__ = (u'header_size', u'pcName', u'pcLevel', u'pcLocation',
                 u'gameDays', u'gameTicks', u'ssWidth', u'ssHeight', u'ssData',
                 u'masters', u'_save_path', u'_mastersStart')
    # map slots to (seek position, unpacker) - seek position negative means
    # seek relative to ins.tell(), otherwise to the beginning of the file
    unpackers = OrderedDict()

    def __init__(self, save_path):
        self._save_path = save_path
        try:
            with save_path.open('rb') as ins:
                self.load_header(ins)
        #--Errors
        except (OSError, struct.error, OverflowError):
            bolt.deprint(u'Failed to read %s' % save_path, traceback=True)
            raise_bolt_error(u'Failed to read %s' % save_path, SaveHeaderError)

    def load_header(self, ins):
        save_magic = unpack_string(ins, len(self.__class__.save_magic))
        if save_magic != self.__class__.save_magic:
            raise SaveHeaderError(u'Magic wrong: %r (expected %r)' % (
                save_magic, self.__class__.save_magic))
        for attr, unp in self.__class__.unpackers.iteritems():
            if unp[0]:
                if unp[0] > 0: ins.seek(unp[0])
                else: ins.seek(ins.tell() - unp[0])
            self.__setattr__(attr, unp[1](ins))
        self.load_image_data(ins)
        self.load_masters(ins)
        # additional calculations - TODO(ut): rework decoding
        self.calc_time()
        self.pcName = decode(cstrip(self.pcName))
        self.pcLocation = decode(cstrip(self.pcLocation), bolt.pluginEncoding,
                                 avoidEncodings=('utf8', 'utf-8'))
        self.masters = [bolt.GPath(decode(x)) for x in self.masters]

    def load_image_data(self, ins):
        self.ssData = ins.read(3 * self.ssWidth * self.ssHeight)

    def _drop_alpha(self, ins): ## TODO: Setup Bash to use the alpha data
        # Game is in 32bit RGB, Bash is expecting 24bit RGB
        ssData = ins.read(4 * self.ssWidth * self.ssHeight)
        # pick out only every 3 bytes, drop the 4th (alpha channel)
        #ssAlpha = ''.join(itertools.islice(ssData, 0, None, 4))
        self.ssData = ''.join(
            itertools.compress(ssData, itertools.cycle(reversed(range(4)))))

    def load_masters(self, ins):
        self._mastersStart = ins.tell()
        self.masters = []
        numMasters = unpack_byte(ins)
        for count in xrange(numMasters):
            self.masters.append(unpack_str8(ins))

    def calc_time(self): pass

    @property
    def image(self):
        return self.ssWidth, self.ssHeight, self.ssData

    def writeMasters(self, ins, out):
        """Rewrites masters of existing save file."""
        out.write(ins.read(self._mastersStart))
        oldMasters = self._write_masters(ins, out)
        #--Copy the rest
        for block in iter(partial(ins.read, 0x5000000), ''):
            out.write(block)
        return oldMasters

    def _write_masters(self, ins, out):
        ins.seek(4, 1) # Discard oldSize
        _pack(out, '=I', self._master_block_size())
        #--Skip old masters
        numMasters = unpack_byte(ins)
        oldMasters = self._dump_masters(ins, numMasters, out)
        #--Offsets
        offset = out.tell() - ins.tell()
        #--File Location Table
        for i in xrange(6):
            # formIdArrayCount offset, unkownTable3Offset,
            # globalDataTable1Offset, globalDataTable2Offset,
            # changeFormsOffset, globalDataTable3Offset
            oldOffset = unpack_int(ins)
            _pack(out, '=I', oldOffset + offset)
        return oldMasters

    def _dump_masters(self, ins, numMasters, out):
        oldMasters = []
        for x in xrange(numMasters):
            oldMasters.append(unpack_str16(ins))
        #--Write new masters
        _pack(out, '=B', len(self.masters))
        for master in self.masters:
            _pack(out, '=H', len(master))
            out.write(master.s)
        return oldMasters

    def _master_block_size(self):
        return 1 + sum(len(x) + 2 for x in self.masters)

    @property
    def can_edit_header(self):
        """Whether or not this header can be edited - if False, it will still
        be read and displayed, but the Save/Cancel buttons will be disabled."""
        return True

class OblivionSaveHeader(SaveFileHeader):
    save_magic = 'TES4SAVEGAME'
    __slots__ = ('gameTime', 'ssSize')
    unpackers = OrderedDict([
        ('header_size', (34, unpack_int)),
        ('pcName',      (42, unpack_str8)),
        ('pcLevel',     (00, unpack_short)),
        ('pcLocation',  (00, unpack_str8)),
        ('gameDays',    (00, unpack_float)),
        ('gameTicks',   (00, unpack_int)),
        ('gameTime',    (00, lambda ins: unpack_string(ins, 16))),
        ('ssSize',      (00, unpack_int)),
        ('ssWidth',     (00, unpack_int)),
        ('ssHeight',    (00, unpack_int)),
    ])

    def _write_masters(self, ins, out):
        #--Skip old masters
        numMasters = unpack_byte(ins)
        oldMasters = []
        for x in xrange(numMasters):
            oldMasters.append(unpack_str8(ins))
        #--Write new masters
        _pack(out, '=B', len(self.masters))
        for master in self.masters:
            _pack(out, '=B', len(master))
            out.write(master.s)
        #--Fids Address
        offset = out.tell() - ins.tell()
        fidsAddress = unpack_int(ins)
        _pack(out, '=I', fidsAddress + offset)
        return oldMasters

class SkyrimSaveHeader(SaveFileHeader):
    """Valid Save Game Versions 8, 9, 12 (?)"""
    save_magic = 'TESV_SAVEGAME'
    # extra slots - only version is really used, gameDate used once (calc_time)
    # _formVersion distinguish between old and new save formats
    # _compressType of Skyrim SE saves - used to decide how to read/write them
    __slots__ = ('gameDate', 'saveNumber', 'version', 'raceEid', 'pcSex',
                 'pcExp', 'pcLvlExp', 'filetime', '_formVersion',
                 '_compressType', '_sse_start')

    unpackers = OrderedDict([
        ('header_size', (00, unpack_int)),
        ('version',     (00, unpack_int)),
        ('saveNumber',  (00, unpack_int)),
        ('pcName',      (00, unpack_str16)),
        ('pcLevel',     (00, unpack_int)),
        ('pcLocation',  (00, unpack_str16)),
        ('gameDate',    (00, unpack_str16)),
        ('raceEid',     (00, unpack_str16)), # pcRace
        ('pcSex',       (00, unpack_short)),
        ('pcExp',       (00, unpack_float)),
        ('pcLvlExp',    (00, unpack_float)),
        ('filetime',    (00, lambda ins: unpack_string(ins, 8))),
        ('ssWidth',     (00, unpack_int)),
        ('ssHeight',    (00, unpack_int)),
    ])

    def __is_sse(self): return self.version == 12

    def _esl_block(self): return self.__is_sse() and self._formVersion >= 78

    def load_image_data(self, ins):
        if self.__is_sse():
            self._compressType = unpack_short(ins)
        if ins.tell() != self.header_size + 17: raise SaveHeaderError(
            u'New Save game header size (%s) not as expected (%s).' % (
                ins.tell() - 17, self.header_size))
        #--Image Data
        if self.__is_sse():
            self._drop_alpha(ins)
        else:
            super(SkyrimSaveHeader, self).load_image_data(ins)

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
            ins = self._sse_decompress(ins, compressed_size, decompressed_size)
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
        for count in xrange(numMasters):
            self.masters.append(unpack_str16(ins))
        # SSE / FO4 save format with esl block
        if self._esl_block():
            _num_esl_masters = unpack_short(ins)
            for count in xrange(_num_esl_masters):
                self.masters.append(unpack_str16(ins))
        # Check for master's table size
        if ins.tell() + sse_offset != self._mastersStart + mastersSize + 4:
            raise SaveHeaderError(
                u'Save game masters size (%i) not as expected (%i).' % (
                    ins.tell() + sse_offset - self._mastersStart - 4,
                    mastersSize))

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
            raise SaveHeaderError(u'Failed to compress header: %r' % e)

    def _sse_decompress(self, ins, compressed_size, decompressed_size):
        """Decompresses the specified data using either LZ4 or zlib, depending
        on self._compressType. Do not call for uncompressed files!"""
        decompressor = (self._sse_decompress_lz4
                       if self._compressType == 2
                       else self._sse_decompress_zlib)
        return decompressor(ins, compressed_size, decompressed_size)

    @staticmethod
    def _sse_decompress_zlib(ins, compressed_size, decompressed_size):
        try:
            decompressed_data = zlib.decompress(ins.read(compressed_size))
        except zlib.error as e:
            raise SaveHeaderError(u'zlib error while decompressing '
                                  u'zlib-compressed header: %r' % e)
        if len(decompressed_data) != decompressed_size:
            raise SaveHeaderError(u'zlib-decompressed header size incorrect - '
                                  u'expected %u, but got %u.' % (
                decompressed_size, len(decompressed_data)))
        return StringIO.StringIO(decompressed_data)

    @staticmethod
    def _sse_decompress_lz4(ins, compressed_size, decompressed_size):
        try:
            decompressed_data = lz4.block.decompress(
                ins.read(compressed_size), uncompressed_size=decompressed_size * 2)
        except lz4.block.LZ4BlockError as e:
            raise SaveHeaderError(u'LZ4 error while decompressing '
                                  u'lz4-compressed header: %r' % e)
        if len(decompressed_data) != decompressed_size:
            raise SaveHeaderError(u'lz4-decompressed header size incorrect - '
                                  u'expected %u, but got %u.' % (
                decompressed_size, len(decompressed_data)))
        return StringIO.StringIO(decompressed_data)

    def calc_time(self):
        # gameDate format: hours.minutes.seconds
        hours, minutes, seconds = [int(x) for x in self.gameDate.split('.')]
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
        to_compress = StringIO.StringIO()
        to_compress.write(struct_pack(u'=B', self._formVersion))
        ins.seek(1, 1) # skip the form version
        old_masters = self._write_masters(ins, to_compress)
        for block in iter(partial(ins.read, 0x5000000), b''):
            to_compress.write(block)
        # Compress the gathered data, write out the sizes and finally write out
        # the actual compressed data
        compressed_data = self._sse_compress(to_compress)
        _pack(out, u'=I', to_compress.tell())   # decompressed_size
        _pack(out, u'=I', len(compressed_data)) # compressed_size
        out.write(compressed_data)
        return old_masters

    def _dump_masters(self, ins, numMasters, out):
        # Store these two blocks distinctly, *never* combine them - that
        # destroys critical information since there is no way to tell ESL
        # status just from the name
        regular_masters = []
        esl_masters = []
        for x in xrange(numMasters):
            regular_masters.append(unpack_str16(ins))
        # SSE/FO4 format has separate ESL block
        has_esl_block = self._esl_block()
        if has_esl_block:
            _num_esl_masters = unpack_short(ins)
            for count in xrange(_num_esl_masters):
                esl_masters.append(unpack_str16(ins))
        # Write out the (potentially altered) masters - note that we have to
        # encode here, since we may be writing to StringIO instead of a file
        num_regulars = len(regular_masters)
        _pack(out, '=B', num_regulars)
        for master in self.masters[:num_regulars]:
            _pack(out, '=H', len(master))
            out.write(encode(master.s))
        if has_esl_block:
            _pack(out, '=H', len(esl_masters))
            for master in self.masters[num_regulars:]:
                _pack(out, '=H', len(master))
                out.write(encode(master.s))
        return regular_masters + esl_masters

    def _master_block_size(self):
        return (3 if self._esl_block() else 1) + sum(
            len(x) + 2 for x in self.masters)

class Fallout4SaveHeader(SkyrimSaveHeader): # pretty similar to skyrim
    """Valid Save Game Versions 11, 12, 13, 15 (?)"""
    save_magic = 'FO4_SAVEGAME'

    __slots__ = ()

    def _esl_block(self): return self.version == 15 and self._formVersion >= 68

    def load_image_data(self, ins):
        if ins.tell() != self.header_size + 16: raise SaveHeaderError(
            u'New Save game header size (%s) not as expected (%s).' % (
                ins.tell() - 16, self.header_size))
        #--Image Data
        self._drop_alpha(ins)

    def load_masters(self, ins):
        self._formVersion = unpack_byte(ins)
        unpack_str16(ins) # drop "gameVersion"
        self._mastersStart = ins.tell()
        #--Masters
        self._load_masters_16(ins)

    def calc_time(self):
        # gameDate format: Xd.Xh.Xm.X days.X hours.X minutes
        # russian game format: '0д.0ч.9м.0 д.0 ч.9 мин'
        self.gameDate = unicode(self.gameDate, encoding='utf-8')
        days, hours, minutes, _days, _hours, _minutes = self.gameDate.split(
            '.')
        days = int(days[:-1])
        hours = int(hours[:-1])
        minutes = int(minutes[:-1])
        self.gameDays = float(days) + float(hours) / 24 + float(minutes) / (
            24 * 60)
        # Assuming still 1000 ticks per second
        self.gameTicks = (days * 24 * 60 * 60 + hours * 60 * 60 + minutes
                             * 60) * 1000

    def writeMasters(self, ins, out):
        # Call the SaveFileHeader version - *not* the Skyrim one
        super(SkyrimSaveHeader, self).writeMasters(ins, out)

class FalloutNVSaveHeader(SaveFileHeader):
    save_magic = 'FO3SAVEGAME'
    __slots__ = ('language', 'ssDepth', 'pcNick', '_unknown', 'gameDate')
    _masters_unknown_byte = 0x1B
    unpackers = OrderedDict([
        ('header_size', (00, unpack_int)),
        ('_unknown',    (00, unpack_str_int_delim)),
        ('language',    (00, lambda ins: unpack_many(ins, '64sc')[0])),
        ('ssWidth',     (00, unpack_str_int_delim)),
        ('ssHeight',    (00, unpack_str_int_delim)),
        ('ssDepth',     (00, unpack_str_int_delim)),
        ('pcName',      (00, unpack_str16_delim_null)),
        ('pcNick',      (00, unpack_str16_delim_null)),
        ('pcLevel',     (00, unpack_str_int_delim)),
        ('pcLocation',  (00, unpack_str16_delim_null)),
        ('gameDate',    (00, unpack_str16_delim_null)),
    ])

    def load_masters(self, ins):
        self._mastersStart = ins.tell()
        self._master_list_size(ins)
        self.masters = []
        numMasters = unpack_str_byte_delim(ins)
        for count in xrange(numMasters):
            self.masters.append(unpack_str16_delim_null(ins))

    def _master_list_size(self, ins):
        formVersion, masterListSize = unpack_many(ins, '=BI')
        if formVersion != self._masters_unknown_byte: raise SaveHeaderError(
            u'Unknown byte at position %d is %r not 0x%X' % (
                ins.tell() - 4, formVersion, self._masters_unknown_byte))
        return masterListSize

    def _write_masters(self, ins, out):
        self._master_list_size(ins) # discard old size
        _pack(out, '=B', self._masters_unknown_byte)
        _pack(out, '=I', self._master_block_size())
        #--Skip old masters
        numMasters = unpack_str_byte_delim(ins) # get me the Byte
        oldMasters = self._dump_masters(ins, numMasters, out)
        #--Offsets
        offset = out.tell() - ins.tell()
        #--File Location Table
        for i in xrange(5):
            # formIdArrayCount offset and 5 others
            oldOffset = unpack_int(ins)
            _pack(out, '=I', oldOffset + offset)
        return oldMasters

    def _dump_masters(self, ins, numMasters, out):
        oldMasters = []
        for count in xrange(numMasters):
            oldMasters.append(unpack_str16_delim_null(ins))
        # Write new masters - note the silly delimiters
        _pack(out, '=B', len(self.masters))
        _pack(out, '=c', '|')
        for master in self.masters:
            _pack(out, '=H', len(master))
            _pack(out, '=c', '|')
            out.write(master.s)
            _pack(out, '=c', '|')
        return oldMasters

    def _master_block_size(self):
        return 2 + sum(len(x) + 4 for x in self.masters)

    def calc_time(self):
        # gameDate format: hours.minutes.seconds
        hours, minutes, seconds = [int(x) for x in self.gameDate.split('.')]
        playSeconds = hours * 60 * 60 + minutes * 60 + seconds
        self.gameDays = float(playSeconds) / (24 * 60 * 60)
        self.gameTicks = playSeconds * 1000

class Fallout3SaveHeader(FalloutNVSaveHeader):
    save_magic = 'FO3SAVEGAME'
    __slots__ = ()
    _masters_unknown_byte = 0x15
    unpackers = copy.copy(FalloutNVSaveHeader.unpackers)
    del unpackers['language']

class MorrowindSaveHeader(SaveFileHeader):
    """Morrowind saves are identical in format to record definitions.
    Accordingly, we delegate loading the header to our existing mod API."""
    save_magic = 'TES3'
    __slots__ = ('pc_curr_health', 'pc_max_health')

    def load_header(self, ins):
        # TODO(inf) A bit ugly, this is not a mod - maybe move readHeader out?
        from . import ModInfo
        save_info = ModInfo(self._save_path, load_cache=True)
        ##: Figure out where some more of these are (e.g. level)
        self.header_size = save_info.header.size
        self.pcName = decode(cstrip(save_info.header.pc_name))
        self.pcLevel = 0
        self.pcLocation = decode(cstrip(save_info.header.curr_cell),
                                 bolt.pluginEncoding,
                                 avoidEncodings=(u'utf8', u'utf-8'))
        self.gameDays = self.gameTicks = 0
        self.masters = save_info.masterNames[:]
        self.pc_curr_health = save_info.header.pc_curr_health
        self.pc_max_health = save_info.header.pc_max_health
        # Read the image data - note that it comes as BGRA, which we
        # need to turn into RGB - ##: in the future: RGBA
        out = StringIO.StringIO()
        for pxl in save_info.header.screenshot_data:
            out.write(struct_pack(u'3B', pxl.red, pxl.green, pxl.blue))
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
    elif game_fsName in (u'Enderal', u'Skyrim',  u'Skyrim Special Edition'):
        return SkyrimSaveHeader
    elif game_fsName in (u'Fallout4',  u'Fallout4VR'):
        return Fallout4SaveHeader
    elif game_fsName == u'FalloutNV':
        return FalloutNVSaveHeader
    elif game_fsName == u'Fallout3':
        return Fallout3SaveHeader
    elif game_fsName == u'Morrowind':
        return MorrowindSaveHeader
