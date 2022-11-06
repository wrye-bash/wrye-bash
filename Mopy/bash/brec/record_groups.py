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

__author__ = 'Utumno'

# Python imports
from collections import deque, defaultdict
from functools import wraps
from itertools import chain

# Wrye Bash imports
from . import MelRecord
from .mod_io import GrupHeader, RecordHeader, TopGrupHeader, \
    ExteriorGrupHeader, ChildrenGrupHeader, FastModReader, unpack_header
from .record_structs import RecordType
from .utils_constants import DUMMY_FID, group_types, FormId
from ..bolt import attrgetter_cache, sig_to_str, dict_sort, \
    fast_cached_property
from ..exception import AbstractError, ModError, ModFidMismatchError

class _AMobBase:
    """Group of records and/or subgroups."""
    def __init__(self, loadFactory, ins, endPos):
        self.changed = False
        self.loadFactory = loadFactory
        # due to subclasses sometimes setting ins to None
        self.inName = getattr(self, 'inName', None) or (ins and ins.inName)
        if ins:
            self._load_rec_group(ins, endPos)

    def _load_err(self, msg): ##: add ins and print more info
        raise ModError(self.inName, msg)

    def setChanged(self,value=True):
        """Sets changed attribute to value. [Default = True.]"""
        self.changed = value

    ##: This should be dropped later once we ensure we correctly call
    # setChanged() on all non-BP uses of ModFile where we modify records and
    # make the BP call setChanged() during its record trimming phase on all
    # keepIds - hard right now due to having to trace ModFile.load() calls.
    def set_records_changed(self):
        """Mark all records in this record group as changed."""
        if type(self) != MobBase: # ugh
            for r in self.iter_records():
                r.setChanged()

    def updateMasters(self, masterset_add):
        """Updates set of master names according to masters actually used."""
        for record in self.iter_records():
            record.updateMasters(masterset_add)

    # Abstract methods --------------------------------------------------------
    def getSize(self):
        """Returns size (including size of any group headers)."""
        raise AbstractError

    def getNumRecords(self,includeGroups=True):
        """Returns number of records, including self (if plusSelf), unless
        there's no subrecords, in which case, it returns 0."""
        raise AbstractError

    def dump(self, out):
        """Dumps record header and data into output file stream."""
        raise AbstractError

    def iter_present_records(self, include_ignored=False, rec_key='fid',
                             __attrgetters=attrgetter_cache):
        """Filters iter_records, returning only records that have not set
        the deleted flag and/or the ignore flag if include_ignored is False."""
        key_get = __attrgetters[rec_key]
        return ((key_get(r), r) for r in self.iter_records() if not
                r.flags1.deleted and (include_ignored or not r.flags1.ignored))

    def get_all_signatures(self):
        """Returns a set of all signatures actually contained in this block."""
        raise AbstractError('get_all_signatures not implemented')

    def iter_records(self):
        """Flattens the structure of this record block into a linear sequence
        of records. Works as an iterator for memory reasons."""
        raise AbstractError('iter_records not implemented')

    def keepRecords(self, p_keep_ids):
        """Keeps records with fid in set p_keep_ids. Discards the rest."""
        raise AbstractError('keepRecords not implemented')

    def _load_rec_group(self, ins, endPos):
        """Loads data from input stream. Called by __init__()."""
        raise AbstractError('_load_rec_group not implemented')

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
        raise AbstractError(f'{self}: merge_records not implemented')

    def updateRecords(self, srcBlock, mergeIds):
        """Update the contents of records inside the BP to ones from a
        source plugin. We never add new records into the BP here. That's
        only done by importers (using setRecord) or by merging files (via
        merge_records)."""
        raise AbstractError('updateRecords not implemented')

class MobBase(_AMobBase):
    """Group of records and/or subgroups. This basic implementation does not
    support unpacking, but can report its number of records and be dumped."""

    def __init__(self, grup_head, loadFactory, ins=None, do_unpack=False):
        self.header = grup_head
        self.size = grup_head.size
        # binary blob of the whole record group minus its GRUP header ##: rename
        self.data = None
        self.numRecords = -1
        # we need to store the _end_pos for _WorldChildren
        self._end_pos = ins and (ins.tell() + grup_head.blob_size()) ##: WIP!
        if ins:
            # self._end_pos = ins.tell() + grup_head.blob_size()
            #--Read, but don't analyze.
            if not do_unpack:
                self.data = ins.read(grup_head.blob_size(),
                                     type(self).__name__)
                self.inName = ins.inName
                ins = None # block _load_rec_group in super
        super().__init__(loadFactory, ins, self._end_pos)

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
            with FastModReader(self.inName, self.data) as ins:
                ins_tell = ins.tell
                ins_size = ins.size
                while ins_tell() != ins_size:
                    header = unpack_header(ins)
                    if header.recType != b'GRUP':
                        # FMR.seek doesn't have *debug_str arg so use blob_size
                        ins.seek(header.blob_size(), 1) # instead of skip_blob
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
        if self.numRecords > 0:
            self.header.size = self.size
            out.write(self.header.pack_head())
            out.write(self.data)

