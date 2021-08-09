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
"""This module contains the skyrim record classes."""
from collections import OrderedDict
from ... import brec, bolt, bush
from ...bolt import Flags, struct_pack, structs_cache, unpack_str16
from ...brec import MelRecord, MelObject, MelGroups, MelStruct, FID, \
    MelGroup, MelString, MreLeveledListBase, MelSet, MelFid, MelNull, \
    MelOptStruct, MelFids, MreHeaderBase, MelBase, MelFidList, MelRelations, \
    MreGmstBase, MelLString, MelMODS, MelColorInterpolator, MelRegions, \
    MelValueInterpolator, MelUnion, AttrValDecider, MelRegnEntrySubrecord, \
    PartialLoadDecider, FlagDecider, MelFloat, MelSInt8, MelSInt32, MelUInt8, \
    MelUInt16, MelUInt32, MelActionFlags, MelCounter, MelRaceData, \
    MelPartialCounter, MelBounds, null3, null4, MelSequential, \
    MelTruncatedStruct, MelIcons, MelIcons2, MelIcon, MelIco2, MelEdid, \
    MelFull, MelArray, MelWthrColors, MelFactions, MelReadOnly, \
    MreActorBase, MreWithItems, MelCtdaFo3, MelRef3D, MelXlod, \
    MelWorldBounds, MelEnableParent, MelRefScale, MelMapMarker, MelMdob, \
    MelEnchantment, MelDecalData, MelDescription, MelSInt16, MelSkipInterior, \
    MelPickupSound, MelDropSound, MelActivateParents, BipedFlags, MelColor, \
    MelColorO, MelSpells, MelFixedString, MelUInt8Flags, MelUInt16Flags, \
    MelUInt32Flags, MelOwnership, MelDebrData, get_structs, MelWeatherTypes, \
    MelActorSounds, MelFactionRanks, MelSorted, vmad_properties_key, \
    vmad_qust_fragments_key, vmad_fragments_key, vmad_script_key, \
    vmad_qust_aliases_key, MelReflectedRefractedBy, perk_effect_key
from ...exception import ModError, ModSizeError, StateError

# Set MelModel in brec but only if unset, otherwise we are being imported from
# fallout4.records
if brec.MelModel is None:

    class _MelModel(MelGroup):
        """Represents a model record."""
        # MODB and MODD are no longer used by TES5Edit
        typeSets = {
            b'MODL': (b'MODL', b'MODT', b'MODS'),
            b'MOD2': (b'MOD2', b'MO2T', b'MO2S'),
            b'MOD3': (b'MOD3', b'MO3T', b'MO3S'),
            b'MOD4': (b'MOD4', b'MO4T', b'MO4S'),
            b'MOD5': (b'MOD5', b'MO5T', b'MO5S'),
            b'DMDL': (b'DMDL', b'DMDT', b'DMDS'),
        }

        def __init__(self, attr=u'model', mel_sig=b'MODL'):
            types = self.__class__.typeSets[mel_sig]
            MelGroup.__init__(
                self, attr,
                MelString(types[0], u'modPath'),
                # Ignore texture hashes - they're only an optimization, plenty
                # of records in Skyrim.esm are missing them
                MelNull(types[1]),
                MelMODS(types[2], u'alternateTextures')
            )

    brec.MelModel = _MelModel
from ...brec import MelModel

#------------------------------------------------------------------------------
_is_sse = bush.game.fsName in (
    u'Skyrim Special Edition', u'Skyrim VR', u'Enderal Special Edition',
    u'Skyrim Special Edition MS')
def if_sse(le_version, se_version):
    """Resolves to one of two different objects, depending on whether we're
    managing Skyrim LE or SE."""
    return se_version if _is_sse else le_version

def sse_only(sse_obj):
    """Wrapper around if_sse that resolves to None for SLE. Useful for things
    that have been added in SSE as MelSet will ignore None elements. Can also
    be used with Flags, but keep in mind that a None flag will still take up an
    index in the flags list, so it's a good idea to specify flag indices
    explicitly when using it."""
    return if_sse(le_version=None, se_version=sse_obj)

#------------------------------------------------------------------------------
# Record Elements    ----------------------------------------------------------
#------------------------------------------------------------------------------
##: See what we can do with MelUnion & MelTruncatedStruct here
class MelBipedObjectData(MelStruct):
    """Handler for BODT/BOD2 subrecords.  Reads both types, writes only BOD2"""
    _bp_flags = BipedFlags()

    # Legacy Flags, (For BODT subrecords) - #4 is the only one not discarded.
    LegacyFlags = Flags(0, Flags.getNames(
        u'modulates_voice', # From ARMA
        u'unknown_2',
        u'unknown_3',
        u'unknown_4',
        u'non_playable', # From ARMO
        u'unknown_6',
        u'unknown_7',
        u'unknown_8',
    ), unknown_is_unused=True) # mirrors xEdit, though it doesn't make sense

    ArmorTypeFlags = Flags(0, Flags.getNames(
        u'light_armor',
        u'heavy_armor',
        u'clothing',
    ))

    def __init__(self):
        super(MelBipedObjectData, self).__init__(b'BOD2', [u'2I'],
            (MelBipedObjectData._bp_flags, u'biped_flags'),
            (MelBipedObjectData.ArmorTypeFlags, u'armorFlags'))

    def getLoaders(self,loaders):
        # Loads either old style BODT or new style BOD2 records
        loaders[b'BOD2'] = self
        loaders[b'BODT'] = self

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        __unpacker2=structs_cache[u'IB3s'].unpack
        __unpacker3=structs_cache[u'IB3sI'].unpack
        if sub_type == b'BODT':
            # Old record type, use alternate loading routine
            if size_ == 8:
                # Version 20 of this subrecord is only 8 bytes (armorType
                # omitted)
                bp_flags, legacyFlags, _bp_unused = ins.unpack(
                    __unpacker2, size_, *debug_strs)
                armorFlags = 0
            elif size_ != 12:
                raise ModSizeError(ins.inName, debug_strs, (12, 8), size_)
            else:
                bp_flags, legacyFlags, _bp_unused, armorFlags = ins.unpack(
                    __unpacker3, size_, *debug_strs)
            # legacyData is discarded except for non-playable status
            record.biped_flags = MelBipedObjectData._bp_flags(bp_flags)
            record.flags1.isNotPlayable = MelBipedObjectData.LegacyFlags(
                legacyFlags)[4]
            record.armorFlags = MelBipedObjectData.ArmorTypeFlags(armorFlags)
        else:
            # BOD2 - new style, MelStruct can handle it
            super(MelBipedObjectData, self).load_mel(record, ins, sub_type,
                                                     size_, *debug_strs)

#------------------------------------------------------------------------------
class MelAttacks(MelSorted):
    """Handles the ATKD/ATKE subrecords shared between NPC_ and RACE."""
    _atk_flags = Flags(0, Flags.getNames(u'ignoreWeapon', u'bashAttack',
                                         u'powerAttack', u'leftAttack',
                                         u'rotatingAttack'))

    def __init__(self):
        super(MelAttacks, self).__init__(MelGroups(u'attacks',
             MelStruct(b'ATKD', [u'2f', u'2I', u'3f', u'I', u'3f'], u'attack_mult', u'attack_chance',
                       (FID, u'attack_spell'),
                       (self._atk_flags, u'attack_data_flags'),
                       u'attack_angle', u'strike_angle', u'attack_stagger',
                       (FID, u'attack_type'), u'attack_knockdown',
                       u'recovery_time', u'stamina_mult'),
             MelString(b'ATKE', u'attack_event'),
        ), sort_by_attrs='attack_chance')

#------------------------------------------------------------------------------
class MelCoed(MelOptStruct):
    """Needs custom unpacker to look at FormID type of owner.  If owner is an
    NPC then it is followed by a FormID.  If owner is a faction then it is
    followed by an signed integer or '=Iif' instead of '=IIf' """ # see #282
    def __init__(self):
        MelOptStruct.__init__(self,b'COED', [u'I', u'I', u'f'],(FID,'owner'),(FID,'glob'),
                              'itemCondition')

#------------------------------------------------------------------------------
class MelConditions(MelGroups):
    """A list of conditions. See also MelConditionCounter, which is commonly
    combined with this class."""
    def __init__(self, conditions_attr=u'conditions'):
        super(MelConditions, self).__init__(conditions_attr,
            MelGroups(u'condition_list',
                MelCtdaFo3(suffix_fmt=[u'2I', u'i'],
                    suffix_elements=[u'runOn', (FID, u'reference'), u'param3'],
                    old_suffix_fmts={u'2I', u'I', u''}),
            ),
            MelString(b'CIS1', u'param_cis1'),
            MelString(b'CIS2', u'param_cis2'),
        )

class MelConditionCounter(MelCounter):
    """Wraps MelCounter for the common task of defining a counter that counts
    MelConditions."""
    def __init__(self):
        MelCounter.__init__(
            self, MelUInt32(b'CITC', 'conditionCount'), counts='conditions')

#------------------------------------------------------------------------------
class MelDestructible(MelGroup):
    """Represents a set of destruct record."""

    MelDestStageFlags = Flags(0, Flags.getNames(
        (0, 'capDamage'),
        (1, 'disable'),
        (2, 'destroy'),
        (3, 'ignoreExternalDmg'),
        ))

    def __init__(self,attr='destructible'):
        MelGroup.__init__(self,attr,
            MelStruct(b'DEST', [u'i', u'2B', u'2s'],'health','count','vatsTargetable','dest_unused'),
            MelGroups('stages',
                MelStruct(b'DSTD', [u'4B', u'i', u'2I', u'i'], u'health', u'index',
                          u'damageStage',
                          (MelDestructible.MelDestStageFlags, u'flagsDest'),
                          u'selfDamagePerSecond', (FID, u'explosion'),
                          (FID, u'debris'), u'debrisCount'),
                MelModel(u'model', b'DMDL'),
                MelBase(b'DSTF','footer'),
            ),
        )

#------------------------------------------------------------------------------
class MelEffects(MelGroups):
    """Represents ingredient/potion/enchantment/spell effects."""
    def __init__(self):
        MelGroups.__init__(self, u'effects',
            MelFid(b'EFID', u'effect_formid'), # baseEffect
            MelStruct(b'EFIT', [u'f', u'2I'], u'magnitude', u'area', u'duration'),
            MelConditions(),
        )

#------------------------------------------------------------------------------
class MelEquipmentType(MelFid):
    """Handles the common ETYP subrecord."""
    def __init__(self):
        super(MelEquipmentType, self).__init__(b'ETYP', u'equipment_type')

#------------------------------------------------------------------------------
class MelIdleHandler(MelGroup):
    """Occurs three times in PACK, so moved here to deduplicate the
    definition a bit."""
    # The subrecord type used for the marker
    _attr_lookup = {
        u'on_begin': b'POBA',
        u'on_change': b'POCA',
        u'on_end': b'POEA',
    }

    def __init__(self, attr):
        super(MelIdleHandler, self).__init__(attr,
            MelBase(self._attr_lookup[attr], attr + u'_marker'),
            MelFid(b'INAM', u'idle_anim'),
            # The next four are leftovers from earlier CK versions
            MelBase(b'SCHR', u'unused1'),
            MelBase(b'SCTX', u'unused2'),
            MelBase(b'QNAM', u'unused3'),
            MelBase(b'TNAM', u'unused4'),
            MelTopicData(u'idle_topic_data'),
        )

#------------------------------------------------------------------------------
class MelItems(MelSorted):
    """Wraps MelGroups for the common task of defining a list of items."""
    def __init__(self):
        super(MelItems, self).__init__(MelGroups('items',
            MelStruct(b'CNTO', [u'I', u'i'], (FID, u'item'), u'count'),
            MelCoed(),
        ), sort_by_attrs=('item', 'count', 'itemCondition', 'owner', 'glob'))

class MelItemsCounter(MelCounter):
    """Wraps MelCounter for the common task of defining an items counter."""
    def __init__(self):
        super(MelItemsCounter, self).__init__(MelUInt32(b'COCT', 'item_count'),
                                              counts='items')

#------------------------------------------------------------------------------
class MelKeywords(MelSequential):
    """Wraps MelSequential for the common task of defining a list of keywords
    and a corresponding counter."""
    def __init__(self):
        MelSequential.__init__(self,
            MelCounter(MelUInt32(b'KSIZ', u'keyword_count'),
                       counts=u'keywords'),
            MelSorted(MelFidList(b'KWDA', u'keywords')),
        )

#------------------------------------------------------------------------------
class MelLinkedReferences(MelSorted):
    """The Linked References for a reference record (REFR, ACHR, etc.)."""
    def __init__(self):
        super(MelLinkedReferences, self).__init__(
            MelGroups(u'linked_references',
                MelStruct(b'XLKR', [u'2I'], (FID, u'keyword_ref'),
                          (FID, u'linked_ref')),
            ), sort_by_attrs='keyword_ref')

#------------------------------------------------------------------------------
class MelLocation(MelUnion):
    """A PLDT/PLVD (Location) subrecord. Occurs in PACK and FACT."""
    def __init__(self, sub_sig):
        super(MelLocation, self).__init__({
            (0, 1, 4, 6): MelOptStruct(sub_sig, [u'i', u'I', u'i'], u'location_type',
                (FID, u'location_value'), u'location_radius'),
            (2, 3, 7, 10, 11, 12): MelOptStruct(sub_sig, [u'i', u'4s', u'i'],
                u'location_type', u'location_value', u'location_radius'),
            5: MelOptStruct(sub_sig, [u'i', u'I', u'i'], u'location_type',
                u'location_value', u'location_radius'),
            (8, 9): MelOptStruct(sub_sig, [u'3i'], u'location_type',
                u'location_value', u'location_radius'),
            }, decider=PartialLoadDecider(
                loader=MelSInt32(sub_sig, u'location_type'),
                decider=AttrValDecider(u'location_type'))
        )

#------------------------------------------------------------------------------
class MelSMFlags(MelStruct):
    """Handles Story Manager flags shared by SMBN, SMQN and SMEN."""
    _node_flags = Flags(0, Flags.getNames(u'sm_random', u'no_child_warn'))
    _quest_flags = Flags(0, Flags.getNames(
        u'do_all_before_repeating',
        u'shares_event',
        u'num_quests_to_run'
    ))

    def __init__(self, with_quest_flags=False):
        sm_fmt = [u'I']
        sm_elements = [(self._node_flags, u'node_flags')]
        if with_quest_flags:
            sm_fmt = [u'2H']
            sm_elements.append((self._quest_flags, u'quest_flags'))
        super(MelSMFlags, self).__init__(b'DNAM', sm_fmt, *sm_elements)

#------------------------------------------------------------------------------
class MelSpellCounter(MelCounter):
    """Handles the SPCT (Spell Counter) subrecord. To be used in combination
    with MelSpells."""
    def __init__(self):
        super(MelSpellCounter, self).__init__(
            MelUInt32(b'SPCT', u'spell_count'), counts=u'spells')

#------------------------------------------------------------------------------
class MelSpit(MelStruct):
    """Handles the SPIT subrecord shared between SCRL and SPEL."""
    spit_flags = Flags(0, Flags.getNames(
        (0,  u'manualCostCalc'),
        (17, u'pcStartSpell'),
        (19, u'areaEffectIgnoresLOS'),
        (20, u'ignoreResistance'),
        (21, u'noAbsorbReflect'),
        (23, u'noDualCastModification'),
    ))

    def __init__(self):
        super(MelSpit, self).__init__(b'SPIT',
            [u'3I', u'f', u'2I', u'2f', u'I'], u'cost',
            (MelSpit.spit_flags, u'dataFlags'), u'spellType', u'chargeTime',
            u'castType', u'targetType', u'castDuration', u'range',
            (FID, u'halfCostPerk'))

#------------------------------------------------------------------------------
class MelTopicData(MelGroups):
    """Occurs twice in PACK, so moved here to deduplicate the definition a
    bit. Can't be placed inside MrePack, since one of its own subclasses
    depends on this."""
    def __init__(self, attr):
        MelGroups.__init__(self, attr,
            MelUnion({
                0: MelStruct(b'PDTO', [u'2I'], u'data_type',
                    (FID, u'topic_ref')),
                1: MelStruct(b'PDTO', [u'I', u'4s'], u'data_type', u'topic_subtype'),
            }, decider=PartialLoadDecider(
                loader=MelUInt32(b'PDTO', u'data_type'),
                decider=AttrValDecider(u'data_type'))),
        )

#------------------------------------------------------------------------------
class MelWaterVelocities(MelSequential):
    """Handles the XWCU/XWCS/XWCN subrecords shared by REFR and CELL."""
    def __init__(self):
        super(MelWaterVelocities, self).__init__(
            # Old version of XWCN - replace with XWCN upon dumping
            MelReadOnly(MelUInt32(b'XWCS', u'water_velocities_count')),
            MelCounter(MelUInt32(b'XWCN', u'water_velocities_count'),
                       counts=u'water_velocities'),
            MelArray(u'water_velocities',
                MelStruct(b'XWCU', [u'4f'], u'x_offset', u'y_offset',
                    u'z_offset', u'unknown1'),
            ),
        )

#------------------------------------------------------------------------------
# VMAD - Virtual Machine Adapters
def _dump_str16(str_val, __packer=structs_cache[u'H'].pack):
    """Encodes the specified string using the plugin encoding and returns data
    for both its length (as a 16-bit integer) and its encoded value."""
    encoded_str = bolt.encode(str_val, firstEncoding=bolt.pluginEncoding)
    return __packer(len(encoded_str)) + encoded_str

def _dump_vmad_str16(str_val, __packer=structs_cache[u'H'].pack):
    """Encodes the specified string using UTF-8 and returns data for both its
    length (as a 16-bit integer) and its encoded value."""
    encoded_str = str_val.encode(u'utf8')
    return __packer(len(encoded_str)) + encoded_str

def _read_str16(ins):
    """Reads a 16-bit length integer, then reads a string in that length."""
    return bolt.decoder(unpack_str16(ins))

def _read_vmad_str16(ins):
    """Reads a 16-bit length integer, then reads a string in that length.
    Always uses UTF-8 to decode."""
    return unpack_str16(ins).decode(u'utf8')

class _AVmadComponent(object):
    """Abstract base class for VMAD components. Specify a 'processors'
    class variable to use. Syntax: OrderedDict, mapping an attribute name
    for the record to a tuple containing an unpacker, a packer and a size.
    'str16' is a special value that instead calls _read_str16/_dump_str16 to
    handle the matching attribute.

    You can override any of the methods specified below to do other things
    after or before 'processors' has been evaluated, just be sure to call
    super(...).{dump,load}_data(...) when appropriate.

    :type processors: OrderedDict[str, tuple[callable, callable, int] | str]"""
    processors = OrderedDict()

    def dump_frag(self, record):
        """Dumps data for this fragment using the specified record and
        returns the result as a string, ready for writing to an output
        stream."""
        out_data = b''
        for attr, fmt in self.__class__.processors.items():
            attr_val = getattr(record, attr)
            if fmt != u'str16':
                out_data += fmt[1](attr_val)
            else:
                out_data += _dump_str16(attr_val)
        return out_data

    def load_frag(self, record, ins, vmad_version, obj_format, *debug_strs):
        """Loads data for this fragment from the specified input stream and
        attaches it to the specified record. The version of VMAD and the object
        format are also given."""
        for attr, fmt in self.__class__.processors.items():
            if fmt != u'str16':
                setattr(record, attr, ins.unpack(fmt[0], fmt[2],
                                                 *debug_strs)[0])
            else:
                setattr(record, attr, _read_str16(ins))

    def make_new(self):
        """Creates a new runtime instance of this component with the
        appropriate __slots__ set."""
        try:
            return self._component_class()
        except AttributeError:
            # TODO(inf) This seems to work - what we're currently doing in
            #  records code, namely reassigning __slots__, does *nothing*:
            #  https://stackoverflow.com/questions/27907373/dynamically-change-slots-in-python-3
            #  Fix that by refactoring class creation like this for
            #  MelBase/MelSet etc.!
            class _MelComponentInstance(MelObject):
                __slots__ = self.used_slots
            self._component_class = _MelComponentInstance # create only once
            return self._component_class()

    # Note that there is no has_fids - components (e.g. properties) with fids
    # could dynamically get added at runtime, so we must always call map_fids
    # to make sure.
    def map_fids(self, record, map_function, save=False):
        """Maps fids for this component. Does nothing by default, you *must*
        override this if your component or some of its children can contain
        fids!"""
        pass

    @property
    def used_slots(self):
        """Returns a list containing the slots needed by this component. Note
        that this should not change at runtime, since the class created with it
        is cached - see make_new above."""
        return list(self.__class__.processors)

class _AFixedContainer(_AVmadComponent):
    """Abstract base class for components that contain a fixed number of other
    components. Which ones are present is determined by a flags field. You
    need to specify a processor that sets an attribute named, by default,
    fragment_flags to the right value (you can change the name using the class
    variable flags_attr). Additionally, you have to set flags_mapper to a
    bolt.Flags instance that can be used for decoding the flags and
    flags_to_children to an OrderedDict that maps flag names to child attribute
    names. The order of this dict is the order in which the children will be
    read and written. Finally, you need to set child_loader to an instance of
    the correct class for your class type. Note that you have to do this
    inside __init__, as it is an instance variable."""
    # Abstract - to be set by subclasses
    flags_attr = u'fragment_flags'
    flags_mapper = None
    flags_to_children = OrderedDict()
    child_loader = None

    def load_frag(self, record, ins, vmad_version, obj_format, *debug_strs):
        # Load the regular attributes first
        super(_AFixedContainer, self).load_frag(record, ins, vmad_version,
                                                obj_format, *debug_strs)
        # Then, process the flags and decode them
        child_flags = self.__class__.flags_mapper(
            getattr(record, self.__class__.flags_attr))
        setattr(record, self.__class__.flags_attr, child_flags)
        # Finally, inspect the flags and load the appropriate children. We must
        # always load and dump these in the exact order specified by the
        # subclass!
        new_child = self.child_loader.make_new
        load_child = self.child_loader.load_frag
        for flag_attr, child_attr in \
                self.__class__.flags_to_children.items():
            cont_child = None
            if getattr(child_flags, flag_attr):
                cont_child = new_child()
                load_child(cont_child, ins, vmad_version, obj_format,
                           *debug_strs)
            setattr(record, child_attr, cont_child)

    def dump_frag(self, record):
        # Update the flags first, then dump the regular attributes
        # Also use this chance to store the value of each present child
        children = []
        child_flags = getattr(record, self.__class__.flags_attr)
        store_child = children.append
        for flag_attr, child_attr in \
                self.__class__.flags_to_children.items():
            cont_child = getattr(record, child_attr)
            write_child = cont_child is not None
            # No need to store children we won't be writing out
            if write_child:
                store_child(cont_child)
            setattr(child_flags, flag_attr, write_child)
        out_data = super(_AFixedContainer, self).dump_frag(record)
        # Then, dump each child for which the flag is now set, in order
        dump_child = self.child_loader.dump_frag
        for cont_child in children:
            out_data += dump_child(cont_child)
        return out_data

    @property
    def used_slots(self):
        return list(self.__class__.flags_to_children.values()) + super(
            _AFixedContainer, self).used_slots

class _AVariableContainer(_AVmadComponent):
    """Abstract base class for components that contain a variable number of
    iother components, with the count stored in a preceding integer. You need
    to specify a processor that sets an attribute named, by default,
    fragment_count to the right value (you can change the name using the class
    variable counter_attr). Additionally, you have to set child_loader to an
    instance of the correct class for your child type. Note that you have
    to do this inside __init__, as it is an instance variable. The attribute
    name used for the list of children may also be customized via the class
    variable children_attr."""
    # Abstract - to be set by subclasses
    child_loader = None
    children_attr = u'fragments'
    counter_attr = u'fragment_count'

    def load_frag(self, record, ins, vmad_version, obj_format, *debug_strs):
        # Load the regular attributes first
        super(_AVariableContainer, self).load_frag(record, ins, vmad_version,
                                                   obj_format, *debug_strs)
        # Then, load each child
        children = []
        new_child = self.child_loader.make_new
        load_child = self.child_loader.load_frag
        append_child = children.append
        for x in range(getattr(record, self.__class__.counter_attr)):
            cont_child = new_child()
            load_child(cont_child, ins, vmad_version, obj_format, *debug_strs)
            append_child(cont_child)
        setattr(record, self.__class__.children_attr, children)

    def dump_frag(self, record):
        # Update the child count, then dump the
        children = getattr(record, self.__class__.children_attr)
        setattr(record, self.__class__.counter_attr, len(children))
        out_data = super(_AVariableContainer, self).dump_frag(record)
        # Then, dump each child
        dump_child = self.child_loader.dump_frag
        for cont_child in children:
            out_data += dump_child(cont_child)
        return out_data

    def map_fids(self, record, map_function, save=False):
        map_child = self.child_loader.map_fids
        for cont_child in getattr(record, self.__class__.children_attr):
            map_child(cont_child, map_function, save)

    @property
    def used_slots(self):
        return [self.__class__.children_attr] + super(
            _AVariableContainer, self).used_slots

class ObjectRef(object):
    """An object ref is a FormID and an AliasID. Using a class instead of
    namedtuple for two reasons: lower memory usage (due to __slots__) and
    easier usage/access in the patchers."""
    __slots__ = (u'aid', u'fid')

    def __init__(self, aid, fid):
        self.aid = aid # The AliasID
        self.fid = fid # The FormID

    def dump_out(self, __packer=structs_cache[u'HhI'].pack):
        """Returns the dumped version of this ObjectRef, ready for writing onto
        an output stream."""
        # Write only object format v2
        return __packer(0, self.aid, self.fid)

    def map_fids(self, map_function, save=False):
        """Maps the specified function onto this ObjectRef's fid. If save is
        True, the result is stored, otherwise it is discarded."""
        result = map_function(self.fid)
        if save: self.fid = result

    def __repr__(self):
        return u'ObjectRef<%s, %s>' % (self.aid, self.fid)

    # Static helper methods
    @classmethod
    def array_from_file(cls, ins, obj_format, *debug_strs):
        """Reads an array of ObjectRefs directly from the specified input
        stream. Needs the current object format and a read ID as well."""
        __unpacker=structs_cache[u'I'].unpack
        make_ref = cls.from_file
        return [make_ref(ins, obj_format, *debug_strs) for _x in
                range(ins.unpack(__unpacker, 4, *debug_strs)[0])]

    @staticmethod
    def dump_array(target_list, __packer=structs_cache[u'I'].pack):
        """Returns the dumped version of the specified list of ObjectRefs,
        ready for writing onto an output stream. This includes a leading 32-bit
        integer denoting the size."""
        out_data = __packer(len(target_list))
        for obj_ref in target_list: # type: ObjectRef
            out_data += obj_ref.dump_out()
        return out_data

    @classmethod
    def from_file(cls, ins, obj_format, *debug_strs):
        """Reads an ObjectRef directly from the specified input stream. Needs
        the current object format and a read ID as well."""
        __unpacker1=structs_cache[u'IhH'].unpack
        __unpacker2=structs_cache[u'HhI'].unpack
        if obj_format == 1: # object format v1 - fid, aid, unused
            fid, aid, _unused = ins.unpack(__unpacker1, 8, *debug_strs)
        else: # object format v2 - unused, aid, fid
            _unused, aid, fid = ins.unpack(__unpacker2, 8, *debug_strs)
        return cls(aid, fid)

