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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This module contains oblivion multitweak item patcher classes that belong
to the Clothes Multitweaker - as well as the tweaker itself."""
from .base import CustomChoiceTweak, MultiTweaker, MultiTweakItem

# Patchers: 30 ----------------------------------------------------------------
class _AClothesTweak(MultiTweakItem):
    tweak_read_classes = b'CLOT',
    clothes_flags: dict[str, int] = {
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

    def __init__(self):
        super(_AClothesTweak, self).__init__()
        type_key = self.tweak_key[:self.tweak_key.find(u'.')]
        self.or_type_flags = type_key == u'rings'
        self.type_flags = self.clothes_flags[type_key]

    def wants_record(self, record):
        if record.is_not_playable():
            return False
        rec_type_flags = int(record.biped_flags) & 0xFFFF
        my_type_flags = self.type_flags
        return ((rec_type_flags == my_type_flags) or (self.or_type_flags and (
                rec_type_flags & my_type_flags == rec_type_flags)))

#------------------------------------------------------------------------------
class _AClothesTweak_MaxWeight(_AClothesTweak, CustomChoiceTweak):
    """Shared code of max weight tweaks."""
    tweak_log_msg = _(u'Clothes Reweighed: %(total_changed)d')

    @property
    def chosen_weight(self): return self.choiceValues[self.chosen][0]

    def wants_record(self, record):
        # Guess (i.e. super_weight) is intentionally overweight
        max_weight = self.chosen_weight
        super_weight = max(10, 5 * max_weight)
        return super(_AClothesTweak_MaxWeight, self).wants_record(
            record) and max_weight < record.weight < super_weight

    def tweak_record(self, record):
        record.weight = self.chosen_weight

    def _tweak_make_log_header(self, log):
        log.setHeader(f'=== {self.tweak_name} [{self.chosen_weight:4.2f}]')

#------------------------------------------------------------------------------
class ClothesTweak_MaxWeightAmulets(_AClothesTweak_MaxWeight):
    tweak_name = _(u'Max Weight Amulets')
    tweak_tip = _(u'Amulet weight will be capped.')
    tweak_key = u'amulets.maxWeight'
    tweak_choices = [(u'0.0', 0.0), (u'0.1', 0.1), (u'0.2', 0.2),
                     (u'0.5', 0.5)]

#------------------------------------------------------------------------------
class ClothesTweak_MaxWeightRings(_AClothesTweak_MaxWeight):
    tweak_name = _(u'Max Weight Rings')
    tweak_tip = _(u'Ring weight will be capped.')
    tweak_key = u'rings.maxWeight'
    tweak_choices = [(u'0.0', 0.0), (u'0.1', 0.1), (u'0.2', 0.2),
                     (u'0.5', 0.5)]

#------------------------------------------------------------------------------
class ClothesTweak_MaxWeightHoods(_AClothesTweak_MaxWeight):
    tweak_name = _(u'Max Weight Hoods')
    tweak_tip = _(u'Hood weight will be capped.')
    tweak_key = u'hoods.maxWeight'
    tweak_choices = [(u'0.2', 0.2), (u'0.5', 0.5), (u'1.0', 1.0)]

#------------------------------------------------------------------------------
class _AClothesTweak_Unblock(_AClothesTweak):
    """Unlimited rings, amulets."""
    tweak_log_msg = _(u'Clothes Tweaked: %(total_changed)d')
    _unblock_flags: int

    @property
    def unblock_flags(self):
        try:
            return self._unblock_flags
        except AttributeError:
            self._unblock_flags = self.clothes_flags[
                self.tweak_key[self.tweak_key.rfind(u'.') + 1:]]
        return self._unblock_flags

    def wants_record(self, record):
        return super(_AClothesTweak_Unblock, self).wants_record(
            record) and int(record.biped_flags & self.unblock_flags)

    def tweak_record(self, record):
        record.biped_flags &= ~self.unblock_flags

#------------------------------------------------------------------------------
class ClothesTweak_UnlimitedAmulets(_AClothesTweak_Unblock):
    tweak_name = _(u'Unlimited Amulets')
    tweak_tip = _(u"Wear unlimited number of amulets - but they won't "
                  u'display. Will affect all clothes flagged as amulets.')
    tweak_key = u'amulets.unblock.amulets'

#------------------------------------------------------------------------------
class ClothesTweak_UnlimitedRings(_AClothesTweak_Unblock):
    tweak_name = _(u'Unlimited Rings')
    tweak_tip = _(u"Wear unlimited number of rings - but they won't "
                  u'display. Will affect all clothes flagged as rings.')
    tweak_key = u'rings.unblock.rings'

#------------------------------------------------------------------------------
class ClothesTweak_GlovesShowRings(_AClothesTweak_Unblock):
    tweak_name = _(u'Gloves Show Rings')
    tweak_tip = _(u'Gloves will always show rings (conflicts with Unlimited '
                  u'Rings).')
    tweak_key = u'gloves.unblock.rings2'

#------------------------------------------------------------------------------
class ClothesTweak_RobesShowPants(_AClothesTweak_Unblock):
    tweak_name = _(u'Robes Show Pants')
    tweak_tip = _(u"Robes will allow pants, greaves, skirts - but they'll "
                  u'clip.')
    tweak_key = u'robes.unblock.pants'

#------------------------------------------------------------------------------
class ClothesTweak_RobesShowAmulets(_AClothesTweak_Unblock):
    tweak_name = _(u'Robes Show Amulets')
    tweak_tip = _(u'Robes will always show amulets (conflicts with Unlimited '
                  u'Amulets).')
    tweak_key = u'robes.show.amulets2'

#------------------------------------------------------------------------------
class TweakClothesPatcher(MultiTweaker):
    """Patches clothes in miscellaneous ways."""
    _tweak_classes = {
        ClothesTweak_MaxWeightAmulets, ClothesTweak_MaxWeightRings,
        ClothesTweak_MaxWeightHoods, ClothesTweak_UnlimitedAmulets,
        ClothesTweak_UnlimitedRings, ClothesTweak_GlovesShowRings,
        ClothesTweak_RobesShowPants, ClothesTweak_RobesShowAmulets,
    }