#------------------------------------------------------------------------------
class MobObjects(MobBase):
    """Represents a group consisting of the record types specified in
    _accepted_sigs."""
    _bad_form = None # yak
    _accepted_sigs = {b'OVERRIDE'} # overriden via properties must be static
    _grup_header_type: type[GrupHeader] | None = None

    def __init__(self, header, loadFactory, ins=None, do_unpack=False):
        self.id_records = {}
        if ins and all(loadFactory.sig_to_type[r] is None for r in
                       self._accepted_sigs):
            header.skip_blob(ins)
            self.inName = ins.inName
            ins = None # block _load_rec_group
        super().__init__(header, loadFactory, ins, do_unpack)

    def _load_rec_group(self, ins, endPos):
        """Loads data from input stream. Called by load()."""
        insAtEnd = ins.atEnd
        errLabel = f'{self}'
        while not insAtEnd(endPos,errLabel):
            #--Get record info and handle it
            header = unpack_header(ins)
            if header.recType not in self._accepted_sigs:
                self._load_err(f'Unexpected {header!r} record in {errLabel}.')
            grel = self._group_element(header, ins)
            if grel is not None: self.setRecord(grel, _loading=True)
            else: header.skip_blob(ins)
        self.setChanged()

    def _group_element(self, header, ins, do_unpack=True) -> 'MreRecord':
        rec_class = self.loadFactory.sig_to_type[header.recType]
        return None if rec_class is None else rec_class(header, ins,
                                                        do_unpack=do_unpack)

    def _write_header(self, out):
        """getSize not only gets the size - essentially prepares the whole
        grup for dumping - WIP"""
        if self.header:
            self.header.size = self.getSize()
            out.write(self.header.pack_head())# keep the rest of the header
        elif self._grup_header_type:
            raise self._load_err(f'Missing header in {self!r}')

    @classmethod
    def empty_mob(cls, load_f, head_label, *head_arg):
        """Get an empty MobObjects collection to use in merge_records etc."""
        raise AbstractError

    def __bool__(self): return bool(self.id_records)

    def getActiveRecords(self, rec_sig=None):
        """Returns non-ignored records - XXX what about isKeyedByEid?"""
        return [(rec_key, r) for rec_key, r in self.id_records.items() if
                not r.flags1.ignored]

    def getNumRecords(self,includeGroups=True):
        """Returns number of records, including self - if empty return 0."""
        num_recs = len(self.id_records)
        if num_recs: num_recs += includeGroups #--Count self
        self.numRecords = num_recs
        return num_recs

    def getSize(self):
        """Returns size (including size of any group headers)."""
        if not self.changed:
            return self.size
        else:
            if not self.id_records: return 0
            hsize = RecordHeader.rec_header_size
            recs_size = sum((hsize + r.getSize()) for r in self.id_records.values())
            return hsize + recs_size # add hsize for the GRUP header

    def dump(self,out):
        """Dumps group header and then records."""
        if not self.changed:
            out.write(self.header.pack_head())
            out.write(self.data)
        else:
            if not self.id_records: return
            self._write_header(out)
            self._sort_group()
            for record in self.id_records.values():
                record.dump(out)

    def _sort_group(self):
        """Sorts records by FormID - now eid order matters too for
        isKeyedByEid records."""
        self.id_records = dict(dict_sort(self.id_records))

    def getRecord(self, rec_rid):
        """Gets record with corresponding id.
        If record doesn't exist, returns None."""
        return self.id_records.get(rec_rid, None)

    def setRecord(self, record, do_copy=True, _loading=False):
        """Adds record to self.id_records."""
        el_key = record.group_key()
        if _loading and el_key in self.id_records:
            self._load_err(f'Duplicate {el_key} record in {self}')
        self.id_records[el_key] = record if _loading or not do_copy else \
            record.getTypeCopy()

    def keepRecords(self, p_keep_ids):
        """Keeps records with fid in set p_keep_ids. Discards the rest."""
        self.id_records = {rec_key: record for rec_key, record in
                           self.id_records.items() if rec_key in p_keep_ids}
        self.setChanged()

    def updateRecords(self, srcBlock, mergeIds):
        merge_ids_discard = mergeIds.discard
        copy_to_self = self.setRecord
        dest_rec_fids = self.id_records
        for rid, record in srcBlock.getActiveRecords():
            if rid in dest_rec_fids:
                copy_to_self(record)
                merge_ids_discard(rid)

    def merge_records(self, block, loadSet, mergeIds, iiSkipMerge, doFilter):
        # YUCK, drop these local imports!
        from ..mod_files import MasterSet
        filtered = {}
        loadSetIsSuperset = loadSet.issuperset
        mergeIdsAdd = mergeIds.add
        copy_to_self = self.setRecord
        for rid, src_rec in block.getActiveRecords():
            if rid == self._bad_form: continue
            #--Include this record?
            if doFilter:
                # If we're Filter-tagged, perform merge filtering. Then, check
                # if the record has any FormIDs with masters that are on disk
                # left. If it does not, skip the whole record (because all of
                # its contents have been merge-filtered out).
                src_rec.mergeFilter(loadSet)
                masterset = MasterSet()
                src_rec.updateMasters(masterset.add)
                if not loadSetIsSuperset(masterset):
                    continue
            # We're either not Filter-tagged or we want to keep this record
            filtered[rkey := src_rec.group_key()] = src_rec
            # If we're IIM-tagged and this is not one of the IIM-approved
            # record types, skip merging
            if not iiSkipMerge:
                # We're past all hurdles - stick a copy of this record into
                # ourselves and mark it as merged
                mergeIdsAdd(rkey)
                copy_to_self(src_rec)
        # Apply any merge filtering we've done above to the record block in
        # question. That way, patchers won't see the records that have been
        # filtered out here.
        block.id_records = filtered

    def iter_records(self):
        return self.id_records.values()

    def __repr__(self):
        return f'<{self}: {len(self.id_records)} {self._accepted_sigs} ' \
               f'record(s)>'

    def __str__(self): return f'{group_types[self.header.groupType]} GRUP'

class _ChildrenGrup(MobObjects):
    """Represents a children group."""
    _grup_header_type = ChildrenGrupHeader
    _children_grup_type = -1

    def __init__(self, header, loadFactory, ins=None, do_unpack=False,
                 master_rec=None):
        if master_rec and (groupFid := header.label) != master_rec.fid:
            self._load_err(f'Children subgroup ({groupFid}) does '
                           f'not match parent {master_rec!r}.')
        super().__init__(header, loadFactory, ins, do_unpack)

    @classmethod
    def empty_mob(cls, load_f, head_label, *head_arg):
        """Get an empty MobObjects collection to use in merge_records etc."""
        head = cls._grup_header_type(0, head_label, *head_arg) if \
            cls._grup_header_type else None
        mob = cls(head, load_f)
        mob.setChanged()
        return mob

    def get_all_signatures(self):
        return {r._rec_sig for r in self.id_records.values()}

