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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Builds on the basic elements defined in base_elements.py to provide
definitions for some commonly needed subrecords."""
from itertools import chain
from typing import Type

from .advanced_elements import AttrValDecider, MelArray, MelTruncatedStruct, \
    MelUnion, FlagDecider, MelSorted, MelSimpleArray, MelCounter, \
    FidNotNullDecider, MelPartialCounter
from .basic_elements import MelBase, MelFid, MelGroup, MelGroups, MelLString, \
    MelNull, MelSequential, MelString, MelStruct, MelUInt32, MelOptStruct, \
    MelFloat, MelReadOnly, MelFids, MelUInt32Flags, MelUInt8Flags, MelSInt32, \
    MelStrings, MelUInt8, MelUInt16Flags
from .utils_constants import int_unpacker, FID, null1, ZERO_FID, gen_color, \
    gen_color3, gen_ambient_lighting
from ..bolt import Flags, encode, struct_pack, dict_sort, TrimmedFlags, \
    structs_cache
from ..exception import ModError

#------------------------------------------------------------------------------
class _MelCoed(MelOptStruct):
    """Handles the COED (Owner Data) subrecord used for inventory items and
    leveled lists since FO3."""
    ##: Needs custom unpacker to look at FormID type of owner. If item_owner is
    # an NPC then it is followed by a FormID. If item_owner is a faction then
    # it is followed by an signed integer or '=Iif' instead of '=IIf' - see
    # #282
    def __init__(self):
        super().__init__(b'COED', ['2I', 'f'], (FID, 'item_owner'),
            (FID, 'item_global'), 'item_condition')

#------------------------------------------------------------------------------
class AMelItems(MelSequential):
    """Base class for handling the CNTO (Items) subrecords defining items. Can
    handle all games since Oblivion via the two kwargs."""
    def __init__(self, *, with_coed=True, with_counter=True):
        items_elements = [MelStruct(b'CNTO', ['I', 'i'], (FID, 'item'),
            'count')]
        items_sort_attrs = ('item', 'count')
        if with_coed:
            items_elements.append(_MelCoed())
            items_sort_attrs += ('item_condition', 'item_owner', 'item_global')
        final_elements = [MelSorted(MelGroups('items', *items_elements),
            sort_by_attrs=items_sort_attrs)]
        if with_counter:
            final_elements.insert(0, MelCounter(
                MelUInt32(b'COCT', 'item_count'), counts='items'))
        super().__init__(*final_elements)

#------------------------------------------------------------------------------
class AMelLLItems(MelSequential):
    """Base class for handling the LVLO (and LLCT) subrecords defining leveled
    list items. Can handle all games since Oblivion via the two kwargs."""
    def __init__(self, lvl_element: MelBase, *, with_coed=True,
            with_counter=True):
        lvl_elements = [lvl_element]
        lvl_sort_attrs = ('level', 'listId', 'count')
        if with_coed:
            lvl_elements.append(_MelCoed())
            lvl_sort_attrs += ('item_condition', 'item_owner', 'item_global')
        final_elements = [MelSorted(MelGroups('entries', *lvl_elements),
            sort_by_attrs=lvl_sort_attrs)]
        if with_counter:
            final_elements.insert(0, MelCounter(
                MelUInt8(b'LLCT', 'entry_count'), counts='entries'))
        super().__init__(*final_elements)

#------------------------------------------------------------------------------
class MelActiFlags(MelUInt16Flags):
    """Handles the ACTI subrecord FNAM (Flags). Note that this subrecord is
    inherited by a couple other records too."""
    _acti_flags = Flags.from_names(
        (0, 'no_displacement'),
        (1, 'ignored_by_sandbox'),
        (4, 'is_a_radio'), # Introduced in FO4
    )

    def __init__(self):
        super().__init__(b'FNAM', 'acti_flags', self._acti_flags)

#------------------------------------------------------------------------------
class MelActionFlags(MelUInt32Flags):
    """XACT (Action Flags) subrecord for REFR records."""
    _act_flags = Flags.from_names('act_use_default', 'act_activate',
                                  'act_open', 'act_open_by_default')

    def __init__(self):
        super().__init__(b'XACT', 'action_flags', self._act_flags)

    ##: HACK - right solution is having None as the default for flags combined
    # with the ability to mark subrecords as required (e.g. for QSDT)
    def pack_subrecord_data(self, record):
        flag_val = getattr(record, self.attr)
        return self.packer(
            flag_val) if flag_val != self._flag_default else None

#------------------------------------------------------------------------------
class MelActivateParents(MelGroup):
    """XAPD/XAPR (Activate Parents) subrecords for REFR records."""
    _ap_flags = TrimmedFlags.from_names('parent_activate_only')

    def __init__(self):
        super().__init__('activate_parents',
            MelUInt8Flags(b'XAPD', 'activate_parent_flags', self._ap_flags),
            MelSorted(MelGroups('activate_parent_refs',
                MelStruct(b'XAPR', ['I', 'f'], (FID, 'ap_reference'),
                    'ap_delay'),
            ), sort_by_attrs='ap_reference'),
        )

#------------------------------------------------------------------------------
class MelActorSounds(MelSorted):
    """Handles the CSDT/CSDI/CSDC subrecord complex used by CREA records in
    TES4/FO3/FNV and NPC_ records in TES5."""
    def __init__(self):
        super().__init__(MelGroups('sounds',
            MelUInt32(b'CSDT', 'type'),
            MelSorted(MelGroups('sound_types',
                MelFid(b'CSDI', 'sound'),
                MelUInt8(b'CSDC', 'chance'),
            ), sort_by_attrs='sound'),
        ), sort_by_attrs='type')

#------------------------------------------------------------------------------
class MelAddnDnam(MelStruct):
    """Handles the ADDN subrecord DNAM (Data)."""
    def __init__(self):
        # addon_flags is 2 unknown bytes in FO3/FNV, but decoding it as a short
        # can't hurt and is much simpler
        super().__init__(b'DNAM', ['2H'], 'master_particle_system_cap',
            'addon_flags') # not really flags, behaves more like an enum

#------------------------------------------------------------------------------
class MelAlchEnit(MelStruct):
    """Handles the ALCH subrecord ENIT (Effect Data) since Skyrim."""
    _enit_flags = Flags.from_names(
        (0,  'alch_no_auto_calc'),
        (1,  'alch_is_food'),
        (16, 'medicine'),
        (17, 'poison'),
    )

    def __init__(self):
        super().__init__(b'ENIT', ['i', '2I', 'f', 'I'], 'value',
            (self._enit_flags, 'flags'), (FID, 'addiction'), 'addictionChance',
            (FID, 'soundConsume'))

#------------------------------------------------------------------------------
class MelAnimations(MelSorted): ##: case insensitive
    """Handles the common KFFZ (Animations) subrecord."""
    def __init__(self):
        super().__init__(MelStrings(b'KFFZ', 'animations'))

#------------------------------------------------------------------------------
class MelArmaShared(MelSequential):
    """Handles the ARMA subrecords DNAM, MOD2-MOD5, NAM0-NAM3, MODL, SNDD and
    ONAM."""
    _weigth_slider_flags = Flags.from_names((1, 'slider_enabled'))

    def __init__(self, mel_model: Type[MelBase]):
        super().__init__(
            MelStruct(b'DNAM', ['4B', '2s', 'B', 's', 'f'],
                'male_priority', 'female_priority',
                (self._weigth_slider_flags, 'slider_flags_m'),
                (self._weigth_slider_flags, 'slider_flags_f'), 'unknown_dnam1',
                'detection_sound_value', 'unknown_dnam2', 'weapon_adjust'),
            mel_model(b'MOD2', 'male_model'),
            mel_model(b'MOD3', 'female_model'),
            mel_model(b'MOD4', 'male_model_1st'),
            mel_model(b'MOD5', 'female_model_1st'),
            MelFid(b'NAM0', 'skin0'),
            MelFid(b'NAM1', 'skin1'),
            MelFid(b'NAM2', 'skin2'),
            MelFid(b'NAM3', 'skin3'),
            MelSorted(MelFids('additional_races', MelFid(b'MODL'))),
            MelFid(b'SNDD', 'footstep_sound'),
            MelFid(b'ONAM', 'art_object'),
        )

#------------------------------------------------------------------------------
class MelArtType(MelUInt32):
    """Handles the ARTO subrecord DNAM (Art Type)."""
    def __init__(self):
        super().__init__(b'DNAM', 'art_type')

#------------------------------------------------------------------------------
class MelAspcBnam(MelFid):
    """Handles the ASPC subrecord BNAM (Environment Type (reverb))."""
    def __init__(self):
        super().__init__(b'BNAM', 'environment_type')

#------------------------------------------------------------------------------
class MelAspcRdat(MelFid):
    """Handles the ASPC subrecord RDAT (Use Sound From Region (Interiors
    Only))."""
    def __init__(self):
        super().__init__(b'RDAT', 'use_sound_from_region')

#------------------------------------------------------------------------------
class MelAttx(MelLString):
    """Handles the common ATTX (Activate Text Override) subrecord. Skyrim uses
    an RNAM signature instead."""
    def __init__(self, mel_sig=b'ATTX'):
        super().__init__(mel_sig, 'activate_text_override')

#------------------------------------------------------------------------------
class MelBamt(MelFid):
    """Handles the common BAMT (Alternate Block Material) subrecord."""
    def __init__(self):
        super().__init__(b'BAMT', 'alternate_block_material')

#------------------------------------------------------------------------------
class MelBids(MelFid):
    """Handles the common BIDS (Block Bash Impact Data Set) subrecord."""
    def __init__(self):
        super().__init__(b'BIDS', 'block_bash_impact_dataset')

#------------------------------------------------------------------------------
class MelBodyParts(MelSorted):
    """Handles the common NIFZ (Body Parts) subrecord."""
    def __init__(self): ##: case insensitive
        super().__init__(MelStrings(b'NIFZ', 'bodyParts'))

#------------------------------------------------------------------------------
class MelBookDescription(MelLString):
    """Handles the BOOK subrecord CNAM (Description)."""
    def __init__(self):
        super().__init__(b'CNAM', 'description')

#------------------------------------------------------------------------------
class MelBookText(MelLString):
    """Handles the BOOK subrecord DESC (Book Text), except in Morrowind, where
    TEXT is used."""
    def __init__(self, txt_sig=b'DESC'):
        super().__init__(txt_sig, 'book_text')

#------------------------------------------------------------------------------
class MelBounds(MelGroup):
    """Wrapper around MelGroup for the common task of defining OBND - Object
    Bounds. Uses MelGroup to avoid merging them when importing."""
    def __init__(self):
        super().__init__('bounds',
            MelStruct(b'OBND', ['6h'], 'boundX1', 'boundY1', 'boundZ1',
                'boundX2', 'boundY2', 'boundZ2'),
        )

#------------------------------------------------------------------------------
class MelClmtTiming(MelStruct):
    """Handles the CLMT subrecord TNAM (Timing)."""
    def __init__(self):
        super().__init__(b'TNAM', ['6B'], 'rise_begin', 'rise_end',
            'set_begin', 'set_end', 'volatility', 'phase_length')

#------------------------------------------------------------------------------
class MelClmtTextures(MelSequential):
    """Handles the CLMT subrecords FNAM and GNAM."""
    def __init__(self):
        super().__init__(
            MelString(b'FNAM', 'sun_texture'),
            MelString(b'GNAM', 'sun_glare_texture'),
        )

#------------------------------------------------------------------------------
class MelClmtWeatherTypes(MelSorted):
    """Handles the CLMT subrecord WLST (Weather Types)."""
    def __init__(self, *, with_global=True):
        weather_fmt = ['I', 'i']
        weather_elements = [(FID, 'weather'), 'chance']
        if with_global:
            weather_fmt.append('I')
            weather_elements.append((FID, 'global'))
        super().__init__(MelArray('weather_types',
            MelStruct(b'WLST', weather_fmt, *weather_elements),
        ), sort_by_attrs='weather')

#------------------------------------------------------------------------------
class MelCobjOutput(MelSequential):
    """Handles the COBJ subrecords CNAM and BNAM."""
    def __init__(self):
        super().__init__(
            MelFid(b'CNAM', 'created_object'),
            MelFid(b'BNAM', 'workbench_keyword'),
        )

#------------------------------------------------------------------------------
class MelColor(MelStruct):
    """Required Color."""
    def __init__(self, color_sig=b'CNAM'):
        super().__init__(color_sig, ['4B'], 'red', 'green', 'blue',
            'unused_alpha')

#------------------------------------------------------------------------------
class MelColorInterpolator(MelArray):
    """Wrapper around MelArray that defines a time interpolator - an array
    of five floats, where each entry in the array describes a point on a curve,
    with 'time' as the X axis and 'red', 'green', 'blue' and 'alpha' as the Y
    axis."""
    def __init__(self, interp_sig, attr):
        super().__init__(attr, MelStruct(interp_sig, ['5f'], 'time', 'red',
            'green', 'blue', 'alpha'))

#------------------------------------------------------------------------------
class MelColorO(MelOptStruct):
    """Optional Color."""
    def __init__(self, color_sig=b'CNAM'):
        super().__init__(color_sig, ['4B'], 'red', 'green', 'blue',
            'unused_alpha')

#------------------------------------------------------------------------------
class MelContData(MelStruct):
    """Handles the CONT subrecord DATA (Data)."""
    # Flags 1 & 3 introduced in Skyrim, treat as unknown for earlier games
    _cont_flags = Flags.from_names('allow_sounds_when_animation',
        'cont_respawns', 'show_owner')

    def __init__(self):
        super().__init__(b'DATA', ['B', 'f'], (self._cont_flags, 'cont_flags'),
            'cont_weight')

#------------------------------------------------------------------------------
class MelCpthShared(MelSequential):
    """Handles the CPTH subrecords ANAM, DATA and SNAM. Identical between all
    games' CPTH records."""
    def __init__(self):
        super().__init__(
            MelSimpleArray('related_camera_paths', MelFid(b'ANAM')),
            MelUInt8(b'DATA', 'camera_zoom'),
            MelFids('camera_shots', MelFid(b'SNAM')),
        ),

