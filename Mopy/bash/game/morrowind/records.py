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
"""This module contains the Morrowind record classes. Also contains records
and subrecords used for the saves - see MorrowindSaveHeader for more
information."""

from ...bolt import Flags, flag
from ...brec import AMreCell, AMreHeader, AMreLeveledList, AutoFixedString, \
    FixedString, MelArray, MelBase, MelBookText, MelColor, MelColorO, \
    MelCounter, MelDescription, MelEffectsTes3, MelFixedString, MelFloat, \
    MelGroup, MelGroups, MelIcons, MelLists, MelLLChanceNoneTes3, \
    MelLLFlagsTes3, MelNull, MelRecord, MelRef3D, MelRefScale, MelSequential, \
    MelSet, MelSInt32, MelString, MelStrings, MelStruct, MelTruncatedStruct, \
    MelUInt8, MelUInt16, MelUInt32, MelUInt32Flags, MelUnion, SaveDecider, \
    SizeDecider, color_attrs, color3_attrs, position_attrs, rotation_attrs

#------------------------------------------------------------------------------
# Record Elements -------------------------------------------------------------
#------------------------------------------------------------------------------
class MelModel(MelGroup):
    """Represents a model subrecord."""
    def __init__(self):
        super().__init__('model', MelString(b'MODL', 'modPath'))

#------------------------------------------------------------------------------
class MelMWId(MelString): # needed everywhere, so put it early
    """Wraps MelString to define a common NAME handler."""
    def __init__(self):
        super().__init__(b'NAME', 'mw_id')

#------------------------------------------------------------------------------
class MelAidt(MelStruct):
    """Handles the CREA/NPC_ subrecord AIDT (AI Data)."""
    class _ServiceFlags(Flags):
        ai_weapon: bool
        ai_armor: bool
        ai_clothing: bool
        ai_books: bool
        ai_ingredient: bool
        ai_picks: bool
        ai_probes: bool
        ai_lights: bool
        ai_apparatus: bool
        ai_repair_items: bool
        ai_misc: bool
        ai_spells: bool
        ai_magic_items: bool
        ai_potions: bool
        ai_training: bool
        ai_spellmaking: bool
        ai_enchanting: bool
        ai_repair: bool

    def __init__(self):
        super().__init__(b'AIDT', ['B', 's', '3B', '3s', 'I'], 'ai_hello',
            'ai_unknown1', 'ai_fight', 'ai_flee', 'ai_alarm', 'ai_unknown2',
            (self._ServiceFlags, 'ai_service_flags'))

#------------------------------------------------------------------------------
class _MelAIAccompanyPackage(MelStruct):
    """Deduplicated from AI_E and AI_F (see below)."""
    def __init__(self, ai_package_sig):
        super().__init__(ai_package_sig,
            ['3f', 'H', '32s', 'B', 's'], 'dest_x', 'dest_y', 'dest_z',
            'package_duration', (FixedString(32), 'package_id'),
            'unknown_marker', 'unused1')

class MelAIPackagesTes3(MelGroups):
    """Handles the AI_* and CNDT subrecords, which have the additional
    complication that they may occur in any order."""
    def __init__(self):
        super().__init__('ai_packages',
            MelUnion({
                b'AI_A': MelStruct(b'AI_A', ['32s', 'B'],
                    (FixedString(32), 'package_name'), 'unknown_marker'),
                b'AI_E': _MelAIAccompanyPackage(b'AI_E'),
                b'AI_F': _MelAIAccompanyPackage(b'AI_F'),
                b'AI_T': MelStruct(b'AI_T', ['3f', 'B', '3s'], 'dest_x',
                    'dest_y', 'dest_z', 'unknown_marker', 'unused1'),
                b'AI_W': MelStruct(b'AI_W', ['2H', '10B'], 'wanter_distance',
                    'wanter_duration', 'time_of_day', 'idle_1', 'idle_2',
                    'idle_3', 'idle_4', 'idle_5', 'idle_6', 'idle_7',
                    'idle_8', 'unknown_marker'),
            }),
            # Only present for AI_E and AI_F, but won't be dumped unless
            # already present, so that's fine
            MelString(b'CNDT', 'cell_name'),
        )

#------------------------------------------------------------------------------
class MelArmorData(MelGroups):
    """Handles the INDX, BNAM and CNAM subrecords shared by ARMO and CLOT."""
    def __init__(self):
        super(MelArmorData, self).__init__(u'armor_data',
            MelUInt8(b'INDX', u'biped_object'),
            MelString(b'BNAM', u'armor_name_male'),
            MelString(b'CNAM', u'armor_name_female'),
        )

#------------------------------------------------------------------------------
class MelDestinations(MelGroups):
    """Handles the common DODT/DNAM subrecords."""
    def __init__(self):
        super().__init__('cell_travel_destinations',
            MelStruct(b'DODT', ['6f'], *position_attrs('destination'),
                *rotation_attrs('destination')),
            MelString(b'DNAM', 'destination_cell_name'),
        )

