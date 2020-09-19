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
to the Names Multitweaker - as well as the NamesTweaker itself."""

from __future__ import division
import re
# Internal
from ...bolt import RecPath
from ...brec import MreRecord # yuck, see usage below
from ...exception import AbstractError
from ...parsers import LoadFactory, ModFile # yuck, see usage below
from ...patcher.base import AMultiTweakItem, AMultiTweaker
from ...patcher.patchers.base import MultiTweakItem, CBash_MultiTweakItem
from ...patcher.patchers.base import MultiTweaker, CBash_MultiTweaker

_ignored_chars=frozenset(u'+-=.()[]')

class _ANamesTweak(AMultiTweakItem):
    """Shared code of PBash/CBash names tweaks and hasty abstraction over
    CBash/PBash differences to allow moving duplicate code into _A classes."""
    tweak_log_msg = _(u'Items Renamed: %(total_changed)d')

    @property
    def chosen_format(self): return self.choiceValues[self.chosen][0]

    def tweak_record(self, record):
        record.full = self._exec_rename(record)

    def _do_exec_rename(self, *placeholder):
        """Does the actual renaming, returning the new name as its reuslt.
        Should be CBash/PBash-agnostic, and take any information it needs as
        parameters - see overrides for examples."""
        raise AbstractError(u'_do_exec_rename not implemented')

    def _exec_rename(self, record):
        """Convenience method that calls _do_exec_rename, passing the correct
        CBash/PBash record attributes in."""
        return self._do_exec_rename(*self._get_rename_params(record))

    def _get_effect_school(self, magic_effect):
        """Returns the school of the specified MGEF."""
        raise AbstractError(u'_get_effect_school not implemented')

    def _get_record_signature(self, record):
        """Returns the record signature of the specified record."""
        raise AbstractError(u'_get_record_signature not implemented')

    def _get_rename_params(self, record):
        """Returns the parameters that should be passed to _do_exec_rename.
        Passes only the record itself by default."""
        return (record,)

    def _has_mgefs_indexed(self):
        """Returns a truthy value if MGEFs have been indexed already. Different
        implementations are necessary for CBash and PBash."""
        raise AbstractError(u'_has_mgefs_indexed not implemented')

    def _is_effect_hostile(self, magic_effect):
        """Returns a truthy value if the specified MGEF is nonhostile."""
        raise AbstractError(u'_is_effect_nonhostile not implemented')

    def _try_renaming(self, record):
        """Checks if renaming via _exec_rename would change the specified
        record's name."""
        return record.full != self._exec_rename(record)

class _PNamesTweak(_ANamesTweak, MultiTweakItem):
    """Shared code of PBash names tweaks."""
    _tweak_mgef_hostiles = set()
    _tweak_mgef_school = {}

    def prepare_for_tweaking(self, patch_file):
        # These are cached, so fine to call for all tweaks
        self._tweak_mgef_hostiles = patch_file.getMgefHostiles()
        self._tweak_mgef_school = patch_file.getMgefSchool()

    def _get_effect_school(self, magic_effect):
        return (magic_effect.scriptEffect.school if magic_effect.scriptEffect
                else self._tweak_mgef_school.get(magic_effect.name, 6))

    def _get_record_signature(self, record):
        return record.recType

    def _has_mgefs_indexed(self):
        return self._tweak_mgef_hostiles

    def _is_effect_hostile(self, magic_effect):
        return (magic_effect.scriptEffect.flags.hostile
                if magic_effect.scriptEffect
                else magic_effect.name in self._tweak_mgef_hostiles)

class _CNamesTweak(_ANamesTweak, CBash_MultiTweakItem):
    """Shared code of CBash names tweaks."""
    def _get_effect_school(self, magic_effect):
         return (magic_effect.schoolType if magic_effect.script
                 else self.patchFile.mgef_school.get(magic_effect.name, 6))

    def _get_record_signature(self, record):
        return record._Type

    def _has_mgefs_indexed(self):
        return self.patchFile.hostileEffects

    def _is_effect_hostile(self, magic_effect):
        return (magic_effect.IsHostile if magic_effect.script
                else magic_effect.name in self.patchFile.hostileEffects)

