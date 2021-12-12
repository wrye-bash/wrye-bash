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
"""This module contains the MultiTweakItem classes that tweak RACE records."""

from collections import defaultdict
from .base import MultiTweakItem, MultiTweaker
from ... import bush
from ...bolt import attrgetter_cache

_vanilla_races = [u'argonian', u'breton', u'dremora', u'dark elf',
                  u'dark seducer', u'golden saint', u'high elf', u'imperial',
                  u'khajiit', u'nord', u'orc', u'redguard', u'wood elf']

class _ARaceTweak(MultiTweakItem):
    """ABC for race tweaks."""
    tweak_read_classes = b'RACE',
    tweak_log_msg = _(u'Races Tweaked: %(total_changed)d')
    tweak_races_data = None # sentinel, set by the tweaker

    def _calc_changed_face_parts(self, face_attr, collected_races_data):
        """Calculates a changes dictionary for the specified face attribute,
        using the specified collected races data."""
        changed_parts = defaultdict(list)
        #process hair lists
        if self.choiceValues[self.chosen][0] == 1:
            # Merge face parts only from vanilla races to custom parts
            for race in collected_races_data:
                if race in (b'HAIR', b'EYES'): continue # ugh
                old_r_data = collected_races_data[race][face_attr]
                for r in _vanilla_races:
                    if r in race:
                        new_r_data = collected_races_data[r][face_attr]
                        if new_r_data != old_r_data:
                            # Merge the data and combine it with data from
                            # previous iterations
                            merged_r_data = set(new_r_data + old_r_data +
                                                changed_parts[race])
                            changed_parts[race] = list(merged_r_data)
        else: # full back and forth merge!
            for race in collected_races_data:
                if race in (b'HAIR', b'EYES'): continue # ugh
                old_r_data = collected_races_data[race][face_attr]
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
                            new_r_data = collected_races_data[r][face_attr]
                            if new_r_data != old_r_data:
                                # Merge the data and combine it with data from
                                # previous iterations
                                merged_r_data = set(new_r_data + old_r_data +
                                                    changed_parts[race])
                                changed_parts[race] = list(merged_r_data)
        return changed_parts

    def _get_changed_eyes(self):
        """Returns the changed eyes dictionary. A cached wrapper around
        _calc_changed_face_parts."""
        try:
            return self._cached_changed_eyes
        except AttributeError:
            self._cached_changed_eyes = self._calc_changed_face_parts(
                u'eyes', self.tweak_races_data)
            return self._cached_changed_eyes

    def _get_changed_hairs(self):
        """Returns the changed hairs dictionary. A cached wrapper around
        _calc_changed_face_parts."""
        try:
            return self._cached_changed_hairs
        except AttributeError:
            self._cached_changed_hairs = self._calc_changed_face_parts(
               u'hairs', self.tweak_races_data)
            return self._cached_changed_hairs

# -----------------------------------------------------------------------------
class RaceTweak_BiggerOrcsAndNords(_ARaceTweak):
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
            getattr(record, a) != v for a, v in zip(
                self._tweak_attrs, self.choiceValues[self.chosen][0][is_orc]))

    def tweak_record(self, record):
        is_orc = u'orc' in record.full.lower()
        for tweak_attr, tweak_val in zip(
                self._tweak_attrs, self.choiceValues[self.chosen][0][is_orc]):
            setattr(record, tweak_attr, tweak_val)

# -----------------------------------------------------------------------------
class RaceTweak_MergeSimilarRaceHairs(_ARaceTweak):
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
        elif self.tweak_races_data is None: return True
        # Cached, so calling this over and over is fine
        changed_hairs = self._get_changed_hairs()
        rec_full = record.full.lower()
        return (rec_full in changed_hairs and
                record.hairs != changed_hairs[rec_full])

    def tweak_record(self, record):
        record.hairs = self._get_changed_hairs()[record.full.lower()]

# -----------------------------------------------------------------------------
class RaceTweak_MergeSimilarRaceEyes(_ARaceTweak):
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
        if self.tweak_races_data is None: return True
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
        tweak_data = self.tweak_races_data
        return tweak_data is None or getattr(
            record, race_attr) != tweak_data[race_sig]

    def tweak_record(self, record):
        race_sig, race_attr = self._sig_and_attr
        setattr(record, race_attr, self.tweak_races_data[race_sig])