#------------------------------------------------------------------------------
class MelEnchantmentTes3(MelString):
    """Handles ENAM, Morrowind's version of EITM."""
    def __init__(self):
        super().__init__(b'ENAM', 'enchantment')

#------------------------------------------------------------------------------
class MelFullTes3(MelString):
    """Handles FNAM, Morrowind's version of FULL."""
    def __init__(self):
        super().__init__(b'FNAM', 'full')

#------------------------------------------------------------------------------
class MelIconTes3(MelIcons):
    """Handles ITEX, Morrowind's version of ICON."""
    def __init__(self):
        super().__init__(icon_sig=b'ITEX', mico_attr='')

#------------------------------------------------------------------------------
class MelItems(MelGroups):
    """Wraps MelGroups for the common task of defining a list of items."""
    def __init__(self):
        super(MelItems, self).__init__(u'items',
            MelStruct(b'NPCO', [u'I', u'32s'], u'count', (FixedString(32), u'item')),
        )

#------------------------------------------------------------------------------
class MelLLItemsTes3(MelSequential):
    """Handles the leveled list INDX/INAM/INTV subrecords."""
    def __init__(self, *, item_sig: bytes):
        super().__init__(
            MelCounter(MelUInt32(b'INDX', 'entry_count'), counts='entries'),
            # Bad names to mirror the other games (needed by AMreLeveledList)
            MelGroups('entries',
                MelString(item_sig, 'listId'),
                MelUInt16(b'INTV', 'level'),
            ),
        )

#------------------------------------------------------------------------------
class MelReference(MelSequential):
    """Defines a single 'reference', which is Morrowind's version of REFRs in
    later games."""
    def __init__(self):
        super(MelReference, self).__init__(
            MelUInt32(b'FRMR', u'object_index'),
            MelMWId(),
            MelBase(b'UNAM', u'ref_blocked_marker'),
            MelRefScale(),
            MelString(b'ANAM', u'ref_owner'),
            MelString(b'BNAM', u'global_variable'),
            MelString(b'CNAM', u'ref_faction'),
            MelSInt32(b'INDX', u'ref_faction_rank'),
            MelString(b'XSOL', u'ref_soul'),
            MelFloat(b'XCHG', u'enchantment_charge'),
            ##: INTV should have a decider - uint32 or float, depending on
            # object type
            MelBase(b'INTV', u'remaining_usage'),
            MelUInt32(b'NAM9', u'gold_value'),
            MelDestinations(),
            MelUInt32(b'FLTV', u'lock_level'),
            MelString(b'KNAM', u'key_name'),
            MelString(b'TNAM', u'trap_name'),
            MelBase(b'ZNAM', u'ref_disabled_marker'),
            MelRef3D(),
        )

#------------------------------------------------------------------------------
class MelSavesOnly(MelSequential):
    """Record element that only loads contents if the input file is a save
    file."""
    def __init__(self, *elements):
        super(MelSavesOnly, self).__init__(*(MelUnion({
            True: element,
            False: MelNull(next(iter(element.signatures))),
        }, decider=SaveDecider()) for element in elements))

#------------------------------------------------------------------------------
class MelScriptId(MelString):
    """Handles the common SCRI subrecord."""
    def __init__(self):
        super(MelScriptId, self).__init__(b'SCRI', u'script_id'),

#------------------------------------------------------------------------------
class MelSpellsTes3(MelGroups):
    """Handles NPCS, Morrowind's version of SPLO."""
    def __init__(self):
        super().__init__('spells', MelFixedString(b'NPCS', 'spell_id', 32))

#------------------------------------------------------------------------------
# Shared (plugins + saves) record classes -------------------------------------
#------------------------------------------------------------------------------
class MreTes3(AMreHeader):
    """TES3 Record. File header."""
    rec_sig = b'TES3'
    _post_masters_sigs = {b'GMDT', b'SCRD', b'SCRS'}

    melSet = MelSet(
        MelStruct(b'HEDR', ['f', 'I', '32s', '256s', 'I'], ('version', 1.3),
            'esp_flags', (AutoFixedString(32), 'author_pstr'),
            (AutoFixedString(256), 'description_pstr'), 'numRecords'),
        AMreHeader.MelMasterNames(),
        MelSavesOnly(
            # Wrye Mash calls unknown1 'day', but that seems incorrect?
            MelStruct(b'GMDT', [u'6f', u'64s', u'f', u'32s'], u'pc_curr_health',
                u'pc_max_health', u'unknown1', u'unknown2', u'unknown3',
                u'unknown4', (FixedString(64), u'curr_cell'),
                u'unknown5', (AutoFixedString(32), u'pc_name')),
            MelBase(b'SCRD', u'unknown_scrd'), # likely screenshot-related
            MelArray(u'screenshot_data',
                # Yes, the correct order is bgra
                MelStruct(b'SCRS', [u'4B'], u'blue', u'green', u'red', u'alpha'),
            ),
        ),
    )

