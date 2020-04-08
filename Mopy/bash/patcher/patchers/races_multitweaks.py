# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This module contains the oblivion MultitweakItem patcher classes that tweak
races records. As opposed to the rest of the multitweak items these are not
grouped by a MultiTweaker but by the RacePatcher (also in this module) which
is a special patcher. Notice the PBash ones do not log in buildPatch - the
RacesTweaker patcher was calling their "log" method - now super's _patchLog()
"""

from __future__ import print_function
import random
import re
from collections import defaultdict, Counter
# Internal
from ... import bosh, bush
from ...bolt import SubProgress, GPath, deprint
from ...brec import MreRecord, MelObject, strFid
from ...cint import ValidateDict, FormID
from ...exception import AbstractError, BoltError
from ...mod_files import ModFile, LoadFactory
from ...patcher.base import AMultiTweakItem, AListPatcher, AMultiTweaker
from .base import MultiTweakItem, CBash_MultiTweakItem, SpecialPatcher, \
    ListPatcher, CBash_ListPatcher, CBash_MultiTweaker

# Utilities & Constants -------------------------------------------------------
def _find_vanilla_eyes():
    """Converts vanilla default_eyes to use long FormIDs and returns the
    result."""
    def _conv_fid(race_fid): return GPath(race_fid[0]), race_fid[1]
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

class _ARaceTweakItem(AMultiTweakItem):
    """ABC for race tweaks."""
    tweak_read_classes = b'RACE',
    tweak_log_msg = _(u'Races Tweaked: %(total_changed)d')

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
        """Returns the changed eyes dictionary. A cached CBash/PBash-agnostic
        wrapper around _calc_changed_face_parts."""
        try:
            return self._cached_changed_eyes
        except AttributeError:
            self._cached_changed_eyes = self._calc_changed_face_parts(
                u'eyes', self._get_races_data())
            return self._cached_changed_eyes

    def _get_changed_hairs(self):
        """Returns the changed hairs dictionary. A cached CBash/PBash-agnostic
        wrapper around _calc_changed_face_parts."""
        try:
            return self._cached_changed_hairs
        except AttributeError:
            self._cached_changed_hairs = self._calc_changed_face_parts(
               u'hairs', self._get_races_data())
            return self._cached_changed_hairs

    def _get_races_data(self):
        """Returns the collected race data. Needs different implementations for
        CBash and PBash."""
        raise AbstractError()

class _PRaceTweak(_ARaceTweakItem, MultiTweakItem):
    """Shared code of PBash race tweaks."""
    _tweak_races_data = None # sentinel, set in RacePatcher.buildPatch

    def __init__(self):
        super(_PRaceTweak, self).__init__()
        self.tweak_count = Counter()

    def _get_races_data(self):
        return self._tweak_races_data

    def buildPatch(self, progress, patchFile):
        raise AbstractError(u'buildPatch not implemented')

class _CRaceTweak(_ARaceTweakItem, CBash_MultiTweakItem):
    def _get_races_data(self):
        return self.patchFile.races_data

# -----------------------------------------------------------------------------
class ARaceTweaker_BiggerOrcsAndNords(_ARaceTweakItem):
    """Adjusts the Orc and Nord race records to be taller/heavier."""
    tweak_read_classes = b'RACE',
    tweak_name = _(u'Bigger Nords and Orcs')
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
            getattr(record, a) != v for a, v in zip(
                self._tweak_attrs, self.choiceValues[self.chosen][0][is_orc]))

    # This sounds like a good concept, doesn't it? Later in this branch ;)
    def _tweak_record(self, record):
        is_orc = u'orc' in record.full.lower()
        for tweak_attr, tweak_val in zip(
                self._tweak_attrs,
                self.choiceValues[self.chosen][0][is_orc]):
            setattr(record, tweak_attr, tweak_val)

class RaceTweaker_BiggerOrcsAndNords(ARaceTweaker_BiggerOrcsAndNords,
                                     _PRaceTweak):
    def buildPatch(self, progress, patchFile):
        """Edits patch file as desired."""
        keep = patchFile.getKeeper()
        for record in patchFile.RACE.records:
            if self.wants_record(record):
                self._tweak_record(record)
                keep(record.fid)
                self.tweak_count[record.fid[0]] += 1

class CBash_RaceTweaker_BiggerOrcsAndNords(ARaceTweaker_BiggerOrcsAndNords,
                                           _CRaceTweak):
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                self._tweak_record(record)
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

# -----------------------------------------------------------------------------
class ARaceTweaker_MergeSimilarRaceHairs(_ARaceTweakItem):
    """Merges similar race's hairs (kinda specifically designed for SOVVM's
    bearded races)."""
    tweak_name = _(u'Merge Hairs from similar races')
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
        elif self._get_races_data() is None: return True
        # Cached, so calling this over and over is fine
        changed_hairs = self._get_changed_hairs()
        rec_full = record.full.lower()
        return (rec_full in changed_hairs and
                record.hairs != changed_hairs[rec_full])

class RaceTweaker_MergeSimilarRaceHairs(ARaceTweaker_MergeSimilarRaceHairs,
                                        _PRaceTweak):
    def buildPatch(self, progress, patchFile):
        """Edits patch file as desired."""
        keep = patchFile.getKeeper()
        changed_hairs = self._get_changed_hairs()
        for record in patchFile.RACE.records:
            if self.wants_record(record):
                record.hairs = changed_hairs[record.full.lower()]
                keep(record.fid)
                self.tweak_count[record.fid[0]] += 1

class CBash_RaceTweaker_MergeSimilarRaceHairs(
    ARaceTweaker_MergeSimilarRaceHairs, _CRaceTweak):
    def apply(self, modFile, record, bashTags):
        """Edits patch file as desired. """
        changed_hairs = self._get_changed_hairs()
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.hairs = changed_hairs[override.full.lower()]
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

# -----------------------------------------------------------------------------
class ARaceTweaker_MergeSimilarRaceEyes(_ARaceTweakItem):
    """Merges similar race's eyes."""
    tweak_name = _(u'Merge Eyes from similar races')
    tweak_tip = _(u'Merges eye lists from similar races (f.e. give RBP khajit '
                  u'eyes to all the other varieties of khajits in Elsweyr)')
    tweak_key = u'MergeSimilarRaceEyeLists'
    tweak_choices = [(_(u'Merge eyes only from vanilla races'), 1),
                     (_(u'Full eye merge between similar races'), 0)]

    def wants_record(self, record):
        if not record.full: return False
        # If this is None, we don't have race data yet and have to blindly
        # forward records until the patcher sends it to us
        if self._get_races_data() is None: return True
        # Cached, so calling this over and over is fine
        changed_eyes = self._get_changed_eyes()
        rec_full = record.full.lower()
        return (rec_full in changed_eyes and
                record.eyes != changed_eyes[rec_full])

