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
    FixedString, MelArray, MelBase, MelBookText, MelColorO, \
    MelCounter, MelDescription, MelEffectsTes3, MelFixedString, MelFloat, \
    MelGroup, MelGroups, MelIcons, AMelLists, MelLLChanceNoneTes3, \
    MelLLFlagsTes3, MelNull, MelRecord, MelRef3D, MelRefScale, MelSequential, \
    MelSet, MelSInt32, MelString, MelStrings, MelStruct, MelTruncatedStruct, \
    MelUInt8, MelUInt16, MelUInt32, MelUInt32Flags, MelUnion, SaveDecider, \
    SizeDecider, color_attrs, color3_attrs, position_attrs, rotation_attrs, \
    MelReadOnly, MgefFlagsTes3

#------------------------------------------------------------------------------
# Common Flags
class ServiceFlags(Flags):
    service_weapon: bool
    service_armor: bool
    service_clothing: bool
    service_books: bool
    service_ingredient: bool
    service_picks: bool
    service_probes: bool
    service_lights: bool
    service_apparatus: bool
    service_repair_items: bool
    service_misc: bool
    service_spells: bool
    service_magic_items: bool
    service_potions: bool
    service_training: bool
    service_spellmaking: bool
    service_enchanting: bool
    service_repair: bool

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
class MelDeleted(MelUInt32):
    """The presence of this subrecord means that the record in question is
    being deleted by the current plugin."""
    def __init__(self):
        super().__init__(b'DELE', 'marked_deleted')

#------------------------------------------------------------------------------
class MelAidt(MelStruct):
    """Handles the CREA/NPC_ subrecord AIDT (AI Data)."""

    def __init__(self):
        super().__init__(b'AIDT', ['H', '3B', '3s', 'I'], 'ai_hello',
            'ai_fight', 'ai_flee', 'ai_alarm', 'ai_unused1',
            (ServiceFlags, 'ai_service_flags'))

#------------------------------------------------------------------------------
class MelAIPackagesTes3(MelGroups):
    """Handles the AI_* and CNDT subrecords, which have the additional
    complication that they may occur in any order."""
    def __init__(self):
        super().__init__('ai_packages',
            MelUnion({
                # AI_A: AI Activate
                b'AI_A': MelStruct(b'AI_A', ['32s', 'B'],
                    (FixedString(32), 'package_name'), 'ai_reset'),
                # AI_E: AI Escort
                b'AI_E': MelStruct(b'AI_E', ['3f', 'H', '32s', 'B', 's'],
                    *position_attrs('dest'), 'package_duration',
                    (FixedString(32), 'package_id'), 'ai_reset', 'unused1'),
                # AI_F: AI Follow
                b'AI_F': MelStruct(b'AI_F', ['3f', 'H', '32s', 'B', 's'],
                    *position_attrs('dest'), 'package_duration',
                    (FixedString(32), 'package_id'), 'ai_reset', 'unused1'),
                # AI_T: AI Travel
                b'AI_T': MelStruct(b'AI_T', ['3f', 'B', '3s'],
                    *position_attrs('dest'), 'ai_reset', 'unused1'),
                # AI_W: AI Wander
                b'AI_W': MelStruct(b'AI_W', ['2H', '10B'], 'wander_distance',
                    'wander_duration', 'time_of_day', 'idle_chance_1',
                    'idle_chance_2', 'idle_chance_3', 'idle_chance_4',
                    'idle_chance_5', 'idle_chance_6', 'idle_chance_7',
                    'idle_chance_8', 'idle_chance_9'),
            }),
            # Only present for AI_E and AI_F, but won't be dumped unless
            # already present, so that's fine
            MelString(b'CNDT', 'target_cell_name'),
        )

#------------------------------------------------------------------------------
class MelBipedObjects(MelGroups):
    """Handles the INDX, BNAM and CNAM subrecords shared by ARMO and CLOT."""
    def __init__(self):
        super().__init__('biped_objects',
            MelUInt8(b'INDX', 'body_part_index'),
            MelString(b'BNAM', 'armor_name_male'),
            MelString(b'CNAM', 'armor_name_female'),
        )