#------------------------------------------------------------------------------
# Plugins-only record classes -------------------------------------------------
#------------------------------------------------------------------------------
class MreActi(MelRecord):
    """Activator."""
    rec_sig = b'ACTI'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelFullTes3(),
        MelScriptId(),
    )

#------------------------------------------------------------------------------
class MreAlch(MelRecord):
    """Potion."""
    rec_sig = b'ALCH'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelString(b'TEXT', u'inventory_icon'),
        MelScriptId(),
        MelFullTes3(),
        MelStruct(b'ALDT', [u'f', u'2I'], u'potion_weight', u'potion_value',
            u'potion_auto_calc'),
        MelEffectsTes3(),
    )

#------------------------------------------------------------------------------
class MreAppa(MelRecord):
    """Alchemical Apparatus."""
    rec_sig = b'APPA'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelFullTes3(),
        MelScriptId(),
        MelStruct(b'AADT', [u'I', u'2f', u'I'], u'appa_type', u'appa_quality',
            u'appa_weight', u'appa_value'),
        MelIconTes3(),
    )

#------------------------------------------------------------------------------
class MreArmo(MelRecord):
    """Armor."""
    rec_sig = b'ARMO'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelFullTes3(),
        MelScriptId(),
        MelStruct(b'AODT', [u'I', u'f', u'4I'], u'armo_type', u'armo_weight',
            u'armo_value', u'armo_health', u'enchant_points', u'armor_rating'),
        MelIconTes3(),
        MelArmorData(),
        MelEnchantmentTes3(),
    )

#------------------------------------------------------------------------------
class MreBody(MelRecord):
    """Body Parts."""
    rec_sig = b'BODY'

    class _part_flags(Flags):
        part_female: bool
        part_playable: bool

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelString(b'FNAM', u'race_name'),
        MelStruct(b'BYDT', [u'4B'], u'part_index', u'part_vampire',
            (_part_flags, u'part_flags'), u'part_type'),
    )

#------------------------------------------------------------------------------
class MreBook(MelRecord):
    """Book."""
    rec_sig = b'BOOK'

    class _scroll_flags(Flags):
        is_scroll: bool

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelFullTes3(),
        MelStruct(b'BKDT', [u'f', u'2I', u'i', u'I'], u'book_weight', u'book_value',
            (_scroll_flags, u'scroll_flags'), u'skill_id', u'enchant_points'),
        MelScriptId(),
        MelIconTes3(),
        MelBookText(b'TEXT'),
        MelEnchantmentTes3(),
    )

#------------------------------------------------------------------------------
class MreBsgn(MelRecord):
    """Birthsign."""
    rec_sig = b'BSGN'

    melSet = MelSet(
        MelMWId(),
        MelFullTes3(),
        MelSpellsTes3(),
        MelString(b'TNAM', u'texture_filename'),
        MelDescription(),
    )

#------------------------------------------------------------------------------
class MreCell(AMreCell):
    """Cell."""
    # TODO ref_types and co?

    class _cell_flags(Flags):
        is_interior_cell: bool = flag(0)
        has_water: bool = flag(1)
        illegal_to_sleep_here: bool = flag(2)
        behave_like_exterior: bool = flag(7)

    melSet = MelSet(
        MelMWId(),
        MelStruct(b'DATA', [u'3I'], (_cell_flags, u'cell_flags'), u'cell_x',
            u'cell_y'),
        MelString(b'RGNN', u'region_name'),
        MelColorO(b'NAM5'),
        MelFloat(b'WHGT', u'water_height'),
        MelStruct(b'AMBI', ['12B', 'f'], *color_attrs('ambi_ambient'),
            *color_attrs('ambi_sunlight'), *color_attrs('ambi_fog'),
            'fog_density'),
        MelGroups(u'moved_references',
            MelUInt32(b'MVRF', u'reference_id'),
            MelString(b'CNAM', u'new_interior_cell'),
            ##: Double-check the signeds - UESP does not list them either way
            MelStruct(b'CNDT', ['2i'], 'new_exterior_cell_x',
                      'new_exterior_cell_y'),
            MelReference(),
        ),
        ##: Move this into a dedicated Mob* class instead - difficult to
        # manipulate otherwise, tons of duplicate signatures and a distributor
        # is impossible due to the lack of static separators in the record.
        MelGroups(u'persistent_children',
            MelReference(),
        ),
        MelCounter(MelUInt32(b'NAM0', u'temporary_children_counter'),
            counts=u'temporary_children'),
        MelGroups(u'temporary_children',
            MelReference(),
        ),
    )

