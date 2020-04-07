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
"""This module contains oblivion multitweak item patcher classes that belong
to the Gmst Multitweaker - as well as the GmstTweaker itself. Gmst stands
for game settings."""
from __future__ import print_function
from ... import bush # for game
from ...bolt import SubProgress, deprint, floats_equal
from ...brec import MreRecord, RecHeader
from ...exception import StateError
from ...patcher.base import AMultiTweaker, DynamicTweak
from ...patcher.patchers.base import MultiTweakItem, CBash_MultiTweakItem
from ...patcher.patchers.base import MultiTweaker, CBash_MultiTweaker

# Patchers: 30 ----------------------------------------------------------------
class _AGlobalsTweak(DynamicTweak):
    """Shared code of CBash/PBash globals tweaks."""
    tweak_read_classes = b'GLOB',

    @property
    def chosen_value(self):
        # Globals are always stored as floats, regardless of what the CS says
        return float(self.choiceValues[self.chosen][0])

    def wants_record(self, record):
        return (getattr(record, u'eid', None) and # skip missing and empty EDID
                record.eid.lower() == self.tweak_key and
                record.value != self.chosen_value)

    def _patchLog(self, log, count):
        if count: log(u'* ' + _(u'%s set to: %4.2f') % (
            self.tweak_name, self.chosen_value))

class GlobalsTweak(_AGlobalsTweak, MultiTweakItem):
    """set a global to specified value"""
    def buildPatch(self, log, progress, patchFile):
        """Build patch."""
        keep = patchFile.getKeeper()
        for record in patchFile.GLOB.records:
            if self.wants_record(record):
                record.value = self.chosen_value
                keep(record.fid)
                self._patchLog(log, 1)
                break

class CBash_GlobalsTweak(_AGlobalsTweak, CBash_MultiTweakItem):
    """Sets a global to specified value"""
    scanOrder = 29
    editOrder = 29

    def __init__(self, tweak_name, tweak_tip, tweak_key, *choices):
        super(CBash_GlobalsTweak, self).__init__(tweak_name, tweak_tip,
                                                 tweak_key, *choices)
        self.count = 0 ##: I hate this, can't we find a nicer way? :/

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                self.count = 1
                override.value = self.chosen_value
                record.UnloadRecord()
                record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        self._patchLog(log, self.count)

#------------------------------------------------------------------------------
# FIXME(inf) I moved this code out, it *definitely* doesn't belong here. This
#  is patcher config validation, it should be a popup for the user!
# is_oblivion = bush.game.fsName.lower() == u'oblivion'
# if is_oblivion and target_value < 0:
#     deprint(u"GMST values can't be negative - currently %s - "
#             u'skipping setting GMST.' % target_value)
#     return False
class _AGmstTweak(DynamicTweak):
    """Shared code of PBash/CBash GMST tweaks."""
    tweak_read_classes = b'GMST',

    @property
    def chosen_eids(self):
        return ((self.tweak_key,), self.tweak_key)[isinstance(self.tweak_key,
                                                              tuple)]

    @property
    def chosen_values(self): return self.choiceValues[self.chosen]

    @property
    def eid_was_itpo(self):
        try:
            return self._eid_was_itpo
        except AttributeError:
            self._eid_was_itpo = {e.lower(): False for e in self.chosen_eids}
            return self._eid_was_itpo

    def _find_chosen_value(self, wanted_eid):
        """Returns the value the user chose for the game setting with the
        specified editor ID. Note that wanted_eid must be lower-case!"""
        for test_eid, test_val in zip(self.chosen_eids, self.chosen_values):
            if wanted_eid == test_eid.lower():
                # FIXME(inf) Same for this too, just tell the user that they
                #  have to enter a float if the GMST starts with 'f'!
                if wanted_eid.startswith(u'f') and type(test_val) != float:
                    deprint(u'converting custom value to float for GMST %s: %s'
                            % (wanted_eid, test_val))
                    test_val = float(test_val)
                return test_val
        return None

    def _find_original_eid(self, lower_eid):
        """We need to find the original case of the EDID, otherwise getFMSTFid
        blows - plus the dumped record will look nicer :)."""
        for orig_eid in self.chosen_eids:
            if lower_eid == orig_eid.lower():
                return orig_eid
        return lower_eid # fallback, should never happen

    def wants_record(self, record):
        rec_eid = record.eid.lower()
        if rec_eid not in self.eid_was_itpo: return False # not needed
        target_val = self._find_chosen_value(rec_eid)
        if rec_eid.startswith(u'f'):
            ret_val = not floats_equal(record.value, target_val)
        else:
            ret_val = record.value != target_val
        # Remember whether the last entry was ITPO or not
        self.eid_was_itpo[rec_eid] = not ret_val
        return ret_val

    def _patchLog(self, log):
        if len(self.choiceLabels) > 1:
            if self.choiceLabels[self.chosen].startswith(_(u'Custom')):
                if isinstance(self.chosen_values[0], basestring):
                    log(u'* %s: %s %s' % (
                        self.tweak_name, self.choiceLabels[self.chosen],
                        self.chosen_values[0]))
                else:
                    log(u'* %s: %s %4.2f' % (
                        self.tweak_name, self.choiceLabels[self.chosen],
                        self.chosen_values[0]))
            else:
                log(u'* %s: %s' % (
                    self.tweak_name, self.choiceLabels[self.chosen]))
        else:
            log(u'* ' + self.tweak_name)

