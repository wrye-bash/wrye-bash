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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2026 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
import io
import struct
import zlib
from types import SimpleNamespace

import pytest

from ... import plugin_types
from ...bosh.save_headers import StarfieldSaveHeader
from ...exception import SaveHeaderError
from ...game import _SFPluginFlag

# Helpers ---------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _sf_scale_flags(monkeypatch):
    """The plugin table has a block per scale flag - ESL, then MID for
    Starfield. Those are only set up when a game's install is."""
    monkeypatch.setattr(plugin_types, 'scale_flags', {
        _SFPluginFlag.ESL: 253, _SFPluginFlag.MID: 252})

def _str16(bstr: bytes):
    return struct.pack('<H', len(bstr)) + bstr

# creation name, creation id and flags of a plugin
_creation = (b'Creation Name', b'TM_0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0',
             b'\1\0')
_no_creation = (b'', b'', b'')

def _sf_plugin(name: bytes, form_version, creation_data):
    """A plugin entry of a Starfield save's plugin table - creation_data is
    None for the plugins that carry no creation metadata."""
    entry = _str16(name)
    if form_version >= 140:
        entry += b'\0' if creation_data is None else b'\1'
    if creation_data is not None:
        # creation name, id, flags and achievement friendly
        entry += b''.join(map(_str16, creation_data)) + b'\1'
    return entry

def _sf_save(form_version, regular, light=(), medium=(), tail=b''):
    """Decompressed contents of a Starfield save: its header, its plugin
    table - (name, creation_data) pairs - and tail for the rest of it."""
    header = (struct.pack('<IBI', 186, 12, 7) + _str16(b'Barrett')
        + struct.pack('<I', 42) + _str16(b'New Atlantis')
        + _str16(b'3d.4h.5m.3 days.4 hours.5 minutes')
        + _str16(b'HumanRace') + struct.pack('<HffQI', 0, 1.0, 2.0, 0, 0)
        + b'\0' * 8)
    def _block(count_fmt, plugins):
        return struct.pack(count_fmt, len(plugins)) + b''.join(
            _sf_plugin(n, form_version, c) for n, c in plugins)
    table = (_block('<B', regular) + _block('<H', light)
             + _block('<I', medium))
    return (b'SFS_SAVEGAME' + struct.pack('<I', len(header)) + header
        + bytes([form_version]) + _str16(b'1.12.30.0') + _str16(b'1.7.23.0')
        # the plugin table size includes the two bytes after it
        + struct.pack('<H', len(table) + 2) + b'\0\0' + table + tail)

def _bcps(payload: bytes, chunk_size=0, align=16):
    """Wrap payload in a BCPS container, as the game does: it is split into
    chunk_size chunks, each compressed separately and padded to a multiple of
    align - see SFS.bt in Nexus-Mods/StarfieldSaveTool."""
    chunk_size = chunk_size or len(payload)
    chunks = [zlib.compress(payload[i:i + chunk_size])
              for i in range(0, len(payload), chunk_size)]
    chunk_sizes = struct.pack(f'<{len(chunks)}I', *map(len, chunks))
    return (struct.pack('<4sIQQQQQQQI4s', b'BCPS', 1, 72, 0,
        72 + len(chunk_sizes), len(payload), 0, chunk_size, align, 0,
        b'ZIP ') + chunk_sizes + b''.join(
        c + b'\xff' * (-len(c) % align) for c in chunks))

def _read_header(container: bytes):
    return StarfieldSaveHeader(SimpleNamespace(abs_path='Save1.sfs'),
                               ins=io.BytesIO(container))

def _check_masters(form_version, regular, light, medium, **bcps_kwargs):
    sf_save = _sf_save(form_version, regular, light, medium)
    header = _read_header(_bcps(sf_save, **bcps_kwargs))
    assert header.masters_regular == [n.decode() for n, _c in regular]
    assert header.scale_masters == {
        _SFPluginFlag.ESL: [n.decode() for n, _c in light],
        _SFPluginFlag.MID: [n.decode() for n, _c in medium]}
    return header

# Starfield plugin table ------------------------------------------------------
@pytest.mark.parametrize('form_version', [122, 139])
def test_sf_v122_creation_metadata(form_version):
    """Before 140 there was no flag for the creation metadata: the plugins
    the game had hardcoded as core lack it, whatever their case - but not
    ones we pin since, like ShatteredSpace.esm (#730)."""
    regular = [(b'Starfield.esm', None), (b'Constellation.esm', None),
        (b'OLDMARS.ESM', None), (b'BlueprintShips-Starfield.esm', None),
        (b'SFBGS003.esm', None), (b'sfbgs006.esm', None),
        (b'SFBGS007.esm', None), (b'SFBGS008.esm', None),
        (b'ShatteredSpace.esm', _creation), (b'SFBGS004.esm', _creation),
        (b'Unofficial Starfield Patch.esm', _no_creation)]
    light = [(b'Light.esm', _creation)]
    medium = [(b'Medium.esm', _no_creation)]
    _check_masters(form_version, regular, light, medium)

def test_sf_v140_creation_flag():
    """From 140 on, a flag before the creation metadata says if it's
    there - the names don't matter."""
    regular = [(b'Starfield.esm', None), (b'SFBGS003.esm', _creation),
               (b'ShatteredSpace.esm', None), (b'Mod.esm', _no_creation)]
    light = [(b'Light.esm', None)]
    medium = [(b'Medium.esm', _creation)]
    header = _check_masters(140, regular, light, medium)
    assert header.pcName == 'Barrett'

# BCPS chunks -----------------------------------------------------------------
_regular = [(b'Starfield.esm', None),
            *((b'Mod%02d.esm' % i, _creation) for i in range(20))]
_light = [(b'Light.esm', _creation)]
_medium = [(b'Medium.esm', _no_creation)]

@pytest.mark.parametrize('chunk_size', [64, 1 << 18])
def test_bcps_chunks(chunk_size):
    """The header and plugin table may span several chunks - or the whole
    save may be smaller than one chunk."""
    _check_masters(140, _regular, _light, _medium, chunk_size=chunk_size)

def test_bcps_inflates_needed_chunks_only():
    """Reading the header must not inflate the rest of the save - here the
    chunks past the first one are garbage."""
    sf_save = _sf_save(140, _regular, _light, _medium,
                       tail=bytes(range(256)) * 64)
    container = _bcps(sf_save, chunk_size=4096)
    comp_location, = struct.unpack_from('<Q', container, 24)
    first_comp_size, = struct.unpack_from('<I', container, 72)
    first_end = comp_location + first_comp_size
    container = container[:first_end] + b'\xff' * (len(container) - first_end)
    header = _read_header(container)
    assert header.masters_regular == [n.decode() for n, _c in _regular]

def test_bcps_broken_chunk():
    """A chunk the header needs that does not inflate fails the read."""
    container = _bcps(_sf_save(140, _regular, _light, _medium),
                      chunk_size=64)
    with pytest.raises(SaveHeaderError):
        _read_header(container[:len(container) // 2])
