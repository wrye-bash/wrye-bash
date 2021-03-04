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
"""Temp module, contains the Race Records patcher. It imports the tweak classes
from multitweak_races.py."""

from __future__ import print_function

import random
import re
from collections import defaultdict

# Internal
from .multitweak_races import *
from ..base import ModLoader
from ... import bush
from ...bolt import GPath

# Utilities & Constants -------------------------------------------------------
def _find_vanilla_eyes():
    """Converts vanilla default_eyes to use long FormIDs and returns the
    result."""
    def _conv_fid(rc_fid): return GPath(rc_fid[0]), rc_fid[1]
    ret = {}
    for race_fid, race_eyes in bush.game.default_eyes.iteritems():
        new_key = _conv_fid(race_fid)
        new_val = [_conv_fid(eye_fid) for eye_fid in race_eyes]
        ret[new_key] = new_val
    return ret

_main_master = GPath(bush.game.master_file)

#------------------------------------------------------------------------------
# Race Records ----------------------------------------------------------------
#------------------------------------------------------------------------------
class RaceRecordsPatcher(ModLoader):
    """Race patcher."""
    patcher_group = u'Special'
    patcher_order = 40
    _read_sigs = (b'RACE', b'HAIR', b'NPC_')
    _tweak_classes = {
        RaceTweak_BiggerOrcsAndNords, RaceTweak_MergeSimilarRaceHairs,
        RaceTweak_MergeSimilarRaceEyes, RaceTweak_PlayableEyes,
        RaceTweak_PlayableHairs, RaceTweak_SexlessHairs, RaceTweak_AllEyes,
        RaceTweak_AllHairs,
    }

    def __init__(self, p_name, p_file):
        super(RaceRecordsPatcher, self).__init__(p_name, p_file)
        self.isActive = True #--Always enabled to support eye filtering
        self.scanTypes = {b'RACE', b'HAIR', b'NPC_'}
        self.vanilla_eyes = _find_vanilla_eyes()

    def scanModFile(self, modFile, progress):
        """Add appropriate records from modFile."""
        if not (set(modFile.tops) & self.scanTypes): return
        #--Hair
        patchBlock = self.patchFile.tops[b'HAIR']
        id_records = patchBlock.id_records
        for record in modFile.tops[b'HAIR'].getActiveRecords():
            if record.fid not in id_records:
                patchBlock.setRecord(record.getTypeCopy())
        #--Npcs with unassigned eyes
        patchBlock = self.patchFile.tops[b'NPC_']
        id_records = patchBlock.id_records
        for record in modFile.tops[b'NPC_'].getActiveRecords():
            if not record.eye and record.fid not in id_records:
                patchBlock.setRecord(record.getTypeCopy())
        #--Race block
        patchBlock = self.patchFile.tops[b'RACE']
        id_records = patchBlock.id_records
        for record in modFile.tops[b'RACE'].getActiveRecords():
            if record.fid not in id_records:
                patchBlock.setRecord(record.getTypeCopy())

    def buildPatch(self,log,progress):
        """Updates races as needed."""
        if not self.isActive: return
        patchFile = self.patchFile
        if b'RACE' not in patchFile.tops: return
        keep = patchFile.getKeeper()
        mod_npcsFixed = defaultdict(set)
        reProcess = re.compile(
            u'(?:dremora)|(?:akaos)|(?:lathulet)|(?:orthe)|(?:ranyu)',
            re.I | re.U)
        #--Sort Eyes/Hair
        final_eyes = {}
        defaultMaleHair = {}
        defaultFemaleHair = {}
        maleHairs = {x.fid for x in patchFile.tops[b'HAIR'].records
                     if not x.flags.notMale}
        femaleHairs = {x.fid for x in patchFile.tops[b'HAIR'].records
                       if not x.flags.notFemale}
        for race in patchFile.tops[b'RACE'].records:
            if (race.flags.playable or race.fid == (
                    _main_master, 0x038010)) and race.eyes:
                final_eyes[race.fid] = [x for x in
                                        self.vanilla_eyes.get(race.fid, [])
                                        if x in race.eyes]
                if not final_eyes[race.fid]:
                    final_eyes[race.fid] = [race.eyes[0]]
                defaultMaleHair[race.fid] = [x for x in race.hairs if
                                             x in maleHairs]
                defaultFemaleHair[race.fid] = [x for x in race.hairs if
                                               x in femaleHairs]
        #--Npcs with unassigned eyes/hair
        for npc in patchFile.tops[b'NPC_'].records:
            if npc.fid == (_main_master, 0x000007): continue  #
            # skip player
            if npc.full is not None and npc.race == (
                    _main_master, 0x038010) and not reProcess.search(
                    npc.full): continue
            raceEyes = final_eyes.get(npc.race)
            random.seed(npc.fid[1]) # make it deterministic
            if not npc.eye and raceEyes:
                npc.eye = random.choice(raceEyes)
                mod_npcsFixed[npc.fid[0]].add(npc.fid)
                keep(npc.fid)
            raceHair = (
                (defaultMaleHair, defaultFemaleHair)[npc.flags.female]).get(
                npc.race)
            if not npc.hair and raceHair:
                npc.hair = random.choice(raceHair)
                mod_npcsFixed[npc.fid[0]].add(npc.fid)
                keep(npc.fid)
            if not npc.hairLength:
                npc.hairLength = random.random()
                mod_npcsFixed[npc.fid[0]].add(npc.fid)
                keep(npc.fid)
        #--Done
        log.setHeader(u'= ' + self._patcher_name)
        if mod_npcsFixed:
            log(u'\n=== ' + _(u'Eyes/Hair Assigned for NPCs'))
            for srcMod in sorted(mod_npcsFixed):
                log(u'* %s: %d' % (srcMod, len(mod_npcsFixed[srcMod])))
