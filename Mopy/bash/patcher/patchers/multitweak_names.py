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
"""This module contains oblivion multitweak item patcher classes that belong
to the Names Multitweaker - as well as the tweaker itself."""

import re
from collections import defaultdict, OrderedDict

# Internal
from .base import MultiTweakItem, IndexingTweak, MultiTweaker, \
    CustomChoiceTweak
from ... import bush
from ...bolt import build_esub, RecPath
from ...exception import AbstractError, BPConfigError

_ignored_chars = frozenset(u'+-=.()[]<>')

##: The Armor/Clothes tweaks allow customizing the tags used. The others should
# too, but before we do that we need to replace NamesTweak_BodyPartCodes with
# something better (e.g. a special 'settings patcher' inside the BP)

class _ANamesTweak(CustomChoiceTweak):
    """Shared code of names tweaks."""
    _tweak_mgef_hostiles = set()
    _tweak_mgef_school = {}
    _choice_formats = [] # The default formats for this tweak
    _example_item = _example_code = u'' # An example item name and its code
    _example_stat = 0 # The example item's stat
    _may_have_stats = False # Whether formats with '%02d' in them are OK
    _may_lack_specifiers = False # Whether formats without '%s' in them are OK
    _prepends_name = False # Whether the tweak prepends or appends the name

    def __init__(self):
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
        super(_ANamesTweak, self).__init__()

    @property
    def chosen_format(self): return self.choiceValues[self.chosen][0]

    def validate_values(self, chosen_values):
        wanted_fmt = chosen_values[0]
        if self._may_lack_specifiers:
            if self._may_have_stats:
                # May contain any combination of a single %s and a single %02d,
                # but no other specifiers
                fmt_params = ()
                if u'%s' in wanted_fmt:
                    fmt_params = (u'A', 1) if u'%02d' in wanted_fmt else u'A'
                elif u'%02d' in wanted_fmt:
                    fmt_params = 1
                if fmt_params:
                    try:
                        wanted_fmt % fmt_params
                    except TypeError:
                        return _(u'The format you entered is not valid for '
                                 u'this tweak. It may contain exactly one '
                                 u"'%s' and one '%02d' as well as any regular "
                                 u'characters, but no other format '
                                 u"specifiers. See the 'Tweak Names' section "
                                 u'of the Advanced Readme for more '
                                 u'information.')
            else:
                # May contain a single %s, but no other specifiers
                if u'%s' in wanted_fmt:
                    try:
                        wanted_fmt % u'A'
                    except TypeError:
                        return _(u'The format you entered is not valid for '
                                 u'this tweak. It may contain exactly one '
                                 u"'%s' and any regular characters, but no "
                                 u"other format specifiers. See the 'Tweak "
                                 u"Names' section of the Advanced Readme for "
                                 u'more information.')
        elif self._may_have_stats:
            # Must contain a single %s and may contain a %02d
            fmt_params = (u'A', 1) if u'%02d' in wanted_fmt else u'A'
            try:
                wanted_fmt % fmt_params
            except TypeError:
                return _(u'The format you entered is not valid for this '
                         u"tweak. It must contain exactly one '%s' and may "
                         u"contain one '%02d' as well as any regular "
                         u'characters, but no other format specifiers. See '
                         u"the 'Tweak Names' section of the Advanced Readme "
                         u'for more information.')
        else:
            # Must contain a single %s and no other specifiers
            try:
                wanted_fmt % u'A'
            except TypeError:
                return _(u'The format you entered is not valid for this '
                         u"tweak. It must contain exactly one '%s' and may "
                         u'contain any regular characters, but no other '
                         u"format specifiers. See the 'Tweak Names' section "
                         u'of the Advanced Readme for more information.')
        return super(_ANamesTweak, self).validate_values(chosen_values)

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
        raise AbstractError(u'_exec_rename not implemented')

