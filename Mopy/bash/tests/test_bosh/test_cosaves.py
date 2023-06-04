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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
import io

from .. import get_meta_value, iter_games, iter_resources, \
    resource_to_displayName, set_game
from ... import bush
from ...bolt import LogFile, Rounder, GPath_no_norm
from ...bosh.cosaves import PluggyCosave, _Remappable, _xSEChunk, \
    _xSEChunkPLGN, _xSEHeader, _xSEModListChunk, get_cosave_types, xSECosave
from ...wbtemp import TempFile

# Helper functions ------------------------------------------------------------
_xse_cosave_exts = (u'.obse', u'.fose', u'.nvse', u'.skse', u'.f4se')
_pluggy_cosave_exts = (u'.pluggy',)
_cosave_exts = _xse_cosave_exts + _pluggy_cosave_exts
def iter_cosaves(filter_by_game: set = frozenset()):
    """Version of iter_resources('saves') that only yields cosaves."""
    for r in iter_resources(u'saves', filter_by_game):
        if r.endswith(_cosave_exts):
            yield r

def _map_cosaves(map_func, cosv_exts, cosv_type):
    """Maps the specified function over all cosaves with one of the specified
    extensions, setting up the correct cosave tags, extensions, etc. first."""
    for gm_folder in iter_games(u'saves'):
        gm_displayName = resource_to_displayName[gm_folder]
        set_game(gm_displayName)
        get_cosave_types(bush.game.fsName, None,
                         bush.game.Se.cosave_tag, bush.game.Se.cosave_ext)
        for c in iter_cosaves(filter_by_game={gm_folder}):
            if c.endswith(cosv_exts):
                map_func(cosv_type(c))

def map_xse_cosaves(map_func):
    """Convenience wrapper around _map_cosaves for xSE cosaves."""
    _map_cosaves(map_func, _xse_cosave_exts, xSECosave)

def map_pluggy_cosaves(map_func):
    """Convenience wrapper around _map_cosaves for Pluggy cosaves."""
    _map_cosaves(map_func, _pluggy_cosave_exts, PluggyCosave)

# Cosave tests ----------------------------------------------------------------
# not easily creatable under NTFS, and unlikely anyways
_impossible_master = u'<|impossible|>'
class ATestACosave(object):
    # Override in subclasses and set to pluggy/xSE-specific ones
    _cosv_exts = ()
    _cosv_type = None

    def _do_map_cosaves(self, map_func):
        """Convenience wrapper around _map_cosaves that passes in
        self._cosv_exts and self._cosv_type."""
        _map_cosaves(map_func, self._cosv_exts, self._cosv_type)

    def test_write_cosave(self):
        """Tests if writing out all cosaves produces the same checksum."""
        def _check_writing(curr_cosave: xSECosave):
            with TempFile() as t:
                temp_cosave_path = GPath_no_norm(t)
                curr_cosave.write_cosave(temp_cosave_path)
                assert curr_cosave.abs_path.crc == temp_cosave_path.crc
                # write_cosave and write_cosave_safe should have the same
                # behavior
                curr_cosave.write_cosave_safe(temp_cosave_path)
                assert curr_cosave.abs_path.crc == temp_cosave_path.crc
                # Cosave writing should not change mtime, since we use that to
                # detect desyncs between save and cosave
                assert Rounder(curr_cosave.abs_path.mtime) == Rounder(
                    temp_cosave_path.mtime)
        self._do_map_cosaves(_check_writing)

    def test_get_master_list(self):
        """Tests if get_master_list is correctly implemented."""
        def _check_get_master_list(curr_cosave: xSECosave):
            assert curr_cosave.get_master_list() == get_meta_value(
                curr_cosave.abs_path, u'cosave_body')[u'cosave_masters']
        self._do_map_cosaves(_check_get_master_list)

    def test_has_accurate_master_list(self):
        """Tests if has_accurate_master_list is correctly implemented."""
        def _check_has_accurate_master_list(curr_cosave: xSECosave):
            assert (not bush.game.has_esl or
                    curr_cosave.has_accurate_master_list() ==
                    get_meta_value(curr_cosave.abs_path, u'cosave_body')[
                        u'masters_are_accurate'])
        self._do_map_cosaves(_check_has_accurate_master_list)

    def test_dump_to_log(self):
        """Tests that dump_to_log is correctly implemented."""
        def _check_dump_to_log(curr_cosave: xSECosave):
            test_log = LogFile(io.StringIO())
            # This wouldn't work on SSE/FO4, but save_masters_ is only used for
            # ARVR and STVR, which don't exist in SKSE/F4SE
            sv_masters = curr_cosave.get_master_list()
            curr_cosave.dump_to_log(test_log, sv_masters)
            assert isinstance(test_log.out.getvalue(), str)
            # Remapping should make the new filename appear in the log
            curr_cosave.remap_plugins({
                curr_cosave.get_master_list()[0]: _impossible_master})
            curr_cosave.dump_to_log(test_log, sv_masters)
            assert _impossible_master in test_log.out.getvalue()
        self._do_map_cosaves(_check_dump_to_log)

    def test_remap_plugins(self):
        """Tests that remap_plugins is correctly implemented."""
        def _check_remap_plugins(curr_cosave: xSECosave):
            # Check that it doesn't throw errors
            first_master = curr_cosave.get_master_list()[0]
            curr_cosave.remap_plugins({first_master: _impossible_master})
            # Check that writing the result out produces a bytestring
            # containing the remapped master name
            with TempFile() as t:
                temp_cosave_path = GPath_no_norm(t)
                curr_cosave.write_cosave(temp_cosave_path)
                assert curr_cosave.abs_path.crc != temp_cosave_path.crc
                with open(temp_cosave_path, 'rb') as ins:
                    assert _impossible_master.encode('ascii') in ins.read()
                # Check that undoing the mapping produces the original file
                # again
                curr_cosave.remap_plugins({_impossible_master: first_master})
                curr_cosave.write_cosave(temp_cosave_path)
                assert curr_cosave.abs_path.crc == temp_cosave_path.crc
        self._do_map_cosaves(_check_remap_plugins)

