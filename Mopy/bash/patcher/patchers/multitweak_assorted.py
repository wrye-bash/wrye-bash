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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This module contains oblivion multitweak item patcher classes that belong
to the Assorted Multitweaker - as well as the tweaker itself."""

from __future__ import annotations

import re

from .base import CustomChoiceTweak, IndexingTweak, MultiTweaker, \
    MultiTweakItem
from ... import bolt, bush

#------------------------------------------------------------------------------
class _AShowsTweak(MultiTweakItem):
    """Shared code of 'show clothing/armor' tweaks."""
    _hides_bit = None # override in implementations

    def wants_record(self, record):
        return (record.biped_flags[self._hides_bit] and
                not record.is_not_playable())

    def tweak_record(self, record):
        record.biped_flags[self._hides_bit] = False

#------------------------------------------------------------------------------
class _AArmoShowsTweak(_AShowsTweak):
    """Fix armor to show amulets/rings."""
    tweak_read_classes = b'ARMO',
    tweak_log_msg = _(u'Armor Pieces Tweaked: %(total_changed)d')

class AssortedTweak_ArmorShows_Amulets(_AArmoShowsTweak):
    tweak_name = _(u'Armor Shows Amulets')
    tweak_tip = _(u'Prevents armor from hiding amulets.')
    tweak_key = u'armorShowsAmulets'
    _hides_bit = 17

class AssortedTweak_ArmorShows_Rings(_AArmoShowsTweak):
    tweak_name = _(u'Armor Shows Rings')
    tweak_tip = _(u'Prevents armor from hiding rings.')
    tweak_key = u'armorShowsRings'
    _hides_bit = 16

#------------------------------------------------------------------------------
class _AClotShowsTweak(_AShowsTweak):
    """Fix robes, gloves and the like to show amulets/rings."""
    tweak_read_classes = b'CLOT',
    tweak_log_msg = _(u'Clothes Tweaked: %(total_changed)d')

class AssortedTweak_ClothingShows_Amulets(_AClotShowsTweak):
    tweak_name = _(u'Clothing Shows Amulets')
    tweak_tip = _(u'Prevents Clothing from hiding amulets.')
    tweak_key = u'ClothingShowsAmulets'
    _hides_bit = 17

class AssortedTweak_ClothingShows_Rings(_AClotShowsTweak):
    tweak_name = _(u'Clothing Shows Rings')
    tweak_tip = _(u'Prevents Clothing from hiding rings.')
    tweak_key = u'ClothingShowsRings'
    _hides_bit = 16

#------------------------------------------------------------------------------
class AssortedTweak_BowReach(MultiTweakItem):
    """Fix bows to have reach = 1.0."""
    tweak_read_classes = b'WEAP',
    tweak_name = _(u'Bow Reach Fix')
    tweak_tip = _(u'Fix bows with zero reach (zero reach causes CTDs).')
    tweak_key = u'BowReach'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'Bows Fixed: %(total_changed)d')
    default_enabled = True

    def wants_record(self, record):
        return record.weaponType == 5 and record.reach <= 0

    def tweak_record(self, record):
        record.reach = 1.0

#------------------------------------------------------------------------------
class AssortedTweak_SkyrimStyleWeapons(MultiTweakItem):
    """Sets all one handed weapons as blades, two handed weapons as blunt."""
    tweak_read_classes = b'WEAP',
    tweak_name = _(u'Skyrim-style Weapons')
    tweak_tip = _(u'Sets all one handed weapons as blades, two handed weapons '
                  u'as blunt.')
    tweak_key = u'skyrimweaponsstyle'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'Weapons Adjusted: %(total_changed)d')

    def wants_record(self, record):
        return record.weaponType in (1, 2)

    def tweak_record(self, record):
        record.weaponType = (3 if record.weaponType == 1 else 0)

#------------------------------------------------------------------------------
class AssortedTweak_ConsistentRings(MultiTweakItem):
    """Sets rings to all work on same finger."""
    tweak_read_classes = b'CLOT',
    tweak_name = _(u'Right Hand Rings')
    tweak_tip = _(u'Fixes rings to unequip consistently by making them '
                  u'prefer the right hand.')
    tweak_key = u'ConsistentRings'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'Rings Fixed: %(total_changed)d')
    default_enabled = True

    def wants_record(self, record):
        return record.biped_flags.leftRing

    def tweak_record(self, record):
        record.biped_flags.leftRing = False
        record.biped_flags.rightRing = True

#------------------------------------------------------------------------------
_in_checks = (u'briarheart', u'child', u'corpse', u'dummy',
              u'ghostly immobility', u'no wings', u'skin', u'test', u'token',
              u'tsaesci tail', u'werewolf', u'widget', u'willful')
_starts_checks = (u'fx', u'zz')
# Checks that can't be expressed via simple in/startswith checks
_remaining_checks = re.compile(u'see.*me|mark(?!ynaz)')

class _APlayableTweak(MultiTweakItem):
    """Shared code of 'armor/clothing playable' tweaks."""
    tweak_order = 9 # Run before 'armor/clothing shows' tweaks

    @staticmethod
    def _any_body_flag_set(record):
        return record.biped_flags.any_body_flag_set

    @staticmethod
    def _playable_skip(test_str):
        """Small helper method for wants_record, checks if the specified string
        (either from a FULL or EDID subrecord) indicates that the record it
        comes from should remain nonplayable."""
        return (any(i in test_str for i in _in_checks) or
                test_str.startswith(_starts_checks) or
                _remaining_checks.search(test_str))

    def wants_record(self, record):
        # 'script_fid' does not exist for later games, so use getattr
        if (not record.is_not_playable() or not self._any_body_flag_set(record)
                or getattr(record, u'script_fid', None)): return False
        # Later games mostly have these 'non-playable indicators' in the EDID
        clothing_eid = record.eid
        if clothing_eid and self._playable_skip(clothing_eid.lower()):
            return False
        clothing_name = record.full
        return clothing_name and not self._playable_skip(clothing_name.lower())

    def tweak_record(self, record):
        record.set_playable()

#------------------------------------------------------------------------------
class AssortedTweak_ClothingPlayable(_APlayableTweak):
    """Sets all clothes to playable."""
    tweak_read_classes = b'CLOT',
    tweak_name = _(u'All Clothing Playable')
    tweak_tip = _(u'Sets all clothing to be playable.')
    tweak_key = u'PlayableClothing'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_header = _(u'Playable Clothes')
    tweak_log_msg = _(u'Clothes Set As Playable: %(total_changed)d')

#------------------------------------------------------------------------------
class AssortedTweak_ArmorPlayable(_APlayableTweak):
    """Sets all armors to be playable."""
    tweak_read_classes = b'ARMO',
    tweak_name = _(u'All Armor Playable')
    tweak_tip = _(u'Sets all armor to be playable.')
    tweak_key = u'PlayableArmor'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_header = _(u'Playable Armor')
    tweak_log_msg = _(u'Armor Pieces Set As Playable: %(total_changed)d')

#------------------------------------------------------------------------------
class AssortedTweak_DarnBooks(MultiTweakItem):
    """DarNifies books."""
    tweak_read_classes = b'BOOK',
    tweak_name = _(u'DarNified Books')
    tweak_tip = _(u'Books will be reformatted for DarN UI.')
    tweak_key = u'DarnBooks'
    tweak_choices = [(u'default', u'default')]
    tweak_log_msg = _(u'Books DarNified: %(total_changed)d')
    _align_text = {u'^^': u'center', u'<<': u'left', u'>>': u'right'}
    _re_align = re.compile(r'^(<<|\^\^|>>)', re.M)
    _re_bold = re.compile(r'(__|\*\*|~~)')
    _re_color = re.compile('<font color="?([a-fA-F0-9]+)"?>', re.I | re.M)
    _re_div = re.compile('<div', re.I | re.M)
    _re_head_2 = re.compile(r'^(<<|\^\^|>>|)==\s*(\w[^=]+?)==\s*\r\n', re.M)
    _re_head_3 = re.compile(r'^(<<|\^\^|>>|)===\s*(\w[^=]+?)\r\n', re.M)
    _re_font = re.compile('<font', re.I | re.M)
    _re_font_1 = re.compile('(<?<font face=1( ?color=[0-9a-zA]+)?>)+',
                            re.I | re.M)
    _re_tag_in_word = re.compile('([a-z])<font face=1>', re.M)

    def wants_record(self, record):
        return (record.book_text and not record.enchantment and
                record.book_text != self._darnify(record))

    def tweak_record(self, record):
        record.book_text = self._darnify(record)

    def _darnify(self, record):
        """Darnifies the text of the specified record and returns it as a
        string."""
        self.inBold = False
        rec_text = record.book_text
        if self._re_head_2.match(rec_text):
            rec_text = self._re_head_2.sub(
                r'\1<font face=1 color=220000>\2<font face=3 '
                r'color=444444>\r\n', rec_text)
            rec_text = self._re_head_3.sub(
                r'\1<font face=3 color=220000>\2<font face=3 '
                r'color=444444>\r\n', rec_text)
            rec_text = self._re_align.sub(self._replace_align, rec_text)
            rec_text = self._re_bold.sub(self._replace_bold, rec_text)
            rec_text = re.sub(r'\r\n', r'<br>\r\n', rec_text)
        else:
            ma_color = self._re_color.search(rec_text)
            if ma_color:
                color = ma_color.group(1)
            elif record.flags.isScroll:
                color = '000000'
            else:
                color = '444444'
            font_face = f'<font face=3 color={color}>'
            rec_text = self._re_tag_in_word.sub(r'\1', rec_text)
            if (self._re_div.search(rec_text) and
                    not self._re_font.search(rec_text)):
                rec_text = font_face + rec_text
            else:
                rec_text = self._re_font_1.sub(font_face, rec_text)
        return rec_text

    # Helper methods for _darnify
    def _replace_bold(self, _mo):
        self.inBold = not self.inBold
        return f"<font face=3 color={'440000' if self.inBold else '444444'}>"

    def _replace_align(self, mo):
        return f'<div align={self._align_text[mo.group(1)]}>'

#------------------------------------------------------------------------------
class AssortedTweak_FogFix(MultiTweakItem):
    """Fix fog in cell to be non-zero."""
    tweak_name = _(u'Nvidia Fog Fix')
    tweak_tip = _(u'Fix fog related Nvidia black screen problems.')
    tweak_key = u'FogFix'
    tweak_choices = [(u'0.0001', u'0.0001')]
    tweak_log_msg = _(u'Cells With Fog Tweaked To 0.0001: %(total_changed)d')
    # Probably not needed on newer games, so default-enable only on TES4
    default_enabled = bush.game.fsName == u'Oblivion'
    tweak_read_classes = b'CELL',

    def wants_record(self, record):
        # All of these floats must be approximately equal to 0
        for fog_attr in (u'fogNear', u'fogFar', u'fogClip'):
            fog_val = getattr(record, fog_attr)
            if fog_val is not None and fog_val != 0.0: # type: bolt.Rounder
                return False
        return not record.should_skip()

    def tweak_record(self, record):
        record.fogNear = 0.0001

#------------------------------------------------------------------------------
class AssortedTweak_NoLightFlicker(MultiTweakItem):
    """Remove light flickering for low end machines."""
    tweak_read_classes = b'LIGH',
    tweak_name = _(u'No Light Flicker')
    tweak_tip = _(u'Remove flickering from lights. For use on low-end '
                  u'machines.')
    tweak_key = u'NoLightFlicker'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'Lights Unflickered: %(total_changed)d')
    _interested_flags = ('light_flickers', 'light_flickers_slow',
                         'light_pulses', 'light_pulses_slow')

    def wants_record(self, record):
        return any(getattr(record.light_flags, f_attr)
                   for f_attr in self._interested_flags)

    def tweak_record(self, record):
        for f_attr in self._interested_flags:
            setattr(record.light_flags, f_attr, False)

class AssortedTweak_NoLightFlicker_Fo4(AssortedTweak_NoLightFlicker):
    _interested_flags = ('light_flickers', 'light_pulses')

#------------------------------------------------------------------------------
class _AWeightTweak(CustomChoiceTweak):
    """Base class for weight tweaks."""
    _log_weight_value: str

    @property
    def chosen_weight(self): return self.choiceValues[self.chosen][0]

    def _tweak_make_log_header(self, log):
        super()._tweak_make_log_header(log)
        log(self._log_weight_value % {'weight_value': self.chosen_weight})

    def wants_record(self, record):
        return (record.weight or 0.0) > self.chosen_weight

    def tweak_record(self, record):
        record.weight = self.chosen_weight

class _AWeightTweak_SEFF(_AWeightTweak):
    """Base class for weight tweaks that need to ignore SEFF effects."""
    _seff_code = (b'SEFF', 0)
    _ignore_effects = bush.game.fsName != u'Oblivion'

    def wants_record(self, record):
        if not super().wants_record(record):
            return False
        return (self._ignore_effects or
                ##: Skip OBME records, at least for now
                (record.obme_record_version is None and
                 self._seff_code not in record.getEffects()))

#------------------------------------------------------------------------------
class AssortedTweak_PotionWeight(_AWeightTweak_SEFF):
    """Reweighs standard potions down to 0.1."""
    tweak_read_classes = b'ALCH',
    tweak_name = _(u'Reweigh: Potions (Maximum)')
    tweak_tip = _(u'Potion weight will be capped.')
    tweak_key = u'MaximumPotionWeight'
    tweak_choices = [(u'0.1', 0.1), (u'0.2', 0.2), (u'0.4', 0.4),
                     (u'0.6', 0.6)]
    tweak_log_msg = _(u'Potions Reweighed: %(total_changed)d')
    _log_weight_value = _('Potions set to maximum weight of %(weight_value)f.')

    def validate_values(self, chosen_values: tuple) -> str | None:
        if chosen_values[0] >= 1.0:
            return _("Maximum potion weight cannot exceed 1.0. Potions with "
                     "higher weight are ignored by this tweak (since they "
                     "are usually special 'potion in name only' items).")
        return super().validate_values(chosen_values)

    def wants_record(self, record):
        return (record.weight or 0.0) < 1.0 and super().wants_record(record)

#------------------------------------------------------------------------------
class AssortedTweak_IngredientWeight(_AWeightTweak_SEFF):
    """Reweighs standard ingredients down to 0.1."""
    tweak_read_classes = b'INGR',
    tweak_name = _(u'Reweigh: Ingredients')
    tweak_tip = _(u'Ingredient weight will be capped.')
    tweak_key = u'MaximumIngredientWeight'
    tweak_choices = [(u'0.1', 0.1), (u'0.2', 0.2), (u'0.4', 0.4),
                     (u'0.6', 0.6)]
    tweak_log_msg = _(u'Ingredients Reweighed: %(total_changed)d')
    _log_weight_value = _('Ingredients set to maximum weight of '
                          '%(weight_value)f.')

#------------------------------------------------------------------------------
class AssortedTweak_PotionWeightMinimum(_AWeightTweak):
    """Reweighs any potions up to 4."""
    tweak_read_classes = b'ALCH',
    tweak_name = _(u'Reweigh: Ingestibles (Minimum)')
    tweak_tip = _(u'The weight of ingestibles like potions and drinks will be '
                  u'floored.')
    tweak_key = u'MinimumPotionWeight'
    tweak_choices = [(u'0.1', 0.1), (u'0.5', 0.5), (u'1.0', 1.0),
                     (u'2.0', 2.0), (u'4.0', 4.0)]
    tweak_log_msg = _(u'Ingestibles Reweighed: %(total_changed)d')
    tweak_order = 11 # Run after Reweigh: Potions (Maximum) for consistency
    _log_weight_value = _('Ingestibles set to minimum weight of '
                          '%(weight_value)f.')

    ##: no SEFF condition - intended?
    # Probably no SEFF condition because that one delegates to its own super()
    # and that checks weight *greater than* chosen_weight - refactor that
    def wants_record(self, record):
        return (record.weight or 0.0) < self.chosen_weight

#------------------------------------------------------------------------------
class _AStaffTweak(MultiTweakItem):
    """Base class for tweaks that target staves."""
    tweak_read_classes = b'WEAP',
    tweak_log_msg = _('Staves Changed: %(total_changed)d')

    def wants_record(self, record):
        staff_attr, staff_val = bush.game.staff_condition
        return super().wants_record(record) and getattr(
            record, staff_attr) == staff_val

class AssortedTweak_StaffWeight(_AStaffTweak, _AWeightTweak):
    """Reweighs staves."""
    tweak_name = _(u'Reweigh: Staves')
    tweak_tip =  _(u'Staff weight will be capped.')
    tweak_key = u'StaffWeight'
    tweak_choices = [(u'1.0', 1.0), (u'2.0', 2.0), (u'3.0', 3.0),
                     (u'4.0', 4.0), (u'5.0', 5.0), (u'6.0', 6.0),
                     (u'7.0', 7.0), (u'8.0', 8.0)]
    tweak_log_msg = _(u'Staves Reweighed: %(total_changed)d')
    _log_weight_value = _('Staves set to maximum weight of %(weight_value)f.')

#------------------------------------------------------------------------------
class AssortedTweak_ArrowWeight(_AWeightTweak):
    tweak_read_classes = b'AMMO',
    tweak_name = _(u'Reweigh: Ammunition')
    tweak_tip = _(u'The weight of ammunition (e.g. arrows, bullets, etc.) '
                  u'will be capped.')
    tweak_key = u'MaximumArrowWeight'
    tweak_choices = [(u'0.0', 0.0), (u'0.1', 0.1), (u'0.2', 0.2),
                     (u'0.4', 0.4), (u'0.6', 0.6)]
    tweak_log_msg = _(u'Ammunition Reweighed: %(total_changed)d')
    _log_weight_value = _('Ammunition set to maximum weight of '
                          '%(weight_value)f.')

#------------------------------------------------------------------------------
class AssortedTweak_BookWeight(_AWeightTweak):
    tweak_read_classes = b'BOOK',
    tweak_name = _(u'Reweigh: Books')
    tweak_tip = _(u'The weight of books will be capped.')
    tweak_key = u'reweigh_books'
    tweak_choices = [(u'0.0', 0.0), (u'0.3', 0.3), (u'0.5', 0.5),
                     (u'0.75', 0.75), (u'1.0', 1.0)]
    tweak_log_msg = _(u'Books Reweighed: %(total_changed)d')
    _log_weight_value = _('Books set to maximum weight of %(weight_value)f.')

#------------------------------------------------------------------------------
class _AASTweakMin(MultiTweakItem):
    """Base class for tweaks that alter minimum attack speeds."""
    _log_attack_speed_value: str

    @property
    def chosen_attack_speed(self): return self.choiceValues[self.chosen][0]

    def _tweak_make_log_header(self, log):
        super()._tweak_make_log_header(log)
        log(self._log_attack_speed_value % {
            'attack_speed_value': self.chosen_attack_speed})

    def wants_record(self, record):
        return record.speed < self.chosen_attack_speed

    def tweak_record(self, record):
        record.speed = self.chosen_attack_speed

class AssortedTweak_AttackSpeedStavesMinimum(_AStaffTweak, _AASTweakMin):
    """Sets a floor for staff attack speeds."""
    tweak_name = _('Attack Speed: Staves (Minimum)')
    tweak_tip = _('Ensures every staff has at least the chosen attack speed.')
    tweak_key = 'attack_speed_staves_min'
    tweak_choices = [('0.1', 0.1), ('0.5', 0.5), ('1.0', 1.0), ('2.0', 2.0)]
    default_choice = '1.0'
    _log_attack_speed_value = _('Staff attack speed set to minimum of '
                                '%(attack_speed_value)f.')

#------------------------------------------------------------------------------
class _AASTweakMax(_AASTweakMin):
    """Base class for tweaks that alter maximum attack speeds."""
    def wants_record(self, record):
        return record.speed > self.chosen_attack_speed

class AssortedTweak_AttackSpeedStavesMaximum(_AStaffTweak, _AASTweakMax):
    """Sets a ceiling for staff attack speeds."""
    tweak_name = _('Attack Speed: Staves (Maximum)')
    tweak_tip = _('Ensures every staff has at most the chosen attack speed.')
    tweak_key = 'attack_speed_staves_max'
    tweak_choices = [('0.1', 0.1), ('0.5', 0.5), ('1.0', 1.0), ('2.0', 2.0)]
    default_choice = '1.0'
    _log_attack_speed_value = _('Staff attack speed set to maximum of '
                                '%(attack_speed_value)f.')

#------------------------------------------------------------------------------
class AssortedTweak_ScriptEffectSilencer(MultiTweakItem):
    """Silences the script magic effect and gives it an extremely high
    speed."""
    tweak_read_classes = b'MGEF',
    tweak_name = _(u'Magic: Script Effect Silencer')
    tweak_tip = _(u'Script Effect will be silenced and have no graphics.')
    tweak_key = u'SilentScriptEffect'
    tweak_choices = [(u'0', 0)]
    tweak_log_msg = _(u'Script Effect Silenced.')
    default_enabled = True
    _silent_attrs = dict.fromkeys(
        ['areaSound', 'boltSound', 'castingSound', 'effectShader',
         'enchantEffect', 'hitSound', 'light'], bush.game.master_fid(0))
    _silent_attrs['model'] = None
    _silent_attrs['projectileSpeed'] = 9999

    def wants_record(self, record):
        # u'' here is on purpose! We're checking the EDID, which gets decoded
        return record.eid == u'SEFF' and any(
            getattr(record, a) != v for a, v in self._silent_attrs.items())

    def tweak_record(self, record):
        for mgef_attr, mgef_val in self._silent_attrs.items():
            setattr(record, mgef_attr, mgef_val)
        record.flags.no_hit_effect = True

    def tweak_log(self, log, count):
        # count would be pointless, always one record
        super().tweak_log(log, {})

#------------------------------------------------------------------------------
class AssortedTweak_HarvestChance(CustomChoiceTweak):
    """Adjust Harvest Chances."""
    tweak_read_classes = b'FLOR',
    tweak_name = _(u'Harvest Chance')
    tweak_tip = _(u'Harvest chances on all plants will be set to the chosen '
                  u'percentage.')
    tweak_key = u'HarvestChance'
    tweak_choices = [(u'10%', 10), (u'20%', 20), (u'30%', 30), (u'40%', 40),
                     (u'50%', 50), (u'60%', 60), (u'70%', 70), (u'80%', 80),
                     (u'90%', 90), (u'100%', 100)]
    tweak_log_msg = _(u'Harvest Chances Changed: %(total_changed)d')
    _season_attrs = ('sip_spring', 'sip_summer', 'sip_fall', 'sip_winter')

    @property
    def chosen_chance(self):
        return self.choiceValues[self.chosen][0]

    def wants_record(self, record):
        return (u'nirnroot' not in record.eid.lower() # skip Nirnroots
                and any(getattr(record, a) != self.chosen_chance for a
                        in self._season_attrs))

    def tweak_record(self, record):
        for attr in self._season_attrs:
            setattr(record, attr, self.chosen_chance)

#------------------------------------------------------------------------------
class AssortedTweak_WindSpeed(MultiTweakItem):
    """Disables Weather winds."""
    tweak_read_classes = b'WTHR',
    tweak_name = _(u'Disable Wind')
    tweak_tip = _(u'Disables the wind on all weathers.')
    tweak_key = u'windSpeed'
    tweak_log_msg = _(u'Winds Disabled: %(total_changed)d')
    tweak_choices = [(u'Disable', 0)]

    def wants_record(self, record):
        return record.windSpeed != 0

    def tweak_record(self, record):
        record.windSpeed = 0

#------------------------------------------------------------------------------
class AssortedTweak_UniformGroundcover(MultiTweakItem):
    """Eliminates random variation in groundcover."""
    tweak_read_classes = b'GRAS',
    tweak_name = _(u'Uniform Groundcover')
    tweak_tip = _(u'Eliminates random variation in groundcover (grasses, '
                  u'shrubs, etc.).')
    tweak_key = u'UniformGroundcover'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'Grasses Normalized: %(total_changed)d')

    def wants_record(self, record):
        return record.height_range != 0.0 # type: bolt.Rounder

    def tweak_record(self, record):
        record.height_range = 0.0

#------------------------------------------------------------------------------
class AssortedTweak_SetCastWhenUsedEnchantmentCosts(CustomChoiceTweak):
    """Sets Cast When Used Enchantment number of uses."""
    tweak_read_classes = b'ENCH',
    tweak_name = _(u'Number Of Uses For Pre-enchanted Weapons And Staves')
    tweak_tip = _(u'The charge amount and cast cost will be edited so that '
                  u'all enchanted weapons and staves have the amount of uses '
                  u'specified. Cost will be rounded up to 1 (unless set to '
                  u'unlimited) so number of uses may not exactly match for '
                  u'all weapons.')
    tweak_key = u'Number of uses:'
    tweak_choices = [(u'1', 1), (u'5', 5), (u'10', 10), (u'20', 20),
                     (u'30', 30), (u'40', 40), (u'50', 50), (u'80', 80),
                     (u'100', 100), (u'250', 250), (u'500', 500),
                     (_(u'Unlimited'), 0)]
    tweak_log_header = _(u'Set Enchantment Number of Uses')
    tweak_log_msg = _(u'Enchantments Set: %(total_changed)d')

    def wants_record(self, record):
        if record.item_type not in (1, 2): return False
        new_cost, new_amount = self._calc_cost_and_amount(record)
        return (record.enchantment_cost != new_cost or
                record.charge_amount != new_amount)

    def tweak_record(self, record):
        new_cost, new_amount = self._calc_cost_and_amount(record)
        record.enchantment_cost = new_cost
        record.charge_amount = new_amount

    def _calc_cost_and_amount(self, record):
        """Calculates the new enchantment cost and charge amount for the
        specified record based on the number of uses the user chose."""
        chosen_uses = self.choiceValues[self.chosen][0]
        final_cost = (max(record.charge_amount // chosen_uses, 1)
                      if chosen_uses != 0 else 0)
        return final_cost, final_cost * chosen_uses

#------------------------------------------------------------------------------
##: This will have to become more powerful in the process if we want it to
# support FO3/FNV eventually ##: does it even make sense there?
class AssortedTweak_DefaultIcons(MultiTweakItem):
    """Sets a default icon for any records that don't have any icon
    assigned."""
    tweak_name = _(u'Default Icons')
    tweak_tip = _(u"Sets a default icon for any records that don't have any "
                  u'icon assigned.')
    tweak_key = u'icons'
    tweak_choices = [(u'1', 1)]
    tweak_read_classes = (b'ALCH', b'AMMO', b'APPA', b'BOOK', b'BSGN', b'CLAS',  # ToDo 'FACT', / per game
        b'INGR', b'KEYM', b'LIGH', b'MISC', b'QUST', b'SGST', b'SLGM', b'WEAP'
    )
    tweak_log_msg = _(u'Default Icons Set: %(total_changed)d')
    default_enabled = True

    def wants_record(self, record):
        return record.can_set_icon()

    def tweak_record(self, record):
        record.set_default_icon()

#------------------------------------------------------------------------------
class _AAttenuationTweak(CustomChoiceTweak):
    """Shared code of sound attenuation tweaks."""
    tweak_read_classes = bush.game.static_attenuation_rec_type,
    tweak_choices = [(u'0%', 0), (u'5%', 5), (u'10%', 10), (u'20%', 20),
                     (u'50%', 50), (u'80%', 80)]
    tweak_log_msg = _(u'Sounds Modified: %(total_changed)d')
    _nirnroot_words = {u'nirnroot', u'vynroot', u'vynwurz'}

    @classmethod
    def _is_nirnroot(cls, record):
        """Helper method for checking whether a record is a nirnroot."""
        return (reid := record.eid) and any(
            x in reid.lower() for x in cls._nirnroot_words)

    @property
    def chosen_atten(self): return self.choiceValues[self.chosen][0] / 100

    def wants_record(self, record):
        return (record.static_attenuation and
                self.chosen_atten != 1) # avoid ITPOs

    def tweak_record(self, record):
        # Must be an int on py3, otherwise errors on dump
        record.static_attenuation = int(
            record.static_attenuation * self.chosen_atten)

#------------------------------------------------------------------------------
class AssortedTweak_SetSoundAttenuationLevels(_AAttenuationTweak):
    """Sets Sound Attenuation Levels for all records except Nirnroots."""
    tweak_name = _('Set Sound Attenuation Levels')
    tweak_tip = _('Sets sound attenuation levels to tweak percentage times '
                  'current level. Does not affect %(nirnroots)s.') % {
        'nirnroots': bush.game.nirnroots}
    tweak_key = 'Attenuation%:'

    def wants_record(self, record):
        return super().wants_record(record) and not self._is_nirnroot(record)

#------------------------------------------------------------------------------
class AssortedTweak_SetSoundAttenuationLevels_NirnrootOnly(_AAttenuationTweak):
    """Sets Sound Attenuation Levels for Nirnroots."""
    tweak_name = _('Set Sound Attenuation Levels: %(nirnroots)s Only') % {
        'nirnroots': bush.game.nirnroots}
    tweak_tip = _('Sets sound attenuation levels to tweak percentage times '
                  'current level. Only affects %(nirnroots)s.') % {
        'nirnroots': bush.game.nirnroots}
    tweak_key = 'Nirnroot Attenuation%:'

    def wants_record(self, record):
        return super().wants_record(record) and self._is_nirnroot(record)

#------------------------------------------------------------------------------
class AssortedTweak_FactioncrimeGoldMultiplier(MultiTweakItem):
    """Fix factions with unset crime gold multiplier to have a
    crime gold multiplier of 1.0."""
    tweak_read_classes = b'FACT',
    tweak_name = _(u'Faction Crime Gold Multiplier Fix')
    tweak_tip = _(u'Fix factions with unset Crime Gold Multiplier to have a '
                  u'Crime Gold Multiplier of 1.0.')
    tweak_key = u'FactioncrimeGoldMultiplier'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'Factions Fixed: %(total_changed)d')

    def wants_record(self, record):
        return record.crime_gold_multiplier is None

    def tweak_record(self, record):
        record.crime_gold_multiplier = 1.0

#------------------------------------------------------------------------------
class AssortedTweak_LightFadeValueFix(MultiTweakItem):
    """Fix lights with missing fade value."""
    tweak_read_classes = b'LIGH',
    tweak_name = _(u'No Light Fade Value Fix')
    tweak_tip = _(u'Sets Light Fade values to default of 1.0 if not set.')
    tweak_key = u'NoLightFadeValueFix'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'Lights With Fade Values Added: %(total_changed)d')

    def wants_record(self, record):
        return record.light_fade is None

    def tweak_record(self, record):
        record.light_fade = 1.0

#------------------------------------------------------------------------------
class AssortedTweak_TextlessLSCRs(MultiTweakItem):
    """Removes the description from loading screens."""
    tweak_read_classes = b'LSCR',
    tweak_name = _(u'No Description Loading Screens')
    tweak_tip = _(u'Removes the description from loading screens.')
    tweak_key = u'NoDescLSCR'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'Loading Screens Tweaked: %(total_changed)d')

    def wants_record(self, record):
        return record.description

    def tweak_record(self, record):
        record.description = u''

#------------------------------------------------------------------------------
class AssortedTweak_SEFFIcon(CustomChoiceTweak):
    """Changes the icon for the SEFF (Script Effect) magic effect."""
    tweak_read_classes = b'MGEF',
    tweak_name = _(u'Magic: Script Effect Icon Changer')
    tweak_tip = _(u'Changes the Script Effect icon to one of several choices, '
                  u'or to a custom icon.')
    tweak_key = u'seff_icon_changer'
    tweak_choices = [(_(u'Unused Magic Icon'), u'magic\\magic_all_icon.dds'),
                     (_(u'Unused Darkness Icon'),
                      u'magic\\illusion_icons\\darkness_illusion.dds'),
                     (_(u'Default (Burden)'),
                      u'magic\\alteration_icons\\burden_alteration.dds')]
    tweak_log_msg = _(u'Script Effect icon changed.')

    @property
    def chosen_icon(self): return self.choiceValues[self.chosen][0].lower()

    def wants_record(self, record):
        # u'' here is on purpose! We're checking the EDID, which gets decoded
        return (record.eid == u'SEFF' and
                record.iconPath.lower() != self.chosen_icon)

    def tweak_record(self, record):
        record.iconPath = self.chosen_icon

#------------------------------------------------------------------------------
class AssortedTweak_GunsUseISAnimation(MultiTweakItem):
    """Set all guns to use ironsight animations."""
    tweak_read_classes = b'WEAP',
    tweak_name = _(u'All Guns Use Iron Sights Animation')
    tweak_tip = _(u'Makes all guns use the iron sights animation.')
    tweak_key = u'GunsUseIronSights'
    tweak_log_msg = _(u'Guns set to use iron sights: %(total_changed)d')
    tweak_choices = [(_(u'All Guns'), {1, 2}),
                     (_(u'Energy Weapons Only'), {1}),
                     (_(u'Conventional Weapons Only'), {2})]

    def wants_record(self, record):
        return (record.equipment_type in self.choiceValues[self.chosen][0] and
                not record.dnamFlags1.hasScope and
                record.dnamFlags1.dontUse1stPersonISAnimations)

    def tweak_record(self, record):
        record.dnamFlags1.dontUse1stPersonISAnimations = False

#------------------------------------------------------------------------------
class AssortedTweak_AllWaterDamages(MultiTweakItem):
    """Add the 'Causes Damage' flag to all WATR records."""
    tweak_read_classes = b'WATR',
    tweak_name = _(u'Mark All Water As Damaging')
    tweak_tip = _(u'Adds the "Causes Damage" flag to every type of water in '
                  u'the game. Used by some needs mods.')
    tweak_key = u'AllWaterDamages'
    tweak_log_msg = _(u'Waters marked as damaging: %(total_changed)d')

    def wants_record(self, record):
        return not record.flags.causesDamage

    def tweak_record(self, record):
        record.flags.causesDamage = True

#------------------------------------------------------------------------------
class AssortedTweak_AbsorbSummonFix(IndexingTweak):
    """Adds the 'No Absorb/Reflect' flag to summoning spells."""
    tweak_read_classes = b'SPEL',
    tweak_name = _(u'Magic: Summoning Absorption Fix')
    tweak_tip = _(u'Adds the "No Absorb/Reflect" flag to all summoning '
                  u'spells. Fixes those spells with spell absorption.')
    tweak_key = u'AbsorbSummonFix'
    tweak_log_msg = _(u'Spells fixed: %(total_changed)d')
    default_enabled = True
    _look_up_mgef = None
    _index_sigs = [b'MGEF']

    def prepare_for_tweaking(self, patch_file):
        super(AssortedTweak_AbsorbSummonFix, self).prepare_for_tweaking(
            patch_file)
        self._look_up_mgef = self._indexed_records[b'MGEF']

    def wants_record(self, record):
        if record.spell_flags.no_absorb_reflect: return False
        # If we don't have MGEF lookup available yet, just forward everything
        if not self._look_up_mgef: return True
        # Otherwise, we can look through the effects for the right archetype
        for spell_eff in record.effects:
            mgef_record = self._look_up_mgef.get(spell_eff.effect_formid)
            if mgef_record and mgef_record.effect_archetype == 18:
                return True # 18 == Summon Creature
        return False

    def tweak_record(self, record):
        record.spell_flags.no_absorb_reflect = True

#------------------------------------------------------------------------------
class TweakAssortedPatcher(MultiTweaker):
    """Tweaks assorted stuff. Sub-tweaks behave like patchers themselves."""
    # Run this before all other tweakers, since it contains the 'playable'
    # tweaks, which set the playable flag on various records. Tweaks from other
    # tweakers use this flag to determine which records to target, so they
    # *must* run afterwards or we'll miss some records.
    patcher_order = 29
    _tweak_classes = {globals()[t] for t in bush.game.assorted_tweaks}
