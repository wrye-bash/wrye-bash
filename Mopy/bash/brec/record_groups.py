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
"""Houses classes for reading, manipulating and writing groups of records."""

# Python imports
import io
from collections import deque
from itertools import chain
from operator import itemgetter, attrgetter

# Wrye Bash imports
from .mod_io import GrupHeader, ModReader, RecordHeader, TopGrupHeader
from .utils_constants import group_types, fid_key
from ..bolt import pack_int, structs_cache, attrgetter_cache, sig_to_str
from ..exception import AbstractError, ModError, ModFidMismatchError

class MobBase(object):
    """Group of records and/or subgroups. This basic implementation does not
    support unpacking, but can report its number of records and be written."""

    __slots__ = [u'header',u'size',u'label',u'groupType', u'stamp', u'debug',
                 u'data', u'changed', u'numRecords', u'loadFactory',
                 u'inName'] ##: nice collection of forbidden names, including header -> group_header

    def __init__(self, header, loadFactory, ins=None, do_unpack=False):
        self.header = header
        self.size = header.size
        if header.recType == b'GRUP':
            self.label, self.groupType, self.stamp = (
                header.label, header.groupType, header.stamp)
        else: # TODO(ut) should MobBase used for *non* GRUP headers??
            # Yes it's weird, but this is how it needs to work
            self.label, self.groupType, self.stamp = (
                header.flags1, header.fid, header.flags2)
        # binary blob of the whole record group minus its GRUP header ##: rename
        self.data = None
        self.changed = False
        self.numRecords = -1
        self.loadFactory = loadFactory
        self.inName = ins and ins.inName
        if ins: self.load_rec_group(ins, do_unpack)

    def load_rec_group(self, ins=None, do_unpack=False):
        """Load data from ins stream or internal data buffer."""
        #--Read, but don't analyze.
        if not do_unpack:
            self.data = ins.read(self.header.blob_size(), type(self).__name__)
        #--Analyze ins.
        elif ins is not None:
            self._load_rec_group(ins, ins.tell() + self.header.blob_size())
        #--Analyze internal buffer.
        else:
            with self.getReader() as reader:
                self._load_rec_group(reader, reader.size)
        #--Discard raw data?
        if do_unpack:
            self.data = None
            self.setChanged()

    def setChanged(self,value=True):
        """Sets changed attribute to value. [Default = True.]"""
        self.changed = value

    def getSize(self):
        """Returns size (including size of any group headers)."""
        if self.changed: raise AbstractError
        return self.size

    def getNumRecords(self,includeGroups=True):
        """Returns number of records, including self (if plusSelf), unless
        there's no subrecords, in which case, it returns 0."""
        if self.changed:
            raise AbstractError
        elif self.numRecords > -1: #--Cached value.
            return self.numRecords
        elif not self.data: #--No data >> no records, not even self.
            self.numRecords = 0
            return self.numRecords
        else:
            numSubRecords = 0
            num_groups = 1 # the top level grup itself - not included in data
            reader = self.getReader()
            errLabel = group_types[self.groupType]
            readerAtEnd = reader.atEnd
            readerRecHeader = reader.unpackRecHeader
            while not readerAtEnd(reader.size, errLabel):
                header = readerRecHeader()
                if header.recType != b'GRUP':
                    header.skip_blob(reader)
                    numSubRecords += 1
                else: num_groups += 1
            self.numRecords = numSubRecords + includeGroups * num_groups
            return self.numRecords

    def dump(self,out):
        """Dumps record header and data into output file stream."""
        if self.changed:
            raise AbstractError
        if self.numRecords == -1:
            self.getNumRecords()
        if self.numRecords > 0: ##: trivially True for MobBase with includeGroups=True
            self.header.size = self.size
            out.write(self.header.pack_head())
            out.write(self.data)

    def getReader(self):
        """Returns a ModReader wrapped around self.data."""
        return ModReader(self.inName, io.BytesIO(self.data))

    def iter_present_records(self, include_ignored=False, rec_key=u'fid',
                             __attrgetters=attrgetter_cache):
        """Filters iter_records, returning only records that have not set
        the deleted flag and/or the ignore flag if include_ignored is False."""
        return ((__attrgetters[rec_key](r), r) for r in self.iter_records()
                if not r.flags1.deleted
                and (include_ignored or not r.flags1.ignored))

    # Abstract methods --------------------------------------------------------
    def get_all_signatures(self):
        """Returns a set of all signatures contained in this block."""
        raise AbstractError(u'get_all_signatures not implemented')

    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if
        converting to short format. Base implementation does nothing as its
        records are not unpacked."""

    def indexRecords(self):
        """Indexes records by fid."""
        raise AbstractError(u'indexRecords not implemented')

    def iter_records(self):
        """Flattens the structure of this record block into a linear sequence
        of records. Works as an iterator for memory reasons."""
        raise AbstractError(u'iter_records not implemented')

    def keepRecords(self, p_keep_ids):
        """Keeps records with fid in set p_keep_ids. Discards the rest."""
        raise AbstractError(u'keepRecords not implemented')

    def _load_rec_group(self, ins, endPos):
        """Loads data from input stream. Called by load_rec_group()."""
        raise AbstractError(u'_load_rec_group not implemented')

    ##: params here are not the prettiest
    def merge_records(self, block, loadSet, mergeIds, iiSkipMerge, doFilter):
        """Merges records from the specified block into this block and performs
        merge filtering if doFilter is True.

        :param block: The block to merge records from.
        :param loadSet: The set of currently loaded plugins.
        :param mergeIds: A set into which the fids of all records that will be
            merged by this operation will be added.
        :param iiSkipMerge: If True, skip merging and only perform merge
            filtering. Used by IIM mode.
        :param doFilter: If True, perform merge filtering."""
        from ..bolt import deprint
        deprint(u'merge_records missing for %s' % self.label)
        raise AbstractError(u'merge_records not implemented')

    def _sort_group(self):
        """Performs any sorting of records that has to be done in this record
        group."""
        raise AbstractError(u'_sort_group not implemented')

    def updateMasters(self, masterset_add):
        """Updates set of master names according to masters actually used."""
        raise AbstractError(u'updateMasters not implemented')

    def updateRecords(self, srcBlock, mergeIds):
        """Looks through all of the records in 'block', and updates any
        records in self that exist with the data in 'block'. 'block' must be in
        long fids format."""
        raise AbstractError(u'updateRecords not implemented')

#------------------------------------------------------------------------------
class MobObjects(MobBase):
    """Represents a top level group consisting of one type of record only. I.e.
    all top groups except CELL, WRLD and DIAL."""

    def __init__(self, header, loadFactory, ins=None, do_unpack=False):
        self.records = []
        self.id_records = {}
        from .. import bush
        self._null_fid = (bush.game.master_file, 0)
        # DarkPCB record
        self._bad_form = bush.game.displayName == u'Oblivion' and (
            bush.game.master_file, 0xA31D) or None
        super(MobObjects, self).__init__(header, loadFactory, ins, do_unpack)

    def get_all_signatures(self):
        return {self.label}

    def _load_rec_group(self, ins, endPos):
        """Loads data from input stream. Called by load()."""
        expType = self.label
        recClass = self.loadFactory.getRecClass(expType)
        insAtEnd = ins.atEnd
        insRecHeader = ins.unpackRecHeader
        recordsAppend = self.records.append
        errLabel = f'{(exp_str := sig_to_str(expType))} Top Block'
        while not insAtEnd(endPos,errLabel):
            #--Get record info and handle it
            header = insRecHeader()
            if header.recType != expType:
                header_str = sig_to_str(header.recType)
                msg = f'Unexpected {header_str} record in {exp_str} group.'
                raise ModError(ins.inName, msg)
            recordsAppend(recClass(header, ins, True))
        self.setChanged()

    def getActiveRecords(self):
        """Returns non-ignored records."""
        return [record for record in self.records if not record.flags1.ignored]

    def getNumRecords(self,includeGroups=True):
        """Returns number of records, including self - if empty return 0."""
        numRecords = len(self.records)
        if numRecords: numRecords += includeGroups #--Count self
        self.numRecords = numRecords
        return numRecords

    def getSize(self):
        """Returns size (including size of any group headers)."""
        if not self.changed:
            return self.size
        else:
            hsize = RecordHeader.rec_header_size
            return hsize + sum(
                (hsize + record.getSize()) for record in self.records)

    def dump(self,out):
        """Dumps group header and then records."""
        if not self.changed:
            out.write(TopGrupHeader(self.size, self.label,
                                    ##: self.header.pack_head() ?
                                    self.stamp).pack_head())
            out.write(self.data)
        else:
            size = self.getSize()
            if size == RecordHeader.rec_header_size: return
            out.write(TopGrupHeader(size, self.label, self.stamp).pack_head())
            self._sort_group()
            for record in self.records:
                record.dump(out)

    def _sort_group(self):
        """Sorts records by FormID."""
        self.records.sort(key=fid_key)

    def updateMasters(self, masterset_add):
        """Updates set of master names according to masters actually used."""
        for record in self.records:
            record.updateMasters(masterset_add)

    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if
        converting to short format."""
        for record in self.records:
            record.convertFids(mapper,toLong)
        self.id_records.clear()

    def indexRecords(self):
        """Indexes records by fid."""
        self.id_records.clear()
        for record in self.records:
            self.id_records[record.fid] = record

    def getRecord(self, rec_fid):
        """Gets record with corresponding id.
        If record doesn't exist, returns None."""
        if not self.records: return None
        if not self.id_records: self.indexRecords()
        return self.id_records.get(rec_fid, None)

    def setRecord(self,record):
        """Adds record to record list and indexed."""
        self_recs = self.records
        if self_recs and not self.id_records:
            self.indexRecords()
        record_id = record.fid
        if record.isKeyedByEid and record_id == self._null_fid:
            record_id = record.eid
        self_id_recs = self.id_records
        # This check fails fairly often, so do this instead of try/except
        if record_id in self_id_recs:
            ##: Building a fid -> index mapping in indexRecords could make this
            # O(1) instead of O(n) - see if that's worth it (memory!)
            self_recs[self_recs.index(
                self_id_recs[record_id])] = record
        else:
            self_recs.append(record)
        self_id_recs[record_id] = record

    def copy_records(self, records):
        """Copies the specified records into this block, overwriting existing
        records. Note that the records *must* already be in long fid format!
        If condition_func is given, it will be called on each record to decide
        whether or not to copy it.

        :type records: list[brec.MreRecord]"""
        copy_record = self.setRecord
        for record in records:
            copy_record(record.getTypeCopy())

    def keepRecords(self, p_keep_ids):
        """Keeps records with fid in set p_keep_ids. Discards the rest."""
        self.records = [record for record in self.records if (
                record.isKeyedByEid and record.fid == self._null_fid
                and record.eid in p_keep_ids) or record.fid in p_keep_ids]
        self.id_records.clear()
        self.setChanged()

    def updateRecords(self, srcBlock, mergeIds):
        if self.records and not self.id_records:
            self.indexRecords()
        merge_ids_discard = mergeIds.discard
        copy_to_self = self.setRecord
        dest_rec_fids = self.id_records
        for record in srcBlock.getActiveRecords():
            src_rec_fid = record.fid
            if src_rec_fid in dest_rec_fids:
                copy_to_self(record.getTypeCopy())
                merge_ids_discard(src_rec_fid)

    def merge_records(self, block, loadSet, mergeIds, iiSkipMerge, doFilter):
        # YUCK, drop these local imports!
        from ..mod_files import MasterSet
        filtered = []
        filteredAppend = filtered.append
        loadSetIsSuperset = loadSet.issuperset
        mergeIdsAdd = mergeIds.add
        copy_to_self = self.setRecord
        for record in block.getActiveRecords():
            fid = record.fid
            if fid == self._bad_form: continue
            #--Include this record?
            if doFilter:
                # If we're Filter-tagged, perform merge filtering. Then, check
                # if the record has any FormIDs with masters that are on disk
                # left. If it does not, skip the whole record (because all of
                # its contents have been merge-filtered out).
                record.mergeFilter(loadSet)
                masterset = MasterSet()
                record.updateMasters(masterset.add)
                if not loadSetIsSuperset(masterset):
                    continue
            # We're either not Filter-tagged or we want to keep this record
            filteredAppend(record)
            # If we're IIM-tagged and this is not one of the IIM-approved
            # record types, skip merging
            if iiSkipMerge: continue
            # We're past all hurdles - stick a copy of this record into
            # ourselves and mark it as merged
            if record.isKeyedByEid and fid == self._null_fid:
                mergeIdsAdd(record.eid)
            else:
                mergeIdsAdd(fid)
            copy_to_self(record.getTypeCopy())
        # Apply any merge filtering we've done above to the record block in
        # question. That way, patchers won't see the records that have been
        # filtered out here.
        block.records = filtered
        block.indexRecords()

    def iter_records(self):
        return iter(self.records)

    def __repr__(self):
        return (f'<{sig_to_str(self.label)} GRUP: {len(self.records)} '
                f'record(s)>')

