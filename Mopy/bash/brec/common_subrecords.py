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
"""Builds on the basic elements defined in base_elements.py to provide
definitions for some commonly needed subrecords."""
from itertools import chain

from .advanced_elements import AttrValDecider, FidNotNullDecider, \
    FlagDecider, MelArray, MelCounter, MelPartialCounter, MelSimpleArray, \
    MelSorted, MelTruncatedStruct, MelUnion, PartialLoadDecider, MelExtra
from .basic_elements import MelBase, MelFid, MelFloat, MelGroup, \
    MelGroups, MelLString, MelNull, MelReadOnly, MelSequential, \
    MelSInt32, MelString, MelStrings, MelStruct, MelUInt8, MelUInt8Flags, \
    MelUInt16Flags, MelUInt32, MelUInt32Flags, MelSInt8, MelUInt16, \
    MelSimpleGroups, MelUInt32Bool
from .utils_constants import FID, ZERO_FID, ambient_lighting_attrs, \
    color_attrs, color3_attrs, int_unpacker, null1, gen_coed_key, \
    PackGeneralFlags, PackInterruptFlags, position_attrs, rotation_attrs, \
    EnableParentFlags
from ..bolt import Flags, TrimmedFlags, dict_sort, encode, flag, struct_pack, \
    structs_cache
from ..exception import ModError

#------------------------------------------------------------------------------
class _MelCoed(MelStruct):
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
        base_attrs = ('item', 'count')
        sort_kwargs = {'sort_by_attrs': base_attrs}
        if with_coed:
            items_elements.append(_MelCoed())
            sort_kwargs = {'sort_special': gen_coed_key(base_attrs)}
        final_elements = [MelSorted(MelGroups('items', *items_elements),
            **sort_kwargs)]
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
        base_attrs = ('level', 'listId', 'count')
        sort_kwargs = {'sort_by_attrs': base_attrs}
        if with_coed:
            lvl_elements.append(_MelCoed())
            sort_kwargs = {'sort_special': gen_coed_key(base_attrs)}
        final_elements = [MelSorted(MelGroups('entries', *lvl_elements),
            **sort_kwargs)]
        if with_counter:
            final_elements.insert(0, MelCounter(
                MelUInt8(b'LLCT', 'entry_count'), counts='entries'))
        super().__init__(*final_elements)

#------------------------------------------------------------------------------
class MelActiFlags(MelUInt16Flags):
    """Handles the ACTI subrecord FNAM (Flags). Note that this subrecord is
    inherited by a couple other records too."""
    class _acti_flags(Flags):
        no_displacement: bool = flag(0)
        ignored_by_sandbox: bool = flag(1)
        is_a_radio: bool = flag(4) # Introduced in FO4

    def __init__(self):
        super().__init__(b'FNAM', 'acti_flags', self._acti_flags)

#------------------------------------------------------------------------------
class MelActionFlags(MelUInt32Flags):
    """XACT (Action Flags) subrecord for REFR records."""
    class _act_flags(Flags):
        act_use_default: bool
        act_activate: bool
        act_open: bool
        act_open_by_default: bool

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
    class _ap_flags(TrimmedFlags):
        parent_activate_only: bool

    def __init__(self):
        super().__init__('activate_parents',
            MelUInt8Flags(b'XAPD', 'activate_parent_flags', self._ap_flags),
            MelSorted(MelGroups('activate_parent_refs',
                MelStruct(b'XAPR', ['I', 'f'], (FID, 'ap_reference'),
                    'ap_delay'),
            ), sort_by_attrs='ap_reference'),
        )

#------------------------------------------------------------------------------
class MelAddnDnam(MelStruct):
    """Handles the ADDN subrecord DNAM (Data)."""
    def __init__(self):
        # addon_flags is 2 unknown bytes in FO3/FNV, but decoding it as a short
        # can't hurt and is much simpler
        super().__init__(b'DNAM', ['2H'], 'master_particle_system_cap',
            'addon_flags') # not really flags, behaves more like an enum

#------------------------------------------------------------------------------
class MelAIPackages(MelSimpleGroups):
    """Handles the CREA/NPC_ subrecord PKID (Packages)."""
    def __init__(self):
        super().__init__('ai_packages', MelFid(b'PKID'))

#------------------------------------------------------------------------------
class MelAlchEnit(MelStruct):
    """Handles the ALCH subrecord ENIT (Effect Data) since Skyrim."""
    class _enit_flags(Flags):
        alch_no_auto_calc: bool = flag(0)
        alch_is_food: bool = flag(1)
        medicine: bool = flag(16)
        poison: bool = flag(17)

    def __init__(self):
        super().__init__(b'ENIT', ['i', '2I', 'f', 'I'], 'value',
            (self._enit_flags, 'flags'), (FID, 'addiction'), 'addictionChance',
            (FID, 'sound_consume'))

#------------------------------------------------------------------------------
class MelAnimations(MelSorted): ##: case insensitive
    """Handles the common KFFZ (Animations) subrecord."""
    def __init__(self):
        super().__init__(MelStrings(b'KFFZ', 'animations'))