# Implementation --------------------------------------------------------------
class MelVmad(MelBase):
    """Virtual Machine Adapter. Forms the bridge between the Papyrus scripting
    system and the record definitions. A very complex subrecord that requires
    careful loading and dumping. The following is split into several sections,
    detailing fragments, fragment headers, properties, scripts and aliases.

    Note that this code is somewhat heavily optimized for performance, so
    expect lots of inlines and other non-standard or ugly code.

    :type _handler_map: dict[bytes, type|_AVmadComponent]"""
    # Fragments ---------------------------------------------------------------
    class FragmentBasic(_AVmadComponent):
        """Implements the following fragments:

            - SCEN OnBegin/OnEnd fragments
            - PACK fragments
            - INFO fragments"""
        processors = OrderedDict([
            (u'unknown1',      get_structs(u'b')),
            (u'script_name',   u'str16'),
            (u'fragment_name', u'str16'),
        ])

    class FragmentPERK(_AVmadComponent):
        """Implements PERK fragments."""
        processors = OrderedDict([
            (u'fragment_index', get_structs(u'H')),
            (u'unknown1',       get_structs(u'h')),
            (u'unknown2',       get_structs(u'b')),
            (u'script_name',    u'str16'),
            (u'fragment_name',  u'str16'),
        ])

    class FragmentQUST(_AVmadComponent):
        """Implements QUST fragments."""
        processors = OrderedDict([
            (u'quest_stage',       get_structs(u'H')),
            (u'unknown1',          get_structs(u'h')),
            (u'quest_stage_index', get_structs(u'I')),
            (u'unknown2',          get_structs(u'b')),
            (u'script_name',       u'str16'),
            (u'fragment_name',     u'str16'),
        ])

    class FragmentSCENPhase(_AVmadComponent):
        """Implements SCEN phase fragments."""
        processors = OrderedDict([
            (u'fragment_flags', get_structs(u'B')),
            (u'phase_index',    get_structs(u'B')),
            (u'unknown1',       get_structs(u'h')),
            (u'unknown2',       get_structs(u'b')),
            (u'unknown3',       get_structs(u'b')),
            (u'script_name',    u'str16'),
            (u'fragment_name',  u'str16'),
        ])
        _scen_fragment_phase_flags = Flags(0, Flags.getNames(u'on_start',
            u'on_completion'))

        def load_frag(self, record, ins, vmad_version, obj_format,
                      *debug_strs):
            super(MelVmad.FragmentSCENPhase, self).load_frag(
                record, ins, vmad_version, obj_format, *debug_strs)
            # Turn the read byte into flags for easier runtime usage
            record.fragment_phase_flags = self._scen_fragment_phase_flags(
                record.fragment_phase_flags)

    # Fragment Headers --------------------------------------------------------
    class VmadHandlerINFO(_AFixedContainer):
        """Implements special VMAD handling for INFO records."""
        processors = OrderedDict([
            (u'extra_bind_data_version', get_structs(u'b')),
            (u'fragment_flags',          get_structs(u'B')), # Updated before writing
            (u'file_name',               u'str16'),
        ])
        flags_mapper = Flags(0, Flags.getNames(u'on_begin', u'on_end'))
        flags_to_children = OrderedDict([
            (u'on_begin', u'begin_frag'),
            (u'on_end',   u'end_frag'),
        ])

        def __init__(self):
            super(MelVmad.VmadHandlerINFO, self).__init__()
            self.child_loader = MelVmad.FragmentBasic()

    class VmadHandlerPACK(_AFixedContainer):
        """Implements special VMAD handling for PACK records."""
        processors = OrderedDict([
            (u'extra_bind_data_version', get_structs(u'b')),
            (u'fragment_flags',          get_structs(u'B')), # Updated before writing
            (u'file_name',               u'str16'),
        ])
        flags_mapper = Flags(0, Flags.getNames(u'on_begin', u'on_end',
            u'on_change'))
        flags_to_children = OrderedDict([
            (u'on_begin',  u'begin_frag'),
            (u'on_end',    u'end_frag'),
            (u'on_change', u'change_frag'),
        ])

        def __init__(self):
            super(MelVmad.VmadHandlerPACK, self).__init__()
            self.child_loader = MelVmad.FragmentBasic()

    class VmadHandlerPERK(_AVariableContainer):
        """Implements special VMAD handling for PERK records."""
        processors = OrderedDict([
            (u'extra_bind_data_version', get_structs(u'b')),
            (u'file_name',               u'str16'),
            (u'fragment_count',          get_structs(u'H')), # Updated before writing
        ])

        def __init__(self):
            super(MelVmad.VmadHandlerPERK, self).__init__()
            self.child_loader = MelVmad.FragmentPERK()

        def dump_frag(self, record):
            record.fragments.sort(key=vmad_fragments_key)
            return super(MelVmad.VmadHandlerPERK, self).dump_frag(record)

    class VmadHandlerQUST(_AVariableContainer):
        """Implements special VMAD handling for QUST records."""
        processors = OrderedDict([
            (u'extra_bind_data_version', get_structs(u'b')),
            (u'fragment_count',          get_structs(u'H')),
            (u'file_name',               u'str16'),
        ])

        def __init__(self):
            super(MelVmad.VmadHandlerQUST, self).__init__()
            self.child_loader = MelVmad.FragmentQUST()
            self._alias_loader = MelVmad.Alias()

        def load_frag(self, record, ins, vmad_version, obj_format,
                      *debug_strs):
            # Load the regular fragments first
            super(MelVmad.VmadHandlerQUST, self).load_frag(
                record, ins, vmad_version, obj_format, *debug_strs)
            # Then, load each alias
            record.qust_aliases = []
            new_alias = self._alias_loader.make_new
            load_alias = self._alias_loader.load_frag
            append_alias = record.qust_aliases.append
            __unpacker=structs_cache[u'H'].unpack
            for x in range(ins.unpack(__unpacker, 2, *debug_strs)[0]):
                alias = new_alias()
                load_alias(alias, ins, vmad_version, obj_format, *debug_strs)
                append_alias(alias)

        def dump_frag(self, record, __packer=structs_cache[u'H'].pack):
            # Dump the regular fragments first
            record.fragments.sort(key=vmad_qust_fragments_key)
            out_data = super(MelVmad.VmadHandlerQUST, self).dump_frag(record)
            # Then, dump each alias
            q_aliases = record.qust_aliases
            q_aliases.sort(key=vmad_qust_aliases_key)
            out_data += __packer(len(q_aliases))
            dump_alias = self._alias_loader.dump_frag
            for alias in q_aliases:
                out_data += dump_alias(alias)
            return out_data

        def map_fids(self, record, map_function, save=False):
            # No need to call parent, QUST fragments can't contain fids
            map_alias = self._alias_loader.map_fids
            for alias in record.qust_aliases:
                map_alias(alias, map_function, save)

        @property
        def used_slots(self):
            return [u'qust_aliases'] + super(
                MelVmad.VmadHandlerQUST, self).used_slots

    ##: Identical to VmadHandlerINFO + some overrides
    class VmadHandlerSCEN(_AFixedContainer):
        """Implements special VMAD handling for SCEN records."""
        processors = OrderedDict([
            (u'extra_bind_data_version', get_structs(u'b')),
            (u'fragment_flags',          get_structs(u'B')), # Updated before writing
            (u'file_name',               u'str16'),
        ])
        flags_mapper = Flags(0, Flags.getNames(u'on_begin', u'on_end'))
        flags_to_children = OrderedDict([
            (u'on_begin', u'begin_frag'),
            (u'on_end',   u'end_frag'),
        ])

        def __init__(self):
            super(MelVmad.VmadHandlerSCEN, self).__init__()
            self.child_loader = MelVmad.FragmentBasic()
            self._phase_loader = MelVmad.FragmentSCENPhase()

        def load_frag(self, record, ins, vmad_version, obj_format,
                      *debug_strs):
            __unpacker=structs_cache[u'H'].unpack
            # First, load the regular attributes and fragments
            super(MelVmad.VmadHandlerSCEN, self).load_frag(
                record, ins, vmad_version, obj_format, *debug_strs)
            # Then, load each phase fragment
            record.phase_fragments = []
            frag_count = ins.unpack(__unpacker, 2, *debug_strs)[0]
            new_fragment = self._phase_loader.make_new
            load_fragment = self._phase_loader.load_frag
            append_fragment = record.phase_fragments.append
            for x in range(frag_count):
                phase_fragment = new_fragment()
                load_fragment(phase_fragment, ins, vmad_version, obj_format,
                              *debug_strs)
                append_fragment(phase_fragment)

        def dump_frag(self, record, __packer=structs_cache[u'H'].pack):
            # First, dump the regular attributes and fragments
            out_data = super(MelVmad.VmadHandlerSCEN, self).dump_frag(record)
            # Then, dump each phase fragment
            phase_frags = record.phase_fragments
            out_data += __packer(len(phase_frags))
            dump_fragment = self._phase_loader.dump_frag
            for phase_fragment in phase_frags:
                out_data += dump_fragment(phase_fragment)
            return out_data

        @property
        def used_slots(self):
            return [u'phase_fragments'] + super(
                MelVmad.VmadHandlerSCEN, self).used_slots

    # Scripts -----------------------------------------------------------------
    class Script(_AVariableContainer):
        """Represents a single script."""
        children_attr = u'properties'
        counter_attr = u'property_count'
        processors = OrderedDict([
            (u'script_name',    u'str16'),
            (u'script_flags',   get_structs(u'B')),
            (u'property_count', get_structs(u'H')),
        ])
        # actually an enum, 0x0 means 'local'
        _script_status_flags = Flags(0, Flags.getNames(u'inherited',
            u'removed'))

        def __init__(self):
            super(MelVmad.Script, self).__init__()
            self.child_loader = MelVmad.Property()

        def load_frag(self, record, ins, vmad_version, obj_format,
                      *debug_strs):
            # Load the data, then process the flags
            super(MelVmad.Script, self).load_frag(record, ins, vmad_version,
                                                  obj_format, *debug_strs)
            record.script_flags = self._script_status_flags(
                record.script_flags)

        def dump_frag(self, record):
            record.properties.sort(key=vmad_properties_key)
            return super(MelVmad.Script, self).dump_frag(record)

    # Properties --------------------------------------------------------------
    class Property(_AVmadComponent):
        """Represents a single script property."""
        # Processors for VMAD >= v4
        _new_processors = OrderedDict([
            (u'prop_name',  u'str16'),
            (u'prop_type',  get_structs(u'B')),
            (u'prop_flags', get_structs(u'B')),
        ])
        # Processors for VMAD <= v3
        _old_processors = OrderedDict([
            (u'prop_name', u'str16'),
            (u'prop_type', get_structs(u'B')),
        ])
        _property_status_flags = Flags(0, Flags.getNames(u'edited',
            u'removed'))

        def load_frag(self, record, ins, vmad_version, obj_format,
                      *debug_strs):
            __unpackers={k: structs_cache[k].unpack for k in
                         (u'i', u'f', u'B', u'I',)}
            # Load the three regular attributes first - need to check version
            if vmad_version >= 4:
                MelVmad.Property.processors = MelVmad.Property._new_processors
            else:
                MelVmad.Property.processors = MelVmad.Property._old_processors
                record.prop_flags = 1
            super(MelVmad.Property, self).load_frag(record, ins, vmad_version,
                                                    obj_format, *debug_strs)
            record.prop_flags = self._property_status_flags(
                record.prop_flags)
            # Then, read the data in the format corresponding to the
            # property_type we just read - warning, some of these look *very*
            # unusual; these are the fastest implementations, at least on py2.
            # In particular, '!= 0' is faster than 'bool()', '[x for x in a]'
            # is slightly faster than 'list(a)' and "repr(c) + 'f'" is faster
            # than "'%uf' % c" or "unicode(c) + 'f'". # PY3: revisit
            property_type = record.prop_type
            if property_type == 0: # null
                record.prop_data = None
            elif property_type == 1: # object
                record.prop_data = ObjectRef.from_file(
                    ins, obj_format, *debug_strs)
            elif property_type == 2: # string
                record.prop_data = _read_vmad_str16(ins)
            elif property_type == 3: # sint32
                record.prop_data = ins.unpack(__unpackers[u'i'], 4,
                                              *debug_strs)[0]
            elif property_type == 4: # float
                record.prop_data = ins.unpack(__unpackers[u'f'], 4,
                                              *debug_strs)[0]
            elif property_type == 5: # bool (stored as uint8)
                # Faster than bool() and other, similar checks
                record.prop_data = ins.unpack(
                    __unpackers[u'B'], 1, *debug_strs) != (0,)
            elif property_type == 11: # object array
                record.prop_data = ObjectRef.array_from_file(ins, obj_format,
                                                             *debug_strs)
            elif property_type == 12: # string array
                record.prop_data = [_read_vmad_str16(ins) for _x in
                                    range(ins.unpack(
                                        __unpackers[u'I'], 4, *debug_strs)[0])]
            elif property_type == 13: # sint32 array
                array_len = ins.unpack(__unpackers[u'I'], 4, *debug_strs)[0]
                # Do *not* change without extensive benchmarking! This is
                # faster than all alternatives, at least on py2.
                record.prop_data = [x for x in ins.unpack(
                    structs_cache[u'%di' % array_len].unpack, array_len * 4,
                    *debug_strs)]
            elif property_type == 14: # float array
                array_len = ins.unpack(__unpackers[u'I'], 4, *debug_strs)[0]
                # Do *not* change without extensive benchmarking! This is
                # faster than all alternatives, at least on py2.
                record.prop_data = [x for x in ins.unpack(
                    structs_cache[u'%df' % array_len].unpack, array_len * 4,
                    *debug_strs)]
            elif property_type == 15: # bool array (stored as uint8 array)
                array_len = ins.unpack(__unpackers[u'I'], 4, *debug_strs)[0]
                # Do *not* change without extensive benchmarking! This is
                # faster than all alternatives, at least on py2.
                record.prop_data = [x != 0 for x in ins.unpack(
                    structs_cache[u'%dB' % array_len].unpack, array_len,
                    *debug_strs)]
            else:
                raise ModError(ins.inName, u'Unrecognized VMAD property type: '
                                           u'%u' % property_type)

        def dump_frag(self, record, __packers={
            k: structs_cache[k].pack for k in (u'i', u'f', u'B', u'I')}):
            # Dump the three regular attributes first - note that we only write
            # out VMAD with version of 5 and object format 2, so make sure we
            # use new_processors here
            MelVmad.Property.processors = MelVmad.Property._new_processors
            out_data = super(MelVmad.Property, self).dump_frag(record)
            # Then, dump out the data corresponding to the property type
            # See load_frag for warnings and explanations about the code style
            property_data = record.prop_data
            property_type = record.prop_type
            if property_type == 0: # null
                return out_data
            elif property_type == 1: # object
                return out_data + property_data.dump_out()
            elif property_type == 2: # string
                return out_data + _dump_vmad_str16(property_data)
            elif property_type == 3: # sint32
                return out_data + __packers[u'i'](property_data)
            elif property_type == 4: # float
                return out_data + __packers[u'f'](property_data)
            elif property_type == 5: # bool (stored as uint8)
                # Faster than int(record.prop_data)
                return out_data + __packers[u'B'](1 if property_data else 0)
            elif property_type == 11: # object array
                return out_data + ObjectRef.dump_array(property_data)
            elif property_type == 12: # string array
                out_data += __packers[u'I'](len(property_data))
                return out_data + b''.join(_dump_vmad_str16(x) for x in
                                           property_data)
            elif property_type == 13: # sint32 array
                array_len = len(property_data)
                out_data += __packers[u'I'](array_len)
                return out_data + struct_pack(f'={array_len}i', *property_data)
            elif property_type == 14: # float array
                array_len = len(property_data)
                out_data += __packers[u'I'](array_len)
                return out_data + struct_pack(f'={array_len}f', *property_data)
            elif property_type == 15: # bool array (stored as uint8 array)
                array_len = len(property_data)
                out_data += __packers[u'I'](array_len)
                # Faster than [int(x) for x in property_data]
                return out_data + struct_pack(f'={array_len}B',
                                              *[x != 0 for x in property_data])
            else:
                # TODO(inf) Dumped file name! Please!
                raise ModError(u'', u'Unrecognized VMAD property type: %u' %
                               property_type)

        def map_fids(self, record, map_function, save=False):
            property_type = record.prop_type
            if property_type == 1: # object
                record.prop_data.map_fids(map_function, save)
            elif property_type == 11: # object array
                for obj_ref in record.prop_data:
                    obj_ref.map_fids(map_function, save)

        @property
        def used_slots(self):
            # Manually implemented to avoid depending on self.processors, which
            # may be either _new_processors or _old_processors right now
            return [u'prop_name', u'prop_type', u'prop_flags', u'prop_data']

    # Aliases -----------------------------------------------------------------
    class Alias(_AVariableContainer):
        """Represents a single alias."""
        # Can't use any processors when loading - see below
        _load_processors = OrderedDict()
        _dump_processors = OrderedDict([
            (u'alias_vmad_version', get_structs(u'h')),
            (u'alias_obj_format',   get_structs(u'h')),
            (u'script_count',       get_structs(u'H')),
        ])
        children_attr = u'scripts'
        counter_attr = u'script_count'

        def __init__(self):
            super(MelVmad.Alias, self).__init__()
            self.child_loader = MelVmad.Script()

        def load_frag(self, record, ins, vmad_version, obj_format,
                      *debug_strs):
            __unpacker_H=structs_cache[u'H'].unpack
            __unpacker_h=structs_cache[u'h'].unpack
            MelVmad.Alias.processors = MelVmad.Alias._load_processors
            # Aliases start with an ObjectRef, skip that for now and unpack
            # the three regular attributes. We need to do this, since one of
            # the attributes is alias_obj_format, which tells us how to unpack
            # the ObjectRef at the start.
            ins.seek(8, 1, *debug_strs)
            record.alias_vmad_version = ins.unpack(__unpacker_h, 2,
                                                   *debug_strs)[0]
            record.alias_obj_format = ins.unpack(__unpacker_h, 2,
                                                 *debug_strs)[0]
            record.script_count = ins.unpack(__unpacker_H, 2, *debug_strs)[0]
            # Change our active VMAD version and object format to the ones we
            # read from this alias
            vmad_version = record.alias_vmad_version
            obj_format = record.alias_obj_format
            # Now we can go back and unpack the ObjectRef - note us passing the
            # (potentially) modified object format
            ins.seek(-14, 1, *debug_strs)
            record.alias_ref_obj = ObjectRef.from_file(ins, obj_format,
                                                       *debug_strs)
            # Skip back over the three attributes we read at the start
            ins.seek(6, 1, *debug_strs)
            # Finally, load the scripts attached to this alias - again, note
            # the (potentially) changed VMAD version and object format
            super(MelVmad.Alias, self).load_frag(record, ins, vmad_version,
                                                 obj_format, *debug_strs)

        def dump_frag(self, record):
            MelVmad.Alias.processors = MelVmad.Alias._dump_processors
            # Dump out the ObjectRef first and make sure we dump out VMAD v5
            # and object format v2, then we can fall back on our parent's
            # dump_frag implementation
            out_data = record.alias_ref_obj.dump_out()
            record.alias_vmad_version = 5
            record.alias_obj_format = 2
            record.scripts.sort(key=vmad_script_key)
            return out_data + super(MelVmad.Alias, self).dump_frag(record)

        def map_fids(self, record, map_function, save=False):
            record.alias_ref_obj.map_fids(map_function, save)
            super(MelVmad.Alias, self).map_fids(record, map_function, save)

        @property
        def used_slots(self):
            # Manually implemented to avoid depending on self.processors, which
            # may be either _load_processors or _dump_processors right now
            return [u'alias_ref_obj', u'alias_vmad_version',
                    u'alias_obj_format', u'script_count', u'scripts']

    # Subrecord Implementation ------------------------------------------------
    _handler_map = {
        b'INFO': VmadHandlerINFO,
        b'PACK': VmadHandlerPACK,
        b'PERK': VmadHandlerPERK,
        b'QUST': VmadHandlerQUST,
        b'SCEN': VmadHandlerSCEN,
    }

    def __init__(self):
        MelBase.__init__(self, b'VMAD', u'vmdata')
        self._script_loader = self.Script()
        self._vmad_class = None

    def _get_special_handler(self, record_sig):
        """Internal helper method for instantiating / retrieving a VMAD handler
        instance.

        :param record_sig: The signature of the record type in question.
        :type record_sig: bytes
        :rtype: _AVmadComponent"""
        special_handler = self._handler_map[record_sig]
        if isinstance(special_handler, type):
            # These initializations need to be delayed, since they require
            # MelVmad to be fully initialized first, so do this JIT
            self._handler_map[record_sig] = special_handler = special_handler()
        return special_handler

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        __unpacker=structs_cache[u'=hhH'].unpack
        # Remember where this VMAD subrecord ends
        end_of_vmad = ins.tell() + size_
        if self._vmad_class is None:
            class _MelVmadImpl(MelObject):
                __slots__ = (u'scripts', u'special_data')
            self._vmad_class = _MelVmadImpl # create only once
        record.vmdata = vmad = self._vmad_class()
        # Begin by unpacking the VMAD header and doing some error checking
        vmad_version, obj_format, script_count = ins.unpack(__unpacker, 6,
                                                            *debug_strs)
        if vmad_version < 1 or vmad_version > 5:
            raise ModError(ins.inName, u'Unrecognized VMAD version: %u' %
                           vmad_version)
        if obj_format not in (1, 2):
            raise ModError(ins.inName, u'Unrecognized VMAD object format: %u' %
                           obj_format)
        # Next, load any scripts that may be present
        vmad.scripts = []
        new_script = self._script_loader.make_new
        load_script = self._script_loader.load_frag
        append_script = vmad.scripts.append
        for i in range(script_count):
            script_ = new_script()
            load_script(script_, ins, vmad_version, obj_format, *debug_strs)
            append_script(script_)
        # If the record type is one of the ones that need special handling and
        # we still have something to read, call the appropriate handler
        if record._rec_sig in self._handler_map and ins.tell() < end_of_vmad:
            special_handler = self._get_special_handler(record._rec_sig)
            vmad.special_data = special_handler.make_new()
            special_handler.load_frag(vmad.special_data, ins, vmad_version,
                                      obj_format, *debug_strs)
        else:
            vmad.special_data = None

    def pack_subrecord_data(self, record, __packer1=structs_cache[u'2h'].pack,
                            __packer2=structs_cache[u'H'].pack):
        vmad = getattr(record, self.attr)
        if vmad is None: return None
        # Start by dumping out the VMAD header - we read all VMAD versions and
        # object formats, but only dump out VMAD v5 and object format v2
        out_data = __packer1(5, 2)
        # Next, dump out all attached scripts
        vm_scripts = vmad.scripts
        vm_scripts.sort(key=vmad_script_key)
        out_data += __packer2(len(vm_scripts))
        dump_script = self._script_loader.dump_frag
        for vmad_script in vm_scripts:
            out_data += dump_script(vmad_script)
        # If the subrecord has special data attached, ask the appropriate
        # handler to dump that out
        if vmad.special_data and record._rec_sig in self._handler_map:
            out_data += self._get_special_handler(record._rec_sig).dump_frag(
                vmad.special_data)
        # Finally, write out the subrecord header, followed by the dumped data
        return out_data

    def hasFids(self, formElements):
        # Unconditionally add ourselves - see comment above
        # _AVmadComponent.map_fids for more information
        formElements.add(self)

    def mapFids(self, record, function, save=False):
        vmad = getattr(record, self.attr)
        if vmad is None: return
        map_script = self._script_loader.map_fids
        for vmad_script in vmad.scripts:
            map_script(vmad_script, function, save)
        if vmad.special_data and record._rec_sig in self._handler_map:
            self._get_special_handler(record._rec_sig).map_fids(
                vmad.special_data, function, save)