#------------------------------------------------------------------------------
class MelTravelServices(MelGroups):
    """Handles the common DODT/DNAM subrecords."""
    def __init__(self):
        super().__init__('travel_services',
            MelStruct(b'DODT', ['6f'], *position_attrs('destination'),
                *rotation_attrs('destination')),
            MelFixedString(b'DNAM', 'destination_cell_name', 64),
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
        super().__init__('items',
            MelStruct(b'NPCO', ['i', '32s'], 'count',
                (FixedString(32), 'item')),
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
        super().__init__(
            MelUInt32(b'FRMR', 'object_index'),
            MelMWId(),
            MelBase(b'UNAM', 'ref_blocked_marker'),
            MelRefScale(),
            MelString(b'ANAM', 'ref_owner'),
            MelString(b'BNAM', 'global_variable'),
            MelString(b'CNAM', 'ref_faction'),
            MelSInt32(b'INDX', 'ref_faction_rank'),
            MelString(b'XSOL', 'ref_soul'),
            MelFloat(b'XCHG', 'enchantment_charge'),
            ##: INTV should have a decider - uint32 or float, depending on
            # object type
            MelBase(b'INTV', 'remaining_usage'),
            MelUInt32(b'NAM9', 'gold_value'),
            MelTravelServices(),
            MelUInt32(b'FLTV', 'lock_level'),
            MelString(b'KNAM', 'key_name'),
            MelString(b'TNAM', 'trap_name'),
            MelBase(b'ZNAM', 'ref_disabled_marker'),
            MelRef3D(),
        )

#------------------------------------------------------------------------------
class MelSavesOnly(MelSequential):
    """Record element that only loads contents if the input file is a save
    file."""
    def __init__(self, *elements):
        super().__init__(*(MelUnion({
            True: element,
            False: MelNull(next(iter(element.signatures))),
        }, decider=SaveDecider()) for element in elements))

#------------------------------------------------------------------------------
class MelScriptId(MelString):
    """Handles the common SCRI subrecord."""
    def __init__(self):
        super().__init__(b'SCRI', 'script_id'),

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
            MelStruct(b'GMDT', ['6f', '64s', 'f', '32s'], 'pc_curr_health',
                'pc_max_health', 'unknown1', 'unknown2', 'unknown3',
                'unknown4', (FixedString(64), 'curr_cell'),
                'unknown5', (AutoFixedString(32), 'pc_name')),
            MelBase(b'SCRD', 'unknown_scrd'), # likely screenshot-related
            MelArray('screenshot_data',
                # Yes, the correct order is bgra
                MelStruct(b'SCRS', ['4B'], 'blue', 'green', 'red', 'alpha'),
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
        MelDeleted(),
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
        MelDeleted(),
        MelModel(),
        MelString(b'TEXT', 'inventory_icon'),
        MelScriptId(),
        MelFullTes3(),
        MelStruct(b'ALDT', ['f', '2I'], 'potion_weight', 'potion_value',
            'potion_auto_calc'),
        MelEffectsTes3(),
    )

#------------------------------------------------------------------------------
class MreAppa(MelRecord):
    """Alchemical Apparatus."""
    rec_sig = b'APPA'

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelModel(),
        MelFullTes3(),
        MelScriptId(),
        MelStruct(b'AADT', ['I', '2f', 'I'], 'appa_type', 'appa_quality',
            'appa_weight', 'appa_value'),
        MelIconTes3(),
    )

#------------------------------------------------------------------------------
class MreArmo(MelRecord):
    """Armor."""
    rec_sig = b'ARMO'

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelModel(),
        MelFullTes3(),
        MelScriptId(),
        MelStruct(b'AODT', ['I', 'f', '4I'], 'armo_type', 'armo_weight',
            'armo_value', 'armo_health', 'enchanting_charge', 'armor_rating'),
        MelIconTes3(),
        MelBipedObjects(),
        MelEnchantmentTes3(),
    )

#------------------------------------------------------------------------------
class MreBody(MelRecord):
    """Body Parts."""
    rec_sig = b'BODY'

    class _PartFlags(Flags):
        part_female: bool
        part_playable: bool

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelModel(),
        MelString(b'FNAM', 'skin_race_name'),
        MelStruct(b'BYDT', ['4B'], 'part_index', 'skin_type',
            (_PartFlags, 'part_flags'), 'part_type'),
    )

#------------------------------------------------------------------------------
class MreBook(MelRecord):
    """Book."""
    rec_sig = b'BOOK'

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelModel(),
        MelFullTes3(),
        MelStruct(b'BKDT', ['f', 'i', 'I', '2i'], 'book_weight', 'book_value',
            'is_scroll', 'taught_skill_id', 'enchanting_charge'),
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
        MelDeleted(),
        MelMWId(),
        MelFullTes3(),
        MelString(b'TNAM', 'constellation_image'),
        MelDescription(),
        MelSpellsTes3(),
    )