class _AMgefNamesTweak(_ANamesTweak):
    """Shared code of a few names tweaks that handle MGEFs.
    Oblivion-specific."""
    def prepare_for_tweaking(self, patch_file):
        self._tweak_mgef_hostiles = patch_file.getMgefHostiles()
        self._tweak_mgef_school = patch_file.getMgefSchool()
        super(_ANamesTweak, self).prepare_for_tweaking(patch_file)

    def _is_effect_hostile(self, magic_effect):
        """Returns a truthy value if the specified MGEF is hostile."""
        return (magic_effect.scriptEffect.flags.hostile
                if magic_effect.scriptEffect
                else magic_effect.effect_sig in self._tweak_mgef_hostiles)

    def _get_effect_school(self, magic_effect):
        """Returns the school of the specified MGEF."""
        return (magic_effect.scriptEffect.school if magic_effect.scriptEffect
                else self._tweak_mgef_school.get(magic_effect.effect_sig, 6))

    def wants_record(self, record):
        # Once we have MGEFs indexed, we can try renaming to check more
        # thoroughly (i.e. during the buildPatch/apply phase)
        old_full = record.full
        return (old_full and (not self._tweak_mgef_hostiles or
                old_full != self._exec_rename(record)))

##: This would be better handled with some sort of settings menu for the BP
class NamesTweak_BodyPartCodes(CustomChoiceTweak): # loads no records
    """Only exists to change _PFile.bodyTags - see _ANamesTweaker.__init__ for
    the implementation."""
    tweak_name = _(u'Body Part Codes')
    tweak_tip = _(u'Sets body part codes used by Armor/Clothes name tweaks.')
    tweak_key = u'bodyTags'
    tweak_log_msg = u'' # we log nothing
    tweak_choices = [(c, c) for c in bush.game.body_part_codes]
    tweak_order = 9 # Run before all other tweaks

    def __init__(self):
        super(NamesTweak_BodyPartCodes, self).__init__()
        len_first = len(self.tweak_choices[0][0])
        # Verify that the body_part_codes constant is valid
        for tc in self.tweak_choices[1:]:
            if len(tc[0]) != len_first:
                raise SyntaxError(u'Not all body part codes have the same '
                                  u'length for this game.')

    def tweak_log(self, log, count): pass # 'internal' tweak, log nothing

    def validate_values(self, chosen_values):
        cho_len = len(chosen_values[0])
        req_len = len(self.tweak_choices[0][0])
        if cho_len != req_len:
            return _(u'The value has length %d, but must have length %d to '
                     u'match the number of body part types for this game. See '
                     u"the 'Tweak Names' section of the Advanced Readme for "
                     u'more information.') % (cho_len, req_len)
        return super(NamesTweak_BodyPartCodes, self).validate_values(
            chosen_values)

#------------------------------------------------------------------------------
class _ANamesTweak_Body(_ANamesTweak):
    """Shared code of 'body names' tweaks."""
    _tweak_body_tags = u'' # Set in _ANamesTweaker.__init__

    def wants_record(self, record):
        if self._is_nonplayable(record):
            return False
        return super(_ANamesTweak_Body, self).wants_record(record)

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
        else: return record.full # Weird record, don't change anything
        armor_addition = (u'LH'[body_flags.heavyArmor]
                          if record._rec_sig == b'ARMO' else u'')
        prefix_subs = (equipment_tag + armor_addition,)
        prefix_format = self.chosen_format
        if self._may_have_stats and u'%02d' in prefix_format:
            # Armor rating is scaled up x100 in the records
            prefix_subs += (record.strength / 100,)
        return prefix_format % prefix_subs + record.full

class  _ANamesTweak_Body_Fo3(_ANamesTweak_Body):
    _is_fnv = bush.game.fsName == u'FalloutNV'

    def _exec_rename(self, record):
        head_tag, body_tag, gloves_tag, pipboy_tag, backpack_tag, fancy_tag, \
        accessory_tag = self._tweak_body_tags
        gen_flags = record.generalFlags
        if gen_flags.powerArmor:
            armor_addition = u'P'
        elif gen_flags.heavyArmor:
            armor_addition = u'H'
        elif self._is_fnv and gen_flags.medium_armor: # flag added in FNV
            armor_addition = u'M'
        else: # light armor
            armor_addition = u'L'
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
        elif (body_flags.bodyAddOn1 or body_flags.bodyAddOn2 or
              body_flags.bodyAddOn3):
            equipment_tag = accessory_tag
        elif body_flags.pipboy:
            equipment_tag = pipboy_tag
        else: return record.full # Weird record, don't change anything
        prefix_subs = (equipment_tag + armor_addition,)
        prefix_format = self.chosen_format
        if self._may_have_stats and u'%02d' in prefix_format:
            if self._is_fnv:
                # Use damage threshold instead of damage resistance for FNV.
                # Note that that one is *not* scaled up x100 in the records
                prefix_subs += (record.dt,)
            else:
                # Damage resistance is scaled up x100 in the records
                prefix_subs += (record.dr / 100,)
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