_EOF = -1 # endPos is at the end of file - used for non-headed groups
class _Nested(_AMobBase):
    """A nested grup of records with some optional records[ in front]."""
    # sig -> attr - these records should appear at most once except if required
    _extra_records: dict[bytes, str] = {}
    # we need to know the top type this group belongs to for _load_rec_group
    _top_type = None
    _mob_objects_type: dict[int, type[_ChildrenGrup]] = {}
    _mob_objects: dict[int, _ChildrenGrup]
    _marker_groups = {0} # when we hit a top group loading is over

    def __init__(self, loadFactory, ins=None, end_pos=None, **kwargs):
        for att in self._extra_records.values():
            setattr(self, att, kwargs.get(att, None))
        self._mob_objects = {}
        if ins: ins.rewind()
        self._end_pos = end_pos or _EOF # we don't know the size in advance
        super().__init__(loadFactory, ins, self._end_pos)
        self._set_mob_objects()

    def _set_mob_objects(self, head_label=None):
        for gt, mob_type in self._mob_objects_type.items():
            mobs = self._mob_objects.get(gt)
            # if not None might still be empty with size == rec_header_size -
            # I kept those empty groups instead of creating a new one (size==0)
            if mobs is None:
                args = self.loadFactory, head_label or DUMMY_FID, gt
                self._mob_objects[gt] = mob_type.empty_mob(*args)

    def getSize(self):
        return sum(chg.getSize() for chg in chain(self._stray_recs().values(),
                                                  self._mob_objects.values()))

    def getNumRecords(self,includeGroups=True):
        nrecs = sum(1 for __ in self.iter_records())
        if includeGroups and nrecs: # no recs => no top or nested groups
            nrecs += sum(1 for m in self._mob_objects if m)
        return nrecs

    def get_all_signatures(self):
        return {i._rec_sig for i in self.iter_records()}

    def iter_records(self):
        return chain(iter(self._stray_recs().values()),
                     *(v.iter_records() for v in self._mob_objects.values()))

    def merge_records(self, src_block, loadSet, mergeIds, iiSkipMerge, doFilter):
        from ..mod_files import MasterSet # YUCK
        mergeIdsAdd = mergeIds.add
        loadSetIsSuperset = loadSet.issuperset
        for single_attr in self._extra_records.values():
            # Grab the version that we're trying to merge, and check if there's
            # even one present
            src_rec = getattr(src_block, single_attr)
            if src_rec and not src_rec.flags1.ignored:
                # If we're Filter-tagged, perform merge filtering first
                if doFilter:
                    src_rec.mergeFilter(loadSet)
                    masterset = MasterSet()
                    src_rec.updateMasters(masterset.add)
                    if not loadSetIsSuperset(masterset):
                        # Filtered out, discard this record and skip to next
                        setattr(src_block, single_attr, None)
                        continue
                # In IIM, skip all merging (duh)
                if not iiSkipMerge:
                    # We're past all hurdles - stick a copy of this record into
                    # ourselves and mark it as merged
                    self._validate(single_attr, src_rec)
                    mergeIdsAdd(src_rec.fid)
                    setattr(self, single_attr, src_rec.getTypeCopy())
        for gt, block_mob in src_block._mob_objects.items():
            self._mob_objects[gt].merge_records(block_mob, loadSet, mergeIds,
                                                iiSkipMerge, doFilter)

    def _validate(self, single_attr, src_rec): pass ## todo just for WRLD...?

    def updateRecords(self, srcBlock, mergeIds):
        for chg in self._mob_objects.values():
            chg.updateRecords(srcBlock, mergeIds)
        for att in srcBlock._extra_records.values():
            if (rec := getattr(srcBlock, att)) and not rec.flags1.ignored:
                setattr(self, att, rec.getTypeCopy())
                mergeIds.discard(rec.fid)

    def keepRecords(self, p_keep_ids):
        for chg in self._mob_objects.values():
            chg.keepRecords(p_keep_ids)
        for att in self._extra_records.values():
            if (rec := getattr(self, att)) and rec.group_key() not in p_keep_ids:
                setattr(self, att, None)

    def _load_rec_group(self, ins, endPos, master_rec=None):
        """Loads data from input stream. Called by load()."""
        insAtEnd = ins.atEnd
        errLabel = f'{self}'
        subgroups_loaded = set()
        while not insAtEnd(endPos, errLabel):
            #--Get record info and handle it
            header = unpack_header(ins)
            if (head_sig := header.recType) in self._extra_records:
                rec_name = self._extra_records[head_sig]
                if getattr(self, rec_name) is not None:
                    if head_sig == self._top_type: # next record
                        ins.rewind()
                        break
                    self._load_err(f'Duplicate {rec_name}')
                grel = self._group_element(header, ins)
                if grel: setattr(self, rec_name, grel)
                else: header.skip_blob(ins)
            elif head_sig == b'GRUP':
                if (gt := header.groupType) in self._marker_groups:
                    ins.rewind() # either next Top Grup or a cell block header
                    break
                if gt in subgroups_loaded:
                    self._load_err(f'Duplicate subgroup type {gt} in {self}')
                self._load_mobs(gt, header, ins, master_rec)
                subgroups_loaded.add(gt)
            else:
                self._load_err(f'Unexpected {sig_to_str(head_sig)} record in '
                               f'{self} group.')
        self.setChanged()

    def _load_mobs(self, gt, header, ins, master_rec):
        try:
            self._mob_objects[gt] = self._mob_objects_type[gt](header,
                self.loadFactory, ins, do_unpack=True, master_rec=master_rec)
        except KeyError:
            self._load_err(f'Sub {gt} in {self}')

    def _group_element(self, header, ins, do_unpack=True) -> 'MreRecord':
        rec_class = self.loadFactory.sig_to_type[header.recType]
        return None if rec_class is None else rec_class(header, ins,
                                                        do_unpack=do_unpack)

    def dump(self, out):
        for r in self._stray_recs().values():
            r.dump(out)
        for m in self._mob_objects.values():
            m.dump(out)

    def _stray_recs(self):
        return {att: rec for att in self._extra_records.values() if
                (rec := getattr(self, att, None))}

def _process_rec(sig, after=True, target=None):
    """Hack to do some processing before or after calling super method omitting
    the processed signature (or self._top_grup). Must only be used *once*
    per method override chain (else RecursionError). If we do the processing
    before, and it returns falsy, super won't be called."""
    def _exclude_rec(meth):
        @wraps(meth)
        def _call_super(self, *args, **kwargs):
            if not after:
                if not meth(self, *args, **kwargs): # don't call super
                    return
            target_ = self if target is None else args[target]
            old = getattr(target_, '_extra_records')
            recs = dict(old)
            try:
                del old[self._top_type if sig is None else sig]
                # we decorate the final method in the inheritance chain, and we
                # want to call the immediate ancestor - get that
                parent_function = [f for t in type(self).__mro__ if
                                   (f := t.__dict__.get(meth.__name__))][1]
                parent_function(self, *args, **kwargs)
            finally:
                setattr(target_, '_extra_records', {**recs, **old})
            # Now execute the logic for the excluded record
            if after: meth(self, *args, **kwargs)
        return _call_super
    return _exclude_rec