#------------------------------------------------------------------------------
class MreCell(AMreCell):
    """Cell."""
    # TODO ref_types and co?

    class _CellFlags(Flags):
        is_interior_cell: bool = flag(0)
        has_water: bool = flag(1)
        illegal_to_sleep_here: bool = flag(2)
        has_map_color: bool = flag(6)
        behave_like_exterior: bool = flag(7)

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelStruct(b'DATA', ['I', '2i'], (_CellFlags, 'cell_flags'), 'cell_x',
            'cell_y'),
        # Old version of WHGT, read but write only WHGT
        MelReadOnly(MelUInt32(b'INTV', 'water_height')),
        MelString(b'RGNN', 'region_name'),
        MelColorO(b'NAM5'),
        MelFloat(b'WHGT', 'water_height'),
        MelStruct(b'AMBI', ['12B', 'f'], *color_attrs('ambi_ambient'),
            *color_attrs('ambi_sunlight'), *color_attrs('ambi_fog'),
            'fog_density'),
        MelGroups('moved_references',
            MelUInt32(b'MVRF', 'reference_id'),
            MelString(b'CNAM', 'new_interior_cell'),
            ##: Double-check the signeds - UESP does not list them either way
            MelStruct(b'CNDT', ['2i'], 'new_exterior_cell_x',
                      'new_exterior_cell_y'),
            MelReference(),
        ),
        ##: Move this into a dedicated Mob* class instead - difficult to
        # manipulate otherwise, tons of duplicate signatures and a distributor
        # is impossible due to the lack of static separators in the record.
        MelGroups('persistent_children',
            MelReference(),
        ),
        MelCounter(MelUInt32(b'NAM0', 'temporary_children_counter'),
            counts='temporary_children'),
        MelGroups('temporary_children',
            MelReference(),
        ),
    )

#------------------------------------------------------------------------------
class MreClas(MelRecord):
    """Class."""
    rec_sig = b'CLAS'

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelFullTes3(),
        MelStruct(b'CLDT', ['2i', 'I', '10i', '2I'], 'primary1', 'primary2',
            'specialization', 'minor1', 'major1', 'minor2', 'major2',
            'minor3', 'major3', 'minor4', 'major4', 'minor5', 'major5',
            'class_playable', (ServiceFlags, 'class_service_flags')),
        MelDescription(),
    )

#------------------------------------------------------------------------------
class MreClot(MelRecord):
    """Clothing."""
    rec_sig = b'CLOT'

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelModel(),
        MelFullTes3(),
        MelStruct(b'CTDT', ['I', 'f', '2H'], 'clot_type', 'clot_weight',
            'clot_value', 'enchanting_charge'),
        MelScriptId(),
        MelIconTes3(),
        MelBipedObjects(),
        MelEnchantmentTes3(),
    )

#------------------------------------------------------------------------------
class MreCont(MelRecord):
    """Container."""
    rec_sig = b'CONT'

    class _ContFlags(Flags):
        cont_organic: bool = flag(0)
        cont_respawns: bool = flag(1)
        can_hold_items: bool = flag(3)

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelModel(),
        MelFullTes3(),
        MelFloat(b'CNDT', 'cont_weight'),
        MelUInt32Flags(b'FLAG', 'cont_flags', _ContFlags),
        MelScriptId(),
        MelItems(),
    )

