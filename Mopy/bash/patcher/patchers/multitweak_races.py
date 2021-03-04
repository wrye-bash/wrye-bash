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
"""This module contains the Oblivion MultiTweakItem classes that tweak RACE
records. As opposed to the rest of the multitweak items these are not grouped
by a MultiTweaker but by the RacePatcher (see _race_records.py)."""

from itertools import izip

from .base import MultiTweakItem

_vanilla_races = [u'argonian', u'breton', u'dremora', u'dark elf',
                  u'dark seducer', u'golden saint', u'high elf', u'imperial',
                  u'khajiit', u'nord', u'orc', u'redguard', u'wood elf']

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
            getattr(record, a) != v for a, v in izip(
                self._tweak_attrs, self.choiceValues[self.chosen][0][is_orc]))

    def tweak_record(self, record):
        is_orc = u'orc' in record.full.lower()
        for tweak_attr, tweak_val in izip(
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
        elif self._tweak_races_data is None: return True
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
    def wants_record(self, record):
        return not record.flags.playable

    def tweak_record(self, record):
        record.flags.playable = True

# -----------------------------------------------------------------------------
class RaceTweak_PlayableEyes(_ARPlayableTweak):
    """Sets all eyes to be playable."""
    tweak_read_classes = b'EYES',
    tweak_name = _(u'Playable Eyes')
    tweak_tip = _(u'Sets all eyes to be playable.')
    tweak_key = u'playableeyes'
    tweak_choices = [(u'Get it done', 1)]
    tweak_log_msg = _(u'Eyes Tweaked: %(total_changed)d')

# -----------------------------------------------------------------------------
class RaceTweak_PlayableHairs(_ARPlayableTweak):
    """Sets all hairs to be playable."""
    tweak_read_classes = b'HAIR',
    tweak_name = _(u'Playable Hairs')
    tweak_tip = _(u'Sets all Hairs to be playable.')
    tweak_key = u'playablehairs'
    tweak_choices = [(u'Get it done', 1)]
    tweak_log_msg = _(u'Hairs Tweaked: %(total_changed)d')

# -----------------------------------------------------------------------------
class RaceTweak_SexlessHairs(_ARaceTweak):
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