class _ComplexRec(_Nested):
    """Itself a collection of records - a required record, and an optional
    ChildrenGrup that might be simple or complex (as for CellChildren)."""

    @property
    def master_record(self):
        """The master CELL, WRLD or DIAL record."""
        return getattr(self, self._extra_records[self._top_type])

    @master_record.setter
    def master_record(self, rec):
        setattr(self, self._extra_records[self._top_type], rec)

    def group_key(self): return self.master_record.group_key()

    def _set_mob_objects(self, head_label=None):
        super()._set_mob_objects(self.master_record and self.master_record.group_key())

    def _load_rec_group(self, ins, endPos, master_rec=None):
        """Loads data from input stream. Called by load()."""
        if ins.atEnd(endPos, f'{self}'): return # empty top level group?
        header = unpack_header(ins)
        if self._top_type != (hsig := header.recType): # first record required
            if hsig == b'GRUP' and header.groupType == MobWorld._grp_key and \
                    _loaded_world_records is not None:
                if prev_wrld := _loaded_world_records.get(header.label):
                    super(_ComplexRec, prev_wrld)._load_rec_group(
                        ins, endPos, prev_wrld.master_record)
                    return
                header.skip_blob()
                global _orphans_skipped
                _orphans_skipped += 1
                return
            self._load_err(f'Missing {self._extra_records[self._top_type]} '
                           f'from {self}')
        recClass = self.loadFactory.sig_to_type[hsig]
        self.master_record = recClass(header, ins, do_unpack=True)
        if _loaded_world_records is not None:
            _loaded_world_records[self.master_record.group_key()] = self
        super()._load_rec_group(ins, endPos, self.master_record)

    @_process_rec(None)
    def keepRecords(self, p_keep_ids):
        if mr_rec := self.master_record:
            # Get rid of the master record and look for children
            self.master_record = None
            any_children_kept = any(self.iter_records())
            if any_children_kept or mr_rec.group_key() in p_keep_ids:
                # Either we want to keep the master record or at least one of
                # its children, so restore the master record and keep it if it
                # isn't already kept. Otherwise, just don't undo the master
                # record deletion from before
                p_keep_ids.add(mr_rec.group_key())
                self.master_record = mr_rec

    @_process_rec(None, after=False, target=0)
    def updateRecords(self, srcBlock, mergeIds):
        src_dial = srcBlock.master_record
        # Copy the latest version of the master record over. We can safely mark
        # it as not merged because keepRecords above ensures that we never
        # discard a master record when it still has children
        if not src_dial.flags1.ignored:
            self.master_record = src_dial.getTypeCopy()
            mergeIds.discard(src_dial.fid)
            return True # call super

    @_process_rec(None, after=False)
    def merge_records(self, src_block, loadSet, mergeIds, iiSkipMerge, doFilter):
        from ..mod_files import MasterSet # YUCK
        mergeIdsAdd = mergeIds.add
        loadSetIsSuperset = loadSet.issuperset
        # First, check the main DIAL record
        src_rec = src_block.master_record
        if not src_rec.flags1.ignored:
            # If we're Filter-tagged, perform merge filtering first
            if doFilter:
                src_rec.mergeFilter(loadSet)
                masterset = MasterSet()
                src_rec.updateMasters(masterset.add)
                if not loadSetIsSuperset(masterset):
                    # Filtered out, discard this DIAL record (and, by
                    # extension, all its INFO children)
                    self.master_record = None # will drop us from MobDials
                    return
            # In IIM, we can't just return here since we also need to filter
            # the children that came with this complex record
            if not iiSkipMerge:
                # We're past all hurdles - mark the record as merged, and stick
                # a copy into ourselves
                mergeIdsAdd(src_rec.fid)
                self.master_record = src_rec.getTypeCopy()
            # Now we're ready to filter and merge the children
            return True

    def __str__(self):
        return f'{sig_to_str(self._top_type)} Record'
        ## self.master_record.fid blows as record is None on loading
        ## AttributeError: 'NoneType' object has no attribute 'fid'

    def __repr__(self):
        rec_children = f'{self._mob_objects!r}' if any(
            self._mob_objects.values()) else "No children"
        return f'<{self}: {self.master_record!r}: {rec_children}>'

class TopGrup(MobObjects):
    """Represents a top level group with simple records. I.e. all top groups
    except CELL, WRLD and DIAL."""
    _grup_header_type = TopGrupHeader

    def __init__(self, header, loadFactory, ins=None, do_unpack=False):
        self._accepted_sigs = {header.label} # needed in _load_rec_group
        super().__init__(header, loadFactory, ins, do_unpack)

    def get_all_signatures(self):
        return self._accepted_sigs if self else set()

    @classmethod
    def empty_mob(cls, load_f, head_label, *head_arg):
        """Get an empty MobObjects collection to use in merge_records etc."""
        head = cls._grup_header_type(0, head_label, *head_arg)
        mob = cls(head, load_f)
        mob.setChanged()
        return mob

    def __str__(self):
        return f'{sig_to_str(self.header.label)} {super().__str__()}'