#------------------------------------------------------------------------------
class MelDalc(MelTruncatedStruct):
    """Handles the common DALC (Directional Ambient Lighting Colors)
    subrecord."""
    def __init__(self):
        super().__init__(b'DALC', ['28B', 'f'],
            *gen_ambient_lighting(attr_prefix='dalc'), old_versions={'24B'})

#------------------------------------------------------------------------------
class MelDebrData(MelStruct):
    """Handles the DEBR subrecord DATA (Data)."""
    _debr_flags = Flags.from_names('has_collision_data', 'collision')

    def __init__(self):
        # Format doesn't matter, struct.Struct('') works! ##: MelStructured
        super().__init__(b'DATA', [], 'debr_percentage', ('modPath', null1),
            (self._debr_flags, 'debr_flags'))

    @staticmethod
    def _expand_formats(elements, struct_formats):
        return [0] * len(elements)

    def load_mel(self, record, ins, sub_type, size_, *debug_strs,
            __unpack_byte=structs_cache['B'].unpack):
        byte_data = ins.read(size_, *debug_strs)
        record.debr_percentage = __unpack_byte(byte_data[0:1])[0]
        record.modPath = byte_data[1:-2]
        if byte_data[-2:-1] != null1:
            raise ModError(ins.inName, f'Unexpected subrecord: {debug_strs}')
        record.debr_flags = self._debr_flags(__unpack_byte(byte_data[-1:])[0])

    def pack_subrecord_data(self, record, *, __pack=structs_cache['B'].pack):
        return b''.join([__pack(record.debr_percentage), record.modPath, null1,
                         __pack(record.debr_flags.dump())])

#------------------------------------------------------------------------------
class MelDecalData(MelOptStruct):
    """Handles the common DODT (Decal Data) subrecord."""
    _decal_flags = TrimmedFlags.from_names(
        'parallax',
        'alpha_blending',
        'alpha_testing',
        'no_subtextures', # since Skyrim
    )

    def __init__(self):
        super().__init__(b'DODT', ['7f', 'B', 'B', '2s', '3B', 's'],
            'decal_min_width', 'decal_max_width', 'decal_min_height',
            'decal_max_height', 'decal_depth', 'decal_shininess',
            'decal_parallax_scale', 'decal_parallax_passes',
            (self._decal_flags, 'decal_flags'), 'decal_unused1',
            *gen_color('decal_color'))