# xSE cosave tests ------------------------------------------------------------
_valid_first_chunk_sigs = {u'MODS', u'PLGN'}
class TestxSECosave(ATestACosave):
    _cosv_exts = _xse_cosave_exts
    _cosv_type = xSECosave

    def test_read_cosave_light(self):
        """Tests if light-loading all cosaves works and only loads the first
        chunk."""
        def _check_reading_light(curr_cosave: xSECosave):
            curr_cosave.read_cosave(light=True)
            # The first plugin chunk, which belongs to the script extender,
            # must *always* be present, otherwise the cosave is invalid
            assert len(curr_cosave.cosave_chunks) == 1
            assert len(curr_cosave.cosave_chunks[0].chunks) == 1
            assert (curr_cosave.cosave_chunks[0].chunks[0].chunk_type
                    in _valid_first_chunk_sigs)
        self._do_map_cosaves(_check_reading_light)

    def test_read_cosave(self):
        """Tests if full-loading all cosaves works and if the number of cosave
        chunks matches the expected number specified in the header."""
        def _check_reading_full(curr_cosave: xSECosave):
            curr_cosave.read_cosave()
            assert (len(curr_cosave.cosave_chunks) ==
                    curr_cosave.cosave_header.num_plugin_chunks)
        self._do_map_cosaves(_check_reading_full)

class Test_xSEHeader(object):
    def test_write_header(self):
        """Tests that the output of write_header is acceptable."""
        def _check_write_header(curr_cosave: xSECosave):
            # Check that it matches the first 20 bytes
            curr_cosave.read_cosave(light=True)
            with curr_cosave.abs_path.open(u'rb') as ins:
                header_bytes = ins.read(20)
            a_out = io.BytesIO()
            curr_cosave.cosave_header.write_header(a_out)
            assert a_out.getvalue() == header_bytes
            # Check that it works on a roundtrip
            b_out = io.BytesIO()
            _xSEHeader(io.BytesIO(a_out.getvalue()),
                       curr_cosave.abs_path).write_header(b_out)
            assert a_out.getvalue() == b_out.getvalue()
        map_xse_cosaves(_check_write_header)

    def test_header_attrs(self):
        """Tests if the header attributes we read match the ones in the meta
        file."""
        def _check_header_attrs(curr_cosave: xSECosave):
            curr_cosave.read_cosave(light=True)
            cosv_path = curr_cosave.abs_path
            meta_header = get_meta_value(cosv_path, u'cosave_header')
            for header_attr in (u'savefile_tag', u'format_version',
                                u'se_version', u'se_minor_version',
                                u'game_version', u'num_plugin_chunks'):
                assert (getattr(curr_cosave.cosave_header, header_attr) ==
                        meta_header[header_attr])
        map_xse_cosaves(_check_header_attrs)

