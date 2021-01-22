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

"""This module contains the oblivion MultitweakItem patcher classes that tweak
races records. As opposed to the rest of the multitweak items these are not
grouped by a MultiTweaker but by the race patcher (also in this module) which
is a special patcher. Notice the PBash ones do not log in buildPatch - the
RacesTweaker patcher was calling their "log" method - now super's _patchLog()
"""

from __future__ import print_function

import random
import re
from collections import defaultdict, Counter
from itertools import izip

# Internal
from .base import MultiTweakItem, ListPatcher
from ... import bosh, bush
from ...bolt import GPath, deprint
from ...brec import MelObject, strFid
from ...exception import BoltError
from ...mod_files import ModFile, LoadFactory
from ...patcher.base import AMultiTweaker

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

_vanilla_races = [u'argonian', u'breton', u'dremora', u'dark elf',
                  u'dark seducer', u'golden saint', u'high elf', u'imperial',
                  u'khajiit', u'nord', u'orc', u'redguard', u'wood elf']

# Patchers: 40 ----------------------------------------------------------------
_main_master = GPath(bush.game.master_file)

class _ARaceTweak(MultiTweakItem):
    """ABC for race tweaks."""
    tweak_read_classes = b'RACE',
    tweak_log_msg = _(u'Races Tweaked: %(total_changed)d')
    _tweak_races_data = None # sentinel, set in RaceRecordsPatcher.buildPatch

    def _calc_changed_face_parts(self, face_attr, collected_races_data):
        """Calculates a changes dictionary for the specified face attribute,
        using the specified collected races data."""
        changed_hairs = {}
        #process hair lists
        if self.choiceValues[self.chosen][0] == 1:
            # Merge face parts only from vanilla races to custom parts
            for race in collected_races_data:
                for r in _vanilla_races:
                    if r in race:
                        if (collected_races_data[r][face_attr] !=
                                collected_races_data[race][face_attr]):
                            # yuach nasty but quickly and easily removes
                            # duplicates.
                            changed_hairs[race] = list(set(
                                collected_races_data[r][face_attr] +
                                collected_races_data[race][face_attr]))
        else: # full back and forth merge!
            for race in collected_races_data:
                # nasty processing slog
                rs = race.split(u'(')
                rs = rs[0].split()
                if len(rs) > 1 and rs[1] in [u'elf', u'seducer']:
                    rs[0] = rs[0] + u' ' + rs[1]
                    del(rs[1])
                for r in collected_races_data:
                    if r == race: continue
                    for s in rs:
                        if s in r:
                            if (collected_races_data[r][face_attr] !=
                                    collected_races_data[race][face_attr]):
                                # list(set([]) disgusting thing again
                                changed_hairs[race] = list(set(
                                    collected_races_data[r][face_attr] +
                                    collected_races_data[race][face_attr]))
        return changed_hairs

    def _get_changed_eyes(self):
        """Returns the changed eyes dictionary. A cached wrapper around
        _calc_changed_face_parts."""
        try:
            return self._cached_changed_eyes
        except AttributeError:
            self._cached_changed_eyes = self._calc_changed_face_parts(
                u'eyes', self._tweak_races_data)
            return self._cached_changed_eyes

    def _get_changed_hairs(self):
        """Returns the changed hairs dictionary. A cached wrapper around
        _calc_changed_face_parts."""
        try:
            return self._cached_changed_hairs
        except AttributeError:
            self._cached_changed_hairs = self._calc_changed_face_parts(
               u'hairs', self._tweak_races_data)
            return self._cached_changed_hairs

    def prepare_for_tweaking(self, patch_file):
        self._tweak_races_data = patch_file.races_data

