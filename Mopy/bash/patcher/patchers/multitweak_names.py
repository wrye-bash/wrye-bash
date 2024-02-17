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
to the Names Multitweaker - as well as the tweaker itself."""

from __future__ import annotations

import re
from collections import defaultdict

from .base import CustomChoiceTweak, IndexingTweak, MultiTweaker, \
    MultiTweakItem
from ... import bush
from ...bolt import RecPath, build_esub, setattr_deep
from ...exception import BPConfigError

_ignored_chars = frozenset(u'+-=.()[]<>')

##: The Armor/Clothes tweaks allow customizing the tags used. The others should
# too, but before we do that we need to replace NamesTweak_BodyPartCodes with
# something better (e.g. a special 'settings patcher' inside the BP)

class _ANamesTweak(CustomChoiceTweak):
    """Shared code of names tweaks."""
    _choice_formats = [] # The default formats for this tweak
    _example_item = _example_code = u'' # An example item name and its code
    _example_stat = 0 # The example item's stat
    _may_have_stats = False # Whether formats with '%02d' in them are OK
    _may_lack_specifiers = False # Whether formats without '%s' in them are OK
    _prepends_name = False # Whether the tweak prepends or appends the name

    def __init__(self, bashed_patch):
        # Generate choices based on the example item, code and stat
        dynamic_choices = []
        for choice_fmt in self._choice_formats:
            if choice_fmt == u'----':
                formatted_label = u'----'
            else:
                if self._may_have_stats and u'%02d' in choice_fmt:
                    formatted_label = choice_fmt % (self._example_code,
                                                    self._example_stat)
                elif self._may_lack_specifiers and u'%s' not in choice_fmt:
                    formatted_label = choice_fmt
                else:
                    formatted_label = choice_fmt % self._example_code
                if self._prepends_name:
                    formatted_label = self._example_item + formatted_label
                else:
                    formatted_label += self._example_item
            dynamic_choices.append((formatted_label, choice_fmt))
        self.tweak_choices = dynamic_choices
        super(_ANamesTweak, self).__init__(bashed_patch)

    @property
    def chosen_format(self): return self.choiceValues[self.chosen][0]

    def validate_values(self, chosen_values: tuple) -> str | None:
        wanted_fmt = chosen_values[0]
        if self._may_lack_specifiers:
            if self._may_have_stats:
                # May contain any combination of a single %s and a single %02d,
                # but no other specifiers
                fmt_params = ()
                if '%s' in wanted_fmt:
                    fmt_params = ('A', 1) if '%02d' in wanted_fmt else 'A'
                elif '%02d' in wanted_fmt:
                    fmt_params = 1
                if fmt_params:
                    try:
                        wanted_fmt % fmt_params
                    except TypeError:
                        # Do *not* change the %s/%02d, they're on purpose
                        return _("The format you entered is not valid for "
                                 "this tweak. It may contain exactly one '%s' "
                                 "and one '%02d' as well as any regular "
                                 "characters, but no other format specifiers. "
                                 "See the 'Tweak Names' section of the "
                                 "Advanced Readme for more information.")
            else:
                # May contain a single %s, but no other specifiers
                if '%s' in wanted_fmt:
                    try:
                        wanted_fmt % 'A'
                    except TypeError:
                        # Do *not* change the %s, it's on purpose
                        return _("The format you entered is not valid for "
                                 "this tweak. It may contain exactly one '%s' "
                                 "and any regular characters, but no other "
                                 "format specifiers. See the 'Tweak Names' "
                                 "section of the Advanced Readme for more "
                                 "information.")
        elif self._may_have_stats:
            # Must contain a single %s and may contain a %02d
            fmt_params = ('A', 1) if '%02d' in wanted_fmt else 'A'
            try:
                wanted_fmt % fmt_params
            except TypeError:
                # Do *not* change the %s/%02d, they're on purpose
                return _("The format you entered is not valid for this tweak. "
                         "It must contain exactly one '%s' and may contain "
                         "one '%02d' as well as any regular characters, but "
                         "no other format specifiers. See the 'Tweak Names' "
                         "section of the Advanced Readme for more "
                         "information.")
        else:
            # Must contain a single %s and no other specifiers
            try:
                wanted_fmt % 'A'
            except TypeError:
                # Do *not* change the %s, it's on purpose
                return _("The format you entered is not valid for this tweak. "
                         "It must contain exactly one '%s' and may contain "
                         "any regular characters, but no other format "
                         "specifiers. See the 'Tweak Names' section of the "
                         "Advanced Readme for more information.")
        return super().validate_values(chosen_values)

    def wants_record(self, record):
        old_full = record.full
        # Skip records that are probably already labeled or otherwise unusual
        # (i.e. start with a non-word character)
        return (old_full and old_full[0] not in _ignored_chars and
                old_full != self._exec_rename(record))

    def tweak_record(self, record):
        record.full = self._exec_rename(record)

    def _exec_rename(self, record):
        """Does the actual renaming, returning the new name as its result."""
        raise NotImplementedError

class _AMgefNamesTweak(_ANamesTweak):
    """Shared code of a few names tweaks that handle MGEFs.
    Oblivion-specific."""
    _tweak_mgef_hostiles = set()
    _look_up_mgef = None

    def prepare_for_tweaking(self, patch_file):
        self._tweak_mgef_hostiles = patch_file.getMgefHostiles()
        super(_ANamesTweak, self).prepare_for_tweaking(patch_file)

    def wants_record(self, record):
        # Once we have MGEFs indexed, we can try renaming to check more
        # thoroughly (i.e. during the buildPatch/apply phase)
        old_full = record.full
        return (old_full and (not self._tweak_mgef_hostiles or
                old_full != self._exec_rename(record)))

class _AEffectsTweak_Tes5(IndexingTweak, _ANamesTweak):
    """Skyrim implementation of _AEffectsTweak's API."""
    _index_sigs = [b'MGEF']
    _look_up_mgef = None

    def wants_record(self, record):
        # If we haven't indexed MGEFs yet, we have to forward all records
        return not self._look_up_mgef or super().wants_record(record)

    def prepare_for_tweaking(self, patch_file):
        super().prepare_for_tweaking(patch_file)
        self._look_up_mgef = self._indexed_records[b'MGEF']