class _AMgefNamesTweak(_ANamesTweak):
    """Shared code of a few names tweaks that handle MGEFs."""
    def wants_record(self, record):
        # Once we have MGEFs indexed, we can try renaming to check more
        # thoroughly (i.e. during the buildPatch/apply phase)
        return (record.full and not self._has_mgefs_indexed() or
                self._try_renaming(record))

# Patchers: 30 ----------------------------------------------------------------
class _ANamesTweak_BodyTags(AMultiTweakItem): # not _ANamesTweak, no classes!
    """Only exists to change _PFile.bodyTags - see _ANamesTweaker.__init__ for
    the implementation."""
    tweak_name = _(u'Body Part Codes')
    tweak_tip = _(u'Sets body part codes used by Armor/Clothes name tweaks. '
                  u'A: Amulet, R: Ring, etc.')
    tweak_key = u'bodyTags'
    tweak_choices = [(u'ARGHTCCPBS', u'ARGHTCCPBS'),
                     (u'ABGHINOPSL', u'ABGHINOPSL')]

##: This would be better handled with some sort of settings menu for the BP
class NamesTweak_BodyTags(_ANamesTweak_BodyTags, _PNamesTweak):
    def tweak_log(self, log, count): pass # 'internal' tweak, log nothing
class CBash_NamesTweak_BodyTags(_ANamesTweak_BodyTags,
                                CBash_MultiTweakItem): pass

#------------------------------------------------------------------------------
class _ANamesTweak_Body(_ANamesTweak):
    """Shared code of CBash/PBash body names tweaks."""
    _tweak_body_tags = u'' # set in _ANamesTweaker.__init__

    def wants_record(self, record):
        old_full = record.full
        return (old_full and old_full[0] not in _ignored_chars and
                self._try_renaming(record))

    def _do_exec_rename(self, record, heavy_armor_addition, is_head, is_ring,
                        is_amulet, is_robe, is_chest, is_pants, is_gloves,
                        is_shoes, is_tail, is_shield):
        curr_name = record.full
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
        else: return curr_name # Weird record, don't change anything
        prefix_subs = (equipment_tag + heavy_armor_addition,)
        prefix_format = self.chosen_format
        if u'%02d' in prefix_format: # Whether or not to show stats
            prefix_subs += (record.strength / 100,)
        return prefix_format % prefix_subs + curr_name

class _PNamesTweak_Body(_ANamesTweak_Body, _PNamesTweak):
    """Shared code of PBash body names tweaks."""
    def wants_record(self, record):
        return not self._is_nonplayable(record) and super(
            _PNamesTweak_Body, self).wants_record(record)

    def _get_rename_params(self, record):
        body_flags = record.biped_flags
        return (record, (u'LH'[body_flags.heavyArmor]
                         if record.recType == b'ARMO' else u''),
                body_flags.head or body_flags.hair,
                body_flags.rightRing or body_flags.leftRing, body_flags.amulet,
                body_flags.upperBody or body_flags.lowerBody,
                body_flags.upperBody, body_flags.lowerBody, body_flags.hand,
                body_flags.foot, body_flags.tail, body_flags.shield)

class _CNamesTweak_Body(_ANamesTweak_Body, CBash_MultiTweakItem):
    """Shared code of CBash body names tweaks."""
    def wants_record(self, record):
        return record.IsPlayable and super(
            _CNamesTweak_Body, self).wants_record(record)

    def _get_rename_params(self, record):
        return (record, (u'LH'[record.IsHeavyArmor]
                         if record._Type == b'ARMO' else u''),
                record.IsHead or record.IsHair,
                record.IsRightRing or record.IsLeftRing, record.IsAmulet,
                record.IsUpperBody or record.IsLowerBody, record.IsUpperBody,
                record.IsLowerBody, record.IsHand, record.IsFoot,
                record.IsTail, record.IsShield)

#------------------------------------------------------------------------------
class _AArmoNamesTweak(_ANamesTweak_Body):
    """Shared code of CBash/PBash armor names tweaks."""
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

class NamesTweak_Body_Armor(_AArmoNamesTweak, _PNamesTweak_Body): pass
class CBash_NamesTweak_Body_Armor(_AArmoNamesTweak, _CNamesTweak_Body): pass