class TopComplexGrup(TopGrup):
    """CELL, WRLD and DIAL."""
    _top_rec_class: type[_ComplexRec] = None

    def get_all_signatures(self):
        return {*chain(
            *(r.get_all_signatures() for r in self.id_records.values()))}

    def _group_element(self, header, ins, do_unpack=True, **kwargs) -> _ComplexRec:
        return self._top_rec_class(self.loadFactory, ins, **kwargs)

    def getActiveRecords(self, rec_sig=None):
        """Returns non-ignored records - XXX what about isKeyedByEid?"""
        if rec_sig is None: # iterate our top record blocks
            return [(k, r) for k, r in self.id_records.items() if
                    not r.master_record.flags1.ignored]
        # iterate all records - top or nested - keeping rec_sig ones
        return [(r.group_key(), r) for r in self.iter_records() if
                r._rec_sig == rec_sig and not r.flags1.ignored]

    def getNumRecords(self,includeGroups=True):
        """Returns number of records, including self - if empty return 0."""
        if not self: return 0
        num_recs = sum(r.getNumRecords(includeGroups) for r in
                       self.id_records.values()) + includeGroups #--Count self
        self.numRecords = num_recs
        return num_recs

    def getSize(self):
        """Returns size (including size of any group headers)."""
        if not self.changed:
            return self.size
        else:
            if not self.id_records: return 0
            recs_size = sum((r.getSize()) for r in self.id_records.values())
            # add hsize for the GRUP header
            return RecordHeader.rec_header_size + recs_size

    def iter_records(self):
        return chain(*(d.iter_records() for d in self.id_records.values()))

    def setRecord(self, block, do_copy=True, _loading=False):
        """Adds the specified complex record to self, overriding an existing
        one with the same FormID or creating a new complex record block."""
        if isinstance(block, MelRecord):
            # it's the block's master record (needed for _merge_records)
            if not _loading and do_copy:
                block = block.getTypeCopy()
            master_rec = block
            block = self._group_element(None, ins=None, **{ # the master record
                sig_to_str(master_rec._rec_sig).lower(): master_rec})
            block.setChanged()
        grel_key = block.group_key()
        if grel_key in self.id_records:
            if _loading:
                self._load_err(f'Duplicate {grel_key} record in {self}')
            self.id_records[grel_key].master_record = block.master_record
        else:
            self.id_records[grel_key] = block
        return self.id_records[grel_key] # complex records: return this back

    def keepRecords(self, p_keep_ids):
        for complex_rec in self.id_records.values():
            complex_rec.keepRecords(p_keep_ids)
        # loop above may set complex_rec.master_record to None
        self.id_records = {k: d for k, d in self.id_records.items() if
                           d.master_record is not None}
        self.setChanged()

    def updateRecords(self, srcBlock, mergeIds):
        lookup_dial = self.id_records.get
        for dfid, src_dial in srcBlock.id_records.items():
            # Check if we have a corresponding DIAL record in the destination
            dest_dial = lookup_dial(dfid)
            if dest_dial:
                dest_dial.updateRecords(src_dial, mergeIds)

    def merge_records(self, block, loadSet, mergeIds, iiSkipMerge, doFilter):
        from ..mod_files import MasterSet # YUCK
        lookup_dial = self.id_records.get
        filtered_dials = {}
        loadSetIsSuperset = loadSet.issuperset
        for src_fid, src_dialogue in block.id_records.items():
            # Check if we already have a dialogue with that FormID
            dest_dialogue = lookup_dial(src_fid)
            if was_newly_added := not dest_dialogue:
                # We do not, add it and get it - will typeCopy the rec
                dest_dialogue = self.setRecord(src_dialogue.master_record)
            # Delegate merging to the (potentially newly added) child dialogue
            dest_dialogue.merge_records(src_dialogue, loadSet, mergeIds,
                iiSkipMerge, doFilter)
            # In IIM, skip all merging - note that we need to remove the child
            # dialogue again if it was newly added in IIM mode.
            if iiSkipMerge:
                if was_newly_added:
                    del self.id_records[dest_dialogue.group_key()]
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
                        del self.id_records[dest_dialogue.group_key()]
                    continue
            # We're either not Filter-tagged or we want to keep this dialogue
            filtered_dials[src_fid] = src_dialogue
        # Apply any merge filtering we've done above to the record block
        block.id_records = filtered_dials

#------------------------------------------------------------------------------
class MobDial(_ComplexRec):
    """A single DIAL with INFO children."""
    _extra_records = {b'DIAL': 'dial'}
    _top_type = b'DIAL'

    class _DialChildren(_ChildrenGrup):
        _accepted_sigs = {b'INFO'}
        _children_grup_type = 7
        _stamp2 = 0

        def _write_header(self, out):
            # TODO(ut) why? what about other children grups?
            self.header.extra = self._stamp2
            super()._write_header(out)

        def _sort_group(self):
            """Sorts the INFOs of this DIAL record by their (PNAM) Previous
            Info. These do not simply describe a linear list, but a directed
            graph - e.g. you can have edges B->A and C->A, which would leave
            both C->B->A and B->C->A as valid orders. To decide in such
            cases, we stick with whatever the previous order was.

            Note: We assume the PNAM graph is acyclic - cyclic graphs are
            errors in plugins anyways, so the behavior of PBash when
            encountering such errors is undefined."""
            # First gather a list of all 'orphans', i.e. INFOs that have no
            # PNAM. We'll start with these and insert non-orphans into the
            # list at the right spot based on their PNAM
            sorted_infos = []
            remaining_infos = deque()
            for r in self.iter_records():
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
                    ##: This isn't wholly correct - really, we'd have to
                    # check for cycles and missing FIDs here, then behave as
                    # follows:
                    #  - missing PNAM FID: Exactly like right now, append to
                    #    sorted
                    #  - cycle: raise error/deprint
                    #  - otherwise: re-appendleft the FID again, keep going
                    #    until we've added its PNAM
                    if curr_info.fid in visited_fids:
                        # Either the PNAM points to a record that's not in our
                        # file (which is fine and happens all the time),
                        # or this INFO is in a cycle, or the PNAM points to
                        # a non-existent record.
                        # To handle this situation, we simply append it to the
                        # end of our sorted INFOs.
                        # We don't warn here because trying to differentiate
                        # the valid and common case from the two error cases
                        # would be too slow. xEdit can do this much better.
                        sorted_infos.append(curr_info)
                    else:
                        # We'll have to revisit this INFO later when its
                        # PNAM may have been added, so move it to the end (
                        # == left side) of the queue
                        visited_fids.add(curr_info.fid)
                        remaining_infos.appendleft(curr_info)
            self.id_records = {rec.fid: rec for rec in sorted_infos}
    _mob_objects_type = {_DialChildren._children_grup_type: _DialChildren}

    def dump(self, out):
        # Update TIFC if needed (i.e. Skyrim+)
        if hasattr(mr := self.master_record, 'info_count'):
            mr.info_count = len(self._mob_objects[7].id_records)
        super().dump(out)

    def set_stamp(self, val):
        self._mob_objects[7].header.stamp = val

class MobDials(TopComplexGrup):
    """DIAL top block of mod file."""
    _top_rec_class = MobDial

    def getSize(self):
        """Patch _mob_objects (INFO) headers are created with 0 stamp - I
        repeated here what the old code did, but we should check."""
        for dialogue in self.id_records.values():
            dialogue.set_stamp(self.header.stamp)
        return super().getSize()

#------------------------------------------------------------------------------
class _CellRefs(_ChildrenGrup):
    """Cell reference children groups."""
    @fast_cached_property
    def _accepted_sigs(self): return RecordType.sig_to_class[b'CELL'].ref_types

class _PersRefs(_CellRefs):
    _children_grup_type = 8
class _TempRefs(_CellRefs):
    _children_grup_type = 9
    @fast_cached_property
    def _accepted_sigs(self):
        return {*RecordType.sig_to_class[b'CELL'].ref_types, b'PGRD'}
class _DistRefs(_CellRefs):
    _children_grup_type = 10