#------------------------------------------------------------------------------
##: This would be better handled with some sort of settings menu for the BP
class NamesTweak_BodyPartCodes(CustomChoiceTweak): # loads no records
    """Sets the body part codes used by other names tweaks. See
    TweakNamesPatcher.__init__ and __ANamesTweak_Body._tweak_body_tags"""
    tweak_name = _(u'Body Part Codes')
    tweak_tip = _(u'Sets body part codes used by Armor/Clothes name tweaks.')
    tweak_key = u'bodyTags'
    tweak_log_msg = u'' # we log nothing
    tweak_choices = [(c, c) for c in bush.game.body_part_codes]
    tweak_order = 9 # Run before all other tweaks

    def __init__(self, bashed_patch):
        super(NamesTweak_BodyPartCodes, self).__init__(bashed_patch)
        len_first = len(self.tweak_choices[0][0])
        # Verify that the body_part_codes constant is valid
        for tc in self.tweak_choices[1:]:
            if len(tc[0]) != len_first:
                raise SyntaxError(u'Not all body part codes have the same '
                                  u'length for this game.')

    def tweak_log(self, log, count): pass # 'internal' tweak, log nothing

    def validate_values(self, chosen_values: tuple) -> str | None:
        cho_len = len(chosen_values[0])
        req_len = len(self.tweak_choices[0][0])
        if cho_len != req_len:
            return _("The value has length %(actual_len)d, but must have "
                     "length %(expected_len)d to match the number of body "
                     "part types for this game. See the 'Tweak Names' section "
                     "of the Advanced Readme for more information.") % {
                'actual_len': cho_len, 'expected_len': req_len}
        return super().validate_values(chosen_values)

#------------------------------------------------------------------------------
class _ANamesTweak_Body(_ANamesTweak):
    """Shared code of 'body names' tweaks."""
    _tweak_body_tags = u'' # Set in TweakNamesPatcher.__init__

    def wants_record(self, record):
        return not record.is_not_playable() and super().wants_record(record)

class _ANamesTweak_Body_Tes4(_ANamesTweak_Body):
    def _exec_rename(self, record):
        amulet_tag, ring_tag, gloves_tag, head_tag, tail_tag, robe_tag, \
        chest_tag, pants_tag, shoes_tag, shield_tag = self._tweak_body_tags
        body_flags = record.biped_flags
        if body_flags.head or body_flags.hair:
            equipment_tag = head_tag
        elif body_flags.rightRing or body_flags.leftRing:
            equipment_tag = ring_tag
        elif body_flags.amulet:
            equipment_tag = amulet_tag
        elif body_flags.upperBody and body_flags.lowerBody:
            equipment_tag = robe_tag
        elif body_flags.upperBody:
            equipment_tag = chest_tag
        elif body_flags.lowerBody:
            equipment_tag = pants_tag
        elif body_flags.hand:
            equipment_tag = gloves_tag
        elif body_flags.foot:
            equipment_tag = shoes_tag
        elif body_flags.tail:
            equipment_tag = tail_tag
        elif body_flags.shield:
            equipment_tag = shield_tag
        else:
            return record.full # Weird record, don't change anything
        armor_addition = (u'LH'[body_flags.heavy_armor]
                          if record._rec_sig == b'ARMO' else u'')
        prefix_subs = (equipment_tag + armor_addition,)
        prefix_format = self.chosen_format
        if self._may_have_stats and u'%02d' in prefix_format:
            # Armor rating is scaled up x100 in the records
            prefix_subs += (record.strength / 100,)
        return prefix_format % prefix_subs + record.full