# -----------------------------------------------------------------------------
class RaceTweak_AllHairs(_ARUnblockTweak):
    """Gives all races ALL hairs."""
    tweak_name = _(u'Races Have All Hairs')
    tweak_tip = _(u'Gives all races every available hair.')
    tweak_key = u'hairyraces'
    tweak_choices = [(u'get down tonight', 1)]
    _sig_and_attr = (b'HAIR', u'hairs')

# -----------------------------------------------------------------------------
class RaceTweak_AllEyes(_ARUnblockTweak):
    """Gives all races ALL eyes."""
    tweak_name = _(u'Races Have All Eyes')
    tweak_tip = _(u'Gives all races every available eye.')
    tweak_key = u'eyeyraces'
    tweak_choices = [(u'what a lot of eyes you have dear', 1)]
    _sig_and_attr = (b'EYES', u'eyes')

# -----------------------------------------------------------------------------
class _ARPlayableTweak(_ARaceTweak):
    """Shared code of playable hair/eyes tweaks."""
    tweak_choices = [(u'Get it done', 1)]

    def wants_record(self, record):
        return not record.flags.playable

    def tweak_record(self, record):
        record.flags.playable = True

class RaceTweak_PlayableEyes(_ARPlayableTweak):
    """Sets all eyes to be playable."""
    tweak_read_classes = b'EYES',
    tweak_name = _(u'Playable Eyes')
    tweak_tip = _(u'Sets all eyes to be playable.')
    tweak_key = u'playableeyes'
    tweak_log_msg = _(u'Eyes Tweaked: %(total_changed)d')

# -----------------------------------------------------------------------------
class RaceTweak_PlayableHairs(_ARPlayableTweak):
    """Sets all hairs to be playable."""
    tweak_read_classes = b'HAIR',
    tweak_name = _(u'Playable Hairs')
    tweak_tip = _(u'Sets all hairs to be playable.')
    tweak_key = u'playablehairs'
    tweak_log_msg = _(u'Hairs Tweaked: %(total_changed)d')

# -----------------------------------------------------------------------------
class RaceTweak_PlayableHeadParts(_ARPlayableTweak):
    """Sets all head parts to be playable."""
    tweak_read_classes = b'HDPT',
    tweak_name = _(u'Playable Head Parts')
    tweak_tip = _(u'Sets all head parts to be playable.')
    tweak_key = u'playable_head_parts'
    tweak_log_msg = _(u'Head Parts Tweaked: %(total_changed)d')

# -----------------------------------------------------------------------------
class _ARGenderlessTweak(_ARaceTweak):
    """Shared code of genderless hair/eyes tweaks."""
    tweak_choices = [(u'Get it done', 1)]

    def wants_record(self, record):
        return record.flags.notMale or record.flags.notFemale

    def tweak_record(self, record):
        record.flags.notMale = False
        record.flags.notFemale = False

class RaceTweak_GenderlessHairs(_ARGenderlessTweak):
    """Sets all hairs to be playable, regardless of gender."""
    tweak_read_classes = b'HAIR',
    tweak_name = _(u'Genderless Hairs')
    tweak_tip = _(u'Lets characters of any gender use any hair.')
    tweak_key = u'sexlesshairs'
    tweak_log_msg = _(u'Hairs Tweaked: %(total_changed)d')

# -----------------------------------------------------------------------------
class RaceTweak_GenderlessHeadParts(_ARGenderlessTweak):
    """Sets all head parts to be playable, regardless of gender."""
    tweak_read_classes = b'HDPT',
    tweak_name = _(u'Genderless Head Parts')
    tweak_tip = _(u'Lets characters of any gender use any head part.')
    tweak_key = u'genderless_head_parts'
    tweak_log_msg = _(u'Head Parts Tweaked: %(total_changed)d')

    def wants_record(self, record):
        # Exclude eyes and faces (types 2 & 3) because they just look wrong
        return record.hdpt_type not in (2, 3) and super(
            RaceTweak_GenderlessHeadParts, self).wants_record(record)