#------------------------------------------------------------------------------
class _AClotNamesTweak(_ANamesTweak_Body):
    """Shared code of CBash/PBash clothes names tweaks."""
    tweak_read_classes = b'CLOT',
    tweak_name = _(u'Clothes')
    tweak_tip = _(u'Rename clothes to sort by type.')
    tweak_key = u'CLOT' # u'' is intended, not a record sig, ugh...
    tweak_choices = [(_(u'P Grey Trousers'),   u'%s '),
                     (_(u'P. Grey Trousers'),  u'%s. '),
                     (_(u'P - Grey Trousers'), u'%s - '),
                     (_(u'(P) Grey Trousers'), u'(%s) ')]
    tweak_log_msg = _(u'Clothes Renamed: %(total_changed)d')

class NamesTweak_Body_Clothes(_AClotNamesTweak, _PNamesTweak_Body): pass
class CBash_NamesTweak_Body_Clothes(_AClotNamesTweak, _CNamesTweak_Body): pass

#------------------------------------------------------------------------------
_re_old_potion_label = re.compile(u'^(-|X) ', re.U)
_re_old_potion_end = re.compile(u' -$', re.U)

class _ANamesTweak_Potions(_AMgefNamesTweak):
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

class NamesTweak_Potions(_ANamesTweak_Potions, _PNamesTweak):
    def _get_rename_params(self, record):
        return record, record.flags.isFood

class CBash_NamesTweak_Potions(_ANamesTweak_Potions, _CNamesTweak):
    def _get_rename_params(self, record):
        return record, record.IsFood

#------------------------------------------------------------------------------
_re_old_magic_label = re.compile(u'^(\([ACDIMR]\d\)|\w{3,6}:) ', re.U)

class _ANamesTweak_Scrolls(_AMgefNamesTweak):
    """Names tweaker for scrolls."""
    tweak_read_classes = b'BOOK',
    tweak_name = _(u'Notes and Scrolls')
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

class NamesTweak_Scrolls(_ANamesTweak_Scrolls, _PNamesTweak):
    _look_up_ench = None

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
        ench_factory = LoadFactory(False, MreRecord.type_class[b'ENCH'])
        for pl_path in patch_file.loadMods:
            ench_plugin = ModFile(patch_file.p_file_minfos[pl_path],
                                  ench_factory)
            ench_plugin.load(do_unpack=True)
            for record in ench_plugin.ENCH.getActiveRecords():
                id_ench[record.fid] = record

    def finish_tweaking(self, patch_file):
        # Clean this up ##: not sure if actually needed?
        self._look_up_ench = None

    def _get_rename_params(self, record):
        return record, lambda e: self._look_up_ench.get(e, 6)

class CBash_NamesTweak_Scrolls(_ANamesTweak_Scrolls, _CNamesTweak):
    def wants_record(self, record):
        return (record.IsScroll and not record.IsFixed and super(
            CBash_NamesTweak_Scrolls, self).wants_record(record))

    def _get_rename_params(self, record):
        return (record, lambda e: (
                self.patchFile.Current.LookupRecords(e) or [None])[0])

#------------------------------------------------------------------------------
class _ANamesTweak_Spells(_AMgefNamesTweak):
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
            _ANamesTweak_Spells, self).wants_record(record)

    def _do_exec_rename(self, record):
        school = 6 # Default to 6 (U: unknown)
        if record.effects:
            school = self._get_effect_school(record.effects[0])
        # Remove existing label
        wip_name = _re_old_magic_label.sub(u'', record.full or u'')
        if u'%s' in self.chosen_format: # don't remove tags
            if u'%d' in self.chosen_format: # show level
                wip_name = self.chosen_format % (u'ACDIMRU'[school],
                                            record.level) + wip_name
            else:
                wip_name = self.chosen_format % u'ACDIMRU'[school] + wip_name
        return wip_name

class NamesTweak_Spells(_ANamesTweak_Spells, _PNamesTweak): pass
class CBash_NamesTweak_Spells(_ANamesTweak_Spells, _CNamesTweak): pass

#------------------------------------------------------------------------------
class _ANamesTweak_Weapons(_ANamesTweak):
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
        return (record.full and (self._get_record_signature(record) != b'AMMO'
                                 or record.full[0] not in _ignored_chars)
                and self._try_renaming(record))

    def _do_exec_rename(self, record):
        weapon_index = record.weaponType if self._get_record_signature(
            record) == b'WEAP' else 6
        format_subs = (u'CDEFGBA'[weapon_index],)
        if u'%02d' in self.chosen_format:
            format_subs += (record.damage,)
        return self.chosen_format % format_subs + record.full