#------------------------------------------------------------------------------
class MreCrea(MelRecord):
    """Creature."""
    rec_sig = b'CREA'

    # Default is 0x48 (crea_walks | crea_none)
    class _CreaFlags(Flags):
        crea_biped: bool = flag(0)
        crea_respawn: bool = flag(1)
        weapon_and_shield: bool = flag(2)
        crea_can_hold_items: bool = flag(3)
        crea_swims: bool = flag(4)
        crea_flies: bool = flag(5)
        crea_walks: bool = flag(6)
        crea_essential: bool = flag(7)
        skeleton_blood: bool = flag(10)
        metal_blood: bool = flag(11)

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelModel(),
        MelString(b'CNAM', 'sound_gen_creature'),
        MelFullTes3(),
        MelScriptId(),
        MelStruct(b'NPDT', ['I', '12i', 'I', '9i', 'I'], 'crea_type',
            'crea_level', 'crea_attr_strength', 'crea_attr_intelligence',
            'crea_attr_willpower', 'crea_attr_agility', 'crea_attr_speed',
            'crea_attr_endurance', 'crea_attr_personality', 'crea_attr_luck',
            'crea_health', 'crea_magicka', 'crea_fatigue', 'crea_soul',
            'crea_skill_combat', 'crea_skill_magic', 'crea_skill_stealth',
            'crea_attack_1_min', 'crea_attack_1_max', 'crea_attack_2_min',
            'crea_attack_2_max', 'crea_attack_3_min', 'crea_attack_3_max',
            'crea_barter_gold'),
        MelUInt32Flags(b'FLAG', 'crea_flags', _CreaFlags),
        MelRefScale(),
        MelItems(),
        MelSpellsTes3(),
        MelAidt(),
        MelTravelServices(),
        MelAIPackagesTes3(),
    )

#------------------------------------------------------------------------------
class MreDial(MelRecord):
    """Dialog Topic."""
    rec_sig = b'DIAL'

    melSet = MelSet(
        MelMWId(),
        MelStruct(b'DATA', ['B', '3s'], 'dialogue_type', 'unused1'),
        MelDeleted(),
    )

#------------------------------------------------------------------------------
class MreDoor(MelRecord):
    """Door."""
    rec_sig = b'DOOR'

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelModel(),
        MelFullTes3(),
        MelScriptId(),
        MelString(b'SNAM', 'sound_open'),
        MelString(b'ANAM', 'sound_close'),
    )

#------------------------------------------------------------------------------
class MreEnch(MelRecord):
    """Enchantment."""
    rec_sig = b'ENCH'

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelStruct(b'ENDT', ['4I'], 'ench_type', 'ench_cost', 'ench_charge',
            'ench_auto_calc'),
        MelEffectsTes3(),
    )

#------------------------------------------------------------------------------
class MreFact(MelRecord):
    """Faction."""
    rec_sig = b'FACT'

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelFullTes3(),
        MelGroups('ranks', # always 10
            MelFixedString(b'RNAM', 'rank_name', 32),
        ),
        MelStruct(b'FADT', ['2i', '50I', '7i', 'I'], 'faction_attribute_1',
            'faction_attribute_2',
            # Rank 1 ----------------------------------------------------------
            'rank_1_attribute_1', 'rank_1_attribute_2', 'rank_1_skill_primary',
            'rank_1_skill_secondary', 'rank_1_reputation',
            # Rank 2 ----------------------------------------------------------
            'rank_2_attribute_1', 'rank_2_attribute_2', 'rank_2_skill_primary',
            'rank_2_skill_secondary', 'rank_2_reputation',
            # Rank 3 ----------------------------------------------------------
            'rank_3_attribute_1', 'rank_3_attribute_2', 'rank_3_skill_primary',
            'rank_3_skill_secondary', 'rank_3_reputation',
            # Rank 4 ----------------------------------------------------------
            'rank_4_attribute_1', 'rank_4_attribute_2', 'rank_4_skill_primary',
            'rank_4_skill_secondary', 'rank_4_reputation',
            # Rank 5 ----------------------------------------------------------
            'rank_5_attribute_1', 'rank_5_attribute_2', 'rank_5_skill_primary',
            'rank_5_skill_secondary', 'rank_5_reputation',
            # Rank 6 ----------------------------------------------------------
            'rank_6_attribute_1', 'rank_6_attribute_2', 'rank_6_skill_primary',
            'rank_6_skill_secondary', 'rank_6_reputation',
            # Rank 7 ----------------------------------------------------------
            'rank_7_attribute_1', 'rank_7_attribute_2', 'rank_7_skill_primary',
            'rank_7_skill_secondary', 'rank_7_reputation',
            # Rank 8 ----------------------------------------------------------
            'rank_8_attribute_1', 'rank_8_attribute_2', 'rank_8_skill_primary',
            'rank_8_skill_secondary', 'rank_8_reputation',
            # Rank 9 ----------------------------------------------------------
            'rank_9_attribute_1', 'rank_9_attribute_2', 'rank_9_skill_primary',
            'rank_9_skill_secondary', 'rank_9_reputation',
            # Rank 10 ---------------------------------------------------------
            'rank_10_attribute_1', 'rank_10_attribute_2',
            'rank_10_skill_primary', 'rank_10_skill_secondary',
            'rank_10_reputation',
            # Favored Skills --------------------------------------------------
            'favored_skill_1', 'favored_skill_2', 'favored_skill_3',
            'favored_skill_4', 'favored_skill_5', 'favored_skill_6',
            'favored_skill_7', 'hidden_from_pc'),
        MelGroups('relations', # bad names to match other games
            MelString(b'ANAM', 'faction'),
            MelSInt32(b'INTV', 'mod'),
        ),
    )