class RaceTweaker_MergeSimilarRaceEyes(ARaceTweaker_MergeSimilarRaceEyes,
                                       _PRaceTweak):
    def buildPatch(self, progress, patchFile):
        """Edits patch file as desired."""
        keep = patchFile.getKeeper()
        changed_eyes = self._get_changed_eyes()
        for record in patchFile.RACE.records:
            if self.wants_record(record):
                record.eyes = changed_eyes[record.full.lower()]
                keep(record.fid)
                self.tweak_count[record.fid[0]] += 1

class CBash_RaceTweaker_MergeSimilarRaceEyes(ARaceTweaker_MergeSimilarRaceEyes,
                                             _CRaceTweak):
    def apply(self, modFile, record, bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.eyes = self._get_changed_eyes()[record.full.lower()]
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

# -----------------------------------------------------------------------------
class _ARUnblockTweak(_ARaceTweakItem):
    """Shared code of CBash/PBash 'races have all X' tweaks."""
    # First item is the record signature to retrieve race data for, second item
    # is the record attribute to patch
    _sig_and_attr = (b'OVERRIDE', u'OVERRIDE')

    def wants_record(self, record):
        race_sig, race_attr = self._sig_and_attr
        # If this is None, we don't have race data yet and have to blindly
        # forward records until the patcher sends it to us
        tweak_data = self._get_races_data()
        return tweak_data is None or getattr(
            record, race_attr) != tweak_data[race_sig]

class _PRUnblockTweak(_ARUnblockTweak, _PRaceTweak):
    """Shared code of PBash 'races have all X' tweaks."""
    def buildPatch(self, progress, patchFile):
        """Edits patch file as desired."""
        keep = patchFile.getKeeper()
        for record in patchFile.RACE.records:
            if self.wants_record(record):
                race_sig, race_attr = self._sig_and_attr
                setattr(record, race_attr, self._get_races_data()[race_sig])
                keep(record.fid)
                self.tweak_count[record.fid[0]] += 1

class _CRUnblockTweak(_ARUnblockTweak, _CRaceTweak):
    """Shared code of CBash 'races have all X' tweaks."""
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                race_sig, race_attr = self._sig_and_attr
                setattr(override, race_attr, self._get_races_data()[race_sig])
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

# -----------------------------------------------------------------------------
class ARaceTweaker_AllHairs(_ARUnblockTweak):
    """Gives all races ALL hairs."""
    tweak_name = _(u'Races Have All Hairs')
    tweak_tip = _(u'Gives all races every available hair.')
    tweak_key = u'hairyraces'
    tweak_choices = [(u'get down tonight', 1)]
    _sig_and_attr = (b'HAIR', u'hairs')

class RaceTweaker_AllHairs(ARaceTweaker_AllHairs, _PRUnblockTweak): pass
class CBash_RaceTweaker_AllHairs(ARaceTweaker_AllHairs, _CRUnblockTweak): pass

# -----------------------------------------------------------------------------
class ARaceTweaker_AllEyes(_ARUnblockTweak):
    """Gives all races ALL eyes."""
    tweak_name = _(u'Races Have All Eyes')
    tweak_tip = _(u'Gives all races every available eye.')
    tweak_key = u'eyeyraces'
    tweak_choices = [(u'what a lot of eyes you have dear', 1)]
    _sig_and_attr = (b'EYES', u'eyes')

class RaceTweaker_AllEyes(ARaceTweaker_AllEyes, _PRUnblockTweak): pass
class CBash_RaceTweaker_AllEyes(ARaceTweaker_AllEyes, _CRUnblockTweak): pass

# -----------------------------------------------------------------------------
class _PPlayableTweak(_PRaceTweak):
    """Shared code of PBash playable hair/eyes tweaks."""
    def wants_record(self, record):
        return not record.flags.playable

    def buildPatch(self, progress, patchFile):
        """Edits patch file as desired."""
        keep = patchFile.getKeeper()
        for record in getattr(patchFile, unicode(self.tweak_read_classes[0]),
                              u'ascii').records:
            if self.wants_record(record):
                record.flags.playable = True
                keep(record.fid)
                self.tweak_count[record.fid[0]] += 1

class _CPlayableTweak(_CRaceTweak):
    """Shared code of CBash playable hair/eyes tweaks."""
    def wants_record(self, record):
        return not record.IsPlayable

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.IsPlayable = True
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

# -----------------------------------------------------------------------------
class ARaceTweaker_PlayableEyes(_ARaceTweakItem):
    """Sets all eyes to be playable."""
    tweak_read_classes = b'EYES',
    tweak_name = _(u'Playable Eyes')
    tweak_tip = _(u'Sets all eyes to be playable.')
    tweak_key = u'playableeyes'
    tweak_choices = [(u'Get it done', 1)]
    tweak_log_msg = _(u'Eyes Tweaked: %(total_changed)d')

class RaceTweaker_PlayableEyes(ARaceTweaker_PlayableEyes,
                               _PPlayableTweak): pass
class CBash_RaceTweaker_PlayableEyes(ARaceTweaker_PlayableEyes,
                                     _CPlayableTweak): pass

# -----------------------------------------------------------------------------
class ARaceTweaker_PlayableHairs(_ARaceTweakItem):
    """Sets all hairs to be playable."""
    tweak_read_classes = b'HAIR',
    tweak_name = _(u'Playable Hairs')
    tweak_tip = _(u'Sets all Hairs to be playable.')
    tweak_key = u'playablehairs'
    tweak_choices = [(u'Get it done', 1)]
    tweak_log_msg = _(u'Hairs Tweaked: %(total_changed)d')

class RaceTweaker_PlayableHairs(ARaceTweaker_PlayableHairs,
                                _PPlayableTweak): pass
class CBash_RaceTweaker_PlayableHairs(ARaceTweaker_PlayableHairs,
                                      _CPlayableTweak): pass

# -----------------------------------------------------------------------------
class ARaceTweaker_SexlessHairs(_ARaceTweakItem):
    """Sets all hairs to be playable by both males and females."""
    tweak_read_classes = b'HAIR',
    tweak_name = _(u'Sexless Hairs')
    tweak_tip = _(u'Lets any sex of character use any hair.')
    tweak_key = u'sexlesshairs'
    tweak_choices = [(u'Get it done', 1)]
    tweak_log_msg = _(u'Hairs Tweaked: %(total_changed)d')

class RaceTweaker_SexlessHairs(ARaceTweaker_SexlessHairs, _PRaceTweak):
    def wants_record(self, record):
        return record.flags.notMale or record.flags.notFemale

    def buildPatch(self, progress, patchFile):
        """Edits patch file as desired."""
        keep = patchFile.getKeeper()
        for record in patchFile.HAIR.records:
            if self.wants_record(record):
                record.flags.notMale = False
                record.flags.notFemale = False
                keep(record.fid)
                self.tweak_count[record.fid[0]] += 1

class CBash_RaceTweaker_SexlessHairs(ARaceTweaker_SexlessHairs,
                                     _CRaceTweak):
    def wants_record(self, record):
        return record.IsNotFemale or record.IsNotMale

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.IsNotFemale = False
                override.IsNotMale = False
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
# Race Patcher ----------------------------------------------------------------
#------------------------------------------------------------------------------
class RacePatcher(AMultiTweaker, ListPatcher):
    """Race patcher - we inherit from AMultiTweaker to use tweak_instances."""
    group = _(u'Special')
    scanOrder = 40
    editOrder = 40
    _read_write_records = ('RACE', 'EYES', 'HAIR', 'NPC_',)
    _tweak_classes = [RaceTweaker_BiggerOrcsAndNords,
        RaceTweaker_MergeSimilarRaceHairs, RaceTweaker_MergeSimilarRaceEyes,
        RaceTweaker_PlayableEyes, RaceTweaker_PlayableHairs,
        RaceTweaker_SexlessHairs, RaceTweaker_AllEyes, RaceTweaker_AllHairs, ]

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
        self.scanTypes = {'RACE', 'EYES', 'HAIR', 'NPC_'}
        self.vanilla_eyes = _find_vanilla_eyes()
        self.enabled_tweaks = enabled_tweaks

    def initData(self,progress):
        """Get data from source files."""
        # HACK - wholesale copy of MultiTweaker.initData, see #494
        # Has to come before the srcs check, because of isActive nonsense this
        # patcher will still run and blow up in scanModFile otherwise
        self._tweak_dict = t_dict = defaultdict(lambda: ([], []))
        for tweak in self.enabled_tweaks: # type: _PRaceTweak
            for read_sig in tweak.getReadClasses():
                t_dict[read_sig][tweak.supports_pooling].append(tweak)
        if not self.isActive or not self.srcs: return
        loadFactory = LoadFactory(False,MreRecord.type_class['RACE'])
        progress.setFull(len(self.srcs))
        cachedMasters = {}
        for index,srcMod in enumerate(self.srcs):
            if srcMod not in bosh.modInfos: continue
            srcInfo = bosh.modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            bashTags = srcInfo.getBashTags()
            if 'RACE' not in srcFile.tops: continue
            self.tempRaceData = {} #so as not to carry anything over!
            if u'R.ChangeSpells' in bashTags and u'R.AddSpells' in bashTags:
                raise BoltError(
                    u'WARNING mod %s has both R.AddSpells and R.ChangeSpells '
                    u'tags - only one of those tags should be on a mod at '
                    u'one time' % srcMod.s)
            for race in srcFile.RACE.getActiveRecords():
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
                    if 'RACE' not in masterFile.tops: continue
                    cachedMasters[master] = masterFile
                for race in masterFile.RACE.getActiveRecords():
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
        modName = modFile.fileInfo.name
        if not (set(modFile.tops) & self.scanTypes): return
        srcEyes = set(
            [record.fid for record in modFile.EYES.getActiveRecords()])
        #--Eyes, Hair
        for type in ('EYES','HAIR'):
            patchBlock = getattr(self.patchFile,type)
            id_records = patchBlock.id_records
            for record in getattr(modFile,type).getActiveRecords():
                races_data[type].append(record.fid)
                if record.fid not in id_records:
                    patchBlock.setRecord(record.getTypeCopy())
        #--Npcs with unassigned eyes
        patchBlock = self.patchFile.NPC_
        id_records = patchBlock.id_records
        for record in modFile.NPC_.getActiveRecords():
            if not record.eye and record.fid not in id_records:
                patchBlock.setRecord(record.getTypeCopy())
        #--Race block
        patchBlock = self.patchFile.RACE
        id_records = patchBlock.id_records
        for record in modFile.RACE.getActiveRecords():
            if record.fid not in id_records:
                patchBlock.setRecord(record.getTypeCopy())
            if not record.rightEye or not record.leftEye:
                # Don't complain if the FULL is missing, that probably means
                # it's an internal or unused RACE
                if record.full:
                    deprint(u'No right and/or no left eye recorded in race '
                            u'%s, from mod %s' % (record.full, modName))
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
                for p_tweak in poolable_tweaks: # type: _PRaceTweak
                    if p_tweak.wants_record(record):
                        pool_record(record)
                        break # Exit as soon as a tweak is interested
        # Finally, copy all pooled records in one fell swoop
        for rsig, pooled_records in rec_pool.iteritems():
            if pooled_records: # only copy if we could pool
                getattr(self.patchFile, rsig.decode(u'ascii')).copy_records(
                    pooled_records)

    def buildPatch(self,log,progress):
        """Updates races as needed."""
        debug = False
        tweak_data = self.races_data
        if not self.isActive: return
        patchFile = self.patchFile
        keep = patchFile.getKeeper()
        if 'RACE' not in patchFile.tops: return
        racesPatched = []
        racesSorted = []
        racesFiltered = []
        mod_npcsFixed = {}
        reProcess = re.compile(
            u'(?:dremora)|(?:akaos)|(?:lathulet)|(?:orthe)|(?:ranyu)',
            re.I | re.U)
        #--Import race info
        for race in patchFile.RACE.records:
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
                oldRelations = set((x.faction,x.mod) for x in race.relations)
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
        for race in patchFile.RACE.records:
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
                maxEyesMesh = \
                    sorted(mesh_eye.keys(), key=lambda a: len(mesh_eye[a]),
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
        for tweak in self.enabled_tweaks: # type: _PRaceTweak
            tweak._tweak_races_data = tweak_data
            tweak.buildPatch(progress, self.patchFile)
        #--Sort Eyes/Hair
        final_eyes = {}
        defaultMaleHair = {}
        defaultFemaleHair = {}
        eyeNames  = dict((x.fid,x.full) for x in patchFile.EYES.records)
        hairNames = dict((x.fid,x.full) for x in patchFile.HAIR.records)
        maleHairs = set(
            x.fid for x in patchFile.HAIR.records if not x.flags.notMale)
        femaleHairs = set(
            x.fid for x in patchFile.HAIR.records if not x.flags.notFemale)
        for race in patchFile.RACE.records:
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
        for npc in patchFile.NPC_.records:
            if npc.fid == (_main_master, 0x000007): continue  #
            # skip player
            if npc.full is not None and npc.race == (
                    _main_master, 0x038010) and not reProcess.search(
                    npc.full): continue
            raceEyes = final_eyes.get(npc.race)
            if not npc.eye and raceEyes:
                npc.eye = random.choice(raceEyes)
                srcMod = npc.fid[0]
                if srcMod not in mod_npcsFixed: mod_npcsFixed[srcMod] = set()
                mod_npcsFixed[srcMod].add(npc.fid)
                keep(npc.fid)
            raceHair = (
                (defaultMaleHair, defaultFemaleHair)[npc.flags.female]).get(
                npc.race)
            if not npc.hair and raceHair:
                npc.hair = random.choice(raceHair)
                srcMod = npc.fid[0]
                if srcMod not in mod_npcsFixed: mod_npcsFixed[srcMod] = set()
                mod_npcsFixed[srcMod].add(npc.fid)
                keep(npc.fid)
            if not npc.hairLength:
                npc.hairLength = random.random()
                srcMod = npc.fid[0]
                if srcMod not in mod_npcsFixed: mod_npcsFixed[srcMod] = set()
                keep(npc.fid)
                if npc.fid in mod_npcsFixed[srcMod]: continue
                mod_npcsFixed[srcMod].add(npc.fid)

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
                  u"been removed from the following races."))
            for eid in sorted(racesFiltered):
                log(u'* ' + eid)
        if mod_npcsFixed:
            log(u'\n=== ' + _(u'Eyes/Hair Assigned for NPCs'))
            for srcMod in sorted(mod_npcsFixed):
                log(u'* %s: %d' % (srcMod.s,len(mod_npcsFixed[srcMod])))
        for tweak in self.enabled_tweaks: # type: _PRaceTweak
            tweak._patchLog(log, tweak.tweak_count)