#------------------------------------------------------------------------------
class MreClas(MelRecord):
    """Class."""
    rec_sig = b'CLAS'

    class _class_flags(Flags):
        class_playable: bool

    class _ac_flags(Flags):
        ac_weapon: bool
        ac_armor: bool
        ac_clothing: bool
        ac_books: bool
        ac_ingredients: bool
        ac_picks: bool
        ac_probes: bool
        ac_lights: bool
        ac_apparatus: bool
        ac_repair_items: bool
        ac_misc: bool
        ac_spells: bool
        ac_magic_items: bool
        ac_potions: bool
        ac_training: bool
        ac_spellmaking: bool
        ac_enchanting: bool
        ac_repair: bool

    melSet = MelSet(
        MelMWId(),
        MelFullTes3(),
        ##: UESP says 'alternating minor/major' skills - not sure what exactly
        # it means, check with real data
        MelStruct(b'CLDT', [u'15I'], u'primary1', u'primary2',
            u'specialization', u'minor1', u'major1', u'minor2', u'major2',
            u'minor3', u'major3', u'minor4', u'major4', u'minor5', u'major5',
            (_class_flags, u'class_flags'), (_ac_flags, u'auto_calc_flags')),
        MelDescription(),
    )

#------------------------------------------------------------------------------
class MreClot(MelRecord):
    """Clothing."""
    rec_sig = b'CLOT'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelFullTes3(),
        MelStruct(b'CTDT', [u'I', u'f', u'2H'], u'clot_type', u'clot_weight',
            u'clot_value', u'enchant_points'),
        MelScriptId(),
        MelIconTes3(),
        MelArmorData(),
        MelEnchantmentTes3(),
    )

#------------------------------------------------------------------------------
class MreCont(MelRecord):
    """Container."""
    rec_sig = b'CONT'

    class _cont_flags(Flags):
        cont_organic: bool
        cont_respawns: bool
        default_unknown: bool   # always set

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelFullTes3(),
        MelFloat(b'CNDT', u'cont_weight'),
        MelUInt32Flags(b'FLAG', u'cont_flags', _cont_flags),
        MelItems(),
        MelScriptId(),
    )

#------------------------------------------------------------------------------
class MreCrea(MelRecord):
    """Creature."""
    rec_sig = b'CREA'

    # Default is 0x48 (crea_walks | crea_none)
    class _CreaFlags(Flags):
        crea_biped: bool
        crea_respawn: bool
        weapon_and_shield: bool
        crea_none: bool
        crea_swims: bool
        crea_flies: bool
        crea_walks: bool
        crea_essential: bool

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelString(b'CNAM', u'sound_gen_creature'),
        MelFullTes3(),
        MelScriptId(),
        MelStruct(b'NPDT', [u'24I'], u'crea_type', u'crea_level',
            u'crea_strength', u'crea_intelligence', u'crea_willpower',
            u'crea_agility', u'crea_speed', u'crea_endurance',
            u'crea_personality', u'crea_luck', u'crea_health',
            u'crea_spell_points', u'crea_fatigue', u'crea_soul',
            u'crea_combat', u'crea_magic', u'crea_stealth',
            u'crea_attack_min_1', u'crea_attack_max_1', u'crea_attack_min_2',
            u'crea_attack_max_2', u'crea_attack_min_3', u'crea_attack_max_3',
            u'crea_gold'),
        MelStruct(b'FLAG', ['B', '3s'], ('crea_flags', _CreaFlags),
            'blood_type'),
        MelRefScale(),
        MelItems(),
        MelSpellsTes3(),
        MelAidt(),
        MelDestinations(),
        MelAIPackagesTes3(),
    )

#------------------------------------------------------------------------------
class MreDial(MelRecord):
    """Dialog Topic."""
    rec_sig = b'DIAL'

    melSet = MelSet(
        MelMWId(),
        MelUInt8(b'DATA', u'dialogue_type'),
    )

#------------------------------------------------------------------------------
class MreDoor(MelRecord):
    """Door."""
    rec_sig = b'DOOR'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelFullTes3(),
        MelScriptId(),
        MelString(b'SNAM', u'sound_open'),
        MelString(b'ANAM', u'sound_close'),
    )

#------------------------------------------------------------------------------
class MreEnch(MelRecord):
    """Enchantment."""
    rec_sig = b'ENCH'

    melSet = MelSet(
        MelMWId(),
        MelStruct(b'ENDT', [u'4I'], u'ench_type', u'ench_cost', u'ench_charge',
            u'ench_auto_calc'),
        MelEffectsTes3(),
    )