#------------------------------------------------------------------------------
class _ANamesTweak_Body_Armor(_ANamesTweak_Body):
    tweak_read_classes = b'ARMO',
    tweak_name = _(u'Sort: Armor/Clothes')
    tweak_tip = _(u'Rename armor and clothes to sort by type.')
    tweak_key = u'ARMO' # u'' is intended, not a record sig, ugh...
    tweak_log_msg = _(u'Armor Pieces Renamed: %(total_changed)d')
    _choice_formats = [u'%s ', u'%s. ', u'%s - ', u'(%s) ', u'----',
                       u'%s%02d ', u'%s%02d. ', u'%s%02d - ', u'(%s%02d) ']
    _may_have_stats = True

class NamesTweak_Body_Armor_Tes4(_ANamesTweak_Body_Tes4,
                                 _ANamesTweak_Body_Armor):
    tweak_name = _(u'Sort: Armor')
    tweak_tip = _(u'Rename armor to sort by type and armor rating.')
    _example_item = _(u'Leather Boots')
    _example_code = u'BL'
    _example_stat = 2

class NamesTweak_Body_Armor_Fo3(_ANamesTweak_Body_Armor):
    _example_item = _(u'Sleepwear')
    _example_code = u'A'
    _example_stat = 1
    _is_fnv = bush.game.fsName == 'FalloutNV'

    def _exec_rename(self, record):
        head_tag, body_tag, gloves_tag, pipboy_tag, backpack_tag, fancy_tag, \
        accessory_tag = self._tweak_body_tags
        gen_flags = record.generalFlags
        if gen_flags.power_armor:
            armor_addition = 'P'
        elif gen_flags.heavy_armor:
            armor_addition = 'H'
        elif self._is_fnv and gen_flags.medium_armor: # flag added in FNV
            armor_addition = 'M'
        else: # Implicitly light armor
            armor_addition = 'L'
        body_flags = record.biped_flags
        if body_flags.upperBody:
            equipment_tag = body_tag
        elif (body_flags.head or body_flags.hair or body_flags.headband or
              body_flags.hat):
            equipment_tag = head_tag
        elif body_flags.leftHand or body_flags.rightHand:
            equipment_tag = gloves_tag
        elif (body_flags.necklace or body_flags.eyeGlasses or
              body_flags.noseRing or body_flags.earrings or body_flags.mask or
              body_flags.choker or body_flags.mouthObject):
            equipment_tag = fancy_tag
        elif body_flags.backpack:
            equipment_tag = backpack_tag
        elif (body_flags.bodyAddon1 or body_flags.bodyAddon2 or
              body_flags.bodyAddon3):
            equipment_tag = accessory_tag
        elif body_flags.pipboy:
            equipment_tag = pipboy_tag
        else:
            return record.full # Weird record, don't change anything
        prefix_subs = (equipment_tag + armor_addition,)
        prefix_format = self.chosen_format
        if self._may_have_stats and '%02d' in prefix_format:
            if self._is_fnv:
                # Use damage threshold instead of damage resistance for FNV.
                # Note that that one is *not* scaled up x100 in the records
                prefix_subs += (record.dt,)
            else:
                # Damage resistance is scaled up x100 in the records
                prefix_subs += (record.dr / 100,)
        return prefix_format % prefix_subs + record.full

class NamesTweak_Body_Armor_Tes5(_ANamesTweak_Body_Armor):
    _example_item = _('Iron Armor')
    _example_code = 'AH'
    _example_stat = 25

    def _exec_rename(self, record):
        armo_type = record.armor_type
        if armo_type == 0: # Light Armor
            armor_addition = 'L'
        elif armo_type == 1: # Heavy Armor
            armor_addition = 'H'
        elif armo_type == 2: # Clothing
            armor_addition = 'C'
        else:
            return record.full # Record is broken, don't change anything
        head_tag, body_tag, arms_tag, legs_tag, amulet_tag, ring_tag, \
        shield_tag = self._tweak_body_tags
        body_flags = record.biped_flags
        if (body_flags.head or body_flags.hair or body_flags.circlet
                or body_flags.long_hair or body_flags.addon_ears):
            equipment_tag = head_tag
        elif body_flags.body:
            equipment_tag = body_tag
        elif body_flags.hands or body_flags.forearms:
            equipment_tag = arms_tag
        elif body_flags.feet or body_flags.calves:
            equipment_tag = legs_tag
        elif body_flags.amulet:
            equipment_tag = amulet_tag
        elif body_flags.ring:
            equipment_tag = ring_tag
        elif body_flags.shield:
            equipment_tag = shield_tag
        else:
            return record.full # Weird record, don't change anything
        prefix_subs = (equipment_tag + armor_addition,)
        prefix_format = self.chosen_format
        if self._may_have_stats and '%02d' in prefix_format:
            # Armor rating is scaled up x100 in the records
            prefix_subs += (record.armorRating / 100,)
        return prefix_format % prefix_subs + record.full

#------------------------------------------------------------------------------
class NamesTweak_Body_Clothes(_ANamesTweak_Body_Tes4):
    tweak_read_classes = b'CLOT',
    tweak_name = _(u'Sort: Clothes')
    tweak_tip = _(u'Rename clothes to sort by type.')
    tweak_key = u'CLOT' # u'' is intended, not a record sig, ugh...
    tweak_log_msg = _(u'Clothes Renamed: %(total_changed)d')
    _choice_formats = [u'%s ', u'%s. ', u'%s - ', u'(%s) ']
    _example_item = _(u'Grey Trousers')
    _example_code = u'P'