#------------------------------------------------------------------------------
##: MobDial, MobCell and MobWorld need a base class; same with MobDials,
# MobCells and MobWorlds
class MobDial(MobObjects):
    """A single DIAL with INFO children."""
    __slots__ = [u'dial', u'stamp2']

    def __init__(self, header, loadFactory, dial, ins=None, do_unpack=True):
        self.dial = dial
        self.stamp2 = 0
        super(MobDial, self).__init__(header, loadFactory, ins, do_unpack)

    def _load_rec_group(self, ins, endPos):
        info_class = self.loadFactory.getRecClass(b'INFO')
        if not info_class:
            self.header.skip_blob(ins) # DIAL already read, skip all INFOs
        read_header = ins.unpackRecHeader
        ins_at_end = ins.atEnd
        append_info = self.records.append
        while not ins_at_end(endPos, u'DIAL Block'):
            header = read_header()
            if header.recType == b'INFO':
                append_info(info_class(header, ins, True))
            elif header.recType == b'DIAL':
                raise ModError(ins.inName, u'Duplicate DIAL record (%r) '
                                           u'inside DIAL block (a header size '
                                           u'is likely incorrect).' % header)
            else:
                raise ModError(ins.inName,
                    u'Unexpected %r in DIAL group.' % header)
        self.setChanged()

    def getSize(self):
        hsize = RecordHeader.rec_header_size
        size = hsize + self.dial.getSize()
        if self.records:
            # First hsize is for the single GRUP header before the INFOs
            size += hsize + sum(hsize + i.getSize() for i in self.records)
        return size

    def getNumRecords(self,includeGroups=True):
        # DIAL record + GRUP + INFOs
        self.numRecords = 1 + (includeGroups + len(self.records)
                               if self.records else 0)
        return self.numRecords

    def dump(self, out):
        # Update TIFC if needed (i.e. Skyrim+)
        if hasattr(self.dial, u'info_count'):
            self.dial.info_count = len(self.records)
        self.dial.getSize()
        self.dial.dump(out)
        if not self.changed:
            out.write(self.header.pack_head())
            out.write(self.data)
        else:
            if not self.records: return
            # Now we're ready to dump out the headers and each INFO child
            hsize = RecordHeader.rec_header_size
            infos_size = hsize + sum(hsize + i.getSize() for i in self.records)
            # Write out a GRUP header (needed in order to know the number of
            # bytes to read for all the INFOs), then dump all the INFOs
            out.write(GrupHeader(infos_size, self.dial.fid, 7, self.stamp,
                self.stamp2).pack_head())
            self._sort_group()
            for info in self.records:
                info.dump(out)

    def get_all_signatures(self):
        return {self.dial._rec_sig} | {i._rec_sig for i in self.records}

    def convertFids(self, mapper, toLong):
        self.dial.convertFids(mapper, toLong)
        super(MobDial, self).convertFids(mapper, toLong)

    def iter_records(self):
        return chain([self.dial], self.records)

    def keepRecords(self, p_keep_ids):
        self.records = [i for i in self.records if i.fid in p_keep_ids]
        if self.records:
            p_keep_ids.add(self.dial.fid) # must keep parent around
        if self.dial.fid not in p_keep_ids:
            self.dial = None # will drop us from MobDials
        self.id_records.clear()
        self.setChanged()

    def merge_records(self, block, loadSet, mergeIds, iiSkipMerge, doFilter):
        from ..mod_files import MasterSet # YUCK
        mergeIdsAdd = mergeIds.add
        loadSetIsSuperset = loadSet.issuperset
        # First, check the main DIAL record
        src_dial = block.dial
        src_dial_fid = src_dial.fid
        if self.dial.fid != src_dial_fid:
            raise ModFidMismatchError(self.inName, u'DIAL', self.dial.fid,
                src_dial_fid)
        if not src_dial.flags1.ignored:
            # If we're Filter-tagged, perform merge filtering first
            if doFilter:
                src_dial.mergeFilter(loadSet)
                masterset = MasterSet()
                src_dial.updateMasters(masterset.add)
                if not loadSetIsSuperset(masterset):
                    # Filtered out, discard this DIAL record (and, by
                    # extension, all its INFO children)
                    self.dial = None # will drop us from MobDials
                    return
            # In IIM, we can't just return here since we also need to filter
            # the INFO children that came with this DIAL record
            if not iiSkipMerge:
                # We're past all hurdles - mark the record as merged, and stick
                # a copy into ourselves
                mergeIdsAdd(src_dial_fid)
                self.dial = src_dial.getTypeCopy()
            # Now we're ready to filter and merge the INFO children
            super(MobDial, self).merge_records(block, loadSet, mergeIds,
                iiSkipMerge, doFilter)

    def updateMasters(self, masterset_add):
        if self.dial: # May have gotten set to None through merge filtering
            self.dial.updateMasters(masterset_add)
        super(MobDial, self).updateMasters(masterset_add)

    def updateRecords(self, srcBlock, mergeIds):
        src_dial = srcBlock.dial
        src_dial_fid = src_dial.fid
        if self.dial.fid != src_dial_fid:
            raise ModFidMismatchError(self.inName, u'DIAL', self.dial.fid,
                src_dial_fid)
        # Copy the latest version of the DIAL record over. We can safely mark
        # it as not merged because keepRecords above ensures that we never
        # discard a DIAL when it still has INFO children
        if not src_dial.flags1.ignored:
            self.dial = src_dial.getTypeCopy()
            mergeIds.discard(src_dial_fid)
        super(MobDial, self).updateRecords(srcBlock, mergeIds)

    def _sort_group(self):
        """Sorts the INFOs of this DIAL record by their (PNAM) Previous Info.
        These do not simply describe a linear list, but a directed graph - e.g.
        you can have edges B->A and C->A, which would leave both C->B->A and
        B->C->A as valid orders. To decide in such cases, we stick with
        whatever the previous order was.

        Note: We assume the PNAM graph is acyclic - cyclic graphs are errors
        in plugins anyways, so the behavior of PBash when encountering such
        errors is undefined."""
        # First gather a list of all 'orphans', i.e. INFOs that have no PNAM.
        # We'll start with these and insert non-orphans into the list at the
        # right spot based on their PNAM
        sorted_infos = []
        remaining_infos = deque()
        for r in self.records:
            if not r.prev_info:
                sorted_infos.append(r)
            else:
                remaining_infos.append(r)
        visited_fids = set()
        while remaining_infos:
            # Pop from the right to maintain the original sort order when
            # inserting multiple INFOs with the same PNAM
            curr_info = remaining_infos.pop()
            wanted_prev_fid = curr_info.prev_info
            # Look if a record matching the PNAM has already been inserted
            for i, prev_candidate in enumerate(sorted_infos):
                if prev_candidate.fid == wanted_prev_fid:
                    # It has, so just insert our INFO after it
                    sorted_infos.insert(i + 1, curr_info)
                    break
            else:
                # Not in the sorted INFOs, check for a cycle/unknown record
                if curr_info.fid in visited_fids:
                    # Either the PNAM points to a record that's not in our
                    # file (which is fine and happens all the time), or this
                    # INFO is in a cycle, or the PNAM points to a non-existent
                    # record.
                    # To handle this situation, we simply append it to the end
                    # of our sorted INFOs.
                    # We don't warn here because trying to differentiate the
                    # valid and common case from the two error cases would be
                    # too slow. xEdit can do this much better.
                    sorted_infos.append(curr_info)
                else:
                    # We'll have to revisit this INFO later when its PNAM may
                    # have been added, so move it to the end (== left side) of
                    # the queue
                    visited_fids.add(curr_info.fid)
                    remaining_infos.appendleft(curr_info)
        self.records = sorted_infos

    def __repr__(self):
        return f'<DIAL ({self.dial!r}): {len(self.records)} INFO record(s)>'