#------------------------------------------------------------------------------
class MreFact(MelRecord):
    """Faction."""
    rec_sig = b'FACT'

    melSet = MelSet(
        MelMWId(),
        MelFullTes3(),
        MelGroups(u'ranks', # always 10
            MelString(b'RNAM', u'rank_name'),
        ),
        ##: Double-check that these are all unsigned (especially
        # rank_*_reaction), xEdit makes most of them signed (and puts them in
        # an enum, which makes no sense). Also, why couldn't Bethesda put these
        # into the ranks list up above?
        MelStruct(b'FADT', [u'52I', u'7i', u'I'], u'faction_attribute_1',
            u'faction_attribute_2', u'rank_1_attribute_1',
            u'rank_1_attribute_2', u'rank_1_skill_1', u'rank_1_skill_2',
            u'rank_1_reaction', u'rank_2_attribute_1', u'rank_2_attribute_2',
            u'rank_2_skill_1', u'rank_2_skill_2', u'rank_2_reaction',
            u'rank_3_attribute_1', u'rank_3_attribute_2', u'rank_3_skill_1',
            u'rank_3_skill_2', u'rank_3_reaction', u'rank_4_attribute_1',
            u'rank_4_attribute_2', u'rank_4_skill_1', u'rank_4_skill_2',
            u'rank_4_reaction', u'rank_5_attribute_1', u'rank_5_attribute_2',
            u'rank_5_skill_1', u'rank_5_skill_2', u'rank_5_reaction',
            u'rank_6_attribute_1', u'rank_6_attribute_2', u'rank_6_skill_1',
            u'rank_6_skill_2', u'rank_6_reaction', u'rank_7_attribute_1',
            u'rank_7_attribute_2', u'rank_7_skill_1', u'rank_7_skill_2',
            u'rank_7_reaction', u'rank_8_attribute_1', u'rank_8_attribute_2',
            u'rank_8_skill_1', u'rank_8_skill_2', u'rank_8_reaction',
            u'rank_9_attribute_1', u'rank_9_attribute_2', u'rank_9_skill_1',
            u'rank_9_skill_2', u'rank_9_reaction', u'rank_10_attribute_1',
            u'rank_10_attribute_2', u'rank_10_skill_1', u'rank_10_skill_2',
            u'rank_10_reaction', u'skill_1', u'skill_2', u'skill_3',
            u'skill_4', u'skill_5', u'skill_6', u'skill_7',
            u'hidden_from_pc'),
        MelGroups(u'relations', # bad names to match other games
            MelString(b'ANAM', u'faction'),
            MelSInt32(b'INTV', u'mod'),
        ),
    )

#------------------------------------------------------------------------------
class MreGlob(MelRecord):
    """Global."""
    rec_sig = b'GLOB'

    melSet = MelSet(
        MelMWId(),
        MelFixedString(b'FNAM', 'global_format', 1),
        MelFloat(b'FLTV', u'global_value'),
    )

#------------------------------------------------------------------------------
class MelGmstUnion(MelUnion):
    """Some GMSTs do not have one of the value subrecords - fall back to
    using the first letter of the NAME subrecord in those cases."""
    _fmt_mapping = {
        u'f': b'FLTV',
        u'i': b'INTV',
        u's': b'STRV',
    }

    def _get_element_from_record(self, record):
        if not hasattr(record, self.decider_result_attr):
            format_char = record.mw_id[0] if record.mw_id else u'i'
            return self._get_element(self._fmt_mapping[format_char])
        return super(MelGmstUnion, self)._get_element_from_record(record)

class MreGmst(MelRecord):
    """Game Setting."""
    melSet = MelSet(
        MelMWId(),
        MelGmstUnion({
            b'FLTV': MelFloat(b'FLTV', u'value'),
            b'INTV': MelSInt32(b'INTV', u'value'),
            b'STRV': MelString(b'STRV', u'value'),
        }),
    )

#------------------------------------------------------------------------------
class MreInfo(MelRecord):
    """Dialog Response."""
    rec_sig = b'INFO'

    melSet = MelSet(
        MelString(b'INAM', u'info_name_string'),
        MelString(b'PNAM', u'prev_info'),
        MelString(b'NNAM', u'next_info'),
        MelStruct(b'DATA', [u'B', u'3s', u'I', u'B', u'b', u'B', u's'], u'dialogue_type', u'unused1',
            u'disposition', u'dialogue_rank', u'speaker_gender', u'pc_rank',
            u'unused2'),
        MelString(b'ONAM', u'actor_name'),
        MelString(b'RNAM', u'race_name'),
        MelString(b'CNAM', u'class_name'),
        MelString(b'FNAM', u'faction_name'),
        MelString(b'ANAM', u'cell_name'),
        MelString(b'DNAM', u'pc_faction_name'),
        MelString(b'SNAM', u'sound_name'),
        MelMWId(),
        MelGroups(u'conditions',
            MelString(b'SCVR', u'condition_string'),
            MelUInt32(b'INTV', u'comparison_int'),
            MelFloat(b'FLTV', u'comparison_float'),
        ),
        MelString(b'BNAM', u'result_text'),
        MelUInt8(b'QSTN', u'quest_name'),
        MelUInt8(b'QSTF', u'quest_finished'),
        MelUInt8(b'QSTR', u'quest_restart'),
    )

#------------------------------------------------------------------------------
class MreIngr(MelRecord):
    """Ingredient."""
    rec_sig = b'INGR'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelFullTes3(),
        MelStruct(b'IRDT', [u'f', u'I', u'12i'], u'ingr_weight', u'ingr_value',
            u'effect_index_1', u'effect_index_2', u'effect_index_3',
            u'effect_index_4', u'skill_id_1', u'skill_id_2', u'skill_id_3',
            u'skill_id_4', u'attribute_id_1', u'attribute_id_2',
            u'attribute_id_3', u'attribute_id_4'),
        MelScriptId(),
        MelIconTes3(),
    )