#------------------------------------------------------------------------------
# Skyrim Records --------------------------------------------------------------
#------------------------------------------------------------------------------
class MreTes4(MreHeaderBase):
    """TES4 Record.  File header."""
    rec_sig = b'TES4'

    melSet = MelSet(
        MelStruct(b'HEDR', [u'f', u'2I'], ('version', 1.7), 'numRecords',
                  ('nextObject', 0x800)),
        MreHeaderBase.MelAuthor(),
        MreHeaderBase.MelDescription(),
        MreHeaderBase.MelMasterNames(),
        MelFidList(b'ONAM','overrides',),
        MelBase(b'SCRN', 'screenshot'),
        MelBase(b'INTV', 'unknownINTV'),
        MelBase(b'INCC', 'unknownINCC'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAact(MelRecord):
    """Action."""
    rec_sig = b'AACT'
    melSet = MelSet(
        MelEdid(),
        MelColorO(b'CNAM'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAchr(MelRecord):
    """Placed NPC."""
    rec_sig = b'ACHR'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelFid(b'NAME', u'ref_base'),
        MelFid(b'XEZN', u'encounter_zone'),
        MelBase(b'XRGD', u'ragdoll_data'),
        MelBase(b'XRGB', u'ragdoll_biped_data'),
        MelFloat(b'XPRD', u'idle_time'),
        MelBase(b'XPPA', u'patrol_script_marker'),
        MelFid(b'INAM', u'ref_idle'),
        MelBase(b'SCHR', u'unused_schr'),
        MelBase(b'SCDA', u'unused_scda'),
        MelBase(b'SCTX', u'unused_sctx'),
        MelBase(b'QNAM', u'unused_qnam'),
        MelBase(b'SCRO', u'unused_scro'),
        MelTopicData(u'topic_data'),
        MelFid(b'TNAM', u'ref_topic'),
        MelSInt32(b'XLCM', u'level_modifier'),
        MelFid(b'XMRC', u'merchant_container'),
        MelSInt32(b'XCNT', u'ref_count'),
        MelFloat(b'XRDS', u'ref_radius'),
        MelFloat(b'XHLP', u'ref_health'),
        MelLinkedReferences(),
        MelActivateParents(),
        MelStruct(b'XCLP', [u'3B', u's', u'3B', u's'], u'start_color_red', u'start_color_green',
                  u'start_color_blue', u'start_color_unused', u'end_color_red',
                  u'end_color_green', u'end_color_blue', u'end_color_unused'),
        MelFid(b'XLCN', u'persistent_location'),
        MelFid(b'XLRL', u'location_reference'),
        MelBase(b'XIS2', u'ignored_by_sandbox_2'),
        MelArray(u'location_ref_type',
            MelFid(b'XLRT', u'location_ref')
        ),
        MelFid(b'XHOR', u'ref_horse'),
        MelFloat(b'XHTW', u'head_tracking_weight'),
        MelFloat(b'XFVC', u'favor_cost'),
        MelEnableParent(),
        MelOwnership(),
        MelFid(b'XEMI', u'ref_emittance'),
        MelFid(b'XMBR', u'multi_bound_reference'),
        MelBase(b'XIBS', u'ignored_by_sandbox_1'),
        MelRefScale(),
        MelRef3D(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreActi(MelRecord):
    """Activator."""
    rec_sig = b'ACTI'

    ActivatorFlags = Flags(0, Flags.getNames(
        (0, 'noDisplacement'),
        (1, 'ignoredBySandbox'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelColor(b'PNAM'),
        MelFid(b'SNAM', u'soundLooping'),
        MelFid(b'VNAM', u'soundActivation'),
        MelFid(b'WNAM', 'water'),
        MelLString(b'RNAM', 'activate_text_override'),
        MelUInt16Flags(b'FNAM', u'flags', ActivatorFlags),
        MelFid(b'KNAM', 'keyword'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAddn(MelRecord):
    """Addon Node."""
    rec_sig = b'ADDN'

    _AddnFlags = Flags(0, Flags.getNames(
        (1, 'alwaysLoaded'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelSInt32(b'DATA', 'node_index'),
        MelFid(b'SNAM', 'ambientSound'),
        MelStruct(b'DNAM', [u'2H'], 'master_particle_system_cap',
                  (_AddnFlags, 'addon_flags')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAlch(MelRecord):
    """Ingestible."""
    rec_sig = b'ALCH'

    IngestibleFlags = Flags(0, Flags.getNames(
        (0, 'noAutoCalc'),
        (1, 'isFood'),
        (16, 'medicine'),
        (17, 'poison'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelKeywords(),
        MelDescription(),
        MelModel(),
        MelDestructible(),
        MelIcons(),
        MelPickupSound(),
        MelDropSound(),
        MelEquipmentType(),
        MelFloat(b'DATA', 'weight'),
        MelStruct(b'ENIT', [u'i', u'2I', u'f', u'I'], u'value', (IngestibleFlags, u'flags'),
                  (FID, u'addiction'), u'addictionChance',
                  (FID, u'soundConsume')),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAmmo(MelRecord):
    """Ammunition."""
    rec_sig = b'AMMO'

    AmmoTypeFlags = Flags(0, Flags.getNames(
        (0, 'notNormalWeapon'),
        (1, 'nonPlayable'),
        (2, 'nonBolt'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelPickupSound(),
        MelDropSound(),
        MelDescription(),
        MelKeywords(),
        if_sse(
            le_version=MelStruct(b'DATA', [u'I', u'I', u'f', u'I'], (FID, 'projectile'),
                                 (AmmoTypeFlags, 'flags'), 'damage', 'value'),
            se_version=MelTruncatedStruct(b'DATA', [u'2I', u'f', u'I', u'f'],
                (FID, 'projectile'), (AmmoTypeFlags, 'flags'),
                'damage', 'value', 'weight', old_versions={'2IfI'}),
        ),
        MelString(b'ONAM', 'short_name'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAnio(MelRecord):
    """Animated Object."""
    rec_sig = b'ANIO'
    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelString(b'BNAM', 'unload_event'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAppa(MelRecord):
    """Alchemical Apparatus."""
    rec_sig = b'APPA'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelPickupSound(),
        MelDropSound(),
        MelUInt32(b'QUAL', 'quality'),
        MelDescription(),
        MelStruct(b'DATA', [u'I', u'f'],'value','weight'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArma(MelRecord):
    """Armor Addon."""
    rec_sig = b'ARMA'

    WeightSliderFlags = Flags(0, Flags.getNames(
            (0, 'unknown0'),
            (1, 'enabled'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelBipedObjectData(),
        MelFid(b'RNAM','race'),
        MelStruct(b'DNAM', [u'4B', u'2s', u'B', u's', u'f'],'malePriority','femalePriority',
                  (WeightSliderFlags, u'maleFlags'),
                  (WeightSliderFlags, u'femaleFlags'),
                  'unknown','detectionSoundValue','unknown1','weaponAdjust',),
        MelModel(u'male_model', b'MOD2'),
        MelModel(u'female_model', b'MOD3'),
        MelModel(u'male_model_1st', b'MOD4'),
        MelModel(u'female_model_1st', b'MOD5'),
        MelFid(b'NAM0', 'skin0'),
        MelFid(b'NAM1', 'skin1'),
        MelFid(b'NAM2', 'skin2'),
        MelFid(b'NAM3', 'skin3'),
        MelSorted(MelFids(b'MODL', 'additional_races')),
        MelFid(b'SNDD', 'footstepSound'),
        MelFid(b'ONAM', 'art_object'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArmo(MelRecord):
    """Armor."""
    rec_sig = b'ARMO'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelEnchantment(),
        MelSInt16(b'EAMT', 'enchantmentAmount'),
        MelModel(u'model2', b'MOD2'),
        MelIcons(u'maleIconPath', u'maleSmallIconPath'),
        MelModel(u'model4', b'MOD4'),
        MelIcons2(),
        MelBipedObjectData(),
        MelDestructible(),
        MelPickupSound(),
        MelDropSound(),
        MelString(b'BMCT', 'ragdollTemplatePath'), #Ragdoll Constraint Template
        MelEquipmentType(),
        MelFid(b'BIDS', 'bashImpact'),
        MelFid(b'BAMT', 'material'),
        MelFid(b'RNAM', 'race'),
        MelKeywords(),
        MelDescription(),
        MelFids(b'MODL','addons'),
        MelStruct(b'DATA', [u'i', u'f'],'value','weight'),
        MelSInt32(b'DNAM', 'armorRating'),
        MelFid(b'TNAM','templateArmor'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArto(MelRecord):
    """Art Effect Object."""
    rec_sig = b'ARTO'

    ArtoTypeFlags = Flags(0, Flags.getNames(
            (0, 'magic_casting'),
            (1, 'magic_hit_effect'),
            (2, 'enchantment_effect'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelUInt32Flags(b'DNAM', u'flags', ArtoTypeFlags),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAspc(MelRecord):
    """Acoustic Space."""
    rec_sig = b'ASPC'
    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFid(b'SNAM', 'ambientSound'),
        MelFid(b'RDAT', 'regionData'),
        MelFid(b'BNAM', 'reverb'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAstp(MelRecord):
    """Association Type."""
    rec_sig = b'ASTP'

    AstpTypeFlags = Flags(0, Flags.getNames('related'))

    melSet = MelSet(
        MelEdid(),
        MelString(b'MPRT','maleParent'),
        MelString(b'FPRT','femaleParent'),
        MelString(b'MCHT','maleChild'),
        MelString(b'FCHT','femaleChild'),
        MelUInt32Flags(b'DATA', u'flags', AstpTypeFlags),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAvif(MelRecord):
    """Actor Value Information."""
    rec_sig = b'AVIF'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelString(b'ANAM','abbreviation'),
        MelBase(b'CNAM','cnam_p'),
        MelOptStruct(b'AVSK', [u'4f'],'skillUseMult','skillOffsetMult','skillImproveMult',
                     'skillImproveOffset',),
        MelGroups('perkTree',
            MelFid(b'PNAM', 'perk',),
            MelBase(b'FNAM','fnam_p'),
            MelUInt32(b'XNAM', 'perkGridX'),
            MelUInt32(b'YNAM', 'perkGridY'),
            MelFloat(b'HNAM', 'horizontalPosition'),
            MelFloat(b'VNAM', 'verticalPosition'),
            MelFid(b'SNAM','associatedSkill',),
            MelGroups('connections',
                MelUInt32(b'CNAM', 'lineToIndex'),
            ),
            MelUInt32(b'INAM', 'index',),
        ),
    ).with_distributor({
        b'CNAM': u'cnam_p',
        b'PNAM': {
            b'CNAM': u'perkTree',
        },
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreBook(MelRecord):
    """Book."""
    rec_sig = b'BOOK'

    _book_type_flags = Flags(0, Flags.getNames(
        'teaches_skill',
        'cant_be_taken',
        'teaches_spell',
    ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDescription(u'book_text'),
        MelDestructible(),
        MelPickupSound(),
        MelDropSound(),
        MelKeywords(),
        MelUnion({
            False: MelStruct(b'DATA', [u'2B', u'2s', u'i', u'I', u'f'],
                (_book_type_flags, u'book_flags'), u'book_type',
                u'unused1', u'book_skill', u'value', u'weight'),
            True: MelStruct(b'DATA', [u'2B', u'2s', u'2I', u'f'],
                (_book_type_flags, u'book_flags'), u'book_type',
                u'unused1', (FID, u'book_spell'), u'value',
                u'weight'),
        }, decider=PartialLoadDecider(
            loader=MelUInt8Flags(b'DATA', u'book_flags', _book_type_flags),
            decider=FlagDecider(u'book_flags', [u'teaches_spell']),
        )),
        MelFid(b'INAM','inventoryArt'),
        MelLString(b'CNAM','description'),
    )
    __slots__ = melSet.getSlotsUsed() + ['modb']

#------------------------------------------------------------------------------
class MreBptd(MelRecord):
    """Body Part Data."""
    rec_sig = b'BPTD'

    _flags = Flags(0, Flags.getNames('severable','ikData','ikBipedData',
        'explodable','ikIsHead','ikHeadtracking','toHitChanceAbsolute'))

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelSorted(MelGroups('bodyParts',
            MelLString(b'BPTN', u'partName'),
            MelString(b'PNAM','poseMatching'),
            MelString(b'BPNN', 'nodeName'),
            MelString(b'BPNT','vatsTarget'),
            MelString(b'BPNI','ikDataStartNode'),
            MelStruct(b'BPND', [u'f', u'3B', u'b', u'2B', u'H', u'2I', u'2f', u'i', u'2I', u'7f', u'2I', u'2B', u'2s', u'f'],'damageMult',
                      (_flags,'flags'),'partType','healthPercent','actorValue',
                      'toHitChance','explodableChancePercent',
                      'explodableDebrisCount',(FID, u'explodableDebris'),
                      (FID, u'explodableExplosion'),'trackingMaxAngle',
                      'explodableDebrisScale','severableDebrisCount',
                      (FID, u'severableDebris'),(FID, u'severableExplosion'),
                      'severableDebrisScale','goreEffectPosTransX',
                      'goreEffectPosTransY','goreEffectPosTransZ',
                      'goreEffectPosRotX','goreEffectPosRotY','goreEffectPosRotZ',
                      (FID, u'severableImpactDataSet'),
                      (FID, u'explodableImpactDataSet'),'severableDecalCount',
                      'explodableDecalCount','unused',
                      'limbReplacementScale'),
            MelString(b'NAM1','limbReplacementModel'),
            MelString(b'NAM4','goreEffectsTargetBone'),
            # Ignore texture hashes - they're only an optimization, plenty of
            # records in Skyrim.esm are missing them
            MelNull(b'NAM5'),
        ), sort_by_attrs='nodeName'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCams(MelRecord):
    """Camera Shot."""
    rec_sig = b'CAMS'

    CamsFlagsFlags = Flags(0, Flags.getNames(
            (0, 'positionFollowsLocation'),
            (1, 'rotationFollowsTarget'),
            (2, 'dontFollowBone'),
            (3, 'firstPersonCamera'),
            (4, 'noTracer'),
            (5, 'startAtTimeZero'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelTruncatedStruct(b'DATA', [u'4I', u'7f'], 'action', 'location', 'target',
                           (CamsFlagsFlags, u'flags'), 'timeMultPlayer',
                           'timeMultTarget', 'timeMultGlobal', 'maxTime',
                           'minTime', 'targetPctBetweenActors',
                           'nearTargetDistance', old_versions={'4I6f'}),
        MelFid(b'MNAM','imageSpaceModifier',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCell(MelRecord):
    """Cell."""
    rec_sig = b'CELL'
    _has_duplicate_attrs = True # XWCS is an older version of XWCN

    CellDataFlags1 = Flags(0, Flags.getNames(
        (0,'isInterior'),
        (1,'hasWater'),
        (2,'cantFastTravel'),
        (3,'noLODWater'),
        (5,'publicPlace'),
        (6,'handChanged'),
        (7,'showSky'),
        ))

    CellDataFlags2 = Flags(0, Flags.getNames(
        (0,'useSkyLighting'),
        ))

    CellInheritedFlags = Flags(0, Flags.getNames(
            (0, 'ambientColor'),
            (1, 'directionalColor'),
            (2, 'fogColor'),
            (3, 'fogNear'),
            (4, 'fogFar'),
            (5, 'directionalRotation'),
            (6, 'directionalFade'),
            (7, 'clipDistance'),
            (8, 'fogPower'),
            (9, 'fogMax'),
            (10, 'lightFadeDistances'),
        ))

    _land_flags = Flags(0, Flags.getNames(u'quad1', u'quad2', u'quad3',
        u'quad4'), unknown_is_unused=True)

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelTruncatedStruct(b'DATA', [u'2B'], (CellDataFlags1, u'flags'),
                           (CellDataFlags2, u'skyFlags'),
                           old_versions={'B'}),
        ##: The other games skip this in interiors - why / why not here?
        # None defaults here are on purpose - XCLC does not necessarily exist,
        # but 0 is a valid value for both coordinates (duh)
        MelOptStruct(b'XCLC', [u'2i', u'I'], (u'posX', None), (u'posY', None),
            (_land_flags, u'land_flags')),
        MelTruncatedStruct(b'XCLL',
            [u'3B', u's', u'3B', u's', u'3B', u's', u'2f', u'2i', u'3f', u'3B',
             u's', u'3B', u's', u'3B', u's', u'3B', u's', u'3B', u's', u'3B',
             u's', u'3B', u's', u'f', u'3B', u's', u'3f', u'I'],
            'ambientRed', 'ambientGreen', 'ambientBlue', 'unused1',
            'directionalRed', 'directionalGreen', 'directionalBlue',
            'unused2', 'fogRed', 'fogGreen', 'fogBlue',
            'unused3', 'fogNear', 'fogFar', 'directionalXY',
            'directionalZ', 'directionalFade', 'fogClip', 'fogPower',
            'redXplus', 'greenXplus', 'blueXplus', 'unknownXplus',
            'redXminus', 'greenXminus', 'blueXminus', 'unknownXminus',
            'redYplus', 'greenYplus', 'blueYplus', 'unknownYplus',
            'redYminus', 'greenYminus', 'blueYminus', 'unknownYminus',
            'redZplus', 'greenZplus', 'blueZplus', 'unknownZplus',
            'redZminus', 'greenZminus', 'blueZminus', 'unknownZminus',
            'redSpec', 'greenSpec', 'blueSpec', 'unknownSpec',
            'fresnelPower', 'fogColorFarRed', 'fogColorFarGreen',
            'fogColorFarBlue', 'unused4', 'fogMax', 'lightFadeBegin',
            'lightFadeEnd', (CellInheritedFlags, u'inherits'),
            is_optional=True, old_versions={
                '3Bs3Bs3Bs2f2i3f3Bs3Bs3Bs3Bs3Bs3Bs', '3Bs3Bs3Bs2fi'}),
        MelBase(b'TVDT','occlusionData'),
        # Decoded in xEdit, but properly reading it is relatively slow - see
        # 'Simple Records' option in xEdit - so we skip that for now
        MelBase(b'MHDT','maxHeightData'),
        MelFid(b'LTMP','lightTemplate',),
        # leftover flags, they are now in XCLC
        MelBase(b'LNAM','unknown_LNAM'),
        # Drop in interior cells for Skyrim, see #302 for discussion on this
        MelSkipInterior(MelFloat(b'XCLW', u'waterHeight')),
        MelString(b'XNAM','waterNoiseTexture'),
        MelRegions(),
        MelFid(b'XLCN','location',),
        MelWaterVelocities(),
        MelFid(b'XCWT','water'),
        MelOwnership(),
        MelFid(b'XILL','lockList',),
        MelString(b'XWEM','waterEnvironmentMap'),
        MelFid(b'XCCM','climate',), # xEdit calls this 'Sky/Weather From Region'
        MelFid(b'XCAS','acousticSpace',),
        MelFid(b'XEZN','encounterZone',),
        MelFid(b'XCMO','music',),
        MelFid(b'XCIM','imageSpace',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClas(MelRecord):
    """Class."""
    rec_sig = b'CLAS'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelIcons(),
        MelStruct(b'DATA', [u'4s', u'b', u'19B', u'f', u'I', u'4B'],'unknown','teaches','maximumtraininglevel',
                  'skillWeightsOneHanded','skillWeightsTwoHanded',
                  'skillWeightsArchery','skillWeightsBlock',
                  'skillWeightsSmithing','skillWeightsHeavyArmor',
                  'skillWeightsLightArmor','skillWeightsPickpocket',
                  'skillWeightsLockpicking','skillWeightsSneak',
                  'skillWeightsAlchemy','skillWeightsSpeech',
                  'skillWeightsAlteration','skillWeightsConjuration',
                  'skillWeightsDestruction','skillWeightsIllusion',
                  'skillWeightsRestoration','skillWeightsEnchanting',
                  'bleedoutDefault','voicePoints',
                  'attributeWeightsHealth','attributeWeightsMagicka',
                  'attributeWeightsStamina','attributeWeightsUnknown',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClfm(MelRecord):
    """Color."""
    rec_sig = b'CLFM'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelColorO(),
        MelUInt32(b'FNAM', 'playable'), # actually a bool, stored as uint32
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClmt(MelRecord):
    """Climate."""
    rec_sig = b'CLMT'

    melSet = MelSet(
        MelEdid(),
        MelWeatherTypes(),
        MelString(b'FNAM','sunPath',),
        MelString(b'GNAM','glarePath',),
        MelModel(),
        MelStruct(b'TNAM', [u'6B'],'riseBegin','riseEnd','setBegin','setEnd','volatility','phaseLength',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCobj(MreWithItems):
    """Constructible Object (Recipes)."""
    rec_sig = b'COBJ'
    isKeyedByEid = True # NULL fids are acceptable

    melSet = MelSet(
        MelEdid(),
        MelItemsCounter(),
        MelItems(),
        MelConditions(),
        MelFid(b'CNAM','resultingItem'),
        MelFid(b'BNAM','craftingStation'),
        MelUInt16(b'NAM1', 'resultingQuantity'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreColl(MelRecord):
    """Collision Layer."""
    rec_sig = b'COLL'

    CollisionLayerFlags = Flags(0, Flags.getNames(
        (0,'triggerVolume'),
        (1,'sensor'),
        (2,'navmeshObstacle'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelDescription(),
        MelUInt32(b'BNAM', 'layerID'),
        MelColor(b'FNAM'),
        MelUInt32Flags(b'GNAM', u'flags', CollisionLayerFlags,),
        MelString(b'MNAM', u'col_layer_name',),
        MelUInt32(b'INTV', 'interactablesCount'),
        MelSorted(MelFidList(b'CNAM', 'collidesWith')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCont(MreWithItems):
    """Container."""
    rec_sig = b'CONT'

    ContTypeFlags = Flags(0, Flags.getNames(
        (0, 'allowSoundsWhenAnimation'),
        (1, 'respawns'),
        (2, 'showOwner'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelItemsCounter(),
        MelItems(),
        MelDestructible(),
        MelStruct(b'DATA', [u'B', u'f'],(ContTypeFlags, u'flags'),'weight'),
        MelFid(b'SNAM','soundOpen'),
        MelFid(b'QNAM','soundClose'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCpth(MelRecord):
    """Camera Path"""
    rec_sig = b'CPTH'

    melSet = MelSet(
        MelEdid(),
        MelConditions(),
        MelFidList(b'ANAM','relatedCameraPaths',),
        MelUInt8(b'DATA', 'cameraZoom'),
        MelFids(b'SNAM','cameraShots',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCsty(MelRecord):
    """Combat Style."""
    rec_sig = b'CSTY'

    CstyTypeFlags = Flags(0, Flags.getNames(
        (0, 'dueling'),
        (1, 'flanking'),
        (2, 'allowDualWielding'),
    ))

    melSet = MelSet(
        MelEdid(),
        # esm = Equipment Score Mult
        MelStruct(b'CSGD', [u'10f'],'offensiveMult','defensiveMult','groupOffensiveMult',
        'esmMelee','esmMagic','esmRanged','esmShout','esmUnarmed','esmStaff',
        'avoidThreatChance',),
        MelBase(b'CSMD','unknownValue'),
        MelStruct(b'CSME', [u'8f'],'atkStaggeredMult','powerAtkStaggeredMult','powerAtkBlockingMult',
        'bashMult','bashRecoilMult','bashAttackMult','bashPowerAtkMult','specialAtkMult',),
        MelStruct(b'CSCR', [u'4f'],'circleMult','fallbackMult','flankDistance','stalkTime',),
        MelFloat(b'CSLR', 'strafeMult'),
        MelStruct(b'CSFL', [u'8f'],'hoverChance','diveBombChance','groundAttackChance','hoverTime',
        'groundAttackTime','perchAttackChance','perchAttackTime','flyingAttackChance',),
        MelUInt32Flags(b'DATA', u'flags', CstyTypeFlags),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDebr(MelRecord):
    """Debris."""
    rec_sig = b'DEBR'

    dataFlags = Flags(0, Flags.getNames('hasCollissionData'))

    melSet = MelSet(
        MelEdid(),
        MelGroups('models',
            MelDebrData(),
            MelBase(b'MODT','modt_p'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDial(MelRecord):
    """Dialogue."""
    rec_sig = b'DIAL'

    DialTopicFlags = Flags(0, Flags.getNames(
        (0, 'doAllBeforeRepeating'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelFloat(b'PNAM', 'priority',),
        MelFid(b'BNAM','branch',),
        MelFid(b'QNAM','quest',),
        MelStruct(b'DATA', [u'2B', u'H'],(DialTopicFlags, u'flags_dt'),'category',
                  'subtype',),
        MelFixedString(b'SNAM', u'subtypeName', 4),
        MelUInt32(b'TIFC', u'info_count'), # Updated in MobDial.dump
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDlbr(MelRecord):
    """Dialog Branch."""
    rec_sig = b'DLBR'

    DialogBranchFlags = Flags(0, Flags.getNames(
        (0,'topLevel'),
        (1,'blocking'),
        (2,'exclusive'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelFid(b'QNAM','quest',),
        MelUInt32(b'TNAM', u'category'),
        MelUInt32Flags(b'DNAM', u'flags', DialogBranchFlags),
        MelFid(b'SNAM','startingTopic',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDlvw(MelRecord):
    """Dialog View"""
    rec_sig = b'DLVW'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'QNAM','quest',),
        MelFids(b'BNAM','branches',),
        MelGroups('unknownTNAM',
            MelBase(b'TNAM','unknown',),
        ),
        MelBase(b'ENAM','unknownENAM'),
        MelBase(b'DNAM','unknownDNAM'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MelDobjDnam(MelSorted):
    """This DNAM can have < 8 bytes of noise at the end, so store those
    in a variable and dump them out again when writing."""
    def __init__(self):
        super(MelDobjDnam, self).__init__(MelArray('objects',
            MelStruct(b'DNAM', [u'2I'], 'objectUse', (FID, 'objectID')),
        ), sort_by_attrs='objectUse')

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        # Load everything but the noise
        start_pos = ins.tell()
        super(MelDobjDnam, self).load_mel(record, ins, sub_type, size_,
                                          *debug_strs)
        # Now, read the remainder of the subrecord and store it
        read_size = ins.tell() - start_pos
        record.unknownDNAM = ins.read(size_ - read_size)

    def pack_subrecord_data(self, record):
        return super(MelDobjDnam, self).pack_subrecord_data(
            record) + record.unknownDNAM

    def getSlotsUsed(self):
        return super(MelDobjDnam, self).getSlotsUsed() + ('unknownDNAM',)

class MreDobj(MelRecord):
    """Default Object Manager."""
    rec_sig = b'DOBJ'

    melSet = MelSet(
        MelEdid(),
        MelDobjDnam(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDoor(MelRecord):
    """Door."""
    rec_sig = b'DOOR'

    DoorTypeFlags = Flags(0, Flags.getNames(
        (1, 'automatic'),
        (2, 'hidden'),
        (3, 'minimalUse'),
        (4, 'slidingDoor'),
        (5, 'doNotOpenInCombatSearch'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelFid(b'SNAM','soundOpen'),
        MelFid(b'ANAM','soundClose'),
        MelFid(b'BNAM','soundLoop'),
        MelUInt8Flags(b'FNAM', u'flags', DoorTypeFlags),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDual(MelRecord):
    """Dual Cast Data."""
    rec_sig = b'DUAL'

    DualCastDataFlags = Flags(0, Flags.getNames(
        (0,'hitEffectArt'),
        (1,'projectile'),
        (2,'explosion'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelStruct(b'DATA', [u'6I'],(FID,'projectile'),(FID,'explosion'),(FID,'effectShader'),
                  (FID,'hitEffectArt'),(FID,'impactDataSet'),(DualCastDataFlags, u'flags'),),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEczn(MelRecord):
    """Encounter Zone."""
    rec_sig = b'ECZN'

    EcznTypeFlags = Flags(0, Flags.getNames(
            (0, 'neverResets'),
            (1, 'matchPCBelowMinimumLevel'),
            (2, 'disableCombatBoundary'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelTruncatedStruct(b'DATA', [u'2I', u'2b', u'B', u'b'], (FID, u'owner'),
                           (FID, u'location'), u'rank',
                           'minimumLevel', (EcznTypeFlags, u'flags'),
                           'maxLevel', old_versions={'2I'}),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEfsh(MelRecord):
    """Effect Shader."""
    rec_sig = b'EFSH'

    EfshGeneralFlags = Flags(0, Flags.getNames(
        (0, 'noMembraneShader'),
        (1, 'membraneGrayscaleColor'),
        (2, 'membraneGrayscaleAlpha'),
        (3, 'noParticleShader'),
        (4, 'edgeEffectInverse'),
        (5, 'affectSkinOnly'),
        (6, 'ignoreAlpha'),
        (7, 'projectUVs'),
        (8, 'ignoreBaseGeometryAlpha'),
        (9, 'lighting'),
        (10, 'noWeapons'),
        (11, 'unknown11'),
        (12, 'unknown12'),
        (13, 'unknown13'),
        (14, 'unknown14'),
        (15, 'particleAnimated'),
        (16, 'particleGrayscaleColor'),
        (17, 'particleGrayscaleAlpha'),
        (18, 'unknown18'),
        (19, 'unknown19'),
        (20, 'unknown20'),
        (21, 'unknown21'),
        (22, 'unknown22'),
        (23, 'unknown23'),
        (24, 'useBloodGeometry'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelIcon(u'fillTexture'),
        MelIco2(u'particleTexture'),
        MelString(b'NAM7','holesTexture'),
        MelString(b'NAM8','membranePaletteTexture'),
        MelString(b'NAM9','particlePaletteTexture'),
        MelTruncatedStruct(b'DATA',
            [u'4s', u'3I', u'3B', u's', u'9f', u'3B', u's', u'8f', u'5I',
             u'19f', u'3B', u's', u'3B', u's', u'3B', u's', u'11f', u'I',
             u'5f', u'3B', u's', u'f', u'2I', u'6f', u'I', u'3B', u's', u'3B',
             u's', u'9f', u'8I', u'2f', u'I'],
            'unused1', 'memSBlend', 'memBlendOp', 'memZFunc','fillRed',
            'fillGreen', 'fillBlue', 'unused2', 'fillAlphaIn', 'fillFullAlpha',
            'fillAlphaOut', 'fillAlphaRatio', 'fillAlphaAmp', 'fillAlphaPulse',
            'fillAnimSpeedU', 'fillAnimSpeedV', 'edgeEffectOff', 'edgeRed',
            'edgeGreen', 'edgeBlue', 'unused3', 'edgeAlphaIn', 'edgeFullAlpha',
            'edgeAlphaOut', 'edgeAlphaRatio', 'edgeAlphaAmp', 'edgeAlphaPulse',
            'fillFullAlphaRatio', 'edgeFullAlphaRatio', 'memDestBlend',
            'partSourceBlend', 'partBlendOp', 'partZTestFunc', 'partDestBlend',
            'partBSRampUp', 'partBSFull', 'partBSRampDown', 'partBSRatio',
            'partBSPartCount', 'partBSLifetime', 'partBSLifetimeDelta',
            'partSSpeedNorm', 'partSAccNorm', 'partSVel1', 'partSVel2',
            'partSVel3', 'partSAccel1', 'partSAccel2', 'partSAccel3',
            'partSKey1', 'partSKey2', 'partSKey1Time', 'partSKey2Time',
            'key1Red', 'key1Green', 'key1Blue', 'unused4', 'key2Red',
            'key2Green', 'key2Blue', 'unused5', 'key3Red', 'key3Green',
            'key3Blue', 'unused6', 'colorKey1Alpha', 'colorKey2Alpha',
            'colorKey3Alpha', 'colorKey1KeyTime', 'colorKey2KeyTime',
            'colorKey3KeyTime', 'partSSpeedNormDelta', 'partSSpeedRotDeg',
            'partSSpeedRotDegDelta', 'partSRotDeg', 'partSRotDegDelta',
            (FID, 'addonModels'), 'holesStart', 'holesEnd', 'holesStartVal',
            'holesEndVal', 'edgeWidthAlphaUnit', 'edgeAlphRed',
            'edgeAlphGreen', 'edgeAlphBlue', 'unused7', 'expWindSpeed',
            'textCountU', 'textCountV', 'addonModelIn', 'addonModelOut',
            'addonScaleStart', 'addonScaleEnd', 'addonScaleIn',
            'addonScaleOut', (FID, 'ambientSound'), 'key2FillRed',
            'key2FillGreen', 'key2FillBlue', 'unused8', 'key3FillRed',
            'key3FillGreen', 'key3FillBlue', 'unused9', 'key1ScaleFill',
            'key2ScaleFill', 'key3ScaleFill', 'key1FillTime', 'key2FillTime',
            'key3FillTime', 'colorScale', 'birthPosOffset',
            'birthPosOffsetRange','startFrame', 'startFrameVariation',
            'endFrame','loopStartFrame', 'loopStartVariation', 'frameCount',
            'frameCountVariation', (EfshGeneralFlags, u'flags'),
            'fillTextScaleU', 'fillTextScaleV', 'sceneGraphDepthLimit',
            old_versions={
                '4s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I6fI3Bs3Bs9f8I2f',
                '4s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I6fI3Bs3Bs6f',
                '4s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I6fI',
                '4s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I6f'
            }),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEnch(MelRecord):
    """Object Effect."""
    rec_sig = b'ENCH'

    EnchGeneralFlags = Flags(0, Flags.getNames(
        (0, 'noAutoCalc'),
        (1, 'unknownTwo'),
        (2, 'extendDurationOnRecast'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelTruncatedStruct(b'ENIT', [u'i', u'2I', u'i', u'2I', u'f', u'2I'], 'enchantmentCost',
                           (EnchGeneralFlags, u'generalFlags'), 'castType',
                           'enchantmentAmount', 'targetType', 'enchantType',
                           'chargeTime', (FID, 'baseEnchantment'),
                           (FID, 'wornRestrictions'),
                           old_versions={'i2Ii2IfI'}),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEqup(MelRecord):
    """Equip Type."""
    rec_sig = b'EQUP'
    melSet = MelSet(
        MelEdid(),
        MelFidList(b'PNAM','canBeEquipped'),
        MelUInt32(b'DATA', 'useAllParents'), # actually a bool
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreExpl(MelRecord):
    """Explosion."""
    rec_sig = b'EXPL'

    ExplTypeFlags = Flags(0, Flags.getNames(
        (1, 'alwaysUsesWorldOrientation'),
        (2, 'knockDownAlways'),
        (3, 'knockDownByFormular'),
        (4, 'ignoreLosCheck'),
        (5, 'pushExplosionSourceRefOnly'),
        (6, 'ignoreImageSpaceSwap'),
        (7, 'chain'),
        (8, 'noControllerVibration'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelEnchantment(),
        MelFid(b'MNAM','imageSpaceModifier'),
        MelTruncatedStruct(
            b'DATA', [u'6I', u'5f', u'2I'], (FID, u'light'), (FID, u'sound1'),
            (FID, u'sound2'), (FID, u'impactDataset'),
            (FID, u'placedObject'), (FID, u'spawnProjectile'),
            u'force', u'damage', u'radius', u'isRadius', u'verticalOffsetMult',
            (ExplTypeFlags, u'flags'), u'soundLevel',
            old_versions={u'6I5fI', u'6I5f', u'6I4f'}),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEyes(MelRecord):
    """Eyes."""
    rec_sig = b'EYES'

    EyesTypeFlags = Flags(0, Flags.getNames(
            (0, 'playable'),
            (1, 'notMale'),
            (2, 'notFemale'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelIcons(),
        MelUInt8Flags(b'DATA', u'flags', EyesTypeFlags),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFact(MelRecord):
    """Faction."""
    rec_sig = b'FACT'

    _general_flags = Flags(0, Flags.getNames(
        ( 0, u'hidden_from_pc'),
        ( 1, u'special_combat'),
        ( 6, u'track_crime'),
        ( 7, u'ignore_crimes_murder'),
        ( 8, u'ignore_crimes_assault'),
        ( 9, u'ignore_crimes_stealing'),
        (10, u'ignore_crimes_trespass'),
        (11, u'do_not_report_crimes_against_members'),
        (12, u'crime_gold_use_defaults'),
        (13, u'ignore_crimes_pickpocket'),
        (14, u'allow_sell'), # vendor
        (15, u'can_be_owner'),
        (16, u'ignore_crimes_werewolf'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelRelations(),
        MelUInt32Flags(b'DATA', u'general_flags', _general_flags),
        MelFid(b'JAIL', u'exterior_jail_marker'),
        MelFid(b'WAIT', u'follower_wait_marker'),
        MelFid(b'STOL', u'stolen_goods_container'),
        MelFid(b'PLCN', u'player_inventory_container'),
        MelFid(b'CRGR', u'shared_crime_faction_list'),
        MelFid(b'JOUT', u'jail_outfit'),
        # 'cv_arrest' and 'cv_attack_on_sight' are actually bools, cv means
        # 'crime value' (which is what this struct is about)
        MelTruncatedStruct(b'CRVA', [u'2B', u'5H', u'f', u'2H'], u'cv_arrest',
                           u'cv_attack_on_sight', u'cv_murder', u'cv_assault',
                           u'cv_trespass', u'cv_pickpocket',
                           u'cv_unknown', u'cv_steal_multiplier', u'cv_escape',
                           u'cv_werewolf', old_versions={u'2B5Hf', u'2B5H'}),
        MelFactionRanks(),
        MelFid(b'VEND', u'vendor_buy_sell_list'),
        MelFid(b'VENC', u'merchant_container'),
        # 'vv_only_buys_stolen_items' and 'vv_not_sell_buy' are actually bools,
        # vv means 'vendor value' (which is what this struct is about)
        MelStruct(b'VENV', [u'3H', u'2s', u'2B', u'2s'], u'vv_start_hour', u'vv_end_hour',
                  u'vv_radius', u'vv_unknown1', u'vv_only_buys_stolen_items',
                  u'vv_not_sell_buy', u'vv_unknown2'),
        MelLocation(b'PLVD'),
        MelConditionCounter(),
        MelConditions(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFlor(MelRecord):
    """Flora."""
    rec_sig = b'FLOR'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelBase(b'PNAM','unknown01'),
        MelLString(b'RNAM','activateTextOverride'),
        MelBase(b'FNAM','unknown02'),
        MelFid(b'PFIG','ingredient'),
        MelFid(b'SNAM','harvestSound'),
        MelStruct(b'PFPC', [u'4B'],'spring','summer','fall','winter',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFstp(MelRecord):
    """Footstep."""
    rec_sig = b'FSTP'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'DATA','impactSet'),
        MelString(b'ANAM','tag'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFsts(MelRecord):
    """Footstep Set."""
    rec_sig = b'FSTS'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'XCNT', [u'5I'],'walkForward','runForward','walkForwardAlt',
                  'runForwardAlt','walkForwardAlternate2',),
        MelFidList(b'DATA','footstepSets'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFurn(MelRecord):
    """Furniture."""
    rec_sig = b'FURN'

    FurnGeneralFlags = Flags(0, Flags.getNames(
        (1, 'ignoredBySandbox'),
    ))

    FurnActiveMarkerFlags = Flags(0, Flags.getNames(
        (0, 'sit0'),
        (1, 'sit1'),
        (2, 'sit2'),
        (3, 'sit3'),
        (4, 'sit4'),
        (5, 'sit5'),
        (6, 'sit6'),
        (7, 'sit7'),
        (8, 'sit8'),
        (9, 'sit9'),
        (10, 'sit10'),
        (11, 'sit11'),
        (12, 'sit12'),
        (13, 'sit13'),
        (14, 'sit14'),
        (15, 'sit15'),
        (16, 'sit16'),
        (17, 'sit17'),
        (18, 'sit18'),
        (19, 'sit19'),
        (20, 'sit20'),
        (21, 'Sit21'),
        (22, 'Sit22'),
        (23, 'sit23'),
        (24, 'unknown25'),
        (25, 'disablesActivation'),
        (26, 'isPerch'),
        (27, 'mustExittoTalk'),
        (28, 'unknown29'),
        (29, 'unknown30'),
        (30, 'unknown31'),
        (31, 'unknown32'),
    ))

    MarkerEntryPointFlags = Flags(0, Flags.getNames(
            (0, 'front'),
            (1, 'behind'),
            (2, 'right'),
            (3, 'left'),
            (4, 'up'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelBase(b'PNAM','pnam_p'),
        MelUInt16Flags(b'FNAM', u'general_f', FurnGeneralFlags),
        MelFid(b'KNAM','interactionKeyword'),
        MelUInt32Flags(b'MNAM', u'activeMarkers', FurnActiveMarkerFlags),
        MelStruct(b'WBDT', [u'B', u'b'],'benchType','usesSkill',),
        MelFid(b'NAM1','associatedSpell'),
        MelGroups('markers',
            MelUInt32(b'ENAM', 'markerIndex',),
            MelStruct(b'NAM0', [u'2s', u'H'], u'unknown1',
                      (MarkerEntryPointFlags, u'disabledPoints_f')),
            MelFid(b'FNMK','markerKeyword',),
        ),
        MelGroups('entryPoints',
            MelStruct(b'FNPR', [u'2H'], u'markerType',
                      (MarkerEntryPointFlags, u'entryPointsFlags')),
        ),
        MelString(b'XMRK','modelFilename'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreGmst(MreGmstBase):
    """Game Setting."""
    isKeyedByEid = True # NULL fids are acceptable.

#------------------------------------------------------------------------------
class MreGras(MelRecord):
    """Grass."""
    rec_sig = b'GRAS'

    GrasTypeFlags = Flags(0, Flags.getNames(
            (0, 'vertexLighting'),
            (1, 'uniformScaling'),
            (2, 'fitToSlope'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelStruct(b'DATA', [u'3B', u's', u'H', u'2s', u'I', u'4f', u'B', u'3s'],'density','minSlope','maxSlope',
                  'unkGras1','unitsFromWater','unkGras2',
                  'unitsFromWaterType','positionRange','heightRange',
                  'colorRange', 'wave_period', (GrasTypeFlags, u'flags'),
                  'unkGras3',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreHazd(MelRecord):
    """Hazard."""
    rec_sig = b'HAZD'

    HazdTypeFlags = Flags(0, Flags.getNames(
        (0, 'affectsPlayerOnly'),
        (1, 'inheritDurationFromSpawnSpell'),
        (2, 'alignToImpactNormal'),
        (3, 'inheritRadiusFromSpawnSpell'),
        (4, 'dropToGround'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelFid(b'MNAM','imageSpaceModifier'),
        MelStruct(b'DATA', [u'I', u'4f', u'5I'],'limit','radius','lifetime',
                  'imageSpaceRadius','targetInterval',(HazdTypeFlags, u'flags'),
                  (FID,'spell'),(FID,'light'),(FID,'impactDataSet'),(FID,'sound'),),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreHdpt(MelRecord):
    """Head Part."""
    rec_sig = b'HDPT'

    HdptTypeFlags = Flags(0, Flags.getNames(
        (0, 'playable'),
        (1, 'notFemale'),
        (2, 'notMale'),
        (3, 'isExtraPart'),
        (4, 'useSolidTint'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelUInt8Flags(b'DATA', u'flags', HdptTypeFlags),
        MelUInt32(b'PNAM', 'hdpt_type'),
        MelSorted(MelFids(b'HNAM', 'extraParts')),
        MelGroups('partsData',
            MelUInt32(b'NAM0', 'headPartType',),
            MelString(b'NAM1','filename'),
        ),
        MelFid(b'TNAM','textureSet'),
        MelFid(b'CNAM','color'),
        MelFid(b'RNAM','validRaces'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIdle(MelRecord):
    """Idle Animation."""
    rec_sig = b'IDLE'

    IdleTypeFlags = Flags(0, Flags.getNames(
        u'parent',
        u'sequence',
        u'noAttacking',
        u'blocking',
    ), unknown_is_unused=True)

    melSet = MelSet(
        MelEdid(),
        MelConditions(),
        MelString(b'DNAM','filename'),
        MelString(b'ENAM','animationEvent'),
        MelGroups('idleAnimations',
            MelStruct(b'ANAM', [u'I', u'I'],(FID,'parent'),(FID,'prevId'),),
        ),
        MelStruct(b'DATA', [u'4B', u'H'],'loopMin','loopMax',(IdleTypeFlags, u'flags'),
                  'animationGroupSection','replayDelay',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIdlm(MelRecord):
    """Idle Marker."""
    rec_sig = b'IDLM'

    IdlmTypeFlags = Flags(0, Flags.getNames(
        (0, 'runInSequence'),
        (1, 'unknown1'),
        (2, 'doOnce'),
        (3, 'unknown3'),
        (4, 'ignoredBySandbox'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8Flags(b'IDLF', u'flags', IdlmTypeFlags),
        MelCounter(MelUInt8(b'IDLC', 'animation_count'), counts='animations'),
        MelFloat(b'IDLT', 'idleTimerSetting'),
        MelFidList(b'IDLA','animations'),
        MelModel(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreInfo(MelRecord):
    """Dialog Response."""
    rec_sig = b'INFO'

    _InfoResponsesFlags = Flags(0, Flags.getNames(
            (0, 'useEmotionAnimation'),
        ))

    _EnamResponseFlags = Flags(0, Flags.getNames(
        (0,  u'goodbye'),
        (1,  u'random'),
        (2,  u'say_once'),
        (3,  u'requires_player_activation'),
        (4,  u'info_refusal'),
        (5,  u'random_end'),
        (6,  u'invisible_continue'),
        (7,  u'walk_away'),
        (8,  u'walk_away_invisible_in_menu'),
        (9,  u'force_subtitle'),
        (10, u'can_move_while_greeting'),
        (11, u'no_lip_file'),
        (12, u'requires_post_processing'),
        (13, u'audio_output_override'),
        (14, u'spends_favor_points'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBase(b'DATA','unknownDATA'),
        MelStruct(b'ENAM', [u'2H'], (_EnamResponseFlags, u'flags'),
                  'resetHours',),
        MelFid(b'TPIC', u'info_topic'),
        MelFid(b'PNAM', 'prev_info'),
        MelUInt8(b'CNAM', 'favorLevel'),
        MelFids(b'TCLT','linkTo',),
        MelFid(b'DNAM','responseData',),
        MelGroups('responses',
            MelStruct(b'TRDT', [u'2I', u'4s', u'B', u'3s', u'I', u'B', u'3s'], u'emotionType', u'emotionValue',
                      u'unused1', u'responseNumber',
                      u'unused2', (FID, u'sound'),
                      (_InfoResponsesFlags, u'responseFlags'),
                      u'unused3'),
            MelLString(b'NAM1','responseText'),
            MelString(b'NAM2','scriptNotes'),
            MelString(b'NAM3','edits'),
            MelFid(b'SNAM','idleAnimationsSpeaker',),
            MelFid(b'LNAM','idleAnimationsListener',),
        ),
        MelConditions(),
        MelGroups('leftOver',
            MelBase(b'SCHR','unknown1'),
            MelFid(b'QNAM','unknown2'),
            MelNull(b'NEXT'),
        ),
        MelLString(b'RNAM','prompt'),
        MelFid(b'ANAM','speaker',),
        MelFid(b'TWAT','walkAwayTopic',),
        MelFid(b'ONAM','audioOutputOverride',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreImad(MelRecord):
    """Image Space Adapter."""
    rec_sig = b'IMAD'

    _ImadDofFlags = Flags(0, Flags.getNames(
        (0, 'useTarget'),
        (1, 'unknown2'),
        (2, 'unknown3'),
        (3, 'unknown4'),
        (4, 'unknown5'),
        (5, 'unknown6'),
        (6, 'unknown7'),
        (7, 'unknown8'),
        (8, 'modeFront'),
        (9, 'modeBack'),
        (10, 'noSky'),
        (11, 'blurRadiusBit2'),
        (12, 'blurRadiusBit1'),
        (13, 'blurRadiusBit0'),
    ))
    _ImadRadialBlurFlags = Flags(0, Flags.getNames(
        (0, 'useTarget')
    ))

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DNAM', [u'I', u'f', u'49I', u'2f', u'8I'], u'animatable', u'duration',
                  u'eyeAdaptSpeedMult', u'eyeAdaptSpeedAdd',
                  u'bloomBlurRadiusMult', u'bloomBlurRadiusAdd',
                  u'bloomThresholdMult', u'bloomThresholdAdd',
                  u'bloomScaleMult', u'bloomScaleAdd', u'targetLumMinMult',
                  u'targetLumMinAdd', u'targetLumMaxMult', u'targetLumMaxAdd',
                  u'sunlightScaleMult', u'sunlightScaleAdd', u'skyScaleMult',
                  u'skyScaleAdd', u'unknown08Mult', u'unknown48Add',
                  u'unknown09Mult', u'unknown49Add', u'unknown0AMult',
                  u'unknown4AAdd', u'unknown0BMult', u'unknown4BAdd',
                  u'unknown0CMult', u'unknown4CAdd', u'unknown0DMult',
                  u'unknown4DAdd', u'unknown0EMult', u'unknown4EAdd',
                  u'unknown0FMult', u'unknown4FAdd', u'unknown10Mult',
                  u'unknown50Add', u'saturationMult', u'saturationAdd',
                  u'brightnessMult', u'brightnessAdd', u'contrastMult',
                  u'contrastAdd', u'unknown14Mult', u'unknown54Add',
                  u'tintColor', u'blurRadius', u'doubleVisionStrength',
                  u'radialBlurStrength', u'radialBlurRampUp',
                  u'radialBlurStart',
                  (_ImadRadialBlurFlags, u'radialBlurFlags'),
                  u'radialBlurCenterX', u'radialBlurCenterY', u'dofStrength',
                  u'dofDistance', u'dofRange', (_ImadDofFlags, u'dofFlags'),
                  u'radialBlurRampDown', u'radialBlurDownStart', u'fadeColor',
                  u'motionBlurStrength'),
        MelValueInterpolator(b'BNAM', 'blurRadiusInterp'),
        MelValueInterpolator(b'VNAM', 'doubleVisionStrengthInterp'),
        MelColorInterpolator(b'TNAM', 'tintColorInterp'),
        MelColorInterpolator(b'NAM3', 'fadeColorInterp'),
        MelValueInterpolator(b'RNAM', 'radialBlurStrengthInterp'),
        MelValueInterpolator(b'SNAM', 'radialBlurRampUpInterp'),
        MelValueInterpolator(b'UNAM', 'radialBlurStartInterp'),
        MelValueInterpolator(b'NAM1', 'radialBlurRampDownInterp'),
        MelValueInterpolator(b'NAM2', 'radialBlurDownStartInterp'),
        MelValueInterpolator(b'WNAM', 'dofStrengthInterp'),
        MelValueInterpolator(b'XNAM', 'dofDistanceInterp'),
        MelValueInterpolator(b'YNAM', 'dofRangeInterp'),
        MelValueInterpolator(b'NAM4', 'motionBlurStrengthInterp'),
        MelValueInterpolator(b'\x00IAD', 'eyeAdaptSpeedMultInterp'),
        MelValueInterpolator(b'\x40IAD', 'eyeAdaptSpeedAddInterp'),
        MelValueInterpolator(b'\x01IAD', 'bloomBlurRadiusMultInterp'),
        MelValueInterpolator(b'\x41IAD', 'bloomBlurRadiusAddInterp'),
        MelValueInterpolator(b'\x02IAD', 'bloomThresholdMultInterp'),
        MelValueInterpolator(b'\x42IAD', 'bloomThresholdAddInterp'),
        MelValueInterpolator(b'\x03IAD', 'bloomScaleMultInterp'),
        MelValueInterpolator(b'\x43IAD', 'bloomScaleAddInterp'),
        MelValueInterpolator(b'\x04IAD', 'targetLumMinMultInterp'),
        MelValueInterpolator(b'\x44IAD', 'targetLumMinAddInterp'),
        MelValueInterpolator(b'\x05IAD', 'targetLumMaxMultInterp'),
        MelValueInterpolator(b'\x45IAD', 'targetLumMaxAddInterp'),
        MelValueInterpolator(b'\x06IAD', 'sunlightScaleMultInterp'),
        MelValueInterpolator(b'\x46IAD', 'sunlightScaleAddInterp'),
        MelValueInterpolator(b'\x07IAD', 'skyScaleMultInterp'),
        MelValueInterpolator(b'\x47IAD', 'skyScaleAddInterp'),
        MelBase(b'\x08IAD', 'unknown08IAD'),
        MelBase(b'\x48IAD', 'unknown48IAD'),
        MelBase(b'\x09IAD', 'unknown09IAD'),
        MelBase(b'\x49IAD', 'unknown49IAD'),
        MelBase(b'\x0AIAD', 'unknown0aIAD'),
        MelBase(b'\x4AIAD', 'unknown4aIAD'),
        MelBase(b'\x0BIAD', 'unknown0bIAD'),
        MelBase(b'\x4BIAD', 'unknown4bIAD'),
        MelBase(b'\x0CIAD', 'unknown0cIAD'),
        MelBase(b'\x4CIAD', 'unknown4cIAD'),
        MelBase(b'\x0DIAD', 'unknown0dIAD'),
        MelBase(b'\x4DIAD', 'unknown4dIAD'),
        MelBase(b'\x0EIAD', 'unknown0eIAD'),
        MelBase(b'\x4EIAD', 'unknown4eIAD'),
        MelBase(b'\x0FIAD', 'unknown0fIAD'),
        MelBase(b'\x4FIAD', 'unknown4fIAD'),
        MelBase(b'\x10IAD', 'unknown10IAD'),
        MelBase(b'\x50IAD', 'unknown50IAD'),
        MelValueInterpolator(b'\x11IAD', 'saturationMultInterp'),
        MelValueInterpolator(b'\x51IAD', 'saturationAddInterp'),
        MelValueInterpolator(b'\x12IAD', 'brightnessMultInterp'),
        MelValueInterpolator(b'\x52IAD', 'brightnessAddInterp'),
        MelValueInterpolator(b'\x13IAD', 'contrastMultInterp'),
        MelValueInterpolator(b'\x53IAD', 'contrastAddInterp'),
        MelBase(b'\x14IAD', 'unknown14IAD'),
        MelBase(b'\x54IAD', 'unknown54IAD'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreImgs(MelRecord):
    """Image Space."""
    rec_sig = b'IMGS'

    melSet = MelSet(
        MelEdid(),
        MelBase(b'ENAM','eman_p'),
        MelStruct(b'HNAM', [u'9f'],'eyeAdaptSpeed','bloomBlurRadius','bloomThreshold','bloomScale',
                  'receiveBloomThreshold','white','sunlightScale','skyScale',
                  'eyeAdaptStrength',),
        MelStruct(b'CNAM', [u'3f'],'Saturation','Brightness','Contrast',),
        MelStruct(b'TNAM', [u'4f'],'tintAmount','tintRed','tintGreen','tintBlue',),
        MelStruct(b'DNAM', [u'3f', u'2s', u'H'],'dofStrength','dofDistance','dofRange','unknown',
                  'skyBlurRadius',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIngr(MelRecord):
    """Ingredient."""
    rec_sig = b'INGR'

    IngrTypeFlags = Flags(0,  Flags.getNames(
        (0, 'no_auto_calc'),
        (1, 'food_item'),
        (8, 'references_persist'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelKeywords(),
        MelModel(),
        MelIcons(),
        MelEquipmentType(),
        MelPickupSound(),
        MelDropSound(),
        MelStruct(b'DATA', [u'i', u'f'],'value','weight'),
        MelStruct(b'ENIT', [u'i', u'I'],'ingrValue',(IngrTypeFlags, u'flags'),),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIpct(MelRecord):
    """Impact."""
    rec_sig = b'IPCT'

    _IpctTypeFlags = Flags(0, Flags.getNames('noDecalData'))

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelTruncatedStruct(b'DATA', [u'f', u'I', u'2f', u'I', u'2B', u'2s'], 'effectDuration',
                           'effectOrientation', 'angleThreshold',
                           'placementRadius', 'soundLevel',
                           (_IpctTypeFlags, u'ipctFlags'), 'impactResult',
                           'unkIpct1', old_versions={'fI2f'}),
        MelDecalData(),
        MelFid(b'DNAM','textureSet'),
        MelFid(b'ENAM','secondarytextureSet'),
        MelFid(b'SNAM','sound1'),
        MelFid(b'NAM1','sound2'),
        MelFid(b'NAM2','hazard'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIpds(MelRecord):
    """Impact Dataset."""
    rec_sig = b'IPDS'

    melSet = MelSet(
        MelEdid(),
        MelSorted(MelGroups('impactData',
            MelStruct(b'PNAM', [u'2I'], (FID, 'material'), (FID, 'impact')),
        ), sort_by_attrs='material'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreKeym(MelRecord):
    """Key."""
    rec_sig = b'KEYM'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelPickupSound(),
        MelDropSound(),
        MelKeywords(),
        MelStruct(b'DATA', [u'i', u'f'],'value','weight'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreKywd(MelRecord):
    """Keyword record."""
    rec_sig = b'KYWD'

    melSet = MelSet(
        MelEdid(),
        MelColorO(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLcrt(MelRecord):
    """Location Reference Type."""
    rec_sig = b'LCRT'

    melSet = MelSet(
        MelEdid(),
        MelColorO(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLctn(MelRecord):
    """Location"""
    rec_sig = b'LCTN'

    melSet = MelSet(
        MelEdid(),
        MelArray('actorCellPersistentReference',
            MelStruct(b'ACPR', [u'2I', u'2h'], (FID, 'actor'), (FID, 'location'),
                      'gridX', 'gridY'),
        ),
        MelArray('locationCellPersistentReference',
            MelStruct(b'LCPR', [u'2I', u'2h'], (FID, 'actor'), (FID, 'location'),
                      'gridX', 'gridY'),
        ),
        MelFidList(b'RCPR','referenceCellPersistentReference',),
        MelArray('actorCellUnique',
            MelStruct(b'ACUN', [u'3I'], (FID, 'actor'), (FID, 'eef'),
                      (FID, 'location')),
        ),
        MelArray('locationCellUnique',
            MelStruct(b'LCUN', [u'3I'], (FID, 'actor'), (FID, 'eef'),
                      (FID, 'location')),
        ),
        MelFidList(b'RCUN','referenceCellUnique',),
        MelArray('actorCellStaticReference',
            MelStruct(b'ACSR', [u'3I', u'2h'], (FID, 'locRefType'), (FID, 'marker'),
                      (FID, 'location'), 'gridX', 'gridY'),
        ),
        MelArray('locationCellStaticReference',
            MelStruct(b'LCSR', [u'3I', u'2h'], (FID, 'locRefType'), (FID, 'marker'),
                      (FID, 'location'), 'gridX', 'gridY'),
        ),
        MelFidList(b'RCSR','referenceCellStaticReference',),
        MelGroups(u'actorCellEncounterCell',
            MelArray(u'coordinates',
                MelStruct(b'ACEC', [u'2h'], u'grid_x', u'grid_y'),
                     prelude=MelFid(b'ACEC', u'location'),
            ),
        ),
        MelGroups(u'locationCellEncounterCell',
            MelArray(u'coordinates',
                MelStruct(b'LCEC', [u'2h'], u'grid_x', u'grid_y'),
                     prelude=MelFid(b'LCEC', u'location'),
            ),
        ),
        MelGroups(u'referenceCellEncounterCell',
            MelArray(u'coordinates',
                MelStruct(b'RCEC', [u'2h'], u'grid_x', u'grid_y'),
                     prelude=MelFid(b'RCEC', u'location'),
            ),
        ),
        MelFidList(b'ACID','actorCellMarkerReference',),
        MelFidList(b'LCID','locationCellMarkerReference',),
        MelArray('actorCellEnablePoint',
            MelStruct(b'ACEP', [u'2I', u'2h'], (FID, 'actor'), (FID,'ref'), 'gridX',
                      'gridY'),
        ),
        MelArray('locationCellEnablePoint',
            MelStruct(b'LCEP', [u'2I', u'2h'], (FID, 'actor'), (FID,'ref'), 'gridX',
                      'gridY'),
        ),
        MelFull(),
        MelKeywords(),
        MelFid(b'PNAM','parentLocation',),
        MelFid(b'NAM1','music',),
        MelFid(b'FNAM','unreportedCrimeFaction',),
        MelFid(b'MNAM','worldLocationMarkerRef',),
        MelFloat(b'RNAM', 'worldLocationRadius'),
        MelFid(b'NAM0','horseMarkerRef',),
        MelColorO(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLgtm(MelRecord):
    """Lighting Template."""
    rec_sig = b'LGTM'

    class MelLgtmData(MelStruct):
        """Older format skips 8 bytes in the middle and has the same unpacked
        length, so we can't use MelTruncatedStruct."""
        def load_mel(self, record, ins, sub_type, size_, *debug_strs):
            __unpacker=structs_cache[u'3Bs3Bs3Bs2f2i3f24s3Bs3f4s'].unpack
            if size_ == 92:
                super(MreLgtm.MelLgtmData, self).load_mel(
                    record, ins, sub_type, size_, *debug_strs)
                return
            elif size_ == 84:
                unpacked_val = ins.unpack(__unpacker, size_, *debug_strs)
                # Pad it with 8 null bytes in the middle
                unpacked_val = (unpacked_val[:19]
                                + (unpacked_val[19] + null4 * 2,)
                                + unpacked_val[20:])
                for attr, value, action in zip(self.attrs, unpacked_val,
                                                self.actions):
                    if callable(action): value = action(value)
                    setattr(record, attr, value)
            else:
                raise ModSizeError(ins.inName, debug_strs, (92, 84), size_)

    melSet = MelSet(
        MelEdid(),
        MelLgtmData(b'DATA',
            [u'3B', u's', u'3B', u's', u'3B', u's', u'2f', u'2i', u'3f',
             u'32s', u'3B', u's', u'3f', u'4s'], 'redLigh', 'greenLigh',
            'blueLigh','unknownLigh', 'redDirect', 'greenDirect', 'blueDirect',
            'unknownDirect', 'redFog', 'greenFog', 'blueFog', 'unknownFog',
            'fogNear', 'fogFar', 'dirRotXY', 'dirRotZ', 'directionalFade',
            'fogClipDist', 'fogPower', 'ambientColors',
            'redFogFar', 'greenFogFar', 'blueFogFar', 'unknownFogFar',
            'fogMax', 'lightFaceStart', 'lightFadeEnd',
            'unknownData2'),
        MelTruncatedStruct(
            b'DALC', [u'4B', u'4B', u'4B', u'4B', u'4B', u'4B', u'4B', u'f'],
            'redXplus', 'greenXplus', 'blueXplus',
            'unknownXplus', 'redXminus', 'greenXminus', 'blueXminus',
            'unknownXminus', 'redYplus', 'greenYplus', 'blueYplus',
            'unknownYplus', 'redYminus', 'greenYminus', 'blueYminus',
            'unknownYminus', 'redZplus', 'greenZplus', 'blueZplus',
            'unknownZplus', 'redZminus', 'greenZminus', 'blueZminus',
            'unknownZminus', 'redSpec', 'greenSpec', 'blueSpec',
            'unknownSpec', 'fresnelPower', old_versions={'4B4B4B4B4B4B'}),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLigh(MelRecord):
    """Light."""
    rec_sig = b'LIGH'

    LighTypeFlags = Flags(0, Flags.getNames(
            (0, 'dynamic'),
            (1, 'canbeCarried'),
            (2, 'negative'),
            (3, 'flicker'),
            (4, 'unknown'),
            (5, 'offByDefault'),
            (6, 'flickerSlow'),
            (7, 'pulse'),
            (8, 'pulseSlow'),
            (9, 'spotLight'),
            (10, 'shadowSpotlight'),
            (11, 'shadowHemisphere'),
            (12, 'shadowOmnidirectional'),
            (13, 'portalstrict'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelModel(),
        MelDestructible(),
        MelFull(),
        MelIcons(),
        # fe = 'Flicker Effect'
        MelStruct(b'DATA', [u'i', u'I', u'4B', u'I', u'6f', u'I', u'f'],'duration','radius','red','green','blue',
                  'unknown',(LighTypeFlags, u'flags'),'falloffExponent','fov',
                  'nearClip','fePeriod','feIntensityAmplitude',
                  'feMovementAmplitude','value','weight',),
        MelFloat(b'FNAM', u'fade'),
        MelFid(b'SNAM','sound'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLscr(MelRecord):
    """Load Screen."""
    rec_sig = b'LSCR'

    melSet = MelSet(
        MelEdid(),
        MelIcons(),
        MelDescription(),
        MelConditions(),
        MelFid(b'NNAM','loadingScreenNIF'),
        MelFloat(b'SNAM', 'initialScale'),
        MelStruct(b'RNAM', [u'3h'],'rotGridY','rotGridX','rotGridZ',),
        MelStruct(b'ONAM', [u'2h'],'rotOffsetMin','rotOffsetMax',),
        MelStruct(b'XNAM', [u'3f'],'transGridY','transGridX','transGridZ',),
        MelString(b'MOD2','cameraPath'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLtex(MelRecord):
    """Landscape Texture."""
    rec_sig = b'LTEX'

    _SnowFlags = Flags(0, Flags.getNames(
        'considered_snow',
    ))

    melSet = MelSet(
        MelEdid(),
        MelFid(b'TNAM','textureSet',),
        MelFid(b'MNAM','materialType',),
        MelStruct(b'HNAM', [u'2B'], 'friction', 'restitution',),
        MelUInt8(b'SNAM', 'textureSpecularExponent'),
        MelSorted(MelFids(b'GNAM', 'grasses')),
        sse_only(MelUInt32Flags(b'INAM', u'snow_flags', _SnowFlags))
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLeveledList(MreLeveledListBase):
    """Skyrim Leveled item/creature/spell list. Defines some common
    subrecords."""
    __slots__ = []

    class MelLlct(MelCounter):
        def __init__(self):
            MelCounter.__init__(
                self, MelUInt8(b'LLCT', u'entry_count'), counts=u'entries')

    class MelLvlo(MelSorted):
        def __init__(self, with_coed=True):
            lvl_elements = [
                MelStruct(b'LVLO', [u'2H', u'I', u'2H'], u'level', u'unknown1',
                          (FID, u'listId'), (u'count', 1), u'unknown2'),
            ]
            lvl_sort_attrs = ('level', 'listId', 'count')
            if with_coed:
                lvl_elements.append(MelCoed())
                lvl_sort_attrs += ('itemCondition', 'owner', 'glob')
            MelSorted.__init__(self, MelGroups(u'entries', *lvl_elements),
                               sort_by_attrs=lvl_sort_attrs)

#------------------------------------------------------------------------------
class MreLvli(MreLeveledList):
    """Leveled Item."""
    rec_sig = b'LVLI'
    top_copy_attrs = ('chanceNone','glob',)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8(b'LVLD', 'chanceNone'),
        MelUInt8Flags(b'LVLF', u'flags', MreLeveledListBase._flags),
        MelFid(b'LVLG', 'glob'),
        MreLeveledList.MelLlct(),
        MreLeveledList.MelLvlo(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLvln(MreLeveledList):
    """Leveled NPC."""
    rec_sig = b'LVLN'
    top_copy_attrs = ('chanceNone','model','modt_p',)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8(b'LVLD', 'chanceNone'),
        MelUInt8Flags(b'LVLF', u'flags', MreLeveledListBase._flags),
        MelFid(b'LVLG', 'glob'),
        MreLeveledList.MelLlct(),
        MreLeveledList.MelLvlo(),
        MelString(b'MODL','model'),
        MelBase(b'MODT','modt_p'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLvsp(MreLeveledList):
    """Leveled Spell."""
    rec_sig = b'LVSP'

    top_copy_attrs = ('chanceNone',)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8(b'LVLD', 'chanceNone'),
        MelUInt8Flags(b'LVLF', u'flags', MreLeveledListBase._flags),
        MreLeveledList.MelLlct(),
        MreLeveledList.MelLvlo(with_coed=False),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMato(MelRecord):
    """Material Object."""
    rec_sig = b'MATO'

    _MatoTypeFlags = Flags(0, Flags.getNames(
        'singlePass',
    ))
    _SnowFlags = Flags(0, Flags.getNames(
        'considered_snow',
    ))

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelGroups('property_data',
            MelBase(b'DNAM', 'data_entry'),
        ),
        if_sse(
            le_version=MelTruncatedStruct(
                b'DATA', [u'11f', u'I'], 'falloffScale', 'falloffBias', 'noiseUVScale',
                'materialUVScale', 'projectionVectorX', 'projectionVectorY',
                'projectionVectorZ', 'normalDampener', 'singlePassColorRed',
                'singlePassColorGreen', 'singlePassColorBlue',
                (_MatoTypeFlags, 'single_pass_flags'), old_versions={'7f'}),
            se_version=MelTruncatedStruct(
                b'DATA', [u'11f', u'I', u'B', u'3s'], 'falloffScale', 'falloffBias',
                'noiseUVScale', 'materialUVScale', 'projectionVectorX',
                'projectionVectorY', 'projectionVectorZ', 'normalDampener',
                'singlePassColorRed', 'singlePassColorGreen',
                'singlePassColorBlue', (_MatoTypeFlags, 'single_pass_flags'),
                (_SnowFlags, 'snow_flags'), 'unused1',
                old_versions={u'7f', u'11fI'}),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMatt(MelRecord):
    """Material Type."""
    rec_sig = b'MATT'

    MattTypeFlags = Flags(0, Flags.getNames(
            (0, 'stairMaterial'),
            (1, 'arrowsStick'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelFid(b'PNAM', 'materialParent',),
        MelString(b'MNAM','materialName'),
        MelStruct(b'CNAM', [u'3f'], 'red', 'green', 'blue'),
        MelFloat(b'BNAM', 'buoyancy'),
        MelUInt32Flags(b'FNAM', u'flags', MattTypeFlags),
        MelFid(b'HNAM', 'havokImpactDataSet',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMesg(MelRecord):
    """Message."""
    rec_sig = b'MESG'

    MesgTypeFlags = Flags(0, Flags.getNames(
            (0, 'messageBox'),
            (1, 'autoDisplay'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelDescription(),
        MelFull(),
        MelFid(b'INAM','iconUnused'), # leftover
        MelFid(b'QNAM','materialParent'),
        MelUInt32Flags(b'DNAM', u'flags', MesgTypeFlags),
        MelUInt32(b'TNAM', 'displayTime'),
        MelGroups('menuButtons',
            MelLString(b'ITXT','buttonText'),
            MelConditions(),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMgef(MelRecord):
    """Magic Effect."""
    rec_sig = b'MGEF'

    MgefGeneralFlags = Flags(0, Flags.getNames(
            ( 0, u'hostile'),
            ( 1, u'recover'),
            ( 2, u'detrimental'),
            ( 3, u'snaptoNavmesh'),
            ( 4, u'noHitEvent'),
            ( 8, u'dispellwithKeywords'),
            ( 9, u'noDuration'),
            (10, u'noMagnitude'),
            (11, u'noArea'),
            (12, u'fXPersist'),
            (14, u'goryVisuals'),
            (15, u'hideinUI'),
            (17, u'noRecast'),
            (21, u'powerAffectsMagnitude'),
            (22, u'powerAffectsDuration'),
            (26, u'painless'),
            (27, u'noHitEffect'),
            (28, u'noDeathDispel'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelFull(),
        MelMdob(),
        MelKeywords(),
        MelPartialCounter(MelStruct(b'DATA',
            [u'I', u'f', u'I', u'2i', u'H', u'2s', u'I', u'f', u'4I', u'4f',
             u'I', u'i', u'4I', u'i', u'3I', u'f', u'I', u'f', u'7I', u'2f'],
            (MgefGeneralFlags, u'flags'), u'base_cost',
            (FID, u'associated_item'), u'magic_skill', u'resist_value',
            u'counter_effect_count', u'unused1', (FID, u'light'),
            u'taper_weight', (FID, u'hit_shader'), (FID, u'enchant_shader'),
            u'minimum_skill_level', u'spellmaking_area',
            u'spellmaking_casting_time', u'taper_curve', u'taper_duration',
            u'second_av_weight', u'effect_archetype', u'actorValue',
            (FID, u'projectile'), (FID, u'explosion'), u'casting_type',
            u'delivery', u'second_av', (FID, u'casting_art'),
            (FID, u'hit_effect_art'), (FID, u'effect_impact_data'),
            u'skill_usage_multiplier', (FID, u'dual_casting_art'),
            u'dual_casting_scale', (FID, u'enchant_art'),
            (FID, u'hit_visuals'), (FID, u'enchant_visuals'),
            (FID, u'equip_ability'), (FID, u'effect_imad'),
            (FID, u'perk_to_apply'), u'casting_sound_level',
            u'script_effect_ai_score', u'script_effect_ai_delay_time'),
            counter=u'counter_effect_count', counts=u'counter_effects'),
        MelSorted(MelGroups(u'counter_effects',
            MelFid(b'ESCE', u'counter_effect_code'),
        ), sort_by_attrs='counter_effect_code'),
        MelArray(u'sounds',
            MelStruct(b'SNDD', [u'2I'], u'soundType', (FID, u'sound')),
        ),
        MelLString(b'DNAM', u'magic_item_description'),
        MelConditions(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMisc(MelRecord):
    """Misc. Item."""
    rec_sig = b'MISC'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelPickupSound(),
        MelDropSound(),
        MelKeywords(),
        MelStruct(b'DATA', [u'I', u'f'],'value','weight'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMovt(MelRecord):
    """Movement Type."""
    rec_sig = b'MOVT'

    melSet = MelSet(
        MelEdid(),
        MelString(b'MNAM','mnam_n'),
        MelTruncatedStruct(b'SPED', [u'11f'], 'leftWalk', 'leftRun', 'rightWalk',
                           'rightRun', 'forwardWalk', 'forwardRun', 'backWalk',
                           'backRun', 'rotateInPlaceWalk', 'rotateInPlaceRun',
                           'rotateWhileMovingRun', old_versions={'10f'}),
        MelOptStruct(b'INAM', [u'3f'],'directional','movementSpeed','rotationSpeed'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMstt(MelRecord):
    """Moveable Static."""
    rec_sig = b'MSTT'

    MsttTypeFlags = Flags(0, Flags.getNames(
        (0, 'onLocalMap'),
        (1, 'unknown2'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelUInt8Flags(b'DATA', u'flags', MsttTypeFlags),
        MelFid(b'SNAM','sound'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMusc(MelRecord):
    """Music Type."""
    rec_sig = b'MUSC'

    MuscTypeFlags = Flags(0, Flags.getNames(
            (0,'playsOneSelection'),
            (1,'abruptTransition'),
            (2,'cycleTracks'),
            (3,'maintainTrackOrder'),
            (4,'unknown5'),
            (5,'ducksCurrentTrack'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelUInt32Flags(b'FNAM', u'flags', MuscTypeFlags),
        # Divided by 100 in TES5Edit, probably for editing only
        MelStruct(b'PNAM', [u'2H'],'priority','duckingDB'),
        MelFloat(b'WNAM', 'fadeDuration'),
        MelFidList(b'TNAM','musicTracks'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMust(MelRecord):
    """Music Track."""
    rec_sig = b'MUST'

    melSet = MelSet(
        MelEdid(),
        MelUInt32(b'CNAM', 'trackType'),
        MelFloat(b'FLTV', 'duration'),
        MelUInt32(b'DNAM', 'fadeOut'),
        MelString(b'ANAM','trackFilename'),
        MelString(b'BNAM','finaleFilename'),
        MelArray('points',
            MelFloat(b'FNAM', u'cuePoints'),
        ),
        MelOptStruct(b'LNAM', [u'2f', u'I'],'loopBegins','loopEnds','loopCount',),
        MelConditionCounter(),
        MelConditions(),
        MelFidList(b'SNAM','tracks',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Not Mergable - FormIDs unaccounted for
class MreNavi(MelRecord):
    """Navigation Mesh Info Map."""
    rec_sig = b'NAVI'

    melSet = MelSet(
        MelEdid(),
        MelUInt32(b'NVER', 'version'),
        # NVMI and NVPP would need special routines to handle them
        # If no mitigation is needed, then leave it as MelBase
        MelBase(b'NVMI','navigationMapInfos',),
        MelBase(b'NVPP','preferredPathing',),
        MelFidList(b'NVSI','navigationMesh'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Not Mergable - FormIDs unaccounted for
class MreNavm(MelRecord):
    """Navigation Mesh."""
    rec_sig = b'NAVM'

    NavmTrianglesFlags = Flags(0, Flags.getNames(
            (0, 'edge01link'),
            (1, 'edge12link'),
            (2, 'edge20link'),
            (3, 'unknown4'),
            (4, 'unknown5'),
            (5, 'unknown6'),
            (6, 'preferred'),
            (7, 'unknown8'),
            (8, 'unknown9'),
            (9, 'water'),
            (10, 'door'),
            (11, 'found'),
            (12, 'unknown13'),
            (13, 'unknown14'),
            (14, 'unknown15'),
            (15, 'unknown16'),
        ))

    NavmCoverFlags = Flags(0, Flags.getNames(
            (0, 'edge01wall'),
            (1, 'edge01ledgecover'),
            (2, 'unknown3'),
            (3, 'unknown4'),
            (4, 'edge01left'),
            (5, 'edge01right'),
            (6, 'edge12wall'),
            (7, 'edge12ledgecover'),
            (8, 'unknown9'),
            (9, 'unknown10'),
            (10, 'edge12left'),
            (11, 'edge12right'),
            (12, 'unknown13'),
            (13, 'unknown14'),
            (14, 'unknown15'),
            (15, 'unknown16'),
        ))

    melSet = MelSet(
        MelEdid(),
        # NVNM, ONAM, PNAM, NNAM would need special routines to handle them
        # If no mitigation is needed, then leave it as MelBase
        MelBase(b'NVNM','navMeshGeometry'), # door triangles are sorted
        MelBase(b'ONAM','onam_p'),
        MelBase(b'PNAM','pnam_p'),
        MelBase(b'NNAM','nnam_p'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreNpc(MreActorBase):
    """Non-Player Character."""
    rec_sig = b'NPC_'

    _TemplateFlags = Flags(0, Flags.getNames(
            (0, 'useTraits'),
            (1, 'useStats'),
            (2, 'useFactions'),
            (3, 'useSpellList'),
            (4, 'useAIData'),
            (5, 'useAIPackages'),
            (6, 'useModelAnimation'),
            (7, 'useBaseData'),
            (8, 'useInventory'),
            (9, 'useScript'),
            (10, 'useDefPackList'),
            (11, 'useAttackData'),
            (12, 'useKeywords'),
        ))

    NpcFlags1 = Flags(0, Flags.getNames(
            (0, 'female'),
            (1, 'essential'),
            (2, 'isCharGenFacePreset'),
            (3, 'respawn'),
            (4, 'autoCalc'),
            (5, 'unique'),
            (6, 'doesNotAffectStealth'),
            (7, 'pcLevelMult'),
            (8, 'useTemplate'),
            (9, 'unknown9'),
            (10, 'unknown10'),
            (11, 'protected'),
            (12, 'unknown12'),
            (13, 'unknown13'),
            (14, 'summonable'),
            (15, 'unknown15'),
            (16, 'doesNotBleed'),
            (17, 'unknown17'),
            (18, 'bleedoutOverride'),
            (19, 'oppositeGenderAnims'),
            (20, 'simpleActor'),
            (21, 'loopedScript'),
            (22, 'unknown22'),
            (23, 'unknown23'),
            (24, 'unknown24'),
            (25, 'unknown25'),
            (26, 'unknown26'),
            (27, 'unknown27'),
            (28, 'loopedAudio'),
            (29, 'isGhost'),
            (30, 'unknown30'),
            (31, 'invulnerable'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelStruct(b'ACBS', [u'I', u'2H', u'h', u'3H', u'h', u'3H'],
                  (NpcFlags1, u'flags'),'magickaOffset',
                  'staminaOffset','level_offset','calcMin',
                  'calcMax','speedMultiplier','dispositionBase',
                  (_TemplateFlags, u'templateFlags'), 'healthOffset',
                  'bleedoutOverride',),
        MelFactions(),
        MelFid(b'INAM', 'deathItem'),
        MelFid(b'VTCK', 'voice'),
        MelFid(b'TPLT', 'template'),
        MelFid(b'RNAM','race'),
        MelSpellCounter(),
        MelSpells(),
        MelDestructible(),
        MelFid(b'WNAM', 'wornArmor'),
        MelFid(b'ANAM', 'farawaymodel'),
        MelFid(b'ATKR', 'attackRace'),
        MelAttacks(),
        MelFid(b'SPOR', 'spectator'),
        MelFid(b'OCOR', 'observe'),
        MelFid(b'GWOR', 'guardWarn'),
        MelFid(b'ECOR', 'combat'),
        MelCounter(MelUInt32(b'PRKZ', 'perk_count'), counts='perks'),
        MelSorted(MelGroups('perks',
            MelOptStruct(b'PRKR', [u'I', u'B', u'3s'],(FID, 'perk'),'rank','prkrUnused'),
        ), sort_by_attrs='perk'),
        MelItemsCounter(),
        MelItems(),
        MelStruct(b'AIDT', [u'B', u'B', u'B', u'B', u'B', u'B', u'B', u'B', u'I', u'I', u'I'], 'aggression', 'confidence',
                  'energyLevel', 'responsibility', 'mood', 'assistance',
                  'aggroRadiusBehavior',
                  'aidtUnknown', 'warn', 'warnAttack', 'attack'),
        MelFids(b'PKID', 'aiPackages',),
        MelKeywords(),
        MelFid(b'CNAM', 'iclass'),
        MelFull(),
        MelLString(b'SHRT', 'shortName'),
        MelBase(b'DATA', 'marker'),
        MelStruct(b'DNAM', [u'36B', u'H', u'H', u'H', u'2s', u'f', u'B', u'3s'],
            'oneHandedSV','twoHandedSV','marksmanSV','blockSV','smithingSV',
            'heavyArmorSV','lightArmorSV','pickpocketSV','lockpickingSV',
            'sneakSV','alchemySV','speechcraftSV','alterationSV','conjurationSV',
            'destructionSV','illusionSV','restorationSV','enchantingSV',
            'oneHandedSO','twoHandedSO','marksmanSO','blockSO','smithingSO',
            'heavyArmorSO','lightArmorSO','pickpocketSO','lockpickingSO',
            'sneakSO','alchemySO','speechcraftSO','alterationSO','conjurationSO',
            'destructionSO','illusionSO','restorationSO','enchantingSO',
            'health','magicka','stamina','dnamUnused1',
            'farawaymodeldistance','gearedupweapons','dnamUnused2'),
        MelSorted(MelFids(b'PNAM', 'head_part_addons')),
        MelFid(b'HCLF', u'hair_color'),
        MelFid(b'ZNAM', u'combatStyle'),
        MelFid(b'GNAM', u'gifts'),
        MelBase(b'NAM5', u'nam5_p'),
        MelFloat(b'NAM6', u'height'),
        MelFloat(b'NAM7', u'weight'),
        MelUInt32(b'NAM8', u'sound_level'),
        MelActorSounds(),
        MelFid(b'CSCR', u'audio_template'),
        MelFid(b'DOFT', u'default_outfit'),
        MelFid(b'SOFT', u'sleep_outfit'),
        MelFid(b'DPLT', u'default_package'),
        MelFid(b'CRIF', u'crime_faction'),
        MelFid(b'FTST', u'face_texture'),
        MelOptStruct(b'QNAM', [u'3f'], u'skin_tone_r', u'skin_tone_g',
            u'skin_tone_b'),
        MelOptStruct(b'NAM9', [u'19f'], u'nose_long', u'nose_up', u'jaw_up',
            u'jaw_wide', u'jaw_forward', u'cheeks_up', u'cheeks_back',
            u'eyes_up', u'eyes_out', u'brows_up', u'brows_out',
            u'brows_forward', u'lips_up', u'lips_out', u'chin_wide',
            u'chin_down', u'chin_underbite', u'eyes_back', u'nam9_unused'),
        MelOptStruct(b'NAMA', [u'I', u'i', u'2I'], u'nose', u'unknown', u'eyes', u'mouth'),
        MelSorted(MelGroups(u'face_tint_layer',
            MelUInt16(b'TINI', u'tint_item'),
            MelStruct(b'TINC', [u'4B'], u'tintRed', u'tintGreen', u'tintBlue',
                u'tintAlpha'),
            MelSInt32(b'TINV', u'tint_value'),
            MelSInt16(b'TIAS', u'preset'),
        ), sort_by_attrs='tint_item'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreOtft(MelRecord):
    """Outfit."""
    rec_sig = b'OTFT'

    melSet = MelSet(
        MelEdid(),
        MelSorted(MelFidList(b'INAM', 'items')),
    )
    __slots__ = melSet.getSlotsUsed()

    def mergeFilter(self, modSet):
        if not self.longFids: raise StateError(u'Fids not in long format')
        self.items = [i for i in self.items if i[0] in modSet]

#------------------------------------------------------------------------------
class MrePack(MelRecord):
    """Package."""
    rec_sig = b'PACK'

    _GeneralFlags = Flags(0, Flags.getNames(
        (0, 'offers_services'),
        (2, 'must_complete'),
        (3, 'maintain_speed_at_goal'),
        (6, 'unlock_doors_at_package_start'),
        (7, 'unlock_doors_at_package_end'),
        (9, 'continue_if_pc_near'),
        (10, 'once_per_day'),
        (13, 'preferred_speed'),
        (17, 'always_sneak'),
        (18, 'allow_swimming'),
        (20, 'ignore_combat'),
        (21, 'weapons_unequipped'),
        (23, 'weapon_drawn'),
        (27, 'no_combat_alert'),
        (29, 'wear_sleep_outfit'),
    ))
    _InterruptFlags = Flags(0, Flags.getNames(
        (0, 'hellos_to_player'),
        (1, 'random_conversations'),
        (2, 'observe_combat_behavior'),
        (3, 'greet_corpse_behavior'),
        (4, 'reaction_to_player_actions'),
        (5, 'friendly_fire_comments'),
        (6, 'aggro_radius_behavior'),
        (7, 'allow_idle_chatter'),
        (9, 'world_interactions'),
    ))
    _SubBranchFlags = Flags(0, Flags.getNames(
        (0, 'repeat_when_complete'),
    ))
    _BranchFlags = Flags(0, Flags.getNames(
        (0, 'success_completes_package'),
    ))

    class MelDataInputs(MelGroups):
        """Occurs twice in PACK, so moved here to deduplicate the
        definition a bit."""
        _DataInputFlags = Flags(0, Flags.getNames(
            (0, 'public'),
        ))

        def __init__(self, attr):
            MelGroups.__init__(self, attr,
                MelSInt8(b'UNAM', 'input_index'),
                MelString(b'BNAM', 'input_name'),
                MelUInt32Flags(b'PNAM', u'input_flags', self._DataInputFlags),
            ),

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelStruct(b'PKDT', [u'I', u'3B', u's', u'H', u'2s'], (_GeneralFlags, u'generalFlags'),
                  'package_type', 'interruptOverride', 'preferredSpeed',
                  'unknown1', (_InterruptFlags, u'interruptFlags'),
                  'unknown2'),
        MelStruct(b'PSDT', [u'2b', u'B', u'2b', u'3s', u'i'], 'schedule_month', 'schedule_day',
                  'schedule_date', 'schedule_hour', 'schedule_minute',
                  'unused1', 'schedule_duration'),
        MelConditions(),
        MelGroup('idleAnimations',
            MelUInt8(b'IDLF', u'animation_flags'),
            MelPartialCounter(MelStruct(b'IDLC', [u'B', u'3s'], 'animation_count',
                                        'unknown'),
                              counter='animation_count', counts='animations'),
            MelFloat(b'IDLT', 'idleTimerSetting',),
            MelFidList(b'IDLA', 'animations'),
            MelBase(b'IDLB', 'unknown1'),
        ),
        MelFid(b'CNAM', 'combatStyle',),
        MelFid(b'QNAM', 'owner_quest'),
        MelStruct(b'PKCU', [u'3I'], 'dataInputCount', (FID, 'packageTemplate'),
                  'versionCount'),
        MelGroups('data_input_values',
            MelString(b'ANAM', 'value_type'),
            MelUnion({
                u'Bool': MelUInt8(b'CNAM', u'value_val'),
                u'Int': MelUInt32(b'CNAM', u'value_val'),
                u'Float': MelFloat(b'CNAM', u'value_val'),
                # Mirrors what xEdit does, despite how weird it looks
                u'ObjectList': MelFloat(b'CNAM', u'value_val'),
            }, decider=AttrValDecider(u'value_type'),
                # All other kinds of values, typically missing
                fallback=MelBase(b'CNAM', u'value_val')),
            MelBase(b'BNAM', 'unknown1'),
            MelTopicData('value_topic_data'),
            MelLocation(b'PLDT'),
            MelUnion({
                (0, 1, 3): MelOptStruct(b'PTDA', [u'i', u'I', u'i'], u'target_type',
                    (FID, u'target_value'), u'target_count'),
                2: MelOptStruct(b'PTDA', [u'i', u'I', u'i'], u'target_type',
                    u'target_value', u'target_count'),
                4: MelOptStruct(b'PTDA', [u'3i'], u'target_type',
                    u'target_value', u'target_count'),
                (5, 6): MelOptStruct(b'PTDA', [u'i', u'4s', u'i'], u'target_type',
                    u'target_value', u'target_count'),
            }, decider=PartialLoadDecider(
                loader=MelSInt32(b'PTDA', u'target_type'),
                decider=AttrValDecider(u'target_type'))),
            MelBase(b'TPIC', 'unknown2'),
        ),
        MelDataInputs('data_inputs1'),
        MelBase(b'XNAM', 'marker'),
        MelGroups('procedure_tree_branches',
            MelString(b'ANAM', 'branch_type'),
            MelConditionCounter(),
            MelConditions(),
            MelOptStruct(b'PRCB', [u'2I'], 'sub_branch_count',
                         (_SubBranchFlags, u'sub_branch_flags')),
            MelString(b'PNAM', 'procedure_type'),
            MelUInt32Flags(b'FNAM', u'branch_flags', _BranchFlags),
            MelGroups('data_input_indices',
                MelUInt8(b'PKC2', 'input_index'),
            ),
            MelGroups('flag_overrides',
                MelStruct(b'PFO2', [u'2I', u'2H', u'B', u'3s'],
                          (_GeneralFlags, u'set_general_flags'),
                          (_GeneralFlags, u'clear_general_flags'),
                          (_InterruptFlags, u'set_interrupt_flags'),
                          (_InterruptFlags, u'clear_interrupt_flags'),
                          'preferred_speed_override', 'unknown1'),
            ),
            MelGroups('unknown1',
                MelBase(b'PFOR', 'unknown1'),
            ),
        ),
        MelDataInputs('data_inputs2'),
        MelIdleHandler(u'on_begin'),
        MelIdleHandler(u'on_end'),
        MelIdleHandler(u'on_change'),
    ).with_distributor({
        b'PKDT': {
            b'CTDA|CIS1|CIS2': u'conditions',
            b'CNAM': u'combatStyle',
            b'QNAM': u'owner_quest',
            b'ANAM': (u'data_input_values', {
                b'BNAM|CNAM|PDTO': u'data_input_values',
            }),
            b'UNAM': (u'data_inputs1', {
                b'BNAM|PNAM': u'data_inputs1',
            }),
        },
        b'XNAM': {
            b'ANAM|CTDA|CIS1|CIS2|PNAM': u'procedure_tree_branches',
            b'UNAM': (u'data_inputs2', {
                b'BNAM|PNAM': u'data_inputs2',
            }),
        },
        b'POBA': {
            b'INAM|SCHR|SCTX|QNAM|TNAM|PDTO': u'on_begin',
        },
        b'POEA': {
            b'INAM|SCHR|SCTX|QNAM|TNAM|PDTO': u'on_end',
        },
        b'POCA': {
            b'INAM|SCHR|SCTX|QNAM|TNAM|PDTO': u'on_change',
        },
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MrePerk(MelRecord):
    """Perk."""
    rec_sig = b'PERK'

    _PerkScriptFlags = Flags(0, Flags.getNames(
        (0, 'runImmediately'),
        (1, 'replaceDefault'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelFull(),
        MelDescription(),
        MelIcons(),
        MelConditions(),
        MelTruncatedStruct(b'DATA', [u'5B'], 'trait', 'minLevel',
                           'ranks', 'playable', 'hidden',
                           old_versions={'4B'}),
        MelFid(b'NNAM', 'next_perk'),
        MelSorted(MelGroups('effects',
            MelStruct(b'PRKE', [u'3B'], 'type', 'rank', 'priority'),
            MelUnion({
                0: MelStruct(b'DATA', [u'I', u'B', u'3s'], (FID, u'quest'), u'quest_stage',
                             u'unused_data'),
                1: MelFid(b'DATA', u'ability'),
                2: MelStruct(b'DATA', [u'3B'], u'entry_point', u'function',
                             u'perk_conditions_tab_count'),
            }, decider=AttrValDecider(u'type')),
            MelSorted(MelGroups('effectConditions',
                MelSInt8(b'PRKC', 'runOn'),
                MelConditions(),
            ), sort_by_attrs='runOn'),
            MelGroups('effectParams',
                MelUInt8(b'EPFT', 'function_parameter_type'),
                MelLString(b'EPF2','buttonLabel'),
                MelStruct(b'EPF3', [u'2H'],(_PerkScriptFlags, u'script_flags'),
                          'fragment_index'),
                # EPFT has the following meanings:
                #  0: Unknown
                #  1: EPFD=float
                #  2: EPFD=float, float
                #  3: EPFD=fid (LVLI)
                #  4: EPFD=fid (SPEL), EPF2=string, EPF3=uint16 (flags)
                #  5: EPFD=fid (SPEL)
                #  6: EPFD=string
                #  7: EPFD=lstring
                # TODO(inf) there is a special case: If EPFT is 2 and
                #  DATA/function is one of 5, 12, 13 or 14, then:
                #  EPFD=uint32, float
                #  See commented out skeleton below - needs '../' syntax
                MelUnion({
                    0: MelBase(b'EPFD', u'param1'),
                    1: MelFloat(b'EPFD', u'param1'),
                    2: MelStruct(b'EPFD', [u'I', u'f'], u'param1', u'param2'),
                    # 2: MelUnion({
                    #     (5, 12, 13, 14): MelStruct(b'EPFD', [u'I', u'f'], u'param1',
                    #        u'param2'),
                    # }, decider=AttrValDecider(u'../function',
                    #    assign_missing=-1),
                    #    fallback=MelStruct(b'EPFD', [u'2f'], u'param1',
                    #        u'param2')),
                    (3, 4, 5): MelFid(b'EPFD', u'param1'),
                    6: MelString(b'EPFD', u'param1'),
                    7: MelLString(b'EPFD', u'param1'),
                }, decider=AttrValDecider(u'function_parameter_type')),
            ),
            MelBase(b'PRKF','footer'),
        ), sort_special=perk_effect_key),
    ).with_distributor({
        b'DESC': {
            b'CTDA|CIS1|CIS2': u'conditions',
            b'DATA': u'trait',
        },
        b'PRKE': {
            b'CTDA|CIS1|CIS2|DATA': u'effects',
        },
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreProj(MelRecord):
    """Projectile."""
    rec_sig = b'PROJ'

    ProjTypeFlags = Flags(0, Flags.getNames(
        (0, 'is_hitscan'),
        (1, 'is_explosive'),
        (2, 'alt_trigger'),
        (3, 'has_muzzle_flash'),
        (5, 'can_be_disabled'),
        (6, 'can_be_picked_up'),
        (7, 'is_super_sonic'),
        (8, 'pins_limbs'),
        (9, 'pass_through_small_transparent'),
        (10, 'disable_combat_aim_correction'),
        (11, 'projectile_rotates'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelTruncatedStruct(b'DATA',
            [u'2H', u'3f', u'2I', u'3f', u'2I', u'3f', u'3I', u'4f', u'2I'],
            (ProjTypeFlags, u'flags'),
            'projectileTypes', 'gravity', ('speed', 10000.0),
            ('range', 10000.0), (FID, u'light'), (FID, u'muzzleFlash'),
            'tracerChance', 'explosionAltTrigerProximity',
            'explosionAltTrigerTimer', (FID, u'explosion'),
            (FID, u'sound'), 'muzzleFlashDuration',
            'fadeDuration', 'impactForce',
            (FID, u'soundCountDown'), (FID, u'soundDisable'),
            (FID, u'defaultWeaponSource'), 'coneSpread',
            'collisionRadius', 'lifetime',
            'relaunchInterval', (FID, u'decalData'),
            (FID, u'collisionLayer'), old_versions={'2H3f2I3f2I3f3I4fI',
                                                    '2H3f2I3f2I3f3I4f'}),
        MelGroup('models',
            MelString(b'NAM1','muzzleFlashPath'),
            # Ignore texture hashes - they're only an optimization, plenty of
            # records in Skyrim.esm are missing them
            MelNull(b'NAM2'),
        ),
        MelUInt32(b'VNAM', 'soundLevel',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Needs testing should be mergable
class MreQust(MelRecord):
    """Quest."""
    rec_sig = b'QUST'

    _questFlags = Flags(0,Flags.getNames(
        (0,  u'startGameEnabled'),
        (1,  u'completed'),
        (2,  u'add_idle_topic_to_hello'),
        (3,  u'allowRepeatedStages'),
        (4,  u'starts_enabled'),
        (5,  u'displayed_in_hud'),
        (6,  u'failed'),
        (7,  u'stage_wait'),
        (8,  u'runOnce'),
        (9,  u'excludeFromDialogueExport'),
        (10, u'warnOnAliasFillFailure'),
        (11, u'active'),
        (12, u'repeats_conditions'),
        (13, u'keep_instance'),
        (14, u'want_dormat'),
        (15, u'has_dialogue_data'),
    ))
    _stageFlags = Flags(0,Flags.getNames(
        (0,'unknown0'),
        (1,'startUpStage'),
        (2,'startDownStage'),
        (3,'keepInstanceDataFromHereOn'),
    ))
    stageEntryFlags = Flags(0,Flags.getNames('complete','fail'))
    objectiveFlags = Flags(0,Flags.getNames('oredWithPrevious'))
    targetFlags = Flags(0,Flags.getNames('ignoresLocks'))
    aliasFlags = Flags(0,Flags.getNames(
        (0,'reservesLocationReference'),
        (1,'optional'),
        (2,'questObject'),
        (3,'allowReuseInQuest'),
        (4,'allowDead'),
        (5,'inLoadedArea'),
        (6,'essential'),
        (7,'allowDisabled'),
        (8,'storesText'),
        (9,'allowReserved'),
        (10,'protected'),
        (11,'noFillType'),
        (12,'allowDestroyed'),
        (13,'closest'),
        (14,'usesStoredText'),
        (15,'initiallyDisabled'),
        (16,'allowCleared'),
        (17,'clearsNameWhenRemoved'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelFull(),
        MelStruct(b'DNAM', [u'H', u'2B', u'4s', u'I'], (_questFlags, u'questFlags'),
                  'priority', 'formVersion', 'unknown', 'questType'),
        MelOptStruct(b'ENAM', [u'4s'], u'event_name'),
        MelFids(b'QTGL','textDisplayGlobals'),
        MelString(b'FLTR','objectWindowFilter'),
        MelConditions('dialogueConditions'),
        MelBase(b'NEXT','marker'),
        MelConditions('eventConditions'),
        MelSorted(MelGroups('stages',
            MelStruct(b'INDX', [u'H', u'2B'],'index',(_stageFlags, u'flags'),'unknown'),
            MelGroups('logEntries',
                MelUInt8Flags(b'QSDT', u'stageFlags', stageEntryFlags),
                MelConditions(),
                MelLString(b'CNAM','log_text'),
                MelFid(b'NAM0', 'nextQuest'),
                MelBase(b'SCHR', 'unusedSCHR'),
                MelBase(b'SCTX', 'unusedSCTX'),
                MelBase(b'QNAM', 'unusedQNAM'),
            ),
        ), sort_by_attrs='index'),
        MelGroups('objectives',
            MelUInt16(b'QOBJ', 'index'),
            MelUInt32Flags(b'FNAM', u'flags', objectiveFlags),
            MelLString(b'NNAM','description'),
            MelGroups('targets',
                MelStruct(b'QSTA', [u'i', u'B', u'3s'],'alias',(targetFlags,'flags'),'unused1'),
                MelConditions(),
            ),
        ),
        MelBase(b'ANAM','aliasMarker'),
        MelGroups(u'qust_aliases',
            MelUnion({
                b'ALST': MelUInt32(b'ALST', u'aliasId'),
                b'ALLS': MelUInt32(b'ALLS', u'aliasId'),
            }),
            MelString(b'ALID', 'aliasName'),
            MelUInt32Flags(b'FNAM', u'flags', aliasFlags),
            MelSInt32(b'ALFI', u'forcedIntoAlias'), # alias ID
            MelFid(b'ALFL','specificLocation'),
            MelFid(b'ALFR','forcedReference'),
            MelFid(b'ALUA','uniqueActor'),
            MelGroup('locationAliasReference',
                MelSInt32(b'ALFA', 'alias'),
                MelFid(b'KNAM','keyword'),
                MelFid(b'ALRT','referenceType'),
            ),
            MelGroup('externalAliasReference',
                MelFid(b'ALEQ','quest'),
                MelSInt32(b'ALEA', 'alias'),
            ),
            MelGroup('createReferenceToObject',
                MelFid(b'ALCO','object'),
                MelStruct(b'ALCA', [u'h', u'H'], 'alias', 'create_target'),
                MelUInt32(b'ALCL', 'createLevel'),
            ),
            MelGroup('findMatchingReferenceNearAlias',
                MelSInt32(b'ALNA', 'alias'),
                MelUInt32(b'ALNT', 'type'),
            ),
            MelGroup('findMatchingReferenceFromEvent',
                MelStruct(b'ALFE', [u'4s'],'fromEvent'),
                MelStruct(b'ALFD', [u'4s'],'eventData'),
            ),
            MelConditions(),
            MelKeywords(),
            MelItemsCounter(),
            MelItems(),
            MelFid(b'SPOR','spectatorOverridePackageList'),
            MelFid(b'OCOR','observeDeadBodyOverridePackageList'),
            MelFid(b'GWOR','guardWarnOverridePackageList'),
            MelFid(b'ECOR','combatOverridePackageList'),
            MelFid(b'ALDN','displayName'),
            MelFids(b'ALSP','aliasSpells'),
            MelFids(b'ALFC','aliasFactions'),
            MelFids(b'ALPC','aliasPackageData'),
            MelFid(b'VTCK','voiceType'),
            MelBase(b'ALED','aliasEnd'),
        ),
        MelLString(b'NNAM','description'),
        MelGroups('targets',
            MelStruct(b'QSTA', [u'I', u'B', u'3s'], (FID, 'target'), (targetFlags, 'flags'),
                      'unknown1'),
            MelConditions(),
        ),
    ).with_distributor({
        b'DNAM': {
            b'CTDA|CIS1|CIS2': u'dialogueConditions',
        },
        b'NEXT': {
            b'CTDA|CIS1|CIS2': u'eventConditions',
        },
        b'INDX': {
            b'CTDA|CIS1|CIS2': u'stages',
        },
        b'QOBJ': {
            b'CTDA|CIS1|CIS2|FNAM|NNAM|QSTA': u'objectives',
        },
        b'ANAM': {
            b'CTDA|CIS1|CIS2|FNAM': u'qust_aliases',
            # ANAM is required, so piggyback off of it here to resolve QSTA
            b'QSTA': (u'targets', {
                b'CTDA|CIS1|CIS2': u'targets',
            }),
            b'NNAM': u'description',
        },
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class _MelTintMasks(MelGroups):
    """Hacky way to allow a MelGroups of two MelGroups."""
    def __init__(self, attr):
        super(_MelTintMasks, self).__init__(attr,
            MelGroups(u'tint_textures',
                MelUInt16(b'TINI', u'tint_index'),
                MelString(b'TINT', u'tint_file'),
                MelUInt16(b'TINP', u'tint_mask_type'),
                MelFid(b'TIND', u'tint_preset_default'),
            ),
            MelGroups(u'tint_presets',
                MelFid(b'TINC', u'preset_color'),
                MelFloat(b'TINV', u'preset_default'),
                MelUInt16(b'TIRS', u'preset_index'),
            ),
        )
        self._init_sigs = {b'TINI'}

class _RaceDataFlags1(Flags):
    """The Overlay/Override Head Part List flags are mutually exclusive."""
    def _clean_unused_flags(self):
        if self.overlay_head_part_list and self.override_head_part_list:
            self.overlay_head_part_list = False
        super(_RaceDataFlags1, self)._clean_unused_flags()

class MreRace(MelRecord):
    """Race."""
    rec_sig = b'RACE'

    _data_flags_1 = _RaceDataFlags1(0, Flags.getNames(
        u'playable', u'facegen_head', u'child', u'tilt_front_back',
        u'tilt_left_right', u'no_shadow', u'swims', u'flies', u'walks',
        u'immobile', u'not_pushable', u'no_combat_in_water',
        u'no_rotating_to_head_track', u'dont_show_blood_spray',
        u'dont_show_blood_decal', u'uses_head_track_anim',
        u'spells_align_with_magic_mode', u'use_world_raycasts_for_footik',
        u'allow_ragdoll_collisions', u'regen_hp_in_combat', u'cant_open_doors',
        u'allow_pc_dialogue', u'no_knockdowns', u'allow_pickpocket',
        u'always_use_proxy_controller', u'dont_show_weapon_blood',
        u'overlay_head_part_list', u'override_head_part_list',
        u'can_pickup_items', u'allow_multiple_membrane_shaders',
        u'can_dual_wield', u'avoids_roads',
    ))
    _data_flags_2 = Flags(0, Flags.getNames(
        (0, u'use_advanced_avoidance'),
        (1, u'non_hostile'),
        (4, u'allow_mounted_combat'),
    ))
    _equip_type_flags = Flags(0, Flags.getNames(
        u'et_hand_to_hand_melee', u'et_one_hand_sword', u'et_one_hand_dagger',
        u'et_one_hand_axe', u'et_one_hand_mace', u'et_two_hand_sword',
        u'et_two_hand_axe', u'et_bow', u'et_staff', u'et_spell', u'et_shield',
        u'et_torch', u'et_crossbow',
    ), unknown_is_unused=True)

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(), # required
        MelSpellCounter(),
        MelSpells(),
        MelFid(b'WNAM', u'race_skin'),
        MelBipedObjectData(), # required
        MelKeywords(),
        MelRaceData(b'DATA', # required
            [u'14b', u'2s', u'4f', u'I', u'7f', u'I', u'2i', u'f', u'i', u'5f',
             u'i', u'4f', u'I', u'9f'], u'skills', u'unknown1',
            u'maleHeight', u'femaleHeight', u'maleWeight', u'femaleWeight',
            (_data_flags_1, u'data_flags_1'), u'starting_health',
            u'starting_magicka', u'starting_stamina', u'base_carry_weight',
            u'base_mass', u'acceleration_rate', u'deceleration_rate',
            u'race_size', u'head_biped_object', u'hair_biped_object',
            u'injured_health_percentage', u'shield_biped_object',
            u'health_regen', u'magicka_regen', u'stamina_regen',
            u'unarmed_damage', u'unarmed_reach', u'body_biped_object',
            u'aim_angle_tolerance', u'flight_radius',
            u'angular_acceleration_tolerance', u'angular_tolerance',
            (_data_flags_2, u'data_flags_2'), (u'mount_offset_x', -63.479000),
            u'mount_offset_y', u'mount_offset_z',
            (u'dismount_offset_x', -50.0), u'dismount_offset_y',
            (u'dismount_offset_z', 65.0), u'mount_camera_offset_x',
            (u'mount_camera_offset_y', -300.0), u'mount_camera_offset_z',
            old_versions={u'14b2s4fI7fI2ifi5fi4fI'}),
        MelBase(b'MNAM', u'male_marker', b''), # required
        MelString(b'ANAM', u'male_skeletal_model'),
        # Texture hash - we have to give it a name for the distributor
        MelReadOnly(MelBase(b'MODT', u'male_hash')),
        MelBase(b'FNAM', u'female_marker', b''), # required
        MelString(b'ANAM', u'female_skeletal_model'),
        # Texture hash - we have to give it a name for the distributor
        MelReadOnly(MelBase(b'MODT', u'female_hash')),
        MelBase(b'NAM2', u'marker_nam2_1'),
        MelSorted(MelGroups(u'movement_type_names',
            MelString(b'MTNM', u'mt_name'),
        ), sort_by_attrs='mt_name'),
        # required
        MelStruct(b'VTCK', [u'2I'], (FID, u'maleVoice'), (FID, u'femaleVoice')),
        MelOptStruct(b'DNAM', [u'2I'], (FID, u'male_decapitate_armor'),
                     (FID, u'female_decapitate_armor')),
        MelOptStruct(b'HCLF', [u'2I'], (FID, u'male_default_hair_color'),
                     (FID, u'female_default_hair_color')),
        ##: Needs to be updated for total tint count, but not even xEdit can do
        # that right now
        MelUInt16(b'TINL', u'tint_count'),
        MelFloat(b'PNAM', u'facegen_main_clamp'), # required
        MelFloat(b'UNAM', u'facegen_face_clamp'), # required
        MelFid(b'ATKR', u'attack_race'),
        MelAttacks(),
        MelBase(b'NAM1', u'body_data_marker', b''), # required
        MelBase(b'MNAM', u'male_data_marker', b''), # required
        MelSorted(MelGroups(u'male_body_data',
            MelUInt32(b'INDX', u'body_part_index'), # required
            MelModel(),
        ), sort_by_attrs='body_part_index'),
        MelBase(b'FNAM', u'female_data_marker', b''), # required
        MelSorted(MelGroups(u'female_body_data',
            MelUInt32(b'INDX', u'body_part_index'), # required
            MelModel(),
        ), sort_by_attrs='body_part_index'),
        # These seem like unused leftovers from TES4/FO3, never occur in
        # vanilla or in any of the ~400 mod plugins I checked
        MelSorted(MelFidList(b'HNAM', u'hairs')),
        MelSorted(MelFidList(b'ENAM', u'eyes')),
        MelFid(b'GNAM', u'body_part_data'), # required
        MelBase(b'NAM2', u'marker_nam2_2'),
        MelBase(b'NAM3', u'behavior_graph_marker', b''), # required
        MelBase(b'MNAM', u'male_graph_marker', b''), # required
        MelModel(u'male_behavior_graph'),
        MelBase(b'FNAM', u'female_graph_marker', b''), # required
        MelModel(u'female_behavior_graph'),
        MelFid(b'NAM4', u'material_type'),
        MelFid(b'NAM5', u'impact_data_set'),
        MelFid(b'NAM7', u'decapitation_fx'),
        MelFid(b'ONAM', u'open_loot_sound'),
        MelFid(b'LNAM', u'close_loot_sound'),
        MelGroups(u'biped_object_names', ##: required, len should always be 32!
            MelString(b'NAME', u'bo_name'),
        ),
        MelSorted(MelGroups(u'movement_types',
            MelFid(b'MTYP', u'movement_type'),
            MelOptStruct(b'SPED', [u'11f'], u'override_left_walk',
                         u'override_left_run', u'override_right_walk',
                         u'override_right_run', u'override_forward_walk',
                         u'override_forward_run', u'override_back_walk',
                         u'override_back_run', u'override_rotate_walk',
                         u'override_rotate_run', u'unknown1'),
        ), sort_by_attrs='movement_type'),
        MelUInt32Flags(b'VNAM', u'equip_type_flags', _equip_type_flags),
        MelSorted(MelGroups(u'equip_slots',
            MelFid(b'QNAM', u'equip_slot'),
        ), sort_by_attrs='equip_slot'),
        MelFid(b'UNES', u'unarmed_equip_slot'),
        MelGroups(u'phoneme_target_names',
            MelString(b'PHTN', u'pt_name'),
        ),
        MelGroups(u'facefx_phonemes',
            MelTruncatedStruct(
                b'PHWT', [u'16f'], u'aah_lipbigaah_weight',
                u'bigaah_lipdst_weight', u'bmp_lipeee_weight',
                u'chjsh_lipfv_weight', u'dst_lipk_weight', u'eee_lipl_weight',
                u'eh_lipr_weight', u'fv_lipth_weight', u'i_weight',
                u'k_weight', u'n_weight', u'oh_weight', u'oohq_weight',
                u'r_weight', u'th_weight', u'w_weight', old_versions={u'8f'}),
        ),
        MelFid(b'WKMV', u'base_movement_default_walk'),
        MelFid(b'RNMV', u'base_movement_default_run'),
        MelFid(b'SWMV', u'base_movement_default_swim'),
        MelFid(b'FLMV', u'base_movement_default_fly'),
        MelFid(b'SNMV', u'base_movement_default_sneak'),
        MelFid(b'SPMV', u'base_movement_default_sprint'),
        MelBase(b'NAM0', u'male_head_data_marker'),
        MelBase(b'MNAM', u'male_head_parts_marker'),
        MelSorted(MelGroups(u'male_head_parts',
            MelUInt32(b'INDX', u'head_part_number'),
            MelFid(b'HEAD', u'head_part'),
        ), sort_by_attrs='head_part_number'),
        # The MPAVs are semi-decoded in xEdit, but including them seems wholly
        # unnecessary (too complex to edit, tons of flags, many unknowns)
        MelBase(b'MPAI', u'male_morph_unknown1'),
        MelBase(b'MPAV', u'male_nose_variants'),
        MelBase(b'MPAI', u'male_morph_unknown2'),
        MelBase(b'MPAV', u'male_brow_variants'),
        MelBase(b'MPAI', u'male_morph_unknown3'),
        MelBase(b'MPAV', u'male_eye_variants'),
        MelBase(b'MPAI', u'male_morph_unknown4'),
        MelBase(b'MPAV', u'male_lip_variants'),
        MelSorted(MelGroups(u'male_race_presets',
            MelFid(b'RPRM', u'preset_npc'),
        ), sort_by_attrs='preset_npc'),
        MelSorted(MelGroups(u'male_available_hair_colors',
            MelFid(b'AHCM', u'hair_color'),
        ), sort_by_attrs='hair_color'),
        MelSorted(MelGroups(u'male_face_texture_sets',
            MelFid(b'FTSM', u'face_texture_set'),
        ), sort_by_attrs='face_texture_set'),
        MelFid(b'DFTM', u'male_default_face_texture'),
        _MelTintMasks(u'male_tint_masks'),
        MelModel(u'male_head_model'),
        MelBase(b'NAM0', u'female_head_data_marker'),
        MelBase(b'FNAM', u'female_head_parts_marker'),
        MelSorted(MelGroups(u'female_head_parts',
            MelUInt32(b'INDX', u'head_part_number'),
            MelFid(b'HEAD', u'head_part'),
        ), sort_by_attrs='head_part_number'),
        # The MPAVs are semi-decoded in xEdit, but including them seems wholly
        # unnecessary (too complex to edit, tons of flags, many unknowns)
        MelBase(b'MPAI', u'female_morph_unknown1'),
        MelBase(b'MPAV', u'female_nose_variants'),
        MelBase(b'MPAI', u'female_morph_unknown2'),
        MelBase(b'MPAV', u'female_brow_variants'),
        MelBase(b'MPAI', u'female_morph_unknown3'),
        MelBase(b'MPAV', u'female_eye_variants'),
        MelBase(b'MPAI', u'female_morph_unknown4'),
        MelBase(b'MPAV', u'female_lip_variants'),
        MelSorted(MelGroups(u'female_race_presets',
            MelFid(b'RPRF', u'preset_npc'),
        ), sort_by_attrs='preset_npc'),
        MelSorted(MelGroups(u'female_available_hair_colors',
            MelFid(b'AHCF', u'hair_color'),
        ), sort_by_attrs='hair_color'),
        MelSorted(MelGroups(u'female_face_texture_sets',
            MelFid(b'FTSF', u'face_texture_set'),
        ), sort_by_attrs='face_texture_set'),
        MelFid(b'DFTF', u'female_default_face_texture'),
        _MelTintMasks(u'female_tint_masks'),
        MelModel(u'female_head_model'),
        MelFid(b'NAM8', u'morph_race'),
        MelFid(b'RNAM', u'armor_race'),
    ).with_distributor({
        b'DATA': {
            b'MNAM': (u'male_marker', {
                b'ANAM': u'male_skeletal_model',
                b'MODT': u'male_hash',
            }),
            b'FNAM': (u'female_marker', {
                b'ANAM': u'female_skeletal_model',
                b'MODT': u'female_hash',
            }),
            b'NAM2': u'marker_nam2_1',
        },
        b'NAM1': {
            b'MNAM': (u'male_data_marker', {
                b'INDX|MODL|MODT|MODS': u'male_body_data',
            }),
            b'FNAM': (u'female_data_marker', {
                b'INDX|MODL|MODT|MODS': u'female_body_data',
            }),
            b'NAM2': u'marker_nam2_2',
        },
        b'NAM3': {
            b'MNAM': (u'male_graph_marker', {
                b'MODL|MODT|MODS': u'male_behavior_graph',
            }),
            b'FNAM': (u'female_graph_marker', {
                b'MODL|MODT|MODS': u'female_behavior_graph',
            }),
        },
        b'NAM0': (u'male_head_data_marker', {
            b'MNAM': (u'male_head_parts_marker', {
                b'INDX|HEAD': u'male_head_parts',
                b'MPAI': [
                    (b'MPAI', u'male_morph_unknown1'),
                    (b'MPAV', u'male_nose_variants'),
                    (b'MPAI', u'male_morph_unknown2'),
                    (b'MPAV', u'male_brow_variants'),
                    (b'MPAI', u'male_morph_unknown3'),
                    (b'MPAV', u'male_eye_variants'),
                    (b'MPAI', u'male_morph_unknown4'),
                    (b'MPAV', u'male_lip_variants'),
                ],
                b'TINI|TINT|TINP|TIND|TINC|TINV|TIRS': u'male_tint_masks',
                b'MODL|MODT|MODS': u'male_head_model',
            }),
            # For some ungodly reason Bethesda inserted another NAM0 after the
            # male section. So we have to make a hierarchy where the second
            # NAM0 sits inside the dict of the first NAM0.
            b'NAM0': (u'female_head_data_marker', {
                b'FNAM': (u'female_head_parts_marker', {
                    b'INDX|HEAD': u'female_head_parts',
                    b'MPAI': [
                        (b'MPAI', u'female_morph_unknown1'),
                        (b'MPAV', u'female_nose_variants'),
                        (b'MPAI', u'female_morph_unknown2'),
                        (b'MPAV', u'female_brow_variants'),
                        (b'MPAI', u'female_morph_unknown3'),
                        (b'MPAV', u'female_eye_variants'),
                        (b'MPAI', u'female_morph_unknown4'),
                        (b'MPAV', u'female_lip_variants'),
                    ],
                    b'TINI|TINT|TINP|TIND|TINC|TINV|TIRS':
                        u'female_tint_masks',
                    b'MODL|MODT|MODS': u'female_head_model',
                }),
            }),
        }),
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Needs Updating
class MreRefr(MelRecord):
    """Placed Object."""
    rec_sig = b'REFR'

    _lockFlags = Flags(0, Flags.getNames(None, None, 'leveledLock'))
    _destinationFlags = Flags(0, Flags.getNames('noAlarm'))
    _parentActivate = Flags(0, Flags.getNames('parentActivateOnly'))
    reflectFlags = Flags(0, Flags.getNames('reflection', 'refraction'))
    roomDataFlags = Flags(0, Flags.getNames(
        (6,'hasImageSpace'),
        (7,'hasLightingTemplate'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelFid(b'NAME','base'),
        MelOptStruct(b'XMBO', [u'3f'],'boundHalfExtentsX','boundHalfExtentsY','boundHalfExtentsZ'),
        MelOptStruct(b'XPRM', [u'f', u'f', u'f', u'f', u'f', u'f', u'f', u'I'],'primitiveBoundX','primitiveBoundY','primitiveBoundZ',
                     'primitiveColorRed','primitiveColorGreen','primitiveColorBlue',
                     'primitiveUnknown','primitiveType'),
        MelBase(b'XORD','xord_p'),
        MelOptStruct(b'XOCP', [u'9f'],'occlusionPlaneWidth','occlusionPlaneHeight',
                     'occlusionPlanePosX','occlusionPlanePosY','occlusionPlanePosZ',
                     'occlusionPlaneRot1','occlusionPlaneRot2','occlusionPlaneRot3',
                     'occlusionPlaneRot4'),
        MelArray('portalData',
            MelStruct(b'XPOD', [u'2I'], (FID, 'portalOrigin'),
                      (FID, 'portalDestination')),
        ),
        MelOptStruct(b'XPTL', [u'9f'],'portalWidth','portalHeight','portalPosX','portalPosY','portalPosZ',
                     'portalRot1','portalRot2','portalRot3','portalRot4'),
        MelGroup('bound_data',
            MelPartialCounter(MelStruct(
                b'XRMR', [u'B', u'B', u'2s'], u'linked_rooms_count',
                (roomDataFlags, u'room_flags'), u'unknown1'),
                counter='linked_rooms_count', counts='linked_rooms'),
            MelFid(b'LNAM', 'lightingTemplate'),
            MelFid(b'INAM', 'imageSpace'),
            MelSorted(MelFids(b'XLRM', 'linked_rooms')),
        ),
        MelBase(b'XMBP','multiboundPrimitiveMarker'),
        MelBase(b'XRGD','ragdollData'),
        MelBase(b'XRGB','ragdollBipedData'),
        MelFloat(b'XRDS', 'radius'),
        MelReflectedRefractedBy(),
        MelSorted(MelFids(b'XLTW', 'litWaters')),
        MelFid(b'XEMI', 'emittance'),
        MelOptStruct(b'XLIG', [u'4f', u'4s'], u'fov90Delta', u'fadeDelta',
            u'end_distance_cap', u'shadowDepthBias', u'unknown2'),
        MelOptStruct(b'XALP', [u'B', u'B'],'cutoffAlpha','baseAlpha',),
        MelOptStruct(b'XTEL', [u'I', u'6f', u'I'],(FID,'destinationFid'),'destinationPosX',
                     'destinationPosY','destinationPosZ','destinationRotX',
                     'destinationRotY','destinationRotZ',
                     (_destinationFlags,'destinationFlags')),
        MelFids(b'XTNM','teleportMessageBox'),
        MelFid(b'XMBR','multiboundReference'),
        MelWaterVelocities(),
        MelOptStruct(b'XCVL', [u'4s', u'f', u'4s'], u'unknown3', u'angleX', u'unknown4'),
        MelFid(b'XCZR', u'unknown5'),
        MelBase(b'XCZA', 'xcza_p',),
        MelFid(b'XCZC', u'unknown6'),
        MelRefScale(),
        MelFid(b'XSPC','spawnContainer'),
        MelActivateParents(),
        MelFid(b'XLIB','leveledItemBaseObject'),
        MelSInt32(b'XLCM', 'levelModifier'),
        MelFid(b'XLCN','persistentLocation',),
        MelUInt32(b'XTRI', 'collisionLayer'),
        # {>>Lock Tab for REFR when 'Locked' is Unchecked this record is not present <<<}
        MelTruncatedStruct(b'XLOC', [u'B', u'3s', u'I', u'B', u'3s', u'8s'], 'lockLevel', 'unused1',
                           (FID, 'lockKey'), (_lockFlags, 'lockFlags'),
                           'unused3', 'unused4',
                           old_versions={'B3sIB3s4s', 'B3sIB3s'}),
        MelFid(b'XEZN','encounterZone'),
        MelOptStruct(b'XNDP', [u'I', u'H', u'2s'], (FID, u'navMesh'),
            u'teleportMarkerTriangle', u'unknown7'),
        MelFidList(b'XLRT','locationRefType',),
        MelNull(b'XIS2',),
        MelOwnership(),
        MelSInt32(b'XCNT', 'count'),
        MelFloat(b'XCHG', u'charge'),
        MelFid(b'XLRL','locationReference'),
        MelEnableParent(),
        MelLinkedReferences(),
        MelGroup('patrolData',
            MelFloat(b'XPRD', 'idleTime'),
            MelBase(b'XPPA','patrolScriptMarker'),
            MelFid(b'INAM', 'idle'),
            MelBase(b'SCHR','schr_p',),
            MelBase(b'SCTX','sctx_p',),
            MelTopicData('topic_data'),
        ),
        MelActionFlags(),
        MelFloat(b'XHTW', 'headTrackingWeight'),
        MelFloat(b'XFVC', 'favorCost'),
        MelBase(b'ONAM','onam_p'),
        MelMapMarker(),
        MelFid(b'XATR', 'attachRef'),
        MelXlod(),
        MelRef3D(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRegn(MelRecord):
    """Region."""
    rec_sig = b'REGN'

    obflags = Flags(0, Flags.getNames(
        ( 0,'conform'),
        ( 1,'paintVertices'),
        ( 2,'sizeVariance'),
        ( 3,'deltaX'),
        ( 4,'deltaY'),
        ( 5,'deltaZ'),
        ( 6,'Tree'),
        ( 7,'hugeRock'),))
    sdflags = Flags(0, Flags.getNames(
        ( 0,'pleasant'),
        ( 1,'cloudy'),
        ( 2,'rainy'),
        ( 3,'snowy'),))
    rdatFlags = Flags(0, Flags.getNames(
        ( 0,'Override'),))

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'RCLR', [u'3B', u's'],'mapRed','mapBlue','mapGreen','unused1'),
        MelFid(b'WNAM','worldspace'),
        MelGroups('areas',
            MelUInt32(b'RPLI', 'edgeFalloff'),
            MelArray('points',
                MelStruct(b'RPLD', [u'2f'], 'posX', 'posY'),
            ),
        ),
        MelSorted(MelGroups('entries',
            MelStruct(b'RDAT', [u'I', u'2B', u'2s'], 'entryType', (rdatFlags, 'flags'),
                      'priority', 'unused1'),
            MelIcon(),
            MelRegnEntrySubrecord(7, MelFid(b'RDMO', 'music')),
            MelRegnEntrySubrecord(7, MelSorted(MelArray('sounds',
                MelStruct(b'RDSA', [u'2I', u'f'], (FID, 'sound'),
                          (sdflags, 'flags'), 'chance'),
            ), sort_by_attrs='sound')),
            MelRegnEntrySubrecord(4, MelString(b'RDMP', 'mapName')),
            MelRegnEntrySubrecord(2, MelArray('objects',
                MelStruct(b'RDOT',
                    [u'I', u'H', u'2s', u'f', u'4B', u'2H', u'5f', u'3H', u'2s', u'4s'], (FID, 'objectId'),
                    'parentIndex', 'unk1', 'density', 'clustering',
                    'minSlope', 'maxSlope', (obflags, 'flags'),
                    'radiusWRTParent', 'radius', 'minHeight', 'maxHeight',
                    'sink', 'sinkVar', 'sizeVar', 'angleVarX', 'angleVarY',
                    'angleVarZ', 'unk2', 'unk3'),
            )),
            MelRegnEntrySubrecord(6, MelSorted(MelArray('grasses',
                MelStruct(b'RDGS', [u'I', u'4s'], (FID, 'grass'), 'unknown'),
            ), sort_by_attrs='grass')),
            MelRegnEntrySubrecord(3, MelSorted(MelArray('weatherTypes',
                MelStruct(b'RDWT', [u'3I'], (FID, u'weather'), u'chance',
                          (FID, u'global')),
            ), sort_by_attrs='weather')),
        ), sort_by_attrs='entryType'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRela(MelRecord):
    """Relationship."""
    rec_sig = b'RELA'

    RelationshipFlags = Flags(0, Flags.getNames(
        (0,'Unknown 1'),
        (1,'Unknown 2'),
        (2,'Unknown 3'),
        (3,'Unknown 4'),
        (4,'Unknown 5'),
        (5,'Unknown 6'),
        (6,'Unknown 7'),
        (7,'Secret'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', [u'2I', u'H', u's', u'B', u'I'],(FID,'parent'),(FID,'child'),'rankType',
                  'unknown',(RelationshipFlags, u'relaFlags'),(FID,'associationType'),),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRevb(MelRecord):
    """Reverb Parameters"""
    rec_sig = b'REVB'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', [u'2H', u'4b', u'6B'],'decayTimeMS','hfReferenceHZ','roomFilter',
                  'hfRoomFilter','reflections','reverbAmp','decayHFRatio',
                  'reflectDelayMS','reverbDelayMS','diffusion','density',
                  'unknown',),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRfct(MelRecord):
    """Visual Effect."""
    rec_sig = b'RFCT'

    RfctTypeFlags = Flags(0, Flags.getNames(
        u'rotate_to_face_target',
        u'attach_to_camera',
        u'inherit_rotation',
    ))

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', [u'3I'], (FID, u'rfct_art'), (FID, u'rfct_shader'),
            (RfctTypeFlags, u'rfct_flags')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreScen(MelRecord):
    """Scene."""
    rec_sig = b'SCEN'

    ScenFlags5 = Flags(0, Flags.getNames(
            (15, 'faceTarget'),
            (16, 'looping'),
            (17, 'headtrackPlayer'),
        ))

    ScenFlags3 = Flags(0, Flags.getNames(
            (0, 'deathPauseunsused'),
            (1, 'deathEnd'),
            (2, 'combatPause'),
            (3, 'combatEnd'),
            (4, 'dialoguePause'),
            (5, 'dialogueEnd'),
            (6, 'oBS_COMPause'),
            (7, 'oBS_COMEnd'),
        ))

    ScenFlags2 = Flags(0, Flags.getNames(
            (0, 'noPlayerActivation'),
            (1, 'optional'),
        ))

    ScenFlags1 = Flags(0, Flags.getNames(
            (0, 'beginonQuestStart'),
            (1, 'stoponQuestEnd'),
            (2, 'unknown3'),
            (3, 'repeatConditionsWhileTrue'),
            (4, 'interruptible'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelUInt32Flags(b'FNAM', u'flags', ScenFlags1),
        MelGroups('phases',
            MelNull(b'HNAM'),
            # Phase description. Always present, even if just a null-terminator
            MelString(b'NAM0', u'phase_desc',),
            MelGroup('startConditions',
                MelConditions(),
            ),
            MelNull(b'NEXT'),
            MelGroup('completionConditions',
                MelConditions(),
            ),
            # The next three are all leftovers
            MelGroup(u'unused1',
                MelBase(b'SCHR','schr_p'),
                MelBase(b'SCDA','scda_p'),
                MelBase(b'SCTX','sctx_p'),
                MelBase(b'QNAM','qnam_p'),
                MelBase(b'SCRO','scro_p'),
            ),
            MelNull(b'NEXT'),
            MelGroup(u'unused2',
                MelBase(b'SCHR','schr_p'),
                MelBase(b'SCDA','scda_p'),
                MelBase(b'SCTX','sctx_p'),
                MelBase(b'QNAM','qnam_p'),
                MelBase(b'SCRO','scro_p'),
            ),
            MelUInt32(b'WNAM', 'editorWidth'),
            MelNull(b'HNAM'),
        ),
        MelGroups('actors',
            MelUInt32(b'ALID', 'actorID'),
            MelUInt32Flags(b'LNAM', u'scenFlags2', ScenFlags2),
            MelUInt32Flags(b'DNAM', u'flags3', ScenFlags3),
        ),
        MelGroups('actions',
            MelUInt16(b'ANAM', 'actionType'),
            MelString(b'NAM0', u'action_desc',),
            MelUInt32(b'ALID', 'actorID',),
            MelBase(b'LNAM','lnam_p',),
            MelUInt32(b'INAM', 'index'),
            MelUInt32Flags(b'FNAM', u'flags', ScenFlags5),
            MelUInt32(b'SNAM', 'startPhase'),
            MelUInt32(b'ENAM', 'endPhase'),
            MelFloat(b'SNAM', 'timerSeconds'),
            MelFids(b'PNAM','packages'),
            MelFid(b'DATA','topic'),
            MelUInt32(b'HTID', 'headtrackActorID'),
            MelFloat(b'DMAX', 'loopingMax'),
            MelFloat(b'DMIN', 'loopingMin'),
            MelUInt32(b'DEMO', 'emotionType'),
            MelUInt32(b'DEVA', 'emotionValue'),
            MelGroup('unused', # leftover
                MelBase(b'SCHR','schr_p'),
                MelBase(b'SCDA','scda_p'),
                MelBase(b'SCTX','sctx_p'),
                MelBase(b'QNAM','qnam_p'),
                MelBase(b'SCRO','scro_p'),
            ),
            MelNull(b'ANAM'),
        ),
        # The next three are all leftovers
        MelGroup(u'unused1',
            MelBase(b'SCHR','schr_p'),
            MelBase(b'SCDA','scda_p'),
            MelBase(b'SCTX','sctx_p'),
            MelBase(b'QNAM','qnam_p'),
            MelBase(b'SCRO','scro_p'),
        ),
        MelNull(b'NEXT'),
        MelGroup(u'unused2',
            MelBase(b'SCHR','schr_p'),
            MelBase(b'SCDA','scda_p'),
            MelBase(b'SCTX','sctx_p'),
            MelBase(b'QNAM','qnam_p'),
            MelBase(b'SCRO','scro_p'),
        ),
        MelFid(b'PNAM','quest',),
        MelUInt32(b'INAM', 'lastActionIndex'),
        MelBase(b'VNAM','vnam_p'),
        MelConditions(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreScrl(MelRecord):
    """Scroll."""
    rec_sig = b'SCRL'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelKeywords(),
        MelMdob(),
        MelEquipmentType(),
        MelDescription(),
        MelModel(),
        MelDestructible(),
        MelPickupSound(),
        MelDropSound(),
        MelStruct(b'DATA', [u'I', u'f'], u'itemValue', u'itemWeight'),
        MelSpit(),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreShou(MelRecord):
    """Shout."""
    rec_sig = b'SHOU'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelMdob(),
        MelDescription(),
        MelGroups('wordsOfPower',
            MelStruct(b'SNAM', [u'2I', u'f'], (FID, u'word'), (FID, u'spell'),
                      u'recoveryTime'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSlgm(MelRecord):
    """Soul Gem."""
    rec_sig = b'SLGM'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelPickupSound(),
        MelDropSound(),
        MelKeywords(),
        MelStruct(b'DATA', [u'I', u'f'],'value','weight'),
        MelUInt8(b'SOUL', u'soul'),
        MelUInt8(b'SLCP', u'capacity', 1),
        MelFid(b'NAM0','linkedTo'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSmbn(MelRecord):
    """Story Manager Branch Node."""
    rec_sig = b'SMBN'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'PNAM', u'sm_parent'),
        MelFid(b'SNAM', u'sm_child'),
        MelConditionCounter(),
        MelConditions(),
        MelSMFlags(),
        MelUInt32(b'XNAM', u'max_concurrent_quests'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSmen(MelRecord):
    """Story Manager Event Node."""
    rec_sig = b'SMEN'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'PNAM', u'sm_parent'),
        MelFid(b'SNAM', u'sm_child'),
        MelConditionCounter(),
        MelConditions(),
        MelSMFlags(),
        MelUInt32(b'XNAM', u'max_concurrent_quests'),
        MelUInt32(b'ENAM', u'sm_type'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSmqn(MelRecord):
    """Story Manager Quest Node."""
    rec_sig = b'SMQN'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'PNAM', u'sm_parent'),
        MelFid(b'SNAM', u'sm_child'),
        MelConditionCounter(),
        MelConditions(),
        MelSMFlags(with_quest_flags=True),
        MelUInt32(b'XNAM', u'max_concurrent_quests'),
        MelUInt32(b'MNAM', u'num_quests_to_run'),
        MelCounter(MelUInt32(b'QNAM', u'quest_count'), counts=u'sm_quests'),
        MelGroups(u'sm_quests',
            MelFid(b'NNAM', u'sm_quest'),
            MelUInt32(b'FNAM', u'sm_quest_flags'), # all unknown
            MelFloat(b'RNAM', u'hours_until_reset'),
        )
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSnct(MelRecord):
    """Sound Category."""
    rec_sig = b'SNCT'

    SoundCategoryFlags = Flags(0, Flags.getNames(
        (0,'muteWhenSubmerged'),
        (1,'shouldAppearOnMenu'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt32Flags(b'FNAM', u'flags', SoundCategoryFlags),
        MelFid(b'PNAM','parent',),
        MelUInt16(b'VNAM', 'staticVolumeMultiplier'),
        MelUInt16(b'UNAM', 'defaultMenuValue'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSndr(MelRecord):
    """Sound Descriptor."""
    rec_sig = b'SNDR'

    melSet = MelSet(
        MelEdid(),
        MelBase(b'CNAM','cnam_p'),
        MelFid(b'GNAM','category',),
        MelFid(b'SNAM','altSoundFor',),
        MelGroups('sounds',
            MelString(b'ANAM', 'sound_file_name',),
        ),
        MelFid(b'ONAM','outputModel',),
        MelLString(b'FNAM','string'),
        MelConditions(),
        MelStruct(b'LNAM', [u's', u'B', u's', u'B'],'unkSndr1','looping',
                  'unkSndr2','rumbleSendValue',),
        MelStruct(b'BNAM', [u'2b', u'2B', u'H'], u'pctFrequencyShift',
            u'pctFrequencyVariance', u'priority', u'dbVariance',
            u'staticAtten'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSopm(MelRecord):
    """Sound Output Model."""
    rec_sig = b'SOPM'

    _sopm_flags = Flags(0, Flags.getNames(
        u'attenuates_with_distance',
        u'allows_rumble',
    ))

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'NAM1', [u'B', u'2s', u'B'], (_sopm_flags, u'flags'),
            u'unknown1', u'reverbSendpct'),
        MelBase(b'FNAM', u'unused_fnam'),
        MelUInt32(b'MNAM', u'outputType'),
        MelBase(b'CNAM', u'unused_cnam'),
        MelBase(b'SNAM', u'unused_snam'),
        MelStruct(b'ONAM', [u'24B'], u'ch0_l', u'ch0_r', u'ch0_c', u'ch0_lFE',
            u'ch0_rL', u'ch0_rR', u'ch0_bL', u'ch0_bR', u'ch1_l', u'ch1_r',
            u'ch1_c', u'ch1_lFE', u'ch1_rL', u'ch1_rR', u'ch1_bL', u'ch1_bR',
            u'ch2_l', u'ch2_r', u'ch2_c', u'ch2_lFE', u'ch2_rL', u'ch2_rR',
            u'ch2_bL', u'ch2_bR'),
        MelStruct(b'ANAM', [u'4s', u'2f', u'5B', u'3s'], u'unknown2',
            u'minDistance', u'maxDistance', u'curve1', u'curve2', u'curve3',
            u'curve4', u'curve5', u'unknown3'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSoun(MelRecord):
    """Sound Marker."""
    rec_sig = b'SOUN'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelString(b'FNAM','soundFileUnused'), # leftover
        MelBase(b'SNDD','soundDataUnused'), # leftover
        MelFid(b'SDSC','soundDescriptor'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSpel(MelRecord):
    """Spell."""
    rec_sig = b'SPEL'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelKeywords(),
        MelMdob(),
        MelEquipmentType(),
        MelDescription(),
        MelSpit(),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSpgd(MelRecord):
    """Shader Particle Geometry."""
    rec_sig = b'SPGD'

    _SpgdDataFlags = Flags(0, Flags.getNames('rain', 'snow'))

    melSet = MelSet(
        MelEdid(),
        MelTruncatedStruct(b'DATA',
            [u'7f', u'4I', u'f'], 'gravityVelocity', 'rotationVelocity',
            'particleSizeX', 'particleSizeY', 'centerOffsetMin',
            'centerOffsetMax', 'initialRotationRange', 'numSubtexturesX',
            'numSubtexturesY', (_SpgdDataFlags, u'typeFlags'),
            'boxSize', 'particleDensity', old_versions={'7f3I'}),
        MelIcon(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreStat(MelRecord):
    """Static."""
    rec_sig = b'STAT'

    _SnowFlags = Flags(0, Flags.getNames(
        'considered_Snow',
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        if_sse(
            le_version=MelStruct(b'DNAM', [u'f', u'I'], 'maxAngle30to120',
                                 (FID, 'material')),
            se_version=MelTruncatedStruct(
                b'DNAM', [u'f', u'I', u'B', u'3s'], 'maxAngle30to120',
                (FID, 'material'), (_SnowFlags, 'snow_flags'), 'unused1',
                old_versions={'fI'}),
        ),
        # Contains null-terminated mesh filename followed by random data
        # up to 260 bytes and repeats 4 times
        MelBase(b'MNAM', 'distantLOD'),
        MelBase(b'ENAM', 'unknownENAM'),
    )
    __slots__ = melSet.getSlotsUsed()

# MNAM Should use a custom unpacker if needed for the patcher otherwise MelBase
#------------------------------------------------------------------------------
class MreTact(MelRecord):
    """Talking Activator."""
    rec_sig = b'TACT'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelBase(b'PNAM','pnam_p'),
        MelFid(b'SNAM', 'soundLoop'),
        MelBase(b'FNAM','fnam_p'),
        MelFid(b'VNAM', 'voiceType'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreTree(MelRecord):
    """Tree."""
    rec_sig = b'TREE'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelModel(),
        MelFid(b'PFIG','harvestIngredient'),
        MelFid(b'SNAM','harvestSound'),
        MelStruct(b'PFPC', [u'4B'],'spring','summer','fall','wsinter',),
        MelFull(),
        MelStruct(b'CNAM', [u'12f'], u'trunk_flexibility', u'branch_flexibility',
                  u'trunk_amplitude', u'front_amplitude', u'back_amplitude',
                  u'side_amplitude', u'front_frequency', u'back_frequency',
                  u'side_frequency', u'leaf_flexibility', u'leaf_amplitude',
                  u'leaf_frequency'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreTxst(MelRecord):
    """Texture Set."""
    rec_sig = b'TXST'

    TxstTypeFlags = Flags(0, Flags.getNames(
        (0, 'noSpecularMap'),
        (1, 'facegenTextures'),
        (2, 'hasModelSpaceNormalMap'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelGroups('destructionData',
            MelString(b'TX00','difuse'),
            MelString(b'TX01','normalGloss'),
            MelString(b'TX02','enviroMaskSubSurfaceTint'),
            MelString(b'TX03','glowDetailMap'),
            MelString(b'TX04','height'),
            MelString(b'TX05','environment'),
            MelString(b'TX06','multilayer'),
            MelString(b'TX07','backlightMaskSpecular'),
        ),
        MelDecalData(),
        MelUInt16Flags(b'DNAM', u'flags', TxstTypeFlags),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreVtyp(MelRecord):
    """Voice Type."""
    rec_sig = b'VTYP'

    VtypTypeFlags = Flags(0, Flags.getNames(
            (0, 'allowDefaultDialog'),
            (1, 'female'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelUInt8Flags(b'DNAM', u'flags', VtypTypeFlags),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWatr(MelRecord):
    """Water."""
    rec_sig = b'WATR'

    WatrTypeFlags = Flags(0, Flags.getNames(
            (0, 'causesDamage'),
        ))

    # Struct elements shared by DNAM in SLE and SSE
    _dnam_common = [
        'unknown1', 'unknown2', 'unknown3', 'unknown4',
        'specularPropertiesSunSpecularPower',
        'waterPropertiesReflectivityAmount', 'waterPropertiesFresnelAmount',
        'unknown5', 'fogPropertiesAboveWaterFogDistanceNearPlane',
        'fogPropertiesAboveWaterFogDistanceFarPlane',
        # Shallow Color
        'red_sc','green_sc','blue_sc','unknown_sc',
        # Deep Color
        'red_dc','green_dc','blue_dc','unknown_dc',
        # Reflection Color
        'red_rc','green_rc','blue_rc','unknown_rc',
        'unknown6', 'unknown7', 'unknown8', 'unknown9', 'unknown10',
        'displacementSimulatorStartingSize', 'displacementSimulatorForce',
        'displacementSimulatorVelocity', 'displacementSimulatorFalloff',
        'displacementSimulatorDampner', 'unknown11',
        'noisePropertiesNoiseFalloff', 'noisePropertiesLayerOneWindDirection',
        'noisePropertiesLayerTwoWindDirection',
        'noisePropertiesLayerThreeWindDirection',
        'noisePropertiesLayerOneWindSpeed', 'noisePropertiesLayerTwoWindSpeed',
        'noisePropertiesLayerThreeWindSpeed', 'unknown12', 'unknown13',
        'fogPropertiesAboveWaterFogAmount', 'unknown14',
        'fogPropertiesUnderWaterFogAmount',
        'fogPropertiesUnderWaterFogDistanceNearPlane',
        'fogPropertiesUnderWaterFogDistanceFarPlane',
        'waterPropertiesRefractionMagnitude',
        'specularPropertiesSpecularPower', 'unknown15',
        'specularPropertiesSpecularRadius',
        'specularPropertiesSpecularBrightness',
        'noisePropertiesLayerOneUVScale', 'noisePropertiesLayerTwoUVScale',
        'noisePropertiesLayerThreeUVScale',
        'noisePropertiesLayerOneAmplitudeScale',
        'noisePropertiesLayerTwoAmplitudeScale',
        'noisePropertiesLayerThreeAmplitudeScale',
        'waterPropertiesReflectionMagnitude',
        'specularPropertiesSunSparkleMagnitude',
        'specularPropertiesSunSpecularMagnitude',
        'depthPropertiesReflections', 'depthPropertiesRefraction',
        'depthPropertiesNormals', 'depthPropertiesSpecularLighting',
        'specularPropertiesSunSparklePower',
    ]

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelGroups('unused',
            MelString(b'NNAM','noiseMap',),
        ),
        MelUInt8(b'ANAM', 'opacity'),
        MelUInt8Flags(b'FNAM', u'flags', WatrTypeFlags),
        MelBase(b'MNAM','unused1'),
        MelFid(b'TNAM','material',),
        MelFid(b'SNAM','openSound',),
        MelFid(b'XNAM','spell',),
        MelFid(b'INAM','imageSpace',),
        MelUInt16(b'DATA', 'damagePerSecond'),
        if_sse(
            le_version=MelStruct(b'DNAM', [u'7f', u'4s', u'2f', u'3B', u's', u'3B', u's', u'3B', u's', u'4s', u'43f'],
                                 *_dnam_common),
            se_version=MelTruncatedStruct(b'DNAM',
                [u'7f', u'4s', u'2f', u'3B', u's', u'3B', u's', u'3B', u's',
                 u'4s', u'44f'],
                *(_dnam_common + ['noisePropertiesFlowmapScale']),
                old_versions={'7f4s2f3Bs3Bs3Bs4s43f'}),
        ),
        MelBase(b'GNAM','unused2'),
        # Linear Velocity
        MelStruct(b'NAM0', [u'3f'],'linv_x','linv_y','linv_z',),
        # Angular Velocity
        MelStruct(b'NAM1', [u'3f'],'andv_x','andv_y','andv_z',),
        MelString(b'NAM2', 'noiseTextureLayer1'),
        MelString(b'NAM3', 'noiseTextureLayer2'),
        MelString(b'NAM4', 'noiseTextureLayer3'),
        sse_only(MelString(b'NAM5', 'flowNormalsNoiseTexture')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWeap(MelRecord):
    """Weapon"""
    rec_sig = b'WEAP'

    WeapFlags3 = Flags(0, Flags.getNames(
        (0, 'onDeath'),
    ))

    WeapFlags2 = Flags(0, Flags.getNames(
            (0, 'playerOnly'),
            (1, 'nPCsUseAmmo'),
            (2, 'noJamAfterReloadunused'),
            (3, 'unknown4'),
            (4, 'minorCrime'),
            (5, 'rangeFixed'),
            (6, 'notUsedinNormalCombat'),
            (7, 'unknown8'),
            (8, 'dont_use_3rd_person_IS_anim'),
            (9, 'unknown10'),
            (10, 'rumbleAlternate'),
            (11, 'unknown12'),
            (12, 'nonhostile'),
            (13, 'boundWeapon'),
        ))

    WeapFlags1 = Flags(0, Flags.getNames(
            (0, 'ignoresNormalWeaponResistance'),
            (1, 'automaticunused'),
            (2, 'hasScopeunused'),
            (3, 'cant_drop'),
            (4, 'hideBackpackunused'),
            (5, 'embeddedWeaponunused'),
            (6, 'dont_use_1st_person_IS_anim_unused'),
            (7, 'nonplayable'),
        ))

    class MelWeapCrdt(MelTruncatedStruct):
        """Handle older truncated CRDT for WEAP subrecord.

        Old Skyrim format H2sfB3sI FormID is the last integer.

        New Format H2sfB3s4sI4s FormID is the integer prior to the last 4S.
        Bethesda did not append the record they inserted bytes which shifts the
        FormID 4 bytes."""
        def _pre_process_unpacked(self, unpacked_val):
            if len(unpacked_val) == 6:
                # old skyrim record, insert null bytes in the middle(!)
                crit_damage, crit_unknown1, crit_mult, crit_flags, \
                crit_unknown2, crit_effect = unpacked_val
                ##: Why use null3 instead of crit_unknown2?
                unpacked_val = (crit_damage, crit_unknown1, crit_mult,
                                crit_flags, null3, null4, crit_effect, null4)
            return MelTruncatedStruct._pre_process_unpacked(self, unpacked_val)

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(u'model1', b'MODL'),
        MelIcons(),
        MelEnchantment(),
        MelUInt16(b'EAMT', 'enchantPoints'),
        MelDestructible(),
        MelEquipmentType(),
        MelFid(b'BIDS','blockBashImpactDataSet',),
        MelFid(b'BAMT','alternateBlockMaterial',),
        MelPickupSound(),
        MelDropSound(),
        MelKeywords(),
        MelDescription(),
        MelModel(u'model2', b'MOD3'),
        MelBase(b'NNAM','unused1'),
        MelFid(b'INAM','impactDataSet',),
        MelFid(b'WNAM','firstPersonModelObject',),
        MelFid(b'SNAM','attackSound',),
        MelFid(b'XNAM','attackSound2D',),
        MelFid(b'NAM7','attackLoopSound',),
        MelFid(b'TNAM','attackFailSound',),
        MelFid(b'UNAM','idleSound',),
        MelFid(b'NAM9','equipSound',),
        MelFid(b'NAM8','unequipSound',),
        MelStruct(b'DATA', [u'I', u'f', u'H'],'value','weight','damage',),
        MelStruct(b'DNAM', [u'B', u'3s', u'2f', u'H', u'2s', u'f', u'4s', u'4B', u'2f', u'2I', u'5f', u'12s', u'i', u'8s', u'i', u'4s', u'f'], u'animationType',
                  u'dnamUnk1', u'speed', u'reach',
                  (WeapFlags1, u'dnamFlags1'), u'dnamUnk2',
                  u'sightFOV', u'dnamUnk3', u'baseVATSToHitChance',
                  u'attackAnimation', u'numProjectiles',
                  u'embeddedWeaponAVunused', u'minRange', u'maxRange',
                  u'onHit', (WeapFlags2, u'dnamFlags2'),
                  u'animationAttackMultiplier', u'dnamUnk4',
                  u'rumbleLeftMotorStrength', u'rumbleRightMotorStrength',
                  u'rumbleDuration', u'dnamUnk5', u'skill',
                  u'dnamUnk6', u'resist', u'dnamUnk7', u'stagger'),
        if_sse(
            le_version=MelStruct(b'CRDT',
                [u'H', u'2s', u'f', u'B', u'3s', u'I'], u'critDamage', u'crdtUnk1',
                u'criticalMultiplier', (WeapFlags3, u'criticalFlags'),
                u'crdtUnk2', (FID, u'criticalEffect')),
            se_version=MelWeapCrdt(b'CRDT',
                [u'H', u'2s', u'f', u'B', u'3s', u'4s', u'I', u'4s'], u'critDamage', u'crdtUnk1',
                u'criticalMultiplier', (WeapFlags3, u'criticalFlags'),
                u'crdtUnk2', u'crdtUnk3',
                (FID, u'criticalEffect'), u'crdtUnk4',
                old_versions={u'H2sfB3sI'}),
        ),
        MelUInt32(b'VNAM', 'detectionSoundLevel'),
        MelFid(b'CNAM','template',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWoop(MelRecord):
    """Word of Power."""
    rec_sig = b'WOOP'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelLString(b'TNAM','translation'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWrld(MelRecord):
    """Worldspace."""
    rec_sig = b'WRLD'

    WrldFlags2 = Flags(0, Flags.getNames(
            (0, 'smallWorld'),
            (1, 'noFastTravel'),
            (2, 'unknown3'),
            (3, 'noLODWater'),
            (4, 'noLandscape'),
            (5, 'unknown6'),
            (6, 'fixedDimensions'),
            (7, 'noGrass'),
        ))

    WrldFlags1 = Flags(0, Flags.getNames(
            (0, 'useLandData'),
            (1, 'useLODData'),
            (2, 'useMapData'),
            (3, 'useWaterData'),
            (4, 'useClimateData'),
            (5, 'useImageSpaceDataunused'),
            (6, 'useSkyCell'),
        ))

    melSet = MelSet(
        MelEdid(),
        if_sse(le_version=MelNull(b'RNAM'), # unused
               # This formatting is hideous, not sure how to improve it though
               se_version=MelGroups(
                   u'large_references', MelArray(
                       u'large_refs', MelStruct(
                           b'RNAM', ['I', 'h', 'h'], (FID, u'lr_ref'),
                           u'lr_y', u'lr_x'),
                       prelude=MelPartialCounter(
                           MelStruct(b'RNAM', ['h', 'h', 'I'], 'lr_grid_y',
                                     'lr_grid_x', 'large_refs_count'),
                           counter='large_refs_count', counts='large_refs')))),
        MelBase(b'MHDT','maxHeightData'),
        MelFull(),
        # Fixed Dimensions Center Cell
        MelOptStruct(b'WCTR', [u'2h'],'fixedX','fixedY',),
        MelFid(b'LTMP','interiorLighting',),
        MelFid(b'XEZN','encounterZone',),
        MelFid(b'XLCN','location',),
        MelGroup('parent',
            MelFid(b'WNAM','worldspace',),
            MelStruct(b'PNAM', [u'B', u's'],(WrldFlags1, u'parentFlags'),'unknown',),
        ),
        MelFid(b'CNAM','climate',),
        MelFid(b'NAM2','water',),
        MelFid(b'NAM3','lODWaterType',),
        MelFloat(b'NAM4', u'lODWaterHeight'),
        MelOptStruct(b'DNAM', [u'2f'],'defaultLandHeight',
                     'defaultWaterHeight',),
        MelIcon(u'mapImage'),
        MelModel(u'cloudModel', b'MODL'),
        MelTruncatedStruct(b'MNAM', [u'2i', u'4h', u'3f'], 'usableDimensionsX',
                           'usableDimensionsY', 'cellCoordinatesX',
                           'cellCoordinatesY', 'seCellX', 'seCellY',
                           'cameraDataMinHeight', 'cameraDataMaxHeight',
                           'cameraDataInitialPitch', is_optional=True,
                           old_versions={'2i4h2f', '2i4h'}),
        MelStruct(b'ONAM', [u'4f'],'worldMapScale','cellXOffset','cellYOffset',
                  'cellZOffset',),
        MelFloat(b'NAMA', 'distantLODMultiplier'),
        MelUInt8Flags(b'DATA', u'dataFlags', WrldFlags2),
        MelWorldBounds(),
        MelFid(b'ZNAM','music',),
        MelString(b'NNAM','canopyShadowunused'),
        MelString(b'XNAM','waterNoiseTexture'),
        MelString(b'TNAM','hDLODDiffuseTexture'),
        MelString(b'UNAM','hDLODNormalTexture'),
        MelString(b'XWEM','waterEnvironmentMapunused'),
        MelNull(b'OFST'), # Not even CK/xEdit can recalculate these right now
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Many Things Marked MelBase that need updated
class MreWthr(MelRecord):
    """Weather"""
    rec_sig = b'WTHR'

    WthrFlags2 = Flags(0, Flags.getNames(
            (0, 'layer_0'),
            (1, 'layer_1'),
            (2, 'layer_2'),
            (3, 'layer_3'),
            (4, 'layer_4'),
            (5, 'layer_5'),
            (6, 'layer_6'),
            (7, 'layer_7'),
            (8, 'layer_8'),
            (9, 'layer_9'),
            (10, 'layer_10'),
            (11, 'layer_11'),
            (12, 'layer_12'),
            (13, 'layer_13'),
            (14, 'layer_14'),
            (15, 'layer_15'),
            (16, 'layer_16'),
            (17, 'layer_17'),
            (18, 'layer_18'),
            (19, 'layer_19'),
            (20, 'layer_20'),
            (21, 'layer_21'),
            (22, 'layer_22'),
            (23, 'layer_23'),
            (24, 'layer_24'),
            (25, 'layer_25'),
            (26, 'layer_26'),
            (27, 'layer_27'),
            (28, 'layer_28'),
            (29, 'layer_29'),
            (30, 'layer_30'),
            (31, 'layer_31'),
        ))

    WthrFlags1 = Flags(0, Flags.getNames(
            (0, 'weatherPleasant'),
            (1, 'weatherCloudy'),
            (2, 'weatherRainy'),
            (3, 'weatherSnow'),
            (4, 'skyStaticsAlwaysVisible'),
            (5, 'skyStaticsFollowsSunPosition'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelString(b'\x300TX','cloudTextureLayer_0'),
        MelString(b'\x310TX','cloudTextureLayer_1'),
        MelString(b'\x320TX','cloudTextureLayer_2'),
        MelString(b'\x330TX','cloudTextureLayer_3'),
        MelString(b'\x340TX','cloudTextureLayer_4'),
        MelString(b'\x350TX','cloudTextureLayer_5'),
        MelString(b'\x360TX','cloudTextureLayer_6'),
        MelString(b'\x370TX','cloudTextureLayer_7'),
        MelString(b'\x380TX','cloudTextureLayer_8'),
        MelString(b'\x390TX','cloudTextureLayer_9'),
        MelString(b'\x3A0TX','cloudTextureLayer_10'),
        MelString(b'\x3B0TX','cloudTextureLayer_11'),
        MelString(b'\x3C0TX','cloudTextureLayer_12'),
        MelString(b'\x3D0TX','cloudTextureLayer_13'),
        MelString(b'\x3E0TX','cloudTextureLayer_14'),
        MelString(b'\x3F0TX','cloudTextureLayer_15'),
        MelString(b'\x400TX','cloudTextureLayer_16'),
        MelString(b'A0TX','cloudTextureLayer_17'),
        MelString(b'B0TX','cloudTextureLayer_18'),
        MelString(b'C0TX','cloudTextureLayer_19'),
        MelString(b'D0TX','cloudTextureLayer_20'),
        MelString(b'E0TX','cloudTextureLayer_21'),
        MelString(b'F0TX','cloudTextureLayer_22'),
        MelString(b'G0TX','cloudTextureLayer_23'),
        MelString(b'H0TX','cloudTextureLayer_24'),
        MelString(b'I0TX','cloudTextureLayer_25'),
        MelString(b'J0TX','cloudTextureLayer_26'),
        MelString(b'K0TX','cloudTextureLayer_27'),
        MelString(b'L0TX','cloudTextureLayer_28'),
        MelBase(b'DNAM', 'unused1'),
        MelBase(b'CNAM', 'unused2'),
        MelBase(b'ANAM', 'unused3'),
        MelBase(b'BNAM', 'unused4'),
        MelBase(b'LNAM','lnam_p'),
        MelFid(b'MNAM','precipitationType',),
        MelFid(b'NNAM','visualEffect',),
        MelBase(b'ONAM', 'unused5'),
        MelArray('cloudSpeedY',
            MelUInt8(b'RNAM', 'cloud_speed_layer'),
        ),
        MelArray('cloudSpeedX',
            MelUInt8(b'QNAM', 'cloud_speed_layer'),
        ),
        MelArray('cloudColors',
            MelWthrColors(b'PNAM'),
        ),
        MelArray('cloudAlphas',
            MelStruct(b'JNAM', [u'4f'], 'sunAlpha', 'dayAlpha', 'setAlpha',
                      'nightAlpha'),
        ),
        MelArray('daytimeColors',
            MelWthrColors(b'NAM0'),
        ),
        MelStruct(b'FNAM', [u'8f'],'dayNear','dayFar','nightNear','nightFar',
                  'dayPower','nightPower','dayMax','nightMax',),
        MelStruct(b'DATA', [u'B', u'2s', u'16B'],'windSpeed','unknown','transDelta',
                  'sunGlare','sunDamage','precipitationBeginFadeIn',
                  'precipitationEndFadeOut','thunderLightningBeginFadeIn',
                  'thunderLightningEndFadeOut','thunderLightningFrequency',
                  (WthrFlags1, u'wthrFlags1'),'red','green','blue',
                  'visualEffectBegin','visualEffectEnd',
                  'windDirection','windDirectionRange',),
        MelUInt32Flags(b'NAM1', u'wthrFlags2', WthrFlags2),
        MelGroups('sounds',
            MelStruct(b'SNAM', [u'2I'], (FID, 'sound'), 'type'),
        ),
        MelSorted(MelFids(b'TNAM', 'skyStatics')),
        MelStruct(b'IMSP', [u'4I'], (FID, 'image_space_sunrise'),
                  (FID, 'image_space_day'), (FID, 'image_space_sunset'),
                  (FID, 'image_space_night'),),
        sse_only(MelOptStruct(
            b'HNAM', [u'4I'], (FID, 'volumetricLightingSunrise'),
            (FID, 'volumetricLightingDay'), (FID, 'volumetricLightingSunset'),
            (FID, 'volumetricLightingNight'))),
        MelGroups('wthrAmbientColors',
            MelTruncatedStruct(b'DALC',
                [u'4B', u'4B', u'4B', u'4B', u'4B', u'4B', u'4B', u'f'],
                'redXplus', 'greenXplus',
                'blueXplus', 'unknownXplus', 'redXminus', 'greenXminus',
                'blueXminus', 'unknownXminus', 'redYplus', 'greenYplus',
                'blueYplus', 'unknownYplus', 'redYminus', 'greenYminus',
                'blueYminus', 'unknownYminus', 'redZplus', 'greenZplus',
                'blueZplus', 'unknownZplus', 'redZminus', 'greenZminus',
                'blueZminus', 'unknownZminus', 'redSpec', 'greenSpec',
                'blueSpec', 'unknownSpec', 'fresnelPower',
                old_versions={'4B4B4B4B4B4B'}),
        ),
        MelBase(b'NAM2', 'unused6'),
        MelBase(b'NAM3', 'unused7'),
        MelModel(u'aurora', b'MODL'),
        sse_only(MelFid(b'GNAM', 'sunGlareLensFlare')),
    )
    __slots__ = melSet.getSlotsUsed()
