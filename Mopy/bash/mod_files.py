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
"""This module houses the entry point for reading and writing plugin files
through PBash (LoadFactory + ModFile) as well as some related classes."""

from collections import defaultdict
from itertools import chain
from zlib import decompress as zlib_decompress, error as zlib_error

from . import bolt, bush, env, load_order
from .bolt import deprint, SubProgress, structs_cache, struct_error, decoder, \
    sig_to_str, str_to_sig
from .brec import MreRecord, ModReader, RecordHeader, RecHeader, null1, \
    TopGrupHeader, MobBase, MobDials, MobICells, MobObjects, MobWorlds, \
    unpack_header, FastModReader, Subrecord
from .exception import MasterMapError, ModError, StateError, ModReadError

class MasterSet(set):
    """Set of master names."""
    def add(self,element):
        """Add an element it's not empty. Special handling for tuple."""
        if isinstance(element,tuple):
            set.add(self,element[0])
        elif element:
            set.add(self,element)

    def getOrdered(self):
        """Returns masters in proper load order."""
        return load_order.get_ordered(self)

class MasterMap(object):
    """Serves as a map between two sets of masters."""
    def __init__(self,inMasters,outMasters):
        """Initiation."""
        mast_map = {}
        outMastersIndex = outMasters.index
        for index,master in enumerate(inMasters):
            if master in outMasters:
                mast_map[index] = outMastersIndex(master)
            else:
                mast_map[index] = -1
        self._mast_map = mast_map

    def __call__(self, short_fid, default=-1):
        """Maps a fid from first set of masters to second. If no mapping
        is possible, then either returns default (if defined) or raises MasterMapError."""
        if not short_fid: return short_fid
        inIndex = int(short_fid >> 24)
        outIndex = self._mast_map.get(inIndex, -2)
        if outIndex >= 0:
            return (int(outIndex) << 24 ) | (short_fid & 0xFFFFFF)
        elif default != -1:
            return default
        else:
            raise MasterMapError(inIndex)

class LoadFactory(object):
    """Factory for mod representation objects."""
    def __init__(self, keepAll, *, by_sig=(), generic=()):
        """Pass a collection of signatures to load - either by their
        respective type or using generic MreRecord.
        :param by_sig: pass an iterable of top group signatures to load
        :type by_sig: Iterable[bytes]
        :param generic: top group signatures to load as generic MreRecord
        :type generic: Iterable[bytes]
        """
        self.keepAll = keepAll
        self.recTypes = set()
        self.topTypes = set()
        self.type_class = {}
        recClasses = chain(generic, (MreRecord.type_class[x] for x in by_sig))
        for recClass in recClasses:
            self.addClass(recClass)

    def addClass(self, recClass, __cell_rec_sigs=frozenset([b'WRLD', b'ROAD',
            b'CELL', b'REFR', b'ACHR', b'ACRE', b'PGRD', b'LAND'])):
        """Adds specified class."""
        if isinstance(recClass, bytes):
            class_sig = recClass
            recClass = MreRecord
        else:
            try:
                class_sig = recClass.rec_sig
            except AttributeError:
                raise ValueError(f'addClass: bytes or MreRecord expected - '
                                 f'got: {recClass!r}!')
        #--Don't replace complex class with default (MreRecord) class
        if class_sig in self.type_class and recClass == MreRecord:
            return
        self.recTypes.add(class_sig)
        self.type_class[class_sig] = recClass
        #--Top type
        if class_sig in __cell_rec_sigs:
            self.topTypes.add(b'CELL')
            self.topTypes.add(b'WRLD')
            if self.keepAll:
                for cell_rec_sig in __cell_rec_sigs:
                    if cell_rec_sig not in self.type_class:
                        self.type_class[cell_rec_sig] = MreRecord
        ##: apart from this and cell stuff above set(type_class) == topTypes
        elif class_sig == b'INFO':
            self.topTypes.add(b'DIAL')
        else:
            self.topTypes.add(class_sig)

    def getRecClass(self,type):
        """Returns class for record type or None."""
        default = (self.keepAll and MreRecord) or None
        return self.type_class.get(type,default)

    def getCellTypeClass(self):
        """Returns type_class dictionary for cell objects."""
        return {r: self.getRecClass(r) for r in (
            b'REFR', b'ACHR', b'ACRE', b'PGRD', b'LAND', b'CELL', b'ROAD')}

    def getUnpackCellBlocks(self,topType):
        """Returns whether cell blocks should be unpacked or not. Only relevant
        if CELL and WRLD top types are expanded."""
        return (
            self.keepAll or
            (self.recTypes & {b'REFR', b'ACHR', b'ACRE', b'PGRD', b'LAND'}) or
            (topType == b'WRLD' and b'LAND' in self.recTypes))

    def getTopClass(self, top_rec_type):
        """Return top block class for top block type, or None.

        :rtype: type[MobBase]"""
        if top_rec_type in self.topTypes:
            if   top_rec_type == b'DIAL': return MobDials
            elif top_rec_type == b'CELL': return MobICells
            elif top_rec_type == b'WRLD': return MobWorlds
            else: return MobObjects
        else:
            return MobBase if self.keepAll else None

    def __repr__(self):
        return f'<LoadFactory: load {len(self.recTypes)} types ' \
               f'({", ".join(map(sig_to_str, self.recTypes))}), ' \
               f'{u"keep" if self.keepAll else u"discard"} others>'