#------------------------------------------------------------------------------
class MreLand(MelRecord):
    """Landscape."""
    rec_sig = b'LAND'

    class _data_type_flags(Flags): ##: Shouldn't we set/use these?
        include_vnml_vhgt_wnam: bool
        include_vclr: bool
        include_vtex: bool

    ##: No MelMWId, will that be a problem?
    melSet = MelSet(
        MelStruct(b'INTV', [u'2I'], u'land_x', u'land_y'),
        MelUInt32Flags(b'DATA', u'dt_flags', _data_type_flags),
        # These are all very large and too complex to manipulate -> MelBase
        MelBase(b'VNML', u'vertex_normals'),
        MelBase(b'VHGT', u'vertex_height_map'),
        MelBase(b'WNAM', u'world_map_heights'),
        MelBase(b'VCLR', u'vertex_colors'),
        MelBase(b'VTEX', u'vertex_textures'),
    )

#------------------------------------------------------------------------------
class MreLevc(AMreLeveledList):
    """Leveled Creature."""
    rec_sig = b'LEVC'
    _top_copy_attrs = ('lvl_chance_none',)
    _entry_copy_attrs = ('level', 'listId')

    melSet = MelSet(
        MelMWId(),
        MelLLFlagsTes3(),
        MelLLChanceNoneTes3(),
        MelLLItemsTes3(item_sig=b'CNAM'),
    )

#------------------------------------------------------------------------------
class MreLevi(AMreLeveledList):
    """Leveled Item."""
    rec_sig = b'LEVI'
    _top_copy_attrs = ('lvl_chance_none',)
    _entry_copy_attrs = ('level', 'listId')

    melSet = MelSet(
        MelMWId(),
        MelLLFlagsTes3(),
        MelLLChanceNoneTes3(),
        MelLLItemsTes3(item_sig=b'INAM'),
    )

#------------------------------------------------------------------------------
class MreLigh(MelRecord):
    """Light."""
    rec_sig = b'LIGH'

    class _light_flags(Flags):
        light_dynamic: bool
        light_can_take: bool
        light_negative: bool
        light_flickers: bool
        light_fire: bool
        light_off_by_default: bool
        light_flickers_slow: bool
        light_pulses: bool
        light_pulses_slow: bool

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelFullTes3(),
        MelIconTes3(),
        MelStruct(b'LHDT', ['f', 'I', 'i', 'I', '4B', 'I'], 'weight', 'value',
            'duration', 'light_radius', *color_attrs('light_color'),
            (_light_flags, 'light_flags')),
        MelString(b'SNAM', 'sound_name'),
        MelScriptId(),
    )

#------------------------------------------------------------------------------
class MreLock(MelRecord):
    """Lockpicking Item."""
    rec_sig = b'LOCK'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelFullTes3(),
        MelStruct(b'LKDT', [u'f', u'I', u'f', u'I'], u'lock_weight', u'lock_value',
            u'lock_quality', u'lock_uses'),
        MelScriptId(),
        MelIconTes3(),
    )

#------------------------------------------------------------------------------
class MreLtex(MelRecord):
    """Landscape Texture."""
    rec_sig = b'LTEX'

    melSet = MelSet(
        MelMWId(),
        MelUInt32(b'INTV', 'ltex_index'),
        MelString(b'DATA', 'ltex_texture_name'),
    )

#------------------------------------------------------------------------------
class MreMgef(MelRecord):
    """Magic Effect."""
    rec_sig = b'MGEF'

    class _mgef_flags(Flags):
        spellmaking: bool = flag(9)
        enchanting: bool = flag(10)
        negative: bool = flag(11)

    ##: No MelMWId, will that be a problem?
    ##: This will be a pain. They're hardcoded like in Oblivion, but use an int
    # index instead of a fourcc (i.e. the EDID in Oblivion).
    # Bad names to match other games (MGEF is scary since it's littered
    # implicity all over our codebase still)
    melSet = MelSet(
        MelUInt32(b'INDX', u'mgef_index'),
        MelStruct(b'MEDT', ['I', 'f', '4I', '3f'], 'school', 'base_cost',
            (_mgef_flags, 'flags'), *color3_attrs('mgef_color'), 'speed_x',
            'size_x', 'size_cap'),
        MelIconTes3(),
        MelString(b'PTEX', u'particle_texture'),
        MelString(b'BSND', u'boltSound'),
        MelString(b'CSND', u'castingSound'),
        MelString(b'HSND', u'hitSound'),
        MelString(b'ASND', u'areaSound'),
        MelString(b'CVFX', u'casting_visual'),
        MelString(b'BVFX', u'bolt_visual'),
        MelString(b'HVFX', u'hit_visual'),
        MelString(b'AVFX', u'are_visual'),
        MelDescription(),
    )

