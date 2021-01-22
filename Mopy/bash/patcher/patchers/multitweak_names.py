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

from __future__ import division

import re
from collections import OrderedDict

# Internal
from ...bolt import build_esub, RecPath
from ...exception import AbstractError
from ...mod_files import LoadFactory, ModFile  # yuck, see usage below
from ...patcher.patchers.base import MultiTweakItem
from ...patcher.patchers.base import MultiTweaker

_ignored_chars=frozenset(u'+-=.()[]')

class _ANamesTweak(MultiTweakItem):
    """Shared code of names tweaks."""
    tweak_log_msg = _(u'Items Renamed: %(total_changed)d')
    _tweak_mgef_hostiles = set()
    _tweak_mgef_school = {}

    @property
    def chosen_format(self): return self.choiceValues[self.chosen][0]

    def tweak_record(self, record):
        record.full = self._exec_rename(record)

    def _do_exec_rename(self, *placeholder):
        """Does the actual renaming, returning the new name as its result.
        Should take any information it needs as parameters - see overrides for
        examples."""
        raise AbstractError(u'_do_exec_rename not implemented')

    def _exec_rename(self, record):
        """Convenience method that calls _do_exec_rename, passing the correct
        record attributes in."""
        return self._do_exec_rename(*self._get_rename_params(record))

    def _get_rename_params(self, record):
        """Returns the parameters that should be passed to _do_exec_rename.
        Passes only the record itself by default."""
        return (record,)

    def _is_effect_hostile(self, magic_effect):
        """Returns a truthy value if the specified MGEF is hostile."""
        return (magic_effect.scriptEffect.flags.hostile
                if magic_effect.scriptEffect
                else magic_effect.effect_sig in self._tweak_mgef_hostiles)

    def _try_renaming(self, record):
        """Checks if renaming via _exec_rename would change the specified
        record's name."""
        return record.full != self._exec_rename(record)

    def prepare_for_tweaking(self, patch_file):
        # These are cached, so fine to call for all tweaks
        self._tweak_mgef_hostiles = patch_file.getMgefHostiles()
        self._tweak_mgef_school = patch_file.getMgefSchool()

class _AMgefNamesTweak(_ANamesTweak):
    """Shared code of a few names tweaks that handle MGEFs."""
    def _get_effect_school(self, magic_effect):
        """Returns the school of the specified MGEF."""
        return (magic_effect.scriptEffect.school if magic_effect.scriptEffect
                else self._tweak_mgef_school.get(magic_effect.effect_sig, 6))

    def wants_record(self, record):
        # Once we have MGEFs indexed, we can try renaming to check more
        # thoroughly (i.e. during the buildPatch/apply phase)
        return (record.full and (not self._tweak_mgef_hostiles or
                self._try_renaming(record)))

##: This would be better handled with some sort of settings menu for the BP
class NamesTweak_BodyTags(MultiTweakItem): # not _ANamesTweak, no classes!
    """Only exists to change _PFile.bodyTags - see _ANamesTweaker.__init__ for
    the implementation."""
    tweak_name = _(u'Body Part Codes')
    tweak_tip = _(u'Sets body part codes used by Armor/Clothes name tweaks. '
                  u'A: Amulet, R: Ring, etc.')
    tweak_key = u'bodyTags'
    tweak_choices = [(u'ARGHTCCPBS', u'ARGHTCCPBS'),
                     (u'ABGHINOPSL', u'ABGHINOPSL')]
    tweak_order = 9 # Run before all other tweaks

    def tweak_log(self, log, count): pass # 'internal' tweak, log nothing