# -----------------------------------------------------------------------------
class _ARFBGGTweak(_ARaceTweak):
    """Forces behavior graph path to match the gender it's specified for."""
    tweak_choices = [(_(u'Match'), u'match_gender'),
                     (_(u'Invert'), u'invert_gender'),]
    # Variables based on whether or not we're targeting the female graph
    # (0 = male, 1 = female)
    _graph_defaults = (r'Actors\Character\DefaultMale.hkx',
                       r'Actors\Character\DefaultFemale.hkx')
    _graph_defaults_lower = tuple(g.lower() for g in reversed(_graph_defaults))
    _graph_attrs = (u'male_behavior_graph', u'female_behavior_graph')
    # Whether to target the male or female behavior graph
    _targets_female_graph = False

    def _set_cached_attrs(self, __attrget=attrgetter_cache):
        """Set the target attributes based on the selection the user made."""
        female_graph = self._targets_female_graph
        self._target_graph_getter = __attrget[self._graph_attrs[female_graph]]
        # Apply the inversion now if the user has chosen to invert
        if self.choiceValues[self.chosen][0] == u'invert_gender':
            female_graph = not female_graph
        self._target_graph_out = self._graph_defaults[female_graph]
        self._target_graph_in = self._graph_defaults_lower[female_graph]

    @property
    def get_target_graph(self):
        try:
            return self._target_graph_getter
        except AttributeError:
            self._set_cached_attrs()
            return self._target_graph_getter

    def wants_record(self, record):
        target_graph = self.get_target_graph(record)
        return (target_graph and target_graph.modPath.lower() ==
                self._target_graph_in)

    def tweak_record(self, record):
        self.get_target_graph(record).modPath = self._target_graph_out

class RaceTweak_ForceBehaviorGraphGender_Female(_ARFBGGTweak):
    tweak_name = _(u'Force Behavior Graph Gender: Female')
    tweak_tip = _(u'Controls whether certain races will use inverted gender '
                  u'animations (e.g. orcs).')
    tweak_key = u'force_behavior_graph_gender_female'
    _targets_female_graph = True

class RaceTweak_ForceBehaviorGraphGender_Male(_ARFBGGTweak):
    tweak_name = _(u'Force Behavior Graph Gender: Male')
    tweak_tip = _(u'Controls whether certain races will use inverted gender '
                  u'animations (e.g. orcs).')
    tweak_key = u'force_behavior_graph_gender_male'

# -----------------------------------------------------------------------------
class TweakRacesPatcher(MultiTweaker):
    """Tweaks race things."""
    _tweak_classes = {globals()[t] for t in bush.game.race_tweaks}

    def initData(self, progress):
        super(TweakRacesPatcher, self).initData(progress)
        if bush.game.race_tweaks_need_collection:
            self.collected_tweak_data = {b'EYES': [], b'HAIR': []}

    def scanModFile(self, modFile, progress):
        if bush.game.race_tweaks_need_collection:
            # Need to gather EYES/HAIR data for the tweaks
            tweak_data = self.collected_tweak_data
            for tweak_type in (b'EYES', b'HAIR'):
                if tweak_type not in modFile.tops: continue
                for record in modFile.tops[tweak_type].getActiveRecords():
                    tweak_data[tweak_type].append(record.fid)
        super(TweakRacesPatcher, self).scanModFile(modFile, progress)

    def buildPatch(self, log, progress):
        if (bush.game.race_tweaks_need_collection
                and b'RACE' in self.patchFile.tops):
            # Need to gather RACE data for the tweaks
            tweak_data = self.collected_tweak_data
            for record in self.patchFile.tops[b'RACE'].getActiveRecords():
                ##: Are these checks needed for the tweak data collection?
                # if not record.eyes:
                #     continue  # Sheogorath. Assume is handled correctly.
                # if not record.rightEye or not record.leftEye:
                #     continue # WIPZ race?
                # if re.match(u'^117[a-zA-Z]', record.eid, flags=re.U):
                #     continue  # x117 race?
                if record.full:
                    tweak_data[record.full.lower()] = {
                        u'hairs': record.hairs, u'eyes': record.eyes,
                        u'relations': record.relations}
            for race_tweak in self.enabled_tweaks:
                race_tweak.tweak_races_data = self.collected_tweak_data
        super(TweakRacesPatcher, self).buildPatch(log, progress)