class NamesTweak_Body_Armor_Fo3(_ANamesTweak_Body_Fo3,
                                _ANamesTweak_Body_Armor):
    _example_item = _(u'Sleepwear')
    _example_code = u'A'
    _example_stat = 1

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

class NamesTweak_Ingestibles_Tes4(_ANamesTweak_Ingestibles, _AMgefNamesTweak):
    tweak_read_classes = b'ALCH',
    tweak_tip = _(u'Label ingestibles (potions and drinks) to sort by type '
                  u'and effect.')
    _example_item = _(u'Illness')
    _example_code = u'XD'

    def _exec_rename(self, record):
        school = 6 # Default to 6 (U: unknown)
        for i, rec_effect in enumerate(record.effects):
            if i == 0:
                school = self._get_effect_school(rec_effect)
            # Non-hostile effect?
            if not self._is_effect_hostile(rec_effect):
                is_poison = False
                break
        else:
            is_poison = True
        # Remove existing label and ending
        wip_name = _re_old_potion_label.sub(u'', record.full)
        wip_name = _re_old_potion_end.sub(u'', wip_name)
        if record.flags.isFood:
            return u'.' + wip_name
        else:
            effect_label = (u'X' if is_poison else u'') + u'ACDIMRU'[school]
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
        if etyp_label == u'F' and not record.flags.isFood:
            etyp_label = u'O'
        return self.chosen_format % etyp_label + record.full

#------------------------------------------------------------------------------
_re_old_magic_label = re.compile(r'^(\([ACDIMR]\d\)|\w{3,6}:) ', re.U)

class NamesTweak_Scrolls(_AMgefNamesTweak, IndexingTweak):
    """Names tweaker for scrolls."""
    tweak_read_classes = b'BOOK',
    tweak_name = _(u'Sort: Notes/Scrolls')
    tweak_tip = _(u'Mark notes and scrolls to sort separately from books.')
    tweak_key = u'scrolls'
    tweak_log_msg = _(u'Notes and Scrolls Renamed: %(total_changed)d')
    _choice_formats = [u'~', u'~%s ', u'~%s. ', u'~%s - ', u'~(%s) ', u'----',
                       u'.', u'.%s ', u'.%s. ', u'.%s - ', u'.(%s) ']
    _example_item = _(u'Fireball')
    _example_code = u'D'
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
            school = 6 # Default to 6 (U: unknown)
            enchantment = self._look_up_ench[rec_ench]
            if enchantment and enchantment.effects:
                school = self._get_effect_school(enchantment.effects[0])
            # Remove existing label
            wip_name = _re_old_magic_label.sub(u'', wip_name)
            wip_name = magic_format[1:] % u'ACDIMRU'[school] + wip_name
        # Order by whether or not the scroll is enchanted
        return order_format[is_enchanted] + wip_name

    def validate_values(self, chosen_values):
        wanted_fmt = chosen_values[0]
        if not wanted_fmt or wanted_fmt[0] not in (u'~', u'.'):
            return _(u"The format must begin with a '~' or a '.'. See the "
                     u"'Tweak Names' section of the Advanced Readme for more "
                     u'information.')
        return super(NamesTweak_Scrolls, self).validate_values(chosen_values)

    def wants_record(self, record):
        return (record.flags.isScroll and not record.flags.isFixed and
                super(NamesTweak_Scrolls, self).wants_record(record))

    def prepare_for_tweaking(self, patch_file):
        super(NamesTweak_Scrolls, self).prepare_for_tweaking(patch_file)
        self._look_up_ench = self._indexed_records[b'ENCH']