#------------------------------------------------------------------------------
_re_old_potion_label = re.compile(u'^(-|X) ', re.U)
_re_old_potion_end = re.compile(u' -$', re.U)

class _ANamesTweak_Ingestibles(_ANamesTweak):
    """Names tweaker for potions."""
    tweak_read_classes = b'ALCH',
    tweak_name = _(u'Sort: Ingestibles')
    tweak_tip = _(u'Label ingestibles (potions and food) to sort by type.')
    tweak_key = u'ALCH' # u'' is intended, not a record sig, ugh...
    tweak_log_msg = _(u'Ingestibles Renamed: %(total_changed)d')
    _choice_formats = [u'%s ', u'%s. ', u'%s - ', u'(%s) ']

class NamesTweak_Ingestibles_Tes4(_ANamesTweak_Ingestibles,
                                  _AMgefNamesTweak):
    tweak_tip = _(u'Label ingestibles (potions and drinks) to sort by type '
                  u'and effect.')
    _example_item = _('Poison of Illness')
    _example_code = 'XD'

    def _exec_rename(self, record):
        # Remove existing label and ending
        wip_name = _re_old_potion_label.sub('', record.full)
        wip_name = _re_old_potion_end.sub('', wip_name)
        if record.flags.alch_is_food:
            return '.' + wip_name
        else:
            poison_tag = 'X' if record.is_harmful(self._tweak_mgef_hostiles) else ''
            effect_label = poison_tag + record.get_spell_school()
            return self.chosen_format % effect_label + wip_name

class NamesTweak_Ingestibles_Fo3(_ANamesTweak_Ingestibles):
    # Ingestibles are pretty much limited to food and medicine in FO3/FNV, so
    # we just show the equipment type
    _example_item = _(u'Radroach Meat')
    _example_code = u'F'
    _valid_ingestibles = set(range(10, 14))

    def _exec_rename(self, record):
        alch_etyp = record.equipment_type
        if alch_etyp in self._valid_ingestibles:
            etyp_label = u'CSFA'[alch_etyp - 10]
        else:
            etyp_label = u'U' # Unknown
        # Food doubles as the miscellaneous category, so label non-food in the
        # food category as 'other'
        if etyp_label == 'F' and not record.flags.alch_is_food:
            etyp_label = 'O'
        # Remove existing label and ending
        wip_name = _re_old_potion_label.sub('', record.full)
        wip_name = _re_old_potion_end.sub('', wip_name)
        return self.chosen_format % etyp_label + wip_name

#------------------------------------------------------------------------------
_re_old_magic_label = re.compile(r'^(\([ACDIMR]\d\)|\w{3,6}:) ', re.U)

class _ANamesTweak_Scrolls(IndexingTweak, _ANamesTweak):
    tweak_key = 'scrolls'
    _example_item = _('Fireball')
    _example_code = 'D'

class NamesTweak_NotesScrolls(_ANamesTweak_Scrolls, _AMgefNamesTweak):
    """Names tweaker for notes and scrolls - Oblivion only!"""
    tweak_read_classes = b'BOOK',
    tweak_name = _(u'Sort: Notes/Scrolls')
    tweak_tip = _(u'Mark notes and scrolls to sort separately from books.')
    tweak_log_msg = _(u'Notes and Scrolls Renamed: %(total_changed)d')
    _choice_formats = [u'~', u'~%s ', u'~%s. ', u'~%s - ', u'~(%s) ', u'----',
                       u'.', u'.%s ', u'.%s. ', u'.%s - ', u'.(%s) ']
    _may_lack_specifiers = True
    _look_up_ench = None
    _index_sigs = [b'ENCH']

    def _exec_rename(self, record):
        magic_format = self.chosen_format
        order_format = (u'~.', u'.~')[magic_format[0] == u'~']
        wip_name = record.full
        rec_ench = record.enchantment
        is_enchanted = bool(rec_ench)
        if is_enchanted and u'%s' in magic_format:
            enchantment = self._look_up_ench[rec_ench]
            if enchantment: ##: true?
                school = enchantment.get_spell_school()
            else: school = 'U' # U: unknown
            # Remove existing label
            wip_name = _re_old_magic_label.sub(u'', wip_name)
            wip_name = magic_format[1:] % school + wip_name
        # Order by whether or not the scroll is enchanted
        return order_format[is_enchanted] + wip_name

    def validate_values(self, chosen_values: tuple) -> str | None:
        wanted_fmt = chosen_values[0]
        if not wanted_fmt or wanted_fmt[0] not in ('~', '.'):
            return _("The format must begin with a '~' or a '.'. See the "
                     "'Tweak Names' section of the Advanced Readme for more "
                     "information.")
        return super().validate_values(chosen_values)

    def wants_record(self, record):
        return (record.flags.isScroll and not record.flags.isFixed and
                super().wants_record(record))

    def prepare_for_tweaking(self, patch_file):
        super().prepare_for_tweaking(patch_file)
        self._look_up_ench = self._indexed_records[b'ENCH']