class _CellChildren(_Nested, _ChildrenGrup):
    """The notorious group 6. It's a _ChildrenGrup that is-a _Nested group
    instead of a MobObjects."""
    _top_type = b'CELL'
    _mob_objects_type = {cl._children_grup_type: cl for cl in
                         (_PersRefs, _TempRefs, _DistRefs)}
    _mob_objects: dict[int, _CellRefs]
    _children_grup_type = 6
    @fast_cached_property
    def _accepted_sigs(self):
        # needed in childrenGrup ## TODO define statically in _validate_records
        return {*RecordType.sig_to_class[b'CELL'].ref_types, b'PGRD'}

    # todo do_unpack handling (and rename -> data -> _grup_blob)
    def __init__(self, grup_head, loadFactory, ins=None, do_unpack=False,
                 master_rec=None):
        # Initialize the _Nested attributes that _load_rec_group relies on
        for att in self._extra_records.values():
            setattr(self, att, None)
        # _mob_objects is now a dict as we have multiple children
        self._mob_objects = {}
        # then load as a MobBase to handle the header and specify endPos
        super(_Nested, self).__init__(grup_head, loadFactory, ins, do_unpack,
                                      master_rec)
        self._set_mob_objects(grup_head.label)

    def getSize(self):
        gsize = super().getSize()
        if gsize:
            gsize += RecordHeader.rec_header_size # the children group header
        return gsize

    def getNumRecords(self,includeGroups=True):
        nrecs = super().getNumRecords(includeGroups)
        if includeGroups and nrecs: # no records => no top or nested groups
            nrecs += 1 # 1 for the group 6 header
        return nrecs

    def iter_records(self):
        recs = (rec for att in self._extra_records.values() if
                (rec := getattr(self, att)))
        mo = lambda gt: self._mob_objects[gt].iter_records()
        return chain(mo(8), recs, mo(9), mo(10))

    def __bool__(self): return any(self.iter_records())

    def dump(self,out):
        # TODO(ut) validate order
        extra_recs = (getattr(self, att) for att in
                      self._extra_records.values())
        mget = self._mob_objects.get # for wrapping don't remove inline :P
        subs = [m for m in (mget(8), *extra_recs, mget(10), mget(9)) if m]
        if subs:
            self._write_header(out)
            for sub in subs:
                sub.dump(out)

    def updateRecords(self, srcBlock, mergeIds):
        for gt, chg in self._mob_objects.items():
            chg.updateRecords(srcBlock._mob_objects[gt], mergeIds)
        for att in srcBlock._extra_records.values():
            todo_why_we_check = getattr(self, att) # todo why_we_check
            if todo_why_we_check and (record := getattr(srcBlock, att)):
                self._validate(att, record)
                if not record.flags1.ignored:
                    setattr(self, att, record.getTypeCopy())
                    mergeIds.discard(record.fid)

    def __repr__(self):
        s = []
        for att in self._mob_objects.values():
            if att: s.append(f'{att!r}')
        for k, att in self._extra_records.items():
            k = sig_to_str(k)
            s.append(f'{k}: {rec!r}' if (
                rec := getattr(self, att)) else f"no '{att}'")
        children = ', '.join(s) if s else 'No children'
        return f'<{self}: {self._accepted_sigs}: {children}'

class MobCell(_ComplexRec):
    """Represents cell block structure -- including the cell and all
    subrecords."""
    _extra_records = {b'CELL': 'cell'}
    _top_type = b'CELL'
    _mob_objects_type = {6: _CellChildren}
    _mob_objects: dict[int, _CellChildren]
    block_types = 2, 3
    _marker_groups = {0, *block_types}

    def dump(self,out):
        for k,v in self._extra_records.items():
            if rec := getattr(self, v, None): rec.dump(out)
        self._mob_objects[6].dump(out)

    # Old API ##: we should eliminate this
    @property
    def persistent_refs(self):
        return self._mob_objects[6]._mob_objects[8]

    @property
    def temp_refs(self):
        return self._mob_objects[6]._mob_objects[9]