#------------------------------------------------------------------------------
class MreMisc(MelRecord):
    """Misc. Item."""
    rec_sig = b'MISC'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelFullTes3(),
        MelStruct(b'MCDT', [u'f', u'I', u'4s'], u'misc_weight', u'misc_value',
            u'unknown1'),
        MelScriptId(),
        MelIconTes3(),
    )

#------------------------------------------------------------------------------
class MreNpc_(MelRecord):
    """Non-Player Character."""
    rec_sig = b'NPC_'

    class NpcFlags(Flags):
        npc_female: bool
        npc_essential: bool
        npc_respawn: bool
        default_unknown: bool # always set
        npc_auto_calc: bool

    class MelNpcData(MelLists):
        """Converts attributes and skills into lists."""
        _attr_indexes = {
            'npc_level': 0, 'attributes': slice(1, 9), 'skills': slice(9, 36),
            'unknown2': 36, 'npc_health': 38, 'npc_spell_points': 39,
            'npc_fatigue': 40, 'npc_disposition': 41, 'npc_reputation': 42,
            'npc_rank': 43, 'unknown3': 44, 'npc_gold': 45}

    class NpcDataDecider(SizeDecider):
        """At load time we can decide based on the subrecord size, but at dump
        time we need to consider the auto-calculate flag instead."""
        can_decide_at_dump = True

        def decide_dump(self, record):
            return 12 if record.npc_flags.npc_auto_calc else 52

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelFullTes3(),
        MelString(b'RNAM', 'race'),
        MelString(b'CNAM', 'npc_class'),
        MelString(b'ANAM', u'faction_name'),
        MelString(b'BNAM', u'head_model'),
        MelString(b'KNAM', u'hair_model'),
        MelScriptId(),
        MelUnion({
            12: MelStruct(b'NPDT', [u'H', u'3B', u'3s', u'I'], u'npc_level', u'npc_disposition',
                u'npc_reputation', u'npc_rank', u'unknown1',
                u'npc_gold'),
            52: MelNpcData(b'NPDT', [u'H', u'8B', u'27B', u's', u'H', u'H', u'H', u'B', u'B', u'B', u's', u'I'], u'npc_level',
                (u'attributes', [0] * 8), (u'skills', [0] * 27),
                u'unknown2', u'npc_health', u'npc_spell_points',
                u'npc_fatigue', u'npc_disposition', u'npc_reputation',
                u'npc_rank', u'unknown3', u'npc_gold'),
        }, decider=NpcDataDecider()),
        MelStruct(b'FLAG', ['B', '3s'], ('npc_flags', NpcFlags),
            'blood_type'),
        MelItems(),
        MelSpellsTes3(),
        MelAidt(),
        MelDestinations(),
        MelAIPackagesTes3(),
    )

#------------------------------------------------------------------------------
class MrePgrd(MelRecord):
    """Path Grid."""
    rec_sig = b'PGRD'

    melSet = MelSet(
        MelStruct(b'DATA', [u'2I', u'2s', u'H'], u'pgrd_x', u'pgrd_y',
            u'unknown1', u'point_count'),
        MelMWId(),
        # Could be loaded via MelArray, but are very big and not very useful
        MelBase(b'PGRP', u'point_array'),
        MelBase(b'PGRC', u'point_edges'),
    )

#------------------------------------------------------------------------------
class MreProb(MelRecord):
    """Probe Item."""
    rec_sig = b'PROB'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelFullTes3(),
        MelStruct(b'PBDT', [u'f', u'I', u'f', u'I'], u'probe_weight', u'probe_value',
            u'probe_quality', u'probe_uses'),
        MelIconTes3(),
        MelScriptId(),
    )

#------------------------------------------------------------------------------
class MreRace(MelRecord):
    """Race."""
    rec_sig = b'RACE'

    class _race_flags(Flags):
        playable: bool
        beast_race: bool

    melSet = MelSet(
        MelMWId(),
        MelFullTes3(),
        # Bad names to match other games (race patcher)
        MelStruct(b'RADT', [u'14i', u'16I', u'4f', u'I'], u'skill1', u'skill1Boost', u'skill2',
            u'skill2Boost', u'skill3', u'skill3Boost', u'skill4',
            u'skill4Boost', u'skill5', u'skill5Boost', u'skill6',
            u'skill6Boost', u'skill7', u'skill7Boost', u'maleStrength',
            u'femaleStrength', u'maleIntelligence', u'femaleIntelligence',
            u'maleWillpower', u'femaleWillpower', u'maleAgility',
            u'femaleAgility', u'maleSpeed', u'femaleSpeed', u'maleEndurance',
            u'femaleEndurance', u'malePersonality', u'femalePersonality',
            u'maleLuck', u'femaleLuck', u'maleHeight', u'femaleHeight',
            u'maleWeight', u'femaleWeight', (_race_flags, u'race_flags')),
        MelSpellsTes3(),
        MelDescription(),
    )