#------------------------------------------------------------------------------
class MreGlob(MelRecord):
    """Global."""
    rec_sig = b'GLOB'

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelFixedString(b'FNAM', 'global_format', 1),
        MelFloat(b'FLTV', 'global_value'),
    )

#------------------------------------------------------------------------------
class _MelGmstUnion(MelUnion):
    """Some GMSTs do not have one of the value subrecords - fall back to
    using the first letter of the NAME subrecord in those cases."""
    _fmt_mapping = {
        'f': b'FLTV',
        'i': b'INTV',
        's': b'STRV',
    }

    def _get_element_from_record(self, record):
        if not hasattr(record, self.decider_result_attr):
            format_char = record.mw_id[0] if record.mw_id else 'i'
            return self._get_element(self._fmt_mapping[format_char])
        return super()._get_element_from_record(record)

class MreGmst(MelRecord):
    """Game Setting."""
    melSet = MelSet(
        MelMWId(),
        _MelGmstUnion({
            b'FLTV': MelFloat(b'FLTV', 'value'),
            b'INTV': MelSInt32(b'INTV', 'value'),
            b'STRV': MelString(b'STRV', 'value'),
        }),
    )

#------------------------------------------------------------------------------
class MreInfo(MelRecord):
    """Dialog Response."""
    rec_sig = b'INFO'

    melSet = MelSet(
        MelString(b'INAM', 'reponse_id'),
        MelString(b'PNAM', 'prev_info'),
        MelString(b'NNAM', 'next_info'),
        MelStruct(b'DATA', ['B', '3s', 'I', '2b', 'B', 's'],
            'dialogue_type', 'unused1', 'disposition', 'dialogue_rank',
            'speaker_gender', 'player_faction_rank', 'unused2'),
        MelString(b'ONAM', 'speaker_name'),
        MelString(b'RNAM', 'speaker_race_name'),
        MelString(b'CNAM', 'speaker_class_name'),
        MelString(b'FNAM', 'speaker_faction_name'),
        MelString(b'ANAM', 'speaker_cell_name'),
        MelString(b'DNAM', 'player_faction_name'),
        MelString(b'SNAM', 'sound_name'),
        MelMWId(),
        MelDeleted(),
        MelUInt8(b'QSTN', 'quest_name'),
        MelUInt8(b'QSTF', 'quest_finished'),
        MelUInt8(b'QSTR', 'quest_restart'),
        MelGroups('conditions',
            MelString(b'SCVR', 'condition_string'),
            MelUnion({
                b'INTV': MelSInt32(b'INTV', 'comparison_value'),
                b'FLTV': MelFloat(b'FLTV', 'comparison_value'),
            }),
        ),
        MelString(b'BNAM', 'result_text'),
    )

#------------------------------------------------------------------------------
class MreIngr(MelRecord):
    """Ingredient."""
    rec_sig = b'INGR'

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelModel(),
        MelFullTes3(),
        MelStruct(b'IRDT', ['f', '13i'], 'ingr_weight', 'ingr_value',
            'effect_index_1', 'effect_index_2', 'effect_index_3',
            'effect_index_4', 'skill_id_1', 'skill_id_2', 'skill_id_3',
            'skill_id_4', 'attribute_id_1', 'attribute_id_2',
            'attribute_id_3', 'attribute_id_4'),
        MelScriptId(),
        MelIconTes3(),
    )

#------------------------------------------------------------------------------
class MreLand(MelRecord):
    """Landscape."""
    rec_sig = b'LAND'

    class _DataTypeFlags(Flags): ##: Shouldn't we set/use these?
        has_vertex_normals_or_height_map: bool
        has_vertex_colors: bool
        has_landscape_textures: bool
        user_created_or_edited: bool

    # No MelMWId, the land_x and land_y will have to substitute once we get
    # around to further MW support
    melSet = MelSet(
        MelStruct(b'INTV', ['2I'], 'land_x', 'land_y'),
        MelUInt32Flags(b'DATA', 'dt_flags', _DataTypeFlags),
        # These are all very large and too complex to manipulate -> MelBase
        MelBase(b'VNML', 'vertex_normals'),
        MelBase(b'VHGT', 'vertex_height_map'),
        MelBase(b'WNAM', 'world_map_painting'),
        MelBase(b'VCLR', 'vertex_colors'),
        MelBase(b'VTEX', 'vertex_textures'),
    )