#------------------------------------------------------------------------------
class MelDescription(MelLString):
    """Handles the description (DESC) subrecord."""
    def __init__(self):
        super().__init__(b'DESC', 'description')

#------------------------------------------------------------------------------
class MelDoorFlags(MelUInt8Flags):
    _door_flags = Flags.from_names(
        'oblivion_gate' # Oblivion only
        'automatic',
        'hidden',
        'minimal_use',
        'sliding_door', # since FO3
        'do_not_open_in_combat_search', # since Skyrim
        'no_to_text', # since FO4
    )

    def __init__(self):
        super().__init__(b'FNAM', 'door_flags', self._door_flags)

#------------------------------------------------------------------------------
class MelEdid(MelString):
    """Handles an Editor ID (EDID) subrecord."""
    def __init__(self):
        super().__init__(b'EDID', 'eid')

#------------------------------------------------------------------------------
class MelEnableParent(MelOptStruct):
    """Enable Parent struct for a reference record (REFR, ACHR, etc.)."""
    # The pop_in flag doesn't technically exist for all XESP subrecords, but it
    # will just be ignored for those where it doesn't exist, so no problem.
    _parent_flags = Flags.from_names('opposite_parent', 'pop_in')

    def __init__(self):
        super().__init__(b'XESP', ['I', 'B', '3s'], (FID, 'ep_reference'),
            (self._parent_flags, 'parent_flags'), 'xesp_unused')

#------------------------------------------------------------------------------
class MelEnchantment(MelFid):
    """Represents the common enchantment/object effect subrecord."""
    def __init__(self, ench_sig=b'EITM'):
        super().__init__(ench_sig, 'enchantment')

#------------------------------------------------------------------------------
class MelEquipmentType(MelFid):
    """Handles the common ETYP (Equipment Type) subrecord."""
    def __init__(self):
        super().__init__(b'ETYP', 'equipment_type')

#------------------------------------------------------------------------------
class MelEqupPnam(MelSimpleArray):
    """Handles the EQUP subrecord PNAM (Slot Parents)."""
    def __init__(self):
        super().__init__('slot_parents', MelFid(b'PNAM'))

#------------------------------------------------------------------------------
class MelFactFlags(MelUInt32Flags):
    """Handles the FACT subrecord DATA (Flags) since Skyrim."""
    _fact_flags = Flags.from_names(
        ( 0, 'hidden_from_pc'),
        ( 1, 'special_combat'),
        ( 6, 'track_crime'),
        ( 7, 'ignore_crimes_murder'),
        ( 8, 'ignore_crimes_assault'),
        ( 9, 'ignore_crimes_stealing'),
        (10, 'ignore_crimes_trespass'),
        (11, 'do_not_report_crimes_against_members'),
        (12, 'crime_gold_use_defaults'),
        (13, 'ignore_crimes_pickpocket'),
        (14, 'allow_sell'), # also called 'vendor'
        (15, 'can_be_owner'),
        (16, 'ignore_crimes_werewolf'),
    )

    def __init__(self):
        super().__init__(b'DATA', 'fact_flags', self._fact_flags),

#------------------------------------------------------------------------------
class MelFactFids(MelSequential):
    """Handles the FACT subrecords JAIL, WAIT, STOL, PCLN, CRGR and JOUT."""
    def __init__(self):
        super().__init__(
            MelFid(b'JAIL', 'exterior_jail_marker'),
            MelFid(b'WAIT', 'follower_wait_marker'),
            MelFid(b'STOL', 'stolen_goods_container'),
            MelFid(b'PLCN', 'player_inventory_container'),
            MelFid(b'CRGR', 'shared_crime_faction_list'),
            MelFid(b'JOUT', 'jail_outfit'),
        )

#------------------------------------------------------------------------------
class MelFactRanks(MelSorted):
    """Handles the FACT subrecords RNAM, MNAM, FNAM and INAM."""
    def __init__(self):
        super().__init__(MelGroups('ranks',
            # Unsigned since Skyrim, but no one's going to use ranks >2 billion
            MelSInt32(b'RNAM', 'rank_level'),
            MelLString(b'MNAM', 'male_title'),
            MelLString(b'FNAM', 'female_title'),
            MelString(b'INAM', 'insignia_path'),
        ), sort_by_attrs='rank_level')

#------------------------------------------------------------------------------
class MelFactVendorInfo(MelSequential):
    """Handles the FACT subrecords VEND, VENC and VENV."""
    def __init__(self):
        super().__init__(
            MelFid(b'VEND', 'vendor_buy_sell_list'),
            MelFid(b'VENC', 'merchant_container'),
            # 'vv_only_buys_stolen_items' and 'vv_not_sell_buy' are actually
            # bools, vv means 'vendor value' (which is what this struct is
            # about)
            MelStruct(b'VENV', ['3H', '2s', '2B', '2s'], 'vv_start_hour',
                'vv_end_hour', 'vv_radius', 'vv_unknown1',
                'vv_only_buys_stolen_items', 'vv_not_sell_buy', 'vv_unknown2'),
        )

#------------------------------------------------------------------------------
class MelFactions(MelSorted):
    """Handles the common SNAM (Factions) subrecord."""
    def __init__(self):
        super().__init__(MelGroups('factions',
            MelStruct(b'SNAM', ['I', 'B', '3s'], (FID, 'faction'), 'rank',
                ('unused1', b'ODB')),
        ), sort_by_attrs='faction')

#------------------------------------------------------------------------------
class MelFlstFids(MelFids):
    """Handles the FLST subrecord LNAM (FormIDs)."""
    def __init__(self):
        super().__init__('formIDInList', MelFid(b'LNAM')) # Do *not* sort!

#------------------------------------------------------------------------------
class MelFull(MelLString):
    """Handles a name (FULL) subrecord."""
    def __init__(self):
        super().__init__(b'FULL', 'full')

#------------------------------------------------------------------------------
class MelFurnMarkerData(MelSequential):
    """Handles the FURN subrecords ENAM, NAM0, FNMK (Skyrim only), FNPR and
    XMRK."""
    _entry_points = Flags.from_names('entry_point_front', 'entry_point_behind',
        'entry_point_right', 'entry_point_left', 'entry_point_up')

    def __init__(self, *, with_marker_keyword=False):
        marker_elements = [
            # Unsigned in Skyrim, but no one's going to use >2 billion indices
            MelSInt32(b'ENAM', 'furn_marker_index'),
            MelStruct(b'NAM0', ['2s', 'H'], 'furn_marker_unknown',
                (self._entry_points, 'furn_marker_disabled_entry_points')),
        ]
        if with_marker_keyword:
            marker_elements.append(MelFid(b'FNMK', 'furn_marker_keyword'))
        super().__init__(
            MelGroups('furn_markers', *marker_elements),
            MelGroups('marker_entry_points',
                MelStruct(b'FNPR', ['2H'], 'furn_marker_type',
                    (self._entry_points, 'furn_marker_entry_points')),
            ),
            MelString(b'XMRK', 'marker_model'),
        )

#------------------------------------------------------------------------------
class MelGrasData(MelStruct):
    """Handles the GRAS subrecord DATA (Data)."""
    _gras_flags = Flags.from_names('vertex_lighting', 'uniform_scaling',
        'fit_to_slope')

    def __init__(self):
        super().__init__(b'DATA', ['3B', 's', 'H', '2s', 'I', '4f', 'B', '3s'],
            'gras_density', 'gras_min_slope', 'gras_max_slope',
            'gras_unknown1', 'units_from_water', 'gras_unknown2',
            'units_from_water_type', 'position_range', 'height_range',
            'color_range', 'wave_period', (self._gras_flags, 'gras_flags'),
            'gras_unknown3')

#------------------------------------------------------------------------------
class MelHairFlags(MelUInt8Flags):
    """Handles the HAIR subrecord DATA (Flags)."""
    _hair_flags = Flags.from_names('playable', 'not_male', 'not_female',
        'hair_fixed')

    def __init__(self):
        super().__init__(b'DATA', 'flags', self._hair_flags)