#------------------------------------------------------------------------------
class NamesTweak_Spells(_AMgefNamesTweak):
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
        return record.spellType == 0 and super(
            NamesTweak_Spells, self).wants_record(record)

    def _exec_rename(self, record):
        school = 6 # Default to 6 (U: unknown)
        if record.effects:
            school = self._get_effect_school(record.effects[0])
        # Remove existing label
        wip_name = _re_old_magic_label.sub(u'', record.full)
        if u'%s' in self.chosen_format: # show spell school
            if u'%02d' in self.chosen_format: # also show level
                wip_name = self.chosen_format % (u'ACDIMRU'[school],
                                                 record.level) + wip_name
            else:
                wip_name = self.chosen_format % u'ACDIMRU'[school] + wip_name
        else:
            if u'%02d' in self.chosen_format: # no school, but show level
                wip_name = self.chosen_format % record.level + wip_name
            else: # nothing special, just prepend a static format
                wip_name = self.chosen_format + wip_name
        return wip_name

    # Upgrade older format that used different values - drop on VDATA3?
    def init_tweak_config(self, configs):
        if self.tweak_key in configs:
            is_enabled, tweak_value = configs[self.tweak_key]
            if tweak_value == u'NOTAGS':
                # NOTAGS was replaced by an empty string
                tweak_value = u''
            elif u'%d' in tweak_value:
                # %d was replaced by %02d
                tweak_value = tweak_value.replace(u'%d', u'%02d')
            configs[self.tweak_key] = (is_enabled, tweak_value)
        super(NamesTweak_Spells, self).init_tweak_config(configs)

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

    def wants_record(self, record):
        # Do not use _ignored_chars, AMMO in FO3/FNV can start with dots
        ##: What about WEAP? Pre-tweak-pooling didn't do it - kept it that way,
        # but I'm not sure *why* pre-TP didn't do it
        old_full = record.full
        return (old_full and old_full != self._exec_rename(record))

class NamesTweak_Weapons_Tes4(_ANamesTweak_Weapons):
    _example_item = _(u'Elven Bow')
    _example_code = u'B'
    _example_stat = 14
    _valid_weapons = set(range(0, 5))
    _w_type_attr = u'weaponType'

    def _exec_rename(self, record):
        if record._rec_sig == b'WEAP':
            weapon_index = record.weaponType
            if weapon_index not in self._valid_weapons:
                weapon_index = 6 # O, other
            format_subs = (u'CDEFGBO'[weapon_index],)
        else:
            format_subs = (u'A',)
        if u'%02d' in self.chosen_format:
            format_subs += (record.damage,)
        return self.chosen_format % format_subs + record.full

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
    _w_type_attr = u'equipment_type'

    def _exec_rename(self, record):
        weap_etyp = record.equipment_type
        if weap_etyp not in self._valid_weapons:
            weap_etyp = 7 # O, other
        format_subs = (u'BESMUTLO'[weap_etyp],)
        if u'%02d' in self.chosen_format:
            format_subs += (record.damage,)
        return self.chosen_format % format_subs + record.full

#------------------------------------------------------------------------------
_re_old_ammo_label = re.compile(r'^(.*)( \(WG \d+\.\d+\))$')
_re_flst_ammo_weight = re.compile(r'^AmmoWeight(\d)(\d{2})List$')

class _ANamesTweak_AmmoWeight(_ANamesTweak):
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
        raise AbstractError(u'_get_record_weight not implemented')

class NamesTweak_AmmoWeight(_ANamesTweak_AmmoWeight):
    def _get_record_weight(self, record):
        return record.weight

class NamesTweak_AmmoWeight_Fnv(NamesTweak_AmmoWeight):
    _example_item = _(u'BB')