#------------------------------------------------------------------------------
class MreRegn(MelRecord):
    """Region."""
    rec_sig = b'REGN'

    melSet = MelSet(
        MelMWId(),
        MelFullTes3(),
        MelTruncatedStruct(b'WEAT', [u'10B'], u'chance_clear', u'chance_cloudy',
            u'chance_foggy', u'chance_overcast', u'chance_rain',
            u'chance_thunder', u'chance_ash', u'chance_blight',
            u'chance_snow', u'chance_blizzard', old_versions={u'8B'}),
        MelString(b'BNAM', u'sleep_creature'),
        MelColor(),
        MelGroups(u'sound_chances',
            MelStruct(b'SNAM', [u'32s', u'B'], (FixedString(32), u'sound_name'),
                u'sound_chance'),
        ),
    )

#------------------------------------------------------------------------------
class MreRepa(MelRecord):
    """Repair Item."""
    rec_sig = b'REPA'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelFullTes3(),
        MelStruct(b'RIDT', [u'f', u'2I', u'f'], u'repa_weight', u'repa_value',
            u'repa_uses', u'repa_quality'),
        MelIconTes3(),
        MelScriptId(),
    )

#------------------------------------------------------------------------------
class MreScpt(MelRecord):
    """Script."""
    rec_sig = b'SCPT'

    melSet = MelSet(
        # Yes, the usual NAME sits in this subrecord instead
        MelStruct(b'SCHD', [u'32s', u'5I'], (FixedString(32), u'mw_id'),
            u'num_shorts', u'num_longs', u'num_floats', u'script_data_size',
            u'local_var_size'),
        MelStrings(b'SCVR', u'script_variables'),
        MelBase(b'SCDT', u'compiled_script'),
        MelString(b'SCTX', u'script_source'),
    )

#------------------------------------------------------------------------------
class MreSkil(MelRecord):
    """Skill."""
    rec_sig = b'SKIL'

    ##: No MelMWId, will that be a problem?
    melSet = MelSet(
        MelUInt32(b'INDX', u'skill_index'),
        MelStruct(b'SKDT', [u'2I', u'4f'], u'skill_attribute',
            u'skill_specialization', u'use_value_1', u'use_value_2',
            u'use_value_3', u'use_value_4'),
        MelDescription(),
    )

#------------------------------------------------------------------------------
class MreSndg(MelRecord):
    """Sound Generator."""
    rec_sig = b'SNDG'

    melSet = MelSet(
        MelMWId(),
        MelUInt32(b'DATA', u'sdng_type'),
        MelString(b'CNAM', u'creature_name'),
        ##: Investigate what this is and if we should use it instead of NAME
        MelString(b'SNAM', u'sound_id'),
    )

#------------------------------------------------------------------------------
class MreSoun(MelRecord):
    """Sound."""
    rec_sig = b'SOUN'

    melSet = MelSet(
        MelMWId(),
        MelString(b'FNAM', u'sound_filename'),
        MelStruct(b'DATA', [u'3B'], u'atten_volume', u'min_range',
            u'max_range'),
    )

#------------------------------------------------------------------------------
class MreSpel(MelRecord):
    """Spell."""
    rec_sig = b'SPEL'

    class _SpellFlags(Flags):
        auto_cost_calc: bool
        pc_start_spell: bool
        always_suceeds: bool

    melSet = MelSet(
        MelMWId(),
        MelFullTes3(),
        MelStruct(b'SPDT', ['3I'], 'spell_type', 'spell_cost',
            (_SpellFlags, 'spell_flags')),
        MelEffectsTes3(),
    )

#------------------------------------------------------------------------------
class MreSscr(MelRecord):
    """Start Script."""
    rec_sig = b'SSCR'

    melSet = MelSet(
        MelString(b'DATA', u'unknown_digits'), # series of ASCII digits
        MelMWId(),
    )

#------------------------------------------------------------------------------
class MreStat(MelRecord):
    """Static."""
    rec_sig = b'STAT'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
    )

#------------------------------------------------------------------------------
class MreWeap(MelRecord):
    """Weapon."""
    rec_sig = b'WEAP'

    class _weapon_flags(Flags):
        ignore_normal_weapon_resistance: bool
        is_silver: bool

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelFullTes3(),
        MelStruct(b'WPDT', [u'f', u'I', u'2H', u'2f', u'H', u'6B', u'I'], u'weapon_weight', u'weapon_value',
            u'weapon_type', u'weapon_health', u'weapon_speed', u'weapon_reach',
            u'enchant_points', u'chop_minimum', u'chop_maximum',
            u'slash_minimum', u'slash_maximum', u'thrust_minimum',
            u'thrust_maximum', (_weapon_flags, u'weapon_flags')),
        MelIconTes3(),
        MelEnchantmentTes3(),
        MelScriptId(),
    )