#-------------------------- CBash only RacePatchers --------------------------#
class _CBashOnlyRacePatchers(SpecialPatcher, AListPatcher):
    iiMode = False
    scanRequiresChecked = True
    _read_write_records = ('RACE',)

    def initData(self, progress):
        if not self.isActive: return
        for top_group_sig in self.getTypes():
            self.patchFile.group_patchers[top_group_sig].append(self)

class CBash_RacePatcher_Relations(_CBashOnlyRacePatchers):
    """Merges changes to race relations."""
    autoKey = {u'R.Relations'}

    def __init__(self, p_name, p_file, p_sources):
        super(CBash_RacePatcher_Relations, self).__init__(p_name, p_file,
                                                          p_sources)
        self.racesPatched = set()
        self.fid_faction_mod = {}

    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        if bashTags & self.autoKey:
            relations = record.ConflictDetails(('relations_list',))
            if relations:
                self.fid_faction_mod.setdefault(record.fid, {}).update(
                    relations['relations_list'])

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        fid = record.fid
        if fid in self.fid_faction_mod:
            newRelations = set((faction, mod) for faction, mod in
                               self.fid_faction_mod[fid].iteritems() if
                               faction.ValidateFormID(self.patchFile))
            curRelations = set(record.relations_list)
            changed = newRelations - curRelations
            if changed:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for faction,mod in changed:
                        for relation in override.relations:
                            if relation.faction == faction:
                                relation.mod = mod
                                break
                        else:
                            relation = override.create_relation()
                            relation.faction,relation.mod = faction,mod
                    self.racesPatched.add(record.eid)
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