#------------------------------------------------------------------------------
class MelArmaShared(MelSequential):
    """Handles the ARMA subrecords DNAM, MOD2-MOD5, NAM0-NAM3, MODL, SNDD and
    ONAM."""
    class _weight_slider_flags(Flags):
        slider_enabled: bool = flag(1)

    def __init__(self, mel_model: type[MelBase]):
        super().__init__(
            MelStruct(b'DNAM', ['4B', '2s', 'B', 's', 'f'],
                'male_priority', 'female_priority',
                (self._weight_slider_flags, 'slider_flags_m'),
                (self._weight_slider_flags, 'slider_flags_f'), 'unknown_dnam1',
                'detection_sound_value', 'unknown_dnam2', 'weapon_adjust'),
            mel_model(b'MOD2', 'male_model'),
            mel_model(b'MOD3', 'female_model'),
            mel_model(b'MOD4', 'male_model_1st'),
            mel_model(b'MOD5', 'female_model_1st'),
            MelFid(b'NAM0', 'skin0'),
            MelFid(b'NAM1', 'skin1'),
            MelFid(b'NAM2', 'skin2'),
            MelFid(b'NAM3', 'skin3'),
            MelSorted(MelSimpleGroups('additional_races', MelFid(b'MODL'))),
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
class MelAttackRace(MelFid):
    """Handles the NPC_/RACE subrecord ATKR (Attack Race)."""
    def __init__(self):
        super().__init__(b'ATKR', 'attack_race')

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
# FIXME(inf) We need to go through xEdit's source code and add is_required to
#  all our MelBounds wherever xEdit (on the dev-4.1.5 branch) has wbOBND(True)
#  instead of plain wbOBND
class MelBounds(MelGroup):
    """Wrapper around MelGroup for the common task of defining OBND - Object
    Bounds. Uses MelGroup to avoid merging them when importing."""
    def __init__(self, *, is_required=False):
        super().__init__('bounds',
            MelStruct(b'OBND', ['6h'], 'boundX1', 'boundY1', 'boundZ1',
                'boundX2', 'boundY2', 'boundZ2', is_required=is_required),
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
##: This should pass is_required and be renamed to MelColorR, also double-check
# that all these really are required in xEdit
class MelColor(MelStruct):
    """Required Color."""
    def __init__(self, color_sig=b'CNAM'):
        super().__init__(color_sig, ['4B'], 'red', 'green', 'blue', 'alpha')

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
##: This should be renamed MelColor, see comment near current MelColor above
class MelColorO(MelStruct):
    """Optional Color."""
    def __init__(self, color_sig=b'CNAM'):
        super().__init__(color_sig, ['4B'], 'red', 'green', 'blue', 'alpha')

#------------------------------------------------------------------------------
class MelCombatStyle(MelFid):
    """Handles the common ZNAM/CNAM (Combat Style) subrecord."""
    def __init__(self, cs_sig=b'ZNAM'):
        super().__init__(cs_sig, 'combat_style')

#------------------------------------------------------------------------------
class MelContData(MelStruct):
    """Handles the CONT subrecord DATA (Data)."""
    # Flags 1 & 3 introduced in Skyrim, treat as unknown for earlier games
    class _cont_flags(Flags):
        allow_sounds_when_animation: bool
        cont_respawns: bool
        show_owner: bool

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
            MelSimpleGroups('camera_shots', MelFid(b'SNAM')),
        )

#------------------------------------------------------------------------------
class MelDalc(MelTruncatedStruct):
    """Handles the common DALC (Directional Ambient Lighting Colors)
    subrecord."""
    def __init__(self):
        super().__init__(b'DALC', ['28B', 'f'],
            *ambient_lighting_attrs('dalc'), old_versions={'24B'})

#------------------------------------------------------------------------------
class MelDeathItem(MelFid):
    """Handles the common INAM (Death Item) subrecord."""
    def __init__(self):
        super().__init__(b'INAM', 'death_item')

#------------------------------------------------------------------------------
class MelDebrData(MelStruct):
    """Handles the DEBR subrecord DATA (Data)."""
    class _debr_flags(Flags):
        has_collision_data: bool
        collision: bool

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
class MelDecalData(MelStruct):
    """Handles the common DODT (Decal Data) subrecord."""
    class _decal_flags(TrimmedFlags):
        parallax: bool
        alpha_blending: bool
        alpha_testing: bool
        no_subtextures: bool # since Skyrim

    def __init__(self):
        super().__init__(b'DODT', ['7f', 'B', 'B', '2s', '3B', 's'],
            'decal_min_width', 'decal_max_width', 'decal_min_height',
            'decal_max_height', 'decal_depth', 'decal_shininess',
            'decal_parallax_scale', 'decal_parallax_passes',
            (self._decal_flags, 'decal_flags'), 'decal_unused1',
            *color_attrs('decal_color'))

#------------------------------------------------------------------------------
class MelDescription(MelLString):
    """Handles the description (DESC) subrecord."""
    def __init__(self):
        super().__init__(b'DESC', 'description')

#------------------------------------------------------------------------------
class MelDoorFlags(MelUInt8Flags):
    class _door_flags(Flags):
        oblivion_gate: bool # Oblivion only
        automatic: bool
        hidden: bool
        minimal_use: bool
        sliding_door: bool # since FO3
        do_not_open_in_combat_search: bool # since Skyrim
        no_to_text: bool # since FO4

    def __init__(self):
        super().__init__(b'FNAM', 'door_flags', self._door_flags)

#------------------------------------------------------------------------------
class MelEdid(MelString):
    """Handles an Editor ID (EDID) subrecord."""
    def __init__(self, is_required=False):
        super().__init__(b'EDID', 'eid',
            set_default='' if is_required else None)

#------------------------------------------------------------------------------
class MelEnableParent(MelStruct):
    """Enable Parent struct for a reference record (REFR, ACHR, etc.)."""
    def __init__(self):
        super().__init__(b'XESP', ['I', 'B', '3s'], (FID, 'ep_reference'),
            (EnableParentFlags, 'enable_parent_flags'), 'xesp_unused')

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
        super().__init__('slot_parents', MelParent())

#------------------------------------------------------------------------------
class MelEyesFlags(MelUInt8Flags): # required
    """Handles the EYES subrecord DATA (Flags)."""
    class _EyesFlags(Flags):
        playable: bool
        not_male: bool # since FO3
        not_female: bool # since FO3

    def __init__(self):
        super().__init__(b'DATA', 'flags', self._EyesFlags, set_default=0)

#------------------------------------------------------------------------------
class MelFactFlags(MelUInt32Flags):
    """Handles the FACT subrecord DATA (Flags) since Skyrim."""
    class _fact_flags(Flags):
        hidden_from_pc: bool = flag(0)
        special_combat: bool = flag(1)
        track_crime: bool = flag(6)
        ignore_crimes_murder: bool = flag(7)
        ignore_crimes_assault: bool = flag(8)
        ignore_crimes_stealing: bool = flag(9)
        ignore_crimes_trespass: bool = flag(10)
        do_not_report_crimes_against_members: bool = flag(11)
        crime_gold_use_defaults: bool = flag(12)
        ignore_crimes_pickpocket: bool = flag(13)
        allow_sell: bool = flag(14) # also called 'vendor'
        can_be_owner: bool = flag(15)
        ignore_crimes_werewolf: bool = flag(16)

    def __init__(self):
        super().__init__(b'DATA', 'fact_flags', self._fact_flags)

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
    """Handles the common SNAM (Factions) subrecord. The unused 3 bytes at the
    end are gone since FO4."""
    def __init__(self, *, with_unused=False):
        snam_types = ['I', 'B']
        snam_args = [(FID, 'faction'), 'rank']
        if with_unused:
            snam_types.append('3s')
            snam_args.append(('unused1', b'ODB'))
        super().__init__(MelGroups('factions',
            MelStruct(b'SNAM', snam_types, *snam_args),
        ), sort_by_attrs='faction')

#------------------------------------------------------------------------------
class MelFilterString(MelString):
    """Handles the common FLTR (Filter) subrecord."""
    def __init__(self):
        super().__init__(b'FLTR', 'filter_string')

#------------------------------------------------------------------------------
class MelFlstFids(MelSimpleGroups):
    """Handles the FLST subrecord LNAM (FormIDs)."""
    def __init__(self):
        super().__init__('formIDInList', MelFid(b'LNAM')) # Do *not* sort!

#------------------------------------------------------------------------------
class MelFull(MelLString):
    """Handles a name (FULL) subrecord."""
    def __init__(self, *, is_required=False):
        super().__init__(b'FULL', 'full',
            set_default='' if is_required else None)

#------------------------------------------------------------------------------
class MelFurnMarkerData(MelSequential):
    """Handles the FURN subrecords ENAM, NAM0, FNMK (Skyrim only), FNPR and
    XMRK."""
    class _entry_points(Flags):
        entry_point_front: bool
        entry_point_behind: bool
        entry_point_right: bool
        entry_point_left: bool
        entry_point_up: bool

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
    class _gras_flags(Flags):
        vertex_lighting: bool
        uniform_scaling: bool
        fit_to_slope: bool

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
    class _hair_flags(Flags):
        playable: bool
        not_male: bool
        not_female: bool
        hair_fixed: bool

    def __init__(self):
        super().__init__(b'DATA', 'flags', self._hair_flags)

#------------------------------------------------------------------------------
class MelHdptShared(MelSequential):
    """Handles the HDPT subrecords DATA, PNAM, HNAM, NAM0, NAM1, TNAM, CNAM and
    RNAM."""
    class _hdpt_flags(Flags):
        playable: bool
        not_female: bool
        not_male: bool
        is_extra_part: bool
        use_solid_tint: bool
        uses_body_texture: bool # since FO4

    def __init__(self):
        super().__init__(
            MelUInt8Flags(b'DATA', 'flags', self._hdpt_flags),
            MelUInt32(b'PNAM', 'hdpt_type'),
            MelSorted(MelSimpleGroups('extra_parts', MelFid(b'HNAM'))),
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
    def __init__(self, icon_attr='iconPath', mico_attr='smallIconPath', *,
            icon_sig=b'ICON', mico_sig=b'MICO', is_required=False):
        """Creates a new MelIcons with the specified attributes.

        :param icon_attr: The attribute to use for the ICON subrecord. If
            falsy, this means 'do not include an ICON subrecord'.
        :param mico_attr: The attribute to use for the MICO subrecord. If
            falsy, this means 'do not include a MICO subrecord'."""
        final_elements = []
        if icon_attr:
            final_elements.append(MelString(icon_sig, icon_attr,
                set_default='' if is_required else None))
        if mico_attr:
            final_elements.append(MelString(mico_sig, mico_attr,
                set_default='' if is_required else None))
        if not final_elements:
            raise SyntaxError('MelIcons: At least one of icon_attr or '
                              'mico_attr must be specified')
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
    def __init__(self, icon_attr='iconPath', *, is_required=False):
        super().__init__(icon_attr=icon_attr, mico_attr='',
            is_required=is_required)

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
            counters={'idle_animation_count': 'idle_animations'})

#------------------------------------------------------------------------------
class MelIdleData(MelStruct):
    """Handles the IDLE subrecord DATA (Data) since Skyrim."""
    class _idle_flags(TrimmedFlags):
        idle_parent: bool
        idle_sequence: bool
        no_attacking: bool
        idle_blocking: bool

    def __init__(self):
        super().__init__(b'DATA', ['4B', 'H'], 'looping_min', 'looping_max',
            (self._idle_flags, 'idle_flags'), 'animation_group_section',
            'replay_delay')

#------------------------------------------------------------------------------
class MelIdleAnimFlags(MelUInt8Flags):
    """Handles the common subrecord IDLF (Flags)."""
    class _IdleAnimFlags(Flags):
        run_in_sequence: bool = flag(0)
        do_once: bool = flag(2)
        ignored_by_sandbox: bool = flag(4) # since Skyrim

    def __init__(self):
        super().__init__(b'IDLF', 'idle_anim_flags', self._IdleAnimFlags)

#------------------------------------------------------------------------------
class MelIdleEnam(MelString):
    """Handles the IDLE subrecord ENAM (Animation Event)."""
    def __init__(self):
        super().__init__(b'ENAM', 'animation_event')

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
            *color3_attrs('tint_color'))

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
    class _enit_flags(Flags):
        ingr_no_auto_calc: bool = flag(0)
        food_item: bool = flag(1)
        references_persist: bool = flag(8)

    def __init__(self):
        super().__init__(b'ENIT', ['i', 'I'], 'ingredient_value',
            (self._enit_flags, 'flags'))