class GmstTweak(_AGmstTweak, MultiTweakItem):
    """Sets a gmst to specified value"""
    def buildPatch(self, log, progress, patchFile):
        """Build patch."""
        keep = patchFile.getKeeper()
        for record in patchFile.GMST.records:
            # Do case-insensitive comparisons
            if self.wants_record(record):
                rec_eid = record.eid.lower()
                # We don't need to inject a GMST for this EDID anymore
                self.eid_was_itpo[rec_eid] = True
                record.value = self._find_chosen_value(rec_eid)
                keep(record.fid)
        # Inject new records for any remaining EDIDs
        for remaining_eid, was_itpo in self.eid_was_itpo.iteritems():
            if not was_itpo:
                new_gmst = MreRecord.type_class[b'GMST'](RecHeader(b'GMST'))
                new_gmst.eid = self._find_original_eid(remaining_eid)
                new_gmst.value = self._find_chosen_value(remaining_eid)
                new_gmst.longFids = True
                new_gmst.fid = new_gmst.getGMSTFid()
                if new_gmst.fid is not None:
                    keep(new_gmst.fid)
                    patchFile.GMST.setRecord(new_gmst)
        self._patchLog(log)

class CBash_GmstTweak(_AGmstTweak, CBash_MultiTweakItem):
    """Sets a gmst to specified value"""
    scanOrder = 29
    editOrder = 29

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                rec_eid = record.eid.lower()
                # We don't need to create a GMST for this EDID anymore
                self.eid_was_itpo[rec_eid] = True
                override.value = self._find_chosen_value(rec_eid)
                record.UnloadRecord()
                record._RecordID = override._RecordID

    def finishPatch(self,patchFile,progress):
        """Edits the bashed patch file directly."""
        subProgress = SubProgress(progress)
        subProgress.setFull(max(len(self.chosen_values), 1))
        pstate = 0
        for remaining_eid, was_itpo in self.eid_was_itpo.iteritems():
            subProgress(pstate, _(u'Finishing GMST Tweaks...'))
            if not was_itpo:
                orig_eid = self._find_original_eid(remaining_eid)
                record = patchFile.create_GMST(orig_eid)
                if not record:
                    print(orig_eid)
                    print(patchFile.Current.Debug_DumpModFiles())
                    for conflict in patchFile.Current.LookupRecords(orig_eid,
                                                                    False):
                        print(conflict.GetParentMod().ModName)
                    raise StateError(u'Tweak Settings: Unable to create GMST!')
                record.value = self._find_chosen_value(remaining_eid)
            pstate += 1

    def buildPatchLog(self,log):
        """Will write to log."""
        self._patchLog(log)

#------------------------------------------------------------------------------
class _AGmstTweaker(AMultiTweaker):
    """Tweaks miscellaneous gmsts in miscellaneous ways."""
    _class_tweaks = [] # override in implemententations

    @classmethod
    def tweak_instances(cls):
        instances = []
        for clazz, game_tweaks in cls._class_tweaks:
            for tweak in game_tweaks:
                if isinstance(tweak, tuple):
                    instances.append(clazz(*tweak))
                elif isinstance(tweak, list):
                    args = tweak[0]
                    kwdargs = tweak[1]
                    instances.append(clazz(*args, **kwdargs))
        instances.sort(key=lambda a: a.tweak_name.lower())
        return instances

class GmstTweaker(MultiTweaker, _AGmstTweaker):
    """Tweaks miscellaneous gmsts in miscellaneous ways."""
    scanOrder = 29
    editOrder = 29
    _class_tweaks = [(GlobalsTweak, bush.game.GlobalsTweaks),
                    (GmstTweak, bush.game.GmstTweaks)]

class CBash_GmstTweaker(CBash_MultiTweaker, _AGmstTweaker):
    """Tweaks miscellaneous gmsts in miscellaneous ways."""
    _class_tweaks = [(CBash_GlobalsTweak, bush.game.GlobalsTweaks),
                     (CBash_GmstTweak, bush.game.GmstTweaks)]