class CBash_RacePatcher_Imports(_CBashOnlyRacePatchers):
    """Imports various race fields."""
    tag_attrs = {
        u'Hair'  : ('hairs',),
        u'Body-M': ('maleTail_list','maleUpperBodyPath','maleLowerBodyPath',
                    'maleHandPath', 'maleFootPath', 'maleTailPath'),
        u'Body-F': ('femaleTail_list','femaleUpperBodyPath',
                    'femaleLowerBodyPath', 'femaleHandPath', 'femaleFootPath',
                    'femaleTailPath'),
        u'Body-Size-M': ('maleHeight','maleWeight'),
        u'Body-Size-F': ('femaleHeight','femaleWeight'),
        u'Voice-M': ('maleVoice',),
        u'Voice-F': ('femaleVoice',),
        u'R.Teeth': ('teethLower_list','teethUpper_list',),
        u'R.Mouth': ('mouth_list','tongue_list',),
        u'R.Ears': ('maleEars_list','femaleEars_list',),
        u'R.Head': ('head_list','fggs_p','fgga_p','fgts_p','snam_p'),
        u'R.Attributes-M': ('maleStrength','maleIntelligence','maleWillpower',
                            'maleAgility', 'maleSpeed', 'maleEndurance',
                            'malePersonality', 'maleLuck'),
        u'R.Attributes-F': ('femaleStrength','femaleIntelligence',
                            'femaleWillpower', 'femaleAgility', 'femaleSpeed',
                            'femaleEndurance', 'femalePersonality',
                            'femaleLuck'),
        u'R.Skills': ('skill1','skill1Boost','skill2','skill2Boost','skill3',
                      'skill3Boost', 'skill4', 'skill4Boost', 'skill5',
                      'skill5Boost', 'skill6', 'skill6Boost', 'skill7',
                      'skill7Boost'),
        u'R.Description': ('text',),
        }
    autoKey = set(tag_attrs)

    def __init__(self, p_name, p_file, p_sources):
        super(CBash_RacePatcher_Imports, self).__init__(p_name, p_file,
                                                        p_sources)
        self.racesPatched = set()
        self.fid_attr_value = defaultdict(dict)

    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        recordId = record.fid
        for bashKey in bashTags & self.autoKey:
            attrs = self.tag_attrs[bashKey]
            if bashKey == u'Hair':
                hairs = self.fid_attr_value[recordId].get('hairs', [])
                hairs.extend([hair for hair in record.hairs if
                              hair.ValidateFormID(
                                  self.patchFile) and hair not in hairs])
                attr_value = {'hairs':hairs}
            else:
                attr_value = record.ConflictDetails(attrs)
                if not ValidateDict(attr_value, self.patchFile):
                    self.patchFile.patcher_mod_skipcount[self._patcher_name][
                        modFile.GName] += 1
                    continue
            self.fid_attr_value[recordId].update(attr_value)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        prev_attr_value = self.fid_attr_value.get(recordId,None)

        if prev_attr_value:
            cur_attr_value = dict(
                (attr, getattr(record, attr)) for attr in prev_attr_value)
            if cur_attr_value != prev_attr_value:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_attr_value.iteritems():
                        setattr(override,attr,value)
                    self.racesPatched.add(record.eid)
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