#------------------------------------------------------------------------------
class _ANamesTweak_Body(_ANamesTweak):
    """Shared code of 'body names' tweaks."""
    _tweak_body_tags = u'' # set in _ANamesTweaker.__init__

    def wants_record(self, record):
        if self._is_nonplayable(record):
            return False
        old_full = record.full
        return (old_full and old_full[0] not in _ignored_chars and
                self._try_renaming(record))

    def _do_exec_rename(self, record, heavy_armor_addition, is_head, is_ring,
                        is_amulet, is_robe, is_chest, is_pants, is_gloves,
                        is_shoes, is_tail, is_shield):
        record_full = record.full
        amulet_tag, ring_tag, gloves_tag, head_tag, tail_tag, robe_tag, \
        chest_tag, pants_tag, shoes_tag, shield_tag = self._tweak_body_tags
        if is_head: equipment_tag = head_tag
        elif is_ring: equipment_tag = ring_tag
        elif is_amulet: equipment_tag = amulet_tag
        elif is_robe: equipment_tag = robe_tag
        elif is_chest: equipment_tag = chest_tag
        elif is_pants: equipment_tag = pants_tag
        elif is_gloves: equipment_tag = gloves_tag
        elif is_shoes: equipment_tag = shoes_tag
        elif is_tail: equipment_tag = tail_tag
        elif is_shield: equipment_tag = shield_tag
        else: return record_full # Weird record, don't change anything
        prefix_subs = (equipment_tag + heavy_armor_addition,)
        prefix_format = self.chosen_format
        if u'%02d' in prefix_format: # Whether or not to show stats
            prefix_subs += (record.strength / 100,)
        return prefix_format % prefix_subs + record_full

    def _get_rename_params(self, record):
        body_flags = record.biped_flags
        return (record, (u'LH'[body_flags.heavyArmor]
                         if record.recType == b'ARMO' else u''),
                body_flags.head or body_flags.hair,
                body_flags.rightRing or body_flags.leftRing, body_flags.amulet,
                body_flags.upperBody and body_flags.lowerBody,
                body_flags.upperBody, body_flags.lowerBody, body_flags.hand,
                body_flags.foot, body_flags.tail, body_flags.shield)

#------------------------------------------------------------------------------
class NamesTweak_Body_Armor(_ANamesTweak_Body):
    tweak_read_classes = b'ARMO',
    tweak_name = _(u'Armor')
    tweak_tip = _(u'Rename armor to sort by type.')
    tweak_key = u'ARMO' # u'' is intended, not a record sig, ugh...
    tweak_choices = [(_(u'BL Leather Boots'),     u'%s '),
                     (_(u'BL. Leather Boots'),    u'%s. '),
                     (_(u'BL - Leather Boots'),   u'%s - '),
                     (_(u'(BL) Leather Boots'),   u'(%s) '),
                     (u'----', u'----'),
                     (_(u'BL02 Leather Boots'),   u'%s%02d '),
                     (_(u'BL02. Leather Boots'),  u'%s%02d. '),
                     (_(u'BL02 - Leather Boots'), u'%s%02d - '),
                     (_(u'(BL02) Leather Boots'), u'(%s%02d) ')]
    tweak_log_msg = _(u'Armor Pieces Renamed: %(total_changed)d')

#------------------------------------------------------------------------------
class NamesTweak_Body_Clothes(_ANamesTweak_Body):
    tweak_read_classes = b'CLOT',
    tweak_name = _(u'Clothes')
    tweak_tip = _(u'Rename clothes to sort by type.')
    tweak_key = u'CLOT' # u'' is intended, not a record sig, ugh...
    tweak_choices = [(_(u'P Grey Trousers'),   u'%s '),
                     (_(u'P. Grey Trousers'),  u'%s. '),
                     (_(u'P - Grey Trousers'), u'%s - '),
                     (_(u'(P) Grey Trousers'), u'(%s) ')]
    tweak_log_msg = _(u'Clothes Renamed: %(total_changed)d')

#------------------------------------------------------------------------------
_re_old_potion_label = re.compile(u'^(-|X) ', re.U)
_re_old_potion_end = re.compile(u' -$', re.U)

class NamesTweak_Potions(_AMgefNamesTweak):
    """Names tweaker for potions."""
    tweak_read_classes = b'ALCH',
    tweak_name = _(u'Potions')
    tweak_tip = _(u'Label potions to sort by type and effect.')
    tweak_key = u'ALCH' # u'' is intended, not a record sig, ugh...
    tweak_choices = [(_(u'XD Illness'),   u'%s '),
                     (_(u'XD. Illness'),  u'%s. '),
                     (_(u'XD - Illness'), u'%s - '),
                     (_(u'(XD) Illness'), u'(%s) ')]
    tweak_log_msg = _(u'Potions Renamed: %(total_changed)d')

    def _do_exec_rename(self, record, is_food):
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
        if is_food:
            return u'.' + wip_name
        else:
            effect_label = (u'X' if is_poison else u'') + u'ACDIMRU'[school]
            return self.chosen_format % effect_label + wip_name

    def _get_rename_params(self, record):
        return record, record.flags.isFood

#------------------------------------------------------------------------------
_re_old_magic_label = re.compile(u'^(\([ACDIMR]\d\)|\w{3,6}:) ', re.U)