#------------------------------------------------------------------------------
class MelHdptShared(MelSequential):
    """Handles the HDPT subrecords DATA, PNAM, HNAM, NAM0, NAM1, TNAM, CNAM and
    RNAM."""
    _hdpt_flags = Flags.from_names(
        'playable',
        'not_female',
        'not_male',
        'is_extra_part',
        'use_solid_tint',
        'uses_body_texture', # since FO4
    )

    def __init__(self):
        super().__init__(
            MelUInt8Flags(b'DATA', 'flags', self._hdpt_flags),
            MelUInt32(b'PNAM', 'hdpt_type'),
            MelSorted(MelFids('extra_parts', MelFid(b'HNAM'))),
            MelGroups('head_parts',
                MelUInt32(b'NAM0', 'head_part_type'),
                MelString(b'NAM1', 'head_part_filename'),
            ),
            MelFid(b'TNAM', 'hdpt_texture_set'),
            MelFid(b'CNAM', 'hdpt_color'),
            MelFid(b'RNAM', 'valid_races'),
        )

#------------------------------------------------------------------------------
class MelIcons(MelSequential):
    """Handles icon subrecords. Defaults to ICON and MICO, with attribute names
    'iconPath' and 'smallIconPath', since that's most common."""
    def __init__(self, icon_attr='iconPath', mico_attr='smallIconPath',
            icon_sig=b'ICON', mico_sig=b'MICO'):
        """Creates a new MelIcons with the specified attributes.

        :param icon_attr: The attribute to use for the ICON subrecord. If
            falsy, this means 'do not include an ICON subrecord'.
        :param mico_attr: The attribute to use for the MICO subrecord. If
            falsy, this means 'do not include a MICO subrecord'."""
        final_elements = []
        if icon_attr: final_elements.append(MelString(icon_sig, icon_attr))
        if mico_attr: final_elements.append(MelString(mico_sig, mico_attr))
        super().__init__(*final_elements)

class MelIcons2(MelIcons):
    """Handles ICO2 and MIC2 subrecords. Defaults to attribute names
    'femaleIconPath' and 'femaleSmallIconPath', since that's most common."""
    def __init__(self, ico2_attr='femaleIconPath',
            mic2_attr='femaleSmallIconPath'):
        super().__init__(icon_attr=ico2_attr, mico_attr=mic2_attr,
            icon_sig=b'ICO2', mico_sig=b'MIC2')

class MelIcon(MelIcons):
    """Handles a standalone ICON subrecord, i.e. without any MICO subrecord."""
    def __init__(self, icon_attr='iconPath'):
        super().__init__(icon_attr=icon_attr, mico_attr='')

class MelIco2(MelIcons2):
    """Handles a standalone ICO2 subrecord, i.e. without any MIC2 subrecord."""
    def __init__(self, ico2_attr):
        super().__init__(ico2_attr=ico2_attr, mic2_attr='')

#------------------------------------------------------------------------------
class MelIdleAnimations(MelSimpleArray):
    """Handles the IDLM and PACK subrecord IDLA (Animations)."""
    def __init__(self):
        super().__init__('idle_animations', MelFid(b'IDLA'))

#------------------------------------------------------------------------------
class MelIdleAnimationCount(MelCounter):
    """Handles the newer version of the IDLM and PACK subrecord IDLC (Animation
    Count), which lacks the unused padding bytes."""
    def __init__(self):
        super().__init__(MelUInt8(b'IDLC', 'idle_animation_count'),
            counts='idle_animations')

#------------------------------------------------------------------------------
class MelIdleAnimationCountOld(MelPartialCounter):
    """Handles the older version of the IDLM and PACK subrecord IDLC (Animation
    Count), which contained three unused padding bytes."""
    def __init__(self):
        super().__init__(MelTruncatedStruct(b'IDLC', ['B', '3s'],
            'idle_animation_count', 'unused1', old_versions={'B'}),
            counters={'idle_animation_count': 'idle_animations'}),

#------------------------------------------------------------------------------
class MelIdleData(MelStruct):
    """Handles the IDLE subrecord DATA (Data) since Skyrim."""
    _idle_flags = TrimmedFlags.from_names('idle_parent', 'idle_sequence',
        'no_attacking', 'idle_blocking')

    def __init__(self):
        super().__init__(b'DATA', ['4B', 'H'], 'looping_min', 'looping_max',
            (self._idle_flags, 'idle_flags'), 'animation_group_section',
            'replay_delay'),

#------------------------------------------------------------------------------
class MelIdleEnam(MelString):
    """Handles the IDLE subrecord ENAM (Animation Event)."""
    def __init__(self):
        super().__init__(b'ENAM', 'animation_event'),

#------------------------------------------------------------------------------
class MelIdleRelatedAnims(MelStruct):
    """Handles the IDLE subrecord Related Idle Animations."""
    def __init__(self, ra_sig=b'ANAM'):
        super().__init__(ra_sig, ['2I'], (FID, 'ra_parent'),
            (FID, 'ra_previous_sibling'))

#------------------------------------------------------------------------------
class MelIdleTimerSetting(MelFloat):
    """Handles the common IDLT subrecord (Idle Timer Setting)."""
    def __init__(self):
        super().__init__(b'IDLT', 'idle_timer_setting')

#------------------------------------------------------------------------------
class MelIdlmFlags(MelUInt8Flags):
    """Handles the IDLM subrecord IDLF (Flags)."""
    _idlm_flags = Flags.from_names(
        (0, 'run_in_sequence'),
        (2, 'do_once'),
        (4, 'ignored_by_sandbox'), # since Skyrim
    )

    def __init__(self):
        super().__init__(b'IDLF', 'idlm_flags', self._idlm_flags)

#------------------------------------------------------------------------------
class MelImageSpaceMod(MelFid):
    """Handles the common MNAM (Image Space Modifer) subrecord."""
    def __init__(self):
        super().__init__(b'MNAM', 'image_space_modifier')

#------------------------------------------------------------------------------
class MelImgsCinematic(MelStruct):
    """Handles the IMGS subrecord CNAM (Cinematic)."""
    def __init__(self):
        super().__init__(b'CNAM', ['3f'], 'cinematic_saturation',
            'cinematic_brightness', 'cinematic_contrast')

#------------------------------------------------------------------------------
class MelImgsTint(MelStruct):
    """Handles the IMGS subrecord TNAM (Tint)."""
    def __init__(self):
        super().__init__(b'TNAM', ['4f'], 'tint_amount',
            *gen_color3('tint_color'))

#------------------------------------------------------------------------------
class MelImpactDataset(MelFid):
    """Handles various common Impact Dataset subrecords."""
    def __init__(self, ids_sig: bytes):
        super().__init__(ids_sig, 'impact_dataset')

#------------------------------------------------------------------------------
class MelInfoResponsesFo3(MelGroups):
    """Handles the INFO subrecords TRDT, NAM1-3, SNAM and LNAM in FO3, FNV and
    TES5."""
    def __init__(self):
        super().__init__('info_responses',
            MelStruct(b'TRDT', ['I', 'i', '4s', 'B', '3s', 'I', 'B', '3s'],
                'rd_emotion_type', 'rd_emotion_value', 'rd_unused1',
                'rd_response_number', 'rd_unused2', (FID, 'rd_sound'),
                'rd_use_emotion_animation', 'rd_unused3'),
            MelLString(b'NAM1', 'response_text'),
            MelString(b'NAM2', 'script_notes'),
            MelString(b'NAM3', 'response_edits'),
            MelFid(b'SNAM', 'idle_animations_speaker'),
            MelFid(b'LNAM', 'idle_animations_listener'),
        )

#------------------------------------------------------------------------------
class MelIngredient(MelFid):
    """Handles the common PFIG (Ingredient) subrecord."""
    def __init__(self):
        super().__init__(b'PFIG', 'ingredient')

#------------------------------------------------------------------------------
class MelIngrEnit(MelStruct):
    """Handles the INGR subrecord ENIT (Effect Data)."""
    _enit_flags = Flags.from_names(
        (0, 'ingr_no_auto_calc'),
        (1, 'food_item'),
        (8, 'references_persist'),
    )

    def __init__(self):
        super().__init__(b'ENIT', ['i', 'I'], 'ingredient_value',
            (self._enit_flags, 'flags'))

