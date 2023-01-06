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
"""This module houses checkers. A checker is a patcher that verifies certain
properties about records and either notifies the user or attempts a fix when it
notices a problem."""

import random
import re
from collections import defaultdict, Counter
from itertools import chain

from .base import is_templated
from ..base import ModLoader, ScanPatcher
from ... import bush
from ...bolt import FName, dict_sort, sig_to_str
from ...brec import FormId
from ...mod_files import LoadFactory

class _Checker(ScanPatcher):
    """Common checkers code."""
    patcher_group = 'Special'
    patcher_order = 40

    def _add_to_patch(self, rid, record, top_sig):
        return rid not in self.patchFile.tops[top_sig].id_records

class ContentsCheckerPatcher(_Checker):
    """Checks contents of leveled lists, inventories and containers for
    correct content types."""
    patcher_order = 50
    contType_entryTypes = bush.game.cc_valid_types
    contTypes = set(contType_entryTypes)
    entryTypes = set(chain.from_iterable(contType_entryTypes.values()))
    _read_sigs = tuple(contTypes | entryTypes)

    def __init__(self, p_name, p_file):
        super(ContentsCheckerPatcher, self).__init__(p_name, p_file)
        self.fid_to_type = {}
        self.id_eid = {}

    @property
    def active_write_sigs(self):
        return tuple(self.contTypes) if self.isActive else ()

    def scanModFile(self, modFile, progress, scan_sigs=None):
        """Scan modFile."""
        # First, map fids to record type for all records for the valid record
        # types. We need to know if a given fid belongs to one of the valid
        # types, otherwise we want to remove it.
        id_type = self.fid_to_type
        for entry_type, block in modFile.iter_tops(self.entryTypes):
            for rid, _record in block.iter_present_records():
                if rid not in id_type:
                    id_type[rid] = entry_type
        # Second, make sure the Bashed Patch contains all records for all the
        # types we may end up patching
        super().scanModFile(modFile, progress, self.contTypes)

    def buildPatch(self,log,progress):
        """Make changes to patchfile."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        fid_to_type = self.fid_to_type
        id_eid = self.id_eid
        log.setHeader(f'= {self._patcher_name}')
        # Execute each pass - one pass is needed for every distinct record
        # class layout, e.g. leveled list classes generally share the same
        # layout (LVLI.entries[i].listId, LVLN.entries[i].listId, etc.)
        # whereas CONT, NPC_, etc. have a different layout (CONT.items[i].item,
        # NPC_.items[i].item)
        for cc_pass in bush.game.cc_passes:
            # Validate our pass syntax first
            if len(cc_pass) not in (2, 3):
                raise RuntimeError(
                    f'Unknown Contents Checker pass type {cc_pass!r}')
            # See explanation below (entry_fid definition)
            needs_entry_attr = len(cc_pass) == 3
            group_attr = cc_pass[1]
            entry_attr = cc_pass[2] if needs_entry_attr else None
            # First entry in the pass is always the record types this pass
            # applies to
            for rec_type, block in self.patchFile.iter_tops(cc_pass[0]):
                # Set up a dict to track which entries we have removed per fid
                id_removed = defaultdict(list)
                # Grab the types that are actually valid for our current record
                # types
                valid_types = set(self.contType_entryTypes[rec_type])
                for rid, record in block.id_records.items():
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
                        entry_fid = getattr(entry, entry_attr) \
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
                            id_removed[rid].append(entry_fid)
                            id_eid[rid] = record.eid
                    # Check if after filtering using the code above, our two
                    # lists have diverged and, if so, keep the changed record
                    if len(new_entries) != len(current_entries):
                        setattr(record, group_attr, new_entries)
                        keep(rid, record)
                # Log the result if we removed at least one entry
                if id_removed:
                    log(f'\n=== {sig_to_str(rec_type)}')
                    for contId in sorted(id_removed):
                        log(f'* {id_eid[contId]}')
                        for removedId in sorted(id_removed[contId]):
                            log(f'  . {removedId.mod_fn}: '
                                f'{removedId.object_dex:06X}')

#------------------------------------------------------------------------------
class RaceCheckerPatcher(_Checker): # patcher_order 40 to run after Tweak Races
    _read_sigs = (b'EYES', b'HAIR', b'RACE')

    def buildPatch(self, log, progress):
        if not self.isActive: return
        if b'RACE' not in self.patchFile.tops: return
        keep = self.patchFile.getKeeper()
        racesSorted = []
        eyeNames = {k: x.full for k, x in
                    self.patchFile.tops[b'EYES'].id_records.items()}
        hairNames = {k: x.full for k, x in
                     self.patchFile.tops[b'HAIR'].id_records.items()}
        skip_race_fid = bush.game.master_fid(0x038010)
        for rid, race in self.patchFile.tops[b'RACE'].id_records.items():
            if (race.flags.playable or rid == skip_race_fid) and race.eyes:
                prev_hairs = race.hairs[:]
                race.hairs.sort(key=lambda x: hairNames.get(x) or '')
                prev_eyes = race.eyes[:]
                race.eyes.sort(key=lambda x: eyeNames.get(x) or '')
                if race.hairs != prev_hairs or race.eyes != prev_eyes:
                    racesSorted.append(race.eid)
                    keep(rid, race)
        log.setHeader(f'= {self._patcher_name}')
        log(f'\n=== {_("Eyes/Hair Sorted")}')
        if not racesSorted:
            log(f'. ~~{_("None")}~~')
        else:
            for eid in sorted(racesSorted):
                log(f'* {eid}')

#------------------------------------------------------------------------------
def _find_vanilla_eyes():
    """Converts vanilla default_eyes to use long FormIDs and returns the
    result."""
    def _conv_fid(rc_fid):
        rc_file, rc_obj = rc_fid
        if rc_file is None: # special case: None = game master
            return bush.game.master_fid(rc_obj)
        return FormId.from_tuple((FName(rc_file), rc_obj))
    ret = {}
    for race_fid, race_eyes in bush.game.default_eyes.items():
        new_key = _conv_fid(race_fid)
        new_val = [_conv_fid(eye_fid) for eye_fid in race_eyes]
        ret[new_key] = new_val
    return ret

class NpcCheckerPatcher(_Checker):
    _read_sigs = (b'HAIR', b'NPC_', b'RACE')

    def __init__(self, p_name, p_file):
        super(NpcCheckerPatcher, self).__init__(p_name, p_file)
        self.vanilla_eyes = _find_vanilla_eyes()

    def buildPatch(self,log,progress):
        """Updates races as needed."""
        if not self.isActive: return
        patchFile = self.patchFile
        if not set(patchFile.tops) & {b'NPC_', b'RACE'}: return
        keep = patchFile.getKeeper()
        mod_npcsFixed = Counter()
        reProcess = re.compile(
            u'(?:dremora)|(?:akaos)|(?:lathulet)|(?:orthe)|(?:ranyu)',
            re.I | re.U)
        #--Sort Eyes/Hair
        final_eyes = {}
        defaultMaleHair = {}
        defaultFemaleHair = {}
        maleHairs = {f for f, x in patchFile.tops[b'HAIR'].id_records.items()
                     if not x.flags.not_male}
        femaleHairs = {f for f, x in patchFile.tops[b'HAIR'].id_records.items()
                       if not x.flags.not_female}
        skip_race_fid = bush.game.master_fid(0x038010)
        for rid, race in patchFile.tops[b'RACE'].id_records.items():
            if (race.flags.playable or rid == skip_race_fid) and race.eyes:
                final_eyes[rid] = [x for x in self.vanilla_eyes.get(rid, [])
                                   if x in race.eyes]
                if not final_eyes[rid]:
                    final_eyes[rid] = [race.eyes[0]]
                defaultMaleHair[rid] = [x for x in race.hairs if
                                        x in maleHairs]
                defaultFemaleHair[rid] = [x for x in race.hairs if
                                          x in femaleHairs]
        #--Npcs with unassigned eyes/hair
        player_fid = bush.game.master_fid(0x000007)
        for npc_fid, npc in patchFile.tops[b'NPC_'].id_records.items():
            if npc_fid == player_fid: continue # skip player
            if (npc.full is not None and npc.race == skip_race_fid and
                    not reProcess.search(npc.full)): continue
            if is_templated(npc, u'useModelAnimation'):
                continue # Changing templated actors wouldn't do anything
            raceEyes = final_eyes.get(npc.race)
            npc_src_plugin = npc_fid.mod_fn
            random.seed(npc_fid.object_dex)  # make it deterministic
            if not npc.eye and raceEyes:
                npc.eye = random.choice(raceEyes)
                mod_npcsFixed[npc_src_plugin] += 1
                keep(npc_fid, npc)
            raceHair = (
                (defaultMaleHair, defaultFemaleHair)[npc.flags.female]).get(
                npc.race)
            if not npc.hair and raceHair:
                npc.hair = random.choice(raceHair)
                mod_npcsFixed[npc_src_plugin] += 1
                keep(npc_fid, npc)
            if not npc.hairLength:
                npc.hairLength = random.random()
                mod_npcsFixed[npc_src_plugin] += 1
                keep(npc_fid, npc)
        #--Done
        log.setHeader(u'= ' + self._patcher_name)
        if mod_npcsFixed:
            log(u'\n=== ' + _(u'Eyes/Hair Assigned for NPCs'))
            for src_mod, num_fixed in dict_sort(mod_npcsFixed):
                log(f'* {src_mod}: {num_fixed:d}')

#------------------------------------------------------------------------------
class TimescaleCheckerPatcher(ModLoader):
    patcher_group = 'Special'
    patcher_order = 40
    _read_sigs = (b'GRAS',)

    def __init__(self, p_name, p_file):
        super(TimescaleCheckerPatcher, self).__init__(p_name, p_file)
        # We want to use _mod_file_read for GLOB records, not GRAS records
        self.loadFactory = LoadFactory(False, by_sig=[b'GLOB'])

    def _add_to_patch(self, rid, record, top_sig):
        return rid not in self.patchFile.tops[top_sig].id_records \
            and record.wave_period != 0.0

    def buildPatch(self, log, progress):
        if not self.isActive: return
        # The base timescale to which all wave periods are relative
        def_timescale = bush.game.default_wp_timescale
        # First, look in the BP to see if we have a record that overrides the
        # timescale
        def find_timescale(glob_file):
            if b'GLOB' not in glob_file.tops: return None
            glob_recs = glob_file.tops[b'GLOB'].iter_present_records()
            for glob_eid, glob_rec in ((r.eid, r) for _gkey, r in glob_recs):
                if glob_eid and glob_eid.lower() == u'timescale':
                    return glob_rec.global_value
            return None
        final_timescale = find_timescale(self.patchFile)
        # If the BP didn't have it, look through all plugins that could
        # override the timescale and look for the last override (hence the
        # reversed order)
        if final_timescale is None:
            relevant_plugins = [v for v in
                                self.patchFile.merged_or_loaded_ord.values()]
            for r_plugin in reversed(relevant_plugins):
                final_timescale = find_timescale(self._mod_file_read(r_plugin))
                if final_timescale is not None:
                    break
        # If none of the plugins had it (this should be impossible), assume the
        # timescale is identical to the default timescale
        if final_timescale is None:
            final_timescale = def_timescale
        if final_timescale == def_timescale:
            # Nothing to do, all grasses will have a matching wave period
            return
        keep = self.patchFile.getKeeper()
        grasses_changed = Counter()
        # The multiplier should do the inverse of what the final timescale is
        # doing, e.g. changing timescale from 30 to 20 -> multiply wave period
        # by 1.5 (= 30/20)
        wp_multiplier = def_timescale / final_timescale
        for grass_fid, grass_rec in self.patchFile.tops[b'GRAS'].id_records.items():
            grass_rec.wave_period *= wp_multiplier
            grasses_changed[grass_fid.mod_fn] += 1
            keep(grass_fid, grass_rec)
        log.setHeader(u'= ' + self._patcher_name)
        if grasses_changed:
            log(u'\n=== ' + _(u'Wave Periods changed'))
            for src_mod, num_fixed in dict_sort(grasses_changed):
                log(f'* {src_mod}: {num_fixed:d}')
