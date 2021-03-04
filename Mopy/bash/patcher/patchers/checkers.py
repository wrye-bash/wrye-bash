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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module houses checkers. A checker is a patcher that verifies certain
properties about records and either notifies the user or attempts a fix when it
notices a problem."""

from collections import defaultdict
from itertools import chain
# Internal
from ..base import Patcher
from ... import bush

class ContentsCheckerPatcher(Patcher):
    """Checks contents of leveled lists, inventories and containers for
    correct content types."""
    patcher_group = u'Special'
    patcher_order = 50
    contType_entryTypes = bush.game.cc_valid_types
    contTypes = set(contType_entryTypes)
    entryTypes = set(chain.from_iterable(contType_entryTypes.itervalues()))
    _read_sigs = tuple(contTypes | entryTypes)

    def __init__(self, p_name, p_file):
        super(ContentsCheckerPatcher, self).__init__(p_name, p_file)
        self.fid_to_type = {}
        self.id_eid = {}

    @property
    def active_write_sigs(self):
        return tuple(self.contTypes) if self.isActive else ()

    def scanModFile(self, modFile, progress):
        """Scan modFile."""
        # First, map fids to record type for all records for the valid record
        # types. We need to know if a given fid belongs to one of the valid
        # types, otherwise we want to remove it.
        id_type = self.fid_to_type
        for entry_type in self.entryTypes:
            if entry_type not in modFile.tops: continue
            for record in modFile.tops[entry_type].getActiveRecords():
                fid = record.fid
                if fid not in id_type:
                    id_type[fid] = entry_type
        # Second, make sure the Bashed Patch contains all records for all the
        # types we may end up patching
        for cont_type in self.contTypes:
            if cont_type not in modFile.tops: continue
            patchBlock = self.patchFile.tops[cont_type]
            pb_add_record = patchBlock.setRecord
            id_records = patchBlock.id_records
            for record in modFile.tops[cont_type].getActiveRecords():
                if record.fid not in id_records:
                    pb_add_record(record.getTypeCopy())

    def buildPatch(self,log,progress):
        """Make changes to patchfile."""
        if not self.isActive: return
        modFile = self.patchFile
        keep = self.patchFile.getKeeper()
        fid_to_type = self.fid_to_type
        id_eid = self.id_eid
        log.setHeader(u'= ' + self._patcher_name)
        # Execute each pass - one pass is needed for every distinct record
        # class layout, e.g. leveled list classes generally share the same
        # layout (LVLI.entries[i].listId, LVLN.entries[i].listId, etc.)
        # whereas CONT, NPC_, etc. have a different layout (CONT.items[i].item,
        # NPC_.items[i].item)
        for cc_pass in bush.game.cc_passes:
            # Validate our pass syntax first
            if len(cc_pass) not in (2, 3):
                raise RuntimeError(u'Unknown Contents Checker pass type %r' %
                                   cc_pass)
            # See explanation below (entry_fid definition)
            needs_entry_attr = len(cc_pass) == 3
            # First entry in the pass is always the record types this pass
            # applies to
            for rec_type in cc_pass[0]:
                if rec_type not in modFile.tops: continue
                # Set up a dict to track which entries we have removed per fid
                id_removed = defaultdict(list)
                # Grab the types that are actually valid for our current record
                # types
                valid_types = set(self.contType_entryTypes[rec_type])
                for record in modFile.tops[rec_type].records:
                    group_attr = cc_pass[1]
                    # Set up two lists, one containing the current record
                    # contents, and a second one that we will be filling with
                    # only valid entries.
                    new_entries = []
                    current_entries = getattr(record, group_attr)
                    for entry in current_entries:
                        # If len(cc_pass) == 3, then this is a list of
                        # MelObject instances, so we have to take an additional
                        # step to retrieve the fids (e.g. for MelGroups or
                        # MelStructs)
                        entry_fid = getattr(entry, cc_pass[2]) \
                            if needs_entry_attr else entry
                        # Actually check if the fid has the correct type. If
                        # it's not valid, then this will return None, which is
                        # obviously not in the valid_types.
                        if fid_to_type.get(entry_fid, None) in valid_types:
                            # The type is valid, so grow our new list
                            new_entries.append(entry)
                        else:
                            # The type is wrong, so discard the entry. At this
                            # point, we know that the lists have diverged - but
                            # we need to keep going, there may be more invalid
                            # entries for this record.
                            id_removed[record.fid].append(entry_fid)
                            id_eid[record.fid] = record.eid
                    # Check if after filtering using the code above, our two
                    # lists have diverged and, if so, keep the changed record
                    if len(new_entries) != len(current_entries):
                        setattr(record, group_attr, new_entries)
                        keep(record.fid)
                # Log the result if we removed at least one entry
                if id_removed:
                    log(u'\n=== ' + rec_type)
                    for contId in sorted(id_removed):
                        log(u'* ' + id_eid[contId])
                        for removedId in sorted(id_removed[contId]):
                            log(u'  . %s: %06X' % (removedId[0],
                                                   removedId[1]))