#------------------------------------------------------------------------------
class MelInteractionKeyword(MelFid):
    """Handles the common KNAM (Interaction Keyword) subrecord."""
    def __init__(self):
        super().__init__(b'KNAM', 'interaction_keyword')

#------------------------------------------------------------------------------
class MelInventoryArt(MelFid):
    """Handles the BOOK subrecord INAM (Inventory Art)."""
    def __init__(self):
        super().__init__(b'INAM', 'inventory_art')

#------------------------------------------------------------------------------
class MelIpctHazard(MelFid):
    """Handles the IPCT subrecord NAM2 (Hazard)."""
    def __init__(self):
        super().__init__(b'NAM2', 'ipct_hazard')

#------------------------------------------------------------------------------
class MelIpctSounds(MelSequential):
    """Handles the IPCT subrecords SNAM and NAM1."""
    def __init__(self):
        super().__init__(
            MelSound(),
            MelFid(b'NAM1', 'ipct_sound2'),
        )

#------------------------------------------------------------------------------
class MelIpctTextureSets(MelSequential):
    """Handles the IPCT subrecords DNAM and ENAM."""
    def __init__(self, *, with_secondary=True):
        tex_sets = [MelFid(b'DNAM', 'ipct_texture_set')]
        if with_secondary:
            tex_sets.append(MelFid(b'ENAM', 'secondary_texture_set'))
        super().__init__(*tex_sets)

#------------------------------------------------------------------------------
class MelIpdsPnam(MelSorted):
    """Handles the IPDS subrecord PNAM (Data)."""
    def __init__(self):
        super().__init__(MelGroups('impact_data',
            MelStruct(b'PNAM', ['2I'], (FID, 'ipds_material'),
                (FID, 'ipds_impact')),
        ), sort_by_attrs='ipds_material')

#------------------------------------------------------------------------------
class MelKeywords(MelSequential):
    """Handles the KSIZ/KWDA (Keywords) subrecords."""
    def __init__(self):
        super().__init__(
            MelCounter(MelUInt32(b'KSIZ', 'keyword_count'), counts='keywords'),
            MelSorted(MelSimpleArray('keywords', MelFid(b'KWDA'))),
        )

#------------------------------------------------------------------------------
class MelLandMpcd(MelGroups):
    """Handles the LAND subrecord MPCD (Unknown)."""
    def __init__(self):
        super().__init__('unknown_mpcd',
            MelBase(b'MPCD', 'unknown1'),
        )

#------------------------------------------------------------------------------
class MelLandShared(MelSequential):
    """Handles the LAND subrecords shared by all games."""
    _land_flags = Flags.from_names(
        (0,  'has_vertex_normals_height_map'),
        (1,  'has_vertex_colors'),
        (2,  'has_layers'),
        (10, 'has_mpcd'), # since Skyrim
    )

    def __init__(self):
        super().__init__(
            MelUInt32Flags(b'DATA', 'land_flags', self._land_flags),
            MelBase(b'VNML', 'vertex_normals'),
            MelBase(b'VHGT', 'vertex_height_map'),
            MelBase(b'VCLR', 'vertex_colors'),
            MelSorted(MelGroups('layers',
                # Start a new layer each time we hit one of these
                MelUnion({
                    b'ATXT': MelStruct(b'ATXT', ['I', 'B', 's', 'h'],
                        (FID, 'atxt_texture'), 'quadrant', 'unknown', 'layer'),
                    b'BTXT': MelStruct(b'BTXT', ['I', 'B', 's', 'h'],
                        (FID, 'btxt_texture'), 'quadrant', 'unknown', 'layer'),
                }),
                # VTXT only exists for ATXT layers, i.e. if ATXT's FormID is
                # valid
                MelUnion({
                    True:  MelBase(b'VTXT', 'alpha_layer_data'), # sorted
                    False: MelNull(b'VTXT'),
                }, decider=FidNotNullDecider('atxt_texture')),
            ), sort_by_attrs=('quadrant', 'layer')),
            MelSimpleArray('vertex_textures', MelFid(b'VTEX')),
        )

#------------------------------------------------------------------------------
class MelLctnShared(MelSequential):
    """Handles the LCTN subrecords shared between Skyrim and FO4."""
    def __init__(self):
        super().__init__(
            MelEdid(),
            MelArray('actor_cell_persistent_reference',
                MelStruct(b'ACPR', ['2I', '2h'], (FID, 'acpr_actor'),
                    (FID, 'acpr_location'), 'acpr_grid_x', 'acpr_grid_y'),
            ),
            MelArray('location_cell_persistent_reference',
                MelStruct(b'LCPR', ['2I', '2h'], (FID, 'lcpr_actor'),
                    (FID, 'lcpr_location'), 'lcpr_grid_x', 'lcpr_grid_y'),
            ),
            MelSimpleArray('reference_cell_persistent_reference',
                MelFid(b'RCPR')),
            MelArray('actor_cell_unique',
                MelStruct(b'ACUN', ['3I'], (FID, 'acun_actor'),
                    (FID, 'acun_ref'), (FID, 'acun_location')),
            ),
            MelArray('location_cell_unique',
                MelStruct(b'LCUN', ['3I'], (FID, 'lcun_actor'),
                    (FID, 'lcun_ref'), (FID, 'lcun_location')),
            ),
            MelSimpleArray('reference_cell_unique', MelFid(b'RCUN')),
            MelArray('actor_cell_static_reference',
                MelStruct(b'ACSR', ['3I', '2h'], (FID, 'acsr_loc_ref_type'),
                    (FID, 'acsr_marker'), (FID, 'acsr_location'),
                    'acsr_grid_x', 'acsr_grid_y'),
            ),
            MelArray('location_cell_static_reference',
                MelStruct(b'LCSR', ['3I', '2h'], (FID, 'lcsr_loc_ref_type'),
                    (FID, 'lcsr_marker'), (FID, 'lcsr_location'),
                    'lcsr_grid_x', 'lcsr_grid_y'),
            ),
            MelSimpleArray('reference_cell_static_reference', MelFid(b'RCSR')),
            MelGroups('actor_cell_encounter_cell',
                MelArray('acec_coordinates',
                    MelStruct(b'ACEC', ['2h'], 'acec_grid_x', 'acec_grid_y'),
                    prelude=MelFid(b'ACEC', 'acec_location'),
                ),
            ),
            MelGroups('location_cell_encounter_cell',
                MelArray('lcec_coordinates',
                    MelStruct(b'LCEC', ['2h'], 'lcec_grid_x', 'lcec_grid_y'),
                    prelude=MelFid(b'LCEC', 'lcec_location'),
                ),
            ),
            MelGroups('reference_cell_encounter_cell',
                MelArray('rcec_coordinates',
                    MelStruct(b'RCEC', ['2h'], 'rcec_grid_x', 'rcec_grid_y'),
                    prelude=MelFid(b'RCEC', 'rcec_location'),
                ),
            ),
            MelSimpleArray('actor_cell_marker_reference', MelFid(b'ACID')),
            MelSimpleArray('location_cell_marker_reference', MelFid(b'LCID')),
            MelArray('actor_cell_enable_point',
                MelStruct(b'ACEP', ['2I', '2h'], (FID, 'acep_actor'),
                    (FID, 'acep_ref'), 'acep_grid_x', 'acep_grid_y'),
            ),
            MelArray('location_cell_enable_point',
                MelStruct(b'LCEP', ['2I', '2h'], (FID, 'lcep_actor'),
                    (FID, 'lcep_ref'), 'lcep_grid_x', 'lcep_grid_y'),
            ),
            MelFull(),
            MelKeywords(),
            MelFid(b'PNAM', 'parent_location'),
            MelFid(b'NAM1', 'lctn_music'),
            MelFid(b'FNAM', 'unreported_crime_faction'),
            MelFid(b'MNAM', 'world_location_marker_ref'),
            MelFloat(b'RNAM', 'world_location_radius'),
        )