#------------------------------------------------------------------------------
class MreLevc(AMreLeveledList):
    """Leveled Creature."""
    rec_sig = b'LEVC'
    _top_copy_attrs = ('lvl_chance_none',)
    _entry_copy_attrs = ('level', 'listId')

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
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
        MelDeleted(),
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
        MelDeleted(),
        MelModel(),
        MelFullTes3(),
        MelIconTes3(),
        MelStruct(b'LHDT', ['f', '2i', 'f', '4B', 'I'], 'weight', 'value',
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
        MelDeleted(),
        MelModel(),
        MelFullTes3(),
        MelStruct(b'LKDT', ['f', 'i', 'f', 'i'], 'lock_weight', 'lock_value',
            'lock_quality', 'lock_uses'),
        MelScriptId(),
        MelIconTes3(),
    )

#------------------------------------------------------------------------------
class MreLtex(MelRecord):
    """Landscape Texture."""
    rec_sig = b'LTEX'

    melSet = MelSet(
        MelDeleted(),
        MelMWId(),
        MelUInt32(b'INTV', 'ltex_index'),
        MelString(b'DATA', 'ltex_texture_name'),
    )

#------------------------------------------------------------------------------
class MreMgef(MelRecord):
    """Magic Effect."""
    rec_sig = b'MGEF'

    # No MelMWId - the identifier here will have to be the INDX instead
    ##: This will be a pain. They're hardcoded like in Oblivion, but use an int
    # index instead of a fourcc (i.e. the EDID in Oblivion).
    # Bad names to match other games (MGEF is scary since it's littered
    # implicity all over our codebase still)
    melSet = MelSet(
        MelUInt32(b'INDX', 'mgef_index'),
        MelStruct(b'MEDT', ['I', 'f', '4I', '3f'], 'school', 'base_cost',
            (MgefFlagsTes3, 'flags'), *color3_attrs('mgef_color'),
            'mgef_size_mult', 'mgef_speed_mult', 'mgef_size_cap'),
        MelIconTes3(),
        MelString(b'PTEX', 'particle_texture'),
        MelString(b'BSND', 'boltSound'),
        MelString(b'CSND', 'castingSound'),
        MelString(b'HSND', 'hitSound'),
        MelString(b'ASND', 'areaSound'),
        MelString(b'CVFX', 'casting_visual'),
        MelString(b'BVFX', 'bolt_visual'),
        MelString(b'HVFX', 'hit_visual'),
        MelString(b'AVFX', 'are_visual'),
        MelDescription(),
    )

#------------------------------------------------------------------------------
class MreMisc(MelRecord):
    """Misc. Item."""
    rec_sig = b'MISC'

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelModel(),
        MelFullTes3(),
        MelStruct(b'MCDT', ['f', 'i', 'I'], 'misc_weight', 'misc_value',
            'misc_is_key'),
        MelScriptId(),
        MelIconTes3(),
    )

