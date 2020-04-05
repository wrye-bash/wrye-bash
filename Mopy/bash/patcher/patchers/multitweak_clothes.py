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
to the Clothes Multitweaker - as well as the ClothesTweaker itself."""
import itertools
from collections import Counter
from ...patcher.base import AMultiTweaker, DynamicNamedTweak
from ...patcher.patchers.base import MultiTweakItem, CBash_MultiTweakItem
from ...patcher.patchers.base import MultiTweaker, CBash_MultiTweaker

# Patchers: 30 ----------------------------------------------------------------
class AClothesTweak(DynamicNamedTweak):
    tweak_read_classes = b'CLOT',
    clothes_flags = {
        u'hoods':    0x00000002,
        u'shirts':   0x00000004,
        u'pants':    0x00000008,
        u'gloves':   0x00000010,
        u'amulets':  0x00000100,
        u'rings2':   0x00010000,
        u'amulets2': 0x00020000,
        #--Multi
        u'robes':    0x0000000C, # (1<<2) | (1<<3),
        u'rings':    0x000000C0, # (1<<6) | (1<<7),
    }

    def __init__(self, tweak_name, tweak_tip, key, *choices):
        super(AClothesTweak, self).__init__(tweak_name, tweak_tip, key,
                                            *choices)
        type_key = key[:key.find(u'.')]
        self.or_type_flags = type_key in (u'robes', u'rings')
        self.type_flags = self.clothes_flags[type_key]

    def wants_record(self, record):
        rec_type_flags = int(record.flags) & 0xFFFF
        my_type_flags = self.type_flags
        return ((rec_type_flags == my_type_flags) or (self.or_type_flags and (
                rec_type_flags & my_type_flags == rec_type_flags)))

class ClothesTweak(AClothesTweak, MultiTweakItem):
    def wants_record(self, record):
        return super(ClothesTweak, self).wants_record(
            record) and not record.flags.notPlayable

class CBash_ClothesTweak(AClothesTweak, CBash_MultiTweakItem):
    def wants_record(self, record):
        return super(CBash_ClothesTweak, self).wants_record(
            record) and record.IsPlayable

#------------------------------------------------------------------------------
class _AMaxWeightTweak(AClothesTweak):
    """Shared code of PBash/CBash max weight tweaks."""
    def __init__(self, tweak_name, tweak_tip, key, *choices):
        super(_AMaxWeightTweak, self).__init__(tweak_name, tweak_tip, key,
                                               *choices)
        self.logMsg = u'* ' + _(u'Clothes Reweighed: %d')

    @property
    def chosen_weight(self): return self.choiceValues[self.chosen][0]

    def wants_record(self, record):
        # Guess (i.e. super_weight) is intentionally overweight
        max_weight = self.chosen_weight
        super_weight = max(10, 5 * max_weight)
        return super(_AMaxWeightTweak, self).wants_record(
            record) and max_weight < record.weight < super_weight

    def _patchLog(self, log, count):
        self.logHeader = (u'=== '+ self.tweak_name +
                          u' [%4.2f]' % self.chosen_weight)
        super(_AMaxWeightTweak, self)._patchLog(log, count)

class ClothesTweak_MaxWeight(_AMaxWeightTweak, ClothesTweak):
    """Enforce a max weight for specified clothes."""
    def buildPatch(self, log, progress, patchFile):
        """Build patch."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.CLOT.records:
            if self.wants_record(record):
                record.weight = self.chosen_weight
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log, count)

class CBash_ClothesTweak_MaxWeight(_AMaxWeightTweak, CBash_ClothesTweak):
    """Enforce a max weight for specified clothes."""
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.weight = self.chosen_weight
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _AUnblockTweak(AClothesTweak):
    def __init__(self, tweak_name, tweak_tip, key, *choices):
        super(_AUnblockTweak, self).__init__(tweak_name, tweak_tip, key,
                                             *choices)
        self.logMsg = u'* ' + _(u'Clothes Tweaked: %d')
        self.unblock_flags = self.clothes_flags[key[key.rfind(u'.') + 1:]]

    def wants_record(self, record):
        return super(_AUnblockTweak, self).wants_record(
            record) and int(record.flags & self.unblock_flags)

class ClothesTweak_Unblock(_AUnblockTweak, ClothesTweak):
    """Unlimited rings, amulets."""
    def buildPatch(self, log, progress, patchFile):
        """Build patch."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.CLOT.records:
            if self.wants_record(record):
                record.flags &= ~self.unblock_flags
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log, count)

class CBash_ClothesTweak_Unblock(_AUnblockTweak, CBash_ClothesTweak):
    """Unlimited rings, amulets."""
    scanOrder = 31 ##: this causes silly changes to e.g. JailPants, investigate
    editOrder = 31

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.flags &= ~self.unblock_flags
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _AClothesTweaker(AMultiTweaker):
    """Patches clothes in miscellaneous ways."""
    _read_write_records = (b'CLOT',)
    _unblock = ((_(u'Unlimited Amulets'),
                 _(u"Wear unlimited number of amulets - but they won't"
                   u'display.'),
                 u'amulets.unblock.amulets',),
                (_(u'Unlimited Rings'),
                 _(u"Wear unlimited number of rings - but they won't"
                   u'display.'),
                 u'rings.unblock.rings'),
                (_(u'Gloves Show Rings'),
                 _(u'Gloves will always show rings. (Conflicts with Unlimited '
                   u'Rings.)'),
                 u'gloves.unblock.rings2'),
                (_(u'Robes Show Pants'),
                _(u"Robes will allow pants, greaves, skirts - but they'll"
                  u'clip.'),
                u'robes.unblock.pants'),
                (_(u'Robes Show Amulets'),
                _(u'Robes will always show amulets. (Conflicts with Unlimited '
                  u'Amulets.)'),
                u'robes.show.amulets2'),)
    _max_weight = ((_(u'Max Weight Amulets'),
                    _(u'Amulet weight will be capped.'),
                    u'amulets.maxWeight',
                    (u'0.0', 0.0),
                    (u'0.1', 0.1),
                    (u'0.2', 0.2),
                    (u'0.5', 0.5),
                    (_(u'Custom'), 0.0),),
                   (_(u'Max Weight Rings'), _(u'Ring weight will be capped.'),
                    u'rings.maxWeight',
                    (u'0.0', 0.0),
                    (u'0.1', 0.1),
                    (u'0.2', 0.2),
                    (u'0.5', 0.5),
                    (_(u'Custom'), 0.0),),
                   (_(u'Max Weight Hoods'), _(u'Hood weight will be capped.'),
                    u'hoods.maxWeight',
                    (u'0.2', 0.2),
                    (u'0.5', 0.5),
                    (u'1.0', 1.0),
                    (_(u'Custom'), 0.0),),)
    scanOrder = 31
    editOrder = 31

class ClothesTweaker(_AClothesTweaker,MultiTweaker):
    @classmethod
    def tweak_instances(cls):
        return sorted(itertools.chain(
            (ClothesTweak_Unblock(*x) for x in cls._unblock),
            (ClothesTweak_MaxWeight(*x) for x in cls._max_weight)),
                      key=lambda a: a.tweak_name.lower())

class CBash_ClothesTweaker(_AClothesTweaker,CBash_MultiTweaker):
    @classmethod
    def tweak_instances(cls):
        return sorted(itertools.chain(
            (CBash_ClothesTweak_Unblock(*x) for x in cls._unblock),
            (CBash_ClothesTweak_MaxWeight(*x) for x in cls._max_weight)),
                      key=lambda a: a.tweak_name.lower())