# -----------------------------------------------------------------------------
class RaceTweaker_BiggerOrcsAndNords(_ARaceTweak):
    """Adjusts the Orc and Nord race records to be taller/heavier."""
    tweak_read_classes = b'RACE',
    tweak_name = _(u'Bigger Nords And Orcs')
    tweak_tip = _(u'Adjusts the Orc and Nord race records to be '
                  u'taller/heavier - to be more lore friendly.')
    tweak_key = u'BiggerOrcsandNords'
    # Syntax: ((nord m height, nord f height, nord m weight, nord f weight),
    #          (orc m height, orc f height, orc m weight, orc f weight))
    tweak_choices = [(u'Bigger Nords and Orcs',
                      ((1.09, 1.09, 1.13, 1.06), (1.09, 1.09, 1.13, 1.0))),
                     (u'MMM Resized Races',
                      ((1.08, 1.07, 1.28, 1.19), (1.09, 1.06, 1.36, 1.3))),
                     (u'RBP',
                      ((1.075,1.06,1.20,1.125),(1.06,1.045,1.275,1.18)))]
    _tweak_attrs = [u'maleHeight', u'femaleHeight', u'maleWeight',
                    u'femaleWeight']

    def wants_record(self, record):
        if not record.full: return False
        rec_full = record.full.lower()
        is_orc = u'orc' in rec_full
        return (u'nord' in rec_full or is_orc) and any(
            getattr(record, a) != v for a, v in izip(
                self._tweak_attrs, self.choiceValues[self.chosen][0][is_orc]))

    def tweak_record(self, record):
        is_orc = u'orc' in record.full.lower()
        for tweak_attr, tweak_val in izip(
                self._tweak_attrs, self.choiceValues[self.chosen][0][is_orc]):
            setattr(record, tweak_attr, tweak_val)

# -----------------------------------------------------------------------------
class RaceTweaker_MergeSimilarRaceHairs(_ARaceTweak):
    """Merges similar race's hairs (kinda specifically designed for SOVVM's
    bearded races)."""
    tweak_name = _(u'Merge Hairs From Similar Races')
    tweak_tip = _(u'Merges hair lists from similar races (e.g. give RBP '
                  u'khajit hair to all the other varieties of khajits in '
                  u'Elsweyr).')
    tweak_key = u'MergeSimilarRaceHairLists'
    tweak_choices = [(_(u'Merge hairs only from vanilla races'), 1),
                     (_(u'Full hair merge between similar races'), 0)]

    def wants_record(self, record):
        if not record.full: return False
        # If this is None, we don't have race data yet and have to blindly
        # forward records until the patcher sends it to us
        elif self._tweak_races_data is None: return True
        # Cached, so calling this over and over is fine
        changed_hairs = self._get_changed_hairs()
        rec_full = record.full.lower()
        return (rec_full in changed_hairs and
                record.hairs != changed_hairs[rec_full])

    def tweak_record(self, record):
        record.hairs = self._get_changed_hairs()[record.full.lower()]

# -----------------------------------------------------------------------------
class RaceTweaker_MergeSimilarRaceEyes(_ARaceTweak):
    """Merges similar race's eyes."""
    tweak_name = _(u'Merge Eyes From Similar Races')
    tweak_tip = _(u'Merges eye lists from similar races (f.e. give RBP khajit '
                  u'eyes to all the other varieties of khajits in Elsweyr)')
    tweak_key = u'MergeSimilarRaceEyeLists'
    tweak_choices = [(_(u'Merge eyes only from vanilla races'), 1),
                     (_(u'Full eye merge between similar races'), 0)]

    def wants_record(self, record):
        if not record.full: return False
        # If this is None, we don't have race data yet and have to blindly
        # forward records until the patcher sends it to us
        if self._tweak_races_data is None: return True
        # Cached, so calling this over and over is fine
        changed_eyes = self._get_changed_eyes()
        rec_full = record.full.lower()
        return (rec_full in changed_eyes and
                record.eyes != changed_eyes[rec_full])

    def tweak_record(self, record):
        record.eyes = self._get_changed_eyes()[record.full.lower()]

# -----------------------------------------------------------------------------
class _ARUnblockTweak(_ARaceTweak):
    """Shared code of 'races have all X' tweaks."""
    # First item is the record signature to retrieve race data for, second item
    # is the record attribute to patch
    _sig_and_attr = (b'OVERRIDE', u'OVERRIDE')

    def wants_record(self, record):
        race_sig, race_attr = self._sig_and_attr
        # If this is None, we don't have race data yet and have to blindly
        # forward records until the patcher sends it to us
        tweak_data = self._tweak_races_data
        return tweak_data is None or getattr(
            record, race_attr) != tweak_data[race_sig]

    def tweak_record(self, record):
        race_sig, race_attr = self._sig_and_attr
        setattr(record, race_attr, self._tweak_races_data[race_sig])

