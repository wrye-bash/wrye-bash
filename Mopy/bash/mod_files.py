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
"""This module houses the entry point for reading and writing plugin files
through PBash (LoadFactory + ModFile) as well as some related classes."""

from collections import defaultdict
from collections.abc import Iterable
from zlib import decompress as zlib_decompress
from zlib import error as zlib_error

from . import bolt, bush, env
from .bolt import MasterSet, SubProgress, decoder, deprint, sig_to_str, \
    struct_error, GPath_no_norm
# first import of brec for games with patchers - _dynamic_import_modules
from .brec import ZERO_FID, FastModReader, FormIdReadContext, \
    FormIdWriteContext, MobBase, ModReader, MreRecord, RecHeader, \
    RecordHeader, RecordType, Subrecord, TopGrup, int_unpacker, null1, \
    unpack_header, FormId, SubrecordBlob
from .exception import MasterMapError, ModError, ModReadError, StateError
from .load_order import get_ordered
from .wbtemp import TempFile

class MasterMap(object):
    """Serves as a map between two sets of masters."""
    def __init__(self,inMasters,outMasters):
        """Initiation."""
        mast_map = {}
        outMastersIndex = outMasters.index
        for index,master in enumerate(inMasters):
            try:
                mast_map[index] = outMastersIndex(master)
            except ValueError:
                mast_map[index] = -1
        self._mast_map = mast_map

    def __call__(self, short_fid: int | None, dflt_fid=-1):
        """Maps a fid from first set of masters to second. If no mapping
        is possible, then either returns default (if defined) or raises MasterMapError."""
        if not short_fid: return short_fid
        inIndex = int(short_fid >> 24)
        outIndex = self._mast_map.get(inIndex, -2)
        if outIndex >= 0:
            return (int(outIndex) << 24 ) | (short_fid & 0xFFFFFF)
        elif dflt_fid != -1:
            return dflt_fid
        else:
            raise MasterMapError(inIndex)

class LoadFactory:
    """Encapsulate info on which record type we use to load which record
    signature."""
    grup_class = {} # map top record group signatures to class loading them
    __slots__ = ('keepAll', 'topTypes', 'sig_to_type', 'all_sigs')

    def __init__(self, keepAll, *, by_sig: Iterable[bytes] = (),
                 generic: Iterable[bytes] = ()):
        """Pass a collection of signatures to load - either by their
        respective type or using generic MreRecord.
        :param by_sig: pass an iterable of top group signatures to unpack
        :param generic: top group signatures to load as generic MreRecord"""
        self.keepAll = keepAll
        self.topTypes = set()
        self.sig_to_type = defaultdict(lambda: MreRecord if keepAll else None)
        self.all_sigs = set()
        # no generic classes if we keep all (we return MreRecord anyway)
        self.add_class(*by_sig, generic=() if keepAll else generic)

    def add_class(self, *by_sig, generic: Iterable[bytes] = ()):
        """Adds specified record types - see __init__."""
        all_sigs = {*by_sig, *generic}
        if all_sigs - RecHeader.valid_record_sigs:
            raise ModError(None, f'Unknown signatures: '
                                 f'{all_sigs - RecHeader.valid_record_sigs}')
        #--Don't replace complex class with default (MreRecord) class
        if generic:
            self.sig_to_type = {**dict.fromkeys(generic, MreRecord),
                                **self.sig_to_type}
        if by_sig:
            self.sig_to_type.update(
                (k, RecordType.sig_to_class[k]) for k in by_sig)
        self.all_sigs = {*self.all_sigs, *all_sigs}
        #--Top type
        for class_sig in all_sigs:
            if class_sig in RecordType.nested_to_top:
                self.topTypes.update(RecordType.nested_to_top[class_sig])
            if class_sig in RecordHeader.top_grup_sigs:
                self.topTypes.add(class_sig) # b'CELL' appears in both

    def getTopClass(self, top_rec_type) -> type[MobBase | TopGrup] | None:
        """Return top block class for top block type, or None."""
        try:
            mob_type = self.grup_class[top_rec_type]
            return mob_type if top_rec_type in self.topTypes else (
                MobBase if self.keepAll else None)
        except KeyError:
            raise ModError(None, f'Invalid top group signature {top_rec_type}')

    def __repr__(self):
        return f'<LoadFactory: load {len(self.sig_to_type)} types ' \
               f'({", ".join(map(sig_to_str, self.sig_to_type))}), ' \
               f'{"keep" if self.keepAll else "discard"} others>'