class NamesTweak_AmmoWeight_Fo3(NamesTweak_AmmoWeight_Fnv, IndexingTweak):
    """FO3 requires FWE (FO3 Wanderers Edition)."""
    tweak_tip = _(u'Requires FWE. Appends the FWE weight of ammunition to the '
                  u'end of the ammunition name.')
    _index_sigs = [b'FLST']

    def __init__(self):
        super(NamesTweak_AmmoWeight_Fo3, self).__init__()
        self._look_up_weight = None

    def prepare_for_tweaking(self, patch_file):
        super(NamesTweak_AmmoWeight_Fo3, self).prepare_for_tweaking(patch_file)
        # Gather weight from FWE FormID Lists
        self._look_up_weight = luw = defaultdict(lambda: 0.0)
        for flst_rec in self._indexed_records[b'FLST'].values():
            ma_flst = _re_flst_ammo_weight.match(flst_rec.eid)
            if ma_flst:
                flst_weight = float(u'%s.%s' % (ma_flst.group(1),
                                                ma_flst.group(2)))
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
class _ATextReplacer(MultiTweakItem):
    """Base class for replacing any text via regular expressions."""
    ##: Move to game/*/constants, and boom, we have a cross-game text replacer!
    _match_replace_rpaths = {
        b'ALCH': (u'full', u'effects[i].scriptEffect?.full'),
        b'AMMO': (u'full',),
        b'APPA': (u'full',),
        b'ARMO': (u'full',),
        b'BOOK': (u'full', u'book_text'),
        b'BSGN': (u'full', u'description'),
        b'CLAS': (u'full', u'description'),
        b'CLOT': (u'full',),
        b'CONT': (u'full',),
        b'CREA': (u'full',),
        b'DOOR': (u'full',),
        b'ENCH': (u'full', u'effects[i].scriptEffect?.full',),
        b'EYES': (u'full',),
        b'FACT': (u'full',), ##: maybe add male_title/female_title?
        b'FLOR': (u'full',),
        b'FURN': (u'full',),
        b'GMST': (u'value',),
        b'HAIR': (u'full',),
        b'INGR': (u'full', u'effects[i].scriptEffect?.full'),
        b'KEYM': (u'full',),
        b'LIGH': (u'full',),
        b'LSCR': (u'full', u'description'),
        b'MGEF': (u'full', u'description'),
        b'MISC': (u'full',),
        b'NPC_': (u'full',),
        b'QUST': (u'full', u'stages[i].entries[i].text'),
        b'RACE': (u'full', u'description'),
        b'SGST': (u'full', u'effects[i].scriptEffect?.full'),
        b'SKIL': (u'description', u'apprentice', u'journeyman', u'expert',
                  u'master'),
        b'SLGM': (u'full',),
        b'SPEL': (u'full', u'effects[i].scriptEffect?.full'),
        b'WEAP': (u'full',),
    }
    tweak_read_classes = tuple(_match_replace_rpaths)
    tweak_log_msg = _(u'Items Renamed: %(total_changed)d')
    # Will be passed to OrderedDict to construct a dict that maps regexes we
    # want to match to replacement strings. Those replacements will be passed
    # to re.sub, so they will apply in order and may use the results of their
    # regex groups. # PY3: replace with regular dict
    _tr_replacements = []
    _tr_extra_gmsts = {} # override in implementations

    def __init__(self):
        super(_ATextReplacer, self).__init__()
        self._re_mapping = OrderedDict([(re.compile(m, re.U), r) for m, r in
                                        self._tr_replacements])
        # Convert the match/replace strings to record paths
        self._match_replace_rpaths = {
            rsig: tuple([RecPath(r) for r in rpaths])
            for rsig, rpaths in self._match_replace_rpaths.items()
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
                if not rp.rp_exists(record): continue
                for val in rp.rp_eval(record):
                    if can_change(val or u''): return True
            return False

    def tweak_record(self, record):
        record_sig = record._rec_sig
        for re_to_match, replacement in self._re_mapping.items():
            replacement_sub = re_to_match.sub
            def exec_replacement(rec_val):
                if rec_val: # or blow up on re.sub
                    return replacement_sub(replacement, rec_val)
                return rec_val
            for rp in self._match_replace_rpaths[record_sig]: # type: RecPath
                if rp.rp_exists(record):
                    rp.rp_map(record, exec_replacement)

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
    _tr_replacements = [(r'\b(d|D)(?:warven|warf)\b', r'\1wemer')]

#------------------------------------------------------------------------------
class NamesTweak_DwarfsToDwarves(_ATextReplacer):
    """Replaces 'dwarfs' with 'dwarves' for proper spelling."""
    tweak_name = _(u'Proper English Text: Dwarfs -> Dwarves')
    tweak_tip = _(u'Replace any occurrences of the word "dwarfs" with '
                  u'"dwarves" to better follow proper English.')
    tweak_key = u'Dwarfs'
    tweak_choices = [(u'Proper English Text: Dwarfs -> Dwarves', u'Dwarves')]
    _tr_replacements = [(r'\b(d|D)warfs\b', r'\1warves')]

#------------------------------------------------------------------------------
class NamesTweak_StaffsToStaves(_ATextReplacer):
    """Replaces 'staffs' with 'staves' for proper spelling."""
    tweak_name = _(u'Proper English Text: Staffs -> Staves')
    tweak_tip = _(u'Replace any occurrences of the word "staffs" with '
                  u'"staves" to better follow proper English.')
    tweak_key = u'Staffs'
    tweak_choices = [(u'Proper English Text: Staffs -> Staves', u'Staves')]
    _tr_replacements = [(r'\b(s|S)taffs\b', r'\1taves')]

#------------------------------------------------------------------------------
class NamesTweak_FatigueToStamina(_ATextReplacer):
    """Replaces 'fatigue' with 'stamina', similar to Skyrim."""
    tweak_name = _(u'Skyrim-style Text: Fatigue -> Stamina')
    tweak_tip = _(u'Replace any occurrences of the word "fatigue" with '
                  u'"stamina", similar to Skyrim.')
    tweak_key = u'FatigueToStamina'
    tweak_choices = [(u'1.0', u'1.0')]
    _tr_replacements = [(r'\b(f|F)atigue\b', build_esub(u'$1(s)tamina'))]
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
    _tr_replacements = [
        (r'\b(t|T)he (m|M)arksman\b', _mta_esub(u'he')),
        (r'\b(a|A) (m|M)arksman\b', _mta_esub(u'n')),
        # These four work around vanilla Oblivion records, ugh...
        (r'\b(a|A)pprentice (m|M)arksman\b', _mta_esub(u'pprentice')),
        (r'\b(j|J)ourneyman (m|M)arksman\b', _mta_esub(u'ourneyman')),
        (r'\b(e|E)xpert (m|M)arksman\b', _mta_esub(u'xpert')),
        (r'\b(m|M)aster (m|M)arksman\b', _mta_esub(u'aster')),
        (r'\b(m|M)arksman\b', build_esub(u'$1(a)rchery')),
    ]
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
    _tr_replacements = [
        (r'\b(s|S)ecurity\b', build_esub(u'$1(l)ockpicking'))
    ]
    _tr_extra_gmsts = {u'sSkillNameSecurity': u'Lockpicking',
                       u'sSkillDescSecurity': u'Lockpicking Description'}

#------------------------------------------------------------------------------
class TweakNamesPatcher(MultiTweaker):
    """Tweaks record full names in various ways."""
    _tweak_classes = {globals()[t] for t in bush.game.names_tweaks}

    def __init__(self, p_name, p_file, enabled_tweaks):
        super(TweakNamesPatcher, self).__init__(p_name, p_file, enabled_tweaks)
        body_part_tags = u''
        for names_tweak in enabled_tweaks:
            # Always the first one if it's enabled, so this is safe
            if isinstance(names_tweak, NamesTweak_BodyPartCodes):
                body_part_tags = p_file.bodyTags = names_tweak.choiceValues[
                    names_tweak.chosen][0]
            elif isinstance(names_tweak, _ANamesTweak_Body):
                if not body_part_tags:
                    raise BPConfigError(_(u"'Body Part Codes' must be enabled "
                                          u"when using the '%s' tweak.")
                                        % names_tweak.tweak_name)
                names_tweak._tweak_body_tags = body_part_tags