# -----------------------------------------------------------------------------
class RaceTweaker_AllHairs(_ARUnblockTweak):
    """Gives all races ALL hairs."""
    tweak_name = _(u'Races Have All Hairs')
    tweak_tip = _(u'Gives all races every available hair.')
    tweak_key = u'hairyraces'
    tweak_choices = [(u'get down tonight', 1)]
    _sig_and_attr = (b'HAIR', u'hairs')

# -----------------------------------------------------------------------------
class RaceTweaker_AllEyes(_ARUnblockTweak):
    """Gives all races ALL eyes."""
    tweak_name = _(u'Races Have All Eyes')
    tweak_tip = _(u'Gives all races every available eye.')
    tweak_key = u'eyeyraces'
    tweak_choices = [(u'what a lot of eyes you have dear', 1)]
    _sig_and_attr = (b'EYES', u'eyes')

# -----------------------------------------------------------------------------
class _ARPlayableTweak(_ARaceTweak):
    """Shared code of playable hair/eyes tweaks."""
    def wants_record(self, record):
        return not record.flags.playable

    def tweak_record(self, record):
        record.flags.playable = True

# -----------------------------------------------------------------------------
class RaceTweaker_PlayableEyes(_ARPlayableTweak):
    """Sets all eyes to be playable."""
    tweak_read_classes = b'EYES',
    tweak_name = _(u'Playable Eyes')
    tweak_tip = _(u'Sets all eyes to be playable.')
    tweak_key = u'playableeyes'
    tweak_choices = [(u'Get it done', 1)]
    tweak_log_msg = _(u'Eyes Tweaked: %(total_changed)d')

# -----------------------------------------------------------------------------
class RaceTweaker_PlayableHairs(_ARPlayableTweak):
    """Sets all hairs to be playable."""
    tweak_read_classes = b'HAIR',
    tweak_name = _(u'Playable Hairs')
    tweak_tip = _(u'Sets all Hairs to be playable.')
    tweak_key = u'playablehairs'
    tweak_choices = [(u'Get it done', 1)]
    tweak_log_msg = _(u'Hairs Tweaked: %(total_changed)d')

# -----------------------------------------------------------------------------
class RaceTweaker_SexlessHairs(_ARaceTweak):
    """Sets all hairs to be playable by both males and females."""
    tweak_read_classes = b'HAIR',
    tweak_name = _(u'Sexless Hairs')
    tweak_tip = _(u'Lets any sex of character use any hair.')
    tweak_key = u'sexlesshairs'
    tweak_choices = [(u'Get it done', 1)]
    tweak_log_msg = _(u'Hairs Tweaked: %(total_changed)d')

    def wants_record(self, record):
        return record.flags.notMale or record.flags.notFemale

    def tweak_record(self, record):
        record.flags.notMale = False
        record.flags.notFemale = False