#------------------------------------------------------------------------------
class NamesTweak_Scrolls(_ANamesTweak_Scrolls, _AEffectsTweak_Tes5):
    """Skyrim!"""
    tweak_read_classes = b'SCRL',
    tweak_name = _('Sort: Scrolls')
    tweak_tip = _('Mark scrolls to sort by magic school.')
    tweak_log_msg = _('Scrolls Renamed: %(total_changed)d')
    _choice_formats = ['%s ', '%s. ', '%s - ', '(%s) ', '----', '%s ', '%s. ',
                       '%s - ', '(%s) ']

    def _exec_rename(self, record):
        school_tag = record.get_spell_school(self._look_up_mgef)
        # Remove existing label
        wip_name = _re_old_magic_label.sub('', record.full)
        return self.chosen_format % school_tag + wip_name

#------------------------------------------------------------------------------
class _ANamesTweak_Spells(_ANamesTweak):
    """Names tweaker for spells."""
    tweak_read_classes = b'SPEL',
    tweak_name = _(u'Sort: Spells')
    tweak_tip = _(u'Label spells to sort by school and level.')
    tweak_key = u'SPEL' # u'' is intended, not a record sig, ugh...
    tweak_log_msg = _(u'Spells Renamed: %(total_changed)d')
    _choice_formats = [u'', u'----', u'%s ', u'%s. ', u'%s - ', u'(%s) ',
                       u'----', u'%s%02d ', u'%s%02d. ', u'%s%02d - ',
                       u'(%s%02d) ']
    _example_item = _(u'Fireball')
    _example_code = u'D'
    _example_stat = 2
    _may_have_stats = True
    _may_lack_specifiers = True

    def wants_record(self, record):
        return record.spell_type == 0 and super().wants_record(record)

    def _exec_rename(self, record):
        school_tag = record.get_spell_school(self._look_up_mgef)
        level_tag = record.get_spell_level()
        # Remove existing label
        wip_name = _re_old_magic_label.sub(u'', record.full)
        if u'%s' in self.chosen_format: # show spell school
            if u'%02d' in self.chosen_format: # also show level
                wip_name = self.chosen_format % (school_tag,
                                                 level_tag) + wip_name
            else:
                wip_name = self.chosen_format % school_tag + wip_name
        else:
            if u'%02d' in self.chosen_format: # no school, but show level
                wip_name = self.chosen_format % level_tag + wip_name
            else: # nothing special, just prepend a static format
                wip_name = self.chosen_format + wip_name
        return wip_name

class NamesTweak_Spells(_ANamesTweak_Spells, _AMgefNamesTweak):
    # Upgrade older format that used different values - we'll probably have to
    # keep this around indefinitely, unfortunately
    def init_tweak_config(self, configs):
        if self.tweak_key in configs:
            is_enabled, tweak_value = configs[self.tweak_key]
            if tweak_value in ('NOTAGS', ('NOTAGS',)):
                # NOTAGS was replaced by an empty string
                tweak_value = ('',)
            cleaned_tv = []
            for t_v in tweak_value:
                # %d was replaced by %02d
                cleaned_tv.append(t_v.replace('%d', '%02d'))
            tweak_value = tuple(cleaned_tv)
            configs[self.tweak_key] = (is_enabled, tweak_value)
        super(NamesTweak_Spells, self).init_tweak_config(configs)

class NamesTweak_Spells_Tes5(_ANamesTweak_Spells, _AEffectsTweak_Tes5): pass

#------------------------------------------------------------------------------
class _ANamesTweak_Weapons(_ANamesTweak):
    """Names tweaker for weapons and ammo."""
    tweak_read_classes = b'AMMO', b'WEAP',
    tweak_name = _(u'Sort: Weapons/Ammunition')
    tweak_tip = _(u'Label weapons and ammunition to sort by type and damage.')
    tweak_key = u'WEAP' # u'' is intended, not a record sig, ugh...
    tweak_log_msg = _(u'Weapons and Ammuntion Renamed: %(total_changed)d')
    _choice_formats = [u'%s ', u'%s. ', u'%s - ', u'(%s) ', u'----',
                       u'%s%02d ', u'%s%02d. ', u'%s%02d - ', u'(%s%02d) ']
    _may_have_stats = True
    _example_item = _('Elven Bow')
    _example_code = 'B'
    _example_stat = 14
    _valid_weapons = set() # override in subclasses
    _w_type_attr = '' # override in subclasses
    _weapon_tags = '' # override in subclasses

    def wants_record(self, record):
        # Do not use _ignored_chars, AMMO in FO3/FNV can start with dots
        ##: What about WEAP? Pre-tweak-pooling didn't do it - kept it that way,
        # but I'm not sure *why* pre-TP didn't do it
        old_full = record.full
        return old_full and old_full != self._exec_rename(record)

    def _exec_rename(self, record):
        if record._rec_sig == b'WEAP':
            weapon_index = getattr(record, self._w_type_attr)
            if weapon_index not in self._valid_weapons:
                format_subs = ('O',) # O, other
            else:
                format_subs = (self._weapon_tags[weapon_index],)
        else:
            format_subs = ('A',)
        if '%02d' in self.chosen_format:
            format_subs += (record.damage,)
        return self.chosen_format % format_subs + record.full