class MobDials(MobBase):
    """DIAL top block of mod file."""
    def __init__(self, header, loadFactory, ins=None, do_unpack=True):
        self.dialogues = []
        self.id_dialogues = {}
        super(MobDials, self).__init__(header, loadFactory, ins, do_unpack)

    def _load_rec_group(self, ins, endPos):
        """Loads data from input stream. Called by load()."""
        dial_class = self.loadFactory.getRecClass(b'DIAL')
        ins_seek = ins.seek
        if not dial_class: ins_seek(endPos) # skip the whole group
        expType = self.label
        insAtEnd = ins.atEnd
        insRecHeader = ins.unpackRecHeader
        append_dialogue = self.dialogues.append
        loadFactory = self.loadFactory
        while not insAtEnd(endPos,
                           errLabel := f'{sig_to_str(expType)} Top Block'):
            #--Get record info and handle it
            dial_header = insRecHeader()
            if dial_header.recType == expType:
                # Read the full DIAL record now
                dial = dial_class(dial_header, ins, True)
                if insAtEnd(endPos, errLabel):
                    # We've hit the end of the block, finish off this DIAL
                    self.set_dialogue(dial)
                else:
                    # Otherwise, we need to investigate the next header
                    next_header = insRecHeader()
                    if (next_header.recType == b'GRUP' and
                            next_header.groupType == 7):
                        # This is a regular DIAL record with children
                        append_dialogue(MobDial(next_header, loadFactory, dial,
                            ins, do_unpack=True))
                    elif next_header.recType == expType:
                        # This is a DIAL record without children. Finish this
                        # one, then rewind and process next_header normally
                        self.set_dialogue(dial)
                        ins_seek(-RecordHeader.rec_header_size, 1)
                    else:
                        raise ModError(ins.inName,
                                       f'Unexpected {next_header!r} in '
                                       f'{sig_to_str(expType)} block.')
            else:
                raise ModError(ins.inName,
                               f'Unexpected {dial_header!r} in '
                               f'{sig_to_str(expType)} top block.')
        self.id_dialogues.clear()
        self.setChanged()

    def getSize(self):
        """Returns size of records plus group and record headers."""
        size = RecordHeader.rec_header_size
        for dialogue in self.dialogues:
            # Resynchronize the stamps (##: unsure if needed)
            dialogue.stamp = self.stamp
            size += dialogue.getSize()
        return size

    def getNumRecords(self,includeGroups=True):
        """Returns number of records, including self plus info records."""
        self.numRecords = sum(d.getNumRecords(includeGroups)
                              for d in self.dialogues)
        self.numRecords += includeGroups # top DIAL GRUP
        return self.numRecords

    def dump(self, out):
        if not self.changed:
            out.write(self.header.pack_head())
            out.write(self.data)
        else:
            dial_size = self.getSize()
            if dial_size == RecordHeader.rec_header_size: return
            out.write(TopGrupHeader(dial_size, self.label,
                                    self.stamp).pack_head())
            self._sort_group()
            for dialogue in self.dialogues:
                dialogue.dump(out)

    def convertFids(self, mapper, toLong):
        for dialogue in self.dialogues:
            dialogue.convertFids(mapper, toLong)

    def get_all_signatures(self):
        return set(chain.from_iterable(d.get_all_signatures()
                                       for d in self.dialogues))

    def indexRecords(self):
        self.id_dialogues = {d.dial.fid: d for d in self.dialogues}

    def iter_records(self):
        return chain.from_iterable(d.iter_records() for d in self.dialogues)

    def keepRecords(self, p_keep_ids):
        for dialogue in self.dialogues:
            dialogue.keepRecords(p_keep_ids)
        self.dialogues = [d for d in self.dialogues if d.dial]
        self.id_dialogues.clear()
        self.setChanged()

    def merge_records(self, block, loadSet, mergeIds, iiSkipMerge, doFilter):
        from ..mod_files import MasterSet # YUCK
        if self.dialogues and not self.id_dialogues:
            self.indexRecords()
        lookup_dial = self.id_dialogues.get
        filtered_dials = []
        filtered_append = filtered_dials.append
        loadSetIsSuperset = loadSet.issuperset
        for src_dialogue in block.dialogues:
            was_newly_added = False
            src_fid = src_dialogue.dial.fid
            # Check if we already have a dialogue with that FormID
            dest_dialogue = lookup_dial(src_fid)
            if not dest_dialogue:
                # We do not, add it and then look up again
                self.set_dialogue(src_dialogue.dial.getTypeCopy())
                dest_dialogue = lookup_dial(src_fid)
                was_newly_added = True
            # Delegate merging to the (potentially newly added) child dialogue
            dest_dialogue.merge_records(src_dialogue, loadSet, mergeIds,
                iiSkipMerge, doFilter)
            # In IIM, skip all merging - note that we need to remove the child
            # dialogue again if it was newly added in IIM mode.
            if iiSkipMerge:
                if was_newly_added:
                    self.remove_dialogue(dest_dialogue.dial)
                continue
            # If we're Filter-tagged, check if the dialogue got filtered out
            if doFilter:
                masterset = MasterSet()
                src_dialogue.updateMasters(masterset.add)
                if not loadSetIsSuperset(masterset):
                    # The child dialogue got filtered out. If it was newly
                    # added, we need to remove it from this block again.
                    # Otherwise, we can just skip forward to the next child.
                    if was_newly_added:
                        self.remove_dialogue(dest_dialogue.dial)
                    continue
            # We're either not Filter-tagged or we want to keep this dialogue
            filtered_append(src_dialogue)
        # Apply any merge filtering we've done above to the record block
        block.dialogues = filtered_dials
        block.indexRecords()

    def remove_dialogue(self, dialogue):
        """Removes the specified DIAL from this block. The exact DIAL object
        must be present, otherwise a ValueError is raised."""
        if self.dialogues and not self.id_dialogues:
            self.indexRecords()
        self.dialogues.remove(dialogue)
        del self.id_dialogues[dialogue.fid]

    def set_dialogue(self, dialogue):
        """Adds the specified DIAL to self, overriding an existing one with
        the same FormID or creating a new DIAL block."""
        if self.dialogues and not self.id_dialogues:
            self.indexRecords()
        dial_fid = dialogue.fid
        if dial_fid in self.id_dialogues:
            self.id_dialogues[dial_fid].dial = dialogue
        else:
            dial_block = MobDial(GrupHeader(0, 0, 7, self.stamp),
                self.loadFactory, dialogue)
            dial_block.setChanged()
            self.dialogues.append(dial_block)
            self.id_dialogues[dial_fid] = dial_block

    def _sort_group(self):
        """Sorts DIAL groups by the FormID of the DIAL record."""
        self.dialogues.sort(key=attrgetter_cache[u'dial.fid'])

    def updateMasters(self, masterset_add):
        for dialogue in self.dialogues:
            dialogue.updateMasters(masterset_add)

    def updateRecords(self, srcBlock, mergeIds):
        if self.dialogues and not self.id_dialogues:
            self.indexRecords()
        lookup_dial = self.id_dialogues.get
        for src_dial in srcBlock.dialogues:
            # Check if we have a corresponding DIAL record in the destination
            dest_dial = lookup_dial(src_dial.dial.fid)
            if dest_dial:
                dest_dial.updateRecords(src_dial, mergeIds)

    def __repr__(self):
        return f'<DIAL GRUP: {len(self.dialogues)} record(s)>'