class NamesTweak_Scrolls(_AMgefNamesTweak):
    """Names tweaker for scrolls."""
    tweak_read_classes = b'BOOK',
    tweak_name = _(u'Notes And Scrolls')
    tweak_tip = _(u'Mark notes and scrolls to sort separately from books.')
    tweak_key = u'scrolls'
    tweak_choices = [(_(u'~Fire Ball'),     u'~'),
                     (_(u'~D Fire Ball'),   u'~%s '),
                     (_(u'~D. Fire Ball'),  u'~%s. '),
                     (_(u'~D - Fire Ball'), u'~%s - '),
                     (_(u'~(D) Fire Ball'), u'~(%s) '),
                     (u'----', u'----'),
                     (_(u'.Fire Ball'),     u'.'),
                     (_(u'.D Fire Ball'),   u'.%s '),
                     (_(u'.D. Fire Ball'),  u'.%s. '),
                     (_(u'.D - Fire Ball'), u'.%s - '),
                     (_(u'.(D) Fire Ball'), u'.(%s) ')]
    tweak_log_msg = _(u'Notes and Scrolls Renamed: %(total_changed)d')
    _look_up_ench = None

    def _do_exec_rename(self, record, look_up_ench):
        # Magic label
        order_format = (u'~.', u'.~')[self.chosen_format[0] == u'~']
        magic_format = self.chosen_format[1:]
        wip_name = record.full
        rec_ench = record.enchantment
        is_enchanted = bool(rec_ench)
        if magic_format and is_enchanted:
            school = 6 # Default to 6 (U: unknown)
            enchantment = look_up_ench(rec_ench)
            if enchantment and enchantment.effects:
                school = self._get_effect_school(enchantment.effects[0])
            # Remove existing label
            wip_name = _re_old_magic_label.sub(u'', wip_name)
            wip_name = magic_format % u'ACDIMRU'[school] + wip_name
        # Ordering
        return order_format[is_enchanted] + wip_name

    def wants_record(self, record):
        return (record.flags.isScroll and not record.flags.isFixed and
                super(NamesTweak_Scrolls, self).wants_record(record))

    def prepare_for_tweaking(self, patch_file):
        super(NamesTweak_Scrolls, self).prepare_for_tweaking(patch_file)
        # HACK - and what an ugly one - we need a general API to express to the
        # BP that a patcher/tweak wants it to index all records for certain
        # record types in some central place (and NOT by forwarding all records
        # into the BP!)
        self._look_up_ench = id_ench = {}
        ench_factory = LoadFactory(False, by_sig=[b'ENCH'])
        for pl_path in patch_file.loadMods:
            ench_plugin = ModFile(patch_file.p_file_minfos[pl_path],
                                  ench_factory)
            ench_plugin.load(do_unpack=True)
            for record in ench_plugin.tops[b'ENCH'].getActiveRecords():
                id_ench[record.fid] = record

    def _get_rename_params(self, record):
        return record, lambda e: self._look_up_ench.get(e, 6) ##: 6?

#------------------------------------------------------------------------------
class NamesTweak_Spells(_AMgefNamesTweak):
    """Names tweaker for spells."""
    tweak_read_classes = b'SPEL',
    tweak_name = _(u'Spells')
    tweak_tip = _(u'Label spells to sort by school and level.')
    tweak_key = u'SPEL' # u'' is intended, not a record sig, ugh...
    tweak_choices = [(_(u'Fire Ball'),      u'NOTAGS'),
                     (u'----', u'----'),
                     (_(u'D Fire Ball'),    u'%s '),
                     (_(u'D. Fire Ball'),   u'%s. '),
                     (_(u'D - Fire Ball'),  u'%s - '),
                     (_(u'(D) Fire Ball'),  u'(%s) '),
                     (u'----', u'----'),
                     (_(u'D2 Fire Ball'),   u'%s%d '),
                     (_(u'D2. Fire Ball'),  u'%s%d. '),
                     (_(u'D2 - Fire Ball'), u'%s%d - '),
                     (_(u'(D2) Fire Ball'), u'(%s%d) ')]
    tweak_log_msg = _(u'Spells Renamed: %(total_changed)d')

    def wants_record(self, record):
        return record.spellType == 0 and super(
            NamesTweak_Spells, self).wants_record(record)

    def _do_exec_rename(self, record):
        school = 6 # Default to 6 (U: unknown)
        if record.effects:
            school = self._get_effect_school(record.effects[0])
        # Remove existing label
        wip_name = _re_old_magic_label.sub(u'', record.full)
        if u'%s' in self.chosen_format: # don't remove tags
            if u'%d' in self.chosen_format: # show level
                wip_name = self.chosen_format % (u'ACDIMRU'[school],
                                            record.level) + wip_name
            else:
                wip_name = self.chosen_format % u'ACDIMRU'[school] + wip_name
        return wip_name