class Test_xSEPluginChunk(object):
    def test_chunk_length(self):
        """Tests that chunk_length is correctly implemented."""
        def _check_chunk_length(curr_cosave: xSECosave):
            curr_cosave.read_cosave()
            for pchunk in curr_cosave.cosave_chunks:
                assert pchunk.chunk_length() == pchunk.orig_size
        map_xse_cosaves(_check_chunk_length)

    def test_remap_plugins(self):
        """Tests that remap_plugins is correctly implemented."""
        def _check_remap_plugins(curr_cosave: xSECosave):
            curr_cosave.read_cosave()
            first_master = curr_cosave.get_master_list()[0]
            test_mapping = {first_master: first_master + u'1'}
            for pchunk in curr_cosave.cosave_chunks:
                # Remap by making the first master one byte longer, then
                # check that the resulting sizes are now >= than before (can't
                # perform any better check than that here because of LIMD/LMOD,
                # handled in chunk-specific tests below)
                pchunk.remap_plugins(test_mapping)
                assert pchunk.chunk_length() >= pchunk.orig_size
        map_xse_cosaves(_check_remap_plugins)

class ATest_xSEChunk(object):
    # The chunk signature that this class wants to test
    _target_chunk_sig = u'OVERRIDE'

    # Helpers and overrides ---------------------------------------------------
    def _get_remapping(self, curr_chunk: _xSEChunk) -> dict:
        """Returns a dictionary that can be passed to cchunk.remap_plugins.
        Must increase the size of exactly one master by exactly one byte."""
        raise NotImplementedError

    def _map_chunks(self, map_func):
        """Maps the specified functions over all chunks with signature
        _target_chunk_sig."""
        def _process_cosave(curr_cosave: xSECosave):
            curr_cosave.read_cosave()
            for pchunk in curr_cosave.cosave_chunks:
                for cchunk in pchunk.chunks:
                    if self._wants_chunk(cchunk):
                        map_func(cchunk)
        map_xse_cosaves(_process_cosave)

    def _wants_chunk(self, curr_chunk: _xSEChunk) -> bool:
        """Whether or not _map_chunks should map over this chunk."""
        return curr_chunk.chunk_type == self._target_chunk_sig

    # Actual test cases -------------------------------------------------------
    def test_chunk_length(self):
        """Tests that chunk_length is correctly implemented."""
        def _check_chunk_length(curr_chunk: _xSEChunk):
            assert curr_chunk.chunk_length() == curr_chunk.data_len
        self._map_chunks(_check_chunk_length)

    def test_remap_plugins(self):
        """Tests that remap_plugins is correctly implemented."""
        def _check_remap_plugins(curr_chunk: _xSEChunk):
            if not isinstance(curr_chunk, _Remappable): return
            curr_chunk.remap_plugins(self._get_remapping(curr_chunk))
            # PyCharm/py2 is too stupid to combine _Remappable and _xSEChunk
            assert curr_chunk.chunk_length() == curr_chunk.data_len + 1
        self._map_chunks(_check_remap_plugins)

class ATest_xSEModListChunk(ATest_xSEChunk):
    def _get_remapping(self, curr_chunk: _xSEModListChunk) -> dict:
        first_master = curr_chunk.mod_names[0]
        return {first_master: first_master + u'1'}

class Test_xSEChunk_ARVR(ATest_xSEChunk):
    _target_chunk_sig = u'ARVR'

class Test_xSEChunk_DATA(ATest_xSEModListChunk):
    _target_chunk_sig = u'DATA'

class Test_xSEChunk_LMOD(ATest_xSEModListChunk):
    _target_chunk_sig = u'LMOD'

class Test_xSEChunk_LIMD(ATest_xSEModListChunk):
    _target_chunk_sig = u'LIMD'

class Test_xSEChunk_MODS(ATest_xSEModListChunk):
    _target_chunk_sig = u'MODS'

class Test_xSEChunk_PLGN(ATest_xSEChunk):
    _target_chunk_sig = u'PLGN'

    def _get_remapping(self, curr_chunk: _xSEChunkPLGN) -> dict:
        first_master = curr_chunk.mod_entries[0].mod_name
        return {first_master: first_master + u'1'}

class Test_xSEChunk_STVR(ATest_xSEChunk):
    _target_chunk_sig = u'STVR'

# Fallback class for all chunks that haven't been decoded yet and hence don't
# have a special class above
class Test_xSEChunk_Others(ATest_xSEChunk):
    def _wants_chunk(self, curr_chunk):
        return not curr_chunk.fully_decoded

# Pluggy cosave tests ---------------------------------------------------------
class TestPluggyCosave(ATestACosave):
    _cosv_exts = _pluggy_cosave_exts
    _cosv_type = PluggyCosave

# TODO(inf) Gather some pluggy cosaves and expand this