#------------------------------------------------------------------------------
class MelLensShared(MelSequential):
    """Handles the LENS subrecords shared between Skyrim and FO4."""
    _lfs_flags = Flags.from_names('lfs_rotates', 'lfs_shrinks_when_occluded')

    def __init__(self, *, sprites_are_sorted=True):
        lfs_element = MelGroups('lens_flare_sprites',
            MelString(b'DNAM', 'lfs_sprite_id'),
            MelString(b'FNAM', 'lfs_texture'),
            MelStruct(b'LFSD', ['8f', 'I'], *gen_color3('lfs_tint'),
                'lfs_width', 'lfs_height', 'lfs_position', 'lfs_angular_fade',
                'lfs_opacity', (self._lfs_flags, 'lfs_flags')),
            )
        if sprites_are_sorted:
            lfs_element = MelSorted(lfs_element, sort_by_attrs='lfs_sprite_id')
        super().__init__(
            MelEdid(),
            MelFloat(b'CNAM', 'color_influence'),
            MelFloat(b'DNAM', 'fade_distance_radius_scale'),
            MelCounter(MelUInt32(b'LFSP', 'sprite_count'),
                counts='lens_flare_sprites'),
            lfs_element,
        )

#------------------------------------------------------------------------------
class MelLighFade(MelFloat):
    """Handles the LIGH subrecord FNAM (Fade)."""
    def __init__(self):
        super().__init__(b'FNAM', 'light_fade')

#------------------------------------------------------------------------------
class MelLighLensFlare(MelFid):
    """Handles the LIGH subrecord LNAM (Lens Flare)."""
    def __init__(self):
        super().__init__(b'LNAM', 'light_lens_flare')

#------------------------------------------------------------------------------
class MelLLChanceNone(MelUInt8):
    """Handles the leveled list subrecord LVLD (Chance None)."""
    _cn_sig = b'LVLD'

    def __init__(self):
        super().__init__(self._cn_sig, 'lvl_chance_none')

class MelLLChanceNoneTes3(MelLLChanceNone):
    """Morrowind version - different subrecord signature."""
    _cn_sig = b'NNAM'

#------------------------------------------------------------------------------
class _AMelLLFlags:
    """Base class for leveled list flags subrecords."""
    _lvl_flags = Flags.from_names(
        'calc_from_all_levels',
        'calc_for_each_item',
        'use_all_items', # since Oblivion
        'special_loot', # Skyrim only
    )
    _flags_sig: bytes

    def __init__(self):
        super().__init__(self._flags_sig, 'flags', self._lvl_flags)

class MelLLFlags(_AMelLLFlags, MelUInt8Flags):
    """Handles the leveled list subrecord LVLF (Flags)."""
    _flags_sig = b'LVLF'

class MelLLFlagsTes3(_AMelLLFlags, MelUInt32Flags):
    """Handles the leveled list subrecord DATA (Flags)."""
    _flags_sig = b'DATA'

#------------------------------------------------------------------------------
class MelLLGlobal(MelFid):
    """Handles the leveled list subrecord LVLG (Global)."""
    def __init__(self):
        super().__init__(b'LVLG', 'lvl_global')

#------------------------------------------------------------------------------
class MelLscrCameraPath(MelString):
    """Handles the LSCR subrecord MOD2 (Camera Path)."""
    def __init__(self):
        super().__init__(b'MOD2', 'lscr_camera_path')

#------------------------------------------------------------------------------
class MelLscrLocations(MelSorted):
    """Handles the LSCR subrecord LNAM (Locations)."""
    def __init__(self):
        super().__init__(MelGroups('lscr_locations',
            MelStruct(b'LNAM', ['2I', '2h'], (FID, 'll_direct'),
                (FID, 'll_indirect'), 'll_grid_y', 'll_grid_x'),
        ), sort_by_attrs=('ll_direct', 'll_indirect', 'll_grid_y',
                          'll_grid_x'))

#------------------------------------------------------------------------------
class MelLscrNif(MelFid):
    """Handles the LSCR subrecord NNAM (Loading Screen NIF)."""
    def __init__(self):
        super().__init__(b'NNAM', 'lscr_nif')

#------------------------------------------------------------------------------
class MelLscrRotation(MelStruct):
    """Handles the LSCR subrecord ONAM (Rotation)."""
    def __init__(self):
        super().__init__(b'ONAM', ['2h'], 'lscr_rotation_min',
            'lscr_rotation_max')

#------------------------------------------------------------------------------
class MelLtexGrasses(MelSorted):
    """Handles the LTEX subrecord GNAM (Grasses)."""
    def __init__(self):
        super().__init__(MelFids('ltex_grasses', MelFid(b'GNAM')))

#------------------------------------------------------------------------------
class MelLtexSnam(MelUInt8):
    """Handles the LTEX subrecord SNAM (Texture Specular Exponent)."""
    def __init__(self):
        super().__init__(b'SNAM', 'texture_specular_exponent')

#------------------------------------------------------------------------------
class MelMapMarker(MelGroup):
    """Map marker struct for a reference record (REFR, ACHR, etc.). Also
    supports the WMI1 subrecord from FNV."""
    # Same idea as above - show_all_hidden is FO3+, but that's no problem.
    _marker_flags = Flags.from_names('visible', 'can_travel_to',
                                     'show_all_hidden')

    def __init__(self, *, with_reputation=False):
        group_elems = [
            MelBase(b'XMRK', 'marker_data'),
            MelUInt8Flags(b'FNAM', 'marker_flags', self._marker_flags),
            MelFull(),
            MelOptStruct(b'TNAM', ['B', 's'], 'marker_type', 'unused1'),
        ]
        if with_reputation:
            group_elems.append(MelFid(b'WMI1', 'marker_reputation'))
        super().__init__('map_marker', *group_elems)

#------------------------------------------------------------------------------
class MelMatoPropertyData(MelGroups):
    """Handles the MATO subrecord DNAM (Property Data)."""
    def __init__(self):
        super().__init__('property_data',
            MelBase(b'DNAM', 'data_entry'),
        )

#------------------------------------------------------------------------------
class MelMattShared(MelSequential):
    """Implements the MATT subrecords PNAM, MNAM, CNAM, BNAM, FNAM and HNAM."""
    _matt_flags = Flags.from_names(
        'stair_material',
        'arrows_stick',
        'can_tunnel', # since FO4
    )

    def __init__(self):
        super().__init__(
            MelFid(b'PNAM', 'matt_material_parent'),
            MelString(b'MNAM', 'matt_material_name'),
            MelStruct(b'CNAM', ['3f'], *gen_color3('havok_display_color')),
            MelFloat(b'BNAM', 'matt_buoyancy'),
            MelUInt32Flags(b'FNAM', 'matt_flags', self._matt_flags),
            MelImpactDataset(b'HNAM'),
        )

#------------------------------------------------------------------------------
class MelMdob(MelFid):
    """Represents the common Menu Display Object subrecord."""
    def __init__(self):
        super().__init__(b'MDOB', 'menu_display_object')

#------------------------------------------------------------------------------
class MelMODS(MelBase):
    """MODS/MO2S/etc/DMDS subrecord"""
    _fid_element = MelFid(null1) # dummy MelFid instance to use its loader

    def hasFids(self,formElements):
        formElements.add(self)

    def setDefault(self,record):
        setattr(record, self.attr, None)

    def load_mel(self, record, ins, sub_type, size_, *debug_strs,
                 __unpacker=int_unpacker, __load_fid=_fid_element.load_bytes):
        insUnpack = ins.unpack
        insRead32 = ins.readString32
        count, = insUnpack(__unpacker, 4, *debug_strs)
        mods_data = []
        dataAppend = mods_data.append
        for x in range(count):
            string = insRead32(*debug_strs)
            int_fid = __load_fid(ins, 4)
            index, = insUnpack(__unpacker, 4, *debug_strs)
            dataAppend((string, int_fid, index))
        setattr(record, self.attr, mods_data)

    def pack_subrecord_data(self, record, *, __packer=structs_cache['I'].pack,
                            __fid_packer=_fid_element.packer):
        mods_data = getattr(record, self.attr)
        if mods_data is not None:
            # Sort by 3D Name and 3D Index
            mods_data.sort(key=lambda e: (e[0], e[2]))
            return b''.join([__packer(len(mods_data)), *(chain(*(
                [__packer(len(string)), encode(string), __fid_packer(int_fid),
                 __packer(index)] for (string, int_fid, index) in
            mods_data)))])

    def mapFids(self, record, function, save_fids=False):
        attr = self.attr
        mods_data = getattr(record, attr)
        if mods_data is not None:
            mods_data = [(string,function(fid),index) for (string,fid,index)
                         in mods_data]
            if save_fids: setattr(record, attr, mods_data)