#------------------------------------------------------------------------------
class MreNpc_(MelRecord):
    """Non-Player Character."""
    rec_sig = b'NPC_'

    class NpcFlags(Flags):
        npc_female: bool = flag(0)
        npc_essential: bool = flag(1)
        npc_respawn: bool = flag(2)
        npc_can_hold_items: bool = flag(3)
        npc_auto_calc: bool = flag(4)
        skeleton_blood: bool = flag(10)
        metal_blood: bool = flag(11)

    class MelNpcData(AMelLists):
        """Converts attributes and skills into lists."""
        _attr_indexes = {
            'npc_level': 0, 'attributes': slice(1, 9), 'skills': slice(9, 36),
            'unused2': 36, 'npc_health': 38, 'npc_magicka': 39,
            'npc_fatigue': 40, 'npc_disposition': 41, 'npc_reputation': 42,
            'npc_rank': 43, 'unused3': 44, 'npc_gold': 45,
        }

    class NpcDataDecider(SizeDecider):
        """At load time we can decide based on the subrecord size, but at dump
        time we need to consider the auto-calculate flag instead."""
        can_decide_at_dump = True

        def decide_dump(self, record):
            return 12 if record.npc_flags.npc_auto_calc else 52

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelModel(),
        MelFullTes3(),
        MelString(b'RNAM', 'race'),
        MelString(b'CNAM', 'npc_class'),
        MelString(b'ANAM', 'faction_name'),
        MelString(b'BNAM', 'head_body_part'),
        MelString(b'KNAM', 'hair_body_part'),
        MelScriptId(),
        MelUnion({
            12: MelStruct(b'NPDT', ['H', '3B', '3s', 'I'], 'npc_level',
                'npc_disposition', 'npc_reputation', 'npc_rank', 'unused1',
                'npc_gold'),
            52: MelNpcData(b'NPDT', ['H', '8B', '27B', 's', '3H', '3B', 's', 'I'],
                'npc_level', ('attributes', [0] * 8), ('skills', [0] * 27),
                'unused2', 'npc_health', 'npc_magicka', 'npc_fatigue',
                'npc_disposition', 'npc_reputation', 'npc_rank', 'unused3',
                'npc_gold'),
        }, decider=NpcDataDecider()),
        MelUInt32Flags(b'FLAG', 'npc_flags', NpcFlags),
        MelItems(),
        MelSpellsTes3(),
        MelAidt(),
        MelTravelServices(),
        MelAIPackagesTes3(),
    )

#------------------------------------------------------------------------------
class MrePgrd(MelRecord):
    """Path Grid."""
    rec_sig = b'PGRD'

    # This MelMWId is ignored, the pgrd_x and pgrd_y will have to substitute
    # once we get around to further MW support
    melSet = MelSet(
        MelStruct(b'DATA', ['2i', '2H'], 'pgrd_x', 'pgrd_y',
            'pgrd_granularity', 'point_count'),
        MelMWId(),
        # Could be loaded via MelArray, but are very big and not very useful
        MelBase(b'PGRP', 'point_array'),
        MelBase(b'PGRC', 'point_edges'),
    )

#------------------------------------------------------------------------------
class MreProb(MelRecord):
    """Probe."""
    rec_sig = b'PROB'

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelModel(),
        MelFullTes3(),
        MelStruct(b'PBDT', ['f', 'i', 'f', 'i'], 'probe_weight', 'probe_value',
            'probe_quality', 'probe_uses'),
        MelScriptId(),
        MelIconTes3(),
    )

#------------------------------------------------------------------------------
class MreRace(MelRecord):
    """Race."""
    rec_sig = b'RACE'

    class _RaceFlags(Flags):
        playable: bool
        beast_race: bool

    class _MelRaceRadt(AMelLists):
        _attr_indexes = {
            'skills': slice(14), 'maleStrength': 15, 'femaleStrength': 16,
            'maleIntelligence': 17, 'femaleIntelligence': 18,
            'maleWillpower': 19, 'femaleWillpower': 20, 'maleAgility': 21,
            'femaleAgility': 22, 'maleSpeed': 23, 'femaleSpeed': 24,
            'maleEndurance': 25, 'femaleEndurance': 26, 'malePersonality': 27,
            'femalePersonality': 28, 'maleLuck': 29, 'femaleLuck': 30,
            'maleHeight': 31, 'femaleHeight': 32, 'maleWeight': 33,
            'femaleWeight': 34,
        }

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelFullTes3(),
        # Bad names to match other games (race patchers)
        _MelRaceRadt(b'RADT', ['14i', '16i', '4f', 'I'], ('skills', [0] * 14),
            'maleStrength', 'femaleStrength', 'maleIntelligence',
            'femaleIntelligence', 'maleWillpower', 'femaleWillpower',
            'maleAgility', 'femaleAgility', 'maleSpeed', 'femaleSpeed',
            'maleEndurance', 'femaleEndurance', 'malePersonality',
            'femalePersonality', 'maleLuck', 'femaleLuck', 'maleHeight',
            'femaleHeight', 'maleWeight', 'femaleWeight',
            (_RaceFlags, 'race_flags')),
        MelSpellsTes3(),
        MelDescription(),
    )