class CBash_RacePatcher_Spells(_CBashOnlyRacePatchers):
    """Merges changes to race spells."""
    autoKey = {u'R.AddSpells', u'R.ChangeSpells'}

    def __init__(self, p_name, p_file, p_sources):
        super(CBash_RacePatcher_Spells, self).__init__(p_name, p_file,
                                                       p_sources)
        self.racesPatched = set()
        self.id_spells = defaultdict(set)

    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        tags = bashTags & self.autoKey
        if tags:
            if u'R.ChangeSpells' in tags and u'R.AddSpells' in tags:
                raise BoltError(
                    u'WARNING mod %s has both R.AddSpells and R.ChangeSpells '
                    u'tags - only one of those tags should be on a mod at '
                    u'one time' % modFile.ModName)
            curSpells = set([spell for spell in record.spells if
                             spell.ValidateFormID(self.patchFile)])
            if curSpells:
                if u'R.ChangeSpells' in tags:
                    self.id_spells[record.fid] = curSpells
                elif u'R.AddSpells' in tags:
                    self.id_spells[record.fid] |= curSpells

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        if recordId in self.id_spells:
            newSpells = self.id_spells[recordId]
            curSpells = set(record.spells)
            changed = newSpells - curSpells
            if changed:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.spells = newSpells
                    self.racesPatched.add(record.eid)
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