class NamesTweak_Weapons_Tes4(_ANamesTweak_Weapons):
    _valid_weapons = set(range(0, 6))
    _w_type_attr = u'weaponType'
    _weapon_tags = 'CDEFGB'

class NamesTweak_Weapons_Fo3(_ANamesTweak_Weapons):
    # AMMO does not have a damage field in FO3/FNV, so just adding 'A' to all
    # of them doesn't help much
    tweak_read_classes = b'WEAP',
    tweak_name = _(u'Sort: Weapons')
    tweak_tip = _(u'Label weapons to sort by type and damage.')
    _example_item = _(u'BB Gun')
    _example_code = u'S'
    _example_stat = 10
    _valid_weapons = set(range(0, 7))
    _w_type_attr = 'equipment_type'
    _weapon_tags = 'BESMUTL'

class NamesTweak_Weapons_Tes5(_ANamesTweak_Weapons):
    _valid_weapons = set(range(0, 10))
    _w_type_attr = 'animationType'
    _weapon_tags = 'HSDXMGWBTC'
    _example_stat = 13

#------------------------------------------------------------------------------
_re_old_ammo_label = re.compile(r'^(.*)( \(WG \d+\.\d+\))$')
_re_flst_ammo_weight = re.compile(r'^AmmoWeight(\d)(\d{2})List$')

class NamesTweak_AmmoWeight(_ANamesTweak):
    """Appends ammunition weight to the end of the ammunition's name."""
    tweak_read_classes = b'AMMO',
    tweak_name = _(u'Append Ammunition Weight')
    tweak_tip = _(u'Appends the weight of ammunition to the end of the '
                  u'ammunition name.')
    tweak_key = u'AmmoWeight'
    tweak_log_msg = _(u'Ammunition Renamed: %(total_changed)d')
    _choice_formats = [u' (WG %s)', u' (%s)']
    _example_item = _(u'Iron Arrow')
    _example_code = u'0.01'
    _prepends_name = True

    def _exec_rename(self, record):
        old_full = record.full
        fmt_weight = self.chosen_format % (
                u'%.2f' % self._get_record_weight(record))
        # Strip out any old weight labels if they're present
        ma_ammo = _re_old_ammo_label.match(old_full)
        if ma_ammo:
            return ma_ammo.group(1) + fmt_weight
        else:
            return old_full + fmt_weight

    def _get_record_weight(self, record):
        return record.weight or 0.0

class NamesTweak_AmmoWeight_Fnv(NamesTweak_AmmoWeight):
    _example_item = _(u'BB')

class NamesTweak_AmmoWeight_Fo3(IndexingTweak, NamesTweak_AmmoWeight_Fnv):
    """FO3 requires FWE (FO3 Wanderers Edition)."""
    tweak_tip = _(u'Requires FWE. Appends the FWE weight of ammunition to the '
                  u'end of the ammunition name.')
    _index_sigs = [b'FLST']

    def __init__(self, bashed_patch):
        super(NamesTweak_AmmoWeight_Fo3, self).__init__(bashed_patch)
        self._look_up_weight = None

    def prepare_for_tweaking(self, patch_file):
        super(NamesTweak_AmmoWeight_Fo3, self).prepare_for_tweaking(patch_file)
        # Gather weight from FWE FormID Lists
        self._look_up_weight = luw = defaultdict(lambda: 0.0)
        for flst_rec in self._indexed_records[b'FLST'].values():
            ma_flst = _re_flst_ammo_weight.match(flst_rec.eid)
            if ma_flst:
                flst_weight = float(f'{ma_flst.group(1)}.{ma_flst.group(2)}')
                for ammo_fid in flst_rec.formIDInList:
                    luw[ammo_fid] = flst_weight

    def wants_record(self, record):
        if self._look_up_weight is None:
            return True # We haven't collected weights yet, forward everything
        elif not self._look_up_weight:
            return False # We've collected weights, but not found anything
        return super(NamesTweak_AmmoWeight_Fo3, self).wants_record(record)

    def _get_record_weight(self, record):
        return self._look_up_weight[record.fid]

#------------------------------------------------------------------------------
class _ANamesTweak_RenameF(CustomChoiceTweak):
    """Base class for Rename Gold/Caps tweaks."""
    tweak_read_classes = b'MISC',
    tweak_key = 'rename_gold'
    _gold_fid = bush.game.master_fid(0x00000F)
    # Only interested in one specific record, see finish_tweaking below
    _found_gold = False
    _gold_attrs = bush.game.gold_attrs()

    def wants_record(self, record):
        return record.fid == self._gold_fid

    def tweak_record(self, record):
        record.full = self.choiceValues[self.chosen][0]
        self._found_gold = True

    def finish_tweaking(self, patch_file):
        # Gold001 is built into the engine, so if none of the plugins in the LO
        # override it (usually the game master does), we have to create an
        # override from scratch
        if not self._found_gold:
            gold_rec = patch_file.create_record(b'MISC', self._gold_fid)
            self.tweak_record(gold_rec) # Sets the FULL
            for gold_attr, gold_value in self._gold_attrs.items():
                if '.' in gold_attr:
                    # Check if we have to set a MelObject for a MelGroup's attr
                    ##: This should have a better solution (in records?)
                    obj_attr = gold_attr.split('.', maxsplit=1)[0]
                    if getattr(gold_rec, obj_attr) is None:
                        setattr(gold_rec, obj_attr,
                                gold_rec.getDefault(obj_attr))
                setattr_deep(gold_rec, gold_attr, gold_value)

    def tweak_log(self, log, count):
        # count would be pointless, always one record
        super().tweak_log(log, {})