#------------------------------------------------------------------------------
class MobCells(MobObjects):
    """A block containing cells. It's an anomalous MobObjects, as it may not
    have a header (exterior WRLD cells) - WIP

    Note that "blocks" here only roughly match the file block structure.

    "Bsb" is a tuple of the file (block,subblock) labels. For interior
    cells, bsbs are tuples of two numbers, while for exterior cells, bsb labels
    are tuples of grid tuples."""
    _block_type, _subblock_type = -1, -1
    _cell_type = MobCell

    def __init__(self, header, loadFactory, ins=None, do_unpack=False,
                 endPos=_EOF):
        if header is None:
            self.id_records = {}
            super(MobBase, self).__init__(loadFactory, ins, endPos)
        else: # MobICells
            super().__init__(header, loadFactory, ins, do_unpack)

    def getNumRecords(self, includeGroups=True, *,
                      __get_cell=attrgetter_cache['master_record']):
        """Returns number of records, including self and all children."""
        count = sum(
            r.getNumRecords(includeGroups) for r in self.id_records.values())
        if count and includeGroups:
            blocks_bsbs = {__get_cell(cell_block).getBsb() for cell_block in
                           self.id_records.values()}
            # 1 GRUP header for each separate subblock and one for every block
            count += len(blocks_bsbs) + len({x1[0] for x1 in blocks_bsbs})
        return count

    def _group_element(self, header, ins, end_pos=None, do_unpack=True, **kwargs) -> _cell_type:
        return self._cell_type(self.loadFactory, ins, end_pos, **kwargs)

    def getSize(self):
        """Return the total size of the block, but also compute dictionaries
        containing the sizes of the individual blocks/subblocks and the cell
        ids every block contains."""
        if not self.changed:
            return self.size
        self.size = 0
        self._block_subblock_cells = defaultdict(lambda: defaultdict(list))
        hsize = RecordHeader.rec_header_size # add the size of subblock header
        self._block_subblock_sizes = defaultdict(
            lambda: defaultdict(lambda: hsize))
        for cell_rid, mob_cell in self.id_records.items():
            block, subblock = mob_cell.master_record.getBsb()
            cell_size = mob_cell.getSize()
            self._block_subblock_sizes[block][subblock] += cell_size
            self._block_subblock_cells[block][subblock].append(cell_rid)
        # sum sublock sizes to get the block size (+ hsize for block header)
        self._block_sizes = defaultdict(lambda: hsize)
        for block, subs_sizes in self._block_subblock_cells.items():
            bsize = sum(self._block_subblock_sizes[block].values())
            self._block_sizes[block] += bsize # includes the sizes of headers
            self.size += self._block_sizes[block]
        # self.setChanged(False) ## FIXME revisit all setChanged machinery
        return self.size

    def _load_rec_group(self, ins, endPos):
        """Loads data from input stream. Called by load()."""
        endBlockPos = endSubblockPos = 0
        insAtEnd = ins.atEnd
        insTell = ins.tell
        while not insAtEnd(endPos, f'{self}'):
            header = unpack_header(ins)
            _rsig = header.recType
            if _rsig == b'CELL':
                cell = self._group_element(self.loadFactory, ins, endPos)
                if endBlockPos and ((pos := insTell()) > endBlockPos or
                                    pos > endSubblockPos):
                    self._load_err(f'{cell.master_record!r} outside of block '
                                   f'or subblock.')
                self.setRecord(cell, _loading=True)
            elif _rsig == b'GRUP':
                gt = header.groupType
                if gt == self._block_type: # Block number
                    endBlockPos = insTell() + header.blob_size()
                elif gt == self._subblock_type: # Sub-block number
                    endSubblockPos = insTell() + header.blob_size()
                else:
                    self._load_err(f'Unexpected subgroup {gt:d} in '
                                   f'{self} group.')
            else:
                self._load_err(f'Unexpected {sig_to_str(_rsig)} record in '
                               f'{self} group.')
        self.setChanged()

    def _sort_group(self):
        """First sort by the block they belong to, then by the CELL FormID."""
        self._block_subblock_cells = {
            block: {k: sorted(v) for k, v in dict_sort(subblock_dict)} for
            (block, subblock_dict) in dict_sort(self._block_subblock_cells)}

    def dumpBlocks(self, out):
        """Dumps the cell blocks and their block and sub-block groups to
        out."""
        bsb_size = self._block_sizes
        # _ExteriorCells have no grup header - so what is stamp here?
        head_st = self.header.stamp if self._grup_header_type else 0
        outWrite = out.write
        for block, subs_sizes in self._block_subblock_cells.items():
            # Write the block header
            outWrite(self._block_header_type(bsb_size[block], block,
                self._block_type, head_st).pack_head())
            subs_size = self._block_subblock_sizes[block]
            for sub, mob_cells in subs_sizes.items():
                outWrite(self._block_header_type(subs_size[sub], sub,
                    self._subblock_type, head_st).pack_head())
                for cfid in mob_cells:
                    self.id_records[cfid].dump(out)

    def dump(self,out):
        """Dumps group header and then records."""
        # if not self.changed:
        #     out.write(self.header.pack_head())
        #     out.write(self.data)
        if self.id_records:
            self.header.size = self.getSize()
            out.write(self.header.pack_head())
            self._sort_group()
            self.dumpBlocks(out)

#------------------------------------------------------------------------------
class MobICells(MobCells, TopComplexGrup):
    """Tes4 top block for interior cell records."""
    _top_rec_class = MobCell
    _block_type, _subblock_type = MobCell.block_types
    _block_header_type = GrupHeader

    def getNumRecords(self, includeGroups=True):
        count = super().getNumRecords(includeGroups)
        return (count + 1) if count else 0

    def getSize(self):
        count = super().getSize()
        return (count + RecordHeader.rec_header_size) if count else 0

#------------------------------------------------------------------------------
class _WrldTempRefs(_TempRefs):
    @fast_cached_property
    def _accepted_sigs(self):
        return {*RecordType.sig_to_class[b'CELL'].ref_types, b'PGRD', b'LAND'}

class _ExtCellChildren(_CellChildren):
    _top_type = b'CELL' # these are part of an WRLD record
    _mob_objects_type = {cl._children_grup_type: cl for cl in
                         (_PersRefs, _WrldTempRefs, _DistRefs)}
    @fast_cached_property
    def _accepted_sigs(self):
        return {*RecordType.sig_to_class[b'CELL'].ref_types, b'PGRD', b'LAND'}

class _ExtCell(MobCell):
    _mob_objects_type = {6: _ExtCellChildren}
    block_types = 4, 5
    _marker_groups = {0, *block_types}

    def __repr__(self): return f'ExteriorCell'

class _ExteriorCells(MobCells):
    """No header MobObjects containing cells divided in blocks/subblocks."""
    _grup_header_type = None
    _block_type, _subblock_type = _ExtCell.block_types
    _block_header_type = ExteriorGrupHeader
    _cell_type = _ExtCell

    # maybe _ExteriorCells is-a TopComplexGrup? then we need to track overrides
    # that need to delegate to MobObjects - wait till we further thin base API
    def iter_records(self):
        return TopComplexGrup.iter_records(self)

    def get_all_signatures(self):
        return TopComplexGrup.get_all_signatures(self)

    def keepRecords(self, p_keep_ids):
        return TopComplexGrup.keepRecords(self, p_keep_ids)

    def getActiveRecords(self, rec_sig=None):
        return TopComplexGrup.getActiveRecords(self, rec_sig)

    def setRecord(self, block, do_copy=True, _loading=False):
        """We want to get a block here not a mere record."""
        return TopComplexGrup.setRecord(self, block, do_copy, _loading)

    @classmethod
    def empty_mob(cls, load_f, head_label, *head_arg):
        """_ExteriorCells is a header-less group."""
        mob = cls(None, load_f)
        mob.setChanged()
        return mob

    def dump(self,out):
        """Dumps group header and then records."""
        # if not self.changed:
        #     out.write(self.header.pack_head())
        #     out.write(self.data)
        if self.id_records:
            self.getSize() # populate the block data structures
            self._sort_group()
            self.dumpBlocks(out)

    def __str__(self): return f'Exterior Cells' # todo add the WRLD info

class _PersistentCell(MobCell):
    _marker_groups = {0, 4} # we get a group 4 of exterior cells right after