#------------------------------------------------------------------------------
class NamesTweak_Weapons(_ANamesTweak):
    """Names tweaker for weapons and ammo."""
    tweak_read_classes = b'AMMO', b'WEAP',
    tweak_name = _(u'Weapons')
    tweak_tip = _(u'Label ammo and weapons to sort by type and damage.')
    tweak_key = u'WEAP' # u'' is intended, not a record sig, ugh...
    tweak_choices = [(_(u'B Iron Bow'),     u'%s '),
                     (_(u'B. Iron Bow'),    u'%s. '),
                     (_(u'B - Iron Bow'),   u'%s - '),
                     (_(u'(B) Iron Bow'),   u'(%s) '),
                     (u'----', u'----'),
                     (_(u'B08 Iron Bow'),   u'%s%02d '),
                     (_(u'B08. Iron Bow'),  u'%s%02d. '),
                     (_(u'B08 - Iron Bow'), u'%s%02d - '),
                     (_(u'(B08) Iron Bow'), u'(%s%02d) ')]

    def wants_record(self, record):
        return (record.full and (record.recType != b'AMMO'
                                 or record.full[0] not in _ignored_chars)
                and self._try_renaming(record))

    def _do_exec_rename(self, record):
        weapon_index = record.weaponType if record.recType  == b'WEAP' else 6
        format_subs = (u'CDEFGBA'[weapon_index],)
        if u'%02d' in self.chosen_format:
            format_subs += (record.damage,)
        return self.chosen_format % format_subs + record.full

#------------------------------------------------------------------------------
class _ATextReplacer(_ANamesTweak):
    """Base class for replacing any text via regular expressions."""
    ##: Move to game/*/constants, and boom, we have a cross-game text replacer!
    _match_replace_rpaths = {
        b'ALCH': (u'full', u'effects[i].scriptEffect?.full'),
        b'AMMO': (u'full',),
        b'APPA': (u'full',),
        b'ARMO': (u'full',),
        b'BOOK': (u'full', u'book_text'),
        b'BSGN': (u'full', u'text'),
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
        b'MGEF': (u'full', u'text'),
        b'MISC': (u'full',),
        b'NPC_': (u'full',),
        b'QUST': (u'full', u'stages[i].entries[i].text'),
        b'RACE': (u'full', u'text'),
        b'SGST': (u'full', u'effects[i].scriptEffect?.full'),
        b'SKIL': (u'description', u'apprentice', u'journeyman', u'expert',
                  u'master'),
        b'SLGM': (u'full',),
        b'SPEL': (u'full', u'effects[i].scriptEffect?.full'),
        b'WEAP': (u'full',),
    }
    tweak_read_classes = tuple(_match_replace_rpaths)
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
            for rsig, rpaths in self._match_replace_rpaths.iteritems()
        }

    def wants_record(self, record):
        def can_change(test_text):
            return any(m.search(test_text) for m in self._re_mapping)
        record_sig = record.recType
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
        for re_to_match, replacement in self._re_mapping.iteritems():
            replacement_sub = re_to_match.sub
            def exec_replacement(rec_val):
                if rec_val: # or blow up on re.sub
                    return replacement_sub(replacement, rec_val)
                return rec_val
            record_sig = record.recType
            for rp in self._match_replace_rpaths[record_sig]: # type: RecPath
                if rp.rp_exists(record):
                    rp.rp_map(record, exec_replacement)

    def finish_tweaking(self, patch_file):
        # These GMSTs don't exist in Oblivion.esm, so create them in the BP
        for extra_eid, extra_val in self._tr_extra_gmsts.iteritems():
            patch_file.new_gmst(extra_eid, extra_val)

#------------------------------------------------------------------------------
class NamesTweak_DwarvenToDwemer(_ATextReplacer):
    """Replaces 'dwarven' with 'dwemer' to better follow lore."""
    tweak_name = _(u'Lore Friendly Text: Dwarven -> Dwemer')
    tweak_tip = _(u'Replace any occurrences of the word "dwarf" or "dwarven" '
                  u'with "dwemer" to better follow lore.')
    tweak_key = u'Dwemer'
    tweak_choices = [(u'Lore Friendly Text: Dwarven -> Dwemer', u'Dwemer')]
    _tr_replacements = [(u'' r'\b(d|D)(?:warven|warf)\b', u'' r'\1wemer')]

#------------------------------------------------------------------------------
class NamesTweak_DwarfsToDwarves(_ATextReplacer):
    """Replaces 'dwarfs' with 'dwarves' for proper spelling."""
    tweak_name = _(u'Proper English Text: Dwarfs -> Dwarves')
    tweak_tip = _(u'Replace any occurrences of the word "dwarfs" with '
                  u'"dwarves" to better follow proper English.')
    tweak_key = u'Dwarfs'
    tweak_choices = [(u'Proper English Text: Dwarfs -> Dwarves', u'Dwarves')]
    _tr_replacements = [(u'' r'\b(d|D)warfs\b', u'' r'\1warves')]