#------------------------------------------------------------------------------
class MobCell(MobBase):
    """Represents cell block structure -- including the cell and all
    subrecords."""
    __slots__ = [u'cell', u'persistent_refs', u'distant_refs', u'temp_refs',
                 u'land', u'pgrd']

    def __init__(self, header, loadFactory, cell, ins=None, do_unpack=False):
        self.cell = cell
        self.persistent_refs = []
        self.distant_refs = []
        self.temp_refs = []
        self.land = None
        self.pgrd = None
        super(MobCell, self).__init__(header, loadFactory, ins, do_unpack)

    def _load_rec_group(self, ins, endPos):
        """Loads data from input stream. Called by load()."""
        cellType_class = self.loadFactory.getCellTypeClass()
        insAtEnd = ins.atEnd
        insRecHeader = ins.unpackRecHeader
        cellGet = cellType_class.get
        persistentAppend = self.persistent_refs.append
        tempAppend = self.temp_refs.append
        distantAppend = self.distant_refs.append
        subgroupLoaded = [False, False, False]
        groupType = None # guaranteed to compare False to any of them
        while not insAtEnd(endPos, u'Cell Block'):
            header = insRecHeader()
            _rsig = header.recType
            recClass = cellGet(_rsig)
            if _rsig == b'GRUP':
                groupType = header.groupType
                if groupType not in (8, 9, 10):
                    raise ModError(self.inName,
                                   f'Unexpected subgroup {groupType:d} in '
                                   f'cell children group.')
                if subgroupLoaded[groupType - 8]:
                    raise ModError(self.inName,
                                   f'Extra subgroup {groupType:d} in cell '
                                   f'children group.')
                else:
                    subgroupLoaded[groupType - 8] = True
            elif _rsig not in cellType_class:
                raise ModError(self.inName,
                               f'Unexpected {sig_to_str(_rsig)} record in '
                               f'cell children group.')
            elif not recClass:
                header.skip_blob(ins)
            elif _rsig in (b'REFR',b'ACHR',b'ACRE'):
                record = recClass(header,ins,True)
                if   groupType ==  8: persistentAppend(record)
                elif groupType ==  9: tempAppend(record)
                elif groupType == 10: distantAppend(record)
            elif _rsig == b'LAND':
                self.land = recClass(header, ins, True)
            elif _rsig == b'PGRD':
                self.pgrd = recClass(header, ins, True)
        self.setChanged()

    def getSize(self):
        """Returns size (including size of any group headers)."""
        return RecordHeader.rec_header_size + self.cell.getSize() + \
               self.getChildrenSize()

    def getChildrenSize(self):
        """Returns size of all children, including the group header.  This
        does not include the cell itself."""
        size = self.getPersistentSize() + self.getTempSize() + \
               self.getDistantSize()
        return size + RecordHeader.rec_header_size * bool(size)

    def getPersistentSize(self):
        """Returns size of all persistent children, including the persistent
        children group."""
        hsize = RecordHeader.rec_header_size
        size = sum(hsize + x.getSize() for x in self.persistent_refs)
        return size + hsize * bool(size)

    def getTempSize(self):
        """Returns size of all temporary children, including the temporary
        children group."""
        hsize = RecordHeader.rec_header_size
        size = sum(hsize + x.getSize() for x in self.temp_refs)
        if self.pgrd: size += hsize + self.pgrd.getSize()
        if self.land: size += hsize + self.land.getSize()
        return size + hsize * bool(size)

    def getDistantSize(self):
        """Returns size of all distant children, including the distant
        children group."""
        hsize = RecordHeader.rec_header_size
        size = sum(hsize + x.getSize() for x in self.distant_refs)
        return size + hsize * bool(size)

    def getNumRecords(self,includeGroups=True):
        """Returns number of records, including self and all children."""
        count = 1 # CELL record, always present
        if self.persistent_refs:
            count += len(self.persistent_refs) + includeGroups
        if self.temp_refs or self.pgrd or self.land:
            count += len(self.temp_refs) + includeGroups
            count += bool(self.pgrd) + bool(self.land)
        if self.distant_refs:
            count += len(self.distant_refs) + includeGroups
        if count != 1:
            # CELL GRUP only exists if the CELL has at least one child
            count += includeGroups
        return count

    def getBsb(self):
        """Returns tesfile block and sub-block indices for cells in this group.
        For interior cell, bsb is (blockNum,subBlockNum). For exterior cell,
        bsb is ((blockY,blockX),(subblockY,subblockX)). Needs short fids!"""
        cell = self.cell
        #--Interior cell
        if cell.flags.isInterior:
            baseFid = cell.fid & 0x00FFFFFF
            return baseFid % 10, baseFid % 100 // 10
        #--Exterior cell
        else:
            x, y = cell.posX, cell.posY
            if x is None: x = 0
            if y is None: y = 0
            return (y // 32, x // 32), (y // 8, x // 8)

    def dump(self,out):
        """Dumps group header and then records."""
        self.cell.getSize()
        self.cell.dump(out)
        childrenSize = self.getChildrenSize()
        if not childrenSize: return
        self._sort_group()
        self._write_group_header(out, childrenSize, 6)
        # The order is persistent -> temporary -> distant
        if self.persistent_refs:
            self._write_group_header(out, self.getPersistentSize(), 8)
            for record in self.persistent_refs:
                record.dump(out)
        if self.temp_refs or self.pgrd or self.land:
            self._write_group_header(out, self.getTempSize(), 9)
            # The order is LAND -> PGRD -> temporary references
            if self.land:
                self.land.dump(out)
            if self.pgrd:
                self.pgrd.dump(out)
            for record in self.temp_refs:
                record.dump(out)
        if self.distant_refs:
            self._write_group_header(out, self.getDistantSize(), 10)
            for record in self.distant_refs:
                record.dump(out)

    def _write_group_header(self, out, group_size, group_type):
        out.write(GrupHeader(group_size, self.cell.fid, group_type,
                             self.stamp).pack_head()) # FIXME was TESIV only - self.extra??

    #--Fid manipulation, record filtering ----------------------------------
    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if
        converting to short format."""
        self.cell.convertFids(mapper,toLong)
        for record in self.temp_refs:
            record.convertFids(mapper,toLong)
        for record in self.persistent_refs:
            record.convertFids(mapper,toLong)
        for record in self.distant_refs:
            record.convertFids(mapper,toLong)
        if self.land:
            self.land.convertFids(mapper,toLong)
        if self.pgrd:
            self.pgrd.convertFids(mapper,toLong)

    def get_all_signatures(self):
        cell_sigs = {self.cell._rec_sig}
        cell_sigs.update(r._rec_sig for r in self.temp_refs)
        cell_sigs.update(r._rec_sig for r in self.persistent_refs)
        cell_sigs.update(r._rec_sig for r in self.distant_refs)
        if self.land: cell_sigs.add(self.land._rec_sig)
        if self.pgrd: cell_sigs.add(self.pgrd._rec_sig)
        return cell_sigs

    def _sort_group(self):
        """Sort temporary/persistent/distant references by FormID."""
        self.persistent_refs.sort(key=fid_key)
        self.temp_refs.sort(key=fid_key)
        self.distant_refs.sort(key=fid_key)

    def updateMasters(self, masterset_add):
        """Updates set of master names according to masters actually used."""
        self.cell.updateMasters(masterset_add)
        for record in chain(self.persistent_refs, self.distant_refs,
                self.temp_refs):
            record.updateMasters(masterset_add)
        if self.land:
            self.land.updateMasters(masterset_add)
        if self.pgrd:
            self.pgrd.updateMasters(masterset_add)

    def updateRecords(self, srcBlock, mergeIds, __attrget=attrgetter(
        u'cell', u'pgrd', u'land', u'persistent_refs', u'temp_refs',
        u'distant_refs')):
        """Updates any records in 'self' that exist in 'srcBlock'."""
        mergeDiscard = mergeIds.discard
        self_src_attrs = list(zip(__attrget(self), __attrget(srcBlock)))
        for attr, (myRecord, record) in zip((u'cell', u'pgrd', u'land'),
                                             self_src_attrs):
            if myRecord and record:
                src_rec_fid = record.fid
                if myRecord.fid != src_rec_fid:
                    raise ModFidMismatchError(self.inName, myRecord.rec_str,
                                              myRecord.fid, src_rec_fid)
                if not record.flags1.ignored:
                    record = record.getTypeCopy()
                    setattr(self, attr, record)
                    mergeDiscard(src_rec_fid)
        for attr, (self_rec_list, src_rec_list) in zip(
                (u'persistent_refs', u'temp_refs', u'distant_refs'),
                self_src_attrs[3:]):
            fids = {record.fid: i for i, record in enumerate(self_rec_list)}
            for record in src_rec_list:
                src_fid = record.fid
                if not record.flags1.ignored and src_fid in fids:
                    self_rec_list[fids[src_fid]] = record.getTypeCopy()
                    mergeDiscard(src_fid)

    def iter_records(self):
        single_recs = [x for x in (self.cell, self.pgrd, self.land) if x]
        return chain(single_recs, self.persistent_refs, self.distant_refs,
            self.temp_refs)

    def keepRecords(self, p_keep_ids):
        """Keeps records with fid in set p_keep_ids. Discards the rest."""
        if self.pgrd and self.pgrd.fid not in p_keep_ids:
            self.pgrd = None
        if self.land and self.land.fid not in p_keep_ids:
            self.land = None
        self.temp_refs = [x for x in self.temp_refs if x.fid in p_keep_ids]
        self.persistent_refs = [x for x in self.persistent_refs
                                if x.fid in p_keep_ids]
        self.distant_refs = [x for x in self.distant_refs
                             if x.fid in p_keep_ids]
        if (self.pgrd or self.land or self.persistent_refs or self.temp_refs or
                self.distant_refs):
            p_keep_ids.add(self.cell.fid)
        self.setChanged()

    def merge_records(self, block, loadSet, mergeIds, iiSkipMerge, doFilter):
        from ..mod_files import MasterSet # YUCK
        loadSetIsSuperset = loadSet.issuperset
        mergeIdsAdd = mergeIds.add
        for single_attr in (u'cell', u'pgrd', u'land'):
            # Grab the version that we're trying to merge, and check if there's
            # even one present
            src_rec = getattr(block, single_attr)
            if src_rec and not src_rec.flags1.ignored:
                # If we're Filter-tagged, perform merge filtering first
                if doFilter:
                    src_rec.mergeFilter(loadSet)
                    masterset = MasterSet()
                    src_rec.updateMasters(masterset.add)
                    if not loadSetIsSuperset(masterset):
                        # Filtered out, discard this record and skip to next
                        setattr(block, single_attr, None)
                        continue
                # In IIM, skip all merging (duh)
                if iiSkipMerge: continue
                dest_rec = getattr(self, single_attr)
                if dest_rec and dest_rec.fid != src_rec.fid:
                    raise ModFidMismatchError(self.inName, dest_rec.rec_str,
                                              dest_rec.fid, src_rec.fid)
                # We're past all hurdles - stick a copy of this record into
                # ourselves and mark it as merged
                mergeIdsAdd(src_rec.fid)
                setattr(self, single_attr, src_rec.getTypeCopy())
        for list_attr in (u'temp_refs', u'persistent_refs', u'distant_refs'):
            filtered_list = []
            filtered_append = filtered_list.append
            # Build a mapping from fids in the current list to the index at
            # which they're stored ##: cache? see also updateRecords above
            dest_list = getattr(self, list_attr)
            append_to_dest = dest_list.append
            id_fids = {record.fid: i for i, record
                       in enumerate(dest_list)}
            for src_rec in getattr(block, list_attr):
                if src_rec.flags1.ignored: continue
                # If we're Filter-tagged, perform merge filtering first
                if doFilter:
                    src_rec.mergeFilter(loadSet)
                    masterset = MasterSet()
                    src_rec.updateMasters(masterset.add)
                    if not loadSetIsSuperset(masterset):
                        continue
                # We're either not Filter-tagged or we want to keep this record
                filtered_append(src_rec)
                # In IIM, skip all merging (duh)
                if iiSkipMerge: continue
                # We're past all hurdles - stick a copy of this record into
                # ourselves and mark it as merged
                src_fid = src_rec.fid
                rec_copy = src_rec.getTypeCopy()
                mergeIdsAdd(src_fid)
                if rec_copy.fid in id_fids:
                    dest_list[id_fids[src_fid]] = rec_copy
                else:
                    append_to_dest(rec_copy)
            # Apply any merge filtering we've done here
            setattr(block, list_attr, filtered_list)

    def __repr__(self):
        return (u'<CELL (%r): %u persistent record(s), %u distant record(s), '
                u'%u temporary record(s), %s, %s>') % (
            self.cell, len(self.persistent_refs), len(self.distant_refs),
            len(self.temp_refs),
            u'LAND: %r' % self.land if self.land else u'no LAND',
            u'PGRD: %r' % self.pgrd if self.pgrd else u'no PGRD')

#------------------------------------------------------------------------------
class MobCells(MobBase):
    """A block containing cells. Subclassed by MobWorld and MobICells.

    Note that "blocks" here only roughly match the file block structure.

    "Bsb" is a tuple of the file (block,subblock) labels. For interior
    cells, bsbs are tuples of two numbers, while for exterior cells, bsb labels
    are tuples of grid tuples."""

    def __init__(self, header, loadFactory, ins=None, do_unpack=False):
        self.cellBlocks = [] #--Each cellBlock is a cell and its related
        # records.
        self.id_cellBlock = {}
        super(MobCells, self).__init__(header, loadFactory, ins, do_unpack)

    def indexRecords(self):
        """Indexes records by fid."""
        self.id_cellBlock = {x.cell.fid: x for x in self.cellBlocks}

    def setCell(self,cell):
        """Adds record to record list and indexed."""
        if self.cellBlocks and not self.id_cellBlock:
            self.indexRecords()
        cfid = cell.fid
        if cfid in self.id_cellBlock:
            self.id_cellBlock[cfid].cell = cell
        else:
            cellBlock = MobCell(GrupHeader(0, 0, 6, self.stamp), ##: Note label is 0 here - specialized GrupHeader subclass?
                                self.loadFactory, cell)
            cellBlock.setChanged()
            self.cellBlocks.append(cellBlock)
            self.id_cellBlock[cfid] = cellBlock

    def remove_cell(self, cell):
        """Removes the specified cell from this block. The exact cell object
        must be present, otherwise a ValueError is raised."""
        if self.cellBlocks and not self.id_cellBlock:
            self.indexRecords()
        self.cellBlocks.remove(cell)
        del self.id_cellBlock[cell.fid]

    def getBsbSizes(self): ##: This is the _sort_group for MobCells
        """Returns the total size of the block, but also returns a
        dictionary containing the sizes of the individual block,subblocks."""
        bsbCellBlocks = [(x.getBsb(),x) for x in self.cellBlocks]
        # First sort by the CELL FormID, then by the block they belong to
        bsbCellBlocks.sort(key=lambda y: y[1].cell.fid)
        bsbCellBlocks.sort(key=itemgetter(0))
        bsb_size = {}
        hsize = RecordHeader.rec_header_size
        totalSize = hsize
        bsb_set_default = bsb_size.setdefault
        for bsb,cellBlock in bsbCellBlocks:
            cellBlockSize = cellBlock.getSize()
            totalSize += cellBlockSize
            bsb0 = (bsb[0],None) #--Block group
            bsb_set_default(bsb0,hsize)
            if bsb_set_default(bsb, hsize) == hsize:
                bsb_size[bsb0] += hsize
            bsb_size[bsb] += cellBlockSize
            bsb_size[bsb0] += cellBlockSize
        totalSize += hsize * len(bsb_size)
        return totalSize,bsb_size,bsbCellBlocks

    def dumpBlocks(self,out,bsbCellBlocks,bsb_size,blockGroupType,
                   subBlockGroupType):
        """Dumps the cell blocks and their block and sub-block groups to
        out."""
        curBlock = None
        curSubblock = None
        stamp = self.stamp
        outWrite = out.write
        for bsb,cellBlock in bsbCellBlocks:
            (block,subblock) = bsb
            bsb0 = (block,None)
            if block != curBlock:
                curBlock,curSubblock = bsb0
                outWrite(GrupHeader(bsb_size[bsb0], block, blockGroupType, ##: Here come the tuples - specialized GrupHeader subclass?
                                    stamp).pack_head())
            if subblock != curSubblock:
                curSubblock = subblock
                outWrite(GrupHeader(bsb_size[bsb], subblock, subBlockGroupType, ##: Here come the tuples - specialized GrupHeader subclass?
                                    stamp).pack_head())
            cellBlock.dump(out)

    def getNumRecords(self,includeGroups=True):
        """Returns number of records, including self and all children."""
        count = sum(x.getNumRecords(includeGroups) for x in self.cellBlocks)
        if count and includeGroups:
            blocks_bsbs = {x2.getBsb() for x2 in self.cellBlocks} ##: needs short fids !!
            # 1 GRUP header for every cellBlock and one for each separate (?) subblock
            count += 1 + len(blocks_bsbs) + len({x1[0] for x1 in blocks_bsbs})
        return count

    #--Fid manipulation, record filtering ----------------------------------
    def get_all_signatures(self):
        return set(chain.from_iterable(c.get_all_signatures()
                                       for c in self.cellBlocks))

    def iter_records(self):
        return chain.from_iterable(c.iter_records() for c in self.cellBlocks)

    def keepRecords(self, p_keep_ids):
        """Keeps records with fid in set p_keep_ids. Discards the rest."""
        #--Note: this call will add the cell to p_keep_ids if any of its
        # related records are kept.
        for cellBlock in self.cellBlocks: cellBlock.keepRecords(p_keep_ids)
        self.cellBlocks = [x for x in self.cellBlocks if x.cell.fid in p_keep_ids]
        self.id_cellBlock.clear()
        self.setChanged()

    def merge_records(self, block, loadSet, mergeIds, iiSkipMerge, doFilter):
        from ..mod_files import MasterSet # YUCK
        if self.cellBlocks and not self.id_cellBlock:
            self.indexRecords()
        lookup_cell_block = self.id_cellBlock.get
        filtered_cell_blocks = []
        filtered_append = filtered_cell_blocks.append
        loadSetIsSuperset = loadSet.issuperset
        for src_cell_block in block.cellBlocks:
            was_newly_added = False
            src_fid = src_cell_block.cell.fid
            # Check if we already have a cell with that FormID
            dest_cell_block = lookup_cell_block(src_fid)
            if not dest_cell_block:
                # We do not, add it and then look up again
                ##: Shouldn't all the setCell calls use getTypeCopy?
                self.setCell(src_cell_block.cell)
                dest_cell_block = lookup_cell_block(src_fid)
                was_newly_added = True
            # Delegate merging to the (potentially newly added) child cell
            dest_cell_block.merge_records(src_cell_block, loadSet,
                mergeIds, iiSkipMerge, doFilter)
            # In IIM, skip all merging - note that we need to remove the child
            # cell again if it was newly added in IIM mode.
            if iiSkipMerge:
                if was_newly_added:
                    self.remove_cell(dest_cell_block.cell)
                continue
            # If we're Filter-tagged, check if the child cell got filtered out
            if doFilter:
                masterset = MasterSet()
                src_cell_block.updateMasters(masterset.add)
                if not loadSetIsSuperset(masterset):
                    # The child cell got filtered out. If it was newly added,
                    # we need to remove it from this block again. Otherwise, we
                    # can just skip forward to the next child cell.
                    if was_newly_added:
                        self.remove_cell(dest_cell_block.cell)
                    continue
            # We're either not Filter-tagged or we want to keep this cell
            filtered_append(src_cell_block)
        # Apply any merge filtering we've done above to the record block
        block.cellBlocks = filtered_cell_blocks
        block.indexRecords()

    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if
        converting to short format."""
        for cellBlock in self.cellBlocks:
            cellBlock.convertFids(mapper,toLong)

    def updateRecords(self, srcBlock, mergeIds):
        """Updates any records in 'self' that exist in 'srcBlock'."""
        if self.cellBlocks and not self.id_cellBlock:
            self.indexRecords()
        id_Get = self.id_cellBlock.get
        for srcCellBlock in srcBlock.cellBlocks:
            cellBlock = id_Get(srcCellBlock.cell.fid)
            if cellBlock:
                cellBlock.updateRecords(srcCellBlock, mergeIds)

    def updateMasters(self, masterset_add):
        """Updates set of master names according to masters actually used."""
        for cellBlock in self.cellBlocks:
            cellBlock.updateMasters(masterset_add)

    def __repr__(self):
        return u'<CELL GRUP: %u record(s)>' % len(self.cellBlocks)

#------------------------------------------------------------------------------
class MobICells(MobCells):
    """Tes4 top block for interior cell records."""

    def _load_rec_group(self, ins, endPos):
        """Loads data from input stream. Called by load()."""
        expType = self.label
        recCellClass = self.loadFactory.getRecClass(expType)
        insSeek = ins.seek
        if not recCellClass: insSeek(endPos) # skip the whole group
        cell = None
        endBlockPos = endSubblockPos = 0
        unpackCellBlocks = self.loadFactory.getUnpackCellBlocks(b'CELL')
        insAtEnd = ins.atEnd
        insRecHeader = ins.unpackRecHeader
        cellBlocksAppend = self.cellBlocks.append
        selfLoadFactory = self.loadFactory
        insTell = ins.tell
        def build_cell_block(unpack_block=False, skip_delta=False):
            """Helper method that parses and stores a cell block for the
            current cell."""
            if unpack_block:
                cellBlock = MobCell(header, selfLoadFactory, cell, ins, True)
            else:
                cellBlock = MobCell(header, selfLoadFactory, cell)
                if skip_delta:
                    insSeek(delta, 1)
            cellBlocksAppend(cellBlock)
        while not insAtEnd(endPos, f'{sig_to_str(expType)} Top Block'):
            header = insRecHeader()
            _rsig = header.recType
            if _rsig == expType:
                if cell:
                    # If we already have a cell lying around, finish it off
                    build_cell_block()
                cell = recCellClass(header,ins,True)
                if insTell() > endBlockPos or insTell() > endSubblockPos:
                    raise ModError(self.inName,
                                   f'Interior cell <{cell.fid:X}> {cell.eid} '
                                   f'outside of block or subblock.')
            elif _rsig == b'GRUP':
                groupFid,groupType = header.label, header.groupType
                delta = header.blob_size()
                if groupType == 2: # Block number
                    endBlockPos = insTell() + delta
                elif groupType == 3: # Sub-block number
                    endSubblockPos = insTell() + delta
                elif groupType == 6: # Cell Children
                    if cell:
                        if groupFid != cell.fid:
                            raise ModError(self.inName,
                                f'Cell subgroup ({groupFid:X}) does not match '
                                f'CELL <{cell.fid:X}> {cell.eid}.')
                        build_cell_block(unpack_block=unpackCellBlocks,
                            skip_delta=True)
                        cell = None
                    else:
                        raise ModError(self.inName,
                            f'Extra subgroup {groupType:d} in CELL group.')
                else:
                    raise ModError(self.inName,
                        f'Unexpected subgroup {groupType:d} in CELL group.')
            else:
                raise ModError(self.inName,
                               f'Unexpected {sig_to_str(_rsig)} record in '
                               f'{sig_to_str(expType)} group.')
        if cell:
            # We have a CELL without children left over, finish it
            build_cell_block()
        self.setChanged()

    def dump(self,out):
        """Dumps group header and then records."""
        if not self.changed:
            out.write(self.header.pack_head())
            out.write(self.data)
        elif self.cellBlocks:
            (totalSize, bsb_size, blocks) = self.getBsbSizes()
            self.header.size = totalSize
            out.write(self.header.pack_head())
            self.dumpBlocks(out,blocks,bsb_size,2,3)

#------------------------------------------------------------------------------
class MobWorld(MobCells):

    def __init__(self, header, loadFactory, world, ins=None, do_unpack=False):
        self.world = world
        ##: rename to e.g. persistent_block, this is the cell block that houses
        # all persistent objects in the worldspace
        self.worldCellBlock = None
        self.road = None
        super(MobWorld, self).__init__(header, loadFactory, ins, do_unpack)

    def _load_rec_group(self, ins, endPos, __packer=structs_cache[u'I'].pack,
                        __unpacker=structs_cache[u'2h'].unpack):
        """Loads data from input stream. Called by load()."""
        cellType_class = self.loadFactory.getCellTypeClass()
        errLabel = u'World Block'
        cell = None
        block = None
        # subblock = None # unused var
        endBlockPos = endSubblockPos = 0
        unpackCellBlocks = self.loadFactory.getUnpackCellBlocks(b'WRLD')
        insAtEnd = ins.atEnd
        insRecHeader = ins.unpackRecHeader
        cellGet = cellType_class.get
        insTell = ins.tell
        selfLoadFactory = self.loadFactory
        cellBlocksAppend = self.cellBlocks.append
        from .. import bush
        isFallout = bush.game.fsName != u'Oblivion'
        cells = {}
        def build_cell_block(unpack_block=False, skip_delta=False):
            """Helper method that parses and stores a cell block for the
            current cell."""
            if unpack_block:
                cellBlock = MobCell(header, selfLoadFactory, cell, ins, True)
            else:
                cellBlock = MobCell(header, selfLoadFactory, cell)
                if skip_delta:
                    header.skip_blob(ins)
            if cell.flags1.persistent:
                if self.worldCellBlock:
                    raise ModError(self.inName,
                        u'Misplaced exterior cell %r.' % cell)
                self.worldCellBlock = cellBlock
            else:
                cellBlocksAppend(cellBlock)
        while not insAtEnd(endPos,errLabel):
            curPos = insTell()
            if curPos >= endBlockPos:
                block = None
            if curPos >= endSubblockPos:
                pass # subblock = None # unused var
            #--Get record info and handle it
            header = insRecHeader()
            _rsig = header.recType
            recClass = cellGet(_rsig)
            if _rsig == b'ROAD':
                if not recClass: header.skip_blob(ins)
                else: self.road = recClass(header,ins,True)
            elif _rsig == b'CELL':
                if cell:
                    # If we already have a cell lying around, finish it off
                    build_cell_block()
                cell = recClass(header,ins,True)
                if isFallout: cells[cell.fid] = cell
                if block and (
                        insTell() > endBlockPos or insTell() > endSubblockPos):
                        raise ModError(self.inName,
                            f'Exterior cell {cell!r} after block or subblock.')
            elif _rsig == b'GRUP':
                groupFid,groupType = header.label,header.groupType
                if groupType == 4: # Exterior Cell Block
                    block = __unpacker(__packer(groupFid))
                    block = (block[1],block[0])
                    endBlockPos = insTell() + header.blob_size()
                elif groupType == 5: # Exterior Cell Sub-Block
                    # we don't actually care what the sub-block is, since
                    # we never use that information here. So below was unused:
                    # subblock = structUnpack('2h',structPack('I',groupFid))
                    # subblock = (subblock[1],subblock[0]) # unused var
                    endSubblockPos = insTell() + header.blob_size()
                elif groupType == 6: # Cell Children
                    if isFallout: cell = cells.get(groupFid,None)
                    if cell:
                        if groupFid != cell.fid:
                            raise ModError(self.inName,
                                           f'Cell subgroup ({hex(groupFid)}) '
                                           f'does not match CELL {cell!r}.')
                        build_cell_block(unpack_block=unpackCellBlocks,
                            skip_delta=True)
                        cell = None
                    else:
                        raise ModError(self.inName,
                                       u'Extra cell children subgroup in '
                                       u'world children group.')
                else:
                    raise ModError(self.inName,
                                   f'Unexpected subgroup {groupType:d} in '
                                   f'world children group.')
            else:
                raise ModError(self.inName,
                               f'Unexpected {sig_to_str(_rsig)} record in'
                               f'world children group.')
        if cell:
            # We have a CELL without children left over, finish it
            build_cell_block()
        self.setChanged()

    def getNumRecords(self,includeGroups=True):
        """Returns number of records, including self and all children."""
        if not self.changed:
            return super(MobCells, self).getNumRecords(includeGroups) ##: TTT?
        count = 1 # self.world, always present
        count += bool(self.road)
        if self.worldCellBlock:
            count += self.worldCellBlock.getNumRecords(includeGroups)
        count += super(MobWorld, self).getNumRecords(includeGroups)
        return count

    def dump(self,out):
        """Dumps group header and then records.  Returns the total size of
        the world block."""
        hsize = RecordHeader.rec_header_size
        worldSize = self.world.getSize() + hsize
        self.world.dump(out)
        if not self.changed:
            out.write(self.header.pack_head())
            out.write(self.data)
            return self.size + worldSize
        elif self.cellBlocks or self.road or self.worldCellBlock:
            (totalSize, bsb_size, blocks) = self.getBsbSizes()
            if self.road:
                totalSize += self.road.getSize() + hsize
            if self.worldCellBlock:
                totalSize += self.worldCellBlock.getSize()
            self.header.size = totalSize
            self.header.label = self.world.fid
            self.header.groupType = 1
            out.write(self.header.pack_head())
            # The order is ROAD -> persistent CELL -> blocks
            if self.road:
                self.road.dump(out)
            if self.worldCellBlock:
                self.worldCellBlock.dump(out)
            self.dumpBlocks(out,blocks,bsb_size,4,5)
            return totalSize + worldSize
        else:
            return worldSize

    def set_persistent_cell(self, cell):
        """Updates the persistent CELL block to use the specified CELL or
        creates a new persistent CELL block if one does not already exist in
        this world."""
        if self.worldCellBlock:
            self.worldCellBlock.cell = cell
        else:
            new_pers_block = MobCell(GrupHeader(0, 0, 6, self.stamp), ##: Note label is 0 here - specialized GrupHeader subclass?
                                     self.loadFactory, cell)
            new_pers_block.setChanged()
            self.worldCellBlock = new_pers_block

    #--Fid manipulation, record filtering ----------------------------------
    def get_all_signatures(self):
        all_sigs = super(MobWorld, self).get_all_signatures()
        all_sigs.add(self.world._rec_sig)
        if self.road: all_sigs.add(self.road._rec_sig)
        if self.worldCellBlock:
            all_sigs |= self.worldCellBlock.get_all_signatures()
        return all_sigs

    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if
        converting to short format."""
        self.world.convertFids(mapper,toLong)
        if self.road:
            self.road.convertFids(mapper,toLong)
        if self.worldCellBlock:
            self.worldCellBlock.convertFids(mapper,toLong)
        super(MobWorld, self).convertFids(mapper, toLong)

    def updateMasters(self, masterset_add):
        """Updates set of master names according to masters actually used."""
        self.world.updateMasters(masterset_add)
        if self.road:
            self.road.updateMasters(masterset_add)
        if self.worldCellBlock:
            self.worldCellBlock.updateMasters(masterset_add)
        super(MobWorld, self).updateMasters(masterset_add)

    def updateRecords(self, srcBlock, mergeIds):
        """Updates any records in 'self' that exist in 'srcBlock'."""
        for attr in (u'world', u'road'):
            myRecord = getattr(self, attr)
            record = getattr(srcBlock, attr)
            if myRecord and record:
                src_rec_fid = record.fid
                if myRecord.fid != src_rec_fid:
                    raise ModFidMismatchError(self.inName, myRecord.rec_str,
                                              myRecord.fid, src_rec_fid)
                if not record.flags1.ignored:
                    record = record.getTypeCopy()
                    setattr(self, attr, record)
                    mergeIds.discard(src_rec_fid)
        if self.worldCellBlock and srcBlock.worldCellBlock:
            self.worldCellBlock.updateRecords(srcBlock.worldCellBlock,
                mergeIds)
        super(MobWorld, self).updateRecords(srcBlock, mergeIds)

    def iter_records(self):
        single_recs = [x for x in (self.world, self.road) if x]
        c_recs = (self.worldCellBlock.iter_records() if self.worldCellBlock
                  else [])
        return chain(single_recs, c_recs, super(MobWorld, self).iter_records())

    def keepRecords(self, p_keep_ids):
        """Keeps records with fid in set p_keep_ids. Discards the rest."""
        if self.road and self.road.fid not in p_keep_ids:
            self.road = None
        if self.worldCellBlock:
            self.worldCellBlock.keepRecords(p_keep_ids)
            if self.worldCellBlock.cell.fid not in p_keep_ids:
                self.worldCellBlock = None
        super(MobWorld, self).keepRecords(p_keep_ids)
        if self.road or self.worldCellBlock or self.cellBlocks:
            p_keep_ids.add(self.world.fid)

    def merge_records(self, block, loadSet, mergeIds, iiSkipMerge, doFilter):
        from ..mod_files import MasterSet # YUCK
        mergeIdsAdd = mergeIds.add
        loadSetIsSuperset = loadSet.issuperset
        for single_attr in (u'world', u'road'):
            src_rec = getattr(block, single_attr)
            if src_rec and not src_rec.flags1.ignored:
                # If we're Filter-tagged, perform merge filtering first
                if doFilter:
                    src_rec.mergeFilter(loadSet)
                    masterset = MasterSet()
                    src_rec.updateMasters(masterset.add)
                    if not loadSetIsSuperset(masterset):
                        # Filtered out, discard this record and skip to next
                        setattr(block, single_attr, None)
                        continue
                # In IIM, skip all merging (duh)
                if iiSkipMerge: continue
                dest_rec = getattr(self, single_attr)
                if dest_rec and dest_rec.fid != src_rec.fid:
                    raise ModFidMismatchError(self.inName, dest_rec.rec_str,
                                              dest_rec.fid, src_rec.fid)
                # We're past all hurdles - stick a copy of this record into
                # ourselves and mark it as merged
                mergeIdsAdd(src_rec.fid)
                setattr(self, single_attr, src_rec.getTypeCopy())
        if block.worldCellBlock:
            was_newly_added = False
            # If we don't have a world cell block yet, make a new one to merge
            # the source's world cell block into
            if not self.worldCellBlock:
                self.worldCellBlock = MobCell(GrupHeader(0, 0, 6, self.stamp),
                    self.loadFactory, None) # cell will be set in merge_records
                was_newly_added = True
            # Delegate merging to the (potentially newly added) block
            self.worldCellBlock.merge_records(block.worldCellBlock, loadSet,
                mergeIds, iiSkipMerge, doFilter)
            # In IIM, skip all merging - note that we need to remove the world
            # cell block again if it was newly added in IIM mode.
            if iiSkipMerge:
                if was_newly_added:
                    self.worldCellBlock = None
            elif doFilter:
                # If we're Filter-tagged, check if the world cell block got
                # filtered out
                masterset = MasterSet()
                self.worldCellBlock.updateMasters(masterset.add)
                if not loadSetIsSuperset(masterset):
                    # The cell block got filtered out. If it was newly added,
                    # we need to remove it from this block again.
                    if was_newly_added:
                        self.worldCellBlock = None
        super(MobWorld, self).merge_records(block, loadSet, mergeIds,
            iiSkipMerge, doFilter)

    def __repr__(self):
        return u'<WRLD (%r): %u record(s), %s, %s>' % (
            self.world, len(self.cellBlocks),
            u'persistent CELL: %r' % self.worldCellBlock
            if self.worldCellBlock else u'no persistent CELL',
            u'ROAD: %r' % self.road if self.road else u'no ROAD')

#------------------------------------------------------------------------------
class MobWorlds(MobBase):
    """Tes4 top block for world records and related roads and cells. Consists
    of world blocks."""

    def __init__(self, header, loadFactory, ins=None, do_unpack=False):
        self.worldBlocks = []
        self.id_worldBlocks = {}
        self.orphansSkipped = 0
        super(MobWorlds, self).__init__(header, loadFactory, ins, do_unpack)

    def _load_rec_group(self, ins, endPos):
        """Loads data from input stream. Called by load()."""
        expType = self.label
        recWrldClass = self.loadFactory.getRecClass(expType)
        insSeek = ins.seek
        if not recWrldClass: insSeek(endPos) # skip the whole group
        worldBlocks = self.worldBlocks
        world = None
        insAtEnd = ins.atEnd
        insRecHeader = ins.unpackRecHeader
        selfLoadFactory = self.loadFactory
        worldBlocksAppend = worldBlocks.append
        from .. import bush
        isFallout = bush.game.fsName != u'Oblivion'
        worlds = {}
        header = None
        while not insAtEnd(endPos, f'{sig_to_str(expType)} Top Block'):
            #--Get record info and handle it
            prev_header = header
            header = insRecHeader()
            _rsig = header.recType
            if _rsig == expType:
                # FIXME(inf) The getattr here has to go
                if (prev_header and
                        getattr(prev_header, u'recType', None) == b'WRLD'):
                    # We hit a WRLD directly after another WRLD, so there are
                    # no children to read - just finish this WRLD
                    self.setWorld(world)
                world = recWrldClass(header,ins,True)
                if isFallout: worlds[world.fid] = world
            elif _rsig == b'GRUP':
                groupFid,groupType = header.label,header.groupType
                if groupType != 1:
                    raise ModError(ins.inName,
                                   f'Unexpected subgroup {groupType:d} in '
                                   f'CELL group.')
                if isFallout: world = worlds.get(groupFid,None)
                if not world:
                    #raise ModError(ins.inName,'Extra subgroup %d in WRLD
                    # group.' % groupType)
                    #--Orphaned world records. Skip over.
                    header.skip_blob(ins)
                    self.orphansSkipped += 1
                    continue
                if groupFid != world.fid:
                    raise ModError(ins.inName,
                                   f'WRLD subgroup ({hex(groupFid)}) does '
                                   f'not match WRLD {world!r}.')
                worldBlock = MobWorld(header,selfLoadFactory,world,ins,True)
                worldBlocksAppend(worldBlock)
                world = None
            else:
                raise ModError(ins.inName,
                               f'Unexpected {sig_to_str(_rsig)} record in'
                               f'{expType} group.')
        if world:
            # We have a last WRLD without children lying around, finish it
            self.setWorld(world)
        self.id_worldBlocks.clear()
        self.setChanged()

    def getSize(self):
        """Returns size (including size of any group headers)."""
        return RecordHeader.rec_header_size + sum(
            x.getSize() for x in self.worldBlocks)

    def dump(self,out):
        """Dumps group header and then records."""
        if not self.changed:
            out.write(self.header.pack_head())
            out.write(self.data)
        else:
            if not self.worldBlocks: return
            worldHeaderPos = out.tell()
            header = TopGrupHeader(0, self.label, self.stamp)
            out.write(header.pack_head())
            self._sort_group()
            ##: Why not use getSize here?
            totalSize = RecordHeader.rec_header_size + sum(
                x.dump(out) for x in self.worldBlocks)
            out.seek(worldHeaderPos + 4)
            pack_int(out, totalSize)
            out.seek(worldHeaderPos + totalSize)

    def getNumRecords(self,includeGroups=True):
        """Returns number of records, including self and all children."""
        count = sum(x.getNumRecords(includeGroups) for x in self.worldBlocks)
        return count + includeGroups * bool(count)

    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if
        converting to short format."""
        for worldBlock in self.worldBlocks:
            worldBlock.convertFids(mapper,toLong)

    def get_all_signatures(self):
        return set(chain.from_iterable(w.get_all_signatures()
                                       for w in self.worldBlocks))

    def indexRecords(self):
        """Indexes records by fid."""
        self.id_worldBlocks = {x.world.fid: x for x in self.worldBlocks}

    def _sort_group(self):
        """Sorts WRLD groups by the FormID of the WRLD record."""
        self.worldBlocks.sort(key=attrgetter_cache[u'world.fid'])

    def updateMasters(self, masterset_add):
        """Updates set of master names according to masters actually used."""
        for worldBlock in self.worldBlocks:
            worldBlock.updateMasters(masterset_add)

    def updateRecords(self, srcBlock, mergeIds):
        """Updates any records in 'self' that exist in 'srcBlock'."""
        if self.worldBlocks and not self.id_worldBlocks:
            self.indexRecords()
        id_worldBlocks = self.id_worldBlocks
        idGet = id_worldBlocks.get
        for srcWorldBlock in srcBlock.worldBlocks:
            worldBlock = idGet(srcWorldBlock.world.fid)
            if worldBlock:
                worldBlock.updateRecords(srcWorldBlock, mergeIds)

    def setWorld(self, world):
        """Adds record to record list and indexed."""
        if self.worldBlocks and not self.id_worldBlocks:
            self.indexRecords()
        fid = world.fid
        if fid in self.id_worldBlocks:
            self.id_worldBlocks[fid].world = world
        else:
            worldBlock = MobWorld(GrupHeader(0, 0, 1, self.stamp), ##: groupType = 1
                                  self.loadFactory, world)
            worldBlock.setChanged()
            self.worldBlocks.append(worldBlock)
            self.id_worldBlocks[fid] = worldBlock

    def remove_world(self, world):
        """Removes the specified world from this block. The exact world object
        must be present, otherwise a ValueError is raised."""
        if self.worldBlocks and not self.id_worldBlocks:
            self.indexRecords()
        self.worldBlocks.remove(world)
        del self.id_worldBlocks[world.fid]

    def iter_records(self):
        return chain.from_iterable(w.iter_records() for w in self.worldBlocks)

    def keepRecords(self, p_keep_ids):
        """Keeps records with fid in set p_keep_ids. Discards the rest."""
        for worldBlock in self.worldBlocks: worldBlock.keepRecords(p_keep_ids)
        self.worldBlocks = [x for x in self.worldBlocks if
                            x.world.fid in p_keep_ids]
        self.id_worldBlocks.clear()
        self.setChanged()

    def merge_records(self, block, loadSet, mergeIds, iiSkipMerge, doFilter):
        from ..mod_files import MasterSet # YUCK
        if self.worldBlocks and not self.id_worldBlocks:
            self.indexRecords()
        lookup_world_block = self.id_worldBlocks.get
        filtered_world_blocks = []
        filtered_append = filtered_world_blocks.append
        loadSetIsSuperset = loadSet.issuperset
        for src_world_block in block.worldBlocks:
            was_newly_added = False
            src_fid = src_world_block.world.fid
            # Check if we already have a world with that FormID
            dest_world_block = lookup_world_block(src_fid)
            if not dest_world_block:
                # We do not, add it and then look up again
                ##: Shouldn't all the setWorld calls use getTypeCopy?
                self.setWorld(src_world_block.world)
                dest_world_block = lookup_world_block(src_fid)
                was_newly_added = True
            # Delegate merging to the (potentially newly added) child world
            dest_world_block.merge_records(src_world_block, loadSet,
                mergeIds, iiSkipMerge, doFilter)
            # In IIM, skip all merging - note that we need to remove the child
            # world again if it was newly added in IIM mode.
            if iiSkipMerge:
                if was_newly_added:
                    self.remove_world(dest_world_block.world)
                continue
            # If we're Filter-tagged, check if the child world got filtered out
            if doFilter:
                masterset = MasterSet()
                src_world_block.updateMasters(masterset.add)
                if not loadSetIsSuperset(masterset):
                    # The child world got filtered out. If it was newly added,
                    # we need to remove it from this block again. Otherwise, we
                    # can just skip forward to the next child world.
                    if was_newly_added:
                        self.remove_world(dest_world_block.world)
                    continue
            # We're either not Filter-tagged or we want to keep this world
            filtered_append(src_world_block)
        # Apply any merge filtering we've done above to the record block
        block.worldBlocks = filtered_world_blocks
        block.indexRecords()

    def __repr__(self):
        return u'<WRLD GRUP: %u record(s)>' % len(self.worldBlocks)