class _WorldChildren(_CellChildren):
    ##: rename to e.g. persistent_block, this is the cell block that houses all
    # persistent objects in the worldspace
    _extra_records = {b'ROAD': 'road', b'CELL': 'worldCellBlock'}
    _top_type = b'WRLD'
    _mob_objects_type = {4: _ExteriorCells} # we hit a 4 type block
    _mob_objects: dict[int, _ExteriorCells]
    worldCellBlock: _PersistentCell
    _children_grup_type = 1

    @fast_cached_property
    def _accepted_sigs(self):
        return {*RecordType.sig_to_class[b'CELL'].ref_types, b'PGRD', b'LAND',
                *self._extra_records}

    def _load_mobs(self, gt, header, ins, master_rec):
        try:
            ins.rewind() # to reread first block header
            self._mob_objects[gt] = self._mob_objects_type[gt](None,
                self.loadFactory, ins, do_unpack=True, endPos=self._end_pos)
        except KeyError:
            self._load_err(f'Sub {gt} in {self}')

    def _group_element(self, header, ins, do_unpack=True) -> 'MreRecord':
        if header.recType == b'CELL': # loading the persistent Cell
            # will rewind to reread the header in _Nested.__init__
            rec = _PersistentCell(self.loadFactory, ins, self._end_pos)
            if rec.master_record and not rec.master_record.flags1.persistent:
                self._load_err(f'Misplaced exterior cell '
                               f'{rec.master_record!r}.')
        else: rec = super()._group_element(header, ins, do_unpack)
        return rec

    ##: special cases below are too special
    def _not_dummy(self): ## FIXME do we need this?
        return (pcell := self.worldCellBlock) and (
            pcell if pcell.master_record else None)

    def iter_records(self):
        if self.road:
            yield self.road
        pcell = self._not_dummy()
        cell_recs = pcell.iter_records() if pcell else ()
        yield from chain(cell_recs, self._mob_objects[4].iter_records())

    def getNumRecords(self,includeGroups=True):
        nrecs = 1 if self.road else 0
        nrecs += self._mob_objects[4].getNumRecords(includeGroups)
        if pcell := self._not_dummy():
            nrecs += pcell.getNumRecords(includeGroups)
        if includeGroups and nrecs: # no records => no top or nested groups
            nrecs += 1 # 1 for the group 6 header
        return nrecs

    @_process_rec(b'CELL', target=0)
    def updateRecords(self, srcBlock, mergeIds):
        # FIXME update recs for worldCellBlock - correct?
        if pcell := self._not_dummy():
            if src_cell := srcBlock._not_dummy():
                pcell.updateRecords(src_cell, mergeIds)

    @_process_rec(b'CELL')
    def merge_records(self, src_block, loadSet, mergeIds, iiSkipMerge, doFilter):
        from ..mod_files import MasterSet  # YUCK
        # mergeIdsAdd = mergeIds.add
        loadSetIsSuperset = loadSet.issuperset
        if src_cell := src_block._not_dummy():
            # If we don't have a world cell block yet, make a new one to merge
            # the source's world cell block into
            if was_newly_added := not self.worldCellBlock:
                self.worldCellBlock = _PersistentCell(self.loadFactory, None,
                                                      cell=None)
            # Delegate merging to the (potentially newly added) block
            self.worldCellBlock.merge_records(src_cell, loadSet,
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

    def _validate(self, single_attr, src_rec):
        dest_rec = getattr(self, single_attr)
        ##: This may be wrong, check if ROAD behaves like PGRD/LAND
        if dest_rec and dest_rec.fid != src_rec.fid:
            raise ModFidMismatchError(self.inName, dest_rec.rec_str,
                                      dest_rec.fid, src_rec.fid)

    @_process_rec(b'CELL', after=False)
    def keepRecords(self, p_keep_ids):
        if pcell := self._not_dummy():
            pcell.keepRecords(p_keep_ids)
            if pcell.master_record.fid not in p_keep_ids:
                self.worldCellBlock = None
        return True # keepRecords for the rest of WRLD children

    def set_cell(self, cell_rec):
        """Updates the persistent CELL block to use a copy of the specified
        CELL or creates a new persistent CELL block if one does not already
        exist in this world."""
        if cell_rec.flags.isInterior:
            cell_copy = cell_rec.getTypeCopy()
            if self.worldCellBlock:
                self.worldCellBlock.master_record = cell_copy
            else:
                new_pers_block = _PersistentCell(self.loadFactory, None,
                                                 cell=cell_copy)
                new_pers_block.setChanged()
                self.worldCellBlock = new_pers_block
        else: # exterior cell - will copy it - previous behavior
            self._mob_objects[4].setRecord(cell_rec) #, do_copy=False?

    def dump(self, out):
        # TODO(ut) validate order
        extra_recs = (getattr(self, att) for att in
                      self._extra_records.values())
        subs = [m for m in (*extra_recs, self._mob_objects[4]) if m]
        if subs:
            self._write_header(out)
            for sub in subs:
                sub.dump(out)

class MobWorld(_ComplexRec):
    _extra_records = {b'WRLD': 'wrld'}
    _top_type = b'WRLD'
    _grp_key = 1
    _mob_objects_type = {_grp_key: _WorldChildren}
    _mob_objects: dict[int, _WorldChildren]

    def _load_mobs(self, gt, header, ins, master_rec):
        if gt == self._grp_key: # if != 1 let it blow with a KeyError
            header_fid = header.label
            if header_fid != master_rec.fid:
                if _loaded_world_records is not None and (
                        wrld_block := _loaded_world_records.get(header_fid)):
                    super(MobWorld, wrld_block)._load_mobs(
                        gt, header, ins, wrld_block.master_record)
                    return
                header.skip_blob()
                global _orphans_skipped
                _orphans_skipped += 1
                return
        super()._load_mobs(gt, header, ins, master_rec)

    def get_cells(self):
        return self._mob_objects[self._grp_key].iter_present_records(b'CELL')

    def set_cell(self, cell_rec):
        self._mob_objects[self._grp_key].set_cell(cell_rec)

    @property
    def ext_cells(self):
        return self._mob_objects[self._grp_key]._mob_objects[4]

#------------------------------------------------------------------------------
# In a scenario where we have [wrld_rec1, wrld_rec2, wrld_children1,
# wrld_children3, wrld_rec3, ...], it seems that the game can attach a world
# (also cell?) children group to a previously loaded WRLD record - so in this
# case wrld_children3 is marked as orphaned but wrld_children1 is read normally
_loaded_world_records: dict[FormId, MobWorld] = {}
_orphans_skipped = 0
class MobWorlds(TopComplexGrup):
    """Tes4 top block for world records and related roads and cells. Consists
    of world blocks."""
    _top_rec_class = MobWorld

    def __init__(self, header, loadFactory, ins=None, do_unpack=False):
        global _orphans_skipped, _loaded_world_records # reset the globals
        _loaded_world_records = {}
        self.orphansSkipped = _orphans_skipped = 0
        super().__init__(header, loadFactory, ins, do_unpack)
        self.orphansSkipped = _orphans_skipped