class NamesTweak_Weapons(_ANamesTweak_Weapons, _PNamesTweak): pass
class CBash_NamesTweak_Weapons(_ANamesTweak_Weapons, _CNamesTweak): pass

#------------------------------------------------------------------------------
class _ATextReplacer(_ANamesTweak):
    """Base class for replacing any text via regular expressions."""
    ##: Move to game/*/constants, and boom, we have a cross-game text replacer!
    _match_replace_rpaths = {
        b'ALCH': (u'full', u'effects[i].scriptEffect?.full'),
        b'AMMO': (u'full',),
        b'APPA': (u'full',),
        b'ARMO': (u'full',),
        b'BOOK': (u'full', u'text'),
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
    # Maps regexes we want to match to replacement strings. Those replacements
    # will be passed to re.sub, so they may use the results of regex groups.
    _tr_replacements = {}

    def __init__(self):
        super(_ATextReplacer, self).__init__()
        self._re_mapping = {re.compile(m): r for m, r in
                            self._tr_replacements.iteritems()}
        # Convert the match/replace strings to record paths
        self._match_replace_rpaths = {
            rsig: tuple([RecPath(r) for r in rpaths])
            for rsig, rpaths in self._match_replace_rpaths.iteritems()
        }

    def wants_record(self, record):
        def can_change(test_text):
            return any(m.search(test_text) for m in self._re_mapping)
        record_sig = self._get_record_signature(record)
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
            record_sig = self._get_record_signature(record)
            for rp in self._match_replace_rpaths[record_sig]: # type: RecPath
                if rp.rp_exists(record):
                    rp.rp_map(record, exec_replacement)

class _ATextReplacer_P(_ATextReplacer, _PNamesTweak): pass
class _ATextReplacer_C(_ATextReplacer, _CNamesTweak):
    tweak_read_classes = (b'CELLS',) + _ATextReplacer.tweak_read_classes
    _match_replace_rpaths = _ATextReplacer._match_replace_rpaths.copy()
    _match_replace_rpaths.update({
        b'ALCH': (u'full', u'effects[i].full'),
        b'CELL': (u'full',),
        b'ENCH': (u'full', u'effects[i].full'),
        b'INGR': (u'full', u'effects[i].full'),
        b'SGST': (u'full', u'effects[i].full'),
        b'SPEL': (u'full', u'effects[i].full'),
    })

#------------------------------------------------------------------------------
class _ATR_DwarvenToDwemer(_ATextReplacer):
    """Replaces 'dwarven' with 'dwemer' to better follow lore."""
    tweak_name = _(u'Lore Friendly Text: Dwarven -> Dwemer')
    tweak_tip = _(u'Replace any occurrences of the word "dwarf" or "dwarven" '
                  u'with "dwemer" to better follow lore.')
    tweak_key = u'Dwemer'
    tweak_choices = [(u'Lore Friendly Text: Dwarven -> Dwemer', u'Dwemer')]
    _tr_replacements = {u'' r'\b(d|D)(?:warven|warf)\b': u'' r'\1wemer'}

class NamesTweak_DwarvenToDwemer(_ATR_DwarvenToDwemer, _ATextReplacer_P): pass
class CBash_NamesTweak_DwarvenToDwemer(_ATR_DwarvenToDwemer,
    _ATextReplacer_C): pass

#------------------------------------------------------------------------------
class _ATR_DwarfsToDwarves(_ATextReplacer):
    """Replaces 'dwarfs' with 'dwarves' for proper spelling."""
    tweak_name = _(u'Proper English Text: Dwarfs -> Dwarves')
    tweak_tip = _(u'Replace any occurrences of the word "dwarfs" with '
                  u'"dwarves" to better follow proper English.')
    tweak_key = u'Dwarfs'
    tweak_choices = [(u'Proper English Text: Dwarfs -> Dwarves', u'Dwarves')]
    _tr_replacements = {u'' r'\b(d|D)(?:warfs)\b': u'' r'\1warves'}

class NamesTweak_DwarfsToDwarves(_ATR_DwarfsToDwarves, _ATextReplacer_P): pass
class CBash_NamesTweak_DwarfsToDwarves(_ATR_DwarfsToDwarves,
    _ATextReplacer_C): pass

#------------------------------------------------------------------------------
class _ATR_StaffsToStaves(_ATextReplacer):
    """Replaces 'staffs' with 'staves' for proper spelling."""
    tweak_name = _(u'Proper English Text: Staffs -> Staves')
    tweak_tip = _(u'Replace any occurrences of the word "staffs" with '
                  u'"staves" to better follow proper English.')
    tweak_key = u'Staffs'
    tweak_choices = [(u'Proper English Text: Staffs -> Staves', u'Staves')]
    _tr_replacements = {u'' r'\b(s|S)(?:taffs)\b': u'' r'\1taves'}

class NamesTweak_StaffsToStaves(_ATR_StaffsToStaves, _ATextReplacer_P): pass
class CBash_NamesTweak_StaffsToStaves(_ATR_StaffsToStaves,
    _ATextReplacer_C): pass

#------------------------------------------------------------------------------
class NamesTweak_FatigueToStamina(_ATextReplacer_P):
    """Replaces 'fatigue' with 'stamina', similar to Skyrim."""
    tweak_name = _(u'Skyrim-style Text: Fatigue -> Stamina')
    tweak_tip = _(u'Replace any occurrences of the word "fatigue" with '
                  u'"stamina", similar to Skyrim.')
    tweak_key = u'FatigueToStamina'
    tweak_choices = [(u'1.0', u'1.0')]
    _tr_replacements = {u'' r'\bfatigue\b': u'stamina',
                        u'' r'\bFatigue\b': u'Stamina'}

    def finish_tweaking(self, patch_file):
        # This GMST doesn't exist in Oblivion.esm, so just create it in the BP
        patch_file.new_gmst(u'sDerivedAttributeNameFatigue', u'Stamina')

#------------------------------------------------------------------------------
class _ANamesTweaker(AMultiTweaker):
    """Tweaks record full names in various ways."""
    scanOrder = 32
    editOrder = 32
    _body_tags_tweak = None # override in implementations

    def __init__(self, p_name, p_file, enabled_tweaks):
        super(_ANamesTweaker, self).__init__(p_name, p_file, enabled_tweaks)
        for names_tweak in enabled_tweaks:
            # Always the first one if it's enabled, so this is safe
            if isinstance(names_tweak, _ANamesTweak_BodyTags):
                p_file.bodyTags = names_tweak.choiceValues[
                    names_tweak.chosen][0]
            elif isinstance(names_tweak, _ANamesTweak_Body):
                names_tweak._tweak_body_tags = p_file.bodyTags

    @classmethod
    def tweak_instances(cls):
        return [cls._body_tags_tweak()] + super( # always first, see __init__
            _ANamesTweaker, cls).tweak_instances()

class NamesTweaker(_ANamesTweaker, MultiTweaker):
    _tweak_classes = [NamesTweak_Body_Armor, NamesTweak_Body_Clothes,
                      NamesTweak_Potions, NamesTweak_Scrolls,
                      NamesTweak_Spells, NamesTweak_Weapons,
                      NamesTweak_DwarvenToDwemer, NamesTweak_DwarfsToDwarves,
                      NamesTweak_StaffsToStaves, NamesTweak_FatigueToStamina]
    _body_tags_tweak = NamesTweak_BodyTags

class CBash_NamesTweaker(_ANamesTweaker,CBash_MultiTweaker):
    _tweak_classes = [
        CBash_NamesTweak_Body_Armor, CBash_NamesTweak_Body_Clothes,
        CBash_NamesTweak_Potions, CBash_NamesTweak_Scrolls,
        CBash_NamesTweak_Spells, CBash_NamesTweak_Weapons,
        CBash_NamesTweak_DwarvenToDwemer, CBash_NamesTweak_DwarfsToDwarves,
        CBash_NamesTweak_StaffsToStaves]
    _body_tags_tweak = CBash_NamesTweak_BodyTags

    def __init__(self, p_name, p_file, enabled_tweaks):
        super(CBash_NamesTweaker, self).__init__(p_name, p_file,
            enabled_tweaks)
        # Potions, scrolls and spells names tweaks need MGEFs to be indexed -
        # PBash does this JIT, CBash needs this to be specified when
        # constructing patchers
        p_file.indexMGEFs = True