#------------------------------------------------------------------------------
class NamesTweak_StaffsToStaves(_ATextReplacer):
    """Replaces 'staffs' with 'staves' for proper spelling."""
    tweak_name = _(u'Proper English Text: Staffs -> Staves')
    tweak_tip = _(u'Replace any occurrences of the word "staffs" with '
                  u'"staves" to better follow proper English.')
    tweak_key = u'Staffs'
    tweak_choices = [(u'Proper English Text: Staffs -> Staves', u'Staves')]
    _tr_replacements = [(u'' r'\b(s|S)taffs\b', u'' r'\1taves')]

#------------------------------------------------------------------------------
class NamesTweak_FatigueToStamina(_ATextReplacer):
    """Replaces 'fatigue' with 'stamina', similar to Skyrim."""
    tweak_name = _(u'Skyrim-style Text: Fatigue -> Stamina')
    tweak_tip = _(u'Replace any occurrences of the word "fatigue" with '
                  u'"stamina", similar to Skyrim.')
    tweak_key = u'FatigueToStamina'
    tweak_choices = [(u'1.0', u'1.0')]
    _tr_replacements = [(u'' r'\b(f|F)atigue\b', build_esub(u'$1(s)tamina'))]
    _tr_extra_gmsts = {u'sDerivedAttributeNameFatigue': u'Stamina'}

#------------------------------------------------------------------------------
def _mta_esub(first_suffix): # small helper to deduplicate that nonsense
    return build_esub(u'' r'\1%s $2(a)rcher' % first_suffix)

class NamesTweak_MarksmanToArchery(_ATextReplacer):
    """Replaces 'marksman' with 'archery', similar to Skyrim."""
    tweak_name = _(u'Skyrim-style Text: Marksman -> Archery')
    tweak_tip = _(u'Replace any occurrences of the word "marksman" with '
                  u'"archery", similar to Skyrim.')
    tweak_key = u'MarksmanToArchery'
    tweak_choices = [(u'1.0', u'1.0')]
    _tr_replacements = [
        (u'' r'\b(t|T)he (m|M)arksman\b', _mta_esub(u'he')),
        (u'' r'\b(a|A) (m|M)arksman\b', _mta_esub(u'n')),
        # These four work around vanilla Oblivion records, ugh...
        (u'' r'\b(a|A)pprentice (m|M)arksman\b', _mta_esub(u'pprentice')),
        (u'' r'\b(j|J)ourneyman (m|M)arksman\b', _mta_esub(u'ourneyman')),
        (u'' r'\b(e|E)xpert (m|M)arksman\b', _mta_esub(u'xpert')),
        (u'' r'\b(m|M)aster (m|M)arksman\b', _mta_esub(u'aster')),
        (u'' r'\b(m|M)arksman\b', build_esub(u'$1(a)rchery')),
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
        (u'' r'\b(s|S)ecurity\b', build_esub(u'$1(l)ockpicking'))
    ]
    _tr_extra_gmsts = {u'sSkillNameSecurity': u'Lockpicking',
                       u'sSkillDescSecurity': u'Lockpicking Description'}

#------------------------------------------------------------------------------
class TweakNamesPatcher(MultiTweaker):
    """Tweaks record full names in various ways."""
    _tweak_classes = {
        NamesTweak_BodyTags, NamesTweak_Body_Armor, NamesTweak_Body_Clothes,
        NamesTweak_Potions, NamesTweak_Scrolls, NamesTweak_Spells,
        NamesTweak_Weapons, NamesTweak_DwarvenToDwemer,
        NamesTweak_DwarfsToDwarves, NamesTweak_StaffsToStaves,
        NamesTweak_FatigueToStamina, NamesTweak_MarksmanToArchery,
        NamesTweak_SecurityToLockpicking,
    }

    def __init__(self, p_name, p_file, enabled_tweaks):
        super(TweakNamesPatcher, self).__init__(p_name, p_file, enabled_tweaks)
        for names_tweak in enabled_tweaks[1:]:
            # Always the first one if it's enabled, so this is safe
            if isinstance(names_tweak, NamesTweak_BodyTags):
                p_file.bodyTags = names_tweak.choiceValues[
                    names_tweak.chosen][0]
            elif isinstance(names_tweak, _ANamesTweak_Body):
                names_tweak._tweak_body_tags = p_file.bodyTags