#------------------------------------------------------------------------------
class MelInheritsSoundsFrom(MelFid):
    """Handles the CREA/NPC_ subrecord CSCR (Inherits Sounds From)."""
    def __init__(self):
        super().__init__(b'CSCR', 'inherits_sounds_from')

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
    """Handles the LAND subrecord MPCD (Hi-Res Heightfield Data)."""
    def __init__(self):
        super().__init__('hi_res_heightfield_data',
            MelBase(b'MPCD', 'unknown1'),
        )

#------------------------------------------------------------------------------
class MelLandShared(MelSequential):
    """Handles the LAND subrecords shared by all games."""
    class _land_flags(Flags):
        has_vertex_normals_height_map: bool = flag(0)
        has_vertex_colors: bool = flag(1)
        has_layers: bool = flag(2)
        auto_calc_normals: bool = flag(4)
        has_hi_res_heightfield: bool = flag(5) # since FO4
        has_mpcd: bool = flag(10) # Skyrim's version of has_hi_res_heightfield?

    def __init__(self, *, with_vtex: bool = False):
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
            (MelSimpleArray('vertex_textures', MelFid(b'VTEX'))
             if with_vtex else None),
        )

#------------------------------------------------------------------------------
class MelLctnShared(MelSequential):
    """Handles the LCTN subrecords shared between Skyrim and FO4."""
    def __init__(self):
        super().__init__(
            MelEdid(),
            # Persistent References -------------------------------------------
            MelSorted(MelArray('added_persistent_references',
                MelStruct(b'ACPR', ['2I', '2h'], (FID, 'acpr_ref'),
                    (FID, 'acpr_world_cell'), 'acpr_grid_x', 'acpr_grid_y'),
            ), sort_by_attrs='acpr_ref'),
            MelSorted(MelArray('master_persistent_references',
                MelStruct(b'LCPR', ['2I', '2h'], (FID, 'lcpr_ref'),
                    (FID, 'lcpr_world_cell'), 'lcpr_grid_x', 'lcpr_grid_y'),
            ), sort_by_attrs='lcpr_ref'),
            MelSorted(MelSimpleArray('removed_persistent_references',
                MelFid(b'RCPR'))),
            # Unique NPCs -----------------------------------------------------
            MelSorted(MelArray('added_unique_npcs',
                MelStruct(b'ACUN', ['3I'], (FID, 'acun_npc'),
                    (FID, 'acun_actor_ref'), (FID, 'acun_location')),
            ), sort_by_attrs='acun_actor_ref'),
            MelSorted(MelArray('master_unique_npcs',
                MelStruct(b'LCUN', ['3I'], (FID, 'lcun_npc'),
                    (FID, 'lcun_actor_ref'), (FID, 'lcun_location')),
            ), sort_by_attrs='lcun_actor_ref'),
            MelSorted(MelSimpleArray('removed_unique_npcs', MelFid(b'RCUN'))),
            # Special References ----------------------------------------------
            MelSorted(MelArray('added_special_references',
                MelStruct(b'ACSR', ['3I', '2h'], (FID, 'acsr_loc_ref_type'),
                    (FID, 'acsr_ref'), (FID, 'acsr_world_cell'), 'acsr_grid_x',
                    'acsr_grid_y'),
            ), sort_by_attrs='acsr_ref'),
            MelSorted(MelArray('master_special_references',
                MelStruct(b'LCSR', ['3I', '2h'], (FID, 'lcsr_loc_ref_type'),
                    (FID, 'lcsr_ref'), (FID, 'lcsr_world_cell'),
                    'lcsr_grid_x', 'lcsr_grid_y'),
            ), sort_by_attrs='lcsr_ref'),
            MelSorted(MelSimpleArray('removed_special_references',
                MelFid(b'RCSR'))),
            # Worldspace Cells ------------------------------------------------
            MelSorted(MelGroups('added_worldspace_cells',
                MelArray('acec_coordinates',
                    MelStruct(b'ACEC', ['2h'], 'acec_grid_x', 'acec_grid_y'),
                    prelude=MelFid(b'ACEC', 'acec_world'),
                ),
            ), sort_by_attrs='acec_world'),
            MelSorted(MelGroups('master_worldspace_cells',
                MelArray('lcec_coordinates',
                    MelStruct(b'LCEC', ['2h'], 'lcec_grid_x', 'lcec_grid_y'),
                    prelude=MelFid(b'LCEC', 'lcec_world'),
                ),
            ), sort_by_attrs='lcec_world'),
            MelSorted(MelGroups('removed_worldspace_cells',
                MelArray('rcec_coordinates',
                    MelStruct(b'RCEC', ['2h'], 'rcec_grid_x', 'rcec_grid_y'),
                    prelude=MelFid(b'RCEC', 'rcec_world'),
                ),
            ), sort_by_attrs='rcec_world'),
            # Initially Disabled References -----------------------------------
            MelSorted(MelSimpleArray('added_initially_disabled_references',
                MelFid(b'ACID'))),
            MelSorted(MelSimpleArray('master_initially_disabled_references',
                MelFid(b'LCID'))),
            # Enable Parent References ----------------------------------------
            MelSorted(MelArray('added_enable_parent_references',
                MelStruct(b'ACEP', ['2I', 'B', '3s'], (FID, 'acep_ref'),
                    (FID, 'acep_parent'), (EnableParentFlags, 'acep_flags'),
                    'acep_unused'),
            ), sort_by_attrs='acep_ref'),
            MelSorted(MelArray('master_enable_parent_references',
                MelStruct(b'LCEP', ['2I', '2h'], (FID, 'lcep_ref'),
                    (FID, 'lcep_parent'), (EnableParentFlags, 'lcep_flags'),
                    'lcep_unused'),
            ), sort_by_attrs='lcep_ref'),
            MelFull(),
            MelKeywords(),
            MelParent(),
            MelFid(b'NAM1', 'lctn_music'),
            MelFid(b'FNAM', 'unreported_crime_faction'),
            MelFid(b'MNAM', 'world_location_marker_ref'),
            MelFloat(b'RNAM', 'world_location_radius'),
        )