class _RecGroupDict(dict):
    """dict subclass holding ModFile's collection of top groups key'd by sig"""
    __slots__ = (u'_mod_file',)

    def __init__(self, mod_file, *args, **kwargs):
        super(_RecGroupDict, self).__init__(*args, **kwargs)
        self._mod_file = mod_file

    def __missing__(self, top_grup_sig, __rh=RecordHeader):
        """Return top block of specified topType, creating it, if necessary.
        :raise ModError KeyError"""
        if top_grup_sig not in __rh.top_grup_sigs:
            raise KeyError(f'Invalid top group type: '
                           f'{sig_to_str(top_grup_sig)}')
        topClass = self._mod_file.loadFactory.getTopClass(top_grup_sig)
        if topClass is None:
            raise ModError(self._mod_file.fileInfo.ci_key,
                f'Failed to retrieve top class for {sig_to_str(top_grup_sig)};'
                f' load factory is {self._mod_file.loadFactory!r}')
        self[top_grup_sig] = topClass(TopGrupHeader(0, top_grup_sig, 0),
                                      self._mod_file.loadFactory)
        self[top_grup_sig].setChanged()
        return self[top_grup_sig]

class ModFile(object):
    """Plugin file representation. Will load only the top record types
    specified in its LoadFactory."""
    def __init__(self, fileInfo,loadFactory=None):
        self.fileInfo = fileInfo
        self.loadFactory = loadFactory or LoadFactory(True) ##: trace
        #--Variables to load
        self.tes4 = bush.game.plugin_header_class(RecHeader())
        self.tes4.setChanged()
        self.strings = bolt.StringTable()
        self.tops = _RecGroupDict(self) #--Top groups.
        self.topsSkipped = set() #--Types skipped
        self.longFids = False

    def load(self, do_unpack=False, progress=None, loadStrings=True,
             catch_errors=True, do_map_fids=True): # TODO: let it blow?
        """Load file."""
        progress = progress or bolt.Progress()
        progress.setFull(1.0)
        with ModReader(self.fileInfo.ci_key, self.fileInfo.getPath().open(
                u'rb')) as ins:
            insRecHeader = ins.unpackRecHeader
            # Main header of the mod file - generally has 'TES4' signature
            header = insRecHeader()
            self.tes4 = bush.game.plugin_header_class(header,ins,True)
            subProgress = self.__load_strs(do_unpack, ins, loadStrings,
                                           progress)
            #--Raw data read
            subProgress.setFull(ins.size)
            insAtEnd = ins.atEnd
            insTell = ins.tell
            while not insAtEnd():
                #--Get record info and handle it
                header = insRecHeader()
                if not header.is_top_group_header:
                    raise ModError(self.fileInfo.ci_key, u'Improperly grouped file.')
                label = header.label
                topClass = self.loadFactory.getTopClass(label)
                try:
                    if topClass:
                        new_top = topClass(header, self.loadFactory)
                        load_fully = do_unpack and (topClass != MobBase)
                        new_top.load_rec_group(ins, load_fully)
                        # Starting with FO4, some of Bethesda's official files
                        # have duplicate top-level groups
                        if label not in self.tops:
                            self.tops[label] = new_top
                        elif not load_fully:
                            # Duplicate top-level group and we can't merge due
                            # to not loading it fully. Log and replace the
                            # existing one
                            deprint(f'{self.fileInfo}: Duplicate top-level '
                                f'{label} group loaded as MobBase, replacing')
                            self.tops[label] = new_top
                        else:
                            # Duplicate top-level group and we can merge
                            deprint(f'{self.fileInfo}: Duplicate top-level '
                                    f'{label} group, merging')
                            self.tops[label].merge_records(new_top, set(),
                                set(), False, False)
                    else:
                        self.topsSkipped.add(label)
                        header.skip_blob(ins)
                except:
                    if catch_errors:
                        deprint(f'Error in {self.fileInfo}', traceback=True)
                        break
                    else:
                        # Useful for implementing custom error behavior, see
                        # e.g. Mod_FullLoad
                        raise
                subProgress(insTell())
        # Done reading - convert to long FormIDs at the IO boundary
        if do_map_fids: self._convert_fids(to_long=True)

    def __load_strs(self, do_unpack, ins, loadStrings, progress):
        # Check if we need to handle strings
        self.strings.clear()
        if do_unpack and loadStrings and self.tes4.flags1.hasStrings:
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
        self.fileInfo.tempBackup()
        filePath = self.fileInfo.getPath()
        self.save(filePath.temp)
        if self.fileInfo.mtime is not None: # fileInfo created before the file
            filePath.temp.mtime = self.fileInfo.mtime
        # FIXME If saving a locked (by xEdit f.i.) bashed patch a bogus UAC
        # permissions dialog is displayed (should display file in use)
        env.shellMove(filePath.temp, filePath, parent=None) # silent=True just returns - no error!
        self.fileInfo.extras.clear()

    def save(self,outPath=None):
        """Save data to file.
        outPath -- Path of the output file to write to. Defaults to original file path."""
        if not self.loadFactory.keepAll: raise StateError(u"Insufficient data to write file.")
        # Convert back to short FormIDs at the IO boundary
        self._convert_fids(to_long=False)
        outPath = outPath or self.fileInfo.getPath()
        # Too many masters is fatal and results in cryptic struct errors, so
        # loudly complain about it here
        if self.tes4.num_masters > bush.game.Esp.master_limit:
            raise ModError(self.fileInfo.ci_key,
                u'Attempting to write a file with too many masters (>%u).'
                % bush.game.Esp.master_limit)
        with outPath.open(u'wb') as out:
            #--Mod Record
            self.tes4.setChanged()
            self.tes4.numRecords = sum(block.getNumRecords()
                                       for block in self.tops.values())
            self.tes4.getSize()
            self.tes4.dump(out)
            #--Blocks
            selfTops = self.tops
            for rsig in RecordHeader.top_grup_sigs:
                if rsig in selfTops:
                    selfTops[rsig].dump(out)

    def getLongMapper(self):
        """Returns a mapping function to map short fids to long fids."""
        masters_list = self.augmented_masters()
        max_masters = len(masters_list) - 1
        def mapper(short_fid):
            # Return unchanged for None (== unset) and fids that are already
            # in long format
            ##: Drop long check in the future?
            if short_fid is None or isinstance(short_fid, tuple):
                return short_fid
            # Clamp HITMEs by using at most max_masters for master index
            return (masters_list[min(short_fid >> 24, max_masters)],
                    short_fid & 0xFFFFFF)
        return mapper

    def augmented_masters(self):
        """List of plugin masters with the plugin's own name appended."""
        return [*self.tes4.masters, self.fileInfo.ci_key]

    def getShortMapper(self):
        """Returns a mapping function to map long fids to short fids."""
        masters_list = self.augmented_masters()
        indexes = {mname: index for index, mname in enumerate(masters_list)}
        has_expanded_range = bush.game.Esp.expanded_plugin_range
        if (has_expanded_range and len(masters_list) > 1
                and self.tes4.version >= 1.0):
            # Plugin has at least one master, it may freely use the
            # expanded (0x000-0x800) range
            def _master_index(m_name, _obj_id):
                return indexes[m_name]
        else:
            # 0x000-0x800 are reserved for hardcoded (engine) records
            def _master_index(m_name, obj_id):
                return indexes[m_name] if obj_id >= 0x800 else 0
        def mapper(long_fid):
            if long_fid is None: return None
            if isinstance(long_fid, int): return long_fid
            modName, object_id = long_fid
            return (_master_index(modName, object_id) << 24) | object_id
        return mapper

    def _convert_fids(self, to_long):
        """Convert fids to the specified format - long FormIDs if to_long is
        True, short FormIDs otherwise."""
        mapper = self.getLongMapper() if to_long else self.getShortMapper()
        for target_top in self.tops.values():
            target_top.convertFids(mapper, to_long)
        self.longFids = to_long

    def getMastersUsed(self):
        """Updates set of master names according to masters actually used."""
        if not self.longFids: raise StateError(u"ModFile fids not in long form.")
        masters_set = MasterSet([bush.game.master_file])
        for block in self.tops.values():
            block.updateMasters(masters_set.add)
        # The file itself is always implicitly available, so discard it here
        masters_set.discard(self.fileInfo.ci_key)
        return masters_set.getOrdered()

    def _index_mgefs(self):
        """Indexes and cache all MGEF properties and stores them for retrieval
        by the patchers. We do this once at all so we only have to iterate over
        the MGEFs once."""
        m_school = bush.game.mgef_school.copy()
        m_hostiles = bush.game.hostile_effects.copy()
        m_names = bush.game.mgef_name.copy()
        hostile_recs = set()
        nonhostile_recs = set()
        unpack_eid = structs_cache[u'I'].unpack
        if b'MGEF' in self.tops:
            for record in self.tops[b'MGEF'].getActiveRecords():
                ##: Skip OBME records, at least for now
                if record.obme_record_version is not None: continue
                m_school[record.eid] = record.school
                target_set = (hostile_recs if record.flags.hostile
                              else nonhostile_recs)
                target_set.add(record.eid)
                try:
                    target_set.add(unpack_eid(str_to_sig(record.eid))[0])
                except struct_error:
                    raise ModError(None, f'Failed to unpack EDID for '
                                         f'{record!r}')
                m_names[record.eid] = record.full or u'' # could this be None?
        self.cached_mgef_school = m_school
        self.cached_mgef_hostiles = m_hostiles - nonhostile_recs | hostile_recs
        self.cached_mgef_names = m_names

    def getMgefSchool(self):
        """Return a dictionary mapping magic effect code to magic effect
        school. This is intended for use with the patch file when it records
        for all magic effects. If magic effects are not available, it will
        revert to constants.py version."""
        try:
            # Try to just return the cached version
            return self.cached_mgef_school
        except AttributeError:
            self._index_mgefs()
            return self.cached_mgef_school

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