#------------------------------------------------------------------------------
class MelNextPerk(MelFid):
    """Handles the PERK subrecord NNAM (Next Perk)."""
    def __init__(self):
        super().__init__(b'NNAM', 'next_perk')

#------------------------------------------------------------------------------
class MelNodeIndex(MelSInt32):
    """Handles the ADDN subrecord DATA (Node Index)."""
    def __init__(self):
        super().__init__(b'DATA', 'node_index')

#------------------------------------------------------------------------------
class MelOwnership(MelGroup):
    """Handles XOWN, XRNK for cells and cell children."""

    def __init__(self, attr='ownership'):
        MelGroup.__init__(self, attr,
            MelFid(b'XOWN', 'owner'),
            MelSInt32(b'XRNK', 'rank'),
        )

    def pack_subrecord_data(self, record):
        if record.ownership and record.ownership.owner:
            return super().pack_subrecord_data(record) # else None - don't dump

#------------------------------------------------------------------------------
class MelPerkData(MelTruncatedStruct):
    """Handles the PERK subrecord DATA (Data)."""
    def __init__(self):
        super().__init__(b'DATA', ['5B'], 'perk_trait', 'perk_level',
            'perk_num_ranks', 'perk_playable', 'perk_hidden',
            old_versions={'4B', '3B'})

#------------------------------------------------------------------------------
class MelPerkParamsGroups(MelGroups):
    """Hack to make pe_function available to the group elements so that their
    deciders can use it."""
    def __init__(self, *elements):
        super().__init__('pe_params', *elements)

    def _new_object(self, record):
        target = super()._new_object(record)
        pe_fn = record.pe_function
        target.pe_function = pe_fn if pe_fn is not None else -1
        return target

#------------------------------------------------------------------------------
class MelRace(MelFid):
    """Handles the common RNAM (Race) subrecord."""
    def __init__(self):
        super().__init__(b'RNAM', 'race')

#------------------------------------------------------------------------------
##: This is a strange fusion of MelLists, MelStruct and MelTruncatedStruct
# because one of the attrs is a flags field and in Skyrim it's truncated too
class MelRaceData(MelTruncatedStruct):
    """Pack RACE skills and skill boosts as a single attribute."""

    def __init__(self, sub_sig, sub_fmt, *elements, **kwargs):
        if 'old_versions' not in kwargs:
            kwargs['old_versions'] = set() # set default to avoid errors
        super().__init__(sub_sig, sub_fmt, *elements, **kwargs)

    @staticmethod
    def _expand_formats(elements, struct_formats):
        expanded_fmts = []
        for f in struct_formats:
            if f == '14b':
                expanded_fmts.append(0)
            elif f[-1] != 's':
                expanded_fmts.extend([f[-1]] * int(f[:-1] or 1))
            else:
                expanded_fmts.append(int(f[:-1] or 1))
        return expanded_fmts

    def _pre_process_unpacked(self, unpacked_val):
        # first 14 bytes are the list of skills
        return super()._pre_process_unpacked(
            (list(unpacked_val[:14]), *unpacked_val[14:]))

    def pack_subrecord_data(self, record):
        values = list(record.skills)
        for value, action in zip((getattr(record, a) for a in self.attrs[1:]),
                                 self.actions[1:]):
            try:
                values.append(value.dump() if action is not None else value)
            except AttributeError:
                values.append(action(value).dump())
        return self._packer(*values)

#------------------------------------------------------------------------------
class MelRaceParts(MelNull):
    """Handles a subrecord array, where each subrecord is introduced by an
    INDX subrecord, which determines the meaning of the subrecord. The
    resulting attributes are set directly on the record."""
    def __init__(self, indx_to_attr: dict[int, str], group_loaders):
        """Creates a new MelRaceParts element with the specified INDX mapping
        and group loaders.

        :param indx_to_attr: A mapping from the INDX values to the final
            record attributes that will be used for the subsequent
            subrecords.
        :param group_loaders: A callable that takes the INDX value and
            returns an iterable with one or more MelBase-derived subrecord
            loaders. These will be loaded and dumped directly after each
            INDX."""
        self._last_indx = None # used during loading
        self._indx_to_attr = indx_to_attr
        # Create loaders for use at runtime
        self._indx_to_loader: dict[int, MelBase] = {
            part_indx: MelGroup(part_attr, *group_loaders(part_indx))
            for part_indx, part_attr in indx_to_attr.items()
        }
        self._possible_sigs = {s for element
                               in self._indx_to_loader.values()
                               for s in element.signatures}

    def getLoaders(self, loaders):
        temp_loaders = {}
        for element in self._indx_to_loader.values():
            element.getLoaders(temp_loaders)
        for signature in temp_loaders:
            loaders[signature] = self

    def getSlotsUsed(self):
        return tuple(self._indx_to_attr.values())

    def setDefault(self, record):
        for element in self._indx_to_loader.values():
            element.setDefault(record)

    def load_mel(self, record, ins, sub_type, size_, *debug_strs,
                 __unpacker=int_unpacker):
        if sub_type == b'INDX':
            self._last_indx = ins.unpack(__unpacker, size_, *debug_strs)[0]
        else:
            self._indx_to_loader[self._last_indx].load_mel(record, ins,
                sub_type, size_, *debug_strs)

    def dumpData(self, record, out):
        # Note that we have to dump out the attributes sorted by the INDX value
        for part_indx, part_attr in dict_sort(self._indx_to_attr):
            if hasattr(record, part_attr): # only dump present parts
                MelUInt32(b'INDX', 'UNUSED').packSub(out,
                    struct_pack('=I', part_indx))
                self._indx_to_loader[part_indx].dumpData(record, out)

    @property
    def signatures(self):
        return self._possible_sigs

#------------------------------------------------------------------------------
class MelRaceVoices(MelStruct):
    """Set voices to zero, if equal race fid. If both are zero, then skip
    dumping."""
    def pack_subrecord_data(self, record, *, __zero_fid=ZERO_FID):
        if record.maleVoice == record.fid: record.maleVoice = __zero_fid
        if record.femaleVoice == record.fid: record.femaleVoice = __zero_fid
        if record.maleVoice != __zero_fid or record.femaleVoice != __zero_fid:
            return super(MelRaceVoices, self).pack_subrecord_data(record)
        return None

#------------------------------------------------------------------------------
class MelRandomTeleports(MelSorted):
    """Handles the DOOR subrecord TNAM (Random Teleport Destinations)."""
    def __init__(self):
        super().__init__(MelFids('random_teleports', MelFid(b'TNAM')))

#------------------------------------------------------------------------------
class MelRef3D(MelOptStruct):
    """3D position and rotation for a reference record (REFR, ACHR, etc.)."""
    def __init__(self):
        super().__init__(b'DATA', ['6f'], 'ref_pos_x', 'ref_pos_y',
            'ref_pos_z', 'ref_rot_x', 'ref_rot_y', 'ref_rot_z')

#------------------------------------------------------------------------------
class MelReferences(MelGroups):
    """Handles mixed sets of SCRO and SCRV for scripts, quests, etc."""
    def __init__(self):
        super().__init__('references', MelUnion({
            b'SCRO': MelFid(b'SCRO', 'reference'),
            b'SCRV': MelUInt32(b'SCRV', 'reference'),
        }))

#------------------------------------------------------------------------------
class MelReflectedRefractedBy(MelSorted):
    """Reflected/Refracted By for a reference record (REFR, ACHR, etc.)."""
    _watertypeFlags = Flags.from_names('reflection', 'refraction')

    def __init__(self):
        super().__init__(MelGroups('reflectedRefractedBy',
            MelTruncatedStruct(b'XPWR', ['2I'], (FID, 'waterReference'),
                (self._watertypeFlags, 'waterFlags'), old_versions={'I'}),
        ), sort_by_attrs='waterReference')

#------------------------------------------------------------------------------
class MelRefScale(MelFloat):
    """Scale for a reference record (REFR, ACHR, etc.)."""
    def __init__(self): # default was 1.0
        super().__init__(b'XSCL', 'ref_scale')

#------------------------------------------------------------------------------
class MelRegions(MelSorted):
    """Handles the CELL subrecord XCLR (Regions)."""
    def __init__(self):
        super().__init__(MelSimpleArray('regions', MelFid(b'XCLR')))