class CBash_RacePatcher_Eyes(_CBashOnlyRacePatchers):
    """Merges and filters changes to race eyes."""
    autoKey = {u'Eyes'}
    blueEye = FormID(_main_master, 0x27308)
    argonianEye = FormID(_main_master, 0x3e91e)
    dremoraRace = FormID(_main_master, 0x038010)
    reX117 = re.compile(u'^117[a-z]',re.I|re.U)
    scanRequiresChecked = False
    _read_write_records = ('EYES', 'HAIR', 'RACE')

    def __init__(self, p_name, p_file, p_sources):
        super(CBash_RacePatcher_Eyes, self).__init__(p_name, p_file, p_sources)
        self.isActive = True  #--Always partially enabled to support eye
        # filtering
        self.racesPatched = set()
        self.racesSorted = set()
        self.racesFiltered = []
        self.mod_npcsFixed = {}
        self.hairNames = {}
        self.eyeNames = {}
        self.maleHairs = set()
        self.femaleHairs = set()
        self.id_meshes = {}
        self.id_eyes = {}
        self.srcEyes = {}
        self.eye_meshes = {}
        self.finishedOnce = False
        self.vanilla_eyes = _find_vanilla_eyes()

    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        recordId = record.fid
        if record._Type == 'RACE':
            if record.IsWinning():
                if record.full:
                    self.patchFile.races_data[record.full.lower()] = {
                        'hairs': record.hairs, 'eyes': record.eyes,
                        'relations': record.relations}
            eye_meshes = self.eye_meshes
            srcEyes = self.srcEyes.get(modFile.GName,set())
            curEyes = set([eye for eye in record.eyes if
                           eye.ValidateFormID(self.patchFile)])
            eyePaths = (record.rightEye.modPath, record.leftEye.modPath)
            for eye in curEyes:
                # only map eyes that are (re)defined in this mod
                if eye not in eye_meshes or eye in srcEyes:
                    eye_meshes[eye] = eyePaths
            if modFile.GName in self.srcs and self.autoKey & bashTags:
                allEyes = self.id_eyes.setdefault(recordId,set())
                allEyes |= curEyes
                self.id_meshes[recordId] = eyePaths
        else:
            if not recordId.ValidateFormID(self.patchFile):
                self.patchFile.patcher_mod_skipcount[self._patcher_name][
                    modFile.GName] += 1
                return

            if record._Type == 'HAIR':
                self.patchFile.races_data['HAIR'].append(recordId)
                if record.IsMale:
                    self.maleHairs.add(recordId)
                else:
                    self.femaleHairs.add(recordId)
                self.hairNames.update({recordId:record.full})
            else: #record._Type == 'EYES'
                self.patchFile.races_data['EYES'].append(recordId)
                self.eyeNames.update({recordId:record.full})
                self.srcEyes.setdefault(modFile.GName,set()).add(recordId)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan(modFile,record,bashTags)
        if record._Type in ('HAIR','EYES'):
            return

        recordId = record.fid
        if self.isActive and (recordId in self.id_eyes):
            curEyes = set(record.eyes)
            newEyes = self.id_eyes[recordId]
            changed = newEyes - curEyes
            if not changed:
                newRightEye, newLeftEye = self.id_meshes[recordId]
                curRightEye, curLeftEye = (
                    record.rightEye.modPath, record.leftEye.modPath)
                changed = (newRightEye, newLeftEye) != \
                          (curRightEye, curLeftEye) #modPaths do case
                          #  insensitive comparison by default
            if changed:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.eyes = newEyes
                    override.rightEye.modPath, override.leftEye.modPath = \
                        self.id_meshes[recordId]
                    self.racesPatched.add(record.eid)
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def finishPatch(self,patchFile,progress):
        """Edits the bashed patch file directly."""
        #The patcher gets registered multiple times due to the multiple
        # getTypes
        #This ensures the finishPatch only runs once per bashed patch
        if self.finishedOnce: return
        self.finishedOnce = True
        racesSorted = self.racesSorted
        racesFiltered = self.racesFiltered
        mod_npcsFixed = self.mod_npcsFixed
        Current = patchFile.Current
        subProgress = SubProgress(progress)
        subProgress.setFull(max(len(Current.LoadOrderMods) * 2,1))
        reX117 = self.reX117
        final_eyes = {}
        defaultMaleHair = {}
        defaultFemaleHair = {}
        hairNames = self.hairNames
        eyeNames = self.eyeNames
        maleHairs = self.maleHairs
        femaleHairs = self.femaleHairs
        playableRaces = {self.dremoraRace}

        #--Eye Mesh filtering
        eye_meshes = self.eye_meshes
        try:
            blueEyeMeshes = eye_meshes[self.blueEye]
        except KeyError:
            print(_(
                u"Wrye Bash is low on memory and cannot complete building "
                u"the patch. This will likely succeed if you restart Wrye "
                u"Bash and try again. If it fails repeatedly, please report "
                u"it at the current official Wrye Bash thread at "
                u"https://www.afkmods.com/index.php?/topic/4966-wrye-bash-all-games/. "
                u"We apologize for the inconvenience."))
            return
        try:
            argonianEyeMeshes = eye_meshes[self.argonianEye]
        except KeyError:
            print(_(
                u"Wrye Bash is low on memory and cannot complete building "
                u"the patch. This will likely succeed if you restart Wrye "
                u"Bash and try again. If it fails repeatedly, please report "
                u"it at the current official Wrye Bash thread at "
                u"https://www.afkmods.com/index.php?/topic/4966-wrye-bash-all-games/. "
                u"We apologize for the inconvenience."))
            return
        fixedRaces = set()
        fixedNPCs = {
        FormID(_main_master, 0x000007)}  #causes player to be skipped
        for eye in (
            FormID(_main_master, 0x1a), #--Reanimate
            FormID(_main_master, 0x54bb9), #--Dark Seducer
            FormID(_main_master, 0x54bba), #--Golden Saint
            FormID(_main_master, 0x5fa43), #--Ordered
            self.dremoraRace,
            ):
            eye_meshes.setdefault(eye,blueEyeMeshes)
        def setRaceEyeMesh(race,rightPath,leftPath):
            race.rightEye.modPath = rightPath
            race.leftEye.modPath = leftPath
        #Scan hairs and eyes for later sorting and/or assigning to non-haired
        # npcs
        pstate = 0
        noEyes = 0
        noHair = 0
        for modFile in Current.LoadOrderMods:
            subProgress(pstate, _(u'Filtering eyes...')+u'\n')
            for race in modFile.RACE:
                recordId = race.fid
                if race.IsPlayable:
                    playableRaces.add(recordId)
                currentEyes = race.eyes
                if not currentEyes: continue  #--Sheogorath. Assume is
                # handled correctly.
                if not race.rightEye or not race.leftEye: continue  # no eye
                #  set for either right or left... skip.
                curRightEye, curLeftEye = race.rightEye.modPath, \
                                          race.leftEye.modPath
                if not curRightEye or not curLeftEye: continue  # --WIPZ race?
                if reX117.match(race.eid): continue  #-- x117 race?
                if recordId in fixedRaces: continue  #--already processed
                # once (added to patchFile, and now the patchFile is being
                # processed)
                #IsNewest
                if race.IsWinning():
                    raceChanged = False
                    currentMeshes = (curRightEye, curLeftEye)
                    meshes_eyes = {}
                    for eye in currentEyes:
                        if eye not in eye_meshes:
                            deprint(
                                _(u'Mesh undefined for eye %s in race %s') % (
                                    eye, race.eid))
                            continue
                        rightEye, leftEye = eye_meshes[eye]
                        meshes_eyes.setdefault((rightEye, leftEye), []).append(
                            eye)
                    try:
                        maxEyesMeshes = sorted(meshes_eyes.keys(),
                                               key=lambda a: len(
                                                   meshes_eyes[a]),
                                               reverse=True)[0]
                    except IndexError:
                        maxEyesMeshes = blueEyeMeshes
                    meshesCount = len(meshes_eyes)
                    #--Single eye mesh, but doesn't match current mesh?
                    if meshesCount == 1 and currentMeshes != maxEyesMeshes:
                        currentMeshes = maxEyesMeshes
                        currentEyes = meshes_eyes[maxEyesMeshes]
                        raceChanged = True
                    #--Multiple eye meshes (and playable)?
                    elif meshesCount > 1 and recordId in playableRaces:
                        #--If blueEyeMesh (mesh used for vanilla eyes) is
                        # present, use that.
                        if blueEyeMeshes in meshes_eyes and currentMeshes !=\
                                argonianEyeMeshes:
                            currentMeshes = blueEyeMeshes
                            currentEyes = meshes_eyes[blueEyeMeshes]
                            raceChanged = True
                        elif argonianEyeMeshes in meshes_eyes:
                            currentMeshes = argonianEyeMeshes
                            currentEyes = meshes_eyes[argonianEyeMeshes]
                            raceChanged = True
                        #--Else figure that current eye mesh is the correct one
                        elif currentMeshes in meshes_eyes:
                            currentEyes = meshes_eyes[currentMeshes]
                            raceChanged = True
                        #--Else use most popular eye mesh
                        else:
                            currentMeshes = maxEyesMeshes
                            currentEyes = meshes_eyes[maxEyesMeshes]
                            raceChanged = True
                    if raceChanged:
                        racesFiltered.append(race.eid)

                    #--Sort Eyes/Hair
                    oldHairs = race.hairs
                    currentHairs = oldHairs
                    if recordId in playableRaces:
                        currentHairs = sorted(oldHairs,
                                              key=lambda x: hairNames.get(x))
                        if currentHairs != oldHairs:
                            racesSorted.add(race.eid)
                            raceChanged = True
                        oldEyes = currentEyes
                        currentEyes = sorted(oldEyes,
                                             key=lambda x: eyeNames.get(x))
                        if currentEyes != oldEyes:
                            racesSorted.add(race.eid)
                            raceChanged = True
                        final_eyes[recordId] = [
                            x for x in self.vanilla_eyes.get(recordId, [])
                            if x in currentEyes] or currentEyes
                        defaultMaleHair[recordId] = [x for x in currentHairs if
                                                     x in maleHairs]
                        defaultFemaleHair[recordId] = [x for x in currentHairs
                                                       if x in femaleHairs]

                    if raceChanged:
                        fixedRaces.add(recordId)
                        override = race.CopyAsOverride(patchFile)
                        if override:
                            override.eyes = currentEyes
                            override.hairs = currentHairs
                            override.rightEye.modPath, \
                            override.leftEye.modPath = currentMeshes
                race.UnloadRecord()
            pstate += 1
        for modFile in Current.LoadOrderMods:
            #--Npcs with unassigned eyes/hair
            #--Must run after all race records have been processed
            subProgress(pstate, _(
                u'Assigning random eyes and hairs to npcs missing them...')
                        + u'\n')
            reProcess = re.compile(
                u'(?:dremora)|(?:akaos)|(?:lathulet)|(?:orthe)|(?:ranyu)',
                re.I | re.U)
            for npc in modFile.NPC_:
                recordId = npc.fid
                if recordId in fixedNPCs: continue  #--already processed
                # once (added to patchFile, and now the patchFile is being
                # processed)
                raceId = npc.race
                if raceId not in playableRaces: continue
                if npc.full is not None and raceId == self.dremoraRace and \
                        not reProcess.search(
                        npc.full): continue  # So as not to give OOO's
                # spectral warriors different hairs/eyes since they are
                # dremora race.
                #IsNewest
                if npc.IsWinning():
                    npcChanged = False
                    raceEyes = final_eyes.get(raceId)
                    eye = npc.eye
                    if eye is None and raceEyes:
                        eye = random.choice(raceEyes)
                        npcChanged = True
                    raceHair = ((defaultMaleHair, defaultFemaleHair)[
                            npc.IsFemale]).get(raceId)
                    hair = npc.hair
                    if hair is None and raceHair:
                        hair = random.choice(raceHair)
                        npcChanged = True
                    if npcChanged:
                        fixedNPCs.add(recordId)
                        override = npc.CopyAsOverride(patchFile)
                        if override:
                            override.eye = eye
                            override.hair = hair
                            if not override.hairLength:
                                override.hairLength = random.random()
                            mod_npcsFixed.setdefault(modFile.GName, set()).add(
                                recordId)
                npc.UnloadRecord()
            pstate += 1