class NamesTweak_RenameGold(_ANamesTweak_RenameF):
    """Changes the Gold001 record's FULL to something else."""
    tweak_name = _('Rename Gold')
    tweak_tip = _('Changes the name of gold to something of your choice.')
    tweak_log_msg = _('Gold Renamed.')
    tweak_choices = [(_('Septim'), _('Septim'))]

class NamesTweak_RenameCaps(_ANamesTweak_RenameF):
    """Fallout version of Rename Gold."""
    tweak_name = _('Rename Bottle Caps')
    tweak_tip = _('Changes the name of bottle caps to something of your '
                  'choice.')
    tweak_log_msg = _('Bottle Caps Renamed.')
    tweak_choices = [(_('Caps'), _('Caps'))]

class NamesTweak_RenamePennies(_ANamesTweak_RenameF):
    """Enderal version of Rename Gold."""
    tweak_name = _('Rename Pennies')
    tweak_tip = _('Changes the name of Endralean penny coins to something of '
                  'your choice.')
    tweak_log_msg = _('Endralean Penny Coins Renamed.')
    tweak_choices = [(_('Gold'), _('Gold'))]

#------------------------------------------------------------------------------
class _ATextReplacer(MultiTweakItem):
    """Base class for replacing any text via regular expressions."""
    tweak_read_classes = tuple(bush.game.text_replacer_rpaths)
    tweak_log_msg = _(u'Items Renamed: %(total_changed)d')
    # A dict that maps regexes we want to match to replacement strings. Those
    # replacements will be passed to re.sub, so they will apply in order and
    # may use the results of their regex groups. The replacements may also be
    # esubs (see bolt.build_esub).
    _tr_replacements = {}
    _tr_extra_gmsts = {} # override in implementations

    def __init__(self, bashed_patch):
        super(_ATextReplacer, self).__init__(bashed_patch)
        self._re_mapping = {re.compile(m): r for m, r
                            in self._tr_replacements.items()}
        # Convert the match/replace strings to record paths
        self._match_replace_rpaths = {
            rsig: tuple([RecPath(r) for r in rpaths])
            for rsig, rpaths in bush.game.text_replacer_rpaths.items()
        }

    def wants_record(self, record):
        def can_change(test_text):
            return any(m.search(test_text) for m in self._re_mapping)
        record_sig = record._rec_sig
        if record_sig == b'GMST':
            # GMST needs this check which can't be handled by RecPath yet,
            # thankfully it's identical for all games
            return record.eid[0] == u's' and can_change(record.value or u'')
        else:
            for rp in self._match_replace_rpaths[record_sig]: # type: RecPath
                for val in rp.rp_eval(record):
                    if can_change(val or u''): return True
            return False

    def tweak_record(self, record):
        record_sig = record._rec_sig
        for re_to_match, replacement in self._re_mapping.items():
            replacement_sub = re_to_match.sub
            for rp in self._match_replace_rpaths[record_sig]: # type: RecPath
                rp.rp_map(record, replacement_sub, replacement)

    def finish_tweaking(self, patch_file):
        # These GMSTs don't exist in Oblivion.esm, so create them in the BP
        for extra_eid, extra_val in self._tr_extra_gmsts.items():
            patch_file.new_gmst(extra_eid, extra_val)

#------------------------------------------------------------------------------
class NamesTweak_DwarvenToDwemer(_ATextReplacer):
    """Replaces 'dwarven' with 'dwemer' to better follow lore."""
    tweak_name = _(u'Lore Friendly Text: Dwarven -> Dwemer')
    tweak_tip = _(u'Replace any occurrences of the word "dwarf" or "dwarven" '
                  u'with "dwemer" to better follow lore.')
    tweak_key = u'Dwemer'
    tweak_choices = [(u'Lore Friendly Text: Dwarven -> Dwemer', u'Dwemer')]
    _tr_replacements = {r'\b(d|D)(?:warven|warfs?|warves)\b': r'\1wemer'}

#------------------------------------------------------------------------------
class NamesTweak_DwarfsToDwarves(_ATextReplacer):
    """Replaces 'dwarfs' with 'dwarves' for proper spelling."""
    tweak_name = _(u'Proper English Text: Dwarfs -> Dwarves')
    tweak_tip = _(u'Replace any occurrences of the word "dwarfs" with '
                  u'"dwarves" to better follow proper English.')
    tweak_key = u'Dwarfs'
    tweak_choices = [(u'Proper English Text: Dwarfs -> Dwarves', u'Dwarves')]
    tweak_order = 11 # Run after Dwarven -> Dwemer for consistency
    _tr_replacements = {r'\b(d|D)warfs\b': r'\1warves'}