# TODO(inf) Use this for a bunch of stuff in mods_metadata.py (e.g. UDRs)
class ModHeaderReader(object):
    """Allows very fast reading of a plugin's headers, skipping reading and
    decoding of anything but the headers."""
    @staticmethod
    def formids_in_esl_range(mod_info):
        """Checks if all FormIDs in the specified mod are in the ESL range."""
        num_masters = len(mod_info.masterNames)
        with ModReader(mod_info.ci_key, mod_info.abs_path.open(u'rb')) as ins:
            ins_at_end = ins.atEnd
            ins_unpack_rec_header = ins.unpackRecHeader
            try:
                while not ins_at_end():
                    header = ins_unpack_rec_header()
                    # Skip GRUPs themselves, only process their records
                    header_rec_sig = header.recType
                    if header_rec_sig != b'GRUP':
                        header_fid = header.fid
                        if (header_fid >> 24 >= num_masters and
                                (header_fid & 0xFFFFFF) > 0xFFF):
                            return False # FormID out of range
                        header.skip_blob(ins)
            except (OSError, struct_error) as e:
                raise ModError(ins.inName, u'Error scanning %s, file read '
                    u"pos: %i\nCaused by: '%r'" % (mod_info, ins.tell(), e))
        return True

    @staticmethod
    def extract_mod_data(mod_info, progress, skip_tes4=True,
                         __unpacker=structs_cache[u'I'].unpack):
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
        minf_ci_key = mod_info.ci_key
        sh_unpack = Subrecord.sub_header_unpack
        sh_size = Subrecord.sub_header_size
        main_progress_msg = _(u'Loading: %s') % minf_ci_key
        # Where we'll store all the collected record data
        group_records = defaultdict(lambda: defaultdict(tuple))
        # The current top GRUP label - starts out as TES4/TES3
        tg_label = bush.game.Esp.plugin_header_sig
        # The dict we'll use to store records from the current top GRUP
        records = group_records[tg_label]
        ##: Uncomment these variables and the block below that uses them once
        # all of FO4's record classes have been written
        # The record types that can even contain EDIDs
        #records_with_eids = MreRecord.subrec_sig_to_record_sig[b'EDID']
        # Whether or not we can skip looking for EDIDs for  the current record
        # type because it doesn't even have any
        #skip_eids = tg_label not in records_with_eids
        with mod_info.abs_path.open(u'rb') as ins:
            initial_bytes = ins.read()
        with FastModReader(minf_ci_key, initial_bytes) as ins:
            # More local methods to avoid repeated dot access
            ins_tell = ins.tell
            ins_seek = ins.seek
            ins_read = ins.read
            ins_size = ins.size
            while ins_tell() != ins_size:
                # Unpack the headers - these can be either GRUPs or regular
                # records
                header = unpack_header(ins)
                _rsig = header.recType
                if _rsig == b'GRUP':
                    # Nothing special to do for non-top GRUPs
                    if not header.is_top_group_header: continue
                    tg_label = header.label
                    progress(ins_tell() / minf_size,
                             f'{main_progress_msg}\n{sig_to_str(tg_label)}')
                    records = group_records[tg_label]
                #     skip_eids = tg_label not in records_with_eids
                # elif skip_eids:
                #     # This record type has no EDIDs, skip directly to the next
                #     # record (can't use skip_blob because that passes
                #     # debug_strs to seek()...)
                #     records[header.fid] = (header, u'')
                #     ins_seek(ins_tell() + header.blob_size())
                else:
                    # This is a regular record, look for the EDID subrecord
                    eid = u''
                    blob_siz = header.blob_size()
                    next_record = ins_tell() + blob_siz
                    if header.flags1 & 0x00040000: # 'compressed' flag
                        size_check = __unpacker(ins_read(4))[0]
                        try:
                            new_rec_data = zlib_decompress(ins_read(
                                blob_siz - 4))
                        except zlib_error:
                            if minf_ci_key == u'FalloutNV.esm':
                                # Yep, FalloutNV.esm has a record with broken
                                # zlib data. Just skip it.
                                ins_seek(next_record)
                                continue
                            raise
                        if len(new_rec_data) != size_check:
                            raise ModError(ins.inName,
                                u'Mis-sized compressed data. Expected %d, got '
                                u'%d.' % (blob_siz, len(new_rec_data)))
                    else:
                        new_rec_data = ins_read(blob_siz)
                    recs = FastModReader(minf_ci_key, new_rec_data)
                    recs_seek = recs.seek
                    recs_read = recs.read
                    recs_tell = recs.tell
                    recs_size = recs.size
                    recs_unpack = recs.unpack
                    while recs_tell() != recs_size:
                        # Inlined from unpackSubHeader & FastModReader.unpack
                        read_data = recs_read(sh_size)
                        if len(read_data) != sh_size:
                            raise ModReadError(
                                minf_ci_key, [_rsig, u'SUB_HEAD'],
                                recs_tell() - len(read_data), recs_size)
                        mel_sig, mel_size = sh_unpack(read_data)
                        # Extended storage - very rare, so don't optimize
                        # inlines etc. for it
                        if mel_sig == b'XXXX':
                            # Throw away size here (always == 0)
                            mel_size = recs_unpack(__unpacker, 4, _rsig,
                                                   u'XXXX.SIZE')[0]
                            mel_sig = recs_unpack(sh_unpack, sh_size,
                                                  _rsig, u'XXXX.TYPE')[0]
                        if mel_sig == b'EDID':
                            # No need to worry about newlines, these are Editor
                            # IDs and so won't contain any
                            eid = decoder(recs_read(mel_size).rstrip(null1),
                                          wanted_encoding, avoided_encodings)
                            break
                        else:
                            recs_seek(mel_size, 1)
                    records[header.fid] = (header, eid)
                    ins_seek(next_record) # we may have break'd at EDID
        if skip_tes4:
            del group_records[bush.game.Esp.plugin_header_sig]
        return group_records

    ##: The methods above have to be very fast, but this one can afford to be
    # much slower. Should eventually be absorbed by refactored ModFile API.
    @staticmethod
    def read_temp_child_headers(mod_info):
        """Reads the headers of all temporary CELL chilren in the specified mod
        and returns them as a list. Used for determining FO3/FNV/TES5 ONAM.

        :rtype: list[RecordHeader]"""
        ret_headers = []
        # We want to read only the children of these, so skip their tops
        interested_sigs = {b'CELL', b'WRLD'}
        tops_to_skip = interested_sigs | {bush.game.Esp.plugin_header_sig}
        with ModReader(mod_info.ci_key, mod_info.abs_path.open(u'rb')) as ins:
            ins_at_end = ins.atEnd
            ins_unpack_rec_header = ins.unpackRecHeader
            try:
                while not ins_at_end():
                    header = ins_unpack_rec_header()
                    header_rec_sig = header.recType
                    if header_rec_sig == b'GRUP':
                        header_group_type = header.groupType
                        # Skip all top-level GRUPs we're not interested in
                        # (group type == 0) and all persistent children and
                        # dialog topics (group type == 7 or 8, respectively).
                        if ((header.is_top_group_header and
                             header.label not in interested_sigs)
                                or header_group_type in (7, 8)):
                            # Note that GRUP sizes include their own header
                            # size, so we need to subtract that
                            header.skip_blob(ins)
                    elif header_rec_sig in tops_to_skip:
                        # Skip TES4, CELL and WRLD to get to their contents
                        header.skip_blob(ins)
                    else:
                        # We must be in a temp CELL children group, store the
                        # header and skip the record body
                        ret_headers.append(header)
                        header.skip_blob(ins)
            except (OSError, struct_error) as e:
                raise ModError(ins.inName, u'Error scanning %s, file read '
                    u"pos: %i\nCaused by: '%r'" % (mod_info, ins.tell(), e))
        return ret_headers