#------------------------------------------------------------------------------
class MelLensShared(MelSequential):
    """Handles the LENS subrecords shared between Skyrim and FO4."""
    class _lfs_flags(Flags):
        lfs_rotates: bool
        lfs_shrinks_when_occluded: bool

    def __init__(self, *, sprites_are_sorted=True):
        lfs_element = MelGroups('lens_flare_sprites',
            MelString(b'DNAM', 'lfs_sprite_id'),
            MelString(b'FNAM', 'lfs_texture'),
            MelStruct(b'LFSD', ['8f', 'I'], *color3_attrs('lfs_tint'),
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
class MelLinkColors(MelStruct):
    """Handles the common XCLP (Link Colors) subrecord."""
    def __init__(self):
        super().__init__(b'XCLP', ['3B', 's', '3B', 's'],
            *color_attrs('start_color'), *color_attrs('end_color'))

#------------------------------------------------------------------------------
class MelLinkedOcclusionReferences(MelStruct):
    """Hanldes the REFR subrecord XORD (Linked Occlusion References)."""
    def __init__(self):
        super().__init__(b'XORD', ['4I'],
            (FID, 'linked_occlusion_reference_right'),
            (FID, 'linked_occlusion_reference_left'),
            (FID, 'linked_occlusion_reference_bottom'),
            (FID, 'linked_occlusion_reference_top'))

#------------------------------------------------------------------------------
class MelLLChanceNone(MelUInt8): # required
    """Handles the leveled list subrecord LVLD (Chance None)."""
    _cn_sig = b'LVLD'

    def __init__(self):
        super().__init__(self._cn_sig, 'lvl_chance_none', set_default=0)

class MelLLChanceNoneTes3(MelLLChanceNone):
    """Morrowind version - different subrecord signature."""
    _cn_sig = b'NNAM'

#------------------------------------------------------------------------------
class _AMelLLFlags:
    """Base class for leveled list flags subrecords."""
    class _lvl_flags(Flags):
        calc_from_all_levels: bool
        calc_for_each_item: bool
        use_all_items: bool # since Oblivion
        special_loot: bool # Skyrim only
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
        super().__init__(MelSimpleGroups('ltex_grasses', MelFid(b'GNAM')))

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
    class _marker_flags(Flags):
        visible: bool
        can_travel_to: bool
        show_all_hidden: bool

    def __init__(self, *, with_reputation=False):
        group_elems = [
            MelBase(b'XMRK', 'marker_data'),
            MelUInt8Flags(b'FNAM', 'marker_flags', self._marker_flags),
            MelFull(),
            MelStruct(b'TNAM', ['B', 's'], 'marker_type', 'unused1'),
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
    class _matt_flags(Flags):
        stair_material: bool
        arrows_stick: bool
        can_tunnel: bool # since FO4

    def __init__(self):
        super().__init__(
            MelParent(),
            MelString(b'MNAM', 'matt_material_name'),
            MelStruct(b'CNAM', ['3f'], *color3_attrs('havok_display_color')),
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
class MelMesgButtons(MelGroups):
    """Implements the MESG subrecord ITXT and its conditions."""
    def __init__(self, conditions_element: MelBase):
        super().__init__('menu_buttons',
            MelLString(b'ITXT', 'button_text'),
            conditions_element,
        )

#------------------------------------------------------------------------------
class MelMesgSharedFo3(MelSequential):
    """Implements the MESG subrecords DNAM and TNAM."""
    class _MesgFlags(Flags):
        message_box: bool
        auto_display: bool # called 'Delay Initial Display' in FO4

    def __init__(self, *, prefix_elements: tuple[MelBase, ...] = ()):
        super().__init__(
            *prefix_elements,
            MelUInt32Flags(b'DNAM', 'mesg_flags', self._MesgFlags),
            MelUInt32(b'TNAM', 'display_time'),
        )

class MelMesgShared(MelMesgSharedFo3):
    """Implements the MESG subrecords INAM, QNAM, DNAM and TNAM."""
    def __init__(self):
        super().__init__(prefix_elements=(
            MelFid(b'INAM', 'unused_icon'), # leftover
            MelFid(b'QNAM', 'owner_quest'),
        ))

#------------------------------------------------------------------------------
class MelMgefData(MelPartialCounter):
    """Handles some common code for the MGEF subrecord DATA (Data)."""
    def __init__(self, struct_element: MelStruct):
        super().__init__(struct_element,
            counters={'counter_effect_count': 'counter_effects'})

#------------------------------------------------------------------------------
class MelMgefDnam(MelLString):
    """Handles the MGEF subrecord DNAM (Magic Item Description)."""
    def __init__(self):
        super().__init__(b'DNAM', 'magic_item_description')

#------------------------------------------------------------------------------
class _AMelMgefEsce(MelSorted):
    """Base class for the MGEF subrecord ESCE (Counter Effects)."""
    def __init__(self, *, array_type: type[MelArray | MelGroups],
            esce_element: MelBase, esce_attr: str):
        super().__init__(array_type('counter_effects',
            esce_element,
        ), sort_by_attrs=esce_attr)

class MelMgefEsceTes4(_AMelMgefEsce):
    """Handles the Oblivion version of ESCE, which stores FourCCs."""
    def __init__(self):
        super().__init__(
            array_type=MelArray,
            esce_element=MelStruct(b'ESCE', ['4s'], 'counter_effect_code'),
            esce_attr='counter_effect_code',
        )

class MelMgefEsce(_AMelMgefEsce):
    """Handles the post-Oblivion version of ESCE, which stores FormIDs."""
    def __init__(self):
        super().__init__(
            array_type=MelGroups,
            esce_element=MelFid(b'ESCE', 'counter_effect_fid'),
            esce_attr='counter_effect_fid',
        )

#------------------------------------------------------------------------------
class MelMgefSounds(MelArray):
    """Handles the MGEF subrecord SNDD (Sounds)."""
    def __init__(self):
        super().__init__('mgef_sounds',
            MelStruct(b'SNDD', ['2I'], 'ms_sound_type', (FID, 'ms_sound')),
        )

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
class MelMovtName(MelString):
    """Handles the MOVT subrecord MNAM (Name)."""
    def __init__(self):
        super().__init__(b'MNAM', 'movt_name')

#------------------------------------------------------------------------------
class MelMovtThresholds(MelStruct):
    """Handles the MOVT subrecord INAM (Anim Change Thresholds)."""
    def __init__(self):
        super().__init__(b'INAM', ['3f'], 'threshold_directional',
            'threshold_movement_speed', 'threshold_rotation_speed')

#------------------------------------------------------------------------------
class MelMuscShared(MelSequential):
    """Handles the MUSC subrecords FNAM, PNAM, WNAM and TNAM."""
    class _MusicTypeFlags(Flags):
        plays_one_selection: bool = flag(0)
        abrupt_transition: bool = flag(1)
        cycle_tracks: bool = flag(2)
        maintain_track_order: bool = flag(3)
        ducks_current_track: bool = flag(5)
        does_not_queue: bool = flag(6) # since SSE & FO4

    def __init__(self):
        super().__init__(
            MelUInt32Flags(b'FNAM', 'musc_flags', self._MusicTypeFlags),
            MelStruct(b'PNAM', ['2H'], 'musc_priority', 'musc_ducking'),
            MelFloat(b'WNAM', 'musc_fade_duration'),
            MelSimpleArray('musc_music_tracks', MelFid(b'TNAM')),
        )

#------------------------------------------------------------------------------
##: MUST is identical, but moving it to common_records is problematic due to
# every record in common_records.py getting instantiated for every game, so we
# end up with MelConditions() for games like Morrowind that don't have
# condition_function_data, which blows up on boot
class MelMustShared(MelSequential):
    """Handles the MUST subrecords shared between Skyrim and FO4."""
    def __init__(self, conditions_element: MelBase):
        super().__init__(
            MelEdid(),
            MelUInt32(b'CNAM', 'music_track_type'),
            MelFloat(b'FLTV', 'music_track_duration'),
            MelUInt32(b'DNAM', 'music_track_fade_out'),
            MelString(b'ANAM', 'music_track_file_name'),
            MelString(b'BNAM', 'music_track_finale_file_name'),
            MelStruct(b'LNAM', ['3f'], 'music_track_loop_begins',
                'music_track_loop_ends', 'music_track_loop_count'),
            MelSimpleArray('music_track_cue_points', MelFloat(b'FNAM')),
            conditions_element,
            MelSimpleArray('music_track_tracks', MelFid(b'SNAM')),
        )

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
class MelNoteType(MelUInt8):
    """Handles the NOTE subrecord DATA/DNAM (Type)."""
    def __init__(self, nt_sig: bytes):
        super().__init__(nt_sig, 'note_type')

#------------------------------------------------------------------------------
class MelNpcAnam(MelFid):
    """Handles the NPC_ subrecord ANAM (Far-away Model)."""
    def __init__(self):
        super().__init__(b'ANAM', 'far_away_model')

#------------------------------------------------------------------------------
class MelNpcClass(MelFid):
    """Handles the NPC_ subrecord CNAM (Class)."""
    def __init__(self):
        super().__init__(b'CNAM', 'npc_class')

#------------------------------------------------------------------------------
class MelNpcGiftFilter(MelFid):
    """Handles the NPC_ subrecord GNAM (Gift Filter)."""
    def __init__(self):
        super().__init__(b'GNAM', 'gift_filter')

#------------------------------------------------------------------------------
class MelNpcHairColor(MelFid):
    """Handles the NPC_ subrecord HCLF (Hair Color)."""
    def __init__(self):
        super().__init__(b'HCLF', 'hair_color')

#------------------------------------------------------------------------------
class MelNpcHeadParts(MelSorted):
    """Handles the NPC_ subrecord PNAM (Head Parts)."""
    def __init__(self):
        super().__init__(MelSimpleGroups('head_parts', MelFid(b'PNAM')))

#------------------------------------------------------------------------------
class MelNpcShared(MelSequential):
    """Handles the NPC_ subrecords DOFT, SOFT, DPLT, CRIF and FTST."""
    def __init__(self):
        super().__init__(
            MelFid(b'DOFT', 'default_outfit'),
            MelFid(b'SOFT', 'sleeping_outfit'),
            MelFid(b'DPLT', 'default_package_list'),
            MelFid(b'CRIF', 'crime_faction'),
            MelFid(b'FTST', 'head_texture'),
        )

#------------------------------------------------------------------------------
class MelNpcPerks(MelSequential):
    """Handles the NPC_ subrecords PRKZ (Perk Count) and PRKR (Perks). FO4 got
    rid of the unused data."""
    def __init__(self, *, with_unused=False):
        prkr_types = ['I', 'B']
        prkr_args = [(FID, 'npc_perk_fid'), 'npc_perk_rank']
        if with_unused:
            prkr_types.append('3s')
            prkr_args.append('npc_perk_unused')
        super().__init__(
            MelCounter(MelUInt32(b'PRKZ', 'npc_perk_count'),
                counts='npc_perks'),
            MelSorted(MelGroups('npc_perks',
                MelStruct(b'PRKR', prkr_types, *prkr_args),
            ), sort_by_attrs='npc_perk_fid'),
        )

#------------------------------------------------------------------------------
class MelOcclusionPlane(MelStruct):
    """Handles the REFR subrecord XOCP (Occlusion Plane Data)."""
    def __init__(self):
        super().__init__(b'XOCP', ['9f'], 'occlusion_plane_width',
            'occlusion_plane_height', *position_attrs('occlusion_plane'),
            # This is most likely a quaternion
            'occlusion_plane_rot_a', 'occlusion_plane_rot_b',
            'occlusion_plane_rot_c', 'occlusion_plane_rot_d'),

#------------------------------------------------------------------------------
class MelOverridePackageLists(MelSequential):
    """Handles the NPC_/QUST subrecords SPOR, OCOR, GWOR and ECOR."""
    def __init__(self):
        super().__init__(
            MelFid(b'SPOR', 'override_package_list_spectator'),
            MelFid(b'OCOR', 'override_package_list_observe_dead_body'),
            MelFid(b'GWOR', 'override_package_list_guard_warn'),
            MelFid(b'ECOR', 'override_package_list_combat'),
        )

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
class MelPackDataInputs(MelGroups):
    """Handles the PACK subrecords UNAM, BNAM and PNAM (Data Inputs)."""
    def __init__(self, attr):
        super().__init__(attr,
            MelSInt8(b'UNAM', 'input_index'),
            MelString(b'BNAM', 'input_name'),
            MelUInt32Bool(b'PNAM', 'input_public'),
        )

#------------------------------------------------------------------------------
class MelPackDataInputValues(MelGroups):
    """Handles the PACK subrecord complex for Data Input Values. Needs the
    right PLDT (aka MelLocation) and PTDA implementations passed to it."""
    def __init__(self, *, pldt_element: MelBase, ptda_element: MelBase):
        super().__init__('data_input_values',
            MelString(b'ANAM', 'data_input_value_type'),
            MelUnion({
                'Bool': MelUInt8(b'CNAM', 'data_input_value_val'),
                'Int': MelUInt32(b'CNAM', 'data_input_value_val'),
                'Float': MelFloat(b'CNAM', 'data_input_value_val'),
                # Mirrors what xEdit does, despite how weird it looks
                'ObjectList': MelFloat(b'CNAM', 'data_input_value_val'),
            }, decider=AttrValDecider('data_input_value_type'),
                # All other kinds of values, typically missing
                fallback=MelBase(b'CNAM', 'data_input_value_val')),
            MelBase(b'BNAM', 'unknown1'),
            MelTopicData('value_topic_data'),
            pldt_element,
            ptda_element,
            MelBase(b'TPIC', 'unknown2'),
        )

#------------------------------------------------------------------------------
class MelPackOwnerQuest(MelFid):
    """Handles the PACK subrecord QNAM (Owner Quest)."""
    def __init__(self):
        super().__init__(b'QNAM', 'owner_quest')

#------------------------------------------------------------------------------
class MelPackPkcu(MelStruct):
    """Handles the PACK subrecord PKCU (Counter)."""
    def __init__(self):
        super().__init__(b'PKCU', ['3I'], 'data_input_count',
            (FID, 'package_template'), 'version_counter')

#------------------------------------------------------------------------------
class MelPackPkdt(MelStruct):
    """Handles the new (since Skyrim) version of the PACK subrecord PKDT
    (Package Data)."""
    def __init__(self):
        super().__init__(b'PKDT', ['I', '3B', 's', 'H', '2s'],
            (PackGeneralFlags, 'package_flags'), 'package_ai_type',
            'interrupt_override', 'preferred_speed', 'unknown_pkdt1',
            (PackInterruptFlags, 'interrupt_flags'), 'unknown_pkdt2')

#------------------------------------------------------------------------------
class MelPackIdleHandler(MelGroup):
    """Handles the PACK subrecords POBA, POCA and POEA (On Begin, On Change and
    On End, respectively). Used to have some CK leftovers in it (pre-FO4)."""
    # The subrecord type used for the marker
    _attr_lookup = {
        'on_begin': b'POBA',
        'on_change': b'POCA',
        'on_end': b'POEA',
    }

    def __init__(self, attr, *, ck_leftovers: tuple[MelBase, ...] = ()):
        super().__init__(attr,
            MelBase(self._attr_lookup[attr], f'{attr}_marker'),
            MelFid(b'INAM', 'idle_anim'),
            *ck_leftovers,
            MelTopicData('idle_topic_data'),
        )

#------------------------------------------------------------------------------
class MelPackProcedureTree(MelGroups):
    """Handles the PACK Procedure Tree subrecord complex. Needs a MelConditions
    implementation passed to it."""
    class _SubBranchFlags(Flags): # One unknown flag, not just a bool
        repeat_when_complete: bool

    def __init__(self, conditions_element: MelBase):
        super().__init__('procedure_tree_branches',
            MelString(b'ANAM', 'branch_type'),
            conditions_element,
            MelStruct(b'PRCB', ['2I'], 'sub_branch_count',
                (self._SubBranchFlags, 'sub_branch_flags')),
            MelString(b'PNAM', 'procedure_type'),
            MelUInt32Bool(b'FNAM', 'success_completes_package'),
            MelSimpleGroups('data_input_indices', MelUInt8(b'PKC2')),
            MelGroups('flag_overrides',
                MelStruct(b'PFO2', ['2I', '2H', 'B', '3s'],
                    (PackGeneralFlags, 'set_general_flags'),
                    (PackGeneralFlags, 'clear_general_flags'),
                    (PackInterruptFlags, 'set_interrupt_flags'),
                    (PackInterruptFlags, 'clear_interrupt_flags'),
                    'preferred_speed_override', 'unknown_pfo2'),
            ),
            MelGroups('ptb_unknown1',
                MelBase(b'PFOR', 'unknown_pfor'),
            ),
        ),

#------------------------------------------------------------------------------
class MelPackSchedule(MelStruct):
    """Handles the new (since Skyrim) version of the PACK subrecord PSDT
    (Schedule)."""
    def __init__(self):
        super().__init__(b'PSDT', ['2b', 'B', '2b', '3s', 'i'],
            'schedule_month', 'schedule_day', 'schedule_date', 'schedule_hour',
            'schedule_minute', 'unused1', 'schedule_duration')

#------------------------------------------------------------------------------
class MelPackScheduleOld(MelStruct):
    """Handles the old (pre-Skyrim) version of the PACK subrecord PSDT
    (Schedule)."""
    def __init__(self, *, is_required: bool):
        super().__init__(b'PSDT', ['2b', 'B', 'b', 'i'], 'schedule_month',
            'schedule_day', 'schedule_date', 'schedule_time',
            'schedule_duration', is_required=is_required)

#------------------------------------------------------------------------------
class MelParent(MelFid):
    """Handles the common subrecord PNAM (Parent)."""
    def __init__(self):
        super().__init__(b'PNAM', 'parent_fid')

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
class MelProjMuzzleFlashModel(MelGroup):
    """Handles the PROJ subrecords NAM1 and NAM2 (Muzzle Flash Model)."""
    def __init__(self, ignore_texture_hashes=True):
        super().__init__('muzzle_flash_model',
            MelString(b'NAM1', 'muzzle_flash_path'),
            # Ignore texture hashes - they're only an optimization, plenty of
            # records in Skyrim.esm are missing them
            (MelNull(b'NAM2') if ignore_texture_hashes else
             MelBase(b'NAM2', 'muzzle_flash_hashes')),
        )

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
        super().__init__(MelSimpleGroups('random_teleports', MelFid(b'TNAM')))

#------------------------------------------------------------------------------
class MelRef3D(MelStruct):
    """3D position and rotation for a reference record (REFR, ACHR, etc.)."""
    def __init__(self):
        super().__init__(b'DATA', ['6f'], *position_attrs('ref'),
            *rotation_attrs('ref'))

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
    class _watertypeFlags(Flags):
        reflection: bool
        refraction: bool

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
class MelRegnAreas(MelGroups):
    """Handles the REGN subrecords RPLI and RPLD (and ANAM in FO4)."""
    def __init__(self, with_unknown_anam=False):
        super().__init__('regn_areas',
            MelUInt32(b'RPLI', 'edge_falloff'),
            MelArray('regn_area_points',
                MelStruct(b'RPLD', ['2f'], 'regn_ap_x', 'regn_ap_y'),
            ),
            MelBase(b'ANAM', 'unknown_anam') if with_unknown_anam else None,
        )

#------------------------------------------------------------------------------
class MelRegnRdat(MelExtra):
    """Handles the REGN subrecord RDAT (Data Header)."""
    def __init__(self):
        ##: xEdit marks the last unknown as 2 bytes, but only in Oblivion. In
        # all other games they are an unlimited-length byte array. Figure
        # out if 2 bytes (which is what we had for all games) is correct and
        # submit a PR to xEdit to fix that if it is
        super().__init__(MelStruct(b'RDAT', ['I', '2B'],
            'regn_data_type', 'regn_data_override', 'regn_data_priority'),
            extra_attr='regn_data_unknown')

#------------------------------------------------------------------------------
class MelRegnEntrySubrecord(MelUnion):
    """Wrapper around MelUnion to correctly read/write REGN entry data.
    Skips loading and dumping if regn_data_type != entry_type_val.

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
        }, decider=AttrValDecider('regn_data_type'),
            fallback=MelNull(b'NULL')) # ignore

#------------------------------------------------------------------------------
class MelRegnEntryGrasses(MelRegnEntrySubrecord):
    """Handles the REGN subrecord RDGS (Grasses)."""
    def __init__(self):
        super().__init__(6, MelSorted(MelArray('regn_grasses',
            MelStruct(b'RDGS', ['I', '4s'], (FID, 'regn_grass_fid'),
                'regn_grass_unknown'),
        ), sort_by_attrs='regn_grass_fid'))

#------------------------------------------------------------------------------
class MelRegnEntryMapName(MelRegnEntrySubrecord):
    """Handles the REGN subrecord RDMP (Map Name)."""
    def __init__(self):
        super().__init__(4, MelString(b'RDMP', 'regn_map_name'))

#------------------------------------------------------------------------------
class MelRegnEntryMusic(MelRegnEntrySubrecord):
    """Handles the REGN subrecord RDMO (Music) - FO3 and newer."""
    def __init__(self):
        super().__init__(7, MelFid(b'RDMO', 'regn_music'))

#------------------------------------------------------------------------------
class MelRegnEntryMusicType(MelRegnEntrySubrecord):
    """Handles the REGN subrecord RDMD (Music Type) - FO3 and older."""
    def __init__(self):
        super().__init__(7, MelUInt32(b'RDMD', 'regn_music_type'))

#------------------------------------------------------------------------------
class _AMelRegnEntrySounds(MelRegnEntrySubrecord):
    """Base class for MelRegnEntrySounds and MelRegnEntrySoundsOld since they
    share the same flags and attrs, only signature and attr types differ."""
    _rds_sig: bytes
    _rds_fmt: list[str]

    class _SoundFlags(Flags):
        regn_sound_pleasant: bool
        regn_sound_cloudy: bool
        regn_sound_rainy: bool
        regn_sound_snowy: bool

    def __init__(self):
        super().__init__(7, MelSorted(MelArray('regn_sounds',
            MelStruct(self._rds_sig, self._rds_fmt,
                (FID, 'regn_sound_fid'),
                (self._SoundFlags, 'regn_sound_flags'), 'regn_sound_chance'),
            ), sort_by_attrs='regn_sound_fid'))

class MelRegnEntrySounds(_AMelRegnEntrySounds):
    """Handles the REGN subrecord RDSA (Sounds) - Skyrim and newer."""
    _rds_sig = b'RDSA'
    _rds_fmt = ['2I', 'f']

class MelRegnEntrySoundsOld(_AMelRegnEntrySounds):
    """Handles the REGN subrecord RDSD (Sounds) - FO3 and older."""
    _rds_sig = b'RDSD'
    _rds_fmt = ['3I']

#------------------------------------------------------------------------------
class MelRegnEntryObjects(MelRegnEntrySubrecord):
    """Handles the REGN subrecord RDOT (Objects)."""
    class _ObjectFlags(Flags):
        regn_obj_conform_to_slope: bool
        regn_obj_paint_vertices: bool
        regn_obj_delta_size_variance: bool
        regn_obj_delta_x: bool
        regn_obj_delta_y: bool
        regn_obj_delta_z: bool
        regn_obj_tree: bool
        regn_obj_huge_rock: bool

    def __init__(self):
        super().__init__(2, MelArray('regn_objects',
            MelStruct(b'RDOT',
                ['I', 'H', '2s', 'f', '4B', '2H', '5f', '3H', '2s', '4s'],
                (FID, 'regn_obj_fid'), 'regn_obj_parent_index',
                'regn_obj_unknown1', 'regn_obj_density', 'regn_obj_clustering',
                'regn_obj_min_slope', 'regn_obj_max_slope',
                (self._ObjectFlags, 'regn_obj_flags'),
                'regn_obj_radius_wrt_parent', 'regn_obj_radius',
                'regn_obj_min_height', 'regn_obj_max_height', 'regn_obj_sink',
                'regn_obj_sink_var', 'regn_obj_size_var',
                *rotation_attrs('regn_obj_angle_var'), 'regn_obj_unknown2',
                'regn_obj_unknown3'),
            ))

#------------------------------------------------------------------------------
class MelRegnEntryWeatherTypes(MelRegnEntrySubrecord):
    """Handles the REGN subrecord RDWT (Weather Types) - FO3 added a new
    FormID (Global) to the end."""
    def __init__(self, with_global=True):
        rdwt_elements = [(FID, 'regn_wt_weather'), 'regn_wt_chance']
        rdwt_fmt = ['I', 'I']
        if with_global:
            rdwt_elements.append((FID, 'regn_wt_global'))
            rdwt_fmt.append('I')
        super().__init__(3, MelSorted(MelArray('regn_weather_types',
            MelStruct(b'RDWT', rdwt_fmt, *rdwt_elements),
        ), sort_by_attrs='regn_wt_weather'))

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
class MelRevbData(MelStruct):
    """Handles the REVB subrecord DATA (Data)."""
    def __init__(self):
        super().__init__(b'DATA', ['2H', '4b', '6B'], 'revb_decay_time',
            'revb_hf_reference', 'revb_room_filter', 'revb_room_hf_filter',
            'revb_reflections', 'revb_reverb_amp', 'revb_decay_hf_ratio',
            'revb_reflect_delay', 'revb_reverb_delay', 'revb_diffusion',
            'revb_density', 'revb_unknown', is_required=True)

#------------------------------------------------------------------------------
class MelScolParts(MelGroups):
    """Handles the SCOL subrecords ONAM and DATA (Parts)."""
    def __init__(self):
        super().__init__('scol_parts',
            MelFid(b'ONAM', 'scol_part_static'),
            MelSorted(MelArray('scol_part_placements',
                MelStruct(b'DATA', ['7f'], *position_attrs('scol_part'),
                    *rotation_attrs('scol_part'), 'scol_part_scale'),
            ), sort_by_attrs=(*position_attrs('scol_part'),
                              *rotation_attrs('scol_part'),
                              'scol_part_scale')),
        )

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
            'sip_fall', 'sip_winter')

#------------------------------------------------------------------------------
class MelShortName(MelLString):
    """Defines a 'Short Name' subrecord. Most common signature is ONAM."""
    def __init__(self, sn_sig=b'ONAM'):
        super().__init__(sn_sig, 'short_name')

#------------------------------------------------------------------------------
class MelSkin(MelFid):
    """Handles the common WNAM (Skin) subrecord."""
    def __init__(self):
        super().__init__(b'WNAM', 'skin')

#------------------------------------------------------------------------------
class MelSkipInterior(MelUnion):
    """Union that skips dumping if we're in an interior."""
    def __init__(self, element):
        super().__init__({
            True: MelReadOnly(element),
            False: element,
        }, decider=FlagDecider('flags', ['isInterior']))

#------------------------------------------------------------------------------
class _MelSMFlags(MelStruct):
    """Handles Story Manager flags shared by SMBN, SMQN and SMEN."""
    class _NodeFlags(Flags):
        sm_random: bool
        no_child_warn: bool

    class _QuestFlags(Flags):
        do_all_before_repeating: bool
        shares_event: bool
        num_quests_to_run: bool

    def __init__(self, with_quest_flags=False):
        sm_fmt = ['I']
        sm_elements = [(self._NodeFlags, 'node_flags')]
        if with_quest_flags:
            sm_fmt = ['2H']
            sm_elements.append((self._QuestFlags, 'quest_flags'))
        super().__init__(b'DNAM', sm_fmt, *sm_elements)

class _StoryManagerShared(MelSequential):
    """Deduplicates some subrecords shared by SMBN, SMEN and SMQN."""
    def __init__(self, conditions_element: MelBase, with_quest_flags=False):
        super().__init__(
            MelEdid(),
            MelParent(),
            MelFid(b'SNAM', 'child_fid'),
            conditions_element,
            _MelSMFlags(with_quest_flags=with_quest_flags),
            MelUInt32(b'XNAM', 'max_concurrent_quests'),
        )

##: Same situation as with MelMustShared above
class MelSmbnShared(_StoryManagerShared):
    """Handles the subrecords shared by SMBN."""

#------------------------------------------------------------------------------
##: Same situation as with MelMustShared above
class MelSmenShared(MelSequential):
    """Handles the subrecords shared by SMEN."""
    def __init__(self, conditions_element: MelBase):
        super().__init__(
            _StoryManagerShared(conditions_element),
            MelUInt32(b'ENAM', 'sm_type'),
        )

#------------------------------------------------------------------------------
##: Same situation as with MelMustShared above
class MelSmqnShared(MelSequential):
    """Handles the subrecords shared by SMQN."""
    def __init__(self, conditions_element: MelBase,
            with_extra_hours_until_reset=False):
        super().__init__(
            _StoryManagerShared(conditions_element, with_quest_flags=True),
            MelUInt32(b'MNAM', 'num_quests_to_run'),
            (MelFloat(b'HNAM', 'hours_until_reset')
             if with_extra_hours_until_reset else None),
            MelCounter(MelUInt32(b'QNAM', 'sm_quest_count'),
                counts='sm_quests'),
            MelGroups('sm_quests',
                MelFid(b'NNAM', 'sm_quest_fid'),
                MelUInt32(b'FNAM', 'sm_quest_flags'), # All flags unknown
                MelFloat(b'RNAM', 'hours_until_reset'),
            ),
        )

#------------------------------------------------------------------------------
class MelSnctFlags(MelUInt32Flags):
    """Handles the SNCT subrecord FNAM (Flags)."""
    class _SnctFnamFlags(Flags):
        mute_when_submerged: bool
        should_appear_on_menu: bool
        immune_to_time_speedup: bool # since FO4
        pause_during_menus_immed: bool # since FO4
        pause_during_menus_fade: bool # since FO4
        exclude_from_player_opm_override: bool # since FO4
        pause_during_start_menu: bool # since FO4

    def __init__(self):
        super().__init__(b'FNAM', 'snct_flags', self._SnctFnamFlags) # required

#------------------------------------------------------------------------------
class MelSnctVnamUnam(MelSequential):
    """Handles the SNCT subrecords VNAM (Static Volume Multiplier) and UNAM
    (Default Menu Value)."""
    def __init__(self):
        super().__init__(
            MelUInt16(b'VNAM', 'static_volume_multiplier'),
            MelUInt16(b'UNAM', 'default_menu_value'),
        )

#------------------------------------------------------------------------------
class MelSndrBnam(MelStruct):
    """Handles the SNDR subrecord BNAM (Values)."""
    def __init__(self):
        super().__init__(b'BNAM', ['2b', '2B', 'H'], 'pct_frequency_shift',
            'pct_frequency_variance', 'descriptor_priority', 'db_variance',
            'static_attenuation')

#------------------------------------------------------------------------------
class MelSndrCategory(MelFid):
    """Handles the SNDR subrecord GNAM (Category)."""
    def __init__(self):
        super().__init__(b'GNAM', 'descriptor_category')

#------------------------------------------------------------------------------
class MelSndrLnam(MelStruct):
    """Handles the SNDR subrecord LNAM (Values)."""
    def __init__(self):
        # 'sidechain' is marked unknown in Skyrim - no matter, both are 1 byte
        # and having it as an int can't hurt
        super().__init__(b'LNAM', ['s', '3B'], 'unknown1', 'looping_type',
            'sidechain', 'rumble_send_value')

#------------------------------------------------------------------------------
class MelSndrOutputModel(MelFid):
    """Handles the SNDR subrecord ONAM (Output Model)."""
    def __init__(self):
        super().__init__(b'ONAM', 'output_model')

#------------------------------------------------------------------------------
class MelSndrSounds(MelGroups):
    """Handles the SNDR subrecord ANAM (Sounds)."""
    def __init__(self):
        super().__init__('sound_files',
            MelString(b'ANAM', 'sound_file_name'),
        )

#------------------------------------------------------------------------------
class MelSndrType(MelUInt32):
    """Handles the SNDR subrecord CNAM (Descriptor Type)."""
    def __init__(self):
        super().__init__(b'CNAM', 'descriptor_type')

#------------------------------------------------------------------------------
class MelSopmData(MelStruct):
    """Handles the SOPM subrecord NAM1 (Data)."""
    class _SopmFlags(Flags):
        attenuates_with_distance: bool
        allows_rumble: bool
        applies_doppler: bool # since FO4
        applies_distance_delay: bool # since FO4
        player_output_model: bool # since FO4
        try_play_on_controller: bool # since FO4
        causes_ducking: bool # since FO4
        avoids_ducking: bool # since FO4

    def __init__(self):
        super().__init__(b'NAM1', ['B', '2s', 'B'],
            (self._SopmFlags, 'sopm_flags'), 'sopm_nam1_unknown',
            'reverb_send_pct')

#------------------------------------------------------------------------------
class MelSopmType(MelUInt32):
    """Handles the SOPM subrecord MNAM (Type)."""
    def __init__(self):
        super().__init__(b'MNAM', 'sopm_type')

#------------------------------------------------------------------------------
def _channel_attrs(channel_index: int) -> list[str]:
    """Helper method for generating SOPM channel attributes."""
    return [f'ch{channel_index}_{x}' for x in ('fl', 'fr', 'c', 'lfe', 'rl',
                                               'rr', 'sl', 'sr')]

class MelSopmOutputValues(MelStruct):
    """Handles the SOPM subrecord ONAM (Output Values)."""
    def __init__(self):
        super().__init__(b'ONAM', ['24B'], *_channel_attrs(0),
            *_channel_attrs(1), *_channel_attrs(2))

#------------------------------------------------------------------------------
class MelSound(MelFid):
    """Handles the common SNAM (Sound) subrecord."""
    def __init__(self):
        super().__init__(b'SNAM', 'sound')

#------------------------------------------------------------------------------
class MelSoundActivation(MelFid):
    """Handles the ACTI subrecord VNAM (Sound - Activation)."""
    def __init__(self):
        super().__init__(b'VNAM', 'sound_activation')

#------------------------------------------------------------------------------
class MelSoundClose(MelFid):
    """Handles the CONT/DOOR subrecord QNAM/ANAM (Sound - Close)."""
    def __init__(self, sc_sig=b'QNAM'):
        super().__init__(sc_sig, 'sound_close')

#------------------------------------------------------------------------------
class MelSoundLevel(MelUInt32):
    """Handles the common subrecord NAM5/NAM8/VNAM (Sound Level)."""
    def __init__(self, sl_sig=b'VNAM'):
        super().__init__(sl_sig, 'sound_level')

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
            MelFid(b'YNAM', 'sound_pickup'),
            MelFid(b'ZNAM', 'sound_drop'),
        )

#------------------------------------------------------------------------------
class MelSounSdsc(MelFid):
    """Handles the SOUN subrecord SDSC (Sound Descriptor)."""
    def __init__(self):
        super().__init__(b'SDSC', 'sound_descriptor')

#------------------------------------------------------------------------------
class MelSpellCounter(MelCounter):
    """Handles the SPCT (Spell Counter) subrecord. To be used in combination
    with MelSpells."""
    def __init__(self):
        super().__init__(MelUInt32(b'SPCT', 'spell_count'), counts='spells')

#------------------------------------------------------------------------------
class MelSpells(MelSorted):
    """Handles the common SPLO subrecord."""
    def __init__(self):
        super().__init__(MelSimpleGroups('spells', MelFid(b'SPLO')))

#------------------------------------------------------------------------------
class MelSpit(MelStruct):
    """Handles the SPIT subrecord since Skyrim."""
    class _SpitFlags(Flags):
        manual_cost_calc: bool = flag(0)
        pc_start_spell: bool = flag(17)
        area_effect_ignores_los: bool = flag(19)
        ignore_resistance: bool = flag(20)
        no_absorb_reflect: bool = flag(21)
        no_dual_cast_modification: bool = flag(23)

    def __init__(self):
        super().__init__(b'SPIT', ['3I', 'f', '2I', '2f', 'I'], 'spell_cost',
            (self._SpitFlags, 'spell_flags'), 'spell_type',
            'spell_charge_time', 'spell_cast_type', 'spell_target_type',
            'spell_cast_duration', 'spell_range', (FID, 'casting_perk'))

#------------------------------------------------------------------------------
class MelSpitOld(MelStruct):
    """Handles the SPIT subrecord pre-Skyrim."""
    class SpellFlagsOld(Flags):
        """Implements the SPEL flags for pre-Skyrim games."""
        manual_cost_calc: bool = flag(0)
        immune_to_silence: bool = flag(1)
        pc_start_spell: bool = flag(2)
        area_effect_ignores_los: bool = flag(4)
        script_effect_always_applies: bool = flag(5)
        no_absorb_reflect: bool = flag(6)
        touch_spell_explodes_without_target: bool = flag(7)

        def __setitem__(self, index, value):
            # immune_to_silence activates bits 1 and 3
            Flags.__setitem__(self, index, value)
            if index == 1:
                Flags.__setitem__(self, 3, value)

    def __init__(self):
        super().__init__(b'SPIT', ['3I', 'B', '3s'], 'spell_type',
            'spell_cost', 'spell_level', (self.SpellFlagsOld, 'spell_flags'),
            'unused1')

#------------------------------------------------------------------------------
class MelTactVnam(MelFid):
    """Handles the TACT subrecord VNAM (Voice Type)."""
    def __init__(self):
        super().__init__(b'VNAM', 'activator_voice_type')

#------------------------------------------------------------------------------
class MelTemplate(MelFid):
    """Handles the CREA/NPC_ subrecord TPLT (Template). Has become "Default
    Template" in FO4."""
    def __init__(self, template_attr='template'):
        super().__init__(b'TPLT', template_attr)

#------------------------------------------------------------------------------
class MelTemplateArmor(MelFid):
    """Handles the ARMO subrecord TNAM (Template Armor)."""
    def __init__(self):
        super().__init__(b'TNAM', 'template_armor')


#------------------------------------------------------------------------------
class MelTopicData(MelGroups):
    """Handles the common PDTO (Topic Data) subrecord."""
    def __init__(self, attr: str):
        super().__init__(attr,
            MelUnion({
                0: MelStruct(b'PDTO', ['2I'], 'data_type', (FID, 'topic_ref')),
                1: MelStruct(b'PDTO', ['I', '4s'], 'data_type',
                             'topic_subtype'),
            }, decider=PartialLoadDecider(
                loader=MelUInt32(b'PDTO', 'data_type'),
                decider=AttrValDecider('data_type')),
            fallback=MelNull(b'NULL')), # ignore
        )

#------------------------------------------------------------------------------
class MelTxstFlags(MelUInt16Flags):
    """Handles the TXST subrecord DNAM (Flags)."""
    class _txst_flags(Flags):
        no_specular_map: bool
        facegen_textures: bool # since Skyrim
        has_model_space_normal_map: bool # since Skyrim

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
class MelVoice(MelFid):
    """Handles the common VTCK (Voice) subrecord."""
    def __init__(self):
        super().__init__(b'VTCK', 'voice')

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
class MelWorldspace(MelFid):
    """Handles the REGN/WRLD subrecord WNAM (Worldspace)."""
    def __init__(self, ws_attr='worldspace'):
        super().__init__(b'WNAM', ws_attr)

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
class MelXlod(MelStruct):
    """Distant LOD Data."""
    def __init__(self):
        super().__init__(b'XLOD', ['3f'], 'lod1', 'lod2', 'lod3')