#------------------------------------------------------------------------------
class NamesTweak_StaffsToStaves(_ATextReplacer):
    """Replaces 'staffs' with 'staves' for proper spelling."""
    tweak_name = _(u'Proper English Text: Staffs -> Staves')
    tweak_tip = _(u'Replace any occurrences of the word "staffs" with '
                  u'"staves" to better follow proper English.')
    tweak_key = u'Staffs'
    tweak_choices = [(u'Proper English Text: Staffs -> Staves', u'Staves')]
    _tr_replacements = {r'\b(s|S)taffs\b': r'\1taves'}

#------------------------------------------------------------------------------
class NamesTweak_FatigueToStamina(_ATextReplacer):
    """Replaces 'fatigue' with 'stamina', similar to Skyrim."""
    tweak_name = _(u'Skyrim-style Text: Fatigue -> Stamina')
    tweak_tip = _(u'Replace any occurrences of the word "fatigue" with '
                  u'"stamina", similar to Skyrim.')
    tweak_key = u'FatigueToStamina'
    tweak_choices = [(u'1.0', u'1.0')]
    _tr_replacements = {r'\b(f|F)atigue\b': build_esub('$1(s)tamina')}
    _tr_extra_gmsts = {u'sDerivedAttributeNameFatigue': u'Stamina'}

#------------------------------------------------------------------------------
def _mta_esub(first_suffix): # small helper to deduplicate that nonsense
    return build_esub(r'\1%s $2(a)rcher' % first_suffix)

class NamesTweak_MarksmanToArchery(_ATextReplacer):
    """Replaces 'marksman' with 'archery', similar to Skyrim."""
    tweak_name = _(u'Skyrim-style Text: Marksman -> Archery')
    tweak_tip = _(u'Replace any occurrences of the word "marksman" with '
                  u'"archery", similar to Skyrim.')
    tweak_key = u'MarksmanToArchery'
    tweak_choices = [(u'1.0', u'1.0')]
    _tr_replacements = {
        r'\b(t|T)he (m|M)arksman\b': _mta_esub('he'),
        r'\b(a|A) (m|M)arksman\b': _mta_esub('n'),
        # These four work around vanilla Oblivion records, ugh...
        r'\b(a|A)pprentice (m|M)arksman\b': _mta_esub('pprentice'),
        r'\b(j|J)ourneyman (m|M)arksman\b': _mta_esub('ourneyman'),
        r'\b(e|E)xpert (m|M)arksman\b': _mta_esub('xpert'),
        r'\b(m|M)aster (m|M)arksman\b': _mta_esub('aster'),
        r'\b(m|M)arksman\b': build_esub('$1(a)rchery'),
    }
    _tr_extra_gmsts = {u'sSkillNameMarksman': u'Archery',
                       u'sSkillDescMarksman': u'Archery Description'}

#------------------------------------------------------------------------------
class NamesTweak_SecurityToLockpicking(_ATextReplacer):
    """Replaces 'security' with 'lockpicking', similar to Skyrim."""
    tweak_read_classes = tuple(c for c in _ATextReplacer.tweak_read_classes
                               if c != b'BOOK') # way too many false positives
    tweak_name = _(u'Skyrim-style Text: Security -> Lockpicking')
    tweak_tip = _(u'Replace any occurrences of the word "security" with '
                  u'"lockpicking", similar to Skyrim.')
    tweak_key = u'SecurityToLockpicking'
    tweak_choices = [(u'1.0', u'1.0')]
    _tr_replacements = {r'\b(s|S)ecurity\b': build_esub('$1(l)ockpicking')}
    _tr_extra_gmsts = {u'sSkillNameSecurity': u'Lockpicking',
                       u'sSkillDescSecurity': u'Lockpicking Description'}

#------------------------------------------------------------------------------
class TweakNamesPatcher(MultiTweaker):
    """Tweaks record full names in various ways."""
    _tweak_classes = {globals()[t] for t in bush.game.names_tweaks}

    def __init__(self, p_name, p_file, enabled_tweaks: list[MultiTweakItem]):
        super().__init__(p_name, p_file, enabled_tweaks)
        body_part_tags = ''
        for names_tweak in enabled_tweaks:
            # Always the first one if it's enabled, so this is safe
            if isinstance(names_tweak, NamesTweak_BodyPartCodes):
                body_part_tags = names_tweak.choiceValues[
                    names_tweak.chosen][0]
            elif isinstance(names_tweak, _ANamesTweak_Body):
                if not body_part_tags:
                    raise BPConfigError(
                        _("'Body Part Codes' must be enabled when using the "
                          "'%(bpc_dependent_tweak)s' tweak.") % {
                            'bpc_dependent_tweak': names_tweak.tweak_name})
                names_tweak._tweak_body_tags = body_part_tags