#------------------------------------------------------------------------------
class MelRegnEntrySubrecord(MelUnion):
    """Wrapper around MelUnion to correctly read/write REGN entry data.
    Skips loading and dumping if entryType != entry_type_val.

    entry_type_val meanings:
      - 2: Objects
      - 3: Weather
      - 4: Map
      - 5: Land
      - 6: Grass
      - 7: Sound
      - 8: Imposter (FNV only)"""
    def __init__(self, entry_type_val: int, element):
        super().__init__({
            entry_type_val: element,
        }, decider=AttrValDecider('entryType'),
            fallback=MelNull(b'NULL')) # ignore

#------------------------------------------------------------------------------
class MelRelations(MelSorted):
    """Handles the common XNAM (Relations) subrecord. Group combat reaction
    (GCR) can be excluded (i.e. in Oblivion)."""
    def __init__(self, *, with_gcr=True):
        rel_fmt = ['I', 'i']
        rel_elements = [(FID, 'faction'), 'mod']
        if with_gcr:
            rel_fmt.append('I')
            rel_elements.append('group_combat_reaction')
        super().__init__(MelGroups('relations',
            MelStruct(b'XNAM', rel_fmt, *rel_elements),
        ), sort_by_attrs='faction')

#------------------------------------------------------------------------------
class MelScript(MelFid):
    """Represents the common script subrecord in TES4/FO3/FNV."""
    def __init__(self):
        super().__init__(b'SCRI', 'script_fid')

#------------------------------------------------------------------------------
class MelScriptVars(MelSorted):
    """Handles SLSD and SCVR combos defining script variables."""
    def __init__(self):
        super().__init__(MelGroups('script_vars',
            MelStruct(b'SLSD', ['I', '12s', 'B', '7s'], 'var_index', 'unused1',
                'var_type', 'unused2'),
            MelString(b'SCVR', 'var_name'),
        ), sort_by_attrs='var_index')

#------------------------------------------------------------------------------
class MelSeasons(MelStruct):
    """Handles the common PFPC (Seasonal Ingredient Production) subrecord."""
    def __init__(self):
        super().__init__(b'PFPC', ['4B'], 'sip_spring', 'sip_summer',
            'sip_fall', 'sip_winter'),

#------------------------------------------------------------------------------
class MelShortName(MelLString):
    """Defines a 'Short Name' subrecord. Most common signature is ONAM."""
    def __init__(self, sn_sig=b'ONAM'):
        super().__init__(sn_sig, 'short_name')

#------------------------------------------------------------------------------
class MelSkipInterior(MelUnion):
    """Union that skips dumping if we're in an interior."""
    def __init__(self, element):
        super().__init__({
            True: MelReadOnly(element),
            False: element,
        }, decider=FlagDecider('flags', ['isInterior']))

#------------------------------------------------------------------------------
class MelSound(MelFid):
    """Handles the common SNAM (Sound) subrecord."""
    def __init__(self):
        super().__init__(b'SNAM', 'sound')

#------------------------------------------------------------------------------
class MelSoundActivation(MelFid):
    """Handles the ACTI subrecord VNAM (Sound - Activation)."""
    def __init__(self):
        super().__init__(b'VNAM', 'soundActivation')

#------------------------------------------------------------------------------
class MelSoundClose(MelFid):
    """Handles the CONT/DOOR subrecord QNAM/ANAM (Sound - Close)."""
    def __init__(self, sc_sig=b'QNAM'):
        super().__init__(sc_sig, 'sound_close')

#------------------------------------------------------------------------------
class MelSoundLooping(MelFid):
    """Handles the DOOR subrecord BNAM (Sound - Looping)."""
    def __init__(self):
        super().__init__(b'BNAM', 'sound_looping')

#------------------------------------------------------------------------------
class MelSoundPickupDrop(MelSequential):
    """Handles the common YNAM (Pickup Sound) and ZNAM (Drop Sound) subrecords.
    They always occur together."""
    def __init__(self):
        super().__init__(
            MelFid(b'YNAM', 'pickupSound'),
            MelFid(b'ZNAM', 'dropSound'),
        )

#------------------------------------------------------------------------------
class MelSpells(MelSorted):
    """Handles the common SPLO subrecord."""
    def __init__(self):
        super().__init__(MelFids('spells', MelFid(b'SPLO')))

#------------------------------------------------------------------------------
class MelTemplateArmor(MelFid):
    """Handles the ARMO subrecord TNAM (Template Armor)."""
    def __init__(self):
        super().__init__(b'TNAM', 'template_armor')

#------------------------------------------------------------------------------
class MelTxstFlags(MelUInt16Flags):
    """Handles the TXST subrecord DNAM (Flags)."""
    _txst_flags = Flags.from_names(
        'no_specular_map',
        'facegen_textures', # since Skyrim
        'has_model_space_normal_map', # since Skyrim
    )

    def __init__(self):
        super().__init__(b'DNAM', 'txst_flags', self._txst_flags)

#------------------------------------------------------------------------------
class MelUnloadEvent(MelString):
    """Handles the ANIO subrecord BNAM (Unload Event)."""
    def __init__(self):
        super().__init__(b'BNAM', 'unload_event')

#------------------------------------------------------------------------------
# xEdit calls this 'time interpolator', but that name doesn't really make sense
# Both this class and the color interpolator above interpolate over time
class MelValueInterpolator(MelArray):
    """Wrapper around MelArray that defines a value interpolator - an array
    of two floats, where each entry in the array describes a point on a curve,
    with 'time' as the X axis and 'value' as the Y axis."""
    def __init__(self, interp_sig, attr):
        super().__init__(attr, MelStruct(interp_sig, ['2f'], 'time', 'value'))

#------------------------------------------------------------------------------
class MelValueWeight(MelStruct):
    """Handles a common variant of the DATA subrecord that consists of one
    integer (the value of an object) and one float (the weight of an
    object)."""
    def __init__(self):
        super().__init__(b'DATA', ['I', 'f'], 'value', 'weight')

#------------------------------------------------------------------------------
class MelWaterType(MelFid):
    """Handles the common WNAM (Water Type) subrecord."""
    def __init__(self):
        super().__init__(b'WNAM', 'water_type')

#------------------------------------------------------------------------------
class MelWeight(MelFloat):
    """Handles a common variant of the DATA subrecord that consists of a single
    float denoting the record's weight."""
    def __init__(self):
        super().__init__(b'DATA', 'weight')

#------------------------------------------------------------------------------
class MelWorldBounds(MelSequential):
    """Worldspace (WRLD) bounds."""
    def __init__(self):
        super().__init__(
            MelStruct(b'NAM0', ['2f'], 'object_bounds_min_x',
                'object_bounds_min_y'),
            MelStruct(b'NAM9', ['2f'], 'object_bounds_max_x',
                'object_bounds_max_y'),
        )

#------------------------------------------------------------------------------
class MelWthrColors(MelStruct):
    """Used in WTHR for PNAM and NAM0 for all games but FNV."""
    def __init__(self, wthr_sub_sig):
        super().__init__(wthr_sub_sig, ['3B', 's', '3B', 's', '3B', 's', '3B',
                                        's'], 'riseRed', 'riseGreen',
            'riseBlue', 'unused1', 'dayRed', 'dayGreen', 'dayBlue', 'unused2',
            'setRed', 'setGreen', 'setBlue', 'unused3', 'nightRed',
            'nightGreen', 'nightBlue', 'unused4')

#------------------------------------------------------------------------------
class MelXlod(MelOptStruct):
    """Distant LOD Data."""
    def __init__(self):
        super().__init__(b'XLOD', ['3f'], 'lod1', 'lod2', 'lod3')

#------------------------------------------------------------------------------
class _SpellFlags(Flags):
    """For SpellFlags, immuneToSilence activates bits 1 AND 3."""
    __slots__ = ()

    def __setitem__(self, index, value):
        setter = Flags.__setitem__
        setter(self, index, value)
        if index == 1:
            setter(self, 3, value)

SpellFlags = _SpellFlags.from_names('noAutoCalc','immuneToSilence',
    'startSpell', None, 'ignoreLOS', 'scriptEffectAlwaysApplies',
    'disallowAbsorbReflect', 'touchExplodesWOTarget')