#------------------------------------------------------------------------------
class MreRegn(MelRecord):
    """Region."""
    rec_sig = b'REGN'

    melSet = MelSet(
        MelDeleted(),
        MelMWId(),
        MelFullTes3(),
        MelTruncatedStruct(b'WEAT', ['10B'], 'chance_clear', 'chance_cloudy',
            'chance_foggy', 'chance_overcast', 'chance_rain',
            'chance_thunder', 'chance_ash', 'chance_blight',
            'chance_snow', 'chance_blizzard', old_versions={'8B'}),
        MelString(b'BNAM', 'sleep_creature'),
        MelColorO(),
        MelGroups('sound_chances',
            MelStruct(b'SNAM', ['32s', 'b'], (FixedString(32), 'sound_name'),
                'sound_chance'),
        ),
    )

#------------------------------------------------------------------------------
class MreRepa(MelRecord):
    """Repair Item."""
    rec_sig = b'REPA'

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelModel(),
        MelFullTes3(),
        MelStruct(b'RIDT', ['f', '2i', 'f'], 'repa_weight', 'repa_value',
            'repa_uses', 'repa_quality'),
        MelScriptId(),
        MelIconTes3(),
    )

#------------------------------------------------------------------------------
class MreScpt(MelRecord):
    """Script."""
    rec_sig = b'SCPT'

    melSet = MelSet(
        # Yes, the usual NAME sits in this subrecord instead. Additionally, the
        # CS lets you save it with up to 36 characters, at which point it
        # clobbers num_shorts...
        MelStruct(b'SCHD', ['32s', '5I'], (FixedString(32), 'mw_id'),
            'num_shorts', 'num_longs', 'num_floats', 'script_data_size',
            'local_var_size'),
        MelStrings(b'SCVR', 'script_variables'),
        MelBase(b'SCDT', 'compiled_script'),
        MelString(b'SCTX', 'script_source'),
    )

#------------------------------------------------------------------------------
class MreSkil(MelRecord):
    """Skill."""
    rec_sig = b'SKIL'

    # No MelMWId, this will have to use skill_id instead. Similar situation to
    # MGEF above
    melSet = MelSet(
        MelUInt32(b'INDX', 'skill_id'),
        MelStruct(b'SKDT', ['2I', '4f'], 'skill_attribute',
            'skill_type', 'skill_action_1', 'skill_action_2',
            'skill_action_3', 'skill_action_4'),
        MelDescription(),
    )

#------------------------------------------------------------------------------
class MreSndg(MelRecord):
    """Sound Generator."""
    rec_sig = b'SNDG'

    melSet = MelSet(
        MelMWId(),
        MelUInt32(b'DATA', 'sdng_type'),
        MelString(b'CNAM', 'creature_name'),
        MelString(b'SNAM', 'sound_name'),
        MelDeleted(),
    )

#------------------------------------------------------------------------------
class MreSoun(MelRecord):
    """Sound."""
    rec_sig = b'SOUN'

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelString(b'FNAM', 'sound_filename'),
        MelStruct(b'DATA', ['3B'], 'soun_volume', 'min_range', 'max_range'),
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
        MelDeleted(),
        MelFullTes3(),
        MelStruct(b'SPDT', ['I', 'i', 'I'], 'spell_type', 'spell_cost',
            (_SpellFlags, 'spell_flags')),
        MelEffectsTes3(),
    )

#------------------------------------------------------------------------------
class MreSscr(MelRecord):
    """Start Script."""
    rec_sig = b'SSCR'

    melSet = MelSet(
        MelDeleted(),
        MelString(b'DATA', 'numerical_id'),
        MelMWId(),
    )

#------------------------------------------------------------------------------
class MreStat(MelRecord):
    """Static."""
    rec_sig = b'STAT'

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelModel(),
    )

#------------------------------------------------------------------------------
class MreWeap(MelRecord):
    """Weapon."""
    rec_sig = b'WEAP'

    class _WeaponFlags(Flags):
        is_silver: bool
        ignore_normal_weapon_resistance: bool

    melSet = MelSet(
        MelMWId(),
        MelDeleted(),
        MelModel(),
        MelFullTes3(),
        MelStruct(b'WPDT', ['f', 'i', '2H', '2f', 'H', '6B', 'I'],
            'weapon_weight', 'weapon_value', 'weapon_type', 'weapon_health',
            'weapon_speed', 'weapon_reach', 'enchanting_charge',
            'chop_minimum', 'chop_maximum', 'slash_minimum', 'slash_maximum',
            'thrust_minimum', 'thrust_maximum',
            (_WeaponFlags, 'weapon_flags')),
        MelScriptId(),
        MelIconTes3(),
        MelEnchantmentTes3(),
    )