class _TopGroupDict(dict):
    """dict subclass holding ModFile's collection of top groups key'd by sig"""
    __slots__ = ('_mod_file',)

    def __init__(self, mod_file, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mod_file = mod_file

    def __missing__(self, top_grup_sig):
        """Return top block of specified topType, creating it first.
        :raise ModError"""
        topClass = self._mod_file.loadFactory.getTopClass(top_grup_sig)
        if topClass is None:
            raise ModError(self._mod_file.fileInfo.fn_key,
                f'Failed to retrieve top class for {sig_to_str(top_grup_sig)};'
                f' load factory is {self._mod_file.loadFactory!r}')
        self[top_grup_sig] = topClass.empty_mob(self._mod_file.loadFactory,
                                                top_grup_sig)
        return self[top_grup_sig]

class ModFile(object):
    """Plugin file representation. Will load only the top record types
    specified in its LoadFactory."""
    def __init__(self, fileInfo,loadFactory=None):
        self.fileInfo = fileInfo
        self.loadFactory = loadFactory or LoadFactory(True) ##: trace
        #--Variables to load
        self.tes4 = bush.game.plugin_header_class(
            RecHeader(bush.game.Esp.plugin_header_sig, arg2=ZERO_FID,
                      _entering_context=True))
        self.tes4.setChanged()
        self.strings = bolt.StringTable()
        self.tops = _TopGroupDict(self) #--Top groups.
        self.topsSkipped = set() #--Types skipped

    def load_plugin(self, progress=None, loadStrings=True, catch_errors=True,
                    do_map_fids=True):
        ##: track uses and decide on exception handling
        """Load file."""
        progress = progress or bolt.Progress()
        progress.setFull(1.0)
        cont = FormIdReadContext if do_map_fids else ModReader
        with cont.from_info(self.fileInfo) as ins:
            if not do_map_fids: # hacky - only used for Mod_RecalcRecordCounts
                ins.load_tes4(do_unpack_tes4=False)
            self.tes4 = ins.plugin_header
            if do_map_fids:
                progress = self.__load_strs(ins, loadStrings, progress)
            #--Raw data read
            progress.setFull(ins.size)
            insAtEnd = ins.atEnd
            insTell = ins.tell
            while not insAtEnd():
                #--Get record info and handle it
                g_head = unpack_header(ins)
                if not g_head.is_top_group_header:
                    raise ModError(self.fileInfo.fn_key, u'Improperly grouped file.')
                top_grup_sig = g_head.label
                topClass = self.loadFactory.getTopClass(top_grup_sig)
                try:
                    if topClass:
                        new_top = topClass(g_head, self.loadFactory, ins)
                        # Starting with FO4, some of Bethesda's official files
                        # have duplicate top-level groups
                        if top_grup_sig not in self.tops:
                            self.tops[top_grup_sig] = new_top
                        elif hasattr(new_top, 'grup_blob'):
                            # Duplicate top-level group and we can't merge due
                            # to not loading it fully. Log and replace the
                            # existing one
                            deprint(f'{self.fileInfo}: Duplicate top-level '
                                    f'{sig_to_str(top_grup_sig)} group loaded '
                                    f'as MobBase, replacing')
                            self.tops[top_grup_sig] = new_top
                        else:
                            # Duplicate top-level group and we can merge
                            self.tops[top_grup_sig].merge_records(new_top,
                                None, set(), False)
                    else:
                        self.topsSkipped.add(top_grup_sig)
                        g_head.skip_blob(ins)
                except:
                    if catch_errors:
                        deprint(f'Error in {self.fileInfo}', traceback=True)
                        break
                    else:
                        # Useful for implementing custom error behavior, see
                        # e.g. Mod_FullLoad
                        raise
                progress(insTell())
        if not do_map_fids: return

    def __load_strs(self, ins, loadStrings, progress):
        # Check if we need to handle strings
        self.strings.clear()
        if loadStrings and getattr(self.tes4.flags1, 'localized', False):
            from . import bosh
            stringsProgress = SubProgress(progress, 0,
                                          0.1)  # Use 10% of progress bar
            # for strings
            lang = bosh.oblivionIni.get_ini_language()
            stringsPaths = self.fileInfo.getStringsPaths(lang)
            stringsProgress.setFull(max(len(stringsPaths), 1))
            for i, path in enumerate(stringsPaths):
                self.strings.loadFile(path,
                                      SubProgress(stringsProgress, i, i + 1),
                                      lang)
                stringsProgress(i)
            ins.setStringTable(self.strings)
            subProgress = SubProgress(progress, 0.1, 1.0)
        else:
            ins.setStringTable(None)
            subProgress = progress
        return subProgress

    def safeSave(self):
        """Save data to file safely.  Works under UAC."""
        self.fileInfo.makeBackup()
        filePath = self.fileInfo.getPath()
        with TempFile() as tmp_plugin:
            self.save(tmp_plugin)
            # fileInfo created before the file
            if self.fileInfo.mtime is not None:
                GPath_no_norm(tmp_plugin).mtime = self.fileInfo.mtime ##: ugh
            # FIXME If saving a locked (by xEdit f.i.) bashed patch a bogus UAC
            #  permissions dialog is displayed (should display file in use)
            env.shellMove({tmp_plugin: filePath})
        self.fileInfo.extras.clear()

    def save(self,outPath=None):
        """Save data to file.
        outPath -- Path of the output file to write to. Defaults to original file path."""
        if not self.loadFactory.keepAll:
            raise StateError('Insufficient data to write file.')
        # Too many masters is fatal and results in cryptic struct errors, so
        # loudly complain about it here
        if self.tes4.num_masters > bush.game.Esp.master_limit:
            raise ModError(self.fileInfo.fn_key,
                           f'Attempting to write a file with too many '
                           f'masters (>{bush.game.Esp.master_limit}).')
        outPath = outPath or self.fileInfo.abs_path
        with FormIdWriteContext(outPath, self.augmented_masters(),
                                self.tes4.version) as out:
            #--Mod Record
            self.tes4.setChanged()
            self.tes4.numRecords = sum(block.get_num_headers()
                                       for block in self.tops.values())
            self.tes4.getSize()
            self.tes4.dump(out)
            #--Blocks
            selfTops = self.tops
            for rsig in bush.game.top_groups:
                if rsig in selfTops:
                    selfTops[rsig].dump(out)

    def augmented_masters(self):
        """List of plugin masters with the plugin's own name appended."""
        return [*self.tes4.masters, self.fileInfo.fn_key]

    def iter_tops(self, top_sigs):
        return ((top_sig, t) for top_sig, t in self.tops.items() if
                top_sig in top_sigs)

    def getMastersUsed(self):
        """Updates set of master names according to masters actually used."""
        masters_set = MasterSet([bush.game.master_file])
        for block in self.tops.values():
            block.updateMasters(masters_set.add)
        # The file itself is always implicitly available, so discard it here
        masters_set.discard(self.fileInfo.fn_key)
        return get_ordered(masters_set)

    def _index_mgefs(self):
        """Indexes and cache all MGEF properties and stores them for retrieval
        by the patchers. We do this once at all so we only have to iterate over
        the MGEFs once."""
        mgef_class = RecordType.sig_to_class[b'MGEF']
        m_hostiles = mgef_class.hostile_effects.copy()
        m_names = mgef_class.mgef_name.copy()
        hostile_recs = set()
        nonhostile_recs = set()
        if b'MGEF' in self.tops:
            for _rid, record in self.tops[b'MGEF'].iter_present_records():
                ##: Skip OBME records, at least for now
                if record.obme_record_version is not None: continue
                target_set = (hostile_recs if record.flags.hostile
                              else nonhostile_recs)
                target_set.add(record.eid)
                m_names[record.eid] = record.full or u'' # could this be None?
        self.cached_mgef_hostiles = m_hostiles - nonhostile_recs | hostile_recs
        self.cached_mgef_names = m_names

    def getMgefHostiles(self):
        """Return a set of hostile magic effect codes. This is intended for use
        with the patch file when it records for all magic effects. If magic
        effects are not available, it will revert to constants.py version."""
        try:
             # Try to just return the cached version
            return self.cached_mgef_hostiles
        except AttributeError:
            self._index_mgefs()
            return self.cached_mgef_hostiles

    def getMgefName(self):
        """Return a dictionary mapping magic effect code to magic effect name.
        This is intended for use with the patch file when it records for all
        magic effects. If magic effects are not available, it will revert to
        constants.py version."""
        try:
            return self.cached_mgef_names
        except AttributeError:
            self._index_mgefs()
            return self.cached_mgef_names

    def __repr__(self):
        return f'ModFile<{self.fileInfo}>'

    def create_record(self, new_rec_sig: bytes, new_rec_fid: FormId = None, *,
                      head_flags=0):
        """Create a new record with the specified record signature (and
        optionally the specified FormID - if it's not given, it will become a
        new record inside the mod file's FormID space)."""
        if new_rec_fid is None:
            new_rec_fid = FormId.from_tuple(
                (self.fileInfo.fn_key, self.tes4.getNextObject()))
        new_rec = RecordType.sig_to_class[new_rec_sig](RecHeader(new_rec_sig,
            arg1=head_flags, arg2=new_rec_fid, _entering_context=True))
        new_rec.setChanged()
        self.tops[new_rec_sig].setRecord(new_rec, do_copy=False)
        return new_rec

# TODO(inf) Use this for a bunch of stuff in mods_metadata.py (e.g. UDRs)
class ModHeaderReader(object):
    """Allows very fast reading of a plugin's headers, skipping reading and
    decoding of anything but the headers."""
    @staticmethod
    def formids_in_esl_range(mod_info):
        """Checks if all FormIDs in the specified mod are in the ESL range."""
        num_masters = len(mod_info.masterNames)
        with ModReader.from_info(mod_info) as ins:
            ins_at_end = ins.atEnd
            try:
                while not ins_at_end():
                    next_header = unpack_header(ins)
                    # Skip GRUPs themselves, only process their records
                    if next_header.recType != b'GRUP':
                        header_fid = next_header.fid
                        if (header_fid.mod_dex >= num_masters and
                                header_fid.object_dex > 0xFFF):
                            return False # FormID out of range
                        next_header.skip_blob(ins)
            except (OSError, struct_error) as e:
                raise ModError(ins.inName, f"Error scanning {mod_info}, file "
                    f"read pos: {ins.tell():d}\nCaused by: '{e!r}'")
        return True

    @staticmethod
    def extract_mod_data(mod_info, progress, *, __unpacker=int_unpacker):
        """Reads the headers and EDIDs of every record in the specified mod,
        returning them as a dict, mapping record signature to a dict mapping
        FormIDs to a list of tuples containing the headers and EDIDs of every
        record with that signature. Note that the flags are not processed
        either - if you need that, manually call MreRecord.flags1_() on them.

        :rtype: defaultdict[bytes, defaultdict[int, tuple[RecHeader, str]]]"""
        # This method is *heavily* optimized for performance. Inlines and other
        # ugly code ahead
        progress = progress or bolt.Progress()
        # Store a bunch of repeatedly used constants/methods/etc. because
        # accessing via dot is slow
        wanted_encoding = bolt.pluginEncoding
        avoided_encodings = (u'utf8', u'utf-8')
        minf_size = mod_info.fsize
        plugin_fn = mod_info.fn_key
        sh_unpack = Subrecord.sub_header_unpack
        sh_size = Subrecord.sub_header_size
        main_progress_msg = _(u'Loading: %s') % plugin_fn
        # Where we'll store all the collected record data
        group_records = defaultdict(lambda: defaultdict(tuple))
        # The current top GRUP label - starts out as TES4/TES3
        tg_label = bush.game.Esp.plugin_header_sig
        # The dict we'll use to store records from the current top GRUP
        records = group_records[tg_label]
        ##: Uncomment these variables and the block below that uses them once
        # all of FO4's record classes have been written
        # The record types that can even contain EDIDs
        #records_with_eids = RecordType.subrec_sig_to_record_sig[b'EDID']
        # Whether or not we can skip looking for EDIDs for  the current record
        # type because it doesn't even have any
        #skip_eids = tg_label not in records_with_eids
        with mod_info.abs_path.open(u'rb') as ins:
            initial_bytes = ins.read()
        with FastModReader(plugin_fn, initial_bytes) as ins:
            # PY3.12: Check if removing these is faster now - on py3.11 it is
            # *slower*, even though it really should be faster!
            # More local methods to avoid repeated dot access
            ins_tell = ins.tell
            ins_seek = ins.seek
            ins_read = ins.read
            ins_size = ins.size
            while ins_tell() != ins_size:
                # Unpack the headers - these can be either GRUPs or regular
                # records
                next_header = unpack_header(ins)
                _rsig = next_header.recType
                if _rsig == b'GRUP':
                    # Nothing special to do for non-top GRUPs
                    if not next_header.is_top_group_header: continue
                    tg_label = next_header.label
                    progress(ins_tell() / minf_size,
                             f'{main_progress_msg}\n{sig_to_str(tg_label)}')
                    records = group_records[tg_label]
                #     skip_eids = tg_label not in records_with_eids
                # elif skip_eids:
                #     # This record type has no EDIDs, skip directly to the next
                #     # record (can't use skip_blob because that passes
                #     # debug_strs to seek()...)
                #     records[next_header.fid] = (next_header, '')
                #     ins_seek(ins_tell() + next_header.blob_size)
                else:
                    # This is a regular record, look for the EDID subrecord
                    eid = u''
                    blob_siz = next_header.blob_size
                    next_record = ins_tell() + blob_siz
                    if next_header.flags1 & 0x00040000: # 'compressed' flag
                        size_check = __unpacker(ins_read(4))[0]
                        try:
                            new_rec_data = zlib_decompress(ins_read(
                                blob_siz - 4))
                        except zlib_error:
                            if plugin_fn == u'FalloutNV.esm':
                                # Yep, FalloutNV.esm has a record with broken
                                # zlib data. Just skip it.
                                ins_seek(next_record)
                                continue
                            raise
                        if len(new_rec_data) != size_check:
                            raise ModError(ins.inName,
                                f'Mis-sized compressed data. Expected '
                                f'{size_check}, got {len(new_rec_data)}.')
                    else:
                        new_rec_data = ins_read(blob_siz)
                    fmr = FastModReader(plugin_fn, new_rec_data)
                    fmr_seek = fmr.seek
                    fmr_read = fmr.read
                    fmr_tell = fmr.tell
                    fmr_size = fmr.size
                    fmr_unpack = fmr.unpack
                    while fmr_tell() != fmr_size:
                        # Inlined from unpackSubHeader & FastModReader.unpack
                        read_data = fmr_read(sh_size)
                        if len(read_data) != sh_size:
                            raise ModReadError(
                                plugin_fn, [_rsig, u'SUB_HEAD'],
                                fmr_tell() - len(read_data), fmr_size)
                        mel_sig, mel_size = sh_unpack(read_data)
                        # Extended storage - very rare, so don't optimize
                        # inlines etc. for it
                        if mel_sig == b'XXXX':
                            # Throw away size here (always == 0)
                            mel_size = fmr_unpack(__unpacker, 4, _rsig,
                                                  'XXXX.SIZE')[0]
                            mel_sig = fmr_unpack(sh_unpack, sh_size,
                                                 _rsig, 'XXXX.TYPE')[0]
                        if mel_sig == b'EDID':
                            # No need to worry about newlines, these are Editor
                            # IDs and so won't contain any
                            eid = decoder(fmr_read(mel_size).rstrip(null1),
                                          wanted_encoding, avoided_encodings)
                            break
                        else:
                            fmr_seek(mel_size, 1)
                    records[next_header.fid] = (next_header, eid)
                    ins_seek(next_record) # we may have break'd at EDID
        del group_records[bush.game.Esp.plugin_header_sig] # skip TES4 record
        return group_records

    ##: The methods above have to be very fast, but this one can afford to be
    # much slower. Should eventually be absorbed by refactored ModFile API.
    @staticmethod
    def read_temp_child_headers(mod_info) -> list[RecHeader]:
        """Reads the headers of all temporary CELL chilren in the specified mod
        and returns them as a list. Used for determining FO3/FNV/TES5 ONAM."""
        ret_headers = []
        # We want to read only the children of these, so skip their tops
        interested_sigs = {b'CELL', b'WRLD'}
        tops_to_skip = interested_sigs | {bush.game.Esp.plugin_header_sig}
        with FormIdReadContext.from_info(mod_info) as ins:
            ins_at_end = ins.atEnd
            try:
                while not ins_at_end():
                    next_header = unpack_header(ins)
                    header_rec_sig = next_header.recType
                    if header_rec_sig == b'GRUP':
                        header_group_type = next_header.groupType
                        # Skip all top-level GRUPs we're not interested in
                        # (group type == 0) and all persistent children and
                        # dialog topics (group type == 7 or 8, respectively).
                        if ((next_header.is_top_group_header and
                             next_header.label not in interested_sigs)
                                or header_group_type in (7, 8)):
                            # Note that GRUP sizes include their own header
                            # size, so we need to subtract that
                            next_header.skip_blob(ins)
                    elif header_rec_sig in tops_to_skip:
                        # Skip TES4, CELL and WRLD to get to their contents
                        next_header.skip_blob(ins)
                    else:
                        # We must be in a temp CELL children group, store the
                        # header and skip the record body
                        ret_headers.append(next_header)
                        next_header.skip_blob(ins)
            except (OSError, struct_error) as e:
                msg = f'Error scanning {mod_info}, file read pos: {ins.tell()}'
                raise ModError(ins.inName, msg) from e
        return ret_headers

    @staticmethod
    def read_all_subrecords(mod_info) -> \
            dict[bytes, list[tuple[RecHeader, list[SubrecordBlob]]]]:
        """Read the specified plugin, returning a dict mapping signatures to
        tuples of record headers and the subrecords those headers contain."""
        ret_records = defaultdict(list)
        curr_sig = None
        with FormIdReadContext.from_info(mod_info) as ins:
            try:
                while not ins.atEnd():
                    next_header = unpack_header(ins)
                    if next_header.recType == b'GRUP':
                        if next_header.is_top_group_header:
                            curr_sig = next_header.label
                    else:
                        subrecs = list(
                            MreRecord(next_header, ins).iterate_subrecords())
                        ret_records[curr_sig].append((next_header, subrecs))
            except (OSError, struct_error) as e:
                msg = f'Error scanning {mod_info}, file read pos: {ins.tell()}'
                raise ModError(ins.inName, msg) from e
        return ret_records