class CBash_RacePatcher(CBash_MultiTweaker, CBash_ListPatcher):
    group = _(u'Special')
    scanOrder = 40
    editOrder = 40
    # CBash_RacePatcher is split in several sub-patchers to make it easier to
    # manage. Each one handles a group of tags that are processed similarly
    tweakers_cls = [CBash_RacePatcher_Relations, CBash_RacePatcher_Imports,
                    CBash_RacePatcher_Spells, CBash_RacePatcher_Eyes]
    _tweak_classes = [
        CBash_RaceTweaker_BiggerOrcsAndNords, CBash_RaceTweaker_PlayableHairs,
        CBash_RaceTweaker_PlayableEyes, CBash_RaceTweaker_SexlessHairs,
        CBash_RaceTweaker_MergeSimilarRaceEyes, CBash_RaceTweaker_AllEyes,
        CBash_RaceTweaker_AllHairs, CBash_RaceTweaker_MergeSimilarRaceHairs]

    def __init__(self, p_name, p_file, p_sources, enabled_tweaks):
        # NB: call the CBash_ListPatcher __init__ not the CBash_MultiTweaker!
        super(AMultiTweaker, self).__init__(p_name, p_file, p_sources)
        # this bit is from AMultiTweaker/CBash_MultiTweaker
        self.enabled_tweaks = enabled_tweaks
        for tweak in self.enabled_tweaks:
            tweak.patchFile = p_file
        self.tweakers = [tweak_cls(p_name, p_file, p_sources) for tweak_cls in
                         self.tweakers_cls] # p_name is not really used here
        # Otherwise you'd need at least one src mod to enable tweaks and eye
        # filtering. The isActive on the child patcher is *not* enough (#494).
        self.isActive = True

    def initData(self, progress):
        for tweaker in self.tweakers:
            tweaker.initData(progress)
        super(CBash_RacePatcher, self).initData(progress)

    def buildPatchLog(self,log):
        """Will write to log."""
        racesPatched = set()
        racesSorted = set()
        racesFiltered = []
        mod_npcsFixed = {}
        for tweak in self.tweakers:
            if hasattr(tweak, 'racesPatched'):
                racesPatched |= tweak.racesPatched
            if hasattr(tweak, 'racesSorted'):
                racesSorted |= tweak.racesSorted
            if hasattr(tweak, 'racesFiltered'):
                racesFiltered += tweak.racesFiltered
            if hasattr(tweak, 'mod_npcsFixed'):
                mod_npcsFixed.update(tweak.mod_npcsFixed)
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
                  u"been removed from the following races."))
            for eid in sorted(racesFiltered):
                log(u'* ' + eid)
        if mod_npcsFixed:
            log(u'\n=== ' + _(u'Eyes/Hair Assigned for NPCs'))
            for srcMod in sorted(mod_npcsFixed):
                log(u'* %s: %d' % ( ##: is the .tmp extension possible?
                    (srcMod.sbody if srcMod.cext == u'.tmp' else srcMod.s),
                    len(mod_npcsFixed[srcMod])))
        for tweak in self.enabled_tweaks: # this bit is from CBash_MultiTweaker
            tweak.buildPatchLog(log)