#------------------------------------------------------------------------------
# Race Records ----------------------------------------------------------------
#------------------------------------------------------------------------------
class RaceRecordsPatcher(AMultiTweaker, ListPatcher):
    """Race patcher - we inherit from AMultiTweaker to use tweak_instances."""
    patcher_group = u'Special'
    patcher_order = 40
    _read_sigs = (b'RACE', b'EYES', b'HAIR', b'NPC_')
    _tweak_classes = {
        RaceTweaker_BiggerOrcsAndNords, RaceTweaker_MergeSimilarRaceHairs,
        RaceTweaker_MergeSimilarRaceEyes, RaceTweaker_PlayableEyes,
        RaceTweaker_PlayableHairs, RaceTweaker_SexlessHairs,
        RaceTweaker_AllEyes, RaceTweaker_AllHairs,
    }

    def __init__(self, p_name, p_file, p_sources, enabled_tweaks):
        # NB: call the ListPatcher __init__ not the AMultiTweaker one!
        super(AMultiTweaker, self).__init__(p_name, p_file, p_sources)
        self.races_data = {'EYES':[],'HAIR':[]}
        self.raceData = {} #--Race eye meshes, hair,eyes
        self.tempRaceData = {}
        #--Restrict srcs to active/merged mods.
        self.srcs = [x for x in self.srcs if x in p_file.allSet]
        self.isActive = True #--Always enabled to support eye filtering
        self.bodyKeys = {'TailModel', 'UpperBodyPath', 'LowerBodyPath',
                         'HandPath', 'FootPath', 'TailPath'}
        self.sizeKeys = {'Height', 'Weight'}
        self.raceAttributes = {'Strength', 'Intelligence', 'Willpower',
                               'Agility', 'Speed', 'Endurance', 'Personality',
                               'Luck'}
        self.raceSkills = {'skill1', 'skill1Boost', 'skill2', 'skill2Boost',
                           'skill3', 'skill3Boost', 'skill4', 'skill4Boost',
                           'skill5', 'skill5Boost', 'skill6', 'skill6Boost',
                           'skill7', 'skill7Boost'}
        self.eyeKeys = {u'Eyes'}
        self.eye_mesh = {}
        self.scanTypes = {b'RACE', b'EYES', b'HAIR', b'NPC_'}
        self.vanilla_eyes = _find_vanilla_eyes()
        self.enabled_tweaks = enabled_tweaks

    def initData(self,progress):
        """Get data from source files."""
        # HACK - wholesale copy of MultiTweaker.initData, see #494
        # Has to come before the srcs check, because of isActive nonsense this
        # patcher will still run and blow up in scanModFile otherwise
        self._tweak_dict = t_dict = defaultdict(lambda: ([], []))
        for tweak in self.enabled_tweaks: # type: MultiTweakItem
            for read_sig in tweak.tweak_read_classes:
                t_dict[read_sig][tweak.supports_pooling].append(tweak)
        if not self.isActive or not self.srcs: return
        loadFactory = LoadFactory(False, by_sig=[b'RACE'])
        progress.setFull(len(self.srcs))
        cachedMasters = {}
        for index,srcMod in enumerate(self.srcs):
            if srcMod not in bosh.modInfos: continue
            srcInfo = bosh.modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            bashTags = srcInfo.getBashTags()
            if b'RACE' not in srcFile.tops: continue
            self.tempRaceData = {} #so as not to carry anything over!
            if u'R.ChangeSpells' in bashTags and u'R.AddSpells' in bashTags:
                raise BoltError(
                    u'WARNING mod %s has both R.AddSpells and R.ChangeSpells '
                    u'tags - only one of those tags should be on a mod at '
                    u'one time' % srcMod)
            for race in srcFile.tops[b'RACE'].getActiveRecords():
                tempRaceData = self.tempRaceData.setdefault(race.fid,{})
                raceData = self.raceData.setdefault(race.fid,{})
                if u'Hair' in bashTags:
                    raceHair = raceData.setdefault('hairs',[])
                    for hair in race.hairs:
                        if hair not in raceHair: raceHair.append(hair)
                if self.eyeKeys & bashTags:
                    tempRaceData['rightEye'] = race.rightEye
                    tempRaceData['leftEye'] = race.leftEye
                    raceEyes = raceData.setdefault('eyes',[])
                    for eye in race.eyes:
                        if eye not in raceEyes: raceEyes.append(eye)
                if u'Voice-M' in bashTags:
                    tempRaceData['maleVoice'] = race.maleVoice
                if u'Voice-F' in bashTags:
                    tempRaceData['femaleVoice'] = race.femaleVoice
                if u'Body-M' in bashTags:
                    for body_key in ['male' + k for k in self.bodyKeys]:
                        tempRaceData[body_key] = getattr(race, body_key)
                if u'Body-F' in bashTags:
                    for body_key in ['female' + k for k in self.bodyKeys]:
                        tempRaceData[body_key] = getattr(race, body_key)
                if u'Body-Size-M' in bashTags:
                    for bsize_key in ['male' + k for k in self.sizeKeys]:
                        tempRaceData[bsize_key] = getattr(race, bsize_key)
                if u'Body-Size-F' in bashTags:
                    for bsize_key in ['female' + k for k in self.sizeKeys]:
                        tempRaceData[bsize_key] = getattr(race, bsize_key)
                if u'R.Teeth' in bashTags:
                    for teeth_key in ('teethLower', 'teethUpper'):
                        tempRaceData[teeth_key] = getattr(race, teeth_key)
                if u'R.Mouth' in bashTags:
                    for mouth_key in ('mouth', 'tongue'):
                        tempRaceData[mouth_key] = getattr(race, mouth_key)
                if u'R.Head' in bashTags:
                    tempRaceData['head'] = race.head
                if u'R.Ears' in bashTags:
                    for ears_key in ('maleEars', 'femaleEars'):
                        tempRaceData[ears_key] = getattr(race, ears_key)
                if u'R.Relations' in bashTags:
                    relations = raceData.setdefault('relations',{})
                    for x in race.relations:
                        relations[x.faction] = x.mod
                if u'R.Attributes-F' in bashTags:
                    for af_key in ['female' + k for k in self.raceAttributes]:
                        tempRaceData[af_key] = getattr(race, af_key)
                if u'R.Attributes-M' in bashTags:
                    for am_key in ['male' + k for k in self.raceAttributes]:
                        tempRaceData[am_key] = getattr(race, am_key)
                if u'R.Skills' in bashTags:
                    for skill_key in self.raceSkills:
                        tempRaceData[skill_key] = getattr(race, skill_key)
                if u'R.AddSpells' in bashTags:
                    tempRaceData['AddSpells'] = race.spells
                if u'R.ChangeSpells' in bashTags:
                    raceData['spellsOverride'] = race.spells
                if u'R.Description' in bashTags:
                    tempRaceData['text'] = race.text
            for master in srcInfo.masterNames:
                if not master in bosh.modInfos: continue  # or break
                # filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = bosh.modInfos[master]
                    masterFile = ModFile(masterInfo,loadFactory)
                    masterFile.load(True)
                    if b'RACE' not in masterFile.tops: continue
                    cachedMasters[master] = masterFile
                for race in masterFile.tops[b'RACE'].getActiveRecords():
                    if race.fid not in self.tempRaceData: continue
                    tempRaceData = self.tempRaceData[race.fid]
                    raceData = self.raceData[race.fid]
                    if 'AddSpells' in tempRaceData:
                        raceData.setdefault('AddSpells', [])
                        for spell in tempRaceData['AddSpells']:
                            if spell not in race.spells:
                                if spell not in raceData['AddSpells']:
                                    raceData['AddSpells'].append(spell)
                        del tempRaceData['AddSpells']
                    for race_key in tempRaceData:
                        if tempRaceData[race_key] != getattr(race, race_key):
                            raceData[race_key] = tempRaceData[race_key]
            progress.plus()

    def scanModFile(self, modFile, progress):
        """Add appropriate records from modFile."""
        races_data = self.races_data
        eye_mesh = self.eye_mesh
        if not (set(modFile.tops) & self.scanTypes): return
        srcEyes = {record.fid for record in modFile.tops[b'EYES'].getActiveRecords()}
        #--Eyes, Hair
        for top_grup_sig in (b'EYES', b'HAIR'):
            patchBlock = self.patchFile.tops[top_grup_sig]
            id_records = patchBlock.id_records
            for record in modFile.tops[top_grup_sig].getActiveRecords():
                races_data[top_grup_sig].append(record.fid)
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
            if not record.rightEye or not record.leftEye:
                # Don't complain if the FULL is missing, that probably means
                # it's an internal or unused RACE
                if record.full:
                    deprint(u'No right and/or no left eye recorded in race '
                        u'%s, from mod %s' % (record.full, modFile.fileInfo))
                continue
            for eye in record.eyes:
                if eye in srcEyes:
                    eye_mesh[eye] = (record.rightEye.modPath.lower(),
                                     record.leftEye.modPath.lower())
        # HACK - wholesale copy of MultiTweaker.scanModFile, see #494
        rec_pool = defaultdict(set)
        common_tops = set(modFile.tops) & set(self._tweak_dict)
        for curr_top in common_tops:
            # Need to give other tweaks a chance to do work first
            for o_tweak in self._tweak_dict[curr_top][0]:
                o_tweak.tweak_scan_file(modFile, self.patchFile)
            # Now we can collect all records that poolable tweaks are
            # interested in
            pool_record = rec_pool[curr_top].add
            poolable_tweaks = self._tweak_dict[curr_top][1]
            if not poolable_tweaks: continue # likely complex type, e.g. CELL
            for record in modFile.tops[curr_top].getActiveRecords():
                for p_tweak in poolable_tweaks: # type: MultiTweakItem
                    if p_tweak.wants_record(record):
                        pool_record(record)
                        break # Exit as soon as a tweak is interested
        # Finally, copy all pooled records in one fell swoop
        for top_grup_sig, pooled_records in rec_pool.iteritems():
            if pooled_records: # only copy if we could pool
                self.patchFile.tops[top_grup_sig].copy_records(pooled_records)

    def buildPatch(self,log,progress):
        """Updates races as needed."""
        debug = False
        tweak_data = self.races_data
        if not self.isActive: return
        patchFile = self.patchFile
        keep = patchFile.getKeeper()
        if b'RACE' not in patchFile.tops: return
        racesPatched = []
        racesSorted = []
        racesFiltered = []
        mod_npcsFixed = defaultdict(set)
        reProcess = re.compile(
            u'(?:dremora)|(?:akaos)|(?:lathulet)|(?:orthe)|(?:ranyu)',
            re.I | re.U)
        #--Import race info
        for race in patchFile.tops[b'RACE'].records:
            #~~print 'Building',race.eid
            raceData = self.raceData.get(race.fid,None)
            if not raceData: continue
            raceChanged = False
            #-- Racial Hair and  Eye sets
            if 'hairs' in raceData and (
                        set(race.hairs) != set(raceData['hairs'])):
                race.hairs = raceData['hairs']
                raceChanged = True
            if 'eyes' in raceData:
                if set(race.eyes) != set(raceData['eyes']):
                    race.eyes = raceData['eyes']
                    raceChanged = True
            #-- Eye paths:
            if 'rightEye' in raceData:
                if not race.rightEye:
                    deprint(u'Very odd race %s found - no right eye '
                            u'assigned' % race.full)
                else:
                    if race.rightEye.modPath != raceData['rightEye'].modPath:
                        race.rightEye.modPath = raceData['rightEye'].modPath
                        raceChanged = True
            if 'leftEye' in raceData:
                if not race.leftEye:
                    deprint(u'Very odd race %s found - no left eye '
                            u'assigned' % race.full)
                else:
                    if race.leftEye.modPath != raceData['leftEye'].modPath:
                        race.leftEye.modPath = raceData['leftEye'].modPath
                        raceChanged = True
            #--Teeth/Mouth/head/ears/description
            for basic_key in ('teethLower', 'teethUpper', 'mouth', 'tongue',
                              'text', 'head'):
                if basic_key in raceData:
                    if getattr(race, basic_key) != raceData[basic_key]:
                        setattr(race, basic_key, raceData[basic_key])
                        raceChanged = True
            #--spells
            if 'spellsOverride' in raceData:
                race.spells = raceData['spellsOverride']
            if 'AddSpells' in raceData:
                raceData['spells'] = race.spells
                for spell in raceData['AddSpells']:
                    raceData['spells'].append(spell)
                race.spells = raceData['spells']
            #--skills
            for skill_key in self.raceSkills:
                if skill_key in raceData:
                    if getattr(race, skill_key) != raceData[skill_key]:
                        setattr(race, skill_key, raceData[skill_key])
                        raceChanged = True
            #--Gender info (voice, gender specific body data)
            for gender in ('male','female'):
                bodyKeys = self.bodyKeys.union(self.raceAttributes.union(
                    {'Ears', 'Voice'}))
                bodyKeys = [gender + k for k in bodyKeys]
                for body_key in bodyKeys:
                    if body_key in raceData:
                        if getattr(race, body_key) != raceData[body_key]:
                            setattr(race, body_key, raceData[body_key])
                            raceChanged = True
            #--Relations
            if 'relations' in raceData:
                relations = raceData['relations']
                oldRelations = {(x.faction, x.mod) for x in race.relations}
                newRelations = set(relations.iteritems())
                if newRelations != oldRelations:
                    del race.relations[:]
                    for faction,mod in newRelations:
                        entry = MelObject()
                        entry.faction = faction
                        entry.mod = mod
                        race.relations.append(entry)
                    raceChanged = True
            #--Changed
            if raceChanged:
                racesPatched.append(race.eid)
                keep(race.fid)
        #--Eye Mesh filtering
        eye_mesh = self.eye_mesh
        try:
            blueEyeMesh = eye_mesh[(_main_master, 0x27308)]
        except KeyError:
            print(u'error getting blue eye mesh:')
            print(u'eye meshes:', eye_mesh)
            raise
        argonianEyeMesh = eye_mesh[(_main_master, 0x3e91e)]
        if debug:
            print(u'== Eye Mesh Filtering')
            print(u'blueEyeMesh',blueEyeMesh)
            print(u'argonianEyeMesh',argonianEyeMesh)
        for eye in (
            (_main_master, 0x1a), #--Reanimate
            (_main_master, 0x54bb9), #--Dark Seducer
            (_main_master, 0x54bba), #--Golden Saint
            (_main_master, 0x5fa43), #--Ordered
            ):
            eye_mesh.setdefault(eye,blueEyeMesh)
        def setRaceEyeMesh(race,rightPath,leftPath):
            race.rightEye.modPath = rightPath
            race.leftEye.modPath = leftPath
        for race in patchFile.tops[b'RACE'].records:
            if debug: print(u'===', race.eid)
            if not race.eyes: continue  #--Sheogorath. Assume is handled
            # correctly.
            if not race.rightEye or not race.leftEye: continue #--WIPZ race?
            if re.match(u'^117[a-zA-Z]', race.eid, flags=re.U): continue  #--
            #  x117 race?
            raceChanged = False
            mesh_eye = {}
            for eye in race.eyes:
                if eye not in eye_mesh:
                    deprint(
                        _(u'Mesh undefined for eye %s in race %s, eye removed '
                          u'from race list.') % (
                            strFid(eye), race.eid,))
                    continue
                mesh = eye_mesh[eye]
                if mesh not in mesh_eye:
                    mesh_eye[mesh] = []
                mesh_eye[mesh].append(eye)
            currentMesh = (
                race.rightEye.modPath.lower(), race.leftEye.modPath.lower())
            try:
                maxEyesMesh = sorted(mesh_eye, key=lambda a: len(mesh_eye[a]),
                                     reverse=True)[0]
            except IndexError:
                maxEyesMesh = blueEyeMesh
            #--Single eye mesh, but doesn't match current mesh?
            if len(mesh_eye) == 1 and currentMesh != maxEyesMesh:
                setRaceEyeMesh(race,*maxEyesMesh)
                raceChanged = True
            #--Multiple eye meshes (and playable)?
            if debug:
                for mesh,eyes in mesh_eye.iteritems():
                    print(mesh)
                    for eye in eyes: print(' ',strFid(eye))
            if len(mesh_eye) > 1 and (race.flags.playable or race.fid == (
                    _main_master, 0x038010)):
                #--If blueEyeMesh (mesh used for vanilla eyes) is present,
                # use that.
                if blueEyeMesh in mesh_eye and currentMesh != argonianEyeMesh:
                    setRaceEyeMesh(race,*blueEyeMesh)
                    race.eyes = mesh_eye[blueEyeMesh]
                    raceChanged = True
                elif argonianEyeMesh in mesh_eye:
                    setRaceEyeMesh(race,*argonianEyeMesh)
                    race.eyes = mesh_eye[argonianEyeMesh]
                    raceChanged = True
                #--Else figure that current eye mesh is the correct one
                elif currentMesh in mesh_eye:
                    race.eyes = mesh_eye[currentMesh]
                    raceChanged = True
                #--Else use most popular eye mesh
                else:
                    setRaceEyeMesh(race,*maxEyesMesh)
                    race.eyes = mesh_eye[maxEyesMesh]
                    raceChanged = True
            if raceChanged:
                racesFiltered.append(race.eid)
                keep(race.fid)
            if race.full:
                tweak_data[race.full.lower()] = {'hairs': race.hairs,
                                                 'eyes': race.eyes,
                                                 'relations': race.relations}
        # HACK - wholesale copy of MultiTweaker.buildPatch, see #494, plus
        # lightly edited for race patcher nonsense
        self.patchFile.races_data = tweak_data
        for tweak in self.enabled_tweaks: # type: MultiTweakItem
            tweak.prepare_for_tweaking(self.patchFile)
        common_tops = set(self.patchFile.tops) & set(self._tweak_dict)
        keep = self.patchFile.getKeeper()
        tweak_counter = defaultdict(Counter)
        for curr_top in common_tops:
            top_dict = self._tweak_dict[curr_top]
            # Need to give other tweaks a chance to do work first
            for o_tweak in top_dict[False]:
                o_tweak.tweak_build_patch(log, tweak_counter[o_tweak],
                                          self.patchFile)
            poolable_tweaks = top_dict[True]
            if not poolable_tweaks: continue  # likely complex type, e.g. CELL
            for record in self.patchFile.tops[curr_top].getActiveRecords():
                for p_tweak in poolable_tweaks:  # type: MultiTweakItem
                    # Check if this tweak can actually change the record - just
                    # relying on the check in scanModFile is *not* enough.
                    # After all, another tweak or patcher could have made a
                    # copy of an entirely unrelated record that *it* was
                    # interested in that just happened to have the same record
                    # type
                    if p_tweak.wants_record(record):
                        # Give the tweak a chance to do its work, and remember
                        # that we now want to keep the record. Note that we
                        # can't break early here, because more than one tweak
                        # may want to touch this record
                        p_tweak.tweak_record(record)
                        keep(record.fid)
                        tweak_counter[p_tweak][record.fid[0]] += 1
        # We're done with all tweaks, give them a chance to clean up and do any
        # finishing touches (e.g. injecting records for GMST tweaks)
        for tweak in self.enabled_tweaks:
            tweak.finish_tweaking(self.patchFile)
        #--Sort Eyes/Hair
        final_eyes = {}
        defaultMaleHair = {}
        defaultFemaleHair = {}
        eyeNames  = {x.fid: x.full for x in patchFile.tops[b'EYES'].records}
        hairNames = {x.fid: x.full for x in patchFile.tops[b'HAIR'].records}
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
                race.hairs.sort(key=lambda x: hairNames.get(x))
                race.eyes.sort(key=lambda x: eyeNames.get(x))
                racesSorted.append(race.eid)
                keep(race.fid)
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
        self._srcMods(log)
        log(u'\n=== ' + _(u'Merged'))
        if not racesPatched:
            log(u'. ~~%s~~' % _(u'None'))
        else:
            for eid in sorted(racesPatched):
                log(u'* ' + eid)
        log(u'\n=== ' + _(u'Eyes/Hair Sorted'))
        if not racesSorted:
            log(u'. ~~%s~~' % _(u'None'))
        else:
            for eid in sorted(racesSorted):
                log(u'* ' + eid)
        log(u'\n=== ' + _(u'Eye Meshes Filtered'))
        if not racesFiltered:
            log(u'. ~~%s~~' % _(u'None'))
        else:
            log(_(u"In order to prevent 'googly eyes', incompatible eyes have "
                  u'been removed from the following races.'))
            for eid in sorted(racesFiltered):
                log(u'* ' + eid)
        if mod_npcsFixed:
            log(u'\n=== ' + _(u'Eyes/Hair Assigned for NPCs'))
            for srcMod in sorted(mod_npcsFixed):
                log(u'* %s: %d' % (srcMod, len(mod_npcsFixed[srcMod])))
        for tweak in self.enabled_tweaks: # type: MultiTweakItem
            tweak.tweak_log(log, tweak_counter[tweak])
